"""Resources area summary.

Two inputs.
1. tools/krr.json — Robusta KRR recommendations saved by the core collector's `krr` step (type: tool) via `krr simple -f json`. KRR uses Prometheus history (14 days by default)
      to recommend per-container request/limit values and labels the gap to the current value CRITICAL, WARNING, OK, GOOD or UNKNOWN (UNKNOWN = no data or HPA target).
      simple strategy: CPU request = p95, CPU limit = none (unset) recommended, memory request = limit = max + 15%.
2. metrics/*_p95_*_7d.json — 7-day p95 subqueries from core metrics.yaml. Per-container p95/request and p95/limit ratios. The first-pass evaluation (resources.*-overprovisioned etc.) uses them directly;
      here we only build workload-level top lists.

Output: the `resources` section of summary.json. Shape documented in SKILL.md.
"""

from __future__ import annotations

import contextlib
import re
from collections import Counter, defaultdict
from pathlib import Path

from .controlplane import workload_of
from .snapshot import load_json

SEV_ORDER = {"CRITICAL": 0, "WARNING": 1, "OK": 2, "GOOD": 3, "UNKNOWN": 4}


def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    return None  # "?" (UNKNOWN) or None (no limit recommended)


def _mb(b):
    return None if b is None else round(b / 1048576)


def _cores(c):
    return None if c is None else round(c, 3)


def analyze_krr(snap: Path) -> dict:
    j = load_json(snap / "tools" / "krr.json")
    if not j:
        return {"present": False, "note": "tools/krr.json missing (krr tool absent or collection skipped). Report section 6: tool missing"}
    scans = j.get("scans") or []
    strat = (j.get("strategy") or {}).get("settings") or {}
    rows = []
    totals = {"cpu_request_current": 0.0, "cpu_request_recommended": 0.0, "memory_request_current": 0.0, "memory_request_recommended": 0.0, "containers_with_both": 0}
    unknown_reasons: Counter = Counter()
    by_kind: Counter = Counter()
    for s in scans:
        o = s.get("object") or {}
        alloc = o.get("allocations") or {}
        rec = s.get("recommended") or {}
        cur_req, cur_lim = alloc.get("requests") or {}, alloc.get("limits") or {}
        rec_req, rec_lim = rec.get("requests") or {}, rec.get("limits") or {}
        kind, ns, name, cont = o.get("kind"), o.get("namespace"), o.get("name"), o.get("container")
        by_kind[kind] += 1
        row = {
            "target": f"{ns}/{str(kind).lower()}/{name}:{cont}",
            "kind": kind,
            "namespace": ns,
            "name": name,
            "container": cont,
            "severity": s.get("severity"),
            "cpu_request": _cores(_num(cur_req.get("cpu"))),
            "cpu_request_rec": _cores(_num((rec_req.get("cpu") or {}).get("value"))),
            "cpu_request_sev": (rec_req.get("cpu") or {}).get("severity"),
            "cpu_limit": _cores(_num(cur_lim.get("cpu"))),
            "cpu_limit_rec": _cores(_num((rec_lim.get("cpu") or {}).get("value"))),
            "cpu_limit_sev": (rec_lim.get("cpu") or {}).get("severity"),
            "memory_request_mb": _mb(_num(cur_req.get("memory"))),
            "memory_request_rec_mb": _mb(_num((rec_req.get("memory") or {}).get("value"))),
            "memory_request_sev": (rec_req.get("memory") or {}).get("severity"),
            "memory_limit_mb": _mb(_num(cur_lim.get("memory"))),
            "memory_limit_rec_mb": _mb(_num((rec_lim.get("memory") or {}).get("value"))),
            "memory_limit_sev": (rec_lim.get("memory") or {}).get("severity"),
            "info": {k: v for k, v in (rec.get("info") or {}).items() if v},
            "warnings": o.get("warnings") or [],
            "hpa": bool(o.get("hpa")),
            "pods_live": sum(1 for p in (o.get("pods") or []) if not p.get("deleted")),
        }
        # difference: positive = current is larger than recommended (over-provisioned), negative = recommendation is larger (under-provisioned)
        if row["cpu_request"] is not None and row["cpu_request_rec"] is not None:
            row["cpu_request_delta"] = round(row["cpu_request"] - row["cpu_request_rec"], 3)
            totals["cpu_request_current"] += row["cpu_request"]
            totals["cpu_request_recommended"] += row["cpu_request_rec"]
        if row["memory_request_mb"] is not None and row["memory_request_rec_mb"] is not None:
            row["memory_request_delta_mb"] = row["memory_request_mb"] - row["memory_request_rec_mb"]
            totals["memory_request_current"] += row["memory_request_mb"]
            totals["memory_request_recommended"] += row["memory_request_rec_mb"]
            totals["containers_with_both"] += 1
        # one human-readable line
        parts = []
        if row.get("cpu_request_delta") is not None:
            parts.append(f"CPU request {row['cpu_request']} → {row['cpu_request_rec']} cores")
        elif row["cpu_request_sev"] == "UNKNOWN":
            parts.append(f"CPU {row['info'].get('cpu') or 'no data'}")
        if row["cpu_limit_sev"] not in (None, "UNKNOWN", "OK", "GOOD"):
            parts.append(f"CPU limit {row['cpu_limit']} → {'none' if row['cpu_limit_rec'] is None else row['cpu_limit_rec']}")
        if row.get("memory_request_delta_mb") is not None:
            parts.append(f"memory request {row['memory_request_mb']} → {row['memory_request_rec_mb']} MB")
        if row["memory_limit_sev"] not in (None, "UNKNOWN", "OK", "GOOD") and row["memory_limit_rec_mb"] is not None:
            parts.append(f"memory limit {row['memory_limit_mb']} → {row['memory_limit_rec_mb']} MB")
        row["summary"] = ", ".join(parts) or "no recommendation"
        # kubegap verdict (KRR's severity treats "memory limit larger than recommended" as CRITICAL too, which is noise if used as-is. Measured on a real k3s: most of 19 CRITICALs were limit differences).
        # fail: memory request below the recommendation (max+15%) (under → node overcommit, OOM) / CPU request more than 0.2 cores above the recommendation / memory request more than 512MB above / CPU request below half the recommendation (under)
        # warn: smaller differences. Limit-only differences pass (the CPU limit removal advice goes only to the cpu_limit_remove_recommended list).
        level, reasons = None, []
        dc, dm = row.get("cpu_request_delta"), row.get("memory_request_delta_mb")
        if dm is not None and dm < 0:
            if row["memory_request_sev"] == "CRITICAL" or dm <= -256:
                level = "fail"
                reasons.append(f"memory request under by {-dm} MB")
            elif dm <= -64:
                level = level or "warn"
                reasons.append(f"memory request under by {-dm} MB")
        if dc is not None and dc > 0:
            if dc >= 0.2:
                level = "fail"
                reasons.append(f"CPU request over by {dc} cores")
            elif dc >= 0.1:
                level = level or "warn"
                reasons.append(f"CPU request over by {dc} cores")
        if dc is not None and dc < 0 and row["cpu_request"] and row["cpu_request_rec"] and row["cpu_request_rec"] >= row["cpu_request"] * 2 and -dc >= 0.1:
            level = level or "warn"
            reasons.append(f"CPU request under by {-dc} cores")
        if dm is not None and dm > 0:
            if dm >= 512:
                level = "fail"
                reasons.append(f"memory request over by {dm} MB")
            elif dm >= 256:
                level = level or "warn"
                reasons.append(f"memory request over by {dm} MB")
        row["kubegap_level"] = level
        row["kubegap_reason"] = ", ".join(reasons)
        for w in row["warnings"]:
            unknown_reasons[w] += 1
        rows.append(row)
    rows.sort(key=lambda r: (SEV_ORDER.get(r["severity"], 9), -abs(r.get("cpu_request_delta") or 0) - abs(r.get("memory_request_delta_mb") or 0) / 1024))
    over_cpu = sorted([r for r in rows if (r.get("cpu_request_delta") or 0) > 0.05], key=lambda r: -r["cpu_request_delta"])[:20]
    under_mem = sorted([r for r in rows if (r.get("memory_request_delta_mb") or 0) < -64], key=lambda r: r["memory_request_delta_mb"])[:20]
    over_mem = sorted([r for r in rows if (r.get("memory_request_delta_mb") or 0) > 256], key=lambda r: -r["memory_request_delta_mb"])[:20]
    limit_remove = [r["target"] for r in rows if r["cpu_limit"] is not None and r["cpu_limit_rec"] is None and r["cpu_limit_sev"] in ("WARNING", "CRITICAL")]
    totals = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in totals.items()}
    totals["cpu_request_saving_cores"] = round(totals["cpu_request_current"] - totals["cpu_request_recommended"], 2)
    totals["memory_request_saving_mb"] = round(totals["memory_request_current"] - totals["memory_request_recommended"])
    return {
        "present": True,
        "source": "tools/krr.json",
        "score": j.get("score"),
        "strategy": (j.get("strategy") or {}).get("name"),
        "history_hours": strat.get("history_duration"),
        "cpu_percentile": strat.get("cpu_percentile"),
        "memory_buffer_pct": strat.get("memory_buffer_percentage"),
        "scans": len(scans),
        "by_severity": dict(Counter(r["severity"] for r in rows)),
        "by_kind": dict(by_kind),
        "by_kubegap_level": dict(Counter(r["kubegap_level"] or "pass" for r in rows)),
        "unknown_reasons": dict(unknown_reasons),
        "errors": j.get("errors") or [],
        "cluster_summary": j.get("clusterSummary"),
        "totals": totals,
        "workloads": rows,
        "top_over_cpu": over_cpu,
        "top_over_memory": over_mem,
        "top_under_memory": under_mem,
        "cpu_limit_remove_recommended": limit_remove,
    }


def _metric_rows(snap: Path, qid: str) -> list[tuple[dict, float]]:
    m = load_json(snap / "metrics" / f"{qid}.json")
    out = []
    for s in (m or {}).get("result") or []:
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out.append((s.get("metric") or {}, float(s["value"][1])))
    return out


def analyze_p95(snap: Path, inv: dict | None) -> dict:
    """Group the 7-day p95 ratio metrics per workload and produce top lists (several pods are averaged)."""

    def by_workload(qid):
        acc: dict[str, list[float]] = defaultdict(list)
        for lab, v in _metric_rows(snap, qid):
            acc[f"{workload_of(lab.get('namespace', '') + '/' + lab.get('pod', ''))}:{lab.get('container', '')}"].append(v)
        return {k: round(sum(v) / len(v), 3) for k, v in acc.items()}

    cpu_req, cpu_lim = by_workload("cpu_request_p95_ratio_7d"), by_workload("cpu_limit_p95_ratio_7d")
    mem_req, mem_lim = by_workload("memory_request_p95_ratio_7d"), by_workload("memory_limit_p95_ratio_7d")
    available = any([cpu_req, cpu_lim, mem_req, mem_lim])
    if not available:
        return {"available": False, "note": "metrics/*_p95_*_7d.json missing (no Prometheus or not collected yet)"}

    def top(d, reverse, n=20):
        return [{"workload": k, "ratio": v} for k, v in sorted(d.items(), key=lambda kv: kv[1], reverse=reverse)[:n]]

    large = [{"workload": f"{workload_of(lab.get('namespace', '') + '/' + lab.get('pod', ''))}:{lab.get('container', '')}", "ratio_of_median_node": round(v, 2)} for lab, v in _metric_rows(snap, "large_request_containers")]
    return {
        "available": True,
        "window": "7d, 15m step, p95",
        "containers_measured": {"cpu_vs_request": len(cpu_req), "cpu_vs_limit": len(cpu_lim), "memory_vs_request": len(mem_req), "memory_vs_limit": len(mem_lim)},
        "cpu_overprovisioned_top": top({k: v for k, v in cpu_req.items() if v < 0.35}, False),
        "cpu_near_limit_top": top({k: v for k, v in cpu_lim.items() if v >= 0.75}, True),
        "memory_overprovisioned_top": top({k: v for k, v in mem_req.items() if v < 0.35}, False),
        "memory_near_limit_top": top({k: v for k, v in mem_lim.items() if v >= 0.8}, True),
        "large_requests": sorted(large, key=lambda r: -r["ratio_of_median_node"]),
        "node_cpu_p95": {lab.get("node"): round(v, 3) for lab, v in _metric_rows(snap, "node_cpu_usage_ratio_p95_7d")},
        "node_memory_p95": {lab.get("node"): round(v, 3) for lab, v in _metric_rows(snap, "node_memory_usage_ratio_p95_7d")},
    }


_XMX_RE = re.compile(r"-Xmx(\d+)([kKmMgG])?")
_RAMPCT_RE = re.compile(r"MaxRAMPercentage=(\d+(?:\.\d+)?)")
_JAVA_HINT_RE = re.compile(r"java|jvm|kafka|elasticsearch|opensearch|logstash|zookeeper|cassandra|keycloak|jenkins|sonarqube|spring|tomcat|jmx", re.IGNORECASE)
_SIDECAR_RE = re.compile(r"exporter|proxy|sidecar|istio|envoy|linkerd|reloader|agent|collector|fluent|vector|tailscale|oauth2|log|metrics|init", re.IGNORECASE)


def _parse_mem_mib(s) -> float | None:
    m = re.match(r"^(\d+(?:\.\d+)?)([KMGT]i?|[kKmMgG])?$", str(s or ""))
    if not m:
        return None
    n = float(m.group(1))
    u = (m.group(2) or "").lower()
    mult = {"": 1 / 1024**2, "k": 1 / 1024, "ki": 1 / 1024, "m": 1, "mi": 1, "g": 1024, "gi": 1024, "t": 1024**2, "ti": 1024**2}.get(u, 1)
    return round(n * mult, 1)


def analyze_containers(snap: Path, inv: dict | None) -> dict:
    """Sidecar and JVM resource misconfiguration (Airbnb 2019, Exponea 2019): containers whose JVM heap (-Xmx, MaxRAMPercentage) is large relative to the memory limit, and workloads where sidecars take more than half of the requests."""
    prod = set(((inv or {}).get("namespaces") or {}).get("prod_like") or [])
    jvm, sidecars = [], []
    for kind in ("deployments", "statefulsets", "daemonsets"):
        for o in (load_json(snap / "objects" / f"{kind}.json") or {}).get("items") or []:
            md = o["metadata"]
            ns = md["namespace"]
            tpl = ((o.get("spec") or {}).get("template") or {}).get("spec") or {}
            conts = tpl.get("containers") or []
            key = f"{ns}/{kind[:-1]}/{md['name']}"
            reqs = []
            for c in conts:
                txt = " ".join([f"{e.get('name', '')}={e.get('value', '')}" for e in (c.get("env") or [])] + [str(a) for a in (c.get("args") or [])] + [str(a) for a in (c.get("command") or [])])
                lim = _parse_mem_mib(((c.get("resources") or {}).get("limits") or {}).get("memory"))
                req = _parse_mem_mib(((c.get("resources") or {}).get("requests") or {}).get("memory")) or 0.0
                reqs.append((c.get("name"), req))
                mx = _XMX_RE.search(txt)
                pct = _RAMPCT_RE.search(txt)
                # Do not infer a JVM from the image or container name — a prepull DaemonSet that only runs sleep on a spring image was flagged as "heap not set".
                # Only when command/args run something java-like, a JAVA_OPTS/JAVA_TOOL_OPTIONS/JDK_JAVA_OPTIONS-style env var exists, or -Xmx/MaxRAMPercentage is visible. Excluded when command is sleep, tail or sh -c sleep
                has_cmd = bool(c.get("command") or c.get("args"))
                cmd_txt = " ".join([str(a) for a in (c.get("command") or [])] + [str(a) for a in (c.get("args") or [])])
                holder = bool(re.search(r"\b(sleep|tail -f|pause)\b", cmd_txt)) and not re.search(r"\bjava\b", cmd_txt)
                env_names = {str(e.get("name", "")) for e in (c.get("env") or [])}
                java_env = bool(env_names & {"JAVA_OPTS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "JVM_OPTS", "CATALINA_OPTS", "ES_JAVA_OPTS", "KAFKA_HEAP_OPTS", "KAFKA_OPTS", "JAVA_HOME"})
                javaish = (not holder) and (bool(re.search(r"\bjava\b", cmd_txt)) or java_env or bool(mx or pct) or (not has_cmd and bool(_JAVA_HINT_RE.search(c.get("image", "")))))
                if not javaish:
                    continue
                xmx = None
                if mx:
                    xmx = _parse_mem_mib(mx.group(1) + (mx.group(2) or "m"))
                ram_pct = float(pct.group(1)) if pct else None
                heap_ratio = round(xmx / lim, 2) if (xmx and lim) else (round(ram_pct / 100, 2) if ram_pct else None)
                jvm.append(
                    {
                        "workload": key,
                        "namespace": ns,
                        "container": c.get("name"),
                        "prod": ns in prod,
                        "image": (c.get("image") or "").split("/")[-1][:60],
                        "xmx_mib": xmx,
                        "max_ram_percentage": ram_pct,
                        "limit_mib": lim,
                        "heap_ratio": heap_ratio,
                        "heap_unset": xmx is None and ram_pct is None,
                        "no_limit": lim is None,
                    }
                )
            if len(conts) >= 2:
                total = sum(r for _, r in reqs)
                main = max(reqs, key=lambda x: x[1])[0] if total else conts[0].get("name")
                side = [n for n, _ in reqs if n != main]
                side_req = sum(r for n, r in reqs if n != main)
                sidecars.append(
                    {
                        "workload": key,
                        "namespace": ns,
                        "prod": ns in prod,
                        "main": main,
                        "sidecars": side,
                        "sidecar_request_mib": round(side_req),
                        "total_request_mib": round(total),
                        "sidecar_share": round(side_req / total, 2) if total else None,
                        "sidecar_like_names": all(_SIDECAR_RE.search(n or "") for n in side),
                    }
                )
    return {
        "jvm": sorted(jvm, key=lambda r: -(r["heap_ratio"] or 0)),
        "sidecars": sorted(sidecars, key=lambda r: -(r["sidecar_share"] or 0)),
        "jvm_heap_over": [r["workload"] + ":" + r["container"] for r in jvm if (r["heap_ratio"] or 0) >= 0.85],
        "jvm_heap_unset": [r["workload"] + ":" + r["container"] for r in jvm if r["heap_unset"] and not r["no_limit"]],
        "note": "JVM heap considers only -Xmx or -XX:MaxRAMPercentage (defaults inside the image are unknown). Sidecar share is based on requests; the container with the largest request is treated as the main one",
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    return {"krr": analyze_krr(snap), "p95": analyze_p95(snap, inv), "containers": analyze_containers(snap, inv)}

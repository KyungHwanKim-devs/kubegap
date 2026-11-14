"""Log summary. Called by summarize to build the logs section of summary.json.

Inputs:
- logs/pods/<component>/*.log : component pod logs fetched by the core `component-logs` step with kubectl logs (24 hours, 1500 lines per pod, --prefix --timestamps)
- logs/node/<node>/kubelet-24h.log, containerd-24h.log, ipamd-24h.log (EKS SSM), k3s-errors-24h.log (k3s)
- loki/*.json|txt : what the loki collector fetched from the Loki HTTP API (1-hour window label values, lines per namespace, error lines, JSON lines, /metrics)
- metrics/<id>.json : promtail, loki and fluent-bit metrics
- objects/pods.json : collection gap cross-check (pods Running for over an hour that have no pod label in Loki)

Files are scanned once: signatures choose their targets by file path (glob), each line is pre-filtered with a combined "any pattern" regex, then individual signatures are counted.
Error lines matching no signature are normalized and the top 30 patterns are passed on as unclassified_errors (candidates for new signatures).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
from collections import Counter
from pathlib import Path

from ..foundations import paths, units
from ..foundations import podmetrics as _pm
from ..foundations.logscan import (  # noqa: F401  (the names the tests and the Loki half below use)
    BOOT_WINDOW_S,
    ERROR_RE,
    ISO_RE,
    ISO_TZ_RE,
    KLOG_TS_RE,
    MAX_FILE_BYTES,
    NOT_ERROR_RE,
    PREFIX_RE,
    TS_ANY_RE,
    _parse_iso,
    _strip_prefix,
    _ts_of,
    _utc_str,
    any_regex,
    match_line,
    merge,
    normalize_unclassified,
    scan_texts,
)
from ..foundations.promtext import parse as _parse_prom
from ..foundations.signatures import Signature
from ..foundations.signatures import load as load_signatures
from ..foundations.snapshot import COMPONENT_LOGS_DIR, component_logs_aggregate, load_json, metric_result, metric_rows, metric_sum, parse_ts, taken_at
from ..foundations.workload import workload_of


def _node_boot_windows(snap: Path) -> dict[str, _dt.datetime]:
    """Per node, the 'end of boot window' time = max(node creation time, node-exporter node_boot_time) + BOOT_WINDOW_S. kubelet/containerd lines right after a reboot are filtered too."""
    out: dict[str, _dt.datetime] = {}
    nodes = (load_json(snap / "objects" / "nodes.json") or {}).get("items") or []
    ip_to_node = {}
    for n in nodes:
        ts = _parse_iso((n.get("metadata") or {}).get("creationTimestamp"))
        name = (n.get("metadata") or {}).get("name")
        if ts and name:
            out[name] = ts + _dt.timedelta(seconds=BOOT_WINDOW_S)
        for a in (n.get("status") or {}).get("addresses") or []:
            if a.get("type") == "InternalIP":
                ip_to_node[a.get("address")] = name
    for lab, v in metric_rows(snap, "node_boot_time"):
        inst = lab.get("instance", "").split(":")[0]
        name = ip_to_node.get(inst)
        bt = _dt.datetime.fromtimestamp(v, tz=_dt.UTC) + _dt.timedelta(seconds=BOOT_WINDOW_S)
        if name and (name not in out or bt > out[name]):
            out[name] = bt
    return out


def scan(snap: Path, sigs: list[Signature], *, keep_lines: bool = True) -> dict:
    """Count the node log files under logs/ (everything but logs/pods/, whose lines were counted at collection and never written)."""
    ldir = snap / "logs"
    files = sorted(p for p in ldir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt") and p.stat().st_size > 0 and p.name != "os.txt") if ldir.is_dir() else []

    def sources():
        for f in files:
            try:
                yield str(f.relative_to(snap)), f.read_bytes()[-MAX_FILE_BYTES:].decode("utf-8", "replace")
            except OSError:
                continue

    return scan_texts(sources(), sigs, taken=taken_at(load_json(snap / "inventory.json")), boot_until=_node_boot_windows(snap), keep_lines=keep_lines)


# ---------- Loki ----------


def _loki_json(snap: Path, name: str):
    return load_json(snap / "loki" / f"{name}.json")


def _vector(d) -> dict[str, float]:
    out = {}
    for r in ((d or {}).get("data") or {}).get("result", []) or []:
        ns = (r.get("metric") or {}).get("namespace") or "(none)"
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out[ns] = float(r["value"][1])
    return out


def analyze_loki(snap: Path, inv: dict) -> dict:
    store = (inv.get("stores") or {}).get("loki") or {}
    ldir = snap / "loki"
    # present = whether detection (components) found Loki. setup leaves stores.loki as {ok: false, note: service not found} even without Loki, so judging by that
    # would make a small k3s cluster without Loki present=true — a mismatch caught by selftest's comparison against real snapshot keys.
    detected = "loki" in (inv.get("components_present") or []) or bool(((inv.get("components") or {}).get("loki") or {}).get("present"))
    if not store.get("ok") and not ldir.is_dir():
        return {"present": detected, "ok": False, "note": store.get("error") or store.get("note") or "no Loki (log store is not Loki or not installed)"}
    out: dict = {"present": True, "ok": bool(store.get("ok")), "version": store.get("version"), "retention": store.get("retention")}
    ready = ldir / "ready.txt"
    out["ready"] = ready.read_text(encoding="utf-8", errors="replace").strip() == "ready" if ready.is_file() else None
    vol, err, js = _vector(_loki_json(snap, "volume_1h")), _vector(_loki_json(snap, "errors_1h")), _vector(_loki_json(snap, "json_1h"))
    rows = []
    for ns in sorted(set(vol) | set(err)):
        v = vol.get(ns, 0.0)
        rows.append(
            {
                "namespace": ns,
                "lines_1h": int(v),
                "error_lines_1h": int(err.get(ns, 0.0)),
                "error_ratio": round(err.get(ns, 0.0) / v, 3) if v else None,
                "json_lines_1h": int(js.get(ns, 0.0)) if js else None,
                "json_ratio": (round(js.get(ns, 0.0) / v, 3) if v else None) if js else None,
            }
        )
    rows.sort(key=lambda r: -r["lines_1h"])
    out["namespaces_1h"] = rows
    out["lines_1h_total"] = sum(r["lines_1h"] for r in rows)
    # log volume surge: compare the 1-hour volume per namespace with the previous snapshot. 3x or more growth, or 1,000+ lines dropping to 0, gives surge/vanished
    prev = paths.previous_snapshot(snap)
    prev_vol = _vector(_loki_json(prev, "volume_1h")) if prev else {}
    changes = []
    for ns in sorted(set(vol) | set(prev_vol)):
        cur, before = vol.get(ns, 0.0), prev_vol.get(ns, 0.0)
        ratio = round(cur / before, 2) if before else None
        kind = None
        if before >= 1000 and cur == 0:
            kind = "vanished"
        elif cur >= 5000 and (before == 0 or (ratio is not None and ratio >= 3)):
            kind = "surge"
        if kind:
            changes.append({"namespace": ns, "lines_1h": int(cur), "prev_lines_1h": int(before), "ratio": ratio, "kind": kind})
    out["volume_change"] = {
        "prev_snapshot": prev.name if prev else None,
        "compared_namespaces": len(set(vol) | set(prev_vol)),
        "changes": changes,
        "surge": [c["namespace"] for c in changes if c["kind"] == "surge"],
        "vanished": [c["namespace"] for c in changes if c["kind"] == "vanished"],
    }
    out["window_note"] = "1-hour window. A 24-hour count_over_time has previously OOMKilled a single-binary Loki (2.6, small memory limit), so it is not used"
    # collection gaps: pods Running for over an hour that are absent from Loki's pod label values
    pods_lbl = set((_loki_json(snap, "label_pod_1h") or {}).get("data") or [])
    ns_lbl = set((_loki_json(snap, "label_namespace_1h") or {}).get("data") or [])
    out["pods_with_logs_1h"] = len(pods_lbl)
    out["namespaces_with_logs_1h"] = len(ns_lbl)
    pods = load_json(snap / "objects" / "pods.json") or {}
    now = taken_at(inv)
    missing: list[dict] = []
    running_old = 0
    by_node_total: Counter = Counter()
    by_node_missing: Counter = Counter()
    by_ns_missing: Counter = Counter()
    if pods_lbl:
        for p in pods.get("items", []):
            st = p.get("status") or {}
            if st.get("phase") != "Running":
                continue
            start = st.get("startTime")
            started = parse_ts(start)
            age_h = (now - started).total_seconds() / 3600 if started else 0
            if age_h < 1:
                continue
            running_old += 1
            node = (p.get("spec") or {}).get("nodeName")
            by_node_total[node] += 1
            name, ns = p["metadata"]["name"], p["metadata"]["namespace"]
            if name not in pods_lbl:
                by_node_missing[node] += 1
                by_ns_missing[ns] += 1
                missing.append({"namespace": ns, "pod": name, "workload": workload_of(f"{ns}/{name}"), "node": node, "age_h": round(age_h, 1)})
    nodes_all_missing = [n for n, t in by_node_total.items() if t >= 2 and by_node_missing.get(n, 0) == t]
    out["coverage"] = {
        "running_pods_over_1h": running_old,
        "pods_without_logs_1h": len(missing),
        "gap_ratio": round(len(missing) / running_old, 3) if running_old else None,
        "nodes_all_missing": nodes_all_missing,
        "by_namespace_missing": dict(by_ns_missing.most_common()),
        "pods_without_logs": sorted(missing, key=lambda m: (m["namespace"], m["pod"])),
        "note": "A pod that wrote no log lines in an hour may be fine (idle). If a whole node is missing (nodes_all_missing), that node's promtail is dead; if a whole namespace is missing, promtail's exclusion config is the cause",
        "available": bool(pods_lbl),
    }
    # Loki's own metrics (/metrics scraped once: counters accumulate since process start)
    mtxt = ldir / "metrics.txt"
    if mtxt.is_file():
        # Loki names go through collectors/loki/pod-metrics.yaml (per-version spellings); the process_* names are client_golang's and have one spelling
        m = _parse_prom(mtxt.read_text(encoding="utf-8", errors="replace"))
        disc: Counter = Counter()
        for labels, v in _pm.labeled(m, "loki", "discarded_samples"):
            disc[labels.get("reason", "?")] += v
        err5xx = sum(v for labels, v in _pm.labeled(m, "loki", "request_duration_count") if str(labels.get("status_code", "")).startswith("5"))
        start = m["single"].get("process_start_time_seconds")
        out["self_metrics"] = {
            "discarded_samples_since_start": {k: int(v) for k, v in disc.items() if v},
            "streams_in_memory": int(_pm.single(m, "loki", "memory_streams", 0)),
            "panics": int(_pm.single(m, "loki", "panics", 0)),
            "lines_received_since_start": int(_pm.single(m, "loki", "lines_received", 0)),
            "requests_5xx_since_start": int(err5xx),
            "rss_mb": round((m["single"].get("process_resident_memory_bytes") or 0) / 1024**2),
            "process_uptime_h": round((now.timestamp() - start) / 3600, 1) if start else None,
        }
    # Loki pod restarts and last termination reason (OOMKilled is common)
    rs = []
    for p in pods.get("items", []):
        if p["metadata"]["namespace"] == (store.get("service") or {}).get("namespace") and "loki" in p["metadata"]["name"] and "promtail" not in p["metadata"]["name"]:
            for cs in (p.get("status") or {}).get("containerStatuses", []) or []:
                term = (cs.get("lastState") or {}).get("terminated") or {}
                rs.append({"pod": p["metadata"]["name"], "container": cs.get("name"), "restarts": cs.get("restartCount", 0), "last_reason": term.get("reason"), "last_finished": term.get("finishedAt")})
    out["pods"] = rs
    out["oomkilled"] = any(r.get("last_reason") == "OOMKilled" for r in rs)
    # storage kind (emptyDir loses logs on restart)
    svc = store.get("service") or {}
    for kind in ("statefulsets", "deployments"):
        for o in (load_json(snap / "objects" / f"{kind}.json") or {}).get("items", []):
            if o["metadata"]["namespace"] == svc.get("namespace") and o["metadata"]["name"] == svc.get("name"):
                vols = (o.get("spec", {}).get("template", {}).get("spec", {}) or {}).get("volumes", []) or []
                out["storage"] = {
                    "kind": kind[:-1],
                    "volumes": {v["name"]: next((k for k in v if k != "name"), None) for v in vols},
                    "volume_claim_templates": len(o.get("spec", {}).get("volumeClaimTemplates") or []),
                    "replicas": o.get("spec", {}).get("replicas"),
                }
                out["storage"]["emptydir_data"] = any(k == "emptyDir" and n in ("storage", "data", "loki-data") for n, k in out["storage"]["volumes"].items()) and not out["storage"]["volume_claim_templates"]
    return out


def analyze_agents(snap: Path, inv: dict) -> dict:
    comps = inv.get("components_present") or []
    out: dict = {}
    if "promtail" in comps:
        scraped_p = any(metric_result(snap, q) for q in ("promtail_dropped_1h", "promtail_targets_active", "promtail_request_errors_1h"))
        out["promtail"] = {
            "dropped_entries_1h": metric_sum(snap, "promtail_dropped_1h"),
            "targets_active": metric_sum(snap, "promtail_targets_active"),
            "request_errors_1h": metric_sum(snap, "promtail_request_errors_1h"),
            "metrics_scraped": scraped_p,
            "note": None if scraped_p else "promtail metrics are not in Prometheus (no ServiceMonitor). Dropped lines 0 means not measured",
        }
    if "fluent-bit" in comps or "fluentd" in comps:
        scraped = any(metric_result(snap, q) for q in ("fluentbit_output_errors_1h", "fluentbit_retries_failed_1h", "fluentbit_input_records_1h", "fluentbit_dropped_records_1h"))
        out["fluent-bit"] = {
            "output_errors_1h": metric_sum(snap, "fluentbit_output_errors_1h"),
            "retries_failed_1h": metric_sum(snap, "fluentbit_retries_failed_1h"),
            "records_in_1h": metric_sum(snap, "fluentbit_input_records_1h"),
            "dropped_records_1h": metric_sum(snap, "fluentbit_dropped_records_1h"),
            "metrics_scraped": scraped,  # False means fluent-bit exists but Prometheus does not scrape it, so the numbers above are all 'uncollected values that look like 0'
            "note": None if scraped else "fluent-bit metrics are not in Prometheus (no ServiceMonitor/PodMonitor). Output errors and drops 0 mean not measured",
        }
    if "loki" in comps:
        out["loki_metrics"] = {"discarded_1h": metric_sum(snap, "loki_discarded_1h"), "requests_5xx_1h": metric_sum(snap, "loki_5xx_1h")}
    return out


def scan_section(snap: Path, sigs: list[Signature]) -> dict:
    """The part of the logs section that comes from log lines: the component logs, counted while they were collected (logs/pods/AGGREGATED.json; no
    line of them is a file), joined with the node logs of a full run, counted here from their files. With no aggregate (the step did not run) only
    the node logs are counted and `component_logs` says so."""
    node = scan(snap, sigs, keep_lines=units.collected(snap, "component-log-samples"))
    agg = component_logs_aggregate(snap) or {}
    pods = agg.get("log_scan") if isinstance(agg.get("log_scan"), dict) else None
    res = merge([pods, node], sigs) if pods else node
    ldir = snap / "logs"
    node_files = [str(f.relative_to(snap)) for f in sorted(ldir.rglob("*")) if f.is_file() and COMPONENT_LOGS_DIR not in f.relative_to(snap).parents] if ldir.is_dir() else []
    return {
        "component_logs": "counted while they were collected; no line is stored" if pods else "not counted: the component-logs step left no logs/pods/AGGREGATED.json",
        "components_with_logs": (pods or {}).get("components_with_logs") or [],
        "component_log_lines": (pods or {}).get("lines_by_file") or {},
        "component_logs_capped": agg.get("capped") or [],
        "files": node_files,
        **res,
        "scan_signatures_version": (pods or {}).get("scan_signatures_version") or paths.signatures_version(),
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    sigs, errors = load_signatures(inv.get("collectors_enabled") or ["core"])
    res = scan_section(snap, sigs)
    return {
        "source": "logs/ (signature matches) + loki/ + metrics/ + objects/pods.json",
        "signatures_version": paths.signatures_version(),
        "catalog_size": len(sigs),
        "catalog_errors": errors,
        **res,
        "loki": analyze_loki(snap, inv),
        "agents": analyze_agents(snap, inv),
    }

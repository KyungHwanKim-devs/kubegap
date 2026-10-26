"""Log summary. Called by summarize to build the logs section of summary.json.

Inputs:
- logs/pods/<component>/*.log : component pod logs fetched by the core `component-logs` step with kubectl logs (24 hours, 1500 lines per pod, --prefix --timestamps)
- logs/node/<node>/kubelet-24h.log, containerd-24h.log (EKS SSM), k3s-errors-24h.log (k3s)
- loki/*.json|txt : what the loki collector fetched from the Loki HTTP API (1-hour window label values, lines per namespace, error lines, JSON lines, /metrics)
- metrics/<id>.json : promtail, loki and fluent-bit metrics
- objects/pods.json : collection gap cross-check (pods Running for over an hour that have no pod label in Loki)

Files are scanned once: signatures choose their targets by file path (glob), each line is pre-filtered with a combined "any pattern" regex, then individual signatures are counted.
Error lines matching no signature are normalized and the top 30 patterns are passed on as unclassified_errors (candidates for new signatures).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import paths
from .controlplane import _normalize_msg, workload_of
from .signatures import Signature
from .signatures import load as load_signatures
from .snapshot import load_json

ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
KLOG_TS_RE = re.compile(r"\b[IWEF](\d{2})(\d{2}) (\d{2}:\d{2}:\d{2})")
PREFIX_RE = re.compile(r"^\[pod/([^/\]]+)/([^\]]+)\] ")
ERROR_RE = re.compile(r'(?i)\b(error|fatal|panic|exception|failed|failure)\b|"level":"(error|fatal)"|level=(error|fatal)|^\[?[^\]]*\]? ?\S* ?E\d{4} ')
NOT_ERROR_RE = re.compile(
    r"level=info|\"level\":\"info\"|level=debug|\"level\":\"debug\"|\"severity\":\"(info|debug|notice)\"|\"level\":\"(warn|warning)\"|errors=0|error=nil|error=<nil>|\"error\":\"\"|error: null|RegistrationStatus", re.IGNORECASE
)
# JSON logs whose level/severity field is info are not errors even when the body contains "failed" (seen: actions-runner-controller "severity":"info" lines and ebs-csi NotifyRegistrationStatus were caught as unclassified errors).
BOOT_WINDOW_S = 300  # 300 seconds after node creation or reboot. Was 120, but after a small k3s cluster node reboot the first kubelet line came 140 seconds later, so it was raised. kubelet/containerd lines within this window after node creation are boot ordering (PLEG, network not ready before CNI init) and are excluded from signatures.
ISO_TZ_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?")
MAX_FILE_BYTES = 30 * 1024 * 1024


def _ts_of(line: str) -> str | None:
    m = ISO_RE.search(line)
    if m:
        return m.group(1)
    m = KLOG_TS_RE.search(line)
    if m:
        y = _dt.date.today().year
        return f"{y}-{m.group(1)}-{m.group(2)}T{m.group(3)}"
    return None


def _parse_iso(s: str | None) -> _dt.datetime | None:
    if not s:
        return None
    m = ISO_TZ_RE.search(s)
    if not m:
        return None
    try:
        base = _dt.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    tz = m.group(2)
    if not tz or tz == "Z":
        return base.replace(tzinfo=_dt.UTC)
    sign = 1 if tz[0] == "+" else -1
    hh, mm = int(tz[1:3]), int(tz[-2:])
    return base.replace(tzinfo=_dt.timezone(sign * _dt.timedelta(hours=hh, minutes=mm)))


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
    for r in (load_json(snap / "metrics" / "node_boot_time.json") or {}).get("result") or []:
        inst = (r.get("metric") or {}).get("instance", "").split(":")[0]
        name = ip_to_node.get(inst)
        try:
            bt = _dt.datetime.fromtimestamp(float(r["value"][1]), tz=_dt.UTC) + _dt.timedelta(seconds=BOOT_WINDOW_S)
        except (KeyError, ValueError, TypeError, IndexError):
            continue
        if name and (name not in out or bt > out[name]):
            out[name] = bt
    return out


def _strip_prefix(line: str) -> tuple[str, str | None]:
    """'[pod/x/y] 2026-..Z body' → (body, 'x'). Also strips the timestamp."""
    pod = None
    m = PREFIX_RE.match(line)
    if m:
        pod = m.group(1)
        line = line[m.end() :]
    line = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\s*", "", line, count=1)
    line = re.sub(r"^\S+ \S+\[\d+\]: ", "", line)  # journalctl short-iso: '<host> <unit>[<pid>]: ' (the time was stripped above)
    return line.strip(), pod


def scan(snap: Path, sigs: list[Signature]) -> dict:
    """Scan the text logs under logs/ once and produce signature matches and unclassified errors."""
    ldir = snap / "logs"
    files = sorted(p for p in ldir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt") and p.stat().st_size > 0 and p.name != "os.txt") if ldir.is_dir() else []
    hits: dict[str, dict] = {s.id: {"count": 0, "first": None, "last": None, "files": Counter(), "samples": []} for s in sigs}
    unclassified: Counter = Counter()
    uncl_sample: dict[str, str] = {}
    uncl_files: dict[str, Counter] = defaultdict(Counter)
    lines_total = 0
    error_lines = 0
    scanned: list[str] = []
    boot_until = _node_boot_windows(snap)
    boot_skipped: Counter = Counter()
    # klog lines in the k3s journal ("E1025 13:23:38") are node-local time without a tz. Interpret them once more with the snapshot's taken_at offset (operator local = small k3s cluster node local) to compare against the boot window
    local_tz = None
    try:
        taken = ((load_json(snap / "inventory.json") or {}).get("taken_at")) or ""
        m_tz = re.search(r"([+-]\d{2}):?(\d{2})$", taken)
        if m_tz:
            local_tz = _dt.timezone((1 if m_tz.group(0)[0] == "+" else -1) * _dt.timedelta(hours=int(m_tz.group(1)[1:]), minutes=int(m_tz.group(2))))
    except (ValueError, TypeError):
        local_tz = None
    for f in files:
        rel = str(f.relative_to(snap))
        applicable = [s for s in sigs if s.applies_to(rel)]
        if not applicable:
            continue
        scanned.append(rel)
        any_re = re.compile("|".join(f"(?:{s.pattern})" for s in applicable))
        parts = rel.split("/")
        component = parts[2] if rel.startswith("logs/pods/") and len(parts) > 3 else ("node:" + parts[2] if rel.startswith("logs/node/") and len(parts) > 3 else rel)
        node_boot_until = boot_until.get(parts[2]) if rel.startswith("logs/node/") and len(parts) > 3 else None
        try:
            data = f.read_bytes()[-MAX_FILE_BYTES:].decode("utf-8", "replace")
        except OSError:
            continue
        for line in data.splitlines():
            if not line.strip():
                continue
            lines_total += 1
            matched = False
            if any_re.search(line):
                if node_boot_until is not None:
                    ts_txt = _ts_of(line)
                    lt = _parse_iso(ts_txt)
                    if lt is not None and local_tz is not None and not (ISO_RE.search(line)) and KLOG_TS_RE.search(line):
                        lt_local = lt.replace(tzinfo=local_tz)
                        lt = min(lt, lt_local, key=lambda t: abs((t - node_boot_until).total_seconds()))  # whichever interpretation is closer to the boot time
                    if lt is not None and lt <= node_boot_until:
                        # node log inside the boot window. Not counted, but marked "matched" so it does not become an unclassified error either.
                        for s in applicable:
                            if s.regex.search(line):
                                boot_skipped[s.id] += 1
                                matched = True
                        if matched:
                            continue
                component_matched = any(s.regex.search(line) for s in applicable if s.component != "any")
                for s in applicable:
                    if s.component == "any" and component_matched:
                        continue  # a line consumed by a component signature is not counted again under common.* (seen: metallb.speaker-error and common.context-deadline double-counted 533 times)
                    if s.regex.search(line):
                        matched = True
                        h = hits[s.id]
                        h["count"] += 1
                        h["files"][rel] += 1
                        ts = _ts_of(line)
                        if ts:
                            h["first"] = min(h["first"], ts) if h["first"] else ts
                            h["last"] = max(h["last"], ts) if h["last"] else ts
                        if len(h["samples"]) < 5:
                            h["samples"].append(line[:240])
            if not matched and ERROR_RE.search(line) and not NOT_ERROR_RE.search(line):
                error_lines += 1
                body, _pod = _strip_prefix(line)
                body = re.sub(r'"(ts|time|start time|timestamp|end time)":\s*"[^"]*"', r'"\1":"<ts>"', body)  # time fields in JSON logs
                body = re.sub(r"\[\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\]", "[<ts>]", body)  # fluent-bit [2026/10/25 00:05:48]
                key = f"{component} | {_normalize_msg(body)[:140]}"
                unclassified[key] += 1
                uncl_files[key][rel] += 1
                uncl_sample.setdefault(key, line[:240])
    by_id = {s.id: s for s in sigs}
    sig_rows = []
    for sid, h in hits.items():
        if h["count"] == 0:
            continue
        s = by_id[sid]
        targets = len(h["files"])  # number of distinct pod/node files. Repetition from a single target is warn, not fail (seen: one ExternalSecret repeating produced fail/high)
        sig_rows.append(
            {
                **s.public(),
                "count": h["count"],
                "first": h["first"],
                "last": h["last"],
                "files": dict(h["files"].most_common(6)),
                "targets": targets,
                "samples": h["samples"],
                "status": "fail" if (h["count"] >= s.fail_at and targets >= 2) else ("warn" if h["count"] >= s.warn_at else "info"),
            }
        )
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sig_rows.sort(key=lambda r: (order.get(r["severity"], 9), -r["count"]))
    uncl_rows = [{"pattern": k, "count": c, "files": dict(uncl_files[k].most_common(3)), "sample": uncl_sample.get(k)} for k, c in unclassified.most_common(30)]
    return {
        "files_scanned": scanned,
        "lines_scanned": lines_total,
        "error_lines_unclassified": error_lines,
        "signatures": sig_rows,
        "unclassified_errors": uncl_rows,
        "boot_window_skipped": dict(boot_skipped),
        "boot_window_seconds": BOOT_WINDOW_S,
    }


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


def _parse_prom_text(text: str, names: set[str]) -> dict[str, list[tuple[dict, float]]]:
    out: dict[str, list] = defaultdict(list)
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)", line)
        if not m or m.group(1) not in names:
            continue
        labels = dict(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', m.group(2) or ""))
        with contextlib.suppress(ValueError):
            out[m.group(1)].append((labels, float(m.group(3))))
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
    taken = inv.get("taken_at")
    try:
        now = _dt.datetime.fromisoformat(taken) if taken else _dt.datetime.now().astimezone()
    except ValueError:
        now = _dt.datetime.now().astimezone()
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
            try:
                age_h = (now - _dt.datetime.fromisoformat(start)).total_seconds() / 3600 if start else 0
            except ValueError:
                age_h = 0
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
        "by_namespace_missing": dict(by_ns_missing.most_common(15)),
        "pods_without_logs": sorted(missing, key=lambda m: (m["namespace"], m["pod"]))[:60],
        "note": "A pod that wrote no log lines in an hour may be fine (idle). If a whole node is missing (nodes_all_missing), that node's promtail is dead; if a whole namespace is missing, promtail's exclusion config is the cause",
        "available": bool(pods_lbl),
    }
    # Loki's own metrics (/metrics scraped once: counters accumulate since process start)
    mtxt = ldir / "metrics.txt"
    if mtxt.is_file():
        names = {
            "loki_discarded_samples_total",
            "loki_ingester_memory_streams",
            "loki_panic_total",
            "loki_distributor_lines_received_total",
            "loki_ingester_chunks_flushed_total",
            "loki_ingester_chunks_stored_total",
            "process_resident_memory_bytes",
            "process_start_time_seconds",
            "loki_request_duration_seconds_count",
        }
        m = _parse_prom_text(mtxt.read_text(encoding="utf-8", errors="replace"), names)
        disc: Counter = Counter()
        for labels, v in m.get("loki_discarded_samples_total", []):
            disc[labels.get("reason", "?")] += v
        err5xx = sum(v for labels, v in m.get("loki_request_duration_seconds_count", []) if str(labels.get("status_code", "")).startswith("5"))
        start = next((v for _, v in m.get("process_start_time_seconds", [])), None)
        out["self_metrics"] = {
            "discarded_samples_since_start": {k: int(v) for k, v in disc.items() if v},
            "streams_in_memory": int(sum(v for _, v in m.get("loki_ingester_memory_streams", []))),
            "panics": int(sum(v for _, v in m.get("loki_panic_total", []))),
            "lines_received_since_start": int(sum(v for _, v in m.get("loki_distributor_lines_received_total", []))),
            "requests_5xx_since_start": int(err5xx),
            "rss_mb": round(sum(v for _, v in m.get("process_resident_memory_bytes", [])) / 1024**2),
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


def _metric_sum(snap: Path, qid: str) -> float | None:
    d = load_json(snap / "metrics" / f"{qid}.json")
    if not d or not d.get("ok") or not d.get("result"):
        return None  # 0 series = that metric is not scraped (collector metrics not exposed). Distinct from 0
    tot = 0.0
    for s in d.get("result", []) or []:
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            tot += float(s["value"][1])
    return tot


def analyze_agents(snap: Path, inv: dict) -> dict:
    comps = inv.get("components_present") or []
    out: dict = {}
    if "promtail" in comps:
        scraped_p = any(((load_json(snap / "metrics" / f"{q}.json") or {}).get("result") or []) for q in ("promtail_dropped_1h", "promtail_targets_active", "promtail_request_errors_1h"))
        out["promtail"] = {
            "dropped_entries_1h": _metric_sum(snap, "promtail_dropped_1h"),
            "targets_active": _metric_sum(snap, "promtail_targets_active"),
            "request_errors_1h": _metric_sum(snap, "promtail_request_errors_1h"),
            "metrics_scraped": scraped_p,
            "note": None if scraped_p else "promtail metrics are not in Prometheus (no ServiceMonitor). Dropped lines 0 means not measured",
        }
    if "fluent-bit" in comps or "fluentd" in comps:
        scraped = any(((load_json(snap / "metrics" / f"{q}.json") or {}).get("result") or []) for q in ("fluentbit_output_errors_1h", "fluentbit_retries_failed_1h", "fluentbit_input_records_1h", "fluentbit_dropped_records_1h"))
        out["fluent-bit"] = {
            "output_errors_1h": _metric_sum(snap, "fluentbit_output_errors_1h"),
            "retries_failed_1h": _metric_sum(snap, "fluentbit_retries_failed_1h"),
            "records_in_1h": _metric_sum(snap, "fluentbit_input_records_1h"),
            "dropped_records_1h": _metric_sum(snap, "fluentbit_dropped_records_1h"),
            "metrics_scraped": scraped,  # False means fluent-bit exists but Prometheus does not scrape it, so the numbers above are all 'uncollected values that look like 0'
            "note": None if scraped else "fluent-bit metrics are not in Prometheus (no ServiceMonitor/PodMonitor). Output errors and drops 0 mean not measured",
        }
    if "loki" in comps:
        out["loki_metrics"] = {"discarded_1h": _metric_sum(snap, "loki_discarded_1h"), "requests_5xx_1h": _metric_sum(snap, "loki_5xx_1h")}
    return out


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    sigs, errors = load_signatures(inv.get("collectors_enabled") or ["core"])
    res = scan(snap, sigs)
    ldir = snap / "logs"
    files = [str(f.relative_to(snap)) for f in sorted(ldir.rglob("*")) if f.is_file()] if ldir.is_dir() else []
    pods_dir = snap / "logs" / "pods"
    components = sorted(p.name for p in pods_dir.iterdir() if p.is_dir()) if pods_dir.is_dir() else []
    return {
        "source": "logs/ (signature matches) + loki/ + metrics/ + objects/pods.json",
        "signatures_version": paths.signatures_version(),
        "catalog_size": len(sigs),
        "catalog_errors": errors,
        "components_with_logs": components,
        "files": files,
        **res,
        "loki": analyze_loki(snap, inv),
        "agents": analyze_agents(snap, inv),
    }

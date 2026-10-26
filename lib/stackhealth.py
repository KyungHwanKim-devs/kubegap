"""Health of the observability stack itself: Prometheus, Alertmanager, Grafana, Loki.

"If Prometheus is sick, every other check runs on wrong data." Observability coverage (summary.observability) and the log pipeline (summary.logs) are
handled elsewhere; this module looks only at the state of the four components themselves: memory usage vs limit and OOMKilled, disk (PVC usage, retention,
actual days left), active series and top-cardinality metrics, slow scrapes and sampleLimit violations, rule evaluation delays and misses, failed notifications
to Alertmanager, TSDB compaction failures, WAL corruption, reload failures, replicas, Alertmanager reload/cluster/unused receivers/inhibits,
Grafana datasource response codes (429, 5xx), API 5xx, alert evaluation failures and version, Loki version, memory, request 5xx, rejections,
WAL disk, panics and whether retention is applied.
Inputs: prometheus/{tsdb,flags,buildinfo,runtimeinfo}.json, metrics/prom_*.json, am_*.json, monitoring_*.json (collectors/prometheus/metrics.yaml),
alertmanager/status.json, grafana/health.json + metrics/pod/grafana/*.prom, loki/{metrics.txt,buildinfo.json,ready.txt}, objects (statefulsets, deployments, pods).
Output is the `stackhealth` section of summary.json; shape is documented in SKILL.md. Tokens and webhook URLs are never copied anywhere.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import load_json, objects


def _rows(snap: Path, qid: str) -> list[dict]:
    d = load_json(snap / "metrics" / f"{qid}.json") or {}
    return d.get("result", []) if d.get("ok") else []


def _has(snap: Path, qid: str) -> bool:
    return bool((load_json(snap / "metrics" / f"{qid}.json") or {}).get("ok"))


def _v(row) -> float | None:
    try:
        return float(row["value"][1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _scalar(snap: Path, qid: str) -> float | None:
    r = _rows(snap, qid)
    return _v(r[0]) if r else None


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _major(v: str | None) -> int | None:
    try:
        return int(str(v).split(".")[0])
    except (ValueError, AttributeError):
        return None


def _mib(b) -> float | None:
    return round(b / 1024**2) if isinstance(b, (int, float)) else None


def _workload(snap: Path, pred) -> dict:
    for stem in ("statefulsets", "deployments"):
        for w in objects(snap, stem):
            if pred(w["metadata"]["name"]):
                sp, st = w.get("spec") or {}, w.get("status") or {}
                tpl = (sp.get("template") or {}).get("spec") or {}
                cs = tpl.get("containers") or [{}]
                main = next((c for c in cs if c.get("name") in ("prometheus", "alertmanager", "grafana", "loki")), cs[0])
                lim = (main.get("resources") or {}).get("limits") or {}
                vols = tpl.get("volumes") or []
                data_vol = next((v for v in vols if v.get("name") in ("storage", "data", "loki-data", "grafana-storage") or v.get("name", "").endswith("-db")), None)
                pvc = [v["metadata"]["name"] + ":" + str(((v.get("spec") or {}).get("resources") or {}).get("requests", {}).get("storage")) for v in sp.get("volumeClaimTemplates") or []]
                return {
                    "present": True,
                    "kind": "StatefulSet" if stem == "statefulsets" else "Deployment",
                    "namespace": w["metadata"]["namespace"],
                    "name": w["metadata"]["name"],
                    "replicas": sp.get("replicas"),
                    "ready": st.get("readyReplicas") or 0,
                    "version": _ver(main.get("image")),
                    "memory_limit": lim.get("memory"),
                    "memory_limit_mib": _parse_mem(lim.get("memory")),
                    "cpu_limit": lim.get("cpu"),
                    "args": [str(a) for a in (main.get("args") or [])],
                    "storage": "pvc-template:" + ",".join(pvc)
                    if pvc
                    else ("pvc:" + data_vol["persistentVolumeClaim"]["claimName"] if data_vol and "persistentVolumeClaim" in data_vol else ("emptyDir" if data_vol and "emptyDir" in data_vol else None)),
                }
    return {"present": False}


def _parse_mem(s) -> float | None:
    m = re.match(r"^(\d+(?:\.\d+)?)([KMGT]i?)?$", str(s or ""))
    if not m:
        return None
    n = float(m.group(1))
    u = m.group(2) or ""
    mult = {"": 1, "Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}[u]
    return round(n * mult / 1024**2)


def _pod_last_oom(snap: Path, name_prefix: str) -> dict:
    out = {"oomkilled": False, "restarts": 0, "finished_at": None}
    for p in objects(snap, "pods"):
        if not p["metadata"]["name"].startswith(name_prefix):
            continue
        for cs in (p.get("status") or {}).get("containerStatuses") or []:
            out["restarts"] += cs.get("restartCount") or 0
            term = (cs.get("lastState") or {}).get("terminated") or {}
            if term.get("reason") == "OOMKilled":
                out["oomkilled"] = True
                out["finished_at"] = term.get("finishedAt")
    return out


# ---------------- Prometheus ----------------


def _prometheus(snap: Path, inv: dict) -> dict:
    wl = _workload(snap, lambda n: n.startswith("prometheus-") and "node-exporter" not in n and "operator" not in n)
    store = (inv.get("stores") or {}).get("prometheus") or {}
    if not wl["present"] and not store.get("ok"):
        return {"present": False}
    tsdb = (load_json(snap / "prometheus" / "tsdb.json") or {}).get("data") or {}
    flags = (load_json(snap / "prometheus" / "flags.json") or {}).get("data") or {}
    build = (load_json(snap / "prometheus" / "buildinfo.json") or {}).get("data") or {}
    rt = (load_json(snap / "prometheus" / "runtimeinfo.json") or {}).get("data") or {}
    head = tsdb.get("headStats") or {}
    top_metrics = [{"name": x["name"], "series": x["value"]} for x in (tsdb.get("seriesCountByMetricName") or [])[:10]]
    num_series = head.get("numSeries") or _scalar(snap, "prom_head_series") or store.get("head_series")
    top_share = round(top_metrics[0]["series"] / num_series, 3) if top_metrics and num_series else None
    bucket_series = sum(x["series"] for x in top_metrics if x["name"].endswith("_bucket"))
    rss_ratio = _scalar(snap, "prom_rss_vs_limit")
    pvc_rows = _rows(snap, "prom_pvc_used_ratio")
    pvc_ratio = max([_v(r) or 0 for r in pvc_rows], default=None) if pvc_rows else None
    retention_days = _scalar(snap, "prom_retention_days")
    oldest_days = _scalar(snap, "prom_oldest_sample_days")
    interval = _scalar(snap, "prom_scrape_interval_s") or 30.0
    slow = [{"job": r["metric"].get("job"), "seconds": round(_v(r) or 0, 2)} for r in _rows(snap, "prom_scrape_slow_jobs")]
    slow_jobs = [s for s in slow if s["seconds"] >= interval * 0.5]
    limit_exceeded = {r["metric"].get("job"): round(_v(r) or 0) for r in _rows(snap, "prom_sample_limit_exceeded_1h")}
    notif_errors = {r["metric"].get("alertmanager"): round(_v(r) or 0) for r in _rows(snap, "prom_notifications_errors_1d")}
    rule_ratio = [{"group": (r["metric"].get("rule_group") or "").split(";")[-1], "ratio": round(_v(r) or 0, 3)} for r in _rows(snap, "prom_rule_eval_ratio_top")]
    restarts = {r["metric"].get("pod"): round(_v(r) or 0) for r in _rows(snap, "monitoring_restarts_7d")}
    oom_rows = [f"{r['metric'].get('pod')}/{r['metric'].get('container')}" for r in _rows(snap, "monitoring_oomkilled") if (_v(r) or 0) >= 1]
    oom_obj = _pod_last_oom(snap, "prometheus-")
    reload_ok = _scalar(snap, "prom_reload_ok")
    retention_size = flags.get("storage.tsdb.retention.size") or next((a.split("=", 1)[1] for a in wl.get("args", []) if a.startswith("--storage.tsdb.retention.size=")), None)
    pvc_size = next((a.split(":")[-1] for a in [wl.get("storage") or ""] if a.startswith("pvc-template")), None)
    metrics_available = _has(snap, "prom_head_series") or _has(snap, "prom_rss_vs_limit")
    return {
        "present": True,
        "workload": wl,
        "version": build.get("version") or store.get("version") or wl.get("version"),
        "major": _major(build.get("version") or store.get("version") or wl.get("version")),
        "start_time": rt.get("startTime"),
        "reload_success": rt.get("reloadConfigSuccess", None if reload_ok is None else reload_ok == 1),
        "last_config_time": rt.get("lastConfigTime"),
        "corruption_count": rt.get("corruptionCount"),
        "retention_time": flags.get("storage.tsdb.retention.time") or (store.get("retention") or {}).get("time"),
        "retention_size": retention_size,
        "retention_days": round(retention_days, 1) if retention_days else None,
        "oldest_sample_days": round(oldest_days, 1) if oldest_days else None,
        "retention_shortfall": bool(retention_days and oldest_days is not None and oldest_days < retention_days * 0.8 and rt.get("startTime") and oldest_days > 1),
        "head_series": num_series,
        "label_pairs": head.get("numLabelPairs"),
        "chunks": head.get("chunkCount"),
        "top_metrics": top_metrics,
        "top_metric_share": top_share,
        "top10_bucket_series": bucket_series,
        "top_labels_by_values": [{"label": x["name"], "values": x["value"]} for x in (tsdb.get("labelValueCountByLabelName") or [])[:5]],
        "rss_vs_limit": round(rss_ratio, 3) if rss_ratio is not None else None,
        "memory_limit": wl.get("memory_limit"),
        "oomkilled_last": oom_obj["oomkilled"] or any(x.startswith("prometheus-") and x.endswith("/prometheus") for x in oom_rows),
        "oomkilled_at": oom_obj["finished_at"],
        "restarts": oom_obj["restarts"],
        "pvc_used_ratio": round(pvc_ratio, 3) if pvc_ratio is not None else None,
        "pvc_size": pvc_size,
        "storage": wl.get("storage"),
        "tsdb_bytes": _scalar(snap, "prometheus_storage_bytes"),
        "scrape_interval_s": interval,
        "slow_scrape_jobs": slow_jobs,
        "scrape_top": slow[:5],
        "sample_limit_exceeded_1h": limit_exceeded,
        "notifications_dropped_1d": round(_scalar(snap, "prom_notifications_dropped_1d") or 0),
        "notifications_errors_1d": notif_errors,
        "rule_eval_ratio_top": rule_ratio,
        "rule_eval_ratio_max": max([x["ratio"] for x in rule_ratio], default=None),
        "rule_iterations_missed_1d": round(_scalar(snap, "prom_rule_iterations_missed_1d") or 0),
        "compactions_failed_7d": round(_scalar(snap, "prom_compactions_failed_7d") or 0),
        "wal_corruptions": round(_scalar(snap, "prom_wal_corruptions") or 0),
        "replicas_up": _scalar(snap, "prom_replicas"),
        "monitoring_restarts_7d": restarts,
        "monitoring_oomkilled": oom_rows,
        "admin_api": flags.get("web.enable-admin-api"),
        "lifecycle_api": flags.get("web.enable-lifecycle"),
        "query_timeout": flags.get("query.timeout"),
        "metrics_available": metrics_available,
        "tsdb_status_available": bool(tsdb),
    }


# ---------------- Alertmanager ----------------


def _alertmanager(snap: Path, inv: dict) -> dict:
    wl = _workload(snap, lambda n: n.startswith("alertmanager-"))
    store = (inv.get("stores") or {}).get("alertmanager") or {}
    status = load_json(snap / "alertmanager" / "status.json") or {}
    if not wl["present"] and not status:
        return {"present": False}
    cfg_text = (status.get("config") or {}).get("original") or ""
    referenced: set[str] = set(re.findall(r"^\s*-?\s*receiver:\s*\"?([^\"\n]+)\"?\s*$", cfg_text, re.MULTILINE))
    declared = [r["name"] for r in (load_json(snap / "alertmanager" / "receivers.json") or [])] or re.findall(r"^- name:\s*\"?([^\"\n]+)\"?\s*$", cfg_text, re.MULTILINE)
    unused = [r for r in declared if r not in referenced and r != "null"]
    inhibit = len(re.findall(r"^- source_matchers:|^- target_matchers:", cfg_text, re.MULTILINE))
    inhibit_rules = cfg_text.count("\n- source_matchers:") + cfg_text.count('\n- target_matchers:\n  - alertname="InfoInhibitor"')
    time_intervals = "time_intervals:" in cfg_text or "mute_time_intervals:" in cfg_text
    retention = next((a.split("=", 1)[1] for a in wl.get("args", []) if a.startswith("--data.retention=")), None)
    notif = {r["metric"].get("integration"): round(_v(r) or 0, 1) for r in _rows(snap, "am_notifications_1d")}
    received = {r["metric"].get("status"): round(_v(r) or 0) for r in _rows(snap, "am_received_1d")}
    silences = load_json(snap / "alertmanager" / "silences.json") or []
    cluster = status.get("cluster") or {}
    reload_ok = _scalar(snap, "am_reload_ok")
    return {
        "present": True,
        "workload": wl,
        "version": ((status.get("versionInfo") or {}).get("version")) or store.get("version") or wl.get("version"),
        "cluster_status": cluster.get("status"),
        "cluster_peers": len(cluster.get("peers") or []),
        "cluster_members_metric": _scalar(snap, "am_cluster_members"),
        "reload_success": None if reload_ok is None else reload_ok == 1,
        "invalid_alerts_1d": round(_scalar(snap, "am_invalid_alerts_1d") or 0),
        "receivers": declared,
        "receivers_unused": unused,
        "inhibit_rules": max(inhibit_rules, 0),
        "time_intervals": time_intervals,
        "data_retention": retention,
        "storage": wl.get("storage"),
        "notifications_1d": notif,
        "received_1d": received,
        "silences_total": len(silences),
        "silences_active": sum(1 for s in silences if (s.get("status") or {}).get("state") == "active"),
        "metrics_available": _has(snap, "am_reload_ok") or _has(snap, "am_received_1d"),
        "_inhibit_matchers": inhibit,
    }


# ---------------- Grafana ----------------


def _grafana(snap: Path, inv: dict) -> dict:
    wl = _workload(snap, lambda n: "grafana" in n)
    health = load_json(snap / "grafana" / "health.json") or {}
    store = (inv.get("stores") or {}).get("grafana") or {}
    if not wl["present"] and not health:
        return {"present": False}
    d = snap / "metrics" / "pod" / "grafana"
    files = [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []
    ds: dict[str, Counter] = {}
    api: Counter = Counter()
    alert_fail = 0
    notif_fail = 0
    stats = {}
    version = None
    rss = None
    for f in files:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        for labels, v in pm["labeled"].get("grafana_datasource_request_total", []):
            ds.setdefault(f"{labels.get('datasource')}({labels.get('datasource_type')})", Counter())[labels.get("code")] += int(v)
        for labels, v in pm["labeled"].get("grafana_api_response_status_total", []):
            api[labels.get("code")] += int(v)
        for labels, _v in pm["labeled"].get("grafana_build_info", []):
            version = labels.get("version")
        alert_fail += int(pm["single"].get("grafana_alerting_rule_evaluation_failures_total", 0)) + sum(int(v) for _, v in pm["labeled"].get("grafana_alerting_rule_evaluation_failures_total", []))
        notif_fail += int(pm["single"].get("grafana_alerting_notification_failed_total", 0)) + sum(int(v) for _, v in pm["labeled"].get("grafana_alerting_notification_failed_total", []))
        for k in ("grafana_stat_totals_dashboard", "grafana_stat_totals_datasource", "grafana_stat_totals_users", "grafana_stat_active_users", "grafana_stat_totals_alert_rules"):
            if k in pm["single"]:
                stats[k.replace("grafana_stat_", "")] = int(pm["single"][k])
        rss = pm["single"].get("process_resident_memory_bytes", rss)
    ds_rows = []
    for name, c in ds.items():
        total = sum(c.values())
        bad = sum(v for k, v in c.items() if str(k).startswith("5") or k == "429")
        ds_rows.append({"datasource": name, "requests": total, "errors_5xx_429": bad, "error_ratio": round(bad / total, 4) if total else 0.0, "by_code": dict(c)})
    api_total = sum(api.values())
    api_5xx = sum(v for k, v in api.items() if str(k).startswith("5"))
    ing = [i for i in objects(snap, "ingresses.networking.k8s.io") if "grafana" in i["metadata"]["name"]]
    ver = health.get("version") or store.get("version") or version or wl.get("version")
    return {
        "present": True,
        "workload": wl,
        "version": ver,
        "major": _major(ver),
        "database": health.get("database"),
        "datasources": ds_rows,
        "datasources_with_errors": [r["datasource"] for r in ds_rows if r["error_ratio"] >= 0.01 and r["errors_5xx_429"] >= 10],
        "datasource_error_max_ratio": max([r["error_ratio"] for r in ds_rows], default=None),
        "api_requests": api_total,
        "api_5xx": api_5xx,
        "alert_rule_eval_failures": alert_fail,
        "alert_notification_failures": notif_fail,
        "stats": stats,
        "rss_mib": _mib(rss),
        "ingress_hosts": [r.get("host") for i in ing for r in (i.get("spec") or {}).get("rules") or []],
        "storage": wl.get("storage"),
        "datasources_api": "no auth" if not (snap / "grafana" / "datasources.json").exists() else "read",
        "metrics_available": bool(files),
    }


# ---------------- Loki ----------------


def _loki(snap: Path, inv: dict) -> dict:
    wl = _workload(snap, lambda n: n.startswith("loki") and "promtail" not in n and "canary" not in n)
    build = load_json(snap / "loki" / "buildinfo.json") or {}
    if not wl["present"] and not build:
        return {"present": False}
    txt = snap / "loki" / "metrics.txt"
    pm = _parse_prom(txt.read_text(encoding="utf-8", errors="replace")) if txt.exists() and txt.stat().st_size > 0 else None
    out = {
        "present": True,
        "workload": wl,
        "version": build.get("version") or wl.get("version"),
        "major": _major(build.get("version") or wl.get("version")),
        "ready": (snap / "loki" / "ready.txt").read_text(errors="replace").strip() == "ready" if (snap / "loki" / "ready.txt").exists() else None,
        "metrics_available": pm is not None,
        "storage": wl.get("storage"),
        "memory_limit": wl.get("memory_limit"),
    }
    oom = _pod_last_oom(snap, "loki")
    out.update({"oomkilled_last": oom["oomkilled"], "oomkilled_at": oom["finished_at"], "restarts": oom["restarts"]})
    if pm is None:
        return out
    req5xx: Counter = Counter()
    req_total = 0
    for labels, v in pm["labeled"].get("loki_request_duration_seconds_count", []):
        req_total += int(v)
        if str(labels.get("status_code", "")).startswith("5") and labels.get("route") != "ready":  # /ready 503 during startup is normal
            req5xx[labels.get("route")] += int(v)
    discarded = {labels.get("reason"): int(v) for labels, v in pm["labeled"].get("loki_discarded_samples_total", []) if v > 0}
    rss = pm["single"].get("process_resident_memory_bytes")
    lim = wl.get("memory_limit_mib")
    retention_last = pm["single"].get("loki_boltdb_shipper_apply_retention_last_successful_run_timestamp_seconds")
    log_err = sum(int(v) for labels, v in pm["labeled"].get("loki_log_messages_total", []) if labels.get("level") == "error")
    out.update(
        {
            "requests_total": req_total,
            "requests_5xx": sum(req5xx.values()),
            "requests_5xx_by_route": dict(req5xx),
            "discarded_by_reason": discarded,
            "discarded_total": sum(discarded.values()),
            "wal_disk_full_failures": int(pm["single"].get("loki_ingester_wal_disk_full_failures_total", 0)),
            "panics": int(pm["single"].get("loki_panic_total", 0)),
            "log_error_messages": log_err,
            "rss_mib": _mib(rss),
            "rss_vs_limit": round(rss / (lim * 1024**2), 3) if rss and lim else None,
            "memory_streams": sum(int(v) for _, v in pm["labeled"].get("loki_ingester_memory_streams", [])) or pm["single"].get("loki_ingester_memory_streams"),
            "retention_applied": None if retention_last is None else retention_last > 0,
            "compactor_running": pm["single"].get("loki_boltdb_shipper_compactor_running"),
            "lines_received": sum(int(v) for _, v in pm["labeled"].get("loki_distributor_lines_received_total", [])),
            "bytes_received": sum(int(v) for _, v in pm["labeled"].get("loki_distributor_bytes_received_total", [])),
        }
    )
    return out


PROM_KEYS = [
    "version",
    "major",
    "start_time",
    "reload_success",
    "last_config_time",
    "corruption_count",
    "retention_time",
    "retention_size",
    "retention_days",
    "oldest_sample_days",
    "retention_shortfall",
    "head_series",
    "label_pairs",
    "chunks",
    "top_metrics",
    "top_metric_share",
    "top10_bucket_series",
    "top_labels_by_values",
    "rss_vs_limit",
    "memory_limit",
    "oomkilled_last",
    "oomkilled_at",
    "restarts",
    "pvc_used_ratio",
    "pvc_size",
    "storage",
    "tsdb_bytes",
    "scrape_interval_s",
    "slow_scrape_jobs",
    "scrape_top",
    "sample_limit_exceeded_1h",
    "notifications_dropped_1d",
    "notifications_errors_1d",
    "rule_eval_ratio_top",
    "rule_eval_ratio_max",
    "rule_iterations_missed_1d",
    "compactions_failed_7d",
    "wal_corruptions",
    "replicas_up",
    "monitoring_restarts_7d",
    "monitoring_oomkilled",
    "admin_api",
    "lifecycle_api",
    "query_timeout",
    "metrics_available",
    "tsdb_status_available",
    "replicas",
    "ready",
    "target",
]
AM_KEYS = [
    "version",
    "cluster_status",
    "cluster_peers",
    "cluster_members_metric",
    "reload_success",
    "invalid_alerts_1d",
    "receivers",
    "receivers_unused",
    "inhibit_rules",
    "time_intervals",
    "data_retention",
    "storage",
    "notifications_1d",
    "notifications_1d_total",
    "received_1d",
    "silences_total",
    "silences_active",
    "metrics_available",
    "replicas",
    "ready",
    "target",
]
GRAFANA_KEYS = [
    "version",
    "major",
    "database",
    "datasources",
    "datasources_with_errors",
    "datasource_error_max_ratio",
    "api_requests",
    "api_5xx",
    "alert_rule_eval_failures",
    "alert_notification_failures",
    "stats",
    "rss_mib",
    "ingress_hosts",
    "storage",
    "datasources_api",
    "metrics_available",
    "replicas",
    "ready",
    "target",
]
LOKI_KEYS = [
    "version",
    "major",
    "ready_endpoint",
    "metrics_available",
    "storage",
    "memory_limit",
    "oomkilled_last",
    "oomkilled_at",
    "restarts",
    "requests_total",
    "requests_5xx",
    "requests_5xx_by_route",
    "discarded_by_reason",
    "discarded_total",
    "wal_disk_full_failures",
    "panics",
    "log_error_messages",
    "rss_mib",
    "rss_vs_limit",
    "memory_streams",
    "retention_applied",
    "compactor_running",
    "lines_received",
    "bytes_received",
    "replicas",
    "ready",
    "target",
]


def _finish(d: dict, keys: list[str]) -> dict:
    """Lift the workload summary keys (replicas, ready, target) onto the component dict and fill missing ones with None, so every key used by check expressions always exists (selftest key audit)."""
    if d.get("present"):
        w = d.get("workload") or {}
        d.setdefault("replicas", w.get("replicas"))
        d.setdefault("ready", w.get("ready"))
        d.setdefault("target", f"{w.get('namespace')}/{(w.get('kind') or '').lower()}/{w.get('name')}" if w.get("present") else "cluster")
    for k in keys:
        d.setdefault(k, None)
    d.pop("_inhibit_matchers", None)
    return d


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    en = set(inv.get("collectors_enabled") or [])
    prom = _finish(_prometheus(snap, inv) if "prometheus" in en else {"present": False}, PROM_KEYS)
    am = _alertmanager(snap, inv) if "alertmanager" in en else {"present": False}
    if am.get("present"):
        am["notifications_1d_total"] = round(sum((am.get("notifications_1d") or {}).values()), 1)
    am = _finish(am, AM_KEYS)
    gf = _finish(_grafana(snap, inv) if "grafana" in en else {"present": False}, GRAFANA_KEYS)
    lk = _loki(snap, inv) if "loki" in en else {"present": False}
    if lk.get("present"):
        lk["ready_endpoint"] = lk.pop("ready", None)
    lk = _finish(lk, LOKI_KEYS)
    return {
        "present": any(x.get("present") for x in (prom, am, gf, lk)),
        "prometheus": prom,
        "alertmanager": am,
        "grafana": gf,
        "loki": lk,
        "note": "Counters accumulate since each process started (Prometheus queries state their window). Grafana datasource and dashboard lists are read only when grafana_api_token is set. No token or webhook URL is stored anywhere",
    }

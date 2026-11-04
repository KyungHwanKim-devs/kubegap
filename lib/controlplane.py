"""Control plane summary. Called by summarize to build the controlplane section of summary.json.

EKS: logs/cloudwatch/<id>.json (Logs Insights results) + metrics/apiserver_*.json.
k3s: logs/node/<node>/k3s-*.log|txt (journalctl read over SSH) + metrics/apiserver_*.json (kube-prometheus-stack scrapes the k3s apiserver /metrics too).
Missing inputs are recorded as absent and we continue. Pod names are grouped by owning workload (hash removed) so finding ids stay stable.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .snapshot import load_json

# klog header `Lmmdd hh:mm:ss.uuuuuu <pid, %7d> file.go:line] ` (k8s.io/klog/v2 internal/buffer/buffer.go:117-155@v2.130.1, @v2.140.0); the file name may hold digits
# (cronjob_controllerv2.go) or a directory with --add_dir_header, hence `\S+`.
KLOG_RE = re.compile(r"^([EIWF])\d{4} [\d:.]+ +\d+ (\S+\.go):\d+\] (.*)$")
POD_HASH_RE = re.compile(r"^(.*?)-[0-9a-f]{5,10}-[0-9a-z]{5}$|^(.*?)-\d{6,}-[0-9a-z]{5}$|^(.*?)-[0-9a-z]{5}$")


def _cw(snap: Path, qid: str) -> dict | None:
    return load_json(snap / "logs" / "cloudwatch" / f"{qid}.json")


def _rows(snap: Path, qid: str) -> list[dict]:
    d = _cw(snap, qid)
    return (d or {}).get("rows", []) if (d or {}).get("ok") else []


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def workload_of(pod_ref: str) -> str:
    """'ns/pod-6d7ff4dcdb-fphgn' -> 'ns/pod'. Name-shape guess used when owner information is unavailable."""
    ns, _, pod = pod_ref.partition("/")
    m = POD_HASH_RE.match(pod)
    base = next((g for g in (m.groups() if m else ()) if g), pod)
    return f"{ns}/{base}" if ns else base


def _normalize_msg(msg: str) -> str:
    """Strip the klog header (time, PID, source) and blank out numbers, ids and IPs so errors of the same kind collapse into one line."""
    m = KLOG_RE.match(msg.strip())
    body = m.group(3) if m else msg.strip()
    body = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", "<ip>", body)
    body = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", body)
    body = re.sub(r"\b[a-z0-9-]+-[0-9a-f]{5,10}-[0-9a-z]{5}\b", "<pod>", body)
    body = re.sub(r"\b\d+(\.\d+)?(ms|s|m|h|µs|ns)\b", "<dur>", body)
    body = re.sub(r"\b\d{3,}\b", "<n>", body)
    return body[:160]


def _metric_rows(snap: Path, qid: str) -> list[dict]:
    d = load_json(snap / "metrics" / f"{qid}.json") or {}
    return d.get("result", []) if d.get("ok") else []


def _metric_scalar(snap: Path, qid: str) -> float | None:
    rows = _metric_rows(snap, qid)
    try:
        return sum(float(r["value"][1]) for r in rows) if rows else None
    except (KeyError, ValueError, IndexError):
        return None


def _storage_objects_top(snap: Path) -> list[dict]:
    """Top stored-object counts per resource. apiserver_resource_objects (group, resource) exists since Kubernetes 1.34 and replaces apiserver_storage_objects,
    which is deprecated since 1.34.0 and hidden from 1.37; read the new query first and the old one when it is empty (before 1.34). One series per apiserver
    instance, so keep one value per resource (the instances report the same count)."""
    rows = _metric_rows(snap, "apiserver_resource_objects_top")
    if rows:
        counts = {(f"{r['metric'].get('resource')}.{r['metric']['group']}" if r["metric"].get("group") else r["metric"].get("resource")): max(_int(r["value"][1]), 0) for r in rows}
    else:
        counts = {r["metric"].get("resource"): max(_int(r["value"][1]), 0) for r in _metric_rows(snap, "apiserver_storage_objects_top")}
    return sorted(({"resource": k, "count": v} for k, v in counts.items()), key=lambda x: -x["count"])[:15]


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    platform = (inv.get("cluster") or {}).get("platform")
    out: dict = {"platform": platform, "source": None}

    # ---------- apiserver metrics (common) ----------
    p99 = []
    for r in _metric_rows(snap, "apiserver_p99_latency_by_verb"):
        try:
            v = float(r["value"][1])
        except (KeyError, ValueError, IndexError):
            continue
        if not math.isnan(v):
            p99.append({"verb": r["metric"].get("verb"), "p99_seconds": round(v, 3)})
    p99.sort(key=lambda x: -x["p99_seconds"])
    webhook_p99 = []
    for r in _metric_rows(snap, "apiserver_webhook_p99_by_name"):
        try:
            v = float(r["value"][1])
        except (KeyError, ValueError, IndexError):
            continue
        if not math.isnan(v):  # skip NaN
            webhook_p99.append({"name": r["metric"].get("name"), "p99_seconds": round(v, 3)})
    webhook_p99.sort(key=lambda x: -x["p99_seconds"])
    job = load_json(snap / "prometheus" / "apiserver_job.json") or {}
    out["apiserver_metrics"] = {
        "source": "metrics/apiserver_*.json",
        "job": job.get("job"),  # the job label the apiserver queries filtered on (prometheus/apiserver_job.json: config, detected, or none when no apiserver series exists)
        "job_source": job.get("source"),
        "job_candidates": job.get("candidates"),
        "rate_429": _metric_scalar(snap, "apiserver_429_rate"),
        "rate_5xx": _metric_scalar(snap, "apiserver_5xx_rate"),
        "p99_by_verb": p99,
        "p99_max": p99[0] if p99 else None,
        "watch_count": _metric_scalar(snap, "apiserver_watch_count"),
        "storage_objects_top": _storage_objects_top(snap),
        "webhook_p99": webhook_p99[:10],
        "top_requests": [{"resource": r["metric"].get("resource"), "verb": r["metric"].get("verb"), "rps": round(float(r["value"][1]), 2)} for r in _metric_rows(snap, "apiserver_top_requests")],
        "inflight": {r["metric"].get("request_kind"): _int(r["value"][1]) for r in _metric_rows(snap, "apiserver_inflight")},
    }

    if platform == "eks":
        out["source"] = "logs/cloudwatch/*.json (CloudWatch Logs Insights, 24h)"
        vol = {}
        for r in _rows(snap, "volume_by_stream"):
            stream = r.get("@logStream", "")
            comp = re.sub(r"-[0-9a-f]{32}$", "", stream)
            vol[comp] = vol.get(comp, 0) + _int(r.get("lines"))
        meta = _cw(snap, "volume_by_stream") or {}
        out["log_volume_24h"] = vol
        out["log_group"] = meta.get("log_group")
        out["available"] = bool(meta.get("ok"))
        out["apiserver"] = {
            "errors_by_source": [{"level": r.get("lvl"), "source": r.get("src"), "count": _int(r.get("c"))} for r in _rows(snap, "apiserver_errors_by_source")],
            "slow_traces": [{"op": r.get("op"), "count": _int(r.get("c"))} for r in _rows(snap, "apiserver_slow_traces")],
            "slow_traces_total": sum(_int(r.get("c")) for r in _rows(snap, "apiserver_slow_traces")),
            "webhook_failures": [{"webhook": r.get("webhook"), "count": _int(r.get("c"))} for r in _rows(snap, "apiserver_webhook_failures")],
            "etcd_errors_by_hour": [{"hour": r.get("bin(1h)"), "count": _int(r.get("c"))} for r in _rows(snap, "apiserver_etcd_errors")],
        }
        cm_samples = Counter(_normalize_msg(r.get("@message", "")) for r in _rows(snap, "controller_manager_error_samples"))
        out["controller_manager"] = {
            "errors_by_source": [{"level": r.get("lvl"), "source": r.get("src"), "count": _int(r.get("c"))} for r in _rows(snap, "controller_manager_errors_by_source")],
            "top_errors": [{"message": m, "sample_count": c} for m, c in cm_samples.most_common(10)],
        }
        by_wl: dict[str, int] = defaultdict(int)
        for r in _rows(snap, "scheduler_unschedulable"):
            by_wl[workload_of(r.get("pod") or "?")] += _int(r.get("c"))
        reasons = Counter()
        for r in _rows(snap, "scheduler_unschedulable_samples"):
            m = re.search(r'err="([^"]{0,140})', r.get("@message", ""))
            if m:
                reasons[re.sub(r"\d+", "<n>", m.group(1))] += 1
        out["scheduler"] = {
            "unschedulable_total_24h": sum(_int(r.get("c")) for r in _rows(snap, "scheduler_unschedulable")),
            "by_workload": [{"workload": w, "namespace": w.split("/")[0], "count": c} for w, c in sorted(by_wl.items(), key=lambda kv: -kv[1])],
            "reasons": [{"reason": k, "samples": v} for k, v in reasons.most_common(8)],
        }
        out["authenticator"] = {"failures": [{"message": r.get("msg"), "count": _int(r.get("c"))} for r in _rows(snap, "authenticator_failures")], "failures_total": sum(_int(r.get("c")) for r in _rows(snap, "authenticator_failures"))}
        out["cloud_controller"] = {"errors_by_source": [{"level": r.get("lvl"), "source": r.get("src"), "count": _int(r.get("c"))} for r in _rows(snap, "cloud_controller_errors")]}
        out["audit_stream_lines"] = sum(_int(r.get("lines")) for r in _rows(snap, "audit_stream_present"))
        out["query_failures"] = [{"id": p.stem, "error": (load_json(p) or {}).get("error")} for p in (snap / "logs" / "cloudwatch").glob("*.json") if not (load_json(p) or {}).get("ok")] if (snap / "logs" / "cloudwatch").is_dir() else []

    elif platform in ("k3s", "rke2"):
        out["source"] = "logs/node/<node>/k3s-*.log (journalctl -u k3s/k3s-agent, SSH, 24h)"
        nodes = {}
        ndir = snap / "logs" / "node"
        total_unsched = 0
        total_webhook = 0
        etcd = {"apply_took_too_long": 0, "request_stats_slow": 0, "readindex_slow": 0, "leader_changed": 0, "max_ms": 0.0}
        sched_by_wl: dict[str, int] = defaultdict(int)
        for nd in sorted(ndir.iterdir()) if ndir.is_dir() else []:
            rec: dict = {"node": nd.name}
            stats = nd / "k3s-stats-24h.txt"
            if stats.is_file():
                rows = []
                for line in stats.read_text(encoding="utf-8").splitlines():
                    m = re.match(r"\s*(\d+)\s+(.*)$", line)
                    if m:
                        rows.append({"count": int(m.group(1)), "kind": m.group(2).strip()})
                rec["stats"] = rows[:20]
                rec["errors_24h"] = sum(r["count"] for r in rows if re.match(r"klog [EF]|etcd-json (warn|error)|logrus (warning|error)", r["kind"]))
            err = nd / "k3s-errors-24h.log"
            if err.is_file():
                lines = err.read_text(encoding="utf-8", errors="replace").splitlines()
                rec["error_lines_captured"] = len(lines)
                rec["top_errors"] = [{"message": m_, "count": c} for m_, c in Counter(_normalize_msg(ln) for ln in lines).most_common(10)]
            su = nd / "k3s-scheduler-unschedulable-24h.log"
            if su.is_file():
                lines = su.read_text(encoding="utf-8", errors="replace").splitlines()
                rec["scheduler_unschedulable_lines"] = len(lines)
                total_unsched += len(lines)
                for ln in lines:
                    m = re.search(r'pod="([^"]+)"', ln)
                    if m:
                        sched_by_wl[workload_of(m.group(1))] += 1
            wf = nd / "k3s-webhook-failures-24h.log"
            if wf.is_file():
                n = len(wf.read_text(encoding="utf-8", errors="replace").splitlines())
                rec["webhook_failure_lines"] = n
                total_webhook += n
            es = nd / "k3s-etcd-slow-24h.log"
            if es.is_file():
                text = es.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                rec["etcd_slow_lines"] = len(lines)
                rec["etcd_slow_capped"] = len(lines) >= 200
                etcd["apply_took_too_long"] += text.count('"apply request took too long"')
                etcd["request_stats_slow"] += text.count('"request stats"')
                etcd["readindex_slow"] += text.count("ReadIndex response took too long")
                etcd["leader_changed"] += text.count("leader changed")
                for m in re.finditer(r'"(?:time spent|took)":"([\d.]+)(ms|s)"', text):
                    ms = float(m.group(1)) * (1000 if m.group(2) == "s" else 1)
                    etcd["max_ms"] = max(etcd["max_ms"], ms)
            pl = nd / "kubelet-pleg-eviction-24h.log"
            if pl.is_file():
                lines = pl.read_text(encoding="utf-8", errors="replace").splitlines()
                rec["kubelet_pleg_eviction_lines"] = len(lines)
                rec["kubelet_pleg_eviction_samples"] = [ln[-160:] for ln in lines[:3]]
            nodes[nd.name] = rec
        out["nodes"] = nodes
        out["available"] = bool(nodes)
        out["scheduler"] = {"unschedulable_total_24h": total_unsched, "by_workload": [{"workload": w, "namespace": w.split("/")[0], "count": c} for w, c in sorted(sched_by_wl.items(), key=lambda kv: -kv[1])]}
        out["webhook_failures_total"] = total_webhook
        out["etcd"] = etcd
        out["controller_manager"] = {"note": "k3s runs as one process, so controller-manager errors are mixed into nodes[<server>].top_errors"}
    else:
        out["source"] = None
        out["available"] = False
        out["note"] = f"no control plane log collector for platform {platform}"
    return out

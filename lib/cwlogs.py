"""CloudWatch Logs Insights queries. EKS control plane logs land in the CloudWatch log group
`/aws/eks/<cluster>/cluster` as streams kube-apiserver-*, kube-controller-manager-*, kube-scheduler-*, authenticator-*, cloud-controller-manager-*,
and (if enabled) kube-apiserver-audit-*. Insights is asynchronous: start-query -> query id -> poll get-query-results until done.
Usually a few seconds; long ranges take tens of seconds. Poll interval 2 s, default cap 120 s.

The query list lives in collectors/eks-platform/cwlogs.yaml and collect runs it as a `type: cwlogs` step. Results go to logs/cloudwatch/<id>.json.
"""

from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path

from . import aws as _aws
from . import yamlite
from .runlog import RunLog

TERMINAL = {"Complete", "Failed", "Cancelled", "Timeout", "Unknown"}


def log_group_for(cluster: str) -> str:
    return f"/aws/eks/{cluster}/cluster"


def run_query(group: str, query: str, hours: float, *, profile: str | None, region: str | None, timeout: float = 120.0, limit: int | None = None) -> dict:
    """Run one Insights query to completion and return {ok, status, rows[], statistics, error, seconds}. Never raises."""
    t0 = time.monotonic()
    end = int(time.time())
    start = end - int(hours * 3600)
    args = ["logs", "start-query", "--log-group-name", group, "--start-time", str(start), "--end-time", str(end), "--query-string", query]
    if limit:
        args += ["--limit", str(limit)]
    d, r = _aws.aws_json(args, profile=profile, region=region, timeout=60)
    if d is None or not d.get("queryId"):
        return {"ok": False, "status": "StartFailed", "error": r.error or r.stderr.strip()[-300:] or "no queryId", "rows": [], "seconds": time.monotonic() - t0}
    qid = d["queryId"]
    status, res = "Running", {}
    while time.monotonic() - t0 < timeout:
        time.sleep(2.0)  # Insights is asynchronous; polling is the only option (no completion notification)
        res, r = _aws.aws_json(["logs", "get-query-results", "--query-id", qid], profile=profile, region=region, timeout=60)
        if res is None:
            return {"ok": False, "status": "PollFailed", "query_id": qid, "error": r.error or r.stderr.strip()[-300:], "rows": [], "seconds": time.monotonic() - t0}
        status = res.get("status", "Unknown")
        if status in TERMINAL:
            break
    if status != "Complete":
        # If it did not finish in time, cancel it so it does not keep costing or occupying the queue (cancelling our own query is housekeeping, not a write call)
        if status not in TERMINAL:
            _aws.aws(["logs", "stop-query", "--query-id", qid], profile=profile, region=region, timeout=30)
        return {"ok": False, "status": status, "query_id": qid, "error": f"query status {status}", "rows": [], "seconds": time.monotonic() - t0, "statistics": res.get("statistics")}
    rows = [{f["field"]: f.get("value") for f in row if f.get("field")} for row in res.get("results", [])]
    return {"ok": True, "status": status, "query_id": qid, "rows": rows, "statistics": res.get("statistics"), "seconds": time.monotonic() - t0}


def run_file(path: Path, out_dir: Path, *, cluster: str, profile: str | None, region: str | None, log: RunLog | None = None, collector: str | None = None, echo=None, default_hours: float = 24.0) -> dict:
    """Run and save every query in cwlogs.yaml. Entries: id, why, query, hours (optional), limit (optional)."""
    items = yamlite.load_file(path) or []
    out_dir.mkdir(parents=True, exist_ok=True)
    group = log_group_for(cluster)
    summary = {"ok": 0, "failed": 0, "queries": {}, "log_group": group}
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    for it in items:
        qid = it["id"]
        q = " ".join(str(it["query"]).split())
        hours = float(it.get("hours", default_hours))
        res = run_query(group, q, hours, profile=profile, region=region, limit=it.get("limit"))
        rec = {"id": qid, "why": it.get("why"), "query": q, "hours": hours, "log_group": group, "taken_at": now, **res}
        (out_dir / f"{qid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        summary["queries"][qid] = {"ok": res["ok"], "rows": len(res["rows"]), "status": res["status"], "error": res.get("error"), "scanned_bytes": (res.get("statistics") or {}).get("bytesScanned")}
        summary["ok" if res["ok"] else "failed"] += 1
        if log is not None:
            log.command(id=f"cwlogs.{qid}", cmd=["cwlogs", group, q], code=0 if res["ok"] else 1, seconds=res["seconds"], out_path=f"logs/cloudwatch/{qid}.json" if res["ok"] else None, error=res.get("error"), collector=collector)
        if echo:
            msg = f"rows {len(res['rows'])} ({res['seconds']:.0f}s)" if res["ok"] else "failed: " + str(res.get("error"))[:100]
            echo(f"    {qid:<36} {msg}")
    return summary

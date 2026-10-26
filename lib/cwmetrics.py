"""Generic CloudWatch metrics collection step `cw-metrics` (EBS root volume IOPS/queue length, service quota usage). EKS only, read-only calls.

Step shape in collect.yaml:
  - id: ebs-volume-metrics
    type: cw-metrics
    out: aws/cw-ebs-volumes.json
    hours: 24            # window
    period: 3600         # seconds. 24 points for a 24-hour window
    namespace: AWS/EBS
    dimension: VolumeId  # the dimension name that varies per item
    from_file: {path: aws/ec2-volumes.json, items: "", key: id}   # take dimension values from an earlier step's result in the same snapshot. items "" means the top level is a list
    metrics: [{name: VolumeQueueLength, stat: Average}, {name: VolumeReadOps, stat: Sum}]
  - id: quota-usage
    type: cw-metrics
    out: aws/cw-quota-usage.json
    mode: quotas         # query the UsageMetric (namespace, name, dimensions, recommended statistic) from service-quotas results as is. Item key = QuotaCode
    from_file: {path: aws/service-quotas-ec2.json, items: ""}
    from_files: [aws/service-quotas-vpc.json, ...]   # for several files
    hours: 1
    period: 3600
Result: {window_hours, generated_at, items{key: {metric_stat: {points, max, min, last, avg, sum}}}, meta{key: {source item summary}}, queries, errors[]}
get-metric-data is called in batches of 100 (same approach as the ALB step). Required permission: cloudwatch:GetMetricData.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import re
from pathlib import Path

from . import aws as _aws
from .runlog import RunLog
from .snapshot import load_json


def _items(doc, items_path: str) -> list:
    cur = doc
    for part in [p for p in (items_path or "").split(".") if p]:
        cur = (cur or {}).get(part) if isinstance(cur, dict) else None
    return cur if isinstance(cur, list) else []


def collect(snap: Path, st: dict, *, profile: str | None, region: str | None, log: RunLog | None, collector: str, timeout: float, echo=None) -> dict:
    kw = {"profile": profile, "region": region, "log": log, "collector": collector}
    out_rel = st["out"]
    hours = int(st.get("hours", 24))
    period = int(st.get("period", 3600))
    mode = st.get("mode", "static")
    files = []
    ff = st.get("from_file") or {}
    if ff.get("path"):
        files.append((ff["path"], ff.get("items", ""), ff.get("key")))
    for p in st.get("from_files") or []:
        files.append((p, ff.get("items", ""), ff.get("key")))
    queries: list[dict] = []
    qmeta: dict[str, tuple[str, str]] = {}
    meta: dict[str, dict] = {}
    errors: list[str] = []
    qn = 0

    def add(key: str, ns: str, mname: str, dims: dict, stat: str):
        nonlocal qn
        qid = f"q{qn}"
        qn += 1
        queries.append({"Id": qid, "MetricStat": {"Metric": {"Namespace": ns, "MetricName": mname, "Dimensions": [{"Name": k, "Value": str(v)} for k, v in dims.items()]}, "Period": period, "Stat": stat}})
        qmeta[qid] = (key, f"{mname}_{stat}")

    for path, items_path, key_field in files:
        doc = load_json(snap / path)
        if doc is None:
            errors.append(f"{path} missing (earlier step failed?)")
            continue
        for it in _items(doc, items_path):
            if not isinstance(it, dict):
                continue
            if mode == "quotas":
                um = it.get("UsageMetric") or {}
                if not um.get("MetricName"):
                    continue
                key = it.get("QuotaCode") or it.get("QuotaName")
                meta[key] = {
                    "service": it.get("ServiceCode"),
                    "name": it.get("QuotaName"),
                    "value": it.get("Value"),
                    "unit": it.get("Unit"),
                    "adjustable": it.get("Adjustable"),
                    "global": it.get("GlobalQuota"),
                    "resource": (um.get("MetricDimensions") or {}).get("Resource"),
                    "class": (um.get("MetricDimensions") or {}).get("Class"),
                }
                add(key, um.get("MetricNamespace", "AWS/Usage"), um["MetricName"], um.get("MetricDimensions") or {}, um.get("MetricStatisticRecommendation") or "Maximum")
            else:
                val = it.get(key_field) if key_field else None
                if not val:
                    continue
                meta[str(val)] = {k: v for k, v in it.items() if k in ("size", "type", "iops", "throughput", "az", "state", "attachments", "Size", "VolumeType", "Iops", "AvailabilityZone")}
                for m in st.get("metrics") or []:
                    add(str(val), st.get("namespace", "AWS/EBS"), m["name"], {st.get("dimension", "VolumeId"): val}, m.get("stat", "Average"))
    out: dict = {"window_hours": hours, "period_s": period, "generated_at": _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat(), "mode": mode, "items": {}, "meta": meta, "queries": len(queries), "errors": errors}
    if queries:
        end = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
        start = end - _dt.timedelta(hours=hours)
        tmp = snap / "aws" / f"_mdq_{re.sub(r'[^a-z0-9]+', '_', st.get('id', 'cw'))}.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        for i in range(0, len(queries), 100):
            tmp.write_text(json.dumps(queries[i : i + 100]), encoding="utf-8")
            res, r = _aws.aws_json(
                ["cloudwatch", "get-metric-data", "--metric-data-queries", f"file://{tmp}", "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"), "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ")],
                id=f"{collector}.{st.get('id', 'cw')}.get-metric-data",
                timeout=timeout,
                **kw,
            )
            if res is None:
                errors.append(f"get-metric-data: {r.error or r.stderr.strip()[-200:]}")
                continue
            for mr in res.get("MetricDataResults") or []:
                key, mk = qmeta.get(mr["Id"], (None, None))
                if key is None:
                    continue
                vals = [float(v) for v in mr.get("Values") or []]
                agg: dict = {"points": len(vals), "status": mr.get("StatusCode")}
                if vals:
                    agg.update({"sum": round(sum(vals), 3), "max": round(max(vals), 4), "min": round(min(vals), 4), "last": round(vals[0], 4), "avg": round(sum(vals) / len(vals), 4)})
                out["items"].setdefault(key, {})[mk] = agg
            for m in res.get("Messages") or []:
                errors.append(f"get-metric-data message: {m}")
        with contextlib.suppress(OSError):
            tmp.unlink()
    p = snap / out_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
    if echo:
        echo(f"    saved {out_rel} (items {len(meta)}, queries {len(queries)}, errors {len(errors)})")
    return {"ok": not errors or bool(out["items"]), "items": len(meta), "queries": len(queries), "errors": errors[:5]}

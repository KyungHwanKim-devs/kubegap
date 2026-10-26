"""ALB/NLB and target group state plus CloudWatch metrics. EKS only, read-only calls.

aws elbv2 describe-load-balancers / describe-load-balancer-attributes / describe-target-groups / describe-target-group-attributes / describe-target-health,
aws cloudwatch get-metric-data (24 hours, 1-hour period). Output is a single aws/alb-metrics.json. lib/traffic.py joins it to k8s Services/Ingresses via TargetGroupBindings.

CloudWatch dimensions: LoadBalancer = the 'app/<name>/<id>' part of the ARN (NLB: 'net/...'), TargetGroup = 'targetgroup/<name>/<id>'. Measured on a real cluster: 1 ALB and 40 target groups took 6 get-metric-data calls in 0.6 s.
Required permissions: elasticloadbalancing:Describe*, cloudwatch:GetMetricData.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
from pathlib import Path

from . import aws as _aws
from .runlog import RunLog

LB_METRICS_ALB = [
    ("RequestCount", "Sum"),
    ("HTTPCode_ELB_5XX_Count", "Sum"),
    ("HTTPCode_ELB_4XX_Count", "Sum"),
    ("HTTPCode_Target_5XX_Count", "Sum"),
    ("HTTPCode_Target_4XX_Count", "Sum"),
    ("TargetResponseTime", "p95"),
    ("TargetResponseTime", "p99"),
    ("RejectedConnectionCount", "Sum"),
    ("ActiveConnectionCount", "Sum"),
]
TG_METRICS_ALB = [
    ("RequestCount", "Sum"),
    ("HTTPCode_Target_5XX_Count", "Sum"),
    ("HTTPCode_Target_4XX_Count", "Sum"),
    ("TargetResponseTime", "p95"),
    ("UnHealthyHostCount", "Maximum"),
    ("HealthyHostCount", "Minimum"),
    ("RequestCountPerTarget", "Sum"),
]
LB_METRICS_NLB = [("ActiveFlowCount", "Maximum"), ("ProcessedBytes", "Sum"), ("TCP_ELB_Reset_Count", "Sum"), ("TCP_Target_Reset_Count", "Sum")]
TG_METRICS_NLB = [("UnHealthyHostCount", "Maximum"), ("HealthyHostCount", "Minimum")]


def _dim(arn: str, kind: str) -> str:
    # arn:aws:elasticloadbalancing:<region>:<acct>:loadbalancer/app/x/y → app/x/y ; …:targetgroup/x/y → targetgroup/x/y
    if kind == "lb":
        return arn.split(":loadbalancer/", 1)[1] if ":loadbalancer/" in arn else arn
    return arn.split(":", 5)[5] if arn.count(":") >= 5 else arn


def _attrs(lst: list | None) -> dict:
    return {a.get("Key"): a.get("Value") for a in (lst or [])}


def collect(snap: Path, out_rel: str, *, profile: str | None, region: str | None, log: RunLog, collector: str, timeout: float = 300, hours: int = 24, echo=None) -> dict:
    kw = {"profile": profile, "region": region, "log": log, "collector": collector}
    errors: list[str] = []
    out: dict = {"window_hours": hours, "generated_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"), "lbs": [], "target_groups": [], "errors": errors}
    lbs, r = _aws.aws_json(["elbv2", "describe-load-balancers"], id=f"{collector}.alb.describe-load-balancers", timeout=60, **kw)
    if lbs is None:
        errors.append(f"describe-load-balancers: {r.error or r.stderr.strip()[-200:]}")
        _write(snap, out_rel, out)
        return {"ok": False, "error": errors[-1]}
    queries: list[dict] = []
    qmeta: dict[str, tuple] = {}
    qn = 0
    for lb in lbs.get("LoadBalancers") or []:
        arn = lb["LoadBalancerArn"]
        kind = lb.get("Type")  # application | network | gateway
        attrs, r = _aws.aws_json(["elbv2", "describe-load-balancer-attributes", "--load-balancer-arn", arn], id=f"{collector}.alb.lb-attributes", timeout=60, **kw)
        a = _attrs((attrs or {}).get("Attributes"))
        row = {
            "arn": arn,
            "dim": _dim(arn, "lb"),
            "name": lb.get("LoadBalancerName"),
            "dns": lb.get("DNSName"),
            "type": kind,
            "scheme": lb.get("Scheme"),
            "state": (lb.get("State") or {}).get("Code"),
            "created": lb.get("CreatedTime"),
            "azs": [z.get("ZoneName") for z in lb.get("AvailabilityZones") or []],
            "security_groups": lb.get("SecurityGroups") or [],
            "ip_address_type": lb.get("IpAddressType"),
            "idle_timeout_s": int(a["idle_timeout.timeout_seconds"]) if a.get("idle_timeout.timeout_seconds") else None,
            "deletion_protection": a.get("deletion_protection.enabled") == "true",
            "access_logs": a.get("access_logs.s3.enabled") == "true",
            "drop_invalid_headers": a.get("routing.http.drop_invalid_header_fields.enabled") == "true",
            "http2": a.get("routing.http2.enabled"),
            "cross_zone": a.get("load_balancing.cross_zone.enabled"),
            "target_groups": [],
        }
        if attrs is None:
            errors.append(f"lb-attributes {row['name']}: {r.error or r.stderr.strip()[-120:]}")
        tgs, r = _aws.aws_json(["elbv2", "describe-target-groups", "--load-balancer-arn", arn], id=f"{collector}.alb.describe-target-groups", timeout=60, **kw)
        if tgs is None:
            errors.append(f"describe-target-groups {row['name']}: {r.error or r.stderr.strip()[-120:]}")
        for tg in (tgs or {}).get("TargetGroups") or []:
            tarn = tg["TargetGroupArn"]
            ta, _ = _aws.aws_json(["elbv2", "describe-target-group-attributes", "--target-group-arn", tarn], id=f"{collector}.alb.tg-attributes", timeout=60, **kw)
            ta = _attrs((ta or {}).get("Attributes"))
            th, r2 = _aws.aws_json(["elbv2", "describe-target-health", "--target-group-arn", tarn], id=f"{collector}.alb.target-health", timeout=60, **kw)
            targets = []
            for d in (th or {}).get("TargetHealthDescriptions") or []:
                h = d.get("TargetHealth") or {}
                targets.append({"id": (d.get("Target") or {}).get("Id"), "port": (d.get("Target") or {}).get("Port"), "state": h.get("State"), "reason": h.get("Reason"), "description": (h.get("Description") or "")[:120]})
            trow = {
                "arn": tarn,
                "dim": _dim(tarn, "tg"),
                "name": tg.get("TargetGroupName"),
                "lb": row["name"],
                "lb_dim": row["dim"],
                "lb_type": kind,
                "protocol": tg.get("Protocol"),
                "port": tg.get("Port"),
                "target_type": tg.get("TargetType"),
                "health_check": {
                    "path": tg.get("HealthCheckPath"),
                    "port": tg.get("HealthCheckPort"),
                    "protocol": tg.get("HealthCheckProtocol"),
                    "interval_s": tg.get("HealthCheckIntervalSeconds"),
                    "timeout_s": tg.get("HealthCheckTimeoutSeconds"),
                    "healthy_threshold": tg.get("HealthyThresholdCount"),
                    "unhealthy_threshold": tg.get("UnhealthyThresholdCount"),
                    "matcher": (tg.get("Matcher") or {}).get("HttpCode"),
                },
                "deregistration_delay_s": int(ta["deregistration_delay.timeout_seconds"]) if ta.get("deregistration_delay.timeout_seconds") else None,
                "slow_start_s": int(ta["slow_start.duration_seconds"]) if ta.get("slow_start.duration_seconds") else None,
                "stickiness": ta.get("stickiness.enabled") == "true",
                "algorithm": ta.get("load_balancing.algorithm.type"),
                "targets": targets,
                "targets_total": len(targets),
                "targets_healthy": sum(1 for t in targets if t["state"] == "healthy"),
                "targets_unhealthy": [t for t in targets if t["state"] not in ("healthy", None)],
            }
            if th is None:
                errors.append(f"target-health {trow['name']}: {r2.error or r2.stderr.strip()[-120:]}")
            row["target_groups"].append(trow["name"])
            out["target_groups"].append(trow)
            for mname, stat in TG_METRICS_ALB if kind == "application" else TG_METRICS_NLB:
                qid = f"q{qn}"
                qn += 1
                ns_ = "AWS/ApplicationELB" if kind == "application" else "AWS/NetworkELB"
                queries.append(
                    {"Id": qid, "MetricStat": {"Metric": {"Namespace": ns_, "MetricName": mname, "Dimensions": [{"Name": "LoadBalancer", "Value": row["dim"]}, {"Name": "TargetGroup", "Value": trow["dim"]}]}, "Period": 3600, "Stat": stat}}
                )
                qmeta[qid] = ("tg", trow["dim"], f"{mname}_{stat}")
        for mname, stat in LB_METRICS_ALB if kind == "application" else LB_METRICS_NLB:
            qid = f"q{qn}"
            qn += 1
            ns_ = "AWS/ApplicationELB" if kind == "application" else "AWS/NetworkELB"
            queries.append({"Id": qid, "MetricStat": {"Metric": {"Namespace": ns_, "MetricName": mname, "Dimensions": [{"Name": "LoadBalancer", "Value": row["dim"]}]}, "Period": 3600, "Stat": stat}})
            qmeta[qid] = ("lb", row["dim"], f"{mname}_{stat}")
        out["lbs"].append(row)
    # CloudWatch: call in batches of 100
    metrics: dict = {"lb": {}, "tg": {}}
    end = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    start = end - _dt.timedelta(hours=hours)
    tmp = snap / "aws" / "_mdq.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(queries), 100):
        chunk = queries[i : i + 100]
        tmp.write_text(json.dumps(chunk), encoding="utf-8")
        res, r = _aws.aws_json(
            ["cloudwatch", "get-metric-data", "--metric-data-queries", f"file://{tmp}", "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"), "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ")],
            id=f"{collector}.alb.get-metric-data",
            timeout=timeout,
            **kw,
        )
        if res is None:
            errors.append(f"get-metric-data: {r.error or r.stderr.strip()[-200:]}")
            continue
        for mr in res.get("MetricDataResults") or []:
            kind, dim, key = qmeta.get(mr["Id"], (None, None, None))
            if not kind:
                continue
            vals = [float(v) for v in mr.get("Values") or []]
            stat = key.rsplit("_", 1)[1]
            agg = {"points": len(vals), "status": mr.get("StatusCode")}
            if vals:
                agg["sum"] = round(sum(vals), 3)
                agg["max"] = round(max(vals), 4)
                agg["min"] = round(min(vals), 4)
                agg["last"] = round(vals[0], 4)  # newest first (default TimestampDescending)
                if stat in ("p95", "p99", "Average"):
                    agg["avg"] = round(sum(vals) / len(vals), 4)
            metrics[kind].setdefault(dim, {})[key] = agg
        for m in res.get("Messages") or []:
            errors.append(f"get-metric-data message: {m}")
    with contextlib.suppress(OSError):
        tmp.unlink()
    out["metrics"] = metrics
    out["queries"] = len(queries)
    _write(snap, out_rel, out)
    if echo:
        echo(f"    saved {out_rel} (LBs {len(out['lbs'])}, target groups {len(out['target_groups'])}, queries {len(queries)}, errors {len(errors)})")
    return {"ok": not errors or bool(out["lbs"]), "lbs": len(out["lbs"]), "target_groups": len(out["target_groups"]), "queries": len(queries), "errors": errors[:5]}


def _write(snap: Path, out_rel: str, out: dict):
    p = snap / out_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")

"""EKS platform supplement summary: ACM certificates, service quota usage, EBS volume I/O (root and PVC), cluster security group rules, node group AMI age.

Inputs (all read-only results of the eks-platform collector): aws/acm-certificates.json, aws/service-quotas-*.json + aws/cw-quota-usage.json, aws/ec2-volumes.json + aws/ec2-root-volumes.json + aws/cw-ebs-volumes.json,
aws/describe-security-groups.json, aws/describe-nodegroup-*.json. Result: the `eksplatform` section of summary.json. Shape is described in SKILL.md. Other EKS facts (version, add-ons, logging, endpoint) are covered by inventory.cluster.eks and the eks.* inventory checks.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from .snapshot import load_json

QUOTA_WATCH = {  # only the quotas that actually block Kubernetes operations (ENI, EIP, EBS volume count, ALB/NLB count, instance vCPU)
    "L-1216C47A": "on-demand standard instance vCPU",
    "L-34B43A08": "spot standard instance vCPU",
    "L-0263D0A3": "Elastic IP",
    "L-DF5E4CA3": "network interfaces (ENI)",
    "L-F678F1CE": "VPCs",
    "L-53DA6B97": "ALBs",
    "L-69A177A2": "NLBs",
    "L-B22855CB": "target groups",
    "L-7EED9B64": "listener rules per ALB",
    "L-822D1B1B": "target groups per ALB",
    "L-9365A611": "certificates per ALB",
    "L-D18FCD1D": "gp3 storage (TiB)",
    "L-7A658B76": "gp2 storage (TiB)",
    "L-309BACF6": "EBS snapshots",
    "L-0EA8095F": "NAT gateways (per AZ)",
    "L-E79EC296": "internet gateways",
}
WORLD = ("0.0.0.0/0", "::/0")


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _acm(snap: Path, now) -> dict:
    doc = load_json(snap / "aws" / "acm-certificates.json")
    if doc is None:
        return {"available": False}
    rows = []
    for c in doc.get("CertificateSummaryList") or []:
        na = _ts(c.get("NotAfter"))
        rows.append(
            {
                "domain": c.get("DomainName"),
                "sans": len(c.get("SubjectAlternativeNameSummaries") or []),
                "status": c.get("Status"),
                "type": c.get("Type"),
                "in_use": bool(c.get("InUse")),
                "renewal": c.get("RenewalEligibility"),
                "not_after": (c.get("NotAfter") or "")[:10],
                "days_to_expiry": round((na - now).total_seconds() / 86400, 1) if na else None,
                "key": c.get("KeyAlgorithm"),
                "arn_tail": (c.get("CertificateArn") or "")[-12:],
            }
        )
    in_use = [r for r in rows if r["in_use"]]
    return {
        "available": True,
        "certificates": len(rows),
        "in_use": len(in_use),
        "rows": rows,
        "expiring_30d_in_use": [r["domain"] for r in in_use if r["days_to_expiry"] is not None and r["days_to_expiry"] < 30],
        "expiring_14d_in_use": [r["domain"] for r in in_use if r["days_to_expiry"] is not None and r["days_to_expiry"] < 14],
        "expired_in_use": [r["domain"] for r in in_use if r["status"] == "EXPIRED" or (r["days_to_expiry"] is not None and r["days_to_expiry"] <= 0)],
        "not_renewable_in_use": [r["domain"] for r in in_use if r["renewal"] != "ELIGIBLE" and r["type"] == "AMAZON_ISSUED"],
        "imported_in_use": [r["domain"] for r in in_use if r["type"] == "IMPORTED"],
        "expired_unused": [r["domain"] for r in rows if not r["in_use"] and r["status"] == "EXPIRED"],
        "min_days_in_use": min([r["days_to_expiry"] for r in in_use if r["days_to_expiry"] is not None], default=None),
    }


def _quotas(snap: Path) -> dict:
    usage = load_json(snap / "aws" / "cw-quota-usage.json")
    if usage is None:
        return {"available": False}
    rows = []
    for code, mets in (usage.get("items") or {}).items():
        meta = (usage.get("meta") or {}).get(code) or {}
        val = meta.get("value")
        agg = next(iter(mets.values()), {}) if mets else {}
        used = agg.get("max")
        ratio = round(used / val, 3) if (val and used is not None) else None
        rows.append(
            {
                "code": code,
                "service": meta.get("service"),
                "name": meta.get("name"),
                "label": QUOTA_WATCH.get(code),
                "limit": val,
                "unit": meta.get("unit"),
                "used": used,
                "ratio": ratio,
                "adjustable": meta.get("adjustable"),
                "watched": code in QUOTA_WATCH,
            }
        )
    rows.sort(key=lambda r: -(r["ratio"] or 0))
    return {
        "available": True,
        "quotas": len(rows),
        "with_usage": sum(1 for r in rows if r["used"] is not None),
        "rows": rows[:40],
        "near_limit": [f"{r['label'] or r['name']} {r['used']:.0f}/{r['limit']:.0f}" for r in rows if (r["ratio"] or 0) >= 0.8],
        "over_60": [f"{r['label'] or r['name']} {r['ratio']}" for r in rows if (r["ratio"] or 0) >= 0.6],
        "watched_top": [(r["label"], r["used"], r["limit"], r["ratio"]) for r in rows if r["watched"] and r["used"] is not None][:12],
        "max_ratio": max([r["ratio"] for r in rows if r["ratio"] is not None], default=None),
        "max_ratio_name": next((r["label"] or r["name"] for r in rows if r["ratio"] is not None), None),
    }


def _ebs(snap: Path, inv: dict) -> dict:
    cw = load_json(snap / "aws" / "cw-ebs-volumes.json")
    if cw is None:
        return {"available": False}
    vols = {}
    for f, root in (("ec2-volumes.json", False), ("ec2-root-volumes.json", True)):
        for v in load_json(snap / "aws" / f) or []:
            if isinstance(v, dict) and v.get("id"):
                vols[v["id"]] = {**v, "root": root or bool(v.get("root"))}
    inst2node = {str(n.get("provider_id") or "").rsplit("/", 1)[-1]: n["name"] for n in ((inv.get("nodes") or {}).get("nodes") or [])}
    rows = []
    for vid, mets in (cw.get("items") or {}).items():
        v = vols.get(vid, {})
        att = (v.get("attachments") or [{}])[0] if v.get("attachments") else {}
        pvc = next((t.get("Value") for t in (v.get("tags") or []) if t.get("Key") == "kubernetes.io/created-for/pvc/name"), None)
        ns = next((t.get("Value") for t in (v.get("tags") or []) if t.get("Key") == "kubernetes.io/created-for/pvc/namespace"), None)
        q_avg = (mets.get("VolumeQueueLength_Average") or {}).get("max")
        q_max = (mets.get("VolumeQueueLength_Maximum") or {}).get("max")
        ops = ((mets.get("VolumeReadOps_Sum") or {}).get("sum") or 0) + ((mets.get("VolumeWriteOps_Sum") or {}).get("sum") or 0)
        iops_limit = v.get("iops") or (3000 if v.get("type") == "gp3" else None)
        busiest_hour_ops = max(((mets.get("VolumeReadOps_Sum") or {}).get("max") or 0) + ((mets.get("VolumeWriteOps_Sum") or {}).get("max") or 0), 0)
        rows.append(
            {
                "volume": vid,
                "root": v.get("root", False),
                "node": inst2node.get(att.get("instance")),
                "instance": att.get("instance"),
                "pvc": f"{ns}/{pvc}" if pvc else None,
                "type": v.get("type"),
                "size_gb": v.get("size"),
                "iops": iops_limit,
                "throughput": v.get("throughput"),
                "queue_avg_max_1h": q_avg,
                "queue_max": q_max,
                "ops_24h": round(ops),
                "busiest_hour_ops": round(busiest_hour_ops),
                "busiest_hour_iops_ratio": round(busiest_hour_ops / 3600 / iops_limit, 3) if iops_limit else None,
                "burst_balance_min": (mets.get("BurstBalance_Minimum") or {}).get("min"),
                "io_wait_s_24h": round(((mets.get("VolumeTotalReadTime_Sum") or {}).get("sum") or 0) + ((mets.get("VolumeTotalWriteTime_Sum") or {}).get("sum") or 0), 1),
            }
        )
    rows.sort(key=lambda r: -(r["queue_avg_max_1h"] or 0))
    return {
        "available": True,
        "volumes": len(rows),
        "root_volumes": sum(1 for r in rows if r["root"]),
        "rows": rows,
        "queue_high": [f"{r['volume']}({'root ' + str(r['node']) if r['root'] else r['pvc']}) q={r['queue_avg_max_1h']}" for r in rows if (r["queue_avg_max_1h"] or 0) >= 1.0],
        "iops_near_limit": [f"{r['volume']}({'root ' + str(r['node']) if r['root'] else r['pvc']}) {r['busiest_hour_iops_ratio']}" for r in rows if (r["busiest_hour_iops_ratio"] or 0) >= 0.7],
        "burst_low": [f"{r['volume']} {r['burst_balance_min']}%" for r in rows if r["burst_balance_min"] is not None and r["burst_balance_min"] < 20],
        "max_queue": max([r["queue_avg_max_1h"] for r in rows if r["queue_avg_max_1h"] is not None], default=None),
        "max_iops_ratio": max([r["busiest_hour_iops_ratio"] for r in rows if r["busiest_hour_iops_ratio"] is not None], default=None),
    }


def _security_groups(snap: Path, inv: dict) -> dict:
    doc = load_json(snap / "aws" / "describe-security-groups.json")
    if doc is None:
        return {"available": False}
    eks = (inv.get("cluster") or {}).get("eks") or {}
    rows = []
    for g in doc.get("SecurityGroups") or []:
        open_rules = []
        for p in g.get("IpPermissions") or []:
            cidrs = [r.get("CidrIp") for r in p.get("IpRanges") or []] + [r.get("CidrIpv6") for r in p.get("Ipv6Ranges") or []]
            world = [c for c in cidrs if c in WORLD]
            if world:
                fp, tp = p.get("FromPort"), p.get("ToPort")
                open_rules.append({"protocol": p.get("IpProtocol"), "from": fp, "to": tp, "cidrs": world, "all_ports": p.get("IpProtocol") == "-1" or (fp in (None, 0) and tp in (None, 65535)), "https_only": fp == 443 and tp == 443})
        rows.append({"id": g.get("GroupId"), "name": g.get("GroupName"), "ingress_rules": len(g.get("IpPermissions") or []), "open_to_world": open_rules, "open_non_https": [r for r in open_rules if not r["https_only"]]})
    return {
        "available": True,
        "groups": len(rows),
        "rows": rows,
        "open_to_world_count": sum(len(r["open_to_world"]) for r in rows),
        "open_non_https": [f"{r['name']}: {o['protocol']} {o['from']}-{o['to']}" for r in rows for o in r["open_non_https"]],
        "open_all_ports": [r["name"] for r in rows if any(o["all_ports"] for o in r["open_to_world"])],
        "public_endpoint": eks.get("endpoint_public"),
        "public_cidrs": eks.get("public_access_cidrs"),
    }


def _nodegroups(snap: Path, now) -> dict:
    rows = []
    for f in sorted((snap / "aws").glob("describe-nodegroup-*.json")):
        ng = (load_json(f) or {}).get("nodegroup") or {}
        rv = ng.get("releaseVersion") or ""
        m = re.search(r"(\d{8})$", rv)
        rel = _dt.datetime.strptime(m.group(1), "%Y%m%d").replace(tzinfo=_dt.UTC) if m else None
        rows.append(
            {
                "name": ng.get("nodegroupName"),
                "release_version": rv,
                "ami_type": ng.get("amiType"),
                "k8s_version": ng.get("version"),
                "ami_date": rel.date().isoformat() if rel else None,
                "ami_age_days": round((now - rel).total_seconds() / 86400) if rel else None,
                "status": ng.get("status"),
                "health_issues": len((ng.get("health") or {}).get("issues") or []),
                "desired": (ng.get("scalingConfig") or {}).get("desiredSize"),
                "capacity_type": ng.get("capacityType"),
            }
        )
    return {
        "available": bool(rows),
        "nodegroups": len(rows),
        "rows": rows,
        "ami_old_90d": [f"{r['name']} {r['ami_age_days']}d" for r in rows if (r["ami_age_days"] or 0) >= 90],
        "ami_old_180d": [r["name"] for r in rows if (r["ami_age_days"] or 0) >= 180],
        "max_ami_age_days": max([r["ami_age_days"] for r in rows if r["ami_age_days"] is not None], default=None),
        "unhealthy": [r["name"] for r in rows if r["health_issues"]],
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    if not (inv.get("cluster") or {}).get("eks") and not (snap / "aws" / "describe-cluster.json").exists():
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_dt.UTC)
    return {
        "present": True,
        "acm": _acm(snap, now),
        "quotas": _quotas(snap),
        "ebs": _ebs(snap, inv),
        "security_groups": _security_groups(snap, inv),
        "nodegroups": _nodegroups(snap, now),
        "note": "ACM from list-certificates (InUse, NotAfter, RenewalEligibility). Quota usage is the 1-hour maximum from CloudWatch AWS/Usage (only quotas with a usage metric — services ec2, vpc, elasticloadbalancing, ebs). EBS: 24 hours at 1-hour granularity; queue_avg_max_1h = max of the hourly average queue length, busiest_hour_iops_ratio = average IOPS of the busiest hour ÷ provisioned IOPS. Security groups: only 0.0.0.0/0 and ::/0 inbound rules are counted",
    }

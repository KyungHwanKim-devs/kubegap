"""Storage area summary.

Inputs: objects/storageclasses, persistentvolumes, persistentvolumeclaims, csinodes, volumeattachments, volumesnapshots (if present), nodes, pods, statefulsets, deployments,
metrics/pvc_usage_ratio·pvc_inode_ratio·pvc_capacity_bytes·pvc_available_bytes·pvc_growth_bytes_per_day_7d·node_pvc_pods_count, events.json(FailedAttachVolume·FailedMount·ProvisioningFailed·VolumeResizeFailed),
aws/ec2-volumes.json·ec2-volumes-available.json·ec2-snapshots-30d.json(EKS).

Output is the `storage` section of summary.json: classes (per StorageClass: policies, PVC count, number of default classes), pvcs (per PVC: capacity, usage, inodes, growth rate, days until full, consuming workloads), pv (phase, reclaim policy, AZ), attach (per-node attach count/limit, failure events),
ebs (cluster volume types, IOPS, unattached volumes, 30-day snapshots), snapshots (VolumeSnapshot CRD and objects). Shape is documented in SKILL.md.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
from collections import Counter, defaultdict
from pathlib import Path

from .snapshot import load_json, objects

DB_HINT = ("postgres", "mysql", "mariadb", "mongo", "redis", "neo4j", "elastic", "kafka", "minio", "qdrant", "clickhouse", "influx", "etcd", "db", "data")


def _metric(snap: Path, qid: str, keys: tuple[str, ...]) -> dict[tuple, float]:
    out = {}
    m = load_json(snap / "metrics" / f"{qid}.json")
    for s in (m or {}).get("result") or []:
        lab = s.get("metric") or {}
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out[tuple(lab.get(k) for k in keys)] = float(s["value"][1])
    return out


def _q(v) -> float:
    if v is None:
        return 0.0
    s = str(v)
    for u, mul in (("Ki", 1024), ("Mi", 1024**2), ("Gi", 1024**3), ("Ti", 1024**4), ("K", 1e3), ("M", 1e6), ("G", 1e9), ("T", 1e12)):
        if s.endswith(u):
            return float(s[: -len(u)]) * mul
    try:
        return float(s)
    except ValueError:
        return 0.0


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s)) if s else None
    except ValueError:
        return None


def _pvc_users(pods: list[dict]) -> dict[tuple, set]:
    """(namespace, claim) -> workload names that mount the PVC. Reads objects/pods (passed in)."""
    pvc_users: dict[tuple, set] = defaultdict(set)
    for p in pods:
        own = next((x for x in p["metadata"].get("ownerReferences") or []), {})
        wl = f"{own.get('kind', 'Pod').lower()}/{own.get('name', p['metadata']['name'])}"
        if own.get("kind") == "ReplicaSet":
            wl = "deployment/" + own.get("name", "").rsplit("-", 1)[0]
        for v in (p.get("spec") or {}).get("volumes") or []:
            if v.get("persistentVolumeClaim"):
                pvc_users[(p["metadata"]["namespace"], v["persistentVolumeClaim"].get("claimName"))].add(wl)
    return pvc_users


def _classes(scs: list[dict], sc_pvc: Counter, zones: set) -> list[dict]:
    """One row per StorageClass: policies, default flag, PVC count, in-tree provisioner, Immediate binding across several AZs. Reads objects/storageclasses (passed in)."""
    classes = []
    for sc in scs:
        md = sc["metadata"]
        ann = md.get("annotations") or {}
        classes.append(
            {
                "name": md["name"],
                "provisioner": sc.get("provisioner"),
                "reclaim_policy": sc.get("reclaimPolicy") or "Delete",
                "binding_mode": sc.get("volumeBindingMode") or "Immediate",
                "allow_expansion": bool(sc.get("allowVolumeExpansion")),
                "default": ann.get("storageclass.kubernetes.io/is-default-class") == "true" or ann.get("storageclass.beta.kubernetes.io/is-default-class") == "true",
                "parameters": sc.get("parameters") or {},
                "pvcs": sc_pvc.get(md["name"], 0),
                "intree": str(sc.get("provisioner") or "").startswith("kubernetes.io/"),
                "immediate_multi_az": (sc.get("volumeBindingMode") or "Immediate") == "Immediate" and len(zones) > 1 and "ebs" in str(sc.get("provisioner") or ""),
            }
        )
    return classes


def _pvc_rows(snap: Path, pvcs: list[dict], pvs: list[dict], pvc_users: dict[tuple, set], classes: list[dict], prod: set) -> list[dict]:
    """One row per PVC: capacity, usage, inodes, growth and days-to-full, consuming workloads, bound PV's zone and reclaim policy; sorted by usage. Reads metrics/pvc_usage_ratio, pvc_inode_ratio, pvc_capacity_bytes, pvc_available_bytes, pvc_growth_bytes_per_day_7d."""
    pv_by_name = {pv["metadata"]["name"]: pv for pv in pvs}
    key = ("namespace", "persistentvolumeclaim")
    usage, inode, cap, avail, growth = (_metric(snap, q, key) for q in ("pvc_usage_ratio", "pvc_inode_ratio", "pvc_capacity_bytes", "pvc_available_bytes", "pvc_growth_bytes_per_day_7d"))
    sc_prov = {c["name"]: c["provisioner"] for c in classes}
    rows = []
    for c in pvcs:
        md, sp, st = c["metadata"], c.get("spec") or {}, c.get("status") or {}
        ns, name = md["namespace"], md["name"]
        k = (ns, name)
        pv = pv_by_name.get(sp.get("volumeName") or "")
        zone = None
        if pv:
            for t in (((pv.get("spec") or {}).get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
                for e in t.get("matchExpressions") or []:
                    if "zone" in str(e.get("key")) and e.get("values"):
                        zone = e["values"][0]
        g = growth.get(k)
        av = avail.get(k)
        days = round(av / g) if (g and g > 0 and av is not None) else None
        users = sorted(pvc_users.get(k, set()))
        rows.append(
            {
                "namespace": ns,
                "name": name,
                "target": f"{ns}/{name}",
                "prod": ns in prod,
                "phase": st.get("phase"),
                "storage_class": sp.get("storageClassName"),
                "requested_gb": round(_q(((sp.get("resources") or {}).get("requests") or {}).get("storage")) / 1024**3, 1),
                "capacity_gb": round(cap[k] / 1024**3, 1) if k in cap else None,
                "used_ratio": round(usage[k], 3) if k in usage else None,
                "inode_ratio": round(inode[k], 3) if k in inode else None,
                "growth_gb_per_day": round(g / 1024**3, 3) if g is not None else None,
                "days_to_full": days,
                "metrics": k in usage,
                "host_fs": str(sc_prov.get(sp.get("storageClassName")) or "").endswith("local-path"),  # for local-path the kubelet stats report the whole node disk (measured on a k3s: every PVC showed the same capacity and ratio)
                "workloads": users,
                "db_like": any(h in (name + " ".join(users)).lower() for h in DB_HINT),
                "pv": sp.get("volumeName"),
                "zone": zone,
                "reclaim_policy": ((pv or {}).get("spec") or {}).get("persistentVolumeReclaimPolicy"),
                "access_modes": sp.get("accessModes"),
            }
        )
    rows.sort(key=lambda r: -(r["used_ratio"] or 0))
    return rows


def _pv_rows(pvs: list[dict]) -> list[dict]:
    """One row per PV: phase, reclaim policy, capacity, claim, class. Reads objects/persistentvolumes (passed in)."""
    return [
        {
            "name": pv["metadata"]["name"],
            "phase": (pv.get("status") or {}).get("phase"),
            "reclaim_policy": (pv.get("spec") or {}).get("persistentVolumeReclaimPolicy"),
            "capacity_gb": round(_q(((pv.get("spec") or {}).get("capacity") or {}).get("storage")) / 1024**3, 1),
            "claim": f"{((pv.get('spec') or {}).get('claimRef') or {}).get('namespace')}/{((pv.get('spec') or {}).get('claimRef') or {}).get('name')}",
            "storage_class": (pv.get("spec") or {}).get("storageClassName"),
        }
        for pv in pvs
    ]


def _attach(snap: Path) -> dict:
    """Per-node attach count vs CSI limit, VolumeAttachment errors, volume failure events. Reads objects/csinodes.storage.k8s.io, volumeattachments.storage.k8s.io, metrics/node_pvc_pods_count, events.json."""
    limits = {}
    for cn in objects(snap, "csinodes.storage.k8s.io"):
        for dr in (cn.get("spec") or {}).get("drivers") or []:
            if (dr.get("allocatable") or {}).get("count") is not None:
                limits[(cn["metadata"]["name"], dr.get("name"))] = dr["allocatable"]["count"]
    va_by_node: Counter = Counter()
    va_errors = []
    for va in objects(snap, "volumeattachments.storage.k8s.io"):
        n = (va.get("spec") or {}).get("nodeName")
        va_by_node[n] += 1
        if (va.get("status") or {}).get("attachError") or (va.get("status") or {}).get("detachError"):
            va_errors.append(
                {
                    "node": n,
                    "pv": ((va.get("spec") or {}).get("source") or {}).get("persistentVolumeName"),
                    "error": str(((va.get("status") or {}).get("attachError") or (va.get("status") or {}).get("detachError") or {}).get("message"))[:160],
                }
            )
    pvc_pods = _metric(snap, "node_pvc_pods_count", ("node",))
    attach_rows = []
    for (node, driver), lim in limits.items():
        used = va_by_node.get(node, 0)
        attach_rows.append({"node": node, "driver": driver, "limit": lim, "attached": used, "pvc_pods": pvc_pods.get((node,)), "ratio": round(used / lim, 2) if lim else None})
    attach_rows.sort(key=lambda r: -(r["ratio"] or 0))
    ev_counts: Counter = Counter()
    ev_samples: dict = {}
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        r = e.get("reason")
        if r in ("FailedAttachVolume", "FailedMount", "ProvisioningFailed", "VolumeResizeFailed", "FailedBinding", "VolumeFailedDelete"):
            ev_counts[r] += int(e.get("count") or 1)
            ev_samples.setdefault(r, f"{(e.get('involvedObject') or {}).get('namespace')}/{(e.get('involvedObject') or {}).get('name')}: {(e.get('message') or '')[:140]}")
    return {
        "nodes": attach_rows,
        "errors": va_errors,
        "events": dict(ev_counts),
        "event_samples": ev_samples,
        "volumeattachments": sum(va_by_node.values()),
        "near_limit": [r["node"] for r in attach_rows if (r["ratio"] or 0) >= 0.6],
    }


def _ebs(snap: Path, now: _dt.datetime) -> dict:
    """EKS EBS volumes: types, encryption, IOPS above default, unattached volumes and their cost, 30-day snapshots. Reads aws/ec2-volumes.json, ec2-volumes-available.json, ec2-snapshots-30d.json; {available: False} without them."""
    vols = load_json(snap / "aws" / "ec2-volumes.json")
    if not isinstance(vols, list):
        return {"available": False}
    unattached = [v for v in (load_json(snap / "aws" / "ec2-volumes-available.json") or []) if isinstance(v, dict)]
    snaps = [s for s in (load_json(snap / "aws" / "ec2-snapshots-30d.json") or []) if isinstance(s, dict)]

    def age_days(s):
        t = _ts(s)
        return round((now - t).total_seconds() / 86400) if t else None

    def tag(v, k):
        return next((t.get("Value") for t in (v.get("tags") or []) if t.get("Key") == k), None)

    return {
        "available": True,
        "source": "aws/ec2-volumes.json",
        "volumes": len(vols),
        "by_type": dict(Counter(v.get("type") for v in vols)),
        "by_state": dict(Counter(v.get("state") for v in vols)),
        "gb_total": sum(v.get("size") or 0 for v in vols),
        "gp2": [{"id": v["id"], "size_gb": v.get("size"), "pvc": tag(v, "kubernetes.io/created-for/pvc/name"), "namespace": tag(v, "kubernetes.io/created-for/pvc/namespace")} for v in vols if v.get("type") == "gp2"],
        "unencrypted": [v["id"] for v in vols if v.get("encrypted") is False],
        "iops_above_default": [{"id": v["id"], "iops": v.get("iops"), "throughput": v.get("throughput"), "pvc": tag(v, "kubernetes.io/created-for/pvc/name")} for v in vols if (v.get("iops") or 0) > 3000 or (v.get("throughput") or 0) > 125],
        "unattached": [
            {
                "id": v["id"],
                "size_gb": v.get("size"),
                "type": v.get("type"),
                "age_days": age_days(v.get("created")),
                "az": v.get("az"),
                "name": tag(v, "Name") or tag(v, "kubernetes.io/created-for/pv/name"),
                "cluster": tag(v, "KubernetesCluster"),
            }
            for v in unattached
        ],
        "unattached_gb": sum(v.get("size") or 0 for v in unattached),
        "unattached_monthly_usd_est": round(sum(v.get("size") or 0 for v in unattached) * 0.0912, 2),
        "snapshots_30d": len(snaps),
        "snapshots_30d_gb": sum(s.get("size") or 0 for s in snaps),
        "snapshot_descriptions": dict(Counter((s.get("description") or "")[:40] for s in snaps).most_common(5)),
        "snapshot_latest": max((s.get("start") or "" for s in snaps), default=None),
        "snapshotted_volumes": len({s.get("volume") for s in snaps}),
    }


def _snapshots(snap: Path, now: _dt.datetime, ebs: dict, pvcs: list[dict], rows: list[dict], prod_delete: list[str], platform: str | None) -> dict:
    """CSI VolumeSnapshot CRD/objects/classes plus the EBS snapshot counts, and prod DB PVCs with no snapshot path at all. Reads objects/volumesnapshots.snapshot.storage.k8s.io, volumesnapshotclasses.snapshot.storage.k8s.io, customresourcedefinitions."""
    vs = objects(snap, "volumesnapshots.snapshot.storage.k8s.io")
    crds = {c["metadata"]["name"] for c in objects(snap, "customresourcedefinitions")}
    return {
        "volumesnapshot_crd": "volumesnapshots.snapshot.storage.k8s.io" in crds,
        "volumesnapshots": len(vs),
        "volumesnapshotclasses": len(objects(snap, "volumesnapshotclasses.snapshot.storage.k8s.io")),
        "recent_7d": sum(1 for v in vs if (_ts(v["metadata"].get("creationTimestamp")) or now - _dt.timedelta(days=99)) > now - _dt.timedelta(days=7)),
        "ebs_snapshots_30d": ebs.get("snapshots_30d") if ebs.get("available") else None,
        "ebs_snapshot_descriptions": ebs.get("snapshot_descriptions") if ebs.get("available") else None,
        "pvcs_total": len(pvcs),
        "prod_pvcs": sum(1 for r in rows if r["prod"]),
        "prod_db_pvcs_without_snapshot_path": prod_delete if not vs and not (ebs.get("snapshots_30d") or 0) else [],
        "platform": platform,
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    platform = (inv.get("cluster") or {}).get("platform")
    now = _dt.datetime.now(_dt.UTC)
    pvcs = objects(snap, "persistentvolumeclaims")
    pvs = objects(snap, "persistentvolumes")
    scs = objects(snap, "storageclasses")
    pods = objects(snap, "pods")
    nodes = objects(snap, "nodes")
    zones = {z for n in nodes for z in [(n["metadata"].get("labels") or {}).get("topology.kubernetes.io/zone")] if z}
    sc_pvc = Counter((c.get("spec") or {}).get("storageClassName") for c in pvcs)
    classes = _classes(scs, sc_pvc, zones)
    rows = _pvc_rows(snap, pvcs, pvs, _pvc_users(pods), classes, prod)
    pv_rows = _pv_rows(pvs)
    prod_delete = [r["target"] for r in rows if r["prod"] and r["reclaim_policy"] == "Delete" and r["db_like"]]
    ebs = _ebs(snap, now)
    return {
        "classes": {
            "rows": classes,
            "count": len(classes),
            "default_count": sum(1 for c in classes if c["default"]),
            "default": [c["name"] for c in classes if c["default"]],
            "intree": [c["name"] for c in classes if c["intree"]],
            "no_expansion": [c["name"] for c in classes if not c["allow_expansion"] and c["pvcs"] > 0],
            "immediate_multi_az": [c["name"] for c in classes if c["immediate_multi_az"]],
            "zones": sorted(zones),
        },
        "pvcs": {
            "count": len(rows),
            "with_metrics": sum(1 for r in rows if r["metrics"]),
            "rows": rows,
            "high_usage": [r["target"] for r in rows if (r["used_ratio"] or 0) >= 0.75 and not r["host_fs"]],
            "filling": [r for r in rows if r["days_to_full"] is not None and r["days_to_full"] <= 45 and not r["host_fs"]],
            "unbound": [r["target"] for r in rows if r["phase"] != "Bound"],
            "prod_db_delete_reclaim": prod_delete,
            "by_class": dict(sc_pvc),
        },
        "pv": {
            "count": len(pv_rows),
            "by_phase": dict(Counter(r["phase"] for r in pv_rows)),
            "by_reclaim": dict(Counter(r["reclaim_policy"] for r in pv_rows)),
            "released": [r for r in pv_rows if r["phase"] in ("Released", "Failed")],
            "gb_total": round(sum(r["capacity_gb"] for r in pv_rows), 1),
        },
        "attach": _attach(snap),
        "ebs": ebs,
        "snapshots": _snapshots(snap, now, ebs, pvcs, rows, prod_delete, platform),
    }

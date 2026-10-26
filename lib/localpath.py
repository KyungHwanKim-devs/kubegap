"""local-path-provisioner summary (collectors/local-path-provisioner).

Inputs: summary.k3s.cluster.local_path (per PV: node, capacity, actual usage (du), workload; per-node directory totals; over-capacity list — from the node script's local-path section), summary.k3s.nodes[].local_path.volumes (node directory list),
objects (storageclasses, persistentvolumes, persistentvolumeclaims, configmaps local-path-config, deployments local-path-provisioner), metrics/localpath_*.json (node root filesystem free/size and 7-day trend).
What we look at: node-pinned PVs and over-capacity (the declared capacity is not a limit), orphan directories that exist on the node without a PV (leftovers of deleted PVCs — reclaimPolicy Retain or teardown failure), StorageClass reclaimPolicy, default class and nodePathMap paths,
root filesystem free space and days until full, provisioner Deployment status/version. Output: the `local_path` section of summary.json. Shape documented in SKILL.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .snapshot import load_json, objects


def _rows(snap: Path, qid: str) -> list[dict]:
    d = load_json(snap / "metrics" / f"{qid}.json") or {}
    return d.get("result", []) if d.get("ok") else []


def _v(row) -> float | None:
    try:
        return float(row["value"][1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def analyze(snap: Path, inv: dict | None, k3s: dict | None) -> dict:
    inv = inv or {}
    k3s = k3s or {}
    lp = ((k3s.get("cluster") or {}).get("local_path")) or {}
    scs = [s for s in objects(snap, "storageclasses") if s.get("provisioner") == "rancher.io/local-path"]
    dep = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] == "local-path-provisioner"), None)
    if not scs and not dep and not lp:
        return {"present": False}
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    ip2node = {(n.get("internal_ip") or n.get("ip") or ""): n["name"] for n in ((inv.get("nodes") or {}).get("nodes") or [])}

    def node_of(inst):
        return ip2node.get((inst or "").split(":")[0], inst)

    # --- provisioner and config
    prov = {"present": False}
    if dep:
        sp, st = dep.get("spec") or {}, dep.get("status") or {}
        c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
        prov = {"present": True, "namespace": dep["metadata"]["namespace"], "replicas": sp.get("replicas"), "ready": st.get("readyReplicas") or 0, "version": _ver(c0.get("image")), "image": (c0.get("image") or "").split("/")[-1]}
    cm = next((c for c in objects(snap, "configmaps") if c["metadata"]["name"] == "local-path-config"), None)
    paths: dict[str, list[str]] = {}
    if cm:
        try:
            for e in json.loads((cm.get("data") or {}).get("config.json") or "{}").get("nodePathMap") or []:
                paths[e.get("node")] = e.get("paths") or []
        except json.JSONDecodeError:
            pass
    sc_rows = [
        {
            "name": s["metadata"]["name"],
            "reclaim": s.get("reclaimPolicy"),
            "binding": s.get("volumeBindingMode"),
            "default": (s["metadata"].get("annotations") or {}).get("storageclass.kubernetes.io/is-default-class") == "true",
            "path": (s.get("parameters") or {}).get("path"),
            "node_path": (s.get("parameters") or {}).get("nodePath"),
        }
        for s in scs
    ]
    # --- PV·PVC
    pvs = [p for p in objects(snap, "persistentvolumes") if (p.get("spec") or {}).get("storageClassName") in {s["name"] for s in sc_rows} or "rancher.io/local-path" in json.dumps((p.get("metadata") or {}).get("annotations") or {})]
    pv_rows = []
    for p in pvs:
        sp, st = p.get("spec") or {}, p.get("status") or {}
        ref = sp.get("claimRef") or {}
        path = ((sp.get("hostPath") or {}).get("path")) or ((sp.get("local") or {}).get("path"))
        node = None
        for term in ((sp.get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
            for me in term.get("matchExpressions") or []:
                if me.get("key") == "kubernetes.io/hostname" and me.get("values"):
                    node = me["values"][0]
        pv_rows.append(
            {
                "pv": p["metadata"]["name"],
                "namespace": ref.get("namespace"),
                "pvc": ref.get("name"),
                "node": node,
                "path": path,
                "reclaim": sp.get("persistentVolumeReclaimPolicy"),
                "phase": st.get("phase"),
                "capacity": (sp.get("capacity") or {}).get("storage"),
                "prod": ref.get("namespace") in prod,
                "storage_class": sp.get("storageClassName"),
            }
        )
    released = [r for r in pv_rows if r["phase"] in ("Released", "Failed")]
    # --- orphan directories: present in the node directory list (du) but without a PV
    pv_names = {r["pv"] for r in pv_rows}
    orphan = []
    node_dirs: dict[str, int] = {}
    for rec in k3s.get("nodes") or []:
        vols = (rec.get("local_path") or {}).get("volumes") or []
        node_dirs[rec.get("node")] = len(vols)
        for v in vols:
            if v.get("pv") and v["pv"] not in pv_names:
                orphan.append({"node": rec.get("node"), "dir": f"{v['pv']}_{v.get('namespace')}_{v.get('pvc')}", "namespace": v.get("namespace"), "pvc": v.get("pvc"), "mb": v.get("mb")})
    # --- filesystem free space
    fs = {}
    for r in _rows(snap, "localpath_fs_avail_ratio"):
        fs.setdefault(node_of(r["metric"].get("instance")), {})["avail_ratio"] = round(_v(r) or 0, 3)
    for r in _rows(snap, "localpath_fs_size_bytes"):
        fs.setdefault(node_of(r["metric"].get("instance")), {})["size_gib"] = round((_v(r) or 0) / 1024**3, 1)
    for r in _rows(snap, "localpath_fs_growth_bytes_per_day"):
        fs.setdefault(node_of(r["metric"].get("instance")), {})["growth_gib_per_day"] = round((_v(r) or 0) / 1024**3, 2)
    for n, d in fs.items():
        avail_gib = (d.get("size_gib") or 0) * (d.get("avail_ratio") or 0)
        g = d.get("growth_gib_per_day") or 0
        d["avail_gib"] = round(avail_gib, 1)
        d["days_to_full"] = round(avail_gib / g) if g > 0.01 else None
        d["volumes_gib"] = round(((lp.get("node_total_mb") or {}).get(n) or 0) / 1024, 1)
    over = lp.get("over_capacity") or []
    pinned = lp.get("pinned") or []
    summary = {
        "present": True,
        "provisioner_ready": prov.get("ready"),
        "provisioner_replicas": prov.get("replicas"),
        "provisioner_version": prov.get("version"),
        "node_path_map": paths,
        "storage_classes": [s["name"] for s in sc_rows],
        "default_class": next((s["name"] for s in sc_rows if s["default"]), None),
        "reclaim_policies": {s["name"]: s["reclaim"] for s in sc_rows},
        "pv_count": lp.get("pv_count") or len(pv_rows),
        "by_node": lp.get("by_node") or {},
        "node_total_mb": lp.get("node_total_mb") or {},
        "pinned": pinned,
        "over_capacity": over,
        "over_capacity_count": len(over),
        "released": [f"{r['pv']}({r['namespace']}/{r['pvc']})" for r in released],
        "orphan_dirs": orphan,
        "orphan_mb": sum(o.get("mb") or 0 for o in orphan),
        "node_dirs": node_dirs,
        "prod_pvs_delete_reclaim": [f"{r['namespace']}/{r['pvc']}" for r in pv_rows if r["prod"] and r["reclaim"] == "Delete"],
        "prod_pvs": sum(1 for r in pv_rows if r["prod"]),
        "fs": fs,
        "fs_min_avail_ratio": min([d.get("avail_ratio") for d in fs.values() if d.get("avail_ratio") is not None], default=None),
        "fs_min_days_to_full": min([d["days_to_full"] for d in fs.values() if d.get("days_to_full") is not None], default=None),
        "fs_nodes_low": [n for n, d in fs.items() if (d.get("avail_ratio") or 1) < 0.2],
        "metrics_available": bool(fs),
    }
    return {
        "present": True,
        "provisioner": prov,
        "storage_classes": sc_rows,
        "pvs": pv_rows,
        "over_capacity": over,
        "summary": summary,
        "note": "local-path volumes are plain directories, so PVC capacity is not a limit (du usage can exceed it). Directory usage and orphan directories come from the node script's (SSH) du list (top 30). Filesystem free space comes from node-exporter",
    }

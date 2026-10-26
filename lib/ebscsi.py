"""EBS CSI driver summary (collector collectors/ebs-csi).

Attach limits, VolumeAttachment counts, EBS volumes and snapshots belong to the storage section (lib/storage.py). Here we look at the driver itself:
the controller Deployment (replicas, sidecar versions, --batching, timeout, metrics enabled), the node DaemonSet, the ServiceAccount's IRSA/Pod Identity, add-on version, CSIDriver settings,
VolumeAttachments that have stayed unattached for a long time and attach/detach errors, StorageClasses (ebs provisioner) encryption/expansion/binding, kubelet CSI call success rate and p99 (metrics/ebscsi_*.json).

Inputs: objects/deployments, daemonsets, serviceaccounts, csidrivers, volumeattachments, storageclasses, persistentvolumes, persistentvolumeclaims, aws/describe-addon-aws-ebs-csi-driver.json, pod-identity-associations.json,
metrics/ebscsi_*.json, events.json (FailedAttachVolume, FailedMount, VolumeResizeFailed and the like), inventory.
Result: the `ebscsi` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import math
import re
from collections import Counter
from pathlib import Path

from .snapshot import load_json, objects


def _rows(snap: Path, qid: str) -> list[tuple[dict, float]]:
    out = []
    for s in (load_json(snap / "metrics" / f"{qid}.json") or {}).get("result") or []:
        try:
            v = float(s["value"][1])
            if math.isnan(v) or math.isinf(v):
                continue
            out.append((s.get("metric") or {}, v))
        except (KeyError, ValueError, TypeError, IndexError):
            pass
    return out


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _controller(snap: Path, ctrl: dict | None) -> dict:
    """Controller Deployment: replicas, sidecar versions/timeouts, --batching, metrics flag, placement of its pods. Reads objects/deployments (passed in) and objects/pods."""
    controller = {"present": ctrl is not None}
    if not ctrl:
        return controller
    sp, st = ctrl.get("spec") or {}, ctrl.get("status") or {}
    tpl = (sp.get("template") or {}).get("spec") or {}
    sidecars = {}
    plugin_args: list[str] = []
    for c in tpl.get("containers") or []:
        sidecars[c["name"]] = {"version": _ver(c.get("image")), "args": [a for a in (c.get("args") or []) if any(k in a for k in ("timeout", "leader", "batching", "metrics", "worker", "retry", "kube-api", "modify", "feature"))]}
        if c["name"] == "ebs-plugin":
            plugin_args = [str(a) for a in (c.get("args") or [])]
    timeouts = {n: next((a.split("=", 1)[1] for a in v["args"] if a.startswith("--timeout=")), None) for n, v in sidecars.items() if n.startswith("csi-")}
    controller.update(
        {
            "replicas": sp.get("replicas"),
            "ready": st.get("readyReplicas") or 0,
            "available": st.get("availableReplicas") or 0,
            "service_account": tpl.get("serviceAccountName"),
            "version": _ver(next((c.get("image") for c in tpl.get("containers") or [] if c["name"] == "ebs-plugin"), None)),
            "sidecars": sidecars,
            "sidecar_timeouts": timeouts,
            "batching": any(a == "--batching=true" for a in plugin_args),
            "metrics_flag": any("metrics" in a for a in plugin_args),
            "plugin_args": plugin_args[:12],
            "priority_class": tpl.get("priorityClassName"),
            "anti_affinity": bool((tpl.get("affinity") or {}).get("podAntiAffinity")),
            "pods_by_node": {},
        }
    )
    sel = (sp.get("selector") or {}).get("matchLabels") or {}
    for p in objects(snap, "pods"):
        if p["metadata"]["namespace"] == ctrl["metadata"]["namespace"] and all((p["metadata"].get("labels") or {}).get(k) == v for k, v in sel.items()) and (p.get("status") or {}).get("phase") == "Running":
            nd = p["spec"].get("nodeName")
            controller["pods_by_node"][nd] = controller["pods_by_node"].get(nd, 0) + 1
    controller["all_same_node"] = (controller["replicas"] or 0) >= 2 and len(controller["pods_by_node"]) == 1
    return controller


def _node(node_ds: dict | None) -> dict:
    """Node DaemonSet: desired/ready, plugin version, attach-limit arguments. Reads objects/daemonsets (passed in)."""
    node = {"present": node_ds is not None}
    if not node_ds:
        return node
    st = node_ds.get("status") or {}
    args = [str(a) for c in (node_ds["spec"]["template"]["spec"].get("containers") or []) for a in (c.get("args") or [])]
    node.update(
        {
            "desired": st.get("desiredNumberScheduled"),
            "ready": st.get("numberReady"),
            "version": _ver(next((c.get("image") for c in node_ds["spec"]["template"]["spec"].get("containers") or [] if c["name"] == "ebs-plugin"), None)),
            "volume_attach_limit_arg": next((a.split("=", 1)[1] for a in args if a.startswith("--volume-attach-limit=")), None),
            "reserved_volume_attachments_arg": next((a.split("=", 1)[1] for a in args if a.startswith("--reserved-volume-attachments=")), None),
        }
    )
    return node


def _addon(snap: Path) -> tuple[dict, str | None]:
    """(EKS add-on record, latest available add-on version). Reads aws/describe-addon-aws-ebs-csi-driver.json and describe-addon-versions-aws-ebs-csi-driver.json."""
    addon = (load_json(snap / "aws" / "describe-addon-aws-ebs-csi-driver.json") or {}).get("addon") or {}
    latest = None
    with contextlib.suppress(IndexError, AttributeError):
        latest = (((load_json(snap / "aws" / "describe-addon-versions-aws-ebs-csi-driver.json") or {}).get("addons") or [{}])[0].get("addonVersions") or [{}])[0].get("addonVersion")
    return addon, latest


def _credentials(snap: Path, controller: dict, addon: dict) -> dict:
    """Controller credentials: IRSA annotation, Pod Identity association, add-on role. Reads objects/serviceaccounts and aws/pod-identity-associations.json."""
    sa_name = controller.get("service_account") or "ebs-csi-controller-sa"
    sa = next((s for s in objects(snap, "serviceaccounts") if s["metadata"]["namespace"] == "kube-system" and s["metadata"]["name"] == sa_name), None)
    irsa = ((sa or {}).get("metadata") or {}).get("annotations", {}).get("eks.amazonaws.com/role-arn")
    pia = load_json(snap / "aws" / "pod-identity-associations.json") or {}
    pod_identity = any(a.get("serviceAccount") == sa_name and a.get("namespace") == "kube-system" for a in (pia.get("associations") or []))
    return {
        "service_account": sa_name,
        "irsa_role": irsa,
        "pod_identity": pod_identity,
        "addon_sa_role": addon.get("serviceAccountRoleArn"),
        "has_dedicated_role": bool(irsa or pod_identity or addon.get("serviceAccountRoleArn")),
        "note": "Without a dedicated role the controller uses the node instance role's EC2 permissions — every pod on the node shares them (together with the IMDS hop)",
    }


def _csidriver(driver: dict | None) -> dict:
    """CSIDriver object settings (attachRequired, fsGroupPolicy, ...). Reads objects/csidrivers.storage.k8s.io (passed in)."""
    drv = {"present": driver is not None}
    if driver:
        sp = driver.get("spec") or {}
        drv.update(
            {
                "attach_required": sp.get("attachRequired"),
                "fs_group_policy": sp.get("fsGroupPolicy"),
                "pod_info_on_mount": sp.get("podInfoOnMount"),
                "storage_capacity": sp.get("storageCapacity"),
                "volume_lifecycle_modes": sp.get("volumeLifecycleModes"),
                "selinux_mount": sp.get("seLinuxMount"),
            }
        )
    return drv


def _volume_attachments(snap: Path, inv: dict, now: _dt.datetime) -> dict:
    """EBS VolumeAttachments: rows, those stuck unattached or in error, orphans whose PV or node is gone. Reads objects/volumeattachments.storage.k8s.io, persistentvolumes and inventory nodes."""
    vas = [v for v in objects(snap, "volumeattachments.storage.k8s.io") if (v.get("spec") or {}).get("attacher") == "ebs.csi.aws.com"]
    pv_names = {p["metadata"]["name"] for p in objects(snap, "persistentvolumes")}
    node_names = {n["name"] for n in (inv.get("nodes") or {}).get("nodes") or []}
    va_rows = []
    for v in vas:
        st = v.get("status") or {}
        created = _ts(v["metadata"].get("creationTimestamp"))
        age_min = round((now - created).total_seconds() / 60, 1) if created else None
        pv = ((v.get("spec") or {}).get("source") or {}).get("persistentVolumeName")
        err = (st.get("attachError") or {}).get("message") or (st.get("detachError") or {}).get("message")
        va_rows.append(
            {
                "name": v["metadata"]["name"],
                "node": (v.get("spec") or {}).get("nodeName"),
                "pv": pv,
                "attached": bool(st.get("attached")),
                "age_min": age_min,
                "error": (err or "")[:200] or None,
                "pv_missing": pv not in pv_names if pv else None,
                "node_missing": (v.get("spec") or {}).get("nodeName") not in node_names,
                "deleting": bool(v["metadata"].get("deletionTimestamp")),
            }
        )
    stuck = [r for r in va_rows if (not r["attached"] and (r["age_min"] or 0) >= 10) or r["error"]]
    orphan = [r for r in va_rows if r["pv_missing"] or r["node_missing"]]
    return {"count": len(va_rows), "rows": va_rows[:40], "stuck": stuck, "orphan": orphan}


def _storage_classes(snap: Path) -> list[dict]:
    """StorageClasses with the EBS provisioner: type, encryption, IOPS/throughput, expansion, binding mode. Reads objects/storageclasses."""
    classes = []
    for sc in objects(snap, "storageclasses"):
        prov = sc.get("provisioner")
        if prov not in ("ebs.csi.aws.com", "kubernetes.io/aws-ebs"):
            continue
        params = sc.get("parameters") or {}
        classes.append(
            {
                "name": sc["metadata"]["name"],
                "provisioner": prov,
                "default": (sc["metadata"].get("annotations") or {}).get("storageclass.kubernetes.io/is-default-class") == "true",
                "type": params.get("type"),
                "encrypted": str(params.get("encrypted", "")).lower() == "true",
                "kms_key": params.get("kmsKeyId"),
                "iops": params.get("iops"),
                "throughput": params.get("throughput"),
                "allow_expansion": bool(sc.get("allowVolumeExpansion")),
                "binding_mode": sc.get("volumeBindingMode"),
                "reclaim": sc.get("reclaimPolicy"),
                "intree": prov == "kubernetes.io/aws-ebs",
            }
        )
    return classes


def _metrics(snap: Path) -> dict:
    """kubelet CSI call success/p99, controller storage ops, API errors/throttles. Reads metrics/ebscsi_*.json."""
    ops = {}
    for lab, v in _rows(snap, "ebscsi_node_ops_by_status_24h"):
        m = (lab.get("method_name") or "").split("/")[-1]
        d = ops.setdefault(m, {"ok": 0, "errors": 0, "by_code": {}})
        if lab.get("grpc_status_code") == "OK":
            d["ok"] += int(v)
        else:
            d["errors"] += int(v)
            d["by_code"][lab.get("grpc_status_code")] = d["by_code"].get(lab.get("grpc_status_code"), 0) + int(v)
    p99 = {(lab.get("method_name") or "").split("/")[-1]: round(v, 2) for lab, v in _rows(snap, "ebscsi_node_ops_p99_24h")}
    sops = {}
    for lab, v in _rows(snap, "ebscsi_storage_ops_by_status_24h"):
        d = sops.setdefault(lab.get("operation_name"), {})
        d[lab.get("status")] = d.get(lab.get("status"), 0) + int(v)
    sp99 = {lab.get("operation_name"): round(v, 2) for lab, v in _rows(snap, "ebscsi_storage_ops_p99_24h")}
    ctrl_series = _rows(snap, "ebscsi_controller_metrics_series")
    ctrl_metrics = int(ctrl_series[0][1]) if ctrl_series else 0
    api_err = {lab.get("request"): round(v) for lab, v in _rows(snap, "ebscsi_api_errors_24h") if v > 0}
    thr = _rows(snap, "ebscsi_api_throttles_24h")
    return {
        "kubelet_available": bool(ops or sops),
        "node_ops_24h": ops,
        "node_ops_errors_24h": sum(d["errors"] for d in ops.values()),
        "node_ops_p99_s": p99,
        "stage_p99_s": p99.get("NodeStageVolume"),
        "publish_p99_s": p99.get("NodePublishVolume"),
        "storage_ops_24h": sops,
        "storage_ops_failures_24h": sum(v for d in sops.values() for k, v in d.items() if k != "success"),
        "storage_ops_p99_s": sp99,
        "controller_metrics_enabled": ctrl_metrics > 0,
        "controller_metrics_series": ctrl_metrics,
        "api_errors_24h": api_err,
        "api_throttles_24h": round(thr[0][1]) if thr else None,
    }


def _events(snap: Path) -> Counter:
    """Volume-related failure event counts (FailedAttachVolume, FailedMount, ...). Reads events.json."""
    ev_counts: Counter = Counter()
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        r = e.get("reason") or ""
        if r in ("FailedAttachVolume", "FailedMount", "FailedMapVolume", "VolumeResizeFailed", "FileSystemResizeFailed", "ProvisioningFailed", "VolumeFailedDelete", "FailedDetachVolume", "ExternalExpanding"):
            ev_counts[r] += int(e.get("count") or 1)
    return ev_counts


def _summary(controller: dict, node: dict, windows: dict | None, credentials: dict, drv: dict, va: dict, classes: list[dict], metrics: dict, ev_counts: Counter, addon: dict, latest: str | None) -> dict:
    """Flat summary row the checks read; assembled from the other helpers' results (reads nothing)."""
    return {
        "present": True,
        "version": controller.get("version") or node.get("version"),
        "addon_version": addon.get("addonVersion"),
        "addon_latest": latest,
        "addon_managed": bool(addon),
        "controller_replicas": controller.get("replicas"),
        "controller_ready": controller.get("ready"),
        "controller_all_same_node": controller.get("all_same_node", False),
        "controller_present": controller["present"],
        "node_desired": node.get("desired"),
        "node_ready": node.get("ready"),
        "windows_daemonset_desired": ((windows or {}).get("status") or {}).get("desiredNumberScheduled") if windows else None,
        "has_dedicated_role": credentials["has_dedicated_role"],
        "irsa_role": credentials["irsa_role"],
        "pod_identity": credentials["pod_identity"],
        "batching": controller.get("batching"),
        "sidecar_timeouts": controller.get("sidecar_timeouts"),
        "volume_attachments": va["count"],
        "va_stuck": [r["name"] for r in va["stuck"]],
        "va_stuck_detail": va["stuck"][:6],
        "va_orphan": [r["name"] for r in va["orphan"]],
        "classes": len(classes),
        "classes_unencrypted": [c["name"] for c in classes if not c["encrypted"] and not c["intree"]],
        "classes_no_expansion": [c["name"] for c in classes if not c["allow_expansion"]],
        "classes_intree": [c["name"] for c in classes if c["intree"]],
        "default_class": next((c["name"] for c in classes if c["default"]), None),
        "kubelet_metrics_available": metrics["kubelet_available"],
        "node_ops_errors_24h": metrics["node_ops_errors_24h"],
        "node_ops_errors_detail": {m: d["by_code"] for m, d in metrics["node_ops_24h"].items() if d["errors"]},
        "stage_p99_s": metrics["stage_p99_s"],
        "publish_p99_s": metrics["publish_p99_s"],
        "storage_ops_failures_24h": metrics["storage_ops_failures_24h"],
        "controller_metrics_enabled": metrics["controller_metrics_enabled"],
        "api_errors_24h": metrics["api_errors_24h"],
        "api_throttles_24h": metrics["api_throttles_24h"],
        "events_24h": dict(ev_counts),
        "events_failures_24h": sum(ev_counts.values()),
        "fs_group_policy": drv.get("fs_group_policy"),
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    ctrl = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] == "ebs-csi-controller"), None)
    node_ds = next((d for d in objects(snap, "daemonsets") if d["metadata"]["name"] == "ebs-csi-node"), None)
    driver = next((c for c in objects(snap, "csidrivers.storage.k8s.io") if c["metadata"]["name"] == "ebs.csi.aws.com"), None)
    if not (ctrl or node_ds or driver):
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    controller = _controller(snap, ctrl)
    node = _node(node_ds)
    windows = next((d for d in objects(snap, "daemonsets") if d["metadata"]["name"] == "ebs-csi-node-windows"), None)
    addon, latest = _addon(snap)
    credentials = _credentials(snap, controller, addon)
    drv = _csidriver(driver)
    va = _volume_attachments(snap, inv, now)
    classes = _storage_classes(snap)
    metrics = _metrics(snap)
    ev_counts = _events(snap)
    return {
        "present": True,
        "controller": controller,
        "node": node,
        "credentials": credentials,
        "csidriver": drv,
        "volume_attachments": va,
        "storage_classes": classes,
        "metrics": metrics,
        "events_24h": dict(ev_counts),
        "summary": _summary(controller, node, windows, credentials, drv, va, classes, metrics, ev_counts, addon, latest),
    }

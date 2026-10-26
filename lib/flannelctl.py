"""flannel summary (collector collectors/flannel).

Inputs: summary.k3s (per-node flannel section: mtu, underlying NIC mtu, vxlan local ip/dev, RX/TX errors/dropped, ip_forward, br_netfilter, addrs; cluster podcidr), metrics/flannel_*.json (node-exporter interface counters: 24-hour increase, up, mtu, overlay bytes),
objects/nodes.json (podCIDR, internal IP). What we look at: MTU consistency (underlying − 50), interface errors/drops (cumulative and 24-hour increase), sysctl (ip_forward, br_netfilter), whether nodes share one L2 subnet (vxlan is unencrypted — crossing subnets or public networks calls for the WireGuard backend),
podCIDR usage, nodes whose flannel data could not be read. Result: the `flannel` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import contextlib
import ipaddress
from pathlib import Path

from .snapshot import load_json


def _rows(snap: Path, qid: str) -> list[dict]:
    d = load_json(snap / "metrics" / f"{qid}.json") or {}
    return d.get("result", []) if d.get("ok") else []


def _v(row) -> float | None:
    try:
        return float(row["value"][1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _node_by_instance(inv: dict) -> dict:
    out = {}
    for n in (inv.get("nodes") or {}).get("nodes") or []:
        ip = n.get("internal_ip") or n.get("ip")
        if ip:
            out[ip] = n["name"]
    return out


def analyze(snap: Path, inv: dict | None, k3s: dict | None) -> dict:
    inv = inv or {}
    k3s = k3s or {}
    recs = k3s.get("nodes") or []
    if not isinstance(recs, list):
        recs = list(recs.values())
    cluster = k3s.get("cluster") or {}
    if not recs and not (inv.get("components") or {}).get("flannel", {}).get("present"):
        return {"present": False}
    ip2node = _node_by_instance(inv)

    def node_of(inst: str) -> str:
        return ip2node.get((inst or "").split(":")[0], inst)

    # --- node-exporter counters (24-hour increase)
    errs_1d: dict[str, dict[str, int]] = {}
    drops_1d: dict[str, dict[str, int]] = {}
    up: dict[str, int] = {}
    mtu_ne: dict[str, int] = {}
    overlay_bytes: dict[str, int] = {}
    for r in _rows(snap, "flannel_if_errors_1d"):
        errs_1d.setdefault(node_of(r["metric"].get("instance")), {})[r["metric"].get("device")] = round(_v(r) or 0)
    for r in _rows(snap, "flannel_if_drops_1d"):
        drops_1d.setdefault(node_of(r["metric"].get("instance")), {})[r["metric"].get("device")] = round(_v(r) or 0)
    for r in _rows(snap, "flannel_if_up"):
        up[node_of(r["metric"].get("instance"))] = int(_v(r) or 0)
    for r in _rows(snap, "flannel_if_mtu"):
        mtu_ne[node_of(r["metric"].get("instance"))] = int(_v(r) or 0)
    for r in _rows(snap, "flannel_overlay_bytes_1d"):
        overlay_bytes[node_of(r["metric"].get("instance"))] = round(_v(r) or 0)
    metrics_available = bool(load_json(snap / "metrics" / "flannel_if_up.json") and (load_json(snap / "metrics" / "flannel_if_up.json") or {}).get("ok"))
    # --- node rows (k3s node record + counters)
    nodes = []
    subnets = set()
    for rec in recs:
        fl = rec.get("flannel") or None
        name = rec.get("node")
        if fl and fl.get("local_ip"):
            with contextlib.suppress(ValueError):
                subnets.add(str(ipaddress.ip_interface(f"{fl['local_ip']}/24").network))
        row = dict(rec)
        row["flannel"] = fl
        row["collected"] = rec.get("collected")
        row["errors_1d"] = errs_1d.get(name, {})
        row["drops_1d"] = drops_1d.get(name, {})
        row["if_up"] = up.get(name)
        row["mtu_node_exporter"] = mtu_ne.get(name)
        row["overlay_bytes_1d"] = overlay_bytes.get(name)
        row["sysctl_ok"] = (str((fl or {}).get("ip_forward")) == "1" and str((fl or {}).get("br_netfilter")) == "1") if fl else None
        row["errors_1d_total"] = sum(row["errors_1d"].values())
        row["drops_1d_total"] = sum(row["drops_1d"].values())
        nodes.append(row)
    podcidr = cluster.get("podcidr") or []
    backend = "vxlan" if any((n.get("flannel") or {}).get("local_ip") for n in nodes) else None  # k3s default. host-gw/wireguard have no flannel.1 or a different device
    for n in nodes:
        if (n.get("flannel") or {}).get("vxlan") is None and n.get("flannel") and not n["flannel"].get("local_ip") and n["flannel"].get("mtu"):
            backend = backend or "unknown"
    nodes_with_data = [n["node"] for n in nodes if n.get("flannel") and n["flannel"].get("mtu")]
    nodes_missing = [n["node"] for n in nodes if not (n.get("flannel") and n["flannel"].get("mtu")) and n.get("collected")]
    summary = {
        "present": True,
        "backend": backend,
        "nodes": len(nodes),
        "nodes_with_data": nodes_with_data,
        "nodes_missing_data": nodes_missing,
        "mtu_mismatch": [n["node"] for n in nodes if (n.get("flannel") or {}).get("mtu_ok") is False],
        "mtu": {n["node"]: (n.get("flannel") or {}).get("mtu") for n in nodes if n.get("flannel")},
        "sysctl_off": [n["node"] for n in nodes if n.get("sysctl_ok") is False],
        "if_down": [n for n, v in up.items() if v == 0],
        "errors_1d_total": sum(n["errors_1d_total"] for n in nodes),
        "drops_1d_total": sum(n["drops_1d_total"] for n in nodes),
        "drops_1d_by_node": {n["node"]: n["drops_1d"] for n in nodes if n["drops_1d_total"]},
        "errors_boot_total": sum(((n.get("flannel") or {}).get("rx_errors") or 0) + ((n.get("flannel") or {}).get("tx_errors") or 0) for n in nodes),
        "drops_boot_total": sum(((n.get("flannel") or {}).get("rx_dropped") or 0) + ((n.get("flannel") or {}).get("tx_dropped") or 0) for n in nodes),
        "node_subnets": sorted(subnets),
        "cross_subnet": len(subnets) > 1,
        "overlay_gib_1d": {k: round(v / 1024**3, 2) for k, v in overlay_bytes.items()},
        "podcidr_max_ratio": max([p.get("ratio") or 0 for p in podcidr], default=None),
        "podcidr_nodes": len(podcidr),
        "metrics_available": metrics_available,
    }
    return {
        "present": True,
        "backend": backend,
        "nodes": nodes,
        "podcidr": podcidr,
        "summary": summary,
        "note": "Node data (mtu, vxlan, cumulative counters, sysctl) comes from the k3s-platform node script's flannel section (SSH). 24-hour increases come from node-exporter. The vxlan backend is unencrypted; if nodes span different subnets or a public network, the wireguard-native backend is the right choice",
    }

"""MetalLB summary (collectors/metallb).

Inputs: summary.k3s.cluster.metallb (IPAddressPool size/used/remaining, LoadBalancer Services and their IPs, Pending, L2 leaders — reused from lib/k3s.py), objects (daemonsets speaker, deployments controller, validatingwebhookconfigurations, bgppeers, l2advertisements),
metrics/pod/metallb-speaker/*.prom (speaker metrics: config load/stale, k8s client update errors, layer2 ARP responses/gratuitous, BGP sessions). What we look at: pool remaining and Pending, L2 leader concentration, whether speaker runs on every node and whether its metrics were read, speakers with stale config, controller replicas/version, webhook failurePolicy, mode (L2/BGP).
Output: the `metallb` section of summary.json. Shape documented in SKILL.md.
"""

from __future__ import annotations

import re
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import objects


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def analyze(snap: Path, inv: dict | None, k3s: dict | None) -> dict:
    inv = inv or {}
    base = (((k3s or {}).get("cluster") or {}).get("metallb")) or {}
    speaker = next((d for d in objects(snap, "daemonsets") if d["metadata"]["name"] in ("speaker", "metallb-speaker") or d["metadata"]["name"].endswith("-speaker")), None)
    controller = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] in ("controller", "metallb-controller") or d["metadata"]["name"].endswith("metallb-controller")), None)
    if not base.get("present") and speaker is None and controller is None:
        return {"present": False}
    nodes_total = (inv.get("nodes") or {}).get("count") or len((inv.get("nodes") or {}).get("nodes") or [])

    def wl(d):
        if not d:
            return {"present": False}
        sp, st = d.get("spec") or {}, d.get("status") or {}
        c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
        return {
            "present": True,
            "namespace": d["metadata"]["namespace"],
            "name": d["metadata"]["name"],
            "version": _ver(c0.get("image")),
            "desired": st.get("desiredNumberScheduled", sp.get("replicas")),
            "ready": st.get("numberReady", st.get("readyReplicas")) or 0,
            "args": [str(a) for a in (c0.get("args") or [])],
        }

    sp_, ct_ = wl(speaker), wl(controller)
    ns = sp_.get("namespace") or ct_.get("namespace") or "metallb-system"
    webhooks = [{"name": h.get("name"), "failure_policy": h.get("failurePolicy")} for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io") if "metallb" in w["metadata"]["name"] for h in w.get("webhooks") or []]
    bgp_peers = objects(snap, "bgppeers.metallb.io")
    mode = "bgp" if bgp_peers else ("layer2" if objects(snap, "l2advertisements.metallb.io") else None)
    # --- speaker metrics
    d = snap / "metrics" / "pod" / "metallb-speaker"
    files = [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []
    per_pod = {}
    for f in files:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        s = pm["single"]
        per_pod[f.stem] = {
            "config_loaded": s.get("metallb_k8s_client_config_loaded_bool"),
            "config_stale": s.get("metallb_k8s_client_config_stale_bool"),
            "update_errors": int(s.get("metallb_k8s_client_update_errors_total", 0)),
            "updates": int(s.get("metallb_k8s_client_updates_total", 0)),
            "arp_requests": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_requests_received", [])),
            "arp_responses": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_responses_sent", [])),
            "gratuitous": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_gratuitous_sent", [])),
            "bgp_sessions_up": sum(int(v) for _, v in pm["labeled"].get("metallb_bgp_session_up", [])),
            "bgp_sessions": len(pm["labeled"].get("metallb_bgp_session_up", [])),
            "announced": sum(1 for _, v in pm["labeled"].get("metallb_speaker_announced", []) if v >= 1),
        }
    l2 = base.get("l2") or {}
    summary = {
        "present": True,
        "mode": mode,
        "version": sp_.get("version") or ct_.get("version"),
        "namespace": ns,
        "speaker_desired": sp_.get("desired"),
        "speaker_ready": sp_.get("ready"),
        "speaker_all_nodes": (sp_.get("ready") or 0) >= nodes_total if sp_.get("present") else None,
        "nodes_total": nodes_total,
        "controller_replicas": ct_.get("desired"),
        "controller_ready": ct_.get("ready"),
        "pools": len(base.get("pools") or []),
        "total_ips": base.get("total_ips"),
        "used": base.get("used"),
        "free": base.get("free"),
        "pending": [f"{s['namespace']}/{s['name']}" for s in base.get("pending") or []],
        "lb_services": len(base.get("services") or []),
        "l2_available": l2.get("available"),
        "speakers_read": len(files),
        "speakers_unreadable": l2.get("speakers_unreadable") or [],
        "leader_node": l2.get("leader_node"),
        "leader_share": l2.get("leader_share"),
        "pinned_by_selector": l2.get("pinned_by_selector"),
        "config_stale_pods": [p for p, v in per_pod.items() if v["config_stale"] == 1 or v["config_loaded"] == 0],
        "update_errors_total": sum(v["update_errors"] for v in per_pod.values()),
        "arp_requests_total": sum(v["arp_requests"] for v in per_pod.values()),
        "arp_responses_total": sum(v["arp_responses"] for v in per_pod.values()),
        "gratuitous_total": sum(v["gratuitous"] for v in per_pod.values()),
        "bgp_sessions": sum(v["bgp_sessions"] for v in per_pod.values()),
        "bgp_sessions_up": sum(v["bgp_sessions_up"] for v in per_pod.values()),
        "bgp_peers": len(bgp_peers),
        "webhooks_fail": [w["name"] for w in webhooks if w["failure_policy"] == "Fail"],
        "webhooks": len(webhooks),
        "metrics_available": bool(files),
    }
    return {
        "present": True,
        "speaker": sp_,
        "controller": ct_,
        "webhooks": webhooks,
        "pools": base,
        "l2": l2,
        "speaker_metrics": per_pod,
        "summary": summary,
        "note": "Pools, services and L2 leaders come from the same data as lib/k3s.py (k3s.cluster.metallb). Speaker metrics come from the pod proxy or node curl (metrics/pod/metallb-speaker). The webhook only blocks creation of MetalLB CRs (pools, advertisements), not ordinary Services",
    }

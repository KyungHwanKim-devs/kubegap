"""kube-proxy summary (collectors/kube-proxy).

Inputs: objects/configmaps (kube-system/kube-proxy-config, EKS), daemonsets (kube-proxy), services, endpointslices, nodes, logs/node/<node>/kube-proxy.txt (/proxyMode and /healthz read from inside the node),
metrics/kubeproxy_*.json, aws/describe-addon-kube-proxy.json(EKS), inventory(platform, nodes).

On k3s, kube-proxy is embedded in the k3s binary, so there is no DaemonSet or ConfigMap (embedded true) and its metrics appear mixed into the kubelet scrape instances (IP:10250, :6443) — same process, same values, so they are merged by node IP.

Output: the `kubeproxy` section of summary.json: present, embedded, config (mode, metricsBindAddress, conntrack, syncPeriod, nodePortAddresses), daemonset (desired, ready, image, version, addon), scale (Service, EndpointSlice, endpoint counts),
nodes[per node: mode, healthz, iptables rule count, sync p99, pending, last sync age, restore failures, no-local-endpoints, conntrack INVALID drops], metrics (cluster p99, programming p99, targets up/down), summary (for checks). Shape documented in SKILL.md.
"""

from __future__ import annotations

import math
import re
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


def _scalar(snap: Path, qid: str):
    r = _rows(snap, qid)
    return round(r[0][1], 4) if r else None


def _r(x, n=3):
    return None if x is None else round(x, n)


def _parse_config(text: str) -> dict:
    """Roughly read a KubeProxyConfiguration YAML (yamlite handles nested blocks, but here only the needed keys are read via regex)."""

    def g(key, section=None):
        if section:
            m = re.search(rf"^{section}:\n((?:[ \t]+.*\n?)+)", text, re.MULTILINE)
            if not m:
                return None
            m2 = re.search(rf"^\s+{key}:\s*(.*)$", m.group(1), re.MULTILINE)
            return m2.group(1).strip().strip('"') if m2 else None
        m = re.search(rf"^{key}:\s*(.*)$", text, re.MULTILINE)
        return m.group(1).strip().strip('"') if m else None

    return {
        "mode": g("mode") or "iptables (default)",
        "metrics_bind_address": g("metricsBindAddress"),
        "healthz_bind_address": g("healthzBindAddress"),
        "cluster_cidr": g("clusterCIDR"),
        "node_port_addresses": g("nodePortAddresses"),
        "config_sync_period": g("configSyncPeriod"),
        "conntrack": {"max_per_core": g("maxPerCore", "conntrack"), "min": g("min", "conntrack"), "tcp_established_timeout": g("tcpEstablishedTimeout", "conntrack"), "tcp_close_wait_timeout": g("tcpCloseWaitTimeout", "conntrack")},
        "iptables": {"sync_period": g("syncPeriod", "iptables"), "min_sync_period": g("minSyncPeriod", "iptables"), "masquerade_all": g("masqueradeAll", "iptables")},
        "ipvs": {"scheduler": g("scheduler", "ipvs"), "strict_arp": g("strictARP", "ipvs")},
        "source": "configmap kube-system/kube-proxy-config",
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    platform = (inv.get("cluster") or {}).get("platform")
    inv_nodes = (inv.get("nodes") or {}).get("nodes") or []
    ds = next((d for d in objects(snap, "daemonsets") if d["metadata"]["namespace"] == "kube-system" and d["metadata"]["name"] in ("kube-proxy", "rke2-kube-proxy")), None)
    embedded = ds is None and platform in ("k3s", "rke2")
    if ds is None and not embedded:
        return {"present": False}
    # --- config
    cm = next((c for c in objects(snap, "configmaps") if c["metadata"]["namespace"] == "kube-system" and c["metadata"]["name"] in ("kube-proxy-config", "kube-proxy") and "config" in (c.get("data") or {})), None)
    cfg_text = ((cm or {}).get("data") or {}).get("config") or ""
    cfg = (
        _parse_config(cfg_text)
        if cfg_text
        else {
            "mode": None,
            "metrics_bind_address": None,
            "healthz_bind_address": None,
            "cluster_cidr": None,
            "node_port_addresses": None,
            "config_sync_period": None,
            "conntrack": {},
            "iptables": {},
            "ipvs": {},
            "source": "none (embedded in k3s — only changeable via --kube-proxy-arg)" if embedded else "none",
        }
    )
    # --- DaemonSet and addon
    dsinfo = {"present": ds is not None}
    if ds:
        st = ds.get("status") or {}
        c0 = (ds["spec"]["template"]["spec"].get("containers") or [{}])[0]
        m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", c0.get("image", ""))
        dsinfo.update(
            {
                "desired": st.get("desiredNumberScheduled"),
                "ready": st.get("numberReady"),
                "available": st.get("numberAvailable"),
                "image": c0.get("image"),
                "version": m.group(1) if m else None,
                "args": (c0.get("command") or []) + (c0.get("args") or []),
                "resources": c0.get("resources") or {},
            }
        )
    addon = (load_json(snap / "aws" / "describe-addon-kube-proxy.json") or {}).get("addon") or {}
    dsinfo["addon_version"] = addon.get("addonVersion")
    dsinfo["addon_managed"] = bool(addon)
    # --- scale
    svcs = objects(snap, "services")
    eps = objects(snap, "endpointslices.discovery.k8s.io")
    scale = {
        "services": len(svcs),
        "services_by_type": {},
        "endpointslices": len(eps),
        "endpoints": sum(len(e.get("endpoints") or []) for e in eps),
        "external_traffic_local": sum(1 for s in svcs if (s.get("spec") or {}).get("externalTrafficPolicy") == "Local"),
    }
    for s in svcs:
        t = (s.get("spec") or {}).get("type") or "ClusterIP"
        scale["services_by_type"][t] = scale["services_by_type"].get(t, 0) + 1
    # --- node mapping (instance IP → node)
    ip_to_node = {}
    for n in inv_nodes:
        if n.get("internal_ip"):
            ip_to_node[n["internal_ip"]] = n["name"]

    def node_of(inst: str):
        return ip_to_node.get((inst or "").split(":")[0]) or inst

    per: dict[str, dict] = {}

    def put(qid, key, agg=max):
        for lab, v in _rows(snap, qid):
            nd = node_of(lab.get("instance", ""))
            d = per.setdefault(nd, {})
            d[key] = agg(d[key], v) if key in d else v

    put("kubeproxy_sync_p99_by_instance_1h", "sync_p99_s")
    put("kubeproxy_syncs_1h", "syncs_1h")
    put("kubeproxy_rules_pending_s", "rules_pending_s")
    put("kubeproxy_last_sync_age_s", "last_sync_age_s")
    put("kubeproxy_restore_failures_24h", "restore_failures_24h")
    put("kubeproxy_no_local_endpoints_1h", "no_local_endpoints_1h")
    put("kubeproxy_ct_invalid_dropped_1h", "ct_invalid_dropped_1h")
    for lab, v in _rows(snap, "kubeproxy_iptables_rules"):
        nd = node_of(lab.get("instance", ""))
        d = per.setdefault(nd, {})
        tbl = d.setdefault("iptables_rules", {})
        tbl[lab.get("table")] = max(tbl.get(lab.get("table"), 0), int(v))
    targets = {node_of(lab.get("instance", "")): int(v) for lab, v in _rows(snap, "kubeproxy_targets")}
    nodes = []
    gaps = []
    for n in inv_nodes:
        name = n["name"]
        d = per.get(name, {})
        txt_path = snap / "logs" / "node" / name / "kube-proxy.txt"
        local = {}
        if txt_path.is_file():
            for ln in txt_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    local[k.strip()] = v.strip()
        else:
            gaps.append(name)
        rules = d.get("iptables_rules") or {}
        nodes.append(
            {
                "node": name,
                "mode": local.get("mode") or None,
                "healthz": local.get("healthz"),
                "metrics_local_http": local.get("metrics_local"),
                "scrape_up": targets.get(name),
                "metrics_available": bool(d),
                "sync_p99_s": _r(d.get("sync_p99_s"), 4),
                "syncs_1h": _r(d.get("syncs_1h"), 1),
                "rules_pending_s": _r(max(d["rules_pending_s"], 0.0), 1) if "rules_pending_s" in d else None,
                "last_sync_age_s": _r(d.get("last_sync_age_s"), 0),
                "iptables_rules": rules,
                "iptables_rules_total": sum(rules.values()) if rules else None,
                "nat_rules": rules.get("nat"),
                "restore_failures_24h": _r(d.get("restore_failures_24h"), 0),
                "no_local_endpoints_1h": _r(d.get("no_local_endpoints_1h"), 0),
                "ct_invalid_dropped_1h": _r(d.get("ct_invalid_dropped_1h"), 0),
            }
        )
    modes = sorted({x["mode"] for x in nodes if x["mode"]})
    mode = cfg.get("mode") if cfg.get("mode") and not cfg["mode"].endswith("(default)") else (modes[0] if len(modes) == 1 else cfg.get("mode"))
    bind = cfg.get("metrics_bind_address") or ""
    metrics_loopback_only = bind.startswith(("127.0.0.1", "localhost"))
    up_n = sum(1 for v in targets.values() if v == 1)
    down_n = sum(1 for v in targets.values() if v == 0)
    any_metrics = any(x["metrics_available"] for x in nodes) or bool(_rows(snap, "kubeproxy_sync_p99_1h"))
    rest_err = {lab.get("code"): round(v, 1) for lab, v in _rows(snap, "kubeproxy_rest_client_errors_1h")}
    metrics = {
        "available": any_metrics,
        "source": ("job=kube-proxy" if targets else ("embedded in kubelet scrape" if embedded and any_metrics else None)),
        "targets_up": up_n,
        "targets_down": down_n,
        "targets_down_nodes": [k for k, v in targets.items() if v == 0],
        "sync_p99_s": _scalar(snap, "kubeproxy_sync_p99_1h"),
        "programming_p99_s": _scalar(snap, "kubeproxy_programming_p99_1h"),
        "rest_client_errors_1h": rest_err,
        "rest_client_errors_total_1h": round(sum(rest_err.values())),
    }
    nat_max = max((x["nat_rules"] or 0) for x in nodes) if nodes else 0
    summary = {
        "present": True,
        "embedded": embedded,
        "platform": platform,
        "mode": mode,
        "modes_seen": modes,
        "mode_mismatch": len(modes) > 1,
        "metrics_bind_address": cfg.get("metrics_bind_address"),
        "metrics_loopback_only": metrics_loopback_only,
        "metrics_available": any_metrics,
        "metrics_source": metrics["source"],
        "targets_up": up_n,
        "targets_down": down_n,
        "targets_down_nodes": metrics["targets_down_nodes"],
        "nodes_total": len(inv_nodes),
        "daemonset_desired": dsinfo.get("desired"),
        "daemonset_ready": dsinfo.get("ready"),
        "version": dsinfo.get("version"),
        "addon_version": dsinfo.get("addon_version"),
        "services": scale["services"],
        "endpoints": scale["endpoints"],
        "external_traffic_local": scale["external_traffic_local"],
        "nat_rules_max": nat_max,
        "nat_rules_by_node": {x["node"]: x["nat_rules"] for x in nodes if x["nat_rules"] is not None},
        "sync_p99_s": metrics["sync_p99_s"],
        "sync_p99_max_node": max(((x["sync_p99_s"] or 0), x["node"]) for x in nodes)[1] if nodes else None,
        "sync_p99_max_s": max(((x["sync_p99_s"] or 0) for x in nodes), default=None),
        "rules_pending_max_s": max(((x["rules_pending_s"] or 0) for x in nodes), default=None),
        "rules_pending_nodes": [x["node"] for x in nodes if (x["rules_pending_s"] or 0) >= 60],
        "restore_failures_24h": sum(int(x["restore_failures_24h"] or 0) for x in nodes),
        "restore_failure_nodes": [x["node"] for x in nodes if (x["restore_failures_24h"] or 0) > 0],
        "no_local_endpoints_1h": sum(int(x["no_local_endpoints_1h"] or 0) for x in nodes),
        "ct_invalid_dropped_1h": sum(int(x["ct_invalid_dropped_1h"] or 0) for x in nodes),
        "programming_p99_s": metrics["programming_p99_s"],
        "healthz_failing_nodes": [x["node"] for x in nodes if x["healthz"] and x["healthz"] != "200"],
        "node_cmd_unavailable": gaps,
        "conntrack_max_per_core": (cfg.get("conntrack") or {}).get("max_per_core"),
        "rest_client_errors_total_1h": metrics["rest_client_errors_total_1h"],
    }
    return {
        "present": True,
        "embedded": embedded,
        "config": cfg,
        "daemonset": dsinfo,
        "scale": scale,
        "nodes": nodes,
        "metrics": metrics,
        "summary": summary,
        "note": "On k3s, kube-proxy runs inside the k3s process, so there is no DaemonSet or ConfigMap and its metrics appear mixed into the kubelet scrape (instance :10250, :6443). rules_pending_s = queue time − sync time (0 if negative). iptables_rules is 'the number of rules written in the last sync', so after a partial sync (seen on EKS 1.32: nat 5) it is not the full scale — judge scale by services and endpoints",
    }

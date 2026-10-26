"""CoreDNS summary (collector collectors/coredns).

Inputs: objects/configmaps (Corefile and custom from kube-system/coredns), deployments (coredns), pods, poddisruptionbudgets, horizontalpodautoscalers, daemonsets (node-local-dns), nodes,
metrics/coredns_*.json (collectors/coredns/metrics.yaml plus core's coredns_servfail_ratio_1h and coredns_p99_1h), aws/describe-addon-coredns.json and describe-addon-versions-coredns.json (EKS), inventory.

Result: the `coredns` section of summary.json: config (Corefile plugins, cache TTL, forward targets, autopath, log), deployment (replicas, node spread, PDB, spread declarations, autoscaler, NodeLocal DNSCache, image, resources, restarts),
metrics (qps, rcode distribution, NXDOMAIN ratio, type distribution, AAAA ratio, cache hit ratio, p50/p99, upstream forwards, health check failures, panics, reload failures, apiserver call errors, per-pod skew), ndots (pod dnsPolicy/dnsConfig distribution). Shape is described in SKILL.md.
"""

from __future__ import annotations

import contextlib
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
            if math.isnan(v):
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


def _parse_corefile(text: str) -> dict:
    """Roughly parse the Corefile server blocks: plugin names, cache TTL, forward targets, presence of autopath/log/loop/ready, import paths."""
    plugins: list[str] = []
    cache_ttl = None
    forward_to: list[str] = []
    imports: list[str] = []
    zones: list[str] = []
    depth = 0
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if depth == 0 and ln.endswith("{"):
            zones.append(ln[:-1].strip())
        if depth == 1:
            tok = ln.rstrip("{").split()
            if tok:
                name = tok[0]
                if name not in plugins and re.match(r"^[a-z_]+$", name):
                    plugins.append(name)
                if name == "cache" and len(tok) > 1 and tok[1].isdigit():
                    cache_ttl = int(tok[1])
                if name == "forward":
                    forward_to = [t for t in tok[2:] if t and not t.startswith("{")]
                if name == "import":
                    imports += tok[1:]
        if depth == 0 and ln.startswith("import"):
            imports += ln.split()[1:]
        depth += ln.count("{") - ln.count("}")
    return {
        "zones": zones,
        "plugins": plugins,
        "cache_ttl": cache_ttl,
        "forward_to": forward_to,
        "imports": imports,
        "autopath": "autopath" in plugins,
        "log": "log" in plugins,
        "loop": "loop" in plugins,
        "ready": "ready" in plugins,
        "health": "health" in plugins,
        "lameduck": bool(re.search(r"lameduck\s+\d", text)),
        "prometheus": "prometheus" in plugins,
        "hosts": "hosts" in plugins,
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    dep = next((d for d in objects(snap, "deployments") if d["metadata"]["namespace"] == "kube-system" and d["metadata"]["name"] in ("coredns", "rke2-coredns-rke2-coredns")), None)
    if not dep:
        return {"present": False}
    nodes = objects(snap, "nodes")
    nodes_total = len(nodes)
    # --- Corefile
    cm = next((c for c in objects(snap, "configmaps") if c["metadata"]["namespace"] == "kube-system" and c["metadata"]["name"] == "coredns"), None)
    corefile = ((cm or {}).get("data") or {}).get("Corefile") or ""
    cfg = _parse_corefile(corefile)
    custom = next((c for c in objects(snap, "configmaps") if c["metadata"]["namespace"] == "kube-system" and c["metadata"]["name"] == "coredns-custom"), None)
    cfg["custom_keys"] = sorted(((custom or {}).get("data") or {}).keys())
    cfg["node_hosts_entries"] = len([ln for ln in (((cm or {}).get("data") or {}).get("NodeHosts") or "").splitlines() if ln.strip()])
    # --- Deployment
    sp = dep.get("spec") or {}
    tpl = (sp.get("template") or {}).get("spec") or {}
    conts = tpl.get("containers") or []
    image = conts[0].get("image") if conts else None
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    sel = (sp.get("selector") or {}).get("matchLabels") or {}
    pods = [p for p in objects(snap, "pods") if p["metadata"]["namespace"] == "kube-system" and all((p["metadata"].get("labels") or {}).get(k) == v for k, v in sel.items())]
    pod_rows = [
        {
            "pod": p["metadata"]["name"],
            "node": p["spec"].get("nodeName"),
            "phase": (p.get("status") or {}).get("phase"),
            "restarts": sum(int(c.get("restartCount") or 0) for c in (p.get("status") or {}).get("containerStatuses") or []),
            "ready": all(c.get("ready") for c in (p.get("status") or {}).get("containerStatuses") or []),
        }
        for p in pods
    ]
    pod_nodes = Counter(r["node"] for r in pod_rows if r["node"])
    anti = (tpl.get("affinity") or {}).get("podAntiAffinity") or {}
    pdbs = [
        b
        for b in objects(snap, "poddisruptionbudgets.policy")
        if b["metadata"]["namespace"] == "kube-system" and all(((b.get("spec") or {}).get("selector") or {}).get("matchLabels", {}).get(k) == v for k, v in sel.items()) and (b.get("spec") or {}).get("selector")
    ]
    hpa = [h for h in objects(snap, "horizontalpodautoscalers.autoscaling") if h["metadata"]["namespace"] == "kube-system" and ((h.get("spec") or {}).get("scaleTargetRef") or {}).get("name") == dep["metadata"]["name"]]
    cpa = [d["metadata"]["name"] for d in objects(snap, "deployments") if "dns-autoscaler" in d["metadata"]["name"] or "cluster-proportional-autoscaler" in d["metadata"]["name"]]
    nld = [d for d in objects(snap, "daemonsets") if d["metadata"]["name"] in ("node-local-dns", "nodelocaldns")]
    res = (conts[0].get("resources") or {}) if conts else {}
    addon = (load_json(snap / "aws" / "describe-addon-coredns.json") or {}).get("addon") or {}
    latest = None
    with contextlib.suppress(IndexError, AttributeError):
        latest = (((load_json(snap / "aws" / "describe-addon-versions-coredns.json") or {}).get("addons") or [{}])[0].get("addonVersions") or [{}])[0].get("addonVersion")
    deployment = {
        "name": dep["metadata"]["name"],
        "image": image,
        "version": m.group(1) if m else None,
        "addon_version": addon.get("addonVersion"),
        "addon_latest": latest,
        "addon_managed": bool(addon),
        "replicas": sp.get("replicas"),
        "ready": (dep.get("status") or {}).get("readyReplicas") or 0,
        "nodes_total": nodes_total,
        "pods": pod_rows,
        "nodes_with_pods": len(pod_nodes),
        "pods_by_node": dict(pod_nodes),
        "all_same_node": nodes_total >= 2 and len(pod_rows) >= 1 and len(pod_nodes) == 1 and (sp.get("replicas") or 0) >= 2,
        "single_replica": (sp.get("replicas") or 0) < 2,
        "pdb": [b["metadata"]["name"] for b in pdbs],
        "has_pdb": bool(pdbs),
        "anti_affinity": "required" if anti.get("requiredDuringSchedulingIgnoredDuringExecution") else ("preferred" if anti.get("preferredDuringSchedulingIgnoredDuringExecution") else None),
        "topology_spread": bool(tpl.get("topologySpreadConstraints")),
        "spread_declared": bool(anti) or bool(tpl.get("topologySpreadConstraints")),
        "autoscaler": ("hpa" if hpa else ("cluster-proportional" if cpa else None)),
        "autoscaler_names": [h["metadata"]["name"] for h in hpa] + cpa,
        "node_local_dns": bool(nld),
        "resources": res,
        "memory_limit": (res.get("limits") or {}).get("memory"),
        "cpu_request": (res.get("requests") or {}).get("cpu"),
        "priority_class": tpl.get("priorityClassName"),
        "restarts_total": sum(r["restarts"] for r in pod_rows),
        "max_unavailable": ((sp.get("strategy") or {}).get("rollingUpdate") or {}).get("maxUnavailable"),
        "replicas_per_8_nodes": _r((sp.get("replicas") or 0) / max(nodes_total / 8, 1), 2),
    }
    # --- Metrics
    rc = {lab.get("rcode"): v for lab, v in _rows(snap, "coredns_responses_by_rcode_1h")}
    types = {lab.get("type"): v for lab, v in _rows(snap, "coredns_requests_by_type_1h")}
    total_resp = sum(rc.values())
    total_req = sum(types.values())
    qps = {lab.get("pod"): round(v, 2) for lab, v in _rows(snap, "coredns_qps_by_pod")}
    fwd = {}
    for lab, v in _rows(snap, "coredns_forward_by_upstream_rcode_1h"):
        fwd.setdefault(lab.get("to"), {})[lab.get("rcode")] = round(v, 1)
    fwd_total = sum(sum(d.values()) for d in fwd.values())
    fwd_nx = sum(d.get("NXDOMAIN", 0) for d in fwd.values())
    fwd_sf = sum(d.get("SERVFAIL", 0) for d in fwd.values())
    rest_err = {lab.get("code"): round(v, 1) for lab, v in _rows(snap, "coredns_rest_client_errors_1h") if v > 0}
    cache_entries = {}
    for lab, v in _rows(snap, "coredns_cache_entries"):
        cache_entries[lab.get("pod")] = cache_entries.get(lab.get("pod"), 0) + int(v)
    available = bool(rc) or bool(types)
    qvals = sorted(qps.values())
    metrics = {
        "available": available,
        "up_pods": _scalar(snap, "coredns_up"),
        "window": "1h",
        "requests_1h": round(total_req),
        "qps_total": _r(total_req / 3600, 2) if total_req else None,
        "qps_by_pod": qps,
        "qps_skew": _r(qvals[-1] / qvals[0], 2) if len(qvals) >= 2 and qvals[0] > 0 else None,
        "responses_by_rcode": {k: round(v) for k, v in rc.items()},
        "nxdomain_ratio": _r(rc.get("NXDOMAIN", 0) / total_resp) if total_resp else None,
        "servfail_ratio": _r(rc.get("SERVFAIL", 0) / total_resp) if total_resp else None,
        "refused_ratio": _r(rc.get("REFUSED", 0) / total_resp) if total_resp else None,
        "requests_by_type": {k: round(v) for k, v in types.items()},
        "aaaa_ratio": _r(types.get("AAAA", 0) / total_req) if total_req else None,
        "a_ratio": _r(types.get("A", 0) / total_req) if total_req else None,
        "cache_hit_ratio": _scalar(snap, "coredns_cache_hit_ratio_1h"),
        "cache_entries_by_pod": cache_entries,
        "p50_s": _scalar(snap, "coredns_p50_1h"),
        "p99_s": _scalar(snap, "coredns_p99_1h"),
        "forward": {
            "by_upstream_rcode": fwd,
            "total_1h": round(fwd_total),
            "share_of_requests": _r(fwd_total / total_req) if total_req else None,
            "nxdomain_ratio": _r(fwd_nx / fwd_total) if fwd_total else None,
            "servfail_ratio": _r(fwd_sf / fwd_total) if fwd_total else None,
            "servfail_1h": round(fwd_sf),
            "p99_s": _scalar(snap, "coredns_forward_p99_1h"),
            "healthcheck_failures_1h": _scalar(snap, "coredns_forward_healthcheck_failures_1h"),
            "max_concurrent_rejects_1h": _scalar(snap, "coredns_max_concurrent_rejects_1h"),
            "upstreams": sorted(fwd.keys()),
        },
        "panics_1h": _scalar(snap, "coredns_panics_1h"),
        "reload_failed_1h": _scalar(snap, "coredns_reload_failed_1h"),
        "rest_client_errors_1h": rest_err,
        "rest_client_errors_total_1h": round(sum(rest_err.values())),
    }
    # --- pod DNS settings (ndots)
    dns_policy: Counter = Counter()
    ndots: Counter = Counter()
    for p in objects(snap, "pods"):
        dns_policy[p["spec"].get("dnsPolicy") or "ClusterFirst"] += 1
        opts = {o.get("name"): o.get("value") for o in ((p["spec"].get("dnsConfig") or {}).get("options") or [])}
        ndots[opts.get("ndots", "5 (default)")] += 1
    ipv6 = any(":" in (a.get("address") or "") for n in nodes for a in ((n.get("status") or {}).get("addresses") or []) if a.get("type") == "InternalIP")
    nd = {
        "dns_policy": dict(dns_policy),
        "ndots": dict(ndots),
        "pods_default_ndots": ndots.get("5 (default)", 0),
        "cluster_ipv6": ipv6,
        "note": "With the default ndots:5, an external name with fewer than 5 dots (api.example.com) is first tried with <ns>.svc.cluster.local, svc.cluster.local, cluster.local and the VPC search domain appended, producing 3-4 NXDOMAINs before the real name is asked. That is why the NXDOMAIN ratio is high and the query count is several times the number of real names. Fixes: trailing dot (FQDN), ndots:2, or the autopath plugin",
    }
    summary = {
        "present": True,
        "version": deployment["version"],
        "replicas": deployment["replicas"],
        "nodes_total": nodes_total,
        "nodes_with_pods": deployment["nodes_with_pods"],
        "all_same_node": deployment["all_same_node"],
        "single_replica": deployment["single_replica"],
        "has_pdb": deployment["has_pdb"],
        "spread_declared": deployment["spread_declared"],
        "autoscaler": deployment["autoscaler"],
        "node_local_dns": deployment["node_local_dns"],
        "metrics_available": available,
        "qps_total": metrics["qps_total"],
        "nxdomain_ratio": metrics["nxdomain_ratio"],
        "servfail_ratio": metrics["servfail_ratio"],
        "aaaa_ratio": metrics["aaaa_ratio"],
        "cache_hit_ratio": metrics["cache_hit_ratio"],
        "p50_s": metrics["p50_s"],
        "p99_s": metrics["p99_s"],
        "forward_nxdomain_ratio": metrics["forward"]["nxdomain_ratio"],
        "forward_servfail_1h": metrics["forward"]["servfail_1h"],
        "forward_servfail_ratio": metrics["forward"]["servfail_ratio"],
        "forward_healthcheck_failures_1h": metrics["forward"]["healthcheck_failures_1h"],
        "max_concurrent_rejects_1h": metrics["forward"]["max_concurrent_rejects_1h"],
        "upstreams": metrics["forward"]["upstreams"],
        "panics_1h": metrics["panics_1h"],
        "reload_failed_1h": metrics["reload_failed_1h"],
        "rest_client_errors_total_1h": metrics["rest_client_errors_total_1h"],
        "qps_skew": metrics["qps_skew"],
        "qps_by_pod": qps,
        "cache_ttl": cfg["cache_ttl"],
        "autopath": cfg["autopath"],
        "cluster_ipv6": ipv6,
        "pods_default_ndots": nd["pods_default_ndots"],
        "restarts_total": deployment["restarts_total"],
        "memory_limit": deployment["memory_limit"],
        "pods_by_node": deployment["pods_by_node"],
        "pdb": deployment["pdb"],
        "forward_to": cfg["forward_to"],
    }
    return {"present": True, "config": cfg, "deployment": deployment, "metrics": metrics, "ndots": nd, "summary": summary}

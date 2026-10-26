"""VPC CNI (aws-node) summary (collectors/vpc-cni).

Inputs: objects/daemonsets (aws-node env and image), eniconfigs.crd.k8s.amazonaws.com, logs/node/<node>/awscni.prom (ipamd metrics, curl from inside the node),
aws/instance-type-<type>.json (ENI/IP limits), aws/describe-subnets.json (free IPs), aws/describe-addon-vpc-cni.json, events.json (FailedCreatePodSandBox), inventory (nodes, prod_like).

Output is the `vpccni` section of summary.json: present, settings (version, prefix delegation, warm settings, custom networking, pod ENI, network policy mode),
nodes[per node: ENI/IP limits of the instance type, max-pods, running pods (excluding hostNetwork), ipamd metrics (assigned/total/eni/ip_max/no_available/EC2 errors), ip_usage_ratio, max_pods_exceeds_ip_capacity],
subnets[free IPs, usage], warm (total reserved-but-unused IPs), sandbox_failures_24h, gaps. Shape is documented in SKILL.md.

ENI arithmetic: pod IPs a node can hold = ENI count x (IPv4 per ENI - 1). The first IP belongs to the ENI itself. With prefix delegation (/28 prefixes) multiply by 16.
"""

from __future__ import annotations

import re
from pathlib import Path

from .controlplane import workload_of  # noqa: F401  (used by the report to map pod -> workload name)
from .snapshot import load_json, objects

METRIC_RE = re.compile(r"^(awscni_[a-z0-9_]+)(\{([^}]*)\})?\s+([0-9.eE+-]+)\s*$")


def _q(v) -> int:
    try:
        return int(str(v).rstrip("i"))
    except (TypeError, ValueError):
        return 0


def _parse_prom(text: str) -> dict:
    """awscni_* lines -> {metric: value | {labels-tuple: value}}. Single-value metrics become numbers; labelled ones become a list of label dicts."""
    single: dict[str, float] = {}
    labeled: dict[str, list[tuple[dict, float]]] = {}
    for ln in text.splitlines():
        m = METRIC_RE.match(ln.strip())
        if not m:
            continue
        name, labels_txt, val = m.group(1), m.group(3), m.group(4)
        try:
            v = float(val)
        except ValueError:
            continue
        if labels_txt is None:
            single[name] = v
        else:
            labels = dict(re.findall(r'(\w+)="([^"]*)"', labels_txt))
            labeled.setdefault(name, []).append((labels, v))
    return {"single": single, "labeled": labeled}


def _settings(snap: Path) -> dict:
    ds = next((d for d in objects(snap, "daemonsets") if d["metadata"]["name"] == "aws-node" and d["metadata"]["namespace"] == "kube-system"), None)
    if not ds:
        return {"present": False}
    env: dict[str, str] = {}
    image = None
    nodeagent_args: list[str] = []
    for c in ds["spec"]["template"]["spec"].get("containers") or []:
        if c["name"] == "aws-node":
            image = c.get("image")
            for e in c.get("env") or []:
                if "value" in e:
                    env[e["name"]] = str(e["value"])
        if c["name"] == "aws-eks-nodeagent":
            nodeagent_args = [str(a) for a in (c.get("args") or [])]
    m = re.search(r"amazon-k8s-cni:v?([0-9][^\s]*)", image or "")
    addon = (load_json(snap / "aws" / "describe-addon-vpc-cni.json") or {}).get("addon") or {}
    versions = load_json(snap / "aws" / "describe-addon-versions-vpc-cni.json") or {}
    latest = None
    try:
        latest = ((versions.get("addons") or [{}])[0].get("addonVersions") or [{}])[0].get("addonVersion")
    except (IndexError, AttributeError):
        latest = None

    def flag(name, default="false"):
        return str(env.get(name, default)).lower() == "true"

    netpol = next((a.split("=", 1)[1] for a in nodeagent_args if a.startswith("--enable-network-policy=")), None)
    return {
        "present": True,
        "image": image,
        "version": m.group(1) if m else None,
        "addon_version": addon.get("addonVersion"),
        "addon_status": addon.get("status"),
        "addon_latest": latest,
        "addon_managed": bool(addon),
        "status": {"desired": (ds.get("status") or {}).get("desiredNumberScheduled"), "ready": (ds.get("status") or {}).get("numberReady"), "available": (ds.get("status") or {}).get("numberAvailable")},
        "prefix_delegation": flag("ENABLE_PREFIX_DELEGATION"),
        "warm_eni_target": _q(env.get("WARM_ENI_TARGET", "1")),
        "warm_ip_target": _q(env["WARM_IP_TARGET"]) if env.get("WARM_IP_TARGET") else None,
        "minimum_ip_target": _q(env["MINIMUM_IP_TARGET"]) if env.get("MINIMUM_IP_TARGET") else None,
        "warm_prefix_target": _q(env.get("WARM_PREFIX_TARGET", "1")),
        "custom_networking": flag("AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG"),
        "pod_eni": flag("ENABLE_POD_ENI"),
        "ipv6": flag("ENABLE_IPv6"),
        "subnet_discovery": flag("ENABLE_SUBNET_DISCOVERY", "true"),
        "network_policy_mode": env.get("NETWORK_POLICY_ENFORCING_MODE"),
        "nodeagent_enable_network_policy": (netpol.lower() == "true") if netpol is not None else None,
        "external_snat": flag("AWS_VPC_K8S_CNI_EXTERNALSNAT"),
        "env": {k: v for k, v in env.items() if k.startswith(("WARM", "MINIMUM", "ENABLE", "AWS_VPC", "NETWORK", "DISABLE", "ANNOTATE", "MAX_ENI"))},
        "eniconfigs": len(objects(snap, "eniconfigs.crd.k8s.amazonaws.com")),
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    st = _settings(snap)
    if not st.get("present"):
        return {"present": False}
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    inv_nodes = (inv.get("nodes") or {}).get("nodes") or []
    # instance type network limits
    limits: dict[str, dict] = {}
    for f in (snap / "aws").glob("instance-type-*.json") if (snap / "aws").is_dir() else []:
        d = load_json(f)
        rows = d if isinstance(d, list) else ((d or {}).get("InstanceTypes") or [])
        for r in rows or []:
            if isinstance(r, dict) and r.get("InstanceType"):
                limits[r["InstanceType"]] = {"max_eni": r.get("MaximumNetworkInterfaces"), "ipv4_per_eni": r.get("Ipv4AddressesPerInterface"), "hypervisor": r.get("Hypervisor")}
    # pod count (excluding hostNetwork = pods that consume an IP)
    pods = objects(snap, "pods")
    ip_pods: dict[str, int] = {}
    prod_pods: dict[str, int] = {}
    for p in pods:
        if (p.get("status") or {}).get("phase") not in ("Running", "Pending") or p["spec"].get("hostNetwork"):
            continue
        nd = p["spec"].get("nodeName")
        if nd:
            ip_pods[nd] = ip_pods.get(nd, 0) + 1
            if p["metadata"]["namespace"] in prod:
                prod_pods[nd] = prod_pods.get(nd, 0) + 1
    nodes = []
    gaps = []
    warm_idle_total = 0
    for n in inv_nodes:
        name = n["name"]
        lim = limits.get(n.get("instance_type") or "") or {}
        max_eni, per_eni = lim.get("max_eni"), lim.get("ipv4_per_eni")
        if max_eni and per_eni:
            cap = max_eni * (per_eni - 1) * (16 if st["prefix_delegation"] else 1)
        else:
            cap = None
        max_pods = _q((n.get("allocatable") or {}).get("pods"))
        prom = snap / "logs" / "node" / name / "awscni.prom"
        met: dict = {"available": False}
        if prom.is_file() and prom.stat().st_size > 0:
            pm = _parse_prom(prom.read_text(encoding="utf-8", errors="replace"))
            sg = pm["single"]
            ec2_err = 0
            ec2_err_by = {}
            for labels, v in pm["labeled"].get("awscni_aws_api_latency_ms_count", []):
                if labels.get("error") == "true" and labels.get("api") != "GetMetadata":  # IMDS 404 is a normal lookup miss; excluded
                    ec2_err += int(v)
                    ec2_err_by[labels.get("api")] = ec2_err_by.get(labels.get("api"), 0) + int(v)
            met = {
                "available": True,
                "assigned": int(sg.get("awscni_assigned_ip_addresses", 0)),
                "total": int(sg.get("awscni_total_ip_addresses", 0)),
                "eni_allocated": int(sg.get("awscni_eni_allocated", 0)),
                "eni_max": int(sg.get("awscni_eni_max", 0)),
                "ip_max": int(sg.get("awscni_ip_max", 0)),
                "prefixes": int(sg.get("awscni_total_ipv4_prefixes", 0)),
                "no_available_ip_events": int(sg.get("awscni_no_available_ip_addresses", 0)),
                "force_removed_enis": int(sg.get("awscni_force_removed_enis", 0)),
                "force_removed_ips": int(sg.get("awscni_force_removed_ips", 0)),
                "ec2_api_errors": ec2_err,
                "ec2_api_errors_by_api": ec2_err_by,
                "per_eni": {ln.get("eni"): int(v) for ln, v in pm["labeled"].get("awscni_assigned_ip_per_eni", [])},
            }
            warm_idle_total += max(met["total"] - met["assigned"], 0)
        else:
            gaps.append(name)
        ip_max = met.get("ip_max") or cap
        used = met.get("assigned") if met["available"] else ip_pods.get(name, 0)
        ratio = round(used / ip_max, 3) if ip_max else None
        nodes.append(
            {
                "node": name,
                "instance_type": n.get("instance_type"),
                "pool": n.get("nodepool") or n.get("nodegroup"),
                "max_eni": max_eni,
                "ipv4_per_eni": per_eni,
                "ip_capacity_calc": cap,
                "max_pods": max_pods,
                "pods_with_ip": ip_pods.get(name, 0),
                "prod_pods": prod_pods.get(name, 0),
                "metrics": met,
                "ip_max": ip_max,
                "ip_used": used,
                "ip_usage_ratio": ratio,
                "eni_at_max": bool(met["available"] and met["eni_max"] and met["eni_allocated"] >= met["eni_max"]),
                # The EKS AMI max-pods formula is ENI x (IP - 1) + 2; the +2 is for aws-node and kube-proxy, which use hostNetwork and no IP, so it is normal. Anything above that is a mismatch (measured: every node was exactly +2)
                "max_pods_exceeds_ip_capacity": bool(ip_max and max_pods > ip_max + 2),
                "max_pods_over_ip": (max_pods - ip_max) if ip_max else None,
                "ip_headroom": (ip_max - used) if ip_max is not None else None,
                "no_available_ip_events": met.get("no_available_ip_events", 0) if met["available"] else None,
                "ec2_api_errors": met.get("ec2_api_errors") if met["available"] else None,
                "metrics_available": met["available"],
                "prefix_delegation": st["prefix_delegation"],
                "hypervisor": lim.get("hypervisor"),
            }
        )
    nodes.sort(key=lambda r: -(r["ip_usage_ratio"] or 0))
    # subnets
    subs = []
    for sn in (load_json(snap / "aws" / "describe-subnets.json") or {}).get("Subnets") or []:
        cidr = sn.get("CidrBlock") or ""
        try:
            size = 2 ** (32 - int(cidr.split("/")[1])) - 5  # AWS reserves 5 addresses
        except (IndexError, ValueError):
            size = None
        avail = sn.get("AvailableIpAddressCount")
        name = next((t.get("Value") for t in sn.get("Tags") or [] if t.get("Key") == "Name"), None)
        subs.append(
            {
                "subnet_id": sn.get("SubnetId"),
                "name": name,
                "az": sn.get("AvailabilityZone"),
                "cidr": cidr,
                "usable": size,
                "available": avail,
                "used_ratio": round((size - avail) / size, 3) if (size and avail is not None) else None,
                "available_ratio": round(avail / size, 3) if (size and avail is not None) else None,
                "nodes": sum(1 for n in inv_nodes if (n.get("zone") == sn.get("AvailabilityZone"))),
            }
        )
    subs.sort(key=lambda s: s["available"] if s["available"] is not None else 10**9)
    sandbox = 0
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        if e.get("reason") == "FailedCreatePodSandBox":
            sandbox += int(e.get("count") or 1)
    # warm pool: with only WARM_ENI_TARGET and no WARM_IP_TARGET, one whole ENI (= per_eni - 1 IPs) is kept empty on every node
    per_node_reserve = None
    if not st["prefix_delegation"] and st["warm_ip_target"] is None and st["warm_eni_target"] >= 1:
        per_node_reserve = st["warm_eni_target"]
    _near = [r["node"] for r in nodes if (r["ip_usage_ratio"] or 0) >= 0.75]
    _noip = [r["node"] for r in nodes if (r["no_available_ip_events"] or 0) > 0]
    return {
        "present": True,
        "settings": st,
        "nodes": nodes,
        "node_count": len(nodes),
        # check-oriented summary in the same shape as the other platform collectors. max-pods may exceed the IP limit by up to 2 (hostNetwork pods)
        "summary": {
            "present": True,
            "nodes": len(nodes),
            "prefix_delegation": st["prefix_delegation"],
            "warm_eni_target": st["warm_eni_target"],
            "warm_ip_target": st["warm_ip_target"],
            "nodes_near_ip_limit": _near,
            "nodes_no_available_ip": _noip,
            "nodes_max_pods_over_ip": [r["node"] for r in nodes if r["max_pods_exceeds_ip_capacity"]],
            "min_ip_headroom": min([r["ip_headroom"] for r in nodes if r["ip_headroom"] is not None], default=None),
            "metrics_unavailable_nodes": gaps,
            "subnets_low": [s["subnet_id"] for s in subs if (s["available_ratio"] or 1) < 0.25],
            "max_pods_rule": "normal when max-pods <= IP limit + 2 (allowance for hostNetwork pods)",
        },
        "nodes_near_ip_limit": [r["node"] for r in nodes if (r["ip_usage_ratio"] or 0) >= 0.75],
        "nodes_eni_at_max": [r["node"] for r in nodes if r["eni_at_max"]],
        "nodes_no_available_ip": [r["node"] for r in nodes if (r["no_available_ip_events"] or 0) > 0],
        "nodes_max_pods_over_ip": [r["node"] for r in nodes if r["max_pods_exceeds_ip_capacity"]],
        "metrics_unavailable_nodes": gaps,
        "subnets": subs,
        "subnets_low": [s["subnet_id"] for s in subs if (s["available_ratio"] or 1) < 0.25],
        "warm": {
            "policy": ("prefix" if st["prefix_delegation"] else ("ip_target" if st["warm_ip_target"] is not None else "whole_eni")),
            "warm_eni_target": st["warm_eni_target"],
            "warm_ip_target": st["warm_ip_target"],
            "minimum_ip_target": st["minimum_ip_target"],
            "reserved_enis_per_node": per_node_reserve,
            "idle_ips_total": warm_idle_total,
            "summary": {
                "policy": ("prefix" if st["prefix_delegation"] else ("ip_target" if st["warm_ip_target"] is not None else "whole_eni")),
                "warm_eni_target": st["warm_eni_target"],
                "warm_ip_target": st["warm_ip_target"],
                "idle_ips_total": warm_idle_total,
                "subnets_low": [s["subnet_id"] for s in subs if (s["available_ratio"] or 1) < 0.25],
                "min_subnet_available": min([s["available"] for s in subs if s["available"] is not None], default=None),
                "nodes": len(nodes),
                "prefix_delegation": st["prefix_delegation"],
                "nitro_nodes": sum(1 for r in nodes if r["hypervisor"] == "nitro"),
                "nodes_near_ip_limit": [r["node"] for r in nodes if (r["ip_usage_ratio"] or 0) >= 0.5],
                "nodes_no_available_ip": [r["node"] for r in nodes if (r["no_available_ip_events"] or 0) > 0],
                "metrics_unavailable_nodes": gaps,
            },
        },
        "sandbox_failures_24h": sandbox,
        "note": "ip_max is the value reported by ipamd (otherwise computed as ENI count x (IPv4 per ENI - 1)). assigned is the number of IPs ipamd handed to pods, so hostNetwork pods are not included. no_available_ip_events accumulates since the process started.",
    }

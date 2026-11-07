"""Evidence sentences a check expression calls through `_sg_text` and `_oom_text`: the security-group exposure of a load balancer, the OOM history of a workload.

Part of the evaluator (lib/judgement/evaluate).
"""

from __future__ import annotations


def sg_text(item: dict) -> str:
    """One phrase for the evidence of traffic.db-exposed: what the load balancer's security groups let in, as counts, never the addresses themselves."""
    state = item.get("sg_exposure")
    allowed = item.get("allowed_sources") or {}
    if state == "open":
        ports = ", ".join(str(p) for p in sorted(int(p) for p in item.get("open_ports") or []))
        return f"open to 0.0.0.0/0 on {ports}" if ports else "open to 0.0.0.0/0"
    if state == "allow-list":
        n = max(allowed.values(), default=0)
        widths = list((item.get("widest_prefix") or {}).values())
        known = [w for w in widths if w is not None]
        hidden = sum(1 for w in widths if w is None)
        if known:
            width = f"widest /{min(known)}" + (f"; {hidden} port{'s' if hidden != 1 else ''} also allow{'s' if hidden == 1 else ''} a prefix list or security group reference" if hidden else "")
        else:
            width = "width unknown, a prefix list or security group reference"
        return f"allow-list, at most {n} source{'s' if n != 1 else ''} per port, {width}"
    if state == "blocked":
        return "no inbound rule covers the ports"
    if state == "no-security-group":
        return "none on the load balancer, only the targets' groups filter it"
    if state == "not-read":
        return "not read"
    if state == "unmatched":
        return "unknown, no described load balancer matched the Service address"
    return "not applicable"


def oom_text(item: dict) -> str:
    """The evidence of resources.oomkilled-repeated from a `resilience.oom_7d` row: both sources with their windows, never one number standing for the other."""
    total = item.get("kernel_nodes_total") or 0
    if item.get("kernel_log_read"):
        n = item.get("kernel_kills_24h") or 0
        kern = f"kernel log: {n} kill{'s' if n != 1 else ''} in 24 h on {item.get('kernel_nodes_read')} of {total} node{'s' if total != 1 else ''} read"
        if item.get("last_kill"):
            kern += f", last {item['last_kill']}"
        if item.get("kernel_nodes_old_script"):
            kern += f"; {item['kernel_nodes_old_script']} node{'s' if item['kernel_nodes_old_script'] != 1 else ''} ran the older node script, which keeps no oom-kill lines"
    elif item.get("kernel_nodes_old_script"):
        kern = f"kernel log read on {item['kernel_nodes_old_script']} node{'s' if item['kernel_nodes_old_script'] != 1 else ''} with the older node script, which keeps no oom-kill lines, so kills are not attributed; {item.get('kernel_cgroup_ooms_on_nodes') or 0} container OOM{'s' if (item.get('kernel_cgroup_ooms_on_nodes') or 0) != 1 else ''} counted on those nodes for every workload together"
    elif not item.get("kernel_any_node_read"):
        kern = "kernel log not read in this mode"
    elif total == 0:
        kern = "kernel log read, but the nodes of this workload's pods are unknown"
    else:
        kern = "kernel log not read on its node, no node access there"
    pods = item.get("pods_oomkilled") or 0
    rep = item.get("pods_replaced") or 0
    prom = f"Prometheus: {pods} pod{'s' if pods != 1 else ''} ended by OOM in 7 days" + (f", {rep} already replaced" if rep else "") + f", {item.get('restarts_of_those_pods') or 0} restarts in those pods"
    return f"{kern}. {prom}. cAdvisor counter {item.get('cadvisor_oom_events_7d') or 0}"

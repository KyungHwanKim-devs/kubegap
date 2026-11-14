"""Evidence sentences a check expression calls through the `_*_text` helpers of Context.helpers(): the security-group exposure of a load balancer, the OOM
history of a workload, and the twelve sentences that were Python expressions of 500 to 1,200 characters inside checks.yaml (#24). Each helper takes the
values the expression had (`item`, `labels`, `v`, the thresholds, `summary`) and returns the same sentence; tests/test_evidence_helpers.py compares
them with the former expressions.

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


def shown(xs, n: int) -> str:
    """The first `n` of a list for an evidence sentence, always with how many were left out: `['a', 'b'] and 8 more`. An evidence sentence is
    something to read; the finding's `details` and the summary keep the whole list. A cut list without its remainder reads as the whole
    (a report once said 11 workloads where there were 15). A text is cut to `n` characters with an ellipsis."""
    if isinstance(xs, str):
        return xs if len(xs) <= n else xs[:n].rstrip() + "…"
    xs = list(xs or [])
    return str(xs) if len(xs) <= n else f"{xs[:n]} and {len(xs) - n} more"


def placement_text(item: dict) -> str:
    """Evidence of resilience.replicas-same-node. The check fires in two cases that read very differently, so the sentence says which one first: every
    replica is on one node now, or they are apart now and nothing declares that they must be. A report once said four Deployments had every
    replica on one node where each had its replicas on two nodes of one zone."""
    case = (
        "every replica is on one node now. " if item.get("all_same_node") else "the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. "
    )
    tail = " — only one eligible node, so a spread declaration still lands on the same node" if item.get("single_eligible_node") else ""
    return (
        f"{case}replicas {item['replicas']} (Running {item['running']}), node distribution {item['nodes']}, AZ distribution {item['zones']}, "
        f"topologySpread {item['topology_spread']}, podAntiAffinity {item['anti_affinity']}, nodes eligible under scheduling constraints {item['eligible_nodes']}{tail}"
    )


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
    prom = (
        f"Prometheus: {pods} pod{'s' if pods != 1 else ''} ended by OOM in 7 days"
        + (f", {rep} already replaced" if rep else "")
        + f", {item.get('restarts_of_those_pods') or 0} restarts in those pods"
        # of the pods that were ended by OOM, not of the workload's current pod: a replacement pod's own restarts are not counted here
        + ((" (none of those pods is running now)" if rep >= pods else f" (those of them still running: {item.get('live_pod_restarts_max') or 0} at most)") if rep else "")
    )
    now = item.get("pods_now")
    running = ""
    if now:

        def one(p: dict) -> str:
            if p.get("restarts") is None:
                return f"{p['pod']} (created {p.get('created')})"
            last = f", its previous run ended {p['last_ended']} with reason {p.get('last_reason')}, exit code {p.get('last_exit_code')}" if p.get("last_ended") else ""
            return f"{p['pod']} (created {p.get('created')}, {p['restarts']} restart{'s' if p['restarts'] != 1 else ''} of this container since{last})"

        running = ". Running now: " + ", ".join(one(p) for p in now)
    return f"{kern}. {prom}. cAdvisor counter {item.get('cadvisor_oom_events_7d') or 0}{running}"


def argocd_backend_text(item) -> str:
    """argocd.backend-errors: the controller's connection to the cluster, its caches, git, redis, the repo-server queue and the gRPC error counts."""
    return (
        f"cluster connection {item['cluster_connection_ok']}, cache age {item['cluster_cache_age_s']}s, k8s API 5xx/429 {item['k8s_api_errors']}, "
        f"git requests {item['git_requests']} / failures {item['git_failures']} ({item['git_failure_ratio']}), redis failures {item['redis_failed']}/{item['redis_total']}, "
        f"repo-server pending {item['repo_pending_requests']}, gRPC errors {item['grpc_errors']} (PermissionDenied {item['grpc_permission_denied']} and Unauthenticated {item['grpc_unauthenticated']} counted separately)"
    )


def throttling_text(labels, v, threshold, warn_threshold) -> str:
    """resources.cpu-throttling: the 5-minute and 24-hour throttling ratios of a pod and which of the two thresholds the day crosses."""
    now = f"pod {labels['pod']}: throttling ratio now {v.get('cpu_throttle_ratio_5m', 0):.2f}"
    if "cpu_throttle_ratio_24h" not in v:
        return now + ", no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most"
    day = v["cpu_throttle_ratio_24h"]
    if day >= threshold:
        verdict = "throttled through the day"
    elif day >= warn_threshold:
        verdict = "throttled through the day, below the fail line"
    else:
        verdict = "throttled this moment, not through the day"
    tail = "; no 5-minute value, under 0.01 now" if "cpu_throttle_ratio_5m" not in v else ""
    return f"{now}, 24 h or the pod's life {day:.2f}: {verdict}{tail}"


def oom_last_text(summary, labels) -> str:
    """resources.oomkilled: when the container was last OOMKilled, from summary.resilience.restarts.oom_last keyed namespace/pod/container."""
    key = f"{labels['namespace']}/{labels['pod']}/{labels['container']}"
    last = ((summary.get("resilience") or {}).get("restarts") or {}).get("oom_last", {}).get(key, {})
    return f"pod {labels['pod']}: last termination reason OOMKilled, finished at {last.get('finished')} ({last.get('age_days')} days ago). The container has restarted {last.get('restarts')} times since the pod was created, for any reason and not only in the last 7 days. An OOM older than 7 days is warn, older than 30 days is excluded"


def no_backup_text(signals: dict) -> str:
    """resilience.no-backup: no backup tool, and the signals that may stand in for one (`Context.backup_signals()`)."""
    stale = signals["stale_backup_cronjobs"]
    extra = f"; backup-like CronJobs that are suspended or have not succeeded in 7 days, not counted: {stale}" if stale else ""
    return (
        f"no backup tool (family backup). Alternative signals: etcd snapshots {signals['etcd_snapshots']}, backup-like CronJobs that ran in the last 7 days {signals['backup_cronjobs']}, "
        f"VolumeSnapshots {signals['volume_snapshots']}{extra}. If signals exist, the LLM checks whether copies leave the node"
    )


def n_plus_one_text(item) -> str:
    """resilience.n-plus-one: what is left without the largest node against the requests, the pools short of room, and whether an autoscaler would replace the node."""
    pools = item.get("pools_short") or []
    pools_text = (
        " Pools short of room: "
        + "; ".join(
            f"{p['pods']} pods limited to {', '.join(p['eligible_nodes']) or 'no other node'} need {p['needed_cpu']} cores and {p['needed_memory_gb']} GB, free there {p['free_cpu']} cores and {p['free_memory_gb']} GB" for p in pools
        )
        + "."
        if pools
        else ""
    )
    tight = " Fits only inside the 2% margin." if item.get("tight") and not pools else ""
    autoscaler = f"{item.get('autoscaler_name') or 'present'} (delay until a new node)" if item.get("autoscaler", item.get("karpenter")) else "absent (permanent)"
    return (
        f"Allocatable without the largest node {item['largest_node']} ({item['largest_node_cpu']} cores, {item['largest_node_memory_gb']}GB): "
        f"CPU {item['allocatable_cpu_without_largest']} cores vs total requests {item['requests_cpu_total']} ({'OK' if item['cpu_ok'] else 'short'}), "
        f"memory {item['allocatable_memory_gb_without_largest']}GB vs {item['requests_memory_gb_total']}GB ({'OK' if item['memory_ok'] else 'short'}). "
        f"Pods on that node {item['pods_on_largest_node']} (prod {item['prod_pods_on_largest_node']}). Pods that fit on no other node {item['cannot_fit_elsewhere']}.{pools_text}{tight} Node autoscaler {autoscaler}"
    )


def ingress_5xx_text(item) -> str:
    """traffic.ingress-5xx-ratio: the 5xx share of an ingress over its window, with the low-traffic clause that makes it warn only."""
    m = item["metrics"]
    requests_a_day = m.get("requests_24h_equiv") if m.get("requests_24h_equiv") is not None else m.get("requests") or 0
    low = " (under 100 requests a day and under 10 errors: warn only)" if requests_a_day < 100 and (m.get("errors_5xx") or 0) < 10 else ""
    return f"{item['hosts'][:2]}: {m.get('window')} 5xx {m.get('errors_5xx')} of {m.get('requests')} requests = {(m.get('errors_ratio') or 0) * 100:.2f}%{low} (source {m.get('source')}), p95 max {m.get('p95_s_max_1h')}s"


def ingress_latency_text(item) -> str:
    """traffic.ingress-p95-latency: the p95 figures of an ingress (weighted, hourly average, 1h max, the latest hour with requests) and its traffic."""
    m = item["metrics"]
    at = f" at {str(m.get('p95_s_last_at'))[:16]}" if m.get("p95_s_last_at") else ""
    since = f", {m.get('hours_since_requests')} hours before the newest hour, no requests since" if (m.get("hours_since_requests") or 0) > 0 else ""
    low = " (under 100 requests a day: warn only)" if m.get("requests_24h_equiv") is not None and m.get("requests_24h_equiv") < 100 else ""
    return (
        f"{item['hosts'][:2]}: p95 request-weighted {m.get('p95_s_weighted')}s, hourly average {m.get('p95_s_avg')}s, 1h max {m.get('p95_s_max_1h')}s, "
        f"latest hour with requests {m.get('p95_s_last_1h')}s on {m.get('requests_last_1h')} requests{at}{since}, {m.get('requests')} requests/{m.get('window')}{low} (source {m.get('source')})"
    )


def nginx_vulnerable_text(item) -> str:
    """traffic.ingress-nginx-vulnerable-version: the controller version against the fixed ones, the admission webhook and whether a NetworkPolicy closes its port."""
    controllers = ", ".join(f"{c['kind']} {c['namespace']}/{c['name']}" for c in item["controllers"])
    unknown = f"; no version in the image tag of {', '.join(item['unknown_version_controllers'])}" if item["unknown_version_controllers"] else ""
    policy = f", failurePolicy {item['admission_webhooks'][0]['failure_policy']}" if item["admission_webhooks"] else ""
    netpol = item.get("webhook_network_policy") or {}
    closed = f"; webhook port closed to pods by NetworkPolicy {', '.join(netpol.get('policies') or [])}" if netpol.get("mitigated") else ""
    return f"ingress-nginx {item['version'] or 'version unknown'} ({controllers}){unknown}; fixed in {' and '.join(item['fixed_versions'])}; admission webhook {'on' if item['admission_webhook'] else 'off'}{policy}{closed}"


def ecr_stale_storage_text(item) -> str:
    """ecr.stale-storage: repositories nobody pulls, repositories the cluster does not use, empty ones, and the largest by stored size."""
    stale = "; ".join(f"{r['name']} {r['gib']} GiB" + (", never pulled" if r["days_since_pull"] is None else f", last pull {r['days_since_pull']} days ago") for r in item["repos_stale_pull"][:8])
    largest = ", ".join(f"{r['name']} {r['gib']} GiB" for r in item["largest_repos"])
    return (
        f"repositories with no pull for more than {item['stale_pull_days']} days: {stale} (total {item['stale_pull_gib']} GiB), "
        f"repositories not used by the cluster {item['repos_unused_by_cluster']} (total {item['unused_gib']} GiB), empty repositories {item['repos_empty']}, largest repositories by stored size {largest}"
    )


def metallb_speaker_text(item) -> str:
    """traffic.metallb-speaker-not-ready: speaker and controller readiness against the nodes and the LoadBalancer Services."""
    head = ("no speaker DaemonSet found: " if item["speaker_desired"] is None else "") + ("no MetalLB controller found: " if item["controller_replicas"] is None else "")
    return head + (
        f"{item['lb_services']} LoadBalancer services, speaker ready {item['speaker_ready']}/{item['speaker_desired']} ({item['nodes_total']} nodes, all nodes {item['speaker_all_nodes']}, nodes it can run on {item.get('speaker_eligible')}), "
        f"controller {item['controller_ready']}/{item['controller_replicas']}, speakers with metrics read {item['speakers_read']}, unreadable {item['speakers_unreadable']}, version {item['version']}, mode {item['mode']}"
    )


def metallb_config_text(item) -> str:
    """traffic.metallb-config-stale: the config state of the MetalLB components and the counters that are only there when the speaker metrics were read."""

    def counter(key: str):
        return item[key] if item["update_errors_read"] else "not read"

    bgp = item["bgp_sessions"]
    up = item["bgp_sessions_up"] if bgp is not None else "not read"
    return (
        f"source {item['config_source']}: components with stale/unloaded config {item['config_stale_pods']}, errors {item['config_errors']}, not reported {item['config_not_reported']}, "
        f"k8s client update errors {counter('update_errors_total')}, ARP requests/responses {counter('arp_requests_total')}/{counter('arp_responses_total')}, gratuitous ARP {counter('gratuitous_total')}, "
        f"BGP sessions up {up}/{bgp if bgp is not None else 'not read'}"
    )


def snat_private_routes_text(item) -> str:
    """vpccni.external-snat-off-with-private-routes: the private routes SNAT still applies to, by kind, and the destinations exempted by the CNI's own list."""
    where = "in the node subnets" if item.get("scoped_to_node_subnets") else "in the cluster VPC"
    excluded = f"; exempted by AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS {item.get('excluded_destinations')}" if item.get("excluded_destinations") else ""
    return (
        f"AWS_VPC_K8S_CNI_EXTERNALSNAT false; private routes {where}: peering {item['peering_routes']}, transit gateway {item['transit_gateway_routes']}, VPN {item['vpn_routes']}, "
        f"Outposts local gateway {item['local_gateway_routes']}, appliance {item.get('appliance_routes', 0)}; destinations still SNATed {item['private_destinations'][:6]}{excluded}"
    )

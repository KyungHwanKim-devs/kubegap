"""The twelve evidence helpers of #24 say exactly what the expressions they replaced said. Each former expression is kept here as the oracle and
evaluated with the same names the evaluator gave it (`item`, `labels`, `v`, the thresholds, `summary`, `backup_signals`); the helper must give the same
sentence on inputs that walk every branch."""

from __future__ import annotations

from lib.judgement.evaluate import evidence
from lib.judgement.evaluate.rules import SAFE_BUILTINS

FORMER = {
    "argocd.backend-errors": "f\"cluster connection {item['cluster_connection_ok']}, cache age {item['cluster_cache_age_s']}s, k8s API 5xx/429 {item['k8s_api_errors']}, git requests {item['git_requests']} / failures {item['git_failures']} ({item['git_failure_ratio']}), redis failures {item['redis_failed']}/{item['redis_total']}, repo-server pending {item['repo_pending_requests']}, gRPC errors {item['grpc_errors']} (PermissionDenied {item['grpc_permission_denied']} and Unauthenticated {item['grpc_unauthenticated']} counted separately)\"",
    "resources.cpu-throttling": "(f\"pod {labels['pod']}: throttling ratio now {v.get('cpu_throttle_ratio_5m', 0):.2f}, 24 h or the pod's life {v['cpu_throttle_ratio_24h']:.2f}: \" + ('throttled through the day' if v['cpu_throttle_ratio_24h'] >= threshold else ('throttled through the day, below the fail line' if v['cpu_throttle_ratio_24h'] >= warn_threshold else 'throttled this moment, not through the day')) + ('; no 5-minute value, under 0.01 now' if 'cpu_throttle_ratio_5m' not in v else '')) if 'cpu_throttle_ratio_24h' in v else f\"pod {labels['pod']}: throttling ratio now {v.get('cpu_throttle_ratio_5m', 0):.2f}, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most\"",
    "resources.oomkilled": "f\"pod {labels['pod']}: last termination reason OOMKilled, finished at {((summary.get('resilience') or {}).get('restarts') or {}).get('oom_last', {}).get(labels['namespace'] + '/' + labels['pod'] + '/' + labels['container'], {}).get('finished')} ({((summary.get('resilience') or {}).get('restarts') or {}).get('oom_last', {}).get(labels['namespace'] + '/' + labels['pod'] + '/' + labels['container'], {}).get('age_days')} days ago), {((summary.get('resilience') or {}).get('restarts') or {}).get('oom_last', {}).get(labels['namespace'] + '/' + labels['pod'] + '/' + labels['container'], {}).get('restarts')} restarts. An OOM older than 7 days is warn, older than 30 days is excluded\"",
    "resilience.no-backup": "f\"no backup tool (family backup). Alternative signals: etcd snapshots {backup_signals()['etcd_snapshots']}, backup-like CronJobs that ran in the last 7 days {backup_signals()['backup_cronjobs']}, VolumeSnapshots {backup_signals()['volume_snapshots']}{'; backup-like CronJobs that are suspended or have not succeeded in 7 days, not counted: ' + str(backup_signals()['stale_backup_cronjobs']) if backup_signals()['stale_backup_cronjobs'] else ''}. If signals exist, the LLM checks whether copies leave the node\"",
    "resilience.n-plus-one": "f\"Allocatable without the largest node {item['largest_node']} ({item['largest_node_cpu']} cores, {item['largest_node_memory_gb']}GB): CPU {item['allocatable_cpu_without_largest']} cores vs total requests {item['requests_cpu_total']} ({'OK' if item['cpu_ok'] else 'short'}), memory {item['allocatable_memory_gb_without_largest']}GB vs {item['requests_memory_gb_total']}GB ({'OK' if item['memory_ok'] else 'short'}). Pods on that node {item['pods_on_largest_node']} (prod {item['prod_pods_on_largest_node']}). Pods that fit on no other node {item['cannot_fit_elsewhere']}.{' Pools short of room: ' + '; '.join(str(p['pods']) + ' pods limited to ' + (', '.join(p['eligible_nodes']) or 'no other node') + ' need ' + str(p['needed_cpu']) + ' cores and ' + str(p['needed_memory_gb']) + ' GB, free there ' + str(p['free_cpu']) + ' cores and ' + str(p['free_memory_gb']) + ' GB' for p in item.get('pools_short') or []) + '.' if item.get('pools_short') else ''}{' Fits only inside the 2% margin.' if item.get('tight') and not item.get('pools_short') else ''} Node autoscaler {(item.get('autoscaler_name') or 'present') + ' (delay until a new node)' if item.get('autoscaler', item.get('karpenter')) else 'absent (permanent)'}\"",
    "traffic.ingress-5xx-ratio": "f\"{item['hosts'][:2]}: {item['metrics'].get('window')} 5xx {item['metrics'].get('errors_5xx')} of {item['metrics'].get('requests')} requests = {(item['metrics'].get('errors_ratio') or 0)*100:.2f}%{' (under 100 requests a day and under 10 errors: warn only)' if (item['metrics'].get('requests_24h_equiv') if item['metrics'].get('requests_24h_equiv') is not None else item['metrics'].get('requests') or 0) < 100 and (item['metrics'].get('errors_5xx') or 0) < 10 else ''} (source {item['metrics'].get('source')}), p95 max {item['metrics'].get('p95_s_max_1h')}s\"",
    "traffic.ingress-p95-latency": "f\"{item['hosts'][:2]}: p95 request-weighted {item['metrics'].get('p95_s_weighted')}s, hourly average {item['metrics'].get('p95_s_avg')}s, 1h max {item['metrics'].get('p95_s_max_1h')}s, latest hour with requests {item['metrics'].get('p95_s_last_1h')}s on {item['metrics'].get('requests_last_1h')} requests{' at ' + str(item['metrics'].get('p95_s_last_at'))[:16] if item['metrics'].get('p95_s_last_at') else ''}{', ' + str(item['metrics'].get('hours_since_requests')) + ' hours before the newest hour, no requests since' if (item['metrics'].get('hours_since_requests') or 0) > 0 else ''}, {item['metrics'].get('requests')} requests/{item['metrics'].get('window')}{' (under 100 requests a day: warn only)' if item['metrics'].get('requests_24h_equiv') is not None and item['metrics'].get('requests_24h_equiv') < 100 else ''} (source {item['metrics'].get('source')})\"",
    "traffic.ingress-nginx-vulnerable-version": "f\"ingress-nginx {item['version'] or 'version unknown'} ({', '.join(c['kind'] + ' ' + c['namespace'] + '/' + c['name'] for c in item['controllers'])}){'; no version in the image tag of ' + ', '.join(item['unknown_version_controllers']) if item['unknown_version_controllers'] else ''}; fixed in {' and '.join(item['fixed_versions'])}; admission webhook {'on' if item['admission_webhook'] else 'off'}{', failurePolicy ' + str(item['admission_webhooks'][0]['failure_policy']) if item['admission_webhooks'] else ''}{'; webhook port closed to pods by NetworkPolicy ' + ', '.join((item.get('webhook_network_policy') or {}).get('policies') or []) if (item.get('webhook_network_policy') or {}).get('mitigated') else ''}\"",
    "ecr.stale-storage": "f\"repositories with no pull for more than {item['stale_pull_days']} days: {'; '.join(str(r['name']) + ' ' + str(r['gib']) + ' GiB' + (', never pulled' if r['days_since_pull'] is None else ', last pull ' + str(r['days_since_pull']) + ' days ago') for r in item['repos_stale_pull'][:8])} (total {item['stale_pull_gib']} GiB), repositories not used by the cluster {item['repos_unused_by_cluster']} (total {item['unused_gib']} GiB), empty repositories {item['repos_empty']}, largest repositories by stored size {', '.join(str(r['name']) + ' ' + str(r['gib']) + ' GiB' for r in item['largest_repos'])}\"",
    "traffic.metallb-speaker-not-ready": "('no speaker DaemonSet found: ' if item['speaker_desired'] is None else '') + ('no MetalLB controller found: ' if item['controller_replicas'] is None else '') + f\"{item['lb_services']} LoadBalancer services, speaker ready {item['speaker_ready']}/{item['speaker_desired']} ({item['nodes_total']} nodes, all nodes {item['speaker_all_nodes']}, nodes it can run on {item.get('speaker_eligible')}), controller {item['controller_ready']}/{item['controller_replicas']}, speakers with metrics read {item['speakers_read']}, unreadable {item['speakers_unreadable']}, version {item['version']}, mode {item['mode']}\"",
    "traffic.metallb-config-stale": "f\"source {item['config_source']}: components with stale/unloaded config {item['config_stale_pods']}, errors {item['config_errors']}, not reported {item['config_not_reported']}, k8s client update errors {item['update_errors_total'] if item['update_errors_read'] else 'not read'}, ARP requests/responses {item['arp_requests_total'] if item['update_errors_read'] else 'not read'}/{item['arp_responses_total'] if item['update_errors_read'] else 'not read'}, gratuitous ARP {item['gratuitous_total'] if item['update_errors_read'] else 'not read'}, BGP sessions up {item['bgp_sessions_up'] if item['bgp_sessions'] is not None else 'not read'}/{item['bgp_sessions'] if item['bgp_sessions'] is not None else 'not read'}\"",
    "vpccni.external-snat-off-with-private-routes": "f\"AWS_VPC_K8S_CNI_EXTERNALSNAT false; private routes {'in the node subnets' if item.get('scoped_to_node_subnets') else 'in the cluster VPC'}: peering {item['peering_routes']}, transit gateway {item['transit_gateway_routes']}, VPN {item['vpn_routes']}, Outposts local gateway {item['local_gateway_routes']}, appliance {item.get('appliance_routes', 0)}; destinations still SNATed {item['private_destinations'][:6]}{'; exempted by AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS ' + str(item.get('excluded_destinations')) if item.get('excluded_destinations') else ''}\"",
}


def former(check_id: str, **env) -> str:
    return eval(FORMER[check_id], {"__builtins__": SAFE_BUILTINS}, env)


def test_argocd_backend_text():
    item = {
        "cluster_connection_ok": True,
        "cluster_cache_age_s": 12,
        "k8s_api_errors": 3,
        "git_requests": 40,
        "git_failures": 2,
        "git_failure_ratio": 0.05,
        "redis_failed": 1,
        "redis_total": 9,
        "repo_pending_requests": 0,
        "grpc_errors": 4,
        "grpc_permission_denied": 1,
        "grpc_unauthenticated": 2,
    }
    assert evidence.argocd_backend_text(item) == former("argocd.backend-errors", item=item)


def test_throttling_text_walks_the_four_branches():
    labels = {"pod": "api-1"}
    for v in ({"cpu_throttle_ratio_5m": 0.3, "cpu_throttle_ratio_24h": 0.6}, {"cpu_throttle_ratio_5m": 0.3, "cpu_throttle_ratio_24h": 0.3}, {"cpu_throttle_ratio_24h": 0.1}, {"cpu_throttle_ratio_5m": 0.9}):
        assert evidence.throttling_text(labels, v, 0.5, 0.25) == former("resources.cpu-throttling", labels=labels, v=v, threshold=0.5, warn_threshold=0.25)


def test_oom_last_text_with_and_without_a_recorded_kill():
    labels = {"namespace": "web", "pod": "api-1", "container": "app"}
    summary = {"resilience": {"restarts": {"oom_last": {"web/api-1/app": {"finished": "2026-11-01T00:00:00Z", "age_days": 6, "restarts": 3}}}}}
    assert evidence.oom_last_text(summary, labels) == former("resources.oomkilled", summary=summary, labels=labels)
    assert evidence.oom_last_text({}, labels) == former("resources.oomkilled", summary={}, labels=labels)


def test_no_backup_text_with_and_without_stale_cronjobs():
    for stale in ([], ["ops/db-backup"]):
        signals = {"etcd_snapshots": 2, "backup_cronjobs": 1, "volume_snapshots": 0, "stale_backup_cronjobs": stale}
        assert evidence.no_backup_text(signals) == former("resilience.no-backup", backup_signals=lambda: signals)


def _n1(**over):
    item = {
        "largest_node": "n1",
        "largest_node_cpu": 8,
        "largest_node_memory_gb": 32.0,
        "allocatable_cpu_without_largest": 12.5,
        "requests_cpu_total": 10.1,
        "cpu_ok": True,
        "allocatable_memory_gb_without_largest": 50.0,
        "requests_memory_gb_total": 60.0,
        "memory_ok": False,
        "pods_on_largest_node": 20,
        "prod_pods_on_largest_node": 5,
        "cannot_fit_elsewhere": 1,
    }
    item.update(over)
    return item


def test_n_plus_one_text_walks_pools_tight_and_autoscaler():
    pool = {"pods": 2, "eligible_nodes": ["n2", "n3"], "needed_cpu": 1.5, "needed_memory_gb": 4.0, "free_cpu": 0.5, "free_memory_gb": 1.0}
    lonely = {**pool, "eligible_nodes": []}
    for item in (_n1(), _n1(pools_short=[pool, lonely]), _n1(tight=True), _n1(tight=True, pools_short=[pool]), _n1(autoscaler=True, autoscaler_name="karpenter"), _n1(karpenter=True), _n1(autoscaler=True)):
        assert evidence.n_plus_one_text(item) == former("resilience.n-plus-one", item=item)


def _ingress(**metrics):
    return {"hosts": ["a.example", "b.example", "c.example"], "metrics": metrics}


def test_ingress_5xx_text_low_traffic_clause():
    base = {"window": "24h", "errors_5xx": 4, "requests": 50, "errors_ratio": 0.08, "source": "nginx", "p95_s_max_1h": 1.2}
    for m in (base, {**base, "requests_24h_equiv": 500}, {**base, "requests_24h_equiv": 20, "errors_5xx": 40}, {**base, "requests": None, "errors_ratio": None}):
        item = _ingress(**m)
        assert evidence.ingress_5xx_text(item) == former("traffic.ingress-5xx-ratio", item=item)


def test_ingress_latency_text_walks_at_since_and_low():
    base = {"p95_s_weighted": 0.4, "p95_s_avg": 0.3, "p95_s_max_1h": 2.0, "p95_s_last_1h": 0.5, "requests_last_1h": 30, "requests": 900, "window": "24h", "source": "nginx"}
    for m in (base, {**base, "p95_s_last_at": "2026-11-07T10:00:00+09:00"}, {**base, "hours_since_requests": 5}, {**base, "requests_24h_equiv": 40}, {**base, "requests_24h_equiv": 400, "hours_since_requests": 0}):
        item = _ingress(**m)
        assert evidence.ingress_latency_text(item) == former("traffic.ingress-p95-latency", item=item)


def test_nginx_vulnerable_text_walks_unknown_policy_and_netpol():
    base = {
        "version": "1.11.0",
        "controllers": [{"kind": "Deployment", "namespace": "ingress", "name": "ctl"}],
        "unknown_version_controllers": [],
        "fixed_versions": ["1.11.5", "1.12.1"],
        "admission_webhook": True,
        "admission_webhooks": [{"failure_policy": "Fail"}],
    }
    for item in (
        base,
        {**base, "version": None, "unknown_version_controllers": ["ingress/ctl"], "admission_webhook": False, "admission_webhooks": []},
        {**base, "webhook_network_policy": {"mitigated": True, "policies": ["ingress/webhook-only"]}},
        {**base, "webhook_network_policy": {"mitigated": False}},
    ):
        assert evidence.nginx_vulnerable_text(item) == former("traffic.ingress-nginx-vulnerable-version", item=item)


def test_ecr_stale_storage_text_cuts_at_eight_and_names_never_pulled():
    repos = [{"name": f"r{i}", "gib": i * 1.5, "days_since_pull": None if i % 2 else 100 + i} for i in range(10)]
    item = {"stale_pull_days": 90, "repos_stale_pull": repos, "stale_pull_gib": 40.5, "repos_unused_by_cluster": 3, "unused_gib": 9.0, "repos_empty": 2, "largest_repos": repos[:3]}
    assert evidence.ecr_stale_storage_text(item) == former("ecr.stale-storage", item=item)


def test_metallb_speaker_text_with_and_without_the_daemonset_and_controller():
    base = {
        "lb_services": 4,
        "speaker_ready": 2,
        "speaker_desired": 3,
        "nodes_total": 3,
        "speaker_all_nodes": False,
        "speaker_eligible": 3,
        "controller_ready": 1,
        "controller_replicas": 1,
        "speakers_read": 2,
        "speakers_unreadable": 1,
        "version": "0.14.9",
        "mode": "l2",
    }
    for item in (base, {**base, "speaker_desired": None}, {**base, "controller_replicas": None}, {**base, "speaker_desired": None, "controller_replicas": None}):
        assert evidence.metallb_speaker_text(item) == former("traffic.metallb-speaker-not-ready", item=item)


def test_metallb_config_text_counters_read_or_not():
    base = {
        "config_source": "metrics",
        "config_stale_pods": 0,
        "config_errors": 1,
        "config_not_reported": 0,
        "update_errors_read": True,
        "update_errors_total": 2,
        "arp_requests_total": 30,
        "arp_responses_total": 29,
        "gratuitous_total": 3,
        "bgp_sessions": 2,
        "bgp_sessions_up": 1,
    }
    for item in (base, {**base, "update_errors_read": False}, {**base, "bgp_sessions": None, "bgp_sessions_up": None}):
        assert evidence.metallb_config_text(item) == former("traffic.metallb-config-stale", item=item)


def test_metallb_config_text_reads_no_counter_it_does_not_show():
    """An ItemRecorder keeps the keys the sentence read; the counters stay unread when the speaker metrics were not."""
    seen = set()

    class Recorder(dict):
        def __getitem__(self, k):
            seen.add(k)
            return super().__getitem__(k)

    item = Recorder(
        {
            "config_source": "x",
            "config_stale_pods": 0,
            "config_errors": 0,
            "config_not_reported": 0,
            "update_errors_read": False,
            "update_errors_total": 9,
            "arp_requests_total": 9,
            "arp_responses_total": 9,
            "gratuitous_total": 9,
            "bgp_sessions": None,
            "bgp_sessions_up": None,
        }
    )
    evidence.metallb_config_text(item)
    assert "update_errors_total" not in seen and "arp_requests_total" not in seen and "bgp_sessions_up" not in seen


def test_snat_private_routes_text_scope_and_exemptions():
    base = {"peering_routes": 2, "transit_gateway_routes": 1, "vpn_routes": 0, "local_gateway_routes": 0, "private_destinations": [f"10.{i}.0.0/16" for i in range(8)]}
    for item in (base, {**base, "scoped_to_node_subnets": True, "appliance_routes": 1}, {**base, "excluded_destinations": ["10.9.0.0/16"]}):
        assert evidence.snat_private_routes_text(item) == former("vpccni.external-snat-off-with-private-routes", item=item)

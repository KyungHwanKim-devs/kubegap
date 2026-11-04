"""The pod-metrics tables resolve a metric to the spelling the running version emits, and the parsers read one spelling, never two (#120).
The fixtures are written from the components' sources at the tags named in collectors/<area>/pod-metrics.yaml, not from a cluster."""

from __future__ import annotations

import json
from pathlib import Path

from lib import collect, karpenterctl, kedactl, podmetrics, promtext, stackhealth, yamlite

ROOT = Path(__file__).resolve().parent.parent

# kubernetes-sigs/karpenter pkg/metrics/metrics.go, pkg/controllers/metrics/nodepool/controller.go, pkg/controllers/disruption/metrics.go,
# pkg/controllers/metrics/pod/controller.go, aws/karpenter-provider-aws pkg/controllers/interruption/metrics.go — v0.37.0 spellings
KARPENTER_0 = """leader_election_master_status{name="karpenter-leader-election"} 1
process_start_time_seconds 1.7e9
process_resident_memory_bytes 2e8
karpenter_nodepool_usage{nodepool="default",resource_type="cpu"} 40
karpenter_nodepool_limit{nodepool="default",resource_type="cpu"} 100
karpenter_nodeclaims_created{reason="provisioning",nodepool="default",capacity_type="spot"} 12
karpenter_nodeclaims_terminated{reason="expiration",nodepool="default",capacity_type="spot"} 3
karpenter_nodeclaims_disrupted{type="consolidation",nodepool="default"} 5
karpenter_interruption_received_messages{message_type="SpotInterruptionKind"} 7
karpenter_interruption_actions_performed{action_type="CordonAndDrain"} 7
karpenter_interruption_deleted_messages 7
karpenter_consistency_errors{check="NodeShape"} 2
karpenter_cluster_state_synced 1
karpenter_pods_startup_time_seconds_sum 120
karpenter_pods_startup_time_seconds_count 10
karpenter_disruption_eligible_nodes{method="consolidation",consolidation_type="single"} 2
karpenter_disruption_budgets_allowed_disruptions{nodepool="default"} 1
karpenter_provisioner_scheduling_queue_depth 0
"""

# the same facts as Karpenter v1.15.1 spells them (no release emits both sets)
KARPENTER_1 = """leader_election_master_status{name="karpenter-leader-election"} 1
process_start_time_seconds 1.7e9
process_resident_memory_bytes 2e8
karpenter_nodepools_usage{nodepool="default",resource_type="cpu"} 40
karpenter_nodepools_limit{nodepool="default",resource_type="cpu"} 100
karpenter_nodeclaims_created_total{reason="provisioning",nodepool="default",min_values_relaxed="false"} 12
karpenter_nodeclaims_terminated_total{nodepool="default",capacity_type="spot",zone="ap-northeast-2a"} 3
karpenter_nodeclaims_disrupted_total{reason="underutilized",nodepool="default",capacity_type="spot"} 5
karpenter_interruption_received_messages_total{message_type="SpotInterruptionKind"} 7
karpenter_interruption_deleted_messages_total 7
karpenter_cluster_state_synced 1
karpenter_pods_startup_duration_seconds_sum 120
karpenter_pods_startup_duration_seconds_count 10
karpenter_voluntary_disruption_eligible_nodes{reason="underutilized"} 2
karpenter_nodepools_allowed_disruptions{nodepool="default",reason="underutilized"} 1
karpenter_scheduler_queue_depth 0
"""


def _snap(tmp_path, folder, text):
    d = tmp_path / "metrics" / "pod" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "pod-0.prom").write_text(text)
    return tmp_path


def _keep(area, sid):
    st = next(s for s in yamlite.load_file(ROOT / "collectors" / area / "collect.yaml") if s.get("id") == sid)
    return collect._metrics_filter(st.get("keep"))


def test_karpenter_both_spellings_give_the_same_summary(tmp_path):
    out = {}
    for tag, text in (("0.37", KARPENTER_0), ("1.15", KARPENTER_1)):
        kept = _keep("karpenter", "controller-metrics")(text)  # what the step would have saved: the keep filter must let both spellings through
        pods = karpenterctl._pod_metrics(_snap(tmp_path / tag, "karpenter", kept))
        out[tag] = pods["pod-0"]
    for tag in out:
        p = out[tag]
        assert p["leader"] and p["nodepool_usage_ratio"] == {"default/cpu": 0.4}
        assert p["nodeclaims_created_by_reason"] == {"provisioning": 12}
        assert p["interruption_messages_by_type"] == {"SpotInterruptionKind": 7} and p["interruption_deleted_messages"] == 7
        assert p["cluster_state_synced"] is True and p["pods_startup_avg_s"] == 12.0 and p["pods_startup_count"] == 10
        assert p["disruption_budgets_allowed"] == {"default/-": 1} or p["disruption_budgets_allowed"] == {"default/underutilized": 1}
        assert p["scheduling_queue_depth"] == 0
    assert out["0.37"]["names"]["nodepool_usage"] == "karpenter_nodepool_usage" and out["1.15"]["names"]["nodepool_usage"] == "karpenter_nodepools_usage"
    # what 1.0 removed is None, not zero: the report says "not emitted by this version" instead of "no interruption actions"
    assert out["0.37"]["interruption_actions"] == {"CordonAndDrain": 7} and out["0.37"]["consistency_errors"] == 2
    assert out["1.15"]["interruption_actions"] is None and out["1.15"]["consistency_errors"] is None
    assert out["0.37"]["nodeclaims_terminated_by_reason"] == {"expiration": 3} and out["1.15"]["nodeclaims_terminated_by_reason"] is None  # 1.x dropped the reason label: None, not pool names
    assert out["0.37"]["nodeclaims_disrupted_by_reason"] == {"consolidation": 5} and out["1.15"]["nodeclaims_disrupted_by_reason"] == {"underutilized": 5}  # 0.x type, 1.x reason


def test_a_fresh_karpenter_1x_with_no_series_yet_still_reports_the_removed_metrics_as_removed(tmp_path):
    """Before any NodePool exists no nodepools_* series proves the generation; the controller image version does."""
    pods = karpenterctl._pod_metrics(_snap(tmp_path, "karpenter", "karpenter_cluster_state_synced 1\nprocess_start_time_seconds 1.7e9\n"), version="1.15.1")
    assert pods["pod-0"]["interruption_actions"] is None and pods["pod-0"]["consistency_errors"] is None and pods["pod-0"]["nodes_disrupted_total"] is None
    pods = karpenterctl._pod_metrics(_snap(tmp_path / "old", "karpenter", "karpenter_cluster_state_synced 1\n"), version="0.37.0")
    assert pods["pod-0"]["interruption_actions"] == {} and pods["pod-0"]["consistency_errors"] is None  # 0.x: no series yet is {} / absent, not removed


def test_two_spellings_in_one_text_are_never_added():
    pm = promtext.parse('karpenter_nodeclaims_created_total{reason="a"} 5\nkarpenter_nodeclaims_created{reason="a"} 100\n')
    assert podmetrics.by_label(pm, "karpenter", "nodeclaims_created", "reason") == {"a": 5.0}


# kedacore/keda pkg/metricscollector/prommetrics.go: v2.16.0 (both generations present) and v2.17.2 (only the newer)
KEDA_216 = """keda_build_info{version="2.16.0"} 1
keda_scaler_errors_total{namespace="prod",scaledObject="web",scaler="prometheusScaler",metric="s0-prometheus",triggerIndex="0",type="prometheus"} 4
keda_scaler_detail_errors_total{namespace="prod",scaledObject="web",scaler="prometheusScaler",metric="s0-prometheus",triggerIndex="0",type="prometheus"} 4
keda_scaled_object_errors_total{namespace="prod",scaledObject="web"} 4
keda_scaler_errors{namespace="prod",scaledObject="web",scaler="prometheusScaler",metric="s0-prometheus",triggerIndex="0",type="prometheus"} 1
"""
KEDA_217 = """keda_build_info{version="2.17.2"} 1
keda_scaler_detail_errors_total{namespace="prod",scaledObject="web",scaler="prometheusScaler",metric="s0-prometheus",triggerIndex="0",type="prometheus"} 4
keda_scaled_object_errors_total{namespace="prod",scaledObject="web"} 4
"""


def test_keda_scaler_errors_are_read_once_in_both_generations(tmp_path):
    for tag, text in (("2.16", KEDA_216), ("2.17", KEDA_217)):
        snap = _snap(tmp_path / tag, "keda-operator", _keep("keda", "operator-metrics")(text))
        (snap / "objects").mkdir(exist_ok=True)
        so = {"metadata": {"name": "web", "namespace": "prod"}, "spec": {"scaleTargetRef": {"name": "web"}, "triggers": [{"type": "prometheus", "metadata": {}}]}, "status": {}}
        (snap / "objects" / "scaledobjects.keda.sh.json").write_text(json.dumps({"items": [so]}))  # the analyzer needs KEDA to be present
        res = kedactl.analyze(snap, {"namespaces": {"prod_like": ["prod"]}}, {})
        s = res["summary"]
        assert s["scaler_errors_total"] == 4 and s["scaled_object_errors_total"] == 4, (tag, s)
        assert s["operator_metrics_present"] is True
        assert s["operator_metrics_names"]["scaler_errors"] == "keda_scaler_detail_errors_total"


# grafana/grafana pkg/infra/metrics/metrics.go: grafana_stat_total_users is singular
GRAFANA = """grafana_build_info{version="12.2.1",revision="x",branch="HEAD",goversion="go1.24",edition="oss"} 1
grafana_stat_totals_dashboard 42
grafana_stat_totals_datasource{plugin_id="prometheus"} 3
grafana_stat_total_users 5
grafana_stat_active_users 2
grafana_stat_totals_alert_rules 7
grafana_api_response_status_total{code="200"} 100
process_resident_memory_bytes 1e8
"""


def test_grafana_user_total_is_read_under_its_real_name(tmp_path):
    kept = _keep("grafana", "self-metrics")(GRAFANA)
    assert "grafana_stat_total_users 5" in kept
    snap = _snap(tmp_path, "grafana", kept)
    (snap / "objects").mkdir(exist_ok=True)
    (snap / "grafana").mkdir(exist_ok=True)
    (snap / "grafana" / "health.json").write_text(json.dumps({"version": "12.2.1", "database": "ok"}))
    g = stackhealth._grafana(snap, {"stores": {"grafana": {"present": True}}})
    assert g["stats"]["total_users"] == 5 and g["stats"]["active_users"] == 2 and g["stats"]["totals_dashboard"] == 42
    assert g["stats"]["totals_datasource"] == 3  # labeled by plugin_id: summed, not skipped


def test_every_table_name_passes_its_step_keep_filter():
    """A name the table says kubegap reads must survive the collection filter, with and without labels, as a plain value or a histogram _sum/_count."""
    for area, entries in podmetrics.tables().items():
        steps = [s for s in yamlite.load_file(ROOT / "collectors" / area / "collect.yaml") if s.get("type") == "pod-metrics"]
        keeps = [collect._metrics_filter(s.get("keep")) for s in steps]
        for e in entries:
            labels = ",".join(f'{k}="404"' for k in (e.get("labels") or [])) or 'grpc_code="OK"'
            for n in e.get("names") or []:
                name = n["name"]
                samples = [f"{name} 1\n", f"{name}{{{labels}}} 5\n", f"{name}_sum 1\n", f"{name}_count 1\n", f'{name}{{{labels},response_code="503"}} 5\n']
                assert any(k(s) for k in keeps for s in samples), (area, name, "not kept by any pod-metrics step of the area")

"""The library code that consumes the queries #122 and #123 corrected, run on synthetic metrics files: the control-plane summary prefers the 1.34+ object-count
metric, the kube-proxy summary reads the no-local-endpoint gauge per node and policy and adds the full and partial restore failures of two queries, the EBS CSI
summary judges controller metrics from the request histogram count, the Prometheus summary judges each job against its own scrape interval and names the
sample-limit targets from targets.json, and the Loki summaries read every Loki name through the per-version table."""

from __future__ import annotations

import json
from pathlib import Path

from lib import controlplane, ebscsi, kubeproxy, logs, stackhealth


def _metric(root: Path, qid: str, rows: list[tuple[dict, float]]) -> None:
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    (root / "metrics" / f"{qid}.json").write_text(json.dumps({"id": qid, "ok": True, "result": [{"metric": m, "value": [0, str(v)]} for m, v in rows]}), encoding="utf-8")


def test_storage_objects_prefer_the_resource_objects_query_and_fall_back_before_1_34(tmp_path):
    _metric(tmp_path, "apiserver_storage_objects_top", [({"resource": "pods", "instance": "a"}, 300), ({"resource": "pods", "instance": "b"}, 300), ({"resource": "events", "instance": "a"}, 900)])
    assert controlplane._storage_objects_top(tmp_path) == [{"resource": "events", "count": 900}, {"resource": "pods", "count": 300}]
    _metric(tmp_path, "apiserver_resource_objects_top", [({"group": "", "resource": "pods"}, 310), ({"group": "events.k8s.io", "resource": "events"}, 950), ({"group": "apps", "resource": "deployments"}, 40)])
    assert controlplane._storage_objects_top(tmp_path) == [{"resource": "events.events.k8s.io", "count": 950}, {"resource": "pods", "count": 310}, {"resource": "deployments.apps", "count": 40}]


def _kubeproxy_snapshot(tmp_path: Path) -> tuple[Path, dict]:
    snap = tmp_path / "snap"
    (snap / "objects").mkdir(parents=True)
    (snap / "logs" / "node").mkdir(parents=True)
    inv = {"cluster": {"platform": "k3s"}, "nodes": {"nodes": [{"name": "n1", "internal_ip": "10.0.0.1"}, {"name": "n2", "internal_ip": "10.0.0.2"}]}}
    return snap, inv


def test_no_local_endpoint_services_adds_the_policies_of_a_node_and_keeps_the_max_over_its_scrape_ports(tmp_path):
    snap, inv = _kubeproxy_snapshot(tmp_path)
    # n1 is a k3s server scraped on :10250 and :6443 (one process, one registry); n2 only on :10250
    _metric(
        snap,
        "kubeproxy_no_local_endpoint_services",
        [
            ({"instance": "10.0.0.1:10250", "traffic_policy": "external"}, 2),
            ({"instance": "10.0.0.1:10250", "traffic_policy": "internal"}, 1),
            ({"instance": "10.0.0.1:6443", "traffic_policy": "external"}, 2),
            ({"instance": "10.0.0.1:6443", "traffic_policy": "internal"}, 1),
            ({"instance": "10.0.0.2:10250", "traffic_policy": "external"}, 0),
            ({"instance": "10.0.0.2:10250", "traffic_policy": "internal"}, 0),
        ],
    )
    # n1 had 2 full and 1 partial restore failure; n2 has no partial series yet (1.33+: a CounterVec child exists only after its first failure)
    _metric(snap, "kubeproxy_restore_failures_24h", [({"instance": "10.0.0.1:10250"}, 2), ({"instance": "10.0.0.1:6443"}, 2), ({"instance": "10.0.0.2:10250"}, 1)])
    _metric(snap, "kubeproxy_partial_restore_failures_24h", [({"instance": "10.0.0.1:10250"}, 1), ({"instance": "10.0.0.1:6443"}, 1)])
    out = kubeproxy.analyze(snap, inv)
    rows = {n["node"]: n for n in out["nodes"]}
    assert rows["n1"]["no_local_endpoint_services"] == 3 and rows["n2"]["no_local_endpoint_services"] == 0
    assert out["summary"]["no_local_endpoint_services"] == 3
    assert out["summary"]["no_local_endpoint_services_by_node"] == {"n1": 3}
    assert rows["n1"]["restore_failures_24h"] == 3 and rows["n2"]["restore_failures_24h"] == 1
    assert out["summary"]["restore_failures_24h"] == 4 and out["summary"]["restore_failure_nodes"] == ["n1", "n2"]
    assert "no_local_endpoints_1h" not in out["summary"]


def test_restore_failures_absent_until_the_first_failure_read_as_none_not_as_a_number(tmp_path):
    snap, inv = _kubeproxy_snapshot(tmp_path)
    _metric(snap, "kubeproxy_syncs_1h", [({"instance": "10.0.0.1:10250"}, 6)])
    _metric(snap, "kubeproxy_restore_failures_24h", [])
    _metric(snap, "kubeproxy_partial_restore_failures_24h", [])
    out = kubeproxy.analyze(snap, inv)
    rows = {n["node"]: n for n in out["nodes"]}
    assert rows["n1"]["metrics_available"] and rows["n1"]["restore_failures_24h"] is None
    assert out["summary"]["restore_failures_24h"] == 0 and out["summary"]["restore_failure_nodes"] == []


def test_ebs_csi_controller_metrics_are_judged_from_the_request_histogram_count(tmp_path):
    _metric(tmp_path, "ebscsi_controller_metrics_series", [])
    m = ebscsi._metrics(tmp_path)
    assert m["controller_metrics_enabled"] is False and m["controller_metrics_series"] == 0
    _metric(tmp_path, "ebscsi_controller_metrics_series", [({}, 16)])
    _metric(tmp_path, "ebscsi_api_errors_24h", [({"request": "AttachVolume"}, 2), ({"request": "DescribeVolumes"}, 0)])
    _metric(tmp_path, "ebscsi_api_throttles_24h", [({}, 5)])
    m = ebscsi._metrics(tmp_path)
    assert m["controller_metrics_enabled"] is True and m["controller_metrics_series"] == 16
    assert m["api_errors_24h"] == {"AttachVolume": 2} and m["api_throttles_24h"] == 5


def _prom_snapshot(tmp_path: Path, targets: list[dict]) -> tuple[Path, dict]:
    snap = tmp_path / "snap"
    (snap / "objects").mkdir(parents=True)
    (snap / "prometheus").mkdir()
    (snap / "prometheus" / "targets.json").write_text(json.dumps({"status": "success", "data": {"activeTargets": targets, "droppedTargets": []}}), encoding="utf-8")
    inv = {"stores": {"prometheus": {"ok": True, "version": "3.7.3"}}}
    return snap, inv


def _target(job: str, instance: str, interval: str, error: str = "") -> dict:
    return {"labels": {"job": job, "instance": instance}, "scrapeInterval": interval, "scrapeTimeout": "10s", "health": "down" if error else "up", "lastError": error}


def test_slow_scrapes_are_judged_against_each_jobs_own_interval_and_sample_limit_targets_come_from_targets_json(tmp_path):
    """The interval query returns the longest configured interval (one series per interval), so a 10s kubelet job taking 6s passed against 30s;
    the dropped-scrape counter has no target label, so `sum by (job)` named the Prometheus itself as the job over the limit."""
    snap, inv = _prom_snapshot(
        tmp_path,
        [
            _target("kubelet", "10.0.0.1:10250", "10s"),
            _target("kubelet", "10.0.0.2:10250", "10s"),
            _target("apiserver", "10.0.0.3:6443", "30s"),
            _target("app", "10.0.0.4:8080", "30s", "sample limit exceeded"),
            _target("node-exporter", "10.0.0.1:9100", "30s"),
        ],
    )
    _metric(snap, "prom_scrape_slow_jobs", [({"job": "kubelet"}, 6.0), ({"job": "apiserver"}, 6.0), ({"job": "app"}, 0.2)])
    _metric(snap, "prom_scrape_interval_s", [({}, 30.0)])
    _metric(snap, "prom_sample_limit_exceeded_1h", [({}, 3.0)])
    _metric(snap, "prom_replicas", [({}, 1.0)])
    _metric(snap, "prom_head_series", [({}, 120000.0)])
    out = stackhealth._prometheus(snap, inv)
    assert out["slow_scrape_jobs"] == [{"job": "kubelet", "seconds": 6.0, "interval": 10.0}]
    assert out["scrape_interval_s"] == 30.0  # the most common interval of the targets, not the query's max
    assert out["sample_limit_exceeded_1h"] == 3 and out["sample_limit_targets"] == [{"job": "app", "instance": "10.0.0.4:8080"}]
    assert out["replicas_up"] == 1.0


def test_without_targets_json_the_interval_query_is_the_fallback(tmp_path):
    snap = tmp_path / "snap"
    (snap / "objects").mkdir(parents=True)
    inv = {"stores": {"prometheus": {"ok": True}}}
    _metric(snap, "prom_scrape_slow_jobs", [({"job": "kubelet"}, 16.0)])
    _metric(snap, "prom_scrape_interval_s", [({}, 30.0)])
    _metric(snap, "prom_head_series", [({}, 1.0)])
    out = stackhealth._prometheus(snap, inv)
    assert out["slow_scrape_jobs"] == [{"job": "kubelet", "seconds": 16.0, "interval": 30.0}] and out["sample_limit_targets"] == []
    assert stackhealth._duration_s("1m30s") == 90.0 and stackhealth._duration_s("500ms") == 0.5 and stackhealth._duration_s("") is None and stackhealth._duration_s("x") is None


LOKI_TEXT_3 = """# HELP loki_compactor_apply_retention_last_successful_run_timestamp_seconds x
loki_compactor_apply_retention_last_successful_run_timestamp_seconds 1.7e9
loki_boltdb_shipper_compactor_running 1
loki_request_duration_seconds_count{method="POST",route="loki_api_v1_push",status_code="204",ws="false"} 100
loki_request_duration_seconds_count{method="GET",route="loki_api_v1_query",status_code="500",ws="false"} 3
loki_discarded_samples_total{reason="rate_limited",tenant="fake"} 7
loki_internal_log_messages_total{level="error"} 4
loki_log_messages_total{level="error"} 4
loki_ingester_memory_streams{tenant="fake"} 12
loki_distributor_lines_received_total{tenant="fake"} 5000
loki_distributor_bytes_received_total{tenant="fake",retention_hours="744"} 90000
loki_panic_total 0
loki_ingester_wal_disk_full_failures_total 0
process_resident_memory_bytes 2.0e8
process_start_time_seconds 1.7e9
"""


def _loki_snapshot(tmp_path: Path, text: str) -> tuple[Path, dict]:
    snap = tmp_path / "snap"
    (snap / "objects").mkdir(parents=True)
    (snap / "loki").mkdir()
    (snap / "loki" / "metrics.txt").write_text(text, encoding="utf-8")
    (snap / "loki" / "buildinfo.json").write_text(json.dumps({"version": "3.7.9"}), encoding="utf-8")
    return snap, {"stores": {"loki": {"ok": True, "version": "3.7.9", "service": {"namespace": "monitoring", "name": "loki"}}}, "components_present": ["loki"]}


def test_loki_self_metrics_are_read_under_the_name_of_each_version(tmp_path):
    """Loki 3.0 renamed the retention-run timestamp to loki_compactor_...; the old spelling read only Loki 2, so retention_applied was None on every Loki 3."""
    snap, inv = _loki_snapshot(tmp_path, LOKI_TEXT_3)
    out = stackhealth._loki(snap, inv)
    assert out["retention_applied"] is True and out["compactor_running"] == 1.0
    assert out["requests_total"] == 103 and out["requests_5xx"] == 3 and out["requests_5xx_by_route"] == {"loki_api_v1_query": 3}
    assert out["discarded_by_reason"] == {"rate_limited": 7} and out["log_error_messages"] == 4 and out["memory_streams"] == 12
    assert out["lines_received"] == 5000 and out["bytes_received"] == 90000 and out["panics"] == 0
    assert out["metrics_found"]["retention_last_run"] == "loki_compactor_apply_retention_last_successful_run_timestamp_seconds"
    assert out["metrics_found"]["log_messages"] == "loki_internal_log_messages_total"
    old = LOKI_TEXT_3.replace("loki_compactor_apply_retention", "loki_boltdb_shipper_apply_retention").replace('loki_internal_log_messages_total{level="error"} 4\n', "")
    snap, inv = _loki_snapshot(tmp_path / "old", old)
    out = stackhealth._loki(snap, inv)
    assert out["retention_applied"] is True and out["metrics_found"]["retention_last_run"] == "loki_boltdb_shipper_apply_retention_last_successful_run_timestamp_seconds"
    assert out["log_error_messages"] == 4 and out["metrics_found"]["log_messages"] == "loki_log_messages_total"
    snap, inv = _loki_snapshot(tmp_path / "none", "loki_panic_total 0\n")
    out = stackhealth._loki(snap, inv)
    assert out["retention_applied"] is None and out["memory_streams"] is None and out["metrics_found"]["retention_last_run"] is None


def test_the_logs_summary_reads_the_same_loki_table(tmp_path):
    snap, inv = _loki_snapshot(tmp_path, LOKI_TEXT_3)
    out = logs.analyze_loki(snap, inv)
    sm = out["self_metrics"]
    assert sm["discarded_samples_since_start"] == {"rate_limited": 7} and sm["streams_in_memory"] == 12 and sm["lines_received_since_start"] == 5000
    assert sm["requests_5xx_since_start"] == 3 and sm["panics"] == 0 and sm["rss_mb"] == 191

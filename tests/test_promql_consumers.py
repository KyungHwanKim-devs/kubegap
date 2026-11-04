"""The library code that consumes the queries #122 corrected, run on synthetic metrics files: the control-plane summary prefers the 1.34+ object-count
metric, the kube-proxy summary reads the no-local-endpoint gauge per node and policy and adds the full and partial restore failures of two queries, and the EBS CSI
summary judges controller metrics from the request histogram count."""

from __future__ import annotations

import json
from pathlib import Path

from lib import controlplane, ebscsi, kubeproxy


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

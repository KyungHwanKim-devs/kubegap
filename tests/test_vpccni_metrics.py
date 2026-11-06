"""The ipamd /metrics text a node step saves (logs/node/<node>/awscni.prom) is read through collectors/vpc-cni/pod-metrics.yaml (#127)."""

from __future__ import annotations

import json

from lib import vpccni

PROM = """awscni_add_ip_req_count 558
awscni_assigned_ip_addresses 35
awscni_assigned_ip_per_eni{eni="eni-0a"} 3
awscni_assigned_ip_per_eni{eni="eni-0b"} 8
awscni_aws_api_latency_ms_count{api="DescribeNetworkInterfaces",error="false",status="200"} 12
awscni_aws_api_latency_ms_count{api="AssignPrivateIpAddresses",error="true",status="400"} 2
awscni_aws_api_latency_ms_count{api="GetMetadata",error="true",status="404"} 9
awscni_aws_api_latency_ms_sum{api="DescribeNetworkInterfaces",error="false",status="200"} 300
awscni_eni_allocated 2
awscni_eni_max 3
awscni_force_removed_enis 0
awscni_force_removed_ips 1
awscni_ip_max 42
awscni_no_available_ip_addresses 4
awscni_total_ip_addresses 44
awscni_total_ipv4_prefixes 0
"""


def _snapshot(tmp_path, prom: str | None):
    (tmp_path / "objects").mkdir()
    ds = {"metadata": {"name": "aws-node", "namespace": "kube-system"}, "spec": {"template": {"spec": {"containers": [{"name": "aws-node", "image": "x/amazon-k8s-cni:v1.19.0", "env": []}]}}}, "status": {}}
    (tmp_path / "objects" / "daemonsets.json").write_text(json.dumps({"items": [ds]}), encoding="utf-8")
    if prom is not None:
        d = tmp_path / "logs" / "node" / "n1"
        d.mkdir(parents=True)
        (d / "awscni.prom").write_text(prom, encoding="utf-8")
    return {"nodes": {"nodes": [{"name": "n1", "instance_type": "m6i.large", "allocatable": {"pods": "29"}}]}}


def test_ipamd_metrics_are_read_by_table_key(tmp_path):
    inv = _snapshot(tmp_path, PROM)
    node = vpccni.analyze(tmp_path, inv)["nodes"][0]
    met = node["metrics"]
    assert met["available"]
    assert (met["assigned"], met["total"], met["eni_allocated"], met["eni_max"], met["ip_max"]) == (35, 44, 2, 3, 42)
    assert (met["prefixes"], met["no_available_ip_events"], met["force_removed_enis"], met["force_removed_ips"]) == (0, 4, 0, 1)
    assert met["per_eni"] == {"eni-0a": 3, "eni-0b": 8}
    assert met["ec2_api_errors"] == 2 and met["ec2_api_errors_by_api"] == {"AssignPrivateIpAddresses": 2}, "the IMDS 404 of GetMetadata is not an EC2 API error"


def test_empty_prom_file_is_a_gap(tmp_path):
    inv = _snapshot(tmp_path, "")
    out = vpccni.analyze(tmp_path, inv)
    assert out["nodes"][0]["metrics"] == {"available": False}

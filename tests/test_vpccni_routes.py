"""Private routes of the cluster VPC (peering, transit gateway, VPN) read from aws/describe-route-tables.json; absent file means not collected."""

from __future__ import annotations

import json

import pytest

from lib import vpccni


def _write(tmp_path, routes):
    (tmp_path / "aws").mkdir(exist_ok=True)
    (tmp_path / "aws" / "describe-route-tables.json").write_text(json.dumps({"RouteTables": [{"RouteTableId": "rtb-1", "Routes": routes}]}), encoding="utf-8")


def test_not_collected_without_file(tmp_path):
    r = vpccni._private_routes(tmp_path)
    assert r == {"collected": False, "peering": 0, "transit_gateway": 0, "vpn": 0, "local_gateway": 0, "appliance": 0, "destinations": [], "excluded": [], "scoped_to_node_subnets": False}


def test_counts_each_private_target_and_ignores_local_igw_nat(tmp_path):
    _write(
        tmp_path,
        [
            {"DestinationCidrBlock": "10.0.0.0/16", "GatewayId": "local"},
            {"DestinationCidrBlock": "0.0.0.0/0", "NatGatewayId": "nat-1"},
            {"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-1"},
            {"DestinationCidrBlock": "10.20.0.0/16", "VpcPeeringConnectionId": "pcx-1"},
            {"DestinationCidrBlock": "10.30.0.0/16", "TransitGatewayId": "tgw-1"},
            {"DestinationCidrBlock": "192.168.0.0/16", "GatewayId": "vgw-1"},
            {"DestinationPrefixListId": "pl-1", "VpcPeeringConnectionId": "pcx-2"},
        ],
    )
    r = vpccni._private_routes(tmp_path)
    assert r["collected"] and (r["peering"], r["transit_gateway"], r["vpn"]) == (2, 1, 1)
    assert r["destinations"] == ["10.20.0.0/16", "10.30.0.0/16", "192.168.0.0/16", "pl-1"]


def test_only_local_and_nat_routes(tmp_path):
    _write(tmp_path, [{"DestinationCidrBlock": "10.0.0.0/16", "GatewayId": "local"}, {"DestinationCidrBlock": "0.0.0.0/0", "NatGatewayId": "nat-1"}])
    r = vpccni._private_routes(tmp_path)
    assert r["collected"] and r["peering"] == r["transit_gateway"] == r["vpn"] == 0 and r["destinations"] == []


def test_blackhole_routes_are_ignored_and_cloud_wan_outposts_counted(tmp_path):
    _write(
        tmp_path,
        [
            {"DestinationCidrBlock": "10.20.0.0/16", "VpcPeeringConnectionId": "pcx-gone", "State": "blackhole"},
            {"DestinationCidrBlock": "10.40.0.0/16", "CoreNetworkArn": "arn:aws:networkmanager::1:core-network/x", "State": "active"},
            {"DestinationCidrBlock": "10.50.0.0/16", "LocalGatewayId": "lgw-1", "State": "active"},
        ],
    )
    r = vpccni._private_routes(tmp_path)
    assert (r["peering"], r["transit_gateway"], r["vpn"], r["local_gateway"]) == (0, 1, 0, 1)
    assert r["destinations"] == ["10.40.0.0/16", "10.50.0.0/16"]


def test_empty_route_table_list_means_not_collected(tmp_path):
    """`Values=None` in the VPC filter makes AWS return an empty list with exit 0; every real VPC has a main route table, so empty means the filter was wrong."""
    (tmp_path / "aws").mkdir()
    (tmp_path / "aws" / "describe-route-tables.json").write_text(json.dumps({"RouteTables": []}), encoding="utf-8")
    assert vpccni._private_routes(tmp_path)["collected"] is False


def _aws_node(tmp_path, external_snat):
    (tmp_path / "objects").mkdir(exist_ok=True)
    ds = {
        "metadata": {"name": "aws-node", "namespace": "kube-system"},
        "spec": {"template": {"spec": {"containers": [{"name": "aws-node", "image": "x/amazon-k8s-cni:v1.19.0", "env": [{"name": "AWS_VPC_K8S_CNI_EXTERNALSNAT", "value": external_snat}]}]}}},
        "status": {},
    }
    (tmp_path / "objects" / "daemonsets.json").write_text(json.dumps({"items": [ds]}), encoding="utf-8")


def test_summary_snat_only_when_routes_collected(tmp_path):
    _aws_node(tmp_path, "false")
    inv = {"nodes": {"nodes": []}}
    assert vpccni.analyze(tmp_path, inv)["snat"] is None
    _write(tmp_path, [{"DestinationCidrBlock": "10.20.0.0/16", "VpcPeeringConnectionId": "pcx-1", "State": "active"}])
    snat = vpccni.analyze(tmp_path, inv)["snat"]
    assert snat["external_snat"] is False and snat["peering_routes"] == 1 and snat["private_destinations"] == ["10.20.0.0/16"]


@pytest.mark.parametrize(
    "version,randomize,external,expected",
    [
        ("1.19.0-eksbuild.1", "prng", False, "random-fully"),
        ("1.19.0", None, False, "random-fully"),
        ("1.19.0", "PRNG", False, "random-fully"),  # not a recognised value: the CNI falls back to the version default, prng on 1.19
        ("1.6.3", "PRNG", False, "random"),  # same fallback on an old CNI: hashrandom
        ("1.19.0", "NONE", False, "random-fully"),
        ("1.7.0", None, False, "random-fully"),
        ("1.6.3", None, False, "random"),
        ("1.6.3", "hashrandom", False, "random"),
        ("1.6.3", "prng", False, "random-fully"),
        ("1.19.0", "hashrandom", False, "random"),
        ("1.19.0", "none", False, "sequential"),
        ("1.3.0", None, False, "sequential"),
        ("1.4.0", None, False, "random"),
        ("1.3.0", "prng", False, "sequential"),
        ("1.19.0", "prng", True, "not-applicable"),
        (None, "prng", False, "unknown"),
        (None, None, False, "unknown"),
        ("latest", "prng", False, "unknown"),
        (None, "none", False, "sequential"),
    ],
)
def test_snat_port_mode(version, randomize, external, expected):
    assert vpccni.snat_port_mode(version, randomize, external) == expected

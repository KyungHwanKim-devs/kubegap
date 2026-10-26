"""lib/discover.py platform detector. The function is pure: it reads the kubeconfig flags, node provider IDs and kubelet versions, detected components and a few objects."""

import pytest

from lib import discover

detect = discover.detect_platform


def nodes(provider_ids, kubelet_versions):
    return {"count": len(provider_ids), "nodes": [{"name": f"n{i}", "provider_id": p} for i, p in enumerate(provider_ids)], "kubelet_versions": kubelet_versions}


def comps(*present):
    return {name: {"present": True} for name in present}


def test_eks_by_kubeconfig_flag():
    platform, reasons = detect({"is_eks": True}, nodes([""], ["v1.31.0"]), {}, {})
    assert platform == "eks"
    assert any("EKS" in r for r in reasons)


def test_eks_by_aws_provider_and_eks_kubelet_version_suffix():
    platform, reasons = detect({}, nodes(["aws://us-east-1a/i-1", "aws://us-east-1a/i-2"], ["v1.31.4-eks-abc123"]), {}, {})
    assert platform == "eks"
    assert "node providerID is aws://" in reasons


def test_aws_provider_without_eks_kubelet_is_not_eks():
    platform, _ = detect({}, nodes(["aws://x/i-1"], ["v1.31.0"]), {}, {})
    assert platform == "unknown"


def test_k3s_by_component():
    platform, reasons = detect({}, nodes(["k3s://node1"], ["v1.30.2+k3s1"]), comps("k3s"), {})
    assert platform == "k3s"
    assert "+k3s in node kubelet version" in reasons


def test_k3s_by_two_weaker_signals():
    objs = {"storageclasses": {"items": [{"metadata": {"name": "local-path"}}]}}
    platform, reasons = detect({}, nodes([""], ["v1.30.0"]), comps("local-path-provisioner"), objs)
    assert platform == "k3s"
    assert len(reasons) == 2


def test_rke2_by_component():
    platform, reasons = detect({}, nodes([""], ["v1.30.0+rke2r1"]), comps("rke2"), {})
    assert platform == "rke2"
    assert reasons == ["+rke2 in node kubelet version"]


def test_gke_by_gce_provider():
    platform, reasons = detect({}, nodes(["gce://proj/zone/vm"], ["v1.30.5-gke.1"]), {}, {})
    assert platform == "gke"
    assert reasons == ["node providerID is gce://"]


def test_aks_by_azure_provider():
    platform, reasons = detect({}, nodes(["azure:///subscriptions/x/vm"], ["v1.30.0"]), {}, {})
    assert platform == "aks"
    assert reasons == ["node providerID is azure://"]


@pytest.mark.parametrize("provider", ["", "kubeadm://x", "vsphere://y"])
def test_unknown(provider):
    platform, reasons = detect({}, nodes([provider], ["v1.30.0"]), {}, {})
    assert platform == "unknown"
    assert reasons and "no evidence" in reasons[0]

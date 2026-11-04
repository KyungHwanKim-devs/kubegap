"""Component detection against the names the official charts and manifests produce (#130). Every expectation here is a name read in the
project's source and cited on the rule's entry in lib/components.py; the point of the tests is the release-name shapes the rules missed
until #130: a Helm chart names its workload <release> or <release>-<chart>, so the chart name is a suffix."""

from __future__ import annotations

import pytest

from lib import discover
from lib.components import COMPONENTS, EVIDENCE_KEYS


def _objs(**kinds) -> dict:
    """kinds: daemonsets=[("ns", "name", "image"), ...], crds=["name"], nodes=[("version", {annotations})], storageclasses=["prov"], configmaps=[("ns","name",{data})]"""
    out: dict = {}
    for kind in ("daemonsets", "deployments", "statefulsets", "cronjobs"):
        items = []
        for ns, name, image in kinds.get(kind, []):
            pod = {"spec": {"containers": [{"name": "c", "image": image}]}}
            spec = {"jobTemplate": {"spec": {"template": pod}}} if kind == "cronjobs" else {"template": pod}
            items.append({"metadata": {"namespace": ns, "name": name}, "spec": spec})
        out[kind] = {"items": items}
    out["customresourcedefinitions"] = {"items": [{"metadata": {"name": n}, "spec": {"group": n.split(".", 1)[1]}} for n in kinds.get("crds", [])]}
    out["nodes"] = {"items": [{"metadata": {"name": f"n{i}", "annotations": ann}, "status": {"nodeInfo": {"kubeletVersion": v}}} for i, (v, ann) in enumerate(kinds.get("nodes", []))]}
    out["storageclasses"] = {"items": [{"metadata": {"name": f"sc{i}"}, "provisioner": p} for i, p in enumerate(kinds.get("storageclasses", []))]}
    out["configmaps"] = {"items": [{"metadata": {"namespace": ns, "name": n}, "data": d} for ns, n, d in kinds.get("configmaps", [])]}
    out["namespaces"] = {"items": []}
    return out


def _present(objs, aws_addons=None) -> dict[str, str]:
    return {k: v["evidence"] for k, v in discover.detect_components(objs, aws_addons).items() if v["present"]}


def test_nothing_installed_detects_nothing():
    assert _present(_objs()) == {}


@pytest.mark.parametrize(
    "kind,ns,name,image,component",
    [
        # <release>-<chart> and <release> names the fullname helpers produce (lib/components.py cites each chart's _helpers.tpl)
        ("deployments", "monitoring", "monitoring-prometheus-server", "quay.io/other/x", "prometheus"),
        ("statefulsets", "monitoring", "prometheus-alertmanager", "x", {"alertmanager", "prometheus"}),  # the charts/prometheus subchart; the prometheus-* prefix takes it too, as its source says
        ("statefulsets", "mon", "am", "x", None),
        ("daemonsets", "lb", "lb-metallb-speaker", "x", "metallb"),
        ("daemonsets", "metallb-system", "speaker", "x", "metallb"),
        ("deployments", "nth", "nth-aws-node-termination-handler", "x", "node-termination-handler"),
        ("daemonsets", "kube-system", "aws-node-termination-handler", "x", "node-termination-handler"),
        ("deployments", "ca", "ca-aws-cluster-autoscaler", "x", "cluster-autoscaler"),
        ("deployments", "kube-system", "aws-cluster-autoscaler", "x", "cluster-autoscaler"),
        ("deployments", "dns", "route53-external-dns", "x", "external-dns"),
        ("deployments", "x", "my-release-nfs-subdir-external-provisioner", "x", "nfs-provisioner"),
        ("deployments", "default", "nfs-client-provisioner", "x", "nfs-provisioner"),
        ("daemonsets", "kube-system", "csi-secrets-store-secrets-store-csi-driver", "x", "secrets-store-csi"),
        ("daemonsets", "kube-system", "csi-secrets-store", "x", "secrets-store-csi"),
        ("deployments", "stakater", "stakater-reloader", "x", "reloader"),
        ("daemonsets", "reboot", "reboot-kured", "x", "kured"),
        ("deployments", "argo", "argo-cd-argocd-server", "x", "argocd"),
        ("deployments", "k", "my-karpenter", "x", "karpenter"),
        ("deployments", "kube-system", "rke2-metrics-server", "x", "metrics-server"),
        ("deployments", "ms", "metrics-server", "x", "metrics-server"),
        ("deployments", "local-path-storage", "local-path-provisioner", "x", "local-path-provisioner"),
        ("deployments", "istio-system", "istiod-canary", "x", "istio"),
        ("deployments", "rke2", "rke2-traefik", "x", "traefik"),
        ("statefulsets", "es", "quickstart-es-default", "docker.elastic.co/elasticsearch/elasticsearch:9.1.0", "elasticsearch-opensearch"),  # ECK: by image; a name glob on -es- would take sales-es-worker too
        ("statefulsets", "sales", "sales-es-worker", "ghcr.io/acme/worker:1", None),
        ("deployments", "vm", "vmsingle-demo", "x", "victoria-metrics"),
        ("statefulsets", "vm", "vm-victoria-metrics-single-server", "x", "victoria-metrics"),
        ("statefulsets", "mon", "vmsingle-demo", "x", None),  # the StatefulSet the old rule looked for: nothing produces it
        ("daemonsets", "otel", "my-opentelemetry-collector-agent", "x", "opentelemetry-collector"),
        ("daemonsets", "aws", "cloudwatch-agent", "x", "cloudwatch-agent"),
        ("daemonsets", "amazon-cloudwatch", "fluent-bit", "x", "fluent-bit"),  # not cloudwatch-agent any more
        ("cronjobs", "kube-system", "descheduler-cronjob", "x", "descheduler"),
        ("cronjobs", "kube-system", "descheduler", "x", "descheduler"),
        ("deployments", "logging", "logging-loki", "x", "loki"),
        ("statefulsets", "kube-system", "kube-prometheus-stack-kube-state-metrics", "x", "kube-state-metrics"),
        # images, release-name independent
        ("statefulsets", "v", "hashicorp-vault", "hashicorp/vault:1.17", "vault"),
        ("statefulsets", "v", "vault-prod", "docker.io/hashicorp/vault:1.17", "vault"),
        ("deployments", "x", "thanos-query", "docker.io/thanosio/thanos:v0.42.5", "thanos"),
        ("deployments", "x", "thanos-query", "docker.io/bitnami/thanos:0.42", "thanos"),
        ("statefulsets", "x", "aggregator", "docker.io/timberio/vector:0.50", "vector"),
        ("deployments", "x", "cost-model", "icr.io/kubecost/cost-model:3.3.1", "kubecost-opencost"),
        ("deployments", "x", "simplest", "jaegertracing/jaeger:2.0", "tempo-jaeger"),
        ("statefulsets", "x", "cluster-master", "opensearchproject/opensearch:3", "elasticsearch-opensearch"),
        ("deployments", "x", "custom", "ghcr.io/stakater/reloader:v1.4.23", "reloader"),
        ("daemonsets", "x", "efs", "public.ecr.aws/efs-csi-driver/amazon/aws-efs-csi-driver:v2", "efs-csi"),
        ("daemonsets", "x", "lp", "docker.io/rancher/local-path-provisioner:v0.0.37", "local-path-provisioner"),
        ("daemonsets", "x", "lp", "public.ecr.aws/something/else:1", None),  # ECR Public is not the cluster's registry
        ("deployments", "x", "app", "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:1", "ecr"),
    ],
)
def test_official_names_are_detected(kind, ns, name, image, component):
    present = _present(_objs(**{kind: [(ns, name, image)]}))
    if component is None:
        assert present == {}, present
    else:
        want = component if isinstance(component, set) else {component}
        assert set(present) == want, present
        assert all(present[c].startswith((kind[:-1] + " ", "image ")) for c in want)


def test_kube_proxy_is_present_on_rke2_and_k3s_without_a_daemonset():
    """RKE2 runs kube-proxy as a static pod and k3s inside its process; until #130 the RKE2 rule looked for a DaemonSet rke2-kube-proxy* that no release produced."""
    for ver, marker in (("v1.37.1+rke2r1", "+rke2"), ("v1.37.1+k3s1", "+k3s")):
        present = _present(_objs(nodes=[(ver, {})]))
        assert present["kube-proxy"] == f"node version contains {marker}", present
    assert "kube-proxy" not in _present(_objs(nodes=[("v1.37.1-eks-abc", {})]))


def test_fluent_bit_events_input_in_both_config_formats():
    classic = "[INPUT]\n    name kubernetes_events\n    tag k8s_events\n"
    yaml = "pipeline:\n  inputs:\n    - name: kubernetes_events\n      tag: k8s\n"
    for data in (classic, yaml):
        assert "fluent-bit-events" in _present(_objs(configmaps=[("logging", "fluent-bit", {"fluent-bit.conf": data})]))
    assert "fluent-bit-events" not in _present(_objs(configmaps=[("logging", "fluent-bit", {"fluent-bit.conf": "[INPUT]\n    Name tail\n"})]))


def test_every_rule_entry_names_a_known_evidence_kind_and_a_source():
    """An unknown key never matches (cronjob_ignored sat on the descheduler rule until #130); every entry cites where its name comes from."""
    seen = 0
    for comp in COMPONENTS:
        for e in comp["any"]:
            keys = [k for k in e if k != "source"]
            assert len(keys) == 1 and keys[0] in EVIDENCE_KEYS, (comp["name"], e)
            assert isinstance(e.get("source"), str) and e["source"], (comp["name"], keys[0])
            seen += 1
    assert seen >= 140

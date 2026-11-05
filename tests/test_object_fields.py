"""What reading the Kubernetes API types and the operator CRD types changed (#124): the object files the readers open, the Event count, the condition
reasons and API-version-dependent paths. Every case names the report defect it pins (K1-1 ... O-6 in references/sources.md)."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from lib import argocdctl, certmanager, diff, discover, ebscsi, esoctl, events, hygiene, karpenterctl, localpath, resilience, scaling, snapshot, summarize, tenancy, traffic, vpccni
from lib.k3s import _node_base

ROOT = Path(__file__).resolve().parent.parent
NOW = dt.datetime(2026, 11, 5, 3, 0, tzinfo=dt.UTC)
INV = {"taken_at": NOW.isoformat(), "namespaces": {"prod_like": ["prod"]}}


def _write(snap: Path, stem: str, items: list, folder: str = "objects"):
    p = snap / folder / f"{stem}.json" if folder else snap / f"{stem}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"items": items}), encoding="utf-8")


# ---------- K1-1: the CronJob file is `cronjobs.json` since discovery fetches CronJobs (lib/discover.py OBJECT_KINDS), `cronjobs.batch.json` before ----------


def test_every_literal_stem_matches_what_discovery_writes():
    """A reader names a kind discovery fetches by its short name (that is the file discovery writes and the dump-all step then skips)."""
    short = set(discover.OBJECT_KINDS)
    bad = []
    for f in sorted((ROOT / "lib").glob("*.py")):
        for m in re.finditer(r'objects\((?:[\w.]+, *)?"([\w.-]+)"\)', f.read_text(encoding="utf-8")):
            stem = m.group(1)
            if "." in stem and stem.split(".", 1)[0] in short:
                bad.append(f"{f.name}: {stem}")
    assert not bad, f"discovery writes these kinds under the short name, the reader must use it: {bad}"


def test_discovery_stems_are_the_table_discovery_fetches():
    assert frozenset(discover.OBJECT_KINDS) == snapshot.DISCOVERY_STEMS


def test_objects_never_falls_back_for_a_kind_discovery_does_not_fetch(tmp_path):
    _write(tmp_path, "pods", [{"metadata": {"name": "p"}}])
    _write(tmp_path, "jobs.batch", [{"metadata": {"name": "j"}}])
    assert snapshot.objects(tmp_path, "pods.metrics.k8s.io") == []  # never pods.json
    assert snapshot.objects(tmp_path, "jobs") == []  # jobs is not a discovery kind


def test_objects_reads_the_old_and_the_new_cronjob_file(tmp_path):
    cj = [{"metadata": {"namespace": "p", "name": "backup"}, "spec": {"schedule": "0 3 * * *"}}]
    _write(tmp_path, "cronjobs.batch", cj)
    assert snapshot.objects(tmp_path, "cronjobs") == cj  # a snapshot from before 2026-11-05
    assert snapshot.objects(tmp_path, "cronjobs.batch") == cj
    new = tmp_path / "new"
    _write(new, "cronjobs", cj)
    assert snapshot.objects(new, "cronjobs") == cj
    assert snapshot.objects(new, "cronjobs.batch") == cj  # the reverse, for a caller that still spells the group
    assert snapshot.objects(new, "jobs.batch") == []


def test_cronjob_checks_see_the_cronjobs_discovery_wrote(tmp_path):
    _write(tmp_path, "cronjobs", [{"metadata": {"namespace": "p", "name": "pg-backup"}, "spec": {"schedule": "0 3 * * *", "jobTemplate": {"spec": {"template": {"spec": {"containers": [{"name": "c", "image": "pg"}]}}}}}, "status": {}}])
    for stem in ("deployments", "statefulsets", "daemonsets", "pods", "nodes", "poddisruptionbudgets.policy", "jobs.batch"):
        _write(tmp_path, stem, [])
    cx = resilience._Ctx(tmp_path, INV)
    assert resilience._cronjobs(cx, NOW)["count"] == 1


# ---------- K1-2, K3-6: the Event count of an events.k8s.io recorder lives in series.count ----------


def test_event_count_reads_series_count():
    assert events.count_of({"count": 7}) == 7
    assert events.count_of({"series": {"count": 12, "lastObservedTime": "2026-11-05T02:00:00Z"}}) == 12
    assert events.count_of({"reason": "Scheduled"}) == 1


def test_no_reader_counts_events_without_the_helper():
    """resilience, storage, ebscsi, traffic and scaling summed `count` only (K1-2, K3-6); they go through events.count_of now."""
    for f in (ROOT / "lib").glob("*.py"):
        assert 'e.get("count") or 1' not in f.read_text(encoding="utf-8"), f.name


# ---------- K1-3, K1-4, K1-5, K1-6: resilience ----------


def test_statefulset_max_unavailable_is_read_from_update_strategy(tmp_path):
    _write(
        tmp_path,
        "statefulsets",
        [
            {
                "metadata": {"namespace": "p", "name": "db"},
                "spec": {
                    "replicas": 3,
                    "updateStrategy": {"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 2}},
                    "template": {"metadata": {"labels": {"app": "db"}}, "spec": {"containers": [{"name": "c", "ports": [{"containerPort": 5432}]}]}},
                },
            }
        ],
    )
    _write(tmp_path, "services", [{"metadata": {"namespace": "p", "name": "db"}, "spec": {"selector": {"app": "db"}, "ports": [{"port": 5432}]}}])
    for stem in ("deployments", "daemonsets", "pods", "nodes", "cronjobs", "poddisruptionbudgets.policy", "namespaces", "persistentvolumeclaims"):
        _write(tmp_path, stem, [])
    rows = resilience._graceful(resilience._Ctx(tmp_path, INV))["rows"]
    assert rows[0]["strategy"] == "RollingUpdate" and rows[0]["max_unavailable"] == 2


def test_pdb_row_carries_the_disruption_allowed_reason(tmp_path):
    _write(
        tmp_path,
        "poddisruptionbudgets.policy",
        [
            {
                "metadata": {"namespace": "p", "name": "api"},
                "spec": {"minAvailable": 1, "selector": {"matchLabels": {"app": "api"}}},
                "status": {"disruptionsAllowed": 0, "expectedPods": 2, "currentHealthy": 2, "desiredHealthy": 2, "conditions": [{"type": "DisruptionAllowed", "status": "False", "reason": "SyncFailed"}]},
            }
        ],
    )
    for stem in ("deployments", "statefulsets", "daemonsets", "pods", "nodes", "cronjobs"):
        _write(tmp_path, stem, [])
    row = resilience._pdbs(resilience._Ctx(tmp_path, INV))["rows"][0]
    assert row["blocks_drain"] is True and row["disruption_allowed_reason"] == "SyncFailed"


def test_match_fields_compare_the_node_name_not_a_label():
    node = {"metadata": {"name": "worker-1", "labels": {"metadata.name": "other"}}, "spec": {}}
    assert resilience._field_match({"key": "metadata.name", "operator": "In", "values": ["worker-1"]}, node)
    assert not resilience._field_match({"key": "metadata.name", "operator": "In", "values": ["worker-2"]}, node)
    pod = {"affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchFields": [{"key": "metadata.name", "operator": "In", "values": ["worker-1"]}]}]}}}}
    assert resilience.eligible_nodes(pod, [node]) == ["worker-1"]


def test_pv_node_pin_accepts_a_custom_affinity_key():
    def pv(key, values):
        return {"spec": {"nodeAffinity": {"required": {"nodeSelectorTerms": [{"matchExpressions": [{"key": key, "operator": "In", "values": values}]}]}}}}

    assert resilience._pv_node(pv("kubernetes.io/hostname", ["kkh"])) == "kkh"
    assert resilience._pv_node(pv("topology.example.com/node", ["kkh2"])) == "kkh2"  # local-path-provisioner's nodeAffinityKey parameter
    assert resilience._pv_node(pv("topology.kubernetes.io/zone", ["a", "b"])) is None


# ---------- K2-1, K2-2, K2-4, K2-5, K2-6 ----------


def test_statefulset_change_time_comes_from_its_newest_controller_revision(tmp_path):
    recent = (NOW - dt.timedelta(hours=2)).isoformat(timespec="seconds")
    old = (NOW - dt.timedelta(days=9)).isoformat(timespec="seconds")
    _write(tmp_path, "deployments", [])
    _write(tmp_path, "daemonsets", [])
    _write(tmp_path, "statefulsets", [{"metadata": {"namespace": "p", "name": "db", "generation": 4}, "status": {"observedGeneration": 4}}])
    _write(
        tmp_path,
        "controllerrevisions.apps",
        [
            {"metadata": {"namespace": "p", "name": "db-1", "creationTimestamp": old, "ownerReferences": [{"kind": "StatefulSet", "name": "db"}]}},
            {"metadata": {"namespace": "p", "name": "db-2", "creationTimestamp": recent, "ownerReferences": [{"kind": "StatefulSet", "name": "db"}]}},
        ],
    )
    _write(tmp_path, "events", [], folder="")
    out = summarize.summarize_recent_changes(tmp_path, now=NOW)
    assert [(w["kind"], w["name"], w["last_update"]) for w in out["workloads"]] == [("StatefulSet", "db", recent)]


def test_pvc_unused_counts_from_the_start_ordinal(tmp_path):
    _write(
        tmp_path,
        "statefulsets",
        [{"metadata": {"namespace": "p", "name": "db"}, "spec": {"replicas": 2, "ordinals": {"start": 5}, "volumeClaimTemplates": [{"metadata": {"name": "data"}}], "template": {"spec": {"containers": [{"name": "c"}]}}}}],
    )
    _write(tmp_path, "persistentvolumeclaims", [{"metadata": {"namespace": "p", "name": f"data-db-{i}"}} for i in (5, 6)])
    for stem in ("deployments", "daemonsets", "cronjobs", "pods", "configmaps", "serviceaccounts", "services", "jobs.batch"):
        _write(tmp_path, stem, [])
    assert hygiene._orphans(hygiene._Ctx(tmp_path, INV))["pvc_unused"] == []


def test_templating_recognises_the_default_argocd_label_and_the_eks_component_label(tmp_path):
    _write(tmp_path, "applications.argoproj.io", [{"metadata": {"namespace": "argocd", "name": "shop"}, "status": {"resources": [{"kind": "Deployment", "namespace": "prod", "name": "shop-api"}]}}])
    _write(
        tmp_path,
        "deployments",
        [
            {"metadata": {"namespace": "prod", "name": "shop-api", "labels": {"app.kubernetes.io/instance": "shop"}, "annotations": {}}, "spec": {"template": {"spec": {"containers": []}}}},
            {"metadata": {"namespace": "ops", "name": "ebs-csi-controller", "labels": {"eks.amazonaws.com/component": "ebs-csi-controller"}, "annotations": {}}, "spec": {"template": {"spec": {"containers": []}}}},
            {"metadata": {"namespace": "prod", "name": "loose", "labels": {"app.kubernetes.io/instance": "shop"}, "annotations": {}}, "spec": {"template": {"spec": {"containers": []}}}},
        ],
    )
    for stem in ("statefulsets", "daemonsets", "cronjobs", "pods"):
        _write(tmp_path, stem, [])
    out = hygiene._templating(hygiene._Ctx(tmp_path, INV))
    assert out["by_manager"] == {"argocd": 1, "platform": 1, "none": 1}
    assert [r["workload"] for r in out["unmanaged"]] == ["prod/deployment/loose"]


def test_diff_hashes_every_configuration_key_of_the_spec_less_kinds():
    for k in ("volumeBindingMode", "mountOptions", "allowedTopologies", "imagePullSecrets", "description", "preemptionPolicy"):
        assert k in diff.BODY_KEYS


# ---------- K3-1 ... K3-7 ----------


def test_local_path_class_reports_the_parameters_the_provisioner_reads(tmp_path):
    _write(tmp_path, "storageclasses", [{"metadata": {"name": "local-path-kkh2"}, "provisioner": "rancher.io/local-path", "parameters": {"path": "/ignored", "nodePath": "/data", "pathPattern": "{{ .PVC.Namespace }}/{{ .PVC.Name }}"}}])
    for stem in ("persistentvolumes", "persistentvolumeclaims", "pods", "deployments", "configmaps"):
        _write(tmp_path, stem, [])
    sc = localpath.analyze(tmp_path, INV, None)["storage_classes"][0]
    assert sc["node_path"] == "/data" and sc["path_pattern"] == "{{ .PVC.Namespace }}/{{ .PVC.Name }}" and "path" not in sc


def test_ebs_parameters_are_matched_case_insensitively_and_expanding_is_a_failure_only_as_warning(tmp_path):
    _write(tmp_path, "storageclasses", [{"metadata": {"name": "gp3-enc"}, "provisioner": "ebs.csi.aws.com", "parameters": {"Type": "gp3", "Encrypted": "true", "KmsKeyId": "arn:aws:kms:k"}}])
    _write(tmp_path, "csidrivers.storage.k8s.io", [{"metadata": {"name": "ebs.csi.aws.com"}, "spec": {"attachRequired": True}}])
    _write(
        tmp_path,
        "events",
        [{"reason": "ExternalExpanding", "type": "Normal", "count": 3}, {"reason": "ExternalExpanding", "type": "Warning", "count": 2}, {"reason": "FailedAttachVolume", "type": "Warning", "series": {"count": 4}}],
        folder="",
    )
    for stem in (
        "deployments",
        "daemonsets",
        "csinodes.storage.k8s.io",
        "volumeattachments.storage.k8s.io",
        "persistentvolumes",
        "persistentvolumeclaims",
        "pods",
        "serviceaccounts",
        "volumesnapshots.snapshot.storage.k8s.io",
        "volumesnapshotclasses.snapshot.storage.k8s.io",
    ):
        _write(tmp_path, stem, [])
    out = ebscsi.analyze(tmp_path, INV)
    sc = next(c for c in out["storage_classes"] if c["name"] == "gp3-enc")
    assert sc["type"] == "gp3" and sc["encrypted"] is True and sc["kms_key"] == "arn:aws:kms:k"
    assert out["events_24h"] == {"ExternalExpanding": 2, "FailedAttachVolume": 4} and out["summary"]["classes_unencrypted"] == []


def test_ingress_nginx_allowlist_counts_as_an_auth_hint():
    assert "nginx.ingress.kubernetes.io/allowlist-source-range" in traffic.AUTH_ANN


def test_target_group_binding_by_name_is_matched_to_the_target_group(tmp_path):
    _write(tmp_path, "targetgroupbindings.elbv2.k8s.aws", [{"metadata": {"namespace": "prod", "name": "api"}, "spec": {"targetGroupName": "k8s-prod-api-1234", "serviceRef": {"name": "api", "port": 80}, "targetType": "ip"}}])
    (tmp_path / "aws").mkdir()
    (tmp_path / "aws" / "alb-metrics.json").write_text(
        json.dumps(
            {
                "target_groups": [{"arn": "arn:aws:elasticloadbalancing:r:1:targetgroup/k8s-prod-api-1234/9", "dim": "targetgroup/k8s-prod-api-1234/9", "name": "k8s-prod-api-1234"}],
                "metrics": {"tg": {"targetgroup/k8s-prod-api-1234/9": {"RequestCount_Sum": {"points": [1]}}}},
            }
        )
    )
    assert traffic.alb_covered_services(tmp_path) == {("prod", "api")}


def test_k3s_node_args_are_passed_through_as_k3s_masked_them():
    o = {"metadata": {"name": "kkh", "annotations": {"k3s.io/node-args": json.dumps(["agent", "--server", "https://10.0.0.2:6443", "--token", "********"])}}, "status": {"addresses": []}}
    rec = _node_base({"name": "kkh"}, o, set())
    assert rec["args"] == ["agent", "--server", "https://10.0.0.2:6443", "--token", "********"]


# ---------- N-1 ... N-15 ----------


def _argo_snapshot(tmp_path, version: str, cm: dict, apps: list):
    _write(
        tmp_path,
        "deployments",
        [{"metadata": {"namespace": "argocd", "name": "argocd-server"}, "spec": {"replicas": 1, "template": {"spec": {"containers": [{"name": "server", "image": f"quay.io/argoproj/argocd:v{version}"}]}}}, "status": {"readyReplicas": 1}}],
    )
    _write(tmp_path, "configmaps", [{"metadata": {"namespace": "argocd", "name": "argocd-cm"}, "data": cm}])
    _write(tmp_path, "applications.argoproj.io", apps)
    for stem in ("statefulsets", "appprojects.argoproj.io", "applicationsets.argoproj.io", "ingresses.networking.k8s.io", "pods", "services"):
        _write(tmp_path, stem, [])


def _app(name, automated):
    return {
        "metadata": {"namespace": "argocd", "name": name},
        "spec": {"project": "default", "source": {"repoURL": "https://git/x", "targetRevision": "v1.2.3", "path": "k8s"}, "destination": {"namespace": "prod"}, "syncPolicy": {"automated": automated} if automated is not None else {}},
        "status": {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}, "reconciledAt": NOW.isoformat()},
    }


def test_argocd_automated_requires_enabled_not_false_and_3x_defaults_to_120s(tmp_path):
    _argo_snapshot(tmp_path, "3.2.0", {}, [_app("on", {}), _app("off", {"enabled": False, "selfHeal": True}), _app("manual", None)])
    out = argocdctl.analyze(tmp_path, INV)
    assert out["config"]["timeout_reconciliation_s"] == 120 and out["config"]["timeout_reconciliation"] == "120s (default)"
    assert sorted(out["summary"]["prod_not_automated"]) == ["argocd/application/manual", "argocd/application/off"]
    assert out["summary"]["prod_no_self_heal"] == ["argocd/application/on"]


def test_argocd_2x_keeps_180s_and_reads_compound_durations(tmp_path):
    _argo_snapshot(tmp_path, "2.13.0", {"timeout.reconciliation": "2m30s"}, [])
    out = argocdctl.analyze(tmp_path, INV)
    assert out["config"]["timeout_reconciliation_s"] == 150
    _argo_snapshot(tmp_path, "2.13.0", {}, [])
    assert argocdctl.analyze(tmp_path, INV)["config"]["timeout_reconciliation_s"] == 180


def test_eso_refresh_interval_reads_go_durations_and_zero_means_disabled():
    assert esoctl._interval_h("1h30m") == 1.5
    assert esoctl._interval_h("90m0s") == 1.5
    assert esoctl._interval_h("0") is None
    assert esoctl._interval_h("1h") == 1.0


def _cm_snapshot(tmp_path, certs, crs, orders):
    _write(tmp_path, "certificates.cert-manager.io", certs)
    _write(tmp_path, "certificaterequests.cert-manager.io", crs)
    _write(tmp_path, "orders.acme.cert-manager.io", orders)
    for stem in (
        "deployments",
        "clusterissuers.cert-manager.io",
        "issuers.cert-manager.io",
        "challenges.acme.cert-manager.io",
        "ingresses.networking.k8s.io",
        "validatingwebhookconfigurations.admissionregistration.k8s.io",
        "mutatingwebhookconfigurations.admissionregistration.k8s.io",
    ):
        _write(tmp_path, stem, [])


def _cr(name, status, reason, age_h):
    return {"metadata": {"namespace": "p", "name": name, "creationTimestamp": (NOW - dt.timedelta(hours=age_h)).isoformat()}, "status": {"conditions": [{"type": "Ready", "status": status, "reason": reason}]}}


def _cert(name, issuing_age_h):
    conds = [{"type": "Ready", "status": "False", "reason": "DoesNotExist"}, {"type": "Issuing", "status": "True", "reason": "DoesNotExist", "lastTransitionTime": (NOW - dt.timedelta(hours=issuing_age_h)).isoformat()}]
    return {"metadata": {"namespace": "p", "name": name}, "spec": {"secretName": name, "issuerRef": {"kind": "ClusterIssuer", "name": "le"}}, "status": {"conditions": conds}}


def test_certificate_requests_pending_are_not_failed_and_issuing_is_stuck_only_after_an_hour(tmp_path):
    _cm_snapshot(
        tmp_path,
        [_cert("fresh", 0.05), _cert("stuck", 3)],
        [_cr("inflight", "False", "Pending", 0.1), _cr("old-inflight", "False", "Pending", 2), _cr("bad", "False", "Failed", 1), _cr("ok", "True", "Issued", 1)],
        [{"metadata": {"namespace": "p", "name": "o1"}, "status": {"state": "expired", "reason": "too late"}}],
    )
    s = certmanager.analyze(tmp_path, INV)["summary"]
    assert s["certificaterequests_failed"] == ["p/bad(Failed)"]
    assert s["certificaterequests_pending_old"] == ["p/old-inflight"]
    assert [x.split("(")[0] for x in s["issuing_stuck"]] == ["p/certificate/stuck"]
    assert s["orders_bad"] == ["p/o1(expired: too late)"]


def test_runner_pods_and_sidecars_and_cluster_roles(tmp_path):
    assert "Runner" in tenancy.CI_OWNER_KINDS and "ScaledJob" not in tenancy.CI_OWNER_KINDS
    pod = {
        "spec": {
            "containers": [{"name": "app", "resources": {"requests": {"cpu": "500m"}}}],
            "initContainers": [{"name": "proxy", "restartPolicy": "Always", "resources": {"requests": {"cpu": "250m"}}}, {"name": "init", "resources": {"requests": {"cpu": "4"}}}],
        }
    }
    assert tenancy._requests(pod)[0] == pytest.approx(0.75)


def test_summerwind_runner_deployment_reads_its_runner_spec_and_autoscaler(tmp_path):
    _write(
        tmp_path,
        "runnerdeployments.actions.summerwind.dev",
        [{"metadata": {"namespace": "arc-runners", "name": "build"}, "spec": {"replicas": 2, "template": {"spec": {"resources": {"requests": {"cpu": "1", "memory": "2Gi"}}, "dockerdContainerResources": {"requests": {"cpu": "500m"}}}}}}],
    )
    _write(tmp_path, "horizontalrunnerautoscalers.actions.summerwind.dev", [{"metadata": {"namespace": "arc-runners", "name": "build"}, "spec": {"scaleTargetRef": {"name": "build"}, "minReplicas": 1, "maxReplicas": 8}}])
    _write(tmp_path, "nodepools.karpenter.sh", [{"metadata": {"name": "default"}, "spec": {}, "status": {"resources": {"cpu": "8"}}}])
    for stem in (
        "autoscalingrunnersets.actions.github.com",
        "scaledjobs.keda.sh",
        "namespaces",
        "pods",
        "resourcequotas",
        "limitranges",
        "networkpolicies.networking.k8s.io",
        "rolebindings.rbac.authorization.k8s.io",
        "deployments",
        "statefulsets",
        "daemonsets",
        "cronjobs",
        "nodes",
    ):
        _write(tmp_path, stem, [])
    inv = {**INV, "nodes": {"nodes": [{"name": "n1", "nodepool": "default"}, {"name": "n2", "nodepool": "default"}]}}
    cx = tenancy._Ctx(tmp_path, inv)
    row = tenancy._ci_templates(cx, [])[0]
    assert (row["min"], row["max"], row["cpu_request"], row["has_requests"]) == (1, 8, 1.5, True)
    assert cx.pools["default"]["nodeclaims"] == 2  # v1beta1 pools have no status.resources.nodes: the pool's nodes are counted (N-4)


# ---------- O-1 ... O-6 ----------


def _karpenter_snapshot(tmp_path, api: str, pool: dict, claims: list):
    _write(tmp_path, "nodepools.karpenter.sh", [{"apiVersion": api, "metadata": {"name": "default"}, **pool}])
    _write(tmp_path, "nodeclaims.karpenter.sh", [{"apiVersion": api, **c} for c in claims])
    _write(
        tmp_path,
        "events",
        [
            {"reason": "DisruptionBlocked", "involvedObject": {"kind": "NodePool", "name": "default"}, "message": 'Cannot disrupt NodeClaim: pdb "prod/api" prevents pod evictions', "count": 3},
            {"reason": "DisruptionBlocked", "involvedObject": {"kind": "NodePool", "name": "default"}, "message": "Cannot disrupt Node: state node is nominated for a pending pod", "count": 2},
        ],
        folder="",
    )
    for stem in ("pods", "deployments", "horizontalpodautoscalers.autoscaling", "scaledobjects.keda.sh", "apiservices.apiregistration.k8s.io", "nodes", "poddisruptionbudgets.policy"):
        _write(tmp_path, stem, [])


def _claim(name, age_h, conds):
    return {
        "metadata": {"name": name, "labels": {"karpenter.sh/nodepool": "default"}, "creationTimestamp": (NOW - dt.timedelta(hours=age_h)).isoformat()},
        "status": {"nodeName": name, "conditions": [{"type": t, "status": "True", "lastTransitionTime": NOW.isoformat()} for t in conds]},
    }


def test_karpenter_v1_expire_after_lives_on_the_template_and_expiry_is_computed(tmp_path):
    own = _claim("own", 800, ["Ready"])
    own["spec"] = {"expireAfter": "2000h"}  # the claim keeps the expireAfter it was made with; a later pool edit does not move it
    never = _claim("never", 800, ["Ready"])
    never["spec"] = {"expireAfter": "Never"}
    _karpenter_snapshot(
        tmp_path, "karpenter.sh/v1", {"spec": {"disruption": {"consolidationPolicy": "WhenEmptyOrUnderutilized"}, "template": {"spec": {"expireAfter": "720h"}}}}, [_claim("old", 800, ["Ready"]), _claim("young", 10, ["Ready"]), own, never]
    )
    k = scaling._karpenter(tmp_path, INV, NOW)
    assert k["nodepools"][0]["expire_after"] == "720h" and k["nodepools"][0]["expire_after_h"] == 720
    assert [r["name"] for r in k["expired_not_replaced"]] == ["old"]
    assert k["nodepools"][0]["disruption_blocked"] == {"PDB": 3, "nominated for pending pods": 2}


def test_karpenter_v1beta1_keeps_the_expired_condition(tmp_path):
    _karpenter_snapshot(tmp_path, "karpenter.sh/v1beta1", {"spec": {"disruption": {"consolidationPolicy": "WhenUnderutilized", "expireAfter": "720h"}}}, [_claim("flagged", 800, ["Ready", "Expired"]), _claim("unflagged", 800, ["Ready"])])
    k = scaling._karpenter(tmp_path, INV, NOW)
    assert k["nodepools"][0]["expire_after_h"] == 720
    assert [r["name"] for r in k["expired_not_replaced"]] == ["flagged"]


def test_ec2nodeclass_root_volume_is_the_flagged_mapping(tmp_path):
    _write(
        tmp_path,
        "ec2nodeclasses.karpenter.k8s.aws",
        [
            {
                "metadata": {"name": "al2023"},
                "spec": {
                    "amiFamily": "AL2023",
                    "amiSelectorTerms": [{"alias": "al2023@latest"}],
                    "blockDeviceMappings": [
                        {"deviceName": "/dev/xvdb", "ebs": {"volumeSize": "500Gi", "volumeType": "st1", "encrypted": False}},
                        {"deviceName": "/dev/xvda", "rootVolume": True, "ebs": {"volumeSize": "100Gi", "volumeType": "gp3", "encrypted": True}},
                    ],
                },
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        ],
    )
    _write(tmp_path, "nodepools.karpenter.sh", [{"metadata": {"name": "default"}, "spec": {"template": {"spec": {"nodeClassRef": {"name": "al2023"}}}}}])
    for stem in ("deployments", "pods", "poddisruptionbudgets.policy", "serviceaccounts", "nodeclaims.karpenter.sh"):
        _write(tmp_path, stem, [])
    c = karpenterctl.analyze(tmp_path, INV)["ec2nodeclasses"][0]
    assert (c["root_volume_gb"], c["root_volume_type"], c["root_encrypted"]) == (100, "gp3", True)


def test_vpc_cni_booleans_parse_like_strconv_parsebool_and_warm_prefix_defaults_to_zero(tmp_path):
    def ds(env):
        return [
            {
                "metadata": {"namespace": "kube-system", "name": "aws-node"},
                "spec": {"template": {"spec": {"containers": [{"name": "aws-node", "image": "x/amazon-k8s-cni:v1.19.0", "env": [{"name": k, "value": v} for k, v in env.items()]}]}}},
                "status": {"desiredNumberScheduled": 2, "numberReady": 2},
            }
        ]

    _write(tmp_path, "daemonsets", ds({"ENABLE_PREFIX_DELEGATION": "1", "AWS_VPC_K8S_CNI_EXTERNALSNAT": "T", "ENABLE_POD_ENI": "nonsense", "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "tRue"}))
    st = vpccni._settings(tmp_path)
    assert st["prefix_delegation"] is True and st["external_snat"] is True and st["pod_eni"] is False and st["custom_networking"] is False and st["warm_prefix_target"] == 0
    _write(tmp_path, "daemonsets", ds({"WARM_PREFIX_TARGET": "1", "ENABLE_PREFIX_DELEGATION": "false"}))
    st = vpccni._settings(tmp_path)
    assert st["prefix_delegation"] is False and st["warm_prefix_target"] == 1

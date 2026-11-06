"""MetalLB 0.16 serves /metrics only over TLS with authentication, so the checks read what MetalLB publishes as objects; and MetalLB is read on every platform (#155).

The status objects below are the ones the chart and the native manifest of v0.16.2 wrote on a kind cluster on 2026-11-05, reduced to the fields that matter."""

from __future__ import annotations

import json
from pathlib import Path

from lib import k3s, metallbctl, summarize

ROOT = Path(__file__).resolve().parent.parent
INV = {"nodes": {"count": 2, "nodes": [{"name": "kind-worker"}, {"name": "kind-control-plane"}]}}
SKIP = "daemonset metallb-system/speaker serves its metrics on port 9120 (metricshttps), over TLS with authentication, which the pod proxy and the node curl cannot read"
L2_WEB = {
    "metadata": {"name": "l2-lrcz7", "namespace": "metallb-system", "generateName": "l2-", "labels": {"metallb.io/node": "kind-worker", "metallb.io/service-name": "web", "metallb.io/service-namespace": "default"}},
    "spec": {},
    "status": {"node": "kind-worker", "serviceName": "web", "serviceNamespace": "default"},
}
BGP_WEB = {"metadata": {"name": "bgp-778jd", "namespace": "metallb-system"}, "spec": {}, "status": {"node": "kind-worker", "peers": ["lab"], "serviceName": "web", "serviceNamespace": "default"}}
STATE_VALID = {
    "metadata": {"name": "speaker-kind-worker", "labels": {"metallb.io/component-type": "speaker", "metallb.io/node-name": "kind-worker"}},
    "status": {"result": "Valid", "conditions": [{"type": "configReconcilerValid", "status": "True"}]},
}
OVERLAP = 'configuration error: CIDR "172.18.255.200/29" in pool "lab" overlaps with already defined CIDR "172.18.255.205/32"'
STATE_INVALID = {"metadata": {"name": "controller", "labels": {"metallb.io/component-type": "controller"}}, "status": {"result": "Invalid", "errorSummary": OVERLAP}}


def workload(version, port=("metricshttps", 9120)):
    return {
        "metadata": {"name": "speaker", "namespace": "metallb-system"},
        "spec": {"template": {"spec": {"containers": [{"image": f"quay.io/metallb/speaker:{version}", "ports": [{"name": port[0], "containerPort": port[1]}]}]}}},
        "status": {"desiredNumberScheduled": 2, "numberReady": 2},
    }


def service(name, *ips):
    return {"metadata": {"name": name, "namespace": "default"}, "spec": {"type": "LoadBalancer"}, "status": {"loadBalancer": {"ingress": [{"ip": ip} for ip in ips]}}}


def snap(tmp_path, version="v0.16.2", step=None, metrics=None, **kinds):
    objs = tmp_path / "objects"
    objs.mkdir()
    base = {
        "daemonsets": [workload(version)],
        "ipaddresspools.metallb.io": [{"metadata": {"name": "lab"}, "spec": {"addresses": ["172.18.255.200-172.18.255.210"]}}],
        "l2advertisements.metallb.io": [{"metadata": {"name": "lab"}, "spec": {}}],
        "services": [service("web", "172.18.255.200"), service("web2", "172.18.255.201")],
        **{k.replace("__", "."): v for k, v in kinds.items()},
    }
    for stem, items in base.items():
        if items is not None:
            (objs / f"{stem}.json").write_text(json.dumps({"items": items}))
    (tmp_path / "collect-result.json").write_text(json.dumps({"metallb": {"steps": {"metallb-speaker-metrics": step if step is not None else {"ok": True, "skipped": SKIP, "pods": {}, "target": {"skip": SKIP}}}}}))
    if metrics:
        d = tmp_path / "metrics" / "pod" / "metallb-speaker"
        d.mkdir(parents=True)
        (d / "speaker-a.prom").write_text(metrics)
    return tmp_path


L2 = "servicel2statuses__metallb__io"
BGP = "servicebgpstatuses__metallb__io"
STATE = "configurationstates__metallb__io"


def test_the_leader_comes_from_the_status_objects_with_one_row_per_service_ip(tmp_path):
    web2 = {"metadata": {"name": "l2-x"}, "status": {"node": "kind-worker", "serviceName": "web2", "serviceNamespace": "default"}}
    out = metallbctl.analyze(snap(tmp_path, **{L2: [L2_WEB, web2], BGP: [], STATE: [STATE_VALID]}), INV)
    l2, s = out["l2"], out["summary"]
    assert l2["available"] is True and l2["source"].startswith("objects/servicel2statuses") and l2["metrics_tls_only"] is True
    assert l2["announced"] == [{"ip": "172.18.255.200", "node": "kind-worker", "protocol": "layer2", "service": "default/web"}, {"ip": "172.18.255.201", "node": "kind-worker", "protocol": "layer2", "service": "default/web2"}]
    assert (l2["announced_total"], l2["by_node"], l2["leader_node"], l2["leader_share"]) == (2, {"kind-worker": 2}, "kind-worker", 1.0)
    assert s["l2_available"] is True and s["metrics_available"] is False and s["metrics_tls_only"] is True and s["speakers_unreadable"] == []


def test_a_dual_stack_service_counts_each_ip_as_the_metric_does(tmp_path):
    out = metallbctl.analyze(snap(tmp_path, services=[service("web", "172.18.255.200", "fd00::1")], **{L2: [L2_WEB], BGP: [], STATE: []}), INV)
    assert [r["ip"] for r in out["l2"]["announced"]] == ["172.18.255.200", "fd00::1"]


def test_bgp_announcements_read_like_the_metric_protocol_label(tmp_path):
    out = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [BGP_WEB], STATE: [], "bgppeers__metallb__io": [{"metadata": {"name": "lab"}}]}), INV)
    assert out["summary"]["mode"] == "bgp" and out["l2"]["announced"][0] == {"ip": "172.18.255.200", "node": "kind-worker", "protocol": "bgp", "service": "default/web"}


def test_bgp_rows_are_no_l2_leader(tmp_path):
    """Seen on 0.14.9 with a live FRR peer and both advertisement kinds: 2 IPs came out as "4 IPs announced" with both counted as L2 leadership."""
    rows = "".join(f'metallb_speaker_announced{{ip="172.18.255.200",node="kind-worker",protocol="{p}",service="default/web"}} 1\n' for p in ("bgp", "layer2"))
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    l2 = metallbctl.analyze(snap(tmp_path, version="v0.15.2", step=step, metrics=rows + "metallb_k8s_client_config_loaded_bool 1\n", daemonsets=[workload("v0.15.2", ("monitoring", 7472))]), INV)["l2"]
    assert (len(l2["announced"]), l2["announced_total"], l2["by_node"], l2["leader_share"]) == (2, 1, {"kind-worker": 1}, 1.0)


def test_a_bgp_only_cluster_has_no_l2_leader_even_with_one_announcing_node(tmp_path):
    """One eligible node over BGP is not "L2 leaders concentrated on one node"."""
    l2 = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [BGP_WEB]}), INV)["l2"]
    assert (l2["available"], len(l2["announced"]), l2["announced_total"], l2["by_node"], l2["leader_node"], l2["leader_share"]) == (True, 1, 0, {}, None, None)


def test_a_status_created_a_moment_ago_has_no_node_and_is_left_out(tmp_path):
    """CreateOrPatch creates the object first and the next reconcile writes status (layer2_status_controller.go:153@v0.16.2)."""
    out = metallbctl.analyze(snap(tmp_path, **{L2: [{"metadata": {"name": "l2-new"}, "spec": {}}], BGP: [], STATE: []}), INV)
    assert out["l2"]["announced"] == [] and out["l2"]["available"] is True


def test_config_state_is_the_stale_flag_with_its_reason(tmp_path):
    out = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [], STATE: [STATE_INVALID, STATE_VALID]}), INV)
    s = out["summary"]
    assert (s["config_read"], s["config_source"], s["config_stale_pods"], s["config_errors"]) == (True, "configurationstates", ["controller"], [OVERLAP])
    assert s["update_errors_read"] is False and "metallb_k8s_client_update_errors_total" in s["metrics_not_read"]
    assert {r["name"]: (r["component"], r["node"], r["result"]) for r in out["config_states"]} == {"controller": ("controller", None, "Invalid"), "speaker-kind-worker": ("speaker", "kind-worker", "Valid")}


def test_unknown_is_not_a_judgement(tmp_path):
    """Unknown: the component has not reported (configurationstate_types.go:33@v0.16.2, configuration_state_controller.go:56). Only Unknown means the state was not read, never a pass."""
    unknown = {"metadata": {"name": "speaker-kind-worker", "labels": {}}, "status": {"result": "Unknown"}}
    s = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [], STATE: [unknown]}), INV)["summary"]
    assert s["config_read"] is False and s["config_source"] is None and s["config_not_reported"] == ["speaker-kind-worker"]


def test_metrics_stay_the_source_whenever_they_were_read(tmp_path):
    """Up to 0.15 nothing changes, even with ConfigurationState present (v0.15.3) or a ServiceL2Status that disagrees."""
    prom = 'metallb_speaker_announced{ip="172.18.255.200",node="kind-control-plane",protocol="layer2",service="default/web"} 1\nmetallb_k8s_client_config_stale_bool 1\nmetallb_k8s_client_config_loaded_bool 1\nmetallb_k8s_client_update_errors_total 3\n'
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    plain = [workload("v0.15.3", ("monitoring", 7472))]
    s_ = snap(tmp_path, version="v0.15.3", step=step, metrics=prom, daemonsets=plain, **{L2: [L2_WEB], STATE: [STATE_VALID]})
    out = metallbctl.analyze(s_, INV)
    s = out["summary"]
    assert out["l2"]["source"].startswith("metrics/") and out["l2"]["leader_node"] == "kind-control-plane"
    assert (s["config_source"], s["config_stale_pods"], s["update_errors_read"], s["update_errors_total"], s["metrics_tls_only"], s["metrics_not_read"]) == ("metrics", ["speaker-a"], True, 3, False, [])


def test_an_empty_status_list_says_nothing_before_0_16(tmp_path):
    """--enable-l2-service-status defaults to false at v0.14.5 (speaker/main.go:90): the k3s cluster runs it, announces, and has zero objects. Unread metrics stay unread, and the warning stays: the pod proxy failing is real."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "502"}}}
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=step, daemonsets=[workload("v0.14.5", ("monitoring", 7472))], **{L2: []}), INV)
    assert out["l2"]["available"] is False and out["l2"]["metrics_tls_only"] is False and out["summary"]["speakers_unreadable"][0]["pod"] == "speaker-a"


def test_an_empty_status_list_is_an_answer_from_0_16_only_when_it_was_saved(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    saved = metallbctl.analyze(snap(tmp_path / "a", **{L2: [], BGP: []}), INV)["l2"]
    assert saved["available"] is True and saved["announced_total"] == 0
    denied = metallbctl.analyze(snap(tmp_path / "b"), INV)["l2"]  # a role without metallb.io: the files do not exist, and that is not "nothing announced"
    assert denied["available"] is False and denied["metrics_tls_only"] is True


def test_the_https_skip_counts_without_a_version(tmp_path):
    """An image pinned by digest has no version in its tag; the step's reason still says the metrics are over TLS."""
    wl = workload("v0.16.2")
    wl["spec"]["template"]["spec"]["containers"][0]["image"] = "quay.io/metallb/speaker@sha256:abc"
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[wl], **{L2: [L2_WEB], BGP: [], STATE: []}), INV)["summary"]
    assert s["version"] is None and s["metrics_tls_only"] is True and s["l2_available"] is True


def test_a_disabled_metrics_port_on_0_16_is_not_an_unreadable_speaker(tmp_path):
    """--port=0 (speaker/main.go:99@v0.16.2): no port to discover, so the step tries the default and every pod fails. Nothing is wrong with the speaker."""
    step = {"ok": False, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "connection refused"}}}
    wl = workload("v0.16.2")
    wl["spec"]["template"]["spec"]["containers"][0]["ports"] = []
    s = metallbctl.analyze(snap(tmp_path, step=step, daemonsets=[wl], **{L2: [L2_WEB], BGP: [], STATE: [STATE_VALID]}), INV)["summary"]
    assert s["speakers_unreadable"] == [] and s["metrics_tls_only"] is True


def test_metallb_is_read_on_a_platform_that_is_not_k3s(tmp_path):
    """Pools and Services were built inside lib/k3s.py, so on kubeadm a Service counted as 0 and the L2 check raised KeyError on an empty dict. Observed on kind before this change."""
    s_ = snap(tmp_path, **{L2: [L2_WEB], BGP: [], STATE: [STATE_VALID]})
    out = metallbctl.analyze(s_, {**INV, "cluster": {"platform": "kubeadm"}})
    assert (out["summary"]["pools"], out["summary"]["total_ips"], out["summary"]["used"], out["summary"]["lb_services"]) == (1, 11, 2, 2)
    assert out["pools"]["present"] is True and out["pools"]["free"] == 9 and out["l2"]["available"] is True


def test_no_metallb_stays_absent(tmp_path):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "services.json").write_text(json.dumps({"items": [service("elb", "1.2.3.4")]}))
    assert metallbctl.analyze(tmp_path, {}) == {"present": False}


def test_the_k3s_section_no_longer_carries_metallb(tmp_path):
    """One reader: k3s.cluster.metallb would only repeat metallb, and the fixtures of collectors/k3s-platform/checks.yaml no longer list it."""
    assert "_metallb" not in (ROOT / "lib" / "k3s.py").read_text(encoding="utf-8")
    assert next(row for row in summarize.COMPONENT_SECTIONS if row[0] == "metallb")[3] is None
    assert not hasattr(k3s, "_metallb")


def frr_first(version):
    """metallb-frr.yaml: the DaemonSet's first container is frr (config/manifests/metallb-frr.yaml:1904,1993@v0.14.9)."""
    wl = workload(version, ("monitoring", 7472))
    speaker = wl["spec"]["template"]["spec"]["containers"][0]
    speaker["name"] = "speaker"
    wl["spec"]["template"]["spec"]["containers"] = [{"name": "frr", "image": "quay.io/frrouting/frr:9.1.0"}, speaker]
    return wl


def test_the_frr_container_is_not_the_metallb_version(tmp_path):
    """Read from the first container, 9.1.0 passed as 0.16 or later: an unreadable 0.14 speaker stopped warning. Review of this change, measured with a proxy returning 503."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "HTTP 503"}}}
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, daemonsets=[frr_first("v0.14.9")]), INV)["summary"]
    assert s["version"] == "0.14.9" and s["metrics_tls_only"] is False and s["metrics_not_read"] == []
    assert [e["pod"] for e in s["speakers_unreadable"]] == ["speaker-a"]


def test_another_daemonset_called_speaker_is_not_metallb(tmp_path):
    other = {"metadata": {"name": "a-speaker", "namespace": "voice"}, "spec": {"template": {"spec": {"containers": [{"name": "speaker", "image": "example.com/voice:9.9.9"}]}}}, "status": {}}
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[other, workload("v0.16.2")], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert s["version"] == "0.16.2"


def test_counters_nobody_read_are_null_not_zero(tmp_path):
    s = metallbctl.analyze(snap(tmp_path, **{L2: [L2_WEB], BGP: [], STATE: [STATE_VALID]}), INV)["summary"]
    assert all(s[k] is None for k in ("update_errors_total", "arp_requests_total", "arp_responses_total", "gratuitous_total", "bgp_sessions", "bgp_sessions_up"))


def test_one_valid_state_does_not_stand_for_the_cluster(tmp_path):
    """Two speakers desired (workload()), a controller Deployment, and only one speaker's object: the rest is named, and the check warns on it."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    controller = {
        "metadata": {"name": "controller", "namespace": "metallb-system"},
        "spec": {"replicas": 1, "template": {"spec": {"containers": [{"name": "controller", "image": "quay.io/metallb/controller:v0.16.2"}]}}},
        "status": {"readyReplicas": 1},
    }
    s = metallbctl.analyze(snap(tmp_path / "a", deployments=[controller], **{L2: [], BGP: [], STATE: [STATE_VALID]}), INV)["summary"]
    assert s["config_read"] is True and s["config_not_reported"] == ["1 of 2 speakers", "controller"]
    unknown = {"metadata": {"name": "speaker-kind-control-plane", "labels": {"metallb.io/component-type": "speaker"}}, "status": {"result": "Unknown"}}
    s = metallbctl.analyze(snap(tmp_path / "b", **{L2: [], BGP: [], STATE: [STATE_VALID, unknown]}), INV)["summary"]
    assert s["config_not_reported"] == ["speaker-kind-control-plane"]


def test_a_status_with_nothing_to_announce_does_not_count(tmp_path):
    """Its row would dilute the leader share: two IPs on one node are a fail, a third row for a Service that is gone turned it into a pass."""
    gone = {"metadata": {"name": "l2-gone"}, "status": {"node": "kind-control-plane", "serviceName": "deleted", "serviceNamespace": "default"}}
    pending = {"metadata": {"name": "l2-p"}, "status": {"node": "kind-control-plane", "serviceName": "pending", "serviceNamespace": "default"}}
    web2 = {"metadata": {"name": "l2-x"}, "status": {"node": "kind-worker", "serviceName": "web2", "serviceNamespace": "default"}}
    services = [service("web", "172.18.255.200"), service("web2", "172.18.255.201"), service("pending")]
    l2 = metallbctl.analyze(snap(tmp_path, services=services, **{L2: [L2_WEB, web2, gone, pending], BGP: [], STATE: []}), INV)["l2"]
    assert l2["announced_total"] == 2 and l2["leader_share"] == 1.0


def test_a_bgp_status_of_a_node_that_is_gone_does_not_count(tmp_path):
    """Only its own node removes a ServiceBGPStatus (bgp_status_controller.go:76-87@v0.16.2); until the Pod object is collected the row stays."""
    gone = {"metadata": {"name": "bgp-old"}, "status": {"node": "node-removed", "peers": ["lab"], "serviceName": "web", "serviceNamespace": "default"}}
    l2 = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [BGP_WEB, gone], STATE: []}), INV)["l2"]
    assert [r["node"] for r in l2["announced"]] == ["kind-worker"]


def test_every_metallb_check_runs_wherever_metallb_is_present():
    """`profiles: [lab]` reported all six as disabled on a kubeadm cluster of 4 nodes or more (small-prod, lib/discover.py), so being read was not enough."""
    from lib import yamlite

    checks = yamlite.load_file(ROOT / "collectors/metallb/checks.yaml")
    assert len(checks) == 6 and all(set(c["profiles"]) == {"prod", "lab"} for c in checks)


def test_a_metric_file_without_a_metallb_series_is_not_a_read(tmp_path):
    """Observed on kind at v0.14.9 with metallb-frr.yaml: the step read the frr-metrics sidecar and saved only process_* lines, and every metric check passed."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    prom = "process_resident_memory_bytes 2.0e+07\nprocess_start_time_seconds 1.7e+09\n"
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=prom, daemonsets=[frr_first("v0.14.9")]), INV)
    assert out["summary"]["metrics_available"] is False and out["summary"]["speakers_read"] == 0 and out["summary"]["config_read"] is False and out["l2"]["available"] is False


def test_the_frr_sidecar_series_do_not_make_a_read(tmp_path):
    """The sidecar prints metallb_bgp_session_up (frr-tools/metrics/collector/bgp.go:21@v0.14.9): a filter on `metallb_` let it through on a BGP cluster, with no config value behind `config_read`."""
    step = {"ok": True, "target": {"port": 7473}, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    prom = 'metallb_bgp_session_up{peer="172.20.0.4:179"} 1\nmetallb_bgp_updates_total{peer="172.20.0.4:179"} 2\n'
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=prom, daemonsets=[frr_first("v0.14.9")], bgppeers__metallb__io=[{"metadata": {"name": "lab"}}]), INV)["summary"]
    assert s["metrics_available"] is False and s["config_read"] is False
    assert s["speakers_unreadable"] == [{"pod": "speaker-a", "node": "kind-worker", "error": "port 7473 answered with no MetalLB series"}]


GOOD = "metallb_k8s_client_config_loaded_bool 1\nmetallb_k8s_client_config_stale_bool 0\nmetallb_k8s_client_update_errors_total 0\n"


def test_bgp_sessions_on_an_frr_install_are_unknown_not_zero(tmp_path):
    """The gauge is the sidecar's in FRR mode (internal/bgp/native/stats.go:51@v0.16.2 registers it for native only): good speaker files and peers say nothing about the sessions."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=GOOD, daemonsets=[frr_first("v0.14.9")], bgppeers__metallb__io=[{"metadata": {"name": "lab"}}]), INV)["summary"]
    assert s["bgp_sessions"] is None and s["bgp_sessions_up"] is None and s["metrics_not_read"] == ["metallb_bgp_session_up"]
    assert s["update_errors_total"] == 0


def test_layer2_without_peers_has_zero_sessions(tmp_path):
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=GOOD, daemonsets=[workload("v0.14.9", ("monitoring", 7472))]), INV)["summary"]
    assert s["bgp_sessions"] == 0 and s["metrics_not_read"] == []


def test_one_good_file_does_not_hide_a_pod_that_answered_with_nothing(tmp_path):
    step = {"ok": True, "target": {"port": 7473}, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}, "speaker-b": {"ok": True, "node": "kind-control-plane"}}}
    s_ = snap(tmp_path, version="v0.14.9", step=step, metrics=GOOD, daemonsets=[workload("v0.14.9", ("monitoring", 7472))])
    (tmp_path / "metrics" / "pod" / "metallb-speaker" / "speaker-b.prom").write_text("process_start_time_seconds 1.7e+09\n")
    s = metallbctl.analyze(s_, INV)["summary"]
    assert s["speakers_read"] == 1 and [e["pod"] for e in s["speakers_unreadable"]] == ["speaker-b"]


def test_a_speaker_pinned_on_purpose_is_named(tmp_path):
    """Two speakers of four nodes with a nodeSelector is a layout, not a fault. The os selector of every manifest does not count as pinning."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    pinned = workload("v0.16.2")
    pinned["spec"]["template"]["spec"]["nodeSelector"] = {"kubernetes.io/os": "linux", "role": "edge"}
    inv = {"nodes": {"count": 4, "nodes": [{"name": "kind-worker"}]}}
    s = metallbctl.analyze(snap(tmp_path / "a", daemonsets=[pinned], **{L2: [], BGP: [], STATE: []}), inv)["summary"]
    assert s["speaker_all_nodes"] is False and s["speakers_pinned"] is True
    os_only = workload("v0.16.2")
    os_only["spec"]["template"]["spec"]["nodeSelector"] = {"kubernetes.io/os": "linux"}
    s = metallbctl.analyze(snap(tmp_path / "b", daemonsets=[os_only], **{L2: [], BGP: [], STATE: []}), inv)["summary"]
    assert s["speakers_pinned"] is False

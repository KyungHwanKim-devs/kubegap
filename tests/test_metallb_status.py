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
    assert s["version"] == "0.14.9" and s["metrics_tls_only"] is False and s["metrics_not_read"] == metallbctl.METRICS_NOT_READ
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
    assert len(checks) == 8 and all(set(c["profiles"]) == {"prod", "lab"} for c in checks)


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


def node(name, labels=None, taints=None, **spec):
    return {"metadata": {"name": name, "labels": labels or {}}, "spec": {"taints": taints or [], **spec}}


def test_a_speaker_kept_off_nodes_on_purpose_is_named(tmp_path):
    """Two speakers of four nodes with a nodeSelector is a layout, not a fault. The os selector of every manifest does not count."""
    pinned = workload("v0.16.2")
    pinned["spec"]["template"]["spec"]["nodeSelector"] = {"kubernetes.io/os": "linux", "role": "edge"}
    linux = {"kubernetes.io/os": "linux"}
    nodes = [node("a", {**linux, "role": "edge"}), node("b", {**linux, "role": "edge"}), node("c", linux), node("d", linux)]
    inv = {"nodes": {"count": 4, "nodes": [{"name": n["metadata"]["name"]} for n in nodes]}}
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[pinned], nodes=nodes, **{L2: [], BGP: [], STATE: []}), inv)["summary"]
    assert (s["speaker_all_nodes"], s["speaker_eligible"]) == (False, 2)


def test_a_taint_keeps_a_speaker_off_a_node_like_a_selector_does(tmp_path):
    """T6 of the third review: no selector, one tainted node, speakers 2 of 3. The DaemonSet runs everywhere it can."""
    taint = [{"key": "dedicated", "value": "db", "effect": "NoSchedule"}]
    nodes = [node("a"), node("b"), node("c", taints=taint)]
    inv = {"nodes": {"count": 3, "nodes": [{"name": n["metadata"]["name"]} for n in nodes]}}
    s = metallbctl.analyze(snap(tmp_path, nodes=nodes, **{L2: [], BGP: [], STATE: []}), inv)["summary"]
    assert (s["speaker_eligible"], s["speaker_ready"]) == (2, 2)


def test_no_node_list_means_eligibility_is_unknown(tmp_path):
    s = metallbctl.analyze(snap(tmp_path, **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert s["speaker_eligible"] is None


def test_a_speaker_daemonset_with_no_pod_is_not_a_layout(tmp_path):
    """T1 of the third review: the node label lost, 0 of 0 speakers, two Services still hold IPs. Nothing announces them; the rule fails on speaker_desired 0 with lb_services above 0."""
    pinned = workload("v0.16.2")
    pinned["spec"]["template"]["spec"]["nodeSelector"] = {"lb": "yes"}
    pinned["status"] = {"desiredNumberScheduled": 0, "numberReady": 0}
    nodes = [node("kind-worker"), node("kind-control-plane")]
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[pinned], nodes=nodes, **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["speaker_desired"], s["speaker_ready"], s["speaker_eligible"], s["lb_services"]) == (0, 0, 0, 2)


def test_another_implementations_service_is_not_metallbs(tmp_path):
    """T2 of the third review: MetalLB without --lb-class ignores every Service that sets a class (service_controller.go:159-175@v0.16.2). An NLB with a hostname is neither Pending nor a user of the pool."""
    nlb = {"metadata": {"name": "nlb", "namespace": "default"}, "spec": {"type": "LoadBalancer", "loadBalancerClass": "service.k8s.aws/nlb"}, "status": {"loadBalancer": {"ingress": [{"hostname": "a.elb.amazonaws.com"}]}}}
    vip = {"metadata": {"name": "vip", "namespace": "default"}, "spec": {"type": "LoadBalancer", "loadBalancerClass": "kube-vip.io/kube-vip-class"}, "status": {"loadBalancer": {"ingress": [{"ip": "10.9.9.9"}]}}}
    out = metallbctl.analyze(snap(tmp_path, services=[service("web", "172.18.255.200"), nlb, vip], **{L2: [], BGP: [], STATE: []}), INV)
    s = out["summary"]
    assert (s["pending"], s["used"], s["free"], s["lb_services"], s["lb_services_other_class"]) == ([], 1, 10, 1, 2)


def test_lb_class_set_means_only_that_class_is_metallbs(tmp_path):
    """With --lb-class a Service with no class is ignored as well (service_controller.go:166-168@v0.16.2)."""
    ds = workload("v0.16.2")
    ds["spec"]["template"]["spec"]["containers"][0]["args"] = ["--lb-class=metallb.io/lb"]
    mine = service("mine", "172.18.255.200")
    mine["spec"]["loadBalancerClass"] = "metallb.io/lb"
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[ds], services=[mine, service("other", "10.0.0.1")], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["lb_services"], s["lb_services_other_class"], s["used"]) == (1, 1, 1)


def test_a_pending_metallb_service_stays_pending(tmp_path):
    pending = {"metadata": {"name": "web", "namespace": "default"}, "spec": {"type": "LoadBalancer"}, "status": {}}
    s = metallbctl.analyze(snap(tmp_path, services=[pending], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert s["pending"] == ["default/web"]


def partial_step():
    return {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}, "speaker-b": {"ok": False, "node": "kind-control-plane", "error": "HTTP 503"}}}


PROM = 'metallb_speaker_announced{ip="172.18.255.200",node="kind-worker",protocol="layer2",service="default/web"} 1\nmetallb_k8s_client_config_loaded_bool 1\nmetallb_k8s_client_config_stale_bool 0\n'


def test_an_unread_speaker_answers_through_its_configuration_state(tmp_path):
    """T3 of the third review: one speaker read, the other 503 and Invalid. The answer is in the snapshot, so config-stale must not pass on half its input."""
    invalid = {"metadata": {"name": "speaker-b", "labels": {"metallb.io/component-type": "speaker", "metallb.io/node-name": "kind-control-plane"}}, "status": {"result": "Invalid", "errorSummary": OVERLAP}}
    plain = [workload("v0.15.3", ("monitoring", 7472))]
    s = metallbctl.analyze(snap(tmp_path, version="v0.15.3", step=partial_step(), metrics=PROM, daemonsets=plain, **{STATE: [invalid]}), INV)["summary"]
    assert (s["config_source"], s["config_stale_pods"], s["config_not_reported"]) == ("metrics and configurationstates", ["speaker-b"], [])
    assert s["config_errors"] == [OVERLAP]


def test_a_speaker_no_source_answers_for_is_not_reported(tmp_path):
    plain = [workload("v0.14.9", ("monitoring", 7472))]
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=partial_step(), metrics=PROM, daemonsets=plain), INV)["summary"]
    assert (s["config_source"], s["config_stale_pods"], s["config_not_reported"]) == ("metrics", [], ["speaker-b"])


def test_status_rows_stand_for_the_speakers_nobody_read(tmp_path):
    """One speaker's rows are not the cluster's: the status resources name every leader."""
    other = {"metadata": {"name": "l2-b"}, "status": {"node": "kind-control-plane", "serviceName": "web2", "serviceNamespace": "default"}}
    plain = [workload("v0.15.3", ("monitoring", 7472))]
    l2 = metallbctl.analyze(snap(tmp_path, version="v0.15.3", step=partial_step(), metrics=PROM, daemonsets=plain, **{L2: [L2_WEB, other]}), INV)["l2"]
    assert l2["source"].startswith("objects/") and l2["by_node"] == {"kind-worker": 1, "kind-control-plane": 1}


def test_a_release_named_metallb_something_keeps_its_controller(tmp_path):
    """T5 of the third review: the chart's fullname is the release name when it holds `metallb` (_helpers.tpl:14-20@v0.16.2), so release metallb-prod gives metallb-prod-controller."""
    ctl = {
        "metadata": {"name": "metallb-prod-controller", "namespace": "metallb-system"},
        "spec": {"replicas": 1, "template": {"spec": {"containers": [{"name": "controller", "image": "quay.io/metallb/controller:v0.16.2"}]}}},
        "status": {"readyReplicas": 0},
    }
    s = metallbctl.analyze(snap(tmp_path, deployments=[ctl], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["controller_replicas"], s["controller_ready"]) == (1, 0)


def test_another_operators_controller_is_not_metallbs(tmp_path):
    ctl = {
        "metadata": {"name": "ingress-nginx-controller", "namespace": "ingress"},
        "spec": {"replicas": 2, "template": {"spec": {"containers": [{"name": "controller", "image": "registry.k8s.io/ingress-nginx/controller:v1.10.0"}]}}},
        "status": {"readyReplicas": 2},
    }
    s = metallbctl.analyze(snap(tmp_path, deployments=[ctl], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert s["controller_replicas"] is None


def test_bgp_rows_do_not_make_l2_read(tmp_path):
    """T7 of the third review: the ServiceL2Status List failed, BGP rows exist: L2 was not read."""
    l2 = metallbctl.analyze(snap(tmp_path, **{L2: None, BGP: [BGP_WEB], STATE: []}), INV)["l2"]
    assert (l2["available"], l2["source"], l2["announced_total"]) == (False, None, 0)


def test_unread_values_are_unread_everywhere(tmp_path):
    """T8 of the third review: the per-pod BGP values and the list of metrics not read."""
    prom = "metallb_k8s_client_config_loaded_bool 1\n"
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    plain = [workload("v0.14.9", ("monitoring", 7472))]
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=prom, daemonsets=plain, bgppeers__metallb__io=[{"metadata": {"name": "lab"}}]), INV)
    assert out["speaker_metrics"]["speaker-a"]["bgp_sessions"] is None and out["speaker_metrics"]["speaker-a"]["bgp_sessions_up"] is None


def test_metrics_unread_before_0_16_are_named_too(tmp_path):
    step = {"ok": True, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "HTTP 503"}}}
    s = metallbctl.analyze(snap(tmp_path, version="v0.15.3", step=step, daemonsets=[workload("v0.15.3", ("monitoring", 7472))]), INV)["summary"]
    assert s["metrics_not_read"] == metallbctl.METRICS_NOT_READ


def foreign_speaker(desired=2, **template):
    return {
        "metadata": {"name": "announce-speaker", "namespace": "voice"},
        "spec": {"selector": {"matchLabels": {"app": "tts"}}, "template": {"spec": {"containers": [{"name": "tts", "image": "ghcr.io/acme/tts-speaker:1.2.3"}], **template}}},
        "status": {"desiredNumberScheduled": desired, "numberReady": desired},
    }


def bare(tmp_path, **kinds):
    objs = tmp_path / "objects"
    objs.mkdir()
    for stem, items in kinds.items():
        (objs / f"{stem}.json").write_text(json.dumps({"items": items}))
    return tmp_path


def test_a_speaker_shaped_name_alone_is_not_metallb(tmp_path):
    """U2 of the fourth review: no MetalLB, a DaemonSet called x-speaker. No section, so no MetalLB finding, with or without cloud LoadBalancer Services."""
    assert metallbctl.analyze(bare(tmp_path, daemonsets=[foreign_speaker(0, nodeSelector={"x": "y"})], services=[service("cloud")]), INV) == {"present": False}


def test_labels_identify_metallb_past_a_fullname_override_and_a_mirror(tmp_path):
    """U2: `fullnameOverride: lb` and mirrored images: neither the name nor the image says metallb, the selector does, for the speaker and the controller."""
    labels = lambda role: {"app.kubernetes.io/name": "metallb", "app.kubernetes.io/component": role}  # noqa: E731
    ds = {
        "metadata": {"name": "lb-speaker", "namespace": "net"},
        "spec": {"selector": {"matchLabels": labels("speaker")}, "template": {"spec": {"containers": [{"name": "speaker", "image": "harbor.corp/net/speaker:v0.16.2"}]}}},
        "status": {"desiredNumberScheduled": 2, "numberReady": 2},
    }
    dp = {
        "metadata": {"name": "lb-controller", "namespace": "net"},
        "spec": {"replicas": 1, "selector": {"matchLabels": labels("controller")}, "template": {"spec": {"containers": [{"name": "controller", "image": "harbor.corp/net/controller:v0.16.2"}]}}},
        "status": {"readyReplicas": 1},
    }
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[ds], deployments=[dp], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["speaker_desired"], s["controller_replicas"], s["version"]) == (2, 1, "0.16.2")


def test_a_renamed_daemonset_is_found_by_its_labels(tmp_path):
    """U1 row E2: `speaker-prod` does not end in -speaker."""
    ds = workload("v0.16.2")
    ds["metadata"]["name"] = "speaker-prod"
    ds["spec"]["selector"] = {"matchLabels": {"app": "metallb", "component": "speaker"}}
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[ds], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert s["speaker_desired"] == 2


def test_unknown_speakers_are_not_zero_speakers(tmp_path):
    """U1: a DaemonSet List that failed leaves `objects/daemonsets.json` absent: the summary says not read, and the rule's needs skips on it."""
    s = metallbctl.analyze(snap(tmp_path, daemonsets=None, **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["speaker_desired"], s["daemonsets_read"]) == (None, False)


def test_no_speaker_daemonset_found_is_said_as_found(tmp_path):
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[], **{L2: [], BGP: [], STATE: []}), INV)["summary"]
    assert (s["speaker_desired"], s["daemonsets_read"]) == (None, True)


def test_a_bgp_cluster_keeps_its_metric_path_with_one_speaker_unread(tmp_path):
    """U4: BGP rows hold no L2, so they must not replace the metric path: the leader check has no L2 to judge rather than saying nothing was read."""
    step = partial_step()
    plain = [workload("v0.15.3", ("monitoring", 7472))]
    prom = "metallb_k8s_client_config_loaded_bool 1\n"
    l2 = metallbctl.analyze(snap(tmp_path, version="v0.15.3", step=step, metrics=prom, daemonsets=plain, **{BGP: [BGP_WEB], L2: []}), INV)["l2"]
    assert l2["source"].startswith("metrics/") and l2["available"] is True and l2["announced_total"] == 0


def test_part_of_the_rows_is_marked_partial(tmp_path):
    """U5: up to 0.14.5 no status row exists by default, so one speaker's rows are a part: the leader checks skip on `partial`."""
    plain = [workload("v0.14.5", ("monitoring", 7472))]
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=partial_step(), metrics=PROM, daemonsets=plain), INV)
    assert out["l2"]["partial"] is True and out["summary"]["l2_partial"] is True


def test_every_speaker_read_is_not_partial(tmp_path):
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    plain = [workload("v0.14.9", ("monitoring", 7472))]
    assert metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, metrics=PROM, daemonsets=plain), INV)["l2"]["partial"] is False


def test_a_single_dash_lb_class_is_read(tmp_path):
    """U6: Go's flag package takes one dash or two (golang/go src/flag/flag.go:52-53@go1.25.0)."""
    for args in (["-lb-class=metallb.io/lb"], ["--lb-class=metallb.io/lb"], ["--lb-class", "metallb.io/lb"], ["-lb-class", "metallb.io/lb"]):
        assert metallbctl._lb_class({"args": args}) == "metallb.io/lb"
    assert metallbctl._lb_class({"args": ["--port=7472"]}) == ""


def test_the_rule_reads_no_removed_key():
    text = (ROOT / "collectors/metallb/checks.yaml").read_text(encoding="utf-8")
    assert "speakers_pinned" not in text and "kept off tainted nodes" not in text


# ---------- #162: a Service IP nobody announces, and a BGP session that is down ----------

STATES_ONE_DOWN = [
    {"metadata": {"name": "kind-worker-10.0.0.1"}, "status": {"node": "kind-worker", "peer": "10.0.0.1", "vrf": "default", "bgpStatus": "Established", "bfdStatus": "N/A"}},
    {"metadata": {"name": "kind-worker-10.0.0.2"}, "status": {"node": "kind-worker", "peer": "10.0.0.2", "vrf": "default", "bgpStatus": "Idle", "bfdStatus": "N/A"}},
]
SESSIONS = "bgpsessionstates__frrk8s__metallb__io"
PEERS = [{"metadata": {"name": "p1"}, "spec": {"peerAddress": "10.0.0.1"}}, {"metadata": {"name": "p2"}, "spec": {"peerAddress": "10.0.0.2"}}]


def sub(p, name):
    d = p / name
    d.mkdir()
    return d


def with_env(wl, value):
    wl["spec"]["template"]["spec"]["containers"][0]["env"] = [{"name": "METALLB_BGP_TYPE", "value": value}]
    return wl


def rows(out):
    return {s["name"]: (s["pool"], s["pool_advertised"], s["announced_by"], s["announcers_read"]) for s in out["pools"]["services"]}


def test_the_issue_s_fixture_is_two_services_nobody_announces(tmp_path):
    """#162: 0.16.2, speakers 2 of 2, no L2Advertisement, empty status lists, two Services with IPs. Every row says so: the pool is known, nothing reaches it, nobody announces, and the announcers were read (0.16 writes the status objects)."""
    out = metallbctl.analyze(snap(tmp_path, **{"l2advertisements__metallb__io": [], L2: [], BGP: [], STATE: [STATE_VALID]}), INV)
    assert rows(out) == {"web": ("lab", [], [], True), "web2": ("lab", [], [], True)}


def test_an_announced_service_names_its_nodes_and_the_advertisement_that_reaches_the_pool(tmp_path):
    out = metallbctl.analyze(snap(tmp_path, **{L2: [L2_WEB], BGP: [], STATE: [STATE_VALID]}), INV)
    assert rows(out) == {"web": ("lab", ["L2Advertisement/lab"], [{"node": "kind-worker", "protocol": "layer2"}], True), "web2": ("lab", ["L2Advertisement/lab"], [], True)}


def test_an_advertisement_reaches_pools_by_name_by_selector_or_all(tmp_path):
    """internal/config/config.go:699-700,738-739@v0.16.2: both lists empty reaches every pool; else the names and the label-selector matches."""
    pools = [
        {"metadata": {"name": "a", "labels": {"tier": "edge"}}, "spec": {"addresses": ["172.18.255.200-172.18.255.201"]}},
        {"metadata": {"name": "b", "labels": {"tier": "core"}}, "spec": {"addresses": ["172.18.255.202/31"]}},
        {"metadata": {"name": "c"}, "spec": {"addresses": ["172.18.255.204/32"]}},
    ]
    l2 = [{"metadata": {"name": "all"}, "spec": {}}, {"metadata": {"name": "named"}, "spec": {"ipAddressPools": ["b"]}}]
    bgp = [
        {"metadata": {"name": "edge"}, "spec": {"ipAddressPoolSelectors": [{"matchLabels": {"tier": "edge"}}]}},
        {"metadata": {"name": "nomatch"}, "spec": {"ipAddressPoolSelectors": [{"matchExpressions": [{"key": "tier", "operator": "In", "values": ["none"]}]}]}},
    ]
    s = snap(tmp_path, **{"ipaddresspools__metallb__io": pools, "l2advertisements__metallb__io": l2, "bgpadvertisements__metallb__io": bgp, L2: [], BGP: [], STATE: []})
    assert metallbctl._advertised_pools(s, pools) == {"a": ["L2Advertisement/all", "BGPAdvertisement/edge"], "b": ["L2Advertisement/all", "L2Advertisement/named"], "c": ["L2Advertisement/all"]}
    services = [service("w", "172.18.255.203"), service("x", "172.18.255.204"), service("y", "192.0.2.9")]
    s2 = snap(sub(tmp_path, "2"), **{"ipaddresspools__metallb__io": pools, "l2advertisements__metallb__io": [], "bgpadvertisements__metallb__io": [], "services": services, L2: [], BGP: [], STATE: []})
    assert {r: v[:2] for r, v in rows(metallbctl.analyze(s2, INV)).items()} == {"w": ("b", []), "x": ("c", []), "y": (None, None)}


def test_an_empty_status_list_is_an_answer_from_0_14_6(tmp_path):
    """The `--enable-l2-service-status` flag of v0.14.5 (speaker/main.go:90) is gone at v0.14.6: from there the speaker writes ServiceL2Status for every announced Service, so an empty saved list means nobody announces (STATUS_ALWAYS_SINCE)."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "502"}}}
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.6", step=step, daemonsets=[workload("v0.14.6", ("monitoring", 7472))], **{L2: []}), INV)
    assert out["l2"]["available"] is True and out["l2"]["source"].startswith("objects/") and out["l2"]["announced_total"] == 0
    assert rows(out)["web"] == ("lab", ["L2Advertisement/lab"], [], True)
    older = metallbctl.analyze(snap(sub(tmp_path, "old"), version="v0.14.5", step=step, daemonsets=[workload("v0.14.5", ("monitoring", 7472))], **{L2: []}), INV)
    assert older["l2"]["available"] is False and rows(older)["web"] == ("lab", ["L2Advertisement/lab"], [], False)


def test_unread_speakers_leave_the_announcers_unread(tmp_path):
    """One speaker of two read on 0.14.5 and no status objects: its rows are a part, so no Service is judged on them (partial), only on its pool's advertisements."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}, "speaker-b": {"ok": False, "node": "kind-control-plane", "error": "502"}}}
    prom = 'metallb_speaker_announced{ip="172.18.255.200",node="kind-worker",protocol="layer2",service="default/web"} 1\nmetallb_k8s_client_config_loaded_bool 1\n'
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=step, metrics=prom, daemonsets=[workload("v0.14.5", ("monitoring", 7472))]), INV)
    assert out["l2"]["partial"] is True and rows(out)["web2"] == ("lab", ["L2Advertisement/lab"], [], False)


def test_bgp_sessions_come_from_the_speaker_metrics_in_native_mode(tmp_path):
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    prom = 'metallb_bgp_session_up{peer="10.0.0.1:179"} 1\nmetallb_bgp_session_up{peer="10.0.0.2:179"} 0\nmetallb_k8s_client_config_loaded_bool 1\n'
    s = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=step, metrics=prom, daemonsets=[workload("v0.14.5", ("monitoring", 7472))], bgppeers__metallb__io=PEERS), INV)["summary"]
    assert (s["bgp_backend"], s["bgp_sessions_read"], s["bgp_session_source"], s["bgp_sessions_total"]) == ("native", True, metallbctl.METRICS_SOURCE, 2)
    assert s["bgp_sessions_down"] == [{"node": "kind-worker", "peer": "10.0.0.2:179", "state": "down"}]


def test_bgp_sessions_come_from_bgpsessionstate_in_frr_k8s_mode(tmp_path):
    """frr-k8s mode from 0.15.2: one BGPSessionState per node and peer, `Established` is the session (metallb/frr-k8s internal/frr/parse.go:41@v0.0.27)."""
    s = metallbctl.analyze(snap(tmp_path, daemonsets=[with_env(workload("v0.16.2"), "frr-k8s")], **{"bgppeers__metallb__io": PEERS, SESSIONS: STATES_ONE_DOWN, L2: [], BGP: [], STATE: []}), INV)
    assert s["bgp_session_states"][1] == {"name": "kind-worker-10.0.0.2", "node": "kind-worker", "peer": "10.0.0.2", "vrf": "default", "bgp_status": "Idle", "bfd_status": "N/A", "up": False}
    sm = s["summary"]
    assert (sm["bgp_backend"], sm["bgp_sessions_read"], sm["bgp_session_source"], sm["bgp_sessions_total"]) == ("frr-k8s", True, f"objects/{metallbctl.BGP_SESSION_STATE}.json", 2)
    assert sm["bgp_sessions_down"] == [{"node": "kind-worker", "peer": "10.0.0.2", "state": "Idle"}]


def prometheus(tmp_path, result, present):
    d = tmp_path / "metrics"
    d.mkdir(exist_ok=True)
    (d / "metallb_bgp_session_down.json").write_text(json.dumps({"ok": True, "result": result}))
    if present is not None:
        (d / "series-present.json").write_text(json.dumps({"names": present}))


def test_bgp_sessions_come_from_prometheus_when_nothing_else_answers(tmp_path):
    """Native mode on 0.16 (TLS metrics, no BGPSessionState): the session state is Prometheus' when it scrapes the speaker. An empty answer is "all up" only when series-present.json saw the name."""
    down = [{"metric": {"__name__": "metallb_bgp_session_up", "peer": "10.0.0.2:179", "pod": "speaker-x", "node": "kind-worker"}, "value": [0, "0"]}]
    kinds = {"bgppeers__metallb__io": PEERS, L2: [], BGP: [], STATE: []}
    s = snap(tmp_path, **kinds)
    prometheus(s, down, {"metallb_bgp_session_up": 2})
    sm = metallbctl.analyze(s, INV)["summary"]
    assert (sm["bgp_backend"], sm["bgp_sessions_read"], sm["bgp_session_source"], sm["bgp_sessions_total"]) == ("native", True, "metrics/metallb_bgp_session_down.json", None)
    assert sm["bgp_sessions_down"] == [{"node": "kind-worker", "peer": "10.0.0.2:179", "state": "down"}]
    s2 = snap(sub(tmp_path, "allup"), **kinds)
    prometheus(s2, [], {"frrk8s_bgp_session_up": 4})
    assert metallbctl.analyze(s2, INV)["summary"]["bgp_sessions_down"] == []
    s3 = snap(sub(tmp_path, "unscraped"), **kinds)
    prometheus(s3, [], {"metallb_bgp_session_up": 0})
    sm3 = metallbctl.analyze(s3, INV)["summary"]
    assert sm3["bgp_sessions_read"] is False and sm3["bgp_sessions_down"] is None and sm3["bgp_session_source"] is None


def test_peers_with_no_session_source_are_not_read(tmp_path):
    """FRR mode: the speaker prints no session gauge (it is the sidecar's), no BGPSessionState, no Prometheus. Not read, never 0 down."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    sm = metallbctl.analyze(snap(tmp_path, version="v0.15.3", step=step, metrics="metallb_k8s_client_config_loaded_bool 1\n", daemonsets=[with_env(workload("v0.15.3", ("monitoring", 7472)), "frr")], bgppeers__metallb__io=PEERS), INV)[
        "summary"
    ]
    assert (sm["bgp_backend"], sm["bgp_sessions_read"], sm["bgp_sessions_down"], sm["bgp_sessions"]) == ("frr", False, None, None)


def test_no_peers_is_nothing_to_judge(tmp_path):
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}}}
    sm = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=step, metrics="metallb_k8s_client_config_loaded_bool 1\n", daemonsets=[workload("v0.14.5", ("monitoring", 7472))]), INV)["summary"]
    assert (sm["bgp_peers"], sm["bgp_sessions_read"], sm["bgp_sessions_total"], sm["bgp_sessions_down"]) == (0, True, 0, [])


def test_an_empty_selector_reaches_every_pool(tmp_path):
    """metav1.LabelSelectorAsSelector of an empty selector is labels.Everything() (config.go:1335@v0.16.2)."""
    pools = [{"metadata": {"name": "a"}, "spec": {"addresses": ["172.18.255.200/32"]}}]
    s = snap(tmp_path, ipaddresspools__metallb__io=pools, l2advertisements__metallb__io=[{"metadata": {"name": "any"}, "spec": {"ipAddressPoolSelectors": [{}]}}])
    assert metallbctl._advertised_pools(s, pools) == {"a": ["L2Advertisement/any"]}


def test_a_bgp_advertised_service_is_not_read_from_the_status_objects_before_0_15(tmp_path):
    """0.14.6 to 0.14.9: ServiceL2Status is written, ServiceBGPStatus does not exist yet. Speakers unreadable, BGP mode: the empty L2 list is not "nobody announces" for a BGP-advertised Service (review of #162)."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": False, "node": "kind-worker", "error": "502"}}}
    kinds = {"l2advertisements__metallb__io": [], "bgpadvertisements__metallb__io": [{"metadata": {"name": "bgp"}, "spec": {}}], "bgppeers__metallb__io": PEERS, L2: []}
    out = metallbctl.analyze(snap(tmp_path, version="v0.14.9", step=step, daemonsets=[workload("v0.14.9", ("monitoring", 7472))], **kinds), INV)
    assert out["l2"]["available"] is True and rows(out)["web"] == ("lab", ["BGPAdvertisement/bgp"], [], False)
    newer = metallbctl.analyze(snap(sub(tmp_path, "15"), version="v0.15.0", step=step, daemonsets=[workload("v0.15.0", ("monitoring", 7472))], **{**kinds, BGP: []}), INV)
    assert rows(newer)["web"] == ("lab", ["BGPAdvertisement/bgp"], [], True)


def test_bgp_sessions_of_a_speaker_nobody_read_are_not_read(tmp_path):
    """Native mode, one speaker of two read and printing its session up: the other speaker's session was not read, so the metrics do not answer (review of #162)."""
    step = {"ok": True, "pods": {"speaker-a": {"ok": True, "node": "kind-worker"}, "speaker-b": {"ok": False, "node": "kind-control-plane", "error": "502"}}}
    prom = 'metallb_bgp_session_up{peer="10.0.0.1:179"} 1\nmetallb_k8s_client_config_loaded_bool 1\n'
    sm = metallbctl.analyze(snap(tmp_path, version="v0.14.5", step=step, metrics=prom, daemonsets=[workload("v0.14.5", ("monitoring", 7472))], bgppeers__metallb__io=PEERS), INV)["summary"]
    assert (sm["bgp_sessions_read"], sm["bgp_session_source"], sm["bgp_sessions_down"]) == (False, None, None)

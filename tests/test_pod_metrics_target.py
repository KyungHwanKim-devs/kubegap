"""Where a pod-metrics step reads (#136): the component's workload found at discovery, config.yaml, or the step's default, and the step saying which."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from lib import collect, podmetrics, shell
from lib.config import Config
from lib.runlog import RunLog


def _wl(kind, ns, name, labels, ports, image="x"):
    return {
        "metadata": {"namespace": ns, "name": name},
        "spec": {"selector": {"matchLabels": labels}, "template": {"metadata": {"labels": labels}, "spec": {"containers": [{"name": "c", "image": image, "ports": [{"name": n, "containerPort": p} for n, p in ports]}]}}},
    }


def _objs(*workloads):
    out = {"deployments": {"items": []}, "daemonsets": {"items": []}, "statefulsets": {"items": []}}
    for kind, wl in workloads:
        out[kind + "s"]["items"].append(wl)
    return out


def test_defaults_when_nothing_is_found_or_configured():
    t = podmetrics.discover_targets(_objs(), Config())
    assert len(t) == 11
    assert t["argocd.repo-server-metrics"] == {"namespace": "argocd", "selector": "app.kubernetes.io/name=argocd-repo-server", "port": 8084, "workload": None, "source": {"namespace": "default", "selector": "default", "port": "default"}}


def test_a_workload_in_another_namespace_with_another_release_name_is_found():
    """A release named argo-cd in namespace gitops: the chart renders argo-cd-argocd-repo-server with the chart's labels and the metrics container port."""
    labels = {"app.kubernetes.io/instance": "argo-cd", "app.kubernetes.io/name": "argocd-repo-server"}
    t = podmetrics.discover_targets(_objs(("deployment", _wl("deployment", "gitops", "argo-cd-argocd-repo-server", labels, [("server", 8081), ("metrics", 8084)]))), Config())["argocd.repo-server-metrics"]
    assert t["namespace"] == "gitops" and t["selector"] == "app.kubernetes.io/instance=argo-cd,app.kubernetes.io/name=argocd-repo-server" and t["port"] == 8084
    assert t["workload"] == "deployment gitops/argo-cd-argocd-repo-server" and t["source"] == {"namespace": "discovered", "selector": "discovered", "port": "discovered"}


def test_the_discovered_container_port_wins_over_the_default():
    """Karpenter 1.x listens on 8080 (pkg/operator/options/options.go:216@v1.15.1); the step's 8000 is the pre-1.0 default."""
    t = podmetrics.discover_targets(_objs(("deployment", _wl("deployment", "kube-system", "karpenter", {"app.kubernetes.io/name": "karpenter"}, [("http-metrics", 8080), ("webhook-metrics", 8001)]))), Config())[
        "karpenter.controller-metrics"
    ]
    assert t["port"] == 8080 and t["namespace"] == "kube-system" and t["source"]["port"] == "discovered"


def test_a_workload_without_a_named_metrics_port_keeps_the_default_port():
    t = podmetrics.discover_targets(_objs(("deployment", _wl("deployment", "cm", "cert-manager", {"app.kubernetes.io/name": "cert-manager", "app.kubernetes.io/component": "controller"}, []))), Config())["cert-manager.controller-metrics"]
    assert t["port"] == 9402 and t["source"] == {"namespace": "discovered", "selector": "discovered", "port": "default"}
    assert t["selector"] == "app.kubernetes.io/component=controller,app.kubernetes.io/name=cert-manager"


def test_a_sibling_workload_with_a_suffix_is_not_the_controller():
    """cert-manager-webhook and cert-manager-cainjector end with a suffix; the controller is the one named exactly <fullname>."""
    objs = _objs(
        ("deployment", _wl("deployment", "cm", "cert-manager-webhook", {"app.kubernetes.io/component": "webhook"}, [("https", 10250)])),
        ("deployment", _wl("deployment", "cm", "cert-manager", {"app.kubernetes.io/component": "controller"}, [("http-metrics", 9402)])),
    )
    t = podmetrics.discover_targets(objs, Config())["cert-manager.controller-metrics"]
    assert t["workload"] == "deployment cm/cert-manager" and t["selector"] == "app.kubernetes.io/component=controller"


def test_config_overrides_discovery_and_defaults_field_by_field():
    objs = _objs(("deployment", _wl("deployment", "gitops", "argocd-repo-server", {"app.kubernetes.io/name": "argocd-repo-server"}, [("metrics", 8084)])))
    cfg = Config({"components": {"argocd": {"metrics_port": 9999}, "grafana": {"namespace": "observability", "selector": "app=grafana"}}})
    t = podmetrics.discover_targets(objs, cfg)
    assert t["argocd.repo-server-metrics"]["port"] == 9999 and t["argocd.repo-server-metrics"]["source"] == {"namespace": "discovered", "selector": "discovered", "port": "config"}
    assert t["grafana.self-metrics"]["namespace"] == "observability" and t["grafana.self-metrics"]["selector"] == "app=grafana" and t["grafana.self-metrics"]["port"] == 3000
    assert t["grafana.self-metrics"]["source"] == {"namespace": "config", "selector": "config", "port": "default"}


def test_metallb_0_16_https_metrics_make_the_step_skip_with_the_reason():
    """MetalLB 0.16 names the port metricshttps and serves it with authentication (internal/k8s/k8s.go:159-163@v0.16.2): no false pass, no silent empty read."""
    sp = _wl("daemonset", "metallb-system", "speaker", {"app": "metallb", "component": "speaker"}, [("metricshttps", 9120), ("memberlist-tcp", 7946)])
    t = podmetrics.discover_targets(_objs(("daemonset", sp)), Config())["metallb.metallb-speaker-metrics"]
    assert t["port"] == 7472 and t["source"]["port"] == "default"
    assert t["skip"] == "daemonset metallb-system/speaker serves its metrics on port 9120 (metricshttps), over TLS with authentication, which the pod proxy and the node curl cannot read"
    # a plain-HTTP port named in config.yaml is read on purpose
    t2 = podmetrics.discover_targets(_objs(("daemonset", sp)), Config({"components": {"metallb": {"metrics_port": 7472}}}))["metallb.metallb-speaker-metrics"]
    assert "skip" not in t2 and t2["source"]["port"] == "config"


def test_an_old_inventory_without_targets_reads_the_step_defaults():
    step = next(s for f, s in podmetrics.pod_metrics_steps() if f == "argocd" and s["id"] == "server-metrics")
    assert podmetrics.default_target(step)["port"] == 8083


# ---------- the step uses the target and says where it read ----------


def _ctx(tmp_path, inv, state=None):
    return collect.StepContext("argocd", Path("collectors/argocd"), "ctx", Config(), inv, tmp_path, RunLog(None), None, None, None, None, None, state or collect.CollectState())


def _kubectl_recording(calls, pods, body="argocd_app_info 1\n"):
    def kubectl(args, **kw):
        calls.append(args)
        if args[:2] == ["get", "pods"]:
            return shell.Result(cmd=["kubectl"], code=0, stdout=json.dumps({"items": pods}))
        out = kw.get("out_path")
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(body)
        return shell.Result(cmd=["kubectl"], code=0, stdout=body)

    return kubectl


def test_the_step_lists_pods_and_proxies_where_discovery_said(tmp_path, monkeypatch):
    step = next(s for f, s in podmetrics.pod_metrics_steps() if f == "argocd" and s["id"] == "repo-server-metrics")
    tgt = {
        "namespace": "gitops",
        "selector": "app.kubernetes.io/name=argocd-repo-server",
        "port": 8085,
        "workload": "deployment gitops/argo-cd-argocd-repo-server",
        "source": {"namespace": "discovered", "selector": "discovered", "port": "discovered"},
    }
    calls: list = []
    monkeypatch.setattr(collect.kube, "kubectl", _kubectl_recording(calls, [{"metadata": {"name": "repo-1"}, "spec": {"nodeName": "n1"}, "status": {"phase": "Running", "podIP": "10.0.0.9"}}]))
    res = collect._step_pod_metrics(_ctx(tmp_path, {"pod_metrics_targets": {"argocd.repo-server-metrics": tgt}}), step)
    assert calls[0][:6] == ["get", "pods", "-n", "gitops", "-l", "app.kubernetes.io/name=argocd-repo-server"]
    assert calls[1][:3] == ["get", "--raw", "/api/v1/namespaces/gitops/pods/repo-1:8085/proxy/metrics"]
    assert res["ok"] is True and res["target"] == tgt and res["pods"]["repo-1"]["ok"]


def test_no_pod_behind_the_target_names_the_target_and_its_source(tmp_path, monkeypatch):
    step = next(s for f, s in podmetrics.pod_metrics_steps() if f == "argocd" and s["id"] == "repo-server-metrics")
    monkeypatch.setattr(collect.kube, "kubectl", _kubectl_recording([], []))
    res = collect._step_pod_metrics(_ctx(tmp_path, {}), step)  # an inventory from before #136: the defaults apply
    assert res["ok"] is False and res["target"]["source"] == {"namespace": "default", "selector": "default", "port": "default"}
    assert (
        res["error"]
        == "no pods match argocd / app.kubernetes.io/name=argocd-repo-server / port 8084 (namespace default, selector default, port default); set components.<name>.namespace/selector/metrics_port in config.yaml if the component lives elsewhere"
    )


def test_a_https_target_is_a_skip_not_a_failure(tmp_path, monkeypatch):
    step = next(s for f, s in podmetrics.pod_metrics_steps() if f == "metallb")
    tgt = {**podmetrics.default_target(step), "skip": "daemonset metallb-system/speaker serves its metrics on port 9120 (metricshttps), over TLS with authentication, which the pod proxy and the node curl cannot read"}
    calls: list = []
    monkeypatch.setattr(collect.kube, "kubectl", _kubectl_recording(calls, []))
    log = RunLog(tmp_path / "run.log")
    ctx = collect.StepContext("metallb", Path("collectors/metallb"), "ctx", Config(), {"pod_metrics_targets": {"metallb.metallb-speaker-metrics": tgt}}, tmp_path, log, None, None, None, None, None, collect.CollectState())
    res = collect._step_pod_metrics(ctx, step)
    assert res["skipped"] is True and res["ok"] is True and res["note"] == tgt["skip"] and calls == []
    assert "metricshttps" in (tmp_path / "run.log").read_text()


def test_the_node_fallback_sends_the_discovered_port(tmp_path, monkeypatch):
    step = next(s for f, s in podmetrics.pod_metrics_steps() if f == "argocd" and s["id"] == "repo-server-metrics")
    tgt = {**podmetrics.default_target(step), "port": 8085, "source": {"namespace": "default", "selector": "default", "port": "discovered"}}
    sent: list = []

    class NA:
        method = "ssm"
        nodes = ("n1",)

        def run_on_node(self, node, cmd, timeout=60, id=None, collector=None, *, step=None, params=None):
            sent.append((node, cmd, step, params))
            return SimpleNamespace(ok=True, stdout="argocd_git_request_total 1\n", error=None)

    monkeypatch.setattr(
        collect.kube,
        "kubectl",
        lambda args, **kw: (
            shell.Result(cmd=["kubectl"], code=0, stdout=json.dumps({"items": [{"metadata": {"name": "repo-1"}, "spec": {"nodeName": "n1"}, "status": {"phase": "Running", "podIP": "10.0.0.9"}}]}))
            if args[:2] == ["get", "pods"]
            else shell.Result(cmd=["kubectl"], code=None, timed_out=True, error="Client.Timeout exceeded")
        ),
    )
    inv = {"pod_metrics_targets": {"argocd.repo-server-metrics": tgt}, "nodes": {"nodes": [{"name": "n1"}]}}
    state = collect.CollectState()
    state.proxy_blocked.add("ctx")
    ctx = collect.StepContext("argocd", Path("collectors/argocd"), "ctx", Config(), inv, tmp_path, RunLog(None), None, None, None, SimpleNamespace(na=NA()), None, state)
    res = collect._step_pod_metrics(ctx, step)
    assert res["pods"]["repo-1"]["via"] == "node:n1"
    assert sent[0][2] == "argocd/repo-server-metrics" and sent[0][3] == {"podIp": "10.0.0.9", "port": 8085} and "http://10.0.0.9:8085/metrics" in sent[0][1]


def test_several_matching_workloads_prefer_the_default_namespace_and_are_listed():
    """`*/*grafana` matches both logging/loki-grafana and monitoring/grafana: the one in the step's default namespace wins and both are named (review of #136)."""
    objs = _objs(("deployment", _wl("deployment", "logging", "loki-grafana", {"app": "loki-grafana"}, [("grafana", 3000)])), ("deployment", _wl("deployment", "monitoring", "grafana", {"app": "grafana"}, [("grafana", 3000)])))
    t = podmetrics.discover_targets(objs, Config())["grafana.self-metrics"]
    assert t["workload"] == "deployment monitoring/grafana" and t["candidates"] == ["deployment logging/loki-grafana", "deployment monitoring/grafana"]
    # neither in the default namespace: the first by namespace and name, and the list says what else there was
    objs = _objs(("deployment", _wl("deployment", "obs", "grafana", {"app": "grafana"}, [])), ("deployment", _wl("deployment", "logging", "loki-grafana", {"app": "x"}, [])))
    t = podmetrics.discover_targets(objs, Config())["grafana.self-metrics"]
    assert t["workload"] == "deployment logging/loki-grafana" and len(t["candidates"]) == 2


def test_an_invalid_config_port_is_ignored_and_said_instead_of_aborting_discovery():
    t = podmetrics.discover_targets(_objs(), Config({"components": {"argocd": {"metrics_port": "abc"}, "keda": {"metrics_port": 70000}}}))
    assert t["argocd.repo-server-metrics"]["port"] == 8084 and t["argocd.repo-server-metrics"]["source"]["port"] == "default (config value 'abc' ignored: not a port)"
    assert t["keda.operator-metrics"]["port"] == 8080 and "ignored" in t["keda.operator-metrics"]["source"]["port"]


def test_metallb_before_0_16_is_read_on_its_monitoring_port():
    """The plain port is named monitoring through 0.15 (metallb-native.yaml:2110-2111@v0.15.3); with the 0.15 chart's kube-rbac-proxy both ports exist and the plain one is read."""
    sp = _wl("daemonset", "metallb-system", "speaker", {"app": "metallb", "component": "speaker"}, [("monitoring", 7472), ("memberlist-tcp", 7946)])
    t = podmetrics.discover_targets(_objs(("daemonset", sp)), Config())["metallb.metallb-speaker-metrics"]
    assert t["port"] == 7472 and t["source"]["port"] == "discovered" and "skip" not in t
    both = _wl("daemonset", "metallb-system", "lb-metallb-speaker", {"app.kubernetes.io/component": "speaker", "app.kubernetes.io/name": "metallb"}, [("monitoring", 7472), ("metricshttps", 9120)])
    t = podmetrics.discover_targets(_objs(("daemonset", both)), Config())["metallb.metallb-speaker-metrics"]
    assert t["port"] == 7472 and "skip" not in t and t["selector"] == "app.kubernetes.io/component=speaker,app.kubernetes.io/name=metallb"

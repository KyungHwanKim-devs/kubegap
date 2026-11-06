"""Which node command backends collection sends node steps to, and how discover handles config.yaml node_access: daemonset."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from lib import collect, discover
from lib.node import NodeResult
from lib.runlog import RunLog


class _FakeNA:
    def __init__(self, method):
        self.method, self.calls = method, []

    def run_on_node(self, node, cmd, timeout=60, id=None, collector=None, *, step=None, params=None):
        self.calls.append((node, cmd, step))
        return NodeResult(node, self.method, True, stdout="line1\nline2\n")

    def capabilities(self):
        return {}


def _runner(method):
    r = collect.NodeRunner({"node_access": {"method": method}, "nodes": {"nodes": [{"name": "n1", "roles": []}]}}, {}, RunLog(None))
    r.na = _FakeNA(method)
    return r


STEP = {"id": "os", "type": "node", "cmd": "uname -r", "out": "logs/node/{node}/os.txt", "nodes": "all"}


@pytest.mark.parametrize("method", ["ssh", "ssm", "daemonset"])
def test_node_step_runs_on_every_backend(tmp_path, method):
    runner = _runner(method)
    rec = collect._run_node_step(STEP, "os", "core", {}, {}, tmp_path, RunLog(None), runner, 30, None)
    assert rec["ok"] and rec["nodes"]["n1"]["ok"], rec
    assert runner.na.calls == [("n1", "uname -r", "core/os")]
    assert (tmp_path / "logs/node/n1/os.txt").read_text() == "line1\nline2\n"


def test_node_step_skipped_without_backend(tmp_path):
    runner = _runner("none")
    rec = collect._run_node_step(STEP, "os", "core", {}, {}, tmp_path, RunLog(None), runner, 30, None)
    assert rec == {"ok": False, "skipped": "no node command backend"}
    assert runner.na.calls == []
    assert collect._run_node_step(STEP, "os", "core", {}, {}, tmp_path, RunLog(None), None, 30, None)["skipped"]


@pytest.mark.parametrize("method,ok", [("ssh", True), ("ssm", True), ("daemonset", True), ("none", False)])
def test_pod_metrics_node_fallback_precondition(method, ok):
    def ctx(node_access):
        return collect.StepContext("core", Path("collectors/core"), None, {}, {}, Path("."), RunLog(None), None, None, {}, node_access, None, collect.CollectState())

    assert ctx(SimpleNamespace(na=SimpleNamespace(method=method))).node_backend_ok() is ok
    assert ctx(None).node_backend_ok() is False


def _pods(*nodes):
    return {"items": [{"spec": {"nodeName": n}, "status": {"phase": "Running"}} for n in nodes]}


def test_discover_forced_daemonset_without_pods(monkeypatch):
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: ({"items": []}, None))
    out = discover._node_access("k3s", {"nodes": []}, {"node_access": "daemonset"}, None, RunLog(None))
    assert out["method"] == "daemonset" and out["source"] == "config.yaml"
    assert out["daemonset_nodes"] == [] and "no kubegap-node-reader pod is Running" in out["reasons"][0]


def test_discover_forced_daemonset_with_pods(monkeypatch):
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: (_pods("a", "b"), None))
    out = discover._node_access("k3s", {"nodes": []}, {"node_access": "daemonset"}, None, RunLog(None))
    assert out["method"] == "daemonset" and out["daemonset_nodes"] == ["a", "b"]


def test_discover_detects_daemonset_pods_on_k3s(monkeypatch):
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: (_pods("a"), None))
    assert discover._node_access("k3s", {"nodes": []}, {}, None, RunLog(None))["method"] == "daemonset"
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: ({"items": []}, None))
    assert discover._node_access("k3s", {"nodes": []}, {}, None, RunLog(None))["method"] == "ssh"


def test_discover_eks_ignores_daemonset_pods_unless_forced(monkeypatch):
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: (_pods("a"), None))
    assert discover._node_access("eks", {"nodes": []}, {}, None, RunLog(None))["method"] == "ssm"
    out = discover._node_access("eks", {"nodes": []}, {"node_access": "daemonset"}, None, RunLog(None))
    assert out["method"] == "daemonset" and out["daemonset_nodes"] == ["a"]


def test_discover_other_forced_backend_skips_daemonset_detection(monkeypatch):
    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: (_pods("a"), None))
    for forced in ("ssh", "none"):
        out = discover._node_access("k3s", {"nodes": []}, {"node_access": forced}, None, RunLog(None))
        assert out["method"] == forced and "daemonset_nodes" not in out


def test_forced_daemonset_without_pods_fails_per_node(monkeypatch):
    from lib import node as node_mod

    monkeypatch.setattr(node_mod._kube, "kubectl_json", lambda *a, **k: ({"items": []}, None))
    na = node_mod.NodeAccess({"node_access": {"method": "daemonset", "daemonset_nodes": []}, "nodes": {"nodes": [{"name": "n1"}]}}, {"node_access": "daemonset"})
    r = na.run_on_node("n1", "true")
    assert not r.ok and r.backend == "daemonset" and "no Running kubegap-node-reader pod" in r.error


# ---------- the pod-metrics node fallback goes only to Running pods with a pod address (#93) ----------

PM_STEP = {"id": "speaker-metrics", "type": "pod-metrics", "namespace": "metallb", "selector": "app=speaker", "port": 7472, "out": "metrics/metallb", "timeout": 10}


def _pm_ctx(tmp_path, na, log=None, blocked=True):
    from lib.config import Config

    inv = {"nodes": {"nodes": [{"name": "n1"}, {"name": "n2"}]}}
    state = collect.CollectState()
    if blocked:
        state.proxy_blocked.add("ctx")
    return collect.StepContext("metallb", Path("collectors/metallb"), "ctx", Config(), inv, tmp_path, log or RunLog(None), None, None, None, SimpleNamespace(na=na), None, state)


def _pod(name, phase, ip, node="n1"):
    st = {"phase": phase}
    if ip is not None:
        st["podIP"] = ip
    return {"metadata": {"name": name}, "spec": {"nodeName": node}, "status": st}


def _fake_kubectl(pods):
    import json

    from lib import shell

    def kubectl(args, **kw):
        if args[:2] == ["get", "pods"]:
            return shell.Result(cmd=["kubectl"], code=0, stdout=json.dumps({"items": pods}))
        return shell.Result(cmd=["kubectl"], code=None, timed_out=True, error="Client.Timeout exceeded")

    return kubectl


def test_pod_metrics_fallback_curls_only_the_running_pod_with_a_pod_address(tmp_path, monkeypatch):
    pods = [_pod("ok", "Running", "10.0.0.5"), _pod("pending", "Pending", None), _pod("imds", "Running", "169.254.169.254"), _pod("v6", "Running", "fd00::5"), _pod("lo", "Running", "127.0.0.1")]
    monkeypatch.setattr(collect.kube, "kubectl", _fake_kubectl(pods))
    na = _FakeNA("ssh")
    log = RunLog(tmp_path / "run.log")
    res = collect._step_pod_metrics(_pm_ctx(tmp_path, na, log), PM_STEP)
    assert [c[0] for c in na.calls] == ["n1"] and "http://10.0.0.5:7472/metrics" in na.calls[0][1], na.calls
    assert res["ok"] is True and "skipped" not in res
    p = res["pods"]
    assert p["ok"]["ok"] and p["ok"]["via"] == "node:n1" and (tmp_path / "metrics/metallb/ok.prom").read_text() == "line1\nline2\n"
    assert p["pending"] == {"ok": False, "skipped": "pod not Running (Pending)", "via": None, "node": "n1", "out": None, "error": None}
    assert p["imds"]["ok"] is False and p["imds"]["skipped"] == "node fallback refused: link-local (podIP 169.254.169.254)"
    assert p["v6"]["skipped"] == "node fallback refused: IPv6 pod: node-side metrics fallback not supported (podIP fd00::5)"
    assert p["lo"]["skipped"] == "node fallback refused: loopback (podIP 127.0.0.1)"
    lines = (tmp_path / "run.log").read_text().splitlines()
    skips = [ln for ln in lines if '"kind": "skip"' in ln]
    assert len(skips) == 4 and any("metallb.speaker-metrics.pending" in ln and "pod not Running (Pending)" in ln for ln in skips), skips
    assert any("metallb.speaker-metrics.imds.node" in ln and "link-local" in ln for ln in skips)


def test_pod_metrics_step_reports_skipped_when_every_pod_was_skipped(tmp_path, monkeypatch):
    pods = [_pod("a", "Succeeded", "10.0.0.9"), _pod("b", "Running", "169.254.1.1")]
    monkeypatch.setattr(collect.kube, "kubectl", _fake_kubectl(pods))
    na = _FakeNA("ssm")
    res = collect._step_pod_metrics(_pm_ctx(tmp_path, na), PM_STEP)
    assert na.calls == [] and res["ok"] is False
    assert res["skipped"] == "a: pod not Running (Succeeded); b: node fallback refused: link-local (podIP 169.254.1.1)"


def test_pod_metrics_refusal_after_a_real_proxy_error_stays_a_failure(tmp_path, monkeypatch):
    """A 403 from the proxy is a real failure; the refused fallback is added to its error instead of turning the pod, and the step, into a skip."""
    import json

    from lib import shell

    def kubectl(args, **kw):
        if args[:2] == ["get", "pods"]:
            return shell.Result(cmd=["kubectl"], code=0, stdout=json.dumps({"items": [_pod("pub", "Running", "203.0.113.9"), _pod("noip", "Running", None)]}))
        return shell.Result(cmd=["kubectl"], code=1, stderr='Error from server (Forbidden): pods "x" is forbidden')

    monkeypatch.setattr(collect.kube, "kubectl", kubectl)
    na = _FakeNA("ssh")
    res = collect._step_pod_metrics(_pm_ctx(tmp_path, na, blocked=False), PM_STEP)
    assert na.calls == [] and res["ok"] is False and "skipped" not in res
    e = res["pods"]["pub"]
    assert "skipped" not in e and e["error"].startswith('Error from server (Forbidden): pods "x" is forbidden; node fallback refused: not in a pod address range')
    assert res["pods"]["noip"]["error"].endswith("; node fallback refused: no podIP")


def test_metallb_speaker_evidence_carries_the_skip_reason(tmp_path):
    """metallbctl._l2 lists unreadable speakers from the step's pod entries; a skipped pod has no error, so the skip reason is what the evidence shows."""
    import json

    from lib import metallbctl

    cr = {"metallb": {"steps": {"metallb-speaker-metrics": {"pods": {"speaker-a": {"ok": False, "node": "n1", "error": None, "skipped": "pod not Running (Pending)"}, "speaker-b": {"ok": True, "node": "n2"}}}}}}
    (tmp_path / "collect-result.json").write_text(json.dumps(cr))
    out = metallbctl._l2(tmp_path, [], ["n1", "n2"], {"speaker-b": "metallb_k8s_client_config_loaded_bool 1\n"}, metallbctl._step(tmp_path), False, False)
    assert out["speakers_unreadable"] == [{"pod": "speaker-a", "node": "n1", "error": "pod not Running (Pending)"}]

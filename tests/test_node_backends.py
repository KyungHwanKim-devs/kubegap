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

"""The kubeconfig a run was given reaches the external tool steps (#104)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from lib import collect, yamlite
from lib.runlog import RunLog

ROOT = Path(__file__).resolve().parent.parent


def _fake_tool(tmp_path, monkeypatch):
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    fake = bindir / "faketool"
    fake.write_text('#!/bin/sh\nprintf \'{"args": "%s", "kubeconfig": "%s"}\' "$*" "${KUBECONFIG-unset}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")


STEP = {"id": "audit", "type": "tool", "tool": "faketool", "cmd": ["faketool", "audit", "--context", "{context}"], "out": "tools/audit.json"}


def test_tool_gets_the_kubeconfig_as_environment(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch)
    monkeypatch.setenv("KUBECONFIG", "/session/kc")
    snap = tmp_path / "snap"
    res = collect._run_tool_step(STEP, "audit", "core", "ctx-x", "/x/kc", snap, RunLog(None), None, 30, None)
    assert res["ok"], res
    out = (snap / "tools" / "audit.json").read_text()
    assert '"kubeconfig": "/x/kc"' in out and '"args": "audit --context ctx-x"' in out


def test_without_a_kubeconfig_the_session_environment_is_left_alone(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch)
    monkeypatch.setenv("KUBECONFIG", "/session/a:/session/b")
    snap = tmp_path / "snap"
    res = collect._run_tool_step(STEP, "audit", "core", "ctx-x", None, snap, RunLog(None), None, 30, None)
    assert res["ok"], res
    assert '"kubeconfig": "/session/a:/session/b"' in (snap / "tools" / "audit.json").read_text()
    monkeypatch.delenv("KUBECONFIG")
    res = collect._run_tool_step(STEP, "audit", "core", "ctx-x", None, snap, RunLog(None), None, 30, None)
    assert '"kubeconfig": "unset"' in (snap / "tools" / "audit.json").read_text()


def test_per_item_tool_runs_get_it_too(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch)
    snap = tmp_path / "snap"
    (snap / "tools").mkdir(parents=True)
    (snap / "tools" / "list.json").write_text('[{"name": "r1"}, {"name": "r2"}]')
    step = {**STEP, "cmd": ["faketool", "get", "{item.name}"], "out": "tools/values/{item_safe}.json", "for_each_file": {"path": "tools/list.json", "key": ["name"]}}
    res = collect._run_tool_step(step, "audit", "core", "ctx-x", "/x/kc", snap, RunLog(None), None, 30, None)
    assert res["ok"] and res["runs"] == 2, res
    for n in ("r1", "r2"):
        assert '"kubeconfig": "/x/kc"' in (snap / "tools" / "values" / f"{n}.json").read_text()


def test_every_tool_step_names_the_context():
    """A tool step that forgot {context} would read the current context of the kubeconfig, not the one the run was asked for."""
    for f in sorted(ROOT.glob("collectors/*/collect.yaml")):
        for st in yamlite.load_file(f) or []:
            if isinstance(st, dict) and st.get("type") == "tool":
                assert "{context}" in " ".join(map(str, st["cmd"])), f"{f.parent.name}/{st['id']}"


def test_daemonset_backend_and_its_discovery_use_the_run_kubeconfig(monkeypatch):
    from lib import discover, shell
    from lib import node as node_mod

    calls = []

    def fake_json(args, **kw):
        calls.append((args[:2], kw.get("context"), kw.get("kubeconfig")))
        return {"items": [{"metadata": {"name": "p1"}, "spec": {"nodeName": "n1"}, "status": {"phase": "Running"}}]}, None

    def fake_kubectl(args, **kw):
        calls.append((args[:2], kw.get("context"), kw.get("kubeconfig")))
        return shell.Result(cmd=["kubectl"], code=0, stdout="ok\n")

    monkeypatch.setattr(node_mod._kube, "kubectl_json", fake_json)
    monkeypatch.setattr(node_mod._kube, "kubectl", fake_kubectl)
    na = node_mod.NodeAccess({"context": "ctx-x", "node_access": {"method": "daemonset", "daemonset_nodes": ["n1"]}, "nodes": {"nodes": [{"name": "n1"}]}}, {"node_access": "daemonset"}, kubeconfig="/x/kc")
    assert na.run_on_node("n1", "true").ok
    assert calls == [(["get", "pods"], "ctx-x", "/x/kc"), (["exec", "-n"], "ctx-x", "/x/kc")]
    calls.clear()
    monkeypatch.setattr(discover.kube, "kubectl_json", fake_json)
    out = discover._node_access("k3s", {"nodes": []}, {}, None, RunLog(None), context="ctx-x", kubeconfig="/x/kc")
    assert out["method"] == "daemonset" and calls == [(["get", "pods"], "ctx-x", "/x/kc")]

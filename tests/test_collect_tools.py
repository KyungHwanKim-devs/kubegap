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
    """A tool step that forgot {context} would read the current context of the kubeconfig, not the one the run was asked for. A step fed on stdin contacts no cluster."""
    for f in sorted(ROOT.glob("collectors/*/collect.yaml")):
        for st in yamlite.load_file(f) or []:
            if isinstance(st, dict) and st.get("type") == "tool":
                names_context = "{context}" in " ".join(map(str, st["cmd"]))
                assert names_context != bool(st.get("stdin")), f"{f.parent.name}/{st['id']}"


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


def test_krr_config_block_is_dropped_from_the_saved_file(tmp_path, monkeypatch):
    """krr's JSON carries its whole Config (robusta_krr/core/models/result.py:70@v1.31.1), kubeconfig path and EKS access key included (core/models/config.py:27, 47); kubegap reads none of it."""
    import json

    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    fake = bindir / "krr"
    doc = {
        "scans": [],
        "score": 0,
        "strategy": {"name": "simple", "settings": {"history_duration": 336.0}},
        "errors": [],
        "clusterSummary": {},
        "config": {"kubeconfig": "/home/me/.kube/config", "eks_access_key": "AKIAEXAMPLEEXAMPLE00", "prometheus_url": "http://127.0.0.1:9090"},
    }
    fake.write_text('#!/bin/sh\nfor a in "$@"; do out="$a"; done\nprintf \'%s\' \'' + json.dumps(doc).replace("'", "'\\''") + '\' > "$out"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    step = {"id": "krr", "type": "tool", "tool": "krr", "cmd": ["krr", "simple", "-c", "{context}", "-f", "json", "--fileoutput", "{out}"], "writes_out": True, "out": "tools/krr.json"}
    snap = tmp_path / "snap"
    res = collect._run_tool_step(step, "krr", "core", "ctx", None, snap, RunLog(None), None, 30, None)
    assert res["ok"], res
    saved = json.loads((snap / "tools" / "krr.json").read_text())
    assert "config" not in saved and saved["strategy"]["settings"]["history_duration"] == 336.0
    assert "AKIAEXAMPLE" not in (snap / "tools" / "krr.json").read_text()
    assert stat.S_IMODE((snap / "tools" / "krr.json").stat().st_mode) == 0o600


def test_deprecation_tools_are_skipped_without_a_server_version(tmp_path, monkeypatch):
    """No made-up target: pluto flags every API against the target and kubent lists every rule set whose Since is below it (pkg/printer/filter.go:12@0.7.3)."""
    _fake_tool(tmp_path, monkeypatch)
    step = {"id": "pluto", "type": "tool", "tool": "faketool", "cmd": ["faketool", "--target-versions", "k8s={k8s_next_minor}"], "out": "tools/pluto.json"}
    snap = tmp_path / "snap"
    res = collect._run_tool_step(step, "pluto", "core", "ctx", None, snap, RunLog(None), None, 30, None, inv={"cluster": {"server_version": None}})
    assert res["ok"] is False and res["skipped"].startswith("server version unknown") and not (snap / "tools" / "pluto.json").exists()
    res = collect._run_tool_step(step, "pluto", "core", "ctx", None, snap, RunLog(None), None, 30, None, inv={"cluster": {"server_version": "v1.32.13-eks-abc"}})
    assert res["ok"] and '"args": "--target-versions k8s=v1.33.0"' in (snap / "tools" / "pluto.json").read_text()


def _api_resources(tmp_path, monkeypatch, stdout, ok):
    class R:
        pass

    r = R()
    r.ok, r.stdout, r.stderr, r.error = ok, stdout, "unable to retrieve the complete list of server APIs: metrics.k8s.io/v1beta1: the server is currently unable to handle the request", None
    monkeypatch.setattr(collect.kube, "kubectl", lambda *a, **k: r)
    return collect.list_api_resources("ctx", None, RunLog(None))


TABLE = "NAME          SHORTNAMES   APIVERSION   NAMESPACED   KIND         VERBS\ndeployments   deploy       apps/v1      true         Deployment   get,list\n"


def test_a_partial_discovery_still_reads_what_kubectl_printed(tmp_path, monkeypatch):
    """kubectl api-resources prints what it found and exits non-zero when one aggregated API is down (staging/src/k8s.io/kubectl/pkg/cmd/apiresources/apiresources.go:180-182,251@v1.37.2). `[]` lost the whole dump, and now pluto with it."""
    assert [r["full"] for r in _api_resources(tmp_path, monkeypatch, TABLE, False)] == ["deployments.apps"]
    assert _api_resources(tmp_path, monkeypatch, "", False) == []


def test_a_crd_with_the_plural_of_a_discovery_kind_is_fetched(tmp_path, monkeypatch):
    """`name in done` also matched services.serving.knative.dev, so a Knative Service was never saved and pluto could not see it."""
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "services.json").write_text('{"items": []}')
    res = [
        {"name": "services", "full": "services", "namespaced": True, "kind": "Service", "apiversion": "v1"},
        {"name": "services", "full": "services.serving.knative.dev", "namespaced": True, "kind": "Service", "apiversion": "serving.knative.dev/v1"},
    ]
    monkeypatch.setattr(collect, "list_api_resources", lambda *a: res)
    asked = []

    def fake_json(args, **k):
        asked.append(args[1])
        return {"items": []}, None

    monkeypatch.setattr(collect.kube, "kubectl_json", fake_json)
    out = collect.dump_all("ctx", None, tmp_path, [], 10, RunLog(None), "core")
    assert out["skipped"] == ["services"] and asked == ["services.serving.knative.dev"] and (tmp_path / "objects" / "services.serving.knative.dev.json").is_file()

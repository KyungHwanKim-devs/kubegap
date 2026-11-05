"""pluto judges the last-applied apiVersion of what kubegap saved, so it never reaches the cluster and cannot read a Secret (#154)."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path

from lib import collect, hygiene, lastapplied, scrub, yamlite
from lib.runlog import RunLog

ROOT = Path(__file__).resolve().parent.parent
ANN = "kubectl.kubernetes.io/last-applied-configuration"
INV = {"cluster": {"server_version": "v1.32.0"}}
SAVED = {"kinds": 3, "skipped": ["pods"], "failed": {}, "not_permitted": []}


def obj(kind, name, namespace="prod-a", applied=None, **extra):
    meta = {"name": name, "annotations": {ANN: json.dumps(applied) if isinstance(applied, dict) else applied}}
    if namespace:
        meta["namespace"] = namespace
    return {"apiVersion": "v1", "kind": kind, "metadata": meta, **extra}


def save(snap, stem, *items):
    (snap / "objects").mkdir(exist_ok=True)
    (snap / "objects" / f"{stem}.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": list(items)}))


def test_each_entry_holds_only_what_pluto_reads(tmp_path):
    """The Stub of pkg/api/versions.go:46-57@v5.24.5: kind, apiVersion, metadata.name, metadata.namespace. spec and labels of the applied manifest stay out."""
    applied = {"apiVersion": "apps/v1beta2", "kind": "Deployment", "metadata": {"name": "web", "labels": {"a": "b"}}, "spec": {"template": {"spec": {"containers": [{"env": [{"name": "PASSWORD", "value": "hunter2"}]}]}}}}
    save(tmp_path, "deployments", obj("Deployment", "web", applied=applied))
    assert lastapplied.stubs(tmp_path) == [{"apiVersion": "apps/v1beta2", "kind": "Deployment", "metadata": {"name": "web", "namespace": "prod-a"}}]
    assert "hunter2" not in lastapplied.pluto_input(tmp_path)[0]


def test_name_and_namespace_come_from_the_object_not_the_manifest(tmp_path):
    """`kubectl apply -n` and generateName leave them out of the manifest; a cluster-scoped object has no namespace key at all (pluto's Output omits it too)."""
    save(tmp_path, "deployments", obj("Deployment", "web", applied={"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"generateName": "web-"}}))
    save(tmp_path, "storageclasses", obj("StorageClass", "fast", namespace=None, applied={"apiVersion": "storage.k8s.io/v1", "kind": "StorageClass", "metadata": {"name": "fast"}}))
    assert [s["metadata"] for s in lastapplied.stubs(tmp_path)] == [{"name": "web", "namespace": "prod-a"}, {"name": "fast"}]


def test_objects_pluto_would_skip_are_skipped(tmp_path):
    good = {"apiVersion": "apps/v1", "kind": "StatefulSet", "metadata": {"name": "db"}}
    bare = {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "plain"}}  # applied by Helm or server-side apply: no annotation
    save(tmp_path, "controllerrevisions.apps", obj("ControllerRevision", "db-7f", applied=good))  # discovery_api.go:148@v5.24.5: the annotation is its StatefulSet's
    save(tmp_path, "ingresses.networking.k8s.io", obj("Ingress", "broken", applied="{not json"), obj("Ingress", "list", applied="[]"))
    save(tmp_path, "services", bare)
    assert lastapplied.stubs(tmp_path) == []


def test_a_scrubbed_configmap_is_skipped_and_nothing_of_it_is_read(tmp_path):
    """lib/scrub.py replaces the annotation of a ConfigMap by {len, shape} before the file is written; pluto has no rule for ConfigMap or Secret (versions.yaml@v5.24.5)."""
    cm = obj("ConfigMap", "app", applied={"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "app"}, "data": {"a": "b"}}, data={"a": "b"})
    doc = {"items": [cm]}
    assert scrub.scrub_or_error(doc) is None and not isinstance(cm["metadata"]["annotations"][ANN], str)
    save(tmp_path, "configmaps", cm)
    assert lastapplied.stubs(tmp_path) == []


def test_empty_snapshot_is_a_valid_empty_list(tmp_path):
    (tmp_path / "objects").mkdir()
    text, n = lastapplied.pluto_input(tmp_path)
    assert n == 0 and json.loads(text) == {"apiVersion": "v1", "kind": "List", "items": []}


def _step():
    return next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == "pluto")


def _fake_pluto(tmp_path, monkeypatch, body):
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    fake = bindir / "pluto"
    fake.write_text("#!/bin/sh\n" + body)
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")


def test_step_feeds_the_saved_objects_and_counts_what_the_dump_saw(tmp_path, monkeypatch):
    stdin_file = tmp_path / "stdin.json"
    _fake_pluto(tmp_path, monkeypatch, f'cat > {shlex.quote(str(stdin_file))}\nprintf \'%s\\n\' \'{{"target-versions": {{"k8s": "v1.33.0"}}}}\'\n')
    save(tmp_path, "deployments", obj("Deployment", "web", applied={"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "web"}}))
    dump = {"kinds": 110, "skipped": ["pods"], "failed": {"foos.example.com": "boom"}, "not_permitted": ["csrs.certificates.k8s.io"]}
    res = collect._run_tool_step(_step(), "pluto", "core", "ctx", None, tmp_path, RunLog(None), None, 10, None, inv=INV, objects_dump=dump)
    assert res["ok"] is True and res["api_read"] is True
    assert (res["lists_ok"], res["lists_failed"], res["manifests"]) == (111, 2, 1)
    assert [i["metadata"]["name"] for i in json.loads(stdin_file.read_text())["items"]] == ["web"]


def test_a_failed_dump_never_reads_as_a_clean_cluster(tmp_path, monkeypatch):
    """Without this guard an empty List goes in, `{"target-versions": ...}` comes out with exit 0, and hygiene.deprecated-api passes on nothing."""
    ran = tmp_path / "ran"
    _fake_pluto(tmp_path, monkeypatch, f"touch {shlex.quote(str(ran))}\nprintf '%s\\n' '{{}}'\n")
    (tmp_path / "objects").mkdir()
    for dump in (None, {"kinds": 0, "skipped": [], "failed": {"x": "y"}, "not_permitted": []}):
        res = collect._run_tool_step(_step(), "pluto", "core", "ctx", None, tmp_path, RunLog(None), None, 10, None, inv=INV, objects_dump=dump)
        assert res["ok"] is False and res["api_read"] is False and "objects.dump-all saved no kind" in res["error"]
    assert not ran.exists()
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": {"pluto": res}}}))
    summary = hygiene._deprecated(hygiene._Ctx(tmp_path, {}))
    assert summary["pluto_read"] is False and summary["items"] is None


def test_a_cluster_with_no_annotation_is_read_with_zero_manifests(tmp_path, monkeypatch):
    """A cluster managed by Helm or server-side apply: the dump saved kinds, nothing carries the annotation, and the answer is an honest clean result, not a failure."""
    _fake_pluto(tmp_path, monkeypatch, 'cat > /dev/null\nprintf \'%s\\n\' \'{"target-versions": {"k8s": "v1.33.0"}}\'\n')
    save(tmp_path, "services", obj("Service", "plain", applied=None))
    res = collect._run_tool_step(_step(), "pluto", "core", "ctx", None, tmp_path, RunLog(None), None, 10, None, inv=INV, objects_dump=SAVED)
    assert res["ok"] is True and res["api_read"] is True and res["manifests"] == 0


def test_the_pluto_step_runs_after_the_dump_it_reads():
    ids = [s["id"] for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml")]
    assert ids.index("objects.dump-all") < ids.index("pluto")


def test_dump_result_reaches_the_tool_step(tmp_path, monkeypatch):
    """collect.yaml steps share nothing but StepContext.state: the pluto handler must see what the dump handler returned in the same run."""
    seen = {}
    monkeypatch.setattr(collect, "dump_all", lambda *a, **k: SAVED)
    monkeypatch.setattr(collect, "_run_tool_step", lambda *a, **k: seen.update(k) or {"ok": True})
    state = collect.CollectState()
    ctx = collect.StepContext("core", tmp_path, "ctx", None, {}, tmp_path, RunLog(None), None, None, None, None, None, state)
    collect.STEP_HANDLERS["kubectl-dump-all"](ctx, {"id": "objects.dump-all"})
    collect.STEP_HANDLERS["tool"](ctx, _step())
    assert seen["objects_dump"] is SAVED


def test_the_exclude_list_is_the_one_the_pluto_comparison_was_made_against():
    """Every kind excluded from the dump is out of pluto's sight too. references/sources.md compares this list with versions.yaml@v5.24.5; a new entry, or a pluto upgrade, needs that comparison again."""
    dump = next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == "objects.dump-all")
    assert set(dump["exclude"]) == {
        "secrets",
        "events",
        "events.events.k8s.io",
        "componentstatuses",
        "bindings",
        "localsubjectaccessreviews.authorization.k8s.io",
        "selfsubjectaccessreviews.authorization.k8s.io",
        "selfsubjectrulesreviews.authorization.k8s.io",
        "subjectaccessreviews.authorization.k8s.io",
        "tokenreviews.authentication.k8s.io",
        "selfsubjectreviews.authentication.k8s.io",
        "pods.metrics.k8s.io",
        "nodes.metrics.k8s.io",
        "packagerevisions.*",
    }

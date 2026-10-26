"""lib/diff.py: compare two tiny hand-built snapshot folders and check the shape and values of diff.json."""

import json

import pytest

from lib import diff as diffmod


def deployment(ns, name, replicas, generation=1):
    return {"kind": "Deployment", "apiVersion": "apps/v1", "metadata": {"namespace": ns, "name": name, "generation": generation}, "spec": {"replicas": replicas, "template": {"spec": {"containers": [{"name": "c", "image": "img:1"}]}}}}


def finding(check, target, status="fail", sev="high"):
    return {"id": f"{check}.{target}", "check": check, "status": status, "severity_default": sev, "target": target, "evidence": {"v": 1}}


def write_snapshot(folder, deployments, pods, findings, taken_at, nodes=("n1",)):
    (folder / "objects").mkdir(parents=True)
    (folder / "objects" / "deployments.apps.json").write_text(json.dumps({"items": deployments}))
    (folder / "objects" / "pods.json").write_text(json.dumps({"items": pods}))
    (folder / "findings-draft.json").write_text(json.dumps({"rubric_version": "0.1.0", "profile": {"name": "prod"}, "findings": findings}))
    inv = {
        "taken_at": taken_at,
        "cluster": {"server_version": "v1.31.0-eks-abc"},
        "profile": {"name": "prod"},
        "nodes": {"count": len(nodes), "nodes": [{"name": n} for n in nodes], "kubelet_versions": ["v1.31.0"]},
        "namespaces": {"names": ["default", "kube-system"]},
        "components_present": ["coredns"],
    }
    (folder / "inventory.json").write_text(json.dumps(inv))


@pytest.fixture
def snapshots(tmp_path):
    ctx = tmp_path / "ctx"
    a, b = ctx / "2026-01-01T00-00-00", ctx / "2026-01-02T00-00-00"
    pod = {"kind": "Pod", "metadata": {"namespace": "default", "name": "p1"}}
    write_snapshot(
        a,
        deployments=[deployment("default", "keep", 2), deployment("default", "gone", 1), deployment("default", "scaled", 1, generation=3)],
        pods=[pod],
        findings=[finding("resilience.no-pdb", "default/keep"), finding("resilience.no-pdb", "default/gone"), finding("hygiene.x", "default/flip", status="warn", sev="low")],
        taken_at="2026-01-01T00:00:00+00:00",
    )
    write_snapshot(
        b,
        deployments=[deployment("default", "keep", 2), deployment("default", "scaled", 3, generation=4), deployment("prod", "new", 1)],
        pods=[pod, {"kind": "Pod", "metadata": {"namespace": "default", "name": "p2"}}],
        findings=[finding("resilience.no-pdb", "default/keep"), finding("resilience.no-pdb", "prod/new"), finding("hygiene.x", "default/flip", status="fail", sev="low")],
        taken_at="2026-01-02T00:00:00+00:00",
        nodes=("n1", "n2"),
    )
    return a, b


def test_diff_objects(snapshots):
    a, b = snapshots
    out = diffmod.diff_objects(a, b)
    assert out["kinds_compared"] == 1  # pods are count-only
    assert out["added"] == [{"kind": "deployments.apps", "name": "prod/new"}]
    assert out["removed"] == [{"kind": "deployments.apps", "name": "default/gone"}]
    assert len(out["changed"]) == 1
    ch = out["changed"][0]
    assert ch["kind"] == "deployments.apps" and ch["name"] == "default/scaled"
    assert ch["generation"] == [3, 4]
    assert ch["changed_fields"] == ["spec.replicas"]
    assert out["count_only"] == {"pods": {"before": 1, "after": 2, "delta": 1}}
    assert out["summary"] == {"added": 1, "removed": 1, "changed": 1}
    assert out["kinds_only_in_a"] == [] and out["kinds_only_in_b"] == []


def test_diff_findings(snapshots):
    a, b = snapshots
    out = diffmod.diff_findings(a, b)
    assert [f["id"] for f in out["new"]] == ["resilience.no-pdb.prod/new"]
    assert out["new"][0]["evidence"] == {"v": 1}
    assert [f["id"] for f in out["resolved"]] == ["resilience.no-pdb.default/gone"]
    assert out["changed"] == [{"id": "hygiene.x.default/flip", "status": ["warn", "fail"], "severity_default": ["low", "low"]}]
    assert out["summary"] == {"new": 1, "resolved": 1, "changed": 1}
    assert out["counts_before"] == {"fail": {"high": 2}, "warn": {"low": 1}}
    assert out["counts_after"] == {"fail": {"high": 2, "low": 1}, "warn": {}}
    assert out["profile"] == ["prod", "prod"] and out["rubric_version"] == ["0.1.0", "0.1.0"]
    # default/gone disappeared and prod/new appeared for the same check, but in different namespaces: not a rename suspect
    assert out["rename_suspects"] == []


def test_diff_findings_rename_suspect_same_namespace(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_snapshot(a, [], [], [finding("c.k", "ns/old")], "t")
    write_snapshot(b, [], [], [finding("c.k", "ns/new")], "t")
    out = diffmod.diff_findings(a, b)
    assert out["rename_suspects"] == [{"resolved": "c.k.ns/old", "new_candidates": ["c.k.ns/new"]}]


def test_diff_findings_missing_side(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_snapshot(a, [], [], [], "t")
    b.mkdir()
    out = diffmod.diff_findings(a, b)
    assert "missing" in out and out["a"] is True and out["b"] is False


def test_persisted_findings_counts_consecutive_runs(snapshots):
    _a, b = snapshots
    out = diffmod.persisted_findings(b)
    assert out["runs_checked"] == 2
    runs = {r["id"]: r["runs"] for r in out["rows"]}
    assert runs == {"resilience.no-pdb.default/keep": 2, "hygiene.x.default/flip": 2, "resilience.no-pdb.prod/new": 1}
    assert out["max_runs"] == 2 and out["persisted_3plus"] == 0


def test_diff_inventory(snapshots):
    a, b = snapshots
    out = diffmod.diff_inventory(a, b)
    assert out["node_count"] == [1, 2]
    assert out["nodes_added"] == ["n2"] and out["nodes_removed"] == []
    assert out["taken_at"] == ["2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"]
    assert out["components_added"] == [] and out["namespaces_added"] == []
    assert out["stores_changed"] == {} and out["eks_changed"] == {}


def test_diff_writes_diff_json_with_top_level_shape(snapshots):
    a, b = snapshots
    d = diffmod.diff(a, b, write=True)
    assert set(d) >= {"kubegap", "generated_at", "a", "b", "a_name", "b_name", "inventory", "objects", "findings", "events", "metrics"}
    assert d["a_name"] == a.name and d["b_name"] == b.name
    assert d["findings"]["persisted"]["runs_checked"] == 2
    assert d["events"]["changed"] == [] and d["metrics"] == {}  # no summary.json / metrics folder in the fixture
    on_disk = json.loads((b / "diff.json").read_text())
    assert on_disk["objects"]["summary"] == {"added": 1, "removed": 1, "changed": 1}


def test_print_summary_runs_on_fixture(snapshots):
    a, b = snapshots
    lines = []
    diffmod.print_summary(diffmod.diff(a, b, write=False), echo=lines.append)
    text = "\n".join(lines)
    assert "added 1, removed 1, changed 1" in text
    assert "resolved [fail/high] resilience.no-pdb.default/gone" in text


def test_append_history_writes_and_replaces_row(snapshots):
    _a, b = snapshots
    path = diffmod.append_history(b)
    assert path == b.parent / "history.csv"
    first = path.read_text().splitlines()
    assert first[0].split(",") == diffmod.HISTORY_COLUMNS
    assert len(first) == 2
    diffmod.append_history(b)  # same snapshot again: the row is replaced, not appended
    assert len(path.read_text().splitlines()) == 2
    row = dict(zip(diffmod.HISTORY_COLUMNS, first[1].split(","), strict=True))
    assert row["snapshot"] == b.name and row["high"] == "2" and row["low"] == "1" and row["warn"] == "0" and row["nodes"] == "2"

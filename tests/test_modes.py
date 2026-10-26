"""Collection modes: step filtering, snapshot mode marker, same-mode latest/previous selection, check tagging."""

from __future__ import annotations

import json

from lib import collect, paths, rubric


def test_step_in_mode_defaults_to_every_mode():
    assert collect.step_in_mode({"id": "x", "type": "kubectl"}, "daily")
    assert collect.step_in_mode({"id": "x", "type": "kubectl"}, "full")


def test_step_marked_full_is_skipped_by_daily():
    st = {"id": "krr", "type": "tool", "modes": ["full"]}
    assert not collect.step_in_mode(st, "daily")
    assert collect.step_in_mode(st, "full")


def test_snapshot_mode_defaults_to_full_without_marker(tmp_path):
    assert paths.snapshot_mode(tmp_path) == "full"
    (tmp_path / "MODE").write_text("daily\n")
    assert paths.snapshot_mode(tmp_path) == "daily"
    (tmp_path / "MODE").write_text("weird\n")
    assert paths.snapshot_mode(tmp_path) == "full"


def _snap(root, name, mode):
    d = root / name
    d.mkdir()
    (d / "inventory.json").write_text(json.dumps({"context": "c"}))
    (d / "MODE").write_text(mode + "\n")
    return d


def test_previous_snapshot_stays_within_mode(tmp_path):
    ctx = tmp_path / "c"
    ctx.mkdir()
    d1 = _snap(ctx, "2026-10-20T00-00-00", "daily")
    f1 = _snap(ctx, "2026-10-21T00-00-00", "full")
    d2 = _snap(ctx, "2026-10-22T00-00-00", "daily")
    f2 = _snap(ctx, "2026-10-23T00-00-00", "full")
    assert paths.previous_snapshot(d2) == d1
    assert paths.previous_snapshot(f2) == f1
    assert paths.previous_snapshot(d1) is None  # first daily run: nothing to compare with


def test_latest_snapshot_by_mode(tmp_path):
    ctx = tmp_path / "c"
    ctx.mkdir()
    d1 = _snap(ctx, "2026-10-20T00-00-00", "daily")
    f1 = _snap(ctx, "2026-10-21T00-00-00", "full")
    assert paths.latest_snapshot("c", tmp_path) == f1
    assert paths.latest_snapshot("c", tmp_path, mode="daily") == d1
    assert paths.resolve_snapshot("latest", "c", tmp_path, mode="daily") == d1
    assert paths.resolve_snapshot("latest", "c", tmp_path) == f1


def test_validate_modes_field():
    base = {"id": "a.b", "name": "n", "area": "a", "type": "summary", "severity_default": "low", "rule": {"expr": "True"}, "profiles": ["eks"], "test": {"cases": []}}
    assert not [e for e in rubric.validate({**base, "modes": ["full"]}, "t") if "modes" in e]
    assert [e for e in rubric.validate({**base, "modes": ["weekly"]}, "t") if "modes" in e]
    assert [e for e in rubric.validate({**base, "modes": []}, "t") if "modes" in e]


def test_tenancy_pools_accept_string_taints(tmp_path):
    """Regression: discover writes node taints as `key=value:effect` strings; tenancy used to call .get() on them and the whole section died on the first tainted node."""
    from lib import tenancy

    (tmp_path / "objects").mkdir()
    inv = {
        "nodes": {"nodes": [{"name": "n1", "nodegroup": "build", "taints": ["workload-type=build:NoSchedule", "node.kubernetes.io/unschedulable:NoSchedule"]}, {"name": "n2", "taints": [{"key": "k", "value": "v", "effect": "NoExecute"}]}]}
    }
    node_pool, pools = tenancy._pools(inv, tmp_path)
    assert node_pool == {"n1": "build", "n2": "(no-pool)"}
    assert pools["build"]["taints"] == [{"key": "workload-type", "value": "build", "effect": "NoSchedule"}]  # the node.kubernetes.io/ taint is a node-lifecycle taint, not a pool taint
    assert pools["(no-pool)"]["taints"] == [{"key": "k", "value": "v", "effect": "NoExecute"}]

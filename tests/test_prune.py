"""Snapshot retention: per-mode counts, the latest of each mode always kept, incomplete and in-progress folders, retention resolution."""

from __future__ import annotations

import json
import os
import time

import pytest

from lib import prune


def _snap(ctx, name, mode, complete=True):
    d = ctx / name
    d.mkdir()
    (d / "MODE").write_text(mode + "\n")
    if complete:
        (d / "inventory.json").write_text(json.dumps({"context": "c"}))
    else:
        (d / "INCOMPLETE").write_text("x")
    (d / "objects").mkdir()
    (d / "objects" / "pods.json").write_text("{}" * 100)
    return d


def _names(ps):
    return [p.name for p in ps]


def test_keeps_newest_n_per_mode(tmp_path):
    for day in range(1, 6):
        _snap(tmp_path, f"2026-10-0{day}T00-00-00", "daily")
    for day in range(6, 9):
        _snap(tmp_path, f"2026-10-0{day}T00-00-00", "full")
    p = prune.plan(tmp_path, keep_daily=2, keep_full=1)
    assert _names(p.remove) == ["2026-10-01T00-00-00", "2026-10-02T00-00-00", "2026-10-03T00-00-00", "2026-10-06T00-00-00", "2026-10-07T00-00-00"]
    assert _names(p.keep) == ["2026-10-04T00-00-00", "2026-10-05T00-00-00", "2026-10-08T00-00-00"]


def test_zero_still_keeps_latest_of_each_mode(tmp_path):
    _snap(tmp_path, "2026-10-01T00-00-00", "full")
    _snap(tmp_path, "2026-10-02T00-00-00", "daily")
    _snap(tmp_path, "2026-10-03T00-00-00", "daily")
    p = prune.plan(tmp_path, keep_daily=0, keep_full=0)
    assert _names(p.keep) == ["2026-10-01T00-00-00", "2026-10-03T00-00-00"]  # the only full is old but it is the full baseline
    assert _names(p.remove) == ["2026-10-02T00-00-00"]


def test_mode_without_retention_is_untouched(tmp_path):
    for day in range(1, 4):
        _snap(tmp_path, f"2026-10-0{day}T00-00-00", "full")
    _snap(tmp_path, "2026-10-04T00-00-00", "daily")
    _snap(tmp_path, "2026-10-05T00-00-00", "daily")
    p = prune.plan(tmp_path, keep_daily=1, keep_full=None)
    assert _names(p.remove) == ["2026-10-04T00-00-00"]


def test_incomplete_removed_unless_in_progress(tmp_path):
    _snap(tmp_path, "2026-10-01T00-00-00", "daily")
    old = _snap(tmp_path, "2026-10-02T00-00-00", "daily", complete=False)
    live = _snap(tmp_path, "2026-10-03T00-00-00", "daily", complete=False)
    now = time.time()
    (old / "run.log").write_text("x")
    os.utime(old / "run.log", (now - 3600, now - 3600))
    (live / "run.log").write_text("x")
    p = prune.plan(tmp_path, keep_daily=5, keep_full=5, now=now)
    assert _names(p.remove) == ["2026-10-02T00-00-00"]
    assert "2026-10-03T00-00-00" in _names(p.keep)
    assert "2026-10-01T00-00-00" in _names(p.keep)  # an incomplete newer folder does not take the baseline slot


def test_apply_deletes_only_snapshot_folders(tmp_path):
    _snap(tmp_path, "2026-10-01T00-00-00", "daily")
    _snap(tmp_path, "2026-10-02T00-00-00", "daily")
    (tmp_path / "history.csv").write_text("a,b\n")
    (tmp_path / "setup.json").write_text("{}")
    (tmp_path / "notes").mkdir()
    p = prune.plan(tmp_path, keep_daily=1, keep_full=1)
    freed = prune.apply(p)
    assert freed > 0
    assert sorted(x.name for x in tmp_path.iterdir()) == ["2026-10-02T00-00-00", "history.csv", "notes", "setup.json"]


def test_missing_context_dir(tmp_path):
    p = prune.plan(tmp_path / "nope", 1, 1)
    assert p.keep == [] and p.remove == []


def test_retention_flags_override_config():
    assert prune.retention({"keep_daily": 14, "keep_full": 4}, None, None) == (14, 4)
    assert prune.retention({"keep_daily": 14, "keep_full": 4}, 3, None) == (3, 4)
    assert prune.retention(None, None, 2) == (None, 2)
    for bad in (-1, "7", True):
        with pytest.raises(ValueError):
            prune.retention({"keep_daily": bad}, None, None)

"""Snapshot folders are created readable by the owner only, existing open folders are warned about and left alone (#86)."""

import ast
import os
import stat
from pathlib import Path

import pytest

from lib.foundations import paths, snapshot

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _umask_022_and_fresh_open_dirs(monkeypatch):
    old = os.umask(0o022)
    monkeypatch.setattr(paths, "_open_dirs", {})
    yield
    os.umask(old)


def _mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def test_new_snapshot_dir_makes_root_context_and_snapshot_folders_0700(tmp_path):
    root = tmp_path / "snapshots"
    snap = paths.new_snapshot_dir("ctx", root=root)
    assert snap.parent.parent == root
    assert _mode(root) == 0o700 and _mode(snap.parent) == 0o700 and _mode(snap) == 0o700


def test_every_missing_component_is_0700_not_only_the_last(tmp_path):
    p = paths.ensure_private_dir(tmp_path / "a" / "b" / "c")
    assert p.is_dir()
    assert _mode(tmp_path / "a") == 0o700 and _mode(tmp_path / "a" / "b") == 0o700 and _mode(p) == 0o700


def test_write_private_creates_owner_only_parents(tmp_path):
    snapshot.write_private(tmp_path / "x" / "y" / "f.json", "{}")
    assert _mode(tmp_path / "x") == 0o700 and _mode(tmp_path / "x" / "y") == 0o700
    assert _mode(tmp_path / "x" / "y" / "f.json") == 0o600


def test_existing_open_folder_is_recorded_once_not_printed_and_not_changed(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(paths, "_open_dirs", {})
    open_dir = tmp_path / "open"
    open_dir.mkdir(mode=0o755)
    sub = paths.ensure_private_dir(open_dir / "sub", base=tmp_path)
    paths.ensure_private_dir(open_dir / "sub2", base=tmp_path)
    assert capsys.readouterr().err == "", "no warning on stderr: setup asks about it instead (#171)"
    assert paths.open_dirs() == [(open_dir.resolve(), 0o755)]
    assert _mode(open_dir) == 0o755, "an existing folder is never chmod-ed by ensure_private_dir"
    assert _mode(sub) == 0o700 and _mode(open_dir / "sub2") == 0o700


def test_protect_home_chmods_the_recorded_folders_outermost_first(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_open_dirs", {})
    top = tmp_path / "home"
    top.mkdir(mode=0o755)
    (top / "snapshots").mkdir(mode=0o755)
    paths.ensure_private_dir(top / "snapshots" / "ctx", base=top)
    assert [d for d, _ in paths.open_dirs()] == [top.resolve(), (top / "snapshots").resolve()]
    assert paths.protect_home() == [top.resolve(), (top / "snapshots").resolve()]
    assert _mode(top) == 0o700 and _mode(top / "snapshots") == 0o700
    assert paths.open_dirs() == [] and paths.protect_home() == []


def test_a_private_existing_folder_is_not_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_open_dirs", {})
    d = tmp_path / "closed"
    d.mkdir(mode=0o700)
    paths.ensure_private_dir(d / "sub", base=tmp_path)
    assert paths.open_dirs() == []


def test_nothing_above_the_base_is_inspected(tmp_path, monkeypatch):
    """tmp_path itself is 0700 on pytest, so make an open folder above the base and check that it is not reported."""
    above = tmp_path / "above"
    above.mkdir(mode=0o755)
    base = above / "root"
    monkeypatch.setattr(paths, "_open_dirs", {})
    paths.ensure_private_dir(base / "ctx" / "snap", base=base)
    assert paths.open_dirs() == []
    assert _mode(base) == 0o700 and _mode(base / "ctx") == 0o700


def test_a_path_outside_user_dir_without_a_base_creates_but_does_not_inspect(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(paths, "USER_DIR", tmp_path / "userdir")
    above = tmp_path / "elsewhere"
    above.mkdir(mode=0o755)
    paths.ensure_private_dir(above / "a" / "b")
    assert "readable by other users" not in capsys.readouterr().err
    assert _mode(above / "a") == 0o700 and _mode(above / "a" / "b") == 0o700


def test_a_path_under_user_dir_is_inspected_from_user_dir(tmp_path, capsys, monkeypatch):
    user_dir = tmp_path / "userdir"
    user_dir.mkdir(mode=0o755)
    monkeypatch.setattr(paths, "USER_DIR", user_dir)
    monkeypatch.setattr(paths, "_open_dirs", {})
    paths.ensure_private_dir(user_dir / "snapshots" / "ctx")
    assert paths.open_dirs() == [(user_dir.resolve(), 0o755)]
    assert _mode(user_dir / "snapshots") == 0o700


def test_runlog_file_is_owner_only(tmp_path):
    from lib.foundations.runlog import RunLog

    log = RunLog(tmp_path / "ctx" / "snap" / "run.log")
    log.note("x")
    log.note("y")
    assert _mode(tmp_path / "ctx") == 0o700 and _mode(tmp_path / "ctx" / "snap") == 0o700
    assert _mode(tmp_path / "ctx" / "snap" / "run.log") == 0o600
    assert len((tmp_path / "ctx" / "snap" / "run.log").read_text().splitlines()) == 2


def test_runlog_recreated_after_unlink_is_still_owner_only(tmp_path):
    """setup deletes setup.log after building the RunLog and writes again; the mode must not depend on that order."""
    from lib.foundations.runlog import RunLog

    p = tmp_path / "setup.log"
    log = RunLog(p)
    log.note("first")
    p.unlink()
    log.stage("setup", "start")
    assert _mode(p) == 0o600 and "first" not in p.read_text()


def test_two_runs_in_the_same_second_get_different_folders(tmp_path):
    import datetime as dt

    now = dt.datetime(2026, 11, 4, 1, 2, 3)
    a = paths.new_snapshot_dir("ctx", root=tmp_path, now=now)
    b = paths.new_snapshot_dir("ctx", root=tmp_path, now=now)
    c = paths.new_snapshot_dir("ctx", root=tmp_path, now=now)
    assert [a.name, b.name, c.name] == ["2026-11-04T01-02-03", "2026-11-04T01-02-03-2", "2026-11-04T01-02-03-3"]
    assert _mode(a) == _mode(b) == _mode(c) == 0o700


def test_a_file_in_the_way_raises(tmp_path):
    (tmp_path / "afile").write_text("x")
    with pytest.raises(FileExistsError, match="not a directory"):
        paths.ensure_private_dir(tmp_path / "afile")


def test_a_symlink_inside_the_base_is_still_inspected(tmp_path):
    """~/.kubegap/snapshots -> a shared disk: the link resolves outside the base, but the open target must still be recorded."""
    base = tmp_path / "base"
    base.mkdir(mode=0o700)
    target = tmp_path / "shared"
    target.mkdir(mode=0o755)
    (base / "snapshots").symlink_to(target)
    paths.ensure_private_dir(base / "snapshots" / "ctx", base=base)
    assert paths.open_dirs() == [(target.resolve(), 0o755)], "recorded under its real path, so protect-home changes the target"
    assert _mode(target / "ctx") == 0o700


def _mkdir_calls(source: str, filename: str) -> list[str]:
    out = []
    for node in ast.walk(ast.parse(source, filename)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("mkdir", "makedirs"):
            out.append(f"{filename}:{node.lineno}")
    return out


def test_no_other_module_creates_folders():
    """Every folder under a snapshot, the user dir or .tools/ comes from paths.ensure_private_dir (lib/commands/tools.py included since #88)."""
    offenders = []
    for f in [*sorted(ROOT.glob("lib/*/*.py")), ROOT / "scripts" / "kubegap"]:
        if f.name == "paths.py":
            continue
        offenders += _mkdir_calls(f.read_text(encoding="utf-8"), str(f.relative_to(ROOT)))
    assert offenders == []


def test_mkdir_scanner_sees_the_known_forms():
    src = 'p.mkdir(parents=True)\nos.makedirs(p)\nPath("x").mkdir()\nopen(p)\n'
    assert _mkdir_calls(src, "x.py") == ["x.py:1", "x.py:2", "x.py:3"]

"""Snapshot files are written atomically, owner-only, through lib.snapshot.write_private and nothing else (#87)."""

import ast
import stat
from pathlib import Path

import pytest

from lib import snapshot

ROOT = Path(__file__).resolve().parent.parent


def test_writes_content_owner_only_and_leaves_no_temp_file(tmp_path):
    p = tmp_path / "summary.json"
    snapshot.write_private(p, '{"a": 1}\n')
    assert p.read_text(encoding="utf-8") == '{"a": 1}\n'
    assert stat.S_IMODE(p.stat().st_mode) == 0o600
    assert [x.name for x in tmp_path.iterdir()] == ["summary.json"]


def test_creates_missing_parent_folders(tmp_path):
    p = tmp_path / "objects" / "deep" / "pods.json"
    snapshot.write_private(p, "[]")
    assert p.read_text(encoding="utf-8") == "[]"


def test_replaces_an_existing_file(tmp_path):
    p = tmp_path / "MODE"
    p.write_text("daily\n")
    snapshot.write_private(p, "full\n")
    assert p.read_text() == "full\n"
    assert [x.name for x in tmp_path.iterdir()] == ["MODE"]


def test_keeps_the_old_file_and_no_temp_file_when_the_rename_fails(tmp_path, monkeypatch):
    p = tmp_path / "summary.json"
    p.write_text("old")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(snapshot.os, "replace", boom)
    with pytest.raises(OSError, match="disk full"):
        snapshot.write_private(p, "new")
    assert p.read_text() == "old"
    assert [x.name for x in tmp_path.iterdir()] == ["summary.json"]


def test_keeps_the_old_file_when_the_write_itself_fails(tmp_path, monkeypatch):
    p = tmp_path / "findings-draft.json"
    p.write_text("old")

    def boom(fd):
        raise OSError("fsync failed")

    monkeypatch.setattr(snapshot.os, "fsync", boom)
    with pytest.raises(OSError, match="fsync failed"):
        snapshot.write_private(p, "new")
    assert p.read_text() == "old"
    assert [x.name for x in tmp_path.iterdir()] == ["findings-draft.json"]


def test_custom_mode(tmp_path):
    p = tmp_path / "x"
    snapshot.write_private(p, "x", mode=0o640)
    assert stat.S_IMODE(p.stat().st_mode) == 0o640


def test_preserves_newlines_exactly(tmp_path):
    p = tmp_path / "history.csv"
    snapshot.write_private(p, "a,b\r\n1,2\r\n")
    assert p.read_bytes() == b"a,b\r\n1,2\r\n"


def _write_calls(source: str, filename: str) -> list[str]:
    """Calls in `source` that write a file by any way other than write_private: Path.write_text / write_bytes, and open()/Path.open() with a w, a or x mode."""
    out = []
    for node in ast.walk(ast.parse(source, filename)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr in ("write_text", "write_bytes"):
            out.append(f"{filename}:{node.lineno}: .{fn.attr}(")
            continue
        is_open = (isinstance(fn, ast.Name) and fn.id == "open") or (isinstance(fn, ast.Attribute) and fn.attr in ("open", "fdopen"))
        if not is_open:
            continue
        mode = None
        pos = 0 if (isinstance(fn, ast.Attribute) and fn.attr == "open") else 1  # Path.open(mode, ...) versus open(file, mode, ...) and os.fdopen(fd, mode, ...)
        if len(node.args) > pos and isinstance(node.args[pos], ast.Constant):
            mode = node.args[pos].value
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = kw.value.value
        if isinstance(mode, str) and mode[:1] in ("w", "a", "x"):
            out.append(f"{filename}:{node.lineno}: open(..., {mode!r})")
    return out


def test_no_other_module_writes_files():
    """Every file write in lib/ and scripts/kubegap goes through write_private. Exceptions: run.log is appended line by line (runlog.py); tool binaries are installed with write_bytes (tools.py)."""
    offenders = []
    for f in [*sorted(ROOT.glob("lib/*.py")), ROOT / "scripts" / "kubegap"]:
        if f.name in ("snapshot.py", "runlog.py", "tools.py"):
            continue
        offenders += _write_calls(f.read_text(encoding="utf-8"), str(f.relative_to(ROOT)))
    assert offenders == []


def test_write_call_scanner_catches_the_known_forms():
    src = "\n".join(
        [
            'p.write_text("x")',
            'p.write_bytes(b"x")',
            'open(str(p), "w")',
            'open(p.with_suffix(".x"), "wt")',
            'with open(\n    p,\n    "a",\n) as f:\n    pass',
            'p.open(mode="x")',
            'os.fdopen(fd, "w")',
            'p.open("a", encoding="utf-8")',
            "open(p)",
            'open(p, "r")',
            'p.open("rb")',
            '"""a docstring that says .write_text( and open(p, "w")"""',
        ]
    )
    found = _write_calls(src, "x.py")
    assert sorted(int(x.split(":")[1]) for x in found) == [1, 2, 3, 4, 5, 10, 11, 12], found


def test_tools_only_writes_binaries_and_runlog_only_appends():
    tools = _write_calls((ROOT / "lib" / "tools.py").read_text(encoding="utf-8"), "lib/tools.py")
    assert tools and all("write_bytes" in x for x in tools), tools
    runlog = _write_calls((ROOT / "lib" / "runlog.py").read_text(encoding="utf-8"), "lib/runlog.py")
    assert runlog and all("'a'" in x for x in runlog), runlog


def test_remove_stale_temp_removes_only_temp_files(tmp_path):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / ".pods.json.ab12cd.tmp").write_text("half")
    (tmp_path / "objects" / "pods.json").write_text("{}")
    (tmp_path / ".summary.json.x.tmp").write_text("half")
    assert snapshot.remove_stale_temp(tmp_path) == 2
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == ["pods.json"]

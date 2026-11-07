"""A venv-installed tool reports the tag it was installed from, and the version probe never runs inside this repository (#119).
krr v1.31.1 ships `__version__ = "dev"` (robusta_krr/__init__.py:3) and then prints `git describe --tags` of the working directory (robusta_krr/utils/version.py:13-24)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from lib.commands import tools
from lib.foundations import shell


def _krr():
    return next(t for t in tools.TOOLS if t.name == "krr")


def test_venv_tag_is_read_from_the_pip_source():
    assert tools._venv_tag({"pip": "https://github.com/robusta-dev/krr/archive/refs/tags/v1.31.1.tar.gz"}) == "v1.31.1"
    assert tools._venv_tag({"pip": "robusta-krr==1.31.1"}) == "1.31.1"
    assert tools._venv_tag({"pip": "robusta-krr"}) is None


def test_the_probe_runs_outside_the_repository_and_a_pinned_venv_reports_its_tag(tmp_path, monkeypatch):
    tools_dir = tmp_path / ".tools"
    venv = tools_dir / "krr-venv"
    (venv / "bin").mkdir(parents=True)
    real = venv / "bin" / "krr"
    real.write_text("#!/bin/sh\necho v0.1.2-32-gabcdef-main\n")  # what krr prints when its cwd is this repository
    real.chmod(0o700)
    (tools_dir / "bin").mkdir()
    (tools_dir / "bin" / "krr").symlink_to(real)
    (venv / tools._PIN_FILE).write_text("v1.31.1\n")
    monkeypatch.setattr(shell, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(shell, "TOOLS_BIN", tools_dir / "bin")
    monkeypatch.setenv("PATH", f"{tools_dir / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    seen = {}
    real_run = shell.run

    def spy(cmd, **kw):
        seen["cwd"] = kw.get("cwd")
        return real_run(cmd, **kw)

    monkeypatch.setattr(shell, "run", spy)
    v = tools.tool_version(_krr())
    assert seen["cwd"] == Path(tempfile.gettempdir())
    assert v == "v1.31.1 (installed from that tag; the tool reports 0.1.2)"
    real.write_text("#!/bin/sh\necho 1.31.1\n")
    assert tools.tool_version(_krr()) == "v1.31.1"


def test_a_tool_outside_a_venv_reports_what_it_prints(tmp_path, monkeypatch):
    monkeypatch.setattr(shell, "run", lambda cmd, **kw: shell.Result(cmd=cmd, code=0, stdout="Polaris version:10.2.6\n"))
    polaris = next(t for t in tools.TOOLS if t.name == "polaris")
    assert tools.tool_version(polaris) == "10.2.6"
    assert tools._venv_pin("/opt/homebrew/bin/polaris") is None


def test_install_in_venv_records_the_tag(tmp_path, monkeypatch):
    tools_dir = tmp_path / ".tools"
    monkeypatch.setattr(shell, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(shell, "TOOLS_BIN", tools_dir / "bin")
    monkeypatch.setattr(shell, "which", lambda name: "/usr/bin/python3" if name == "python3.11" else None)

    def fake_run(cmd, **kw):
        if cmd[1:3] == ["-m", "venv"]:
            (Path(cmd[3]) / "bin").mkdir(parents=True)
            (Path(cmd[3]) / "bin" / "pip").write_text("")
        if cmd[0].endswith("/pip"):
            (Path(cmd[0]).parent / "krr").write_text("#!/bin/sh\n")
        return shell.Result(cmd=cmd, code=0)

    monkeypatch.setattr(shell, "run", fake_run)
    res = tools.install_in_venv(_krr())
    assert res["ok"] and res["version"] == "v1.31.1", res
    assert (tools_dir / "krr-venv" / tools._PIN_FILE).read_text().strip() == "v1.31.1"
    assert tools._venv_pin(str(tools_dir / "bin" / "krr")) == "v1.31.1"

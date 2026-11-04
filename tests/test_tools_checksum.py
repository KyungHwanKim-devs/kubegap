"""`kubegap setup --install` downloads the pinned version of a tool and places it only when its sha256 matches the digest pinned in lib/tools.py (#88)."""

import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from lib import shell, snapshot, tools
from lib.tools import Tool

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _tools_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(shell, "TOOLS_DIR", tmp_path / ".tools")
    monkeypatch.setattr(shell, "TOOLS_BIN", tmp_path / ".tools" / "bin")
    old = os.umask(0o022)
    yield
    os.umask(old)


def _serve(monkeypatch, responses: dict):
    """tools._get that answers from `responses` (url -> bytes) and records every URL asked for. Anything else is a 404."""
    asked = []

    def fake_get(url, timeout=60):
        asked.append(url)
        if url not in responses:
            raise OSError(f"HTTP 404: {url}")
        return responses[url]

    monkeypatch.setattr(tools, "_get", fake_get)
    return asked


def _tool(download: dict, name="t") -> Tool:
    return Tool(name, "test tool", download=download)


def _tgz(bin_name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo(f"{bin_name}-1.0/{bin_name}")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _zip(bin_name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{bin_name}-1.0/{bin_name}", data)
    return buf.getvalue()


KEY = tools.platform_key()
BLOB = b"#!/bin/sh\necho hello\n"
URL = f"https://github.com/x/y/releases/download/v1.0.0/t-{KEY}"


def test_matching_digest_installs_an_executable_from_the_versioned_url(monkeypatch):
    asked = _serve(monkeypatch, {URL: BLOB})
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {KEY: hashlib.sha256(BLOB).hexdigest()}}))
    assert res["ok"] and res["version"] == "v1.0.0" and res["checksum"] == "verified", res
    target = shell.TOOLS_BIN / "t"
    assert target.read_bytes() == BLOB and os.access(target, os.X_OK) and stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE(shell.TOOLS_BIN.stat().st_mode) == 0o700 and stat.S_IMODE(shell.TOOLS_DIR.stat().st_mode) == 0o700
    assert asked == [URL], "one request, to the versioned asset; no release API, no latest"
    assert [x.name for x in shell.TOOLS_BIN.iterdir()] == ["t"], "no temporary file left behind"


def test_mismatch_writes_nothing(monkeypatch):
    _serve(monkeypatch, {URL: BLOB + b"tampered"})
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {KEY: hashlib.sha256(BLOB).hexdigest()}}))
    assert res["ok"] is False and "checksum mismatch for t-" in res["error"], res
    assert not (shell.TOOLS_BIN / "t").exists()
    assert not shell.TOOLS_BIN.exists() or list(shell.TOOLS_BIN.iterdir()) == []


@pytest.mark.parametrize("packer, ext", [(_tgz, ".tar.gz"), (_zip, ".zip")])
def test_archives_are_hashed_whole_and_the_executable_is_extracted(monkeypatch, packer, ext):
    archive = packer("t", BLOB)
    url = f"https://example.org/t-1.0.0-{KEY}{ext}"
    good = {"version": "v1.0.0", "url": "https://example.org/t-{version}-{os}-{arch}" + ext, "bin": "t", "sha256": {KEY: hashlib.sha256(archive).hexdigest()}}
    _serve(monkeypatch, {url: archive})
    res = tools.install_download(_tool(good))
    assert res["ok"], res
    assert (shell.TOOLS_BIN / "t").read_bytes() == BLOB and os.access(shell.TOOLS_BIN / "t", os.X_OK)
    (shell.TOOLS_BIN / "t").unlink()
    _serve(monkeypatch, {url: packer("t", BLOB + b"x")})
    res = tools.install_download(_tool(good))
    assert res["ok"] is False and "checksum mismatch" in res["error"]
    assert not (shell.TOOLS_BIN / "t").exists()


def test_a_platform_without_a_pinned_digest_downloads_nothing(monkeypatch):
    asked = _serve(monkeypatch, {URL: BLOB})
    other = next(k for k in tools.PLATFORMS if k != KEY)
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {other: hashlib.sha256(BLOB).hexdigest()}}))
    assert res["ok"] is False and f"no pinned sha256 for {KEY}" in res["error"]
    assert asked == [] and not (shell.TOOLS_BIN / "t").exists()


def test_a_download_error_is_an_install_failure_not_an_exception(monkeypatch):
    _serve(monkeypatch, {})
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {KEY: "0" * 64}}))
    assert res["ok"] is False and "404" in res["error"] and not (shell.TOOLS_BIN / "t").exists()


def test_an_interrupted_write_leaves_no_half_binary(monkeypatch):
    _serve(monkeypatch, {URL: BLOB})

    def boom(fd):
        raise OSError("disk full")

    monkeypatch.setattr(snapshot.os, "fsync", boom)
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {KEY: hashlib.sha256(BLOB).hexdigest()}}))
    assert res["ok"] is False and "disk full" in res["error"]
    assert list(shell.TOOLS_BIN.iterdir()) == []


def test_a_new_version_replaces_the_old_binary_and_a_venv_symlink(monkeypatch):
    shell.TOOLS_BIN.mkdir(parents=True)
    real = shell.TOOLS_DIR / "t-venv" / "bin" / "t"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"old venv")
    (shell.TOOLS_BIN / "t").symlink_to(real)
    _serve(monkeypatch, {URL: BLOB})
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": {KEY: hashlib.sha256(BLOB).hexdigest()}}))
    assert res["ok"], res
    assert not (shell.TOOLS_BIN / "t").is_symlink() and (shell.TOOLS_BIN / "t").read_bytes() == BLOB
    assert real.read_bytes() == b"old venv", "the venv's own file is untouched; only the link in bin/ is replaced"


def test_every_pinned_tool_is_installed_from_one_versioned_url_and_never_asks_what_is_newest(monkeypatch):
    """The real TOOLS table: each download entry has a version and a 64-hex digest per supported platform, install fetches exactly the
    versioned asset URL, and no request goes to a release API, stable.txt or any other 'latest' endpoint."""
    monkeypatch.setattr(tools, "host_os", lambda: KEY.split("-")[0])
    for t in tools.TOOLS:
        d = t.download
        if not d:
            continue
        assert d.get("version"), t.name
        keys = [k for k in tools.PLATFORMS if k.split("-")[0] in d.get("only_os", ["darwin", "linux"])]
        assert sorted(d["sha256"]) == sorted(keys), (t.name, d["sha256"])
        assert all(tools._HEX64.match(h) for h in d["sha256"].values()), t.name
        if not tools._download_applicable(t):
            continue
        asked = _serve(monkeypatch, {})
        res = tools.install_download(t)
        assert res["ok"] is False, t.name
        assert len(asked) == 1, (t.name, asked)
        url = asked[0]
        assert "api.github.com" not in url and "stable.txt" not in url and "latest" not in url, (t.name, url)
        assert d["version"] in url or tools._bare_version(d, d["version"]) in url, (t.name, url)
        assert url.startswith("https://"), url


def test_install_plan_shows_the_pinned_version(monkeypatch):
    monkeypatch.setattr(shell, "which", lambda name: None)
    line = tools.install_plan(tools.by_name("jq"))
    assert "jq-1.8.2" in line and "sha256 pinned" in line and "GitHub release jqlang/jq" in line
    line = tools.install_plan(tools.by_name("kubectl"))
    assert "v1.37.2" in line and "dl.k8s.io" in line


# ---------- the publisher's checksum files, read only by --check-tool-updates ----------


def test_parse_checksum_text_list_and_single():
    hexes = [f"{i:064x}" for i in range(3)]
    text = f"{hexes[0]}  t-linux-amd64.tar.gz\n{hexes[1]} *t-darwin-arm64.tar.gz\nnot a line\n{hexes[2]}  t-darwin-arm64\n"
    assert tools.parse_checksum_text(text, "t-linux-amd64.tar.gz", "list") == hexes[0]
    assert tools.parse_checksum_text(text, "t-darwin-arm64.tar.gz", "list") == hexes[1]
    assert tools.parse_checksum_text(text, "t-darwin-arm64", "list") == hexes[2]
    assert tools.parse_checksum_text(text, "t-windows-amd64.zip", "list") is None
    assert tools.parse_checksum_text(f"{hexes[0]}\n", "any", "single") == hexes[0]
    assert tools.parse_checksum_text(f"{hexes[0]}  helm-v3.22.1-linux-amd64.tar.gz\n", "any", "single") == hexes[0], "sha256sum output in a single-format file still starts with the hex"
    assert tools.parse_checksum_text("<html>not found</html>", "any", "single") is None
    assert tools.parse_checksum_text("abc  t-linux-amd64.tar.gz\n", "t-linux-amd64.tar.gz", "list") is None, "a short hex is malformed, not a digest"


def test_check_updates_reports_a_pin_behind_with_the_material_of_the_new_pin(monkeypatch):
    d = {"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}.tar.gz", "bin": "t", "sha256": dict.fromkeys(tools.PLATFORMS, "0" * 64), "checksums": {"asset": "checksums.txt", "format": "list"}}
    monkeypatch.setattr(tools, "TOOLS", [_tool(d, "t"), Tool("nodl", "no download")])
    hexes = {k: f"{i + 1:064x}" for i, k in enumerate(tools.PLATFORMS)}
    listing = "".join(f"{h}  t-{k}.tar.gz\n" for k, h in hexes.items())
    asked = _serve(monkeypatch, {"https://api.github.com/repos/x/y/releases/latest": json.dumps({"tag_name": "v1.1.0"}).encode(), "https://github.com/x/y/releases/download/v1.1.0/checksums.txt": listing.encode()})
    rows = tools.check_updates()
    assert [r["name"] for r in rows] == ["t"]
    assert rows[0]["behind"] is True and rows[0]["latest"] == "v1.1.0" and rows[0]["sha256"] == hexes
    assert not any("download/v1.1.0/t-" in u for u in asked), "with a checksum list, the assets themselves are not downloaded"
    # current pin: no checksum fetch at all
    asked.clear()
    d["version"] = "v1.1.0"
    rows = tools.check_updates()
    assert rows[0]["behind"] is False and rows[0]["sha256"] is None and asked == ["https://api.github.com/repos/x/y/releases/latest"]


def test_check_updates_computes_digests_when_the_publisher_ships_no_checksum_file(monkeypatch):
    d = {"version": "0.7.3", "repo": "x/y", "asset": "t-{version}-{os}-{arch}.tar.gz", "bin": "t", "strip_tag": "", "sha256": dict.fromkeys(tools.PLATFORMS, "0" * 64)}
    monkeypatch.setattr(tools, "TOOLS", [_tool(d, "t")])
    blobs = {f"https://github.com/x/y/releases/download/0.8.0/t-0.8.0-{k}.tar.gz": k.encode() for k in tools.PLATFORMS}
    _serve(monkeypatch, {"https://api.github.com/repos/x/y/releases/latest": json.dumps({"tag_name": "0.8.0"}).encode(), **blobs})
    rows = tools.check_updates()
    assert rows[0]["behind"] and rows[0]["sha256"] == {k: hashlib.sha256(k.encode()).hexdigest() for k in tools.PLATFORMS}


def test_check_updates_latest_by_match_url_and_tags(monkeypatch):
    rel = json.dumps([{"tag_name": "v4.3.1"}, {"tag_name": "v3.23.0-rc.1", "prerelease": True}, {"tag_name": "v3.22.1"}]).encode()
    _serve(monkeypatch, {"https://api.github.com/repos/h/h/releases?per_page=50": rel, "https://x/stable.txt": b"v1.38.0\n", "https://api.github.com/repos/a/a/tags?per_page=1": json.dumps([{"name": "2.40.0"}]).encode()})
    assert tools.latest_version({"latest": {"repo": "h/h", "match": r"^v3\."}}) == "v3.22.1"
    assert tools.latest_version({"latest": {"url": "https://x/stable.txt"}}) == "v1.38.0"
    assert tools.latest_version({"latest": {"tags": "a/a"}}) == "2.40.0"


def test_check_updates_never_writes_and_reports_a_fetch_error_per_tool(monkeypatch):
    monkeypatch.setattr(tools, "TOOLS", [_tool({"version": "v1", "repo": "x/y", "asset": "t", "bin": "t", "sha256": {}}, "t")])
    _serve(monkeypatch, {})
    rows = tools.check_updates()
    assert rows[0]["error"] and "404" in rows[0]["error"] and rows[0]["behind"] is None
    assert not shell.TOOLS_DIR.exists()


# ---------- setup output ----------


def test_setup_prints_installed_version_and_checksum_verified(monkeypatch):
    from lib import setup as _setup
    from lib.config import Config

    status = [{"name": "jq", "role": "JSON processing", "required": True, "present": False, "path": None, "version": None, "checks": ["*"], "installable": True, "note": ""}]
    monkeypatch.setattr(_setup.tools, "check_tools", lambda: status)
    monkeypatch.setattr(
        _setup.tools,
        "install_tool",
        lambda tool, log=None: {
            "name": "jq",
            "method": "download https://github.com/jqlang/jq/releases/download/jq-1.8.2/jq-macos-arm64",
            "ok": True,
            "error": None,
            "version": "jq-1.8.2",
            "sha256": "ab" * 32,
            "checksum": "verified",
            "sha256_from": "publisher",
        },
    )
    lines = []
    monkeypatch.setattr(_setup, "_p", lines.append)
    _setup.run_setup(None, Config(), install=["jq"])
    assert any(ln.strip() == "installed jq jq-1.8.2, checksum verified against the publisher's checksum file (download https://github.com/jqlang/jq/releases/download/jq-1.8.2/jq-macos-arm64)" for ln in lines), lines


def test_check_tool_updates_command_prints_and_exits_nonzero_when_behind(monkeypatch):
    from lib import setup as _setup

    rows = [
        {"name": "jq", "pinned": "jq-1.8.2", "latest": "jq-1.8.2", "behind": False, "sha256": None, "error": None},
        {"name": "pluto", "pinned": "v5.24.5", "latest": "v5.25.0", "behind": True, "sha256": {"darwin-arm64": "a" * 64}, "error": None},
        {"name": "aws", "pinned": "2.39.3", "latest": None, "behind": None, "sha256": None, "error": "OSError: no network"},
    ]
    monkeypatch.setattr(_setup.tools, "check_updates", lambda only=None: rows)
    lines = []
    monkeypatch.setattr(_setup, "_p", lines.append)
    assert _setup.check_tool_updates() == 1
    text = "\n".join(lines)
    assert "jq        pinned jq-1.8.2   newest jq-1.8.2   current" in text
    assert "pluto     pinned v5.24.5    newest v5.25.0    BEHIND" in text and '"version": "v5.25.0",' in text and '"sha256": {"darwin-arm64": "' + "a" * 64 + '"},' in text
    assert "aws       pinned 2.39.3     could not check: OSError: no network" in text
    assert "2 of 3 pins behind or unchecked" in text
    monkeypatch.setattr(_setup.tools, "check_updates", lambda only=None: rows[:1])
    assert _setup.check_tool_updates() == 0


# ---------- a tool that writes its own output file ----------


def test_tool_output_written_by_the_tool_itself_is_made_owner_only(tmp_path, monkeypatch):
    from lib import collect
    from lib.runlog import RunLog

    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    fake = bindir / "faketool"
    fake.write_text('#!/bin/sh\numask 022\necho \'{"ok": true}\' > "$1"\n')
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    snap = tmp_path / "snap"
    st = {"id": "krr", "type": "tool", "tool": "faketool", "cmd": ["faketool", "{out}"], "out": "tools/krr.json", "writes_out": True}
    res = collect._run_tool_step(st, "krr", "core", None, None, snap, RunLog(None), None, 30, None)
    assert res["ok"], res
    assert stat.S_IMODE((snap / "tools" / "krr.json").stat().st_mode) == 0o600


# ---------- review findings on #88 ----------


def test_an_unsupported_cpu_downloads_nothing(monkeypatch):
    monkeypatch.setattr(tools.platform, "machine", lambda: "armv7l")
    asked = _serve(monkeypatch, {URL: BLOB})
    res = tools.install_download(_tool({"version": "v1.0.0", "repo": "x/y", "asset": "t-{os}-{arch}", "bin": "t", "sha256": dict.fromkeys(tools.PLATFORMS, hashlib.sha256(BLOB).hexdigest())}))
    assert res["ok"] is False and "unsupported architecture armv7l" in res["error"]
    assert asked == [] and not shell.TOOLS_DIR.exists()


def test_check_updates_names_an_unknown_or_unpinned_tool_instead_of_calling_it_current(monkeypatch):
    _serve(monkeypatch, {})
    rows = tools.check_updates(["bogus", "krr"])
    assert [(r["name"], r["error"]) for r in rows] == [("bogus", "unknown tool"), ("krr", "no download entry (installed through brew or a virtualenv, not pinned here)")]
    from lib import setup as _setup

    monkeypatch.setattr(_setup.tools, "check_updates", lambda only=None: rows)
    lines = []
    monkeypatch.setattr(_setup, "_p", lines.append)
    assert _setup.check_tool_updates(["bogus", "krr"]) == 1
    assert any("bogus" in ln and "could not check: unknown tool" in ln for ln in lines), lines


def test_a_third_party_tap_formula_installs_the_pinned_download_first(monkeypatch):
    calls = []
    monkeypatch.setattr(shell, "which", lambda name: "/opt/homebrew/bin/brew" if name == "brew" else None)
    monkeypatch.setattr(shell, "run", lambda cmd, **kw: calls.append(cmd) or shell.Result(cmd=cmd, code=0, stdout=""))
    monkeypatch.setattr(tools, "install_download", lambda tool, log=None: {"name": tool.name, "method": "download x", "ok": True, "error": None, "checksum": "verified"})
    res = tools.install_tool(tools.by_name("pluto"))
    assert res["method"] == "download x" and calls == [], "no brew trust, no brew install when the pinned download succeeds"
    res = tools.install_tool(tools.by_name("jq"))
    assert res["method"] == "brew install jq" and calls == [["brew", "install", "jq"]], "a homebrew-core formula still goes through brew first"
    calls.clear()
    monkeypatch.setattr(tools, "install_download", lambda tool, log=None: {"name": tool.name, "method": "download x", "ok": False, "error": "checksum mismatch for pluto_x"})
    res = tools.install_tool(tools.by_name("pluto"))
    assert res["method"] == "brew install FairwindsOps/tap/pluto" and res["fallback_from"] == ["checksum mismatch for pluto_x"]
    assert calls[0] == ["brew", "trust", "--formula", "FairwindsOps/tap/pluto"]
    plan = tools.install_plan(tools.by_name("pluto"))
    assert plan.index("official binary v5.24.5") < plan.index("brew install FairwindsOps/tap/pluto")


def test_setup_says_where_the_pinned_digest_came_from(monkeypatch):
    from lib import setup as _setup
    from lib.config import Config

    status = [{"name": n, "role": "x", "required": False, "present": False, "path": None, "version": None, "checks": [], "installable": True, "note": ""} for n in ("kubent", "jq")]
    monkeypatch.setattr(_setup.tools, "check_tools", lambda: status)
    monkeypatch.setattr(
        _setup.tools, "install_tool", lambda tool, log=None: {"name": tool.name, "method": "download x", "ok": True, "error": None, "version": "v1", "checksum": "verified", "sha256_from": "asset" if tool.name == "kubent" else "publisher"}
    )
    lines = []
    monkeypatch.setattr(_setup, "_p", lines.append)
    _setup.run_setup(None, Config(), install=True)
    assert any("installed kubent v1, checksum verified against a digest computed from the asset when it was pinned; the publisher ships no checksum file" in ln for ln in lines), lines
    assert any("installed jq v1, checksum verified against the publisher's checksum file" in ln for ln in lines), lines


def test_every_real_install_result_reports_its_digest_provenance(monkeypatch):
    monkeypatch.setattr(tools, "host_os", lambda: KEY.split("-")[0])
    for t in tools.TOOLS:
        d = t.download
        if not d or not tools._download_applicable(t):
            continue
        assert (d.get("checksums") is None) == (t.name in ("kubent", "aws")), t.name


# What the archive readers do with a hostile member name (#128): the facts are cited in references/sources.md, the tests pin them on the running interpreter.
def _tgz_members(members: list[tuple[str, bytes | None]]) -> bytes:
    """A tar.gz with the members in order; a `None` payload makes a symbolic link to `../outside`."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in members:
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.SYMTYPE
                info.linkname = "../outside"
                tf.addfile(info)
            else:
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _zip_members(members: list[tuple[str, bytes | None]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members:
            if data is None:
                zi = zipfile.ZipInfo(name)
                zi.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(zi, "../outside")
            else:
                zf.writestr(name, data)
    return buf.getvalue()


@pytest.mark.parametrize("packer, ext", [(_tgz_members, ".tar.gz"), (_zip_members, ".zip")])
def test_a_member_named_with_dotdot_is_read_as_content_and_written_to_the_target_only(tmp_path, packer, ext):
    """`extractfile`/`read` never write a path: the member's bytes land at kubegap's own target, nothing appears outside it
    (tarfile.py:2485@v3.11.18, :2633@v3.14.10; zipfile.py:1564@v3.11.18, zipfile/__init__.py:1712@v3.14.10)."""
    target = shell.TOOLS_BIN / "t"
    err = tools._place_binary(packer([("../../escape/t", b"evil"), ("t-1.0/t", BLOB)]), "t" + ext, "t", target)
    assert err is None and target.read_bytes() == b"evil"  # the first regular member with that basename wins; the archive's digest was checked before this point
    assert not (tmp_path / "escape").exists() and not (shell.TOOLS_DIR / "escape").exists() and not (shell.TOOLS_DIR.parent / "escape").exists()
    assert [p.name for p in shell.TOOLS_BIN.iterdir()] == ["t"] and not target.is_symlink()


def test_a_symbolic_link_member_is_never_chosen_from_a_tar(tmp_path):
    """TarInfo.isfile() is false for a link (tarfile.py:1666@v3.11.18, :1739@v3.14.10), so a link named like the binary is skipped and a tar with only the link has no executable."""
    target = shell.TOOLS_BIN / "t"
    assert tools._place_binary(_tgz_members([("t-1.0/t", None)]), "t.tar.gz", "t", target) == "no t executable inside t.tar.gz"
    assert not target.exists()
    assert tools._place_binary(_tgz_members([("t-1.0/t", None), ("bin/t", BLOB)]), "t.tar.gz", "t", target) is None
    assert target.read_bytes() == BLOB and not target.is_symlink()


def test_a_symbolic_link_member_of_a_zip_is_read_as_its_link_text(tmp_path):
    """zipfile has no link type on read: the entry's bytes are the link text, and that is what would be placed; the pinned digest is what prevents it."""
    target = shell.TOOLS_BIN / "t"
    assert tools._place_binary(_zip_members([("t-1.0/t", None)]), "t.zip", "t", target) is None
    assert target.read_bytes() == b"../outside" and not target.is_symlink()


def test_aws_zip_extraction_stays_inside_the_work_folder_and_makes_no_link(tmp_path, monkeypatch):
    """`extractall` drops the root and every `..` part of a member name and writes regular files only (zipfile.py:1758,1775-1781@v3.11.18; zipfile/__init__.py:1918,1935-1941@v3.14.10)."""
    seen = {}

    def fake_run(cmd, timeout, id, log=None):
        work = shell.TOOLS_DIR / "aws-cli-src"
        seen["escape_outside"] = (shell.TOOLS_DIR / "escape.txt").exists() or (tmp_path / "escape.txt").exists() or Path("/escape.txt").exists()
        seen["escape_inside"] = (work / "escape.txt").read_text() if (work / "escape.txt").is_file() else None
        seen["abs_inside"] = (work / "tmp" / "abs.txt").is_file()
        seen["link"] = (work / "aws" / "dist" / "link").is_symlink()
        seen["link_text"] = (work / "aws" / "dist" / "link").read_text()
        return type("R", (), {"ok": True, "error": None, "stderr": ""})()

    monkeypatch.setattr(shell, "run", fake_run)
    blob = _zip_members([("../../escape.txt", b"out"), ("/tmp/abs.txt", b"abs"), ("aws/install", b"#!/bin/sh\n"), ("aws/dist/aws", b"bin"), ("aws/dist/link", None)])
    assert tools._aws_install(blob) == {"ok": True}
    assert seen == {"escape_outside": False, "escape_inside": "out", "abs_inside": True, "link": False, "link_text": "../outside"}

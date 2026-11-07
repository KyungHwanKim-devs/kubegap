"""A summary section or first-level key that the last tagged release documented and the working tree does not must be named in the CHANGELOG since
that release (#147): the code keeps no alias for it, so the sentence is what a reader of an old summary.json gets. Names only: a key whose type changed
(a map that became a number) is not seen here, and a key name that another CHANGELOG entry happens to mention in backticks counts as named."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from lib.commands import regress

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def _last_tag() -> str:
    tags = [t for t in _git("tag", "--list", "v*", "--sort=-v:refname").split() if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    if not tags:
        pytest.fail("no release tag v<major>.<minor>.<patch> in this checkout: CI fetches them (fetch-depth: 0); run `git fetch --tags` locally")
    return tags[0]


def _changelog_since(tag: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(tag[1:])}\]", text, re.MULTILINE)
    assert m, f"CHANGELOG has no heading for {tag}"
    return text[: m.start()]


def test_a_summary_key_the_last_release_had_is_named_in_the_changelog_when_it_goes():
    tag = _last_tag()
    with tempfile.TemporaryDirectory() as td:
        old = Path(td) / "summary-shape.md"
        old.write_text(_git("show", f"{tag}:references/summary-shape.md"), encoding="utf-8")
        before = regress.documented_shape(old)
    now = regress.documented_shape()
    since = _changelog_since(tag)
    gone = [s for s in before if s not in now] + [f"{s}.{k}" for s in before if s in now for k in sorted(before[s] - now[s])]
    unnamed = [g for g in gone if f"`{g.rsplit('.', 1)[-1]}`" not in since and f"`{g}`" not in since]
    assert unnamed == [], f"gone since {tag} without a CHANGELOG line that names them: {unnamed}"


def test_the_comparison_sees_a_removed_key(tmp_path):
    (tmp_path / "old.md").write_text("## a\n\n`a{x, y}`\n\n## b\n\n`b{z}`\n")
    (tmp_path / "new.md").write_text("## a\n\n`a{x}`\n")
    before, now = regress.documented_shape(tmp_path / "old.md"), regress.documented_shape(tmp_path / "new.md")
    gone = [s for s in before if s not in now] + [f"{s}.{k}" for s in before if s in now for k in sorted(before[s] - now[s])]
    assert gone == ["b", "a.y"]

"""The snapshot carries its format version and a kubegap of another version does not read it (#97)."""

from __future__ import annotations

import json

import pytest

from lib.foundations import paths, snapshot


def _snap(tmp_path, inv: dict | None):
    if inv is not None:
        (tmp_path / "inventory.json").write_text(json.dumps(inv))
    return tmp_path


def test_the_current_version_passes(tmp_path):
    snapshot.check_schema(_snap(tmp_path, {"kubegap": "0.1.5", "schema": paths.SCHEMA_VERSION}))


@pytest.mark.parametrize("inv", [None, {"kubegap": "0.1.4"}, {"kubegap": "x", "schema": "1"}])
def test_a_snapshot_without_the_key_is_version_0_and_refused(tmp_path, inv):
    s = _snap(tmp_path, inv)
    assert snapshot.schema_of(s) == 0
    with pytest.raises(SystemExit, match=rf"has format version 0; this kubegap reads version {paths.SCHEMA_VERSION}\. A snapshot of another format version is not read"):
        snapshot.check_schema(s)


def test_a_newer_version_is_refused_with_both_numbers(tmp_path):
    s = _snap(tmp_path, {"schema": paths.SCHEMA_VERSION + 1})
    with pytest.raises(SystemExit, match=rf"format version {paths.SCHEMA_VERSION + 1}; this kubegap reads version {paths.SCHEMA_VERSION}"):
        snapshot.check_schema(s)


def test_discover_summarize_and_evaluate_write_the_version():
    """The three writers put `schema` next to `kubegap`, so a consumer that opens one file sees it."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for f in ("lib/collection/discover.py", "lib/summaries/summarize.py", "lib/judgement/evaluate/__init__.py"):
        src = (root / f).read_text(encoding="utf-8")
        assert '"schema": paths.SCHEMA_VERSION' in src, f
    assert "check_schema(snap)" in (root / "scripts" / "kubegap").read_text(encoding="utf-8"), "the CLI refuses before any reader opens the snapshot"
    assert "check_schema(snap)" in (root / "lib" / "commands" / "regress.py").read_text(encoding="utf-8"), "the regression harness demands the same of a fixture"


def test_the_fixtures_carry_the_current_version():
    from lib.commands import regress

    for f in regress.fixtures():
        assert snapshot.schema_of(f) == paths.SCHEMA_VERSION, f.name

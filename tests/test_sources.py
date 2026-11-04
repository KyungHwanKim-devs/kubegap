"""references/sources.md lists every fact kubegap relies on from another project's source, with a `path:line@tag` citation and the kubegap location (#119).
Every `type: tool` step must carry a `source:` line, so a new tool cannot be added from memory."""

from __future__ import annotations

import re
from pathlib import Path

from lib import yamlite

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "references" / "sources.md"
CITATION = re.compile(r"[\w./-]+\.(?:go|py|rego|toml|yaml):\d+(?:-\d+)?(?:, ?\d+(?:-\d+)?)*@[\w.+-]+")
KUBEGAP_LOCATION = re.compile(r"`(lib/[\w/]+\.py)(?::(\w+))?`|step `([\w.-]+)`|check `([\w.-]+)`|`([A-Za-z_]\w*)`")


def _rows():
    rows = []
    for ln in SOURCES.read_text(encoding="utf-8").splitlines():
        if ln.startswith("| ") and not ln.startswith("| Fact") and not ln.startswith("|---"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 4:
                rows.append(cells)
    return rows


def test_every_row_cites_a_file_line_and_version_or_says_unverified():
    rows = _rows()
    assert len(rows) >= 40
    for fact, _where, source, _holds in rows:
        assert CITATION.search(source) or source.startswith("**unverified"), (fact, source)


def test_every_kubegap_location_exists():
    steps = {f"{Path(f).parent.name}.{s.get('id')}" for f in (ROOT / "collectors").glob("*/collect.yaml") for s in yamlite.load_file(f) or []}
    checks = {c.get("id") for f in (ROOT / "collectors").glob("*/checks.yaml") for c in yamlite.load_file(f) or []}
    lib_texts = [f.read_text(encoding="utf-8") for f in (ROOT / "lib").glob("*.py")]
    seen = 0
    for fact, where, _source, _holds in _rows():
        for m in KUBEGAP_LOCATION.finditer(where):
            seen += 1
            path, func, step, check, bare = m.groups()
            if path:
                text = (ROOT / path).read_text(encoding="utf-8")
                assert not func or f"def {func}(" in text, (fact, path, func)
            elif step:
                assert step in steps, (fact, step)
            elif check:
                assert check in checks, (fact, check)
            elif bare:
                assert any(f"def {bare}(" in t for t in lib_texts), (fact, bare, "no such function in lib/")
    assert seen >= 40


def test_every_tool_step_names_its_source():
    for f in (ROOT / "collectors").glob("*/collect.yaml"):
        for s in yamlite.load_file(f) or []:
            if s.get("type") == "tool":
                assert CITATION.search(str(s.get("source") or "")), (f.name, s.get("id"), "add a source: line citing the pinned version's file:line")

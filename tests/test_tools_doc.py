"""The optional-tools table of docs/SETUP.md and docs/ko/SETUP.md is generated from lib/commands/tools.py and the check catalog (#23);
these tests fail when the table is stale or when a tool names a check the catalog does not have (the first-run question
once offered argocd, promtool and amtool for checks that did not exist and steps that never ran them)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from lib.commands import tools
from lib.foundations import paths

ROOT = paths.ROOT
BEGIN, END = "<!-- tools-table:begin -->\n", "<!-- tools-table:end -->\n"


def _cli(*args: str) -> str:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "tools", *args], check=True, capture_output=True, text=True, cwd=ROOT).stdout


def _slice(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert BEGIN in text and END in text, f"{path} lost the tools-table markers"
    return text.split(BEGIN, 1)[1].split(END, 1)[0]


@pytest.mark.parametrize("language, doc", [("en", "docs/SETUP.md"), ("ko", "docs/ko/SETUP.md")])
def test_tools_table_is_current(language, doc):
    assert _cli("--markdown", "--language", language) == _slice(ROOT / doc), f"run `scripts/kubegap tools --markdown --language {language}` and paste it between the markers of {doc}"


def test_every_tool_check_pattern_names_a_check_of_the_catalog():
    catalog = tools.catalog()
    for t in tools.TOOLS:
        for pat in t.checks:
            assert tools.check_ids([pat], catalog), f"{t.name}: `{pat}` matches no check id; the first-run question would promise checks that do not exist"


def test_every_tool_is_run_by_a_step_or_is_a_client():
    """A tool in the table is either run by a `type: tool` step, is a required client, or is the access path of a step family (aws, ssh)."""
    steps = set()
    for f in sorted(paths.COLLECTORS_DIR.glob("*/collect.yaml")):
        steps |= set(re.findall(r"^\s+tool:\s*([a-z0-9-]+)\s*$", f.read_text(encoding="utf-8"), re.MULTILINE))
    for t in tools.TOOLS:
        assert t.required or t.name in steps or t.name in ("aws", "ssh"), f"{t.name} is offered for install but no collection step runs it"


def test_checks_text_counts_a_prefix_and_keeps_an_id():
    catalog = {"node.a": {"modes": ["full"]}, "node.b": {}, "eks.x": {}, "resources.krr-recommendation": {"requires_tool": "krr"}}
    assert tools.checks_text(["node.*", "resources.krr-recommendation"], catalog) == "node.* (2), resources.krr-recommendation"
    assert tools.checks_text(["node.*@full"], catalog) == "node.* (1, full mode)"
    assert tools.check_ids(["node.*@full"], catalog) == ["node.a"], "the Prometheus-read node checks run without node access and are not counted"
    assert tools.checks_text(["*"], catalog) == "every check (4)"
    assert tools.checks_text(["node.*"], None) == "node.*"
    assert tools.check_ids(["eks.*", "nothing.here"], catalog) == ["eks.x"]


def test_the_node_access_tools_count_only_the_node_script_checks():
    """What the table says aws and ssh feed must be the number the first-run question promises (firstrun.node_script_checks)."""
    from lib.commands import firstrun

    catalog = tools.catalog()
    for name in ("aws", "ssh"):
        ids = [c for c in tools.check_ids(tools.by_name(name).checks, catalog) if c.startswith("node.")]
        assert len(ids) == firstrun.node_script_checks()

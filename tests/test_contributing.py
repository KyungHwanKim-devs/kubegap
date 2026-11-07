"""CONTRIBUTING.md cannot rot silently (#152): every command it shows exists, it names what CI runs and on which Pythons, its review checklist is whole,
and the Korean half has the sections of the English half. README and the development reference point at it."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
ENGLISH, _, KOREAN = TEXT.partition("\n---\n")


def _fenced_commands(text: str) -> list[str]:
    out = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
        for line in block.splitlines():
            cmd = line.split("#", 1)[0].strip()
            if cmd:
                out.append(cmd)
    return out


def test_every_kubegap_sub_command_it_names_exists():
    help_text = subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "--help"], capture_output=True, text=True, check=True).stdout
    known = set(re.findall(r"^    (\S+)\s", help_text.split("positional arguments:", 1)[1], re.MULTILINE))
    named = set(re.findall(r"scripts/kubegap ([a-z-]+)", ENGLISH))
    assert named <= known, named - known
    assert {"selftest", "regress", "checks", "verified", "tools", "node-commands"} <= named, "the guide names the sub-commands that regenerate files and run the tests"


def test_the_commands_are_the_ones_ci_runs_and_on_the_same_pythons():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    runs = re.findall(r"- run: (.+)", ci)
    for needle in ("ruff check .", "ruff format --check .", "pytest -q", "scripts/kubegap selftest"):
        assert any(needle in r for r in runs), needle
        assert any(needle in c for c in _fenced_commands(ENGLISH)), needle
    assert "scripts/kubegap regress" in _fenced_commands(ENGLISH), "the regression run is a documented command even though CI reaches it through pytest"
    versions = re.search(r"python-version: \[(.*?)\]", ci).group(1)
    for v in re.findall(r'"([\d.]+)"', versions):
        assert v in ENGLISH, f"Python {v} is in the CI matrix but not in CONTRIBUTING.md"


def test_the_review_checklist_is_whole():
    for phrase in (
        "Project intent",
        "User intent of the issue",
        "Root cause, not a patch",
        "Issue text verified",
        "What the change does not do",
        "Every external claim cited",
        "Tests the reviewer ran",
        "Existing helper reused",
        "No boundary crossed",
        "No interface changed silently",
    ):
        assert phrase in ENGLISH, phrase
    for phrase in ("read-only", "Secret value", "deterministic", "false pass", "standard library"):
        assert phrase in ENGLISH, phrase


def test_the_korean_half_has_the_sections_of_the_english_half():
    assert KOREAN.startswith("\n# 기여하기"), "the Korean guide follows a --- line and starts with its own title"
    en = re.findall(r"^## ", ENGLISH, re.MULTILINE)
    ko = re.findall(r"^## ", KOREAN, re.MULTILINE)
    assert len(en) == len(ko) == 6, (len(en), len(ko))
    assert len(re.findall(r"^\d+\. \*\*", KOREAN, re.MULTILINE)) == len(re.findall(r"^\d+\. \*\*", ENGLISH, re.MULTILINE)), "the numbered steps and checklist items match"
    assert _fenced_commands(KOREAN) == _fenced_commands(ENGLISH)


def test_the_other_documents_point_at_it():
    for path in ("README.md", "README.ko.md", "SKILL.md", "references/development.md"):
        assert "CONTRIBUTING.md" in (ROOT / path).read_text(encoding="utf-8"), path
    dev = (ROOT / "references" / "development.md").read_text(encoding="utf-8")
    assert "review checklist" in dev and "pull request rules" in dev, "development.md says the process lives in CONTRIBUTING.md"

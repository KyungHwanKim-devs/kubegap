"""docs/CHECKS.md is generated from the check definitions; this test fails when someone changes a check without regenerating it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_checks_catalog_is_current():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "checks", "--markdown"], check=True, capture_output=True, text=True, cwd=ROOT).stdout
    assert out == (ROOT / "docs" / "CHECKS.md").read_text(encoding="utf-8"), "run `scripts/kubegap checks --markdown > docs/CHECKS.md`"


def test_skill_frontmatter_mirrors_rubric_version():
    """SKILL.md's `rubric_version` is what a host shows for the skill; it must be the rubric that ships with it."""
    version = (ROOT / "rubric" / "version").read_text(encoding="utf-8").strip()
    head = (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    assert f'rubric_version: "{version}"' in head, f'SKILL.md frontmatter must carry rubric_version: "{version}"'

"""docs/CHECKS.md is generated from the check definitions; this test fails when someone changes a check without regenerating it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_checks_catalog_is_current():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "checks", "--markdown"], check=True, capture_output=True, text=True, cwd=ROOT).stdout
    assert out == (ROOT / "docs" / "CHECKS.md").read_text(encoding="utf-8"), "run `scripts/kubegap checks --markdown > docs/CHECKS.md`"

"""Make `lib` importable when pytest is run from anywhere (pyproject.toml also sets pythonpath = ["."]; this is the belt to that suspender)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

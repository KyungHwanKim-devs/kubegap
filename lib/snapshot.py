"""Shared readers for snapshot files. Every summary module used to carry its own copy of these three helpers; they live here now.

A snapshot folder holds `objects/<resource>.json` (kubectl get -o json output, a list under "items"), `metrics/<query>.json`, `aws/*.json` and so on.
Reads are forgiving on purpose: a missing or corrupt file returns None (or an empty list), because one failed collection step must not stop the summary.
The missing input shows up as an "error"/"note" field in the module's own output and from there in the report's tool-notes section.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """Parse one JSON file. Returns None when the file is missing or not valid JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def items(doc: Any) -> list:
    """The "items" list of a kubectl list document. Empty list for None, a non-dict or a document without items."""
    return (doc.get("items") or []) if isinstance(doc, dict) else []


def objects(snap: Path, stem: str) -> list:
    """Items of `objects/<stem>.json` in the snapshot. `stem` is the resource file name, e.g. "deployments" or "bgppeers.metallb.io"."""
    return items(load_json(snap / "objects" / f"{stem}.json"))

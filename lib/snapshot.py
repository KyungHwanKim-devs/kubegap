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


COMPONENT_LOGS_DIR = Path("logs") / "pods"
COMPONENT_LOGS_MARKER = "REMOVED.txt"
COMPONENT_LOGS_AGGREGATE = "AGGREGATED.json"


def component_logs_removed(snap: Path) -> bool:
    """True when summarize has deleted the component pod logs of this snapshot (marker file left in logs/pods/)."""
    return (snap / COMPONENT_LOGS_DIR / COMPONENT_LOGS_MARKER).is_file()


def component_logs_aggregate(snap: Path) -> dict | None:
    """What summarize saved from the raw component logs before deleting them: {"log_scan": {...}, "karpenter_logs": {...}}. None when the logs are still there (or were never collected)."""
    d = load_json(snap / COMPONENT_LOGS_DIR / COMPONENT_LOGS_AGGREGATE)
    return d if isinstance(d, dict) else None


def objects(snap: Path, stem: str) -> list:
    """Items of `objects/<stem>.json` in the snapshot. `stem` is the resource file name, e.g. "deployments" or "bgppeers.metallb.io"."""
    return items(load_json(snap / "objects" / f"{stem}.json"))

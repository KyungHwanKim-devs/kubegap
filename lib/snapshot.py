"""Shared readers and the one writer for snapshot files. Every summary module used to carry its own copy of the three readers; they live here now.

A snapshot folder holds `objects/<resource>.json` (kubectl get -o json output, a list under "items"), `metrics/<query>.json`, `aws/*.json` and so on.
Reads are forgiving on purpose: a missing or corrupt file returns None (or an empty list), because one failed collection step must not stop the summary.
The missing input shows up as an "error"/"note" field in the module's own output and from there in the report's tool-notes section.

Every file under a snapshot or context folder is written through `write_private` and nothing else: it writes a temporary file next to the target,
syncs it and renames it over the target, so a reader sees the old file or the new one and never a truncated one, and the file is readable by
its owner only; missing folders on the way are created owner-only as well (`paths.ensure_private_dir`). `write_private_bytes` is the same for binary
content (the tool binaries `kubegap setup --install` places in `.tools/bin/`). `tests/test_snapshot_write.py` asserts that no other module in `lib/` writes files.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from . import paths


def write_private(path: Path, text: str, *, mode: int = 0o600) -> None:
    """Write `text` to `path` atomically with owner-only permissions. Creates missing parent folders.

    A temporary file `.<name>.<random>.tmp` in the same folder takes the content, is flushed and fsynced, gets `mode`, and replaces `path`
    in one rename. On any error the temporary file is removed and the error re-raised; `path` keeps whatever it held before.
    """
    write_private_bytes(path, text.encode("utf-8"), mode=mode)


def write_private_bytes(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    """`write_private` for bytes: the same temporary file, fsync, chmod and rename. `mode` 0o700 places an executable."""
    path = Path(path)
    paths.ensure_private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        try:
            f = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def remove_stale_temp(root: Path) -> int:
    """Remove `.<name>.<random>.tmp` files that a killed process left under `root`, so no directory walk mistakes one for data. Returns the count."""
    n = 0
    for p in Path(root).rglob(".*.tmp"):
        if p.is_file():
            with contextlib.suppress(OSError):
                p.unlink()
                n += 1
    return n


def load_json(path: Path) -> Any:
    """Parse one JSON file. Returns None when the file is missing or not valid JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def items(doc: Any) -> list:
    """The "items" list of a kubectl list document. Empty list for None, a non-dict or a document without items."""
    return (doc.get("items") or []) if isinstance(doc, dict) else []


_HELM_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)?(?: ([+-]\d{4}))?")  # Go time.String(): 2025-12-29 02:07:42.385466 +0900 KST
_ISO_IN_TEXT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?")


def parse_ts(s: Any) -> _dt.datetime | None:
    """An aware datetime from a timestamp the snapshot holds, else None.

    Reads the ISO 8601 forms kubectl and the inventory write (`2026-11-05T08:25:17Z`, `2026-11-05T17:25:17+09:00`, with a fraction), helm's
    `time.String()` form in `helm list` output (`2025-12-29 02:07:42.385466 +0900 KST`) and the first ISO timestamp inside a longer string (a log line).
    A timestamp without an offset is UTC, so every value compares with every other. Every summary module reads its timestamps through this one function.
    """
    if not s:
        return None
    s = str(s)
    try:
        d = _dt.datetime.fromisoformat(s)
    except ValueError:
        d = None
    if d is None:
        m = _HELM_TS_RE.match(s)
        if m:
            d = _dt.datetime.strptime(m.group(1) + (m.group(2) or "+0000"), "%Y-%m-%d %H:%M:%S%z")
        else:
            m = _ISO_IN_TEXT_RE.search(s)
            if not m:
                return None
            d = _dt.datetime.fromisoformat(m.group(0).replace(",", "."))
    return d.replace(tzinfo=_dt.UTC) if d.tzinfo is None else d


def taken_at(inv: dict | None) -> _dt.datetime:
    """When the snapshot was taken: `taken_at` of inventory.json, aware. Every age, window and expiry a summary module or a check computes measures
    from here, never from the wall clock, so summarizing the same snapshot a day later gives the same result (#165). An inventory without the key
    (only one a test builds) gets the wall clock."""
    return parse_ts((inv or {}).get("taken_at")) or _dt.datetime.now(_dt.UTC)


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


# the kinds lib/discover.py fetches before the dump-all step (its OBJECT_KINDS; tests/test_object_fields.py keeps the two equal): their files carry the short name
LEGACY_STEMS = {"cronjobs.batch": "cronjobs"}  # the spelling readers used before 2026-11-05 -> the file discovery writes
DISCOVERY_STEMS = frozenset(["configmaps", "cronjobs", "customresourcedefinitions", "daemonsets", "deployments", "namespaces", "nodes", "pods", "services", "statefulsets", "storageclasses"])


def objects(snap: Path, stem: str) -> list:
    """Items of `objects/<stem>.json` in the snapshot. `stem` is the resource file name, e.g. "deployments" or "bgppeers.metallb.io".

    The kinds discovery fetches (`lib/discover.py` KINDS) are written under the short name (`cronjobs`), the dump-all step writes every other
    non-core kind as `<name>.<group>` (`jobs.batch`). A reader names the short stem; a snapshot written before 2026-11-05 still has `cronjobs.batch.json`
    (discovery did not fetch CronJobs then), so a missing discovery stem falls back to the one `<stem>.<group>.json` file of that name, and the legacy spelling `cronjobs.batch` to `cronjobs`; nothing else falls back, so `pods.metrics.k8s.io` never reads `pods.json` (#124)."""
    p = snap / "objects" / f"{stem}.json"
    if not p.is_file():
        alt = p
        if stem in LEGACY_STEMS:
            alt = snap / "objects" / f"{LEGACY_STEMS[stem]}.json"
        elif stem in DISCOVERY_STEMS:
            cands = sorted((snap / "objects").glob(f"{stem}.*.json")) if (snap / "objects").is_dir() else []
            alt = cands[0] if len(cands) == 1 else p
        p = alt if alt.is_file() else p
    return items(load_json(p))

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
import math
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


def schema_of(snap: Path) -> int:
    """The format version inventory.json records (`schema`); 0 when the key or the file is missing (a snapshot from before the key existed)."""
    inv = load_json(Path(snap) / "inventory.json")
    v = inv.get("schema") if isinstance(inv, dict) else None
    return v if type(v) is int else 0  # not isinstance: True is an int to isinstance and would read as version 1


def check_schema(snap: Path) -> None:
    """Refuse a snapshot of another format version (#97). Raises SystemExit with the message; the readers behind it would otherwise fail on a missing key or,
    worse, read a renamed file as absent and judge nothing. There is no reading of an older version: it is collected again."""
    v = schema_of(snap)
    if v != paths.SCHEMA_VERSION:
        raise SystemExit(f"kubegap: snapshot {snap} has format version {v}; this kubegap reads version {paths.SCHEMA_VERSION}. A snapshot of another format version is not read: collect again with this version.")


def load_json(path: Path) -> Any:
    """Parse one JSON file. Returns None when the file is missing or not valid JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def items(doc: Any) -> list:
    """The "items" list of a kubectl list document. Empty list for None, a non-dict or a document without items."""
    return (doc.get("items") or []) if isinstance(doc, dict) else []


def event_count(e: dict) -> int:
    """How many times the Event happened: `count` for events written through the legacy recorder, `series.count` for events written through the
    events.k8s.io recorder (the scheduler's `Scheduled`, `FailedScheduling`, `Preempted`), which has no `count` in the core/v1 view and keeps the repeats in
    `series.count` (kubernetes/kubernetes pkg/apis/events/v1/conversion.go:40-42@v1.37.2; staging/src/k8s.io/client-go/tools/events/event_broadcaster.go:181@v1.37.2); 1 when neither is there."""
    c = e.get("count") or ((e.get("series") or {}).get("count")) or 1
    return int(c) if isinstance(c, (int, float)) else 1


# ---------- metrics/<query id>.json, written by lib/collection/prom.run_queries: {"ok": true, "resultType", "result": [...]} or {"ok": false, "error": ...} ----------
# Twenty-one private readers of this file in fifteen summary modules disagreed on whether to look at `ok` and whether to drop NaN (#150). This is the one reading:
# a query that did not run has no rows, and a value Prometheus could not compute is not a value.


def metric_doc(snap: Path, qid: str) -> dict | None:
    """The whole result document of one query, `ok` and `error` included; None when the query was not run (lib/judgement/evaluate reads the error)."""
    doc = load_json(snap / "metrics" / f"{qid}.json")
    return doc if isinstance(doc, dict) else None


def metric_result(snap: Path, qid: str) -> list[dict]:
    """The `result` rows of a query that ran (`{"metric": {...}, "value": [ts, "text"]}` each); empty when it failed or was not run."""
    doc = metric_doc(snap, qid)
    return (doc.get("result") or []) if doc and doc.get("ok") else []


def metric_sample(row: dict) -> float | None:
    """The sample of one result row exactly as Prometheus wrote it, NaN and infinities included; None when the row has no readable sample. For the
    evaluator and the diff, whose rules say themselves what a NaN means (`value == value` in a check expression)."""
    try:
        return float(row["value"][1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def metric_value(row: dict) -> float | None:
    """The sample of one result row as a measured number: None when the row has none or it is NaN or infinite, which a summary cannot report."""
    v = metric_sample(row)
    return None if v is None or math.isnan(v) or math.isinf(v) else v


def metric_rows(snap: Path, qid: str) -> list[tuple[dict, float]]:
    """(labels, value) per result row of a query that ran, rows without a usable value left out."""
    out = []
    for row in metric_result(snap, qid):
        v = metric_value(row)
        if v is not None:
            out.append((row.get("metric") or {}, v))
    return out


def metric_by(snap: Path, qid: str, *keys: str) -> dict:
    """The rows of a query keyed by label: `{label value: sample}` for one key, `{(value, value, ...): sample}` for several; a row missing one of the
    labels is left out (it cannot be addressed)."""
    out: dict = {}
    for lab, v in metric_rows(snap, qid):
        vals = tuple(lab.get(k) for k in keys)
        if any(x is None for x in vals):
            continue
        out[vals[0] if len(keys) == 1 else vals] = v
    return out


def series_present(snap: Path) -> dict[str, int] | None:
    """metrics/series-present.json (lib/collection/prom.record_series_present): metric name → series count at collection time, 0 for a name Prometheus has no series of.
    None when the file was not written."""
    doc = load_json(snap / "metrics" / "series-present.json")
    return doc.get("names") if isinstance(doc, dict) and isinstance(doc.get("names"), dict) else None


def node_os_text(snap: Path, node: str) -> str | None:
    """`logs/node/<node>/os.txt`, the node script's output (collectors/core/node-os.sh), or None when the node was not read."""
    path = snap / "logs" / "node" / node / "os.txt"
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def metric_sum(snap: Path, qid: str) -> float | None:
    """The sum of every row's value; None when the query has no rows (a series nobody scrapes is not a zero)."""
    rows = metric_rows(snap, qid)
    return sum(v for _, v in rows) if rows else None


def metric_scalar(snap: Path, qid: str) -> float | None:
    """The value of the first row of a query that returns one series (a sum, a ratio); None without one."""
    rows = metric_rows(snap, qid)
    return rows[0][1] if rows else None


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


_READ: dict[str, set[str]] = {}  # str(snapshot folder) -> the stems `objects()` was asked for in this process; summarize reports their status (#160)


def objects(snap: Path, stem: str) -> list:
    """Items of `objects/<stem>.json` in the snapshot. `stem` is the resource file name, e.g. "deployments" or "bgppeers.metallb.io".

    The kinds discovery fetches (`lib/collection/discover.py` OBJECT_KINDS) are written under the short name (`cronjobs`), the dump-all step writes every other
    non-core kind as `<name>.<group>` (`jobs.batch`), and a reader spells the file name exactly: nothing falls back, so `pods.metrics.k8s.io` never
    reads `pods.json` (#124). A missing or unreadable file gives an empty list, and the stem is recorded so `object_files()` can say why the file is
    missing: a kind the cluster does not serve is normal, a kind it serves without a file of that name is a reader's spelling mistake (#160)."""
    _READ.setdefault(str(snap), set()).add(stem)
    return items(load_json(snap / "objects" / f"{stem}.json"))


def forget_reads(snap: Path) -> None:
    """Start the record of `objects()` reads afresh for this snapshot (summarize calls it first, so a rerun in one process reports this run only)."""
    _READ.pop(str(snap), None)


def dump_record(snap: Path) -> dict | None:
    """The `objects.dump-all` step record of collect-result.json: `{kinds, items, written[], served[], fetched_by_discovery[], failed{}, excluded[], not_permitted[], discovery_error}`
    (lib/collection/collect.py dump_all). None when the snapshot has none (the step did not run)."""
    cr = load_json(snap / "collect-result.json") or {}
    rec = ((cr.get("core") or {}).get("steps") or {}).get("objects.dump-all") if isinstance(cr, dict) else None
    return rec if isinstance(rec, dict) else None


OBJECT_FILE_STATUS = {
    "ok": "the file is there (an empty item list means the cluster has none)",
    "not-served": "the cluster does not serve this kind",
    "excluded": "excluded from collection",
    "denied": "the ClusterRole does not grant list on this kind",
    "failed": "the kubectl get or the scrub failed (the dump-all record carries the error)",
    "unlisted": "the cluster serves this kind but the snapshot has no file of that name",
    "no-record": "the snapshot has no dump-all record, or its API discovery failed",
}


def object_file_status(snap: Path, stem: str, rec: dict | None) -> str:
    """Why `objects/<stem>.json` is or is not in the snapshot, one of OBJECT_FILE_STATUS, judged against `rec`, the snapshot's `dump_record`.

    `not-served` is the normal reason for a missing file: a CRD that is not installed (no Karpenter on k3s), and a check that reads it skips as
    "not served". `unlisted` is a defect in kubegap: `kubectl api-resources` listed the kind, nothing excluded or denied it, and still no file of that
    name exists, so the reader's stem and the file name disagree (#124 found CronJob readers opening `cronjobs.batch.json` while discovery wrote
    `cronjobs.json`, and every CronJob check passed on an empty list). A stem is served when it is a full name in `served` or the resource name of
    one (`jobs` for `jobs.batch`): the file of a discovery kind carries the short name, every other file the full name, so either spelling of a served
    kind without a file is `unlisted`. A `kubectl api-resources` that failed leaves `served` empty with `discovery_error` set; nothing can be judged then."""
    if (snap / "objects" / f"{stem}.json").is_file():
        return "ok"
    if rec is None or (rec["discovery_error"] and not rec["served"]):
        return "no-record"
    if stem in rec["excluded"]:
        return "excluded"
    if stem in rec["not_permitted"]:
        return "denied"
    if stem in rec["failed"]:
        return "failed"
    if stem in rec["served"] or stem in {str(full).split(".", 1)[0] for full in rec["served"]}:
        return "unlisted"
    return "not-served"


def object_files(snap: Path) -> dict[str, str]:
    """Stem -> status for every stem a reader asked `objects()` for on this snapshot in this process, sorted; summarize writes it to `collection.object_files`."""
    rec = dump_record(snap)
    return {stem: object_file_status(snap, stem, rec) for stem in sorted(_READ.get(str(snap), ()))}


def missing_reason(stem: str, status: str) -> str:
    """The skip reason of a check whose object file is missing: `objects/<stem>.json missing: <why>`."""
    return f"objects/{stem}.json missing: {OBJECT_FILE_STATUS.get(status, status)}"

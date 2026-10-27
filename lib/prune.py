"""Remove old snapshot folders of one context (`kubegap prune`).

A full snapshot is around 40 MB, so daily runs fill a disk within months. Retention is counted per mode: the newest N complete daily
snapshots and the newest M complete full snapshots stay. The newest complete snapshot of each mode always stays, whatever N and M say,
because it is the baseline the next run of that mode is diffed against (`paths.previous_snapshot`). Incomplete snapshots (interrupted
collections) are removed unless their run.log was written in the last 10 minutes, which means a collection is still running.

Only folders named like a snapshot (`paths.is_snapshot_name`) are touched; files next to them in the context folder (setup.json,
history.csv, node-access.json) stay.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

IN_PROGRESS_SECONDS = 600  # same window `kubegap collect` uses to refuse a second collection


@dataclass
class Plan:
    keep: list[Path] = field(default_factory=list)
    remove: list[Path] = field(default_factory=list)
    reasons: dict[Path, str] = field(default_factory=dict)


def retention(cfg_value, keep_daily: int | None, keep_full: int | None) -> tuple[int | None, int | None]:
    """Flags win over `retention: {keep_daily, keep_full}` in config.yaml. None = that mode is not pruned."""
    r = cfg_value if isinstance(cfg_value, dict) else {}
    d = keep_daily if keep_daily is not None else r.get("keep_daily")
    f = keep_full if keep_full is not None else r.get("keep_full")
    for name, v in (("keep_daily", d), ("keep_full", f)):
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
            raise ValueError(f"retention {name} must be a non-negative integer, got {v!r}")
    return d, f


def _in_progress(snap: Path, now: float) -> bool:
    rl = snap / "run.log"
    return rl.is_file() and now - rl.stat().st_mtime < IN_PROGRESS_SECONDS


def plan(context_dir: Path, keep_daily: int | None, keep_full: int | None, now: float | None = None) -> Plan:
    """Decide which snapshot folders to remove. Nothing is deleted here."""
    now = time.time() if now is None else now
    keep_n = {"daily": keep_daily, "full": keep_full}
    p = Plan()
    if not context_dir.is_dir():
        return p
    snaps = sorted(s for s in context_dir.iterdir() if s.is_dir() and paths.is_snapshot_name(s.name))
    seen = dict.fromkeys(paths.MODES, 0)
    for s in reversed(snaps):  # newest first
        mode = paths.snapshot_mode(s)
        if paths.is_incomplete(s):
            if _in_progress(s, now):
                p.keep.append(s)
                p.reasons[s] = "collection in progress"
            else:
                p.remove.append(s)
                p.reasons[s] = "incomplete"
            continue
        seen[mode] += 1
        n = keep_n[mode]
        if n is None:
            p.keep.append(s)
            p.reasons[s] = f"{mode}: no retention set"
        elif seen[mode] == 1:
            p.keep.append(s)
            p.reasons[s] = f"latest {mode} (comparison baseline)"
        elif seen[mode] <= n:
            p.keep.append(s)
            p.reasons[s] = f"{mode} {seen[mode]}/{n}"
        else:
            p.remove.append(s)
            p.reasons[s] = f"{mode} beyond keep {n}"
    p.keep.reverse()
    p.remove.reverse()
    return p


def folder_size(path: Path) -> int:
    total = 0
    for f in path.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def apply(p: Plan) -> int:
    """Delete the folders in the plan. Returns bytes freed."""
    freed = 0
    for s in p.remove:
        freed += folder_size(s)
        shutil.rmtree(s)
    return freed

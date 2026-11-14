"""A daily run keeps less on disk. Once it is judged and compared, the raw material is deleted: the objects, the events and whatever log files
are left. What stays is what the report and the next run read: the inventory, the summary, the findings, the comparison, the metric results
(numbers), and objects-digest.json, the hashes the next comparison needs. No agent opens a raw object of a daily run: there is none.

A full run keeps everything; the analysis of a full report opens the raw files.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..foundations import paths
from ..foundations.snapshot import write_private
from . import diff as _diff

RAW = ("objects", "events.json", "logs")  # the folders and files a daily run deletes after `diff`


def slim(snap: Path) -> list[str]:
    """Delete the raw material of a daily snapshot, after writing the digest that stands in for objects/. Returns what was removed. A full
    snapshot is left alone and gives []."""
    if paths.snapshot_mode(snap) != "daily":
        return []
    if (snap / "objects").is_dir():
        write_private(snap / _diff.DIGEST_FILE, json.dumps(_diff.object_digest(snap), ensure_ascii=False))
    gone = []
    for name in RAW:
        p = snap / name
        if p.is_dir():
            shutil.rmtree(p)
            gone.append(name + "/")
        elif p.is_file():
            p.unlink()
            gone.append(name)
    return gone

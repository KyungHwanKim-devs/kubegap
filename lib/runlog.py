"""run.log: records every executed command with its timing and exit code.

The report appendix ("every command and query that ran, and each collector's failures and skip reasons") is built from this file.
Format is one JSON object per line (JSON Lines), which is convenient both for `tail -f` and for re-reading in code.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
import threading
from pathlib import Path
from typing import Any


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


class RunLog:
    def __init__(self, path: Path | None, echo: bool = False):
        self.path = path
        self.echo = echo
        self._lock = threading.Lock()  # collectors run in parallel threads; each JSON line must land whole
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, kind: str, **fields: Any) -> None:
        rec = {"t": _now(), "kind": kind, **fields}
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self._lock:
            if self.path is not None:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            if self.echo:
                print(line, file=sys.stderr)

    # Named helpers for the common kinds. The kind values are read as-is by summarize/evaluate/report.
    def meta(self, **fields: Any) -> None:
        self.write("meta", **fields)

    def command(self, id: str, cmd: list[str] | str, code: int | None, seconds: float, out_path: str | None = None, timed_out: bool = False, error: str | None = None, collector: str | None = None) -> None:
        self.write("command", id=id, collector=collector, cmd=cmd, code=code, seconds=round(seconds, 3), out=out_path, timed_out=timed_out, error=error)

    def skip(self, id: str, reason: str, collector: str | None = None) -> None:
        self.write("skip", id=id, collector=collector, reason=reason)

    def note(self, message: str, **fields: Any) -> None:
        self.write("note", message=message, **fields)

    def stage(self, name: str, status: str, **fields: Any) -> None:
        """Start/end of a pipeline stage (setup/discover/collect/summarize/evaluate)."""
        self.write("stage", name=name, status=status, **fields)


def read_runlog(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"kind": "unparsed", "raw": line})
    return out

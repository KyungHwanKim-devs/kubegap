"""External command execution. Timeouts and failures come back as a result object instead of an exception.

Collectors run dozens of kubectl/aws/curl commands, and one failure must not stop the rest.
So this function never raises; the caller checks `result.ok`, records it in run.log and moves on.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .runlog import RunLog

DEFAULT_TIMEOUT = 60

# Where setup puts tools it downloaded itself (the install path when brew is missing or fails). Prepended to PATH.
# Default is `.tools/` inside the repo. Override with $KUBEGAP_TOOLS_DIR (e.g. container validation, so binaries for another OS do not mix into the same repo).
TOOLS_DIR = Path(os.environ.get("KUBEGAP_TOOLS_DIR") or (Path(__file__).resolve().parent.parent / ".tools")).expanduser()
TOOLS_BIN = TOOLS_DIR / "bin"
if str(TOOLS_BIN) not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = str(TOOLS_BIN) + os.pathsep + os.environ.get("PATH", "")


@dataclass
class Result:
    cmd: list[str]
    code: int | None = None  # None = could not run at all (command missing, etc.) or timed out
    stdout: str = ""
    stderr: str = ""
    seconds: float = 0.0
    timed_out: bool = False
    error: str | None = None  # why it could not run (FileNotFoundError, etc.)
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.timed_out and self.error is None


def which(name: str) -> str | None:
    return shutil.which(name)


def run(
    cmd: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    env: dict | None = None,
    cwd: Path | None = None,
    stdin: str | None = None,
    id: str | None = None,
    log: RunLog | None = None,
    out_path: Path | None = None,
    collector: str | None = None,
) -> Result:
    """Run a command. If `out_path` is given, stdout is saved to that file (only on success).

    If `id` and `log` are given, one line is written to run.log. The saved path is recorded relative to the
    snapshot folder so the LLM can open it directly from the report appendix.
    """
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    t0 = time.monotonic()
    res = Result(cmd=list(cmd))
    try:
        cp = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout, env=full_env, cwd=str(cwd) if cwd else None, input=stdin, errors="replace")
        res.code, res.stdout, res.stderr = cp.returncode, cp.stdout, cp.stderr
    except subprocess.TimeoutExpired as e:
        res.timed_out = True
        res.stdout = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        res.stderr = (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        res.error = f"timeout after {timeout}s"
    except FileNotFoundError:
        res.error = f"command not found: {cmd[0]}"
    except OSError as e:
        res.error = f"{type(e).__name__}: {e}"
    res.seconds = time.monotonic() - t0

    rel_out = None
    if out_path is not None and res.ok:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(res.stdout, encoding="utf-8")
        rel_out = str(out_path)
        if log is not None and log.path is not None:
            with contextlib.suppress(ValueError):
                rel_out = str(out_path.relative_to(log.path.parent))
    if log is not None and id is not None:
        log.command(id=id, cmd=res.cmd, code=res.code, seconds=res.seconds, out_path=rel_out, timed_out=res.timed_out, error=res.error or (res.stderr.strip()[-500:] or None if not res.ok else None), collector=collector)
    return res

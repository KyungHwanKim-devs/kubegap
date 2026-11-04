"""Paths and snapshot folder conventions.

Snapshots accumulate under `snapshots/<kube context>/<YYYY-MM-DDTHH-MM-SS>/`.
They are split per context because a user may audit several clusters (e.g. an EKS cluster and a small k3s cluster)
from the same machine, and "compare with the last run" must only compare the same cluster.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import os
import re
import stat
import sys
import threading
from pathlib import Path

# Even when scripts/kubegap is invoked through a symlink (~/.claude/skills/kubegap), resolve() finds the real repo location.
ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "scripts"
LIB_DIR = ROOT / "lib"
RUBRIC_DIR = ROOT / "rubric"
PROFILES_DIR = RUBRIC_DIR / "profiles"
COLLECTORS_DIR = ROOT / "collectors"


def collect_steps() -> list[tuple[str, dict]]:
    """(collector folder name, step) for every step of collectors/*/collect.yaml, folders sorted: the one walk lib/nodecommands and lib/podmetrics share."""
    from . import yamlite  # yamlite imports nothing from lib; the lazy import keeps this module free of it at import time

    return [(f.parent.name, st) for f in sorted(COLLECTORS_DIR.glob("*/collect.yaml")) for st in (yamlite.load_file(f) or []) if isinstance(st, dict)]


SIGNATURES_DIR = ROOT / "signatures"
TEMPLATES_DIR = ROOT / "templates"
# Data and personal config live outside the skill folder (~/.kubegap/) so that cluster data and AWS profiles do not accumulate in the skill repository. The old location (inside the skill folder) is still read for compatibility.
USER_DIR = Path(os.environ.get("KUBEGAP_HOME") or (Path.home() / ".kubegap")).expanduser()
DEFAULT_SNAPSHOTS_ROOT = USER_DIR / "snapshots"
LEGACY_SNAPSHOTS_ROOT = ROOT / "snapshots"
DEFAULT_CONFIG = (USER_DIR / "config.yaml") if (USER_DIR / "config.yaml").is_file() or not (ROOT / "config.yaml").is_file() else ROOT / "config.yaml"

_TS_FMT = "%Y-%m-%dT%H-%M-%S"

_warned_open_dirs: set[Path] = set()
_warn_lock = threading.Lock()


def ensure_private_dir(path: Path, base: Path | None = None) -> Path:
    """Create `path` and its missing parents readable by the owner only (mode 0700) and return it.

    Every missing component is created one by one with 0700: `Path.mkdir(mode=..., parents=True)` would give the mode to the last folder
    only and leave the parents at the umask default. Components that already exist are never chmod-ed, the user owns that decision; instead,
    each existing component below `base` (USER_DIR by default) that other users can read gets one warning on stderr per process. A path
    outside `base` is created the same way but nothing above it is inspected, so a snapshots root under /tmp does not warn about /tmp.
    """
    path = Path(path)
    base = Path(base) if base is not None else USER_DIR
    try:
        rel = path.resolve().relative_to(base.resolve())
        chain = [base, *(base / p for p in (Path(*rel.parts[: i + 1]) for i in range(len(rel.parts))))]
    except ValueError:
        try:  # a symlink inside base (snapshots -> a shared disk) resolves outside it; the unresolved spelling still tells which folders to inspect
            rel = path.relative_to(base)
            chain = [base, *(base / p for p in (Path(*rel.parts[: i + 1]) for i in range(len(rel.parts))))]
        except ValueError:
            chain = [path]
            while not chain[0].parent.exists() and chain[0].parent != chain[0]:
                chain.insert(0, chain[0].parent)
    for d in chain:
        if d.is_dir():
            mode = stat.S_IMODE(d.stat().st_mode)
            if mode & 0o077:
                key = d.resolve()
                with _warn_lock:
                    first = key not in _warned_open_dirs
                    _warned_open_dirs.add(key)
                if first:
                    print(f"kubegap: warning: {d} is readable by other users (mode {mode:04o}); chmod 700 it if that is not intended", file=sys.stderr)
            continue
        with contextlib.suppress(FileExistsError):  # another thread created it in between
            d.mkdir(mode=0o700)
        if not d.is_dir():
            raise FileExistsError(f"{d} exists and is not a directory")
    return path


_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}$")


def read_version(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def rubric_version() -> str:
    return read_version(RUBRIC_DIR / "version")


def signatures_version() -> str:
    return read_version(SIGNATURES_DIR / "version")


def safe_name(name: str) -> str:
    """Make a context name usable as a folder name (for things like `arn:aws:eks:...`)."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "unknown-context"


def snapshots_root(override: str | os.PathLike | None = None, config_value: str | None = None) -> Path:
    """Priority: --snapshots-root > $KUBEGAP_SNAPSHOTS > snapshots_root in config > ~/.kubegap/snapshots (or the old location kubegap/snapshots when the new one is absent and the old one has data)."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("KUBEGAP_SNAPSHOTS")
    if env:
        return Path(env).expanduser().resolve()
    if config_value:
        return Path(config_value).expanduser().resolve()
    if not DEFAULT_SNAPSHOTS_ROOT.is_dir() and LEGACY_SNAPSHOTS_ROOT.is_dir() and any(LEGACY_SNAPSHOTS_ROOT.iterdir()):
        return LEGACY_SNAPSHOTS_ROOT
    return DEFAULT_SNAPSHOTS_ROOT


def context_root(context: str, root: Path | None = None) -> Path:
    return (root or snapshots_root()) / safe_name(context)


def new_snapshot_dir(context: str, root: Path | None = None, now: _dt.datetime | None = None) -> Path:
    """Create a new snapshot folder and return its path. Called twice in the same second, it appends `-2`, `-3`."""
    now = now or _dt.datetime.now()
    base = context_root(context, root)
    ensure_private_dir(base, base=root or snapshots_root())
    stamp = now.strftime(_TS_FMT)
    n = 1
    while True:  # the final mkdir is the claim on the name: two runs started in the same second get different folders
        path = base / (stamp if n == 1 else f"{stamp}-{n}")
        try:
            path.mkdir(mode=0o700)
            return path
        except FileExistsError:
            n += 1


def list_snapshots(context: str, root: Path | None = None) -> list[Path]:
    """Oldest first. Snapshots without `report.md` (failed runs) are included."""
    base = context_root(context, root)
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))


def is_incomplete(snap: Path) -> bool:
    """A snapshot where collect did not finish (the INCOMPLETE marker file remains). summarize, evaluate and diff warn about it and exclude it from latest selection."""
    return (snap / "INCOMPLETE").is_file() or not (snap / "inventory.json").is_file()  # a folder cut off during detection (no inventory.json) also counts as incomplete


MODES = ("daily", "full")
DEFAULT_MODE = "daily"


def snapshot_mode(snap: Path) -> str:
    """Collection mode of a snapshot: the `MODE` marker file written by collect (`daily` or `full`). Snapshots from before modes existed have no marker and count as full."""
    try:
        m = (snap / "MODE").read_text(encoding="utf-8").strip()
    except OSError:
        return "full"
    return m if m in MODES else "full"


def latest_snapshot(context: str, root: Path | None = None, *, allow_incomplete: bool = False, mode: str | None = None) -> Path | None:
    """Most recent complete snapshot of the context; with `mode`, the most recent one collected in that mode (daily compares with daily, full with full)."""
    snaps = [s for s in list_snapshots(context, root) if (allow_incomplete or not is_incomplete(s)) and (mode is None or snapshot_mode(s) == mode)]
    return snaps[-1] if snaps else None


def previous_snapshot(current: Path) -> Path | None:
    """The snapshot just before `current` in the same context folder **and the same mode**. A daily run is compared with the previous daily run, a full run with the previous full run: a daily snapshot lacks the inputs of a full one, so comparing across modes would report every full-only finding as "resolved"."""
    mode = snapshot_mode(current)
    siblings = sorted(p for p in current.parent.iterdir() if p.is_dir() and not p.name.startswith("."))
    try:
        i = siblings.index(current)
    except ValueError:
        return None
    for prev in reversed(siblings[:i]):
        if not is_incomplete(prev) and snapshot_mode(prev) == mode:  # an incomplete collection cannot serve as a comparison baseline
            return prev
    return None


def resolve_snapshot(spec: str, context: str | None, root: Path | None = None, mode: str | None = None) -> Path:
    """Resolve the `--snapshot <date>` argument to an actual folder.

    Accepted forms:
    - an existing path (absolute or relative)
    - `latest`: the most recent snapshot of that context (with `mode`: the most recent one of that mode)
    - a full folder name (`2026-10-24T22-10-05`) or a date prefix (`2026-10-24`): if the prefix matches several, the most recent one
    """
    p = Path(spec).expanduser()
    if p.is_dir():
        return p.resolve()
    if context is None:
        raise FileNotFoundError(f"snapshot not found: {spec} (context unknown too)")
    snaps = list_snapshots(context, root)
    if not snaps:
        raise FileNotFoundError(f"no snapshots for context {context!r} ({context_root(context, root)})")
    if spec == "latest":
        complete = [s for s in snaps if not is_incomplete(s) and (mode is None or snapshot_mode(s) == mode)]
        if not complete and mode:
            raise FileNotFoundError(f"no complete {mode} snapshot for context {context!r}. Available: {', '.join(f'{s.name} ({snapshot_mode(s)})' for s in snaps[-5:])}")
        return (complete or snaps)[-1]
    matches = [s for s in snaps if s.name == spec or s.name.startswith(spec)]
    if not matches:
        raise FileNotFoundError(f"snapshot {spec!r} not found in context {context!r}. Available: {', '.join(s.name for s in snaps[-5:])}")
    return matches[-1]


def is_snapshot_name(name: str) -> bool:
    """Treat `2026-10-24T22-10-05`, or `2026-10-24T22-10-05-2` with a same-second collision suffix, as a snapshot folder name."""
    return bool(_TS_RE.match(name[:19])) and (len(name) == 19 or name[19] == "-")

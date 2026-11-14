"""Collection units: the pieces of a cluster a mode chooses to read (collectors/units.yaml).

A mode is the set of units that name it. A step of a collect.yaml belongs to one unit (`unit:`); a check that cannot be judged without a
unit says so (`needs:`). Code that has to behave differently when something is not collected asks `collected(snap_or_mode, unit)`; nothing
asks which mode it is. The declarations also carry the sentences that tell a user what a mode reads and what it leaves out, so the
documentation and the report are printed from the same file the collection obeys.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import paths, yamlite

FILE = paths.COLLECTORS_DIR / "units.yaml"
SENSITIVITIES = ("low", "config", "logs", "node", "cloud", "secret-adjacent")
FIELDS = {"id", "reads", "keeps", "drops", "ko", "sensitivity", "modes", "platforms", "full_only_because", "unseen"}


@lru_cache(maxsize=1)
def _load() -> tuple[dict, ...]:
    return tuple(u for u in (yamlite.load_file(FILE) or []) if isinstance(u, dict))


def units() -> list[dict]:
    return list(_load())


def ids() -> list[str]:
    return [u["id"] for u in _load()]


def get(unit: str) -> dict:
    for u in _load():
        if u["id"] == unit:
            return u
    raise KeyError(f"no collection unit named {unit!r} in {FILE.name} (units: {', '.join(ids())})")


def of_mode(mode: str) -> frozenset[str]:
    """The units a mode collects."""
    return frozenset(u["id"] for u in _load() if mode in (u.get("modes") or []))


def modes_of(unit: str) -> list[str]:
    return list(get(unit).get("modes") or [])


def of_snapshot(snap: Path) -> frozenset[str]:
    """The units the mode of this snapshot collects."""
    return of_mode(paths.snapshot_mode(snap))


def collected(where: Path | str, unit: str) -> bool:
    """Whether `unit` is collected in a mode (given by name) or was in the run that made a snapshot (given by its folder)."""
    get(unit)  # a misspelt unit is an error, not a quiet False
    return unit in (of_mode(where) if isinstance(where, str) else of_snapshot(where))


def missing(needs: list[str] | None, mode: str) -> list[str]:
    """Of the units a check needs, those the mode does not collect."""
    have = of_mode(mode)
    return [n for n in needs or [] if n not in have]


def left_out(mode: str, platform: str | None = None) -> list[dict]:
    """The units a mode does not collect, in the file's order. With `platform`, only those that exist on it (a k3s cluster has no cloud account)."""
    return [u for u in _load() if mode not in (u.get("modes") or []) and (platform is None or not u.get("platforms") or platform in u["platforms"])]


TABLE = {
    "en": {"head": ["Unit", "What is read", "What is written to the snapshot", "What is read and not written", "Sensitivity", "Daily", "Full"], "yes": "yes", "no": "no", "nothing": "—"},
    "ko": {"head": ["수집 단위", "읽는 것", "스냅샷에 쓰는 것", "읽지만 쓰지 않는 것", "민감도", "daily", "full"], "yes": "모음", "no": "모으지 않음", "nothing": "—"},
}


def render_table(language: str) -> str:
    """The table of docs/DATA.md and docs/ko/DATA.md: what each unit reads, keeps and drops, and which mode collects it. Printed from the
    declarations the collection obeys, so the document cannot say something else (tests/test_units.py compares)."""
    t = TABLE[language]
    rows = []
    for u in _load():
        said = u.get("ko") or {} if language == "ko" else u
        cell = lambda k: str(said.get(k) or t["nothing"]).replace("|", "\\|")  # noqa: E731
        rows.append([f"`{u['id']}`", cell("reads"), cell("keeps"), cell("drops"), u["sensitivity"], *(t["yes"] if m in u["modes"] else t["no"] for m in paths.MODES)])
    lines = ["| " + " | ".join(t["head"]) + " |", "|" + "---|" * len(t["head"])]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows]) + "\n"


def validate() -> list[str]:
    """What is wrong with units.yaml and with the steps that name its units, one line each."""
    errs: list[str] = []
    seen: set[str] = set()
    for u in _load():
        uid = u.get("id")
        if not isinstance(uid, str) or not uid:
            errs.append(f"{FILE.name}: a unit has no id: {u}")
            continue
        if uid in seen:
            errs.append(f"{FILE.name}: {uid} is declared twice")
        seen.add(uid)
        extra = set(u) - FIELDS
        if extra:
            errs.append(f"{FILE.name}: {uid} has unknown fields {sorted(extra)}")
        for f in ("reads", "keeps"):
            if not (isinstance(u.get(f), str) and u[f].strip()):
                errs.append(f"{FILE.name}: {uid} needs `{f}`, a sentence")
            if not (isinstance(u.get("ko"), dict) and isinstance(u["ko"].get(f), str) and u["ko"][f].strip()):
                errs.append(f"{FILE.name}: {uid} needs `ko.{f}`, the same in Korean")
        if u.get("drops") and not (u.get("ko") or {}).get("drops"):
            errs.append(f"{FILE.name}: {uid} has `drops` and no `ko.drops`")
        if u.get("sensitivity") not in SENSITIVITIES:
            errs.append(f"{FILE.name}: {uid} sensitivity must be one of {SENSITIVITIES}")
        modes = u.get("modes")
        if not isinstance(modes, list) or not modes or any(m not in paths.MODES for m in modes):
            errs.append(f"{FILE.name}: {uid} modes must be a non-empty list of {paths.MODES}")
            continue
        if "daily" in modes and u.get("sensitivity") != "low":
            errs.append(f"{FILE.name}: {uid} is collected by the daily run and its sensitivity is {u.get('sensitivity')}; the daily run collects units of low sensitivity only")
        if "full" not in modes:
            errs.append(f"{FILE.name}: {uid} is not collected by the full run; the full run collects everything")
        if "daily" not in modes:
            if u.get("sensitivity") == "low" and not u.get("full_only_because"):
                errs.append(f"{FILE.name}: {uid} is of low sensitivity and left out of the daily run; `full_only_because` says why")
            un = u.get("unseen")
            if not (isinstance(un, dict) and all(isinstance(un.get(lang), str) and un[lang].strip() for lang in ("en", "ko"))):
                errs.append(f"{FILE.name}: {uid} is left out of the daily run; `unseen` says in en and ko what a reader cannot learn without it")
    for collector, st in paths.collect_steps():
        where = f"collectors/{collector}/collect.yaml: {st.get('id')}"
        if "modes" in st:
            errs.append(f"{where} has `modes`; a step names its `unit`, and the unit says which modes collect it")
        if st.get("unit") not in seen:
            errs.append(f"{where} must name its `unit`, one of {sorted(seen)} (got {st.get('unit')!r})")
        for a in st.get("adds") or []:
            if a not in seen:
                errs.append(f"{where}: `adds` names {a!r}, which is not a unit")
    return errs

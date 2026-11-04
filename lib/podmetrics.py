"""Metric names kubegap reads from a component's own /metrics, per version (#120).

Each `collectors/<area>/pod-metrics.yaml` lists, per logical key, the candidate metric names from the newest spelling to the oldest, the release
range in which the component emits each one (`since` inclusive, `before` exclusive, both optional) and the line that defines it in the
component's source at the tags that were read. A parser asks for the first candidate present in a parsed /metrics text (lib/promtext), so a
rename in a new release is one YAML entry and never a parser edit, and two spellings of one counter are never added together.

The tables are data, not code: tests/test_sources.py requires a `source:` on every name, checks that every name passes the step's `keep` filter
in collect.yaml, and that no parser spells a metric name outside its table.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from . import paths, yamlite


@cache
def table(area: str) -> list[dict]:
    """The entries of collectors/<area>/pod-metrics.yaml (an empty list when the area has none)."""
    p = paths.COLLECTORS_DIR / area / "pod-metrics.yaml"
    return list(yamlite.load_file(p) or []) if p.is_file() else []


def entry(area: str, key: str) -> dict:
    for e in table(area):
        if e.get("key") == key:
            return e
    raise KeyError(f"{area}/pod-metrics.yaml has no entry {key!r}")


def candidates(area: str, key: str, suffix: str = "") -> list[str]:
    """The metric names that may carry `key`, newest spelling first; `suffix` appends `_sum`/`_count` for histograms and summaries."""
    return [str(n["name"]) + suffix for n in entry(area, key).get("names") or []]


def pick(parsed: dict, area: str, key: str, suffix: str = "") -> str | None:
    """The first candidate name present in `parsed` (as a single value or a labeled series), else None."""
    single, labeled = parsed.get("single") or {}, parsed.get("labeled") or {}
    for name in candidates(area, key, suffix):
        if name in single or labeled.get(name):
            return name
    return None


def labeled(parsed: dict, area: str, key: str, suffix: str = "") -> list[tuple[dict, float]]:
    """The labeled rows of the first present candidate ([] when none); a value without labels counts as one row with empty labels."""
    name = pick(parsed, area, key, suffix)
    if name is None:
        return []
    rows = list((parsed.get("labeled") or {}).get(name) or [])
    if not rows and name in (parsed.get("single") or {}):
        rows = [({}, parsed["single"][name])]
    return rows


def single(parsed: dict, area: str, key: str, default=None, suffix: str = ""):
    """The unlabeled value of the first present candidate, else the sum of its labeled rows, else `default`."""
    name = pick(parsed, area, key, suffix)
    if name is None:
        return default
    if name in (parsed.get("single") or {}):
        return parsed["single"][name]
    return sum(v for _, v in (parsed.get("labeled") or {}).get(name) or [])


def present(parsed: dict, area: str, key: str) -> bool:
    return pick(parsed, area, key) is not None


def by_label(parsed: dict, area: str, key: str, label_keys: tuple[str, ...] | str) -> dict[str, float]:
    """Sum the first present candidate's rows per label value; `label_keys` names the label in each spelling (the first one a row carries wins)."""
    keys = (label_keys,) if isinstance(label_keys, str) else tuple(label_keys)
    out: dict[str, float] = {}
    for labels, v in labeled(parsed, area, key):
        k = next((labels[x] for x in keys if labels.get(x)), None) or "-"
        out[k] = out.get(k, 0) + v
    return out


def found(parsed: dict, area: str) -> dict[str, str | None]:
    """Which spelling each key of the area's table resolved to in `parsed` (None when absent): the report's evidence of the metrics schema a run saw."""
    return {str(e.get("key")): pick(parsed, area, str(e.get("key"))) for e in table(area)}


def _vt(v) -> tuple[int, ...]:
    return tuple(int(x) for x in str(v).split("."))


def floor_version(parsed: dict, area: str) -> str | None:
    """The highest `since` among the spellings present in `parsed`: the oldest release this text can come from, as far as the table knows."""
    best = None
    for e in table(area):
        for n in e.get("names") or []:
            name = str(n["name"])
            if n.get("since") and (name in (parsed.get("single") or {}) or (parsed.get("labeled") or {}).get(name)) and (best is None or _vt(n["since"]) > _vt(best)):
                best = str(n["since"])
    return best


def removed(parsed: dict, area: str, key: str) -> bool:
    """True when every spelling of `key` carries a `before` bound and another present name proves the text comes from a release at or past it:
    the component no longer emits the metric, which is not the same as a counter that has no series yet."""
    names = entry(area, key).get("names") or []
    if not names or any(not n.get("before") for n in names):
        return False
    floor = floor_version(parsed, area)
    return floor is not None and all(_vt(floor) >= _vt(n["before"]) for n in names)


def all_names(area: str) -> list[str]:
    return [str(n["name"]) for e in table(area) for n in e.get("names") or []]


def tables() -> dict[str, list[dict]]:
    """Every area that has a table, for the tests and the catalog."""
    return {p.parent.name: table(p.parent.name) for p in sorted(Path(paths.COLLECTORS_DIR).glob("*/pod-metrics.yaml"))}

"""The PromQL queries of collectors/*/metrics.yaml and the metric names each one reads, taken from its `source:` entries (#121, #122: one entry per
name, `<name>: <owner>/<repo> <file>:<line>@<tag> …`; entries that begin with `label` describe a label, not a name). Used by lib/collection/prom to ask Prometheus
which of those names have any series at all (metrics/series-present.json) and by lib/judgement/evaluate to tell "the situation did not occur" from "the series
does not exist" when a query comes back empty (#141). tests/test_sources.py reads the same list."""

from __future__ import annotations

import functools
import re

from . import paths

NAME = re.compile(r"^([A-Za-z_:][A-Za-z0-9_:]*):\s")


def queries() -> list[tuple[str, dict]]:
    """(collector folder name, query item) for every query of collectors/*/metrics.yaml, folders sorted."""
    from . import yamlite  # yamlite imports nothing from lib

    return [(f.parent.name, it) for f in sorted(paths.COLLECTORS_DIR.glob("*/metrics.yaml")) for it in (yamlite.load_file(f) or []) if isinstance(it, dict)]


def names_of(item: dict) -> list[str]:
    """The metric names a query's `source:` entries cite, in order, without duplicates. Empty for a query that reads `__name__` patterns only."""
    out: list[str] = []
    for e in item.get("source") or []:
        m = NAME.match(str(e))
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


@functools.cache
def names_by_query() -> dict[str, list[str]]:
    """query id → the names it reads, over every metrics.yaml."""
    return {it["id"]: names_of(it) for _, it in queries()}

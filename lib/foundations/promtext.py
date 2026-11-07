"""Parser for the Prometheus text exposition format (/metrics) — for the .prom files fetched by the pod-metrics and node steps.

parse(text) → {"single": {name: value}, "labeled": {name: [(label dict, value), …]}}. Histogram/summary _bucket, _sum and _count keep their names as-is (the consumer picks what it needs).
"""

from __future__ import annotations

import math
import re

LINE_RE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{([^}]*)\})?\s+([-+]?(?:[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|NaN|Inf|\+Inf|-Inf))(\s+\d+)?\s*$")
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')


def parse(text: str) -> dict:
    single: dict[str, float] = {}
    labeled: dict[str, list[tuple[dict, float]]] = {}
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        m = LINE_RE.match(ln)
        if not m:
            continue
        name, labels_txt, val = m.group(1), m.group(3), m.group(4)
        try:
            v = float(val)
        except ValueError:
            continue
        if math.isnan(v):  # NaN
            continue
        if labels_txt is None:
            single[name] = v
        else:
            labels = {k: bytes(val_, "utf-8").decode("unicode_escape") for k, val_ in LABEL_RE.findall(labels_txt)}
            labeled.setdefault(name, []).append((labels, v))
    return {"single": single, "labeled": labeled}


def sum_by(parsed: dict, name: str, keys: tuple[str, ...]) -> dict[tuple, float]:
    out: dict[tuple, float] = {}
    for labels, v in parsed["labeled"].get(name, []):
        k = tuple(labels.get(x) for x in keys)
        out[k] = out.get(k, 0.0) + v
    return out

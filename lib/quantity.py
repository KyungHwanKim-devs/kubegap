"""Kubernetes resource quantities and the small number helpers next to them: the one home for reading `500m`, `2Gi`, `1.5` into a number (#150).

Four summary modules carried their own quantity reader, each with a different unit table (one without Ti, one without the decimal K/M/G/T, one without
the milli suffix), and three more converted memory strings to MiB inline. The suffixes are the ones apimachinery's Quantity accepts
(kubernetes/kubernetes staging/src/k8s.io/apimachinery/pkg/api/resource/suffix.go:113-116, 128-130@v1.30.14: binary Ki/Mi/Gi/Ti/Pi/Ei, decimal
k/M/G/T/P/E, and `m` for a thousandth). `tests/test_helper_homes.py` fails on a unit table written anywhere else under lib/.
"""

from __future__ import annotations

# Longest suffix first, so `Mi` is tried before `M` and `m`.
_SUFFIXES: tuple[tuple[str, float], ...] = (
    ("Ki", 1024.0),
    ("Mi", 1024.0**2),
    ("Gi", 1024.0**3),
    ("Ti", 1024.0**4),
    ("Pi", 1024.0**5),
    ("Ei", 1024.0**6),
    ("k", 1e3),
    ("K", 1e3),  # not a Quantity suffix, but k3s and kubelet config files carry it, and the four readers accepted it
    ("M", 1e6),
    ("G", 1e9),
    ("T", 1e12),
    ("P", 1e15),
    ("E", 1e18),
    ("m", 1e-3),
)

MIB = 1024.0**2


def parse(v, default: float | None = 0.0) -> float | None:
    """A Kubernetes quantity as a plain number: CPU in cores, memory in bytes. `None`, an empty string and text that is not a quantity give `default`,
    0.0 unless the caller says otherwise, because a missing request is a request of nothing."""
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    for suffix, mul in _SUFFIXES:
        if s.endswith(suffix):
            try:
                return float(s[: -len(suffix)]) * mul
            except ValueError:
                return default
    try:
        return float(s)
    except ValueError:
        return default


def to_float(v, default: float | None = None) -> float | None:
    """`float(v)`, or `default` when `v` is None or not a number."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def to_int(v, default: int | None = 0) -> int | None:
    """`int(float(v))`, or `default` when `v` is None or not a number."""
    f = to_float(v)
    return int(f) if f is not None else default


def rounded(x, n: int = 3) -> float | None:
    """`round(x, n)` that lets None through, for a value a summary did not measure."""
    return None if x is None else round(x, n)

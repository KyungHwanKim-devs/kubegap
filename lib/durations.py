"""One reader of Go duration strings (`time.ParseDuration`): the form Kubernetes and its operators print in `metav1.Duration` fields and ConfigMap values.

The grammar is `[-+]?([0-9]*(\\.[0-9]*)?[a-z]+)+` with the units ns, us (or µs/μs), ms, s, m and h; `0` alone is allowed, a number without a unit is not
(golang/go src/time/format.go:1605-1614,1621-1718@go1.25.0: `unitMap`, `ParseDuration`). Karpenter's `expireAfter`/`consolidateAfter` also take `Never`
(the CRD pattern `^(([0-9]+(s|m|h))+)|(Never)$`, kubernetes-sigs/karpenter pkg/apis/v1/nodepool.go:65,213@v1.0.0); callers map that themselves. Before this module three copies accepted only `^\\d+[smh]$`
(`1h30m`, `3m0s`, `90m0s` fell through to None: a silent skip of the check that read them, #124 N-7/N-8).
"""

from __future__ import annotations

import re

_UNIT_S = {"ns": 1e-9, "us": 1e-6, "µs": 1e-6, "μs": 1e-6, "ms": 1e-3, "s": 1.0, "m": 60.0, "h": 3600.0}
_PART = re.compile(r"(\d+(?:\.\d*)?|\.\d+)(ns|us|µs|μs|ms|s|m|h)")
_WHOLE = re.compile(r"^[-+]?(?:(?:\d+(?:\.\d*)?|\.\d+)(?:ns|us|µs|μs|ms|s|m|h))+$")


def go_duration_s(text) -> float | None:
    """Seconds of a Go duration string, or None when the text is not one (empty, `Never`, a bare number other than 0, a day unit)."""
    s = str(text if text is not None else "").strip()
    if s in ("0", "+0", "-0"):
        return 0.0
    if not _WHOLE.match(s):
        return None
    sign = -1.0 if s.startswith("-") else 1.0
    return sign * sum(float(n) * _UNIT_S[u] for n, u in _PART.findall(s.lstrip("+-")))

"""Alertmanager's loaded configuration, as the `/api/v2/status` response carries it in `config.original` (the YAML text the server parsed; the
schema is `prometheus/alertmanager config/config.go`, cited per key in references/sources.md, #126).

One parser for the two readers (lib/summaries/observability.py and lib/summaries/stackhealth.py): until #126 stackhealth counted receivers, routes and inhibit rules
with regular expressions over the text, which do not know which section a line belongs to. The text is parsed with lib/foundations/yamlite; when yamlite
cannot read it (anchors, aliases and multi-document YAML are out of its subset by design) the readers say so and the checks that need the
structure skip instead of counting zero receivers.
"""

from __future__ import annotations

from . import yamlite


def parse(text: str | None) -> tuple[dict | None, str | None]:
    """(config, error): the mapping yamlite reads from the text, or None and the reason ("empty" or the parse error)."""
    if not text:
        return None, "empty"
    try:
        # Alertmanager serves Config.String(): yaml.Marshal of the loaded struct, and go-yaml folds plain scalars at 80 columns (a long `title:`
        # becomes two lines), which yamlite's load rejects; the folds are undone first.
        cfg = yamlite.load(yamlite.unfold_plain_scalars(text))
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if not isinstance(cfg, dict):
        return None, f"top level is {type(cfg).__name__}, not a mapping"
    return cfg, None


def receiver_kinds(cfg: dict) -> dict[str, list[str]]:
    """receiver name -> the integration kinds it configures (slack, email, ...), [] for a receiver with no *_configs (a null receiver)."""
    out: dict[str, list[str]] = {}
    for rcv in cfg.get("receivers") or []:
        if isinstance(rcv, dict):
            out[str(rcv.get("name"))] = [k.replace("_configs", "") for k in rcv if str(k).endswith("_configs") and rcv.get(k)]
    return out


def walk_routes(route: dict | None, depth: int = 0, acc: list | None = None) -> list[dict]:
    """The routing tree flattened, root first: receiver, matchers (`matchers`, or the old `match`/`match_re`), continue, group_by, repeat_interval."""
    acc = [] if acc is None else acc
    route = route or {}
    acc.append(
        {
            "depth": depth,
            "receiver": route.get("receiver"),
            "matchers": route.get("matchers") or route.get("match") or route.get("match_re"),
            "continue": route.get("continue"),
            "group_by": route.get("group_by"),
            "repeat_interval": route.get("repeat_interval"),
        }
    )
    for r in route.get("routes") or []:
        if isinstance(r, dict):
            walk_routes(r, depth + 1, acc)
    return acc


def referenced_receivers(cfg: dict) -> set[str]:
    """Every receiver a route names (the root route's default and every child route)."""
    return {str(r["receiver"]) for r in walk_routes(cfg.get("route")) if r.get("receiver")}


def has_time_intervals(cfg: dict) -> bool:
    """`time_intervals` (0.24+) or the older `mute_time_intervals` declared at the top level."""
    return bool(cfg.get("time_intervals") or cfg.get("mute_time_intervals"))

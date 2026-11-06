"""Metric names kubegap reads from a component's own /metrics, per version (#120).

Each `collectors/<area>/pod-metrics.yaml` lists, per logical key, the candidate metric names from the newest spelling to the oldest, the release
range in which the component emits each one (`since` inclusive, `before` exclusive, both optional) and the line that defines it in the
component's source at the tags that were read. A parser asks for the first candidate present in a parsed /metrics text (lib/promtext), so a
rename in a new release is one YAML entry and never a parser edit, and two spellings of one counter are never added together.

The tables are data, not code: tests/test_sources.py requires a `source:` on every name, checks that every name passes the step's `keep` filter
in collect.yaml, and that no parser spells a metric name outside its table.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from . import paths, yamlite
from .components import match_name
from .snapshot import items


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


def removed(parsed: dict, area: str, key: str, version: str | None = None) -> bool:
    """True when every spelling of `key` carries a `before` bound and the text is known to come from a release at or past it: by another present
    name's `since`, or by `version` (the component's image tag, which a fresh deployment whose counters have no series yet still carries).
    The component no longer emits the metric, which is not the same as a counter that has no series yet."""
    names = entry(area, key).get("names") or []
    if not names or any(not n.get("before") for n in names):
        return False
    floor = floor_version(parsed, area)
    v = re.match(r"v?(\d+\.\d+(?:\.\d+)?)", str(version or ""))
    if v and (floor is None or _vt(v.group(1)) > _vt(floor)):
        floor = v.group(1)
    return floor is not None and all(_vt(floor) >= _vt(n["before"]) for n in names)


def by_label_or_none(parsed: dict, area: str, key: str, label: str) -> dict[str, float] | None:
    """Like by_label for one label, but None when the present spelling carries no such label at all (a 1.x counter that dropped `reason`):
    a summary keyed by the wrong label would read as if the reasons had changed."""
    rows = labeled(parsed, area, key)
    if rows and not any(label in lab for lab, _ in rows):
        return None
    return by_label(parsed, area, key, label)


def all_names(area: str) -> list[str]:
    return [str(n["name"]) for e in table(area) for n in e.get("names") or []]


def tables() -> dict[str, list[dict]]:
    """Every area that has a table, for the tests and the catalog."""
    return {p.parent.name: table(p.parent.name) for p in sorted(Path(paths.COLLECTORS_DIR).glob("*/pod-metrics.yaml"))}


# ---------- where a pod-metrics step reads (#136) ----------


def pod_metrics_steps() -> list[tuple[str, dict]]:
    """(collector folder name, step) for every `type: pod-metrics` step of collectors/*/collect.yaml."""
    return [(folder, st) for folder, st in paths.collect_steps() if st.get("type") == "pod-metrics"]


def default_target(st: dict) -> dict:
    """The step's own namespace, selector and port: what every step read until #136, and the fallback when nothing is discovered or configured."""
    return {"namespace": st["namespace"], "selector": st["selector"], "port": int(st["port"]), "workload": None, "source": {"namespace": "default", "selector": "default", "port": "default"}}


def _discovered(objs: dict, disc: dict, default_port: int, default_namespace: str | None = None) -> dict | None:
    """The workload (kind and `namespace/name` glob of `discover:`) among the fetched objects, with its namespace, its pod selector (spec.selector.matchLabels)
    and the container port named as `port_names` says. When several workloads match (two installs, or a sibling such as loki-grafana next to grafana), the
    one in the step's default namespace is taken, else the first by kind order, namespace and name, and every match (every one running the `image:` hint when one does) is listed in `candidates` so the
    choice is visible; `components.<name>` in config.yaml is the override. A port named as `https_port_names` says marks a metrics endpoint served over
    TLS with authentication, which kubegap cannot read through the pod proxy or a node curl: the step then skips and says so instead of reading nothing, with the `https_note` of the block, which says what stands in for it. `container` limits the port search to that container when it exists."""
    kinds = disc.get("kind") or []
    kinds = [kinds] if isinstance(kinds, str) else list(kinds)
    names = disc.get("port_names") or []
    https_names = disc.get("https_port_names") or []
    matches: list[tuple[str, dict]] = []
    for kind in kinds:
        for o in sorted(items(objs.get(kind + "s")), key=lambda o: (o["metadata"].get("namespace") or "", o["metadata"]["name"])):
            if match_name(str(disc["name"]), o["metadata"].get("namespace") or "", o["metadata"]["name"]):
                matches.append((kind, o))
    if not matches:
        return None
    hint = disc.get("image")  # names can collide (any DaemonSet may be called x-speaker): when `image:` is set, a workload running that image, or selecting a label with that value for a mirrored image, goes first

    def hinted(o: dict) -> bool:
        spec = o.get("spec") or {}
        return any(hint in str(c.get("image")) for c in ((spec.get("template") or {}).get("spec") or {}).get("containers") or []) or hint in ((spec.get("selector") or {}).get("matchLabels") or {}).values()

    matches = [m for m in matches if hint and hinted(m[1])] or matches
    candidates = [f"{k} {o['metadata'].get('namespace') or ''}/{o['metadata']['name']}" for k, o in matches]
    kind, o = next(((k, o) for k, o in matches if (o["metadata"].get("namespace") or "") == default_namespace), matches[0])
    ns, name = o["metadata"].get("namespace") or "", o["metadata"]["name"]
    spec = o.get("spec") or {}
    labels = ((spec.get("selector") or {}).get("matchLabels")) or {}
    containers = ((spec.get("template") or {}).get("spec") or {}).get("containers") or []
    # `container:` names whose ports count, because a sidecar can use the same port name: metallb-frr.yaml names both frr-metrics:7473 and speaker:7472 `monitoring`, and frr-metrics comes first
    own = [c for c in containers if c.get("name") == disc.get("container")] or [c for c in containers if disc.get("container") and str(disc["container"]) in str(c.get("image"))]
    ports = [pt for c in (own or containers) for pt in (c.get("ports") or [])]
    port, port_source, https = default_port, "default", None
    for pt in ports:
        if pt.get("name") in names and pt.get("containerPort"):
            port, port_source = int(pt["containerPort"]), "discovered"
            break
    else:
        for pt in ports:
            if pt.get("name") in https_names and pt.get("containerPort"):
                https = int(pt["containerPort"])
                break
    out = {
        "namespace": ns,
        "selector": ",".join(f"{k}={v}" for k, v in sorted(labels.items())) or None,
        "port": port,
        "workload": f"{kind} {ns}/{name}",
        "candidates": candidates,
        "source": {"namespace": "discovered", "selector": "discovered" if labels else "default", "port": port_source},
    }
    if https is not None:
        out["skip"] = f"{kind} {ns}/{name} serves its metrics on port {https} ({next(pt.get('name') for pt in ports if pt.get('containerPort') == https)}), over TLS with authentication, which the pod proxy and the node curl cannot read"
        if disc.get("https_note"):
            out["skip"] += f"; {disc['https_note']}"
    return out


def discover_targets(objs: dict, cfg) -> dict[str, dict]:
    """`<collector>.<step id>` -> {namespace, selector, port, workload, source{namespace, selector, port}: discovered|config|default, skip?} for every pod-metrics step.
    Precedence per field: `components.<name>.{namespace, selector, metrics_port}` of config.yaml, then the workload found by the step's `discover:` block among
    `objs` (the Deployments, DaemonSets and StatefulSets discovery fetched), then the step's own values. `<name>` is the step's `component`, else its collector folder."""
    comps = (cfg or {}).get("components") if isinstance(cfg, dict) else None
    out: dict[str, dict] = {}
    for folder, st in pod_metrics_steps():
        key = f"{folder}.{st['id']}"
        tgt = default_target(st)
        disc = st.get("discover")
        if isinstance(disc, dict) and disc.get("name"):
            found = _discovered(objs, disc, int(st["port"]), st.get("namespace"))
            if found:
                tgt = found
                if found.get("source", {}).get("selector") == "default":
                    tgt["selector"] = st["selector"]
        conf = (comps or {}).get(st.get("component") or folder) if isinstance(comps, dict) else None
        if isinstance(conf, dict):
            for field in ("namespace", "selector"):
                if conf.get(field) not in (None, ""):
                    tgt[field] = str(conf[field])
                    tgt["source"][field] = "config"
            mp = conf.get("metrics_port")
            if mp not in (None, ""):
                if re.fullmatch(r"[1-9][0-9]{0,4}", str(mp)) and int(mp) <= 65535:
                    tgt["port"] = int(mp)
                    tgt["source"]["port"] = "config"
                    tgt.pop("skip", None)  # the user named a plain-HTTP port on purpose
                else:
                    tgt["source"]["port"] = f"{tgt['source']['port']} (config value {mp!r} ignored: not a port)"  # a config mistake must not abort discovery
        out[key] = tgt
    return out

"""Rubric loader. Reads checks.yaml, validates the schema, and resolves severity, thresholds and enablement from the platform (detected), the scale (asked) and config.yaml."""

from __future__ import annotations

import datetime as _dt
import functools as _functools
import json

from . import paths, yamlite

TYPES = ("metric", "object", "summary", "inventory", "absence", "aws", "llm", "signature")
SEVERITIES = ("critical", "high", "medium", "low", "info")
REQUIRED = ("id", "name", "area", "type", "severity_default", "why")
SCALES = ("small", "medium", "large")
# What a finding of the check is: a `state` the cluster is in now (a setting, a missing piece, a placement), or an `occurrence` counted over a
# window (events, log lines, restarts, failed deliveries), which may already be over. The report keeps what happened apart from what is wrong.
NATURES = ("state", "occurrence")
PLATFORM_FAMILIES = ("eks", "k3s", "other")


class RubricError(ValueError):
    pass


def platform_family(platform: str | None) -> str:
    """The platform file and the `platforms:` value a detected platform reads: RKE2 shares k3s (one binary, same datastore and node layout);
    everything that is neither EKS nor k3s is "other"."""
    if platform in ("k3s", "rke2"):
        return "k3s"
    return "eks" if platform == "eks" else "other"


def load_platform(platform: str | None) -> dict:
    """rubric/platforms/<family>.yaml: the targets a check must not judge on that platform and the component families it makes pointless."""
    fam = platform_family(platform)
    d = yamlite.load_file(paths.PLATFORMS_DIR / f"{fam}.yaml") or {}
    d["name"] = fam
    d.setdefault("exclude", {})
    d.setdefault("families_not_expected", [])
    return d


@_functools.lru_cache(maxsize=1)
def load_scales() -> dict:
    return yamlite.load_file(paths.RUBRIC_DIR / "scales.yaml") or {}


def guess_scale(nodes: int) -> str:
    """The scale used when nobody answered the question: by node count, with the limits of rubric/scales.yaml."""
    g = load_scales().get("guess_by_nodes") or {}
    if nodes <= int(g.get("small", 3)):
        return "small"
    return "medium" if nodes <= int(g.get("medium", 20)) else "large"


def resolve_scale(cfg: dict, answered: str | None, nodes: int) -> dict:
    """{name, source}. config.yaml `scale` wins, then the answer to the first-run question for this cluster, then the guess."""
    v = str(cfg.get("scale") or "").lower()
    if v in SCALES:
        return {"name": v, "source": "config.yaml"}
    v = str(answered or "").lower()
    if v in SCALES:
        return {"name": v, "source": "answered"}
    return {"name": guess_scale(nodes), "source": "guessed", "nodes": nodes}


def expected_families(scale: str, platform: dict) -> list[str]:
    fams = (load_scales().get("expected_families") or {}).get(scale) or []
    return [f for f in fams if f not in (platform.get("families_not_expected") or [])]


def severity_for(check: dict, scale: str) -> str:
    """The first-pass severity of a check at a scale. A check writes one level for every scale or one per scale."""
    v = check.get("severity_default")
    return v[scale] if isinstance(v, dict) else v


def applies(check: dict, platform: str | None, scale: str) -> str | None:
    """None when the check runs here, else why not. `platforms:` and `scales:` are optional; leaving one out means all."""
    fam = platform_family(platform)
    if check.get("platforms") and fam not in check["platforms"]:
        return f"not for platform {fam} (runs on: {', '.join(check['platforms'])})"
    if check.get("scales") and scale not in check["scales"]:
        return f"not expected at scale {scale} (expected at: {', '.join(check['scales'])})"
    if check.get("type") == "absence" and check.get("family") and check["family"] not in expected_families(scale, load_platform(platform)):
        return f"family {check['family']} is not expected at scale {scale} on platform {fam}"
    return None


def load_severity_rules() -> dict:
    p = paths.RUBRIC_DIR / "severity.yaml"
    return yamlite.load_file(p) if p.is_file() else {}


def load_known_issues() -> tuple[dict[str, list[dict]], list[str]]:
    """rubric/known-issues.yaml: {<check id>: [{issue, note}]}. The defects of kubegap itself that are open on the tracker, attached to the checks they affect, so a finding
    carries the issue number and the report's tool notes cite it instead of describing the defect again. The PR that closes an issue removes its line.
    Returns the table and a list of errors; a damaged file never stops an evaluation, it is reported like a check load error."""
    p = paths.RUBRIC_DIR / "known-issues.yaml"
    if not p.is_file():
        return {}, []
    try:
        data = yamlite.load_file(p) or {}
    except Exception as e:  # yamlite raises its own error type; whatever it is, the file is unusable and that is the whole message
        return {}, [f"rubric/known-issues.yaml: {type(e).__name__}: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("checks"), dict | type(None)):
        return {}, ["rubric/known-issues.yaml: expected a mapping with a `checks` mapping"]
    out: dict[str, list[dict]] = {}
    errors: list[str] = []
    for cid, entries in (data.get("checks") or {}).items():
        rows = []
        for e in entries if isinstance(entries, list) else [entries]:
            if not isinstance(e, dict) or e.get("issue") is None:
                errors.append(f"rubric/known-issues.yaml: {cid}: every entry needs `issue`")
                continue
            try:
                rows.append({"issue": int(e["issue"]), "note": str(e.get("note") or "").strip()})
            except (TypeError, ValueError):
                errors.append(f"rubric/known-issues.yaml: {cid}: issue {e.get('issue')!r} is not a number")
        if rows:
            out[str(cid)] = rows
    return out, errors


# The parts of a check that decide its verdict. Not here: the texts (rewording is not a rule change) and the gates `modes`, `platforms`, `scales`, `requires_tool`,
# whose effect is already visible in check_results.status (not-collected, disabled, tool-missing) and is classified by diff from that status.
RULE_HASH_KEYS = ("type", "inputs", "join_on", "join_any", "each", "cluster_level", "target", "rule", "exclude_transient")


def _hash_normal(v):
    """Numbers as float, so a rule written `1` and reloaded as `1.0` by another parser version keeps its hash; everything else as is."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, dict):
        return {str(k): _hash_normal(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_hash_normal(x) for x in v]
    return v


def rule_hash(check: dict, extra: str | None = None) -> str:
    """Twelve hex characters over the parts of a check that decide its verdict (RULE_HASH_KEYS). `extra` is mixed in for a check whose verdict lives elsewhere,
    as the signature check's does in signatures/catalog.yaml. `diff` compares the hash of both snapshots to tell a criteria change from a cluster change."""
    import hashlib

    body = {k: _hash_normal(check.get(k)) for k in RULE_HASH_KEYS if check.get(k) is not None}
    if extra:
        body["_extra"] = extra
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:12]


def catalog_hash() -> str:
    """sha256[:12] of signatures/catalog.yaml, the verdict source of the signature check."""
    import hashlib

    p = paths.SIGNATURES_DIR / "catalog.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else ""


def load_k8s_versions() -> list[dict]:
    p = paths.RUBRIC_DIR / "k8s-versions.yaml"
    return yamlite.load_file(p) or [] if p.is_file() else []


def validate(check: dict, source: str) -> list[str]:
    errs = []
    for k in REQUIRED:
        if k not in check:
            errs.append(f"{source}: {check.get('id', '?')} is missing {k}")
    if check.get("type") not in TYPES:
        errs.append(f"{source}: {check.get('id')} type {check.get('type')!r} must be one of {TYPES}")
    sev = check.get("severity_default")
    if isinstance(sev, dict):
        if sorted(sev) != sorted(SCALES) or any(v not in SEVERITIES for v in sev.values()):
            errs.append(f"{source}: {check.get('id')} severity_default per scale needs exactly {SCALES}, each one of {SEVERITIES}: {sev!r}")
    elif sev not in SEVERITIES:
        errs.append(f"{source}: {check.get('id')} severity_default {sev!r}")
    for key, allowed in (("platforms", PLATFORM_FAMILIES), ("scales", SCALES)):
        v = check.get(key)
        if v is not None and (not isinstance(v, list) or not v or any(x not in allowed for x in v)):
            errs.append(f"{source}: {check.get('id')} {key} must be a non-empty list of {allowed}")
    if check.get("nature", "state") not in NATURES:
        errs.append(f"{source}: {check.get('id')} nature must be one of {NATURES}")
    if check.get("overdue") not in (None, True):
        errs.append(f"{source}: {check.get('id')} overdue is `true` or absent: a failure of this check is a date already passed, and it grows while it waits")
    if "profiles" in check:
        errs.append(f"{source}: {check.get('id')} has `profiles`; a check names `platforms` and `scales` instead")
    rule = check.get("rule") or {}
    if check.get("type") not in ("absence", "llm") and not (rule.get("expr") or rule.get("warn_expr")):
        # A rule with only warn_expr is a warn-only check (it can never fail); a rule with neither would never produce a finding
        errs.append(f"{source}: {check.get('id')} requires rule.expr or rule.warn_expr")
    if check.get("type") == "absence" and not (check.get("family") or check.get("component")):
        errs.append(f"{source}: {check.get('id')} absence requires family or component")
    if "measured" in check and not (isinstance(check["measured"], str) and check["measured"].strip()):
        # What was measured on the clusters the check was written on; the report keeps it apart from public cases
        errs.append(f"{source}: {check.get('id')} measured must be non-empty text")
    modes = check.get("modes")
    if modes is not None and (not isinstance(modes, list) or not modes or any(m not in ("daily", "full") for m in modes)):
        errs.append(f"{source}: {check.get('id')} modes must be a non-empty list of daily/full")
    cid = check.get("id") or ""
    if cid.count(".") < 1:
        errs.append(f"{source}: id {cid!r} must have the form <area>.<check-id>")
    return errs


def catalog() -> tuple[dict, ...]:
    """Every check of every collector, loaded once per process (firstrun counts, the tool table and `kubegap tools` share it)."""
    return _catalog()


@_functools.lru_cache(maxsize=1)
def _catalog() -> tuple[dict, ...]:
    from . import paths as _paths

    return tuple(load_checks([p.name for p in sorted(_paths.COLLECTORS_DIR.iterdir()) if (p / "checks.yaml").is_file()])[0])


def load_checks(collectors: list[str]) -> tuple[list[dict], list[str]]:
    """Merge checks.yaml from every enabled collector folder. Records the collector name in check['collector']."""
    checks: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for name in collectors:
        p = paths.COLLECTORS_DIR / name / "checks.yaml"
        if not p.is_file():
            continue
        try:
            items = yamlite.load_file(p) or []
        except yamlite.YamlError as e:
            errors.append(f"{p}: {e}")
            continue
        for c in items:
            errs = validate(c, str(p.relative_to(paths.ROOT)))
            if errs:
                errors.extend(errs)
                continue
            if c["id"] in seen:
                errors.append(f"{p}: duplicate check id {c['id']}")
                continue
            seen.add(c["id"])
            c["collector"] = name
            c["source_file"] = str(p.relative_to(paths.ROOT))
            checks.append(c)
    return checks, errors


def resolve_thresholds(check: dict, platform: str | None, scale: str, cfg_overrides: dict) -> dict:
    """A threshold is one number, or a mapping with `default` and the platforms or scales that differ from it. The scale's value wins over the
    platform's. config.yaml overrides win over both."""
    rule = check.get("rule") or {}
    fam = platform_family(platform)
    out = {}
    for key in ("threshold", "warn_threshold"):
        v = rule.get(key)
        if isinstance(v, dict):
            v = v.get(scale, v.get(fam, v.get("default")))
        out[key] = v
    ov = (cfg_overrides or {}).get(check["id"]) or {}
    if "threshold" in ov:
        out["threshold"] = ov["threshold"]
    if "warn_threshold" in ov:
        out["warn_threshold"] = ov["warn_threshold"]
    return out


def active_suppressions(cfg_suppress: list | None, today: _dt.date) -> tuple[list[dict], list[dict]]:
    """Split the config.yaml suppress list into (active, expired); `today` is the snapshot date (`evaluate.Context.today`)."""
    active, expired = [], []
    for s in cfg_suppress or []:
        until = s.get("until")
        exp = False
        if until:
            try:
                exp = _dt.date.fromisoformat(str(until)) < today
            except ValueError:
                exp = False
        (expired if exp else active).append(s)
    return active, expired


LEARN_DIR = paths.RUBRIC_DIR / "learn"
DETECT_KINDS = ("metric", "alert", "dashboard", "command")


def _is_url(v) -> bool:
    return isinstance(v, str) and v.startswith("https://") and " " not in v


def validate_learn(topic: dict, source: str, check_ids: set[str]) -> list[str]:
    """What a learn topic must carry so that a report can teach from it: how the thing works with the pages it was read from, how the state is watched,
    how it is solved at each scale, and what to read next. Every address is one a person opened; the file says nothing from memory."""
    errs: list[str] = []
    name = topic.get("topic")
    if not isinstance(name, str) or name != source.rsplit("/", 1)[-1].removesuffix(".yaml"):
        errs.append(f"{source}: topic must equal the file name")
    checks = topic.get("checks")
    if not isinstance(checks, list) or not checks:
        errs.append(f"{source}: checks must list the check ids this topic explains")
    for cid in checks or []:
        if cid not in check_ids:
            errs.append(f"{source}: check {cid} does not exist")
    if not (isinstance(topic.get("mechanism"), str) and len(topic["mechanism"].split()) >= 60):
        errs.append(f"{source}: mechanism is how it works, in paragraphs (60 words or more)")
    srcs = topic.get("sources")
    if not isinstance(srcs, list) or not srcs or any(not isinstance(s, dict) or not s.get("title") or not _is_url(s.get("url")) for s in srcs):
        errs.append(f"{source}: sources must list {{title, url}} of the pages the mechanism was read from")
    detect = topic.get("detect")
    if not isinstance(detect, list) or not detect or any(not isinstance(d, dict) or d.get("kind") not in DETECT_KINDS or not d.get("what") for d in detect):
        errs.append(f"{source}: detect must list {{kind: {'|'.join(DETECT_KINDS)}, what, example}}")
    elif all(d["kind"] == "command" for d in detect):
        errs.append(f"{source}: detect is commands only; name the metric, alert or dashboard that shows the state, and keep a command as an example")
    sols = topic.get("solutions")
    if not isinstance(sols, list) or not sols:
        errs.append(f"{source}: solutions must not be empty")
    covered: set[str] = set()
    for s in sols or []:
        sc = s.get("scale") if isinstance(s, dict) else None
        if not isinstance(sc, list) or not sc or any(x not in SCALES for x in sc) or not s.get("approach") or not s.get("tradeoff"):
            errs.append(f"{source}: a solution needs scale (a list of {SCALES}), approach and tradeoff")
        else:
            covered.update(sc)
    if sols and covered != set(SCALES):
        errs.append(f"{source}: solutions leave a scale without an answer: {sorted(set(SCALES) - covered)}")
    for c in topic.get("cases") or []:
        if not isinstance(c, dict) or not _is_url(c.get("url")) or not c.get("company") or not c.get("summary") or not c.get("match"):
            errs.append(f"{source}: a case needs company, url, summary (what the page says happened) and match (why it is the same mechanism)")
    reading = topic.get("reading")
    if not isinstance(reading, list) or len(reading) < 2 or any(not isinstance(r, dict) or not r.get("title") or not _is_url(r.get("url")) or not r.get("why") for r in reading):
        errs.append(f"{source}: reading must list two or more {{title, url, why}}")
    return errs


@_functools.lru_cache(maxsize=1)
def _learn() -> tuple[tuple[dict, ...], tuple[str, ...]]:
    ids = {c["id"] for c in catalog()}
    topics, errs, owner = [], [], {}
    for path in sorted(LEARN_DIR.glob("*.yaml")):
        source = f"rubric/learn/{path.name}"
        try:
            doc = yamlite.load_file(path)
        except Exception as e:
            errs.append(f"{source}: {e}")
            continue
        if not isinstance(doc, dict):
            errs.append(f"{source}: not a mapping")
            continue
        found = validate_learn(doc, source, ids)
        errs += found
        for cid in doc.get("checks") or []:
            if cid in owner:
                errs.append(f"{source}: check {cid} is already explained by {owner[cid]}")
            owner[cid] = doc.get("topic")
        if not found:
            topics.append(doc)
    return tuple(topics), tuple(errs)


def load_learn() -> tuple[list[dict], list[str]]:
    """The learn topics of rubric/learn/*.yaml: what a report teaches about a group of checks (how it works, how to watch it, how to solve it at each scale,
    public cases, what to read). One file per topic; a check belongs to one topic at most."""
    topics, errs = _learn()
    return list(topics), list(errs)


def learn_for(check_ids) -> list[dict]:
    """The topics that explain any of `check_ids`, in file order."""
    want = set(check_ids)
    return [t for t in load_learn()[0] if want & set(t["checks"])]


def load_incident_library() -> dict | None:
    """references/incident-library.yaml: the public case urls that Incident Library also holds, url -> case id, and the base address of its case pages. None when the file is absent."""
    path = paths.ROOT / "references" / "incident-library.yaml"
    if not path.is_file():
        return None
    doc = yamlite.load(path.read_text(encoding="utf-8")) or {}
    return {"base": str(doc.get("base", "")).rstrip("/"), "cases": {str(x["url"]).rstrip("/"): str(x["id"]) for x in doc.get("cases") or []}}

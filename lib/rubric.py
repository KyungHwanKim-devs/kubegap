"""Rubric loader. Reads checks.yaml, validates the schema, and resolves thresholds and enablement from the profile and config.yaml."""

from __future__ import annotations

import datetime as _dt
import functools as _functools
import json

from . import paths, yamlite

TYPES = ("metric", "object", "summary", "inventory", "absence", "aws", "llm", "signature")
SEVERITIES = ("critical", "high", "medium", "low", "info")
REQUIRED = ("id", "name", "area", "type", "severity_default", "why", "profiles")


class RubricError(ValueError):
    pass


def load_profile(name: str) -> dict:
    p = paths.PROFILES_DIR / f"{name}.yaml"
    if not p.is_file():
        return {"name": name, "missing": True, "disabled_checks": [], "thresholds": {}, "exclude": {}, "expected_families": None}
    d = yamlite.load_file(p) or {}
    d.setdefault("disabled_checks", [])
    d.setdefault("thresholds", {})
    d.setdefault("exclude", {})
    return d


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


# The parts of a check that decide its verdict. Not here: the texts (rewording is not a rule change) and the gates `modes`, `profiles`, `requires_tool`,
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
    if check.get("severity_default") not in SEVERITIES:
        errs.append(f"{source}: {check.get('id')} severity_default {check.get('severity_default')!r}")
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


def resolve_thresholds(check: dict, profile: dict, cfg_overrides: dict) -> dict:
    """Override order: rule.threshold.<profile> -> profile file thresholds -> config.yaml overrides."""
    rule = check.get("rule") or {}
    pname = profile.get("name")
    out = {}
    for key in ("threshold", "warn_threshold"):
        v = rule.get(key)
        if isinstance(v, dict):
            v = v.get(pname, v.get(profile.get("base") or "", v.get("default")))  # a new profile inherits thresholds from its base profile
        out[key] = v
    prof_t = (profile.get("thresholds") or {}).get(check["id"]) or {}
    if "fail" in prof_t:
        out["threshold"] = prof_t["fail"]
    if "warn" in prof_t:
        out["warn_threshold"] = prof_t["warn"]
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

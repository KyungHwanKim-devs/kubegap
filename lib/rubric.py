"""Rubric loader. Reads checks.yaml, validates the schema, and resolves thresholds and enablement from the profile and config.yaml."""

from __future__ import annotations

import datetime as _dt

from . import paths, yamlite

TYPES = ("metric", "object", "summary", "inventory", "absence", "aws", "llm", "signature")
SEVERITIES = ("critical", "high", "medium", "low", "info")
REQUIRED = ("id", "name", "area", "type", "severity_default", "why", "profiles")


class RubricError(ValueError):
    pass


PROFILE_ALIASES = {"eks": "prod", "k3s": "lab", "homelab": "lab"}  # profile names before 0.1.51 were platform names; snapshots and configs from then still say so


def load_profile(name: str) -> dict:
    name = PROFILE_ALIASES.get(name, name)
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
    modes = check.get("modes")
    if modes is not None and (not isinstance(modes, list) or not modes or any(m not in ("daily", "full") for m in modes)):
        errs.append(f"{source}: {check.get('id')} modes must be a non-empty list of daily/full")
    cid = check.get("id") or ""
    if cid.count(".") < 1:
        errs.append(f"{source}: id {cid!r} must have the form <area>.<check-id>")
    return errs


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


def active_suppressions(cfg_suppress: list | None, today: _dt.date | None = None) -> tuple[list[dict], list[dict]]:
    """Split the config.yaml suppress list into (active, expired)."""
    today = today or _dt.date.today()
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

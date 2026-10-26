"""lib/rubric.py: threshold resolution, profile loading and check validation. Uses the real rubric/profiles folder (repo-local, no cluster)."""

import pytest

from lib import rubric


def check(**over):
    base = {"id": "area.check", "name": "n", "area": "area", "type": "metric", "severity_default": "high", "why": "w", "profiles": ["eks"], "rule": {"expr": "v > t"}}
    base.update(over)
    return base


# ---------- resolve_thresholds ----------


def test_threshold_scalar_is_used_as_is():
    out = rubric.resolve_thresholds(check(rule={"expr": "x", "threshold": 0.8, "warn_threshold": 0.6}), {"name": "prod"}, {})
    assert out == {"threshold": 0.8, "warn_threshold": 0.6}


def test_threshold_per_profile_override():
    c = check(rule={"expr": "x", "threshold": {"default": 5, "prod": 10, "lab": 2}})
    assert rubric.resolve_thresholds(c, {"name": "lab"}, {})["threshold"] == 2
    assert rubric.resolve_thresholds(c, {"name": "prod"}, {})["threshold"] == 10
    assert rubric.resolve_thresholds(c, {"name": "dev"}, {})["threshold"] == 5  # not listed: default


def test_threshold_falls_back_to_base_profile():
    # small-prod declares base: eks, so a check that only knows eks and small k3s cluster resolves to the eks value.
    c = check(rule={"expr": "x", "threshold": {"default": 1, "prod": 10, "lab": 2}})
    prof = rubric.load_profile("small-prod")
    assert prof.get("base") == "prod"
    assert rubric.resolve_thresholds(c, prof, {})["threshold"] == 10


def test_profile_file_thresholds_beat_rule_and_config_beats_profile():
    c = check(rule={"expr": "x", "threshold": {"default": 1, "prod": 10}, "warn_threshold": 0.5})
    prof = {"name": "prod", "thresholds": {"area.check": {"fail": 20, "warn": 0.7}}}
    assert rubric.resolve_thresholds(c, prof, {}) == {"threshold": 20, "warn_threshold": 0.7}
    cfg = {"area.check": {"threshold": 30}}
    assert rubric.resolve_thresholds(c, prof, cfg) == {"threshold": 30, "warn_threshold": 0.7}
    assert rubric.resolve_thresholds(c, prof, {"area.check": {"warn_threshold": 0.9}})["warn_threshold"] == 0.9


def test_missing_threshold_is_none():
    assert rubric.resolve_thresholds(check(), {"name": "prod"}, None) == {"threshold": None, "warn_threshold": None}


# ---------- load_profile ----------


def test_load_profile_missing_returns_marker_with_empty_defaults():
    p = rubric.load_profile("no-such-profile")
    assert p["missing"] is True
    assert p["name"] == "no-such-profile"
    assert p["disabled_checks"] == [] and p["thresholds"] == {} and p["exclude"] == {}


def test_load_profile_existing_has_defaults_filled():
    p = rubric.load_profile("prod")
    assert p["name"] == "prod"
    assert "missing" not in p
    assert isinstance(p["disabled_checks"], list) and isinstance(p["thresholds"], dict) and isinstance(p["exclude"], dict)


# ---------- validate ----------


def test_validate_accepts_a_complete_check():
    assert rubric.validate(check(test={"cases": [{"expect": "fail", "item": {}}]}), "src") == []


def test_validate_reports_missing_required_fields_and_bad_enums():
    errs = rubric.validate({"id": "nodots", "type": "bogus", "severity_default": "urgent"}, "src")
    joined = "\n".join(errs)
    for k in ("name", "area", "why", "profiles"):
        assert f"is missing {k}" in joined
    assert "type 'bogus'" in joined
    assert "severity_default 'urgent'" in joined
    assert "must have the form <area>.<check-id>" in joined


def test_validate_requires_expr_for_metric_but_not_for_absence_or_llm():
    assert any("requires rule.expr" in e for e in rubric.validate(check(rule={}), "src"))
    assert rubric.validate(check(type="llm", rule={}), "src") == []
    assert rubric.validate(check(type="absence", rule={}, family="backup"), "src") == []
    assert any("absence requires family or component" in e for e in rubric.validate(check(type="absence", rule={}), "src"))


@pytest.mark.xfail(strict=False, reason="validate does not yet require test.cases; today that is enforced by `kubegap selftest` (lib/selftest.py reports checks without a test section)")
def test_validate_rejects_check_without_test_cases():
    errs = rubric.validate(check(), "src")
    assert any("test" in e for e in errs)


def test_validate_accepts_warn_only_check():
    # A rule with only warn_expr can never fail but is still a valid check
    c = check(rule={"warn_expr": "v > t"}, test={"cases": [{"expect": "warn", "item": {}}]})
    assert rubric.validate(c, "src") == []


# ---------- active_suppressions ----------


def test_active_suppressions_split_by_until_date():
    import datetime as dt

    today = dt.date(2026, 6, 1)
    sup = [{"id": "a", "until": "2026-05-31"}, {"id": "b", "until": "2026-06-01"}, {"id": "c"}, {"id": "d", "until": "not-a-date"}]
    active, expired = rubric.active_suppressions(sup, today)
    assert [s["id"] for s in expired] == ["a"]
    assert [s["id"] for s in active] == ["b", "c", "d"]
    assert rubric.active_suppressions(None, today) == ([], [])

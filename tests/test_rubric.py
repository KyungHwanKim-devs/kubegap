"""lib/foundations/rubric.py: severity, threshold and enablement by platform and scale, and check validation. Uses the real rubric folder (repo-local, no cluster)."""

import pytest

from lib.foundations import rubric


def check(**over):
    base = {"id": "area.check", "name": "n", "area": "area", "type": "metric", "severity_default": "high", "why": "w", "rule": {"expr": "v > t"}}
    base.update(over)
    return base


# ---------- resolve_thresholds ----------


def test_threshold_scalar_is_used_as_is():
    out = rubric.resolve_thresholds(check(rule={"expr": "x", "threshold": 0.8, "warn_threshold": 0.6}), "eks", "large", {})
    assert out == {"threshold": 0.8, "warn_threshold": 0.6}


def test_threshold_per_platform_and_scale_with_scale_winning():
    c = check(rule={"expr": "x", "threshold": {"default": 5, "k3s": 2, "large": 10}})
    assert rubric.resolve_thresholds(c, "k3s", "small", {})["threshold"] == 2
    assert rubric.resolve_thresholds(c, "rke2", "small", {})["threshold"] == 2  # RKE2 reads the k3s facts
    assert rubric.resolve_thresholds(c, "eks", "medium", {})["threshold"] == 5  # neither listed: default
    assert rubric.resolve_thresholds(c, "k3s", "large", {})["threshold"] == 10  # the scale's value wins over the platform's


def test_config_overrides_beat_the_rule():
    c = check(rule={"expr": "x", "threshold": {"default": 1, "k3s": 10}, "warn_threshold": 0.5})
    assert rubric.resolve_thresholds(c, "k3s", "small", {"area.check": {"threshold": 30}}) == {"threshold": 30, "warn_threshold": 0.5}
    assert rubric.resolve_thresholds(c, "k3s", "small", {"area.check": {"warn_threshold": 0.9}})["warn_threshold"] == 0.9


def test_missing_threshold_is_none():
    assert rubric.resolve_thresholds(check(), "eks", "large", None) == {"threshold": None, "warn_threshold": None}


# ---------- platform and scale ----------


def test_platform_family_and_file():
    assert [rubric.platform_family(p) for p in ("eks", "k3s", "rke2", "gke", "aks", "unknown", None)] == ["eks", "k3s", "k3s", "other", "other", "other", "other"]
    for name in ("eks", "k3s", "gke"):
        p = rubric.load_platform(name)
        assert p["name"] == rubric.platform_family(name) and isinstance(p["exclude"], dict) and isinstance(p["families_not_expected"], list)


def test_expected_families_grow_with_scale_and_a_platform_takes_some_out():
    k3s, eks = rubric.load_platform("k3s"), rubric.load_platform("eks")
    small, medium, large = (set(rubric.expected_families(s, eks)) for s in rubric.SCALES)
    assert small < medium < large
    assert "slo" not in small and "slo" in medium and "progressive-delivery" in large - medium
    assert "node-autoscaler" in medium and "node-autoscaler" not in rubric.expected_families("large", k3s)  # a fixed node count has nothing to scale


def test_severity_and_gates_per_scale():
    c = check(severity_default={"small": "low", "medium": "high", "large": "critical"})
    assert [rubric.severity_for(c, s) for s in rubric.SCALES] == ["low", "high", "critical"]
    assert rubric.severity_for(check(), "small") == "high"
    assert rubric.applies(check(), "k3s", "small") is None
    assert "platform k3s" in rubric.applies(check(platforms=["eks", "other"]), "k3s", "large")
    assert rubric.applies(check(platforms=["k3s"]), "rke2", "small") is None
    assert "scale small" in rubric.applies(check(scales=["medium", "large"]), "eks", "small")


def test_every_check_of_the_catalog_has_a_level_at_every_scale():
    for c in rubric.catalog():
        for s in rubric.SCALES:
            assert rubric.severity_for(c, s) in rubric.SEVERITIES, c["id"]
        assert "profiles" not in c, c["id"]


# ---------- validate ----------


def test_validate_accepts_a_complete_check():
    assert rubric.validate(check(test={"cases": [{"expect": "fail", "item": {}}]}), "src") == []


def test_validate_reports_missing_required_fields_and_bad_enums():
    errs = rubric.validate({"id": "nodots", "type": "bogus", "severity_default": "urgent"}, "src")
    joined = "\n".join(errs)
    for k in ("name", "area", "why"):
        assert f"is missing {k}" in joined
    assert "type 'bogus'" in joined
    assert "severity_default 'urgent'" in joined
    assert "must have the form <area>.<check-id>" in joined
    assert any("per scale" in e for e in rubric.validate(check(severity_default={"small": "low", "large": "high"}), "src"))
    assert any("platforms must be" in e for e in rubric.validate(check(platforms=["lab"]), "src"))
    assert any("scales must be" in e for e in rubric.validate(check(scales=[]), "src"))
    assert any("`profiles`" in e for e in rubric.validate(check(profiles=["prod"]), "src"))


def test_validate_requires_expr_for_metric_but_not_for_absence_or_llm():
    assert any("requires rule.expr" in e for e in rubric.validate(check(rule={}), "src"))
    assert rubric.validate(check(type="llm", rule={}), "src") == []
    assert rubric.validate(check(type="absence", rule={}, family="backup"), "src") == []
    assert any("absence requires family or component" in e for e in rubric.validate(check(type="absence", rule={}), "src"))


@pytest.mark.xfail(strict=False, reason="validate does not yet require test.cases; today that is enforced by `kubegap selftest` (lib/commands/selftest.py reports checks without a test section)")
def test_validate_rejects_check_without_test_cases():
    errs = rubric.validate(check(), "src")
    assert any("test" in e for e in errs)


def test_validate_accepts_warn_only_check():
    # A rule with only warn_expr can never fail but is still a valid check
    c = check(rule={"warn_expr": "v > t"}, test={"cases": [{"expect": "warn", "item": {}}]})
    assert rubric.validate(c, "src") == []


def test_validate_measured_is_text():
    assert rubric.validate(check(measured="Measured on a real EKS cluster: 2/2 replicas."), "src") == []
    assert any("measured" in e for e in rubric.validate(check(measured=""), "src"))
    assert any("measured" in e for e in rubric.validate(check(measured=["a list"]), "src"))


# ---------- active_suppressions ----------


def test_active_suppressions_split_by_until_date():
    import datetime as dt

    today = dt.date(2026, 6, 1)
    sup = [{"id": "a", "until": "2026-05-31"}, {"id": "b", "until": "2026-06-01"}, {"id": "c"}, {"id": "d", "until": "not-a-date"}]
    active, expired = rubric.active_suppressions(sup, today)
    assert [s["id"] for s in expired] == ["a"]
    assert [s["id"] for s in active] == ["b", "c", "d"]
    assert rubric.active_suppressions(None, today) == ([], [])


def test_no_check_expression_is_longer_than_500_characters():
    """An evidence sentence longer than that is code: it goes into lib/judgement/evaluate/evidence.py as a helper the expression calls (#24). The twelve that
    were over 500 characters did; the ones between 200 and 500 are prose templates a reader can still follow in place."""
    from pathlib import Path

    from lib.foundations import yamlite

    root = Path(__file__).resolve().parent.parent
    long = []
    for f in sorted((root / "collectors").glob("*/checks.yaml")):
        for c in yamlite.load_file(f) or []:
            if not isinstance(c, dict):
                continue
            for name, text in (("expr", (c.get("rule") or {}).get("expr")), ("warn_expr", (c.get("rule") or {}).get("warn_expr")), ("target", c.get("target")), ("evidence", c.get("evidence"))):
                if isinstance(text, str) and len(text) > 500:
                    long.append(f"{c['id']} {name} ({len(text)} chars)")
    assert long == [], "move the sentence into an evidence helper"

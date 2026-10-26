"""lib/evaluate.py pure helpers: the sandboxed expression evaluator and the static helpers checks.yaml expressions call."""

import datetime as dt

import pytest

from lib import evaluate
from lib.evaluate import SAFE_BUILTINS, Context, _eval, _excluded, _get_path, _status

# ---------- sandboxed eval ----------


def test_eval_allows_arithmetic_comparison_and_safe_builtins():
    env = {"v": 0.9, "t": 0.8, "items": [1, 2, 3]}
    assert _eval("v > t", env) is True
    assert _eval("len(items) * 2 + 1", env) == 7
    assert _eval("max(items) - min(items)", env) == 2
    assert _eval("round(v * 100)", env) == 90
    assert _eval("re.match(r'^v1\\.(\\d+)', 'v1.31.2').group(1)", env) == "31"


def test_eval_blocks_import_and_other_builtins():
    with pytest.raises(NameError):
        _eval("__import__('os').system('true')", {})
    with pytest.raises(NameError):
        _eval("open('/etc/passwd')", {})
    with pytest.raises(NameError):
        _eval("eval('1')", {})
    assert "__import__" not in SAFE_BUILTINS and "open" not in SAFE_BUILTINS


def test_status_fail_beats_warn_and_defaults_to_pass():
    env = {"v": 5}
    assert _status({"expr": "v > 3", "warn_expr": "v > 1"}, env) == "fail"
    assert _status({"expr": "v > 10", "warn_expr": "v > 1"}, env) == "warn"
    assert _status({"expr": "v > 10"}, env) == "pass"
    assert _status({}, env) == "pass"
    assert _status({"warn_expr": "v > 1"}, env) == "warn"  # warn-only rule


# ---------- small pure helpers ----------


def test_get_path():
    d = {"a": {"b": {"c": 1}}, "x": [1]}
    assert _get_path(d, "a.b.c") == 1
    assert _get_path(d, "a.b") == {"c": 1}
    assert _get_path(d, "a.missing.c") is None
    assert _get_path(d, "x.0") is None  # lists are not traversed


def test_excluded_uses_case_sensitive_globs():
    prof = {"exclude": {"traffic.endpoint-zero": ["kube-system/kube-prometheus-stack-*", "monitoring/exact"]}}
    assert _excluded("traffic.endpoint-zero", "kube-system/kube-prometheus-stack-kube-etcd", prof)
    assert _excluded("traffic.endpoint-zero", "monitoring/exact", prof)
    assert not _excluded("traffic.endpoint-zero", "monitoring/Exact", prof)
    assert not _excluded("other.check", "monitoring/exact", prof)
    assert not _excluded("traffic.endpoint-zero", "x", {})


def test_days_until():
    today = dt.date.today()
    assert Context.days_until((today + dt.timedelta(days=10)).isoformat()) == 10
    assert Context.days_until((today - dt.timedelta(days=3)).isoformat() + "T12:00:00Z") == -3
    assert Context.days_until(None) is None
    assert Context.days_until("") is None
    assert Context.days_until("not-a-date") is None


def test_addon_minor_gap():
    assert Context.addon_minor_gap("v1.18.1-eksbuild.1", "v1.19.0-eksbuild.1") == 1
    assert Context.addon_minor_gap("v1.18.1", "v1.18.5") == 0
    assert Context.addon_minor_gap("v1.30.0", "v2.1.0") == (2 - 1) * 100 + (1 - 30)  # a major bump counts as 100 minors
    assert Context.addon_minor_gap(None, "v1.19.0") == 0
    assert Context.addon_minor_gap("garbage", "v1.19.0") == 0


def test_karpenter_budget_allowed_rounds_up_and_ignores_scheduled_budgets():
    assert Context.karpenter_budget_allowed({"disruption": {"budgets": [{"nodes": "10%"}]}}, 4) == 1  # ceil(0.4)
    assert Context.karpenter_budget_allowed({"disruption": {"budgets": [{"nodes": "25%"}, {"nodes": "3"}]}}, 10) == 3  # min(3, 3)
    assert Context.karpenter_budget_allowed({"disruption": {"budgets": [{"nodes": "0", "schedule": "* * * * *"}, {"nodes": "2"}]}}, 10) == 2
    assert Context.karpenter_budget_allowed({"disruption": {"budgets": []}}, 10) == 1  # no budgets: Karpenter default 10%
    assert Context.karpenter_budget_allowed({}, 10) == 1
    assert Context.karpenter_budget_allowed({"disruption": {"budgets": [{"nodes": "1", "schedule": "@daily"}]}}, 10) is None  # only scheduled budgets


def test_pod_spec_for_pod_and_for_workload():
    pod = {"kind": "Pod", "spec": {"containers": [{"name": "c"}]}}
    deploy = {"kind": "Deployment", "spec": {"template": {"spec": {"containers": [{"name": "d"}]}}}}
    assert Context.pod_spec(pod) == {"containers": [{"name": "c"}]}
    assert Context.pod_spec(deploy) == {"containers": [{"name": "d"}]}
    assert Context.pod_spec({"kind": "Deployment"}) == {}


def test_selector_matches():
    m = Context._selector_matches
    labels = {"app": "web", "tier": "front"}
    assert m({"matchLabels": {"app": "web"}}, labels)
    assert not m({"matchLabels": {"app": "api"}}, labels)
    assert m({"matchExpressions": [{"key": "tier", "operator": "In", "values": ["front", "back"]}]}, labels)
    assert not m({"matchExpressions": [{"key": "tier", "operator": "NotIn", "values": ["front"]}]}, labels)
    assert m({"matchExpressions": [{"key": "app", "operator": "Exists"}]}, labels)
    assert not m({"matchExpressions": [{"key": "app", "operator": "DoesNotExist"}]}, labels)
    assert not m(None, labels)
    assert not m({}, labels)


def test_symptom_metric_regex():
    assert evaluate.SYMPTOM_METRIC_RE.search("sum(rate(http_requests_total[5m]))")
    assert evaluate.SYMPTOM_METRIC_RE.search("probe_success == 0")
    assert not evaluate.SYMPTOM_METRIC_RE.search("node_memory_MemAvailable_bytes")

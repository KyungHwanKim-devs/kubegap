"""lib/judgement/evaluate pure helpers: the sandboxed expression evaluator and the static helpers checks.yaml expressions call."""

import datetime as dt
import json
from pathlib import Path

import pytest

from lib.judgement import evaluate
from lib.judgement.evaluate import Context
from lib.judgement.evaluate.context import get_path
from lib.judgement.evaluate.rules import SAFE_BUILTINS, eval_expr, excluded, status

# ---------- sandboxed eval ----------


def test_eval_allows_arithmetic_comparison_and_safe_builtins():
    env = {"v": 0.9, "t": 0.8, "items": [1, 2, 3]}
    assert eval_expr("v > t", env) is True
    assert eval_expr("len(items) * 2 + 1", env) == 7
    assert eval_expr("max(items) - min(items)", env) == 2
    assert eval_expr("round(v * 100)", env) == 90
    assert eval_expr("re.match(r'^v1\\.(\\d+)', 'v1.31.2').group(1)", env) == "31"


def test_eval_blocks_import_and_other_builtins():
    with pytest.raises(NameError):
        eval_expr("__import__('os').system('true')", {})
    with pytest.raises(NameError):
        eval_expr("open('/etc/passwd')", {})
    with pytest.raises(NameError):
        eval_expr("eval('1')", {})
    assert "__import__" not in SAFE_BUILTINS and "open" not in SAFE_BUILTINS


def test_status_fail_beats_warn_and_defaults_to_pass():
    env = {"v": 5}
    assert status({"expr": "v > 3", "warn_expr": "v > 1"}, env) == "fail"
    assert status({"expr": "v > 10", "warn_expr": "v > 1"}, env) == "warn"
    assert status({"expr": "v > 10"}, env) == "pass"
    assert status({}, env) == "pass"
    assert status({"warn_expr": "v > 1"}, env) == "warn"  # warn-only rule


# ---------- small pure helpers ----------


def test_get_path():
    d = {"a": {"b": {"c": 1}}, "x": [1]}
    assert get_path(d, "a.b.c") == 1
    assert get_path(d, "a.b") == {"c": 1}
    assert get_path(d, "a.missing.c") is None
    assert get_path(d, "x.0") is None  # lists are not traversed


def test_excluded_uses_case_sensitive_globs():
    prof = {"exclude": {"traffic.endpoint-zero": ["kube-system/kube-prometheus-stack-*", "monitoring/exact"]}}
    assert excluded("traffic.endpoint-zero", "kube-system/kube-prometheus-stack-kube-etcd", prof)
    assert excluded("traffic.endpoint-zero", "monitoring/exact", prof)
    assert not excluded("traffic.endpoint-zero", "monitoring/Exact", prof)
    assert not excluded("other.check", "monitoring/exact", prof)
    assert not excluded("traffic.endpoint-zero", "x", {})


def _ctx(inv: dict) -> Context:
    return Context(Path("/nonexistent"), inv, {}, "large")


def test_days_until():
    today = dt.date.today()
    c = _ctx({})
    assert c.today == today
    assert c.days_until((today + dt.timedelta(days=10)).isoformat()) == 10
    assert c.days_until((today - dt.timedelta(days=3)).isoformat() + "T12:00:00Z") == -3
    assert c.days_until(None) is None
    assert c.days_until("") is None
    assert c.days_until("not-a-date") is None


def test_days_until_pinned_today():
    """Embedded test cases set inv["today"] so date-based verdicts do not drift with the calendar."""
    c = _ctx({"today": "2026-10-25"})
    assert c.today == dt.date(2026, 10, 25)
    assert c.days_until("2026-10-28") == 3
    assert c.days_until("2026-10-25T00:00:00Z") == 0


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
    assert evaluate.context.SYMPTOM_METRIC_RE.search("sum(rate(http_requests_total[5m]))")
    assert evaluate.context.SYMPTOM_METRIC_RE.search("probe_success == 0")
    assert not evaluate.context.SYMPTOM_METRIC_RE.search("node_memory_MemAvailable_bytes")


# ---------- database-like containers ----------


def test_is_db_like_by_name_image_and_workload():
    from lib.foundations.workload import is_db_like

    assert is_db_like("neo4j", "neo4j:2026.05.0-community", "app-neo4j")
    assert is_db_like("db", "public.ecr.aws/bitnami/postgresql:16", "shop-db")
    assert is_db_like("app", "ghcr.io/x/y:1", "shop-postgresql")  # the workload name alone is enough
    assert not is_db_like("metrics", "public.ecr.aws/bitnami/redis-exporter:1.55.0", "redis-master")  # the exporter next to a database
    assert not is_db_like("kafka-ui", "docker.io/provectuslabs/kafka-ui:v0.7.1", "kafka-ui")
    assert is_db_like("kafka", "docker.io/bitnami/kafka:3.7", "kafka-controller")  # Bitnami names its KRaft brokers kafka-controller
    assert not is_db_like("umami", "ghcr.io/umami-software/umami:postgresql-latest", "umami")  # the tag is not looked at
    assert not is_db_like("web", "nginx:1.27", "web")
    assert not is_db_like("mongodb-agent", "quay.io/mongodb/mongodb-agent:107", "my-mongo")  # the operator's sidecar in a database pod
    assert not is_db_like("redis-commander", "rediscommander/redis-commander:latest", "redis-commander")
    assert not is_db_like("kafka-connect", "confluentinc/cp-kafka-connect:7.6", "kafka-connect")
    assert not is_db_like("kafka", "confluentinc/cp-kafka-connect:7.6", "kafka-connect")  # the container name says kafka, the image says connect


def test_image_repo():
    from lib.foundations.workload import image_repo

    assert image_repo("neo4j:2026.05.0-community") == "neo4j"
    assert image_repo("public.ecr.aws/bitnami/redis:7.2.3-debian-11-r1") == "redis"
    assert image_repo("localhost:5000/redis:7") == "redis"
    assert image_repo("ghcr.io/x/postgres@sha256:abcd") == "postgres"
    assert image_repo(None) == ""


def _cx_with_pods(tmp_path, pods):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "pods.json").write_text(json.dumps({"items": pods}), encoding="utf-8")
    return Context(tmp_path, {}, {}, "large")


def test_db_like_labels_look_up_the_pod_container(tmp_path):
    pods = [
        {
            "metadata": {"namespace": "prod-a", "name": "redis-master-0", "ownerReferences": [{"kind": "StatefulSet", "name": "redis-master"}]},
            "spec": {"containers": [{"name": "redis", "image": "public.ecr.aws/bitnami/redis:7.2.3"}, {"name": "metrics", "image": "public.ecr.aws/bitnami/redis-exporter:1.55.0"}]},
        }
    ]
    cx = _cx_with_pods(tmp_path, pods)
    assert cx.db_like({"namespace": "prod-a", "pod": "redis-master-0", "container": "redis"})
    assert not cx.db_like({"namespace": "prod-a", "pod": "redis-master-0", "container": "metrics"})
    assert not cx.db_like({"namespace": "prod-a", "pod": "redis-master-0"})  # no container label: the exporter sidecar keeps the pod from counting
    assert not cx.db_like({"namespace": "prod-a"})


def test_db_like_sees_init_container_sidecars(tmp_path):
    pods = [
        {
            "metadata": {"namespace": "prod-a", "name": "shop-postgresql-0", "ownerReferences": [{"kind": "StatefulSet", "name": "shop-postgresql"}]},
            "spec": {"initContainers": [{"name": "postgresql", "image": "postgres:16", "restartPolicy": "Always"}], "containers": [{"name": "app", "image": "ghcr.io/x/app:1"}]},
        }
    ]
    cx = _cx_with_pods(tmp_path, pods)
    assert cx.db_like({"namespace": "prod-a", "pod": "shop-postgresql-0", "container": "postgresql"})
    assert cx.db_like({"namespace": "prod-a", "pod": "shop-postgresql-0", "container": "app"})  # the workload name shop-postgresql carries the hint
    assert not cx.db_like({"namespace": "prod-a", "pod": "shop-postgresql-0", "container": "nothing"})


def test_db_like_guesses_a_gone_pod_from_its_name(tmp_path):
    cx = _cx_with_pods(tmp_path, [])
    assert cx.db_like({"namespace": "prod-a", "pod": "shop-postgresql-0", "container": "postgresql"})
    assert not cx.db_like({"namespace": "prod-a", "pod": "web-6d7ff4dcdb-abcde", "container": "app"})

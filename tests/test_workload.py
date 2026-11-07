"""lib/workload: the name, key and nature of a workload read from the objects alone (#150)."""

from lib import workload


def test_workload_of_strips_the_hashes_kubernetes_appends():
    assert workload.workload_of("web/api-6d7ff4dcdb-fphgn") == "web/api"  # Deployment: replicaset hash + pod hash
    assert workload.workload_of("batch/report-29301234-abcde") == "batch/report"  # CronJob: job number + pod hash
    assert workload.workload_of("kube-system/node-exporter-x7k2p") == "kube-system/node-exporter"  # DaemonSet: pod hash only
    assert workload.workload_of("db/postgres-0") == "db/postgres-0"  # StatefulSet pods keep their ordinal: not a hash


def test_key_is_namespace_kind_name():
    assert workload.key("Deployment", {"metadata": {"namespace": "web", "name": "api"}}) == "web/deployment/api"


def test_image_repo_drops_registry_tag_and_digest():
    assert workload.image_repo("public.ecr.aws/bitnami/redis:7.2.3") == "redis"
    assert workload.image_repo("redis@sha256:abc") == "redis" and workload.image_repo("ghcr.io/x/umami:postgresql-latest") == "umami"
    assert workload.image_repo(None) == ""


def test_is_db_like_by_name_by_image_and_by_statefulset_with_a_claim():
    assert workload.is_db_like("postgres", "postgres:16", "shop-db")
    assert workload.is_db_like("main", "ghcr.io/acme/app:1", "redis-cache")
    assert not workload.is_db_like("redis-exporter", "oliver006/redis_exporter:v1", "redis")  # a helper next to the store
    assert not workload.is_db_like("grafana", "grafana/grafana:11", "kube-prometheus-stack-grafana")  # release named after a store
    assert workload.is_db_like("app", "acme/app:1", "whatever", stateful=True)
    assert not workload.is_db_like("init", "acme/db:1", "whatever", stateful=True)  # an init container of a store is not the store


def test_mounts_pvc():
    assert workload.mounts_pvc({"volumes": [{"name": "d", "persistentVolumeClaim": {"claimName": "data"}}]})
    assert not workload.mounts_pvc({"volumes": [{"name": "d", "emptyDir": {}}]}) and not workload.mounts_pvc(None)


def test_selector_matches_labels_and_expressions_and_an_empty_selector_matches_nothing():
    labels = {"app": "api", "tier": "web"}
    assert workload.selector_matches({"app": "api"}, labels)
    assert workload.selector_matches({"matchLabels": {"app": "api"}, "matchExpressions": [{"key": "tier", "operator": "In", "values": ["web"]}]}, labels)
    assert not workload.selector_matches({"matchExpressions": [{"key": "tier", "operator": "NotIn", "values": ["web"]}]}, labels)
    assert workload.selector_matches({"matchExpressions": [{"key": "app", "operator": "Exists"}]}, labels)
    assert not workload.selector_matches({"matchExpressions": [{"key": "app", "operator": "DoesNotExist"}]}, labels)
    assert not workload.selector_matches({}, labels) and not workload.selector_matches(None, labels)


def _node(name, labels=None, taints=None, unschedulable=False):
    return {"metadata": {"name": name, "labels": labels or {}}, "spec": {"taints": taints or [], "unschedulable": unschedulable}}


def test_eligible_nodes_honours_selector_affinity_taints_and_cordon():
    nodes = [_node("a", {"pool": "x"}), _node("b", {"pool": "y"}), _node("c", {"pool": "x"}, taints=[{"key": "k", "effect": "NoSchedule"}]), _node("d", {"pool": "x"}, unschedulable=True)]
    assert workload.eligible_nodes({"nodeSelector": {"pool": "x"}}, nodes) == ["a"]
    assert workload.eligible_nodes({"nodeSelector": {"pool": "x"}, "tolerations": [{"key": "k", "operator": "Exists"}]}, nodes) == ["a", "c"]
    aff = {"affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "pool", "operator": "In", "values": ["y"]}]}]}}}}
    assert workload.eligible_nodes(aff, nodes) == ["b"]
    assert workload.eligible_nodes({"nodeName": "zzz"}, nodes) == ["zzz"]
    assert workload.eligible_nodes({"nodeName": "zzz"}, nodes, ignore_node_name=True) == ["a", "b"]

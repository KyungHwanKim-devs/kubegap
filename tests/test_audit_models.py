"""The model behind seven checks, one test per state: store detection, node autoscalers and N+1 pools, backup signals, app-metric rule classes, private routes of the node subnets, the ConfigMap oldest reader, nginx version tags and the webhook NetworkPolicy, the request-weighted latest hour."""

from __future__ import annotations

import datetime as dt
import json

from lib.foundations.workload import is_db_like
from lib.judgement.evaluate import Context
from lib.summaries import observability, resilience, traffic, vpccni
from lib.summaries.traffic import _latest_hour

# ---------- database-like ----------


def test_store_by_structure_and_by_name_and_helper_tokens():
    assert is_db_like("store", "registry.corp/platform/ledger-store:3.1", "ledger", stateful=True)  # a StatefulSet with a PVC, unknown image
    assert not is_db_like("store", "registry.corp/platform/ledger-store:3.1", "ledger")  # the same without the structural signal
    assert is_db_like("prometheus", "quay.io/prometheus/prometheus:v2.5", "prometheus-k8s")
    assert is_db_like("mysql", "mysql:8", "mysql-quickstart")  # quickstart does not trip the ui token
    assert not is_db_like("metrics", "bitnami/redis-exporter:1", "redis-master", stateful=True)  # the exporter next to a store, even in a StatefulSet
    assert not is_db_like("init", "busybox:1", "postgres", stateful=True)
    assert is_db_like("app", "ghcr.io/x/magento:2", "magento-redis")  # agent inside magento is not a token
    assert is_db_like("vmsingle", "victoriametrics/victoria-metrics:v1.132.0", "vm-single", stateful=True)  # metrics in the image name is not a helper token
    assert not is_db_like("grafana", "grafana/grafana:11", "kube-prometheus-stack-grafana")  # the release prefix does not make Grafana a store
    assert not is_db_like("promtail", "grafana/promtail:3", "loki-stack-promtail")
    assert is_db_like("loki", "grafana/loki:3", "loki-stack")


def test_context_db_like_uses_statefulset_pvc(tmp_path):
    (tmp_path / "objects").mkdir()
    pods = [
        {
            "metadata": {"namespace": "p", "name": "ledger-0", "ownerReferences": [{"kind": "StatefulSet", "name": "ledger"}]},
            "spec": {"volumes": [{"name": "data", "persistentVolumeClaim": {"claimName": "data-ledger-0"}}], "containers": [{"name": "store", "image": "registry.corp/ledger-store:3"}]},
        }
    ]
    (tmp_path / "objects" / "pods.json").write_text(json.dumps({"items": pods}))
    cx = Context(tmp_path, {}, {}, {"name": "prod"})
    assert cx.db_like({"namespace": "p", "pod": "ledger-0", "container": "store"})


# ---------- autoscaler and N+1 pools ----------


def _node(name, cpu, mem_gb, labels=None):
    return {"metadata": {"name": name, "labels": labels or {}}, "status": {"allocatable": {"cpu": str(cpu), "memory": f"{mem_gb}Gi"}}, "spec": {}}


def _pod(ns, name, node, cpu, mem_gb, selector=None):
    spec = {"nodeName": node, "containers": [{"name": "c", "resources": {"requests": {"cpu": str(cpu), "memory": f"{mem_gb}Gi"}}}]}
    if selector:
        spec["nodeSelector"] = selector
    return {"metadata": {"namespace": ns, "name": name}, "spec": spec, "status": {"phase": "Running"}}


def _write(tmp_path, stem, items):
    (tmp_path / "objects").mkdir(exist_ok=True)
    (tmp_path / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}))


def test_n_plus_one_fails_per_pool_when_the_cluster_sum_fits(tmp_path):
    nodes = [_node("big", 8, 32, {"role": "app"}), _node("app2", 4, 16, {"role": "app"}), _node("sys1", 8, 32), _node("sys2", 8, 32)]
    pods = [_pod("prod", f"a{i}", "big", 1, 4, {"role": "app"}) for i in range(6)] + [_pod("prod", "x", "app2", 2.5, 12, {"role": "app"})]
    ds = _pod("kube-system", "node-agent-app2", "app2", 0.5, 1)  # a DaemonSet pod also occupies the room on app2
    ds["metadata"]["ownerReferences"] = [{"kind": "DaemonSet", "name": "node-agent"}]
    pods.append(ds)
    _write(tmp_path, "nodes", nodes)
    _write(tmp_path, "pods", pods)
    for stem in ("deployments", "statefulsets", "daemonsets", "services"):
        _write(tmp_path, stem, [])
    cx = resilience._Ctx(tmp_path, {"components": {"cluster-autoscaler": {"present": True}}})
    out = resilience._n_plus_one(cx)
    assert out["total_ok"] is True  # 6 cores of requests against 20 cores elsewhere
    assert out["ok"] is False and out["pools_short"][0]["eligible_nodes"] == ["app2"]  # but the app pods may only go to app2, which has 1 core left
    assert out["pools_short"][0]["free_cpu"] == 1.0  # 4 cores minus 2.5 of the app pod minus 0.5 of the DaemonSet pod
    assert out["autoscaler"] is True and out["autoscaler_name"] == "cluster-autoscaler"


# ---------- backup signals ----------


def test_backup_signals_count_only_live_cronjobs(tmp_path):
    today = dt.date.today()
    recent = (today - dt.timedelta(days=2)).isoformat() + "T02:00:00Z"
    old = (today - dt.timedelta(days=90)).isoformat() + "T02:00:00Z"
    crons = [
        {"metadata": {"namespace": "p", "name": "pg-backup"}, "spec": {}, "status": {"lastSuccessfulTime": recent}},
        {"metadata": {"namespace": "p", "name": "mysql-dump"}, "spec": {"suspend": True}, "status": {"lastSuccessfulTime": recent}},
        {"metadata": {"namespace": "p", "name": "neo-snapshot", "creationTimestamp": "2026-01-01T00:00:00Z"}, "spec": {}, "status": {"lastSuccessfulTime": old}},
        {"metadata": {"namespace": "p", "name": "new-backup", "creationTimestamp": today.isoformat() + "T00:00:00Z"}, "spec": {}, "status": {}},
        {"metadata": {"namespace": "p", "name": "web"}, "spec": {}, "status": {}},
    ]
    _write(tmp_path, "cronjobs", crons)
    cx = Context(tmp_path, {}, {}, {"name": "prod"})
    sig = cx.backup_signals()
    assert sig["backup_cronjobs"] == ["p/pg-backup", "p/new-backup"]
    assert sig["stale_backup_cronjobs"] == ["p/mysql-dump (suspended)", "p/neo-snapshot (last success 90 days ago)"]
    assert sig["any"] is True


# ---------- alert rule classes ----------


def test_app_rules_split_by_what_they_look_at():
    assert observability.classify_expr("kafka_consumergroup_lag > 1000") == "app"
    assert observability.classify_expr("image_inference_success_rate < 0.9") == "app"
    assert observability.classify_expr("myapp_build_info == 1") == "app-cause"
    assert observability.classify_expr("myapp_workers_total < 3") == "app-cause"
    assert observability.classify_expr('sum(rate(http_requests_total{code=~"5.."}[5m])) > 0') == "symptom"
    assert observability.classify_expr('sum(rate(gateway_requests_total{status!="ok"}[5m])) / sum(rate(gateway_requests_total[5m])) > 0.01') == "app"  # a status selector is a failure signal
    assert observability.classify_expr("gateway_requests_total > 0", "GatewayErrorRateHigh") == "app"  # the rule name says what it looks at


# ---------- private routes ----------


def test_private_routes_scoped_to_node_subnets_with_exclusions(tmp_path):
    (tmp_path / "aws").mkdir()
    tables = [
        {
            "RouteTableId": "rtb-nodes",
            "Associations": [{"SubnetId": "subnet-a"}],
            "Routes": [
                {"DestinationCidrBlock": "10.20.0.0/16", "VpcPeeringConnectionId": "pcx-1"},
                {"DestinationCidrBlock": "10.30.0.0/16", "TransitGatewayId": "tgw-1"},
                {"DestinationCidrBlock": "172.16.0.0/12", "NetworkInterfaceId": "eni-fw"},
            ],
        },
        {"RouteTableId": "rtb-db", "Associations": [{"SubnetId": "subnet-db"}], "Routes": [{"DestinationCidrBlock": "10.99.0.0/16", "VpcPeeringConnectionId": "pcx-2"}]},
        {"RouteTableId": "rtb-main", "Associations": [{"Main": True}], "Routes": []},
    ]
    (tmp_path / "aws" / "describe-route-tables.json").write_text(json.dumps({"RouteTables": tables}))
    r = vpccni._private_routes(tmp_path, {"subnet-a"}, ["10.20.0.0/16"])
    assert r["scoped_to_node_subnets"] is True
    assert r["peering"] == 1 and r["transit_gateway"] == 1 and r["appliance"] == 1  # the database subnet's peering route does not count
    assert r["excluded"] == ["10.20.0.0/16"] and r["destinations"] == ["10.30.0.0/16", "172.16.0.0/12"]
    unscoped = vpccni._private_routes(tmp_path, set(), [])
    assert unscoped["peering"] == 2 and unscoped["scoped_to_node_subnets"] is False


def test_node_subnets_from_instances(tmp_path):
    (tmp_path / "aws").mkdir()
    (tmp_path / "aws" / "ec2-instances-imds.json").write_text(json.dumps([{"id": "i-1", "subnet": "subnet-a"}, {"id": "i-2"}]))
    assert vpccni._node_subnets(tmp_path, [{"provider_id": "aws:///ap-northeast-2a/i-1"}, {"provider_id": "aws:///ap-northeast-2a/i-2"}]) == {"subnet-a"}


def test_snat_port_mode_falls_back_to_the_addon_version():
    assert vpccni.snat_port_mode("1.19.0", None, False) == "random-fully"
    assert vpccni.snat_port_mode(None, None, False) == "unknown"


# ---------- nginx ----------


def test_nginx_version_anywhere_in_the_tag(tmp_path):
    from tests.test_nginx_controller import _controller
    from tests.test_nginx_controller import _write as _w

    _w(tmp_path, "deployments", [_controller("rancher/nginx-ingress-controller:nginx-1.2.1-rancher1", args=["--validating-webhook=:8443"])])
    for stem in ("daemonsets", "validatingwebhookconfigurations.admissionregistration.k8s.io", "networkpolicies.networking.k8s.io", "policyendpoints.networking.k8s.aws"):
        _w(tmp_path, stem, [])
    n = traffic._nginx(tmp_path, [], {"cluster": {"platform": "eks"}})
    assert n["version"] == "1.2.1" and n["vulnerable"] is True and n["webhook_network_policy"]["mitigated"] is False


def test_nginx_webhook_closed_by_network_policy(tmp_path):
    from tests.test_nginx_controller import _controller
    from tests.test_nginx_controller import _write as _w

    c = _controller("registry.k8s.io/ingress-nginx/controller:v1.11.0", args=["--validating-webhook=:8443"])
    c["spec"]["template"]["metadata"] = {"labels": {"app.kubernetes.io/name": "ingress-nginx"}}
    _w(tmp_path, "deployments", [c])
    np = {
        "metadata": {"namespace": c["metadata"]["namespace"], "name": "webhook-apiserver-only"},
        "spec": {
            "podSelector": {"matchLabels": {"app.kubernetes.io/name": "ingress-nginx"}},
            "policyTypes": ["Ingress"],
            "ingress": [{"from": [{"ipBlock": {"cidr": "10.0.0.0/8"}}], "ports": [{"port": 8443}]}, {"ports": [{"port": 80}, {"port": 443}]}],
        },
    }
    _w(tmp_path, "networkpolicies.networking.k8s.io", [np])
    _w(tmp_path, "policyendpoints.networking.k8s.aws", [{"metadata": {"name": "x"}}])
    aws_node = {"metadata": {"namespace": "kube-system", "name": "aws-node"}, "spec": {"template": {"spec": {"containers": [{"name": "aws-eks-nodeagent", "args": ["--enable-network-policy=true"]}]}}}}
    _w(tmp_path, "daemonsets", [aws_node])
    _w(tmp_path, "validatingwebhookconfigurations.admissionregistration.k8s.io", [])
    n = traffic._nginx(tmp_path, [], {"cluster": {"platform": "eks"}})
    wn = n["webhook_network_policy"]
    assert n["vulnerable"] is True and wn["policies"] == [f"{np['metadata']['namespace']}/webhook-apiserver-only"] and wn["enforced"] is True and wn["mitigated"] is True
    # the same policy on an EKS cluster whose CNI does not enforce policies mitigates nothing
    aws_node["spec"]["template"]["spec"]["containers"][0]["args"] = ["--enable-network-policy=false"]
    _w(tmp_path, "daemonsets", [aws_node])
    assert traffic._nginx(tmp_path, [], {"cluster": {"platform": "eks"}})["webhook_network_policy"]["mitigated"] is False
    # a rule that admits every namespace keeps the webhook open
    np["spec"]["ingress"][0]["from"] = [{"namespaceSelector": {}}]
    aws_node["spec"]["template"]["spec"]["containers"][0]["args"] = ["--enable-network-policy=true"]
    _w(tmp_path, "daemonsets", [aws_node])
    _w(tmp_path, "networkpolicies.networking.k8s.io", [np])
    assert traffic._nginx(tmp_path, [], {"cluster": {"platform": "eks"}})["webhook_network_policy"]["mitigated"] is False


# ---------- latest hour with requests ----------


def test_latest_hour_skips_idle_hours_and_weights_p95_by_requests():
    p95 = {"avg": 5.0, "last": 9.0, "last_at": "T3", "series": [{"t": "T3", "v": 9.0}, {"t": "T1", "v": 1.0}]}
    req = {"series": [{"t": "T4", "v": 0}, {"t": "T3", "v": 2}, {"t": "T2", "v": 0}, {"t": "T1", "v": 998}]}
    out = _latest_hour(p95, req)
    assert out["p95_s_weighted"] == 1.016  # 998 requests at 1 s and 2 at 9 s
    assert out["p95_s_last_1h"] == 9.0 and out["requests_last_1h"] == 2 and out["hours_since_requests"] == 1  # the newest hour T4 had no requests
    assert _latest_hour(p95, None)["p95_s_weighted"] == 5.0  # no request series: fall back to the plain average

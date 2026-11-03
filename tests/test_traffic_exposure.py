"""Exposure rows of the traffic summary read the load balancer's security groups: a database port open to 0.0.0.0/0 is `open`, one limited to listed addresses is `allow-list`, an NLB without security groups or with unread groups is told apart, and an NLB built outside the cluster names the Services its TargetGroupBindings bind."""

from __future__ import annotations

import json

from lib import traffic
from lib.traffic import sg_exposure

KAFKA_ARN = "arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-kafka/1"
DB_ARN = "arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-mysql/1"
KAFKA_DNS = "k8s-kafka-1.elb.ap-northeast-2.amazonaws.com"
DB_DNS = "db-shared-1.elb.ap-northeast-2.amazonaws.com"


def _write(tmp_path, rel, data):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")


def _snapshot(tmp_path, *, db_sg=("sg-db",), read=True, db_cidrs=("203.0.113.1/32", "203.0.113.2/32")):
    for stem in ("deployments", "statefulsets", "daemonsets", "endpointslices.discovery.k8s.io", "ingresses.networking.k8s.io"):
        _write(tmp_path, f"objects/{stem}.json", {"items": []})
    _write(
        tmp_path,
        "objects/services.json",
        {
            "items": [
                {
                    "metadata": {"namespace": "middleware", "name": "kafka-external", "annotations": {}},
                    "spec": {"type": "LoadBalancer", "ports": [{"port": 9094, "targetPort": 9094}, {"port": 443, "targetPort": 9094}]},
                    "status": {"loadBalancer": {"ingress": [{"hostname": KAFKA_DNS}]}},
                },
                {"metadata": {"namespace": "prod-a", "name": "mysql"}, "spec": {"type": "ClusterIP", "ports": [{"port": 3306}]}},
            ]
        },
    )
    _write(
        tmp_path,
        "objects/targetgroupbindings.elbv2.k8s.aws.json",
        {"items": [{"metadata": {"namespace": "prod-a", "name": "mysql-tgb"}, "spec": {"targetGroupARN": DB_ARN, "serviceRef": {"name": "mysql", "port": 3306}, "targetType": "ip"}}]},
    )
    _write(
        tmp_path,
        "aws/alb-metrics.json",
        {
            "window_hours": 24,
            "lbs": [
                {"arn": "lb1", "dim": "net/kafka/1", "name": "kafka-lb", "dns": KAFKA_DNS, "type": "network", "scheme": "internet-facing", "security_groups": ["sg-kafka"], "target_groups": ["tg-kafka"]},
                {"arn": "lb2", "dim": "net/db/1", "name": "db-shared", "dns": DB_DNS, "type": "network", "scheme": "internet-facing", "security_groups": list(db_sg), "target_groups": ["tg-mysql"]},
            ],
            "target_groups": [
                {"arn": KAFKA_ARN, "dim": "targetgroup/tg-kafka/1", "name": "tg-kafka", "lb": "kafka-lb", "lb_dim": "net/kafka/1", "lb_type": "network", "protocol": "TCP", "port": 9094, "target_type": "ip"},
                {"arn": DB_ARN, "dim": "targetgroup/tg-mysql/1", "name": "tg-mysql", "lb": "db-shared", "lb_dim": "net/db/1", "lb_type": "network", "protocol": "TCP", "port": 3306, "target_type": "ip"},
            ],
            "security_groups_read": read,
            "security_groups": {
                "sg-kafka": {
                    "name": "k8s-kafka",
                    "description": "",
                    "inbound": [
                        {"protocol": "tcp", "from_port": 9094, "to_port": 9094, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": 0},
                        {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": 0},
                    ],
                },
                "sg-db": {"name": "db-shared-nlb", "description": "office only", "inbound": [{"protocol": "tcp", "from_port": 3306, "to_port": 3311, "cidrs": list(db_cidrs), "cidrs_v6": [], "prefix_lists": [], "security_groups": 0}]},
            }
            if read
            else {},
            "metrics": {"lb": {}, "tg": {}},
            "errors": [],
        },
    )


def _rows(tmp_path):
    out = traffic.analyze(tmp_path, {"namespaces": {"prod_like": ["prod-a"]}})
    return {r["target"]: r for r in out["exposure"]}, out


def test_open_security_group_and_allow_list_are_told_apart(tmp_path):
    _snapshot(tmp_path)
    rows, out = _rows(tmp_path)
    kafka = rows["loadbalancer/middleware/kafka-external"]
    assert kafka["sg_exposure"] == "open"
    assert kafka["allowed_cidrs"] == {"9094": ["0.0.0.0/0"], "443": ["0.0.0.0/0"]}
    assert kafka["note"] == "DB port open to the internet by the security group"
    db = rows["nlb/db-shared"]
    assert db["sg_exposure"] == "allow-list"
    assert db["allowed_cidrs"] == {"3306": ["203.0.113.1/32", "203.0.113.2/32"]}
    assert db["bound_services"] == ["prod-a/mysql"]
    assert db["prod"] is True
    assert "1 TargetGroupBindings bind it to prod-a/mysql" in db["note"]
    assert "limited by the security group to listed addresses" in db["note"]
    assert out["alb"]["lbs"][1]["security_groups_read"] is True
    assert [r["target"] for r in out["db_exposed"]] == ["loadbalancer/middleware/kafka-external", "nlb/db-shared"]


def test_nlb_without_security_group_counts_as_open(tmp_path):
    _snapshot(tmp_path, db_sg=())
    rows, out = _rows(tmp_path)
    assert rows["nlb/db-shared"]["sg_exposure"] == "no-security-group"
    assert "no security group" in rows["nlb/db-shared"]["note"]
    assert out["alb"]["lbs"][1]["security_groups_read"] is None


def test_unread_security_groups_say_so(tmp_path):
    _snapshot(tmp_path, read=False)
    rows, out = _rows(tmp_path)
    assert rows["nlb/db-shared"]["sg_exposure"] == "not-read"
    assert rows["loadbalancer/middleware/kafka-external"]["sg_exposure"] == "not-read"
    assert "could not be read" in rows["nlb/db-shared"]["note"]


def test_sg_exposure_rules():
    lb = {"security_groups": ["sg"], "security_groups_read": True, "inbound_rules": [{"protocol": "-1", "from_port": None, "to_port": None, "cidrs": ["10.0.0.0/8"], "cidrs_v6": [], "prefix_lists": [], "security_groups": 2}]}
    assert sg_exposure(lb, [5432]) == {"sg_exposure": "allow-list", "allowed_cidrs": {"5432": ["10.0.0.0/8", "2 security group(s)"]}}
    lb["inbound_rules"].append({"protocol": "tcp", "from_port": 5432, "to_port": 5432, "cidrs": [], "cidrs_v6": ["::/0"], "prefix_lists": [], "security_groups": 0})
    assert sg_exposure(lb, [5432])["sg_exposure"] == "open"
    assert sg_exposure(None, [5432]) == {"sg_exposure": None, "allowed_cidrs": {}}

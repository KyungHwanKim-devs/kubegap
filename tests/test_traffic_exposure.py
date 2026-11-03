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
                {
                    "arn": "lb2",
                    "dim": "net/db/1",
                    "name": "db-shared",
                    "dns": DB_DNS,
                    "type": "network",
                    "scheme": "internet-facing",
                    "security_groups": list(db_sg),
                    "listeners": [{"port": 3306, "protocol": "TCP", "target_groups": ["tg-mysql"]}, {"port": 3307, "protocol": "TCP", "target_groups": ["tg-mysql"]}],
                    "target_groups": ["tg-mysql"],
                },
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
                        {"protocol": "tcp", "from_port": 9094, "to_port": 9094, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []},
                        {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []},
                    ],
                },
                "sg-db": {"name": "db-shared-nlb", "description": "office only", "inbound": [{"protocol": "tcp", "from_port": 3306, "to_port": 3311, "cidrs": list(db_cidrs), "cidrs_v6": [], "prefix_lists": [], "security_groups": []}]},
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
    assert kafka["allowed_sources"] == {"9094": 1, "443": 1}
    assert kafka["open_ports"] == [443, 9094]
    assert kafka["note"] == "DB port open to the internet by the security group"
    db = rows["nlb/db-shared"]
    assert db["sg_exposure"] == "allow-list"
    assert db["allowed_sources"] == {"3306": 2, "3307": 2}  # judged on the listener ports, not the target group port
    assert db["target_group_ports"] == [3306]
    assert db["ports"] == [3306, 3307]  # the listener ports, which the security group filters
    assert "203.0.113" not in json.dumps(db)  # counts only, never the addresses
    assert db["bound_services"] == ["prod-a/mysql"]
    assert db["prod"] is True
    assert "1 TargetGroupBinding binds it to prod-a/mysql" in db["note"]
    assert "limited by the security group to listed addresses" in db["note"]
    assert out["alb"]["lbs"][1]["security_groups_read"] is True
    assert [r["target"] for r in out["db_exposed"]] == ["loadbalancer/middleware/kafka-external", "nlb/db-shared"]


def test_nlb_without_security_group_counts_as_open(tmp_path):
    _snapshot(tmp_path, db_sg=())
    rows, out = _rows(tmp_path)
    assert rows["nlb/db-shared"]["sg_exposure"] == "no-security-group"
    assert "no security group on the load balancer" in rows["nlb/db-shared"]["note"]
    assert out["alb"]["lbs"][1]["security_groups_read"] is None


def test_unread_security_groups_say_so(tmp_path):
    _snapshot(tmp_path, read=False)
    rows, _ = _rows(tmp_path)
    assert rows["nlb/db-shared"]["sg_exposure"] == "not-read"
    assert rows["loadbalancer/middleware/kafka-external"]["sg_exposure"] == "not-read"
    assert "could not be read" in rows["nlb/db-shared"]["note"]


def test_missing_group_in_response_means_not_read(tmp_path):
    _snapshot(tmp_path, db_sg=("sg-db", "sg-other"))
    rows, out = _rows(tmp_path)
    assert out["alb"]["lbs"][1]["security_groups_read"] is False
    assert rows["nlb/db-shared"]["sg_exposure"] == "not-read"


def test_service_lb_without_a_described_load_balancer_is_unmatched(tmp_path):
    _snapshot(tmp_path)
    d = json.loads((tmp_path / "aws" / "alb-metrics.json").read_text())
    d["lbs"][0]["dns"] = "someone-else.elb.amazonaws.com"
    (tmp_path / "aws" / "alb-metrics.json").write_text(json.dumps(d))
    rows, _ = _rows(tmp_path)
    kafka = rows["loadbalancer/middleware/kafka-external"]
    assert kafka["sg_exposure"] == "unmatched"
    assert "no described load balancer matched" in kafka["note"]


def test_only_database_ports_decide(tmp_path):
    _snapshot(tmp_path)
    d = json.loads((tmp_path / "aws" / "alb-metrics.json").read_text())
    # the kafka Service: 9094 allow-listed, 443 open to everyone but forwarding to a non-database port -> the row is allow-list, not open
    d["security_groups"]["sg-kafka"]["inbound"][0]["cidrs"] = ["203.0.113.9/32"]
    svc = json.loads((tmp_path / "objects" / "services.json").read_text())
    svc["items"][0]["spec"]["ports"][1]["targetPort"] = 8443
    (tmp_path / "objects" / "services.json").write_text(json.dumps(svc))
    # the db NLB gains a public 443 listener forwarding to a non-database target group
    d["lbs"][1]["listeners"].append({"port": 443, "protocol": "TCP", "target_groups": ["tg-web"]})
    d["security_groups"]["sg-db"]["inbound"].append({"protocol": "tcp", "from_port": 443, "to_port": 443, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []})
    (tmp_path / "aws" / "alb-metrics.json").write_text(json.dumps(d))
    rows, _ = _rows(tmp_path)
    assert rows["loadbalancer/middleware/kafka-external"]["sg_exposure"] == "allow-list"
    assert rows["nlb/db-shared"]["sg_exposure"] == "allow-list"
    assert rows["nlb/db-shared"]["ports"] == [443, 3306, 3307]  # every listener is listed, only the database ones are judged


def test_describe_load_balancers_failure_is_not_read(tmp_path):
    _snapshot(tmp_path)
    (tmp_path / "aws" / "alb-metrics.json").write_text(json.dumps({"window_hours": 24, "lbs": [], "target_groups": [], "errors": ["describe-load-balancers: AccessDenied"], "metrics": {"lb": {}, "tg": {}}}))
    rows, _ = _rows(tmp_path)
    assert rows["loadbalancer/middleware/kafka-external"]["sg_exposure"] == "not-read"


def test_listener_parsing():
    from lib.albmetrics import _listener, _tg_name

    assert _tg_name("arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-web/abc") == "tg-web"
    assert _tg_name(None) is None and _tg_name("") is None
    li = {
        "Port": 443,
        "Protocol": "HTTPS",
        "DefaultActions": [
            {
                "Type": "forward",
                "TargetGroupArn": "arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-a/1",
                "ForwardConfig": {"TargetGroups": [{"TargetGroupArn": "arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-b/2", "Weight": 1}, {"Weight": 0}]},
            }
        ],
    }
    assert _listener(li) == {"port": 443, "protocol": "HTTPS", "target_groups": ["tg-a", "tg-b"]}
    assert _listener({"Port": 80, "Protocol": "HTTP", "DefaultActions": [{"Type": "redirect"}]}) == {"port": 80, "protocol": "HTTP", "target_groups": []}


def test_sg_exposure_rules():
    lb = {"security_groups": ["sg"], "security_groups_read": True, "inbound_rules": [{"protocol": "-1", "from_port": None, "to_port": None, "cidrs": ["10.0.0.0/8"], "cidrs_v6": [], "prefix_lists": [], "security_groups": ["sg-a", "sg-b"]}]}
    assert sg_exposure(lb, [5432]) == {"sg_exposure": "allow-list", "allowed_sources": {"5432": 3}, "open_ports": []}  # one CIDR and two referenced groups
    lb["inbound_rules"].append({"protocol": "tcp", "from_port": 5432, "to_port": 5432, "cidrs": [], "cidrs_v6": ["::/0"], "prefix_lists": [], "security_groups": []})
    assert sg_exposure(lb, [5432])["sg_exposure"] == "open"
    assert sg_exposure(None, [5432]) == {"sg_exposure": None, "allowed_sources": {}, "open_ports": []}
    # a UDP rule on the port opens nothing; no covering rule at all is blocked; one open port among allow-listed ones makes the row open
    udp = {"security_groups": ["sg"], "security_groups_read": True, "inbound_rules": [{"protocol": "udp", "from_port": 3306, "to_port": 3306, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []}]}
    assert sg_exposure(udp, [3306])["sg_exposure"] == "blocked"
    mixed = {
        "security_groups": ["sg"],
        "security_groups_read": True,
        "inbound_rules": [
            {"protocol": "tcp", "from_port": 3306, "to_port": 3306, "cidrs": ["203.0.113.1/32"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []},
            {"protocol": "tcp", "from_port": 5432, "to_port": 5432, "cidrs": ["0.0.0.0/0"], "cidrs_v6": [], "prefix_lists": [], "security_groups": []},
        ],
    }
    assert sg_exposure(mixed, [3306, 5432]) == {"sg_exposure": "open", "allowed_sources": {"3306": 1, "5432": 1}, "open_ports": [5432]}

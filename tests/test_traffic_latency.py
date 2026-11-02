"""Latest-hour p95 in the traffic summary: an ALB target group whose one bad hour lifts the 24-hour average still shows that the latest hour is back to normal."""

from __future__ import annotations

import json

from lib import traffic

TG_ARN = "arn:aws:elasticloadbalancing:ap-northeast-2:1:targetgroup/tg-web/1"
TG_DIM = "targetgroup/tg-web/1"
LB_DIM = "app/web/1"


def _write(tmp_path, rel, data):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")


def _snapshot(tmp_path):
    for stem in ("services", "deployments", "statefulsets", "daemonsets", "endpointslices.discovery.k8s.io"):
        _write(tmp_path, f"objects/{stem}.json", {"items": []})
    _write(tmp_path, "objects/targetgroupbindings.elbv2.k8s.aws.json", {"items": [{"metadata": {"namespace": "prod-a", "name": "tgb"}, "spec": {"targetGroupARN": TG_ARN, "serviceRef": {"name": "web", "port": 80}, "targetType": "ip"}}]})
    _write(
        tmp_path,
        "objects/ingresses.networking.k8s.io.json",
        {
            "items": [
                {
                    "metadata": {"namespace": "prod-a", "name": "web", "annotations": {}},
                    "spec": {"ingressClassName": "alb", "rules": [{"host": "www.example.com", "http": {"paths": [{"path": "/", "backend": {"service": {"name": "web", "port": {"number": 80}}}}]}}]},
                }
            ]
        },
    )
    # six hourly p95 points: one at 19.4 s, the latest at 0.05 s; the average 3.49 s is over the fail threshold
    p95 = {"points": 6, "status": "Complete", "sum": 20.944, "max": 19.4475, "min": 0.0495, "last": 0.0527, "avg": 3.4907}
    _write(
        tmp_path,
        "aws/alb-metrics.json",
        {
            "window_hours": 24,
            "lbs": [{"arn": "lb", "dim": LB_DIM, "name": "web", "type": "application", "scheme": "internet-facing", "target_groups": [TG_ARN]}],
            "target_groups": [{"arn": TG_ARN, "dim": TG_DIM, "name": "tg-web", "lb": "web", "lb_dim": LB_DIM, "lb_type": "application", "protocol": "HTTP", "port": 80, "target_type": "ip"}],
            "metrics": {"lb": {LB_DIM: {"RequestCount_Sum": {"sum": 4350.0}, "TargetResponseTime_p95": p95}}, "tg": {TG_DIM: {"RequestCount_Sum": {"sum": 4350.0}, "TargetResponseTime_p95": p95}}},
            "errors": [],
        },
    )


def test_alb_latest_hour_is_carried_to_target_group_lb_and_ingress(tmp_path):
    _snapshot(tmp_path)
    out = traffic.analyze(tmp_path, {"namespaces": {"prod_like": ["prod-a"]}})
    tg = out["alb"]["target_groups"][0]
    assert (tg["p95_s_avg"], tg["p95_s_max_1h"], tg["p95_s_last_1h"]) == (3.4907, 19.4475, 0.0527)
    assert out["alb"]["lbs"][0]["p95_s_last_1h"] == 0.0527
    ing = out["ingresses"][0]
    assert ing["target"] == "prod-a/web"
    assert ing["metrics"]["p95_s_last_1h"] == 0.0527
    assert ing["metrics"]["p95_s_avg"] == 3.4907


def test_missing_latest_hour_is_none(tmp_path):
    _snapshot(tmp_path)
    d = json.loads((tmp_path / "aws" / "alb-metrics.json").read_text())
    for kind in ("lb", "tg"):
        for m in d["metrics"][kind].values():
            m["TargetResponseTime_p95"].pop("last")
    (tmp_path / "aws" / "alb-metrics.json").write_text(json.dumps(d))
    out = traffic.analyze(tmp_path, {"namespaces": {"prod_like": ["prod-a"]}})
    assert out["alb"]["target_groups"][0]["p95_s_last_1h"] is None
    assert out["ingresses"][0]["metrics"]["p95_s_last_1h"] is None

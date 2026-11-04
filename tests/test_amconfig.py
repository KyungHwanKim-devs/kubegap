"""Alertmanager's loaded configuration read through lib/amconfig (#126): the receivers a route names, nested routes, inhibit rules, time intervals,
and what happens when yamlite cannot read the text."""

from __future__ import annotations

import json
from pathlib import Path

from lib import amconfig, stackhealth

EKS_LIKE = """global:
  resolve_timeout: 5m
route:
  receiver: "null"
  group_by:
  - namespace
  routes:
  - receiver: "null"
    matchers:
    - alertname = "Watchdog"
  - receiver: slack-critical
    matchers:
    - severity = "critical"
    routes:
    - receiver: pagerduty
      matchers:
      - team = "infra"
inhibit_rules:
- source_matchers:
  - severity = "critical"
  target_matchers:
  - severity = "warning"
  equal:
  - namespace
receivers:
- name: "null"
- name: slack-critical
  slack_configs:
  - api_url: https://hooks.example/x
- name: pagerduty
  pagerduty_configs:
  - routing_key: k
- name: email-unused
  email_configs:
  - to: a@example.com
time_intervals:
- name: business-hours
  time_intervals:
  - weekdays: ["monday:friday"]
templates:
- /etc/alertmanager/config/*.tmpl
"""


def test_the_routing_tree_receivers_and_inhibit_rules_come_from_the_structure():
    cfg, err = amconfig.parse(EKS_LIKE)
    assert err is None and cfg["route"]["receiver"] == "null"
    assert amconfig.receiver_kinds(cfg) == {"null": [], "slack-critical": ["slack"], "pagerduty": ["pagerduty"], "email-unused": ["email"]}
    assert amconfig.referenced_receivers(cfg) == {"null", "slack-critical", "pagerduty"}  # the nested route's receiver counts
    assert [r["depth"] for r in amconfig.walk_routes(cfg["route"])] == [0, 1, 1, 2]
    assert amconfig.has_time_intervals(cfg) and len(cfg["inhibit_rules"]) == 1


def test_unreadable_text_is_an_error_not_an_empty_configuration():
    assert amconfig.parse("") == (None, "empty")
    cfg, err = amconfig.parse("route: &r\n  receiver: x\n")
    assert cfg is None and err.startswith("YamlError")
    cfg, err = amconfig.parse("- just\n- a list\n")
    assert cfg is None and "not a mapping" in err


def _am_snapshot(tmp_path: Path, original: str) -> tuple[Path, dict]:
    snap = tmp_path / "snap"
    (snap / "objects").mkdir(parents=True)
    (snap / "alertmanager").mkdir()
    (snap / "alertmanager" / "status.json").write_text(json.dumps({"cluster": {"status": "disabled", "peers": []}, "versionInfo": {"version": "0.29.0"}, "config": {"original": original}, "uptime": "x"}), encoding="utf-8")
    return snap, {"stores": {"alertmanager": {"ok": True, "version": "0.29.0"}}}


def test_the_stack_summary_names_the_unused_receiver_and_counts_rules_from_the_parsed_configuration(tmp_path):
    snap, inv = _am_snapshot(tmp_path, EKS_LIKE)
    out = stackhealth._alertmanager(snap, inv)
    assert out["config_parsed"] is True and out["config_parse_error"] is None
    assert out["receivers"] == ["email-unused", "null", "pagerduty", "slack-critical"]  # no receivers.json: the names come from the configuration
    assert out["receivers_unused"] == ["email-unused"] and out["inhibit_rules"] == 1 and out["time_intervals"] is True


def test_an_unparsable_configuration_is_reported_and_nothing_is_counted(tmp_path):
    snap, inv = _am_snapshot(tmp_path, "route: &anchor\n  receiver: x\n")
    out = stackhealth._alertmanager(snap, inv)
    assert out["config_parsed"] is False and out["config_parse_error"].startswith("YamlError")
    assert out["receivers_unused"] == [] and out["inhibit_rules"] == 0 and out["time_intervals"] is False

"""Dashboards and datasources that Helm put into ConfigMaps are read without a Grafana token: kept by the scrubber because of the sidecar
labels, summarised by lib/observability.py, counted by `setup` so the first-run question is asked only for dashboards made in Grafana itself."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from lib import monitoring, observability, scrub, shell
from lib.snapshot import write_private

DASH = {"uid": "09ec8aa1e996d6ffcd6817bbaff4db1b", "title": "Kubernetes / API server", "panels": [{"targets": [{"expr": "sum(rate(apiserver_request_total[5m]))"}]}, {"panels": [{"targets": [{"expr": "up"}]}]}]}
DASH_CM = {"kind": "ConfigMap", "metadata": {"namespace": "monitoring", "name": "kps-apiserver", "labels": {"grafana_dashboard": "1"}, "annotations": {"grafana_folder": "Kubernetes"}}, "data": {"apiserver.json": json.dumps(DASH)}}
DS_YAML = """apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://kps-prometheus:9090/
  isDefault: true
  basicAuth: true
  basicAuthUser: reader
  secureJsonData:
    basicAuthPassword: hunter2hunter2
- name: Alertmanager
  type: alertmanager
  url: http://kps-alertmanager:9093/
"""
DS_CM = {"kind": "ConfigMap", "metadata": {"namespace": "monitoring", "name": "kps-grafana-datasource", "labels": {"grafana_datasource": "1"}}, "data": {"datasource.yaml": DS_YAML}}


def test_scrub_keeps_dashboard_json_and_only_the_safe_fields_of_a_datasource_file():
    cm = scrub.scrub_configmap(copy.deepcopy(DASH_CM))
    assert json.loads(cm["data"]["apiserver.json"]) == DASH and cm[scrub.MARK]["kept_keys"] == ["apiserver.json"]
    ds = scrub.scrub_configmap(copy.deepcopy(DS_CM))
    text = json.dumps(ds)
    assert "hunter2hunter2" not in text and "reader" not in text
    assert ds["data"]["datasource.yaml"]["datasources"] == [
        {"name": "Prometheus", "type": "prometheus", "url": "http://kps-prometheus:9090/", "isDefault": True},
        {"name": "Alertmanager", "type": "alertmanager", "url": "http://kps-alertmanager:9093/", "isDefault": False},
    ]
    plain = scrub.scrub_configmap({"kind": "ConfigMap", "metadata": {"namespace": "x", "name": "y"}, "data": {"a.json": json.dumps(DASH)}})
    assert plain["data"]["a.json"] == {"len": len(json.dumps(DASH)), "shape": scrub.shape(json.dumps(DASH))}, "without the sidecar label a JSON value is dropped like any other"


def _snap(tmp_path: Path, cms: list[dict], with_api: bool = False) -> Path:
    snap = tmp_path / "snap"
    write_private(snap / "objects" / "configmaps.json", json.dumps({"kind": "List", "items": [scrub.scrub_configmap(copy.deepcopy(c)) for c in cms]}))
    write_private(snap / "grafana" / "health.json", json.dumps({"database": "ok", "version": "12.2.1"}))
    if with_api:
        write_private(snap / "grafana" / "dashboards.json", json.dumps([{"uid": "a"}, {"uid": "b"}]))
        write_private(snap / "grafana" / "datasources.json", json.dumps([{"name": "P", "type": "prometheus", "url": "u", "isDefault": True}]))
    return snap


def test_summary_reads_the_lists_from_the_configmaps_without_a_token(tmp_path):
    g = observability._grafana(_snap(tmp_path, [DASH_CM, DS_CM]), [{"expr": "rate(apiserver_request_total[5m]) > 1"}, {"expr": "kube_pod_status_phase == 1"}])
    assert g["lists_source"] == "provisioned configmaps" and g["dashboards"] == 1
    assert g["datasources"][0] == {"name": "Prometheus", "type": "prometheus", "url": "http://kps-prometheus:9090/", "default": True}
    dj = g["dashboards_json"]
    assert dj["available"] and dj["source"] == "provisioned configmaps" and dj["read"] == 1
    assert dj["rows"][0] == {"uid": DASH["uid"], "title": "Kubernetes / API server", "panels_with_expr": 2, "metrics": 2, "folder": "Kubernetes"}
    assert dj["alert_metrics_without_panel"] == ["kube_pod_status_phase"]
    none = observability._grafana(_snap(tmp_path / "n", []), [])
    assert none["lists_source"] == "none" and none["dashboards"] == "no auth (config.yaml grafana_api_token)" and not none["dashboards_json"]["available"]
    api = observability._grafana(_snap(tmp_path / "a", [DASH_CM], with_api=True), [])
    assert api["lists_source"] == "api" and api["dashboards"] == 2, "with a token the API lists win"


def test_setup_counts_the_configmaps_and_reads_the_total_from_grafana_metrics(monkeypatch):
    def kubectl_json(args, **kw):
        label = args[args.index("-l") + 1]
        return {"items": [{}] * (25 if label == "grafana_dashboard" else 1)}, shell.Result(cmd=["kubectl"], code=0)

    class R:
        def __init__(self, ok, body):
            self.ok, self.body = ok, body

    calls = []

    def get(url, params=None, headers=None, **kw):
        calls.append(url)
        if url.endswith("/metrics"):
            return R(True, "# HELP grafana_stat_totals_dashboard total amount of dashboards\ngrafana_stat_totals_dashboard 30\n")
        return R(True, json.dumps({"data": {"result": [{"value": [0, "31"]}]}}))

    monkeypatch.setattr(monitoring.kube, "kubectl_json", kubectl_json)
    monkeypatch.setattr(monitoring.http, "get", get)
    g = {"ok": True, "access": "config"}
    p = monitoring.grafana_provisioned("ctx", None, g, "http://grafana:3000", {"ok": True, "access": "config"}, "http://prom:9090")
    assert p == {"dashboards": 25, "datasources": 1, "total_dashboards": 30, "total_source": "grafana /metrics", "error": None}
    assert calls == ["http://grafana:3000/metrics"], "Grafana's own /metrics answers; Prometheus is not asked"
    assert monitoring.describe_provisioned(p) == "read without a token: 25 dashboard and 1 datasource ConfigMaps; Grafana counts 30, so 5 made in Grafana itself need a token to be listed"
    assert monitoring.describe_provisioned({"dashboards": 25, "datasources": 1, "total_dashboards": 25}).endswith("Grafana counts 25, nothing missing")
    assert monitoring.describe_provisioned({"dashboards": 0, "datasources": 0}).startswith("no dashboard or datasource ConfigMaps")
    monkeypatch.setattr(monitoring.http, "get", lambda url, params=None, headers=None, **kw: R(False, "") if url.endswith("/metrics") else R(True, json.dumps({"data": {"result": [{"value": [0, "31"]}]}})))
    p2 = monitoring.grafana_provisioned("ctx", None, g, "http://grafana:3000", {"ok": True, "access": "config"}, "http://prom:9090")
    assert p2["total_dashboards"] == 31 and p2["total_source"] == "prometheus", "when Grafana's /metrics is closed, a Prometheus that scrapes it is asked"
    p3 = monitoring.grafana_provisioned("ctx", None, {"ok": False}, None, {"ok": False}, None)
    assert p3["total_dashboards"] is None and p3["dashboards"] == 25
    assert monitoring._total_from_text('grafana_stat_totals_dashboard{org="1"} 7\n') == 7 and monitoring._total_from_text("nothing") is None

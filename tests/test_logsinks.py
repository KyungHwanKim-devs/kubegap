"""Where the logs go, read from the shipper's configuration (lib/logsinks.py, #174). The texts are the shapes of real ConfigMaps: the fluent-bit
classic format of the maintainer's k3s cluster, the fluent-bit chart's own example, a fluentd match block and a promtail clients block."""

from __future__ import annotations

from lib import firstrun, logsinks, shell
from lib.config import Config

FLUENT_BIT = """[SERVICE]
    Flush         1
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
[FILTER]
    Name                kubernetes
    Match               kube.*
[OUTPUT]
    Name            es
    Match           kube.*
    Host            elasticsearch-master.logging.svc.cluster.local
    Port            9200
    Logstash_Format On
[OUTPUT]
    Name            stdout
    Match           *
"""
FLUENT_BIT_YAML = """pipeline:
  outputs:
    - name: loki
      match: "*"
      host: loki.observability.example.internal
      port: 3100
    - name: cloudwatch_logs
      match: host.*
      region: ap-northeast-2
"""
FLUENTD = """<source>
  @type tail
</source>
<match kube.**>
  @type elasticsearch
  host es.logging.svc
  port 9200
</match>
<match **>
  @type cloudwatch_logs
  log_group_name app
</match>
"""
PROMTAIL = """server:
  http_listen_port: 3101
clients:
  - url: http://loki-gateway.obs.example.internal/loki/api/v1/push
scrape_configs: []
"""


def test_classic_fluent_bit_outputs_name_the_store_and_drop_stdout():
    out = logsinks.parse_outputs(FLUENT_BIT, "fluent-bit")
    assert out == [{"plugin": "es", "host": "elasticsearch-master.logging.svc.cluster.local", "port": 9200, "url": None}]


def test_yaml_fluent_bit_fluentd_and_promtail_outputs():
    y = logsinks.parse_outputs(FLUENT_BIT_YAML, "fluent-bit")
    assert [o["plugin"] for o in y] == ["loki", "cloudwatch_logs"] and y[0]["host"] == "loki.observability.example.internal" and y[0]["port"] == 3100
    f = logsinks.parse_outputs(FLUENTD, "fluentd")
    assert [(o["plugin"], o["host"]) for o in f] == [("elasticsearch", "es.logging.svc"), ("cloudwatch_logs", None)]
    p = logsinks.parse_outputs(PROMTAIL, "promtail")
    assert p == [{"plugin": "loki", "host": None, "port": None, "url": "http://loki-gateway.obs.example.internal/loki/api/v1/push"}]


def _fake_kubectl(daemonsets, configmaps, services):
    def f(args, **kw):
        ok = shell.Result(cmd=["kubectl"], code=0)
        if args[:2] == ["get", "daemonsets"]:
            return {"items": daemonsets}, ok
        if args[:2] == ["get", "configmaps"]:
            return {"items": configmaps.get(args[3], [])}, ok
        if args[:2] == ["get", "svc"]:
            return {"items": services}, ok
        raise AssertionError(args)

    return f


def _ds(ns, name):
    return {"metadata": {"namespace": ns, "name": name}}


def _cm(ns, name, data):
    return {"metadata": {"namespace": ns, "name": name}, "data": data}


def _svc(ns, name, port):
    return {"metadata": {"namespace": ns, "name": name}, "spec": {"ports": [{"port": port}]}}


def test_detect_reads_only_the_shipper_namespace_and_names_the_store(monkeypatch):
    calls = []
    fake = _fake_kubectl(
        [_ds("logging", "fluent-bit"), _ds("kube-system", "kube-proxy")],
        {"logging": [_cm("logging", "fluent-bit-config", {"fluent-bit.conf": FLUENT_BIT})]},
        [_svc("logging", "elasticsearch-master", 9200), _svc("logging", "elasticsearch-master-headless", 9200)],
    )
    monkeypatch.setattr(logsinks.kube, "kubectl_json", lambda args, **kw: (calls.append(args), fake(args, **kw))[1])
    got = logsinks.detect("ctx")
    assert got["shippers"] == [{"namespace": "logging", "name": "fluent-bit", "kind": "fluent-bit"}]
    assert got["logs_go_to"] == ["elasticsearch"] and got["loki_outside"] is None
    assert got["outputs"][0]["source"] == "configmap logging/fluent-bit-config:fluent-bit.conf"
    assert got["stores"] == [{"kind": "elasticsearch", "namespace": "logging", "name": "elasticsearch-master", "port": 9200}]
    assert [c[:3] for c in calls if c[1] == "configmaps"] == [["get", "configmaps", "-n"]] and calls[1][3] == "logging", "ConfigMaps of the shipper's namespace only"
    assert logsinks.explain(got) == "logs go to elasticsearch (fluent-bit output es → elasticsearch-master.logging.svc.cluster.local:9200, configmap logging/fluent-bit-config:fluent-bit.conf)"
    assert logsinks.explain(got, "ko").startswith("로그는 elasticsearch (fluent-bit 출력 es → ") and logsinks.explain(got, "ko").endswith("로 가요")


def test_a_loki_outside_the_cluster_is_found_in_the_shipper_config(monkeypatch):
    fake = _fake_kubectl([_ds("obs", "promtail")], {"obs": [_cm("obs", "promtail", {"promtail.yaml": PROMTAIL})]}, [])
    monkeypatch.setattr(logsinks.kube, "kubectl_json", fake)
    got = logsinks.detect("ctx")
    assert got["logs_go_to"] == ["loki"] and got["loki_outside"] == "http://loki-gateway.obs.example.internal/loki/api/v1/push"


def test_without_a_shipper_nothing_is_claimed(monkeypatch):
    monkeypatch.setattr(logsinks.kube, "kubectl_json", _fake_kubectl([], {}, [_svc("logging", "elasticsearch-master", 9200)]))
    got = logsinks.detect("ctx")
    assert got["shippers"] == [] and got["outputs"] == [] and got["logs_go_to"] == ["elasticsearch"], "a log store Service alone says the logs go there"
    monkeypatch.setattr(logsinks.kube, "kubectl_json", _fake_kubectl([], {}, []))
    assert logsinks.explain(logsinks.detect("ctx")) is None


def _setup_with(sinks):
    mon = {k: {"kind": k, "ok": k != "loki", "access": None if k == "loki" else "port-forward", "service": None if k == "loki" else {"namespace": "m", "name": k, "port": 80}} for k in firstrun.STORES}
    return {"cluster": {"reachable": True, "platform": "k3s", "node_count": 2}, "monitoring": mon, "log_sinks": sinks}


def test_loki_is_not_asked_when_the_logs_go_elsewhere_and_the_report_is_told():
    es = {
        "shippers": [{"namespace": "logging", "name": "fluent-bit", "kind": "fluent-bit"}],
        "outputs": [{"plugin": "es", "host": "es", "port": 9200, "url": None, "shipper": "fluent-bit", "source": "configmap logging/fluent-bit-config:fluent-bit.conf"}],
        "stores": [],
        "logs_go_to": ["elasticsearch"],
        "loki_outside": None,
        "error": None,
    }
    ids = [q["id"] for q in firstrun.questions(_setup_with(es), Config({"grafana_api_token": "x"}), None)]
    assert "stores" not in ids
    notes = firstrun.noted(_setup_with(es), Config(), None)
    assert notes == ["loki: not asked. logs go to elasticsearch (fluent-bit output es → es:9200, configmap logging/fluent-bit-config:fluent-bit.conf); Loki is not read"]
    assert firstrun.noted(_setup_with(es), Config(), None, language="ko") == ["loki: 묻지 않았어요. 로그는 elasticsearch (fluent-bit 출력 es → es:9200, configmap logging/fluent-bit-config:fluent-bit.conf)로 가요. Loki는 읽지 않아요"]
    assert firstrun.noted(_setup_with(es), Config({"loki_url": "http://l:3100"}), None) == []
    text = firstrun.render([], "ctx", None, notes)
    assert text.splitlines()[-2].startswith("note loki: not asked") and "could not see" in text.splitlines()[-1]


def test_loki_is_still_asked_without_a_shipper_or_with_a_loki_output():
    none = {"shippers": [], "outputs": [], "stores": [], "logs_go_to": [], "loki_outside": None, "error": None}
    assert "stores" in [q["id"] for q in firstrun.questions(_setup_with(none), Config({"grafana_api_token": "x"}), None)]
    outside = {
        "shippers": [{"namespace": "obs", "name": "promtail", "kind": "promtail"}],
        "outputs": [{"plugin": "loki", "host": None, "port": None, "url": "http://loki.example.internal:3100/loki/api/v1/push", "shipper": "promtail", "source": "configmap obs/promtail:promtail.yaml"}],
        "stores": [],
        "logs_go_to": ["loki"],
        "loki_outside": "http://loki.example.internal:3100/loki/api/v1/push",
        "error": None,
    }
    q = next(q for q in firstrun.questions(_setup_with(outside), Config({"grafana_api_token": "x"}), None) if q["id"] == "stores")
    assert "loki=http://loki.example.internal:3100/loki/api/v1/push" in q["explain"] and "loki=http://loki.example.internal:3100/loki/api/v1/push" in q["typed"]
    assert firstrun.noted(_setup_with(outside), Config(), None) == []

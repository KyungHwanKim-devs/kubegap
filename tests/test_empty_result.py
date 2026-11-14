"""A metric check that gets no series back says why (#141): the names its query cites against metrics/series-present.json, a skip when one has no series,
a pass counted as `empty` when every name is there, `rule.empty: skip` when the check wants no verdict on an empty result; and the pieces around it."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from lib.collection import prom
from lib.foundations import metricnames
from lib.judgement import evaluate

ROOT = Path(__file__).resolve().parent.parent
INV = {"cluster": {"platform": "k3s"}, "namespaces": {"prod_like": []}, "scale": {"name": "small", "source": "guessed"}, "nodes": {"nodes": []}}


def _snap(tmp_path, metric: dict | None, present: dict | None):
    (tmp_path / "metrics").mkdir()
    (tmp_path / "inventory.json").write_text(json.dumps(INV))
    if metric is not None:
        (tmp_path / "metrics" / "q.json").write_text(json.dumps(metric))
    if present is not None:
        (tmp_path / "metrics" / "series-present.json").write_text(json.dumps({"names": present}))
    return evaluate.Context(tmp_path, INV, {}, "small")


def _check(**kw):
    c = {"id": "t.metric", "name": "t", "area": "t", "type": "metric", "inputs": ["q"], "rule": {"expr": "value > 0"}, "evidence": "f'{value}'", "severity_default": "low", "profiles": ["lab"]}
    c.update(kw)
    return c


EMPTY = {"ok": True, "result": []}


def test_an_empty_result_with_a_name_that_has_no_series_is_a_skip_naming_it(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["node_processes_state", "up"]})
    cx = _snap(tmp_path, EMPTY, {"node_processes_state": 0, "up": 12})
    r = evaluate.evaluate_check(_check(), cx, {})
    assert r["status"] == "skip" and r["reason"] == "no series of `node_processes_state` (not scraped, or the exporter renamed or removed it)"


def test_an_empty_result_with_every_name_present_is_a_pass_counted_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["up"]})
    cx = _snap(tmp_path, EMPTY, {"up": 12})
    r = evaluate.evaluate_check(_check(), cx, {})
    assert r["status"] == "done" and r["counts"] == {"empty": 1} and r["findings"] == []


def test_without_a_presence_record_an_empty_result_is_a_skip_saying_so(tmp_path, monkeypatch):
    """The record is missing exactly when the presence query failed or did not run, the loss #141 exists to expose; a pass would hide it."""
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["up"]})
    cx = _snap(tmp_path, EMPTY, None)
    r = evaluate.evaluate_check(_check(), cx, {})
    assert r["status"] == "skip" and r["reason"].startswith("the query returned no series and the series presence was not recorded")


def test_rule_empty_skip_wins_over_the_names(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["up"]})
    cx = _snap(tmp_path, EMPTY, {"up": 12})
    r = evaluate.evaluate_check(_check(rule={"expr": "value > 0", "empty": "skip", "empty_reason": "no scrape target answered"}), cx, {})
    assert r["status"] == "skip" and r["reason"] == "no scrape target answered"


def test_rule_empty_pass_keeps_a_counter_that_appears_on_its_first_event_a_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["kubeproxy_sync_proxy_rules_iptables_restore_failures_total"]})
    cx = _snap(tmp_path, EMPTY, {"kubeproxy_sync_proxy_rules_iptables_restore_failures_total": 0})
    r = evaluate.evaluate_check(_check(rule={"expr": "value > 0", "empty": "pass"}), cx, {})
    assert r["status"] == "done" and r["counts"] == {"empty": 1}


def test_a_result_with_series_is_judged_as_before(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["up"]})
    cx = _snap(tmp_path, {"ok": True, "result": [{"metric": {"job": "a"}, "value": [0, "1"]}]}, {"up": 0})
    r = evaluate.evaluate_check(_check(), cx, {})
    assert r["status"] == "done" and r["counts"] == {"fail": 1}


def test_a_joined_query_with_nothing_to_join_asks_the_same_question(tmp_path, monkeypatch):
    monkeypatch.setattr(metricnames, "names_by_query", lambda: {"q": ["kube_pod_info"], "r": ["up"]})
    (tmp_path / "metrics").mkdir()
    (tmp_path / "inventory.json").write_text(json.dumps(INV))
    for qid in ("q", "r"):
        (tmp_path / "metrics" / f"{qid}.json").write_text(json.dumps(EMPTY))
    (tmp_path / "metrics" / "series-present.json").write_text(json.dumps({"names": {"kube_pod_info": 0, "up": 3}}))
    cx = evaluate.Context(tmp_path, INV, {}, "small")
    r = evaluate.evaluate_check(_check(inputs=["q", "r"], join_on="pod", rule={"expr": "v.get('q', 0) > 0"}), cx, {})
    assert r["status"] == "skip" and "`kube_pod_info`" in r["reason"]


# ---------- the names and the presence record ----------


def test_names_of_takes_the_cited_names_and_leaves_the_label_entries():
    it = {"source": ["up: prometheus/prometheus scrape/scrape.go:1@v3.7.3", "label job on up: the scrape configuration", "node_cpu_seconds_total: prometheus/node_exporter collector/cpu_linux.go:1@v1.7.0", "up: again"]}
    assert metricnames.names_of(it) == ["up", "node_cpu_seconds_total"]


def test_every_query_that_cites_names_is_known_by_id():
    by = metricnames.names_by_query()
    assert len(by) >= 170 and sum(1 for v in by.values() if v) >= 170
    assert by["coredns_up"] == ["up"] or "up" in by["coredns_up"]


def test_record_series_present_writes_counts_and_zero_for_an_absent_name(tmp_path):
    p = prom.Prometheus.__new__(prom.Prometheus)
    p._present_lock = threading.Lock()
    asked = []

    def fake_query(expr, timeout=30, time=None):
        asked.append(expr)
        return {"ok": True, "resultType": "vector", "result": [{"metric": {"__name__": "up"}, "value": [0, "12"]}]}

    p.query = fake_query
    items = [{"id": "a", "source": ["up: x y:1@v1", "node_processes_state: x y:2@v1"]}, {"id": "b", "source": ["up: x y:1@v1"]}]
    doc = p.record_series_present(items, tmp_path)
    assert asked == ['count by (__name__) ({__name__=~"node_processes_state|up"})']
    assert doc == {"names": {"node_processes_state": 0, "up": 12}}
    assert json.loads((tmp_path / "series-present.json").read_text()) == doc
    # a second metrics file merges into the same record
    p.record_series_present([{"id": "c", "source": ["coredns_build_info: x y:1@v1"]}], tmp_path)
    assert json.loads((tmp_path / "series-present.json").read_text())["names"] == {"coredns_build_info": 0, "node_processes_state": 0, "up": 12}


def test_record_series_present_does_nothing_for_queries_without_names(tmp_path):
    p = prom.Prometheus.__new__(prom.Prometheus)
    p._present_lock = threading.Lock()
    p.query = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no query expected"))
    assert p.record_series_present([{"id": "cardinality_top_metrics", "query": 'topk(20, count by (__name__) ({__name__=~".+"}))'}], tmp_path) is None
    assert not (tmp_path / "series-present.json").exists()

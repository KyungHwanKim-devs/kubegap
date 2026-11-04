"""The `{apiserver_job}` placeholder of the apiserver queries (#140): filled from config, else detected once per run from the job values of
apiserver_request_total, and when no such series exists the queries are saved as failed with the reason, which lib/evaluate.py turns into a skip."""

from __future__ import annotations

import json
from pathlib import Path

from lib.prom import Prometheus


class _Fake(Prometheus):
    def __init__(self, jobs: list[str], detect_error: str | None = None):
        super().__init__("http://fake:9090", "test")
        self.jobs = jobs
        self.detect_error = detect_error
        self.sent: list[str] = []

    def query(self, expr: str, timeout: float = 30, time: str | None = None) -> dict:
        self.sent.append(expr)
        if expr.startswith("count by (job) (apiserver_request_total)"):
            if self.detect_error:
                return {"ok": False, "error": self.detect_error, "errorType": "timeout"}
            return {"ok": True, "resultType": "vector", "result": [{"metric": {"job": j}, "value": [0, "1"]} for j in self.jobs]}
        return {"ok": True, "resultType": "vector", "result": [{"metric": {}, "value": [0, "2"]}]}


def _metrics_file(tmp_path: Path) -> Path:
    f = tmp_path / "metrics.yaml"
    f.write_text(
        '- id: apiserver_watch_count\n  why: w\n  query: sum(apiserver_longrunning_requests{job="{apiserver_job}",verb="WATCH"})\n- id: node_count\n  why: n\n  query: count(kube_node_info)\n',
        encoding="utf-8",
    )
    return f


def _run(tmp_path: Path, jobs: list[str], configured: str | None = None, detect_error: str | None = None) -> tuple[_Fake, dict, dict]:
    snap = tmp_path / "snap"
    (snap / "metrics").mkdir(parents=True)
    p = _Fake(jobs, detect_error)
    p.run_file(_metrics_file(tmp_path), snap / "metrics", vars={"apiserver_job": configured})
    rec = json.loads((snap / "metrics" / "apiserver_watch_count.json").read_text(encoding="utf-8"))
    resolved = json.loads((snap / "prometheus" / "apiserver_job.json").read_text(encoding="utf-8"))
    return p, rec, resolved


def test_the_kube_prometheus_stack_name_wins_when_several_jobs_serve_the_apiserver(tmp_path):
    p, rec, resolved = _run(tmp_path, ["kubelet", "apiserver", "kubernetes-apiservers"])
    assert resolved == {"job": "apiserver", "source": "detected", "candidates": ["apiserver", "kubelet", "kubernetes-apiservers"], "error": None}
    assert rec["ok"] and rec["query"] == 'sum(apiserver_longrunning_requests{job="apiserver",verb="WATCH"})'
    assert p.sent.count("count by (job) (apiserver_request_total)") == 1, "detected once per run"


def test_a_hand_written_scrape_config_job_is_detected(tmp_path):
    _, rec, resolved = _run(tmp_path, ["kubernetes-apiservers"])
    assert resolved["job"] == "kubernetes-apiservers" and resolved["source"] == "detected"
    assert 'job="kubernetes-apiservers"' in rec["query"]


def test_the_config_value_is_used_without_detection(tmp_path):
    p, rec, resolved = _run(tmp_path, ["apiserver"], configured="my-apiserver")
    assert resolved["job"] == "my-apiserver" and resolved["source"] == "config"
    assert 'job="my-apiserver"' in rec["query"] and not any(e.startswith("count by (job)") for e in p.sent)


def test_without_any_apiserver_series_the_queries_are_failed_with_the_reason_and_the_others_still_run(tmp_path):
    p, rec, resolved = _run(tmp_path, [])
    assert resolved["job"] is None and resolved["source"] == "none"
    assert rec["ok"] is False and "no apiserver_request_total series" in rec["error"] and "apiserver_job" in rec["error"]
    other = json.loads((tmp_path / "snap" / "metrics" / "node_count.json").read_text(encoding="utf-8"))
    assert other["ok"] and other["series"] == 1
    assert not any("{apiserver_job}" in e or 'job="None"' in e for e in p.sent)


def test_a_failed_detection_query_is_reported_as_such_not_as_no_apiserver(tmp_path):
    _, rec, resolved = _run(tmp_path, ["apiserver"], detect_error="query timed out in query execution")
    assert resolved["job"] is None and resolved["source"] == "none" and resolved["error"] == "query timed out in query execution"
    assert rec["ok"] is False and rec["error"].startswith("apiserver job detection failed: query timed out") and rec["errorType"] == "apiserver_job_detect"


def test_the_only_job_is_taken_when_no_known_name_matches(tmp_path):
    """k3s without kube-prometheus-stack: the kubelet scrape serves the apiserver registry and is the only candidate."""
    _, rec, resolved = _run(tmp_path, ["kubelet"])
    assert resolved["job"] == "kubelet" and resolved["source"] == "detected" and 'job="kubelet"' in rec["query"]

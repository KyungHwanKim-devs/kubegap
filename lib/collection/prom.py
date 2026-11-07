"""Prometheus HTTP API queries. Connect via port-forward or a configured URL, run the query list and save each result to metrics/<id>.json."""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..foundations import http, yamlite
from ..foundations import metricnames as _metricnames
from ..foundations.runlog import RunLog
from ..foundations.snapshot import load_json, write_private
from . import monitoring
from .portfwd import PortForward

PROMQL_WORKERS = 3  # concurrent instant queries. Heavy 7-day range queries compete for Prometheus CPU: at 6 they took 20-29 s each on a real cluster (3-6 s when serial), so keep this low


class Prometheus:
    """The port-forward is alive only inside `with Prometheus.connect(...) as p:`."""

    def __init__(self, base_url: str, access: str, service: dict | None = None, pf: PortForward | None = None):
        self.base = base_url.rstrip("/")
        self._present_lock = threading.Lock()  # record_series_present: collectors run in parallel and every metrics.yaml merges into one file
        self.access = access
        self.service = service
        self._pf = pf
        self._apiserver_job: dict | None = None
        self._apiserver_lock = threading.Lock()

    @classmethod
    def connect(cls, context: str | None, configured_url: str | None, kubeconfig: str | None = None, services: dict | None = None, log: RunLog | None = None) -> Prometheus | None:
        if configured_url:
            return cls(configured_url, "config")
        svc = (services or {}).get("prometheus")
        if svc is None:
            found, _err = monitoring.find_services(context, kubeconfig, log=log)
            svc = found.get("prometheus")
        if svc is None:
            return None
        pf = PortForward(context, svc.namespace, svc.name, svc.port, kubeconfig=kubeconfig)
        if not pf.start():
            if log:
                log.note("prometheus port-forward failed", error=pf.error)
            return None
        return cls(pf.url, "port-forward", svc.to_dict(), pf)

    def close(self):
        if self._pf:
            self._pf.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def query(self, expr: str, timeout: float = 30, time: str | None = None) -> dict:
        params = {"query": expr, "timeout": f"{int(timeout)}s"}
        if time:
            params["time"] = time
        r = http.get(f"{self.base}/api/v1/query", params=params, timeout=timeout + 5)
        j = r.json() or {}
        if not r.ok or j.get("status") != "success":
            return {"ok": False, "error": j.get("error") or r.error or f"HTTP {r.status}", "errorType": j.get("errorType")}
        return {"ok": True, "resultType": j["data"]["resultType"], "result": j["data"]["result"]}

    # The apiserver job name: kube-prometheus-stack gives the apiserver job="apiserver" (its ServiceMonitor's jobLabel reads the kubernetes Service's component
    # label, #122), a hand-written scrape config usually "kubernetes-apiservers" (Prometheus's own example, documentation/examples/prometheus-kubernetes.yml:24@v2.49.1,
    # :24@v3.15.1), a ServiceMonitor without jobLabel the Service name "kubernetes" (the operator's default relabeling, prometheus-operator pkg/prometheus/promcfg.go:1368-1372@v0.71.0,
    # :2058-2062@v0.86.2). With none of the known names, the one job found (alphabetically first of several) is taken: on k3s without kube-prometheus-stack that is
    # "kubelet", whose scrape serves the apiserver registry once per server node (#122), so the numbers are right there. The 14 apiserver
    # queries of collectors/core/metrics.yaml filter on `{apiserver_job}`; the name comes from config.yaml (apiserver_job) or is detected once per run from the
    # job values of apiserver_request_total. With no such series under any job the queries are not run: they are saved as failed with the reason, so the
    # control-plane checks that read them are skipped (lib/judgement/evaluate skips a failed query) instead of passing on nothing.
    APISERVER_JOB_NAMES = ("apiserver", "kubernetes-apiservers", "kube-apiserver", "kubernetes")

    def resolve_apiserver_job(self, configured: str | None, out_dir: Path | None = None) -> dict:
        """{"job", "source", "candidates", "error"}: source is config, detected or none. Resolved once per connection (a lock keeps it to one query even when two
        query files carry the placeholder); written to prometheus/apiserver_job.json when out_dir is given."""
        with self._apiserver_lock:
            if getattr(self, "_apiserver_job", None) is None:
                if configured:
                    self._apiserver_job = {"job": str(configured), "source": "config", "candidates": [], "error": None}
                else:
                    res = self.query("count by (job) (apiserver_request_total)", timeout=30)
                    jobs = sorted({str(r["metric"].get("job")) for r in (res.get("result") or []) if r.get("metric", {}).get("job")}) if res.get("ok") else []
                    job = next((j for j in self.APISERVER_JOB_NAMES if j in jobs), jobs[0] if jobs else None)
                    self._apiserver_job = {"job": job, "source": "detected" if job else "none", "candidates": jobs, "error": None if res.get("ok") else res.get("error")}
            if out_dir is not None:
                write_private(out_dir / "apiserver_job.json", json.dumps(self._apiserver_job, ensure_ascii=False, indent=1))
            return self._apiserver_job

    def record_series_present(self, items: list[dict], out_dir: Path, *, log: RunLog | None = None, collector: str | None = None, timeout: float = 30, echo=None) -> dict | None:
        """One query per metrics file: how many series each metric name the file's queries cite has right now, merged into metrics/series-present.json
        (`{"names": {<name>: <series>}}`, 0 for a name Prometheus has no series of). lib/judgement/evaluate reads it when a query comes back empty (#141): a name
        with no series is "not scraped, renamed or removed", a skip; every name present is "the situation did not occur", a pass. The selector is a
        `__name__` regex matcher inside the braces (prometheus/prometheus promql/parser/parse.go:427-430,846-856@v3.7.3: a metric name may be given as
        a label matcher on `__name__` instead of outside the braces), aggregated with `count by (__name__)`."""
        names = sorted({n for it in items for n in _metricnames.names_of(it)})
        if not names:
            return None
        expr = 'count by (__name__) ({__name__=~"' + "|".join(names) + '"})'
        t0 = _dt.datetime.now()
        res = self.query(expr, timeout=timeout)
        secs = (_dt.datetime.now() - t0).total_seconds()
        if log:
            log.command(
                id="promql.series-present",
                cmd=["promql", f"count by (__name__) of {len(names)} names"],
                code=0 if res["ok"] else 1,
                seconds=secs,
                out_path="metrics/series-present.json" if res["ok"] else None,
                error=res.get("error"),
                collector=collector,
            )
        if not res["ok"]:
            if echo:
                echo(f"    {'series-present':<32} failed: {str(res.get('error'))[:120]}")
            return None
        counts = dict.fromkeys(names, 0)
        for r in res["result"]:
            n = (r.get("metric") or {}).get("__name__")
            if n in counts:
                with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
                    counts[n] = int(float(r["value"][1]))
        path = out_dir / "series-present.json"
        with self._present_lock:  # read, merge, write as one step: two collectors finishing together would otherwise drop each other's names
            doc = load_json(path) or {"names": {}}
            doc["names"].update(counts)
            doc["names"] = dict(sorted(doc["names"].items()))
            write_private(path, json.dumps(doc, ensure_ascii=False, indent=1))
        if echo:
            echo(f"    {'series-present':<32} {sum(1 for v in counts.values() if v)} of {len(counts)} names have series")
        return doc

    def run_file(self, path: Path, out_dir: Path, log: RunLog | None = None, collector: str | None = None, timeout: float = 30, echo=None, vars: dict | None = None) -> dict:
        """Read metrics.yaml and run/save each query. `vars` fills the `{apiserver_job}` placeholder (config value, or None to detect). Returns a summary (series count per query, failures)."""
        items = yamlite.load_file(path) or []
        summary = {"ok": 0, "failed": 0, "queries": {}}
        now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
        apiserver_job = None
        if any("{apiserver_job}" in str(it["query"]) for it in items):
            apiserver_job = self.resolve_apiserver_job((vars or {}).get("apiserver_job"), out_dir.parent / "prometheus")

        def run(it):
            expr = " ".join(str(it["query"]).split())
            if "{apiserver_job}" in expr:
                if not apiserver_job or not apiserver_job.get("job"):
                    if apiserver_job and apiserver_job.get("error"):  # the detection query itself failed (timeout, 5xx): not "no apiserver"
                        return it, expr, {"ok": False, "error": f"apiserver job detection failed: {apiserver_job['error']}", "errorType": "apiserver_job_detect"}, 0.0
                    return it, expr, {"ok": False, "error": "no apiserver_request_total series under any job label: the apiserver is not scraped, or set apiserver_job in config.yaml", "errorType": "apiserver_job"}, 0.0
                expr = expr.replace("{apiserver_job}", apiserver_job["job"])
            t0 = _dt.datetime.now()
            res = self.query(expr, timeout=timeout)
            return it, expr, res, (_dt.datetime.now() - t0).total_seconds()

        # Instant queries are independent; a few at a time shortens a 170-query list without turning into a load test of Prometheus
        with ThreadPoolExecutor(max_workers=min(PROMQL_WORKERS, max(1, len(items))), thread_name_prefix="promql") as pool:
            done = list(pool.map(run, items))
        self.record_series_present(items, out_dir, log=log, collector=collector, timeout=timeout, echo=echo)
        for it, expr, res, secs in done:
            qid = it["id"]
            rec = {"id": qid, "query": expr, "why": it.get("why"), "taken_at": now, **res}
            if res["ok"]:
                rec["series"] = len(res["result"])
                summary["ok"] += 1
            else:
                summary["failed"] += 1
            write_private(out_dir / f"{qid}.json", json.dumps(rec, ensure_ascii=False, indent=1))
            summary["queries"][qid] = {"ok": res["ok"], "series": rec.get("series"), "error": res.get("error")}
            if log:
                log.command(id=f"promql.{qid}", cmd=["promql", expr], code=0 if res["ok"] else 1, seconds=secs, out_path=f"metrics/{qid}.json" if res["ok"] else None, error=res.get("error"), collector=collector)
            if echo:
                echo(f"    {qid:<32} {('series ' + str(rec['series'])) if res['ok'] else 'failed: ' + str(res.get('error'))[:120]}")
        return summary

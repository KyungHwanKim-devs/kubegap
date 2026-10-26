"""Prometheus HTTP API queries. Connect via port-forward or a configured URL, run the query list and save each result to metrics/<id>.json."""

from __future__ import annotations

import datetime as _dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import http, monitoring, yamlite
from .portfwd import PortForward
from .runlog import RunLog

PROMQL_WORKERS = 3  # concurrent instant queries. Heavy 7-day range queries compete for Prometheus CPU: at 6 they took 20-29 s each on a real cluster (3-6 s when serial), so keep this low


class Prometheus:
    """The port-forward is alive only inside `with Prometheus.connect(...) as p:`."""

    def __init__(self, base_url: str, access: str, service: dict | None = None, pf: PortForward | None = None):
        self.base = base_url.rstrip("/")
        self.access = access
        self.service = service
        self._pf = pf

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

    def run_file(self, path: Path, out_dir: Path, log: RunLog | None = None, collector: str | None = None, timeout: float = 30, echo=None) -> dict:
        """Read metrics.yaml and run/save each query. Returns a summary (series count per query, failures)."""
        items = yamlite.load_file(path) or []
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {"ok": 0, "failed": 0, "queries": {}}
        now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

        def run(it):
            expr = " ".join(str(it["query"]).split())
            t0 = _dt.datetime.now()
            res = self.query(expr, timeout=timeout)
            return it, expr, res, (_dt.datetime.now() - t0).total_seconds()

        # Instant queries are independent; a few at a time shortens a 170-query list without turning into a load test of Prometheus
        with ThreadPoolExecutor(max_workers=min(PROMQL_WORKERS, max(1, len(items))), thread_name_prefix="promql") as pool:
            done = list(pool.map(run, items))
        for it, expr, res, secs in done:
            qid = it["id"]
            rec = {"id": qid, "query": expr, "why": it.get("why"), "taken_at": now, **res}
            if res["ok"]:
                rec["series"] = len(res["result"])
                summary["ok"] += 1
            else:
                summary["failed"] += 1
            (out_dir / f"{qid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            summary["queries"][qid] = {"ok": res["ok"], "series": rec.get("series"), "error": res.get("error")}
            if log:
                log.command(id=f"promql.{qid}", cmd=["promql", expr], code=0 if res["ok"] else 1, seconds=secs, out_path=f"metrics/{qid}.json" if res["ok"] else None, error=res.get("error"), collector=collector)
            if echo:
                echo(f"    {qid:<32} {('series ' + str(rec['series'])) if res['ok'] else 'failed: ' + str(res.get('error'))[:120]}")
        return summary

"""The store steps: PromQL query lists through lib/collection/prom and HTTP GETs against Prometheus, Alertmanager, Loki and Grafana.

Part of the collector (lib/collection/collect): the runner in the package's __init__ dispatches each collect.yaml step to a handler here through
STEP_HANDLERS; every handler has the signature `(ctx: StepContext, st: dict) -> dict`, the per-step entry of collect-result.json.
"""

from __future__ import annotations

import ipaddress
import json
import re
import urllib.parse
from pathlib import Path

from ...foundations.config import Config
from ...foundations.runlog import RunLog
from ...foundations.snapshot import write_private
from .context import StepContext, Stores


def plain_http_token_host(base: str) -> str | None:
    """The host a token would travel to in clear text: the URL is plain http and the host is not loopback. None otherwise.

    A port-forward and the `http://localhost:3000` of config.example.yaml stay on this machine, so they are not reported.
    """
    u = urllib.parse.urlsplit(base)
    host = u.hostname
    if u.scheme != "http" or not host:
        return None
    if host == "localhost":
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    mapped = getattr(ip, "ipv4_mapped", None)  # ::ffff:127.0.0.1; is_loopback honours it only from Python 3.12
    if ip.is_loopback or (mapped is not None and mapped.is_loopback):
        return None
    return host


def run_http_step(st: dict, sid: str, name: str, cfg: Config, snap: Path, log: RunLog, stores: Stores, timeout: float, echo) -> dict:
    from ...foundations import http as _http

    kind = st["store"]
    base = stores.url(kind)
    if not base:
        log.skip(id=f"{name}.{sid}", reason=f"no {kind} connection", collector=name)
        if echo:
            echo(f"    skipped: no {kind} connection")
        return {"ok": False, "skipped": f"no {kind} connection"}
    headers = {"Accept": "application/json"}
    if st.get("auth"):
        token = cfg.get(st["auth"])
        if not token:
            log.skip(id=f"{name}.{sid}", reason=f"config.yaml {st['auth']} missing (API requires auth)", collector=name)
            if echo:
                echo(f"    skipped: config.yaml has no {st['auth']}, so the authenticated endpoint {st['path']} is not read")
            return {"ok": False, "skipped": f"{st['auth']} missing"}
        headers["Authorization"] = f"Bearer {token}"
        plain_host = plain_http_token_host(base)
        with stores._lock:
            first = bool(plain_host) and plain_host not in stores.warned_plain_http
            if first:
                stores.warned_plain_http.add(plain_host)
        if first:
            log.note("token sent over plain http", host=plain_host, store=kind)
            if echo:
                echo(f"    warning: {kind}_url is plain http, so {st['auth']} travels to {plain_host} in clear text; use an https address or a port-forward")
    import time as _t

    t0 = _t.monotonic()
    if st.get("accept") == "text":
        headers["Accept"] = "text/plain"
    # Time placeholders in params values: {now_s} {now_ns} {ago_1h_s} {ago_1h_ns} {ago_24h_s} {ago_24h_ns}. Loki uses nanoseconds, Prometheus seconds.
    now = int(_t.time())
    ph = {"now_s": now, "now_ns": now * 10**9, "ago_1h_s": now - 3600, "ago_1h_ns": (now - 3600) * 10**9, "ago_24h_s": now - 86400, "ago_24h_ns": (now - 86400) * 10**9}

    def _sub(v):  # str.format conflicts with LogQL braces, so only known placeholders are substituted
        for k, val in ph.items():
            v = v.replace("{" + k + "}", str(val))
        return v

    params = {k: _sub(v) if isinstance(v, str) else v for k, v in (st.get("params") or {}).items()} or None
    ff = st.get("for_each_file")
    if ff:
        # One GET per item of an earlier step's result (JSON list) — e.g. /api/dashboards/uid/<uid> for every uid from Grafana /api/search. Placeholders {item.<field>} {item_safe}
        try:
            doc = json.loads((snap / ff["path"]).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = None
        items = doc if isinstance(doc, list) else ((doc or {}).get(ff.get("items") or "items") if isinstance(doc, dict) else None) or []
        runs: dict = {}
        for it in items[: int(ff.get("limit", 300))]:
            if not isinstance(it, dict) or not it.get(ff.get("key") or "uid"):
                continue
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(it[ff.get("key") or "uid"]))
            path_i = st["path"]
            for k, v in it.items():
                if isinstance(v, (str, int, float)):
                    path_i = path_i.replace("{item." + k + "}", str(v))
            t_i = _t.monotonic()
            r = _http.get(base.rstrip("/") + path_i, params=params, timeout=timeout, headers=headers)
            out_i = snap / str(st["out"]).replace("{item_safe}", safe)
            if r.ok:
                write_private(out_i, r.body)
            err_i = None if r.ok else (r.error or f"HTTP {r.status}")
            runs[safe] = {"ok": r.ok, "status": getattr(r, "status", None), "error": err_i}
            log.command(id=f"{name}.{sid}.{safe}", cmd=["http", kind, path_i], code=0 if r.ok else (r.status or 1), seconds=_t.monotonic() - t_i, out_path=str(out_i.relative_to(snap)) if r.ok else None, error=err_i, collector=name)
        if echo:
            echo(f"    {sum(1 for x in runs.values() if x['ok'])}/{len(runs)} items saved ({str(st['out']).rsplit('/', 1)[0]})")
        return {"ok": any(x["ok"] for x in runs.values()) if runs else False, "runs": len(runs), "seconds": round(_t.monotonic() - t0, 1)}
    r = _http.get(base.rstrip("/") + st["path"], params=params, timeout=timeout, headers=headers)
    out = snap / st["out"]
    if r.ok:
        write_private(out, r.body)
    log.command(
        id=f"{name}.{sid}", cmd=["http", kind, st["path"]], code=0 if r.ok else (r.status or 1), seconds=_t.monotonic() - t0, out_path=st["out"] if r.ok else None, error=None if r.ok else (r.error or f"HTTP {r.status}"), collector=name
    )
    if echo:
        echo(f"    {'saved ' + st['out'] + f' ({len(r.body) // 1024} KB)' if r.ok else 'failed: ' + str(r.error or r.status)}")
    return {"ok": r.ok, "status": r.status, "bytes": len(r.body) if r.ok else 0, "error": None if r.ok else (r.error or f"HTTP {r.status}")}


def step_promql(ctx: StepContext, st: dict) -> dict:
    if ctx.prom is None:
        if ctx.echo:
            ctx.echo("    skipped: no Prometheus connection")
        return ctx.skip(st["id"], "no Prometheus connection")
    return ctx.prom.run_file(ctx.folder / st["file"], ctx.snap / "metrics", log=ctx.log, collector=ctx.name, timeout=float(st.get("timeout", 60)), echo=ctx.echo, vars={"apiserver_job": ctx.cfg.get("apiserver_job")})


def step_http(ctx: StepContext, st: dict) -> dict:
    if ctx.stores is None:
        return {"ok": False, "error": "no stores"}
    return run_http_step(st, st["id"], ctx.name, ctx.cfg, ctx.snap, ctx.log, ctx.stores, float(st.get("timeout", 60)), ctx.echo)

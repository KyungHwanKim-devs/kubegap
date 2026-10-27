"""Collection (collect).

For every collector folder listed in `collectors_enabled` of `inventory.json`, read its `collect.yaml` and run the commands.
Each command has a timeout and failure handling; on failure it is logged to run.log and we move on. The LLM is not involved in this stage.
Secrets are never fetched by any path. If Secrets are mixed into fetched objects, data and stringData are stripped (defensive).
"""

from __future__ import annotations

import contextlib
import json
import re
import threading
import time as _time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import aws as _aws
from . import kube, nodecommands, paths, yamlite
from .config import Config
from .portfwd import PortForward
from .prom import Prometheus
from .runlog import RunLog

SECRET_KINDS = {"Secret", "SecretList"}
NON_WORKLOAD_COMPONENTS = {"ecr", "eks-managed-addons", "k3s", "rke2"}  # registry and platform names are not pods and not log collection targets (app pod logs once ended up under the "ecr" component)


COLLECTOR_WORKERS = 3  # collectors run concurrently; capped so that kubegap's own ~100 LISTs and ~170 PromQL queries do not show up as an apiserver/Prometheus latency spike in the data it is collecting
ITEM_WORKERS = 4  # parallel items inside one step: AWS for_each calls, per-node commands (PromQL has its own cap, prom.PROMQL_WORKERS)


@dataclass
class CollectState:
    """Mutable state of one collection run, shared by all collectors of that run.

    Kept on an object that `collect()` creates (not a module global) so that two collections in one process — tests, or a
    future multi-context run — do not leak state into each other."""

    proxy_blocked: set = field(default_factory=set)  # contexts where the apiserver pod proxy timed out in this run (pod-metrics goes straight to node curl)


class _Blocked:
    """Fake failure result used to go straight to node curl without trying the proxy."""

    ok = False
    stdout = ""
    stderr = "apiserver pod proxy blocked earlier in this run"
    error = "proxy blocked (skipped)"


def _scrub(obj):
    """Strip Secret values. Also handles Secret items inside lists."""
    if isinstance(obj, dict):
        if isinstance(obj.get("kind"), str) and obj.get("kind") in SECRET_KINDS:
            obj.pop("data", None)
            obj.pop("stringData", None)
        for v in obj.values():
            _scrub(v)
    elif isinstance(obj, list):
        for v in obj:
            _scrub(v)
    return obj


def _glob_match(name: str, patterns: list[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def list_api_resources(context: str | None, kubeconfig: str | None, log: RunLog) -> list[dict]:
    """Parse `kubectl api-resources --verbs=list -o wide` into a list of (name, namespaced, kind, full name)."""
    r = kube.kubectl(["api-resources", "--verbs=list", "-o", "wide"], context=context, timeout=60, id="collect.api-resources", log=log, kubeconfig=kubeconfig)
    if not r.ok:
        return []
    lines = r.stdout.splitlines()
    if not lines:
        return []
    header = lines[0]
    cols = [m.start() for m in re.finditer(r"\S+", header)]
    names = re.findall(r"\S+", header)
    out = []
    for line in lines[1:]:
        if not line.strip():
            continue
        row = {}
        for i, (c, n) in enumerate(zip(cols, names, strict=False)):
            end = cols[i + 1] if i + 1 < len(cols) else None
            row[n] = line[c:end].strip()
        group = row.get("APIVERSION", "").split("/")[0] if "/" in row.get("APIVERSION", "") else ""
        full = row["NAME"] + (f".{group}" if group else "")
        out.append({"name": row["NAME"], "full": full, "namespaced": row.get("NAMESPACED") == "true", "kind": row.get("KIND"), "apiversion": row.get("APIVERSION")})
    return out


def dump_all(context: str | None, kubeconfig: str | None, snap: Path, exclude: list[str], timeout: float, log: RunLog, collector: str, echo=None) -> dict:
    resources = list_api_resources(context, kubeconfig, log)
    done = {p.stem for p in (snap / "objects").glob("*.json")}
    summary = {"kinds": 0, "items": 0, "skipped": [], "failed": {}, "excluded": []}
    hard_exclude = ["secrets", "secrets.*"]
    for res in resources:
        full, name = res["full"], res["name"]
        if _glob_match(name, hard_exclude) or _glob_match(full, hard_exclude) or (res.get("kind") or "") in SECRET_KINDS:
            summary["excluded"].append(full)
            continue
        if _glob_match(name, exclude) or _glob_match(full, exclude):
            summary["excluded"].append(full)
            continue
        # Kinds discovery already fetched (nodes, pods, deployments ...) are not fetched again. File name: core group = name only, others = name.group
        core_group = not res.get("apiversion", "").count("/")
        file_stem = name if core_group else full
        if name in done or full in done:
            summary["skipped"].append(full)
            continue
        args = ["get", full] + (["-A"] if res["namespaced"] else [])
        data, r = kube.kubectl_json(args, context=context, timeout=timeout, id=f"collect.get-{full}", log=log, kubeconfig=kubeconfig, collector=collector)
        if data is None:
            summary["failed"][full] = r.error or r.stderr.strip()[-200:]
            continue
        _scrub(data)
        (snap / "objects" / f"{file_stem}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        n = len(data.get("items", []) or [])
        summary["kinds"] += 1
        summary["items"] += n
    if echo:
        echo(f"    {summary['kinds']} kinds, {summary['items']} objects saved. skipped (fetched by discovery) {len(summary['skipped'])}, excluded {len(summary['excluded'])}, failed {len(summary['failed'])}")
        for k, v in summary["failed"].items():
            echo(f"      failed {k}: {v[:100]}")
    return summary


def _aws_vars(eks: dict) -> dict:
    import datetime as _dt

    today = _dt.datetime.now(_dt.UTC).date()
    return {
        "cluster": eks.get("name"),
        "region": eks.get("region"),
        "account": eks.get("account"),
        "k8s_version": eks.get("version"),
        "date_30d_ago": (today - _dt.timedelta(days=30)).isoformat(),
        "date_7d_ago": (today - _dt.timedelta(days=7)).isoformat(),
        "date_today": today.isoformat(),
        "date_tomorrow": (today + _dt.timedelta(days=1)).isoformat(),
    }


def _aws_lists(eks: dict, inv: dict | None = None) -> dict:
    types = sorted({n.get("instance_type") for n in ((inv or {}).get("nodes") or {}).get("nodes", []) if n.get("instance_type")})
    return {
        "subnet_ids": list(eks.get("subnet_ids") or []),
        "security_groups": list(eks.get("security_groups") or []),
        "nodegroups": list(eks.get("nodegroups") or []),
        "addons": list((eks.get("addons") or {}).keys()),
        "instance_types": types,
        "ecr_repositories": list(eks.get("ecr_repositories") or []),
        "service_codes": ["ec2", "vpc", "elasticloadbalancing", "ebs"],  # service-quotas step
        "instance_ids": sorted(
            {str(n.get("provider_id") or "").rsplit("/", 1)[-1] for n in ((inv or {}).get("nodes") or {}).get("nodes", []) if str(n.get("provider_id") or "").startswith("aws:///")}
        ),  # node EC2 instance ids (for root volume lookup)
    }


def _expand_args(template: list, vars_: dict, lists: dict) -> list[str]:
    """Plural placeholders like `{subnet_ids}` expand a list into several arguments; the rest are filled with format."""
    out: list[str] = []
    for a in template:
        a = str(a)
        key = a[1:-1] if a.startswith("{") and a.endswith("}") else None
        if key in lists:
            out.extend(str(x) for x in lists[key])
        else:
            # str.format conflicts with JMESPath braces (--query "Volumes[].{id:VolumeId}"), so only known placeholders are substituted (otherwise every aws step fails with "placeholder has no value")
            for k, v in vars_.items():
                a = a.replace("{" + k + "}", str(v))
            for k, v in lists.items():  # plural placeholders embedded in a string are joined with commas — "Name=attachment.instance-id,Values={instance_ids}"
                if "{" + k + "}" in a:
                    a = a.replace("{" + k + "}", ",".join(str(x) for x in v))
            out.append(a)
    return out


def _run_aws_step(st: dict, sid: str, name: str, eks: dict, cfg: Config, snap: Path, log: RunLog, timeout: float, echo, inv: dict | None = None) -> dict:
    vars_ = _aws_vars(eks)
    lists = _aws_lists(eks, inv)
    prof = cfg.get("aws_profile") or eks.get("profile")
    region = st.get("region") or cfg.get("aws_region") or eks.get("region")  # the pricing API exists only in us-east-1, so a step may pin the region
    items: list = [None]
    if st.get("for_each"):
        src = str(st["for_each"]).split(".")[-1]
        items = lists.get(src, [])
        if not items:
            if echo:
                echo(f"    skipped: {st['for_each']} is empty")
            return {"ok": True, "runs": 0, "note": f"{st['for_each']} is empty"}

    def one(item):
        v = {**vars_, "item": item, "item_safe": str(item).replace("/", "__") if item is not None else ""}  # for file names (ECR repository names contain /: bitnami/kafka)
        if any(k in str(st["args"]) for k in ("{subnet_ids}", "{security_groups}")) and not any(lists[k] for k in ("subnet_ids", "security_groups") if "{" + k + "}" in str(st["args"])):
            return item or sid, {"ok": False, "error": "list is empty"}, None
        try:
            args = _expand_args(st["args"], v, lists)
            out = snap / str(st["out"]).format(**v)
        except KeyError as e:
            return item or sid, {"ok": False, "error": f"placeholder {e} has no value"}, None
        r = _aws.aws(args, profile=prof, region=region, timeout=timeout, id=f"{name}.{sid}" + (f".{item}" if item else ""), log=log, out_path=out, collector=name)
        if not r.ok and st.get("tolerate_errors") and "NotFound" in ((r.stderr or "") + (r.error or "")):
            return item or sid, {"ok": True, "out": None, "error": None, "note": "none (NotFound — normal response)"}, None  # ecr get-lifecycle-policy's LifecyclePolicyNotFoundException means "no policy", not a failure
        rec = {"ok": r.ok, "out": str(out.relative_to(snap)) if r.ok else None, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
        line = None if (st.get("tolerate_errors") and not r.ok) else f"    {'saved ' + str(out.relative_to(snap)) if r.ok else 'failed' + (f' ({item})' if item else '') + ': ' + str(rec['error'])[:120]}"
        return item or sid, rec, line

    runs: dict = {}
    for key, rec, line in _parallel(one, items):  # for_each items (nodegroups, ECR repositories, instance types) are independent calls
        runs[key] = rec
        if echo and line:
            echo(line)
    # tolerate_errors: for calls where a per-item failure is a normal response (ecr get-lifecycle-policy's LifecyclePolicyNotFoundException = no policy), the step is ok if any item succeeded
    ok = any(x["ok"] for x in runs.values()) if st.get("tolerate_errors") else all(x["ok"] for x in runs.values())
    return {"ok": ok, "runs": len(runs), "failed": sum(1 for x in runs.values() if not x["ok"]), "detail": runs}


class Stores:
    """Open each store (prometheus, alertmanager, loki, grafana) endpoint once and reuse it during collection. A configured URL is used directly without port-forwarding."""

    def __init__(self, context: str | None, cfg: Config, inv: dict, kubeconfig: str | None, log: RunLog):
        self.context, self.cfg, self.kubeconfig, self.log = context, cfg, kubeconfig, log
        self._pf: dict[str, PortForward] = {}
        self._lock = threading.Lock()  # several collectors may ask for the same store at once
        self._url: dict[str, str] = {}
        self._svc = {}
        for kind, info in (inv.get("stores") or {}).items():
            if info.get("service"):
                self._svc[kind] = info["service"]

    def url(self, kind: str) -> str | None:
        with self._lock:
            return self._url_locked(kind)

    def _url_locked(self, kind: str) -> str | None:
        if kind in self._url:
            return self._url[kind]
        u = self.cfg.url(kind)
        if u:
            self._url[kind] = u
            return u
        svc = self._svc.get(kind)
        if not svc:
            return None
        pf = PortForward(self.context, svc["namespace"], svc["name"], svc["port"], kubeconfig=self.kubeconfig)
        if not pf.start():
            self.log.note(f"{kind} port-forward failed", error=pf.error)
            return None
        self._pf[kind] = pf
        self._url[kind] = pf.url
        return pf.url

    def close(self):
        for pf in self._pf.values():
            pf.stop()


def _run_http_step(st: dict, sid: str, name: str, cfg: Config, snap: Path, log: RunLog, stores: Stores, timeout: float, echo) -> dict:
    from . import http as _http

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
            r = _http.get(base.rstrip("/") + path_i, params=params, timeout=timeout, headers=headers)
            out_i = snap / str(st["out"]).replace("{item_safe}", safe)
            if r.ok:
                out_i.parent.mkdir(parents=True, exist_ok=True)
                out_i.write_text(r.body, encoding="utf-8")
            runs[safe] = {"ok": r.ok, "status": getattr(r, "status", None)}
        if echo:
            echo(f"    {sum(1 for x in runs.values() if x['ok'])}/{len(runs)} items saved ({str(st['out']).rsplit('/', 1)[0]})")
        return {"ok": any(x["ok"] for x in runs.values()) if runs else False, "runs": len(runs), "seconds": round(_t.monotonic() - t0, 1)}
    r = _http.get(base.rstrip("/") + st["path"], params=params, timeout=timeout, headers=headers)
    out = snap / st["out"]
    if r.ok:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(r.body, encoding="utf-8")
    log.command(
        id=f"{name}.{sid}", cmd=["http", kind, st["path"]], code=0 if r.ok else (r.status or 1), seconds=_t.monotonic() - t0, out_path=st["out"] if r.ok else None, error=None if r.ok else (r.error or f"HTTP {r.status}"), collector=name
    )
    if echo:
        echo(f"    {'saved ' + st['out'] + f' ({len(r.body) // 1024} KB)' if r.ok else 'failed: ' + str(r.error or r.status)}")
    return {"ok": r.ok, "status": r.status, "bytes": len(r.body) if r.ok else 0, "error": None if r.ok else (r.error or f"HTTP {r.status}")}


def _run_tool_step(st: dict, sid: str, name: str, context: str | None, kubeconfig: str | None, snap: Path, log: RunLog, stores: Stores | None, timeout: float, echo, inv: dict | None = None) -> dict:
    """Run an external CLI (KRR, Polaris, Pluto, etc.) locally. Placeholders in cmd: {context} {kubeconfig} {out} (absolute path) {prometheus_url} etc. {<store>_url}.
    tool: executable name (PATH or .tools/bin). If missing, the step is skipped and becomes input for the report's "tool missing" section. If a store URL is needed but there is no connection, the step is skipped."""
    from . import shell as _shell

    tool = st.get("tool") or st["cmd"][0]
    path = _shell.which(tool)
    if not path:
        log.skip(id=f"{name}.{sid}", reason=f"tool {tool} missing", collector=name)
        if echo:
            echo(f"    skipped: tool {tool} missing (setup --install-only {tool})")
        return {"ok": False, "skipped": f"tool {tool} missing", "tool_missing": tool}
    out = snap / st["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    ph = {"context": context or "", "kubeconfig": kubeconfig or "", "out": str(out)}
    # Next minor of the cluster server version (target for Pluto/kubent). v1.32.13-eks -> v1.33.0 / 1.33
    import re as _re

    m = _re.match(r"v?(\d+)\.(\d+)", str(((inv or {}).get("cluster") or {}).get("server_version") or ""))
    if m:
        ph["k8s_next_minor"] = f"v{m.group(1)}.{int(m.group(2)) + 1}.0"
        ph["k8s_next_minor_short"] = f"{m.group(1)}.{int(m.group(2)) + 1}"
    else:
        ph["k8s_next_minor"], ph["k8s_next_minor_short"] = "v1.99.0", "1.99"
    for store in ("prometheus", "alertmanager", "loki", "grafana"):
        if any(f"{{{store}_url}}" in str(a) for a in st["cmd"]):
            url = stores.url(store) if stores else None
            if not url:
                log.skip(id=f"{name}.{sid}", reason=f"no {store} connection", collector=name)
                if echo:
                    echo(f"    skipped: no {store} connection")
                return {"ok": False, "skipped": f"no {store} connection"}
            ph[f"{store}_url"] = url

    def build(extra: dict) -> list[str]:
        cmd_ = []
        for a in st["cmd"]:
            a = str(a)
            for k, v in {**ph, **extra}.items():
                a = a.replace("{" + k + "}", str(v))
            if a == "" and "{kubeconfig}" in str(st["cmd"]):
                continue
            cmd_.append(a)
        if not kubeconfig:  # if the value of the --kubeconfig {kubeconfig} pair is empty, drop the option too
            cmd_ = [a for i, a in enumerate(cmd_) if not (a in ("--kubeconfig", "-k") and (i + 1 >= len(cmd_) or cmd_[i + 1] == ""))]
        cmd_[0] = path
        return cmd_

    ff = st.get("for_each_file")
    if ff:
        # Run once per item of an earlier step's result in the same snapshot (JSON list) — e.g. helm get values per release. Placeholders {item.<field>} {item_safe}
        try:
            doc = json.loads((snap / ff["path"]).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = None
        items = doc if isinstance(doc, list) else ((doc or {}).get(ff.get("items") or "items") if isinstance(doc, dict) else None) or []
        runs: dict = {}
        for it in items[: int(ff.get("limit", 200))]:
            if not isinstance(it, dict):
                continue
            safe = "__".join(str(it.get(k, "")) for k in (ff.get("key") or ["name"])).replace("/", "_")
            extra = {f"item.{k}": v for k, v in it.items() if isinstance(v, (str, int, float))}
            extra["item_safe"] = safe
            out_i = snap / str(st["out"]).replace("{item_safe}", safe)
            out_i.parent.mkdir(parents=True, exist_ok=True)
            r = _shell.run(build(extra), timeout=timeout, id=f"{name}.{sid}.{safe}", log=log, collector=name, out_path=out_i)
            runs[safe] = {"ok": r.ok and out_i.is_file(), "error": None if r.ok else (r.error or r.stderr.strip()[-160:])}
        if echo:
            echo(f"    {sum(1 for x in runs.values() if x['ok'])}/{len(runs)} items saved ({str(st['out']).rsplit('/', 1)[0]})")
        return {"ok": any(x["ok"] for x in runs.values()) if runs else False, "runs": len(runs), "failed": sum(1 for x in runs.values() if not x["ok"]), "detail": runs}
    cmd = build({})
    r = _shell.run(cmd, timeout=timeout, id=f"{name}.{sid}", log=log, collector=name, out_path=None if st.get("writes_out") else out)
    ok = r.ok and out.is_file() and out.stat().st_size > 0
    if echo:
        echo(f"    {'saved ' + st['out'] + f' ({out.stat().st_size // 1024} KB)' if ok else 'failed: ' + str(r.error or r.stderr.strip()[-200:] or 'no output')}")
    return {"ok": ok, "seconds": round(r.seconds, 1) if hasattr(r, "seconds") else None, "error": None if ok else (r.error or r.stderr.strip()[-300:] or "no output")}


class NodeRunner:
    """For node command steps. Builds the NodeAccess and the capabilities table once and reuses them."""

    def __init__(self, inv: dict, cfg: Config, log: RunLog):
        from .node import NodeAccess

        self.na = NodeAccess(inv, cfg, log)
        self._caps: dict | None = None
        self.nodes = {n["name"]: n for n in (inv.get("nodes") or {}).get("nodes", [])}

    def caps(self) -> dict:
        if self._caps is None:
            self._caps = self.na.capabilities() if self.na.method == "ssh" else {}
        return self._caps

    def select(self, which: str) -> list[str]:
        names = list(self.nodes)
        if which == "server":
            return [n for n in names if any(r in ("control-plane", "master") for r in self.nodes[n].get("roles", []))] or names[:1]
        if which == "agent":
            return [n for n in names if not any(r in ("control-plane", "master") for r in self.nodes[n].get("roles", []))]
        return names


def _run_node_step(st: dict, sid: str, name: str, inv: dict, cfg: Config, snap: Path, log: RunLog, runner: NodeRunner | None, timeout: float, echo) -> dict:
    if runner is None or runner.na.method not in ("ssh", "ssm"):
        log.skip(id=f"{name}.{sid}", reason=f"no node command backend ({runner.na.method if runner else '-'})", collector=name)
        if echo:
            echo("    skipped: no node command backend")
        return {"ok": False, "skipped": "no node command backend"}
    req = st.get("requires")
    caps = runner.caps()
    if st.get("script"):
        # Script files (collectors/<collector>/<file>) are sent as is because their line structure matters. SSM takes line-by-line commands, SSH one argument.
        cmd = (paths.COLLECTORS_DIR / name / str(st["script"])).read_text(encoding="utf-8")
    else:
        cmd = " ".join(str(st["cmd"]).split())

    def one(node: str):
        cap = ((caps.get(node) or {}).get("caps") or {}) if caps else {}
        if req and caps and cap.get(req) not in ("yes", "sudo"):
            rec = {"ok": False, "skipped": f"node permission missing ({req}={cap.get(req, '?')}). See deploy/node-access/README.md"}
            log.skip(id=f"{name}.{sid}.{node}", reason=rec["skipped"], collector=name)
            return node, rec, f"    {node}: skipped — {rec['skipped']}"
        r = runner.na.run_on_node(node, cmd, timeout=timeout, id=f"{name}.{sid}", collector=name, step=f"{name}/{sid}")
        if "---Output truncated---" in r.stdout:
            r.stdout += "\n### truncated\n"
        out = snap / str(st["out"]).format(node=node)
        if r.ok or r.stdout:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(r.stdout, encoding="utf-8")
        lines = r.stdout.count("\n")
        rec = {"ok": r.ok, "lines": lines, "out": str(out.relative_to(snap)) if (r.ok or r.stdout) else None, "error": r.error}
        return node, rec, f"    {node}: {'saved ' + rec['out'] + f' ({lines} lines)' if rec['out'] else 'failed: ' + str(r.error)[:120]}"

    runs: dict = {}
    for node, rec, line in _parallel(one, runner.select(st.get("nodes", "all"))):  # nodes are independent; SSM/SSH sessions run side by side
        runs[node] = rec
        if echo:
            echo(line)
    return {"ok": all(x.get("ok") for x in runs.values()) if runs else False, "nodes": runs}


# Log workloads of components detected only by CRD (components.py rules without a workload pattern). "ns/name" globs.
LOG_HINTS: dict[str, list[str]] = {
    "keda": ["*/keda-operator*", "*/keda-admission*"],
    "cert-manager": ["*/cert-manager*"],
    "external-secrets": ["*/external-secrets*"],
    "prometheus-operator": ["*/*prometheus-operator*"],
    "argocd": ["*/argocd-*"],
    "metallb": ["*/metallb-*", "metallb-system/*"],
    "karpenter": ["*/karpenter*"],
    "reloader": ["*/reloader*"],
    "actions-runner-controller": ["*/*gha-rs-controller*", "*/actions-runner-controller*"],
    "ebs-csi": ["kube-system/ebs-csi-*"],
    "velero": ["*/velero*"],
    "longhorn": ["longhorn-system/longhorn-manager*"],
    "vpa": ["*/vpa-*"],
}


def _run_component_logs_step(st: dict, sid: str, name: str, inv: dict, context: str | None, kubeconfig: str | None, snap: Path, log: RunLog, timeout: float, echo) -> dict:
    """Fetch workload pod logs of detected components (components_present) with kubectl logs into logs/pods/<component>/<ns>_<workload>.log.
    User application logs are not fetched (that is Loki's job). Capped tail lines per pod, 24 hours."""
    from .components import COMPONENTS
    from .discover import _match_name

    kinds = ("daemonsets", "deployments", "statefulsets")
    objs = {}
    for k in kinds:
        try:
            objs[k] = (json.loads((snap / "objects" / f"{k}.json").read_text(encoding="utf-8")) or {}).get("items", [])
        except (OSError, json.JSONDecodeError):
            objs[k] = []
    present = [c for c in (inv.get("components_present") or []) if c not in set(st.get("exclude") or []) and c not in NON_WORKLOAD_COMPONENTS]
    rules = {c["name"]: c for c in COMPONENTS}
    since, tail, tail_ds = str(st.get("since", "24h")), int(st.get("tail", 1500)), int(st.get("tail_daemonset", 600))
    targets: list[tuple[str, str, str, str, dict]] = []
    seen: set[tuple[str, str]] = set()
    for comp in present:
        pats: list[tuple[str | None, str]] = []
        for rule in (rules.get(comp) or {}).get("any", []):
            for k, v in rule.items():
                if k in ("daemonset", "deployment", "statefulset"):
                    pats.append((k + "s", v))
                elif k == "image":
                    pats.append((None, v))
        pats += [(None if False else k, h) for h in LOG_HINTS.get(comp, []) for k in kinds]
        for kind, pat in pats:
            for k in [kind] if kind else kinds:
                for o in objs[k]:
                    m = o["metadata"]
                    if kind is None and not pat.startswith("*/") and "/" not in pat:
                        imgs = [c.get("image", "") for c in ((o.get("spec", {}).get("template", {}).get("spec", {}) or {}).get("containers") or [])]
                        hit = any(pat in i for i in imgs)
                    else:
                        hit = _match_name(pat, m["namespace"], m["name"])
                    if hit and (m["namespace"], m["name"]) not in seen:
                        seen.add((m["namespace"], m["name"]))
                        targets.append((comp, k, m["namespace"], m["name"], o))
    result: dict = {"ok": True, "components": {}, "targets": len(targets)}
    for comp, kind, ns, wl, o in targets:
        sel = (o.get("spec", {}).get("selector") or {}).get("matchLabels") or {}
        rec = result["components"].setdefault(comp, {})
        if not sel:
            rec[f"{ns}/{wl}"] = {"ok": False, "error": "no selector.matchLabels"}
            continue
        selector = ",".join(f"{k}={v}" for k, v in sel.items())
        out = snap / "logs" / "pods" / comp / f"{ns}_{wl}.log"
        out.parent.mkdir(parents=True, exist_ok=True)
        args = ["logs", "-n", ns, "-l", selector, "--all-containers", "--prefix", "--timestamps", f"--since={since}", f"--tail={tail_ds if kind == 'daemonsets' else tail}", "--max-log-requests", "40", "--ignore-errors"]
        r = kube.kubectl(args, context=context, timeout=timeout, id=f"{name}.{sid}.{comp}.{ns}/{wl}", log=log, out_path=out, kubeconfig=kubeconfig, collector=name)
        lines = r.stdout.count("\n") if r.ok else 0
        if r.ok and lines == 0:
            out.unlink(missing_ok=True)
        rec[f"{ns}/{wl}"] = {"ok": r.ok, "kind": kind[:-1], "lines": lines, "out": str(out.relative_to(snap)) if (r.ok and lines) else None, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
    if echo:
        for comp, wls in result["components"].items():
            echo(f"    {comp:<28} workloads {len(wls)}, lines {sum(w.get('lines', 0) for w in wls.values())}" + ("" if all(w["ok"] for w in wls.values()) else " (some failed)"))
    return result


@dataclass
class StepContext:
    """Everything a step handler may need, bundled so that all `_step_<type>` handlers share one signature `(ctx, st) -> dict`.

    One StepContext is built per collector (`name`, `folder`), and the connections (`prom`, `stores`, `node_access`) and the
    per-run `state` are shared across collectors by `collect()`."""

    name: str
    folder: Path
    context: str | None
    cfg: Config
    inv: dict
    snap: Path
    log: RunLog
    kubeconfig: str | None
    prom: Prometheus | None
    stores: Stores | None
    node_access: NodeRunner | None
    echo: Callable | None
    state: CollectState

    @property
    def eks(self) -> dict:
        return (self.inv.get("cluster") or {}).get("eks") or {}

    def node_backend_ok(self) -> bool:
        """True when a node command backend exists (ssh or ssm), the precondition for the pod-metrics node-curl fallback."""
        return self.node_access is not None and getattr(getattr(self.node_access, "na", None), "method", None) in ("ssh", "ssm")

    def skip(self, sid: str, reason: str, result: dict | None = None) -> dict:
        self.log.skip(id=f"{self.name}.{sid}", reason=reason, collector=self.name)
        return result if result is not None else {"ok": False, "error": reason}


# ---------- step handlers. Signature: (ctx: StepContext, st: dict) -> dict (the per-step entry in collect-result.json) ----------


def _step_kubectl_dump_all(ctx: StepContext, st: dict) -> dict:
    return dump_all(ctx.context, ctx.kubeconfig, ctx.snap, st.get("exclude", []), float(st.get("timeout", 60)), ctx.log, ctx.name, ctx.echo)


def _step_kubectl(ctx: StepContext, st: dict) -> dict:
    sid, timeout = st["id"], float(st.get("timeout", 60))
    if st.get("for_each") == "nodes":
        # Once per node (e.g. kubelet configz). Failed nodes are recorded in runs with error and we continue.
        runs = {}
        for node in [n["name"] for n in (ctx.inv.get("nodes") or {}).get("nodes", [])]:
            out = ctx.snap / str(st["out"]).format(item=node, node=node)
            out.parent.mkdir(parents=True, exist_ok=True)
            r = kube.kubectl([str(a).format(item=node, node=node) for a in st["args"]], context=ctx.context, timeout=timeout, id=f"{ctx.name}.{sid}.{node}", log=ctx.log, out_path=out, kubeconfig=ctx.kubeconfig, collector=ctx.name)
            runs[node] = {"ok": r.ok, "out": str(out.relative_to(ctx.snap)) if r.ok else None, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
        if ctx.echo:
            ctx.echo(f"    {sum(1 for x in runs.values() if x['ok'])} of {len(runs)} nodes saved ({st['out']})")
        return {"ok": any(x["ok"] for x in runs.values()), "nodes": runs}
    out = ctx.snap / st["out"]
    r = kube.kubectl(list(st["args"]), context=ctx.context, timeout=timeout, id=f"{ctx.name}.{sid}", log=ctx.log, out_path=out, kubeconfig=ctx.kubeconfig, collector=ctx.name)
    if r.ok and out.suffix == ".json":
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
            _scrub(data)
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            n = len(data.get("items", []) or []) if isinstance(data, dict) else None
        except json.JSONDecodeError:
            n = None
    else:
        n = None
    res = {"ok": r.ok, "items": n, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
    if ctx.echo:
        ctx.echo(f"    {'saved ' + st['out'] + (f' ({n} items)' if n is not None else '') if r.ok else 'failed: ' + str(res['error'])[:120]}")
    return res


def _step_pod_metrics(ctx: StepContext, st: dict) -> dict:
    """Read /metrics through the pod proxy (read-only GET, for components Prometheus does not scrape — e.g. the MetalLB speaker). <out>/<pod>.prom per pod"""
    sid, timeout = st["id"], float(st.get("timeout", 60))
    name, snap, inv, context, node_access = ctx.name, ctx.snap, ctx.inv, ctx.context, ctx.node_access
    sel = st["selector"]
    ns = st["namespace"]
    r = kube.kubectl(["get", "pods", "-n", ns, "-l", sel, "-o", "json"], context=context, timeout=timeout, id=f"{name}.{sid}.list", log=ctx.log, kubeconfig=ctx.kubeconfig, collector=name)
    runs: dict = {}
    if not r.ok:
        res = {"ok": False, "pods": {}, "error": r.error or r.stderr.strip()[-200:]}
    else:
        try:
            plist = json.loads(r.stdout).get("items") or []
        except json.JSONDecodeError:
            plist = []
        skip_arg = st.get("skip_if_container_arg")  # e.g. with the KEDA operator `--enable-prometheus-metrics=false`, no /metrics is normal -> skip instead of counting a failure
        if skip_arg and plist and all(any(skip_arg in str(a) for c in ((p.get("spec") or {}).get("containers") or []) for a in (c.get("args") or [])) for p in plist):
            if ctx.echo:
                ctx.echo(f"    skipped: {skip_arg} (metrics disabled, expected)")
            return ctx.skip(sid, f"container arg {skip_arg}", {"ok": True, "skipped": True, "pods": {}, "note": f"container arg {skip_arg} — no metrics is expected"})
        node_ok = ctx.node_backend_ok()
        for p in plist:
            pname = p["metadata"]["name"]
            out = snap / st["out"] / f"{pname}.prom"
            out.parent.mkdir(parents=True, exist_ok=True)
            if context in ctx.state.proxy_blocked and node_ok:
                # The pod proxy already timed out in this context (EKS node SG). Go straight to node curl instead of waiting 20-30 s again per pod (on a real EKS run, 11 proxy waits took a large share of an 817 s collection)
                rr = _Blocked()
            else:
                rr = kube.kubectl(
                    ["get", "--raw", f"/api/v1/namespaces/{ns}/pods/{pname}:{st['port']}/proxy{st.get('path', '/metrics')}"],
                    context=context,
                    timeout=min(timeout, 20),
                    id=f"{name}.{sid}.{pname}",
                    log=ctx.log,
                    out_path=out,
                    kubeconfig=ctx.kubeconfig,
                    collector=name,
                )
                err_text = ((rr.error or "") + (getattr(rr, "stderr", "") or "")).lower()
                # kubectl reports a blocked proxy as "Client.Timeout exceeded" or "context deadline exceeded" (never "timed out"); an earlier version matched only "timed out", so every pod waited the full 20 s on EKS
                if not rr.ok and (getattr(rr, "timed_out", False) or any(k in err_text for k in ("timed out", "timeout", "deadline exceeded"))) and node_ok:
                    ctx.state.proxy_blocked.add(context)
            via = "apiserver-proxy"
            if rr.ok and out.exists():
                # Make the proxy path look like the node path — drop comments and histogram buckets, and keep only matching lines if a keep regex exists (seen on a k3s: where the proxy worked, a 324 KB raw Argo CD server metrics dump was stored as is).
                try:
                    _keep = re.compile(st["keep"]) if st.get("keep") else None
                    _lines = [ln for ln in out.read_text(encoding="utf-8", errors="replace").splitlines() if ln and not ln.startswith("#") and "_bucket{" not in ln and (_keep is None or _keep.search(ln))]
                    out.write_text("\n".join(_lines) + ("\n" if _lines else ""), encoding="utf-8")
                except (OSError, re.error):
                    pass
            if not rr.ok and node_ok:
                # Fallback for clusters where apiserver -> pod proxy is blocked by the node security group (timeouts seen on EKS and small k3s cluster): curl the pod IP from inside a reachable node.
                # Try the node hosting the pod first, then (if e.g. not registered in SSM) another node — the pod network is reachable from any node.
                pip = (p.get("status") or {}).get("podIP")
                cand = [(p.get("spec") or {}).get("nodeName")] + [n["name"] for n in (inv.get("nodes") or {}).get("nodes", []) if n["name"] != (p.get("spec") or {}).get("nodeName")]
                for nd in [c for c in cand if c]:
                    if pip is None:
                        break
                    # Because of the SSM 24,000-character output cap, histogram buckets (_bucket) and comments are filtered on the node (the ALB controller leader was truncated with buckets included). _sum and _count remain
                    # The curl text comes from lib/nodecommands (same source as COMMANDS.md and the SSM document); on SSM only the step name and podIp are sent. `keep` narrows chatty controllers to the metric names the checks need.
                    nr = node_access.na.run_on_node(
                        nd, nodecommands.pod_metrics_cmd(pip, st["port"], st.get("path", "/metrics"), st.get("keep")), timeout=30, id=f"{name}.{sid}.{pname}.node", collector=name, step=f"{name}/{sid}", params={"podIp": pip}
                    )
                    if nr.ok and nr.stdout.strip():
                        out.write_text(nr.stdout, encoding="utf-8")
                        rr = nr
                        via = f"node:{nd}"
                        break
            runs[pname] = {
                "ok": rr.ok,
                "via": via if rr.ok else None,
                "node": (p.get("spec") or {}).get("nodeName"),
                "out": str(out.relative_to(snap)) if rr.ok else None,
                "error": None if rr.ok else (rr.error or getattr(rr, "stderr", "").strip()[-200:]),
            }
        res = {"ok": any(x["ok"] for x in runs.values()) if runs else False, "pods": runs, "error": None if runs else f"no {sel} pods in {ns}"}
    if ctx.echo:
        ctx.echo(f"    {sum(1 for x in runs.values() if x['ok'])} of {len(runs)} pods /metrics saved ({st['out']})")
    return res


def _step_promql(ctx: StepContext, st: dict) -> dict:
    if ctx.prom is None:
        if ctx.echo:
            ctx.echo("    skipped: no Prometheus connection")
        return ctx.skip(st["id"], "no Prometheus connection")
    return ctx.prom.run_file(ctx.folder / st["file"], ctx.snap / "metrics", log=ctx.log, collector=ctx.name, timeout=float(st.get("timeout", 60)), echo=ctx.echo)


def _step_http(ctx: StepContext, st: dict) -> dict:
    if ctx.stores is None:
        return {"ok": False, "error": "no stores"}
    return _run_http_step(st, st["id"], ctx.name, ctx.cfg, ctx.snap, ctx.log, ctx.stores, float(st.get("timeout", 60)), ctx.echo)


def _step_cwlogs(ctx: StepContext, st: dict) -> dict:
    from . import cwlogs as _cw

    eks = ctx.eks
    return _cw.run_file(
        ctx.folder / st["file"],
        ctx.snap / "logs" / "cloudwatch",
        cluster=eks.get("name"),
        profile=ctx.cfg.get("aws_profile") or eks.get("profile"),
        region=ctx.cfg.get("aws_region") or eks.get("region"),
        log=ctx.log,
        collector=ctx.name,
        echo=ctx.echo,
        default_hours=float(st.get("hours", 24)),
    )


def _step_node(ctx: StepContext, st: dict) -> dict:
    return _run_node_step(st, st["id"], ctx.name, ctx.inv, ctx.cfg, ctx.snap, ctx.log, ctx.node_access, float(st.get("timeout", 60)), ctx.echo)


def _step_alb_metrics(ctx: StepContext, st: dict) -> dict:
    from . import albmetrics as _alb

    eks = ctx.eks
    return _alb.collect(
        ctx.snap,
        st["out"],
        profile=ctx.cfg.get("aws_profile") or eks.get("profile"),
        region=ctx.cfg.get("aws_region") or eks.get("region"),
        log=ctx.log,
        collector=ctx.name,
        timeout=float(st.get("timeout", 60)),
        hours=int(st.get("hours", 24)),
        echo=ctx.echo,
    )


def _step_cw_metrics(ctx: StepContext, st: dict) -> dict:
    from . import cwmetrics as _cw

    eks = ctx.eks
    return _cw.collect(
        ctx.snap, {**st, "id": st["id"]}, profile=ctx.cfg.get("aws_profile") or eks.get("profile"), region=ctx.cfg.get("aws_region") or eks.get("region"), log=ctx.log, collector=ctx.name, timeout=float(st.get("timeout", 60)), echo=ctx.echo
    )


def _step_tool(ctx: StepContext, st: dict) -> dict:
    return _run_tool_step(st, st["id"], ctx.name, ctx.context, ctx.kubeconfig, ctx.snap, ctx.log, ctx.stores, float(st.get("timeout", 60)), ctx.echo, inv=ctx.inv)


def _step_component_logs(ctx: StepContext, st: dict) -> dict:
    return _run_component_logs_step(st, st["id"], ctx.name, ctx.inv, ctx.context, ctx.kubeconfig, ctx.snap, ctx.log, float(st.get("timeout", 60)), ctx.echo)


def _step_aws(ctx: StepContext, st: dict) -> dict:
    return _run_aws_step(st, st["id"], ctx.name, ctx.eks, ctx.cfg, ctx.snap, ctx.log, float(st.get("timeout", 60)), ctx.echo, inv=ctx.inv)


# Dispatch table: collect.yaml `type` -> handler. A new step type is one function plus one entry here.
STEP_HANDLERS: dict[str, Callable[[StepContext, dict], dict]] = {
    "kubectl-dump-all": _step_kubectl_dump_all,
    "kubectl": _step_kubectl,
    "pod-metrics": _step_pod_metrics,
    "promql": _step_promql,
    "http": _step_http,
    "cwlogs": _step_cwlogs,
    "node": _step_node,
    "alb-metrics": _step_alb_metrics,
    "cw-metrics": _step_cw_metrics,
    "tool": _step_tool,
    "component-logs": _step_component_logs,
    "aws": _step_aws,
}

# Step types that call a cloud provider API and are only meaningful when the inventory says the cluster runs on that cloud.
# This is the single place where a cloud is gated: a GKE or AKS step type would be registered here with its own cloud key, and
# `_cloud_available` would learn to read that cloud's inventory block (today only `cluster.eks` exists).
CLOUD_STEP_TYPES: dict[str, str] = {"aws": "aws", "cwlogs": "aws", "alb-metrics": "aws", "cw-metrics": "aws"}
_CLOUD_SKIP_REASON = {"aws": "not EKS"}


def _cloud_available(inv: dict, cloud: str) -> bool:
    """Whether the inventory carries the facts a cloud-API step needs (for aws: the `cluster.eks` dict written by discover on EKS)."""
    if cloud == "aws":
        return bool((inv.get("cluster") or {}).get("eks"))
    return False


def _parallel(fn, items, workers: int | None = None) -> list:
    """Run fn over items in a small thread pool and return the results in input order (collect-result.json stays deterministic). One item → no pool."""
    items = list(items)
    if len(items) <= 1:
        return [fn(it) for it in items]
    with ThreadPoolExecutor(max_workers=min(workers or ITEM_WORKERS, len(items)), thread_name_prefix="step") as pool:
        return list(pool.map(fn, items))


def step_in_mode(st: dict, mode: str) -> bool:
    """A step runs in every mode unless its collect.yaml entry lists `modes:`; `modes: [full]` marks a step the daily run skips (slow tools, per-node scripts, CloudWatch queries, cost data)."""
    modes = st.get("modes")
    return not modes or mode in modes


def run_collector(
    name: str,
    context: str | None,
    cfg: Config,
    inv: dict,
    snap: Path,
    log: RunLog,
    kubeconfig: str | None = None,
    prom: Prometheus | None = None,
    stores: Stores | None = None,
    node_access: NodeRunner | None = None,
    echo=None,
    state: CollectState | None = None,
    mode: str = paths.DEFAULT_MODE,
) -> dict:
    folder = paths.COLLECTORS_DIR / name
    spec_path = folder / "collect.yaml"
    result: dict = {"collector": name, "steps": {}}
    if not spec_path.is_file():
        result["skipped"] = "no collect.yaml (collector not implemented)"
        log.skip(id=f"collector.{name}", reason=result["skipped"], collector=name)
        return result
    steps = yamlite.load_file(spec_path) or []
    ctx = StepContext(name, folder, context, cfg, inv, snap, log, kubeconfig, prom, stores, node_access, echo, state if state is not None else CollectState())
    for st in steps:
        sid, typ = st["id"], st["type"]
        if echo:
            echo(f"  [{name}] {sid}")
        if not step_in_mode(st, mode):
            result["steps"][sid] = ctx.skip(sid, f"not collected in {mode} mode", {"ok": True, "skipped": f"not collected in {mode} mode", "mode_skipped": True, "out": st.get("out") or st.get("file")})
            continue
        handler = STEP_HANDLERS.get(typ)
        if handler is None:
            result["steps"][sid] = ctx.skip(sid, f"unknown type {typ} (known: {', '.join(STEP_HANDLERS)})")
            continue
        cloud = CLOUD_STEP_TYPES.get(typ)
        if cloud and not _cloud_available(inv, cloud):
            result["steps"][sid] = ctx.skip(sid, _CLOUD_SKIP_REASON[cloud])
            continue
        result["steps"][sid] = handler(ctx, st)
    return result


def collect(context: str, cfg: Config, inv: dict, snap: Path, log: RunLog, *, kubeconfig: str | None = None, only: list[str] | None = None, mode: str = paths.DEFAULT_MODE, echo=print) -> dict:
    if mode not in paths.MODES:
        raise ValueError(f"unknown collection mode {mode!r} (expected one of {', '.join(paths.MODES)})")
    log.stage("collect", "start", mode=mode)
    (snap / "MODE").write_text(mode + "\n", encoding="utf-8")  # read back by paths.snapshot_mode: latest/previous selection stays within one mode
    enabled = inv.get("collectors_enabled") or ["core"]
    if only:
        enabled = [c for c in enabled if c in only]
    results = {}
    (snap / "INCOMPLETE").write_text("collect in progress. If this file remains, the snapshot was interrupted.\n", encoding="utf-8")
    t_start = _time.monotonic()
    prom = Prometheus.connect(context, cfg.url("prometheus"), kubeconfig, log=log)
    if prom is None:
        echo("  Could not connect to Prometheus; all PromQL steps are skipped")
    stores = Stores(context, cfg, inv, kubeconfig, log)
    node_runner = NodeRunner(inv, cfg, log)
    state = CollectState()
    print_lock = threading.Lock()

    def run_one(name: str) -> tuple[str, dict]:
        # Collectors are independent of each other (a step only reads outputs of earlier steps in the same collector), so they run concurrently.
        # Output lines are buffered per collector and printed as one block when it finishes, so the log stays readable.
        buf: list[str] = []
        res = run_collector(name, context, cfg, inv, snap, log, kubeconfig=kubeconfig, prom=prom, stores=stores, node_access=node_runner, echo=buf.append if echo else None, state=state, mode=mode)
        if echo:
            with print_lock:
                for line in buf:
                    echo(line)
        return name, res

    try:
        # `core` is submitted first: it is the longest collector (object dump, events, the PromQL list), so starting it first keeps it from becoming the tail of the run
        order = [c for c in enabled if c == "core"] + [c for c in enabled if c != "core"]
        with ThreadPoolExecutor(max_workers=COLLECTOR_WORKERS, thread_name_prefix="collector") as pool:
            for name, res in pool.map(run_one, order):
                results[name] = res
        results = {name: results[name] for name in enabled}  # keep collect-result.json in the inventory's collector order
    finally:
        if prom:
            prom.close()
        stores.close()
    steps = [(cn, sid, st) for cn, cr in results.items() for sid, st in ((cr or {}).get("steps") or {}).items()]
    results["_summary"] = {  # top-level summary. The key is not a collector name, so consumers skip keys starting with '_'
        "mode": mode,
        "collectors": [c for c in results if not c.startswith("_")],
        "steps": len(steps),
        "mode_skipped": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("mode_skipped")],
        "failed": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("ok") is False and not st.get("skipped")],
        "skipped": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("skipped") and not st.get("mode_skipped")],
        "seconds_total": round(_time.monotonic() - t_start, 1),
    }
    (snap / "collect-result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with contextlib.suppress(OSError):
        (snap / "INCOMPLETE").unlink()
    log.stage("collect", "end", collectors=len(results) - 1)
    return results

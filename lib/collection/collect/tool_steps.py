"""The tool step: an external CLI (krr, polaris, pluto, kubent, helm) run locally against the cluster or the saved objects.

Part of the collector (lib/collection/collect): the runner in the package's __init__ dispatches each collect.yaml step to a handler here through
STEP_HANDLERS; every handler has the signature `(ctx: StepContext, st: dict) -> dict`, the per-step entry of collect-result.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ...foundations import lastapplied, mask, paths, versions
from ...foundations.runlog import RunLog
from ...foundations.snapshot import write_private
from .context import StepContext, Stores


def run_tool_step(st: dict, sid: str, name: str, context: str | None, kubeconfig: str | None, snap: Path, log: RunLog, stores: Stores | None, timeout: float, echo, inv: dict | None = None, objects_dump: dict | None = None) -> dict:
    """Run an external CLI (KRR, Polaris, Pluto, etc.) locally. Placeholders in cmd: {context} {out} (absolute path) {prometheus_url} etc. {<store>_url}.
    tool: executable name (PATH or .tools/bin). If missing, the step is skipped and becomes input for the report's "tool missing" section. If a store URL is needed but there is no connection, the step is skipped.
    The kubeconfig the run was given reaches every tool as the KUBECONFIG environment variable, so a command names the context only and a context that lives outside
    ~/.kube/config still resolves (#104). Checked in the sources of the pinned versions, not assumed: polaris v10.2.6 has no kubeconfig flag and calls controller-runtime
    GetConfigWithContext (pkg/kube/resources.go:249), whose loader reads KUBECONFIG (controller-runtime v0.25.2 pkg/client/config/config.go:123); kubent 0.7.3 defaults its
    --kubeconfig flag to os.Getenv(KUBECONFIG) (pkg/config/config.go:50); helm v4.3.1 reads it in pkg/cli/environment.go:101; krr v1.31.1 passes kubeconfig=None to kubernetes-python
    load_kube_config (core/integrations/kubernetes/__init__.py:185), whose default location is the KUBECONFIG value (kubernetes/config/kube_config.py:48). A future tool that reads
    only a flag would need the flag in its cmd; none of the four does. pluto does not contact the cluster: a step with `stdin: last-applied` gets lib/foundations/lastapplied.py's List on stdin,
    built from what objects.dump-all saved, and fails instead of judging nothing when that step saved no kind (`objects_dump`, the step's result)."""
    from ...foundations import shell as _shell

    tool_env = {"KUBECONFIG": kubeconfig} if kubeconfig else None

    tool = st.get("tool") or st["cmd"][0]
    path = _shell.which(tool)
    if not path:
        log.skip(id=f"{name}.{sid}", reason=f"tool {tool} missing", collector=name)
        if echo:
            echo(f"    skipped: tool {tool} missing (setup --install-only {tool})")
        return {"ok": False, "skipped": f"tool {tool} missing", "tool_missing": tool}
    out = snap / st["out"]
    paths.ensure_private_dir(out.parent)  # the tool writes the file itself, so the folder must exist before it runs
    ph = {"context": context or "", "out": str(out)}
    # Next minor of the cluster server version (target for Pluto/kubent). v1.32.13-eks -> v1.33.0 / 1.33
    nxt = versions.next_minor_text(((inv or {}).get("cluster") or {}).get("server_version"))
    if nxt:
        ph["k8s_next_minor"] = f"v{nxt}.0"
        ph["k8s_next_minor_short"] = nxt
    elif any("{k8s_next_minor" in str(a) for a in st["cmd"]):
        # No server version, no target: a made-up one (this used to be 1.99) makes pluto flag every API as removed and kubent list every rule set, and the summary
        # would judge the rows against the same invented minor. Skipping is the honest answer; the check then skips with the step's reason.
        reason = "server version unknown: no target minor for the deprecated-API tools"
        log.skip(id=f"{name}.{sid}", reason=reason, collector=name)
        if echo:
            echo(f"    skipped: {reason}")
        return {"ok": False, "skipped": reason}
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
            cmd_.append(a)
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
            r = _shell.run(build(extra), timeout=timeout, env=tool_env, id=f"{name}.{sid}.{safe}", log=log, collector=name, out_path=out_i)
            runs[safe] = {"ok": r.ok and out_i.is_file(), "error": None if r.ok else (r.error or r.stderr.strip()[-160:])}
        if echo:
            echo(f"    {sum(1 for x in runs.values() if x['ok'])}/{len(runs)} items saved ({str(st['out']).rsplit('/', 1)[0]})")
        return {"ok": any(x["ok"] for x in runs.values()) if runs else False, "runs": len(runs), "failed": sum(1 for x in runs.values() if not x["ok"]), "detail": runs}
    cmd = build({})
    stdin, counts = None, {}
    if st.get("stdin") == "last-applied":
        # What pluto sees is what the dump saw: kinds saved or already fetched by discovery, and kinds the server refused or that failed. No kind saved, no judgement: an empty input would read as a clean cluster.
        dump = objects_dump or {}
        counts = {"lists_ok": int(dump.get("kinds") or 0) + len(dump.get("fetched_by_discovery") or []), "lists_failed": len(dump.get("failed") or {}) + len(dump.get("not_permitted") or []) + (1 if dump.get("discovery_error") else 0)}
        if not counts["lists_ok"]:
            error = f"{tool}: API resources not confirmed read; objects.dump-all saved no kind"
            log.skip(id=f"{name}.{sid}", reason=error, collector=name)
            if echo:
                echo(f"    failed: {error}")
            return {"ok": False, "seconds": None, "error": error, "api_read": False, **counts}
        stdin, counts["manifests"] = lastapplied.pluto_input(snap)
    r = _shell.run(cmd, timeout=timeout, env=tool_env, stdin=stdin, id=f"{name}.{sid}", log=log, collector=name, out_path=None if st.get("writes_out") else out)
    if st.get("writes_out") and out.is_file():
        out.chmod(0o600)  # the tool wrote the file with its own mode (krr: 0644); every file in a snapshot is owner-only
    if tool == "krr" and out.is_file():  # whatever the exit code: the file may be complete when krr is killed after writing it
        # krr's JSON carries its whole Config (robusta_krr/core/models/result.py:70@v1.31.1): kubeconfig path, prometheus_url, this file's absolute path and, when someone
        # runs it with the EKS flags, eks_access_key as plain text (core/models/config.py:47; only the *_secret_key, auth header and token fields are SecretStr and come out
        # masked). Nothing in kubegap reads it, so it is dropped before the file is read again; strategy.settings, which the summary reads, is a separate key.
        try:
            doc = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = None
        if isinstance(doc, dict) and "config" in doc:
            doc.pop("config")
            write_private(out, json.dumps(doc, ensure_ascii=False, indent=2))
    ok = r.ok and out.is_file() and out.stat().st_size > 0
    read = None
    error = r.error or r.stderr.strip()[-300:] or "no output"
    if tool == "kubent":
        read = False
        stderr = mask.strip_control(r.stderr)[0]  # kubent's zerolog ConsoleWriter colours field names (SGR sequences); lib/foundations/mask knows the shapes
        # kubent logs one line per List and one more when it failed, and swallows the failure: pkg/collector/cluster.go:121,124-125@0.7.3 at --log-level=debug
        # (the default is Info, pkg/config/config.go:38; the step passes the flag). `Retrieving` minus `Failed to retrieve` is the number of Lists that succeeded.
        # A forbidden kind is a failed List, so the count never says the whole API was read (#132). Observed 2026-11-04 with the pinned binary: 41 started / 13 failed
        # on k3s and on EKS, 0 / 0 against a context that does not exist.
        started = len(re.findall(r"\bRetrieving ?: ", stderr))
        counts = {"lists_failed": len(re.findall(r"\bFailed to retrieve: ", stderr))}
        counts["lists_ok"] = max(started - counts["lists_failed"], 0)
        if ok:
            try:
                doc = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                doc = None
            # `Retrieved N resources from collector name=Cluster` (cmd/kubent/main.go:49) counts the objects that carry a last-applied-configuration annotation
            # (cluster.go:129-130), so 0 is what a cluster managed by Helm or server-side apply prints after reading everything; a positive N is still evidence
            # when the log carries no List lines. main.go:45,56: the collector failed to initialise or to return, whatever else the log says.
            cluster = re.search(r"Retrieved ([0-9]+) resources from collector[^\n]*name=Cluster\b", stderr)
            if cluster:
                counts["manifests"] = int(cluster.group(1))
            read = isinstance(doc, list) and (counts["lists_ok"] > 0 or bool(cluster and int(cluster.group(1))))
            if "Failed to initialize collector" in stderr or "Failed to retrieve data from collector" in stderr:
                read = False
            ok = bool(read)
            if not ok:
                # The tail of stderr is not the reason: kubent ends every run with its `Loaded ruleset` lines. Keep the lines that say what happened.
                why = [ln.strip() for ln in stderr.splitlines() if any(k in ln for k in ("Failed", "Retrieved", "ERR", "error"))]
                error = f"{tool}: API resources not confirmed read" + (f"; {'; '.join(why[-3:])[-300:]}" if why else " (no item and no successful List in its log)")
    elif tool == "pluto":
        read = False
        if ok:
            # The input is the evidence of what was read (the guard above). What is left to confirm is that pluto answered: pkg/api/output.go:58@v5.24.5 omits empty items, so a clean run is `{"target-versions": ...}`.
            try:
                doc = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                doc = None
            read = isinstance(doc, dict)
            ok = read
            if not ok:
                error = f"{tool}: output is not the JSON object it prints"
        elif r.stdout.strip():
            # pluto prints the error of `detect` with fmt.Println, to stdout, and exits 1 (cmd/root.go:407,413,419@v5.24.5); stderr holds klog's `assuming default targetVersion` lines only, so the tail of stderr would not say why.
            error = "; ".join(x for x in (r.error, r.stdout.strip()[-300:], mask.strip_control(r.stderr)[0].strip()[-300:]) if x)
    if echo:
        echo(f"    {'saved ' + st['out'] + f' ({out.stat().st_size // 1024} KB)' if ok else 'failed: ' + error}")
    result = {"ok": ok, "seconds": round(r.seconds, 1) if hasattr(r, "seconds") else None, "error": None if ok else error, **counts}
    if read is not None:
        result["api_read"] = bool(ok and read)
    return result


def step_tool(ctx: StepContext, st: dict) -> dict:
    return run_tool_step(st, st["id"], ctx.name, ctx.context, ctx.kubeconfig, ctx.snap, ctx.log, ctx.stores, float(st.get("timeout", 60)), ctx.echo, inv=ctx.inv, objects_dump=ctx.state.objects_dump)

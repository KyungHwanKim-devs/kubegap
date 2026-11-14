"""The Kubernetes API steps: kubectl Lists and the dump of every kind, /metrics through the pod proxy (with the node-curl fallback), component pod logs.

Part of the collector (lib/collection/collect): the runner in the package's __init__ dispatches each collect.yaml step to a handler here through
STEP_HANDLERS; every handler has the signature `(ctx: StepContext, st: dict) -> dict`, the per-step entry of collect-result.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ...foundations import components, podmetrics, scrub
from ...foundations.runlog import RunLog
from ...foundations.snapshot import write_private
from .. import kube, nodecommands
from .context import StepContext

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

SECRET_KINDS = {"Secret", "SecretList"}


NON_WORKLOAD_COMPONENTS = {"ecr", "eks-managed-addons", "k3s", "rke2"}  # registry and platform names are not pods and not log collection targets (app pod logs once ended up under the "ecr" component)


class Blocked:
    """Fake failure result used to go straight to node curl without trying the proxy."""

    ok = False
    stdout = ""
    stderr = "apiserver pod proxy blocked earlier in this run"
    error = "proxy blocked (skipped)"


def glob_match(name: str, patterns: list[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def api_resources(context: str | None, kubeconfig: str | None, log: RunLog) -> tuple[list[dict], str | None]:
    """Parse `kubectl api-resources --verbs=list -o wide` into a list of (name, namespaced, kind, full name), with the error of a discovery that was only partial.
    kubectl prints what it found and still exits non-zero when one group failed (an unhealthy aggregated API), so those rows are good; on a timeout the last row may be cut, so nothing is."""
    r = kube.kubectl(["api-resources", "--verbs=list", "-o", "wide"], context=context, timeout=60, id="collect.api-resources", log=log, kubeconfig=kubeconfig)
    error = None if r.ok else (r.error or r.stderr.strip()[-200:] or "kubectl api-resources failed")
    if (not r.ok and not r.stdout.strip()) or r.timed_out:
        return [], error
    lines = r.stdout.splitlines()
    if not lines:
        return [], error
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
    return out, error


DISCOVERY_RESOURCES = {
    "nodes",
    "namespaces",
    "services",
    "pods",
    "configmaps",
    "storageclasses.storage.k8s.io",
    "customresourcedefinitions.apiextensions.k8s.io",
    "daemonsets.apps",
    "deployments.apps",
    "statefulsets.apps",
    "cronjobs.batch",
}  # discover.OBJECT_KINDS as `kubectl api-resources` names them


def dump_all(context: str | None, kubeconfig: str | None, snap: Path, exclude: list[str], timeout: float, log: RunLog, collector: str, echo=None, *, light: bool = False) -> dict:
    resources, discovery_error = api_resources(context, kubeconfig, log)
    done = {p.stem for p in (snap / "objects").glob("*.json")}
    # `served` is every kind the API listed and `written` every file stem this step wrote; with `fetched_by_discovery` (the kinds lib/collection/discover.py had saved, by full
    # name), `excluded`, `not_permitted` and `failed` they let a reader of a missing objects file tell "the cluster has no such kind" from "the file is named
    # differently" (#160). The key is not `skipped`: in a step record that word is the reason the whole step did not run, and `_summary.skipped` and report
    # section 7-1 listed this step as skipped with the eleven kinds as its reason.
    summary = {"kinds": 0, "items": 0, "written": [], "served": [res["full"] for res in resources], "fetched_by_discovery": [], "failed": {}, "excluded": [], "not_permitted": [], "discovery_error": discovery_error}
    hard_exclude = ["secrets", "secrets.*"]
    for res in resources:
        full, name = res["full"], res["name"]
        if glob_match(name, hard_exclude) or glob_match(full, hard_exclude) or (res.get("kind") or "") in SECRET_KINDS:
            summary["excluded"].append(full)
            continue
        if glob_match(name, exclude) or glob_match(full, exclude):
            summary["excluded"].append(full)
            continue
        # Kinds discovery already fetched (nodes, pods, deployments ...) are not fetched again. File name: core group and discovery's kinds = name only, others = name.group.
        # A discovery kind keeps its short name even when discovery failed to save it and this step fetches it, so a kind has one file name whoever wrote it (#160)
        core_group = not res.get("apiversion", "").count("/")
        file_stem = name if core_group or full in DISCOVERY_RESOURCES else full
        if full in done or (full in DISCOVERY_RESOURCES and name in done):  # `name` alone would also match a CRD of the same plural (services.serving.knative.dev), which was then never fetched
            summary["fetched_by_discovery"].append(full)
            continue
        args = ["get", full] + (["-A"] if res["namespaced"] else [])
        data, r = kube.kubectl_json(args, context=context, timeout=timeout, id=f"collect.get-{full}", log=log, kubeconfig=kubeconfig, collector=collector)
        if data is None:
            if "is forbidden:" in (r.stderr or "") or "(Forbidden)" in (r.stderr or ""):  # RBAC denial: the ClusterRole does not grant this kind. A check that needs it skips as "missing", never passes
                summary["not_permitted"].append(full)
            else:
                summary["failed"][full] = r.error or r.stderr.strip()[-200:]
            continue
        err = scrub.scrub_or_error(data, light=light)
        if err:  # the kind is not written; run.log and the step record carry the failure so report section 7-1 shows it
            summary["failed"][full] = err
            summary["ok"] = False
            log.command(id=f"{collector}.scrub-{full}", cmd=["scrub", full], code=0, seconds=0.0, error=err, collector=collector)
            continue
        write_private(snap / "objects" / f"{file_stem}.json", json.dumps(data, ensure_ascii=False))
        n = len(data.get("items", []) or [])
        summary["written"].append(file_stem)
        summary["kinds"] += 1
        summary["items"] += n
    if echo:
        echo(
            f"    {summary['kinds']} kinds, {summary['items']} objects saved. fetched by discovery already {len(summary['fetched_by_discovery'])}, excluded {len(summary['excluded'])}, not permitted by the ClusterRole {len(summary['not_permitted'])}, failed {len(summary['failed'])}"
        )
        for k, v in summary["failed"].items():
            echo(f"      failed {k}: {v[:100]}")
    return summary


def run_component_logs_step(st: dict, sid: str, name: str, inv: dict, context: str | None, kubeconfig: str | None, snap: Path, log: RunLog, timeout: float, echo) -> dict:
    """Fetch workload pod logs of detected components (components_present) with kubectl logs into logs/pods/<component>/<ns>_<workload>.log.
    User application logs are not fetched (that is Loki's job). Capped tail lines per pod, 24 hours."""
    from ...foundations.components import COMPONENTS

    kinds = ("daemonsets", "deployments", "statefulsets")
    objs = {}
    for k in kinds:
        try:
            objs[k] = (json.loads((snap / "objects" / f"{k}.json").read_text(encoding="utf-8")) or {}).get("items", [])
        except (OSError, json.JSONDecodeError):
            objs[k] = []
    present = [c for c in (inv.get("components_present") or []) if c not in set(st.get("exclude") or []) and c not in NON_WORKLOAD_COMPONENTS]
    rules = {c["name"]: c for c in COMPONENTS}
    since, tail, tail_ds = str(st.get("since", "24h")), int(st.get("tail", 1500)), int(st.get("tail_daemonset", 600))  # tail_daemonset: Kubernetes DaemonSet workloads (one pod per node, so a smaller cap each)
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
                        hit = components.match_name(pat, m["namespace"], m["name"])
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


def metrics_filter(keep: str | None):
    """A `shell.run` transform that makes the proxy path look like the node path before the file exists: drop comments and histogram buckets,
    and keep only the lines a `keep` regex matches (on a k3s, where the proxy worked, a 324 KB raw Argo CD server metrics dump was once stored as is).
    An invalid regex keeps every non-comment line rather than failing the step."""
    try:
        rx = re.compile(keep) if keep else None
    except re.error:
        rx = None

    def fn(text: str) -> str:
        lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#") and "_bucket{" not in ln and (rx is None or rx.search(ln))]
        return "\n".join(lines) + ("\n" if lines else "")

    return fn


def step_kubectl_dump_all(ctx: StepContext, st: dict) -> dict:
    ctx.state.objects_dump = dump_all(ctx.context, ctx.kubeconfig, ctx.snap, st.get("exclude", []), float(st.get("timeout", 60)), ctx.log, ctx.name, ctx.echo, light=ctx.light)
    return ctx.state.objects_dump


def step_kubectl(ctx: StepContext, st: dict) -> dict:
    sid, timeout = st["id"], float(st.get("timeout", 60))
    if st.get("for_each") == "nodes":
        # Once per node (e.g. kubelet configz). Failed nodes are recorded in runs with error and we continue.
        runs = {}
        for node in [n["name"] for n in (ctx.inv.get("nodes") or {}).get("nodes", [])]:
            out = ctx.snap / str(st["out"]).format(item=node, node=node)
            tf = scrub.json_scrubber(light=ctx.light)[0] if out.suffix == ".json" else None
            r = kube.kubectl(
                [str(a).format(item=node, node=node) for a in st["args"]], context=ctx.context, timeout=timeout, id=f"{ctx.name}.{sid}.{node}", log=ctx.log, out_path=out, kubeconfig=ctx.kubeconfig, collector=ctx.name, transform=tf
            )
            runs[node] = {"ok": r.ok, "out": str(out.relative_to(ctx.snap)) if r.ok else None, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
        if ctx.echo:
            ctx.echo(f"    {sum(1 for x in runs.values() if x['ok'])} of {len(runs)} nodes saved ({st['out']})")
        return {"ok": any(x["ok"] for x in runs.values()), "nodes": runs}
    out = ctx.snap / st["out"]
    # JSON output is scrubbed inside shell.run before the file exists (lib/foundations/scrub.py json_scrubber); if scrubbing raises, nothing is written and the step fails
    tf, info = scrub.json_scrubber(light=ctx.light) if out.suffix == ".json" else (None, {"items": None})
    r = kube.kubectl(list(st["args"]), context=ctx.context, timeout=timeout, id=f"{ctx.name}.{sid}", log=ctx.log, out_path=out, kubeconfig=ctx.kubeconfig, collector=ctx.name, transform=tf)
    n = info["items"] if r.ok else None
    res = {"ok": r.ok, "items": n, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
    if ctx.echo:
        ctx.echo(f"    {'saved ' + st['out'] + (f' ({n} items)' if n is not None else '') if r.ok else 'failed: ' + str(res['error'])[:120]}")
    return res


def step_pod_metrics(ctx: StepContext, st: dict) -> dict:
    """Read /metrics through the pod proxy (read-only GET, for components Prometheus does not scrape — e.g. the MetalLB speaker). <out>/<pod>.prom per pod"""
    sid, timeout = st["id"], float(st.get("timeout", 60))
    name, snap, inv, context, node_access = ctx.name, ctx.snap, ctx.inv, ctx.context, ctx.node_access
    # Where to read: found at discovery among the cluster's workloads, set in config.yaml, or the step's default (lib/foundations/podmetrics.discover_targets, #136).
    # An inventory from before #136 has no targets: every field is then the step's default, as before.
    tgt = (inv.get("pod_metrics_targets") or {}).get(f"{name}.{sid}") or podmetrics.default_target(st)
    sel, ns, port = tgt["selector"], tgt["namespace"], int(tgt["port"])
    where = f"{ns} / {sel} / port {port} ({', '.join(f'{k} {v}' for k, v in tgt['source'].items())}{', ' + tgt['workload'] if tgt.get('workload') else ''})"
    if tgt.get("skip"):
        if ctx.echo:
            ctx.echo(f"    skipped: {tgt['skip']}")
        return ctx.skip(sid, tgt["skip"], {"ok": True, "skipped": tgt["skip"], "pods": {}, "target": tgt, "note": tgt["skip"]})  # the reason, not True: report section 7-1 prints `skipped`
    r = kube.kubectl(["get", "pods", "-n", ns, "-l", sel, "-o", "json"], context=context, timeout=timeout, id=f"{name}.{sid}.list", log=ctx.log, kubeconfig=ctx.kubeconfig, collector=name)
    runs: dict = {}
    if not r.ok:
        res = {"ok": False, "pods": {}, "target": tgt, "error": r.error or r.stderr.strip()[-200:]}
    else:
        try:
            plist = json.loads(r.stdout).get("items") or []
        except json.JSONDecodeError:
            plist = []
        skip_arg = st.get("skip_if_container_arg")  # e.g. with the KEDA operator `--enable-prometheus-metrics=false`, no /metrics is normal -> skip instead of counting a failure
        if skip_arg and plist and all(any(skip_arg in str(a) for c in ((p.get("spec") or {}).get("containers") or []) for a in (c.get("args") or [])) for p in plist):
            if ctx.echo:
                ctx.echo(f"    skipped: {skip_arg} (metrics disabled, expected)")
            return ctx.skip(sid, f"container arg {skip_arg}", {"ok": True, "skipped": f"container arg {skip_arg}: no metrics is expected", "pods": {}, "target": tgt, "note": f"container arg {skip_arg} — no metrics is expected"})
        node_ok = ctx.node_backend_ok()
        for p in plist:
            pname = p["metadata"]["name"]
            out = snap / st["out"] / f"{pname}.prom"
            phase = (p.get("status") or {}).get("phase")
            pip = (p.get("status") or {}).get("podIP")
            if phase != "Running":
                # Nothing listens in a pod that is not Running; the proxy would only time out (and mark the proxy blocked for the whole context) and the node curl would go to a stale or absent address
                reason = f"pod not Running ({phase or 'no phase'})"
                ctx.log.skip(id=f"{name}.{sid}.{pname}", reason=reason, collector=name)
                runs[pname] = {"ok": False, "skipped": reason, "via": None, "node": (p.get("spec") or {}).get("nodeName"), "out": None, "error": None}
                continue
            ip_ok, ip_why = nodecommands.pod_ip_allowed(pip) if pip else (False, "no podIP")
            if context in ctx.state.proxy_blocked and node_ok:
                # The pod proxy already timed out in this context (EKS node SG). Go straight to node curl instead of waiting 20-30 s again per pod (on a real EKS run, 11 proxy waits took a large share of an 817 s collection)
                rr = Blocked()
            else:
                rr = kube.kubectl(
                    ["get", "--raw", f"/api/v1/namespaces/{ns}/pods/{pname}:{port}/proxy{st.get('path', '/metrics')}"],
                    context=context,
                    timeout=min(timeout, 20),
                    id=f"{name}.{sid}.{pname}",
                    log=ctx.log,
                    out_path=out,
                    kubeconfig=ctx.kubeconfig,
                    collector=name,
                    transform=metrics_filter(st.get("keep")),
                )
                err_text = ((rr.error or "") + (getattr(rr, "stderr", "") or "")).lower()
                # kubectl reports a blocked proxy as "Client.Timeout exceeded" or "context deadline exceeded" (never "timed out"); an earlier version matched only "timed out", so every pod waited the full 20 s on EKS
                if not rr.ok and (getattr(rr, "timed_out", False) or any(k in err_text for k in ("timed out", "timeout", "deadline exceeded"))) and node_ok:
                    ctx.state.proxy_blocked.add(context)
            via = "apiserver-proxy"
            skipped = None
            if not rr.ok and node_ok and not ip_ok:
                # The node curl is pointed only at a pod address (nodecommands.pod_ip_allowed); loopback, link-local and the like are refused here for every backend, the SSM document's allowedPattern is the second layer.
                # The pod counts as skipped only when the proxy was not really tried (blocked earlier or timed out); after a real proxy error (403, 5xx) it stays a failure that also names the refusal
                refused = f"node fallback refused: {ip_why}" + (f" (podIP {pip})" if pip else "")
                ctx.log.skip(id=f"{name}.{sid}.{pname}.node", reason=refused, collector=name)
                if isinstance(rr, Blocked) or getattr(rr, "timed_out", False):
                    skipped = refused
                else:
                    rr.error = f"{rr.error or getattr(rr, 'stderr', '').strip()[-120:]}; {refused}"
            elif not rr.ok and node_ok:
                # Fallback for clusters where apiserver -> pod proxy is blocked by the node security group (timeouts seen on EKS and small k3s cluster): curl the pod IP from inside a reachable node.
                # Try the node hosting the pod first, then (if e.g. not registered in SSM) another node — the pod network is reachable from any node.
                cand = [(p.get("spec") or {}).get("nodeName")] + [n["name"] for n in (inv.get("nodes") or {}).get("nodes", []) if n["name"] != (p.get("spec") or {}).get("nodeName")]
                for nd in [c for c in cand if c]:
                    # Because of the SSM 24,000-character output cap, histogram buckets (_bucket) and comments are filtered on the node (the ALB controller leader was truncated with buckets included). _sum and _count remain
                    # The curl text comes from lib/collection/nodecommands (same source as COMMANDS.md and the SSM document); on SSM only the step name and podIp are sent. `keep` narrows chatty controllers to the metric names the checks need.
                    nr = node_access.na.run_on_node(
                        nd, nodecommands.pod_metrics_cmd(pip, port, st.get("path", "/metrics"), st.get("keep")), timeout=30, id=f"{name}.{sid}.{pname}.node", collector=name, step=f"{name}/{sid}", params={"podIp": pip, "port": port}
                    )
                    if nr.ok and nr.stdout.strip():
                        write_private(out, nr.stdout)
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
            if skipped:
                runs[pname]["skipped"] = skipped
        # No pod behind the target is said with the target and where it came from, so a wrong namespace or selector is readable in the step result (#136)
        res = {
            "ok": any(x["ok"] for x in runs.values()) if runs else False,
            "pods": runs,
            "target": tgt,
            "error": None if runs else f"no pods match {where}; set components.<name>.namespace/selector/metrics_port in config.yaml if the component lives elsewhere",
        }
        if runs and all(x.get("skipped") for x in runs.values()):
            res["skipped"] = "; ".join(f"{k}: {v['skipped']}" for k, v in runs.items())  # every pod skipped: the step says why in section 7-1 instead of counting as a failure
    if ctx.echo:
        n_skip = sum(1 for x in runs.values() if x.get("skipped"))
        ctx.echo(f"    {sum(1 for x in runs.values() if x['ok'])} of {len(runs)} pods /metrics saved ({st['out']})" + (f", {n_skip} skipped: " + "; ".join(x["skipped"] for x in runs.values() if x.get("skipped")) if n_skip else ""))
    return res


def step_component_logs(ctx: StepContext, st: dict) -> dict:
    return run_component_logs_step(st, st["id"], ctx.name, ctx.inv, ctx.context, ctx.kubeconfig, ctx.snap, ctx.log, float(st.get("timeout", 60)), ctx.echo)

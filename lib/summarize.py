"""Summarize.

Reads a snapshot folder and produces `summary.json`, the first file the LLM opens. It is a starting point, not a gate: it gathers numbers
and lists, and records the source file path (`source`) on every item so the LLM can open it directly. It makes no pass/fail judgement;
that is evaluate's job. Log signature aggregation is delegated to the signature catalog.
"""

from __future__ import annotations

import datetime as _dt
import importlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from . import __version__, paths
from .runlog import read_runlog
from .snapshot import items, load_json

WAITING_REASONS = ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError", "CreateContainerError", "InvalidImageName", "RunContainerError")
LABEL_KEEP = ("__name__", "namespace", "pod", "container", "node", "instance", "mountpoint", "qos_class", "reason", "job", "horizontalpodautoscaler", "endpoint", "kind", "phase", "poddisruptionbudget", "service", "deployment")


def _rel(snap: Path, p: Path) -> str:
    return str(p.relative_to(snap))


# ---------- events ----------


def summarize_events(snap: Path) -> dict:
    path = snap / "events.json"
    out: dict = {"source": _rel(snap, path), "count": 0, "by_type": {}, "reasons": [], "top_objects": [], "warning_samples": {}}
    if not path.is_file():
        out["missing"] = "events.json missing. Either collect did not run on this snapshot (discover-only folder) or event collection failed"
        return out
    ev = items(load_json(path))
    out["count"] = len(ev)
    if not ev:
        return out
    by_type = Counter(e.get("type") or "Unknown" for e in ev)
    out["by_type"] = dict(by_type)
    reasons: dict[str, dict] = {}
    objects = Counter()
    samples: dict[str, list] = defaultdict(list)
    for e in ev:
        reason = e.get("reason") or "?"
        typ = e.get("type") or "?"
        inv = e.get("involvedObject") or {}
        obj = f"{inv.get('kind', '?')}/{inv.get('namespace', '') + '/' if inv.get('namespace') else ''}{inv.get('name', '?')}"
        count = e.get("count") or ((e.get("series") or {}).get("count")) or 1
        first = e.get("firstTimestamp") or e.get("eventTime") or (e.get("metadata") or {}).get("creationTimestamp")
        last = e.get("lastTimestamp") or ((e.get("series") or {}).get("lastObservedTime")) or first
        r = reasons.setdefault(reason, {"reason": reason, "type": typ, "events": 0, "occurrences": 0, "first": first, "last": last, "objects": Counter()})
        r["events"] += 1
        r["occurrences"] += int(count) if isinstance(count, (int, float)) else 1
        if first and (r["first"] is None or first < r["first"]):
            r["first"] = first
        if last and (r["last"] is None or last > r["last"]):
            r["last"] = last
        r["objects"][obj] += 1
        objects[obj] += 1
        if typ == "Warning" and len(samples[reason]) < 3:
            samples[reason].append({"object": obj, "message": (e.get("message") or "")[:300], "last": last})
    out["reasons"] = sorted([{**r, "objects_top": [o for o, _ in r["objects"].most_common(5)]} for r in reasons.values()], key=lambda r: (-r["occurrences"], r["reason"]))
    for r in out["reasons"]:
        r.pop("objects", None)
    out["top_objects"] = [{"object": o, "events": n} for o, n in objects.most_common(10)]
    out["warning_samples"] = dict(samples)
    # per-Reason trend across every snapshot in the context folder (lib/events.py)
    try:
        from .events import build_history

        h = build_history(snap.parent, snap)
        out["history"] = {
            "source": "../events-history.json",
            "snapshots": h["snapshot_count"],
            "unique_events": h["unique_events"],
            "tracked_hits": [{k: r[k] for k in ("reason", "type", "severity_hint", "meaning", "occurrences", "events", "first", "last", "trend", "per_snapshot", "objects_top")} for r in h["tracked_hits"]],
            "tracked_silent": h["tracked_silent"],
            "top_warning_reasons": [{k: r[k] for k in ("reason", "occurrences", "trend", "per_snapshot")} for r in h["reasons"] if r["type"] == "Warning"][:15],
        }
    except Exception as e:  # a failure in the trend analysis must not block the whole summary
        out["history"] = {"error": f"{type(e).__name__}: {e}"}
    return out


# ---------- metrics ----------


def _labels(m: dict) -> dict:
    return {k: v for k, v in m.items() if k in LABEL_KEEP}


def summarize_metrics(snap: Path) -> dict:
    out: dict = {}
    mdir = snap / "metrics"
    for f in sorted(mdir.glob("*.json")) if mdir.is_dir() else []:
        d = load_json(f) or {}
        rec: dict = {"source": _rel(snap, f), "why": d.get("why"), "ok": d.get("ok"), "series": d.get("series")}
        if not d.get("ok"):
            rec["error"] = d.get("error")
            out[f.stem] = rec
            continue
        rows = []
        for r in d.get("result", []):
            try:
                val = float(r["value"][1])
            except (KeyError, ValueError, TypeError, IndexError):
                val = None
            rows.append({"labels": _labels(r.get("metric", {})), "value": val})
        nums = [r["value"] for r in rows if r["value"] is not None and r["value"] == r["value"]]
        if nums:
            rec["stats"] = {"min": min(nums), "max": max(nums), "mean": sum(nums) / len(nums), "n": len(nums)}
        rows.sort(key=lambda r: -(r["value"] if r["value"] is not None else float("-inf")))
        rec["top"] = rows[:30]
        rec["truncated"] = max(0, len(rows) - 30)
        out[f.stem] = rec
    # kubectl top
    for name in ("top-nodes.txt", "top-pods.txt"):
        p = mdir / name
        if p.is_file():
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            out[name.replace(".txt", "")] = {"source": _rel(snap, p), "lines": len(lines), "head": lines[:30]}
    return out


# ---------- objects ----------


def _restarts(pod: dict) -> int:
    return sum(int(c.get("restartCount") or 0) for c in ((pod.get("status") or {}).get("containerStatuses") or []))


def summarize_objects(snap: Path, inv: dict | None) -> dict:
    odir = snap / "objects"
    out: dict = {"source": "objects/", "kinds": {}, "kind_count": 0}
    if not odir.is_dir():
        return out
    kinds = {}
    for f in sorted(odir.glob("*.json")):
        d = load_json(f)
        kinds[f.stem] = len(items(d)) if d is not None else None
    out["kinds"] = kinds
    out["kind_count"] = len(kinds)

    pods = items(load_json(odir / "pods.json"))
    per_ns_pods = Counter(p["metadata"]["namespace"] for p in pods)
    deps = items(load_json(odir / "deployments.json"))
    per_ns_deps = Counter(d["metadata"]["namespace"] for d in deps)
    out["namespaces"] = {ns: {"pods": per_ns_pods.get(ns, 0), "deployments": per_ns_deps.get(ns, 0)} for ns in sorted(set(per_ns_pods) | set(per_ns_deps))}

    restarts = sorted(({"namespace": p["metadata"]["namespace"], "pod": p["metadata"]["name"], "restarts": _restarts(p), "node": (p.get("spec") or {}).get("nodeName")} for p in pods), key=lambda r: -r["restarts"])
    out["pods"] = {
        "source": "objects/pods.json",
        "count": len(pods),
        "by_phase": dict(Counter((p.get("status") or {}).get("phase") or "Unknown" for p in pods)),
        "restarts_top": [r for r in restarts[:20] if r["restarts"] > 0],
        "pending": [
            {
                "namespace": p["metadata"]["namespace"],
                "pod": p["metadata"]["name"],
                "reason": next((c.get("reason") for c in ((p.get("status") or {}).get("conditions") or []) if c.get("type") == "PodScheduled" and c.get("status") == "False"), None),
                "message": next((c.get("message") for c in ((p.get("status") or {}).get("conditions") or []) if c.get("type") == "PodScheduled" and c.get("status") == "False"), "")[:200],
            }
            for p in pods
            if (p.get("status") or {}).get("phase") == "Pending"
        ],
        "waiting": [],
        "failed": [],
        "qos": dict(Counter((p.get("status") or {}).get("qosClass") or "?" for p in pods)),
    }
    for p in pods:
        for c in (p.get("status") or {}).get("containerStatuses") or []:
            w = (c.get("state") or {}).get("waiting") or {}
            if w.get("reason") in WAITING_REASONS:
                out["pods"]["waiting"].append({"namespace": p["metadata"]["namespace"], "pod": p["metadata"]["name"], "container": c.get("name"), "reason": w.get("reason"), "message": (w.get("message") or "")[:200]})
        if (p.get("status") or {}).get("phase") == "Failed":
            out["pods"]["failed"].append({"namespace": p["metadata"]["namespace"], "pod": p["metadata"]["name"], "reason": (p.get("status") or {}).get("reason"), "owner": ((p["metadata"].get("ownerReferences") or [{}])[0]).get("kind")})

    out["deployments"] = {
        "source": "objects/deployments.json",
        "count": len(deps),
        "unavailable": [
            {"namespace": d["metadata"]["namespace"], "name": d["metadata"]["name"], "desired": (d.get("spec") or {}).get("replicas"), "available": (d.get("status") or {}).get("availableReplicas", 0)}
            for d in deps
            if ((d.get("spec") or {}).get("replicas") or 0) > ((d.get("status") or {}).get("availableReplicas") or 0)
        ],
        "replicas_1": sum(1 for d in deps if (d.get("spec") or {}).get("replicas") == 1),
        "replicas_0": sum(1 for d in deps if (d.get("spec") or {}).get("replicas") == 0),
    }

    # Services with a selector but no ready endpoints (based on endpoints.json)
    svcs = items(load_json(odir / "services.json"))
    eps_file = odir / "endpoints.json"
    eps = {(e["metadata"]["namespace"], e["metadata"]["name"]): e for e in items(load_json(eps_file))}
    no_ep = []
    for s in svcs if eps_file.is_file() else []:
        spec = s.get("spec") or {}
        if not spec.get("selector") or spec.get("type") == "ExternalName":
            continue
        key = (s["metadata"]["namespace"], s["metadata"]["name"])
        e = eps.get(key)
        ready = sum(len(ss.get("addresses") or []) for ss in ((e or {}).get("subsets") or []))
        if ready == 0:
            no_ep.append({"namespace": key[0], "service": key[1], "selector": spec.get("selector"), "type": spec.get("type")})
    out["services"] = {
        "source": "objects/services.json + objects/endpoints.json",
        "count": len(svcs),
        "by_type": dict(Counter((s.get("spec") or {}).get("type") or "ClusterIP" for s in svcs)),
        "no_ready_endpoints": no_ep if eps_file.is_file() else None,
        **({} if eps_file.is_file() else {"missing": "objects/endpoints.json missing. collect did not run on this snapshot"}),
    }

    nodes = items(load_json(odir / "nodes.json"))
    out["nodes"] = {
        "source": "objects/nodes.json",
        "count": len(nodes),
        "not_ready": [n["metadata"]["name"] for n in nodes if not any(c.get("type") == "Ready" and c.get("status") == "True" for c in ((n.get("status") or {}).get("conditions") or []))],
        "pressure": [
            {"node": n["metadata"]["name"], "condition": c["type"]}
            for n in nodes
            for c in ((n.get("status") or {}).get("conditions") or [])
            if c.get("type") in ("MemoryPressure", "DiskPressure", "PIDPressure") and c.get("status") == "True"
        ],
        "unschedulable": [n["metadata"]["name"] for n in nodes if (n.get("spec") or {}).get("unschedulable")],
    }
    return out


# ---------- external tools / logs (placeholder) ----------

# ---------- generic CRD status.conditions scan (covers operators in general) ----------
BAD_FALSE = {"Ready", "Available", "Healthy", "Synced", "Reconciled", "Succeeded", "Accepted", "Programmed", "Established", "Initialized", "Bound", "Issuing", "Approved", "Installed", "Provisioned", "Registered", "Scheduled"}
BAD_TRUE = {"Degraded", "Stalled", "Failed", "Error", "Unhealthy", "Suspended", "Drifted", "Disrupted", "InsufficientCapacity"}
SKIP_KINDS = {"pods", "nodes", "events", "jobs.batch", "replicasets.apps", "endpointslices.discovery.k8s.io", "leases.coordination.k8s.io"}


def summarize_conditions(snap: Path) -> dict:
    """Scan status.conditions on every object and collect bad patterns (Ready=False, Degraded=True and the like). Operators without a dedicated collector get baseline coverage."""
    odir = snap / "objects"
    out: dict = {"source": "objects/*.json", "scanned_kinds": 0, "scanned_objects": 0, "unhealthy": [], "by_kind": {}}
    if not odir.is_dir():
        return out
    now = _dt.datetime.now(_dt.UTC)
    for f in sorted(odir.glob("*.json")):
        if f.stem in SKIP_KINDS:
            continue
        objs = items(load_json(f))
        has_conditions = False
        for o in objs:
            conds = (o.get("status") or {}).get("conditions") or []
            if not isinstance(conds, list) or not conds:
                continue
            has_conditions = True
            out["scanned_objects"] += 1
            for c in conds:
                if not isinstance(c, dict):
                    continue
                t, st = c.get("type"), str(c.get("status"))
                bad = (t in BAD_FALSE and st == "False") or (t in BAD_TRUE and st == "True")
                if not bad:
                    continue
                lt = c.get("lastTransitionTime")
                try:
                    age_h = round((now - _dt.datetime.fromisoformat(str(lt))).total_seconds() / 3600, 1) if lt else None
                except ValueError:
                    age_h = None
                ns = o["metadata"].get("namespace")
                out["unhealthy"].append({"kind": f.stem, "namespace": ns, "name": o["metadata"]["name"], "condition": t, "status": st, "reason": c.get("reason"), "message": (c.get("message") or "")[:240], "since": lt, "age_hours": age_h})
                out["by_kind"][f.stem] = out["by_kind"].get(f.stem, 0) + 1
        if has_conditions:
            out["scanned_kinds"] += 1
    out["unhealthy"].sort(key=lambda r: -(r["age_hours"] or 0))
    out["count"] = len(out["unhealthy"])
    return out


# ---------- admission webhooks (Jetstack self-lockout) ----------


def summarize_webhooks(snap: Path) -> dict:
    """Each webhook of every ValidatingWebhookConfiguration and MutatingWebhookConfiguration: failurePolicy, ready endpoint count of its service, timeout, whether it targets its own namespace."""
    odir = snap / "objects"
    eps = {(e["metadata"]["namespace"], e["metadata"]["name"]): e for e in items(load_json(odir / "endpoints.json"))}
    svc_ns_of = {}
    for sv in items(load_json(odir / "services.json")):
        svc_ns_of[(sv["metadata"]["namespace"], sv["metadata"]["name"])] = True
    rows = []
    for stem, kind in (("validatingwebhookconfigurations.admissionregistration.k8s.io", "Validating"), ("mutatingwebhookconfigurations.admissionregistration.k8s.io", "Mutating")):
        for cfg in items(load_json(odir / f"{stem}.json")):
            for w in cfg.get("webhooks") or []:
                cc = w.get("clientConfig") or {}
                svc = cc.get("service") or {}
                sns, sname = svc.get("namespace"), svc.get("name")
                ready = None
                if sns and sname:
                    e = eps.get((sns, sname))
                    ready = sum(len(ss.get("addresses") or []) for ss in ((e or {}).get("subsets") or [])) if e is not None else 0
                rules = w.get("rules") or []
                resources = sorted({r for rule in rules for r in (rule.get("resources") or [])})
                ns_sel = w.get("namespaceSelector") or {}
                # self-lockout: the webhook intercepts pod/deployment creation in its own namespace (the namespace selector does not exclude it) and failurePolicy=Fail
                excludes_self = False
                restricts = bool(ns_sel.get("matchLabels"))  # only labelled namespaces are targeted -> safe as long as its own namespace lacks that label (LLM verifies)
                for ex in ns_sel.get("matchExpressions") or []:
                    op = ex.get("operator")
                    if ex.get("key") in ("kubernetes.io/metadata.name", "name") and op == "NotIn" and sns in (ex.get("values") or []):
                        excludes_self = True
                    if op in ("In", "Exists"):
                        restricts = True
                obj_sel = w.get("objectSelector") or {}
                if obj_sel.get("matchLabels") or obj_sel.get("matchExpressions"):
                    restricts = True  # only objects with a specific label are targeted (e.g. runner pods). The webhook's own pods usually lack that label
                targets_pods = any(r in ("pods", "*", "deployments", "replicasets") for r in resources)
                # self-lockout risk = Fail policy + pod-like targets + namespace selector that is empty or only excludes others, so its own namespace is caught too.
                # If the selector narrows targets with In/Exists/matchLabels it is not treated as a risk; the report only notes "verify selector".
                self_lock_risk = bool(sns) and w.get("failurePolicy") == "Fail" and targets_pods and not excludes_self and not restricts
                rows.append(
                    {
                        "kind": kind,
                        "config": cfg["metadata"]["name"],
                        "webhook": w.get("name"),
                        "failure_policy": w.get("failurePolicy"),
                        "timeout_seconds": w.get("timeoutSeconds"),
                        "service": f"{sns}/{sname}" if sns else (cc.get("url") or "?"),
                        "ready_endpoints": ready,
                        "resources": resources[:8],
                        "namespace_selector": ns_sel or None,
                        "object_selector": obj_sel or None,
                        "self_lock_risk": self_lock_risk,
                        "side_effects": w.get("sideEffects"),
                    }
                )
    return {
        "source": "objects/*webhookconfigurations*.json + objects/endpoints.json",
        "count": len(rows),
        "webhooks": rows,
        "no_endpoints": [r for r in rows if r["ready_endpoints"] == 0],
        "fail_policy": sum(1 for r in rows if r["failure_policy"] == "Fail"),
        "self_lock_risk": [r for r in rows if r["self_lock_risk"]],
    }


def summarize_recent_changes(snap: Path, hours: int = 24) -> dict:
    """`quick` scope: workloads changed in the last N hours. Defined by the status.conditions lastUpdateTime of Deployments, StatefulSets and DaemonSets
    (the Progressing condition is refreshed on every rollout), or by the targets of ScalingReplicaSet/SuccessfulCreate events. generation is recorded too."""
    odir = snap / "objects"
    since = _dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=hours)
    changed: list[dict] = []
    for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet")):
        for o in items(load_json(odir / f"{stem}.json")):
            latest = None
            for cnd in (o.get("status") or {}).get("conditions") or []:
                t = cnd.get("lastUpdateTime") or cnd.get("lastTransitionTime")
                if t:
                    try:
                        dt = _dt.datetime.fromisoformat(t)
                    except ValueError:
                        continue
                    if latest is None or dt > latest:
                        latest = dt
            if latest and latest >= since:
                changed.append(
                    {
                        "kind": kind,
                        "namespace": o["metadata"]["namespace"],
                        "name": o["metadata"]["name"],
                        "last_update": latest.isoformat(timespec="seconds"),
                        "generation": o["metadata"].get("generation"),
                        "observed_generation": (o.get("status") or {}).get("observedGeneration"),
                    }
                )
    ev_targets = []
    for e in items(load_json(snap / "events.json")):
        if e.get("reason") in ("ScalingReplicaSet", "SuccessfulCreate", "Killing", "Scheduled"):
            t = e.get("lastTimestamp") or e.get("eventTime") or ((e.get("series") or {}).get("lastObservedTime"))
            try:
                dt = _dt.datetime.fromisoformat(str(t)) if t else None
            except ValueError:
                dt = None
            if dt and dt >= since:
                inv = e.get("involvedObject") or {}
                ev_targets.append(f"{inv.get('kind')}/{inv.get('namespace')}/{inv.get('name')}")
    changed.sort(key=lambda r: r["last_update"], reverse=True)
    return {
        "source": "objects/deployments.json, objects/statefulsets.json, objects/daemonsets.json, events.json",
        "hours": hours,
        "workloads": changed,
        "namespaces": sorted({c["namespace"] for c in changed}),
        "event_targets": sorted(set(ev_targets))[:50],
        "count": len(changed),
    }


def _collection_meta(snap: Path) -> dict:
    """Mode of this snapshot and the steps the mode skipped, so the report can say "not collected in daily mode" instead of treating the gaps as defects."""
    cr = load_json(snap / "collect-result.json") or {}
    s = cr.get("_summary") or {}
    return {"mode": paths.snapshot_mode(snap), "mode_skipped_steps": s.get("mode_skipped") or [], "failed_steps": s.get("failed") or [], "seconds_total": s.get("seconds_total")}


def summarize_tools(snap: Path) -> dict:
    tdir = snap / "tools"
    if not tdir.is_dir():
        return {"source": "tools/", "note": "no external tool output (KRR runs in the core krr step; Polaris and Pluto in the hygiene tools step)", "files": []}
    return {"source": "tools/", "files": [_rel(snap, f) for f in sorted(tdir.glob("*"))]}


def summarize_logs(snap: Path, inv: dict | None = None) -> dict:
    try:
        from .logs import analyze

        return analyze(snap, inv)
    except Exception as e:  # a failure in log analysis must not block the whole summary
        return {"error": f"{type(e).__name__}: {e}", "signatures": [], "unclassified_errors": []}


# ---------- run.log ----------


def summarize_run(snap: Path) -> dict:
    recs = read_runlog(snap / "run.log")
    cmds = [r for r in recs if r.get("kind") == "command"]
    skips = [r for r in recs if r.get("kind") == "skip"]
    failed = [r for r in cmds if (r.get("code") not in (0, None)) or r.get("timed_out") or (r.get("code") is None and r.get("error"))]
    return {
        "source": "run.log",
        "commands": len(cmds),
        "failed": [{"id": r.get("id"), "collector": r.get("collector"), "error": (r.get("error") or "")[:200]} for r in failed],
        "skipped": [{"id": r.get("id"), "reason": r.get("reason")} for r in skips],
        "seconds_total": round(sum(float(r.get("seconds") or 0) for r in cmds), 1),
        "by_collector": dict(Counter(r.get("collector") or "-" for r in cmds)),
    }


def _component(module: str, snap: Path, inv: dict | None, *extra, on_error: dict | None = None) -> dict:
    """Run `lib/<module>.py` analyze(snap, inv, *extra). Every section module exposes the same entry point; a failure in one must not block the whole
    summary, so it is recorded as {"error": ...} (plus `on_error` keys, e.g. k3s keeps `present: None`) and summarize goes on."""
    try:
        mod = importlib.import_module(f".{module}", __package__)
        return mod.analyze(snap, inv, *extra)
    except Exception as e:
        return {**(on_error or {}), "error": f"{type(e).__name__}: {e}"}


# Optional component sections, in summary.json key order. Each row: (summary key, lib module, collectors that enable it, section passed as the
# analyze() third argument or None). A component whose collector is not in inventory.collectors_enabled gets {"present": False} so checks can
# still address the key. `ecr` additionally turns on when aws/ecr-repositories.json exists (older snapshots collected it without the collector).
COMPONENT_SECTIONS: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("vpccni", "vpccni", ("vpc-cni",), None),
    ("coredns", "coredns", ("coredns",), None),
    ("kubeproxy", "kubeproxy", ("kube-proxy",), None),
    ("ebscsi", "ebscsi", ("ebs-csi",), None),
    ("albctl", "albctl", ("alb-controller",), "traffic"),
    ("karpenterctl", "karpenterctl", ("karpenter",), "scaling"),
    ("kedactl", "kedactl", ("keda",), "scaling"),
    ("esoctl", "esoctl", ("external-secrets",), None),
    ("argocdctl", "argocdctl", ("argocd",), None),
    ("flannel", "flannelctl", ("flannel",), "k3s"),
    ("local_path", "localpath", ("local-path-provisioner",), "k3s"),
    ("metallb", "metallbctl", ("metallb",), "k3s"),
    ("certmanager", "certmanager", ("cert-manager",), None),
    ("eksplatform", "eksplatform", ("eks-platform",), None),
    ("ecr", "ecr", ("ecr",), None),
    ("stackhealth", "stackhealth", ("prometheus", "alertmanager", "grafana", "loki"), None),
)


def _component_enabled(key: str, enabled_by: tuple[str, ...], snap: Path, collectors_enabled: list[str]) -> bool:
    if any(c in collectors_enabled for c in enabled_by):
        return True
    return key == "ecr" and (snap / "aws" / "ecr-repositories.json").exists()


def summarize(snap: Path, echo=print) -> dict:
    inv = load_json(snap / "inventory.json")
    s = {
        "kubegap": __version__,
        "snapshot": str(snap),
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "inventory": None,
        "events": summarize_events(snap),
        "metrics": summarize_metrics(snap),
        "objects": summarize_objects(snap, inv),
        "conditions": summarize_conditions(snap),
        "webhooks": summarize_webhooks(snap),
        "observability": _component("observability", snap, inv),
        "controlplane": _component("controlplane", snap, inv),
        "nodeos": _component("nodeos", snap, inv),
        "k3s": _component("k3s", snap, inv, on_error={"present": None}),
        "recent_changes": summarize_recent_changes(snap),
        "logs": summarize_logs(snap, inv),
        "tools": summarize_tools(snap),
        "resources": _component("resources", snap, inv),
        "scaling": _component("scaling", snap, inv),
        "traffic": _component("traffic", snap, inv),
        "resilience": _component("resilience", snap, inv),
        "storage": _component("storage", snap, inv),
        "run": summarize_run(snap),
        "collection": _collection_meta(snap),
    }
    s["hygiene"] = _component("hygiene", snap, inv, s.get("webhooks"))
    s["security"] = _component("security", snap, inv, s.get("k3s"))
    s["tenancy"] = _component("tenancy", snap, inv, s.get("security"))
    collectors_enabled = (inv or {}).get("collectors_enabled") or []
    for key, module, enabled_by, depends_on in COMPONENT_SECTIONS:
        if not _component_enabled(key, enabled_by, snap, collectors_enabled):
            s[key] = {"present": False}
        elif depends_on:
            s[key] = _component(module, snap, inv, s.get(depends_on))
        else:
            s[key] = _component(module, snap, inv)
    s["cost"] = _component("cost", snap, inv, s)
    if inv:
        s["inventory"] = {
            "source": "inventory.json",
            "context": inv.get("context"),
            "taken_at": inv.get("taken_at"),
            "platform": inv["cluster"]["platform"],
            "server_version": inv["cluster"].get("server_version"),
            "profile": inv["profile"]["name"],
            "node_access": inv["node_access"]["method"],
            "nodes": inv["nodes"]["count"],
            "namespaces": inv["namespaces"]["count"],
            "crds": inv["crds"]["count"],
            "components_present": inv.get("components_present"),
            "missing_families": inv.get("missing_families"),
            "stores": {k: ({"ok": v.get("ok"), "version": v.get("version"), "retention": v.get("retention")}) for k, v in (inv.get("stores") or {}).items()},
            "eks": ({k: inv["cluster"]["eks"].get(k) for k in ("version", "support_type", "control_plane_logging_off", "public_access_cidrs", "secrets_encryption", "addons")} if inv["cluster"].get("eks") else None),
            "ssm_unregistered": [x["node"] for x in inv["node_access"].get("ssm_unregistered", [])],
        }
    (snap / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if echo:
        e, o, m, r = s["events"], s["objects"], s["metrics"], s["run"]
        if e.get("missing"):
            echo(f"events: {e['missing']}")
        else:
            echo(f"events {e['count']} (Warning {e['by_type'].get('Warning', 0)}), {len(e['reasons'])} distinct Reasons. top: " + ", ".join(f"{x['reason']}x{x['occurrences']}" for x in e["reasons"][:5]))
        echo(
            f"objects {o['kind_count']} kinds, pods {o['pods']['count']}: top restarts {len(o['pods']['restarts_top'])}, Pending {len(o['pods']['pending'])}, "
            f"waiting reasons {len(o['pods']['waiting'])}, Failed {len(o['pods']['failed'])}; Deployment unavailable {len(o['deployments']['unavailable'])}, "
            f"replicas=1 {o['deployments']['replicas_1']}; Services without ready endpoints {len(o['services']['no_ready_endpoints']) if o['services']['no_ready_endpoints'] is not None else '(no endpoints)'}"
        )
        c, w = s["conditions"], s["webhooks"]
        echo(
            f"CRD conditions: {c['count']} unhealthy of {c['scanned_objects']} objects ({c['scanned_kinds']} kinds) {dict(list(c['by_kind'].items())[:6])}; "
            f"webhooks {w['count']} (failurePolicy Fail {w['fail_policy']}, zero endpoints {len(w['no_endpoints'])}, self-lockout risk {len(w['self_lock_risk'])})"
        )
        ob = s["observability"]
        if "error" in ob:
            echo(f"observability: analysis failed {ob['error']}")
        else:
            echo(
                f"observability: alerting rules {ob['rules']['alerting']} (symptom {ob['rules']['by_class'].get('symptom', 0)}, cause {ob['rules']['by_class'].get('cause', 0)}, app {ob['rules']['by_class'].get('app', 0)}), "
                f"never fired in 15d {ob['alerts']['never_fired_count']}, firing all of 7d {len(ob['alerts']['always_firing_7d'])}, failure modes covered {ob['failure_modes']['covered_count']}/{ob['failure_modes']['applicable_count']}, "
                f"default receiver {ob['alertmanager'].get('default_receiver')}{' (null!)' if ob['alertmanager'].get('default_is_null') else ''}, silences {len(ob['alertmanager'].get('silences_active', []))}, "
                f"ingresses without latency/traffic/error metrics {len(ob['golden_signals']['missing_lte'])} of {ob['golden_signals']['ingresses']}, targets down {len(ob['targets']['down'])}"
            )
        cp = s["controlplane"]
        if "error" in cp:
            echo(f"control plane: analysis failed {cp['error']}")
        elif cp.get("available"):
            am_ = cp["apiserver_metrics"]
            echo(
                f"control plane ({cp['platform']}): unschedulable 24h {cp.get('scheduler', {}).get('unschedulable_total_24h')}, "
                f"apiserver 429 {am_['rate_429']} /s, 5xx {am_['rate_5xx']} /s, p99 max {am_['p99_max']}, WATCH {am_['watch_count']}"
                + (
                    f", log lines 24h {sum(cp['log_volume_24h'].values()):,}, slow traces {cp['apiserver']['slow_traces_total']}"
                    if cp["platform"] == "eks"
                    else f", etcd slow apply {cp['etcd']['apply_took_too_long']}, slow request {cp['etcd']['request_stats_slow']} (max {cp['etcd']['max_ms']:.0f}ms)"
                )
            )
        else:
            echo(f"control plane: no logs ({cp.get('note') or cp.get('source')})")
        echo(
            f"metric queries {sum(1 for v in m.values() if 'ok' in v)} (failed {sum(1 for v in m.values() if v.get('ok') is False)}), commands {r['commands']} (failed {len(r['failed'])}, skipped {len(r['skipped'])}), total {r['seconds_total']}s"
        )
        echo(f"saved: {snap / 'summary.json'}")
    return s

"""Resilience area summary.

Inputs: objects/deployments, statefulsets, daemonsets, pods, nodes, poddisruptionbudgets, priorityclasses, cronjobs, jobs, persistentvolumeclaims, persistentvolumes, services, namespaces,
events.json (Preempted, Unhealthy), inventory (prod_like, karpenter presence, platform).

Output: the `resilience` section of summary.json: probes (per-workload probe kinds, paths, suspicion flags), pdbs (zero allowed disruptions, orphans), graceful (preStop, grace, shell PID1, readiness gate), placement (replica spread over nodes/AZs, spread declarations),
single_node (nodeSelector, nodeName, hostPath pinning), az_volumes (AZ pinned by EBS PVs and node count in that AZ), n_plus_one (allocatable minus the largest node vs the request sum, pods that cannot fit elsewhere),
restarts (top container restarts and causes), cronjobs (policy, last success, active Job count), jobs (failed/completed totals), priority (PriorityClass, prod vs non-prod priority, Preempted). Shape documented in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .controlplane import workload_of
from .snapshot import load_json, objects

SUSPECT_LIVENESS_RE = re.compile(r"(db|database|mysql|postgres|redis|mongo|kafka|ready|readiness|deps|dependenc|upstream|downstream|elastic|full=true)", re.IGNORECASE)
DB_SELF_PROBE_RE = re.compile(
    r"(pg_isready|mysqladmin|mysql .*-e|redis-cli|valkey-cli|mongosh|mongo .*ping|cqlsh|nodetool|clickhouse-client|rabbitmq-diagnostics|rabbitmqctl|etcdctl endpoint|_cluster/health|minio.*health)", re.IGNORECASE
)  # standard probes that check the DB's own response — not external dependencies (seen: 6 mysql false positives)
DB_HINT_RE = re.compile(r"(postgres|pgsql|mysql|mariadb|mongo|redis|valkey|elastic|opensearch|kafka|rabbit|clickhouse|qdrant|milvus|minio|etcd|cassandra|neo4j|influx|timescale)", re.IGNORECASE)
SHELLS = ("sh", "/bin/sh", "bash", "/bin/bash", "/usr/bin/bash", "ash", "/bin/ash")


def _ts(s):
    if not s:
        return None
    try:
        return _dt.datetime.fromisoformat(str(s))
    except ValueError:
        return None


def _q(v) -> float:
    """Kubernetes quantity → CPU cores or bytes."""
    if v is None:
        return 0.0
    s = str(v)
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "k": 1e3}
    if s.endswith("m"):
        return float(s[:-1]) / 1000
    for u, mul in units.items():
        if s.endswith(u):
            return float(s[: -len(u)]) * mul
    try:
        return float(s)
    except ValueError:
        return 0.0


def _match(sel: dict | None, labels: dict) -> bool:
    if not sel:
        return False
    ml = sel.get("matchLabels") if ("matchLabels" in sel or "matchExpressions" in sel) else sel
    if any(labels.get(k) != v for k, v in (ml or {}).items()):
        return False
    for e in sel.get("matchExpressions") or []:
        k, op, vals = e.get("key"), e.get("operator"), e.get("values") or []
        if op == "In" and labels.get(k) not in vals:
            return False
        if op == "NotIn" and labels.get(k) in vals:
            return False
        if op == "Exists" and k not in labels:
            return False
        if op == "DoesNotExist" and k in labels:
            return False
    return True


def _cron_interval_h(expr: str | None) -> float | None:
    """Approximate run interval (hours) from a cron expression. None if unknown."""
    if not expr:
        return None
    f = expr.split()
    if len(f) != 5:
        return None
    minute, hour, dom, _mon, dow = f
    if minute == "*" and hour == "*":
        return 1 / 60
    m = re.match(r"\*/(\d+)$", minute)
    if m:
        return int(m.group(1)) / 60  # even with an hour range (7-15), this is the interval within that window
    m = re.match(r"\*/(\d+)$", hour)
    if m:
        return float(m.group(1))
    if hour == "*" and minute.isdigit():
        return 1.0
    if hour.isdigit() or re.match(r"^\d+(,\d+)*$", hour):
        n = len(hour.split(","))
        if dom == "*" and dow == "*":
            return 24.0 / n
        if dow != "*":
            days = len(dow.split(",")) if "-" not in dow else (int(dow.split("-")[1]) - int(dow.split("-")[0]) + 1)
            return 24.0 * 7 / max(days * n, 1)
        return 24.0 * 30 / n
    return None


class _Ctx:
    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        inv = inv or {}
        self.prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
        self.platform = (inv.get("cluster") or {}).get("platform")
        self.karpenter = bool(((inv.get("components") or {}).get("karpenter") or {}).get("present")) or "karpenter" in (inv.get("components_present") or [])
        self.pods = objects(snap, "pods")
        self.nodes = objects(snap, "nodes")
        self.services = objects(snap, "services")
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet")):
            for o in objects(snap, stem):
                self.workloads.append((kind, o))
        self.node_zone = {n["metadata"]["name"]: (n["metadata"].get("labels") or {}).get("topology.kubernetes.io/zone") for n in self.nodes}
        self.rs_owner = {}
        for rs in objects(snap, "replicasets.apps"):
            own = next((o for o in rs["metadata"].get("ownerReferences") or []), None)
            if own:
                self.rs_owner[(rs["metadata"]["namespace"], rs["metadata"]["name"])] = (own.get("kind"), own.get("name"))

    def wl_key(self, kind, o):
        return f"{o['metadata']['namespace']}/{kind.lower()}/{o['metadata']['name']}"

    def tpl(self, o):
        return ((o.get("spec") or {}).get("template") or {}).get("spec") or {}

    def tpl_labels(self, o):
        return (((o.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}

    def pods_of(self, kind, o) -> list:
        ns, name = o["metadata"]["namespace"], o["metadata"]["name"]
        out = []
        for p in self.pods:
            if p["metadata"]["namespace"] != ns or p["status"].get("phase") not in ("Running", "Pending"):
                continue
            own = next((x for x in p["metadata"].get("ownerReferences") or []), None)
            if not own:
                continue
            if kind == "Deployment" and own.get("kind") == "ReplicaSet":
                if self.rs_owner.get((ns, own.get("name"))) == ("Deployment", name) or own.get("name", "").rsplit("-", 1)[0] == name:
                    out.append(p)
            elif own.get("kind") == kind and own.get("name") == name:
                out.append(p)
        return out

    def serves(self, o) -> bool:
        labels = self.tpl_labels(o)
        if not any((c.get("ports") or []) for c in self.tpl(o).get("containers") or []):
            return False
        return any(s["metadata"]["namespace"] == o["metadata"]["namespace"] and (s.get("spec") or {}).get("selector") and all(labels.get(k) == v for k, v in s["spec"]["selector"].items()) for s in self.services)


def _expr_match(e: dict, labels: dict) -> bool:
    k, op, vals = e.get("key"), e.get("operator"), e.get("values") or []
    has = k in labels
    if op == "In":
        return has and labels[k] in vals
    if op == "NotIn":
        return not has or labels[k] not in vals
    if op == "Exists":
        return has
    if op == "DoesNotExist":
        return not has
    if op == "Gt":
        try:
            return has and float(labels[k]) > float(vals[0])
        except (ValueError, IndexError):
            return False
    if op == "Lt":
        try:
            return has and float(labels[k]) < float(vals[0])
        except (ValueError, IndexError):
            return False
    return True


def _tolerates(tolerations: list, taints: list) -> bool:
    for t in taints or []:
        if t.get("effect") not in ("NoSchedule", "NoExecute"):
            continue
        ok = False
        for tol in tolerations or []:
            if tol.get("effect") and tol["effect"] != t.get("effect"):
                continue
            if tol.get("operator") == "Exists":
                if not tol.get("key") or tol["key"] == t.get("key"):
                    ok = True
                    break
            elif tol.get("key") == t.get("key") and (tol.get("value") or "") == (t.get("value") or ""):
                ok = True
                break
        if not ok:
            return False
    return True


def eligible_nodes(pod_spec: dict, nodes: list[dict], *, ignore_node_name: bool = False) -> list[str]:
    """Node names this pod can land on, considering only nodeName, nodeSelector, required nodeAffinity and taints/tolerations (inter-pod affinity and resources excluded).
    A real pod spec carries the scheduler-filled nodeName, so pass ignore_node_name=True when computing from pods (only the template's nodeName is a constraint)."""
    out = []
    if pod_spec.get("nodeName") and not ignore_node_name:
        return [pod_spec["nodeName"]]
    sel = pod_spec.get("nodeSelector") or {}
    req = (((pod_spec.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []
    for n in nodes:
        if (n.get("spec") or {}).get("unschedulable"):
            continue
        labels = n["metadata"].get("labels") or {}
        if any(labels.get(k) != v for k, v in sel.items()):
            continue
        if req and not any(
            all(_expr_match(e, labels) for e in (t.get("matchExpressions") or [])) and all((labels.get(f.get("key")) in (f.get("values") or [])) if f.get("operator") == "In" else True for f in (t.get("matchFields") or [])) for t in req
        ):
            continue
        if not _tolerates(pod_spec.get("tolerations") or [], (n.get("spec") or {}).get("taints") or []):
            continue
        out.append(n["metadata"]["name"])
    return out


def _probes(cx: _Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        for c in cx.tpl(o).get("containers") or []:
            flags = []
            probes = {}
            for pk in ("livenessProbe", "readinessProbe", "startupProbe"):
                pr = c.get(pk)
                if not pr:
                    probes[pk] = None
                    continue
                typ = next((t for t in ("httpGet", "tcpSocket", "exec", "grpc") if t in pr), "?")
                path = (pr.get("httpGet") or {}).get("path") or (" ".join((pr.get("exec") or {}).get("command") or []) if typ == "exec" else None)
                probes[pk] = {
                    "type": typ,
                    "path": path,
                    "port": (pr.get("httpGet") or pr.get("tcpSocket") or {}).get("port"),
                    "timeout_s": pr.get("timeoutSeconds", 1),
                    "period_s": pr.get("periodSeconds", 10),
                    "failure_threshold": pr.get("failureThreshold", 3),
                    "initial_delay_s": pr.get("initialDelaySeconds", 0),
                }
            lv, rd, st = probes["livenessProbe"], probes["readinessProbe"], probes["startupProbe"]
            img_repo = (c.get("image") or "").split("@")[0].rsplit("/", 1)[-1].split(":")[0]  # tag excluded — umami:postgresql-latest was caught as a DB
            db_like = bool(DB_HINT_RE.search(f"{c.get('name')} {img_repo} {o['metadata']['name']}")) and not re.search(r"exporter|operator|controller|proxy|ui|insight", f"{c.get('name')} {o['metadata']['name']}", re.IGNORECASE)
            self_probe = bool(lv and lv["type"] == "exec" and lv["path"] and DB_SELF_PROBE_RE.search(str(lv["path"])))
            if lv and lv["path"] and SUSPECT_LIVENESS_RE.search(str(lv["path"])) and not (db_like and self_probe):
                flags.append(f"liveness path looks like a dependency/ready check (suspect: {lv['path']})")
            if lv and rd and lv["type"] == "httpGet" and rd["type"] == "httpGet" and lv["path"] == rd["path"]:
                flags.append(f"liveness and readiness share the same path ({lv['path']}) — a dependency outage becomes a restart loop")
            if lv and lv["type"] == "exec":
                flags.append("liveness exec (forks a process)")
            if rd and rd["type"] == "exec":
                flags.append("readiness exec (forks a process every period, node load)")
            for pk, pr in (("liveness", lv), ("readiness", rd)):
                if pr and pr["type"] == "exec" and pr["timeout_s"] <= 1:
                    flags.append(f"{pk} exec timeout 1s (false failures when the node is busy)")
            if lv and lv["failure_threshold"] * lv["period_s"] <= 15 and not st:
                flags.append(f"liveness failure window {lv['failure_threshold'] * lv['period_s']}s (no startupProbe) — a short stall restarts the container")
            if db_like and lv and lv["timeout_s"] <= 1:
                flags.append(f"DB container liveness timeout {lv['timeout_s']}s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)")
            rows.append(
                {
                    "workload": cx.wl_key(kind, o),
                    "kind": kind,
                    "namespace": ns,
                    "name": o["metadata"]["name"],
                    "container": c.get("name"),
                    "prod": ns in cx.prod,
                    "serves_traffic": cx.serves(o),
                    "liveness": lv,
                    "readiness": rd,
                    "startup": st,
                    "flags": flags,
                    "dependency_liveness": any("suspect" in f for f in flags),
                    "same_path": any("same path" in f for f in flags),
                    "suspect_liveness": any("suspect" in f or "same path" in f for f in flags),
                    "exec_probe": any("exec" in f for f in flags),
                    "aggressive_liveness": any("failure window" in f for f in flags),
                    "db_like": db_like,
                    "db_probe_timeout_1s": any("DB container liveness timeout" in f for f in flags),
                }
            )
    return {
        "containers": len(rows),
        "rows": [r for r in rows if r["flags"]],
        "all": rows,
        "counts": {
            "suspect_liveness": sum(r["suspect_liveness"] for r in rows),
            "dependency_liveness": sum(r["dependency_liveness"] for r in rows),
            "same_path": sum(r["same_path"] for r in rows),
            "exec_probe": sum(r["exec_probe"] for r in rows),
            "aggressive_liveness": sum(r["aggressive_liveness"] for r in rows),
            "db_probe_timeout_1s": sum(r["db_probe_timeout_1s"] for r in rows),
            "no_liveness": sum(1 for r in rows if not r["liveness"]),
            "no_readiness": sum(1 for r in rows if not r["readiness"]),
            "with_startup": sum(1 for r in rows if r["startup"]),
        },
    }


def _pdbs(cx: _Ctx) -> dict:
    rows = []
    for pdb in objects(cx.snap, "poddisruptionbudgets.policy"):
        md, sp, st = pdb["metadata"], pdb.get("spec") or {}, pdb.get("status") or {}
        ns = md["namespace"]
        covered = [cx.wl_key(k, o) for k, o in cx.workloads if o["metadata"]["namespace"] == ns and _match(sp.get("selector"), cx.tpl_labels(o))]
        replicas = [((o.get("spec") or {}).get("replicas")) for k, o in cx.workloads if cx.wl_key(k, o) in covered and k != "DaemonSet"]
        rep = max([r for r in replicas if r is not None], default=None)
        mn, mx = sp.get("minAvailable"), sp.get("maxUnavailable")
        never = False
        if rep is not None:
            if isinstance(mn, int) and mn >= rep:
                never = True
            if isinstance(mn, str) and mn.endswith("%") and int(mn[:-1]) >= 100:
                never = True
            if mx == 0 or mx == "0%":
                never = True
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "min_available": mn,
                "max_unavailable": mx,
                "selector": sp.get("selector"),
                "covered_workloads": covered,
                "covered_replicas": rep,
                "disruptions_allowed": st.get("disruptionsAllowed"),
                "current_healthy": st.get("currentHealthy"),
                "desired_healthy": st.get("desiredHealthy"),
                "expected_pods": st.get("expectedPods"),
                "blocks_drain": (st.get("disruptionsAllowed") == 0 and (st.get("expectedPods") or 0) > 0),
                "never_allows": never,
                "orphan": not covered and (st.get("expectedPods") or 0) == 0,
                "prod": ns in cx.prod,
            }
        )
    return {"count": len(rows), "rows": rows, "blocking": [r["target"] for r in rows if r["blocks_drain"]], "never_allows": [r["target"] for r in rows if r["never_allows"]], "orphans": [r["target"] for r in rows if r["orphan"]]}


def _graceful(cx: _Ctx) -> dict:
    ns_gate = {n["metadata"]["name"]: (n["metadata"].get("labels") or {}).get("elbv2.k8s.aws/pod-readiness-gate-inject") for n in objects(cx.snap, "namespaces")}
    pvc_modes = {(c["metadata"]["namespace"], c["metadata"]["name"]): ((c.get("spec") or {}).get("accessModes") or []) for c in objects(cx.snap, "persistentvolumeclaims")}
    rows = []
    for kind, o in cx.workloads:
        if kind == "DaemonSet":
            continue
        tpl = cx.tpl(o)
        serving = cx.serves(o)
        if not serving:
            continue
        conts = tpl.get("containers") or []
        shell = [c["name"] for c in conts if (c.get("command") or [None])[0] in SHELLS and "-c" in (c.get("command") or []) + (c.get("args") or [])]
        pvc_names = [v["persistentVolumeClaim"]["claimName"] for v in tpl.get("volumes") or [] if v.get("persistentVolumeClaim")]
        rwo = [c for c in pvc_names if "ReadWriteMany" not in (pvc_modes.get((o["metadata"]["namespace"], c)) or ["ReadWriteOnce"])]
        ext = sorted({k for c in conts for k in ((c.get("resources") or {}).get("limits") or {}) if "/" in k and not k.startswith("hugepages")})
        reasons = ([f"RWO PVC {rwo[:2]}"] if rwo else []) + ([f"extended resource {ext}"] if ext else [])
        rows.append(
            {
                "workload": cx.wl_key(kind, o),
                "namespace": o["metadata"]["namespace"],
                "prod": o["metadata"]["namespace"] in cx.prod,
                "recreate_justified": bool(reasons),
                "recreate_reason": reasons,
                "prestop": any((c.get("lifecycle") or {}).get("preStop") for c in conts),
                "grace_s": tpl.get("terminationGracePeriodSeconds", 30),
                "shell_pid1_containers": shell,
                "readiness_gate": ns_gate.get(o["metadata"]["namespace"]),
                "replicas": (o.get("spec") or {}).get("replicas"),
                "strategy": ((o.get("spec") or {}).get("strategy") or {}).get("type") or ((o.get("spec") or {}).get("updateStrategy") or {}).get("type"),
                "max_unavailable": (((o.get("spec") or {}).get("strategy") or {}).get("rollingUpdate") or {}).get("maxUnavailable"),
            }
        )
    return {
        "serving_workloads": len(rows),
        "rows": rows,
        "shell_pid1_no_prestop": [r["workload"] for r in rows if r["shell_pid1_containers"] and not r["prestop"]],
        "recreate_strategy": [r["workload"] for r in rows if r["strategy"] == "Recreate"],
        "recreate_unjustified": [r["workload"] for r in rows if r["strategy"] == "Recreate" and not r["recreate_justified"]],
        "readiness_gate_namespaces": sorted(n for n, v in ns_gate.items() if v == "enabled"),
    }


def _placement(cx: _Ctx) -> dict:
    rows = []
    zones_total = len({z for z in cx.node_zone.values() if z})
    for kind, o in cx.workloads:
        if kind == "DaemonSet":
            continue
        rep = (o.get("spec") or {}).get("replicas") or 0
        if rep < 2:
            continue
        pods = [p for p in cx.pods_of(kind, o) if p["status"].get("phase") == "Running"]
        nodes = Counter(p["spec"].get("nodeName") for p in pods)
        zones = Counter(cx.node_zone.get(p["spec"].get("nodeName")) for p in pods)
        tpl = cx.tpl(o)
        tsc = tpl.get("topologySpreadConstraints") or []
        anti = (tpl.get("affinity") or {}).get("podAntiAffinity") or {}
        hard_anti = bool(anti.get("requiredDuringSchedulingIgnoredDuringExecution"))
        soft_anti = bool(anti.get("preferredDuringSchedulingIgnoredDuringExecution"))
        elig = eligible_nodes(tpl, cx.nodes)
        rows.append(
            {
                "workload": cx.wl_key(kind, o),
                "namespace": o["metadata"]["namespace"],
                "prod": o["metadata"]["namespace"] in cx.prod,
                "replicas": rep,
                "running": len(pods),
                "nodes": dict(nodes),
                "zones": dict(zones),
                "all_same_node": len(pods) >= 2 and len(nodes) == 1,
                "all_same_zone": zones_total > 1 and len(pods) >= 2 and len([z for z in zones if z]) == 1,
                "eligible_nodes": len(elig),
                "single_eligible_node": len(elig) == 1 and len(cx.nodes) > 1,
                "spread_declared": bool(tsc) or hard_anti or soft_anti,
                "topology_spread": [{"key": t.get("topologyKey"), "max_skew": t.get("maxSkew"), "when": t.get("whenUnsatisfiable")} for t in tsc],
                "anti_affinity": "required" if hard_anti else ("preferred" if soft_anti else None),
            }
        )
    # workloads that can only go to one node because of scheduling constraints (regardless of replica count). Seen on a k3s: required nodeAffinity (role NotIn observability) plus that label on node B → 15 prod workloads pinned to node A
    pinned = []
    try:
        _pvcs = (json.loads((cx.snap / "objects" / "persistentvolumeclaims.json").read_text(encoding="utf-8")) or {}).get("items") or []
        _scs = (json.loads((cx.snap / "objects" / "storageclasses.json").read_text(encoding="utf-8")) or {}).get("items") or []
    except (OSError, json.JSONDecodeError, AttributeError):
        _pvcs, _scs = [], []
    pvc_sc = {(x["metadata"]["namespace"], x["metadata"]["name"]): ((x.get("spec") or {}).get("storageClassName") or "") for x in _pvcs}
    local_scs = {x["metadata"]["name"] for x in _scs if x.get("provisioner") in ("rancher.io/local-path", "kubernetes.io/no-provisioner", "openebs.io/local")}
    for kind, o in cx.workloads:
        if kind == "DaemonSet":
            continue
        tpl2 = cx.tpl(o)
        elig = eligible_nodes(tpl2, cx.nodes)
        if len(cx.nodes) > 1 and len(elig) <= 1:
            why = []
            if tpl2.get("nodeName"):
                why.append(f"nodeName {tpl2['nodeName']}")
            if tpl2.get("nodeSelector"):
                why.append(f"nodeSelector {tpl2['nodeSelector']}")
            req = (((tpl2.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms")
            if req:
                why.append(f"required nodeAffinity {json.dumps(req, ensure_ascii=False)[:160]}")
            if not why:
                why.append("taint/toleration")
            # unavoidable pinning: node directory volumes (local-path PVC), extended resources such as GPUs and hostNetwork cannot change nodes → record the reason and warn instead of fail
            reasons = []
            for v in tpl2.get("volumes") or []:
                claim = (v.get("persistentVolumeClaim") or {}).get("claimName")
                sc = pvc_sc.get((o["metadata"]["namespace"], claim)) if claim else None
                if sc and ("local-path" in sc or sc in local_scs):
                    reasons.append(f"local-path PVC {claim}")
                if v.get("hostPath"):
                    reasons.append(f"hostPath {v['hostPath'].get('path')}")
            for c in tpl2.get("containers") or []:
                res = c.get("resources") or {}
                for k in list((res.get("limits") or {}).keys()) + list((res.get("requests") or {}).keys()):
                    if "/" in k and not k.startswith("hugepages") and k != "ephemeral-storage":
                        reasons.append(f"extended resource {k}")
            default_sc = next((x["metadata"]["name"] for x in _scs if ((x.get("metadata") or {}).get("annotations") or {}).get("storageclass.kubernetes.io/is-default-class") == "true"), None)
            for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:  # a StatefulSet creates PVCs from templates (small k3s cluster DBs land here)
                sc = ((vct.get("spec") or {}).get("storageClassName")) or default_sc or ""
                if "local-path" in sc or sc in local_scs:
                    reasons.append(f"local-path volumeClaimTemplate {(vct.get('metadata') or {}).get('name')}")
            if tpl2.get("hostNetwork"):
                reasons.append("hostNetwork")
            reasons = sorted(set(reasons))
            pinned.append(
                {
                    "workload": cx.wl_key(kind, o),
                    "namespace": o["metadata"]["namespace"],
                    "prod": o["metadata"]["namespace"] in cx.prod,
                    "replicas": (o.get("spec") or {}).get("replicas"),
                    "eligible_nodes": elig,
                    "nodes_total": len(cx.nodes),
                    "constraints": why,
                    "serves_traffic": cx.serves(o),
                    "pin_reasons": reasons,
                    "unavoidable": bool(reasons),
                }
            )
    # prod pod concentration per node (DaemonSets excluded). If prod piles onto one spot node, a single reclaim cuts several services at once (seen on a real cluster: 27 prod pods on one node)
    node_meta = {n["metadata"]["name"]: n for n in cx.nodes}
    prod_by_node: Counter = Counter()
    prod_wl_by_node: dict[str, set] = defaultdict(set)
    for p in cx.pods:
        if p["status"].get("phase") != "Running" or p["metadata"]["namespace"] not in cx.prod:
            continue
        own = next((o for o in p["metadata"].get("ownerReferences") or []), {})
        if own.get("kind") == "DaemonSet":
            continue
        nd = p["spec"].get("nodeName")
        if nd:
            prod_by_node[nd] += 1
            prod_wl_by_node[nd].add(workload_of(f"{p['metadata']['namespace']}/{p['metadata']['name']}"))
    prod_total = sum(prod_by_node.values())
    conc = []
    for nd, c in prod_by_node.most_common():
        lab = (node_meta.get(nd) or {}).get("metadata", {}).get("labels") or {}
        ctype = lab.get("karpenter.sh/capacity-type") or lab.get("eks.amazonaws.com/capacityType") or lab.get("node.kubernetes.io/capacity-type")
        conc.append(
            {
                "node": nd,
                "prod_pods": c,
                "share": round(c / prod_total, 2) if prod_total else None,
                "prod_workloads": sorted(prod_wl_by_node[nd])[:30],
                "workload_count": len(prod_wl_by_node[nd]),
                "capacity_type": (ctype or "").lower() or None,
                "spot": (ctype or "").lower() == "spot",
                "pool": lab.get("karpenter.sh/nodepool") or lab.get("eks.amazonaws.com/nodegroup"),
                "nodes_total": len(cx.nodes),
                "prod_total": prod_total,
                "autoscaler": cx.karpenter,
            }
        )
    return {
        "zones_in_cluster": zones_total,
        "multi_replica_workloads": len(rows),
        "rows": rows,
        "prod_by_node": conc,
        "prod_pods_total": prod_total,
        "single_eligible_node": pinned,
        "single_eligible_node_prod": [r["workload"] for r in pinned if r["prod"]],
        "single_eligible_node_prod_avoidable": [r["workload"] for r in pinned if r["prod"] and not r["unavoidable"]],
        "prod_max_share": conc[0]["share"] if conc else None,
        "prod_max_node": conc[0]["node"] if conc else None,
        "same_node": [r["workload"] for r in rows if r["all_same_node"]],
        "same_zone": [r["workload"] for r in rows if r["all_same_zone"]],
        "no_spread_declared": [r["workload"] for r in rows if not r["spread_declared"]],
    }


def _single_node(cx: _Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        if kind == "DaemonSet":
            continue
        tpl = cx.tpl(o)
        reasons = []
        ns_sel = tpl.get("nodeSelector") or {}
        if "kubernetes.io/hostname" in ns_sel:
            reasons.append(f"nodeSelector kubernetes.io/hostname={ns_sel['kubernetes.io/hostname']}")
        if tpl.get("nodeName"):
            reasons.append(f"nodeName {tpl['nodeName']}")
        hp = [v["name"] for v in tpl.get("volumes") or [] if "hostPath" in v]
        if hp:
            reasons.append(f"hostPath volume {hp}")
        aff = ((tpl.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}
        for t in aff.get("nodeSelectorTerms") or []:
            for e in t.get("matchExpressions") or []:
                if e.get("key") == "kubernetes.io/hostname" and e.get("operator") == "In":
                    reasons.append(f"nodeAffinity hostname In {e.get('values')}")
        if reasons:
            rows.append({"workload": cx.wl_key(kind, o), "namespace": o["metadata"]["namespace"], "prod": o["metadata"]["namespace"] in cx.prod, "reasons": reasons, "replicas": (o.get("spec") or {}).get("replicas")})
    return {"rows": rows}


def _az_volumes(cx: _Ctx) -> dict:
    if cx.platform != "eks":
        return {"applicable": False, "rows": []}
    zone_nodes = Counter(z for z in cx.node_zone.values() if z)
    pv_zone = {}
    for pv in objects(cx.snap, "persistentvolumes"):
        sp = pv.get("spec") or {}
        zone = None
        for t in ((sp.get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
            for e in t.get("matchExpressions") or []:
                if e.get("key") in ("topology.kubernetes.io/zone", "topology.ebs.csi.aws.com/zone", "failure-domain.beta.kubernetes.io/zone") and e.get("values"):
                    zone = e["values"][0]
        cr = sp.get("claimRef") or {}
        if zone and cr:
            pv_zone[(cr.get("namespace"), cr.get("name"))] = {"pv": pv["metadata"]["name"], "zone": zone, "sc": sp.get("storageClassName")}
    rows = []
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        claims = []
        for v in cx.tpl(o).get("volumes") or []:
            if "persistentVolumeClaim" in v:
                claims.append(v["persistentVolumeClaim"].get("claimName"))
        if kind == "StatefulSet":
            for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
                for i in range((o.get("spec") or {}).get("replicas") or 1):
                    claims.append(f"{vct['metadata']['name']}-{o['metadata']['name']}-{i}")
        zones = {}
        for c in claims:
            z = pv_zone.get((ns, c))
            if z:
                zones[c] = z["zone"]
        if zones:
            zset = set(zones.values())
            rows.append(
                {
                    "workload": cx.wl_key(kind, o),
                    "namespace": ns,
                    "prod": ns in cx.prod,
                    "claims": zones,
                    "zones": sorted(zset),
                    "nodes_in_zone": {z: zone_nodes.get(z, 0) for z in zset},
                    "zone_without_nodes": [z for z in zset if zone_nodes.get(z, 0) == 0],
                }
            )
    return {"applicable": True, "zone_nodes": dict(zone_nodes), "rows": rows, "zone_without_nodes": [r["workload"] for r in rows if r["zone_without_nodes"]]}


def _n_plus_one(cx: _Ctx) -> dict:
    nodes = []
    for n in cx.nodes:
        if (n.get("spec") or {}).get("unschedulable"):
            continue
        alloc = (n.get("status") or {}).get("allocatable") or {}
        nodes.append(
            {
                "name": n["metadata"]["name"],
                "cpu": _q(alloc.get("cpu")),
                "memory": _q(alloc.get("memory")),
                "role": "control-plane" if any(k.startswith(("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/master")) for k in (n["metadata"].get("labels") or {})) else "worker",
            }
        )
    if not nodes:
        return {"available": False}
    req_cpu = req_mem = 0.0
    per_pod = []
    for p in cx.pods:
        if p["status"].get("phase") != "Running":
            continue
        own = next((x.get("kind") for x in p["metadata"].get("ownerReferences") or []), None)
        if own == "DaemonSet":
            continue  # a DaemonSet runs one per node and is not a candidate to move
        c = m = 0.0
        for cont in p["spec"].get("containers") or []:
            r = (cont.get("resources") or {}).get("requests") or {}
            c += _q(r.get("cpu"))
            m += _q(r.get("memory"))
        req_cpu += c
        req_mem += m
        per_pod.append((p["metadata"]["namespace"], p["metadata"]["name"], p["spec"].get("nodeName"), c, m))
    total_cpu, total_mem = sum(n["cpu"] for n in nodes), sum(n["memory"] for n in nodes)
    big = max(nodes, key=lambda n: n["cpu"])
    rest_cpu, rest_mem = total_cpu - big["cpu"], total_mem - max(n["memory"] for n in nodes)
    # pods that cannot fit on any remaining node when the one (largest) node is lost (request larger than the remaining nodes' allocatable)
    others = [n for n in nodes if n["name"] != big["name"]]
    # scheduling constraints (nodeSelector, required nodeAffinity, taints) are considered too, not just resources — on a small k3s cluster 30 prod pods could only go to one node via nodeAffinity yet "cannot fit: []" was reported
    node_objs = {n["metadata"]["name"]: n for n in cx.nodes}
    pod_spec_by = {(p["metadata"]["namespace"], p["metadata"]["name"]): p["spec"] for p in cx.pods}
    cannot_fit = []
    for ns, pod, nd, c, m in per_pod:
        if nd != big["name"]:
            continue
        spec = pod_spec_by.get((ns, pod)) or {}
        elig = [e for e in eligible_nodes(spec, [node_objs[n["name"]] for n in others if n["name"] in node_objs], ignore_node_name=True) if e != big["name"]]
        if not elig:
            cannot_fit.append(
                {"namespace": ns, "pod": pod, "node": nd, "cpu": round(c, 2), "memory_gb": round(m / 1024**3, 2), "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node", "eligible_nodes": []}
            )
            continue
        elig_cpu = max(n["cpu"] for n in others if n["name"] in elig)
        elig_mem = max(n["memory"] for n in others if n["name"] in elig)
        if c > elig_cpu or m > elig_mem:
            cannot_fit.append({"namespace": ns, "pod": pod, "node": nd, "cpu": round(c, 2), "memory_gb": round(m / 1024**3, 2), "reason": "request exceeds the allocatable of every eligible node", "eligible_nodes": elig})
    on_big = [x for x in per_pod if x[2] == big["name"]]
    return {
        "available": True,
        "nodes": len(nodes),
        "largest_node": big["name"],
        "largest_node_cpu": big["cpu"],
        "largest_node_memory_gb": round(big["memory"] / 1024**3, 1),
        "allocatable_cpu_total": round(total_cpu, 2),
        "allocatable_cpu_without_largest": round(rest_cpu, 2),
        "requests_cpu_total": round(req_cpu, 2),
        "allocatable_memory_gb_total": round(total_mem / 1024**3, 1),
        "allocatable_memory_gb_without_largest": round(rest_mem / 1024**3, 1),
        "requests_memory_gb_total": round(req_mem / 1024**3, 1),
        "cpu_ok": req_cpu <= rest_cpu * 1.02,
        "memory_ok": req_mem <= rest_mem * 1.02,
        "ok": req_cpu <= rest_cpu * 1.02 and req_mem <= rest_mem * 1.02,
        "margin": 0.02,  # 2% margin: a single minute-level CronJob pod (0.01 cores) used to flip pass/fail back and forth
        "pods_on_largest_node": len(on_big),
        "prod_pods_on_largest_node": sum(1 for x in on_big if x[0] in cx.prod),
        "cannot_fit_elsewhere": cannot_fit,
        "cannot_fit_prod": [f"{x['namespace']}/{x['pod']}" for x in cannot_fit if x["namespace"] in cx.prod],
        "karpenter": cx.karpenter,
        "note": "With Karpenter, pods only fail to start until a new node comes up (measured p50 62 seconds). Without it (small k3s cluster), this is the list of pods that can never start again if one node dies",
    }


def _node_boot_times(cx: _Ctx) -> dict[str, _dt.datetime]:
    """node_boot_time_seconds (node-exporter, instance=IP:9100) → node name. The baseline for separating reboot-induced restarts and post-boot logs."""
    ip_to_node = {}
    for n in cx.nodes:
        for a in (n.get("status") or {}).get("addresses") or []:
            if a.get("type") == "InternalIP":
                ip_to_node[a.get("address")] = n["metadata"]["name"]
    out = {}
    m = load_json(cx.snap / "metrics" / "node_boot_time.json") or {}
    for r in m.get("result") or []:
        inst = (r.get("metric") or {}).get("instance", "").split(":")[0]
        node = ip_to_node.get(inst) or (r.get("metric") or {}).get("node")
        try:
            if node:
                out[node] = _dt.datetime.fromtimestamp(float(r["value"][1]), tz=_dt.UTC)
        except (KeyError, ValueError, TypeError, IndexError):
            pass
    return out


def _restarts(cx: _Ctx) -> dict:
    boot = _node_boot_times(cx)
    unhealthy: Counter = Counter()
    by_probe: Counter = Counter()  # (ns, pod, liveness|readiness|startup) → count. startup failures cause restarts, readiness failures do not
    for e in (load_json(cx.snap / "events.json") or {}).get("items") or []:
        io = e.get("involvedObject") or {}
        if e.get("reason") == "Unhealthy" and io.get("kind") == "Pod":
            unhealthy[(io.get("namespace"), io.get("name"))] += int(e.get("count") or 1)
            msg = str(e.get("message") or "")
            kind_p = "startup" if msg.startswith("Startup") else ("readiness" if msg.startswith("Readiness") else ("liveness" if msg.startswith("Liveness") else "?"))
            by_probe[(io.get("namespace"), io.get("name"), kind_p)] += int(e.get("count") or 1)
    rows = []
    for p in cx.pods:
        ns, name = p["metadata"]["namespace"], p["metadata"]["name"]
        for cs in p["status"].get("containerStatuses") or []:
            rc = cs.get("restartCount") or 0
            if rc < 3:
                continue
            last = (cs.get("lastState") or {}).get("terminated") or {}
            waiting = ((cs.get("state") or {}).get("waiting") or {}).get("reason")
            cause = last.get("reason") or "?"
            fin = _ts(last.get("finishedAt"))
            bt = boot.get(p["spec"].get("nodeName"))
            rebooted = bool(fin and bt and abs((bt - fin).total_seconds()) <= 600)
            if rebooted:
                kind = "node reboot (container Unknown/255 — not a crash)"
            elif cause == "OOMKilled":
                kind = "OOM (memory limit)"
            elif by_probe.get((ns, name, "liveness")) or by_probe.get((ns, name, "startup")):
                kind = "probe failure (" + ("liveness" if by_probe.get((ns, name, "liveness")) else "startup") + " restart)"
            elif unhealthy.get((ns, name)) and cause == "Error":
                kind = f"crash (exit {last.get('exitCode')}) + readiness failure"
            elif cause == "Error" and (last.get("exitCode") or 0) != 0:
                kind = f"crash (exit {last.get('exitCode')})"
            else:
                kind = cause
            rows.append(
                {
                    "namespace": ns,
                    "pod": name,
                    "container": cs.get("name"),
                    "restarts": rc,
                    "waiting": waiting,
                    "last_reason": cause,
                    "exit_code": last.get("exitCode"),
                    "last_finished": last.get("finishedAt"),
                    "unhealthy_events": unhealthy.get((ns, name), 0),
                    "unhealthy_by_probe": {k: by_probe[(ns, name, k)] for k in ("liveness", "readiness", "startup") if by_probe.get((ns, name, k))},
                    "cause": kind,
                    "prod": ns in cx.prod,
                    "node_rebooted_at": bt.isoformat(timespec="seconds") if (rebooted and bt) else None,
                    "rebooted": rebooted,
                    "crashloop": waiting == "CrashLoopBackOff",
                }
            )
    rows.sort(key=lambda r: -r["restarts"])
    # containers whose last termination reason is OOMKilled (regardless of restart count) — input for resources.oomkilled to attach "when" (seen: an OOM from 5 months ago reported as high)
    oom_last = {}
    now = _dt.datetime.now(_dt.UTC)
    for p in cx.pods:
        ns, name = p["metadata"]["namespace"], p["metadata"]["name"]
        for cs in p["status"].get("containerStatuses") or []:
            last = (cs.get("lastState") or {}).get("terminated") or {}
            if last.get("reason") == "OOMKilled":
                fin = _ts(last.get("finishedAt"))
                oom_last[f"{ns}/{name}/{cs.get('name')}"] = {"finished": last.get("finishedAt"), "age_days": round((now - fin).total_seconds() / 86400, 1) if fin else None, "restarts": cs.get("restartCount") or 0, "prod": ns in cx.prod}
    return {
        "rows": rows[:40],
        "by_cause": dict(Counter(r["cause"] for r in rows)),
        "crashloop_now": [f"{r['namespace']}/{r['pod']}" for r in rows if r["crashloop"]],
        "oom_last": oom_last,
        "oom_recent_7d": sorted(k for k, v in oom_last.items() if (v["age_days"] or 0) <= 7),
    }


def _cronjobs(cx: _Ctx, now: _dt.datetime) -> dict:
    jobs = objects(cx.snap, "jobs.batch")
    jobs_by_owner: dict[tuple, list] = defaultdict(list)
    for j in jobs:
        own = next((x for x in j["metadata"].get("ownerReferences") or []), None)
        if own and own.get("kind") == "CronJob":
            jobs_by_owner[(j["metadata"]["namespace"], own.get("name"))].append(j)
    rows = []
    for cj in objects(cx.snap, "cronjobs.batch"):
        md, sp, st = cj["metadata"], cj.get("spec") or {}, cj.get("status") or {}
        ns = md["namespace"]
        jt = (sp.get("jobTemplate") or {}).get("spec") or {}
        interval = _cron_interval_h(sp.get("schedule"))
        last_ok = _ts(st.get("lastSuccessfulTime"))
        last_sched = _ts(st.get("lastScheduleTime"))
        age_ok = round((now - last_ok).total_seconds() / 3600, 1) if last_ok else None
        myjobs = jobs_by_owner.get((ns, md["name"]), [])
        failed = [j["metadata"]["name"] for j in myjobs if (j.get("status") or {}).get("failed")]
        durs = []
        for j in myjobs:
            js = j.get("status") or {}
            a, b = _ts(js.get("startTime")), _ts(js.get("completionTime"))
            if a and b:
                durs.append((b - a).total_seconds())
        durs.sort()
        max_dur = durs[-1] if durs else None
        med_dur = durs[len(durs) // 2] if durs else None
        runtime_ratio = round(max_dur / (interval * 3600), 2) if (max_dur is not None and interval) else None
        gaps = []
        if (sp.get("concurrencyPolicy") or "Allow") == "Allow":
            gaps.append("concurrencyPolicy Allow (overlap allowed)")
        if jt.get("activeDeadlineSeconds") is None:
            gaps.append("activeDeadlineSeconds missing (a stuck Job runs forever)")
        if jt.get("backoffLimit") is None and not jt.get("podFailurePolicy"):
            gaps.append("backoffLimit default 6 and no podFailurePolicy")
        if jt.get("ttlSecondsAfterFinished") is None and (sp.get("successfulJobsHistoryLimit", 3) or 0) > 10:
            gaps.append("many finished Jobs retained")
        if sp.get("startingDeadlineSeconds") is None:
            gaps.append("startingDeadlineSeconds missing (the controller stops after 100 missed schedules)")
        stale = (not sp.get("suspend") and bool(interval and age_ok is not None and age_ok > max(interval * 3, 3))) or (last_ok is None and last_sched is not None and (now - last_sched).total_seconds() > 86400 and not sp.get("suspend"))
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "schedule": sp.get("schedule"),
                "interval_h": interval,
                "suspend": bool(sp.get("suspend")),
                "concurrency_policy": sp.get("concurrencyPolicy") or "Allow",
                "starting_deadline_s": sp.get("startingDeadlineSeconds"),
                "backoff_limit": jt.get("backoffLimit"),
                "active_deadline_s": jt.get("activeDeadlineSeconds"),
                "ttl_s": jt.get("ttlSecondsAfterFinished"),
                "pod_failure_policy": bool(jt.get("podFailurePolicy")),
                "history_limits": [sp.get("successfulJobsHistoryLimit", 3), sp.get("failedJobsHistoryLimit", 1)],
                "last_schedule": st.get("lastScheduleTime"),
                "last_success": st.get("lastSuccessfulTime"),
                "hours_since_success": age_ok,
                "active_jobs": len(st.get("active") or []),
                "jobs_total": len(myjobs),
                "failed_jobs": failed,
                "stale": stale,
                "policy_gaps": gaps,
                "prod": ns in cx.prod,
                "jobs_timed": len(durs),
                "max_job_duration_s": round(max_dur) if max_dur is not None else None,
                "median_job_duration_s": round(med_dur) if med_dur is not None else None,
                "runtime_over_interval": runtime_ratio,
            }
        )
    finished_no_ttl = [j for j in jobs if ((j.get("status") or {}).get("succeeded") or (j.get("status") or {}).get("failed")) and (j.get("spec") or {}).get("ttlSecondsAfterFinished") is None]
    succeeded_pods = sum(1 for p in cx.pods if p["status"].get("phase") == "Succeeded")
    failed_pods = sum(1 for p in cx.pods if p["status"].get("phase") == "Failed")
    return {
        "count": len(rows),
        "rows": rows,
        "stale": [r["target"] for r in rows if r["stale"]],
        "stacking": [r["target"] for r in rows if r["active_jobs"] >= 3],
        "runtime_exceeds_interval": [r["target"] for r in rows if (r["runtime_over_interval"] or 0) >= 1.0],
        "jobs": {"total": len(jobs), "failed": sum(1 for j in jobs if (j.get("status") or {}).get("failed")), "finished_without_ttl": len(finished_no_ttl), "succeeded_pods": succeeded_pods, "failed_pods": failed_pods},
    }


BACKUP_NAME_RE = re.compile(r"(backup|dump|snapshot|archive|bak)", re.IGNORECASE)
OFFSITE_RE = re.compile(r"(s3://|s3\.|aws s3|rclone|restic|gs://|gsutil|b2 |backblaze|minio|mc cp|azcopy|rsync .*@|scp |sftp|wal-g|pgbackrest|borg|kopia)", re.IGNORECASE)


def _pv_node(pv: dict) -> str | None:
    for t in (((pv.get("spec") or {}).get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
        for e in t.get("matchExpressions") or []:
            if e.get("key") == "kubernetes.io/hostname" and e.get("values"):
                return e["values"][0]
    return None


def _backup_locality(cx: _Ctx) -> dict:
    """Does the backup CronJob's output stay only on 'the same node disk as the source'? Inputs: jobTemplate volumes and commands of cronjobs.batch,
    PVC → PV nodeAffinity (local-path), PVC nodes of DB workloads in the same namespace. offsite_hint when a command that ships the dump via S3, rclone, restic etc. is visible."""
    pvc_node: dict[tuple, str | None] = {}
    pvc_pv: dict[tuple, str] = {}
    for pv in objects(cx.snap, "persistentvolumes"):
        cr = (pv.get("spec") or {}).get("claimRef") or {}
        if cr.get("name"):
            pvc_node[(cr.get("namespace"), cr["name"])] = _pv_node(pv)
            pvc_pv[(cr.get("namespace"), cr["name"])] = pv["metadata"]["name"]
    db_pvcs: dict[str, list[tuple]] = defaultdict(list)  # ns → [(workload, pvc, node)]
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        if not DB_HINT_RE.search(o["metadata"]["name"] + " " + " ".join(c.get("image", "") for c in cx.tpl(o).get("containers") or [])):
            continue
        claims = [v["persistentVolumeClaim"]["claimName"] for v in cx.tpl(o).get("volumes") or [] if v.get("persistentVolumeClaim")]
        for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
            for p in cx.pods_of(kind, o):
                for v in p["spec"].get("volumes") or []:
                    if v.get("persistentVolumeClaim") and v["persistentVolumeClaim"]["claimName"].startswith(vct["metadata"]["name"] + "-"):
                        claims.append(v["persistentVolumeClaim"]["claimName"])
        for c in sorted(set(claims)):
            db_pvcs[ns].append((cx.wl_key(kind, o), c, pvc_node.get((ns, c))))
    rows = []
    for cj in objects(cx.snap, "cronjobs.batch"):
        md, sp = cj["metadata"], cj.get("spec") or {}
        ns = md["namespace"]
        pod = (((sp.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
        text = " ".join(
            " ".join((c.get("command") or []) + (c.get("args") or [])) + " " + " ".join(str(e.get("value") or "") for e in c.get("env") or []) + " " + c.get("image", "")
            for c in (pod.get("containers") or []) + (pod.get("initContainers") or [])
        )
        if not BACKUP_NAME_RE.search(md["name"] + " " + text[:400]):
            continue
        claims = [v["persistentVolumeClaim"]["claimName"] for v in pod.get("volumes") or [] if v.get("persistentVolumeClaim")]
        host_paths = [v["hostPath"].get("path") for v in pod.get("volumes") or [] if v.get("hostPath")]
        dest_nodes = {pvc_node.get((ns, c)) for c in claims}
        offsite = bool(OFFSITE_RE.search(text))
        src = db_pvcs.get(ns, [])
        src_nodes = {n for _, _, n in src if n}
        same_node = bool(dest_nodes & src_nodes) or (bool(host_paths) and bool(pod.get("nodeSelector") or pod.get("nodeName")))
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "prod": ns in cx.prod,
                "schedule": sp.get("schedule"),
                "suspend": bool(sp.get("suspend")),
                "dest_pvcs": claims,
                "dest_nodes": sorted(n for n in dest_nodes if n),
                "host_paths": host_paths,
                "offsite_hint": offsite,
                "source_db": [{"workload": w, "pvc": c, "node": n} for w, c, n in src][:6],
                "source_nodes": sorted(src_nodes),
                "same_node_as_source": same_node,
                "local_only": not offsite and (bool(claims) or bool(host_paths)),
                "note": "offsite_hint = whether command, args or env values contain strings such as s3, rclone or restic (names only, values are not recorded)",
            }
        )
    dbs_without_backup = []
    backed_ns = {r["namespace"] for r in rows if not r["suspend"]}
    for ns, lst in db_pvcs.items():
        if ns not in backed_ns and ns in cx.prod:
            dbs_without_backup += [w for w, _, _ in lst]
    return {
        "rows": rows,
        "count": len(rows),
        "local_only": [r["target"] for r in rows if r["local_only"]],
        "same_node": [r["target"] for r in rows if r["same_node_as_source"]],
        "prod_db_without_backup_cronjob": sorted(set(dbs_without_backup)),
        "db_workloads_with_pvc": sum(len(v) for v in db_pvcs.values()),
    }


def _priority(cx: _Ctx) -> dict:
    pcs = [
        {"name": p["metadata"]["name"], "value": p.get("value"), "global_default": bool(p.get("globalDefault")), "preemption": p.get("preemptionPolicy") or "PreemptLowerPriority"}
        for p in objects(cx.snap, "priorityclasses.scheduling.k8s.io")
    ]
    user_pcs = [p for p in pcs if not p["name"].startswith("system-")]
    prod_max = 0
    nonprod_max = 0
    prod_without = 0
    prod_pods = 0
    by_class: Counter = Counter()
    offenders = []
    for p in cx.pods:
        if p["status"].get("phase") != "Running":
            continue
        ns = p["metadata"]["namespace"]
        pr = p["spec"].get("priority") or 0
        pc = p["spec"].get("priorityClassName")
        by_class[pc or "(none, 0)"] += 1
        if ns in cx.prod:
            prod_pods += 1
            prod_max = max(prod_max, pr)
            if not pc:
                prod_without += 1
        elif not ns.startswith("kube-") and not (pc or "").startswith("system-"):
            nonprod_max = max(nonprod_max, pr)
            if pr > 0:
                offenders.append({"namespace": ns, "pod": p["metadata"]["name"], "priority": pr, "class": pc})
    preempted = sum(int(e.get("count") or 1) for e in ((load_json(cx.snap / "events.json") or {}).get("items") or []) if e.get("reason") == "Preempted")
    inversion = [o for o in offenders if o["priority"] > prod_max] if prod_pods else []
    return {
        "classes": pcs,
        "user_classes": user_pcs,
        "pods_by_class": dict(by_class),
        "prod_pods": prod_pods,
        "prod_pods_without_class": prod_without,
        "prod_max_priority": prod_max,
        "nonprod_max_priority": nonprod_max,
        "inversion": inversion[:20],
        "preempted_events": preempted,
        "no_user_classes_with_prod": bool(prod_pods) and not user_pcs,
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    cx = _Ctx(snap, inv)
    now = _dt.datetime.now(_dt.UTC)
    return {
        "probes": _probes(cx),
        "pdbs": _pdbs(cx),
        "graceful": _graceful(cx),
        "placement": _placement(cx),
        "single_node": _single_node(cx),
        "az_volumes": _az_volumes(cx),
        "n_plus_one": _n_plus_one(cx),
        "restarts": _restarts(cx),
        "cronjobs": _cronjobs(cx, now),
        "priority": _priority(cx),
        "backup": _backup_locality(cx),
    }

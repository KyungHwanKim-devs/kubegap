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

from .nodetext import kernel_oom_kills
from .quantity import parse as quantity
from .snapshot import event_count, load_json, metric_doc, metric_rows, objects, parse_ts, taken_at
from .workload import eligible_nodes, image_repo, is_db_like, mounts_pvc, selector_matches, workload_of
from .workload import key as wl_key

SUSPECT_LIVENESS_RE = re.compile(r"(db|database|mysql|postgres|redis|mongo|kafka|ready|readiness|deps|dependenc|upstream|downstream|elastic|full=true)", re.IGNORECASE)
DB_SELF_PROBE_RE = re.compile(
    r"(pg_isready|mysqladmin|mysql .*-e|redis-cli|valkey-cli|mongosh|mongo .*ping|cqlsh|nodetool|clickhouse-client|rabbitmq-diagnostics|rabbitmqctl|etcdctl endpoint|_cluster/health|minio.*health)", re.IGNORECASE
)  # standard probes that check the DB's own response — not external dependencies (seen: 6 mysql false positives)
SHELLS = ("sh", "/bin/sh", "bash", "/bin/bash", "/usr/bin/bash", "ash", "/bin/ash")


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
        self.now = taken_at(inv)  # every age in this module is measured from the snapshot time (#165)
        comps = inv.get("components") or {}
        present = set(inv.get("components_present") or [])
        self.karpenter = bool((comps.get("karpenter") or {}).get("present")) or "karpenter" in present
        self.cluster_autoscaler = bool((comps.get("cluster-autoscaler") or {}).get("present")) or "cluster-autoscaler" in present
        self.autoscaler = self.karpenter or self.cluster_autoscaler  # any node autoscaler turns a lost node into minutes of waiting instead of a permanent loss
        self.autoscaler_name = "karpenter" if self.karpenter else ("cluster-autoscaler" if self.cluster_autoscaler else None)
        self.pods = objects(snap, "pods")
        self.nodes = objects(snap, "nodes")
        self.services = objects(snap, "services")
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet")):
            for o in objects(snap, stem):
                self.workloads.append((kind, o))
        self.node_zone = {n["metadata"]["name"]: (n["metadata"].get("labels") or {}).get("topology.kubernetes.io/zone") for n in self.nodes}
        self.pod_by_name = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in self.pods}
        self.job_owner = {}
        for j in objects(snap, "jobs.batch"):
            own = next((o for o in j["metadata"].get("ownerReferences") or []), None)
            if own:
                self.job_owner[(j["metadata"]["namespace"], j["metadata"]["name"])] = (own.get("kind"), own.get("name"))
        self.job_names = set(self.job_owner) | {(j["metadata"]["namespace"], j["metadata"]["name"]) for j in objects(snap, "jobs.batch")}
        self.cronjob_names = {(c["metadata"]["namespace"], c["metadata"]["name"]) for c in objects(snap, "cronjobs")}
        self.rs_names = {(rs["metadata"]["namespace"], rs["metadata"]["name"]) for rs in objects(snap, "replicasets.apps")}
        self.rs_owner = {}
        for rs in objects(snap, "replicasets.apps"):
            own = next((o for o in rs["metadata"].get("ownerReferences") or []), None)
            if own:
                self.rs_owner[(rs["metadata"]["namespace"], rs["metadata"]["name"])] = (own.get("kind"), own.get("name"))

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


def _probes(cx: _Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        stateful = kind == "StatefulSet" and (bool((o.get("spec") or {}).get("volumeClaimTemplates")) or mounts_pvc(cx.tpl(o)))
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
            db_like = is_db_like(c.get("name"), c.get("image"), o["metadata"]["name"], stateful=stateful)
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
                    "workload": wl_key(kind, o),
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
        covered = [wl_key(k, o) for k, o in cx.workloads if o["metadata"]["namespace"] == ns and selector_matches(sp.get("selector"), cx.tpl_labels(o))]
        replicas = [((o.get("spec") or {}).get("replicas")) for k, o in cx.workloads if wl_key(k, o) in covered and k != "DaemonSet"]
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
                # the DisruptionAllowed condition's reason tells InsufficientPods (the budget holds) from SyncFailed (the controller could not compute the budget, and the apiserver denies evictions as well: kubernetes/kubernetes pkg/controller/disruption/disruption.go:982-990@v1.37.2) (#124 K1-4)
                "disruption_allowed_reason": next((c.get("reason") for c in st.get("conditions") or [] if c.get("type") == "DisruptionAllowed"), None),
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
                "workload": wl_key(kind, o),
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
                # Deployments carry `spec.strategy`, StatefulSets and DaemonSets `spec.updateStrategy` (kubernetes/kubernetes staging/src/k8s.io/api/apps/v1/types.go:436,268,715@v1.37.2) (#124 K1-3)
                "max_unavailable": ((((o.get("spec") or {}).get("strategy") or (o.get("spec") or {}).get("updateStrategy") or {}).get("rollingUpdate") or {}).get("maxUnavailable")),
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
                "workload": wl_key(kind, o),
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
                    "workload": wl_key(kind, o),
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
        ctype = lab.get("karpenter.sh/capacity-type") or lab.get("eks.amazonaws.com/capacityType")  # `node.kubernetes.io/capacity-type` was read too; no project sets that label (#124 K1)
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
                "autoscaler": cx.autoscaler,
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
            rows.append({"workload": wl_key(kind, o), "namespace": o["metadata"]["namespace"], "prod": o["metadata"]["namespace"] in cx.prod, "reasons": reasons, "replicas": (o.get("spec") or {}).get("replicas")})
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
                    "workload": wl_key(kind, o),
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
                "cpu": quantity(alloc.get("cpu")),
                "memory": quantity(alloc.get("memory")),
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
            c += quantity(r.get("cpu"))
            m += quantity(r.get("memory"))
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
    # N+1 per pool of eligible nodes: pods that may only land on some nodes (nodeSelector, nodeAffinity, taints) must fit into the free room of those nodes alone;
    # the cluster-wide sum says they fit while the labelled nodes are full. The free room of a node is its allocatable minus the requests already running there.
    used_cpu: dict[str, float] = {}
    used_mem: dict[str, float] = {}
    for p in cx.pods:  # every running pod, DaemonSets included: their requests occupy the room the moving pods would need
        if p["status"].get("phase") != "Running" or not p["spec"].get("nodeName"):
            continue
        nd = p["spec"]["nodeName"]
        for cont in p["spec"].get("containers") or []:
            r = (cont.get("resources") or {}).get("requests") or {}
            used_cpu[nd] = used_cpu.get(nd, 0.0) + quantity(r.get("cpu"))
            used_mem[nd] = used_mem.get(nd, 0.0) + quantity(r.get("memory"))
    pools: dict[tuple, dict] = {}
    for ns, pod, _nd, c, m in on_big:
        spec = pod_spec_by.get((ns, pod)) or {}
        elig = tuple(sorted(e for e in eligible_nodes(spec, [node_objs[n["name"]] for n in others if n["name"] in node_objs], ignore_node_name=True) if e != big["name"]))
        pl = pools.setdefault(elig, {"eligible_nodes": list(elig), "pods": 0, "prod_pods": 0, "needed_cpu": 0.0, "needed_memory": 0.0})
        pl["pods"] += 1
        pl["prod_pods"] += 1 if ns in cx.prod else 0
        pl["needed_cpu"] += c
        pl["needed_memory"] += m
    pool_rows = []
    for elig, pl in pools.items():
        free_cpu = sum(max(n["cpu"] - used_cpu.get(n["name"], 0.0), 0.0) for n in others if n["name"] in elig)
        free_mem = sum(max(n["memory"] - used_mem.get(n["name"], 0.0), 0.0) for n in others if n["name"] in elig)
        ok_pool = pl["needed_cpu"] <= free_cpu and pl["needed_memory"] <= free_mem
        within_margin = not ok_pool and pl["needed_cpu"] <= free_cpu * 1.02 and pl["needed_memory"] <= free_mem * 1.02
        pool_rows.append(
            {
                **pl,
                "needed_cpu": round(pl["needed_cpu"], 2),
                "needed_memory_gb": round(pl["needed_memory"] / 1024**3, 2),
                "free_cpu": round(free_cpu, 2),
                "free_memory_gb": round(free_mem / 1024**3, 2),
                "ok": ok_pool or within_margin,
                "tight": within_margin,  # fits only inside the 2% flapping margin: pass, but the report says so
            }
        )
        pool_rows[-1].pop("needed_memory", None)
    pools_ok = all(r["ok"] for r in pool_rows)
    short = [r for r in pool_rows if not r["ok"]]
    ok_total = req_cpu <= rest_cpu * 1.02 and req_mem <= rest_mem * 1.02
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
        "ok": ok_total and pools_ok,
        "total_ok": ok_total,
        "pools": pool_rows,
        "pools_short": [{"eligible_nodes": r["eligible_nodes"], "pods": r["pods"], "needed_cpu": r["needed_cpu"], "free_cpu": r["free_cpu"], "needed_memory_gb": r["needed_memory_gb"], "free_memory_gb": r["free_memory_gb"]} for r in short],
        "tight": any(r["tight"] for r in pool_rows) or (ok_total and not (req_cpu <= rest_cpu and req_mem <= rest_mem)),
        "margin": 0.02,  # 2% margin: a single minute-level CronJob pod (0.01 cores) used to flip pass/fail back and forth; inside the margin the result is ok and tight
        "pods_on_largest_node": len(on_big),
        "prod_pods_on_largest_node": sum(1 for x in on_big if x[0] in cx.prod),
        "cannot_fit_elsewhere": cannot_fit,
        "cannot_fit_prod": [f"{x['namespace']}/{x['pod']}" for x in cannot_fit if x["namespace"] in cx.prod],
        "karpenter": cx.karpenter,
        "autoscaler": cx.autoscaler,
        "autoscaler_name": cx.autoscaler_name,
        "note": "With a node autoscaler, Karpenter or cluster-autoscaler, pods only fail to start until a new node comes up (Karpenter measured p50 62 seconds). Without one, this is the list of pods that can never start again if one node dies. pools_short lists the groups of pods whose eligible nodes alone have no room for them",
    }


def _node_boot_times(cx: _Ctx) -> dict[str, _dt.datetime]:
    """node_boot_time_seconds (node-exporter, instance=IP:9100) → node name. The baseline for separating reboot-induced restarts and post-boot logs."""
    ip_to_node = {}
    for n in cx.nodes:
        for a in (n.get("status") or {}).get("addresses") or []:
            if a.get("type") == "InternalIP":
                ip_to_node[a.get("address")] = n["metadata"]["name"]
    out = {}
    for lab, v in metric_rows(cx.snap, "node_boot_time"):
        inst = lab.get("instance", "").split(":")[0]
        node = ip_to_node.get(inst) or lab.get("node")
        if node:
            out[node] = _dt.datetime.fromtimestamp(v, tz=_dt.UTC)
    return out


def _restarts(cx: _Ctx) -> dict:
    boot = _node_boot_times(cx)
    unhealthy: Counter = Counter()
    by_probe: Counter = Counter()  # (ns, pod, liveness|readiness|startup) → count. startup failures cause restarts, readiness failures do not
    for e in (load_json(cx.snap / "events.json") or {}).get("items") or []:
        io = e.get("involvedObject") or {}
        if e.get("reason") == "Unhealthy" and io.get("kind") == "Pod":
            unhealthy[(io.get("namespace"), io.get("name"))] += event_count(e)
            msg = str(e.get("message") or "")
            kind_p = "startup" if msg.startswith("Startup") else ("readiness" if msg.startswith("Readiness") else ("liveness" if msg.startswith("Liveness") else "?"))
            by_probe[(io.get("namespace"), io.get("name"), kind_p)] += event_count(e)
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
            fin = parse_ts(last.get("finishedAt"))
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
    now = cx.now
    for p in cx.pods:
        ns, name = p["metadata"]["namespace"], p["metadata"]["name"]
        for cs in p["status"].get("containerStatuses") or []:
            last = (cs.get("lastState") or {}).get("terminated") or {}
            if last.get("reason") == "OOMKilled":
                fin = parse_ts(last.get("finishedAt"))
                oom_last[f"{ns}/{name}/{cs.get('name')}"] = {"finished": last.get("finishedAt"), "age_days": round((now - fin).total_seconds() / 86400, 1) if fin else None, "restarts": cs.get("restartCount") or 0, "prod": ns in cx.prod}
    return {
        "rows": rows[:40],
        "by_cause": dict(Counter(r["cause"] for r in rows)),
        "crashloop_now": [f"{r['namespace']}/{r['pod']}" for r in rows if r["crashloop"]],
        "oom_last": oom_last,
        "oom_recent_7d": sorted(k for k, v in oom_last.items() if (v["age_days"] or 0) <= 7),
    }


_KIND_SHORT = {"Deployment": "deploy", "StatefulSet": "sts", "DaemonSet": "ds", "Job": "job", "CronJob": "cronjob", "ReplicaSet": "rs", "ReplicationController": "rc"}


def _owner_of_pod(cx: _Ctx, ns: str, pod: str, created_by: tuple[str | None, str | None] | None) -> str:
    """`deploy/<name>`, `sts/<name>`, `cronjob/<name>` … for a pod, the same shape lib.evaluate.Context.workload gives a metric series. A live pod is read from its ownerReferences;
    a pod that is already gone is read from kube_pod_info's created_by, and a ReplicaSet is resolved to its Deployment through the ReplicaSets still in the snapshot, else by stripping the hash with a `?` mark."""
    obj = cx.pod_by_name.get((ns, pod))
    if obj is not None:
        own = next(iter(obj["metadata"].get("ownerReferences") or []), None)
        if own:
            created_by = (own.get("kind"), own.get("name"))
    kind, name = created_by or (None, None)
    if not kind or not name:
        return f"pod/{pod}"
    if kind == "ReplicaSet":
        parent = cx.rs_owner.get((ns, name))
        if parent:
            kind, name = parent
        elif (ns, name) in cx.rs_names:
            return f"rs/{name}"  # a ReplicaSet of its own, no Deployment above it
        else:
            # the ReplicaSet is gone too: strip the hash, and drop the guess mark when a Deployment of that name exists in the namespace, as lib.evaluate.Context.workload does
            name = name.rsplit("-", 1)[0]
            confirmed = any(k == "Deployment" and o["metadata"]["namespace"] == ns and o["metadata"]["name"] == name for k, o in cx.workloads) or ("Deployment", name) in {v for (n, _), v in cx.rs_owner.items() if n == ns}
            return f"{'deploy' if confirmed else 'deploy?'}/{name}"
    elif kind == "Job":
        parent = cx.job_owner.get((ns, name))
        if parent:
            kind, name = parent
        elif (ns, name) not in cx.job_names and re.search(r"-\d{6,}$", name):
            # a finished CronJob run whose Job is gone: <cronjob>-<schedule id>. One target per CronJob, as lib.evaluate.Context.workload gives it
            base = name.rsplit("-", 1)[0]
            return f"{'cronjob' if (ns, base) in cx.cronjob_names else 'cronjob?'}/{base}"
    return f"{_KIND_SHORT.get(kind, kind.lower())}/{name}"


def oom_7d(cx: _Ctx) -> dict:
    """OOM history per workload and container over 7 days, pods a rollout has replaced included.

    Two sources that measure different things, both kept and both named in the row:
    - Prometheus (`metrics/oom_pods_7d.json`, `metrics/pod_info_7d.json`, both modes): every pod that ended with OOMKilled at any time in 7 days, with that pod's 7-day restart increase.
      The restarts are an upper bound of its OOM kills, since a probe failure restarts a container too; the number of pods is the number of distinct lives of the workload that died of OOM at least once.
    - Kernel log (`logs/node/<node>/os.txt`, full mode, nodes the node backend reached): one entry per `oom-kill:` line, attributed through the pod uid in the cgroup path. Exact count, 24-hour window.
      `kernel_nodes_read` says how many of the nodes the workload's pods ran on had a kernel log, so a 0 is "none seen" only when every node was read.
    cAdvisor's `container_oom_events_total` (`metrics/oom_events_7d.json`) is carried as `cadvisor_oom_events_7d` for the evidence only: on cgroup v2 nodes it stayed at 0 through five kernel kills."""
    rows: dict[str, dict] = {}
    info: dict[tuple[str, str], dict] = {}
    for lab, _v in metric_rows(cx.snap, "pod_info_7d"):
        info[(lab.get("namespace"), lab.get("pod"))] = lab
    by_uid: dict[str, tuple[str, str]] = {}
    for p in cx.pods:
        if p["metadata"].get("uid"):
            by_uid[p["metadata"]["uid"]] = (p["metadata"]["namespace"], p["metadata"]["name"])
    for (ns, pod), lab in info.items():
        if lab.get("uid"):
            by_uid.setdefault(lab["uid"], (ns, pod))
    live = {(p["metadata"]["namespace"], p["metadata"]["name"]) for p in cx.pods}
    pod_nodes: dict[tuple[str, str], str | None] = {}

    def row_for(ns: str, pod: str, container: str | None) -> dict:
        lab = info.get((ns, pod)) or {}
        wl = _owner_of_pod(cx, ns, pod, (lab.get("created_by_kind"), lab.get("created_by_name")))
        key = f"{ns}/{wl}" + (f":{container}" if container else "")
        obj = cx.pod_by_name.get((ns, pod))
        pod_nodes[(ns, pod)] = (obj or {}).get("spec", {}).get("nodeName") if obj else lab.get("node")
        return rows.setdefault(
            key,
            {
                "target": key,
                "namespace": ns,
                "workload": wl,
                "container": container,
                "prod": ns in cx.prod,
                "pods": [],
                "pods_oomkilled": 0,
                "pods_replaced": 0,
                "restarts_of_those_pods": 0,
                "live_pod_restarts_max": 0,
                "cadvisor_oom_events_7d": 0,
                "kernel_kills_24h": 0,
                "kernel_kill_times": [],
                "kernel_nodes_read": 0,
                "kernel_nodes_total": 0,
                "kernel_log_read": False,
                "kernel_any_node_read": False,
                "kernel_nodes_old_script": 0,
                "kernel_cgroup_ooms_on_nodes": 0,
                "nodes": [],
            },
        )

    for lab, v in metric_rows(cx.snap, "oom_pods_7d"):
        ns, pod, c = lab.get("namespace"), lab.get("pod"), lab.get("container")
        if not ns or not pod:
            continue
        rc = round(v)
        if rc < 1:
            continue  # the OOMKilled reason label outlives the window; a kill inside 7 days always leaves a restart in it
        r = row_for(ns, pod, c)
        r["pods"].append({"pod": pod, "restarts_7d": rc, "live": (ns, pod) in live, "node": pod_nodes.get((ns, pod))})
        r["pods_oomkilled"] += 1
        r["restarts_of_those_pods"] += rc
        if (ns, pod) in live:
            r["live_pod_restarts_max"] = max(r["live_pod_restarts_max"], rc)
        else:
            r["pods_replaced"] += 1
    for lab, v in metric_rows(cx.snap, "oom_events_7d"):
        ns, pod, c = lab.get("namespace"), lab.get("pod"), lab.get("container")
        if ns and pod and v > 0:
            row_for(ns, pod, c)["cadvisor_oom_events_7d"] += round(v)
    # kernel kills: uid → pod → row. A kill in a pod that has no OOM row in Prometheus (kube-state-metrics missed the termination, or the pod was deleted before its next scrape) still opens a row
    node_names = [n["metadata"]["name"] for n in cx.nodes]
    kernel = kernel_oom_kills(cx.snap, node_names)
    kills_unmapped = 0
    for node, rec in kernel.items():
        for k in rec["kills"]:
            tgt = by_uid.get(k["pod_uid"] or "")
            if not tgt:
                kills_unmapped += 1
                continue
            ns, pod = tgt
            # the kernel names the task, not the container; a pod with one app container gets it, a multi-container pod is counted on the pod
            obj = cx.pod_by_name.get(tgt)
            containers = [c.get("name") for c in ((obj or {}).get("spec") or {}).get("containers") or []]
            known = [r for r in rows.values() if any(p["pod"] == pod for p in r["pods"]) and r["namespace"] == ns]
            if len(known) == 1:
                r = known[0]
            elif known:
                # several containers of this pod ended by OOM: the kernel names the task, not the container, so the kill goes to the container that restarted most, the one most likely dying
                r = max(known, key=lambda x: sum(p["restarts_7d"] for p in x["pods"] if p["pod"] == pod))
            elif len(containers) == 1:
                r = row_for(ns, pod, containers[0])
            else:
                r = row_for(ns, pod, None)
            r["kernel_kills_24h"] += 1
            if k.get("time"):
                r["kernel_kill_times"].append(k["time"])
            if node not in r["nodes"]:
                r["nodes"].append(node)
    for r in rows.values():
        nodes = {p.get("node") for p in r["pods"] if p.get("node")} | set(r["nodes"])
        r["nodes"] = sorted(nodes)
        r["kernel_nodes_total"] = len(nodes)
        read = [n for n in nodes if n in kernel and kernel[n]["source"] in ("journalctl", "dmesg")]
        r["kernel_nodes_read"] = sum(1 for n in read if kernel[n]["oom_section"])
        r["kernel_nodes_old_script"] = sum(1 for n in read if not kernel[n]["oom_section"])  # the log was read, but by a node script that kept no oom-kill lines: a 0 from it means "unknown", not "none"
        r["kernel_cgroup_ooms_on_nodes"] = sum(kernel[n]["oom_cgroup_count"] for n in read if not kernel[n]["oom_section"])
        r["kernel_log_read"] = r["kernel_nodes_read"] > 0
        r["kernel_any_node_read"] = any(rec["source"] in ("journalctl", "dmesg") for rec in kernel.values())  # False in daily mode, where no node log is collected at all
        r["kernel_kill_times"] = sorted(r["kernel_kill_times"])[-10:]
        r["last_kill"] = r["kernel_kill_times"][-1] if r["kernel_kill_times"] else None
        r["pods"].sort(key=lambda p: (-p["restarts_7d"], p["pod"]))
    out_rows = sorted(rows.values(), key=lambda r: (-r["kernel_kills_24h"], -r["pods_oomkilled"], -r["restarts_of_those_pods"], r["target"]))
    prometheus_read = bool((metric_doc(cx.snap, "oom_pods_7d") or {}).get("ok"))
    return {
        "source": "metrics/oom_pods_7d.json + metrics/pod_info_7d.json + metrics/oom_events_7d.json + logs/node/<node>/os.txt oom_samples + objects/pods.json",
        "prometheus_read": prometheus_read,
        "kernel_nodes_read": sorted(n for n, rec in kernel.items() if rec["source"] in ("journalctl", "dmesg") and rec["oom_section"]),
        "kernel_nodes_old_script": sorted(n for n, rec in kernel.items() if rec["source"] in ("journalctl", "dmesg") and not rec["oom_section"]),
        "kernel_kills_unmapped": kills_unmapped,  # oom-kill lines whose pod uid no live pod and no 7-day Prometheus pod carries: a pod deleted before kube-state-metrics saw its last state
        # rows is None when the Prometheus side was not collected (a snapshot from before rubric 0.1.66, or no Prometheus): the check then skips instead of passing on an empty table
        "rows": out_rows if prometheus_read else None,
        "repeated": [r["target"] for r in out_rows if r["kernel_kills_24h"] >= 3 or r["restarts_of_those_pods"] >= 3] if prometheus_read else [],
    }


def _cronjobs(cx: _Ctx, now: _dt.datetime) -> dict:
    jobs = objects(cx.snap, "jobs.batch")
    jobs_by_owner: dict[tuple, list] = defaultdict(list)
    for j in jobs:
        own = next((x for x in j["metadata"].get("ownerReferences") or []), None)
        if own and own.get("kind") == "CronJob":
            jobs_by_owner[(j["metadata"]["namespace"], own.get("name"))].append(j)
    rows = []
    for cj in objects(cx.snap, "cronjobs"):
        md, sp, st = cj["metadata"], cj.get("spec") or {}, cj.get("status") or {}
        ns = md["namespace"]
        jt = (sp.get("jobTemplate") or {}).get("spec") or {}
        interval = _cron_interval_h(sp.get("schedule"))
        last_ok = parse_ts(st.get("lastSuccessfulTime"))
        last_sched = parse_ts(st.get("lastScheduleTime"))
        age_ok = round((now - last_ok).total_seconds() / 3600, 1) if last_ok else None
        myjobs = jobs_by_owner.get((ns, md["name"]), [])
        failed = [j["metadata"]["name"] for j in myjobs if (j.get("status") or {}).get("failed")]
        durs = []
        for j in myjobs:
            js = j.get("status") or {}
            a, b = parse_ts(js.get("startTime")), parse_ts(js.get("completionTime"))
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
# The stores whose data lives nowhere else and so need a dump: the DB_HINT_RE names minus the caches, queues, coordination services and monitoring stores
# (redis, valkey, memcache, kafka, rabbit, nats, pulsar, zookeeper, etcd, prometheus, thanos, loki, mimir, cortex, tempo, victoria, vault), whose data is
# rebuilt, re-ingested or backed up by other means, and minus minio, which is where dumps go (OFFSITE_RE) rather than what is dumped; those are listed as
# excluded so the reader sees them (#169).
BACKUP_TARGET_RE = re.compile(r"(postgres|pgsql|mysql|mariadb|mongo|elastic|opensearch|clickhouse|qdrant|milvus|cassandra|neo4j|influx|timescale|solr|couch|cockroach|tidb|scylla|weaviate|meili|typesense)", re.IGNORECASE)
OFFSITE_RE = re.compile(r"(s3://|s3\.|aws s3|rclone|restic|gs://|gsutil|b2 |backblaze|minio|mc cp|azcopy|rsync .*@|scp |sftp|wal-g|pgbackrest|borg|kopia)", re.IGNORECASE)


def _pv_node(pv: dict) -> str | None:
    """The node a PV is pinned to: a required term with one `In` expression and one value. `kubernetes.io/hostname` is the key the local-path
    provisioner (rancher/local-path-provisioner provisioner.go:526-529@v0.0.37, overridable by the StorageClass parameter `nodeAffinityKey`, :540-542)
    and static local PVs write; any other single-value key is a pin too (#124 K1-6)."""
    for t in (((pv.get("spec") or {}).get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
        exprs = [e for e in t.get("matchExpressions") or [] if e.get("operator", "In") == "In" and len(e.get("values") or []) == 1]
        for e in exprs:
            if e.get("key") == "kubernetes.io/hostname":
                return e["values"][0]
        if len(exprs) == 1 and len(t.get("matchExpressions") or []) == 1:
            return exprs[0]["values"][0]
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
    services: dict[str, list[tuple[str, dict]]] = defaultdict(list)  # ns → [(service name, selector)]
    for s in cx.services:
        sel = (s.get("spec") or {}).get("selector")
        if sel:
            services[s["metadata"]["namespace"]].append((s["metadata"]["name"], sel))
    db_pvcs: dict[str, list[tuple]] = defaultdict(list)  # ns → [(workload, pvc, node)]
    databases: list[dict] = []  # one row per store that needs a dump (BACKUP_TARGET_RE) and mounts a PVC
    excluded: list[str] = []  # stores DB_HINT_RE names that are not dump targets (caches, queues, monitoring)
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        containers = cx.tpl(o).get("containers") or []
        name_and_repos = o["metadata"]["name"] + " " + " ".join(image_repo(c.get("image")) for c in containers)  # the repository, never the tag: umami:postgresql-latest is an app
        if not any(is_db_like(c.get("name"), c.get("image"), o["metadata"]["name"]) for c in containers):
            continue  # the shared gate: a Grafana whose release is called prometheus, an exporter or a sidecar next to a store is not a store
        claims = [v["persistentVolumeClaim"]["claimName"] for v in cx.tpl(o).get("volumes") or [] if v.get("persistentVolumeClaim")]
        for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
            for p in cx.pods_of(kind, o):
                for v in p["spec"].get("volumes") or []:
                    if v.get("persistentVolumeClaim") and v["persistentVolumeClaim"]["claimName"].startswith(vct["metadata"]["name"] + "-"):
                        claims.append(v["persistentVolumeClaim"]["claimName"])
        if not claims:
            continue
        for c in sorted(set(claims)):
            db_pvcs[ns].append((wl_key(kind, o), c, pvc_node.get((ns, c))))
        if not BACKUP_TARGET_RE.search(name_and_repos):
            excluded.append(wl_key(kind, o))
            continue
        labels = cx.tpl_labels(o)
        databases.append(
            {
                "namespace": ns,
                "kind": kind.lower(),
                "name": o["metadata"]["name"],
                "target": wl_key(kind, o),
                "prod": ns in cx.prod,
                "pvcs": sorted(set(claims)),
                "services": sorted(sn for sn, sel in services.get(ns, []) if all(labels.get(k) == v for k, v in sel.items())),
                "backup_cronjobs": [],
                "other_backup_cronjobs_in_namespace": [],
            }
        )
    rows = []
    for cj in objects(cx.snap, "cronjobs"):
        md, sp = cj["metadata"], cj.get("spec") or {}
        ns = md["namespace"]
        pod = (((sp.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
        cmd_text = " ".join(" ".join((c.get("command") or []) + (c.get("args") or [])) + " " + " ".join(str(e.get("value") or "") for e in c.get("env") or []) for c in (pod.get("containers") or []) + (pod.get("initContainers") or []))
        text = cmd_text + " " + " ".join(c.get("image", "") for c in (pod.get("containers") or []) + (pod.get("initContainers") or []))
        if not BACKUP_NAME_RE.search(md["name"] + " " + text[:400]):
            continue
        claims = [v["persistentVolumeClaim"]["claimName"] for v in pod.get("volumes") or [] if v.get("persistentVolumeClaim")]
        host_paths = [v["hostPath"].get("path") for v in pod.get("volumes") or [] if v.get("hostPath")]
        dest_nodes = {pvc_node.get((ns, c)) for c in claims}
        offsite = bool(OFFSITE_RE.search(text))
        src = db_pvcs.get(ns, [])
        src_nodes = {n for _, _, n in src if n}
        same_node = bool(dest_nodes & src_nodes) or (bool(host_paths) and bool(pod.get("nodeSelector") or pod.get("nodeName")))
        # Which database this CronJob dumps: its command, args or env values name the database's Service (the host of pg_dump -h, mysqldump -h, a connection
        # string), the workload itself, or its first pod (<statefulset>-0), as a whole token. A name that is only the prefix of another (app-postgres of
        # app-postgres-mx) does not match (#169). The image is not part of the match (a CronJob running the postgres image would claim a database named
        # postgres), and a user name that equals a sibling's name would (pg_dump -U postgres): the known limit of a token match. The text is not recorded: an env
        # value may be a credential.
        targets_db = []
        for db in databases:
            if db["namespace"] != ns:
                continue
            keys = [*db["services"], db["name"]] + ([f"{db['name']}-0"] if db["kind"] == "statefulset" else [])
            hit = next((k for k in keys if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", cmd_text)), None)  # a dot may precede: pg-0.pg-headless names the Service
            if hit:
                targets_db.append({"target": db["target"], "matched_by": hit})
                if not sp.get("suspend"):
                    db["backup_cronjobs"].append({"name": md["name"], "matched_by": hit})
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "prod": ns in cx.prod,
                "schedule": sp.get("schedule"),
                "suspend": bool(sp.get("suspend")),
                "targets_db": targets_db,
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
    for db in databases:
        own = {b["name"] for b in db["backup_cronjobs"]}
        db["other_backup_cronjobs_in_namespace"] = [{"name": r["name"], "suspend": r["suspend"], "targets_db": [t["target"] for t in r["targets_db"]]} for r in rows if r["namespace"] == db["namespace"] and r["name"] not in own]
    return {
        "rows": rows,
        "count": len(rows),
        "local_only": [r["target"] for r in rows if r["local_only"]],
        "same_node": [r["target"] for r in rows if r["same_node_as_source"]],
        "databases": databases,
        "excluded_stores": sorted(excluded),
        "note": "databases: every store that needs a dump (BACKUP_TARGET_RE) with a PVC, and the backup CronJobs whose command, args or env name its Service, its workload or its first pod; excluded_stores: caches, queues, monitoring stores and MinIO with a PVC, which this check does not ask a dump of",
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
    preempted = sum(event_count(e) for e in ((load_json(cx.snap / "events.json") or {}).get("items") or []) if e.get("reason") == "Preempted")
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
    now = cx.now
    return {
        "probes": _probes(cx),
        "pdbs": _pdbs(cx),
        "graceful": _graceful(cx),
        "placement": _placement(cx),
        "single_node": _single_node(cx),
        "az_volumes": _az_volumes(cx),
        "n_plus_one": _n_plus_one(cx),
        "restarts": _restarts(cx),
        "oom_7d": oom_7d(cx),
        "cronjobs": _cronjobs(cx, now),
        "priority": _priority(cx),
        "backup": _backup_locality(cx),
    }

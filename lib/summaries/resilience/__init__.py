"""Resilience area summary.

Inputs: objects/deployments, statefulsets, daemonsets, pods, nodes, poddisruptionbudgets, priorityclasses, cronjobs, jobs, persistentvolumeclaims, persistentvolumes, services, namespaces,
events.json (Preempted, Unhealthy), inventory (prod_like, karpenter presence, platform).

Output: the `resilience` section of summary.json: probes (per-workload probe kinds, paths, suspicion flags), pdbs (zero allowed disruptions, orphans), graceful (preStop, grace, shell PID1, readiness gate), placement (replica spread over nodes/AZs, spread declarations),
single_node (nodeSelector, nodeName, hostPath pinning), az_volumes (AZ pinned by EBS PVs and node count in that AZ), n_plus_one (allocatable minus the largest node vs the request sum, pods that cannot fit elsewhere),
restarts (top container restarts and causes), cronjobs (policy, last success, active Job count), jobs (failed/completed totals), priority (PriorityClass, prod vs non-prod priority, Preempted). Shape documented in SKILL.md.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from ...foundations.scrub import command_shape
from ...foundations.snapshot import event_count, load_json, objects, parse_ts, taken_at
from ...foundations.workload import eligible_nodes, is_db_like, mounts_pvc, selector_matches, workload_of
from ...foundations.workload import key as wl_key
from .backup import backup_locality
from .capacity import n_plus_one
from .cronjobs import cronjobs
from .oom import node_boot_times, oom_7d

SUSPECT_LIVENESS_RE = re.compile(r"(db|database|mysql|postgres|redis|mongo|kafka|ready|readiness|deps|dependenc|upstream|downstream|elastic|full=true)", re.IGNORECASE)
DB_SELF_PROBE_RE = re.compile(
    r"(pg_isready|mysqladmin|mysql .*-e|redis-cli|valkey-cli|mongosh|mongo .*ping|cqlsh|nodetool|clickhouse-client|rabbitmq-diagnostics|rabbitmqctl|etcdctl endpoint|_cluster/health|minio.*health)", re.IGNORECASE
)  # standard probes that check the DB's own response — not external dependencies (seen: 6 mysql false positives)


class Ctx:
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


def _probes(cx: Ctx) -> dict:
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
                path = (pr.get("httpGet") or {}).get("path") or (
                    " ".join((pr.get("exec") or {}).get("command") or []) or None if typ == "exec" else None
                )  # None for an exec probe whose command the run did not keep (no app-settings): its text cannot be read for a dependency
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


def _pdbs(cx: Ctx) -> dict:
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


def _graceful(cx: Ctx) -> dict:
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
        shell = [c["name"] for c in conts if command_shape(c)["shell"]]
        pvc_names = [v["persistentVolumeClaim"]["claimName"] for v in tpl.get("volumes") or [] if v.get("persistentVolumeClaim")]
        rwo = [c for c in pvc_names if "ReadWriteMany" not in (pvc_modes.get((o["metadata"]["namespace"], c)) or ["ReadWriteOnce"])]
        ext = sorted({k for c in conts for k in ((c.get("resources") or {}).get("limits") or {}) if "/" in k and not k.startswith("hugepages")})
        reasons = ([f"RWO PVC {rwo}"] if rwo else []) + ([f"extended resource {ext}"] if ext else [])
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


def _placement(cx: Ctx) -> dict:
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
                "prod_workloads": sorted(prod_wl_by_node[nd]),
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


def _single_node(cx: Ctx) -> dict:
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


def _az_volumes(cx: Ctx) -> dict:
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


def _restarts(cx: Ctx) -> dict:
    boot = node_boot_times(cx)
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
        "rows": rows,
        "by_cause": dict(Counter(r["cause"] for r in rows)),
        "crashloop_now": [f"{r['namespace']}/{r['pod']}" for r in rows if r["crashloop"]],
        "oom_last": oom_last,
        "oom_recent_7d": sorted(k for k, v in oom_last.items() if (v["age_days"] or 0) <= 7),
    }


def _priority(cx: Ctx) -> dict:
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
        "inversion": inversion,
        "preempted_events": preempted,
        "no_user_classes_with_prod": bool(prod_pods) and not user_pcs,
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    cx = Ctx(snap, inv)
    now = cx.now
    return {
        "probes": _probes(cx),
        "pdbs": _pdbs(cx),
        "graceful": _graceful(cx),
        "placement": _placement(cx),
        "single_node": _single_node(cx),
        "az_volumes": _az_volumes(cx),
        "n_plus_one": n_plus_one(cx),
        "restarts": _restarts(cx),
        "oom_7d": oom_7d(cx),
        "cronjobs": cronjobs(cx, now),
        "priority": _priority(cx),
        "backup": backup_locality(cx),
    }

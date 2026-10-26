"""Karpenter controller summary (collectors/karpenter).

NodePool/NodeClaim state, latency, expiry, DisruptionBlocked and budgets belong to the scaling section (summary.scaling.karpenter). This module covers the controller itself and its metrics:
Deployment (replicas, node spread, PDB, version, env: feature gates, batching, interruption queue), the ServiceAccount's IRSA/Pod Identity, EC2NodeClass (AMI family, AMI selector, IMDS, root volume, role, conditions),
metrics/pod/karpenter/<pod>.prom (leader, pool usage/limit, NodeClaim create/terminate/disruption reasons, spot interruption messages and actions, cloud API errors and latency, cluster state sync, consistency errors, pod startup time, disruption budget allowance, reconcile errors).
Output: the `karpenterctl` section of summary.json. Shape documented in SKILL.md.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import load_json, objects


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _r(x, n=3):
    return None if x is None else round(x, n)


def _q(v) -> float:
    s = str(v or 0)
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
    if s.endswith("m"):
        return float(s[:-1]) / 1000
    for u, mul in units.items():
        if s.endswith(u):
            return float(s[: -len(u)]) * mul
    try:
        return float(s)
    except ValueError:
        return 0.0


def _pod_metrics(snap: Path) -> dict:
    d = snap / "metrics" / "pod" / "karpenter"
    pods = {}
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        sg, lb = pm["single"], pm["labeled"]
        leader = any(v >= 1 for _, v in lb.get("leader_election_master_status", [])) or sg.get("leader_election_master_status", 0) >= 1

        def by(name, key):
            out: dict = {}
            for labels, v in lb.get(name, []):
                k = labels.get(key) or "-"
                out[k] = out.get(k, 0) + v
            return out

        usage = {}
        for labels, v in lb.get("karpenter_nodepool_usage", []):
            usage.setdefault(labels.get("nodepool"), {})[labels.get("resource_type")] = v
        limit = {}
        for labels, v in lb.get("karpenter_nodepool_limit", []):
            limit.setdefault(labels.get("nodepool"), {})[labels.get("resource_type")] = v
        pool_ratio = {}
        for pool, res in usage.items():
            for rt, u in res.items():
                lim = (limit.get(pool) or {}).get(rt)
                if lim:
                    pool_ratio[f"{pool}/{rt}"] = round(u / lim, 3)
        cp_err = {}
        for labels, v in lb.get("karpenter_cloudprovider_errors_total", []):
            k = f"{labels.get('method')}" + (f"({labels.get('controller')})" if labels.get("controller") else "")
            cp_err[k] = cp_err.get(k, 0) + int(v)
        recon_err = {k: int(v) for k, v in by("controller_runtime_reconcile_errors_total", "controller").items() if v > 0}
        startup_sum = sum(v for _, v in lb.get("karpenter_pods_startup_time_seconds_sum", [])) or sg.get("karpenter_pods_startup_time_seconds_sum", 0)
        startup_cnt = sum(v for _, v in lb.get("karpenter_pods_startup_time_seconds_count", [])) or sg.get("karpenter_pods_startup_time_seconds_count", 0)
        term_sum = sum(v for _, v in lb.get("karpenter_nodes_termination_time_seconds_sum", [])) or sg.get("karpenter_nodes_termination_time_seconds_sum", 0)
        term_cnt = sum(v for _, v in lb.get("karpenter_nodes_termination_time_seconds_count", [])) or sg.get("karpenter_nodes_termination_time_seconds_count", 0)
        synced = sg.get("karpenter_cluster_state_synced")
        if synced is None:
            vals = [v for _, v in lb.get("karpenter_cluster_state_synced", [])]
            synced = vals[0] if vals else None
        budgets = {}
        for labels, v in lb.get("karpenter_disruption_budgets_allowed_disruptions", []):
            budgets[f"{labels.get('nodepool')}/{labels.get('reason') or '-'}"] = int(v)
        pods[f.stem] = {
            "leader": leader,
            "process_start": sg.get("process_start_time_seconds"),
            "rss_mb": round(sg.get("process_resident_memory_bytes", 0) / 1024**2) if sg.get("process_resident_memory_bytes") else None,
            "nodepool_usage": usage,
            "nodepool_limit": limit,
            "nodepool_usage_ratio": pool_ratio,
            "nodeclaims_created_by_reason": {k: int(v) for k, v in by("karpenter_nodeclaims_created", "reason").items()},
            "nodeclaims_terminated_by_reason": {k: int(v) for k, v in by("karpenter_nodeclaims_terminated", "reason").items()},
            "nodeclaims_disrupted_by_reason": {k: int(v) for k, v in by("karpenter_nodeclaims_disrupted", "reason").items()},
            "interruption_messages_by_type": {k: int(v) for k, v in by("karpenter_interruption_received_messages", "message_type").items()},
            "interruption_actions": {k: int(v) for k, v in by("karpenter_interruption_actions_performed", "action_type").items()},
            "interruption_deleted_messages": int(sg.get("karpenter_interruption_deleted_messages", 0)),
            "cloudprovider_errors": cp_err,
            "cloudprovider_errors_total": sum(cp_err.values()),
            "reconcile_errors": recon_err,
            "reconcile_errors_total": sum(recon_err.values()),
            "cluster_state_synced": (synced == 1) if synced is not None else None,
            "consistency_errors": int(sum(v for _, v in lb.get("karpenter_consistency_errors", [])) + sg.get("karpenter_consistency_errors", 0)) if ("karpenter_consistency_errors" in sg or lb.get("karpenter_consistency_errors")) else None,
            "consistency_errors_by_check": {k: int(v) for k, v in by("karpenter_consistency_errors", "check").items()},
            "pods_startup_avg_s": _r(startup_sum / startup_cnt, 1) if startup_cnt else None,
            "pods_startup_count": int(startup_cnt),
            "node_termination_avg_s": _r(term_sum / term_cnt, 1) if term_cnt else None,
            "disruption_eligible_nodes": {k: int(v) for k, v in by("karpenter_disruption_eligible_nodes", "method").items()},
            "disruption_budgets_allowed": budgets,
            "disruption_actions": {k: int(v) for k, v in by("karpenter_disruption_actions_performed_total", "method").items()},
            "nodes_disrupted_total": {k: int(v) for k, v in by("karpenter_disruption_nodes_disrupted_total", "method").items()},
            "scheduling_queue_depth": sg.get("karpenter_provisioner_scheduling_queue_depth"),
        }
    return pods


def analyze(snap: Path, inv: dict | None, scaling: dict | None = None) -> dict:
    inv = inv or {}
    dep = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] == "karpenter"), None)
    pools = objects(snap, "nodepools.karpenter.sh")
    if not dep and not pools:
        return {"present": False}
    controller = {"present": dep is not None}
    if dep:
        sp, st = dep.get("spec") or {}, dep.get("status") or {}
        tpl = (sp.get("template") or {}).get("spec") or {}
        c0 = (tpl.get("containers") or [{}])[0]
        env = {e["name"]: e.get("value") for e in (c0.get("env") or []) if "value" in e}
        sel = (sp.get("selector") or {}).get("matchLabels") or {}
        by_node = Counter(
            p["spec"].get("nodeName")
            for p in objects(snap, "pods")
            if p["metadata"]["namespace"] == dep["metadata"]["namespace"] and all((p["metadata"].get("labels") or {}).get(k) == v for k, v in sel.items()) and (p.get("status") or {}).get("phase") == "Running"
        )
        pdbs = [
            b["metadata"]["name"]
            for b in objects(snap, "poddisruptionbudgets.policy")
            if b["metadata"]["namespace"] == dep["metadata"]["namespace"] and (b.get("spec") or {}).get("selector") and all(((b.get("spec") or {}).get("selector") or {}).get("matchLabels", {}).get(k) == v for k, v in sel.items())
        ]
        sa_name = tpl.get("serviceAccountName") or "karpenter"
        sa = next((s for s in objects(snap, "serviceaccounts") if s["metadata"]["namespace"] == dep["metadata"]["namespace"] and s["metadata"]["name"] == sa_name), None)
        irsa = ((sa or {}).get("metadata") or {}).get("annotations", {}).get("eks.amazonaws.com/role-arn")
        pia = load_json(snap / "aws" / "pod-identity-associations.json") or {}
        pod_identity = any(a.get("serviceAccount") == sa_name for a in (pia.get("associations") or []))
        gates = dict(kv.split("=", 1) for kv in (env.get("FEATURE_GATES") or "").split(",") if "=" in kv)
        nodes_karp = {n["name"] for n in (inv.get("nodes") or {}).get("nodes") or [] if n.get("nodepool")}
        controller.update(
            {
                "namespace": dep["metadata"]["namespace"],
                "replicas": sp.get("replicas"),
                "ready": st.get("readyReplicas") or 0,
                "version": _ver(c0.get("image")),
                "image": c0.get("image"),
                "pods_by_node": dict(by_node),
                "all_same_node": (sp.get("replicas") or 0) >= 2 and len(by_node) == 1,
                "on_karpenter_node": [n for n in by_node if n in nodes_karp],
                "pdb": pdbs,
                "has_pdb": bool(pdbs),
                "anti_affinity": bool((tpl.get("affinity") or {}).get("podAntiAffinity")),
                "priority_class": tpl.get("priorityClassName"),
                "service_account": sa_name,
                "irsa_role": irsa,
                "pod_identity": pod_identity,
                "has_dedicated_role": bool(irsa or pod_identity),
                "env": {k: v for k, v in env.items() if k in ("CLUSTER_NAME", "INTERRUPTION_QUEUE", "FEATURE_GATES", "BATCH_MAX_DURATION", "BATCH_IDLE_DURATION", "LOG_LEVEL", "VM_MEMORY_OVERHEAD_PERCENT", "RESERVED_ENIS", "METRICS_PORT")},
                "feature_gates": gates,
                "drift_enabled": gates.get("Drift", "true").lower() != "false",
                "spot_to_spot_consolidation": gates.get("SpotToSpotConsolidation", "false").lower() == "true",
                "interruption_queue": env.get("INTERRUPTION_QUEUE"),
                "resources": c0.get("resources") or {},
            }
        )
    # --- EC2NodeClass
    classes = []
    for c in objects(snap, "ec2nodeclasses.karpenter.k8s.aws"):
        sp = c.get("spec") or {}
        md = sp.get("metadataOptions") or {}
        root = next(((b.get("ebs") or {}) for b in (sp.get("blockDeviceMappings") or [])), {})
        ami_terms = sp.get("amiSelectorTerms") or []
        conds = {x.get("type"): x.get("status") for x in (c.get("status") or {}).get("conditions") or []}
        classes.append(
            {
                "name": c["metadata"]["name"],
                "ami_family": sp.get("amiFamily"),
                "ami_selector": ami_terms,
                "ami_alias": next((t.get("alias") for t in ami_terms if t.get("alias")), None),
                "ami_pinned": any(t.get("id") or (t.get("alias") and "@latest" not in str(t.get("alias"))) for t in ami_terms),
                "role": sp.get("role"),
                "instance_profile": sp.get("instanceProfile"),
                "imds_hop_limit": md.get("httpPutResponseHopLimit"),
                "imds_tokens": md.get("httpTokens"),
                "root_volume_gb": _q(root.get("volumeSize")) / 1024**3 if root.get("volumeSize") else None,
                "root_volume_type": root.get("volumeType"),
                "root_encrypted": root.get("encrypted"),
                "detailed_monitoring": sp.get("detailedMonitoring"),
                "user_data": bool(sp.get("userData")),
                "ready": conds.get("Ready") == "True",
                "conditions": conds,
                "subnet_selector": sp.get("subnetSelectorTerms"),
                "sg_selector": sp.get("securityGroupSelectorTerms"),
            }
        )
    pools_using = Counter(((p.get("spec") or {}).get("template") or {}).get("spec", {}).get("nodeClassRef", {}).get("name") for p in pools)
    for c in classes:
        c["nodepools"] = pools_using.get(c["name"], 0)
    pm = _pod_metrics(snap)
    leader = next((p for p, d in pm.items() if d["leader"]), None) or (max(pm, key=lambda p: pm[p]["pods_startup_count"] + sum(pm[p]["nodeclaims_created_by_reason"].values())) if pm else None)
    ld = pm.get(leader) if leader else None
    sk = (scaling or {}).get("karpenter") or {}
    summary = {
        "present": True,
        "version": controller.get("version") or sk.get("version"),
        "k8s_supported": sk.get("k8s_supported"),
        "replicas": controller.get("replicas"),
        "ready": controller.get("ready"),
        "all_same_node": controller.get("all_same_node", False),
        "on_karpenter_node": controller.get("on_karpenter_node", []),
        "has_pdb": controller.get("has_pdb", False),
        "has_dedicated_role": controller.get("has_dedicated_role", False),
        "irsa_role": controller.get("irsa_role"),
        "interruption_queue": controller.get("interruption_queue"),
        "drift_enabled": controller.get("drift_enabled"),
        "spot_to_spot_consolidation": controller.get("spot_to_spot_consolidation"),
        "feature_gates": controller.get("feature_gates"),
        "ec2nodeclasses": len(classes),
        "ami_families": sorted({c["ami_family"] for c in classes if c["ami_family"]}),
        "classes_al2": [c["name"] for c in classes if (c["ami_family"] or "").upper() == "AL2"],
        "classes_ami_unpinned": [c["name"] for c in classes if not c["ami_pinned"]],
        "classes_imds_hop_gt1": [c["name"] for c in classes if (c["imds_hop_limit"] or 1) > 1],
        "classes_imds_tokens_optional": [c["name"] for c in classes if c["imds_tokens"] and c["imds_tokens"] != "required"],
        "classes_root_small": [c["name"] for c in classes if c["root_volume_gb"] is not None and c["root_volume_gb"] < 50],
        "classes_root_unencrypted": [c["name"] for c in classes if c["root_encrypted"] is not True],
        "classes_not_ready": [c["name"] for c in classes if not c["ready"]],
        "root_volume_gb": {c["name"]: c["root_volume_gb"] for c in classes},
        "metrics_available": bool(pm),
        "leader_found": leader is not None,
        "leader_process_start": (ld or {}).get("process_start"),
        "leader_uptime_days": round((__import__("time").time() - (ld or {}).get("process_start")) / 86400, 1) if (ld or {}).get("process_start") else None,
        "nodepool_usage_ratio": (ld or {}).get("nodepool_usage_ratio") or {},
        "nodepool_usage_max": max(((ld or {}).get("nodepool_usage_ratio") or {}).values(), default=None),
        "nodeclaims_created_by_reason": (ld or {}).get("nodeclaims_created_by_reason"),
        "nodeclaims_terminated_by_reason": (ld or {}).get("nodeclaims_terminated_by_reason"),
        "nodeclaims_disrupted_by_reason": (ld or {}).get("nodeclaims_disrupted_by_reason"),
        "interruption_messages_by_type": (ld or {}).get("interruption_messages_by_type"),
        "interruption_actions": (ld or {}).get("interruption_actions"),
        "interruption_messages_total": sum(((ld or {}).get("interruption_messages_by_type") or {}).values()),
        "cloudprovider_errors_total": (ld or {}).get("cloudprovider_errors_total"),
        "cloudprovider_errors": (ld or {}).get("cloudprovider_errors"),
        "reconcile_errors_total": (ld or {}).get("reconcile_errors_total"),
        "reconcile_errors": (ld or {}).get("reconcile_errors"),
        "cluster_state_synced": (ld or {}).get("cluster_state_synced"),
        "consistency_errors": (ld or {}).get("consistency_errors"),
        "pods_startup_avg_s": (ld or {}).get("pods_startup_avg_s"),
        "pods_startup_count": (ld or {}).get("pods_startup_count"),
        "node_termination_avg_s": (ld or {}).get("node_termination_avg_s"),
        "disruption_budgets_allowed": (ld or {}).get("disruption_budgets_allowed"),
        "nodes_disrupted_total": (ld or {}).get("nodes_disrupted_total"),
        "nodepools": len(pools),
        "nodepools_without_limits": [p["metadata"]["name"] for p in pools if not ((p.get("spec") or {}).get("limits"))],
    }
    return {
        "present": True,
        "controller": controller,
        "ec2nodeclasses": classes,
        "metrics": {"available": bool(pm), "leader_pod": leader, "pods": pm},
        "summary": summary,
        "note": "Metrics accumulate since the leader process started. Pool usage/limit comes from karpenter_nodepool_usage/limit (leader only). NodePool/NodeClaim details are in summary.scaling.karpenter",
    }

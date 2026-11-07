"""Scaling area summary.

Inputs: objects/horizontalpodautoscalers.autoscaling.json, scaledobjects.keda.sh.json, scaledjobs.keda.sh.json, apiservices.apiregistration.k8s.io.json,
nodepools.karpenter.sh.json, nodeclaims.karpenter.sh.json, deployments.json (Karpenter's INTERRUPTION_QUEUE), events.json (DisruptionBlocked reasons),
logs/pods/karpenter/*.log (launched/registered/initialized nodeclaim timestamps, "disrupting via", failures), metrics/hpa_*.json and pod_pending_seconds.json.

Output is the `scaling` section of summary.json (shape in SKILL.md). The first-pass scaling.* checks iterate the hpa/keda/karpenter lists here via `each`.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import versions
from .durations import go_duration_s
from .events import count_of
from .snapshot import component_logs_aggregate, component_logs_removed, load_json, objects, parse_ts, taken_at

# The Karpenter disruption line, in the three shapes it has had (references/sources.md, "lib/scaling.py Karpenter log facts"; kubernetes-sigs/karpenter):
# - through 0.37: `"message":"disrupting via <reason> <decision>, terminating N nodes (M pods) <node>/<type>/<capacity>, …"` (pkg/controllers/disruption/controller.go:188@v0.37.0,
#   Command.String() types.go:184-194@v0.37.0);
# - 1.0.0 to 1.2.x: `"message":"disrupting nodeclaim(s) via <decision>, terminating N nodes (M pods) …"` with the reason as a field (controller.go:188@v1.0.0, types.go:141-151@v1.0.0);
# - from 1.3.0: `"message":"disrupting node(s)"` with structured values `decision`, `disrupted-node-count`, `pod-count`, `disrupted-nodes` (a list of {Node, NodeClaim, instance-type,
#   capacity-type}) and the reason as a `reason` field (controller.go:205@v1.3.0, queue.go:295@v1.6.0; types.go:143-176@v1.3.0, :167-200@v1.6.0) or, at 1.15.1, as the first
#   token of the `command` field `<reason>/<id>: <decision>: nodepools=[…]: [nodes] …` (queue.go:388-390@v1.15.1, types.go:350-380,449-487@v1.15.1).
_DISRUPT_037 = re.compile(r'"message":"disrupting via (\w+) (\w+), terminating (\d+) nodes \((\d+) pods\) ([^"]+)"')
_DISRUPT_10 = re.compile(r'"message":"disrupting nodeclaim\(s\) via (\w+), terminating (\d+) nodes \((\d+) pods\) ([^"]+)"')
_DISRUPT_13 = re.compile(r'"message":"disrupting node\(s\)"')
# The launch failure: the lifecycle controller's own ERROR line (`launching nodeclaim`/`creating nodeclaim`, pkg/controllers/nodeclaim/lifecycle/launch.go:84-86,100,103@v0.37.0,
# :99,113,132@v1.15.1), controller-runtime's `"msg":"Reconciler error"` whose `"error"` starts `launching nodeclaim, creating instance, …` for IAM and parameter failures, and the
# EC2 codes the provider relays (aws/karpenter-provider-aws pkg/providers/instance/instance.go@v0.37.0, @v1.15.1). The level is spelled ERROR at every version
# (pkg/operator/logging/logging.go:64-74@v0.37.0, :42-71@v1.15.1, CapitalLevelEncoder).
_LAUNCH_FAIL = re.compile(r'"level":"ERROR".*(launching|creating) nodeclaim|"error":"launching nodeclaim,|InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity')
_LAUNCH_CODE = re.compile(r"(InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity)")
_LAUNCH_PHRASE = re.compile(r"(launching nodeclaim|creating nodeclaim)")


def disruption_line(line: str) -> tuple[str, str, int, int, str] | None:
    """(reason, decision, nodes, pods, node names) of a Karpenter disruption log line in any of its three shapes, else None."""
    m = _DISRUPT_037.search(line)
    if m:
        return m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
    m = _DISRUPT_10.search(line)
    if m:
        r = re.search(r'"reason":"(\w+)"', line)
        return (r.group(1) if r else "?"), m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    if _DISRUPT_13.search(line):
        r = re.search(r'"reason":"(\w+)"', line) or re.search(r'"command":"(\w+)/', line)
        d = re.search(r'"decision":"(\w+)"', line)
        n = re.search(r'"disrupted-node-count":(\d+)', line)
        p = re.search(r'"pod-count":(\d+)', line)
        names = ", ".join(re.findall(r'"Node":\{"name":"([^"]+)"', line))  # only disrupted-nodes entries carry a Node
        # 1.15.1 writes the reason capitalised inside `command` (`DisruptionReason` constants, pkg/apis/v1/nodepool.go:184-189@v1.15.1); 1.3 to 1.6 lower-case it
        return (r.group(1).lower() if r else "?"), (d.group(1).lower() if d else "?"), int(n.group(1)) if n else 0, int(p.group(1)) if p else 0, names
    return None


def launch_failure_key(line: str) -> str | None:
    """The failure kind of a Karpenter launch-failure log line (the EC2 code or the controller phrase), else None."""
    if _LAUNCH_FAIL.search(line):
        m = _LAUNCH_CODE.search(line) or _LAUNCH_PHRASE.search(line)  # the EC2 code names the cause; the controller phrase only says a launch failed
        return m.group(1) if m else None
    return None


def _dur_h(s: str | None) -> float | None:
    """'720h' '30m' '20m0s' -> hours; None for `Never`, empty or zero. For Karpenter expireAfter/consolidateAfter (lib/durations)."""
    secs = go_duration_s(s)
    return round(secs / 3600, 3) if secs else None


def _metric_map(snap: Path, qid: str, keys: tuple[str, ...]) -> dict[tuple, float]:
    m = load_json(snap / "metrics" / f"{qid}.json")
    out = {}
    for s in (m or {}).get("result") or []:
        lab = s.get("metric") or {}
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out[tuple(lab.get(k) for k in keys)] = float(s["value"][1])
    return out


# ---------- HPA ----------


def _hpa(snap: Path, inv: dict | None, now: _dt.datetime) -> dict:
    items = objects(snap, "horizontalpodautoscalers.autoscaling")
    prod = set(((inv or {}).get("namespaces") or {}).get("prod_like") or [])
    at_max = _metric_map(snap, "hpa_at_max_ratio_15d", ("namespace", "horizontalpodautoscaler"))
    at_min = _metric_map(snap, "hpa_at_min_ratio_15d", ("namespace", "horizontalpodautoscaler"))
    changes = _metric_map(snap, "hpa_desired_changes_7d", ("namespace", "horizontalpodautoscaler"))
    rows = []
    for h in items:
        md, sp, st = h["metadata"], h.get("spec") or {}, h.get("status") or {}
        ns, name = md["namespace"], md["name"]
        ref = sp.get("scaleTargetRef") or {}
        mtypes = []
        for m in sp.get("metrics") or []:
            t = m.get("type")
            if t == "Resource":
                mtypes.append((m.get("resource") or {}).get("name") or "resource")
            elif t == "External":
                mtypes.append("external:" + ((m.get("external") or {}).get("metric") or {}).get("name", "?")[:40])
            elif t in ("Pods", "Object"):
                mtypes.append(t.lower() + ":" + (((m.get(t.lower()) or {}).get("metric") or {}).get("name") or "?")[:40])
            else:
                mtypes.append(str(t))
        conds = {c.get("type"): (c.get("status"), c.get("reason"), (c.get("message") or "")[:160]) for c in st.get("conditions") or []}
        keda_owned = name.startswith("keda-hpa-") or any((o.get("kind") == "ScaledObject") for o in md.get("ownerReferences") or [])
        cur_util = None
        for cm in st.get("currentMetrics") or []:
            r = (cm.get("resource") or {}).get("current") or {}
            if (cm.get("resource") or {}).get("name") == "cpu" and r.get("averageUtilization") is not None:
                cur_util = r["averageUtilization"]
        tgt_util = next((((m.get("resource") or {}).get("target") or {}).get("averageUtilization") for m in sp.get("metrics") or [] if m.get("type") == "Resource" and (m.get("resource") or {}).get("name") == "cpu"), None)
        beh = sp.get("behavior") or {}
        mn, mx = sp.get("minReplicas", 1), sp.get("maxReplicas")
        cur, des = st.get("currentReplicas"), st.get("desiredReplicas")
        sa = conds.get("ScalingActive", (None, None, ""))
        last_scale = parse_ts(st.get("lastScaleTime"))
        row = {
            "namespace": ns,
            "name": name,
            "target": f"{ns}/{(ref.get('kind') or 'Deployment').lower()}/{ref.get('name')}",
            "target_kind": ref.get("kind"),
            "target_name": ref.get("name"),
            "min": mn,
            "max": mx,
            "current": cur,
            "desired": des,
            "metric_types": mtypes,
            "cpu_only": mtypes == ["cpu"],
            "has_behavior": bool(beh),
            "scale_down_stabilization_s": ((beh.get("scaleDown") or {}).get("stabilizationWindowSeconds")) if beh else None,
            "scale_up_policies": bool((beh.get("scaleUp") or {}).get("policies")) if beh else False,
            "conditions": {k: {"status": v[0], "reason": v[1]} for k, v in conds.items()},
            "scaling_active": sa[0] == "True",
            "scaling_active_reason": sa[1],
            "scaling_active_message": sa[2],
            "keda_owned": keda_owned,
            "prod": ns in prod,
            "current_cpu_utilization": cur_util,
            "target_cpu_utilization": tgt_util,
            "at_max_now": (cur is not None and mx is not None and cur >= mx),
            "at_min_now": (cur is not None and cur <= mn),
            "min_eq_max": mn == mx,
            "at_max_ratio_15d": at_max.get((ns, name)),
            "at_min_ratio_15d": at_min.get((ns, name)),
            "desired_changes_7d": changes.get((ns, name)),
            "last_scale_time": st.get("lastScaleTime"),
            "days_since_last_scale": round((now - last_scale).total_seconds() / 86400, 1) if last_scale else None,
        }
        # Judgement aid: for a KEDA-owned HPA, ScalingDisabled is normal while the ScaledObject is inactive (Active False), so it is not counted as inactive
        row["scaling_inactive"] = (not row["scaling_active"]) and not keda_owned
        row["never_scaled_15d"] = row["at_min_ratio_15d"] is not None and row["at_min_ratio_15d"] >= 0.99 and mx and mx > mn
        rows.append(row)
    rows.sort(key=lambda r: (not r["scaling_inactive"], -(r["at_max_ratio_15d"] or 0), r["namespace"], r["name"]))
    return {
        "count": len(rows),
        "rows": rows,
        "counts": {
            "cpu_only": sum(r["cpu_only"] for r in rows),
            "with_behavior": sum(r["has_behavior"] for r in rows),
            "keda_owned": sum(r["keda_owned"] for r in rows),
            "scaling_inactive": sum(r["scaling_inactive"] for r in rows),
            "at_max_now": sum(r["at_max_now"] for r in rows),
            "min_eq_max": sum(r["min_eq_max"] for r in rows),
            "never_scaled_15d": sum(bool(r["never_scaled_15d"]) for r in rows),
            "prod": sum(r["prod"] for r in rows),
        },
        "metrics_available": bool(at_max or at_min or changes),
        # If every HPA in this namespace has sat at min for 15 days with CPU below half the target, a missing HPA in the same namespace is not urgent
        "idle_namespaces": sorted(
            {
                ns
                for ns in {r["namespace"] for r in rows}
                if all(
                    r["never_scaled_15d"] and (r["current_cpu_utilization"] is None or r["target_cpu_utilization"] is None or r["current_cpu_utilization"] < r["target_cpu_utilization"] / 2)
                    for r in rows
                    if r["namespace"] == ns and not r["keda_owned"]
                )
                and any(r["namespace"] == ns and not r["keda_owned"] for r in rows)
            }
        ),
    }


# ---------- KEDA ----------


def _keda(snap: Path) -> dict:
    sos = objects(snap, "scaledobjects.keda.sh")
    sjs = objects(snap, "scaledjobs.keda.sh")
    errors = _metric_map(snap, "keda_scaler_errors_24h", ("namespace", "scaledObject"))
    rows = []
    for s in sos:
        md, sp, st = s["metadata"], s.get("spec") or {}, s.get("status") or {}
        conds = {c.get("type"): (c.get("status"), c.get("reason"), (c.get("message") or "")[:160]) for c in st.get("conditions") or []}
        rows.append(
            {
                "namespace": md["namespace"],
                "name": md["name"],
                "target": f"{md['namespace']}/{sp.get('scaleTargetRef', {}).get('name')}",
                "min": sp.get("minReplicaCount", 0),
                "max": sp.get("maxReplicaCount"),
                "idle": sp.get("idleReplicaCount"),
                "triggers": [t.get("type") for t in sp.get("triggers") or []],
                "polling_s": sp.get("pollingInterval"),
                "cooldown_s": sp.get("cooldownPeriod"),
                "fallback": bool(sp.get("fallback")),
                "ready": conds.get("Ready", (None,))[0] == "True",
                "active": conds.get("Active", (None,))[0] == "True",
                "fallback_active": conds.get("Fallback", (None,))[0] == "True",
                "paused": conds.get("Paused", (None,))[0] == "True",
                "ready_message": conds.get("Ready", (None, None, ""))[2],
                "hpa": st.get("hpaName"),
                "scaler_errors_24h": errors.get((md["namespace"], md["name"])),
            }
        )
    return {
        "present": bool(sos or sjs),
        "scaledobjects": rows,
        "scaledjobs": len(sjs),
        "not_ready": [r["target"] for r in rows if not r["ready"]],
        "fallback_active": [r["target"] for r in rows if r["fallback_active"]],
        "trigger_types": dict(Counter(t for r in rows for t in r["triggers"])),
    }


# ---------- metrics API ----------


def _metrics_api(snap: Path, keda_present: bool) -> dict:
    items = objects(snap, "apiservices.apiregistration.k8s.io")
    want = {"v1beta1.metrics.k8s.io": "metrics-server (CPU/memory HPA, kubectl top)", "v1beta1.external.metrics.k8s.io": "external metrics (KEDA)", "v1beta1.custom.metrics.k8s.io": "custom metrics (prometheus-adapter)"}
    rows, unavailable = {}, []
    found = {a["metadata"]["name"]: a for a in items}
    for name, role in want.items():
        a = found.get(name)
        if not a:
            rows[name] = {"present": False, "available": None, "role": role}
            continue
        c = next((c for c in (a.get("status") or {}).get("conditions") or [] if c.get("type") == "Available"), {})
        ok = c.get("status") == "True"
        rows[name] = {"present": True, "available": ok, "reason": c.get("reason"), "message": (c.get("message") or "")[:160], "role": role, "service": ((a.get("spec") or {}).get("service") or {})}
        if not ok:
            unavailable.append({"name": name, "role": role, "reason": c.get("reason"), "message": (c.get("message") or "")[:160]})
    if not items:
        return {"available": False, "note": "objects/apiservices.apiregistration.k8s.io.json missing", "apis": {}, "unavailable": []}
    if not rows["v1beta1.metrics.k8s.io"]["present"]:
        unavailable.append({"name": "v1beta1.metrics.k8s.io", "role": want["v1beta1.metrics.k8s.io"], "reason": "APIService missing (metrics-server not installed)", "message": ""})
    if keda_present and not rows["v1beta1.external.metrics.k8s.io"]["present"]:
        unavailable.append({"name": "v1beta1.external.metrics.k8s.io", "role": want["v1beta1.external.metrics.k8s.io"], "reason": "KEDA is installed but the APIService is missing", "message": ""})
    return {"available": True, "apis": rows, "unavailable": unavailable}


# ---------- Karpenter ----------


def _load_compat() -> list[dict]:
    """rubric/karpenter-compat.yaml: the Kubernetes minors each Karpenter version supports, read from Karpenter's own generated table (cited per row).
    Raises on a missing or malformed file; the caller records the error."""
    from . import paths, yamlite

    rows = yamlite.load_file(paths.ROOT / "rubric" / "karpenter-compat.yaml") or []
    return [{"karpenter": str(r["karpenter"]), "min_k8s": str(r.get("min_k8s") or ""), "max_k8s": str(r["max_k8s"])} for r in rows if isinstance(r, dict)]


def compat_row(rows: list[dict], kver: str | None) -> dict | None:
    """The row for an installed Karpenter version: a row names a minor ("1.4", every 1.4.x) or a patch ("1.0.5", that patch and the later ones of its
    minor); of the rows of the installed minor, the one with the highest version not above the installed one applies, so "1.0.4" reads the "1.0" row
    and "1.0.6" the "1.0.5" row (Karpenter 1.0.5 extended support to Kubernetes 1.31: compatibility.yaml:57-59@v1.15.1). None when the minor is not in the table."""
    mm = versions.major_minor(kver)
    tv = versions.triple(kver) or ((*mm, 0) if mm else None)
    if not mm:
        return None
    best = None
    for r in rows:
        rmm = versions.major_minor(r["karpenter"])
        if rmm != mm:
            continue
        rt = versions.triple(r["karpenter"]) or (*rmm, 0)
        if rt <= tv and (best is None or rt > best[0]):
            best = (rt, r)
    return best[1] if best else None


def _karpenter(snap: Path, inv: dict | None, now: _dt.datetime) -> dict:
    pools = objects(snap, "nodepools.karpenter.sh")
    claims = objects(snap, "nodeclaims.karpenter.sh")
    comps = (inv or {}).get("components") or {}
    present = bool(pools or claims or (comps.get("karpenter") or {}).get("present"))
    if not present:
        return {"present": False}
    # interruption queue: karpenter Deployment env
    iq = None
    for d in objects(snap, "deployments"):
        if d["metadata"]["name"] == "karpenter":
            for c in (d.get("spec") or {}).get("template", {}).get("spec", {}).get("containers", []):
                for e in c.get("env") or []:
                    if e.get("name") == "INTERRUPTION_QUEUE":
                        iq = e.get("value") or (e.get("valueFrom") and "valueFrom")
    # DisruptionBlocked reasons from events, per node and per pool
    blocked: dict[str, Counter] = defaultdict(Counter)
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        if e.get("reason") != "DisruptionBlocked":
            continue
        io = e.get("involvedObject") or {}
        msg = e.get("message") or ""
        if "do-not-disrupt" in msg:
            kind = "do-not-disrupt pods"
        elif "blocking budget" in msg:
            kind = "budget"
        elif "pdb" in msg.lower() or "poddisruptionbudget" in msg.lower():  # `PDB "ns/name"` at 0.37, `pdb "ns/name" prevents pod evictions` at 1.0, `PodDisruptionBudget=` at 1.15 (#124 O-4)
            kind = "PDB"
        elif "nominated" in msg.lower():  # `Nominated for a pending pod` at 0.37, `state node is nominated` at 1.0, `Node is nominated` at 1.15
            kind = "nominated for pending pods"
        else:
            kind = msg[:60]
        blocked[f"{io.get('kind')}/{io.get('name')}"][kind] += count_of(e)
    pool_rows = []
    claims_by_pool: Counter = Counter(((c["metadata"].get("labels") or {}).get("karpenter.sh/nodepool")) for c in claims)
    for p in pools:
        sp, st = p.get("spec") or {}, p.get("status") or {}
        dis = sp.get("disruption") or {}
        tmpl_spec = (sp.get("template") or {}).get("spec") or {}
        # `expireAfter` is `spec.disruption.expireAfter` at karpenter.sh/v1beta1 (kubernetes-sigs/karpenter pkg/apis/v1beta1/nodepool.go:88@v0.37.0) and `spec.template.spec.expireAfter` at v1 (pkg/apis/v1/nodepool.go:217@v1.0.0, :272@v1.15.1) (#124 O-1)
        expire_after = dis.get("expireAfter") if "expireAfter" in dis else tmpl_spec.get("expireAfter")
        reqs = {r.get("key"): r.get("values") for r in tmpl_spec.get("requirements") or []}
        pool_rows.append(
            {
                "name": p["metadata"]["name"],
                "weight": sp.get("weight"),
                "limits": sp.get("limits") or {},
                "has_limits": bool((sp.get("limits") or {}).get("cpu")),
                "consolidation_policy": dis.get("consolidationPolicy"),
                "consolidate_after": dis.get("consolidateAfter"),
                "expire_after": expire_after,
                "expire_after_h": _dur_h(expire_after),
                "budgets": dis.get("budgets"),
                "capacity_types": reqs.get("karpenter.sh/capacity-type"),
                "archs": reqs.get("kubernetes.io/arch"),
                "instance_categories": reqs.get("karpenter.k8s.aws/instance-category"),
                "nodeclaims": claims_by_pool.get(p["metadata"]["name"], 0),
                "resources": st.get("resources") or {},
                "disruption_blocked": dict(blocked.get(f"NodePool/{p['metadata']['name']}", {})),
            }
        )
    pool_expire = {r["name"]: r["expire_after_h"] for r in pool_rows}
    dnd_by_node: dict[str, list[str]] = {}  # pods with karpenter.sh/do-not-disrupt=true: what blocks replacement of an expired node
    for pod in objects(snap, "pods"):
        if ((pod.get("metadata") or {}).get("annotations") or {}).get("karpenter.sh/do-not-disrupt") == "true" and (pod.get("spec") or {}).get("nodeName"):
            dnd_by_node.setdefault(pod["spec"]["nodeName"], []).append(f"{pod['metadata']['namespace']}/{pod['metadata']['name']}")
    claim_rows = []
    for c in claims:
        md, st = c["metadata"], c.get("status") or {}
        labels = md.get("labels") or {}
        conds = {x.get("type"): x for x in st.get("conditions") or []}
        created = parse_ts(md.get("creationTimestamp"))

        def secs(t):
            tt = parse_ts((conds.get(t) or {}).get("lastTransitionTime")) if (conds.get(t) or {}).get("status") == "True" else None
            return round((tt - created).total_seconds()) if (tt and created) else None

        pool = labels.get("karpenter.sh/nodepool")
        age_h = round((now - created).total_seconds() / 3600, 1) if created else None
        # Karpenter 1.x applies the NodeClaim's own spec.expireAfter, copied from the pool template when the claim is made (kubernetes-sigs/karpenter pkg/apis/v1/nodeclaim.go:75@v1.0.0, :83@v1.15.1;
        # pkg/controllers/nodeclaim/expiration/controller.go:51-54@v1.0.0, :72-75@v1.15.1), so a pool edited later does not move an existing claim; a v1beta1 claim has no expireAfter and the pool's value applies
        spec = c.get("spec") or {}
        exp_h = _dur_h(spec.get("expireAfter")) if "expireAfter" in spec else pool_expire.get(pool)
        claim_rows.append(
            {
                "name": md["name"],
                "pool": pool,
                "node": st.get("nodeName"),
                "instance_type": labels.get("node.kubernetes.io/instance-type"),
                "capacity_type": labels.get("karpenter.sh/capacity-type"),
                "zone": labels.get("topology.kubernetes.io/zone"),
                "arch": labels.get("kubernetes.io/arch"),
                "created": md.get("creationTimestamp"),
                "age_h": age_h,
                "launched_s": secs("Launched"),
                "registered_s": secs("Registered"),
                "initialized_s": secs("Initialized"),
                "ready": (conds.get("Ready") or {}).get("status") == "True",
                # the `Expired` condition exists at v1beta1 only (kubernetes-sigs/karpenter pkg/apis/v1beta1/nodeclaim_status.go:30@v0.37.0); from 1.0.0 expiration is a timer on the NodeClaim
                # (pkg/controllers/nodeclaim/expiration/controller.go:51-54@v1.0.0, :72-75@v1.15.1), so a claim past its expireAfter counts as expired there (#124 O-2)
                "expired": (conds.get("Expired") or {}).get("status") == "True" or (c.get("apiVersion") != "karpenter.sh/v1beta1" and exp_h is not None and age_h is not None and age_h > exp_h),
                "drifted": (conds.get("Drifted") or {}).get("status") == "True",
                "expire_after_h": exp_h,
                "hours_past_expiry": round(age_h - exp_h, 1) if (age_h is not None and exp_h) and age_h > exp_h else None,
                "disruption_blocked": dict(blocked.get(f"NodeClaim/{md['name']}", {})) or dict(blocked.get(f"Node/{st.get('nodeName')}", {})),
                "do_not_disrupt_pods": sorted(dnd_by_node.get(st.get("nodeName") or "", []))[:8],
                "do_not_disrupt_pod_count": len(dnd_by_node.get(st.get("nodeName") or "", [])),
                "allocatable_cpu": (st.get("allocatable") or {}).get("cpu"),
            }
        )
    # logs: 24h launched->initialized latency (including deleted NodeClaims), disruption actions, failures
    lat: dict[str, dict] = defaultdict(dict)
    disruptions: Counter = Counter()
    disrupted_nodes = []
    launch_failures: Counter = Counter()
    created_24h = 0
    for f in sorted((snap / "logs" / "pods" / "karpenter").glob("*.log")) if (snap / "logs" / "pods" / "karpenter").is_dir() else []:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if '"logger":"controller"' not in line and "level=" not in line:
                continue
            ts = parse_ts(line)
            m = re.search(r'"message":"(launched|registered|initialized) nodeclaim".*?"NodeClaim":\{"name":"([^"]+)"', line)
            if m and ts:
                lat[m.group(2)][m.group(1)] = ts
                if m.group(1) == "launched":
                    created_24h += 1
                continue
            d = disruption_line(line)
            if d:
                reason, decision, n_nodes, n_pods, names = d
                disruptions[f"{reason} {decision}"] += n_nodes
                disrupted_nodes.append({"time": ts.isoformat() if ts else None, "reason": f"{reason} {decision}", "nodes": names[:200], "pods": n_pods})
                continue
            key = launch_failure_key(line)
            if key:
                launch_failures[key] += 1
    lat_rows = []
    for name, d in lat.items():
        if "launched" in d and "initialized" in d:
            lat_rows.append(
                {"nodeclaim": name, "launched_to_initialized_s": round((d["initialized"] - d["launched"]).total_seconds()), "launched_to_registered_s": round((d["registered"] - d["launched"]).total_seconds()) if "registered" in d else None}
            )
    lat_vals = sorted(r["launched_to_initialized_s"] for r in lat_rows)
    lat_stats = {"n": len(lat_vals), "p50_s": lat_vals[len(lat_vals) // 2] if lat_vals else None, "max_s": lat_vals[-1] if lat_vals else None, "slowest": sorted(lat_rows, key=lambda r: -r["launched_to_initialized_s"])[:5]}
    cur_lat = sorted(r["initialized_s"] for r in claim_rows if r.get("initialized_s") is not None)
    spot = sum(1 for r in claim_rows if r["capacity_type"] == "spot")
    # Karpenter version vs cluster Kubernetes version (rubric/karpenter-compat.yaml). Input for a proper check rather than a one-line log signature
    kver = None
    for d in objects(snap, "deployments"):
        if d["metadata"]["name"] == "karpenter":
            for c in (d.get("spec") or {}).get("template", {}).get("spec", {}).get("containers", []):
                m = re.search(r":v?(\d+\.\d+\.\d+)", c.get("image", ""))
                if m:
                    kver = m.group(1)
    if not kver:
        for h in load_json(snap / "tools" / "helm-list.json") or []:
            if isinstance(h, dict) and h.get("name") == "karpenter":
                m = re.search(r"(\d+\.\d+\.\d+)", str(h.get("app_version") or h.get("chart") or ""))
                if m:
                    kver = m.group(1)
    k8s_minor = versions.minor_text(((inv or {}).get("cluster") or {}).get("server_version"))
    compat_error = None
    try:
        compat = _load_compat()
    except Exception as e:  # a malformed table must show up in the report's tool notes instead of silently disabling the version check
        compat, compat_error = [], f"{type(e).__name__}: {e}"
    kmm = versions.minor_text(kver) if kver else None
    row = compat_row(compat, kver) if kver else None
    max_k8s = row["max_k8s"] if row else None
    min_k8s = (row.get("min_k8s") or None) if row else None

    supported = None
    if max_k8s and k8s_minor:
        # Both ends of the table are judged: the table's minK8sVersion is as much a boundary as its max (a 1.x Karpenter on a 1.24 cluster is outside it)
        supported = versions.major_minor(k8s_minor) <= versions.major_minor(max_k8s) and (not min_k8s or versions.major_minor(k8s_minor) >= versions.major_minor(min_k8s))
    out = {
        "present": True,
        "interruption_queue": iq,
        "nodepools": pool_rows,
        "nodeclaims": claim_rows,
        "version": kver,
        "k8s_minor": k8s_minor,
        "k8s_max_supported": max_k8s,
        "k8s_min_supported": min_k8s,
        "compat_row": row["karpenter"] if row else None,
        "k8s_supported": supported,
        "version_note": None if supported is not None else ("could not read Karpenter version" if not kver else f"{kmm} not in compatibility table (rubric/karpenter-compat.yaml)"),
        "nodeclaim_count": len(claim_rows),
        "spot_nodeclaims": spot,
        "spot_ratio": round(spot / len(claim_rows), 2) if claim_rows else None,
        "current_latency": {"n": len(cur_lat), "p50_s": cur_lat[len(cur_lat) // 2] if cur_lat else None, "max_s": cur_lat[-1] if cur_lat else None},
        "latency_24h": lat_stats,
        "nodeclaims_launched_24h": created_24h,
        "disruptions_24h": dict(disruptions),
        "disrupted_24h": disrupted_nodes[-20:],
        "launch_failures_24h": dict(launch_failures),
        "expired_not_replaced": [r for r in claim_rows if r["expired"] and (r["hours_past_expiry"] or 0) >= 24],
        "drifted": [r["name"] for r in claim_rows if r["drifted"]],
        "disruption_blocked_total": {k: dict(v) for k, v in blocked.items()},
    }
    if compat_error:
        out["compat_error"] = compat_error
    return out


# ---------- pending ----------


def _pending(snap: Path) -> dict:
    rows = []
    m = load_json(snap / "metrics" / "pod_pending_seconds.json")
    for s in (m or {}).get("result") or []:
        lab = s.get("metric") or {}
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            rows.append({"namespace": lab.get("namespace"), "pod": lab.get("pod"), "pending_s": round(float(s["value"][1]))})
    rows.sort(key=lambda r: -r["pending_s"])
    return {"available": m is not None, "count": len(rows), "rows": rows[:30]}


# Karpenter keys computed from logs/pods/karpenter/*.log. summarize saves them to logs/pods/AGGREGATED.json before deleting the logs; analyze() restores them on a rerun.
KARPENTER_LOG_KEYS = ("latency_24h", "nodeclaims_launched_24h", "disruptions_24h", "disrupted_24h", "launch_failures_24h")


def analyze(snap: Path, inv: dict | None) -> dict:
    now = taken_at(inv)
    keda = _keda(snap)
    hpa = _hpa(snap, inv, now)
    karpenter = _karpenter(snap, inv, now)
    agg = component_logs_aggregate(snap) if component_logs_removed(snap) else None
    if karpenter.get("present") and agg and isinstance(agg.get("karpenter_logs"), dict):
        karpenter.update({k: agg["karpenter_logs"].get(k) for k in KARPENTER_LOG_KEYS if k in agg["karpenter_logs"]})
        karpenter["logs_note"] = "24h latency, launches, disruptions and launch failures read from logs/pods/AGGREGATED.json (raw logs deleted after the first summarize)"
    return {"hpa": hpa, "keda": keda, "metrics_api": _metrics_api(snap, keda["present"]), "karpenter": karpenter, "pending": _pending(snap)}

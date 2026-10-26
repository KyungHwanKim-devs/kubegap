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

from .snapshot import load_json, objects

ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?")


def _ts(s) -> _dt.datetime | None:
    if not s:
        return None
    m = ISO_RE.search(str(s))
    if not m:
        return None
    try:
        d = _dt.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    tz = m.group(2)
    if not tz or tz == "Z":
        return d.replace(tzinfo=_dt.UTC)
    sign = 1 if tz[0] == "+" else -1
    return d.replace(tzinfo=_dt.timezone(sign * _dt.timedelta(hours=int(tz[1:3]), minutes=int(tz[-2:]))))


def _dur_h(s: str | None) -> float | None:
    """'720h' '30m' '20m0s' -> hours. For Karpenter expireAfter/consolidateAfter."""
    if not s or s == "Never":
        return None
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)([hms])", str(s)):
        total += float(num) * {"h": 1, "m": 1 / 60, "s": 1 / 3600}[unit]
    return round(total, 3) if total else None


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
        last_scale = _ts(st.get("lastScaleTime"))
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


def _load_compat() -> dict:
    """rubric/karpenter-compat.yaml: Karpenter minor -> highest supported Kubernetes minor. Raises on a missing or malformed file; the caller records the error."""
    from . import paths, yamlite

    rows = yamlite.load_file(paths.ROOT / "rubric" / "karpenter-compat.yaml") or []
    return {str(r["karpenter"]): str(r["max_k8s"]) for r in rows if isinstance(r, dict)}


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
        elif "PDB" in msg or "PodDisruptionBudget" in msg:
            kind = "PDB"
        elif "Nominated" in msg:
            kind = "nominated for pending pods"
        else:
            kind = msg[:60]
        blocked[f"{io.get('kind')}/{io.get('name')}"][kind] += int(e.get("count") or 1)
    pool_rows = []
    claims_by_pool: Counter = Counter(((c["metadata"].get("labels") or {}).get("karpenter.sh/nodepool")) for c in claims)
    for p in pools:
        sp, st = p.get("spec") or {}, p.get("status") or {}
        dis = sp.get("disruption") or {}
        reqs = {r.get("key"): r.get("values") for r in ((sp.get("template") or {}).get("spec") or {}).get("requirements") or []}
        pool_rows.append(
            {
                "name": p["metadata"]["name"],
                "weight": sp.get("weight"),
                "limits": sp.get("limits") or {},
                "has_limits": bool((sp.get("limits") or {}).get("cpu")),
                "consolidation_policy": dis.get("consolidationPolicy"),
                "consolidate_after": dis.get("consolidateAfter"),
                "expire_after": dis.get("expireAfter"),
                "expire_after_h": _dur_h(dis.get("expireAfter")),
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
        created = _ts(md.get("creationTimestamp"))

        def secs(t):
            tt = _ts((conds.get(t) or {}).get("lastTransitionTime")) if (conds.get(t) or {}).get("status") == "True" else None
            return round((tt - created).total_seconds()) if (tt and created) else None

        pool = labels.get("karpenter.sh/nodepool")
        age_h = round((now - created).total_seconds() / 3600, 1) if created else None
        exp_h = pool_expire.get(pool)
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
                "expired": (conds.get("Expired") or {}).get("status") == "True",
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
            ts = _ts(line)
            m = re.search(r'"message":"(launched|registered|initialized) nodeclaim".*?"NodeClaim":\{"name":"([^"]+)"', line)
            if m and ts:
                lat[m.group(2)][m.group(1)] = ts
                if m.group(1) == "launched":
                    created_24h += 1
                continue
            m = re.search(r'"message":"disrupting via (\w+) (\w+), terminating (\d+) nodes \((\d+) pods\) ([^"]+)"', line)
            if m:
                disruptions[f"{m.group(1)} {m.group(2)}"] += int(m.group(3))
                disrupted_nodes.append({"time": ts.isoformat() if ts else None, "reason": f"{m.group(1)} {m.group(2)}", "nodes": m.group(5)[:200], "pods": int(m.group(4))})
                continue
            if re.search(r'"level":"ERROR".*(launching|creating) nodeclaim|InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity', line):
                key = re.search(r"(InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity|launching nodeclaim|creating nodeclaim)", line).group(1)
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
    k8s_minor = None
    sv = ((inv or {}).get("cluster") or {}).get("server_version") or ""
    m = re.match(r"v?(\d+\.\d+)", sv)
    if m:
        k8s_minor = m.group(1)
    compat_error = None
    try:
        compat = _load_compat()
    except Exception as e:  # a malformed table must show up in the report's tool notes instead of silently disabling the version check
        compat, compat_error = {}, f"{type(e).__name__}: {e}"
    kmm = ".".join(kver.split(".")[:2]) if kver else None
    max_k8s = compat.get(kmm) if kmm else None

    def _minor(v):
        return tuple(int(x) for x in v.split("."))

    supported = None
    if max_k8s and k8s_minor:
        supported = _minor(k8s_minor) <= _minor(max_k8s)
    out = {
        "present": True,
        "interruption_queue": iq,
        "nodepools": pool_rows,
        "nodeclaims": claim_rows,
        "version": kver,
        "k8s_minor": k8s_minor,
        "k8s_max_supported": max_k8s,
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


def analyze(snap: Path, inv: dict | None) -> dict:
    now = _dt.datetime.now(_dt.UTC)
    keda = _keda(snap)
    hpa = _hpa(snap, inv, now)
    return {"hpa": hpa, "keda": keda, "metrics_api": _metrics_api(snap, keda["present"]), "karpenter": _karpenter(snap, inv, now), "pending": _pending(snap)}

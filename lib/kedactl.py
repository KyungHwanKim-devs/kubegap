"""KEDA summary (collectors/keda).

ScaledObject Ready/Active/Fallback, HPA ownership and external.metrics APIService availability belong to the scaling section (summary.scaling.keda, metrics_api). This module covers the KEDA components themselves:
operator, metrics-apiserver and admission-webhooks Deployments (replicas, version, PDB, flags), webhook failurePolicy, existence of the Secrets referenced by TriggerAuthentication/ClusterTriggerAuthentication (names only, via kube_secret_info),
ScaledObject fallback, pollingInterval, cooldown, min 0, last active time, trigger kinds and auth references, ScaledJob, the metrics-apiserver's external metrics API request codes and gRPC results (metrics/pod/keda-metrics-apiserver/*.prom), and whether operator metrics exist.
Output: the `kedactl` section of summary.json. Shape documented in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import load_json, objects


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _deploy(snap: Path, name_sub: str) -> dict:
    d = next((d for d in objects(snap, "deployments") if d["metadata"]["name"].endswith(name_sub) and "keda" in d["metadata"]["name"]), None)
    if not d:
        return {"present": False}
    sp, st = d.get("spec") or {}, d.get("status") or {}
    c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
    args = [str(a) for a in (c0.get("args") or [])]
    sel = (sp.get("selector") or {}).get("matchLabels") or {}
    pdbs = [
        b["metadata"]["name"]
        for b in objects(snap, "poddisruptionbudgets.policy")
        if b["metadata"]["namespace"] == d["metadata"]["namespace"] and (b.get("spec") or {}).get("selector") and all(((b.get("spec") or {}).get("selector") or {}).get("matchLabels", {}).get(k) == v for k, v in sel.items())
    ]
    return {
        "present": True,
        "name": d["metadata"]["name"],
        "namespace": d["metadata"]["namespace"],
        "replicas": sp.get("replicas"),
        "ready": st.get("readyReplicas") or 0,
        "version": _ver(c0.get("image")),
        "args": args,
        "pdb": pdbs,
        "has_pdb": bool(pdbs),
        "resources": c0.get("resources") or {},
    }


def analyze(snap: Path, inv: dict | None, scaling: dict | None = None) -> dict:
    inv = inv or {}
    op = _deploy(snap, "keda-operator")
    ms = _deploy(snap, "metrics-apiserver")
    wh = _deploy(snap, "admission-webhooks")
    sos = objects(snap, "scaledobjects.keda.sh")
    sjs = objects(snap, "scaledjobs.keda.sh")
    if not (op["present"] or ms["present"] or sos):
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    # operator flags
    op_args = op.get("args") or []
    prom_flag = next((a.split("=", 1)[1] for a in op_args if a.startswith("--enable-prometheus-metrics=")), None)
    op["prometheus_metrics_enabled"] = None if prom_flag is None else prom_flag.lower() == "true"
    op["leader_elect"] = any(a.startswith("--leader-elect") for a in op_args)
    # APIService
    apis = next((a for a in objects(snap, "apiservices.apiregistration.k8s.io") if a["metadata"]["name"] == "v1beta1.external.metrics.k8s.io"), None)
    api_cond = {c.get("type"): c.get("status") for c in ((apis or {}).get("status") or {}).get("conditions") or []} if apis else {}
    apiservice = {
        "present": apis is not None,
        "service": ((apis or {}).get("spec") or {}).get("service", {}).get("name"),
        "available": api_cond.get("Available") == "True",
        "keda_owned": "keda" in str(((apis or {}).get("spec") or {}).get("service", {}).get("name", "")),
    }
    # webhooks
    webhooks = []
    for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io"):
        if "keda" in w["metadata"]["name"]:
            for h in w.get("webhooks") or []:
                webhooks.append({"name": h.get("name"), "failure_policy": h.get("failurePolicy"), "timeout_s": h.get("timeoutSeconds")})
    # set of Secret names (kube_secret_info metric — no values)
    secret_names = {(x["metric"].get("namespace"), x["metric"].get("secret")) for x in ((load_json(snap / "metrics" / "secrets_by_name.json") or {}).get("result") or [])}
    secrets_known = bool(secret_names)
    # TriggerAuthentication
    auths = []
    for stem, cluster in (("triggerauthentications.keda.sh", False), ("clustertriggerauthentications.keda.sh", True)):
        for t in objects(snap, stem):
            ns = t["metadata"].get("namespace") or (op.get("namespace") or "keda")
            refs = [(r.get("name"), r.get("key")) for r in ((t.get("spec") or {}).get("secretTargetRef") or [])]
            missing = sorted({n for n, _ in refs if secrets_known and (ns, n) not in secret_names})
            auths.append(
                {
                    "namespace": ns,
                    "name": t["metadata"]["name"],
                    "cluster": cluster,
                    "secret_refs": sorted({n for n, _ in refs}),
                    "secret_missing": missing,
                    "pod_identity": ((t.get("spec") or {}).get("podIdentity") or {}).get("provider"),
                    "env_refs": len((t.get("spec") or {}).get("env") or []),
                    "prod": ns in prod,
                }
            )
    auth_index = {(a["namespace"], a["name"], a["cluster"]) for a in auths}
    # ScaledObject
    so_rows = []
    for x in sos:
        ns, name = x["metadata"]["namespace"], x["metadata"]["name"]
        sp = x.get("spec") or {}
        st = x.get("status") or {}
        conds = {c.get("type"): c.get("status") for c in st.get("conditions") or []}
        last_active = _ts(st.get("lastActiveTime"))
        days_inactive = round((now - last_active).total_seconds() / 86400, 1) if last_active else None
        triggers = sp.get("triggers") or []
        auth_missing = []
        for t in triggers:
            ref = t.get("authenticationRef") or {}
            if ref.get("name"):
                is_cluster = ref.get("kind") == "ClusterTriggerAuthentication"
                if (op.get("namespace") or "keda" if is_cluster else ns, ref["name"], is_cluster) not in auth_index and (ns, ref["name"], is_cluster) not in auth_index:
                    auth_missing.append(ref["name"])
        so_rows.append(
            {
                "namespace": ns,
                "name": name,
                "target": f"{ns}/scaledobject/{name}",
                "prod": ns in prod,
                "scale_target": ((sp.get("scaleTargetRef") or {}).get("name")),
                "min": sp.get("minReplicaCount"),
                "max": sp.get("maxReplicaCount"),
                "polling_interval_s": sp.get("pollingInterval", 30),
                "cooldown_s": sp.get("cooldownPeriod", 300),
                "fallback": bool(sp.get("fallback")),
                "trigger_types": [t.get("type") for t in triggers],
                "triggers": len(triggers),
                "external_triggers": sum(1 for t in triggers if t.get("type") not in ("cpu", "memory")),
                "auth_refs": [(t.get("authenticationRef") or {}).get("name") for t in triggers if t.get("authenticationRef")],
                "auth_missing": auth_missing,
                "ready": conds.get("Ready") == "True",
                "active": conds.get("Active") == "True",
                "fallback_active": conds.get("Fallback") == "True",
                "paused": conds.get("Paused") == "True",
                "last_active": st.get("lastActiveTime"),
                "days_since_active": days_inactive,
                "hpa": st.get("hpaName"),
                "scale_to_zero": (sp.get("minReplicaCount") or 0) == 0,
            }
        )
    # metrics-apiserver metrics
    api_pods = {}
    d = snap / "metrics" / "pod" / "keda-metrics-apiserver"
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        by_code: Counter = Counter()
        by_code_ext: Counter = Counter()
        for labels, v in pm["labeled"].get("apiserver_request_total", []):
            by_code[labels.get("code")] += int(v)
            if "external.metrics" in (labels.get("group") or "") or labels.get("group") == "external.metrics.k8s.io":
                by_code_ext[labels.get("code")] += int(v)
        grpc: Counter = Counter()
        for labels, v in pm["labeled"].get("keda_internal_metricsservice_grpc_client_handled_total", []):
            grpc[labels.get("grpc_code")] += int(v)
        api_pods[f.stem] = {
            "requests_by_code": dict(by_code),
            "external_metrics_requests_by_code": dict(by_code_ext),
            "requests_non_2xx": sum(v for k, v in by_code.items() if not str(k).startswith(("2", "3"))),  # 304 Not Modified is normal
            "grpc_by_code": dict(grpc),
            "grpc_non_ok": sum(v for k, v in grpc.items() if k != "OK"),
            "registered_metrics": pm["single"].get("registered_metrics_total"),
            "rss_mb": round(pm["single"].get("process_resident_memory_bytes", 0) / 1024**2) if pm["single"].get("process_resident_memory_bytes") else None,
        }
    op_pods = {}
    d2 = snap / "metrics" / "pod" / "keda-operator"
    for f in [x for x in sorted(d2.glob("*.prom")) if x.stat().st_size > 0] if d2.is_dir() else []:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        keda_names = sorted({n for n in list(pm["single"]) + list(pm["labeled"]) if n.startswith("keda_")})
        errs = {}
        for labels, v in pm["labeled"].get("keda_scaler_errors_total", []) + pm["labeled"].get("keda_scaler_errors", []):
            k = f"{labels.get('namespace')}/{labels.get('scaledObject')}/{labels.get('scaler')}"
            errs[k] = errs.get(k, 0) + int(v)
        op_pods[f.stem] = {"keda_metric_names": keda_names[:20], "keda_metrics_present": bool(keda_names), "scaler_errors": errs, "scaler_errors_total": sum(errs.values())}
    sk = (scaling or {}).get("keda") or {}
    summary = {
        "present": True,
        "version": op.get("version") or ms.get("version"),
        "operator_replicas": op.get("replicas"),
        "operator_ready": op.get("ready"),
        "metrics_apiserver_replicas": ms.get("replicas"),
        "metrics_apiserver_ready": ms.get("ready"),
        "webhooks_replicas": wh.get("replicas"),
        "webhooks_ready": wh.get("ready"),
        "has_pdb": bool(op.get("has_pdb") or ms.get("has_pdb")),
        "operator_prometheus_metrics": op.get("prometheus_metrics_enabled"),
        "apiservice_available": apiservice["available"],
        "apiservice_keda_owned": apiservice["keda_owned"],
        "webhook_fail_policy": [w["name"] for w in webhooks if w["failure_policy"] == "Fail"],
        "scaledobjects": len(so_rows),
        "scaledjobs": len(sjs),
        "unused": len(so_rows) + len(sjs) == 0,
        "scaledobjects_prod": sum(1 for r in so_rows if r["prod"]),
        "trigger_types": dict(Counter(t for r in so_rows for t in r["trigger_types"])),
        "scale_to_zero": [r["target"] for r in so_rows if r["scale_to_zero"]],
        "never_active_14d": [r["target"] for r in so_rows if (r["days_since_active"] is None or r["days_since_active"] > 14) and not r["paused"]],
        "not_ready": [r["target"] for r in so_rows if not r["ready"]],
        "fallback_active": [r["target"] for r in so_rows if r["fallback_active"]],
        "prod_external_without_fallback": [r["target"] for r in so_rows if r["prod"] and r["external_triggers"] > 0 and not r["fallback"]],
        "auth_missing": [r["target"] for r in so_rows if r["auth_missing"]],
        "secret_missing": [f"{a['namespace']}/{a['name']}: {a['secret_missing']}" for a in auths if a["secret_missing"]],
        "secrets_known": secrets_known,
        "triggerauths": len(auths),
        "polling_interval_min_s": min((r["polling_interval_s"] for r in so_rows), default=None),
        "api_metrics_available": bool(api_pods),
        "api_requests_non_2xx": sum(p["requests_non_2xx"] for p in api_pods.values()),
        "api_grpc_non_ok": sum(p["grpc_non_ok"] for p in api_pods.values()),
        "api_requests_by_code": {k: v for p in api_pods.values() for k, v in p["requests_by_code"].items()},
        "operator_metrics_present": any(p["keda_metrics_present"] for p in op_pods.values()),
        "scaler_errors_total": sum(p["scaler_errors_total"] for p in op_pods.values()) if op_pods else None,
        "scaler_errors_24h_logs": sum((x.get("scaler_errors_24h") or 0) for x in (sk.get("scaledobjects") or [])) if sk else None,
    }
    return {
        "present": True,
        "operator": op,
        "metrics_apiserver": ms,
        "admission_webhooks": wh,
        "apiservice": apiservice,
        "webhooks": webhooks,
        "trigger_authentications": auths,
        "scaledobjects": so_rows,
        "scaledjobs": len(sjs),
        "metrics": {"metrics_apiserver": api_pods, "operator": op_pods},
        "summary": summary,
        "note": "Secret existence is judged by name only via kube_secret_info (no values). Operator metrics are empty when --enable-prometheus-metrics=false",
    }

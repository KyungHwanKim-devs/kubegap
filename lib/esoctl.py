"""External Secrets Operator summary (collector collectors/external-secrets).

Secret values are never read anywhere. The list of ExternalSecrets with Ready False belongs to the security section (security.externalsecret-not-ready). Here we look at the operator itself:
the three Deployments (controller, webhook, cert-controller) replicas/versions/args, webhook failurePolicy, (Cluster)SecretStore provider, auth method (IRSA jwt vs static key Secret) and Ready,
ExternalSecret refreshInterval and refreshTime (refresh lag), creationPolicy/deletionPolicy, store references, PushSecret count, controller metrics (metrics/pod/external-secrets/*.prom:
provider API call success/failure, sync errors, reconcile errors). Result: the `esoctl` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import objects


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _interval_h(s) -> float | None:
    m = re.match(r"^(\d+)([smh])$", str(s or ""))
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return n / 3600 if u == "s" else (n / 60 if u == "m" else float(n))


def _deploy(snap: Path, name: str) -> dict:
    d = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] == name), None)
    if not d:
        return {"present": False}
    sp, st = d.get("spec") or {}, d.get("status") or {}
    c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
    return {
        "present": True,
        "namespace": d["metadata"]["namespace"],
        "replicas": sp.get("replicas"),
        "ready": st.get("readyReplicas") or 0,
        "version": _ver(c0.get("image")),
        "args": [str(a) for a in (c0.get("args") or [])],
        "service_account": ((sp.get("template") or {}).get("spec") or {}).get("serviceAccountName"),
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    ctrl = _deploy(snap, "external-secrets")
    wh = _deploy(snap, "external-secrets-webhook")
    cert = _deploy(snap, "external-secrets-cert-controller")
    ess = objects(snap, "externalsecrets.external-secrets.io")
    if not ctrl["present"] and not ess:
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    ns_eso = ctrl.get("namespace") or "external-secrets"
    sa = next((s for s in objects(snap, "serviceaccounts") if s["metadata"]["namespace"] == ns_eso and s["metadata"]["name"] == (ctrl.get("service_account") or "external-secrets")), None)
    irsa = ((sa or {}).get("metadata") or {}).get("annotations", {}).get("eks.amazonaws.com/role-arn")
    concurrent = next((a.split("=", 1)[1] for a in ctrl.get("args") or [] if a.startswith("--concurrent=")), None)
    # stores
    stores = []
    for stem, cluster in (("clustersecretstores.external-secrets.io", True), ("secretstores.external-secrets.io", False)):
        for s in objects(snap, stem):
            prov = (s.get("spec") or {}).get("provider") or {}
            pname = next(iter(prov.keys()), None)
            pcfg = prov.get(pname) or {}
            auth = pcfg.get("auth") or {}
            if "jwt" in auth or "serviceAccountRef" in json.dumps(auth):
                auth_kind = "irsa/jwt(ServiceAccount)"
            elif "secretRef" in auth:
                auth_kind = "static-key(Secret)"
            elif auth:
                auth_kind = ",".join(sorted(auth.keys()))
            else:
                auth_kind = "none (node role/IMDS or provider default)"
            conds = {c.get("type"): c.get("status") for c in (s.get("status") or {}).get("conditions") or []}
            stores.append(
                {
                    "kind": "ClusterSecretStore" if cluster else "SecretStore",
                    "namespace": s["metadata"].get("namespace"),
                    "name": s["metadata"]["name"],
                    "provider": pname,
                    "auth": auth_kind,
                    "region": pcfg.get("region"),
                    "service": pcfg.get("service"),
                    "ready": conds.get("Ready") == "True",
                    "static_key_secret": ((auth.get("secretRef") or {}).get("accessKeyIDSecretRef") or {}).get("name") if "secretRef" in auth else None,
                }
            )
    # ExternalSecret
    rows = []
    for x in ess:
        ns, name = x["metadata"]["namespace"], x["metadata"]["name"]
        sp = x.get("spec") or {}
        st = x.get("status") or {}
        conds = {c.get("type"): (c.get("status"), c.get("reason"), c.get("message")) for c in st.get("conditions") or []}
        ready = conds.get("Ready", (None, None, None))
        rt = _ts(st.get("refreshTime"))
        interval_h = _interval_h(sp.get("refreshInterval"))
        age_h = round((now - rt).total_seconds() / 3600, 1) if rt else None
        stale = bool(interval_h and age_h is not None and age_h > max(interval_h * 3, 1.0))
        tgt = sp.get("target") or {}
        rows.append(
            {
                "namespace": ns,
                "name": name,
                "target": f"{ns}/externalsecret/{name}",
                "prod": ns in prod,
                "store": ((sp.get("secretStoreRef") or {}).get("name")),
                "store_kind": ((sp.get("secretStoreRef") or {}).get("kind")),
                "refresh_interval": sp.get("refreshInterval"),
                "refresh_interval_h": interval_h,
                "refresh_age_h": age_h,
                "stale": stale,
                "ready": ready[0] == "True",
                "reason": ready[1],
                "message": (ready[2] or "")[:160],
                "creation_policy": tgt.get("creationPolicy", "Owner"),
                "deletion_policy": tgt.get("deletionPolicy", "Retain"),
                "keys": len(sp.get("data") or []),
                "data_from": bool(sp.get("dataFrom")),
                "synced_version": st.get("syncedResourceVersion"),
            }
        )
    # webhook
    webhooks = []
    for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io"):
        if "externalsecret" in w["metadata"]["name"] or "secretstore" in w["metadata"]["name"]:
            for h in w.get("webhooks") or []:
                webhooks.append({"name": h.get("name"), "failure_policy": h.get("failurePolicy"), "timeout_s": h.get("timeoutSeconds")})
    # metrics
    pods = {}
    d = snap / "metrics" / "pod" / "external-secrets"
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        api = {}
        for labels, v in pm["labeled"].get("externalsecret_provider_api_calls_count", []):
            k = f"{labels.get('provider')}/{labels.get('call')}"
            api.setdefault(k, {})[labels.get("status")] = api.get(k, {}).get(labels.get("status"), 0) + int(v)
        recon_err = {labels.get("controller"): int(v) for labels, v in pm["labeled"].get("controller_runtime_reconcile_errors_total", []) if v > 0}
        sync_err = sum(v for _, v in pm["labeled"].get("externalsecret_sync_calls_error", [])) + pm["single"].get("externalsecret_sync_calls_error", 0)
        sync_total = sum(v for _, v in pm["labeled"].get("externalsecret_sync_calls_total", [])) + pm["single"].get("externalsecret_sync_calls_total", 0)
        api_err = sum(d_.get("error", 0) for d_ in api.values())
        api_ok = sum(d_.get("success", 0) for d_ in api.values())
        pods[f.stem] = {
            "provider_api_calls": api,
            "api_errors": api_err,
            "api_success": api_ok,
            "api_error_ratio": round(api_err / (api_err + api_ok), 4) if (api_err + api_ok) else None,
            "sync_calls_total": int(sync_total),
            "sync_calls_error": int(sync_err),
            "reconcile_errors": recon_err,
            "reconcile_errors_total": sum(recon_err.values()),
            "rss_mb": round(pm["single"].get("process_resident_memory_bytes", 0) / 1024**2) if pm["single"].get("process_resident_memory_bytes") else None,
        }
    agg = {
        "available": bool(pods),
        "api_errors": sum(p["api_errors"] for p in pods.values()),
        "api_success": sum(p["api_success"] for p in pods.values()),
        "reconcile_errors_total": sum(p["reconcile_errors_total"] for p in pods.values()),
        "sync_calls_error": sum(p["sync_calls_error"] for p in pods.values()),
        "sync_calls_total": sum(p["sync_calls_total"] for p in pods.values()),
    }
    agg["api_error_ratio"] = round(agg["api_errors"] / (agg["api_errors"] + agg["api_success"]), 4) if (agg["api_errors"] + agg["api_success"]) else None
    pushes = len(objects(snap, "pushsecrets.external-secrets.io"))
    summary = {
        "present": True,
        "version": ctrl.get("version"),
        "controller_replicas": ctrl.get("replicas"),
        "controller_ready": ctrl.get("ready"),
        "webhook_replicas": wh.get("replicas"),
        "webhook_ready": wh.get("ready"),
        "cert_controller_ready": cert.get("ready"),
        "cert_controller_replicas": cert.get("replicas"),
        "concurrent": concurrent,
        "irsa_role": irsa,
        "stores": len(stores),
        "stores_not_ready": [f"{s['kind']}/{s['name']}" for s in stores if not s["ready"]],
        "stores_static_key": [f"{s['kind']}/{s['name']}" for s in stores if s["auth"].startswith("static-key")],
        "stores_auth": {f"{s['kind']}/{s['name']}": s["auth"] for s in stores},
        "providers": sorted({s["provider"] for s in stores if s["provider"]}),
        "externalsecrets": len(rows),
        "externalsecrets_prod": sum(1 for r in rows if r["prod"]),
        "not_ready": [r["target"] for r in rows if not r["ready"]],
        "not_ready_prod": [r["target"] for r in rows if not r["ready"] and r["prod"]],
        "stale": [r["target"] for r in rows if r["stale"] and r["ready"]],
        "stale_detail": [{"target": r["target"], "refresh_interval": r["refresh_interval"], "refresh_age_h": r["refresh_age_h"]} for r in rows if r["stale"] and r["ready"]][:6],
        "refresh_intervals": dict(Counter(r["refresh_interval"] for r in rows)),
        "deletion_policy_delete": [r["target"] for r in rows if r["deletion_policy"] == "Delete"],
        "orphan_creation": [r["target"] for r in rows if r["creation_policy"] == "Orphan"],
        "pushsecrets": pushes,
        "webhook_fail_policy": [w["name"] for w in webhooks if w["failure_policy"] == "Fail"],
        "webhooks": len(webhooks),
        "metrics_available": agg["available"],
        "api_errors": agg["api_errors"],
        "api_success": agg["api_success"],
        "api_error_ratio": agg["api_error_ratio"],
        "reconcile_errors_total": agg["reconcile_errors_total"],
        "sync_calls_error": agg["sync_calls_error"],
        "sync_calls_total": agg["sync_calls_total"],
        "not_ready_oldest_refresh_h": max([r["refresh_age_h"] or 0 for r in rows if not r["ready"]], default=None),
    }
    return {
        "present": True,
        "controller": ctrl,
        "webhook": wh,
        "cert_controller": cert,
        "irsa_role": irsa,
        "stores": stores,
        "externalsecrets": {"count": len(rows), "rows": rows},
        "webhooks": webhooks,
        "metrics": {"available": agg["available"], "pods": pods, **{k: v for k, v in agg.items() if k != "available"}},
        "summary": summary,
        "note": "Secret values are not read. stale = Ready items whose refreshTime is older than 3× refreshInterval (minimum 1 hour). Metrics are cumulative since the process started",
    }

"""cert-manager summary (collector collectors/cert-manager).

Inputs: objects (certificates, certificaterequests, issuers, clusterissuers, orders, challenges, ingresses, deployments cert-manager*, validatingwebhookconfigurations), metrics/pod/cert-manager/*.prom (controller :9402: expiry/renewal times, Ready, ACME client response codes, sync errors).
What we look at: per Certificate: Ready, days to expiry, renewalTime passed without renewal, issuer, revision, prod; Issuer/ClusterIssuer Ready and ACME server (prod using staging?); failed CertificateRequests/Orders (errored, long pending) and Challenges (pending/invalid with reason);
Ingress TLS Secrets not managed by cert-manager (nobody watches their expiry) and Ingresses without TLS; component (controller, webhook, cainjector) replicas and versions; webhook failurePolicy; ACME client 4xx/5xx and sync errors.
Secret values (keys, certificate bodies) are never read. Result: the `certmanager` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import objects


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _conds(obj) -> dict:
    return {c.get("type"): (c.get("status"), c.get("reason"), (c.get("message") or "")[:160]) for c in (obj.get("status") or {}).get("conditions") or []}


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    certs = objects(snap, "certificates.cert-manager.io")
    deps = [d for d in objects(snap, "deployments") if d["metadata"]["name"].startswith("cert-manager")]
    if not certs and not deps:
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    comps = {}
    for d in deps:
        sp, st = d.get("spec") or {}, d.get("status") or {}
        c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
        comps[d["metadata"]["name"].replace("cert-manager-", "") if d["metadata"]["name"] != "cert-manager" else "controller"] = {
            "replicas": sp.get("replicas"),
            "ready": st.get("readyReplicas") or 0,
            "version": _ver(c0.get("image")),
            "namespace": d["metadata"]["namespace"],
        }
    version = (comps.get("controller") or {}).get("version")
    # --- issuers
    issuers = []
    for stem, kind in (("clusterissuers.cert-manager.io", "ClusterIssuer"), ("issuers.cert-manager.io", "Issuer")):
        for o in objects(snap, stem):
            sp = o.get("spec") or {}
            acme = sp.get("acme") or {}
            typ = next(iter(k for k in sp if k in ("acme", "ca", "selfSigned", "vault", "venafi")), None)
            c = _conds(o).get("Ready", (None, None, None))
            issuers.append(
                {
                    "kind": kind,
                    "namespace": o["metadata"].get("namespace"),
                    "name": o["metadata"]["name"],
                    "type": typ,
                    "acme_server": acme.get("server"),
                    "staging": "staging" in str(acme.get("server") or ""),
                    "ready": c[0] == "True",
                    "reason": c[1],
                    "solvers": [("dns01" if "dns01" in s else "http01" if "http01" in s else "?") for s in acme.get("solvers") or []],
                    "certificates": 0,
                }
            )

    def issuer_key(ref: dict, ns: str):
        return (ref.get("kind") or "Issuer", None if (ref.get("kind") or "Issuer") == "ClusterIssuer" else ns, ref.get("name"))

    imap = {(i["kind"], i["namespace"], i["name"]): i for i in issuers}
    # --- Certificate
    rows = []
    for o in certs:
        ns, name = o["metadata"]["namespace"], o["metadata"]["name"]
        sp, st = o.get("spec") or {}, o.get("status") or {}
        c = _conds(o)
        ready = c.get("Ready", (None, None, None))
        issuing = c.get("Issuing", (None, None, None))
        na, rt = _ts(st.get("notAfter")), _ts(st.get("renewalTime"))
        days = round((na - now).total_seconds() / 86400, 1) if na else None
        renew_overdue_h = round((now - rt).total_seconds() / 3600, 1) if rt and now > rt else None
        ref = sp.get("issuerRef") or {}
        iss = imap.get(issuer_key(ref, ns))
        if iss:
            iss["certificates"] += 1
        rows.append(
            {
                "namespace": ns,
                "name": name,
                "target": f"{ns}/certificate/{name}",
                "prod": ns in prod,
                "secret": sp.get("secretName"),
                "dns_names": sp.get("dnsNames") or [],
                "issuer": f"{ref.get('kind', 'Issuer')}/{ref.get('name')}",
                "issuer_staging": bool(iss and iss["staging"]),
                "ready": ready[0] == "True",
                "reason": ready[1],
                "message": ready[2],
                "issuing": issuing[0] == "True",
                "issuing_reason": issuing[1],
                "issuing_message": issuing[2],
                "not_after": (st.get("notAfter") or "")[:10],
                "days_to_expiry": days,
                "renewal_time": (st.get("renewalTime") or "")[:10],
                "renewal_overdue_h": renew_overdue_h,
                "revision": st.get("revision"),
                "duration": sp.get("duration"),
                "renew_before": sp.get("renewBefore"),
            }
        )
    # --- requests, orders, challenges
    crs = objects(snap, "certificaterequests.cert-manager.io")
    cr_failed = [f"{o['metadata']['namespace']}/{o['metadata']['name']}({_conds(o).get('Ready', (None, None))[1]})" for o in crs if _conds(o).get("Ready", (None,))[0] == "False"]
    cr_denied = [f"{o['metadata']['namespace']}/{o['metadata']['name']}" for o in crs if _conds(o).get("Denied", (None,))[0] == "True"]
    orders = objects(snap, "orders.acme.cert-manager.io")
    order_state = Counter((o.get("status") or {}).get("state") or "none" for o in orders)
    orders_bad = [
        f"{o['metadata']['namespace']}/{o['metadata']['name']}({(o.get('status') or {}).get('state')}: {((o.get('status') or {}).get('reason') or '')[:100]})" for o in orders if (o.get("status") or {}).get("state") in ("errored", "invalid")
    ]
    orders_pending_old = [
        f"{o['metadata']['namespace']}/{o['metadata']['name']}"
        for o in orders
        if (o.get("status") or {}).get("state") in ("pending", "processing", None) and (_ts(o["metadata"].get("creationTimestamp")) and (now - _ts(o["metadata"]["creationTimestamp"])).total_seconds() > 3600)
    ]
    challenges = objects(snap, "challenges.acme.cert-manager.io")
    ch_rows = [
        {
            "namespace": o["metadata"]["namespace"],
            "name": o["metadata"]["name"],
            "type": (o.get("spec") or {}).get("type"),
            "dns": (o.get("spec") or {}).get("dnsName"),
            "state": (o.get("status") or {}).get("state"),
            "reason": ((o.get("status") or {}).get("reason") or "")[:160],
            "age_h": round((now - _ts(o["metadata"]["creationTimestamp"])).total_seconds() / 3600, 1) if _ts(o["metadata"].get("creationTimestamp")) else None,
        }
        for o in challenges
    ]
    ch_bad = [c for c in ch_rows if c["state"] in ("invalid", "errored") or ((c["state"] in ("pending", "processing", None)) and (c["age_h"] or 0) > 1)]
    # --- Ingress TLS
    cert_secrets = {(r["namespace"], r["secret"]) for r in rows}
    ing_tls = []
    ing_no_tls = []
    for i in objects(snap, "ingresses.networking.k8s.io"):
        ns = i["metadata"]["namespace"]
        sp = i.get("spec") or {}
        ann = i["metadata"].get("annotations") or {}
        if not sp.get("tls"):
            if not any(k.startswith("alb.ingress.kubernetes.io/certificate-arn") for k in ann):
                ing_no_tls.append(f"{ns}/{i['metadata']['name']}")
            continue
        for t in sp.get("tls") or []:
            managed = (ns, t.get("secretName")) in cert_secrets or any(k in ann for k in ("cert-manager.io/cluster-issuer", "cert-manager.io/issuer"))
            ing_tls.append({"ingress": f"{ns}/{i['metadata']['name']}", "secret": t.get("secretName"), "hosts": t.get("hosts") or [], "managed": managed, "prod": ns in prod})
    webhooks = [
        {"name": h.get("name"), "failure_policy": h.get("failurePolicy"), "timeout_s": h.get("timeoutSeconds")}
        for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io") + objects(snap, "mutatingwebhookconfigurations.admissionregistration.k8s.io")
        if "cert-manager" in w["metadata"]["name"]
        for h in w.get("webhooks") or []
    ]
    # --- metrics
    d = snap / "metrics" / "pod" / "cert-manager"
    files = [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []
    acme: Counter = Counter()
    sync_err = 0
    sync_calls = 0
    not_ready_metric = 0
    exp_min_days = None
    for f in files:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        for labels, v in pm["labeled"].get("certmanager_http_acme_client_request_count", []):
            acme[labels.get("status")] += int(v)
        sync_err += int(pm["single"].get("certmanager_controller_sync_error_count", 0)) + sum(int(v) for _, v in pm["labeled"].get("certmanager_controller_sync_error_count", []))
        sync_calls += sum(int(v) for _, v in pm["labeled"].get("certmanager_controller_sync_call_count", []))
        for labels, v in pm["labeled"].get("certmanager_certificate_ready_status", []):
            if labels.get("condition") == "False" and v >= 1:
                not_ready_metric += 1
        for _labels, v in pm["labeled"].get("certmanager_certificate_expiration_timestamp_seconds", []):
            dd = (v - now.timestamp()) / 86400
            exp_min_days = dd if exp_min_days is None or dd < exp_min_days else exp_min_days
    acme_err = sum(v for k, v in acme.items() if str(k).startswith(("4", "5")))
    acme_total = sum(acme.values())
    expiring = sorted([r for r in rows if r["days_to_expiry"] is not None and r["days_to_expiry"] < 30], key=lambda r: r["days_to_expiry"])
    summary = {
        "present": True,
        "version": version,
        "components": {k: f"{v['ready']}/{v['replicas']}" for k, v in comps.items()},
        "components_not_ready": [k for k, v in comps.items() if (v["ready"] or 0) < (v["replicas"] or 0)],
        "components_single_replica": [k for k, v in comps.items() if (v["replicas"] or 0) == 1],
        "certificates": len(rows),
        "certificates_prod": sum(1 for r in rows if r["prod"]),
        "not_ready": [f"{r['target']}({r['reason']})" for r in rows if not r["ready"]],
        "not_ready_prod": [r["target"] for r in rows if not r["ready"] and r["prod"]],
        "expiring_30d": [(r["target"], r["days_to_expiry"]) for r in expiring],
        "expiring_14d": [r["target"] for r in expiring if (r["days_to_expiry"] or 99) < 14],
        "expired": [r["target"] for r in rows if (r["days_to_expiry"] or 99) <= 0],
        "min_days_to_expiry": min([r["days_to_expiry"] for r in rows if r["days_to_expiry"] is not None], default=None),
        "renewal_overdue": [(r["target"], r["renewal_overdue_h"]) for r in rows if (r["renewal_overdue_h"] or 0) > 24],
        "issuing_stuck": [f"{r['target']}({r['issuing_reason']}: {r['issuing_message'][:80]})" for r in rows if r["issuing"] and not r["ready"]],
        "staging_certs": [r["target"] for r in rows if r["issuer_staging"]],
        "staging_certs_prod": [r["target"] for r in rows if r["issuer_staging"] and r["prod"]],
        "issuers": len(issuers),
        "issuers_not_ready": [f"{i['kind']}/{i['name']}({i['reason']})" for i in issuers if not i["ready"]],
        "issuers_unused": [f"{i['kind']}/{i['name']}" for i in issuers if i["certificates"] == 0],
        "issuer_types": dict(Counter(i["type"] for i in issuers)),
        "solvers": sorted({s for i in issuers for s in i["solvers"]}),
        "certificaterequests": len(crs),
        "certificaterequests_failed": cr_failed[:10],
        "certificaterequests_denied": cr_denied[:10],
        "orders": len(orders),
        "orders_by_state": dict(order_state),
        "orders_bad": orders_bad[:10],
        "orders_pending_old": orders_pending_old[:10],
        "challenges": len(ch_rows),
        "challenges_bad": [{"challenge": c["namespace"] + "/" + c["name"], "type": c["type"], "dns": c["dns"], "state": c["state"], "reason": c["reason"]} for c in ch_bad][:10],
        "ingress_tls": len(ing_tls),
        "ingress_tls_unmanaged": [(t["ingress"], t["secret"]) for t in ing_tls if not t["managed"]][:12],
        "ingress_tls_unmanaged_prod": [t["ingress"] for t in ing_tls if not t["managed"] and t["prod"]],
        "ingress_no_tls": ing_no_tls[:12],
        "webhooks_fail": [w["name"] for w in webhooks if w["failure_policy"] == "Fail"],
        "webhook_replicas": (comps.get("webhook") or {}).get("replicas"),
        "metrics_available": bool(files),
        "acme_requests": acme_total,
        "acme_errors": acme_err,
        "acme_by_status": dict(acme),
        "acme_error_ratio": round(acme_err / acme_total, 4) if acme_total else None,
        "sync_errors": sync_err,
        "sync_calls": sync_calls,
        "not_ready_metric": not_ready_metric,
        "min_days_to_expiry_metric": round(exp_min_days, 1) if exp_min_days is not None else None,
    }
    return {
        "present": True,
        "components": comps,
        "issuers": issuers,
        "certificates": {"count": len(rows), "rows": rows},
        "challenges": ch_rows,
        "ingress_tls": ing_tls,
        "webhooks": webhooks,
        "summary": summary,
        "note": "Secret values (certificates, keys) are not read. Expiry/renewal comes from Certificate status (notAfter, renewalTime). ACME client response codes are cumulative since the controller started. On the small k3s cluster every Ingress TLS Secret was managed by cert-manager (measured)",
    }

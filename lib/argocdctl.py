"""Argo CD summary (collector collectors/argocd).

The Sync/Health list of Applications belongs to hygiene.templating.argocd_apps. Here we take the operator's view:
component replicas and versions (application-controller, repo-server, server, redis, dex, applicationset, notifications), per Application: automated sync, prune, selfHeal, syncOptions, targetRevision (branch tracking), last operation phase/time,
reconciledAt age, how long it has been OutOfSync/Degraded, whether Namespaces/CRDs are managed as prune targets; AppProject boundaries (use of the default project, sourceRepos/destinations wildcards),
server settings (admin.enabled, SSO (dex/oidc), exec.enabled, server.insecure, RBAC policy.default, url), Ingress TLS, notifications (argocd-notifications-cm triggers/services), ApplicationSets,
controller metrics (metrics/pod/argocd-*/...: sync result phases, k8s API response codes, cluster cache age, git request failures, redis failures, gRPC codes).
Result: the `argocdctl` section of summary.json. Shape is described in SKILL.md. Git credentials and Secret values are never read.
"""

from __future__ import annotations

import datetime as _dt
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


def _dur_s(s) -> float | None:
    m = re.match(r"^(\d+)([smh])$", str(s or ""))
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return n if u == "s" else (n * 60 if u == "m" else n * 3600)


def _prom_dir(snap: Path, name: str) -> dict:
    d = snap / "metrics" / "pod" / name
    out = {}
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        out[f.stem] = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
    return out


def _csv_lines(v) -> int:
    """policy.csv line count. The snapshot holds {lines, len} for it (lib/scrub.py); older snapshots hold the text."""
    if isinstance(v, dict):
        return int(v.get("lines") or 0)
    return len([ln for ln in (v or "").splitlines() if ln.strip()])


def _non_empty(v) -> bool:
    """Whether a ConfigMap value is set. Scrubbed values are {len, shape} or {present, len}; older snapshots hold the string."""
    if isinstance(v, dict):
        return bool(v.get("present")) if "present" in v else int(v.get("len") or 0) > 0
    return bool(v)


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    apps = objects(snap, "applications.argoproj.io")
    wls = [w for w in objects(snap, "deployments") + objects(snap, "statefulsets") if w["metadata"]["namespace"] == "argocd" and w["metadata"]["name"].startswith("argocd-")]
    if not apps and not wls:
        return {"present": False}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    comps = {}
    for w in wls:
        sp, st = w.get("spec") or {}, w.get("status") or {}
        c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
        comps[w["metadata"]["name"].replace("argocd-", "")] = {
            "replicas": sp.get("replicas"),
            "ready": st.get("readyReplicas") or 0,
            "version": _ver(c0.get("image")),
            "kind": "StatefulSet" if "volumeClaimTemplates" in sp or (w["metadata"]["name"].endswith("controller") and "serviceName" in sp) else "Deployment",
        }
    version = (comps.get("server") or comps.get("application-controller") or {}).get("version")
    # --- settings
    cms = {c["metadata"]["name"]: (c.get("data") or {}) for c in objects(snap, "configmaps") if c["metadata"]["namespace"] == "argocd"}
    cm, params, rbac, notif = cms.get("argocd-cm", {}), cms.get("argocd-cmd-params-cm", {}), cms.get("argocd-rbac-cm", {}), cms.get("argocd-notifications-cm", {})

    def flag(d, k, default):
        v = d.get(k)
        return default if v is None else str(v).lower() == "true"

    sso = _non_empty(cm.get("dex.config")) or _non_empty(cm.get("oidc.config"))
    reconcile_s = _dur_s(cm.get("timeout.reconciliation")) or 180
    config = {
        "url": cm.get("url"),
        "admin_enabled": flag(cm, "admin.enabled", True),
        "sso_configured": sso,
        "sso_kind": "dex" if _non_empty(cm.get("dex.config")) else ("oidc" if _non_empty(cm.get("oidc.config")) else None),
        "exec_enabled": flag(cm, "exec.enabled", False),
        "anonymous_enabled": flag(cm, "users.anonymous.enabled", False),
        "server_insecure": flag(params, "server.insecure", False),
        "timeout_reconciliation": cm.get("timeout.reconciliation", "180s (default)"),
        "timeout_reconciliation_s": reconcile_s,
        "status_processors": params.get("controller.status.processors"),
        "operation_processors": params.get("controller.operation.processors"),
        "rbac_policy_default": rbac.get("policy.default", ""),
        # The snapshot does not hold ConfigMap values (lib/scrub.py): policy.csv arrives as {lines, len} and resource.exclusions as {len, shape}. Older snapshots still carry the strings.
        "rbac_policy_csv_lines": _csv_lines(rbac.get("policy.csv")),
        "resource_exclusions": _non_empty(cm.get("resource.exclusions")),
        "ignore_resource_updates": sum(1 for k in cm if k.startswith("resource.customizations.ignoreResourceUpdates")),
        "application_namespaces": params.get("application.namespaces") or None,
        "notifications_triggers": [k for k in notif if k.startswith("trigger.")],
        "notifications_services": [k for k in notif if k.startswith("service.")],
        "notifications_configured": any(k.startswith("service.") for k in notif),
    }
    ing = [i for i in objects(snap, "ingresses.networking.k8s.io") if i["metadata"]["namespace"] == "argocd"]
    ingress = [
        {
            "name": i["metadata"]["name"],
            "hosts": [r.get("host") for r in (i.get("spec") or {}).get("rules") or []],
            "tls": bool((i.get("spec") or {}).get("tls"))
            or bool((i["metadata"].get("annotations") or {}).get("alb.ingress.kubernetes.io/certificate-arn"))
            or "443" in str((i["metadata"].get("annotations") or {}).get("alb.ingress.kubernetes.io/listen-ports", "")),
        }
        for i in ing
    ]
    # --- projects
    projects = []
    for p in objects(snap, "appprojects.argoproj.io"):
        sp = p.get("spec") or {}
        projects.append(
            {
                "name": p["metadata"]["name"],
                "source_repos": sp.get("sourceRepos") or [],
                "destinations": sp.get("destinations") or [],
                "cluster_resource_whitelist": sp.get("clusterResourceWhitelist") or [],
                "wildcard_sources": "*" in (sp.get("sourceRepos") or []),
                "wildcard_destinations": any(d.get("namespace") == "*" and d.get("server") == "*" for d in (sp.get("destinations") or [])),
                "roles": len(sp.get("roles") or []),
                "apps": sum(1 for a in apps if (a.get("spec") or {}).get("project") == p["metadata"]["name"]),
            }
        )
    # --- Application
    rows = []
    for a in apps:
        sp, st = a.get("spec") or {}, a.get("status") or {}
        src = sp.get("source") or ((sp.get("sources") or [{}])[0] if sp.get("sources") else {})
        pol = sp.get("syncPolicy") or {}
        auto = pol.get("automated")
        op = st.get("operationState") or {}
        dest_ns = (sp.get("destination") or {}).get("namespace")
        kinds = Counter(r.get("kind") for r in st.get("resources") or [])
        fin = _ts(op.get("finishedAt"))
        rec = _ts(st.get("reconciledAt"))
        sync = (st.get("sync") or {}).get("status")
        health = (st.get("health") or {}).get("status")
        cond = [c.get("type") for c in st.get("conditions") or []]
        rows.append(
            {
                "name": a["metadata"]["name"],
                "namespace": a["metadata"]["namespace"],
                "target": f"argocd/application/{a['metadata']['name']}",
                "project": sp.get("project"),
                "dest_namespace": dest_ns,
                "prod": (dest_ns in prod) or any(r.get("namespace") in prod for r in st.get("resources") or []),
                "repo": (src.get("repoURL") or "")[-60:],
                "path": src.get("path"),
                "chart": src.get("chart"),
                "target_revision": src.get("targetRevision"),
                "tracks_moving_ref": str(src.get("targetRevision") or "HEAD") in ("HEAD", "main", "master", "develop", "dev") or not re.match(r"^v?\d", str(src.get("targetRevision") or "HEAD")),
                "automated": bool(auto),
                "prune": bool((auto or {}).get("prune")),
                "self_heal": bool((auto or {}).get("selfHeal")),
                "sync_options": pol.get("syncOptions") or [],
                "sync": sync,
                "health": health,
                "conditions": cond,
                "last_op_phase": op.get("phase"),
                "last_op_finished": op.get("finishedAt"),
                "last_op_age_h": round((now - fin).total_seconds() / 3600, 1) if fin else None,
                "reconciled_age_min": round((now - rec).total_seconds() / 60, 1) if rec else None,
                "resources": len(st.get("resources") or []),
                "manages_namespace": kinds.get("Namespace", 0),
                "manages_crd": kinds.get("CustomResourceDefinition", 0),
                "history": len(st.get("history") or []),
                "ignore_differences": bool(sp.get("ignoreDifferences")),
                "revision": (st.get("sync") or {}).get("revision", "")[:12],
            }
        )
    # --- metrics
    ctl = _prom_dir(snap, "argocd-application-controller")
    repo = _prom_dir(snap, "argocd-repo-server")
    srv = _prom_dir(snap, "argocd-server")
    sync_by_phase: Counter = Counter()
    k8s_codes: Counter = Counter()
    redis_failed = 0
    redis_total = 0
    cache_age = None
    api_objects = None
    cluster_conn = None
    for pm in ctl.values():
        for labels, v in pm["labeled"].get("argocd_app_sync_total", []):
            sync_by_phase[labels.get("phase")] += int(v)
        for labels, v in pm["labeled"].get("argocd_app_k8s_request_total", []):
            k8s_codes[labels.get("response_code")] += int(v)
        for labels, v in pm["labeled"].get("argocd_redis_request_total", []):
            redis_total += int(v)
            if labels.get("failed") == "true":
                redis_failed += int(v)
        for _labels, v in pm["labeled"].get("argocd_cluster_cache_age_seconds", []):
            cache_age = v
        for _labels, v in pm["labeled"].get("argocd_cluster_api_resource_objects", []):
            api_objects = int(v)
        for _labels, v in pm["labeled"].get("argocd_cluster_connection_status", []):
            cluster_conn = v
        cache_age = cache_age if cache_age is not None else pm["single"].get("argocd_cluster_cache_age_seconds")
        api_objects = api_objects if api_objects is not None else pm["single"].get("argocd_cluster_api_resource_objects")
        cluster_conn = cluster_conn if cluster_conn is not None else pm["single"].get("argocd_cluster_connection_status")
    git_req = 0
    git_fail = 0
    repo_pending = None
    for pm in repo.values():
        git_req += sum(int(v) for _, v in pm["labeled"].get("argocd_git_request_total", []))
        git_fail += (
            int(pm["single"].get("argocd_git_lsremote_fail_total", 0))
            + int(pm["single"].get("argocd_git_fetch_fail_total", 0))
            + sum(int(v) for _, v in pm["labeled"].get("argocd_git_lsremote_fail_total", []) + pm["labeled"].get("argocd_git_fetch_fail_total", []))
        )
        for labels, v in pm["labeled"].get("argocd_redis_request_total", []):
            redis_total += int(v)
            if labels.get("failed") == "true":
                redis_failed += int(v)
        repo_pending = pm["single"].get("argocd_repo_pending_request_total", repo_pending)
    grpc: Counter = Counter()
    for pm in srv.values():
        for labels, v in pm["labeled"].get("grpc_server_handled_total", []):
            grpc[labels.get("grpc_code")] += int(v)
        for labels, v in pm["labeled"].get("argocd_redis_request_total", []):
            redis_total += int(v)
            if labels.get("failed") == "true":
                redis_failed += int(v)
    # collect.yaml's keep filter keeps only 4xx/5xx k8s request lines, so without a 200 line the total is unknown.
    metrics = {
        "available": bool(ctl or repo or srv),
        "controller_pods": list(ctl),
        "repo_pods": list(repo),
        "server_pods": list(srv),
        "sync_by_phase": dict(sync_by_phase),
        "sync_failed": sync_by_phase.get("Failed", 0) + sync_by_phase.get("Error", 0),
        "sync_total": sum(sync_by_phase.values()),
        "k8s_api_by_code": dict(k8s_codes),
        "k8s_api_errors": sum(v for k, v in k8s_codes.items() if str(k) and (str(k).startswith("5") or k == "429")),
        "k8s_api_total": sum(k8s_codes.values()) if "200" in k8s_codes else None,
        "k8s_api_5xx_429": sum(v for k, v in k8s_codes.items() if str(k).startswith("5") or k == "429"),
        "k8s_api_4xx": sum(v for k, v in k8s_codes.items() if str(k).startswith("4") and k != "429"),
        "cluster_cache_age_s": cache_age,
        "cluster_api_objects": api_objects,
        "cluster_connection_ok": (cluster_conn == 1) if cluster_conn is not None else None,
        "git_requests": git_req,
        "git_failures": git_fail,
        "git_failure_ratio": round(git_fail / git_req, 4) if git_req else None,
        "repo_pending_requests": repo_pending,
        "redis_failed": redis_failed,
        "redis_total": redis_total,
        "redis_failure_ratio": round(redis_failed / redis_total, 4) if redis_total else None,
        "grpc_by_code": dict(grpc),
        "grpc_errors": sum(v for k, v in grpc.items() if k not in ("OK", "Canceled", "Unauthenticated", "NotFound", "PermissionDenied", "InvalidArgument", "AlreadyExists", "FailedPrecondition")),
        "grpc_unauthenticated": grpc.get("Unauthenticated", 0),
        "grpc_permission_denied": grpc.get("PermissionDenied", 0),
        "grpc_total": sum(grpc.values()),
    }
    out_of_sync = [r for r in rows if r["sync"] not in ("Synced", None)]
    # Progressing (rolling out) and Suspended (intentional) are not unhealthy. Only Degraded, Missing and Unknown count as unhealthy.
    unhealthy = [r for r in rows if r["health"] not in ("Healthy", "Progressing", "Suspended", None)]
    progressing = [r for r in rows if r["health"] == "Progressing"]
    summary = {
        "present": True,
        "version": version,
        "components": {k: f"{v['ready']}/{v['replicas']}" for k, v in comps.items()},
        "components_not_ready": [k for k, v in comps.items() if (v["ready"] or 0) < (v["replicas"] or 0)],
        "applications": len(rows),
        "applications_prod": sum(1 for r in rows if r["prod"]),
        "applicationsets": len(objects(snap, "applicationsets.argoproj.io")),
        "out_of_sync": [r["target"] for r in out_of_sync],
        "out_of_sync_prod": [r["target"] for r in out_of_sync if r["prod"]],
        "unhealthy": [f"{r['target']}({r['health']})" for r in unhealthy],
        "unhealthy_prod": [r["target"] for r in unhealthy if r["prod"]],
        "progressing": [r["target"] for r in progressing],
        "degraded": [r["target"] for r in rows if r["health"] == "Degraded"],
        "last_op_failed": [f"{r['target']}({r['last_op_phase']})" for r in rows if r["last_op_phase"] in ("Failed", "Error")],
        "conditions": sorted({c for r in rows for c in r["conditions"]}),
        "apps_with_conditions": [r["target"] for r in rows if r["conditions"]],
        "prod_not_automated": [r["target"] for r in rows if r["prod"] and not r["automated"]],
        "prod_no_self_heal": [r["target"] for r in rows if r["prod"] and r["automated"] and not r["self_heal"]],
        "prune_with_namespace_or_crd": [r["target"] for r in rows if r["prune"] and (r["manages_namespace"] or r["manages_crd"])],
        "prod_tracking_moving_ref": [r["target"] for r in rows if r["prod"] and r["tracks_moving_ref"]],
        "reconcile_stale": [r["target"] for r in rows if (r["reconciled_age_min"] or 0) * 60 > reconcile_s * 3],
        "reconcile_timeout_s": reconcile_s,
        "ignore_differences_apps": sum(1 for r in rows if r["ignore_differences"]),
        "projects": len(projects),
        "default_project_apps": next((p["apps"] for p in projects if p["name"] == "default"), 0),
        "wildcard_projects": [p["name"] for p in projects if p["wildcard_sources"] and p["wildcard_destinations"]],
        "admin_enabled": config["admin_enabled"],
        "sso_configured": config["sso_configured"],
        "exec_enabled": config["exec_enabled"],
        "anonymous_enabled": config["anonymous_enabled"],
        "server_insecure": config["server_insecure"],
        "rbac_policy_default": config["rbac_policy_default"],
        "rbac_policy_csv_lines": config["rbac_policy_csv_lines"],
        "url": config["url"],
        "ingress_hosts": [h for i in ingress for h in i["hosts"]],
        "ingress_tls": all(i["tls"] for i in ingress) if ingress else None,
        "notifications_configured": config["notifications_configured"],
        "notifications_triggers": len(config["notifications_triggers"]),
        "metrics_available": metrics["available"],
        "sync_failed": metrics["sync_failed"],
        "sync_total": metrics["sync_total"],
        "sync_failure_ratio": round(metrics["sync_failed"] / metrics["sync_total"], 4) if metrics["sync_total"] else None,
        "k8s_api_errors": metrics["k8s_api_errors"],
        "k8s_api_4xx": metrics["k8s_api_4xx"],
        "cluster_cache_age_s": metrics["cluster_cache_age_s"],
        "cluster_connection_ok": metrics["cluster_connection_ok"],
        "git_requests": metrics["git_requests"],
        "git_failures": metrics["git_failures"],
        "git_failure_ratio": metrics["git_failure_ratio"],
        "redis_failed": metrics["redis_failed"],
        "redis_total": metrics["redis_total"],
        "redis_failure_ratio": metrics["redis_failure_ratio"],
        "grpc_errors": metrics["grpc_errors"],
        "grpc_unauthenticated": metrics["grpc_unauthenticated"],
        "grpc_permission_denied": metrics["grpc_permission_denied"],
        "grpc_total": metrics["grpc_total"],
        "repo_pending_requests": metrics["repo_pending_requests"],
        "version_major": int(version.split(".")[0]) if version else None,
        "components_single_replica": [k for k, v in comps.items() if (v["replicas"] or 0) == 1 and k in ("server", "repo-server")],
        "exec_enabled_flag": config["exec_enabled"],
    }
    return {
        "present": True,
        "components": comps,
        "config": config,
        "ingress": ingress,
        "projects": projects,
        "applications": {"count": len(rows), "rows": rows},
        "metrics": metrics,
        "summary": summary,
        "note": "Metrics are cumulative since each process started. Git credentials and Secret values are not read. prod = destination namespace or a managed resource's namespace is prod_like",
    }

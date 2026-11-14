"""Argo CD summary (collector collectors/argocd).

The Sync/Health list of Applications belongs to hygiene.templating.argocd_apps. Here we take the operator's view:
component replicas and versions (application-controller, repo-server, server, redis, dex, applicationset, notifications), per Application: automated sync, prune, selfHeal, syncOptions, targetRevision (branch tracking), last operation phase/time,
reconciledAt age, how long it has been OutOfSync/Degraded, whether Namespaces/CRDs are managed as prune targets; AppProject boundaries (use of the default project, sourceRepos/destinations wildcards),
server settings (admin.enabled, SSO (dex/oidc), exec.enabled, server.insecure, RBAC policy.default, url), Ingress TLS, notifications (argocd-notifications-cm triggers/services), ApplicationSets,
controller metrics (metrics/pod/argocd-*/...: sync result phases, k8s API response codes, cluster cache age, git request failures, redis failures, gRPC codes).
Result: the `argocdctl` section of summary.json. Shape is described in SKILL.md. Git credentials and Secret values are never read.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ..foundations.durations import go_duration_s
from ..foundations.promtext import parse as _parse_prom
from ..foundations.snapshot import dump_record, load_json, object_file_status, objects, parse_ts, taken_at
from ..foundations.versions import image_version, major_minor


def _dur_s(s) -> float | None:
    """Seconds of a Go duration (`180s`, `3m0s`, `2m30s`): Argo CD parses `timeout.reconciliation` with `time.ParseDuration` (lib/foundations/durations)."""
    secs = go_duration_s(s)
    return secs if secs and secs > 0 else None


def _prom_dir(snap: Path, name: str) -> dict:
    d = snap / "metrics" / "pod" / name
    out = {}
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        out[f.stem] = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
    return out


def _csv_lines(v) -> int:
    """policy.csv line count: the snapshot holds {lines, len} for it (lib/foundations/scrub.py LINE_COUNT_ONLY)."""
    return int(v.get("lines") or 0) if isinstance(v, dict) else 0


def _non_empty(v) -> bool:
    """Whether a ConfigMap value is set: scrubbed values are {len, shape} or {present, len} (lib/foundations/scrub.py)."""
    if isinstance(v, dict):
        return bool(v.get("present")) if "present" in v else int(v.get("len") or 0) > 0
    return False


# What stops Argo CD from deleting an object an Application tracks (#207). Two paths delete: automated prune, when the object leaves what the source
# renders, and the cascade of the resources finalizer, when the Application itself is deleted. Each reads the live object and nothing else.
#   prune:   `pruneObject` skips an object whose `argocd.argoproj.io/sync-options` holds `Prune=false`, and nothing else on the object
#            (argoproj/gitops-engine pkg/sync/sync_context.go:1002@bd7681ae3f8b, :1224@b89b0871b414; argoproj/argo-cd gitops-engine/pkg/sync/sync_context.go:356,1511@v3.6.1)
#   cascade: `shouldBeDeleted` skips every CRD, an object with `Delete=false` and an object with `helm.sh/resource-policy: keep`
#            (argoproj/argo-cd controller/appcontroller.go:1101-1105@v2.13.0, :1166-1170@v3.2.0, :1321-1330@v3.6.1; util/helm/helm.go:21,22@v3.2.0)
#   `Prune=confirm` and `Delete=confirm` wait for a person; the values exist from 2.14.0
#            (argoproj/gitops-engine pkg/sync/common/types.go:42,44@c19f8cfa4d27, absent at :23-35@bd7681ae3f8b; pkg/sync/sync_context.go:1176@c19f8cfa4d27; argoproj/argo-cd controller/appcontroller.go:1230@v2.14.0)
#   from 3.4.0 the Application's own `syncPolicy.syncOptions` is the default when the object has no `Prune=`/`Delete=` option of its own
#            (argoproj/argo-cd controller/sync.go:350@v3.4.0, controller/appcontroller.go:1173@v3.4.0; neither line exists at v3.3.0)
#   the annotation is a comma-separated list, each item trimmed (argoproj/gitops-engine pkg/sync/resource/annotations.go:16-31@bd7681ae3f8b, :16-31@b89b0871b414)
#   the cascade runs when the Application carries a resources finalizer, plain or with a propagation policy
#            (argoproj/argo-cd pkg/apis/application/v1alpha1/application_defaults.go:10,16,19@v3.2.0; pkg/apis/application/v1alpha1/types.go:3276-3283@v3.2.0)
SYNC_OPTIONS = "argocd.argoproj.io/sync-options"
HELM_RESOURCE_POLICY = "helm.sh/resource-policy"
RESOURCES_FINALIZER = "resources-finalizer.argocd.argoproj.io"
TRACKED_KINDS = {("", "Namespace"): "namespaces", ("apiextensions.k8s.io", "CustomResourceDefinition"): "customresourcedefinitions"}


def _csv(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _option(values: list[str], key: str) -> str | None:
    """The value of `key=<value>` in a sync-options list, None when the list has no such option."""
    return next((x.split("=", 1)[1] for x in values if x.startswith(key + "=")), None)


def _guards(annotations: dict, app_options: list[str], ver: tuple[int, int] | None) -> tuple[bool, bool]:
    """(automated prune leaves the object, the cascade on Application deletion leaves it), read from the object's annotations as Argo CD of this version reads them.
    Without a version (no semver image tag) only what every version read honours counts: `Prune=false`, `Delete=false` and Helm's `keep`."""
    own = _csv(annotations.get(SYNC_OPTIONS))
    stops = {"false", "confirm"} if ver and ver >= (2, 14) else {"false"}
    prune, delete = _option(own, "Prune"), _option(own, "Delete")
    if ver and ver >= (3, 4):
        prune = _option(app_options, "Prune") if prune is None else prune
        delete = _option(app_options, "Delete") if delete is None else delete
    return prune in stops, delete in stops or "keep" in _csv(annotations.get(HELM_RESOURCE_POLICY))


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    apps = objects(snap, "applications.argoproj.io")
    wls = [w for w in objects(snap, "deployments") + objects(snap, "statefulsets") if w["metadata"]["namespace"] == "argocd" and w["metadata"]["name"].startswith("argocd-")]
    if not apps and not wls:
        return {"present": False}
    now = taken_at(inv)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    comps = {}
    for w in wls:
        sp, st = w.get("spec") or {}, w.get("status") or {}
        c0 = ((sp.get("template") or {}).get("spec") or {}).get("containers", [{}])[0]
        comps[w["metadata"]["name"].replace("argocd-", "")] = {
            "replicas": sp.get("replicas"),
            "ready": st.get("readyReplicas") or 0,
            "version": image_version(c0.get("image")),
            "kind": "StatefulSet" if "volumeClaimTemplates" in sp or (w["metadata"]["name"].endswith("controller") and "serviceName" in sp) else "Deployment",
        }
    version = next((comps[k]["version"] for k in ("server", "application-controller", "repo-server", "applicationset-controller", "dex-server", "notifications-controller") if (comps.get(k) or {}).get("version")), None)
    # --- settings
    cms = {c["metadata"]["name"]: (c.get("data") or {}) for c in objects(snap, "configmaps") if c["metadata"]["namespace"] == "argocd"}
    cm, params, rbac, notif = cms.get("argocd-cm", {}), cms.get("argocd-cmd-params-cm", {}), cms.get("argocd-rbac-cm", {}), cms.get("argocd-notifications-cm", {})

    def flag(d, k, default):
        v = d.get(k)
        return default if v is None else str(v).lower() == "true"

    sso = _non_empty(cm.get("dex.config")) or _non_empty(cm.get("oidc.config"))
    # The controller's default resync period is 180 s through 2.x and 120 s from 3.0.0 (argoproj/argo-cd cmd/argocd-application-controller/commands/argocd_application_controller.go:44@v2.13.0, :47@v3.0.0; #124 N-2)
    reconcile_default = 120 if (version or "").split(".")[0].isdigit() and int(version.split(".")[0]) >= 3 else 180
    reconcile_s = _dur_s(cm.get("timeout.reconciliation")) or reconcile_default
    config = {
        "url": cm.get("url"),
        "admin_enabled": flag(cm, "admin.enabled", True),
        "sso_configured": sso,
        "sso_kind": "dex" if _non_empty(cm.get("dex.config")) else ("oidc" if _non_empty(cm.get("oidc.config")) else None),
        "exec_enabled": flag(cm, "exec.enabled", False),
        "anonymous_enabled": flag(cm, "users.anonymous.enabled", False),
        "server_insecure": flag(params, "server.insecure", False),
        "timeout_reconciliation": cm.get("timeout.reconciliation", f"{reconcile_default}s (default)"),
        "timeout_reconciliation_s": reconcile_s,
        "reconcile_default_basis": f"Argo CD {version}: {reconcile_default} s" if version else "no semver image tag on any argocd-* workload: assumed 2.x (180 s)",
        "status_processors": params.get("controller.status.processors"),
        "operation_processors": params.get("controller.operation.processors"),
        "rbac_policy_default": rbac.get("policy.default", ""),
        # The snapshot does not hold ConfigMap values (lib/foundations/scrub.py): policy.csv arrives as {lines, len} and resource.exclusions as {len, shape}. Older snapshots still carry the strings.
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
    ver = major_minor(version)
    rec = dump_record(snap)
    live = {stem: {o["metadata"]["name"]: (o["metadata"].get("annotations") or {}) for o in objects(snap, stem)} for stem in TRACKED_KINDS.values()}
    unread = {stem for stem in TRACKED_KINDS.values() if object_file_status(snap, stem, rec) != "ok"}
    tracked_unread: set[str] = set()
    rows = []
    for a in apps:
        sp, st = a.get("spec") or {}, a.get("status") or {}
        src = sp.get("source") or ((sp.get("sources") or [{}])[0] if sp.get("sources") else {})
        pol = sp.get("syncPolicy") or {}
        auto = pol.get("automated")
        # Argo CD auto-syncs when `automated` is set and `automated.enabled` is not false (the field exists from 3.1.0: argoproj/argo-cd pkg/apis/application/v1alpha1/types.go:1532@v3.1.0; `IsAutomatedSyncEnabled` :1458-1463@v3.2.0; #124 N-1)
        automated = auto is not None and (auto or {}).get("enabled") is not False
        op = st.get("operationState") or {}
        dest_ns = (sp.get("destination") or {}).get("namespace")
        kinds = Counter(r.get("kind") for r in st.get("resources") or [])
        prune = bool(automated and (auto or {}).get("prune"))
        cascade = any(str(f).startswith(RESOURCES_FINALIZER) for f in a["metadata"].get("finalizers") or [])
        prune_deletes, cascade_deletes = [], []
        for r in st.get("resources") or []:
            stem = TRACKED_KINDS.get((r.get("group") or "", r.get("kind")))
            if not stem:
                continue
            if stem in unread:
                tracked_unread.add(stem)
                continue
            # an object the Application lists and the cluster no longer has cannot be deleted again
            if r.get("name") not in live[stem]:
                continue
            keeps_on_prune, keeps_on_delete = _guards(live[stem][r.get("name")], pol.get("syncOptions") or [], ver)
            if prune and not keeps_on_prune:
                prune_deletes.append(f"{r.get('kind')}/{r.get('name')}")
            if cascade and stem == "namespaces" and not keeps_on_delete:
                cascade_deletes.append(f"{r.get('kind')}/{r.get('name')}")
        fin = parse_ts(op.get("finishedAt"))
        rec = parse_ts(st.get("reconciledAt"))
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
                "repo_url": re.sub(r"//[^/@]*@", "//", src.get("repoURL") or ""),  # whole, for the report to name where a workload is declared; a login written into the URL is left out
                "path": src.get("path"),
                "chart": src.get("chart"),
                "target_revision": src.get("targetRevision"),
                "tracks_moving_ref": str(src.get("targetRevision") or "HEAD") in ("HEAD", "main", "master", "develop", "dev") or not re.match(r"^v?\d", str(src.get("targetRevision") or "HEAD")),
                "automated": automated,
                "prune": prune,
                "cascade": cascade,
                "self_heal": bool(automated and (auto or {}).get("selfHeal")),
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
                "prune_deletes": sorted(prune_deletes),
                "cascade_deletes": sorted(cascade_deletes),
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
    # the pod-metrics steps record every pod they tried; a pod that neither the proxy nor a node could read is named here, so one answering pod does not hide another's silence
    steps = ((load_json(snap / "collect-result.json") or {}).get("argocd") or {}).get("steps") or {}
    pods_unread = sorted(pod for st in steps.values() if isinstance(st, dict) for pod, r in (st.get("pods") or {}).items() if isinstance(r, dict) and not r.get("ok") and not str(r.get("skipped") or "").startswith("pod not Running"))
    metrics = {
        "available": bool(ctl or repo or srv),
        "pods_unread": pods_unread,
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
        "prune_deletes_namespace_or_crd": [r["target"] for r in rows if r["prune_deletes"]],
        "prune_deletes_objects": [f"{r['name']} {o}" for r in rows for o in r["prune_deletes"]],
        "cascade_deletes_namespace": [f"{r['name']} {o}" for r in rows for o in r["cascade_deletes"]],
        "tracked_objects_read": not tracked_unread,
        "tracked_objects_unread": sorted(tracked_unread),
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
        "pods_unread": metrics["pods_unread"],
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

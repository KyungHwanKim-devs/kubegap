"""ConfigMap changes: which workloads read a ConfigMap, how, and when its data last changed.

Part of the hygiene section (lib/summaries/hygiene): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

from collections import defaultdict

from ...foundations.snapshot import objects, parse_ts
from ...foundations.workload import workload_of


# ---------- ConfigMaps changed after the pods that use them started ----------
# A ConfigMap edited without a pod restart is a change nobody has seen take effect yet; it applies the next time the pod is recreated (node
# replacement, deploy), weeks later, with nobody connecting the two (Pusher 2019). A file mount is refreshed by the kubelet within a sync period,
# so only env, envFrom and subPath references keep the old value until a restart. Secrets are not in the snapshot (never collected), so they are
# not judged here. The change time is the latest managedFields time of the ConfigMap, which kubectl returns only with --show-managed-fields
# (lib/collection/discover); a snapshot taken without it has no times and the section is None, so the check skips as not collected.
def cm_refs(spec: dict) -> dict[str, dict]:
    """ConfigMap name -> {"modes": set, "containers": set} for one pod spec. Modes: 'env' (env/envFrom), 'subpath' (volumeMount with subPath or
    subPathExpr, a bind mount the kubelet does not refresh), 'file' (volume or projected mount, refreshed by the kubelet). containers are the
    names of the containers that read it, so the caller can use their own start time."""
    out: dict[str, dict] = defaultdict(lambda: {"modes": set(), "containers": set()})
    vol_cm: dict[str, list[str]] = defaultdict(list)  # volume name -> configmap names (a projected volume may carry several)
    for v in spec.get("volumes") or []:
        if (v.get("configMap") or {}).get("name"):
            vol_cm[v["name"]].append(v["configMap"]["name"])
        for src in (v.get("projected") or {}).get("sources") or []:
            if (src.get("configMap") or {}).get("name"):
                vol_cm[v["name"]].append(src["configMap"]["name"])
    for c in (spec.get("containers") or []) + (spec.get("initContainers") or []) + (spec.get("ephemeralContainers") or []):
        cname = c.get("name")
        for e in c.get("env") or []:
            name = ((e.get("valueFrom") or {}).get("configMapKeyRef") or {}).get("name")
            if name:
                out[name]["modes"].add("env")
                out[name]["containers"].add(cname)
        for ef in c.get("envFrom") or []:
            name = (ef.get("configMapRef") or {}).get("name")
            if name:
                out[name]["modes"].add("env")
                out[name]["containers"].add(cname)
        for m in c.get("volumeMounts") or []:
            for name in vol_cm.get(m.get("name"), []):
                out[name]["modes"].add("subpath" if m.get("subPath") or m.get("subPathExpr") else "file")
                out[name]["containers"].add(cname)
    for names in vol_cm.values():  # a volume declared but mounted nowhere still counts as a file reference
        for name in names:
            if not out[name]["modes"]:
                out[name]["modes"].add("file")
    return dict(out)


SYSTEM_CONFIGMAPS = {"kube-root-ca.crt", "openshift-service-ca.crt"}  # injected into every namespace and into every pod's service account token volume by the control plane; refreshed by the kubelet, never edited by a person


def data_change(md: dict) -> tuple | None:
    """(time, manager) of the latest managedFields entry that wrote `data` or `binaryData`. Entries that only touched labels or annotations
    (kubectl label, an Argo CD tracking annotation, leader-election annotations rewritten every few seconds) are not changes of the configuration."""
    best = None
    for e in md.get("managedFields") or []:
        fields = e.get("fieldsV1") or {}
        if not isinstance(fields, dict) or not ({"f:data", "f:binaryData"} & set(fields)):
            continue
        t = parse_ts(e.get("time"))
        if t and (best is None or t > best[0]):
            best = (t, e.get("manager"))
    return best


def config_changes(cx) -> dict | None:
    cms = [c for c in objects(cx.snap, "configmaps") if (c.get("metadata") or {}).get("name") not in SYSTEM_CONFIGMAPS]
    changed: dict[tuple, dict] = {}
    with_time = 0
    for c in cms:
        md = c.get("metadata") or {}
        if not any(e.get("time") for e in md.get("managedFields") or []):
            continue
        with_time += 1
        dc = data_change(md)
        if c.get("immutable"):
            # an immutable ConfigMap cannot be edited; the only change is delete and recreate under the same name, and then the creation time is the change time
            created = parse_ts(md.get("creationTimestamp"))
            if created:
                dc = (created, (dc[1] if dc else None) or "recreated")
        if dc:
            changed[(md.get("namespace"), md.get("name"))] = {"changed_at": dc[0], "changed_by": dc[1], "immutable": bool(c.get("immutable"))}
    if not with_time:
        return None
    rows: dict[tuple, dict] = {}
    pods_checked = 0
    for p in cx.pods:
        st = p.get("status") or {}
        pod_started = parse_ts(st.get("startTime"))
        if st.get("phase") != "Running" or not pod_started:
            continue
        pods_checked += 1
        ns, pod = p["metadata"]["namespace"], p["metadata"]["name"]
        # env and subPath are resolved when a container starts, so a container restarted after the change already holds the new value: compare with the container's own start
        container_started = {}
        for cs in (st.get("containerStatuses") or []) + (st.get("initContainerStatuses") or []) + (st.get("ephemeralContainerStatuses") or []):
            t = parse_ts((((cs.get("state") or {}).get("running") or {}).get("startedAt")) or (((cs.get("state") or {}).get("terminated") or {}).get("startedAt")))
            if t:
                container_started[cs.get("name")] = t
        for name, ref in cm_refs(p.get("spec") or {}).items():
            cm = changed.get((ns, name))
            if not cm:
                continue
            starts = [container_started[c] for c in ref["containers"] if c in container_started]
            started = min(starts) if starts else pod_started  # the oldest reader decides: a sidecar restarted after the change does not refresh the app container next to it
            if cm["changed_at"] <= started:
                continue
            modes = ref["modes"]
            restart_needed = bool(modes & {"env", "subpath"})
            r = rows.setdefault(
                (ns, name),
                {
                    "namespace": ns,
                    "configmap": name,
                    "changed_at": cm["changed_at"].isoformat(),
                    "changed_by": cm["changed_by"] or "unknown manager",
                    "prod": ns in cx.prod,
                    "pods": [],
                    "workloads": [],
                    "restart_needed_pods": 0,
                    "refresh_only_pods": 0,
                    "ref_modes": [],
                    "oldest_pod_start": started.isoformat(),
                    "stale_hours": 0,
                },
            )
            r["pods"].append(pod)
            wl = workload_of(f"{ns}/{pod}")
            if wl not in r["workloads"]:
                r["workloads"].append(wl)
            for m in modes:
                if m not in r["ref_modes"]:
                    r["ref_modes"].append(m)
            if restart_needed:
                r["restart_needed_pods"] += 1
            else:
                r["refresh_only_pods"] += 1
            r["oldest_pod_start"] = min(r["oldest_pod_start"], started.isoformat())
            r["stale_hours"] = max(r["stale_hours"], round((cm["changed_at"] - started).total_seconds() / 3600, 1))
    stale = sorted(rows.values(), key=lambda r: (-r["restart_needed_pods"], -r["stale_hours"]))
    return {
        "configmaps_with_time": with_time,
        "configmaps_total": len(cms),
        "pods_checked": pods_checked,
        "stale": stale,
        "restart_needed": [r for r in stale if r["restart_needed_pods"]],
        "refresh_only": [r for r in stale if not r["restart_needed_pods"]],
        "note": "changed_at is the latest managedFields entry that wrote data or binaryData; a re-apply of identical content (Argo CD sync, helm upgrade) also refreshes it, and so does a label-only or annotation-only write by the same manager that wrote the data earlier (the apiserver refreshes the manager's whole entry); a label-only write by another manager does not. Compared with the start of the containers that read the ConfigMap, so a container restarted after the change is not listed. File mounts are refreshed by the kubelet, env/envFrom/subPath are not. Secrets are not collected and not judged",
    }

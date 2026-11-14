"""Structure and hygiene summary.

Inputs: tools/polaris.json (Polaris audit, failures only), tools/pluto.json and tools/kubent.json (deprecated APIs), tools/helm-list.json (release metadata only; user values are never collected), aws/list-insights.json (EKS Upgrade Insights),
metrics/apiserver_requested_deprecated_apis·secrets_by_name·secret_types, objects/(deployments·statefulsets·daemonsets·cronjobs·jobs·pods·configmaps·replicasets·persistentvolumeclaims·persistentvolumes·
services·ingresses·serviceaccounts·customresourcedefinitions·namespaces·externalsecrets·applications.argoproj.io), summary.webhooks.

Result: the `hygiene` section of summary.json: polaris (score, counts per check, failures per workload; the Security category is used by the security section), deprecated (merged Pluto, kubent, metrics and EKS insights), helm (release status, chart, age),
images (:latest, no tag, digest, pullPolicy Always), labels (workloads without standard labels, workloads in the default namespace), orphans (unreferenced ConfigMaps/Secrets, Pending PVCs, Released PVs, Services without pods, 0-replica ReplicaSets),
crds (CRDs with 0 objects, webhook count), templating (share of workloads managed by Helm/Argo CD, unmanaged prod workloads). Shape is described in SKILL.md.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from ...foundations import scrub
from ...foundations.snapshot import load_json, metric_doc, metric_rows, objects, parse_ts, taken_at
from ...foundations.workload import key as wl_key
from .configchanges import config_changes
from .toolreports import deprecated, helm, polaris

OPERATOR_PREFIXES = (
    "argocd-",
    "repo-",
    "alertmanager-",
    "prometheus-",
    "cert-manager-",
    "letsencrypt-",
    "loki-",
    "grafana-",
    "external-secrets-",
    "keda-",
    "karpenter-",
    "metallb-",
    "ingress-nginx-",
    "nginx-ingress-",
    "reloader-",
    "arc-",
    "kube-prometheus-stack-",
    "sh.helm",
)
WELL_KNOWN_CM = {
    "kube-root-ca.crt",
    "istio-ca-root-cert",
    "cluster-info",
    "extension-apiserver-authentication",
    "coredns",
    "kube-proxy",
    "kube-proxy-config",
    "aws-auth",
    "amazon-vpc-cni",
    "local-path-config",
    "chart-content-",
    "kubeadm-config",
    "kubelet-config",
}
SECRET_TYPES_SKIP = {"kubernetes.io/service-account-token", "helm.sh/release.v1", "bootstrap.kubernetes.io/token", "kubernetes.io/dockercfg"}


class Ctx:
    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        inv = inv or {}
        self.prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
        self.platform = (inv.get("cluster") or {}).get("platform")
        self.server_version = (inv.get("cluster") or {}).get("server_version")
        self.now = taken_at(inv)  # every age in this module is measured from the snapshot time (#165)
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs", "CronJob")):
            for o in objects(snap, stem):
                self.workloads.append((kind, o))
        self.pods = objects(snap, "pods")
        self.argo_apps = objects(snap, "applications.argoproj.io")
        # what Argo CD manages, whatever its tracking method: Application status.resources (argoproj/argo-cd pkg/apis/application/v1alpha1/types.go:1018@v2.13.0, :1151@v3.6.1) (#124 K2-5)
        self.argo_app_of = {((r.get("kind") or "").lower(), r.get("namespace"), r.get("name")): a["metadata"]["name"] for a in self.argo_apps for r in (a.get("status") or {}).get("resources") or []}
        self.argo_managed = set(self.argo_app_of)

    @staticmethod
    def tpl(kind, o) -> dict:
        if kind == "CronJob":
            return ((((o.get("spec") or {}).get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
        return ((o.get("spec") or {}).get("template") or {}).get("spec") or {}


WELL_KNOWN_NODE_LABEL_RE = re.compile(
    r"^(kubernetes\.io/|node\.kubernetes\.io/|topology\.kubernetes\.io/|beta\.kubernetes\.io/|failure-domain\.beta\.kubernetes\.io/|karpenter\.sh/|karpenter\.k8s\.aws/|eks\.amazonaws\.com/|k8s\.io/|node-role\.kubernetes\.io/|node\.k3s\.io/|k3s\.io/)"
)


def _node_labels(cx: Ctx) -> dict:
    """Node label keys that workloads depend on via nodeSelector or required nodeAffinity — user labels the platform does not guarantee can disappear on node replacement or upgrade (Reddit 2023 upgrade thread: labels changed mid-upgrade)."""
    nodes = objects(cx.snap, "nodes")
    node_keys: Counter = Counter()
    for n in nodes:
        for k in (n.get("metadata") or {}).get("labels") or {}:
            node_keys[k] += 1
    used: dict[str, dict] = {}
    for kind, o in cx.workloads:
        tpl = cx.tpl(kind, o)
        keys = set((tpl.get("nodeSelector") or {}).keys())
        req = (((tpl.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []
        for term in req:
            for me in term.get("matchExpressions") or []:
                if me.get("key") and me.get("operator") in (
                    None,
                    "In",
                    "Exists",
                    "Gt",
                    "Lt",
                ):  # NotIn/DoesNotExist mean "nodes without this label", so they are not a dependency (e.g. avoiding Fargate with eks.amazonaws.com/compute-type NotIn)
                    keys.add(me["key"])
        for t in tpl.get("topologySpreadConstraints") or []:
            if t.get("topologyKey"):
                keys.add(t["topologyKey"])
        for k in keys:
            d = used.setdefault(k, {"key": k, "workloads": [], "prod_workloads": 0, "nodes_with_label": node_keys.get(k, 0), "nodes_total": len(nodes), "well_known": bool(WELL_KNOWN_NODE_LABEL_RE.match(k))})
            d["workloads"].append(wl_key(kind, o))
            d["prod_workloads"] += 1 if o["metadata"]["namespace"] in cx.prod else 0
    rows = sorted(used.values(), key=lambda r: (r["well_known"], -r["prod_workloads"], r["key"]))  # full key: deterministic output
    for r in rows:
        r["workload_count"] = len(r["workloads"])
        r["workloads"] = r["workloads"]
    return {
        "keys_used": len(rows),
        "rows": rows,
        "custom_keys": [r["key"] for r in rows if not r["well_known"]],
        "custom_prod": [r["key"] for r in rows if not r["well_known"] and r["prod_workloads"]],
        "keys_on_no_node": [r["key"] for r in rows if r["nodes_with_label"] == 0],
        "keys_on_single_node": [r["key"] for r in rows if r["nodes_with_label"] == 1 and r["nodes_total"] > 1],
    }


# ---------- Polaris ----------


# ---------- Deprecated API ----------


# ---------- Helm ----------


# ---------- images ----------


def _images(cx: Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        tpl = cx.tpl(kind, o)
        for c in (tpl.get("containers") or []) + (tpl.get("initContainers") or []):
            img = c.get("image") or ""
            last = img.rsplit("/", 1)[-1]
            digest = "@sha256:" in img
            tag = last.split(":", 1)[1] if ":" in last and not digest else None
            kind_tag = "digest" if digest else ("latest" if tag == "latest" else ("untagged" if tag is None else "tag"))
            pull = c.get("imagePullPolicy") or ("Always" if kind_tag in ("latest", "untagged") else "IfNotPresent")
            registry = img.split("/")[0] if "/" in img and ("." in img.split("/")[0] or ":" in img.split("/")[0]) else "docker.io"
            if kind_tag in ("latest", "untagged") or (pull == "Always" and kind_tag == "tag"):
                rows.append(
                    {
                        "workload": wl_key(kind, o),
                        "namespace": o["metadata"]["namespace"],
                        "prod": o["metadata"]["namespace"] in cx.prod,
                        "container": c.get("name"),
                        "image": img[:160],
                        "tag_kind": kind_tag,
                        "pull_policy": pull,
                        "registry": registry,
                        "holder": bool(re.search(r"\b(sleep|pause|tail -f)\b", " ".join([str(a) for a in (c.get("command") or [])] + [str(a) for a in (c.get("args") or [])]))),  # prepull holder containers that pre-fetch images onto nodes
                        "mutable": kind_tag in ("latest", "untagged"),
                        "always_pull_with_tag": pull == "Always" and kind_tag == "tag",
                    }
                )
    allc = sum(len(cx.tpl(k, o).get("containers") or []) for k, o in cx.workloads)
    return {
        "containers": allc,
        "rows": rows,
        "mutable": [r["workload"] + ":" + r["container"] for r in rows if r["mutable"]],
        "always_pull_with_tag": [r["workload"] + ":" + r["container"] for r in rows if r["always_pull_with_tag"]],
        "registries": dict(Counter((img.split("/")[0] if "/" in img and ("." in img.split("/")[0]) else "docker.io") for k, o in cx.workloads for c in (cx.tpl(k, o).get("containers") or []) for img in [c.get("image") or ""])),
    }


# ---------- labels and namespaces ----------


def _labels(cx: Ctx) -> dict:
    no_std = []
    default_ns = []
    total = 0
    for kind, o in cx.workloads:
        total += 1
        md = o["metadata"]
        labels = md.get("labels") or {}
        tl = (((o.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {} if kind != "CronJob" else {}
        if not any(k.startswith("app.kubernetes.io/") for k in list(labels) + list(tl)):
            no_std.append({"workload": wl_key(kind, o), "namespace": md["namespace"], "prod": md["namespace"] in cx.prod, "labels": dict(list(labels.items()))})
        if md["namespace"] == "default":
            default_ns.append({"workload": wl_key(kind, o), "prod": md["namespace"] in cx.prod})
    ns_names = [n["metadata"]["name"] for n in objects(cx.snap, "namespaces")]
    return {
        "workloads": total,
        "without_standard_labels": no_std,
        "standard_label_ratio": round(1 - len(no_std) / total, 2) if total else None,
        "default_namespace_workloads": default_ns,
        "namespaces": len(ns_names),
        "env_split": {"prod_like": sorted(cx.prod), "dev_like": sorted(n for n in ns_names if re.search(r"(^|-)(dev|stg|staging|test|qa)(-|$)", n))},
    }


# ---------- orphans ----------


def _orphans(cx: Ctx) -> dict:
    cm_refs: set[tuple] = set()
    sec_refs: set[tuple] = set()
    arg_texts: list[tuple] = []

    def collect(ns: str, tpl: dict):
        for v in tpl.get("volumes") or []:
            if v.get("configMap"):
                cm_refs.add((ns, v["configMap"].get("name")))
            if v.get("secret"):
                sec_refs.add((ns, v["secret"].get("secretName")))
            for src in (v.get("projected") or {}).get("sources") or []:
                if src.get("configMap"):
                    cm_refs.add((ns, src["configMap"].get("name")))
                if src.get("secret"):
                    sec_refs.add((ns, src["secret"].get("name")))
        for c in (tpl.get("containers") or []) + (tpl.get("initContainers") or []):
            for e in c.get("env") or []:
                vf = e.get("valueFrom") or {}
                if vf.get("configMapKeyRef"):
                    cm_refs.add((ns, vf["configMapKeyRef"].get("name")))
                if vf.get("secretKeyRef"):
                    sec_refs.add((ns, vf["secretKeyRef"].get("name")))
            for ef in c.get("envFrom") or []:
                if ef.get("configMapRef"):
                    cm_refs.add((ns, ef["configMapRef"].get("name")))
                if ef.get("secretRef"):
                    sec_refs.add((ns, ef["secretRef"].get("name")))
        for ips in tpl.get("imagePullSecrets") or []:
            sec_refs.add((ns, ips.get("name")))
        # Controllers that take it as an argument like --configmap=<ns>/<name> (ingress-nginx, argocd etc.). If the full name appears in an argument string it counts as a reference
        for c in tpl.get("containers") or []:
            for a in (c.get("args") or []) + (c.get("command") or []):
                arg_texts.append((ns, str(a)))

    for kind, o in cx.workloads:
        collect(o["metadata"]["namespace"], cx.tpl(kind, o))
    for p in cx.pods:
        collect(p["metadata"]["namespace"], p.get("spec") or {})
    for j in objects(cx.snap, "jobs.batch"):
        collect(j["metadata"]["namespace"], (((j.get("spec") or {}).get("template") or {}).get("spec") or {}))
    for ing in objects(cx.snap, "ingresses.networking.k8s.io"):
        for t in (ing.get("spec") or {}).get("tls") or []:
            if t.get("secretName"):
                sec_refs.add((ing["metadata"]["namespace"], t["secretName"]))
    for sa in objects(cx.snap, "serviceaccounts"):
        for s in (sa.get("secrets") or []) + (sa.get("imagePullSecrets") or []):
            sec_refs.add((sa["metadata"]["namespace"], s.get("name")))
    for es in objects(cx.snap, "externalsecrets.external-secrets.io"):
        sec_refs.add((es["metadata"]["namespace"], ((es.get("spec") or {}).get("target") or {}).get("name") or es["metadata"]["name"]))
    for cert in objects(cx.snap, "certificates.cert-manager.io"):
        sec_refs.add((cert["metadata"]["namespace"], (cert.get("spec") or {}).get("secretName")))
    for ta in objects(cx.snap, "triggerauthentications.keda.sh"):
        for r in (ta.get("spec") or {}).get("secretTargetRef") or []:
            sec_refs.add((ta["metadata"]["namespace"], r.get("name")))
    for iss in objects(cx.snap, "issuers.cert-manager.io") + objects(cx.snap, "clusterissuers.cert-manager.io"):
        pk = (((iss.get("spec") or {}).get("acme") or {}).get("privateKeySecretRef") or {}).get("name")
        if pk:
            sec_refs.add((iss["metadata"].get("namespace") or "cert-manager", pk))

    # Recursively look for secretRef/secretName inside other CRs (SecretStore, ClusterSecretStore, Provider, Grafana datasource etc.) — names only, not values. Seen on a k3s: the credentials Secret used by a ClusterSecretStore was reported as an orphan
    def walk(obj, ns_default):
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if kl in ("secretname", "secret") and isinstance(v, str):
                    sec_refs.add((ns_default, v))
                elif "secret" in kl and isinstance(v, dict) and isinstance(v.get("name"), str):
                    sec_refs.add((v.get("namespace") or ns_default, v["name"]))
                walk(v, ns_default)
        elif isinstance(obj, list):
            for x in obj:
                walk(x, ns_default)

    for f in sorted((cx.snap / "objects").glob("*.*.json")):  # a stem with a group = CRD objects
        for o in (load_json(f) or {}).get("items") or []:
            walk(o.get("spec") or {}, (o.get("metadata") or {}).get("namespace") or "cert-manager")

    def in_args(ns: str, name: str) -> bool:
        return any(n == ns and name in a for n, a in arg_texts)

    # ConfigMap
    orphan_cm = []
    cms = objects(cx.snap, "configmaps")
    # Large ConfigMaps: etcd object limit is 1 MiB (apiserver --max-request-bytes is 1.5 MiB). Approximated by the character count of data+binaryData
    big_cm = []
    for c in cms:
        size = scrub.configmap_chars(c)  # values are not in the snapshot; the scrub record keeps the original character count
        if size >= 256 * 1024:
            big_cm.append({"namespace": c["metadata"]["namespace"], "name": c["metadata"]["name"], "kib": round(size / 1024), "keys": len(c.get("data") or {}) + len(c.get("binaryData") or {}), "prod": c["metadata"]["namespace"] in cx.prod})
    big_cm.sort(key=lambda r: -r["kib"])
    for cm in cms:
        md = cm["metadata"]
        ns, name = md["namespace"], md["name"]
        if (ns, name) in cm_refs or md.get("ownerReferences") or any(name.startswith(w) for w in WELL_KNOWN_CM) or ns.startswith("kube-") or in_args(ns, name) or name.startswith(OPERATOR_PREFIXES):
            continue
        labels = md.get("labels") or {}
        ann = md.get("annotations") or {}
        if any(k in labels for k in ("grafana_dashboard", "grafana_datasource", "grafana_alert")) or "control-plane.alpha.kubernetes.io/leader" in ann or labels.get("owner") == "helm":
            continue
        if name.startswith("sh.helm.release") or name.endswith("-lock") or "leader" in name:
            continue
        orphan_cm.append(
            {
                "namespace": ns,
                "name": name,
                "prod": ns in cx.prod,
                "keys": sorted((cm.get("data") or {}).keys()),
                "age_days": round((cx.now - parse_ts(md.get("creationTimestamp"))).total_seconds() / 86400) if parse_ts(md.get("creationTimestamp")) else None,
            }
        )
    # Secrets (name and type only, from metrics)
    types = {(ln.get("namespace"), ln.get("secret")): ln.get("type") for ln, _ in metric_rows(cx.snap, "secret_types")}
    orphan_sec = []
    secrets_read = bool((metric_doc(cx.snap, "secrets_by_name") or {}).get("ok"))  # kube_secret_info through Prometheus; without it the orphan list means nothing (#141)
    secret_names = {(ln.get("namespace"), ln.get("secret")) for ln, _ in metric_rows(cx.snap, "secrets_by_name")}
    for ns, name in sorted(secret_names, key=lambda x: (str(x[0]), str(x[1]))):
        if not ns or not name or (ns, name) in sec_refs or ns.startswith("kube-"):
            continue
        t = types.get((ns, name))
        if t in SECRET_TYPES_SKIP or name.startswith("default-token") or name.endswith("-token") or name.startswith(OPERATOR_PREFIXES) or in_args(ns, name):
            continue
        orphan_sec.append({"namespace": ns, "name": name, "type": t, "prod": ns in cx.prod})
    # PVC·PV
    pvc_unbound = [
        {"namespace": p["metadata"]["namespace"], "name": p["metadata"]["name"], "phase": (p.get("status") or {}).get("phase"), "storage_class": (p.get("spec") or {}).get("storageClassName"), "prod": p["metadata"]["namespace"] in cx.prod}
        for p in objects(cx.snap, "persistentvolumeclaims")
        if (p.get("status") or {}).get("phase") != "Bound"
    ]
    pv_released = [
        {
            "name": p["metadata"]["name"],
            "phase": (p.get("status") or {}).get("phase"),
            "capacity": ((p.get("spec") or {}).get("capacity") or {}).get("storage"),
            "claim": ((p.get("spec") or {}).get("claimRef") or {}).get("name"),
            "reclaim": (p.get("spec") or {}).get("persistentVolumeReclaimPolicy"),
        }
        for p in objects(cx.snap, "persistentvolumes")
        if (p.get("status") or {}).get("phase") in ("Released", "Failed")
    ]
    pvc_bound = {(p["metadata"]["namespace"], p["metadata"]["name"]) for p in objects(cx.snap, "persistentvolumeclaims")}
    pvc_used = set()
    for kind, o in cx.workloads:
        for v in cx.tpl(kind, o).get("volumes") or []:
            if v.get("persistentVolumeClaim"):
                pvc_used.add((o["metadata"]["namespace"], v["persistentVolumeClaim"].get("claimName")))
        if kind == "StatefulSet":
            start = (((o.get("spec") or {}).get("ordinals") or {}).get("start")) or 0  # pods are numbered from spec.ordinals.start (kubernetes/kubernetes pkg/controller/statefulset/stateful_set_utils.go:100-102@v1.37.2) (#124 K2-2)
            for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
                for i in range(start, start + ((o.get("spec") or {}).get("replicas") or 1) + 2):
                    pvc_used.add((o["metadata"]["namespace"], f"{vct['metadata']['name']}-{o['metadata']['name']}-{i}"))
    for p in cx.pods:
        for v in (p.get("spec") or {}).get("volumes") or []:
            if v.get("persistentVolumeClaim"):
                pvc_used.add((p["metadata"]["namespace"], v["persistentVolumeClaim"].get("claimName")))
    pvc_unused = [{"namespace": ns, "name": n, "prod": ns in cx.prod} for ns, n in sorted(pvc_bound - pvc_used)]
    # Services without pods (selector matches no pod)
    pod_labels = defaultdict(list)
    for p in cx.pods:
        pod_labels[p["metadata"]["namespace"]].append(p["metadata"].get("labels") or {})
    svc_no_pods = []
    for s in objects(cx.snap, "services"):
        sel = (s.get("spec") or {}).get("selector")
        if not sel or (s.get("spec") or {}).get("type") == "ExternalName":
            continue
        ns = s["metadata"]["namespace"]
        if ns.startswith("kube-"):
            continue  # kube-prometheus-stack's control plane Services (no pods on EKS/k3s is normal) are handled by the observability section
        if not any(all(ln.get(k) == v for k, v in sel.items()) for ln in pod_labels.get(ns, [])):
            svc_no_pods.append({"namespace": ns, "name": s["metadata"]["name"], "selector": sel, "prod": ns in cx.prod})
    rss = objects(cx.snap, "replicasets.apps")
    zero_rs = [r for r in rss if ((r.get("spec") or {}).get("replicas") or 0) == 0]
    rhl = Counter(((o.get("spec") or {}).get("revisionHistoryLimit", 10)) for k, o in cx.workloads if k == "Deployment")
    rh_zero = [
        {"workload": f"{o['metadata']['namespace']}/{k.lower()}/{o['metadata']['name']}", "namespace": o["metadata"]["namespace"], "prod": o["metadata"]["namespace"] in cx.prod}
        for k, o in cx.workloads
        if k in ("Deployment", "StatefulSet", "DaemonSet") and (o.get("spec") or {}).get("revisionHistoryLimit") == 0
    ]  # with 0, kubectl rollout undo is impossible
    return {
        "configmaps_total": len(cms),
        "orphan_configmaps": orphan_cm,
        "large_configmaps": big_cm,
        "secrets_read": secrets_read,
        "secrets_total": len(secret_names) if secrets_read else None,
        "orphan_secrets": orphan_sec if secrets_read else None,
        "pvc_unbound": pvc_unbound,
        "pvc_unused": pvc_unused,
        "pv_released": pv_released,
        "services_without_pods": svc_no_pods,
        "replicasets_total": len(rss),
        "replicasets_zero": len(zero_rs),
        "revision_history_limits": {str(k): v for k, v in rhl.items()},
        "revision_history_zero": rh_zero,
    }


# ---------- CRDs and webhooks ----------


def _crds(cx: Ctx, summary_webhooks: dict | None) -> dict:
    crds = objects(cx.snap, "customresourcedefinitions")
    import os

    files = {f[:-5] for f in os.listdir(cx.snap / "objects")} if (cx.snap / "objects").is_dir() else set()
    rows = []
    for c in crds:
        sp = c.get("spec") or {}
        stem = f"{(sp.get('names') or {}).get('plural')}.{sp.get('group')}"
        n = len(objects(cx.snap, stem)) if stem in files else None
        rows.append({"crd": c["metadata"]["name"], "group": sp.get("group"), "objects": n, "scope": sp.get("scope")})
    by_group = Counter(r["group"] for r in rows)
    zero = [r["crd"] for r in rows if r["objects"] == 0]
    return {
        "count": len(crds),
        "groups": dict(by_group),
        "zero_object_crds": zero,
        "zero_object_count": len(zero),
        "not_dumped": [r["crd"] for r in rows if r["objects"] is None],
        "zero_by_group": dict(Counter(r["group"] for r in rows if r["objects"] == 0)),
        "webhooks": (summary_webhooks or {}).get("count") if isinstance(summary_webhooks, dict) else None,
    }


# ---------- templating / GitOps management ----------


def _templating(cx: Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        md = o["metadata"]
        labels = md.get("labels") or {}
        ann = md.get("annotations") or {}
        managed = None
        # Who declares the workload, by name, from what the snapshot holds: the report says "change it where it is declared" and names that place only with this evidence
        argocd_app = helm_release = None
        if labels.get("app.kubernetes.io/managed-by") == "Helm" or any(k.startswith("meta.helm.sh/") for k in ann):
            managed = "helm"
            helm_release = ann.get("meta.helm.sh/release-name")
        # Argo CD's default tracking is the label `app.kubernetes.io/instance` = application name (argoproj/argo-cd common/common.go:161@v2.13.0, :190@v3.6.1), which Helm releases also set, so a
        # workload counts as Argo-managed when an Application lists it in status.resources; the configured `argocd.argoproj.io/instance` label and the tracking annotation are exact on their own (#124 K2-5)
        if "argocd.argoproj.io/tracking-id" in ann or "argocd.argoproj.io/instance" in labels or (kind.lower(), md["namespace"], md["name"]) in cx.argo_managed:
            managed = "argocd" + ("+helm" if managed == "helm" else "")
            # the tracking annotation is `<application>:<group>/<kind>:<namespace>/<name>` (argoproj/argo-cd util/argo/resource_tracking.go:199@v2.13.0, :234@v3.6.1); status.resources names the application whatever the tracking method
            argocd_app = cx.argo_app_of.get((kind.lower(), md["namespace"], md["name"])) or (ann.get("argocd.argoproj.io/tracking-id") or "").split(":", 1)[0] or None
        if any(k.startswith(("kustomize.toolkit.fluxcd.io/", "helm.toolkit.fluxcd.io/")) for k in labels):
            managed = "flux"
        # EKS add-ons carry the labels `app.kubernetes.io/managed-by: EKS` and `eks.amazonaws.com/component` (observed on the add-on workloads; no public manifest, #124 K2-4)
        if labels.get("app.kubernetes.io/managed-by") in ("eks", "EKS") or "eks.amazonaws.com/component" in labels or md["namespace"] == "kube-system":
            managed = managed or "platform"
        rows.append(
            {
                "workload": wl_key(kind, o),
                "namespace": md["namespace"],
                "prod": md["namespace"] in cx.prod,
                "managed_by": managed,
                "argocd_app": argocd_app,
                "helm_release": helm_release,
                "last_applied": "kubectl.kubernetes.io/last-applied-configuration" in ann,
            }
        )
    apps = cx.argo_apps
    return {
        "workloads": len(rows),
        "by_manager": dict(Counter(r["managed_by"] or "none" for r in rows)),
        "unmanaged": [{k: v for k, v in r.items() if k not in ("argocd_app", "helm_release")} for r in rows if not r["managed_by"]],
        "owners": [{k: r[k] for k in ("workload", "managed_by", "argocd_app", "helm_release") if r[k]} for r in rows if r["managed_by"] and r["managed_by"] != "platform"],
        "unmanaged_prod": [r["workload"] for r in rows if not r["managed_by"] and r["prod"]],
        "argocd_applications": len(apps),
        "argocd_apps": [
            {
                "name": a["metadata"]["name"],
                "sync": ((a.get("status") or {}).get("sync") or {}).get("status"),
                "health": ((a.get("status") or {}).get("health") or {}).get("status"),
                "automated": bool(((a.get("spec") or {}).get("syncPolicy") or {}).get("automated")),
                "prune": bool((((a.get("spec") or {}).get("syncPolicy") or {}).get("automated") or {}).get("prune")),
                "dest_ns": ((a.get("spec") or {}).get("destination") or {}).get("namespace"),
            }
            for a in apps
        ],
    }


def analyze(snap: Path, inv: dict | None, summary_webhooks: dict | None = None) -> dict:
    cx = Ctx(snap, inv)
    now = cx.now
    return {
        "polaris": polaris(cx),
        "deprecated": deprecated(cx),
        "helm": helm(cx, now),
        "images": _images(cx),
        "labels": _labels(cx),
        "node_labels": _node_labels(cx),
        "orphans": _orphans(cx),
        "crds": _crds(cx, summary_webhooks),
        "templating": _templating(cx),
        "failed_pods": _failed_pods(cx, now),
        "ephemeral": _ephemeral(cx),
        "config_changes": config_changes(cx),
    }


def _failed_pods(cx: Ctx, now) -> dict:
    """Pods left in the Failed phase (Evicted, UnexpectedAdmissionError, Job pods after OOM, etc.). Job-owned pods belong to the ttl check (resilience.finished-jobs-accumulating) and are excluded.
    They are not removed until kube-controller-manager's terminated-pod-gc-threshold (default 12,500), cluttering `kubectl get pods` and consuming etcd."""
    rows = []
    by_reason: Counter = Counter()
    by_ns: Counter = Counter()
    for p in cx.pods:
        st = p.get("status") or {}
        if st.get("phase") != "Failed":
            continue
        own = next((o for o in p["metadata"].get("ownerReferences") or []), {})
        if own.get("kind") == "Job":
            continue
        reason = st.get("reason") or next((((c.get("lastState") or {}).get("terminated") or {}).get("reason") for c in st.get("containerStatuses") or [] if (c.get("lastState") or {}).get("terminated")), None) or "Failed"
        ns = p["metadata"]["namespace"]
        created = parse_ts(p["metadata"].get("creationTimestamp"))
        age_h = round((now - created).total_seconds() / 3600, 1) if created else None
        by_reason[reason] += 1
        by_ns[ns] += 1
        rows.append(
            {
                "namespace": ns,
                "pod": p["metadata"]["name"],
                "owner_kind": own.get("kind"),
                "reason": reason,
                "message": str(st.get("message") or "")[:160],
                "age_h": age_h,
                "node": (p.get("spec") or {}).get("nodeName"),
                "prod": ns in cx.prod,
            }
        )
    rows.sort(key=lambda r: -(r["age_h"] or 0))
    return {
        "count": len(rows),
        "by_reason": dict(by_reason),
        "by_namespace": dict(by_ns.most_common()),
        "rows": rows,
        "oldest_h": rows[0]["age_h"] if rows else None,
        "summary": {
            "count": len(rows),
            "by_reason": dict(by_reason),
            "by_namespace": dict(by_ns.most_common()),
            "oldest_h": rows[0]["age_h"] if rows else None,
            "prod": sum(1 for r in rows if r["prod"]),
            "sample": [f"{r['namespace']}/{r['pod']}" for r in rows],
        },
    }


def _ephemeral(cx: Ctx) -> dict:
    """ephemeral-storage request/limit and emptyDir sizeLimit. Without them, when a pod fills the node disk, kubelet cannot tell who is to blame (DiskPressure) and evicts arbitrarily (seen on a real cluster: a node at 87% disk)."""
    containers = 0
    with_req = 0
    with_lim = 0
    no_req_prod: set = set()
    emptydir_nolimit: set = set()
    emptydir_nolimit_prod: set = set()
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        tpl = cx.tpl(kind, o)
        wl = wl_key(kind, o)
        for c in tpl.get("containers") or []:
            containers += 1
            res = c.get("resources") or {}
            if (res.get("requests") or {}).get("ephemeral-storage"):
                with_req += 1
            elif ns in cx.prod:
                no_req_prod.add(wl)
            if (res.get("limits") or {}).get("ephemeral-storage"):
                with_lim += 1
        for v in tpl.get("volumes") or []:
            ed = v.get("emptyDir")
            if ed is not None and not ed.get("sizeLimit") and ed.get("medium") != "Memory":
                emptydir_nolimit.add(wl)
                if ns in cx.prod:
                    emptydir_nolimit_prod.add(wl)
    return {
        "containers": containers,
        "with_request": with_req,
        "with_limit": with_lim,
        "request_ratio": round(with_req / containers, 3) if containers else None,
        "prod_without_request": sorted(no_req_prod),
        "emptydir_without_sizelimit": sorted(emptydir_nolimit),
        "emptydir_without_sizelimit_prod": sorted(emptydir_nolimit_prod),
        "summary": {
            "containers": containers,
            "with_request": with_req,
            "request_ratio": round(with_req / containers, 3) if containers else None,
            "prod_without_request": len(no_req_prod),
            "emptydir_without_sizelimit": len(emptydir_nolimit),
            "emptydir_without_sizelimit_prod": sorted(emptydir_nolimit_prod),
        },
    }

"""Structure and hygiene summary.

Inputs: tools/polaris.json (Polaris audit, failures only), tools/pluto.json and tools/kubent.json (deprecated APIs), tools/helm-list.json, aws/list-insights.json (EKS Upgrade Insights),
metrics/apiserver_requested_deprecated_apis·secrets_by_name·secret_types, objects/(deployments·statefulsets·daemonsets·cronjobs·jobs·pods·configmaps·replicasets·persistentvolumeclaims·persistentvolumes·
services·ingresses·serviceaccounts·customresourcedefinitions·namespaces·externalsecrets·applications.argoproj.io), summary.webhooks.

Result: the `hygiene` section of summary.json: polaris (score, counts per check, failures per workload; the Security category is used by the security section), deprecated (merged Pluto, kubent, metrics and EKS insights), helm (release status, chart, age),
images (:latest, no tag, digest, pullPolicy Always), labels (workloads without standard labels, workloads in the default namespace), orphans (unreferenced ConfigMaps/Secrets, Pending PVCs, Released PVs, Services without pods, 0-replica ReplicaSets),
crds (CRDs with 0 objects, webhook count), templating (share of workloads managed by Helm/Argo CD, unmanaged prod workloads). Shape is described in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import scrub
from .snapshot import load_json, objects

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
SECURITY_CATEGORY = "Security"


def _metric_rows(snap: Path, qid: str):
    m = load_json(snap / "metrics" / f"{qid}.json")
    for s in (m or {}).get("result") or []:
        try:
            yield (s.get("metric") or {}), float(s["value"][1])
        except (KeyError, ValueError, TypeError, IndexError):
            continue


def _ts(s):
    if not s:
        return None
    s = str(s)
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        pass
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", s)  # helm: 2025-12-29 02:07:42.385466 +0900 KST
    if m:
        tz = re.search(r"([+-]\d{4}) ", s)
        d = _dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        if tz:
            sign = 1 if tz.group(1)[0] == "+" else -1
            d = d.replace(tzinfo=_dt.timezone(sign * _dt.timedelta(hours=int(tz.group(1)[1:3]), minutes=int(tz.group(1)[3:5]))))
        return d
    return None


class _Ctx:
    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        inv = inv or {}
        self.prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
        self.platform = (inv.get("cluster") or {}).get("platform")
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs.batch", "CronJob")):
            for o in objects(snap, stem):
                self.workloads.append((kind, o))
        self.pods = objects(snap, "pods")

    @staticmethod
    def tpl(kind, o) -> dict:
        if kind == "CronJob":
            return ((((o.get("spec") or {}).get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
        return ((o.get("spec") or {}).get("template") or {}).get("spec") or {}

    def key(self, kind, o) -> str:
        return f"{o['metadata']['namespace']}/{kind.lower()}/{o['metadata']['name']}"


WELL_KNOWN_NODE_LABEL_RE = re.compile(
    r"^(kubernetes\.io/|node\.kubernetes\.io/|topology\.kubernetes\.io/|beta\.kubernetes\.io/|failure-domain\.beta\.kubernetes\.io/|karpenter\.sh/|karpenter\.k8s\.aws/|eks\.amazonaws\.com/|k8s\.io/|node-role\.kubernetes\.io/|node\.k3s\.io/|k3s\.io/)"
)


def _node_labels(cx: _Ctx) -> dict:
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
            d["workloads"].append(cx.key(kind, o))
            d["prod_workloads"] += 1 if o["metadata"]["namespace"] in cx.prod else 0
    rows = sorted(used.values(), key=lambda r: (r["well_known"], -r["prod_workloads"], r["key"]))  # full key: deterministic output
    for r in rows:
        r["workload_count"] = len(r["workloads"])
        r["workloads"] = r["workloads"][:8]
    return {
        "keys_used": len(rows),
        "rows": rows,
        "custom_keys": [r["key"] for r in rows if not r["well_known"]],
        "custom_prod": [r["key"] for r in rows if not r["well_known"] and r["prod_workloads"]],
        "keys_on_no_node": [r["key"] for r in rows if r["nodes_with_label"] == 0],
        "keys_on_single_node": [r["key"] for r in rows if r["nodes_with_label"] == 1 and r["nodes_total"] > 1],
    }


# ---------- Polaris ----------


def _polaris(cx: _Ctx) -> dict:
    d = load_json(cx.snap / "tools" / "polaris.json")
    if not d:
        return {"present": False, "note": "tools/polaris.json missing (polaris not installed or not collected yet)"}
    by_check: Counter = Counter()
    sev_of: dict[str, str] = {}
    cat_of: dict[str, str] = {}
    rows = []
    for r in d.get("Results") or []:
        failed = []

        def take(res: dict, where: str):
            for cid, v in (res or {}).items():
                if v.get("Success"):
                    continue
                failed.append({"check": cid, "severity": v.get("Severity"), "category": v.get("Category"), "where": where, "message": v.get("Message")})
                by_check[cid] += 1
                sev_of[cid] = v.get("Severity")
                cat_of[cid] = v.get("Category")

        take(r.get("Results"), "controller")
        pr = r.get("PodResult") or {}
        take(pr.get("Results"), "pod")
        for cr in pr.get("ContainerResults") or []:
            take(cr.get("Results"), f"container:{cr.get('Name')}")
        if not failed:
            continue
        ns = r.get("Namespace") or ""
        rows.append(
            {
                "namespace": ns,
                "name": r.get("Name"),
                "kind": r.get("Kind"),
                "target": f"{ns}/{str(r.get('Kind')).lower()}/{r.get('Name')}",
                "prod": ns in cx.prod,
                "danger": sum(1 for f in failed if f["severity"] == "danger"),
                "warning": sum(1 for f in failed if f["severity"] == "warning"),
                "danger_checks": sorted({f["check"] for f in failed if f["severity"] == "danger"}),
                "non_security_danger": sorted({f["check"] for f in failed if f["severity"] == "danger" and f["category"] != SECURITY_CATEGORY}),
                "non_security_warning": sorted({f["check"] for f in failed if f["severity"] == "warning" and f["category"] != SECURITY_CATEGORY}),
                "security_danger": sorted({f["check"] for f in failed if f["severity"] == "danger" and f["category"] == SECURITY_CATEGORY}),
                "security_warning": sorted({f["check"] for f in failed if f["severity"] == "warning" and f["category"] == SECURITY_CATEGORY}),
                "failed": failed,
            }
        )
    rows.sort(key=lambda r: (-r["danger"], -r["warning"]))
    checks = [{"check": c, "severity": sev_of[c], "category": cat_of[c], "count": n} for c, n in by_check.most_common()]
    return {
        "present": True,
        "source": "tools/polaris.json",
        "score": d.get("Score"),
        "audited": len(d.get("Results") or []),
        "cluster_info": d.get("ClusterInfo"),
        "version": d.get("PolarisOutputVersion"),
        "checks": checks,
        "by_category": {f"{k[0]}/{k[1]}": v for k, v in Counter((cat_of[c], sev_of[c]) for c in by_check.elements()).items()} if by_check else {},
        "workloads": rows,
        "non_security_danger_workloads": [r["target"] for r in rows if r["non_security_danger"]],
        "security_danger_workloads": [r["target"] for r in rows if r["security_danger"]],
    }


# ---------- Deprecated API ----------


def _deprecated(cx: _Ctx) -> dict:
    items = []
    pl = load_json(cx.snap / "tools" / "pluto.json") or {}
    for it in pl.get("items") or []:
        items.append(
            {
                "source": "pluto",
                "kind": it.get("kind"),
                "name": it.get("name"),
                "namespace": it.get("namespace"),
                "api": it.get("api", {}).get("version") if isinstance(it.get("api"), dict) else it.get("api"),
                "deprecated_in": (it.get("api") or {}).get("deprecated-in") if isinstance(it.get("api"), dict) else it.get("deprecated-in"),
                "removed_in": (it.get("api") or {}).get("removed-in") if isinstance(it.get("api"), dict) else it.get("removed-in"),
                "replacement": (it.get("api") or {}).get("replacement-api") if isinstance(it.get("api"), dict) else it.get("replacement-api"),
                "deprecated": bool(it.get("deprecated")),
                "removed": bool(it.get("removed")),
            }
        )
    kb = load_json(cx.snap / "tools" / "kubent.json")
    for it in kb if isinstance(kb, list) else []:
        items.append(
            {
                "source": "kubent",
                "kind": it.get("Kind"),
                "name": it.get("Name"),
                "namespace": it.get("Namespace"),
                "api": it.get("ApiVersion"),
                "deprecated_in": it.get("Since"),
                "removed_in": it.get("Since"),
                "replacement": it.get("ReplaceWith"),
                "deprecated": True,
                "removed": False,
                "rule": it.get("RuleSet"),
            }
        )
    called = [{"group": ln.get("group"), "version": ln.get("version"), "resource": ln.get("resource"), "removed_release": ln.get("removed_release"), "calls": v} for ln, v in _metric_rows(cx.snap, "apiserver_requested_deprecated_apis")]
    insights = []
    ins = load_json(cx.snap / "aws" / "list-insights.json") or {}
    for i in ins.get("insights") or []:
        insights.append(
            {
                "name": i.get("name"),
                "category": i.get("category"),
                "status": (i.get("insightStatus") or {}).get("status"),
                "reason": ((i.get("insightStatus") or {}).get("reason") or "")[:200],
                "k8s_version": i.get("kubernetesVersion"),
                "last_transition": i.get("lastTransitionTime"),
            }
        )
    return {
        "items": items,
        "count": len(items),
        "removed_next": [i for i in items if i["removed"]],
        "pluto_present": (cx.snap / "tools" / "pluto.json").is_file(),
        "kubent_present": (cx.snap / "tools" / "kubent.json").is_file(),
        "called_deprecated_apis": called,
        "eks_insights": insights,
        "eks_insights_failing": [i for i in insights if i["status"] in ("ERROR", "WARNING")],
        "target": pl.get("target-versions"),
    }


# ---------- Helm ----------


def _helm(cx: _Ctx, now: _dt.datetime) -> dict:
    d = load_json(cx.snap / "tools" / "helm-list.json")
    if d is None:
        return {"present": False, "note": "tools/helm-list.json missing (helm not installed or not collected yet)"}
    rows = []
    for r in d if isinstance(d, list) else []:
        upd = _ts(r.get("updated"))
        chart = r.get("chart") or ""
        m = re.match(r"(.+)-(v?\d[\w.\-]*)$", chart)
        rows.append(
            {
                "namespace": r.get("namespace"),
                "name": r.get("name"),
                "target": f"{r.get('namespace')}/{r.get('name')}",
                "status": r.get("status"),
                "revision": r.get("revision"),
                "chart": chart,
                "chart_name": m.group(1) if m else chart,
                "chart_version": m.group(2) if m else None,
                "app_version": r.get("app_version"),
                "updated": r.get("updated"),
                "age_days": round((now - upd).total_seconds() / 86400) if upd else None,
                "prod": (r.get("namespace") in cx.prod),
            }
        )
    # Per release, the user values (tools/helm-values/<ns>__<name>.json, `helm get values -o json`: null when there are none) — a release running on pure chart defaults is not drift but "never tuned"
    vdir = cx.snap / "tools" / "helm-values"
    values_read = 0
    for r in rows:
        f = vdir / f"{r['namespace']}__{r['name']}.json"
        r["user_values_keys"] = None
        r["pure_defaults"] = None
        if not f.is_file():
            continue
        values_read += 1
        v = load_json(f)
        r["user_values_keys"] = sorted(v.keys())[:40] if isinstance(v, dict) else []
        r["user_values_count"] = len(v) if isinstance(v, dict) else 0
        r["pure_defaults"] = not v
    return {
        "present": True,
        "count": len(rows),
        "values_read": values_read,
        "pure_defaults": [r["target"] for r in rows if r.get("pure_defaults")],
        "pure_defaults_prod": [r["target"] for r in rows if r.get("pure_defaults") and r["prod"]],
        "releases": rows,
        "not_deployed": [r for r in rows if r["status"] != "deployed"],
        "by_status": dict(Counter(r["status"] for r in rows)),
        "stale_365d": [r["target"] for r in rows if (r["age_days"] or 0) >= 365],
    }


# ---------- images ----------


def _images(cx: _Ctx) -> dict:
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
                        "workload": cx.key(kind, o),
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


def _labels(cx: _Ctx) -> dict:
    no_std = []
    default_ns = []
    total = 0
    for kind, o in cx.workloads:
        total += 1
        md = o["metadata"]
        labels = md.get("labels") or {}
        tl = (((o.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {} if kind != "CronJob" else {}
        if not any(k.startswith("app.kubernetes.io/") for k in list(labels) + list(tl)):
            no_std.append({"workload": cx.key(kind, o), "namespace": md["namespace"], "prod": md["namespace"] in cx.prod, "labels": dict(list(labels.items())[:5])})
        if md["namespace"] == "default":
            default_ns.append({"workload": cx.key(kind, o), "prod": md["namespace"] in cx.prod})
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


def _orphans(cx: _Ctx) -> dict:
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
                "keys": sorted((cm.get("data") or {}).keys())[:5],
                "age_days": round((_dt.datetime.now(_dt.UTC) - _ts(md.get("creationTimestamp"))).total_seconds() / 86400) if _ts(md.get("creationTimestamp")) else None,
            }
        )
    # Secrets (name and type only, from metrics)
    types = {(ln.get("namespace"), ln.get("secret")): ln.get("type") for ln, _ in _metric_rows(cx.snap, "secret_types")}
    orphan_sec = []
    secret_names = {(ln.get("namespace"), ln.get("secret")) for ln, _ in _metric_rows(cx.snap, "secrets_by_name")}
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
            for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
                for i in range(((o.get("spec") or {}).get("replicas") or 1) + 2):
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
        "secrets_total": len(secret_names),
        "orphan_secrets": orphan_sec,
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


def _crds(cx: _Ctx, summary_webhooks: dict | None) -> dict:
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


def _templating(cx: _Ctx) -> dict:
    rows = []
    for kind, o in cx.workloads:
        md = o["metadata"]
        labels = md.get("labels") or {}
        ann = md.get("annotations") or {}
        managed = None
        if labels.get("app.kubernetes.io/managed-by") == "Helm" or any(k.startswith("meta.helm.sh/") for k in ann):
            managed = "helm"
        if "argocd.argoproj.io/tracking-id" in ann or "argocd.argoproj.io/instance" in labels:
            managed = "argocd" + ("+helm" if managed == "helm" else "")
        if any(k.startswith(("kustomize.toolkit.fluxcd.io/", "helm.toolkit.fluxcd.io/")) for k in labels):
            managed = "flux"
        if labels.get("app.kubernetes.io/managed-by") in ("eks", "EKS") or ann.get("eks.amazonaws.com/addon") or md["namespace"] == "kube-system":
            managed = managed or "platform"
        rows.append({"workload": cx.key(kind, o), "namespace": md["namespace"], "prod": md["namespace"] in cx.prod, "managed_by": managed, "last_applied": "kubectl.kubernetes.io/last-applied-configuration" in ann})
    apps = objects(cx.snap, "applications.argoproj.io")
    return {
        "workloads": len(rows),
        "by_manager": dict(Counter(r["managed_by"] or "none" for r in rows)),
        "unmanaged": [r for r in rows if not r["managed_by"]],
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
    cx = _Ctx(snap, inv)
    now = _dt.datetime.now(_dt.UTC)
    return {
        "polaris": _polaris(cx),
        "deprecated": _deprecated(cx),
        "helm": _helm(cx, now),
        "images": _images(cx),
        "labels": _labels(cx),
        "node_labels": _node_labels(cx),
        "orphans": _orphans(cx),
        "crds": _crds(cx, summary_webhooks),
        "templating": _templating(cx),
        "failed_pods": _failed_pods(cx, now),
        "ephemeral": _ephemeral(cx),
    }


def _failed_pods(cx: _Ctx, now) -> dict:
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
        age_h = None
        try:
            created = _dt.datetime.fromisoformat(str(p["metadata"].get("creationTimestamp")))
            age_h = round((now - created).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            pass
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
        "rows": rows[:40],
        "oldest_h": rows[0]["age_h"] if rows else None,
        "summary": {
            "count": len(rows),
            "by_reason": dict(by_reason),
            "by_namespace": dict(by_ns.most_common(8)),
            "oldest_h": rows[0]["age_h"] if rows else None,
            "prod": sum(1 for r in rows if r["prod"]),
            "sample": [f"{r['namespace']}/{r['pod']}" for r in rows[:6]],
        },
    }


def _ephemeral(cx: _Ctx) -> dict:
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
        wl = cx.key(kind, o)
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
            "emptydir_without_sizelimit_prod": sorted(emptydir_nolimit_prod)[:10],
        },
    }

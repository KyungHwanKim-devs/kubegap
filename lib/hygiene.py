"""Structure and hygiene summary.

Inputs: tools/polaris.json (Polaris audit, failures only), tools/pluto.json and tools/kubent.json (deprecated APIs), tools/helm-list.json (release metadata only; user values are never collected), aws/list-insights.json (EKS Upgrade Insights),
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

from . import scrub, versions
from .controlplane import workload_of
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
        self.server_version = (inv.get("cluster") or {}).get("server_version")
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs", "CronJob")):
            for o in objects(snap, stem):
                self.workloads.append((kind, o))
        self.pods = objects(snap, "pods")
        self.argo_apps = objects(snap, "applications.argoproj.io")
        # what Argo CD manages, whatever its tracking method: Application status.resources (argoproj/argo-cd pkg/apis/application/v1alpha1/types.go:1018@v2.13.0, :1151@v3.6.1) (#124 K2-5)
        self.argo_managed = {((r.get("kind") or "").lower(), r.get("namespace"), r.get("name")) for a in self.argo_apps for r in (a.get("status") or {}).get("resources") or []}

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
    # source: polaris v10.2.6 pkg/validator/output.go:45-54 AuditData{PolarisOutputVersion, AuditTime, SourceType, SourceName, DisplayName, ClusterInfo, Results, Score},
    # :95-101 ClusterInfo{Version, Nodes, Pods, Namespaces, Controllers}, :151-158 Result{Name, Namespace, Kind, Results, PodResult, CreatedTime}, :188-192 PodResult{Name, Results,
    # ContainerResults}, :222-225 ContainerResult{Name, Results}, :104-112 ResultMessage{ID, Message, Details, Success, Severity, Category, Mutations}; pkg/config/severity.go:22-28
    # severities ignore|warning|danger; pkg/config/checks/*.yaml categories Security (27), Reliability (13), Efficiency (4). The step runs without --only-show-failed-tests:
    # that filter keeps a controller only when its PodResult is non-empty (output.go:180-185; schema.go:245-249 always sets one), so a controller whose only failures are
    # controller-level checks vanished. The successes are skipped here instead. len(Results) is every audited object of every kind (controllers, Ingresses, Namespaces,
    # bindings …) and ClusterInfo.Controllers (pkg/validator/fullaudit.go:55, GetNumberOfControllers) the audited controllers.
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
        "with_failures": len(rows),
        "controllers": (d.get("ClusterInfo") or {}).get("Controllers"),
        "cluster_info": d.get("ClusterInfo"),
        "version": d.get("PolarisOutputVersion"),
        "checks": checks,
        "by_category": {f"{k[0]}/{k[1]}": v for k, v in Counter((cat_of[c], sev_of[c]) for c in by_check.elements()).items()} if by_check else {},
        "workloads": rows,
        "non_security_danger_workloads": [r["target"] for r in rows if r["non_security_danger"]],
        "security_danger_workloads": [r["target"] for r in rows if r["security_danger"]],
    }


# ---------- Deprecated API ----------


def _next_minor(server_version, pluto_target: dict | None) -> str | None:
    """The minor the two tools were asked about: the one after the server's (what collect passes as {k8s_next_minor}), else pluto's recorded k8s target."""
    return versions.next_minor_text(server_version) or versions.minor_text((pluto_target or {}).get("k8s"))


def _deprecated(cx: _Ctx) -> dict:
    steps = ((load_json(cx.snap / "collect-result.json") or {}).get("core") or {}).get("steps") or {}
    read = {f"{tool}_read": bool((steps.get(tool) or {}).get("ok") and (steps.get(tool) or {}).get("api_read")) for tool in ("pluto", "kubent")}
    # How much of the API each tool saw: successful and failed Lists counted from its log by lib/collect.py (#132); None for a snapshot taken before the counts existed.
    lists = {f"{tool}_lists_{k}": (steps.get(tool) or {}).get(f"lists_{k}") for tool in ("pluto", "kubent") for k in ("ok", "failed")}
    items = []
    # source: pluto v5.24.5 pkg/api/output.go:28-55 Output{name, filePath, namespace (omitempty), api, deprecated, removed, replacementAvailable}, :57-59 Instance{items (omitempty),
    # target-versions}, pkg/api/versions.go:60-76 Version{version, kind, deprecated-in, removed-in, replacement-api, replacement-available-in, component}; deprecated and removed are
    # judged against the target in FilterOutput (output.go:162-163). A cluster-scoped object has no namespace key.
    pl = load_json(cx.snap / "tools" / "pluto.json") or {}
    for it in (pl.get("items") or []) if read["pluto_read"] else []:
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
    # source: kubent 0.7.3 pkg/printer/json.go:32-40 encodes []judge.Result; pkg/judge/judge.go:3-11 Result{Name, Namespace, Kind, ApiVersion, RuleSet, ReplaceWith, Since}, Since as
    # text with three segments, "1.21.0" (judge/version.go:12-14 wraps hashicorp go-version, which pads). Since is the minor in which the API was deprecated, not removed:
    # pkg/rules/rego/deprecated-1-25.rego:13-33 gives PodDisruptionBudget policy/v1beta1
    # `since: 1.21` inside the rule set "Deprecated APIs removed in 1.25", so the removal minor exists only in the RuleSet text ("Deprecated APIs to be removed in future" for the ones
    # without a date, deprecated-future.rego:13). `-t` keeps the rows whose Since <= target or is empty (pkg/printer/filter.go:12). The rules write "<undefined>" for a missing
    # name or namespace (deprecated-1-25.rego:7-9; rego.go:61-64 is the fallback) and "<removed>" for an API with no successor (deprecated-1-25.rego:34-37).
    target = _next_minor(cx.server_version, pl.get("target-versions"))
    kb = load_json(cx.snap / "tools" / "kubent.json")
    for it in kb if read["kubent_read"] and isinstance(kb, list) else []:
        m = re.search(r"removed in (\d+\.\d+)", str(it.get("RuleSet") or ""))
        removed_in = m.group(1) if m else None
        ns = it.get("Namespace")
        rep = it.get("ReplaceWith")
        nm = it.get("Name")
        items.append(
            {
                "source": "kubent",
                "kind": it.get("Kind"),
                "name": None if nm == "<undefined>" else nm,
                "namespace": None if ns == "<undefined>" else ns,
                "api": it.get("ApiVersion"),
                "deprecated_in": it.get("Since"),
                "removed_in": removed_in,
                "replacement": None if rep == "<removed>" else rep,
                "deprecated": True,
                "removed": bool(removed_in and target and versions.major_minor(removed_in) <= versions.major_minor(target)),
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
    for item in items:
        item.update(read)
    return {
        **read,
        **lists,
        # None makes the existing evaluator skip even when there are no rows on which to test rule.needs.
        "items": items if any(read.values()) else None,
        "count": len(items) if any(read.values()) else None,
        "removed_next": [i for i in items if i["removed"]],
        "pluto_present": (cx.snap / "tools" / "pluto.json").is_file(),
        "kubent_present": (cx.snap / "tools" / "kubent.json").is_file(),
        "called_deprecated_apis": called,
        "eks_insights": insights,
        "eks_insights_failing": [i for i in insights if i["status"] in ("ERROR", "WARNING")],
        "target": pl.get("target-versions"),
        "target_minor": target,
    }


# ---------- Helm ----------


def _helm_missing_note(snap: Path) -> str:
    """Why tools/helm-list.json is absent. Helm reads release records from Secrets, so the shipped ClusterRole (no secrets) makes `helm list` fail; tell that apart from helm not being installed."""
    step = (((load_json(snap / "collect-result.json") or {}).get("core") or {}).get("steps") or {}).get("helm-list") or {}
    err = str(step.get("error") or "")
    if step.get("tool_missing"):
        return "helm is not installed; the Helm checks are skipped (kubegap setup --install-only helm)"
    if step.get("mode_skipped"):
        return "helm list is not collected in daily mode; the Helm checks run in a full run"
    if "forbidden" in err.lower() and "secret" in err.lower():
        return "helm list failed: Helm stores release records in Secrets and the credentials used have no secrets read permission (the shipped kubegap ClusterRole leaves it out on purpose). The Helm checks are skipped"
    if err:
        return f"helm list failed: {err[:200]}"
    return "tools/helm-list.json missing (helm not installed or not collected yet)"


def _helm(cx: _Ctx, now: _dt.datetime) -> dict:
    # source: helm v4.3.1 pkg/cmd/list.go:142-150 releaseElement{name, namespace, revision, updated, status, chart, app_version}, :158-181 (an empty list prints `[]`, updated is
    # Go time.String() unless --time-format), pkg/release/common/status.go:25-41 the nine status values; identical in helm v3.22.1 cmd/helm/list.go:135-173 and pkg/release/status.go:25-41.
    d = load_json(cx.snap / "tools" / "helm-list.json")
    if d is None:
        return {"present": False, "note": _helm_missing_note(cx.snap)}
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
    # User values (`helm get values`) are deliberately not collected: they often carry credentials (issue #3). Only the list metadata above is known.
    return {
        "present": True,
        "count": len(rows),
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
        # Argo CD's default tracking is the label `app.kubernetes.io/instance` = application name (argoproj/argo-cd common/common.go:161@v2.13.0, :190@v3.6.1), which Helm releases also set, so a
        # workload counts as Argo-managed when an Application lists it in status.resources; the configured `argocd.argoproj.io/instance` label and the tracking annotation are exact on their own (#124 K2-5)
        if "argocd.argoproj.io/tracking-id" in ann or "argocd.argoproj.io/instance" in labels or (kind.lower(), md["namespace"], md["name"]) in cx.argo_managed:
            managed = "argocd" + ("+helm" if managed == "helm" else "")
        if any(k.startswith(("kustomize.toolkit.fluxcd.io/", "helm.toolkit.fluxcd.io/")) for k in labels):
            managed = "flux"
        # EKS add-ons carry the labels `app.kubernetes.io/managed-by: EKS` and `eks.amazonaws.com/component` (observed on the add-on workloads; no public manifest, #124 K2-4)
        if labels.get("app.kubernetes.io/managed-by") in ("eks", "EKS") or "eks.amazonaws.com/component" in labels or md["namespace"] == "kube-system":
            managed = managed or "platform"
        rows.append({"workload": cx.key(kind, o), "namespace": md["namespace"], "prod": md["namespace"] in cx.prod, "managed_by": managed, "last_applied": "kubectl.kubernetes.io/last-applied-configuration" in ann})
    apps = cx.argo_apps
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
        "config_changes": _config_changes(cx),
    }


# ---------- ConfigMaps changed after the pods that use them started ----------
# A ConfigMap edited without a pod restart is a change nobody has seen take effect yet; it applies the next time the pod is recreated (node
# replacement, deploy), weeks later, with nobody connecting the two (Pusher 2019). A file mount is refreshed by the kubelet within a sync period,
# so only env, envFrom and subPath references keep the old value until a restart. Secrets are not in the snapshot (never collected), so they are
# not judged here. The change time is the latest managedFields time of the ConfigMap, which kubectl returns only with --show-managed-fields
# (lib/discover); a snapshot taken without it has no times and the section is None, so the check skips as not collected.
def _cm_refs(spec: dict) -> dict[str, dict]:
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


def _data_change(md: dict) -> tuple | None:
    """(time, manager) of the latest managedFields entry that wrote `data` or `binaryData`. Entries that only touched labels or annotations
    (kubectl label, an Argo CD tracking annotation, leader-election annotations rewritten every few seconds) are not changes of the configuration."""
    best = None
    for e in md.get("managedFields") or []:
        fields = e.get("fieldsV1") or {}
        if not isinstance(fields, dict) or not ({"f:data", "f:binaryData"} & set(fields)):
            continue
        t = _ts(e.get("time"))
        if t and (best is None or t > best[0]):
            best = (t, e.get("manager"))
    return best


def _config_changes(cx: _Ctx) -> dict | None:
    cms = [c for c in objects(cx.snap, "configmaps") if (c.get("metadata") or {}).get("name") not in SYSTEM_CONFIGMAPS]
    changed: dict[tuple, dict] = {}
    with_time = 0
    for c in cms:
        md = c.get("metadata") or {}
        if not any(e.get("time") for e in md.get("managedFields") or []):
            continue
        with_time += 1
        dc = _data_change(md)
        if c.get("immutable"):
            # an immutable ConfigMap cannot be edited; the only change is delete and recreate under the same name, and then the creation time is the change time
            created = _ts(md.get("creationTimestamp"))
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
        pod_started = _ts(st.get("startTime"))
        if st.get("phase") != "Running" or not pod_started:
            continue
        pods_checked += 1
        ns, pod = p["metadata"]["namespace"], p["metadata"]["name"]
        # env and subPath are resolved when a container starts, so a container restarted after the change already holds the new value: compare with the container's own start
        container_started = {}
        for cs in (st.get("containerStatuses") or []) + (st.get("initContainerStatuses") or []) + (st.get("ephemeralContainerStatuses") or []):
            t = _ts((((cs.get("state") or {}).get("running") or {}).get("startedAt")) or (((cs.get("state") or {}).get("terminated") or {}).get("startedAt")))
            if t:
                container_started[cs.get("name")] = t
        for name, ref in _cm_refs(p.get("spec") or {}).items():
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

"""Multi-tenancy area summary.

Tenant = namespace. Namespaces are classified into five kinds: prod (inventory prod_like), dev (dev_like), ci (runners/builds: by name or by ARC/KEDA ScaledJob objects),
system (kube-* and namespaces where detected platform components live) and other (shared namespaces such as a database or middleware namespace, default, ...).

Inputs: objects/namespaces, resourcequotas, limitranges, pods, deployments, statefulsets, daemonsets, networkpolicies, rolebindings, clusterrolebindings,
autoscalingrunnersets, scaledjobs, nodepools (karpenter), inventory (nodes' nodepool/nodegroup/taints/allocatable, prod_like, dev_like, components),
metrics/namespace_cpu_p95_7d·namespace_cpu_max_7d·namespace_cpu_median_7d·namespace_memory_p95_7d_bytes·namespace_node_cpu_share_p95_7d·
node_cpu_saturated_minutes_7d·namespace_cpu_throttled_ratio_7d.

Output is the `tenancy` section of summary.json: namespaces (one row per tenant: kind, pods, requests, quota, LimitRange, NetworkPolicy, PSA, usage, burst, which nodes and pools it runs on),
quotas (hard/used ratio per ResourceQuota, whether LimitRange defaults exist), limitranges, isolation (tenant mix per pool, nodes with mixed tenants, CI runner template placement constraints and dedicated pools),
rbac (subjects with edit/admin across several prod tenants), noisy (noisy-neighbour inputs: node saturation minutes, dominant namespace, burst, throttling; the judgement is left to the LLM, type: llm). Shape is documented in SKILL.md.
"""

from __future__ import annotations

import contextlib
import re
from collections import Counter, defaultdict
from pathlib import Path

from .resilience import _q
from .snapshot import load_json, objects

SYSTEM_NS = {
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "monitoring",
    "logging",
    "argocd",
    "cert-manager",
    "external-secrets",
    "ingress-nginx",
    "metallb-system",
    "keda",
    "karpenter",
    "reloader",
    "arc-system",
    "arc-systems",
    "gatekeeper-system",
    "kyverno",
    "istio-system",
    "linkerd",
    "flux-system",
    "velero",
    "aws-load-balancer-controller",
    "amazon-cloudwatch",
    "aws-observability",
    "longhorn-system",
    "rook-ceph",
    "local-path-storage",
    "external-dns",
    "sealed-secrets",
    "vault",
    "falco",
    "trivy-system",
    "kubecost",
    "opencost",
    "goldilocks",
    "polaris",
}
CI_NS_RE = re.compile(r"(runner|^ci$|^ci-|-ci$|jenkins|tekton|drone|buildkit|gitlab|woodpecker|argo-workflows|^arc-runners)", re.IGNORECASE)
CI_OWNER_KINDS = {"EphemeralRunner", "EphemeralRunnerSet", "AutoscalingRunnerSet", "AutoscalingListener", "RunnerDeployment", "RunnerSet", "ScaledJob", "PipelineRun", "TaskRun"}
NODE_TOLERATION_PREFIX = ("node.kubernetes.io/", "node.cloudprovider.kubernetes.io/", "kubernetes.io/", "CriticalAddonsOnly")
BROAD_ROLES = {"admin", "edit", "cluster-admin"}


def _metric_rows(snap: Path, qid: str) -> list[tuple[dict, float]]:
    m = load_json(snap / "metrics" / f"{qid}.json")
    out = []
    for s in (m or {}).get("result") or []:
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out.append((s.get("metric") or {}, float(s["value"][1])))
    return out


def _metric_by(snap: Path, qid: str, key: str = "namespace") -> dict[str, float]:
    return {lab.get(key): v for lab, v in _metric_rows(snap, qid) if lab.get(key)}


def _r(x, n=2):
    return None if x is None else round(x, n)


def _owner_kind(pod: dict) -> str | None:
    refs = pod["metadata"].get("ownerReferences") or []
    return refs[0].get("kind") if refs else None


class _Tenants:
    """Classify a namespace into a kind."""

    def __init__(self, snap: Path, inv: dict | None, namespaces: list[str]):
        inv = inv or {}
        self.prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
        self.dev = set((inv.get("namespaces") or {}).get("dev_like") or [])
        self.system = set(SYSTEM_NS)
        for ns in namespaces:
            if ns.startswith("kube-"):
                self.system.add(ns)
        for _cid, c in (inv.get("components") or {}).items() if isinstance(inv.get("components"), dict) else []:
            ev = (c or {}).get("evidence") or ""
            m = re.search(r"\s([a-z0-9-]+)/[a-z0-9.-]+$", ev)
            if (c or {}).get("present") and m:
                self.system.add(m.group(1))
        self.ci = {ns for ns in namespaces if CI_NS_RE.search(ns) and ns not in self.prod}
        for stem in ("autoscalingrunnersets.actions.github.com", "runnerdeployments.actions.summerwind.dev", "scaledjobs.keda.sh"):
            for o in objects(snap, stem):
                ns = o["metadata"].get("namespace")
                if ns and ns not in self.prod:
                    self.ci.add(ns)
        self.system -= self.prod | self.dev | self.ci

    def kind(self, ns: str | None) -> str:
        if ns is None:
            return "other"
        if ns in self.prod:
            return "prod"
        if ns in self.ci:
            return "ci"
        if ns in self.dev:
            return "dev"
        if ns in self.system:
            return "system"
        return "other"


def _requests(pod: dict) -> tuple[float, float, float, float, int, int]:
    """(cpu_req, mem_req, cpu_lim, mem_lim, containers_without_requests, containers_without_memory_limit)."""
    cr = mr = cl = ml = 0.0
    noreq = nolim = 0
    for c in pod["spec"].get("containers") or []:
        res = c.get("resources") or {}
        rq, lm = res.get("requests") or {}, res.get("limits") or {}
        if not rq.get("cpu") and not rq.get("memory"):
            noreq += 1
        if not lm.get("memory"):
            nolim += 1
        cr += _q(rq.get("cpu"))
        mr += _q(rq.get("memory"))
        cl += _q(lm.get("cpu"))
        ml += _q(lm.get("memory"))
    return cr, mr, cl, ml, noreq, nolim


def _placement_constraint(pod_spec: dict) -> dict:
    """Whether a runner/batch template constrains where it is scheduled. A nodeSelector that only picks an arch does not count."""
    sel = {k: v for k, v in (pod_spec.get("nodeSelector") or {}).items() if k not in ("kubernetes.io/arch", "kubernetes.io/os", "beta.kubernetes.io/arch", "beta.kubernetes.io/os")}
    tols = [t for t in (pod_spec.get("tolerations") or []) if t.get("key") and not str(t["key"]).startswith(NODE_TOLERATION_PREFIX)]
    aff = (pod_spec.get("affinity") or {}).get("nodeAffinity") or {}
    return {
        "node_selector": sel,
        "tolerations": [{"key": t.get("key"), "value": t.get("value"), "effect": t.get("effect")} for t in tols],
        "node_affinity": bool(aff),
        "constrained": bool(sel or tols or aff),
    }


def _taint_dict(t) -> dict:
    """inventory.json stores node taints as `key=value:effect` strings (discover); NodePool templates carry dicts. Normalise to {key, value, effect}. The first tainted node on a real cluster (a CI build pool) crashed the whole tenancy section before this existed."""
    if isinstance(t, dict):
        return {"key": t.get("key"), "value": t.get("value"), "effect": t.get("effect")}
    s = str(t)
    kv, _, effect = s.partition(":")
    key, _, value = kv.partition("=")
    return {"key": key, "value": value or None, "effect": effect or None}


def _pools(inv: dict | None, snap: Path) -> tuple[dict[str, str], dict[str, dict]]:
    """node -> pool name, pool -> {taints, labels, source}."""
    node_pool: dict[str, str] = {}
    pools: dict[str, dict] = {}
    for n in ((inv or {}).get("nodes") or {}).get("nodes") or []:
        pool = n.get("nodepool") or n.get("nodegroup") or ("(no-pool)")
        node_pool[n["name"]] = pool
        p = pools.setdefault(pool, {"pool": pool, "source": "karpenter" if n.get("nodepool") else ("nodegroup" if n.get("nodegroup") else "none"), "nodes": [], "taints": [], "labels": {}})
        p["nodes"].append(n["name"])
        for t in n.get("taints") or []:
            t = _taint_dict(t)
            if t not in p["taints"] and not str(t.get("key", "")).startswith(NODE_TOLERATION_PREFIX):
                p["taints"].append(t)
    for np_ in objects(snap, "nodepools.karpenter.sh"):
        name = np_["metadata"]["name"]
        tmpl = (np_.get("spec") or {}).get("template") or {}
        p = pools.setdefault(name, {"pool": name, "source": "karpenter", "nodes": [], "taints": [], "labels": {}})
        p["labels"] = (tmpl.get("metadata") or {}).get("labels") or {}
        p["taints"] = [{"key": t.get("key"), "value": t.get("value"), "effect": t.get("effect")} for t in ((tmpl.get("spec") or {}).get("taints") or [])] or p["taints"]
        p["nodeclaims"] = ((np_.get("status") or {}).get("resources") or {}).get("nodes")
    return node_pool, pools


def _pool_matches(constraint: dict, pool: dict) -> bool:
    """Do the runner template's nodeSelector and tolerations match this pool's labels and taints?"""
    labels = pool.get("labels") or {}
    sel = constraint.get("node_selector") or {}
    if sel and all(labels.get(k) == v for k, v in sel.items()):
        return True
    keys = {t.get("key") for t in constraint.get("tolerations") or []}
    return bool(keys) and any(t.get("key") in keys for t in pool.get("taints") or [])


class _Ctx:
    """Inputs shared by the helpers: tenant classifier, running pods, pools, node allocatable and the 7-day namespace/node metrics."""

    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        self.inv = inv = inv or {}
        self.ns_objs = objects(snap, "namespaces")
        self.ns_names = [n["metadata"]["name"] for n in self.ns_objs]
        self.tn = _Tenants(snap, inv, self.ns_names)
        pods = objects(snap, "pods")
        self.running = [p for p in pods if (p.get("status") or {}).get("phase") in ("Running", "Pending")]
        self.node_pool, self.pools = _pools(inv, snap)
        self.node_alloc = {n["name"]: n for n in (inv.get("nodes") or {}).get("nodes") or []}
        self.nodes_total = len(self.node_alloc)
        self.karpenter = bool(objects(snap, "nodepools.karpenter.sh"))
        self.separation_possible = self.karpenter or self.nodes_total >= 3
        # --- metrics ---
        self.cpu_p95 = _metric_by(snap, "namespace_cpu_p95_7d")
        self.cpu_max = _metric_by(snap, "namespace_cpu_max_7d")
        self.cpu_med = _metric_by(snap, "namespace_cpu_median_7d")
        self.mem_p95 = _metric_by(snap, "namespace_memory_p95_7d_bytes")
        self.throttled = _metric_by(snap, "namespace_cpu_throttled_ratio_7d")
        self.sat_min = _metric_by(snap, "node_cpu_saturated_minutes_7d", "node")
        self.node_share: dict[str, dict[str, float]] = defaultdict(dict)
        for lab, v in _metric_rows(snap, "namespace_node_cpu_share_p95_7d"):
            if lab.get("node") and lab.get("namespace"):
                self.node_share[lab["node"]][lab["namespace"]] = v
        self.metrics_available = bool(self.cpu_p95)
        self.cluster_p95_total = sum(self.cpu_p95.values()) or None


def _quotas(cx: _Ctx) -> dict[str, list[dict]]:
    """namespace -> ResourceQuota rows (hard/used ratios, near-limit keys, whether requests/limits are required). Reads objects/resourcequotas."""
    quotas_by_ns: dict[str, list[dict]] = defaultdict(list)
    for q in objects(cx.snap, "resourcequotas"):
        ns = q["metadata"]["namespace"]
        hard = (q.get("spec") or {}).get("hard") or {}
        used = (q.get("status") or {}).get("used") or {}
        ratios = {}
        for k, hv in hard.items():
            h = _q(hv)
            u = _q(used.get(k))
            ratios[k] = _r(u / h, 3) if h else None
        near = sorted([k for k, r in ratios.items() if r is not None and r >= 0.8], key=lambda k: -ratios[k])
        quotas_by_ns[ns].append(
            {
                "namespace": ns,
                "name": q["metadata"]["name"],
                "target": f"{ns}/{q['metadata']['name']}",
                "hard": hard,
                "used": used,
                "ratios": ratios,
                "max_ratio": max([r for r in ratios.values() if r is not None], default=0.0),
                "near_limit": near,
                "requires_requests": any(k in ("requests.cpu", "requests.memory", "cpu", "memory") for k in hard),
                "requires_limits": any(k in ("limits.cpu", "limits.memory") for k in hard),
                "scopes": (q.get("spec") or {}).get("scopes") or [],
                "prod": ns in cx.tn.prod,
                "kind": cx.tn.kind(ns),
            }
        )
    return quotas_by_ns


def _limitranges(cx: _Ctx) -> dict[str, list[dict]]:
    """namespace -> LimitRange rows (Container defaults, max/min). Reads objects/limitranges."""
    lr_by_ns: dict[str, list[dict]] = defaultdict(list)
    for lr in objects(cx.snap, "limitranges"):
        ns = lr["metadata"]["namespace"]
        lims = (lr.get("spec") or {}).get("limits") or []
        cont = [ln for ln in lims if ln.get("type") == "Container"]
        lr_by_ns[ns].append(
            {
                "namespace": ns,
                "name": lr["metadata"]["name"],
                "target": f"{ns}/{lr['metadata']['name']}",
                "types": [ln.get("type") for ln in lims],
                "default_request": (cont[0].get("defaultRequest") if cont else None),
                "default_limit": (cont[0].get("default") if cont else None),
                "max": (cont[0].get("max") if cont else None),
                "min": (cont[0].get("min") if cont else None),
                "prod": ns in cx.tn.prod,
            }
        )
    return lr_by_ns


def _boundaries(cx: _Ctx, security: dict | None) -> tuple[Counter, dict, bool | None]:
    """(NetworkPolicy count per namespace, PSA enforce level per namespace, whether NetworkPolicy is enforced by the CNI). Reads objects/networkpolicies.networking.k8s.io and namespace labels; enforcement comes from the security section."""
    netpol_count = Counter(o["metadata"]["namespace"] for o in objects(cx.snap, "networkpolicies.networking.k8s.io"))
    psa = {}
    for n in cx.ns_objs:
        lab = n["metadata"].get("labels") or {}
        e = lab.get("pod-security.kubernetes.io/enforce")
        if e:
            psa[n["metadata"]["name"]] = e
    enforced = (security or {}).get("networkpolicy", {}).get("enforced") if security else None
    return netpol_count, psa, enforced


def _rbac_scope(cx: _Ctx) -> tuple[dict[str, set], dict[str, set], list[dict]]:
    """(subjects bound per namespace, subjects with admin/edit per tenant namespace, subjects with broad roles across two or more tenants). Reads objects/rolebindings.rbac.authorization.k8s.io."""
    rb_subjects_by_ns: dict[str, set] = defaultdict(set)
    broad_by_subject: dict[str, set] = defaultdict(set)
    for rb in objects(cx.snap, "rolebindings.rbac.authorization.k8s.io"):
        ns = rb["metadata"]["namespace"]
        role = (rb.get("roleRef") or {}).get("name")
        for s in rb.get("subjects") or []:
            if s.get("kind") == "Group" and str(s.get("name", "")).startswith("system:"):
                continue
            if s.get("kind") == "ServiceAccount" and (s.get("namespace") or ns) in cx.tn.system:
                continue
            sid = f"{s.get('kind')}:{(s.get('namespace') + '/') if s.get('kind') == 'ServiceAccount' and s.get('namespace') else ''}{s.get('name')}"
            rb_subjects_by_ns[ns].add(sid)
            if role in BROAD_ROLES and cx.tn.kind(ns) in ("prod", "dev", "other", "ci"):
                broad_by_subject[sid].add(ns)
    cross_tenant = []
    for sid, nss in sorted(broad_by_subject.items()):
        prod_ns = sorted(n for n in nss if n in cx.tn.prod)
        if len(nss) >= 2:
            cross_tenant.append({"subject": sid, "namespaces": sorted(nss), "prod_namespaces": prod_ns, "prod_count": len(prod_ns), "target": sid})
    return rb_subjects_by_ns, broad_by_subject, cross_tenant


def _pod_aggregation(cx: _Ctx) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """(running pods per namespace, per-node accumulators: tenant/namespace counters, requests, limits, CI pods). Reads objects/pods (via the context)."""
    ns_pods: dict[str, list[dict]] = defaultdict(list)
    node_rows: dict[str, dict] = {}
    for p in cx.running:
        ns = p["metadata"]["namespace"]
        ns_pods[ns].append(p)
        node = p["spec"].get("nodeName")
        if not node:
            continue
        kind = cx.tn.kind(ns)
        owner = _owner_kind(p)
        cr, mr, cl, ml, _noreq, nolim = _requests(p)
        nr = node_rows.setdefault(
            node,
            {
                "node": node,
                "pool": cx.node_pool.get(node, "(no-pool)"),
                "tenants": Counter(),
                "namespaces": Counter(),
                "pods": 0,
                "cpu_requests": 0.0,
                "cpu_limits": 0.0,
                "memory_requests": 0.0,
                "memory_limits": 0.0,
                "containers_without_memory_limit": 0,
                "ci_pods": [],
                "prod_namespaces": set(),
                "dev_namespaces": set(),
                "ci_namespaces": set(),
            },
        )
        if owner == "DaemonSet":
            continue  # DaemonSets run on every node, so they do not count as tenant mixing
        nr["pods"] += 1
        nr["tenants"][kind] += 1
        nr["namespaces"][ns] += 1
        nr["cpu_requests"] += cr
        nr["cpu_limits"] += cl
        nr["memory_requests"] += mr
        nr["memory_limits"] += ml
        nr["containers_without_memory_limit"] += nolim
        if kind == "prod":
            nr["prod_namespaces"].add(ns)
        elif kind == "dev":
            nr["dev_namespaces"].add(ns)
        elif kind == "ci":
            nr["ci_namespaces"].add(ns)
            heavy = owner in CI_OWNER_KINDS or "runner" in p["metadata"]["name"] or cr >= 1.0
            nr["ci_pods"].append({"pod": p["metadata"]["name"], "namespace": ns, "owner_kind": owner, "cpu_request": _r(cr, 3), "heavy": heavy})
    return ns_pods, node_rows


def _workload_counts(cx: _Ctx) -> Counter:
    """Workloads per namespace. Reads objects/deployments, statefulsets, daemonsets, cronjobs."""
    workload_counts: Counter = Counter()
    for stem in ("deployments", "statefulsets", "daemonsets", "cronjobs"):
        for o in objects(cx.snap, stem):
            workload_counts[o["metadata"]["namespace"]] += 1
    return workload_counts


def _node_rows(cx: _Ctx, node_rows: dict[str, dict]) -> list[dict]:
    """Finished node rows: tenant mix, requests/limits vs allocatable, overcommit, saturation minutes, dominant namespace, CI/dev sharing with prod. Reads inventory allocatable and metrics (via the context)."""
    nodes_out = []
    for node, nr in sorted(node_rows.items()):
        alloc = (cx.node_alloc.get(node) or {}).get("allocatable") or {}
        acpu, amem = _q(alloc.get("cpu")), _q(alloc.get("memory"))
        share = cx.node_share.get(node) or {}
        dom = max(share.items(), key=lambda kv: kv[1]) if share else None
        tenants = dict(nr["tenants"])
        tenant_kinds = [k for k in tenants if k != "system"]
        row = {
            "node": node,
            "pool": nr["pool"],
            "pods": nr["pods"],
            "tenants": tenants,
            "tenant_kinds": sorted(tenant_kinds),
            "tenant_count": len(tenant_kinds),
            "namespaces": dict(nr["namespaces"].most_common()),
            "prod_pods": tenants.get("prod", 0),
            "dev_pods": tenants.get("dev", 0),
            "ci_pods": len(nr["ci_pods"]),
            "prod_namespaces": sorted(nr["prod_namespaces"]),
            "dev_namespaces": sorted(nr["dev_namespaces"]),
            "ci_namespaces": sorted(nr["ci_namespaces"]),
            "ci_pod_list": nr["ci_pods"][:10],
            "ci_heavy": any(c["heavy"] for c in nr["ci_pods"]),
            "allocatable_cpu": _r(acpu, 2),
            "allocatable_memory_gb": _r(amem / 1024**3, 1) if amem else None,
            "cpu_requests": _r(nr["cpu_requests"], 2),
            "cpu_limits": _r(nr["cpu_limits"], 2),
            "memory_requests_gb": _r(nr["memory_requests"] / 1024**3, 1),
            "memory_limits_gb": _r(nr["memory_limits"] / 1024**3, 1),
            "memory_limit_overcommit": _r(nr["memory_limits"] / amem, 2) if amem else None,
            "cpu_limit_overcommit": _r(nr["cpu_limits"] / acpu, 2) if acpu else None,
            "containers_without_memory_limit": nr["containers_without_memory_limit"],
            "cpu_saturated_minutes_7d": _r(cx.sat_min.get(node), 0) if node in cx.sat_min else None,
            "dominant_namespace": dom[0] if dom else None,
            "dominant_share_p95": _r(dom[1], 3) if dom else None,
            "dominant_kind": cx.tn.kind(dom[0]) if dom else None,
            "namespace_share_p95": {k: _r(v, 3) for k, v in sorted(share.items(), key=lambda kv: -kv[1])[:6]},
            "shares_ci_prod": tenants.get("prod", 0) > 0 and len(nr["ci_pods"]) > 0,
            "shares_dev_prod": tenants.get("prod", 0) > 0 and tenants.get("dev", 0) > 0,
            "separation_possible": cx.separation_possible,
        }
        nodes_out.append(row)
    return nodes_out


def _pool_rows(cx: _Ctx, nodes_out: list[dict]) -> list[dict]:
    """One row per node pool: source, taints, labels, tenant mix and whether prod shares the pool with CI or dev. Reads inventory nodes and objects/nodepools.karpenter.sh (via the context)."""
    pools_out = []
    for name, p in sorted(cx.pools.items()):
        tenants: Counter = Counter()
        nss: set = set()
        for row in nodes_out:
            if row["pool"] == name:
                tenants.update(row["tenants"])
                nss.update(row["namespaces"])
        pools_out.append(
            {
                "pool": name,
                "source": p.get("source"),
                "nodes": len(p["nodes"]),
                "tainted": bool(p.get("taints")),
                "taints": p.get("taints") or [],
                "labels": p.get("labels") or {},
                "tenants": dict(tenants),
                "tenant_kinds": sorted(k for k in tenants if k != "system"),
                "namespaces": sorted(nss),
                "mixed_prod_ci": tenants.get("prod", 0) > 0 and tenants.get("ci", 0) > 0,
                "mixed_prod_dev": tenants.get("prod", 0) > 0 and tenants.get("dev", 0) > 0,
            }
        )
    return pools_out


def _ci_templates(cx: _Ctx, pools_out: list[dict]) -> list[dict]:
    """CI runner templates: placement constraints, matching and dedicated (tainted) pools, requests. Reads objects/autoscalingrunnersets.actions.github.com, runnerdeployments.actions.summerwind.dev, scaledjobs.keda.sh; falls back to deployments/cronjobs in CI namespaces."""
    ci_templates = []
    for stem, kind_label, path in (
        ("autoscalingrunnersets.actions.github.com", "AutoscalingRunnerSet", ("spec", "template", "spec")),
        ("runnerdeployments.actions.summerwind.dev", "RunnerDeployment", ("spec", "template", "spec")),
        ("scaledjobs.keda.sh", "ScaledJob", ("spec", "jobTargetRef", "template", "spec")),
    ):
        for o in objects(cx.snap, stem):
            ns = o["metadata"]["namespace"]
            cur = o
            for k in path:
                cur = (cur or {}).get(k) or {}
            cons = _placement_constraint(cur)
            matched = [p["pool"] for p in pools_out if _pool_matches(cons, cx.pools[p["pool"]])] if cons["constrained"] else []
            reqs = [((c.get("resources") or {}).get("requests") or {}) for c in cur.get("containers") or []]
            ci_templates.append(
                {
                    "namespace": ns,
                    "kind": kind_label,
                    "name": o["metadata"]["name"],
                    "target": f"{ns}/{kind_label}/{o['metadata']['name']}",
                    "min": (o.get("spec") or {}).get("minRunners", (o.get("spec") or {}).get("minReplicaCount")),
                    "max": (o.get("spec") or {}).get("maxRunners", (o.get("spec") or {}).get("maxReplicaCount")),
                    **cons,
                    "matching_pools": matched,
                    "dedicated_pool": next((p for p in matched if cx.pools[p].get("taints")), None),
                    "cpu_request": _r(sum(_q(r.get("cpu")) for r in reqs), 2),
                    "memory_request_gb": _r(sum(_q(r.get("memory")) for r in reqs) / 1024**3, 2),
                    "has_requests": any(r for r in reqs),
                }
            )
    # CI-namespace workloads running as CronJobs/Deployments also count as templates (when there is no runner CR)
    if not ci_templates:
        for stem, kind_label in (("deployments", "Deployment"), ("cronjobs", "CronJob")):
            for o in objects(cx.snap, stem):
                ns = o["metadata"]["namespace"]
                if cx.tn.kind(ns) != "ci":
                    continue
                spec = o.get("spec") or {}
                pod_spec = ((spec.get("template") or {}).get("spec") if kind_label == "Deployment" else (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec")) or {}
                cons = _placement_constraint(pod_spec)
                matched = [p["pool"] for p in pools_out if _pool_matches(cons, cx.pools[p["pool"]])] if cons["constrained"] else []
                ci_templates.append(
                    {
                        "namespace": ns,
                        "kind": kind_label,
                        "name": o["metadata"]["name"],
                        "target": f"{ns}/{kind_label}/{o['metadata']['name']}",
                        "min": None,
                        "max": None,
                        **cons,
                        "matching_pools": matched,
                        "dedicated_pool": next((p for p in matched if cx.pools[p].get("taints")), None),
                        "cpu_request": None,
                        "memory_request_gb": None,
                        "has_requests": None,
                    }
                )
    return ci_templates


def _multi_org(cx: _Ctx, rb_subjects_by_ns: dict[str, set]) -> bool:
    """Multi-organisation signal: if two or more distinct sets of human subjects (User/Group, excluding SAs) are bound to tenant namespaces, the tenants are treated as different organisations. With a single organisation, missing quotas/LimitRanges are low severity. Reads nothing (RoleBinding subjects are passed in)."""
    human_subjects = {sid for ns_, subs in rb_subjects_by_ns.items() for sid in subs if not sid.startswith("ServiceAccount:") and cx.tn.kind(ns_) in ("prod", "dev", "ci", "other")}
    return len(human_subjects) >= 2


def _namespace_row(cx: _Ctx, ns: str, plist: list[dict], nodes_out: list[dict], parts: dict) -> dict:
    """One namespace row: requests/limits, quota/LimitRange/NetworkPolicy/PSA/RBAC presence, nodes and pools it runs on, 7-day usage and burst. parts = the per-namespace lookups built by the other helpers; reads nothing itself."""
    kind = cx.tn.kind(ns)
    cr = mr = cl = ml = 0.0
    noreq = nolim = 0
    nodes_c: Counter = Counter()
    for p in plist:
        a, b, c, d, e, f = _requests(p)
        cr += a
        mr += b
        cl += c
        ml += d
        noreq += e
        nolim += f
        if p["spec"].get("nodeName"):
            nodes_c[p["spec"]["nodeName"]] += 1
    pools_c: Counter = Counter()
    for n, c in nodes_c.items():
        pools_c[cx.node_pool.get(n, "(no-pool)")] += c
    shares_prod = any(r["prod_pods"] > 0 and (r["namespaces"].get(ns, 0) > 0) and (kind != "prod" or len(r["prod_namespaces"]) > 1) for r in nodes_out)
    p95, mx, med = cx.cpu_p95.get(ns), cx.cpu_max.get(ns), cx.cpu_med.get(ns)
    burst = (mx / med) if (mx is not None and med and med > 0.01) else None
    node_share_max = max(((n, s.get(ns)) for n, s in cx.node_share.items() if s.get(ns) is not None), key=lambda kv: kv[1], default=(None, None))
    lrs = parts["lr_by_ns"].get(ns, [])
    quotas_by_ns, rb_subjects_by_ns = parts["quotas_by_ns"], parts["rb_subjects_by_ns"]
    return {
        "namespace": ns,
        "kind": kind,
        "prod": kind == "prod",
        "system": kind == "system",
        "pods": len(plist),
        "workloads": parts["workload_counts"].get(ns, 0),
        "cpu_requests": _r(cr, 2),
        "cpu_limits": _r(cl, 2),
        "memory_requests_gb": _r(mr / 1024**3, 2),
        "memory_limits_gb": _r(ml / 1024**3, 2),
        "containers_without_requests": noreq,
        "containers_without_memory_limit": nolim,
        "has_quota": ns in quotas_by_ns,
        "quota_names": [q["name"] for q in quotas_by_ns.get(ns, [])],
        "quota_max_ratio": max([q["max_ratio"] for q in quotas_by_ns.get(ns, [])], default=None),
        "has_limitrange": bool(lrs),
        "limitrange_default_request": bool(lrs and any(ln["default_request"] for ln in lrs)),
        "networkpolicies": parts["netpol_count"].get(ns, 0),
        "networkpolicy_enforced": parts["enforced"],
        "psa_enforce": parts["psa"].get(ns),
        "rbac_subjects": sorted(rb_subjects_by_ns.get(ns, set()))[:10],
        "rbac_subject_count": len(rb_subjects_by_ns.get(ns, set())),
        "nodes": dict(nodes_c.most_common()),
        "node_count": len(nodes_c),
        "pools": dict(pools_c.most_common()),
        "shares_nodes_with_prod": shares_prod,
        "cpu_p95_7d": _r(p95, 3),
        "cpu_max_7d": _r(mx, 3),
        "cpu_median_7d": _r(med, 3),
        "burst_ratio_7d": _r(burst, 1),
        "cpu_share_of_cluster_p95": _r(p95 / cx.cluster_p95_total, 3) if (p95 is not None and cx.cluster_p95_total) else None,
        "memory_p95_7d_gb": _r(cx.mem_p95.get(ns, 0) / 1024**3, 2) if ns in cx.mem_p95 else None,
        "throttled_ratio_7d": _r(cx.throttled.get(ns), 3) if ns in cx.throttled else None,
        "node_share_p95_max": _r(node_share_max[1], 3) if node_share_max[1] is not None else None,
        "node_share_p95_max_node": node_share_max[0],
        "tenants_total": None,  # filled below
        "multi_org": parts["multi_org"],
        "cluster_saturated_7d": parts["cluster_saturated_7d"],
        "separation_possible": cx.separation_possible,
    }


def _namespace_rows(cx: _Ctx, ns_pods: dict[str, list[dict]], nodes_out: list[dict], parts: dict) -> tuple[list[dict], list[dict]]:
    """(all namespace rows sorted by name, tenant rows = prod/dev/ci/other namespaces with pods); fills tenants_total. Reads nothing (lookups are passed in)."""
    ns_rows = [_namespace_row(cx, ns, ns_pods.get(ns, []), nodes_out, parts) for ns in sorted(cx.ns_names)]
    tenant_rows = [r for r in ns_rows if r["kind"] in ("prod", "dev", "ci", "other") and r["pods"] > 0]
    for r in ns_rows:
        r["tenants_total"] = len(tenant_rows)
    return ns_rows, tenant_rows


def _quota_rows(quotas_by_ns: dict[str, list[dict]], ns_rows: list[dict]) -> list[dict]:
    """ResourceQuota rows joined with their namespace's LimitRange defaults and containers without requests. Reads nothing."""
    quotas_out = []
    for ns, qs in sorted(quotas_by_ns.items()):
        nsrow = next((r for r in ns_rows if r["namespace"] == ns), {})
        for q in qs:
            q = dict(q)
            q["limitrange_default_request"] = nsrow.get("limitrange_default_request", False)
            q["has_limitrange"] = nsrow.get("has_limitrange", False)
            q["containers_without_requests"] = nsrow.get("containers_without_requests", 0)
            quotas_out.append(q)
    return quotas_out


def _noisy(cx: _Ctx, nodes_out: list[dict], ns_rows: list[dict]) -> dict:
    """Noisy-neighbour inputs: saturated nodes, bursty tenants, throttled prod namespaces, top CPU shares, shared nodes dominated by one namespace. Reads nothing (rows are passed in); the verdict is left to the LLM."""
    return {
        "metrics_available": cx.metrics_available,
        "nodes_saturated_7d": sorted(
            [
                {
                    "node": r["node"],
                    "minutes": r["cpu_saturated_minutes_7d"],
                    "dominant_namespace": r["dominant_namespace"],
                    "dominant_share_p95": r["dominant_share_p95"],
                    "dominant_kind": r["dominant_kind"],
                    "tenant_kinds": r["tenant_kinds"],
                }
                for r in nodes_out
                if (r["cpu_saturated_minutes_7d"] or 0) > 0
            ],
            key=lambda x: -(x["minutes"] or 0),
        ),
        "burst_tenants": sorted(
            [
                {
                    "namespace": r["namespace"],
                    "kind": r["kind"],
                    "burst_ratio_7d": r["burst_ratio_7d"],
                    "cpu_max_7d": r["cpu_max_7d"],
                    "cpu_median_7d": r["cpu_median_7d"],
                    "has_quota": r["has_quota"],
                    "shares_nodes_with_prod": r["shares_nodes_with_prod"],
                }
                for r in ns_rows
                if (r["burst_ratio_7d"] or 0) >= 3 and (r["cpu_max_7d"] or 0) >= 0.5
            ],
            key=lambda x: -(x["burst_ratio_7d"] or 0),
        ),
        "throttled_prod": sorted(
            [{"namespace": r["namespace"], "throttled_ratio_7d": r["throttled_ratio_7d"], "shares_nodes_with_prod": r["shares_nodes_with_prod"], "nodes": r["nodes"]} for r in ns_rows if r["prod"] and (r["throttled_ratio_7d"] or 0) >= 0.1],
            key=lambda x: -(x["throttled_ratio_7d"] or 0),
        ),
        "top_cpu_share": [{"namespace": r["namespace"], "kind": r["kind"], "cpu_p95_7d": r["cpu_p95_7d"], "share": r["cpu_share_of_cluster_p95"]} for r in sorted(ns_rows, key=lambda r: -(r["cpu_p95_7d"] or 0))[:8]],
        "dominated_shared_nodes": [
            {
                "node": r["node"],
                "dominant_namespace": r["dominant_namespace"],
                "dominant_kind": r["dominant_kind"],
                "dominant_share_p95": r["dominant_share_p95"],
                "tenant_kinds": r["tenant_kinds"],
                "cpu_saturated_minutes_7d": r["cpu_saturated_minutes_7d"],
            }
            for r in nodes_out
            if r["tenant_count"] >= 2 and (r["dominant_share_p95"] or 0) >= 0.5
        ],
        "note": "The noisy-neighbour verdict is left to the LLM (type: llm, tenancy.noisy-neighbor). If node saturation minutes are 0, no neighbour could have done harm. Only nodes where a dominant namespace, saturation and prod throttling on the same node overlap are candidates.",
    }


def _namespaces_section(ns_rows: list[dict], tenant_rows: list[dict]) -> dict:
    """The `namespaces` output block: counts by kind, rows, and prod/tenant namespaces lacking quota, LimitRange, NetworkPolicy or PSA. Reads nothing."""
    return {
        "count": len(ns_rows),
        "by_kind": dict(Counter(r["kind"] for r in ns_rows)),
        "tenants_total": len(tenant_rows),
        "rows": ns_rows,
        "prod_without_quota": [r["namespace"] for r in ns_rows if r["prod"] and not r["has_quota"]],
        "tenants_without_quota": [r["namespace"] for r in tenant_rows if not r["has_quota"]],
        "tenants_without_limitrange": [r["namespace"] for r in tenant_rows if not r["has_limitrange"]],
        "prod_without_networkpolicy": [r["namespace"] for r in ns_rows if r["prod"] and r["networkpolicies"] == 0],
        "prod_without_psa": [r["namespace"] for r in ns_rows if r["prod"] and not r["psa_enforce"]],
        "classification_rule": "prod=inventory prod_like, dev=dev_like, ci=name (runner, ci, jenkins, tekton, ...) or a namespace with a runner CR, system=kube-* plus detected component namespaces, other=everything else",
    }


def _isolation_section(cx: _Ctx, pools_out: list[dict], nodes_out: list[dict], ci_templates: list[dict]) -> dict:
    """The `isolation` output block: pools, nodes, nodes shared by CI/dev and prod, CI templates and their constraints, plus a flat summary. Reads nothing."""
    return {
        "nodes_total": cx.nodes_total,
        "karpenter": cx.karpenter,
        "separation_possible": cx.separation_possible,
        "pools": pools_out,
        "nodes": nodes_out,
        "shared_nodes": [r for r in nodes_out if r["tenant_count"] >= 2],
        "ci_prod_nodes": [r["node"] for r in nodes_out if r["shares_ci_prod"]],
        "dev_prod_nodes": [r["node"] for r in nodes_out if r["shares_dev_prod"]],
        "ci_templates": ci_templates,
        "ci_namespaces": sorted(cx.tn.ci),
        "prod_namespaces": sorted(cx.tn.prod),
        "prod_present": bool(cx.tn.prod),
        "ci_unconstrained": [t["target"] for t in ci_templates if not t["constrained"]],
        "ci_without_dedicated_pool": [t["target"] for t in ci_templates if not t["dedicated_pool"]],
        "summary": {
            "ci_templates": len(ci_templates),
            "ci_constrained": sum(1 for t in ci_templates if t["constrained"]),
            "ci_dedicated_pool": sum(1 for t in ci_templates if t["dedicated_pool"]),
            "pools_tainted": sum(1 for p in pools_out if p["tainted"]),
            "pools": len(pools_out),
            "separation_possible": cx.separation_possible,
            "prod_present": bool(cx.tn.prod),
            "ci_prod_nodes": len([r for r in nodes_out if r["shares_ci_prod"]]),
            "dev_prod_nodes": len([r for r in nodes_out if r["shares_dev_prod"]]),
            "ci_pool_names": sorted({t["dedicated_pool"] for t in ci_templates if t["dedicated_pool"]}),
            "ci_unconstrained": [t["target"] for t in ci_templates if not t["constrained"]],
            "ci_without_dedicated_pool": [t["target"] for t in ci_templates if not t["dedicated_pool"]],
        },
    }


def analyze(snap: Path, inv: dict | None, security: dict | None = None) -> dict:
    cx = _Ctx(snap, inv)
    quotas_by_ns = _quotas(cx)
    lr_by_ns = _limitranges(cx)
    netpol_count, psa, enforced = _boundaries(cx, security)
    rb_subjects_by_ns, broad_by_subject, cross_tenant = _rbac_scope(cx)
    ns_pods, node_acc = _pod_aggregation(cx)
    nodes_out = _node_rows(cx, node_acc)
    pools_out = _pool_rows(cx, nodes_out)
    ci_templates = _ci_templates(cx, pools_out)
    parts = {
        "quotas_by_ns": quotas_by_ns,
        "lr_by_ns": lr_by_ns,
        "netpol_count": netpol_count,
        "psa": psa,
        "enforced": enforced,
        "rb_subjects_by_ns": rb_subjects_by_ns,
        "workload_counts": _workload_counts(cx),
        "multi_org": _multi_org(cx, rb_subjects_by_ns),
        "cluster_saturated_7d": any((v or 0) > 0 for v in cx.sat_min.values()),
    }
    ns_rows, tenant_rows = _namespace_rows(cx, ns_pods, nodes_out, parts)
    quotas_out = _quota_rows(quotas_by_ns, ns_rows)
    return {
        "namespaces": _namespaces_section(ns_rows, tenant_rows),
        "quotas": {
            "count": len(quotas_out),
            "rows": quotas_out,
            "near_limit": [q["target"] for q in quotas_out if q["max_ratio"] >= 0.8],
            "requires_requests_without_limitrange": [q["target"] for q in quotas_out if q["requires_requests"] and not q["limitrange_default_request"]],
        },
        "limitranges": {"count": sum(len(v) for v in lr_by_ns.values()), "rows": [ln for v in lr_by_ns.values() for ln in v]},
        "isolation": _isolation_section(cx, pools_out, nodes_out, ci_templates),
        "rbac": {"cross_tenant_broad": cross_tenant, "subjects_with_broad_roles": len(broad_by_subject)},
        "noisy": _noisy(cx, nodes_out, ns_rows),
    }

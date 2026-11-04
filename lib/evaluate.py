"""First-pass evaluation (evaluate).

Applies the expressions and thresholds in checks.yaml to the snapshot (summary.json, metrics/, objects/, inventory.json, aws/)
and writes per-check pass/warn/fail plus a default severity to `findings-draft.json`. Checks without an expression (type: llm)
are marked "LLM judgment". This is where the script stops; final severity, priority and conflict resolution are done by the LLM.
Finding ids are `<area>.<check id>.<ns>/<resource>` or `.cluster`.

Check expressions (`expr`, `warn_expr`, `target`, `evidence`) are Python evaluated with `eval` over a restricted builtins dict (SAFE_BUILTINS);
that restriction only keeps honest expressions small and is NOT a sandbox against malicious input. Expressions therefore come only from the
repository's own checks.yaml and rubric profiles, never from user config: config.yaml can set thresholds, profile names and suppressions, not code.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import fnmatch
import functools
import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from . import __version__, paths, rubric, versions
from .config import Config
from .resilience import is_db_like, mounts_pvc
from .snapshot import items, load_json, write_private

SAFE_BUILTINS = {
    "len": len,
    "any": any,
    "all": all,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "sorted": sorted,
    "isinstance": isinstance,
    "True": True,
    "False": False,
    "None": None,
    "re": re,
}

SYMPTOM_METRIC_RE = re.compile(r"\b(http_|grpc_|nginx_ingress_controller_|traefik_|aws_applicationelb_|probe_|haproxy_|envoy_|istio_requests|sli:|slo:)")


def _get_path(d, dotted: str):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class Context:
    """Snapshot data and helper functions shared during evaluation."""

    def __init__(self, snap: Path, inv: dict, summary: dict, profile: dict, ns_profiles: dict[str, dict] | None = None):
        self.snap, self.inv, self.summary, self.profile = snap, inv, summary, profile
        self.ns_profiles: dict[str, dict] = ns_profiles or {}  # config.yaml namespace_profiles: namespace glob -> loaded profile dict
        self.prod_like = set((inv.get("namespaces") or {}).get("prod_like") or [])
        self._objects: dict[str, list] = {}
        self._k8s_versions = rubric.load_k8s_versions()
        # `inv["today"]` (YYYY-MM-DD) pins the date the date-based checks compare against. Only the embedded test cases set it, so their
        # expected verdicts do not change as the calendar moves past a version's end-of-support date. A real inventory has no such key.
        self.today = _dt.date.fromisoformat(str(inv["today"])[:10]) if inv.get("today") else _dt.date.today()
        self._addon_versions: dict[str, dict] = {}
        self._owners: dict[tuple[str, str], str] | None = None
        self._pods: dict[tuple[str, str], dict] | None = None

    # ---- Stable finding ids: pod -> owning workload ----
    _KIND_SHORT: ClassVar[dict[str, str]] = {"Deployment": "deploy", "StatefulSet": "sts", "DaemonSet": "ds", "Job": "job", "CronJob": "cronjob", "ReplicaSet": "rs", "ReplicationController": "rc"}

    def _build_owners(self) -> None:
        self._owners = {}
        rs_owner: dict[tuple[str, str], tuple[str, str]] = {}
        for rs in self.objects("replicasets.apps"):
            ns, name = rs["metadata"]["namespace"], rs["metadata"]["name"]
            o = next(iter(rs["metadata"].get("ownerReferences") or []), None)
            if o:
                rs_owner[(ns, name)] = (o.get("kind"), o.get("name"))
        job_owner: dict[tuple[str, str], tuple[str, str]] = {}
        for j in self.objects("jobs.batch"):
            ns, name = j["metadata"]["namespace"], j["metadata"]["name"]
            o = next(iter(j["metadata"].get("ownerReferences") or []), None)
            if o:
                job_owner[(ns, name)] = (o.get("kind"), o.get("name"))
        for pod in self.objects("pods"):
            ns, name = pod["metadata"]["namespace"], pod["metadata"]["name"]
            o = next(iter(pod["metadata"].get("ownerReferences") or []), None)
            if not o:
                self._owners[(ns, name)] = f"pod/{name}"
                continue
            kind, oname = o.get("kind"), o.get("name")
            if kind == "ReplicaSet" and (ns, oname) in rs_owner:
                kind, oname = rs_owner[(ns, oname)]
            elif kind == "Job" and (ns, oname) in job_owner:
                kind, oname = job_owner[(ns, oname)]
            self._owners[(ns, name)] = f"{self._KIND_SHORT.get(kind, (kind or 'owner').lower())}/{oname}"

    def workload(self, labels: dict) -> str:
        """Map a metric label namespace/pod to its owning workload, e.g. `ns/deploy/<name>`. If the pod is not in the snapshot (already gone), strip the hash and guess."""
        if self._owners is None:
            self._build_owners()
        ns, pod = labels.get("namespace"), labels.get("pod")
        if not pod:
            return ns or "cluster"
        w = self._owners.get((ns, pod))
        if w is None:
            # A pod missing from the snapshot (already gone) is guessed from its name shape. `?` marks a guess.
            #   Job pod of a CronJob: <cronjob>-<numeric schedule id>-<pod hash>
            #   Deployment pod:       <deploy>-<rs hex hash>-<pod hash>
            if m := re.match(r"^(.*)-\d{6,}-[0-9a-z]{5}$", pod):
                w = f"cronjob?/{m.group(1)}"
            elif m := re.match(r"^(.*)-[0-9a-f]{5,10}-[0-9a-z]{5}$", pod):
                w = f"deploy?/{m.group(1)}"
            else:
                w = f"pod/{pod}"
            # Drop the guess marker (?) when a confirmed owner with the same name exists in the namespace
            if "?" in w and (ns, w.replace("?", "")) in self._known_owner_names:
                w = w.replace("?", "")
        return f"{ns}/{w}"

    def db_like(self, labels: dict) -> bool:
        """Does the metric's container run a database, cache or message queue? Looks the pod up in objects/pods.json and judges the container named in
        `labels['container']` by its name, image repository and owning workload, with lib.resilience.is_db_like. Init containers count, since a native sidecar reports its own series.
        Without a container label every container of the pod must be database-like, so a pod-level series of a Redis with an exporter sidecar is not.
        A pod that is already gone from the snapshot is judged from the pod and container names alone."""
        ns, pod, container = labels.get("namespace"), labels.get("pod"), labels.get("container")
        if not pod:
            return False
        if self._pods is None:
            self._pods = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in self.objects("pods")}
        owner = self.workload(labels)  # `ns/deploy/name`, `ns/deploy?/name`, `ns/sts/name`, `ns/pod/name`: the name never contains `/`
        wl = owner.rsplit("/", 1)[-1]
        obj = self._pods.get((ns, pod))
        if obj is None:
            return is_db_like(container, None, wl)
        spec = self.pod_spec(obj)
        stateful = "/sts/" in owner and mounts_pvc(spec)  # a StatefulSet pod with a PersistentVolumeClaim is a store whatever its image is called
        cs = [c for c in (spec.get("containers") or []) + (spec.get("initContainers") or []) if not container or c.get("name") == container]
        return bool(cs) and all(is_db_like(c.get("name"), c.get("image"), wl, stateful=stateful) for c in cs)

    TRANSIENT_KINDS: ClassVar[tuple[str, ...]] = ("job", "cronjob", "cronjob?", "runner", "ephemeralrunner", "autoscalingrunnerset")

    def is_transient(self, labels: dict) -> bool:
        """Pods that are normally short-lived or idle: owned by a Job/CronJob, or GitHub Actions runners (ARC EphemeralRunner). Excluded from usage-vs-request and throttling checks."""
        w = self.workload(labels)
        kind = w.split("/")[1] if w.count("/") >= 2 else ""
        return kind in self.TRANSIENT_KINDS or "runner" in kind

    @functools.cached_property
    def _known_owner_names(self) -> set[tuple[str, str]]:
        """(namespace, workload) pairs with a confirmed owner in the snapshot. Computed once, after the owner map is built."""
        if self._owners is None:
            self._build_owners()
        return {(ns, w) for (ns, _), w in (self._owners or {}).items()}

    # ---- Objects ----
    def objects(self, file_stem: str) -> list:
        if file_stem not in self._objects:
            self._objects[file_stem] = items(load_json(self.snap / "objects" / f"{file_stem}.json"))
        return self._objects[file_stem]

    def metric(self, qid: str) -> dict | None:
        return load_json(self.snap / "metrics" / f"{qid}.json")

    @functools.cached_property
    def _node_ids(self) -> set[str]:
        """Names and addresses of the nodes in inventory.json. Empty when the inventory lists no nodes, as in the embedded test cases; then no series is treated as a gone node."""
        ids: set[str] = set()
        for n in ((self.inv.get("nodes") or {}).get("nodes") or []) if isinstance(self.inv.get("nodes"), dict) else []:
            for k in ("name", "internal_ip", "external_ip"):
                if n.get(k):
                    ids.add(str(n[k]))
        return ids

    def node_gone(self, labels: dict, area: str | None = None) -> str | None:
        """For a series that names a node: the node's name or address when the inventory knows the cluster's nodes and this one is not among them, else None.
        A series names a node when it carries a `node` label without a `pod` label, or, in a check of area `node`, an `instance` label (node-exporter's `<ip>:9100`; prometheus-operator adds the
        exporter's `pod` label to those, so the pod label does not disqualify a node-area series). `instance` labels of other areas belong to apiservers, kube-state-metrics or Prometheus itself
        and are never compared. The port is dropped and IPv6 brackets removed before the comparison. A node that left within the metric window still has series in it, and a check about the
        nodes of the cluster has nothing to say about a node that is no longer one of them."""
        if not self._node_ids:
            return None
        if labels.get("node") and not labels.get("pod"):
            raw = str(labels["node"])
        elif area == "node" and (labels.get("node") or labels.get("instance")):
            raw = str(labels.get("node") or labels.get("instance"))
        else:
            return None
        name = raw
        if m := re.match(r"^\[(.+)\](?::\d+)?$", raw):
            name = m.group(1)
        elif ":" in raw and raw.rsplit(":", 1)[1].isdigit() and raw.count(":") == 1:
            name = raw.rsplit(":", 1)[0]
        return None if (name in self._node_ids or raw in self._node_ids) else name

    def aws_file(self, name: str):
        return load_json(self.snap / "aws" / name)

    # ---- Helpers (names available inside expressions) ----
    def is_prod(self, ns: str | None) -> bool:
        return ns in self.prod_like

    @staticmethod
    def pod_spec(obj: dict) -> dict:
        if (obj.get("kind") == "Pod") or ("containers" in (obj.get("spec") or {})):
            return obj.get("spec") or {}
        return ((obj.get("spec") or {}).get("template") or {}).get("spec") or {}

    def containers(self, obj: dict) -> list:
        return self.pod_spec(obj).get("containers") or []

    @staticmethod
    def _template_labels(obj: dict) -> dict:
        return (((obj.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}

    @staticmethod
    def _selector_matches(selector: dict | None, labels: dict) -> bool:
        if not selector:
            return False
        ml = selector.get("matchLabels") or {}
        if any(labels.get(k) != v for k, v in ml.items()):
            return False
        for e in selector.get("matchExpressions") or []:
            k, op, vals = e.get("key"), e.get("operator"), e.get("values") or []
            if op == "In" and labels.get(k) not in vals:
                return False
            if op == "NotIn" and labels.get(k) in vals:
                return False
            if op == "Exists" and k not in labels:
                return False
            if op == "DoesNotExist" and k in labels:
                return False
        return True

    def pdb_covers(self, obj: dict) -> bool:
        ns = obj["metadata"]["namespace"]
        labels = self._template_labels(obj)
        return any(pdb["metadata"]["namespace"] == ns and self._selector_matches((pdb.get("spec") or {}).get("selector"), labels) for pdb in self.objects("poddisruptionbudgets.policy"))

    def hpa_covers(self, obj: dict) -> bool:
        ns, name, kind = obj["metadata"]["namespace"], obj["metadata"]["name"], obj.get("kind") or "Deployment"
        for h in self.objects("horizontalpodautoscalers.autoscaling"):
            ref = (h.get("spec") or {}).get("scaleTargetRef") or {}
            if h["metadata"]["namespace"] == ns and ref.get("name") == name and (ref.get("kind") or "Deployment") == kind:
                return True
        for so in self.objects("scaledobjects.keda.sh"):
            ref = (so.get("spec") or {}).get("scaleTargetRef") or {}
            if so["metadata"]["namespace"] == ns and ref.get("name") == name:
                return True
        return False

    def has_service(self, obj: dict) -> bool:
        ns = obj["metadata"]["namespace"]
        labels = self._template_labels(obj)
        for s in self.objects("services"):
            sel = (s.get("spec") or {}).get("selector")
            if s["metadata"]["namespace"] == ns and sel and all(labels.get(k) == v for k, v in sel.items()):
                return True
        return False

    def symptom_rule_count(self, rules: list) -> int:
        n = 0
        for pr in rules:
            for g in (pr.get("spec") or {}).get("groups") or []:
                for r in g.get("rules") or []:
                    if r.get("alert") and SYMPTOM_METRIC_RE.search(str(r.get("expr") or "")):
                        n += 1
        return n

    def netpol_coverage(self) -> dict:
        """NetworkPolicy presence per namespace. System namespaces are excluded. Result: {"with": [...], "without": [...], "without_prod": [...]}"""
        system = {"kube-system", "kube-public", "kube-node-lease", "default"}
        ns_all = [n["metadata"]["name"] for n in self.objects("namespaces")]
        has = {np["metadata"]["namespace"] for np in self.objects("networkpolicies.networking.k8s.io")}
        user_ns = [n for n in ns_all if n not in system]
        without = [n for n in user_ns if n not in has]
        return {"with": sorted(has & set(user_ns)), "without": without, "without_prod": [n for n in without if n in self.prod_like], "total_user_ns": len(user_ns)}

    def k8s_support_ends(self, version: str | None) -> dict:
        """The two dates on which support for a minor version ends, each named by its source, because they are different facts with different dates (#11):
        `upstream`, the day the Kubernetes project stops patching the minor (rubric/k8s-versions.yaml), and on EKS `eks_standard`, the day AWS moves the version
        to extended support billing (describe-cluster-versions endOfStandardSupportDate). `primary` is the one the platform's operator acts on: EKS standard support on EKS, upstream elsewhere."""
        out: dict = {"minor": None, "upstream": None, "eks_standard": None, "primary": None, "primary_source": None}
        if not version:
            return out
        minor = versions.minor_text(version)
        if not minor:
            return out
        out["minor"] = minor
        for row in self._k8s_versions:
            if str(row.get("minor")) == minor:
                out["upstream"] = str(row.get("eol"))
        if (self.inv.get("cluster") or {}).get("eks"):
            cv = self.aws_file("describe-cluster-versions.json")
            for v in (cv or {}).get("clusterVersions") or []:
                if v.get("clusterVersion") == minor and v.get("endOfStandardSupportDate"):
                    out["eks_standard"] = str(v["endOfStandardSupportDate"])[:10]
        if out["eks_standard"]:
            out["primary"], out["primary_source"] = out["eks_standard"], "EKS end of standard support"
        elif out["upstream"]:
            out["primary"], out["primary_source"] = out["upstream"], "upstream end of life"
        return out

    def k8s_eol(self, version: str | None):
        """The support end date the platform's operator acts on; see k8s_support_ends for which source it is."""
        return self.k8s_support_ends(version)["primary"]

    def eol_badge(self, version: str | None) -> str:
        """The support end written with its source and the distance: 'EKS end of standard support 2026-03-23, 140 days left; upstream end of life 2026-02-28'.
        On EKS both dates are named when they differ, since they are different events; elsewhere only the upstream date exists."""
        ends = self.k8s_support_ends(version)
        d = self.days_until(ends["primary"])
        if ends["primary"] is None or d is None:
            return "end of support unknown"
        dist = f"{d} days left" if d >= 0 else f"{-d} days past"
        text = f"{ends['primary_source']} {ends['primary']}, {dist}"
        if ends["eks_standard"] and ends["upstream"] and ends["upstream"] != ends["eks_standard"]:
            text += f"; upstream end of life {ends['upstream']}"
        return text

    def backup_signals(self) -> dict:
        """There may be backup activity even without a backup tool: k3s etcd snapshot objects, CronJobs named backup/dump/snapshot, VolumeSnapshots."""
        etcd = self.objects("etcdsnapshotfiles.k3s.cattle.io")
        cron, stale = [], []
        for c in self.objects("cronjobs.batch"):
            if not re.search(r"backup|dump|snapshot|archive", c["metadata"]["name"], re.IGNORECASE):
                continue
            name = f"{c['metadata']['namespace']}/{c['metadata']['name']}"
            last = self.days_until((c.get("status") or {}).get("lastSuccessfulTime"))
            created = self.days_until(c["metadata"].get("creationTimestamp"))
            # a CronJob is a backup signal only while it produces copies: not suspended and succeeded within 7 days, or created in the last 2 days and not yet due
            if (c.get("spec") or {}).get("suspend"):
                stale.append(f"{name} (suspended)")
            elif (last is not None and last >= -7) or (last is None and created is not None and created >= -2):
                cron.append(name)
            else:
                stale.append(f"{name} (last success {-last} days ago)" if last is not None else f"{name} (never succeeded)")
        vs = self.objects("volumesnapshots.snapshot.storage.k8s.io")
        return {"etcd_snapshots": len(etcd), "backup_cronjobs": cron, "stale_backup_cronjobs": stale, "volume_snapshots": len(vs), "any": bool(etcd or cron or vs)}

    def serves_traffic(self, obj: dict) -> bool:
        """Is this a target for readiness/preStop checks: replicas not 0, has a container port, and a Service points at it."""
        if (obj.get("spec") or {}).get("replicas") == 0:
            return False
        if not any((c.get("ports") or []) for c in self.containers(obj)):
            return False
        return self.has_service(obj)

    def days_until(self, date_str) -> int | None:
        if not date_str:
            return None
        try:
            d = _dt.date.fromisoformat(str(date_str)[:10])
        except ValueError:
            return None
        return (d - self.today).days

    def _addon_versions_for(self, addon: str) -> dict:
        if addon not in self._addon_versions:
            d = self.aws_file(f"describe-addon-versions-{addon}.json") or {}
            vs = ((d.get("addons") or [{}])[0]).get("addonVersions") or []
            latest = vs[0].get("addonVersion") if vs else None
            default = next((v.get("addonVersion") for v in vs if any(c.get("defaultVersion") for c in (v.get("compatibilities") or []))), None)
            self._addon_versions[addon] = {"latest": latest, "default": default}
        return self._addon_versions[addon]

    def addon_latest(self, addon: str):
        return self._addon_versions_for(addon)["latest"]

    def addon_default(self, addon: str):
        return self._addon_versions_for(addon)["default"]

    @staticmethod
    def addon_minor_gap(installed: str | None, latest: str | None) -> int:
        return versions.minor_gap(installed, latest)

    def eks_version_dates(self) -> dict:
        cv = self.aws_file("describe-cluster-versions.json") or {}
        rows = cv.get("clusterVersions") or []
        return rows[0] if rows else {}

    def eks_version_status(self):
        return self.eks_version_dates().get("status")

    def karpenter_pool_nodes(self, pool: str) -> int:
        """Number of NodeClaims in the NodePool (label karpenter.sh/nodepool)."""
        return sum(1 for o in self.objects("nodeclaims.karpenter.sh") if ((o.get("metadata") or {}).get("labels") or {}).get("karpenter.sh/nodepool") == pool)

    @staticmethod
    def karpenter_budget_allowed(spec: dict, nodes: int) -> int | None:
        """Minimum allowed disruptions among disruption.budgets without a schedule (always in effect). '10%' means ceil(node count x 10%),
        per the Karpenter docs formula allowed = roundup(total x percentage) - deleting - notready (rounded up). An earlier version used floor;
        real logs (4 actual disruptions) showed that was wrong. No budgets -> None (= default 10%, also rounded up, so at least 1 with one or more nodes)."""
        import math

        budgets = ((spec or {}).get("disruption") or {}).get("budgets") or []
        vals = []
        for b in budgets:
            if b.get("schedule"):
                continue
            v = str(b.get("nodes", "10%"))
            vals.append(math.ceil(nodes * int(v.rstrip("%")) / 100) if v.endswith("%") else int(v))
        if not vals:
            return math.ceil(nodes * 0.1) if budgets == [] else None
        return min(vals)

    def helpers(self) -> dict:
        return {
            "karpenter_pool_nodes": self.karpenter_pool_nodes,
            "karpenter_budget_allowed": self.karpenter_budget_allowed,
            "containers": self.containers,
            "pod_spec": self.pod_spec,
            "pdb_covers": self.pdb_covers,
            "hpa_covers": self.hpa_covers,
            "has_service": self.has_service,
            "symptom_rule_count": self.symptom_rule_count,
            "k8s_eol": self.k8s_eol,
            "k8s_support_ends": self.k8s_support_ends,
            "days_until": self.days_until,
            "aws_file": self.aws_file,
            "addon_latest": self.addon_latest,
            "addon_default": self.addon_default,
            "addon_minor_gap": self.addon_minor_gap,
            "eks_version_status": self.eks_version_status,
            "eks_version_dates": self.eks_version_dates,
            "is_prod": self.is_prod,
            "workload": self.workload,
            "netpol_coverage": self.netpol_coverage,
            "eol_badge": self.eol_badge,
            "backup_signals": self.backup_signals,
            "serves_traffic": self.serves_traffic,
            "db_like": self.db_like,
            "_sg_text": sg_text,
            "_oom_text": oom_text,
            "inv": self.inv,
            "summary": self.summary,
            "ctx": {"profile": self.profile.get("name"), "platform": (self.inv.get("cluster") or {}).get("platform"), "prod_like": sorted(self.prod_like)},
        }


def sg_text(item: dict) -> str:
    """One phrase for the evidence of traffic.db-exposed: what the load balancer's security groups let in, as counts, never the addresses themselves."""
    state = item.get("sg_exposure")
    allowed = item.get("allowed_sources") or {}
    if state == "open":
        ports = ", ".join(str(p) for p in sorted(int(p) for p in item.get("open_ports") or []))
        return f"open to 0.0.0.0/0 on {ports}" if ports else "open to 0.0.0.0/0"
    if state == "allow-list":
        n = max(allowed.values(), default=0)
        widths = list((item.get("widest_prefix") or {}).values())
        known = [w for w in widths if w is not None]
        hidden = sum(1 for w in widths if w is None)
        if known:
            width = f"widest /{min(known)}" + (f"; {hidden} port{'s' if hidden != 1 else ''} also allow{'s' if hidden == 1 else ''} a prefix list or security group reference" if hidden else "")
        else:
            width = "width unknown, a prefix list or security group reference"
        return f"allow-list, at most {n} source{'s' if n != 1 else ''} per port, {width}"
    if state == "blocked":
        return "no inbound rule covers the ports"
    if state == "no-security-group":
        return "none on the load balancer, only the targets' groups filter it"
    if state == "not-read":
        return "not read"
    if state == "unmatched":
        return "unknown, no described load balancer matched the Service address"
    return "not applicable"


def oom_text(item: dict) -> str:
    """The evidence of resources.oomkilled-repeated from a `resilience.oom_7d` row: both sources with their windows, never one number standing for the other."""
    total = item.get("kernel_nodes_total") or 0
    if item.get("kernel_log_read"):
        n = item.get("kernel_kills_24h") or 0
        kern = f"kernel log: {n} kill{'s' if n != 1 else ''} in 24 h on {item.get('kernel_nodes_read')} of {total} node{'s' if total != 1 else ''} read"
        if item.get("last_kill"):
            kern += f", last {item['last_kill']}"
        if item.get("kernel_nodes_old_script"):
            kern += f"; {item['kernel_nodes_old_script']} node{'s' if item['kernel_nodes_old_script'] != 1 else ''} ran the older node script, which keeps no oom-kill lines"
    elif item.get("kernel_nodes_old_script"):
        kern = f"kernel log read on {item['kernel_nodes_old_script']} node{'s' if item['kernel_nodes_old_script'] != 1 else ''} with the older node script, which keeps no oom-kill lines, so kills are not attributed; {item.get('kernel_cgroup_ooms_on_nodes') or 0} container OOM{'s' if (item.get('kernel_cgroup_ooms_on_nodes') or 0) != 1 else ''} counted on those nodes for every workload together"
    elif not item.get("kernel_any_node_read"):
        kern = "kernel log not read in this mode"
    elif total == 0:
        kern = "kernel log read, but the nodes of this workload's pods are unknown"
    else:
        kern = "kernel log not read on its node, no node access there"
    pods = item.get("pods_oomkilled") or 0
    rep = item.get("pods_replaced") or 0
    prom = f"Prometheus: {pods} pod{'s' if pods != 1 else ''} ended by OOM in 7 days" + (f", {rep} already replaced" if rep else "") + f", {item.get('restarts_of_those_pods') or 0} restarts in those pods"
    return f"{kern}. {prom}. cAdvisor counter {item.get('cadvisor_oom_events_7d') or 0}"


def _eval(expr: str, env: dict):
    return eval(expr, {"__builtins__": SAFE_BUILTINS}, env)


def _status(rule: dict, env: dict) -> str:
    """A rule without `expr` never fails (warn-only check); without `warn_expr` it never warns."""
    if rule.get("expr") and _eval(rule["expr"], env):
        return "fail"
    if rule.get("warn_expr") and _eval(rule["warn_expr"], env):
        return "warn"
    return "pass"


def _ns_profile_disables(check_id: str, target: str, env: dict, ns_profiles: dict[str, dict]) -> bool:
    """config.yaml namespace_profiles (glob -> profile name). If the finding's namespace maps to a profile whose disabled_checks lists this check, the finding is not emitted."""
    ns = None
    for key in ("ns",):
        if isinstance(env.get(key), str) and env[key]:
            ns = env[key]
    if ns is None:
        lab = env.get("labels")
        if isinstance(lab, dict) and lab.get("namespace"):
            ns = lab["namespace"]
    if ns is None:
        it = env.get("item")
        if isinstance(it, dict) and isinstance(it.get("namespace"), str):
            ns = it["namespace"]
    if ns is None and "/" in (target or ""):
        ns = target.split("/", 1)[0]
    if not ns:
        return False
    return any(fnmatch.fnmatch(ns, pat) and check_id in (prof.get("disabled_checks") or []) for pat, prof in ns_profiles.items())


def _excluded(check_id: str, target: str, profile: dict) -> bool:
    pats = (profile.get("exclude") or {}).get(check_id) or []
    return any(fnmatch.fnmatchcase(target, p) for p in pats)


def _finding(check: dict, target: str, status: str, evidence, source: str, extra: dict | None = None) -> dict:
    return {
        "id": f"{check['id']}.{target}",
        "check": check["id"],
        "name": check["name"],
        "area": check["area"],
        "type": check["type"],
        "status": status,
        "severity_default": check["severity_default"],
        "symptom_linked": bool(check.get("symptom_linked")),
        "target": target,
        "evidence": evidence,
        "source": source,
        "collector": check.get("collector"),
        **(extra or {}),
    }


KEY_HARD_RE = re.compile(r"item\['([^']+)'\]")
KEY_SOFT_RE = re.compile(r"item\.get\('([^']+)'")


def referenced_keys(check: dict) -> set[str]:
    """The `item` keys a summary check's expressions read: `item['k']` and `item.get('k')` across rule, target and evidence. selftest audits these against a real summary; `details` keeps exactly these."""
    rule = check.get("rule") or {}
    texts = " ".join(str(x) for x in (rule.get("expr"), rule.get("warn_expr"), check.get("target"), check.get("evidence")) if x)
    return set(KEY_HARD_RE.findall(texts)) | set(KEY_SOFT_RE.findall(texts))


class ItemRecorder(dict):
    """A summary or inventory item that remembers which top-level keys the rule, target, evidence and the helpers they call actually read. `details` keeps exactly those keys,
    so a helper such as `_oom_text(item)` that reads `last_kill` leaves `last_kill` in the finding, which a regex over the expression text could never know. Iterating the whole
    item (`str(item)`, `item.items()`) counts as reading every key."""

    def __init__(self, data: dict):
        super().__init__(data)
        self.read: set[str] = set()
        self.read_all = False

    def __getitem__(self, k):
        self.read.add(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self.read.add(k)
        return super().get(k, default)

    def __contains__(self, k):
        self.read.add(k)
        return super().__contains__(k)

    def _all(self):
        self.read_all = True

    def items(self):
        self._all()
        return super().items()

    def values(self):
        self._all()
        return super().values()

    def __iter__(self):
        self._all()
        return super().__iter__()

    def __repr__(self):
        self._all()
        return super().__repr__()

    def kept(self) -> dict:
        if self.read_all:
            return dict(self)
        return {k: super(ItemRecorder, self).__getitem__(k) for k in self.read if dict.__contains__(self, k)}


def _details(check: dict, env: dict) -> dict | None:
    """The material the rule judged, kept whole on the finding (#64). The evidence is one line for a table and may cut a list; `details` is where the rest lives.
    summary and inventory checks: the item's keys that were actually read while judging it (ItemRecorder), never a key the check did not read.
    metric checks: labels and the value, or every joined value. object checks: namespace, name and kind. Checks without an item (absence, cluster-level object checks) carry none."""
    item = env.get("item")
    if isinstance(item, ItemRecorder):
        kept = item.kept()
        return {"key": env.get("key"), "item": kept} if "key" in env else kept
    if isinstance(item, dict):
        keys = referenced_keys(check)
        kept = {k: item[k] for k in keys if k in item} if keys else item
        return {"key": env.get("key"), "item": kept} if "key" in env else kept
    if item is not None and "key" in env:
        return {"key": env.get("key"), "item": item}
    if isinstance(env.get("labels"), dict):
        out: dict = {"labels": env["labels"]}
        if isinstance(env.get("v"), dict):
            out["values"] = env["v"]
        elif "value" in env:
            out["value"] = env["value"]
        return out
    obj = env.get("obj")
    if isinstance(obj, dict):
        return {"namespace": env.get("ns"), "name": env.get("name"), "kind": obj.get("kind")}
    return None


class _Run:
    """Mutable state of one check evaluation shared by the type handlers: the check, its thresholds, the collected findings and status counts.

    `emit()` is the single place where a rule is applied to one target, so exclusions (profile `exclude`, namespace profiles) and the merging of
    several instances of one target (Job pods of a CronJob, replicas) behave the same for every check type."""

    _ORDER: ClassVar[dict[str, int]] = {"fail": 0, "warn": 1}

    def __init__(self, check: dict, cx: Context, thresholds: dict):
        self.check, self.cx, self.thresholds = check, cx, thresholds
        self.rule = check.get("rule") or {}
        self.base_env = {**cx.helpers(), **thresholds}
        self.findings: list[dict] = []
        self.counts: Counter = Counter()
        self._by_target: dict[str, dict] = {}
        self.gone_nodes: set[str] = set()
        self.skipped_reasons: Counter = Counter()

    def emit(self, env: dict, default_target: str, source: str) -> None:
        check, cx = self.check, self.cx
        target = str(_eval(check["target"], env)) if check.get("target") else default_target
        if _excluded(check["id"], target, cx.profile) or (cx.ns_profiles and _ns_profile_disables(check["id"], target, env, cx.ns_profiles)):
            self.counts["excluded"] += 1
            return
        if self.rule.get("needs") and not _eval(self.rule["needs"], env):
            # The rule says what it needs to judge (`needs`); without it the target is not judged, never passed. Counted and named in the result so the report says "N of M not judged: <reason>"
            self.counts["skipped"] += 1
            self.skipped_reasons[self.rule.get("needs_reason") or f"needs {self.rule['needs']}"] += 1
            return
        st = _status(self.rule, env)
        self.counts[st] += 1
        if st not in ("fail", "warn"):
            return
        ev = _eval(check["evidence"], env) if check.get("evidence") else None
        det = _details(check, env)
        if target in self._by_target:
            # When several pods of one workload (Job pods of a CronJob, replicas) map to the same target, merge their evidence into one finding
            f = self._by_target[target]
            f["instances"] = f.get("instances", 1) + 1
            if isinstance(f["evidence"], list):
                f["evidence"].append(ev)
            else:
                f["evidence"] = [f["evidence"], ev]
            if det is not None:
                prev = f.get("details")
                f["details"] = [d for d in ((prev if isinstance(prev, list) else [prev]) + [det]) if d is not None]
            if self._ORDER[st] < self._ORDER[f["status"]]:
                f["status"] = st
            return
        f = _finding(check, target, st, ev, source, {"details": det} if det is not None else None)
        self._by_target[target] = f
        self.findings.append(f)

    def gone_node(self, name: str) -> None:
        """A series of a node that is no longer in the cluster: not judged, counted, and named in the check's result so the report can say the node left within the window."""
        self.gone_nodes.add(name)
        self.counts["gone_node"] += 1

    def done(self) -> dict:
        reasons = "; ".join(f"{r} ({n})" if n > 1 else r for r, n in self.skipped_reasons.most_common())
        if self.counts.get("skipped") and not any(self.counts.get(k) for k in ("pass", "fail", "warn", "excluded", "gone_node")):
            return {**self.skip(f"nothing to judge: {reasons}"), "counts": dict(self.counts)}  # every target lacked what the rule needs: the check is skipped, not passed
        out = {"status": "done", "counts": dict(self.counts), "findings": self.findings}
        if self.gone_nodes:
            out["gone_nodes"] = sorted(self.gone_nodes)
        if self.counts.get("skipped"):
            out["skipped_reason"] = reasons  # some targets were judged, these were not; render lists them in section 7-5
        return out

    @staticmethod
    def skip(reason: str) -> dict:
        return {"status": "skip", "reason": reason, "counts": {}, "findings": []}


def _eval_signature(cx: Context, check: dict, run: _Run) -> dict:
    """Log signatures: one finding per match in summary.logs.signatures. Area, severity and description come from the signature, not the check."""
    for sig in _get_path(cx.summary, "logs.signatures") or []:
        st = sig.get("status")
        if st not in ("fail", "warn"):
            run.counts["pass"] += 1
            continue
        if _excluded(check["id"], sig["id"], cx.profile):
            run.counts["excluded"] += 1
            continue
        run.counts[st] += 1
        ev = (
            f"{sig['count']} occurrences" + (f" ({sig.get('first')} ~ {sig.get('last')})" if sig.get("first") else "") + f", thresholds warn {sig['warn_at']}/fail {sig['fail_at']}"
            f". Files: {list(sig.get('files') or {})[:3]}. Samples: {[x[:160] for x in (sig.get('samples') or [])[:2]]}"
        )
        f = _finding(
            check,
            sig["id"],
            st,
            ev,
            "summary.json:logs.signatures",
            {
                "signature": sig["id"],
                "component": sig["component"],
                "details": {k: sig.get(k) for k in ("count", "first", "last", "warn_at", "fail_at", "files", "samples") if k in sig},
            },  # the evidence cuts files and samples; details keeps them
        )
        f.update(
            area=sig["area"],
            severity_default=sig["severity"],
            name=f"[log] {sig['name']}",
            symptom_linked=sig["area"] in ("traffic", "resilience"),
            why=sig.get("meaning"),
            suggest=sig.get("cause"),
            verify=[sig["verify"]] if sig.get("verify") else None,
            notes="signatures/catalog.yaml " + sig["id"],
        )
        run.findings.append(f)
    return run.done()


def _eval_llm(cx: Context, check: dict, run: _Run) -> dict:
    """No rule: the LLM judges from the listed inputs. One placeholder finding so the report knows to look."""
    return {"status": "llm", "counts": {}, "findings": [_finding(check, "cluster", "llm", check.get("why"), check.get("inputs") or "", {})]}


def _eval_absence(cx: Context, check: dict, run: _Run) -> dict:
    fam, comp = check.get("family"), check.get("component")
    present = set(cx.inv.get("families_present") or [])
    comps = set(cx.inv.get("components_present") or [])
    expected = cx.profile.get("expected_families")
    if fam and expected is not None and fam not in expected:
        return run.skip(f"profile {cx.profile.get('name')} does not require family {fam}")
    missing = (fam and fam not in present) or (comp and comp not in comps)
    if not missing:
        run.counts["pass"] += 1
        return run.done()
    st = "fail"
    ev = f"no component of family {fam or comp} in inventory.components"
    # Even for absence, if rule.warn_expr exists and is true (a substitute signal), downgrade to warn. Example: no backup tool, but etcd snapshots or dump CronJobs exist
    if run.rule.get("warn_expr") and _eval(run.rule["warn_expr"], run.base_env):
        st = "warn"
    if check.get("evidence"):
        ev = _eval(check["evidence"], run.base_env)
    run.findings.append(_finding(check, "cluster", st, ev, "inventory.json"))
    run.counts[st] += 1
    return run.done()


def _metric_target(cx: Context, labels: dict, fallback: str) -> str:
    """Pod series are attributed to their owning workload (stable id across restarts); other series to namespace/node."""
    if labels.get("pod"):
        return cx.workload(labels) + (":" + labels["container"] if labels.get("container") else "")
    return fallback


def _eval_metric(cx: Context, check: dict, run: _Run) -> dict:
    inputs = check.get("inputs") or []
    if len(inputs) == 1:
        m = cx.metric(inputs[0])
        if not m:
            return run.skip(f"metrics/{inputs[0]}.json missing (not collected or no Prometheus)")
        if not m.get("ok"):
            return run.skip(f"query failed: {m.get('error')}")
        for s in m.get("result", []):
            try:
                value = float(s["value"][1])
            except (KeyError, ValueError, TypeError, IndexError):
                continue
            labels = s.get("metric", {})
            if gone := cx.node_gone(labels, check.get("area")):
                run.gone_node(gone)
                continue
            env = {**run.base_env, "value": value, "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
            default_target = _metric_target(cx, labels, "/".join(x for x in (labels.get("namespace"), labels.get("node") or labels.get("instance")) if x) or "cluster")
            if check.get("exclude_transient") and labels.get("pod") and cx.is_transient(labels):
                run.counts["excluded"] += 1
                continue
            run.emit(env, default_target, f"metrics/{inputs[0]}.json")
        return run.done()
    key = check.get("join_on") or "node"
    keys = list(key) if isinstance(key, list) else [key]  # join_on is one label or a list ([namespace, pod, container])
    primary = inputs[0]  # Series absent from the first input are not judged (secondary inputs only supply evidence numbers) unless the check says `join_any: true`, where a series in any input is judged and the rule reads `v` with .get()
    join_any = bool(check.get("join_any"))
    joined: dict[tuple, dict] = {}
    present = []
    for qid in inputs:
        m = cx.metric(qid)
        if not m or not m.get("ok"):
            if qid == primary and not join_any:
                return run.skip(f"metrics/{qid}.json missing or failed")
            continue
        present.append(qid)
        for s in m.get("result", []):
            lab = s.get("metric", {})
            k = tuple(lab.get(x) for x in keys)
            if any(x is None for x in k):
                continue
            with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
                joined.setdefault(k, {})[qid] = float(s["value"][1])
    if join_any and not present:
        return run.skip("metrics/" + ",".join(inputs) + " all missing or failed")
    for k, v in joined.items():
        if primary not in v and not join_any:
            continue
        labels = dict(zip(keys, k, strict=False))
        if gone := cx.node_gone(labels, check.get("area")):
            run.gone_node(gone)
            continue
        env = {**run.base_env, "v": v, "value": v.get(primary, next(iter(v.values()))), "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
        default_target = _metric_target(cx, labels, "/".join(str(x) for x in k))
        if check.get("exclude_transient") and labels.get("pod") and cx.is_transient(labels):
            run.counts["excluded"] += 1
            continue
        run.emit(env, default_target, "metrics/" + ",".join(inputs))
    return run.done()


# Object stems that helpers read (pdb_covers, hpa_covers, has_service) but that are never the judged objects of an object-type check
_HELPER_ONLY_STEMS = ("poddisruptionbudgets.policy", "horizontalpodautoscalers.autoscaling", "services")


def _eval_object(cx: Context, check: dict, run: _Run) -> dict:
    inputs = check.get("inputs") or []
    stems = [Path(i).stem for i in inputs if i.startswith("objects/")]
    if check.get("cluster_level"):
        objs = []
        for st in stems:
            objs += cx.objects(st)
        if not stems or not (cx.snap / "objects" / f"{stems[0]}.json").is_file():
            return run.skip(f"{inputs[0]} missing")
        run.emit({**run.base_env, "objs": objs, "prod": False}, "cluster", ", ".join(inputs))
        return run.done()
    any_file = False
    for st in (st for st in stems if st not in _HELPER_ONLY_STEMS):
        if not (cx.snap / "objects" / f"{st}.json").is_file():
            continue
        any_file = True
        for obj in cx.objects(st):
            ns, name = obj["metadata"].get("namespace") or "", obj["metadata"]["name"]
            env = {**run.base_env, "obj": obj, "ns": ns, "name": name, "spec": obj.get("spec") or {}, "prod": cx.is_prod(ns)}
            run.emit(env, f"{ns}/{name}" if ns else name, f"objects/{st}.json")
    if not any_file:
        return run.skip(f"{', '.join(inputs)} missing")
    return run.done()


def _eval_summary(cx: Context, check: dict, run: _Run) -> dict:
    seq = _get_path(cx.summary, check["each"]) if check.get("each") else None
    if seq is None:
        return run.skip(f"summary.{check.get('each')} missing")
    if check.get("cluster_level") or isinstance(seq, dict):
        seq = [seq]  # If the path is a single dict, it is the one item (cluster level)
    for item in seq:
        default_target = str(item)[:60]
        rec = ItemRecorder(item) if isinstance(item, dict) else item  # after the default target is formed, so forming it does not count as reading every key
        env = {**run.base_env, "item": rec, "prod": cx.is_prod((item or {}).get("namespace")) if isinstance(item, dict) else False}
        run.emit(env, default_target, "summary.json:" + check["each"])
    return run.done()


def _eval_inventory(cx: Context, check: dict, run: _Run) -> dict:
    """Types `inventory` and `aws` share this handler: both read inventory.json (aws checks reach aws/ files through the aws_file helper)."""
    if check.get("each"):
        seq = _get_path(cx.inv, check["each"])
        if seq is None:
            return run.skip(f"inventory.{check['each']} missing")
        pairs = list(seq.items()) if isinstance(seq, dict) else [(None, x) for x in seq]
        for key, item in pairs:
            default_target = str(key if key is not None else item)[:60]
            rec = ItemRecorder(item) if isinstance(item, dict) else item
            run.emit({**run.base_env, "item": rec, "key": key, "prod": False}, default_target, "inventory.json:" + check["each"])
        return run.done()
    eks = (cx.inv.get("cluster") or {}).get("eks")
    if check["type"] == "inventory" and check["id"].startswith("eks."):
        if not eks:
            return run.skip("not EKS")
        if isinstance(eks, dict) and eks.get("error"):
            return run.skip(f"EKS facts not read (eks describe-cluster: {str(eks['error'])[:120]})")  # discover keeps name, region and the error only; a rule on those facts would judge nothing
    run.emit({**run.base_env, "prod": False}, "cluster", "inventory.json")
    return run.done()


# check type -> handler. All handlers share the signature (cx, check, run) -> result dict; adding a type is one function plus one row here.
HANDLERS: dict[str, Callable[[Context, dict, _Run], dict]] = {
    "signature": _eval_signature,
    "llm": _eval_llm,
    "absence": _eval_absence,
    "metric": _eval_metric,
    "object": _eval_object,
    "summary": _eval_summary,
    "inventory": _eval_inventory,
    "aws": _eval_inventory,
}


def evaluate_check(check: dict, cx: Context, thresholds: dict) -> dict:
    """Evaluate one check and return {status, counts, findings[], reason?}. Namespace profiles come from `cx.ns_profiles`."""
    handler = HANDLERS.get(check["type"])
    if handler is None:
        return _Run.skip(f"unknown type {check['type']}")
    return handler(cx, check, _Run(check, cx, thresholds))


def evaluate(snap: Path, cfg: Config, *, profile_override: str | None = None, tools_present: set[str] | None = None, echo=print) -> dict:
    inv = load_json(snap / "inventory.json") or {}
    summary = load_json(snap / "summary.json") or {}
    pname = profile_override or cfg.get("profile") or (inv.get("profile") or {}).get("name") or "prod"
    pname = rubric.PROFILE_ALIASES.get(pname, pname)  # snapshots taken before the rename still say "homelab"
    profile = rubric.load_profile(pname)
    collectors = inv.get("collectors_enabled") or ["core"]
    checks, errors = rubric.load_checks(collectors)
    ns_profiles = {pat: rubric.load_profile(str(name)) for pat, name in (cfg.get("namespace_profiles") or {}).items()}  # namespace-level profiles
    cx = Context(snap, inv, summary, profile, ns_profiles)
    mode = paths.snapshot_mode(
        snap
    )  # daily or full. A check marked `modes: [full]` needs inputs the daily run does not collect, so it is reported as not-collected instead of being evaluated on missing data (which would turn "file absent" into false absence findings)
    active_sup, expired_sup = rubric.active_suppressions(cfg.get("suppress"))
    overrides = cfg.get("overrides") or {}

    results: list[dict] = []
    findings: list[dict] = []
    suppressed: list[dict] = []
    known, known_errors = rubric.load_known_issues()
    errors = list(errors) + known_errors
    catalog = rubric.catalog_hash()
    for c in checks:
        rec = {
            "id": c["id"],
            "name": c["name"],
            "area": c["area"],
            "type": c["type"],
            "collector": c["collector"],
            "severity_default": c["severity_default"],
            "rule_hash": rubric.rule_hash(c, extra=catalog if c["type"] == "signature" else None),
        }
        if c["id"] in known:
            rec["known_issues"] = known[c["id"]]  # open defects of kubegap that affect this check; the finding carries them too, so a tool note cites the number instead of describing the defect again
        applies = pname in (c.get("profiles") or []) or (profile.get("base") in (c.get("profiles") or []))  # derived profiles (small-prod, multi-az-prod, dev) inherit the check set of their base profile
        if not applies or c["id"] in (profile.get("disabled_checks") or []):
            rec.update(status="disabled", reason=f"disabled in profile {pname}")
            results.append(rec)
            continue
        if c.get("modes") and mode not in c["modes"]:
            rec.update(status="not-collected", reason=f"inputs not collected in {mode} mode (collected by: {', '.join(c['modes'])})")
            results.append(rec)
            continue
        req_tool = c.get("requires_tool")
        if req_tool and tools_present is not None and req_tool not in tools_present:
            rec.update(status="tool-missing", reason=f"tool {req_tool} missing")
            results.append(rec)
            continue
        thresholds = rubric.resolve_thresholds(c, profile, overrides)
        try:
            r = evaluate_check(c, cx, thresholds)
        except Exception as e:  # A bug in one check must not stop the whole run. Recorded in the report appendix
            rec.update(status="error", reason=f"{type(e).__name__}: {e}")
            results.append(rec)
            continue
        rec.update(status=r["status"], counts=r.get("counts"), reason=r.get("reason"), thresholds=thresholds)
        if r.get("skipped_reason"):
            rec["skipped_reason"] = r["skipped_reason"]
        if r.get("gone_nodes"):
            rec["gone_nodes"] = r["gone_nodes"]  # node series the inventory no longer lists: left within the metric window, not judged
        for f in r["findings"]:
            f["thresholds"] = thresholds
            for k in ("why", "suggest", "verify", "cases", "measured", "notes"):
                f.setdefault(k, c.get(k))  # signature checks already carry the signature's description
            if c["id"] in known:
                f["known_issues"] = known[c["id"]]  # the evidence is left as the check wrote it; render appends "known issue #N" in its tables
            sup = next((s for s in active_sup if s.get("id") == c["id"] and (not s.get("namespaces") or f["target"].split("/")[0] in s["namespaces"])), None)
            if sup:
                f["status"] = "suppressed"
                f["suppressed_by"] = {"reason": sup.get("reason"), "until": sup.get("until")}
                suppressed.append(f)
            else:
                findings.append(f)
        results.append(rec)

    def counts_by(key, items):
        return dict(Counter(x[key] for x in items))

    out = {
        "kubegap": __version__,
        "rubric_version": paths.rubric_version(),
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "snapshot": str(snap),
        "mode": mode,
        "context": inv.get("context"),
        "profile": {"name": pname, "source": "override" if profile_override else (inv.get("profile") or {}).get("source"), "missing_file": profile.get("missing", False)},
        "checks": {"total": len(checks), "by_status": counts_by("status", results), "load_errors": errors},
        "severity_rules": rubric.load_severity_rules(),
        "findings": sorted(findings, key=lambda f: (["critical", "high", "medium", "low", "info"].index(f["severity_default"]), f["status"] != "fail", f["id"])),
        "findings_count": {
            "by_status": counts_by("status", findings),
            "by_severity_default": counts_by("severity_default", [f for f in findings if f["status"] == "fail"]),
            "warn_by_severity_default": counts_by("severity_default", [f for f in findings if f["status"] == "warn"]),
        },
        "suppressed": suppressed,
        "expired_suppressions": expired_sup,
        "llm_checks": [f for f in findings if f["status"] == "llm"],
        "check_results": results,
    }
    write_private(snap / "findings-draft.json", json.dumps(out, ensure_ascii=False, indent=1, default=str))
    if echo:
        bs = out["checks"]["by_status"]
        echo(
            f"profile {pname}, mode {mode}, {len(checks)} checks: evaluated {bs.get('done', 0)}, disabled {bs.get('disabled', 0)}, skipped {bs.get('skip', 0)}, not collected in this mode {bs.get('not-collected', 0)}, errors {bs.get('error', 0)}, tool missing {bs.get('tool-missing', 0)}"
        )
        if errors:
            echo("load errors: " + "; ".join(errors))
        fc = out["findings_count"]
        echo(f"findings: fail {fc['by_status'].get('fail', 0)} (severity {fc['by_severity_default']}), warn {fc['by_status'].get('warn', 0)}, suppressed {len(suppressed)}")
        for r in results:
            if r["status"] == "error":
                echo(f"  error {r['id']}: {r['reason']}")
        echo(f"saved: {snap / 'findings-draft.json'}")
    return out

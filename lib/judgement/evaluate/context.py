"""The Context: everything of the snapshot an expression may ask for (summary.json, inventory.json, objects, metrics, the owners of pods) and the helper functions it exposes to the rules.

Part of the evaluator (lib/judgement/evaluate).
"""

from __future__ import annotations

import datetime as _dt
import functools
import re
from pathlib import Path
from typing import ClassVar

from ...foundations import metricnames, rubric, versions
from ...foundations.snapshot import dump_record, load_json, metric_doc, missing_reason, object_file_status, series_present, taken_at
from ...foundations.snapshot import objects as snapshot_objects
from ...foundations.workload import is_db_like, mounts_pvc
from .evidence import oom_text, sg_text

SYMPTOM_METRIC_RE = re.compile(r"\b(http_|grpc_|nginx_ingress_controller_|traefik_|aws_applicationelb_|probe_|haproxy_|envoy_|istio_requests|sli:|slo:)")


def get_path(d, dotted: str):
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
        # The date the date-based checks (end of support, certificate expiry, suppress `until`) compare against: the snapshot date, so the same snapshot
        # gives the same verdicts later (#165). `inv["today"]` (YYYY-MM-DD) pins it instead; only the embedded test cases set it. A real inventory has no such key.
        self.today = _dt.date.fromisoformat(str(inv["today"])[:10]) if inv.get("today") else taken_at(inv).date()
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
        `labels['container']` by its name, image repository and owning workload, with lib.foundations.workload.is_db_like. Init containers count, since a native sidecar reports its own series.
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
            self._objects[file_stem] = snapshot_objects(self.snap, file_stem)
        return self._objects[file_stem]

    @functools.cached_property
    def dump_record(self) -> dict | None:
        return dump_record(self.snap)

    def missing_object_file(self, stem: str) -> str:
        """Skip reason for a check whose `objects/<stem>.json` is missing: says whether the cluster does not serve the kind, the ClusterRole denies it, or the name is wrong (#160)."""
        return missing_reason(stem, object_file_status(self.snap, stem, self.dump_record))

    def metric(self, qid: str) -> dict | None:
        return metric_doc(self.snap, qid)

    @functools.cached_property
    def series_present(self) -> dict[str, int] | None:
        """lib/foundations/snapshot.series_present, read once per run."""
        return series_present(self.snap)

    def names_without_series(self, qids: list[str]) -> list[str] | None:
        """Of the metric names the queries `qids` cite (lib/foundations/metricnames), those collection found no series of. Empty when every name has series; None when presence was not recorded."""
        present = self.series_present
        if present is None:
            return None
        return [n for qid in qids for n in metricnames.names_by_query().get(qid, []) if present.get(n) == 0]

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
        for c in self.objects("cronjobs"):
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
        """`versionStatus` of describe-cluster-versions (UNSUPPORTED / STANDARD_SUPPORT / EXTENDED_SUPPORT: awscli/botocore/data/eks/2017-11-01/service-2.json:2774,8206-8210@2.39.3).
        The sibling `status` is deprecated and spelled `extended-support` (:2770-2772,2798-2802), so the rule's value never matched it; `versionStatus` is the one read."""
        return self.eks_version_dates().get("versionStatus")

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

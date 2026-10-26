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

from . import __version__, paths, rubric
from .config import Config
from .snapshot import items, load_json

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
        self._addon_versions: dict[str, dict] = {}
        self._owners: dict[tuple[str, str], str] | None = None

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

    def k8s_eol(self, version: str | None):
        if not version:
            return None
        m = re.match(r"v?(\d+\.\d+)", version)
        if not m:
            return None
        eks = (self.inv.get("cluster") or {}).get("eks")
        if eks:
            cv = self.aws_file("describe-cluster-versions.json")
            for v in (cv or {}).get("clusterVersions") or []:
                if v.get("clusterVersion") == m.group(1) and v.get("endOfStandardSupportDate"):
                    return str(v["endOfStandardSupportDate"])[:10]
        for row in self._k8s_versions:
            if str(row.get("minor")) == m.group(1):
                return str(row.get("eol"))
        return None

    def eol_badge(self, version: str | None) -> str:
        """Human-readable end-of-support badge. Before EOL: 'D-30 (30 days left)'; after: 'D+119 (119 days past EOL)'."""
        eol = self.k8s_eol(version)
        d = self.days_until(eol)
        if eol is None or d is None:
            return "end of support unknown"
        return f"{eol} D-{d} ({d} days left)" if d >= 0 else f"{eol} D+{-d} ({-d} days past EOL)"

    def backup_signals(self) -> dict:
        """There may be backup activity even without a backup tool: k3s etcd snapshot objects, CronJobs named backup/dump/snapshot, VolumeSnapshots."""
        etcd = self.objects("etcdsnapshotfiles.k3s.cattle.io")
        cron = [f"{c['metadata']['namespace']}/{c['metadata']['name']}" for c in self.objects("cronjobs.batch") if re.search(r"backup|dump|snapshot|archive", c["metadata"]["name"], re.IGNORECASE)]
        vs = self.objects("volumesnapshots.snapshot.storage.k8s.io")
        return {"etcd_snapshots": len(etcd), "backup_cronjobs": cron, "volume_snapshots": len(vs), "any": bool(etcd or cron or vs)}

    def serves_traffic(self, obj: dict) -> bool:
        """Is this a target for readiness/preStop checks: replicas not 0, has a container port, and a Service points at it."""
        if (obj.get("spec") or {}).get("replicas") == 0:
            return False
        if not any((c.get("ports") or []) for c in self.containers(obj)):
            return False
        return self.has_service(obj)

    @staticmethod
    def days_until(date_str) -> int | None:
        if not date_str:
            return None
        try:
            d = _dt.date.fromisoformat(str(date_str)[:10])
        except ValueError:
            return None
        return (d - _dt.date.today()).days

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
        def parse(v):
            m = re.match(r"v?(\d+)\.(\d+)", v or "")
            return (int(m.group(1)), int(m.group(2))) if m else None

        a, b = parse(installed), parse(latest)
        if not a or not b:
            return 0
        return (b[0] - a[0]) * 100 + (b[1] - a[1])

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
            "inv": self.inv,
            "summary": self.summary,
            "ctx": {"profile": self.profile.get("name"), "platform": (self.inv.get("cluster") or {}).get("platform"), "prod_like": sorted(self.prod_like)},
        }


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

    def emit(self, env: dict, default_target: str, source: str) -> None:
        check, cx = self.check, self.cx
        st = _status(self.rule, env)
        target = str(_eval(check["target"], env)) if check.get("target") else default_target
        if _excluded(check["id"], target, cx.profile) or (cx.ns_profiles and _ns_profile_disables(check["id"], target, env, cx.ns_profiles)):
            self.counts["excluded"] += 1
            return
        self.counts[st] += 1
        if st not in ("fail", "warn"):
            return
        ev = _eval(check["evidence"], env) if check.get("evidence") else None
        if target in self._by_target:
            # When several pods of one workload (Job pods of a CronJob, replicas) map to the same target, merge their evidence into one finding
            f = self._by_target[target]
            f["instances"] = f.get("instances", 1) + 1
            if isinstance(f["evidence"], list):
                f["evidence"].append(ev)
            else:
                f["evidence"] = [f["evidence"], ev]
            if self._ORDER[st] < self._ORDER[f["status"]]:
                f["status"] = st
            return
        f = _finding(check, target, st, ev, source)
        self._by_target[target] = f
        self.findings.append(f)

    def done(self) -> dict:
        return {"status": "done", "counts": dict(self.counts), "findings": self.findings}

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
        f = _finding(check, sig["id"], st, ev, "summary.json:logs.signatures", {"signature": sig["id"], "component": sig["component"]})
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
            env = {**run.base_env, "value": value, "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
            default_target = _metric_target(cx, labels, "/".join(x for x in (labels.get("namespace"), labels.get("node") or labels.get("instance")) if x) or "cluster")
            if check.get("exclude_transient") and labels.get("pod") and cx.is_transient(labels):
                run.counts["excluded"] += 1
                continue
            run.emit(env, default_target, f"metrics/{inputs[0]}.json")
        return run.done()
    key = check.get("join_on") or "node"
    keys = list(key) if isinstance(key, list) else [key]  # join_on is one label or a list ([namespace, pod, container])
    primary = inputs[0]  # Series absent from the first input are not judged (secondary inputs only supply evidence numbers)
    joined: dict[tuple, dict] = {}
    for qid in inputs:
        m = cx.metric(qid)
        if not m or not m.get("ok"):
            if qid == primary:
                return run.skip(f"metrics/{qid}.json missing or failed")
            continue
        for s in m.get("result", []):
            lab = s.get("metric", {})
            k = tuple(lab.get(x) for x in keys)
            if any(x is None for x in k):
                continue
            with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
                joined.setdefault(k, {})[qid] = float(s["value"][1])
    for k, v in joined.items():
        if primary not in v:
            continue
        labels = dict(zip(keys, k, strict=False))
        env = {**run.base_env, "v": v, "value": v[primary], "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
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
        env = {**run.base_env, "item": item, "prod": cx.is_prod((item or {}).get("namespace")) if isinstance(item, dict) else False}
        run.emit(env, str(item)[:60], "summary.json:" + check["each"])
    return run.done()


def _eval_inventory(cx: Context, check: dict, run: _Run) -> dict:
    """Types `inventory` and `aws` share this handler: both read inventory.json (aws checks reach aws/ files through the aws_file helper)."""
    if check.get("each"):
        seq = _get_path(cx.inv, check["each"])
        if seq is None:
            return run.skip(f"inventory.{check['each']} missing")
        pairs = list(seq.items()) if isinstance(seq, dict) else [(None, x) for x in seq]
        for key, item in pairs:
            run.emit({**run.base_env, "item": item, "key": key, "prod": False}, str(key if key is not None else item)[:60], "inventory.json:" + check["each"])
        return run.done()
    if check["type"] == "inventory" and check["id"].startswith("eks.") and not (cx.inv.get("cluster") or {}).get("eks"):
        return run.skip("not EKS")
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
    for c in checks:
        rec = {"id": c["id"], "name": c["name"], "area": c["area"], "type": c["type"], "collector": c["collector"], "severity_default": c["severity_default"]}
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
        for f in r["findings"]:
            f["thresholds"] = thresholds
            for k in ("why", "suggest", "verify", "cases", "notes"):
                f.setdefault(k, c.get(k))  # signature checks already carry the signature's description
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
    (snap / "findings-draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
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

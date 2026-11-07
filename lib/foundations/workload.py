"""What a workload is, read from the objects alone: its name from a pod's name, its key in a summary, whether a container runs a data store,
whether a pod template mounts a PersistentVolumeClaim, whether a label selector matches, and which nodes a pod spec can land on (#150).

These were private helpers of lib/summaries/controlplane, lib/summaries/resilience, lib/summaries/security and lib/summaries/traffic that the other summary modules and lib/judgement/evaluate
imported from each other; they live here, below the summaries, so that no summary module imports a sibling (tests/test_boundaries.py).
Nothing here reads a file: every function takes the objects it judges.
"""

from __future__ import annotations

import re

# `name-<replicaset hash>-<pod hash>` (Deployment), `name-<job number>-<pod hash>` (CronJob), `name-<pod hash>` (DaemonSet, bare ReplicaSet). A StatefulSet pod (`name-0`) does not match and is returned as it is.
POD_HASH_RE = re.compile(r"^(.*?)-[0-9a-f]{5,10}-[0-9a-z]{5}$|^(.*?)-\d{6,}-[0-9a-z]{5}$|^(.*?)-[0-9a-z]{5}$")


def workload_of(pod_ref: str) -> str:
    """'ns/pod-6d7ff4dcdb-fphgn' -> 'ns/pod'. Name-shape guess used when owner information is unavailable."""
    ns, _, pod = pod_ref.partition("/")
    m = POD_HASH_RE.match(pod)
    base = next((g for g in (m.groups() if m else ()) if g), pod)
    return f"{ns}/{base}" if ns else base


def key(kind: str, o: dict) -> str:
    """`namespace/kind/name` of a workload object, the key the summary sections and the checks address a workload by."""
    return f"{o['metadata']['namespace']}/{kind.lower()}/{o['metadata']['name']}"


def image_repo(image: str | None) -> str:
    """`public.ecr.aws/bitnami/redis:7.2.3` -> `redis`. The tag is left out: umami:postgresql-latest was once caught as a DB."""
    return (image or "").split("@")[0].rsplit("/", 1)[-1].split(":")[0]


DB_HINT_RE = re.compile(
    r"(postgres|pgsql|mysql|mariadb|mongo|redis|valkey|elastic|opensearch|kafka|rabbit|clickhouse|qdrant|milvus|minio|etcd|cassandra|neo4j|influx|timescale"
    r"|prometheus|thanos|loki|mimir|cortex|tempo|victoria|zookeeper|nats|pulsar|solr|couch|cockroach|tidb|scylla|memcache|weaviate|meili|typesense|vault)",
    re.IGNORECASE,
)
# a whole name token that says the container is a helper next to a store, not the store itself; whole tokens so that quickstart does not trip ui or magento agent
NOT_DB_TOKENS = frozenset({"exporter", "operator", "controller", "proxy", "ui", "insight", "insights", "commander", "express", "dashboards", "dashboard", "agent", "connect", "backup", "telegraf", "console", "init", "sidecar"})
# a Helm release named after a monitoring store carries many pods that are not the store (kube-prometheus-stack-grafana, loki-stack-promtail, thanos-query): the workload name alone does not make those a store
MONITORING_RELEASE_RE = re.compile(r"(prometheus|thanos|loki|mimir|cortex|tempo|victoria)", re.IGNORECASE)


def _tokens(*names: str | None) -> set[str]:
    return {t for n in names if n for t in re.split(r"[^a-z0-9]+", n.lower()) if t}


def is_db_like(container: str | None, image: str | None, workload: str | None, *, stateful: bool = False) -> bool:
    """Does this container run a data store, whose rare peaks (a backup, a compaction, a recovery replay, a cache warm-up) sit far above its 7-day p95?
    Two signals say yes. Structural: `stateful`, the workload is a StatefulSet that mounts a PersistentVolumeClaim, which is how Kubernetes itself marks a store, whatever the image is called.
    By name: the container name or image repository, or else the workload name, carries a known store name. A helper next to the store is left out when its own name or image says so
    in a whole token: exporter, operator, controller, proxy, ui, insight, commander, express, dashboards, agent, connect, backup, telegraf, console, init, sidecar, metrics.
    Shared by the probe rows of lib/summaries/resilience and the request checks of lib/judgement/evaluate."""
    c, repo = container or "", image_repo(image)
    if _tokens(c, repo) & NOT_DB_TOKENS:
        return False  # the exporter next to a Redis, the MongoDB operator's agent, the init container of a Postgres
    if stateful:
        return True
    if DB_HINT_RE.search(f"{c} {repo}"):
        return True  # a container named kafka running a kafka image is the broker even when the StatefulSet is called kafka-controller, as Bitnami names its KRaft nodes
    wl = MONITORING_RELEASE_RE.sub("", workload or "")
    return bool(DB_HINT_RE.search(wl)) and not (_tokens(workload) & NOT_DB_TOKENS)


def mounts_pvc(spec: dict | None) -> bool:
    """Does a pod spec, or a workload's pod template, mount a PersistentVolumeClaim?"""
    return any(v.get("persistentVolumeClaim") for v in (spec or {}).get("volumes") or [])


def selector_matches(sel: dict | None, labels: dict) -> bool:
    """A label selector (`matchLabels`, `matchExpressions`, or a bare label map) against an object's labels. An empty selector matches nothing."""
    if not sel:
        return False
    ml = sel.get("matchLabels") if ("matchLabels" in sel or "matchExpressions" in sel) else sel
    if any(labels.get(k) != v for k, v in (ml or {}).items()):
        return False
    for e in sel.get("matchExpressions") or []:
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


def _expr_match(e: dict, labels: dict) -> bool:
    k, op, vals = e.get("key"), e.get("operator"), e.get("values") or []
    has = k in labels
    if op == "In":
        return has and labels[k] in vals
    if op == "NotIn":
        return not has or labels[k] not in vals
    if op == "Exists":
        return has
    if op == "DoesNotExist":
        return not has
    if op == "Gt":
        try:
            return has and float(labels[k]) > float(vals[0])
        except (ValueError, IndexError):
            return False
    if op == "Lt":
        try:
            return has and float(labels[k]) < float(vals[0])
        except (ValueError, IndexError):
            return False
    return True


def _field_match(f: dict, node: dict) -> bool:
    """`matchFields` of a node selector term: the only field key the scheduler supports is `metadata.name` (kubernetes/kubernetes
    staging/src/k8s.io/component-helpers/scheduling/corev1/nodeaffinity/nodeaffinity.go:159,180-182@v1.37.2), compared with the node's name, not its labels (#124 K1-5)."""
    if f.get("operator") != "In":
        return True
    value = node["metadata"].get("name") if f.get("key") == "metadata.name" else None
    return value in (f.get("values") or [])


def _tolerates(tolerations: list, taints: list) -> bool:
    for t in taints or []:
        if t.get("effect") not in ("NoSchedule", "NoExecute"):
            continue
        ok = False
        for tol in tolerations or []:
            if tol.get("effect") and tol["effect"] != t.get("effect"):
                continue
            if tol.get("operator") == "Exists":
                if not tol.get("key") or tol["key"] == t.get("key"):
                    ok = True
                    break
            elif tol.get("key") == t.get("key") and (tol.get("value") or "") == (t.get("value") or ""):
                ok = True
                break
        if not ok:
            return False
    return True


def eligible_nodes(pod_spec: dict, nodes: list[dict], *, ignore_node_name: bool = False) -> list[str]:
    """Node names this pod can land on, considering only nodeName, nodeSelector, required nodeAffinity and taints/tolerations (inter-pod affinity and resources excluded).
    A real pod spec carries the scheduler-filled nodeName, so pass ignore_node_name=True when computing from pods (only the template's nodeName is a constraint)."""
    out = []
    if pod_spec.get("nodeName") and not ignore_node_name:
        return [pod_spec["nodeName"]]
    sel = pod_spec.get("nodeSelector") or {}
    req = (((pod_spec.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []
    for n in nodes:
        if (n.get("spec") or {}).get("unschedulable"):
            continue
        labels = n["metadata"].get("labels") or {}
        if any(labels.get(k) != v for k, v in sel.items()):
            continue
        if req and not any(all(_expr_match(e, labels) for e in (t.get("matchExpressions") or [])) and all(_field_match(f, n) for f in (t.get("matchFields") or [])) for t in req):
            continue
        if not _tolerates(pod_spec.get("tolerations") or [], (n.get("spec") or {}).get("taints") or []):
            continue
        out.append(n["metadata"]["name"])
    return out

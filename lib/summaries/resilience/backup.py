"""Backup locality: whether a backup CronJob's output leaves the node disk its source lives on.

Part of the resilience section (lib/summaries/resilience): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ...foundations.snapshot import objects
from ...foundations.workload import image_repo, is_db_like
from ...foundations.workload import key as wl_key

BACKUP_NAME_RE = re.compile(r"(backup|dump|snapshot|archive|bak)", re.IGNORECASE)


# The stores whose data lives nowhere else and so need a dump: the DB_HINT_RE names minus the caches, queues, coordination services and monitoring stores
# (redis, valkey, memcache, kafka, rabbit, nats, pulsar, zookeeper, etcd, prometheus, thanos, loki, mimir, cortex, tempo, victoria, vault), whose data is
# rebuilt, re-ingested or backed up by other means, and minus minio, which is where dumps go (OFFSITE_RE) rather than what is dumped; those are listed as
# excluded so the reader sees them (#169).
BACKUP_TARGET_RE = re.compile(r"(postgres|pgsql|mysql|mariadb|mongo|elastic|opensearch|clickhouse|qdrant|milvus|cassandra|neo4j|influx|timescale|solr|couch|cockroach|tidb|scylla|weaviate|meili|typesense)", re.IGNORECASE)


OFFSITE_RE = re.compile(r"(s3://|s3\.|aws s3|rclone|restic|gs://|gsutil|b2 |backblaze|minio|mc cp|azcopy|rsync .*@|scp |sftp|wal-g|pgbackrest|borg|kopia)", re.IGNORECASE)


def pv_node(pv: dict) -> str | None:
    """The node a PV is pinned to: a required term with one `In` expression and one value. `kubernetes.io/hostname` is the key the local-path
    provisioner (rancher/local-path-provisioner provisioner.go:526-529@v0.0.37, overridable by the StorageClass parameter `nodeAffinityKey`, :540-542)
    and static local PVs write; any other single-value key is a pin too (#124 K1-6)."""
    for t in (((pv.get("spec") or {}).get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or []:
        exprs = [e for e in t.get("matchExpressions") or [] if e.get("operator", "In") == "In" and len(e.get("values") or []) == 1]
        for e in exprs:
            if e.get("key") == "kubernetes.io/hostname":
                return e["values"][0]
        if len(exprs) == 1 and len(t.get("matchExpressions") or []) == 1:
            return exprs[0]["values"][0]
    return None


def backup_locality(cx) -> dict:
    """Does the backup CronJob's output stay only on 'the same node disk as the source'? Inputs: jobTemplate volumes and commands of cronjobs.batch,
    PVC → PV nodeAffinity (local-path), PVC nodes of DB workloads in the same namespace. offsite_hint when a command that ships the dump via S3, rclone, restic etc. is visible."""
    pvc_node: dict[tuple, str | None] = {}
    pvc_pv: dict[tuple, str] = {}
    for pv in objects(cx.snap, "persistentvolumes"):
        cr = (pv.get("spec") or {}).get("claimRef") or {}
        if cr.get("name"):
            pvc_node[(cr.get("namespace"), cr["name"])] = pv_node(pv)
            pvc_pv[(cr.get("namespace"), cr["name"])] = pv["metadata"]["name"]
    services: dict[str, list[tuple[str, dict]]] = defaultdict(list)  # ns → [(service name, selector)]
    for s in cx.services:
        sel = (s.get("spec") or {}).get("selector")
        if sel:
            services[s["metadata"]["namespace"]].append((s["metadata"]["name"], sel))
    db_pvcs: dict[str, list[tuple]] = defaultdict(list)  # ns → [(workload, pvc, node)]
    databases: list[dict] = []  # one row per store that needs a dump (BACKUP_TARGET_RE) and mounts a PVC
    excluded: list[str] = []  # stores DB_HINT_RE names that are not dump targets (caches, queues, monitoring)
    for kind, o in cx.workloads:
        ns = o["metadata"]["namespace"]
        containers = cx.tpl(o).get("containers") or []
        name_and_repos = o["metadata"]["name"] + " " + " ".join(image_repo(c.get("image")) for c in containers)  # the repository, never the tag: umami:postgresql-latest is an app
        if not any(is_db_like(c.get("name"), c.get("image"), o["metadata"]["name"]) for c in containers):
            continue  # the shared gate: a Grafana whose release is called prometheus, an exporter or a sidecar next to a store is not a store
        claims = [v["persistentVolumeClaim"]["claimName"] for v in cx.tpl(o).get("volumes") or [] if v.get("persistentVolumeClaim")]
        for vct in (o.get("spec") or {}).get("volumeClaimTemplates") or []:
            for p in cx.pods_of(kind, o):
                for v in p["spec"].get("volumes") or []:
                    if v.get("persistentVolumeClaim") and v["persistentVolumeClaim"]["claimName"].startswith(vct["metadata"]["name"] + "-"):
                        claims.append(v["persistentVolumeClaim"]["claimName"])
        if not claims:
            continue
        for c in sorted(set(claims)):
            db_pvcs[ns].append((wl_key(kind, o), c, pvc_node.get((ns, c))))
        if not BACKUP_TARGET_RE.search(name_and_repos):
            excluded.append(wl_key(kind, o))
            continue
        labels = cx.tpl_labels(o)
        databases.append(
            {
                "namespace": ns,
                "kind": kind.lower(),
                "name": o["metadata"]["name"],
                "target": wl_key(kind, o),
                "prod": ns in cx.prod,
                "pvcs": sorted(set(claims)),
                "services": sorted(sn for sn, sel in services.get(ns, []) if all(labels.get(k) == v for k, v in sel.items())),
                "backup_cronjobs": [],
                "other_backup_cronjobs_in_namespace": [],
            }
        )
    rows = []
    for cj in objects(cx.snap, "cronjobs"):
        md, sp = cj["metadata"], cj.get("spec") or {}
        ns = md["namespace"]
        pod = (((sp.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
        cmd_text = " ".join(" ".join((c.get("command") or []) + (c.get("args") or [])) + " " + " ".join(str(e.get("value") or "") for e in c.get("env") or []) for c in (pod.get("containers") or []) + (pod.get("initContainers") or []))
        text = cmd_text + " " + " ".join(c.get("image", "") for c in (pod.get("containers") or []) + (pod.get("initContainers") or []))
        if not BACKUP_NAME_RE.search(md["name"] + " " + text[:400]):
            continue
        claims = [v["persistentVolumeClaim"]["claimName"] for v in pod.get("volumes") or [] if v.get("persistentVolumeClaim")]
        host_paths = [v["hostPath"].get("path") for v in pod.get("volumes") or [] if v.get("hostPath")]
        dest_nodes = {pvc_node.get((ns, c)) for c in claims}
        offsite = bool(OFFSITE_RE.search(text))
        src = db_pvcs.get(ns, [])
        src_nodes = {n for _, _, n in src if n}
        same_node = bool(dest_nodes & src_nodes) or (bool(host_paths) and bool(pod.get("nodeSelector") or pod.get("nodeName")))
        # Which database this CronJob dumps: its command, args or env values name the database's Service (the host of pg_dump -h, mysqldump -h, a connection
        # string), the workload itself, or its first pod (<statefulset>-0), as a whole token. A name that is only the prefix of another (app-postgres of
        # app-postgres-mx) does not match (#169). The image is not part of the match (a CronJob running the postgres image would claim a database named
        # postgres), and a user name that equals a sibling's name would (pg_dump -U postgres): the known limit of a token match. The text is not recorded: an env
        # value may be a credential.
        targets_db = []
        for db in databases:
            if db["namespace"] != ns:
                continue
            keys = [*db["services"], db["name"]] + ([f"{db['name']}-0"] if db["kind"] == "statefulset" else [])
            hit = next((k for k in keys if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", cmd_text)), None)  # a dot may precede: pg-0.pg-headless names the Service
            if hit:
                targets_db.append({"target": db["target"], "matched_by": hit})
                if not sp.get("suspend"):
                    db["backup_cronjobs"].append({"name": md["name"], "matched_by": hit})
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "prod": ns in cx.prod,
                "schedule": sp.get("schedule"),
                "suspend": bool(sp.get("suspend")),
                "targets_db": targets_db,
                "dest_pvcs": claims,
                "dest_nodes": sorted(n for n in dest_nodes if n),
                "host_paths": host_paths,
                "offsite_hint": offsite,
                "source_db": [{"workload": w, "pvc": c, "node": n} for w, c, n in src][:6],
                "source_nodes": sorted(src_nodes),
                "same_node_as_source": same_node,
                "local_only": not offsite and (bool(claims) or bool(host_paths)),
                "note": "offsite_hint = whether command, args or env values contain strings such as s3, rclone or restic (names only, values are not recorded)",
            }
        )
    for db in databases:
        own = {b["name"] for b in db["backup_cronjobs"]}
        db["other_backup_cronjobs_in_namespace"] = [{"name": r["name"], "suspend": r["suspend"], "targets_db": [t["target"] for t in r["targets_db"]]} for r in rows if r["namespace"] == db["namespace"] and r["name"] not in own]
    return {
        "rows": rows,
        "count": len(rows),
        "local_only": [r["target"] for r in rows if r["local_only"]],
        "same_node": [r["target"] for r in rows if r["same_node_as_source"]],
        "databases": databases,
        "excluded_stores": sorted(excluded),
        "note": "databases: every store that needs a dump (BACKUP_TARGET_RE) with a PVC, and the backup CronJobs whose command, args or env name its Service, its workload or its first pod; excluded_stores: caches, queues, monitoring stores and MinIO with a PVC, which this check does not ask a dump of",
    }

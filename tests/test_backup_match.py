"""A backup CronJob counts for the database it names, not for every database in its namespace (#169)."""

from __future__ import annotations

import json
from pathlib import Path

from lib.summaries import resilience

INV = {"cluster": {"platform": "k3s"}, "namespaces": {"prod_like": ["prod-a", "prod-b"]}, "scale": {"name": "small", "source": "guessed"}, "nodes": {"nodes": []}}


def _sts(ns, name, image, labels=None):
    labels = labels or {"app": name}
    return {
        "kind": "StatefulSet",
        "metadata": {"namespace": ns, "name": name, "uid": f"uid-{ns}-{name}"},
        "spec": {"replicas": 1, "selector": {"matchLabels": labels}, "template": {"metadata": {"labels": labels}, "spec": {"containers": [{"name": "db", "image": image}]}}, "volumeClaimTemplates": [{"metadata": {"name": "data"}}]},
    }


def _pod(ns, sts):
    return {
        "kind": "Pod",
        "metadata": {"namespace": ns, "name": f"{sts}-0", "ownerReferences": [{"kind": "StatefulSet", "name": sts}]},
        "spec": {"volumes": [{"name": "data", "persistentVolumeClaim": {"claimName": f"data-{sts}-0"}}], "containers": [{"name": "db"}]},
        "status": {"phase": "Running"},
    }


def _svc(ns, name, selector):
    return {"kind": "Service", "metadata": {"namespace": ns, "name": name}, "spec": {"selector": selector}}


def _cronjob(ns, name, command, env=None, suspend=False):
    return {
        "kind": "CronJob",
        "metadata": {"namespace": ns, "name": name},
        "spec": {
            "schedule": "0 3 * * *",
            "suspend": suspend,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {"containers": [{"name": "dump", "image": "postgres:16", "command": ["/bin/sh", "-c", command], "env": env or []}], "volumes": [{"name": "out", "persistentVolumeClaim": {"claimName": f"{name}-pvc"}}]}
                    }
                }
            },
        },
    }


def _snap(tmp_path: Path, statefulsets, pods, services, cronjobs, deployments=()):
    (tmp_path / "objects").mkdir()
    for stem, items in (
        ("statefulsets", statefulsets),
        ("pods", pods),
        ("services", services),
        ("cronjobs", cronjobs),
        ("deployments", list(deployments)),
        ("persistentvolumes", []),
        ("jobs.batch", []),
        ("replicasets.apps", []),
        ("daemonsets", []),
        ("poddisruptionbudgets.policy", []),
        ("horizontalpodautoscalers.autoscaling", []),
        ("nodes", []),
        ("endpoints", []),
    ):
        (tmp_path / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}))
    (tmp_path / "inventory.json").write_text(json.dumps(INV))
    return tmp_path


def _backup(tmp_path, **kw):
    return resilience.analyze(_snap(tmp_path, **kw), INV)["backup"]


def test_a_cronjob_counts_for_the_database_whose_service_it_names_and_not_for_its_neighbour(tmp_path):
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "mysql", "mysql:8.0"), _sts("prod-a", "qdrant", "qdrant/qdrant:v1.9.2")],
        pods=[_pod("prod-a", "mysql"), _pod("prod-a", "qdrant")],
        services=[_svc("prod-a", "mysql", {"app": "mysql"}), _svc("prod-a", "qdrant", {"app": "qdrant"})],
        cronjobs=[_cronjob("prod-a", "mysql-backup", 'mysqldump -h mysql -u root -p"$P" db | gzip > /backup/x.sql.gz')],
    )
    dbs = {d["name"]: d for d in b["databases"]}
    assert dbs["mysql"]["backup_cronjobs"] == [{"name": "mysql-backup", "matched_by": "mysql"}] and dbs["mysql"]["other_backup_cronjobs_in_namespace"] == []
    assert dbs["qdrant"]["backup_cronjobs"] == [] and dbs["qdrant"]["other_backup_cronjobs_in_namespace"] == [{"name": "mysql-backup", "suspend": False, "targets_db": ["prod-a/statefulset/mysql"]}]
    assert [d["target"] for d in b["databases"] if d["prod"] and not d["backup_cronjobs"]] == ["prod-a/statefulset/qdrant"]
    assert b["rows"][0]["targets_db"] == [{"target": "prod-a/statefulset/mysql", "matched_by": "mysql"}]


def test_a_service_name_that_is_a_prefix_of_another_does_not_match_it(tmp_path):
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "pg", "postgres:16"), _sts("prod-a", "pg-mx", "postgres:16")],
        pods=[_pod("prod-a", "pg"), _pod("prod-a", "pg-mx")],
        services=[_svc("prod-a", "pg", {"app": "pg"}), _svc("prod-a", "pg-mx", {"app": "pg-mx"})],
        cronjobs=[_cronjob("prod-a", "pg-backup", "pg_dump -h pg.prod-a.svc.cluster.local -U u -d d"), _cronjob("prod-a", "pg-mx-backup", "pg_dump -h pg-mx.prod-a.svc.cluster.local -U u -d d")],
    )
    dbs = {d["name"]: d for d in b["databases"]}
    assert [c["name"] for c in dbs["pg"]["backup_cronjobs"]] == ["pg-backup"] and [c["name"] for c in dbs["pg-mx"]["backup_cronjobs"]] == ["pg-mx-backup"]
    assert all(d["backup_cronjobs"] for d in b["databases"])


def test_a_cronjob_running_the_postgres_image_does_not_claim_a_database_named_postgres(tmp_path):
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "postgres", "postgres:16"), _sts("prod-a", "postgres-mx", "postgres:16")],
        pods=[_pod("prod-a", "postgres"), _pod("prod-a", "postgres-mx")],
        services=[_svc("prod-a", "postgres", {"app": "postgres"}), _svc("prod-a", "postgres-mx", {"app": "postgres-mx"})],
        cronjobs=[_cronjob("prod-a", "mx-backup", "pg_dump -h postgres-mx -U admin -d d")],  # the CronJob image is postgres:16: not a match for the database called postgres
    )
    dbs = {d["name"]: d for d in b["databases"]}
    assert dbs["postgres"]["backup_cronjobs"] == [] and [c["name"] for c in dbs["postgres-mx"]["backup_cronjobs"]] == ["mx-backup"]


def test_the_first_pod_and_the_workload_name_match_too_and_a_suspended_cronjob_does_not_count(tmp_path):
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "pg", "postgres:16"), _sts("prod-b", "mongo", "mongo:7")],
        pods=[_pod("prod-a", "pg"), _pod("prod-b", "mongo")],
        services=[_svc("prod-a", "pg-headless", {"app": "pg"}), _svc("prod-b", "mongo", {"app": "mongo"})],
        cronjobs=[_cronjob("prod-a", "nightly-dump", "pg_dump -h pg-0.pg-headless -U u"), _cronjob("prod-b", "mongo-backup", "mongodump --host mongo", suspend=True)],
    )
    dbs = {d["name"]: d for d in b["databases"]}
    assert dbs["pg"]["backup_cronjobs"][0]["matched_by"] == "pg-headless"
    assert dbs["mongo"]["backup_cronjobs"] == [] and b["rows"][1]["targets_db"] == [{"target": "prod-b/statefulset/mongo", "matched_by": "mongo"}]
    assert dbs["mongo"]["other_backup_cronjobs_in_namespace"] == [{"name": "mongo-backup", "suspend": True, "targets_db": ["prod-b/statefulset/mongo"]}]  # the evidence says "(suspended)"


def test_an_env_value_names_the_host_and_the_text_is_not_recorded(tmp_path):
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "pg", "postgres:16")],
        pods=[_pod("prod-a", "pg")],
        services=[_svc("prod-a", "pg", {"app": "pg"})],
        cronjobs=[_cronjob("prod-a", "backup", "pg_dump -h $PGHOST", env=[{"name": "PGHOST", "value": "pg"}, {"name": "PGPASSWORD", "value": "hunter2-not-for-the-summary"}])],
    )
    assert b["databases"][0]["backup_cronjobs"] == [{"name": "backup", "matched_by": "pg"}]
    assert "hunter2" not in json.dumps(b)


def test_caches_are_excluded_and_an_image_tag_is_not_a_store(tmp_path):
    umami = {
        "kind": "Deployment",
        "metadata": {"namespace": "prod-a", "name": "umami"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "umami"}},
            "template": {
                "metadata": {"labels": {"app": "umami"}},
                "spec": {"containers": [{"name": "umami", "image": "ghcr.io/umami-software/umami:postgresql-latest"}], "volumes": [{"name": "d", "persistentVolumeClaim": {"claimName": "umami-data"}}]},
            },
        },
    }
    b = _backup(
        tmp_path,
        statefulsets=[_sts("prod-a", "redis", "redis:7-alpine"), _sts("prod-a", "pg", "postgres:16")],
        pods=[_pod("prod-a", "redis"), _pod("prod-a", "pg")],
        services=[_svc("prod-a", "redis", {"app": "redis"}), _svc("prod-a", "pg", {"app": "pg"})],
        cronjobs=[],
        deployments=[umami],
    )
    assert [d["target"] for d in b["databases"]] == ["prod-a/statefulset/pg"]
    assert b["excluded_stores"] == ["prod-a/statefulset/redis"]
    assert [d["target"] for d in b["databases"] if d["prod"] and not d["backup_cronjobs"]] == ["prod-a/statefulset/pg"]


def test_a_grafana_in_a_release_called_prometheus_and_a_minio_are_not_dump_targets(tmp_path):
    grafana = {
        "kind": "Deployment",
        "metadata": {"namespace": "monitoring", "name": "kube-prometheus-stack-grafana"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "grafana"}},
            "template": {
                "metadata": {"labels": {"app": "grafana"}},
                "spec": {
                    "containers": [{"name": "grafana-sc-dashboard", "image": "quay.io/kiwigrid/k8s-sidecar:1.30.10"}, {"name": "grafana", "image": "grafana/grafana:12.2.1"}],
                    "volumes": [{"name": "d", "persistentVolumeClaim": {"claimName": "grafana"}}],
                },
            },
        },
    }
    b = _backup(tmp_path, statefulsets=[_sts("prod-a", "minio", "minio/minio:RELEASE.2025-04-22T22-12-26Z")], pods=[_pod("prod-a", "minio")], services=[_svc("prod-a", "minio", {"app": "minio"})], cronjobs=[], deployments=[grafana])
    assert b["databases"] == [] and b["excluded_stores"] == ["prod-a/statefulset/minio"]

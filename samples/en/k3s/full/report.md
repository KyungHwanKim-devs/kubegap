# default — full audit, 2026-11-15 01:02

Broken now: none

The 5 largest problems: ① Database backups never leave the node they are written on ② Prometheus keeps 30 days of metrics on an emptyDir volume ③ Nine Argo CD applications would delete a whole Namespace if its manifest went missing ④ Kubernetes 1.33 is past its end of support ⑤ Some alert notifications fail to reach Discord

What already happened: Tempo was killed for memory and its pod restarted up to 163 times · Prometheus restarted and repaired a corrupted write-ahead log

Scale: small

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 2 of 2 Ready |
| Pods | 107 running, 0 pending, 3 failed |
| Namespaces | 28, 8 production |
| Components | 26: actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, istio, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, opentelemetry-collector, prometheus, prometheus-operator, reloader, tempo-jaeger |
| Metrics and log stores | prometheus 3.7.3 / no Loki |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## What already happened

There is no earlier run to compare with, so this covers only what this run collected.

### Tempo was killed for memory and its pod restarted up to 163 times

During the last seven days the tracing store `monitoring/tempo` was ended by the kernel for exceeding its memory limit, and the pod that ended that way counted 163 restarts before it was replaced. The pod running now, `tempo-0`, was created on 2026-11-12 at 16:12 UTC and has restarted once since, so the repeated restarts appear to be over. Whether traces were lost while it restarted cannot be told from this audit. In the same week one pod of `app-ac-prod/app-ac-ai` was also ended by an OOM kill once and has been replaced; its new pod has not restarted.

Why Tempo needed more memory than its limit is not known. The count comes from kube-state-metrics in Prometheus, which records how the old pods ended; the Tempo log, which would say what it was doing, lives in Elasticsearch and was not read. The restart count is an upper bound, because a failing probe restarts a container too.

This did not expose one of the five problems below.

### Prometheus restarted and repaired a corrupted write-ahead log

Prometheus started again on 2026-11-14 at 01:13 UTC, and a minute later, at 01:14:32, it logged "Encountered WAL read error, attempting repair" followed by "Starting corruption repair" for segment 8483. The write-ahead log is the file on disk that protects the newest two hours of samples against a crash. Prometheus has served normally since, its configuration reloaded successfully and no further corruption was logged, so this is over. The samples in the damaged part of that segment were dropped by the repair.

Why the log was damaged is not confirmed. Prometheus had not been killed for memory, so the likely cause is an abrupt stop of the process or its node; the audit has no node access to tell which.

This exposed problem 2, Prometheus keeps 30 days of metrics on an emptyDir volume.

## 1. Database backups never leave the node they are written on

**Why this one.** If both nodes lose their disks, or something with cluster rights deletes the volumes, the databases and their only dumps go together, and the data cannot be brought back.

### What is the matter

There is no backup tool in this cluster, such as Velero, that copies objects and volumes somewhere else. What exists instead are eight CronJobs that run every night between 02:50 and 03:50 and every twelve hours for etcd: `app-a-prod/app-a-postgres-backup`, `app-f-prod/app-f-postgres-backup`, `app-f-prod/app-f-postgres-mx-backup`, `app-f-prod/app-f-postgres-vn-backup`, `app-g-api/app-g-postgres-backup`, `app-h-prod/app-h-mysql-backup`, `kube-system/etcd-snapshot-backup` and `app-i-prod/app-i-postgres-backup`. All eight ran within the last seven days, which is good: the dumps are being made.

All eight write their output to a local-path PersistentVolume bound to the node `node-a`, and none of their commands, arguments or environment values mention a tool that copies anything further, such as `s3`, `rclone` or `restic`. The source databases run on the other node, `node-b`, so a disk failure on one node alone leaves either the database or its dump. A failure of both nodes, a deletion of the namespaces or the volumes with cluster rights, or a loss of the site where the two machines stand takes every copy at once. That last kind of event is what a backup is for.

Eight of the 15 databases found have no dump job at all: `app-k/app-k-postgres`, `app-l-prod/app-l-postgres`, `app-c-prod/app-c-postgres`, `app-h-prod/app-h-qdrant`, `logging/elasticsearch` and the three stores of `app-ac-prod` (`app-ac-neo4j`, `app-ac-opensearch`, `app-ac-postgres`). The k3s server also keeps its own five etcd snapshots on the server disk. Whether any dump has ever been restored cannot be told from this audit.

### Why it comes about

The dumps were set up where it was easiest: a CronJob, a PersistentVolumeClaim on the default local-path StorageClass, and a schedule. That solves "I deleted a table by mistake" and nothing larger. This is inferred from the volume and command of each job; no step of any job sends the file onward.

What a backup protects against is decided by where the copy lives, not by how often it is made. A copy on the same disk as the source only helps against a mistake inside the database. A copy on another node of the same cluster survives a node failure, but not what reaches the whole cluster: a script or a person with cluster rights deleting volumes, a namespace removed with everything in it, or a fire or theft where the machines are. The 3-2-1 rule names the answer: three copies, on two kinds of media, one of them off site.

Volumes from local-path-provisioner make this sharper. Such a volume is a directory on one node: the PersistentVolume carries a node affinity for that host, the size in the claim is not enforced, and the directory is removed when the volume is deleted. There is no storage system behind it that could keep a snapshot elsewhere, so the copy out has to be built.

The cluster state has the same question. k3s takes an etcd snapshot twice a day and keeps five on the server, and each snapshot is encrypted with a key derived from the server token. Restoring it on a new machine needs that token, so a snapshot kept without the token restores nothing. And for every kind of backup, one that has never been restored is not known to work: a file that appears every night says the job ran, not that a database comes up from it.

[GitLab](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/) lost the production database directory to a mistaken command in 2017. Its nightly pg_dump backups had been failing for some time because of a version mismatch, the failure mails were rejected, and the S3 bucket was empty; the data came back from a manual LVM snapshot six hours old. As here, backups were configured and believed to exist, and no one had restored one.

At [InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/) a name collision in the Argo CD configuration made Argo CD delete a whole production environment. The volumes had the reclaim policy Retain, so the data stayed. In this cluster the dump jobs are declared through Argo CD and their volumes are inside the same cluster, so a deletion with cluster rights would reach them too.

### How to watch it

The first thing to watch is whether each dump job still succeeds. kube-state-metrics exports the time of the last successful run of every CronJob, and a rule on its age fires when a job has not succeeded for longer than its schedule allows. This cluster does fire the generic `KubeJobFailed` alert, but the audit did not find a rule on backup age; one would have to be made.

```yaml
- alert: BackupCronJobStale
  expr: time() - kube_cronjob_status_last_successful_time{cronjob=~".*backup.*"} > 86400 * 1.5
  for: 30m
```

Once a copy job exists, the same series for that job shows whether the copy left the cluster. Whether a copy restores is not shown by any metric: it is seen by restoring one dump into an empty database now and then and comparing a few row counts, and for k3s by restoring a snapshot on a spare machine with the server token.

### How it is solved

At the scale this cluster is run at, keep the eight dump jobs as they are and add one step that sends their output to object storage outside the cluster. A CronJob that mounts the dump volume read-only and uploads it with restic or rclone to an S3-compatible bucket is enough. restic encrypts before it uploads, keeps versions and deduplicates; its repository password and the bucket credential live in a Secret, and losing the repository password loses the backups, so keep a copy of it outside the cluster. For k3s, turn on the S3 options of the etcd snapshot so that every snapshot is uploaded too, and keep the server token outside the cluster. The databases without a dump job need one first. The example shows the shape of such a container, not a manifest to apply as it is.

```yaml
containers:
  - name: offsite
    image: restic/restic
    args: ["backup", "/dumps"]
    envFrom:
      - secretRef: { name: offsite-backup }
    volumeMounts:
      - { name: dumps, mountPath: /dumps, readOnly: true }
```

The jobs are declared in the repository `example-org/k8s-manifests` on GitHub, managed by Argo CD with selfHeal on, so a job created or changed by hand in the cluster is reverted. The paths are `prod/app-a-prod`, `prod/app-f-kr`, `prod/app-f-mx`, `prod/app-f-vn`, `prod/app-g-api`, `prod/app-h`, `prod/app-i` and `infra/etcd-snapshot-backup`.

What to be careful of when applying it: the dump volumes are local-path volumes bound to `node-a`, so a copy job that mounts them is scheduled onto `node-a` as well, and it has to run after the dump of the same night has finished.

At a larger scale, Velero backs up objects and volumes together on a schedule to object storage in another account, and restores are practised into a scratch cluster on a calendar.

### Evidence

| What | Value | Source |
|---|---|---|
| Backup tool installed | none | `inventory.missing_families` |
| Backup CronJobs | 8 | `resilience.backup.rows` |
| Of them writing only to a local volume | 8 | `resilience.backup.local_only` |
| Node holding the dump volumes | node-a | `resilience.backup.rows` |
| Node holding the source databases | node-b | `resilience.backup.rows` |
| etcd snapshots kept on the server | 5 | finding `resilience.no-backup.cluster` |
| Databases found | 15 |
| Of them without a dump job | 8 | `resilience.backup.databases` |

### Further reading

- [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/): how believing a backup exists differs from restoring one.
- [k3s: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot): the S3 options and the restore procedure, including the token it needs.
- [restic: Preparing a new repository](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html): the storage back ends restic writes to and how the repository password works.
- [Velero: How Velero Works](https://velero.io/docs/main/how-velero-works/): what a backup, a schedule and a restore do, and what a restore leaves alone.

## 2. Prometheus keeps 30 days of metrics on an emptyDir volume

**Why this one.** The moment the Prometheus pod leaves its node, all 30 days of metrics are gone for good, and every dashboard and every comparison over time starts from empty.

### What is the matter

The single Prometheus of this cluster, `monitoring/prometheus-kube-prometheus-stack-prometheus`, writes its database to the volume `prometheus-kube-prometheus-stack-prometheus-db`, which is an `emptyDir`. The database holds 22.3GiB, the retention is 30 days by time with no size limit (`retentionSize` 0B), and the oldest sample is 31.2 days old, so the full window is there today. It has 174,075 active series and runs at 75% of its 1536Mi memory limit.

An `emptyDir` lives as long as the pod lives on that node. A restart of the container keeps it, which is why the restart of 2026-11-14 kept the 30 days and lost only what the write-ahead log repair dropped; that incident is described above under the title Prometheus restarted and repaired a corrupted write-ahead log. A move of the pod to another node, a node replacement or a delete of the pod does not keep it. The pod is pinned to nodes labelled `role=observability`, so it does not move often, but a drain of that node is enough.

Compactions have not failed in the last seven days, so the disk is not full now. Nothing limits how large the database may grow except the free space of the node filesystem, which this audit already sees as high in use on one node.

### Why it comes about

The kube-prometheus-stack chart creates Prometheus with an `emptyDir` unless `storageSpec` is set in its values, and the StatefulSet has no volume claim template, so it is not set here. The values themselves were not read.

Prometheus keeps the newest data in memory. Incoming samples go into the head block, which covers about two hours and lives in memory; a write-ahead log on disk, in 128MB segments, protects the head against a crash. Every two hours the head is written out as a block, and blocks are compacted in the background into longer ones. Memory therefore follows the number of active series, while disk follows the series and the retention.

Retention is 15 days by time by default, and the size limit is off by default. With only a time limit nothing stops the blocks from outgrowing the volume when the number of series grows; with a full disk compaction fails and in the end writes stop. When both limits are set the first one reached wins, and the Prometheus documentation advises a size limit of at most 80 to 85% of the disk, because a compaction briefly needs more.

Local storage in Prometheus is not replicated: it is a single-node database and has to be treated like one. On an `emptyDir` that database has the life of the pod placement. Kubernetes deletes an `emptyDir` permanently when the pod is removed from its node.

The UK Ministry of Justice lost monitoring on its live cluster for close to two hours in [2023](https://runbooks.cloud-platform.service.justice.gov.uk/incidents/2023-07-25-prometheus-on-live-cluster-down.html), when Prometheus kept being OOM killed as the number of namespaces and rules grew; an external Pingdom check raised the page. In [2024](https://runbooks.cloud-platform.service.justice.gov.uk/incidents/2024-04-15-prometheus.html) its Prometheus restarted after a planned change and the write-ahead log replay took longer than the startup probe allowed, so monitoring was lost for over three hours. In both the restart was the dangerous moment, as it was on 2026-11-14 here. [Saifeddine Rajhi](https://seifrajhi.github.io/blog/prometheus-manage-memory-overload/) describes a Prometheus that ran at about 30Gi and needed over 50Gi while replaying its log during a chart upgrade, so it could not come back; this Prometheus at 75% of its limit has less room for a replay than it seems.

### How to watch it

Once the database is on a volume claim, the kubelet exports used and capacity bytes per claim, and the Prometheus mixin ships `PrometheusTSDBCompactionsFailing`. This cluster has `PrometheusTSDBCompactionsFailing`; a rule on the claim filling up has to be made after the claim exists.

```yaml
- alert: PrometheusVolumeFillingUp
  expr: |
    kubelet_volume_stats_used_bytes{persistentvolumeclaim=~"prometheus-.*"}
      / kubelet_volume_stats_capacity_bytes{persistentvolumeclaim=~"prometheus-.*"} > 0.8
```

Memory against the limit is the second signal, with the threshold well below the limit because a restart needs more. `prometheus_tsdb_head_series` shows a step up after a deployment that adds a high-cardinality metric. A Prometheus that is down evaluates no rules, so only a check from outside the cluster can report that.

### How it is solved

At the scale this cluster is run at, keep one Prometheus and size it on purpose: give it a persistent volume through `prometheus.prometheusSpec.storageSpec`, set `retentionSize` to 80 to 85% of that volume next to `retention`, and set the memory limit with room for a restart. Accept a gap in the metrics whenever it restarts. The values below show the shape; the sizes are to be taken from the 22.3GiB this database already holds, so a 20Gi volume would be too small for 30 days.

```yaml
prometheus:
  prometheusSpec:
    retention: 30d
    retentionSize: "34GiB"
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 40Gi
```

Prometheus is installed by the Helm release `kube-prometheus-stack` (chart version 79.5.0 from the prometheus-community chart repository), managed by the Argo CD application `monitoring` with selfHeal on. A change made in the cluster is reverted, so change the values where that application declares them.

What to be careful of when applying it: adding a volume claim template changes the pod's volumes, so the pod is recreated, and the new pod starts on an empty volume. The 30 days held in the `emptyDir` today are lost at that moment unless they are copied first. The volume will come from the local-path StorageClass, which pins it to the node it is created on and does not enforce its size, so the retention size limit is what really bounds it. The pod is pinned to `node-b`, where the databases also keep their volumes, so a 40Gi volume shares the free space of that root filesystem with them; check that space before choosing the size. The pod has `terminationGracePeriodSeconds` of 600, so the old pod may take up to ten minutes to stop.

At a larger scale, two Prometheus instances scrape the same targets behind a query layer such as Thanos, or a managed Prometheus service takes the storage out of the cluster.

### Evidence

| What | Value | Source |
|---|---|---|
| Storage of the database | emptyDir | `stackhealth.prometheus.storage` |
| Size on disk | 22.3GiB | `stackhealth.prometheus.tsdb_bytes` |
| Retention by time | 30d | `stackhealth.prometheus.retention_time` |
| Retention by size | 0B | `stackhealth.prometheus.retention_size` |
| Oldest sample | 31.2 days | `stackhealth.prometheus.oldest_sample_days` |
| Active series | 174,075 | `stackhealth.prometheus.head_series` |
| Memory in use against limit | 0.752 of 1536Mi | `stackhealth.prometheus.rss_vs_limit` |
| Write-ahead log corruptions | 1 | `stackhealth.prometheus.wal_corruptions` |
| Failed compactions, 7 days | 0 | `stackhealth.prometheus.compactions_failed_7d` |
| Node selector | role=observability | object `statefulset monitoring/prometheus-kube-prometheus-stack-prometheus` |

### Further reading

- [Prometheus: Storage](https://prometheus.io/docs/prometheus/latest/storage/): blocks, the write-ahead log, compaction, both retention limits and the formula for sizing the disk.
- [Prometheus Operator: Storage](https://prometheus-operator.dev/docs/platform/storage/): how to give Prometheus a volume claim and what resizing one involves.
- [Robust Perception: How much RAM does Prometheus 2.x need for cardinality and ingestion?](https://www.robustperception.io/how-much-ram-does-prometheus-2-x-need-for-cardinality-and-ingestion/): where the memory goes per series, to estimate a limit from the number of head series.
- [Saifeddine Rajhi: Prometheus memory overload](https://seifrajhi.github.io/blog/prometheus-manage-memory-overload/): a walk through a Prometheus that could not restart, and how to find the metrics responsible.

## 3. Nine Argo CD applications would delete a whole Namespace if its manifest went missing

**Why this one.** One moved directory or renamed file in the manifest repository would make Argo CD delete a Namespace with every Deployment, Secret and PersistentVolumeClaim in it, and on local-path volumes the data goes with the claim.

### What is the matter

Nine Argo CD applications have automated sync with `prune` on and track a Namespace or a CustomResourceDefinition as one of their own resources: `app-a-prod`, `app-b-prod`, `app-d`, `app-g-api`, `app-ac-prod`, `istio`, `app-k`, `app-n` and `app-l-prod`. Namespaces that Argo CD creates through the `CreateNamespace` option are not counted here, because those are not tracked.

Several of these applications hold databases: `app-a-prod` and `app-g-api` run PostgreSQL with their only dumps on local volumes (problem 1), and `app-ac-prod` runs PostgreSQL, Neo4j and OpenSearch with no dump at all. `istio` is the one most likely to own CRDs. Which of the nine tracks a Namespace and which a CRD is not split out by this audit.

Nothing has gone wrong. This is a state that turns a small mistake in Git into a deletion.

### Why it comes about

The manifests were most likely written with a `Namespace` object at the top of each application directory, which is the natural way to make a directory self-contained, and the applications were set to prune so that removed resources do not linger. Each choice is reasonable alone. That is inferred from the applications' tracked resources; the repository itself was not read.

Automated sync in Argo CD does not delete anything by default: a resource that is no longer in Git stays in the cluster. `prune: true` changes that. From then on a resource that disappears from what Argo CD renders from Git is deleted in the next sync.

"Disappears from Git" covers more than a deliberate removal. A directory that is moved, a file that is renamed, a generator or template that renders a different name all look the same to Argo CD: the old object is no longer among the target resources. The one built-in protection is narrow. Automated sync refuses to prune when an application renders no resources at all, but an application that still renders some resources, only not the Namespace, passes it.

For most kinds a wrong prune removes one object. A Namespace and a CRD are containers. Deleting a Namespace deletes everything in it, while the Namespace sits in Terminating and accepts nothing new. Deleting a CRD deletes every custom object of that kind in the cluster, and recreating the definition starts empty. On local-path volumes a deleted claim also deletes the directory on the node.

At [InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/) a pull request added an Argo CD Application under a name that already existed; the new object replaced the existing application and an entire production environment was deleted, with every API endpoint returning 404 for almost six hours. The volumes had reclaim policy Retain, so the data stayed. The team then added `Prune=false` to stateful resources and Namespaces. In this cluster the volumes are local-path, whose directories are cleaned up when the volume is deleted.

[Argo CD issue 28630](https://github.com/argoproj/argo-cd/issues/28630) reports shared Namespaces managed by Argo CD being deleted and about 97 applications left Missing or OutOfSync. The path there was a manual sync with force, which replaced the Namespace, and `Prune=false` did not prevent it. A Namespace tracked as an application resource is exposed to more than one path.

### How to watch it

There is no metric for pruned resources. What can be watched is the after-effect of the protection: once a Namespace carries `Prune=false`, a sync that would have deleted it leaves the application OutOfSync instead, so an application that stays OutOfSync longer than a rollout takes is the signal to look at. The audit did not check whether this cluster has such a rule.

```yaml
- alert: ArgoAppOutOfSync
  expr: argocd_app_info{sync_status="OutOfSync"} == 1
  for: 30m
```

The list itself can be seen at any time from the applications' status; the command below is an example of the shape.

```bash
kubectl get applications.argoproj.io -A -o json | jq -r '.items[] | select(.spec.syncPolicy.automated.prune==true) | .metadata.name as $n | .status.resources[]? | select(.kind=="Namespace" or .kind=="CustomResourceDefinition") | $n+" "+.kind+"/"+.name'
```

### How it is solved

At the scale this cluster is run at, take the Namespace manifests out of the application directories and let Argo CD create the Namespaces with the sync option `CreateNamespace=true`, or keep the manifests and annotate each Namespace with `Prune=false`. Do the same for CRDs that hold objects you cannot recreate, which is most likely the case in `istio`. A Namespace you really want gone then has to be deleted by hand, and with `Prune=false` the application shows OutOfSync until someone does it. The annotation looks like this:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: app-g-api
  annotations:
    argocd.argoproj.io/sync-options: Prune=false
```

The nine applications are in the namespace `argocd`. Those whose declarations this audit read, `app-a-prod` (path `prod/app-a-prod`), `app-g-api` (path `prod/app-g-api`) and `app-ac-prod` (path `prod/app-ac-prod`), point at the repository `example-org/k8s-manifests` on GitHub with selfHeal on; the other six were not opened. Change the Namespace manifests there; an annotation added by hand in the cluster is reverted on the next sync.

What to be careful of when applying it: removing a Namespace manifest from Git while `prune` is still on is exactly the deletion this problem is about. Add the `Prune=false` annotation and let it sync first, and only then remove the manifest. `CreateNamespace=true` alone is not a protection here: `app-g-api` already has it, and its Namespace still carries the tracking id `app-g-api:/Namespace:/app-g-api`, so it stays tracked.

At a larger scale, Namespaces and CRDs are annotated `Prune=confirm,Delete=confirm` so that a sync which wants to delete them waits for a person, volumes use a StorageClass with reclaim policy Retain, and `FailOnSharedResource=true` stops an application before it changes objects that belong to another one.

### Evidence

| What | Value | Source |
|---|---|---|
| Applications with prune that track a Namespace or CRD | 9 | finding `argocd.prune-manages-namespace-or-crd.cluster` |
| Application names | app-a-prod, app-b-prod, app-d, app-g-api, app-ac-prod, istio, app-k, app-n, app-l-prod | the same finding |
| Databases in app-ac-prod without a dump job | 3 | `resilience.backup.databases` |

### Further reading

- [Argo CD: Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/): `Prune=false`, `Prune=confirm`, `Delete=confirm` and `CreateNamespace`, with what each leaves in the sync status.
- [Argo CD: Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/): what automated sync deletes by default, what prune adds and what the empty-application protection covers.
- [InfluxData: Deleting Production in a Few Easy Steps](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/): a full account of an Argo CD deletion and the changes the team made afterwards.
- [Argo CD: App Deletion](https://argo-cd.readthedocs.io/en/stable/user-guide/app_deletion/): when deleting an Application also deletes its resources.

## 4. Kubernetes 1.33 is past its end of support

**Why this one.** A vulnerability found in Kubernetes 1.33 from now on will not be patched, and every month of waiting adds work to the upgrade that has to come.

### What is the matter

Both nodes and the server run k3s `v1.33.5+k3s1`. The Kubernetes project ended support for the 1.33 minor on 2026-06-28, 140 days before this audit, so no further patch release of 1.33 will come from upstream.

The API server reports one series of `apiserver_requested_deprecated_apis`: some client still requests `endpoints` in version `v1`, which Kubernetes deprecated in favour of EndpointSlices. The series carries no release in which it is removed, so it does not block the next upgrade, but it is the kind of call to look for before each step.

### Why it comes about

No upgrade is scheduled, so the cluster stays on the version it was installed with or last upgraded to. That is inferred from the version and from the components this audit found, among which there is no system-upgrade-controller.

The Kubernetes project maintains release branches for the three newest minors. A minor gets patch releases for about fourteen months: twelve months of standard support, then two months in which only fixes for vulnerabilities with a CVE, dependency problems and critical core issues are released. After that it is end of life. Vulnerabilities that only affect an old version may not even be reported.

The cost of waiting comes from one rule: the API server must not skip a minor when it is upgraded, even in a single-server cluster. A cluster two or three minors behind needs two or three upgrades in a row, each with its own removed APIs and add-on compatibility to check. kubelets may be up to three minors older than the API server, so nodes can lag, but not without limit, and k3s follows the same skew policy: servers first, then agents, one minor at a time.

Each minor also removes API versions deprecated earlier. Asking the API server does not show which manifests still use them, because it converts objects to whatever version is requested; tools such as Pluto read the manifests and Helm releases instead.

[ZenML](https://status.zenml.io/incidents/bnrlb8tck3v0) ran its production EKS cluster on an outdated Kubernetes version. The upgrade covered several Terraform modules at once, one change removed IAM permissions from the worker nodes, and the workspaces were down for about eight hours. An upgrade that has been put off tends to arrive as several changes in one night.

### How to watch it

The end-of-support date is a calendar fact, not a metric, so it is watched by putting it on the calendar. What can be measured is whether anything still calls an API version that a later minor removes: a series of `apiserver_requested_deprecated_apis` with a `removed_release` label is a client to fix before the upgrade.

```promql
apiserver_requested_deprecated_apis{removed_release!=""}
```

The rule `KubeVersionMismatch` exists in this cluster and catches nodes left on different versions during an upgrade.

### How it is solved

At the scale this cluster is run at, put the upgrade on the calendar: one minor at a time, a few weeks after k3s offers it. On k3s a Plan of the system-upgrade-controller that follows a release channel upgrades the server and then the agent node by node, with cordon and drain. Before each step run Pluto over the manifests and Helm releases for API versions the next minor removes. Choose the channel with care: the controller does not protect against a jump of more than one minor, so while the cluster is catching up, a channel tied to the next Kubernetes minor is safer than `stable` or `latest`, which k3s offers next to it. The Plan below shows the shape for the server node, with the channel to be replaced.

```yaml
apiVersion: upgrade.cattle.io/v1
kind: Plan
metadata:
  name: server-plan
  namespace: system-upgrade
spec:
  concurrency: 1
  cordon: true
  nodeSelector:
    matchExpressions:
      - { key: node-role.kubernetes.io/control-plane, operator: In, values: ["true"] }
  serviceAccountName: system-upgrade
  upgrade:
    image: rancher/k3s-upgrade
  channel: https://update.k3s.io/v1-release/channels/stable
```

Nothing in the cluster marks the k3s installation as managed by Argo CD or Helm; k3s is installed on the nodes themselves.

What to be careful of when applying it: this cluster has two nodes, the databases run on `node-b` with local-path volumes bound to it, and their dumps sit on `node-a`. A drain of either node stops whatever is pinned to it until the node is back, because local-path volumes cannot follow a pod to the other node. The node `node-b` is also the control-plane node and carries `role=observability`, so the server Plan drains the node where the databases and Prometheus run; Prometheus keeps its 30 days on an `emptyDir`, which a drain deletes, so fix problem 2 first or accept that loss. Take a copy of the databases off the cluster before the first upgrade (problem 1), and expect each database to be down for the length of its node's upgrade. Do not leave the channel at `stable` on 1.33: it can jump more than one minor.

At a larger scale the upgrade is a written, rehearsed procedure: a non-production cluster first, removed APIs scanned in CI, control plane then add-ons then nodes, with PodDisruptionBudgets in place.

### Evidence

| What | Value | Source |
|---|---|---|
| Server version | v1.33.5+k3s1 | `inventory.server_version` |
| Upstream end of life of 1.33 | 2026-06-28 | finding `platform.k8s-version-eol.cluster` |
| Days past end of life | 140 | the same finding |
| Nodes | 2 | `inventory.nodes` |
| Deprecated API series requested | 1 (endpoints v1) | `metrics.apiserver_requested_deprecated_apis` |

### Further reading

- [Kubernetes: Patch Releases](https://kubernetes.io/releases/patch-releases/): the support period of a minor, what maintenance mode still fixes, and the end-of-life date of each release.
- [k3s: Automated Upgrades](https://docs.k3s.io/upgrades/automated): how a Plan upgrades a k3s cluster node by node and what the controller does not guard against.
- [Amazon EKS best practices: Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html): the order of an in-place upgrade and the tools that find removed APIs before it.

## 5. Some alert notifications fail to reach Discord

**Why this one.** An alert that fires and is not delivered is an outage nobody hears about, and the always-firing Watchdog alert that would reveal a broken path is routed to a receiver that sends nowhere.

### What is the matter

Alertmanager tried to send 60 notifications in the last 24 hours, and 8 of them failed; the other 52 were delivered. All failures are on the `slack` integration. The receivers of this cluster are named `discord` (the default) and `discord-critical`, so the `slack` integration is most likely how a Discord webhook is called, which Discord supports. Which of the two receivers the failures came from is not split out, so the failures may touch any alert.

The rule `AlertmanagerFailedToSendAlerts` exists in this cluster and was firing in 27 rule evaluation samples over the last seven days; it travels down the same path, so whether it was seen is not known. Alertmanager's configuration reloaded successfully.

The routing tree sends alerts with severity `info` or `none` to the receiver `null`, which has no integration. `Watchdog`, the alert that always fires to prove the path works, has severity `none` and is firing now, so it goes to `null` and proves nothing.

### Why it comes about

Why 8 of 60 failed is not known. A share that fails while the rest succeeds points more at rate limits or brief network errors on the way to Discord than at an expired webhook, which would fail every notification; that is inferred from the numbers. The Alertmanager log names the error per notification, and it was not read: logs of this cluster go to Elasticsearch, which this audit does not query.

An alert travels over two hops. Prometheus evaluates the rules and sends what fires to Alertmanager. Alertmanager deduplicates, groups and routes it to a receiver, and the receiver's integration calls the outside service. Each hop can fail while everything looks healthy from inside, because the component that would report the failure is the one that failed. Prometheus here reports no errors sending to Alertmanager and dropped nothing in a day, so the first hop is sound.

On the second hop Alertmanager counts each notification and each failure per integration, in `alertmanager_notifications_total` and `alertmanager_notifications_failed_total`. That counter is the only place an expired webhook or a rejected request shows up. Alertmanager does retry, but it raises no alert of its own beyond what a rule asks for, and such an alert travels down the same path.

That is why the `Watchdog` alert exists. It always fires, so it should always arrive somewhere; sent to an external heartbeat service, its silence becomes the alarm when the whole path breaks.

### How to watch it

The share of failed notifications per integration shows it as it happens. `AlertmanagerFailedToSendAlerts` from the Alertmanager mixin is built on it and is present here.

```promql
rate(alertmanager_notifications_failed_total[15m])
  / rate(alertmanager_notifications_total[15m]) > 0.01
```

For a total failure, route `Watchdog` to a heartbeat service outside the cluster. That route does not exist today.

### How it is solved

At the scale this cluster is run at, read the Alertmanager log in Elasticsearch for the errors on the `slack` integration and fix what it names; if it is rate limiting, a longer `group_interval` or fewer, better grouped alerts reduce the calls. Then add the one check that does not depend on the path itself: a route that sends `Watchdog` to the webhook of an external heartbeat service. The route must come before the one that sends severity `none` to `null`, because the first match wins. The example shows the shape; the address is a placeholder.

```yaml
route:
  receiver: discord
  routes:
    - matchers:
        - alertname = "Watchdog"
      receiver: heartbeat
      repeat_interval: 5m
receivers:
  - name: heartbeat
    webhook_configs:
      - url: https://heartbeat.example/ping/<id>
```

Alertmanager is part of the Helm release `kube-prometheus-stack`, managed by the Argo CD application `monitoring` with selfHeal on, so change the routes in the values that application uses; a change made in the cluster is reverted.

What to be careful of when applying it: Helm replaces a list in the values instead of merging it, so the Watchdog route has to be added to the existing `routes` list next to the routes for `null` and `discord-critical`, not put in its place; pasted as it stands, critical alerts would lose their own receiver and info alerts would start reaching Discord. The heartbeat service pages when the signal stops, so a Prometheus or Alertmanager restart, such as the one on 2026-11-14, will now page too.

At a larger scale alerts about a failing integration go through a second integration, routes are tested with `amtool config routes test` before they are applied, and Alertmanager runs as a cluster of replicas.

### Evidence

| What | Value | Source |
|---|---|---|
| Notifications attempted, 24 h | 60 | `metrics.am_notifications_1d` |
| Notifications failed, 24 h | 8 | `observability.alertmanager.notifications_failed_1d` |
| Integration that failed | slack | the same row |
| Default receiver | discord | `observability.alertmanager.default_receiver` |
| Receiver for severity info or none | null | `observability.alertmanager.routes` |
| Firing now | Watchdog | `observability.alerts.firing_now` |
| AlertmanagerFailedToSendAlerts, 7 days | 27 samples | `observability.alerts.firing_7d_by_alert` |
| Alerts Prometheus failed to send, 24 h | 0 dropped | `stackhealth.prometheus.notifications_dropped_1d` |

### Further reading

- [Prometheus Operator runbooks: Watchdog](https://runbooks.prometheus-operator.dev/runbooks/general/watchdog/): how an always-firing alert proves the whole path works, and what to connect it to.
- [Alertmanager mixin: alerts](https://raw.githubusercontent.com/prometheus/alertmanager/main/doc/alertmanager-mixin/alerts.libsonnet): the rules that watch Alertmanager itself, with their thresholds.
- [Prometheus: Alertmanager high availability](https://prometheus.io/docs/alerting/latest/high_availability/): what is replicated between instances and why duplicates are preferred over misses.

## The next largest problems

- **CPU limits throttle application, database and monitoring containers.** Nine containers were throttled in between a quarter and three fifths of their scheduling periods over the last day or their pod's life, among them `app-h-prod/app-h-api-server`, `app-g-api/app-g-postgres`, `logging/elasticsearch`, `logging/fluent-bit` and Prometheus itself, and seven more are throttled below the fail line. While a container is throttled, its work waits for the next period even if it is urgent. Severity: high.
- **MinIO in app-g-api runs at 95% of its memory limit.** The seven-day p95 of the working set of `app-g-api/app-g-minio-0` is 0.95 of its limit, so a small rise in use ends in an OOM kill and a restart. Severity: high.

## Since the previous report

There is no earlier run to compare with, so this covers only what this run collected.

## Each area in one line

| Area | What |
|---|---|
| resources | CPU limits throttle nine containers above the fail line and seven below it, MinIO sits at 95% of its memory limit, and Tempo was killed for memory this week. |
| scaling | No critical or high problem was found here. |
| observability | Prometheus stores its 30 days on an emptyDir volume, 8 of 60 notifications failed in a day, and the Watchdog alert is routed to a receiver that sends nowhere. |
| traffic | MetalLB speaker readiness and configuration freshness raised high warnings that were not opened in depth. |
| resilience | No backup tool exists and all eight backup CronJobs write their dumps to local volumes on the node node-a only. |
| hygiene | Nine Argo CD applications with prune enabled track a Namespace or CRD as a resource. |
| storage | The filesystem holding local-path volumes has little free space, raised as a high warning. |
| security | One ConfigMap, default/app-ai-backend-config, has keys that look like secrets, raised as a high warning. |
| cost | This audit found no problem here. |
| tenancy | This audit found no problem here. |
| node OS | Nodes were not read, by the user's choice; one node root filesystem is high in use as seen from node-exporter. |
| platform | The cluster runs k3s v1.33.5, 140 days past the upstream end of life of 1.33. |

## Limits of this run

**Not judged because the cluster does not hold the data**

- Loki is not installed and the logs go to Elasticsearch, which this audit does not query.
  - Weaker for it: Why Tempo and app-ac-ai ran out of memory, and why some Discord notifications failed, are inferred without application or Alertmanager logs.
  - To see it: Read the Alertmanager pod log and the Tempo log for the week in Elasticsearch.

**Not read by kubegap yet**

- 13 components were read only through their objects and metrics; kubegap has no checks of their own for them: actions-runner-controller, elasticsearch-opensearch, fluent-bit, fluent-bit-events, ingress-nginx, istio, kube-state-metrics, metrics-server, node-exporter, opentelemetry-collector, prometheus-operator, reloader, tempo-jaeger.
  - Weaker for it: a fault inside one of these components is not in this report.
- The collection stopped at one of its own limits and read only part of: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, coredns: kube-system/coredns, external-secrets: external-secrets/external-secrets, fluent-bit: logging/fluent-bit, ingress-nginx: ingress-nginx/nginx-ingress-ingress-nginx-controller, istio: istio-system/istiod, metallb: metallb-system/speaker, tempo-jaeger: monitoring/tempo).
  - Weaker for it: a number counted from these is a lower bound, and the oldest lines of the day or the rest of a list are not in this report.

**What you answered not to read at the first-run questions**

- Node checks.
  - What answering adds: up to 26 node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape.
  - To see it: `/kubegap setup` asks the question again.

## Numbers

Severity is for a cluster run at scale small.

No earlier full run to compare with.

| Severity | fail | warn |
|---|---|---|
| critical | 0 | 2 |
| high | 15 | 23 |
| medium | 93 | 173 |
| low | 13 | 115 |

Checks behind each entry:

- Tempo was killed for memory and its pod restarted up to 163 times: `resources.oomkilled-repeated.monitoring/sts/tempo:tempo`, `resources.oomkilled-repeated.app-ac-prod/deploy/app-ac-ai:ai`
- Prometheus restarted and repaired a corrupted write-ahead log: `logs.signatures.prometheus.wal-corrupt`
- Database backups never leave the node they are written on: `resilience.no-backup.cluster`, `resilience.backup-same-node.*`
- Prometheus keeps 30 days of metrics on an emptyDir volume: `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`
- Nine Argo CD applications would delete a whole Namespace if its manifest went missing: `argocd.prune-manages-namespace-or-crd.cluster`
- Kubernetes 1.33 is past its end of support: `platform.k8s-version-eol.cluster`
- Some alert notifications fail to reach Discord: `observability.alertmanager-notification-failed.slack`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.2.0, rubric 0.1.94 · snapshot `~/.kubegap/snapshots/<context>/2026-11-15T01-02-12`

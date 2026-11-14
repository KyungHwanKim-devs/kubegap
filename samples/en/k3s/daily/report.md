# default — daily audit, 2026-11-15 00:59

Broken now: 0 · Happened since the last audit: 3 · Matter most now: 3

Broken now: nothing

Happened since the last audit: Prometheus restarted and repaired a corrupted WAL · Tempo was killed out of memory and kept restarting · The app-ac-ai pod was killed out of memory once

What matters most now: ① No backup is shown to leave the cluster ② Prometheus keeps its metrics on emptyDir ③ Some alerts do not reach the channel

Scale: small

There are 17 kinds of serious problem a daily audit cannot see. They are listed at the end; to check them, run `/kubegap full`.

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 2 of 2 Ready |
| Pods | 106 running, 0 pending, 3 failed |
| Namespaces | 28, 8 production |
| Components | 26 |
| Metrics and log stores | prometheus 3.7.3 / no Loki |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## What happened since the last audit

This is the first daily audit of this cluster, so there is no earlier one to compare with. What is listed happened within the period this audit collected.

### Prometheus restarted and repaired a corrupted WAL

On 2026-11-14 at 01:14 UTC the Prometheus log recorded 2 lines of a WAL corruption and its repair, right after the pod started. The WAL (write-ahead log) holds the most recent samples before they are written into blocks. The repair finished and Prometheus is Ready now, but the samples in the damaged segment are lost. Why the pod restarted cannot be told from this audit. It is over now.

### Tempo was killed out of memory and kept restarting

A `tempo` pod in `monitoring` ended with OOMKilled in the last 7 days and its pods restarted 163 times in that period. OOMKilled means the kernel ended the container for going over its memory limit. The pod running now, `tempo-0`, has restarted once since it was created.

### The app-ac-ai pod was killed out of memory once

A pod of `app-ac-ai` in `app-ac-prod` ended with OOMKilled once in the last 7 days and was replaced. The pod running now has not restarted. It is over now.

## What matters most now

### 1. No backup is shown to leave the cluster

**What it is.** No backup tool such as Velero is installed and there are no VolumeSnapshots. Several CronJobs that look like backups ran in the last 7 days (database dumps in `app-f-prod`, `app-h-prod`, `app-g-api` and others, and `etcd-snapshot-backup` in `kube-system`) and 5 etcd snapshots. Where those copies are written cannot be read in this audit.

**Why it matters.** If a copy is kept on the same node disk as the data, a lost disk takes the databases and their backups at once. A namespace deleted by mistake or a broken etcd then cannot be brought back.

**What to do.** For a small k3s cluster, keep the k3s etcd snapshots and the database dumps, and add a step that copies them to storage outside the cluster, such as an S3-compatible bucket. Then restore one dump into a scratch database once, because a dump that was never restored may not work. Where the CronJobs write today can be found with `/kubegap full`.

Further reading: [k3s: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot)

### 2. Prometheus keeps its metrics on emptyDir

**What it is.** Prometheus stores 22.3GiB of time series on an emptyDir volume, which lives only as long as the pod stays on its node. Retention is 30d with no size cap, so only time trims the data. The WAL corruption repaired on 2026-11-14 happened on this storage.

**Why it matters.** When the pod moves to another node or the node is replaced, all 30 days of metrics are gone. Without a size cap the node disk fills before retention trims anything, and node `<ip>` is already at 75% disk usage.

**What to do.** Give Prometheus a PVC through `storageSpec` in the `kube-prometheus-stack` values that Argo CD syncs, and set `retention.size` to about 80% of that PVC. Switching to a PVC starts with an empty volume, so the metrics on the emptyDir are lost once.

Further reading: [Prometheus: Storage](https://prometheus.io/docs/prometheus/latest/storage/)

### 3. Some alerts do not reach the channel

**What it is.** Alertmanager tried 60 notifications in the last 24 hours and 8 failed; the other 52 were delivered. Alertmanager is the component that sends the alerts Prometheus fires to a channel. The failures are on the `slack` integration, which the default receiver `discord` uses.

**Why it matters.** An alert that fails to send is not retried forever, so a node or a database can go down and nobody is told. The users are then the first to notice.

**What to do.** Read the Alertmanager log for the error of the failed sends, such as a rate limit or an expired webhook, and fix the receiver. To know at all times that the path works, route the always-firing `Watchdog` alert to a service outside the cluster.

Further reading: [Prometheus Operator runbooks: Watchdog](https://runbooks.prometheus-operator.dev/runbooks/general/watchdog/)

## What else is open

- Kubernetes `v1.33` is past its end of support
- Nine Argo CD Applications with prune enabled manage a Namespace or CRD
- MinIO in `app-g-api` runs near its memory limit
- Containers with heavy CPU throttling
- MetalLB speaker is not ready on every node and its config may be stale

## What this audit did not look at

A daily audit is the light one. It read the Kubernetes API and the metric and log stores only.

- It did not keep how your applications are started and configured (command, arguments, environment values, ConfigMap keys). So it cannot tell whether a database has a backup job, whether a credential is written into a ConfigMap, or whether a JVM heap is larger than its memory limit.
- It counted how many lines of the platform components' logs match a known failure pattern and kept no text of any line. So an error that matches no known pattern is not in this report.
- It contacted no node. So it cannot see a node disk filling up, the kernel ending processes for lack of memory, certificates of a k3s server about to expire, the etcd snapshots of k3s, or errors of the kubelet and the container runtime.
- It did not read the kubelet's settings (eviction thresholds, reserved resources, maxPods).
- It did not read the control plane's logs. So it cannot see slow API requests, failing admission webhooks, authentication failures or a slow etcd.
- It did not run the extra tools, which take minutes. So it has no request and limit recommendations from a week of use and does not list the API versions the next Kubernetes removes.
- It did not read the Helm releases. So a release that failed or was left half-installed is not in this report.
- Secret values are not read by any audit.
- The collection stopped at one of its own limits and read only part of: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, coredns: kube-system/coredns, external-secrets: external-secrets/external-secrets, fluent-bit: logging/fluent-bit, ingress-nginx: ingress-nginx/nginx-ingress-ingress-nginx-controller, istio: istio-system/istiod, metallb: metallb-system/speaker, tempo-jaeger: monitoring/tempo). A number counted from these may be lower than the real one.

So 62 of the 349 checks were not looked at this time: the inside of the nodes, cost, APIs about to be removed and the like. They are counted neither as a problem nor as a pass.

In particular, the problems below can be serious and still cannot be seen by a daily audit, because they show only in the inside of a node, in the cloud account or in how applications are configured. That they are not in this report does not mean they are not there.

- Workloads with pods that could not be scheduled in the last 24 hours
- Node-level OOM killer invoked (different from container OOMKilled)
- Kernel soft lockup / hung task / RCU stall
- Disk I/O errors or filesystem errors
- conntrack table full (packets dropped)
- Container runtime not RuntimeReady/NetworkReady
- Node clock not synchronized (timedatectl)
- Objects using APIs removed in the next minor version (Pluto, kubent)
- DB backup (dump) stays only on the same node disk as the source (no off-node copy)
- Secret-like keys or config lines inside a ConfigMap (key names only are recorded)
- ip_forward or bridge-nf-call-iptables disabled on a flannel node (same-node Service traffic breaks)
- Embedded etcd snapshots missing or stale
- k3s internal certificates expiring soon
- k3s datastore (etcd/kine) requests are slow (apply latency, fdatasync, leader changes)
- k3s datastore DB is large (near the 2GiB etcd quota)
- local-path volume usage exceeds the PVC capacity (capacity is not enforced)
- Node filesystem hosting local-path volumes has little free space (volumes have no capacity limit)

To check these, to follow a cause down to the raw material, and to have each problem explained with its principle, how to watch it and how it is solved at each scale, run `/kubegap full`.

Check ids (`/kubegap explain <id>`):

- Prometheus restarted and repaired a corrupted WAL: `logs.signatures.prometheus.wal-corrupt`
- Tempo was killed out of memory and kept restarting: `resources.oomkilled-repeated.monitoring/sts/tempo:tempo`
- The app-ac-ai pod was killed out of memory once: `resources.oomkilled-repeated.app-ac-prod/deploy/app-ac-ai:ai`
- No backup is shown to leave the cluster: `resilience.no-backup.cluster`
- Prometheus keeps its metrics on emptyDir: `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`, `logs.signatures.prometheus.wal-corrupt`, `node.disk-usage.192.168.90.101:9100:/`
- Some alerts do not reach the channel: `observability.alertmanager-notification-failed.slack`

kubegap 0.2.0, rubric 0.1.94 · snapshot `~/.kubegap/snapshots/<context>/2026-11-15T00-59-05`

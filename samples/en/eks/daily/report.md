# app-u-cluster-eks — daily audit, 2026-11-15 01:45

Broken now: 0 · Happened since the last audit: 1 · Matter most now: 3

Broken now: nothing

Happened since the last audit: Prometheus was restarted out of memory

What matters most now: ① The cluster has no backup ② Alertmanager and Loki keep their data on emptyDir ③ Kubernetes and Karpenter are both past their supported versions

Scale: medium

There are 22 kinds of serious problem a daily audit cannot see. They are listed at the end; to check them, run `/kubegap full`.

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 9 of 9 Ready |
| Pods | 131 running, 0 pending, 0 failed |
| Namespaces | 21, 8 production |
| Components | 22 |
| Metrics and log stores | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## What happened since the last audit

This is the first daily audit of this cluster, so there is no earlier one to compare with. What is listed happened within the period this audit collected.

### Prometheus was restarted out of memory

The `prometheus` container of `prometheus-kube-prometheus-stack-prometheus-0` in `monitoring` reached its memory limit and was ended by the kernel at 2026-11-14T14:34:30Z. A container ended this way is reported as OOMKilled. It has restarted 3 times since the pod was created and is running again now. Why its memory grew cannot be told from this audit. It is over now.

## What matters most now

### 1. The cluster has no backup

**What it is.** No backup tool is installed, there are no etcd snapshots, no VolumeSnapshots and no CronJob that looks like a backup ran in the last 7 days. A backup here means a copy of the Kubernetes objects and the volume data kept outside the cluster.

**Why it matters.** If a volume is deleted, a namespace is removed by mistake or the cluster is lost, the data on the persistent volumes cannot be brought back. Services such as `app-z-neo4j` in `prod-app-z-backend` keep their data on such volumes.

**What to do.** Install Velero and give it a Schedule that backs up the Kubernetes objects and the volumes to an S3 bucket in another account or region. On EKS, add an AWS Backup plan for the EBS volumes and copy the snapshots to another region. Restore into a scratch cluster on a regular date, because a backup that was never restored is not known to work.

Further reading: [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/)

### 2. Alertmanager and Loki keep their data on emptyDir

**What it is.** The StatefulSets `alertmanager-kube-prometheus-stack-alertmanager` and `loki-stack` in `monitoring` store their data on emptyDir volumes, each with a single replica. An emptyDir is a scratch volume that is deleted together with the pod.

**Why it matters.** When either pod is deleted or moved to another node, by a drain, an eviction, a node replacement or a rollout, all stored logs and all alert silences are gone. Karpenter replaces nodes in this cluster, so such a move is a normal event here, not a rare one.

**What to do.** Declare a volume claim in the chart values on a StorageClass that allows expansion: `alertmanagerSpec.storage` for Alertmanager and `persistence.enabled` for Loki. Run Alertmanager with more than one replica so that a pod with a fresh volume is filled again by its peers. Switching the volume recreates the pod, so the logs held now are lost once at that moment.

Further reading: [Prometheus Operator: Storage](https://prometheus-operator.dev/docs/platform/storage/)

### 3. Kubernetes and Karpenter are both past their supported versions

**What it is.** The control plane runs `v1.32.13`, whose upstream support ended 260 days ago. Karpenter `0.37.0` supports Kubernetes up to `1.30` only, and the EC2NodeClass still uses the AL2 image family, which has no image from Kubernetes `1.33` on. Karpenter is the component that launches new nodes when pods cannot be scheduled.

**Why it matters.** Outside its support table Karpenter stops resolving node images, so new nodes may fail to launch and pods that need room stay Pending. The control plane receives no more security patches.

**What to do.** Upgrade Karpenter first, one minor at a time and with its CRDs, until it supports the cluster version, then upgrade the control plane one minor at a time. Move the EC2NodeClass to AL2023 with a pinned image version kept in Git, and give each NodePool a disruption budget so that replacing nodes does not happen during busy hours. Check the removed APIs with Pluto before each control plane step.

Further reading: [Karpenter: Compatibility](https://karpenter.sh/docs/upgrading/compatibility/)

## What else is open

- Prometheus is CPU throttled
- No alert rule covers OOM kills
- Secret-looking environment variables set as plain text
- NetworkPolicies exist but the CNI does not enforce them
- A privileged container outside the system namespaces

## What this audit did not look at

A daily audit is the light one. It read the Kubernetes API and the metric and log stores only.

- It did not keep how your applications are started and configured (command, arguments, environment values, ConfigMap keys). So it cannot tell whether a database has a backup job, whether a credential is written into a ConfigMap, or whether a JVM heap is larger than its memory limit.
- It counted how many lines of the platform components' logs match a known failure pattern and kept no text of any line. So an error that matches no known pattern is not in this report.
- It contacted no node. So it cannot see a node disk filling up, the kernel ending processes for lack of memory, certificates of a k3s server about to expire, the etcd snapshots of k3s, or errors of the kubelet and the container runtime.
- It did not read the kubelet's settings (eviction thresholds, reserved resources, maxPods).
- It did not read the control plane's logs. So it cannot see slow API requests, failing admission webhooks, authentication failures or a slow etcd.
- It called no AWS API. So it cannot tell whether backups exist (AWS Backup, snapshots), whether a subnet is running out of addresses, whether the cluster endpoint or a security group is open to the world, how the load balancers are set and whether they return errors, or what the cluster costs.
- It did not run the extra tools, which take minutes. So it has no request and limit recommendations from a week of use and does not list the API versions the next Kubernetes removes.
- It did not read the Helm releases. So a release that failed or was left half-installed is not in this report.
- Secret values are not read by any audit.
- The collection stopped at one of its own limits and read only part of: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, ebs-csi: kube-system/ebs-csi-controller, external-dns: kube-system/external-dns, external-secrets: external-secrets/external-secrets, external-secrets: external-secrets/external-secrets-cert-controller, loki: monitoring/loki-stack). A number counted from these may be lower than the real one.

So 86 of the 367 checks were not looked at this time: the inside of the nodes, cost, APIs about to be removed and the like. They are counted neither as a problem nor as a pass.

In particular, the problems below can be serious and still cannot be seen by a daily audit, because they show only in the inside of a node, in the cloud account or in how applications are configured. That they are not in this report does not mean they are not there.

- Workloads with pods that could not be scheduled in the last 24 hours
- apiserver logs of failed webhook calls
- Node-level OOM killer invoked (different from container OOMKilled)
- Kernel soft lockup / hung task / RCU stall
- Disk I/O errors or filesystem errors
- conntrack table full (packets dropped)
- Container runtime not RuntimeReady/NetworkReady
- Node clock not synchronized (timedatectl)
- EKS Secret KMS envelope encryption is off
- Node IMDS reachable from pods (hop limit 2 or more, or tokens optional)
- Objects using APIs removed in the next minor version (Pluto, kubent)
- ALB/NLB target group has unhealthy targets (health check failing)
- DB backup (dump) stays only on the same node disk as the source (no off-node copy)
- Secret-like keys or config lines inside a ConfigMap (key names only are recorded)
- Cluster public endpoint open to the whole world
- No EBS snapshot policy (DLM) or AWS Backup plan
- ACM certificate in use is expiring soon, expired, or cannot auto-renew
- AWS service quota usage near the limit (at the limit, node, LB and IP creation fail silently)
- Cluster security group inbound open to 0.0.0.0/0 (other than 443)
- Node pod IPs near the limit of its instance type
- ipamd has already answered "no available IP" on a node
- Node subnet has few free IPs

To check these, to follow a cause down to the raw material, and to have each problem explained with its principle, how to watch it and how it is solved at each scale, run `/kubegap full`.

Check ids (`/kubegap explain <id>`):

- Prometheus was restarted out of memory: `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`, `resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`
- The cluster has no backup: `resilience.no-backup.cluster`
- Alertmanager and Loki keep their data on emptyDir: `observability.stack-storage-emptydir.*`
- Kubernetes and Karpenter are both past their supported versions: `platform.karpenter-version-compat.cluster`, `platform.k8s-version-eol.cluster`, `karpenter.ec2nodeclass-al2.cluster`

kubegap 0.2.0, rubric 0.1.94 · snapshot `~/.kubegap/snapshots/<context>/2026-11-15T01-45-51`

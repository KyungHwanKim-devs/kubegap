# kubegap report details — arn:aws:eks:us-east-1:<account>:cluster/my-cluster (`my-cluster`), daily mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `llm/facts.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `my-cluster` / arn:aws:eks:us-east-1:<account>:cluster/my-cluster (eks, v1.32.13-eks-577a51e) |
| Run time / mode | 2026-11-05T17:01:11+09:00 / daily (collection 151.3 s, 33 steps skipped by mode, 0 failed) |
| Profile | `prod` (detected) |
| kubegap / rubric / signatures | 0.1.2 / 0.1.80 / 1.1.0 |
| Nodes / namespaces / pods / CRDs | 10 (Ready 10) / 25 / 157 / 47 |
| Components (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics store | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| Log store | loki 2.6.1 |
| Node access | ssm (EKS: SSM send-command); SSM unregistered 2 |
| Snapshot | `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 1 | 3 | fail +0 · warn +1 |
| high | 27 | 21 | fail -3 · warn +3 |
| medium | 99 | 133 | fail +12 · warn -8 |
| low | 8 | 134 | fail -2 · warn +1 |
| info | 2 | 0 | no previous run of this mode |

Checks 365: evaluated 299, disabled by profile 2, skipped 6, not collected in this mode 56, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

| Finding | First pass | Final | Reason |
|---|---|---|---|
| traffic.db-exposed.nlb/acme-db-shared | warn high | warn medium | The security group admits at most 4 sources per port, the widest a /32, so the database ports are not open to the internet at large. |

### 1-2. Aggregates the LLM recounted

| Finding | First pass | Final | Reason |
|---|---|---|---|
| resilience.replicas-same-node.* | 4 findings | 4 prod Deployments with every replica on node-1-139: app-r, app-o-ai, app-o-backend, app-l-frontend | One cause, grouped into problem 1. |
| pods on node-1-139 | 33 pods (prod 20) | 38 pods in objects/pods.json, 5 of them DaemonSet pods, so 33 that a drain evicts: 20 prod, 12 dev, 1 external-secrets | Counted from objects/pods.json by spec.nodeName. |
| single-replica prod services on node-1-139 without PDB | not counted | 6: app-m-admin, app-o-admin, app-o-frontend, app-p-backend, app-n-admin-frontend, app-s-backend | Deployments from objects/deployments.json with replicas 1 matched against objects/poddisruptionbudgets.policy.json selectors. |
| traffic.alb-unhealthy-targets.* | 6 findings | 6 target groups, 4 prod and 2 dev, one item | One cause: no healthcheck-path annotation. |
| later | critical and high findings outside today's problems | 22 groups: 15 listed, 7 more (ExternalSecret database/mysql-app-n-secret UpdateFailed and ESO provider errors; EC2NodeClass IMDS hop limit and root volume encryption; node root disks at 81% and 79%; subnet us-east-1c with 61 free IPs; CPU throttling of the app-m and app-o frontends; apiserver 503 at 0.004/s; 115 Unhealthy probe events) | Grouped by cause as in the analysis procedure. |

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `eks.public-endpoint-open.cluster` | high | 5 | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | high | 5 | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 194 occurrences total (90 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 … |
| `karpenter.ec2nodeclass-al2.cluster` | high | 5 | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 205MB |
| `observability.no-event-retention.cluster` | high |  | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 251 days past |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | high |  | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling … |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.27, 24 h or the pod's life 0.26: throttled through the day |
| `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` | high |  | kernel log not read in this mode. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods. cAdvisor counter 0 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | high |  | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (6.3 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | high |  | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | high |  | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | high |  | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | high |  | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | high |  | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | high |  | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0 … |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | high |  | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-nlb.elb.us-east-1.amazonaws.com'], sourceRanges None … |

## 3. Changes since the previous run of this mode

Compared `2026-10-27T15-58-44` → `2026-11-05T17-01-11` (rubric 0.1.51 → 0.1.80).

- **New (28)**: `cost.idle-node.node-2-158` (warn/low), `cost.idle-node.node-2-64` (warn/low), `loki.request-errors.monitoring/statefulset/loki-stack` (warn/medium), `node.disk-usage.<ip>:9100:/` (warn/high), `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` (warn/medium), `resilience.n-plus-one.cluster` (warn/critical), `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` (warn/high), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` (fail/medium), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` (fail/medium), `resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend` (warn/high), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-4248d:runner` (fail/medium), `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-file-worker:file-worker` (fail/medium), `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-graph-worker:graph-worker` (fail/medium), `resources.node-memory-request-usage-gap.node-2-59` (fail/medium), `resources.node-memory-request-usage-gap.node-2-64` (fail/medium), `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` (warn/high), `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` (fail/high), `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` (fail/high), `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` (warn/medium), `scaling.hpa-flapping.prod-app-l-backend/hpa/keda-hpa-app-l-file-worker` (warn/medium), `traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend` (warn/medium), `traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana` (warn/medium), `traffic.ingress-p95-latency.prod-app-q/app-q-ai` (warn/medium), `traffic.pod-not-ready.kube-system/ebs-csi-node` (warn/medium), `traffic.pod-not-ready.monitoring/loki-stack-promtail` (warn/medium), `traffic.pod-not-ready.prod-app-l-backend/app-l-file-worker` (fail/medium), `traffic.pod-not-ready.prod-app-l-backend/app-l-graph-worker` (fail/medium), `vpccni.subnet-ips-low.subnet-a` (warn/high)
- **Resolved (24)**: `controlplane.apiserver-latency.LIST` (warn/medium), `controlplane.apiserver-latency.PATCH` (warn/medium), `cost.idle-node.node-1-4` (warn/low), `cost.idle-node.node-1-62` (warn/low), `events.tracked-warning-reasons.FreeDiskSpaceFailed` (fail/high), `hygiene.failed-pods-lingering.cluster` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `node.network-errors.<ip>:9100:eth0` (fail/medium), `observability.alert-firing-stale.KubePodNotReady/dev-app-o` (fail/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-r` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-l-backend` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/app-s-prod` (fail/medium), `resources.cpu-request-overprovisioned.prod-app-q/deploy/app-q-ai:ai` (warn/medium), `resources.cpu-throttling.monitoring/deploy/kube-prometheus-stack-operator:kube-prometheus-stack` (warn/high), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-lc4vw:runner` (fail/medium), `resources.large-request-binpacking.arc-runners/pod/self-hosted-arm64-8msc5-runner-qg8mg:runner` (fail/medium), `resources.large-request-binpacking.arc-runners/pod/self-hosted-arm64-8msc5-runner-wxs47:runner` (fail/medium), `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` (fail/high), `resources.node-memory-request-usage-gap.node-1-139` (warn/medium), `resources.oomkilled-repeated.monitoring/sts/loki-stack:loki` (warn/high), `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (warn/high), `traffic.alb-unhealthy-targets.prod-app-p/app-p-backend` (warn/high), `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend` (warn/medium), `vpccni.subnet-ips-low.subnet-b` (warn/high)
- **Changed (17)**: `resilience.prod-concentration.node-1-139` (['fail', 'warn']/['high', 'high']), `resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle` (['fail', 'warn']/['medium', 'medium']), `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['medium', 'medium']), `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['low', 'low']), `resources.node-request-usage-gap.node-1-62` (['warn', 'fail']/['medium', 'medium']), `resources.oomkilled.monitoring/sts/loki-stack:loki` (['fail', 'warn']/['high', 'high']), `tenancy.prod-without-quota.prod-app-r` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-q` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-m` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-o` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-l-backend` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-p` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-n` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.app-s-prod` (['warn', 'fail']/['medium', 'medium']), `tenancy.tenant-without-limitrange.prod-app-l-backend` (['warn', 'fail']/['medium', 'medium']), `traffic.alb-elb-5xx.k8s-shared-alb` (['warn', 'fail']/['medium', 'medium']), `traffic.db-exposed.nlb/acme-db-shared` (['fail', 'warn']/['high', 'high'])
- **Rename suspects (3)**: `None`, `None`, `None`
- **Objects**: added 17, removed 5, changed 19: `configmaps/kube-system/aws-load-balancer-controller-leader` metadata.resourceVersion, `configmaps/kube-system/extension-apiserver-authentication` metadata.resourceVersion, `deployments/dev-app-m/app-m-backend` spec.template, `deployments/dev-app-m/app-m-frontend` spec.template, `deployments/prod-app-q/app-q-ai` spec.template, `deployments/prod-app-q/app-q-backend` spec.template, `deployments/prod-app-q/app-q-studio` spec.template, `deployments/prod-app-q/app-q-web` spec.template, `deployments/prod-app-l-backend/app-l-backend` spec.template, `deployments/prod-app-l-backend/app-l-embedding-server` spec.template, `deployments/prod-app-l-backend/app-l-file-worker` spec.replicas,spec.template, `deployments/prod-app-l-backend/app-l-graph-worker` spec.replicas,spec.template
- **Warning events**: UpdateFailed +827 (ExternalSecret/database/mysql-app-n-secret), NetworkNotReady +20 (Pod/kube-system/ebs-csi-node-4kks6), FailedScheduling +15 (Pod/prod-app-l-backend/app-l-file-worker-db75d7fdc-9h5xx), FailedToUpdateEndpointSlices +10 (Service/kube-system/kube-prometheus-stack-kube-proxy), InstanceTerminating +6 (NodeClaim/build-arm64-gp64z), FailedDraining +5 (Node/node-2-115), Unhealthy +5 (Pod/prod-app-m/app-m-backend-7c46f75bf6-gvlh2), CgroupV1 +4 (Node/node-2-115), InvalidDiskCapacity +4 (Node/node-2-115)

### 3-0. Criteria changes, not cluster changes

These findings appeared, disappeared or changed because the checks did, not the cluster, and they are kept out of the lists above. Taken from `diff.json` `findings.criteria_changes`; the report writes them as a criteria change and never as a tool defect.


Checks from before rule hashes, under a different rubric version; their findings stay in the lists above marked `rule_known: false`, and the report reads these checks' notes: `controlplane.apiserver-latency`, `cost.idle-node`, `events.tracked-warning-reasons`, `hygiene.failed-pods-lingering`, `loki.request-errors`, `node.disk-usage`, `node.network-errors`, `observability.alert-firing-stale`, `resilience.db-probe-timeout`, `resilience.n-plus-one`, `resilience.prod-concentration`, `resilience.restarts-crashloop`, `resources.cpu-request-overprovisioned`, `resources.cpu-throttling`, `resources.large-request-binpacking`, `resources.memory-limit-near-p95`, `resources.memory-request-overprovisioned`, `resources.node-memory-request-usage-gap`, `resources.node-request-usage-gap`, `resources.oomkilled`, `resources.oomkilled-repeated`, `scaling.hpa-flapping`, `tenancy.prod-without-quota`, `tenancy.tenant-without-limitrange`, `traffic.alb-elb-5xx`, `traffic.alb-unhealthy-targets`, `traffic.db-exposed`, `traffic.ingress-5xx-ratio`, `traffic.ingress-p95-latency`, `traffic.pod-not-ready`, `vpccni.subnet-ips-low`
- **Persisted (Toil)**: 394 findings present in all 5 runs checked, 397 in 3 or more; top checks: `resources.cpu-request-overprovisioned` 36, `traffic.alb-deregistration-vs-grace` 28, `resilience.no-prestop` 21, `scaling.no-hpa-serving-prod` 21, `resilience.exec-probe` 17, `resilience.single-replica-in-prod` 16, `resources.memory-request-overprovisioned` 14, `scaling.hpa-never-scaled` 13

### 3-1. Why things changed

Between 2026-10-27 and 2026-11-05 the node count went from 8 to 10. Node node-1-4 left, and node-2-158 (build-arm64), node-2-59 and node-2-64 (default) joined on 2026-11-05. On 2026-11-05 between 06:49 and 07:58 UTC, Karpenter consolidated five short-lived spot nodes of the default pool and created two new ones for pending pods. That is when the 15 newest FailedScheduling events, for prod-app-l-backend/app-l-file-worker among others, and the NetworkNotReady events of the new nodes' ebs-csi-node pods appear. The app-l-file-worker HPA, driven by KEDA, changed its desired count 47 times in 7 days, which explains the not-ready minutes of the app-l workers. The share of prod pods on node-1-139 dropped from 62% to 45% because pods moved to the new app nodes, but the node itself stayed, blocked by the do-not-disrupt pod of app-m-admin since 2026-10-06. prod-app-q/app-q-ai rolled out ten times, revisions 27 to 36, and the three releases of 2026-11-02 are the ones whose pods were OOM-killed. argocd-application-controller was OOM-killed on 2026-10-30, its first OOM since 2026-05-12. UpdateFailed on ExternalSecret database/mysql-app-n-secret grew from 1728 to 2555 occurrences. The EKS platform version moved from eks.55 to eks.58. The checks were updated between the two runs (rubric 0.1.51 to 0.1.80), and 31 checks have no rule hash, so their new and resolved findings may partly come from the checks.

## 4. Detail per area

(daily mode: no per-area detail; see section 2 and `report.md`)

## 5. Absence list

| Finding | Status | Severity | Why it should exist | Proposal |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |
| `observability.no-slo.cluster` | warn | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `observability.no-event-retention.cluster` | fail | high | Kubernetes events are kept for only one hour by default. FailedScheduling, OOMKilling and Unhealthy from the night are gone by morning. The most undervalued material is lost. | Ship events to Loki or Elasticsearch with kubernetes-event-exporter. Alternatively, the promtail/alloy event source if Loki exists, or `[INPUT] kubernetes_events` with fluent-bit (detection … |
| `security.no-certificate-manager.cluster` | warn | medium | When TLS certificate renewal is manual, services keep going down from expiry. cert-manager (or ACM plus ALB on EKS) automates renewal. On EKS, ALBs using ACM certificates work without cert-manager … | Install cert-manager, or if ACM is in use, suppress this check in config.yaml with a reason. |
| `hygiene.no-progressive-delivery.cluster` | fail | info | A rolling update is "replace everything", so a defect in the new version reaches all traffic immediately. Without a canary tool (some traffic -> check metrics -> expand), deployment verification … | As services grow, automate canary judgment with Argo Rollouts (same ecosystem as Argo CD) + AnalysisTemplate (ALB 5xx, p95 Prometheus queries). |

Expected families missing (inventory): backup, event-retention, slo, certificates, progressive-delivery.

## 6. Suppressed, tool missing, not collected

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in daily mode 56: `resources.krr-recommendation`, `controlplane.webhook-call-failures`, `controlplane.controller-error-repeat`, `controlplane.apiserver-slow-traces`, `controlplane.authenticator-failures`, `node.kernel-oom-node-level`, `node.kernel-lockup`, `node.kernel-io-fs-errors`, `node.kernel-nic-events`, `node.conntrack-table-full`, `node.kernel-net-mem-pressure`, `node.cgroup-v1`, `node.sysctl-tuning`, `node.cri-not-ready`, `node.cri-exited-containers`, `node.pod-logs-large`, `node.pod-dir-large`, `node.service-restarts`, `node.reboot-required`, `node.os-updates-pending`, `node.kubelet-reserved-missing`, `node.kubelet-eviction-memory-missing`, `node.clock-unsynced-os`, `node.zombie-processes`, `node.os-not-collected`, `cost.idle-compute-high`, `cost.request-waste`, `security.imds-hop-limit`, `security.polaris-security-danger`, `hygiene.polaris-reliability-danger`, `hygiene.eks-upgrade-insight`, `hygiene.helm-release-not-deployed`, `hygiene.helm-release-stale`, `node.kubelet-api-qps-low`, `node.docker-and-containerd`, `node.container-writable-layer-large`, `node.large-images`, `eks.addon-outdated`, `eks.extended-support`, `eks.no-backup-policy`, `eks.service-quota-near-limit`, `ecr.scan-disabled`, `ecr.tag-mutable-prod`, `ecr.no-lifecycle-policy`, `ecr.stale-storage`, `ecr.dockerhub-dependency`, `ecr.pull-failures`, `ecr.no-replication`, `ecr.untagged-images`, `kubeproxy.node-cmd-unavailable`, `vpccni.node-ip-exhaustion`, `vpccni.max-pods-exceeds-ip-capacity`, `vpccni.prefix-delegation-off`, `vpccni.ec2-api-errors`, `vpccni.metrics-unreadable`, `vpccni.external-snat-off-with-private-routes`
- Skipped or errored 6: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `hygiene.deprecated-api` (skip: summary.hygiene.deprecated.items missing), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing), `observability.alert-metric-without-dashboard` (skip: nothing to judge: dashboards json not available), `storage.ebs-volume-io-saturated` (skip: nothing to judge: ebs not available)
- Judged in part 0 (some targets lacked what the rule needs; those are not judged, not passed): none

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 |  | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'cronjobs.batch', 'storageclasses.storage.k8s.io']); node-os (not collected in daily mode); kubelet-configz (not collected in daily mode); krr (not collected in daily mode); polaris (not collected in daily mode); pluto (not collected in daily mode); kubent (not collected in daily mode); helm-list (not collected in daily mode) |
| eks-platform | 29 |  | addon-versions (not collected in daily mode); cluster-versions (not collected in daily mode); insights (not collected in daily mode); route-tables (not collected in daily mode); controlplane-logs (not collected in daily mode); kubelet-journal (not collected in daily mode); containerd-journal (not collected in daily mode); dlm-policies (not collected in daily mode); backup-plans (not collected in daily mode); ec2-snapshots-30d (not collected in daily mode); ec2-instances-imds (not collected in daily mode); pod-identity-associations (not collected in daily mode); ec2-spot-prices (not collected in daily mode); pricing-ondemand (not collected in daily mode); ce-cost-30d (not collected in daily mode); service-quotas (not collected in daily mode); quota-usage (not collected in daily mode); ec2-root-volumes (not collected in daily mode); ebs-volume-metrics (not collected in daily mode) |
| actions-runner-controller | 0 |  | no collect.yaml (collector not implemented) |
| alb-controller | 1 |  |  |
| alertmanager | 4 |  |  |
| argocd | 3 |  |  |
| coredns | 1 |  |  |
| ebs-csi | 1 |  |  |
| ecr | 5 |  | registry (not collected in daily mode); scanning-configuration (not collected in daily mode); pull-through-cache (not collected in daily mode); images (not collected in daily mode); lifecycle-policy (not collected in daily mode) |
| external-dns | 0 |  | no collect.yaml (collector not implemented) |
| external-secrets | 1 |  |  |
| grafana | 5 |  | datasources (grafana_api_token missing); dashboards (grafana_api_token missing); dashboards-json (grafana_api_token missing) |
| karpenter | 1 |  |  |
| keda | 2 |  | operator-metrics (True) |
| kube-proxy | 2 |  | proxy-mode (not collected in daily mode) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| loki | 9 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| promtail | 0 |  | no collect.yaml (collector not implemented) |
| victoria-metrics | 0 |  | no collect.yaml (collector not implemented) |
| vpc-cni | 2 |  | ipamd-metrics (not collected in daily mode) |

498 commands, 151.3 s. Failed steps: 0

Commands that failed inside a step that still succeeded (run.log): 10: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

### 7-2. Checks evaluated

365 checks: disabled 2, done 299, llm 2, not-collected 56, skip 6. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.0, 23 files, 23768 lines scanned (components: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 28.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 66 | 2026-11-04T23:34:21Z , 2026-11-05T07:54:24Z | [pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:34:21.347410868Z … |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-04T08:48:29Z , 2026-11-04T08:48:29Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T08:48:29.881532186Z … |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-05T03:23:13Z , 2026-11-05T08:03:38Z | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:13.503404100Z W1105 03:23:13.503303       1 reflector.go:561] … |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 42 | 2026-11-04T09:02:26Z , 2026-11-05T07:55:11Z | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T09:02:26.073535127Z E1104 09:02:26.073405       1 scraper.go:149] "Failed to scrape node" … |
| karpenter.spot-interruption | karpenter | resilience | low | info | 2 | 2026-11-04T09:01:23Z , 2026-11-05T05:31:47Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T09:01:23.567148794Z … |

| Normalized message | Count | Files |
|---|---|---|
| grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=admin fromAlert=false t=<ts> level=error msg="Er | 12 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node node-2-64 | 10 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| kube-proxy \| "Kube-proxy configuration may be incomplete or incorrect" err="nodePortAddresses is unset; NodePort connections will be accepted on all loca | 3 | logs/pods/kube-proxy/kube-system_kube-proxy.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node node-<n> | 2 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| grafana \| logger=http.server t=<ts> level=error msg="Failed to parse user ID" error="identifier is not initialized" | 1 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |

### 7-4. Raw files the LLM read directly

- `inventory.json`
- `findings-draft.json`
- `diff.json`
- `summary.json`
- `events.json`
- `objects/pods.json`
- `objects/deployments.json`
- `objects/replicasets.apps.json`
- `objects/nodes.json`
- `objects/nodepools.karpenter.sh.json`
- `objects/nodeclaims.karpenter.sh.json`
- `objects/poddisruptionbudgets.policy.json`
- `objects/applications.argoproj.io.json`
- `objects/ingresses.networking.k8s.io.json`
- `objects/horizontalpodautoscalers.autoscaling.json`
- `objects/prometheuses.monitoring.coreos.com.json`
- `objects/prometheusrules.monitoring.coreos.com.json`
- `objects/configmaps.json`
- `metrics/memory_p95_7d_bytes.json`
- `metrics/container_memory_request_bytes.json`
- `metrics/oom_pods_7d.json`
- `~/.kubegap/snapshots/my-cluster/2026-10-27T15-58-44/findings-draft.json`
- `~/.kubegap/snapshots/my-cluster/2026-10-27T15-58-44/summary.json`

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `observability.no-slo.cluster` | warn | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] known issue #15 |
| `observability.no-symptom-alerts.cluster` | warn | critical | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 14. Symptom ratio 0.0. Symptom rules: [] |
| `resilience.n-plus-one.cluster` | warn | critical | Allocatable without the largest node node-1-139 (3.92 cores, 29.8GB): CPU 19.36 cores vs total requests 14.41 (OK), memory 52.1GB vs 51.5GB (OK). Pods on that node 33 (prod 20). Pods that fit on no other node []. Pools short of room: 32 pods limited to … |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | fail | high | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 194 occurrences total (90 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 41, 42, 45, 45, 0, 0, 0, 3, 0, 12, 0, 0, 15, 15], flat), first … |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 205MB |
| `observability.no-event-retention.cluster` | fail | high | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 251 days past |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | fail | high | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 4 |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.27, 24 h or the pod's life 0.26: throttled through the day |
| `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` | fail | high | kernel log not read in this mode. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods. cAdvisor counter 0 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | fail | high | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (6.3 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | fail | high | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | fail | high | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail | high | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-t-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | fail | high | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-q-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | fail | high | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-o-frontend'] |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | fail | high | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0, health check / expected codes 200, backends ['deployment/app-l-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | fail | high | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-nlb.elb.us-east-1.amazonaws.com'], sourceRanges None, security group open to 0.0.0.0/0 on 9094. DB port open to the internet by the … |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 115 occurrences total (40 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 6, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 6, 10, 10, 10, 0, 0, 0, 5, 4, 49, 0, 0, 9, 9], flat), first 2026-10-08T12:34:17Z last … |
| `events.tracked-warning-reasons.UpdateFailed` | warn | high | Operator reconcile failure (ExternalSecret etc.). 2556 occurrences total (1 events, trend over 37 snapshots [1483, 1486, 1492, 1495, 1496, 1517, 1521, 1535, 1538, 1541, 1546, 1548, 1550, 1551, 1552, 1561, 1564, 1565, 1569, 1570, 1572, 1584, 1593, 1596, 1624, 1632, 1632, 1637, 1638, 1639, 1726 … |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 66 occurrences (2026-11-04T23:34:21Z ~ 2026-11-05T07:54:24Z), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: ['[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:34:21.347410868Z … |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-04T08:48:29Z ~ 2026-11-04T08:48:29Z), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T08:48:29.881532186Z … |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.81 |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.79 |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.673 (limit 1536Mi), active series 200114, Prometheus container last terminated OOMKilled True (2026-10-06T12:32:06Z), restarts 1, OOMKilled containers in the monitoring namespace ['loki-stack-0/loki', 'prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7 … |
| `resilience.prod-concentration.node-1-139` | warn | high | Node node-1-139 (pool default, spot) holds prod pods 20/44 (0.45), 15 workloads: ['prod-app-r/app-r', 'prod-app-m/app-m-admin', 'prod-app-m/app-m-api', 'prod-app-m/app-m-backend' … |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn | high | ["pod app-m-frontend-67888bfd9-jpxzw: throttling ratio now 0.23, 24 h or the pod's life 0.23: throttled through the day, below the fail line", "pod app-m-frontend-67888bfd9-ncp94: throttling ratio now 0.00, 24 h or the pod's life 0.22: throttled through the day, below the fail line; no … |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7f6d6dc65b-lnmq4: throttling ratio now 0.10, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | warn | high | ["pod app-m-frontend-6d7ff4dcdb-qfmxq: throttling ratio now 0.19, 24 h or the pod's life 0.24: throttled through the day, below the fail line", "pod app-m-frontend-6d7ff4dcdb-tzwjn: throttling ratio now 0.15, 24 h or the pod's life 0.22: throttled through the day, below the fail line"] |
| `resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7d5fc5c884-hrllj: throttling ratio now 0.15, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` | warn | high | kernel log not read in this mode. Prometheus: 1 pod ended by OOM in 7 days, 1 restarts in those pods. cAdvisor counter 1 |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | warn | high | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (11.6 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `traffic.db-exposed.nlb/acme-db-shared` | warn | high | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 3307, 3308, 3309, 3310, 3311, 5432, 5433, 6379, 7687], exposure internet-facing, addresses ['nlb-db-shared.elb.us-east-1.amazonaws.com'], sourceRanges None, security group allow-list, at most 4 sources per … |
| `vpccni.subnet-ips-low.subnet-a` | warn | high | subnet subnet-a (acme-vpc-eks-private-us-east-1c, us-east-1c, <ip>/24): free IPs 61/251 (used 0.757), 6 nodes in this AZ |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 12/12 (prod 8) |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-1a', 'gp3-1c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-1a', 'gp3-1c'] |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eks.nodegroup-ami-old.nodegroups` | fail | medium | node groups 1, max AMI age 331 days, over 90 days ['system_core-20251217040546303900000001 331d'], over 180 days ['system_core-20251217040546303900000001'], health issues [] |
| `eks.ssm-unregistered.node-1-117` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eks.ssm-unregistered.node-2-60` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 30008 / errors 2555 (ratio 0.0785), sync failures 2555/68694, reconcile errors 2555, ExternalSecrets not Ready ['database/externalsecret/mysql-app-n-secret'] (oldest refresh 7755.0 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2603, {'101': 4, '200': 2267, '400': 6, '429': 326}), ('Prometheus(prometheus)', 1534, {'200': 1349, '301': 185}), ('VictoriaMetrics_onprem(prometheus)', 141, {'200': 141})], error rate 1% or more ['Loki(loki)'] (max 0.1252), Grafana … |
| `hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 57.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 57.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodNotReady` | fail | medium | 7d firing samples 47752 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 139 pods Running for over 1h, 57 are absent from Loki pod labels (ratio 0.41). Nodes with every pod missing: ['node-2-158']. By namespace: {'kube-system': 21, 'monitoring': 14, 'prod-app-l-backend': 3, 'argocd': 2, 'dev-app-o': 2, 'dev-app-n': 2, 'keda' … |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret` | fail | medium | Ready=False (SecretSyncedError) for 7761.6 hours: could not get secret data from provider |
| `resilience.db-probe-timeout.prod-app-m/statefulset/app-m-backend-mysql:mysql` | fail | medium | prod-app-m/statefulset/app-m-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-o/statefulset/app-o-backend-mysql:mysql` | fail | medium | prod-app-o/statefulset/app-o-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-l-backend/statefulset/app-l-neo4j:neo4j` | fail | medium | prod-app-l-backend/statefulset/app-l-neo4j container neo4j: liveness tcpSocket timeout 1s, period 30s, failureThreshold 3, readiness tcpSocket timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | fail | medium | prod-app-n/statefulset/app-n-backend-prod-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.no-pdb.prod-app-o/app-o-ai` | fail | medium | replicas 3, no PDB selects these pods |
| `resilience.no-pdb.prod-app-o/app-o-backend` | fail | medium | replicas 2, no PDB selects these pods |
| `resilience.no-readiness-probe.prod-app-o/app-o-admin` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-o/app-o-ai` | fail | medium | containers without a readinessProbe: ai |
| `resilience.no-readiness-probe.prod-app-o/app-o-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-o/app-o-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.prod-app-l-backend/tts-proxy` | fail | medium | containers without a readinessProbe: tailscale, forwarder |
| `resilience.no-readiness-probe.prod-app-n/app-n-admin-frontend` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-n/app-n-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-n/app-n-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.app-s-prod/app-s-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.app-s-prod/app-s-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend` | fail | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api` | fail | medium | replicas 2, AZ distribution {'us-east-1a': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend` | fail | medium | replicas 2, AZ distribution {'us-east-1a': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend` | fail | medium | replicas 2, AZ distribution {'us-east-1a': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend` | fail | medium | replicas 2, AZ distribution {'us-east-1a': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server` | fail | medium | replicas 2, AZ distribution {'us-east-1a': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.single-node-dependency.prod-app-l-backend/deployment/tts-proxy` | fail | medium | ["hostPath volume ['dev-net-tun']"], replicas 1 |
| `resilience.single-replica-in-prod.prod-app-q/app-q-ai` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-q/app-q-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-q/app-q-studio` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-q/app-q-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-m/app-m-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-o/app-o-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-o/app-o-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-l-backend/app-l-pg-proxy` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-l-backend/tts-proxy` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-p/app-p-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-p/app-p-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-n/app-n-admin-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-n/app-n-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-n/app-n-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-s-prod/app-s-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-s-prod/app-s-frontend` | fail | medium | replicas 1, no HPA |
| `resources.besteffort-in-prod.prod-app-l-backend/deploy/tts-proxy` | fail | medium | pod tts-proxy-7b6db97b69-4bbjf: QoS BestEffort (neither request nor limit) |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` | fail | medium | ['pod app-l-backend-78679bf4b-lhhg4: 7d CPU p95 0.003 cores / request 0.50 cores = 0.01', 'pod app-l-backend-78679bf4b-mbnjd: 7d CPU p95 0.003 cores / request 0.50 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-8445d87f5-dwqrx: 7d CPU p95 0.006 cores / request 0.50 cores = 0.01', 'pod app-l-embedding-server-8445d87f5-jfv9l: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00'] |
| `resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter` | fail | medium | middleware/statefulset/kafka-controller container jmx-exporter (jmx-exporter:0.20.0-debian-11-r4): -Xmx NoneMiB, MaxRAMPercentage 100.0, memory limit 128.0MiB -> heap/limit 1.0 (heap unset False) |
| `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-4248d:runner` | fail | medium | pod self-hosted-arm64-8msc5-runner-4248d: request is 104% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-8445d87f5-dwqrx: request is 59% of the median node allocatable', 'pod app-l-embedding-server-8445d87f5-jfv9l: request is 59% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-file-worker:file-worker` | fail | medium | pod app-l-file-worker-db75d7fdc-f7tm4: request is 52% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-graph-worker:graph-worker` | fail | medium | pod app-l-graph-worker-d57c9ff8b-xwvfq: request is 52% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | medium | pod app-l-neo4j-0: request is 59% of the median node allocatable |
| `resources.no-memory-limit.prod-app-l-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-memory-request-usage-gap.node-2-59` | fail | medium | memory requests/allocatable 0.85, working set/allocatable 7d p95 0.33 (instant 0.27) |
| `resources.node-memory-request-usage-gap.node-2-64` | fail | medium | memory requests/allocatable 0.85, working set/allocatable 7d p95 0.27 (instant 0.26) |
| `resources.node-request-usage-gap.node-1-117` | fail | medium | CPU requests/allocatable 0.96, usage/allocatable 7d p95 0.09 (5m instant 0.09) |
| `resources.node-request-usage-gap.node-1-139` | fail | medium | CPU requests/allocatable 0.92, usage/allocatable 7d p95 0.05 (5m instant 0.18) |
| `resources.node-request-usage-gap.node-1-62` | fail | medium | CPU requests/allocatable 0.87, usage/allocatable 7d p95 0.06 (5m instant 0.42) |
| `resources.node-request-usage-gap.node-2-60` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.06) |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node node-1-139 (r8gd.xlarge spot): age 1022.6h, 302.6h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 21327}. do-not-disrupt pods on this node 1: prod-app-m/app-m-admin-57f5fcc58d-khsh5 |
| `security.externalsecret-not-ready.database/mysql-app-n-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.networkpolicy-coverage.cluster` | fail | medium | 18 of 21 user namespaces have no NetworkPolicy, of which production ['prod-app-r', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-n']; with: ['prod-app-q', 'prod-app-p', 'app-s-prod'] |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days 0 {}, prod PVCs 7 |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-1a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-1c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.burst-tenant-unbounded.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): 7d CPU median 0.011 cores, p95 0.026 cores, max 3.905 cores = 352.3x the median. No quota, shares nodes with prod True, nodes {'node-1-139': 4, 'node-2-135': 3 … |
| `tenancy.prod-boundary-missing.prod-app-r` | fail | medium | prod-app-r: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-m` | fail | medium | prod-app-m: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-o` | fail | medium | prod-app-o: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-l-backend` | fail | medium | prod-app-l-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-n` | fail | medium | prod-app-n: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.prod-app-r` | fail | medium | prod-app-r (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 0.004 cores (cluster share 0.003), memory p95 0.2GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-q` | fail | medium | prod-app-q (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 0.009 cores (cluster share 0.008), memory p95 0.93GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-m` | fail | medium | prod-app-m (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 0.109 cores (cluster share 0.088), memory p95 1.88GB, 7d max/median 1.5x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-o` | fail | medium | prod-app-o (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 0.037 cores (cluster share 0.03), memory p95 2.8GB, 7d max/median 2.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): no ResourceQuota. Pods 11, CPU requests total 4.72 cores, memory requests total 18.53GB, 7d CPU p95 0.026 cores (cluster share 0.021), memory p95 9.62GB, 7d max/median 352.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-p` | fail | medium | prod-app-p (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.006 cores (cluster share 0.005), memory p95 0.74GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-n` | fail | medium | prod-app-n (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.024 cores (cluster share 0.019), memory p95 1.0GB, 7d max/median 4.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.app-s-prod` | fail | medium | app-s-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 0.023 cores (cluster share 0.018), memory p95 0.5GB, 7d max/median 2.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.tenant-without-limitrange.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 11). 7d CPU p95 0.026 cores, memory p95 9.62GB |
| `traffic.alb-elb-5xx.k8s-shared-alb` | fail | medium | ALB k8s-shared-alb (internet-facing): 24h requests 205586.0, ELB 5xx 168.0, target 5xx 770.0, rejected connections 0, idle timeout 300s, target groups 40 |
| `traffic.ingress-p95-latency.prod-app-m/app-m-api` | fail | medium | ['canary-api-v1.example-b.ai', 'api.v1.example-b.ai']: p95 request-weighted 14.9046s, hourly average 16.7739s, 1h max 53.064s, latest hour with requests 16.5933s on 3.0 requests at 2026-11-05T07:02, 1287.0 requests/24h (source alb-cloudwatch) |
| `traffic.pod-not-ready.prod-app-l-backend/app-l-file-worker` | fail | medium | 24h minimum Ready ratio 0.875 (pod app-l-file-worker-db75d7fdc-f7tm4, about 180 min not ready), pods below 0.99 1, Unhealthy events 2 |
| `traffic.pod-not-ready.prod-app-l-backend/app-l-graph-worker` | fail | medium | 24h minimum Ready ratio 0.8889 (pod app-l-graph-worker-d57c9ff8b-xwvfq, about 160 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.shared-alb-group.alb-group/acme-prod-lb` | fail | medium | ALB group acme-prod-lb: 40 ingresses, 47 hosts, 15 namespaces ['argocd', 'dev-app-m', 'dev-app-o', 'dev-app-n', 'dev-app-t', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p' … |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `albctl.tgb-stale-or-orphan.cluster` | warn | medium | TargetGroupBindings 51 (targetType {'ip': 51}), generation lagging [], Service missing [], hand-made TGBs 9, target groups without a binding (traffic section) 1 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.my-cluster |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version … |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.513, queries per second 79.28, NXDOMAIN share of queries forwarded upstream 0.482 (upstreams ['<ip>:53']), pods with default ndots (5) 157, autopath False, cache hit ratio 0.9053 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.acme.ai/role` | warn | medium | Label acme.ai/role: 33 workloads (production 8) depend on it via nodeSelector/affinity, present on 5/10 nodes — e.g. argocd/deployment/argocd-applicationset-controller, argocd/deployment/argocd-dex-server, argocd/deployment/argocd-notifications-controller |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 38 workloads (production 25) depend on it via nodeSelector/affinity, present on 5/10 nodes — e.g. dev-app-m/deployment/app-m-admin, dev-app-m/deployment/app-m-api, dev-app-m/deployment/app-m-backend |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 31.3s (8485 pods), node termination average 15.1s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-o/scaledobject/app-o-ai-kafka-lag', 'prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-05T03:23:13Z ~ 2026-11-05T08:03:38Z), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:13.503404100Z W1105 03:23:13.503303       1 … |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 42 occurrences (2026-11-04T09:02:26Z ~ 2026-11-05T07:55:11Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T09:02:26.073535127Z E1104 09:02:26.073405       1 scraper.go:149] … |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | warn | medium | RSS 205MiB / limit 512Mi = 0.4, in-memory streams 66, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 1 5xx out of 5955681 requests since start (by route {'loki_api_v1_series': 1}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 10130, rejected {} |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerFailedReload', 'AlertmanagerMembersInconsistent', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown' … |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | dev-app-m/statefulset/app-m-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | dev-app-o/statefulset/app-o-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | warn | medium | dev-app-n/statefulset/app-n-backend-dev-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | dev-app-t/statefulset/app-t-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-postgres:postgres` | warn | medium | dev-app-t/statefulset/app-t-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` | warn | medium | monitoring/statefulset/loki-stack container loki: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 112, 'system-cluster-critical': 9, 'system-node-critical': 30}, prod pods without a class 44 of 44, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.cluster` | warn | medium | Of 17 DB workloads with a PVC, production DBs without a backup CronJob in the same namespace: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-m/statefulset/app-m-backend-mysql', 'prod-app-o/statefulset/app-o-backend-mysql' … |
| `resilience.recreate-strategy-serving.monitoring/deployment/vmauth` | warn | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master` | warn | medium | Containers whose command is sh -c ['redis', 'metrics'], no preStop, terminationGracePeriodSeconds 30 |
| `resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | medium | pod argocd-repo-server-d487895cc-bth22: 7d CPU p95 0.002 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller` | warn | medium | pod argocd-application-controller-0: 7d CPU p95 0.034 cores / request 0.20 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-api:api` | warn | medium | pod app-m-api-575d497d9b-5ttcv: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` | warn | medium | pod app-m-backend-76775dbdd-ttz69: 7d CPU p95 0.017 cores / request 0.10 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | medium | pod app-o-ai-7cdbdc7544-szzcl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | medium | pod app-o-backend-69dbdf4f65-9x6jc: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.10 cores = 0.09; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-n/deploy/app-n-backend:backend` | warn | medium | pod app-n-backend-7cfd8c975-b9p48: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13 |
| `resources.cpu-request-overprovisioned.dev-app-n/sts/app-n-backend-dev-mysql:mysql` | warn | medium | pod app-n-backend-dev-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-t/deploy/app-t-backend:backend` | warn | medium | pod app-t-backend-5ff4994f96-fxsr6: 7d CPU p95 0.001 cores / request 0.20 cores = 0.00 |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-mysql:mysql` | warn | medium | pod app-t-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | medium | pod app-t-postgres-0: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08; database-like: keep the request |
| `resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | medium | ['pod karpenter-9769889bd-pkxd2: 7d CPU p95 0.018 cores / request 0.20 cores = 0.09', 'pod karpenter-9769889bd-nphgs: 7d CPU p95 0.000 cores / request 0.20 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-7fc99cdd4d-jpng8: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-c5b6f8b88-jt7dp: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-54ffcbbfd6-2wtvl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/aws-load-balancer-controller:aws-load-balancer-controller` | warn | medium | ['pod aws-load-balancer-controller-dbcd6944f-svnmr: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02', 'pod aws-load-balancer-controller-dbcd6944f-psh2b: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | ['pod coredns-c7dbf4744-lz5fs: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07', 'pod coredns-c7dbf4744-cb76h: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-65d4b7df64-xxfjs: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05 |
| `resources.cpu-request-overprovisioned.kube-system/ds/kube-proxy:kube-proxy` | warn | medium | ['pod kube-proxy-d297j: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-snbf9: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-77wxc: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-4zj2m: 7d CPU p95 0.000 cores / request 0.10 cores = … |
| `resources.cpu-request-overprovisioned.middleware/deploy/kafka-ui:kafka-ui` | warn | medium | pod kafka-ui-7cb8bcb988-gls7p: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.middleware/sts/kafka-controller:kafka` | warn | medium | pod kafka-controller-0: 7d CPU p95 0.068 cores / request 0.20 cores = 0.34; database-like: keep the request |
| `resources.cpu-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana` | warn | medium | pod kube-prometheus-stack-grafana-7c9959564d-w8qx7: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.monitoring/sts/loki-stack:loki` | warn | medium | pod loki-stack-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07; database-like: keep the request |
| `resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | medium | pod vm-single-0: 7d CPU p95 0.001 cores / request 0.30 cores = 0.00; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | medium | pod app-q-backend-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.011 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | medium | ['pod app-o-backend-596479b6f8-cx44t: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod app-o-backend-596479b6f8-nv9j2: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.prod-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | medium | ['pod app-l-frontend-6d58bbfcfc-nfk9x: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod app-l-frontend-6d58bbfcfc-2qgs6: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | warn | medium | pod app-l-neo4j-0: 7d CPU p95 0.005 cores / request 0.50 cores = 0.01; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-p/sts/app-p-postgresql:postgresql` | warn | medium | pod app-p-postgresql-0: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-n/sts/app-n-backend-prod-mysql:mysql` | warn | medium | pod app-n-backend-prod-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend` | warn | medium | pod app-s-backend-6dd8fcbf96-nshrh: 7d CPU p95 0.014 cores / request 0.10 cores = 0.14 |
| `resources.cpu-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | medium | pod app-s-backend-postgresql-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07; database-like: keep the request |
| `resources.node-memory-request-usage-gap.node-1-241` | warn | medium | memory requests/allocatable 0.66, working set/allocatable 7d p95 0.33 (instant 0.34) |
| `resources.node-memory-request-usage-gap.node-2-135` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.42 (instant 0.42) |
| `resources.node-request-usage-gap.node-2-135` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.05 (5m instant 0.05) |
| `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` | warn | medium | 42 desired changes over 7 days |
| `scaling.hpa-flapping.prod-app-l-backend/hpa/keda-hpa-app-l-file-worker` | warn | medium | 47 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']. Share of containers allowing root 0.62 (28 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 88/93, of which 31 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-r/deployment/app-r', 'prod-app-q/deployment/app-q-ai', 'prod-app-q/deployment/app-q-backend' … |
| `storage.ebs-unencrypted.cluster` | warn | medium | 17 of 17 volumes unencrypted: ['vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0'] |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-n/data-app-n-backend-prod-mysql-0', 'prod-app-m/data-app-m-backend-mysql-0', 'prod-app-l-backend/data-app-l-neo4j-0', 'app-s-prod/data-app-s-backend-postgresql-0', 'prod-app-p/data-app-p-postgresql-0' … |
| `tenancy.prod-boundary-missing.prod-app-q` | warn | medium | prod-app-q: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-p` | warn | medium | prod-app-p: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.app-s-prod` | warn | medium | app-s-prod: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 1, CPU requests total 2.0 cores, memory requests total 4.0GB, 7d CPU p95 0.471 cores (cluster share 0.384), memory p95 1.96GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-m` | warn | medium | dev-app-m (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 0.052 cores (cluster share 0.042), memory p95 0.86GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-o` | warn | medium | dev-app-o (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 2.25GB, 7d CPU p95 0.035 cores (cluster share 0.028), memory p95 1.4GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-n` | warn | medium | dev-app-n (dev): no ResourceQuota. Pods 4, CPU requests total 0.3 cores, memory requests total 1.0GB, 7d CPU p95 0.024 cores (cluster share 0.02), memory p95 0.95GB, 7d max/median 1.5x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-t` | warn | medium | dev-app-t (dev): no ResourceQuota. Pods 4, CPU requests total 0.55 cores, memory requests total 1.88GB, 7d CPU p95 0.017 cores (cluster share 0.014), memory p95 0.85GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.node-1-117` | warn | medium | Node node-1-117 (pool system_core-20251217040546303900000001): tenant kinds ['dev', 'prod'], namespaces ['kube-system', 'keda', 'monitoring', 'argocd', 'dev-app-o', 'dev-app-t']. Memory limit total 11.6GB / allocatable 6.9GB = 1.68x, request total 4.7GB … |
| `tenancy.shared-node-limit-overcommit.node-1-139` | warn | medium | Node node-1-139 (pool default): tenant kinds ['dev', 'prod'], namespaces ['prod-app-o', 'dev-app-m', 'dev-app-o', 'prod-app-m', 'prod-app-l-backend', 'dev-app-n']. Memory limit total 46.1GB / allocatable 29.8GB = 1.55x, request total 18.8GB … |
| `tenancy.shared-node-limit-overcommit.node-2-218` | warn | medium | Node node-2-218 (pool system-ondemand): tenant kinds ['dev', 'other', 'prod'], namespaces ['monitoring', 'arc-system', 'argocd', 'dev-app-t', 'keda', 'kube-system']. Memory limit total 5.0GB / allocatable 3.2GB = 1.55x, request total 1.7GB, containers … |
| `tenancy.tenant-without-limitrange.arc-runners` | warn | medium | arc-runners (ci): no LimitRange, containers without requests 1 / without a memory limit 1 (pods 1). 7d CPU p95 0.471 cores, memory p95 1.96GB |
| `traffic.alb-deregistration-vs-grace.argocd/argocd-server` | warn | medium | Target group k8s-app-svc-74c4dcbda2: deregistration_delay 300s, backends ['deployment/argocd-server'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.dev-app-n/app-n-admin-frontend` | warn | medium | Target group k8s-app-svc-ae7a7a06ff: deregistration_delay 300s, backends ['deployment/app-n-admin-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.dev-app-n/app-n-backend` | warn | medium | Target group k8s-app-svc-0987e78003: deregistration_delay 300s, backends ['deployment/app-n-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.dev-app-n/app-n-frontend` | warn | medium | Target group k8s-app-svc-133751726c: deregistration_delay 300s, backends ['deployment/app-n-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.dev-app-t/app-t-backend` | warn | medium | Target group k8s-app-svc-b347218b4f: deregistration_delay 300s, backends ['deployment/app-t-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.dev-app-t/app-t-frontend` | warn | medium | Target group k8s-app-svc-e9834ca5fe: deregistration_delay 300s, backends ['deployment/app-t-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.middleware/kafka-ui` | warn | medium | Target group k8s-app-svc-0a6256c8b2: deregistration_delay 300s, backends ['deployment/kafka-ui'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.middleware/redis-insight` | warn | medium | Target group k8s-app-svc-e7e7fd218a: deregistration_delay 300s, backends ['deployment/redis-insight'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.monitoring/kube-prometheus-stack-grafana` | warn | medium | Target group k8s-app-svc-af0f3aa6c7: deregistration_delay 300s, backends ['deployment/kube-prometheus-stack-grafana'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.monitoring/vmauth` | warn | medium | Target group k8s-app-svc-e07e5153ee: deregistration_delay 300s, backends ['deployment/vmauth'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-r/app-r` | warn | medium | Target group k8s-app-svc-e238817282: deregistration_delay 300s, backends ['deployment/app-r'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-q/app-q-ai` | warn | medium | Target group k8s-app-svc-fc2d368787: deregistration_delay 300s, backends ['deployment/app-q-ai'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-q/app-q-backend` | warn | medium | Target group k8s-app-svc-bb495c72c8: deregistration_delay 300s, backends ['deployment/app-q-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-q/app-q-studio` | warn | medium | Target group k8s-app-svc-57e5adf3bf: deregistration_delay 300s, backends ['deployment/app-q-studio'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-q/app-q-web` | warn | medium | Target group k8s-app-svc-022a51fc31: deregistration_delay 300s, backends ['deployment/app-q-web'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-o/app-o-admin` | warn | medium | Target group k8s-app-svc-37417ab44f: deregistration_delay 300s, backends ['deployment/app-o-admin'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-o/app-o-ai` | warn | medium | Target group k8s-app-svc-b22674073c: deregistration_delay 300s, backends ['deployment/app-o-ai'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-o/app-o-backend` | warn | medium | Target group k8s-app-svc-89a3732998: deregistration_delay 300s, backends ['deployment/app-o-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-o/app-o-frontend` | warn | medium | Target group k8s-app-svc-032c25d752: deregistration_delay 300s, backends ['deployment/app-o-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-backend` | warn | medium | Target group k8s-app-svc-8c88bb317a: deregistration_delay 300s, backends ['deployment/app-l-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-frontend` | warn | medium | Target group k8s-app-svc-9726e5b1d3: deregistration_delay 300s, backends ['deployment/app-l-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-p/app-p-backend` | warn | medium | Target group k8s-app-svc-f68effe430: deregistration_delay 300s, backends ['deployment/app-p-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-p/app-p-web` | warn | medium | Target group k8s-app-svc-194ae69849: deregistration_delay 300s, backends ['deployment/app-p-web'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-n/app-n-admin-frontend` | warn | medium | Target group k8s-app-svc-d0c066d282: deregistration_delay 300s, backends ['deployment/app-n-admin-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-n/app-n-backend` | warn | medium | Target group k8s-app-svc-7df87a92cc: deregistration_delay 300s, backends ['deployment/app-n-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-n/app-n-frontend` | warn | medium | Target group k8s-app-svc-36f816b829: deregistration_delay 300s, backends ['deployment/app-n-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.app-s-prod/app-s-backend` | warn | medium | Target group k8s-app-svc-bea446d347: deregistration_delay 300s, backends ['deployment/app-s-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.app-s-prod/app-s-frontend` | warn | medium | Target group k8s-app-svc-e72ef00971: deregistration_delay 300s, backends ['deployment/app-s-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.my-cluster']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-m/app-m-admin` | warn | medium | ingress ['admin-dev.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-o/app-o-admin` | warn | medium | ingress ['admin-dev.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin-dev.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-m/app-m-admin` | warn | medium | ingress ['canary-admin.example-b.ai', 'admin.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-o/app-o-admin` | warn | medium | ingress ['admin.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend` | warn | medium | ['canary-api.example-b.ai', 'api.example-b.ai']: 24h 5xx 663.0 of 95751.0 requests = 0.69% (source alb-cloudwatch), p95 max 0.4879s |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend` | warn | medium | ['canary.example-b.ai', 'www.example-b.ai']: 24h 5xx 80.0 of 54895.0 requests = 0.15% (source alb-cloudwatch), p95 max 0.7156s |
| `traffic.ingress-5xx-ratio.prod-app-n/app-n-frontend` | warn | medium | ['example-c.ai', 'www.example-c.ai']: 24h 5xx 26.0 of 9883.0 requests = 0.26% (source alb-cloudwatch), p95 max 2.3884s |
| `traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana` | warn | medium | ['monitor.my-cluster']: p95 request-weighted 2.5054s, hourly average 0.9895s, 1h max 5.8148s, latest hour with requests 0.0235s on 2.0 requests at 2026-11-05T04:02, 3 hours before the newest hour, no requests since, 56.0 requests/24h (under 100 requests a day: warn only) (source alb-cloudwatch) |
| `traffic.ingress-p95-latency.prod-app-q/app-q-ai` | warn | medium | ['app-q-ai.my-cluster']: p95 request-weighted 2.3216s, hourly average 2.4097s, 1h max 2.6742s, latest hour with requests 2.1453s on 10.0 requests at 2026-11-05T07:02, 15.0 requests/24h (under 100 requests a day: warn only) (source alb-cloudwatch) |
| `traffic.pod-not-ready.arc-runners/self-hosted-arm64-8msc5-runner` | warn | medium | 24h minimum Ready ratio 0.9862 (pod self-hosted-arm64-8msc5-runner-4248d, about 20 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.kube-system/ebs-csi-node` | warn | medium | 24h minimum Ready ratio 0.9375 (pod ebs-csi-node-f9n5j, about 90 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.monitoring/loki-stack-promtail` | warn | medium | 24h minimum Ready ratio 0.9375 (pod loki-stack-promtail-zgjxk, about 90 min not ready), pods below 0.99 2, Unhealthy events 0 |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 111 (0.009), without one in prod 33. emptyDirs without sizeLimit 21 (prod: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-l-backend/deployment/app-l-embedding-server', 'prod-app-l-backend/deployment/tts-proxy' … |
| `hygiene.old-replicasets.cluster` | fail | low | Of 418 ReplicaSets, 351 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 61, '3': 6} |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend` | fail | low | HPA prod-app-l-backend/app-l-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 20.2 days ago |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-frontend` | fail | low | HPA prod-app-l-backend/app-l-frontend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 1% / target 70%, metrics ['cpu'], last scale 87.4 days ago |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `tenancy.dev-shares-prod-nodes.node-1-117` | fail | low | Node node-1-117 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-o', 'app-s-prod']) together with dev pods 2 (['dev-app-o', 'dev-app-t']). Memory limit total/allocatable 1.68, CPU limit total/allocatable 3.37, containers without a … |
| `tenancy.dev-shares-prod-nodes.node-1-139` | fail | low | Node node-1-139 (pool default): prod pods 20 (['prod-app-r', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']) together with dev pods 12 (['dev-app-m', 'dev-app-o', 'dev-app-n' … |
| `tenancy.dev-shares-prod-nodes.node-2-218` | fail | low | Node node-2-218 (pool system-ondemand): prod pods 1 (['prod-app-q']) together with dev pods 1 (['dev-app-t']). Memory limit total/allocatable 1.55, CPU limit total/allocatable 1.55, containers without a memory limit 2 |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 241005, top [['Elastic Load Balancing v2/DescribeTargetHealth', 75710], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 42892], ['EC2/DescribeInstances', 38529], ['EC2/DescribeSecurityGroups', 24893], ['Elastic Load Balancing v2/RegisterTargets' … |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster disabled (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 8, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 8, apps whose targetRevision is a branch or HEAD 8 ['argocd/application/app-r-prod', 'argocd/application/app-q-prod', 'argocd/application/app-m-prod', 'argocd/application/app-o-prod', 'argocd/application/app-s-prod', 'argocd/application/app-l-backend-prod' … |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.5, cluster IPv6 False, queries per second 79.28. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-node.node-2-158` | warn | low | Node node-2-158 (c6gn.xlarge, pool build-arm64): CPU p95 0.02497745825366951, memory p95 0.1941742880824938, None USD/month |
| `cost.idle-node.node-2-64` | warn | low | Node node-2-64 (c9g.large, pool default): CPU p95 0.030197817898433652, memory p95 0.26792339247832986, None USD/month |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | controller EC2 API request series 0, driver 1.37.0 (add-on v1.37.0-eksbuild.1). When enabled, shows EC2 API errors {} / throttles None |
| `eso.version-old.cluster` | warn | low | external-secrets 0.9.13 (ExternalSecrets 47, PushSecrets 0) |
| `grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana` | warn | low | Grafana 10.2.3 (database ok), ingress ['monitor.my-cluster'], dashboards 28 |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.unused-crds.cluster` | warn | low | 26 of 47 CRDs have zero objects (by group {'generators.external-secrets.io': 7, 'monitoring.coreos.com': 6, 'networking.k8s.aws': 4, 'eventing.keda.sh': 2, 'external-secrets.io': 3, 'keda.sh': 2, 'crd.k8s.amazonaws.com': 1, 'vpcresources.k8s.aws': 1}), 18 webhooks |
| `karpenter.spot-to-spot-consolidation-off.cluster` | warn | low | FEATURE_GATES {'Drift': 'true', 'SpotToSpotConsolidation': 'false'}, NodeClaims terminated by spot interruption 261, drift True |
| `keda.operator-metrics-disabled.cluster` | warn | low | --enable-prometheus-metrics False, operator keda_* metrics exposed False, scaler errors in logs (24h) 0 |
| `keda.scaledobject-never-active.cluster` | warn | low | inactive for more than 14 days ['dev-app-o/scaledobject/app-o-ai-kafka-lag'], not Ready [], fallback active [], scale-to-zero targets ['prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'] |
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 1355 packets (sum over nodes), services with externalTrafficPolicy Local 0, Services with a Local traffic policy and no endpoint on the node (max over nodes) 0 |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alerts-never-fired.cluster` | warn | low | 128 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 36 of 40 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-m', 'app-m-admin'), ('dev-app-m', 'app-m-api'), ('dev-app-m', 'app-m-backend'), ('dev-app-m', 'app-m-frontend'), ('dev-app-o', 'app-o-admin')]) … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"'])], receivers ['null', 'slack-sre', 'slack-system'], default receiver … |
| `observability.unclassified-errors.cluster` | warn | low | 28 unclassified error lines (23768 lines scanned, 23 files). Top: [('grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 unam', 12), ('ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver', 10), ('kube-proxy … |
| `observability.unstructured-logs.argocd` | warn | low | Of 18433 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-n` | warn | low | Of 59518 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.app-s-prod` | warn | low | Of 946512 lines in 1h, 0 parse as JSON (0.0) |
| `prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus StatefulSet replicas 1 (ready 1), restarts 1, started 2026-10-06T12:32:07.180790214Z |
| `prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus 2.49.1 — 2.53 is the last 2.x LTS (2024-07), 3.0 was released 2024-11 |
| `resilience.exec-probe.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-o/statefulset/app-o-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-t/statefulset/app-t-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-t/statefulset/app-t-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app_t -d … |
| `resilience.exec-probe.kube-system/daemonset/aws-node:aws-node` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s', 'port': None, 'timeout_s': 10, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s' … |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.middleware/statefulset/redis-master:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': 'sh -c /health/ping_liveness_local.sh 5', 'port': None, 'timeout_s': 6, 'period_s': 5, 'failure_threshold': 5, 'initial_delay_s': 20}, readiness {'type': 'exec' … |
| `resilience.exec-probe.prod-app-q/statefulset/app-q-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-q" -d "dbname=app-q" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.prod-app-m/statefulset/app-m-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-o/statefulset/app-o-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-l-backend/deployment/app-l-file-worker:file-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.FileWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.GraphWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-p/statefulset/app-p-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-p" -d "dbname=app-p" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.app-s-prod/statefulset/app-s-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-s-user" -d "dbname=app-s_tp" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-ai:ai` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-studio:studio` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-admin:admin` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-api:api` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-backend:backend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-l-backend/deployment/app-l-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-p/deployment/app-p-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 7860, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.prod-app-p/deployment/app-p-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.no-prestop.prod-app-r/app-r` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-q/app-q-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-q/app-q-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-q/app-q-studio` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-q/app-q-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-o/app-o-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-o/app-o-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-o/app-o-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-o/app-o-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-l-backend/app-l-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-l-backend/app-l-embedding-server` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-l-backend/app-l-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-l-backend/app-l-pg-proxy` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-l-backend/tts-proxy` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-p/app-p-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-p/app-p-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-n/app-n-admin-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-n/app-n-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-n/app-n-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-s-prod/app-s-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-s-prod/app-s-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | low | pod argocd-repo-server-d487895cc-bth22: 7d memory working set p95 92 MB / request 512 MB = 0.18 |
| `resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` | warn | low | pod app-m-backend-76775dbdd-ttz69: 7d memory working set p95 80 MB / request 256 MB = 0.31 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | low | pod app-o-ai-7cdbdc7544-szzcl: 7d memory working set p95 342 MB / request 1024 MB = 0.33 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | low | pod app-o-backend-69dbdf4f65-9x6jc: 7d memory working set p95 131 MB / request 512 MB = 0.26 |
| `resources.memory-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | low | pod app-t-postgres-0: 7d memory working set p95 28 MB / request 256 MB = 0.11; database-like: keep the request |
| `resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | low | pod karpenter-9769889bd-nphgs: 7d memory working set p95 24 MB / request 256 MB = 0.09 |
| `resources.memory-request-overprovisioned.middleware/sts/redis-master:redis` | warn | low | pod redis-master-0: 7d memory working set p95 5 MB / request 256 MB = 0.02; database-like: keep the request |
| `resources.memory-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | low | pod vm-single-0: 7d memory working set p95 165 MB / request 512 MB = 0.32; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | low | pod app-q-backend-postgresql-0: 7d memory working set p95 52 MB / request 256 MB = 0.20; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-ai:ai` | warn | low | ['pod app-o-ai-55b7448547-mzrjj: 7d memory working set p95 680 MB / request 2048 MB = 0.33', 'pod app-o-ai-55b7448547-mpj4r: 7d memory working set p95 411 MB / request 2048 MB = 0.20'] |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | low | ['pod app-o-backend-596479b6f8-cx44t: 7d memory working set p95 98 MB / request 512 MB = 0.19', 'pod app-o-backend-596479b6f8-nv9j2: 7d memory working set p95 81 MB / request 512 MB = 0.16'] |
| `resources.memory-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | low | ['pod app-l-frontend-6d58bbfcfc-nfk9x: 7d memory working set p95 79 MB / request 256 MB = 0.31', 'pod app-l-frontend-6d58bbfcfc-2qgs6: 7d memory working set p95 75 MB / request 256 MB = 0.29'] |
| `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | warn | low | pod app-l-neo4j-0: 7d memory working set p95 975 MB / request 4096 MB = 0.24; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | low | pod app-s-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.22; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-backend` | warn | low | HPA prod-app-l-backend/app-l-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-frontend` | warn | low | HPA prod-app-l-backend/app-l-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin` | warn | low | HPA dev-app-m/app-m-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 168.8 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api` | warn | low | HPA dev-app-m/app-m-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 198.5 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend` | warn | low | HPA dev-app-m/app-m-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 20% / target 70%, metrics ['cpu'], last scale 69.3 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin` | warn | low | HPA dev-app-o/app-o-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 58.4 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend` | warn | low | HPA dev-app-o/app-o-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 20.4 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend` | warn | low | HPA dev-app-o/app-o-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 20% / target 70%, metrics ['cpu'], last scale 20.4 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend` | warn | low | HPA dev-app-n/app-n-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 38.8 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend` | warn | low | HPA dev-app-n/app-n-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 14% / target 70%, metrics ['cpu'], last scale 42.8 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-frontend` | warn | low | HPA dev-app-n/app-n-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 3.3 days ago |
| `scaling.hpa-never-scaled.dev-app-t/deployment/app-t-backend` | warn | low | HPA dev-app-t/app-t-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 22.4 days ago |
| `scaling.hpa-never-scaled.dev-app-t/deployment/app-t-frontend` | warn | low | HPA dev-app-t/app-t-frontend: share of 15 days at min 1.00, min 1 max 2, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale None days ago |
| `scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-backend` | warn | low | HPA prod-app-l-backend/app-l-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-frontend` | warn | low | HPA prod-app-l-backend/app-l-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
| `scaling.no-hpa-serving-prod.prod-app-r/app-r` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-q/app-q-ai` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-q/app-q-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-q/app-q-studio` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-q/app-q-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-m/app-m-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-m/app-m-api` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-m/app-m-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-m/app-m-frontend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-o/app-o-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-o/app-o-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-o/app-o-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-l-backend/app-l-embedding-server` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-l-backend/tts-proxy` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-p/app-p-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-p/app-p-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-n/app-n-admin-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-n/app-n-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-n/app-n-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-s-prod/app-s-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-s-prod/app-s-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `tenancy.dev-shares-prod-nodes.node-1-62` | warn | low | Node node-1-62 (pool default): prod pods 13 (['prod-app-q', 'prod-app-m', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']) together with dev pods 1 (['dev-app-n']). Memory limit total/allocatable 0.88, CPU limit total/allocatable … |
| `tenancy.dev-shares-prod-nodes.node-2-60` | warn | low | Node node-2-60 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-m', 'prod-app-n']) together with dev pods 2 (['dev-app-m', 'dev-app-n']). Memory limit total/allocatable 1.49, CPU limit total/allocatable 2.44, containers … |
| `traffic.alb-protection-off.k8s-shared-alb` | warn | low | ALB k8s-shared-alb: deletion_protection False, access_logs False, target groups in the ingress group 40 |
| `vpccni.warm-pool-whole-eni.cluster` | warn | low | warm policy whole_eni (WARM_ENI_TARGET 1, WARM_IP_TARGET None), idle reserved IPs total 0, min subnet free 61, subnets below 25% free ['subnet-a'] |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |
| `hygiene.no-progressive-delivery.cluster` | fail | info | No progressive-delivery component (Argo Rollouts, Flagger). All deployments are rolling updates (replace everything) -- ALB weighted target groups are not used either |

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "symptom_ratio": 0.0,
 "by_class": {
  "app-cause": 5,
  "app": 14,
  "cause": 138
 },
 "symptom_rules": [],
 "alerting": 157
}
```

</details>
<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "autoscaler": true,
 "largest_node": "node-1-139",
 "memory_ok": true,
 "pools_short": [
  {
   "eligible_nodes": [
    "node-1-62",
    "node-2-59",
    "node-2-64"
   ],
   "pods": 32,
   "needed_cpu": 3.3,
   "free_cpu": 1.62,
   "needed_memory_gb": 18.62,
   "free_memory_gb": 8.61
  }
 ],
 "ok": false,
 "cpu_ok": true,
 "allocatable_memory_gb_without_largest": 52.1,
 "requests_memory_gb_total": 51.5,
 "requests_cpu_total": 14.41,
 "autoscaler_name": "karpenter",
 "allocatable_cpu_without_largest": 19.36,
 "tight": false,
 "largest_node_cpu": 3.92,
 "pods_on_largest_node": 33,
 "prod_pods_on_largest_node": 20,
 "karpenter": true,
 "largest_node_memory_gb": 29.8,
 "cannot_fit_elsewhere": [],
 "available": true
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.FailedScheduling</code></summary>

```json
{
 "per_snapshot": [
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  36,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  41,
  42,
  45,
  45,
  0,
  0,
  0,
  3,
  0,
  12,
  0,
  0,
  15,
  15
 ],
 "occurrences": 194,
 "type": "Warning",
 "first": "2026-10-25T03:33:08Z",
 "events": 90,
 "objects_top": [
  {
   "object": "Pod/prod-app-l-backend/app-l-backend-5c5c54d5dd-7phsx",
   "occurrences": 8
  },
  {
   "object": "Pod/prod-app-l-backend/app-l-embedding-server-577b67cff8-lrsfj",
   "occurrences": 8
  },
  {
   "object": "Pod/prod-app-p/app-p-backend-7799c489bd-4zh5b",
   "occurrences": 8
  },
  {
   "object": "Pod/dev-app-n/app-n-frontend-f7b9d96d4-r4svh",
   "occurrences": 8
  },
  {
   "object": "Pod/prod-app-m/app-m-backend-7c46f75bf6-gfggb",
   "occurrences": 8
  }
 ],
 "reason": "FailedScheduling",
 "severity_hint": "high",
 "meaning": "No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked",
 "last": "2026-11-05T07:54:59Z",
 "trend": "flat"
}
```

</details>
<details><summary><code>karpenter.ec2nodeclass-al2.cluster</code></summary>

```json
{
 "ami_families": [
  "AL2"
 ],
 "classes_al2": [
  "default"
 ],
 "classes_ami_unpinned": [
  "default"
 ],
 "ec2nodeclasses": 1
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.OOMKill</code></summary>

```json
{
 "symptom": "pods die and requests fail or slow down",
 "importance": "critical",
 "mode": "OOMKill"
}
```

</details>
<details><summary><code>observability.loki-oomkilled.cluster</code></summary>

```json
{
 "self_metrics": {
  "discarded_samples_since_start": {},
  "streams_in_memory": 66,
  "panics": 0,
  "lines_received_since_start": 253619086,
  "requests_5xx_since_start": 4,
  "rss_mb": 205,
  "process_uptime_h": 271.8
 },
 "storage": {
  "kind": "statefulset",
  "volumes": {
   "tmp": "emptyDir",
   "config": "secret",
   "storage": "emptyDir"
  },
  "volume_claim_templates": 0,
  "replicas": 1,
  "emptydir_data": true
 },
 "pods": [
  {
   "pod": "loki-stack-0",
   "container": "loki",
   "restarts": 1,
   "last_reason": "OOMKilled",
   "last_finished": "2026-10-25T00:15:41Z"
  }
 ],
 "oomkilled": true
}
```

</details>
<details><summary><code>observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "namespace": "monitoring",
 "name": "alertmanager-kube-prometheus-stack-alertmanager",
 "kind": "StatefulSet"
}
```

</details>
<details><summary><code>observability.stack-storage-emptydir.monitoring/loki-stack</code></summary>

```json
{
 "namespace": "monitoring",
 "name": "loki-stack",
 "kind": "StatefulSet"
}
```

</details>
<details><summary><code>platform.karpenter-version-compat.cluster</code></summary>

```json
{
 "k8s_minor": "1.32",
 "present": true,
 "version": "0.37.0",
 "compat_row": "0.37",
 "k8s_min_supported": "1.23",
 "k8s_max_supported": "1.30",
 "version_note": null,
 "k8s_supported": false
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-r/deployment/app-r</code></summary>

```json
{
 "single_eligible_node": false,
 "prod": true,
 "eligible_nodes": 4,
 "running": 2,
 "topology_spread": [],
 "workload": "prod-app-r/deployment/app-r",
 "zones": {
  "us-east-1a": 2
 },
 "anti_affinity": null,
 "nodes": {
  "node-1-139": 2
 },
 "all_same_node": true,
 "replicas": 2
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-o/deployment/app-o-ai</code></summary>

```json
{
 "single_eligible_node": false,
 "prod": true,
 "eligible_nodes": 4,
 "running": 3,
 "topology_spread": [],
 "workload": "prod-app-o/deployment/app-o-ai",
 "zones": {
  "us-east-1a": 3
 },
 "anti_affinity": null,
 "nodes": {
  "node-1-139": 3
 },
 "all_same_node": true,
 "replicas": 3
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-o/deployment/app-o-backend</code></summary>

```json
{
 "single_eligible_node": false,
 "prod": true,
 "eligible_nodes": 4,
 "running": 2,
 "topology_spread": [],
 "workload": "prod-app-o/deployment/app-o-backend",
 "zones": {
  "us-east-1a": 2
 },
 "anti_affinity": null,
 "nodes": {
  "node-1-139": 2
 },
 "all_same_node": true,
 "replicas": 2
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "single_eligible_node": false,
 "prod": true,
 "eligible_nodes": 4,
 "running": 2,
 "topology_spread": [],
 "workload": "prod-app-l-backend/deployment/app-l-frontend",
 "zones": {
  "us-east-1a": 2
 },
 "anti_affinity": "preferred",
 "nodes": {
  "node-1-139": 2
 },
 "all_same_node": true,
 "replicas": 2
}
```

</details>
<details><summary><code>resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "container": "prometheus"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.2627119784527423,
  "cpu_throttle_ratio_5m": 0.2672811059907834
 }
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai</code></summary>

```json
{
 "restarts_of_those_pods": 13,
 "pods_oomkilled": 3,
 "kernel_nodes_total": 2,
 "kernel_nodes_old_script": 0,
 "kernel_any_node_read": false,
 "cadvisor_oom_events_7d": 0,
 "kernel_kills_24h": 0,
 "target": "prod-app-q/deploy/app-q-ai:ai",
 "kernel_log_read": false,
 "pods_replaced": 3
}
```

</details>
<details><summary><code>resources.oomkilled.argocd/sts/argocd-application-controller:application-controller</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_container_status_last_terminated_reason",
  "container": "application-controller",
  "endpoint": "http",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "argocd",
  "pod": "argocd-application-controller-0",
  "reason": "OOMKilled",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "7e465a96-0e92-48b2-82ac-acd8c909f172"
 },
 "value": 1.0
}
```

</details>
<details><summary><code>security.networkpolicy-not-enforced.cluster</code></summary>

```json
{
 "policies": 3,
 "policies_but_not_enforced": true,
 "enforced": false,
 "enforcement": "aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints",
 "namespaces_with_policy": [
  "prod-app-q",
  "prod-app-p",
  "app-s-prod"
 ]
}
```

</details>
<details><summary><code>security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy</code></summary>

```json
{
 "severe": true,
 "system": false,
 "flags": [
  "hostPath ['dev-net-tun']",
  "capabilities [\"tailscale:['NET_ADMIN']\"]"
 ],
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "root_allowed_containers": [
  "tailscale",
  "forwarder"
 ]
}
```

</details>
<details><summary><code>storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0</code></summary>

```json
{
 "days_to_full": null,
 "inode_ratio": 0.0,
 "host_fs": false,
 "growth_gb_per_day": 0.0,
 "storage_class": "gp3",
 "used_ratio": 0.902,
 "capacity_gb": 9.7,
 "workloads": [
  "statefulset/app-t-mysql"
 ],
 "target": "dev-app-t/data-app-t-mysql-0",
 "metrics": true
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend</code></summary>

```json
{
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "name": "k8s-app-svc-133751726c",
 "lb_type": "application",
 "unhealthy_max_24h": 1.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ],
 "target": "dev-app-n/app-n-frontend",
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.dev-app-t/app-t-backend</code></summary>

```json
{
 "targets_total": 1,
 "port": 8000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 1
 },
 "name": "k8s-app-svc-b347218b4f",
 "lb_type": "application",
 "unhealthy_max_24h": 1.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 8000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ],
 "target": "dev-app-t/app-t-backend",
 "workloads": [
  "deployment/app-t-backend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-q/app-q-backend</code></summary>

```json
{
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 1
 },
 "name": "k8s-app-svc-bb495c72c8",
 "lb_type": "application",
 "unhealthy_max_24h": 1.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ],
 "target": "prod-app-q/app-q-backend",
 "workloads": [
  "deployment/app-q-backend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend</code></summary>

```json
{
 "targets_total": 1,
 "port": 3003,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "name": "k8s-app-svc-032c25d752",
 "lb_type": "application",
 "unhealthy_max_24h": 1.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3003,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ],
 "target": "prod-app-o/app-o-frontend",
 "workloads": [
  "deployment/app-o-frontend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend</code></summary>

```json
{
 "targets_total": 2,
 "port": 8000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 2
 },
 "name": "k8s-app-svc-8c88bb317a",
 "lb_type": "application",
 "unhealthy_max_24h": 2.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 8000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  },
  {
   "id": "<ip>",
   "port": 8000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ],
 "target": "prod-app-l-backend/app-l-backend",
 "workloads": [
  "deployment/app-l-backend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend</code></summary>

```json
{
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "name": "k8s-app-svc-36f816b829",
 "lb_type": "application",
 "unhealthy_max_24h": 1.0,
 "health_check": {
  "path": "/",
  "port": "traffic-port",
  "protocol": "HTTP",
  "interval_s": 15,
  "timeout_s": 5,
  "healthy_threshold": 2,
  "unhealthy_threshold": 2,
  "matcher": "200"
 },
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ],
 "target": "prod-app-n/app-n-frontend",
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "targets_healthy": 0
}
```

</details>
<details><summary><code>traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external</code></summary>

```json
{
 "open_ports": [
  9094
 ],
 "type": "loadbalancer",
 "hosts": [
  "k8s-app-svc-nlb.elb.us-east-1.amazonaws.com"
 ],
 "allowed_sources": {
  "9094": 1
 },
 "sg_exposure": "open",
 "name": "kafka-controller-0-external",
 "namespace": "middleware",
 "source_ranges": null,
 "scheme": "internet-facing",
 "target": "loadbalancer/middleware/kafka-controller-0-external",
 "ports": [
  9094,
  443
 ],
 "note": "DB port open to the internet by the security group"
}
```

</details>
<details><summary><code>controlplane.apiserver-5xx.cluster</code></summary>

```json
{
 "labels": {
  "code": "503"
 },
 "value": 0.003703703703703704
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.Unhealthy</code></summary>

```json
{
 "per_snapshot": [
  0,
  0,
  0,
  0,
  0,
  0,
  6,
  11,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  8,
  0,
  6,
  10,
  10,
  10,
  0,
  0,
  0,
  5,
  4,
  49,
  0,
  0,
  9,
  9
 ],
 "occurrences": 115,
 "type": "Warning",
 "first": "2026-10-08T12:34:17Z",
 "events": 40,
 "objects_top": [
  {
   "object": "Pod/middleware/kafka-exporter-78d46ff57f-dn65f",
   "occurrences": 49
  },
  {
   "object": "Pod/prod-app-m/app-m-backend-7c46f75bf6-gvlh2",
   "occurrences": 7
  },
  {
   "object": "Pod/monitoring/loki-stack-0",
   "occurrences": 6
  },
  {
   "object": "Pod/prod-app-r/app-r-dd59d5f64-nhjfl",
   "occurrences": 5
  },
  {
   "object": "Pod/prod-app-l-backend/app-l-embedding-server-577b67cff8-lrsfj",
   "occurrences": 4
  }
 ],
 "reason": "Unhealthy",
 "severity_hint": "medium",
 "meaning": "Probe failure. Readiness removes it from traffic, liveness restarts it",
 "last": "2026-11-05T08:08:48Z",
 "trend": "flat"
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.UpdateFailed</code></summary>

```json
{
 "per_snapshot": [
  1483,
  1486,
  1492,
  1495,
  1496,
  1517,
  1521,
  1535,
  1538,
  1541,
  1546,
  1548,
  1550,
  1551,
  1552,
  1561,
  1564,
  1565,
  1569,
  1570,
  1572,
  1584,
  1593,
  1596,
  1624,
  1632,
  1632,
  1637,
  1638,
  1639,
  1726,
  1728,
  2351,
  2492,
  2500,
  2555,
  2556
 ],
 "occurrences": 2556,
 "type": "Warning",
 "first": "2026-10-08T12:31:38Z",
 "events": 1,
 "objects_top": [
  {
   "object": "ExternalSecret/database/mysql-app-n-secret",
   "occurrences": 2556
  }
 ],
 "reason": "UpdateFailed",
 "severity_hint": "medium",
 "meaning": "Operator reconcile failure (ExternalSecret etc.)",
 "last": "2026-11-05T08:11:04Z",
 "trend": "up"
}
```

</details>
<details><summary><code>karpenter.ec2nodeclass-hardening.cluster</code></summary>

```json
{
 "classes_root_unencrypted": [
  "default"
 ],
 "classes_imds_tokens_optional": [],
 "root_volume_gb": {
  "default": 50.0
 },
 "classes_imds_hop_gt1": [
  "default"
 ]
}
```

</details>
<details><summary><code>logs.signatures.external-secrets.provider-error</code></summary>

```json
{
 "count": 66,
 "first": "2026-11-04T23:34:21Z",
 "last": "2026-11-05T07:54:24Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/external-secrets/external-secrets_external-secrets.log": 66
 },
 "samples": [
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:34:21.347410868Z {\"level\":\"error\",\"ts\":1793835261.3472605,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:34:21.357518677Z {\"level\":\"error\",\"ts\":1793835261.3574286,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:51:01.440615188Z {\"level\":\"error\",\"ts\":1793836261.4404976,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-04T23:51:01.450997080Z {\"level\":\"error\",\"ts\":1793836261.4508991,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:07:41.508869578Z {\"level\":\"error\",\"ts\":1793837261.5087564,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\""
 ]
}
```

</details>
<details><summary><code>logs.signatures.karpenter.version-unsupported</code></summary>

```json
{
 "count": 1,
 "first": "2026-11-04T08:48:29Z",
 "last": "2026-11-04T08:48:29Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/karpenter/karpenter_karpenter.log": 1
 },
 "samples": [
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T08:48:29.881532186Z {\"level\":\"ERROR\",\"time\":\"2026-11-04T08:48:29.881Z\",\"logger\":\"controller\",\"message\":\"failed validating kubernetes version\",\"commit\":\"490ef94\",\"controller\":\"nodeclass.s"
 ]
}
```

</details>
<details><summary><code>node.disk-usage.<ip>:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "<ip>:9100",
  "mountpoint": "/"
 },
 "value": 0.8080534466244725
}
```

</details>
<details><summary><code>node.disk-usage.<ip>:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "<ip>:9100",
  "mountpoint": "/"
 },
 "value": 0.7869442403379256
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.Scheduling failure</code></summary>

```json
{
 "symptom": "new pods do not start",
 "importance": "high",
 "mode": "Scheduling failure"
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.VPC CNI IP exhaustion</code></summary>

```json
{
 "symptom": "pods Pending without network",
 "importance": "high",
 "mode": "VPC CNI IP exhaustion"
}
```

</details>
<details><summary><code>prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "monitoring_oomkilled": [
  "loki-stack-0/loki",
  "prometheus-kube-prometheus-stack-prometheus-0/prometheus"
 ],
 "present": true,
 "rss_vs_limit": 0.673,
 "monitoring_restarts_7d": {},
 "head_series": 200114,
 "oomkilled_at": "2026-10-06T12:32:06Z",
 "restarts": 1,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "memory_limit": "1536Mi",
 "oomkilled_last": true
}
```

</details>
<details><summary><code>resilience.prod-concentration.node-1-139</code></summary>

```json
{
 "node": "node-1-139",
 "autoscaler": true,
 "share": 0.45,
 "pool": "default",
 "workload_count": 15,
 "prod_total": 44,
 "prod_workloads": [
  "prod-app-r/app-r",
  "prod-app-m/app-m-admin",
  "prod-app-m/app-m-api",
  "prod-app-m/app-m-backend",
  "prod-app-m/app-m-frontend",
  "prod-app-o/app-o-admin",
  "prod-app-o/app-o-ai",
  "prod-app-o/app-o-backend",
  "prod-app-o/app-o-frontend",
  "prod-app-l-backend/app-l-backend",
  "prod-app-l-backend/app-l-embedding-server",
  "prod-app-l-backend/app-l-frontend",
  "prod-app-p/app-p-backend",
  "prod-app-n/app-n-admin-frontend",
  "app-s-prod/app-s-backend"
 ],
 "capacity_type": "spot",
 "nodes_total": 10,
 "prod_pods": 20
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller</code></summary>

```json
{
 "last_reason": "OOMKilled",
 "last_finished": "2026-10-30T09:00:04Z",
 "cause": "OOM (memory limit)",
 "waiting": null,
 "unhealthy_events": 0,
 "pod": "argocd-application-controller-0",
 "crashloop": false,
 "node_rebooted_at": null,
 "namespace": "argocd",
 "exit_code": 137,
 "restarts": 42,
 "rebooted": false,
 "container": "application-controller"
}
```

</details>
<details><summary><code>resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "dev-app-m",
   "pod": "app-m-frontend-67888bfd9-jpxzw",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.23364401177034858,
   "cpu_throttle_ratio_5m": 0.2274678111587983
  }
 },
 {
  "labels": {
   "namespace": "dev-app-m",
   "pod": "app-m-frontend-67888bfd9-ncp94",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.21822541966426856
  }
 },
 {
  "labels": {
   "namespace": "dev-app-m",
   "pod": "app-m-frontend-67888bfd9-qv7nw",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.14972144846796656
  }
 },
 {
  "labels": {
   "namespace": "dev-app-m",
   "pod": "app-m-frontend-67888bfd9-w4ffr",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.13615023474178403
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-frontend-7f6d6dc65b-lnmq4",
  "container": "frontend"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.11540916634750414,
  "cpu_throttle_ratio_5m": 0.1037037037037037
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-m",
   "pod": "app-m-frontend-6d7ff4dcdb-qfmxq",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.24133405631389931,
   "cpu_throttle_ratio_5m": 0.18635170603674542
  }
 },
 {
  "labels": {
   "namespace": "prod-app-m",
   "pod": "app-m-frontend-6d7ff4dcdb-tzwjn",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.2215826171558294,
   "cpu_throttle_ratio_5m": 0.14522821576763484
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-o",
  "pod": "app-o-frontend-7d5fc5c884-hrllj",
  "container": "frontend"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.1179459201418488,
  "cpu_throttle_ratio_5m": 0.15384615384615383
 }
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller</code></summary>

```json
{
 "restarts_of_those_pods": 1,
 "pods_oomkilled": 1,
 "kernel_nodes_total": 1,
 "kernel_nodes_old_script": 0,
 "kernel_any_node_read": false,
 "cadvisor_oom_events_7d": 1,
 "kernel_kills_24h": 0,
 "target": "argocd/sts/argocd-application-controller:application-controller",
 "kernel_log_read": false,
 "pods_replaced": 0
}
```

</details>
<details><summary><code>resources.oomkilled.monitoring/sts/loki-stack:loki</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_container_status_last_terminated_reason",
  "container": "loki",
  "endpoint": "http",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "monitoring",
  "pod": "loki-stack-0",
  "reason": "OOMKilled",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "9bf247d9-dc5b-49b2-8e0a-c54039c4c301"
 },
 "value": 1.0
}
```

</details>
<details><summary><code>traffic.db-exposed.nlb/acme-db-shared</code></summary>

```json
{
 "type": "nlb (defined outside the cluster)",
 "hosts": [
  "nlb-db-shared.elb.us-east-1.amazonaws.com"
 ],
 "allowed_sources": {
  "3306": 4,
  "3307": 4,
  "3308": 4,
  "3309": 4,
  "3310": 4,
  "3311": 4,
  "5432": 4,
  "5433": 4,
  "6379": 1,
  "7687": 4
 },
 "sg_exposure": "allow-list",
 "name": "acme-db-shared",
 "namespace": null,
 "scheme": "internet-facing",
 "widest_prefix": {
  "3306": 32,
  "3307": 32,
  "3308": 32,
  "3309": 32,
  "3310": 32,
  "3311": 32,
  "5432": 32,
  "5433": 32,
  "6379": 32,
  "7687": 32
 },
 "target": "nlb/acme-db-shared",
 "ports": [
  3306,
  3307,
  3308,
  3309,
  3310,
  3311,
  5432,
  5433,
  6379,
  7687
 ],
 "note": "NLB created outside Kubernetes; 9 TargetGroupBindings bind it to dev-app-m/app-m-backend-mysql, dev-app-o/app-o-backend-mysql, dev-app-n/app-n-backend-dev-mysql, prod-app-q/app-q-backend-postgresql, prod-app-m/app-m-backend-mysql, prod-app-o/app-o-backend-mysql and 3 more. DB port on an external address, limited by the security group to listed addresses"
}
```

</details>
<details><summary><code>vpccni.subnet-ips-low.subnet-a</code></summary>

```json
{
 "cidr": "<ip>/24",
 "available_ratio": 0.243,
 "usable": 251,
 "subnet_id": "subnet-a",
 "name": "acme-vpc-eks-private-us-east-1c",
 "az": "us-east-1c",
 "nodes": 6,
 "used_ratio": 0.757,
 "available": 61
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 12,
 "default_project_apps": 12,
 "applications_prod": 8,
 "projects": 1,
 "wildcard_projects": [
  "default"
 ]
}
```

</details>
<details><summary><code>ebscsi.storageclass-unencrypted.cluster</code></summary>

```json
{
 "classes_no_expansion": [
  "gp2",
  "gp3",
  "gp3-1a",
  "gp3-1c"
 ],
 "classes_unencrypted": [
  "gp3",
  "gp3-1a",
  "gp3-1c"
 ],
 "classes_intree": [
  "gp2"
 ],
 "default_class": "gp3",
 "classes": 4
}
```

</details>
<details><summary><code>eks.nodegroup-ami-old.nodegroups</code></summary>

```json
{
 "available": true,
 "max_ami_age_days": 331,
 "ami_old_90d": [
  "system_core-20251217040546303900000001 331d"
 ],
 "ami_old_180d": [
  "system_core-20251217040546303900000001"
 ],
 "nodegroups": 1,
 "unhealthy": []
}
```

</details>
<details><summary><code>eks.ssm-unregistered.node-1-117</code></summary>

```json
{
 "key": null,
 "item": {
  "node": "node-1-117",
  "instance_id": "i-0123456789abcdef0"
 }
}
```

</details>
<details><summary><code>eks.ssm-unregistered.node-2-60</code></summary>

```json
{
 "key": null,
 "item": {
  "node": "node-2-60",
  "instance_id": "i-0123456789abcdef0"
 }
}
```

</details>
<details><summary><code>eso.provider-api-errors.cluster</code></summary>

```json
{
 "sync_calls_total": 68694,
 "not_ready": [
  "database/externalsecret/mysql-app-n-secret"
 ],
 "metrics_available": true,
 "sync_calls_error": 2555,
 "reconcile_errors_total": 2555,
 "api_error_ratio": 0.0785,
 "api_errors": 2555,
 "api_success": 30008,
 "not_ready_oldest_refresh_h": 7755.0
}
```

</details>
<details><summary><code>grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "present": true,
 "metrics_available": true,
 "api_requests": 6952042,
 "datasource_error_max_ratio": 0.1252,
 "datasources_with_errors": [
  "Loki(loki)"
 ],
 "api_5xx": 9,
 "datasources": [
  {
   "datasource": "Loki(loki)",
   "requests": 2603,
   "errors_5xx_429": 326,
   "error_ratio": 0.1252,
   "by_code": {
    "101": 4,
    "200": 2267,
    "400": 6,
    "429": 326
   }
  },
  {
   "datasource": "Prometheus(prometheus)",
   "requests": 1534,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 1349,
    "301": 185
   }
  },
  {
   "datasource": "VictoriaMetrics_onprem(prometheus)",
   "requests": 141,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 141
   }
  }
 ],
 "target": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale</code></summary>

```json
{
 "tag_kind": "latest",
 "holder": false,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "mutable": true,
 "image": "tailscale/tailscale:latest",
 "pull_policy": "IfNotPresent",
 "registry": "docker.io",
 "container": "tailscale"
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeControllerManagerDown</code></summary>

```json
{
 "labels": {
  "alertname": "KubeControllerManagerDown",
  "severity": "critical"
 },
 "value": 57.8008723263884
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeSchedulerDown</code></summary>

```json
{
 "labels": {
  "alertname": "KubeSchedulerDown",
  "severity": "critical"
 },
 "value": 57.80081445601803
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeControllerManagerDown</code></summary>

```json
{
 "alertname": "KubeControllerManagerDown",
 "samples_7d": 20160.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubePodNotReady</code></summary>

```json
{
 "alertname": "KubePodNotReady",
 "samples_7d": 47752.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeSchedulerDown</code></summary>

```json
{
 "alertname": "KubeSchedulerDown",
 "samples_7d": 20160.0
}
```

</details>
<details><summary><code>observability.log-coverage-gap.cluster</code></summary>

```json
{
 "nodes_all_missing": [
  "node-2-158"
 ],
 "running_pods_over_1h": 139,
 "pods_without_logs_1h": 57,
 "gap_ratio": 0.41,
 "by_namespace_missing": {
  "kube-system": 21,
  "monitoring": 14,
  "prod-app-l-backend": 3,
  "argocd": 2,
  "dev-app-o": 2,
  "dev-app-n": 2,
  "keda": 2,
  "middleware": 2,
  "app-s-prod": 2,
  "arc-runners": 1,
  "dev-app-m": 1,
  "dev-app-t": 1,
  "karpenter": 1,
  "prod-app-q": 1,
  "prod-app-m": 1
 },
 "available": true
}
```

</details>
<details><summary><code>operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret</code></summary>

```json
{
 "age_hours": 7761.6,
 "kind": "externalsecrets.external-secrets.io",
 "name": "mysql-app-n-secret",
 "namespace": "database",
 "message": "could not get secret data from provider",
 "status": "False",
 "reason": "SecretSyncedError",
 "condition": "Ready"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "prod": true,
 "workload": "prod-app-m/statefulset/app-m-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "prod": true,
 "workload": "prod-app-o/statefulset/app-o-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-l-backend/statefulset/app-l-neo4j:neo4j</code></summary>

```json
{
 "prod": true,
 "workload": "prod-app-l-backend/statefulset/app-l-neo4j",
 "readiness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "liveness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "startup": null,
 "db_probe_timeout_1s": true,
 "container": "neo4j"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "prod": true,
 "workload": "prod-app-n/statefulset/app-n-backend-prod-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.no-pdb.prod-app-o/app-o-ai</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-pdb.prod-app-o/app-o-backend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-o/app-o-admin</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-o/app-o-ai</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-o/app-o-backend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-o/app-o-frontend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-l-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-n/app-n-backend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-n/app-n-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.app-s-prod/app-s-backend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.app-s-prod/app-s-frontend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend</code></summary>

```json
{
 "prod": true,
 "prestop": false,
 "recreate_reason": [],
 "workload": "prod-app-p/deployment/app-p-backend",
 "recreate_justified": false,
 "grace_s": 30,
 "strategy": "Recreate",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-api</code></summary>

```json
{
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-m/deployment/app-m-api",
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend</code></summary>

```json
{
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-m/deployment/app-m-backend",
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend</code></summary>

```json
{
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-m/deployment/app-m-frontend",
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-l-backend/deployment/app-l-backend",
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server</code></summary>

```json
{
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-l-backend/deployment/app-l-embedding-server",
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.single-node-dependency.prod-app-l-backend/deployment/tts-proxy</code></summary>

```json
{
 "reasons": [
  "hostPath volume ['dev-net-tun']"
 ],
 "prod": true,
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-q/app-q-ai</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-q/app-q-backend</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-q/app-q-studio</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-q/app-q-web</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-m/app-m-admin</code></summary>

```json
{
 "namespace": "prod-app-m",
 "name": "app-m-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-o/app-o-admin</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-o/app-o-frontend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-l-backend/app-l-pg-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-pg-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-l-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-p/app-p-backend</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-p/app-p-web</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-n/app-n-backend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-n/app-n-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-s-prod/app-s-backend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-s-prod/app-s-frontend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.besteffort-in-prod.prod-app-l-backend/deploy/tts-proxy</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_status_qos_class",
  "container": "kube-state-metrics",
  "endpoint": "http",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-l-backend",
  "pod": "tts-proxy-7b6db97b69-4bbjf",
  "qos_class": "BestEffort",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "99b58936-3d63-43b5-8ffe-c9ceb4353c71"
 },
 "value": 1.0
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-backend-78679bf4b-lhhg4",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.005792472588242948,
   "cpu_p95_7d_cores": 0.002896236294121474,
   "container_cpu_request_cores": 0.5
  }
 },
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-backend-78679bf4b-mbnjd",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.00533530269262311,
   "cpu_p95_7d_cores": 0.002667651346311555,
   "container_cpu_request_cores": 0.5
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-embedding-server-8445d87f5-dwqrx",
   "container": "embedding"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.01115876788749496,
   "cpu_p95_7d_cores": 0.00557938394374748,
   "container_cpu_request_cores": 0.5
  }
 },
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-embedding-server-8445d87f5-jfv9l",
   "container": "embedding"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0024242061048593477,
   "cpu_p95_7d_cores": 0.0012121030524296738,
   "container_cpu_request_cores": 0.5
  }
 }
]
```

</details>
<details><summary><code>resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter</code></summary>

```json
{
 "heap_unset": false,
 "limit_mib": 128.0,
 "heap_ratio": 1.0,
 "workload": "middleware/statefulset/kafka-controller",
 "max_ram_percentage": 100.0,
 "xmx_mib": null,
 "image": "jmx-exporter:0.20.0-debian-11-r4",
 "container": "jmx-exporter"
}
```

</details>
<details><summary><code>resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-4248d:runner</code></summary>

```json
{
 "labels": {
  "container": "runner",
  "namespace": "arc-runners",
  "pod": "self-hosted-arm64-8msc5-runner-4248d"
 },
 "value": 1.0362694300518136
}
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding</code></summary>

```json
[
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-l-backend",
   "pod": "app-l-embedding-server-8445d87f5-dwqrx"
  },
  "value": 0.5917815764686096
 },
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-l-backend",
   "pod": "app-l-embedding-server-8445d87f5-jfv9l"
  },
  "value": 0.5917815764686096
 }
]
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-file-worker:file-worker</code></summary>

```json
{
 "labels": {
  "container": "file-worker",
  "namespace": "prod-app-l-backend",
  "pod": "app-l-file-worker-db75d7fdc-f7tm4"
 },
 "value": 0.5181347150259068
}
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-graph-worker:graph-worker</code></summary>

```json
{
 "labels": {
  "container": "graph-worker",
  "namespace": "prod-app-l-backend",
  "pod": "app-l-graph-worker-d57c9ff8b-xwvfq"
 },
 "value": 0.5181347150259068
}
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-l-backend/sts/app-l-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "container": "neo4j",
  "namespace": "prod-app-l-backend",
  "pod": "app-l-neo4j-0"
 },
 "value": 0.5917815764686096
}
```

</details>
<details><summary><code>resources.no-memory-limit.prod-app-l-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-2-59</code></summary>

```json
{
 "labels": {
  "node": "node-2-59"
 },
 "values": {
  "node_memory_request_ratio": 0.8487658223402312,
  "node_memory_usage_ratio_p95_7d": 0.3263234571023166,
  "node_memory_usage_ratio": 0.26663435467329766
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-2-64</code></summary>

```json
{
 "labels": {
  "node": "node-2-64"
 },
 "values": {
  "node_memory_request_ratio": 0.8487658223402312,
  "node_memory_usage_ratio_p95_7d": 0.26792339247832986,
  "node_memory_usage_ratio": 0.25726668633483657
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-117</code></summary>

```json
{
 "labels": {
  "node": "node-1-117"
 },
 "values": {
  "node_cpu_request_ratio": 0.9637305699481866,
  "node_cpu_usage_ratio_p95_7d": 0.09451303935662735,
  "node_cpu_usage_ratio_5m": 0.09212665594855125
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-139</code></summary>

```json
{
 "labels": {
  "node": "node-1-139"
 },
 "values": {
  "node_cpu_request_ratio": 0.9183673469387752,
  "node_cpu_usage_ratio_p95_7d": 0.052939050266295334,
  "node_cpu_usage_ratio_5m": 0.18338139175150447
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-62</code></summary>

```json
{
 "labels": {
  "node": "node-1-62"
 },
 "values": {
  "node_cpu_request_ratio": 0.8652849740932644,
  "node_cpu_usage_ratio_p95_7d": 0.056685595805818015,
  "node_cpu_usage_ratio_5m": 0.42135705665116735
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-2-60</code></summary>

```json
{
 "labels": {
  "node": "node-2-60"
 },
 "values": {
  "node_cpu_request_ratio": 0.9896373056994822,
  "node_cpu_usage_ratio_p95_7d": 0.061878486724614754,
  "node_cpu_usage_ratio_5m": 0.060175253596561534
 }
}
```

</details>
<details><summary><code>scaling.karpenter-expired-not-replaced.default-n44bh</code></summary>

```json
{
 "node": "node-1-139",
 "age_h": 1022.6,
 "do_not_disrupt_pod_count": 1,
 "hours_past_expiry": 302.6,
 "do_not_disrupt_pods": [
  "prod-app-m/app-m-admin-57f5fcc58d-khsh5"
 ],
 "name": "default-n44bh",
 "disruption_blocked": {
  "do-not-disrupt pods": 21327
 },
 "expire_after_h": 720.0,
 "capacity_type": "spot",
 "instance_type": "r8gd.xlarge"
}
```

</details>
<details><summary><code>security.externalsecret-not-ready.database/mysql-app-n-secret</code></summary>

```json
{
 "message": "could not get secret data from provider",
 "name": "mysql-app-n-secret",
 "reason": "SecretSyncedError",
 "namespace": "database"
}
```

</details>
<details><summary><code>storage.csi-snapshot-unavailable.cluster</code></summary>

```json
{
 "recent_7d": 0,
 "prod_pvcs": 7,
 "ebs_snapshots_30d": 0,
 "volumesnapshots": 0,
 "ebs_snapshot_descriptions": {},
 "platform": "eks",
 "volumesnapshotclasses": 0,
 "volumesnapshot_crd": false
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3</code></summary>

```json
{
 "key": null,
 "item": {
  "name": "gp3",
  "provisioner": "ebs.csi.aws.com",
  "expansion": false
 }
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3-1a</code></summary>

```json
{
 "key": null,
 "item": {
  "name": "gp3-1a",
  "provisioner": "ebs.csi.aws.com",
  "expansion": false
 }
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3-1c</code></summary>

```json
{
 "key": null,
 "item": {
  "name": "gp3-1c",
  "provisioner": "ebs.csi.aws.com",
  "expansion": false
 }
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.prod-app-l-backend</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "system": false,
 "cpu_max_7d": 3.905,
 "has_quota": false,
 "kind": "prod",
 "namespace": "prod-app-l-backend",
 "cpu_median_7d": 0.011,
 "nodes": {
  "node-1-139": 4,
  "node-2-135": 3,
  "node-1-62": 2,
  "node-2-64": 1,
  "node-2-59": 1
 },
 "burst_ratio_7d": 352.3,
 "cpu_p95_7d": 0.026,
 "cpu_limits": 16.2
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-r</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-r",
 "pods": 2,
 "networkpolicies": 0,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-m</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-m",
 "pods": 8,
 "networkpolicies": 0,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-o</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-o",
 "pods": 8,
 "networkpolicies": 0,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-l-backend</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-l-backend",
 "pods": 11,
 "networkpolicies": 0,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-n</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-n",
 "pods": 4,
 "networkpolicies": 0,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-r</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.1,
 "memory_requests_gb": 0.25,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-r",
 "pods": 2,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.004,
 "memory_p95_7d_gb": 0.2,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.003
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-q</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.29,
 "memory_requests_gb": 0.84,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-q",
 "pods": 5,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.009,
 "memory_p95_7d_gb": 0.93,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.008
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-m</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.35,
 "memory_requests_gb": 1.62,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-m",
 "pods": 8,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.109,
 "memory_p95_7d_gb": 1.88,
 "burst_ratio_7d": 1.5,
 "cpu_share_of_cluster_p95": 0.088
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-o</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.51,
 "memory_requests_gb": 8.0,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-o",
 "pods": 8,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.037,
 "memory_p95_7d_gb": 2.8,
 "burst_ratio_7d": 2.2,
 "cpu_share_of_cluster_p95": 0.03
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-l-backend</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 4.72,
 "memory_requests_gb": 18.53,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-l-backend",
 "pods": 11,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.026,
 "memory_p95_7d_gb": 9.62,
 "burst_ratio_7d": 352.3,
 "cpu_share_of_cluster_p95": 0.021
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-p</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.62,
 "memory_requests_gb": 1.28,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-p",
 "pods": 3,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.006,
 "memory_p95_7d_gb": 0.74,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.005
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-n</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.25,
 "memory_requests_gb": 1.12,
 "kind": "prod",
 "has_quota": false,
 "namespace": "prod-app-n",
 "pods": 4,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.024,
 "memory_p95_7d_gb": 1.0,
 "burst_ratio_7d": 4.2,
 "cpu_share_of_cluster_p95": 0.019
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-s-prod</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "prod": true,
 "cpu_requests": 0.25,
 "memory_requests_gb": 0.94,
 "kind": "prod",
 "has_quota": false,
 "namespace": "app-s-prod",
 "pods": 3,
 "cluster_saturated_7d": true,
 "tenants_total": 14,
 "cpu_p95_7d": 0.023,
 "memory_p95_7d_gb": 0.5,
 "burst_ratio_7d": 2.1,
 "cpu_share_of_cluster_p95": 0.018
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.prod-app-l-backend</code></summary>

```json
{
 "multi_org": false,
 "prod": true,
 "kind": "prod",
 "namespace": "prod-app-l-backend",
 "containers_without_memory_limit": 2,
 "pods": 11,
 "has_limitrange": false,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.026,
 "memory_p95_7d_gb": 9.62,
 "containers_without_requests": 2
}
```

</details>
<details><summary><code>traffic.alb-elb-5xx.k8s-shared-alb</code></summary>

```json
{
 "type": "application",
 "elb_5xx_24h": 168.0,
 "target_groups": 40,
 "rejected_connections_24h": 0,
 "name": "k8s-shared-alb",
 "idle_timeout_s": 300,
 "requests_24h": 205586.0,
 "scheme": "internet-facing",
 "target_5xx_24h": 770.0
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-m/app-m-api</code></summary>

```json
{
 "target": "prod-app-m/app-m-api",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 1287.0,
  "requests_24h_equiv": 1287.0,
  "rps_avg": 0.015,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 53.064,
  "p95_s_avg": 16.7739,
  "p95_s_weighted": 14.9046,
  "p95_s_last_1h": 16.5933,
  "p95_s_last_at": "2026-11-05T07:02:00+00:00",
  "requests_last_1h": 3.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-c50edbe2df"
  ]
 },
 "hosts": [
  "canary-api-v1.example-b.ai",
  "api.v1.example-b.ai"
 ]
}
```

</details>
<details><summary><code>traffic.pod-not-ready.prod-app-l-backend/app-l-file-worker</code></summary>

```json
{
 "prod": true,
 "unhealthy_events": 2,
 "workload": "prod-app-l-backend/app-l-file-worker",
 "pods_below_99": 1,
 "worst_pod": "app-l-file-worker-db75d7fdc-f7tm4",
 "min_ready_ratio_24h": 0.875,
 "not_ready_minutes_24h": 180
}
```

</details>
<details><summary><code>traffic.pod-not-ready.prod-app-l-backend/app-l-graph-worker</code></summary>

```json
{
 "prod": true,
 "unhealthy_events": 0,
 "workload": "prod-app-l-backend/app-l-graph-worker",
 "pods_below_99": 1,
 "worst_pod": "app-l-graph-worker-d57c9ff8b-xwvfq",
 "min_ready_ratio_24h": 0.8889,
 "not_ready_minutes_24h": 160
}
```

</details>
<details><summary><code>traffic.shared-alb-group.alb-group/acme-prod-lb</code></summary>

```json
{
 "lb": [
  "k8s-app-svc-alb.us-east-1.elb.amazonaws.com"
 ],
 "prod": true,
 "mixed_prod_nonprod": true,
 "hosts": 47,
 "ingress_count": 40,
 "kinds": [
  "dev",
  "other",
  "prod"
 ],
 "group": "acme-prod-lb",
 "namespaces": [
  "argocd",
  "dev-app-m",
  "dev-app-o",
  "dev-app-n",
  "dev-app-t",
  "middleware",
  "monitoring",
  "prod-app-r",
  "prod-app-q",
  "prod-app-m",
  "prod-app-o",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "namespace_count": 15,
 "target": "alb-group/acme-prod-lb"
}
```

</details>
<details><summary><code>albctl.reconcile-errors.cluster</code></summary>

```json
{
 "leader_found": true,
 "ingresses_without_lb": [],
 "reconcile_errors_total": 41,
 "metrics_available": true,
 "tgb_stale": [],
 "rest_client_429_503": 126,
 "workqueue_depth_max": 0.0
}
```

</details>
<details><summary><code>albctl.tgb-stale-or-orphan.cluster</code></summary>

```json
{
 "tgb_by_target_type": {
  "ip": 51
 },
 "traffic_target_groups_without_tgb": 1,
 "tgb_stale": [],
 "tgb_service_missing": [],
 "tgb_count": 51,
 "tgb_manual": [
  "dev-app-m/app-m-dev-mysql-tgb",
  "dev-app-o/app-o-dev-mysql-tgb",
  "dev-app-n/app-n-dev-mysql-tgb",
  "prod-app-q/app-q-prod-postgresql-tgb",
  "prod-app-m/app-m-prod-mysql-tgb",
  "prod-app-o/app-o-prod-mysql-tgb",
  "prod-app-l-backend/app-l-prod-neo4j-tgb",
  "prod-app-l-backend/app-l-prod-pg-proxy-tgb",
  "prod-app-n/app-n-prod-mysql-tgb"
 ]
}
```

</details>
<details><summary><code>argocd.admin-account-no-sso.cluster</code></summary>

```json
{
 "anonymous_enabled": false,
 "exec_enabled": false,
 "rbac_policy_csv_lines": 0,
 "sso_configured": false,
 "admin_enabled": true,
 "rbac_policy_default": "",
 "url": "https://deploy.my-cluster"
}
```

</details>
<details><summary><code>argocd.components-not-ha.cluster</code></summary>

```json
{
 "version": "2.13.0",
 "components": {
  "applicationset-controller": "1/1",
  "dex-server": "1/1",
  "notifications-controller": "1/1",
  "redis": "1/1",
  "repo-server": "1/1",
  "server": "1/1",
  "application-controller": "1/1"
 },
 "applications_prod": 8,
 "components_not_ready": [],
 "components_single_replica": [
  "repo-server",
  "server"
 ]
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "pods_default_ndots": 157,
 "upstreams": [
  "<ip>:53"
 ],
 "metrics_available": true,
 "qps_total": 79.28,
 "forward_nxdomain_ratio": 0.482,
 "cache_hit_ratio": 0.9053,
 "autopath": false,
 "nxdomain_ratio": 0.513
}
```

</details>
<details><summary><code>eso.controller-single-replica.cluster</code></summary>

```json
{
 "webhook_replicas": 1,
 "concurrent": "1",
 "cert_controller_replicas": 1,
 "cert_controller_ready": 1,
 "webhook_fail_policy": [
  "validate.externalsecret.external-secrets.io",
  "validate.secretstore.external-secrets.io",
  "validate.clustersecretstore.external-secrets.io"
 ],
 "controller_replicas": 1,
 "webhook_ready": 1,
 "controller_ready": 1
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl</code></summary>

```json
{
 "tag_kind": "latest",
 "prod": false,
 "workload": "arc-runners/cronjob/arc-cool-down",
 "mutable": true,
 "image": "bitnami/kubectl:latest",
 "pull_policy": "Always",
 "registry": "docker.io",
 "container": "kubectl"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl</code></summary>

```json
{
 "tag_kind": "latest",
 "prod": false,
 "workload": "arc-runners/cronjob/arc-warm-up",
 "mutable": true,
 "image": "bitnami/kubectl:latest",
 "pull_policy": "Always",
 "registry": "docker.io",
 "container": "kubectl"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight</code></summary>

```json
{
 "tag_kind": "latest",
 "prod": false,
 "workload": "middleware/deployment/redis-insight",
 "mutable": true,
 "image": "redis/redisinsight:latest",
 "pull_policy": "Always",
 "registry": "docker.io",
 "container": "redis-insight"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.acme.ai/role</code></summary>

```json
{
 "workload_count": 33,
 "key": "acme.ai/role",
 "nodes_with_label": 5,
 "well_known": false,
 "prod_workloads": 8,
 "nodes_total": 10,
 "workloads": [
  "argocd/deployment/argocd-applicationset-controller",
  "argocd/deployment/argocd-dex-server",
  "argocd/deployment/argocd-notifications-controller",
  "argocd/deployment/argocd-redis",
  "argocd/deployment/argocd-repo-server",
  "argocd/deployment/argocd-server",
  "kube-system/deployment/external-dns",
  "middleware/deployment/kafka-exporter"
 ]
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.workload-type</code></summary>

```json
{
 "workload_count": 38,
 "key": "workload-type",
 "nodes_with_label": 5,
 "well_known": false,
 "prod_workloads": 25,
 "nodes_total": 10,
 "workloads": [
  "dev-app-m/deployment/app-m-admin",
  "dev-app-m/deployment/app-m-api",
  "dev-app-m/deployment/app-m-backend",
  "dev-app-m/deployment/app-m-frontend",
  "dev-app-o/deployment/app-o-admin",
  "dev-app-o/deployment/app-o-ai",
  "dev-app-o/deployment/app-o-backend",
  "dev-app-o/deployment/app-o-frontend"
 ]
}
```

</details>
<details><summary><code>karpenter.consistency-errors.cluster</code></summary>

```json
{
 "cluster_state_synced": true,
 "metrics_available": true,
 "pods_startup_avg_s": 31.3,
 "node_termination_avg_s": 15.1,
 "consistency_errors": 3,
 "pods_startup_count": 8485,
 "reconcile_errors": {}
}
```

</details>
<details><summary><code>keda.components-single-replica.cluster</code></summary>

```json
{
 "metrics_apiserver_ready": 1,
 "scaledobjects_prod": 3,
 "unused": false,
 "has_pdb": false,
 "apiservice_available": true,
 "operator_replicas": 1,
 "metrics_apiserver_replicas": 1,
 "operator_ready": 1
}
```

</details>
<details><summary><code>keda.prod-external-trigger-no-fallback.cluster</code></summary>

```json
{
 "polling_interval_min_s": 15,
 "prod_external_without_fallback": [
  "prod-app-o/scaledobject/app-o-ai-kafka-lag",
  "prod-app-l-backend/scaledobject/app-l-file-worker",
  "prod-app-l-backend/scaledobject/app-l-graph-worker"
 ],
 "trigger_types": {
  "kafka": 4,
  "metrics-api": 2
 }
}
```

</details>
<details><summary><code>logs.signatures.ebs-csi.snapshot-crd-missing</code></summary>

```json
{
 "count": 1500,
 "first": "2026-11-05T03:23:13Z",
 "last": "2026-11-05T08:03:38Z",
 "warn_at": 1,
 "fail_at": 100,
 "files": {
  "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 1500
 },
 "samples": [
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:13.503404100Z W1105 03:23:13.503303       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:13.503446925Z E1105 03:23:13.503347       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:48.702487455Z W1105 03:23:48.702392       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:23:48.702689241Z E1105 03:23:48.702636       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:24:01.768261955Z W1105 03:24:01.768144       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metrics-server.scrape-failed</code></summary>

```json
{
 "count": 42,
 "first": "2026-11-04T09:02:26Z",
 "last": "2026-11-05T07:55:11Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/metrics-server/kube-system_metrics-server.log": 42
 },
 "samples": [
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T09:02:26.073535127Z E1104 09:02:26.073405       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T10:00:26.042265249Z E1104 10:00:26.042102       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T12:14:41.093306131Z E1104 12:14:41.093190       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T12:43:56.034087527Z E1104 12:43:56.033942       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T12:43:56.059510652Z E1104 12:43:56.059394       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal er"
 ]
}
```

</details>
<details><summary><code>loki.memory-pressure.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "present": true,
 "rss_vs_limit": 0.4,
 "oomkilled_at": "2026-10-25T00:15:41Z",
 "rss_mib": 205,
 "restarts": 1,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/loki-stack",
 "memory_limit": "512Mi",
 "memory_streams": 66,
 "oomkilled_last": true
}
```

</details>
<details><summary><code>loki.request-errors.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "panics": 0,
 "requests_total": 5955681,
 "present": true,
 "discarded_by_reason": {},
 "metrics_available": true,
 "wal_disk_full_failures": 0,
 "log_error_messages": 10130,
 "requests_5xx_by_route": {
  "loki_api_v1_series": 1
 },
 "requests_5xx": 1,
 "target": "monitoring/statefulset/loki-stack"
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "by_severity": {
  "critical": 48,
  "warning": 97,
  "page": 2,
  "high": 3,
  "none": 2,
  "info": 5
 },
 "by_class": {
  "app-cause": 5,
  "app": 14,
  "cause": 138
 },
 "page_severity_cause": [
  "AlertmanagerFailedReload",
  "AlertmanagerMembersInconsistent",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterCrashlooping",
  "etcdMembersDown",
  "etcdInsufficientMembers",
  "etcdNoLeader",
  "etcdHighFsyncDurations",
  "etcdDatabaseQuotaLowSpace",
  "KubeAPIErrorBudgetBurn",
  "KubeAPIErrorBudgetBurn",
  "KubeStateMetricsListErrors",
  "KubeStateMetricsWatchErrors",
  "KubeStateMetricsShardingMismatch",
  "KubeStateMetricsShardsMissing",
  "KubePersistentVolumeFillingUp",
  "KubePersistentVolumeInodesFillingUp",
  "KubePersistentVolumeErrors",
  "KubeClientCertificateExpiration",
  "KubeAPIDown",
  "KubeControllerManagerDown",
  "KubeProxyDown",
  "KubeletClientCertificateExpiration",
  "KubeletServerCertificateExpiration",
  "KubeletDown",
  "KubeSchedulerDown",
  "NodeFilesystemSpaceFillingUp",
  "NodeFilesystemAlmostOutOfSpace",
  "NodeFilesystemFilesFillingUp",
  "NodeFilesystemAlmostOutOfFiles",
  "NodeRAIDDegraded",
  "NodeFileDescriptorLimit",
  "PrometheusBadConfig",
  "PrometheusRemoteStorageFailures",
  "PrometheusRemoteWriteBehind",
  "PrometheusRuleFailures",
  "PrometheusTargetSyncFailure",
  "PrometheusErrorSendingAlertsToAnyAlertmanager"
 ],
 "alerting": 157
}
```

</details>
<details><summary><code>observability.promtail-dropped.cluster</code></summary>

```json
{
 "dropped_entries_1h": null,
 "targets_active": null,
 "metrics_scraped": false,
 "request_errors_1h": null
}
```

</details>
<details><summary><code>observability.slo-without-burn-rate.cluster</code></summary>

```json
{
 "slo_labelled_rules": [
  "ImageInferenceE2ESuccessRateDrop",
  "ImageInferenceEntitlementFailureSpike",
  "LoraTrainingSuccessRateDrop",
  "LoraTrainingDurationP95High",
  "LoraTrainingCallbackTimeout"
 ],
 "any_signal": true,
 "sli_recording_rules": [],
 "tools": [],
 "burn_rate_alerts": []
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "prod": false,
 "workload": "dev-app-m/statefulset/app-m-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "prod": false,
 "workload": "dev-app-o/statefulset/app-o-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "prod": false,
 "workload": "dev-app-n/statefulset/app-n-backend-dev-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-t/statefulset/app-t-mysql:mysql</code></summary>

```json
{
 "prod": false,
 "workload": "dev-app-t/statefulset/app-t-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-t/statefulset/app-t-postgres:postgres</code></summary>

```json
{
 "prod": false,
 "workload": "dev-app-t/statefulset/app-t-postgres",
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": null,
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "prod": false,
 "workload": "monitoring/statefulset/loki-stack",
 "readiness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 },
 "liveness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 },
 "startup": null,
 "db_probe_timeout_1s": true,
 "container": "loki"
}
```

</details>
<details><summary><code>resilience.priority-inversion.cluster</code></summary>

```json
{
 "preempted_events": 0,
 "prod_max_priority": 0,
 "no_user_classes_with_prod": true,
 "pods_by_class": {
  "(none, 0)": 112,
  "system-cluster-critical": 9,
  "system-node-critical": 30
 },
 "prod_pods_without_class": 44,
 "user_classes": [],
 "inversion": [],
 "prod_pods": 44,
 "nonprod_max_priority": 0
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.cluster</code></summary>

```json
{
 "prod_db_without_backup_cronjob": [
  "prod-app-q/statefulset/app-q-backend-postgresql",
  "prod-app-m/statefulset/app-m-backend-mysql",
  "prod-app-o/statefulset/app-o-backend-mysql",
  "prod-app-l-backend/statefulset/app-l-neo4j",
  "prod-app-p/statefulset/app-p-postgresql",
  "prod-app-n/statefulset/app-n-backend-prod-mysql",
  "app-s-prod/statefulset/app-s-backend-postgresql"
 ],
 "local_only": [],
 "db_workloads_with_pvc": 17,
 "same_node": [],
 "count": 0
}
```

</details>
<details><summary><code>resilience.recreate-strategy-serving.monitoring/deployment/vmauth</code></summary>

```json
{
 "prod": false,
 "prestop": false,
 "recreate_reason": [],
 "workload": "monitoring/deployment/vmauth",
 "namespace": "monitoring",
 "recreate_justified": false,
 "grace_s": 30,
 "strategy": "Recreate",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master</code></summary>

```json
{
 "prod": false,
 "prestop": false,
 "shell_pid1_containers": [
  "redis",
  "metrics"
 ],
 "workload": "middleware/statefulset/redis-master",
 "grace_s": 30
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server</code></summary>

```json
{
 "labels": {
  "namespace": "argocd",
  "pod": "argocd-repo-server-d487895cc-bth22",
  "container": "repo-server"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.012495733754629828,
  "cpu_p95_7d_cores": 0.0024991467509259658,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller</code></summary>

```json
{
 "labels": {
  "namespace": "argocd",
  "pod": "argocd-application-controller-0",
  "container": "application-controller"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1702110730512147,
  "cpu_p95_7d_cores": 0.03404221461024294,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-api:api</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-m",
  "pod": "app-m-api-575d497d9b-5ttcv",
  "container": "api"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.11378513752468306,
  "cpu_p95_7d_cores": 0.011378513752468306,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-m",
  "pod": "app-m-backend-76775dbdd-ttz69",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1716915751801608,
  "cpu_p95_7d_cores": 0.01716915751801608,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-m/sts/app-m-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-m",
  "pod": "app-m-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.10118530421088598,
  "cpu_p95_7d_cores": 0.010118530421088599,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-ai-7cdbdc7544-szzcl",
  "container": "ai"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.02496637967128669,
  "cpu_p95_7d_cores": 0.002496637967128669,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-backend-69dbdf4f65-9x6jc",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1103621602096111,
  "cpu_p95_7d_cores": 0.01103621602096111,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-o/sts/app-o-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.08884969746402845,
  "cpu_p95_7d_cores": 0.008884969746402845,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-n/deploy/app-n-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-n",
  "pod": "app-n-backend-7cfd8c975-b9p48",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1262058727488336,
  "cpu_p95_7d_cores": 0.01262058727488336,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-n/sts/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-n",
  "pod": "app-n-backend-dev-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1032220413581271,
  "cpu_p95_7d_cores": 0.01032220413581271,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-t/deploy/app-t-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-t",
  "pod": "app-t-backend-5ff4994f96-fxsr6",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.004991649733091124,
  "cpu_p95_7d_cores": 0.0009983299466182248,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-t",
  "pod": "app-t-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.04465649733005835,
  "cpu_p95_7d_cores": 0.00893129946601167,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-t",
  "pod": "app-t-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.07503438203147618,
  "cpu_p95_7d_cores": 0.007503438203147618,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller</code></summary>

```json
[
 {
  "labels": {
   "namespace": "karpenter",
   "pod": "karpenter-9769889bd-pkxd2",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.08880069572320455,
   "cpu_p95_7d_cores": 0.01776013914464091,
   "container_cpu_request_cores": 0.2
  }
 },
 {
  "labels": {
   "namespace": "karpenter",
   "pod": "karpenter-9769889bd-nphgs",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0021754143855616287,
   "cpu_p95_7d_cores": 0.0004350828771123258,
   "container_cpu_request_cores": 0.2
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "labels": {
  "namespace": "keda",
  "pod": "keda-admission-webhooks-7fc99cdd4d-jpng8",
  "container": "keda-admission-webhooks"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.002914606937671353,
  "cpu_p95_7d_cores": 0.0002914606937671353,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "labels": {
  "namespace": "keda",
  "pod": "keda-operator-metrics-apiserver-c5b6f8b88-jt7dp",
  "container": "keda-operator-metrics-apiserver"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.01781877776139189,
  "cpu_p95_7d_cores": 0.0017818777761391892,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator</code></summary>

```json
{
 "labels": {
  "namespace": "keda",
  "pod": "keda-operator-54ffcbbfd6-2wtvl",
  "container": "keda-operator"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.016533930112398672,
  "cpu_p95_7d_cores": 0.0016533930112398675,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/deploy/aws-load-balancer-controller:aws-load-balancer-controller</code></summary>

```json
[
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "aws-load-balancer-controller-dbcd6944f-svnmr",
   "container": "aws-load-balancer-controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.023078673141631752,
   "cpu_p95_7d_cores": 0.0023078673141631754,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "aws-load-balancer-controller-dbcd6944f-psh2b",
   "container": "aws-load-balancer-controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.009425140273268913,
   "cpu_p95_7d_cores": 0.0009425140273268914,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns</code></summary>

```json
[
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "coredns-c7dbf4744-lz5fs",
   "container": "coredns"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.07065552304091595,
   "cpu_p95_7d_cores": 0.007065552304091596,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "coredns-c7dbf4744-cb76h",
   "container": "coredns"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.06635704168919143,
   "cpu_p95_7d_cores": 0.0066357041689191435,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server</code></summary>

```json
{
 "labels": {
  "namespace": "kube-system",
  "pod": "metrics-server-65d4b7df64-xxfjs",
  "container": "metrics-server"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.05299588312969913,
  "cpu_p95_7d_cores": 0.005299588312969913,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/ds/kube-proxy:kube-proxy</code></summary>

```json
[
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-d297j",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.006957164178918865,
   "cpu_p95_7d_cores": 0.0006957164178918865,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-snbf9",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.006416312153615189,
   "cpu_p95_7d_cores": 0.0006416312153615189,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-77wxc",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.004157624770424392,
   "cpu_p95_7d_cores": 0.00041576247704243926,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-4zj2m",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.003491200095329152,
   "cpu_p95_7d_cores": 0.0003491200095329152,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-n4sbq",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0033353020603246178,
   "cpu_p95_7d_cores": 0.0003335302060324618,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-t9t6c",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.00332482087904412,
   "cpu_p95_7d_cores": 0.00033248208790441204,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-kq4wd",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0032253998433873924,
   "cpu_p95_7d_cores": 0.00032253998433873926,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.middleware/deploy/kafka-ui:kafka-ui</code></summary>

```json
{
 "labels": {
  "namespace": "middleware",
  "pod": "kafka-ui-7cb8bcb988-gls7p",
  "container": "kafka-ui"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.009412994198431895,
  "cpu_p95_7d_cores": 0.0009412994198431896,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.middleware/sts/kafka-controller:kafka</code></summary>

```json
{
 "labels": {
  "namespace": "middleware",
  "pod": "kafka-controller-0",
  "container": "kafka"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.34182438043102487,
  "cpu_p95_7d_cores": 0.06836487608620498,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "kube-prometheus-stack-grafana-7c9959564d-w8qx7",
  "container": "grafana"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.01962770725098252,
  "cpu_p95_7d_cores": 0.0019627707250982522,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.monitoring/sts/loki-stack:loki</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "loki-stack-0",
  "container": "loki"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.06714844812854961,
  "cpu_p95_7d_cores": 0.0067148448128549615,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "vm-single-0",
  "container": "vmsingle"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.0046115798108657255,
  "cpu_p95_7d_cores": 0.0013834739432597176,
  "container_cpu_request_cores": 0.3
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-q",
  "pod": "app-q-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.05074310663981131,
  "cpu_p95_7d_cores": 0.005074310663981132,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-m/sts/app-m-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-m",
  "pod": "app-m-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.054801757862798714,
  "cpu_p95_7d_cores": 0.010960351572559743,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-backend-596479b6f8-cx44t",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.09661121473462486,
   "cpu_p95_7d_cores": 0.009661121473462486,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-backend-596479b6f8-nv9j2",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0961130425631853,
   "cpu_p95_7d_cores": 0.00961130425631853,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-o/sts/app-o-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-o",
  "pod": "app-o-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.04472575856910098,
  "cpu_p95_7d_cores": 0.008945151713820196,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-frontend-6d58bbfcfc-nfk9x",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.007120783005546277,
   "cpu_p95_7d_cores": 0.0007120783005546277,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-frontend-6d58bbfcfc-2qgs6",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.006550889871724822,
   "cpu_p95_7d_cores": 0.0006550889871724823,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-l-backend",
  "pod": "app-l-neo4j-0",
  "container": "neo4j"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.009738986922119022,
  "cpu_p95_7d_cores": 0.004869493461059511,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-p/sts/app-p-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-p",
  "pod": "app-p-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.044704654404631484,
  "cpu_p95_7d_cores": 0.0044704654404631484,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-n/sts/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-n",
  "pod": "app-n-backend-prod-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.048538927452796234,
  "cpu_p95_7d_cores": 0.009707785490559248,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "app-s-prod",
  "pod": "app-s-backend-6dd8fcbf96-nshrh",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.14328994968369457,
  "cpu_p95_7d_cores": 0.014328994968369457,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "app-s-prod",
  "pod": "app-s-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.06972185998749919,
  "cpu_p95_7d_cores": 0.00697218599874992,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-1-241</code></summary>

```json
{
 "labels": {
  "node": "node-1-241"
 },
 "values": {
  "node_memory_request_ratio": 0.6637597400652016,
  "node_memory_usage_ratio_p95_7d": 0.3252818184541721,
  "node_memory_usage_ratio": 0.3422347747222669
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-2-135</code></summary>

```json
{
 "labels": {
  "node": "node-2-135"
 },
 "values": {
  "node_memory_request_ratio": 0.992571564691715,
  "node_memory_usage_ratio_p95_7d": 0.4164266174438147,
  "node_memory_usage_ratio": 0.4216874744088373
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-2-135</code></summary>

```json
{
 "labels": {
  "node": "node-2-135"
 },
 "values": {
  "node_cpu_request_ratio": 0.7357512953367876,
  "node_cpu_usage_ratio_p95_7d": 0.04725583114258754,
  "node_cpu_usage_ratio_5m": 0.04868041794764913
 }
}
```

</details>
<details><summary><code>scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "app-m-frontend",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "dev-app-m",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 42.0
}
```

</details>
<details><summary><code>scaling.hpa-flapping.prod-app-l-backend/hpa/keda-hpa-app-l-file-worker</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "keda-hpa-app-l-file-worker",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-l-backend",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 47.0
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
 "root_allowed_ratio": 0.62,
 "prod_without_psa": [
  "prod-app-r",
  "prod-app-q",
  "prod-app-m",
  "prod-app-o",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "psa_enforced_namespaces": [],
 "root_allowed_prod": [
  "prod-app-r/deployment/app-r",
  "prod-app-q/deployment/app-q-ai",
  "prod-app-q/deployment/app-q-backend",
  "prod-app-q/deployment/app-q-studio",
  "prod-app-q/deployment/app-q-web",
  "prod-app-m/deployment/app-m-admin",
  "prod-app-m/deployment/app-m-api",
  "prod-app-m/deployment/app-m-backend",
  "prod-app-m/deployment/app-m-frontend",
  "prod-app-o/deployment/app-o-admin",
  "prod-app-o/deployment/app-o-ai",
  "prod-app-o/deployment/app-o-backend",
  "prod-app-o/deployment/app-o-frontend",
  "prod-app-l-backend/deployment/app-l-backend",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/app-l-file-worker",
  "prod-app-l-backend/deployment/app-l-frontend",
  "prod-app-l-backend/deployment/app-l-graph-worker",
  "prod-app-l-backend/deployment/app-l-pg-proxy",
  "prod-app-l-backend/deployment/tts-proxy",
  "prod-app-p/deployment/app-p-backend",
  "prod-app-p/deployment/app-p-web",
  "prod-app-n/deployment/app-n-admin-frontend",
  "prod-app-n/deployment/app-n-backend",
  "prod-app-n/deployment/app-n-frontend",
  "app-s-prod/deployment/app-s-backend",
  "app-s-prod/deployment/app-s-frontend",
  "prod-app-l-backend/statefulset/app-l-neo4j"
 ]
}
```

</details>
<details><summary><code>security.rbac-wildcard.argocd-application-controller</code></summary>

```json
{
 "clusterrole": "argocd-application-controller",
 "prod": false,
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "argocd",
   "name": "argocd-application-controller"
  }
 ],
 "bound": true
}
```

</details>
<details><summary><code>security.sa-token-mounted-without-rbac.cluster</code></summary>

```json
{
 "token_mounted": 88,
 "service_accounts": 111,
 "automount_false_sa": 6,
 "workloads": 93,
 "token_mounted_without_rbac_prod": [
  "prod-app-r/deployment/app-r",
  "prod-app-q/deployment/app-q-ai",
  "prod-app-q/deployment/app-q-backend",
  "prod-app-q/deployment/app-q-studio",
  "prod-app-q/deployment/app-q-web",
  "prod-app-m/deployment/app-m-admin",
  "prod-app-m/deployment/app-m-api",
  "prod-app-m/deployment/app-m-backend",
  "prod-app-m/statefulset/app-m-backend-mysql",
  "prod-app-m/deployment/app-m-frontend",
  "prod-app-o/deployment/app-o-admin",
  "prod-app-o/deployment/app-o-ai",
  "prod-app-o/deployment/app-o-backend",
  "prod-app-o/statefulset/app-o-backend-mysql",
  "prod-app-o/deployment/app-o-frontend",
  "prod-app-l-backend/deployment/app-l-backend",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/app-l-file-worker",
  "prod-app-l-backend/deployment/app-l-frontend",
  "prod-app-l-backend/deployment/app-l-graph-worker",
  "prod-app-l-backend/statefulset/app-l-neo4j",
  "prod-app-l-backend/deployment/app-l-pg-proxy",
  "prod-app-l-backend/deployment/tts-proxy",
  "prod-app-p/deployment/app-p-backend",
  "prod-app-p/deployment/app-p-web",
  "prod-app-n/deployment/app-n-admin-frontend",
  "prod-app-n/deployment/app-n-backend",
  "prod-app-n/statefulset/app-n-backend-prod-mysql",
  "prod-app-n/deployment/app-n-frontend",
  "app-s-prod/deployment/app-s-backend",
  "app-s-prod/deployment/app-s-frontend"
 ]
}
```

</details>
<details><summary><code>storage.ebs-unencrypted.cluster</code></summary>

```json
{
 "available": true,
 "unencrypted": [
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0",
  "vol-0123456789abcdef0"
 ],
 "volumes": 17
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
 "prod_db_delete_reclaim": [
  "prod-app-n/data-app-n-backend-prod-mysql-0",
  "prod-app-m/data-app-m-backend-mysql-0",
  "prod-app-l-backend/data-app-l-neo4j-0",
  "app-s-prod/data-app-s-backend-postgresql-0",
  "prod-app-p/data-app-p-postgresql-0",
  "prod-app-q/data-app-q-backend-postgresql-0",
  "prod-app-o/data-app-o-backend-mysql-0"
 ],
 "rows": [
  {
   "namespace": "dev-app-t",
   "name": "data-app-t-mysql-0",
   "target": "dev-app-t/data-app-t-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.902,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": null,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-t-mysql"
   ],
   "db_like": true,
   "pv": "pvc-ebee9c1c-11b1-41af-b913-e3c72dad2bda",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "monitoring",
   "name": "prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "target": "monitoring/prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.459,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.003,
   "days_to_full": 3197,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/prometheus-kube-prometheus-stack-prometheus"
   ],
   "db_like": true,
   "pv": "pvc-0bced2ad-d452-4dce-a717-e11877feae44",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-n",
   "name": "data-app-n-backend-prod-mysql-0",
   "target": "prod-app-n/data-app-n-backend-prod-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.129,
   "inode_ratio": 0.001,
   "growth_gb_per_day": 0.0,
   "days_to_full": 35255,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-n-backend-prod-mysql"
   ],
   "db_like": true,
   "pv": "pvc-a50dcc70-b062-457a-b0e3-07a3e6da2ec6",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-m",
   "name": "data-app-m-backend-mysql-0",
   "target": "prod-app-m/data-app-m-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.077,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.001,
   "days_to_full": 5438,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-m-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-9f1aab56-d94c-499d-8df6-2def93e79427",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-n",
   "name": "data-app-n-backend-dev-mysql-0",
   "target": "dev-app-n/data-app-n-backend-dev-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.06,
   "inode_ratio": 0.001,
   "growth_gb_per_day": 0.0,
   "days_to_full": 1952315,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-n-backend-dev-mysql"
   ],
   "db_like": true,
   "pv": "pvc-0138f912-7588-42ed-9850-b6f7e4dfd422",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-l-backend",
   "name": "data-app-l-neo4j-0",
   "target": "prod-app-l-backend/data-app-l-neo4j-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.051,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.001,
   "days_to_full": 15140,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-l-neo4j"
   ],
   "db_like": true,
   "pv": "pvc-5cccf1df-7624-45a2-833d-2191c5490713",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-s-prod",
   "name": "data-app-s-backend-postgresql-0",
   "target": "app-s-prod/data-app-s-backend-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.048,
   "inode_ratio": 0.003,
   "growth_gb_per_day": -0.0,
   "days_to_full": null,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-s-backend-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-f226562f-a020-4027-a0d4-1494585c8b6f",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-m",
   "name": "data-app-m-backend-mysql-0",
   "target": "dev-app-m/data-app-m-backend-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.031,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": 507869,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-m-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-273a8340-e63c-44b5-8618-433a85e68cdd",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-p",
   "name": "data-app-p-postgresql-0",
   "target": "prod-app-p/data-app-p-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.027,
   "inode_ratio": 0.003,
   "growth_gb_per_day": 0.0,
   "days_to_full": 41745,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-p-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-8d1f15c7-e0e6-4410-bd40-64d7332aef0d",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-o",
   "name": "data-app-o-backend-mysql-0",
   "target": "dev-app-o/data-app-o-backend-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.022,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": null,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-o-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-878f1d5b-67fc-4640-8d1d-516caa26e7df",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-q",
   "name": "data-app-q-backend-postgresql-0",
   "target": "prod-app-q/data-app-q-backend-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.022,
   "inode_ratio": 0.003,
   "growth_gb_per_day": 0.002,
   "days_to_full": 4846,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-q-backend-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-1a304f49-fa2e-43ed-a996-df104613c88c",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "middleware",
   "name": "data-kafka-controller-0",
   "target": "middleware/data-kafka-controller-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.013,
   "inode_ratio": 0.001,
   "growth_gb_per_day": 0.016,
   "days_to_full": 1202,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/kafka-controller"
   ],
   "db_like": true,
   "pv": "pvc-b86f8034-3a78-4458-b3b8-c6aed3a919a2",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-o",
   "name": "data-app-o-backend-mysql-0",
   "target": "prod-app-o/data-app-o-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 50.0,
   "capacity_gb": 48.9,
   "used_ratio": 0.009,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": 3854402,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-o-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-ebc5618b-a1af-40d3-b15d-4969ed13487e",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "middleware",
   "name": "redis-data-redis-master-0",
   "target": "middleware/redis-data-redis-master-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.008,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.003,
   "days_to_full": 2885,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/redis-master"
   ],
   "db_like": true,
   "pv": "pvc-391869b9-4c33-41b5-977f-553dc4d5dc0f",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-t",
   "name": "data-app-t-postgres-0",
   "target": "dev-app-t/data-app-t-postgres-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.006,
   "inode_ratio": 0.002,
   "growth_gb_per_day": 0.0,
   "days_to_full": null,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/app-t-postgres"
   ],
   "db_like": true,
   "pv": "pvc-750ab148-9691-40f1-8eeb-ed31aead86a8",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "monitoring",
   "name": "server-volume-vm-single-0",
   "target": "monitoring/server-volume-vm-single-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 50.0,
   "capacity_gb": 48.9,
   "used_ratio": 0.001,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.001,
   "days_to_full": 51619,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "statefulset/vm-single"
   ],
   "db_like": false,
   "pv": "pvc-6af4b3e1-029f-453e-b7c6-198a618fb3e5",
   "zone": "us-east-1c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "monitoring",
   "name": "kube-prometheus-stack-grafana",
   "target": "monitoring/kube-prometheus-stack-grafana",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.0,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": 44407678881,
   "metrics": true,
   "host_fs": false,
   "workloads": [
    "deployment/kube-prometheus-stack-grafana"
   ],
   "db_like": false,
   "pv": "pvc-9787333f-be2a-4ec2-9b6b-6b81756a4e94",
   "zone": "us-east-1a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  }
 ]
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-q</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-q",
 "pods": 5,
 "networkpolicies": 1,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-p</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "prod-app-p",
 "pods": 3,
 "networkpolicies": 1,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-s-prod</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": true,
 "has_quota": false,
 "namespace": "app-s-prod",
 "pods": 3,
 "networkpolicies": 1,
 "rbac_subject_count": 0,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "tenants_total": 14,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-runners</code></summary>

```json
{
 "shares_nodes_with_prod": false,
 "prod": false,
 "cpu_requests": 2.0,
 "memory_requests_gb": 4.0,
 "kind": "ci",
 "has_quota": false,
 "namespace": "arc-runners",
 "pods": 1,
 "burst_ratio_7d": null,
 "tenants_total": 14,
 "cpu_p95_7d": 0.471,
 "memory_p95_7d_gb": 1.96,
 "cpu_share_of_cluster_p95": 0.384
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-m</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": false,
 "cpu_requests": 0.4,
 "memory_requests_gb": 1.25,
 "kind": "dev",
 "has_quota": false,
 "namespace": "dev-app-m",
 "pods": 5,
 "burst_ratio_7d": 1.4,
 "tenants_total": 14,
 "cpu_p95_7d": 0.052,
 "memory_p95_7d_gb": 0.86,
 "cpu_share_of_cluster_p95": 0.042
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-o</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": false,
 "cpu_requests": 0.4,
 "memory_requests_gb": 2.25,
 "kind": "dev",
 "has_quota": false,
 "namespace": "dev-app-o",
 "pods": 5,
 "burst_ratio_7d": 1.1,
 "tenants_total": 14,
 "cpu_p95_7d": 0.035,
 "memory_p95_7d_gb": 1.4,
 "cpu_share_of_cluster_p95": 0.028
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-n</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": false,
 "cpu_requests": 0.3,
 "memory_requests_gb": 1.0,
 "kind": "dev",
 "has_quota": false,
 "namespace": "dev-app-n",
 "pods": 4,
 "burst_ratio_7d": 1.5,
 "tenants_total": 14,
 "cpu_p95_7d": 0.024,
 "memory_p95_7d_gb": 0.95,
 "cpu_share_of_cluster_p95": 0.02
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-t</code></summary>

```json
{
 "shares_nodes_with_prod": true,
 "prod": false,
 "cpu_requests": 0.55,
 "memory_requests_gb": 1.88,
 "kind": "dev",
 "has_quota": false,
 "namespace": "dev-app-t",
 "pods": 4,
 "burst_ratio_7d": 1.1,
 "tenants_total": 14,
 "cpu_p95_7d": 0.017,
 "memory_p95_7d_gb": 0.85,
 "cpu_share_of_cluster_p95": 0.014
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-1-117</code></summary>

```json
{
 "node": "node-1-117",
 "tenant_count": 2,
 "memory_limits_gb": 11.6,
 "memory_requests_gb": 4.7,
 "pool": "system_core-20251217040546303900000001",
 "memory_limit_overcommit": 1.68,
 "namespaces": {
  "kube-system": 3,
  "keda": 2,
  "monitoring": 2,
  "argocd": 1,
  "dev-app-o": 1,
  "dev-app-t": 1,
  "karpenter": 1,
  "prod-app-o": 1,
  "app-s-prod": 1
 },
 "allocatable_memory_gb": 6.9,
 "tenant_kinds": [
  "dev",
  "prod"
 ],
 "prod_pods": 2,
 "containers_without_memory_limit": 3
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-1-139</code></summary>

```json
{
 "node": "node-1-139",
 "tenant_count": 2,
 "memory_limits_gb": 46.1,
 "memory_requests_gb": 18.8,
 "pool": "default",
 "memory_limit_overcommit": 1.55,
 "namespaces": {
  "prod-app-o": 7,
  "dev-app-m": 4,
  "dev-app-o": 4,
  "prod-app-m": 4,
  "prod-app-l-backend": 4,
  "dev-app-n": 2,
  "dev-app-t": 2,
  "prod-app-r": 2,
  "external-secrets": 1,
  "prod-app-p": 1,
  "prod-app-n": 1,
  "app-s-prod": 1
 },
 "allocatable_memory_gb": 29.8,
 "tenant_kinds": [
  "dev",
  "prod"
 ],
 "prod_pods": 20,
 "containers_without_memory_limit": 0
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-2-218</code></summary>

```json
{
 "node": "node-2-218",
 "tenant_count": 3,
 "memory_limits_gb": 5.0,
 "memory_requests_gb": 1.7,
 "pool": "system-ondemand",
 "memory_limit_overcommit": 1.55,
 "namespaces": {
  "monitoring": 4,
  "arc-system": 1,
  "argocd": 1,
  "dev-app-t": 1,
  "keda": 1,
  "kube-system": 1,
  "middleware": 1,
  "prod-app-q": 1
 },
 "allocatable_memory_gb": 3.2,
 "tenant_kinds": [
  "dev",
  "other",
  "prod"
 ],
 "prod_pods": 1,
 "containers_without_memory_limit": 2
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-runners</code></summary>

```json
{
 "prod": false,
 "kind": "ci",
 "namespace": "arc-runners",
 "containers_without_memory_limit": 1,
 "pods": 1,
 "has_limitrange": false,
 "cpu_p95_7d": 0.471,
 "memory_p95_7d_gb": 1.96,
 "containers_without_requests": 1
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.argocd/argocd-server</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-74c4dcbda2",
 "lb_type": "application",
 "target": "argocd/argocd-server",
 "workloads": [
  "deployment/argocd-server"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-admin-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-ae7a7a06ff",
 "lb_type": "application",
 "target": "dev-app-n/app-n-admin-frontend",
 "workloads": [
  "deployment/app-n-admin-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-0987e78003",
 "lb_type": "application",
 "target": "dev-app-n/app-n-backend",
 "workloads": [
  "deployment/app-n-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-133751726c",
 "lb_type": "application",
 "target": "dev-app-n/app-n-frontend",
 "workloads": [
  "deployment/app-n-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-t/app-t-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-b347218b4f",
 "lb_type": "application",
 "target": "dev-app-t/app-t-backend",
 "workloads": [
  "deployment/app-t-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-t/app-t-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-e9834ca5fe",
 "lb_type": "application",
 "target": "dev-app-t/app-t-frontend",
 "workloads": [
  "deployment/app-t-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.middleware/kafka-ui</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-0a6256c8b2",
 "lb_type": "application",
 "target": "middleware/kafka-ui",
 "workloads": [
  "deployment/kafka-ui"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.middleware/redis-insight</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-e7e7fd218a",
 "lb_type": "application",
 "target": "middleware/redis-insight",
 "workloads": [
  "deployment/redis-insight"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-af0f3aa6c7",
 "lb_type": "application",
 "target": "monitoring/kube-prometheus-stack-grafana",
 "workloads": [
  "deployment/kube-prometheus-stack-grafana"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.monitoring/vmauth</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-e07e5153ee",
 "lb_type": "application",
 "target": "monitoring/vmauth",
 "workloads": [
  "deployment/vmauth"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-r/app-r</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-e238817282",
 "lb_type": "application",
 "target": "prod-app-r/app-r",
 "workloads": [
  "deployment/app-r"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-ai</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-fc2d368787",
 "lb_type": "application",
 "target": "prod-app-q/app-q-ai",
 "workloads": [
  "deployment/app-q-ai"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-bb495c72c8",
 "lb_type": "application",
 "target": "prod-app-q/app-q-backend",
 "workloads": [
  "deployment/app-q-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-studio</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-57e5adf3bf",
 "lb_type": "application",
 "target": "prod-app-q/app-q-studio",
 "workloads": [
  "deployment/app-q-studio"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-web</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-022a51fc31",
 "lb_type": "application",
 "target": "prod-app-q/app-q-web",
 "workloads": [
  "deployment/app-q-web"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-admin</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-37417ab44f",
 "lb_type": "application",
 "target": "prod-app-o/app-o-admin",
 "workloads": [
  "deployment/app-o-admin"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-ai</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-b22674073c",
 "lb_type": "application",
 "target": "prod-app-o/app-o-ai",
 "workloads": [
  "deployment/app-o-ai"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-89a3732998",
 "lb_type": "application",
 "target": "prod-app-o/app-o-backend",
 "workloads": [
  "deployment/app-o-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-032c25d752",
 "lb_type": "application",
 "target": "prod-app-o/app-o-frontend",
 "workloads": [
  "deployment/app-o-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-8c88bb317a",
 "lb_type": "application",
 "target": "prod-app-l-backend/app-l-backend",
 "workloads": [
  "deployment/app-l-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-9726e5b1d3",
 "lb_type": "application",
 "target": "prod-app-l-backend/app-l-frontend",
 "workloads": [
  "deployment/app-l-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-p/app-p-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-f68effe430",
 "lb_type": "application",
 "target": "prod-app-p/app-p-backend",
 "workloads": [
  "deployment/app-p-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-p/app-p-web</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-194ae69849",
 "lb_type": "application",
 "target": "prod-app-p/app-p-web",
 "workloads": [
  "deployment/app-p-web"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-d0c066d282",
 "lb_type": "application",
 "target": "prod-app-n/app-n-admin-frontend",
 "workloads": [
  "deployment/app-n-admin-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-7df87a92cc",
 "lb_type": "application",
 "target": "prod-app-n/app-n-backend",
 "workloads": [
  "deployment/app-n-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-36f816b829",
 "lb_type": "application",
 "target": "prod-app-n/app-n-frontend",
 "workloads": [
  "deployment/app-n-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.app-s-prod/app-s-backend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-bea446d347",
 "lb_type": "application",
 "target": "app-s-prod/app-s-backend",
 "workloads": [
  "deployment/app-s-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.app-s-prod/app-s-frontend</code></summary>

```json
{
 "deregistration_delay_s": 300,
 "backend_grace_s": 30,
 "backend_prestop": false,
 "name": "k8s-app-svc-e72ef00971",
 "lb_type": "application",
 "target": "app-s-prod/app-s-frontend",
 "workloads": [
  "deployment/app-s-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/argocd/argocd-server</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "deploy.my-cluster"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/argocd/argocd-server"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-m/app-m-admin</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "admin-dev.example-b.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/dev-app-m/app-m-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-o/app-o-admin</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "admin-dev.example-d.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/dev-app-o/app-o-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-n/app-n-admin-frontend</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "admin-dev.example-c.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/dev-app-n/app-n-admin-frontend"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-m/app-m-admin</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "canary-admin.example-b.ai",
  "admin.example-b.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/prod-app-m/app-m-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-o/app-o-admin</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "admin.example-d.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/prod-app-o/app-o-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "type": "ingress",
 "hosts": [
  "admin.example-c.ai"
 ],
 "admin_like": true,
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "tls": true,
 "target": "ingress/prod-app-n/app-n-admin-frontend"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-m/app-m-backend</code></summary>

```json
{
 "target": "prod-app-m/app-m-backend",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 95751.0,
  "requests_24h_equiv": 95751.0,
  "rps_avg": 1.108,
  "errors_5xx": 663.0,
  "errors_ratio": 0.00692,
  "p95_s_max_1h": 0.4879,
  "p95_s_avg": 0.1315,
  "p95_s_weighted": 0.2168,
  "p95_s_last_1h": 0.0544,
  "p95_s_last_at": "2026-11-05T07:02:00+00:00",
  "requests_last_1h": 1793.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-d65740e6d5"
  ]
 },
 "hosts": [
  "canary-api.example-b.ai",
  "api.example-b.ai"
 ]
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend</code></summary>

```json
{
 "target": "prod-app-m/app-m-frontend",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 54895.0,
  "requests_24h_equiv": 54895.0,
  "rps_avg": 0.635,
  "errors_5xx": 80.0,
  "errors_ratio": 0.00146,
  "p95_s_max_1h": 0.7156,
  "p95_s_avg": 0.2716,
  "p95_s_weighted": 0.2773,
  "p95_s_last_1h": 0.5082,
  "p95_s_last_at": "2026-11-05T07:02:00+00:00",
  "requests_last_1h": 3251.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-e87721a9c3"
  ]
 },
 "hosts": [
  "canary.example-b.ai",
  "www.example-b.ai",
  "example-b.ai"
 ]
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-n/app-n-frontend</code></summary>

```json
{
 "target": "prod-app-n/app-n-frontend",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 9883.0,
  "requests_24h_equiv": 9883.0,
  "rps_avg": 0.114,
  "errors_5xx": 26.0,
  "errors_ratio": 0.00263,
  "p95_s_max_1h": 2.3884,
  "p95_s_avg": 0.331,
  "p95_s_weighted": 0.6122,
  "p95_s_last_1h": 0.3111,
  "p95_s_last_at": "2026-11-05T07:02:00+00:00",
  "requests_last_1h": 390.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 1.0,
  "unhealthy_now": 1,
  "target_groups": [
   "k8s-app-svc-36f816b829"
  ]
 },
 "hosts": [
  "example-c.ai",
  "www.example-c.ai"
 ]
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "target": "monitoring/kube-prometheus-stack-grafana",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 56.0,
  "requests_24h_equiv": 56.0,
  "rps_avg": 0.001,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 5.8148,
  "p95_s_avg": 0.9895,
  "p95_s_weighted": 2.5054,
  "p95_s_last_1h": 0.0235,
  "p95_s_last_at": "2026-11-05T04:02:00+00:00",
  "requests_last_1h": 2.0,
  "hours_since_requests": 3,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-af0f3aa6c7"
  ]
 },
 "hosts": [
  "monitor.my-cluster"
 ]
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-q/app-q-ai</code></summary>

```json
{
 "target": "prod-app-q/app-q-ai",
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 15.0,
  "requests_24h_equiv": 15.0,
  "rps_avg": 0.0,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 2.6742,
  "p95_s_avg": 2.4097,
  "p95_s_weighted": 2.3216,
  "p95_s_last_1h": 2.1453,
  "p95_s_last_at": "2026-11-05T07:02:00+00:00",
  "requests_last_1h": 10.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-fc2d368787"
  ]
 },
 "hosts": [
  "app-q-ai.my-cluster"
 ]
}
```

</details>
<details><summary><code>traffic.pod-not-ready.arc-runners/self-hosted-arm64-8msc5-runner</code></summary>

```json
{
 "unhealthy_events": 0,
 "pods_below_99": 1,
 "workload": "arc-runners/self-hosted-arm64-8msc5-runner",
 "worst_pod": "self-hosted-arm64-8msc5-runner-4248d",
 "min_ready_ratio_24h": 0.9862,
 "not_ready_minutes_24h": 20
}
```

</details>
<details><summary><code>traffic.pod-not-ready.kube-system/ebs-csi-node</code></summary>

```json
{
 "unhealthy_events": 0,
 "pods_below_99": 1,
 "workload": "kube-system/ebs-csi-node",
 "worst_pod": "ebs-csi-node-f9n5j",
 "min_ready_ratio_24h": 0.9375,
 "not_ready_minutes_24h": 90
}
```

</details>
<details><summary><code>traffic.pod-not-ready.monitoring/loki-stack-promtail</code></summary>

```json
{
 "unhealthy_events": 0,
 "pods_below_99": 2,
 "workload": "monitoring/loki-stack-promtail",
 "worst_pod": "loki-stack-promtail-zgjxk",
 "min_ready_ratio_24h": 0.9375,
 "not_ready_minutes_24h": 90
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "emptydir_without_sizelimit": 21,
 "emptydir_without_sizelimit_prod": [
  "prod-app-q/statefulset/app-q-backend-postgresql",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/tts-proxy",
  "prod-app-p/deployment/app-p-backend",
  "prod-app-p/statefulset/app-p-postgresql",
  "app-s-prod/statefulset/app-s-backend-postgresql"
 ],
 "prod_without_request": 33,
 "request_ratio": 0.009,
 "containers": 111,
 "with_request": 1
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "revision_history_limits": {
  "10": 61,
  "3": 6
 },
 "replicasets_zero": 351,
 "replicasets_total": 418
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "prod": true,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "prod-app-l-backend",
 "name": "app-l-backend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 20.2,
 "current_cpu_utilization": 0,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "prod": true,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "prod-app-l-backend",
 "name": "app-l-frontend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 87.4,
 "current_cpu_utilization": 1,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-frontend"
}
```

</details>
<details><summary><code>storage.legacy-intree-storageclass.gp2</code></summary>

```json
{
 "key": null,
 "item": {
  "default": false,
  "name": "gp2",
  "provisioner": "kubernetes.io/aws-ebs",
  "parameters": {
   "fsType": "ext4",
   "type": "gp2"
  }
 }
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-117</code></summary>

```json
{
 "node": "node-1-117",
 "separation_possible": true,
 "shares_dev_prod": true,
 "dev_pods": 2,
 "cpu_limit_overcommit": 3.37,
 "pool": "system_core-20251217040546303900000001",
 "prod_namespaces": [
  "prod-app-o",
  "app-s-prod"
 ],
 "memory_limit_overcommit": 1.68,
 "dev_namespaces": [
  "dev-app-o",
  "dev-app-t"
 ],
 "prod_pods": 2,
 "containers_without_memory_limit": 3
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-139</code></summary>

```json
{
 "node": "node-1-139",
 "separation_possible": true,
 "shares_dev_prod": true,
 "dev_pods": 12,
 "cpu_limit_overcommit": 6.99,
 "pool": "default",
 "prod_namespaces": [
  "prod-app-r",
  "prod-app-m",
  "prod-app-o",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "memory_limit_overcommit": 1.55,
 "dev_namespaces": [
  "dev-app-m",
  "dev-app-o",
  "dev-app-n",
  "dev-app-t"
 ],
 "prod_pods": 20,
 "containers_without_memory_limit": 0
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-2-218</code></summary>

```json
{
 "node": "node-2-218",
 "separation_possible": true,
 "shares_dev_prod": true,
 "dev_pods": 1,
 "cpu_limit_overcommit": 1.55,
 "pool": "system-ondemand",
 "prod_namespaces": [
  "prod-app-q"
 ],
 "memory_limit_overcommit": 1.55,
 "dev_namespaces": [
  "dev-app-t"
 ],
 "prod_pods": 1,
 "containers_without_memory_limit": 2
}
```

</details>
<details><summary><code>albctl.aws-api-churn.cluster</code></summary>

```json
{
 "aws_api_slow_ops_avg_s": [
  [
   "Shield/GetSubscriptionState",
   0.759
  ],
  [
   "EC2/RevokeSecurityGroupIngress",
   0.317
  ],
  [
   "EC2/AuthorizeSecurityGroupIngress",
   0.295
  ],
  [
   "Elastic Load Balancing v2/RegisterTargets",
   0.283
  ],
  [
   "Elastic Load Balancing v2/CreateTargetGroup",
   0.266
  ]
 ],
 "metrics_available": true,
 "aws_api_calls_total": 241005,
 "aws_api_top_ops": [
  [
   "Elastic Load Balancing v2/DescribeTargetHealth",
   75710
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroupAttributes",
   42892
  ],
  [
   "EC2/DescribeInstances",
   38529
  ],
  [
   "EC2/DescribeSecurityGroups",
   24893
  ],
  [
   "Elastic Load Balancing v2/RegisterTargets",
   11739
  ],
  [
   "Elastic Load Balancing v2/DeregisterTargets",
   11609
  ],
  [
   "Elastic Load Balancing v2/DescribeTags",
   9114
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancers",
   3700
  ]
 ],
 "aws_api_retries_avg": 0.0,
 "rest_client_429_503": 126
}
```

</details>
<details><summary><code>alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "data_retention": "120h",
 "cluster_peers": 0,
 "present": true,
 "cluster_status": "disabled",
 "ready": 1,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager",
 "replicas": 1
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "applications_prod": 8,
 "notifications_triggers": 0,
 "notifications_configured": false
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "ignore_differences_apps": 3,
 "applications_prod": 8,
 "prod_tracking_moving_ref": [
  "argocd/application/app-r-prod",
  "argocd/application/app-q-prod",
  "argocd/application/app-m-prod",
  "argocd/application/app-o-prod",
  "argocd/application/app-s-prod",
  "argocd/application/app-l-backend-prod",
  "argocd/application/app-p-prod",
  "argocd/application/app-n-prod"
 ]
}
```

</details>
<details><summary><code>argocd.version-eol.cluster</code></summary>

```json
{
 "version": "2.13.0",
 "components": {
  "applicationset-controller": "1/1",
  "dex-server": "1/1",
  "notifications-controller": "1/1",
  "redis": "1/1",
  "repo-server": "1/1",
  "server": "1/1",
  "application-controller": "1/1"
 },
 "version_major": 2
}
```

</details>
<details><summary><code>coredns.aaaa-noise.cluster</code></summary>

```json
{
 "qps_total": 79.28,
 "metrics_available": true,
 "aaaa_ratio": 0.5,
 "cluster_ipv6": false
}
```

</details>
<details><summary><code>cost.idle-node.node-2-158</code></summary>

```json
{
 "node": "node-2-158",
 "cpu_p95_ratio": 0.02497745825366951,
 "pool": "build-arm64",
 "memory_p95_ratio": 0.1941742880824938,
 "monthly_usd": null,
 "instance_type": "c6gn.xlarge"
}
```

</details>
<details><summary><code>cost.idle-node.node-2-64</code></summary>

```json
{
 "node": "node-2-64",
 "cpu_p95_ratio": 0.030197817898433652,
 "pool": "default",
 "memory_p95_ratio": 0.26792339247832986,
 "monthly_usd": null,
 "instance_type": "c9g.large"
}
```

</details>
<details><summary><code>ebscsi.controller-metrics-disabled.cluster</code></summary>

```json
{
 "api_throttles_24h": null,
 "addon_version": "v1.37.0-eksbuild.1",
 "version": "1.37.0",
 "api_errors_24h": {},
 "controller_metrics_enabled": false,
 "controller_metrics_series": 0,
 "controller_present": true
}
```

</details>
<details><summary><code>eso.version-old.cluster</code></summary>

```json
{
 "version": "0.9.13",
 "pushsecrets": 0,
 "externalsecrets": 47
}
```

</details>
<details><summary><code>grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "ingress_hosts": [
  "monitor.my-cluster"
 ],
 "major": 10,
 "present": true,
 "version": "10.2.3",
 "stats": {
  "totals_dashboard": 28,
  "totals_datasource": 4,
  "total_users": 1,
  "active_users": 1,
  "totals_alert_rules": 0
 },
 "database": "ok",
 "target": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "tag_kind": "tag",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-admission-webhooks",
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.17.2",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "container": "keda-admission-webhooks"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "tag_kind": "tag",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator-metrics-apiserver",
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.17.2",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "container": "keda-operator-metrics-apiserver"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator</code></summary>

```json
{
 "tag_kind": "tag",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator",
 "image": "ghcr.io/kedacore/keda:2.17.2",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "container": "keda-operator"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent</code></summary>

```json
{
 "tag_kind": "tag",
 "always_pull_with_tag": true,
 "workload": "kube-system/daemonset/aws-node",
 "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1",
 "pull_policy": "Always",
 "registry": "<account>.dkr.ecr.us-east-1.amazonaws.com",
 "container": "aws-eks-nodeagent"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init</code></summary>

```json
{
 "tag_kind": "tag",
 "always_pull_with_tag": true,
 "workload": "kube-system/daemonset/aws-node",
 "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1",
 "pull_policy": "Always",
 "registry": "<account>.dkr.ecr.us-east-1.amazonaws.com",
 "container": "aws-vpc-cni-init"
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "zero_by_group": {
  "generators.external-secrets.io": 7,
  "monitoring.coreos.com": 6,
  "networking.k8s.aws": 4,
  "eventing.keda.sh": 2,
  "external-secrets.io": 3,
  "keda.sh": 2,
  "crd.k8s.amazonaws.com": 1,
  "vpcresources.k8s.aws": 1
 },
 "zero_object_count": 26,
 "count": 47,
 "webhooks": 18
}
```

</details>
<details><summary><code>karpenter.spot-to-spot-consolidation-off.cluster</code></summary>

```json
{
 "feature_gates": {
  "Drift": "true",
  "SpotToSpotConsolidation": "false"
 },
 "drift_enabled": true,
 "nodeclaims_terminated_by_reason": {
  "expiration": 6,
  "emptiness": 317,
  "interruption": 261,
  "consolidation": 279
 },
 "spot_to_spot_consolidation": false
}
```

</details>
<details><summary><code>keda.operator-metrics-disabled.cluster</code></summary>

```json
{
 "operator_prometheus_metrics": false,
 "operator_metrics_present": false,
 "unused": false,
 "scaler_errors_24h_logs": 0
}
```

</details>
<details><summary><code>keda.scaledobject-never-active.cluster</code></summary>

```json
{
 "never_active_14d": [
  "dev-app-o/scaledobject/app-o-ai-kafka-lag"
 ],
 "fallback_active": [],
 "not_ready": [],
 "scale_to_zero": [
  "prod-app-l-backend/scaledobject/app-l-file-worker",
  "prod-app-l-backend/scaledobject/app-l-graph-worker"
 ]
}
```

</details>
<details><summary><code>kubeproxy.conntrack-invalid-drops.cluster</code></summary>

```json
{
 "external_traffic_local": 0,
 "metrics_available": true,
 "no_local_endpoint_services": 0,
 "ct_invalid_dropped_1h": 1355
}
```

</details>
<details><summary><code>loki.version-old.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "major": 2,
 "compactor_running": 1.0,
 "present": true,
 "version": "2.6.1",
 "retention_applied": false,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/loki-stack"
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
 "rules_total": 141,
 "never_fired_15d": [
  "AlertmanagerClusterCrashlooping",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerFailedReload",
  "AlertmanagerFailedToSendAlerts",
  "AlertmanagerMembersInconsistent",
  "ConfigReloaderSidecarErrors",
  "PartnerAConsumerLagHigh",
  "PartnerAConsumerMembersBelowExpected",
  "AppMAngleBridgeMembersBelowExpected",
  "AppMBridgeLagHigh",
  "AppMBridgeMembersBelowExpected",
  "AppMEditBridgeLagHigh",
  "AppMEditBridgeMembersBelowExpected",
  "AppMGenerationFailing",
  "ImageInferenceE2ESuccessRateDrop",
  "ImageInferenceEntitlementFailureSpike",
  "KubeAPIDown",
  "KubeAPIErrorBudgetBurn",
  "KubeAPITerminatedRequests",
  "KubeAggregatedAPIDown",
  "KubeAggregatedAPIErrors",
  "KubeCPUQuotaOvercommit",
  "KubeClientCertificateExpiration",
  "KubeClientErrors",
  "KubeDaemonSetMisScheduled",
  "KubeDaemonSetNotScheduled",
  "KubeDaemonSetRolloutStuck",
  "KubeDeploymentGenerationMismatch",
  "KubeHpaReplicasMismatch",
  "KubeJobFailed",
  "KubeJobNotCompleted",
  "KubeMemoryQuotaOvercommit",
  "KubeNodeNotReady",
  "KubeNodeReadinessFlapping",
  "KubeNodeUnreachable",
  "KubePersistentVolumeErrors",
  "KubePersistentVolumeFillingUp",
  "KubePersistentVolumeInodesFillingUp",
  "KubePodCrashLooping",
  "KubeProxyDown",
  "KubeQuotaAlmostFull",
  "KubeQuotaExceeded",
  "KubeQuotaFullyUsed",
  "KubeStateMetricsListErrors",
  "KubeStateMetricsShardingMismatch",
  "KubeStateMetricsShardsMissing",
  "KubeStateMetricsWatchErrors",
  "KubeStatefulSetGenerationMismatch",
  "KubeStatefulSetReplicasMismatch",
  "KubeStatefulSetUpdateNotRolledOut",
  "KubeVersionMismatch",
  "KubeletClientCertificateExpiration",
  "KubeletClientCertificateRenewalErrors",
  "KubeletDown",
  "KubeletPlegDurationHigh",
  "KubeletPodStartUpLatencyHigh",
  "KubeletServerCertificateExpiration",
  "KubeletServerCertificateRenewalErrors",
  "KubeletTooManyPods",
  "LoraTrainingCallbackTimeout",
  "LoraTrainingDurationP95High",
  "LoraTrainingSuccessRateDrop",
  "NodeBondingDegraded",
  "NodeClockNotSynchronising",
  "NodeClockSkewDetected",
  "NodeDiskIOSaturation",
  "NodeFileDescriptorLimit",
  "NodeFilesystemAlmostOutOfFiles",
  "NodeFilesystemAlmostOutOfSpace",
  "NodeFilesystemFilesFillingUp",
  "NodeHighNumberConntrackEntriesUsed",
  "NodeMemoryHighUtilization",
  "NodeMemoryMajorPagesFaults",
  "NodeNetworkInterfaceFlapping",
  "NodeNetworkReceiveErrs",
  "NodeNetworkTransmitErrs",
  "NodeRAIDDegraded",
  "NodeRAIDDiskFailure",
  "NodeSystemdServiceFailed",
  "NodeTextFileCollectorScrapeError",
  "OnPremiseConsumerLagHigh",
  "OnPremiseConsumerMembersBelowExpected",
  "PrometheusBadConfig",
  "PrometheusDuplicateTimestamps",
  "PrometheusErrorSendingAlertsToAnyAlertmanager",
  "PrometheusErrorSendingAlertsToSomeAlertmanagers",
  "PrometheusHighQueryLoad",
  "PrometheusLabelLimitHit",
  "PrometheusMissingRuleEvaluations",
  "PrometheusNotConnectedToAlertmanagers",
  "PrometheusNotIngestingSamples",
  "PrometheusNotificationQueueRunningFull",
  "PrometheusOperatorListErrors",
  "PrometheusOperatorNodeLookupErrors",
  "PrometheusOperatorNotReady",
  "PrometheusOperatorReconcileErrors",
  "PrometheusOperatorRejectedResources",
  "PrometheusOperatorStatusUpdateErrors",
  "PrometheusOperatorSyncFailed",
  "PrometheusOperatorWatchErrors",
  "PrometheusOutOfOrderTimestamps",
  "PrometheusRemoteStorageFailures",
  "PrometheusRemoteWriteBehind",
  "PrometheusRemoteWriteDesiredShards",
  "PrometheusRuleFailures",
  "PrometheusSDRefreshFailure",
  "PrometheusScrapeBodySizeLimitHit",
  "PrometheusScrapeSampleLimitHit",
  "PrometheusTSDBCompactionsFailing",
  "PrometheusTSDBReloadsFailing",
  "PrometheusTargetLimitHit",
  "PrometheusTargetSyncFailure",
  "TargetDown",
  "etcdDatabaseHighFragmentationRatio",
  "etcdDatabaseQuotaLowSpace",
  "etcdExcessiveDatabaseGrowth",
  "etcdGRPCRequestsSlow",
  "etcdHighCommitDurations",
  "etcdHighFsyncDurations",
  "etcdHighNumberOfFailedGRPCRequests",
  "etcdHighNumberOfFailedProposals",
  "etcdHighNumberOfLeaderChanges",
  "etcdInsufficientMembers",
  "etcdMemberCommunicationSlow",
  "etcdMembersDown",
  "etcdNoLeader"
 ],
 "never_fired_count": 128,
 "fired_15d": [
  "CPUThrottlingHigh",
  "InfoInhibitor",
  "KubeContainerWaiting",
  "KubeControllerManagerDown",
  "KubeDeploymentReplicasMismatch",
  "KubeDeploymentRolloutStuck",
  "KubeHpaMaxedOut",
  "KubePodNotReady",
  "KubeSchedulerDown",
  "NodeCPUHighUsage",
  "NodeFilesystemSpaceFillingUp",
  "NodeSystemSaturation",
  "Watchdog"
 ]
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "ingresses": 40,
 "namespaces_with_saturation_metrics": [
  "default",
  "kube-system",
  "middleware",
  "monitoring"
 ],
 "missing_saturation": [
  {
   "namespace": "argocd",
   "ingress": "argocd-server",
   "class": "alb",
   "hosts": [
    "deploy.my-cluster"
   ],
   "services": [
    "argocd-server"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-m",
   "ingress": "app-m-admin",
   "class": "alb",
   "hosts": [
    "admin-dev.example-b.ai"
   ],
   "services": [
    "app-m-admin"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-m",
   "ingress": "app-m-api",
   "class": "alb",
   "hosts": [
    "api-dev.v1.example-b.ai"
   ],
   "services": [
    "app-m-api"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-m",
   "ingress": "app-m-backend",
   "class": "alb",
   "hosts": [
    "api-dev.example-b.ai"
   ],
   "services": [
    "app-m-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-m",
   "ingress": "app-m-frontend",
   "class": "alb",
   "hosts": [
    "dev.example-b.ai"
   ],
   "services": [
    "app-m-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-o",
   "ingress": "app-o-admin",
   "class": "alb",
   "hosts": [
    "admin-dev.example-d.ai"
   ],
   "services": [
    "app-o-admin"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-o",
   "ingress": "app-o-ai",
   "class": "alb",
   "hosts": [
    "ai-dev.example-d.ai"
   ],
   "services": [
    "app-o-ai"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-o",
   "ingress": "app-o-backend",
   "class": "alb",
   "hosts": [
    "app-o-api-dev.my-cluster"
   ],
   "services": [
    "app-o-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-o",
   "ingress": "app-o-frontend",
   "class": "alb",
   "hosts": [
    "app-o-dev.my-cluster"
   ],
   "services": [
    "app-o-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-n",
   "ingress": "app-n-admin-frontend",
   "class": "alb",
   "hosts": [
    "admin-dev.example-c.ai"
   ],
   "services": [
    "app-n-admin-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-n",
   "ingress": "app-n-backend",
   "class": "alb",
   "hosts": [
    "api-dev.example-c.ai"
   ],
   "services": [
    "app-n-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-n",
   "ingress": "app-n-frontend",
   "class": "alb",
   "hosts": [
    "dev.example-c.ai"
   ],
   "services": [
    "app-n-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-t",
   "ingress": "app-t-backend",
   "class": "alb",
   "hosts": [
    "demo-api.example-d.ai"
   ],
   "services": [
    "app-t-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-t",
   "ingress": "app-t-frontend",
   "class": "alb",
   "hosts": [
    "demo.example-d.ai"
   ],
   "services": [
    "app-t-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-r",
   "ingress": "app-r",
   "class": "alb",
   "hosts": [
    "app-r.my-cluster"
   ],
   "services": [
    "app-r"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-q",
   "ingress": "app-q-ai",
   "class": "alb",
   "hosts": [
    "app-q-ai.my-cluster"
   ],
   "services": [
    "app-q-ai"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-q",
   "ingress": "app-q-backend",
   "class": "alb",
   "hosts": [
    "app-q-api.my-cluster"
   ],
   "services": [
    "app-q-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-q",
   "ingress": "app-q-studio",
   "class": "alb",
   "hosts": [
    "app-q-studio.my-cluster"
   ],
   "services": [
    "app-q-studio"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-q",
   "ingress": "app-q-web",
   "class": "alb",
   "hosts": [
    "app-q.my-cluster"
   ],
   "services": [
    "app-q-web"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-m",
   "ingress": "app-m-admin",
   "class": "alb",
   "hosts": [
    "canary-admin.example-b.ai",
    "admin.example-b.ai"
   ],
   "services": [
    "app-m-admin"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-m",
   "ingress": "app-m-api",
   "class": "alb",
   "hosts": [
    "canary-api-v1.example-b.ai",
    "api.v1.example-b.ai"
   ],
   "services": [
    "app-m-api"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-m",
   "ingress": "app-m-backend",
   "class": "alb",
   "hosts": [
    "canary-api.example-b.ai",
    "api.example-b.ai"
   ],
   "services": [
    "app-m-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-m",
   "ingress": "app-m-frontend",
   "class": "alb",
   "hosts": [
    "canary.example-b.ai",
    "www.example-b.ai",
    "example-b.ai"
   ],
   "services": [
    "app-m-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-o",
   "ingress": "app-o-admin",
   "class": "alb",
   "hosts": [
    "admin.example-d.ai"
   ],
   "services": [
    "app-o-admin"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-o",
   "ingress": "app-o-ai",
   "class": "alb",
   "hosts": [
    "ai.example-d.ai"
   ],
   "services": [
    "app-o-ai"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-o",
   "ingress": "app-o-backend",
   "class": "alb",
   "hosts": [
    "api.example-d.ai"
   ],
   "services": [
    "app-o-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-o",
   "ingress": "app-o-frontend",
   "class": "alb",
   "hosts": [
    "example-d.ai",
    "www.example-d.ai"
   ],
   "services": [
    "app-o-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-l-backend",
   "ingress": "app-l-backend",
   "class": "alb",
   "hosts": [
    "app-l-api.my-cluster"
   ],
   "services": [
    "app-l-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-l-backend",
   "ingress": "app-l-frontend",
   "class": "alb",
   "hosts": [
    "app-l.my-cluster"
   ],
   "services": [
    "app-l-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-p",
   "ingress": "app-p-backend",
   "class": "alb",
   "hosts": [
    "app-p-api.my-cluster"
   ],
   "services": [
    "app-p-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-p",
   "ingress": "app-p-web",
   "class": "alb",
   "hosts": [
    "app-p.my-cluster"
   ],
   "services": [
    "app-p-web"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-n",
   "ingress": "app-n-admin-frontend",
   "class": "alb",
   "hosts": [
    "admin.example-c.ai"
   ],
   "services": [
    "app-n-admin-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-n",
   "ingress": "app-n-backend",
   "class": "alb",
   "hosts": [
    "api.example-c.ai"
   ],
   "services": [
    "app-n-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-n",
   "ingress": "app-n-frontend",
   "class": "alb",
   "hosts": [
    "example-c.ai",
    "www.example-c.ai"
   ],
   "services": [
    "app-n-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-s-prod",
   "ingress": "app-s-backend",
   "class": "alb",
   "hosts": [
    "app-s-tp-api.my-cluster"
   ],
   "services": [
    "app-s-backend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-s-prod",
   "ingress": "app-s-frontend",
   "class": "alb",
   "hosts": [
    "app-s-tp-prod.my-cluster"
   ],
   "services": [
    "app-s-frontend"
   ],
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  }
 ]
}
```

</details>
<details><summary><code>observability.severity-channels-not-separated.cluster</code></summary>

```json
{
 "routes": [
  {
   "depth": 0,
   "receiver": "slack-system",
   "matchers": null,
   "continue": false,
   "group_by": [
    "namespace"
   ],
   "repeat_interval": "12h"
  },
  {
   "depth": 1,
   "receiver": "null",
   "matchers": [
    "alertname=\"Watchdog\""
   ],
   "continue": false,
   "group_by": null,
   "repeat_interval": null
  },
  {
   "depth": 1,
   "receiver": "slack-sre",
   "matchers": [
    "env=\"prod\"",
    "service=\"image-inference\"",
    "slo=\"img-inference\""
   ],
   "continue": false,
   "group_by": null,
   "repeat_interval": null
  },
  {
   "depth": 1,
   "receiver": "slack-sre",
   "matchers": [
    "env=\"prod\"",
    "service=\"lora-training\"",
    "slo=\"lora-training\""
   ],
   "continue": false,
   "group_by": null,
   "repeat_interval": null
  }
 ],
 "default_receiver": "slack-system",
 "receivers": {
  "null": [],
  "slack-sre": [
   "slack"
  ],
  "slack-system": [
   "slack"
  ]
 }
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "files_scanned": [
  "logs/pods/actions-runner-controller/arc-system_arc-gha-rs-controller.log",
  "logs/pods/alb-controller/kube-system_aws-load-balancer-controller.log",
  "logs/pods/argocd/argocd_argocd-application-controller.log",
  "logs/pods/argocd/argocd_argocd-applicationset-controller.log",
  "logs/pods/argocd/argocd_argocd-notifications-controller.log",
  "logs/pods/argocd/argocd_argocd-repo-server.log",
  "logs/pods/argocd/argocd_argocd-server.log",
  "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log",
  "logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log",
  "logs/pods/ebs-csi/kube-system_ebs-csi-node.log",
  "logs/pods/external-dns/kube-system_external-dns.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-cert-controller.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-webhook.log",
  "logs/pods/external-secrets/external-secrets_external-secrets.log",
  "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log",
  "logs/pods/karpenter/karpenter_karpenter.log",
  "logs/pods/keda/keda_keda-operator.log",
  "logs/pods/kube-proxy/kube-system_kube-proxy.log",
  "logs/pods/loki/monitoring_loki-stack.log",
  "logs/pods/metrics-server/kube-system_metrics-server.log",
  "logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log",
  "logs/pods/promtail/monitoring_loki-stack-promtail.log",
  "logs/pods/vpc-cni/kube-system_aws-node.log"
 ],
 "lines_scanned": 23768,
 "unclassified_errors": [
  {
   "pattern": "grafana | logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=admin fromAlert=false t=<ts> level=error msg=\"Er",
   "count": 12,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 12
   },
   "sample": "[pod/kube-prometheus-stack-grafana-7c9959564d-w8qx7/grafana] 2026-11-05T00:48:02.570707587Z logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=admin fromAlert=false t=2026-11-05T00:48:02.570517672Z l"
  },
  {
   "pattern": "ebs-csi | \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node node-2-64",
   "count": 10,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log": 5,
    "logs/pods/ebs-csi/kube-system_ebs-csi-node.log": 5
   },
   "sample": "[pod/ebs-csi-node-f9n5j/ebs-plugin] 2026-11-05T07:55:24.239902036Z E1105 07:55:24.239847       1 node.go:857] \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node node-2-64"
  },
  {
   "pattern": "kube-proxy | \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted on all loca",
   "count": 3,
   "files": {
    "logs/pods/kube-proxy/kube-system_kube-proxy.log": 3
   },
   "sample": "[pod/kube-proxy-gt6jd/kube-proxy] 2026-11-05T07:55:00.087767464Z E1105 07:55:00.087581       1 server.go:234] \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted o"
  },
  {
   "pattern": "ebs-csi | \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node node-<n>",
   "count": 2,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log": 1,
    "logs/pods/ebs-csi/kube-system_ebs-csi-node.log": 1
   },
   "sample": "[pod/ebs-csi-node-fcjd4/ebs-plugin] 2026-11-05T06:50:46.843341208Z E1105 06:50:46.843247       1 node.go:857] \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node node-2-158"
  },
  {
   "pattern": "grafana | logger=http.server t=<ts> level=error msg=\"Failed to parse user ID\" error=\"identifier is not initialized\"",
   "count": 1,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 1
   },
   "sample": "[pod/kube-prometheus-stack-grafana-7c9959564d-w8qx7/grafana] 2026-11-05T01:55:16.616453134Z logger=http.server t=2026-11-05T01:55:16.616342688Z level=error msg=\"Failed to parse user ID\" error=\"identifier is not initialized\""
  }
 ],
 "error_lines_unclassified": 28
}
```

</details>
<details><summary><code>observability.unstructured-logs.argocd</code></summary>

```json
{
 "json_ratio": 0.0,
 "json_lines_1h": 0,
 "namespace": "argocd",
 "lines_1h": 18433
}
```

</details>
<details><summary><code>observability.unstructured-logs.dev-app-n</code></summary>

```json
{
 "json_ratio": 0.0,
 "json_lines_1h": 0,
 "namespace": "dev-app-n",
 "lines_1h": 59518
}
```

</details>
<details><summary><code>observability.unstructured-logs.app-s-prod</code></summary>

```json
{
 "json_ratio": 0.0,
 "json_lines_1h": 0,
 "namespace": "app-s-prod",
 "lines_1h": 946512
}
```

</details>
<details><summary><code>prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "present": true,
 "start_time": "2026-10-06T12:32:07.180790214Z",
 "ready": 1,
 "restarts": 1,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "replicas": 1
}
```

</details>
<details><summary><code>prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "present": true,
 "version": "2.49.1",
 "major": 2,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "dev-app-m/statefulset/app-m-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "dev-app-o/statefulset/app-o-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "dev-app-n/statefulset/app-n-backend-dev-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-t/statefulset/app-t-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "dev-app-t/statefulset/app-t-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-t/statefulset/app-t-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "dev-app-t/statefulset/app-t-postgres",
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/aws-node:aws-node</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "workload": "kube-system/daemonset/aws-node",
 "readiness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 1
 },
 "liveness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "container": "aws-node"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "workload": "kube-system/daemonset/ebs-csi-node-windows",
 "readiness": null,
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "node-driver-registrar"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "workload": "kube-system/daemonset/ebs-csi-node",
 "readiness": null,
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "node-driver-registrar"
}
```

</details>
<details><summary><code>resilience.exec-probe.middleware/statefulset/redis-master:redis</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "workload": "middleware/statefulset/redis-master",
 "readiness": {
  "type": "exec",
  "path": "sh -c /health/ping_readiness_local.sh 1",
  "port": null,
  "timeout_s": 2,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "liveness": {
  "type": "exec",
  "path": "sh -c /health/ping_liveness_local.sh 5",
  "port": null,
  "timeout_s": 6,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-q/statefulset/app-q-backend-postgresql:postgresql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "workload": "prod-app-q/statefulset/app-q-backend-postgresql",
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-q\" -d \"dbname=app-q\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-q\" -d \"dbname=app-q\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "container": "postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "prod-app-m/statefulset/app-m-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "prod-app-o/statefulset/app-o-backend-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-l-backend/deployment/app-l-file-worker:file-worker</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "workload": "prod-app-l-backend/deployment/app-l-file-worker",
 "readiness": null,
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.FileWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "file-worker"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "workload": "prod-app-l-backend/deployment/app-l-graph-worker",
 "readiness": null,
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.GraphWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "graph-worker"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-p/statefulset/app-p-postgresql:postgresql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "workload": "prod-app-p/statefulset/app-p-postgresql",
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-p\" -d \"dbname=app-p\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-p\" -d \"dbname=app-p\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "container": "postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "workload": "prod-app-n/statefulset/app-n-backend-prod-mysql",
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-s-prod/statefulset/app-s-backend-postgresql:postgresql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "workload": "app-s-prod/statefulset/app-s-backend-postgresql",
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-s-user\" -d \"dbname=app-s_tp\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-s-user\" -d \"dbname=app-s_tp\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "container": "postgresql"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-ai:ai</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-q/deployment/app-q-ai",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "ai"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-backend:backend</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-q/deployment/app-q-backend",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-studio:studio</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-q/deployment/app-q-studio",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "studio"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-web:web</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-q/deployment/app-q-web",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "same_path": true,
 "container": "web"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-admin:admin</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-m/deployment/app-m-admin",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "admin"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-api:api</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-m/deployment/app-m-api",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "api"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-backend:backend</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-m/deployment/app-m-backend",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-frontend:frontend</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-m/deployment/app-m-frontend",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-l-backend/deployment/app-l-backend:backend</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-l-backend/deployment/app-l-backend",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-p/deployment/app-p-backend:backend</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-p/deployment/app-p-backend",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "same_path": true,
 "container": "backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-p/deployment/app-p-web:web</code></summary>

```json
{
 "prod": true,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "dependency_liveness": false,
 "workload": "prod-app-p/deployment/app-p-web",
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "same_path": true,
 "container": "web"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-r/app-r</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-q/app-q-ai</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-q/app-q-backend</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-q/app-q-studio</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-q/app-q-web</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-o/app-o-admin</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-o/app-o-ai</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-o/app-o-backend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-o/app-o-frontend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-l-backend/app-l-backend</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-l-backend/app-l-embedding-server</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-embedding-server",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-l-backend/app-l-frontend</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-l-backend/app-l-pg-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-pg-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-l-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-p/app-p-backend</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-p/app-p-web</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-n/app-n-backend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-n/app-n-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-s-prod/app-s-backend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-s-prod/app-s-frontend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server</code></summary>

```json
{
 "labels": {
  "namespace": "argocd",
  "pod": "argocd-repo-server-d487895cc-bth22",
  "container": "repo-server"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.1796886444091797,
  "memory_p95_7d_bytes": 96469606.4,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-m",
  "pod": "app-m-backend-76775dbdd-ttz69",
  "container": "backend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.31087799072265626,
  "memory_p95_7d_bytes": 83450675.2,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-ai-7cdbdc7544-szzcl",
  "container": "ai"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.3339500427246094,
  "memory_p95_7d_bytes": 358576128.0,
  "container_memory_request_bytes": 1073741824.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-o",
  "pod": "app-o-backend-69dbdf4f65-9x6jc",
  "container": "backend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.25682830810546875,
  "memory_p95_7d_bytes": 137883648.0,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-t",
  "pod": "app-t-postgres-0",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.<account>,
  "memory_p95_7d_bytes": 29425664.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller</code></summary>

```json
{
 "labels": {
  "namespace": "karpenter",
  "pod": "karpenter-9769889bd-nphgs",
  "container": "controller"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.0939178466796875,
  "memory_p95_7d_bytes": 25210880.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.middleware/sts/redis-master:redis</code></summary>

```json
{
 "labels": {
  "namespace": "middleware",
  "pod": "redis-master-0",
  "container": "redis"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.0212860107421875,
  "memory_p95_7d_bytes": 5713920.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.monitoring/sts/vm-single:vmsingle</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "vm-single-0",
  "container": "vmsingle"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.3214740753173828,
  "memory_p95_7d_bytes": 172590080.0,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-q",
  "pod": "app-q-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.20465164184570311,
  "memory_p95_7d_bytes": 54935756.8,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-ai:ai</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-ai-55b7448547-mzrjj",
   "container": "ai"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.3322715759277344,
   "memory_p95_7d_bytes": 713547776.0,
   "container_memory_request_bytes": 2147483648.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-ai-55b7448547-mpj4r",
   "container": "ai"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.20062828063964844,
   "memory_p95_7d_bytes": 430845952.0,
   "container_memory_request_bytes": 2147483648.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-backend-596479b6f8-cx44t",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.19206161499023439,
   "memory_p95_7d_bytes": 103112294.4,
   "container_memory_request_bytes": 536870912.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-o",
   "pod": "app-o-backend-596479b6f8-nv9j2",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.1577564239501953,
   "memory_p95_7d_bytes": 84694835.19999999,
   "container_memory_request_bytes": 536870912.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-frontend-6d58bbfcfc-nfk9x",
   "container": "frontend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.30987396240234377,
   "memory_p95_7d_bytes": 83181158.4,
   "container_memory_request_bytes": 268435456.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-l-backend",
   "pod": "app-l-frontend-6d58bbfcfc-2qgs6",
   "container": "frontend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.29246368408203127,
   "memory_p95_7d_bytes": 78507622.4,
   "container_memory_request_bytes": 268435456.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-l-backend",
  "pod": "app-l-neo4j-0",
  "container": "neo4j"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2380896091461181,
  "memory_p95_7d_bytes": 1022587084.7999997,
  "container_memory_request_bytes": 4294967296.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "app-s-prod",
  "pod": "app-s-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2166748046875,
  "memory_p95_7d_bytes": 58163200.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "prod": true,
 "name": "app-l-backend",
 "namespace": "prod-app-l-backend",
 "target_cpu_utilization": 70,
 "current_cpu_utilization": 0,
 "metric_types": [
  "cpu"
 ],
 "cpu_only": true,
 "target": "prod-app-l-backend/deployment/app-l-backend"
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "prod": true,
 "name": "app-l-frontend",
 "namespace": "prod-app-l-backend",
 "target_cpu_utilization": 70,
 "current_cpu_utilization": 1,
 "metric_types": [
  "cpu"
 ],
 "cpu_only": true,
 "target": "prod-app-l-backend/deployment/app-l-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-m",
 "name": "app-m-admin",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 168.8,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-m/deployment/app-m-admin"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-m",
 "name": "app-m-api",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 198.5,
 "current_cpu_utilization": 12,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-m/deployment/app-m-api"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-m",
 "name": "app-m-backend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 69.3,
 "current_cpu_utilization": 20,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-m/deployment/app-m-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-o",
 "name": "app-o-admin",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 58.4,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-o/deployment/app-o-admin"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-o",
 "name": "app-o-backend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 20.4,
 "current_cpu_utilization": 12,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-o/deployment/app-o-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-o",
 "name": "app-o-frontend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 20.4,
 "current_cpu_utilization": 20,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-o/deployment/app-o-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-n",
 "name": "app-n-admin-frontend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 38.8,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-n/deployment/app-n-admin-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-n",
 "name": "app-n-backend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 42.8,
 "current_cpu_utilization": 14,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-n/deployment/app-n-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-frontend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-n",
 "name": "app-n-frontend",
 "at_min_ratio_15d": 0.9986111111111098,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 3.3,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-n/deployment/app-n-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-t/deployment/app-t-backend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "dev-app-t",
 "name": "app-t-backend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": 22.4,
 "current_cpu_utilization": 0,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-t/deployment/app-t-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-t/deployment/app-t-frontend</code></summary>

```json
{
 "prod": false,
 "never_scaled_15d": true,
 "keda_owned": false,
 "max": 2,
 "namespace": "dev-app-t",
 "name": "app-t-frontend",
 "at_min_ratio_15d": 1.0,
 "target_cpu_utilization": 70,
 "days_since_last_scale": null,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "target": "dev-app-t/deployment/app-t-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "desired_changes_7d": 0.0,
 "prod": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "prod-app-l-backend",
 "name": "app-l-backend",
 "target": "prod-app-l-backend/deployment/app-l-backend",
 "min": 2,
 "has_behavior": false
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "desired_changes_7d": 0.0,
 "prod": true,
 "keda_owned": false,
 "max": 3,
 "namespace": "prod-app-l-backend",
 "name": "app-l-frontend",
 "target": "prod-app-l-backend/deployment/app-l-frontend",
 "min": 2,
 "has_behavior": false
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-r/app-r</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-q/app-q-ai</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-q/app-q-backend</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-q/app-q-studio</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-q/app-q-web</code></summary>

```json
{
 "namespace": "prod-app-q",
 "name": "app-q-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-m/app-m-admin</code></summary>

```json
{
 "namespace": "prod-app-m",
 "name": "app-m-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-m/app-m-api</code></summary>

```json
{
 "namespace": "prod-app-m",
 "name": "app-m-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-m/app-m-backend</code></summary>

```json
{
 "namespace": "prod-app-m",
 "name": "app-m-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-m/app-m-frontend</code></summary>

```json
{
 "namespace": "prod-app-m",
 "name": "app-m-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-o/app-o-admin</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-o/app-o-backend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-o/app-o-frontend</code></summary>

```json
{
 "namespace": "prod-app-o",
 "name": "app-o-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-l-backend/app-l-embedding-server</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "app-l-embedding-server",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-l-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-l-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-p/app-p-backend</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-p/app-p-web</code></summary>

```json
{
 "namespace": "prod-app-p",
 "name": "app-p-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-n/app-n-backend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-n/app-n-frontend</code></summary>

```json
{
 "namespace": "prod-app-n",
 "name": "app-n-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-s-prod/app-s-backend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-s-prod/app-s-frontend</code></summary>

```json
{
 "namespace": "app-s-prod",
 "name": "app-s-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-62</code></summary>

```json
{
 "node": "node-1-62",
 "separation_possible": true,
 "shares_dev_prod": true,
 "dev_pods": 1,
 "cpu_limit_overcommit": 4.72,
 "pool": "default",
 "prod_namespaces": [
  "prod-app-q",
  "prod-app-m",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "memory_limit_overcommit": 0.88,
 "dev_namespaces": [
  "dev-app-n"
 ],
 "prod_pods": 13,
 "containers_without_memory_limit": 0
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-2-60</code></summary>

```json
{
 "node": "node-2-60",
 "separation_possible": true,
 "shares_dev_prod": true,
 "dev_pods": 2,
 "cpu_limit_overcommit": 2.44,
 "pool": "system_core-20251217040546303900000001",
 "prod_namespaces": [
  "prod-app-m",
  "prod-app-n"
 ],
 "memory_limit_overcommit": 1.49,
 "dev_namespaces": [
  "dev-app-m",
  "dev-app-n"
 ],
 "prod_pods": 2,
 "containers_without_memory_limit": 2
}
```

</details>
<details><summary><code>traffic.alb-protection-off.k8s-shared-alb</code></summary>

```json
{
 "type": "application",
 "target_groups": 40,
 "deletion_protection": false,
 "name": "k8s-shared-alb",
 "access_logs": false
}
```

</details>
<details><summary><code>vpccni.warm-pool-whole-eni.cluster</code></summary>

```json
{
 "idle_ips_total": 0,
 "subnets_low": [
  "subnet-a"
 ],
 "warm_eni_target": 1,
 "policy": "whole_eni",
 "min_subnet_available": 61,
 "warm_ip_target": null
}
```

</details>

### 7-6. Tool notes (about kubegap itself)

1. diff.json findings.persisted lists only 60 rows, so the run count of findings such as traffic.alb-unhealthy-targets.* and resilience.replicas-same-node.* cannot be read per finding; it had to be checked against the previous findings-draft.json.
2. No check reports a NodeClaim past its NodePool expireAfter or a node blocked by karpenter.sh/do-not-disrupt. Here NodeClaim default-n44bh was 12 days past 720h, with 21327 DisruptionBlocked events in events.json items[46]. This is a candidate for a new check.

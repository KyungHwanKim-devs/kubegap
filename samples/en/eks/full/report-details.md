# kubegap report details — arn:aws:eks:us-east-1:<account>:cluster/my-cluster (`my-cluster`), full mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the LLM's fragments in `llm/`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `my-cluster` / arn:aws:eks:us-east-1:<account>:cluster/my-cluster (eks, v1.32.13-eks-577a51e) |
| Run time / mode | 2026-11-03T11:17:15+09:00 / full (collection 315.2 s, 0 steps skipped by mode, 5 failed) |
| Profile | `prod` (detected) |
| kubegap / rubric / signatures | 0.1.2 / 0.1.63 / 1.0.15 |
| Nodes / namespaces / pods / CRDs | 8 (Ready 8) / 25 / 145 / 47 |
| Components (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics store | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| Log store | loki 2.6.1 |
| Node access | ssm (EKS: SSM send-command); SSM unregistered 2 |
| Snapshot | `~/.kubegap/snapshots/my-cluster/2026-11-03T11-17-15` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 1 | 2 | fail +0 · warn +0 |
| high | 32 | 25 | fail -4 · warn +2 |
| medium | 111 | 167 | fail +4 · warn -3 |
| low | 16 | 138 | fail -2 · warn +2 |
| info | 2 | 0 | no previous run of this mode |

Checks 365: evaluated 358, disabled by profile 2, skipped 3, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

### Severities

| finding id | first pass | final | reason |
|---|---|---|---|
| `observability.failure-mode-uncovered.OOMKill` | fail/high | fail/critical | Rule ①, symptom seen. `prod-app-q/app-q-ai` was OOM-killed three times on 2026-11-02, at 08:34, 08:35 and 09:38 UTC, according to the kernel lines in logs/node/node-1-62/os.txt. No alert fired, because no rule covers OOM kills. |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail/medium | fail/high | Raised one level. The node it pins holds 20 of 42 prod pods, is 241.4 hours past its 720-hour expiry and has its root disk 82% full. It is the node problem 2 of report.md is about. |
| `resilience.n-plus-one.cluster` | pass | warn/high | Added by the LLM. The check passed only because of its 2% margin: requests are 47.47 GB against 46.6 GB of allocatable memory without the largest node. 31 of the pods on that node can only run on nodes labeled `workload-type=app`. The only other such node, `ip-10-0-1-62`, has 0.16 cores of CPU request room. A warn with Karpenter present is high under rule ③. |
| `observability.no-symptom-alerts.cluster` | warn/critical | warn/high | Rule ③, warn means high. The rules `ImageInferenceE2ESuccessRateDrop`, `LoraTrainingSuccessRateDrop` and `LoraTrainingDurationP95High` are real user-facing symptom alerts for app-m. The other seven prod products have none. |
| `observability.no-slo.cluster` | warn/critical | warn/high | Rule ③, warn means high. Five rules labeled `slo=img-inference` or `slo=lora-training` route to `slack-sre`. There are no SLI recording rules and no burn-rate alerts. |
| `traffic.db-exposed.nlb/acme-db-shared` | fail/high | warn/low | Lowered two levels. The NLB carries security group `sg-db-shared-nlb`, named "Shared NLB for dev/prod MySQL (office IP only)". It allows 3306–3311, 5432, 5433, 6379 and 7687 only from four /32 addresses, read in extra/nlb-security-groups.txt. It is still an internet-facing load balancer in front of production databases, so it stays as a warn. |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | fail/high | warn/low | Lowered two levels. These are KEDA scale-from-zero queue workers. Each pending pod was nominated to a new Karpenter NodeClaim within 2 seconds and started about 100 seconds later, according to events.json from 01:41:06 to 01:42:45 UTC. That is the designed path, and no user request waits on it. |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` | warn/high | warn/low | Same reason as app-l-file-worker. |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn/high | warn/low | Lowered two levels. A CI runner pod waited for the tainted `build-arm64` pool to add a node. CI only, no user impact. |
| `events.tracked-warning-reasons.FailedScheduling` | fail/high | fail/medium | All 12 events in this window are the KEDA workers above. They stay as a medium design signal: the app nodes have so little CPU request room that every worker needs a new node. |
| `events.tracked-warning-reasons.UpdateFailed` | warn/high | warn/low | Lowered two levels. Every occurrence is the dev ExternalSecret `database/mysql-app-n-secret`, which has failed since December 2025. It is not prod. |
| `logs.signatures.external-secrets.provider-error` | warn/high | warn/low | Same cause as `UpdateFailed`. |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | warn/high | warn/medium | Ended event. The last occurrence was 2026-10-27T05:55:55Z. The disk problem itself stays under `node.disk-usage` at high. |
| `vpccni.node-ip-exhaustion.node-1-139` | fail/high | fail/medium | 34 of 56 IPs are used, leaving 22 free. The 4 "no available IP" events are cumulative since ipamd started on a node that has been up 40.1 days. |
| `vpccni.node-ip-exhaustion.node-1-241` | warn/high | warn/medium | System node with max-pods 11. Six of nine IPs used and no allocation failures. |
| `vpccni.node-ip-exhaustion.node-2-218` | warn/high | warn/medium | System node with max-pods 17. 13 of 15 IPs used and no allocation failures. |
| `eks.service-quota-near-limit.aws-account` | warn/high | warn/low | Lowered two levels. The highest ratio is 3 of 5 VPCs. No operational quota is above 47%. |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | fail/high | fail/medium | One OOM in 171 days. The previous container ran from 2026-05-12 to 2026-10-30, per objects/pods.json. The 7-day memory p95 is 51% of the 768 Mi limit. Argo CD is not on the request path. |
| `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` | warn/high | warn/medium | Same single OOM. |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn/high | warn/low | Lowered two levels. It is not crash-looping. The 42 restarts are lifetime counts since 2026-03-13, and at most one happened after 2026-05-12. |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | warn/high | warn/medium | The OOM was 9.1 days ago. It is handled with the observability stack storage item. |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn/high | warn/medium | The OOM was 27.6 days ago. Same group. |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn/high | warn/medium | Working set is 73.8% of the 1536 Mi limit, with no OOM in the last 27 days. |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn/high | warn/medium | Monitoring only, with no rule evaluations missed in 1 day. |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | fail/high | fail/medium | Log shipper only. A promtail OOM loses logs, not user requests. |
| `observability.loki-oomkilled.cluster` | fail/high | fail/medium | A single OOM on 2026-10-25. It belongs to the observability stack storage item. |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | fail/high | fail/medium | The 5-minute throttle ratio is 0.26. The ALB p95 for this frontend is 0.22 s on average and 0.54 s in the worst hour, so users see no effect yet. The 7-day limit usage p95 is 8%. |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn/high | warn/low | Dev namespace. |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn/high | warn/low | Dev namespace. |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail/high | fail/low | Dev namespace. Tool note 26 still applies. |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail/high | fail/low | Dev namespace with 0 requests in 24 hours. |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | fail/high | fail/medium | This is a Tailscale sidecar. NET_ADMIN and /dev/net/tun are what Tailscale needs to build its tunnel. It is kept as a medium because the pod also runs as root, is BestEffort and uses `tailscale/tailscale:latest`. |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | fail/high | fail/medium | Dev database at 90.2% of 9.7 GB, growing 0.0 GB a day. |
| `logs.signatures.containerd.shim-error` | fail/medium | fail/low | The lines are "cleaning up after shim disconnected" warnings. They match the app-q-ai crash loops, the KEDA workers and the three node removals in this window. |
| `observability.alerts-always-firing.KubePodNotReady` | fail/medium | fail/low | Ended. The alert is not firing now. The 20 Failed pods behind it are gone, and the 169,042 samples are history from the 7-day window. |
| `controlplane.apiserver-latency.LIST` | warn/medium | warn/low | Measured during collection. The query is a 5-minute rate taken while kubegap was listing objects, so it likely includes kubegap itself. |
| `controlplane.apiserver-latency.PATCH` | warn/medium | warn/low | Same 5-minute window. It overlaps the removal of three Karpenter nodes between 02:03 and 02:13 UTC. |
| `node.network-errors.<ip>:9100:eth0` | warn/medium | warn/info | Lowered two levels. Karpenter removed the node at 2026-11-02T05:09:54Z, and it is not in inventory.json. |

### Recounted aggregates

| finding id | first pass | final | reason |
|---|---|---|---|
| `observability.no-symptom-alerts.cluster` | 0 symptom rules of 157 | 3 symptom rules, all for app-m | `ImageInferenceE2ESuccessRateDrop` fires on an end-to-end success ratio below 0.95. `LoraTrainingSuccessRateDrop` fires on a success ratio below 0.99. `LoraTrainingDurationP95High` fires on a p95 training time over 7,200 s. Read in prometheus/rules.json. |
| `resilience.n-plus-one.cluster` | ok, requests 47.5 GB within a 2% margin of 46.6 GB | short by 0.9 GB cluster-wide, and the app pool has no spare node | Recounted from objects/pods.json. Non-DaemonSet requests are 12.41 cores and 47.47 GB. The pods on `ip-10-0-1-139` that need `workload-type=app` are 31, requesting 3.25 cores and 18.3 GB. `ip-10-0-1-62` has 0.16 cores of request room left. |
| `resilience.prod-concentration.node-1-139` | 20 of 42 prod pods on one node | 33 of 42 prod pods on two spot nodes in us-east-1 | Sum of `ip-10-0-1-139` with 20 and `ip-10-0-1-62` with 13, from summary.json resilience.placement.prod_by_node. |
| `traffic.db-exposed.nlb/acme-db-shared` | sourceRanges None | four /32 office addresses | The load balancer's own security group, read in extra/nlb-security-groups.txt. |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | 42 restarts | 1 restart since 2026-05-12 | lastState.terminated startedAt 2026-05-12T08:32:38Z, finishedAt 2026-10-30T09:00:04Z, in objects/pods.json. |
| `resources.node-request-usage-gap.*` | 4 fail, 1 warn | app nodes at 89% and 92% CPU requested | The five pods app-p-backend, two app-l-backend and two app-l-embedding-server request 0.5 cores each, 2.5 cores together, and use at most 0.002 cores each at the 7-day p95. Recounted from objects/pods.json and the over-request findings. |

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | high |  | 24h 'Unable to schedule pod; no fit' 8 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, < |
| `eks.no-backup-policy.cluster` | high | 2 | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | high | 2 | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | high | 2 | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 15 occurrences total (12 events, trend over 2 snapshots [3, 12], up), first 2026-10-27T05:51:42Z last 2026-11-03T01:47:34Z. Top obje |
| `karpenter.ec2nodeclass-al2.cluster` | high |  | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 185MB |
| `observability.no-event-retention.cluster` | high |  | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e, end of support 2026-03-23 D+225 (225 days past EOL) |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes up to 1.30, the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | high |  | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constr |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | high |  | ['pod app-m-frontend-6d7ff4dcdb-qfmxq: 5m throttling ratio 0.26 (stalled for 26% of periods)', 'pod app-m-frontend-6d7ff4dcdb-tzwjn: 5m throttling ratio 0.25 (stalled for 25% of periods)'] |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | high |  | pod loki-stack-promtail-dc9mw: 7d memory working set p95 / limit = 0.91 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | high |  | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (3.7 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` | high |  | pod app-q-ai-577d8cbd67-xvh58: last termination reason OOMKilled, finished at 2026-11-02T09:38:06Z (0.7 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | high |  | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | high |  | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 3.0,  |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | high |  | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | high |  | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | high |  | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | high |  | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0,  |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | high |  | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-31ecf1515b-96449818f244837f.elb.us-east-1.amazonaws.com'], sourceRanges None. DB po |
| `traffic.db-exposed.nlb/acme-db-shared` | high |  | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 5432, 6379, 7687], exposure internet-facing, addresses ['acme-db-shared-d7d643f6896a3b2b.elb.us-east-1.amazonaws.com'], sourceRanges None. no TargetG |
| `vpccni.node-ip-exhaustion.node-1-139` | high |  | node node-1-139 (r8gd.xlarge, pool default): pod IPs 34/56 (0.607), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 20. prefix delegation False |

## 3. Changes since the previous run of this mode

Compared `2026-10-27T15-30-14` → `2026-11-03T11-17-15` (rubric 0.1.51 → 0.1.63).

- **New (29)**: `argocd.admin-account-no-sso.cluster` (warn/medium), `argocd.components-not-ha.cluster` (warn/medium), `argocd.default-project-wildcard.cluster` (fail/medium), `argocd.notifications-not-configured.cluster` (warn/low), `argocd.prod-tracks-moving-ref.cluster` (warn/low), `argocd.version-eol.cluster` (warn/low), `controlplane.apiserver-latency.PATCH` (warn/medium), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` (fail/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` (warn/high), `cost.idle-load-balancer.cluster` (warn/low), `cost.idle-node.node-2-144` (warn/low), `loki.request-errors.monitoring/statefulset/loki-stack` (warn/medium), `node.cgroup-v1.node-2-144` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` (warn/high), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` (fail/medium), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` (fail/medium), `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` (warn/high), `resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai` (fail/medium), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-z2bk5:runner` (fail/medium), `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` (warn/high), `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` (warn/high), `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` (fail/high), `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` (fail/high), `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` (warn/medium), `security.imds-hop-limit.cluster` (warn/high), `traffic.ingress-p95-latency.prod-app-q/app-q-ai` (fail/medium), `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend` (fail/medium), `traffic.pod-not-ready.middleware/kafka-exporter` (warn/medium)
- **Resolved (30)**: `controlplane.apiserver-5xx.cluster` (warn/high), `controlplane.scheduler-unschedulable.prod-app-r/app-r` (warn/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-backend` (fail/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-embedding-server` (fail/high), `controlplane.scheduler-unschedulable.app-s-prod/app-s-backend` (fail/high), `controlplane.scheduler-unschedulable.app-s-prod/app-s-frontend` (warn/high), `cost.idle-node.node-1-4` (warn/low), `cost.idle-node.node-1-62` (warn/low), `hygiene.failed-pods-lingering.cluster` (fail/low), `logs.signatures.kubelet.volume-mount-failed` (warn/medium), `node.cgroup-v1.node-1-4` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/dev-app-o` (fail/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-r` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-l-backend` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/app-s-prod` (fail/medium), `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/medium), `resources.cpu-request-overprovisioned.prod-app-q/deploy/app-q-ai:ai` (warn/medium), `resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend` (warn/medium), `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` (fail/high), `resources.cpu-throttling.prod-app-n/deploy/app-n-frontend:frontend` (warn/high), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-tflzb:runner` (fail/medium), `resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/low), `resources.node-memory-request-usage-gap.node-1-139` (warn/medium), `resources.oomkilled-repeated.monitoring/sts/loki-stack:loki` (warn/high), `traffic.alb-unhealthy-targets.prod-app-p/app-p-backend` (warn/high), `traffic.pod-not-ready.app-s-prod/app-s-frontend` (warn/medium), `traffic.pod-request-skew.prod-app-p/app-p-backend` (warn/medium), `vpccni.subnet-ips-low.subnet-01e43688f4ab26b0e` (warn/high), `vpccni.warm-pool-whole-eni.cluster` (warn/low)
- **Changed (10)**: `events.tracked-warning-reasons.FreeDiskSpaceFailed` (['fail', 'warn']/['high', 'high']), `logs.signatures.containerd.shim-error` (['warn', 'fail']/['medium', 'medium']), `node.network-errors.<ip>:9100:eth0` (['fail', 'warn']/['medium', 'medium']), `resilience.prod-concentration.node-1-139` (['fail', 'warn']/['high', 'high']), `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['medium', 'medium']), `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` (['warn', 'fail']/['high', 'high']), `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['low', 'low']), `resources.node-request-usage-gap.node-1-62` (['warn', 'fail']/['medium', 'medium']), `resources.oomkilled.monitoring/sts/loki-stack:loki` (['fail', 'warn']/['high', 'high'])
- **Rename suspects (3)**: `None`, `None`, `None`
- **Objects**: added 6, removed 5, changed 19: `configmaps/kube-system/aws-load-balancer-controller-leader` metadata.resourceVersion, `configmaps/kube-system/extension-apiserver-authentication` metadata.resourceVersion, `deployments/dev-app-m/app-m-backend` spec.template, `deployments/dev-app-m/app-m-frontend` spec.template, `deployments/prod-app-q/app-q-ai` spec.template, `deployments/prod-app-q/app-q-backend` spec.template, `deployments/prod-app-q/app-q-studio` spec.template, `deployments/prod-app-q/app-q-web` spec.template, `deployments/prod-app-l-backend/app-l-backend` spec.template, `deployments/prod-app-l-backend/app-l-embedding-server` spec.template, `deployments/prod-app-l-backend/app-l-file-worker` spec.template, `deployments/prod-app-l-backend/app-l-graph-worker` spec.template
- **Warning events**: UpdateFailed +625 (ExternalSecret/database/mysql-app-n-secret), FailedComputeMetricsReplicas -112 (), FailedGetResourceMetric -112 (), EvictionThresholdMet -56 (), Unhealthy +44 (Pod/middleware/kafka-exporter-78d46ff57f-dn65f), NetworkNotReady +13 (Pod/kube-system/ebs-csi-node-cf97j), FailedScheduling +9 (Pod/prod-app-l-backend/app-l-file-worker-db75d7fdc-9dkp4), CgroupV1 +2 (Node/node-2-101), FailedDraining +2 (Node/node-2-101), InstanceTerminating +2 (NodeClaim/default-cv77k)
- **Persisted (Toil)**: 0 findings present in all 2 runs checked, 0 in 3 or more; top checks: 

### 3-1. Why things changed

The previous full snapshot is 2026-10-27 15:30 KST, 6 days and 20 hours before this one. Nobody wrote a report for it, so the last full report is the 2026-10-26 16:47 KST one, which was written in Korean.

In those days 16 Deployments received new images through Argo CD. They are four in prod-app-q, four in prod-app-l-backend, two each in prod-app-p, prod-app-n and app-s-prod, and two in dev-app-m. Only image tags and two `restartedAt` annotations changed. No replica count, resource, strategy or placement field changed, according to the field comparison of objects/deployments.json. app-s-backend moved from generation 478 to 535 and app-p-backend from 7 to 20, which makes them the most frequently deployed. The two dev-app-m Deployments restarted their generation count at 1 and 19, so they were deleted and created again.

The app-q-ai rollout on 2026-11-02 went through three ReplicaSets between 08:34 and 08:53 UTC. The kernel on `ip-10-0-1-62` OOM-killed its uvicorn process at 08:34, 08:35 and 09:38 UTC, each time at the 768 Mi limit. The pod now runs with one restart. Its p95 latency rose from 2.07 s over 20 requests to 14.09 s over 130 requests.

app-l-backend, app-l-embedding-server and both app-l workers got image 9bb0a18 on 2026-10-30, and app-l-backend was restarted at 18:00:05 KST. app-l.my-cluster's p95 rose from 0.27 s to 3.14 s on average, with one hour at 41.5 s. The frontend's own image did not change. This time correlation is the only evidence.

The Argo CD application controller was OOM-killed at 2026-10-30T09:00:04Z, one second after the app-l-backend-prod sync finished. The snapshot cannot say whether that sync caused it.

On the node side, Karpenter replaced build node `ip-10-0-1-4` with `ip-10-0-2-144`. Both app nodes are the same machines as on 2026-10-26, so no app node was reclaimed in these seven days. The 20 Failed pods that had been evicted for disk pressure are gone, and `KubePodNotReady` stopped firing. `FreeDiskSpaceFailed` last occurred at 2026-10-27T05:55:55Z, and the root disk of `ip-10-0-1-139` went from 83.7% to 81.6%. The snapshot does not show who deleted the Failed pods. The EKS platform version moved from eks.55 to eks.58.

The counters that never stop kept growing. The do-not-disrupt block on `ip-10-0-1-139` went from 14,171 on 2026-10-26 to 19,728. The dev ExternalSecret failures went from 1,726 to 2,351.

Criteria changes, apart from cluster changes: the rubric went from 0.1.51 to 0.1.63. The six `argocd.*` findings appear as new only because the 2026-10-27 summary had no `argocdctl.summary` section, so those checks were skipped there. `security.imds-hop-limit` passed there on empty IMDS data and is a warn now. `cost.idle-load-balancer` and `loki.request-errors` passed in the previous snapshot and warn now. The snapshot does not show whether that is a criteria change or a change in the cluster. Database-like containers such as `app-l-neo4j` now stay at warn in the over-request checks. The four absences now count as critical on fail and high on warn.

## 4. Detail per area

### Resources

**Resource adjustment table.** These rows combine `cpu-request-overprovisioned`, `memory-request-overprovisioned`, `krr-recommendation` and `large-request-binpacking` for the same container. Recommendations come from KRR with 14 days of history, from tools/krr.json, and from the 7-day p95 in metrics/cpu_p95_7d_cores.json.

| container | CPU request now → proposed | 7-day CPU p95 | memory request now → proposed | related findings |
|---|---|---|---|---|
| prod-app-p/app-p-backend | 500m → 100m | 0.0011 cores | 1Gi → leave | cpu-request-overprovisioned, krr-recommendation |
| prod-app-l-backend/app-l-backend ×2 | 500m → 100m | 0.002 cores | 1Gi → leave | cpu-request-overprovisioned fail, krr-recommendation |
| prod-app-l-backend/app-l-embedding-server ×2 | 500m → 100m | 0.0012 cores | 4Gi → leave, KRR asks 4,165 MB | cpu-request-overprovisioned fail, large-request-binpacking, krr-recommendation |
| prod-app-q/app-q-ai | 100m → leave | 0.0014 cores | 256Mi → 1Gi, limit 768Mi → 1536Mi | oomkilled, oomkilled-repeated, krr-recommendation |
| prod-app-m/app-m-frontend ×2 | 10m → 100m, remove the 200m limit | throttled 26% | 128Mi → 448Mi, KRR asks 427 MB | cpu-throttling, krr-recommendation |
| prod-app-m/app-m-backend ×2 | 30m → 40m, remove the 500m limit | — | 128Mi → 448Mi, KRR asks 426 MB | krr-recommendation |
| argocd/argocd-application-controller | 200m → leave | — | 384Mi → 768Mi, limit 768Mi → 1Gi | oomkilled, krr-recommendation |
| monitoring/prometheus | 200m → leave, remove the 500m limit | throttled 22% | 800Mi → 1700Mi, limit 1536Mi → 2Gi | prometheus.memory-pressure, cpu-throttling, krr-recommendation |
| monitoring/loki-stack | leave | — | 256Mi → 512Mi, limit 512Mi → 768Mi | loki.memory-pressure, krr-recommendation |

The first three rows free 2.0 cores of requests on the two app nodes. That moves `ip-10-0-1-139` from 89% to about 59% CPU requested and `ip-10-0-1-62` from 92% to about 50%. app-l-backend has a CPU HPA with a 70% target. A 100m request makes the HPA react at 70m of real use, which is still 35 times its 7-day p95.

Database-like containers are left out of the cuts on purpose. They are app-l-neo4j, which requests 500m and 4Gi on a 4-core node, and the MySQL and PostgreSQL StatefulSets. The over-request checks mark them database-like and keep them at warn. Remove their CPU limit if they have one and leave the request as it is. If `app-l-neo4j` makes `ip-10-0-2-135` too full, move other pods off that node rather than shrinking Neo4j. Neo4j sizes its page cache and heap from memory, and a quiet week's p95 does not show what it needs during a restart or a large query.

Other items. `prod-app-l-backend/tts-proxy` is BestEffort with no requests or limits on its tailscale and forwarder containers. `middleware/kafka-controller` jmx-exporter has MaxRAMPercentage 100 inside a 128 MiB limit. Totals: KRR finds 5.26 cores of requests above need across 81 containers, against 0.78 cores of 7-day p95 use for the whole cluster. The cluster requests 18.5 times what it uses.

### Scaling

HPA settings table. These rows combine `hpa-cpu-only-prod`, `hpa-no-behavior-prod` and `hpa-never-scaled` per HPA.

| HPA | metric | min/max | behavior | 15-day movement |
|---|---|---|---|---|
| prod-app-l-backend/app-l-backend | CPU 70% | 2/3 | none | at min the whole 15 days, 0 changes in 7 days |
| prod-app-l-backend/app-l-frontend | CPU | 2/3 | none | at min the whole 15 days, 0 changes in 7 days |
| prod-app-o/app-o-ai | KEDA Kafka lag | 3/5 | — | at min the whole 15 days |
| dev-app-m/app-m-frontend | CPU | 1/3 | none | 40 changes in 7 days, `hpa-flapping` |

The app-l-backend HPA never moved because its 500m request is 250 times its use. After the request change in the resource table it can work. 21 prod serving Deployments have no HPA. That is a low item, attached to the resilience rows below. KEDA scales `app-l-file-worker` and `app-l-graph-worker` from zero. Each scale-up this morning needed a new spot node, which started 61 seconds after launch at the median and 93 seconds at most over 24 hours. The three nodes were removed again 16 to 26 minutes later. Three prod ScaledObjects have no fallback for their external trigger. Karpenter terminated 259 NodeClaims for spot interruption since its leader started 66.8 days ago. `SpotToSpotConsolidation` is off.

### Observability

There are 157 alert rules. Three of them watch a user-facing symptom, and all three are for app-m image inference and LoRA training. The seven other prod products have no symptom alert, and nothing watches OOM kills, scheduling failures or VPC CNI IP exhaustion. The app-q-ai OOMs on 2026-11-02 went unnoticed for that reason.

Always firing: `KubeControllerManagerDown` and `KubeSchedulerDown` have fired for 55.6 days. They are false on EKS because the managed control plane is not scraped. Disable `kubeControllerManager`, `kubeScheduler` and `kubeEtcd` in the kube-prometheus-stack values. `KubePodNotReady` is not firing now.

130 of 141 rules did not fire in 15 days. 40 critical or page-severity rules look only at cause metrics. Everything routes to Slack. `slack-sre` receives only the two app-m SLO groups, and `slack-system` receives the rest.

Observability stack storage: Loki runs on emptyDir with retention not applied, and Alertmanager runs on emptyDir with one replica. Loki's single OOM on 2026-10-25 therefore lost its stored logs. Prometheus has a 20Gi PVC that is 45.6% full, with working set at 73.8% of its limit. Promtail runs at 91% of its 256Mi limit.

Loki sees logs from 73 of 139 pods that have run over an hour. Every pod on the tainted build node `ip-10-0-2-144` is missing, because promtail does not tolerate the build taint. Promtail and KEDA operator metrics are not scraped. Kubernetes events are kept for one hour only, and there is no event exporter.

```yaml
# kube-prometheus-stack values
kubeControllerManager: { enabled: false }
kubeScheduler: { enabled: false }
kubeEtcd: { enabled: false }
loki:
  persistence: { enabled: true, size: 20Gi }
  config: { compactor: { retention_enabled: true }, limits_config: { retention_period: 744h } }
```

### Traffic

The ALB `k8s-acmeprodlb-b18a4555d7` handled 176,797 requests in 24 hours. It returned 116 target 5xx and 57 ELB 5xx, a ratio of 0.066%, from aws/alb-metrics.json. It serves 40 ingresses from 15 namespaces, prod and dev together, and has neither access logs nor deletion protection.

Four prod target groups have zero healthy targets, because the health check asks for `/` and gets 404 or 307. They are app-q-backend, app-l-backend, app-o-frontend and app-n-frontend. The ALB then sends traffic to every target, so a dead pod is never taken out.

Latency at the 24-hour p95: api.v1.example-b.ai averages 20.5 s, with a worst hour of 52.7 s and a last hour of 15.1 s, over 408 requests. app-q-ai.my-cluster averages 14.1 s, with a worst hour of 35.6 s, over 130 requests. app-l.my-cluster averages 3.1 s, with a worst hour of 41.5 s, over 1,949 requests. The 5xx ratios are 0.12% for api.example-b.ai and 0.14% for example-c.ai.

28 target groups keep the controller's default 300-second deregistration delay against a 30-second grace period and no preStop. The first five prod backends are app-r, app-q-ai, app-q-backend, app-q-studio and app-q-web.

Exposure: the Kafka external NLB is open to 0.0.0.0/0 on 9094 and 443. The shared database NLB is limited to four office addresses by its own security group. Seven admin or deploy hosts are internet-facing without an auth annotation, and each needs its own login checked. They are deploy.my-cluster, admin.example-b.ai, admin.example-d.ai, admin.example-c.ai and the three dev admin hosts.

```yaml
# per prod ingress
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/success-codes: "200-399"
```

### Resilience

Resilience table, one row per prod workload.

| workload | replicas | finding |
|---|---|---|
| prod-app-r/app-r | 2 | both on `ip-10-0-1-139` |
| prod-app-o/app-o-ai | 3 | all on `ip-10-0-1-139`, no PDB, no readiness probe |
| prod-app-o/app-o-backend | 2 | both on `ip-10-0-1-139`, no PDB, no readiness probe |
| prod-app-l-backend/app-l-frontend | 2 | both on `ip-10-0-1-139` |
| prod-app-m/app-m-api, -backend, -frontend | 2 each | one per node, both in us-east-1 |
| prod-app-l-backend/app-l-backend, app-l-embedding-server | 2 each | one per node, both in us-east-1 |
| prod-app-p/app-p-backend | 1 | Recreate strategy, 13 rollouts in 7 days |
| 15 more single-replica Deployments | 1 | app-q-ai, app-q-backend, app-q-studio, app-q-web, app-m-admin, app-o-admin, app-o-frontend, app-l-pg-proxy, tts-proxy, app-p-web, app-n-admin-frontend, app-n-backend, app-n-frontend, app-s-backend, app-s-frontend |

Readiness probes are missing on 10 prod workloads in app-o, app-n, app-s and tts-proxy. Prod Deployments have no preStop hook in 21 cases. 11 workloads share one path for liveness and readiness.

The database probes use 1-second timeouts with exec in four prod databases: app-m MySQL, app-o MySQL, app-l Neo4j and app-n MySQL. Raise `timeoutSeconds` to 5 for liveness.

N+1: the pods that need `workload-type=app` cannot fit anywhere when `ip-10-0-1-139` goes. They wait for a Karpenter node, about 61 seconds plus image pulls. There are no user PriorityClasses, so prod pods have the same priority as dev during that wait. `vmauth` uses Recreate too.

```yaml
# shared prod chart, Deployments with 2+ replicas
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: kubernetes.io/hostname
  whenUnsatisfiable: DoNotSchedule
  labelSelector: { matchLabels: { app.kubernetes.io/name: "{{ .name }}" } }
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector: { matchLabels: { app.kubernetes.io/name: "{{ .name }}" } }
```

### Hygiene

Each of the 8 prod Argo CD applications tracks `main`. There are no notifications, and no progressive delivery. `tailscale/tailscale:latest` in prod tts-proxy is the one mutable tag in prod. The other mutable tags are in two ARC CronJobs and redis-insight. 349 of 414 ReplicaSets are at zero replicas. 26 of 47 CRDs have no objects. 33 workloads depend on the label `acme.ai/role`, present on 5 of 8 nodes. App workloads depend on `workload-type`. Logs from argocd, dev-app-n and app-s-prod are not JSON. Only 1 of 111 containers requests ephemeral storage, and 21 emptyDirs have no sizeLimit. The EKS upgrade insight for Amazon Linux 2 is ERROR, see Platform.

### Storage

17 EBS gp3 volumes totaling 280 GB are attached. All are unencrypted, all PVs have reclaim policy Delete, and no StorageClass allows expansion. There is no VolumeSnapshot CRD. The EBS CSI snapshot sidecar logged 1,500 list failures in the 4 hours 41 minutes of logs collected, because of that.

The last EBS snapshot was 2026-10-06. All 12 snapshots from the last 30 days are named "pre-delete backup of orphan PVC". Seven prod databases have no backup, see report.md problem 1. The dev MySQL `dev-app-t/data-app-t-mysql-0` is 90.2% full of 9.7 GB and does not grow. The legacy `gp2` StorageClass is unused.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
  annotations: { storageclass.kubernetes.io/is-default-class: "true" }
provisioner: ebs.csi.aws.com
parameters: { type: gp3, encrypted: "true" }
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
```

### Security

Kafka external listener open to the internet: 9094 and 443 accept 0.0.0.0/0. The EKS API endpoint is public to 0.0.0.0/0. Argo CD exposes the admin login at deploy.my-cluster without SSO and with an empty RBAC policy. All 12 applications sit in the `default` project with `*` sources and destinations.

NetworkPolicies exist in prod-app-q, prod-app-p and app-s-prod, but the VPC CNI agent runs with `--enable-network-policy=false`, so none is enforced. No namespace enforces Pod Security Admission. 62% of containers allow root, including 28 prod workloads. All 8 instances allow IMDS from pods with hop limit 2.

29 prod workloads mount a service account token they do not use. `prod-app-l-backend/tts-proxy` runs Tailscale with NET_ADMIN and /dev/net/tun as root. Registry scanning is BASIC with scan-on-push off for 39 of 43 repositories, and 0 images are scanned. 42 of 43 repositories are MUTABLE. Audit logging is off. One dev ExternalSecret, `database/mysql-app-n-secret`, has failed since December 2025.

The shared database NLB is limited to four office addresses, which is acceptable. A private path such as a VPN or SSM port forwarding would remove the public listener.

```yaml
# EC2NodeClass default
spec:
  metadataOptions: { httpEndpoint: enabled, httpPutResponseHopLimit: 1, httpTokens: required }
```

### Cost

Ratios only, as in the previous reports. Nodes use 4% of their allocatable CPU at the 7-day p95, while 73.9% is requested. 95% of node compute is idle by the cost summary. Spot nodes are 38% of the fleet. KRR finds 5.26 reducible request cores. Removing the largest node would still fit all requests on CPU. The DB NLB `acme-db-shared` carried 0 bytes in 24 hours. The build node `ip-10-0-2-144` sat at 0.1% CPU. ECR holds 436.6 GiB in 850 images, 243 of them untagged. Four repositories have no lifecycle policy.

### Tenancy

Tenant boundary table, for 8 prod namespaces.

| namespace | ResourceQuota | LimitRange | NetworkPolicy | PSA enforce |
|---|---|---|---|---|
| prod-app-r | none | none | none | none |
| prod-app-m | none | none | none | none |
| prod-app-o | none | none | none | none |
| prod-app-l-backend | none | none | none | none |
| prod-app-n | none | none | none | none |
| prod-app-q | none | none | 1, not enforced | none |
| prod-app-p | none | none | 1, not enforced | none |
| app-s-prod | none | none | 1, not enforced | none |

Dev and prod pods share `ip-10-0-1-139`, `ip-10-0-1-62` and three system nodes. Memory limits on `ip-10-0-1-117` add up to 1.68 times its allocatable memory. prod-app-l-backend bursts to 2.156 cores against a 0.011-core median. That burst comes from the KEDA workers.

Noisy neighbor, the LLM check: no node spent a minute above 90% CPU in 7 days, and no prod container was throttled at the namespace level. There was no room for one tenant to hurt another in these 7 days.

Change correlation, the LLM check: the app-q-ai rollout at 08:34–08:53 UTC on 2026-11-02 is followed by three OOM kills and a rise in p95 from 2.07 s to 14.09 s. The app-l-backend rollout on 2026-10-30 coincides with app-l.my-cluster p95 rising from 0.27 s to 3.14 s. The first is likely causal, because the kernel killed the new image at its limit. The second is time correlation only, with insufficient evidence.

### Node OS

Six nodes run Amazon Linux 2 with cgroup v1. The two managed nodes run AL2023 and could not be read, because they are not registered in SSM. `ip-10-0-1-139` has its root disk 82% full, 9.2 GB free of 50 GB, with 35.6 GB of images in containerd. kubelet image GC starts at 85% and eviction at 90%. No kernel bugs, filesystem errors or clock problems were seen. There were five cgroup OOM kills, three of them app-q-ai, and one SYN-flood line on `ip-10-0-2-135` from 2026-10-10.

### Platform

Kubernetes 1.32.13 has been on EKS extended support since 2026-03-23, 225 days, and extended support ends 2027-03-23. Upgrade blockers:
- The EC2NodeClass `default` uses AL2, unpinned. Amazon stopped publishing AL2 EKS AMIs on 2025-11-26.
- Karpenter 0.37.0 supports Kubernetes up to 1.30, and it logged "failed validating kubernetes version" on 2026-11-02.
- Add-ons are behind: EBS CSI v1.37.0 against v1.67.2, VPC CNI v1.19.0 against v1.23.2, CoreDNS v1.11.3 against v1.11.4, kube-proxy v1.32.0 against v1.32.13.
- The managed node group AMI is 329 days old.

Argo CD 2.13.0, Prometheus 2.49.1, Loki 2.6.1, Grafana 10.2.3 and External Secrets 0.9.13 are all out of their supported lines. Prefix delegation is off on Nitro nodes. Two managed nodes are missing from SSM.

## 5. Absence list

| Finding | Status | Severity | Why it should exist | Proposal |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same nod | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. A backup is not a backup until a |
| `observability.no-slo.cluster` | warn | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `observability.no-event-retention.cluster` | fail | high | Kubernetes events are kept for only one hour by default. FailedScheduling, OOMKilling and Unhealthy from the night are gone by morning. The most undervalued material is lost. | Ship events to Loki or Elasticsearch with kubernetes-event-exporter. Alternatively, the promtail/alloy event source if Loki exists, or `[INPUT] kubernetes_events` with fluent-bit (detection recognizes |
| `security.no-certificate-manager.cluster` | warn | medium | When TLS certificate renewal is manual, services keep going down from expiry. cert-manager (or ACM plus ALB on EKS) automates renewal. On EKS, ALBs using ACM certificates work without cert-manager, bu | Install cert-manager, or if ACM is in use, suppress this check in config.yaml with a reason. |
| `hygiene.no-progressive-delivery.cluster` | fail | info | A rolling update is "replace everything", so a defect in the new version reaches all traffic immediately. Without a canary tool (some traffic -> check metrics -> expand), deployment verification depen | As services grow, automate canary judgment with Argo Rollouts (same ecosystem as Argo CD) + AnalysisTemplate (ALB 5xx, p95 Prometheus queries). |

Expected families missing (inventory): backup, event-retention, slo, certificates, progressive-delivery.

## 6. Suppressed, tool missing, not collected

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in full mode 0: none
- Skipped or errored 3: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing)

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 | node-os | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'storageclasses.storage.k8s.io']) |
| eks-platform | 29 | kubelet-journal, containerd-journal |  |
| actions-runner-controller | 0 |  | no collect.yaml (collector not implemented) |
| alb-controller | 1 |  |  |
| alertmanager | 4 |  |  |
| argocd | 3 |  |  |
| coredns | 1 |  |  |
| ebs-csi | 1 |  |  |
| ecr | 5 |  |  |
| external-dns | 0 |  | no collect.yaml (collector not implemented) |
| external-secrets | 1 |  |  |
| grafana | 5 |  | datasources (grafana_api_token missing); dashboards (grafana_api_token missing); dashboards-json (grafana_api_token missing) |
| karpenter | 1 |  |  |
| keda | 2 |  | operator-metrics (True) |
| kube-proxy | 2 | proxy-mode |  |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| loki | 9 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| promtail | 0 |  | no collect.yaml (collector not implemented) |
| victoria-metrics | 0 |  | no collect.yaml (collector not implemented) |
| vpc-cni | 2 | ipamd-metrics |  |

671 commands, 315.2 s. Failed commands (run.log): 24: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.bitnami/kafka` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `ecr.lifecycle-policy.bitnami/mysql` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `ecr.lifecycle-policy.ecr-app-s-postgresql-pgvector` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `eks-platform.kubelet-journal.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.app-n` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `eks-platform.kubelet-journal.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

### 7-2. Checks evaluated

365 checks: disabled 2, done 358, llm 2, skip 3. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.0.15, ['logs/node/node-1-139/containerd-24h.log', 'logs/node/node-1-139/kubelet-24h.log', 'logs/node/node-1-241/containerd-24h.log', 'logs/node/node-1-62/containerd-24h.log', 'logs/node/node-1-62/kubelet-24h.log', 'logs/node/node-2-144/containerd-24h.log', 'logs/node/node-2-144/kubelet-24h.log', 'logs/node/node-2-218/containerd-24h.log', 'logs/node/node-2-218/kubelet-24h.log', 'logs/pods/actions-runner-controller/arc-system_arc-gha-rs-controller.log', 'logs/pods/alb-controller/kube-system_aws-load-balancer-controller.log', 'logs/pods/argocd/argocd_argocd-application-controller.log', 'logs/pods/argocd/argocd_argocd-applicationset-controller.log', 'logs/pods/argocd/argocd_argocd-notifications-controller.log', 'logs/pods/argocd/argocd_argocd-repo-server.log', 'logs/pods/argocd/argocd_argocd-server.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-controller.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-node.log', 'logs/pods/external-dns/kube-system_external-dns.log', 'logs/pods/external-secrets/external-secrets_external-secrets-cert-controller.log', 'logs/pods/external-secrets/external-secrets_external-secrets-webhook.log', 'logs/pods/external-secrets/external-secrets_external-secrets.log', 'logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log', 'logs/pods/karpenter/karpenter_karpenter.log', 'logs/pods/keda/keda_keda-operator.log', 'logs/pods/kube-proxy/kube-system_kube-proxy.log', 'logs/pods/loki/monitoring_loki-stack.log', 'logs/pods/metrics-server/kube-system_metrics-server.log', 'logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log', 'logs/pods/promtail/monitoring_loki-stack-promtail.log', 'logs/pods/vpc-cni/kube-system_aws-node.log'] files, 22492 lines scanned (components: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 168.

| Signature | Component | Area | Severity | Status | Count | First ~ last | Sample |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 32 | 2026-11-02T18:14:01 ~ 2026-11-03T02:17:24 | [pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-02T18:14:01.817082720Z {"level":"error","ts":1793643241.8169904,"logger":"controllers.ExternalSe |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-02T08:46:33 ~ 2026-11-02T08:46:33 | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-02T08:46:33.422686915Z {"level":"ERROR","time":"2026-11-02T08:46:33.422Z","logger":"controller","message":"fa |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-02T21:38:22 ~ 2026-11-03T02:19:17 | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-02T21:38:22.161918304Z W1102 21:38:22.161812       1 reflector.go:561] k8s.io/client-go@v0.31. |
| containerd.shim-error | containerd | node | medium | fail | 68 | 2026-11-02T02:56:51 ~ 2026-11-03T00:30:03 | 2026-11-02T02:56:51+0000 node-1-139 containerd[1461]: time="2026-11-02T02:56:51.237295156Z" level=warning msg="cleaning up af |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 14 | 2026-11-02T02:51:56 ~ 2026-11-03T01:47:41 | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-02T02:51:56.106088690Z E1102 02:51:56.105984       1 scraper.go:149] "Failed to scrape node" err="G |
| kubelet.image-gc-failed | kubelet | node | medium | warn | 3 | 2026-11-02T03:01:46 ~ 2026-11-02T07:01:48 | 2026-11-02T03:01:46+0000 node-1-139 kubelet[1593]: E1102 03:01:46.336148    1593 kubelet.go:1564] "Image garbage collection f |
| kubelet.pod-sync-error | kubelet | resilience | low | info | 3 | 2026-11-02T08:35:06 ~ 2026-11-02T08:49:08 | 2026-11-02T08:49:08+0000 node-1-139 kubelet[1593]: E1102 08:49:08.188400    1593 pod_workers.go:1301] "Error syncing pod, ski |

| Normalized message | Count | Files |
|---|---|---|
| external-secrets \| {"level":"error","ts":<n>.<n>,"msg":"Reconciler error","controller":"externalsecret","controllerGroup":"external-secrets.io","controllerKind | 32 | logs/pods/external-secrets/external-secrets_external-secrets.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node ip-10-0-2-<n>.us-east-1.co | 4 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| node:node-1-139 \| time="<n>-11-02T02:56:51.706705940Z" level=error msg="ContainerStatus for \"a533748a279816935f7aa2843fa8b6d66132a25951a284e4af3563c6a4c9b616 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T02:57:36.408394034Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"45e184d13e7701da | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T03:26:54.038576282Z" level=error msg="ContainerStatus for \"70e604f6982b52476a3962a762e43764ac3686798973f33f75d59e68764461c9 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T03:27:15.085861801Z" level=error msg="ContainerStatus for \"5e611a68f859e823310ef52253d5cfb346e9b5f54691172e0f445ac16b1e3570 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T03:27:36.513630479Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"a65547468a1f64d0 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T03:27:36.549068593Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"c328add3d7595628 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T04:35:48.775947449Z" level=error msg="ContainerStatus for \"4cc48da22dc9909a9ea6b68b068dbd0d3d3788b49ec95dc7b2f8f3d8e8965df3 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T04:36:36.775980280Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"7564024789e8f0a2 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T04:52:36.849797968Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"271a888dd0ebd99a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T04:54:11.885755046Z" level=error msg="ContainerStatus for \"5ecbff140e7245c9d5dd0fb80fa33b6d8a678ee564ca357cb3d0130024bdf5b0 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T04:54:36.898432211Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"0c8298b71676c69e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T05:00:33.605216733Z" level=error msg="ContainerStatus for \"69382845adb64c3b87d30441f15c0ede17d46dc4f5777003eecfbdad76874854 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T05:00:36.948582854Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"7ca4d9bb5e171927 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T06:57:37.270162195Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"fd4eb0e9f05e752b | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:18:50.066550137Z" level=error msg="ContainerStatus for \"3816747404b018286aed897516d6b41166a571f78f868154aa8da23bbb851a16 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:19:37.357956239Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"e83bff76c06776d0 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:35:52.973393345Z" level=error msg="ContainerStatus for \"8b1b8e1313621e36ce0b3c0e6180b626e65015522e85721d7d8e8a3d61e41f9b | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:36:23.028472813Z" level=error msg="ContainerStatus for \"c7e7f638f446df4743cdff7250ddbc0a3650e263000cf823ddb73018294cff5f | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:36:37.438503780Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"6906b90d8ca8afa6 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T07:36:37.470832240Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"5d30db4a51d7ac95 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:20:47.975999657Z" level=error msg="ContainerStatus for \"46812fc3fc43d6f3bb61e07eae5d9bfd52c01f8191c79c4687716cd8c22d70c5 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:21:37.619076306Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"54529fec8671d4c4 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:33:20.374059141Z" level=error msg="ContainerStatus for \"b5f3d69227413407f7c0ca65f62eec3cf5f46a4ae3f48c36c86b8d70dc44033a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:33:37.688005181Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"64fbb477cb9a84c6 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:45:35.816598391Z" level=error msg="ContainerStatus for \"179399235fb99afa740cdf121a69ab7954a6251123407873afe2c78064bfe18e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:45:37.749094396Z" level=warning msg="Failed to get podSandbox status for container event for sandboxID \"2990610b8037958d | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:54:19.791149997Z" level=error msg="ContainerStatus for \"b1525123968fd7d9c642e6b7d32ee655a6b16696aa6a3cdc3f64909b7a3ffbe4 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-11-02T08:54:19.791396667Z" level=error msg="ContainerStatus for \"a8e3a11d1dea15b4a63bfaa220c5388d0c36c752c4cfd276e33d46bbc760055a | 1 | logs/node/node-1-139/containerd-24h.log |

### 7-4. Raw files the LLM read directly

inventory.json
findings-draft.json
summary.json
diff.json
collect-result.json
events.json
objects/deployments.json
objects/pods.json
objects/nodes.json
metrics/disk_usage_ratio.json
metrics/node_cpu_request_ratio.json
metrics/node_memory_request_ratio.json
metrics/node_cpu_usage_ratio_p95_7d.json
metrics/node_memory_usage_ratio_p95_7d.json
metrics/cpu_throttle_ratio_5m.json
metrics/cpu_limit_p95_ratio_7d.json
metrics/cpu_p95_7d_cores.json
metrics/cpu_request_p95_ratio_7d.json
metrics/memory_limit_p95_ratio_7d.json
metrics/oom_events_7d.json
metrics/oomkilled_last_terminated.json
metrics/apiserver_p99_latency_by_verb.json
metrics/apiserver_5xx_rate.json
prometheus/rules.json
aws/alb-metrics.json
aws/describe-security-groups.json
logs/pods/AGGREGATED.json
logs/node/node-1-139/kubelet-24h.log
logs/node/node-1-139/kubelet-configz.json
logs/node/node-1-62/kubelet-24h.log
logs/node/node-1-62/os.txt
logs/node/node-1-139/os.txt
extra/nlb-security-groups.txt — read outside the snapshot: `aws ec2 describe-security-groups --profile acme --region us-east-1 --group-ids sg-db-shared-nlb sg-cluster-traffic sg-kafka-nlb --output json`, read-only, run 2026-11-03 after collection
../2026-10-27T15-30-14/objects/deployments.json
../2026-10-27T15-30-14/summary.json
../2026-10-27T15-30-14/findings-draft.json
../2026-10-27T15-30-14/metrics/disk_usage_ratio.json
~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/report.md — the last full report, read for the previous Top 5
~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/report-details.md — section 7-6, for the tool-note numbering

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `observability.no-slo.cluster` | warn | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] |
| `observability.no-symptom-alerts.cluster` | warn | critical | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 19. Symptom ratio 0.0. Symptom rules: [] |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | fail | high | 24h 'Unable to schedule pod; no fit' 8 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untolerated taint {workload |
| `eks.no-backup-policy.cluster` | fail | high | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | fail | high | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 15 occurrences total (12 events, trend over 2 snapshots [3, 12], up), first 2026-10-27T05:51:42Z last 2026-11-03T01:47:34Z. Top objects: ['Pod/prod-app-l-backend/app-l-file-worker-db75d7fdc-9dkp4', 'Pod/prod-rhem |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 185MB |
| `observability.no-event-retention.cluster` | fail | high | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e, end of support 2026-03-23 D+225 (225 days past EOL) |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes up to 1.30, the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | fail | high | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 2 |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | fail | high | ['pod app-m-frontend-6d7ff4dcdb-qfmxq: 5m throttling ratio 0.26 (stalled for 26% of periods)', 'pod app-m-frontend-6d7ff4dcdb-tzwjn: 5m throttling ratio 0.25 (stalled for 25% of periods)'] |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | fail | high | pod loki-stack-promtail-dc9mw: 7d memory working set p95 / limit = 0.91 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | fail | high | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (3.7 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` | fail | high | pod app-q-ai-577d8cbd67-xvh58: last termination reason OOMKilled, finished at 2026-11-02T09:38:06Z (0.7 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | fail | high | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | fail | high | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 3.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail | high | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-t-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | fail | high | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-q-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | fail | high | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-o-frontend'] |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | fail | high | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0, health check / expected codes 200, backends ['deployment/app-l-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | fail | high | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-31ecf1515b-96449818f244837f.elb.us-east-1.amazonaws.com'], sourceRanges None. DB port open on an external address |
| `traffic.db-exposed.nlb/acme-db-shared` | fail | high | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 5432, 6379, 7687], exposure internet-facing, addresses ['acme-db-shared-d7d643f6896a3b2b.elb.us-east-1.amazonaws.com'], sourceRanges None. no TargetGroupBinding; NLB created outside Kubernetes (Terraform etc.). DB inferred from t |
| `vpccni.node-ip-exhaustion.node-1-139` | fail | high | node node-1-139 (r8gd.xlarge, pool default): pod IPs 34/56 (0.607), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 20. prefix delegation False |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn | high | 24h 'Unable to schedule pod; no fit' 35 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untolerated taint {workload |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` | warn | high | 24h 'Unable to schedule pod; no fit' 4 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untolerated taint {workload |
| `eks.service-quota-near-limit.aws-account` | warn | high | quotas with a usage metric 25/65, at 80% or more [], at 60% or more ['VPCs 0.6'], top operational quotas [['VPCs', 3.0, 5.0, 0.6], ['listener rules per ALB', 47.0, 100.0, 0.47], ['target groups per ALB', 40.0, 100.0, 0.4], ['certificates per ALB', 9.0, 25.0, 0.36], ['NLBs', 2.0, 50.0, 0.04], ['ALBs' |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | warn | high | kubelet image GC could not free space. Disk is full of in-use images and logs. 1 occurrences total (1 events, trend over 2 snapshots [1, 0], down), first 2026-10-27T05:55:55Z last 2026-10-27T05:55:55Z. Top objects: ['Node/node-1-139'] |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 54 occurrences total (6 events, trend over 2 snapshots [5, 49], up), first 2026-10-09T06:29:27Z last 2026-11-03T02:04:07Z. Top objects: ['Pod/middleware/kafka-exporter-78d46ff57f-dn65f', 'Pod/prod-app-p/app-p-backend-765df4b49 |
| `events.tracked-warning-reasons.UpdateFailed` | warn | high | Operator reconcile failure (ExternalSecret etc.). 2351 occurrences total (1 events, trend over 2 snapshots [1726, 2351], up), first 2026-10-08T12:31:38Z last 2026-11-03T02:17:24Z. Top objects: ['ExternalSecret/database/mysql-app-n-secret'] |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 32 occurrences (2026-11-02T18:14:01 ~ 2026-11-03T02:17:24), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: ['[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-02T18:14:01.817082720Z {"level":"error","ts":1793643241.81699 |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-02T08:46:33 ~ 2026-11-02T08:46:33), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-02T08:46:33.422686915Z {"level":"ERROR","time":"2026-11-02T08:46:33.422Z","logger":"controller", |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.82 |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.738 (limit 1536Mi), active series 167236, Prometheus container last terminated OOMKilled True (2026-10-06T12:32:06Z), restarts 1, OOMKilled containers in the monitoring namespace ['loki-stack-0/loki', 'prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7  |
| `resilience.prod-concentration.node-1-139` | warn | high | Node node-1-139 (pool default, spot) holds prod pods 20/42 (0.48), 15 workloads: ['prod-app-r/app-r', 'prod-app-q/app-q-backend', 'prod-app-m/app-m-admin', 'prod-app-m/app-m-api', 'prod-app-m/app-m-backend |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn | high | pod app-m-frontend-5f5d598cdb-wk27v: 5m throttling ratio 0.21 (stalled for 21% of periods) |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7f6d6dc65b-lnmq4: 5m throttling ratio 0.11 (stalled for 11% of periods) |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: 5m throttling ratio 0.22 (stalled for 22% of periods) |
| `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` | warn | high | pod argocd-application-controller-0 container application-controller: 1 OOMs in 7 days (increase of cAdvisor container_oom_events_total) |
| `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` | warn | high | pod app-q-ai-577d8cbd67-xvh58 container ai: 1 OOMs in 7 days (increase of cAdvisor container_oom_events_total) |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | warn | high | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (9.1 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-10-06T12:32:06Z (27.6 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.imds-hop-limit.cluster` | warn | high | Of 8 instances, 8 with IMDS hop limit > 1 or tokens optional: {'hop=2 tokens=required': 8}. Examples [('system_core', 'm5.large', 2, 'required'), ('system_core', 'm5.large', 2, 'required'), ('karpenter-node', 't8i.medium', 2, 'required'), ('karpenter-node', 'm7i-flex.large', 2, 'required')]. EC2Node |
| `vpccni.node-ip-exhaustion.node-1-241` | warn | high | node node-1-241 (t8i.small, pool system-ondemand): pod IPs 6/9 (0.667), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 11, prod pods 1. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-2-218` | warn | high | node node-2-218 (t8i.medium, pool system-ondemand): pod IPs 13/15 (0.867), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 17, prod pods 1. prefix delegation False |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 12/12 (prod 8) |
| `cost.idle-compute-high.cluster` | fail | medium | Node compute monthly estimate 472.03 USD (on-demand list price, current spot price), of which idle 447.9 USD (0.95), by pool {'nodegroup:system_core-20251217040546303900000001': 172.28, 'default': 101.4, 'system-ondemand': 154.26, 'build-arm64': 44.09}, 24.31 USD per core-month. Spot node share 0.38 |
| `cost.request-waste.cluster` | fail | medium | CPU request total 6.68 cores -> KRR recommendation 1.42 cores, reducible 5.26 cores ~ 127.85 USD/month |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-2a', 'gp3-2c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-2a', 'gp3-2c'] |
| `ecr.scan-disabled.ecr/registry/<account>` | fail | medium | registry scanning BASIC (rules 0), repositories with scanOnPush off 39/43 (used by prod 25: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod']…), scanned images 0 |
| `eks.addon-outdated.aws-ebs-csi-driver` | fail | medium | installed v1.37.0-eksbuild.1, latest available v1.67.2-eksbuild.1, default v1.67.2-eksbuild.1 |
| `eks.addon-outdated.vpc-cni` | fail | medium | installed v1.19.0-eksbuild.1, latest available v1.23.2-eksbuild.8, default v1.22.4-eksbuild.10 |
| `eks.extended-support.cluster` | fail | medium | version 1.32, supportType EXTENDED, status EXTENDED_SUPPORT, end of standard support 2026-03-23T09:00:00+09:00, end of extended support 2027-03-23T09:00:00+09:00 |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eks.nodegroup-ami-old.nodegroups` | fail | medium | node groups 1, max AMI age 329 days, over 90 days ['system_core-20251217040546303900000001 329d'], over 180 days ['system_core-20251217040546303900000001'], health issues [] |
| `eks.ssm-unregistered.node-1-117` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eks.ssm-unregistered.node-2-60` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 27549 / errors 2351 (ratio 0.0786), sync failures 2351/63066, reconcile errors 2351, ExternalSecrets not Ready ['database/externalsecret/mysql-app-n-secret'] (oldest refresh 7701.3 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2592, {'101': 4, '200': 2261, '400': 6, '429': 321}), ('Prometheus(prometheus)', 1531, {'200': 1349, '301': 182}), ('VictoriaMetrics_onprem(prometheus)', 138, {'200': 138})], error rate 1% or more ['Loki(loki)'] (max 0.1238), Grafana  |
| `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility` | fail | medium | Amazon Linux 2 compatibility (UPGRADE_READINESS, k8s 1.33): ERROR — Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ |
| `hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.polaris-reliability-danger.prod-app-l-backend/deployment/tts-proxy` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing']. Security-category danger ['dangerousCapabilities', 'privilegeEscalationAllowed', 'run |
| `logs.signatures.containerd.shim-error` | fail | medium | 68 occurrences (2026-11-02T02:56:51 ~ 2026-11-03T00:30:03), thresholds warn 5/fail 50. Files: ['logs/node/node-1-139/containerd-24h.log', 'logs/node/node-1-62/containerd-24h.log', 'logs/node/ip-10-0-1-241.us-east-1.compute.in |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 55.6 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 55.6 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodNotReady` | fail | medium | 7d firing samples 169042 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 139 pods Running for over 1h, 66 are absent from Loki pod labels (ratio 0.475). Nodes with every pod missing: ['node-2-144']. By namespace: {'kube-system': 21, 'monitoring': 15, 'prod-app-l-backend': 4, 'middleware': 3, 'argocd': 2, 'dev-app-m': 2, 'dev-in |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret` | fail | medium | Ready=False (SecretSyncedError) for 7700.4 hours: could not get secret data from provider |
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
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api` | fail | medium | replicas 2, AZ distribution {'us-east-1': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend` | fail | medium | replicas 2, AZ distribution {'us-east-1': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend` | fail | medium | replicas 2, AZ distribution {'us-east-1': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend` | fail | medium | replicas 2, AZ distribution {'us-east-1': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server` | fail | medium | replicas 2, AZ distribution {'us-east-1': 2}, node distribution {'node-1-139': 1, 'node-1-62': 1}, topologySpread [] |
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
| `resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | fail | medium | pod vm-single-0: 7d CPU p95 0.001 cores / request 0.30 cores = 0.00 |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` | fail | medium | ['pod app-l-backend-78679bf4b-mbnjd: 7d CPU p95 0.002 cores / request 0.50 cores = 0.00', 'pod app-l-backend-78679bf4b-lhhg4: 7d CPU p95 0.002 cores / request 0.50 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-8445d87f5-dwqrx: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00', 'pod app-l-embedding-server-8445d87f5-jfv9l: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00'] |
| `resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter` | fail | medium | middleware/statefulset/kafka-controller container jmx-exporter (jmx-exporter:0.20.0-debian-11-r4): -Xmx NoneMiB, MaxRAMPercentage 100.0, memory limit 128.0MiB -> heap/limit 1.0 (heap unset False) |
| `resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller` | fail | medium | memory request under by 373 MB, CPU request over by 0.145 cores: CPU request 0.2 → 0.055 cores, CPU limit 0.5 → none, memory request 384 → 757 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.dev-app-o/statefulset/app-o-backend-mysql:mysql` | fail | medium | memory request under by 355 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 867 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | fail | medium | memory request under by 280 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 792 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/loki-stack:loki` | fail | medium | memory request under by 273 MB: CPU request 0.1 → 0.02 cores, CPU limit 0.2 → none, memory request 256 → 529 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 839 MB: CPU request 0.2 → 0.136 cores, CPU limit 0.5 → none, memory request 800 → 1639 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle` | fail | medium | CPU request over by 0.29 cores, memory request over by 322 MB: CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 190 MB, memory limit 1024 → 190 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai` | fail | medium | memory request under by 351 MB: CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 607 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-backend:backend` | fail | medium | memory request under by 298 MB: CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 426 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-frontend:frontend` | fail | medium | memory request under by 299 MB: CPU request 0.01 → 0.032 cores, CPU limit 0.2 → none, memory request 128 → 427 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/statefulset/app-m-backend-mysql:mysql` | fail | medium | memory request under by 395 MB, CPU request over by 0.188 cores: CPU request 0.2 → 0.012 cores, CPU limit 1.0 → none, memory request 768 → 1163 MB, memory limit 1536 → 1163 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-ai:ai` | fail | medium | memory request over by 1069 MB: CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 979 MB, memory limit 4096 → 979 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-embedding-server:embedding` | fail | medium | memory request under by 69 MB, CPU request over by 0.341 cores: CPU request 0.5 → 0.159 cores, CPU limit 2.0 → none, memory request 4096 → 4165 MB, memory limit 6144 → 4165 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/statefulset/app-l-neo4j:neo4j` | fail | medium | CPU request over by 0.49 cores, memory request over by 2881 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1215 MB, memory limit 5120 → 1215 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-backend:backend` | fail | medium | CPU request over by 0.359 cores: CPU request 0.5 → 0.141 cores, CPU limit 2.0 → none, memory request 1024 → 843 MB, memory limit 2048 → 843 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-z2bk5:runner` | fail | medium | pod self-hosted-arm64-8msc5-runner-z2bk5: request is 104% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-8445d87f5-dwqrx: request is 58% of the median node allocatable', 'pod app-l-embedding-server-8445d87f5-jfv9l: request is 58% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | medium | pod app-l-neo4j-0: request is 58% of the median node allocatable |
| `resources.no-memory-limit.prod-app-l-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-request-usage-gap.node-1-117` | fail | medium | CPU requests/allocatable 0.96, usage/allocatable 7d p95 0.10 (5m instant 0.08) |
| `resources.node-request-usage-gap.node-1-139` | fail | medium | CPU requests/allocatable 0.89, usage/allocatable 7d p95 0.06 (5m instant 0.05) |
| `resources.node-request-usage-gap.node-1-62` | fail | medium | CPU requests/allocatable 0.92, usage/allocatable 7d p95 0.05 (5m instant 0.05) |
| `resources.node-request-usage-gap.node-2-60` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.06) |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node node-1-139 (r8gd.xlarge spot): age 961.4h, 241.4h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 19728}. do-not-disrupt pods on this node 1: prod-app-m/app-m-admin-57f5fcc58d-khsh5 |
| `security.externalsecret-not-ready.database/mysql-app-n-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.networkpolicy-coverage.cluster` | fail | medium | 18 of 21 user namespaces have no NetworkPolicy, of which production ['prod-app-r', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-n']; with: ['prod-app-q', 'prod-app-p', 'app-s-prod'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 79. Security danger workloads 74 (prod 28): per check {'dangerousCapabilities': 2, 'hostNetworkSet': 2, 'privilegeEscalationAllowed': 59, 'runAsPrivileged': 3, 'runAsRootAllowed': 58, 'hostPIDSet': 1, 'rolebindingClusterAdminRole': 2, 'rolebindingRolePodExecAttach': 2, 'clusterrolebind |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days 12 {'pre-delete backup of orphan PVC prod-ill': 4, 'pre-delete backup of orphan PVC app-s-prod': 2, 'pre-delete backup of orphan PVC prod-ins': 2, 'pre-delete backup of orphan PVC dev-toot': 1, |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.burst-tenant-unbounded.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): 7d CPU median 0.011 cores, p95 0.012 cores, max 2.156 cores = 194.6x the median. No quota, shares nodes with prod True, nodes {'node-1-139': 4, 'node-2-135': 3, 'ip-10-0-1-62.us-east-1.compute.inter |
| `tenancy.prod-boundary-missing.prod-app-r` | fail | medium | prod-app-r: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-m` | fail | medium | prod-app-m: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-o` | fail | medium | prod-app-o: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-l-backend` | fail | medium | prod-app-l-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-n` | fail | medium | prod-app-n: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `traffic.ingress-p95-latency.prod-app-q/app-q-ai` | fail | medium | ['app-q-ai.my-cluster']: p95 avg 14.091s, 1h max 35.5604s, latest 1h 2.4693s, 130.0 requests/24h (source alb-cloudwatch) |
| `traffic.ingress-p95-latency.prod-app-m/app-m-api` | fail | medium | ['canary-api-v1.example-b.ai', 'api.v1.example-b.ai']: p95 avg 20.4829s, 1h max 52.6524s, latest 1h 15.0582s, 408.0 requests/24h (source alb-cloudwatch) |
| `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend` | fail | medium | ['app-l.my-cluster']: p95 avg 3.1359s, 1h max 41.5368s, latest 1h 0.868s, 1949.0 requests/24h (source alb-cloudwatch) |
| `traffic.shared-alb-group.alb-group/acme-prod-lb` | fail | medium | ALB group acme-prod-lb: 40 ingresses, 47 hosts, 15 namespaces ['argocd', 'dev-app-m', 'dev-app-o', 'dev-app-n', 'dev-app-t', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n |
| `vpccni.prefix-delegation-off.cluster` | fail | medium | ENABLE_PREFIX_DELEGATION false, nitro nodes 8/8. nodes above 50% IP usage ['node-2-218', 'node-1-241', 'node-2-60', 'node-1-62', 'ip-10-0-1-139.us-east-1.c |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `albctl.tgb-stale-or-orphan.cluster` | warn | medium | TargetGroupBindings 51 (targetType {'ip': 51}), generation lagging [], Service missing [], hand-made TGBs 9, target groups without a binding (traffic section) 1 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.my-cluster |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version 2.13 |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.705s |
| `controlplane.apiserver-latency.PATCH` | warn | medium | PATCH p99 0.709s |
| `controlplane.controller-error-repeat.horizontal.go` | warn | medium | 24h E lines 13 times (horizontal.go). Samples: summary.controlplane.controller_manager.top_errors |
| `controlplane.controller-error-repeat.type.go` | warn | medium | 24h W lines 80458 times (type.go). Samples: summary.controlplane.controller_manager.top_errors |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.512, queries per second 78.95, NXDOMAIN share of queries forwarded upstream 0.462 (upstreams ['<ip>:53']), pods with default ndots (5) 145, autopath False, cache hit ratio 0.9174 |
| `ecr.dockerhub-dependency.ecr/registry/<account>` | warn | medium | registry distribution of container images {'<account>.dkr.ecr.us-east-1.amazonaws.com': 70, '<account>.dkr.ecr.us-east-1.amazonaws.com': 55, 'docker.io': 33, 'quay.io': 24, 'ghcr.io': 11, 'public.ecr.aws': 8, 'registry.k8s.io': 3}, docker.io images 20 (e.g. ['alpine/socat:1.8.0.0', ' |
| `eks.addon-outdated.coredns` | warn | medium | installed v1.11.3-eksbuild.1, latest available v1.11.4-eksbuild.97, default v1.11.4-eksbuild.92 |
| `eks.addon-outdated.kube-proxy` | warn | medium | installed v1.32.0-eksbuild.2, latest available v1.32.13-eksbuild.67, default v1.32.13-eksbuild.65 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.acme.ai/role` | warn | medium | Label acme.ai/role: 33 workloads (production 8) depend on it via nodeSelector/affinity, present on 5/8 nodes — e.g. argocd/deployment/argocd-applicationset-controller, argocd/deployment/argocd-dex-server, argocd/deployment/argocd-notifications-controller |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 38 workloads (production 25) depend on it via nodeSelector/affinity, present on 3/8 nodes — e.g. dev-app-m/deployment/app-m-admin, dev-app-m/deployment/app-m-api, dev-app-m/deployment/app-m-backend |
| `hygiene.polaris-reliability-danger.arc-runners/autoscalingrunnerset/self-hosted-arm64` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsPrivileged', 'runAsRootAllowe |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-cool-down` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in  |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-warm-up` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in  |
| `hygiene.polaris-reliability-danger.middleware/deployment/redis-insight` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAll |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 31.6s (8109 pods), node termination average 16.0s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-o/scaledobject/app-o-ai-kafka-lag', 'prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-02T21:38:22 ~ 2026-11-03T02:19:17), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-02T21:38:22.161918304Z W1102 21:38:22.161812       1 reflector.go:56 |
| `logs.signatures.kubelet.image-gc-failed` | warn | medium | 3 occurrences (2026-11-02T03:01:46 ~ 2026-11-02T07:01:48), thresholds warn 1/fail 10. Files: ['logs/node/node-1-139/kubelet-24h.log']. Samples: ['2026-11-02T03:01:46+0000 node-1-139 kubelet[1593]: E1102 03:01:46.336148    1593 kub |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 14 occurrences (2026-11-02T02:51:56 ~ 2026-11-03T01:47:41), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-02T02:51:56.106088690Z E1102 02:51:56.105984       1 scraper.go:149] "Fa |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | warn | medium | RSS 185MiB / limit 512Mi = 0.362, in-memory streams 56, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 1 5xx out of 4780392 requests since start (by route {'loki_api_v1_series': 1}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 7971, rejected {} |
| `node.kernel-net-mem-pressure.node-2-135` | warn | medium | kernel log (since boot (dmesg; journald does not hold 24 hours)) BUG/Oops/Call Trace 0, network pressure (TCP memory, SYN flooding, ARP table) 1, memory pressure (page allocation failure) 0, unstable clocksource 0. Samples: ['[Sat Oct 10 05:24:47 2026] TCP: request_sock_TCP: Possible SYN flooding on |
| `node.network-errors.<ip>:9100:eth0` | warn | medium | Node <ip>:9100 device eth0: 317 RX+TX errors in 24h |
| `node.network-errors.<ip>:9100:eth0` | warn | medium | Node <ip>:9100 device eth0: 4 RX+TX errors in 24h |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerFailedReload', 'AlertmanagerMembersInconsistent', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown', 'AlertmanagerClus |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | dev-app-m/statefulset/app-m-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | dev-app-o/statefulset/app-o-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | warn | medium | dev-app-n/statefulset/app-n-backend-dev-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | dev-app-t/statefulset/app-t-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-postgres:postgres` | warn | medium | dev-app-t/statefulset/app-t-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 106, 'system-cluster-critical': 9, 'system-node-critical': 24}, prod pods without a class 42 of 42, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.cluster` | warn | medium | Of 14 DB workloads with a PVC, production DBs without a backup CronJob in the same namespace: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-m/statefulset/app-m-backend-mysql', 'prod-app-o/statefulset/app-o-backend-mysql', 'prod-app-l-backend/statefulset/ |
| `resilience.recreate-strategy-serving.monitoring/deployment/vmauth` | warn | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master` | warn | medium | Containers whose command is sh -c ['redis', 'metrics'], no preStop, terminationGracePeriodSeconds 30 |
| `resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | medium | pod argocd-repo-server-d487895cc-bth22: 7d CPU p95 0.002 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller` | warn | medium | pod argocd-application-controller-0: 7d CPU p95 0.033 cores / request 0.20 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-api:api` | warn | medium | pod app-m-api-575d497d9b-5ttcv: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | medium | pod app-o-ai-7cdbdc7544-szzcl: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | medium | pod app-o-backend-69dbdf4f65-9x6jc: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.10 cores = 0.09; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-n/deploy/app-n-backend:backend` | warn | medium | pod app-n-backend-7cfd8c975-b9p48: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13 |
| `resources.cpu-request-overprovisioned.dev-app-n/sts/app-n-backend-dev-mysql:mysql` | warn | medium | pod app-n-backend-dev-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-t/deploy/app-t-backend:backend` | warn | medium | pod app-t-backend-5ff4994f96-fxsr6: 7d CPU p95 0.001 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-mysql:mysql` | warn | medium | pod app-t-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | medium | pod app-t-postgres-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07; database-like: keep the request |
| `resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | medium | ['pod karpenter-9769889bd-pkxd2: 7d CPU p95 0.016 cores / request 0.20 cores = 0.08', 'pod karpenter-9769889bd-nphgs: 7d CPU p95 0.000 cores / request 0.20 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-7fc99cdd4d-jpng8: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-c5b6f8b88-jt7dp: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-54ffcbbfd6-2wtvl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/aws-load-balancer-controller:aws-load-balancer-controller` | warn | medium | ['pod aws-load-balancer-controller-dbcd6944f-svnmr: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02', 'pod aws-load-balancer-controller-dbcd6944f-psh2b: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | ['pod coredns-c7dbf4744-lz5fs: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07', 'pod coredns-c7dbf4744-cb76h: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-65d4b7df64-xxfjs: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05 |
| `resources.cpu-request-overprovisioned.kube-system/ds/kube-proxy:kube-proxy` | warn | medium | ['pod kube-proxy-d297j: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-snbf9: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-77wxc: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-4zj2m: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-n4sbq: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-t9t6c: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-kq4wd: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.middleware/deploy/kafka-ui:kafka-ui` | warn | medium | pod kafka-ui-7cb8bcb988-gls7p: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.middleware/sts/kafka-controller:kafka` | warn | medium | pod kafka-controller-0: 7d CPU p95 0.069 cores / request 0.20 cores = 0.34; database-like: keep the request |
| `resources.cpu-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana` | warn | medium | pod kube-prometheus-stack-grafana-7c9959564d-w8qx7: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.monitoring/sts/loki-stack:loki` | warn | medium | pod loki-stack-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07 |
| `resources.cpu-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | medium | pod app-q-backend-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.011 cores / request 0.20 cores = 0.06; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | medium | ['pod app-o-backend-596479b6f8-cx44t: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod app-o-backend-596479b6f8-nv9j2: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.prod-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | medium | ['pod app-l-frontend-6d58bbfcfc-2qgs6: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod app-l-frontend-6d58bbfcfc-nfk9x: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | warn | medium | pod app-l-neo4j-0: 7d CPU p95 0.004 cores / request 0.50 cores = 0.01; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-p/sts/app-p-postgresql:postgresql` | warn | medium | pod app-p-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-n/sts/app-n-backend-prod-mysql:mysql` | warn | medium | pod app-n-backend-prod-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | medium | pod app-s-backend-postgresql-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07; database-like: keep the request |
| `resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 257 MB, memory limit 1024 → 257 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-m/deployment/app-m-frontend:frontend` | warn | medium | memory request under by 103 MB: CPU HPA detected, memory request 128 → 231 MB. KRR severity OK (CPU req UNKNOWN, CPU limit UNKNOWN, memory req OK, memory limit GOOD). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | memory request under by 113 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 625 MB, memory limit 1024 → 625 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-ai:ai` | warn | medium | memory request over by 458 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 566 MB, memory limit 2048 → 566 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 359 MB: CPU HPA detected, memory request 512 → 153 MB, memory limit 8192 → 153 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | CPU request over by 0.19 cores, memory request over by 341 MB: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.karpenter/deployment/karpenter:controller` | warn | medium | memory request under by 163 MB, CPU request over by 0.181 cores: CPU request 0.2 → 0.019 cores, CPU limit 0.5 → none, memory request 256 → 419 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka` | warn | medium | CPU request over by 0.13 cores: CPU request 0.2 → 0.07 cores, CPU limit 0.5 → none, memory request 1536 → 1462 MB, memory limit 2048 → 1462 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail` | warn | medium | memory request under by 144 MB: CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 272 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-backend:backend` | warn | medium | memory request under by 189 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 381 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 396 MB: CPU request 0.1 → 0.011 cores, CPU limit 2.0 → none, memory request 512 → 116 MB, memory limit 2048 → 116 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-backend:backend` | warn | medium | memory request over by 419 MB: CPU HPA detected, memory request 1024 → 605 MB, memory limit 2048 → 605 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-pg-proxy:forwarder` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-n/deployment/app-n-backend:backend` | warn | medium | memory request under by 89 MB: CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 217 MB, memory limit 512 → 217 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | warn | medium | CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 811 MB, memory limit 1536 → 811 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.node-memory-request-usage-gap.node-1-241` | warn | medium | memory requests/allocatable 0.66, working set/allocatable 7d p95 0.32 (instant 0.30) |
| `resources.node-memory-request-usage-gap.node-2-135` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.39 (instant 0.43) |
| `resources.node-request-usage-gap.node-2-135` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.05 (5m instant 0.05) |
| `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` | warn | medium | 40 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']. Share of containers allowing root 0.62 (28 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 86/91, of which 29 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-r/deployment/app-r', 'prod-app-q/deployment/app-q-ai', 'prod-app-q/deployment/app-q-backend', 'prod-app-q/deployment/app-q-s |
| `storage.ebs-unencrypted.cluster` | warn | medium | 17 of 17 volumes unencrypted: ['vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0'] |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-n/data-app-n-backend-prod-mysql-0', 'prod-app-m/data-app-m-backend-mysql-0', 'prod-app-l-backend/data-app-l-neo4j-0', 'app-s-prod/data-app-s-backend-postgresql-0', 'prod-app-p/data-app-p-postgresql-0', 'prod-app-q/data |
| `tenancy.prod-boundary-missing.prod-app-q` | warn | medium | prod-app-q: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-p` | warn | medium | prod-app-p: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.app-s-prod` | warn | medium | app-s-prod: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 1, CPU requests total 2.0 cores, memory requests total 4.0GB, 7d CPU p95 0.469 cores (cluster share 0.385), memory p95 1.77GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-m` | warn | medium | dev-app-m (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 0.052 cores (cluster share 0.043), memory p95 0.86GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-o` | warn | medium | dev-app-o (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 2.25GB, 7d CPU p95 0.035 cores (cluster share 0.029), memory p95 1.4GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-n` | warn | medium | dev-app-n (dev): no ResourceQuota. Pods 4, CPU requests total 0.3 cores, memory requests total 1.0GB, 7d CPU p95 0.024 cores (cluster share 0.02), memory p95 0.95GB, 7d max/median 1.5x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-t` | warn | medium | dev-app-t (dev): no ResourceQuota. Pods 4, CPU requests total 0.55 cores, memory requests total 1.88GB, 7d CPU p95 0.017 cores (cluster share 0.014), memory p95 0.85GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-r` | warn | medium | prod-app-r (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 0.004 cores (cluster share 0.003), memory p95 0.2GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-q` | warn | medium | prod-app-q (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 0.009 cores (cluster share 0.008), memory p95 0.93GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-m` | warn | medium | prod-app-m (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 0.108 cores (cluster share 0.089), memory p95 1.88GB, 7d max/median 1.6x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-o` | warn | medium | prod-app-o (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 0.037 cores (cluster share 0.031), memory p95 2.79GB, 7d max/median 2.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-l-backend` | warn | medium | prod-app-l-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 0.012 cores (cluster share 0.01), memory p95 5.35GB, 7d max/median 194.6x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-p` | warn | medium | prod-app-p (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.015 cores (cluster share 0.012), memory p95 0.81GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-n` | warn | medium | prod-app-n (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.024 cores (cluster share 0.02), memory p95 1.02GB, 7d max/median 2.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.app-s-prod` | warn | medium | app-s-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 0.022 cores (cluster share 0.018), memory p95 0.49GB, 7d max/median 2.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.node-1-117` | warn | medium | Node node-1-117 (pool system_core-20251217040546303900000001): tenant kinds ['dev', 'prod'], namespaces ['kube-system', 'keda', 'monitoring', 'argocd', 'dev-app-o', 'dev-app-t']. Memory limit total 11.6GB / allocatable 6.9GB = 1.68x, request total 4.7GB,  |
| `tenancy.shared-node-limit-overcommit.node-1-139` | warn | medium | Node node-1-139 (pool default): tenant kinds ['dev', 'prod'], namespaces ['prod-app-o', 'dev-app-o', 'prod-app-m', 'prod-app-l-backend', 'dev-app-m', 'dev-app-n']. Memory limit total 45.4GB / allocatable 29.8GB = 1.52x, request total 18.3GB, c |
| `tenancy.shared-node-limit-overcommit.node-2-218` | warn | medium | Node node-2-218 (pool system-ondemand): tenant kinds ['dev', 'other', 'prod'], namespaces ['monitoring', 'arc-system', 'argocd', 'dev-app-t', 'keda', 'kube-system']. Memory limit total 5.0GB / allocatable 3.2GB = 1.55x, request total 1.7GB, containers without |
| `tenancy.tenant-without-limitrange.arc-runners` | warn | medium | arc-runners (ci): no LimitRange, containers without requests 1 / without a memory limit 1 (pods 1). 7d CPU p95 0.469 cores, memory p95 1.77GB |
| `tenancy.tenant-without-limitrange.prod-app-l-backend` | warn | medium | prod-app-l-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 0.012 cores, memory p95 5.35GB |
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
| `traffic.alb-elb-5xx.k8s-acmeprodlb-b18a4555d7` | warn | medium | ALB k8s-acmeprodlb-b18a4555d7 (internet-facing): 24h requests 176797.0, ELB 5xx 57.0, target 5xx 116.0, rejected connections 0, idle timeout 300s, target groups 40 |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.my-cluster']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-m/app-m-admin` | warn | medium | ingress ['admin-dev.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-o/app-o-admin` | warn | medium | ingress ['admin-dev.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin-dev.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-m/app-m-admin` | warn | medium | ingress ['canary-admin.example-b.ai', 'admin.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-o/app-o-admin` | warn | medium | ingress ['admin.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend` | warn | medium | ['canary-api.example-b.ai', 'api.example-b.ai']: 24h 5xx 78.0 of 64424.0 requests = 0.12% (source alb-cloudwatch), p95 max 0.4205s |
| `traffic.ingress-5xx-ratio.prod-app-n/app-n-frontend` | warn | medium | ['example-c.ai', 'www.example-c.ai']: 24h 5xx 12.0 of 8646.0 requests = 0.14% (source alb-cloudwatch), p95 max 0.6393s |
| `traffic.pod-not-ready.middleware/kafka-exporter` | warn | medium | no Ready ratio metric (kube_pod_status_ready not collected), Unhealthy events 49 |
| `vpccni.ec2-api-errors.node-1-62` | warn | medium | node node-1-62: EC2 API failures 20 (by API {'CreateNetworkInterface': 8, 'DeleteNetworkInterface': 12}), force-removed ENIs 0 / IPs 0 (cumulative since ipamd start, IMDS 404 excluded) |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 111 (0.009), without one in prod 33. emptyDirs without sizeLimit 21 (prod: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-l-backend/deployment/app-l-embedding-server', 'prod-app-l-backend/deployment/tts-proxy', 'prod-app-p/d |
| `hygiene.old-replicasets.cluster` | fail | low | Of 414 ReplicaSets, 349 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 61, '3': 6} |
| `node.cgroup-v1.node-1-139` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-241` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-1-62` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-135` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-2-144` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-218` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.os-not-collected.node-1-117` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `node.os-not-collected.node-2-60` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend` | fail | low | HPA prod-app-l-backend/app-l-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 17.6 days ago |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-frontend` | fail | low | HPA prod-app-l-backend/app-l-frontend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 1% / target 70%, metrics ['cpu'], last scale 84.9 days ago |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `tenancy.dev-shares-prod-nodes.node-1-117` | fail | low | Node node-1-117 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-o', 'app-s-prod']) together with dev pods 2 (['dev-app-o', 'dev-app-t']). Memory limit total/allocatable 1.68, CPU limit total/allocatable 3.37, containers without a  |
| `tenancy.dev-shares-prod-nodes.node-1-139` | fail | low | Node node-1-139 (pool default): prod pods 20 (['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n']) together with dev pods 11 (['dev-app-m', 'dev-app-o', 'dev-app-n', 'dev-vx |
| `tenancy.dev-shares-prod-nodes.node-2-218` | fail | low | Node node-2-218 (pool system-ondemand): prod pods 1 (['prod-app-q']) together with dev pods 1 (['dev-app-t']). Memory limit total/allocatable 1.55, CPU limit total/allocatable 1.55, containers without a memory limit 2 |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 239224, top [['Elastic Load Balancing v2/DescribeTargetHealth', 75306], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 42402], ['EC2/DescribeInstances', 38173], ['EC2/DescribeSecurityGroups', 24763], ['Elastic Load Balancing v2/RegisterTargets', 11695]], |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster disabled (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 8, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 8, apps whose targetRevision is a branch or HEAD 8 ['argocd/application/app-r-prod', 'argocd/application/app-q-prod', 'argocd/application/app-m-prod', 'argocd/application/app-o-prod', 'argocd/application/app-s-prod', 'argocd/application/app-l-backend-prod', 'argocd/appl |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `controlplane.apiserver-slow-traces.cluster` | warn | low | 24h Traces (requests over 500ms) 161: [{'op': 'List', 'count': 146}, {'op': 'Call conversion webhook', 'count': 10}, {'op': 'Update', 'count': 4}, {'op': 'DeltaFIFO Pop Process', 'count': 1}] |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.5, cluster IPv6 False, queries per second 78.95. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-load-balancer.cluster` | warn | low | Of 3 LBs (base charge 49.28 USD/month), zero requests and bytes in 24h: ['acme-db-shared']. NAT gateways 1 (43.07 USD/month + data) |
| `cost.idle-node.node-2-144` | warn | low | Node node-2-144 (c6g.xlarge, pool build-arm64): CPU p95 0.0013285542477559336, memory p95 0.027737400029048925, 44.09 USD/month |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | aws_ebs_csi_* series 0, add-on v1.37.0-eksbuild.1. When enabled, shows EC2 API errors {} / throttles None |
| `ecr.no-lifecycle-policy.ecr/registry/<account>` | warn | low | repositories without a lifecycle policy ['app-n', 'bitnami/kafka', 'ecr-app-s-postgresql-pgvector', 'bitnami/mysql'] (total 10.9GiB), overall 43 repositories, 850 images, 436.6GiB ≈ 46.9 USD/month, untagged images 243 (excluding 173 attestations) |
| `ecr.no-replication.ecr/registry/<account>` | warn | low | replication rules 0, repositories used by prod 27, total 436.6GiB |
| `ecr.tag-mutable-prod.ecr/registry/<account>` | warn | low | MUTABLE repositories 42/43, used by prod 26: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod', 'ecr-app-s-postgresql-pgvector', 'ecr-app-q-postgresql-prod']…, |
| `ecr.untagged-images.ecr/registry/<account>` | warn | low | untagged images 243/850 (excluding 173 BuildKit attestation manifests), repositories 43 |
| `eso.version-old.cluster` | warn | low | external-secrets 0.9.13 (ExternalSecrets 47, PushSecrets 0) |
| `grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana` | warn | low | Grafana 10.2.3 (database ok), ingress ['monitor.my-cluster'], dashboards 28 |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.unused-crds.cluster` | warn | low | 26 of 47 CRDs have zero objects (by group {'generators.external-secrets.io': 7, 'monitoring.coreos.com': 6, 'networking.k8s.aws': 4, 'eventing.keda.sh': 2, 'external-secrets.io': 3, 'keda.sh': 2, 'crd.k8s.amazonaws.com': 1, 'vpcresources.k8s.aws': 1}), 18 webhooks |
| `karpenter.spot-to-spot-consolidation-off.cluster` | warn | low | FEATURE_GATES {'Drift': 'true', 'SpotToSpotConsolidation': 'false'}, NodeClaims terminated by spot interruption 259, drift True |
| `keda.operator-metrics-disabled.cluster` | warn | low | --enable-prometheus-metrics False, operator keda_* metrics exposed False, scaler errors in logs (24h) 0 |
| `keda.scaledobject-never-active.cluster` | warn | low | inactive for more than 14 days ['dev-app-o/scaledobject/app-o-ai-kafka-lag'], not Ready [], fallback active [], scale-to-zero targets ['prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'] |
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 1001 packets (sum over nodes), services with externalTrafficPolicy Local 0, no-local-endpoints drops 0 |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alerts-never-fired.cluster` | warn | low | 130 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent', 'ConfigReloaderSidecarE |
| `observability.saturation-signal-missing.cluster` | warn | low | 36 of 40 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-m', 'app-m-admin'), ('dev-app-m', 'app-m-api'), ('dev-app-m', 'app-m-backend'), ('dev-app-m', 'app-m-frontend'), ('dev-app-o', 'app-o-admin')]), n |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"'])], receivers ['null', 'slack-sre', 'slack-system'], default receiver s |
| `observability.unclassified-errors.cluster` | warn | low | 168 unclassified error lines (22492 lines scanned, 32 files). Top: [('external-secrets \| {"level":"error","ts":<n>.<n>,"msg":"Reconciler error","controller":"externalsecr', 32), ('ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver', 4), ('node:ip-10- |
| `observability.unstructured-logs.argocd` | warn | low | Of 16474 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-n` | warn | low | Of 59527 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.app-s-prod` | warn | low | Of 946512 lines in 1h, 0 parse as JSON (0.0) |
| `prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus StatefulSet replicas 1 (ready 1), restarts 1, started 2026-10-06T12:32:07.180790214Z |
| `prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus 2.49.1 — 2.53 is the last 2.x LTS (2024-07), 3.0 was released 2024-11 |
| `resilience.exec-probe.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.dev-app-o/statefulset/app-o-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.dev-app-t/statefulset/app-t-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.dev-app-t/statefulset/app-t-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U vxt_chatbot -d vxt_ |
| `resilience.exec-probe.kube-system/daemonset/aws-node:aws-node` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s', 'port': None, 'timeout_s': 10, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 60}, |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.middleware/statefulset/redis-master:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': 'sh -c /health/ping_liveness_local.sh 5', 'port': None, 'timeout_s': 6, 'period_s': 5, 'failure_threshold': 5, 'initial_delay_s': 20}, readiness {'type': 'exec', 'path': |
| `resilience.exec-probe.prod-app-q/statefulset/app-q-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-q" -d "dbname=app-q" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_ |
| `resilience.exec-probe.prod-app-m/statefulset/app-m-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.prod-app-o/statefulset/app-o-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.prod-app-l-backend/deployment/app-l-file-worker:file-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.FileWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.GraphWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-p/statefulset/app-p-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-p" -d "dbname=app-p" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s' |
| `resilience.exec-probe.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec password_aux="${MYS |
| `resilience.exec-probe.app-s-prod/statefulset/app-s-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-s-user" -d "dbname=app-s_tp" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-ai:ai` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health', 'port' |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health', 'port' |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-studio:studio` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health', 'port' |
| `resilience.liveness-dependency-path.prod-app-q/deployment/app-q-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port':  |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-admin:admin` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeo |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-api:api` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeo |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-backend:backend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeo |
| `resilience.liveness-dependency-path.prod-app-m/deployment/app-m-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeo |
| `resilience.liveness-dependency-path.prod-app-l-backend/deployment/app-l-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health', 'port' |
| `resilience.liveness-dependency-path.prod-app-p/deployment/app-p-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 7860, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/healthz', 'po |
| `resilience.liveness-dependency-path.prod-app-p/deployment/app-p-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port':  |
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
| `resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | low | pod argocd-repo-server-d487895cc-bth22: 7d memory working set p95 91 MB / request 512 MB = 0.18 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | low | pod app-o-ai-7cdbdc7544-szzcl: 7d memory working set p95 342 MB / request 1024 MB = 0.33 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | low | pod app-o-backend-69dbdf4f65-9x6jc: 7d memory working set p95 131 MB / request 512 MB = 0.26 |
| `resources.memory-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | low | pod app-t-postgres-0: 7d memory working set p95 28 MB / request 256 MB = 0.11; database-like: keep the request |
| `resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | low | pod karpenter-9769889bd-nphgs: 7d memory working set p95 24 MB / request 256 MB = 0.09 |
| `resources.memory-request-overprovisioned.middleware/sts/redis-master:redis` | warn | low | pod redis-master-0: 7d memory working set p95 5 MB / request 256 MB = 0.02; database-like: keep the request |
| `resources.memory-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | low | pod vm-single-0: 7d memory working set p95 160 MB / request 512 MB = 0.31 |
| `resources.memory-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | low | pod app-q-backend-postgresql-0: 7d memory working set p95 52 MB / request 256 MB = 0.20; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-ai:ai` | warn | low | ['pod app-o-ai-55b7448547-mzrjj: 7d memory working set p95 680 MB / request 2048 MB = 0.33', 'pod app-o-ai-55b7448547-mpj4r: 7d memory working set p95 411 MB / request 2048 MB = 0.20'] |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | low | ['pod app-o-backend-596479b6f8-cx44t: 7d memory working set p95 96 MB / request 512 MB = 0.19', 'pod app-o-backend-596479b6f8-nv9j2: 7d memory working set p95 77 MB / request 512 MB = 0.15'] |
| `resources.memory-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | low | ['pod app-l-frontend-6d58bbfcfc-nfk9x: 7d memory working set p95 79 MB / request 256 MB = 0.31', 'pod app-l-frontend-6d58bbfcfc-2qgs6: 7d memory working set p95 75 MB / request 256 MB = 0.29'] |
| `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | warn | low | pod app-l-neo4j-0: 7d memory working set p95 769 MB / request 4096 MB = 0.19; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | low | pod app-s-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.22; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-backend` | warn | low | HPA prod-app-l-backend/app-l-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-frontend` | warn | low | HPA prod-app-l-backend/app-l-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin` | warn | low | HPA dev-app-m/app-m-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 166.3 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api` | warn | low | HPA dev-app-m/app-m-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 196.0 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend` | warn | low | HPA dev-app-m/app-m-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 17% / target 70%, metrics ['cpu'], last scale 66.8 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin` | warn | low | HPA dev-app-o/app-o-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 55.8 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend` | warn | low | HPA dev-app-o/app-o-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 17.8 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend` | warn | low | HPA dev-app-o/app-o-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 20% / target 70%, metrics ['cpu'], last scale 17.8 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend` | warn | low | HPA dev-app-n/app-n-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 36.2 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend` | warn | low | HPA dev-app-n/app-n-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 40.2 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-frontend` | warn | low | HPA dev-app-n/app-n-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 6% / target 70%, metrics ['cpu'], last scale 0.8 days ago |
| `scaling.hpa-never-scaled.dev-app-t/deployment/app-t-backend` | warn | low | HPA dev-app-t/app-t-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 19.9 days ago |
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
| `tenancy.dev-shares-prod-nodes.node-1-62` | warn | low | Node node-1-62 (pool default): prod pods 13 (['prod-app-q', 'prod-app-m', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']) together with dev pods 2 (['dev-app-m', 'dev-app-n']). Memory limit total/allocatable 0.93, CPU limit tota |
| `tenancy.dev-shares-prod-nodes.node-2-60` | warn | low | Node node-2-60 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-m', 'prod-app-n']) together with dev pods 2 (['dev-app-m', 'dev-app-n']). Memory limit total/allocatable 1.49, CPU limit total/allocatable 2.44, containers without |
| `traffic.alb-protection-off.k8s-acmeprodlb-b18a4555d7` | warn | low | ALB k8s-acmeprodlb-b18a4555d7: deletion_protection False, access_logs False, target groups in the ingress group 40 |
| `vpccni.metrics-unreadable.cluster` | warn | low | 2 of 8 nodes without readable ipamd metrics (localhost:61678): ['node-1-117', 'node-2-60'] |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |
| `hygiene.no-progressive-delivery.cluster` | fail | info | No progressive-delivery component (Argo Rollouts, Flagger). All deployments are rolling updates (replace everything) -- ALB weighted target groups are not used either |

### 7-6. Tool notes (about kubegap itself)

Numbering continues from the 2026-10-26 16:47 full report, whose notes ended at 48. The 2026-10-27 15:30 snapshot has no report.

Earlier notes still open:
- Notes 2, 20, 30, 37 and 44: network errors on deleted nodes. Reproduced, see 57.
- Note 3: `vpccni.node-ip-exhaustion` on system nodes. Reproduced, see 53.
- Note 4: the VPC quota is high at 3 of 5. Reproduced and lowered.
- Notes 5, 32, 38 and 45: commands that fail on the two nodes missing from SSM. Reproduced, see 58.
- Notes 7, 13 and 22: a node replacement shows up as new and resolved findings. Reproduced: `ip-10-0-1-4` was replaced by `ip-10-0-2-144` in `node.cgroup-v1` and `cost.idle-node`.
- Notes 21, 31, 39 and 46: the EOL date. This run says D+225 from 2026-03-23, which is consistent, and the evidence still names no source.
- Note 25: `<n>` masking in the scheduler evidence. Reproduced in all three `controlplane.scheduler-unschedulable` findings.
- Note 26: dev target groups reported at high. Reproduced and lowered.
- Note 27: `observability.log-coverage-gap` does not say why every pod on a tainted node is missing. Reproduced on the build node `ip-10-0-2-144`.
- Notes 28, 36 and 43: apiserver values measured while collecting. Reproduced, see 60.
- Notes 40 and 47: dollar evidence. Reproduced.
- Note 48: throttling judged from a single 5-minute value. Reproduced, see 59.

Notes closed this run:
- Notes 34 and 41: the stuck 723 5xx count. The app-m-backend 5xx count is now 78 of 64,424, so the number moves.
- Notes 29, 35 and 42: the request floor of the latency check. PR #67 added a warn under 100 requests.

49. **`traffic.db-exposed` treats an NLB defined outside the cluster as open because it never reads that NLB's security group.** aws/describe-security-groups.json holds only the two cluster security groups. aws/alb-metrics.json `lbs[].security_groups` lists `sg-db-shared-nlb` for `acme-db-shared`. That group allows 3306–3311, 5432, 5433, 6379 and 7687 only from four /32 addresses, per extra/nlb-security-groups.txt. The finding says "sourceRanges None" and fail/high, and the 2026-10-26 reports repeated "open to the internet" from it. Suggestion: add a collector step that describes the security groups listed under `lbs[].security_groups`, and judge exposure from their ingress CIDRs. This is a read-only command that should become a collector.
50. **`resilience.n-plus-one` passes because of its 2% margin and because it pools allocatable memory across nodes that app pods cannot use.** summary.json resilience.n_plus_one shows `requests_memory_gb_total` 47.5 against `allocatable_memory_gb_without_largest` 46.6, with `memory_ok: true` and `margin: 0.02` from lib/resilience.py:698. 31 of the pods on the largest node carry `nodeSelector: workload-type=app`, per objects/pods.json. The only other node with that label has 0.16 cores of request room. Suggestion: compute N+1 per node-selector pool, and do not let the margin turn a shortfall into ok.
51. **`resilience.restarts-crashloop` and `resources.oomkilled-repeated` read a lifetime restart count.** `argocd-application-controller-0` shows 42 restarts, yet its previous container ran from 2026-05-12T08:32:38Z to 2026-10-30T09:00:04Z, per objects/pods.json lastState. That is one restart in 171 days, reported as warn/high "crashloop". Suggestion: use the 7-day increase from metrics/restarts_7d.json.
52. **`controlplane.scheduler-unschedulable` and `events.tracked-warning-reasons.FailedScheduling` report fail/high for KEDA scale-from-zero.** In events.json, `app-l-file-worker-db75d7fdc-9dkp4` got FailedScheduling at 01:41:06Z, Nominated to `nodeclaim/default-qqbxg` at 01:41:08Z, and was scheduled once that node was ready about 100 s later. This is Karpenter working as designed. Suggestion: do not count a pod that has a Nominated event and is scheduled within the measured Karpenter launch latency.
53. **`vpccni.node-ip-exhaustion` gives fail/high at 61% IP use because of a cumulative counter.** `ip-10-0-1-139` uses 34 of 56 IPs. Its 4 "no available IP" events are counted since ipamd started on a node that has been up 40.1 days, per summary.json vpccni.nodes. Suggestion: window the counter to 24 hours. Note 3 remains for the system nodes.
54. **`observability.no-symptom-alerts` counts 0 symptom rules although three exist.** In prometheus/rules.json, `ImageInferenceE2ESuccessRateDrop` divides end-to-end successes by starts, below 0.95. `LoraTrainingSuccessRateDrop` does the same below 0.99, and `LoraTrainingDurationP95High` fires on a p95 over 7,200 s. All three carry `category: golden`. They are classified as "app". Suggestion: treat `category: golden` labels and success-over-start ratios as symptoms.
55. **`observability.alerts-always-firing.KubePodNotReady` stays fail although the alert stopped.** summary.json observability.alerts.firing_now has no `KubePodNotReady`, and the 20 Failed pods are gone, yet the 7-day sample count of 169,042 keeps it at fail. Suggestion: add "not firing now" to the evidence and cap the status at warn.
56. **A check that passes on missing data shows up as "new" later.** In the 2026-10-27 snapshot, `security.imds-hop-limit` passed with `summary.security.aws.imds_by_setting` empty, and the six `argocd.*` checks were skipped because `summary.argocdctl.summary` was missing. In this run the same cluster gives warn and fail, and diff.json lists them as new. Suggestion: skip `security.imds-hop-limit` when there is no IMDS data, and have diff mark findings whose check was skip in snapshot A as "first evaluated" instead of new.
57. **Reproduction of note 44.** `node.network-errors.<ip>:9100:eth0` reports 317 errors. Karpenter removed that node at 2026-11-02T05:09:54Z by emptiness delete, per logs/pods/AGGREGATED.json, and it is not in inventory.json.
58. **Reproduction of note 45.** summary.json run.failed lists 24 commands:
    - 19 node commands and controller metric reads on `ip-10-0-1-117` and `ip-10-0-2-60`, which are not registered in SSM.
    - 4 `ecr.lifecycle-policy` lookups that return LifecyclePolicyNotFoundException. That is a finding, not a failure.
    - 1 ALB controller pod proxy timeout.
59. **Reproduction of note 48.** `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` is fail/high on a 5-minute ratio of 0.264. The same container's 7-day limit p95 is 0.08, per metrics/cpu_limit_p95_ratio_7d.json, and its ALB p95 is 0.22 s.
60. **Reproduction of notes 28, 36 and 43.** `controlplane.apiserver-latency` uses `rate(...[5m])` in metrics/apiserver_p99_latency_by_verb.json, taken while collection was listing objects. LIST p99 is 0.705 s and PATCH p99 0.709 s. Suggestion: take the p99 over a 1-hour window that ends before collection starts.
61. **history.csv in this snapshot root has no row for 2026-10-27T15-30-14.** Rows go from 2026-10-26T16-47-02 straight to 2026-11-03T11-17-15. The older rows say profile `eks` where the current ones say `prod`. Trend charts built from history.csv will skip that run and split the profile.

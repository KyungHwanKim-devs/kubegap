# kubegap report details — arn:aws:eks:us-east-1:<account>:cluster/my-cluster (`my-cluster`), full mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `llm/facts.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `my-cluster` / arn:aws:eks:us-east-1:<account>:cluster/my-cluster (eks, v1.32.13-eks-577a51e) |
| Run time / mode | 2026-11-05T17:18:26+09:00 / full (collection 355.7 s, 0 steps skipped by mode, 5 failed) |
| Profile | `prod` (detected) |
| kubegap / rubric / signatures | 0.1.2 / 0.1.80 / 1.1.0 |
| Nodes / namespaces / pods / CRDs | 8 (Ready 8) / 25 / 145 / 47 |
| Components (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics store | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| Log store | loki 2.6.1 |
| Node access | ssm (EKS: SSM send-command); SSM unregistered 2 |
| Snapshot | `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 1 | 3 | fail +0 · warn +1 |
| high | 31 | 25 | fail -1 · warn +1 |
| medium | 120 | 163 | fail +9 · warn -4 |
| low | 16 | 139 | fail +0 · warn +1 |
| info | 2 | 0 | no previous run of this mode |

Checks 365: evaluated 357, disabled by profile 2, skipped 4, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

| Finding | First pass | Final | Reason |
|---|---|---|---|
| resilience.n-plus-one.cluster | critical warn | high warn | Karpenter가 있어서 warn이에요. 네 가지 부재 규칙에서 warn은 high예요. 노드를 잃으면 파드가 영원히 못 뜨는 게 아니라 새 노드를 기다려요. |
| observability.no-slo.cluster | critical warn | high warn | SLO 라벨이 붙은 앱 규칙 5개를 찾아 warn이에요. 네 가지 부재 규칙에서 warn은 high예요. |
| observability.no-symptom-alerts.cluster | critical warn | high warn | 앱 메트릭 규칙 14개를 찾아 warn이에요. 네 가지 부재 규칙에서 warn은 high예요. |
| controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker | high fail | medium fail | KEDA가 0에서 늘린 파드를 Karpenter가 새 노드로 받는 동안 생기는 대기예요. 노드는 p50 58초에 준비되고 수집 시점에 Pending 파드는 0개예요. |
| controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker | high fail | medium fail | app-l-file-worker와 같은 이유예요. |
| controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner | high warn | medium warn | CI 러너가 build-arm64 노드를 기다린 것이고 Pending 파드는 0개예요. |
| events.tracked-warning-reasons.FailedScheduling | high fail | medium fail | 이벤트 대상이 app-l-file-worker와 app-l-graph-worker 파드예요. 위와 같은 이유예요. |
| eks.service-quota-near-limit.aws-account | high warn | low warn | 가장 높은 할당량이 VPC 3/5(60%)이고 80%를 넘는 게 없어요. |
| traffic.db-exposed.nlb/acme-db-shared | high warn | medium warn | 모든 DB 포트가 /32 주소 4개 이하로만 열려 있어요. 분석 절차의 기준대로 medium이에요. |
| controlplane.apiserver-5xx.cluster | high warn | medium warn | 초당 0.004건이고 수집 중에 잰 값이라 kubegap 요청이 섞였을 수 있어요. 사용자 영향으로 세지 않아요. |
| storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0 | high fail | medium fail | dev 네임스페이스이고 하루 증가량이 0GB예요. |
| traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend | high fail | medium fail | dev 대상 그룹이에요. 원인은 문제 4와 같아요. |
| traffic.alb-unhealthy-targets.dev-app-t/app-t-backend | high fail | medium fail | dev 대상 그룹이고 24시간 요청이 0건이에요. |

### 1-2. Aggregates the LLM recounted

| Finding | First pass | Final | Reason |
|---|---|---|---|
| resilience.prod-db-without-backup-cronjob.cluster | 목록 7개 | 7 | summary.json resilience.backup.prod_db_without_backup_cronjob 목록을 셌어요. prod PV 7개(objects/persistentvolumes.json)와 하나씩 맞아요. |
| resilience.n-plus-one.cluster | pods on that node 33 | 38 | objects/pods.json에서 spec.nodeName이 node-1-139인 파드를 세면 38개예요. 체크의 33개는 DaemonSet 파드 5개를 뺀 수예요. |
| resilience.prod-concentration.node-1-139 | prod pods 20 | 20 | objects/pods.json에서 prod 네임스페이스 파드를 다시 셌어요. app-r 2, app-m 4, app-o 7, app-l 4, app-p 1, app-n 1, app-s 1이에요. |
| resilience.prod-concentration.node-1-139 | - | 레플리카 1인 prod 워크로드 6개 | objects/deployments.json에서 replicas 1이고 파드가 이 노드에 있는 것: app-m-admin, app-o-admin, app-o-frontend, app-p-backend, app-n-admin-frontend, app-s-backend. |
| storage.csi-snapshot-unavailable.cluster | EBS snapshots in 30 days 12 | 12개 모두 고아 PVC 삭제 전 스냅샷 | aws/ec2-snapshots-30d.json의 12개가 모두 2026-10-06에 뜬 'pre-delete backup of orphan PVC'이고 delete-after 2026-11-07 태그가 있어요. 지금 쓰는 prod 볼륨의 스냅샷은 0개예요. |

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | high |  | 24h 'Unable to schedule pod; no fit' 78 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient memory, <n> node(s) had untolerated taint … |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` | high |  | 24h 'Unable to schedule pod; no fit' 28 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient memory, <n> node(s) had untolerated taint … |
| `eks.no-backup-policy.cluster` | high | 8 | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'stale_backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | high | 8 | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | high |  | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 194 occurrences total (90 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 … |
| `karpenter.ec2nodeclass-al2.cluster` | high | 8 | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 462MB |
| `observability.no-event-retention.cluster` | high |  | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e: EKS end of standard support 2026-03-23, 227 days past; upstream end of life 2026-02-28 |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | high |  | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling … |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.28, 24 h or the pod's life 0.26: throttled through the day |
| `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` | high |  | kernel log: 0 kills in 24 h on 2 of 2 nodes read. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods. cAdvisor counter 0 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | high |  | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (6.2 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
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
| `vpccni.node-ip-exhaustion.node-1-139` | high |  | node node-1-139 (r8gd.xlarge, pool default): pod IPs 35/56 (0.625), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 20. prefix delegation False |

## 3. Changes since the previous run of this mode

Compared `2026-11-03T11-17-15` → `2026-11-05T17-18-26` (rubric 0.1.63 → 0.1.80).

- **New (19)**: `controlplane.apiserver-5xx.cluster` (warn/high), `cost.idle-node.node-2-158` (warn/low), `node.cgroup-v1.node-2-158` (fail/low), `node.disk-usage.<ip>:9100:/` (warn/high), `observability.unstructured-logs.monitoring` (warn/low), `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` (warn/medium), `resilience.n-plus-one.cluster` (warn/critical), `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/medium), `resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend` (warn/medium), `resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend` (warn/high), `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-file-worker:file-worker` (fail/medium), `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker` (fail/medium), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-4248d:runner` (fail/medium), `resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/low), `scaling.hpa-flapping.prod-app-l-backend/hpa/keda-hpa-app-l-file-worker` (warn/medium), `traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend` (warn/medium), `traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana` (warn/medium), `traffic.pod-not-ready.arc-runners/self-hosted-arm64-8msc5-runner` (warn/medium), `vpccni.ec2-api-errors.node-2-158` (warn/medium)
- **Resolved (12)**: `controlplane.controller-error-repeat.horizontal.go` (warn/medium), `cost.idle-load-balancer.cluster` (warn/low), `cost.idle-node.node-2-144` (warn/low), `node.cgroup-v1.node-2-144` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `node.network-errors.<ip>:9100:eth0` (warn/medium), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-z2bk5:runner` (fail/medium), `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` (fail/high), `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (warn/high), `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` (fail/high), `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend` (fail/medium), `traffic.pod-not-ready.middleware/kafka-exporter` (warn/medium)
- **Changed (19)**: `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` (['warn', 'fail']/['high', 'high']), `logs.signatures.containerd.shim-error` (['fail', 'warn']/['medium', 'medium']), `loki.memory-pressure.monitoring/statefulset/loki-stack` (['warn', 'fail']/['medium', 'medium']), `resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle` (['fail', 'warn']/['medium', 'medium']), `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (['warn', 'fail']/['high', 'high']), `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` (['fail', 'warn']/['high', 'high']), `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` (['warn', 'fail']/['high', 'high']), `tenancy.prod-without-quota.prod-app-r` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-q` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-m` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-o` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-l-backend` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-p` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.prod-app-n` (['warn', 'fail']/['medium', 'medium']), `tenancy.prod-without-quota.app-s-prod` (['warn', 'fail']/['medium', 'medium']), `tenancy.tenant-without-limitrange.prod-app-l-backend` (['warn', 'fail']/['medium', 'medium']), `traffic.alb-elb-5xx.k8s-shared-alb` (['warn', 'fail']/['medium', 'medium']), `traffic.db-exposed.nlb/acme-db-shared` (['fail', 'warn']/['high', 'high']), `traffic.ingress-p95-latency.prod-app-q/app-q-ai` (['fail', 'warn']/['medium', 'medium'])
- **Rename suspects (1)**: `None`
- **Objects**: added 7, removed 6, changed 10: `configmaps/kube-system/aws-load-balancer-controller-leader` metadata.resourceVersion, `deployments/dev-app-m/app-m-frontend` spec.template, `deployments/prod-app-q/app-q-ai` spec.template, `deployments/prod-app-q/app-q-backend` spec.template, `deployments/prod-app-q/app-q-studio` spec.template, `deployments/prod-app-q/app-q-web` spec.template, `deployments/prod-app-p/app-p-backend` spec.template, `deployments/prod-app-p/app-p-web` spec.template, `deployments/app-s-prod/app-s-backend` spec.template, `deployments/app-s-prod/app-s-frontend` spec.template
- **Warning events**: UpdateFailed +205 (ExternalSecret/database/mysql-app-n-secret), Unhealthy -40 (Pod/prod-app-m/app-m-backend-7c46f75bf6-gvlh2), FailedScheduling +3 (Pod/prod-app-l-backend/app-l-file-worker-db75d7fdc-9h5xx), FailedDraining +2 (Node/node-2-115), InstanceTerminating +2 (NodeClaim/default-6xtbg), NetworkNotReady +2 (Pod/kube-system/ebs-csi-node-4kks6), CgroupV1 +1 (Node/node-2-115), InvalidDiskCapacity +1 (Node/node-2-115)

### 3-0. Criteria changes, not cluster changes

These findings appeared, disappeared or changed because the checks did, not the cluster, and they are kept out of the lists above. Taken from `diff.json` `findings.criteria_changes`; the report writes them as a criteria change and never as a tool defect.


Checks from before rule hashes, under a different rubric version; their findings stay in the lists above marked `rule_known: false`, and the report reads these checks' notes: `controlplane.apiserver-5xx`, `controlplane.controller-error-repeat`, `controlplane.scheduler-unschedulable`, `cost.idle-load-balancer`, `cost.idle-node`, `logs.signatures`, `loki.memory-pressure`, `node.cgroup-v1`, `node.disk-usage`, `node.network-errors`, `observability.unstructured-logs`, `resilience.db-probe-timeout`, `resilience.n-plus-one`, `resources.cpu-request-overprovisioned`, `resources.cpu-throttling`, `resources.krr-recommendation`, `resources.large-request-binpacking`, `resources.memory-limit-near-p95`, `resources.memory-request-overprovisioned`, `resources.oomkilled`, `resources.oomkilled-repeated`, `scaling.hpa-flapping`, `tenancy.prod-without-quota`, `tenancy.tenant-without-limitrange`, `traffic.alb-elb-5xx`, `traffic.db-exposed`, `traffic.ingress-5xx-ratio`, `traffic.ingress-p95-latency`, `traffic.pod-not-ready`, `vpccni.ec2-api-errors`
- **Persisted (Toil)**: 428 findings present in all 8 runs checked, 462 in 3 or more; top checks: `resources.cpu-request-overprovisioned` 34, `resources.krr-recommendation` 31, `traffic.alb-deregistration-vs-grace` 28, `resilience.no-prestop` 21, `scaling.no-hpa-serving-prod` 21, `resilience.exec-probe` 17, `resilience.single-replica-in-prod` 16, `resources.memory-request-overprovisioned` 13

### 3-1. Why things changed

지난 full 점검(2026-11-03 11:17 KST)과 이번 점검 사이는 약 54시간이에요. 노드 node-2-144가 떠나고 build-arm64 풀 노드 node-2-158이 2026-11-05 15:49 KST에 새로 떴어요. Deployment 9개의 파드 템플릿이 바뀌었어요. prod-app-q 4개, prod-app-p 2개, app-s-prod 2개, dev-app-m 1개이고, 모두 IAC 저장소 main을 따르는 Argo CD 앱이 동기화한 거예요. app-l-file-worker와 app-l-graph-worker는 KEDA가 0과 N 사이를 오가면서 Karpenter가 노드를 띄웠다 지웠고, 24시간 동안 노드 41대가 떠났어요. 그래서 FailedScheduling과 krr 권장값, HPA 흔들림이 새로 보여요. kubegap 기준이 0.1.63에서 0.1.80으로 바뀌면서 N+1 경고, 공용 DB NLB의 warn 전환, 스로틀링과 OOM 상태 변화가 생겼고 이건 클러스터 변화가 아니에요. 자동 판정 합계는 fail 162에서 170, warn 331에서 330이 됐어요. ResourceQuota나 LimitRange는 바뀌지 않았는데 쿼터 없음 8개가 fail로 올라간 이유는 체크 기록으로 확인하지 못했어요. 지난 점검에는 검토한 리포트가 없어서 시킨 일을 했는지는 따질 수 없어요.

## 4. Detail per area

### resources

krr 권장보다 많이 요청하는 컨테이너가 34개예요(fail 16). 가장 큰 건 app-l-file-worker(CPU 1.0→0.128)와 app-l-graph-worker(1.0→0.542)예요. CPU 요청 과다 38개, 메모리 요청 과다 14개예요. 프론트엔드 스로틀링은 prod-app-m/app-m-frontend 0.23~0.28, prod-app-o/app-o-frontend 0.15이고 Prometheus는 0.28이에요. OOM은 argocd-application-controller(2026-10-30, 재시작 42), app-q-ai(7일 3개), loki-stack(2026-10-25)이에요. middleware/kafka-controller의 jmx-exporter 힙이 limit에 비해 커요. 데이터베이스 요청은 p95로 줄이지 않아요.

### scaling

prod Deployment 21개가 HPA 없이 레플리카 고정이에요. HPA 13개는 한 번도 늘어나지 않았어요. keda-hpa-app-l-file-worker는 7일에 48번 바뀌어요. node-1-139의 NodeClaim이 만료를 301.9시간 넘겼어요(문제 2). system-ondemand 노드 세 대가 2026-11-07~08에 만료돼요. KEDA 외부 트리거에 fallback이 없어요.

### observability

알림 규칙 157개 중 증상 규칙은 0개이고, SLO와 burn rate 알림이 없어요. KubeControllerManagerDown과 KubeSchedulerDown은 57.8일째 울리고 있지만 EKS 관리형 컨트롤플레인이라 잘못 잡힌 알림이에요. KubePodNotReady도 계속 울려요. Loki와 Alertmanager 데이터가 emptyDir에 있고 Loki 보존 기간이 강제되지 않아요. 이벤트 보존이 없어요. Grafana 데이터소스 오류가 있어요.

### traffic

prod ALB 대상 그룹 4개의 헬스 체크가 404로 실패해요(문제 4). Kafka NLB가 0.0.0.0/0에 열려 있어요(문제 3). 공용 DB NLB는 /32로 좁혀져 있어요. 공유 ALB의 24시간 요청 204733건 중 ELB 5xx 168건, 대상 5xx 771건이에요. app-m-frontend 5xx는 0.14%예요. 대상 그룹 28개의 deregistration delay가 파드 grace보다 길어요. 노드 세 대가 ENI 한도에 닿았고 prefix delegation이 꺼져 있어요.

### resilience

prod DB 7개에 백업이 없어요(문제 1). 스팟 노드 한 대에 prod 파드 48%가 있어요(문제 2). prod 레플리카 1인 워크로드 16개, readiness probe 없는 것 10개, preStop 없는 것 21개, 같은 존에만 있는 것 5개예요. tts-proxy는 노드 하나에만 뜰 수 있어요. redis-master는 셸이 PID 1이에요.

### hygiene

변경 상관관계는 24시간 집계값만 있어서 시각을 맞출 수 없었어요. 확인하려면 range query가 필요해요. 가변 이미지 태그 4개, 0 레플리카 ReplicaSet 418개 중 353개가 남아 있어요. 점진 배포 도구가 없어요. AL2 호환성 인사이트가 ERROR예요(문제 5).

### storage

prod DB PV 7개가 reclaimPolicy Delete이고 스냅샷 도구가 없어요(문제 1). StorageClass gp3, gp3-1a, gp3-1c가 암호화되지 않았고 볼륨 확장이 꺼져 있어요. in-tree gp2가 남아 있어요. dev-app-t MySQL PVC가 90%예요.

### security

EKS API 공개 엔드포인트가 0.0.0.0/0이에요. NetworkPolicy 3개가 적용되지 않아요. tts-proxy가 NET_ADMIN과 /dev/net/tun hostPath를 써요. Argo CD default 프로젝트가 모든 저장소와 대상을 허용하고 prod 앱 8개가 거기 있어요. admin 계정 SSO가 없어요. PSA가 강제되지 않고, IMDS hop limit이 2예요. ECR 이미지 스캔이 꺼져 있어요. 인증 없는 관리 화면 후보 Ingress가 7개예요.

### cost

노드 월 추정 479.33 USD 중 유휴가 454.0 USD(95%)예요. CPU 요청 8.68코어를 krr 권장대로 줄이면 2.09코어가 돼 월 162.65 USD쯤 줄어요. 스팟 비중은 0.38이에요. 확장 지원 요금은 여기 들어가 있지 않아요.

### tenancy

prod 네임스페이스 8개 모두 ResourceQuota가 없고, 5개는 경계(쿼터, LimitRange, NetworkPolicy, PSA)가 비어 있어요. dev 파드가 prod와 같은 노드에 있어요. prod-app-l-backend는 7일 CPU 최대가 중앙값의 352배예요. 이웃 영향은 node-1-62가 7일 동안 90분 포화됐지만 가장 많이 쓴 네임스페이스 비중이 2.5%이고 prod 스로틀링이 없어서 근거가 없어요.

### node OS

SSM으로 읽은 노드 6대 중 AL2 노드는 cgroup v1이에요. node-1-139 루트 디스크가 81%이고 kubelet 이미지 GC가 2번 실패했어요. containerd shim 오류가 24시간에 33번 있었어요. node-2-135에서 커널 네트워크 메모리 압박 경고가 있어요. 노드 그룹 두 대는 SSM에 없어서 못 읽었어요.

### platform

EKS 1.32 확장 지원, Karpenter 0.37(1.30까지 지원), EC2NodeClass AL2, 노드 그룹 AMI 331일이에요(문제 5). EKS 애드온 4개 모두 새 버전이 나와 있어요. aws-ebs-csi-driver(v1.37.0)와 vpc-cni(v1.19.0)는 기본 버전보다 많이 뒤처졌어요. 감사 로그가 꺼져 있어요. Argo CD v2.13.0, Prometheus 2.49.1, Loki 2.6.1, Grafana 10.2.3, ESO가 오래된 버전이에요.

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
- Not collected in full mode 0: none
- Skipped or errored 4: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing), `observability.alert-metric-without-dashboard` (skip: nothing to judge: dashboards json not available)
- Judged in part 22 (some targets lacked what the rule needs; those are not judged, not passed): `node.kernel-oom-node-level` (2 not judged: node not read (2)), `node.kernel-lockup` (2 not judged: node not read (2)), `node.kernel-io-fs-errors` (2 not judged: node not read (2)), `node.kernel-nic-events` (2 not judged: node not read (2)), `node.conntrack-table-full` (2 not judged: node not read (2)), `node.kernel-net-mem-pressure` (2 not judged: node not read (2)), `node.cgroup-v1` (2 not judged: node not read (2)), `node.sysctl-tuning` (2 not judged: node not read (2)), `node.cri-not-ready` (2 not judged: node not read, or cri not read (2)), `node.cri-exited-containers` (2 not judged: node not read (2)), `node.service-restarts` (2 not judged: node not read (2)), `node.reboot-required` (2 not judged: node not read (2)), `node.os-updates-pending` (2 not judged: node not read (2)), `node.kubelet-reserved-missing` (2 not judged: node not read, or kubelet not read (2)), `node.kubelet-eviction-memory-missing` (2 not judged: node not read, or kubelet not read (2)), `node.clock-unsynced-os` (2 not judged: node not read (2)), `node.zombie-processes` (2 not judged: node not read (2)), `node.kubelet-api-qps-low` (2 not judged: node not read, or kubelet not read (2)), `node.docker-and-containerd` (2 not judged: node not read (2)), `node.container-writable-layer-large` (2 not judged: node not read (2)), `node.large-images` (2 not judged: node not read (2)), `vpccni.ec2-api-errors` (2 not judged: metrics not read (2))

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 | node-os | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'cronjobs.batch', 'storageclasses.storage.k8s.io']) |
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

680 commands, 355.7 s. Failed steps: 5: `core.node-os` ; `eks-platform.kubelet-journal` ; `eks-platform.containerd-journal` ; `kube-proxy.proxy-mode` ; `vpc-cni.ipamd-metrics` 

Commands that failed inside a step that still succeeded (run.log): 14: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: context deadline exceeded (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.bitnami/mysql` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.bitnami/kafka` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.ecr-app-s-postgresql-pgvector` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.app-n` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

Deprecated-API tools: kubent 28 of 41 Lists answered (13 refused or not served); pluto 101 of 111 Lists answered (10 refused or not served).

### 7-2. Checks evaluated

365 checks: disabled 2, done 357, llm 2, skip 4. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.0, 33 files, 23448 lines scanned (components: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 56.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 62 | 2026-11-05T00:24:21Z , 2026-11-05T08:11:04Z | [pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:24:21.605206449Z … |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-04T08:48:29Z , 2026-11-04T08:48:29Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T08:48:29.881532186Z … |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-05T03:40:39Z , 2026-11-05T08:21:00Z | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:39.431880726Z W1105 03:40:39.431762       1 reflector.go:561] … |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 42 | 2026-11-04T09:02:26Z , 2026-11-05T07:55:11Z | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T09:02:26.073535127Z E1104 09:02:26.073405       1 scraper.go:149] "Failed to scrape node" … |
| containerd.shim-error | containerd | node | medium | warn | 33 | 2026-11-04T09:27:46Z , 2026-11-05T07:20:08Z | 2026-11-04T10:05:50+0000 node-1-139 containerd[1461]: time="2026-11-04T10:05:50.780130578Z" level=warning msg="cleaning up … |
| kubelet.image-gc-failed | kubelet | node | medium | warn | 2 | 2026-11-04T10:06:59Z , 2026-11-05T05:52:02Z | 2026-11-04T10:06:59+0000 node-1-139 kubelet[1593]: E1104 10:06:59.922962    1593 kubelet.go:1564] "Image garbage collection … |
| karpenter.spot-interruption | karpenter | resilience | low | info | 2 | 2026-11-04T09:01:23Z , 2026-11-05T05:31:47Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T09:01:23.567148794Z … |
| common.context-deadline | any | traffic | low | info | 1 | 2026-11-05T08:10:20Z , 2026-11-05T08:10:20Z | [pod/loki-stack-0/loki] 2026-11-05T08:10:20.369702669Z level=warn ts=2026-11-05T08:10:20.368921895Z caller=logging.go:67 traceID=386aaaf2b584283b orgID=fake … |

| Normalized message | Count | Files |
|---|---|---|
| grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=admin fromAlert=false t=<ts> level=error msg="Er | 12 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| node:node-2-158 \| time="<ts>" level=error msg="failed to load cni during init, please check CRI plugin status before setting up network for pods" error="cni c | 2 | logs/node/node-2-158/containerd-24h.log |
| node:node-2-158 \| "Eviction manager: failed to get summary stats" err="failed to get node info: node \"node-<n>\" not fou | 2 | logs/node/node-2-158/kubelet-24h.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node node-<n> | 2 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"49c3df5ef5da35e98fe0dd4ae2e4e3b3a3a206cb8e7932ff7da3baaccfbd0b1c\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"d21bfec6661abdc6830281d5e12eea11710af0b5aaa0fe3b60667f583942ebe3\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"451879ce04a5a050e80ba066b669b770628fb0a6d9a4e75c3706c96ed75f6aaa\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"c7d348db476208861c11c8a2d96978f344aa5ba268f20cd85eae55995220f97b\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"65c000bd3618ac5b99a4a93326265a4a9d70f6c7139e909582f361454ffef1b0\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<ts>" level=error msg="ContainerStatus for \"eb21c65d106f60d00842be72d0033f9df69dc71401deac7d10048951dbd940dd\" failed" error="rpc err | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"49c3df5e | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"d21bfec6 | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"451879ce | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"c7d348db | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"65c000bd | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"eb21c65d | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-241 \| Error while processing event ("/sys/fs/cgroup/devices/kubepods.slice/kubepods-besteffort.slice/kubepods-besteffort-pod339f654f_924a_43ab_893 | 1 | logs/node/node-1-241/kubelet-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"e3fe2f0a26e8fd1cabf1078bedfac56f5748ac70cb4f4c326325953584bc1883\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"5d0178801191d711b6c5ac1e63d41c228f4aa830c168ea5cdf10047d9d928140\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"f296267e9234d46d7bbf83d1f0b4fe207940302086682593163e553f9f8f96a9\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"b2926054ac6be908e21a70b587458c9300c2af55e835e3bbedbe966c7e6eef80\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"504e922981dcdd7c23431189569f44c2db1d53adeaf9ef6406b6eae782bccf41\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| time="<ts>" level=error msg="ContainerStatus for \"64b8cb3dd068c9a644cab358f6d4a4bbc4ae3d64eff7b67a7deebdcba26fb82d\" failed" error="rpc err | 1 | logs/node/node-1-62/containerd-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"e3fe2f0a | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"5d017880 | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"f296267e | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"b2926054 | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"504e9229 | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-1-62 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"64b8cb3d | 1 | logs/node/node-1-62/kubelet-24h.log |
| node:node-2-158 \| time="<ts>" level=error msg="get state for 40de41eb634e79045491651463b174121f5bf659de070b31789600b4fa437cf0" error="context deadline exceede | 1 | logs/node/node-2-158/containerd-24h.log |

### 7-4. Raw files the LLM read directly

- `inventory.json`
- `findings-draft.json`
- `summary.json`
- `diff.json`
- `collect-result.json`
- `events.json (summary.json events.reasons 경유)`
- `objects/pods.json`
- `objects/deployments.json`
- `objects/statefulsets.json`
- `objects/nodes.json`
- `objects/persistentvolumes.json`
- `objects/poddisruptionbudgets.policy.json`
- `objects/applications.argoproj.io.json`
- `objects/ingresses.networking.k8s.io.json`
- `objects/services.json`
- `objects/configmaps.json`
- `objects/nodepools.karpenter.sh.json`
- `aws/dlm-lifecycle-policies.json`
- `aws/backup-plans.json`
- `aws/ec2-snapshots-30d.json`
- `aws/ec2-volumes.json`
- `aws/acm-certificates.json`
- `aws/describe-cluster-versions.json`
- `~/.kubegap/snapshots/my-cluster/2026-11-03T11-17-15/findings-draft.json`

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `observability.no-slo.cluster` | warn | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] known issue #15 |
| `observability.no-symptom-alerts.cluster` | warn | critical | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 14. Symptom ratio 0.0. Symptom rules: [] |
| `resilience.n-plus-one.cluster` | warn | critical | Allocatable without the largest node node-1-139 (3.92 cores, 29.8GB): CPU 15.5 cores vs total requests 12.41 (OK), memory 46.6GB vs 47.5GB (OK). Pods on that node 33 (prod 20). Pods that fit on no other node []. Pools short of room: 32 pods limited to … |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | fail | high | 24h 'Unable to schedule pod; no fit' 78 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient memory, <n> node(s) had untolerated taint {workload-type: build}, <n> node(s) had untolerated  |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` | fail | high | 24h 'Unable to schedule pod; no fit' 28 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient memory, <n> node(s) had untolerated taint {workload-type: build}, <n> node(s) had untolerated  |
| `eks.no-backup-policy.cluster` | fail | high | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'stale_backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FailedScheduling` | fail | high | No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked. 194 occurrences total (90 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 41, 42, 45, 45, 0, 0, 0, 3, 0, 12, 0, 0, 15, 15], flat), first … |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 462MB |
| `observability.no-event-retention.cluster` | fail | high | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e: EKS end of standard support 2026-03-23, 227 days past; upstream end of life 2026-02-28 |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | fail | high | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 2 |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.28, 24 h or the pod's life 0.26: throttled through the day |
| `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` | fail | high | kernel log: 0 kills in 24 h on 2 of 2 nodes read. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods. cAdvisor counter 0 |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | fail | high | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (6.2 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
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
| `vpccni.node-ip-exhaustion.node-1-139` | fail | high | node node-1-139 (r8gd.xlarge, pool default): pod IPs 35/56 (0.625), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 20. prefix delegation False |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn | high | 24h 'Unable to schedule pod; no fit' 17 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient memory, <n> node(s) had untolerated taint {workload-type: build}, <n> node(s) had untolerated  |
| `eks.service-quota-near-limit.aws-account` | warn | high | quotas with a usage metric 25/65, at 80% or more [], at 60% or more ['VPCs 0.6'], top operational quotas [['VPCs', 3.0, 5.0, 0.6], ['listener rules per ALB', 47.0, 100.0, 0.47], ['target groups per ALB', 40.0, 100.0, 0.4], ['certificates per ALB', 9.0, 25.0, 0.36], ['NLBs', 2.0, 50.0, 0.04] … |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 115 occurrences total (40 events, trend over 37 snapshots [0, 0, 0, 0, 0, 0, 6, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 6, 10, 10, 10, 0, 0, 0, 5, 4, 49, 0, 0, 9, 9], flat), first 2026-10-08T12:34:17Z last … |
| `events.tracked-warning-reasons.UpdateFailed` | warn | high | Operator reconcile failure (ExternalSecret etc.). 2556 occurrences total (1 events, trend over 37 snapshots [1483, 1486, 1492, 1495, 1496, 1517, 1521, 1535, 1538, 1541, 1546, 1548, 1550, 1551, 1552, 1561, 1564, 1565, 1569, 1570, 1572, 1584, 1593, 1596, 1624, 1632, 1632, 1637, 1638, 1639, 1726 … |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 62 occurrences (2026-11-05T00:24:21Z ~ 2026-11-05T08:11:04Z), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: ['[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:24:21.605206449Z … |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-04T08:48:29Z ~ 2026-11-04T08:48:29Z), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-04T08:48:29.881532186Z … |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.81 |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.79 |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.729 (limit 1536Mi), active series 200359, Prometheus container last terminated OOMKilled True (2026-10-06T12:32:06Z), restarts 1, OOMKilled containers in the monitoring namespace ['loki-stack-0/loki', 'prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7 … |
| `resilience.prod-concentration.node-1-139` | warn | high | Node node-1-139 (pool default, spot) holds prod pods 20/42 (0.48), 15 workloads: ['prod-app-r/app-r', 'prod-app-m/app-m-admin', 'prod-app-m/app-m-api', 'prod-app-m/app-m-backend' … |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn | high | ["pod app-m-frontend-67888bfd9-jpxzw: throttling ratio now 0.24, 24 h or the pod's life 0.23: throttled through the day, below the fail line", "pod app-m-frontend-67888bfd9-ncp94: throttling ratio now 0.00, 24 h or the pod's life 0.22: throttled through the day, below the fail line; no … |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7f6d6dc65b-lnmq4: throttling ratio now 0.12, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | warn | high | ["pod app-m-frontend-6d7ff4dcdb-qfmxq: throttling ratio now 0.23, 24 h or the pod's life 0.24: throttled through the day, below the fail line", "pod app-m-frontend-6d7ff4dcdb-tzwjn: throttling ratio now 0.28, 24 h or the pod's life 0.22: throttled through the day, below the fail line"] |
| `resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7d5fc5c884-hrllj: throttling ratio now 0.15, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` | warn | high | kernel log not read on its node, no node access there. Prometheus: 1 pod ended by OOM in 7 days, 1 restarts in those pods. cAdvisor counter 1 |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | warn | high | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (11.6 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.imds-hop-limit.cluster` | warn | high | Of 8 instances, 8 with IMDS hop limit > 1 or tokens optional: {'hop=2 tokens=required': 8}. Examples [('system_core', 'm5.large', 2, 'required'), ('system_core', 'm5.large', 2, 'required'), ('karpenter-node', 't8i.medium', 2, 'required'), ('karpenter-node', 'm7i-flex.large', 2, 'required')]. … |
| `traffic.db-exposed.nlb/acme-db-shared` | warn | high | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 3307, 3308, 3309, 3310, 3311, 5432, 5433, 6379, 7687], exposure internet-facing, addresses ['nlb-db-shared.elb.us-east-1.amazonaws.com'], sourceRanges None, security group allow-list, at most 4 sources per … |
| `vpccni.node-ip-exhaustion.node-1-241` | warn | high | node node-1-241 (t8i.small, pool system-ondemand): pod IPs 6/9 (0.667), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 11, prod pods 1. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-2-218` | warn | high | node node-2-218 (t8i.medium, pool system-ondemand): pod IPs 13/15 (0.867), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 17, prod pods 1. prefix delegation False |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 12/12 (prod 8) |
| `cost.idle-compute-high.cluster` | fail | medium | Node compute monthly estimate 479.33 USD (on-demand list price, current spot price), of which idle 454.0 USD (0.95), by pool {'nodegroup:system_core-20251217040546303900000001': 172.28, 'default': 105.05, 'system-ondemand': 154.26, 'build-arm64': 47.74}, 24.68 USD per core-month. Spot node share … |
| `cost.request-waste.cluster` | fail | medium | CPU request total 8.68 cores -> KRR recommendation 2.09 cores, reducible 6.59 cores ~ 162.65 USD/month |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-1a', 'gp3-1c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-1a', 'gp3-1c'] |
| `ecr.scan-disabled.ecr/registry/<account>` | fail | medium | registry scanning BASIC (rules 0), repositories with scanOnPush off 39/43 (used by prod 25: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod']…), scanned images … |
| `eks.addon-outdated.aws-ebs-csi-driver` | fail | medium | installed v1.37.0-eksbuild.1, latest available v1.67.2-eksbuild.1, default v1.67.2-eksbuild.1 |
| `eks.addon-outdated.vpc-cni` | fail | medium | installed v1.19.0-eksbuild.1, latest available v1.23.2-eksbuild.8, default v1.22.4-eksbuild.10 |
| `eks.extended-support.cluster` | fail | medium | version 1.32, supportType EXTENDED, status EXTENDED_SUPPORT, end of standard support 2026-03-23T09:00:00+09:00, end of extended support 2027-03-23T09:00:00+09:00 |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eks.nodegroup-ami-old.nodegroups` | fail | medium | node groups 1, max AMI age 331 days, over 90 days ['system_core-20251217040546303900000001 331d'], over 180 days ['system_core-20251217040546303900000001'], health issues [] |
| `eks.ssm-unregistered.node-1-117` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eks.ssm-unregistered.node-2-60` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 30033 / errors 2556 (ratio 0.0784), sync failures 2556/68745, reconcile errors 2556, ExternalSecrets not Ready ['database/externalsecret/mysql-app-n-secret'] (oldest refresh 7755.3 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2603, {'101': 4, '200': 2267, '400': 6, '429': 326}), ('Prometheus(prometheus)', 1534, {'200': 1349, '301': 185}), ('VictoriaMetrics_onprem(prometheus)', 141, {'200': 141})], error rate 1% or more ['Loki(loki)'] (max 0.1252), Grafana … |
| `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility` | fail | medium | Amazon Linux 2 compatibility (UPGRADE_READINESS, k8s 1.33): ERROR — Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ |
| `hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.polaris-reliability-danger.prod-app-l-backend/deployment/tts-proxy` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing']. Security-category danger ['dangerousCapabilities', 'privilegeEscalationAllowed' … |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | fail | medium | RSS 462MiB / limit 512Mi = 0.901, in-memory streams 54, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 57.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 57.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodNotReady` | fail | medium | 7d firing samples 47192 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 139 pods Running for over 1h, 56 are absent from Loki pod labels (ratio 0.403). Nodes with every pod missing: ['node-2-158']. By namespace: {'kube-system': 21, 'monitoring': 14, 'prod-app-l-backend': 3, 'argocd': 2, 'dev-app-o': 2, 'keda': 2, 'middleware' … |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret` | fail | medium | Ready=False (SecretSyncedError) for 7760.9 hours: could not get secret data from provider |
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
| `resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller` | fail | medium | memory request under by 373 MB, CPU request over by 0.143 cores: CPU request 0.2 → 0.057 cores, CPU limit 0.5 → none, memory request 384 → 757 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.dev-app-o/statefulset/app-o-backend-mysql:mysql` | fail | medium | memory request under by 355 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 867 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | fail | medium | memory request under by 281 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 793 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/loki-stack:loki` | fail | medium | memory request under by 273 MB: CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 529 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 839 MB: CPU request 0.2 → 0.137 cores, CPU limit 0.5 → none, memory request 800 → 1639 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle` | fail | medium | CPU request over by 0.29 cores, memory request over by 319 MB: CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 193 MB, memory limit 1024 → 193 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai` | fail | medium | memory request under by 351 MB: CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 607 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-backend:backend` | fail | medium | memory request under by 298 MB: CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 426 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-frontend:frontend` | fail | medium | memory request under by 296 MB: CPU request 0.01 → 0.032 cores, CPU limit 0.2 → none, memory request 128 → 424 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/statefulset/app-m-backend-mysql:mysql` | fail | medium | memory request under by 395 MB, CPU request over by 0.188 cores: CPU request 0.2 → 0.012 cores, CPU limit 1.0 → none, memory request 768 → 1163 MB, memory limit 1536 → 1163 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-ai:ai` | fail | medium | memory request over by 1075 MB: CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 973 MB, memory limit 4096 → 973 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-embedding-server:embedding` | fail | medium | memory request under by 2634 MB, CPU request over by 0.341 cores: CPU request 0.5 → 0.159 cores, CPU limit 2.0 → none, memory request 4096 → 6730 MB, memory limit 6144 → 6730 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-file-worker:file-worker` | fail | medium | CPU request over by 0.872 cores, memory request over by 337 MB: CPU request 1.0 → 0.128 cores, CPU limit 2.0 → none, memory request 2048 → 1711 MB, memory limit 4096 → 1711 MB. KRR severity CRITICAL (CPU req CRITICAL, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker` | fail | medium | CPU request over by 0.458 cores, memory request over by 670 MB: CPU request 1.0 → 0.542 cores, CPU limit 2.0 → none, memory request 2048 → 1378 MB, memory limit 6144 → 1378 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/statefulset/app-l-neo4j:neo4j` | fail | medium | CPU request over by 0.49 cores, memory request over by 2417 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1679 MB, memory limit 5120 → 1679 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-backend:backend` | fail | medium | CPU request over by 0.359 cores: CPU request 0.5 → 0.141 cores, CPU limit 2.0 → none, memory request 1024 → 866 MB, memory limit 2048 → 866 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-4248d:runner` | fail | medium | pod self-hosted-arm64-8msc5-runner-4248d: request is 104% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-8445d87f5-dwqrx: request is 58% of the median node allocatable', 'pod app-l-embedding-server-8445d87f5-jfv9l: request is 58% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | medium | pod app-l-neo4j-0: request is 58% of the median node allocatable |
| `resources.no-memory-limit.prod-app-l-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-request-usage-gap.node-1-117` | fail | medium | CPU requests/allocatable 0.96, usage/allocatable 7d p95 0.09 (5m instant 0.09) |
| `resources.node-request-usage-gap.node-1-139` | fail | medium | CPU requests/allocatable 0.92, usage/allocatable 7d p95 0.05 (5m instant 0.05) |
| `resources.node-request-usage-gap.node-1-62` | fail | medium | CPU requests/allocatable 0.87, usage/allocatable 7d p95 0.06 (5m instant 0.04) |
| `resources.node-request-usage-gap.node-2-60` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.05) |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node node-1-139 (r8gd.xlarge spot): age 1021.9h, 301.9h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 21337}. do-not-disrupt pods on this node 1: prod-app-m/app-m-admin-57f5fcc58d-khsh5 |
| `security.externalsecret-not-ready.database/mysql-app-n-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.networkpolicy-coverage.cluster` | fail | medium | 18 of 21 user namespaces have no NetworkPolicy, of which production ['prod-app-r', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-n']; with: ['prod-app-q', 'prod-app-p', 'app-s-prod'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 79. Security danger workloads 74 (prod 28): per check {'dangerousCapabilities': 2, 'hostNetworkSet': 2, 'privilegeEscalationAllowed': 59, 'runAsPrivileged': 3, 'runAsRootAllowed': 58, 'hostPIDSet': 1, 'clusterrolebindingClusterAdmin': 2, 'clusterrolebindingPodExecAttach': 4 … |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days 12 {'pre-delete backup of orphan PVC prod-app-m': 4, 'pre-delete backup of orphan PVC app-s-prod': 2, 'pre-delete backup of orphan PVC prod-app-o': 2, 'pre-delete backup of orphan PVC dev-app-n' … |
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
| `tenancy.prod-without-quota.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 0.026 cores (cluster share 0.021), memory p95 9.92GB, 7d max/median 352.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-p` | fail | medium | prod-app-p (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.006 cores (cluster share 0.005), memory p95 0.74GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-n` | fail | medium | prod-app-n (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.024 cores (cluster share 0.019), memory p95 1.0GB, 7d max/median 4.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.app-s-prod` | fail | medium | app-s-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 0.023 cores (cluster share 0.018), memory p95 0.5GB, 7d max/median 2.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.tenant-without-limitrange.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 0.026 cores, memory p95 9.92GB |
| `traffic.alb-elb-5xx.k8s-shared-alb` | fail | medium | ALB k8s-shared-alb (internet-facing): 24h requests 204733.0, ELB 5xx 168.0, target 5xx 771.0, rejected connections 0, idle timeout 300s, target groups 40 |
| `traffic.ingress-p95-latency.prod-app-m/app-m-api` | fail | medium | ['canary-api-v1.example-b.ai', 'api.v1.example-b.ai']: p95 request-weighted 15.0916s, hourly average 17.0241s, 1h max 53.064s, latest hour with requests 16.5933s on 3.0 requests at 2026-11-05T07:20, 1286.0 requests/24h (source alb-cloudwatch) |
| `traffic.shared-alb-group.alb-group/acme-prod-lb` | fail | medium | ALB group acme-prod-lb: 40 ingresses, 47 hosts, 15 namespaces ['argocd', 'dev-app-m', 'dev-app-o', 'dev-app-n', 'dev-app-t', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p' … |
| `vpccni.prefix-delegation-off.cluster` | fail | medium | ENABLE_PREFIX_DELEGATION false, nitro nodes 8/8. nodes above 50% IP usage ['node-2-218', 'node-1-241', 'node-2-60', 'node-1-139' … |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `albctl.tgb-stale-or-orphan.cluster` | warn | medium | TargetGroupBindings 51 (targetType {'ip': 51}), generation lagging [], Service missing [], hand-made TGBs 9, target groups without a binding (traffic section) 1 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.my-cluster |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version … |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.547s |
| `controlplane.apiserver-latency.PATCH` | warn | medium | PATCH p99 0.699s |
| `controlplane.controller-error-repeat.type.go` | warn | medium | 24h W lines 80431 times (type.go). Samples: summary.controlplane.controller_manager.top_errors |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.511, queries per second 78.46, NXDOMAIN share of queries forwarded upstream 0.475 (upstreams ['<ip>:53']), pods with default ndots (5) 145, autopath False, cache hit ratio 0.9095 |
| `ecr.dockerhub-dependency.ecr/registry/<account>` | warn | medium | registry distribution of container images {'<account>.dkr.ecr.us-east-1.amazonaws.com': 70, '<account>.dkr.ecr.us-east-1.amazonaws.com': 55, 'docker.io': 33, 'quay.io': 24, 'ghcr.io': 11, 'public.ecr.aws': 8, 'registry.k8s.io': 3}, docker.io images 20 (e.g. ['alpine/socat:1.8.0.0' … |
| `eks.addon-outdated.coredns` | warn | medium | installed v1.11.3-eksbuild.1, latest available v1.11.4-eksbuild.97, default v1.11.4-eksbuild.97 |
| `eks.addon-outdated.kube-proxy` | warn | medium | installed v1.32.0-eksbuild.2, latest available v1.32.13-eksbuild.67, default v1.32.13-eksbuild.67 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.acme.ai/role` | warn | medium | Label acme.ai/role: 33 workloads (production 8) depend on it via nodeSelector/affinity, present on 5/8 nodes — e.g. argocd/deployment/argocd-applicationset-controller, argocd/deployment/argocd-dex-server, argocd/deployment/argocd-notifications-controller |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 38 workloads (production 25) depend on it via nodeSelector/affinity, present on 3/8 nodes — e.g. dev-app-m/deployment/app-m-admin, dev-app-m/deployment/app-m-api, dev-app-m/deployment/app-m-backend |
| `hygiene.polaris-reliability-danger.arc-runners/autoscalingrunnerset/self-hosted-arm64` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsPrivileged' … |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-cool-down` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-warm-up` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.middleware/deployment/redis-insight` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed' … |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 31.3s (8485 pods), node termination average 15.1s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-o/scaledobject/app-o-ai-kafka-lag', 'prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.containerd.shim-error` | warn | medium | 33 occurrences (2026-11-04T09:27:46Z ~ 2026-11-05T07:20:08Z), thresholds warn 5/fail 50. Files: ['logs/node/node-1-139/containerd-24h.log', 'logs/node/node-1-62/containerd-24h.log' … |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-05T03:40:39Z ~ 2026-11-05T08:21:00Z), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:39.431880726Z W1105 03:40:39.431762       1 … |
| `logs.signatures.kubelet.image-gc-failed` | warn | medium | 2 occurrences (2026-11-04T10:06:59Z ~ 2026-11-05T05:52:02Z), thresholds warn 1/fail 10. Files: ['logs/node/node-1-139/kubelet-24h.log']. Samples: ['2026-11-04T10:06:59+0000 node-1-139 kubelet[1593]: E1104 10:06:59.922962    1593 … |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 42 occurrences (2026-11-04T09:02:26Z ~ 2026-11-05T07:55:11Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-04T09:02:26.073535127Z E1104 09:02:26.073405       1 scraper.go:149] … |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 1 5xx out of 5968052 requests since start (by route {'loki_api_v1_series': 1}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 10130, rejected {} |
| `node.kernel-net-mem-pressure.node-2-135` | warn | medium | kernel log (since boot (dmesg; journald does not hold 24 hours)) BUG/Oops/Call Trace 0, network pressure (TCP memory, SYN flooding, ARP table) 1, memory pressure (page allocation failure) 0, unstable clocksource 0. Samples: ['[Sat Oct 10 05:24:47 2026] TCP: request_sock_TCP: Possible SYN flooding … |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerFailedReload', 'AlertmanagerMembersInconsistent', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown' … |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | dev-app-m/statefulset/app-m-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | dev-app-o/statefulset/app-o-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | warn | medium | dev-app-n/statefulset/app-n-backend-dev-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | dev-app-t/statefulset/app-t-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-t/statefulset/app-t-postgres:postgres` | warn | medium | dev-app-t/statefulset/app-t-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` | warn | medium | monitoring/statefulset/loki-stack container loki: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 106, 'system-cluster-critical': 9, 'system-node-critical': 24}, prod pods without a class 42 of 42, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
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
| `resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 257 MB, memory limit 1024 → 257 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-m/deployment/app-m-frontend:frontend` | warn | medium | memory request under by 85 MB: CPU HPA detected, memory request 128 → 213 MB. KRR severity GOOD (CPU req UNKNOWN, CPU limit UNKNOWN, memory req GOOD, memory limit GOOD). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | memory request under by 113 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 625 MB, memory limit 1024 → 625 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-ai:ai` | warn | medium | memory request over by 458 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 566 MB, memory limit 2048 → 566 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 359 MB: CPU HPA detected, memory request 512 → 153 MB, memory limit 8192 → 153 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | CPU request over by 0.19 cores, memory request over by 341 MB: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.karpenter/deployment/karpenter:controller` | warn | medium | memory request under by 152 MB, CPU request over by 0.18 cores: CPU request 0.2 → 0.02 cores, CPU limit 0.5 → none, memory request 256 → 408 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka` | warn | medium | CPU request over by 0.13 cores: CPU request 0.2 → 0.07 cores, CPU limit 0.5 → none, memory request 1536 → 1466 MB, memory limit 2048 → 1466 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail` | warn | medium | memory request under by 144 MB: CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 272 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-backend:backend` | warn | medium | memory request under by 189 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 381 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 396 MB: CPU request 0.1 → 0.011 cores, CPU limit 2.0 → none, memory request 512 → 116 MB, memory limit 2048 → 116 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-backend:backend` | warn | medium | memory request over by 410 MB: CPU HPA detected, memory request 1024 → 614 MB, memory limit 2048 → 614 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-pg-proxy:forwarder` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-n/deployment/app-n-backend:backend` | warn | medium | memory request under by 89 MB: CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 217 MB, memory limit 512 → 217 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | warn | medium | CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 811 MB, memory limit 1536 → 811 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.node-memory-request-usage-gap.node-1-241` | warn | medium | memory requests/allocatable 0.66, working set/allocatable 7d p95 0.33 (instant 0.43) |
| `resources.node-memory-request-usage-gap.node-2-135` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.42 (instant 0.48) |
| `resources.node-request-usage-gap.node-2-135` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.05 (5m instant 0.04) |
| `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` | warn | medium | 42 desired changes over 7 days |
| `scaling.hpa-flapping.prod-app-l-backend/hpa/keda-hpa-app-l-file-worker` | warn | medium | 48 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']. Share of containers allowing root 0.62 (28 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 86/91, of which 29 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-r/deployment/app-r', 'prod-app-q/deployment/app-q-ai', 'prod-app-q/deployment/app-q-backend' … |
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
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend` | warn | medium | ['canary-api.example-b.ai', 'api.example-b.ai']: 24h 5xx 663.0 of 94891.0 requests = 0.70% (source alb-cloudwatch), p95 max 4.4754s |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend` | warn | medium | ['canary.example-b.ai', 'www.example-b.ai']: 24h 5xx 80.0 of 54991.0 requests = 0.14% (source alb-cloudwatch), p95 max 0.5922s |
| `traffic.ingress-5xx-ratio.prod-app-n/app-n-frontend` | warn | medium | ['example-c.ai', 'www.example-c.ai']: 24h 5xx 26.0 of 9938.0 requests = 0.26% (source alb-cloudwatch), p95 max 2.398s |
| `traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana` | warn | medium | ['monitor.my-cluster']: p95 request-weighted 2.8008s, hourly average 1.1781s, 1h max 5.7888s, latest hour with requests 0.0232s on 6.0 requests at 2026-11-05T03:20, 4 hours before the newest hour, no requests since, 54.0 requests/24h (under 100 requests a day: warn only) (source alb-cloudwatch) |
| `traffic.ingress-p95-latency.prod-app-q/app-q-ai` | warn | medium | ['app-q-ai.my-cluster']: p95 request-weighted 2.2443s, hourly average 2.221s, 1h max 2.6742s, latest hour with requests 2.1485s on 14.0 requests at 2026-11-05T07:20, 21.0 requests/24h (under 100 requests a day: warn only) (source alb-cloudwatch) |
| `traffic.pod-not-ready.arc-runners/self-hosted-arm64-8msc5-runner` | warn | medium | 24h minimum Ready ratio 0.9888 (pod self-hosted-arm64-8msc5-runner-4248d, about 16 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `vpccni.ec2-api-errors.node-1-62` | warn | medium | node node-1-62: EC2 API failures 20 (by API {'CreateNetworkInterface': 8, 'DeleteNetworkInterface': 12}), force-removed ENIs 0 / IPs 0 (cumulative since ipamd start, IMDS 404 excluded) |
| `vpccni.ec2-api-errors.node-2-158` | warn | medium | node node-2-158: EC2 API failures 11 (by API {'CreateNetworkInterface': 11}), force-removed ENIs 0 / IPs 0 (cumulative since ipamd start, IMDS 404 excluded) |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 111 (0.009), without one in prod 33. emptyDirs without sizeLimit 21 (prod: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-l-backend/deployment/app-l-embedding-server', 'prod-app-l-backend/deployment/tts-proxy' … |
| `hygiene.old-replicasets.cluster` | fail | low | Of 418 ReplicaSets, 353 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 61, '3': 6} |
| `node.cgroup-v1.node-1-139` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-241` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-1-62` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-135` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-2-158` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-218` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.os-not-collected.node-1-117` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `node.os-not-collected.node-2-60` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend` | fail | low | HPA prod-app-l-backend/app-l-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 20.1 days ago |
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
| `controlplane.apiserver-slow-traces.cluster` | warn | low | 24h Traces (requests over 500ms) 165: [{'op': 'List', 'count': 153}, {'op': 'Call conversion webhook', 'count': 8}, {'op': 'Update', 'count': 3}, {'op': 'Patch', 'count': 1}] |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.5, cluster IPv6 False, queries per second 78.46. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-node.node-2-158` | warn | low | Node node-2-158 (c6gn.xlarge, pool build-arm64): CPU p95 0.02329421451616407, memory p95 0.1834216996108511, 47.74 USD/month |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | controller EC2 API request series 0, driver 1.37.0 (add-on v1.37.0-eksbuild.1). When enabled, shows EC2 API errors {} / throttles None |
| `ecr.no-lifecycle-policy.ecr/registry/<account>` | warn | low | repositories without a lifecycle policy ['app-n', 'bitnami/kafka', 'ecr-app-s-postgresql-pgvector', 'bitnami/mysql'] (total 10.9GiB), overall 43 repositories, 887 images, 453.6GiB ≈ 48.7 USD/month, untagged images 253 (excluding 176 attestations) |
| `ecr.no-replication.ecr/registry/<account>` | warn | low | replication rules 0, repositories used by prod 27, total 453.6GiB |
| `ecr.tag-mutable-prod.ecr/registry/<account>` | warn | low | MUTABLE repositories 42/43, used by prod 26: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod', 'ecr-app-s-postgresql-pgvector' … |
| `ecr.untagged-images.ecr/registry/<account>` | warn | low | untagged images 253/887 (excluding 176 BuildKit attestation manifests), repositories 43 |
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
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 1248 packets (sum over nodes), services with externalTrafficPolicy Local 0, Services with a Local traffic policy and no endpoint on the node (max over nodes) 0 |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alerts-never-fired.cluster` | warn | low | 128 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 36 of 40 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-m', 'app-m-admin'), ('dev-app-m', 'app-m-api'), ('dev-app-m', 'app-m-backend'), ('dev-app-m', 'app-m-frontend'), ('dev-app-o', 'app-o-admin')]) … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"'])], receivers ['null', 'slack-sre', 'slack-system'], default receiver … |
| `observability.unclassified-errors.cluster` | warn | low | 56 unclassified error lines (23448 lines scanned, 33 files). Top: [('grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 unam', 12), ('node:node-2-158 \| time="<ts>" level=error msg="failed to load cni', 2) … |
| `observability.unstructured-logs.argocd` | warn | low | Of 17411 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-n` | warn | low | Of 59543 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.monitoring` | warn | low | Of 11127 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.app-s-prod` | warn | low | Of 946936 lines in 1h, 0 parse as JSON (0.0) |
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
| `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | warn | low | pod app-l-neo4j-0: 7d memory working set p95 977 MB / request 4096 MB = 0.24; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | low | pod app-s-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.22; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-backend` | warn | low | HPA prod-app-l-backend/app-l-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-frontend` | warn | low | HPA prod-app-l-backend/app-l-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin` | warn | low | HPA dev-app-m/app-m-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 168.8 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api` | warn | low | HPA dev-app-m/app-m-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 198.5 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend` | warn | low | HPA dev-app-m/app-m-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 16% / target 70%, metrics ['cpu'], last scale 69.3 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin` | warn | low | HPA dev-app-o/app-o-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 6% / target 70%, metrics ['cpu'], last scale 58.3 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend` | warn | low | HPA dev-app-o/app-o-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 20.3 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend` | warn | low | HPA dev-app-o/app-o-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 28% / target 70%, metrics ['cpu'], last scale 20.3 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend` | warn | low | HPA dev-app-n/app-n-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 38.8 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend` | warn | low | HPA dev-app-n/app-n-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 13% / target 70%, metrics ['cpu'], last scale 42.8 days ago |
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
| `vpccni.metrics-unreadable.cluster` | warn | low | 2 of 8 nodes without readable ipamd metrics (localhost:61678): ['node-1-117', 'node-2-60'] |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |
| `hygiene.no-progressive-delivery.cluster` | fail | info | No progressive-delivery component (Argo Rollouts, Flagger). All deployments are rolling updates (replace everything) -- ALB weighted target groups are not used either |

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
 "by_class": {
  "app-cause": 5,
  "app": 14,
  "cause": 138
 },
 "symptom_rules": [],
 "symptom_ratio": 0.0
}
```

</details>
<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "prod_pods_on_largest_node": 20,
 "ok": false,
 "pods_on_largest_node": 33,
 "requests_cpu_total": 12.41,
 "pools_short": [
  {
   "eligible_nodes": [
    "node-1-62"
   ],
   "pods": 32,
   "needed_cpu": 3.3,
   "free_cpu": 0.26,
   "needed_memory_gb": 18.62,
   "free_memory_gb": 7.79
  }
 ],
 "cannot_fit_elsewhere": [],
 "tight": true,
 "memory_ok": true,
 "cpu_ok": true,
 "karpenter": true,
 "largest_node_memory_gb": 29.8,
 "largest_node": "node-1-139",
 "available": true,
 "allocatable_memory_gb_without_largest": 46.6,
 "autoscaler_name": "karpenter",
 "autoscaler": true,
 "requests_memory_gb_total": 47.5,
 "largest_node_cpu": 3.92,
 "allocatable_cpu_without_largest": 15.5
}
```

</details>
<details><summary><code>controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker</code></summary>

```json
{
 "workload": "prod-app-l-backend/app-l-file-worker",
 "count": 78
}
```

</details>
<details><summary><code>controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker</code></summary>

```json
{
 "workload": "prod-app-l-backend/app-l-graph-worker",
 "count": 28
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.FailedScheduling</code></summary>

```json
{
 "reason": "FailedScheduling",
 "trend": "flat",
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
 "type": "Warning",
 "meaning": "No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked",
 "events": 90,
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
 "first": "2026-10-25T03:33:08Z",
 "severity_hint": "high",
 "last": "2026-11-05T07:54:59Z",
 "occurrences": 194
}
```

</details>
<details><summary><code>karpenter.ec2nodeclass-al2.cluster</code></summary>

```json
{
 "classes_al2": [
  "default"
 ],
 "ec2nodeclasses": 1,
 "classes_ami_unpinned": [
  "default"
 ],
 "ami_families": [
  "AL2"
 ]
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.OOMKill</code></summary>

```json
{
 "mode": "OOMKill",
 "symptom": "pods die and requests fail or slow down",
 "importance": "critical"
}
```

</details>
<details><summary><code>observability.loki-oomkilled.cluster</code></summary>

```json
{
 "self_metrics": {
  "discarded_samples_since_start": {},
  "streams_in_memory": 54,
  "panics": 0,
  "lines_received_since_start": 253938496,
  "requests_5xx_since_start": 4,
  "rss_mb": 462,
  "process_uptime_h": 272.0
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
 "k8s_max_supported": "1.30",
 "compat_row": "0.37",
 "k8s_minor": "1.32",
 "version": "0.37.0",
 "present": true,
 "version_note": null,
 "k8s_min_supported": "1.23",
 "k8s_supported": false
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-r/deployment/app-r</code></summary>

```json
{
 "topology_spread": [],
 "single_eligible_node": false,
 "nodes": {
  "node-1-139": 2
 },
 "zones": {
  "us-east-1a": 2
 },
 "replicas": 2,
 "eligible_nodes": 2,
 "prod": true,
 "workload": "prod-app-r/deployment/app-r",
 "running": 2,
 "all_same_node": true,
 "anti_affinity": null
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-o/deployment/app-o-ai</code></summary>

```json
{
 "topology_spread": [],
 "single_eligible_node": false,
 "nodes": {
  "node-1-139": 3
 },
 "zones": {
  "us-east-1a": 3
 },
 "replicas": 3,
 "eligible_nodes": 2,
 "prod": true,
 "workload": "prod-app-o/deployment/app-o-ai",
 "running": 3,
 "all_same_node": true,
 "anti_affinity": null
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-o/deployment/app-o-backend</code></summary>

```json
{
 "topology_spread": [],
 "single_eligible_node": false,
 "nodes": {
  "node-1-139": 2
 },
 "zones": {
  "us-east-1a": 2
 },
 "replicas": 2,
 "eligible_nodes": 2,
 "prod": true,
 "workload": "prod-app-o/deployment/app-o-backend",
 "running": 2,
 "all_same_node": true,
 "anti_affinity": null
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "topology_spread": [],
 "single_eligible_node": false,
 "nodes": {
  "node-1-139": 2
 },
 "zones": {
  "us-east-1a": 2
 },
 "replicas": 2,
 "eligible_nodes": 2,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/app-l-frontend",
 "running": 2,
 "all_same_node": true,
 "anti_affinity": "preferred"
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
  "cpu_throttle_ratio_24h": 0.2640261934938741,
  "cpu_throttle_ratio_5m": 0.2770034843205575
 }
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai</code></summary>

```json
{
 "last_kill": null,
 "kernel_log_read": true,
 "kernel_kills_24h": 0,
 "target": "prod-app-q/deploy/app-q-ai:ai",
 "kernel_nodes_old_script": 0,
 "pods_oomkilled": 3,
 "pods_replaced": 3,
 "restarts_of_those_pods": 13,
 "kernel_nodes_read": 2,
 "kernel_nodes_total": 2,
 "cadvisor_oom_events_7d": 0
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
 "enforcement": "aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints",
 "enforced": false,
 "policies_but_not_enforced": true,
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
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "root_allowed_containers": [
  "tailscale",
  "forwarder"
 ],
 "severe": true,
 "flags": [
  "hostPath ['dev-net-tun']",
  "capabilities [\"tailscale:['NET_ADMIN']\"]"
 ],
 "system": false
}
```

</details>
<details><summary><code>storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0</code></summary>

```json
{
 "storage_class": "gp3",
 "workloads": [
  "statefulset/app-t-mysql"
 ],
 "days_to_full": null,
 "target": "dev-app-t/data-app-t-mysql-0",
 "growth_gb_per_day": 0.0,
 "used_ratio": 0.902,
 "capacity_gb": 9.7,
 "metrics": true,
 "inode_ratio": 0.0,
 "host_fs": false
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend</code></summary>

```json
{
 "unhealthy_max_24h": 1.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "name": "k8s-app-svc-133751726c",
 "targets_healthy": 0,
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "target": "dev-app-n/app-n-frontend",
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.dev-app-t/app-t-backend</code></summary>

```json
{
 "unhealthy_max_24h": 1.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-t-backend"
 ],
 "name": "k8s-app-svc-b347218b4f",
 "targets_healthy": 0,
 "targets_total": 1,
 "port": 8000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 1
 },
 "target": "dev-app-t/app-t-backend",
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 8000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-q/app-q-backend</code></summary>

```json
{
 "unhealthy_max_24h": 1.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-q-backend"
 ],
 "name": "k8s-app-svc-bb495c72c8",
 "targets_healthy": 0,
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 1
 },
 "target": "prod-app-q/app-q-backend",
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend</code></summary>

```json
{
 "unhealthy_max_24h": 1.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-o-frontend"
 ],
 "name": "k8s-app-svc-032c25d752",
 "targets_healthy": 0,
 "targets_total": 1,
 "port": 3003,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "target": "prod-app-o/app-o-frontend",
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3003,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend</code></summary>

```json
{
 "unhealthy_max_24h": 2.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-l-backend"
 ],
 "name": "k8s-app-svc-8c88bb317a",
 "targets_healthy": 0,
 "targets_total": 2,
 "port": 8000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 2
 },
 "target": "prod-app-l-backend/app-l-backend",
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
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend</code></summary>

```json
{
 "unhealthy_max_24h": 1.0,
 "lb_type": "application",
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
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "name": "k8s-app-svc-36f816b829",
 "targets_healthy": 0,
 "targets_total": 1,
 "port": 3000,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "target": "prod-app-n/app-n-frontend",
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ]
}
```

</details>
<details><summary><code>traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external</code></summary>

```json
{
 "ports": [
  9094,
  443
 ],
 "source_ranges": null,
 "open_ports": [
  9094
 ],
 "sg_exposure": "open",
 "hosts": [
  "k8s-app-svc-nlb.elb.us-east-1.amazonaws.com"
 ],
 "type": "loadbalancer",
 "name": "kafka-controller-0-external",
 "note": "DB port open to the internet by the security group",
 "scheme": "internet-facing",
 "namespace": "middleware",
 "allowed_sources": {
  "9094": 1
 },
 "target": "loadbalancer/middleware/kafka-controller-0-external"
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-1-139</code></summary>

```json
{
 "ip_usage_ratio": 0.625,
 "eni_at_max": true,
 "node": "node-1-139",
 "metrics_available": true,
 "instance_type": "r8gd.xlarge",
 "ip_max": 56,
 "ip_used": 35,
 "prefix_delegation": false,
 "no_available_ip_events": 4,
 "metrics": {
  "available": true,
  "assigned": 35,
  "total": 56,
  "eni_allocated": 4,
  "eni_max": 4,
  "ip_max": 56,
  "prefixes": 0,
  "no_available_ip_events": 4,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-0123456789abcdef0": 3,
   "eni-0123456789abcdef0": 8,
   "eni-0123456789abcdef0": 11,
   "eni-0123456789abcdef0": 13
  }
 },
 "prod_pods": 20,
 "pool": "default",
 "max_pods": 58
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
<details><summary><code>controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner</code></summary>

```json
{
 "workload": "arc-runners/self-hosted-arm64-8msc5-runner",
 "count": 17
}
```

</details>
<details><summary><code>eks.service-quota-near-limit.aws-account</code></summary>

```json
{
 "with_usage": 25,
 "near_limit": [],
 "available": true,
 "quotas": 65,
 "watched_top": [
  [
   "VPCs",
   3.0,
   5.0,
   0.6
  ],
  [
   "listener rules per ALB",
   47.0,
   100.0,
   0.47
  ],
  [
   "target groups per ALB",
   40.0,
   100.0,
   0.4
  ],
  [
   "certificates per ALB",
   9.0,
   25.0,
   0.36
  ],
  [
   "NLBs",
   2.0,
   50.0,
   0.04
  ],
  [
   "ALBs",
   1.0,
   50.0,
   0.02
  ],
  [
   "target groups",
   54.0,
   3000.0,
   0.018
  ],
  [
   "spot standard instance vCPU",
   18.0,
   1152.0,
   0.016
  ],
  [
   "on-demand standard instance vCPU",
   12.0,
   1152.0,
   0.01
  ]
 ],
 "over_60": [
  "VPCs 0.6"
 ]
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.Unhealthy</code></summary>

```json
{
 "reason": "Unhealthy",
 "trend": "flat",
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
 "type": "Warning",
 "meaning": "Probe failure. Readiness removes it from traffic, liveness restarts it",
 "events": 40,
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
 "first": "2026-10-08T12:34:17Z",
 "severity_hint": "medium",
 "last": "2026-11-05T08:08:48Z",
 "occurrences": 115
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.UpdateFailed</code></summary>

```json
{
 "reason": "UpdateFailed",
 "trend": "up",
 "objects_top": [
  {
   "object": "ExternalSecret/database/mysql-app-n-secret",
   "occurrences": 2556
  }
 ],
 "type": "Warning",
 "meaning": "Operator reconcile failure (ExternalSecret etc.)",
 "events": 1,
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
 "first": "2026-10-08T12:31:38Z",
 "severity_hint": "medium",
 "last": "2026-11-05T08:11:04Z",
 "occurrences": 2556
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
 "classes_imds_hop_gt1": [
  "default"
 ],
 "root_volume_gb": {
  "default": 50.0
 }
}
```

</details>
<details><summary><code>logs.signatures.external-secrets.provider-error</code></summary>

```json
{
 "count": 62,
 "first": "2026-11-05T00:24:21Z",
 "last": "2026-11-05T08:11:04Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/external-secrets/external-secrets_external-secrets.log": 62
 },
 "samples": [
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:24:21.605206449Z {\"level\":\"error\",\"ts\":1793838261.6050858,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:24:21.617120924Z {\"level\":\"error\",\"ts\":1793838261.6170242,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:41:01.715705224Z {\"level\":\"error\",\"ts\":1793839261.715579,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"m",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:41:01.741177989Z {\"level\":\"error\",\"ts\":1793839261.7410848,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-05T00:57:41.893894746Z {\"level\":\"error\",\"ts\":1793840261.893757,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"m"
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
 "value": 0.80801887127276
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
 "value": 0.7869968284556519
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.Scheduling failure</code></summary>

```json
{
 "mode": "Scheduling failure",
 "symptom": "new pods do not start",
 "importance": "high"
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.VPC CNI IP exhaustion</code></summary>

```json
{
 "mode": "VPC CNI IP exhaustion",
 "symptom": "pods Pending without network",
 "importance": "high"
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
 "rss_vs_limit": 0.729,
 "restarts": 1,
 "oomkilled_at": "2026-10-06T12:32:06Z",
 "present": true,
 "oomkilled_last": true,
 "head_series": 200359,
 "monitoring_restarts_7d": {},
 "memory_limit": "1536Mi",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.prod-concentration.node-1-139</code></summary>

```json
{
 "prod_total": 42,
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
 "node": "node-1-139",
 "share": 0.48,
 "nodes_total": 8,
 "autoscaler": true,
 "prod_pods": 20,
 "pool": "default",
 "workload_count": 15,
 "capacity_type": "spot"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller</code></summary>

```json
{
 "node_rebooted_at": null,
 "waiting": null,
 "pod": "argocd-application-controller-0",
 "restarts": 42,
 "unhealthy_events": 0,
 "last_reason": "OOMKilled",
 "container": "application-controller",
 "namespace": "argocd",
 "exit_code": 137,
 "crashloop": false,
 "last_finished": "2026-10-30T09:00:04Z",
 "cause": "OOM (memory limit)",
 "rebooted": false
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
   "cpu_throttle_ratio_24h": 0.23332211986336818,
   "cpu_throttle_ratio_5m": 0.23552123552123552
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
  "cpu_throttle_ratio_24h": 0.11530619337797447,
  "cpu_throttle_ratio_5m": 0.11895910780669144
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
   "cpu_throttle_ratio_24h": 0.24084583323521794,
   "cpu_throttle_ratio_5m": 0.228643216080402
  }
 },
 {
  "labels": {
   "namespace": "prod-app-m",
   "pod": "app-m-frontend-6d7ff4dcdb-tzwjn",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.22168914437320364,
   "cpu_throttle_ratio_5m": 0.27525252525252525
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
  "cpu_throttle_ratio_24h": 0.11805839814435803,
  "cpu_throttle_ratio_5m": 0.15217391304347827
 }
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller</code></summary>

```json
{
 "kernel_log_read": false,
 "kernel_kills_24h": 0,
 "target": "argocd/sts/argocd-application-controller:application-controller",
 "kernel_nodes_old_script": 0,
 "pods_oomkilled": 1,
 "pods_replaced": 0,
 "restarts_of_those_pods": 1,
 "kernel_nodes_total": 1,
 "kernel_any_node_read": true,
 "cadvisor_oom_events_7d": 1
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
<details><summary><code>security.imds-hop-limit.cluster</code></summary>

```json
{
 "applicable": true,
 "pod_identity_associations": 0,
 "imds_hop_limit_gt1": [
  {
   "id": "i-0123456789abcdef0",
   "type": "m5.large",
   "name": "system_core",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "m5.large",
   "name": "system_core",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "t8i.medium",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "m7i-flex.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "c6gn.xlarge",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "r8gd.xlarge",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "t8i.small",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0123456789abcdef0",
   "type": "r8gd.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  }
 ],
 "imds_by_setting": {
  "hop=2 tokens=required": 8
 },
 "ec2nodeclass_metadata": [
  {
   "name": "default",
   "metadataOptions": {
    "httpEndpoint": "enabled",
    "httpProtocolIPv6": "disabled",
    "httpPutResponseHopLimit": 2,
    "httpTokens": "required"
   }
  }
 ],
 "instances": 8,
 "irsa_service_accounts": [
  "external-secrets/external-secrets",
  "karpenter/karpenter",
  "kube-system/aws-load-balancer-controller",
  "kube-system/ebs-csi-controller-sa",
  "kube-system/external-dns",
  "monitoring/loki"
 ]
}
```

</details>
<details><summary><code>traffic.db-exposed.nlb/acme-db-shared</code></summary>

```json
{
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
 "sg_exposure": "allow-list",
 "hosts": [
  "nlb-db-shared.elb.us-east-1.amazonaws.com"
 ],
 "type": "nlb (defined outside the cluster)",
 "name": "acme-db-shared",
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
 "note": "NLB created outside Kubernetes; 9 TargetGroupBindings bind it to dev-app-m/app-m-backend-mysql, dev-app-o/app-o-backend-mysql, dev-app-n/app-n-backend-dev-mysql, prod-app-q/app-q-backend-postgresql, prod-app-m/app-m-backend-mysql, prod-app-o/app-o-backend-mysql and 3 more. DB port on an external address, limited by the security group to listed addresses",
 "scheme": "internet-facing",
 "namespace": null,
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
 "target": "nlb/acme-db-shared"
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-1-241</code></summary>

```json
{
 "ip_usage_ratio": 0.667,
 "eni_at_max": true,
 "node": "node-1-241",
 "max_pods": 11,
 "metrics_available": true,
 "instance_type": "t8i.small",
 "ip_max": 9,
 "ip_used": 6,
 "prefix_delegation": false,
 "no_available_ip_events": 0,
 "metrics": {
  "available": true,
  "assigned": 6,
  "total": 9,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 9,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-0123456789abcdef0": 0,
   "eni-0123456789abcdef0": 3,
   "eni-0123456789abcdef0": 3
  }
 },
 "prod_pods": 1,
 "pool": "system-ondemand",
 "ip_headroom": 3
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-2-218</code></summary>

```json
{
 "ip_usage_ratio": 0.867,
 "eni_at_max": true,
 "node": "node-2-218",
 "metrics_available": true,
 "instance_type": "t8i.medium",
 "ip_max": 15,
 "ip_used": 13,
 "prefix_delegation": false,
 "no_available_ip_events": 0,
 "metrics": {
  "available": true,
  "assigned": 13,
  "total": 15,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 15,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-0123456789abcdef0": 3,
   "eni-0123456789abcdef0": 5,
   "eni-0123456789abcdef0": 5
  }
 },
 "prod_pods": 1,
 "pool": "system-ondemand",
 "max_pods": 17
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications_prod": 8,
 "wildcard_projects": [
  "default"
 ],
 "projects": 1,
 "default_project_apps": 12,
 "applications": 12
}
```

</details>
<details><summary><code>cost.idle-compute-high.cluster</code></summary>

```json
{
 "idle_ratio": 0.95,
 "spot_node_share": 0.38,
 "spot_savings_monthly_usd": 376.36,
 "by_pool": {
  "nodegroup:system_core-20251217040546303900000001": 172.28,
  "default": 105.05,
  "system-ondemand": 154.26,
  "build-arm64": 47.74
 },
 "usd_per_core_month": 24.68,
 "monthly_usd": 479.33,
 "idle_monthly_usd": 454.0
}
```

</details>
<details><summary><code>cost.request-waste.cluster</code></summary>

```json
{
 "requests_cpu_total": 8.68,
 "monthly_usd_est": 162.65,
 "krr_saving_cores": 6.59,
 "recommended_cpu_total": 2.09
}
```

</details>
<details><summary><code>ebscsi.storageclass-unencrypted.cluster</code></summary>

```json
{
 "classes": 4,
 "classes_unencrypted": [
  "gp3",
  "gp3-1a",
  "gp3-1c"
 ],
 "default_class": "gp3",
 "classes_no_expansion": [
  "gp2",
  "gp3",
  "gp3-1a",
  "gp3-1c"
 ],
 "classes_intree": [
  "gp2"
 ]
}
```

</details>
<details><summary><code>ecr.scan-disabled.ecr/registry/<account></code></summary>

```json
{
 "repos_scan_off_prod": [
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-r-eks-prod",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-o-admin-eks-prod",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ],
 "scan_type": "BASIC",
 "images": 887,
 "repositories": 43,
 "registry_scan_on_push": false,
 "critical_high_findings": 0,
 "scan_rules": 0,
 "repos_scan_off": [
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-o-admin-dev",
  "ecr-app-r-eks-prod",
  "bitnami/kafka",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-frontend-prod",
  "app-n-admin-frontend",
  "ecr-app-m-frontend-dev",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "app-n-backend",
  "app-n-frontend",
  "ecr-app-m-admin-dev",
  "ecr-app-m-backend-dev",
  "ecr-app-m-api-dev",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-o-backend-dev",
  "ecr-app-o-admin-eks-prod",
  "app-t-backend",
  "app-t-frontend",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-frontend-dev",
  "ecr-app-o-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ],
 "account": "<account>",
 "images_scanned": 0
}
```

</details>
<details><summary><code>eks.addon-outdated.aws-ebs-csi-driver</code></summary>

```json
{
 "key": "aws-ebs-csi-driver",
 "item": {
  "version": "v1.37.0-eksbuild.1"
 }
}
```

</details>
<details><summary><code>eks.addon-outdated.vpc-cni</code></summary>

```json
{
 "key": "vpc-cni",
 "item": {
  "version": "v1.19.0-eksbuild.1"
 }
}
```

</details>
<details><summary><code>eks.nodegroup-ami-old.nodegroups</code></summary>

```json
{
 "available": true,
 "ami_old_180d": [
  "system_core-20251217040546303900000001"
 ],
 "unhealthy": [],
 "nodegroups": 1,
 "max_ami_age_days": 331,
 "ami_old_90d": [
  "system_core-20251217040546303900000001 331d"
 ]
}
```

</details>
<details><summary><code>eks.ssm-unregistered.node-1-117</code></summary>

```json
{
 "key": null,
 "item": {
  "instance_id": "i-0123456789abcdef0",
  "node": "node-1-117"
 }
}
```

</details>
<details><summary><code>eks.ssm-unregistered.node-2-60</code></summary>

```json
{
 "key": null,
 "item": {
  "instance_id": "i-0123456789abcdef0",
  "node": "node-2-60"
 }
}
```

</details>
<details><summary><code>eso.provider-api-errors.cluster</code></summary>

```json
{
 "sync_calls_error": 2556,
 "api_error_ratio": 0.0784,
 "metrics_available": true,
 "sync_calls_total": 68745,
 "not_ready_oldest_refresh_h": 7755.3,
 "reconcile_errors_total": 2556,
 "api_success": 30033,
 "api_errors": 2556,
 "not_ready": [
  "database/externalsecret/mysql-app-n-secret"
 ]
}
```

</details>
<details><summary><code>grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "api_5xx": 9,
 "datasources_with_errors": [
  "Loki(loki)"
 ],
 "metrics_available": true,
 "datasource_error_max_ratio": 0.1252,
 "present": true,
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
 "api_requests": 6952395,
 "target": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility</code></summary>

```json
{
 "reason": "Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ",
 "status": "ERROR",
 "category": "UPGRADE_READINESS",
 "name": "Amazon Linux 2 compatibility",
 "k8s_version": "1.33"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale</code></summary>

```json
{
 "registry": "docker.io",
 "holder": false,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "mutable": true,
 "container": "tailscale",
 "pull_policy": "IfNotPresent",
 "image": "tailscale/tailscale:latest",
 "tag_kind": "latest"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.prod-app-l-backend/deployment/tts-proxy</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "cpuLimitsMissing",
  "cpuRequestsMissing",
  "deploymentMissingReplicas",
  "livenessProbeMissing",
  "memoryLimitsMissing",
  "memoryRequestsMissing",
  "metadataAndInstanceMismatched",
  "missingPodDisruptionBudget",
  "priorityClassNotSet",
  "pullPolicyNotAlways",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "prod": true,
 "security_danger": [
  "dangerousCapabilities",
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "prod-app-l-backend/deployment/tts-proxy"
}
```

</details>
<details><summary><code>loki.memory-pressure.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "rss_mib": 462,
 "rss_vs_limit": 0.901,
 "restarts": 1,
 "oomkilled_at": "2026-10-25T00:15:41Z",
 "memory_streams": 54,
 "present": true,
 "oomkilled_last": true,
 "storage": "emptyDir",
 "memory_limit": "512Mi",
 "target": "monitoring/statefulset/loki-stack"
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
 "value": 57.813020474538206
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
 "value": 57.812962604167836
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeControllerManagerDown</code></summary>

```json
{
 "samples_7d": 20160.0,
 "alertname": "KubeControllerManagerDown"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubePodNotReady</code></summary>

```json
{
 "samples_7d": 47192.0,
 "alertname": "KubePodNotReady"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeSchedulerDown</code></summary>

```json
{
 "samples_7d": 20160.0,
 "alertname": "KubeSchedulerDown"
}
```

</details>
<details><summary><code>observability.log-coverage-gap.cluster</code></summary>

```json
{
 "running_pods_over_1h": 139,
 "available": true,
 "nodes_all_missing": [
  "node-2-158"
 ],
 "by_namespace_missing": {
  "kube-system": 21,
  "monitoring": 14,
  "prod-app-l-backend": 3,
  "argocd": 2,
  "dev-app-o": 2,
  "keda": 2,
  "middleware": 2,
  "app-s-prod": 2,
  "arc-runners": 1,
  "dev-app-m": 1,
  "dev-app-n": 1,
  "dev-app-t": 1,
  "karpenter": 1,
  "prod-app-q": 1,
  "prod-app-m": 1
 },
 "pods_without_logs_1h": 56,
 "gap_ratio": 0.403
}
```

</details>
<details><summary><code>operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret</code></summary>

```json
{
 "reason": "SecretSyncedError",
 "age_hours": 7760.9,
 "status": "False",
 "message": "could not get secret data from provider",
 "name": "mysql-app-n-secret",
 "condition": "Ready",
 "namespace": "database",
 "kind": "externalsecrets.external-secrets.io"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "workload": "prod-app-m/statefulset/app-m-backend-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "workload": "prod-app-o/statefulset/app-o-backend-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-l-backend/statefulset/app-l-neo4j:neo4j</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "prod": true,
 "workload": "prod-app-l-backend/statefulset/app-l-neo4j",
 "startup": null,
 "container": "neo4j",
 "liveness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "workload": "prod-app-n/statefulset/app-n-backend-prod-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
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
 "recreate_justified": false,
 "grace_s": 30,
 "replicas": 1,
 "strategy": "Recreate",
 "prod": true,
 "workload": "prod-app-p/deployment/app-p-backend",
 "recreate_reason": [],
 "prestop": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-api</code></summary>

```json
{
 "topology_spread": [],
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "replicas": 2,
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-api",
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend</code></summary>

```json
{
 "topology_spread": [],
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "replicas": 2,
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-backend",
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend</code></summary>

```json
{
 "topology_spread": [],
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "replicas": 2,
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-frontend",
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "topology_spread": [],
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "replicas": 2,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/app-l-backend",
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server</code></summary>

```json
{
 "topology_spread": [],
 "zones": {
  "us-east-1a": 2
 },
 "nodes": {
  "node-1-139": 1,
  "node-1-62": 1
 },
 "replicas": 2,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/app-l-embedding-server",
 "all_same_zone": true,
 "all_same_node": false
}
```

</details>
<details><summary><code>resilience.single-node-dependency.prod-app-l-backend/deployment/tts-proxy</code></summary>

```json
{
 "replicas": 1,
 "prod": true,
 "workload": "prod-app-l-backend/deployment/tts-proxy",
 "reasons": [
  "hostPath volume ['dev-net-tun']"
 ]
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
   "cpu_request_p95_ratio_7d": 0.005790369157065604,
   "cpu_p95_7d_cores": 0.002895184578532802,
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
   "cpu_request_p95_ratio_7d": 0.00533176804152647,
   "cpu_p95_7d_cores": 0.002665884020763235,
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
   "cpu_request_p95_ratio_7d": 0.011031092564272364,
   "cpu_p95_7d_cores": 0.005515546282136182,
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
   "cpu_request_p95_ratio_7d": 0.0024236109928838733,
   "cpu_p95_7d_cores": 0.0012118054964419366,
   "container_cpu_request_cores": 0.5
  }
 }
]
```

</details>
<details><summary><code>resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter</code></summary>

```json
{
 "heap_ratio": 1.0,
 "xmx_mib": null,
 "workload": "middleware/statefulset/kafka-controller",
 "container": "jmx-exporter",
 "heap_unset": false,
 "max_ram_percentage": 100.0,
 "image": "jmx-exporter:0.20.0-debian-11-r4",
 "limit_mib": 128.0
}
```

</details>
<details><summary><code>resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "argocd-application-controller",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.2 → 0.057 cores, CPU limit 0.5 → none, memory request 384 → 757 MB",
 "kind": "StatefulSet",
 "target": "argocd/statefulset/argocd-application-controller:application-controller",
 "kubegap_reason": "memory request under by 373 MB, CPU request over by 0.143 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "OK",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-o-backend-mysql",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 867 MB",
 "kind": "StatefulSet",
 "target": "dev-app-o/statefulset/app-o-backend-mysql:mysql",
 "kubegap_reason": "memory request under by 355 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "OK",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-n-backend-dev-mysql",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 793 MB",
 "kind": "StatefulSet",
 "target": "dev-app-n/statefulset/app-n-backend-dev-mysql:mysql",
 "kubegap_reason": "memory request under by 281 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "loki-stack",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 529 MB",
 "kind": "StatefulSet",
 "target": "monitoring/statefulset/loki-stack:loki",
 "kubegap_reason": "memory request under by 273 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "OK",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "CRITICAL",
 "summary": "CPU request 0.2 → 0.137 cores, CPU limit 0.5 → none, memory request 800 → 1639 MB",
 "kind": "StatefulSet",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus",
 "kubegap_reason": "memory request under by 839 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "vm-single",
 "cpu_request_sev": "WARNING",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 193 MB, memory limit 1024 → 193 MB",
 "kind": "StatefulSet",
 "target": "monitoring/statefulset/vm-single:vmsingle",
 "kubegap_reason": "CPU request over by 0.29 cores, memory request over by 319 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "OK",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-q-ai",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 607 MB",
 "kind": "Deployment",
 "target": "prod-app-q/deployment/app-q-ai:ai",
 "kubegap_reason": "memory request under by 351 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-m/deployment/app-m-backend:backend</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-m-backend",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 426 MB",
 "kind": "Deployment",
 "target": "prod-app-m/deployment/app-m-backend:backend",
 "kubegap_reason": "memory request under by 298 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-m/deployment/app-m-frontend:frontend</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-m-frontend",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.01 → 0.032 cores, CPU limit 0.2 → none, memory request 128 → 424 MB",
 "kind": "Deployment",
 "target": "prod-app-m/deployment/app-m-frontend:frontend",
 "kubegap_reason": "memory request under by 296 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-m-backend-mysql",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.2 → 0.012 cores, CPU limit 1.0 → none, memory request 768 → 1163 MB, memory limit 1536 → 1163 MB",
 "kind": "StatefulSet",
 "target": "prod-app-m/statefulset/app-m-backend-mysql:mysql",
 "kubegap_reason": "memory request under by 395 MB, CPU request over by 0.188 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-o/deployment/app-o-ai:ai</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-o-ai",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "CRITICAL",
 "summary": "CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 973 MB, memory limit 4096 → 973 MB",
 "kind": "Deployment",
 "target": "prod-app-o/deployment/app-o-ai:ai",
 "kubegap_reason": "memory request over by 1075 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/deployment/app-l-embedding-server:embedding</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-l-embedding-server",
 "cpu_request_sev": "WARNING",
 "info": {},
 "memory_request_sev": "CRITICAL",
 "summary": "CPU request 0.5 → 0.159 cores, CPU limit 2.0 → none, memory request 4096 → 6730 MB, memory limit 6144 → 6730 MB",
 "kind": "Deployment",
 "target": "prod-app-l-backend/deployment/app-l-embedding-server:embedding",
 "kubegap_reason": "memory request under by 2634 MB, CPU request over by 0.341 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/deployment/app-l-file-worker:file-worker</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-l-file-worker",
 "cpu_request_sev": "CRITICAL",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 1.0 → 0.128 cores, CPU limit 2.0 → none, memory request 2048 → 1711 MB, memory limit 4096 → 1711 MB",
 "kind": "Deployment",
 "target": "prod-app-l-backend/deployment/app-l-file-worker:file-worker",
 "kubegap_reason": "CPU request over by 0.872 cores, memory request over by 337 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-l-graph-worker",
 "cpu_request_sev": "WARNING",
 "info": {},
 "memory_request_sev": "CRITICAL",
 "summary": "CPU request 1.0 → 0.542 cores, CPU limit 2.0 → none, memory request 2048 → 1378 MB, memory limit 6144 → 1378 MB",
 "kind": "Deployment",
 "target": "prod-app-l-backend/deployment/app-l-graph-worker:graph-worker",
 "kubegap_reason": "CPU request over by 0.458 cores, memory request over by 670 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/statefulset/app-l-neo4j:neo4j</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-l-neo4j",
 "cpu_request_sev": "WARNING",
 "info": {},
 "memory_request_sev": "CRITICAL",
 "summary": "CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1679 MB, memory limit 5120 → 1679 MB",
 "kind": "StatefulSet",
 "target": "prod-app-l-backend/statefulset/app-l-neo4j:neo4j",
 "kubegap_reason": "CPU request over by 0.49 cores, memory request over by 2417 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-p/deployment/app-p-backend:backend</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "fail",
 "cpu_limit_sev": "WARNING",
 "name": "app-p-backend",
 "cpu_request_sev": "WARNING",
 "info": {},
 "memory_request_sev": "OK",
 "summary": "CPU request 0.5 → 0.141 cores, CPU limit 2.0 → none, memory request 1024 → 866 MB, memory limit 2048 → 866 MB",
 "kind": "Deployment",
 "target": "prod-app-p/deployment/app-p-backend:backend",
 "kubegap_reason": "CPU request over by 0.359 cores"
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
  "value": 0.5797109782169416
 },
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-l-backend",
   "pod": "app-l-embedding-server-8445d87f5-jfv9l"
  },
  "value": 0.5797109782169416
 }
]
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
 "value": 0.5797109782169416
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
<details><summary><code>resources.node-request-usage-gap.node-1-117</code></summary>

```json
{
 "labels": {
  "node": "node-1-117"
 },
 "values": {
  "node_cpu_request_ratio": 0.9637305699481866,
  "node_cpu_usage_ratio_p95_7d": 0.09451303935662735,
  "node_cpu_usage_ratio_5m": 0.09203027367014721
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
  "node_cpu_usage_ratio_5m": 0.04837377141915788
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
  "node_cpu_usage_ratio_5m": 0.0360220439758737
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
  "node_cpu_usage_ratio_p95_7d": 0.06187848672461477,
  "node_cpu_usage_ratio_5m": 0.05373734762837124
 }
}
```

</details>
<details><summary><code>scaling.karpenter-expired-not-replaced.default-n44bh</code></summary>

```json
{
 "node": "node-1-139",
 "expire_after_h": 720.0,
 "name": "default-n44bh",
 "instance_type": "r8gd.xlarge",
 "disruption_blocked": {
  "do-not-disrupt pods": 21337
 },
 "capacity_type": "spot",
 "hours_past_expiry": 301.9,
 "do_not_disrupt_pod_count": 1,
 "do_not_disrupt_pods": [
  "prod-app-m/app-m-admin-57f5fcc58d-khsh5"
 ],
 "age_h": 1021.9
}
```

</details>
<details><summary><code>security.externalsecret-not-ready.database/mysql-app-n-secret</code></summary>

```json
{
 "reason": "SecretSyncedError",
 "message": "could not get secret data from provider",
 "name": "mysql-app-n-secret",
 "namespace": "database"
}
```

</details>
<details><summary><code>security.polaris-security-danger.cluster</code></summary>

```json
{
 "danger_workloads_prod": [
  "prod-app-l-backend/deployment/tts-proxy",
  "prod-app-o/deployment/app-o-frontend",
  "prod-app-n/deployment/app-n-frontend",
  "prod-app-n/deployment/app-n-admin-frontend",
  "prod-app-o/deployment/app-o-admin",
  "prod-app-n/deployment/app-n-backend",
  "prod-app-o/deployment/app-o-backend",
  "prod-app-o/deployment/app-o-ai",
  "prod-app-l-backend/deployment/app-l-pg-proxy",
  "app-s-prod/deployment/app-s-frontend",
  "app-s-prod/deployment/app-s-backend",
  "prod-app-l-backend/deployment/app-l-graph-worker",
  "prod-app-l-backend/deployment/app-l-file-worker",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/app-l-frontend",
  "prod-app-m/deployment/app-m-admin",
  "prod-app-m/deployment/app-m-backend",
  "prod-app-q/deployment/app-q-ai",
  "prod-app-q/deployment/app-q-web",
  "prod-app-q/deployment/app-q-studio",
  "prod-app-p/deployment/app-p-web",
  "prod-app-r/deployment/app-r",
  "prod-app-m/deployment/app-m-frontend",
  "prod-app-m/deployment/app-m-api",
  "prod-app-q/deployment/app-q-backend",
  "prod-app-p/deployment/app-p-backend",
  "prod-app-l-backend/statefulset/app-l-neo4j",
  "prod-app-l-backend/deployment/app-l-backend"
 ],
 "score": 79,
 "danger_workloads": [
  "kube-system/daemonset/aws-node",
  "arc-runners/autoscalingrunnerset/self-hosted-arm64",
  "prod-app-l-backend/deployment/tts-proxy",
  "kube-system/daemonset/ebs-csi-node-windows",
  "kube-system/daemonset/ebs-csi-node",
  "middleware/deployment/redis-insight",
  "arc-runners/cronjob/arc-cool-down",
  "arc-runners/cronjob/arc-warm-up",
  "monitoring/daemonset/kube-prometheus-stack-prometheus-node-exporter",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "middleware/statefulset/kafka-controller",
  "prod-app-o/deployment/app-o-frontend",
  "prod-app-n/deployment/app-n-frontend",
  "prod-app-n/deployment/app-n-admin-frontend",
  "prod-app-o/deployment/app-o-admin",
  "prod-app-n/deployment/app-n-backend",
  "arc-system/deployment/arc-gha-rs-controller",
  "dev-app-n/deployment/app-n-frontend",
  "dev-app-t/deployment/app-t-frontend",
  "dev-app-t/deployment/app-t-backend",
  "dev-app-n/deployment/app-n-backend",
  "dev-app-n/deployment/app-n-admin-frontend",
  "prod-app-o/deployment/app-o-backend",
  "prod-app-o/deployment/app-o-ai",
  "prod-app-l-backend/deployment/app-l-pg-proxy",
  "monitoring/deployment/vmalert",
  "dev-app-o/deployment/app-o-frontend",
  "dev-app-o/deployment/app-o-admin",
  "app-s-prod/deployment/app-s-frontend",
  "app-s-prod/deployment/app-s-backend",
  "dev-app-o/deployment/app-o-ai",
  "dev-app-m/deployment/app-m-api",
  "prod-app-l-backend/deployment/app-l-graph-worker",
  "dev-app-m/deployment/app-m-backend",
  "dev-app-m/deployment/app-m-admin",
  "prod-app-l-backend/deployment/app-l-file-worker",
  "dev-app-m/deployment/app-m-frontend",
  "dev-app-o/deployment/app-o-backend",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/app-l-frontend",
  "prod-app-m/deployment/app-m-admin",
  "middleware/deployment/kafka-ui",
  "monitoring/deployment/vmauth",
  "prod-app-m/deployment/app-m-backend",
  "prod-app-q/deployment/app-q-ai",
  "prod-app-q/deployment/app-q-web",
  "prod-app-q/deployment/app-q-studio",
  "prod-app-p/deployment/app-p-web",
  "prod-app-r/deployment/app-r",
  "prod-app-m/deployment/app-m-frontend",
  "prod-app-m/deployment/app-m-api",
  "prod-app-q/deployment/app-q-backend",
  "prod-app-p/deployment/app-p-backend",
  "dev-app-t/statefulset/app-t-postgres",
  "prod-app-l-backend/statefulset/app-l-neo4j",
  "prod-app-l-backend/deployment/app-l-backend",
  "monitoring/statefulset/vm-single",
  "/clusterrolebinding/argocd-application-controller",
  "/clusterrolebinding/eks:addon-cluster-admin",
  "argocd/rolebinding/argocd-repo-server",
  "monitoring/rolebinding/kube-prometheus-stack-grafana",
  "middleware/statefulset/redis-master",
  "monitoring/statefulset/loki-stack",
  "monitoring/daemonset/loki-stack-promtail",
  "kube-system/daemonset/kube-proxy",
  "kube-system/deployment/coredns",
  "/clusterrolebinding/argocd-server",
  "/clusterrolebinding/keda-operator",
  "argocd/role/argocd-repo-server",
  "monitoring/role/kube-prometheus-stack-grafana",
  "/clusterrole/argocd-application-controller",
  "/clusterrole/argocd-server",
  "/clusterrole/eks:extension-metrics-apiserver",
  "/clusterrole/keda-operator"
 ],
 "present": true,
 "danger_check_counts": {
  "dangerousCapabilities": 2,
  "hostNetworkSet": 2,
  "privilegeEscalationAllowed": 59,
  "runAsPrivileged": 3,
  "runAsRootAllowed": 58,
  "hostPIDSet": 1,
  "clusterrolebindingClusterAdmin": 2,
  "clusterrolebindingPodExecAttach": 4,
  "rolebindingClusterAdminRole": 2,
  "rolebindingRolePodExecAttach": 2,
  "sensitiveContainerEnvVar": 1,
  "rolePodExecAttach": 2,
  "clusterrolePodExecAttach": 4
 }
}
```

</details>
<details><summary><code>storage.csi-snapshot-unavailable.cluster</code></summary>

```json
{
 "recent_7d": 0,
 "prod_pvcs": 7,
 "volumesnapshot_crd": false,
 "ebs_snapshot_descriptions": {
  "pre-delete backup of orphan PVC prod-app-m": 4,
  "pre-delete backup of orphan PVC app-s-prod": 2,
  "pre-delete backup of orphan PVC prod-app-o": 2,
  "pre-delete backup of orphan PVC dev-app-n": 1,
  "pre-delete backup of orphan PVC dev-app-o": 1
 },
 "platform": "eks",
 "ebs_snapshots_30d": 12,
 "volumesnapshots": 0,
 "volumesnapshotclasses": 0
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3</code></summary>

```json
{
 "key": null,
 "item": {
  "expansion": false,
  "name": "gp3",
  "provisioner": "ebs.csi.aws.com"
 }
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3-1a</code></summary>

```json
{
 "key": null,
 "item": {
  "expansion": false,
  "name": "gp3-1a",
  "provisioner": "ebs.csi.aws.com"
 }
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3-1c</code></summary>

```json
{
 "key": null,
 "item": {
  "expansion": false,
  "name": "gp3-1c",
  "provisioner": "ebs.csi.aws.com"
 }
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.prod-app-l-backend</code></summary>

```json
{
 "cpu_limits": 12.2,
 "cpu_max_7d": 3.905,
 "nodes": {
  "node-1-139": 4,
  "node-2-135": 3,
  "node-1-62": 2
 },
 "has_quota": false,
 "system": false,
 "cpu_p95_7d": 0.026,
 "namespace": "prod-app-l-backend",
 "shares_nodes_with_prod": true,
 "kind": "prod",
 "cpu_median_7d": 0.011,
 "burst_ratio_7d": 352.3
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-r</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-r",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "pods": 2
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-m</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-m",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "pods": 8
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-o</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-o",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "pods": 8
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-l-backend</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-l-backend",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "pods": 9
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-n</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-n",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "pods": 4
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-r</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.003,
 "tenants_total": 14,
 "memory_requests_gb": 0.25,
 "cpu_requests": 0.1,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.004,
 "memory_p95_7d_gb": 0.2,
 "multi_org": false,
 "namespace": "prod-app-r",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 2,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-q</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.008,
 "tenants_total": 14,
 "memory_requests_gb": 0.84,
 "cpu_requests": 0.29,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.009,
 "memory_p95_7d_gb": 0.93,
 "multi_org": false,
 "namespace": "prod-app-q",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 5,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-m</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.088,
 "tenants_total": 14,
 "memory_requests_gb": 1.62,
 "cpu_requests": 0.35,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.109,
 "memory_p95_7d_gb": 1.88,
 "multi_org": false,
 "namespace": "prod-app-m",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 8,
 "burst_ratio_7d": 1.5
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-o</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.03,
 "tenants_total": 14,
 "memory_requests_gb": 8.0,
 "cpu_requests": 0.51,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.037,
 "memory_p95_7d_gb": 2.8,
 "multi_org": false,
 "namespace": "prod-app-o",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 8,
 "burst_ratio_7d": 2.2
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-l-backend</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.021,
 "tenants_total": 14,
 "memory_requests_gb": 14.53,
 "cpu_requests": 2.72,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.026,
 "memory_p95_7d_gb": 9.92,
 "multi_org": false,
 "namespace": "prod-app-l-backend",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 9,
 "burst_ratio_7d": 352.3
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-p</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.005,
 "tenants_total": 14,
 "memory_requests_gb": 1.28,
 "cpu_requests": 0.62,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.006,
 "memory_p95_7d_gb": 0.74,
 "multi_org": false,
 "namespace": "prod-app-p",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 3,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-n</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.019,
 "tenants_total": 14,
 "memory_requests_gb": 1.12,
 "cpu_requests": 0.25,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.024,
 "memory_p95_7d_gb": 1.0,
 "multi_org": false,
 "namespace": "prod-app-n",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 4,
 "burst_ratio_7d": 4.2
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-s-prod</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.018,
 "tenants_total": 14,
 "memory_requests_gb": 0.94,
 "cpu_requests": 0.25,
 "prod": true,
 "has_quota": false,
 "cpu_p95_7d": 0.023,
 "memory_p95_7d_gb": 0.5,
 "multi_org": false,
 "namespace": "app-s-prod",
 "shares_nodes_with_prod": true,
 "cluster_saturated_7d": true,
 "kind": "prod",
 "pods": 3,
 "burst_ratio_7d": 2.1
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.prod-app-l-backend</code></summary>

```json
{
 "containers_without_memory_limit": 2,
 "prod": true,
 "pods": 9,
 "cpu_p95_7d": 0.026,
 "memory_p95_7d_gb": 9.92,
 "multi_org": false,
 "has_limitrange": false,
 "namespace": "prod-app-l-backend",
 "cluster_saturated_7d": true,
 "kind": "prod",
 "containers_without_requests": 2
}
```

</details>
<details><summary><code>traffic.alb-elb-5xx.k8s-shared-alb</code></summary>

```json
{
 "rejected_connections_24h": 0,
 "target_groups": 40,
 "idle_timeout_s": 300,
 "requests_24h": 204733.0,
 "elb_5xx_24h": 168.0,
 "type": "application",
 "name": "k8s-shared-alb",
 "target_5xx_24h": 771.0,
 "scheme": "internet-facing"
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-m/app-m-api</code></summary>

```json
{
 "hosts": [
  "canary-api-v1.example-b.ai",
  "api.v1.example-b.ai"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 1286.0,
  "requests_24h_equiv": 1286.0,
  "rps_avg": 0.015,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 53.064,
  "p95_s_avg": 17.0241,
  "p95_s_weighted": 15.0916,
  "p95_s_last_1h": 16.5933,
  "p95_s_last_at": "2026-11-05T07:20:00+00:00",
  "requests_last_1h": 3.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-c50edbe2df"
  ]
 },
 "target": "prod-app-m/app-m-api"
}
```

</details>
<details><summary><code>traffic.shared-alb-group.alb-group/acme-prod-lb</code></summary>

```json
{
 "kinds": [
  "dev",
  "other",
  "prod"
 ],
 "hosts": 47,
 "prod": true,
 "group": "acme-prod-lb",
 "namespace_count": 15,
 "ingress_count": 40,
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
 "target": "alb-group/acme-prod-lb",
 "mixed_prod_nonprod": true,
 "lb": [
  "k8s-app-svc-alb.us-east-1.elb.amazonaws.com"
 ]
}
```

</details>
<details><summary><code>vpccni.prefix-delegation-off.cluster</code></summary>

```json
{
 "nodes": 8,
 "nitro_nodes": 8,
 "policy": "whole_eni",
 "nodes_near_ip_limit": [
  "node-2-218",
  "node-1-241",
  "node-2-60",
  "node-1-139",
  "node-1-62",
  "node-1-117"
 ],
 "nodes_no_available_ip": [
  "node-1-139"
 ],
 "prefix_delegation": false
}
```

</details>
<details><summary><code>albctl.reconcile-errors.cluster</code></summary>

```json
{
 "tgb_stale": [],
 "workqueue_depth_max": 0.0,
 "leader_found": true,
 "metrics_available": true,
 "reconcile_errors_total": 41,
 "rest_client_429_503": 126,
 "ingresses_without_lb": []
}
```

</details>
<details><summary><code>albctl.tgb-stale-or-orphan.cluster</code></summary>

```json
{
 "tgb_stale": [],
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
 ],
 "tgb_by_target_type": {
  "ip": 51
 },
 "tgb_service_missing": [],
 "tgb_count": 51,
 "traffic_target_groups_without_tgb": 1
}
```

</details>
<details><summary><code>argocd.admin-account-no-sso.cluster</code></summary>

```json
{
 "rbac_policy_csv_lines": 0,
 "sso_configured": false,
 "url": "https://deploy.my-cluster",
 "exec_enabled": false,
 "anonymous_enabled": false,
 "admin_enabled": true,
 "rbac_policy_default": ""
}
```

</details>
<details><summary><code>argocd.components-not-ha.cluster</code></summary>

```json
{
 "applications_prod": 8,
 "components_not_ready": [],
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
 "components_single_replica": [
  "repo-server",
  "server"
 ]
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.LIST</code></summary>

```json
{
 "labels": {
  "verb": "LIST"
 },
 "value": 0.5471875000000018
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.PATCH</code></summary>

```json
{
 "labels": {
  "verb": "PATCH"
 },
 "value": 0.6990625000000006
}
```

</details>
<details><summary><code>controlplane.controller-error-repeat.type.go</code></summary>

```json
{
 "count": 80431,
 "source": "type.go",
 "level": "W"
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "nxdomain_ratio": 0.511,
 "upstreams": [
  "<ip>:53"
 ],
 "autopath": false,
 "cache_hit_ratio": 0.9095,
 "metrics_available": true,
 "qps_total": 78.46,
 "forward_nxdomain_ratio": 0.475,
 "pods_default_ndots": 145
}
```

</details>
<details><summary><code>ecr.dockerhub-dependency.ecr/registry/<account></code></summary>

```json
{
 "pull_through_cache_rules": [],
 "images_by_registry": {
  "<account>.dkr.ecr.us-east-1.amazonaws.com": 70,
  "<account>.dkr.ecr.us-east-1.amazonaws.com": 55,
  "docker.io": 33,
  "quay.io": 24,
  "ghcr.io": 11,
  "public.ecr.aws": 8,
  "registry.k8s.io": 3
 },
 "dockerhub_images": 20,
 "dockerhub_sample": [
  "alpine/socat:1.8.0.0",
  "bitnami/kubectl:latest",
  "docker.io/bitnamilegacy/jmx-exporter:0.20.0-debian-11-r4",
  "docker.io/bitnamilegacy/kafka:3.6.1-debian-11-r3",
  "docker.io/bitnamilegacy/kubectl:1.32.4",
  "docker.io/bitnamilegacy/os-shell:11-debian-11-r95"
 ],
 "replication_rules": 0,
 "account": "<account>"
}
```

</details>
<details><summary><code>eks.addon-outdated.coredns</code></summary>

```json
{
 "key": "coredns",
 "item": {
  "version": "v1.11.3-eksbuild.1"
 }
}
```

</details>
<details><summary><code>eks.addon-outdated.kube-proxy</code></summary>

```json
{
 "key": "kube-proxy",
 "item": {
  "version": "v1.32.0-eksbuild.2"
 }
}
```

</details>
<details><summary><code>eso.controller-single-replica.cluster</code></summary>

```json
{
 "webhook_ready": 1,
 "concurrent": "1",
 "controller_replicas": 1,
 "cert_controller_replicas": 1,
 "webhook_replicas": 1,
 "controller_ready": 1,
 "webhook_fail_policy": [
  "validate.externalsecret.external-secrets.io",
  "validate.secretstore.external-secrets.io",
  "validate.clustersecretstore.external-secrets.io"
 ],
 "cert_controller_ready": 1
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl</code></summary>

```json
{
 "registry": "docker.io",
 "prod": false,
 "workload": "arc-runners/cronjob/arc-cool-down",
 "mutable": true,
 "container": "kubectl",
 "pull_policy": "Always",
 "image": "bitnami/kubectl:latest",
 "tag_kind": "latest"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl</code></summary>

```json
{
 "registry": "docker.io",
 "prod": false,
 "workload": "arc-runners/cronjob/arc-warm-up",
 "mutable": true,
 "container": "kubectl",
 "pull_policy": "Always",
 "image": "bitnami/kubectl:latest",
 "tag_kind": "latest"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight</code></summary>

```json
{
 "registry": "docker.io",
 "prod": false,
 "workload": "middleware/deployment/redis-insight",
 "mutable": true,
 "container": "redis-insight",
 "pull_policy": "Always",
 "image": "redis/redisinsight:latest",
 "tag_kind": "latest"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.acme.ai/role</code></summary>

```json
{
 "nodes_with_label": 5,
 "key": "acme.ai/role",
 "workloads": [
  "argocd/deployment/argocd-applicationset-controller",
  "argocd/deployment/argocd-dex-server",
  "argocd/deployment/argocd-notifications-controller",
  "argocd/deployment/argocd-redis",
  "argocd/deployment/argocd-repo-server",
  "argocd/deployment/argocd-server",
  "kube-system/deployment/external-dns",
  "middleware/deployment/kafka-exporter"
 ],
 "nodes_total": 8,
 "well_known": false,
 "prod_workloads": 8,
 "workload_count": 33
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.workload-type</code></summary>

```json
{
 "nodes_with_label": 3,
 "key": "workload-type",
 "workloads": [
  "dev-app-m/deployment/app-m-admin",
  "dev-app-m/deployment/app-m-api",
  "dev-app-m/deployment/app-m-backend",
  "dev-app-m/deployment/app-m-frontend",
  "dev-app-o/deployment/app-o-admin",
  "dev-app-o/deployment/app-o-ai",
  "dev-app-o/deployment/app-o-backend",
  "dev-app-o/deployment/app-o-frontend"
 ],
 "nodes_total": 8,
 "well_known": false,
 "prod_workloads": 25,
 "workload_count": 38
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.arc-runners/autoscalingrunnerset/self-hosted-arm64</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "cpuLimitsMissing",
  "cpuRequestsMissing",
  "livenessProbeMissing",
  "memoryLimitsMissing",
  "memoryRequestsMissing",
  "priorityClassNotSet",
  "pullPolicyNotAlways",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "prod": false,
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsPrivileged",
  "runAsRootAllowed"
 ],
 "target": "arc-runners/autoscalingrunnerset/self-hosted-arm64"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-cool-down</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "cpuLimitsMissing",
  "cpuRequestsMissing",
  "memoryLimitsMissing",
  "memoryRequestsMissing",
  "metadataAndInstanceMismatched",
  "priorityClassNotSet"
 ],
 "prod": false,
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "arc-runners/cronjob/arc-cool-down"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-warm-up</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "cpuLimitsMissing",
  "cpuRequestsMissing",
  "memoryLimitsMissing",
  "memoryRequestsMissing",
  "metadataAndInstanceMismatched",
  "priorityClassNotSet"
 ],
 "prod": false,
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "arc-runners/cronjob/arc-warm-up"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.middleware/deployment/redis-insight</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "cpuLimitsMissing",
  "deploymentMissingReplicas",
  "livenessProbeMissing",
  "metadataAndInstanceMismatched",
  "missingPodDisruptionBudget",
  "priorityClassNotSet",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "prod": false,
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "middleware/deployment/redis-insight"
}
```

</details>
<details><summary><code>karpenter.consistency-errors.cluster</code></summary>

```json
{
 "cluster_state_synced": true,
 "pods_startup_avg_s": 31.3,
 "pods_startup_count": 8485,
 "consistency_errors": 3,
 "metrics_available": true,
 "reconcile_errors": {},
 "node_termination_avg_s": 15.1
}
```

</details>
<details><summary><code>keda.components-single-replica.cluster</code></summary>

```json
{
 "operator_ready": 1,
 "unused": false,
 "has_pdb": false,
 "metrics_apiserver_ready": 1,
 "apiservice_available": true,
 "scaledobjects_prod": 3,
 "operator_replicas": 1,
 "metrics_apiserver_replicas": 1
}
```

</details>
<details><summary><code>keda.prod-external-trigger-no-fallback.cluster</code></summary>

```json
{
 "prod_external_without_fallback": [
  "prod-app-o/scaledobject/app-o-ai-kafka-lag",
  "prod-app-l-backend/scaledobject/app-l-file-worker",
  "prod-app-l-backend/scaledobject/app-l-graph-worker"
 ],
 "trigger_types": {
  "kafka": 4,
  "metrics-api": 2
 },
 "polling_interval_min_s": 15
}
```

</details>
<details><summary><code>logs.signatures.containerd.shim-error</code></summary>

```json
{
 "count": 33,
 "first": "2026-11-04T09:27:46Z",
 "last": "2026-11-05T07:20:08Z",
 "warn_at": 5,
 "fail_at": 50,
 "files": {
  "logs/node/node-1-139/containerd-24h.log": 13,
  "logs/node/node-1-62/containerd-24h.log": 12,
  "logs/node/node-1-241/containerd-24h.log": 4,
  "logs/node/node-2-218/containerd-24h.log": 4
 },
 "samples": [
  "2026-11-04T10:05:50+0000 node-1-139 containerd[1461]: time=\"2026-11-04T10:05:50.780130578Z\" level=warning msg=\"cleaning up after shim disconnected\" id=49c3df5ef5da35e98fe0dd4ae2e4e3b3a3a206cb8e7932ff7da3ba",
  "2026-11-04T10:05:50+0000 node-1-139 containerd[1461]: time=\"2026-11-04T10:05:50.823880910Z\" level=warning msg=\"cleaning up after shim disconnected\" id=f44e1615485fd232edda6fa16578658eb52ebf8776937baee29d34",
  "2026-11-05T02:35:50+0000 node-1-139 containerd[1461]: time=\"2026-11-05T02:35:50.888650514Z\" level=warning msg=\"cleaning up after shim disconnected\" id=d21bfec6661abdc6830281d5e12eea11710af0b5aaa0fe3b60667f",
  "2026-11-05T02:35:50+0000 node-1-139 containerd[1461]: time=\"2026-11-05T02:35:50.939446703Z\" level=warning msg=\"cleaning up after shim disconnected\" id=56417a970bc3b8cb0d7bc77da665243d3cdf3bcbefd66671b039f7",
  "2026-11-05T05:02:49+0000 node-1-139 containerd[1461]: time=\"2026-11-05T05:02:49.949108468Z\" level=warning msg=\"cleaning up after shim disconnected\" id=451879ce04a5a050e80ba066b669b770628fb0a6d9a4e75c3706c9"
 ]
}
```

</details>
<details><summary><code>logs.signatures.ebs-csi.snapshot-crd-missing</code></summary>

```json
{
 "count": 1500,
 "first": "2026-11-05T03:40:39Z",
 "last": "2026-11-05T08:21:00Z",
 "warn_at": 1,
 "fail_at": 100,
 "files": {
  "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 1500
 },
 "samples": [
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:39.431880726Z W1105 03:40:39.431762       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:39.432023524Z E1105 03:40:39.431966       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:54.750810293Z W1105 03:40:54.750691       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:40:54.750861171Z E1105 03:40:54.750771       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-05T03:41:23.451583901Z W1105 03:41:23.451429       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se"
 ]
}
```

</details>
<details><summary><code>logs.signatures.kubelet.image-gc-failed</code></summary>

```json
{
 "count": 2,
 "first": "2026-11-04T10:06:59Z",
 "last": "2026-11-05T05:52:02Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/node/node-1-139/kubelet-24h.log": 2
 },
 "samples": [
  "2026-11-04T10:06:59+0000 node-1-139 kubelet[1593]: E1104 10:06:59.922962    1593 kubelet.go:1564] \"Image garbage collection failed once. Stats initialization may not have completed yet\" err=\"Failed to garb",
  "2026-11-05T05:52:02+0000 node-1-139 kubelet[1593]: E1105 05:52:02.650894    1593 kubelet.go:1564] \"Image garbage collection failed once. Stats initialization may not have completed yet\" err=\"Failed to garb"
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
<details><summary><code>loki.request-errors.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "requests_5xx": 1,
 "requests_total": 5968052,
 "target": "monitoring/statefulset/loki-stack",
 "requests_5xx_by_route": {
  "loki_api_v1_series": 1
 },
 "metrics_available": true,
 "present": true,
 "discarded_by_reason": {},
 "log_error_messages": 10130,
 "wal_disk_full_failures": 0,
 "panics": 0
}
```

</details>
<details><summary><code>node.kernel-net-mem-pressure.node-2-135</code></summary>

```json
{
 "kernel": {
  "source": "dmesg",
  "window": "since boot (dmesg; journald does not hold 24 hours)",
  "lines": 1142,
  "counts": {
   "oom_node": 0,
   "oom_cgroup": 0,
   "oom_system_victim": 0,
   "lockup": 0,
   "io_error": 0,
   "fs_error": 0,
   "nic": 0,
   "conntrack_full": 0,
   "net_pressure": 1,
   "mem_pressure": 0,
   "bug": 0,
   "segfault": 0,
   "clock": 0
  },
  "samples": [
   "[Sat Oct 10 05:24:47 2026] TCP: request_sock_TCP: Possible SYN flooding on port 9095. Sending cookies.  Check SNMP counters."
  ],
  "oom_samples": [],
  "oom_section": true,
  "oom_kills": [],
  "total_events": 1
 },
 "node": "node-2-135",
 "collected": true
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
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
 ]
}
```

</details>
<details><summary><code>observability.promtail-dropped.cluster</code></summary>

```json
{
 "dropped_entries_1h": null,
 "metrics_scraped": false,
 "request_errors_1h": null,
 "targets_active": null
}
```

</details>
<details><summary><code>observability.slo-without-burn-rate.cluster</code></summary>

```json
{
 "tools": [],
 "burn_rate_alerts": [],
 "slo_labelled_rules": [
  "ImageInferenceE2ESuccessRateDrop",
  "ImageInferenceEntitlementFailureSpike",
  "LoraTrainingSuccessRateDrop",
  "LoraTrainingDurationP95High",
  "LoraTrainingCallbackTimeout"
 ],
 "sli_recording_rules": [],
 "any_signal": true
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "workload": "dev-app-m/statefulset/app-m-backend-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "workload": "dev-app-o/statefulset/app-o-backend-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "workload": "dev-app-n/statefulset/app-n-backend-dev-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-t/statefulset/app-t-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "workload": "dev-app-t/statefulset/app-t-mysql",
 "startup": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 10,
  "initial_delay_s": 15
 },
 "container": "mysql",
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-t/statefulset/app-t-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": false,
 "workload": "dev-app-t/statefulset/app-t-postgres",
 "startup": null,
 "container": "postgres",
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "readiness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 },
 "prod": false,
 "workload": "monitoring/statefulset/loki-stack",
 "startup": null,
 "container": "loki",
 "liveness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 }
}
```

</details>
<details><summary><code>resilience.priority-inversion.cluster</code></summary>

```json
{
 "prod_max_priority": 0,
 "preempted_events": 0,
 "pods_by_class": {
  "(none, 0)": 106,
  "system-cluster-critical": 9,
  "system-node-critical": 24
 },
 "user_classes": [],
 "nonprod_max_priority": 0,
 "inversion": [],
 "no_user_classes_with_prod": true,
 "prod_pods_without_class": 42,
 "prod_pods": 42
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.cluster</code></summary>

```json
{
 "local_only": [],
 "prod_db_without_backup_cronjob": [
  "prod-app-q/statefulset/app-q-backend-postgresql",
  "prod-app-m/statefulset/app-m-backend-mysql",
  "prod-app-o/statefulset/app-o-backend-mysql",
  "prod-app-l-backend/statefulset/app-l-neo4j",
  "prod-app-p/statefulset/app-p-postgresql",
  "prod-app-n/statefulset/app-n-backend-prod-mysql",
  "app-s-prod/statefulset/app-s-backend-postgresql"
 ],
 "same_node": [],
 "count": 0,
 "db_workloads_with_pvc": 17
}
```

</details>
<details><summary><code>resilience.recreate-strategy-serving.monitoring/deployment/vmauth</code></summary>

```json
{
 "recreate_justified": false,
 "grace_s": 30,
 "replicas": 1,
 "strategy": "Recreate",
 "prod": false,
 "workload": "monitoring/deployment/vmauth",
 "namespace": "monitoring",
 "recreate_reason": [],
 "prestop": false
}
```

</details>
<details><summary><code>resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master</code></summary>

```json
{
 "grace_s": 30,
 "prod": false,
 "shell_pid1_containers": [
  "redis",
  "metrics"
 ],
 "workload": "middleware/statefulset/redis-master",
 "prestop": false
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
  "cpu_request_p95_ratio_7d": 0.17168659435701372,
  "cpu_p95_7d_cores": 0.017168659435701374,
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
  "cpu_request_p95_ratio_7d": 0.05296316676553208,
  "cpu_p95_7d_cores": 0.005296316676553208,
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
  "cpu_request_p95_ratio_7d": 0.34162010124761694,
  "cpu_p95_7d_cores": 0.06832402024952339,
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
  "cpu_request_p95_ratio_7d": 0.06718709972469009,
  "cpu_p95_7d_cores": 0.00671870997246901,
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
  "cpu_request_p95_ratio_7d": 0.1432613000845396,
  "cpu_p95_7d_cores": 0.014326130008453961,
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
<details><summary><code>resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "argocd-repo-server",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 257 MB, memory limit 1024 → 257 MB",
 "kind": "Deployment",
 "target": "argocd/deployment/argocd-repo-server:repo-server",
 "kubegap_reason": "CPU request over by 0.19 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-m/deployment/app-m-frontend:frontend</code></summary>

```json
{
 "severity": "GOOD",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "cpu_limit_sev": "UNKNOWN",
 "name": "app-m-frontend",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "memory_request_sev": "GOOD",
 "summary": "CPU HPA detected, memory request 128 → 213 MB",
 "kind": "Deployment",
 "target": "dev-app-m/deployment/app-m-frontend:frontend",
 "kubegap_reason": "memory request under by 85 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-m-backend-mysql",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "OK",
 "summary": "CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 625 MB, memory limit 1024 → 625 MB",
 "kind": "StatefulSet",
 "target": "dev-app-m/statefulset/app-m-backend-mysql:mysql",
 "kubegap_reason": "memory request under by 113 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-o/deployment/app-o-ai:ai</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-o-ai",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 566 MB, memory limit 2048 → 566 MB",
 "kind": "Deployment",
 "target": "dev-app-o/deployment/app-o-ai:ai",
 "kubegap_reason": "memory request over by 458 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-o/deployment/app-o-backend:backend</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "UNKNOWN",
 "name": "app-o-backend",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "memory_request_sev": "WARNING",
 "summary": "CPU HPA detected, memory request 512 → 153 MB, memory limit 8192 → 153 MB",
 "kind": "Deployment",
 "target": "dev-app-o/deployment/app-o-backend:backend",
 "kubegap_reason": "memory request over by 359 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-t/statefulset/app-t-mysql:mysql</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-t-mysql",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB",
 "kind": "StatefulSet",
 "target": "dev-app-t/statefulset/app-t-mysql:mysql",
 "kubegap_reason": "CPU request over by 0.19 cores, memory request over by 341 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.karpenter/deployment/karpenter:controller</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "OK",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "karpenter",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "OK",
 "summary": "CPU request 0.2 → 0.02 cores, CPU limit 0.5 → none, memory request 256 → 408 MB",
 "kind": "Deployment",
 "target": "karpenter/deployment/karpenter:controller",
 "kubegap_reason": "memory request under by 152 MB, CPU request over by 0.18 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "kafka-controller",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.2 → 0.07 cores, CPU limit 0.5 → none, memory request 1536 → 1466 MB, memory limit 2048 → 1466 MB",
 "kind": "StatefulSet",
 "target": "middleware/statefulset/kafka-controller:kafka",
 "kubegap_reason": "CPU request over by 0.13 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "loki-stack-promtail",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "OK",
 "summary": "CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 272 MB",
 "kind": "DaemonSet",
 "target": "monitoring/daemonset/loki-stack-promtail:promtail",
 "kubegap_reason": "memory request under by 144 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-q/deployment/app-q-backend:backend</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "OK",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-q-backend",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "OK",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 381 MB",
 "kind": "Deployment",
 "target": "prod-app-q/deployment/app-q-backend:backend",
 "kubegap_reason": "memory request under by 189 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-q/deployment/app-q-web:web</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-q-web",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "kind": "Deployment",
 "target": "prod-app-q/deployment/app-q-web:web",
 "kubegap_reason": "memory request under by 68 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-o/deployment/app-o-backend:backend</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-o-backend",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "WARNING",
 "summary": "CPU request 0.1 → 0.011 cores, CPU limit 2.0 → none, memory request 512 → 116 MB, memory limit 2048 → 116 MB",
 "kind": "Deployment",
 "target": "prod-app-o/deployment/app-o-backend:backend",
 "kubegap_reason": "memory request over by 396 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-o-backend-mysql",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB",
 "kind": "StatefulSet",
 "target": "prod-app-o/statefulset/app-o-backend-mysql:mysql",
 "kubegap_reason": "CPU request over by 0.19 cores"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/deployment/app-l-backend:backend</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "UNKNOWN",
 "name": "app-l-backend",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "memory_request_sev": "WARNING",
 "summary": "CPU HPA detected, memory request 1024 → 614 MB, memory limit 2048 → 614 MB",
 "kind": "Deployment",
 "target": "prod-app-l-backend/deployment/app-l-backend:backend",
 "kubegap_reason": "memory request over by 410 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-l-backend/deployment/app-l-pg-proxy:forwarder</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-l-pg-proxy",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "kind": "Deployment",
 "target": "prod-app-l-backend/deployment/app-l-pg-proxy:forwarder",
 "kubegap_reason": "memory request under by 68 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-p/deployment/app-p-web:web</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-p-web",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "kind": "Deployment",
 "target": "prod-app-p/deployment/app-p-web:web",
 "kubegap_reason": "memory request under by 68 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-n/deployment/app-n-backend:backend</code></summary>

```json
{
 "severity": "WARNING",
 "memory_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-n-backend",
 "cpu_request_sev": "GOOD",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 217 MB, memory limit 512 → 217 MB",
 "kind": "Deployment",
 "target": "prod-app-n/deployment/app-n-backend:backend",
 "kubegap_reason": "memory request under by 89 MB"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "severity": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "kubegap_level": "warn",
 "cpu_limit_sev": "WARNING",
 "name": "app-n-backend-prod-mysql",
 "cpu_request_sev": "OK",
 "info": {},
 "memory_request_sev": "GOOD",
 "summary": "CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 811 MB, memory limit 1536 → 811 MB",
 "kind": "StatefulSet",
 "target": "prod-app-n/statefulset/app-n-backend-prod-mysql:mysql",
 "kubegap_reason": "CPU request over by 0.189 cores"
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
  "node_memory_usage_ratio_p95_7d": 0.32736954917217953,
  "node_memory_usage_ratio": 0.4282197026437417
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
  "node_memory_usage_ratio_p95_7d": 0.41657824336770366,
  "node_memory_usage_ratio": 0.475335882295471
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
  "node_cpu_usage_ratio_5m": 0.04384517918101138
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
 "value": 48.0
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
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
 ],
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
 "root_allowed_ratio": 0.62,
 "psa_enforced_namespaces": []
}
```

</details>
<details><summary><code>security.rbac-wildcard.argocd-application-controller</code></summary>

```json
{
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "argocd",
   "name": "argocd-application-controller"
  }
 ],
 "prod": false,
 "clusterrole": "argocd-application-controller",
 "bound": true
}
```

</details>
<details><summary><code>security.sa-token-mounted-without-rbac.cluster</code></summary>

```json
{
 "workloads": 91,
 "automount_false_sa": 6,
 "service_accounts": 111,
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
  "prod-app-l-backend/deployment/app-l-frontend",
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
 ],
 "token_mounted": 86
}
```

</details>
<details><summary><code>storage.ebs-unencrypted.cluster</code></summary>

```json
{
 "volumes": 17,
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
 ]
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
   "used_ratio": 0.461,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.004,
   "days_to_full": 2763,
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
   "days_to_full": 35247,
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
   "days_to_full": 5426,
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
   "days_to_full": 1956833,
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
   "days_to_full": 14591,
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
   "days_to_full": 507653,
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
   "days_to_full": 41361,
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
   "days_to_full": 4883,
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
   "days_to_full": 1187,
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
   "days_to_full": 3906536,
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
   "days_to_full": 2882,
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
   "days_to_full": 51486,
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
   "days_to_full": 45083231939,
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
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-q",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 1,
 "pods": 5
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-p</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "prod-app-p",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 1,
 "pods": 3
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-s-prod</code></summary>

```json
{
 "tenants_total": 14,
 "prod": true,
 "has_quota": false,
 "psa_enforce": null,
 "networkpolicy_enforced": false,
 "has_limitrange": false,
 "namespace": "app-s-prod",
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "networkpolicies": 1,
 "pods": 3
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-runners</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.384,
 "tenants_total": 14,
 "memory_requests_gb": 4.0,
 "cpu_requests": 2.0,
 "prod": false,
 "has_quota": false,
 "cpu_p95_7d": 0.471,
 "memory_p95_7d_gb": 1.96,
 "namespace": "arc-runners",
 "shares_nodes_with_prod": false,
 "kind": "ci",
 "pods": 1,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-m</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.042,
 "tenants_total": 14,
 "memory_requests_gb": 1.25,
 "cpu_requests": 0.4,
 "prod": false,
 "has_quota": false,
 "cpu_p95_7d": 0.052,
 "memory_p95_7d_gb": 0.86,
 "namespace": "dev-app-m",
 "shares_nodes_with_prod": true,
 "kind": "dev",
 "pods": 5,
 "burst_ratio_7d": 1.4
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-o</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.028,
 "tenants_total": 14,
 "memory_requests_gb": 2.25,
 "cpu_requests": 0.4,
 "prod": false,
 "has_quota": false,
 "cpu_p95_7d": 0.035,
 "memory_p95_7d_gb": 1.4,
 "namespace": "dev-app-o",
 "shares_nodes_with_prod": true,
 "kind": "dev",
 "pods": 5,
 "burst_ratio_7d": 1.1
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-n</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.02,
 "tenants_total": 14,
 "memory_requests_gb": 1.0,
 "cpu_requests": 0.3,
 "prod": false,
 "has_quota": false,
 "cpu_p95_7d": 0.024,
 "memory_p95_7d_gb": 0.95,
 "namespace": "dev-app-n",
 "shares_nodes_with_prod": true,
 "kind": "dev",
 "pods": 4,
 "burst_ratio_7d": 1.5
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-t</code></summary>

```json
{
 "cpu_share_of_cluster_p95": 0.014,
 "tenants_total": 14,
 "memory_requests_gb": 1.88,
 "cpu_requests": 0.55,
 "prod": false,
 "has_quota": false,
 "cpu_p95_7d": 0.017,
 "memory_p95_7d_gb": 0.85,
 "namespace": "dev-app-t",
 "shares_nodes_with_prod": true,
 "kind": "dev",
 "pods": 4,
 "burst_ratio_7d": 1.1
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-1-117</code></summary>

```json
{
 "containers_without_memory_limit": 3,
 "memory_requests_gb": 4.7,
 "node": "node-1-117",
 "memory_limits_gb": 11.6,
 "allocatable_memory_gb": 6.9,
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
 "memory_limit_overcommit": 1.68,
 "prod_pods": 2,
 "tenant_count": 2,
 "pool": "system_core-20251217040546303900000001",
 "tenant_kinds": [
  "dev",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-1-139</code></summary>

```json
{
 "containers_without_memory_limit": 0,
 "memory_requests_gb": 18.8,
 "node": "node-1-139",
 "memory_limits_gb": 46.1,
 "allocatable_memory_gb": 29.8,
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
 "memory_limit_overcommit": 1.55,
 "prod_pods": 20,
 "tenant_count": 2,
 "pool": "default",
 "tenant_kinds": [
  "dev",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-2-218</code></summary>

```json
{
 "containers_without_memory_limit": 2,
 "memory_requests_gb": 1.7,
 "node": "node-2-218",
 "memory_limits_gb": 5.0,
 "allocatable_memory_gb": 3.2,
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
 "memory_limit_overcommit": 1.55,
 "prod_pods": 1,
 "tenant_count": 3,
 "pool": "system-ondemand",
 "tenant_kinds": [
  "dev",
  "other",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-runners</code></summary>

```json
{
 "containers_without_memory_limit": 1,
 "prod": false,
 "pods": 1,
 "cpu_p95_7d": 0.471,
 "memory_p95_7d_gb": 1.96,
 "has_limitrange": false,
 "namespace": "arc-runners",
 "kind": "ci",
 "containers_without_requests": 1
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.argocd/argocd-server</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/argocd-server"
 ],
 "name": "k8s-app-svc-74c4dcbda2",
 "deregistration_delay_s": 300,
 "target": "argocd/argocd-server",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-admin-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-admin-frontend"
 ],
 "name": "k8s-app-svc-ae7a7a06ff",
 "deregistration_delay_s": 300,
 "target": "dev-app-n/app-n-admin-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-backend"
 ],
 "name": "k8s-app-svc-0987e78003",
 "deregistration_delay_s": 300,
 "target": "dev-app-n/app-n-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-n/app-n-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "name": "k8s-app-svc-133751726c",
 "deregistration_delay_s": 300,
 "target": "dev-app-n/app-n-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-t/app-t-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-t-backend"
 ],
 "name": "k8s-app-svc-b347218b4f",
 "deregistration_delay_s": 300,
 "target": "dev-app-t/app-t-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.dev-app-t/app-t-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-t-frontend"
 ],
 "name": "k8s-app-svc-e9834ca5fe",
 "deregistration_delay_s": 300,
 "target": "dev-app-t/app-t-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.middleware/kafka-ui</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/kafka-ui"
 ],
 "name": "k8s-app-svc-0a6256c8b2",
 "deregistration_delay_s": 300,
 "target": "middleware/kafka-ui",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.middleware/redis-insight</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/redis-insight"
 ],
 "name": "k8s-app-svc-e7e7fd218a",
 "deregistration_delay_s": 300,
 "target": "middleware/redis-insight",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/kube-prometheus-stack-grafana"
 ],
 "name": "k8s-app-svc-af0f3aa6c7",
 "deregistration_delay_s": 300,
 "target": "monitoring/kube-prometheus-stack-grafana",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.monitoring/vmauth</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/vmauth"
 ],
 "name": "k8s-app-svc-e07e5153ee",
 "deregistration_delay_s": 300,
 "target": "monitoring/vmauth",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-r/app-r</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-r"
 ],
 "name": "k8s-app-svc-e238817282",
 "deregistration_delay_s": 300,
 "target": "prod-app-r/app-r",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-ai</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-q-ai"
 ],
 "name": "k8s-app-svc-fc2d368787",
 "deregistration_delay_s": 300,
 "target": "prod-app-q/app-q-ai",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-q-backend"
 ],
 "name": "k8s-app-svc-bb495c72c8",
 "deregistration_delay_s": 300,
 "target": "prod-app-q/app-q-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-studio</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-q-studio"
 ],
 "name": "k8s-app-svc-57e5adf3bf",
 "deregistration_delay_s": 300,
 "target": "prod-app-q/app-q-studio",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-q/app-q-web</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-q-web"
 ],
 "name": "k8s-app-svc-022a51fc31",
 "deregistration_delay_s": 300,
 "target": "prod-app-q/app-q-web",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-admin</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-o-admin"
 ],
 "name": "k8s-app-svc-37417ab44f",
 "deregistration_delay_s": 300,
 "target": "prod-app-o/app-o-admin",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-ai</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-o-ai"
 ],
 "name": "k8s-app-svc-b22674073c",
 "deregistration_delay_s": 300,
 "target": "prod-app-o/app-o-ai",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-o-backend"
 ],
 "name": "k8s-app-svc-89a3732998",
 "deregistration_delay_s": 300,
 "target": "prod-app-o/app-o-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-o/app-o-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-o-frontend"
 ],
 "name": "k8s-app-svc-032c25d752",
 "deregistration_delay_s": 300,
 "target": "prod-app-o/app-o-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-l-backend"
 ],
 "name": "k8s-app-svc-8c88bb317a",
 "deregistration_delay_s": 300,
 "target": "prod-app-l-backend/app-l-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-l-backend/app-l-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-l-frontend"
 ],
 "name": "k8s-app-svc-9726e5b1d3",
 "deregistration_delay_s": 300,
 "target": "prod-app-l-backend/app-l-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-p/app-p-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-p-backend"
 ],
 "name": "k8s-app-svc-f68effe430",
 "deregistration_delay_s": 300,
 "target": "prod-app-p/app-p-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-p/app-p-web</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-p-web"
 ],
 "name": "k8s-app-svc-194ae69849",
 "deregistration_delay_s": 300,
 "target": "prod-app-p/app-p-web",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-admin-frontend"
 ],
 "name": "k8s-app-svc-d0c066d282",
 "deregistration_delay_s": 300,
 "target": "prod-app-n/app-n-admin-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-backend"
 ],
 "name": "k8s-app-svc-7df87a92cc",
 "deregistration_delay_s": 300,
 "target": "prod-app-n/app-n-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-n/app-n-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-n-frontend"
 ],
 "name": "k8s-app-svc-36f816b829",
 "deregistration_delay_s": 300,
 "target": "prod-app-n/app-n-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.app-s-prod/app-s-backend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-s-backend"
 ],
 "name": "k8s-app-svc-bea446d347",
 "deregistration_delay_s": 300,
 "target": "app-s-prod/app-s-backend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.app-s-prod/app-s-frontend</code></summary>

```json
{
 "backend_prestop": false,
 "lb_type": "application",
 "workloads": [
  "deployment/app-s-frontend"
 ],
 "name": "k8s-app-svc-e72ef00971",
 "deregistration_delay_s": 300,
 "target": "app-s-prod/app-s-frontend",
 "backend_grace_s": 30
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/argocd/argocd-server</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "deploy.my-cluster"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/argocd/argocd-server"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-m/app-m-admin</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "admin-dev.example-b.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/dev-app-m/app-m-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-o/app-o-admin</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "admin-dev.example-d.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/dev-app-o/app-o-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-n/app-n-admin-frontend</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "admin-dev.example-c.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/dev-app-n/app-n-admin-frontend"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-m/app-m-admin</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "canary-admin.example-b.ai",
  "admin.example-b.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/prod-app-m/app-m-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-o/app-o-admin</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "admin.example-d.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/prod-app-o/app-o-admin"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-n/app-n-admin-frontend</code></summary>

```json
{
 "admin_like": true,
 "tls": true,
 "hosts": [
  "admin.example-c.ai"
 ],
 "type": "ingress",
 "has_auth_hint": false,
 "scheme": "internet-facing",
 "target": "ingress/prod-app-n/app-n-admin-frontend"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-m/app-m-backend</code></summary>

```json
{
 "hosts": [
  "canary-api.example-b.ai",
  "api.example-b.ai"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 94891.0,
  "requests_24h_equiv": 94891.0,
  "rps_avg": 1.098,
  "errors_5xx": 663.0,
  "errors_ratio": 0.00699,
  "p95_s_max_1h": 4.4754,
  "p95_s_avg": 0.2728,
  "p95_s_weighted": 0.6062,
  "p95_s_last_1h": 0.0496,
  "p95_s_last_at": "2026-11-05T07:20:00+00:00",
  "requests_last_1h": 2047.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-d65740e6d5"
  ]
 },
 "target": "prod-app-m/app-m-backend"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-m/app-m-frontend</code></summary>

```json
{
 "hosts": [
  "canary.example-b.ai",
  "www.example-b.ai",
  "example-b.ai"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 54991.0,
  "requests_24h_equiv": 54991.0,
  "rps_avg": 0.636,
  "errors_5xx": 80.0,
  "errors_ratio": 0.00145,
  "p95_s_max_1h": 0.5922,
  "p95_s_avg": 0.269,
  "p95_s_weighted": 0.2744,
  "p95_s_last_1h": 0.4849,
  "p95_s_last_at": "2026-11-05T07:20:00+00:00",
  "requests_last_1h": 3504.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-e87721a9c3"
  ]
 },
 "target": "prod-app-m/app-m-frontend"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-n/app-n-frontend</code></summary>

```json
{
 "hosts": [
  "example-c.ai",
  "www.example-c.ai"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 9938.0,
  "requests_24h_equiv": 9938.0,
  "rps_avg": 0.115,
  "errors_5xx": 26.0,
  "errors_ratio": 0.00262,
  "p95_s_max_1h": 2.398,
  "p95_s_avg": 0.3382,
  "p95_s_weighted": 0.6037,
  "p95_s_last_1h": 0.3458,
  "p95_s_last_at": "2026-11-05T07:20:00+00:00",
  "requests_last_1h": 340.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 1.0,
  "unhealthy_now": 1,
  "target_groups": [
   "k8s-app-svc-36f816b829"
  ]
 },
 "target": "prod-app-n/app-n-frontend"
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "hosts": [
  "monitor.my-cluster"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 54.0,
  "requests_24h_equiv": 54.0,
  "rps_avg": 0.001,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 5.7888,
  "p95_s_avg": 1.1781,
  "p95_s_weighted": 2.8008,
  "p95_s_last_1h": 0.0232,
  "p95_s_last_at": "2026-11-05T03:20:00+00:00",
  "requests_last_1h": 6.0,
  "hours_since_requests": 4,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-af0f3aa6c7"
  ]
 },
 "target": "monitoring/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-q/app-q-ai</code></summary>

```json
{
 "hosts": [
  "app-q-ai.my-cluster"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 21.0,
  "requests_24h_equiv": 21.0,
  "rps_avg": 0.0,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 2.6742,
  "p95_s_avg": 2.221,
  "p95_s_weighted": 2.2443,
  "p95_s_last_1h": 2.1485,
  "p95_s_last_at": "2026-11-05T07:20:00+00:00",
  "requests_last_1h": 14.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-app-svc-fc2d368787"
  ]
 },
 "target": "prod-app-q/app-q-ai"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.arc-runners/self-hosted-arm64-8msc5-runner</code></summary>

```json
{
 "not_ready_minutes_24h": 16,
 "worst_pod": "self-hosted-arm64-8msc5-runner-4248d",
 "workload": "arc-runners/self-hosted-arm64-8msc5-runner",
 "unhealthy_events": 0,
 "min_ready_ratio_24h": 0.9888,
 "pods_below_99": 1
}
```

</details>
<details><summary><code>vpccni.ec2-api-errors.node-1-62</code></summary>

```json
{
 "metrics": {
  "available": true,
  "assigned": 16,
  "total": 27,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 27,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 20,
  "ec2_api_errors_by_api": {
   "CreateNetworkInterface": 8,
   "DeleteNetworkInterface": 12
  },
  "per_eni": {
   "eni-0123456789abcdef0": 1,
   "eni-0123456789abcdef0": 8,
   "eni-0123456789abcdef0": 7
  }
 },
 "ec2_api_errors": 20,
 "node": "node-1-62",
 "metrics_available": true
}
```

</details>
<details><summary><code>vpccni.ec2-api-errors.node-2-158</code></summary>

```json
{
 "metrics": {
  "available": true,
  "assigned": 2,
  "total": 28,
  "eni_allocated": 2,
  "eni_max": 4,
  "ip_max": 56,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 11,
  "ec2_api_errors_by_api": {
   "CreateNetworkInterface": 11
  },
  "per_eni": {
   "eni-0123456789abcdef0": 2,
   "eni-0123456789abcdef0": 0
  }
 },
 "ec2_api_errors": 11,
 "node": "node-2-158",
 "metrics_available": true
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "request_ratio": 0.009,
 "prod_without_request": 33,
 "emptydir_without_sizelimit_prod": [
  "prod-app-q/statefulset/app-q-backend-postgresql",
  "prod-app-l-backend/deployment/app-l-embedding-server",
  "prod-app-l-backend/deployment/tts-proxy",
  "prod-app-p/deployment/app-p-backend",
  "prod-app-p/statefulset/app-p-postgresql",
  "app-s-prod/statefulset/app-s-backend-postgresql"
 ],
 "with_request": 1,
 "emptydir_without_sizelimit": 21,
 "containers": 111
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "replicasets_zero": 353,
 "replicasets_total": 418,
 "revision_history_limits": {
  "10": 61,
  "3": 6
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-139</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-1-139",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-139",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 42.3,
  "loadavg": "0.62 0.56 0.68",
  "nproc": 4,
  "mem_total_gb": 30.8,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 2,
  "kubelet_rss_mb": 143,
  "containerd_rss_mb": 109,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-241</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-1-241",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-241",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 27.8,
  "loadavg": "0.03 0.06 0.05",
  "nproc": 2,
  "mem_total_gb": 1.9,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 74,
  "containerd_rss_mb": 56,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-62</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-1-62",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-62",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 10.1,
  "loadavg": "0.25 0.19 1.02",
  "nproc": 2,
  "mem_total_gb": 15.3,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 1,
  "kubelet_rss_mb": 111,
  "containerd_rss_mb": 87,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-2-135</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-2-135",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-2-135",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 27.1,
  "loadavg": "0.61 0.32 0.17",
  "nproc": 2,
  "mem_total_gb": 7.6,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 111,
  "containerd_rss_mb": 80,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-2-158</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-2-158",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-2-158",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 0.1,
  "loadavg": "0.08 0.04 0.03",
  "nproc": 4,
  "mem_total_gb": 7.6,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 92,
  "containerd_rss_mb": 62,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.cgroup-v1.node-2-218</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "node": "node-2-218",
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-2-218",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 27.8,
  "loadavg": "0.00 0.02 0.05",
  "nproc": 2,
  "mem_total_gb": 3.7,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 84,
  "containerd_rss_mb": 80,
  "k3s_rss_mb": null
 }
}
```

</details>
<details><summary><code>node.os-not-collected.node-1-117</code></summary>

```json
{
 "node": "node-1-117",
 "reason": "node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore"
}
```

</details>
<details><summary><code>node.os-not-collected.node-2-60</code></summary>

```json
{
 "node": "node-2-60",
 "reason": "node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": true,
 "name": "app-l-backend",
 "current_cpu_utilization": 0,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "prod-app-l-backend",
 "days_since_last_scale": 20.1,
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": true,
 "name": "app-l-frontend",
 "current_cpu_utilization": 1,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "prod-app-l-backend",
 "days_since_last_scale": 87.4,
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-frontend",
 "keda_owned": false
}
```

</details>
<details><summary><code>storage.legacy-intree-storageclass.gp2</code></summary>

```json
{
 "key": null,
 "item": {
  "default": false,
  "parameters": {
   "fsType": "ext4",
   "type": "gp2"
  },
  "name": "gp2",
  "provisioner": "kubernetes.io/aws-ebs"
 }
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-117</code></summary>

```json
{
 "cpu_limit_overcommit": 3.37,
 "containers_without_memory_limit": 3,
 "node": "node-1-117",
 "separation_possible": true,
 "dev_pods": 2,
 "dev_namespaces": [
  "dev-app-o",
  "dev-app-t"
 ],
 "memory_limit_overcommit": 1.68,
 "shares_dev_prod": true,
 "prod_namespaces": [
  "prod-app-o",
  "app-s-prod"
 ],
 "prod_pods": 2,
 "pool": "system_core-20251217040546303900000001"
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-139</code></summary>

```json
{
 "cpu_limit_overcommit": 6.99,
 "containers_without_memory_limit": 0,
 "node": "node-1-139",
 "separation_possible": true,
 "dev_pods": 12,
 "dev_namespaces": [
  "dev-app-m",
  "dev-app-o",
  "dev-app-n",
  "dev-app-t"
 ],
 "memory_limit_overcommit": 1.55,
 "shares_dev_prod": true,
 "prod_namespaces": [
  "prod-app-r",
  "prod-app-m",
  "prod-app-o",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "prod_pods": 20,
 "pool": "default"
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-2-218</code></summary>

```json
{
 "cpu_limit_overcommit": 1.55,
 "containers_without_memory_limit": 2,
 "node": "node-2-218",
 "separation_possible": true,
 "dev_pods": 1,
 "dev_namespaces": [
  "dev-app-t"
 ],
 "memory_limit_overcommit": 1.55,
 "shares_dev_prod": true,
 "prod_namespaces": [
  "prod-app-q"
 ],
 "prod_pods": 1,
 "pool": "system-ondemand"
}
```

</details>
<details><summary><code>albctl.aws-api-churn.cluster</code></summary>

```json
{
 "aws_api_retries_avg": 0.0,
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
 "metrics_available": true,
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
 "aws_api_calls_total": 241005,
 "rest_client_429_503": 126
}
```

</details>
<details><summary><code>alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "cluster_status": "disabled",
 "cluster_peers": 0,
 "ready": 1,
 "replicas": 1,
 "present": true,
 "data_retention": "120h",
 "storage": "emptyDir",
 "target": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager"
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "notifications_configured": false,
 "applications_prod": 8,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "prod_tracking_moving_ref": [
  "argocd/application/app-r-prod",
  "argocd/application/app-q-prod",
  "argocd/application/app-m-prod",
  "argocd/application/app-o-prod",
  "argocd/application/app-s-prod",
  "argocd/application/app-l-backend-prod",
  "argocd/application/app-p-prod",
  "argocd/application/app-n-prod"
 ],
 "applications_prod": 8,
 "ignore_differences_apps": 3
}
```

</details>
<details><summary><code>argocd.version-eol.cluster</code></summary>

```json
{
 "version_major": 2,
 "components": {
  "applicationset-controller": "1/1",
  "dex-server": "1/1",
  "notifications-controller": "1/1",
  "redis": "1/1",
  "repo-server": "1/1",
  "server": "1/1",
  "application-controller": "1/1"
 },
 "version": "2.13.0"
}
```

</details>
<details><summary><code>controlplane.apiserver-slow-traces.cluster</code></summary>

```json
{
 "slow_traces_total": 165,
 "slow_traces": [
  {
   "op": "List",
   "count": 153
  },
  {
   "op": "Call conversion webhook",
   "count": 8
  },
  {
   "op": "Update",
   "count": 3
  },
  {
   "op": "Patch",
   "count": 1
  }
 ]
}
```

</details>
<details><summary><code>coredns.aaaa-noise.cluster</code></summary>

```json
{
 "qps_total": 78.46,
 "cluster_ipv6": false,
 "aaaa_ratio": 0.5,
 "metrics_available": true
}
```

</details>
<details><summary><code>cost.idle-node.node-2-158</code></summary>

```json
{
 "node": "node-2-158",
 "cpu_p95_ratio": 0.02329421451616407,
 "instance_type": "c6gn.xlarge",
 "monthly_usd": 47.74,
 "pool": "build-arm64",
 "memory_p95_ratio": 0.1834216996108511
}
```

</details>
<details><summary><code>ebscsi.controller-metrics-disabled.cluster</code></summary>

```json
{
 "api_throttles_24h": null,
 "api_errors_24h": {},
 "controller_present": true,
 "version": "1.37.0",
 "controller_metrics_enabled": false,
 "controller_metrics_series": 0,
 "addon_version": "v1.37.0-eksbuild.1"
}
```

</details>
<details><summary><code>ecr.no-lifecycle-policy.ecr/registry/<account></code></summary>

```json
{
 "monthly_usd": 48.7,
 "repos_no_lifecycle_gib": 10.9,
 "images": 887,
 "total_gib": 453.6,
 "untagged": 253,
 "attestations": 176,
 "repositories": 43,
 "repos_no_lifecycle": [
  "app-n",
  "bitnami/kafka",
  "ecr-app-s-postgresql-pgvector",
  "bitnami/mysql"
 ],
 "account": "<account>"
}
```

</details>
<details><summary><code>ecr.no-replication.ecr/registry/<account></code></summary>

```json
{
 "repos_mutable_prod": [
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-r-eks-prod",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-o-ai-prod",
  "ecr-app-o-admin-eks-prod",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-backend-eks-prod",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ],
 "repos_scan_off_prod": [
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-r-eks-prod",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-o-admin-eks-prod",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ],
 "total_gib": 453.6,
 "replication_rules": 0,
 "account": "<account>"
}
```

</details>
<details><summary><code>ecr.tag-mutable-prod.ecr/registry/<account></code></summary>

```json
{
 "repos_mutable_prod": [
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-r-eks-prod",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-o-ai-prod",
  "ecr-app-o-admin-eks-prod",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-backend-eks-prod",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ],
 "repos_with_latest_tag": [],
 "images_in_use": 95,
 "digest_pinned": 2,
 "repositories": 43,
 "account": "<account>",
 "repos_mutable": [
  "app-n",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-o-admin-dev",
  "ecr-app-r-eks-prod",
  "bitnami/kafka",
  "ecr-app-q-backend-eks-prod",
  "ecr-app-q-web-eks-prod",
  "ecr-app-p-postgresql-prod",
  "ecr-app-m-frontend-prod",
  "app-n-admin-frontend",
  "ecr-app-m-frontend-dev",
  "ecr-app-m-admin-eks-prod",
  "ecr-app-s-postgresql-pgvector",
  "ecr-app-q-postgresql-prod",
  "app-n-backend",
  "app-n-frontend",
  "ecr-app-m-admin-dev",
  "ecr-app-m-backend-dev",
  "ecr-app-m-api-dev",
  "ecr-app-m-backend-eks-prod",
  "ecr-app-m-api-eks-prod",
  "ecr-app-o-frontend-eks-prod",
  "ecr-app-o-backend-dev",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-o-ai-prod",
  "ecr-app-o-admin-eks-prod",
  "app-t-backend",
  "app-t-frontend",
  "ecr-app-l-embedding-eks-prod",
  "app-n-admin-frontend-prod",
  "app-n-frontend-prod",
  "app-n-backend-prod",
  "ecr-app-m-frontend-eks-prod",
  "ecr-app-o-frontend-dev",
  "ecr-app-o-backend-eks-prod",
  "ecr-app-o-ai-dev",
  "ecr-app-l-backend-eks-prod",
  "ecr-app-l-frontend-eks-prod",
  "ecr-app-q-ai-eks-prod",
  "ecr-app-q-studio-eks-prod",
  "ecr-app-p-web-eks-prod",
  "ecr-app-p-backend-eks-prod"
 ]
}
```

</details>
<details><summary><code>ecr.untagged-images.ecr/registry/<account></code></summary>

```json
{
 "images": 887,
 "untagged": 253,
 "attestations": 176,
 "repositories": 43,
 "account": "<account>"
}
```

</details>
<details><summary><code>eso.version-old.cluster</code></summary>

```json
{
 "pushsecrets": 0,
 "externalsecrets": 47,
 "version": "0.9.13"
}
```

</details>
<details><summary><code>grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "ingress_hosts": [
  "monitor.my-cluster"
 ],
 "database": "ok",
 "major": 10,
 "version": "10.2.3",
 "present": true,
 "stats": {
  "totals_dashboard": 28,
  "totals_datasource": 4,
  "total_users": 1,
  "active_users": 1,
  "totals_alert_rules": 0
 },
 "target": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "always_pull_with_tag": true,
 "registry": "ghcr.io",
 "workload": "keda/deployment/keda-admission-webhooks",
 "container": "keda-admission-webhooks",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.17.2",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "always_pull_with_tag": true,
 "registry": "ghcr.io",
 "workload": "keda/deployment/keda-operator-metrics-apiserver",
 "container": "keda-operator-metrics-apiserver",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.17.2",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator</code></summary>

```json
{
 "always_pull_with_tag": true,
 "registry": "ghcr.io",
 "workload": "keda/deployment/keda-operator",
 "container": "keda-operator",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda:2.17.2",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent</code></summary>

```json
{
 "always_pull_with_tag": true,
 "registry": "<account>.dkr.ecr.us-east-1.amazonaws.com",
 "workload": "kube-system/daemonset/aws-node",
 "container": "aws-eks-nodeagent",
 "pull_policy": "Always",
 "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init</code></summary>

```json
{
 "always_pull_with_tag": true,
 "registry": "<account>.dkr.ecr.us-east-1.amazonaws.com",
 "workload": "kube-system/daemonset/aws-node",
 "container": "aws-vpc-cni-init",
 "pull_policy": "Always",
 "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1",
 "tag_kind": "tag"
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
 "webhooks": 18,
 "zero_object_count": 26,
 "count": 47
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
 "spot_to_spot_consolidation": false,
 "drift_enabled": true,
 "nodeclaims_terminated_by_reason": {
  "expiration": 6,
  "emptiness": 317,
  "interruption": 261,
  "consolidation": 281
 }
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
 "scale_to_zero": [
  "prod-app-l-backend/scaledobject/app-l-file-worker",
  "prod-app-l-backend/scaledobject/app-l-graph-worker"
 ],
 "fallback_active": [],
 "never_active_14d": [
  "dev-app-o/scaledobject/app-o-ai-kafka-lag"
 ],
 "not_ready": []
}
```

</details>
<details><summary><code>kubeproxy.conntrack-invalid-drops.cluster</code></summary>

```json
{
 "external_traffic_local": 0,
 "ct_invalid_dropped_1h": 1248,
 "no_local_endpoint_services": 0,
 "metrics_available": true
}
```

</details>
<details><summary><code>loki.version-old.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "major": 2,
 "version": "2.6.1",
 "present": true,
 "storage": "emptyDir",
 "retention_applied": false,
 "compactor_running": 1.0,
 "target": "monitoring/statefulset/loki-stack"
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
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
 ],
 "rules_total": 141,
 "never_fired_count": 128,
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
 ]
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
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
 ],
 "namespaces_with_saturation_metrics": [
  "default",
  "kube-system",
  "middleware",
  "monitoring"
 ],
 "ingresses": 40
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
  "logs/node/node-1-139/containerd-24h.log",
  "logs/node/node-1-139/kubelet-24h.log",
  "logs/node/node-1-241/containerd-24h.log",
  "logs/node/node-1-241/kubelet-24h.log",
  "logs/node/node-1-62/containerd-24h.log",
  "logs/node/node-1-62/kubelet-24h.log",
  "logs/node/node-2-158/containerd-24h.log",
  "logs/node/node-2-158/kubelet-24h.log",
  "logs/node/node-2-218/containerd-24h.log",
  "logs/node/node-2-218/kubelet-24h.log",
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
   "pattern": "node:node-2-158 | time=\"<ts>\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods\" error=\"cni c",
   "count": 2,
   "files": {
    "logs/node/node-2-158/containerd-24h.log": 2
   },
   "sample": "2026-11-05T06:50:18+0000 node-2-158 containerd[843]: time=\"2026-11-05T06:50:18.831612554Z\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods"
  },
  {
   "pattern": "node:node-2-158 | \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"node-<n>\\\" not fou",
   "count": 2,
   "files": {
    "logs/node/node-2-158/kubelet-24h.log": 2
   },
   "sample": "2026-11-05T06:50:28+0000 node-2-158 kubelet[1540]: E1105 06:50:28.847894    1540 eviction_manager.go:292] \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"node-2-158."
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
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"49c3df5ef5da35e98fe0dd4ae2e4e3b3a3a206cb8e7932ff7da3baaccfbd0b1c\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-04T10:05:51+0000 node-1-139 containerd[1461]: time=\"2026-11-04T10:05:51.014644680Z\" level=error msg=\"ContainerStatus for \\\"49c3df5ef5da35e98fe0dd4ae2e4e3b3a3a206cb8e7932ff7da3baaccfbd0b1c\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"d21bfec6661abdc6830281d5e12eea11710af0b5aaa0fe3b60667f583942ebe3\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-05T02:35:51+0000 node-1-139 containerd[1461]: time=\"2026-11-05T02:35:51.251299260Z\" level=error msg=\"ContainerStatus for \\\"d21bfec6661abdc6830281d5e12eea11710af0b5aaa0fe3b60667f583942ebe3\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"451879ce04a5a050e80ba066b669b770628fb0a6d9a4e75c3706c96ed75f6aaa\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-05T05:02:50+0000 node-1-139 containerd[1461]: time=\"2026-11-05T05:02:50.508196485Z\" level=error msg=\"ContainerStatus for \\\"451879ce04a5a050e80ba066b669b770628fb0a6d9a4e75c3706c96ed75f6aaa\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"c7d348db476208861c11c8a2d96978f344aa5ba268f20cd85eae55995220f97b\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-05T05:44:50+0000 node-1-139 containerd[1461]: time=\"2026-11-05T05:44:50.571423009Z\" level=error msg=\"ContainerStatus for \\\"c7d348db476208861c11c8a2d96978f344aa5ba268f20cd85eae55995220f97b\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"65c000bd3618ac5b99a4a93326265a4a9d70f6c7139e909582f361454ffef1b0\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-05T05:50:55+0000 node-1-139 containerd[1461]: time=\"2026-11-05T05:50:55.275591904Z\" level=error msg=\"ContainerStatus for \\\"65c000bd3618ac5b99a4a93326265a4a9d70f6c7139e909582f361454ffef1b0\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"eb21c65d106f60d00842be72d0033f9df69dc71401deac7d10048951dbd940dd\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-139/containerd-24h.log": 1
   },
   "sample": "2026-11-05T06:56:50+0000 node-1-139 containerd[1461]: time=\"2026-11-05T06:56:50.928582913Z\" level=error msg=\"ContainerStatus for \\\"eb21c65d106f60d00842be72d0033f9df69dc71401deac7d10048951dbd940dd\\\" failed\""
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"49c3df5e",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-04T10:05:51+0000 node-1-139 kubelet[1593]: E1104 10:05:51.014865    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"d21bfec6",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T02:35:51+0000 node-1-139 kubelet[1593]: E1105 02:35:51.251415    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"451879ce",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T05:02:50+0000 node-1-139 kubelet[1593]: E1105 05:02:50.508457    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"c7d348db",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T05:44:50+0000 node-1-139 kubelet[1593]: E1105 05:44:50.571507    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"65c000bd",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T05:50:55+0000 node-1-139 kubelet[1593]: E1105 05:50:55.275698    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-139 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"eb21c65d",
   "count": 1,
   "files": {
    "logs/node/node-1-139/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T06:56:50+0000 node-1-139 kubelet[1593]: E1105 06:56:50.928667    1593 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  },
  {
   "pattern": "node:node-1-241 | Error while processing event (\"/sys/fs/cgroup/devices/kubepods.slice/kubepods-besteffort.slice/kubepods-besteffort-pod339f654f_924a_43ab_893",
   "count": 1,
   "files": {
    "logs/node/node-1-241/kubelet-24h.log": 1
   },
   "sample": "2026-11-04T11:00:00+0000 node-1-241 kubelet[3725]: W1104 11:00:00.221690    3725 watcher.go:93] Error while processing event (\"/sys/fs/cgroup/devices/kubepods.slice/kubepods-besteffort.slice/kubepods-beste"
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"e3fe2f0a26e8fd1cabf1078bedfac56f5748ac70cb4f4c326325953584bc1883\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-04T09:27:46+0000 node-1-62 containerd[1410]: time=\"2026-11-04T09:27:46.912970945Z\" level=error msg=\"ContainerStatus for \\\"e3fe2f0a26e8fd1cabf1078bedfac56f5748ac70cb4f4c326325953584bc1883\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"5d0178801191d711b6c5ac1e63d41c228f4aa830c168ea5cdf10047d9d928140\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-04T12:24:51+0000 node-1-62 containerd[1410]: time=\"2026-11-04T12:24:51.394233320Z\" level=error msg=\"ContainerStatus for \\\"5d0178801191d711b6c5ac1e63d41c228f4aa830c168ea5cdf10047d9d928140\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"f296267e9234d46d7bbf83d1f0b4fe207940302086682593163e553f9f8f96a9\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-05T02:47:52+0000 node-1-62 containerd[1410]: time=\"2026-11-05T02:47:52.366530339Z\" level=error msg=\"ContainerStatus for \\\"f296267e9234d46d7bbf83d1f0b4fe207940302086682593163e553f9f8f96a9\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"b2926054ac6be908e21a70b587458c9300c2af55e835e3bbedbe966c7e6eef80\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-05T03:19:54+0000 node-1-62 containerd[1410]: time=\"2026-11-05T03:19:54.545592590Z\" level=error msg=\"ContainerStatus for \\\"b2926054ac6be908e21a70b587458c9300c2af55e835e3bbedbe966c7e6eef80\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"504e922981dcdd7c23431189569f44c2db1d53adeaf9ef6406b6eae782bccf41\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-05T05:50:52+0000 node-1-62 containerd[1410]: time=\"2026-11-05T05:50:52.234692276Z\" level=error msg=\"ContainerStatus for \\\"504e922981dcdd7c23431189569f44c2db1d53adeaf9ef6406b6eae782bccf41\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"64b8cb3dd068c9a644cab358f6d4a4bbc4ae3d64eff7b67a7deebdcba26fb82d\\\" failed\" error=\"rpc err",
   "count": 1,
   "files": {
    "logs/node/node-1-62/containerd-24h.log": 1
   },
   "sample": "2026-11-05T06:09:42+0000 node-1-62 containerd[1410]: time=\"2026-11-05T06:09:42.071673180Z\" level=error msg=\"ContainerStatus for \\\"64b8cb3dd068c9a644cab358f6d4a4bbc4ae3d64eff7b67a7deebdcba26fb82d\\\" failed\" "
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"e3fe2f0a",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-04T09:27:46+0000 node-1-62 kubelet[1541]: E1104 09:27:46.913212    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"5d017880",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-04T12:24:51+0000 node-1-62 kubelet[1541]: E1104 12:24:51.394309    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"f296267e",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T02:47:52+0000 node-1-62 kubelet[1541]: E1105 02:47:52.366608    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"b2926054",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T03:19:54+0000 node-1-62 kubelet[1541]: E1105 03:19:54.545663    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"504e9229",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T05:50:52+0000 node-1-62 kubelet[1541]: E1105 05:50:52.234770    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-1-62 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"64b8cb3d",
   "count": 1,
   "files": {
    "logs/node/node-1-62/kubelet-24h.log": 1
   },
   "sample": "2026-11-05T06:09:42+0000 node-1-62 kubelet[1541]: E1105 06:09:42.071874    1541 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to"
  },
  {
   "pattern": "node:node-2-158 | time=\"<ts>\" level=error msg=\"get state for 40de41eb634e79045491651463b174121f5bf659de070b31789600b4fa437cf0\" error=\"context deadline exceede",
   "count": 1,
   "files": {
    "logs/node/node-2-158/containerd-24h.log": 1
   },
   "sample": "2026-11-05T06:50:38+0000 node-2-158 containerd[1402]: time=\"2026-11-05T06:50:38.196521709Z\" level=error msg=\"get state for 40de41eb634e79045491651463b174121f5bf659de070b31789600b4fa437cf0\" error=\"context d"
  }
 ],
 "error_lines_unclassified": 56,
 "lines_scanned": 23448
}
```

</details>
<details><summary><code>observability.unstructured-logs.argocd</code></summary>

```json
{
 "json_lines_1h": 0,
 "lines_1h": 17411,
 "json_ratio": 0.0,
 "namespace": "argocd"
}
```

</details>
<details><summary><code>observability.unstructured-logs.dev-app-n</code></summary>

```json
{
 "json_lines_1h": 0,
 "lines_1h": 59543,
 "json_ratio": 0.0,
 "namespace": "dev-app-n"
}
```

</details>
<details><summary><code>observability.unstructured-logs.monitoring</code></summary>

```json
{
 "json_lines_1h": 0,
 "lines_1h": 11127,
 "json_ratio": 0.0,
 "namespace": "monitoring"
}
```

</details>
<details><summary><code>observability.unstructured-logs.app-s-prod</code></summary>

```json
{
 "json_lines_1h": 0,
 "lines_1h": 946936,
 "json_ratio": 0.0,
 "namespace": "app-s-prod"
}
```

</details>
<details><summary><code>prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "ready": 1,
 "replicas": 1,
 "restarts": 1,
 "present": true,
 "start_time": "2026-10-06T12:32:07.180790214Z",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "present": true,
 "major": 2,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "version": "2.49.1"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-m/statefulset/app-m-backend-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-o/statefulset/app-o-backend-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-n/statefulset/app-n-backend-dev-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-t/statefulset/app-t-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-t/statefulset/app-t-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-t/statefulset/app-t-postgres:postgres</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "dev-app-t/statefulset/app-t-postgres",
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_t -d app_t_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/aws-node:aws-node</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 1
 },
 "workload": "kube-system/daemonset/aws-node",
 "container": "aws-node",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 60
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar</code></summary>

```json
{
 "readiness": null,
 "workload": "kube-system/daemonset/ebs-csi-node-windows",
 "container": "node-driver-registrar",
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar</code></summary>

```json
{
 "readiness": null,
 "workload": "kube-system/daemonset/ebs-csi-node",
 "container": "node-driver-registrar",
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.middleware/statefulset/redis-master:redis</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "sh -c /health/ping_readiness_local.sh 1",
  "port": null,
  "timeout_s": 2,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "workload": "middleware/statefulset/redis-master",
 "container": "redis",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "sh -c /health/ping_liveness_local.sh 5",
  "port": null,
  "timeout_s": 6,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-q/statefulset/app-q-backend-postgresql:postgresql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-q\" -d \"dbname=app-q\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "prod-app-q/statefulset/app-q-backend-postgresql",
 "container": "postgresql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-q\" -d \"dbname=app-q\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-m/statefulset/app-m-backend-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-m/statefulset/app-m-backend-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-o/statefulset/app-o-backend-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-o/statefulset/app-o-backend-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-l-backend/deployment/app-l-file-worker:file-worker</code></summary>

```json
{
 "readiness": null,
 "workload": "prod-app-l-backend/deployment/app-l-file-worker",
 "container": "file-worker",
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.FileWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-l-backend/deployment/app-l-graph-worker:graph-worker</code></summary>

```json
{
 "readiness": null,
 "workload": "prod-app-l-backend/deployment/app-l-graph-worker",
 "container": "graph-worker",
 "flags": [
  "liveness exec (forks a process)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.GraphWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-p/statefulset/app-p-postgresql:postgresql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-p\" -d \"dbname=app-p\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "prod-app-p/statefulset/app-p-postgresql",
 "container": "postgresql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-p\" -d \"dbname=app-p\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-n/statefulset/app-n-backend-prod-mysql",
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 }
}
```

</details>
<details><summary><code>resilience.exec-probe.app-s-prod/statefulset/app-s-backend-postgresql:postgresql</code></summary>

```json
{
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-s-user\" -d \"dbname=app-s_tp\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "app-s-prod/statefulset/app-s-backend-postgresql",
 "container": "postgresql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "exec_probe": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-s-user\" -d \"dbname=app-s_tp\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 }
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-ai:ai</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-q/deployment/app-q-ai",
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "container": "ai",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-backend:backend</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-q/deployment/app-q-backend",
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "backend",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-studio:studio</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-q/deployment/app-q-studio",
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "container": "studio",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-q/deployment/app-q-web:web</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-q/deployment/app-q-web",
 "startup": null,
 "container": "web",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-admin:admin</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-admin",
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "admin",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-api:api</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-api",
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "api",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-backend:backend</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-backend",
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "backend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-m/deployment/app-m-frontend:frontend</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-m/deployment/app-m-frontend",
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "frontend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-l-backend/deployment/app-l-backend:backend</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-l-backend/deployment/app-l-backend",
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "backend",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-p/deployment/app-p-backend:backend</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-p/deployment/app-p-backend",
 "startup": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "container": "backend",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-p/deployment/app-p-web:web</code></summary>

```json
{
 "dependency_liveness": false,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "prod": true,
 "workload": "prod-app-p/deployment/app-p-web",
 "startup": null,
 "container": "web",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "serves_traffic": true,
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true
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
  "memory_request_p95_ratio_7d": 0.3109321594238281,
  "memory_p95_7d_bytes": 83465216.0,
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
  "memory_request_p95_ratio_7d": 0.20479583740234375,
  "memory_p95_7d_bytes": 54974464.0,
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
   "memory_request_p95_ratio_7d": 0.1577777862548828,
   "memory_p95_7d_bytes": 84706304.0,
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
  "memory_request_p95_ratio_7d": 0.23859367370605467,
  "memory_p95_7d_bytes": 1024752025.5999999,
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
 "current_cpu_utilization": 0,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "prod-app-l-backend",
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
 "current_cpu_utilization": 1,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "prod-app-l-backend",
 "cpu_only": true,
 "target": "prod-app-l-backend/deployment/app-l-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-m-admin",
 "current_cpu_utilization": 2,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-m",
 "days_since_last_scale": 168.8,
 "min": 1,
 "target": "dev-app-m/deployment/app-m-admin",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-m-api",
 "current_cpu_utilization": 11,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-m",
 "days_since_last_scale": 198.5,
 "min": 1,
 "target": "dev-app-m/deployment/app-m-api",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-m-backend",
 "current_cpu_utilization": 16,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-m",
 "days_since_last_scale": 69.3,
 "min": 1,
 "target": "dev-app-m/deployment/app-m-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-o-admin",
 "current_cpu_utilization": 6,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-o",
 "days_since_last_scale": 58.3,
 "min": 1,
 "target": "dev-app-o/deployment/app-o-admin",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-o-backend",
 "current_cpu_utilization": 11,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-o",
 "days_since_last_scale": 20.3,
 "min": 1,
 "target": "dev-app-o/deployment/app-o-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-o-frontend",
 "current_cpu_utilization": 28,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-o",
 "days_since_last_scale": 20.3,
 "min": 1,
 "target": "dev-app-o/deployment/app-o-frontend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-n-admin-frontend",
 "current_cpu_utilization": 2,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-n",
 "days_since_last_scale": 38.8,
 "min": 1,
 "target": "dev-app-n/deployment/app-n-admin-frontend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-n-backend",
 "current_cpu_utilization": 13,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-n",
 "days_since_last_scale": 42.8,
 "min": 1,
 "target": "dev-app-n/deployment/app-n-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-n/deployment/app-n-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9986111111111098,
 "max": 3,
 "prod": false,
 "name": "app-n-frontend",
 "current_cpu_utilization": 2,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-n",
 "days_since_last_scale": 3.3,
 "min": 1,
 "target": "dev-app-n/deployment/app-n-frontend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-t/deployment/app-t-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 3,
 "prod": false,
 "name": "app-t-backend",
 "current_cpu_utilization": 0,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-t",
 "days_since_last_scale": 22.4,
 "min": 1,
 "target": "dev-app-t/deployment/app-t-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-t/deployment/app-t-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "max": 2,
 "prod": false,
 "name": "app-t-frontend",
 "current_cpu_utilization": 2,
 "never_scaled_15d": true,
 "target_cpu_utilization": 70,
 "metric_types": [
  "cpu"
 ],
 "namespace": "dev-app-t",
 "days_since_last_scale": null,
 "min": 1,
 "target": "dev-app-t/deployment/app-t-frontend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-backend</code></summary>

```json
{
 "max": 3,
 "desired_changes_7d": 0.0,
 "has_behavior": false,
 "prod": true,
 "name": "app-l-backend",
 "namespace": "prod-app-l-backend",
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-backend",
 "keda_owned": false
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-l-backend/deployment/app-l-frontend</code></summary>

```json
{
 "max": 3,
 "desired_changes_7d": 0.0,
 "has_behavior": false,
 "prod": true,
 "name": "app-l-frontend",
 "namespace": "prod-app-l-backend",
 "min": 2,
 "target": "prod-app-l-backend/deployment/app-l-frontend",
 "keda_owned": false
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
 "cpu_limit_overcommit": 4.72,
 "containers_without_memory_limit": 0,
 "node": "node-1-62",
 "separation_possible": true,
 "dev_pods": 1,
 "dev_namespaces": [
  "dev-app-n"
 ],
 "memory_limit_overcommit": 0.88,
 "shares_dev_prod": true,
 "prod_namespaces": [
  "prod-app-q",
  "prod-app-m",
  "prod-app-l-backend",
  "prod-app-p",
  "prod-app-n",
  "app-s-prod"
 ],
 "prod_pods": 13,
 "pool": "default"
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-2-60</code></summary>

```json
{
 "cpu_limit_overcommit": 2.44,
 "containers_without_memory_limit": 2,
 "node": "node-2-60",
 "separation_possible": true,
 "dev_pods": 2,
 "dev_namespaces": [
  "dev-app-m",
  "dev-app-n"
 ],
 "memory_limit_overcommit": 1.49,
 "shares_dev_prod": true,
 "prod_namespaces": [
  "prod-app-m",
  "prod-app-n"
 ],
 "prod_pods": 2,
 "pool": "system_core-20251217040546303900000001"
}
```

</details>
<details><summary><code>traffic.alb-protection-off.k8s-shared-alb</code></summary>

```json
{
 "target_groups": 40,
 "deletion_protection": false,
 "type": "application",
 "name": "k8s-shared-alb",
 "access_logs": false
}
```

</details>
<details><summary><code>vpccni.metrics-unreadable.cluster</code></summary>

```json
{
 "nodes": 8,
 "metrics_unavailable_nodes": [
  "node-1-117",
  "node-2-60"
 ]
}
```

</details>

### 7-6. Tool notes (about kubegap itself)

1. tenancy.prod-without-quota 8개와 tenancy.tenant-without-limitrange.prod-app-l-backend가 2026-11-03 스냅샷과 이번 스냅샷 사이에서 warn에서 fail로 바뀌었어요. 근거 문자열은 사실상 같고(prod-app-p 'no ResourceQuota. Pods 3, CPU requests total 0.62 cores'), diff.json objects에 resourcequotas나 limitranges 변화가 없어요. 체크에 notes가 없고 CHANGELOG에도 기록이 없어서 diff가 이걸 클러스터 변화(changed, rule_known false)로 분류해요. 규칙 변경이었다면 notes에 적어 두는 게 좋아요.
2. controlplane.scheduler-unschedulable와 events.tracked-warning-reasons.FailedScheduling이 KEDA 0→N 확장 직후 Karpenter가 노드를 띄우는 동안의 정상 대기를 high fail로 잡아요. 수집 시점 Pending 0, 노드 준비 p50 58초(summary.json scaling.karpenter.latency_24h)인데도요. ScaledObject 대상이고 Karpenter가 있으면 낮추는 조건을 검토할 만해요.
3. observability.alerts-always-firing와 observability.alert-firing-stale이 EKS에서 KubeControllerManagerDown·KubeSchedulerDown을 medium fail로 내요. 관리형 컨트롤플레인이라 스크레이프 대상이 없어서 생기는 잘못 잡힌 알림인데, 분석 절차에는 그렇게 적혀 있지만 체크는 플랫폼을 보지 않아요.

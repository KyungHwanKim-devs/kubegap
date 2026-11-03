# kubegap 리포트 세부 — arn:aws:eks:us-east-1:<account>:cluster/my-cluster (`my-cluster`), full 모드

리포트의 참조용 절반입니다. `scripts/kubegap render-details` 가 스냅샷 파일과 `llm/` 의 LLM 조각으로 조립했습니다. 사람이 읽는 리포트는 옆의 `report.md` 입니다. 표 안의 데이터, 즉 체크 id·근거 문장·숫자는 영어 그대로입니다.

| 항목 | 값 |
|---|---|
| kube 컨텍스트 / 클러스터 | `my-cluster` / arn:aws:eks:us-east-1:<account>:cluster/my-cluster (eks, v1.32.13-eks-577a51e) |
| 실행 시각 / 모드 | 2026-11-03T11:17:15+09:00 / full (collection 315.2 s, 0 steps skipped by mode, 5 failed) |
| 프로파일 | `prod` (detected) |
| kubegap / 룰 / 서명 카탈로그 | 0.1.2 / 0.1.63 / 1.0.15 |
| 노드 / 네임스페이스 / 파드 / CRD | 8 (Ready 8) / 25 / 145 / 47 |
| 컴포넌트 (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| 메트릭 저장소 | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| 로그 저장소 | loki 2.6.1 |
| 노드 접근 | ssm (EKS: SSM send-command); SSM unregistered 2 |
| 스냅샷 | `~/.kubegap/snapshots/my-cluster/2026-11-03T11-17-15` |

## 1. 1차 결과 집계와 최종 조정

| 심각도(기본) | fail | warn | 같은 모드의 지난 실행 대비 |
|---|---|---|---|
| critical | 1 | 2 | fail +0 · warn +0 |
| high | 32 | 25 | fail -4 · warn +2 |
| medium | 111 | 167 | fail +4 · warn -3 |
| low | 16 | 138 | fail -2 · warn +2 |
| info | 2 | 0 | 같은 모드의 지난 실행 없음 |

Checks 365: evaluated 358, disabled by profile 2, skipped 3, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. 1차 결과와 최종 결과의 차이

### Severities

| finding id | 1차 결과 | 최종 결과 | 이유 |
|---|---|---|---|
| `observability.no-slo.cluster` | warn / critical | warn / high | 규칙 ③ 을 그대로 적용했어요. 1차가 warn 인 것은 slo 레이블이 붙은 알림 규칙 5개를 완화 신호로 찾았기 때문이에요. ImageInferenceE2ESuccessRateDrop, ImageInferenceEntitlementFailureSpike, LoraTrainingSuccessRateDrop, LoraTrainingDurationP95High, LoraTrainingCallbackTimeout 이에요. burn rate 알림과 SLI recording rule 은 0개라 SLO 는 여전히 없어요. 2026-10-26 16:47 리포트는 critical 로 셌는데, 규칙 ③ 은 warn 이면 high 라서 이번엔 high 로 셉니다. |
| `observability.no-symptom-alerts.cluster` | warn / critical | warn / high | 규칙 ③ 을 그대로 적용했어요. 157개 규칙 중 사용자 증상 규칙은 0개이고, 앱 메트릭 규칙 19개를 증상으로 가정한 것이 warn 의 이유예요. 2026-10-26 16:47 리포트는 critical 로 셌는데, 규칙 ③ 은 warn 이면 high 라서 이번엔 high 로 셉니다. 문제 3 의 근거예요. |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` | fail / high | fail / medium | KEDA 가 0 에서 1, 2 로 올린 배치 워커가 Karpenter 노드를 기다린 시간이에요. events.json 에서 01:41:06Z 에 생긴 파드가 01:42:43Z 에 새 노드로 스케줄됐고, 두 번째 파드는 01:43:00Z 에서 01:44:00Z 까지 기다렸어요. 사용자 요청 경로가 아니고 원래 이렇게 동작하게 되어 있어요. 이미지가 1.89 GB 라 받는 데 1분 15초가 더 걸렸어요. |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` | warn / high | warn / medium | 같은 이유예요. 01:46:43Z 에 생긴 파드가 01:47:42Z 에 스케줄됐어요. events.json. |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn / high | warn / low | build-arm64 풀의 CI 러너가 Karpenter 노드를 기다리는 것은 원래 동작이에요. 2026-10-26 16:47 리포트와 같은 내림이에요. |
| `events.tracked-warning-reasons.FailedScheduling` | fail / high | fail / medium | 이번 창의 12건은 전부 위 app-l-file-worker 와 app-l-graph-worker 의 0 에서 늘리기 대기예요. events.json 01:41:06Z~01:47:34Z. 이전 3건도 같은 워커예요. |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | fail / high | warn / medium | 규칙 ⑤. 수집 시각의 5분 비율은 0.26 과 0.25 가 맞아요. metrics/cpu_throttle_ratio_5m.json. 그런데 7일 p95 사용은 200 m 제한의 8.0% 와 8.2% 이고 metrics/cpu_limit_p95_ratio_7d.json, prod-app-m 네임스페이스의 7일 스로틀링 비율은 1.6% 예요. metrics/namespace_cpu_throttled_ratio_7d.json. 짧은 몰아 쓰기라 fail/high 에서 warn/medium 으로 두 단계 내렸어요. 도구 메모 48 재현이에요. |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn / high | warn / medium | dev 네임스페이스이고 5분 순간값 하나예요. |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn / high | warn / medium | dev 네임스페이스이고 5분 순간값 0.11 하나예요. |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn / high | warn / medium | 수집 중에 측정된 값이에요. kubegap 이 PromQL 168개를 보내던 11:18 KST 의 5분 비율 0.22 라 kubegap 자신의 쿼리가 섞였을 가능성이 커요. |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn / high | warn / medium | working set / limit 0.738 이에요. metrics/prom_rss_vs_limit.json. 마지막 OOMKill 은 27.6일 전 한 번이고 그 뒤 재발이 없어요. 2026-10-26 16:47 리포트와 같은 내림이에요. |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn / high | warn / low | 27.6일 전 OOMKill 한 번이고 metrics/oom_events_7d.json 에는 없어요. |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | fail / high | fail / medium | 2026-10-30 09:00 UTC 의 OOMKill 은 직전 OOMKill 인 2026-05-12 이후 처음이에요. objects/pods.json lastState. 재시작 42회는 2026-03-13 파드 생성 이후 누적이고 2026-10-27 스냅샷 41회에서 1회 늘었어요. 7일 p95 는 768Mi 제한의 51% 예요. metrics/memory_limit_p95_ratio_7d.json. 컨트롤러 재시작은 사용자 트래픽을 끊지 않고 동기화만 잠깐 멈춰요. |
| `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` | warn / high | warn / medium | 위와 같은 OOMKill 한 번이에요. |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn / high | warn / medium | 위와 같은 OOMKill 한 번이에요. 지금 Running 이에요. |
| `traffic.db-exposed.nlb/acme-db-shared` | fail / high | fail / medium | 스냅샷 밖에서 읽은 보안 그룹 acme-db-shared-nlb 는 5432, 6379, 3306~3311, 7687, 5433 포트마다 /32 주소 4개 이하만 허용해요. extra/lb-security-group-rules.txt. 인터넷 전체에 열린 것이 아니에요. 24시간 처리 바이트도 0 이에요. aws/alb-metrics.json. 허용 목록 DB 포트가 인터넷 쪽 LB 에 있는 것은 남으니 medium 으로 둡니다. |
| `eks.service-quota-near-limit.aws-account` | warn / high | warn / low | VPCs 3/5 는 계정 쿼터라 클러스터가 런타임에 쓰지 않아요. 클러스터 쪽은 리스너 규칙 47%, 타깃 그룹 40% 예요. 이전 리포트와 같은 내림이에요. |
| `vpccni.node-ip-exhaustion.node-1-241` | warn / high | warn / low | 시스템 노드 t8i.small, IP 9개 중 6개, "no available IP" 이벤트 0건이에요. 이전 리포트와 같은 내림이에요. |
| `vpccni.node-ip-exhaustion.node-2-218` | warn / high | warn / low | 시스템 노드 t8i.medium, IP 15개 중 13개, "no available IP" 이벤트 0건이에요. 이전 리포트와 같은 내림이에요. |
| `events.tracked-warning-reasons.UpdateFailed` | warn / high | warn / medium | 2,351건 전부 dev 용 ExternalSecret database/mysql-app-n-secret 하나예요. events.json. 이전 리포트와 같은 내림이에요. |
| `logs.signatures.external-secrets.provider-error` | warn / high | warn / medium | 같은 dev ExternalSecret 하나의 로그 32줄이에요. |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail / high | fail / medium | dev 네임스페이스예요. prod 타깃 그룹 넷은 high 그대로예요. |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail / high | fail / medium | dev 네임스페이스이고 24시간 요청 0건이에요. |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | fail / high | fail / medium | dev 데모 DB 이고 하루 증가량 0.0 GB 예요. summary.json storage.pvcs. |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | warn / high | warn / medium | 이번 창에는 2026-10-27 05:55 UTC 의 1건뿐이에요. events.json. 디스크 자체는 node.disk-usage 가 high 로 따로 봐요. |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | fail / high | fail / medium | 7일 p95 가 제한의 91% 이지만 metrics/oom_events_7d.json 에 promtail OOM 은 없어요. 로그 유실 위험이라 medium 으로 둡니다. |
| `controlplane.apiserver-latency.LIST` | warn / medium | warn / low | 수집 중에 측정된 값이에요. metrics/apiserver_p99_latency_by_verb.json 이 11:18 KST 에 찍혔고 kubegap 이 오브젝트 LIST 를 보내던 시간이에요. |
| `controlplane.apiserver-latency.PATCH` | warn / medium | warn / low | 수집 중에 측정된 값이에요. 같은 11:18 KST 이고 같은 시간대에 KEDA 와 Karpenter 가 노드 세 대를 정리하며 PATCH 를 보냈어요. events.json 02:04Z~02:13Z. |
| `observability.alerts-always-firing.KubePodNotReady` | fail / medium | fail / low | 이미 끝난 일이에요. 7일 표본 169,042개는 2026-10-26 리포트의 Failed 파드 12개가 남긴 것이고, 지금은 Failed 파드가 0개이며 KubePodNotReady 는 지금 울리지 않아요. summary.json observability.alerts.firing_now. |
| `node.network-errors.<ip>:9100:eth0` | warn / medium | warn / info | 노드 ip-10-0-1-203 은 2026-11-02 05:09 UTC 에 Karpenter 가 비어 있어 지웠어요. summary.json scaling.karpenter.disrupted_24h. 지금 없는 노드의 24시간 increase() 잔상이에요. 도구 메모 44 재현이에요. |
| `tenancy.prod-without-quota.* (13개)` | warn / medium | warn / low | 7일 동안 CPU 90% 를 1분 넘긴 노드가 없고 summary.json tenancy.noisy.nodes_saturated_7d 가 비어 있어요. 이웃 때문에 스로틀링된 prod 네임스페이스도 없어요. 여기서 쿼터는 위생이지 당장의 위험이 아니에요. 13개 모두 이 이유예요. |

### Recounted aggregates

| finding id | 1차 결과 | 최종 결과 | 이유 |
|---|---|---|---|
| `traffic.db-exposed.nlb/acme-db-shared` | sourceRanges None, 인터넷 쪽 NLB 에 DB 포트 4종 | 보안 그룹이 포트마다 /32 주소 4개 이하만 허용, 6379 는 1개 | 1차는 Service 정의만 봐요. 이 NLB 는 클러스터 밖에서 만들어져 Service 가 없고, 보안 그룹은 스냅샷에 없어서 `aws elbv2 describe-load-balancers` 와 `aws ec2 describe-security-groups` 로 따로 읽었어요. extra/lb-security-groups.txt, extra/lb-security-group-rules.txt. |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | sourceRanges None | 보안 그룹 k8s-middlewa-kafkacon 이 9094 와 443 을 0.0.0.0/0 에 열어 둠 | 같은 방법으로 읽었어요. 1차의 "열려 있음" 이 실제로 맞다는 확인이에요. extra/lb-security-group-rules.txt. |
| `resilience.prod-concentration.node-1-139` | prod 파드 20/42 를 노드 하나에 | 20/42 + 같은 2a 영역의 다른 스팟 노드 ip-10-0-1-62 에 13/42, 합 33/42 | report.md 문제 2 는 두 스팟 노드를 합쳐 셌어요. objects/pods.json 에서 Running prod 파드를 노드별로 셌어요. |
| `resilience.n-plus-one.cluster` | pass, 가장 큰 노드를 빼면 메모리 46.6 GB, requests 47.5 GB | pass 는 맞지만 2% 여유 안에서 0.03 GB 차이로 통과 | 코드가 46.6 × 1.02 = 47.53 GB 와 비교해요. lib/resilience.py _n_plus_one. 앱 파드가 갈 수 있는 노드가 workload-type=app 두 대뿐이라는 점은 이 합산에 들어가지 않아요. 도구 메모 49. |

## 2. 지금 fail 인 critical·high, 1차 결과

| 발견 사항 | 심각도 | 연속 실행 수 | 근거 |
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

## 3. 같은 모드의 지난 실행 이후 변화

Compared `2026-10-27T15-30-14` → `2026-11-03T11-17-15` (rubric 0.1.51 → 0.1.63).

- **New (29)**: `argocd.admin-account-no-sso.cluster` (warn/medium), `argocd.components-not-ha.cluster` (warn/medium), `argocd.default-project-wildcard.cluster` (fail/medium), `argocd.notifications-not-configured.cluster` (warn/low), `argocd.prod-tracks-moving-ref.cluster` (warn/low), `argocd.version-eol.cluster` (warn/low), `controlplane.apiserver-latency.PATCH` (warn/medium), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` (fail/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker` (warn/high), `cost.idle-load-balancer.cluster` (warn/low), `cost.idle-node.node-2-144` (warn/low), `loki.request-errors.monitoring/statefulset/loki-stack` (warn/medium), `node.cgroup-v1.node-2-144` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` (warn/high), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` (fail/medium), `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` (fail/medium), `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` (warn/high), `resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai` (fail/medium), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-z2bk5:runner` (fail/medium), `resources.oomkilled-repeated.argocd/sts/argocd-application-controller:application-controller` (warn/high), `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` (warn/high), `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` (fail/high), `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` (fail/high), `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` (warn/medium), `security.imds-hop-limit.cluster` (warn/high), `traffic.ingress-p95-latency.prod-app-q/app-q-ai` (fail/medium), `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend` (fail/medium), `traffic.pod-not-ready.middleware/kafka-exporter` (warn/medium)
- **Resolved (30)**: `controlplane.apiserver-5xx.cluster` (warn/high), `controlplane.scheduler-unschedulable.prod-app-r/app-r` (warn/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-backend` (fail/high), `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-embedding-server` (fail/high), `controlplane.scheduler-unschedulable.app-s-prod/app-s-backend` (fail/high), `controlplane.scheduler-unschedulable.app-s-prod/app-s-frontend` (warn/high), `cost.idle-node.node-1-4` (warn/low), `cost.idle-node.node-1-62` (warn/low), `hygiene.failed-pods-lingering.cluster` (fail/low), `logs.signatures.kubelet.volume-mount-failed` (warn/medium), `node.cgroup-v1.node-1-4` (fail/low), `node.network-errors.<ip>:9100:eth0` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/dev-app-o` (fail/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-r` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/prod-app-l-backend` (warn/medium), `observability.alert-firing-stale.KubePodNotReady/app-s-prod` (fail/medium), `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/medium), `resources.cpu-request-overprovisioned.prod-app-q/deploy/app-q-ai:ai` (warn/medium), `resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend` (warn/medium), `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` (fail/high), `resources.cpu-throttling.prod-app-n/deploy/app-n-frontend:frontend` (warn/high), `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-tflzb:runner` (fail/medium), `resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` (warn/low), `resources.node-memory-request-usage-gap.node-1-139` (warn/medium), `resources.oomkilled-repeated.monitoring/sts/loki-stack:loki` (warn/high), `traffic.alb-unhealthy-targets.prod-app-p/app-p-backend` (warn/high), `traffic.pod-not-ready.app-s-prod/app-s-frontend` (warn/medium), `traffic.pod-request-skew.prod-app-p/app-p-backend` (warn/medium), `vpccni.subnet-ips-low.subnet-01e43688f4ab26b0e` (warn/high), `vpccni.warm-pool-whole-eni.cluster` (warn/low)
- **Changed (10)**: `events.tracked-warning-reasons.FreeDiskSpaceFailed` (['fail', 'warn']/['high', 'high']), `logs.signatures.containerd.shim-error` (['warn', 'fail']/['medium', 'medium']), `node.network-errors.<ip>:9100:eth0` (['fail', 'warn']/['medium', 'medium']), `resilience.prod-concentration.node-1-139` (['fail', 'warn']/['high', 'high']), `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['medium', 'medium']), `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` (['warn', 'fail']/['high', 'high']), `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` (['fail', 'warn']/['low', 'low']), `resources.node-request-usage-gap.node-1-62` (['warn', 'fail']/['medium', 'medium']), `resources.oomkilled.monitoring/sts/loki-stack:loki` (['fail', 'warn']/['high', 'high'])
- **Rename suspects (3)**: `None`, `None`, `None`
- **Objects**: added 6, removed 5, changed 19: `configmaps/kube-system/aws-load-balancer-controller-leader` metadata.resourceVersion, `configmaps/kube-system/extension-apiserver-authentication` metadata.resourceVersion, `deployments/dev-app-m/app-m-backend` spec.template, `deployments/dev-app-m/app-m-frontend` spec.template, `deployments/prod-app-q/app-q-ai` spec.template, `deployments/prod-app-q/app-q-backend` spec.template, `deployments/prod-app-q/app-q-studio` spec.template, `deployments/prod-app-q/app-q-web` spec.template, `deployments/prod-app-l-backend/app-l-backend` spec.template, `deployments/prod-app-l-backend/app-l-embedding-server` spec.template, `deployments/prod-app-l-backend/app-l-file-worker` spec.template, `deployments/prod-app-l-backend/app-l-graph-worker` spec.template
- **Warning events**: UpdateFailed +625 (ExternalSecret/database/mysql-app-n-secret), FailedComputeMetricsReplicas -112 (), FailedGetResourceMetric -112 (), EvictionThresholdMet -56 (), Unhealthy +44 (Pod/middleware/kafka-exporter-78d46ff57f-dn65f), NetworkNotReady +13 (Pod/kube-system/ebs-csi-node-cf97j), FailedScheduling +9 (Pod/prod-app-l-backend/app-l-file-worker-db75d7fdc-9dkp4), CgroupV1 +2 (Node/node-2-101), FailedDraining +2 (Node/node-2-101), InstanceTerminating +2 (NodeClaim/default-cv77k)
- **Persisted (Toil)**: 0 findings present in all 2 runs checked, 0 in 3 or more; top checks: 

### 3-1. 왜 바뀌었나

비교 대상은 직전 full 스냅샷 2026-10-27 15:30 KST 이고, 두 수집 사이는 6일 20시간이에요. 그 스냅샷에는 리포트가 없어서, 지난 문제의 진행은 그 앞의 full 리포트인 2026-10-26 16:47 KST 리포트를 기준으로 봤어요. 그 리포트는 이 스냅샷 루트가 아니라 `~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/` 에 있어요.

노드는 8대로 같지만 한 대가 바뀌었어요. build-arm64 풀의 `ip-10-0-1-4` 가 빠지고, 같은 풀의 c6g.xlarge 스팟 노드 `ip-10-0-2-144` 가 2026-11-03 00:30 UTC 에 CI 러너용으로 새로 떴어요. AWS 쪽에서는 EKS 플랫폼 버전이 eks.55 에서 eks.58 로 올라가고 API 서버 빌드가 v1.32.13-eks-cfb47f5 에서 v1.32.13-eks-577a51e 로 바뀌었어요. 마이너 버전은 1.32 그대로예요.

Deployment 16개의 spec.template 이 바뀌었어요. 배포가 이어진 것이고, prod-app-q 네 개, prod-app-l-backend 네 개, prod-app-p 두 개, prod-app-n 두 개, app-s-prod 두 개, dev-app-m 두 개예요. dev-app-m 의 app-m-backend 와 app-m-frontend 는 generation 이 59 → 1, 879 → 19 로 줄었고 생성 시각이 2026-11-02 03:27 UTC 라서, 업데이트가 아니라 지우고 다시 만든 거예요. FlowSchema `eks-kcm-controllers` 의 spec.rules 가 바뀐 것은 EKS 플랫폼 버전 변경과 같이 온 AWS 관리 변경으로 보여요. 파드는 166개에서 145개로, ReplicaSet 은 422개에서 414개로 줄었어요.

2026-10-26 리포트의 문제 2 로 적힌 노드 `ip-10-0-1-139` 의 Failed 파드 12개가 없어졌어요. 그래서 `hygiene.failed-pods-lingering` 과 네임스페이스 네 개의 KubePodNotReady 오래 울림 발견 사항이 해결로 빠졌어요. 같은 노드의 디스크는 86.4% 에서 82% 로 내려왔지만, 이미지 정리 실패는 2026-11-02 에도 3번 있었어요.

2026-10-27 의 스케줄 실패 발견 사항 다섯 개, app-s-backend, app-s-frontend, app-r, app-l-backend, app-l-embedding-server 는 그날의 노드 교체 때 생긴 것이라 이번 창에는 없어요. 대신 새로 뜬 app-l-file-worker 와 app-l-graph-worker 의 스케줄 실패는 KEDA 가 두 워커를 0 에서 늘릴 때 Karpenter 노드를 1분쯤 기다린 거예요. 그 노드 세 대는 01:42~01:47 UTC 에 떴다가 02:04~02:13 UTC 에 정리됐어요. diff 의 rename 후보 세 개 중 app-l 두 개는 이름이 바뀐 게 아니라 다른 워크로드이고, arc 러너 하나는 임시 러너 파드 이름이 바뀐 진짜 이름 변경이에요.

새로 생긴 사건은 `prod-app-q/app-q-ai` 의 OOMKill 이에요. 새 ReplicaSet 의 파드가 2026-11-02 08:53:47 UTC 에 생기고 44분 뒤인 09:38:06 UTC 에 768Mi 제한에 걸려 죽었어요. Argo CD 의 application-controller 도 2026-10-30 09:00 UTC 에 OOMKill 로 한 번 재시작했어요. `middleware/kafka-exporter` 의 readiness·liveness 프로브 시간 초과가 5건에서 49건으로 늘었어요.

이벤트 쪽 감소의 대부분은 변화가 아니라 보존 기간이 지난 거예요. EvictionThresholdMet 56건, FailedGetResourceMetric 112건, FreeDiskSpaceFailed 1건, NodeHasDiskPressure 40건이 그 경우예요. dev ExternalSecret `database/mysql-app-n-secret` 의 동기화 실패만 1,726건에서 2,351건으로 계속 늘고 있어요.

기준 변경도 있어요. 룰이 0.1.51 에서 0.1.63 으로 올랐어요. Argo CD 점검 항목 13개는 2026-10-27 에 `summary.argocdctl.summary missing` 으로 건너뛰었다가 이번에 처음 평가돼서 발견 사항 여섯 개가 새로 보여요. 클러스터의 Argo CD 가 바뀐 것은 아니에요. 새로 생긴 점검 항목 다섯 개, `hygiene.configmap-changed-after-pod-start`, `vpccni.external-snat-off-with-private-routes`, `vpccni.snat-port-randomization-off`, `traffic.ingress-nginx-retired`, `traffic.ingress-nginx-vulnerable-version` 은 pass 이거나 ingress-nginx 가 없어 건너뛰었어요. `hygiene.helm-release-pure-defaults` 는 룰에서 빠졌어요.

## 4. 영역별 세부

### resources

리소스 조정표로 묶었어요. CPU requests 과대 36개, KRR 권고 32개, 큰 request 3개, 메모리 requests 과대 13개가 같은 컨테이너에 겹쳐요. 전체 목록은 세부 7-5 절에 있고, 여기는 영향이 큰 다섯 줄이에요.

| 컨테이너 | 지금 | 권고 | 근거 | 관련 발견 사항 |
|---|---|---|---|---|
| `prod-app-q/app-q-ai` ai | memory request 256Mi, limit 768Mi | memory request 640Mi, limit 1Gi | 2026-11-02 09:38 UTC OOMKill, KRR 메모리 권고 607 MB | `resources.oomkilled`, `resources.oomkilled-repeated`, `resources.krr-recommendation` |
| `argocd/argocd-application-controller` | memory request 384Mi, limit 768Mi | memory request 768Mi, limit 1Gi | 2026-10-30 OOMKill, KRR 메모리 권고 757 MB, 7일 p95 408 MB | `resources.oomkilled`, `resources.krr-recommendation` |
| `monitoring/prometheus-kube-prometheus-stack-prometheus` | memory request 800Mi, limit 1536Mi | memory request 1.6Gi, limit 2Gi | KRR 메모리 권고 1,639 MB, working set / limit 0.738 | `resources.krr-recommendation`, `prometheus.memory-pressure` |
| `prod-app-l-backend/app-l-backend` backend | CPU request 0.5코어 두 레플리카 | CPU request 0.05코어 | 7일 p95 0.002코어 | `resources.cpu-request-overprovisioned` |
| `prod-app-l-backend/app-l-embedding-server` | CPU request 0.5코어 두 레플리카 | CPU request 0.05코어 | 7일 p95 0.001코어, request 가 노드 중앙값 allocatable 의 58% | `resources.cpu-request-overprovisioned`, `resources.large-request-binpacking` |

`prod-app-l-backend/app-l-neo4j` 는 데이터베이스라 p95 로 request 를 줄이지 않아요. CPU limit 이 있으면 빼고 request 는 그대로 두세요. 노드 CPU requests 는 `ip-10-0-2-60` 99%, `ip-10-0-1-117` 96%, `ip-10-0-1-62` 92%, `ip-10-0-1-139` 89% 인데 7일 p95 사용은 5~10% 예요. 출처는 metrics/node_cpu_request_ratio.json, metrics/node_cpu_usage_ratio_p95_7d.json 이에요. 위 두 app-l 컨테이너만 줄여도 앱 노드에 1.8코어가 비어요. 돈으로 본 같은 표는 `cost.request-waste` 와 `cost.idle-compute-high` 이고, 유휴 비율은 0.95, 줄일 수 있는 CPU 는 5.26코어예요.

`prod-app-m/app-m-frontend` 의 스로틀링은 수집 시각 5분 비율 26% 와 25% 였지만 7일 p95 사용이 200 m 제한의 8% 라 warn 으로 내렸어요. 제한을 없애거나 500 m 로 올리면 사라져요. `prod-app-l-backend/tts-proxy` 는 requests 와 limits 가 모두 없는 BestEffort 이고 메모리 제한도 없어요. `middleware/kafka-controller` 의 jmx-exporter 는 -Xmx 없이 MaxRAMPercentage 100 에 128Mi 제한이라 힙이 제한 전체를 쓸 수 있어요.

```yaml
# prod-app-q/app-q-ai
resources:
  requests: {cpu: 100m, memory: 640Mi}
  limits:   {memory: 1Gi}
```

### scaling

KEDA 가 `prod-app-l-backend/app-l-file-worker` 와 `app-l-graph-worker` 를 0 에서 늘릴 때 파드가 Karpenter 노드를 1분쯤 기다리고, 1.89 GB 이미지를 받는 데 1분 10초쯤 더 걸려요. 스케줄 실패 이벤트 12건과 control plane 로그 47줄은 전부 이 대기라 medium 으로 내렸어요. 기다림을 줄이려면 이미지를 줄이거나 KEDA `minReplicaCount: 1` 로 하나를 켜 두세요. 세 ScaledObject `prod-app-o/app-o-ai-kafka-lag`, `prod-app-l-backend/app-l-file-worker`, `prod-app-l-backend/app-l-graph-worker` 는 외부 트리거가 끊길 때의 fallback 이 없어요.

NodeClaim `default-n44bh` 의 노드 `ip-10-0-1-139` 는 만료 720시간을 241.8시간 넘겼어요. `prod-app-m/app-m-admin` 의 pod template 에 있는 `karpenter.sh/do-not-disrupt: "true"` 하나가 교체를 19,728번 막았어요. 문제 2 의 근거예요. prod HPA 두 개 `app-l-backend`, `app-l-frontend` 는 15일 내내 최소값 2 에 있고 CPU 만 보며 behavior 가 없어요. dev-app-m/app-m-frontend HPA 는 7일 동안 desired 가 40번 바뀌었어요. prod Deployment 21개에 HPA 가 없고, 그중 16개는 레플리카 1개라 resilience 표에 붙였어요.

### observability

사용자 증상을 보는 알림이 0개예요. 문제 3 이에요. 알림 규칙 157개 중 원인 규칙 138개, 앱 메트릭 규칙 19개, 증상 규칙 0개이고, 130개는 15일 동안 한 번도 울리지 않았어요. 실패 유형 15개 중 OOMKill, 스케줄링 실패, VPC CNI IP 고갈 세 가지에 규칙이 없어요.

항상 울리는 알림은 알림 이름당 한 줄로 적어요. KubeControllerManagerDown 은 EKS 관리형 컨트롤 플레인이라 생기는 오탐이에요. KubeSchedulerDown 도 같은 오탐이에요. KubePodNotReady 의 7일 표본 169,042개는 이미 지워진 Failed 파드 12개가 남긴 것이라 지금은 울리지 않아요.

관측 스택 저장소는 한 항목이에요. Loki `monitoring/loki-stack` 은 storage 가 emptyDir 이고 레플리카 1개라 파드가 옮겨지면 로그가 사라져요. 2026-10-25 에 OOMKill 이 한 번 있었어요. Alertmanager 도 emptyDir 에 레플리카 1개라 silence 와 알림 기록이 재시작 때 사라져요. Loki 보존은 retention_period 31d 인데 retention_enabled false 라 실제로는 지워지지 않아요. Running 파드 139개 중 66개가 Loki 에 없고, 새 노드 `ip-10-0-2-144` 는 전부 빠졌어요. promtail 메트릭은 ServiceMonitor 가 없어 Prometheus 에 없어요. Grafana 의 Loki 데이터소스 응답 2,592개 중 429 가 321개예요. 이벤트 보존 도구와 SLO 정의도 없어요.

```yaml
# PrometheusRule 조각: OOMKill 과 ALB 5xx 가 비어 있는 실패 유형
- alert: ContainerOOMKilled
  expr: increase(container_oom_events_total{namespace=~"prod-.*|app-s-prod"}[10m]) > 0
  labels: {severity: warning}
```

```yaml
# kube-prometheus-stack values: EKS 에서 항상 울리는 두 규칙 끄기
kubeControllerManager: {enabled: false}
kubeScheduler: {enabled: false}
```

### traffic

prod ALB 타깃 그룹 넷의 타깃이 전부 unhealthy 예요. `prod-app-q/app-q-backend` 404, `prod-app-o/app-o-frontend` 307, `prod-app-l-backend/app-l-backend` 404 두 개, `prod-app-n/app-n-frontend` 307 이에요. 헬스체크 경로가 기본값 `/` 라서 생긴 일이고, 전부 unhealthy 면 ALB 는 모든 타깃에 그대로 보내서 헬스체크가 아무것도 거르지 못해요. dev 둘 `dev-app-n/app-n-frontend`, `dev-app-t/app-t-backend` 도 같아요. 문제 3 의 일부예요.

지연은 prod 셋이 fail 이에요. `prod-app-m/app-m-api` 는 24시간 408건에 p95 평균 20.48초, 최근 1시간 15.06초예요. `prod-app-q/app-q-ai` 는 130건에 평균 14.09초, 최근 1시간 2.47초예요. `prod-app-l-backend/app-l-frontend` 는 1,949건에 평균 3.14초, 시간당 최대 41.54초, 최근 1시간 0.87초예요. 5xx 는 `api.example-b.ai` 0.12%, `example-c.ai` 0.14% 로 warn 이에요. 2026-10-26 의 0.60% 에서 내려왔어요.

인터넷 노출은 문제 4 예요. `middleware/kafka-controller-0-external` NLB 의 보안 그룹이 9094 와 443 을 0.0.0.0/0 에 열어 두었고 24시간 2.85 GB 가 오갔어요. 클러스터 밖에서 만든 NLB `acme-db-shared` 는 DB 포트를 /32 주소 4개 이하에만 열어서 medium 으로 내렸어요. 이 NLB 는 24시간 처리 바이트가 0 이에요. 인증 표시 없이 인터넷에 열린 어드민 ingress 가 7개예요. `argocd/argocd-server` deploy.my-cluster, prod 의 `app-m-admin`, `app-o-admin`, `app-n-admin-frontend`, dev 의 `app-m-admin`, `app-o-admin`, `app-n-admin-frontend` 이에요.

ALB 그룹 `acme-prod-lb` 하나에 ingress 40개, 호스트 47개, 네임스페이스 15개가 묶여 있어 dev 의 잘못된 ingress 하나가 prod 리스너까지 막을 수 있어요. ALB 컨트롤러 기본 deregistration 300초가 타깃 그룹 28개에 걸려 있어요. 앞의 다섯은 `argocd/argocd-server`, `dev-app-n/app-n-admin-frontend`, `dev-app-n/app-n-backend`, `dev-app-n/app-n-frontend`, `dev-app-t/app-t-backend` 이고, 파드는 30초 뒤 끝나는데 ALB 는 300초 동안 연결을 기다려요. CoreDNS 응답의 51% 가 NXDOMAIN 이고 파드 145개가 기본 ndots 5 예요. `middleware/kafka-exporter` 는 readiness·liveness 프로브 시간 초과가 49건이에요.

```yaml
# prod ingress 넷에 추가
metadata:
  annotations:
    alb.ingress.kubernetes.io/healthcheck-path: /health   # 앱이 200 을 돌려주는 경로로
    alb.ingress.kubernetes.io/success-codes: "200"
```

### resilience

백업이 없어요. 문제 1 이에요. DLM 정책 0개, AWS Backup 계획 0개, VolumeSnapshot 0개, 백업 CronJob 0개이고 prod DB StatefulSet 7개에 덤프가 없어요. prod DB PVC 7개 전부 reclaimPolicy Delete 예요.

배치는 문제 2 예요. resilience 표는 워크로드당 한 줄이에요.

| 워크로드 | 레플리카 | 같은 노드 | 같은 영역 | PDB | readiness | 비고 |
|---|---|---|---|---|---|---|
| `prod-app-r/app-r` | 2 | 둘 다 `ip-10-0-1-139` | 2a | 있음 | 있음 | HPA 없음 |
| `prod-app-o/app-o-ai` | 3 | 셋 다 `ip-10-0-1-139` | 2a | 없음 | 없음 | KEDA kafka lag |
| `prod-app-o/app-o-backend` | 2 | 둘 다 `ip-10-0-1-139` | 2a | 없음 | 없음 | HPA 없음 |
| `prod-app-l-backend/app-l-frontend` | 2 | 둘 다 `ip-10-0-1-139` | 2a | 있음 | 있음 | HPA CPU 만 |
| `prod-app-m/app-m-api`, `app-m-backend`, `app-m-frontend`, `prod-app-l-backend/app-l-backend`, `app-l-embedding-server` | 2 | 노드는 나뉨 | 둘 다 2a | 있음 | 있음 | 영역 분산 없음 |
| `prod-app-p/app-p-backend` | 1 | — | — | — | 있음 | Recreate, 볼륨은 emptyDir tmp 하나라 Recreate 이유 없음 |

레플리카 1개인 prod Deployment 는 16개예요. app-q 넷 `app-q-ai`, `app-q-backend`, `app-q-studio`, `app-q-web`, app-m 하나 `app-m-admin`, app-o 둘 `app-o-admin`, `app-o-frontend`, app-l 둘 `app-l-pg-proxy`, `tts-proxy`, app-p 둘 `app-p-backend`, `app-p-web`, app-n 셋 `app-n-admin-frontend`, `app-n-backend`, `app-n-frontend`, app-s 둘 `app-s-backend`, `app-s-frontend` 이에요. readiness 프로브가 없는 prod Deployment 는 10개이고 app-o 넷, app-n 셋, app-s 둘, `tts-proxy` 예요.

DB 프로브는 Bitnami 기본값 한 항목이에요. prod 의 MySQL 셋 `app-m-backend-mysql`, `app-o-backend-mysql`, `app-n-backend-prod-mysql` 과 `app-l-neo4j` 가 liveness timeout 1초라 디스크가 느린 순간 DB 가 재시작될 수 있어요. dev DB 다섯 개도 같은 설정이에요. `tts-proxy` 는 hostPath `/dev/net/tun` 을 써서 노드 하나에 묶여요. Argo CD, ESO, KEDA 컨트롤러는 레플리카 1개씩이에요. PriorityClass 가 없어 prod 파드 42개가 dev 파드와 같은 우선순위 0 이에요. Docker Hub 이미지 의존과 ECR 복제 없음도 있어요.

```yaml
# 레플리카 2개 이상인 prod Deployment 에
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector: {matchLabels: {app.kubernetes.io/name: <앱>}}
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: {matchLabels: {app.kubernetes.io/name: <앱>}}
```

### hygiene

AL2 → AL2023 이전은 플랫폼 항목과 한 항목이에요. EKS 업그레이드 인사이트가 AL2 호환성을 ERROR 로 내고 있어요. 바뀌는 태그를 쓰는 워크로드는 한 줄씩이에요. `prod-app-l-backend/tts-proxy` tailscale `tailscale/tailscale:latest`, `arc-runners/arc-cool-down` 과 `arc-warm-up` 의 `bitnami/kubectl:latest`, `middleware/redis-insight` `redis/redisinsight:latest` 예요. KEDA 세 개와 aws-node 의 nodeagent 등 다섯 컨테이너는 태그가 있는데 imagePullPolicy Always 예요.

prod 앱 8개 전부 Argo CD 에서 브랜치나 HEAD 를 따라가요. Argo CD 2.13.0, ESO, Grafana 10.2.3, Loki 2.6.1, Prometheus 2.49.1 이 오래된 버전이에요. dev ExternalSecret `database/mysql-app-n-secret` 이 2025-12-17 부터 실패 중이고 이번 창 2,351건이에요. 점진적 배포 도구가 없고, ephemeral-storage requests 가 없으며, 오래된 ReplicaSet 이 남아 있어요. 노드 레이블 `workload-type` 과 `acme.ai/role` 에 기대는 워크로드가 많아요.

### storage

문제 1 의 일부예요. EBS 볼륨 17개 280 GB 가 전부 암호화되지 않았고, StorageClass `gp3`, `gp3-2a`, `gp3-2c` 는 암호화 파라미터와 allowVolumeExpansion 이 없어요. VolumeSnapshot CRD 가 없어 EBS CSI 컨트롤러가 24시간에 1,500줄의 오류를 남겼어요. 최근 30일 EBS 스냅샷 12개는 전부 "pre-delete backup of orphan PVC" 로, 사람이 PVC 를 지우기 전에 손으로 뜬 거예요. dev `dev-app-t/data-app-t-mysql-0` 이 9.7 GB 중 90.2% 지만 하루 증가량 0.0 GB 예요. in-tree 프로비저너 `gp2` StorageClass 가 아직 있어요.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata: {name: gp3-encrypted}
provisioner: ebs.csi.aws.com
parameters: {type: gp3, encrypted: "true"}
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### security

인터넷 노출은 문제 4 예요. Kafka 외부 리스너 9094 와 443 이 0.0.0.0/0 에 열려 있어요. LB 에서 TLS 를 끝내지 않고, 브로커 리스너의 인증 방식은 ConfigMap 값이 수집되지 않아 확인하지 못했어요. EKS API 엔드포인트가 0.0.0.0/0 에 공개예요. Argo CD 는 SSO 없이 admin 계정이 켜져 있고 RBAC 기본 정책이 비어 있으며, 앱 12개가 sourceRepos 와 destinations 가 전부 `*` 인 default 프로젝트에 있어요. `argocd-application-controller` ClusterRole 은 verbs 와 resources 가 `*` 예요.

NetworkPolicy 3개가 `prod-app-q`, `prod-app-p`, `app-s-prod` 에 있지만 aws-eks-nodeagent 가 `--enable-network-policy=false` 라 적용되지 않아요. PSA enforce 는 어느 네임스페이스에도 없어요. `prod-app-l-backend/tts-proxy` 는 NET_ADMIN 과 hostPath `/dev/net/tun`, root 허용이에요. 인스턴스 8대 모두 IMDS hop limit 2 라 파드에서 노드 IAM 역할을 읽을 수 있어요. tokens 는 required 예요. Karpenter EC2NodeClass `default` 는 루트 볼륨 암호화가 설정되지 않았어요. ECR 저장소 43개 중 39개가 푸시 시 스캔이 꺼져 있고 스캔된 이미지는 850개 중 0개예요. Polaris 보안 위험 워크로드 74개, prod 28개예요. 클러스터 안 인증서 관리자는 없어요.

### cost

금액 대신 비율로 적어요. 노드 계산 자원의 유휴 비율이 0.95 이고, KRR 기준으로 줄일 수 있는 CPU requests 가 5.26코어예요. 위 resources 표가 같은 내용이에요. NLB `acme-db-shared` 는 24시간 요청과 바이트가 0 이에요. build-arm64 노드 `ip-10-0-2-144` 는 7일 CPU p95 0.13% 지만 CI 러너용이고 20분 비면 정리돼요. EKS 1.32 가 표준 지원을 넘겨 연장 지원 요금이 붙어요. ECR 수명 주기 정책 없음과 태그 없는 이미지도 있어요. SpotToSpotConsolidation 이 꺼져 있어 스팟 노드 `default-zj4kx` 가 733번 "can't replace a spot node with a spot node" 로 남았어요.

### tenancy

이웃 간섭은 판단할 여지가 없었어요. 7일 동안 CPU 90% 를 1분 넘긴 노드가 없고 이웃 때문에 스로틀링된 prod 네임스페이스도 없어요. summary.json tenancy.noisy. `prod-app-l-backend` 는 7일 CPU 최대 2.156코어가 중앙값 0.011코어의 194.6배인데, 이번 창에서는 KEDA 워커가 따로 띄운 노드에서 돌았어요.

테넌트 경계 표예요.

| 네임스페이스 | ResourceQuota | LimitRange | NetworkPolicy | PSA |
|---|---|---|---|---|
| prod-app-r | 없음 | 없음 | 0, 적용 안 됨 | 없음 |
| prod-app-q | 없음 | 없음 | 1, 적용 안 됨 | 없음 |
| prod-app-m | 없음 | 없음 | 0 | 없음 |
| prod-app-o | 없음 | 없음 | 0 | 없음 |
| prod-app-l-backend | 없음 | 없음 | 0 | 없음 |
| prod-app-p | 없음 | 없음 | 1, 적용 안 됨 | 없음 |
| prod-app-n | 없음 | 없음 | 0 | 없음 |
| app-s-prod | 없음 | 없음 | 1, 적용 안 됨 | 없음 |

dev 파드가 prod 파드와 같은 노드 다섯 대에 섞여 있어요. `ip-10-0-1-139` 에는 prod 20개와 dev 11개가 있어요. 쿼터 없음 13개는 low 로 내렸어요.

### node OS

노드 `ip-10-0-1-139` 의 루트 디스크가 50 GB 중 82% 로 9.2 GB 남았고 그중 containerd 가 36.5 GB 예요. 2026-11-02 에도 이미지 정리가 3번 실패했고 containerd shim 정리 경고가 24시간에 68줄이에요. 2026-10-26 의 87% 보다는 내려왔어요. 이 노드가 만료 뒤에도 교체되지 않아서 쌓인 거라 문제 2 와 원인이 같아요. AL2 노드 6대는 cgroup v1 이에요. SSM 에 등록되지 않은 관리형 노드 `ip-10-0-1-117`, `ip-10-0-2-60` 은 OS 를 보지 못했어요. `ip-10-0-2-135` 에서 2026-10-10 에 포트 9095 SYN flooding 커널 메시지가 한 번 있었어요. `ip-10-0-1-203` 의 네트워크 오류 317건은 이미 지워진 노드의 잔상이에요.

```bash
# ip-10-0-1-139 에서, 읽기 확인 뒤 운영자가 직접
sudo crictl imagefsinfo
sudo crictl rmi --prune
```

### platform

문제 5 예요. Kubernetes 1.32.13 은 표준 지원이 끝난 지 225일이고 연장 지원 중이에요. Karpenter 0.37.0 은 Kubernetes 1.30 까지만 지원하고, Karpenter 로그에 버전 미지원 오류가 2026-11-02 08:46 UTC 에 한 줄 있어요. EC2NodeClass `default` 가 AL2 이고 AMI 를 고정하지 않았어요. EKS 는 2025-11-26 부터 AL2 AMI 를 내지 않고 1.33 부터는 AL2 AMI 가 없어요. 관리형 노드 그룹 AMI 는 329일 됐어요. 애드온은 aws-ebs-csi-driver v1.37.0 → v1.67.2, vpc-cni v1.19.0 → v1.23.2, coredns v1.11.3 → v1.11.4, kube-proxy v1.32.0 → v1.32.13 이 밀려 있어요. 감사 로그가 꺼져 있어요. VPC CNI prefix delegation 이 꺼져 있어 IP 사용 50% 넘는 노드가 여섯 대예요. 계정 VPC 쿼터 3/5 는 low 로 내렸어요. apiserver LIST 0.705초와 PATCH 0.709초 p99 는 수집 중에 측정된 값이라 세지 않았어요.

## 5. 없는 것 목록

| Finding | Status | Severity | Why it should exist | Proposal |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same nod | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. A backup is not a backup until a |
| `observability.no-slo.cluster` | warn | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `observability.no-event-retention.cluster` | fail | high | Kubernetes events are kept for only one hour by default. FailedScheduling, OOMKilling and Unhealthy from the night are gone by morning. The most undervalued material is lost. | Ship events to Loki or Elasticsearch with kubernetes-event-exporter. Alternatively, the promtail/alloy event source if Loki exists, or `[INPUT] kubernetes_events` with fluent-bit (detection recognizes |
| `security.no-certificate-manager.cluster` | warn | medium | When TLS certificate renewal is manual, services keep going down from expiry. cert-manager (or ACM plus ALB on EKS) automates renewal. On EKS, ALBs using ACM certificates work without cert-manager, bu | Install cert-manager, or if ACM is in use, suppress this check in config.yaml with a reason. |
| `hygiene.no-progressive-delivery.cluster` | fail | info | A rolling update is "replace everything", so a defect in the new version reaches all traffic immediately. Without a canary tool (some traffic -> check metrics -> expand), deployment verification depen | As services grow, automate canary judgment with Argo Rollouts (same ecosystem as Argo CD) + AnalysisTemplate (ALB 5xx, p95 Prometheus queries). |

Expected families missing (inventory): backup, event-retention, slo, certificates, progressive-delivery.

## 6. 억제, 도구 없음, 미수집

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in full mode 0: none
- Skipped or errored 3: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing)

## 7. 부록

### 7-1. 실행한 수집기와 스텝

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

### 7-2. 평가한 체크

365 checks: disabled 2, done 358, llm 2, skip 3. Load errors: none.

### 7-3. 서명 일치와 미분류 오류

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

### 7-4. LLM 이 직접 읽은 원본 파일

inventory.json
findings-draft.json
summary.json
diff.json
events.json
collect-result.json
objects/deployments.json
objects/pods.json
objects/statefulsets.json
objects/configmaps.json
objects/nodes.json
objects/nodepools.karpenter.sh.json
objects/persistentvolumeclaims.json
objects/storageclasses.json
objects/services.json
metrics/disk_usage_ratio.json
metrics/node_cpu_request_ratio.json
metrics/node_memory_request_ratio.json
metrics/cpu_throttle_ratio_5m.json
metrics/cpu_limit_p95_ratio_7d.json
metrics/namespace_cpu_throttled_ratio_7d.json
metrics/memory_p95_7d_bytes.json
metrics/memory_limit_p95_ratio_7d.json
metrics/oom_events_7d.json
aws/describe-security-groups.json
extra/lb-security-groups.txt
extra/lb-security-group-rules.txt
../2026-10-27T15-30-14/findings-draft.json
../2026-10-27T15-30-14/summary.json
../2026-10-27T15-30-14/objects/pods.json
~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/report.md
~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/llm/tool-notes.md
~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02/llm/adjustments.md

스냅샷 밖에서 읽은 것, 읽기 전용 명령 두 개:
- `AWS_PROFILE=acme aws --region us-east-1 elbv2 describe-load-balancers --names acme-db-shared k8s-app-svc-31ecf1515b --query 'LoadBalancers[].{name:LoadBalancerName,scheme:Scheme,sgs:SecurityGroups}'` → extra/lb-security-groups.txt
- `AWS_PROFILE=acme aws --region us-east-1 ec2 describe-security-groups --group-ids <위 결과의 보안 그룹 세 개> --query 'SecurityGroups[].{id:GroupId,name:GroupName,in:IpPermissions[]...}'` → extra/lb-security-group-rules.txt

### 7-5. 1차 결과 전체, 모든 fail 과 warn 을 코드 결과 그대로

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
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret` | fail | medium | Ready=False (SecretSyncedError) for 7700.8 hours: could not get secret data from provider |
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
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node node-1-139 (r8gd.xlarge spot): age 961.8h, 241.8h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 19728}. do-not-disrupt pods on this node 1: prod-app-m/app-m-admin-57f5fcc58d-khsh5 |
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
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend` | warn | low | HPA dev-app-n/app-n-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 36.3 days ago |
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

### 7-6. 도구 메모, kubegap 자체에 대한 것

번호는 2026-10-26 16:47 full 리포트의 메모 41~48 에서 이어가요. 직전 full 스냅샷 2026-10-27 15:30 에는 리포트가 없어서 메모도 없어요.

이번에 다시 확인한 이전 메모예요. 3 시스템 노드의 `vpccni.node-ip-exhaustion` high 는 재현됐어요. `ip-10-0-1-241` 6/9, `ip-10-0-2-218` 13/15 예요. 4 계정 VPC 쿼터의 `eks.service-quota-near-limit` high 도 재현됐어요. 5, 32, 38, 45 SSM 미등록 노드 명령 실패는 재현됐고 이번 실패 24개 중 19개예요. 45 의 ECR "정책 없음" 4건이 `_summary.failed` 에 들어가는 것도 그대로예요. 25 스케줄러 근거의 `<n>/<n> nodes are available` 마스킹도 그대로예요. 44 삭제된 노드의 `node.network-errors` 는 `<ip>:9100:eth0` 317건으로 재현됐어요. 46 `platform.k8s-version-eol` 근거 "end of support 2026-03-23 D+225" 에 출처가 없는 것도 그대로예요. 47 비용 체크 근거가 달러로 쓰인 것도 그대로라 이번에도 비율만 인용했어요. 48 5분 순간값 하나로 `resources.cpu-throttling` 이 fail/high 를 내는 것은 `prod-app-m/app-m-frontend` 로 재현됐어요. 5분 0.26, 7일 제한 대비 p95 0.08, 네임스페이스 7일 스로틀링 0.016 이에요. 41 5xx 합이 고정되는 현상은 이번 `api.example-b.ai` 5xx 가 78건으로 바뀌어 재현되지 않았어요. 43 연속 수집은 이번 간격이 6일 20시간이라 해당이 없어요.

49. **`resilience.n-plus-one` 이 2% 여유 안에서 통과하고, 앱 노드 제약을 합산에 넣지 않아요.** `summary.json` resilience.n_plus_one 은 가장 큰 노드를 빼면 메모리 46.6 GB, requests 47.5 GB 인데 `ok: true` 예요. `lib/resilience.py` `_n_plus_one` 이 `req_mem <= rest_mem * 1.02` 로 비교해서 46.6 × 1.02 = 47.53 GB 안에 들어가요. 또 이 합산은 클러스터 전체 allocatable 을 쓰지만, 앱 파드는 nodeSelector `workload-type: app` 때문에 `ip-10-0-1-139` 와 `ip-10-0-1-62` 두 대에만 갈 수 있어요. `ip-10-0-1-139` 의 CPU requests 3.50코어가 갈 곳은 `ip-10-0-1-62` 의 남은 0.16코어뿐이에요. metrics/node_cpu_request_ratio.json 0.8928, 0.9170. `cannot_fit_elsewhere` 는 파드 하나씩만 봐서 비어 있어요. 제안: 가장 큰 노드의 파드를 그 파드들이 갈 수 있는 노드의 남은 allocatable 합과 비교하는 "적격 노드 기준 N+1" 을 같이 내기.
50. **`traffic.db-exposed` 가 NLB 보안 그룹을 읽지 않아요. collector 후보예요.** `acme-db-shared` 는 Service 가 없는 NLB 라 근거가 `sourceRanges None` 이에요. 스냅샷 밖에서 `aws elbv2 describe-load-balancers` 로 보안 그룹 id 를 얻고 `aws ec2 describe-security-groups` 로 규칙을 읽으니 DB 포트마다 /32 주소 4개 이하만 허용이었어요. 같은 방법으로 Kafka NLB 는 0.0.0.0/0 이 맞았어요. extra/lb-security-groups.txt, extra/lb-security-group-rules.txt. `aws/describe-security-groups.json` 에는 클러스터 보안 그룹 두 개만 있어요. 제안: `collect.yaml` 에 LB 보안 그룹 두 명령을 넣고, 0.0.0.0/0 이면 fail, 좁은 허용 목록이면 warn 으로 나누기.
51. **이전 스냅샷에서 건너뛴 체크가 이번에 처음 평가되면 diff 가 "new" 로 셉니다.** Argo CD 점검 항목 13개는 2026-10-27 스냅샷 `findings-draft.json` check_results 에서 `skip`, 이유 `summary.argocdctl.summary missing` 이었어요. 이번에는 `done` 이고 그 결과 `argocd.admin-account-no-sso`, `argocd.components-not-ha`, `argocd.default-project-wildcard`, `argocd.notifications-not-configured`, `argocd.prod-tracks-moving-ref`, `argocd.version-eol` 여섯 개가 `diff.json` findings.new 에 있어요. 클러스터 변화가 아니라 평가 범위 변화예요. 제안: A 에서 skip 이던 체크의 발견 사항은 "처음 평가됨" 으로 따로 분류하기.
52. **KEDA 가 0 에서 늘린 워커의 정상적인 노드 대기가 fail/high 로 올라와요.** `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker` fail/high 와 `events.tracked-warning-reasons.FailedScheduling` fail/high 의 이번 창 12건은 전부 KEDAScaleTargetActivated 직후의 파드예요. events.json 에서 01:41:06Z 생성, 01:41:08Z Nominated, 01:42:43Z 새 노드에 스케줄됐어요. 제안: 소유자가 ScaledObject 대상 Deployment 이고 Nominated 뒤 몇 분 안에 Scheduled 된 파드는 warn 으로 두기.
53. **`observability.alerts-always-firing.KubePodNotReady` 가 이미 멈춘 알림을 fail 로 내요.** 7일 표본 169,042개로 fail 인데 `summary.json` observability.alerts.firing_now 에 KubePodNotReady 가 없고 Failed 파드는 0개예요. 표본은 지워진 Failed 파드 12개가 남긴 거예요. 제안: 지금 울리지 않으면 warn 으로 내리거나, 최근 24시간 표본 비율을 같이 보기.
54. **스냅샷 루트가 두 군데로 갈릴 수 있어요.** 이 세션 환경에는 `KUBEGAP_HOME` 이 작업 폴더로 설정돼 있었어요. `SKILL.md` 는 `$KUBEGAP_SNAPSHOTS` 만 설명하고 `KUBEGAP_HOME` 은 말하지 않아요. 세션이 처음에 `summarize` 와 `evaluate` 를 `--snapshot ~/.kubegap/snapshots/my-cluster/2026-11-03T11-17-15` 절대 경로로 돌렸고, 두 명령은 경고 없이 그 폴더에 summary.json 과 findings-draft.json 을 만들었어요. 그다음 인자 없는 `diff` 는 `KUBEGAP_HOME` 쪽 스냅샷을 비교했어요. 세션은 `KUBEGAP_HOME` 쪽에서 세 명령을 다시 돌렸고, `~/.kubegap` 쪽에 생긴 두 파일은 지우지 않고 남겨 두었어요. 제안: `--snapshot` 이 유효한 스냅샷 루트 밖을 가리키면 경고하기, `SKILL.md` 에 `KUBEGAP_HOME` 설명 넣기.

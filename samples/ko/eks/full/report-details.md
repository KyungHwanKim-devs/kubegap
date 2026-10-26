# kubegap 리포트 세부 — arn:aws:eks:us-east-1:<account>:cluster/my-cluster (`my-cluster`), full 모드

리포트의 참조용 절반입니다. `scripts/kubegap render-details` 가 스냅샷 파일과 `llm/` 의 LLM 조각으로 조립했습니다. 사람이 읽는 리포트는 옆의 `report.md` 입니다. 표 안의 데이터, 즉 체크 id·근거 문장·숫자는 영어 그대로입니다.

| 항목 | 값 |
|---|---|
| kube 컨텍스트 / 클러스터 | `my-cluster` / arn:aws:eks:us-east-1:<account>:cluster/my-cluster (eks, v1.32.13-eks-cfb47f5) |
| 실행 시각 / 모드 | 2026-10-26T16:47:02+09:00 / full (collection 329.6 s, 0 steps skipped by mode, 5 failed) |
| 프로파일 | `eks` (detected) |
| kubegap / 룰 / 서명 카탈로그 | 0.1.0 / 0.1.50 / 1.0.15 |
| 노드 / 네임스페이스 / 파드 / CRD | 8 (Ready 8) / 25 / 157 / 47 |
| 컴포넌트 (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| 메트릭 저장소 | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| 로그 저장소 | loki 2.6.1 |
| 노드 접근 | ssm (EKS: SSM send-command); SSM unregistered 2 |
| 스냅샷 | `~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02` |

## 1. 1차 결과 집계와 최종 조정

| 심각도(기본) | fail | warn | 같은 모드의 지난 실행 대비 |
|---|---|---|---|
| critical | 1 | 2 | fail +0 · warn +0 |
| high | 38 | 20 | fail +0 · warn +0 |
| medium | 108 | 171 | fail +0 · warn +0 |
| low | 18 | 140 | fail +0 · warn +0 |
| info | 2 | 0 | 같은 모드의 지난 실행 없음 |

Checks 361: evaluated 356, disabled by profile 2, skipped 1, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. 1차 결과와 최종 결과의 차이

| finding id | 1차 결과 | 최종 결과 | 이유 |
|---|---|---|---|
| `resilience.prod-concentration.node-1-139` | fail / high | fail / critical | 규칙 ① 증상 연결. 16:27 리포트에서 이어받았어요. 두 번째 앱 노드가 26시간 동안 네 번 스팟 회수됐고 마지막은 오늘 14:17 KST 였어요. `logs/pods/karpenter/karpenter_karpenter.log` 의 "initiating delete from interruption message" 가 2026-10-25T20:09:52Z, 2026-10-26T03:33:23Z, 05:17:28Z 에 있어요. 회수 때마다 `prod-app-p/app-p-backend` 가 멈췄어요. |
| `resilience.n-plus-one.cluster` | warn / high | warn / critical | 규칙 ③. 가장 큰 노드를 빼면 메모리 46.0 GB 에 requests 47.5 GB 라 N+1 이 안 돼요. `summary.json` resilience.n_plus_one 의 margin 0.02. critical 로 셉니다. |
| `observability.no-slo.cluster` | warn / critical | warn / critical | 규칙 ③, 그대로. critical 로 셉니다. |
| `observability.no-symptom-alerts.cluster` | warn / critical | warn / critical | 규칙 ③, 그대로. 157개 규칙 중 사용자 증상을 보는 규칙 0개. 지금 울리는 알림은 KubePodNotReady 12개, KubeControllerManagerDown, KubeSchedulerDown, CPUThrottlingHigh 1개, InfoInhibitor 2개, Watchdog 이에요. `summary.json` observability.alerts.firing_now. |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail / medium | fail / high | 이 NodeClaim 뒤의 노드가 prod 파드 42개 중 28개를 들고 있고 720시간 만료에서 54.9시간이 지났어요. `karpenter.sh/do-not-disrupt` 파드 `prod-app-m/app-m-admin-57f5fcc58d-khsh5` 하나가 교체를 14,171번 막았어요. `events.json` DisruptionBlocked. 16:27 리포트와 같은 판단이에요. |
| `resources.node-request-usage-gap.node-1-139` | fail / medium | fail / high | 규칙 ①. CPU requests 가 allocatable 의 99.5% 인데 7일 p95 사용은 5.6% 예요. `metrics/node_cpu_request_ratio.json` 0.9948, `metrics/node_cpu_usage_ratio_p95_7d.json` 0.0558. 이 때문에 회수 때 쫓겨난 파드가 이 노드로 못 돌아오고 새 노드를 80초쯤 기다렸어요. |
| `resilience.single-replica-in-prod.prod-app-p/app-p-backend` | fail / medium | fail / high | 규칙 ①. 레플리카 1개가 네 번의 회수에서 전부 장애였어요. 14:52 리포트 기준 14:17 KST 에 1분 41초. 아직 replicas 1 이에요. `objects/deployments.json` generation 5. |
| `resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend` | fail / medium | fail / high | 규칙 ①. Recreate 에 레플리카 1개라 재스케줄과 배포가 전부 장애예요. 아직 Recreate 예요. `objects/deployments.json`. |
| `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` | fail / high | warn / medium | 규칙 ⑤ 두 단계 내림. 수집 시각의 5분 스로틀링 비율은 0.419 가 맞아요. `metrics/cpu_throttle_ratio_5m.json`. 그런데 이 컨테이너의 7일 p95 사용은 0.0045코어로 500 m 제한의 0.9% 고 `metrics/cpu_limit_p95_ratio_7d.json` 0.0089, prod-app-p 네임스페이스의 7일 스로틀 비율은 0.5% 예요 `metrics/namespace_cpu_throttled_ratio_7d.json`. 이전 스냅샷 다섯 개 어디에도 이 파드는 1% 선을 넘은 적이 없고, CPUThrottlingHigh 알림은 아직 pending 이에요 `metrics/alerts_pending_now.json`. `app-p-api.my-cluster` 은 24시간 5xx 0건, p95 평균 0.78초예요 `summary.json` traffic.ingresses. 수집 직전에 시작된 짧은 CPU 몰아 쓰기로 보여 증상 없는 warn 으로 둬요. 다음 점검에서 또 보이면 올려요. |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend` | warn / medium | warn / high | 규칙 ①. `api.example-b.ai` 가 24시간 동안 120,706건 중 723건을 5xx 로 응답했어요. 비율 0.60%, 시간당 최대 116건. `aws/alb-metrics.json` 타깃 그룹 k8s-app-svc-d65740e6d5. 이걸 보는 알림이 없어요. 16:27 리포트와 같은 이유예요. |
| `traffic.ingress-5xx-ratio.prod-app-n/app-n-admin-frontend` | warn / medium | warn / low | 어드민 호스트에서 24시간 312건 중 2건이에요. `summary.json` traffic.ingresses. 비율로 보기엔 표본이 너무 작아요. |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn / high | warn / low | `build-arm64` 풀의 CI 러너는 Karpenter 가 노드를 띄울 때까지 기다리는 게 원래 동작이에요. 풀은 비면 20분 뒤 정리돼요. `summary.json` scaling.karpenter.nodepools. 2줄, 사용자 트래픽 없음. |
| `controlplane.scheduler-unschedulable.dev-app-n/app-n-frontend` | warn / high | warn / medium | 규칙 ④ 프로필 맥락. dev 네임스페이스고 prod 파드와 같은 14:17 KST 회수 때 생긴 23줄이에요. |
| `controlplane.apiserver-5xx.cluster` | warn / high | warn / medium | 503 이 초당 0.0037 로 측정된 시각은 수집 중이었어요. `metrics/apiserver_5xx_rate.json` 16:48:16 KST. 16:27 full 수집이 끝나고 19분 뒤에 이번 수집이 시작됐어요. kubegap 자신의 요청이 섞였을 가능성이 커요. 사용자 영향으로 세지 않아요. |
| `controlplane.apiserver-latency.LIST` | warn / medium | warn / low | LIST p99 0.618초는 수집 중에 측정된 값이에요. `metrics/apiserver_p99_latency_by_verb.json` 16:48:16 KST. 16:27 수집과 19분 간격이고, 16:27 에 올라갔던 PATCH 는 이번에 0.096초로 돌아왔어요. 수집 자체가 만든 값이에요. |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn / high | warn / medium | working set / limit 0.775 예요. `metrics/prom_rss_vs_limit.json`. 16:27 의 0.692 보다 올랐지만 14:52 의 0.892 보다 낮고, OOMKill 은 19.8일 전 한 번뿐이에요. 제한 검토는 필요하지만 high 는 아니에요. |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn / high | warn / low | 19.8일 전 OOMKill 한 번이고 이후 재발 없음. `metrics/oom_events_7d.json` 에는 loki 만 있어요. |
| `node.network-errors.<ip>:9100:eth0` | fail / medium | fail / info | 노드 `ip-10-0-2-149` 는 12:33 KST 에 스팟 회수돼 지금 없어요. `inventory.json` nodes 에 없음. 4,857건은 삭제된 인스턴스의 24시간 `increase()` 잔상이에요. 도구 메모 2, 20, 30, 37 패턴. |
| `node.network-errors.<ip>:9100:eth0` | warn / medium | warn / low | 오늘 14:17 KST 에 생긴 노드에서 24시간 147건이에요. 그 노드 dmesg 의 NIC 오류 수는 0 이에요. `summary.json` nodeos.nodes[].kernel.counts. 새 노드 패턴, 도구 메모 2. |
| `eks.service-quota-near-limit.aws-account` | warn / high | warn / low | "VPCs 3 of 5" 는 계정 쿼터라 클러스터가 런타임에 쓰지 않아요. 클러스터 쪽 쿼터는 리스너 규칙 47%, 타깃 그룹 40%, 인증서 36% 로 전부 60% 아래예요. 두 단계 내림, 16:27 리포트와 같음. |
| `vpccni.node-ip-exhaustion.node-1-241` | warn / high | warn / low | 시스템 노드 `system-ondemand` t8i.small, IP 9개 중 6개, "no available IP" 이벤트 0건, max-pods 11 로 묶여 있어요. 두 단계 내림. |
| `vpccni.node-ip-exhaustion.node-2-218` | warn / high | warn / low | 시스템 노드 t8i.medium, IP 15개 중 13개, "no available IP" 이벤트 0건, max-pods 17. 두 단계 내림. |
| `events.tracked-warning-reasons.UpdateFailed` | warn / high | warn / medium | 1,639건 전부 dev ExternalSecret `database/mysql-app-n-secret` 하나예요. "Secret does not exist", `logs/pods/external-secrets/external-secrets_external-secrets.log`. 2025-12-17 부터 실패 중. dev 전용이라 `security.externalsecret-not-ready`, `eso.provider-api-errors`, `operators.unhealthy-condition` 과 한 항목으로 묶어요. |
| `logs.signatures.external-secrets.provider-error` | warn / high | warn / medium | 같은 dev ExternalSecret 하나예요. 로그 32줄. |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail / high | fail / medium | dev 네임스페이스, 규칙 ④. prod 타깃 그룹 4개는 high 그대로예요. 문제 4. |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail / high | fail / medium | dev 네임스페이스, 24시간 요청 0건, 규칙 ④. |
| `tenancy.prod-without-quota.*` (13개) | warn / medium | warn / low | 7일 동안 어떤 노드도 CPU 90% 를 1분 넘긴 적이 없고 `summary.json` tenancy.noisy.nodes_saturated_7d 비어 있음, 이웃 때문에 스로틀링된 prod 네임스페이스도 없어요. 여기서 쿼터는 위생이지 당장의 위험이 아니에요. 16:27 리포트와 같은 내림. |

## 2. 지금 fail 인 critical·high, 1차 결과

| 발견 사항 | 심각도 | 연속 실행 수 | 근거 |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `controlplane.scheduler-unschedulable.prod-app-m/app-m-api` | high |  | 24h 'Unable to schedule pod; no fit' 19 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubern |
| `controlplane.scheduler-unschedulable.prod-app-m/app-m-backend` | high |  | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubern |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-embedding-server` | high | 11 | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubern |
| `controlplane.scheduler-unschedulable.prod-app-p/app-p-backend` | high | 11 | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubern |
| `eks.no-backup-policy.cluster` | high | 11 | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | high | 11 | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | high | 11 | kubelet image GC could not free space. Disk is full of in-use images and logs. 906 occurrences total (1 events, trend over 30 snapshots [417, 422, 439, 450, 454, 524, 533, 574, 585, 594, 611, 617, 624, 628, 630, 658, 668 |
| `karpenter.ec2nodeclass-al2.cluster` | high | 11 | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `node.disk-usage.<ip>:9100:/` | high | 11 | usage 0.86 |
| `observability.failure-mode-uncovered.OOMKill` | high | 11 | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 204MB |
| `observability.no-event-retention.cluster` | high |  | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-cfb47f5, end of support 2026-03-23 D+217 (217 days past EOL) |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes up to 1.30, the cluster runs 1.32.  |
| `resilience.prod-concentration.node-1-139` | high |  | Node node-1-139 (pool default, spot) holds prod pods 28/42 (0.67), 22 workloads: ['prod-app-r/app-r', 'prod-app-q/app-q-ai', 'prod-app-q/app-q-backend' |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | high |  | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-backend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constr |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | high |  | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constr |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: 5m throttling ratio 0.28 (stalled for 28% of periods) |
| `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` | high |  | pod app-p-postgresql-0: 5m throttling ratio 0.42 (stalled for 42% of periods) |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | high |  | ['pod loki-stack-promtail-dc9mw: 7d memory working set p95 / limit = 0.90', 'pod loki-stack-promtail-hxxt7: 7d memory working set p95 / limit = 0.81'] |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | high |  | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (1.3 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | high |  | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | high |  | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 2.0,  |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | high |  | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | high |  | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | high |  | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | high |  | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0,  |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | high |  | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0,  |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | high |  | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-31ecf1515b-96449818f244837f.elb.us-east-1.amazonaws.com'], sourceRanges None. DB po |
| `traffic.db-exposed.nlb/acme-db-shared` | high |  | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 5432, 6379, 7687], exposure internet-facing, addresses ['acme-db-shared-d7d643f6896a3b2b.elb.us-east-1.amazonaws.com'], sourceRanges None. no TargetG |
| `vpccni.node-ip-exhaustion.node-1-139` | high |  | node node-1-139 (r8gd.xlarge, pool default): pod IPs 43/56 (0.768), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 28. prefix delegation False |

## 3. 같은 모드의 지난 실행 이후 변화

Compared `2026-10-26T16-27-58` → `2026-10-26T16-47-02` (rubric 0.1.50 → 0.1.50).

- **New (2)**: `controlplane.apiserver-latency.LIST` (warn/medium), `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` (fail/high)
- **Resolved (2)**: `controlplane.apiserver-latency.PATCH` (warn/medium), `resources.cpu-throttling.prod-app-o/deploy/app-o-frontend:frontend` (warn/high)
- **Changed (1)**: `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` (['fail', 'warn']/['high', 'high'])
- **Rename suspects (0)**: none
- **Objects**: added 0, removed 0, changed 0
- **Warning events**: FreeDiskSpaceFailed +4 (Node/node-1-139), UpdateFailed +1 (ExternalSecret/database/mysql-app-n-secret)
- **Persisted (Toil)**: 415 findings present in all 11 runs checked, 500 in 3 or more; top checks: `resources.cpu-request-overprovisioned` 39, `resources.krr-recommendation` 31, `traffic.alb-deregistration-vs-grace` 28, `resilience.no-prestop` 21, `scaling.no-hpa-serving-prod` 21, `resilience.exec-probe` 17, `resilience.single-replica-in-prod` 16, `resources.memory-request-overprovisioned` 16

### 3-1. 왜 바뀌었나

16:27 full 점검과 이번 점검 사이의 19분은 조용했어요. 노드가 늘거나 줄지 않았고, 스팟 회수도 없었어요. `logs/pods/karpenter/karpenter_karpenter.log` 의 마지막 "initiating delete from interruption message" 는 여전히 2026-10-26T05:17:28Z, 14:17 KST 예요. Deployment, StatefulSet, DaemonSet, Helm 릴리스 어느 것도 spec 이 바뀌지 않았고 `diff.json` objects.changed 는 비어 있어요. 멈추지 않는 카운터 세 개만 올라갔어요. `ip-10-0-1-139` 의 `FreeDiskSpaceFailed` 902 → 906, dev ExternalSecret `database/mysql-app-n-secret` 의 `UpdateFailed` 1,638 → 1,639, 만료 노드를 붙잡는 `DisruptionBlocked` 14,163 → 14,171 이에요.

새 발견 사항 2개는 둘 다 측정값이지 클러스터 변경이 아니에요. `prod-app-p/app-p-postgresql-0` 의 5분 CPU 스로틀링 비율이 42% 로 처음 1% 선을 넘었어요. 이 파드는 이전 스냅샷 다섯 개 어디에도 없었고 7일 p95 사용은 제한의 0.9% 라, 수집 직전에 시작된 짧은 CPU 몰아 쓰기로 보고 warn 으로 내렸어요. apiserver LIST p99 0.618초는 16:27 수집 19분 뒤에 다시 수집하면서 생긴 값이고, 16:27 에 같은 이유로 올라갔던 PATCH p99 는 0.096초로 돌아와 해소됐어요. `prod-app-o/app-o-frontend` 의 스로틀링은 14% 에서 8% 로 내려가 해소됐고, `prod-app-m/app-m-frontend` 는 27% 에서 24% 로 내려와 fail 에서 warn 으로 바뀌었어요. 셋 다 Deployment 는 그대로라 트래픽의 오르내림이에요. Prometheus 의 working set 은 제한의 0.692 에서 0.775 로 올랐고 OOMKill 은 없어요.

룰 버전은 0.1.50 그대로고 평가된 체크도 같은 356개라 기준 변경은 없어요.

## 4. 영역별 세부

### Resources
체크 15개, pass 449, fail 33, warn 95. 항목 네 개예요.

**200 m CPU 제한에 막히는 Next.js 프론트엔드와 Prometheus, 그리고 이번에 처음 보인 app-p PostgreSQL.** 수집 시각에 CPU 제한 때문에 100 ms CFS 주기의 10% 넘게 멈춘 컨테이너가 일곱 개예요. `prod-app-p/app-p-postgresql-0` 42%, `monitoring/prometheus-kube-prometheus-stack-prometheus-0` 28%, `prod-app-m/app-m-frontend` 두 파드 24% 와 23%, `dev-app-m/app-m-frontend` 18%, `dev-app-o/app-o-frontend` 16%, `prod-app-o/app-o-frontend` 8% 예요. 출처는 `metrics/cpu_throttle_ratio_5m.json` 이에요. 프론트엔드 셋은 한 템플릿을 써요. request 10 m, limit 200 m, 메모리 384 Mi 예요. 출처는 `objects/deployments.json`. Prometheus 는 활성 시리즈 161,206개에 limit 500 m 이에요. app-p PostgreSQL 은 request 100 m, limit 500 m 인데 7일 p95 사용이 0.0045코어라 제한의 0.9% 예요. 출처는 `objects/statefulsets.json`, `metrics/cpu_limit_p95_ratio_7d.json`. 이전 스냅샷 다섯 개에 없던 값이고 CPUThrottlingHigh 알림은 pending 이라 warn 으로 내렸어요. 다음 점검에서 또 보이면 autovacuum 이나 배치 쿼리 시각과 맞춰 볼 필요가 있어요. 공유 프론트엔드 차트 제안:
```yaml
resources:
  requests: { cpu: 100m, memory: 256Mi }
  # cpu limit 없음. 메모리 limit 은 유지
  limits: { memory: 384Mi }
```
Prometheus 는 kube-prometheus-stack values 의 `prometheus.prometheusSpec.resources` 에서 `cpu` limit 을 1 로 올리거나 빼요. app-p PostgreSQL 은 limit 을 1 로 올리거나 빼고, 그 전에 42% 가 반복되는지 한 번 더 봐요.

**리소스 조정표, 실제 사용보다 훨씬 큰 requests.** CPU request 가 7일 p95 의 4배를 넘는 컨테이너가 39개 `resources.cpu-request-overprovisioned`, fail 4 warn 35, 메모리는 15개 `resources.memory-request-overprovisioned` 예요. KRR 은 요청된 6.68코어 중 1.45코어면 된다고 봐요. 줄일 수 있는 CPU 5.23코어, 출처는 `summary.json` resources.krr.totals, fail 13 warn 18. 노드 세 대는 CPU 의 96~99% 를 요청해 놓고 6~9% 를 써요. `resources.node-request-usage-gap` fail: `ip-10-0-1-139` 0.99/0.06, `ip-10-0-2-60` 0.99/0.06, `ip-10-0-1-117` 0.96/0.09. warn: `ip-10-0-1-62` 0.71/0.03, `ip-10-0-2-135` 0.74/0.05. request 기준 상위 5개는 app-l-neo4j 500 m 와 4 Gi, app-l-embedding-server 500 m 와 4 Gi 두 개, app-l-backend 500 m 두 개, app-p-backend 500 m, app-r 예요. 전체 목록은 7-5 에 있어요. `resources.large-request-binpacking`: embedding 서버와 neo4j 는 각각 노드 중앙값 allocatable 의 58% 를, arm64 CI 러너는 104% 를 요청해요. 이 표의 비용 쪽 관점이 `cost.idle-compute-high` 유휴 비율 0.95 와 `cost.request-waste` 줄일 수 있는 5.23코어예요.

**request 없음, limit 없음, 힙이 limit 과 같음.** `prod-app-l-backend/tts-proxy` 는 BestEffort 예요. `resources.besteffort-in-prod`, `resources.no-memory-limit`, 컨테이너 tailscale 과 forwarder. `middleware/kafka-controller` 의 jmx-exporter 는 MaxRAMPercentage 100 에 128 MiB limit 이라 힙이 limit 과 같아요. `resources.jvm-heap-vs-limit`. `monitoring/loki-stack-promtail` 은 두 노드에서 메모리 limit 의 90% 와 81% 에 있어요. `resources.memory-limit-near-p95`.

**OOM.** `monitoring/loki-stack-0` 이 2026-10-25T00:15Z 에 512 Mi limit 에서 OOMKilled 됐고 저장소는 emptyDir 이에요. `resources.oomkilled`, `resources.oomkilled-repeated`. Observability 의 Loki 항목과 묶어요. Prometheus 의 OOMKill 한 번은 19.8일 전이라 low 로 내렸어요.

### Scaling
체크 27개 Karpenter·KEDA 포함, pass 176, fail 7, warn 43.

**Karpenter 가 교체하지 못하는 만료 노드.** NodeClaim `default-n44bh` 의 노드 `ip-10-0-1-139` 는 774.9시간 됐고 `expireAfter: 720h` 에서 54.9시간 지났어요. `prod-app-m/app-m-admin-57f5fcc58d-khsh5` 의 `karpenter.sh/do-not-disrupt` 애노테이션이 14,171번 막았어요. `scaling.karpenter-expired-not-replaced`, high 로 올림. `app-amd64-fallback` 풀은 노드 0대고 10% 예산이 83,953번 막혔어요. `events.json` DisruptionBlocked. 스팟 간 통합은 꺼져 있어요. `karpenter.spot-to-spot-consolidation-off`, 스팟 중단으로 끝난 NodeClaim 254개.

**HPA.** prod 서빙 워크로드 21개에 HPA 가 없고 `scaling.no-hpa-serving-prod`, HPA 13개는 7일 동안 한 번도 안 움직였어요 `scaling.hpa-never-scaled`. 모든 노드의 CPU p95 가 10% 아래라 위생 항목이에요. 전체 목록은 7-5.

### Observability
체크 63개 Prometheus·Alertmanager·Grafana·Loki 포함, pass 145, fail 15, warn 38. 항목 네 개예요.

**증상 알림도 SLO 도 없음.** 알림 규칙 157개 중 증상 0, 원인 138, 앱 메트릭 19 예요. SLO 나 번 레이트 규칙은 없어요. `observability.no-symptom-alerts`, `observability.no-slo`, 둘 다 critical. 규칙이 하나도 없는 장애 유형 셋: OOMKill, 스케줄링 실패, VPC CNI IP 고갈. `observability.failure-mode-uncovered`, `summary.json` observability.failure_modes.uncovered. 라우팅은 기본 수신자 `slack-system`, critical 은 `slack-sre`, Watchdog 은 null 이에요. 15일 동안 한 번도 안 울린 규칙 130개.

**채널을 덮는 오래된 알림.** 지금 울리는 알림 18개: 쫓겨난 파드 12개에 걸린 KubePodNotReady 12개로 가장 오래된 건 17.4일, EKS 에서는 참일 수 없는 KubeControllerManagerDown 과 KubeSchedulerDown 47.8일, Prometheus 의 CPUThrottlingHigh, InfoInhibitor 2개, Watchdog. `observability.alerts-always-firing` 3개, `observability.alert-firing-stale` 6개. 고치는 법은 차트 values 에 `kubeControllerManager.enabled: false`, `kubeScheduler.enabled: false`, `kubeEtcd.enabled: false`, 그리고 Failed 파드 12개 삭제예요.

**emptyDir 위의 스택과 Loki 메모리.** Alertmanager 와 Loki 가 레플리카 1개로 emptyDir 에 데이터를 둬요. `observability.stack-storage-emptydir` 2개. Loki 2.6.1 은 보존 정책이 꺼져 있고 `observability.loki-retention-unbounded`, 1.3일 전에 512 Mi 에서 OOMKilled 됐어요 `observability.loki-oomkilled`. 1시간 넘게 Running 인 파드 139개 중 57개가 Loki 에 없고, CI 노드 `ip-10-0-1-209` 의 파드는 전부 없어요. promtail 에 `workload-type: build` 테인트 톨러레이션이 없어서예요. `observability.log-coverage-gap`. 이벤트 보존 컴포넌트 없음 `observability.no-event-retention`.

**수집 중에 측정된 값.** `controlplane.apiserver-5xx` 초당 0.0037 과 `controlplane.apiserver-latency.LIST` 0.618초는 16:27 수집 19분 뒤에 측정돼 내렸어요. Prometheus working set 은 1,536 Mi limit 의 0.775 예요.

### Traffic
체크 41개 ALB 컨트롤러·CoreDNS 포함, pass 269, fail 10, warn 47. 항목 네 개예요.

**healthy 타깃이 0인 타깃 그룹 여섯 개.** prod 서비스 넷과 dev 서비스 둘이 `/` 헬스체크에서 404 나 307 을 받아요. 파드는 Ready 고 트래픽을 받고 있어요. `prod-app-q/app-q-backend` 404, `prod-app-l-backend/app-l-backend` 404 로 2개 중 0개, `prod-app-o/app-o-frontend` 307, `prod-app-n/app-n-frontend` 307, `dev-app-n/app-n-frontend` 307, `dev-app-t/app-t-backend` 404. `traffic.alb-unhealthy-targets`, `aws/alb-metrics.json` HealthyHostCount_Minimum 0. `alb.ingress.kubernetes.io/healthcheck-path` 를 실제 헬스 경로로 바꾸거나 `success-codes: 200-399` 를 넣어요.

**공개 호스트의 오류율과 지연.** `api.example-b.ai` 는 24시간 120,706건 중 723건 5xx, 0.60%, 시간당 최대 116건, 시간당 p95 최대 5.57초예요. `traffic.ingress-5xx-ratio`, high 로 올림. `api.v1.example-b.ai` 는 86건에 p95 평균 10.92초 최대 35.36초, `app-r.my-cluster` 은 7건에 평균 31.08초인데 요청 수 하한 아래라 지연 체크를 통과해요. 도구 메모 42. `admin.example-c.ai` 312건 중 2건은 low 로 내림. `app-p-api.my-cluster` 은 2,542건에 5xx 0건, p95 평균 0.78초예요.

**노출.** 클러스터 밖에서 만든 NLB `acme-db-shared` 가 3306, 5432, 6379, 7687 을 소스 제한 없이 인터넷에 열어요. `middleware/kafka-controller-0-external` 은 9094 를 열어요. `traffic.db-exposed` 2개, high. 어드민·배포 호스트 7개가 TLS 만 있고 인증 애노테이션 없이 인터넷에 있어요. `deploy.my-cluster`, `admin.example-b.ai`, `admin.example-d.ai`, `admin.example-c.ai`, dev 어드민 3개. `traffic.external-exposure`. ALB 그룹 `acme-prod-lb` 하나에 인그레스 40개, 호스트 47개, 네임스페이스 15개가 dev 와 prod 를 섞어 타요. `traffic.shared-alb-group`.

**ALB 컨트롤러 기본 등록 해제 지연.** 타깃 그룹 28개가 파드 종료 유예보다 긴 300초 기본값을 그대로 써요. `traffic.alb-deregistration-vs-grace`. prod 상위 5개는 app-m-backend, app-m-api, app-l-backend, app-q-backend, app-p-backend. 전체는 7-5. TargetGroupBinding 51개 중 수동 9개, 바인딩 없는 타깃 그룹 1개. 리더 시작 이후 reconcile 오류 41건, apiserver 429/503 응답 123건. `albctl.*`.

### Resilience
체크 40개, pass 692, fail 47, warn 64. 항목 세 개예요.

**만료된 스팟 노드 한 대에 몰린 prod.** `ip-10-0-1-139` r8gd.xlarge, 스팟, 풀 default 가 prod 파드 42개 중 28개, 워크로드 22개를 들고 있어요. `ip-10-0-1-62` r8gd.large, 스팟, 오늘 14:17 KST 생성이 5개를 들어요. 둘 다 us-east-1 예요. `resilience.prod-concentration`, critical. N+1 이 안 돼요. 가장 큰 노드를 빼면 메모리 46.0 GB 에 requests 47.5 GB. `resilience.n-plus-one`, critical. 레플리카 2개짜리 prod Deployment 다섯 개가 두 레플리카를 전부 `ip-10-0-1-139` 에 두고 분산 규칙이 없어요. app-r, app-o-ai 는 3개, app-o-backend, app-l-backend, app-l-frontend. `resilience.replicas-same-node` 5개, high. 모든 레플리카가 한 존에 있는 워크로드 4개 `resilience.replicas-same-zone`. prod PriorityClass 없음 `resilience.priority-inversion`. 매니페스트는 리포트 문제 1.

**워크로드별 복원력 표.** prod 워크로드 16개가 레플리카 1개로 돌아요. 그중 `prod-app-p/app-p-backend` 는 Recreate 까지 써서 둘 다 high 로 올렸어요. readiness 프로브 없음 10개, preStop 없음 21개, exec 프로브 17개, 의존 경로를 찌르는 liveness 11개, 타임아웃이 짧은 DB 프로브 9개, app-o-ai 와 app-o-backend 는 PDB 없음. `resilience.single-replica-in-prod`, `recreate-strategy-serving`, `no-readiness-probe`, `no-prestop`, `exec-probe`, `liveness-dependency-path`, `db-probe-timeout`, `no-pdb`. 노출 기준 상위 5개: app-p-backend 레플리카 1개와 Recreate 로 회수마다 장애, app-q-backend 레플리카 1개, app-n-frontend 레플리카 1개, app-o-frontend 레플리카 1개, app-l-embedding-server PDB 없음에 4 Gi 요청. 전체 행은 7-5.

**백업 없음.** 백업 도구 없음, etcd 스냅샷 0, 백업 CronJob 0, VolumeSnapshot 0. `resilience.no-backup`, critical. 자세한 건 Storage.

### Hygiene
체크 35개, pass 229, fail 8, warn 18.

**AL2 수명 종료.** EKS 업그레이드 인사이트 "Amazon Linux 2 compatibility" 가 1.33 에 대해 ERROR 예요. AL2 이미지는 2025-11-26 에 끊겼어요. `hygiene.eks-upgrade-insight`. Platform 항목과 묶어요.

**레이블과 태그.** 워크로드 38개 중 prod 25개가 노드 8대 중 3대에만 있는 `workload-type` 레이블에 묶여 있고, 33개 중 prod 8개가 5대에만 있는 `acme.ai/role` 에 묶여 있어요. `hygiene.node-label-dependency` 2개. 변할 수 있는 이미지 태그는 tts-proxy 와 CI 오브젝트 셋에 있어요. `hygiene.mutable-image-tag`, `hygiene.polaris-reliability-danger`: tts-proxy, self-hosted-arm64, arc-cool-down, arc-warm-up, redis-insight. Polaris 점수 79.

**변경 상관관계, llm 체크.** 16:27 과 16:47 사이에 바뀐 Deployment 가 없어요. `diff.json` objects.changed 비어 있음. 24시간 안의 spec 변경은 12:14 KST `prod-app-p/app-p-backend` generation 5 하나뿐이고 그 뒤 p95 는 1.19초에서 0.78초로 내려갔어요. app-p-postgresql 의 42% 스로틀링은 어떤 변경과도 겹치지 않아요. 되돌릴 것 없음.

### Storage
체크 20개 EBS CSI 포함, pass 59, fail 6, warn 2. 항목 하나예요.

**복구 경로 없는 prod 데이터베이스 일곱 개, 암호화 안 된 볼륨 위에.** PVC: app-n MySQL 7.8 GB, app-m MySQL 7.8 GB, app-o MySQL 48.9 GB, app-l Neo4j 19.5 GB, app-q PostgreSQL 9.7 GB, app-p PostgreSQL 9.7 GB, app-s PostgreSQL 9.7 GB. `summary.json` storage.pvcs. EBS 볼륨 17개 280 GB 전부 gp3, 전부 암호화 안 됨. `storage.ebs-unencrypted`. DLM 정책 0, AWS Backup 플랜 0. `eks.no-backup-policy`. VolumeSnapshot CRD 가 없어 EBS CSI 스냅샷 사이드카가 오류를 계속 남겨요. `storage.csi-snapshot-unavailable`, `logs.signatures ebs-csi.snapshot-crd-missing`. 30일 안의 스냅샷은 손으로 만든 "pre-delete backup of orphan PVC" 12개뿐이에요. StorageClass 넷 다 `allowVolumeExpansion: false` 고 `encrypted: true` 가 없어요. `storage.no-volume-expansion` 3개, `ebscsi.storageclass-unencrypted`. dev MySQL PVC `dev-app-t/data-app-t-mysql-0` 은 90.2% 찼는데 제자리에서 못 키워요. `storage.pvc-usage-high`. 매니페스트는 리포트 문제 3.

### Security
체크 35개 External Secrets 포함, pass 72, fail 10, warn 8. 항목 세 개예요.

**네트워크.** NetworkPolicy 3개가 있지만 VPC CNI 노드 에이전트가 `--enable-network-policy=false` 라 하나도 적용되지 않아요. `security.networkpolicy-not-enforced`. 사용자 네임스페이스 21개 중 18개에 정책이 없고 prod-app-r, prod-app-m, prod-app-o, prod-app-l-backend, prod-app-n 이 포함돼요. `security.networkpolicy-coverage`. 애드온에서 정책 플래그를 켜고 prod 네임스페이스마다 default-deny 를 넣어요.

**노드 자격 증명과 권한.** 인스턴스 8대 전부 IMDS 홉 제한이 2 라 어떤 파드든 노드 역할에 닿아요. `security.imds-hop-limit`, `karpenter.ec2nodeclass-hardening`. `prod-app-l-backend/tts-proxy` 는 `/dev/net/tun` 을 마운트하고 NET_ADMIN 을 가지며 root 를 허용해요. `security.privileged-or-host-access`. Polaris: 보안 danger 워크로드 74개, prod 28개, 대부분 `privilegeEscalationAllowed` 59 와 `runAsRootAllowed` 58. `security.polaris-security-danger`.

**2025-12-17 부터 실패 중인 dev ExternalSecret 하나.** `database/mysql-app-n-secret`, 키 `dev/app-n-db` "Secret does not exist", UpdateFailed 이벤트 1,639건. `security.externalsecret-not-ready`, `eso.provider-api-errors`, `operators.unhealthy-condition`, `logs.signatures external-secrets.provider-error`, `events.tracked-warning-reasons.UpdateFailed`. 키를 만들거나 ExternalSecret 을 지워요.

### Cost
체크 13개 ECR 포함, pass 8, fail 3, warn 5. 금액은 유저 지시로 쓰지 않아요. 노드 컴퓨트의 유휴 비율 0.95, 요청 6.68코어 대 권장 1.45코어, 줄일 수 있는 5.23코어. `cost.idle-compute-high`, `cost.request-waste`. 노드의 스팟 비중 0.38. 위의 리소스 조정표와 같은 사실이에요. ECR 은 Platform 에 적었어요.

### Tenancy
체크 13개, pass 101, fail 9, warn 23.

**시끄러운 이웃, llm 체크.** `summary.json` tenancy.noisy.nodes_saturated_7d 가 비어 있어요. 7일 동안 어떤 노드도 CPU 90% 를 1분 넘긴 적이 없어 이 창에서는 이웃 영향이 들어설 자리가 없어요. `prod-app-l-backend` 는 중앙값 0.012코어 대비 최대 2.63코어로 226배 몰아 쓰고 쿼터 없이 다른 prod 와 노드를 나눠 써요. `tenancy.burst-tenant-unbounded`. 포화가 생기면 첫 후보예요.

**테넌트 경계 표.** prod 네임스페이스 8개에 경계가 없어요. `tenancy.prod-boundary-missing` fail 5 warn 3. ResourceQuota 없는 prod 네임스페이스 13개는 low 로 내림, LimitRange 없는 테넌트 2개. 공유 노드 세 대가 메모리 limit 을 1.55~1.68배 초과 약정해요. `tenancy.shared-node-limit-overcommit`, `ip-10-0-1-117`, `ip-10-0-1-139` 1.66배, `ip-10-0-2-218`. dev 와 prod 가 `ip-10-0-1-139` 를 같이 써요. `tenancy.dev-shares-prod-nodes`. 전체 표는 7-5.

### Node OS
체크 34개, pass 270, fail 10, warn 3. 항목 두 개예요.

**`ip-10-0-1-139` 의 노드 디스크.** 87% 사용, 50 GB 중 6.8 GB 남음. containerd 가 이미지 45개로 38.9 GB, 파드 로그 294 MB, emptyDir 1.3 GB. `summary.json` nodeos.nodes[].disk 와 .cri. kubelet 이미지 정리가 2026-10-23T01:20Z 부터 906번 실패했어요. "attempted to free 3,424,603,340 bytes, found 0 bytes eligible". `events.tracked-warning-reasons.FreeDiskSpaceFailed`, `node.disk-usage`, `logs.signatures kubelet.image-gc-failed`, `containerd.shim-error`. 쫓겨난 파드 12개가 Failed 상태로 남아 있어요. prod-app-l-backend 7, prod-app-r 2, app-s-prod 2, dev-app-o 1. `objects/pods.json`. 매니페스트는 리포트 문제 2.

**그 외.** 수집된 노드 여섯 대가 AL2 에서 cgroup v1 로 돌아요. `node.cgroup-v1`, 클러스터 단위 한 줄. 커널 로그는 여섯 대 모두 OOM 0, lockup 0, NIC 오류 0. `node.network-errors` 는 삭제된 `ip-10-0-2-149` 는 info 로, 새 노드 `ip-10-0-1-62` 는 low 로 내렸고, `ip-10-0-1-241` 의 24시간 721건은 원본을 열지 않아 medium 그대로예요. 관리형 노드 두 대 `ip-10-0-1-117`, `ip-10-0-2-60` 은 SSM 에 등록돼 있지 않아 OS 상태를 몰라요. `eks.ssm-unregistered` 2개, `node.os-not-collected`.

### Platform
체크 25개 platform·EKS·VPC CNI·kube-proxy, pass 33, fail 11, warn 9. 항목 두 개예요.

**표준 지원이 끝난 Kubernetes 1.32, AL2 노드, 두 버전 뒤처진 Karpenter.** 서버 1.32.13, 표준 지원 종료 2026-03-23 로 217일 지남, 연장 지원 종료 2027-03-23. `platform.k8s-version-eol`, `eks.extended-support`. Karpenter 0.37.0 은 1.30 까지만 지원해요. `platform.karpenter-version-compat`, `logs.signatures karpenter.version-unsupported`. EC2NodeClass `default` 는 `amiFamily: AL2` 에 AMI 고정 없음, 루트 볼륨 50 GB 암호화 안 됨, IMDS 홉 2. `karpenter.ec2nodeclass-al2`, `karpenter.ec2nodeclass-hardening`. 노드 OS 편차: 여섯 대는 AL2 커널 5.10 에 containerd 1.7.29, 두 대는 AL2023 커널 6.1 에 containerd 2.1.5. `eks.node-os-skew`. 애드온 뒤처짐: EBS CSI v1.37.0 대 v1.67.2, VPC CNI v1.19.0 대 v1.23.2 는 fail, CoreDNS v1.11.3 대 v1.11.4, kube-proxy v1.32.0 대 v1.32.13 은 warn. `eks.addon-outdated` 4개. 프리픽스 위임이 꺼져 있고 노드 8대 중 5대가 IP 50% 를 넘었어요. `ip-10-0-1-139` 는 56개 중 43개, ENI 4개가 한도, "no available IP" 이벤트 4건. `vpccni.prefix-delegation-off`, `vpccni.node-ip-exhaustion`.

**접근.** API 엔드포인트가 0.0.0.0/0 에 공개돼 있어요. `eks.public-endpoint-open`. 감사 로그 꺼짐 `eks.controlplane-log-off`, info. `deploy.my-cluster` 의 Argo CD 는 admin 계정 켜짐, SSO 없음, RBAC 정책 비어 있음, 애플리케이션 12개 중 prod 8개 전부가 소스와 목적지가 `*` 인 `default` 프로젝트, server 와 repo-server 레플리카 1개. `argocd.admin-account-no-sso`, `argocd.default-project-wildcard`, `argocd.components-not-ha`. ECR: 저장소 43개 중 39개가 푸시 시 스캔 꺼짐, prod 가 쓰는 25개 포함, 스캔된 이미지 0개, 태그 변경 가능 저장소 42개, 복제 규칙 0. `ecr.scan-disabled` 와 ECR warn 5개.

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
- Skipped or errored 1: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing)

## 7. 부록

### 7-1. 실행한 수집기와 스텝

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 14 | node-os | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'storageclasses.storage.k8s.io']) |
| eks-platform | 28 | kubelet-journal, containerd-journal |  |
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

685 commands, 329.6 s. Failed commands (run.log): 24: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: context deadline exceeded (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.bitnami/kafka` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `ecr.lifecycle-policy.bitnami/mysql` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `eks-platform.kubelet-journal.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.kubelet-journal.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.ecr-app-s-postgresql-pgvector` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `ecr.lifecycle-policy.app-n` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy doe; `eks-platform.containerd-journal.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

### 7-2. 평가한 체크

361 checks: disabled 2, done 356, llm 2, skip 1. Load errors: none.

### 7-3. 서명 일치와 미분류 오류

Signature catalog 1.0.15, ['logs/node/node-1-139/containerd-24h.log', 'logs/node/node-1-139/kubelet-24h.log', 'logs/node/node-1-209/containerd-24h.log', 'logs/node/node-1-209/kubelet-24h.log', 'logs/node/node-1-241/containerd-24h.log', 'logs/node/node-1-62/containerd-24h.log', 'logs/node/node-1-62/kubelet-24h.log', 'logs/node/node-2-218/containerd-24h.log', 'logs/node/node-2-218/kubelet-24h.log', 'logs/pods/actions-runner-controller/arc-system_arc-gha-rs-controller.log', 'logs/pods/alb-controller/kube-system_aws-load-balancer-controller.log', 'logs/pods/argocd/argocd_argocd-application-controller.log', 'logs/pods/argocd/argocd_argocd-applicationset-controller.log', 'logs/pods/argocd/argocd_argocd-notifications-controller.log', 'logs/pods/argocd/argocd_argocd-repo-server.log', 'logs/pods/argocd/argocd_argocd-server.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-controller.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log', 'logs/pods/ebs-csi/kube-system_ebs-csi-node.log', 'logs/pods/external-dns/kube-system_external-dns.log', 'logs/pods/external-secrets/external-secrets_external-secrets-cert-controller.log', 'logs/pods/external-secrets/external-secrets_external-secrets-webhook.log', 'logs/pods/external-secrets/external-secrets_external-secrets.log', 'logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log', 'logs/pods/karpenter/karpenter_karpenter.log', 'logs/pods/keda/keda_keda-operator.log', 'logs/pods/kube-proxy/kube-system_kube-proxy.log', 'logs/pods/loki/monitoring_loki-stack.log', 'logs/pods/metrics-server/kube-system_metrics-server.log', 'logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log', 'logs/pods/promtail/monitoring_loki-stack-promtail.log', 'logs/pods/vpc-cni/kube-system_aws-node.log'] files, 20261 lines scanned (components: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 104.

| Signature | Component | Area | Severity | Status | Count | First ~ last | Sample |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 32 | 2026-10-25T23:32:52 ~ 2026-10-26T07:36:15 | [pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-10-25T23:32:52.159059470Z {"level":"error","ts":1792971172.1589532,"logger":"controllers.ExternalSe |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-10-25T08:43:06 ~ 2026-10-25T08:43:06 | [pod/karpenter-9769889bd-pkxd2/controller] 2026-10-25T08:43:06.238647293Z {"level":"ERROR","time":"2026-10-25T08:43:06.238Z","logger":"controller","message":"fa |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-10-26T03:09:09 ~ 2026-10-26T07:49:42 | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-10-26T03:09:09.344081864Z W1026 03:09:09.343977       1 reflector.go:561] k8s.io/client-go@v0.31. |
| kubelet.image-gc-failed | kubelet | node | medium | warn | 69 | 2026-10-25T07:50:38 ~ 2026-10-25T13:30:38 | 2026-10-25T07:50:38+0000 node-1-139 kubelet[1593]: E1025 07:50:38.131520    1593 kubelet.go:1560] "Image garbage collection f |
| containerd.shim-error | containerd | node | medium | warn | 8 | 2026-10-26T00:30:06 ~ 2026-10-26T03:11:13 | 2026-10-26T03:11:08+0000 node-1-209 containerd[1499]: time="2026-10-26T03:11:08.418072915Z" level=warning msg="cleaning up af |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 5 | 2026-10-25T20:10:56 ~ 2026-10-26T05:18:41 | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-10-25T20:10:56.068688251Z E1025 20:10:56.068156       1 scraper.go:149] "Failed to scrape node" err="G |
| grafana.auth-failed | grafana | security | low | info | 2 | 2026-10-25T08:21:40 ~ 2026-10-26T01:20:58 | [pod/kube-prometheus-stack-grafana-7c9959564d-w8qx7/grafana] 2026-10-25T08:21:40.478388240Z logger=authn.service t=2026-10-25T08:21:40.478273724Z level=warn msg |

| Normalized message | Count | Files |
|---|---|---|
| external-secrets \| {"level":"error","ts":<n>.<n>,"msg":"Reconciler error","controller":"externalsecret","controllerGroup":"external-secrets.io","controllerKind | 32 | logs/pods/external-secrets/external-secrets_external-secrets.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node ip-10-0-1-62.us-east-1.com | 2 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| kube-proxy \| "Kube-proxy configuration may be incomplete or incorrect" err="nodePortAddresses is unset; NodePort connections will be accepted on all loca | 2 | logs/pods/kube-proxy/kube-system_kube-proxy.log |
| node:node-1-139 \| time="<n>-10-25T13:31:51.510000686Z" level=error msg="ContainerStatus for \"b7fbc82af7c25aea74203e378228fd5768be9540d3bbb8c9f430680b50c7713a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:31:55.239263243Z" level=error msg="ContainerStatus for \"a3d91f735fd3c88ce6b715db0d183adae1d8d20c6eb7fcf297fd0d090470a277 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:31:55.257285523Z" level=error msg="ContainerStatus for \"9f6b27f0f2f70c9ab2ddf56ca4338c782de9a4d4ce45030ac174eae9f817c35e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:01.915197223Z" level=error msg="ContainerStatus for \"5b945d1d92be574a092136c7222ee5035f4c6d0388b44d4b1db86a59a283caa2 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:01.940919256Z" level=error msg="ContainerStatus for \"169fd1e191df6a217f0ff06394bb16c062820eb37916e0e2cb84af9f207624d3 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:01.989894957Z" level=error msg="ContainerStatus for \"da111474ad1c61b512d805bcb1c82351d62a1d578d7ed1906731e993ad805aaf | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:02.016483055Z" level=error msg="ContainerStatus for \"dd3bee8f0d3486e999991d291741d10859524cbdf90ba97e5b568799c1f13c27 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:02.127703029Z" level=error msg="ContainerStatus for \"9ba5107686eb6f74d6dd98315ee2abf9ffbdc50aff8e767ddcaf92309b727e3a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:06.983400197Z" level=error msg="ContainerStatus for \"e09948e01beff4df6bc90445b4274c19aa0d7697b7b4f837880d298ef921f9fb | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T13:32:07.515873777Z" level=error msg="ContainerStatus for \"93f7c7106cfc2a9abdaf9b23e633ae194ecc2fe9f9f44bf8f33db160d1f0537e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:07.607525513Z" level=error msg="ContainerStatus for \"b7fbc82af7c25aea74203e378228fd5768be9540d3bbb8c9f430680b50c7713a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:11.206980737Z" level=error msg="ContainerStatus for \"a3d91f735fd3c88ce6b715db0d183adae1d8d20c6eb7fcf297fd0d090470a277 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:11.225385547Z" level=error msg="ContainerStatus for \"9f6b27f0f2f70c9ab2ddf56ca4338c782de9a4d4ce45030ac174eae9f817c35e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:17.512735028Z" level=error msg="ContainerStatus for \"da111474ad1c61b512d805bcb1c82351d62a1d578d7ed1906731e993ad805aaf | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:17.549216301Z" level=error msg="ContainerStatus for \"dd3bee8f0d3486e999991d291741d10859524cbdf90ba97e5b568799c1f13c27 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:17.642765980Z" level=error msg="ContainerStatus for \"9ba5107686eb6f74d6dd98315ee2abf9ffbdc50aff8e767ddcaf92309b727e3a | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:17.720936878Z" level=error msg="ContainerStatus for \"5b945d1d92be574a092136c7222ee5035f4c6d0388b44d4b1db86a59a283caa2 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:17.743946663Z" level=error msg="ContainerStatus for \"169fd1e191df6a217f0ff06394bb16c062820eb37916e0e2cb84af9f207624d3 | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:23.492418241Z" level=error msg="ContainerStatus for \"e09948e01beff4df6bc90445b4274c19aa0d7697b7b4f837880d298ef921f9fb | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| time="<n>-10-25T14:00:24.785712778Z" level=error msg="ContainerStatus for \"93f7c7106cfc2a9abdaf9b23e633ae194ecc2fe9f9f44bf8f33db160d1f0537e | 1 | logs/node/node-1-139/containerd-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"b7fbc82a | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"a3d91f73 | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"9f6b27f0 | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-139 \| "ContainerStatus from runtime service f--output truncated-- | 1 | logs/node/node-1-139/kubelet-24h.log |
| node:node-1-209 \| time="<n>-10-26T00:30:48.670390220Z" level=error msg="failed to load cni during init, please check CRI plugin status before setting up netwo | 1 | logs/node/node-1-209/containerd-24h.log |
| node:node-1-209 \| time="<n>-10-26T00:30:53.292523097Z" level=error msg="failed to load cni during init, please check CRI plugin status before setting up netwo | 1 | logs/node/node-1-209/containerd-24h.log |
| node:node-1-209 \| time="<n>-10-26T00:31:10.553615252Z" level=error msg="get state for b48eb7cd67dead98b4d30c911cce607a5d3b02a1c243480a149a61c8c10d5699" error= | 1 | logs/node/node-1-209/containerd-24h.log |

### 7-4. LLM 이 직접 읽은 원본 파일

inventory.json
findings-draft.json
summary.json
diff.json
events.json
objects/statefulsets.json
objects/pods.json
logs/pods/karpenter/karpenter_karpenter.log
aws/alb-metrics.json
metrics/cpu_throttle_ratio_5m.json
metrics/cpu_p95_7d_cores.json
metrics/cpu_limit_p95_ratio_7d.json
metrics/cpu_request_p95_ratio_7d.json
metrics/namespace_cpu_throttled_ratio_7d.json
metrics/alerts_firing_now.json
metrics/alerts_pending_now.json
metrics/alerts_firing_samples_7d.json
metrics/alerts_fired_15d.json
metrics/alerts_firing_stale_days.json
metrics/node_cpu_request_ratio.json
metrics/node_cpu_usage_ratio_p95_7d.json
metrics/prom_rss_vs_limit.json
metrics/apiserver_5xx_rate.json
metrics/apiserver_p99_latency_by_verb.json
../2026-10-26T16-27-58/report.md
../2026-10-26T16-27-58/report-details.md
../2026-10-26T16-27-58/llm/adjustments.md
../2026-10-26T16-27-58/llm/areas.md
../2026-10-26T16-27-58/llm/changes.md
../2026-10-26T16-27-58/llm/tool-notes.md
../2026-10-26T16-27-58/metrics/cpu_throttle_ratio_5m.json
../2026-10-26T16-18-11/metrics/cpu_throttle_ratio_5m.json
../2026-10-26T14-52-49/metrics/cpu_throttle_ratio_5m.json
../2026-10-26T05-14-43/metrics/cpu_throttle_ratio_5m.json
../2026-10-25T22-57-33/metrics/cpu_throttle_ratio_5m.json

### 7-5. 1차 결과 전체, 모든 fail 과 warn 을 코드 결과 그대로

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `observability.no-slo.cluster` | warn | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] |
| `observability.no-symptom-alerts.cluster` | warn | critical | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 19. Symptom ratio 0.0. Symptom rules: [] |
| `controlplane.scheduler-unschedulable.prod-app-m/app-m-api` | fail | high | 24h 'Unable to schedule pod; no fit' 19 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `controlplane.scheduler-unschedulable.prod-app-m/app-m-backend` | fail | high | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-embedding-server` | fail | high | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `controlplane.scheduler-unschedulable.prod-app-p/app-p-backend` | fail | high | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `eks.no-backup-policy.cluster` | fail | high | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | fail | high | kubelet image GC could not free space. Disk is full of in-use images and logs. 906 occurrences total (1 events, trend over 30 snapshots [417, 422, 439, 450, 454, 524, 533, 574, 585, 594, 611, 617, 624, 628, 630, 658, 668, 673, 681, 686, 692, 731, 760, 767, 857, 881, 883, 900, 902, 906], up), first 2 |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `node.disk-usage.<ip>:9100:/` | fail | high | usage 0.86 |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 204MB |
| `observability.no-event-retention.cluster` | fail | high | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-cfb47f5, end of support 2026-03-23 D+217 (217 days past EOL) |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes up to 1.30, the cluster runs 1.32.  |
| `resilience.prod-concentration.node-1-139` | fail | high | Node node-1-139 (pool default, spot) holds prod pods 28/42 (0.67), 22 workloads: ['prod-app-r/app-r', 'prod-app-q/app-q-ai', 'prod-app-q/app-q-backend', 'prod-app-q/app-q-studio', 'prod-app-q/app-q-web', 'prod-i |
| `resilience.replicas-same-node.prod-app-r/deployment/app-r` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` | fail | high | replicas 3 (Running 3), node distribution {'node-1-139': 3}, AZ distribution {'us-east-1': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-backend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` | fail | high | replicas 2 (Running 2), node distribution {'node-1-139': 2}, AZ distribution {'us-east-1': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 2 |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: 5m throttling ratio 0.28 (stalled for 28% of periods) |
| `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql` | fail | high | pod app-p-postgresql-0: 5m throttling ratio 0.42 (stalled for 42% of periods) |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | fail | high | ['pod loki-stack-promtail-dc9mw: 7d memory working set p95 / limit = 0.90', 'pod loki-stack-promtail-hxxt7: 7d memory working set p95 / limit = 0.81'] |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | fail | high | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (1.3 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | fail | high | 3 NetworkPolicies (['prod-app-q', 'prod-app-p', 'app-s-prod']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.privileged-or-host-access.prod-app-l-backend/deployment/tts-proxy` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0` | fail | high | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-t-mysql'], StorageClass gp3 |
| `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-133751726c (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 2.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend` | fail | high | Target group k8s-app-svc-b347218b4f (application, port 8000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-t-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` | fail | high | Target group k8s-app-svc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-q-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` | fail | high | Target group k8s-app-svc-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-o-frontend'] |
| `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` | fail | high | Target group k8s-app-svc-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0, health check / expected codes 200, backends ['deployment/app-l-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` | fail | high | Target group k8s-app-svc-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-n-frontend'] |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | fail | high | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['k8s-app-svc-31ecf1515b-96449818f244837f.elb.us-east-1.amazonaws.com'], sourceRanges None. DB port open on an external address |
| `traffic.db-exposed.nlb/acme-db-shared` | fail | high | nlb (defined outside the cluster) /acme-db-shared: ports [3306, 5432, 6379, 7687], exposure internet-facing, addresses ['acme-db-shared-d7d643f6896a3b2b.elb.us-east-1.amazonaws.com'], sourceRanges None. no TargetGroupBinding; NLB created outside Kubernetes (Terraform etc.). DB inferred from t |
| `vpccni.node-ip-exhaustion.node-1-139` | fail | high | node node-1-139 (r8gd.xlarge, pool default): pod IPs 43/56 (0.768), ENI 4/4 (at limit True), 'no available IP' events 4, max-pods 58, prod pods 28. prefix delegation False |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `controlplane.scheduler-unschedulable.arc-runners/self-hosted-arm64-8msc5-runner` | warn | high | 24h 'Unable to schedule pod; no fit' 2 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `controlplane.scheduler-unschedulable.dev-app-n/app-n-frontend` | warn | high | 24h 'Unable to schedule pod; no fit' 23 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> Insufficient cpu, <n> node(s) had untolerated taint {node.kubernetes.io/not-ready: }, <n> node(s) had untol |
| `eks.service-quota-near-limit.aws-account` | warn | high | quotas with a usage metric 25/65, at 80% or more [], at 60% or more ['VPCs 0.6'], top operational quotas [['VPCs', 3.0, 5.0, 0.6], ['listener rules per ALB', 47.0, 100.0, 0.47], ['target groups per ALB', 40.0, 100.0, 0.4], ['certificates per ALB', 9.0, 25.0, 0.36], ['NLBs', 2.0, 50.0, 0.04], ['ALBs' |
| `events.tracked-warning-reasons.UpdateFailed` | warn | high | Operator reconcile failure (ExternalSecret etc.). 1639 occurrences total (1 events, trend over 30 snapshots [1483, 1486, 1492, 1495, 1496, 1517, 1521, 1535, 1538, 1541, 1546, 1548, 1550, 1551, 1552, 1561, 1564, 1565, 1569, 1570, 1572, 1584, 1593, 1596, 1624, 1632, 1632, 1637, 1638, 1639], up), first |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 32 occurrences (2026-10-25T23:32:52 ~ 2026-10-26T07:36:15), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: ['[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-10-25T23:32:52.159059470Z {"level":"error","ts":1792971172.15895 |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-10-25T08:43:06 ~ 2026-10-25T08:43:06), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-10-25T08:43:06.238647293Z {"level":"ERROR","time":"2026-10-25T08:43:06.238Z","logger":"controller", |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.775 (limit 1536Mi), active series 161206, Prometheus container last terminated OOMKilled True (2026-10-06T12:32:06Z), restarts 1, OOMKilled containers in the monitoring namespace ['loki-stack-0/loki', 'prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7  |
| `resilience.n-plus-one.cluster` | warn | high | Allocatable without the largest node node-1-139 (3.92 cores, 29.8GB): CPU 15.5 cores vs total requests 12.41 (OK), memory 46.0GB vs 47.5GB (short). Pods on that node 41 (prod 28). Pods that fit on no other node []. Node autoscaler present (delay until a new node) |
| `resources.cpu-throttling.dev-app-m/deploy/app-m-frontend:frontend` | warn | high | pod app-m-frontend-77bb87b557-87hjx: 5m throttling ratio 0.18 (stalled for 18% of periods) |
| `resources.cpu-throttling.dev-app-o/deploy/app-o-frontend:frontend` | warn | high | pod app-o-frontend-7f6d6dc65b-lnmq4: 5m throttling ratio 0.16 (stalled for 16% of periods) |
| `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend` | warn | high | ['pod app-m-frontend-6d7ff4dcdb-tzwjn: 5m throttling ratio 0.24 (stalled for 24% of periods)', 'pod app-m-frontend-6d7ff4dcdb-qfmxq: 5m throttling ratio 0.23 (stalled for 23% of periods)'] |
| `resources.oomkilled-repeated.monitoring/sts/loki-stack:loki` | warn | high | pod loki-stack-0 container loki: 1 OOMs in 7 days (increase of cAdvisor container_oom_events_total) |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-10-06T12:32:06Z (19.8 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.imds-hop-limit.cluster` | warn | high | Of 8 instances, 8 with IMDS hop limit > 1 or tokens optional: {'hop=2 tokens=required': 8}. Examples [('system_core', 'm5.large', 2, 'required'), ('system_core', 'm5.large', 2, 'required'), ('karpenter-node', 't8i.medium', 2, 'required'), ('karpenter-node', 'm7i-flex.large', 2, 'required')]. EC2Node |
| `vpccni.node-ip-exhaustion.node-1-241` | warn | high | node node-1-241 (t8i.small, pool system-ondemand): pod IPs 6/9 (0.667), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 11, prod pods 1. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-2-218` | warn | high | node node-2-218 (t8i.medium, pool system-ondemand): pod IPs 13/15 (0.867), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 17, prod pods 1. prefix delegation False |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 12/12 (prod 8) |
| `cost.idle-compute-high.cluster` | fail | medium | Node compute monthly estimate 459.18 USD (on-demand list price, current spot price), of which idle 436.62 USD (0.95), by pool {'nodegroup:system_core-20251217040546303900000001': 172.28, 'default': 93.29, 'build-arm64': 39.35, 'system-ondemand': 154.26}, 23.64 USD per core-month. Spot node share 0.3 |
| `cost.request-waste.cluster` | fail | medium | CPU request total 6.68 cores -> KRR recommendation 1.45 cores, reducible 5.23 cores ~ 123.66 USD/month |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-2a', 'gp3-2c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-2a', 'gp3-2c'] |
| `ecr.scan-disabled.ecr/registry/<account>` | fail | medium | registry scanning BASIC (rules 0), repositories with scanOnPush off 39/43 (used by prod 25: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod']…), scanned images 0 |
| `eks.addon-outdated.aws-ebs-csi-driver` | fail | medium | installed v1.37.0-eksbuild.1, latest available v1.67.2-eksbuild.1, default v1.67.2-eksbuild.1 |
| `eks.addon-outdated.vpc-cni` | fail | medium | installed v1.19.0-eksbuild.1, latest available v1.23.2-eksbuild.8, default v1.22.4-eksbuild.8 |
| `eks.extended-support.cluster` | fail | medium | version 1.32, supportType EXTENDED, status EXTENDED_SUPPORT, end of standard support 2026-03-23T09:00:00+09:00, end of extended support 2027-03-23T09:00:00+09:00 |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eks.nodegroup-ami-old.nodegroups` | fail | medium | node groups 1, max AMI age 321 days, over 90 days ['system_core-20251217040546303900000001 321d'], over 180 days ['system_core-20251217040546303900000001'], health issues [] |
| `eks.ssm-unregistered.node-1-117` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eks.ssm-unregistered.node-2-60` | fail | medium | instance i-0123456789abcdef0 is missing from ssm describe-instance-information or not Online |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 18955 / errors 1639 (ratio 0.0796), sync failures 1639/43322, reconcile errors 1639, ExternalSecrets not Ready ['database/externalsecret/mysql-app-n-secret'] (oldest refresh 7514.8 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2515, {'101': 4, '200': 2203, '400': 6, '429': 302}), ('Prometheus(prometheus)', 1524, {'200': 1349, '301': 175}), ('VictoriaMetrics_onprem(prometheus)', 131, {'200': 131})], error rate 1% or more ['Loki(loki)'] (max 0.1201), Grafana  |
| `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility` | fail | medium | Amazon Linux 2 compatibility (UPGRADE_READINESS, k8s 1.33): ERROR — Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ |
| `hygiene.mutable-image-tag.prod-app-l-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.polaris-reliability-danger.prod-app-l-backend/deployment/tts-proxy` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing']. Security-category danger ['dangerousCapabilities', 'privilegeEscalationAllowed', 'run |
| `node.network-errors.<ip>:9100:eth0` | fail | medium | Node <ip>:9100 device eth0: 4857 RX+TX errors in 24h |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 47.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubePodNotReady/dev-app-o` | fail | medium | Firing for 17.4 days (ALERTS_FOR_STATE). Labels {'namespace': 'dev-app-o', 'pod': 'app-o-ai-7cdbdc7544-f94b5', 'severity': 'warning'} |
| `observability.alert-firing-stale.KubePodNotReady/app-s-prod` | fail | medium | Firing for 7.7 days (ALERTS_FOR_STATE). Labels {'namespace': 'app-s-prod', 'pod': 'app-s-frontend-6bcb5c9597-656ft', 'severity': 'warning'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 47.8 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodNotReady` | fail | medium | 7d firing samples 133999 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 139 pods Running for over 1h, 57 are absent from Loki pod labels (ratio 0.41). Nodes with every pod missing: ['node-1-209']. By namespace: {'kube-system': 19, 'monitoring': 13, 'prod-app-l-backend': 4, 'argocd': 2, 'dev-app-m': 2, 'dev-app-o': 2, 'keda |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-n-secret` | fail | medium | Ready=False (SecretSyncedError) for 7513.9 hours: could not get secret data from provider |
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
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend` | fail | medium | pod app-l-backend-5c5c54d5dd-rkqr9: 7d CPU p95 0.002 cores / request 0.50 cores = 0.00 |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | pod app-l-embedding-server-577b67cff8-2x6zb: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00 |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | medium | pod app-l-neo4j-0: 7d CPU p95 0.004 cores / request 0.50 cores = 0.01 |
| `resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter` | fail | medium | middleware/statefulset/kafka-controller container jmx-exporter (jmx-exporter:0.20.0-debian-11-r4): -Xmx NoneMiB, MaxRAMPercentage 100.0, memory limit 128.0MiB -> heap/limit 1.0 (heap unset False) |
| `resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller` | fail | medium | memory request under by 257 MB, CPU request over by 0.146 cores: CPU request 0.2 → 0.054 cores, CPU limit 0.5 → none, memory request 384 → 641 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.dev-app-o/statefulset/app-o-backend-mysql:mysql` | fail | medium | memory request under by 354 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 866 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.dev-app-n/statefulset/app-n-backend-dev-mysql:mysql` | fail | medium | memory request under by 268 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 780 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/loki-stack:loki` | fail | medium | memory request under by 273 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.2 → none, memory request 256 → 529 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 839 MB: CPU request 0.2 → 0.128 cores, CPU limit 0.5 → none, memory request 800 → 1639 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle` | fail | medium | CPU request over by 0.29 cores, memory request over by 338 MB: CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 174 MB, memory limit 1024 → 174 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-backend:backend` | fail | medium | memory request under by 298 MB: CPU request 0.03 → 0.07 cores, CPU limit 0.5 → none, memory request 128 → 426 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/deployment/app-m-frontend:frontend` | fail | medium | memory request under by 303 MB: CPU request 0.01 → 0.032 cores, CPU limit 0.2 → none, memory request 128 → 431 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-m/statefulset/app-m-backend-mysql:mysql` | fail | medium | memory request under by 386 MB, CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 1154 MB, memory limit 1536 → 1154 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-ai:ai` | fail | medium | memory request over by 528 MB: CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 1520 MB, memory limit 4096 → 1520 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-embedding-server:embedding` | fail | medium | CPU request over by 0.341 cores: CPU request 0.5 → 0.159 cores, CPU limit 2.0 → none, memory request 4096 → 3932 MB, memory limit 6144 → 3932 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/statefulset/app-l-neo4j:neo4j` | fail | medium | CPU request over by 0.49 cores, memory request over by 3215 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 881 MB, memory limit 5120 → 881 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-backend:backend` | fail | medium | CPU request over by 0.359 cores: CPU request 0.5 → 0.141 cores, CPU limit 2.0 → none, memory request 1024 → 783 MB, memory limit 2048 → 783 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.large-request-binpacking.arc-runners/ephemeralrunner/self-hosted-arm64-8msc5-runner-ljqpw:runner` | fail | medium | pod self-hosted-arm64-8msc5-runner-ljqpw: request is 104% of the median node allocatable |
| `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | fail | medium | ['pod app-l-embedding-server-577b67cff8-2x6zb: request is 58% of the median node allocatable', 'pod app-l-embedding-server-d65755ff4-lh57d: request is 58% of the median node allocatable', 'pod app-l-embedding-server-577b67cff8-sb7dx: request is 58% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | medium | pod app-l-neo4j-0: request is 58% of the median node allocatable |
| `resources.no-memory-limit.prod-app-l-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-request-usage-gap.node-1-117` | fail | medium | CPU requests/allocatable 0.96, usage/allocatable 7d p95 0.09 (5m instant 0.09) |
| `resources.node-request-usage-gap.node-1-139` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.05) |
| `resources.node-request-usage-gap.node-2-60` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.06) |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node node-1-139 (r8gd.xlarge spot): age 774.9h, 54.9h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 14171}. do-not-disrupt pods on this node 1: prod-app-m/app-m-admin-57f5fcc58d-khsh5 |
| `security.externalsecret-not-ready.database/mysql-app-n-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.networkpolicy-coverage.cluster` | fail | medium | 18 of 21 user namespaces have no NetworkPolicy, of which production ['prod-app-r', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-n']; with: ['prod-app-q', 'prod-app-p', 'app-s-prod'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 79. Security danger workloads 74 (prod 28): per check {'dangerousCapabilities': 2, 'hostNetworkSet': 2, 'privilegeEscalationAllowed': 59, 'runAsPrivileged': 3, 'runAsRootAllowed': 58, 'hostPIDSet': 1, 'rolebindingClusterAdminRole': 2, 'rolebindingRolePodExecAttach': 2, 'clusterrolebind |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days 12 {'pre-delete backup of orphan PVC prod-ill': 4, 'pre-delete backup of orphan PVC app-s-prod': 2, 'pre-delete backup of orphan PVC prod-ins': 2, 'pre-delete backup of orphan PVC dev-toot': 1, |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.burst-tenant-unbounded.prod-app-l-backend` | fail | medium | prod-app-l-backend (prod): 7d CPU median 0.012 cores, p95 0.013 cores, max 2.627 cores = 226.3x the median. No quota, shares nodes with prod True, nodes {'node-1-139': 5, 'node-2-135': 3, 'ip-10-0-1-62.us-east-1.compute.inter |
| `tenancy.prod-boundary-missing.prod-app-r` | fail | medium | prod-app-r: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-m` | fail | medium | prod-app-m: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-o` | fail | medium | prod-app-o: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-l-backend` | fail | medium | prod-app-l-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-n` | fail | medium | prod-app-n: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `traffic.shared-alb-group.alb-group/acme-prod-lb` | fail | medium | ALB group acme-prod-lb: 40 ingresses, 47 hosts, 15 namespaces ['argocd', 'dev-app-m', 'dev-app-o', 'dev-app-n', 'dev-app-t', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n |
| `vpccni.prefix-delegation-off.cluster` | fail | medium | ENABLE_PREFIX_DELEGATION false, nitro nodes 8/8. nodes above 50% IP usage ['node-2-218', 'node-1-139', 'node-1-241', 'node-2-60', 'ip-10-0-1-117.us-east-1. |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 123, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `albctl.tgb-stale-or-orphan.cluster` | warn | medium | TargetGroupBindings 51 (targetType {'ip': 51}), generation lagging [], Service missing [], hand-made TGBs 9, target groups without a binding (traffic section) 1 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.my-cluster |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version 2.13 |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.618s |
| `controlplane.controller-error-repeat.horizontal.go` | warn | medium | 24h E lines 26 times (horizontal.go). Samples: summary.controlplane.controller_manager.top_errors |
| `controlplane.controller-error-repeat.type.go` | warn | medium | 24h W lines 80478 times (type.go). Samples: summary.controlplane.controller_manager.top_errors |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.503, queries per second 60.49, NXDOMAIN share of queries forwarded upstream 0.435 (upstreams ['<ip>:53']), pods with default ndots (5) 157, autopath False, cache hit ratio 0.8948 |
| `ecr.dockerhub-dependency.ecr/registry/<account>` | warn | medium | registry distribution of container images {'<account>.dkr.ecr.us-east-1.amazonaws.com': 70, '<account>.dkr.ecr.us-east-1.amazonaws.com': 67, 'docker.io': 33, 'quay.io': 24, 'ghcr.io': 11, 'public.ecr.aws': 8, 'registry.k8s.io': 3}, docker.io images 20 (e.g. ['alpine/socat:1.8.0.0', ' |
| `eks.addon-outdated.coredns` | warn | medium | installed v1.11.3-eksbuild.1, latest available v1.11.4-eksbuild.92, default v1.11.4-eksbuild.88 |
| `eks.addon-outdated.kube-proxy` | warn | medium | installed v1.32.0-eksbuild.2, latest available v1.32.13-eksbuild.65, default v1.32.13-eksbuild.62 |
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
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 32.7s (7438 pods), node termination average 17.3s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-o/scaledobject/app-o-ai-kafka-lag', 'prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.containerd.shim-error` | warn | medium | 8 occurrences (2026-10-26T00:30:06 ~ 2026-10-26T03:11:13), thresholds warn 5/fail 50. Files: ['logs/node/node-1-209/containerd-24h.log', 'logs/node/node-1-241/containerd-24h.log', 'logs/node/ip-10-0-2-218.us-east-1.compute.in |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-10-26T03:09:09 ~ 2026-10-26T07:49:42), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-10-26T03:09:09.344081864Z W1026 03:09:09.343977       1 reflector.go:56 |
| `logs.signatures.kubelet.image-gc-failed` | warn | medium | 69 occurrences (2026-10-25T07:50:38 ~ 2026-10-25T13:30:38), thresholds warn 1/fail 10. Files: ['logs/node/node-1-139/kubelet-24h.log']. Samples: ['2026-10-25T07:50:38+0000 node-1-139 kubelet[1593]: E1025 07:50:38.131520    1593 ku |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 5 occurrences (2026-10-25T20:10:56 ~ 2026-10-26T05:18:41), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-10-25T20:10:56.068688251Z E1025 20:10:56.068156       1 scraper.go:149] "Fai |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | warn | medium | RSS 204MiB / limit 512Mi = 0.399, in-memory streams 60, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `node.kernel-net-mem-pressure.node-2-135` | warn | medium | kernel log (since boot (dmesg; journald does not hold 24 hours)) BUG/Oops/Call Trace 0, network pressure (TCP memory, SYN flooding, ARP table) 1, memory pressure (page allocation failure) 0, unstable clocksource 0. Samples: ['[Sat Oct 10 05:24:47 2026] TCP: request_sock_TCP: Possible SYN flooding on |
| `node.network-errors.<ip>:9100:eth0` | warn | medium | Node <ip>:9100 device eth0: 721 RX+TX errors in 24h |
| `node.network-errors.<ip>:9100:eth0` | warn | medium | Node <ip>:9100 device eth0: 147 RX+TX errors in 24h |
| `observability.alert-firing-stale.KubePodNotReady/prod-app-r` | warn | medium | ["Firing for 3.9 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-r', 'pod': 'app-r-dd59d5f64-65mrp', 'severity': 'warning'}", "Firing for 3.9 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-r', 'pod': 'app-r-dd59d5f64-mtlw6', 'severity': 'warning'}"] |
| `observability.alert-firing-stale.KubePodNotReady/prod-app-l-backend` | warn | medium | ["Firing for 3.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-backend-644dd89db4-89nvh', 'severity': 'warning'}", "Firing for 3.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-backend-644dd89db4-crtqs', 'severity': 'warning'}", "Firing for 3.3 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-backend-665c59696d-d5mlr', 'severity': 'warning'}", "Firing for 4.0 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-backend-b777fdcd9-297gb', 'severity': 'warning'}", "Firing for 3.2 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-backend-d64f85856-768hq', 'severity': 'warning'}", "Firing for 3.3 days (ALERTS_FOR_STATE). Labels {'namespace': 'prod-app-l-backend', 'pod': 'app-l-embedding-server-d65755ff4-lh57d', 'severity': 'warning'}"] |
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
| `resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller` | warn | medium | pod argocd-application-controller-0: 7d CPU p95 0.032 cores / request 0.20 cores = 0.16 |
| `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-api:api` | warn | medium | pod app-m-api-575d497d9b-5ttcv: 7d CPU p95 0.012 cores / request 0.10 cores = 0.12 |
| `resources.cpu-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` | warn | medium | pod app-m-backend-695864bdf6-qwhn7: 7d CPU p95 0.017 cores / request 0.10 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10 |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | medium | pod app-o-ai-7cdbdc7544-szzcl: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | medium | pod app-o-backend-69dbdf4f65-9x6jc: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.10 cores = 0.09 |
| `resources.cpu-request-overprovisioned.dev-app-n/deploy/app-n-backend:backend` | warn | medium | pod app-n-backend-7cfd8c975-b9p48: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13 |
| `resources.cpu-request-overprovisioned.dev-app-n/sts/app-n-backend-dev-mysql:mysql` | warn | medium | pod app-n-backend-dev-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10 |
| `resources.cpu-request-overprovisioned.dev-app-t/deploy/app-t-backend:backend` | warn | medium | pod app-t-backend-5ff4994f96-fxsr6: 7d CPU p95 0.001 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-mysql:mysql` | warn | medium | pod app-t-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04 |
| `resources.cpu-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | medium | pod app-t-postgres-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07 |
| `resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | medium | ['pod karpenter-9769889bd-pkxd2: 7d CPU p95 0.014 cores / request 0.20 cores = 0.07', 'pod karpenter-9769889bd-nphgs: 7d CPU p95 0.000 cores / request 0.20 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-7fc99cdd4d-jpng8: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-c5b6f8b88-jt7dp: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-54ffcbbfd6-2wtvl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/aws-load-balancer-controller:aws-load-balancer-controller` | warn | medium | ['pod aws-load-balancer-controller-dbcd6944f-svnmr: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02', 'pod aws-load-balancer-controller-dbcd6944f-psh2b: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | ['pod coredns-c7dbf4744-lz5fs: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06', 'pod coredns-c7dbf4744-cb76h: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-65d4b7df64-xxfjs: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05 |
| `resources.cpu-request-overprovisioned.kube-system/ds/kube-proxy:kube-proxy` | warn | medium | ['pod kube-proxy-snbf9: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-d297j: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-77wxc: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-4zj2m: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-n4sbq: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-t9t6c: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.middleware/deploy/kafka-ui:kafka-ui` | warn | medium | pod kafka-ui-7cb8bcb988-gls7p: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.middleware/sts/kafka-controller:kafka` | warn | medium | pod kafka-controller-0: 7d CPU p95 0.066 cores / request 0.20 cores = 0.33 |
| `resources.cpu-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana` | warn | medium | pod kube-prometheus-stack-grafana-7c9959564d-w8qx7: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.monitoring/sts/loki-stack:loki` | warn | medium | pod loki-stack-0: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06 |
| `resources.cpu-request-overprovisioned.prod-app-q/deploy/app-q-ai:ai` | warn | medium | pod app-q-ai-5ddf98b664-fmzq8: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | medium | pod app-q-backend-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05 |
| `resources.cpu-request-overprovisioned.prod-app-m/sts/app-m-backend-mysql:mysql` | warn | medium | pod app-m-backend-mysql-0: 7d CPU p95 0.012 cores / request 0.20 cores = 0.06 |
| `resources.cpu-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | medium | ['pod app-o-backend-596479b6f8-nv9j2: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod app-o-backend-596479b6f8-cx44t: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.prod-app-o/sts/app-o-backend-mysql:mysql` | warn | medium | pod app-o-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04 |
| `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | medium | ['pod app-l-frontend-6d58bbfcfc-nfk9x: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod app-l-frontend-6d58bbfcfc-2qgs6: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.prod-app-p/sts/app-p-postgresql:postgresql` | warn | medium | pod app-p-postgresql-0: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04 |
| `resources.cpu-request-overprovisioned.prod-app-n/sts/app-n-backend-prod-mysql:mysql` | warn | medium | pod app-n-backend-prod-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05 |
| `resources.cpu-request-overprovisioned.app-s-prod/deploy/app-s-backend:backend` | warn | medium | ['pod app-s-backend-fcdc97cc9-zwt5n: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13', 'pod app-s-backend-fcdc97cc9-dpc8t: 7d CPU p95 0.012 cores / request 0.10 cores = 0.12'] |
| `resources.cpu-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | medium | pod app-s-backend-postgresql-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07 |
| `resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server` | warn | medium | CPU request over by 0.19 cores, memory request over by 272 MB: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 240 MB, memory limit 1024 → 240 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-m/deployment/app-m-frontend:frontend` | warn | medium | memory request under by 111 MB: CPU HPA detected, memory request 128 → 239 MB. KRR severity OK (CPU req UNKNOWN, CPU limit UNKNOWN, memory req OK, memory limit GOOD). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-m/statefulset/app-m-backend-mysql:mysql` | warn | medium | memory request under by 113 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 625 MB, memory limit 1024 → 625 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-ai:ai` | warn | medium | memory request over by 458 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 566 MB, memory limit 2048 → 566 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 340 MB: CPU HPA detected, memory request 512 → 172 MB, memory limit 8192 → 172 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.dev-app-t/statefulset/app-t-mysql:mysql` | warn | medium | CPU request over by 0.19 cores, memory request over by 341 MB: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.karpenter/deployment/karpenter:controller` | warn | medium | memory request under by 163 MB, CPU request over by 0.182 cores: CPU request 0.2 → 0.018 cores, CPU limit 0.5 → none, memory request 256 → 419 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka` | warn | medium | CPU request over by 0.135 cores: CPU request 0.2 → 0.065 cores, CPU limit 0.5 → none, memory request 1536 → 1513 MB, memory limit 2048 → 1513 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail` | warn | medium | memory request under by 157 MB: CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 285 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-backend:backend` | warn | medium | memory request under by 162 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 354 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-q/deployment/app-q-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-o/deployment/app-o-backend:backend` | warn | medium | memory request over by 355 MB: CPU request 0.1 → 0.089 cores, CPU limit 2.0 → none, memory request 512 → 157 MB, memory limit 2048 → 157 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-o/statefulset/app-o-backend-mysql:mysql` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 737 MB, memory limit 1536 → 737 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-backend:backend` | warn | medium | memory request over by 443 MB: CPU HPA detected, memory request 1024 → 581 MB, memory limit 2048 → 581 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.prod-app-l-backend/deployment/app-l-pg-proxy:forwarder` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-p/deployment/app-p-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-n/deployment/app-n-backend:backend` | warn | medium | memory request under by 78 MB: CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 206 MB, memory limit 512 → 206 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-n/statefulset/app-n-backend-prod-mysql:mysql` | warn | medium | CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 811 MB, memory limit 1536 → 811 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.node-memory-request-usage-gap.node-1-139` | warn | medium | memory requests/allocatable 0.68, working set/allocatable 7d p95 0.26 (instant 0.26) |
| `resources.node-memory-request-usage-gap.node-1-209` | warn | medium | memory requests/allocatable 0.70, working set/allocatable 7d p95 0.03 (instant 0.03) |
| `resources.node-memory-request-usage-gap.node-1-241` | warn | medium | memory requests/allocatable 0.66, working set/allocatable 7d p95 0.27 (instant 0.30) |
| `resources.node-memory-request-usage-gap.node-2-135` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.38 (instant 0.38) |
| `resources.node-request-usage-gap.node-1-62` | warn | medium | CPU requests/allocatable 0.71, usage/allocatable 7d p95 0.03 (5m instant 0.04) |
| `resources.node-request-usage-gap.node-2-135` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.05 (5m instant 0.04) |
| `scaling.hpa-flapping.dev-app-m/hpa/app-m-frontend` | warn | medium | 31 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']. Share of containers allowing root 0.62 (28 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 86/91, of which 29 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-r/deployment/app-r', 'prod-app-q/deployment/app-q-ai', 'prod-app-q/deployment/app-q-backend', 'prod-app-q/deployment/app-q-s |
| `storage.ebs-unencrypted.cluster` | warn | medium | 17 of 17 volumes unencrypted: ['vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0', 'vol-0123456789abcdef0'] |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-n/data-app-n-backend-prod-mysql-0', 'prod-app-m/data-app-m-backend-mysql-0', 'prod-app-l-backend/data-app-l-neo4j-0', 'app-s-prod/data-app-s-backend-postgresql-0', 'prod-app-q/data-app-q-backend-postgresql-0', 'prod |
| `tenancy.prod-boundary-missing.prod-app-q` | warn | medium | prod-app-q: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-p` | warn | medium | prod-app-p: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.app-s-prod` | warn | medium | app-s-prod: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 1, CPU requests total 2.0 cores, memory requests total 4.0GB, 7d CPU p95 0.125 cores (cluster share 0.146), memory p95 0.73GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-m` | warn | medium | dev-app-m (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 0.052 cores (cluster share 0.06), memory p95 0.97GB, 7d max/median 1.5x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-o` | warn | medium | dev-app-o (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 2.25GB, 7d CPU p95 0.035 cores (cluster share 0.041), memory p95 1.54GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-n` | warn | medium | dev-app-n (dev): no ResourceQuota. Pods 4, CPU requests total 0.3 cores, memory requests total 1.0GB, 7d CPU p95 0.024 cores (cluster share 0.028), memory p95 0.93GB, 7d max/median 1.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-t` | warn | medium | dev-app-t (dev): no ResourceQuota. Pods 4, CPU requests total 0.55 cores, memory requests total 1.88GB, 7d CPU p95 0.017 cores (cluster share 0.02), memory p95 0.86GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-r` | warn | medium | prod-app-r (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 0.004 cores (cluster share 0.005), memory p95 0.22GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-q` | warn | medium | prod-app-q (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 0.008 cores (cluster share 0.01), memory p95 0.5GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-m` | warn | medium | prod-app-m (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 0.117 cores (cluster share 0.136), memory p95 1.9GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-o` | warn | medium | prod-app-o (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 0.038 cores (cluster share 0.044), memory p95 3.15GB, 7d max/median 2.0x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-l-backend` | warn | medium | prod-app-l-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 0.013 cores (cluster share 0.015), memory p95 7.37GB, 7d max/median 226.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-p` | warn | medium | prod-app-p (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.006 cores (cluster share 0.007), memory p95 0.49GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-n` | warn | medium | prod-app-n (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.025 cores (cluster share 0.029), memory p95 1.01GB, 7d max/median 2.3x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.app-s-prod` | warn | medium | app-s-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 0.02 cores (cluster share 0.023), memory p95 0.49GB, 7d max/median 1.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.node-1-117` | warn | medium | Node node-1-117 (pool system_core-20251217040546303900000001): tenant kinds ['dev', 'prod'], namespaces ['kube-system', 'keda', 'monitoring', 'argocd', 'dev-app-o', 'dev-app-t']. Memory limit total 11.6GB / allocatable 6.9GB = 1.68x, request total 4.7GB,  |
| `tenancy.shared-node-limit-overcommit.node-1-139` | warn | medium | Node node-1-139 (pool default): tenant kinds ['dev', 'prod'], namespaces ['prod-app-o', 'prod-app-l-backend', 'dev-app-m', 'dev-app-o', 'prod-app-q', 'prod-app-m']. Memory limit total 49.4GB / allocatable 29.8GB = 1.66x, request total 19.8G |
| `tenancy.shared-node-limit-overcommit.node-2-218` | warn | medium | Node node-2-218 (pool system-ondemand): tenant kinds ['dev', 'other', 'prod'], namespaces ['monitoring', 'arc-system', 'argocd', 'dev-app-t', 'keda', 'kube-system']. Memory limit total 5.0GB / allocatable 3.2GB = 1.55x, request total 1.7GB, containers without |
| `tenancy.tenant-without-limitrange.arc-runners` | warn | medium | arc-runners (ci): no LimitRange, containers without requests 1 / without a memory limit 1 (pods 1). 7d CPU p95 0.125 cores, memory p95 0.73GB |
| `tenancy.tenant-without-limitrange.prod-app-l-backend` | warn | medium | prod-app-l-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 0.013 cores, memory p95 7.37GB |
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
| `traffic.alb-elb-5xx.k8s-acmeprodlb-b18a4555d7` | warn | medium | ALB k8s-acmeprodlb-b18a4555d7 (internet-facing): 24h requests 215433.0, ELB 5xx 32.0, target 5xx 732.0, rejected connections 0, idle timeout 300s, target groups 40 |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.my-cluster']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-m/app-m-admin` | warn | medium | ingress ['admin-dev.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-o/app-o-admin` | warn | medium | ingress ['admin-dev.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin-dev.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-m/app-m-admin` | warn | medium | ingress ['canary-admin.example-b.ai', 'admin.example-b.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-o/app-o-admin` | warn | medium | ingress ['admin.example-d.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-n/app-n-admin-frontend` | warn | medium | ingress ['admin.example-c.ai']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend` | warn | medium | ['canary-api.example-b.ai', 'api.example-b.ai']: 24h 5xx 723.0 of 120706.0 requests = 0.60% (source alb-cloudwatch), p95 max 5.5671s |
| `traffic.ingress-5xx-ratio.prod-app-n/app-n-admin-frontend` | warn | medium | ['admin.example-c.ai']: 24h 5xx 2.0 of 312.0 requests = 0.64% (source alb-cloudwatch), p95 max 0.9962s |
| `hygiene.failed-pods-lingering.cluster` | fail | low | Failed pods 12 (prod 11), reasons {'Evicted': 12}, namespaces {'prod-app-l-backend': 7, 'prod-app-r': 2, 'app-s-prod': 2, 'dev-app-o': 1}, oldest 774.9h. Example: ['prod-app-r/app-r-dd59d5f64-mtlw6', 'dev-app-o/app-o-ai-7cdbdc7544-f94b5', 'prod-app-r/carpenstree |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 111 (0.009), without one in prod 33. emptyDirs without sizeLimit 21 (prod: ['prod-app-q/statefulset/app-q-backend-postgresql', 'prod-app-l-backend/deployment/app-l-embedding-server', 'prod-app-l-backend/deployment/tts-proxy', 'prod-app-p/d |
| `hygiene.old-replicasets.cluster` | fail | low | Of 417 ReplicaSets, 352 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 61, '3': 6} |
| `node.cgroup-v1.node-1-139` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-209` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-241` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-1-62` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-135` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-2-218` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.os-not-collected.node-1-117` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `node.os-not-collected.node-2-60` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `resources.memory-request-overprovisioned.prod-app-l-backend/sts/app-l-neo4j:neo4j` | fail | low | pod app-l-neo4j-0: 7d memory working set p95 765 MB / request 4096 MB = 0.19 |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-backend` | fail | low | HPA prod-app-l-backend/app-l-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 9.8 days ago |
| `scaling.hpa-never-scaled.prod-app-l-backend/deployment/app-l-frontend` | fail | low | HPA prod-app-l-backend/app-l-frontend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 1% / target 70%, metrics ['cpu'], last scale 77.1 days ago |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `tenancy.dev-shares-prod-nodes.node-1-117` | fail | low | Node node-1-117 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-o', 'app-s-prod']) together with dev pods 2 (['dev-app-o', 'dev-app-t']). Memory limit total/allocatable 1.68, CPU limit total/allocatable 3.37, containers without a  |
| `tenancy.dev-shares-prod-nodes.node-1-139` | fail | low | Node node-1-139 (pool default): prod pods 28 (['prod-app-r', 'prod-app-q', 'prod-app-m', 'prod-app-o', 'prod-app-l-backend', 'prod-app-p', 'prod-app-n', 'app-s-prod']) together with dev pods 12 (['dev-app-m', 'dev-app-o', 'dev-tooto |
| `tenancy.dev-shares-prod-nodes.node-2-218` | fail | low | Node node-2-218 (pool system-ondemand): prod pods 1 (['prod-app-q']) together with dev pods 1 (['dev-app-t']). Memory limit total/allocatable 1.55, CPU limit total/allocatable 1.55, containers without a memory limit 2 |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 233123, top [['Elastic Load Balancing v2/DescribeTargetHealth', 73904], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 40764], ['EC2/DescribeInstances', 37048], ['EC2/DescribeSecurityGroups', 24297], ['Elastic Load Balancing v2/RegisterTargets', 11506]], |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster disabled (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 8, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 8, apps whose targetRevision is a branch or HEAD 8 ['argocd/application/app-r-prod', 'argocd/application/app-q-prod', 'argocd/application/app-m-prod', 'argocd/application/app-o-prod', 'argocd/application/app-s-prod', 'argocd/application/app-l-backend-prod', 'argocd/appl |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `controlplane.apiserver-slow-traces.cluster` | warn | low | 24h Traces (requests over 500ms) 238: [{'op': 'List', 'count': 215}, {'op': 'Call conversion webhook', 'count': 15}, {'op': 'Create', 'count': 6}, {'op': 'Update', 'count': 2}] |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.5, cluster IPv6 False, queries per second 60.49. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-node.node-1-209` | warn | low | Node node-1-209 (c9g.xlarge, pool build-arm64): CPU p95 0.0006705068467009002, memory p95 0.032318602794103674, 39.35 USD/month |
| `cost.idle-node.node-1-62` | warn | low | Node node-1-62 (r8gd.large, pool default): CPU p95 0.03290315867627512, memory p95 0.12397521517246729, 29.78 USD/month |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | aws_ebs_csi_* series 0, add-on v1.37.0-eksbuild.1. When enabled, shows EC2 API errors {} / throttles None |
| `ecr.no-lifecycle-policy.ecr/registry/<account>` | warn | low | repositories without a lifecycle policy ['app-n', 'bitnami/kafka', 'ecr-app-s-postgresql-pgvector', 'bitnami/mysql'] (total 10.9GiB), overall 43 repositories, 787 images, 399.4GiB ≈ 42.9 USD/month, untagged images 227 (excluding 151 attestations) |
| `ecr.no-replication.ecr/registry/<account>` | warn | low | replication rules 0, repositories used by prod 27, total 399.4GiB |
| `ecr.tag-mutable-prod.ecr/registry/<account>` | warn | low | MUTABLE repositories 42/43, used by prod 26: ['ecr-app-s-frontend-eks-prod', 'ecr-app-r-eks-prod', 'ecr-app-q-backend-eks-prod', 'ecr-app-q-web-eks-prod', 'ecr-app-p-postgresql-prod', 'ecr-app-m-admin-eks-prod', 'ecr-app-s-postgresql-pgvector', 'ecr-app-q-postgresql-prod']…, |
| `ecr.untagged-images.ecr/registry/<account>` | warn | low | untagged images 227/787 (excluding 151 BuildKit attestation manifests), repositories 43 |
| `eso.version-old.cluster` | warn | low | external-secrets 0.9.13 (ExternalSecrets 47, PushSecrets 0) |
| `grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana` | warn | low | Grafana 10.2.3 (database ok), ingress ['monitor.my-cluster'], dashboards 28 |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init` | warn | low | image <account>.dkr.ecr.us-east-1.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1 (tag tag, imagePullPolicy Always, registry <account>.dkr.ecr.us-east-1.amazonaws.com) |
| `hygiene.unused-crds.cluster` | warn | low | 26 of 47 CRDs have zero objects (by group {'generators.external-secrets.io': 7, 'monitoring.coreos.com': 6, 'networking.k8s.aws': 4, 'eventing.keda.sh': 2, 'external-secrets.io': 3, 'keda.sh': 2, 'crd.k8s.amazonaws.com': 1, 'vpcresources.k8s.aws': 1}), 18 webhooks |
| `karpenter.spot-to-spot-consolidation-off.cluster` | warn | low | FEATURE_GATES {'Drift': 'true', 'SpotToSpotConsolidation': 'false'}, NodeClaims terminated by spot interruption 254, drift True |
| `keda.operator-metrics-disabled.cluster` | warn | low | --enable-prometheus-metrics False, operator keda_* metrics exposed False, scaler errors in logs (24h) 0 |
| `keda.scaledobject-never-active.cluster` | warn | low | inactive for more than 14 days ['prod-app-l-backend/scaledobject/app-l-graph-worker'], not Ready [], fallback active [], scale-to-zero targets ['prod-app-l-backend/scaledobject/app-l-file-worker', 'prod-app-l-backend/scaledobject/app-l-graph-worker'] |
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 1040 packets (sum over nodes), services with externalTrafficPolicy Local 0, no-local-endpoints drops 0 |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alerts-never-fired.cluster` | warn | low | 130 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent', 'ConfigReloaderSidecarE |
| `observability.saturation-signal-missing.cluster` | warn | low | 36 of 40 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-m', 'app-m-admin'), ('dev-app-m', 'app-m-api'), ('dev-app-m', 'app-m-backend'), ('dev-app-m', 'app-m-frontend'), ('dev-app-o', 'app-o-admin')]), n |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"'])], receivers ['null', 'slack-sre', 'slack-system'], default receiver s |
| `observability.unclassified-errors.cluster` | warn | low | 104 unclassified error lines (20261 lines scanned, 32 files). Top: [('external-secrets \| {"level":"error","ts":<n>.<n>,"msg":"Reconciler error","controller":"externalsecr', 32), ('ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver', 2), ('kube-proxy  |
| `observability.unstructured-logs.argocd` | warn | low | Of 15370 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-n` | warn | low | Of 59437 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.app-s-prod` | warn | low | Of 732671 lines in 1h, 0 parse as JSON (0.0) |
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
| `resilience.exec-probe.app-s-prod/statefulset/app-s-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "pwcuser" -d "dbname=app-s_tp" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s |
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
| `resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | low | pod argocd-repo-server-d487895cc-bth22: 7d memory working set p95 85 MB / request 512 MB = 0.17 |
| `resources.memory-request-overprovisioned.dev-app-m/deploy/app-m-backend:backend` | warn | low | pod app-m-backend-695864bdf6-qwhn7: 7d memory working set p95 79 MB / request 256 MB = 0.31 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-ai:ai` | warn | low | pod app-o-ai-7cdbdc7544-szzcl: 7d memory working set p95 344 MB / request 1024 MB = 0.34 |
| `resources.memory-request-overprovisioned.dev-app-o/deploy/app-o-backend:backend` | warn | low | pod app-o-backend-69dbdf4f65-9x6jc: 7d memory working set p95 131 MB / request 512 MB = 0.26 |
| `resources.memory-request-overprovisioned.dev-app-t/sts/app-t-postgres:postgres` | warn | low | pod app-t-postgres-0: 7d memory working set p95 29 MB / request 256 MB = 0.11 |
| `resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | low | pod karpenter-9769889bd-nphgs: 7d memory working set p95 24 MB / request 256 MB = 0.09 |
| `resources.memory-request-overprovisioned.middleware/sts/redis-master:redis` | warn | low | pod redis-master-0: 7d memory working set p95 5 MB / request 256 MB = 0.02 |
| `resources.memory-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | low | pod vm-single-0: 7d memory working set p95 149 MB / request 512 MB = 0.29 |
| `resources.memory-request-overprovisioned.prod-app-q/sts/app-q-backend-postgresql:postgresql` | warn | low | pod app-q-backend-postgresql-0: 7d memory working set p95 49 MB / request 256 MB = 0.19 |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-ai:ai` | warn | low | ['pod app-o-ai-55b7448547-mzrjj: 7d memory working set p95 609 MB / request 2048 MB = 0.30', 'pod app-o-ai-55b7448547-mpj4r: 7d memory working set p95 414 MB / request 2048 MB = 0.20'] |
| `resources.memory-request-overprovisioned.prod-app-o/deploy/app-o-backend:backend` | warn | low | ['pod app-o-backend-596479b6f8-cx44t: 7d memory working set p95 94 MB / request 512 MB = 0.18', 'pod app-o-backend-596479b6f8-nv9j2: 7d memory working set p95 73 MB / request 512 MB = 0.14'] |
| `resources.memory-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding` | warn | low | pod app-l-embedding-server-577b67cff8-2x6zb: 7d memory working set p95 1042 MB / request 4096 MB = 0.25 |
| `resources.memory-request-overprovisioned.prod-app-l-backend/deploy/app-l-frontend:frontend` | warn | low | ['pod app-l-frontend-6d58bbfcfc-nfk9x: 7d memory working set p95 74 MB / request 256 MB = 0.29', 'pod app-l-frontend-6d58bbfcfc-2qgs6: 7d memory working set p95 72 MB / request 256 MB = 0.28'] |
| `resources.memory-request-overprovisioned.prod-app-p/sts/app-p-postgresql:postgresql` | warn | low | pod app-p-postgresql-0: 7d memory working set p95 83 MB / request 256 MB = 0.32 |
| `resources.memory-request-overprovisioned.app-s-prod/sts/app-s-backend-postgresql:postgresql` | warn | low | pod app-s-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.22 |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-backend` | warn | low | HPA prod-app-l-backend/app-l-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-l-backend/deployment/app-l-frontend` | warn | low | HPA prod-app-l-backend/app-l-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-admin` | warn | low | HPA dev-app-m/app-m-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 158.5 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-api` | warn | low | HPA dev-app-m/app-m-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 188.2 days ago |
| `scaling.hpa-never-scaled.dev-app-m/deployment/app-m-backend` | warn | low | HPA dev-app-m/app-m-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 18% / target 70%, metrics ['cpu'], last scale 59.0 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-admin` | warn | low | HPA dev-app-o/app-o-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 48.0 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-backend` | warn | low | HPA dev-app-o/app-o-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 10.0 days ago |
| `scaling.hpa-never-scaled.dev-app-o/deployment/app-o-frontend` | warn | low | HPA dev-app-o/app-o-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 26% / target 70%, metrics ['cpu'], last scale 10.0 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-admin-frontend` | warn | low | HPA dev-app-n/app-n-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 28.5 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-backend` | warn | low | HPA dev-app-n/app-n-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 13% / target 70%, metrics ['cpu'], last scale 32.5 days ago |
| `scaling.hpa-never-scaled.dev-app-n/deployment/app-n-frontend` | warn | low | HPA dev-app-n/app-n-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 0.2 days ago |
| `scaling.hpa-never-scaled.dev-app-t/deployment/app-t-backend` | warn | low | HPA dev-app-t/app-t-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 12.1 days ago |
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
| `tenancy.dev-shares-prod-nodes.node-1-62` | warn | low | Node node-1-62 (pool default): prod pods 5 (['prod-app-m', 'prod-app-l-backend', 'prod-app-p']) together with dev pods 1 (['dev-app-n']). Memory limit total/allocatable 0.66, CPU limit total/allocatable 2.85, containers without a memory limit 0 |
| `tenancy.dev-shares-prod-nodes.node-2-60` | warn | low | Node node-2-60 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-m', 'prod-app-n']) together with dev pods 2 (['dev-app-m', 'dev-app-n']). Memory limit total/allocatable 1.49, CPU limit total/allocatable 2.44, containers without |
| `traffic.alb-protection-off.k8s-acmeprodlb-b18a4555d7` | warn | low | ALB k8s-acmeprodlb-b18a4555d7: deletion_protection False, access_logs False, target groups in the ingress group 40 |
| `vpccni.metrics-unreadable.cluster` | warn | low | 2 of 8 nodes without readable ipamd metrics (localhost:61678): ['node-1-117', 'node-2-60'] |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |
| `hygiene.no-progressive-delivery.cluster` | fail | info | No progressive-delivery component (Argo Rollouts, Flagger). All deployments are rolling updates (replace everything) -- ALB weighted target groups are not used either |

### 7-6. 도구 메모, kubegap 자체에 대한 것

번호는 2026-10-26 16:27 full 리포트의 메모 34~40 에서 이어가요. 그 앞은 16:18 daily 29~33, 14:52 full 19~28, 14:43 daily 13~18, 05:14 full 1~12 예요.

아직 열려 있는 이전 메모: 1 `traffic.pod-not-ready` 외삽, 이번엔 해당 파드가 없어 재현 안 됨. 2, 20, 30, 37 삭제된 노드와 새 노드의 `node.network-errors`, 메모 44 로 재현. 3 시스템 노드의 `vpccni.node-ip-exhaustion` high, 재현: `ip-10-0-1-241` 6/9, `ip-10-0-2-218` 13/15. 4 계정 VPC 쿼터의 `eks.service-quota-near-limit` high, 재현. 5, 32, 38 SSM 미등록 노드 두 대에서 실패하는 명령, 메모 45 로 재현. 7, 13, 22 노드 교체가 new/resolved 로 보이는 것, 이번엔 교체 없어 재현 안 됨. 19 수집 중 Prometheus working set, 이번 0.775 로 14:52 의 0.892 보다 낮아 재현 안 됨. 21, 31, 39 Kubernetes 1.32 지원 종료일 두 가지, 메모 46. 23 `recent_changes` 가 배포와 재스케줄을 구분 못 함, 이번엔 배포 없음. 24 12:33 KST 회수가 Karpenter 로그에만 보임, 여전함. 25 스케줄러 근거의 `<n>` 마스킹, 재현: `controlplane.scheduler-unschedulable` 근거 전부 "<n>/<n> nodes are available". 26 dev 타깃 그룹의 `traffic.alb-unhealthy-targets` high, 재현하고 다시 내림. 27 `observability.log-coverage-gap` 이 `ip-10-0-1-209` 의 테인트 이유를 안 적음, 재현. 28, 36 수집 간격이 짧을 때의 apiserver 값, 메모 43 으로 재현. 29, 35 `traffic.ingress-p95-latency` 의 시간당 p95 평균과 요청 수 하한, 메모 42 로 재현. 33 `events.tracked-warning-reasons.FailedScheduling` 의 히스토리 의존, 이번엔 조용해서 발견 없음. 34 메모 41 로 재현. 40 메모 47 로 재현.

41. **메모 34 재현, 세 번째.** `api.example-b.ai` 의 24시간 5xx 합이 또 정확히 723.0 이에요. `aws/alb-metrics.json` 타깃 그룹 k8s-app-svc-d65740e6d5: 14:52 스냅샷 723.0 / 122,621 요청, 16:27 스냅샷 723.0 / 120,939 요청, 이번 723.0 / 120,706 요청. 요청 합은 세 번 다 움직였는데 5xx 합은 그대로예요. 이번엔 시간당 최대값도 105 에서 116 으로 바뀌었는데 합은 같아요. 5xx 쿼리의 `StartTime`/`EndTime` 이 요청 쿼리와 다르게 잡히거나, 15개 포인트가 캐시된 응답일 가능성이 있어요. 확인 방법: 두 쿼리의 `queries` 블록과 시간당 포인트 목록을 나란히 비교.
42. **메모 29, 35 재현.** `traffic.ingress-p95-latency` 는 40개 중 40개 pass 인데 `summary.json` traffic.ingresses 에는 `api.v1.example-b.ai` 가 86건 요청에 p95 평균 10.92초, 시간당 최대 35.36초, `app-r.my-cluster` 이 7건에 평균 31.08초예요. 요청 수 하한 때문에 건너뛴 호스트를 근거에 "요청 N건이라 건너뜀" 으로 적어 주면 좋겠어요.
43. **메모 28, 36 재현.** 16:27 full 수집 종료 19분 뒤에 이번 full 수집이 시작됐어요. `controlplane.apiserver-5xx` 503 초당 0.0037 `metrics/apiserver_5xx_rate.json` 16:48:16 KST 과 새로 뜬 `controlplane.apiserver-latency.LIST` 0.618초는 수집이 만든 값이라 내렸어요. `collect` 가 직전 스냅샷의 `taken_at` 이 30분 안이면 경고를 찍어 주면 좋겠어요.
44. **메모 2, 20, 30, 37 재현.** `node.network-errors.<ip>:9100:eth0` 이 여전히 1차 fail/medium 4,857건인데 그 노드는 12:33 KST 에 회수돼 `inventory.json` 에 없어요. `node.network-errors.<ip>:9100:eth0` 은 2.5시간 된 노드에서 147건으로 warn 이에요. `inventory.nodes` 에 없는 인스턴스는 빼 주세요.
45. **메모 5, 32, 38 재현.** 실패 명령 24개 `summary.json` run.failed: ALB 컨트롤러 파드 프록시 타임아웃 1건, SSM 미등록 노드 `ip-10-0-1-117`, `ip-10-0-2-60` 의 "node not registered with SSM" 19건, 라이프사이클 정책이 없는 ECR 저장소 4개의 `ecr.lifecycle-policy` 조회 4건. ECR 의 "정책 없음" 은 발견 사항이지 실패가 아니라 `_summary.failed` 에서 빼야 해요.
46. **메모 21, 31, 39 재현.** `platform.k8s-version-eol.cluster` 근거는 이번에도 "end of support 2026-03-23 D+217" 이에요. 16:18 daily 는 같은 룰 0.1.50 으로 "2026-02-28 D+240" 을 찍었어요. 근거에 출처를 적어 주세요.
47. **메모 40 재현.** `cost.idle-compute-high` 와 `cost.request-waste` 의 근거가 달러로 쓰여 있어요. 이 리포트는 유저 지시로 금액을 쓰지 않아서 비율만 인용했어요. 유휴 비율 0.95, 줄일 수 있는 CPU 5.23코어.
48. **`resources.cpu-throttling` 이 5분 순간값 하나로 fail/high 를 내요.** `prod-app-p/app-p-postgresql-0` 의 `metrics/cpu_throttle_ratio_5m.json` 은 0.419 인데 같은 컨테이너의 `metrics/cpu_limit_p95_ratio_7d.json` 은 0.0089, `metrics/namespace_cpu_throttled_ratio_7d.json` 의 prod-app-p 은 0.005 예요. CPUThrottlingHigh 알림은 `metrics/alerts_pending_now.json` 에만 있고 firing 이 아니에요. 이전 스냅샷 다섯 개에 이 파드가 한 번도 없었어요. 수집 시각에 걸린 짧은 CPU 몰아 쓰기가 high 로 올라와요. 제안: 5분 값 옆에 1시간 또는 6시간 비율을 같이 넣고, 5분만 넘으면 warn, 긴 창도 넘으면 fail 로 나누기.

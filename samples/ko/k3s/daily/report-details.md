# kubegap 상세 리포트 — default (`default`), daily 점검

사람이 먼저 읽을 리포트는 옆의 `report.md`예요. 이 파일에는 판정 전체와 표가 있고, `scripts/kubegap render-details`가 수집 자료와 에이전트가 사실 파일에 쓴 분석 기록을 모아 만들어요. 다음 점검의 에이전트도 이 파일을 읽어요. 점검 항목 id와 근거 문장은 정의에서 그대로 가져와서 영어예요.

| 항목 | 값 |
|---|---|
| kube context / 클러스터 | `default` / default (k3s, v1.33.5+k3s1) |
| 실행 시각 / 모드 | 2026-11-05T17:01:01+09:00 / daily (수집 90.5초, 모드 때문에 건너뛴 단계 16개, 실패 0개) |
| 프로파일 | `lab` (detected) |
| kubegap / 점검 항목 버전 / 로그 시그니처 버전 | 0.1.2 / 0.1.80 / 1.1.0 |
| 노드 / 네임스페이스 / 파드 / CRD | 2 (Ready 2) / 26 / 153 / 64 |
| 컴포넌트 (23) | actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, prometheus, prometheus-operator, reloader |
| 메트릭 저장소 | prometheus 3.7.3 retention 30d / size 0B via port-forward |
| 로그 저장소 | 없음 (Loki를 찾지 못했어요) |
| 노드 접속 | ssh (k3s: SSH); SSM 미등록 0대 |
| 수집 폴더 | `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00` |

## 1. 자동 판정 집계와 에이전트 조정

| 심각도(기본값) | fail | warn | 같은 모드의 지난 점검 대비 |
|---|---|---|---|
| critical | 2 | 2 | fail +1 · warn +0 |
| high | 25 | 66 | fail -6 · warn +1 |
| medium | 56 | 103 | fail +2 · warn -4 |
| low | 9 | 108 | fail +0 · warn +1 |
| info | 0 | 0 | 같은 모드의 지난 점검 없음 |

점검 항목 347개 중 판정 238개, 프로파일에서 끈 것 41개, 건너뜀 11개, 이 모드에서 수집 안 함 55개, 오류 0개, 도구 없음 0개, 에이전트 판정 2개예요. 숨긴 항목은 0개예요.

### 1-1. 자동 판정과 최종 판정이 다른 곳

| 항목 | 자동 판정 | 최종 | 이유 |
|---|---|---|---|
| resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn | fail high | fail critical | symptom_linked이고 실제 증상이 있어요. 7일 재시작 1963번, 24시간 Ready 0분, Deployment Available=False. |
| resilience.no-backup.cluster | warn critical | warn critical | warn이라 규칙상 high지만 critical로 유지해요. 완화 신호인 백업 CronJob 7개가 전부 노드 로컬에만 쓰고 5개는 원본과 같은 노드예요. app-c-postgres는 백업이 없고 etcd 스냅샷도 node-b 로컬이에요. |
| observability.no-symptom-alerts.cluster | warn critical | warn high | warn은 앱 메트릭 알림 7개라는 완화 신호를 찾았다는 뜻이라 규칙대로 high예요. |
| traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external 외 3개 | fail high | fail medium | 작은 k3s 클러스터의 NodePort는 LAN 노출이라 프로파일 규칙으로 medium이에요. 인터넷에서 닿는지는 확인 안 했어요. |
| resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog | fail medium | pass | 마지막 성공이 2026-11-05T08:00:51Z로 수집 시각 08:01Z 직전이에요. 9.2시간은 수집 시각이 아니라 요약을 다시 돌린 2026-11-06T02:12 기준으로 잰 값이에요(도구 메모 1). |
| controlplane.apiserver-5xx.cluster | warn high | warn medium | 503 0.007/s는 수집 중에 잰 값이에요. kubegap이 apiserver pod proxy로 speaker와 파드 메트릭을 읽는 시간과 겹쳐서 사용자 영향으로 세지 않아요. |
| scaling.no-hpa-serving-prod 11개 | warn low | info | 노드 2대의 lab 프로파일이라 프로파일 규칙으로 info예요. |
| operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn | fail medium | fail medium | 상태와 심각도는 그대로예요. 지속 시간 10.4시간은 다시 센 값으로 바꿨어요(recounts). |

### 1-2. 에이전트가 다시 센 숫자

| 항목 | 자동 판정 | 최종 | 이유 |
|---|---|---|---|
| operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn | Available=False 10.4시간 | 수집 시각 기준 약 1.2시간 (2026-11-05T06:50:54Z ~ 08:01:01Z). 컨테이너는 그보다 훨씬 오래 죽어 있었어요 | age를 수집 시각이 아니라 평가를 돌린 2026-11-06T02:12 KST 기준으로 쟀어요. |
| resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn | 재시작 10710번 | 지난 daily 점검 8171번에서 2539번 늘었어요. 2026-10-24 점검에서 이미 7418번 | 세 스냅샷의 objects/pods.json restartCount를 비교했어요. |
| resilience.n-plus-one.cluster | CPU 요청 6.17코어 > 남는 노드 6.0코어로 부족 | 옮길 수 있는 파드 29개는 node-a에 들어가요(필요 2.3코어, 여유 3.45코어). 못 뜨는 건 node-b에 묶인 19개이고, 이건 CPU가 아니라 nodeSelector와 local-path 때문이에요 | summary.json resilience.n_plus_one.pools[0]과 pools[1]을 따로 봤어요. |
| resilience.backup-same-node.* | fail 4개, warn 3개 | 원본과 같은 노드에 쓰는 것 5개(app-d-postgres-backup, app-d-postgres-vn-backup, app-f-mysql-backup, app-g-postgres-backup, app-e-postgres-backup), 다른 노드 로컬 2개(app-a-postgres-backup, app-d-postgres-mx-backup), 노드 밖 복사본 0개 | app-e-postgres-backup은 warn이지만 same_node_as_source true예요. summary.json resilience.backup.rows 7줄을 셌어요. |
| resilience.n-plus-one.cluster (CPU 요청 증가) | 5.99 → 6.17코어 | +0.18코어 중 0.13코어가 HPA 스케일아웃(app-f-admin +1 × 30m, app-f-api-server +1 × 100m) | 두 스냅샷의 objects/deployments.json replicas와 requests를 비교했어요. 나머지 0.05코어는 따로 찾지 않았어요. |

## 2. 지금 fail인 critical과 high (자동 판정)

| 항목 | 심각도 | 연속 횟수 | 근거 |
|---|---|---|---|
| `observability.no-slo.cluster` | critical |  | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules [] known issue #15 |
| `resilience.n-plus-one.cluster` | critical |  | Allocatable without the largest node node-b (12.0 cores, 30.7GB): CPU 6.0 cores vs total requests 6.17 (short), memory 30.7GB vs 23.9GB (OK). Pods on that node 48 (prod 15). Pods that fit on no other node [{'namespace' … |
| `argocd.prune-manages-namespace-or-crd.cluster` | high | 9 | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/acme-site', 'argocd/application/app-e-api' … |
| `coredns.availability.cluster` | high | 9 | replicas 1, nodes with pods 1 of 2 ({'node-b': 1}), PDB [], spread declared (antiAffinity/topologySpread) True, restarts total 1 |
| `events.tracked-warning-reasons.BackOff` | high | 9 | Container keeps dying and the restart interval grows (CrashLoopBackOff). 193081 occurrences total (4 events, trend over 45 snapshots [124477, 124589, 124978, 125226, 125317, 126950, 127112, 127228, 128098, 128331, 800 … |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana` | high |  | emptyDir volumes: storage, sc-dashboard-volume, sc-datasources-volume, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus` | high |  | emptyDir volumes: config-out, prometheus-kube-prometheus-stack-prometheus-db, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.33.5+k3s1: upstream end of life 2026-06-28, 131 days past |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-backup` | high |  | app-d-prod/app-d-postgres-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b') … |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup` | high |  | app-d-prod/app-d-postgres-vn-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-vn-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b') … |
| `resilience.backup-same-node.app-f-prod/app-f-mysql-backup` | high |  | app-f-prod/app-f-mysql-backup: schedule '50 2 * * *', dump PVCs ['mysql-backup-app-f-mysql-0'] → nodes ['node-b'], hostPath [], source DB [('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-mysql', 'node-b') … |
| `resilience.backup-same-node.app-g-prod/app-g-postgres-backup` | high |  | app-g-prod/app-g-postgres-backup: schedule '0 3 * * *', dump PVCs ['app-g-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-g-prod/statefulset/app-g-postgres', 'node-b')], off-node … |
| `resilience.replicas-same-node.app-d-prod/deployment/app-d` | high |  | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-admin` | high |  | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server` | high |  | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client` | high |  | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | high |  | 10710 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-05T07:58:00Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-e-api/sts/app-e-minio:minio` | high |  | pod app-e-minio-0: 7d memory working set p95 / limit = 0.98 |
| `security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts` | high |  | app-a-prod/configmap/app-v-scripts: keys ['discord_sales_bot.py:TOKEN', 'discord_sales_bot.py:OPENAI_API_KEY', 'app-v_autopost.py:client_secret', 'app-v_autopost.py:resource_owner_secret'] … |
| `security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts` | high |  | app-d-prod/configmap/app-d-app-v-scripts: keys ['app-d_ga4_digest.py:DISCORD_BOT_TOKEN', 'app-d_ga4_digest.py:token', 'app-d_policy_radar.py:OPENAI_API_KEY', 'app-d_policy_radar.py:DISCORD_BOT_TOKEN' … |
| `tenancy.quota-near-limit.app-i-prod/app-i-prod-quota` | high |  | app-i-prod/app-i-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi' … |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external` | high |  | nodeport app-d-prod/app-d-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external` | high |  | nodeport app-d-prod/app-d-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external` | high |  | nodeport app-d-prod/app-d-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external` | high |  | nodeport app-g-prod/app-g-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |

## 3. 같은 모드의 지난 점검 이후 변화

`2026-10-27T15-58-38`와 `2026-11-05T17-01-01`를 비교했어요. 점검 항목 버전은 0.1.51에서 0.1.80로 바뀌었어요.

- **새로 생김 (7)**: `controlplane.apiserver-latency.PUT` (warn/medium), `coredns.forward-upstream-errors.cluster` (warn/medium), `logs.signatures.cert-manager.challenge-failed` (warn/medium), `logs.signatures.metallb.speaker-peer-unreachable` (warn/low), `observability.alert-firing-stale.CPUThrottlingHigh/logging` (warn/medium), `resilience.n-plus-one.cluster` (fail/critical), `resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator` (warn/high)
- **해결됨 (13)**: `controlplane.watch-count-high.cluster` (warn/medium), `logs.signatures.grafana.db-locked` (warn/medium), `logs.signatures.grafana.provisioning-error` (warn/medium), `logs.signatures.keda.scaler-error` (warn/medium), `logs.signatures.metallb.speaker-error` (warn/medium), `resilience.restarts-crashloop.arc-systems/arc-actions-runner-controller-5c9d9ffd65-766b6:manager` (warn/high), `resources.cpu-throttling.app-d-prod/sts/app-d-postgres:postgres` (warn/high), `resources.cpu-throttling.app-f-prod/deploy/app-f-api-server:app` (warn/high), `resources.cpu-throttling.app-i-prod/deploy/app-i-web:web` (warn/high), `resources.memory-limit-near-p95.app-a-prod/deploy/app-a-umami:umami` (warn/high), `resources.memory-limit-near-p95.app-a-prod/sts/app-a-postgres:postgres` (warn/high), `scaling.hpa-flapping.app-f-prod/hpa/app-f-app-w` (warn/medium), `traffic.pod-not-ready.argocd/argocd-repo-server` (warn/medium)
- **바뀜 (8)**: `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn` (['warn', 'fail']/['medium', 'medium']), `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog` (['warn', 'fail']/['medium', 'medium']), `resilience.replicas-same-node.app-a-prod/deployment/app-a-backend` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.app-e-api/sts/app-e-postgres:postgres` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` (['fail', 'warn']/['high', 'high']), `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` (['fail', 'warn']/['high', 'high']), `resources.memory-limit-near-p95.logging/ds/fluent-bit:fluent-bit` (['fail', 'warn']/['high', 'high'])
- **이름이 바뀐 것으로 보임 (0)**: 없음
- **오브젝트**: 추가 17개, 삭제 7개, 변경 2개: `deployments/app-f-prod/app-f-admin` spec.replicas, `deployments/app-f-prod/app-f-api-server` spec.replicas
- **Warning 이벤트**: BackOff +35054 (Pod/app-c-prod/app-c-coturn-549854dfcb-jgp4h), Unhealthy -55 (Pod/app-e-api/app-e-postgres-0)

### 3-0. 클러스터가 아니라 점검 항목이 바뀐 것

클러스터가 아니라 점검 항목이 바뀌어서 생기거나 사라진 결과예요. 위 목록에서는 뺐어요. `diff.json`의 `findings.criteria_changes`에서 가져왔고, 리포트에서는 기준 변경으로 다뤄요.

- **지난 점검에 없었거나 돌지 않은 항목 (1)**: `traffic.ingress-nginx-retired.cluster` (new, warn/medium)

규칙 변경을 추적하기 전의 점검 항목이에요. 버전이 달라요. 이 항목은 위 목록에 `rule_known: false`로 남아 있고, 리포트는 항목의 notes를 보고 판단해요: `controlplane.apiserver-latency`, `controlplane.watch-count-high`, `coredns.forward-upstream-errors`, `logs.signatures`, `observability.alert-firing-stale`, `operators.unhealthy-condition`, `resilience.cronjob-stale`, `resilience.n-plus-one`, `resilience.replicas-same-node`, `resilience.restarts-crashloop`, `resources.cpu-throttling`, `resources.memory-limit-near-p95`, `scaling.hpa-flapping`, `traffic.pod-not-ready`
- **계속 남아 있는 항목**: 최근 9번 모두 나온 항목 361개, 3번 이상 나온 항목 363개예요. 많이 나온 점검 항목: `resilience.single-eligible-node` 37, `observability.golden-signals-missing` 29, `resilience.no-prestop` 22, `resilience.liveness-dependency-path` 21, `resources.cpu-request-overprovisioned` 18, `hygiene.mutable-image-tag` 15, `resilience.single-replica-in-prod` 15, `resilience.db-probe-timeout` 13

### 3-1. 왜 바뀌었나

지난 daily 점검(2026-10-27) 이후 노드, 버전, 컴포넌트, 네임스페이스는 바뀌지 않았어요. 오브젝트 변화는 etcd 스냅샷 교체 5개, cert-manager Order 10개 추가, Actions 러너 교체, app-f-prod Deployment 2개의 replicas 변경뿐이에요. replicas 변경은 HPA가 한 일이고, 이 때문에 CPU 요청 합이 5.99코어에서 6.17코어로 늘어 node-b를 잃을 때의 여유 계산이 실패로 바뀌었어요. app-c-coturn은 지난번에도 같은 이미지 digest로 CrashLoopBackOff였고 재시작이 8171번에서 10710번으로 늘었어요. 2026-11-05T06:50:54Z에 Deployment Available 조건이 다시 False로 바뀌면서 그 항목이 warn에서 fail이 됐어요. 2026-10-28T19:25Z에 node-b의 cert-manager와 keda 파드가, 22:06Z에 node-a의 여러 파드가 exit 255로 한꺼번에 끝났어요. 노드나 k3s 재시작으로 보이지만 확인하지 못했어요. cert-manager ACME challenge 실패 10번은 오늘 새벽 갱신 중에 생겼고 Order는 전부 valid로 끝났어요. 체크 기준도 바뀌었어요. rubric이 0.1.51에서 0.1.80으로, 로그 시그니처가 1.0.15에서 1.1.0으로 바뀌어 일부 로그 경고는 이름이 바뀌거나 사라졌어요. CPU 스로틀링 3개와 메모리 근접 2개가 사라진 건 그 순간 값이 기준 아래로 내려온 결과예요.

## 4. 영역별 상세

(daily 점검에는 영역별 상세가 없어요. 2절과 `report.md`를 보세요)

## 5. 없는 것 목록

| 항목 | 상태 | 심각도 | 필요한 이유 | 제안 |
|---|---|---|---|---|
| `observability.no-slo.cluster` | fail | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `resilience.no-backup.cluster` | warn | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |

있어야 하는데 없는 도구 종류: backup, slo.

## 6. 숨긴 항목, 도구 없음, 수집 안 함

- 숨긴 항목 0: 없음
- 숨김 기한이 지난 항목 0: 없음
- 도구 없음 0: 없음
- daily 모드에서 수집 안 함 55: `resources.krr-recommendation`, `controlplane.etcd-slow`, `node.kernel-oom-node-level`, `node.kernel-lockup`, `node.kernel-io-fs-errors`, `node.kernel-nic-events`, `node.conntrack-table-full`, `node.kernel-net-mem-pressure`, `node.cgroup-v1`, `node.sysctl-tuning`, `node.cri-not-ready`, `node.cri-exited-containers`, `node.pod-logs-large`, `node.pod-dir-large`, `node.service-restarts`, `node.reboot-required`, `node.os-updates-pending`, `node.kubelet-reserved-missing`, `node.kubelet-eviction-memory-missing`, `node.clock-unsynced-os`, `node.zombie-processes`, `node.os-not-collected`, `security.polaris-security-danger`, `hygiene.polaris-reliability-danger`, `hygiene.helm-release-not-deployed`, `hygiene.helm-release-stale`, `node.kubelet-api-qps-low`, `node.docker-and-containerd`, `node.container-writable-layer-large`, `node.large-images`, `platform.k3s-secrets-encryption-off`, `platform.k3s-check-config-missing`, `platform.k3s-etcd-snapshot-stale`, `platform.k3s-etcd-snapshot-local-only`, `platform.k3s-certificate-expiring`, `platform.k3s-journald-unbounded`, `platform.k3s-apiserver-bind-all`, `node.smartmontools-missing`, `node.thermal-high`, `platform.k3s-datastore-slow`, `platform.k3s-datastore-large`, `traffic.flannel-mtu-mismatch`, `traffic.flannel-errors`, `traffic.podcidr-near-full`, `traffic.flannel-sysctl-off`, `traffic.flannel-vxlan-cross-subnet`, `traffic.flannel-drops-growing`, `traffic.flannel-node-data-missing`, `kubeproxy.node-cmd-unavailable`, `storage.local-path-over-capacity`, `storage.local-path-node-pinned`, `storage.local-path-fs-near-full`, `storage.local-path-orphan-dirs`, `storage.local-path-prod-delete-reclaim`, `storage.local-path-provisioner-unhealthy`
- 건너뛰었거나 오류가 난 점검 항목 11: `observability.log-volume-change` (skip: summary.logs.loki.volume_change missing), `security.no-secrets-manager` (skip: profile lab does not require family secrets-manager), `scaling.no-node-autoscaler` (skip: profile lab does not require family node-autoscaler), `observability.log-coverage-gap` (skip: summary.logs.loki.coverage missing), `observability.loki-not-ready` (skip: nothing to judge: loki not present), `observability.loki-ingest-discarded` (skip: summary.logs.agents.loki_metrics missing), `observability.promtail-dropped` (skip: summary.logs.agents.promtail missing), `observability.log-error-ratio-high` (skip: summary.logs.loki.namespaces_1h missing), `observability.unstructured-logs` (skip: summary.logs.loki.namespaces_1h missing), `hygiene.deprecated-api` (skip: summary.hygiene.deprecated.items missing), `observability.alert-metric-without-dashboard` (skip: nothing to judge: dashboards json not available)
- 일부만 판정한 점검 항목 0 (판정에 필요한 자료가 없는 대상은 판정하지 않았고 통과로 세지 않았어요): 없음

## 7. 부록

### 7-1. 실행한 수집기와 단계

| 수집기 | 단계 | 실패 | 건너뜀 (이유) |
|---|---|---|---|
| core | 13 |  | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'cronjobs.batch', 'storageclasses.storage.k8s.io']); node-os (not collected in daily mode); kubelet-configz (not collected in daily mode); krr (not collected in daily mode); polaris (not collected in daily mode); pluto (not collected in daily mode); kubent (not collected in daily mode); helm-list (not collected in daily mode) |
| k3s-platform | 8 |  | k3s-journal-errors (not collected in daily mode); k3s-journal-stats (not collected in daily mode); k3s-scheduler-unschedulable (not collected in daily mode); k3s-webhook-failures (not collected in daily mode); k3s-etcd-slow (not collected in daily mode); kubelet-pleg (not collected in daily mode); k3s-node (not collected in daily mode); containerd-log (not collected in daily mode) |
| actions-runner-controller | 0 |  | no collect.yaml (collector not implemented) |
| alertmanager | 4 |  |  |
| argocd | 3 |  |  |
| cert-manager | 1 |  |  |
| coredns | 1 |  |  |
| elasticsearch-opensearch | 0 |  | no collect.yaml (collector not implemented) |
| external-secrets | 1 |  |  |
| flannel | 1 |  |  |
| fluent-bit | 0 |  | no collect.yaml (collector not implemented) |
| fluent-bit-events | 0 |  | no collect.yaml (collector not implemented) |
| grafana | 5 |  | datasources (grafana_api_token missing); dashboards (grafana_api_token missing); dashboards-json (grafana_api_token missing) |
| ingress-nginx | 0 |  | no collect.yaml (collector not implemented) |
| keda | 2 |  | operator-metrics (True) |
| kube-proxy | 2 |  | proxy-mode (not collected in daily mode) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| local-path-provisioner | 1 |  |  |
| metallb | 1 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| reloader | 0 |  | no collect.yaml (collector not implemented) |

명령 348개, 90.5초. 실패한 단계 0개

단계는 성공했지만 그 안에서 실패한 명령 2개 (run.log): `argocd.repo-server-metrics.argocd-repo-server-848dcbb4db-jz8xs` Error from server (ServiceUnavailable): error trying to reach service: proxy error from 127.0.0.1:6443 while dialing …; `metallb.metallb-speaker-metrics.speaker-xfxlv` Unable to connect to the server: context deadline exceeded (Client.Timeout exceeded while awaiting headers)

### 7-2. 판정한 점검 항목

점검 항목 347개: disabled 41, done 238, llm 2, not-collected 55, skip 11. 불러오기 오류: 없음.

### 7-3. 로그 시그니처 일치와 분류 안 된 오류

로그 시그니처 1.1.0으로 파일 21개, 20697줄을 읽었어요 (컴포넌트: alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, fluent-bit, grafana, ingress-nginx, keda, local-path-provisioner, metallb, metrics-server, prometheus, reloader). 분류 안 된 오류는 41줄이에요.

| 시그니처 | 컴포넌트 | 영역 | 심각도 | 상태 | 횟수 | 처음, 마지막 | 샘플 |
|---|---|---|---|---|---|---|---|
| fluent-bit.flush-failed | fluent-bit | observability | medium | warn | 10 | 2026-11-05T07:33:46Z , 2026-11-05T07:59:41Z | [pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:33:46.228066540+09:00 [2026/11/05 07:33:46] [ warn] [engine] failed to flush chunk … |
| cert-manager.challenge-failed | cert-manager | security | medium | warn | 10 | 2026-11-05T02:31:09Z , 2026-11-05T03:35:40Z | [pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.690144851Z E1105 02:31:09.689988       1 sync.go:190] "propagation check … |
| fluent-bit.upstream-down | fluent-bit | observability | medium | warn | 7 | 2026-11-05T07:30:56Z , 2026-11-05T08:02:06Z | [pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:30:56.226441555+09:00 [2026/11/05 07:30:56] [error] [input:kubernetes_events:kubernetes_events.1] upstream … |
| metallb.speaker-peer-unreachable | metallb | traffic | low | warn | 482 | 2026-11-05T04:42:34Z , 2026-11-05T08:02:35Z | [pod/speaker-lqmcg/speaker] 2026-11-05T04:42:34.862388956Z {"caller":"speakerlist.go:259","error":"1 error occurred:\n\t* Failed to join <ip>:7946 … |
| cert-manager.orphan-tls-secret | cert-manager | hygiene | low | warn | 64 | 2026-11-04T15:18:56Z , 2026-11-05T00:57:19Z | [pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553816246Z E1104 15:18:56.553660       1 indexers.go:61] "unable to … |

| 메시지 형태 | 횟수 | 파일 |
|---|---|---|
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="argocd/argocd-tls" error="Operat | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="app-f-prod/app-f-api-prod-tls" error=" | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="monitoring/grafana-acme-com- | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="logging/kibana-tls" error="Opera | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="argocd/argocd-tls-7" erro | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'argocd/cm-acme-http-solver-zznj7' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="argocd-tls-7-<n>" resource_namespace="argocd" resource_kind="Order" re | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.orders" key="argocd/argocd-tls-7-<n>" error="Operation cannot b | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "challenge in work queue no longer exists" err="challenge.acme.cert-manager.io \"argocd-tls-7-<n>-<n>\" not found" logger="cert-manager.chal | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to error processing" err="challenges.acme.cert-manager.io \"argocd-tls-7-<n>-<n>\" not found" logger="cert-manager.orde | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-readiness" key="argocd/argocd-tls" error="Operatio | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-issuing" key="argocd/argocd-tls" error="Operation  | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="app-f-prod/app-f-api-prod-tls-7 | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'app-f-prod/cm-acme-http-solver-nf26f' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="app-f-api-prod-tls-7-<n>" resource_namespace="app-f-prod" resource_kind="Ord | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.orders" key="app-f-prod/app-f-api-prod-tls-7-<n>" error="Operation ca | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "challenge in work queue no longer exists" err="challenge.acme.cert-manager.io \"app-f-api-prod-tls-7-<n>-<n>\" not found" logger="cert-manager | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to error processing" err="challenges.acme.cert-manager.io \"app-f-api-prod-tls-7-<n>-<n>\" not found" logger="cert-manager | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-readiness" key="app-f-prod/app-f-api-prod-tls" error="Op | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-issuing" key="app-f-prod/app-f-api-prod-tls" error="Oper | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="monitoring/grafana-acme-co | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'monitoring/cm-acme-http-solver-6qn6f' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="grafana-acme-com-tls-7-<n>" resource_namespace="monitoring" resour | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.orders" key="monitoring/grafana-acme-com-tls-7-<n>" error=" | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "challenge in work queue no longer exists" err="challenge.acme.cert-manager.io \"grafana-acme-com-tls-7-<n>-<n>\" not found" logger="cer | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-readiness" key="monitoring/grafana-acme-com-tl | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="logging/kibana-tls-7" err | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'logging/cm-acme-http-solver-jlpgp' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="kibana-tls-7-<n>" resource_namespace="logging" resource_kind="Order" r | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.orders" key="logging/kibana-tls-7-<n>" error="Operation cannot  | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |

### 7-4. 에이전트가 직접 읽은 원본 파일

- `inventory.json`
- `findings-draft.json`
- `summary.json`
- `diff.json`
- `events.json`
- `objects/deployments.json`
- `objects/pods.json`
- `objects/statefulsets.json`
- `objects/services.json`
- `objects/configmaps.json`
- `objects/applications.argoproj.io.json`
- `objects/horizontalpodautoscalers.autoscaling.json`
- `objects/etcdsnapshotfiles.k3s.cattle.io.json`
- `objects/storageclasses.json`
- `metrics/restarts_7d.json`
- `metrics/disk_usage_ratio.json`
- `metrics/targets_down.json`
- `metrics/scrape_targets_down_by_job.json`
- `metrics/ingress_nginx_5xx_ratio_1h.json`
- `metrics/flannel_if_up.json`
- `metrics/memory_limit_p95_ratio_7d.json`
- `metrics/memory_p95_7d_bytes.json`
- `extra/coturn-previous-head.txt`
- `extra/coturn-previous.txt`
- `extra/coturn-help-full.txt`
- `extra/speaker-node-a-tail.txt`
- `extra/speaker-node-b-tail.txt`
- `extra/nodes-wide.txt`
- `extra/apiserver-proxy-to-node-a.txt`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/findings-draft.json`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/summary.json`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/objects/pods.json`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/objects/deployments.json`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/events.json`
- `~/.kubegap/snapshots/default/2026-10-27T15-58-38/inventory.json`
- `~/.kubegap/snapshots/default/2026-10-24T23-56-28/objects/pods.json`
- `https://kubernetes.io/docs/concepts/storage/volumes/`
- `https://prometheus-operator.dev/docs/platform/storage/`

### 7-5. 자동 판정 전체 (모든 fail과 warn, 코드 결과 그대로)

| id | 상태 | 기본 심각도 | 근거 |
|---|---|---|---|
| `observability.no-slo.cluster` | fail | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules [] known issue #15 |
| `resilience.n-plus-one.cluster` | fail | critical | Allocatable without the largest node node-b (12.0 cores, 30.7GB): CPU 6.0 cores vs total requests 6.17 (short), memory 30.7GB vs 23.9GB (OK). Pods on that node 48 (prod 15). Pods that fit on no other node [{'namespace': 'app-a-prod', 'pod': 'app-a-postgres-0', 'node': 'node-b', 'cpu': 0.2 … |
| `observability.no-symptom-alerts.cluster` | warn | critical | 161 alert rules: symptom 0, cause 153, app metrics (assumed symptom) 7. Symptom ratio 0.0. Symptom rules: [] |
| `resilience.no-backup.cluster` | warn | critical | no backup tool (family backup). Alternative signals: etcd snapshots 5, backup-like CronJobs that ran in the last 7 days ['app-a-prod/app-a-postgres-backup', 'app-d-prod/app-d-postgres-backup', 'app-d-prod/app-d-postgres-mx-backup', 'app-d-prod/app-d-postgres-vn-backup' … |
| `argocd.prune-manages-namespace-or-crd.cluster` | fail | high | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/acme-site', 'argocd/application/app-e-api', 'argocd/application/app-h', 'argocd/application/app-k' … |
| `coredns.availability.cluster` | fail | high | replicas 1, nodes with pods 1 of 2 ({'node-b': 1}), PDB [], spread declared (antiAffinity/topologySpread) True, restarts total 1 |
| `events.tracked-warning-reasons.BackOff` | fail | high | Container keeps dying and the restart interval grows (CrashLoopBackOff). 193081 occurrences total (4 events, trend over 45 snapshots [124477, 124589, 124978, 125226, 125317, 126950, 127112, 127228, 128098, 128331, 800, 938, 1096, 1165, 1210, 1717, 1926, 1994, 2246, 2292, 2359, 2566, 2613, 3508 … |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana` | fail | high | emptyDir volumes: storage, sc-dashboard-volume, sc-datasources-volume, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus` | fail | high | emptyDir volumes: config-out, prometheus-kube-prometheus-stack-prometheus-db, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.33.5+k3s1: upstream end of life 2026-06-28, 131 days past |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-backup` | fail | high | app-d-prod/app-d-postgres-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-mx', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-vn', 'node-b') … |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup` | fail | high | app-d-prod/app-d-postgres-vn-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-vn-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-mx', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-vn', 'node-b') … |
| `resilience.backup-same-node.app-f-prod/app-f-mysql-backup` | fail | high | app-f-prod/app-f-mysql-backup: schedule '50 2 * * *', dump PVCs ['mysql-backup-app-f-mysql-0'] → nodes ['node-b'], hostPath [], source DB [('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-qdrant', 'node-a')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-g-prod/app-g-postgres-backup` | fail | high | app-g-prod/app-g-postgres-backup: schedule '0 3 * * *', dump PVCs ['app-g-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-g-prod/statefulset/app-g-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.replicas-same-node.app-d-prod/deployment/app-d` | fail | high | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-admin` | fail | high | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server` | fail | high | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client` | fail | high | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | fail | high | 10710 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-05T07:58:00Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-e-api/sts/app-e-minio:minio` | fail | high | pod app-e-minio-0: 7d memory working set p95 / limit = 0.98 |
| `security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts` | fail | high | app-a-prod/configmap/app-v-scripts: keys ['discord_sales_bot.py:TOKEN', 'discord_sales_bot.py:OPENAI_API_KEY', 'app-v_autopost.py:client_secret', 'app-v_autopost.py:resource_owner_secret'], mounted/referenced by ['app-a-prod/cronjob/app-v-autopost-en' … |
| `security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts` | fail | high | app-d-prod/configmap/app-d-app-v-scripts: keys ['app-d_ga4_digest.py:DISCORD_BOT_TOKEN', 'app-d_ga4_digest.py:token', 'app-d_policy_radar.py:OPENAI_API_KEY', 'app-d_policy_radar.py:DISCORD_BOT_TOKEN', 'app-d_sales_bot.py:TOKEN', 'app-d_sales_bot.py:OPENAI_API_KEY'], mounted/referenced by … |
| `tenancy.quota-near-limit.app-i-prod/app-i-prod-quota` | fail | high | app-i-prod/app-i-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi', 'requests.storage': '30Gi'}, used {'limits.cpu': '1800m', 'limits.memory': '2Gi' … |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external` | fail | high | nodeport app-d-prod/app-d-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external` | fail | high | nodeport app-d-prod/app-d-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external` | fail | high | nodeport app-d-prod/app-d-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external` | fail | high | nodeport app-g-prod/app-g-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.007 (code 503) |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 265 occurrences total (28 events, trend over 45 snapshots [0, 0, 0, 0, 7, 0, 0, 8, 0, 33, 0, 0, 5, 6, 6, 0, 7, 7, 9, 9, 9, 0, 0, 12, 16, 0, 27, 28, 30, 31, 31, 32, 32, 33, 33, 33, 34, 62, 62, 74, 0, 0, 0, 7, 7], flat), first … |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.77 |
| `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | storage emptyDir (PVC None), PVC usage None, TSDB 21.3GiB, retention 30d (size cap 0B), actual oldest sample 30.8 days, failed compactions over 7 days 0, WAL corruptions 0, corruptions at startup 0 |
| `resilience.backup-same-node.app-a-prod/app-a-postgres-backup` | warn | high | app-a-prod/app-a-postgres-backup: schedule '15 3 * * *', dump PVCs ['app-a-postgres-backup-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-a-prod/statefulset/app-a-postgres', 'node-b'), ('app-a-prod/statefulset/app-a-redis', 'node-b')], off-node copy hint (s3 … |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup` | warn | high | app-d-prod/app-d-postgres-mx-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-mx-backup-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-mx', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-vn', 'node-b') … |
| `resilience.backup-same-node.app-e-api/app-e-postgres-backup` | warn | high | app-e-api/app-e-postgres-backup: schedule '50 3 * * *', dump PVCs ['app-e-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-e-api/statefulset/app-e-minio', 'node-b'), ('app-e-api/statefulset/app-e-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-backend` | warn | high | replicas 2 (Running 2), node distribution {'node-b': 1, 'node-a': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend` | warn | high | replicas 2 (Running 2), node distribution {'node-b': 1, 'node-a': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway` | warn | high | replicas 2 (Running 2), node distribution {'node-a': 1, 'node-b': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller` | warn | high | replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller` | warn | high | 12 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resilience.restarts-crashloop.cert-manager/cert-manager-cainjector-7bf5c557bb-kbtv7:cert-manager-cainjector` | warn | high | 14 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator` | warn | high | 10 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres` | warn | high | app-a-prod/statefulset/app-a-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis` | warn | high | app-a-prod/statefulset/app-a-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn` | warn | high | app-c-prod/deployment/app-c-coturn: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['hostNetwork'], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-signaling` | warn | high | app-c-prod/deployment/app-c-signaling: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-web` | warn | high | app-c-prod/deployment/app-c-web: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres` | warn | high | app-c-prod/statefulset/app-c-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d` | warn | high | app-d-prod/deployment/app-d: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 2, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-admin` | warn | high | app-d-prod/deployment/app-d-admin: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-mx` | warn | high | app-d-prod/deployment/app-d-mx: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-mx-worker` | warn | high | app-d-prod/deployment/app-d-mx-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-vn` | warn | high | app-d-prod/deployment/app-d-vn: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-vn-worker` | warn | high | app-d-prod/deployment/app-d-vn-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-d-prod/deployment/app-d-worker` | warn | high | app-d-prod/deployment/app-d-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres` | warn | high | app-d-prod/statefulset/app-d-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-d-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-mx` | warn | high | app-d-prod/statefulset/app-d-postgres-mx: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-d-postgres-mx-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-vn` | warn | high | app-d-prod/statefulset/app-d-postgres-vn: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-d-postgres-vn-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-d-prod/statefulset/app-d-redis` | warn | high | app-d-prod/statefulset/app-d-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-d-redis-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-e-api/statefulset/app-e-minio` | warn | high | app-e-api/statefulset/app-e-minio: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-e-minio-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-e-api/statefulset/app-e-postgres` | warn | high | app-e-api/statefulset/app-e-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-e-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-admin` | warn | high | app-f-prod/deployment/app-f-admin: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 3, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-api-server` | warn | high | app-f-prod/deployment/app-f-api-server: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 3, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-app-x-client` | warn | high | app-f-prod/deployment/app-f-app-x-client: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 2, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-embed` | warn | high | app-f-prod/deployment/app-f-embed: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['extended resource nvidia.com/gpu'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-excel-agent` | warn | high | app-f-prod/deployment/app-f-excel-agent: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-app-w` | warn | high | app-f-prod/deployment/app-f-app-w: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-mysql` | warn | high | app-f-prod/statefulset/app-f-mysql: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate mysql-backup', 'local-path volumeClaimTemplate mysql-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-qdrant` | warn | high | app-f-prod/statefulset/app-f-qdrant: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-qdrant-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/deployment/kibana` | warn | high | logging/deployment/kibana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/statefulset/elasticsearch` | warn | high | logging/statefulset/elasticsearch: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-prod/deployment/app-g` | warn | high | app-g-prod/deployment/app-g: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-prod/statefulset/app-g-postgres` | warn | high | app-g-prod/statefulset/app-g-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-g-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana` | warn | high | monitoring/deployment/kube-prometheus-stack-grafana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics` | warn | high | monitoring/deployment/kube-prometheus-stack-kube-state-metrics: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator` | warn | high | monitoring/deployment/kube-prometheus-stack-operator: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | high | monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.registry/statefulset/registry` | warn | high | registry/statefulset/registry: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate registry-data'], replicas 1, serves traffic True |
| `resources.cpu-throttling.app-e-api/sts/app-e-postgres:postgres` | warn | high | pod app-e-postgres-0: throttling ratio now 0.46, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-c7fr8: throttling ratio now 0.29, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most', 'pod fluent-bit-nnsb5: throttling ratio now 0.28, no 24-hour value: under 0.001 through the day or the query was not collected … |
| `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` | warn | high | pod elasticsearch-0: throttling ratio now 0.43, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.56, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.memory-limit-near-p95.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-c7fr8: 7d memory working set p95 / limit = 0.84', 'pod fluent-bit-nnsb5: 7d memory working set p95 / limit = 0.82'] |
| `security.plaintext-configmap-secret.default/configmap/app-y-backend-config` | warn | high | default/configmap/app-y-backend-config: keys ['JWT_RELAY_SECRET', 'JWT_SECRET', 'TWITTER_CLIENT_SECRET', 'TWITTER_CLIENT_SECRET_RELAY'], mounted/referenced by [] |
| `security.plaintext-secret-env.logging/cronjob/es-index-retention:retention` | warn | high | Container retention env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/deployment/kibana:kibana` | warn | high | Container kibana env ['ELASTICSEARCH_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch` | warn | high | Container elasticsearch env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn` | warn | high | ['hostNetwork'], containers allowing root ['coturn'] |
| `tenancy.ci-shares-prod-nodes.node-a` | warn | high | Node node-a (pool (no-pool)): prod pods 32 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']) together with CI pods 1 (['arc-actions-runner-controller-5c9d9ffd65-766b6']). Heavy runners True, minutes above 90% node CPU in 7d 0.0, memory … |
| `tenancy.ci-shares-prod-nodes.node-b` | warn | high | Node node-b (pool (no-pool)): prod pods 15 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']) together with CI pods 2 (['ci-runner-8tt2w-2p2pg', 'ci-runner-8tt2w-4w6rk']). Heavy runners True, minutes above 90% node CPU in 7d … |
| `tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota` | warn | high | app-a-prod/app-a-prod-quota: requests entries in hard ['requests.memory'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota` | warn | high | app-b-prod/app-b-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-i-prod/app-i-prod-quota` | warn | high | app-i-prod/app-i-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `coredns.nxdomain-ratio-high.cluster` | fail | medium | NXDOMAIN share of responses in 1h 0.696, queries per second 30.92, NXDOMAIN share of queries forwarded upstream 0.847 (upstreams ['1.1.1.1:53', '8.8.8.8:53']), pods with default ndots (5) 153, autopath False, cache hit ratio 0.8509 |
| `eso.store-static-credentials.cluster` | fail | medium | stores with static key auth ['ClusterSecretStore/aws-secret-store'] (all auth methods {'ClusterSecretStore/aws-secret-store': 'static-key(Secret)'}), providers ['aws'], ExternalSecrets 39 (prod 33) |
| `hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix` | fail | medium | image arizephoenix/phoenix:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn` | fail | medium | image coturn/coturn:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `observability.alert-firing-stale.CPUThrottlingHigh/monitoring` | fail | medium | Firing for 73.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'monitoring', 'pod': 'prometheus-kube-prometheus-stack-prometheus-0', 'severity': 'info'} |
| `observability.alert-firing-stale.KubeCPUOvercommit` | fail | medium | Firing for 30.6 days (ALERTS_FOR_STATE). Labels {'severity': 'warning'} |
| `observability.alert-firing-stale.KubeJobFailed/app-a-prod` | fail | medium | ["Firing for 11.2 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-a-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'warning'}", "Firing for 7.4 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace' … |
| `observability.alert-firing-stale.KubePodCrashLooping/app-c-prod` | fail | medium | Firing for 38.1 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-c-prod', 'pod': 'app-c-coturn-549854dfcb-jgp4h', 'severity': 'warning'} |
| `observability.alert-firing-stale.KubeQuotaFullyUsed/app-i-prod` | fail | medium | Firing for 127.4 days (ALERTS_FOR_STATE). Labels {'namespace': 'app-i-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'info'} |
| `observability.alerts-always-firing.CPUThrottlingHigh` | fail | medium | 7d firing samples 86849 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeCPUOvercommit` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeDeploymentReplicasMismatch` | fail | medium | 7d firing samples 20098 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeJobFailed` | fail | medium | 7d firing samples 40320 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodCrashLooping` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeQuotaFullyUsed` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.ingress-controller-metrics-missing.ingress-controller` | fail | medium | 29 ingresses, 0 ingress-controller request metric series, namespaces with app http_* metrics [], ALB CloudWatch False — per-backend gaps are the 29 golden-signals-missing (warn) findings |
| `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn` | fail | medium | Available=False (MinimumReplicasUnavailable) for 10.4 hours: Deployment does not have minimum availability. |
| `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog` | fail | medium | schedule '* * * * *' (about every 0.016666666666666666h), last success 2026-11-05T08:00:51Z (9.2h ago), last schedule 2026-11-05T08:01:00Z, active Jobs 1, failed Jobs ['app-a-sandbox-watchdog-29881700', 'app-a-sandbox-watchdog-29887083'], suspend False |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres` | fail | medium | app-a-prod/statefulset/app-a-postgres container postgres: liveness exec timeout 1s, period 15s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis` | fail | medium | app-a-prod/statefulset/app-a-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres` | fail | medium | app-c-prod/statefulset/app-c-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-mx:postgres` | fail | medium | app-d-prod/statefulset/app-d-postgres-mx container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-vn:postgres` | fail | medium | app-d-prod/statefulset/app-d-postgres-vn container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres:postgres` | fail | medium | app-d-prod/statefulset/app-d-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-d-prod/statefulset/app-d-redis:redis` | fail | medium | app-d-prod/statefulset/app-d-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-mysql:mysql` | fail | medium | app-f-prod/statefulset/app-f-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-qdrant:qdrant` | fail | medium | app-f-prod/statefulset/app-f-qdrant container qdrant: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-g-prod/statefulset/app-g-postgres:postgres` | fail | medium | app-g-prod/statefulset/app-g-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-i-prod/deployment/app-i-postgres:postgres` | fail | medium | app-i-prod/deployment/app-i-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.single-node-dependency.app-c-prod/deployment/app-c-coturn` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-node-dependency.app-c-prod/statefulset/app-c-postgres` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resilience.single-node-dependency.app-f-prod/deployment/app-f-embed` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-node-dependency.app-f-prod/statefulset/app-f-mysql` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resilience.single-node-dependency.app-f-prod/statefulset/app-f-qdrant` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-replica-in-prod.app-a-prod/app-a-phoenix` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-a-prod/app-a-umami` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-b-prod/app-b-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-b-prod/app-b-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-coturn` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-signaling` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-d-prod/app-d-mx-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-d-prod/app-d-vn-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-d-prod/app-d-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-f-prod/app-f-embed` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-f-prod/app-f-excel-agent` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-i-prod/app-i-api` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-i-prod/app-i-postgres` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-i-prod/app-i-web` | fail | medium | replicas 1, no HPA |
| `resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-embed:app` | fail | medium | pod app-f-embed-67f6f74f6c-lb7lj: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00 |
| `security.networkpolicy-coverage.cluster` | fail | medium | 20 of 22 user namespaces have no NetworkPolicy, of which production ['app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']; with: ['app-a-prod', 'argocd'] |
| `tenancy.prod-boundary-missing.app-c-prod` | fail | medium | app-c-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-d-prod` | fail | medium | app-d-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-f-prod` | fail | medium | app-f-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-g-prod` | fail | medium | app-g-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `traffic.pod-not-ready.app-c-prod/app-c-coturn` | fail | medium | 24h minimum Ready ratio 0.0 (pod app-c-coturn-549854dfcb-jgp4h, about 1440 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL None |
| `argocd.app-out-of-sync-or-unhealthy.cluster` | warn | medium | Applications 18 (prod 10), OutOfSync ['argocd/application/root'] (prod []), Degraded/Missing/Unknown [] (prod []), Progressing (rolling out, not abnormal) ['argocd/application/app-c'], apps with conditions ['ExcludedResourceWarning']: ['argocd/application/app-k'], last operation failed [] |
| `argocd.default-project-wildcard.cluster` | warn | medium | AppProjects 2, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 4/18 (prod 10) |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.825s |
| `controlplane.apiserver-latency.PUT` | warn | medium | PUT p99 0.700s |
| `coredns.forward-upstream-errors.cluster` | warn | medium | upstreams ['1.1.1.1:53', '8.8.8.8:53']: SERVFAIL in 1h 0 (0.0), health check failures 1.0084, max_concurrent rejections 0.0, overall SERVFAIL ratio 0.0 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk` | warn | medium | image registry.acme.com/app-a-sandbox-adk:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c` | warn | medium | image registry.acme.com/app-a-sandbox-c:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express` | warn | medium | image registry.acme.com/app-a-sandbox-express:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go` | warn | medium | image registry.acme.com/app-a-sandbox-go:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs` | warn | medium | image registry.acme.com/app-a-sandbox-nestjs:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network` | warn | medium | image registry.acme.com/app-a-sandbox-network:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs` | warn | medium | image registry.acme.com/app-a-sandbox-nextjs:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python` | warn | medium | image registry.acme.com/app-a-sandbox-python:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml` | warn | medium | image registry.acme.com/app-a-sandbox-python-ml:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring` | warn | medium | image registry.acme.com/app-a-sandbox-spring:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql` | warn | medium | image registry.acme.com/app-a-sandbox-sql:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo` | warn | medium | image registry.acme.com/app-a-sandbox-todo:latest (tag latest, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.mutable-image-tag.registry/cronjob/registry-tag-cleanup:tag-cleanup` | warn | medium | image curlimages/curl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.role` | warn | medium | Label role: 7 workloads (production 0) depend on it via nodeSelector/affinity, present on 1/2 nodes — e.g. logging/deployment/kibana, monitoring/deployment/kube-prometheus-stack-grafana, monitoring/deployment/kube-prometheus-stack-kube-state-metrics |
| `hygiene.node-label-dependency.storage` | warn | medium | Label storage: 10 workloads (production 7) depend on it via nodeSelector/affinity, present on 1/2 nodes — e.g. app-a-prod/statefulset/app-a-postgres, app-a-prod/statefulset/app-a-redis, app-d-prod/statefulset/app-d-postgres |
| `hygiene.pvc-unbound-or-unused.cluster` | warn | medium | Non-Bound PVCs [], Released/Failed PVs [], Bound PVCs used by no pod [('default', 'data-app-z-db-0')] |
| `logs.signatures.cert-manager.challenge-failed` | warn | medium | 10 occurrences (2026-11-05T02:31:09Z ~ 2026-11-05T03:35:40Z), thresholds warn 5/fail 100. Files: ['logs/pods/cert-manager/cert-manager_cert-manager.log']. Samples: ['[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.690144851Z E1105 02:31:09.689988       1 sync.go:190] … |
| `logs.signatures.fluent-bit.flush-failed` | warn | medium | 10 occurrences (2026-11-05T07:33:46Z ~ 2026-11-05T07:59:41Z), thresholds warn 10/fail 500. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ["[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:33:46.228066540+09:00 [2026/11/05 07:33:46] [ warn] [engine] failed to flush chunk … |
| `logs.signatures.fluent-bit.upstream-down` | warn | medium | 7 occurrences (2026-11-05T07:30:56Z ~ 2026-11-05T08:02:06Z), thresholds warn 5/fail 200. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ['[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:30:56.226441555+09:00 [2026/11/05 07:30:56] [error] … |
| `observability.alert-firing-stale.CPUThrottlingHigh/logging` | warn | medium | Firing for 3.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'logging', 'pod': 'elasticsearch-0', 'severity': 'info'} |
| `observability.fluentbit-output-errors.cluster` | warn | medium | Output errors in 1h None, failed retries (dropped) None, dropped records None, input records None -- fluent-bit metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured, so they are not really 0 |
| `observability.golden-signals-missing.app-a-prod/app-a-backend` | warn | medium | hosts ['api.app-a.acme.com', 'api.example-a.dev'], backends ['app-a-backend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-frontend` | warn | medium | hosts ['app-a.acme.com', 'example-a.dev', 'www.example-a.dev'], backends ['app-a-frontend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-phoenix` | warn | medium | hosts ['obs.example-a.dev'], backends ['app-a-phoenix'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-umami` | warn | medium | hosts ['umami.example-a.dev', 'umami.example-l.com'], backends ['app-a-umami'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.argocd/argocd-server-ingress` | warn | medium | hosts ['argocd.acme.com'], backends ['argocd-server'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-b-prod/app-b-backend` | warn | medium | hosts ['app-b-api.acme.com'], backends ['app-b-backend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-b-prod/app-b-frontend` | warn | medium | hosts ['app-b.acme.com'], backends ['app-b-frontend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-c-prod/app-c-signaling-ingress` | warn | medium | hosts ['app-c.acme.com', 'example-h.space', 'www.example-h.space'], backends ['app-c-signaling-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-c-prod/app-c-web-ingress` | warn | medium | hosts ['app-c.acme.com', 'example-h.space', 'www.example-h.space'], backends ['app-c-web-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.acme-site/acme-site` | warn | medium | hosts ['acme.com'], backends ['acme-site'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-d-prod/app-d-admin-ingress` | warn | medium | hosts ['admin.example-e.com'], backends ['app-d-admin-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-d-prod/app-d-ingress` | warn | medium | hosts ['app.example-e.com'], backends ['app-d-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-d-prod/app-d-mx-ingress` | warn | medium | hosts ['mx.example-e.com'], backends ['app-d-mx-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-d-prod/app-d-vn-ingress` | warn | medium | hosts ['vn.example-e.com'], backends ['app-d-vn-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-e-api/app-e-api` | warn | medium | hosts ['app-e-api.acme.com', 'app-e-cdn.acme.com'], backends ['app-e-api', 'app-e-minio'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-admin-ingress` | warn | medium | hosts ['app-f-admin-prod.acme.com', 'example-f.com', 'www.example-f.com'], backends ['app-f-admin-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-api-server-ingress` | warn | medium | hosts ['app-f-api-prod.acme.com'], backends ['app-f-api-server-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-api-server-oauth-ingress` | warn | medium | hosts ['example-k.kr', 'www.example-k.kr'], backends ['app-f-api-server-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-app-x-client-ingress` | warn | medium | hosts ['app-f-app-x-client-prod.acme.com', 'example-k.kr', 'www.example-k.kr'], backends ['app-f-app-x-client-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-app-w-ingress` | warn | medium | hosts ['app-f-app-w-prod.acme.com', 'example-g.com', 'www.example-g.com'], backends ['app-f-app-w-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.logging/kibana` | warn | medium | hosts ['kibana.acme.com'], backends ['kibana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-g-prod/app-g-ingress` | warn | medium | hosts ['app-g.acme.com', 'example-j.com', 'www.example-j.com'], backends ['app-g-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.monitoring/monitoring-grafana-ingress` | warn | medium | hosts ['grafana.acme.com'], backends ['kube-prometheus-stack-grafana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h/app-h` | warn | medium | hosts ['app-h.acme.com'], backends ['app-h'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.registry/registry` | warn | medium | hosts ['registry.acme.com'], backends ['registry'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-k/app-k` | warn | medium | hosts ['app-k.acme.com'], backends ['app-k-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-k/app-k-auth` | warn | medium | hosts ['app-k.acme.com'], backends ['app-k-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-i-prod/app-i-api` | warn | medium | hosts ['api.example-i.dev'], backends ['app-i-api'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-i-prod/app-i-web` | warn | medium | hosts ['example-i.dev'], backends ['app-i-web'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 161 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AppAClusterCPU80', 'AppAClusterMem80', 'AppABackendDown', 'AppAFrontendDown', 'AppAPostgresDown', 'AppAGatewayDown']), classes {'cause': 153 … |
| `resilience.cronjob-policy.app-d-prod/app-d-postgres-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-d-prod/app-d-postgres-mx-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-d-prod/app-d-postgres-vn-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-f-prod/app-f-mysql-backup` | warn | medium | schedule '50 2 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-g-prod/app-g-postgres-backup` | warn | medium | schedule '0 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog` | warn | medium | app-a-prod/app-a-sandbox-watchdog: schedule '* * * * *' (about 0.016666666666666666h), recent Job max 51s / median 51s = 0.85x the interval (1 measured), concurrencyPolicy Forbid, active Jobs 1 |
| `resilience.db-probe-timeout.app-e-api/statefulset/app-e-postgres:postgres` | warn | medium | app-e-api/statefulset/app-e-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-h/deployment/app-h-postgres:postgres` | warn | medium | app-h/deployment/app-h-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 92, 'system-cluster-critical': 1, 'system-node-critical': 3}, prod pods without a class 49 of 49, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.cluster` | warn | medium | Of 16 DB workloads with a PVC, production DBs without a backup CronJob in the same namespace: ['app-c-prod/statefulset/app-c-postgres', 'app-i-prod/deployment/app-i-postgres']. Backup CronJobs 7 (local only 7, same node as source 5) |
| `resilience.single-node-dependency.registry/statefulset/registry` | warn | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-backend:backend` | warn | medium | ['pod app-a-backend-79c97cbbd6-kkc2d: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03', 'pod app-a-backend-79c97cbbd6-ztv7h: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-frontend:frontend` | warn | medium | ['pod app-a-frontend-574ff75654-6sqcp: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06', 'pod app-a-frontend-574ff75654-rjbzg: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-gateway:gateway` | warn | medium | ['pod app-a-gateway-6d898d5f68-rqgsj: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod app-a-gateway-6d898d5f68-5sd56: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-phoenix:phoenix` | warn | medium | pod app-a-phoenix-56ddc584cf-znjvs: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07 |
| `resources.cpu-request-overprovisioned.app-a-prod/sts/app-a-postgres:postgres` | warn | medium | pod app-a-postgres-0: 7d CPU p95 0.055 cores / request 0.20 cores = 0.28; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-e-api/deploy/app-e-api:api` | warn | medium | pod app-e-api-7cb685d8cf-zxqt7: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-api-server:app` | warn | medium | ['pod app-f-api-server-5d6b56f78b-xxzbl: 7d CPU p95 0.015 cores / request 0.10 cores = 0.15', 'pod app-f-api-server-5d6b56f78b-srwnk: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07', 'pod app-f-api-server-5d6b56f78b-fd59m: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06'] |
| `resources.cpu-request-overprovisioned.app-f-prod/sts/app-f-mysql:mysql` | warn | medium | pod app-f-mysql-0: 7d CPU p95 0.016 cores / request 0.20 cores = 0.08; database-like: keep the request |
| `resources.cpu-request-overprovisioned.ingress-nginx/deploy/nginx-ingress-ingress-nginx-controller:controller` | warn | medium | ['pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04', 'pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-5d67c9bcfb-8fcdl: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-7ff5758fd7-gq7g7: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-85ff5bb446-lwkl6: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | pod coredns-59d4d457d-qjng8: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-7bfffcd44-fkpfm: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08 |
| `resources.cpu-request-overprovisioned.logging/deploy/kibana:kibana` | warn | medium | pod kibana-59c97cdf75-ht2zf: 7d CPU p95 0.004 cores / request 0.20 cores = 0.02 |
| `resources.cpu-request-overprovisioned.app-h/deploy/app-h:web` | warn | medium | pod app-h-54c94979b5-b65b5: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.app-i-prod/deploy/app-i-postgres:postgres` | warn | medium | pod app-i-postgres-76b69b654d-lzf4d: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01; database-like: keep the request |
| `scaling.hpa-flapping.app-f-prod/hpa/app-f-api-server` | warn | medium | 34 desired changes over 7 days |
| `security.no-default-deny.cluster` | warn | medium | Namespaces with default-deny (ingress, empty podSelector) [], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']. Enforced True |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label ['metallb-system'], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']. Share of containers allowing root 0.71 (58 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 80/82, of which 37 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix' … |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['app-f-prod/app-f-qdrant-data-app-f-qdrant-0', 'app-a-prod/app-a-postgres-backup-pvc', 'app-a-prod/data-app-a-postgres-0', 'app-a-prod/data-app-a-redis-0', 'app-c-prod/postgres-data-app-c-postgres-0' … |
| `tenancy.burst-tenant-unbounded.app-f-prod` | warn | medium | app-f-prod (prod): 7d CPU median 0.027 cores, p95 0.059 cores, max 0.589 cores = 22.1x the median. No quota, shares nodes with prod True, nodes {'node-a': 12, 'node-b': 1}, CPU limit total 8.2 cores |
| `tenancy.prod-boundary-missing.app-b-prod` | warn | medium | app-b-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-i-prod` | warn | medium | app-i-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-without-quota.arc-systems` | warn | medium | arc-systems (ci): no ResourceQuota. Pods 3, CPU requests total 1.0 cores, memory requests total 2.0GB, 7d CPU p95 0.004 cores (cluster share 0.003), memory p95 0.36GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-c-prod` | warn | medium | app-c-prod (prod): no ResourceQuota. Pods 4, CPU requests total 0.17 cores, memory requests total 0.66GB, 7d CPU p95 0.01 cores (cluster share 0.01), memory p95 0.23GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-d-prod` | warn | medium | app-d-prod (prod): no ResourceQuota. Pods 12, CPU requests total 0.49 cores, memory requests total 3.91GB, 7d CPU p95 0.028 cores (cluster share 0.025), memory p95 1.66GB, 7d max/median 1.6x. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-f-prod` | warn | medium | app-f-prod (prod): no ResourceQuota. Pods 13, CPU requests total 1.28 cores, memory requests total 8.12GB, 7d CPU p95 0.059 cores (cluster share 0.054), memory p95 4.73GB, 7d max/median 22.1x. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-g-prod` | warn | medium | app-g-prod (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.28GB, 7d CPU p95 0.006 cores (cluster share 0.005), memory p95 0.14GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.tenant-without-limitrange.arc-systems` | warn | medium | arc-systems (ci): no LimitRange, containers without requests 4 / without a memory limit 4 (pods 3). 7d CPU p95 0.004 cores, memory p95 0.36GB |
| `traffic.coredns-latency.cluster` | warn | medium | 1h DNS request p99 0.1355s, SERVFAIL ratio 0.0 |
| `traffic.ingress-nginx-retired.cluster` | warn | medium | ingress-nginx 1.14.0 (Deployment ingress-nginx/nginx-ingress-ingress-nginx-controller); ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes; admission webhook on |
| `hygiene.no-standard-labels.cluster` | fail | low | Of 110 workloads, share with standard labels 0.23. prod workloads without: ['app-a-prod/deployment/app-a-backend', 'app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix' … |
| `node.swap-enabled.<ip>:9100` | fail | low | swap 8.0 GiB |
| `platform.k3s-server-url-stale.node-b` | fail | low | host <ip> of --server https://<ip>:6443 is not among current node IPs or names |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend` | fail | low | HPA app-a-prod/app-a-backend: share of 15 days at min 1.00, min 2 max 6, current CPU utilization 3% / target 70%, metrics ['cpu'], last scale 3.4 days ago |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend` | fail | low | HPA app-a-prod/app-a-frontend: share of 15 days at min 1.00, min 2 max 4, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 1.3 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d` | fail | low | HPA app-d-prod/app-d: share of 15 days at min 1.00, min 2 max 5, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.8 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d-mx` | fail | low | HPA app-d-prod/app-d-mx: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.8 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d-vn` | fail | low | HPA app-d-prod/app-d-vn: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.8 days ago |
| `scaling.hpa-never-scaled.app-g-prod/deployment/app-g` | fail | low | HPA app-g-prod/app-g: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 60%, metrics ['cpu', 'memory'], last scale 7.8 days ago |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 10, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 10, apps whose targetRevision is a branch or HEAD 10 ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-c', 'argocd/application/app-d-kr', 'argocd/application/app-d-mx', 'argocd/application/app-d-shared', 'argocd/application/app-d-vn' … |
| `certmanager.controller-errors.cluster` | warn | low | sync calls since controller start 2454 / errors 233, ACME requests 117 by status {'200': 105, '201': 7, '400': 5} (4xx/5xx 5, ratio 0.0427), Ready False metric 0 |
| `certmanager.version-old.cluster` | warn | low | cert-manager 1.14.4 (components {'controller': '1/1', 'cainjector': '1/1', 'webhook': '1/1'}), webhooks with Fail 2 / webhook replicas 1 |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.487, cluster IPv6 False, queries per second 30.92. The glibc resolver always asks A and AAAA as a pair |
| `cost.k3s-node-efficiency.cluster` | warn | low | 2 nodes, allocatable 18.0 cores, 7-day p95 actual use 0.89 cores (0.049), request total 6.51 cores (7.3x actual use). Would requests still fit without the largest node: False |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex` | warn | low | image ghcr.io/dexidp/dex:v2.43.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis` | warn | low | image public.ecr.aws/docker/library/redis:8.2.2-alpine (tag tag, imagePullPolicy Always, registry public.ecr.aws) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.app-d-prod/deployment/app-d-vn:db-migrate` | warn | low | image registry.acme.com/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673 (tag tag, imagePullPolicy Always, registry registry.acme.com) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.failed-pods-lingering.cluster` | warn | low | Failed pods 4 (prod 4), reasons {'Failed': 2, 'UnexpectedAdmissionError': 2}, namespaces {'app-a-prod': 2, 'app-f-prod': 2}, oldest 3849.4h. Example: ['app-a-prod/app-u', 'app-a-prod/app-a-experiment', 'app-f-prod/app-f-embed-67f6f74f6c-rlm8m', 'app-f-prod/app-f-embed-67f6f74f6c-b6kdt'] |
| `hygiene.no-ephemeral-storage-requests.cluster` | warn | low | Containers with an ephemeral-storage request 0 of 126 (0.0), without one in prod 63. emptyDirs without sizeLimit 11 (prod: []) |
| `hygiene.old-replicasets.cluster` | warn | low | Of 292 ReplicaSets, 235 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 54, '0': 3, '3': 1, '2': 1} |
| `hygiene.orphan-secrets.cluster` | warn | low | Of 139 Secrets (metric kube_secret_info), 9 unreferenced candidates: [('argocd', 'ghcr-auth-secret', 'kubernetes.io/dockerconfigjson'), ('argocd', 'ghcr-pull-secret', 'kubernetes.io/dockerconfigjson'), ('default', 'app-d-prod-tls', 'kubernetes.io/tls'), ('default', 'app-z-auth-secret', 'Opaque') … |
| `hygiene.unused-crds.cluster` | warn | low | 42 of 64 CRDs have zero objects (by group {'generators.external-secrets.io': 17, 'monitoring.coreos.com': 6, 'metallb.io': 5, 'acme.cert-manager.io': 1, 'eventing.keda.sh': 2, 'external-secrets.io': 4, 'keda.sh': 4, 'helm.cattle.io': 2, 'actions.summerwind.dev': 1}), 28 webhooks |
| `keda.unused.cluster` | warn | low | KEDA v2.19.0 operator 1/1, metrics-apiserver 1/1, webhooks 1/1 — ScaledObject 0, ScaledJob 0 |
| `logs.signatures.cert-manager.orphan-tls-secret` | warn | low | 64 occurrences (2026-11-04T15:18:56Z ~ 2026-11-05T00:57:19Z), thresholds warn 1/fail 1000. Files: ['logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log']. Samples: ['[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553816246Z E1104 … |
| `logs.signatures.metallb.speaker-peer-unreachable` | warn | low | 482 occurrences (2026-11-05T04:42:34Z ~ 2026-11-05T08:02:35Z), thresholds warn 60/fail 2000. Files: ['logs/pods/metallb/metallb-system_speaker.log']. Samples: ['[pod/speaker-lqmcg/speaker] 2026-11-05T04:42:34.862388956Z {"caller":"speakerlist.go:259","error":"1 error occurred:\\n\\t* Failed to join … |
| `observability.alerts-never-fired.cluster` | warn | low | 135 of 145 rules did not fire in 15 days (['AppAClusterCPU50', 'AppAClusterCPU80', 'AppAClusterMem50', 'AppAClusterMem80', 'AppAFrontendDown', 'AppAGatewayDown', 'AppAGatewayErrorRateHigh', 'AppAGatewayHighCost', 'AppAGatewayUpstreamRejecting' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 28 of 29 ingress backends have no saturation metric (e.g. [('app-a-prod', 'app-a-backend'), ('app-a-prod', 'app-a-frontend'), ('app-a-prod', 'app-a-phoenix'), ('app-a-prod', 'app-a-umami'), ('argocd', 'argocd-server-ingress'), ('app-b-prod' … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('discord', None), ('null', ['severity=~"info\|none"'])], receivers ['null', 'discord'], default receiver discord |
| `observability.unclassified-errors.cluster` | warn | low | 41 unclassified error lines (20697 lines scanned, 21 files). Top: [('cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certific', 2), ('cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certific', 2), ('cert-manager … |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-a' … |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'redis-cli ping', 'port': None … |
| `resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-c', 'port' … |
| `resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-mx:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-vn:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-d-prod/statefulset/app-d-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-d-prod/statefulset/app-d-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'redis-cli ping', 'port': None … |
| `resilience.exec-probe.app-e-api/statefulset/app-e-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'mysqladmin ping -h localhost' … |
| `resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true \| … |
| `resilience.exec-probe.app-g-prod/statefulset/app-g-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-h/deployment/app-h-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app_h -d … |
| `resilience.exec-probe.app-i-prod/deployment/app-i-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-i -d … |
| `resilience.finished-jobs-accumulating.cluster` | warn | low | 58 Jobs (3 failed), 56 finished Jobs without ttl, 53 Succeeded pods, 4 Failed pods |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 15}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-gateway:gateway` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8080, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 5}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-phoenix:phoenix` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 6006, 'timeout_s': 1, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 40}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-umami:umami` | warn | low | ['liveness and readiness share the same path (/api/heartbeat) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/api/heartbeat', 'port': 3000, 'timeout_s': 1, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.app-b-prod/deployment/app-b-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-b-prod/deployment/app-b-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-c-prod/deployment/app-c-signaling:app` | warn | low | ['liveness and readiness share the same path (/ws/socket.io/?EIO=4&transport=polling) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/ws/socket.io/?EIO=4&transport=polling', 'port': 3001, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3 … |
| `resilience.liveness-dependency-path.app-c-prod/deployment/app-c-web:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-d-prod/deployment/app-d-admin:app` | warn | low | ['liveness and readiness share the same path (/login) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/login', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 15}, readiness {'type': 'httpGet', 'path': '/login', 'port' … |
| `resilience.liveness-dependency-path.app-d-prod/deployment/app-d-mx:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-d-prod/deployment/app-d-vn:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-d-prod/deployment/app-d:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-admin:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-api-server:app` | warn | low | ['liveness and readiness share the same path (/healthcheck) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthcheck', 'port': 8080, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 5, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-x-client:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-embed:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-excel-agent:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8080, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-w:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-g-prod/deployment/app-g:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-i-prod/deployment/app-i-api:api` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8080, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-i-prod/deployment/app-i-web:web` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.no-prestop.app-a-prod/app-a-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-gateway` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-phoenix` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-umami` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-b-prod/app-b-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-b-prod/app-b-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-c-prod/app-c-signaling` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-c-prod/app-c-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-d-prod/app-d` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-d-prod/app-d-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-d-prod/app-d-mx` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-d-prod/app-d-vn` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-app-x-client` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-embed` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-excel-agent` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-app-w` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-g-prod/app-g` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-i-prod/app-i-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-i-prod/app-i-postgres` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-i-prod/app-i-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resources.memory-request-overprovisioned.app-c-prod/sts/app-c-postgres:postgres` | warn | low | pod app-c-postgres-0: 7d memory working set p95 52 MB / request 256 MB = 0.20; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-f-prod/deploy/app-f-embed:app` | warn | low | pod app-f-embed-67f6f74f6c-lb7lj: 7d memory working set p95 638 MB / request 2048 MB = 0.31 |
| `resources.memory-request-overprovisioned.app-f-prod/sts/app-f-qdrant:qdrant` | warn | low | pod app-f-qdrant-0: 7d memory working set p95 49 MB / request 256 MB = 0.19; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-i-prod/deploy/app-i-postgres:postgres` | warn | low | pod app-i-postgres-76b69b654d-lzf4d: 7d memory working set p95 65 MB / request 256 MB = 0.25; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: metrics ['cpu'], current CPU 3% / target 70% |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: metrics ['cpu'], current CPU 2% / target 70% |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 3.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 4.0 desired changes over 7 days |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-gateway` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-phoenix` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-umami` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-signaling` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-f-prod/app-f-embed` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-f-prod/app-f-excel-agent` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-i-prod/app-i-api` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-i-prod/app-i-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller` | warn | low | Service ingress-nginx/nginx-ingress-ingress-nginx-controller: externalTrafficPolicy Local, ports [80, 443], addresses ['<ip>'] |
| `traffic.metallb-single-lb-service.cluster` | warn | low | mode layer2, 1 LoadBalancer services, pool used 1/10, leader node-b (1.0), pinned by nodeSelectors False, 2 nodes |

표의 근거는 칸에 맞게 줄였어요. 판정에 쓴 자료 전체는 아래에 항목별로 접혀 있고, `findings-draft.json`의 `details`와 같아요.

<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "pools_short": [
  {
   "eligible_nodes": [],
   "pods": 19,
   "needed_cpu": 1.49,
   "free_cpu": 0,
   "needed_memory_gb": 7.41,
   "free_memory_gb": 0.0
  }
 ],
 "allocatable_memory_gb_without_largest": 30.7,
 "largest_node": "node-b",
 "karpenter": false,
 "tight": false,
 "largest_node_memory_gb": 30.7,
 "allocatable_cpu_without_largest": 6.0,
 "memory_ok": true,
 "largest_node_cpu": 12.0,
 "available": true,
 "cpu_ok": false,
 "pods_on_largest_node": 48,
 "prod_pods_on_largest_node": 15,
 "requests_memory_gb_total": 23.9,
 "cannot_fit_elsewhere": [
  {
   "namespace": "app-a-prod",
   "pod": "app-a-postgres-0",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 0.5,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-a-redis-0",
   "node": "node-b",
   "cpu": 0.02,
   "memory_gb": 0.03,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-c-prod",
   "pod": "app-c-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.25,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-postgres-mx-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-postgres-vn-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-redis-0",
   "node": "node-b",
   "cpu": 0.02,
   "memory_gb": 0.03,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-e-api",
   "pod": "app-e-minio-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-e-api",
   "pod": "app-e-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-f-prod",
   "pod": "app-f-mysql-0",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 1.56,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "logging",
   "pod": "elasticsearch-0",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 2.0,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "logging",
   "pod": "kibana-59c97cdf75-ht2zf",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 0.5,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-g-prod",
   "pod": "app-g-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.09,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "monitoring",
   "pod": "alertmanager-kube-prometheus-stack-alertmanager-0",
   "node": "node-b",
   "cpu": 0.0,
   "memory_gb": 0.2,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "monitoring",
   "pod": "kube-prometheus-stack-grafana-74c84c99-g4grd",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.5,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "monitoring",
   "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
   "node": "node-b",
   "cpu": 0.0,
   "memory_gb": 0.0,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "monitoring",
   "pod": "kube-prometheus-stack-operator-74656dd4f5-5fmv5",
   "node": "node-b",
   "cpu": 0.0,
   "memory_gb": 0.0,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "monitoring",
   "pod": "prometheus-kube-prometheus-stack-prometheus-0",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 1.0,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "registry",
   "pod": "registry-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  }
 ],
 "ok": false,
 "autoscaler": false,
 "requests_cpu_total": 6.17
}
```

</details>
<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "alerting": 161,
 "by_class": {
  "cause": 153,
  "app-cause": 1,
  "app": 7
 },
 "symptom_ratio": 0.0,
 "symptom_rules": []
}
```

</details>
<details><summary><code>argocd.prune-manages-namespace-or-crd.cluster</code></summary>

```json
{
 "prune_with_namespace_or_crd": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/acme-site",
  "argocd/application/app-e-api",
  "argocd/application/app-h",
  "argocd/application/app-k",
  "argocd/application/app-i-prod"
 ],
 "applications_prod": 10
}
```

</details>
<details><summary><code>coredns.availability.cluster</code></summary>

```json
{
 "nodes_total": 2,
 "replicas": 1,
 "single_replica": true,
 "restarts_total": 1,
 "spread_declared": true,
 "nodes_with_pods": 1,
 "pdb": [],
 "pods_by_node": {
  "node-b": 1
 }
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.BackOff</code></summary>

```json
{
 "events": 4,
 "trend": "up",
 "reason": "BackOff",
 "per_snapshot": [
  124477,
  124589,
  124978,
  125226,
  125317,
  126950,
  127112,
  127228,
  128098,
  128331,
  800,
  938,
  1096,
  1165,
  1210,
  1717,
  1926,
  1994,
  2246,
  2292,
  2359,
  2566,
  2613,
  3508,
  3783,
  4055,
  6386,
  6640,
  6663,
  6960,
  6983,
  7166,
  7166,
  7371,
  7416,
  7509,
  7759,
  13779,
  13916,
  15826,
  43863,
  44324,
  44877,
  48970,
  49085
 ],
 "type": "Warning",
 "occurrences": 193081,
 "last": "2026-11-05T08:21:42Z",
 "severity_hint": "high",
 "first": "2026-10-05T18:39:29Z",
 "objects_top": [
  {
   "object": "Pod/app-c-prod/app-c-coturn-549854dfcb-jgp4h",
   "occurrences": 193078
  },
  {
   "object": "Pod/app-i-prod/app-i-api-7867899bb6-5xzqb",
   "occurrences": 3
  }
 ],
 "meaning": "Container keeps dying and the restart interval grows (CrashLoopBackOff)"
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
<details><summary><code>observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "namespace": "monitoring",
 "name": "alertmanager-kube-prometheus-stack-alertmanager",
 "kind": "StatefulSet"
}
```

</details>
<details><summary><code>observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "namespace": "monitoring",
 "name": "kube-prometheus-stack-grafana",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "namespace": "monitoring",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "kind": "StatefulSet"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-d-prod/statefulset/app-d-postgres",
   "pvc": "app-d-postgres-data-app-d-postgres-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-mx",
   "pvc": "app-d-postgres-mx-data-app-d-postgres-mx-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-vn",
   "pvc": "app-d-postgres-vn-data-app-d-postgres-vn-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-redis",
   "pvc": "app-d-redis-data-app-d-redis-0",
   "node": "node-b"
  }
 ],
 "schedule": "30 3 * * *",
 "target": "app-d-prod/app-d-postgres-backup",
 "offsite_hint": false,
 "dest_nodes": [
  "node-b"
 ],
 "suspend": false,
 "prod": true,
 "same_node_as_source": true,
 "dest_pvcs": [
  "app-d-postgres-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-d-prod/statefulset/app-d-postgres",
   "pvc": "app-d-postgres-data-app-d-postgres-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-mx",
   "pvc": "app-d-postgres-mx-data-app-d-postgres-mx-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-vn",
   "pvc": "app-d-postgres-vn-data-app-d-postgres-vn-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-redis",
   "pvc": "app-d-redis-data-app-d-redis-0",
   "node": "node-b"
  }
 ],
 "schedule": "30 3 * * *",
 "target": "app-d-prod/app-d-postgres-vn-backup",
 "offsite_hint": false,
 "dest_nodes": [
  "node-b"
 ],
 "suspend": false,
 "prod": true,
 "same_node_as_source": true,
 "dest_pvcs": [
  "app-d-postgres-vn-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-f-prod/app-f-mysql-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-f-prod/statefulset/app-f-mysql",
   "pvc": "mysql-backup-app-f-mysql-0",
   "node": "node-b"
  },
  {
   "workload": "app-f-prod/statefulset/app-f-mysql",
   "pvc": "mysql-data-app-f-mysql-0",
   "node": "node-b"
  },
  {
   "workload": "app-f-prod/statefulset/app-f-qdrant",
   "pvc": "app-f-qdrant-data-app-f-qdrant-0",
   "node": "node-a"
  }
 ],
 "schedule": "50 2 * * *",
 "target": "app-f-prod/app-f-mysql-backup",
 "offsite_hint": false,
 "dest_nodes": [
  "node-b"
 ],
 "suspend": false,
 "prod": true,
 "same_node_as_source": true,
 "dest_pvcs": [
  "mysql-backup-app-f-mysql-0"
 ]
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-g-prod/app-g-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-g-prod/statefulset/app-g-postgres",
   "pvc": "app-g-postgres-data-app-g-postgres-0",
   "node": "node-b"
  }
 ],
 "schedule": "0 3 * * *",
 "target": "app-g-prod/app-g-postgres-backup",
 "offsite_hint": false,
 "dest_nodes": [
  "node-b"
 ],
 "suspend": false,
 "prod": true,
 "same_node_as_source": true,
 "dest_pvcs": [
  "app-g-postgres-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-d-prod/deployment/app-d</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": true,
 "all_same_node": true,
 "eligible_nodes": 1,
 "prod": true,
 "nodes": {
  "node-a": 2
 },
 "workload": "app-d-prod/deployment/app-d"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "zones": {
  "null": 3
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "replicas": 3,
 "running": 3,
 "anti_affinity": null,
 "single_eligible_node": true,
 "all_same_node": true,
 "eligible_nodes": 1,
 "prod": true,
 "nodes": {
  "node-a": 3
 },
 "workload": "app-f-prod/deployment/app-f-admin"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server</code></summary>

```json
{
 "zones": {
  "null": 3
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "replicas": 3,
 "running": 3,
 "anti_affinity": null,
 "single_eligible_node": true,
 "all_same_node": true,
 "eligible_nodes": 1,
 "prod": true,
 "nodes": {
  "node-a": 3
 },
 "workload": "app-f-prod/deployment/app-f-api-server"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": true,
 "all_same_node": true,
 "eligible_nodes": 1,
 "prod": true,
 "nodes": {
  "node-a": 2
 },
 "workload": "app-f-prod/deployment/app-f-app-x-client"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn</code></summary>

```json
{
 "pod": "app-c-coturn-549854dfcb-jgp4h",
 "crashloop": true,
 "restarts": 10710,
 "namespace": "app-c-prod",
 "cause": "crash (exit 255)",
 "last_finished": "2026-11-05T07:58:00Z",
 "unhealthy_events": 0,
 "node_rebooted_at": null,
 "waiting": "CrashLoopBackOff",
 "exit_code": 255,
 "rebooted": false,
 "container": "coturn",
 "last_reason": "Error"
}
```

</details>
<details><summary><code>resources.memory-limit-near-p95.app-e-api/sts/app-e-minio:minio</code></summary>

```json
{
 "labels": {
  "container": "minio",
  "namespace": "app-e-api",
  "pod": "app-e-minio-0"
 },
 "value": 0.9820388793945312
}
```

</details>
<details><summary><code>security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts</code></summary>

```json
{
 "mounted_by": [
  "app-a-prod/cronjob/app-v-autopost-en",
  "app-a-prod/cronjob/app-v-autopost-ja",
  "app-a-prod/cronjob/app-v-digest-day",
  "app-a-prod/cronjob/app-v-digest-month",
  "app-a-prod/cronjob/app-v-digest-week",
  "app-a-prod/cronjob/app-v-radar-global"
 ],
 "keys": [
  "discord_sales_bot.py:TOKEN",
  "discord_sales_bot.py:OPENAI_API_KEY",
  "app-v_autopost.py:client_secret",
  "app-v_autopost.py:resource_owner_secret"
 ],
 "prod": true,
 "target": "app-a-prod/configmap/app-v-scripts"
}
```

</details>
<details><summary><code>security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts</code></summary>

```json
{
 "mounted_by": [
  "app-d-prod/cronjob/app-d-ga4-digest-day",
  "app-d-prod/cronjob/app-d-ga4-digest-month",
  "app-d-prod/cronjob/app-d-ga4-digest-week",
  "app-d-prod/cronjob/app-d-policy-radar",
  "app-d-prod/deployment/app-d-sales-bot"
 ],
 "keys": [
  "app-d_ga4_digest.py:DISCORD_BOT_TOKEN",
  "app-d_ga4_digest.py:token",
  "app-d_policy_radar.py:OPENAI_API_KEY",
  "app-d_policy_radar.py:DISCORD_BOT_TOKEN",
  "app-d_sales_bot.py:TOKEN",
  "app-d_sales_bot.py:OPENAI_API_KEY"
 ],
 "prod": true,
 "target": "app-d-prod/configmap/app-d-app-v-scripts"
}
```

</details>
<details><summary><code>tenancy.quota-near-limit.app-i-prod/app-i-prod-quota</code></summary>

```json
{
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "30Gi"
 },
 "target": "app-i-prod/app-i-prod-quota",
 "max_ratio": 1.0,
 "near_limit": [
  "persistentvolumeclaims"
 ],
 "used": {
  "limits.cpu": "1800m",
  "limits.memory": "2Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "200m",
  "requests.memory": "512Mi",
  "requests.storage": "20Gi"
 }
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external</code></summary>

```json
{
 "namespace": "app-d-prod",
 "target": "nodeport/app-d-prod/app-d-postgres-external",
 "source_ranges": null,
 "hosts": [],
 "type": "nodeport",
 "sg_exposure": null,
 "ports": [
  5432
 ],
 "allowed_sources": {},
 "scheme": "node-ip (all node interfaces)",
 "name": "app-d-postgres-external",
 "note": "DB port open on an external address"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external</code></summary>

```json
{
 "namespace": "app-d-prod",
 "target": "nodeport/app-d-prod/app-d-postgres-mx-external",
 "source_ranges": null,
 "hosts": [],
 "type": "nodeport",
 "sg_exposure": null,
 "ports": [
  5432
 ],
 "allowed_sources": {},
 "scheme": "node-ip (all node interfaces)",
 "name": "app-d-postgres-mx-external",
 "note": "DB port open on an external address"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external</code></summary>

```json
{
 "namespace": "app-d-prod",
 "target": "nodeport/app-d-prod/app-d-postgres-vn-external",
 "source_ranges": null,
 "hosts": [],
 "type": "nodeport",
 "sg_exposure": null,
 "ports": [
  5432
 ],
 "allowed_sources": {},
 "scheme": "node-ip (all node interfaces)",
 "name": "app-d-postgres-vn-external",
 "note": "DB port open on an external address"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external</code></summary>

```json
{
 "namespace": "app-g-prod",
 "target": "nodeport/app-g-prod/app-g-postgres-external",
 "source_ranges": null,
 "hosts": [],
 "type": "nodeport",
 "sg_exposure": null,
 "ports": [
  5432
 ],
 "allowed_sources": {},
 "scheme": "node-ip (all node interfaces)",
 "name": "app-g-postgres-external",
 "note": "DB port open on an external address"
}
```

</details>
<details><summary><code>controlplane.apiserver-5xx.cluster</code></summary>

```json
{
 "labels": {
  "code": "503"
 },
 "value": 0.007407407407407408
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.Unhealthy</code></summary>

```json
{
 "events": 28,
 "trend": "flat",
 "reason": "Unhealthy",
 "per_snapshot": [
  0,
  0,
  0,
  0,
  7,
  0,
  0,
  8,
  0,
  33,
  0,
  0,
  5,
  6,
  6,
  0,
  7,
  7,
  9,
  9,
  9,
  0,
  0,
  12,
  16,
  0,
  27,
  28,
  30,
  31,
  31,
  32,
  32,
  33,
  33,
  33,
  34,
  62,
  62,
  74,
  0,
  0,
  0,
  7,
  7
 ],
 "type": "Warning",
 "occurrences": 265,
 "last": "2026-11-05T07:53:09Z",
 "severity_hint": "medium",
 "first": "2026-10-21T02:04:50Z",
 "objects_top": [
  {
   "object": "Pod/argocd/argocd-repo-server-848dcbb4db-jz8xs",
   "occurrences": 207
  },
  {
   "object": "Pod/app-e-api/app-e-postgres-0",
   "occurrences": 24
  },
  {
   "object": "Pod/app-a-prod/app-a-backend-79c97cbbd6-2t8rj",
   "occurrences": 5
  },
  {
   "object": "Pod/app-a-prod/app-a-backend-79c97cbbd6-cvldp",
   "occurrences": 5
  },
  {
   "object": "Pod/app-d-prod/app-d-vn-worker-76bdf4cc86-cj7bp",
   "occurrences": 4
  }
 ],
 "meaning": "Probe failure. Readiness removes it from traffic, liveness restarts it"
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
 "value": 0.7723992380275929
}
```

</details>
<details><summary><code>prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "pvc_used_ratio": null,
 "wal_corruptions": 0,
 "retention_shortfall": false,
 "oldest_sample_days": 30.8,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "compactions_failed_7d": 0,
 "storage": "emptyDir",
 "pvc_size": null,
 "present": true,
 "tsdb_bytes": 22888066609.0,
 "retention_time": "30d",
 "retention_size": "0B",
 "corruption_count": 0
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-a-prod/app-a-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-a-prod/statefulset/app-a-postgres",
   "pvc": "data-app-a-postgres-0",
   "node": "node-b"
  },
  {
   "workload": "app-a-prod/statefulset/app-a-redis",
   "pvc": "data-app-a-redis-0",
   "node": "node-b"
  }
 ],
 "schedule": "15 3 * * *",
 "target": "app-a-prod/app-a-postgres-backup",
 "dest_nodes": [
  "node-a"
 ],
 "offsite_hint": false,
 "suspend": false,
 "same_node_as_source": false,
 "local_only": true,
 "dest_pvcs": [
  "app-a-postgres-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-d-prod/statefulset/app-d-postgres",
   "pvc": "app-d-postgres-data-app-d-postgres-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-mx",
   "pvc": "app-d-postgres-mx-data-app-d-postgres-mx-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-vn",
   "pvc": "app-d-postgres-vn-data-app-d-postgres-vn-0",
   "node": "node-b"
  },
  {
   "workload": "app-d-prod/statefulset/app-d-redis",
   "pvc": "app-d-redis-data-app-d-redis-0",
   "node": "node-b"
  }
 ],
 "schedule": "30 3 * * *",
 "target": "app-d-prod/app-d-postgres-mx-backup",
 "dest_nodes": [
  "node-a"
 ],
 "offsite_hint": false,
 "suspend": false,
 "same_node_as_source": false,
 "local_only": true,
 "dest_pvcs": [
  "app-d-postgres-mx-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-e-api/app-e-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "source_db": [
  {
   "workload": "app-e-api/statefulset/app-e-minio",
   "pvc": "app-e-minio-data-app-e-minio-0",
   "node": "node-b"
  },
  {
   "workload": "app-e-api/statefulset/app-e-postgres",
   "pvc": "app-e-postgres-data-app-e-postgres-0",
   "node": "node-b"
  }
 ],
 "schedule": "50 3 * * *",
 "target": "app-e-api/app-e-postgres-backup",
 "offsite_hint": false,
 "dest_nodes": [
  "node-b"
 ],
 "suspend": false,
 "prod": false,
 "same_node_as_source": true,
 "local_only": true,
 "dest_pvcs": [
  "app-e-postgres-backup-pvc"
 ]
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": false,
 "all_same_node": false,
 "spread_declared": false,
 "eligible_nodes": 2,
 "prod": true,
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "workload": "app-a-prod/deployment/app-a-backend"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": false,
 "all_same_node": false,
 "spread_declared": false,
 "eligible_nodes": 2,
 "prod": true,
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "workload": "app-a-prod/deployment/app-a-frontend"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": false,
 "all_same_node": false,
 "spread_declared": false,
 "eligible_nodes": 2,
 "prod": true,
 "nodes": {
  "node-a": 1,
  "node-b": 1
 },
 "workload": "app-a-prod/deployment/app-a-gateway"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "zones": {
  "null": 2
 },
 "topology_spread": [],
 "replicas": 2,
 "running": 2,
 "anti_affinity": null,
 "single_eligible_node": false,
 "all_same_node": true,
 "eligible_nodes": 2,
 "prod": false,
 "nodes": {
  "node-b": 2
 },
 "workload": "ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller</code></summary>

```json
{
 "pod": "cert-manager-7c4b5b58df-4v7td",
 "crashloop": false,
 "restarts": 12,
 "namespace": "cert-manager",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z",
 "unhealthy_events": 0,
 "node_rebooted_at": null,
 "waiting": null,
 "exit_code": 255,
 "rebooted": false,
 "container": "cert-manager-controller",
 "last_reason": "Unknown"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-cainjector-7bf5c557bb-kbtv7:cert-manager-cainjector</code></summary>

```json
{
 "pod": "cert-manager-cainjector-7bf5c557bb-kbtv7",
 "crashloop": false,
 "restarts": 14,
 "namespace": "cert-manager",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z",
 "unhealthy_events": 0,
 "node_rebooted_at": null,
 "waiting": null,
 "exit_code": 255,
 "rebooted": false,
 "container": "cert-manager-cainjector",
 "last_reason": "Unknown"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator</code></summary>

```json
{
 "pod": "keda-operator-85ff5bb446-lwkl6",
 "crashloop": false,
 "restarts": 10,
 "namespace": "keda",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z",
 "unhealthy_events": 0,
 "node_rebooted_at": null,
 "waiting": null,
 "exit_code": 255,
 "rebooted": false,
 "container": "keda-operator",
 "last_reason": "Unknown"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "workload": "app-a-prod/statefulset/app-a-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "workload": "app-a-prod/statefulset/app-a-redis"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": false,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [
  "hostNetwork"
 ],
 "workload": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-signaling</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-c-prod/deployment/app-c-signaling"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-web</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-c-prod/deployment/app-c-web"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate postgres-data"
 ],
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 2,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-admin</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-admin"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-mx</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-mx"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-mx-worker</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": false,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-mx-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-vn</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-vn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-vn-worker</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": false,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-vn-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-worker</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": false,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-d-prod/deployment/app-d-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-data"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-mx</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-mx-data"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres-mx"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-vn</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-vn-data"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres-vn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-redis</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-redis-data"
 ],
 "workload": "app-d-prod/statefulset/app-d-redis"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-e-api/statefulset/app-e-minio</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-e-minio-data"
 ],
 "workload": "app-e-api/statefulset/app-e-minio"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-e-api/statefulset/app-e-postgres</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-e-postgres-data"
 ],
 "workload": "app-e-api/statefulset/app-e-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 3,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-f-prod/deployment/app-f-admin"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-api-server</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 3,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-f-prod/deployment/app-f-api-server"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-app-x-client</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 2,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-f-prod/deployment/app-f-app-x-client"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-embed</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [
  "extended resource nvidia.com/gpu"
 ],
 "workload": "app-f-prod/deployment/app-f-embed"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-excel-agent</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-f-prod/deployment/app-f-excel-agent"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-app-w</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-f-prod/deployment/app-f-app-w"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-mysql</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate mysql-backup",
  "local-path volumeClaimTemplate mysql-data"
 ],
 "workload": "app-f-prod/statefulset/app-f-mysql"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-qdrant</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-qdrant-data"
 ],
 "workload": "app-f-prod/statefulset/app-f-qdrant"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/deployment/kibana</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "logging/deployment/kibana"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/statefulset/elasticsearch</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "workload": "logging/statefulset/elasticsearch"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-prod/deployment/app-g</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "prod": true,
 "pin_reasons": [],
 "workload": "app-g-prod/deployment/app-g"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-prod/statefulset/app-g-postgres</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": true,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-g-postgres-data"
 ],
 "workload": "app-g-prod/statefulset/app-g-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "monitoring/deployment/kube-prometheus-stack-kube-state-metrics"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "monitoring/deployment/kube-prometheus-stack-operator"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [],
 "workload": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.registry/statefulset/registry</code></summary>

```json
{
 "nodes_total": 2,
 "serves_traffic": true,
 "replicas": 1,
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "prod": false,
 "pin_reasons": [
  "local-path volumeClaimTemplate registry-data"
 ],
 "workload": "registry/statefulset/registry"
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-e-api/sts/app-e-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-e-api",
  "pod": "app-e-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_throttle_ratio_5m": 0.455
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit</code></summary>

```json
[
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-c7fr8",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_5m": 0.2878473662380755
  }
 },
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-nnsb5",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_5m": 0.2837528604118993
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch</code></summary>

```json
{
 "labels": {
  "namespace": "logging",
  "pod": "elasticsearch-0",
  "container": "elasticsearch"
 },
 "values": {
  "cpu_throttle_ratio_5m": 0.4264990328820116
 }
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
  "cpu_throttle_ratio_5m": 0.5605599513085818
 }
}
```

</details>
<details><summary><code>resources.memory-limit-near-p95.logging/ds/fluent-bit:fluent-bit</code></summary>

```json
[
 {
  "labels": {
   "container": "fluent-bit",
   "namespace": "logging",
   "pod": "fluent-bit-c7fr8"
  },
  "value": 0.8412124633789062
 },
 {
  "labels": {
   "container": "fluent-bit",
   "namespace": "logging",
   "pod": "fluent-bit-nnsb5"
  },
  "value": 0.8228927612304686
 }
]
```

</details>
<details><summary><code>security.plaintext-configmap-secret.default/configmap/app-y-backend-config</code></summary>

```json
{
 "mounted_by": [],
 "keys": [
  "JWT_RELAY_SECRET",
  "JWT_SECRET",
  "TWITTER_CLIENT_SECRET",
  "TWITTER_CLIENT_SECRET_RELAY"
 ],
 "prod": false,
 "target": "default/configmap/app-y-backend-config"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/cronjob/es-index-retention:retention</code></summary>

```json
{
 "container": "retention",
 "prod": false,
 "env_names": [
  "ELASTIC_PASSWORD"
 ],
 "workload": "logging/cronjob/es-index-retention"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/deployment/kibana:kibana</code></summary>

```json
{
 "container": "kibana",
 "prod": false,
 "env_names": [
  "ELASTICSEARCH_PASSWORD"
 ],
 "workload": "logging/deployment/kibana"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "container": "elasticsearch",
 "prod": false,
 "env_names": [
  "ELASTIC_PASSWORD"
 ],
 "workload": "logging/statefulset/elasticsearch"
}
```

</details>
<details><summary><code>security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "host_access": true,
 "root_allowed_containers": [
  "coturn"
 ],
 "workload": "app-c-prod/deployment/app-c-coturn",
 "system": false,
 "severe": false,
 "flags": [
  "hostNetwork"
 ]
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-a</code></summary>

```json
{
 "cpu_saturated_minutes_7d": 0.0,
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "prod_pods": 32,
 "ci_pods": 1,
 "ci_heavy": true,
 "separation_possible": false,
 "node": "node-a",
 "pool": "(no-pool)",
 "shares_ci_prod": true,
 "memory_limit_overcommit": 1.04,
 "ci_pod_list": [
  {
   "pod": "arc-actions-runner-controller-5c9d9ffd65-766b6",
   "namespace": "arc-systems",
   "owner_kind": "ReplicaSet",
   "cpu_request": 0.0,
   "heavy": true
  }
 ]
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-b</code></summary>

```json
{
 "cpu_saturated_minutes_7d": 0.0,
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "prod_pods": 15,
 "ci_pods": 2,
 "ci_heavy": true,
 "separation_possible": false,
 "node": "node-b",
 "pool": "(no-pool)",
 "shares_ci_prod": true,
 "memory_limit_overcommit": 0.99,
 "ci_pod_list": [
  {
   "pod": "ci-runner-8tt2w-2p2pg",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  },
  {
   "pod": "ci-runner-8tt2w-4w6rk",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  }
 ]
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota</code></summary>

```json
{
 "requires_requests": true,
 "hard": {
  "count/pods": "200",
  "limits.memory": "80Gi",
  "requests.memory": "60Gi"
 },
 "target": "app-a-prod/app-a-prod-quota",
 "containers_without_requests": 0,
 "has_limitrange": false,
 "limitrange_default_request": false
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota</code></summary>

```json
{
 "requires_requests": true,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "20Gi"
 },
 "target": "app-b-prod/app-b-prod-quota",
 "containers_without_requests": 0,
 "has_limitrange": false,
 "limitrange_default_request": false
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-i-prod/app-i-prod-quota</code></summary>

```json
{
 "requires_requests": true,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "30Gi"
 },
 "target": "app-i-prod/app-i-prod-quota",
 "containers_without_requests": 0,
 "has_limitrange": false,
 "limitrange_default_request": false
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "metrics_available": true,
 "qps_total": 30.92,
 "autopath": false,
 "upstreams": [
  "1.1.1.1:53",
  "8.8.8.8:53"
 ],
 "forward_nxdomain_ratio": 0.847,
 "pods_default_ndots": 153,
 "nxdomain_ratio": 0.696,
 "cache_hit_ratio": 0.8509
}
```

</details>
<details><summary><code>eso.store-static-credentials.cluster</code></summary>

```json
{
 "stores_static_key": [
  "ClusterSecretStore/aws-secret-store"
 ],
 "externalsecrets": 39,
 "stores_auth": {
  "ClusterSecretStore/aws-secret-store": "static-key(Secret)"
 },
 "externalsecrets_prod": 33,
 "providers": [
  "aws"
 ]
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "docker.io",
 "pull_policy": "IfNotPresent",
 "holder": false,
 "mutable": true,
 "image": "arizephoenix/phoenix:latest",
 "prod": true,
 "workload": "app-a-prod/deployment/app-a-phoenix",
 "container": "phoenix"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "docker.io",
 "pull_policy": "Always",
 "holder": false,
 "mutable": true,
 "image": "coturn/coturn:latest",
 "prod": true,
 "workload": "app-c-prod/deployment/app-c-coturn",
 "container": "coturn"
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/monitoring</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "prometheus",
  "instance": "<ip>:10250",
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "service": "kube-prometheus-stack-kubelet",
  "severity": "info"
 },
 "value": 73.09639540509217
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeCPUOvercommit</code></summary>

```json
{
 "labels": {
  "alertname": "KubeCPUOvercommit",
  "severity": "warning"
 },
 "value": 30.556117627314396
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeJobFailed/app-a-prod</code></summary>

```json
[
 {
  "labels": {
   "alertname": "KubeJobFailed",
   "condition": "true",
   "container": "kube-state-metrics",
   "endpoint": "http",
   "instance": "<ip>:8080",
   "job": "kube-state-metrics",
   "job_name": "app-a-sandbox-watchdog-29881700",
   "namespace": "app-a-prod",
   "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
   "service": "kube-prometheus-stack-kube-state-metrics",
   "severity": "warning"
  },
  "value": 11.150862997684765
 },
 {
  "labels": {
   "alertname": "KubeJobFailed",
   "condition": "true",
   "container": "kube-state-metrics",
   "endpoint": "http",
   "instance": "<ip>:8080",
   "job": "kube-state-metrics",
   "job_name": "app-a-sandbox-watchdog-29887083",
   "namespace": "app-a-prod",
   "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
   "service": "kube-prometheus-stack-kube-state-metrics",
   "severity": "warning"
  },
  "value": 7.412668553240321
 }
]
```

</details>
<details><summary><code>observability.alert-firing-stale.KubePodCrashLooping/app-c-prod</code></summary>

```json
{
 "labels": {
  "alertname": "KubePodCrashLooping",
  "container": "coturn",
  "endpoint": "http",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "app-c-prod",
  "pod": "app-c-coturn-549854dfcb-jgp4h",
  "reason": "CrashLoopBackOff",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "severity": "warning",
  "uid": "faf3240b-a897-45ce-8aa9-136f745cc344"
 },
 "value": 38.126904664351436
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeQuotaFullyUsed/app-i-prod</code></summary>

```json
{
 "labels": {
  "alertname": "KubeQuotaFullyUsed",
  "container": "kube-state-metrics",
  "endpoint": "http",
  "namespace": "app-i-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "resource": "persistentvolumeclaims",
  "resourcequota": "app-i-prod-quota",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "severity": "info"
 },
 "value": 127.36063151620328
}
```

</details>
<details><summary><code>observability.alerts-always-firing.CPUThrottlingHigh</code></summary>

```json
{
 "samples_7d": 86849.0,
 "alertname": "CPUThrottlingHigh"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeCPUOvercommit</code></summary>

```json
{
 "samples_7d": 20160.0,
 "alertname": "KubeCPUOvercommit"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeDeploymentReplicasMismatch</code></summary>

```json
{
 "samples_7d": 20098.0,
 "alertname": "KubeDeploymentReplicasMismatch"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeJobFailed</code></summary>

```json
{
 "samples_7d": 40320.0,
 "alertname": "KubeJobFailed"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubePodCrashLooping</code></summary>

```json
{
 "samples_7d": 20160.0,
 "alertname": "KubePodCrashLooping"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeQuotaFullyUsed</code></summary>

```json
{
 "samples_7d": 20160.0,
 "alertname": "KubeQuotaFullyUsed"
}
```

</details>
<details><summary><code>observability.ingress-controller-metrics-missing.ingress-controller</code></summary>

```json
{
 "ingress_controller_metric_series": 0,
 "missing_lte": [
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-backend",
   "class": "nginx",
   "hosts": [
    "api.app-a.acme.com",
    "api.example-a.dev"
   ],
   "services": [
    "app-a-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-frontend",
   "class": "nginx",
   "hosts": [
    "app-a.acme.com",
    "example-a.dev",
    "www.example-a.dev"
   ],
   "services": [
    "app-a-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-phoenix",
   "class": "nginx",
   "hosts": [
    "obs.example-a.dev"
   ],
   "services": [
    "app-a-phoenix"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-umami",
   "class": "nginx",
   "hosts": [
    "umami.example-a.dev",
    "umami.example-l.com"
   ],
   "services": [
    "app-a-umami"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "argocd",
   "ingress": "argocd-server-ingress",
   "class": "nginx",
   "hosts": [
    "argocd.acme.com"
   ],
   "services": [
    "argocd-server"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-b-prod",
   "ingress": "app-b-backend",
   "class": "nginx",
   "hosts": [
    "app-b-api.acme.com"
   ],
   "services": [
    "app-b-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-b-prod",
   "ingress": "app-b-frontend",
   "class": "nginx",
   "hosts": [
    "app-b.acme.com"
   ],
   "services": [
    "app-b-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-c-prod",
   "ingress": "app-c-signaling-ingress",
   "class": "nginx",
   "hosts": [
    "app-c.acme.com",
    "example-h.space",
    "www.example-h.space"
   ],
   "services": [
    "app-c-signaling-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-c-prod",
   "ingress": "app-c-web-ingress",
   "class": "nginx",
   "hosts": [
    "app-c.acme.com",
    "example-h.space",
    "www.example-h.space"
   ],
   "services": [
    "app-c-web-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "acme-site",
   "ingress": "acme-site",
   "class": "nginx",
   "hosts": [
    "acme.com"
   ],
   "services": [
    "acme-site"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-admin-ingress",
   "class": "nginx",
   "hosts": [
    "admin.example-e.com"
   ],
   "services": [
    "app-d-admin-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-ingress",
   "class": "nginx",
   "hosts": [
    "app.example-e.com"
   ],
   "services": [
    "app-d-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-mx-ingress",
   "class": "nginx",
   "hosts": [
    "mx.example-e.com"
   ],
   "services": [
    "app-d-mx-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-vn-ingress",
   "class": "nginx",
   "hosts": [
    "vn.example-e.com"
   ],
   "services": [
    "app-d-vn-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-e-api",
   "ingress": "app-e-api",
   "class": "nginx",
   "hosts": [
    "app-e-api.acme.com",
    "app-e-cdn.acme.com"
   ],
   "services": [
    "app-e-api",
    "app-e-minio"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-admin-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-admin-prod.acme.com",
    "example-f.com",
    "www.example-f.com"
   ],
   "services": [
    "app-f-admin-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-api-server-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-api-prod.acme.com"
   ],
   "services": [
    "app-f-api-server-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-api-server-oauth-ingress",
   "class": "nginx",
   "hosts": [
    "example-k.kr",
    "www.example-k.kr"
   ],
   "services": [
    "app-f-api-server-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-app-x-client-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-app-x-client-prod.acme.com",
    "example-k.kr",
    "www.example-k.kr"
   ],
   "services": [
    "app-f-app-x-client-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-app-w-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-app-w-prod.acme.com",
    "example-g.com",
    "www.example-g.com"
   ],
   "services": [
    "app-f-app-w-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "logging",
   "ingress": "kibana",
   "class": "nginx",
   "hosts": [
    "kibana.acme.com"
   ],
   "services": [
    "kibana"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-g-prod",
   "ingress": "app-g-ingress",
   "class": "nginx",
   "hosts": [
    "app-g.acme.com",
    "example-j.com",
    "www.example-j.com"
   ],
   "services": [
    "app-g-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "monitoring",
   "ingress": "monitoring-grafana-ingress",
   "class": "nginx",
   "hosts": [
    "grafana.acme.com"
   ],
   "services": [
    "kube-prometheus-stack-grafana"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": true,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-h",
   "ingress": "app-h",
   "class": "nginx",
   "hosts": [
    "app-h.acme.com"
   ],
   "services": [
    "app-h"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "registry",
   "ingress": "registry",
   "class": "nginx",
   "hosts": [
    "registry.acme.com"
   ],
   "services": [
    "registry"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-k",
   "ingress": "app-k",
   "class": "nginx",
   "hosts": [
    "app-k.acme.com"
   ],
   "services": [
    "app-k-workstation"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-k",
   "ingress": "app-k-auth",
   "class": "nginx",
   "hosts": [
    "app-k.acme.com"
   ],
   "services": [
    "app-k-workstation"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-i-prod",
   "ingress": "app-i-api",
   "class": "nginx",
   "hosts": [
    "api.example-i.dev"
   ],
   "services": [
    "app-i-api"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-i-prod",
   "ingress": "app-i-web",
   "class": "nginx",
   "hosts": [
    "example-i.dev"
   ],
   "services": [
    "app-i-web"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  }
 ],
 "alb_cloudwatch_available": false,
 "ingresses": 29,
 "namespaces_with_app_http_metrics": []
}
```

</details>
<details><summary><code>operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn</code></summary>

```json
{
 "namespace": "app-c-prod",
 "kind": "deployments",
 "reason": "MinimumReplicasUnavailable",
 "condition": "Available",
 "status": "False",
 "name": "app-c-coturn",
 "message": "Deployment does not have minimum availability.",
 "age_hours": 10.4
}
```

</details>
<details><summary><code>resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog</code></summary>

```json
{
 "stale": true,
 "schedule": "* * * * *",
 "target": "app-a-prod/app-a-sandbox-watchdog",
 "last_success": "2026-11-05T08:00:51Z",
 "suspend": false,
 "last_schedule": "2026-11-05T08:01:00Z",
 "active_jobs": 1,
 "interval_h": 0.016666666666666666,
 "hours_since_success": 9.2,
 "failed_jobs": [
  "app-a-sandbox-watchdog-29881700",
  "app-a-sandbox-watchdog-29887083"
 ]
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/statefulset/app-a-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/statefulset/app-a-redis",
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-mx:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-d-prod/statefulset/app-d-postgres-mx",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-vn:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-d-prod/statefulset/app-d-postgres-vn",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-d-prod/statefulset/app-d-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-redis:redis</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "startup": null,
 "workload": "app-d-prod/statefulset/app-d-redis",
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-mysql:mysql</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-qdrant:qdrant</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": "http",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/readyz",
  "port": "http",
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-qdrant",
 "container": "qdrant"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-g-prod/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
 "startup": null,
 "workload": "app-g-prod/statefulset/app-g-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-i-prod/deployment/app-i-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "startup": null,
 "workload": "app-i-prod/deployment/app-i-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "prod": true,
 "replicas": 1,
 "workload": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "prod": true,
 "replicas": 1,
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/deployment/app-f-embed</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "prod": true,
 "replicas": 1,
 "workload": "app-f-prod/deployment/app-f-embed"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/statefulset/app-f-mysql</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "prod": true,
 "replicas": 1,
 "workload": "app-f-prod/statefulset/app-f-mysql"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/statefulset/app-f-qdrant</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "prod": true,
 "replicas": 1,
 "workload": "app-f-prod/statefulset/app-f-qdrant"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-phoenix",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-a-prod/app-a-umami</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-umami",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-b-prod/app-b-backend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-b-prod/app-b-frontend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-c-prod/app-c-coturn</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-coturn",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-c-prod/app-c-signaling</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-signaling",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-c-prod/app-c-web</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-d-prod/app-d-mx-worker</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-mx-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-d-prod/app-d-vn-worker</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-vn-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-d-prod/app-d-worker</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-f-prod/app-f-embed</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-f-prod/app-f-excel-agent</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-i-prod/app-i-api</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-i-prod/app-i-postgres</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-postgres",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-i-prod/app-i-web</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-embed:app</code></summary>

```json
{
 "labels": {
  "namespace": "app-f-prod",
  "pod": "app-f-embed-67f6f74f6c-lb7lj",
  "container": "app"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.002762732754755539,
  "cpu_p95_7d_cores": 0.0013813663773777694,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-c-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-c-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 4,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": false,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-d-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-d-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 12,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": false,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-f-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-f-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 13,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": false,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-g-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-g-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 2,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": false,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>traffic.pod-not-ready.app-c-prod/app-c-coturn</code></summary>

```json
{
 "worst_pod": "app-c-coturn-549854dfcb-jgp4h",
 "min_ready_ratio_24h": 0.0,
 "unhealthy_events": 0,
 "not_ready_minutes_24h": 1440,
 "pods_below_99": 1,
 "prod": true,
 "workload": "app-c-prod/app-c-coturn"
}
```

</details>
<details><summary><code>argocd.admin-account-no-sso.cluster</code></summary>

```json
{
 "rbac_policy_default": "",
 "sso_configured": false,
 "rbac_policy_csv_lines": 0,
 "admin_enabled": true,
 "anonymous_enabled": false,
 "url": null,
 "exec_enabled": false
}
```

</details>
<details><summary><code>argocd.app-out-of-sync-or-unhealthy.cluster</code></summary>

```json
{
 "applications": 18,
 "out_of_sync": [
  "argocd/application/root"
 ],
 "unhealthy_prod": [],
 "apps_with_conditions": [
  "argocd/application/app-k"
 ],
 "conditions": [
  "ExcludedResourceWarning"
 ],
 "last_op_failed": [],
 "unhealthy": [],
 "out_of_sync_prod": [],
 "degraded": [],
 "progressing": [
  "argocd/application/app-c"
 ],
 "applications_prod": 10
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 18,
 "projects": 2,
 "wildcard_projects": [
  "default"
 ],
 "default_project_apps": 4,
 "applications_prod": 10
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.LIST</code></summary>

```json
{
 "labels": {
  "verb": "LIST"
 },
 "value": 0.8246406250000015
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.PUT</code></summary>

```json
{
 "labels": {
  "verb": "PUT"
 },
 "value": 0.7004615384615415
}
```

</details>
<details><summary><code>coredns.forward-upstream-errors.cluster</code></summary>

```json
{
 "max_concurrent_rejects_1h": 0.0,
 "metrics_available": true,
 "forward_healthcheck_failures_1h": 1.0084,
 "forward_servfail_1h": 0,
 "upstreams": [
  "1.1.1.1:53",
  "8.8.8.8:53"
 ],
 "forward_servfail_ratio": 0.0,
 "servfail_ratio": 0.0
}
```

</details>
<details><summary><code>eso.controller-single-replica.cluster</code></summary>

```json
{
 "webhook_replicas": 1,
 "concurrent": "1",
 "controller_replicas": 1,
 "webhook_ready": 1,
 "cert_controller_ready": 1,
 "cert_controller_replicas": 1,
 "controller_ready": 1,
 "webhook_fail_policy": [
  "validate.externalsecret.external-secrets.io",
  "validate.secretstore.external-secrets.io",
  "validate.clustersecretstore.external-secrets.io"
 ]
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-adk:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-adk"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-c:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-c"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-express:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-express"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-go:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-go"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-nestjs:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-nestjs"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-network:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-network"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-nextjs:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-nextjs"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-python:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-python"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-python-ml:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-python-ml"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-spring:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-spring"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-sql:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-sql"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "holder": true,
 "mutable": true,
 "image": "registry.acme.com/app-a-sandbox-todo:latest",
 "prod": true,
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "container": "hold-todo"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.registry/cronjob/registry-tag-cleanup:tag-cleanup</code></summary>

```json
{
 "tag_kind": "latest",
 "registry": "docker.io",
 "pull_policy": "Always",
 "mutable": true,
 "image": "curlimages/curl:latest",
 "prod": false,
 "workload": "registry/cronjob/registry-tag-cleanup",
 "container": "tag-cleanup"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.role</code></summary>

```json
{
 "prod_workloads": 0,
 "nodes_total": 2,
 "nodes_with_label": 1,
 "workload_count": 7,
 "well_known": false,
 "key": "role",
 "workloads": [
  "logging/deployment/kibana",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "monitoring/deployment/kube-prometheus-stack-kube-state-metrics",
  "monitoring/deployment/kube-prometheus-stack-operator",
  "logging/statefulset/elasticsearch",
  "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager",
  "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
 ]
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.storage</code></summary>

```json
{
 "prod_workloads": 7,
 "nodes_total": 2,
 "nodes_with_label": 1,
 "workload_count": 10,
 "well_known": false,
 "key": "storage",
 "workloads": [
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-d-prod/statefulset/app-d-postgres",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "app-d-prod/statefulset/app-d-redis",
  "app-e-api/statefulset/app-e-minio",
  "app-e-api/statefulset/app-e-postgres"
 ]
}
```

</details>
<details><summary><code>hygiene.pvc-unbound-or-unused.cluster</code></summary>

```json
{
 "pvc_unbound": [],
 "pvc_unused": [
  {
   "namespace": "default",
   "name": "data-app-z-db-0",
   "prod": false
  }
 ],
 "pv_released": []
}
```

</details>
<details><summary><code>logs.signatures.cert-manager.challenge-failed</code></summary>

```json
{
 "count": 10,
 "first": "2026-11-05T02:31:09Z",
 "last": "2026-11-05T03:35:40Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/cert-manager/cert-manager_cert-manager.log": 10
 },
 "samples": [
  "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.690144851Z E1105 02:31:09.689988       1 sync.go:190] \"propagation check failed\" err=\"wrong status code '404', expected '200'\" logger=\"cert-manager.challenges\" ",
  "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.731163600Z E1105 02:31:09.731031       1 sync.go:190] \"propagation check failed\" err=\"wrong status code '404', expected '200'\" logger=\"cert-manager.challenges\" ",
  "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:19.695743508Z E1105 02:31:19.695642       1 sync.go:190] \"propagation check failed\" err=\"wrong status code '503', expected '200'\" logger=\"cert-manager.challenges\" ",
  "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:19.717618834Z E1105 02:31:19.717496       1 sync.go:190] \"propagation check failed\" err=\"wrong status code '503', expected '200'\" logger=\"cert-manager.challenges\" ",
  "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:07:56.812447266Z E1105 03:07:56.812388       1 sync.go:190] \"propagation check failed\" err=\"did not get expected response when querying endpoint, expected \\\"ZpOgx2g1J"
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.flush-failed</code></summary>

```json
{
 "count": 10,
 "first": "2026-11-05T07:33:46Z",
 "last": "2026-11-05T07:59:41Z",
 "warn_at": 10,
 "fail_at": 500,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 10
 },
 "samples": [
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:33:46.228066540+09:00 [2026/11/05 07:33:46] [ warn] [engine] failed to flush chunk '1-1793864015.954723395.flb', retry in 8 seconds: task_id=6, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:33:46.228478886+09:00 [2026/11/05 07:33:46] [ warn] [engine] failed to flush chunk '1-1793864016.874502320.flb', retry in 10 seconds: task_id=8, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:37:36.226299423+09:00 [2026/11/05 07:37:36] [ warn] [engine] failed to flush chunk '1-1793864245.332492621.flb', retry in 10 seconds: task_id=3, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:37:36.228145261+09:00 [2026/11/05 07:37:36] [ warn] [engine] failed to flush chunk '1-1793864245.963626695.flb', retry in 10 seconds: task_id=5, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:46:46.227885418+09:00 [2026/11/05 07:46:46] [ warn] [engine] failed to flush chunk '1-1793864797.85016177.flb', retry in 11 seconds: task_id=9, input=tail.0 > output=es.0 (out_id=0)"
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.upstream-down</code></summary>

```json
{
 "count": 7,
 "first": "2026-11-05T07:30:56Z",
 "last": "2026-11-05T08:02:06Z",
 "warn_at": 5,
 "fail_at": 200,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 7
 },
 "samples": [
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:30:56.226441555+09:00 [2026/11/05 07:30:56] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:35:37.226372236+09:00 [2026/11/05 07:35:37] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:36:26.226358062+09:00 [2026/11/05 07:36:26] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:40:42.230385026+09:00 [2026/11/05 07:40:42] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:53:32.226194176+09:00 [2026/11/05 07:53:32] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error"
 ]
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/logging</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "elasticsearch",
  "instance": "<ip>:10250",
  "namespace": "logging",
  "pod": "elasticsearch-0",
  "service": "kube-prometheus-stack-kubelet",
  "severity": "info"
 },
 "value": 3.1279926273143954
}
```

</details>
<details><summary><code>observability.fluentbit-output-errors.cluster</code></summary>

```json
{
 "records_in_1h": null,
 "output_errors_1h": null,
 "dropped_records_1h": null,
 "metrics_scraped": false,
 "retries_failed_1h": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-backend</code></summary>

```json
{
 "namespace": "app-a-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "api.app-a.acme.com",
  "api.example-a.dev"
 ],
 "source": null,
 "services": [
  "app-a-backend"
 ],
 "ingress": "app-a-backend"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-frontend</code></summary>

```json
{
 "namespace": "app-a-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-a.acme.com",
  "example-a.dev",
  "www.example-a.dev"
 ],
 "source": null,
 "services": [
  "app-a-frontend"
 ],
 "ingress": "app-a-frontend"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "namespace": "app-a-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "obs.example-a.dev"
 ],
 "source": null,
 "services": [
  "app-a-phoenix"
 ],
 "ingress": "app-a-phoenix"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-umami</code></summary>

```json
{
 "namespace": "app-a-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "umami.example-a.dev",
  "umami.example-l.com"
 ],
 "source": null,
 "services": [
  "app-a-umami"
 ],
 "ingress": "app-a-umami"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.argocd/argocd-server-ingress</code></summary>

```json
{
 "namespace": "argocd",
 "hosts": [
  "argocd.acme.com"
 ],
 "source": null,
 "services": [
  "argocd-server"
 ],
 "ingress": "argocd-server-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-backend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-b-api.acme.com"
 ],
 "source": null,
 "services": [
  "app-b-backend"
 ],
 "ingress": "app-b-backend"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-frontend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-b.acme.com"
 ],
 "source": null,
 "services": [
  "app-b-frontend"
 ],
 "ingress": "app-b-frontend"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-signaling-ingress</code></summary>

```json
{
 "namespace": "app-c-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.acme.com",
  "example-h.space",
  "www.example-h.space"
 ],
 "source": null,
 "services": [
  "app-c-signaling-svc"
 ],
 "ingress": "app-c-signaling-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-web-ingress</code></summary>

```json
{
 "namespace": "app-c-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.acme.com",
  "example-h.space",
  "www.example-h.space"
 ],
 "source": null,
 "services": [
  "app-c-web-svc"
 ],
 "ingress": "app-c-web-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.acme-site/acme-site</code></summary>

```json
{
 "namespace": "acme-site",
 "hosts": [
  "acme.com"
 ],
 "source": null,
 "services": [
  "acme-site"
 ],
 "ingress": "acme-site"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-admin-ingress</code></summary>

```json
{
 "namespace": "app-d-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "admin.example-e.com"
 ],
 "source": null,
 "services": [
  "app-d-admin-svc"
 ],
 "ingress": "app-d-admin-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-ingress</code></summary>

```json
{
 "namespace": "app-d-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app.example-e.com"
 ],
 "source": null,
 "services": [
  "app-d-svc"
 ],
 "ingress": "app-d-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-mx-ingress</code></summary>

```json
{
 "namespace": "app-d-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "mx.example-e.com"
 ],
 "source": null,
 "services": [
  "app-d-mx-svc"
 ],
 "ingress": "app-d-mx-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-vn-ingress</code></summary>

```json
{
 "namespace": "app-d-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "vn.example-e.com"
 ],
 "source": null,
 "services": [
  "app-d-vn-svc"
 ],
 "ingress": "app-d-vn-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-e-api/app-e-api</code></summary>

```json
{
 "namespace": "app-e-api",
 "hosts": [
  "app-e-api.acme.com",
  "app-e-cdn.acme.com"
 ],
 "source": null,
 "services": [
  "app-e-api",
  "app-e-minio"
 ],
 "ingress": "app-e-api"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-admin-ingress</code></summary>

```json
{
 "namespace": "app-f-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-admin-prod.acme.com",
  "example-f.com",
  "www.example-f.com"
 ],
 "source": null,
 "services": [
  "app-f-admin-svc"
 ],
 "ingress": "app-f-admin-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-api-server-ingress</code></summary>

```json
{
 "namespace": "app-f-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-api-prod.acme.com"
 ],
 "source": null,
 "services": [
  "app-f-api-server-svc"
 ],
 "ingress": "app-f-api-server-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-api-server-oauth-ingress</code></summary>

```json
{
 "namespace": "app-f-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "example-k.kr",
  "www.example-k.kr"
 ],
 "source": null,
 "services": [
  "app-f-api-server-svc"
 ],
 "ingress": "app-f-api-server-oauth-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-app-x-client-ingress</code></summary>

```json
{
 "namespace": "app-f-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-app-x-client-prod.acme.com",
  "example-k.kr",
  "www.example-k.kr"
 ],
 "source": null,
 "services": [
  "app-f-app-x-client-svc"
 ],
 "ingress": "app-f-app-x-client-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-app-w-ingress</code></summary>

```json
{
 "namespace": "app-f-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-app-w-prod.acme.com",
  "example-g.com",
  "www.example-g.com"
 ],
 "source": null,
 "services": [
  "app-f-app-w-svc"
 ],
 "ingress": "app-f-app-w-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.logging/kibana</code></summary>

```json
{
 "namespace": "logging",
 "hosts": [
  "kibana.acme.com"
 ],
 "source": null,
 "services": [
  "kibana"
 ],
 "ingress": "kibana"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-g-prod/app-g-ingress</code></summary>

```json
{
 "namespace": "app-g-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "app-g.acme.com",
  "example-j.com",
  "www.example-j.com"
 ],
 "source": null,
 "services": [
  "app-g-svc"
 ],
 "ingress": "app-g-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.monitoring/monitoring-grafana-ingress</code></summary>

```json
{
 "namespace": "monitoring",
 "hosts": [
  "grafana.acme.com"
 ],
 "source": null,
 "services": [
  "kube-prometheus-stack-grafana"
 ],
 "ingress": "monitoring-grafana-ingress"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h/app-h</code></summary>

```json
{
 "namespace": "app-h",
 "hosts": [
  "app-h.acme.com"
 ],
 "source": null,
 "services": [
  "app-h"
 ],
 "ingress": "app-h"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.registry/registry</code></summary>

```json
{
 "namespace": "registry",
 "hosts": [
  "registry.acme.com"
 ],
 "source": null,
 "services": [
  "registry"
 ],
 "ingress": "registry"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-k/app-k</code></summary>

```json
{
 "namespace": "app-k",
 "hosts": [
  "app-k.acme.com"
 ],
 "source": null,
 "services": [
  "app-k-workstation"
 ],
 "ingress": "app-k"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-k/app-k-auth</code></summary>

```json
{
 "namespace": "app-k",
 "hosts": [
  "app-k.acme.com"
 ],
 "source": null,
 "services": [
  "app-k-workstation"
 ],
 "ingress": "app-k-auth"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-i-prod/app-i-api</code></summary>

```json
{
 "namespace": "app-i-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "api.example-i.dev"
 ],
 "source": null,
 "services": [
  "app-i-api"
 ],
 "ingress": "app-i-api"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-i-prod/app-i-web</code></summary>

```json
{
 "namespace": "app-i-prod",
 "cluster_ic_metrics": false,
 "hosts": [
  "example-i.dev"
 ],
 "source": null,
 "services": [
  "app-i-web"
 ],
 "ingress": "app-i-web"
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "alerting": 161,
 "by_class": {
  "cause": 153,
  "app-cause": 1,
  "app": 7
 },
 "by_severity": {
  "warning": 106,
  "critical": 46,
  "none": 2,
  "info": 7
 },
 "page_severity_cause": [
  "AppAClusterCPU80",
  "AppAClusterMem80",
  "AppABackendDown",
  "AppAFrontendDown",
  "AppAPostgresDown",
  "AppAGatewayDown",
  "AlertmanagerFailedReload",
  "AlertmanagerMembersInconsistent",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterCrashlooping",
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
  "KubeletClientCertificateExpiration",
  "KubeletServerCertificateExpiration",
  "KubeletDown",
  "NodeFilesystemSpaceFillingUp",
  "NodeFilesystemAlmostOutOfSpace",
  "NodeFilesystemFilesFillingUp",
  "NodeFilesystemAlmostOutOfFiles",
  "NodeRAIDDegraded",
  "NodeFileDescriptorLimit",
  "PrometheusBadConfig",
  "PrometheusRemoteStorageFailures",
  "PrometheusRemoteWriteBehind",
  "PrometheusRuleFailures"
 ]
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-backup</code></summary>

```json
{
 "pod_failure_policy": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "target": "app-d-prod/app-d-postgres-backup",
 "suspend": false,
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "concurrency_policy": "Allow",
 "active_deadline_s": null,
 "prod": true,
 "backoff_limit": null,
 "starting_deadline_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-mx-backup</code></summary>

```json
{
 "pod_failure_policy": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "target": "app-d-prod/app-d-postgres-mx-backup",
 "suspend": false,
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "concurrency_policy": "Allow",
 "active_deadline_s": null,
 "prod": true,
 "backoff_limit": null,
 "starting_deadline_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-vn-backup</code></summary>

```json
{
 "pod_failure_policy": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "target": "app-d-prod/app-d-postgres-vn-backup",
 "suspend": false,
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "concurrency_policy": "Allow",
 "active_deadline_s": null,
 "prod": true,
 "backoff_limit": null,
 "starting_deadline_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-f-prod/app-f-mysql-backup</code></summary>

```json
{
 "pod_failure_policy": false,
 "schedule": "50 2 * * *",
 "ttl_s": null,
 "target": "app-f-prod/app-f-mysql-backup",
 "suspend": false,
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "concurrency_policy": "Allow",
 "active_deadline_s": null,
 "prod": true,
 "backoff_limit": null,
 "starting_deadline_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-g-prod/app-g-postgres-backup</code></summary>

```json
{
 "pod_failure_policy": false,
 "schedule": "0 3 * * *",
 "ttl_s": null,
 "target": "app-g-prod/app-g-postgres-backup",
 "suspend": false,
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "concurrency_policy": "Allow",
 "active_deadline_s": null,
 "prod": true,
 "backoff_limit": null,
 "starting_deadline_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog</code></summary>

```json
{
 "runtime_over_interval": 0.85,
 "schedule": "* * * * *",
 "target": "app-a-prod/app-a-sandbox-watchdog",
 "suspend": false,
 "jobs_timed": 1,
 "median_job_duration_s": 51,
 "active_jobs": 1,
 "concurrency_policy": "Forbid",
 "interval_h": 0.016666666666666666,
 "max_job_duration_s": 51
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-e-api/statefulset/app-e-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": false,
 "startup": null,
 "workload": "app-e-api/statefulset/app-e-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-h/deployment/app-h-postgres:postgres</code></summary>

```json
{
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": false,
 "startup": null,
 "workload": "app-h/deployment/app-h-postgres",
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.priority-inversion.cluster</code></summary>

```json
{
 "nonprod_max_priority": 0,
 "preempted_events": 0,
 "no_user_classes_with_prod": true,
 "pods_by_class": {
  "(none, 0)": 92,
  "system-cluster-critical": 1,
  "system-node-critical": 3
 },
 "prod_pods_without_class": 49,
 "user_classes": [],
 "prod_pods": 49,
 "prod_max_priority": 0,
 "inversion": []
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.cluster</code></summary>

```json
{
 "db_workloads_with_pvc": 16,
 "count": 7,
 "prod_db_without_backup_cronjob": [
  "app-c-prod/statefulset/app-c-postgres",
  "app-i-prod/deployment/app-i-postgres"
 ],
 "local_only": [
  "app-a-prod/app-a-postgres-backup",
  "app-d-prod/app-d-postgres-backup",
  "app-d-prod/app-d-postgres-mx-backup",
  "app-d-prod/app-d-postgres-vn-backup",
  "app-e-api/app-e-postgres-backup",
  "app-f-prod/app-f-mysql-backup",
  "app-g-prod/app-g-postgres-backup"
 ],
 "same_node": [
  "app-d-prod/app-d-postgres-backup",
  "app-d-prod/app-d-postgres-vn-backup",
  "app-e-api/app-e-postgres-backup",
  "app-f-prod/app-f-mysql-backup",
  "app-g-prod/app-g-postgres-backup"
 ]
}
```

</details>
<details><summary><code>resilience.single-node-dependency.registry/statefulset/registry</code></summary>

```json
{
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "prod": false,
 "replicas": 1,
 "workload": "registry/statefulset/registry"
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-backend-79c97cbbd6-kkc2d",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.02994467626017421,
   "cpu_p95_7d_cores": 0.002994467626017421,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-backend-79c97cbbd6-ztv7h",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.02092568130557267,
   "cpu_p95_7d_cores": 0.002092568130557267,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-frontend-574ff75654-6sqcp",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.05869103675126618,
   "cpu_p95_7d_cores": 0.005869103675126618,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-frontend-574ff75654-rjbzg",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.057552602982122496,
   "cpu_p95_7d_cores": 0.00575526029821225,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-gateway:gateway</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-gateway-6d898d5f68-rqgsj",
   "container": "gateway"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0020036138267931266,
   "cpu_p95_7d_cores": 0.0002003613826793127,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-gateway-6d898d5f68-5sd56",
   "container": "gateway"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0011948396445554637,
   "cpu_p95_7d_cores": 0.00011948396445554637,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-phoenix:phoenix</code></summary>

```json
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-phoenix-56ddc584cf-znjvs",
  "container": "phoenix"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.06877979900908544,
  "cpu_p95_7d_cores": 0.006877979900908545,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/sts/app-a-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.2773502237092566,
  "cpu_p95_7d_cores": 0.055470044741851326,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-e-api/deploy/app-e-api:api</code></summary>

```json
{
 "labels": {
  "namespace": "app-e-api",
  "pod": "app-e-api-7cb685d8cf-zxqt7",
  "container": "api"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.013375778211018183,
  "cpu_p95_7d_cores": 0.0013375778211018184,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-api-server:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-f-prod",
   "pod": "app-f-api-server-5d6b56f78b-xxzbl",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.15094288726514282,
   "cpu_p95_7d_cores": 0.015094288726514282,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-f-prod",
   "pod": "app-f-api-server-5d6b56f78b-srwnk",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.06979495898436303,
   "cpu_p95_7d_cores": 0.006979495898436302,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-f-prod",
   "pod": "app-f-api-server-5d6b56f78b-fd59m",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.061897482563614895,
   "cpu_p95_7d_cores": 0.0061897482563614895,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-f-prod/sts/app-f-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "app-f-prod",
  "pod": "app-f-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.07836713019584644,
  "cpu_p95_7d_cores": 0.01567342603916929,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.ingress-nginx/deploy/nginx-ingress-ingress-nginx-controller:controller</code></summary>

```json
[
 {
  "labels": {
   "namespace": "ingress-nginx",
   "pod": "nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.042984883371671376,
   "cpu_p95_7d_cores": 0.004298488337167138,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "ingress-nginx",
   "pod": "nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.04011477711650641,
   "cpu_p95_7d_cores": 0.0040114777116506415,
   "container_cpu_request_cores": 0.1
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
  "pod": "keda-admission-webhooks-5d67c9bcfb-8fcdl",
  "container": "keda-admission-webhooks"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.003137685447836962,
  "cpu_p95_7d_cores": 0.0003137685447836962,
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
  "pod": "keda-operator-metrics-apiserver-7ff5758fd7-gq7g7",
  "container": "keda-operator-metrics-apiserver"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.03318082076023784,
  "cpu_p95_7d_cores": 0.003318082076023784,
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
  "pod": "keda-operator-85ff5bb446-lwkl6",
  "container": "keda-operator"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.01812935854052349,
  "cpu_p95_7d_cores": 0.001812935854052349,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns</code></summary>

```json
{
 "labels": {
  "namespace": "kube-system",
  "pod": "coredns-59d4d457d-qjng8",
  "container": "coredns"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.09916200634860058,
  "cpu_p95_7d_cores": 0.009916200634860059,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server</code></summary>

```json
{
 "labels": {
  "namespace": "kube-system",
  "pod": "metrics-server-7bfffcd44-fkpfm",
  "container": "metrics-server"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.08007355007372452,
  "cpu_p95_7d_cores": 0.008007355007372452,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.logging/deploy/kibana:kibana</code></summary>

```json
{
 "labels": {
  "namespace": "logging",
  "pod": "kibana-59c97cdf75-ht2zf",
  "container": "kibana"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.020003923652777526,
  "cpu_p95_7d_cores": 0.004000784730555505,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-h/deploy/app-h:web</code></summary>

```json
{
 "labels": {
  "namespace": "app-h",
  "pod": "app-h-54c94979b5-b65b5",
  "container": "web"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.011148281642504643,
  "cpu_p95_7d_cores": 0.0011148281642504644,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-i-prod/deploy/app-i-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-i-prod",
  "pod": "app-i-postgres-76b69b654d-lzf4d",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.014412221750652638,
  "cpu_p95_7d_cores": 0.001441222175065264,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>scaling.hpa-flapping.app-f-prod/hpa/app-f-api-server</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "app-f-api-server",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "app-f-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 34.0
}
```

</details>
<details><summary><code>security.no-default-deny.cluster</code></summary>

```json
{
 "prod_without_default_deny": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "enforced": true,
 "default_deny_ingress_namespaces": []
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
 "prod_without_psa": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "psa_enforced_namespaces": [
  "metallb-system"
 ],
 "root_allowed_prod": [
  "app-a-prod/deployment/app-a-backend",
  "app-a-prod/deployment/app-a-phoenix",
  "app-a-prod/deployment/app-a-umami",
  "app-a-prod/deployment/app-v-sales-bot",
  "app-b-prod/deployment/app-b-backend",
  "app-c-prod/deployment/app-c-coturn",
  "app-c-prod/deployment/app-c-signaling",
  "app-c-prod/deployment/app-c-web",
  "app-d-prod/deployment/app-d",
  "app-d-prod/deployment/app-d-admin",
  "app-d-prod/deployment/app-d-mx",
  "app-d-prod/deployment/app-d-mx-worker",
  "app-d-prod/deployment/app-d-sales-bot",
  "app-d-prod/deployment/app-d-vn",
  "app-d-prod/deployment/app-d-vn-worker",
  "app-d-prod/deployment/app-d-worker",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-api-server",
  "app-f-prod/deployment/app-f-app-x-client",
  "app-f-prod/deployment/app-f-embed",
  "app-f-prod/deployment/app-f-excel-agent",
  "app-f-prod/deployment/app-f-app-w",
  "app-g-prod/deployment/app-g",
  "app-i-prod/deployment/app-i-postgres",
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-c-prod/statefulset/app-c-postgres",
  "app-d-prod/statefulset/app-d-postgres",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "app-d-prod/statefulset/app-d-redis",
  "app-f-prod/statefulset/app-f-mysql",
  "app-f-prod/statefulset/app-f-qdrant",
  "app-g-prod/statefulset/app-g-postgres",
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-a-prod/cronjob/app-v-autopost-en",
  "app-a-prod/cronjob/app-v-autopost-ja",
  "app-a-prod/cronjob/app-v-digest-day",
  "app-a-prod/cronjob/app-v-digest-month",
  "app-a-prod/cronjob/app-v-digest-week",
  "app-a-prod/cronjob/app-v-radar-global",
  "app-a-prod/cronjob/app-v-radar-global-eu",
  "app-a-prod/cronjob/app-v-radar-japan",
  "app-a-prod/cronjob/app-v-radar-japan-noon",
  "app-a-prod/cronjob/umami-report-day",
  "app-a-prod/cronjob/umami-report-month",
  "app-a-prod/cronjob/umami-report-week",
  "app-d-prod/cronjob/app-d-ga4-digest-day",
  "app-d-prod/cronjob/app-d-ga4-digest-month",
  "app-d-prod/cronjob/app-d-ga4-digest-week",
  "app-d-prod/cronjob/app-d-policy-radar",
  "app-d-prod/cronjob/app-d-postgres-backup",
  "app-d-prod/cronjob/app-d-postgres-mx-backup",
  "app-d-prod/cronjob/app-d-postgres-vn-backup",
  "app-f-prod/cronjob/app-f-mysql-backup",
  "app-g-prod/cronjob/app-g-postgres-backup"
 ],
 "root_allowed_ratio": 0.71
}
```

</details>
<details><summary><code>security.rbac-wildcard.argocd-application-controller</code></summary>

```json
{
 "bound": true,
 "prod": false,
 "clusterrole": "argocd-application-controller",
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "argocd",
   "name": "argocd-application-controller"
  }
 ]
}
```

</details>
<details><summary><code>security.sa-token-mounted-without-rbac.cluster</code></summary>

```json
{
 "token_mounted_without_rbac_prod": [
  "app-a-prod/deployment/app-a-frontend",
  "app-a-prod/deployment/app-a-gateway",
  "app-a-prod/deployment/app-a-phoenix",
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-a-prod/deployment/app-a-umami",
  "app-b-prod/deployment/app-b-backend",
  "app-b-prod/deployment/app-b-frontend",
  "app-c-prod/deployment/app-c-coturn",
  "app-c-prod/statefulset/app-c-postgres",
  "app-c-prod/deployment/app-c-signaling",
  "app-c-prod/deployment/app-c-web",
  "app-d-prod/deployment/app-d",
  "app-d-prod/deployment/app-d-admin",
  "app-d-prod/deployment/app-d-mx",
  "app-d-prod/deployment/app-d-mx-worker",
  "app-d-prod/statefulset/app-d-postgres",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "app-d-prod/statefulset/app-d-redis",
  "app-d-prod/deployment/app-d-vn",
  "app-d-prod/deployment/app-d-vn-worker",
  "app-d-prod/deployment/app-d-worker",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-api-server",
  "app-f-prod/deployment/app-f-app-x-client",
  "app-f-prod/deployment/app-f-embed",
  "app-f-prod/deployment/app-f-excel-agent",
  "app-f-prod/statefulset/app-f-mysql",
  "app-f-prod/deployment/app-f-app-w",
  "app-f-prod/statefulset/app-f-qdrant",
  "app-g-prod/deployment/app-g",
  "app-g-prod/statefulset/app-g-postgres",
  "app-i-prod/deployment/app-i-api",
  "app-i-prod/deployment/app-i-postgres",
  "app-i-prod/deployment/app-i-web"
 ],
 "token_mounted": 80,
 "service_accounts": 91,
 "automount_false_sa": 1,
 "workloads": 82
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
 "rows": [
  {
   "namespace": "app-f-prod",
   "name": "app-f-qdrant-data-app-f-qdrant-0",
   "target": "app-f-prod/app-f-qdrant-data-app-f-qdrant-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 10.0,
   "capacity_gb": 106.7,
   "used_ratio": 0.726,
   "inode_ratio": 0.166,
   "growth_gb_per_day": -0.467,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "statefulset/app-f-qdrant"
   ],
   "db_like": true,
   "pv": "pvc-76f7091e-04fe-4abb-98b6-e814163b9ee6",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-h",
   "name": "app-h-postgres-data",
   "target": "app-h/app-h-postgres-data",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": 106.7,
   "used_ratio": 0.726,
   "inode_ratio": 0.166,
   "growth_gb_per_day": -0.468,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "deployment/app-h-postgres"
   ],
   "db_like": true,
   "pv": "pvc-123d97df-e04a-495f-9283-69147d9a8679",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-a-prod",
   "name": "app-a-postgres-backup-pvc",
   "target": "app-a-prod/app-a-postgres-backup-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": -0.244,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-a-postgres-backup-29894595",
    "job/app-a-postgres-backup-29896035",
    "job/app-a-postgres-backup-29897475"
   ],
   "db_like": true,
   "pv": "pvc-ff3e86cb-38ac-461e-93ea-fc0c6f0fadda",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-a-prod",
   "name": "data-app-a-postgres-0",
   "target": "app-a-prod/data-app-a-postgres-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-a-postgres"
   ],
   "db_like": true,
   "pv": "pvc-d82daba5-58bf-4f2b-aa68-94278a5a33fd",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-a-prod",
   "name": "data-app-a-redis-0",
   "target": "app-a-prod/data-app-a-redis-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 1.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-a-redis"
   ],
   "db_like": true,
   "pv": "pvc-645a9c5d-9faa-4441-b506-436861a32ebf",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-b-prod",
   "name": "app-b-artifacts",
   "target": "app-b-prod/app-b-artifacts",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "deployment/app-b-backend"
   ],
   "db_like": false,
   "pv": "pvc-5e9317ac-0de1-4afb-b312-8244dbebd7bd",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-c-prod",
   "name": "postgres-data-app-c-postgres-0",
   "target": "app-c-prod/postgres-data-app-c-postgres-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-c-postgres"
   ],
   "db_like": true,
   "pv": "pvc-fedc8d18-9f78-48d0-91be-54dcece66bab",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "default",
   "name": "data-app-z-db-0",
   "target": "default/data-app-z-db-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [],
   "db_like": true,
   "pv": "pvc-8548aa25-05f2-4388-8c7e-872d080f2a0c",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-backup-pvc",
   "target": "app-d-prod/app-d-postgres-backup-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-d-postgres-backup-29894610",
    "job/app-d-postgres-backup-29896050",
    "job/app-d-postgres-backup-29897490"
   ],
   "db_like": true,
   "pv": "pvc-e8064a22-b689-4d23-adef-de705d889c95",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-data-app-d-postgres-0",
   "target": "app-d-prod/app-d-postgres-data-app-d-postgres-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-d-postgres"
   ],
   "db_like": true,
   "pv": "pvc-d3dc33a5-26ca-4c1a-a9e7-526e2c0a0e7a",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-mx-backup-pvc",
   "target": "app-d-prod/app-d-postgres-mx-backup-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-d-postgres-mx-backup-29894610",
    "job/app-d-postgres-mx-backup-29896050",
    "job/app-d-postgres-mx-backup-29897490"
   ],
   "db_like": true,
   "pv": "pvc-378c5351-e088-4317-9671-7f05346e9531",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-mx-data-app-d-postgres-mx-0",
   "target": "app-d-prod/app-d-postgres-mx-data-app-d-postgres-mx-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-d-postgres-mx"
   ],
   "db_like": true,
   "pv": "pvc-c57619eb-bdde-45d0-b9c0-0845856203af",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-vn-backup-pvc",
   "target": "app-d-prod/app-d-postgres-vn-backup-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-d-postgres-vn-backup-29894610",
    "job/app-d-postgres-vn-backup-29896050",
    "job/app-d-postgres-vn-backup-29897490"
   ],
   "db_like": true,
   "pv": "pvc-76170548-ef10-4112-9aaf-5332ae1eeeaa",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-postgres-vn-data-app-d-postgres-vn-0",
   "target": "app-d-prod/app-d-postgres-vn-data-app-d-postgres-vn-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-d-postgres-vn"
   ],
   "db_like": true,
   "pv": "pvc-5bef8ef5-dc76-48cf-8642-05c4099a8d95",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-redis-data-app-d-redis-0",
   "target": "app-d-prod/app-d-redis-data-app-d-redis-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 1.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-d-redis"
   ],
   "db_like": true,
   "pv": "pvc-9fad0f20-f5fa-49ff-89f8-af0aaf8d55bd",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-e-api",
   "name": "app-e-minio-data-app-e-minio-0",
   "target": "app-e-api/app-e-minio-data-app-e-minio-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 50.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-e-minio"
   ],
   "db_like": true,
   "pv": "pvc-b31ee6ea-3238-4ecc-a34d-877a14177ad5",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-e-api",
   "name": "app-e-postgres-backup-pvc",
   "target": "app-e-api/app-e-postgres-backup-pvc",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-e-postgres-backup-29894630",
    "job/app-e-postgres-backup-29896070",
    "job/app-e-postgres-backup-29897510"
   ],
   "db_like": true,
   "pv": "pvc-228da581-f434-4f84-ba50-d91df7133690",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-e-api",
   "name": "app-e-postgres-data-app-e-postgres-0",
   "target": "app-e-api/app-e-postgres-data-app-e-postgres-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-e-postgres"
   ],
   "db_like": true,
   "pv": "pvc-b6f729e1-b443-4ed2-866f-8fc9825078ae",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-f-prod",
   "name": "mysql-backup-app-f-mysql-0",
   "target": "app-f-prod/mysql-backup-app-f-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-f-mysql-backup-29894570",
    "job/app-f-mysql-backup-29896010",
    "job/app-f-mysql-backup-29897450",
    "statefulset/app-f-mysql"
   ],
   "db_like": true,
   "pv": "pvc-a9a03cde-f245-4987-b4b8-e61763da9993",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-f-prod",
   "name": "mysql-data-app-f-mysql-0",
   "target": "app-f-prod/mysql-data-app-f-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 20.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-f-mysql"
   ],
   "db_like": true,
   "pv": "pvc-d15ad7cd-aea4-482d-8b3e-f0386a4f73a1",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "logging",
   "name": "data-elasticsearch-0",
   "target": "logging/data-elasticsearch-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 20.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/elasticsearch"
   ],
   "db_like": true,
   "pv": "pvc-db50eb33-8393-45cd-93b3-042e019e1186",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-g-prod",
   "name": "app-g-postgres-backup-pvc",
   "target": "app-g-prod/app-g-postgres-backup-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-g-postgres-backup-29894580",
    "job/app-g-postgres-backup-29896020",
    "job/app-g-postgres-backup-29897460"
   ],
   "db_like": true,
   "pv": "pvc-4ce85409-5052-4afb-8c7c-fa0a912f7e09",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-g-prod",
   "name": "app-g-postgres-data-app-g-postgres-0",
   "target": "app-g-prod/app-g-postgres-data-app-g-postgres-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 30.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-g-postgres"
   ],
   "db_like": true,
   "pv": "pvc-8729556f-dbf5-40ce-a48b-57eb4e27edc6",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "registry",
   "name": "registry-data-registry-0",
   "target": "registry/registry-data-registry-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 50.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/registry-gc-29894640",
    "job/registry-gc-29896080",
    "job/registry-gc-29897520",
    "statefulset/registry"
   ],
   "db_like": true,
   "pv": "pvc-1a2c9674-3fcb-4205-85f2-3f2d08fd1c92",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-i-prod",
   "name": "app-i-artifacts",
   "target": "app-i-prod/app-i-artifacts",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "deployment/app-i-api"
   ],
   "db_like": false,
   "pv": "pvc-c66c539e-96b8-4cb2-ba16-90df9d05a84f",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-i-prod",
   "name": "app-i-postgres-data",
   "target": "app-i-prod/app-i-postgres-data",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "deployment/app-i-postgres"
   ],
   "db_like": true,
   "pv": "pvc-291c9301-e481-4b69-9234-bb77f18d6faf",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  }
 ],
 "prod_db_delete_reclaim": [
  "app-f-prod/app-f-qdrant-data-app-f-qdrant-0",
  "app-a-prod/app-a-postgres-backup-pvc",
  "app-a-prod/data-app-a-postgres-0",
  "app-a-prod/data-app-a-redis-0",
  "app-c-prod/postgres-data-app-c-postgres-0",
  "app-d-prod/app-d-postgres-backup-pvc",
  "app-d-prod/app-d-postgres-data-app-d-postgres-0",
  "app-d-prod/app-d-postgres-mx-backup-pvc",
  "app-d-prod/app-d-postgres-mx-data-app-d-postgres-mx-0",
  "app-d-prod/app-d-postgres-vn-backup-pvc",
  "app-d-prod/app-d-postgres-vn-data-app-d-postgres-vn-0",
  "app-d-prod/app-d-redis-data-app-d-redis-0",
  "app-f-prod/mysql-backup-app-f-mysql-0",
  "app-f-prod/mysql-data-app-f-mysql-0",
  "app-g-prod/app-g-postgres-backup-pvc",
  "app-g-prod/app-g-postgres-data-app-g-postgres-0",
  "app-i-prod/app-i-postgres-data"
 ]
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.app-f-prod</code></summary>

```json
{
 "namespace": "app-f-prod",
 "kind": "prod",
 "cpu_max_7d": 0.589,
 "cpu_median_7d": 0.027,
 "shares_nodes_with_prod": true,
 "cpu_p95_7d": 0.059,
 "nodes": {
  "node-a": 12,
  "node-b": 1
 },
 "system": false,
 "cpu_limits": 8.2,
 "has_quota": false,
 "burst_ratio_7d": 22.1
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-b-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-b-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 2,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": true,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-i-prod</code></summary>

```json
{
 "psa_enforce": null,
 "namespace": "app-i-prod",
 "rbac_subject_count": 0,
 "networkpolicies": 0,
 "shares_nodes_with_prod": true,
 "pods": 3,
 "prod": true,
 "has_limitrange": false,
 "tenants_total": 12,
 "has_quota": true,
 "networkpolicy_enforced": true
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-systems</code></summary>

```json
{
 "memory_p95_7d_gb": 0.36,
 "namespace": "arc-systems",
 "kind": "ci",
 "memory_requests_gb": 2.0,
 "cpu_share_of_cluster_p95": 0.003,
 "cpu_requests": 1.0,
 "shares_nodes_with_prod": true,
 "pods": 3,
 "prod": false,
 "cpu_p95_7d": 0.004,
 "tenants_total": 12,
 "has_quota": false,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-c-prod</code></summary>

```json
{
 "memory_p95_7d_gb": 0.23,
 "namespace": "app-c-prod",
 "kind": "prod",
 "memory_requests_gb": 0.66,
 "cpu_share_of_cluster_p95": 0.01,
 "cpu_requests": 0.17,
 "shares_nodes_with_prod": true,
 "pods": 4,
 "prod": true,
 "cpu_p95_7d": 0.01,
 "tenants_total": 12,
 "cluster_saturated_7d": false,
 "has_quota": false,
 "multi_org": false,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-d-prod</code></summary>

```json
{
 "memory_p95_7d_gb": 1.66,
 "namespace": "app-d-prod",
 "kind": "prod",
 "memory_requests_gb": 3.91,
 "cpu_share_of_cluster_p95": 0.025,
 "cpu_requests": 0.49,
 "shares_nodes_with_prod": true,
 "pods": 12,
 "prod": true,
 "cpu_p95_7d": 0.028,
 "tenants_total": 12,
 "cluster_saturated_7d": false,
 "has_quota": false,
 "multi_org": false,
 "burst_ratio_7d": 1.6
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-f-prod</code></summary>

```json
{
 "memory_p95_7d_gb": 4.73,
 "namespace": "app-f-prod",
 "kind": "prod",
 "memory_requests_gb": 8.12,
 "cpu_share_of_cluster_p95": 0.054,
 "cpu_requests": 1.28,
 "shares_nodes_with_prod": true,
 "pods": 13,
 "prod": true,
 "cpu_p95_7d": 0.059,
 "tenants_total": 12,
 "cluster_saturated_7d": false,
 "has_quota": false,
 "multi_org": false,
 "burst_ratio_7d": 22.1
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-g-prod</code></summary>

```json
{
 "memory_p95_7d_gb": 0.14,
 "namespace": "app-g-prod",
 "kind": "prod",
 "memory_requests_gb": 0.28,
 "cpu_share_of_cluster_p95": 0.005,
 "cpu_requests": 0.1,
 "shares_nodes_with_prod": true,
 "pods": 2,
 "prod": true,
 "cpu_p95_7d": 0.006,
 "tenants_total": 12,
 "cluster_saturated_7d": false,
 "has_quota": false,
 "multi_org": false,
 "burst_ratio_7d": null
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-systems</code></summary>

```json
{
 "memory_p95_7d_gb": 0.36,
 "namespace": "arc-systems",
 "kind": "ci",
 "containers_without_requests": 4,
 "cpu_p95_7d": 0.004,
 "prod": false,
 "has_limitrange": false,
 "containers_without_memory_limit": 4,
 "pods": 3
}
```

</details>
<details><summary><code>traffic.coredns-latency.cluster</code></summary>

```json
{
 "servfail_ratio_1h": 0.0,
 "p99_s_1h": 0.1355
}
```

</details>
<details><summary><code>traffic.ingress-nginx-retired.cluster</code></summary>

```json
{
 "version": "1.14.0",
 "present": true,
 "retired_note": "ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes",
 "admission_webhook": true,
 "retired": true,
 "controllers": [
  {
   "kind": "Deployment",
   "namespace": "ingress-nginx",
   "name": "nginx-ingress-ingress-nginx-controller",
   "image": "registry.k8s.io/ingress-nginx/controller:v1.14.0",
   "version": "1.14.0",
   "replicas": 2,
   "ready": 2,
   "webhook_arg": true
  }
 ]
}
```

</details>
<details><summary><code>hygiene.no-standard-labels.cluster</code></summary>

```json
{
 "without_standard_labels": [
  {
   "workload": "app-a-prod/deployment/app-a-backend",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/deployment/app-a-frontend",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/deployment/app-a-gateway",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/deployment/app-a-phoenix",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {
    "app": "app-a-phoenix"
   }
  },
  {
   "workload": "app-a-prod/deployment/app-a-umami",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {
    "app": "app-a-umami"
   }
  },
  {
   "workload": "app-a-prod/deployment/app-v-sales-bot",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-b-prod/deployment/app-b-backend",
   "namespace": "app-b-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-b-prod/deployment/app-b-frontend",
   "namespace": "app-b-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-c-prod/deployment/app-c-coturn",
   "namespace": "app-c-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-c-prod/deployment/app-c-signaling",
   "namespace": "app-c-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-c-prod/deployment/app-c-web",
   "namespace": "app-c-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "acme-site/deployment/acme-site",
   "namespace": "acme-site",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-admin",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-mx",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-mx-worker",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-sales-bot",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-vn",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-vn-worker",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/deployment/app-d-worker",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-e-api/deployment/app-e-api",
   "namespace": "app-e-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-admin",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-api-server",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-app-x-client",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-embed",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-excel-agent",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-app-w",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "kube-system/deployment/coredns",
   "namespace": "kube-system",
   "prod": false,
   "labels": {
    "k8s-app": "kube-dns",
    "kubernetes.io/name": "CoreDNS",
    "objectset.rio.cattle.io/hash": "bce283298811743a0386ab510f2f67ef74240c57"
   }
  },
  {
   "workload": "kube-system/deployment/local-path-provisioner",
   "namespace": "kube-system",
   "prod": false,
   "labels": {
    "objectset.rio.cattle.io/hash": "183f35c65ffbc3064603f43f1580d8c68a2dabd4"
   }
  },
  {
   "workload": "kube-system/deployment/metrics-server",
   "namespace": "kube-system",
   "prod": false,
   "labels": {
    "k8s-app": "metrics-server",
    "objectset.rio.cattle.io/hash": "e10e245e13e46a725c9dddd4f9eb239f147774fd"
   }
  },
  {
   "workload": "logging/deployment/kibana",
   "namespace": "logging",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "metallb-system/deployment/controller",
   "namespace": "metallb-system",
   "prod": false,
   "labels": {
    "app": "metallb",
    "component": "controller"
   }
  },
  {
   "workload": "app-g-prod/deployment/app-g",
   "namespace": "app-g-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h/deployment/app-h",
   "namespace": "app-h",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-h/deployment/app-h-postgres",
   "namespace": "app-h",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-i-prod/deployment/app-i-api",
   "namespace": "app-i-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-i-prod/deployment/app-i-postgres",
   "namespace": "app-i-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-i-prod/deployment/app-i-web",
   "namespace": "app-i-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/statefulset/app-a-postgres",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/statefulset/app-a-redis",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-c-prod/statefulset/app-c-postgres",
   "namespace": "app-c-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-mx",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/statefulset/app-d-postgres-vn",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/statefulset/app-d-redis",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-e-api/statefulset/app-e-minio",
   "namespace": "app-e-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-e-api/statefulset/app-e-postgres",
   "namespace": "app-e-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-f-prod/statefulset/app-f-mysql",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/statefulset/app-f-qdrant",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "logging/statefulset/elasticsearch",
   "namespace": "logging",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-g-prod/statefulset/app-g-postgres",
   "namespace": "app-g-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "registry/statefulset/registry",
   "namespace": "registry",
   "prod": false,
   "labels": {
    "app": "registry"
   }
  },
  {
   "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {
    "app": "app-a-sandbox-prepull"
   }
  },
  {
   "workload": "kube-system/daemonset/nvidia-device-plugin",
   "namespace": "kube-system",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "logging/daemonset/fluent-bit",
   "namespace": "logging",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "metallb-system/daemonset/speaker",
   "namespace": "metallb-system",
   "prod": false,
   "labels": {
    "app": "metallb",
    "component": "speaker"
   }
  },
  {
   "workload": "app-a-prod/cronjob/app-a-postgres-backup",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-a-sandbox-watchdog",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-autopost-en",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-autopost-ja",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-digest-day",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-digest-month",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-digest-week",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-radar-global",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-radar-global-eu",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-radar-japan",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-v-radar-japan-noon",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/umami-report-day",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/umami-report-month",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/umami-report-week",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-ga4-digest-day",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-ga4-digest-month",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-ga4-digest-week",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-policy-radar",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-postgres-backup",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-postgres-mx-backup",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-d-prod/cronjob/app-d-postgres-vn-backup",
   "namespace": "app-d-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-e-api/cronjob/app-e-postgres-backup",
   "namespace": "app-e-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-mysql-backup",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "kube-system/cronjob/containerd-cleanup-node-a",
   "namespace": "kube-system",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "kube-system/cronjob/containerd-cleanup-node-b",
   "namespace": "kube-system",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "logging/cronjob/es-index-retention",
   "namespace": "logging",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-g-prod/cronjob/app-g-postgres-backup",
   "namespace": "app-g-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "registry/cronjob/registry-gc",
   "namespace": "registry",
   "prod": false,
   "labels": {
    "app": "registry"
   }
  },
  {
   "workload": "registry/cronjob/registry-tag-cleanup",
   "namespace": "registry",
   "prod": false,
   "labels": {
    "app": "registry"
   }
  }
 ],
 "standard_label_ratio": 0.23,
 "workloads": 110
}
```

</details>
<details><summary><code>node.swap-enabled.<ip>:9100</code></summary>

```json
{
 "labels": {
  "__name__": "node_memory_SwapTotal_bytes",
  "container": "node-exporter",
  "endpoint": "http-metrics",
  "instance": "<ip>:9100",
  "job": "node-exporter",
  "namespace": "monitoring",
  "pod": "kube-prometheus-stack-prometheus-node-exporter-rsgt8",
  "service": "kube-prometheus-stack-prometheus-node-exporter"
 },
 "value": 8589930496.0
}
```

</details>
<details><summary><code>platform.k3s-server-url-stale.node-b</code></summary>

```json
{
 "server_url": "https://<ip>:6443",
 "node": "node-b",
 "host": "<ip>"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "target_cpu_utilization": 70,
 "days_since_last_scale": 3.4,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-backend",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.9981481481481481,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "prod": true,
 "current_cpu_utilization": 3,
 "name": "app-a-backend",
 "max": 6
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "target_cpu_utilization": 70,
 "days_since_last_scale": 1.3,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-frontend",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.9979166666666667,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "prod": true,
 "current_cpu_utilization": 2,
 "name": "app-a-frontend",
 "max": 4
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d</code></summary>

```json
{
 "target_cpu_utilization": 60,
 "days_since_last_scale": 7.8,
 "namespace": "app-d-prod",
 "target": "app-d-prod/deployment/app-d",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.999537037037037,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 2,
 "prod": true,
 "current_cpu_utilization": 4,
 "name": "app-d",
 "max": 5
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d-mx</code></summary>

```json
{
 "target_cpu_utilization": 60,
 "days_since_last_scale": 7.8,
 "namespace": "app-d-prod",
 "target": "app-d-prod/deployment/app-d-mx",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.999537037037037,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "prod": true,
 "current_cpu_utilization": 4,
 "name": "app-d-mx",
 "max": 4
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d-vn</code></summary>

```json
{
 "target_cpu_utilization": 60,
 "days_since_last_scale": 7.8,
 "namespace": "app-d-prod",
 "target": "app-d-prod/deployment/app-d-vn",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.999537037037037,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "prod": true,
 "current_cpu_utilization": 4,
 "name": "app-d-vn",
 "max": 4
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-g-prod/deployment/app-g</code></summary>

```json
{
 "target_cpu_utilization": 60,
 "days_since_last_scale": 7.8,
 "namespace": "app-g-prod",
 "target": "app-g-prod/deployment/app-g",
 "never_scaled_15d": true,
 "keda_owned": false,
 "at_min_ratio_15d": 0.999537037037037,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "prod": true,
 "current_cpu_utilization": 2,
 "name": "app-g",
 "max": 3
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "notifications_configured": false,
 "applications_prod": 10,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "ignore_differences_apps": 16,
 "applications_prod": 10,
 "prod_tracking_moving_ref": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/app-c",
  "argocd/application/app-d-kr",
  "argocd/application/app-d-mx",
  "argocd/application/app-d-shared",
  "argocd/application/app-d-vn",
  "argocd/application/app-f",
  "argocd/application/app-g",
  "argocd/application/app-i-prod"
 ]
}
```

</details>
<details><summary><code>certmanager.controller-errors.cluster</code></summary>

```json
{
 "sync_calls": 2454,
 "acme_requests": 117,
 "metrics_available": true,
 "sync_errors": 233,
 "not_ready_metric": 0,
 "acme_errors": 5,
 "acme_by_status": {
  "200": 105,
  "201": 7,
  "400": 5
 },
 "acme_error_ratio": 0.0427
}
```

</details>
<details><summary><code>certmanager.version-old.cluster</code></summary>

```json
{
 "components": {
  "controller": "1/1",
  "cainjector": "1/1",
  "webhook": "1/1"
 },
 "webhook_replicas": 1,
 "version": "1.14.4",
 "webhooks_fail": [
  "webhook.cert-manager.io",
  "webhook.cert-manager.io"
 ]
}
```

</details>
<details><summary><code>coredns.aaaa-noise.cluster</code></summary>

```json
{
 "qps_total": 30.92,
 "aaaa_ratio": 0.487,
 "metrics_available": true,
 "cluster_ipv6": false
}
```

</details>
<details><summary><code>cost.k3s-node-efficiency.cluster</code></summary>

```json
{
 "p95_util_ratio": 0.049,
 "p95_used_cpu": 0.89,
 "can_drop_largest_node": false,
 "requested_cpu": 6.51,
 "request_over_usage": 7.3,
 "nodes": 2,
 "allocatable_cpu": 18.0
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-applicationset-controller",
 "container": "argocd-applicationset-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-dex-server",
 "container": "copyutil"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "ghcr.io",
 "pull_policy": "Always",
 "image": "ghcr.io/dexidp/dex:v2.43.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-dex-server",
 "container": "dex"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-notifications-controller",
 "container": "argocd-notifications-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "public.ecr.aws",
 "pull_policy": "Always",
 "image": "public.ecr.aws/docker/library/redis:8.2.2-alpine",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-redis",
 "container": "redis"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-repo-server",
 "container": "argocd-repo-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-server",
 "container": "argocd-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "quay.io",
 "pull_policy": "Always",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "always_pull_with_tag": true,
 "workload": "argocd/statefulset/argocd-application-controller",
 "container": "argocd-application-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.app-d-prod/deployment/app-d-vn:db-migrate</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "registry.acme.com",
 "pull_policy": "Always",
 "image": "registry.acme.com/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
 "always_pull_with_tag": true,
 "workload": "app-d-prod/deployment/app-d-vn",
 "container": "db-migrate"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "ghcr.io",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.19.0",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-admission-webhooks",
 "container": "keda-admission-webhooks"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "ghcr.io",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.19.0",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator-metrics-apiserver",
 "container": "keda-operator-metrics-apiserver"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator</code></summary>

```json
{
 "tag_kind": "tag",
 "registry": "ghcr.io",
 "pull_policy": "Always",
 "image": "ghcr.io/kedacore/keda:2.19.0",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator",
 "container": "keda-operator"
}
```

</details>
<details><summary><code>hygiene.failed-pods-lingering.cluster</code></summary>

```json
{
 "sample": [
  "app-a-prod/app-u",
  "app-a-prod/app-a-experiment",
  "app-f-prod/app-f-embed-67f6f74f6c-rlm8m",
  "app-f-prod/app-f-embed-67f6f74f6c-b6kdt"
 ],
 "count": 4,
 "by_reason": {
  "Failed": 2,
  "UnexpectedAdmissionError": 2
 },
 "prod": 4,
 "oldest_h": 3849.4,
 "by_namespace": {
  "app-a-prod": 2,
  "app-f-prod": 2
 }
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "prod_without_request": 63,
 "request_ratio": 0.0,
 "with_request": 0,
 "emptydir_without_sizelimit": 11,
 "emptydir_without_sizelimit_prod": [],
 "containers": 126
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "revision_history_limits": {
  "10": 54,
  "0": 3,
  "3": 1,
  "2": 1
 },
 "replicasets_zero": 235,
 "replicasets_total": 292
}
```

</details>
<details><summary><code>hygiene.orphan-secrets.cluster</code></summary>

```json
{
 "orphan_secrets": [
  {
   "namespace": "argocd",
   "name": "ghcr-auth-secret",
   "type": "kubernetes.io/dockerconfigjson",
   "prod": false
  },
  {
   "namespace": "argocd",
   "name": "ghcr-pull-secret",
   "type": "kubernetes.io/dockerconfigjson",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-d-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-z-auth-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-z-aws-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-z-db-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-z-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  },
  {
   "namespace": "app-d-prod",
   "name": "app-d-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  },
  {
   "namespace": "app-f-prod",
   "name": "app-f-store-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  }
 ],
 "secrets_total": 139
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "zero_object_count": 42,
 "webhooks": 28,
 "count": 64,
 "zero_by_group": {
  "generators.external-secrets.io": 17,
  "monitoring.coreos.com": 6,
  "metallb.io": 5,
  "acme.cert-manager.io": 1,
  "eventing.keda.sh": 2,
  "external-secrets.io": 4,
  "keda.sh": 4,
  "helm.cattle.io": 2,
  "actions.summerwind.dev": 1
 }
}
```

</details>
<details><summary><code>keda.unused.cluster</code></summary>

```json
{
 "scaledjobs": 0,
 "version": "2.19.0",
 "operator_ready": 1,
 "webhooks_ready": 1,
 "webhooks_replicas": 1,
 "metrics_apiserver_replicas": 1,
 "operator_replicas": 1,
 "metrics_apiserver_ready": 1,
 "scaledobjects": 0,
 "unused": true
}
```

</details>
<details><summary><code>logs.signatures.cert-manager.orphan-tls-secret</code></summary>

```json
{
 "count": 64,
 "first": "2026-11-04T15:18:56Z",
 "last": "2026-11-05T00:57:19Z",
 "warn_at": 1,
 "fail_at": 1000,
 "files": {
  "logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log": 64
 },
 "samples": [
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553816246Z E1104 15:18:56.553660       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-d-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553871350Z E1104 15:18:56.553679       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-d-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553889414Z E1104 15:18:56.553718       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-d-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553904643Z E1104 15:18:56.553720       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-d-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553915022Z E1104 15:18:56.553727       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-d-p"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metallb.speaker-peer-unreachable</code></summary>

```json
{
 "count": 482,
 "first": "2026-11-05T04:42:34Z",
 "last": "2026-11-05T08:02:35Z",
 "warn_at": 60,
 "fail_at": 2000,
 "files": {
  "logs/pods/metallb/metallb-system_speaker.log": 482
 },
 "samples": [
  "[pod/speaker-lqmcg/speaker] 2026-11-05T04:42:34.862388956Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-05T04:42:44.863358645Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-05T04:42:59.057306211Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-05T04:43:40.932396786Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-05T04:44:40.932359738Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro"
 ]
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
 "never_fired_count": 135,
 "rules_total": 145,
 "never_fired_15d": [
  "AppAClusterCPU50",
  "AppAClusterCPU80",
  "AppAClusterMem50",
  "AppAClusterMem80",
  "AppAFrontendDown",
  "AppAGatewayDown",
  "AppAGatewayErrorRateHigh",
  "AppAGatewayHighCost",
  "AppAGatewayUpstreamRejecting",
  "AppALLMQuotaExhausted",
  "AppAPostgresDown",
  "AppASandboxProvisionFailing",
  "AppATooManySandboxes",
  "AppAWatchdogFailing",
  "AlertmanagerClusterCrashlooping",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerFailedReload",
  "AlertmanagerFailedToSendAlerts",
  "AlertmanagerMembersInconsistent",
  "ConfigReloaderSidecarErrors",
  "KubeAPIDown",
  "KubeAPIErrorBudgetBurn",
  "KubeAPITerminatedRequests",
  "KubeAggregatedAPIDown",
  "KubeAggregatedAPIErrors",
  "KubeCPUQuotaOvercommit",
  "KubeClientCertificateExpiration",
  "KubeClientErrors",
  "KubeContainerWaiting",
  "KubeDaemonSetMisScheduled",
  "KubeDaemonSetNotScheduled",
  "KubeDaemonSetRolloutStuck",
  "KubeDeploymentGenerationMismatch",
  "KubeDeploymentRolloutStuck",
  "KubeHpaReplicasMismatch",
  "KubeJobNotCompleted",
  "KubeMemoryOvercommit",
  "KubeMemoryQuotaOvercommit",
  "KubeNodeEviction",
  "KubeNodeNotReady",
  "KubeNodePressure",
  "KubeNodeReadinessFlapping",
  "KubeNodeUnreachable",
  "KubePdbNotEnoughHealthyPods",
  "KubePersistentVolumeErrors",
  "KubePersistentVolumeFillingUp",
  "KubePersistentVolumeInodesFillingUp",
  "KubePodNotReady",
  "KubeQuotaAlmostFull",
  "KubeQuotaExceeded",
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
  "NodeBondingDegraded",
  "NodeCPUHighUsage",
  "NodeClockNotSynchronising",
  "NodeClockSkewDetected",
  "NodeDiskIOSaturation",
  "NodeFileDescriptorLimit",
  "NodeFilesystemAlmostOutOfFiles",
  "NodeFilesystemAlmostOutOfSpace",
  "NodeFilesystemFilesFillingUp",
  "NodeFilesystemSpaceFillingUp",
  "NodeHighNumberConntrackEntriesUsed",
  "NodeMemoryHighUtilization",
  "NodeMemoryMajorPagesFaults",
  "NodeNetworkInterfaceFlapping",
  "NodeNetworkReceiveErrs",
  "NodeNetworkTransmitErrs",
  "NodeRAIDDegraded",
  "NodeRAIDDiskFailure",
  "NodeSystemSaturation",
  "NodeSystemdServiceCrashlooping",
  "NodeSystemdServiceFailed",
  "NodeTextFileCollectorScrapeError",
  "PrometheusBadConfig",
  "PrometheusDuplicateTimestamps",
  "PrometheusErrorSendingAlertsToAnyAlertmanager",
  "PrometheusErrorSendingAlertsToSomeAlertmanagers",
  "PrometheusHighQueryLoad",
  "PrometheusKubernetesListWatchFailures",
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
 "fired_15d": [
  "AppABackendDown",
  "CPUThrottlingHigh",
  "InfoInhibitor",
  "KubeCPUOvercommit",
  "KubeDeploymentReplicasMismatch",
  "KubeHpaMaxedOut",
  "KubeJobFailed",
  "KubePodCrashLooping",
  "KubeQuotaFullyUsed",
  "Watchdog"
 ]
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "missing_saturation": [
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-backend",
   "class": "nginx",
   "hosts": [
    "api.app-a.acme.com",
    "api.example-a.dev"
   ],
   "services": [
    "app-a-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-frontend",
   "class": "nginx",
   "hosts": [
    "app-a.acme.com",
    "example-a.dev",
    "www.example-a.dev"
   ],
   "services": [
    "app-a-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-phoenix",
   "class": "nginx",
   "hosts": [
    "obs.example-a.dev"
   ],
   "services": [
    "app-a-phoenix"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-umami",
   "class": "nginx",
   "hosts": [
    "umami.example-a.dev",
    "umami.example-l.com"
   ],
   "services": [
    "app-a-umami"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "argocd",
   "ingress": "argocd-server-ingress",
   "class": "nginx",
   "hosts": [
    "argocd.acme.com"
   ],
   "services": [
    "argocd-server"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-b-prod",
   "ingress": "app-b-backend",
   "class": "nginx",
   "hosts": [
    "app-b-api.acme.com"
   ],
   "services": [
    "app-b-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-b-prod",
   "ingress": "app-b-frontend",
   "class": "nginx",
   "hosts": [
    "app-b.acme.com"
   ],
   "services": [
    "app-b-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-c-prod",
   "ingress": "app-c-signaling-ingress",
   "class": "nginx",
   "hosts": [
    "app-c.acme.com",
    "example-h.space",
    "www.example-h.space"
   ],
   "services": [
    "app-c-signaling-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-c-prod",
   "ingress": "app-c-web-ingress",
   "class": "nginx",
   "hosts": [
    "app-c.acme.com",
    "example-h.space",
    "www.example-h.space"
   ],
   "services": [
    "app-c-web-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "acme-site",
   "ingress": "acme-site",
   "class": "nginx",
   "hosts": [
    "acme.com"
   ],
   "services": [
    "acme-site"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-admin-ingress",
   "class": "nginx",
   "hosts": [
    "admin.example-e.com"
   ],
   "services": [
    "app-d-admin-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-ingress",
   "class": "nginx",
   "hosts": [
    "app.example-e.com"
   ],
   "services": [
    "app-d-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-mx-ingress",
   "class": "nginx",
   "hosts": [
    "mx.example-e.com"
   ],
   "services": [
    "app-d-mx-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-d-prod",
   "ingress": "app-d-vn-ingress",
   "class": "nginx",
   "hosts": [
    "vn.example-e.com"
   ],
   "services": [
    "app-d-vn-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-e-api",
   "ingress": "app-e-api",
   "class": "nginx",
   "hosts": [
    "app-e-api.acme.com",
    "app-e-cdn.acme.com"
   ],
   "services": [
    "app-e-api",
    "app-e-minio"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-admin-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-admin-prod.acme.com",
    "example-f.com",
    "www.example-f.com"
   ],
   "services": [
    "app-f-admin-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-api-server-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-api-prod.acme.com"
   ],
   "services": [
    "app-f-api-server-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-api-server-oauth-ingress",
   "class": "nginx",
   "hosts": [
    "example-k.kr",
    "www.example-k.kr"
   ],
   "services": [
    "app-f-api-server-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-app-x-client-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-app-x-client-prod.acme.com",
    "example-k.kr",
    "www.example-k.kr"
   ],
   "services": [
    "app-f-app-x-client-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-f-prod",
   "ingress": "app-f-app-w-ingress",
   "class": "nginx",
   "hosts": [
    "app-f-app-w-prod.acme.com",
    "example-g.com",
    "www.example-g.com"
   ],
   "services": [
    "app-f-app-w-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "logging",
   "ingress": "kibana",
   "class": "nginx",
   "hosts": [
    "kibana.acme.com"
   ],
   "services": [
    "kibana"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-g-prod",
   "ingress": "app-g-ingress",
   "class": "nginx",
   "hosts": [
    "app-g.acme.com",
    "example-j.com",
    "www.example-j.com"
   ],
   "services": [
    "app-g-svc"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-h",
   "ingress": "app-h",
   "class": "nginx",
   "hosts": [
    "app-h.acme.com"
   ],
   "services": [
    "app-h"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "registry",
   "ingress": "registry",
   "class": "nginx",
   "hosts": [
    "registry.acme.com"
   ],
   "services": [
    "registry"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-k",
   "ingress": "app-k",
   "class": "nginx",
   "hosts": [
    "app-k.acme.com"
   ],
   "services": [
    "app-k-workstation"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-k",
   "ingress": "app-k-auth",
   "class": "nginx",
   "hosts": [
    "app-k.acme.com"
   ],
   "services": [
    "app-k-workstation"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-i-prod",
   "ingress": "app-i-api",
   "class": "nginx",
   "hosts": [
    "api.example-i.dev"
   ],
   "services": [
    "app-i-api"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-i-prod",
   "ingress": "app-i-web",
   "class": "nginx",
   "hosts": [
    "example-i.dev"
   ],
   "services": [
    "app-i-web"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": null,
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  }
 ],
 "namespaces_with_saturation_metrics": [
  "default",
  "kube-system",
  "monitoring"
 ],
 "ingresses": 29
}
```

</details>
<details><summary><code>observability.severity-channels-not-separated.cluster</code></summary>

```json
{
 "default_receiver": "discord",
 "routes": [
  {
   "depth": 0,
   "receiver": "discord",
   "matchers": null,
   "continue": false,
   "group_by": [
    "namespace",
    "alertname"
   ],
   "repeat_interval": "4h"
  },
  {
   "depth": 1,
   "receiver": "null",
   "matchers": [
    "severity=~\"info|none\""
   ],
   "continue": false,
   "group_by": null,
   "repeat_interval": null
  }
 ],
 "receivers": {
  "null": [],
  "discord": [
   "slack"
  ]
 }
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "lines_scanned": 20697,
 "error_lines_unclassified": 41,
 "unclassified_errors": [
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manager\" key=\"argocd/argocd-tls\" error=\"Operat",
   "count": 2,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 2
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:06.067267928Z I1105 02:31:06.067138       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manage"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manager\" key=\"app-f-prod/app-f-api-prod-tls\" error=\"",
   "count": 2,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 2
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:07:53.037080205Z I1105 03:07:53.036991       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manage"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manager\" key=\"monitoring/grafana-acme-com-",
   "count": 2,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 2
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:20:48.042521235Z I1105 03:20:48.042447       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manage"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manager\" key=\"logging/kibana-tls\" error=\"Opera",
   "count": 2,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 2
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:35:36.080070617Z I1105 03:35:36.080007       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manage"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-issuer-acme\" key=\"argocd/argocd-tls-7\" erro",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:06.154886084Z I1105 02:31:06.154785       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-iss"
  },
  {
   "pattern": "cert-manager | ingress 'argocd/cm-acme-http-solver-zznj7' in work queue no longer exists",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:40.528020266Z E1105 02:31:40.527962       1 controller.go:98] ingress 'argocd/cm-acme-http-solver-zznj7' in work queue no longer exists"
  },
  {
   "pattern": "cert-manager | \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"argocd-tls-7-<n>\" resource_namespace=\"argocd\" resource_kind=\"Order\" re",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:40.838653999Z E1105 02:31:40.838541       1 sync.go:73] \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"argocd-tls-7-3273522432\" resource_nam"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"argocd/argocd-tls-7-<n>\" error=\"Operation cannot b",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:40.838694064Z I1105 02:31:40.838586       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"argocd/arg"
  },
  {
   "pattern": "cert-manager | \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"argocd-tls-7-<n>-<n>\\\" not found\" logger=\"cert-manager.chal",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:43.235946308Z E1105 02:31:43.235796       1 controller.go:208] \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"argocd-tls-7-327352"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to error processing\" err=\"challenges.acme.cert-manager.io \\\"argocd-tls-7-<n>-<n>\\\" not found\" logger=\"cert-manager.orde",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:43.237948748Z E1105 02:31:43.237848       1 controller.go:167] \"re-queuing item due to error processing\" err=\"challenges.acme.cert-manager.io \\\"argocd-tls-7-327352"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\" key=\"argocd/argocd-tls\" error=\"Operatio",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:43.272823170Z I1105 02:31:43.272581       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\""
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" key=\"argocd/argocd-tls\" error=\"Operation ",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:43.277837862Z I1105 02:31:43.277723       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" k"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-issuer-acme\" key=\"app-f-prod/app-f-api-prod-tls-7",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:07:53.094107406Z I1105 03:07:53.094020       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-iss"
  },
  {
   "pattern": "cert-manager | ingress 'app-f-prod/cm-acme-http-solver-nf26f' in work queue no longer exists",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:17.694057214Z E1105 03:08:17.693966       1 controller.go:98] ingress 'app-f-prod/cm-acme-http-solver-nf26f' in work queue no longer exists"
  },
  {
   "pattern": "cert-manager | \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"app-f-api-prod-tls-7-<n>\" resource_namespace=\"app-f-prod\" resource_kind=\"Ord",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:18.076589938Z E1105 03:08:18.076543       1 sync.go:73] \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"app-f-api-prod-tls-7-4182544094\" resourc"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"app-f-prod/app-f-api-prod-tls-7-<n>\" error=\"Operation ca",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:18.076626678Z I1105 03:08:18.076567       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"app-f-prod/app-f"
  },
  {
   "pattern": "cert-manager | \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"app-f-api-prod-tls-7-<n>-<n>\\\" not found\" logger=\"cert-manager",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:19.032555823Z E1105 03:08:19.032481       1 controller.go:208] \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"app-f-api-prod-tls-7-4"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to error processing\" err=\"challenges.acme.cert-manager.io \\\"app-f-api-prod-tls-7-<n>-<n>\\\" not found\" logger=\"cert-manager",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:19.032647738Z E1105 03:08:19.032610       1 controller.go:167] \"re-queuing item due to error processing\" err=\"challenges.acme.cert-manager.io \\\"app-f-api-prod-tls-7-4"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\" key=\"app-f-prod/app-f-api-prod-tls\" error=\"Op",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:19.060078922Z I1105 03:08:19.060002       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\""
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" key=\"app-f-prod/app-f-api-prod-tls\" error=\"Oper",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:08:19.065028022Z I1105 03:08:19.064934       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" k"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-issuer-acme\" key=\"monitoring/grafana-acme-co",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:20:48.099986130Z I1105 03:20:48.099909       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-iss"
  },
  {
   "pattern": "cert-manager | ingress 'monitoring/cm-acme-http-solver-6qn6f' in work queue no longer exists",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:21:12.841968911Z E1105 03:21:12.841799       1 controller.go:98] ingress 'monitoring/cm-acme-http-solver-6qn6f' in work queue no longer exists"
  },
  {
   "pattern": "cert-manager | \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"grafana-acme-com-tls-7-<n>\" resource_namespace=\"monitoring\" resour",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:21:13.155385285Z E1105 03:21:13.155280       1 sync.go:73] \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"grafana-acme-com-tls-7-811628322\""
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"monitoring/grafana-acme-com-tls-7-<n>\" error=\"",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:21:13.155442413Z I1105 03:21:13.155350       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"monitoring"
  },
  {
   "pattern": "cert-manager | \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"grafana-acme-com-tls-7-<n>-<n>\\\" not found\" logger=\"cer",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:21:14.111195989Z E1105 03:21:14.111107       1 controller.go:208] \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"grafana-acme-co"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\" key=\"monitoring/grafana-acme-com-tl",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:21:14.138478538Z I1105 03:21:14.138368       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\""
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-issuer-acme\" key=\"logging/kibana-tls-7\" err",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:35:36.161636298Z I1105 03:35:36.161505       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-iss"
  },
  {
   "pattern": "cert-manager | ingress 'logging/cm-acme-http-solver-jlpgp' in work queue no longer exists",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:36:01.298029713Z E1105 03:36:01.297919       1 controller.go:98] ingress 'logging/cm-acme-http-solver-jlpgp' in work queue no longer exists"
  },
  {
   "pattern": "cert-manager | \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"kibana-tls-7-<n>\" resource_namespace=\"logging\" resource_kind=\"Order\" r",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:36:01.615372987Z E1105 03:36:01.615296       1 sync.go:73] \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"kibana-tls-7-436656874\" resource_name"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"logging/kibana-tls-7-<n>\" error=\"Operation cannot ",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T03:36:01.615419505Z I1105 03:36:01.615326       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"logging/ki"
  }
 ],
 "files_scanned": [
  "logs/pods/argocd/argocd_argocd-application-controller.log",
  "logs/pods/argocd/argocd_argocd-applicationset-controller.log",
  "logs/pods/argocd/argocd_argocd-dex-server.log",
  "logs/pods/argocd/argocd_argocd-notifications-controller.log",
  "logs/pods/argocd/argocd_argocd-repo-server.log",
  "logs/pods/argocd/argocd_argocd-server.log",
  "logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log",
  "logs/pods/cert-manager/cert-manager_cert-manager-webhook.log",
  "logs/pods/cert-manager/cert-manager_cert-manager.log",
  "logs/pods/coredns/kube-system_coredns.log",
  "logs/pods/elasticsearch-opensearch/logging_elasticsearch.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-cert-controller.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-webhook.log",
  "logs/pods/external-secrets/external-secrets_external-secrets.log",
  "logs/pods/fluent-bit/logging_fluent-bit.log",
  "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log",
  "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log",
  "logs/pods/keda/keda_keda-operator.log",
  "logs/pods/metallb/metallb-system_controller.log",
  "logs/pods/metallb/metallb-system_speaker.log",
  "logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-a-prod/statefulset/app-a-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "app-a-prod/statefulset/app-a-redis",
 "exec_probe": true,
 "container": "redis",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-mx:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-d-prod/statefulset/app-d-postgres-mx",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-vn:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-d-prod/statefulset/app-d-postgres-vn",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-d-prod/statefulset/app-d-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-redis:redis</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "app-d-prod/statefulset/app-d-redis",
 "exec_probe": true,
 "container": "redis",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-e-api/statefulset/app-e-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-e-api/statefulset/app-e-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-mysql:mysql</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "exec_probe": true,
 "container": "mysql",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'\n",
  "port": null,
  "timeout_s": 10,
  "period_s": 30,
  "failure_threshold": 10,
  "initial_delay_s": 90
 },
 "readiness": {
  "type": "exec",
  "path": "sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "workload": "logging/statefulset/elasticsearch",
 "exec_probe": true,
 "container": "elasticsearch",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "readiness exec timeout 1s (false failures when the node is busy)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-g-prod/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-g-prod/statefulset/app-g-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-h/deployment/app-h-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-h/deployment/app-h-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-i-prod/deployment/app-i-postgres:postgres</code></summary>

```json
{
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-i-prod/deployment/app-i-postgres",
 "exec_probe": true,
 "container": "postgres",
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ]
}
```

</details>
<details><summary><code>resilience.finished-jobs-accumulating.cluster</code></summary>

```json
{
 "total": 58,
 "failed_pods": 4,
 "failed": 3,
 "finished_without_ttl": 56,
 "succeeded_pods": 53
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-frontend:frontend</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-frontend",
 "container": "frontend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-gateway:gateway</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 2
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-gateway",
 "container": "gateway",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 6006,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 40
 },
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 6006,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-phoenix",
 "container": "phoenix",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-umami:umami</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/api/heartbeat",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/api/heartbeat",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-umami",
 "container": "umami",
 "flags": [
  "liveness and readiness share the same path (/api/heartbeat) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-backend:backend</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-b-prod/deployment/app-b-backend",
 "container": "backend",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-frontend:frontend</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-b-prod/deployment/app-b-frontend",
 "container": "frontend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-signaling:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "readiness": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "workload": "app-c-prod/deployment/app-c-signaling",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/ws/socket.io/?EIO=4&transport=polling) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-web:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-c-prod/deployment/app-c-web",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-admin:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "readiness": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "workload": "app-d-prod/deployment/app-d-admin",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/login) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-mx:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-d-prod/deployment/app-d-mx",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-vn:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-d-prod/deployment/app-d-vn",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-d-prod/deployment/app-d",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-admin:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 30
 },
 "workload": "app-f-prod/deployment/app-f-admin",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-api-server:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 5,
  "initial_delay_s": 60
 },
 "readiness": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 5,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 30,
  "initial_delay_s": 90
 },
 "workload": "app-f-prod/deployment/app-f-api-server",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/healthcheck) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-x-client:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "workload": "app-f-prod/deployment/app-f-app-x-client",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-embed:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 15
 },
 "workload": "app-f-prod/deployment/app-f-embed",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-excel-agent:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 18,
  "initial_delay_s": 10
 },
 "workload": "app-f-prod/deployment/app-f-excel-agent",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-w:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "workload": "app-f-prod/deployment/app-f-app-w",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-g-prod/deployment/app-g:app</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-g-prod/deployment/app-g",
 "container": "app",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-i-prod/deployment/app-i-api:api</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-i-prod/deployment/app-i-api",
 "container": "api",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-i-prod/deployment/app-i-web:web</code></summary>

```json
{
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "same_path": true,
 "serves_traffic": true,
 "dependency_liveness": false,
 "prod": true,
 "startup": null,
 "workload": "app-i-prod/deployment/app-i-web",
 "container": "web",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ]
}
```

</details>
<details><summary><code>resilience.no-prestop.app-a-prod/app-a-backend</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-a-prod/app-a-frontend</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-a-prod/app-a-gateway</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-gateway",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-phoenix",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-a-prod/app-a-umami</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-umami",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-b-prod/app-b-backend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-b-prod/app-b-frontend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-c-prod/app-c-signaling</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-signaling",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-c-prod/app-c-web</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-d-prod/app-d</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-d-prod/app-d-admin</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-d-prod/app-d-mx</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-mx",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-d-prod/app-d-vn</code></summary>

```json
{
 "namespace": "app-d-prod",
 "name": "app-d-vn",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-admin</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-app-x-client</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-app-x-client",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-embed</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-excel-agent</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-app-w</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-app-w",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-g-prod/app-g</code></summary>

```json
{
 "namespace": "app-g-prod",
 "name": "app-g",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-i-prod/app-i-api</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-i-prod/app-i-postgres</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-postgres",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-i-prod/app-i-web</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-c-prod/sts/app-c-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-c-prod",
  "pod": "app-c-postgres-0",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.20264358520507814,
  "memory_p95_7d_bytes": 54396723.2,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-f-prod/deploy/app-f-embed:app</code></summary>

```json
{
 "labels": {
  "namespace": "app-f-prod",
  "pod": "app-f-embed-67f6f74f6c-lb7lj",
  "container": "app"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.3117103576660156,
  "memory_p95_7d_bytes": 669392896.0,
  "container_memory_request_bytes": 2147483648.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-f-prod/sts/app-f-qdrant:qdrant</code></summary>

```json
{
 "labels": {
  "namespace": "app-f-prod",
  "pod": "app-f-qdrant-0",
  "container": "qdrant"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.191876220703125,
  "memory_p95_7d_bytes": 51506380.8,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-i-prod/deploy/app-i-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-i-prod",
  "pod": "app-i-postgres-76b69b654d-lzf4d",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2540130615234375,
  "memory_p95_7d_bytes": 68186112.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "target_cpu_utilization": 70,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-backend",
 "metric_types": [
  "cpu"
 ],
 "prod": true,
 "current_cpu_utilization": 3,
 "name": "app-a-backend",
 "cpu_only": true
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "target_cpu_utilization": 70,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-frontend",
 "metric_types": [
  "cpu"
 ],
 "prod": true,
 "current_cpu_utilization": 2,
 "name": "app-a-frontend",
 "cpu_only": true
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "has_behavior": false,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-backend",
 "desired_changes_7d": 3.0,
 "keda_owned": false,
 "min": 2,
 "prod": true,
 "name": "app-a-backend",
 "max": 6
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "has_behavior": false,
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-frontend",
 "desired_changes_7d": 4.0,
 "keda_owned": false,
 "min": 2,
 "prod": true,
 "name": "app-a-frontend",
 "max": 4
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-a-prod/app-a-gateway</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-gateway",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-phoenix",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-a-prod/app-a-umami</code></summary>

```json
{
 "namespace": "app-a-prod",
 "name": "app-a-umami",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-b-prod/app-b-backend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-b-prod/app-b-frontend</code></summary>

```json
{
 "namespace": "app-b-prod",
 "name": "app-b-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-c-prod/app-c-signaling</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-signaling",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-c-prod/app-c-web</code></summary>

```json
{
 "namespace": "app-c-prod",
 "name": "app-c-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-f-prod/app-f-embed</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-f-prod/app-f-excel-agent</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-i-prod/app-i-api</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-i-prod/app-i-web</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "namespace": "ingress-nginx",
 "external_traffic_policy": "Local",
 "target": "loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller",
 "hosts": [
  "<ip>"
 ],
 "ports": [
  80,
  443
 ],
 "name": "nginx-ingress-ingress-nginx-controller"
}
```

</details>
<details><summary><code>traffic.metallb-single-lb-service.cluster</code></summary>

```json
{
 "nodes_total": 2,
 "leader_node": "node-b",
 "mode": "layer2",
 "lb_services": 1,
 "leader_share": 1.0,
 "pinned_by_selector": false,
 "l2_available": true,
 "total_ips": 10,
 "used": 1
}
```

</details>

### 7-6. 도구 메모 (kubegap 자체에 대한 것)

1. summarize와 evaluate를 수집 뒤 한참 지나 돌리면 시간 계산이 수집 시각(taken_at 2026-11-05T17:01:01+09:00)이 아니라 실행 시각(generated_at 2026-11-06T02:12:31+09:00)을 기준으로 해요. summary.json resilience.cronjobs.rows[1].hours_since_success 9.2(실제 0.0), resilience.cronjobs.rows[0].hours_since_success 13.8(실제 4.6), findings-draft operators.unhealthy-condition app-c-coturn details.age_hours 10.4(실제 약 1.2). 그 결과 resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog이 거짓 fail이 됐어요. 인증서 days_to_expiry도 같은 기준으로 보여요.
2. inventory.signatures_version이 1.0.15에서 1.1.0으로 바뀌었는데 diff.json findings.criteria_changes에 로그 시그니처 변경이 안 들어가요. logs.signatures.metallb.speaker-error(resolved, 496번)와 logs.signatures.metallb.speaker-peer-unreachable(new, 482번)은 같은 memberlist 연결 실패인데 new와 resolved로 나뉘었어요. rule_unknown_checks에 logs.signatures만 있어요.
3. resilience.n-plus-one은 옮길 수 없는 파드까지 더한 CPU 요청 합(6.17)을 남는 노드의 allocatable(6.0)과 비교해 'CPU short'라고 써요. summary.json resilience.n_plus_one.pools[0]은 옮길 수 있는 29개가 들어간다고(needed_cpu 2.3, free_cpu 3.45) 하고, 부족한 건 pools[1]의 묶인 19개예요. evidence 첫 문장이 원인을 CPU로 잘못 읽게 해요. suggest의 '요청부터 줄여라'도 이 경우엔 해결책이 아니에요.
4. observability.stack-storage-emptydir의 why가 'OOMKill 뒤 재시작하면 0부터 시작한다'고 써요. Kubernetes 문서는 emptyDir 데이터가 컨테이너 크래시에는 남고 파드가 노드에서 지워질 때 지워진다고 해요. 컨테이너 재시작과 파드 재생성을 구분해야 해요.
5. summary.json k3s.cluster.embedded_etcd가 false인데 objects/etcdsnapshotfiles.k3s.cattle.io.json에 node-b의 etcd 스냅샷 5개가 있고 node-b 역할에 etcd가 있어요. daily 모드에서 노드 데이터가 없어서 생긴 값으로 보여요.
6. resilience.restarts-crashloop의 node_rebooted_at이 null인데, node-b의 cert-manager·cainjector·keda-operator가 같은 2026-10-28T19:25:01Z에, node-a의 argocd-repo-server·speaker·coturn 이전 컨테이너가 같은 22:06:17Z에 exit 255(Unknown)로 끝났어요. 노드 단위 동시 종료를 묶어 보지 못해서 high warn 3개가 따로 나와요.
7. security.plaintext-configmap-secret이 ConfigMap 안 .py 스크립트 본문의 이름(TOKEN, OPENAI_API_KEY, client_secret)을 fail high로 잡아요. 값을 버려서 환경 변수 조회인지 하드코딩인지 구분할 수 없어요. 스크립트 안의 이름 일치는 warn이 맞아 보여요.
8. mask가 coturn 인자 `--user=<사용자>:<비밀번호>` 형태의 자격 증명을 못 잡아요. 조치 검증자가 objects/deployments.json의 인자 값을 그대로 인용했고, 그 값이 report.md에 다섯 군데 들어갔는데 mask 결과는 0이었어요. report.md와 facts.json에서는 손으로 지웠어요. llm/writing/actions.json, draft.md, replaced.md에는 아직 남아 있어요. 조치 검증자 안내에도 인자 속 자격 증명 값을 인용하지 말라는 규칙이 필요해 보여요.

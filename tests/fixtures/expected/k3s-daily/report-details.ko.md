# kubegap 상세 리포트 — default (`default`), daily 점검

사람이 먼저 읽을 리포트는 옆의 `report.md`입니다. 이 파일에는 판정 전체와 표가 있고, `scripts/kubegap render-details`가 수집 자료와 에이전트가 사실 파일에 쓴 분석 기록을 모아 만듭니다. 다음 점검의 에이전트도 이 파일을 읽습니다. 점검 항목 id와 근거 문장은 정의에서 그대로 가져와서 영어입니다.

| 항목 | 값 |
|---|---|
| kube context / 클러스터 | `default` / default (k3s, v1.33.5+k3s1) |
| 실행 시각 / 모드 | 2026-11-07T10:22:59+09:00 / daily (수집 262.7초, 모드 때문에 건너뛴 단계 16개, 실패 0개) |
| 운영 규모 | `small` (묻지 못해 노드 수로 짐작) |
| kubegap / 점검 항목 버전 / 로그 시그니처 버전 | <kubegap> / 0.1.94 / 1.1.0 |
| 검증한 버전 범위 | Kubernetes v1.33.5+k3s1 (검증 범위 안 1.30 ~ 1.37) · Prometheus 3.7.3 (검증 범위 안 2.49 ~ 3.15) · Alertmanager 0.29.0 (검증 범위 안 0.26 ~ 0.34) · Grafana 12.2.1 (검증 범위 안 10.2 ~ 13.3) |
| 노드 / 네임스페이스 / 파드 / CRD | 2 (Ready 2) / 26 / 153 / 64 |
| 컴포넌트 (23) | actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, prometheus, prometheus-operator, reloader |
| 메트릭 저장소 | prometheus 3.7.3 retention 30d / size 0B via port-forward |
| 로그 저장소 | 없음 (Loki를 찾지 못했습니다) |
| 노드 접속 | none (a daily run does not collect node-os (collected by: full)); SSM 미등록 0대 |
| 수집 폴더 | `<snapshot>` |

## 1. 자동 판정 집계와 에이전트 조정

| 심각도(기본값) | fail | warn | 같은 모드의 지난 점검 대비 |
|---|---|---|---|
| critical | 0 | 1 | 같은 모드의 지난 점검 없음 |
| high | 6 | 14 | 같은 모드의 지난 점검 없음 |
| medium | 69 | 147 | 같은 모드의 지난 점검 없음 |
| low | 9 | 102 | 같은 모드의 지난 점검 없음 |
| info | 0 | 11 | 같은 모드의 지난 점검 없음 |

점검 항목 349개 중 판정 232개, 이 플랫폼이나 규모에서는 안 보는 것 44개, 건너뜀 9개, 이 모드에서 수집 안 함 62개, 오류 0개, 도구 없음 0개, 에이전트 판정 2개입니다. 숨긴 항목은 0개입니다.

### 1-1. 자동 판정과 최종 판정이 다른 곳

(이번 점검에서 쓰지 않음)

### 1-2. 에이전트가 다시 센 숫자

(이번 점검에서 쓰지 않음)

## 2. 지금 fail인 critical과 high (자동 판정)

| 항목 | 심각도 | 연속 횟수 | 근거 |
|---|---|---|---|
| `argocd.prune-manages-namespace-or-crd.cluster` | high |  | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-d', 'argocd/application/app-g-api' … |
| `events.tracked-warning-reasons.BackOff` | high |  | Container keeps dying and the restart interval grows (CrashLoopBackOff). 60363 occurrences total (1 events, trend over 1 snapshots [60363], flat), first 2026-10-28T22:06:36Z last 2026-11-07T01:21:42Z. Top objects … |
| `platform.k8s-version-eol.cluster` | high |  | server v1.33.5+k3s1: upstream end of life 2026-06-28, 132 days past |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | high |  | 11193 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-07T01:18:42Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio` | high |  | pod app-g-minio-0: 7d memory working set p95 / limit = 0.98 |
| `tenancy.quota-near-limit.app-l-prod/app-l-prod-quota` | high |  | app-l-prod/app-l-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi' … |

(연속 횟수는 diff.json이 있어야 나옵니다. 이번 점검에는 없습니다)

## 3. 같은 모드의 지난 점검 이후 변화

비교할 이전 daily 점검이 없습니다.

### 3-1. 왜 바뀌었나

(이번 점검에서 쓰지 않음)

## 4. 영역별 상세

(daily 점검에는 영역별 상세가 없습니다. 2절과 `report.md`를 보세요)

## 5. 없는 것 목록

| 항목 | 상태 | 심각도 | 필요한 이유 | 제안 |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | warn | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |

있어야 하는데 없는 도구 종류: backup.

## 6. 숨긴 항목, 도구 없음, 수집 안 함

- 숨긴 항목 0: 없음
- 숨김 기한이 지난 항목 0: 없음
- 도구 없음 0: 없음
- daily 모드에서 수집 안 함 62: `resources.krr-recommendation`, `controlplane.scheduler-unschedulable`, `controlplane.etcd-slow`, `node.kernel-oom-node-level`, `node.kernel-lockup`, `node.kernel-io-fs-errors`, `node.kernel-nic-events`, `node.conntrack-table-full`, `node.kernel-net-mem-pressure`, `node.cgroup-v1`, `node.sysctl-tuning`, `node.cri-not-ready`, `node.cri-exited-containers`, `node.pod-logs-large`, `node.pod-dir-large`, `node.service-restarts`, `node.reboot-required`, `node.os-updates-pending`, `node.kubelet-reserved-missing`, `node.kubelet-eviction-memory-missing`, `node.clock-unsynced-os`, `node.zombie-processes`, `node.os-not-collected`, `observability.unclassified-errors`, `security.polaris-security-danger`, `hygiene.polaris-reliability-danger`, `hygiene.deprecated-api`, `hygiene.helm-release-not-deployed`, `hygiene.helm-release-stale`, `resources.jvm-heap-vs-limit`, `node.kubelet-api-qps-low`, `resilience.backup-same-node`, `resilience.prod-db-without-backup-cronjob`, `security.plaintext-configmap-secret`, `node.docker-and-containerd`, `node.container-writable-layer-large`, `node.large-images`, `platform.k3s-secrets-encryption-off`, `platform.k3s-check-config-missing`, `platform.k3s-etcd-snapshot-stale`, `platform.k3s-etcd-snapshot-local-only`, `platform.k3s-certificate-expiring`, `platform.k3s-journald-unbounded`, `platform.k3s-apiserver-bind-all`, `node.smartmontools-missing`, `node.thermal-high`, `platform.k3s-datastore-slow`, `platform.k3s-datastore-large`, `traffic.flannel-mtu-mismatch`, `traffic.flannel-errors`, `traffic.podcidr-near-full`, `traffic.flannel-sysctl-off`, `traffic.flannel-vxlan-cross-subnet`, `traffic.flannel-drops-growing`, `traffic.flannel-node-data-missing`, `kubeproxy.node-cmd-unavailable`, `storage.local-path-over-capacity`, `storage.local-path-node-pinned`, `storage.local-path-fs-near-full`, `storage.local-path-orphan-dirs`, `storage.local-path-prod-delete-reclaim`, `storage.local-path-provisioner-unhealthy`
- 건너뛰었거나 오류가 난 점검 항목 9: `observability.log-volume-change` (skip: summary.logs.loki.volume_change missing), `observability.log-coverage-gap` (skip: summary.logs.loki.coverage missing), `observability.loki-not-ready` (skip: nothing to judge: loki not present), `observability.loki-ingest-discarded` (skip: summary.logs.agents.loki_metrics missing), `observability.promtail-dropped` (skip: summary.logs.agents.promtail missing), `observability.log-error-ratio-high` (skip: summary.logs.loki.namespaces_1h missing), `observability.unstructured-logs` (skip: summary.logs.loki.namespaces_1h missing), `traffic.ingress-5xx-ratio` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (29)), `traffic.ingress-p95-latency` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (29))
- 일부만 판정한 점검 항목 0 (판정에 필요한 자료가 없는 대상은 판정하지 않았고 통과로 세지 않았습니다): 없음
- 질의 결과가 빈 항목 5 (질의가 읽는 메트릭 이름이 모두 있으므로 그런 일이 없었다는 뜻입니다. 이름 자체가 없으면 건너뜀으로 처리합니다): `resources.oomkilled`, `resources.large-request-binpacking`, `observability.scrape-targets-down`, `node.network-errors`, `scaling.pod-pending-long`

## 7. 부록

### 7-1. 실행한 수집기와 단계

| 수집기 | 단계 | 실패 | 건너뜀 (이유) |
|---|---|---|---|
| core | 13 |  | node-os (a daily run does not collect node-os); kubelet-configz (a daily run does not collect kubelet-config); krr (a daily run does not collect workload-tools); polaris (a daily run does not collect workload-tools); pluto (a daily run does not collect workload-tools); kubent (a daily run does not collect workload-tools); helm-list (a daily run does not collect helm-releases) |
| k3s-platform | 8 |  | k3s-journal-errors (a daily run does not collect control-plane-logs); k3s-journal-stats (a daily run does not collect control-plane-logs); k3s-scheduler-unschedulable (a daily run does not collect control-plane-logs); k3s-webhook-failures (a daily run does not collect control-plane-logs); k3s-etcd-slow (a daily run does not collect control-plane-logs); kubelet-pleg (a daily run does not collect node-os); k3s-node (a daily run does not collect node-os); containerd-log (a daily run does not collect node-os) |
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
| keda | 2 |  | operator-metrics (container arg --enable-prometheus-metrics=false: no metrics is expected) |
| kube-proxy | 2 |  | proxy-mode (a daily run does not collect node-os) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| local-path-provisioner | 1 |  |  |
| metallb | 1 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| reloader | 0 |  | no collect.yaml (collector not implemented) |

이 클러스터가 제공하지 않는 종류 8개입니다. 이 종류가 필요한 점검 항목은 통과가 아니라 건너뜀으로 처리합니다: `autoscalingrunnersets.actions.github.com`, `configurationstates.metallb.io`, `nodeclaims.karpenter.sh`, `nodepools.karpenter.sh`, `servicebgpstatuses.metallb.io`, `targetgroupbindings.elbv2.k8s.aws`, `volumesnapshotclasses.snapshot.storage.k8s.io`, `volumesnapshots.snapshot.storage.k8s.io`

명령 374개, 262.7초. 실패한 단계 0개

단계는 성공했지만 그 안에서 실패한 명령 2개 (run.log): `argocd.repo-server-metrics.argocd-repo-server-848dcbb4db-jz8xs` Error from server (ServiceUnavailable): error trying to reach service: proxy error from 127.0.0.1:6443 while dialing …; `metallb.metallb-speaker-metrics.speaker-xfxlv` Unable to connect to the server: context deadline exceeded (Client.Timeout exceeded while awaiting headers)

### 7-2. 판정한 점검 항목

점검 항목 349개: disabled 44, done 232, llm 2, not-collected 62, skip 9. 불러오기 오류: 없음.

### 7-3. 로그 시그니처 일치와 분류 안 된 오류

로그 시그니처 1.1.1으로 파일 19개, 19941줄을 읽었습니다 (컴포넌트: argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, fluent-bit, grafana, ingress-nginx, keda, metallb, prometheus). 분류 안 된 오류는 202줄입니다.

| 시그니처 | 컴포넌트 | 영역 | 심각도 | 상태 | 횟수 | 처음, 마지막 | 샘플 |
|---|---|---|---|---|---|---|---|
| metallb.speaker-error | metallb | traffic | medium | warn | 42 | 2026-11-07T01:10:09Z , 2026-11-07T01:23:59Z |  |
| fluent-bit.flush-failed | fluent-bit | observability | medium | warn | 16 | 2026-11-07T00:56:41Z , 2026-11-07T01:23:41Z |  |
| fluent-bit.upstream-down | fluent-bit | observability | medium | warn | 8 | 2026-11-07T00:58:52Z , 2026-11-07T01:19:57Z |  |
| cert-manager.challenge-failed | cert-manager | security | medium | warn | 7 | 2026-11-06T02:40:26Z , 2026-11-06T02:40:27Z |  |
| metallb.speaker-peer-unreachable | metallb | traffic | low | warn | 421 | 2026-11-06T22:06:16Z , 2026-11-07T01:09:40Z |  |
| cert-manager.orphan-tls-secret | cert-manager | hygiene | low | warn | 96 | 2026-11-06T05:52:26Z , 2026-11-07T01:09:11Z |  |
| grafana.auth-failed | grafana | security | low | info | 10 | 2026-11-06T01:46:04Z , 2026-11-06T13:50:10Z |  |

| 메시지 형태 | 횟수 | 파일 |
|---|---|---|
| (없음) | | |

### 7-4. 에이전트가 직접 읽은 원본 파일

(이번 점검에서 쓰지 않음)

### 7-5. 자동 판정 전체 (모든 fail과 warn, 코드 결과 그대로)

| id | 상태 | 기본 심각도 | 근거 |
|---|---|---|---|
| `resilience.no-backup.cluster` | warn | critical | no backup tool (family backup). Alternative signals: etcd snapshots 5, backup-like CronJobs that ran in the last 7 days ['app-a-prod/app-a-postgres-backup', 'app-f-prod/app-f-postgres-backup', 'app-f-prod/app-f-postgres-mx-backup', 'app-f-prod/app-f-postgres-vn-backup' … |
| `argocd.prune-manages-namespace-or-crd.cluster` | fail | high | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-d', 'argocd/application/app-g-api', 'argocd/application/app-k', 'argocd/application/app-n', 'argocd/application/app-l-prod'] (namespaces … |
| `events.tracked-warning-reasons.BackOff` | fail | high | Container keeps dying and the restart interval grows (CrashLoopBackOff). 60363 occurrences total (1 events, trend over 1 snapshots [60363], flat), first 2026-10-28T22:06:36Z last 2026-11-07T01:21:42Z. Top objects: ['Pod/app-c-prod/app-c-coturn-549854dfcb-jgp4h'] |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.33.5+k3s1: upstream end of life 2026-06-28, 132 days past |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | fail | high | 11193 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-07T01:18:42Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio` | fail | high | pod app-g-minio-0: 7d memory working set p95 / limit = 0.98 |
| `tenancy.quota-near-limit.app-l-prod/app-l-prod-quota` | fail | high | app-l-prod/app-l-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi', 'requests.storage': '30Gi'}, used {'limits.cpu': '1800m', 'limits.memory': '2Gi' … |
| `node.disk-usage.192.168.90.101:9100:/` | warn | high | usage 0.77 |
| `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | storage emptyDir (PVC None), PVC usage None, TSDB 20.9GiB, retention 30d (size cap 0B), actual oldest sample 30.3 days, failed compactions over 7 days 0, WAL corruptions 0, corruptions at startup 0 |
| `resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller` | warn | high | 12 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resilience.restarts-crashloop.cert-manager/cert-manager-cainjector-7bf5c557bb-kbtv7:cert-manager-cainjector` | warn | high | 14 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator` | warn | high | 10 restarts, state Running, last termination Unknown (exit 255) 2026-10-28T19:25:01Z, cause class Unknown, Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.app-g-api/sts/app-g-postgres:postgres` | warn | high | pod app-g-postgres-0: throttling ratio now 0.47, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-nnsb5: throttling ratio now 0.30, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most', 'pod fluent-bit-c7fr8: throttling ratio now 0.27, no 24-hour value: under 0.001 through the day or the query was not collected … |
| `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` | warn | high | pod elasticsearch-0: throttling ratio now 0.45, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.54, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.memory-limit-near-p95.app-a-prod/sts/app-a-postgres:postgres` | warn | high | pod app-a-postgres-0: 7d memory working set p95 / limit = 0.81 |
| `resources.memory-limit-near-p95.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-nnsb5: 7d memory working set p95 / limit = 0.85', 'pod fluent-bit-c7fr8: 7d memory working set p95 / limit = 0.84'] |
| `security.plaintext-secret-env.logging/cronjob/es-index-retention:retention` | warn | high | Container retention env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/deployment/kibana:kibana` | warn | high | Container kibana env ['ELASTICSEARCH_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch` | warn | high | Container elasticsearch env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `coredns.availability.cluster` | fail | medium | replicas 1, nodes with pods 1 of 2 ({'node-b': 1}), PDB [], spread declared (antiAffinity/topologySpread) True, restarts total 1 |
| `coredns.nxdomain-ratio-high.cluster` | fail | medium | NXDOMAIN share of responses in 1h 0.701, queries per second 32.29, NXDOMAIN share of queries forwarded upstream 0.818 (upstreams ['1.1.1.1:53', '8.8.8.8:53']), pods with default ndots (5) 153, autopath False, cache hit ratio 0.8443 |
| `eso.store-static-credentials.cluster` | fail | medium | stores with static key auth ['ClusterSecretStore/aws-secret-store'] (all auth methods {'ClusterSecretStore/aws-secret-store': 'static-key(Secret)'}), providers ['aws'], ExternalSecrets 39 (prod 33) |
| `hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix` | fail | medium | image arizephoenix/phoenix:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn` | fail | medium | image coturn/coturn:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `observability.alert-firing-stale.CPUThrottlingHigh/monitoring` | fail | medium | Firing for 74.8 days (ALERTS_FOR_STATE). Labels {'namespace': 'monitoring', 'pod': 'prometheus-kube-prometheus-stack-prometheus-0', 'severity': 'info'} |
| `observability.alert-firing-stale.KubeCPUOvercommit` | fail | medium | Firing for 32.3 days (ALERTS_FOR_STATE). Labels {'severity': 'warning'} |
| `observability.alert-firing-stale.KubeJobFailed/app-a-prod` | fail | medium | ["Firing for 12.9 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-a-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'warning'}", "Firing for 9.1 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace' … |
| `observability.alert-firing-stale.KubePodCrashLooping/app-c-prod` | fail | medium | Firing for 39.9 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-c-prod', 'pod': 'app-c-coturn-549854dfcb-jgp4h', 'severity': 'warning'} |
| `observability.alert-firing-stale.KubeQuotaFullyUsed/app-l-prod` | fail | medium | Firing for 129.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'app-l-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'info'} |
| `observability.alerts-always-firing.CPUThrottlingHigh` | fail | medium | 7d firing samples 86762 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeCPUOvercommit` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeDeploymentReplicasMismatch` | fail | medium | 7d firing samples 20129 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeJobFailed` | fail | medium | 7d firing samples 40320 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodCrashLooping` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeQuotaFullyUsed` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.failure-mode-uncovered.OOMKill` | fail | medium | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.ingress-controller-metrics-missing.ingress-controller` | fail | medium | 29 ingresses, 0 ingress-controller request metric series, namespaces with app http_* metrics [], ALB CloudWatch False — per-backend gaps are the 29 golden-signals-missing (warn) findings |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | medium | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana` | fail | medium | emptyDir volumes: storage, sc-dashboard-volume, sc-datasources-volume, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus` | fail | medium | emptyDir volumes: config-out, prometheus-kube-prometheus-stack-prometheus-db, replicas 1 |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres` | fail | medium | app-a-prod/statefulset/app-a-postgres container postgres: liveness exec timeout 1s, period 15s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis` | fail | medium | app-a-prod/statefulset/app-a-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres` | fail | medium | app-c-prod/statefulset/app-c-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-mx:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres-mx container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-vn:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres-vn container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-redis:redis` | fail | medium | app-f-prod/statefulset/app-f-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-h-prod/statefulset/app-h-mysql:mysql` | fail | medium | app-h-prod/statefulset/app-h-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-h-prod/statefulset/app-h-qdrant:qdrant` | fail | medium | app-h-prod/statefulset/app-h-qdrant container qdrant: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-i-prod/statefulset/app-i-postgres:postgres` | fail | medium | app-i-prod/statefulset/app-i-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-l-prod/deployment/app-l-postgres:postgres` | fail | medium | app-l-prod/deployment/app-l-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.n-plus-one.cluster` | fail | medium | Allocatable without the largest node node-b (12.0 cores, 30.7GB): CPU 6.0 cores vs total requests 6.12 (OK), memory 30.7GB vs 23.8GB (OK). Pods on that node 48 (prod 15). Pods that fit on no other node [{'namespace': 'app-a-prod', 'pod': 'app-a-postgres-0', 'node': 'node-b', 'cpu': 0.2 … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f` | fail | medium | every replica is on one node now. replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible … |
| `resilience.replicas-same-node.app-h-prod/deployment/app-h-admin` | fail | medium | every replica is on one node now. replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible … |
| `resilience.replicas-same-node.app-h-prod/deployment/app-h-api-server` | fail | medium | every replica is on one node now. replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible … |
| `resilience.replicas-same-node.app-h-prod/deployment/app-h-app-q-client` | fail | medium | every replica is on one node now. replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible … |
| `resilience.single-node-dependency.app-c-prod/deployment/app-c-coturn` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-node-dependency.app-c-prod/statefulset/app-c-postgres` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resilience.single-node-dependency.app-h-prod/deployment/app-h-embed` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-node-dependency.app-h-prod/statefulset/app-h-mysql` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resilience.single-node-dependency.app-h-prod/statefulset/app-h-qdrant` | fail | medium | ['nodeSelector kubernetes.io/hostname=node-a'], replicas 1 |
| `resilience.single-replica-in-prod.app-a-prod/app-a-phoenix` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-a-prod/app-a-umami` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-b-prod/app-b-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-b-prod/app-b-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-coturn` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-signaling` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-c-prod/app-c-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-f-prod/app-f-mx-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-f-prod/app-f-vn-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-f-prod/app-f-worker` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-h-prod/app-h-embed` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-h-prod/app-h-excel-agent` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-api` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-postgres` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-web` | fail | medium | replicas 1, no HPA |
| `resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-embed:app` | fail | medium | pod app-h-embed-67f6f74f6c-lb7lj: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00 |
| `scaling.hpa-flapping.app-h-prod/hpa/app-h-api-server` | fail | medium | 76 desired changes over 7 days |
| `security.networkpolicy-coverage.cluster` | fail | medium | 20 of 22 user namespaces have no NetworkPolicy, of which production ['app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-i-prod', 'app-l-prod']; with: ['app-a-prod', 'argocd'] |
| `tenancy.prod-boundary-missing.app-c-prod` | fail | medium | app-c-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-f-prod` | fail | medium | app-f-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-h-prod` | fail | medium | app-h-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-i-prod` | fail | medium | app-i-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-external` | fail | medium | nodeport app-f-prod/app-f-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-mx-external` | fail | medium | nodeport app-f-prod/app-f-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-vn-external` | fail | medium | nodeport app-f-prod/app-f-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-i-prod/app-i-postgres-external` | fail | medium | nodeport app-i-prod/app-i-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.pod-not-ready.app-c-prod/app-c-coturn` | fail | medium | 24h minimum Ready ratio 0.0 (pod app-c-coturn-549854dfcb-jgp4h, about 1440 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL None |
| `argocd.app-out-of-sync-or-unhealthy.cluster` | warn | medium | Applications 18 (prod 10), OutOfSync ['argocd/application/root'] (prod []), Degraded/Missing/Unknown [] (prod []), Progressing (rolling out, not abnormal) ['argocd/application/app-c'], apps with conditions ['ExcludedResourceWarning']: ['argocd/application/app-n'], last operation failed [] |
| `argocd.default-project-wildcard.cluster` | warn | medium | AppProjects 2, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 4/18 (prod 10) |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.807s |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk` | warn | medium | image registry.lab-a.example/app-a-sandbox-adk:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c` | warn | medium | image registry.lab-a.example/app-a-sandbox-c:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express` | warn | medium | image registry.lab-a.example/app-a-sandbox-express:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go` | warn | medium | image registry.lab-a.example/app-a-sandbox-go:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs` | warn | medium | image registry.lab-a.example/app-a-sandbox-nestjs:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network` | warn | medium | image registry.lab-a.example/app-a-sandbox-network:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs` | warn | medium | image registry.lab-a.example/app-a-sandbox-nextjs:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python` | warn | medium | image registry.lab-a.example/app-a-sandbox-python:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml` | warn | medium | image registry.lab-a.example/app-a-sandbox-python-ml:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring` | warn | medium | image registry.lab-a.example/app-a-sandbox-spring:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql` | warn | medium | image registry.lab-a.example/app-a-sandbox-sql:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo` | warn | medium | image registry.lab-a.example/app-a-sandbox-todo:latest (tag latest, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.mutable-image-tag.registry/cronjob/registry-tag-cleanup:tag-cleanup` | warn | medium | image curlimages/curl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.role` | warn | medium | Label role: 7 workloads (production 0) depend on it via nodeSelector/affinity, present on 1/2 nodes — e.g. ['logging/deployment/kibana', 'monitoring/deployment/kube-prometheus-stack-grafana', 'monitoring/deployment/kube-prometheus-stack-kube-state-metrics'] and 4 more |
| `hygiene.node-label-dependency.storage` | warn | medium | Label storage: 10 workloads (production 7) depend on it via nodeSelector/affinity, present on 1/2 nodes — e.g. ['app-a-prod/statefulset/app-a-postgres', 'app-a-prod/statefulset/app-a-redis', 'app-f-prod/statefulset/app-f-postgres'] and 7 more |
| `hygiene.pvc-unbound-or-unused.cluster` | warn | medium | Non-Bound PVCs [], Released/Failed PVs [], Bound PVCs used by no pod [('default', 'data-k-quiz-db-0')] |
| `logs.signatures.cert-manager.challenge-failed` | warn | medium | 7 occurrences (2026-11-06T02:40:26Z ~ 2026-11-06T02:40:27Z), thresholds warn 5/fail 100. Files: ['logs/pods/cert-manager/cert-manager_cert-manager.log']. Samples: [] |
| `logs.signatures.fluent-bit.flush-failed` | warn | medium | 16 occurrences (2026-11-07T00:56:41Z ~ 2026-11-07T01:23:41Z), thresholds warn 10/fail 500. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: [] |
| `logs.signatures.fluent-bit.upstream-down` | warn | medium | 8 occurrences (2026-11-07T00:58:52Z ~ 2026-11-07T01:19:57Z), thresholds warn 5/fail 200. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: [] |
| `logs.signatures.metallb.speaker-error` | warn | medium | 42 occurrences (2026-11-07T01:10:09Z ~ 2026-11-07T01:23:59Z), thresholds warn 5/fail 200. Files: ['logs/pods/metallb/metallb-system_speaker.log']. Samples: [] |
| `observability.alert-firing-stale.CPUThrottlingHigh/app-g-api` | warn | medium | Firing for 3.2 days (ALERTS_FOR_STATE). Labels {'namespace': 'app-g-api', 'pod': 'app-g-postgres-0', 'severity': 'info'} |
| `observability.alert-firing-stale.CPUThrottlingHigh/logging` | warn | medium | Firing for 4.9 days (ALERTS_FOR_STATE). Labels {'namespace': 'logging', 'pod': 'elasticsearch-0', 'severity': 'info'} |
| `observability.alert-firing-stale.KubeDeploymentReplicasMismatch/app-c-prod` | warn | medium | Firing for 3.1 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-c-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'warning'} |
| `observability.fluentbit-output-errors.cluster` | warn | medium | Output errors in 1h None, failed retries (dropped) None, dropped records None, input records None -- fluent-bit metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured, so they are not really 0 |
| `observability.golden-signals-missing.app-a-prod/app-a-backend` | warn | medium | hosts ['api.app-a.lab-a.example', 'api.lab-b.example'], backends ['app-a-backend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-frontend` | warn | medium | hosts ['app-a.lab-a.example', 'lab-b.example', 'www.lab-b.example'], backends ['app-a-frontend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-phoenix` | warn | medium | hosts ['obs.lab-b.example'], backends ['app-a-phoenix'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-umami` | warn | medium | hosts ['umami.lab-b.example', 'umami.lab-j.example'], backends ['app-a-umami'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-b-prod/app-b-backend` | warn | medium | hosts ['observe-api.lab-a.example'], backends ['app-b-backend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-b-prod/app-b-frontend` | warn | medium | hosts ['observe.lab-a.example'], backends ['app-b-frontend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-c-prod/app-c-signaling-ingress` | warn | medium | hosts ['app-c.lab-a.example', 'lab-i.example', 'www.lab-i.example'], backends ['app-c-signaling-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-c-prod/app-c-web-ingress` | warn | medium | hosts ['app-c.lab-a.example', 'lab-i.example', 'www.lab-i.example'], backends ['app-c-web-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-d/app-d` | warn | medium | hosts ['lab-a.example'], backends ['app-d'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-admin-ingress` | warn | medium | hosts ['admin.lab-c.example'], backends ['app-f-admin-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-ingress` | warn | medium | hosts ['k-esg.lab-c.example'], backends ['app-f-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-mx-ingress` | warn | medium | hosts ['mx.lab-c.example'], backends ['app-f-mx-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-f-prod/app-f-vn-ingress` | warn | medium | hosts ['vn.lab-c.example'], backends ['app-f-vn-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-g-api/app-g-api` | warn | medium | hosts ['app-g-api.lab-a.example', 'app-g-cdn.lab-a.example'], backends ['app-g-api', 'app-g-minio'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-admin-ingress` | warn | medium | hosts ['app-h-admin-prod.lab-a.example', 'lab-h.example', 'www.lab-h.example'], backends ['app-h-admin-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-api-server-ingress` | warn | medium | hosts ['app-h-api-prod.lab-a.example'], backends ['app-h-api-server-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-api-server-oauth-ingress` | warn | medium | hosts ['lab-d.example', 'www.lab-d.example'], backends ['app-h-api-server-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-app-p-ingress` | warn | medium | hosts ['app-h-app-p-prod.lab-a.example', 'lab-g.example', 'www.lab-g.example'], backends ['app-h-app-p-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-app-q-client-ingress` | warn | medium | hosts ['app-h-app-q-client-prod.lab-a.example', 'lab-d.example', 'www.lab-d.example'], backends ['app-h-app-q-client-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-i-prod/app-i-ingress` | warn | medium | hosts ['app-j.lab-a.example', 'lab-e.example', 'www.lab-e.example'], backends ['app-i-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-k/app-k` | warn | medium | hosts ['app-k.lab-a.example'], backends ['app-k'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-l-prod/app-l-api` | warn | medium | hosts ['api.lab-f.example'], backends ['app-l-api'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-l-prod/app-l-web` | warn | medium | hosts ['lab-f.example'], backends ['app-l-web'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-n/app-n` | warn | medium | hosts ['app-o.lab-a.example'], backends ['app-n-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-n/app-n-auth` | warn | medium | hosts ['app-o.lab-a.example'], backends ['app-n-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.argocd/argocd-server-ingress` | warn | medium | hosts ['argocd.lab-a.example'], backends ['argocd-server'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.logging/kibana` | warn | medium | hosts ['kibana.lab-a.example'], backends ['kibana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.monitoring/monitoring-grafana-ingress` | warn | medium | hosts ['grafana.lab-a.example'], backends ['kube-prometheus-stack-grafana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.registry/registry` | warn | medium | hosts ['registry.lab-a.example'], backends ['registry'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.no-symptom-alerts.cluster` | warn | medium | 161 alert rules: symptom 0, cause 153, app metrics (assumed symptom) 7. Symptom ratio 0.0. Symptom rules: [] |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 161 alert rules, 42 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AppQClusterCPU80', 'AppQClusterMem80', 'AppQBackendDown', 'AppQFrontendDown', 'AppQPostgresDown', 'AppQGatewayDown'] and 36 more), classes {'cause': 153, 'app-cause': 1, 'app': 7} … |
| `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn` | warn | medium | Available=False (MinimumReplicasUnavailable) for 0.6 hours: Deployment does not have minimum availability. |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-mx-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-vn-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-h-prod/app-h-mysql-backup` | warn | medium | schedule '50 2 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-i-prod/app-i-postgres-backup` | warn | medium | schedule '0 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog` | warn | medium | app-a-prod/app-a-sandbox-watchdog: schedule '* * * * *' (about 0.016666666666666666h), recent Job max 50s / median 50s = 0.83x the interval (1 measured), concurrencyPolicy Forbid, active Jobs 1 |
| `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog` | warn | medium | schedule '* * * * *' (about every 0.016666666666666666h), last success 2026-11-07T01:22:50Z (0.0h ago), last schedule 2026-11-07T01:23:00Z, active Jobs 1, failed Jobs ['app-a-sandbox-watchdog-29881700', 'app-a-sandbox-watchdog-29887083'], suspend False |
| `resilience.db-probe-timeout.app-g-api/statefulset/app-g-postgres:postgres` | warn | medium | app-g-api/statefulset/app-g-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-k/deployment/app-k-postgres:postgres` | warn | medium | app-k/deployment/app-k-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 91, 'system-cluster-critical': 1, 'system-node-critical': 3}, prod pods without a class 48 of 48, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-backend` | warn | medium | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-b': 1, 'node-a': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None … |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend` | warn | medium | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-b': 1, 'node-a': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None … |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway` | warn | medium | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-a': 1, 'node-b': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None … |
| `resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller` | warn | medium | every replica is on one node now. replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres` | warn | medium | app-a-prod/statefulset/app-a-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis` | warn | medium | app-a-prod/statefulset/app-a-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn` | warn | medium | app-c-prod/deployment/app-c-coturn: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['hostNetwork'], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-signaling` | warn | medium | app-c-prod/deployment/app-c-signaling: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-web` | warn | medium | app-c-prod/deployment/app-c-web: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres` | warn | medium | app-c-prod/statefulset/app-c-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f` | warn | medium | app-f-prod/deployment/app-f: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 2, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-admin` | warn | medium | app-f-prod/deployment/app-f-admin: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-mx` | warn | medium | app-f-prod/deployment/app-f-mx: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-mx-worker` | warn | medium | app-f-prod/deployment/app-f-mx-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-vn` | warn | medium | app-f-prod/deployment/app-f-vn: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-vn-worker` | warn | medium | app-f-prod/deployment/app-f-vn-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-f-prod/deployment/app-f-worker` | warn | medium | app-f-prod/deployment/app-f-worker: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres` | warn | medium | app-f-prod/statefulset/app-f-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-mx` | warn | medium | app-f-prod/statefulset/app-f-postgres-mx: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-mx-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-vn` | warn | medium | app-f-prod/statefulset/app-f-postgres-vn: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-vn-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-redis` | warn | medium | app-f-prod/statefulset/app-f-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-redis-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-api/statefulset/app-g-minio` | warn | medium | app-g-api/statefulset/app-g-minio: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-g-minio-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-api/statefulset/app-g-postgres` | warn | medium | app-g-api/statefulset/app-g-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-g-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-admin` | warn | medium | app-h-prod/deployment/app-h-admin: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 3, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-api-server` | warn | medium | app-h-prod/deployment/app-h-api-server: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 3, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-app-p` | warn | medium | app-h-prod/deployment/app-h-app-p: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-app-q-client` | warn | medium | app-h-prod/deployment/app-h-app-q-client: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 2, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-embed` | warn | medium | app-h-prod/deployment/app-h-embed: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['extended resource nvidia.com/gpu'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-excel-agent` | warn | medium | app-h-prod/deployment/app-h-excel-agent: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/statefulset/app-h-mysql` | warn | medium | app-h-prod/statefulset/app-h-mysql: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate mysql-backup', 'local-path volumeClaimTemplate mysql-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/statefulset/app-h-qdrant` | warn | medium | app-h-prod/statefulset/app-h-qdrant: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-h-qdrant-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-i-prod/deployment/app-i` | warn | medium | app-i-prod/deployment/app-i: eligible nodes ['node-a'] (of 2 nodes), constraints ['required nodeAffinity [{"matchExpressions": [{"key": "role", "operator": "NotIn", "values": ["observability"]}]}]'], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-i-prod/statefulset/app-i-postgres` | warn | medium | app-i-prod/statefulset/app-i-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-i-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/deployment/kibana` | warn | medium | logging/deployment/kibana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/statefulset/elasticsearch` | warn | medium | logging/statefulset/elasticsearch: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana` | warn | medium | monitoring/deployment/kube-prometheus-stack-grafana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics` | warn | medium | monitoring/deployment/kube-prometheus-stack-kube-state-metrics: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator` | warn | medium | monitoring/deployment/kube-prometheus-stack-operator: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | medium | monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | medium | monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.registry/statefulset/registry` | warn | medium | registry/statefulset/registry: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate registry-data'], replicas 1, serves traffic True |
| `resilience.single-node-dependency.registry/statefulset/registry` | warn | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-backend:backend` | warn | medium | ['pod app-a-backend-79c97cbbd6-kkc2d: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03', 'pod app-a-backend-79c97cbbd6-ztv7h: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-frontend:frontend` | warn | medium | ['pod app-a-frontend-574ff75654-6sqcp: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06', 'pod app-a-frontend-574ff75654-rjbzg: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-gateway:gateway` | warn | medium | ['pod app-a-gateway-6d898d5f68-rqgsj: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod app-a-gateway-6d898d5f68-5sd56: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00'] |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-phoenix:phoenix` | warn | medium | pod app-a-phoenix-56ddc584cf-znjvs: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07 |
| `resources.cpu-request-overprovisioned.app-a-prod/sts/app-a-postgres:postgres` | warn | medium | pod app-a-postgres-0: 7d CPU p95 0.055 cores / request 0.20 cores = 0.28; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-g-api/deploy/app-g-api:api` | warn | medium | pod app-g-api-7cb685d8cf-zxqt7: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-api-server:app` | warn | medium | ['pod app-h-api-server-5d6b56f78b-xxzbl: 7d CPU p95 0.025 cores / request 0.10 cores = 0.25', 'pod app-h-api-server-5d6b56f78b-srwnk: 7d CPU p95 0.018 cores / request 0.10 cores = 0.18', 'pod app-h-api-server-5d6b56f78b-fd59m: 7d CPU p95 0.015 cores / request 0.10 cores = 0.15'] |
| `resources.cpu-request-overprovisioned.app-h-prod/sts/app-h-mysql:mysql` | warn | medium | pod app-h-mysql-0: 7d CPU p95 0.018 cores / request 0.20 cores = 0.09; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-k/deploy/app-k:web` | warn | medium | pod app-k-54c94979b5-b65b5: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.app-l-prod/deploy/app-l-postgres:postgres` | warn | medium | pod app-l-postgres-76b69b654d-lzf4d: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01; database-like: keep the request |
| `resources.cpu-request-overprovisioned.ingress-nginx/deploy/nginx-ingress-ingress-nginx-controller:controller` | warn | medium | ['pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04', 'pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-5d67c9bcfb-8fcdl: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-7ff5758fd7-gq7g7: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-85ff5bb446-lwkl6: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | pod coredns-59d4d457d-qjng8: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-7bfffcd44-fkpfm: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08 |
| `resources.cpu-request-overprovisioned.logging/deploy/kibana:kibana` | warn | medium | pod kibana-59c97cdf75-ht2zf: 7d CPU p95 0.004 cores / request 0.20 cores = 0.02 |
| `security.no-default-deny.cluster` | warn | medium | Namespaces with default-deny (ingress, empty podSelector) [], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-i-prod', 'app-l-prod']. Enforced True |
| `security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn` | warn | medium | ['hostNetwork'], containers allowing root ['coturn'] |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label ['metallb-system'], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-i-prod', 'app-l-prod']. Share of containers allowing root 0.71 (58 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 79/81, of which 37 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix', 'app-a-prod/statefulset/app-a-postgres' … |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['app-h-prod/app-h-qdrant-data-app-h-qdrant-0', 'app-a-prod/app-a-postgres-backup-pvc', 'app-a-prod/data-app-a-postgres-0', 'app-a-prod/data-app-a-redis-0', 'app-c-prod/postgres-data-app-c-postgres-0', 'app-f-prod/app-f-postgres-backup-pvc' … |
| `tenancy.burst-tenant-unbounded.app-h-prod` | warn | medium | app-h-prod (prod): 7d CPU median 0.028 cores, p95 0.102 cores, max 0.589 cores = 21.3x the median. No quota, shares nodes with prod True, nodes {'node-a': 12, 'node-b': 1}, CPU limit total 8.2 cores |
| `tenancy.prod-boundary-missing.app-b-prod` | warn | medium | app-b-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-l-prod` | warn | medium | app-l-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-without-quota.app-c-prod` | warn | medium | app-c-prod (prod): no ResourceQuota. Pods 4, CPU requests total 0.17 cores, memory requests total 0.66GB, 7d CPU p95 0.01 cores (cluster share 0.009), memory p95 0.23GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-f-prod` | warn | medium | app-f-prod (prod): no ResourceQuota. Pods 12, CPU requests total 0.49 cores, memory requests total 3.91GB, 7d CPU p95 0.027 cores (cluster share 0.024), memory p95 1.66GB, 7d max/median 1.6x. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-h-prod` | warn | medium | app-h-prod (prod): no ResourceQuota. Pods 13, CPU requests total 1.28 cores, memory requests total 8.12GB, 7d CPU p95 0.102 cores (cluster share 0.089), memory p95 5.21GB, 7d max/median 21.3x. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.app-i-prod` | warn | medium | app-i-prod (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.28GB, 7d CPU p95 0.006 cores (cluster share 0.005), memory p95 0.14GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.prod-without-quota.arc-systems` | warn | medium | arc-systems (ci): no ResourceQuota. Pods 3, CPU requests total 1.0 cores, memory requests total 2.0GB, 7d CPU p95 0.004 cores (cluster share 0.003), memory p95 0.36GB, 7d max/median Nonex. Tenants in this cluster 12, shares nodes with prod True |
| `tenancy.tenant-without-limitrange.arc-systems` | warn | medium | arc-systems (ci): no LimitRange, containers without requests 4 / without a memory limit 4 (pods 3). 7d CPU p95 0.004 cores, memory p95 0.36GB |
| `traffic.coredns-latency.cluster` | warn | medium | 1h DNS request p99 0.1457s, SERVFAIL ratio 0.0 |
| `traffic.ingress-nginx-retired.cluster` | warn | medium | ingress-nginx 1.14.0 (Deployment ingress-nginx/nginx-ingress-ingress-nginx-controller); ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes; admission webhook on |
| `hygiene.no-standard-labels.cluster` | fail | low | Of 110 workloads, share with standard labels 0.23. prod workloads without: ['app-a-prod/deployment/app-a-backend', 'app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix', 'app-a-prod/deployment/app-a-umami' … |
| `node.swap-enabled.192.168.90.102:9100` | fail | low | swap 8.0 GiB |
| `platform.k3s-server-url-stale.node-b` | fail | low | host 192.168.90.160 of --server https://192.168.90.160:6443 is not among current node IPs or names |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend` | fail | low | HPA app-a-prod/app-a-backend: share of 15 days at min 1.00, min 2 max 6, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 4.8 days ago |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend` | fail | low | HPA app-a-prod/app-a-frontend: share of 15 days at min 1.00, min 2 max 4, current CPU utilization 3% / target 70%, metrics ['cpu'], last scale 2.6 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f` | fail | low | HPA app-f-prod/app-f: share of 15 days at min 1.00, min 2 max 5, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 9.1 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f-mx` | fail | low | HPA app-f-prod/app-f-mx: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 9.1 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f-vn` | fail | low | HPA app-f-prod/app-f-vn: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 2% / target 60%, metrics ['cpu', 'memory'], last scale 9.1 days ago |
| `scaling.hpa-never-scaled.app-i-prod/deployment/app-i` | fail | low | HPA app-i-prod/app-i: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 9.1 days ago |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 10, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 10, apps whose targetRevision is a branch or HEAD 10 ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-c', 'argocd/application/app-f-kr', 'argocd/application/app-f-mx', 'argocd/application/app-f-shared', 'argocd/application/app-f-vn' … |
| `certmanager.controller-errors.cluster` | warn | low | sync calls since controller start 2654 / errors 233, ACME requests 148 by status {'200': 133, '403': 1, '201': 8, '400': 6} (4xx/5xx 7, ratio 0.0473), Ready False metric 0 |
| `certmanager.version-old.cluster` | warn | low | cert-manager 1.14.4 (components {'controller': '1/1', 'cainjector': '1/1', 'webhook': '1/1'}), webhooks with Fail 2 / webhook replicas 1 |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.487, cluster IPv6 False, queries per second 32.29. The glibc resolver always asks A and AAAA as a pair |
| `cost.k3s-node-efficiency.cluster` | warn | low | 2 nodes, allocatable 18.0 cores, 7-day p95 actual use 0.92 cores (0.051), request total 6.51 cores (7.1x actual use). Would requests still fit without the largest node: False |
| `hygiene.always-pull-with-tag.app-f-prod/deployment/app-f-vn:db-migrate` | warn | low | image registry.lab-a.example/app-f-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673 (tag tag, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex` | warn | low | image ghcr.io/dexidp/dex:v2.43.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis` | warn | low | image public.ecr.aws/docker/library/redis:8.2.2-alpine (tag tag, imagePullPolicy Always, registry public.ecr.aws) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.failed-pods-lingering.cluster` | warn | low | Failed pods 4 (prod 4), reasons {'Failed': 2, 'UnexpectedAdmissionError': 2}, namespaces {'app-a-prod': 2, 'app-h-prod': 2}, oldest 3881.6h. Example: ['app-a-prod/codex-bench', 'app-a-prod/app-a-experiment', 'app-h-prod/app-h-embed-67f6f74f6c-rlm8m', 'app-h-prod/app-h-embed-67f6f74f6c-b6kdt'] |
| `hygiene.no-ephemeral-storage-requests.cluster` | warn | low | Containers with an ephemeral-storage request 0 of 126 (0.0), without one in prod 63. emptyDirs without sizeLimit 11 (prod: []) |
| `hygiene.old-replicasets.cluster` | warn | low | Of 292 ReplicaSets, 235 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 54, '0': 3, '3': 1, '2': 1} |
| `hygiene.orphan-secrets.cluster` | warn | low | Of 139 Secrets (metric kube_secret_info), 9 unreferenced candidates: [('app-f-prod', 'app-f-prod-tls', 'kubernetes.io/tls'), ('app-h-prod', 'app-h-poca-store-prod-tls', 'kubernetes.io/tls'), ('argocd', 'ghcr-auth-secret', 'kubernetes.io/dockerconfigjson'), ('argocd', 'ghcr-pull-secret' … |
| `hygiene.unused-crds.cluster` | warn | low | 42 of 64 CRDs have zero objects (by group {'generators.external-secrets.io': 17, 'monitoring.coreos.com': 6, 'metallb.io': 5, 'acme.cert-manager.io': 1, 'eventing.keda.sh': 2, 'external-secrets.io': 4, 'keda.sh': 4, 'helm.cattle.io': 2, 'actions.summerwind.dev': 1}), 28 webhooks |
| `keda.unused.cluster` | warn | low | KEDA v2.19.0 operator 1/1, metrics-apiserver 1/1, webhooks 1/1 — ScaledObject 0, ScaledJob 0 |
| `logs.signatures.cert-manager.orphan-tls-secret` | warn | low | 96 occurrences (2026-11-06T05:52:26Z ~ 2026-11-07T01:09:11Z), thresholds warn 1/fail 1000. Files: ['logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log']. Samples: [] |
| `logs.signatures.metallb.speaker-peer-unreachable` | warn | low | 421 occurrences (2026-11-06T22:06:16Z ~ 2026-11-07T01:09:40Z), thresholds warn 60/fail 2000. Files: ['logs/pods/metallb/metallb-system_speaker.log']. Samples: [] |
| `observability.alert-metric-without-dashboard.grafana` | warn | low | 25 dashboards (170 panel metrics) — 137 of 175 alert-rule metrics have no panel: ['aggregator_unavailable_apiservice', 'aggregator_unavailable_apiservice_total', 'alertmanager_cluster_members', 'alertmanager_config_hash', 'alertmanager_config_last_reload_successful' … |
| `observability.alerts-never-fired.cluster` | warn | low | 135 of 145 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent', 'AppQClusterCPU50' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 28 of 29 ingress backends have no saturation metric (e.g. [('app-a-prod', 'app-a-backend'), ('app-a-prod', 'app-a-frontend'), ('app-a-prod', 'app-a-phoenix'), ('app-a-prod', 'app-a-umami'), ('argocd', 'argocd-server-ingress'), ('app-b-prod', 'app-b-backend')] and 22 more), namespaces with … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('discord', None), ('null', ['severity=~"info\|none"'])], receivers ['null', 'discord'], default receiver discord |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-mx:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-vn:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-g-api/statefulset/app-g-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-h-prod/statefulset/app-h-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-i-prod/statefulset/app-i-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-k/deployment/app-k-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.app-l-prod/deployment/app-l-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true \| … |
| `resilience.finished-jobs-accumulating.cluster` | warn | low | 58 Jobs (3 failed), 56 finished Jobs without ttl, 53 Succeeded pods, 4 Failed pods |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 15}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-gateway:gateway` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8080, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 5}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-phoenix:phoenix` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 6006, 'timeout_s': 1, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 40}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-a-prod/deployment/app-a-umami:umami` | warn | low | ['liveness and readiness share the same path (/api/heartbeat) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/api/heartbeat', 'port': 3000, 'timeout_s': 1, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.app-b-prod/deployment/app-b-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-b-prod/deployment/app-b-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-c-prod/deployment/app-c-signaling:app` | warn | low | ['liveness and readiness share the same path (/ws/socket.io/?EIO=4&transport=polling) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/ws/socket.io/?EIO=4&transport=polling', 'port': 3001, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3 … |
| `resilience.liveness-dependency-path.app-c-prod/deployment/app-c-web:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-admin:app` | warn | low | ['liveness and readiness share the same path (/login) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/login', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 15}, readiness {'type': 'httpGet', 'path': '/login', 'port' … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-mx:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-vn:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-f-prod/deployment/app-f:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-admin:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-api-server:app` | warn | low | ['liveness and readiness share the same path (/healthcheck) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthcheck', 'port': 8080, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 5, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-p:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-q-client:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-embed:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-excel-agent:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8080, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-i-prod/deployment/app-i:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-l-prod/deployment/app-l-api:api` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 8080, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.app-l-prod/deployment/app-l-web:web` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 15, 'failure_threshold': 3, 'initial_delay_s': 20}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.no-prestop.app-a-prod/app-a-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-gateway` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-phoenix` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-a-prod/app-a-umami` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-b-prod/app-b-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-b-prod/app-b-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-c-prod/app-c-signaling` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-c-prod/app-c-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-mx` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-f-prod/app-f-vn` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-app-p` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-app-q-client` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-embed` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-excel-agent` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-i-prod/app-i` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-postgres` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resources.memory-request-overprovisioned.app-c-prod/sts/app-c-postgres:postgres` | warn | low | pod app-c-postgres-0: 7d memory working set p95 52 MB / request 256 MB = 0.20; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-h-prod/deploy/app-h-embed:app` | warn | low | pod app-h-embed-67f6f74f6c-lb7lj: 7d memory working set p95 638 MB / request 2048 MB = 0.31 |
| `resources.memory-request-overprovisioned.app-h-prod/sts/app-h-qdrant:qdrant` | warn | low | pod app-h-qdrant-0: 7d memory working set p95 51 MB / request 256 MB = 0.20; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-l-prod/deploy/app-l-postgres:postgres` | warn | low | pod app-l-postgres-76b69b654d-lzf4d: 7d memory working set p95 65 MB / request 256 MB = 0.25; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: metrics ['cpu'], current CPU 2% / target 70% |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: metrics ['cpu'], current CPU 3% / target 70% |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 3.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 2.0 desired changes over 7 days |
| `tenancy.ci-shares-prod-nodes.node-a` | warn | low | Node node-a (pool (no-pool)): prod pods 32 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-i-prod', 'app-l-prod']) together with CI pods 1 (['arc-actions-runner-controller-5c9d9ffd65-766b6']). Heavy runners True, minutes above 90% node CPU in 7d 0.0, memory limit … |
| `tenancy.ci-shares-prod-nodes.node-b` | warn | low | Node node-b (pool (no-pool)): prod pods 15 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-i-prod', 'app-l-prod']) together with CI pods 2 (['lab-a-runner-8tt2w-cpndm', 'lab-a-runner-8tt2w-d2pwq']). Heavy runners True, minutes above 90% node CPU in 7d 0.0, memory limit … |
| `tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota` | warn | low | app-a-prod/app-a-prod-quota: requests entries in hard ['requests.memory'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota` | warn | low | app-b-prod/app-b-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-l-prod/app-l-prod-quota` | warn | low | app-l-prod/app-l-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller` | warn | low | Service ingress-nginx/nginx-ingress-ingress-nginx-controller: externalTrafficPolicy Local, ports [80, 443], addresses ['192.168.90.201'] |
| `traffic.metallb-single-lb-service.cluster` | warn | low | mode layer2, 1 LoadBalancer services, pool used 1/10, leader node-b (1.0), pinned by nodeSelectors False, 2 nodes |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-gateway` | warn | info | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-phoenix` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-umami` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-backend` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-frontend` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-signaling` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-web` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-h-prod/app-h-embed` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-h-prod/app-h-excel-agent` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-l-prod/app-l-api` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-l-prod/app-l-web` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |

표의 근거는 칸에 맞게 줄였습니다. 판정에 쓴 자료 전체는 아래에 항목별로 접혀 있고, `findings-draft.json`의 `details`와 같습니다.

<details><summary><code>argocd.prune-manages-namespace-or-crd.cluster</code></summary>

```json
{
 "applications_prod": 10,
 "prune_with_namespace_or_crd": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/app-d",
  "argocd/application/app-g-api",
  "argocd/application/app-k",
  "argocd/application/app-n",
  "argocd/application/app-l-prod"
 ]
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.BackOff</code></summary>

```json
{
 "events": 1,
 "first": "2026-10-28T22:06:36Z",
 "last": "2026-11-07T01:21:42Z",
 "meaning": "Container keeps dying and the restart interval grows (CrashLoopBackOff)",
 "objects_by_count": [
  {
   "object": "Pod/app-c-prod/app-c-coturn-549854dfcb-jgp4h",
   "occurrences": 60363
  }
 ],
 "occurrences": 60363,
 "per_snapshot": [
  60363
 ],
 "reason": "BackOff",
 "severity_hint": "high",
 "trend": "flat",
 "type": "Warning"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn</code></summary>

```json
{
 "cause": "crash (exit 255)",
 "container": "coturn",
 "crashloop": true,
 "exit_code": 255,
 "last_finished": "2026-11-07T01:18:42Z",
 "last_reason": "Error",
 "namespace": "app-c-prod",
 "node_rebooted_at": null,
 "pod": "app-c-coturn-549854dfcb-jgp4h",
 "rebooted": false,
 "restarts": 11193,
 "unhealthy_events": 0,
 "waiting": "CrashLoopBackOff"
}
```

</details>
<details><summary><code>resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio</code></summary>

```json
{
 "labels": {
  "container": "minio",
  "namespace": "app-g-api",
  "pod": "app-g-minio-0"
 },
 "value": 0.9820743560791015
}
```

</details>
<details><summary><code>tenancy.quota-near-limit.app-l-prod/app-l-prod-quota</code></summary>

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
 "max_ratio": 1.0,
 "near_limit": [
  "persistentvolumeclaims"
 ],
 "target": "app-l-prod/app-l-prod-quota",
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
<details><summary><code>node.disk-usage.192.168.90.101:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "192.168.90.101:9100",
  "mountpoint": "/"
 },
 "value": 0.768550380950461
}
```

</details>
<details><summary><code>prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "compactions_failed_7d": 0,
 "corruption_count": 0,
 "oldest_sample_days": 30.3,
 "present": true,
 "pvc_size": null,
 "pvc_used_ratio": null,
 "retention_shortfall": false,
 "retention_size": "0B",
 "retention_time": "30d",
 "storage": "emptyDir",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "tsdb_bytes": 22395275790.0,
 "wal_corruptions": 0
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller</code></summary>

```json
{
 "cause": "Unknown",
 "container": "cert-manager-controller",
 "crashloop": false,
 "exit_code": 255,
 "last_finished": "2026-10-28T19:25:01Z",
 "last_reason": "Unknown",
 "namespace": "cert-manager",
 "node_rebooted_at": null,
 "pod": "cert-manager-7c4b5b58df-4v7td",
 "rebooted": false,
 "restarts": 12,
 "unhealthy_events": 0,
 "waiting": null
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-cainjector-7bf5c557bb-kbtv7:cert-manager-cainjector</code></summary>

```json
{
 "cause": "Unknown",
 "container": "cert-manager-cainjector",
 "crashloop": false,
 "exit_code": 255,
 "last_finished": "2026-10-28T19:25:01Z",
 "last_reason": "Unknown",
 "namespace": "cert-manager",
 "node_rebooted_at": null,
 "pod": "cert-manager-cainjector-7bf5c557bb-kbtv7",
 "rebooted": false,
 "restarts": 14,
 "unhealthy_events": 0,
 "waiting": null
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator</code></summary>

```json
{
 "cause": "Unknown",
 "container": "keda-operator",
 "crashloop": false,
 "exit_code": 255,
 "last_finished": "2026-10-28T19:25:01Z",
 "last_reason": "Unknown",
 "namespace": "keda",
 "node_rebooted_at": null,
 "pod": "keda-operator-85ff5bb446-lwkl6",
 "rebooted": false,
 "restarts": 10,
 "unhealthy_events": 0,
 "waiting": null
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-g-api/sts/app-g-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-g-api",
  "pod": "app-g-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_throttle_ratio_5m": 0.47088607594936716
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
   "pod": "fluent-bit-nnsb5",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_5m": 0.30343347639484974
  }
 },
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-c7fr8",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_5m": 0.27445652173913043
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
  "cpu_throttle_ratio_5m": 0.44806707033069404
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
  "cpu_throttle_ratio_5m": 0.5418250950570341
 }
}
```

</details>
<details><summary><code>resources.memory-limit-near-p95.app-a-prod/sts/app-a-postgres:postgres</code></summary>

```json
{
 "labels": {
  "container": "postgres",
  "namespace": "app-a-prod",
  "pod": "app-a-postgres-0"
 },
 "value": 0.806501293182373
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
   "pod": "fluent-bit-nnsb5"
  },
  "value": 0.8467529296875
 },
 {
  "labels": {
   "container": "fluent-bit",
   "namespace": "logging",
   "pod": "fluent-bit-c7fr8"
  },
  "value": 0.8402954101562499
 }
]
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/cronjob/es-index-retention:retention</code></summary>

```json
{
 "container": "retention",
 "env_names": [
  "ELASTIC_PASSWORD"
 ],
 "prod": false,
 "workload": "logging/cronjob/es-index-retention"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/deployment/kibana:kibana</code></summary>

```json
{
 "container": "kibana",
 "env_names": [
  "ELASTICSEARCH_PASSWORD"
 ],
 "prod": false,
 "workload": "logging/deployment/kibana"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "container": "elasticsearch",
 "env_names": [
  "ELASTIC_PASSWORD"
 ],
 "prod": false,
 "workload": "logging/statefulset/elasticsearch"
}
```

</details>
<details><summary><code>coredns.availability.cluster</code></summary>

```json
{
 "nodes_total": 2,
 "nodes_with_pods": 1,
 "pdb": [],
 "pods_by_node": {
  "node-b": 1
 },
 "replicas": 1,
 "restarts_total": 1,
 "single_replica": true,
 "spread_declared": true
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "autopath": false,
 "cache_hit_ratio": 0.8443,
 "forward_nxdomain_ratio": 0.818,
 "metrics_available": true,
 "nxdomain_ratio": 0.701,
 "pods_default_ndots": 153,
 "qps_total": 32.29,
 "upstreams": [
  "1.1.1.1:53",
  "8.8.8.8:53"
 ]
}
```

</details>
<details><summary><code>eso.store-static-credentials.cluster</code></summary>

```json
{
 "externalsecrets": 39,
 "externalsecrets_prod": 33,
 "providers": [
  "aws"
 ],
 "stores_auth": {
  "ClusterSecretStore/aws-secret-store": "static-key(Secret)"
 },
 "stores_static_key": [
  "ClusterSecretStore/aws-secret-store"
 ]
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "container": "phoenix",
 "holder": false,
 "image": "arizephoenix/phoenix:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "IfNotPresent",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "app-a-prod/deployment/app-a-phoenix"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn</code></summary>

```json
{
 "container": "coturn",
 "holder": false,
 "image": "coturn/coturn:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/monitoring</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "prometheus",
  "instance": "192.168.90.102:10250",
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "service": "kube-prometheus-stack-kubelet",
  "severity": "info"
 },
 "value": 74.82007971064913
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
 "value": 32.279801932871344
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
   "instance": "10.42.5.127:8080",
   "job": "kube-state-metrics",
   "job_name": "app-a-sandbox-watchdog-29881700",
   "namespace": "app-a-prod",
   "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
   "service": "kube-prometheus-stack-kube-state-metrics",
   "severity": "warning"
  },
  "value": 12.874547303241712
 },
 {
  "labels": {
   "alertname": "KubeJobFailed",
   "condition": "true",
   "container": "kube-state-metrics",
   "endpoint": "http",
   "instance": "10.42.5.127:8080",
   "job": "kube-state-metrics",
   "job_name": "app-a-sandbox-watchdog-29887083",
   "namespace": "app-a-prod",
   "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
   "service": "kube-prometheus-stack-kube-state-metrics",
   "severity": "warning"
  },
  "value": 9.136352858797268
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
  "instance": "10.42.5.127:8080",
  "job": "kube-state-metrics",
  "namespace": "app-c-prod",
  "pod": "app-c-coturn-549854dfcb-jgp4h",
  "reason": "CrashLoopBackOff",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "severity": "warning",
  "uid": "faf3240b-a897-45ce-8aa9-136f745cc344"
 },
 "value": 39.85058896990838
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeQuotaFullyUsed/app-l-prod</code></summary>

```json
{
 "labels": {
  "alertname": "KubeQuotaFullyUsed",
  "container": "kube-state-metrics",
  "endpoint": "http",
  "namespace": "app-l-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "resource": "persistentvolumeclaims",
  "resourcequota": "app-l-prod-quota",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "severity": "info"
 },
 "value": 129.08431582176024
}
```

</details>
<details><summary><code>observability.alerts-always-firing.CPUThrottlingHigh</code></summary>

```json
{
 "alertname": "CPUThrottlingHigh",
 "samples_7d": 86762.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeCPUOvercommit</code></summary>

```json
{
 "alertname": "KubeCPUOvercommit",
 "samples_7d": 20160.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeDeploymentReplicasMismatch</code></summary>

```json
{
 "alertname": "KubeDeploymentReplicasMismatch",
 "samples_7d": 20129.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeJobFailed</code></summary>

```json
{
 "alertname": "KubeJobFailed",
 "samples_7d": 40320.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubePodCrashLooping</code></summary>

```json
{
 "alertname": "KubePodCrashLooping",
 "samples_7d": 20160.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeQuotaFullyUsed</code></summary>

```json
{
 "alertname": "KubeQuotaFullyUsed",
 "samples_7d": 20160.0
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.OOMKill</code></summary>

```json
{
 "importance": "critical",
 "mode": "OOMKill",
 "symptom": "pods die and requests fail or slow down"
}
```

</details>
<details><summary><code>observability.ingress-controller-metrics-missing.ingress-controller</code></summary>

```json
{
 "alb_cloudwatch_available": false,
 "ingress_controller_metric_series": 0,
 "ingresses": 29,
 "missing_lte": [
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-backend",
   "class": "nginx",
   "hosts": [
    "api.app-a.lab-a.example",
    "api.lab-b.example"
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
    "app-a.lab-a.example",
    "lab-b.example",
    "www.lab-b.example"
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
    "obs.lab-b.example"
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
    "umami.lab-b.example",
    "umami.lab-j.example"
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
    "argocd.lab-a.example"
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
    "observe-api.lab-a.example"
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
    "observe.lab-a.example"
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
    "app-c.lab-a.example",
    "lab-i.example",
    "www.lab-i.example"
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
    "app-c.lab-a.example",
    "lab-i.example",
    "www.lab-i.example"
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
   "namespace": "app-d",
   "ingress": "app-d",
   "class": "nginx",
   "hosts": [
    "lab-a.example"
   ],
   "services": [
    "app-d"
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
    "admin.lab-c.example"
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
   "ingress": "app-f-ingress",
   "class": "nginx",
   "hosts": [
    "k-esg.lab-c.example"
   ],
   "services": [
    "app-f-svc"
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
   "ingress": "app-f-mx-ingress",
   "class": "nginx",
   "hosts": [
    "mx.lab-c.example"
   ],
   "services": [
    "app-f-mx-svc"
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
   "ingress": "app-f-vn-ingress",
   "class": "nginx",
   "hosts": [
    "vn.lab-c.example"
   ],
   "services": [
    "app-f-vn-svc"
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
   "namespace": "app-g-api",
   "ingress": "app-g-api",
   "class": "nginx",
   "hosts": [
    "app-g-api.lab-a.example",
    "app-g-cdn.lab-a.example"
   ],
   "services": [
    "app-g-api",
    "app-g-minio"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-admin-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-admin-prod.lab-a.example",
    "lab-h.example",
    "www.lab-h.example"
   ],
   "services": [
    "app-h-admin-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-api-server-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-api-prod.lab-a.example"
   ],
   "services": [
    "app-h-api-server-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-api-server-oauth-ingress",
   "class": "nginx",
   "hosts": [
    "lab-d.example",
    "www.lab-d.example"
   ],
   "services": [
    "app-h-api-server-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-app-q-client-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-app-q-client-prod.lab-a.example",
    "lab-d.example",
    "www.lab-d.example"
   ],
   "services": [
    "app-h-app-q-client-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-app-p-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-app-p-prod.lab-a.example",
    "lab-g.example",
    "www.lab-g.example"
   ],
   "services": [
    "app-h-app-p-svc"
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
    "kibana.lab-a.example"
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
   "namespace": "app-i-prod",
   "ingress": "app-i-ingress",
   "class": "nginx",
   "hosts": [
    "app-j.lab-a.example",
    "lab-e.example",
    "www.lab-e.example"
   ],
   "services": [
    "app-i-svc"
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
    "grafana.lab-a.example"
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
   "namespace": "app-k",
   "ingress": "app-k",
   "class": "nginx",
   "hosts": [
    "app-k.lab-a.example"
   ],
   "services": [
    "app-k"
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
    "registry.lab-a.example"
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
   "namespace": "app-n",
   "ingress": "app-n",
   "class": "nginx",
   "hosts": [
    "app-o.lab-a.example"
   ],
   "services": [
    "app-n-workstation"
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
   "namespace": "app-n",
   "ingress": "app-n-auth",
   "class": "nginx",
   "hosts": [
    "app-o.lab-a.example"
   ],
   "services": [
    "app-n-workstation"
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
   "namespace": "app-l-prod",
   "ingress": "app-l-api",
   "class": "nginx",
   "hosts": [
    "api.lab-f.example"
   ],
   "services": [
    "app-l-api"
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
   "namespace": "app-l-prod",
   "ingress": "app-l-web",
   "class": "nginx",
   "hosts": [
    "lab-f.example"
   ],
   "services": [
    "app-l-web"
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
 "namespaces_with_app_http_metrics": []
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
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "app-a-prod/statefulset/app-a-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "container": "redis",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": null,
 "workload": "app-a-prod/statefulset/app-a-redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-mx:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-postgres-mx"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-vn:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-postgres-vn"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-redis:redis</code></summary>

```json
{
 "container": "redis",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": null,
 "workload": "app-f-prod/statefulset/app-f-redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-h-prod/statefulset/app-h-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-h-prod/statefulset/app-h-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-h-prod/statefulset/app-h-qdrant:qdrant</code></summary>

```json
{
 "container": "qdrant",
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
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/readyz",
  "port": "http",
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "app-h-prod/statefulset/app-h-qdrant"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-i-prod/statefulset/app-i-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-i-prod/statefulset/app-i-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-l-prod/deployment/app-l-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "app-l-prod/deployment/app-l-postgres"
}
```

</details>
<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "allocatable_cpu_without_largest": 6.0,
 "allocatable_memory_gb_without_largest": 30.7,
 "autoscaler": false,
 "available": true,
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
   "namespace": "app-f-prod",
   "pod": "app-f-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-f-prod",
   "pod": "app-f-postgres-mx-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-f-prod",
   "pod": "app-f-postgres-vn-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-f-prod",
   "pod": "app-f-redis-0",
   "node": "node-b",
   "cpu": 0.02,
   "memory_gb": 0.03,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-g-api",
   "pod": "app-g-minio-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-g-api",
   "pod": "app-g-postgres-0",
   "node": "node-b",
   "cpu": 0.05,
   "memory_gb": 0.12,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-h-prod",
   "pod": "app-h-mysql-0",
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
   "namespace": "app-i-prod",
   "pod": "app-i-postgres-0",
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
 "cpu_ok": true,
 "karpenter": false,
 "largest_node": "node-b",
 "largest_node_cpu": 12.0,
 "largest_node_memory_gb": 30.7,
 "memory_ok": true,
 "ok": false,
 "pods_on_largest_node": 48,
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
 "prod_pods_on_largest_node": 15,
 "requests_cpu_total": 6.12,
 "requests_memory_gb_total": 23.8,
 "tight": true
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 1,
 "nodes": {
  "node-a": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": true,
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "workload": "app-f-prod/deployment/app-f",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-h-prod/deployment/app-h-admin</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 1,
 "nodes": {
  "node-a": 3
 },
 "prod": true,
 "replicas": 3,
 "running": 3,
 "single_eligible_node": true,
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "workload": "app-h-prod/deployment/app-h-admin",
 "zones": {
  "null": 3
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-h-prod/deployment/app-h-api-server</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 1,
 "nodes": {
  "node-a": 3
 },
 "prod": true,
 "replicas": 3,
 "running": 3,
 "single_eligible_node": true,
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "workload": "app-h-prod/deployment/app-h-api-server",
 "zones": {
  "null": 3
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-h-prod/deployment/app-h-app-q-client</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 1,
 "nodes": {
  "node-a": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": true,
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ],
 "workload": "app-h-prod/deployment/app-h-app-q-client",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "replicas": 1,
 "workload": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "replicas": 1,
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-h-prod/deployment/app-h-embed</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "replicas": 1,
 "workload": "app-h-prod/deployment/app-h-embed"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-h-prod/statefulset/app-h-mysql</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "replicas": 1,
 "workload": "app-h-prod/statefulset/app-h-mysql"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-h-prod/statefulset/app-h-qdrant</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "replicas": 1,
 "workload": "app-h-prod/statefulset/app-h-qdrant"
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
<details><summary><code>resilience.single-replica-in-prod.app-f-prod/app-f-mx-worker</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-mx-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-f-prod/app-f-vn-worker</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-vn-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-f-prod/app-f-worker</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-worker",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-h-prod/app-h-embed</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-h-prod/app-h-excel-agent</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-l-prod/app-l-api</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-l-prod/app-l-postgres</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-postgres",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-l-prod/app-l-web</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-embed:app</code></summary>

```json
{
 "labels": {
  "namespace": "app-h-prod",
  "pod": "app-h-embed-67f6f74f6c-lb7lj",
  "container": "app"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.00275194964061032,
  "cpu_p95_7d_cores": 0.00137597482030516,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>scaling.hpa-flapping.app-h-prod/hpa/app-h-api-server</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "app-h-api-server",
  "instance": "10.42.5.127:8080",
  "job": "kube-state-metrics",
  "namespace": "app-h-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 76.0
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-c-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-c-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 4,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-f-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-f-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 12,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-h-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-h-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 13,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-i-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-i-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 2,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-external</code></summary>

```json
{
 "allowed_sources": {},
 "hosts": [],
 "name": "app-f-postgres-external",
 "namespace": "app-f-prod",
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "source_ranges": null,
 "target": "nodeport/app-f-prod/app-f-postgres-external",
 "type": "nodeport"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-mx-external</code></summary>

```json
{
 "allowed_sources": {},
 "hosts": [],
 "name": "app-f-postgres-mx-external",
 "namespace": "app-f-prod",
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "source_ranges": null,
 "target": "nodeport/app-f-prod/app-f-postgres-mx-external",
 "type": "nodeport"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-vn-external</code></summary>

```json
{
 "allowed_sources": {},
 "hosts": [],
 "name": "app-f-postgres-vn-external",
 "namespace": "app-f-prod",
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "source_ranges": null,
 "target": "nodeport/app-f-prod/app-f-postgres-vn-external",
 "type": "nodeport"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-i-prod/app-i-postgres-external</code></summary>

```json
{
 "allowed_sources": {},
 "hosts": [],
 "name": "app-i-postgres-external",
 "namespace": "app-i-prod",
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "source_ranges": null,
 "target": "nodeport/app-i-prod/app-i-postgres-external",
 "type": "nodeport"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.app-c-prod/app-c-coturn</code></summary>

```json
{
 "min_ready_ratio_24h": 0.0,
 "not_ready_minutes_24h": 1440,
 "pods_below_99": 1,
 "prod": true,
 "unhealthy_events": 0,
 "workload": "app-c-prod/app-c-coturn",
 "worst_pod": "app-c-coturn-549854dfcb-jgp4h"
}
```

</details>
<details><summary><code>argocd.admin-account-no-sso.cluster</code></summary>

```json
{
 "admin_enabled": true,
 "anonymous_enabled": false,
 "exec_enabled": false,
 "rbac_policy_csv_lines": 0,
 "rbac_policy_default": "",
 "sso_configured": false,
 "url": null
}
```

</details>
<details><summary><code>argocd.app-out-of-sync-or-unhealthy.cluster</code></summary>

```json
{
 "applications": 18,
 "applications_prod": 10,
 "apps_with_conditions": [
  "argocd/application/app-n"
 ],
 "conditions": [
  "ExcludedResourceWarning"
 ],
 "degraded": [],
 "last_op_failed": [],
 "out_of_sync": [
  "argocd/application/root"
 ],
 "out_of_sync_prod": [],
 "progressing": [
  "argocd/application/app-c"
 ],
 "unhealthy": [],
 "unhealthy_prod": []
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 18,
 "applications_prod": 10,
 "default_project_apps": 4,
 "projects": 2,
 "wildcard_projects": [
  "default"
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
 "value": 0.8068600000000009
}
```

</details>
<details><summary><code>eso.controller-single-replica.cluster</code></summary>

```json
{
 "cert_controller_ready": 1,
 "cert_controller_replicas": 1,
 "concurrent": "1",
 "controller_ready": 1,
 "controller_replicas": 1,
 "webhook_fail_policy": [
  "validate.externalsecret.external-secrets.io",
  "validate.secretstore.external-secrets.io",
  "validate.clustersecretstore.external-secrets.io"
 ],
 "webhook_ready": 1,
 "webhook_replicas": 1
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk</code></summary>

```json
{
 "container": "hold-adk",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-adk:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c</code></summary>

```json
{
 "container": "hold-c",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-c:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express</code></summary>

```json
{
 "container": "hold-express",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-express:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go</code></summary>

```json
{
 "container": "hold-go",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-go:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs</code></summary>

```json
{
 "container": "hold-nestjs",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-nestjs:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network</code></summary>

```json
{
 "container": "hold-network",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-network:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs</code></summary>

```json
{
 "container": "hold-nextjs",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-nextjs:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "container": "hold-python",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-python:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml</code></summary>

```json
{
 "container": "hold-python-ml",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-python-ml:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring</code></summary>

```json
{
 "container": "hold-spring",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-spring:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql</code></summary>

```json
{
 "container": "hold-sql",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-sql:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo</code></summary>

```json
{
 "container": "hold-todo",
 "holder": true,
 "image": "registry.lab-a.example/app-a-sandbox-todo:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "latest",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.registry/cronjob/registry-tag-cleanup:tag-cleanup</code></summary>

```json
{
 "container": "tag-cleanup",
 "image": "curlimages/curl:latest",
 "mutable": true,
 "prod": false,
 "pull_policy": "Always",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "registry/cronjob/registry-tag-cleanup"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.role</code></summary>

```json
{
 "key": "role",
 "nodes_total": 2,
 "nodes_with_label": 1,
 "prod_workloads": 0,
 "well_known": false,
 "workload_count": 7,
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
 "key": "storage",
 "nodes_total": 2,
 "nodes_with_label": 1,
 "prod_workloads": 7,
 "well_known": false,
 "workload_count": 10,
 "workloads": [
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-f-prod/statefulset/app-f-postgres",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-f-prod/statefulset/app-f-redis",
  "app-g-api/statefulset/app-g-minio",
  "app-g-api/statefulset/app-g-postgres",
  "app-i-prod/statefulset/app-i-postgres",
  "app-g-api/cronjob/app-g-postgres-backup"
 ]
}
```

</details>
<details><summary><code>hygiene.pvc-unbound-or-unused.cluster</code></summary>

```json
{
 "pv_released": [],
 "pvc_unbound": [],
 "pvc_unused": [
  {
   "namespace": "default",
   "name": "data-k-quiz-db-0",
   "prod": false
  }
 ]
}
```

</details>
<details><summary><code>logs.signatures.cert-manager.challenge-failed</code></summary>

```json
{
 "count": 7,
 "first": "2026-11-06T02:40:26Z",
 "last": "2026-11-06T02:40:27Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/cert-manager/cert-manager_cert-manager.log": 7
 },
 "samples": []
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.flush-failed</code></summary>

```json
{
 "count": 16,
 "first": "2026-11-07T00:56:41Z",
 "last": "2026-11-07T01:23:41Z",
 "warn_at": 10,
 "fail_at": 500,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 16
 },
 "samples": []
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.upstream-down</code></summary>

```json
{
 "count": 8,
 "first": "2026-11-07T00:58:52Z",
 "last": "2026-11-07T01:19:57Z",
 "warn_at": 5,
 "fail_at": 200,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 8
 },
 "samples": []
}
```

</details>
<details><summary><code>logs.signatures.metallb.speaker-error</code></summary>

```json
{
 "count": 42,
 "first": "2026-11-07T01:10:09Z",
 "last": "2026-11-07T01:23:59Z",
 "warn_at": 5,
 "fail_at": 200,
 "files": {
  "logs/pods/metallb/metallb-system_speaker.log": 42
 },
 "samples": []
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/app-g-api</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "postgres",
  "instance": "192.168.90.102:10250",
  "namespace": "app-g-api",
  "pod": "app-g-postgres-0",
  "service": "kube-prometheus-stack-kubelet",
  "severity": "info"
 },
 "value": 3.1923019328713416
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/logging</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "elasticsearch",
  "instance": "192.168.90.102:10250",
  "namespace": "logging",
  "pod": "elasticsearch-0",
  "service": "kube-prometheus-stack-kubelet",
  "severity": "info"
 },
 "value": 4.851676932871341
}
```

</details>
<details><summary><code>observability.alert-firing-stale.KubeDeploymentReplicasMismatch/app-c-prod</code></summary>

```json
{
 "labels": {
  "alertname": "KubeDeploymentReplicasMismatch",
  "container": "kube-state-metrics",
  "deployment": "app-c-coturn",
  "endpoint": "http",
  "instance": "10.42.5.127:8080",
  "job": "kube-state-metrics",
  "namespace": "app-c-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "severity": "warning"
 },
 "value": 3.0939917476861565
}
```

</details>
<details><summary><code>observability.fluentbit-output-errors.cluster</code></summary>

```json
{
 "dropped_records_1h": null,
 "metrics_scraped": false,
 "output_errors_1h": null,
 "records_in_1h": null,
 "retries_failed_1h": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-backend</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "api.app-a.lab-a.example",
  "api.lab-b.example"
 ],
 "ingress": "app-a-backend",
 "namespace": "app-a-prod",
 "services": [
  "app-a-backend"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-frontend</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-a.lab-a.example",
  "lab-b.example",
  "www.lab-b.example"
 ],
 "ingress": "app-a-frontend",
 "namespace": "app-a-prod",
 "services": [
  "app-a-frontend"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "obs.lab-b.example"
 ],
 "ingress": "app-a-phoenix",
 "namespace": "app-a-prod",
 "services": [
  "app-a-phoenix"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-umami</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "umami.lab-b.example",
  "umami.lab-j.example"
 ],
 "ingress": "app-a-umami",
 "namespace": "app-a-prod",
 "services": [
  "app-a-umami"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-backend</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "observe-api.lab-a.example"
 ],
 "ingress": "app-b-backend",
 "namespace": "app-b-prod",
 "services": [
  "app-b-backend"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-frontend</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "observe.lab-a.example"
 ],
 "ingress": "app-b-frontend",
 "namespace": "app-b-prod",
 "services": [
  "app-b-frontend"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-signaling-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.lab-a.example",
  "lab-i.example",
  "www.lab-i.example"
 ],
 "ingress": "app-c-signaling-ingress",
 "namespace": "app-c-prod",
 "services": [
  "app-c-signaling-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-web-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.lab-a.example",
  "lab-i.example",
  "www.lab-i.example"
 ],
 "ingress": "app-c-web-ingress",
 "namespace": "app-c-prod",
 "services": [
  "app-c-web-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d/app-d</code></summary>

```json
{
 "hosts": [
  "lab-a.example"
 ],
 "ingress": "app-d",
 "namespace": "app-d",
 "services": [
  "app-d"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-admin-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "admin.lab-c.example"
 ],
 "ingress": "app-f-admin-ingress",
 "namespace": "app-f-prod",
 "services": [
  "app-f-admin-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "k-esg.lab-c.example"
 ],
 "ingress": "app-f-ingress",
 "namespace": "app-f-prod",
 "services": [
  "app-f-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-mx-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "mx.lab-c.example"
 ],
 "ingress": "app-f-mx-ingress",
 "namespace": "app-f-prod",
 "services": [
  "app-f-mx-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-vn-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "vn.lab-c.example"
 ],
 "ingress": "app-f-vn-ingress",
 "namespace": "app-f-prod",
 "services": [
  "app-f-vn-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-g-api/app-g-api</code></summary>

```json
{
 "hosts": [
  "app-g-api.lab-a.example",
  "app-g-cdn.lab-a.example"
 ],
 "ingress": "app-g-api",
 "namespace": "app-g-api",
 "services": [
  "app-g-api",
  "app-g-minio"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h-prod/app-h-admin-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-h-admin-prod.lab-a.example",
  "lab-h.example",
  "www.lab-h.example"
 ],
 "ingress": "app-h-admin-ingress",
 "namespace": "app-h-prod",
 "services": [
  "app-h-admin-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h-prod/app-h-api-server-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-h-api-prod.lab-a.example"
 ],
 "ingress": "app-h-api-server-ingress",
 "namespace": "app-h-prod",
 "services": [
  "app-h-api-server-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h-prod/app-h-api-server-oauth-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "lab-d.example",
  "www.lab-d.example"
 ],
 "ingress": "app-h-api-server-oauth-ingress",
 "namespace": "app-h-prod",
 "services": [
  "app-h-api-server-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h-prod/app-h-app-p-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-h-app-p-prod.lab-a.example",
  "lab-g.example",
  "www.lab-g.example"
 ],
 "ingress": "app-h-app-p-ingress",
 "namespace": "app-h-prod",
 "services": [
  "app-h-app-p-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h-prod/app-h-app-q-client-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-h-app-q-client-prod.lab-a.example",
  "lab-d.example",
  "www.lab-d.example"
 ],
 "ingress": "app-h-app-q-client-ingress",
 "namespace": "app-h-prod",
 "services": [
  "app-h-app-q-client-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-i-prod/app-i-ingress</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-j.lab-a.example",
  "lab-e.example",
  "www.lab-e.example"
 ],
 "ingress": "app-i-ingress",
 "namespace": "app-i-prod",
 "services": [
  "app-i-svc"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-k/app-k</code></summary>

```json
{
 "hosts": [
  "app-k.lab-a.example"
 ],
 "ingress": "app-k",
 "namespace": "app-k",
 "services": [
  "app-k"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-l-prod/app-l-api</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "api.lab-f.example"
 ],
 "ingress": "app-l-api",
 "namespace": "app-l-prod",
 "services": [
  "app-l-api"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-l-prod/app-l-web</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "lab-f.example"
 ],
 "ingress": "app-l-web",
 "namespace": "app-l-prod",
 "services": [
  "app-l-web"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-n/app-n</code></summary>

```json
{
 "hosts": [
  "app-o.lab-a.example"
 ],
 "ingress": "app-n",
 "namespace": "app-n",
 "services": [
  "app-n-workstation"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-n/app-n-auth</code></summary>

```json
{
 "hosts": [
  "app-o.lab-a.example"
 ],
 "ingress": "app-n-auth",
 "namespace": "app-n",
 "services": [
  "app-n-workstation"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.argocd/argocd-server-ingress</code></summary>

```json
{
 "hosts": [
  "argocd.lab-a.example"
 ],
 "ingress": "argocd-server-ingress",
 "namespace": "argocd",
 "services": [
  "argocd-server"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.logging/kibana</code></summary>

```json
{
 "hosts": [
  "kibana.lab-a.example"
 ],
 "ingress": "kibana",
 "namespace": "logging",
 "services": [
  "kibana"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.monitoring/monitoring-grafana-ingress</code></summary>

```json
{
 "hosts": [
  "grafana.lab-a.example"
 ],
 "ingress": "monitoring-grafana-ingress",
 "namespace": "monitoring",
 "services": [
  "kube-prometheus-stack-grafana"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.registry/registry</code></summary>

```json
{
 "hosts": [
  "registry.lab-a.example"
 ],
 "ingress": "registry",
 "namespace": "registry",
 "services": [
  "registry"
 ],
 "source": null
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
  "AppQClusterCPU80",
  "AppQClusterMem80",
  "AppQBackendDown",
  "AppQFrontendDown",
  "AppQPostgresDown",
  "AppQGatewayDown",
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
  "PrometheusRuleFailures",
  "PrometheusTargetSyncFailure",
  "PrometheusErrorSendingAlertsToAnyAlertmanager"
 ]
}
```

</details>
<details><summary><code>operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn</code></summary>

```json
{
 "age_hours": 0.6,
 "condition": "Available",
 "kind": "deployments",
 "message": "Deployment does not have minimum availability.",
 "name": "app-c-coturn",
 "namespace": "app-c-prod",
 "reason": "MinimumReplicasUnavailable",
 "status": "False"
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-f-prod/app-f-postgres-backup</code></summary>

```json
{
 "active_deadline_s": null,
 "active_jobs": 0,
 "backoff_limit": null,
 "concurrency_policy": "Allow",
 "pod_failure_policy": false,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "prod": true,
 "schedule": "30 3 * * *",
 "starting_deadline_s": null,
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-backup",
 "ttl_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-f-prod/app-f-postgres-mx-backup</code></summary>

```json
{
 "active_deadline_s": null,
 "active_jobs": 0,
 "backoff_limit": null,
 "concurrency_policy": "Allow",
 "pod_failure_policy": false,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "prod": true,
 "schedule": "30 3 * * *",
 "starting_deadline_s": null,
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-mx-backup",
 "ttl_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-f-prod/app-f-postgres-vn-backup</code></summary>

```json
{
 "active_deadline_s": null,
 "active_jobs": 0,
 "backoff_limit": null,
 "concurrency_policy": "Allow",
 "pod_failure_policy": false,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "prod": true,
 "schedule": "30 3 * * *",
 "starting_deadline_s": null,
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-vn-backup",
 "ttl_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-h-prod/app-h-mysql-backup</code></summary>

```json
{
 "active_deadline_s": null,
 "active_jobs": 0,
 "backoff_limit": null,
 "concurrency_policy": "Allow",
 "pod_failure_policy": false,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "prod": true,
 "schedule": "50 2 * * *",
 "starting_deadline_s": null,
 "suspend": false,
 "target": "app-h-prod/app-h-mysql-backup",
 "ttl_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-i-prod/app-i-postgres-backup</code></summary>

```json
{
 "active_deadline_s": null,
 "active_jobs": 0,
 "backoff_limit": null,
 "concurrency_policy": "Allow",
 "pod_failure_policy": false,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "prod": true,
 "schedule": "0 3 * * *",
 "starting_deadline_s": null,
 "suspend": false,
 "target": "app-i-prod/app-i-postgres-backup",
 "ttl_s": null
}
```

</details>
<details><summary><code>resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog</code></summary>

```json
{
 "active_jobs": 1,
 "concurrency_policy": "Forbid",
 "interval_h": 0.016666666666666666,
 "jobs_timed": 1,
 "max_job_duration_s": 50,
 "median_job_duration_s": 50,
 "runtime_over_interval": 0.83,
 "schedule": "* * * * *",
 "suspend": false,
 "target": "app-a-prod/app-a-sandbox-watchdog"
}
```

</details>
<details><summary><code>resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog</code></summary>

```json
{
 "active_jobs": 1,
 "failed_jobs": [
  "app-a-sandbox-watchdog-29881700",
  "app-a-sandbox-watchdog-29887083"
 ],
 "hours_since_success": 0.0,
 "interval_h": 0.016666666666666666,
 "last_schedule": "2026-11-07T01:23:00Z",
 "last_success": "2026-11-07T01:22:50Z",
 "schedule": "* * * * *",
 "stale": false,
 "suspend": false,
 "target": "app-a-prod/app-a-sandbox-watchdog"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-g-api/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "startup": null,
 "workload": "app-g-api/statefulset/app-g-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-k/deployment/app-k-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "app-k/deployment/app-k-postgres"
}
```

</details>
<details><summary><code>resilience.priority-inversion.cluster</code></summary>

```json
{
 "inversion": [],
 "no_user_classes_with_prod": true,
 "nonprod_max_priority": 0,
 "pods_by_class": {
  "(none, 0)": 91,
  "system-cluster-critical": 1,
  "system-node-critical": 3
 },
 "preempted_events": 0,
 "prod_max_priority": 0,
 "prod_pods": 48,
 "prod_pods_without_class": 48,
 "user_classes": []
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "app-a-prod/deployment/app-a-backend",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "app-a-prod/deployment/app-a-frontend",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-a": 1,
  "node-b": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "app-a-prod/deployment/app-a-gateway",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 2
 },
 "prod": false,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-a-prod/statefulset/app-a-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-a-prod/statefulset/app-a-redis"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "hostNetwork"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": false,
 "workload": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-signaling</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-c-prod/deployment/app-c-signaling"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-web</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-c-prod/deployment/app-c-web"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate postgres-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 2,
 "serves_traffic": true,
 "workload": "app-f-prod/deployment/app-f"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/deployment/app-f-admin"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-mx</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/deployment/app-f-mx"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-mx-worker</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": false,
 "workload": "app-f-prod/deployment/app-f-mx-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-vn</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/deployment/app-f-vn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-vn-worker</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": false,
 "workload": "app-f-prod/deployment/app-f-vn-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-worker</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": false,
 "workload": "app-f-prod/deployment/app-f-worker"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-postgres-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/statefulset/app-f-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-mx</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-postgres-mx-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/statefulset/app-f-postgres-mx"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-vn</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-postgres-vn-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/statefulset/app-f-postgres-vn"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-redis</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-redis-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-f-prod/statefulset/app-f-redis"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-api/statefulset/app-g-minio</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-g-minio-data"
 ],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-g-api/statefulset/app-g-minio"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-api/statefulset/app-g-postgres</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-g-postgres-data"
 ],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-g-api/statefulset/app-g-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-admin</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 3,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-admin"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-api-server</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 3,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-api-server"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-app-p</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-app-p"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-app-q-client</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 2,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-app-q-client"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-embed</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "extended resource nvidia.com/gpu"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-embed"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/deployment/app-h-excel-agent</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-h-prod/deployment/app-h-excel-agent"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/statefulset/app-h-mysql</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate mysql-backup",
  "local-path volumeClaimTemplate mysql-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-h-prod/statefulset/app-h-mysql"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-h-prod/statefulset/app-h-qdrant</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-h-qdrant-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-h-prod/statefulset/app-h-qdrant"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-i-prod/deployment/app-i</code></summary>

```json
{
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ],
 "eligible_nodes": [
  "node-a"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-i-prod/deployment/app-i"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-i-prod/statefulset/app-i-postgres</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate app-i-postgres-data"
 ],
 "prod": true,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "app-i-prod/statefulset/app-i-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/deployment/kibana</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "logging/deployment/kibana"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/statefulset/elasticsearch</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "logging/statefulset/elasticsearch"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/deployment/kube-prometheus-stack-kube-state-metrics"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/deployment/kube-prometheus-stack-operator"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.registry/statefulset/registry</code></summary>

```json
{
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ],
 "eligible_nodes": [
  "node-b"
 ],
 "nodes_total": 2,
 "pin_reasons": [
  "local-path volumeClaimTemplate registry-data"
 ],
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "registry/statefulset/registry"
}
```

</details>
<details><summary><code>resilience.single-node-dependency.registry/statefulset/registry</code></summary>

```json
{
 "prod": false,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
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
   "cpu_request_p95_ratio_7d": 0.02948953382089552,
   "cpu_p95_7d_cores": 0.002948953382089552,
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
   "cpu_request_p95_ratio_7d": 0.02054791622289717,
   "cpu_p95_7d_cores": 0.002054791622289717,
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
   "cpu_request_p95_ratio_7d": 0.05888426441704926,
   "cpu_p95_7d_cores": 0.0058884264417049265,
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
   "cpu_request_p95_ratio_7d": 0.05524428289724947,
   "cpu_p95_7d_cores": 0.005524428289724947,
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
   "cpu_request_p95_ratio_7d": 0.0020040496206925646,
   "cpu_p95_7d_cores": 0.00020040496206925646,
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
   "cpu_request_p95_ratio_7d": 0.0011986974821001234,
   "cpu_p95_7d_cores": 0.00011986974821001235,
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
  "cpu_request_p95_ratio_7d": 0.06912067895052312,
  "cpu_p95_7d_cores": 0.006912067895052313,
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
  "cpu_request_p95_ratio_7d": 0.27681604075756405,
  "cpu_p95_7d_cores": 0.05536320815151281,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-g-api/deploy/app-g-api:api</code></summary>

```json
{
 "labels": {
  "namespace": "app-g-api",
  "pod": "app-g-api-7cb685d8cf-zxqt7",
  "container": "api"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.014339406303979866,
  "cpu_p95_7d_cores": 0.0014339406303979867,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-api-server:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-5d6b56f78b-xxzbl",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.252462648215657,
   "cpu_p95_7d_cores": 0.025246264821565702,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-5d6b56f78b-srwnk",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.18133510806234315,
   "cpu_p95_7d_cores": 0.018133510806234317,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-5d6b56f78b-fd59m",
   "container": "app"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.1514161296005065,
   "cpu_p95_7d_cores": 0.01514161296005065,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-h-prod/sts/app-h-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "app-h-prod",
  "pod": "app-h-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.09166758997659344,
  "cpu_p95_7d_cores": 0.01833351799531869,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-k/deploy/app-k:web</code></summary>

```json
{
 "labels": {
  "namespace": "app-k",
  "pod": "app-k-54c94979b5-b65b5",
  "container": "web"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.010823194832171304,
  "cpu_p95_7d_cores": 0.0010823194832171304,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-l-prod/deploy/app-l-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-l-prod",
  "pod": "app-l-postgres-76b69b654d-lzf4d",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.014394893551776299,
  "cpu_p95_7d_cores": 0.0014394893551776299,
  "container_cpu_request_cores": 0.1
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
   "cpu_request_p95_ratio_7d": 0.04379937828733188,
   "cpu_p95_7d_cores": 0.004379937828733188,
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
   "cpu_request_p95_ratio_7d": 0.04219969635933342,
   "cpu_p95_7d_cores": 0.004219969635933342,
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
  "cpu_request_p95_ratio_7d": 0.003143914963401943,
  "cpu_p95_7d_cores": 0.00031439149634019433,
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
  "cpu_request_p95_ratio_7d": 0.03300247666978333,
  "cpu_p95_7d_cores": 0.0033002476669783333,
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
  "cpu_request_p95_ratio_7d": 0.018019126984011053,
  "cpu_p95_7d_cores": 0.0018019126984011053,
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
  "cpu_request_p95_ratio_7d": 0.09886240429700137,
  "cpu_p95_7d_cores": 0.009886240429700138,
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
  "cpu_request_p95_ratio_7d": 0.07974813967119745,
  "cpu_p95_7d_cores": 0.007974813967119746,
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
  "cpu_request_p95_ratio_7d": 0.019503324276173867,
  "cpu_p95_7d_cores": 0.0039006648552347735,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>security.no-default-deny.cluster</code></summary>

```json
{
 "default_deny_ingress_namespaces": [],
 "enforced": true,
 "policies": 8,
 "prod_without_default_deny": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-f-prod",
  "app-h-prod",
  "app-i-prod",
  "app-l-prod"
 ]
}
```

</details>
<details><summary><code>security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "flags": [
  "hostNetwork"
 ],
 "host_access": true,
 "root_allowed_containers": [
  "coturn"
 ],
 "severe": false,
 "system": false,
 "workload": "app-c-prod/deployment/app-c-coturn"
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
  "app-f-prod",
  "app-h-prod",
  "app-i-prod",
  "app-l-prod"
 ],
 "psa_enforced_namespaces": [
  "metallb-system"
 ],
 "root_allowed_prod": [
  "app-a-prod/deployment/app-a-backend",
  "app-a-prod/deployment/app-a-phoenix",
  "app-a-prod/deployment/app-a-umami",
  "app-a-prod/deployment/app-m",
  "app-b-prod/deployment/app-b-backend",
  "app-c-prod/deployment/app-c-coturn",
  "app-c-prod/deployment/app-c-signaling",
  "app-c-prod/deployment/app-c-web",
  "app-f-prod/deployment/app-f",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-mx",
  "app-f-prod/deployment/app-f-mx-worker",
  "app-f-prod/deployment/app-f-sales-bot",
  "app-f-prod/deployment/app-f-vn",
  "app-f-prod/deployment/app-f-vn-worker",
  "app-f-prod/deployment/app-f-worker",
  "app-h-prod/deployment/app-h-admin",
  "app-h-prod/deployment/app-h-api-server",
  "app-h-prod/deployment/app-h-app-q-client",
  "app-h-prod/deployment/app-h-embed",
  "app-h-prod/deployment/app-h-excel-agent",
  "app-h-prod/deployment/app-h-app-p",
  "app-i-prod/deployment/app-i",
  "app-l-prod/deployment/app-l-postgres",
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-c-prod/statefulset/app-c-postgres",
  "app-f-prod/statefulset/app-f-postgres",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-f-prod/statefulset/app-f-redis",
  "app-h-prod/statefulset/app-h-mysql",
  "app-h-prod/statefulset/app-h-qdrant",
  "app-i-prod/statefulset/app-i-postgres",
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-a-prod/cronjob/marketing-autopost-en",
  "app-a-prod/cronjob/marketing-autopost-ja",
  "app-a-prod/cronjob/marketing-digest-day",
  "app-a-prod/cronjob/marketing-digest-month",
  "app-a-prod/cronjob/marketing-digest-week",
  "app-a-prod/cronjob/marketing-radar-global",
  "app-a-prod/cronjob/marketing-radar-global-eu",
  "app-a-prod/cronjob/marketing-radar-japan",
  "app-a-prod/cronjob/marketing-radar-japan-noon",
  "app-a-prod/cronjob/umami-report-day",
  "app-a-prod/cronjob/umami-report-month",
  "app-a-prod/cronjob/umami-report-week",
  "app-f-prod/cronjob/app-f-ga4-digest-day",
  "app-f-prod/cronjob/app-f-ga4-digest-month",
  "app-f-prod/cronjob/app-f-ga4-digest-week",
  "app-f-prod/cronjob/app-f-policy-radar",
  "app-f-prod/cronjob/app-f-postgres-backup",
  "app-f-prod/cronjob/app-f-postgres-mx-backup",
  "app-f-prod/cronjob/app-f-postgres-vn-backup",
  "app-h-prod/cronjob/app-h-mysql-backup",
  "app-i-prod/cronjob/app-i-postgres-backup"
 ],
 "root_allowed_ratio": 0.71
}
```

</details>
<details><summary><code>security.rbac-wildcard.argocd-application-controller</code></summary>

```json
{
 "bound": true,
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "argocd",
   "name": "argocd-application-controller"
  }
 ],
 "clusterrole": "argocd-application-controller",
 "prod": false
}
```

</details>
<details><summary><code>security.sa-token-mounted-without-rbac.cluster</code></summary>

```json
{
 "automount_false_sa": 1,
 "service_accounts": 91,
 "token_mounted": 79,
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
  "app-f-prod/deployment/app-f",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-mx",
  "app-f-prod/deployment/app-f-mx-worker",
  "app-f-prod/statefulset/app-f-postgres",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-f-prod/statefulset/app-f-redis",
  "app-f-prod/deployment/app-f-vn",
  "app-f-prod/deployment/app-f-vn-worker",
  "app-f-prod/deployment/app-f-worker",
  "app-h-prod/deployment/app-h-admin",
  "app-h-prod/deployment/app-h-api-server",
  "app-h-prod/deployment/app-h-app-q-client",
  "app-h-prod/deployment/app-h-embed",
  "app-h-prod/deployment/app-h-excel-agent",
  "app-h-prod/statefulset/app-h-mysql",
  "app-h-prod/deployment/app-h-app-p",
  "app-h-prod/statefulset/app-h-qdrant",
  "app-i-prod/deployment/app-i",
  "app-i-prod/statefulset/app-i-postgres",
  "app-l-prod/deployment/app-l-api",
  "app-l-prod/deployment/app-l-postgres",
  "app-l-prod/deployment/app-l-web"
 ],
 "workloads": 81
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
 "prod_db_delete_reclaim": [
  "app-h-prod/app-h-qdrant-data-app-h-qdrant-0",
  "app-a-prod/app-a-postgres-backup-pvc",
  "app-a-prod/data-app-a-postgres-0",
  "app-a-prod/data-app-a-redis-0",
  "app-c-prod/postgres-data-app-c-postgres-0",
  "app-f-prod/app-f-postgres-backup-pvc",
  "app-f-prod/app-f-postgres-data-app-f-postgres-0",
  "app-f-prod/app-f-postgres-mx-backup-pvc",
  "app-f-prod/app-f-postgres-mx-data-app-f-postgres-mx-0",
  "app-f-prod/app-f-postgres-vn-backup-pvc",
  "app-f-prod/app-f-postgres-vn-data-app-f-postgres-vn-0",
  "app-f-prod/app-f-redis-data-app-f-redis-0",
  "app-h-prod/mysql-backup-app-h-mysql-0",
  "app-h-prod/mysql-data-app-h-mysql-0",
  "app-i-prod/app-i-postgres-backup-pvc",
  "app-i-prod/app-i-postgres-data-app-i-postgres-0",
  "app-l-prod/app-l-postgres-data"
 ],
 "rows": [
  {
   "namespace": "app-h-prod",
   "name": "app-h-qdrant-data-app-h-qdrant-0",
   "target": "app-h-prod/app-h-qdrant-data-app-h-qdrant-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 10.0,
   "capacity_gb": 106.7,
   "used_ratio": 0.723,
   "inode_ratio": 0.166,
   "growth_gb_per_day": -0.466,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "statefulset/app-h-qdrant"
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
   "namespace": "app-k",
   "name": "app-k-postgres-data",
   "target": "app-k/app-k-postgres-data",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": 106.7,
   "used_ratio": 0.723,
   "inode_ratio": 0.165,
   "growth_gb_per_day": -0.466,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "deployment/app-k-postgres"
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
   "growth_gb_per_day": -0.29,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-a-postgres-backup-29896035",
    "job/app-a-postgres-backup-29897475",
    "job/app-a-postgres-backup-29898915"
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
   "name": "data-k-quiz-db-0",
   "target": "default/data-k-quiz-db-0",
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-backup-pvc",
   "target": "app-f-prod/app-f-postgres-backup-pvc",
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
    "job/app-f-postgres-backup-29896050",
    "job/app-f-postgres-backup-29897490",
    "job/app-f-postgres-backup-29898930"
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-data-app-f-postgres-0",
   "target": "app-f-prod/app-f-postgres-data-app-f-postgres-0",
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
    "statefulset/app-f-postgres"
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-mx-backup-pvc",
   "target": "app-f-prod/app-f-postgres-mx-backup-pvc",
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
    "job/app-f-postgres-mx-backup-29896050",
    "job/app-f-postgres-mx-backup-29897490",
    "job/app-f-postgres-mx-backup-29898930"
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-mx-data-app-f-postgres-mx-0",
   "target": "app-f-prod/app-f-postgres-mx-data-app-f-postgres-mx-0",
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
    "statefulset/app-f-postgres-mx"
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-vn-backup-pvc",
   "target": "app-f-prod/app-f-postgres-vn-backup-pvc",
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
    "job/app-f-postgres-vn-backup-29896050",
    "job/app-f-postgres-vn-backup-29897490",
    "job/app-f-postgres-vn-backup-29898930"
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
   "namespace": "app-f-prod",
   "name": "app-f-postgres-vn-data-app-f-postgres-vn-0",
   "target": "app-f-prod/app-f-postgres-vn-data-app-f-postgres-vn-0",
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
    "statefulset/app-f-postgres-vn"
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
   "namespace": "app-f-prod",
   "name": "app-f-redis-data-app-f-redis-0",
   "target": "app-f-prod/app-f-redis-data-app-f-redis-0",
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
    "statefulset/app-f-redis"
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
   "namespace": "app-g-api",
   "name": "app-g-minio-data-app-g-minio-0",
   "target": "app-g-api/app-g-minio-data-app-g-minio-0",
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
    "statefulset/app-g-minio"
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
   "namespace": "app-g-api",
   "name": "app-g-postgres-backup-pvc",
   "target": "app-g-api/app-g-postgres-backup-pvc",
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
    "job/app-g-postgres-backup-29896070",
    "job/app-g-postgres-backup-29897510",
    "job/app-g-postgres-backup-29898950"
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
   "namespace": "app-g-api",
   "name": "app-g-postgres-data-app-g-postgres-0",
   "target": "app-g-api/app-g-postgres-data-app-g-postgres-0",
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
    "statefulset/app-g-postgres"
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
   "namespace": "app-h-prod",
   "name": "mysql-backup-app-h-mysql-0",
   "target": "app-h-prod/mysql-backup-app-h-mysql-0",
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
    "job/app-h-mysql-backup-29896010",
    "job/app-h-mysql-backup-29897450",
    "job/app-h-mysql-backup-29898890",
    "statefulset/app-h-mysql"
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
   "namespace": "app-h-prod",
   "name": "mysql-data-app-h-mysql-0",
   "target": "app-h-prod/mysql-data-app-h-mysql-0",
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
    "statefulset/app-h-mysql"
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
   "namespace": "app-i-prod",
   "name": "app-i-postgres-backup-pvc",
   "target": "app-i-prod/app-i-postgres-backup-pvc",
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
    "job/app-i-postgres-backup-29896020",
    "job/app-i-postgres-backup-29897460",
    "job/app-i-postgres-backup-29898900"
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
   "namespace": "app-i-prod",
   "name": "app-i-postgres-data-app-i-postgres-0",
   "target": "app-i-prod/app-i-postgres-data-app-i-postgres-0",
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
    "statefulset/app-i-postgres"
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
    "job/registry-gc-29896080",
    "job/registry-gc-29897520",
    "job/registry-gc-29898960",
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
   "namespace": "app-l-prod",
   "name": "app-l-artifacts",
   "target": "app-l-prod/app-l-artifacts",
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
    "deployment/app-l-api"
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
   "namespace": "app-l-prod",
   "name": "app-l-postgres-data",
   "target": "app-l-prod/app-l-postgres-data",
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
    "deployment/app-l-postgres"
   ],
   "db_like": true,
   "pv": "pvc-291c9301-e481-4b69-9234-bb77f18d6faf",
   "zone": null,
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  }
 ]
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.app-h-prod</code></summary>

```json
{
 "burst_ratio_7d": 21.3,
 "cpu_limits": 8.2,
 "cpu_max_7d": 0.589,
 "cpu_median_7d": 0.028,
 "cpu_metrics_read": true,
 "cpu_p95_7d": 0.102,
 "has_quota": false,
 "kind": "prod",
 "namespace": "app-h-prod",
 "nodes": {
  "node-a": 12,
  "node-b": 1
 },
 "shares_nodes_with_prod": true,
 "system": false
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-b-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": true,
 "namespace": "app-b-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 2,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-l-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": true,
 "namespace": "app-l-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 3,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-c-prod</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.01,
 "cpu_requests": 0.17,
 "cpu_share_of_cluster_p95": 0.009,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.23,
 "memory_requests_gb": 0.66,
 "multi_org": false,
 "namespace": "app-c-prod",
 "pods": 4,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-f-prod</code></summary>

```json
{
 "burst_ratio_7d": 1.6,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.027,
 "cpu_requests": 0.49,
 "cpu_share_of_cluster_p95": 0.024,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.66,
 "memory_requests_gb": 3.91,
 "multi_org": false,
 "namespace": "app-f-prod",
 "pods": 12,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-h-prod</code></summary>

```json
{
 "burst_ratio_7d": 21.3,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.102,
 "cpu_requests": 1.28,
 "cpu_share_of_cluster_p95": 0.089,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 5.21,
 "memory_requests_gb": 8.12,
 "multi_org": false,
 "namespace": "app-h-prod",
 "pods": 13,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-i-prod</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.006,
 "cpu_requests": 0.1,
 "cpu_share_of_cluster_p95": 0.005,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.14,
 "memory_requests_gb": 0.28,
 "multi_org": false,
 "namespace": "app-i-prod",
 "pods": 2,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-systems</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": 0.004,
 "cpu_requests": 1.0,
 "cpu_share_of_cluster_p95": 0.003,
 "has_quota": false,
 "kind": "ci",
 "memory_p95_7d_gb": 0.36,
 "memory_requests_gb": 2.0,
 "namespace": "arc-systems",
 "pods": 3,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 12
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-systems</code></summary>

```json
{
 "containers_without_memory_limit": 4,
 "containers_without_requests": 4,
 "cpu_p95_7d": 0.004,
 "has_limitrange": false,
 "kind": "ci",
 "memory_p95_7d_gb": 0.36,
 "namespace": "arc-systems",
 "pods": 3,
 "prod": false
}
```

</details>
<details><summary><code>traffic.coredns-latency.cluster</code></summary>

```json
{
 "available": true,
 "p99_s_1h": 0.1457,
 "servfail_ratio_1h": 0.0
}
```

</details>
<details><summary><code>traffic.ingress-nginx-retired.cluster</code></summary>

```json
{
 "admission_webhook": true,
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
 ],
 "present": true,
 "retired": true,
 "retired_note": "ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes",
 "version": "1.14.0"
}
```

</details>
<details><summary><code>hygiene.no-standard-labels.cluster</code></summary>

```json
{
 "standard_label_ratio": 0.23,
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
   "workload": "app-a-prod/deployment/app-m",
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
   "workload": "app-d/deployment/app-d",
   "namespace": "app-d",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-admin",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-mx",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-mx-worker",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-sales-bot",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-vn",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-vn-worker",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/deployment/app-f-worker",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-g-api/deployment/app-g-api",
   "namespace": "app-g-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-admin",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-api-server",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-app-q-client",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-embed",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-excel-agent",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/deployment/app-h-app-p",
   "namespace": "app-h-prod",
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
   "workload": "app-i-prod/deployment/app-i",
   "namespace": "app-i-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-k/deployment/app-k",
   "namespace": "app-k",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-k/deployment/app-k-postgres",
   "namespace": "app-k",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-l-prod/deployment/app-l-api",
   "namespace": "app-l-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-l-prod/deployment/app-l-postgres",
   "namespace": "app-l-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-l-prod/deployment/app-l-web",
   "namespace": "app-l-prod",
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
   "workload": "app-f-prod/statefulset/app-f-postgres",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/statefulset/app-f-postgres-mx",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/statefulset/app-f-postgres-vn",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/statefulset/app-f-redis",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-g-api/statefulset/app-g-minio",
   "namespace": "app-g-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-g-api/statefulset/app-g-postgres",
   "namespace": "app-g-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-h-prod/statefulset/app-h-mysql",
   "namespace": "app-h-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-h-prod/statefulset/app-h-qdrant",
   "namespace": "app-h-prod",
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
   "workload": "app-i-prod/statefulset/app-i-postgres",
   "namespace": "app-i-prod",
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
   "workload": "app-a-prod/cronjob/marketing-autopost-en",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-autopost-ja",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-digest-day",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-digest-month",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-digest-week",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-radar-global",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-radar-global-eu",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-radar-japan",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/marketing-radar-japan-noon",
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
   "workload": "app-f-prod/cronjob/app-f-ga4-digest-day",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-ga4-digest-month",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-ga4-digest-week",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-policy-radar",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-postgres-backup",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-postgres-mx-backup",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-f-prod/cronjob/app-f-postgres-vn-backup",
   "namespace": "app-f-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-g-api/cronjob/app-g-postgres-backup",
   "namespace": "app-g-api",
   "prod": false,
   "labels": {}
  },
  {
   "workload": "app-h-prod/cronjob/app-h-mysql-backup",
   "namespace": "app-h-prod",
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
   "workload": "app-i-prod/cronjob/app-i-postgres-backup",
   "namespace": "app-i-prod",
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
 "workloads": 110
}
```

</details>
<details><summary><code>node.swap-enabled.192.168.90.102:9100</code></summary>

```json
{
 "labels": {
  "__name__": "node_memory_SwapTotal_bytes",
  "container": "node-exporter",
  "endpoint": "http-metrics",
  "instance": "192.168.90.102:9100",
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
 "host": "192.168.90.160",
 "node": "node-b",
 "server_url": "https://192.168.90.160:6443"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9981481481481481,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 4.8,
 "keda_owned": false,
 "max": 6,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "name": "app-a-backend",
 "namespace": "app-a-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-a-prod/deployment/app-a-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9983796296296297,
 "current_cpu_utilization": 3,
 "days_since_last_scale": 2.6,
 "keda_owned": false,
 "max": 4,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "name": "app-a-frontend",
 "namespace": "app-a-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-a-prod/deployment/app-a-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-f-prod/deployment/app-f</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "current_cpu_utilization": 4,
 "days_since_last_scale": 9.1,
 "keda_owned": false,
 "max": 5,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 2,
 "name": "app-f",
 "namespace": "app-f-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-f-prod/deployment/app-f",
 "target_cpu_utilization": 60
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-f-prod/deployment/app-f-mx</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "current_cpu_utilization": 4,
 "days_since_last_scale": 9.1,
 "keda_owned": false,
 "max": 4,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "name": "app-f-mx",
 "namespace": "app-f-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-f-prod/deployment/app-f-mx",
 "target_cpu_utilization": 60
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-f-prod/deployment/app-f-vn</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 9.1,
 "keda_owned": false,
 "max": 4,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "name": "app-f-vn",
 "namespace": "app-f-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-f-prod/deployment/app-f-vn",
 "target_cpu_utilization": 60
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-i-prod/deployment/app-i</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "current_cpu_utilization": 4,
 "days_since_last_scale": 9.1,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "name": "app-i",
 "namespace": "app-i-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-i-prod/deployment/app-i",
 "target_cpu_utilization": 60
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "applications_prod": 10,
 "notifications_configured": false,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "applications_prod": 10,
 "ignore_differences_apps": 16,
 "prod_tracking_moving_ref": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/app-c",
  "argocd/application/app-f-kr",
  "argocd/application/app-f-mx",
  "argocd/application/app-f-shared",
  "argocd/application/app-f-vn",
  "argocd/application/app-h",
  "argocd/application/app-i",
  "argocd/application/app-l-prod"
 ]
}
```

</details>
<details><summary><code>certmanager.controller-errors.cluster</code></summary>

```json
{
 "acme_by_status": {
  "200": 133,
  "403": 1,
  "201": 8,
  "400": 6
 },
 "acme_error_ratio": 0.0473,
 "acme_errors": 7,
 "acme_requests": 148,
 "metrics_available": true,
 "not_ready_metric": 0,
 "sync_calls": 2654,
 "sync_errors": 233
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
 "version": "1.14.4",
 "webhook_replicas": 1,
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
 "aaaa_ratio": 0.487,
 "cluster_ipv6": false,
 "metrics_available": true,
 "qps_total": 32.29
}
```

</details>
<details><summary><code>cost.k3s-node-efficiency.cluster</code></summary>

```json
{
 "allocatable_cpu": 18.0,
 "can_drop_largest_node": false,
 "metrics_read": true,
 "nodes": 2,
 "p95_used_cpu": 0.92,
 "p95_util_ratio": 0.051,
 "request_over_usage": 7.1,
 "requested_cpu": 6.51
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.app-f-prod/deployment/app-f-vn:db-migrate</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "db-migrate",
 "image": "registry.lab-a.example/app-f-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "tag",
 "workload": "app-f-prod/deployment/app-f-vn"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "argocd-applicationset-controller",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-applicationset-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "copyutil",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-dex-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "dex",
 "image": "ghcr.io/dexidp/dex:v2.43.0",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-dex-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "argocd-notifications-controller",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-notifications-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "redis",
 "image": "public.ecr.aws/docker/library/redis:8.2.2-alpine",
 "pull_policy": "Always",
 "registry": "public.ecr.aws",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-redis"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "argocd-repo-server",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-repo-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "argocd-server",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/deployment/argocd-server"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "argocd-application-controller",
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "argocd/statefulset/argocd-application-controller"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "keda-admission-webhooks",
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.19.0",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "tag_kind": "tag",
 "workload": "keda/deployment/keda-admission-webhooks"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "keda-operator-metrics-apiserver",
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.19.0",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "tag_kind": "tag",
 "workload": "keda/deployment/keda-operator-metrics-apiserver"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "keda-operator",
 "image": "ghcr.io/kedacore/keda:2.19.0",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "tag_kind": "tag",
 "workload": "keda/deployment/keda-operator"
}
```

</details>
<details><summary><code>hygiene.failed-pods-lingering.cluster</code></summary>

```json
{
 "by_namespace": {
  "app-a-prod": 2,
  "app-h-prod": 2
 },
 "by_reason": {
  "Failed": 2,
  "UnexpectedAdmissionError": 2
 },
 "count": 4,
 "oldest_h": 3881.6,
 "prod": 4,
 "sample": [
  "app-a-prod/codex-bench",
  "app-a-prod/app-a-experiment",
  "app-h-prod/app-h-embed-67f6f74f6c-rlm8m",
  "app-h-prod/app-h-embed-67f6f74f6c-b6kdt"
 ]
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "containers": 126,
 "emptydir_without_sizelimit": 11,
 "emptydir_without_sizelimit_prod": [],
 "prod_without_request": 63,
 "request_ratio": 0.0,
 "with_request": 0
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "replicasets_total": 292,
 "replicasets_zero": 235,
 "revision_history_limits": {
  "10": 54,
  "0": 3,
  "3": 1,
  "2": 1
 }
}
```

</details>
<details><summary><code>hygiene.orphan-secrets.cluster</code></summary>

```json
{
 "orphan_secrets": [
  {
   "namespace": "app-f-prod",
   "name": "app-f-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  },
  {
   "namespace": "app-h-prod",
   "name": "app-h-poca-store-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  },
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
   "name": "app-f-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "k-quiz-auth-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "k-quiz-aws-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "k-quiz-db-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "k-quiz-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  }
 ],
 "secrets_read": true,
 "secrets_total": 139
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "count": 64,
 "webhooks": 28,
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
 },
 "zero_object_count": 42
}
```

</details>
<details><summary><code>keda.unused.cluster</code></summary>

```json
{
 "metrics_apiserver_ready": 1,
 "metrics_apiserver_replicas": 1,
 "operator_ready": 1,
 "operator_replicas": 1,
 "scaledjobs": 0,
 "scaledobjects": 0,
 "unused": true,
 "version": "2.19.0",
 "webhooks_ready": 1,
 "webhooks_replicas": 1
}
```

</details>
<details><summary><code>logs.signatures.cert-manager.orphan-tls-secret</code></summary>

```json
{
 "count": 96,
 "first": "2026-11-06T05:52:26Z",
 "last": "2026-11-07T01:09:11Z",
 "warn_at": 1,
 "fail_at": 1000,
 "files": {
  "logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log": 96
 },
 "samples": []
}
```

</details>
<details><summary><code>logs.signatures.metallb.speaker-peer-unreachable</code></summary>

```json
{
 "count": 421,
 "first": "2026-11-06T22:06:16Z",
 "last": "2026-11-07T01:09:40Z",
 "warn_at": 60,
 "fail_at": 2000,
 "files": {
  "logs/pods/metallb/metallb-system_speaker.log": 421
 },
 "samples": []
}
```

</details>
<details><summary><code>observability.alert-metric-without-dashboard.grafana</code></summary>

```json
{
 "alert_metrics": 175,
 "alert_metrics_without_panel": [
  "aggregator_unavailable_apiservice",
  "aggregator_unavailable_apiservice_total",
  "alertmanager_cluster_members",
  "alertmanager_config_hash",
  "alertmanager_config_last_reload_successful",
  "apiserver_client_certificate_expiration_seconds_bucket",
  "apiserver_client_certificate_expiration_seconds_count",
  "apiserver_request:burnrate1d",
  "apiserver_request:burnrate1h",
  "apiserver_request:burnrate2h",
  "apiserver_request:burnrate30m",
  "apiserver_request:burnrate3d",
  "apiserver_request:burnrate5m",
  "apiserver_request:burnrate6h",
  "apiserver_request_terminations_total",
  "apiserver_request_total",
  "etcd_mvcc_db_total_size_in_use_in_bytes",
  "etcd_network_peer_sent_failures_total",
  "etcd_server_proposals_failed_total",
  "etcd_server_quota_backend_bytes",
  "gateway_cost_usd_total",
  "gateway_requests_total",
  "grpc_server_handling_seconds_bucket",
  "kube_daemonset_status_current_number_scheduled",
  "kube_daemonset_status_desired_number_scheduled",
  "kube_daemonset_status_number_available",
  "kube_daemonset_status_number_misscheduled",
  "kube_daemonset_status_updated_number_scheduled",
  "kube_deployment_metadata_generation",
  "kube_deployment_spec_replicas",
  "kube_deployment_status_condition",
  "kube_deployment_status_observed_generation",
  "kube_deployment_status_replicas_available",
  "kube_deployment_status_replicas_updated",
  "kube_horizontalpodautoscaler_spec_max_replicas",
  "kube_horizontalpodautoscaler_spec_min_replicas",
  "kube_horizontalpodautoscaler_status_current_replicas",
  "kube_horizontalpodautoscaler_status_desired_replicas",
  "kube_job_failed",
  "kube_job_status_active",
  "kube_job_status_failed",
  "kube_job_status_start_time",
  "kube_node_role",
  "kube_node_spec_taint",
  "kube_node_spec_unschedulable",
  "kube_node_status_condition",
  "kube_persistentvolume_status_phase",
  "kube_persistentvolumeclaim_access_mode",
  "kube_persistentvolumeclaim_labels",
  "kube_pod_container_status_waiting_reason",
  "kube_pod_status_phase",
  "kube_poddisruptionbudget_status_current_healthy",
  "kube_poddisruptionbudget_status_desired_healthy",
  "kube_state_metrics_list_total",
  "kube_state_metrics_shard_ordinal",
  "kube_state_metrics_total_shards",
  "kube_state_metrics_watch_total",
  "kube_statefulset_metadata_generation",
  "kube_statefulset_replicas",
  "kube_statefulset_status_current_revision",
  "kube_statefulset_status_observed_generation",
  "kube_statefulset_status_replicas_ready",
  "kube_statefulset_status_replicas_updated",
  "kube_statefulset_status_update_revision",
  "kubelet_certificate_manager_client_expiration_renew_errors",
  "kubelet_certificate_manager_client_ttl_seconds",
  "kubelet_certificate_manager_server_ttl_seconds",
  "kubelet_evictions",
  "kubelet_server_expiration_renew_errors",
  "kubelet_volume_stats_inodes_free",
  "kubelet_volume_stats_used_bytes",
  "kubernetes_build_info",
  "node_bonding_active",
  "node_bonding_slaves",
  "node_disk_io_time_weighted_seconds_total",
  "node_filefd_allocated",
  "node_filefd_maximum",
  "node_filesystem_files",
  "node_filesystem_files_free",
  "node_filesystem_readonly",
  "node_md_disks",
  "node_md_disks_required",
  "node_network_receive_errs_total",
  "node_network_receive_packets_total",
  "node_network_transmit_errs_total",
  "node_network_transmit_packets_total",
  "node_network_up",
  "node_nf_conntrack_entries",
  "node_nf_conntrack_entries_limit",
  "node_quantile:kubelet_pleg_relist_duration_seconds:histogram_quantile",
  "node_systemd_service_restart_total",
  "node_systemd_unit_state",
  "node_textfile_scrape_error",
  "node_timex_maxerror_seconds",
  "node_timex_offset_seconds",
  "node_timex_sync_status",
  "node_vmstat_pgmajfault",
  "prometheus_config_last_reload_successful",
  "prometheus_engine_queries",
  "prometheus_engine_queries_concurrent_max",
  "prometheus_notifications_alertmanagers_discovered",
  "prometheus_notifications_errors_total",
  "prometheus_notifications_queue_capacity",
  "prometheus_notifications_queue_length",
  "prometheus_notifications_sent_total",
  "prometheus_operator_list_operations_failed_total",
  "prometheus_operator_list_operations_total",
  "prometheus_operator_managed_resources",
  "prometheus_operator_node_address_lookup_errors_total",
  "prometheus_operator_ready",
  "prometheus_operator_reconcile_errors_total",
  "prometheus_operator_reconcile_operations_total",
  "prometheus_operator_status_update_errors_total",
  "prometheus_operator_status_update_operations_total",
  "prometheus_operator_syncs",
  "prometheus_operator_watch_operations_failed_total",
  "prometheus_operator_watch_operations_total",
  "prometheus_remote_storage_failed_samples_total",
  "prometheus_remote_storage_queue_highest_sent_timestamp_seconds",
  "prometheus_remote_storage_queue_highest_timestamp_seconds",
  "prometheus_remote_storage_samples_failed_total",
  "prometheus_remote_storage_samples_total",
  "prometheus_remote_storage_shards_desired",
  "prometheus_remote_storage_shards_max",
  "prometheus_remote_storage_succeeded_samples_total",
  "prometheus_rule_evaluation_failures_total",
  "prometheus_rule_group_iterations_missed_total",
  "prometheus_rule_group_rules",
  "prometheus_sd_kubernetes_failures_total",
  "prometheus_sd_refresh_failures_total",
  "prometheus_target_metadata_cache_entries",
  "prometheus_target_scrape_pool_exceeded_label_limits_total",
  "prometheus_target_scrape_pool_exceeded_target_limit_total",
  "prometheus_target_sync_failed_total",
  "prometheus_tsdb_compactions_failed_total",
  "prometheus_tsdb_reloads_failures_total",
  "reloader_last_reload_successful"
 ],
 "alert_metrics_without_panel_count": 137,
 "available": true,
 "panel_metrics": 170,
 "read": 25
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
 "fired_15d": [
  "AppQBackendDown",
  "CPUThrottlingHigh",
  "InfoInhibitor",
  "KubeCPUOvercommit",
  "KubeDeploymentReplicasMismatch",
  "KubeHpaMaxedOut",
  "KubeJobFailed",
  "KubePodCrashLooping",
  "KubeQuotaFullyUsed",
  "Watchdog"
 ],
 "never_fired_15d": [
  "AlertmanagerClusterCrashlooping",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerFailedReload",
  "AlertmanagerFailedToSendAlerts",
  "AlertmanagerMembersInconsistent",
  "AppQClusterCPU50",
  "AppQClusterCPU80",
  "AppQClusterMem50",
  "AppQClusterMem80",
  "AppQFrontendDown",
  "AppQGatewayDown",
  "AppQGatewayErrorRateHigh",
  "AppQGatewayHighCost",
  "AppQGatewayUpstreamRejecting",
  "AppQLLMQuotaExhausted",
  "AppQPostgresDown",
  "AppQSandboxProvisionFailing",
  "AppQTooManySandboxes",
  "AppQWatchdogFailing",
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
 "never_fired_count": 135,
 "rules_total": 145
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "ingresses": 29,
 "missing_saturation": [
  {
   "namespace": "app-a-prod",
   "ingress": "app-a-backend",
   "class": "nginx",
   "hosts": [
    "api.app-a.lab-a.example",
    "api.lab-b.example"
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
    "app-a.lab-a.example",
    "lab-b.example",
    "www.lab-b.example"
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
    "obs.lab-b.example"
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
    "umami.lab-b.example",
    "umami.lab-j.example"
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
    "argocd.lab-a.example"
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
    "observe-api.lab-a.example"
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
    "observe.lab-a.example"
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
    "app-c.lab-a.example",
    "lab-i.example",
    "www.lab-i.example"
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
    "app-c.lab-a.example",
    "lab-i.example",
    "www.lab-i.example"
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
   "namespace": "app-d",
   "ingress": "app-d",
   "class": "nginx",
   "hosts": [
    "lab-a.example"
   ],
   "services": [
    "app-d"
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
    "admin.lab-c.example"
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
   "ingress": "app-f-ingress",
   "class": "nginx",
   "hosts": [
    "k-esg.lab-c.example"
   ],
   "services": [
    "app-f-svc"
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
   "ingress": "app-f-mx-ingress",
   "class": "nginx",
   "hosts": [
    "mx.lab-c.example"
   ],
   "services": [
    "app-f-mx-svc"
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
   "ingress": "app-f-vn-ingress",
   "class": "nginx",
   "hosts": [
    "vn.lab-c.example"
   ],
   "services": [
    "app-f-vn-svc"
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
   "namespace": "app-g-api",
   "ingress": "app-g-api",
   "class": "nginx",
   "hosts": [
    "app-g-api.lab-a.example",
    "app-g-cdn.lab-a.example"
   ],
   "services": [
    "app-g-api",
    "app-g-minio"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-admin-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-admin-prod.lab-a.example",
    "lab-h.example",
    "www.lab-h.example"
   ],
   "services": [
    "app-h-admin-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-api-server-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-api-prod.lab-a.example"
   ],
   "services": [
    "app-h-api-server-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-api-server-oauth-ingress",
   "class": "nginx",
   "hosts": [
    "lab-d.example",
    "www.lab-d.example"
   ],
   "services": [
    "app-h-api-server-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-app-q-client-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-app-q-client-prod.lab-a.example",
    "lab-d.example",
    "www.lab-d.example"
   ],
   "services": [
    "app-h-app-q-client-svc"
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
   "namespace": "app-h-prod",
   "ingress": "app-h-app-p-ingress",
   "class": "nginx",
   "hosts": [
    "app-h-app-p-prod.lab-a.example",
    "lab-g.example",
    "www.lab-g.example"
   ],
   "services": [
    "app-h-app-p-svc"
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
    "kibana.lab-a.example"
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
   "namespace": "app-i-prod",
   "ingress": "app-i-ingress",
   "class": "nginx",
   "hosts": [
    "app-j.lab-a.example",
    "lab-e.example",
    "www.lab-e.example"
   ],
   "services": [
    "app-i-svc"
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
    "app-k.lab-a.example"
   ],
   "services": [
    "app-k"
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
    "registry.lab-a.example"
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
   "namespace": "app-n",
   "ingress": "app-n",
   "class": "nginx",
   "hosts": [
    "app-o.lab-a.example"
   ],
   "services": [
    "app-n-workstation"
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
   "namespace": "app-n",
   "ingress": "app-n-auth",
   "class": "nginx",
   "hosts": [
    "app-o.lab-a.example"
   ],
   "services": [
    "app-n-workstation"
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
   "namespace": "app-l-prod",
   "ingress": "app-l-api",
   "class": "nginx",
   "hosts": [
    "api.lab-f.example"
   ],
   "services": [
    "app-l-api"
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
   "namespace": "app-l-prod",
   "ingress": "app-l-web",
   "class": "nginx",
   "hosts": [
    "lab-f.example"
   ],
   "services": [
    "app-l-web"
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
 ]
}
```

</details>
<details><summary><code>observability.severity-channels-not-separated.cluster</code></summary>

```json
{
 "default_receiver": "discord",
 "receivers": {
  "null": [],
  "discord": [
   "slack"
  ]
 },
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
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-a-prod/statefulset/app-a-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "container": "redis",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "app-a-prod/statefulset/app-a-redis"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-mx:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-f-prod/statefulset/app-f-postgres-mx"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-vn:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-f-prod/statefulset/app-f-postgres-vn"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-f-prod/statefulset/app-f-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-redis:redis</code></summary>

```json
{
 "container": "redis",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "app-f-prod/statefulset/app-f-redis"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-g-api/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-g-api/statefulset/app-g-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-h-prod/statefulset/app-h-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-h-prod/statefulset/app-h-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-i-prod/statefulset/app-i-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "workload": "app-i-prod/statefulset/app-i-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-k/deployment/app-k-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-k/deployment/app-k-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-l-prod/deployment/app-l-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-l-prod/deployment/app-l-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "container": "elasticsearch",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "readiness exec timeout 1s (false failures when the node is busy)"
 ],
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
 "workload": "logging/statefulset/elasticsearch"
}
```

</details>
<details><summary><code>resilience.finished-jobs-accumulating.cluster</code></summary>

```json
{
 "failed": 3,
 "failed_pods": 4,
 "finished_without_ttl": 56,
 "succeeded_pods": 53,
 "total": 58
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-frontend:frontend</code></summary>

```json
{
 "container": "frontend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-gateway:gateway</code></summary>

```json
{
 "container": "gateway",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-gateway"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "container": "phoenix",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 6006,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 40
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-phoenix"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-umami:umami</code></summary>

```json
{
 "container": "umami",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/api/heartbeat) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/api/heartbeat",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-a-prod/deployment/app-a-umami"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-backend:backend</code></summary>

```json
{
 "container": "backend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-b-prod/deployment/app-b-backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-frontend:frontend</code></summary>

```json
{
 "container": "frontend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-b-prod/deployment/app-b-frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-signaling:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/ws/socket.io/?EIO=4&transport=polling) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "workload": "app-c-prod/deployment/app-c-signaling"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-web:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-c-prod/deployment/app-c-web"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-admin:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/login) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "workload": "app-f-prod/deployment/app-f-admin"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-mx:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-f-prod/deployment/app-f-mx"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-vn:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-f-prod/deployment/app-f-vn"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-f-prod/deployment/app-f"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-admin:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 30
 },
 "workload": "app-h-prod/deployment/app-h-admin"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-api-server:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/healthcheck) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 5,
  "initial_delay_s": 60
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 30,
  "initial_delay_s": 90
 },
 "workload": "app-h-prod/deployment/app-h-api-server"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-p:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "workload": "app-h-prod/deployment/app-h-app-p"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-q-client:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "workload": "app-h-prod/deployment/app-h-app-q-client"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-embed:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 15
 },
 "workload": "app-h-prod/deployment/app-h-embed"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-h-prod/deployment/app-h-excel-agent:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 18,
  "initial_delay_s": 10
 },
 "workload": "app-h-prod/deployment/app-h-excel-agent"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-i-prod/deployment/app-i:app</code></summary>

```json
{
 "container": "app",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
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
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "workload": "app-i-prod/deployment/app-i"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-l-prod/deployment/app-l-api:api</code></summary>

```json
{
 "container": "api",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-l-prod/deployment/app-l-api"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-l-prod/deployment/app-l-web:web</code></summary>

```json
{
 "container": "web",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "prod": true,
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
 "startup": null,
 "workload": "app-l-prod/deployment/app-l-web"
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
<details><summary><code>resilience.no-prestop.app-f-prod/app-f</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f",
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
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-mx</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-mx",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-f-prod/app-f-vn</code></summary>

```json
{
 "namespace": "app-f-prod",
 "name": "app-f-vn",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-admin</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-app-p</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-app-p",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-app-q-client</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-app-q-client",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-embed</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-excel-agent</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-i-prod/app-i</code></summary>

```json
{
 "namespace": "app-i-prod",
 "name": "app-i",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-l-prod/app-l-api</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-l-prod/app-l-postgres</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-postgres",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-l-prod/app-l-web</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-web",
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
  "memory_request_p95_ratio_7d": 0.2031402587890625,
  "memory_p95_7d_bytes": 54530048.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-h-prod/deploy/app-h-embed:app</code></summary>

```json
{
 "labels": {
  "namespace": "app-h-prod",
  "pod": "app-h-embed-67f6f74f6c-lb7lj",
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
<details><summary><code>resources.memory-request-overprovisioned.app-h-prod/sts/app-h-qdrant:qdrant</code></summary>

```json
{
 "labels": {
  "namespace": "app-h-prod",
  "pod": "app-h-qdrant-0",
  "container": "qdrant"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2003631591796875,
  "memory_p95_7d_bytes": 53784576.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-l-prod/deploy/app-l-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-l-prod",
  "pod": "app-l-postgres-76b69b654d-lzf4d",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2540435791015625,
  "memory_p95_7d_bytes": 68194304.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "cpu_only": true,
 "current_cpu_utilization": 2,
 "metric_types": [
  "cpu"
 ],
 "name": "app-a-backend",
 "namespace": "app-a-prod",
 "prod": true,
 "target": "app-a-prod/deployment/app-a-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "cpu_only": true,
 "current_cpu_utilization": 3,
 "metric_types": [
  "cpu"
 ],
 "name": "app-a-frontend",
 "namespace": "app-a-prod",
 "prod": true,
 "target": "app-a-prod/deployment/app-a-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "desired_changes_7d": 3.0,
 "has_behavior": false,
 "keda_owned": false,
 "max": 6,
 "min": 2,
 "name": "app-a-backend",
 "namespace": "app-a-prod",
 "prod": true,
 "target": "app-a-prod/deployment/app-a-backend"
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "desired_changes_7d": 2.0,
 "has_behavior": false,
 "keda_owned": false,
 "max": 4,
 "min": 2,
 "name": "app-a-frontend",
 "namespace": "app-a-prod",
 "prod": true,
 "target": "app-a-prod/deployment/app-a-frontend"
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-a</code></summary>

```json
{
 "ci_heavy": true,
 "ci_pod_list": [
  {
   "pod": "arc-actions-runner-controller-5c9d9ffd65-766b6",
   "namespace": "arc-systems",
   "owner_kind": "ReplicaSet",
   "cpu_request": 0.0,
   "heavy": true
  }
 ],
 "ci_pods": 1,
 "cpu_saturated_minutes_7d": 0.0,
 "memory_limit_overcommit": 1.04,
 "node": "node-a",
 "pool": "(no-pool)",
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-f-prod",
  "app-h-prod",
  "app-i-prod",
  "app-l-prod"
 ],
 "prod_pods": 32,
 "separation_possible": false,
 "shares_ci_prod": true
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-b</code></summary>

```json
{
 "ci_heavy": true,
 "ci_pod_list": [
  {
   "pod": "lab-a-runner-8tt2w-cpndm",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  },
  {
   "pod": "lab-a-runner-8tt2w-d2pwq",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  }
 ],
 "ci_pods": 2,
 "cpu_saturated_minutes_7d": 0.0,
 "memory_limit_overcommit": 0.99,
 "node": "node-b",
 "pool": "(no-pool)",
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-f-prod",
  "app-h-prod",
  "app-i-prod",
  "app-l-prod"
 ],
 "prod_pods": 15,
 "separation_possible": false,
 "shares_ci_prod": true
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota</code></summary>

```json
{
 "containers_without_requests": 0,
 "hard": {
  "count/pods": "200",
  "limits.memory": "80Gi",
  "requests.memory": "60Gi"
 },
 "has_limitrange": false,
 "limitrange_default_request": false,
 "requires_requests": true,
 "target": "app-a-prod/app-a-prod-quota"
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota</code></summary>

```json
{
 "containers_without_requests": 0,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "20Gi"
 },
 "has_limitrange": false,
 "limitrange_default_request": false,
 "requires_requests": true,
 "target": "app-b-prod/app-b-prod-quota"
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-l-prod/app-l-prod-quota</code></summary>

```json
{
 "containers_without_requests": 0,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "30Gi"
 },
 "has_limitrange": false,
 "limitrange_default_request": false,
 "requires_requests": true,
 "target": "app-l-prod/app-l-prod-quota"
}
```

</details>
<details><summary><code>traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "external_traffic_policy": "Local",
 "hosts": [
  "192.168.90.201"
 ],
 "name": "nginx-ingress-ingress-nginx-controller",
 "namespace": "ingress-nginx",
 "ports": [
  80,
  443
 ],
 "target": "loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller"
}
```

</details>
<details><summary><code>traffic.metallb-single-lb-service.cluster</code></summary>

```json
{
 "l2_available": true,
 "l2_partial": false,
 "lb_services": 1,
 "leader_node": "node-b",
 "leader_share": 1.0,
 "mode": "layer2",
 "nodes_total": 2,
 "pinned_by_selector": false,
 "total_ips": 10,
 "used": 1
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
<details><summary><code>scaling.no-hpa-serving-prod.app-h-prod/app-h-embed</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-embed",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-h-prod/app-h-excel-agent</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-excel-agent",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-l-prod/app-l-api</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-l-prod/app-l-web</code></summary>

```json
{
 "namespace": "app-l-prod",
 "name": "app-l-web",
 "kind": "Deployment"
}
```

</details>

### 7-6. 도구 메모 (kubegap 자체에 대한 것)

(이번 점검에서 쓰지 않음)

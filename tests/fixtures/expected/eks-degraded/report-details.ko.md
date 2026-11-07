# kubegap 상세 리포트 — arn:aws:eks:ap-northeast-2:<account>:cluster/app-u-cluster-eks (`app-u-cluster`), full 점검

사람이 먼저 읽을 리포트는 옆의 `report.md`예요. 이 파일에는 판정 전체와 표가 있고, `scripts/kubegap render-details`가 수집 자료와 에이전트가 사실 파일에 쓴 분석 기록을 모아 만들어요. 다음 점검의 에이전트도 이 파일을 읽어요. 점검 항목 id와 근거 문장은 정의에서 그대로 가져와서 영어예요.

| 항목 | 값 |
|---|---|
| kube context / 클러스터 | `app-u-cluster` / arn:aws:eks:ap-northeast-2:<account>:cluster/app-u-cluster-eks (eks, v1.32.13-eks-577a51e) |
| 실행 시각 / 모드 | 2026-11-07T10:33:37+09:00 / full (수집 300.7초, 모드 때문에 건너뛴 단계 0개, 실패 40개) |
| 프로파일 | `prod` (detected) |
| kubegap / 점검 항목 버전 / 로그 시그니처 버전 | 0.1.4 / 0.1.84 / 1.1.0 |
| 노드 / 네임스페이스 / 파드 / CRD | 9 (Ready 9) / 26 / 154 / 47 |
| 컴포넌트 (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| 메트릭 저장소 | 없음 |
| 로그 저장소 | loki 2.6.1 |
| 노드 접속 | none (degraded fixture: no node access); SSM 미등록 0대 |
| 수집 폴더 | `<snapshot>` |

## 1. 자동 판정 집계와 에이전트 조정

| 심각도(기본값) | fail | warn | 같은 모드의 지난 점검 대비 |
|---|---|---|---|
| critical | 1 | 3 | 같은 모드의 지난 점검 없음 |
| high | 15 | 8 | 같은 모드의 지난 점검 없음 |
| medium | 84 | 120 | 같은 모드의 지난 점검 없음 |
| low | 15 | 113 | 같은 모드의 지난 점검 없음 |
| info | 2 | 0 | 같은 모드의 지난 점검 없음 |

점검 항목 367개 중 판정 231개, 프로파일에서 끈 것 2개, 건너뜀 132개, 이 모드에서 수집 안 함 0개, 오류 0개, 도구 없음 0개, 에이전트 판정 2개예요. 숨긴 항목은 0개예요.

### 1-1. 자동 판정과 최종 판정이 다른 곳

(이번 점검에서 쓰지 않음)

### 1-2. 에이전트가 다시 센 숫자

(이번 점검에서 쓰지 않음)

## 2. 지금 fail인 critical과 high (자동 판정)

| 항목 | 심각도 | 연속 횟수 | 근거 |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `eks.public-endpoint-open.cluster` | high |  | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `karpenter.ec2nodeclass-al2.cluster` | high |  | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 289MB |
| `observability.no-event-retention.cluster` | high |  | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 252 days past |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.prod-concentration.ip-10-0-1-139.ap-northeast-2.compute.internal` | high |  | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default, spot) holds prod pods 23/45 (0.51), 18 workloads: ['app-ab-prod/app-ab-backend', 'app-ab-prod/app-ab-frontend', 'prod-app-s/app-s-admin' … |
| `resilience.replicas-same-node.prod-app-w/deployment/app-w` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-ai` | high |  | replicas 3 (Running 3), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 3}, AZ distribution {'ap-northeast-2a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-backend` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-z-backend/deployment/app-z-frontend` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling … |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/tts-proxy` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |

(연속 횟수는 diff.json이 있어야 나와요. 이번 점검에는 없어요)

## 3. 같은 모드의 지난 점검 이후 변화

비교할 이전 full 점검이 없어요.

### 3-1. 왜 바뀌었나

(이번 점검에서 쓰지 않음)

## 4. 영역별 상세

(이번 점검에서 쓰지 않음)

## 5. 없는 것 목록

| 항목 | 상태 | 심각도 | 필요한 이유 | 제안 |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |
| `observability.no-slo.cluster` | warn | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `observability.no-event-retention.cluster` | fail | high | Kubernetes events are kept for only one hour by default. FailedScheduling, OOMKilling and Unhealthy from the night are gone by morning. The most undervalued material is lost. | Ship events to Loki or Elasticsearch with kubernetes-event-exporter. Alternatively, the promtail/alloy event source if Loki exists, or `[INPUT] kubernetes_events` with fluent-bit (detection … |
| `security.no-certificate-manager.cluster` | fail | medium | When TLS certificate renewal is manual, services keep going down from expiry. cert-manager (or ACM plus ALB on EKS) automates renewal. On EKS, ALBs using ACM certificates work without cert-manager … | Install cert-manager, or if ACM is in use, suppress this check in config.yaml with a reason. |
| `hygiene.no-progressive-delivery.cluster` | fail | info | A rolling update is "replace everything", so a defect in the new version reaches all traffic immediately. Without a canary tool (some traffic -> check metrics -> expand), deployment verification … | As services grow, automate canary judgment with Argo Rollouts (same ecosystem as Argo CD) + AnalysisTemplate (ALB 5xx, p95 Prometheus queries). |

있어야 하는데 없는 도구 종류: backup, event-retention, slo, certificates, progressive-delivery.

## 6. 숨긴 항목, 도구 없음, 수집 안 함

- 숨긴 항목 0: 없음
- 숨김 기한이 지난 항목 0: 없음
- 도구 없음 0: 없음
- full 모드에서 수집 안 함 0: 없음
- 건너뛰었거나 오류가 난 점검 항목 132: `resources.cpu-throttling` (skip: metrics/cpu_throttle_ratio_24h,cpu_throttle_ratio_5m all missing or failed), `resources.oomkilled` (skip: metrics/oomkilled_last_terminated.json missing (not collected or no Prometheus)), `resources.oomkilled-repeated` (skip: summary.resilience.oom_7d.rows missing), `resources.node-memory-request-usage-gap` (skip: metrics/node_memory_request_ratio.json missing or failed), `resources.besteffort-in-prod` (skip: metrics/besteffort_pods.json missing (not collected or no Prometheus)), `resources.node-request-usage-gap` (skip: metrics/node_cpu_request_ratio.json missing or failed), `resources.cpu-request-overprovisioned` (skip: metrics/cpu_request_p95_ratio_7d.json missing or failed), `resources.cpu-limit-near-p95` (skip: metrics/cpu_limit_p95_ratio_7d.json missing (not collected or no Prometheus)), `resources.memory-request-overprovisioned` (skip: metrics/memory_request_p95_ratio_7d.json missing or failed), `resources.memory-limit-near-p95` (skip: metrics/memory_limit_p95_ratio_7d.json missing (not collected or no Prometheus)), `resources.large-request-binpacking` (skip: metrics/large_request_containers.json missing (not collected or no Prometheus)), `node.conntrack-usage` (skip: metrics/conntrack_ratio.json missing (not collected or no Prometheus)), `node.disk-usage` (skip: metrics/disk_usage_ratio.json missing (not collected or no Prometheus)), `node.inode-usage` (skip: metrics/inode_usage_ratio.json missing (not collected or no Prometheus)), `node.ntp-offset` (skip: metrics/ntp_offset_seconds.json missing (not collected or no Prometheus)), `node.ntp-unsynced` (skip: metrics/ntp_sync_status.json missing (not collected or no Prometheus)), `node.swap-enabled` (skip: metrics/node_swap_total_bytes.json missing (not collected or no Prometheus)), `observability.alerts-always-firing` (skip: alert firing samples not read (metrics/alerts_firing_samples_7d.json missing or failed)), `observability.alertmanager-default-null` (skip: nothing to judge: Alertmanager configuration not read, or outside yamlite's YAML subset (config_error)), `observability.alertmanager-notification-failed` (skip: metrics/alertmanager_notifications_failed_1d.json missing (not collected or no Prometheus)), `observability.severity-channels-not-separated` (skip: nothing to judge: Alertmanager configuration not read, or outside yamlite's YAML subset (config_error)), `observability.scrape-targets-down` (skip: metrics/scrape_targets_down_by_job.json missing (not collected or no Prometheus)), `security.networkpolicy-coverage` (skip: objects/networkpolicies.networking.k8s.io.json missing: the ClusterRole does not grant list on this kind), `events.tracked-warning-reasons` (skip: summary.events.history.tracked_hits missing), `controlplane.scheduler-unschedulable` (skip: control plane logs not read (CloudWatch Logs Insights: logs/cloudwatch/volume_by_stream.json missing)), `controlplane.apiserver-429` (skip: metrics/apiserver_429_rate.json missing (not collected or no Prometheus)), `controlplane.apiserver-5xx` (skip: metrics/apiserver_5xx_rate.json missing (not collected or no Prometheus)), `controlplane.apiserver-latency` (skip: metrics/apiserver_p99_latency_by_verb.json missing (not collected or no Prometheus)), `controlplane.webhook-latency` (skip: metrics/apiserver_webhook_p99_by_name.json missing (not collected or no Prometheus)), `controlplane.webhook-call-failures` (skip: control plane logs not read (CloudWatch Logs Insights: logs/cloudwatch/volume_by_stream.json missing)), `controlplane.controller-error-repeat` (skip: control plane logs not read (CloudWatch Logs Insights: logs/cloudwatch/volume_by_stream.json missing)), `controlplane.apiserver-slow-traces` (skip: control plane logs not read (CloudWatch Logs Insights: logs/cloudwatch/volume_by_stream.json missing)), `controlplane.authenticator-failures` (skip: control plane logs not read (CloudWatch Logs Insights: logs/cloudwatch/volume_by_stream.json missing)), `node.kernel-oom-node-level` (skip: nothing to judge: node not read (9)), `node.kernel-lockup` (skip: nothing to judge: node not read (9)), `node.kernel-io-fs-errors` (skip: nothing to judge: node not read (9)), `node.kernel-nic-events` (skip: nothing to judge: node not read (9)), `node.conntrack-table-full` (skip: nothing to judge: node not read (9)), `node.kernel-net-mem-pressure` (skip: nothing to judge: node not read (9)), `node.cgroup-v1` (skip: nothing to judge: node not read (9)), `node.sysctl-tuning` (skip: nothing to judge: node not read (9)), `node.cri-not-ready` (skip: nothing to judge: node not read, or cri not read (9)), `node.cri-exited-containers` (skip: nothing to judge: node not read (9)), `node.pod-logs-large` (skip: summary.nodeos.pod_logs missing), `node.pod-dir-large` (skip: summary.nodeos.pod_dirs missing), `node.service-restarts` (skip: nothing to judge: node not read (9)), `node.reboot-required` (skip: nothing to judge: node not read (9)), `node.os-updates-pending` (skip: nothing to judge: node not read (9)), `node.kubelet-reserved-missing` (skip: nothing to judge: node not read, or kubelet not read (9)), `node.kubelet-eviction-memory-missing` (skip: nothing to judge: node not read, or kubelet not read (9)), `node.clock-unsynced-os` (skip: nothing to judge: node not read (9)), `node.zombie-processes` (skip: nothing to judge: node not read (9)), `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `observability.alert-firing-stale` (skip: metrics/alerts_firing_stale_days.json missing (not collected or no Prometheus)), `cost.idle-compute-high` (skip: nothing to judge: pricing (pricing:GetProducts) or node CPU usage metrics (node_cpu_usage_ratio_p95_7d) not read), `cost.request-waste` (skip: nothing to judge: pricing (pricing:GetProducts) or the KRR totals not read), `cost.unused-eip` (skip: nothing to judge: EC2 addresses not read (ec2:DescribeAddresses)), `cost.idle-load-balancer` (skip: nothing to judge: load balancers not read (elasticloadbalancing:Describe*)), `cost.idle-node` (skip: node CPU usage metrics not read (node_cpu_usage_ratio_p95_7d)), `security.networkpolicy-not-enforced` (skip: nothing to judge: NetworkPolicy objects not read (objects/networkpolicies.networking.k8s.io.json denied, failed or without a record)), `security.no-default-deny` (skip: nothing to judge: NetworkPolicy objects not read (objects/networkpolicies.networking.k8s.io.json denied, failed or without a record)), `security.imds-hop-limit` (skip: nothing to judge: not EKS, or EC2 instance list not read (ec2:DescribeInstances)), `storage.pvc-usage-high` (skip: nothing to judge: PVC usage metrics not read (kubelet_volume_stats_*) (18)), `storage.ebs-unattached` (skip: nothing to judge: ebs not available), `storage.ebs-gp2-volumes` (skip: nothing to judge: ebs not available), `storage.ebs-unencrypted` (skip: nothing to judge: ebs not available), `hygiene.eks-upgrade-insight` (skip: EKS upgrade insights not read (aws/list-insights.json missing: eks:ListInsights refused or not an EKS cluster)), `hygiene.orphan-secrets` (skip: nothing to judge: Secret names not read (kube_secret_info through Prometheus)), `traffic.lb-idle-timeout-long` (skip: summary.traffic.alb.lbs missing), `traffic.alb-target-type-instance` (skip: summary.traffic.alb.target_groups missing), `node.memory-available-low` (skip: metrics/node_memory_available_ratio.json missing (not collected or no Prometheus)), `node.network-errors` (skip: metrics/node_network_errors_1d.json missing (not collected or no Prometheus)), `node.timewait-sockets-high` (skip: metrics/node_tcp_timewait.json missing (not collected or no Prometheus)), `node.kubelet-pleg-slow` (skip: metrics/kubelet_pleg_p99_1h.json missing (not collected or no Prometheus)), `controlplane.watch-count-high` (skip: metrics/apiserver_watch_per_node.json missing (not collected or no Prometheus)), `controlplane.apiserver-401-rate` (skip: metrics/apiserver_401_rate_1h.json missing (not collected or no Prometheus)), `controlplane.etcd-db-size` (skip: metrics/apiserver_storage_size_bytes.json missing (not collected or no Prometheus)), `node.kubelet-api-qps-low` (skip: nothing to judge: node not read, or kubelet not read (9)), `traffic.ingress-5xx-ratio` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (41)), `traffic.ingress-p95-latency` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (41)), `traffic.alb-elb-5xx` (skip: summary.traffic.alb.lbs missing), `traffic.alb-unhealthy-targets` (skip: summary.traffic.alb.unhealthy_target_groups missing), `traffic.alb-deregistration-vs-grace` (skip: summary.traffic.alb.target_groups missing), `traffic.alb-protection-off` (skip: summary.traffic.alb.lbs missing), `traffic.db-exposed` (skip: nothing to judge: load balancer security groups not read (elasticloadbalancing:Describe*, ec2:DescribeSecurityGroups)), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing), `traffic.pod-not-ready` (skip: pod readiness ratio not read (metrics/pod_ready_ratio_24h.json missing or failed)), `traffic.coredns-latency` (skip: nothing to judge: CoreDNS metrics not read (coredns_dns_request_duration_seconds)), `scaling.hpa-at-max` (skip: metrics/hpa_at_max_ratio_15d.json missing (not collected or no Prometheus)), `scaling.hpa-never-scaled` (skip: nothing to judge: HPA metrics not read (hpa_at_min_ratio_15d) (18)), `scaling.hpa-flapping` (skip: metrics/hpa_desired_changes_7d.json missing (not collected or no Prometheus)), `scaling.pod-pending-long` (skip: metrics/pod_pending_seconds.json missing (not collected or no Prometheus)), `tenancy.burst-tenant-unbounded` (skip: nothing to judge: namespace CPU metrics not read (namespace_cpu_max_7d, namespace_cpu_median_7d) (26)), `node.docker-and-containerd` (skip: nothing to judge: node not read (9)), `node.container-writable-layer-large` (skip: nothing to judge: node not read (9)), `node.large-images` (skip: nothing to judge: node not read (9)), `eks.addon-outdated` (skip: nothing to judge: add-on versions not read (eks:DescribeAddonVersions) (4)), `eks.ssm-unregistered` (skip: inventory.node_access.ssm_unregistered missing), `eks.no-backup-policy` (skip: nothing to judge: dlm get-lifecycle-policies or backup list-backup-plans not read), `eks.acm-certificate-expiring` (skip: nothing to judge: acm not available), `eks.service-quota-near-limit` (skip: nothing to judge: quotas not available), `storage.ebs-volume-io-saturated` (skip: nothing to judge: ebs not available), `eks.security-group-open-to-world` (skip: nothing to judge: security groups not available), `eks.nodegroup-ami-old` (skip: nothing to judge: nodegroups not available), `albctl.target-group-without-tgb` (skip: nothing to judge: ALB target groups not read (elasticloadbalancing:Describe*)), `alertmanager.receivers-unused-or-no-inhibit` (skip: nothing to judge: alertmanager not present, or its configuration could not be parsed (config_parse_error)), `alertmanager.notifications-silent` (skip: nothing to judge: alertmanager not present; metrics not read), `coredns.nxdomain-ratio-high` (skip: nothing to judge: metrics not read), `coredns.cache-hit-low` (skip: nothing to judge: metrics not read), `coredns.aaaa-noise` (skip: nothing to judge: metrics not read), `coredns.forward-upstream-errors` (skip: nothing to judge: metrics not read), `coredns.panic-or-reload-failed` (skip: nothing to judge: metrics not read), `coredns.pod-imbalance` (skip: nothing to judge: metrics not read), `ebscsi.node-ops-errors` (skip: nothing to judge: kubelet metrics not read), `ecr.scan-disabled` (skip: summary.ecr.summary missing), `ecr.tag-mutable-prod` (skip: summary.ecr.summary missing), `ecr.no-lifecycle-policy` (skip: summary.ecr.summary missing), `ecr.stale-storage` (skip: summary.ecr.summary missing), `ecr.dockerhub-dependency` (skip: summary.ecr.summary missing), `ecr.pull-failures` (skip: summary.ecr.summary missing), `ecr.no-replication` (skip: summary.ecr.summary missing), `ecr.untagged-images` (skip: summary.ecr.summary missing), `kubeproxy.sync-slow` (skip: nothing to judge: metrics not read), `kubeproxy.rules-pending` (skip: nothing to judge: metrics not read), `kubeproxy.restore-failures` (skip: nothing to judge: metrics not read), `kubeproxy.conntrack-invalid-drops` (skip: nothing to judge: conntrack INVALID counter not served: kube-proxy 1.30, ipvs or nftables mode, no nfacct, or the proxy mode not read (summary ct_invalid_reason says which)), `vpccni.node-ip-exhaustion` (skip: nothing to judge: pod IP usage not read (no ipamd metrics and the instance type's limits not read: ec2:DescribeInstanceTypes) (9)), `vpccni.no-available-ip` (skip: nothing to judge: VPC CNI metrics not read (awscni_no_available_ip_addresses) (9)), `vpccni.prefix-delegation-off` (skip: nothing to judge: pod IP usage of no node read (no ipamd metrics and the instance types' limits not read: ec2:DescribeInstanceTypes)), `vpccni.ec2-api-errors` (skip: nothing to judge: metrics not read (9)), `vpccni.external-snat-off-with-private-routes` (skip: summary.vpccni.snat missing)
- 일부만 판정한 점검 항목 0 (판정에 필요한 자료가 없는 대상은 판정하지 않았고 통과로 세지 않았어요): 없음
- 질의 결과가 빈 항목 0 (질의가 읽는 메트릭 이름이 모두 있으므로 그런 일이 없었다는 뜻이에요. 이름 자체가 없으면 건너뜀으로 처리해요): 없음

## 7. 부록

### 7-1. 실행한 수집기와 단계

| 수집기 | 단계 | 실패 | 건너뜀 (이유) |
|---|---|---|---|
| core | 13 | events, metrics.core | node-os (no node command backend) |
| eks-platform | 29 | nodegroup, addon-versions, cluster-versions, insights, subnets, route-tables, ssm-instances, cluster-security-groups, controlplane-logs, dlm-policies, backup-plans, alb-metrics, ec2-volumes, ec2-volumes-available, ec2-snapshots-30d, ec2-instances-imds, pod-identity-associations, ec2-addresses, ec2-nat-gateways, ec2-spot-prices, pricing-ondemand, ce-cost-30d, acm-certificates, service-quotas, quota-usage, ec2-root-volumes, ebs-volume-metrics | kubelet-journal (no node command backend); containerd-journal (no node command backend) |
| actions-runner-controller | 0 |  | no collect.yaml (collector not implemented) |
| alb-controller | 1 |  |  |
| alertmanager | 4 |  | status (no alertmanager connection); silences (no alertmanager connection); alerts (no alertmanager connection); receivers (no alertmanager connection) |
| argocd | 3 |  |  |
| coredns | 1 | metrics |  |
| ebs-csi | 1 | metrics |  |
| ecr | 5 | registry, scanning-configuration, pull-through-cache, images, lifecycle-policy |  |
| external-dns | 0 |  | no collect.yaml (collector not implemented) |
| external-secrets | 1 |  |  |
| grafana | 5 |  | datasources (grafana_api_token missing); dashboards (grafana_api_token missing); dashboards-json (grafana_api_token missing) |
| karpenter | 1 |  |  |
| keda | 2 |  | operator-metrics (container arg --enable-prometheus-metrics=false: no metrics is expected) |
| kube-proxy | 2 | metrics | proxy-mode (no node command backend) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| loki | 9 | metrics.loki |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 | metrics.observability | rules (no prometheus connection); targets (no prometheus connection); runtime (no prometheus connection); tsdb-status (no prometheus connection); flags (no prometheus connection); buildinfo (no prometheus connection) |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| promtail | 0 |  | no collect.yaml (collector not implemented) |
| victoria-metrics | 0 |  | no collect.yaml (collector not implemented) |
| vpc-cni | 3 | instance-type-network | ipamd-metrics (no node command backend); ipamd-log (no node command backend) |

ClusterRole에 없는 종류 1개예요. 이 종류가 필요한 점검 항목은 통과가 아니라 건너뜀으로 처리해요: `networkpolicies.networking.k8s.io`

이 클러스터가 제공하지 않는 종류 7개예요. 이 종류가 필요한 점검 항목은 통과가 아니라 건너뜀으로 처리해요: `certificates.cert-manager.io`, `clusterissuers.cert-manager.io`, `horizontalrunnerautoscalers.actions.summerwind.dev`, `issuers.cert-manager.io`, `runnerdeployments.actions.summerwind.dev`, `volumesnapshotclasses.snapshot.storage.k8s.io`, `volumesnapshots.snapshot.storage.k8s.io`

명령 701개, 300.7초. 실패한 단계 40개: `core.events` Error from server (Forbidden): events is forbidden: User "kubegap" cannot list resource "events" in API group "" at the …; `core.metrics.core` no Prometheus connection; `eks-platform.nodegroup` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.addon-versions` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.cluster-versions` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.insights` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.subnets` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.route-tables` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ssm-instances` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.cluster-security-groups` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.controlplane-logs` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.dlm-policies` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.backup-plans` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.alb-metrics` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ec2-volumes` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ec2-volumes-available` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ec2-snapshots-30d` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ec2-instances-imds` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.pod-identity-associations` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …; `eks-platform.ec2-addresses` An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the …

단계는 성공했지만 그 안에서 실패한 명령 22개 (run.log): `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.kubelet-journal.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.kubelet-journal.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `vpc-cni.ipamd-metrics.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `vpc-cni.ipamd-metrics.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `vpc-cni.ipamd-log.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `vpc-cni.ipamd-log.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

지원 종료 API 도구: kubent List 41번 중 28번 응답 (13번은 거부되었거나 없는 API); pluto 오브젝트 종류 95개 중 95개 저장 (0개는 권한이 없거나 실패); kubent had 167 objects with a last-applied annotation to judge; pluto had 345 objects with a last-applied annotation to judge.

### 7-2. 판정한 점검 항목

점검 항목 367개: disabled 2, done 231, llm 2, skip 132. 불러오기 오류: 없음.

### 7-3. 로그 시그니처 일치와 분류 안 된 오류

로그 시그니처 1.1.0으로 파일 23개, 23380줄을 읽었어요 (컴포넌트: actions-runner-controller, alb-controller, argocd, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). 분류 안 된 오류는 24줄이에요.

| 시그니처 | 컴포넌트 | 영역 | 심각도 | 상태 | 횟수 | 처음, 마지막 | 샘플 |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 62 | 2026-11-06T17:31:20Z , 2026-11-07T01:34:43Z | [pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:31:20.550454017Z … |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-06T08:49:38Z , 2026-11-06T08:49:38Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-06T08:49:38.045274596Z … |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-06T20:55:55Z , 2026-11-07T01:36:03Z | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:55.112553385Z W1106 20:55:55.112429       1 reflector.go:561] … |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 31 | 2026-11-06T01:43:11Z , 2026-11-06T10:09:11Z | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T01:43:11.055572813Z E1106 01:43:11.055448       1 scraper.go:149] "Failed to scrape node" … |
| karpenter.spot-interruption | karpenter | resilience | low | info | 2 | 2026-11-06T02:44:15Z , 2026-11-06T09:09:11Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-06T02:44:15.312621214Z … |

| 메시지 형태 | 횟수 | 파일 |
|---|---|---|
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node … | 8 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| ebs-csi \| "Volume deletion failed" err="persistentvolume pvc-<uuid> is still attached to node ip-10-0-1-98.ap-northeast-2.compute.internal" … | 4 | logs/pods/ebs-csi/kube-system_ebs-csi-controller.log |
| ebs-csi \| "Unhandled Error" err="error syncing volume \"pvc-<uuid>\": persistentvolume pvc-<uuid> is still attached to node … | 4 | logs/pods/ebs-csi/kube-system_ebs-csi-controller.log |
| ebs-csi \| "Event occurred" object="prod-app-x/app-x-api-usage" fieldPath="" kind="PersistentVolumeClaim" apiVersion="v1" type="Warning" … | 3 | logs/pods/ebs-csi/kube-system_ebs-csi-controller.log |
| ebs-csi \| "Unhandled Error" err="error syncing claim \"<uuid>\": failed to provision volume with StorageClass \"gp3\": error generating accessibility … | 3 | logs/pods/ebs-csi/kube-system_ebs-csi-controller.log |
| kube-proxy \| "Kube-proxy configuration may be incomplete or incorrect" err="nodePortAddresses is unset; NodePort connections will be accepted on all … | 2 | logs/pods/kube-proxy/kube-system_kube-proxy.log |

### 7-4. 에이전트가 직접 읽은 원본 파일

(이번 점검에서 쓰지 않음)

### 7-5. 자동 판정 전체 (모든 fail과 warn, 코드 결과 그대로)

| id | 상태 | 기본 심각도 | 근거 |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `observability.no-slo.cluster` | warn | critical | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] known issue #15 |
| `observability.no-symptom-alerts.cluster` | warn | critical | 157 alert rules: symptom 0, cause 130, app metrics (assumed symptom) 22. Symptom ratio 0.0. Symptom rules: [] |
| `resilience.n-plus-one.cluster` | warn | critical | Allocatable without the largest node ip-10-0-1-139.ap-northeast-2.compute.internal (3.92 cores, 29.8GB): CPU 15.45 cores vs total requests 11.51 (OK), memory 46.3GB vs 45.7GB (OK). Pods on that node 34 (prod 23). Pods that fit on no other node []. Pools short of room: 32 pods limited to … |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 289MB |
| `observability.no-event-retention.cluster` | fail | high | no component of family event-retention in inventory.components |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 252 days past |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.prod-concentration.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | high | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default, spot) holds prod pods 23/45 (0.51), 18 workloads: ['app-ab-prod/app-ab-backend', 'app-ab-prod/app-ab-frontend', 'prod-app-s/app-s-admin', 'prod-app-s/app-s-api', 'prod-app-s/app-s-backend', 'prod-app-s/app-s-frontend' … |
| `resilience.replicas-same-node.prod-app-w/deployment/app-w` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-ai` | fail | high | replicas 3 (Running 3), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 3}, AZ distribution {'ap-northeast-2a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-backend` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-z-backend/deployment/app-z-frontend` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 4 |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/tts-proxy` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 62 occurrences (2026-11-06T17:31:20Z ~ 2026-11-07T01:34:43Z), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: ['[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:31:20.550454017Z … |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-06T08:49:38Z ~ 2026-11-06T08:49:38Z), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-06T08:49:38.045274596Z … |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit None (limit 1536Mi), active series None, Prometheus container last terminated OOMKilled True (2026-11-05T08:21:29Z), restarts 2, OOMKilled containers in the monitoring namespace [], restarts over 7 days {} |
| `resilience.replicas-same-node.prod-app-x/deployment/app-x-api` | warn | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 1, 'ip-10-0-1-137.ap-northeast-2.compute.internal': 1}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 13/13 (prod 9) |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-2a', 'gp3-2c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-2a', 'gp3-2c'] |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 31963 / errors 2711 (ratio 0.0782), sync failures 2711/73134, reconcile errors 2711, ExternalSecrets not Ready ['database/externalsecret/mysql-app-v-secret'] (oldest refresh 7796.6 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2614, {'101': 4, '200': 2275, '400': 6, '429': 329}), ('Prometheus(prometheus)', 1535, {'200': 1349, '301': 186}), ('VictoriaMetrics_onprem(prometheus)', 142, {'200': 142})], error rate 1% or more ['Loki(loki)'] (max 0.1259), Grafana … |
| `hygiene.mutable-image-tag.prod-app-z-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.polaris-reliability-danger.prod-app-z-backend/deployment/tts-proxy` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing']. Security-category danger ['dangerousCapabilities', 'privilegeEscalationAllowed' … |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 147 pods Running for over 1h, 83 are absent from Loki pod labels (ratio 0.565). Nodes with every pod missing: []. By namespace: {'kube-system': 23, 'monitoring': 22, 'prod-app-z-backend': 5, 'keda': 3, 'middleware': 3, 'prod-app-t': 3, 'prod-app-s': 3, 'argocd': 2, 'dev-app-s': 2, 'dev-app-y' … |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `operators.unhealthy-condition.externalsecrets/database/mysql-app-v-secret` | fail | medium | Ready=False (SecretSyncedError) for 7795.6 hours: could not get secret data from provider |
| `resilience.db-probe-timeout.prod-app-s/statefulset/app-s-backend-mysql:mysql` | fail | medium | prod-app-s/statefulset/app-s-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | fail | medium | prod-app-v/statefulset/app-v-backend-prod-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-y/statefulset/app-y-backend-mysql:mysql` | fail | medium | prod-app-y/statefulset/app-y-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | medium | prod-app-z-backend/statefulset/app-z-neo4j container neo4j: liveness tcpSocket timeout 1s, period 30s, failureThreshold 3, readiness tcpSocket timeout 1s, startupProbe absent |
| `resilience.no-pdb.prod-app-x/app-x-api` | fail | medium | replicas 2, no PDB selects these pods |
| `resilience.no-pdb.prod-app-y/app-y-ai` | fail | medium | replicas 3, no PDB selects these pods |
| `resilience.no-pdb.prod-app-y/app-y-backend` | fail | medium | replicas 2, no PDB selects these pods |
| `resilience.no-readiness-probe.app-ab-prod/app-ab-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.app-ab-prod/app-ab-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.prod-app-v/app-v-admin-frontend` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-v/app-v-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-v/app-v-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.prod-app-y/app-y-admin` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-y/app-y-ai` | fail | medium | containers without a readinessProbe: ai |
| `resilience.no-readiness-probe.prod-app-y/app-y-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-y/app-y-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.prod-app-z-backend/tts-proxy` | fail | medium | containers without a readinessProbe: tailscale, forwarder |
| `resilience.recreate-strategy-serving.prod-app-r/deployment/app-r-backend` | fail | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.replicas-same-zone.prod-app-x/deployment/app-x-api` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 1, 'ip-10-0-1-137.ap-northeast-2.compute.internal': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-embedding-server` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 1, 'ip-10-0-1-245.ap-northeast-2.compute.internal': 1}, topologySpread [] |
| `resilience.single-node-dependency.prod-app-z-backend/deployment/tts-proxy` | fail | medium | ["hostPath volume ['dev-net-tun']"], replicas 1 |
| `resilience.single-replica-in-prod.app-ab-prod/app-ab-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ab-prod/app-ab-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-r/app-r-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-r/app-r-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-s/app-s-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-ai` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-studio` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-admin-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-y/app-y-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-y/app-y-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-z-backend/app-z-pg-proxy` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-z-backend/tts-proxy` | fail | medium | replicas 1, no HPA |
| `resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter` | fail | medium | middleware/statefulset/kafka-controller container jmx-exporter (jmx-exporter:0.20.0-debian-11-r4): -Xmx NoneMiB, MaxRAMPercentage 100.0, memory limit 128.0MiB -> heap/limit 1.0 (heap unset False) |
| `resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller` | fail | medium | memory request under by 373 MB, CPU request over by 0.143 cores: CPU request 0.2 → 0.057 cores, CPU limit 0.5 → none, memory request 384 → 757 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql` | fail | medium | memory request under by 281 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 793 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.dev-app-y/deployment/app-y-ai:ai` | fail | medium | memory request over by 628 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 396 MB, memory limit 2048 → 396 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-y/statefulset/app-y-backend-mysql:mysql` | fail | medium | memory request under by 355 MB: CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 867 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/loki-stack:loki` | fail | medium | memory request under by 273 MB: CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 529 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 851 MB: CPU request 0.2 → 0.137 cores, CPU limit 0.5 → none, memory request 800 → 1651 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle` | fail | medium | CPU request over by 0.29 cores, memory request over by 316 MB: CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 196 MB, memory limit 1024 → 196 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-r/deployment/app-r-backend:backend` | fail | medium | CPU request over by 0.348 cores: CPU request 0.5 → 0.152 cores, CPU limit 2.0 → none, memory request 1024 → 866 MB, memory limit 2048 → 866 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-s/deployment/app-s-backend:backend` | fail | medium | memory request under by 298 MB: CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 426 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-s/statefulset/app-s-backend-mysql:mysql` | fail | medium | memory request under by 404 MB, CPU request over by 0.188 cores: CPU request 0.2 → 0.012 cores, CPU limit 1.0 → none, memory request 768 → 1172 MB, memory limit 1536 → 1172 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-ai:ai` | fail | medium | memory request under by 351 MB: CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 607 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.prod-app-x/deployment/app-x-api:api` | fail | medium | CPU request over by 0.49 cores, memory request over by 660 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 1024 → 364 MB, memory limit 2048 → 364 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-y/deployment/app-y-ai:ai` | fail | medium | memory request over by 963 MB: CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 1085 MB, memory limit 4096 → 1085 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-embedding-server:embedding` | fail | medium | memory request under by 2651 MB, CPU request over by 0.425 cores: CPU request 0.5 → 0.075 cores, CPU limit 2.0 → none, memory request 4096 → 6747 MB, memory limit 6144 → 6747 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-file-worker:file-worker` | fail | medium | CPU request over by 0.703 cores, memory request over by 337 MB: CPU request 1.0 → 0.297 cores, CPU limit 2.0 → none, memory request 2048 → 1711 MB, memory limit 4096 → 1711 MB. KRR severity CRITICAL (CPU req CRITICAL, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker` | fail | medium | CPU request over by 0.458 cores, memory request over by 670 MB: CPU request 1.0 → 0.542 cores, CPU limit 2.0 → none, memory request 2048 → 1378 MB, memory limit 6144 → 1378 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | medium | CPU request over by 0.49 cores, memory request over by 2417 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1679 MB, memory limit 5120 → 1679 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.no-memory-limit.prod-app-z-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node ip-10-0-1-139.ap-northeast-2.compute.internal (r8gd.xlarge spot): age 1056.5h, 336.5h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {}. do-not-disrupt pods on this node 2: prod-app-s/app-s-admin-57f5fcc58d-khsh5, prod-app-x/app-x-api-5755745bc7-2sjvd |
| `security.externalsecret-not-ready.database/mysql-app-v-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.no-certificate-manager.cluster` | fail | medium | no component of family certificates in inventory.components |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 79. Security danger workloads 74 (prod 29): per check {'dangerousCapabilities': 2, 'hostNetworkSet': 2, 'privilegeEscalationAllowed': 59, 'runAsPrivileged': 2, 'runAsRootAllowed': 58, 'hostPIDSet': 1, 'rolebindingClusterAdminRole': 2, 'rolebindingRolePodExecAttach': 2 … |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days None None, prod PVCs 8 |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.prod-boundary-missing.app-ab-prod` | fail | medium | app-ab-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-r` | fail | medium | prod-app-r: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-s` | fail | medium | prod-app-s: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-t` | fail | medium | prod-app-t: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-v` | fail | medium | prod-app-v: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-w` | fail | medium | prod-app-w: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-x` | fail | medium | prod-app-x: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-y` | fail | medium | prod-app-y: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-z-backend` | fail | medium | prod-app-z-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `traffic.shared-alb-group.alb-group/app-u-prod-lb` | fail | medium | ALB group app-u-prod-lb: 41 ingresses, 48 hosts, 16 namespaces ['app-ab-prod', 'argocd', 'dev-app-aa', 'dev-app-s', 'dev-app-v', 'dev-app-y', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-s', 'prod-app-t', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend'], kinds … |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.lab-k.example |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version … |
| `eks.extended-support.cluster` | warn | medium | version 1.32, supportType EXTENDED, status None, end of standard support None, end of extended support None |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.app-u.ai/role` | warn | medium | Label app-u.ai/role: 34 workloads (production 9) depend on it via nodeSelector/affinity, present on 5/9 nodes — e.g. argocd/deployment/argocd-applicationset-controller, argocd/deployment/argocd-dex-server, argocd/deployment/argocd-notifications-controller |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 39 workloads (production 26) depend on it via nodeSelector/affinity, present on 4/9 nodes — e.g. dev-app-s/deployment/app-s-admin, dev-app-s/deployment/app-s-api, dev-app-s/deployment/app-s-backend |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-cool-down` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-warm-up` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.middleware/deployment/redis-insight` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed' … |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 30.9s (8787 pods), node termination average 14.7s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-y/scaledobject/app-y-ai-kafka-lag', 'prod-app-z-backend/scaledobject/app-z-file-worker', 'prod-app-z-backend/scaledobject/app-z-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-06T20:55:55Z ~ 2026-11-07T01:36:03Z), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:55.112553385Z W1106 20:55:55.112429       1 … |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 31 occurrences (2026-11-06T01:43:11Z ~ 2026-11-06T10:09:11Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T01:43:11.055572813Z E1106 01:43:11.055448       1 scraper.go:149] … |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | warn | medium | RSS 289MiB / limit 512Mi = 0.565, in-memory streams 54, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 1 5xx out of 6899928 requests since start (by route {'loki_api_v1_series': 1}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 11783, rejected {} |
| `observability.golden-signals-missing.app-ab-prod/app-ab-backend` | warn | medium | hosts ['app-ab-tp-api.lab-k.example'], backends ['app-ab-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.app-ab-prod/app-ab-frontend` | warn | medium | hosts ['app-ab-tp-prod.lab-k.example'], backends ['app-ab-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.argocd/argocd-server` | warn | medium | hosts ['deploy.lab-k.example'], backends ['argocd-server'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-aa/app-aa-backend` | warn | medium | hosts ['demo-api.lab-m.example'], backends ['app-aa-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-aa/app-aa-frontend` | warn | medium | hosts ['demo.lab-m.example'], backends ['app-aa-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-s/app-s-admin` | warn | medium | hosts ['admin-dev.lab-l.example'], backends ['app-s-admin'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-s/app-s-api` | warn | medium | hosts ['api-dev.v1.lab-l.example'], backends ['app-s-api'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-s/app-s-backend` | warn | medium | hosts ['api-dev.lab-l.example'], backends ['app-s-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-s/app-s-frontend` | warn | medium | hosts ['dev.lab-l.example'], backends ['app-s-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-v/app-v-admin-frontend` | warn | medium | hosts ['admin-dev.lab-n.example'], backends ['app-v-admin-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-v/app-v-backend` | warn | medium | hosts ['api-dev.lab-n.example'], backends ['app-v-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-v/app-v-frontend` | warn | medium | hosts ['dev.lab-n.example'], backends ['app-v-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-y/app-y-admin` | warn | medium | hosts ['admin-dev.lab-m.example'], backends ['app-y-admin'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-y/app-y-ai` | warn | medium | hosts ['ai-dev.lab-m.example'], backends ['app-y-ai'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-y/app-y-backend` | warn | medium | hosts ['app-y-api-dev.lab-k.example'], backends ['app-y-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.dev-app-y/app-y-frontend` | warn | medium | hosts ['app-y-dev.lab-k.example'], backends ['app-y-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.middleware/kafka-ui` | warn | medium | hosts ['kafka.lab-k.example'], backends ['kafka-ui'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.middleware/redis-insight` | warn | medium | hosts ['redis.lab-k.example'], backends ['redis-insight'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.monitoring/kube-prometheus-stack-grafana` | warn | medium | hosts ['monitor.lab-k.example'], backends ['kube-prometheus-stack-grafana'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.monitoring/vmauth` | warn | medium | hosts ['metrics-write.lab-k.example'], backends ['vmauth'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-r/app-r-backend` | warn | medium | hosts ['app-r-api.lab-k.example'], backends ['app-r-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-r/app-r-web` | warn | medium | hosts ['app-r.lab-k.example'], backends ['app-r-web'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-s/app-s-admin` | warn | medium | hosts ['canary-admin.lab-l.example', 'admin.lab-l.example'], backends ['app-s-admin'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-s/app-s-api` | warn | medium | hosts ['canary-api-v1.lab-l.example', 'api.v1.lab-l.example'], backends ['app-s-api'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-s/app-s-backend` | warn | medium | hosts ['canary-api.lab-l.example', 'api.lab-l.example'], backends ['app-s-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-s/app-s-frontend` | warn | medium | hosts ['canary.lab-l.example', 'www.lab-l.example', 'lab-l.example'], backends ['app-s-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-t/app-t-ai` | warn | medium | hosts ['app-t-ai.lab-k.example'], backends ['app-t-ai'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-t/app-t-backend` | warn | medium | hosts ['app-t-api.lab-k.example'], backends ['app-t-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-t/app-t-studio` | warn | medium | hosts ['app-t-studio.lab-k.example'], backends ['app-t-studio'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-t/app-t-web` | warn | medium | hosts ['app-t.lab-k.example'], backends ['app-t-web'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-v/app-v-admin-frontend` | warn | medium | hosts ['admin.lab-n.example'], backends ['app-v-admin-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-v/app-v-backend` | warn | medium | hosts ['api.lab-n.example'], backends ['app-v-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-v/app-v-frontend` | warn | medium | hosts ['lab-n.example', 'www.lab-n.example'], backends ['app-v-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-w/app-w` | warn | medium | hosts ['app-w.lab-k.example'], backends ['app-w'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-x/app-x-api` | warn | medium | hosts ['app-x-api.lab-k.example'], backends ['app-x-api'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-y/app-y-admin` | warn | medium | hosts ['admin.lab-m.example'], backends ['app-y-admin'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-y/app-y-ai` | warn | medium | hosts ['ai.lab-m.example'], backends ['app-y-ai'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-y/app-y-backend` | warn | medium | hosts ['api.lab-m.example'], backends ['app-y-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-y/app-y-frontend` | warn | medium | hosts ['lab-m.example', 'www.lab-m.example'], backends ['app-y-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-z-backend/app-z-backend` | warn | medium | hosts ['app-z-api.lab-k.example'], backends ['app-z-backend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.golden-signals-missing.prod-app-z-backend/app-z-frontend` | warn | medium | hosts ['app-z.lab-k.example'], backends ['app-z-frontend'], no app http_* metrics, no ingress controller metrics, source alb-cloudwatch (not collected) |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 36 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown', 'AlertmanagerClusterCrashlooping', 'etcdMembersDown' … |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-mysql:mysql` | warn | medium | dev-app-aa/statefulset/app-aa-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-postgres:postgres` | warn | medium | dev-app-aa/statefulset/app-aa-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | medium | dev-app-s/statefulset/app-s-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql` | warn | medium | dev-app-v/statefulset/app-v-backend-dev-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-y/statefulset/app-y-backend-mysql:mysql` | warn | medium | dev-app-y/statefulset/app-y-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` | warn | medium | monitoring/statefulset/loki-stack container loki: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 111, 'system-cluster-critical': 9, 'system-node-critical': 27}, prod pods without a class 45 of 45, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.cluster` | warn | medium | Of 18 DB workloads with a PVC, production DBs without a backup CronJob in the same namespace: ['app-ab-prod/statefulset/app-ab-backend-postgresql', 'prod-app-r/statefulset/app-r-postgresql', 'prod-app-s/statefulset/app-s-backend-mysql', 'prod-app-t/statefulset/app-t-backend-postgresql' … |
| `resilience.recreate-strategy-serving.monitoring/deployment/vmauth` | warn | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master` | warn | medium | Containers whose command is sh -c ['redis', 'metrics'], no preStop, terminationGracePeriodSeconds 30 |
| `resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 257 MB, memory limit 1024 → 257 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-aa/statefulset/app-aa-mysql:mysql` | warn | medium | CPU request over by 0.19 cores, memory request over by 341 MB: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | medium | memory request under by 114 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 626 MB, memory limit 1024 → 626 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.dev-app-y/deployment/app-y-backend:backend` | warn | medium | memory request over by 359 MB: CPU HPA detected, memory request 512 → 153 MB, memory limit 8192 → 153 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.karpenter/deployment/karpenter:controller` | warn | medium | memory request under by 152 MB, CPU request over by 0.18 cores: CPU request 0.2 → 0.02 cores, CPU limit 0.5 → none, memory request 256 → 408 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka` | warn | medium | CPU request over by 0.13 cores: CPU request 0.2 → 0.07 cores, CPU limit 0.5 → none, memory request 1536 → 1466 MB, memory limit 2048 → 1466 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail` | warn | medium | memory request under by 144 MB: CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 272 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-r/deployment/app-r-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-s/deployment/app-s-frontend:frontend` | warn | medium | memory request under by 222 MB: CPU request 0.01 → 0.031 cores, CPU limit 0.2 → none, memory request 128 → 350 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-backend:backend` | warn | medium | memory request under by 189 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 381 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-v/deployment/app-v-backend:backend` | warn | medium | memory request under by 89 MB: CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 217 MB, memory limit 512 → 217 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | warn | medium | CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 812 MB, memory limit 1536 → 812 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-y/deployment/app-y-backend:backend` | warn | medium | memory request over by 396 MB: CPU request 0.1 → 0.01 cores, CPU limit 2.0 → none, memory request 512 → 116 MB, memory limit 2048 → 116 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-y/statefulset/app-y-backend-mysql:mysql` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-backend:backend` | warn | medium | memory request over by 410 MB: CPU HPA detected, memory request 1024 → 614 MB, memory limit 2048 → 614 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-pg-proxy:forwarder` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['app-ab-prod', 'prod-app-r', 'prod-app-s', 'prod-app-t', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend']. Share of containers allowing root 0.61 (29 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 86/92, of which 30 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-w/deployment/app-w', 'prod-app-t/deployment/app-t-ai', 'prod-app-t/deployment/app-t-backend', 'prod-app-t/deployment/app-t-studio', 'prod-app-t/deployment/app-t-web' … |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-t/data-app-t-backend-postgresql-0', 'prod-app-x/data-app-x-postgresql-0', 'prod-app-s/data-app-s-backend-mysql-0', 'prod-app-y/data-app-y-backend-mysql-0', 'prod-app-z-backend/data-app-z-neo4j-0', 'prod-app-r/data-app-r-postgresql-0' … |
| `tenancy.prod-without-quota.app-ab-prod` | warn | medium | app-ab-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 0, CPU requests total 0.0 cores, memory requests total 0.0GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-aa` | warn | medium | dev-app-aa (dev): no ResourceQuota. Pods 4, CPU requests total 0.55 cores, memory requests total 1.88GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-s` | warn | medium | dev-app-s (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-v` | warn | medium | dev-app-v (dev): no ResourceQuota. Pods 4, CPU requests total 0.3 cores, memory requests total 1.0GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-y` | warn | medium | dev-app-y (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 2.25GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-r` | warn | medium | prod-app-r (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-s` | warn | medium | prod-app-s (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-t` | warn | medium | prod-app-t (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-v` | warn | medium | prod-app-v (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-w` | warn | medium | prod-app-w (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-x` | warn | medium | prod-app-x (prod): no ResourceQuota. Pods 3, CPU requests total 1.1 cores, memory requests total 2.25GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-y` | warn | medium | prod-app-y (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-z-backend` | warn | medium | prod-app-z-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 None cores (cluster share None), memory p95 NoneGB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.ip-10-0-1-117.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-1-117.ap-northeast-2.compute.internal (pool system_core-20251217040546303900000001): tenant kinds ['dev', 'prod'], namespaces ['kube-system', 'keda', 'monitoring', 'argocd', 'dev-app-y', 'dev-app-aa']. Memory limit total 11.6GB / allocatable 6.9GB = 1.68x, request total 4.7GB … |
| `tenancy.shared-node-limit-overcommit.ip-10-0-1-139.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default): tenant kinds ['dev', 'prod'], namespaces ['prod-app-y', 'dev-app-y', 'prod-app-s', 'prod-app-z-backend', 'dev-app-s', 'prod-app-v']. Memory limit total 47.0GB / allocatable 29.8GB = 1.58x, request total 18.9GB, containers without a … |
| `tenancy.shared-node-limit-overcommit.ip-10-0-2-218.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-2-218.ap-northeast-2.compute.internal (pool system-ondemand): tenant kinds ['dev', 'other', 'prod'], namespaces ['monitoring', 'argocd', 'dev-app-aa', 'keda', 'kube-system', 'middleware']. Memory limit total 5.7GB / allocatable 3.2GB = 1.79x, request total 2.0GB, containers without a … |
| `tenancy.tenant-without-limitrange.prod-app-z-backend` | warn | medium | prod-app-z-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 None cores, memory p95 NoneGB |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.lab-k.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-s/app-s-admin` | warn | medium | ingress ['admin-dev.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-v/app-v-admin-frontend` | warn | medium | ingress ['admin-dev.lab-n.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-y/app-y-admin` | warn | medium | ingress ['admin-dev.lab-m.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-s/app-s-admin` | warn | medium | ingress ['canary-admin.lab-l.example', 'admin.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-v/app-v-admin-frontend` | warn | medium | ingress ['admin.lab-n.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-y/app-y-admin` | warn | medium | ingress ['admin.lab-m.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 113 (0.009), without one in prod 35. emptyDirs without sizeLimit 22 (prod: ['app-ab-prod/statefulset/app-ab-backend-postgresql', 'prod-app-r/deployment/app-r-backend', 'prod-app-r/statefulset/app-r-postgresql' … |
| `hygiene.old-replicasets.cluster` | fail | low | Of 428 ReplicaSets, 362 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 62, '3': 6} |
| `node.os-not-collected.ip-10-0-1-117.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-1-137.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-1-241.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-1-245.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-2-100.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-2-135.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-2-218.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `node.os-not-collected.ip-10-0-2-60.ap-northeast-2.compute.internal` | fail | low | os.txt missing |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `tenancy.dev-shares-prod-nodes.ip-10-0-1-117.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-1-117.ap-northeast-2.compute.internal (pool system_core-20251217040546303900000001): prod pods 2 (['app-ab-prod', 'prod-app-y']) together with dev pods 2 (['dev-app-aa', 'dev-app-y']). Memory limit total/allocatable 1.68, CPU limit total/allocatable 3.37, containers without a memory … |
| `tenancy.dev-shares-prod-nodes.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default): prod pods 23 (['app-ab-prod', 'prod-app-s', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend']) together with dev pods 10 (['dev-app-aa', 'dev-app-s', 'dev-app-v', 'dev-app-y']). Memory limit … |
| `tenancy.dev-shares-prod-nodes.ip-10-0-2-218.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-2-218.ap-northeast-2.compute.internal (pool system-ondemand): prod pods 2 (['prod-app-t', 'prod-app-x']) together with dev pods 1 (['dev-app-aa']). Memory limit total/allocatable 1.79, CPU limit total/allocatable 1.81, containers without a memory limit 1 |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 242614, top [['Elastic Load Balancing v2/DescribeTargetHealth', 76055], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 43347], ['EC2/DescribeInstances', 38801], ['EC2/DescribeSecurityGroups', 24999], ['Elastic Load Balancing v2/RegisterTargets' … |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster None (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 9, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 9, apps whose targetRevision is a branch or HEAD 9 ['argocd/application/app-w-prod', 'argocd/application/app-t-prod', 'argocd/application/app-x-prod', 'argocd/application/app-s-prod', 'argocd/application/app-y-prod', 'argocd/application/app-ab-prod' … |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `coredns.metrics-unavailable.cluster` | warn | low | no coredns_* series. replicas 2, version 1.11.3. Even with the prometheus plugin in the Corefile, nothing is scraped without a ServiceMonitor |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | controller EC2 API request series 0, driver 1.37.0 (add-on None). When enabled, shows EC2 API errors {} / throttles None |
| `eso.version-old.cluster` | warn | low | external-secrets 0.9.13 (ExternalSecrets 49, PushSecrets 0) |
| `grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana` | warn | low | Grafana 10.2.3 (database ok), ingress ['monitor.lab-k.example'], dashboards 28 |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent` | warn | low | image 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1 (tag tag, imagePullPolicy Always, registry 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init` | warn | low | image 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1 (tag tag, imagePullPolicy Always, registry 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com) |
| `hygiene.failed-pods-lingering.cluster` | warn | low | Failed pods 1 (prod 1), reasons {'Evicted': 1}, namespaces {'prod-app-t': 1}, oldest 16.6h. Example: ['prod-app-t/app-t-backend-5f6c75bd56-n226l'] |
| `hygiene.unused-crds.cluster` | warn | low | 27 of 47 CRDs have zero objects (by group {'generators.external-secrets.io': 7, 'monitoring.coreos.com': 6, 'networking.k8s.aws': 4, 'eventing.keda.sh': 2, 'external-secrets.io': 3, 'keda.sh': 2, 'crd.k8s.amazonaws.com': 1, 'actions.github.com': 1, 'vpcresources.k8s.aws': 1}), 18 webhooks |
| `karpenter.spot-to-spot-consolidation-off.cluster` | warn | low | FEATURE_GATES {'Drift': 'true', 'SpotToSpotConsolidation': 'false'}, NodeClaims terminated by spot interruption 263, drift True |
| `keda.operator-metrics-disabled.cluster` | warn | low | --enable-prometheus-metrics False, operator keda_* metrics exposed False, scaler errors in logs (24h) 0 |
| `keda.scaledobject-never-active.cluster` | warn | low | inactive for more than 14 days ['dev-app-y/scaledobject/app-y-ai-kafka-lag'], not Ready [], fallback active [], scale-to-zero targets ['prod-app-z-backend/scaledobject/app-z-file-worker', 'prod-app-z-backend/scaledobject/app-z-graph-worker'] |
| `kubeproxy.metrics-not-scraped.cluster` | warn | low | metrics False (source None), targets up 0/down 0 [], metricsBindAddress 0.0.0.0:10249 (loopback only False), nodes 9 |
| `kubeproxy.node-cmd-unavailable.cluster` | warn | low | 9 of 9 nodes could not read /proxyMode or /healthz. Mode from the config file: iptables |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alert-metric-without-dashboard.grafana` | warn | low | 28 dashboards (196 panel metrics) — 153 of 194 alert-rule metrics have no panel: Without, aggregator_unavailable_apiservice, aggregator_unavailable_apiservice_total, alerting, alertmanager_cluster_members, alertmanager_config_hash |
| `observability.alerts-never-fired.cluster` | warn | low | 139 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent', 'CPUThrottlingHigh' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 41 of 41 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-s', 'app-s-admin'), ('dev-app-s', 'app-s-api'), ('dev-app-s', 'app-s-backend'), ('dev-app-s', 'app-s-frontend'), ('dev-app-y', 'app-y-admin')]), namespaces with saturation metrics [] |
| `observability.unclassified-errors.cluster` | warn | low | 24 unclassified error lines (23380 lines scanned, 23 files). Top: [('ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver', 8), ('ebs-csi \| "Volume deletion failed" err="persistentvolume pvc-<uuid> is still attached to node ip-10-', 4), ('ebs-csi \| … |
| `observability.unstructured-logs.app-ab-prod` | warn | low | Of 947170 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.argocd` | warn | low | Of 14865 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-v` | warn | low | Of 59439 lines in 1h, 0 parse as JSON (0.0) |
| `prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus StatefulSet replicas 1 (ready 1), restarts 2, started None |
| `prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus 2.49.1 — 2.53 is the last 2.x LTS (2024-07), 3.0 was released 2024-11 |
| `resilience.exec-probe.app-ab-prod/statefulset/app-ab-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "pwcuser" -d "dbname=app-ab_tp" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.dev-app-aa/statefulset/app-aa-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-aa/statefulset/app-aa-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U vxt_chatbot -d … |
| `resilience.exec-probe.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.dev-app-y/statefulset/app-y-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.kube-system/daemonset/aws-node:aws-node` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s', 'port': None, 'timeout_s': 10, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s' … |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.middleware/statefulset/redis-master:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': 'sh -c /health/ping_liveness_local.sh 5', 'port': None, 'timeout_s': 6, 'period_s': 5, 'failure_threshold': 5, 'initial_delay_s': 20}, readiness {'type': 'exec' … |
| `resilience.exec-probe.prod-app-r/statefulset/app-r-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-r" -d "dbname=app-r" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s' … |
| `resilience.exec-probe.prod-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-t/statefulset/app-t-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-t" -d "dbname=app-t" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s' … |
| `resilience.exec-probe.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-x/statefulset/app-x-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-x" -d "dbname=app-x" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s' … |
| `resilience.exec-probe.prod-app-y/statefulset/app-y-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-file-worker:file-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.FileWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.GraphWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.liveness-dependency-path.prod-app-r/deployment/app-r-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 7860, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.prod-app-r/deployment/app-r-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-admin:admin` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-api:api` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-backend:backend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-ai:ai` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-studio:studio` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.liveness-dependency-path.prod-app-x/deployment/app-x-api:api` | warn | low | ['liveness and readiness share the same path (/api/v1/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/api/v1/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.prod-app-z-backend/deployment/app-z-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.no-prestop.app-ab-prod/app-ab-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ab-prod/app-ab-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-r/app-r-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-r/app-r-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-studio` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-admin-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-w/app-w` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-x/app-x-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-embedding-server` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-pg-proxy` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/tts-proxy` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), None desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), None desired changes over 7 days |
| `scaling.no-hpa-serving-prod.app-ab-prod/app-ab-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ab-prod/app-ab-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-r/app-r-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-r/app-r-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-api` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-frontend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-ai` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-studio` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-admin-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-w/app-w` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-x/app-x-api` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-z-backend/app-z-embedding-server` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-z-backend/tts-proxy` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `tenancy.dev-shares-prod-nodes.ip-10-0-1-245.ap-northeast-2.compute.internal` | warn | low | Node ip-10-0-1-245.ap-northeast-2.compute.internal (pool default): prod pods 2 (['prod-app-t', 'prod-app-z-backend']) together with dev pods 1 (['dev-app-s']). Memory limit total/allocatable 0.94, CPU limit total/allocatable 2.98, containers without a memory limit 0 |
| `tenancy.dev-shares-prod-nodes.ip-10-0-2-100.ap-northeast-2.compute.internal` | warn | low | Node ip-10-0-2-100.ap-northeast-2.compute.internal (pool default): prod pods 9 (['prod-app-r', 'prod-app-s', 'prod-app-t', 'prod-app-z-backend']) together with dev pods 2 (['dev-app-aa', 'dev-app-v']). Memory limit total/allocatable 1.1, CPU limit total/allocatable 1.96, containers without a memory … |
| `tenancy.dev-shares-prod-nodes.ip-10-0-2-60.ap-northeast-2.compute.internal` | warn | low | Node ip-10-0-2-60.ap-northeast-2.compute.internal (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-s', 'prod-app-v']) together with dev pods 2 (['dev-app-s', 'dev-app-v']). Memory limit total/allocatable 1.49, CPU limit total/allocatable 2.44, containers without a memory limit … |
| `vpccni.metrics-unreadable.cluster` | warn | low | 9 of 9 nodes without readable ipamd metrics (localhost:61678): ['ip-10-0-1-117.ap-northeast-2.compute.internal', 'ip-10-0-1-137.ap-northeast-2.compute.internal', 'ip-10-0-1-139.ap-northeast-2.compute.internal', 'ip-10-0-1-241.ap-northeast-2.compute.internal' … |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |
| `hygiene.no-progressive-delivery.cluster` | fail | info | No progressive-delivery component (Argo Rollouts, Flagger). All deployments are rolling updates (replace everything) -- ALB weighted target groups are not used either |

표의 근거는 칸에 맞게 줄였어요. 판정에 쓴 자료 전체는 아래에 항목별로 접혀 있고, `findings-draft.json`의 `details`와 같아요.

<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
 "by_class": {
  "app-cause": 5,
  "app": 22,
  "cause": 130
 },
 "symptom_ratio": 0.0,
 "symptom_rules": []
}
```

</details>
<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "allocatable_cpu_without_largest": 15.45,
 "allocatable_memory_gb_without_largest": 46.3,
 "autoscaler": true,
 "autoscaler_name": "karpenter",
 "available": true,
 "cannot_fit_elsewhere": [],
 "cpu_ok": true,
 "karpenter": true,
 "largest_node": "ip-10-0-1-139.ap-northeast-2.compute.internal",
 "largest_node_cpu": 3.92,
 "largest_node_memory_gb": 29.8,
 "memory_ok": true,
 "ok": false,
 "pods_on_largest_node": 34,
 "pools_short": [
  {
   "eligible_nodes": [
    "ip-10-0-1-137.ap-northeast-2.compute.internal",
    "ip-10-0-1-245.ap-northeast-2.compute.internal",
    "ip-10-0-2-100.ap-northeast-2.compute.internal"
   ],
   "pods": 32,
   "needed_cpu": 2.79,
   "free_cpu": 2.62,
   "needed_memory_gb": 14.81,
   "free_memory_gb": 11.64
  },
  {
   "eligible_nodes": [
    "ip-10-0-1-137.ap-northeast-2.compute.internal",
    "ip-10-0-1-245.ap-northeast-2.compute.internal"
   ],
   "pods": 1,
   "needed_cpu": 0.5,
   "free_cpu": 0.28,
   "needed_memory_gb": 4.0,
   "free_memory_gb": 8.39
  }
 ],
 "prod_pods_on_largest_node": 23,
 "requests_cpu_total": 11.51,
 "requests_memory_gb_total": 45.7,
 "tight": false
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
 "importance": "critical",
 "mode": "OOMKill",
 "symptom": "pods die and requests fail or slow down"
}
```

</details>
<details><summary><code>observability.loki-oomkilled.cluster</code></summary>

```json
{
 "oomkilled": true,
 "pods": [
  {
   "pod": "loki-stack-0",
   "container": "loki",
   "restarts": 1,
   "last_reason": "OOMKilled",
   "last_finished": "2026-10-25T00:15:41Z"
  }
 ],
 "self_metrics": {
  "discarded_samples_since_start": {},
  "streams_in_memory": 54,
  "panics": 0,
  "lines_received_since_start": 298336479,
  "requests_5xx_since_start": 4,
  "rss_mb": 289,
  "process_uptime_h": 313.3
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
 }
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
 "compat_row": "0.37",
 "k8s_max_supported": "1.30",
 "k8s_min_supported": "1.23",
 "k8s_minor": "1.32",
 "k8s_supported": false,
 "present": true,
 "version": "0.37.0",
 "version_note": null
}
```

</details>
<details><summary><code>resilience.prod-concentration.ip-10-0-1-139.ap-northeast-2.compute.internal</code></summary>

```json
{
 "autoscaler": true,
 "capacity_type": "spot",
 "node": "ip-10-0-1-139.ap-northeast-2.compute.internal",
 "nodes_total": 9,
 "pool": "default",
 "prod_pods": 23,
 "prod_total": 45,
 "prod_workloads": [
  "app-ab-prod/app-ab-backend",
  "app-ab-prod/app-ab-frontend",
  "prod-app-s/app-s-admin",
  "prod-app-s/app-s-api",
  "prod-app-s/app-s-backend",
  "prod-app-s/app-s-frontend",
  "prod-app-v/app-v-admin-frontend",
  "prod-app-v/app-v-backend",
  "prod-app-v/app-v-frontend",
  "prod-app-w/app-w",
  "prod-app-x/app-x-api",
  "prod-app-y/app-y-admin",
  "prod-app-y/app-y-ai",
  "prod-app-y/app-y-backend",
  "prod-app-y/app-y-frontend",
  "prod-app-z-backend/app-z-backend",
  "prod-app-z-backend/app-z-embedding-server",
  "prod-app-z-backend/app-z-frontend"
 ],
 "share": 0.51,
 "spot": true,
 "workload_count": 18
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-w/deployment/app-w</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "prod-app-w/deployment/app-w",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-y/deployment/app-y-ai</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 3
 },
 "prod": true,
 "replicas": 3,
 "running": 3,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "prod-app-y/deployment/app-y-ai",
 "zones": {
  "ap-northeast-2a": 3
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-y/deployment/app-y-backend</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "prod-app-y/deployment/app-y-backend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-z-backend/deployment/app-z-frontend</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": "preferred",
 "eligible_nodes": 4,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "prod-app-z-backend/deployment/app-z-frontend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>security.privileged-or-host-access.prod-app-z-backend/deployment/tts-proxy</code></summary>

```json
{
 "flags": [
  "hostPath ['dev-net-tun']",
  "capabilities [\"tailscale:['NET_ADMIN']\"]"
 ],
 "root_allowed_containers": [
  "tailscale",
  "forwarder"
 ],
 "severe": true,
 "system": false,
 "workload": "prod-app-z-backend/deployment/tts-proxy"
}
```

</details>
<details><summary><code>karpenter.ec2nodeclass-hardening.cluster</code></summary>

```json
{
 "classes_imds_hop_gt1": [
  "default"
 ],
 "classes_imds_tokens_optional": [],
 "classes_root_unencrypted": [
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
 "first": "2026-11-06T17:31:20Z",
 "last": "2026-11-07T01:34:43Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/external-secrets/external-secrets_external-secrets.log": 62
 },
 "samples": [
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:31:20.550454017Z {\"level\":\"error\",\"ts\":1793986280.5503237,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:31:20.562309177Z {\"level\":\"error\",\"ts\":1793986280.5622146,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:48:00.658098468Z {\"level\":\"error\",\"ts\":1793987280.6579707,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T17:48:00.669209677Z {\"level\":\"error\",\"ts\":1793987280.669104,\"msg\":\"Reconciler error\",\"controller\":\"externalsecret\",\"controllerGroup\":\"external-secrets.io\",\"controllerKind\":\"",
  "[pod/external-secrets-7859bcd5c-g8z4q/external-secrets] 2026-11-06T18:04:40.765776795Z {\"level\":\"error\",\"ts\":1793988280.7656457,\"logger\":\"controllers.ExternalSecret\",\"msg\":\"could not get secret data from provider\",\"ExternalSecret\":{\"name\":\""
 ]
}
```

</details>
<details><summary><code>logs.signatures.karpenter.version-unsupported</code></summary>

```json
{
 "count": 1,
 "first": "2026-11-06T08:49:38Z",
 "last": "2026-11-06T08:49:38Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/karpenter/karpenter_karpenter.log": 1
 },
 "samples": [
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-06T08:49:38.045274596Z {\"level\":\"ERROR\",\"time\":\"2026-11-06T08:49:38.045Z\",\"logger\":\"controller\",\"message\":\"failed validating kubernetes version\",\"commit\":\"490ef94\",\"controller\":\"nodeclass.s"
 ]
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.Scheduling failure</code></summary>

```json
{
 "importance": "high",
 "mode": "Scheduling failure",
 "symptom": "new pods do not start"
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.VPC CNI IP exhaustion</code></summary>

```json
{
 "importance": "high",
 "mode": "VPC CNI IP exhaustion",
 "symptom": "pods Pending without network"
}
```

</details>
<details><summary><code>prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "head_series": null,
 "memory_limit": "1536Mi",
 "monitoring_oomkilled": [],
 "monitoring_restarts_7d": {},
 "oomkilled_at": "2026-11-05T08:21:29Z",
 "oomkilled_last": true,
 "present": true,
 "restarts": 2,
 "rss_vs_limit": null,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-x/deployment/app-x-api</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 1,
  "ip-10-0-1-137.ap-northeast-2.compute.internal": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "prod-app-x/deployment/app-x-api",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller</code></summary>

```json
{
 "cause": "OOM (memory limit)",
 "container": "application-controller",
 "crashloop": false,
 "exit_code": 137,
 "last_finished": "2026-10-30T09:00:04Z",
 "last_reason": "OOMKilled",
 "namespace": "argocd",
 "node_rebooted_at": null,
 "pod": "argocd-application-controller-0",
 "rebooted": false,
 "restarts": 42,
 "unhealthy_events": 0,
 "waiting": null
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 13,
 "applications_prod": 9,
 "default_project_apps": 13,
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
 "classes": 4,
 "classes_intree": [
  "gp2"
 ],
 "classes_no_expansion": [
  "gp2",
  "gp3",
  "gp3-2a",
  "gp3-2c"
 ],
 "classes_unencrypted": [
  "gp3",
  "gp3-2a",
  "gp3-2c"
 ],
 "default_class": "gp3"
}
```

</details>
<details><summary><code>eso.provider-api-errors.cluster</code></summary>

```json
{
 "api_error_ratio": 0.0782,
 "api_errors": 2711,
 "api_success": 31963,
 "metrics_available": true,
 "not_ready": [
  "database/externalsecret/mysql-app-v-secret"
 ],
 "not_ready_oldest_refresh_h": 7796.6,
 "reconcile_errors_total": 2711,
 "sync_calls_error": 2711,
 "sync_calls_total": 73134
}
```

</details>
<details><summary><code>grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "api_5xx": 9,
 "api_requests": 7002292,
 "datasource_error_max_ratio": 0.1259,
 "datasources": [
  {
   "datasource": "Loki(loki)",
   "requests": 2614,
   "errors_5xx_429": 329,
   "error_ratio": 0.1259,
   "by_code": {
    "101": 4,
    "200": 2275,
    "400": 6,
    "429": 329
   }
  },
  {
   "datasource": "Prometheus(prometheus)",
   "requests": 1535,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 1349,
    "301": 186
   }
  },
  {
   "datasource": "VictoriaMetrics_onprem(prometheus)",
   "requests": 142,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 142
   }
  }
 ],
 "datasources_with_errors": [
  "Loki(loki)"
 ],
 "metrics_available": true,
 "present": true,
 "target": "monitoring/deployment/kube-prometheus-stack-grafana"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.prod-app-z-backend/deployment/tts-proxy:tailscale</code></summary>

```json
{
 "container": "tailscale",
 "holder": false,
 "image": "tailscale/tailscale:latest",
 "mutable": true,
 "prod": true,
 "pull_policy": "IfNotPresent",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "prod-app-z-backend/deployment/tts-proxy"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.prod-app-z-backend/deployment/tts-proxy</code></summary>

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
 "target": "prod-app-z-backend/deployment/tts-proxy"
}
```

</details>
<details><summary><code>observability.log-coverage-gap.cluster</code></summary>

```json
{
 "available": true,
 "by_namespace_missing": {
  "kube-system": 23,
  "monitoring": 22,
  "prod-app-z-backend": 5,
  "keda": 3,
  "middleware": 3,
  "prod-app-t": 3,
  "prod-app-s": 3,
  "argocd": 2,
  "dev-app-s": 2,
  "dev-app-y": 2,
  "dev-app-v": 2,
  "karpenter": 2,
  "prod-app-y": 2,
  "prod-app-r": 2,
  "prod-app-v": 2
 },
 "gap_ratio": 0.565,
 "nodes_all_missing": [],
 "pods_without_logs_1h": 83,
 "running_pods_over_1h": 147
}
```

</details>
<details><summary><code>operators.unhealthy-condition.externalsecrets/database/mysql-app-v-secret</code></summary>

```json
{
 "age_hours": 7795.6,
 "condition": "Ready",
 "kind": "externalsecrets.external-secrets.io",
 "message": "could not get secret data from provider",
 "name": "mysql-app-v-secret",
 "namespace": "database",
 "reason": "SecretSyncedError",
 "status": "False"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
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
 "workload": "prod-app-s/statefulset/app-s-backend-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
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
 "workload": "prod-app-v/statefulset/app-v-backend-prod-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
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
 "workload": "prod-app-y/statefulset/app-y-backend-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.prod-app-z-backend/statefulset/app-z-neo4j:neo4j</code></summary>

```json
{
 "container": "neo4j",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "prod": true,
 "readiness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "startup": null,
 "workload": "prod-app-z-backend/statefulset/app-z-neo4j"
}
```

</details>
<details><summary><code>resilience.no-pdb.prod-app-x/app-x-api</code></summary>

```json
{
 "namespace": "prod-app-x",
 "name": "app-x-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-pdb.prod-app-y/app-y-ai</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-pdb.prod-app-y/app-y-backend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.app-ab-prod/app-ab-backend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.app-ab-prod/app-ab-frontend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-v/app-v-backend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-v/app-v-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-y/app-y-admin</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-y/app-y-ai</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-y/app-y-backend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-y/app-y-frontend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-readiness-probe.prod-app-z-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.recreate-strategy-serving.prod-app-r/deployment/app-r-backend</code></summary>

```json
{
 "grace_s": 30,
 "prestop": false,
 "prod": true,
 "recreate_justified": false,
 "recreate_reason": [],
 "replicas": 1,
 "strategy": "Recreate",
 "workload": "prod-app-r/deployment/app-r-backend"
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-x/deployment/app-x-api</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 1,
  "ip-10-0-1-137.ap-northeast-2.compute.internal": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-x/deployment/app-x-api",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-embedding-server</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 1,
  "ip-10-0-1-245.ap-northeast-2.compute.internal": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-z-backend/deployment/app-z-embedding-server",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.single-node-dependency.prod-app-z-backend/deployment/tts-proxy</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "hostPath volume ['dev-net-tun']"
 ],
 "replicas": 1,
 "workload": "prod-app-z-backend/deployment/tts-proxy"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ab-prod/app-ab-backend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ab-prod/app-ab-frontend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-r/app-r-backend</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-r/app-r-web</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-s/app-s-admin</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-t/app-t-ai</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-t/app-t-backend</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-t/app-t-studio</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-t/app-t-web</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-v/app-v-backend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-v/app-v-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-y/app-y-admin</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-y/app-y-frontend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-z-backend/app-z-pg-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-pg-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.prod-app-z-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter</code></summary>

```json
{
 "container": "jmx-exporter",
 "heap_ratio": 1.0,
 "heap_unset": false,
 "image": "jmx-exporter:0.20.0-debian-11-r4",
 "limit_mib": 128.0,
 "max_ram_percentage": 100.0,
 "workload": "middleware/statefulset/kafka-controller",
 "xmx_mib": null
}
```

</details>
<details><summary><code>resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 373 MB, CPU request over by 0.143 cores",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "argocd-application-controller",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.057 cores, CPU limit 0.5 → none, memory request 384 → 757 MB",
 "target": "argocd/statefulset/argocd-application-controller:application-controller"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 281 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "WARNING",
 "name": "app-v-backend-dev-mysql",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 793 MB",
 "target": "dev-app-v/statefulset/app-v-backend-dev-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-y/deployment/app-y-ai:ai</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request over by 628 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-y-ai",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 1024 → 396 MB, memory limit 2048 → 396 MB",
 "target": "dev-app-y/deployment/app-y-ai:ai"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 355 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "WARNING",
 "name": "app-y-backend-mysql",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 867 MB",
 "target": "dev-app-y/statefulset/app-y-backend-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 273 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "loki-stack",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 529 MB",
 "target": "monitoring/statefulset/loki-stack:loki"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 851 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.137 cores, CPU limit 0.5 → none, memory request 800 → 1651 MB",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.29 cores, memory request over by 316 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "vm-single",
 "severity": "CRITICAL",
 "summary": "CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 196 MB, memory limit 1024 → 196 MB",
 "target": "monitoring/statefulset/vm-single:vmsingle"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-r/deployment/app-r-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.348 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "OK",
 "name": "app-r-backend",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.152 cores, CPU limit 2.0 → none, memory request 1024 → 866 MB, memory limit 2048 → 866 MB",
 "target": "prod-app-r/deployment/app-r-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-s/deployment/app-s-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 298 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "app-s-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 426 MB",
 "target": "prod-app-s/deployment/app-s-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 404 MB, CPU request over by 0.188 cores",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "WARNING",
 "name": "app-s-backend-mysql",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.012 cores, CPU limit 1.0 → none, memory request 768 → 1172 MB, memory limit 1536 → 1172 MB",
 "target": "prod-app-s/statefulset/app-s-backend-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-t/deployment/app-t-ai:ai</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 351 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "WARNING",
 "name": "app-t-ai",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 607 MB",
 "target": "prod-app-t/deployment/app-t-ai:ai"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-x/deployment/app-x-api:api</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.49 cores, memory request over by 660 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-x-api",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 1024 → 364 MB, memory limit 2048 → 364 MB",
 "target": "prod-app-x/deployment/app-x-api:api"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-y/deployment/app-y-ai:ai</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request over by 963 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-y-ai",
 "severity": "CRITICAL",
 "summary": "CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 1085 MB, memory limit 4096 → 1085 MB",
 "target": "prod-app-y/deployment/app-y-ai:ai"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/deployment/app-z-embedding-server:embedding</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 2651 MB, CPU request over by 0.425 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-z-embedding-server",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.075 cores, CPU limit 2.0 → none, memory request 4096 → 6747 MB, memory limit 6144 → 6747 MB",
 "target": "prod-app-z-backend/deployment/app-z-embedding-server:embedding"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/deployment/app-z-file-worker:file-worker</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.703 cores, memory request over by 337 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-z-file-worker",
 "severity": "CRITICAL",
 "summary": "CPU request 1.0 → 0.297 cores, CPU limit 2.0 → none, memory request 2048 → 1711 MB, memory limit 4096 → 1711 MB",
 "target": "prod-app-z-backend/deployment/app-z-file-worker:file-worker"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.458 cores, memory request over by 670 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-z-graph-worker",
 "severity": "CRITICAL",
 "summary": "CPU request 1.0 → 0.542 cores, CPU limit 2.0 → none, memory request 2048 → 1378 MB, memory limit 6144 → 1378 MB",
 "target": "prod-app-z-backend/deployment/app-z-graph-worker:graph-worker"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/statefulset/app-z-neo4j:neo4j</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.49 cores, memory request over by 2417 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-z-neo4j",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1679 MB, memory limit 5120 → 1679 MB",
 "target": "prod-app-z-backend/statefulset/app-z-neo4j:neo4j"
}
```

</details>
<details><summary><code>resources.no-memory-limit.prod-app-z-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.karpenter-expired-not-replaced.default-n44bh</code></summary>

```json
{
 "age_h": 1056.5,
 "capacity_type": "spot",
 "disruption_blocked": {},
 "do_not_disrupt_pod_count": 2,
 "do_not_disrupt_pods": [
  "prod-app-s/app-s-admin-57f5fcc58d-khsh5",
  "prod-app-x/app-x-api-5755745bc7-2sjvd"
 ],
 "expire_after_h": 720.0,
 "hours_past_expiry": 336.5,
 "instance_type": "r8gd.xlarge",
 "name": "default-n44bh",
 "node": "ip-10-0-1-139.ap-northeast-2.compute.internal"
}
```

</details>
<details><summary><code>security.externalsecret-not-ready.database/mysql-app-v-secret</code></summary>

```json
{
 "message": "could not get secret data from provider",
 "name": "mysql-app-v-secret",
 "namespace": "database",
 "reason": "SecretSyncedError"
}
```

</details>
<details><summary><code>security.polaris-security-danger.cluster</code></summary>

```json
{
 "danger_check_counts": {
  "dangerousCapabilities": 2,
  "hostNetworkSet": 2,
  "privilegeEscalationAllowed": 59,
  "runAsPrivileged": 2,
  "runAsRootAllowed": 58,
  "hostPIDSet": 1,
  "rolebindingClusterAdminRole": 2,
  "rolebindingRolePodExecAttach": 2,
  "clusterrolebindingClusterAdmin": 2,
  "clusterrolebindingPodExecAttach": 4,
  "sensitiveContainerEnvVar": 1,
  "rolePodExecAttach": 2,
  "clusterrolePodExecAttach": 4
 },
 "danger_workloads": [
  "kube-system/daemonset/aws-node",
  "prod-app-z-backend/deployment/tts-proxy",
  "kube-system/daemonset/ebs-csi-node-windows",
  "kube-system/daemonset/ebs-csi-node",
  "middleware/deployment/redis-insight",
  "arc-runners/cronjob/arc-warm-up",
  "arc-runners/cronjob/arc-cool-down",
  "monitoring/daemonset/kube-prometheus-stack-prometheus-node-exporter",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "middleware/statefulset/kafka-controller",
  "dev-app-v/deployment/app-v-admin-frontend",
  "dev-app-aa/deployment/app-aa-backend",
  "arc-system/deployment/arc-gha-rs-controller",
  "dev-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-frontend",
  "dev-app-v/deployment/app-v-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "dev-app-aa/deployment/app-aa-frontend",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "monitoring/deployment/vmalert",
  "dev-app-s/deployment/app-s-frontend",
  "prod-app-z-backend/deployment/app-z-graph-worker",
  "dev-app-y/deployment/app-y-admin",
  "dev-app-s/deployment/app-s-admin",
  "dev-app-y/deployment/app-y-ai",
  "dev-app-y/deployment/app-y-frontend",
  "dev-app-y/deployment/app-y-backend",
  "app-ab-prod/deployment/app-ab-frontend",
  "dev-app-s/deployment/app-s-api",
  "prod-app-z-backend/deployment/app-z-file-worker",
  "app-ab-prod/deployment/app-ab-backend",
  "dev-app-s/deployment/app-s-backend",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-s/deployment/app-s-admin",
  "monitoring/deployment/vmauth",
  "middleware/deployment/kafka-ui",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-r/deployment/app-r-web",
  "prod-app-w/deployment/app-w",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-t/deployment/app-t-backend",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-t/deployment/app-t-web",
  "prod-app-s/deployment/app-s-api",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "dev-app-aa/statefulset/app-aa-postgres",
  "prod-app-x/deployment/app-x-api",
  "prod-app-z-backend/deployment/app-z-backend",
  "monitoring/statefulset/vm-single",
  "argocd/rolebinding/argocd-repo-server",
  "monitoring/rolebinding/kube-prometheus-stack-grafana",
  "/clusterrolebinding/argocd-application-controller",
  "/clusterrolebinding/eks:addon-cluster-admin",
  "middleware/statefulset/redis-master",
  "monitoring/daemonset/loki-stack-promtail",
  "monitoring/statefulset/loki-stack",
  "kube-system/daemonset/kube-proxy",
  "kube-system/deployment/coredns",
  "argocd/role/argocd-repo-server",
  "monitoring/role/kube-prometheus-stack-grafana",
  "/clusterrole/argocd-application-controller",
  "/clusterrole/argocd-server",
  "/clusterrole/eks:extension-metrics-apiserver",
  "/clusterrole/keda-operator",
  "/clusterrolebinding/argocd-server",
  "/clusterrolebinding/keda-operator"
 ],
 "danger_workloads_prod": [
  "prod-app-z-backend/deployment/tts-proxy",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "prod-app-z-backend/deployment/app-z-graph-worker",
  "app-ab-prod/deployment/app-ab-frontend",
  "prod-app-z-backend/deployment/app-z-file-worker",
  "app-ab-prod/deployment/app-ab-backend",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-s/deployment/app-s-admin",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-r/deployment/app-r-web",
  "prod-app-w/deployment/app-w",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-t/deployment/app-t-backend",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-t/deployment/app-t-web",
  "prod-app-s/deployment/app-s-api",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "prod-app-x/deployment/app-x-api",
  "prod-app-z-backend/deployment/app-z-backend"
 ],
 "present": true,
 "score": 79
}
```

</details>
<details><summary><code>storage.csi-snapshot-unavailable.cluster</code></summary>

```json
{
 "ebs_snapshot_descriptions": null,
 "ebs_snapshots_30d": null,
 "platform": "eks",
 "prod_pvcs": 8,
 "recent_7d": 0,
 "volumesnapshot_crd": false,
 "volumesnapshotclasses": 0,
 "volumesnapshots": 0
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
<details><summary><code>storage.no-volume-expansion.gp3-2a</code></summary>

```json
{
 "key": null,
 "item": {
  "expansion": false,
  "name": "gp3-2a",
  "provisioner": "ebs.csi.aws.com"
 }
}
```

</details>
<details><summary><code>storage.no-volume-expansion.gp3-2c</code></summary>

```json
{
 "key": null,
 "item": {
  "expansion": false,
  "name": "gp3-2c",
  "provisioner": "ebs.csi.aws.com"
 }
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-ab-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-ab-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 3,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-r</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-r",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 3,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-s</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-s",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 8,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-t</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-t",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 5,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-v</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-v",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 4,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-w</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-w",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 2,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-x</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-x",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 3,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-y</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-y",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 8,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.prod-app-z-backend</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-z-backend",
 "networkpolicies": 0,
 "networkpolicy_enforced": false,
 "pods": 9,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>traffic.shared-alb-group.alb-group/app-u-prod-lb</code></summary>

```json
{
 "group": "app-u-prod-lb",
 "hosts": 48,
 "ingress_count": 41,
 "kinds": [
  "dev",
  "other",
  "prod"
 ],
 "lb": [
  "k8s-lab-kprodlb-b18a4555d7-2062640887.ap-northeast-2.elb.amazonaws.com"
 ],
 "mixed_prod_nonprod": true,
 "namespace_count": 16,
 "namespaces": [
  "app-ab-prod",
  "argocd",
  "dev-app-aa",
  "dev-app-s",
  "dev-app-v",
  "dev-app-y",
  "middleware",
  "monitoring",
  "prod-app-r",
  "prod-app-s",
  "prod-app-t",
  "prod-app-v",
  "prod-app-w",
  "prod-app-x",
  "prod-app-y",
  "prod-app-z-backend"
 ],
 "prod": true,
 "target": "alb-group/app-u-prod-lb"
}
```

</details>
<details><summary><code>albctl.reconcile-errors.cluster</code></summary>

```json
{
 "ingresses_without_lb": [],
 "leader_found": true,
 "metrics_available": true,
 "reconcile_errors_total": 41,
 "rest_client_429_503": 126,
 "tgb_stale": [],
 "workqueue_depth_max": 0.0
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
 "url": "https://deploy.lab-k.example"
}
```

</details>
<details><summary><code>argocd.components-not-ha.cluster</code></summary>

```json
{
 "applications_prod": 9,
 "components": {
  "applicationset-controller": "1/1",
  "dex-server": "1/1",
  "notifications-controller": "1/1",
  "redis": "1/1",
  "repo-server": "1/1",
  "server": "1/1",
  "application-controller": "1/1"
 },
 "components_not_ready": [],
 "components_single_replica": [
  "repo-server",
  "server"
 ],
 "version": "2.13.0"
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
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl</code></summary>

```json
{
 "container": "kubectl",
 "image": "bitnami/kubectl:latest",
 "mutable": true,
 "prod": false,
 "pull_policy": "Always",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "arc-runners/cronjob/arc-cool-down"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl</code></summary>

```json
{
 "container": "kubectl",
 "image": "bitnami/kubectl:latest",
 "mutable": true,
 "prod": false,
 "pull_policy": "Always",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "arc-runners/cronjob/arc-warm-up"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight</code></summary>

```json
{
 "container": "redis-insight",
 "image": "redis/redisinsight:latest",
 "mutable": true,
 "prod": false,
 "pull_policy": "Always",
 "registry": "docker.io",
 "tag_kind": "latest",
 "workload": "middleware/deployment/redis-insight"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.app-u.ai/role</code></summary>

```json
{
 "key": "app-u.ai/role",
 "nodes_total": 9,
 "nodes_with_label": 5,
 "prod_workloads": 9,
 "well_known": false,
 "workload_count": 34,
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
 "key": "workload-type",
 "nodes_total": 9,
 "nodes_with_label": 4,
 "prod_workloads": 26,
 "well_known": false,
 "workload_count": 39,
 "workloads": [
  "dev-app-s/deployment/app-s-admin",
  "dev-app-s/deployment/app-s-api",
  "dev-app-s/deployment/app-s-backend",
  "dev-app-s/deployment/app-s-frontend",
  "dev-app-y/deployment/app-y-admin",
  "dev-app-y/deployment/app-y-ai",
  "dev-app-y/deployment/app-y-backend",
  "dev-app-y/deployment/app-y-frontend"
 ]
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
 "consistency_errors": 3,
 "metrics_available": true,
 "node_termination_avg_s": 14.7,
 "pods_startup_avg_s": 30.9,
 "pods_startup_count": 8787,
 "reconcile_errors": {}
}
```

</details>
<details><summary><code>keda.components-single-replica.cluster</code></summary>

```json
{
 "apiservice_available": true,
 "has_pdb": false,
 "metrics_apiserver_ready": 1,
 "metrics_apiserver_replicas": 1,
 "operator_ready": 1,
 "operator_replicas": 1,
 "scaledobjects_prod": 3,
 "unused": false
}
```

</details>
<details><summary><code>keda.prod-external-trigger-no-fallback.cluster</code></summary>

```json
{
 "polling_interval_min_s": 15,
 "prod_external_without_fallback": [
  "prod-app-y/scaledobject/app-y-ai-kafka-lag",
  "prod-app-z-backend/scaledobject/app-z-file-worker",
  "prod-app-z-backend/scaledobject/app-z-graph-worker"
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
 "first": "2026-11-06T20:55:55Z",
 "last": "2026-11-07T01:36:03Z",
 "warn_at": 1,
 "fail_at": 100,
 "files": {
  "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 1500
 },
 "samples": [
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:55.112553385Z W1106 20:55:55.112429       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:55.112601875Z E1106 20:55:55.112473       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:57.386869931Z W1106 20:55:57.386754       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:55:57.386946006Z E1106 20:55:57.386824       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-06T20:56:36.640879575Z W1106 20:56:36.640780       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metrics-server.scrape-failed</code></summary>

```json
{
 "count": 31,
 "first": "2026-11-06T01:43:11Z",
 "last": "2026-11-06T10:09:11Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/metrics-server/kube-system_metrics-server.log": 31
 },
 "samples": [
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T01:43:11.055572813Z E1106 01:43:11.055448       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://10.0.2.160:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T01:43:11.089988869Z E1106 01:43:11.089871       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://10.0.2.66:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T02:37:11.052418502Z E1106 02:37:11.052276       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://10.0.2.250:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T02:37:11.067373879Z E1106 02:37:11.066845       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://10.0.2.160:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-06T02:39:26.060463132Z E1106 02:39:26.060322       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://10.0.2.181:10250/metrics/resource\\\": remote error: tls: internal er"
 ]
}
```

</details>
<details><summary><code>loki.memory-pressure.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "memory_limit": "512Mi",
 "memory_streams": 54,
 "oomkilled_at": "2026-10-25T00:15:41Z",
 "oomkilled_last": true,
 "present": true,
 "restarts": 1,
 "rss_mib": 289,
 "rss_vs_limit": 0.565,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/loki-stack"
}
```

</details>
<details><summary><code>loki.request-errors.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "discarded_by_reason": {},
 "log_error_messages": 11783,
 "metrics_available": true,
 "panics": 0,
 "present": true,
 "requests_5xx": 1,
 "requests_5xx_by_route": {
  "loki_api_v1_series": 1
 },
 "requests_total": 6899928,
 "target": "monitoring/statefulset/loki-stack",
 "wal_disk_full_failures": 0
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-ab-prod/app-ab-backend</code></summary>

```json
{
 "hosts": [
  "app-ab-tp-api.lab-k.example"
 ],
 "ingress": "app-ab-backend",
 "namespace": "app-ab-prod",
 "services": [
  "app-ab-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-ab-prod/app-ab-frontend</code></summary>

```json
{
 "hosts": [
  "app-ab-tp-prod.lab-k.example"
 ],
 "ingress": "app-ab-frontend",
 "namespace": "app-ab-prod",
 "services": [
  "app-ab-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.argocd/argocd-server</code></summary>

```json
{
 "hosts": [
  "deploy.lab-k.example"
 ],
 "ingress": "argocd-server",
 "namespace": "argocd",
 "services": [
  "argocd-server"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-aa/app-aa-backend</code></summary>

```json
{
 "hosts": [
  "demo-api.lab-m.example"
 ],
 "ingress": "app-aa-backend",
 "namespace": "dev-app-aa",
 "services": [
  "app-aa-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-aa/app-aa-frontend</code></summary>

```json
{
 "hosts": [
  "demo.lab-m.example"
 ],
 "ingress": "app-aa-frontend",
 "namespace": "dev-app-aa",
 "services": [
  "app-aa-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-s/app-s-admin</code></summary>

```json
{
 "hosts": [
  "admin-dev.lab-l.example"
 ],
 "ingress": "app-s-admin",
 "namespace": "dev-app-s",
 "services": [
  "app-s-admin"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-s/app-s-api</code></summary>

```json
{
 "hosts": [
  "api-dev.v1.lab-l.example"
 ],
 "ingress": "app-s-api",
 "namespace": "dev-app-s",
 "services": [
  "app-s-api"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-s/app-s-backend</code></summary>

```json
{
 "hosts": [
  "api-dev.lab-l.example"
 ],
 "ingress": "app-s-backend",
 "namespace": "dev-app-s",
 "services": [
  "app-s-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-s/app-s-frontend</code></summary>

```json
{
 "hosts": [
  "dev.lab-l.example"
 ],
 "ingress": "app-s-frontend",
 "namespace": "dev-app-s",
 "services": [
  "app-s-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-v/app-v-admin-frontend</code></summary>

```json
{
 "hosts": [
  "admin-dev.lab-n.example"
 ],
 "ingress": "app-v-admin-frontend",
 "namespace": "dev-app-v",
 "services": [
  "app-v-admin-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-v/app-v-backend</code></summary>

```json
{
 "hosts": [
  "api-dev.lab-n.example"
 ],
 "ingress": "app-v-backend",
 "namespace": "dev-app-v",
 "services": [
  "app-v-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-v/app-v-frontend</code></summary>

```json
{
 "hosts": [
  "dev.lab-n.example"
 ],
 "ingress": "app-v-frontend",
 "namespace": "dev-app-v",
 "services": [
  "app-v-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-y/app-y-admin</code></summary>

```json
{
 "hosts": [
  "admin-dev.lab-m.example"
 ],
 "ingress": "app-y-admin",
 "namespace": "dev-app-y",
 "services": [
  "app-y-admin"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-y/app-y-ai</code></summary>

```json
{
 "hosts": [
  "ai-dev.lab-m.example"
 ],
 "ingress": "app-y-ai",
 "namespace": "dev-app-y",
 "services": [
  "app-y-ai"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-y/app-y-backend</code></summary>

```json
{
 "hosts": [
  "app-y-api-dev.lab-k.example"
 ],
 "ingress": "app-y-backend",
 "namespace": "dev-app-y",
 "services": [
  "app-y-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.dev-app-y/app-y-frontend</code></summary>

```json
{
 "hosts": [
  "app-y-dev.lab-k.example"
 ],
 "ingress": "app-y-frontend",
 "namespace": "dev-app-y",
 "services": [
  "app-y-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.middleware/kafka-ui</code></summary>

```json
{
 "hosts": [
  "kafka.lab-k.example"
 ],
 "ingress": "kafka-ui",
 "namespace": "middleware",
 "services": [
  "kafka-ui"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.middleware/redis-insight</code></summary>

```json
{
 "hosts": [
  "redis.lab-k.example"
 ],
 "ingress": "redis-insight",
 "namespace": "middleware",
 "services": [
  "redis-insight"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.monitoring/kube-prometheus-stack-grafana</code></summary>

```json
{
 "hosts": [
  "monitor.lab-k.example"
 ],
 "ingress": "kube-prometheus-stack-grafana",
 "namespace": "monitoring",
 "services": [
  "kube-prometheus-stack-grafana"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.monitoring/vmauth</code></summary>

```json
{
 "hosts": [
  "metrics-write.lab-k.example"
 ],
 "ingress": "vmauth",
 "namespace": "monitoring",
 "services": [
  "vmauth"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-r/app-r-backend</code></summary>

```json
{
 "hosts": [
  "app-r-api.lab-k.example"
 ],
 "ingress": "app-r-backend",
 "namespace": "prod-app-r",
 "services": [
  "app-r-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-r/app-r-web</code></summary>

```json
{
 "hosts": [
  "app-r.lab-k.example"
 ],
 "ingress": "app-r-web",
 "namespace": "prod-app-r",
 "services": [
  "app-r-web"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-s/app-s-admin</code></summary>

```json
{
 "hosts": [
  "canary-admin.lab-l.example",
  "admin.lab-l.example"
 ],
 "ingress": "app-s-admin",
 "namespace": "prod-app-s",
 "services": [
  "app-s-admin"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-s/app-s-api</code></summary>

```json
{
 "hosts": [
  "canary-api-v1.lab-l.example",
  "api.v1.lab-l.example"
 ],
 "ingress": "app-s-api",
 "namespace": "prod-app-s",
 "services": [
  "app-s-api"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-s/app-s-backend</code></summary>

```json
{
 "hosts": [
  "canary-api.lab-l.example",
  "api.lab-l.example"
 ],
 "ingress": "app-s-backend",
 "namespace": "prod-app-s",
 "services": [
  "app-s-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-s/app-s-frontend</code></summary>

```json
{
 "hosts": [
  "canary.lab-l.example",
  "www.lab-l.example",
  "lab-l.example"
 ],
 "ingress": "app-s-frontend",
 "namespace": "prod-app-s",
 "services": [
  "app-s-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-t/app-t-ai</code></summary>

```json
{
 "hosts": [
  "app-t-ai.lab-k.example"
 ],
 "ingress": "app-t-ai",
 "namespace": "prod-app-t",
 "services": [
  "app-t-ai"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-t/app-t-backend</code></summary>

```json
{
 "hosts": [
  "app-t-api.lab-k.example"
 ],
 "ingress": "app-t-backend",
 "namespace": "prod-app-t",
 "services": [
  "app-t-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-t/app-t-studio</code></summary>

```json
{
 "hosts": [
  "app-t-studio.lab-k.example"
 ],
 "ingress": "app-t-studio",
 "namespace": "prod-app-t",
 "services": [
  "app-t-studio"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-t/app-t-web</code></summary>

```json
{
 "hosts": [
  "app-t.lab-k.example"
 ],
 "ingress": "app-t-web",
 "namespace": "prod-app-t",
 "services": [
  "app-t-web"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "hosts": [
  "admin.lab-n.example"
 ],
 "ingress": "app-v-admin-frontend",
 "namespace": "prod-app-v",
 "services": [
  "app-v-admin-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-v/app-v-backend</code></summary>

```json
{
 "hosts": [
  "api.lab-n.example"
 ],
 "ingress": "app-v-backend",
 "namespace": "prod-app-v",
 "services": [
  "app-v-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-v/app-v-frontend</code></summary>

```json
{
 "hosts": [
  "lab-n.example",
  "www.lab-n.example"
 ],
 "ingress": "app-v-frontend",
 "namespace": "prod-app-v",
 "services": [
  "app-v-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-w/app-w</code></summary>

```json
{
 "hosts": [
  "app-w.lab-k.example"
 ],
 "ingress": "app-w",
 "namespace": "prod-app-w",
 "services": [
  "app-w"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-x/app-x-api</code></summary>

```json
{
 "hosts": [
  "app-x-api.lab-k.example"
 ],
 "ingress": "app-x-api",
 "namespace": "prod-app-x",
 "services": [
  "app-x-api"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-y/app-y-admin</code></summary>

```json
{
 "hosts": [
  "admin.lab-m.example"
 ],
 "ingress": "app-y-admin",
 "namespace": "prod-app-y",
 "services": [
  "app-y-admin"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-y/app-y-ai</code></summary>

```json
{
 "hosts": [
  "ai.lab-m.example"
 ],
 "ingress": "app-y-ai",
 "namespace": "prod-app-y",
 "services": [
  "app-y-ai"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-y/app-y-backend</code></summary>

```json
{
 "hosts": [
  "api.lab-m.example"
 ],
 "ingress": "app-y-backend",
 "namespace": "prod-app-y",
 "services": [
  "app-y-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-y/app-y-frontend</code></summary>

```json
{
 "hosts": [
  "lab-m.example",
  "www.lab-m.example"
 ],
 "ingress": "app-y-frontend",
 "namespace": "prod-app-y",
 "services": [
  "app-y-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-z-backend/app-z-backend</code></summary>

```json
{
 "hosts": [
  "app-z-api.lab-k.example"
 ],
 "ingress": "app-z-backend",
 "namespace": "prod-app-z-backend",
 "services": [
  "app-z-backend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.golden-signals-missing.prod-app-z-backend/app-z-frontend</code></summary>

```json
{
 "hosts": [
  "app-z.lab-k.example"
 ],
 "ingress": "app-z-frontend",
 "namespace": "prod-app-z-backend",
 "services": [
  "app-z-frontend"
 ],
 "source": "alb-cloudwatch (not collected)"
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
 "by_class": {
  "app-cause": 5,
  "app": 22,
  "cause": 130
 },
 "by_severity": {
  "critical": 48,
  "warning": 97,
  "page": 2,
  "high": 3,
  "none": 2,
  "info": 5
 },
 "page_severity_cause": [
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
  "PrometheusRemoteStorageFailures",
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
 "any_signal": true,
 "burn_rate_alerts": [],
 "sli_recording_rules": [],
 "slo_labelled_rules": [
  "ImageInferenceE2ESuccessRateDrop",
  "ImageInferenceEntitlementFailureSpike",
  "LoraTrainingSuccessRateDrop",
  "LoraTrainingDurationP95High",
  "LoraTrainingCallbackTimeout"
 ],
 "tools": []
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
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
 "workload": "dev-app-aa/statefulset/app-aa-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U vxt_chatbot -d vxt_chatbot_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U vxt_chatbot -d vxt_chatbot_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "dev-app-aa/statefulset/app-aa-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
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
 "workload": "dev-app-s/statefulset/app-s-backend-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
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
 "workload": "dev-app-v/statefulset/app-v-backend-dev-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.dev-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

```json
{
 "container": "mysql",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
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
 "workload": "dev-app-y/statefulset/app-y-backend-mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "container": "loki",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 },
 "prod": false,
 "readiness": {
  "type": "httpGet",
  "path": "/ready",
  "port": "http-metrics",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 45
 },
 "startup": null,
 "workload": "monitoring/statefulset/loki-stack"
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
  "(none, 0)": 111,
  "system-cluster-critical": 9,
  "system-node-critical": 27
 },
 "preempted_events": 0,
 "prod_max_priority": 0,
 "prod_pods": 45,
 "prod_pods_without_class": 45,
 "user_classes": []
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.cluster</code></summary>

```json
{
 "count": 0,
 "db_workloads_with_pvc": 18,
 "local_only": [],
 "prod_db_without_backup_cronjob": [
  "app-ab-prod/statefulset/app-ab-backend-postgresql",
  "prod-app-r/statefulset/app-r-postgresql",
  "prod-app-s/statefulset/app-s-backend-mysql",
  "prod-app-t/statefulset/app-t-backend-postgresql",
  "prod-app-v/statefulset/app-v-backend-prod-mysql",
  "prod-app-x/statefulset/app-x-postgresql",
  "prod-app-y/statefulset/app-y-backend-mysql",
  "prod-app-z-backend/statefulset/app-z-neo4j"
 ],
 "same_node": []
}
```

</details>
<details><summary><code>resilience.recreate-strategy-serving.monitoring/deployment/vmauth</code></summary>

```json
{
 "grace_s": 30,
 "namespace": "monitoring",
 "prestop": false,
 "prod": false,
 "recreate_justified": false,
 "recreate_reason": [],
 "replicas": 1,
 "strategy": "Recreate",
 "workload": "monitoring/deployment/vmauth"
}
```

</details>
<details><summary><code>resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master</code></summary>

```json
{
 "grace_s": 30,
 "prestop": false,
 "prod": false,
 "shell_pid1_containers": [
  "redis",
  "metrics"
 ],
 "workload": "middleware/statefulset/redis-master"
}
```

</details>
<details><summary><code>resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.19 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "argocd-repo-server",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 257 MB, memory limit 1024 → 257 MB",
 "target": "argocd/deployment/argocd-repo-server:repo-server"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-aa/statefulset/app-aa-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.19 cores, memory request over by 341 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-aa-mysql",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 1024 → 683 MB, memory limit 2048 → 683 MB",
 "target": "dev-app-aa/statefulset/app-aa-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 114 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "OK",
 "name": "app-s-backend-mysql",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 626 MB, memory limit 1024 → 626 MB",
 "target": "dev-app-s/statefulset/app-s-backend-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.dev-app-y/deployment/app-y-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "UNKNOWN",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 359 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-y-backend",
 "severity": "CRITICAL",
 "summary": "CPU HPA detected, memory request 512 → 153 MB, memory limit 8192 → 153 MB",
 "target": "dev-app-y/deployment/app-y-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.karpenter/deployment/karpenter:controller</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 152 MB, CPU request over by 0.18 cores",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "karpenter",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.02 cores, CPU limit 0.5 → none, memory request 256 → 408 MB",
 "target": "karpenter/deployment/karpenter:controller"
}
```

</details>
<details><summary><code>resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.13 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "kafka-controller",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.07 cores, CPU limit 0.5 → none, memory request 1536 → 1466 MB, memory limit 2048 → 1466 MB",
 "target": "middleware/statefulset/kafka-controller:kafka"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 144 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "OK",
 "name": "loki-stack-promtail",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.017 cores, CPU limit 0.1 → none, memory request 128 → 272 MB",
 "target": "monitoring/daemonset/loki-stack-promtail:promtail"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-r/deployment/app-r-web:web</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 68 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-r-web",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "target": "prod-app-r/deployment/app-r-web:web"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-s/deployment/app-s-frontend:frontend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 222 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "OK",
 "name": "app-s-frontend",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.031 cores, CPU limit 0.2 → none, memory request 128 → 350 MB",
 "target": "prod-app-s/deployment/app-s-frontend:frontend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-t/deployment/app-t-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 189 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-t-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 192 → 381 MB",
 "target": "prod-app-t/deployment/app-t-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-t/deployment/app-t-web:web</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 68 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-t-web",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "target": "prod-app-t/deployment/app-t-web:web"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-v/deployment/app-v-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 89 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "GOOD",
 "name": "app-v-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.03 → 0.013 cores, CPU limit 0.5 → none, memory request 128 → 217 MB, memory limit 512 → 217 MB",
 "target": "prod-app-v/deployment/app-v-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.189 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "app-v-backend-prod-mysql",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 812 MB, memory limit 1536 → 812 MB",
 "target": "prod-app-v/statefulset/app-v-backend-prod-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-y/deployment/app-y-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 396 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-y-backend",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 2.0 → none, memory request 512 → 116 MB, memory limit 2048 → 116 MB",
 "target": "prod-app-y/deployment/app-y-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.19 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "app-y-backend-mysql",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB",
 "target": "prod-app-y/statefulset/app-y-backend-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/deployment/app-z-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "UNKNOWN",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 410 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-z-backend",
 "severity": "CRITICAL",
 "summary": "CPU HPA detected, memory request 1024 → 614 MB, memory limit 2048 → 614 MB",
 "target": "prod-app-z-backend/deployment/app-z-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-z-backend/deployment/app-z-pg-proxy:forwarder</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 68 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-z-pg-proxy",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "target": "prod-app-z-backend/deployment/app-z-pg-proxy:forwarder"
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
 "prod_without_psa": [
  "app-ab-prod",
  "prod-app-r",
  "prod-app-s",
  "prod-app-t",
  "prod-app-v",
  "prod-app-w",
  "prod-app-x",
  "prod-app-y",
  "prod-app-z-backend"
 ],
 "psa_enforced_namespaces": [],
 "root_allowed_prod": [
  "prod-app-w/deployment/app-w",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-t/deployment/app-t-backend",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-t/deployment/app-t-web",
  "prod-app-x/deployment/app-x-api",
  "prod-app-s/deployment/app-s-admin",
  "prod-app-s/deployment/app-s-api",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-y/deployment/app-y-frontend",
  "prod-app-z-backend/deployment/app-z-backend",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/app-z-file-worker",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-z-backend/deployment/app-z-graph-worker",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "prod-app-z-backend/deployment/tts-proxy",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/deployment/app-r-web",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "app-ab-prod/deployment/app-ab-backend",
  "app-ab-prod/deployment/app-ab-frontend",
  "prod-app-z-backend/statefulset/app-z-neo4j"
 ],
 "root_allowed_ratio": 0.61
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
 "automount_false_sa": 7,
 "service_accounts": 113,
 "token_mounted": 86,
 "token_mounted_without_rbac_prod": [
  "prod-app-w/deployment/app-w",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-t/deployment/app-t-backend",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-t/deployment/app-t-web",
  "prod-app-x/deployment/app-x-api",
  "prod-app-s/deployment/app-s-admin",
  "prod-app-s/deployment/app-s-api",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-s/statefulset/app-s-backend-mysql",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-y/statefulset/app-y-backend-mysql",
  "prod-app-y/deployment/app-y-frontend",
  "prod-app-z-backend/deployment/app-z-backend",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "prod-app-z-backend/deployment/tts-proxy",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/deployment/app-r-web",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/statefulset/app-v-backend-prod-mysql",
  "prod-app-v/deployment/app-v-frontend",
  "app-ab-prod/deployment/app-ab-backend",
  "app-ab-prod/deployment/app-ab-frontend"
 ],
 "workloads": 92
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
 "prod_db_delete_reclaim": [
  "prod-app-t/data-app-t-backend-postgresql-0",
  "prod-app-x/data-app-x-postgresql-0",
  "prod-app-s/data-app-s-backend-mysql-0",
  "prod-app-y/data-app-y-backend-mysql-0",
  "prod-app-z-backend/data-app-z-neo4j-0",
  "prod-app-r/data-app-r-postgresql-0",
  "prod-app-v/data-app-v-backend-prod-mysql-0",
  "app-ab-prod/data-app-ab-backend-postgresql-0"
 ],
 "rows": [
  {
   "namespace": "dev-app-s",
   "name": "data-app-s-backend-mysql-0",
   "target": "dev-app-s/data-app-s-backend-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-s-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-273a8340-e63c-44b5-8618-433a85e68cdd",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-y",
   "name": "data-app-y-backend-mysql-0",
   "target": "dev-app-y/data-app-y-backend-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-y-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-878f1d5b-67fc-4640-8d1d-516caa26e7df",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-v",
   "name": "data-app-v-backend-dev-mysql-0",
   "target": "dev-app-v/data-app-v-backend-dev-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-v-backend-dev-mysql"
   ],
   "db_like": true,
   "pv": "pvc-0138f912-7588-42ed-9850-b6f7e4dfd422",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-aa",
   "name": "data-app-aa-mysql-0",
   "target": "dev-app-aa/data-app-aa-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-aa-mysql"
   ],
   "db_like": true,
   "pv": "pvc-ebee9c1c-11b1-41af-b913-e3c72dad2bda",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-aa",
   "name": "data-app-aa-postgres-0",
   "target": "dev-app-aa/data-app-aa-postgres-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-aa-postgres"
   ],
   "db_like": true,
   "pv": "pvc-750ab148-9691-40f1-8eeb-ed31aead86a8",
   "zone": "ap-northeast-2c",
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
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/kafka-controller"
   ],
   "db_like": true,
   "pv": "pvc-b86f8034-3a78-4458-b3b8-c6aed3a919a2",
   "zone": "ap-northeast-2c",
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
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/redis-master"
   ],
   "db_like": true,
   "pv": "pvc-391869b9-4c33-41b5-977f-553dc4d5dc0f",
   "zone": "ap-northeast-2c",
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
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "deployment/kube-prometheus-stack-grafana"
   ],
   "db_like": false,
   "pv": "pvc-9787333f-be2a-4ec2-9b6b-6b81756a4e94",
   "zone": "ap-northeast-2a",
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
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/prometheus-kube-prometheus-stack-prometheus"
   ],
   "db_like": true,
   "pv": "pvc-0bced2ad-d452-4dce-a717-e11877feae44",
   "zone": "ap-northeast-2a",
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
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/vm-single"
   ],
   "db_like": false,
   "pv": "pvc-6af4b3e1-029f-453e-b7c6-198a618fb3e5",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-t",
   "name": "data-app-t-backend-postgresql-0",
   "target": "prod-app-t/data-app-t-backend-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-t-backend-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-1a304f49-fa2e-43ed-a996-df104613c88c",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-x",
   "name": "data-app-x-postgresql-0",
   "target": "prod-app-x/data-app-x-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-x-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-51db83d1-4c6f-450f-b50f-55abbe8ed212",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-s",
   "name": "data-app-s-backend-mysql-0",
   "target": "prod-app-s/data-app-s-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-s-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-9f1aab56-d94c-499d-8df6-2def93e79427",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-y",
   "name": "data-app-y-backend-mysql-0",
   "target": "prod-app-y/data-app-y-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 50.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-y-backend-mysql"
   ],
   "db_like": true,
   "pv": "pvc-ebc5618b-a1af-40d3-b15d-4969ed13487e",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-z-backend",
   "name": "data-app-z-neo4j-0",
   "target": "prod-app-z-backend/data-app-z-neo4j-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-z-neo4j"
   ],
   "db_like": true,
   "pv": "pvc-5cccf1df-7624-45a2-833d-2191c5490713",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-r",
   "name": "data-app-r-postgresql-0",
   "target": "prod-app-r/data-app-r-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-r-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-8d1f15c7-e0e6-4410-bd40-64d7332aef0d",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "prod-app-v",
   "name": "data-app-v-backend-prod-mysql-0",
   "target": "prod-app-v/data-app-v-backend-prod-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-v-backend-prod-mysql"
   ],
   "db_like": true,
   "pv": "pvc-a50dcc70-b062-457a-b0e3-07a3e6da2ec6",
   "zone": "ap-northeast-2c",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ab-prod",
   "name": "data-app-ab-backend-postgresql-0",
   "target": "app-ab-prod/data-app-ab-backend-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": false,
   "workloads": [
    "statefulset/app-ab-backend-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-f226562f-a020-4027-a0d4-1494585c8b6f",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  }
 ]
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-ab-prod</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.25,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 0.94,
 "multi_org": false,
 "namespace": "app-ab-prod",
 "pods": 3,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-runners</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": null,
 "cpu_requests": 0.0,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "ci",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 0.0,
 "namespace": "arc-runners",
 "pods": 0,
 "prod": false,
 "shares_nodes_with_prod": false,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-aa</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": null,
 "cpu_requests": 0.55,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.88,
 "namespace": "dev-app-aa",
 "pods": 4,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-s</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": null,
 "cpu_requests": 0.4,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.25,
 "namespace": "dev-app-s",
 "pods": 5,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-v</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": null,
 "cpu_requests": 0.3,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.0,
 "namespace": "dev-app-v",
 "pods": 4,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-y</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": null,
 "cpu_requests": 0.4,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 2.25,
 "namespace": "dev-app-y",
 "pods": 5,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-r</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.62,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.28,
 "multi_org": false,
 "namespace": "prod-app-r",
 "pods": 3,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-s</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.35,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.62,
 "multi_org": false,
 "namespace": "prod-app-s",
 "pods": 8,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-t</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.29,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 0.84,
 "multi_org": false,
 "namespace": "prod-app-t",
 "pods": 5,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-v</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.25,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 1.12,
 "multi_org": false,
 "namespace": "prod-app-v",
 "pods": 4,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-w</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.1,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 0.25,
 "multi_org": false,
 "namespace": "prod-app-w",
 "pods": 2,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-x</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 1.1,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 2.25,
 "multi_org": false,
 "namespace": "prod-app-x",
 "pods": 3,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-y</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 0.51,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 8.0,
 "multi_org": false,
 "namespace": "prod-app-y",
 "pods": 8,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-z-backend</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": null,
 "cpu_requests": 2.72,
 "cpu_share_of_cluster_p95": null,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "memory_requests_gb": 14.53,
 "multi_org": false,
 "namespace": "prod-app-z-backend",
 "pods": 9,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 14
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.ip-10-0-1-117.ap-northeast-2.compute.internal</code></summary>

```json
{
 "allocatable_memory_gb": 6.9,
 "containers_without_memory_limit": 3,
 "memory_limit_overcommit": 1.68,
 "memory_limits_gb": 11.6,
 "memory_requests_gb": 4.7,
 "namespaces": {
  "kube-system": 3,
  "keda": 2,
  "monitoring": 2,
  "argocd": 1,
  "dev-app-y": 1,
  "dev-app-aa": 1,
  "karpenter": 1,
  "prod-app-y": 1,
  "app-ab-prod": 1
 },
 "node": "ip-10-0-1-117.ap-northeast-2.compute.internal",
 "pool": "system_core-20251217040546303900000001",
 "prod_pods": 2,
 "tenant_count": 2,
 "tenant_kinds": [
  "dev",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.ip-10-0-1-139.ap-northeast-2.compute.internal</code></summary>

```json
{
 "allocatable_memory_gb": 29.8,
 "containers_without_memory_limit": 0,
 "memory_limit_overcommit": 1.58,
 "memory_limits_gb": 47.0,
 "memory_requests_gb": 18.9,
 "namespaces": {
  "prod-app-y": 7,
  "dev-app-y": 4,
  "prod-app-s": 4,
  "prod-app-z-backend": 4,
  "dev-app-s": 3,
  "prod-app-v": 3,
  "dev-app-v": 2,
  "prod-app-w": 2,
  "app-ab-prod": 2,
  "dev-app-aa": 1,
  "external-secrets": 1,
  "prod-app-x": 1
 },
 "node": "ip-10-0-1-139.ap-northeast-2.compute.internal",
 "pool": "default",
 "prod_pods": 23,
 "tenant_count": 2,
 "tenant_kinds": [
  "dev",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.ip-10-0-2-218.ap-northeast-2.compute.internal</code></summary>

```json
{
 "allocatable_memory_gb": 3.2,
 "containers_without_memory_limit": 1,
 "memory_limit_overcommit": 1.79,
 "memory_limits_gb": 5.7,
 "memory_requests_gb": 2.0,
 "namespaces": {
  "monitoring": 4,
  "argocd": 1,
  "dev-app-aa": 1,
  "keda": 1,
  "kube-system": 1,
  "middleware": 1,
  "prod-app-t": 1,
  "prod-app-x": 1
 },
 "node": "ip-10-0-2-218.ap-northeast-2.compute.internal",
 "pool": "system-ondemand",
 "prod_pods": 2,
 "tenant_count": 3,
 "tenant_kinds": [
  "dev",
  "other",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.prod-app-z-backend</code></summary>

```json
{
 "cluster_saturated_7d": false,
 "containers_without_memory_limit": 2,
 "containers_without_requests": 2,
 "cpu_p95_7d": null,
 "has_limitrange": false,
 "kind": "prod",
 "memory_p95_7d_gb": null,
 "multi_org": false,
 "namespace": "prod-app-z-backend",
 "pods": 9,
 "prod": true
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/argocd/argocd-server</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "deploy.lab-k.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/argocd/argocd-server",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-s/app-s-admin</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "admin-dev.lab-l.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/dev-app-s/app-s-admin",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-v/app-v-admin-frontend</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "admin-dev.lab-n.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/dev-app-v/app-v-admin-frontend",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/dev-app-y/app-y-admin</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "admin-dev.lab-m.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/dev-app-y/app-y-admin",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-s/app-s-admin</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "canary-admin.lab-l.example",
  "admin.lab-l.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/prod-app-s/app-s-admin",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "admin.lab-n.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/prod-app-v/app-v-admin-frontend",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>traffic.external-exposure.ingress/prod-app-y/app-y-admin</code></summary>

```json
{
 "admin_like": true,
 "has_auth_hint": false,
 "hosts": [
  "admin.lab-m.example"
 ],
 "scheme": "internet-facing",
 "target": "ingress/prod-app-y/app-y-admin",
 "tls": true,
 "type": "ingress"
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "containers": 113,
 "emptydir_without_sizelimit": 22,
 "emptydir_without_sizelimit_prod": [
  "app-ab-prod/statefulset/app-ab-backend-postgresql",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/statefulset/app-r-postgresql",
  "prod-app-t/statefulset/app-t-backend-postgresql",
  "prod-app-x/statefulset/app-x-postgresql",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/tts-proxy"
 ],
 "prod_without_request": 35,
 "request_ratio": 0.009,
 "with_request": 1
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "replicasets_total": 428,
 "replicasets_zero": 362,
 "revision_history_limits": {
  "10": 62,
  "3": 6
 }
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-1-117.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-1-117.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-1-137.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-1-137.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-1-139.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-1-139.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-1-241.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-1-241.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-1-245.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-1-245.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-2-100.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-2-100.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-2-135.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-2-135.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-2-218.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-2-218.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.ip-10-0-2-60.ap-northeast-2.compute.internal</code></summary>

```json
{
 "node": "ip-10-0-2-60.ap-northeast-2.compute.internal",
 "reason": "os.txt missing"
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
  "parameters": {
   "fsType": "ext4",
   "type": "gp2"
  },
  "provisioner": "kubernetes.io/aws-ebs"
 }
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-1-117.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 3,
 "cpu_limit_overcommit": 3.37,
 "dev_namespaces": [
  "dev-app-aa",
  "dev-app-y"
 ],
 "dev_pods": 2,
 "memory_limit_overcommit": 1.68,
 "node": "ip-10-0-1-117.ap-northeast-2.compute.internal",
 "pool": "system_core-20251217040546303900000001",
 "prod_namespaces": [
  "app-ab-prod",
  "prod-app-y"
 ],
 "prod_pods": 2,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-1-139.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 0,
 "cpu_limit_overcommit": 7.14,
 "dev_namespaces": [
  "dev-app-aa",
  "dev-app-s",
  "dev-app-v",
  "dev-app-y"
 ],
 "dev_pods": 10,
 "memory_limit_overcommit": 1.58,
 "node": "ip-10-0-1-139.ap-northeast-2.compute.internal",
 "pool": "default",
 "prod_namespaces": [
  "app-ab-prod",
  "prod-app-s",
  "prod-app-v",
  "prod-app-w",
  "prod-app-x",
  "prod-app-y",
  "prod-app-z-backend"
 ],
 "prod_pods": 23,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-2-218.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 1,
 "cpu_limit_overcommit": 1.81,
 "dev_namespaces": [
  "dev-app-aa"
 ],
 "dev_pods": 1,
 "memory_limit_overcommit": 1.79,
 "node": "ip-10-0-2-218.ap-northeast-2.compute.internal",
 "pool": "system-ondemand",
 "prod_namespaces": [
  "prod-app-t",
  "prod-app-x"
 ],
 "prod_pods": 2,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>albctl.aws-api-churn.cluster</code></summary>

```json
{
 "aws_api_calls_total": 242614,
 "aws_api_retries_avg": 0.0,
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
   0.265
  ]
 ],
 "aws_api_top_ops": [
  [
   "Elastic Load Balancing v2/DescribeTargetHealth",
   76055
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroupAttributes",
   43347
  ],
  [
   "EC2/DescribeInstances",
   38801
  ],
  [
   "EC2/DescribeSecurityGroups",
   24999
  ],
  [
   "Elastic Load Balancing v2/RegisterTargets",
   11793
  ],
  [
   "Elastic Load Balancing v2/DeregisterTargets",
   11660
  ],
  [
   "Elastic Load Balancing v2/DescribeTags",
   9199
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancers",
   3732
  ]
 ],
 "metrics_available": true,
 "rest_client_429_503": 126
}
```

</details>
<details><summary><code>alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "cluster_peers": 0,
 "cluster_status": null,
 "data_retention": "120h",
 "present": true,
 "ready": 1,
 "replicas": 1,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager"
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "applications_prod": 9,
 "notifications_configured": false,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "applications_prod": 9,
 "ignore_differences_apps": 3,
 "prod_tracking_moving_ref": [
  "argocd/application/app-w-prod",
  "argocd/application/app-t-prod",
  "argocd/application/app-x-prod",
  "argocd/application/app-s-prod",
  "argocd/application/app-y-prod",
  "argocd/application/app-ab-prod",
  "argocd/application/app-z-backend-prod",
  "argocd/application/app-r-prod",
  "argocd/application/app-v-prod"
 ]
}
```

</details>
<details><summary><code>argocd.version-eol.cluster</code></summary>

```json
{
 "components": {
  "applicationset-controller": "1/1",
  "dex-server": "1/1",
  "notifications-controller": "1/1",
  "redis": "1/1",
  "repo-server": "1/1",
  "server": "1/1",
  "application-controller": "1/1"
 },
 "version": "2.13.0",
 "version_major": 2
}
```

</details>
<details><summary><code>coredns.metrics-unavailable.cluster</code></summary>

```json
{
 "metrics_available": false,
 "replicas": 2,
 "version": "1.11.3"
}
```

</details>
<details><summary><code>ebscsi.controller-metrics-disabled.cluster</code></summary>

```json
{
 "addon_version": null,
 "api_errors_24h": {},
 "api_throttles_24h": null,
 "controller_metrics_enabled": false,
 "controller_metrics_series": 0,
 "controller_present": true,
 "version": "1.37.0"
}
```

</details>
<details><summary><code>eso.version-old.cluster</code></summary>

```json
{
 "externalsecrets": 49,
 "pushsecrets": 0,
 "version": "0.9.13"
}
```

</details>
<details><summary><code>grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "database": "ok",
 "ingress_hosts": [
  "monitor.lab-k.example"
 ],
 "major": 10,
 "present": true,
 "stats": {
  "totals_dashboard": 28,
  "totals_datasource": 4,
  "total_users": 1,
  "active_users": 1,
  "totals_alert_rules": 0
 },
 "target": "monitoring/deployment/kube-prometheus-stack-grafana",
 "version": "10.2.3"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "keda-admission-webhooks",
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.17.2",
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
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.17.2",
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
 "image": "ghcr.io/kedacore/keda:2.17.2",
 "pull_policy": "Always",
 "registry": "ghcr.io",
 "tag_kind": "tag",
 "workload": "keda/deployment/keda-operator"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "aws-eks-nodeagent",
 "image": "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1",
 "pull_policy": "Always",
 "registry": "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com",
 "tag_kind": "tag",
 "workload": "kube-system/daemonset/aws-node"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "aws-vpc-cni-init",
 "image": "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1",
 "pull_policy": "Always",
 "registry": "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com",
 "tag_kind": "tag",
 "workload": "kube-system/daemonset/aws-node"
}
```

</details>
<details><summary><code>hygiene.failed-pods-lingering.cluster</code></summary>

```json
{
 "by_namespace": {
  "prod-app-t": 1
 },
 "by_reason": {
  "Evicted": 1
 },
 "count": 1,
 "oldest_h": 16.6,
 "prod": 1,
 "sample": [
  "prod-app-t/app-t-backend-5f6c75bd56-n226l"
 ]
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "count": 47,
 "webhooks": 18,
 "zero_by_group": {
  "generators.external-secrets.io": 7,
  "monitoring.coreos.com": 6,
  "networking.k8s.aws": 4,
  "eventing.keda.sh": 2,
  "external-secrets.io": 3,
  "keda.sh": 2,
  "crd.k8s.amazonaws.com": 1,
  "actions.github.com": 1,
  "vpcresources.k8s.aws": 1
 },
 "zero_object_count": 27
}
```

</details>
<details><summary><code>karpenter.spot-to-spot-consolidation-off.cluster</code></summary>

```json
{
 "drift_enabled": true,
 "feature_gates": {
  "Drift": "true",
  "SpotToSpotConsolidation": "false"
 },
 "nodeclaims_terminated_by_reason": {
  "expiration": 6,
  "emptiness": 331,
  "interruption": 263,
  "consolidation": 304
 },
 "spot_to_spot_consolidation": false
}
```

</details>
<details><summary><code>keda.operator-metrics-disabled.cluster</code></summary>

```json
{
 "operator_metrics_present": false,
 "operator_prometheus_metrics": false,
 "scaler_errors_24h_logs": 0,
 "unused": false
}
```

</details>
<details><summary><code>keda.scaledobject-never-active.cluster</code></summary>

```json
{
 "fallback_active": [],
 "never_active_14d": [
  "dev-app-y/scaledobject/app-y-ai-kafka-lag"
 ],
 "not_ready": [],
 "scale_to_zero": [
  "prod-app-z-backend/scaledobject/app-z-file-worker",
  "prod-app-z-backend/scaledobject/app-z-graph-worker"
 ]
}
```

</details>
<details><summary><code>kubeproxy.metrics-not-scraped.cluster</code></summary>

```json
{
 "metrics_available": false,
 "metrics_bind_address": "0.0.0.0:10249",
 "metrics_loopback_only": false,
 "metrics_source": null,
 "nodes_total": 9,
 "targets_down": 0,
 "targets_down_nodes": [],
 "targets_up": 0
}
```

</details>
<details><summary><code>kubeproxy.node-cmd-unavailable.cluster</code></summary>

```json
{
 "mode": "iptables",
 "node_cmd_unavailable": [
  "ip-10-0-1-117.ap-northeast-2.compute.internal",
  "ip-10-0-1-137.ap-northeast-2.compute.internal",
  "ip-10-0-1-139.ap-northeast-2.compute.internal",
  "ip-10-0-1-241.ap-northeast-2.compute.internal",
  "ip-10-0-1-245.ap-northeast-2.compute.internal",
  "ip-10-0-2-100.ap-northeast-2.compute.internal",
  "ip-10-0-2-135.ap-northeast-2.compute.internal",
  "ip-10-0-2-218.ap-northeast-2.compute.internal",
  "ip-10-0-2-60.ap-northeast-2.compute.internal"
 ],
 "nodes_total": 9
}
```

</details>
<details><summary><code>loki.version-old.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "compactor_running": 1.0,
 "major": 2,
 "present": true,
 "retention_applied": false,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/loki-stack",
 "version": "2.6.1"
}
```

</details>
<details><summary><code>observability.alert-metric-without-dashboard.grafana</code></summary>

```json
{
 "alert_metrics": 194,
 "alert_metrics_without_panel": [
  "Without",
  "aggregator_unavailable_apiservice",
  "aggregator_unavailable_apiservice_total",
  "alerting",
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
  "cluster",
  "could",
  "create",
  "details",
  "etcd_mvcc_db_total_size_in_use_in_bytes",
  "etcd_network_peer_sent_failures_total",
  "etcd_server_proposals_failed_total",
  "etcd_server_quota_backend_bytes",
  "failed",
  "for",
  "gauges",
  "grpc_server_handling_seconds_bucket",
  "https:",
  "in",
  "io",
  "job",
  "kafka_consumergroup_lag",
  "kafka_consumergroup_members",
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
  "kube_job_status_start_time",
  "kube_node_spec_taint",
  "kube_node_status_condition",
  "kube_persistentvolume_status_phase",
  "kube_persistentvolumeclaim_access_mode",
  "kube_persistentvolumeclaim_labels",
  "kube_pod_container_status_waiting_reason",
  "kube_pod_info",
  "kube_pod_status_phase",
  "kube_state_metrics_list_total",
  "kube_state_metrics_shard_ordinal",
  "kube_state_metrics_total_shards",
  "kube_state_metrics_watch_total",
  "kube_statefulset_metadata_generation",
  "kube_statefulset_replicas",
  "kube_statefulset_status_current_revision",
  "kube_statefulset_status_observed_generation",
  "kube_statefulset_status_replicas",
  "kube_statefulset_status_replicas_ready",
  "kube_statefulset_status_replicas_updated",
  "kube_statefulset_status_update_revision",
  "kubelet_certificate_manager_client_expiration_renew_errors",
  "kubelet_certificate_manager_client_ttl_seconds",
  "kubelet_certificate_manager_server_ttl_seconds",
  "kubelet_server_expiration_renew_errors",
  "kubelet_volume_stats_inodes_free",
  "kubelet_volume_stats_used_bytes"
 ],
 "alert_metrics_without_panel_count": 153,
 "available": true,
 "panel_metrics": 196,
 "read": 28
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
 "fired_15d": [],
 "never_fired_15d": [
  "AlertmanagerClusterCrashlooping",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerFailedReload",
  "AlertmanagerFailedToSendAlerts",
  "AlertmanagerMembersInconsistent",
  "CPUThrottlingHigh",
  "ConfigReloaderSidecarErrors",
  "DmmConsumerLagHigh",
  "DmmConsumerMembersBelowExpected",
  "IlAngleBridgeMembersBelowExpected",
  "IlBridgeLagHigh",
  "IlBridgeMembersBelowExpected",
  "IlEditBridgeLagHigh",
  "IlEditBridgeMembersBelowExpected",
  "IlGenerationFailing",
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
  "KubeContainerWaiting",
  "KubeControllerManagerDown",
  "KubeDaemonSetMisScheduled",
  "KubeDaemonSetNotScheduled",
  "KubeDaemonSetRolloutStuck",
  "KubeDeploymentGenerationMismatch",
  "KubeDeploymentReplicasMismatch",
  "KubeDeploymentRolloutStuck",
  "KubeHpaMaxedOut",
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
  "KubePodNotReady",
  "KubeProxyDown",
  "KubeQuotaAlmostFull",
  "KubeQuotaExceeded",
  "KubeQuotaFullyUsed",
  "KubeSchedulerDown",
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
 "never_fired_count": 139,
 "rules_total": 141
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "ingresses": 41,
 "missing_saturation": [
  {
   "namespace": "argocd",
   "ingress": "argocd-server",
   "class": "alb",
   "hosts": [
    "deploy.lab-k.example"
   ],
   "services": [
    "argocd-server"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-s",
   "ingress": "app-s-admin",
   "class": "alb",
   "hosts": [
    "admin-dev.lab-l.example"
   ],
   "services": [
    "app-s-admin"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-s",
   "ingress": "app-s-api",
   "class": "alb",
   "hosts": [
    "api-dev.v1.lab-l.example"
   ],
   "services": [
    "app-s-api"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-s",
   "ingress": "app-s-backend",
   "class": "alb",
   "hosts": [
    "api-dev.lab-l.example"
   ],
   "services": [
    "app-s-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-s",
   "ingress": "app-s-frontend",
   "class": "alb",
   "hosts": [
    "dev.lab-l.example"
   ],
   "services": [
    "app-s-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-y",
   "ingress": "app-y-admin",
   "class": "alb",
   "hosts": [
    "admin-dev.lab-m.example"
   ],
   "services": [
    "app-y-admin"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-y",
   "ingress": "app-y-ai",
   "class": "alb",
   "hosts": [
    "ai-dev.lab-m.example"
   ],
   "services": [
    "app-y-ai"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-y",
   "ingress": "app-y-backend",
   "class": "alb",
   "hosts": [
    "app-y-api-dev.lab-k.example"
   ],
   "services": [
    "app-y-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-y",
   "ingress": "app-y-frontend",
   "class": "alb",
   "hosts": [
    "app-y-dev.lab-k.example"
   ],
   "services": [
    "app-y-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-v",
   "ingress": "app-v-admin-frontend",
   "class": "alb",
   "hosts": [
    "admin-dev.lab-n.example"
   ],
   "services": [
    "app-v-admin-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-v",
   "ingress": "app-v-backend",
   "class": "alb",
   "hosts": [
    "api-dev.lab-n.example"
   ],
   "services": [
    "app-v-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-v",
   "ingress": "app-v-frontend",
   "class": "alb",
   "hosts": [
    "dev.lab-n.example"
   ],
   "services": [
    "app-v-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-aa",
   "ingress": "app-aa-backend",
   "class": "alb",
   "hosts": [
    "demo-api.lab-m.example"
   ],
   "services": [
    "app-aa-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "dev-app-aa",
   "ingress": "app-aa-frontend",
   "class": "alb",
   "hosts": [
    "demo.lab-m.example"
   ],
   "services": [
    "app-aa-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "middleware",
   "ingress": "kafka-ui",
   "class": "alb",
   "hosts": [
    "kafka.lab-k.example"
   ],
   "services": [
    "kafka-ui"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "middleware",
   "ingress": "redis-insight",
   "class": "alb",
   "hosts": [
    "redis.lab-k.example"
   ],
   "services": [
    "redis-insight"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "monitoring",
   "ingress": "kube-prometheus-stack-grafana",
   "class": "alb",
   "hosts": [
    "monitor.lab-k.example"
   ],
   "services": [
    "kube-prometheus-stack-grafana"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "monitoring",
   "ingress": "vmauth",
   "class": "alb",
   "hosts": [
    "metrics-write.lab-k.example"
   ],
   "services": [
    "vmauth"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-w",
   "ingress": "app-w",
   "class": "alb",
   "hosts": [
    "app-w.lab-k.example"
   ],
   "services": [
    "app-w"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-t",
   "ingress": "app-t-ai",
   "class": "alb",
   "hosts": [
    "app-t-ai.lab-k.example"
   ],
   "services": [
    "app-t-ai"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-t",
   "ingress": "app-t-backend",
   "class": "alb",
   "hosts": [
    "app-t-api.lab-k.example"
   ],
   "services": [
    "app-t-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-t",
   "ingress": "app-t-studio",
   "class": "alb",
   "hosts": [
    "app-t-studio.lab-k.example"
   ],
   "services": [
    "app-t-studio"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-t",
   "ingress": "app-t-web",
   "class": "alb",
   "hosts": [
    "app-t.lab-k.example"
   ],
   "services": [
    "app-t-web"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-x",
   "ingress": "app-x-api",
   "class": "alb",
   "hosts": [
    "app-x-api.lab-k.example"
   ],
   "services": [
    "app-x-api"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-s",
   "ingress": "app-s-admin",
   "class": "alb",
   "hosts": [
    "canary-admin.lab-l.example",
    "admin.lab-l.example"
   ],
   "services": [
    "app-s-admin"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-s",
   "ingress": "app-s-api",
   "class": "alb",
   "hosts": [
    "canary-api-v1.lab-l.example",
    "api.v1.lab-l.example"
   ],
   "services": [
    "app-s-api"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-s",
   "ingress": "app-s-backend",
   "class": "alb",
   "hosts": [
    "canary-api.lab-l.example",
    "api.lab-l.example"
   ],
   "services": [
    "app-s-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-s",
   "ingress": "app-s-frontend",
   "class": "alb",
   "hosts": [
    "canary.lab-l.example",
    "www.lab-l.example",
    "lab-l.example"
   ],
   "services": [
    "app-s-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-y",
   "ingress": "app-y-admin",
   "class": "alb",
   "hosts": [
    "admin.lab-m.example"
   ],
   "services": [
    "app-y-admin"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-y",
   "ingress": "app-y-ai",
   "class": "alb",
   "hosts": [
    "ai.lab-m.example"
   ],
   "services": [
    "app-y-ai"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-y",
   "ingress": "app-y-backend",
   "class": "alb",
   "hosts": [
    "api.lab-m.example"
   ],
   "services": [
    "app-y-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-y",
   "ingress": "app-y-frontend",
   "class": "alb",
   "hosts": [
    "lab-m.example",
    "www.lab-m.example"
   ],
   "services": [
    "app-y-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-z-backend",
   "ingress": "app-z-backend",
   "class": "alb",
   "hosts": [
    "app-z-api.lab-k.example"
   ],
   "services": [
    "app-z-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-z-backend",
   "ingress": "app-z-frontend",
   "class": "alb",
   "hosts": [
    "app-z.lab-k.example"
   ],
   "services": [
    "app-z-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-r",
   "ingress": "app-r-backend",
   "class": "alb",
   "hosts": [
    "app-r-api.lab-k.example"
   ],
   "services": [
    "app-r-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-r",
   "ingress": "app-r-web",
   "class": "alb",
   "hosts": [
    "app-r.lab-k.example"
   ],
   "services": [
    "app-r-web"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-v",
   "ingress": "app-v-admin-frontend",
   "class": "alb",
   "hosts": [
    "admin.lab-n.example"
   ],
   "services": [
    "app-v-admin-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-v",
   "ingress": "app-v-backend",
   "class": "alb",
   "hosts": [
    "api.lab-n.example"
   ],
   "services": [
    "app-v-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "prod-app-v",
   "ingress": "app-v-frontend",
   "class": "alb",
   "hosts": [
    "lab-n.example",
    "www.lab-n.example"
   ],
   "services": [
    "app-v-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-ab-prod",
   "ingress": "app-ab-backend",
   "class": "alb",
   "hosts": [
    "app-ab-tp-api.lab-k.example"
   ],
   "services": [
    "app-ab-backend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  },
  {
   "namespace": "app-ab-prod",
   "ingress": "app-ab-frontend",
   "class": "alb",
   "hosts": [
    "app-ab-tp-prod.lab-k.example"
   ],
   "services": [
    "app-ab-frontend"
   ],
   "latency": false,
   "traffic": false,
   "errors": false,
   "saturation": false,
   "source": "alb-cloudwatch (not collected)",
   "missing_all_lte": true,
   "cluster_ic_metrics": false
  }
 ],
 "namespaces_with_saturation_metrics": []
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "error_lines_unclassified": 24,
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
 "lines_scanned": 23380,
 "unclassified_errors": [
  {
   "pattern": "ebs-csi | \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node …",
   "count": 8,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log": 4,
    "logs/pods/ebs-csi/kube-system_ebs-csi-node.log": 4
   },
   "sample": "[pod/ebs-csi-node-5942l/ebs-plugin] 2026-11-06T09:44:57.444277939Z E1106 09:44:57.444146       1 node.go:857] \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node ip-10-0-1-137.ap-nort"
  },
  {
   "pattern": "ebs-csi | \"Volume deletion failed\" err=\"persistentvolume pvc-<uuid> is still attached to node ip-10-0-1-98.ap-northeast-2.compute.internal\" …",
   "count": 4,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 4
   },
   "sample": "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-provisioner] 2026-11-06T08:58:33.262342297Z E1106 08:58:33.262266       1 controller.go:1558] \"Volume deletion failed\" err=\"persistentvolume pvc-014f87e5-611a-4e1b-a8ca-7392e8b26757 is still atta"
  },
  {
   "pattern": "ebs-csi | \"Unhandled Error\" err=\"error syncing volume \\\"pvc-<uuid>\\\": persistentvolume pvc-<uuid> is still attached to node …",
   "count": 4,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 4
   },
   "sample": "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-provisioner] 2026-11-06T08:58:33.262494744Z E1106 08:58:33.262448       1 controller.go:1025] \"Unhandled Error\" err=\"error syncing volume \\\"pvc-014f87e5-611a-4e1b-a8ca-7392e8b26757\\\": persistentv"
  },
  {
   "pattern": "ebs-csi | \"Event occurred\" object=\"prod-app-x/app-x-api-usage\" fieldPath=\"\" kind=\"PersistentVolumeClaim\" apiVersion=\"v1\" type=\"Warning\" …",
   "count": 3,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 3
   },
   "sample": "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-provisioner] 2026-11-06T07:44:20.454991784Z I1106 07:44:20.454890       1 event.go:389] \"Event occurred\" object=\"prod-app-x/app-x-api-usage\" fieldPath=\"\" kind=\"PersistentVolumeClaim\" apiVersion=\""
  },
  {
   "pattern": "ebs-csi | \"Unhandled Error\" err=\"error syncing claim \\\"<uuid>\\\": failed to provision volume with StorageClass \\\"gp3\\\": error generating accessibility …",
   "count": 3,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 3
   },
   "sample": "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-provisioner] 2026-11-06T07:44:20.455164108Z E1106 07:44:20.455119       1 controller.go:974] \"Unhandled Error\" err=\"error syncing claim \\\"014f87e5-611a-4e1b-a8ca-7392e8b26757\\\": failed to provisi"
  },
  {
   "pattern": "kube-proxy | \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted on all …",
   "count": 2,
   "files": {
    "logs/pods/kube-proxy/kube-system_kube-proxy.log": 2
   },
   "sample": "[pod/kube-proxy-46cc5/kube-proxy] 2026-11-06T08:59:05.940716243Z E1106 08:59:05.939170       1 server.go:234] \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted o"
  }
 ]
}
```

</details>
<details><summary><code>observability.unstructured-logs.app-ab-prod</code></summary>

```json
{
 "json_lines_1h": 0,
 "json_ratio": 0.0,
 "lines_1h": 947170,
 "namespace": "app-ab-prod"
}
```

</details>
<details><summary><code>observability.unstructured-logs.argocd</code></summary>

```json
{
 "json_lines_1h": 0,
 "json_ratio": 0.0,
 "lines_1h": 14865,
 "namespace": "argocd"
}
```

</details>
<details><summary><code>observability.unstructured-logs.dev-app-v</code></summary>

```json
{
 "json_lines_1h": 0,
 "json_ratio": 0.0,
 "lines_1h": 59439,
 "namespace": "dev-app-v"
}
```

</details>
<details><summary><code>prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "present": true,
 "ready": 1,
 "replicas": 1,
 "restarts": 2,
 "start_time": null,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "major": 2,
 "present": true,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "version": "2.49.1"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-ab-prod/statefulset/app-ab-backend-postgresql:postgresql</code></summary>

```json
{
 "container": "postgresql",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"pwcuser\" -d \"dbname=app-ab_tp\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"pwcuser\" -d \"dbname=app-ab_tp\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "app-ab-prod/statefulset/app-ab-backend-postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-aa/statefulset/app-aa-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-aa/statefulset/app-aa-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-aa/statefulset/app-aa-postgres:postgres</code></summary>

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
  "path": "pg_isready -U vxt_chatbot -d vxt_chatbot_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U vxt_chatbot -d vxt_chatbot_analytics",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "dev-app-aa/statefulset/app-aa-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-s/statefulset/app-s-backend-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-v/statefulset/app-v-backend-dev-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.dev-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "dev-app-y/statefulset/app-y-backend-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/aws-node:aws-node</code></summary>

```json
{
 "container": "aws-node",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "readiness": {
  "type": "exec",
  "path": "/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s",
  "port": null,
  "timeout_s": 10,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 1
 },
 "workload": "kube-system/daemonset/aws-node"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar</code></summary>

```json
{
 "container": "node-driver-registrar",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": null,
 "workload": "kube-system/daemonset/ebs-csi-node-windows"
}
```

</details>
<details><summary><code>resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar</code></summary>

```json
{
 "container": "node-driver-registrar",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe",
  "port": null,
  "timeout_s": 15,
  "period_s": 90,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": null,
 "workload": "kube-system/daemonset/ebs-csi-node"
}
```

</details>
<details><summary><code>resilience.exec-probe.middleware/statefulset/redis-master:redis</code></summary>

```json
{
 "container": "redis",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "sh -c /health/ping_liveness_local.sh 5",
  "port": null,
  "timeout_s": 6,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "exec",
  "path": "sh -c /health/ping_readiness_local.sh 1",
  "port": null,
  "timeout_s": 2,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "workload": "middleware/statefulset/redis-master"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-r/statefulset/app-r-postgresql:postgresql</code></summary>

```json
{
 "container": "postgresql",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-r\" -d \"dbname=app-r\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-r\" -d \"dbname=app-r\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "prod-app-r/statefulset/app-r-postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-s/statefulset/app-s-backend-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-s/statefulset/app-s-backend-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-t/statefulset/app-t-backend-postgresql:postgresql</code></summary>

```json
{
 "container": "postgresql",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-t\" -d \"dbname=app-t\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-t\" -d \"dbname=app-t\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "prod-app-t/statefulset/app-t-backend-postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-v/statefulset/app-v-backend-prod-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-x/statefulset/app-x-postgresql:postgresql</code></summary>

```json
{
 "container": "postgresql",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)"
 ],
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c exec pg_isready -U \"app-x\" -d \"dbname=app-x\" -h 127.0.0.1 -p 5432",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c -e exec pg_isready -U \"app-x\" -d \"dbname=app-x\" -h 127.0.0.1 -p 5432\n",
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 5
 },
 "workload": "prod-app-x/statefulset/app-x-postgresql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-y/statefulset/app-y-backend-mysql:mysql</code></summary>

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
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/bash -ec password_aux=\"${MYSQL_ROOT_PASSWORD:-}\"\nif [[ -f \"${MYSQL_ROOT_PASSWORD_FILE:-}\" ]]; then\n    password_aux=$(cat \"$MYSQL_ROOT_PASSWORD_FILE\")\nfi\nmysqladmin status -uroot -p\"${password_aux}\"\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "prod-app-y/statefulset/app-y-backend-mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-z-backend/deployment/app-z-file-worker:file-worker</code></summary>

```json
{
 "container": "file-worker",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)"
 ],
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.FileWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": null,
 "workload": "prod-app-z-backend/deployment/app-z-file-worker"
}
```

</details>
<details><summary><code>resilience.exec-probe.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker</code></summary>

```json
{
 "container": "graph-worker",
 "exec_probe": true,
 "flags": [
  "liveness exec (forks a process)"
 ],
 "liveness": {
  "type": "exec",
  "path": "arq --check app.worker.GraphWorkerSettings",
  "port": null,
  "timeout_s": 10,
  "period_s": 60,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": null,
 "workload": "prod-app-z-backend/deployment/app-z-graph-worker"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-r/deployment/app-r-backend:backend</code></summary>

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
  "port": 7860,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 7860,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-r/deployment/app-r-backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-r/deployment/app-r-web:web</code></summary>

```json
{
 "container": "web",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": null,
 "workload": "prod-app-r/deployment/app-r-web"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-s/deployment/app-s-admin:admin</code></summary>

```json
{
 "container": "admin",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-s/deployment/app-s-admin"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-s/deployment/app-s-api:api</code></summary>

```json
{
 "container": "api",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-s/deployment/app-s-api"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-s/deployment/app-s-backend:backend</code></summary>

```json
{
 "container": "backend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-s/deployment/app-s-backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-s/deployment/app-s-frontend:frontend</code></summary>

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
  "port": "http",
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 3,
  "period_s": 5,
  "failure_threshold": 2,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": "http",
  "timeout_s": 1,
  "period_s": 2,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-s/deployment/app-s-frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-t/deployment/app-t-ai:ai</code></summary>

```json
{
 "container": "ai",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
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
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "workload": "prod-app-t/deployment/app-t-ai"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-t/deployment/app-t-backend:backend</code></summary>

```json
{
 "container": "backend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-t/deployment/app-t-backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-t/deployment/app-t-studio:studio</code></summary>

```json
{
 "container": "studio",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 0
 },
 "workload": "prod-app-t/deployment/app-t-studio"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-t/deployment/app-t-web:web</code></summary>

```json
{
 "container": "web",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 80,
  "timeout_s": 3,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": null,
 "workload": "prod-app-t/deployment/app-t-web"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-x/deployment/app-x-api:api</code></summary>

```json
{
 "container": "api",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/api/v1/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/api/v1/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/api/v1/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": {
  "type": "httpGet",
  "path": "/api/v1/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 0
 },
 "workload": "prod-app-x/deployment/app-x-api"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.prod-app-z-backend/deployment/app-z-backend:backend</code></summary>

```json
{
 "container": "backend",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 5,
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
  "initial_delay_s": 0
 },
 "workload": "prod-app-z-backend/deployment/app-z-backend"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ab-prod/app-ab-backend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ab-prod/app-ab-frontend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-r/app-r-backend</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-r/app-r-web</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-t/app-t-ai</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-t/app-t-backend</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-t/app-t-studio</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-t/app-t-web</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-v/app-v-backend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-v/app-v-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-w/app-w</code></summary>

```json
{
 "namespace": "prod-app-w",
 "name": "app-w",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-x/app-x-api</code></summary>

```json
{
 "namespace": "prod-app-x",
 "name": "app-x-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-y/app-y-admin</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-y/app-y-ai</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-y/app-y-backend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-y/app-y-frontend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-z-backend/app-z-backend</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-z-backend/app-z-embedding-server</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-embedding-server",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-z-backend/app-z-frontend</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-z-backend/app-z-pg-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-pg-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.prod-app-z-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "cpu_only": true,
 "current_cpu_utilization": 0,
 "metric_types": [
  "cpu"
 ],
 "name": "app-z-backend",
 "namespace": "prod-app-z-backend",
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-frontend</code></summary>

```json
{
 "cpu_only": true,
 "current_cpu_utilization": 1,
 "metric_types": [
  "cpu"
 ],
 "name": "app-z-frontend",
 "namespace": "prod-app-z-backend",
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "desired_changes_7d": null,
 "has_behavior": false,
 "keda_owned": false,
 "max": 3,
 "min": 2,
 "name": "app-z-backend",
 "namespace": "prod-app-z-backend",
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-backend"
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-frontend</code></summary>

```json
{
 "desired_changes_7d": null,
 "has_behavior": false,
 "keda_owned": false,
 "max": 3,
 "min": 2,
 "name": "app-z-frontend",
 "namespace": "prod-app-z-backend",
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-frontend"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ab-prod/app-ab-backend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ab-prod/app-ab-frontend</code></summary>

```json
{
 "namespace": "app-ab-prod",
 "name": "app-ab-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-r/app-r-backend</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-r/app-r-web</code></summary>

```json
{
 "namespace": "prod-app-r",
 "name": "app-r-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-s/app-s-admin</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-s/app-s-api</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-s/app-s-backend</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-s/app-s-frontend</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-t/app-t-ai</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-t/app-t-backend</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-t/app-t-studio</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-studio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-t/app-t-web</code></summary>

```json
{
 "namespace": "prod-app-t",
 "name": "app-t-web",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-admin-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-v/app-v-backend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-v/app-v-frontend</code></summary>

```json
{
 "namespace": "prod-app-v",
 "name": "app-v-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-w/app-w</code></summary>

```json
{
 "namespace": "prod-app-w",
 "name": "app-w",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-x/app-x-api</code></summary>

```json
{
 "namespace": "prod-app-x",
 "name": "app-x-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-y/app-y-admin</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-admin",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-y/app-y-backend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-backend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-y/app-y-frontend</code></summary>

```json
{
 "namespace": "prod-app-y",
 "name": "app-y-frontend",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-z-backend/app-z-embedding-server</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-z-embedding-server",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-z-backend/tts-proxy</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "tts-proxy",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-1-245.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 0,
 "cpu_limit_overcommit": 2.98,
 "dev_namespaces": [
  "dev-app-s"
 ],
 "dev_pods": 1,
 "memory_limit_overcommit": 0.94,
 "node": "ip-10-0-1-245.ap-northeast-2.compute.internal",
 "pool": "default",
 "prod_namespaces": [
  "prod-app-t",
  "prod-app-z-backend"
 ],
 "prod_pods": 2,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-2-100.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 1,
 "cpu_limit_overcommit": 1.96,
 "dev_namespaces": [
  "dev-app-aa",
  "dev-app-v"
 ],
 "dev_pods": 2,
 "memory_limit_overcommit": 1.1,
 "node": "ip-10-0-2-100.ap-northeast-2.compute.internal",
 "pool": "default",
 "prod_namespaces": [
  "prod-app-r",
  "prod-app-s",
  "prod-app-t",
  "prod-app-z-backend"
 ],
 "prod_pods": 9,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.ip-10-0-2-60.ap-northeast-2.compute.internal</code></summary>

```json
{
 "containers_without_memory_limit": 2,
 "cpu_limit_overcommit": 2.44,
 "dev_namespaces": [
  "dev-app-s",
  "dev-app-v"
 ],
 "dev_pods": 2,
 "memory_limit_overcommit": 1.49,
 "node": "ip-10-0-2-60.ap-northeast-2.compute.internal",
 "pool": "system_core-20251217040546303900000001",
 "prod_namespaces": [
  "prod-app-s",
  "prod-app-v"
 ],
 "prod_pods": 2,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>vpccni.metrics-unreadable.cluster</code></summary>

```json
{
 "metrics_unavailable_nodes": [
  "ip-10-0-1-117.ap-northeast-2.compute.internal",
  "ip-10-0-1-137.ap-northeast-2.compute.internal",
  "ip-10-0-1-139.ap-northeast-2.compute.internal",
  "ip-10-0-1-241.ap-northeast-2.compute.internal",
  "ip-10-0-1-245.ap-northeast-2.compute.internal",
  "ip-10-0-2-100.ap-northeast-2.compute.internal",
  "ip-10-0-2-135.ap-northeast-2.compute.internal",
  "ip-10-0-2-218.ap-northeast-2.compute.internal",
  "ip-10-0-2-60.ap-northeast-2.compute.internal"
 ],
 "nodes": 9
}
```

</details>

### 7-6. 도구 메모 (kubegap 자체에 대한 것)

(이번 점검에서 쓰지 않음)

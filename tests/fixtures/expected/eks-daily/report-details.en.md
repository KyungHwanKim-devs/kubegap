# kubegap report details — arn:aws:eks:ap-northeast-2:<account>:cluster/app-u-cluster-eks (`app-u-cluster`), daily mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `report/outline.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `app-u-cluster` / arn:aws:eks:ap-northeast-2:<account>:cluster/app-u-cluster-eks (eks, v1.32.13-eks-577a51e) |
| Run time / mode | 2026-11-07T10:33:37+09:00 / daily (collection 300.7 s, 45 steps skipped by mode, 0 failed) |
| Scale | `medium` (guessed) |
| kubegap / rubric / signatures | <kubegap> / 0.1.93 / 1.1.0 |
| Verified against | Kubernetes v1.32.13-eks-577a51e (verified 1.30 to 1.37) · Prometheus 2.49.1 (verified 2.49 to 3.15) · Alertmanager 0.26.0 (verified 0.26 to 0.34) · Loki 2.6.1 (verified 2.6 to 3.7) · Grafana 10.2.3 (verified 10.2 to 13.3) |
| Nodes / namespaces / pods / CRDs | 9 (Ready 9) / 26 / 154 / 47 |
| Components (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics store | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| Log store | loki 2.6.1 |
| Node access | none (a daily run does not collect node-os (collected by: full)); SSM unregistered 0 |
| Snapshot | `<snapshot>` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 1 | 0 | no previous run of this mode |
| high | 22 | 21 | no previous run of this mode |
| medium | 84 | 98 | no previous run of this mode |
| low | 8 | 136 | no previous run of this mode |
| info | 0 | 0 | no previous run of this mode |

Checks 367: evaluated 270, not run on this platform or at this scale 3, skipped 6, not collected in this mode 86, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

(not written this run)

### 1-2. Aggregates the LLM recounted

(not written this run)

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | high |  | kubelet image GC could not free space. Disk is full of in-use images and logs. 1338 occurrences total (1 events, trend over 1 snapshots [1338], flat), first 2026-10-23T01:20:23Z last 2026-11-07T01:32:11Z. Top objects … |
| `karpenter.ec2nodeclass-al2.cluster` | high |  | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | high |  | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 289MB |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 252 days past |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.prod-concentration.ip-10-0-1-139.ap-northeast-2.compute.internal` | high |  | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default, spot) holds prod pods 23/45 (0.51), 18 workloads: ['app-ab-prod/app-ab-backend', 'app-ab-prod/app-ab-frontend', 'prod-app-s/app-s-admin' … |
| `resilience.replicas-same-node.prod-app-w/deployment/app-w` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-ai` | high |  | replicas 3 (Running 3), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 3}, AZ distribution {'ap-northeast-2a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-backend` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling … |
| `resilience.replicas-same-node.prod-app-z-backend/deployment/app-z-frontend` | high |  | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling … |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.28, 24 h or the pod's life 0.28: throttled through the day |
| `resources.cpu-throttling.prod-app-s/deploy/app-s-frontend:frontend` | high |  | ["pod app-s-frontend-6d7ff4dcdb-wjjxj: throttling ratio now 0.00, 24 h or the pod's life 0.46: throttled through the day; no 5-minute value, under 0.01 now", "pod app-s-frontend-6d7ff4dcdb-h7hpl: throttling ratio now … |
| `resources.memory-limit-near-p95.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | high |  | pod app-z-embedding-server-8445d87f5-dwqrx: 7d memory working set p95 / limit = 0.94 |
| `resources.oomkilled-repeated.prod-app-t/deploy/app-t-ai:ai` | high |  | kernel log not read in this mode. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods (none of those pods is running now). cAdvisor counter 0. Running now: app-t-ai-5469577cf8-7nwnb … |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-11-05T08:21:29Z (1.7 days ago), 2 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | high |  | 4 NetworkPolicies (['app-ab-prod', 'prod-app-r', 'prod-app-t', 'prod-app-x']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | high |  | Container neo4j env ['NEO4J_AUTH'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/tts-proxy` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-aa/data-app-aa-mysql-0` | high |  | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-aa-mysql'], StorageClass gp3 |

(consecutive-run counts need diff.json; none for this snapshot)

## 3. Changes since the previous run of this mode

No earlier daily snapshot to compare with.

### 3-1. Why things changed

(not written this run)

## 4. Detail per area

(daily mode: no per-area detail; see section 2 and `report.md`)

## 5. Absence list

| Finding | Status | Severity | Why it should exist | Proposal |
|---|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |
| `observability.no-slo.cluster` | warn | high | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `observability.no-event-retention.cluster` | fail | medium | Kubernetes events are kept for only one hour by default. FailedScheduling, OOMKilling and Unhealthy from the night are gone by morning. The most undervalued material is lost. | Ship events to Loki or Elasticsearch with kubernetes-event-exporter. Alternatively, the promtail/alloy event source if Loki exists, or `[INPUT] kubernetes_events` with fluent-bit (detection … |
| `security.no-certificate-manager.cluster` | warn | medium | When TLS certificate renewal is manual, services keep going down from expiry. cert-manager (or ACM plus ALB on EKS) automates renewal. On EKS, ALBs using ACM certificates work without cert-manager … | Install cert-manager, or if ACM is in use, suppress this check in config.yaml with a reason. |

Expected families missing (inventory): backup, certificates, event-retention, slo.

## 6. Suppressed, tool missing, not collected

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in daily mode 86: `resources.krr-recommendation`, `controlplane.scheduler-unschedulable`, `controlplane.webhook-call-failures`, `controlplane.controller-error-repeat`, `controlplane.apiserver-slow-traces`, `controlplane.authenticator-failures`, `node.kernel-oom-node-level`, `node.kernel-lockup`, `node.kernel-io-fs-errors`, `node.kernel-nic-events`, `node.conntrack-table-full`, `node.kernel-net-mem-pressure`, `node.cgroup-v1`, `node.sysctl-tuning`, `node.cri-not-ready`, `node.cri-exited-containers`, `node.pod-logs-large`, `node.pod-dir-large`, `node.service-restarts`, `node.reboot-required`, `node.os-updates-pending`, `node.kubelet-reserved-missing`, `node.kubelet-eviction-memory-missing`, `node.clock-unsynced-os`, `node.zombie-processes`, `node.os-not-collected`, `observability.unclassified-errors`, `cost.idle-compute-high`, `cost.request-waste`, `cost.unused-eip`, `cost.idle-load-balancer`, `security.eks-secrets-encryption-off`, `security.imds-hop-limit`, `security.polaris-security-danger`, `storage.ebs-unattached`, `storage.ebs-gp2-volumes`, `storage.ebs-unencrypted`, `hygiene.polaris-reliability-danger`, `hygiene.deprecated-api`, `hygiene.eks-upgrade-insight`, `hygiene.helm-release-not-deployed`, `hygiene.helm-release-stale`, `traffic.lb-idle-timeout-long`, `traffic.alb-target-type-instance`, `resources.jvm-heap-vs-limit`, `node.kubelet-api-qps-low`, `traffic.alb-elb-5xx`, `traffic.alb-unhealthy-targets`, `traffic.alb-deregistration-vs-grace`, `traffic.alb-protection-off`, `resilience.backup-same-node`, `resilience.prod-db-without-backup-cronjob`, `security.plaintext-configmap-secret`, `node.docker-and-containerd`, `node.container-writable-layer-large`, `node.large-images`, `eks.audit-log-off`, `eks.public-endpoint-open`, `eks.addon-outdated`, `eks.node-os-skew`, `eks.ssm-unregistered`, `eks.extended-support`, `eks.no-backup-policy`, `eks.acm-certificate-expiring`, `eks.service-quota-near-limit`, `storage.ebs-volume-io-saturated`, `eks.security-group-open-to-world`, `eks.nodegroup-ami-old`, `albctl.target-group-without-tgb`, `ecr.scan-disabled`, `ecr.tag-mutable-prod`, `ecr.no-lifecycle-policy`, `ecr.stale-storage`, `ecr.dockerhub-dependency`, `ecr.pull-failures`, `ecr.no-replication`, `ecr.untagged-images`, `kubeproxy.node-cmd-unavailable`, `vpccni.node-ip-exhaustion`, `vpccni.no-available-ip`, `vpccni.max-pods-exceeds-ip-capacity`, `vpccni.prefix-delegation-off`, `vpccni.subnet-ips-low`, `vpccni.ec2-api-errors`, `vpccni.metrics-unreadable`, `vpccni.external-snat-off-with-private-routes`
- Skipped or errored 6: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `traffic.ingress-5xx-ratio` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (41)), `traffic.ingress-p95-latency` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (41)), `traffic.db-exposed` (skip: nothing to judge: load balancer security groups not read (elasticloadbalancing:Describe*, ec2:DescribeSecurityGroups)), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing)
- Judged in part 0 (some targets lacked what the rule needs; those are not judged, not passed): none
- Query returned no series 4 (every metric name the query reads has series, so nothing happened; a name with no series would be a skip): `observability.alertmanager-notification-failed`, `observability.scrape-targets-down`, `controlplane.apiserver-401-rate`, `scaling.pod-pending-long`

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 |  | node-os (a daily run does not collect node-os); kubelet-configz (a daily run does not collect kubelet-config); krr (a daily run does not collect workload-tools); polaris (a daily run does not collect workload-tools); pluto (a daily run does not collect workload-tools); kubent (a daily run does not collect workload-tools); helm-list (a daily run does not collect helm-releases) |
| eks-platform | 29 |  | nodegroup (a daily run does not collect cloud-account); addon-versions (a daily run does not collect cloud-account); cluster-versions (a daily run does not collect cloud-account); insights (a daily run does not collect cloud-account); subnets (a daily run does not collect cloud-account); route-tables (a daily run does not collect cloud-account); ssm-instances (a daily run does not collect cloud-account); cluster-security-groups (a daily run does not collect cloud-account); controlplane-logs (a daily run does not collect control-plane-logs); kubelet-journal (a daily run does not collect node-os); containerd-journal (a daily run does not collect node-os); dlm-policies (a daily run does not collect cloud-account); backup-plans (a daily run does not collect cloud-account); alb-metrics (a daily run does not collect cloud-account); ec2-volumes (a daily run does not collect cloud-account); ec2-volumes-available (a daily run does not collect cloud-account); ec2-snapshots-30d (a daily run does not collect cloud-account); ec2-instances-imds (a daily run does not collect cloud-account); pod-identity-associations (a daily run does not collect cloud-account); ec2-addresses (a daily run does not collect cloud-account); ec2-nat-gateways (a daily run does not collect cloud-account); ec2-spot-prices (a daily run does not collect cloud-account); pricing-ondemand (a daily run does not collect cloud-account); ce-cost-30d (a daily run does not collect cloud-account); acm-certificates (a daily run does not collect cloud-account); service-quotas (a daily run does not collect cloud-account); quota-usage (a daily run does not collect cloud-account); ec2-root-volumes (a daily run does not collect cloud-account); ebs-volume-metrics (a daily run does not collect cloud-account) |
| actions-runner-controller | 0 |  | no collect.yaml (collector not implemented) |
| alb-controller | 1 |  |  |
| alertmanager | 4 |  |  |
| argocd | 3 |  |  |
| coredns | 1 |  |  |
| ebs-csi | 1 |  |  |
| ecr | 5 |  | registry (a daily run does not collect cloud-account); scanning-configuration (a daily run does not collect cloud-account); pull-through-cache (a daily run does not collect cloud-account); images (a daily run does not collect cloud-account); lifecycle-policy (a daily run does not collect cloud-account) |
| external-dns | 0 |  | no collect.yaml (collector not implemented) |
| external-secrets | 1 |  |  |
| grafana | 5 |  | datasources (grafana_api_token missing); dashboards (grafana_api_token missing); dashboards-json (grafana_api_token missing) |
| karpenter | 1 |  |  |
| keda | 2 |  | operator-metrics (container arg --enable-prometheus-metrics=false: no metrics is expected) |
| kube-proxy | 2 |  | proxy-mode (a daily run does not collect node-os) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| loki | 9 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| promtail | 0 |  | no collect.yaml (collector not implemented) |
| victoria-metrics | 0 |  | no collect.yaml (collector not implemented) |
| vpc-cni | 3 |  | ipamd-metrics (a daily run does not collect node-os); ipamd-log (a daily run does not collect node-os); instance-type-network (a daily run does not collect cloud-account) |

Kinds this cluster does not serve (7; a check that needs one of them is skipped, not passed): `certificates.cert-manager.io`, `clusterissuers.cert-manager.io`, `horizontalrunnerautoscalers.actions.summerwind.dev`, `issuers.cert-manager.io`, `runnerdeployments.actions.summerwind.dev`, `volumesnapshotclasses.snapshot.storage.k8s.io`, `volumesnapshots.snapshot.storage.k8s.io`

701 commands, 300.7 s. Failed steps: 0

Commands that failed inside a step that still succeeded (run.log): 26: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.bitnami/kafka` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.bitnami/mysql` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.ecr-app-ab-postgresql-pgvector` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.app-v` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `grafana.self-metrics.kube-prometheus-stack-grafana-7c9959564d-w8qx7.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.kubelet-journal.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.kubelet-journal.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.ip-10-0-1-117.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `eks-platform.containerd-journal.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `kube-proxy.proxy-mode.ip-10-0-2-60.ap-northeast-2.compute.internal` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

### 7-2. Checks evaluated

367 checks: disabled 3, done 270, llm 2, not-collected 86, skip 6. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.1, 23 files, 23380 lines scanned (components: actions-runner-controller, alb-controller, argocd, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 24.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| external-secrets.provider-error | external-secrets | security | high | warn | 62 | 2026-11-06T17:31:20Z , 2026-11-07T01:34:43Z |  |
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-06T08:49:38Z , 2026-11-06T08:49:38Z |  |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-06T20:55:55Z , 2026-11-07T01:36:03Z |  |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 31 | 2026-11-06T01:43:11Z , 2026-11-06T10:09:11Z |  |
| karpenter.spot-interruption | karpenter | resilience | low | info | 2 | 2026-11-06T02:44:15Z , 2026-11-06T09:09:11Z |  |

| Normalized message | Count | Files |
|---|---|---|
| (none) | | |

### 7-4. Raw files the LLM read directly

(not written this run)

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `events.tracked-warning-reasons.FreeDiskSpaceFailed` | fail | high | kubelet image GC could not free space. Disk is full of in-use images and logs. 1338 occurrences total (1 events, trend over 1 snapshots [1338], flat), first 2026-10-23T01:20:23Z last 2026-11-07T01:32:11Z. Top objects: ['Node/ip-10-0-1-139.ap-northeast-2.compute.internal'] |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.loki-oomkilled.cluster` | fail | high | Loki pods [('loki-stack-0', 1, 'OOMKilled', '2026-10-25T00:15:41Z')]. Storage {'tmp': 'emptyDir', 'config': 'secret', 'storage': 'emptyDir'}, memory RSS 289MB |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e: upstream end of life 2026-02-28, 252 days past |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resilience.prod-concentration.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | high | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default, spot) holds prod pods 23/45 (0.51), 18 workloads: ['app-ab-prod/app-ab-backend', 'app-ab-prod/app-ab-frontend', 'prod-app-s/app-s-admin', 'prod-app-s/app-s-api', 'prod-app-s/app-s-backend', 'prod-app-s/app-s-frontend' … |
| `resilience.replicas-same-node.prod-app-w/deployment/app-w` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-ai` | fail | high | replicas 3 (Running 3), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 3}, AZ distribution {'ap-northeast-2a': 3}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-backend` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.replicas-same-node.prod-app-z-backend/deployment/app-z-frontend` | fail | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 2}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity preferred, nodes eligible under scheduling constraints 4 |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.28, 24 h or the pod's life 0.28: throttled through the day |
| `resources.cpu-throttling.prod-app-s/deploy/app-s-frontend:frontend` | fail | high | ["pod app-s-frontend-6d7ff4dcdb-wjjxj: throttling ratio now 0.00, 24 h or the pod's life 0.46: throttled through the day; no 5-minute value, under 0.01 now", "pod app-s-frontend-6d7ff4dcdb-h7hpl: throttling ratio now 0.38, 24 h or the pod's life 0.42: throttled through the day", "pod … |
| `resources.memory-limit-near-p95.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | fail | high | pod app-z-embedding-server-8445d87f5-dwqrx: 7d memory working set p95 / limit = 0.94 |
| `resources.oomkilled-repeated.prod-app-t/deploy/app-t-ai:ai` | fail | high | kernel log not read in this mode. Prometheus: 3 pods ended by OOM in 7 days, 3 already replaced, 13 restarts in those pods (none of those pods is running now). cAdvisor counter 0. Running now: app-t-ai-5469577cf8-7nwnb (created 2026-11-06T08:26:51Z, 0 restarts of this container since) |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-11-05T08:21:29Z (1.7 days ago), 2 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | fail | high | 4 NetworkPolicies (['app-ab-prod', 'prod-app-r', 'prod-app-t', 'prod-app-x']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | high | Container neo4j env ['NEO4J_AUTH'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/tts-proxy` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `storage.pvc-usage-high.dev-app-aa/data-app-aa-mysql-0` | fail | high | Usage 0.902 (capacity 9.7GB, inodes 0.0), growth 0.0GB/day, None days to full, workloads ['statefulset/app-aa-mysql'], StorageClass gp3 |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 1 occurrences total (1 events, trend over 1 snapshots [1], flat), first 2026-11-07T00:48:24Z last 2026-11-07T00:48:24Z. Top objects: ['Pod/prod-app-s/app-s-backend-7c46f75bf6-ljlnl'] |
| `events.tracked-warning-reasons.UpdateFailed` | warn | high | Operator reconcile failure (ExternalSecret etc.). 2711 occurrences total (1 events, trend over 1 snapshots [2711], flat), first 2026-10-08T12:31:38Z last 2026-11-07T01:18:03Z. Top objects: ['ExternalSecret/database/mysql-app-v-secret'] |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.external-secrets.provider-error` | warn | high | 62 occurrences (2026-11-06T17:31:20Z ~ 2026-11-07T01:34:43Z), thresholds warn 1/fail 10. Files: ['logs/pods/external-secrets/external-secrets_external-secrets.log']. Samples: [] |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-06T08:49:38Z ~ 2026-11-06T08:49:38Z), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: [] |
| `node.disk-usage.10.0.1.139:9100:/` | warn | high | usage 0.85 |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `observability.no-slo.cluster` | warn | high | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] known issue #15 |
| `observability.no-symptom-alerts.cluster` | warn | high | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 14. Symptom ratio 0.0. Symptom rules: [] |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.655 (limit 1536Mi), active series 165690, Prometheus container last terminated OOMKilled True (2026-11-05T08:21:29Z), restarts 2, OOMKilled containers in the monitoring namespace ['loki-stack-0/loki', 'prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7 … |
| `resilience.n-plus-one.cluster` | warn | high | Allocatable without the largest node ip-10-0-1-139.ap-northeast-2.compute.internal (3.92 cores, 29.8GB): CPU 15.45 cores vs total requests 11.51 (OK), memory 46.3GB vs 45.7GB (OK). Pods on that node 34 (prod 23). Pods that fit on no other node []. Pools short of room: 32 pods limited to … |
| `resilience.replicas-same-node.prod-app-x/deployment/app-x-api` | warn | high | replicas 2 (Running 2), node distribution {'ip-10-0-1-139.ap-northeast-2.compute.internal': 1, 'ip-10-0-1-137.ap-northeast-2.compute.internal': 1}, AZ distribution {'ap-northeast-2a': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 4 |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.dev-app-s/deploy/app-s-frontend:frontend` | warn | high | ["pod app-s-frontend-6578574c-qx5nj: throttling ratio now 0.00, 24 h or the pod's life 0.23: throttled through the day, below the fail line; no 5-minute value, under 0.01 now", "pod app-s-frontend-999976975-nf4rv: throttling ratio now 0.12, 24 h or the pod's life 0.11: throttled through the day … |
| `resources.cpu-throttling.dev-app-v/deploy/app-v-frontend:frontend` | warn | high | ["pod app-v-frontend-f7b9d96d4-dn7qv: throttling ratio now 0.00, 24 h or the pod's life 0.23: throttled through the day, below the fail line; no 5-minute value, under 0.01 now", "pod app-v-frontend-f7b9d96d4-jl226: throttling ratio now 0.00, 24 h or the pod's life 0.21: throttled through the day … |
| `resources.cpu-throttling.dev-app-y/deploy/app-y-frontend:frontend` | warn | high | pod app-y-frontend-7f6d6dc65b-lnmq4: throttling ratio now 0.16, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | kernel log not read in this mode. Prometheus: 1 pod ended by OOM in 7 days, 1 restarts in those pods. cAdvisor counter 1. Running now: prometheus-kube-prometheus-stack-prometheus-0 (created 2026-09-08T12:47:49Z, 2 restarts of this container since) |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | warn | high | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (7.7 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `resources.oomkilled.monitoring/sts/loki-stack:loki` | warn | high | pod loki-stack-0: last termination reason OOMKilled, finished at 2026-10-25T00:15:41Z (13.1 days ago), 1 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 13/13 (prod 9) |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-2a', 'gp3-2c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-2a', 'gp3-2c'] |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 31963 / errors 2711 (ratio 0.0782), sync failures 2711/73134, reconcile errors 2711, ExternalSecrets not Ready ['database/externalsecret/mysql-app-v-secret'] (oldest refresh 7796.6 hours ago) |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | fail | medium | responses per datasource (cumulative since start) [('Loki(loki)', 2614, {'101': 4, '200': 2275, '400': 6, '429': 329}), ('Prometheus(prometheus)', 1535, {'200': 1349, '301': 186}), ('VictoriaMetrics_onprem(prometheus)', 142, {'200': 142})], error rate 1% or more ['Loki(loki)'] (max 0.1259), Grafana … |
| `hygiene.mutable-image-tag.prod-app-z-backend/deployment/tts-proxy:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 59.5 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 59.5 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20157 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20157 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 147 pods Running for over 1h, 83 are absent from Loki pod labels (ratio 0.565). Nodes with every pod missing: []. By namespace: {'kube-system': 23, 'monitoring': 22, 'prod-app-z-backend': 5, 'keda': 3, 'middleware': 3, 'prod-app-t': 3, 'prod-app-s': 3, 'argocd': 2, 'dev-app-s': 2, 'dev-app-y' … |
| `observability.loki-retention-unbounded.cluster` | fail | medium | Loki 2.6.1, retention_period 31d, retention_enabled false |
| `observability.no-event-retention.cluster` | fail | medium | no component of family event-retention in inventory.components |
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
| `resources.besteffort-in-prod.prod-app-z-backend/deploy/tts-proxy` | fail | medium | pod tts-proxy-7b6db97b69-4bbjf: QoS BestEffort (neither request nor limit) |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-backend:backend` | fail | medium | pod app-z-backend-78679bf4b-lhhg4: 7d CPU p95 0.003 cores / request 0.50 cores = 0.01 |
| `resources.large-request-binpacking.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | fail | medium | ['pod app-z-embedding-server-8445d87f5-dwqrx: request is 58% of the median node allocatable', 'pod app-z-embedding-server-8445d87f5-sbzpj: request is 58% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-z-backend/sts/app-z-neo4j:neo4j` | fail | medium | pod app-z-neo4j-0: request is 58% of the median node allocatable |
| `resources.no-memory-limit.prod-app-z-backend/tts-proxy` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-request-usage-gap.ip-10-0-1-117.ap-northeast-2.compute.internal` | fail | medium | CPU requests/allocatable 0.96, usage/allocatable 7d p95 0.09 (5m instant 0.09) |
| `resources.node-request-usage-gap.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | medium | CPU requests/allocatable 0.92, usage/allocatable 7d p95 0.09 (5m instant 0.05) |
| `resources.node-request-usage-gap.ip-10-0-1-245.ap-northeast-2.compute.internal` | fail | medium | CPU requests/allocatable 0.90, usage/allocatable 7d p95 0.08 (5m instant 0.01) |
| `resources.node-request-usage-gap.ip-10-0-2-60.ap-northeast-2.compute.internal` | fail | medium | CPU requests/allocatable 0.99, usage/allocatable 7d p95 0.06 (5m instant 0.06) |
| `scaling.hpa-flapping.prod-app-z-backend/hpa/keda-hpa-app-z-file-worker` | fail | medium | 77 desired changes over 7 days |
| `scaling.karpenter-expired-not-replaced.default-n44bh` | fail | medium | NodeClaim default-n44bh → node ip-10-0-1-139.ap-northeast-2.compute.internal (r8gd.xlarge spot): age 1056.5h, 336.5h past expireAfter 720.0h. Blocking reason (DisruptionBlocked): {'do-not-disrupt pods': 22556}. do-not-disrupt pods on this node 2: prod-app-s/app-s-admin-57f5fcc58d-khsh5 … |
| `security.externalsecret-not-ready.database/mysql-app-v-secret` | fail | medium | Ready False (SecretSyncedError): could not get secret data from provider |
| `security.networkpolicy-coverage.cluster` | fail | medium | 18 of 22 user namespaces have no NetworkPolicy, of which production ['prod-app-w', 'prod-app-s', 'prod-app-y', 'prod-app-z-backend', 'prod-app-v']; with: ['app-ab-prod', 'prod-app-r', 'prod-app-t', 'prod-app-x'] |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days None None, prod PVCs 8 |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.burst-tenant-unbounded.prod-app-z-backend` | fail | medium | prod-app-z-backend (prod): 7d CPU median 0.011 cores, p95 0.904 cores, max 3.931 cores = 344.0x the median. No quota, shares nodes with prod True, nodes {'ip-10-0-1-139.ap-northeast-2.compute.internal': 4, 'ip-10-0-2-135.ap-northeast-2.compute.internal': 3 … |
| `tenancy.prod-boundary-missing.prod-app-s` | fail | medium | prod-app-s: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-v` | fail | medium | prod-app-v: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-w` | fail | medium | prod-app-w: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-y` | fail | medium | prod-app-y: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-z-backend` | fail | medium | prod-app-z-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.app-ab-prod` | fail | medium | app-ab-prod (prod): no ResourceQuota. Pods 3, CPU requests total 0.25 cores, memory requests total 0.94GB, 7d CPU p95 0.023 cores (cluster share 0.01), memory p95 0.5GB, 7d max/median 2.0x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-r` | fail | medium | prod-app-r (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.006 cores (cluster share 0.003), memory p95 0.64GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-s` | fail | medium | prod-app-s (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 0.112 cores (cluster share 0.051), memory p95 1.88GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-t` | fail | medium | prod-app-t (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 0.009 cores (cluster share 0.004), memory p95 0.93GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-v` | fail | medium | prod-app-v (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.024 cores (cluster share 0.011), memory p95 1.01GB, 7d max/median 4.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-w` | fail | medium | prod-app-w (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 0.004 cores (cluster share 0.002), memory p95 0.21GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-x` | fail | medium | prod-app-x (prod): no ResourceQuota. Pods 3, CPU requests total 1.1 cores, memory requests total 2.25GB, 7d CPU p95 0.007 cores (cluster share 0.003), memory p95 0.52GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-y` | fail | medium | prod-app-y (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 0.037 cores (cluster share 0.017), memory p95 3.43GB, 7d max/median 1.2x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-z-backend` | fail | medium | prod-app-z-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 0.904 cores (cluster share 0.41), memory p95 11.89GB, 7d max/median 344.0x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.tenant-without-limitrange.prod-app-z-backend` | fail | medium | prod-app-z-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 0.904 cores, memory p95 11.89GB |
| `traffic.shared-alb-group.alb-group/app-u-prod-lb` | fail | medium | ALB group app-u-prod-lb: 41 ingresses, 48 hosts, 16 namespaces ['app-ab-prod', 'argocd', 'dev-app-aa', 'dev-app-s', 'dev-app-v', 'dev-app-y', 'middleware', 'monitoring', 'prod-app-r', 'prod-app-s', 'prod-app-t', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend'], kinds … |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 41, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 1 lines, exec.enabled False, URL https://deploy.lab-k.example |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version … |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.503, queries per second 75.8, NXDOMAIN share of queries forwarded upstream 0.442 (upstreams ['10.0.0.2:53']), pods with default ndots (5) 154, autopath False, cache hit ratio 0.9237 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.app-u.ai/role` | warn | medium | Label app-u.ai/role: 34 workloads (production 9) depend on it via nodeSelector/affinity, present on 5/9 nodes — e.g. ['argocd/deployment/argocd-applicationset-controller', 'argocd/deployment/argocd-dex-server', 'argocd/deployment/argocd-notifications-controller'] and 31 more |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 39 workloads (production 26) depend on it via nodeSelector/affinity, present on 4/9 nodes — e.g. ['dev-app-s/deployment/app-s-admin', 'dev-app-s/deployment/app-s-api', 'dev-app-s/deployment/app-s-backend'] and 36 more |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 30.9s (8787 pods), node termination average 14.7s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-y/scaledobject/app-y-ai-kafka-lag', 'prod-app-z-backend/scaledobject/app-z-file-worker', 'prod-app-z-backend/scaledobject/app-z-graph-worker'], trigger types {'kafka': 4, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-06T20:55:55Z ~ 2026-11-07T01:36:03Z), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: [] |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 31 occurrences (2026-11-06T01:43:11Z ~ 2026-11-06T10:09:11Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: [] |
| `loki.memory-pressure.monitoring/statefulset/loki-stack` | warn | medium | RSS 289MiB / limit 512Mi = 0.565, in-memory streams 54, last termination OOMKilled True(2026-10-25T00:15:41Z), restarts 1, storage emptyDir |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 1 5xx out of 6899928 requests since start (by route {'loki_api_v1_series': 1}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 11783, rejected {} |
| `node.network-errors.10.0.1.139:9100:eth0` | warn | medium | Node 10.0.1.139:9100 device eth0: 187 RX+TX errors in 24h |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerFailedReload', 'AlertmanagerMembersInconsistent', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown' … |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-mysql:mysql` | warn | medium | dev-app-aa/statefulset/app-aa-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-aa/statefulset/app-aa-postgres:postgres` | warn | medium | dev-app-aa/statefulset/app-aa-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | medium | dev-app-s/statefulset/app-s-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql` | warn | medium | dev-app-v/statefulset/app-v-backend-dev-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.dev-app-y/statefulset/app-y-backend-mysql:mysql` | warn | medium | dev-app-y/statefulset/app-y-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` | warn | medium | monitoring/statefulset/loki-stack container loki: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 111, 'system-cluster-critical': 9, 'system-node-critical': 27}, prod pods without a class 45 of 45, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.recreate-strategy-serving.monitoring/deployment/vmauth` | warn | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master` | warn | medium | Containers whose command is sh -c ['redis', 'metrics'], no preStop, terminationGracePeriodSeconds 30 |
| `resources.cpu-request-overprovisioned.app-ab-prod/deploy/app-ab-backend:backend` | warn | medium | pod app-ab-backend-6dd8fcbf96-nshrh: 7d CPU p95 0.014 cores / request 0.10 cores = 0.14 |
| `resources.cpu-request-overprovisioned.app-ab-prod/sts/app-ab-backend-postgresql:postgresql` | warn | medium | pod app-ab-backend-postgresql-0: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07; database-like: keep the request |
| `resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | medium | pod argocd-repo-server-d487895cc-bth22: 7d CPU p95 0.003 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller` | warn | medium | pod argocd-application-controller-0: 7d CPU p95 0.036 cores / request 0.20 cores = 0.18 |
| `resources.cpu-request-overprovisioned.dev-app-aa/deploy/app-aa-backend:backend` | warn | medium | pod app-aa-backend-57fdd58475-5dn47: 7d CPU p95 0.001 cores / request 0.20 cores = 0.00 |
| `resources.cpu-request-overprovisioned.dev-app-aa/sts/app-aa-mysql:mysql` | warn | medium | pod app-aa-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-aa/sts/app-aa-postgres:postgres` | warn | medium | pod app-aa-postgres-0: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-api:api` | warn | medium | pod app-s-api-575d497d9b-5ttcv: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend` | warn | medium | pod app-s-backend-76775dbdd-ttz69: 7d CPU p95 0.017 cores / request 0.10 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-s/sts/app-s-backend-mysql:mysql` | warn | medium | pod app-s-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-v/deploy/app-v-backend:backend` | warn | medium | pod app-v-backend-7cfd8c975-b9p48: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13 |
| `resources.cpu-request-overprovisioned.dev-app-v/sts/app-v-backend-dev-mysql:mysql` | warn | medium | pod app-v-backend-dev-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.dev-app-y/deploy/app-y-ai:ai` | warn | medium | pod app-y-ai-7cdbdc7544-szzcl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.dev-app-y/deploy/app-y-backend:backend` | warn | medium | pod app-y-backend-69dbdf4f65-9x6jc: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11 |
| `resources.cpu-request-overprovisioned.dev-app-y/sts/app-y-backend-mysql:mysql` | warn | medium | pod app-y-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.10 cores = 0.09; database-like: keep the request |
| `resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | medium | ['pod karpenter-9769889bd-pkxd2: 7d CPU p95 0.020 cores / request 0.20 cores = 0.10', 'pod karpenter-9769889bd-nphgs: 7d CPU p95 0.000 cores / request 0.20 cores = 0.00'] |
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
| `resources.cpu-request-overprovisioned.prod-app-r/sts/app-r-postgresql:postgresql` | warn | medium | pod app-r-postgresql-0: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-s/sts/app-s-backend-mysql:mysql` | warn | medium | pod app-s-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql` | warn | medium | pod app-t-backend-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-v/sts/app-v-backend-prod-mysql:mysql` | warn | medium | pod app-v-backend-prod-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend` | warn | medium | ['pod app-y-backend-596479b6f8-cx44t: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod app-y-backend-596479b6f8-nv9j2: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.prod-app-y/sts/app-y-backend-mysql:mysql` | warn | medium | pod app-y-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | warn | medium | pod app-z-embedding-server-8445d87f5-dwqrx: 7d CPU p95 0.140 cores / request 0.50 cores = 0.28 |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend` | warn | medium | ['pod app-z-frontend-6d58bbfcfc-nfk9x: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod app-z-frontend-6d58bbfcfc-2qgs6: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j` | warn | medium | pod app-z-neo4j-0: 7d CPU p95 0.005 cores / request 0.50 cores = 0.01; database-like: keep the request |
| `resources.node-memory-request-usage-gap.ip-10-0-1-241.ap-northeast-2.compute.internal` | warn | medium | memory requests/allocatable 0.66, working set/allocatable 7d p95 0.36 (instant 0.35) |
| `resources.node-memory-request-usage-gap.ip-10-0-2-135.ap-northeast-2.compute.internal` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.44 (instant 0.42) |
| `resources.node-memory-request-usage-gap.ip-10-0-2-218.ap-northeast-2.compute.internal` | warn | medium | memory requests/allocatable 0.71, working set/allocatable 7d p95 0.23 (instant 0.23) |
| `resources.node-request-usage-gap.ip-10-0-1-137.ap-northeast-2.compute.internal` | warn | medium | CPU requests/allocatable 0.80, usage/allocatable 7d p95 0.00 (5m instant 0.00) |
| `resources.node-request-usage-gap.ip-10-0-2-135.ap-northeast-2.compute.internal` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.05 (5m instant 0.04) |
| `scaling.hpa-flapping.dev-app-s/hpa/app-s-frontend` | warn | medium | 44 desired changes over 7 days |
| `scaling.hpa-flapping.prod-app-z-backend/hpa/keda-hpa-app-z-graph-worker` | warn | medium | 34 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['app-ab-prod', 'prod-app-r', 'prod-app-s', 'prod-app-t', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend']. Share of containers allowing root 0.61 (29 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 86/92, of which 30 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-w/deployment/app-w', 'prod-app-t/deployment/app-t-ai', 'prod-app-t/deployment/app-t-backend', 'prod-app-t/deployment/app-t-studio', 'prod-app-t/deployment/app-t-web' … |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-v/data-app-v-backend-prod-mysql-0', 'prod-app-s/data-app-s-backend-mysql-0', 'prod-app-z-backend/data-app-z-neo4j-0', 'app-ab-prod/data-app-ab-backend-postgresql-0', 'prod-app-r/data-app-r-postgresql-0' … |
| `tenancy.prod-boundary-missing.app-ab-prod` | warn | medium | app-ab-prod: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-r` | warn | medium | prod-app-r: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-t` | warn | medium | prod-app-t: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-boundary-missing.prod-app-x` | warn | medium | prod-app-x: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 14 |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 0, CPU requests total 0.0 cores, memory requests total 0.0GB, 7d CPU p95 0.55 cores (cluster share 0.25), memory p95 1.35GB, 7d max/median Nonex. Tenants in this cluster 14, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-aa` | warn | medium | dev-app-aa (dev): no ResourceQuota. Pods 4, CPU requests total 0.55 cores, memory requests total 1.88GB, 7d CPU p95 0.017 cores (cluster share 0.008), memory p95 0.85GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-s` | warn | medium | dev-app-s (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 0.052 cores (cluster share 0.024), memory p95 0.86GB, 7d max/median 1.4x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-v` | warn | medium | dev-app-v (dev): no ResourceQuota. Pods 4, CPU requests total 0.3 cores, memory requests total 1.0GB, 7d CPU p95 0.024 cores (cluster share 0.011), memory p95 0.95GB, 7d max/median 1.7x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.prod-without-quota.dev-app-y` | warn | medium | dev-app-y (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 2.25GB, 7d CPU p95 0.035 cores (cluster share 0.016), memory p95 1.4GB, 7d max/median 1.1x. Tenants in this cluster 14, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.ip-10-0-1-117.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-1-117.ap-northeast-2.compute.internal (pool system_core-20251217040546303900000001): tenant kinds ['dev', 'prod'], namespaces ['kube-system', 'keda', 'monitoring', 'argocd', 'dev-app-y', 'dev-app-aa'] and 3 more. Memory limit total 11.6GB / allocatable 6.9GB = 1.68x, request total … |
| `tenancy.shared-node-limit-overcommit.ip-10-0-1-139.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default): tenant kinds ['dev', 'prod'], namespaces ['prod-app-y', 'dev-app-y', 'prod-app-s', 'prod-app-z-backend', 'dev-app-s', 'prod-app-v'] and 6 more. Memory limit total 47.0GB / allocatable 29.8GB = 1.58x, request total 18.9GB, containers … |
| `tenancy.shared-node-limit-overcommit.ip-10-0-2-218.ap-northeast-2.compute.internal` | warn | medium | Node ip-10-0-2-218.ap-northeast-2.compute.internal (pool system-ondemand): tenant kinds ['dev', 'other', 'prod'], namespaces ['monitoring', 'argocd', 'dev-app-aa', 'keda', 'kube-system', 'middleware'] and 2 more. Memory limit total 5.7GB / allocatable 3.2GB = 1.79x, request total 2.0GB, containers … |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.lab-k.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-s/app-s-admin` | warn | medium | ingress ['admin-dev.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-v/app-v-admin-frontend` | warn | medium | ingress ['admin-dev.lab-n.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-y/app-y-admin` | warn | medium | ingress ['admin-dev.lab-m.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-s/app-s-admin` | warn | medium | ingress ['canary-admin.lab-l.example', 'admin.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-v/app-v-admin-frontend` | warn | medium | ingress ['admin.lab-n.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-y/app-y-admin` | warn | medium | ingress ['admin.lab-m.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 113 (0.009), without one in prod 35. emptyDirs without sizeLimit 22 (prod: ['app-ab-prod/statefulset/app-ab-backend-postgresql', 'prod-app-r/deployment/app-r-backend', 'prod-app-r/statefulset/app-r-postgresql' … |
| `hygiene.old-replicasets.cluster` | fail | low | Of 428 ReplicaSets, 362 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 62, '3': 6} |
| `scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-backend` | fail | low | HPA prod-app-z-backend/app-z-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 21.6 days ago |
| `scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-frontend` | fail | low | HPA prod-app-z-backend/app-z-frontend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 1% / target 70%, metrics ['cpu'], last scale 88.8 days ago |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `tenancy.dev-shares-prod-nodes.ip-10-0-1-117.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-1-117.ap-northeast-2.compute.internal (pool system_core-20251217040546303900000001): prod pods 2 (['app-ab-prod', 'prod-app-y']) together with dev pods 2 (['dev-app-aa', 'dev-app-y']). Memory limit total/allocatable 1.68, CPU limit total/allocatable 3.37, containers without a memory … |
| `tenancy.dev-shares-prod-nodes.ip-10-0-1-139.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-1-139.ap-northeast-2.compute.internal (pool default): prod pods 23 (['app-ab-prod', 'prod-app-s', 'prod-app-v', 'prod-app-w', 'prod-app-x', 'prod-app-y', 'prod-app-z-backend']) together with dev pods 10 (['dev-app-aa', 'dev-app-s', 'dev-app-v', 'dev-app-y']). Memory limit … |
| `tenancy.dev-shares-prod-nodes.ip-10-0-2-218.ap-northeast-2.compute.internal` | fail | low | Node ip-10-0-2-218.ap-northeast-2.compute.internal (pool system-ondemand): prod pods 2 (['prod-app-t', 'prod-app-x']) together with dev pods 1 (['dev-app-aa']). Memory limit total/allocatable 1.79, CPU limit total/allocatable 1.81, containers without a memory limit 1 |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 242614, top [['Elastic Load Balancing v2/DescribeTargetHealth', 76055], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 43347], ['EC2/DescribeInstances', 38801], ['EC2/DescribeSecurityGroups', 24999], ['Elastic Load Balancing v2/RegisterTargets', 11793]] … |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster disabled (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 9, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 9, apps whose targetRevision is a branch or HEAD 9 ['argocd/application/app-w-prod', 'argocd/application/app-t-prod', 'argocd/application/app-x-prod', 'argocd/application/app-s-prod', 'argocd/application/app-y-prod', 'argocd/application/app-ab-prod' … |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.5, cluster IPv6 False, queries per second 75.8. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-node.ip-10-0-1-137.ap-northeast-2.compute.internal` | warn | low | Node ip-10-0-1-137.ap-northeast-2.compute.internal (r8gd.medium, pool default): CPU p95 0.00429569315734247, memory p95 0.043260228361303214, None USD/month |
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
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 822 packets (sum over nodes), services with externalTrafficPolicy Local 0, Services with a Local traffic policy and no endpoint on the node (max over nodes) 0 |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied False(compactor 1.0) |
| `observability.alert-metric-without-dashboard.grafana` | warn | low | 28 dashboards (196 panel metrics) — 132 of 173 alert-rule metrics have no panel: ['aggregator_unavailable_apiservice', 'aggregator_unavailable_apiservice_total', 'alertmanager_cluster_members', 'alertmanager_config_hash', 'alertmanager_config_last_reload_successful' … |
| `observability.alerts-never-fired.cluster` | warn | low | 127 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 37 of 41 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('dev-app-s', 'app-s-admin'), ('dev-app-s', 'app-s-api'), ('dev-app-s', 'app-s-backend'), ('dev-app-s', 'app-s-frontend'), ('dev-app-y', 'app-y-admin')] and 31 more), namespaces with saturation metrics … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"'])], receivers ['null', 'slack-sre', 'slack-system'], default receiver … |
| `observability.unstructured-logs.app-ab-prod` | warn | low | Of 947170 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.argocd` | warn | low | Of 14865 lines in 1h, 0 parse as JSON (0.0) |
| `observability.unstructured-logs.dev-app-v` | warn | low | Of 59439 lines in 1h, 0 parse as JSON (0.0) |
| `prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus StatefulSet replicas 1 (ready 1), restarts 2, started 2026-11-05T08:21:30.131638936Z |
| `prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus 2.49.1 — 2.53 is the last 2.x LTS (2024-07), 3.0 was released 2024-11 |
| `resilience.exec-probe.app-ab-prod/statefulset/app-ab-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s': 30}, readiness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.dev-app-aa/statefulset/app-aa-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.dev-app-aa/statefulset/app-aa-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.dev-app-v/statefulset/app-v-backend-dev-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.dev-app-y/statefulset/app-y-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.kube-system/daemonset/aws-node:aws-node` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s', 'port': None, 'timeout_s': 10, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s' … |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.middleware/statefulset/redis-master:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 6, 'period_s': 5, 'failure_threshold': 5, 'initial_delay_s': 20}, readiness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-r/statefulset/app-r-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s': 30}, readiness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-t/statefulset/app-t-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s': 30}, readiness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-x/statefulset/app-x-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6, 'initial_delay_s': 30}, readiness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-y/statefulset/app-y-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s' … |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-file-worker:file-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': None, 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
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
| `resources.memory-request-overprovisioned.app-ab-prod/sts/app-ab-backend-postgresql:postgresql` | warn | low | pod app-ab-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.22; database-like: keep the request |
| `resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | low | pod argocd-repo-server-d487895cc-bth22: 7d memory working set p95 93 MB / request 512 MB = 0.18 |
| `resources.memory-request-overprovisioned.dev-app-aa/sts/app-aa-postgres:postgres` | warn | low | pod app-aa-postgres-0: 7d memory working set p95 28 MB / request 256 MB = 0.11; database-like: keep the request |
| `resources.memory-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend` | warn | low | pod app-s-backend-76775dbdd-ttz69: 7d memory working set p95 81 MB / request 256 MB = 0.32 |
| `resources.memory-request-overprovisioned.dev-app-y/deploy/app-y-ai:ai` | warn | low | pod app-y-ai-7cdbdc7544-szzcl: 7d memory working set p95 342 MB / request 1024 MB = 0.33 |
| `resources.memory-request-overprovisioned.dev-app-y/deploy/app-y-backend:backend` | warn | low | pod app-y-backend-69dbdf4f65-9x6jc: 7d memory working set p95 132 MB / request 512 MB = 0.26 |
| `resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | low | pod karpenter-9769889bd-nphgs: 7d memory working set p95 24 MB / request 256 MB = 0.10 |
| `resources.memory-request-overprovisioned.middleware/sts/redis-master:redis` | warn | low | pod redis-master-0: 7d memory working set p95 5 MB / request 256 MB = 0.02; database-like: keep the request |
| `resources.memory-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | low | pod vm-single-0: 7d memory working set p95 166 MB / request 512 MB = 0.32; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql` | warn | low | pod app-t-backend-postgresql-0: 7d memory working set p95 55 MB / request 256 MB = 0.21; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend` | warn | low | ['pod app-y-backend-596479b6f8-cx44t: 7d memory working set p95 99 MB / request 512 MB = 0.19', 'pod app-y-backend-596479b6f8-nv9j2: 7d memory working set p95 81 MB / request 512 MB = 0.16'] |
| `resources.memory-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend` | warn | low | ['pod app-z-frontend-6d58bbfcfc-nfk9x: 7d memory working set p95 79 MB / request 256 MB = 0.31', 'pod app-z-frontend-6d58bbfcfc-2qgs6: 7d memory working set p95 74 MB / request 256 MB = 0.29'] |
| `resources.memory-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j` | warn | low | pod app-z-neo4j-0: 7d memory working set p95 1110 MB / request 4096 MB = 0.27; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-aa/deployment/app-aa-backend` | warn | low | HPA dev-app-aa/app-aa-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 23.8 days ago |
| `scaling.hpa-never-scaled.dev-app-aa/deployment/app-aa-frontend` | warn | low | HPA dev-app-aa/app-aa-frontend: share of 15 days at min 1.00, min 1 max 2, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale None days ago |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-admin` | warn | low | HPA dev-app-s/app-s-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 170.2 days ago |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-api` | warn | low | HPA dev-app-s/app-s-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 199.9 days ago |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-backend` | warn | low | HPA dev-app-s/app-s-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 14% / target 70%, metrics ['cpu'], last scale 70.8 days ago |
| `scaling.hpa-never-scaled.dev-app-v/deployment/app-v-admin-frontend` | warn | low | HPA dev-app-v/app-v-admin-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 40.2 days ago |
| `scaling.hpa-never-scaled.dev-app-v/deployment/app-v-backend` | warn | low | HPA dev-app-v/app-v-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 13% / target 70%, metrics ['cpu'], last scale 44.2 days ago |
| `scaling.hpa-never-scaled.dev-app-v/deployment/app-v-frontend` | warn | low | HPA dev-app-v/app-v-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 8% / target 70%, metrics ['cpu'], last scale 0.3 days ago |
| `scaling.hpa-never-scaled.dev-app-y/deployment/app-y-admin` | warn | low | HPA dev-app-y/app-y-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 59.8 days ago |
| `scaling.hpa-never-scaled.dev-app-y/deployment/app-y-backend` | warn | low | HPA dev-app-y/app-y-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 11% / target 70%, metrics ['cpu'], last scale 21.8 days ago |
| `scaling.hpa-never-scaled.dev-app-y/deployment/app-y-frontend` | warn | low | HPA dev-app-y/app-y-frontend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 30% / target 70%, metrics ['cpu'], last scale 21.8 days ago |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
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

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>events.tracked-warning-reasons.FreeDiskSpaceFailed</code></summary>

```json
{
 "events": 1,
 "first": "2026-10-23T01:20:23Z",
 "last": "2026-11-07T01:32:11Z",
 "meaning": "kubelet image GC could not free space. Disk is full of in-use images and logs",
 "objects_by_count": [
  {
   "object": "Node/ip-10-0-1-139.ap-northeast-2.compute.internal",
   "occurrences": 1338
  }
 ],
 "occurrences": 1338,
 "per_snapshot": [
  1338
 ],
 "reason": "FreeDiskSpaceFailed",
 "severity_hint": "high",
 "trend": "flat",
 "type": "Warning"
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
<details><summary><code>resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "container": "prometheus"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.2827207924369473,
  "cpu_throttle_ratio_5m": 0.281590763309814
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.prod-app-s/deploy/app-s-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-s",
   "pod": "app-s-frontend-6d7ff4dcdb-wjjxj",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.4619289340101523
  }
 },
 {
  "labels": {
   "namespace": "prod-app-s",
   "pod": "app-s-frontend-6d7ff4dcdb-h7hpl",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.422753168749724,
   "cpu_throttle_ratio_5m": 0.37678207739307534
  }
 },
 {
  "labels": {
   "namespace": "prod-app-s",
   "pod": "app-s-frontend-6d7ff4dcdb-qfmxq",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.23787358554900917,
   "cpu_throttle_ratio_5m": 0.2853828306264501
  }
 },
 {
  "labels": {
   "namespace": "prod-app-s",
   "pod": "app-s-frontend-6d7ff4dcdb-tzwjn",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.2026594377322334
  }
 }
]
```

</details>
<details><summary><code>resources.memory-limit-near-p95.prod-app-z-backend/deploy/app-z-embedding-server:embedding</code></summary>

```json
{
 "labels": {
  "container": "embedding",
  "namespace": "prod-app-z-backend",
  "pod": "app-z-embedding-server-8445d87f5-dwqrx"
 },
 "value": 0.9429359436035156
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.prod-app-t/deploy/app-t-ai:ai</code></summary>

```json
{
 "cadvisor_oom_events_7d": 0,
 "kernel_any_node_read": false,
 "kernel_kills_24h": 0,
 "kernel_log_read": false,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_total": 2,
 "pods_now": [
  {
   "pod": "app-t-ai-5469577cf8-7nwnb",
   "created": "2026-11-06T08:26:51Z",
   "restarts": 0
  }
 ],
 "pods_oomkilled": 3,
 "pods_replaced": 3,
 "restarts_of_those_pods": 13,
 "target": "prod-app-t/deploy/app-t-ai:ai"
}
```

</details>
<details><summary><code>resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_container_status_last_terminated_reason",
  "container": "prometheus",
  "endpoint": "http",
  "instance": "10.0.2.210:8080",
  "job": "kube-state-metrics",
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "reason": "OOMKilled",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "ab79974f-8369-494a-bee0-c3e0c5558a6e"
 },
 "value": 1.0
}
```

</details>
<details><summary><code>security.networkpolicy-not-enforced.cluster</code></summary>

```json
{
 "enforced": false,
 "enforcement": "aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints",
 "namespaces_with_policy": [
  "app-ab-prod",
  "prod-app-r",
  "prod-app-t",
  "prod-app-x"
 ],
 "policies": 4,
 "policies_but_not_enforced": true
}
```

</details>
<details><summary><code>security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j</code></summary>

```json
{
 "container": "neo4j",
 "env_names": [
  "NEO4J_AUTH"
 ],
 "prod": true,
 "workload": "prod-app-z-backend/statefulset/app-z-neo4j"
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
<details><summary><code>storage.pvc-usage-high.dev-app-aa/data-app-aa-mysql-0</code></summary>

```json
{
 "capacity_gb": 9.7,
 "days_to_full": null,
 "growth_gb_per_day": 0.0,
 "host_fs": false,
 "inode_ratio": 0.0,
 "metrics": true,
 "storage_class": "gp3",
 "target": "dev-app-aa/data-app-aa-mysql-0",
 "used_ratio": 0.902,
 "workloads": [
  "statefulset/app-aa-mysql"
 ]
}
```

</details>
<details><summary><code>controlplane.apiserver-5xx.cluster</code></summary>

```json
{
 "labels": {
  "code": "503"
 },
 "value": 0.003702195401873311
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.Unhealthy</code></summary>

```json
{
 "events": 1,
 "first": "2026-11-07T00:48:24Z",
 "last": "2026-11-07T00:48:24Z",
 "meaning": "Probe failure. Readiness removes it from traffic, liveness restarts it",
 "objects_by_count": [
  {
   "object": "Pod/prod-app-s/app-s-backend-7c46f75bf6-ljlnl",
   "occurrences": 1
  }
 ],
 "occurrences": 1,
 "per_snapshot": [
  1
 ],
 "reason": "Unhealthy",
 "severity_hint": "medium",
 "trend": "flat",
 "type": "Warning"
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.UpdateFailed</code></summary>

```json
{
 "events": 1,
 "first": "2026-10-08T12:31:38Z",
 "last": "2026-11-07T01:18:03Z",
 "meaning": "Operator reconcile failure (ExternalSecret etc.)",
 "objects_by_count": [
  {
   "object": "ExternalSecret/database/mysql-app-v-secret",
   "occurrences": 2711
  }
 ],
 "occurrences": 2711,
 "per_snapshot": [
  2711
 ],
 "reason": "UpdateFailed",
 "severity_hint": "medium",
 "trend": "flat",
 "type": "Warning"
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
 "samples": []
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
 "samples": []
}
```

</details>
<details><summary><code>node.disk-usage.10.0.1.139:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "10.0.1.139:9100",
  "mountpoint": "/"
 },
 "value": 0.8481679528621179
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
<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
 "by_class": {
  "app-cause": 5,
  "app": 14,
  "cause": 138
 },
 "symptom_ratio": 0.0,
 "symptom_rules": []
}
```

</details>
<details><summary><code>prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "head_series": 165690,
 "memory_limit": "1536Mi",
 "monitoring_oomkilled": [
  "loki-stack-0/loki",
  "prometheus-kube-prometheus-stack-prometheus-0/prometheus"
 ],
 "monitoring_restarts_7d": {
  "prometheus-kube-prometheus-stack-prometheus-0": 1
 },
 "oomkilled_at": "2026-11-05T08:21:29Z",
 "oomkilled_last": true,
 "present": true,
 "restarts": 2,
 "rss_vs_limit": 0.655,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
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
<details><summary><code>resources.cpu-throttling.dev-app-s/deploy/app-s-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "dev-app-s",
   "pod": "app-s-frontend-6578574c-qx5nj",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.22954662852147653
  }
 },
 {
  "labels": {
   "namespace": "dev-app-s",
   "pod": "app-s-frontend-999976975-nf4rv",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.10574457757017457,
   "cpu_throttle_ratio_5m": 0.11721611721611723
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.dev-app-v/deploy/app-v-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "dev-app-v",
   "pod": "app-v-frontend-f7b9d96d4-dn7qv",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.23076923076923078
  }
 },
 {
  "labels": {
   "namespace": "dev-app-v",
   "pod": "app-v-frontend-f7b9d96d4-jl226",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.208955223880597
  }
 },
 {
  "labels": {
   "namespace": "dev-app-v",
   "pod": "app-v-frontend-f7b9d96d4-pj26b",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.17808219178082194
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.dev-app-y/deploy/app-y-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-frontend-7f6d6dc65b-lnmq4",
  "container": "frontend"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.11552321632107948,
  "cpu_throttle_ratio_5m": 0.16141732283464566
 }
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "cadvisor_oom_events_7d": 1,
 "kernel_any_node_read": false,
 "kernel_kills_24h": 0,
 "kernel_log_read": false,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_total": 1,
 "pods_now": [
  {
   "pod": "prometheus-kube-prometheus-stack-prometheus-0",
   "created": "2026-09-08T12:47:49Z",
   "restarts": 2
  }
 ],
 "pods_oomkilled": 1,
 "pods_replaced": 0,
 "restarts_of_those_pods": 1,
 "target": "monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus"
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
  "instance": "10.0.2.210:8080",
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
<details><summary><code>resources.oomkilled.monitoring/sts/loki-stack:loki</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_container_status_last_terminated_reason",
  "container": "loki",
  "endpoint": "http",
  "instance": "10.0.2.210:8080",
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
<details><summary><code>observability.alert-firing-stale.KubeControllerManagerDown</code></summary>

```json
{
 "labels": {
  "alertname": "KubeControllerManagerDown",
  "severity": "critical"
 },
 "value": 59.53183667823948
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
 "value": 59.53177880786911
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeControllerManagerDown</code></summary>

```json
{
 "alertname": "KubeControllerManagerDown",
 "samples_7d": 20157.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeSchedulerDown</code></summary>

```json
{
 "alertname": "KubeSchedulerDown",
 "samples_7d": 20157.0
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
  "prod-app-v": 2,
  "app-ab-prod": 2,
  "arc-system": 1,
  "dev-app-aa": 1,
  "prod-app-x": 1
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
<details><summary><code>resources.besteffort-in-prod.prod-app-z-backend/deploy/tts-proxy</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_status_qos_class",
  "container": "kube-state-metrics",
  "endpoint": "http",
  "instance": "10.0.2.210:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-z-backend",
  "pod": "tts-proxy-7b6db97b69-4bbjf",
  "qos_class": "BestEffort",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "99b58936-3d63-43b5-8ffe-c9ceb4353c71"
 },
 "value": 1.0
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-backend-78679bf4b-lhhg4",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.005864835110327634,
  "cpu_p95_7d_cores": 0.002932417555163817,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-z-backend/deploy/app-z-embedding-server:embedding</code></summary>

```json
[
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-z-backend",
   "pod": "app-z-embedding-server-8445d87f5-dwqrx"
  },
  "value": 0.5797106577207329
 },
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-z-backend",
   "pod": "app-z-embedding-server-8445d87f5-sbzpj"
  },
  "value": 0.5797106577207329
 }
]
```

</details>
<details><summary><code>resources.large-request-binpacking.prod-app-z-backend/sts/app-z-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "container": "neo4j",
  "namespace": "prod-app-z-backend",
  "pod": "app-z-neo4j-0"
 },
 "value": 0.5797106577207329
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
<details><summary><code>resources.node-request-usage-gap.ip-10-0-1-117.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-1-117.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.9637305699481866,
  "node_cpu_usage_ratio_p95_7d": 0.09427467120514568,
  "node_cpu_usage_ratio_5m": 0.09016381175202279
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.ip-10-0-1-139.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-1-139.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.9158163265306118,
  "node_cpu_usage_ratio_p95_7d": 0.08545217798097365,
  "node_cpu_usage_ratio_5m": 0.04869886165713801
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.ip-10-0-1-245.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-1-245.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.9042553191489363,
  "node_cpu_usage_ratio_p95_7d": 0.08300501756190033,
  "node_cpu_usage_ratio_5m": 0.013712944695657621
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.ip-10-0-2-60.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-2-60.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.9896373056994822,
  "node_cpu_usage_ratio_p95_7d": 0.0633811399785234,
  "node_cpu_usage_ratio_5m": 0.058324909394507886
 }
}
```

</details>
<details><summary><code>scaling.hpa-flapping.prod-app-z-backend/hpa/keda-hpa-app-z-file-worker</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "keda-hpa-app-z-file-worker",
  "instance": "10.0.2.210:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-z-backend",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 77.0
}
```

</details>
<details><summary><code>scaling.karpenter-expired-not-replaced.default-n44bh</code></summary>

```json
{
 "age_h": 1056.5,
 "capacity_type": "spot",
 "disruption_blocked": {
  "do-not-disrupt pods": 22556
 },
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
<details><summary><code>tenancy.burst-tenant-unbounded.prod-app-z-backend</code></summary>

```json
{
 "burst_ratio_7d": 344.0,
 "cpu_limits": 12.2,
 "cpu_max_7d": 3.931,
 "cpu_median_7d": 0.011,
 "cpu_metrics_read": true,
 "cpu_p95_7d": 0.904,
 "has_quota": false,
 "kind": "prod",
 "namespace": "prod-app-z-backend",
 "nodes": {
  "ip-10-0-1-139.ap-northeast-2.compute.internal": 4,
  "ip-10-0-2-135.ap-northeast-2.compute.internal": 3,
  "ip-10-0-2-100.ap-northeast-2.compute.internal": 1,
  "ip-10-0-1-245.ap-northeast-2.compute.internal": 1
 },
 "shares_nodes_with_prod": true,
 "system": false
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
<details><summary><code>tenancy.prod-without-quota.app-ab-prod</code></summary>

```json
{
 "burst_ratio_7d": 2.0,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.023,
 "cpu_requests": 0.25,
 "cpu_share_of_cluster_p95": 0.01,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.5,
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
<details><summary><code>tenancy.prod-without-quota.prod-app-r</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.006,
 "cpu_requests": 0.62,
 "cpu_share_of_cluster_p95": 0.003,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.64,
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
 "burst_ratio_7d": 1.4,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.112,
 "cpu_requests": 0.35,
 "cpu_share_of_cluster_p95": 0.051,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.88,
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
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.009,
 "cpu_requests": 0.29,
 "cpu_share_of_cluster_p95": 0.004,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.93,
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
 "burst_ratio_7d": 4.2,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.024,
 "cpu_requests": 0.25,
 "cpu_share_of_cluster_p95": 0.011,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.01,
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
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.004,
 "cpu_requests": 0.1,
 "cpu_share_of_cluster_p95": 0.002,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.21,
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
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.007,
 "cpu_requests": 1.1,
 "cpu_share_of_cluster_p95": 0.003,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.52,
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
 "burst_ratio_7d": 1.2,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.037,
 "cpu_requests": 0.51,
 "cpu_share_of_cluster_p95": 0.017,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 3.43,
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
 "burst_ratio_7d": 344.0,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.904,
 "cpu_requests": 2.72,
 "cpu_share_of_cluster_p95": 0.41,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 11.89,
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
<details><summary><code>tenancy.tenant-without-limitrange.prod-app-z-backend</code></summary>

```json
{
 "cluster_saturated_7d": true,
 "containers_without_memory_limit": 2,
 "containers_without_requests": 2,
 "cpu_p95_7d": 0.904,
 "has_limitrange": false,
 "kind": "prod",
 "memory_p95_7d_gb": 11.89,
 "multi_org": false,
 "namespace": "prod-app-z-backend",
 "pods": 9,
 "prod": true
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
 "rbac_policy_csv_lines": 1,
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
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "autopath": false,
 "cache_hit_ratio": 0.9237,
 "forward_nxdomain_ratio": 0.442,
 "metrics_available": true,
 "nxdomain_ratio": 0.503,
 "pods_default_ndots": 154,
 "qps_total": 75.8,
 "upstreams": [
  "10.0.0.2:53"
 ]
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
  "middleware/deployment/kafka-exporter",
  "middleware/deployment/kafka-ui",
  "middleware/deployment/redis-insight",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "monitoring/deployment/kube-prometheus-stack-operator",
  "monitoring/deployment/vmalert",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "argocd/statefulset/argocd-application-controller",
  "dev-app-s/statefulset/app-s-backend-mysql",
  "dev-app-y/statefulset/app-y-backend-mysql",
  "dev-app-v/statefulset/app-v-backend-dev-mysql",
  "dev-app-aa/statefulset/app-aa-mysql",
  "dev-app-aa/statefulset/app-aa-postgres",
  "middleware/statefulset/kafka-controller",
  "middleware/statefulset/redis-master",
  "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager",
  "monitoring/statefulset/loki-stack",
  "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
  "monitoring/statefulset/vm-single",
  "prod-app-t/statefulset/app-t-backend-postgresql",
  "prod-app-x/statefulset/app-x-postgresql",
  "prod-app-s/statefulset/app-s-backend-mysql",
  "prod-app-y/statefulset/app-y-backend-mysql",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "prod-app-r/statefulset/app-r-postgresql",
  "prod-app-v/statefulset/app-v-backend-prod-mysql",
  "app-ab-prod/statefulset/app-ab-backend-postgresql"
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
  "dev-app-y/deployment/app-y-frontend",
  "dev-app-v/deployment/app-v-admin-frontend",
  "dev-app-v/deployment/app-v-backend",
  "dev-app-v/deployment/app-v-frontend",
  "dev-app-aa/deployment/app-aa-backend",
  "dev-app-aa/deployment/app-aa-frontend",
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
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/deployment/app-r-web",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "app-ab-prod/deployment/app-ab-backend",
  "app-ab-prod/deployment/app-ab-frontend"
 ]
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
 "samples": []
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
 "samples": []
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
<details><summary><code>node.network-errors.10.0.1.139:9100:eth0</code></summary>

```json
{
 "labels": {
  "device": "eth0",
  "instance": "10.0.1.139:9100"
 },
 "value": 187.0649531087183
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "alerting": 157,
 "by_class": {
  "app-cause": 5,
  "app": 14,
  "cause": 138
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": {
  "type": "exec",
  "path": null,
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
<details><summary><code>resources.cpu-request-overprovisioned.app-ab-prod/deploy/app-ab-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "app-ab-prod",
  "pod": "app-ab-backend-6dd8fcbf96-nshrh",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.14372492698034348,
  "cpu_p95_7d_cores": 0.01437249269803435,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-ab-prod/sts/app-ab-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "app-ab-prod",
  "pod": "app-ab-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.06952169073532834,
  "cpu_p95_7d_cores": 0.006952169073532834,
  "container_cpu_request_cores": 0.1
 }
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
  "cpu_request_p95_ratio_7d": 0.012876002810367835,
  "cpu_p95_7d_cores": 0.002575200562073567,
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
  "cpu_request_p95_ratio_7d": 0.1806991535066766,
  "cpu_p95_7d_cores": 0.03613983070133532,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-aa/deploy/app-aa-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-aa",
  "pod": "app-aa-backend-57fdd58475-5dn47",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.004670183330130956,
  "cpu_p95_7d_cores": 0.0009340366660261912,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-aa/sts/app-aa-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-aa",
  "pod": "app-aa-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.044754067907769694,
  "cpu_p95_7d_cores": 0.008950813581553939,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-aa/sts/app-aa-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-aa",
  "pod": "app-aa-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.07511811241423316,
  "cpu_p95_7d_cores": 0.007511811241423317,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-api:api</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-api-575d497d9b-5ttcv",
  "container": "api"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.11387528633694577,
  "cpu_p95_7d_cores": 0.011387528633694577,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-backend-76775dbdd-ttz69",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.17286174750932937,
  "cpu_p95_7d_cores": 0.01728617475093294,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-s/sts/app-s-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.10129789081841822,
  "cpu_p95_7d_cores": 0.010129789081841823,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-v/deploy/app-v-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-v",
  "pod": "app-v-backend-7cfd8c975-b9p48",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.12619528305430802,
  "cpu_p95_7d_cores": 0.012619528305430802,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-v/sts/app-v-backend-dev-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-v",
  "pod": "app-v-backend-dev-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.10333470333807893,
  "cpu_p95_7d_cores": 0.010333470333807894,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-y/deploy/app-y-ai:ai</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-ai-7cdbdc7544-szzcl",
  "container": "ai"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.02489732431890859,
  "cpu_p95_7d_cores": 0.002489732431890859,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-y/deploy/app-y-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-backend-69dbdf4f65-9x6jc",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.11131501343081211,
  "cpu_p95_7d_cores": 0.011131501343081211,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-y/sts/app-y-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.08893449055210677,
  "cpu_p95_7d_cores": 0.008893449055210677,
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
   "cpu_request_p95_ratio_7d": 0.0991532477786506,
   "cpu_p95_7d_cores": 0.01983064955573012,
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
   "cpu_request_p95_ratio_7d": 0.00223566517377295,
   "cpu_p95_7d_cores": 0.00044713303475459,
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
  "cpu_request_p95_ratio_7d": 0.003095075222652666,
  "cpu_p95_7d_cores": 0.0003095075222652666,
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
  "cpu_request_p95_ratio_7d": 0.017954506464415484,
  "cpu_p95_7d_cores": 0.0017954506464415486,
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
  "cpu_request_p95_ratio_7d": 0.017218102096255905,
  "cpu_p95_7d_cores": 0.0017218102096255906,
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
   "cpu_request_p95_ratio_7d": 0.02367153100017002,
   "cpu_p95_7d_cores": 0.002367153100017002,
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
   "cpu_request_p95_ratio_7d": 0.009792626422657734,
   "cpu_p95_7d_cores": 0.0009792626422657734,
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
   "cpu_request_p95_ratio_7d": 0.07135395545698191,
   "cpu_p95_7d_cores": 0.007135395545698191,
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
   "cpu_request_p95_ratio_7d": 0.06683902509788925,
   "cpu_p95_7d_cores": 0.006683902509788925,
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
  "cpu_request_p95_ratio_7d": 0.05399275749206629,
  "cpu_p95_7d_cores": 0.005399275749206629,
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
   "cpu_request_p95_ratio_7d": 0.007575347059313433,
   "cpu_p95_7d_cores": 0.0007575347059313434,
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
   "cpu_request_p95_ratio_7d": 0.0072091365504657915,
   "cpu_p95_7d_cores": 0.0007209136550465792,
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
   "cpu_request_p95_ratio_7d": 0.004508116072718936,
   "cpu_p95_7d_cores": 0.00045081160727189365,
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
   "cpu_request_p95_ratio_7d": 0.003741605170206563,
   "cpu_p95_7d_cores": 0.00037416051702065633,
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
   "cpu_request_p95_ratio_7d": 0.0035955307861417676,
   "cpu_p95_7d_cores": 0.0003595530786141768,
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
   "cpu_request_p95_ratio_7d": 0.0035625915613478614,
   "cpu_p95_7d_cores": 0.00035625915613478614,
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
  "cpu_request_p95_ratio_7d": 0.009447938426718618,
  "cpu_p95_7d_cores": 0.000944793842671862,
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
  "cpu_request_p95_ratio_7d": 0.3414046690829845,
  "cpu_p95_7d_cores": 0.0682809338165969,
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
  "cpu_request_p95_ratio_7d": 0.019537024790708474,
  "cpu_p95_7d_cores": 0.0019537024790708475,
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
  "cpu_request_p95_ratio_7d": 0.06917389962598694,
  "cpu_p95_7d_cores": 0.006917389962598695,
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
  "cpu_request_p95_ratio_7d": 0.004625898845984854,
  "cpu_p95_7d_cores": 0.0013877696537954562,
  "container_cpu_request_cores": 0.3
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-r/sts/app-r-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-r",
  "pod": "app-r-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.04479408107876748,
  "cpu_p95_7d_cores": 0.004479408107876748,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-s/sts/app-s-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-s",
  "pod": "app-s-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.051727687566922274,
  "cpu_p95_7d_cores": 0.010345537513384455,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-t",
  "pod": "app-t-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.050899334010273536,
  "cpu_p95_7d_cores": 0.005089933401027354,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-v/sts/app-v-backend-prod-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-v",
  "pod": "app-v-backend-prod-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.05021223838795025,
  "cpu_p95_7d_cores": 0.01004244767759005,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-cx44t",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.09759593776186348,
   "cpu_p95_7d_cores": 0.009759593776186348,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-nv9j2",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.09672536625587282,
   "cpu_p95_7d_cores": 0.009672536625587282,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-y/sts/app-y-backend-mysql:mysql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-y",
  "pod": "app-y-backend-mysql-0",
  "container": "mysql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.04463388041591375,
  "cpu_p95_7d_cores": 0.00892677608318275,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-embedding-server:embedding</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-embedding-server-8445d87f5-dwqrx",
  "container": "embedding"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.2790317510541459,
  "cpu_p95_7d_cores": 0.13951587552707295,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-z-backend",
   "pod": "app-z-frontend-6d58bbfcfc-nfk9x",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.007328249628484884,
   "cpu_p95_7d_cores": 0.0007328249628484884,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "prod-app-z-backend",
   "pod": "app-z-frontend-6d58bbfcfc-2qgs6",
   "container": "frontend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.006823016296655346,
   "cpu_p95_7d_cores": 0.0006823016296655346,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-neo4j-0",
  "container": "neo4j"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.010792466084195455,
  "cpu_p95_7d_cores": 0.0053962330420977275,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.ip-10-0-1-241.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-1-241.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_memory_request_ratio": 0.6637597400652016,
  "node_memory_usage_ratio_p95_7d": 0.3551662858247837,
  "node_memory_usage_ratio": 0.35439266386868173
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.ip-10-0-2-135.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-2-135.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_memory_request_ratio": 0.992571564691715,
  "node_memory_usage_ratio_p95_7d": 0.43543694063069793,
  "node_memory_usage_ratio": 0.41505819691116724
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.ip-10-0-2-218.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-2-218.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_memory_request_ratio": 0.7099221572409463,
  "node_memory_usage_ratio_p95_7d": 0.2313174405357903,
  "node_memory_usage_ratio": 0.22887983009206517
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.ip-10-0-1-137.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-1-137.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.7978723404255321,
  "node_cpu_usage_ratio_p95_7d": 0.00429569315734247,
  "node_cpu_usage_ratio_5m": 0.003790458752069359
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.ip-10-0-2-135.ap-northeast-2.compute.internal</code></summary>

```json
{
 "labels": {
  "node": "ip-10-0-2-135.ap-northeast-2.compute.internal"
 },
 "values": {
  "node_cpu_request_ratio": 0.7357512953367876,
  "node_cpu_usage_ratio_p95_7d": 0.04819973042027416,
  "node_cpu_usage_ratio_5m": 0.043225969570254624
 }
}
```

</details>
<details><summary><code>scaling.hpa-flapping.dev-app-s/hpa/app-s-frontend</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "app-s-frontend",
  "instance": "10.0.2.210:8080",
  "job": "kube-state-metrics",
  "namespace": "dev-app-s",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 44.0
}
```

</details>
<details><summary><code>scaling.hpa-flapping.prod-app-z-backend/hpa/keda-hpa-app-z-graph-worker</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "keda-hpa-app-z-graph-worker",
  "instance": "10.0.2.210:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-z-backend",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 34.0
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
  "prod-app-v/data-app-v-backend-prod-mysql-0",
  "prod-app-s/data-app-s-backend-mysql-0",
  "prod-app-z-backend/data-app-z-neo4j-0",
  "app-ab-prod/data-app-ab-backend-postgresql-0",
  "prod-app-r/data-app-r-postgresql-0",
  "prod-app-t/data-app-t-backend-postgresql-0",
  "prod-app-y/data-app-y-backend-mysql-0",
  "prod-app-x/data-app-x-postgresql-0"
 ],
 "rows": [
  {
   "namespace": "dev-app-aa",
   "name": "data-app-aa-mysql-0",
   "target": "dev-app-aa/data-app-aa-mysql-0",
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
   "namespace": "monitoring",
   "name": "prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "target": "monitoring/prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.448,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.028,
   "days_to_full": 389,
   "metrics": true,
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
   "namespace": "prod-app-v",
   "name": "data-app-v-backend-prod-mysql-0",
   "target": "prod-app-v/data-app-v-backend-prod-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.13,
   "inode_ratio": 0.001,
   "growth_gb_per_day": 0.0,
   "days_to_full": 20537,
   "metrics": true,
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
   "namespace": "prod-app-s",
   "name": "data-app-s-backend-mysql-0",
   "target": "prod-app-s/data-app-s-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.077,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.002,
   "days_to_full": 4035,
   "metrics": true,
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
   "namespace": "dev-app-v",
   "name": "data-app-v-backend-dev-mysql-0",
   "target": "dev-app-v/data-app-v-backend-dev-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.06,
   "inode_ratio": 0.001,
   "growth_gb_per_day": 0.0,
   "days_to_full": 1803806,
   "metrics": true,
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
   "namespace": "prod-app-z-backend",
   "name": "data-app-z-neo4j-0",
   "target": "prod-app-z-backend/data-app-z-neo4j-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.052,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.009,
   "days_to_full": 2098,
   "metrics": true,
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
   "namespace": "app-ab-prod",
   "name": "data-app-ab-backend-postgresql-0",
   "target": "app-ab-prod/data-app-ab-backend-postgresql-0",
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
    "statefulset/app-ab-backend-postgresql"
   ],
   "db_like": true,
   "pv": "pvc-f226562f-a020-4027-a0d4-1494585c8b6f",
   "zone": "ap-northeast-2a",
   "reclaim_policy": "Delete",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "dev-app-s",
   "name": "data-app-s-backend-mysql-0",
   "target": "dev-app-s/data-app-s-backend-mysql-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.031,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": 417236,
   "metrics": true,
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
   "namespace": "prod-app-r",
   "name": "data-app-r-postgresql-0",
   "target": "prod-app-r/data-app-r-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.027,
   "inode_ratio": 0.003,
   "growth_gb_per_day": 0.001,
   "days_to_full": 17229,
   "metrics": true,
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
   "namespace": "dev-app-y",
   "name": "data-app-y-backend-mysql-0",
   "target": "dev-app-y/data-app-y-backend-mysql-0",
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
   "namespace": "prod-app-t",
   "name": "data-app-t-backend-postgresql-0",
   "target": "prod-app-t/data-app-t-backend-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.022,
   "inode_ratio": 0.003,
   "growth_gb_per_day": 0.0,
   "days_to_full": 19351,
   "metrics": true,
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
   "namespace": "prod-app-y",
   "name": "data-app-y-backend-mysql-0",
   "target": "prod-app-y/data-app-y-backend-mysql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 50.0,
   "capacity_gb": 48.9,
   "used_ratio": 0.009,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.0,
   "days_to_full": 30012468,
   "metrics": true,
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
   "namespace": "dev-app-aa",
   "name": "data-app-aa-postgres-0",
   "target": "dev-app-aa/data-app-aa-postgres-0",
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
   "capacity_gb": 19.5,
   "used_ratio": 0.006,
   "inode_ratio": 0.001,
   "growth_gb_per_day": -0.004,
   "days_to_full": null,
   "metrics": true,
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
   "namespace": "prod-app-x",
   "name": "data-app-x-postgresql-0",
   "target": "prod-app-x/data-app-x-postgresql-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 10.0,
   "capacity_gb": 9.7,
   "used_ratio": 0.005,
   "inode_ratio": 0.002,
   "growth_gb_per_day": 0.0,
   "days_to_full": 726879,
   "metrics": true,
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
   "namespace": "middleware",
   "name": "redis-data-redis-master-0",
   "target": "middleware/redis-data-redis-master-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 8.0,
   "capacity_gb": 7.8,
   "used_ratio": 0.001,
   "inode_ratio": 0.0,
   "growth_gb_per_day": -0.006,
   "days_to_full": null,
   "metrics": true,
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
   "days_to_full": 45473,
   "metrics": true,
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
   "growth_gb_per_day": -0.0,
   "days_to_full": null,
   "metrics": true,
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
  }
 ]
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-ab-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-ab-prod",
 "networkpolicies": 1,
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
 "networkpolicies": 1,
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
<details><summary><code>tenancy.prod-boundary-missing.prod-app-t</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-t",
 "networkpolicies": 1,
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
<details><summary><code>tenancy.prod-boundary-missing.prod-app-x</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "prod-app-x",
 "networkpolicies": 1,
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
<details><summary><code>tenancy.prod-without-quota.arc-runners</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": 0.55,
 "cpu_requests": 0.0,
 "cpu_share_of_cluster_p95": 0.25,
 "has_quota": false,
 "kind": "ci",
 "memory_p95_7d_gb": 1.35,
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
 "burst_ratio_7d": 1.1,
 "cpu_p95_7d": 0.017,
 "cpu_requests": 0.55,
 "cpu_share_of_cluster_p95": 0.008,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": 0.85,
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
 "burst_ratio_7d": 1.4,
 "cpu_p95_7d": 0.052,
 "cpu_requests": 0.4,
 "cpu_share_of_cluster_p95": 0.024,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": 0.86,
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
 "burst_ratio_7d": 1.7,
 "cpu_p95_7d": 0.024,
 "cpu_requests": 0.3,
 "cpu_share_of_cluster_p95": 0.011,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": 0.95,
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
 "burst_ratio_7d": 1.1,
 "cpu_p95_7d": 0.035,
 "cpu_requests": 0.4,
 "cpu_share_of_cluster_p95": 0.016,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": 1.4,
 "memory_requests_gb": 2.25,
 "namespace": "dev-app-y",
 "pods": 5,
 "prod": false,
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
<details><summary><code>scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 0,
 "days_since_last_scale": 21.6,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "name": "app-z-backend",
 "namespace": "prod-app-z-backend",
 "never_scaled_15d": true,
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 1,
 "days_since_last_scale": 88.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "name": "app-z-frontend",
 "namespace": "prod-app-z-backend",
 "never_scaled_15d": true,
 "prod": true,
 "target": "prod-app-z-backend/deployment/app-z-frontend",
 "target_cpu_utilization": 70
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
 "aws_api_ops_by_calls": [
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
  ],
  [
   "Elastic Load Balancing v2/DescribeRules",
   3732
  ],
  [
   "ACM/DescribeCertificate",
   3509
  ],
  [
   "EC2/DescribeVpcs",
   2989
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroups",
   1880
  ],
  [
   "Elastic Load Balancing v2/DescribeListeners",
   1866
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancerAttributes",
   1866
  ],
  [
   "Elastic Load Balancing v2/DescribeListenerCertificates",
   1280
  ],
  [
   "Shield/GetSubscriptionState",
   1221
  ],
  [
   "EC2/DescribeNetworkInterfaces",
   1080
  ],
  [
   "ACM/ListCertificates",
   660
  ],
  [
   "WAF Regional/GetWebACLForResource",
   644
  ],
  [
   "WAFV2/GetWebACLForResource",
   644
  ],
  [
   "EC2/DescribeSubnets",
   586
  ],
  [
   "Elastic Load Balancing v2/ModifyRule",
   557
  ],
  [
   "EC2/AuthorizeSecurityGroupIngress",
   195
  ],
  [
   "EC2/RevokeSecurityGroupIngress",
   194
  ],
  [
   "Elastic Load Balancing v2/CreateRule",
   30
  ],
  [
   "Elastic Load Balancing v2/CreateTargetGroup",
   30
  ],
  [
   "Elastic Load Balancing v2/DeleteRule",
   14
  ],
  [
   "Elastic Load Balancing v2/DeleteTargetGroup",
   14
  ],
  [
   "Elastic Load Balancing v2/ModifyTargetGroup",
   13
  ],
  [
   "EC2/DescribeAvailabilityZones",
   2
  ]
 ],
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
  ],
  [
   "EC2/DescribeSubnets",
   0.138
  ],
  [
   "Elastic Load Balancing v2/CreateRule",
   0.103
  ],
  [
   "Elastic Load Balancing v2/ModifyRule",
   0.096
  ],
  [
   "ACM/ListCertificates",
   0.087
  ],
  [
   "EC2/DescribeVpcs",
   0.084
  ],
  [
   "EC2/DescribeInstances",
   0.082
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroups",
   0.081
  ],
  [
   "Elastic Load Balancing v2/DescribeRules",
   0.08
  ],
  [
   "EC2/DescribeSecurityGroups",
   0.076
  ],
  [
   "WAFV2/GetWebACLForResource",
   0.075
  ],
  [
   "Elastic Load Balancing v2/DescribeTags",
   0.071
  ],
  [
   "ACM/DescribeCertificate",
   0.07
  ],
  [
   "EC2/DescribeNetworkInterfaces",
   0.065
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancers",
   0.064
  ],
  [
   "WAF Regional/GetWebACLForResource",
   0.059
  ],
  [
   "Elastic Load Balancing v2/DescribeListeners",
   0.057
  ],
  [
   "Elastic Load Balancing v2/DescribeListenerCertificates",
   0.052
  ],
  [
   "Elastic Load Balancing v2/DeregisterTargets",
   0.05
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancerAttributes",
   0.047
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroupAttributes",
   0.042
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetHealth",
   0.036
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
 "cluster_status": "disabled",
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
<details><summary><code>coredns.aaaa-noise.cluster</code></summary>

```json
{
 "aaaa_ratio": 0.5,
 "cluster_ipv6": false,
 "metrics_available": true,
 "qps_total": 75.8
}
```

</details>
<details><summary><code>cost.idle-node.ip-10-0-1-137.ap-northeast-2.compute.internal</code></summary>

```json
{
 "cpu_p95_ratio": 0.00429569315734247,
 "instance_type": "r8gd.medium",
 "memory_p95_ratio": 0.043260228361303214,
 "monthly_usd": null,
 "node": "ip-10-0-1-137.ap-northeast-2.compute.internal",
 "pool": "default"
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
<details><summary><code>kubeproxy.conntrack-invalid-drops.cluster</code></summary>

```json
{
 "ct_invalid_dropped_1h": 822,
 "external_traffic_local": 0,
 "metrics_available": true,
 "no_local_endpoint_services": 0
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
 "alert_metrics": 173,
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
  "grpc_server_handling_seconds_bucket",
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
  "prometheus_remote_storage_highest_timestamp_in_seconds",
  "prometheus_remote_storage_queue_highest_sent_timestamp_seconds",
  "prometheus_remote_storage_samples_failed_total",
  "prometheus_remote_storage_samples_total",
  "prometheus_remote_storage_shards_desired",
  "prometheus_remote_storage_shards_max",
  "prometheus_remote_storage_succeeded_samples_total",
  "prometheus_rule_evaluation_failures_total",
  "prometheus_rule_group_iterations_missed_total",
  "prometheus_rule_group_rules",
  "prometheus_sd_refresh_failures_total",
  "prometheus_target_metadata_cache_entries",
  "prometheus_target_scrape_pool_exceeded_label_limits_total",
  "prometheus_target_scrape_pool_exceeded_target_limit_total",
  "prometheus_target_sync_failed_total",
  "prometheus_tsdb_compactions_failed_total",
  "prometheus_tsdb_reloads_failures_total",
  "reloader_last_reload_successful",
  "s_failure_total"
 ],
 "alert_metrics_without_panel_count": 132,
 "available": true,
 "panel_metrics": 196,
 "read": 28
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
  "KubeletTooManyPods",
  "NodeCPUHighUsage",
  "NodeFilesystemSpaceFillingUp",
  "NodeSystemSaturation",
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
 "never_fired_count": 127,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
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
   "missing_all_lte": false,
   "cluster_ic_metrics": false
  }
 ],
 "namespaces_with_saturation_metrics": [
  "default",
  "kube-system",
  "middleware",
  "monitoring"
 ]
}
```

</details>
<details><summary><code>observability.severity-channels-not-separated.cluster</code></summary>

```json
{
 "default_receiver": "slack-system",
 "receivers": {
  "null": [],
  "slack-sre": [
   "slack"
  ],
  "slack-system": [
   "slack"
  ]
 },
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
 "start_time": "2026-11-05T08:21:30.131638936Z",
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
  "path": null,
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 6,
  "period_s": 5,
  "failure_threshold": 5,
  "initial_delay_s": 20
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 5,
  "period_s": 10,
  "failure_threshold": 6,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "readiness": {
  "type": "exec",
  "path": null,
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
  "path": null,
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
  "path": null,
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
<details><summary><code>resources.memory-request-overprovisioned.app-ab-prod/sts/app-ab-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "app-ab-prod",
  "pod": "app-ab-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2166900634765625,
  "memory_p95_7d_bytes": 58167296.0,
  "container_memory_request_bytes": 268435456.0
 }
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
  "memory_request_p95_ratio_7d": 0.18167800903320314,
  "memory_p95_7d_bytes": 97537638.4,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-aa/sts/app-aa-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-aa",
  "pod": "app-aa-postgres-0",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.1086578369140625,
  "memory_p95_7d_bytes": 29167616.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-backend-76775dbdd-ttz69",
  "container": "backend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.3174591064453125,
  "memory_p95_7d_bytes": 85217280.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-y/deploy/app-y-ai:ai</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-ai-7cdbdc7544-szzcl",
  "container": "ai"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.33350372314453125,
  "memory_p95_7d_bytes": 358096896.0,
  "container_memory_request_bytes": 1073741824.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-y/deploy/app-y-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-y",
  "pod": "app-y-backend-69dbdf4f65-9x6jc",
  "container": "backend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2570606231689453,
  "memory_p95_7d_bytes": 138008371.2,
  "container_memory_request_bytes": 536870912.0
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
  "memory_request_p95_ratio_7d": 0.0951690673828125,
  "memory_p95_7d_bytes": 25546752.0,
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
  "memory_request_p95_ratio_7d": 0.0213470458984375,
  "memory_p95_7d_bytes": 5730304.0,
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
  "memory_request_p95_ratio_7d": 0.324200439453125,
  "memory_p95_7d_bytes": 174053785.6,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-t",
  "pod": "app-t-backend-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.21312942504882806,
  "memory_p95_7d_bytes": 57211494.39999998,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-cx44t",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.1925159454345703,
   "memory_p95_7d_bytes": 103356211.19999999,
   "container_memory_request_bytes": 536870912.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-nv9j2",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.1590991973876953,
   "memory_p95_7d_bytes": 85415731.19999999,
   "container_memory_request_bytes": 536870912.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-z-backend",
   "pod": "app-z-frontend-6d58bbfcfc-nfk9x",
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
   "namespace": "prod-app-z-backend",
   "pod": "app-z-frontend-6d58bbfcfc-2qgs6",
   "container": "frontend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.29039688110351564,
   "memory_p95_7d_bytes": 77952819.2,
   "container_memory_request_bytes": 268435456.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-neo4j-0",
  "container": "neo4j"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2708877086639404,
  "memory_p95_7d_bytes": 1163453849.6,
  "container_memory_request_bytes": 4294967296.0
 }
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
<details><summary><code>scaling.hpa-never-scaled.dev-app-aa/deployment/app-aa-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 0,
 "days_since_last_scale": 23.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-aa-backend",
 "namespace": "dev-app-aa",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-aa/deployment/app-aa-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-aa/deployment/app-aa-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 2,
 "days_since_last_scale": null,
 "keda_owned": false,
 "max": 2,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-aa-frontend",
 "namespace": "dev-app-aa",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-aa/deployment/app-aa-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-s/deployment/app-s-admin</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 170.2,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-s-admin",
 "namespace": "dev-app-s",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-s/deployment/app-s-admin",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-s/deployment/app-s-api</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 12,
 "days_since_last_scale": 199.9,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-s-api",
 "namespace": "dev-app-s",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-s/deployment/app-s-api",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-s/deployment/app-s-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 14,
 "days_since_last_scale": 70.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-s-backend",
 "namespace": "dev-app-s",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-s/deployment/app-s-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-v/deployment/app-v-admin-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 40.2,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-v-admin-frontend",
 "namespace": "dev-app-v",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-v/deployment/app-v-admin-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-v/deployment/app-v-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 13,
 "days_since_last_scale": 44.2,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-v-backend",
 "namespace": "dev-app-v",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-v/deployment/app-v-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-v/deployment/app-v-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9983796296296282,
 "current_cpu_utilization": 8,
 "days_since_last_scale": 0.3,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-v-frontend",
 "namespace": "dev-app-v",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-v/deployment/app-v-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-y/deployment/app-y-admin</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 59.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-y-admin",
 "namespace": "dev-app-y",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-y/deployment/app-y-admin",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-y/deployment/app-y-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 11,
 "days_since_last_scale": 21.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-y-backend",
 "namespace": "dev-app-y",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-y/deployment/app-y-backend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.dev-app-y/deployment/app-y-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 30,
 "days_since_last_scale": 21.8,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "app-y-frontend",
 "namespace": "dev-app-y",
 "never_scaled_15d": true,
 "prod": false,
 "target": "dev-app-y/deployment/app-y-frontend",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "desired_changes_7d": 0.0,
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
 "desired_changes_7d": 0.0,
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

### 7-6. Tool notes (about kubegap itself)

(not written this run)

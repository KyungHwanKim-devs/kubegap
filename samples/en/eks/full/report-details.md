# kubegap report details — app-u-cluster-eks (`app-u-cluster`), full mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `report/outline.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `app-u-cluster` / arn:aws:eks:ap-northeast-2:<account>:cluster/app-u-cluster-eks (eks, v1.32.13-eks-577a51e) |
| Run time / mode | 2026-11-15T02:09:39+09:00 / full (collection 299.1 s, 0 steps skipped by mode, 6 failed) |
| Scale | `medium` (answered) |
| kubegap / rubric / signatures | 0.2.0 / 0.1.94 / 1.1.1 |
| Verified against | Kubernetes v1.32.13-eks-577a51e (verified 1.30 to 1.37) · Prometheus 2.49.1 (verified 2.49 to 3.15) · Alertmanager 0.26.0 (verified 0.26 to 0.34) · Loki 2.6.1 (verified 2.6 to 3.7) · Grafana 10.2.3 (verified 10.2 to 13.3) |
| Nodes / namespaces / pods / CRDs | 9 (Ready 9) / 21 / 137 / 47 |
| Components (23) | actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics store | prometheus 2.49.1 retention 15d / size 0B via port-forward |
| Log store | loki 2.6.1 |
| Node access | ssm (EKS: SSM send-command); SSM unregistered 2 |
| Snapshot | `~/.kubegap/snapshots/<context>/2026-11-15T02-09-39` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 1 | 0 | no previous run of this mode |
| high | 23 | 27 | no previous run of this mode |
| medium | 105 | 153 | no previous run of this mode |
| low | 14 | 126 | no previous run of this mode |
| info | 1 | 0 | no previous run of this mode |

Checks 367: evaluated 359, not run on this platform or at this scale 3, skipped 3, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

| Finding | Final | Reason |
|---|---|---|
| security.plaintext-secret-env.prod-app-z-backend/deployment/app-ad:tailscale | low | TS_KUBE_SECRET is the name of the Secret in which the Tailscale container keeps its state (the Deployment also mounts a ts-state volume and sets TS_STATE_DIR); the 17-character word-shaped value is a name, not a credential. The real credential, TS_AUTHKEY, already comes from the Secret app-ad-tsauth. |

### 1-2. Aggregates the LLM recounted

(not written this run)

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | critical |  | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `controlplane.scheduler-unschedulable.prod-app-x/app-x-api` | high |  | 24h 'Unable to schedule pod; no fit' 39 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption … |
| `controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-backend` | high |  | 24h 'Unable to schedule pod; no fit' 26 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption … |
| `controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-embedding-server` | high |  | 24h 'Unable to schedule pod; no fit' 26 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption … |
| `eks.no-backup-policy.cluster` | high |  | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'stale_backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | high |  | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `karpenter.ec2nodeclass-al2.cluster` | high |  | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | high |  | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | high |  | server v1.32.13-eks-577a51e: EKS end of standard support 2026-03-23, 237 days past; upstream end of life 2026-02-28 |
| `platform.karpenter-version-compat.cluster` | high |  | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.34, 24 h or the pod's life 0.34: throttled through the day |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-11-14T14:34:30Z (0.1 days ago), 3 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | high |  | 3 NetworkPolicies (['prod-app-t', 'prod-app-x', 'prod-app-r']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.plaintext-secret-env.prod-app-z-backend/deployment/app-ad:tailscale` | high |  | Container tailscale env ['TS_KUBE_SECRET'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | high |  | Container neo4j env ['NEO4J_AUTH'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/app-ad` | high |  | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `traffic.alb-unhealthy-targets.prod-app-t/app-t-backend` | high |  | Target group k8s-prodcurt-curtainc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.prod-app-y/app-y-frontend` | high |  | Target group k8s-prodinse-insertoo-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.alb-unhealthy-targets.prod-app-z-backend/app-z-backend` | high |  | Target group k8s-prodrhem-appnbac-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0 … |
| `traffic.alb-unhealthy-targets.prod-app-v/app-v-frontend` | high |  | Target group k8s-prodtoot-appkf-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0 … |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | high |  | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['<load-balancer>.elb.amazonaws.com'], sourceRanges None … |
| `vpccni.no-available-ip.node-1-116` | high |  | node node-1-116 (t8i.small, pool system-ondemand): ipamd answered 'no available IP' 1 times since it started; pod IPs 6/9 (0.667), ENI 3/3, max-pods 11 |

(consecutive-run counts need diff.json; none for this snapshot)

## 3. Changes since the previous run of this mode

No earlier full snapshot to compare with.

### 3-1. Why things changed

This is the first full audit of this cluster, so there is nothing to compare with.

## 4. Detail per area

(not written this run)

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
- Not collected in full mode 0: none
- Skipped or errored 3: `observability.fluentbit-output-errors` (skip: summary.logs.agents.fluent-bit missing), `traffic.ingress-nginx-vulnerable-version` (skip: summary.traffic.nginx missing), `traffic.ingress-nginx-retired` (skip: summary.traffic.nginx missing)
- Judged in part 23 (some targets lacked what the rule needs; those are not judged, not passed): `node.kernel-oom-node-level` (2 not judged: node not read (2)), `node.kernel-lockup` (2 not judged: node not read (2)), `node.kernel-io-fs-errors` (2 not judged: node not read (2)), `node.kernel-nic-events` (2 not judged: node not read (2)), `node.conntrack-table-full` (2 not judged: node not read (2)), `node.kernel-net-mem-pressure` (2 not judged: node not read (2)), `node.cgroup-v1` (2 not judged: node not read (2)), `node.sysctl-tuning` (2 not judged: node not read (2)), `node.cri-not-ready` (2 not judged: node not read, or cri not read (2)), `node.cri-exited-containers` (2 not judged: node not read (2)), `node.service-restarts` (2 not judged: node not read (2)), `node.reboot-required` (2 not judged: node not read (2)), `node.os-updates-pending` (2 not judged: node not read (2)), `node.kubelet-reserved-missing` (2 not judged: node not read, or kubelet not read (2)), `node.kubelet-eviction-memory-missing` (2 not judged: node not read, or kubelet not read (2)), `node.clock-unsynced-os` (2 not judged: node not read (2)), `node.zombie-processes` (2 not judged: node not read (2)), `node.kubelet-api-qps-low` (2 not judged: node not read, or kubelet not read (2)), `node.docker-and-containerd` (2 not judged: node not read (2)), `node.container-writable-layer-large` (2 not judged: node not read (2)), `node.large-images` (2 not judged: node not read (2)), `vpccni.no-available-ip` (2 not judged: VPC CNI metrics not read (awscni_no_available_ip_addresses) (2)), `vpccni.ec2-api-errors` (2 not judged: metrics not read (2))
- Query returned no series 3 (every metric name the query reads has series, so nothing happened; a name with no series would be a skip): `observability.scrape-targets-down`, `controlplane.apiserver-401-rate`, `scaling.pod-pending-long`

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 | node-os |  |
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
| keda | 2 |  | operator-metrics (container arg --enable-prometheus-metrics=false: no metrics is expected) |
| kube-proxy | 2 | proxy-mode |  |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| loki | 9 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| promtail | 0 |  | no collect.yaml (collector not implemented) |
| victoria-metrics | 0 |  | no collect.yaml (collector not implemented) |
| vpc-cni | 3 | ipamd-metrics, ipamd-log |  |

Kinds this cluster does not serve (7; a check that needs one of them is skipped, not passed): `certificates.cert-manager.io`, `clusterissuers.cert-manager.io`, `horizontalrunnerautoscalers.actions.summerwind.dev`, `issuers.cert-manager.io`, `runnerdeployments.actions.summerwind.dev`, `volumesnapshotclasses.snapshot.storage.k8s.io`, `volumesnapshots.snapshot.storage.k8s.io`

652 commands, 299.1 s. Failed steps: 6: `core.node-os` ; `eks-platform.kubelet-journal` ; `eks-platform.containerd-journal` ; `kube-proxy.proxy-mode` ; `vpc-cni.ipamd-metrics` ; `vpc-cni.ipamd-log` 

Commands that failed inside a step that still succeeded (run.log): 9: `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers); `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-psh2b.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `alb-controller.controller-metrics.aws-load-balancer-controller-dbcd6944f-svnmr.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `argocd.application-controller-metrics.argocd-application-controller-0.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `ecr.lifecycle-policy.bitnami/kafka` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.bitnami/mysql` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `ecr.lifecycle-policy.app-v` An error occurred (LifecyclePolicyNotFoundException) when calling the GetLifecyclePolicy operation: Lifecycle policy …; `karpenter.controller-metrics.karpenter-9769889bd-nphgs.node.node-2-60` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore; `karpenter.controller-metrics.karpenter-9769889bd-pkxd2.node.node-1-117` node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore

Deprecated-API tools: kubent 28 of 41 Lists answered (13 refused or not served); pluto 95 of 95 object kinds saved (0 not permitted or failed); kubent had 131 objects with a last-applied annotation to judge; pluto had 264 objects with a last-applied annotation to judge.

### 7-2. Checks evaluated

367 checks: disabled 3, done 359, llm 2, skip 3. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.1, 30 files, 20959 lines scanned (components: alb-controller, argocd, ebs-csi, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, loki, metrics-server, prometheus, promtail, vpc-cni). Unclassified error lines: 35.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| karpenter.version-unsupported | karpenter | platform | high | warn | 1 | 2026-11-14T08:53:35Z , 2026-11-14T08:53:35Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T08:53:35.259616003Z … |
| ebs-csi.snapshot-crd-missing | ebs-csi | storage | medium | warn | 1500 | 2026-11-14T12:30:01Z , 2026-11-14T17:11:58Z | [pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:01.661807592Z W1114 12:30:01.661676       1 reflector.go:561] … |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 8 | 2026-11-13T22:48:26Z , 2026-11-14T03:04:56Z | [pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-13T22:48:26.038754342Z E1113 22:48:26.038622       1 scraper.go:149] "Failed to scrape node" … |
| containerd.shim-error | containerd | node | medium | info | 2 | 2026-11-13T17:26:28Z , 2026-11-13T17:26:28Z | 2026-11-13T17:26:28+0000 node-2-249 containerd[3609]: time="2026-11-13T17:26:28.218110263Z" level=warning msg="cleaning up … |
| karpenter.spot-interruption | karpenter | resilience | low | warn | 6 | 2026-11-13T22:47:26Z , 2026-11-14T03:04:07Z | [pod/karpenter-9769889bd-pkxd2/controller] 2026-11-13T22:47:26.757771911Z … |

| Normalized message | Count | Files |
|---|---|---|
| grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=owner@lab-k.example fromAlert=false t=<ts> … | 8 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver not found on node … | 4 | logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log, logs/pods/ebs-csi/kube-system_ebs-csi-node.log |
| kube-proxy \| "Kube-proxy configuration may be incomplete or incorrect" err="nodePortAddresses is unset; NodePort connections will be accepted on all … | 2 | logs/pods/kube-proxy/kube-system_kube-proxy.log |
| node:node-1-224 \| time="<ts>" level=error msg="failed to load cni during init, please check CRI plugin status before setting up network for pods" error="cni … | 2 | logs/node/node-1-224/containerd-24h.log |
| node:node-1-224 \| "Eviction manager: failed to get summary stats" err="failed to get node info: node \"ip-10-0-1-<n>.ap-northeast-2.compute.internal\" not … | 2 | logs/node/node-1-224/kubelet-24h.log |
| node:node-1-65 \| time="<ts>" level=error msg="failed to load cni during init, please check CRI plugin status before setting up network for pods" error="cni … | 2 | logs/node/node-1-65/containerd-24h.log |
| node:node-1-65 \| "Eviction manager: failed to get summary stats" err="failed to get node info: node \"node-1-65\" not … | 2 | logs/node/node-1-65/kubelet-24h.log |
| node:node-1-224 \| time="<ts>" level=error msg="failed to reload cni configuration after receiving fs change event(WRITE         … | 1 | logs/node/node-1-224/containerd-24h.log |
| node:node-1-224 \| {"level":"error","ts":"<ts>","caller":"awsutils/awsutils.go:<n>","msg":"r8gd.medium: instance type does not exist"} | 1 | logs/node/node-1-224/ipamd-24h.log |
| node:node-1-224 \| "RuntimeConfig from runtime service failed" err="rpc error: code = Unimplemented desc = unknown method RuntimeConfig for service … | 1 | logs/node/node-1-224/kubelet-24h.log |
| node:node-1-224 \| "Error getting the current node from lister" err="node \"ip-10-0-1-<n>.ap-northeast-2.compute.internal\" not found" | 1 | logs/node/node-1-224/kubelet-24h.log |
| node:node-1-224 \| "eviction manager: failed to check if we have separate container filesystem. Ignoring." err="no imagefs label for configured runtime" | 1 | logs/node/node-1-224/kubelet-24h.log |
| node:node-1-224 \| "Error updating node status, will retry" err="error getting node \"ip-10-0-1-<n>.ap-northeast-2.compute.internal\": node … | 1 | logs/node/node-1-224/kubelet-24h.log |
| node:node-1-65 \| "RuntimeConfig from runtime service failed" err="rpc error: code = Unimplemented desc = unknown method RuntimeConfig for service … | 1 | logs/node/node-1-65/kubelet-24h.log |
| node:node-1-65 \| "Error getting the current node from lister" err="node \"node-1-65\" not found" | 1 | logs/node/node-1-65/kubelet-24h.log |
| node:node-1-65 \| "eviction manager: failed to check if we have separate container filesystem. Ignoring." err="no imagefs label for configured runtime" | 1 | logs/node/node-1-65/kubelet-24h.log |
| node:node-1-65 \| "Error updating node status, will retry" err="error getting node \"node-1-65\": node … | 1 | logs/node/node-1-65/kubelet-24h.log |
| node:node-1-65 \| Error while processing event … | 1 | logs/node/node-1-65/kubelet-24h.log |
| node:node-2-249 \| time="<ts>" level=error msg="ContainerStatus for \"903248a58add682ae3459b665f034b0b56f26badbe2df8fd793c2af4a420c744\" failed" error="rpc … | 1 | logs/node/node-2-249/containerd-24h.log |
| node:node-2-249 \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container … | 1 | logs/node/node-2-249/kubelet-24h.log |

### 7-4. Raw files the LLM read directly

(not written this run)

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `resilience.no-backup.cluster` | fail | critical | no backup tool (family backup). Alternative signals: etcd snapshots 0, backup-like CronJobs that ran in the last 7 days [], VolumeSnapshots 0. If signals exist, the LLM checks whether copies leave the node |
| `controlplane.scheduler-unschedulable.prod-app-x/app-x-api` | fail | high | 24h 'Unable to schedule pod; no fit' 39 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption: disrupting}, <n> Insufficient cpu, <n> node(s) didn… |
| `controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-backend` | fail | high | 24h 'Unable to schedule pod; no fit' 26 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption: disrupting}, <n> Insufficient cpu, <n> node(s) didn… |
| `controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-embedding-server` | fail | high | 24h 'Unable to schedule pod; no fit' 26 times (control plane log). Top reason from summary.controlplane.scheduler.reasons: <n>/<n> nodes are available: <n> node(s) had untolerated taint {karpenter.sh/disruption: disrupting}, <n> Insufficient cpu, <n> node(s) didn… |
| `eks.no-backup-policy.cluster` | fail | high | dlm get-lifecycle-policies Policies 0, backup list-backup-plans 0. In-cluster backup tools: {'etcd_snapshots': 0, 'backup_cronjobs': [], 'stale_backup_cronjobs': [], 'volume_snapshots': 0, 'any': False} |
| `eks.public-endpoint-open.cluster` | fail | high | public True, private True, allowed CIDRs ['0.0.0.0/0'] |
| `karpenter.ec2nodeclass-al2.cluster` | fail | high | EC2NodeClass 1 total, amiFamily AL2 ['default'], AMI families ['AL2'], AMI not pinned (auto-tracks latest) ['default'] |
| `observability.failure-mode-uncovered.OOMKill` | fail | high | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | high | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/loki-stack` | fail | high | emptyDir volumes: tmp, storage, replicas 1 |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.32.13-eks-577a51e: EKS end of standard support 2026-03-23, 237 days past; upstream end of life 2026-02-28 |
| `platform.karpenter-version-compat.cluster` | fail | high | Karpenter 0.37.0 supports Kubernetes 1.23 to 1.30 (table row 0.37), the cluster runs 1.32.  |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.34, 24 h or the pod's life 0.34: throttled through the day |
| `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: last termination reason OOMKilled, finished at 2026-11-14T14:34:30Z (0.1 days ago), 3 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.networkpolicy-not-enforced.cluster` | fail | high | 3 NetworkPolicies (['prod-app-t', 'prod-app-x', 'prod-app-r']), enforced False: aws-eks-nodeagent --enable-network-policy=false, 0 PolicyEndpoints |
| `security.plaintext-secret-env.prod-app-z-backend/deployment/app-ad:tailscale` | fail | high | Container tailscale env ['TS_KUBE_SECRET'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | high | Container neo4j env ['NEO4J_AUTH'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.prod-app-z-backend/deployment/app-ad` | fail | high | ["hostPath ['dev-net-tun']", 'capabilities ["tailscale:[\'NET_ADMIN\']"]'], containers allowing root ['tailscale', 'forwarder'] |
| `traffic.alb-unhealthy-targets.prod-app-t/app-t-backend` | fail | high | Target group k8s-prodcurt-curtainc-bb495c72c8 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-t-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-y/app-y-frontend` | fail | high | Target group k8s-prodinse-insertoo-032c25d752 (application, port 3003): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-y-frontend'] |
| `traffic.alb-unhealthy-targets.prod-app-z-backend/app-z-backend` | fail | high | Target group k8s-prodrhem-appnbac-8c88bb317a (application, port 8000): healthy 0 of 2 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [404]': 2}, 24h UnHealthyHostCount max 2.0, health check / expected codes 200, backends ['deployment/app-z-backend'] |
| `traffic.alb-unhealthy-targets.prod-app-v/app-v-frontend` | fail | high | Target group k8s-prodtoot-appkf-36f816b829 (application, port 3000): healthy 0 of 1 targets, unhealthy {'Target.ResponseCodeMismatch: Health checks failed with these codes: [307]': 1}, 24h UnHealthyHostCount max 1.0, health check / expected codes 200, backends ['deployment/app-v-frontend'] |
| `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` | fail | high | loadbalancer middleware/kafka-controller-0-external: ports [9094, 443], exposure internet-facing, addresses ['<load-balancer>.elb.amazonaws.com'], sourceRanges None, security group open to 0.0.0.0/0 on 9094. DB port open to the internet by the … |
| `vpccni.no-available-ip.node-1-116` | fail | high | node node-1-116 (t8i.small, pool system-ondemand): ipamd answered 'no available IP' 1 times since it started; pod IPs 6/9 (0.667), ENI 3/3, max-pods 11 |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `eks.service-quota-near-limit.aws-account` | warn | high | quotas with a usage metric 25/65, at 80% or more [], at 60% or more ['VPCs 0.6'], top operational quotas [['VPCs', 3.0, 5.0, 0.6], ['listener rules per ALB', 37.0, 100.0, 0.37], ['certificates per ALB', 9.0, 25.0, 0.36], ['target groups per ALB', 30.0, 100.0, 0.3], ['NLBs', 2.0, 50.0, 0.04] … |
| `karpenter.ec2nodeclass-hardening.cluster` | warn | high | IMDS hop limit 2 or more ['default'], tokens optional [], root volume encrypted not set ['default'] (size {'default': 50.0}GB) |
| `logs.signatures.karpenter.version-unsupported` | warn | high | 1 occurrences (2026-11-14T08:53:35Z ~ 2026-11-14T08:53:35Z), thresholds warn 1/fail 10. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T08:53:35.259616003Z … |
| `node.disk-usage.10.0.1.138:9100:/` | warn | high | usage 0.80 |
| `node.disk-usage.10.0.1.21:9100:/` | warn | high | usage 0.76 |
| `observability.failure-mode-uncovered.Scheduling failure` | warn | high | user symptom: new pods do not start. No alert rule covers this failure mode |
| `observability.failure-mode-uncovered.VPC CNI IP exhaustion` | warn | high | user symptom: pods Pending without network. No alert rule covers this failure mode |
| `observability.no-slo.cluster` | warn | high | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'] known issue #15 |
| `observability.no-symptom-alerts.cluster` | warn | high | 157 alert rules: symptom 0, cause 138, app metrics (assumed symptom) 14. Symptom ratio 0.0. Symptom rules: [] |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.731 (limit 1536Mi), active series 177943, Prometheus container last terminated OOMKilled True (2026-11-14T14:34:30Z), restarts 3, OOMKilled containers in the monitoring namespace ['prometheus-kube-prometheus-stack-prometheus-0/prometheus'], restarts over 7 days … |
| `resilience.replicas-same-node.prod-app-w/deployment/app-w` | warn | high | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-1-21': 1 … |
| `resilience.replicas-same-node.prod-app-x/deployment/app-x-api` | warn | high | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-1-65': 1 … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-ai` | warn | high | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 3 (Running 3), node distribution {'node-1-21': 1 … |
| `resilience.replicas-same-node.prod-app-y/deployment/app-y-backend` | warn | high | the replicas are on different nodes now, but nothing declares that they must be (no topologySpread, no podAntiAffinity), so a reschedule may put them on one. replicas 2 (Running 2), node distribution {'node-1-138': 1 … |
| `resilience.restarts-crashloop.argocd/argocd-application-controller-0:application-controller` | warn | high | 42 restarts, state Running, last termination OOMKilled (exit 137) 2026-10-30T09:00:04Z, cause class OOM (memory limit), Unhealthy events 0, node reboot time None |
| `resources.cpu-throttling.prod-app-v/deploy/app-v-frontend:frontend` | warn | high | pod app-v-frontend-64c9f4f4b5-cdzsr: throttling ratio now 0.00, 24 h or the pod's life 0.11: throttled through the day, below the fail line; no 5-minute value, under 0.01 now |
| `resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail` | warn | high | pod loki-stack-promtail-dc9mw: 7d memory working set p95 / limit = 0.82 |
| `resources.oomkilled-repeated.monitoring/sts/loki-stack:loki` | warn | high | kernel log: 1 kill in 24 h on 1 of 1 node read. Prometheus: 1 pod ended by OOM in 7 days, 2 restarts in those pods. cAdvisor counter 0. Running now: loki-stack-0 (created 2026-11-13T07:04:17Z, 2 restarts of this container since, its previous run ended 2026-11-13T07:28:48Z with reason Completed … |
| `resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | kernel log not read on its node, no node access there. Prometheus: 1 pod ended by OOM in 7 days, 1 restarts in those pods. cAdvisor counter 1. Running now: prometheus-kube-prometheus-stack-prometheus-0 (created 2026-09-08T12:47:49Z, 3 restarts of this container since, its previous run ended … |
| `resources.oomkilled.argocd/sts/argocd-application-controller:application-controller` | warn | high | pod argocd-application-controller-0: last termination reason OOMKilled, finished at 2026-10-30T09:00:04Z (15.3 days ago), 42 restarts. An OOM older than 7 days is warn, older than 30 days is excluded |
| `security.imds-hop-limit.cluster` | warn | high | Of 9 instances, 9 with IMDS hop limit > 1 or tokens optional: {'hop=2 tokens=required': 9}. Examples [('system_core', 'm5.large', 2, 'required'), ('system_core', 'm5.large', 2, 'required'), ('karpenter-node', 't8i.medium', 2, 'required'), ('karpenter-node', 'm7i-flex.large', 2, 'required')] and 5 … |
| `traffic.db-exposed.nlb/app-u-db-shared` | warn | high | nlb (defined outside the cluster) /app-u-db-shared: ports [3307, 3308, 3309, 3311, 5432, 5433, 6379, 7687], exposure internet-facing, addresses ['<load-balancer>.elb.amazonaws.com'], sourceRanges None, security group allow-list, at most 4 sources per port, widest … |
| `vpccni.node-ip-exhaustion.node-1-116` | warn | high | node node-1-116 (t8i.small, pool system-ondemand): pod IPs 6/9 (0.667), ENI 3/3 (at limit True), 'no available IP' events 1, max-pods 11, prod pods 1. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-1-21` | warn | high | node node-1-21 (r8gd.large, pool default): pod IPs 23/27 (0.852), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 29, prod pods 16. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-1-224` | warn | high | node node-1-224 (r8gd.medium, pool default): pod IPs 3/6 (0.5), ENI 2/2 (at limit True), 'no available IP' events 0, max-pods 8, prod pods 1. prefix delegation False |
| `vpccni.node-ip-exhaustion.node-2-249` | warn | high | node node-2-249 (t8i.medium, pool system-ondemand): pod IPs 12/15 (0.8), ENI 3/3 (at limit True), 'no available IP' events 0, max-pods 17, prod pods 2. prefix delegation False |
| `argocd.default-project-wildcard.cluster` | fail | medium | AppProjects 1, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 9/9 (prod 8) |
| `cost.idle-compute-high.cluster` | fail | medium | Node compute monthly estimate 432.61 USD (on-demand list price, current spot price), of which idle 409.74 USD (0.95), by pool {'system-ondemand': 154.26, 'nodegroup:system_core-20251217040546303900000001': 172.28, 'default': 106.06}, 26.41 USD per core-month. Spot node share 0.44, spot savings … |
| `cost.request-waste.cluster` | fail | medium | CPU request total 8.43 cores -> KRR recommendation 2.19 cores, reducible 6.24 cores ~ 164.8 USD/month |
| `ebscsi.storageclass-unencrypted.cluster` | fail | medium | ebs.csi.aws.com StorageClasses 4, without encrypted ['gp3', 'gp3-2a', 'gp3-2c'] (default class gp3), in-tree leftovers ['gp2'], without allowVolumeExpansion ['gp2', 'gp3', 'gp3-2a', 'gp3-2c'] |
| `ecr.scan-disabled.ecr/registry/<account>` | fail | medium | registry scanning BASIC (rules 0), repositories with scanOnPush off 31/33 (used by prod 25: ['ecr-app-w-eks-prod', 'ecr-app-t-backend-eks-prod', 'ecr-app-t-web-eks-prod', 'ecr-app-r-postgresql-prod', 'ecr-app-s-admin-eks-prod', 'ecr-app-t-postgresql-prod'] and 19 more) … |
| `eks.addon-outdated.aws-ebs-csi-driver` | fail | medium | installed v1.37.0-eksbuild.1, latest available v1.68.0-eksbuild.1, default v1.68.0-eksbuild.1 |
| `eks.addon-outdated.vpc-cni` | fail | medium | installed v1.19.0-eksbuild.1, latest available v1.23.3-eksbuild.1, default v1.22.4-eksbuild.14 |
| `eks.extended-support.cluster` | fail | medium | version 1.32, supportType EXTENDED, status EXTENDED_SUPPORT, end of standard support 2026-03-23T09:00:00+09:00, end of extended support 2027-03-23T09:00:00+09:00 |
| `eks.node-os-skew.cluster` | fail | medium | OS ['Amazon Linux 2', 'Amazon Linux 2023.9.20251208'], kernels ['5.10.245-245.983.amzn2.aarch64', '5.10.245-245.983.amzn2.x86_64', '6.1.158-180.294.amzn2023.x86_64'], runtimes ['containerd://1.7.29', 'containerd://2.1.5'], cgroup: AL2 may be v1, AL2023 is v2 |
| `eks.nodegroup-ami-old.nodegroups` | fail | medium | node groups 1, max AMI age 341 days, over 90 days ['system_core-20251217040546303900000001 341d'], over 180 days ['system_core-20251217040546303900000001'], health issues [] |
| `eks.ssm-unregistered.node-1-117` | fail | medium | instance i-0141cf1ef71b07012 is missing from ssm describe-instance-information or not Online |
| `eks.ssm-unregistered.node-2-60` | fail | medium | instance i-0fce7d18322427934 is missing from ssm describe-instance-information or not Online |
| `eso.provider-api-errors.cluster` | fail | medium | provider API calls since controller start: success 2860 / errors 168 (ratio 0.0555), sync failures 168/6342, reconcile errors 168, ExternalSecrets not Ready [] (oldest refresh None hours ago) |
| `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility` | fail | medium | Amazon Linux 2 compatibility (UPGRADE_READINESS, k8s 1.33): ERROR — Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ |
| `hygiene.mutable-image-tag.prod-app-z-backend/deployment/app-ad:tailscale` | fail | medium | image tailscale/tailscale:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.polaris-reliability-danger.prod-app-z-backend/deployment/app-ad` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'memoryLimitsMissing', 'memoryRequestsMissing'] and 6 more. Security-category danger ['dangerousCapabilities' … |
| `observability.alert-firing-stale.KubeControllerManagerDown` | fail | medium | Firing for 67.2 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alert-firing-stale.KubeSchedulerDown` | fail | medium | Firing for 67.2 days (ALERTS_FOR_STATE). Labels {'severity': 'critical'} |
| `observability.alerts-always-firing.CPUThrottlingHigh` | fail | medium | 7d firing samples 29714 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeControllerManagerDown` | fail | medium | 7d firing samples 20157 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodNotReady` | fail | medium | 7d firing samples 71218 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeSchedulerDown` | fail | medium | 7d firing samples 20157 (same level as Watchdog = never stops firing) |
| `observability.log-coverage-gap.cluster` | fail | medium | Of 131 pods Running for over 1h, 83 are absent from Loki pod labels (ratio 0.634). Nodes with every pod missing: []. By namespace: {'kube-system': 29, 'monitoring': 24, 'prod-app-z-backend': 5, 'middleware': 4, 'keda': 3, 'prod-app-s': 3, 'argocd': 2, 'dev-app-s': 2, 'karpenter': 2 … |
| `observability.no-event-retention.cluster` | fail | medium | no component of family event-retention in inventory.components |
| `resilience.db-probe-timeout.prod-app-s/statefulset/app-s-backend-mysql:mysql` | fail | medium | prod-app-s/statefulset/app-s-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-y/statefulset/app-y-backend-mysql:mysql` | fail | medium | prod-app-y/statefulset/app-y-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | medium | prod-app-z-backend/statefulset/app-z-neo4j container neo4j: liveness tcpSocket timeout 1s, period 30s, failureThreshold 3, readiness tcpSocket timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | fail | medium | prod-app-v/statefulset/app-v-backend-prod-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.no-pdb.prod-app-x/app-x-api` | fail | medium | replicas 2, no PDB selects these pods |
| `resilience.no-pdb.prod-app-y/app-y-ai` | fail | medium | replicas 3, no PDB selects these pods |
| `resilience.no-pdb.prod-app-y/app-y-backend` | fail | medium | replicas 2, no PDB selects these pods |
| `resilience.no-readiness-probe.prod-app-y/app-y-admin` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-y/app-y-ai` | fail | medium | containers without a readinessProbe: ai |
| `resilience.no-readiness-probe.prod-app-y/app-y-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-y/app-y-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.no-readiness-probe.prod-app-z-backend/app-ad` | fail | medium | containers without a readinessProbe: tailscale, forwarder |
| `resilience.no-readiness-probe.prod-app-v/app-v-admin-frontend` | fail | medium | containers without a readinessProbe: admin |
| `resilience.no-readiness-probe.prod-app-v/app-v-backend` | fail | medium | containers without a readinessProbe: backend |
| `resilience.no-readiness-probe.prod-app-v/app-v-frontend` | fail | medium | containers without a readinessProbe: frontend |
| `resilience.recreate-strategy-serving.prod-app-r/deployment/app-r-backend` | fail | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.replicas-same-zone.prod-app-w/deployment/app-w` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-21': 1, 'node-1-138': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-x/deployment/app-x-api` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-65': 1, 'node-1-224': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-s/deployment/app-s-api` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-21': 1, 'node-1-138': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-s/deployment/app-s-backend` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-21': 1, 'node-1-138': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-s/deployment/app-s-frontend` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-138': 1, 'node-1-21': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-y/deployment/app-y-ai` | fail | medium | replicas 3, AZ distribution {'ap-northeast-2a': 3}, node distribution {'node-1-21': 1, 'node-1-138': 2}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-y/deployment/app-y-backend` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-138': 1, 'node-1-21': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-backend` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-138': 1, 'node-1-65': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-embedding-server` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-138': 1, 'node-1-65': 1}, topologySpread [] |
| `resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-frontend` | fail | medium | replicas 2, AZ distribution {'ap-northeast-2a': 2}, node distribution {'node-1-21': 1, 'node-1-138': 1}, topologySpread [] |
| `resilience.single-node-dependency.prod-app-z-backend/deployment/app-ad` | fail | medium | ["hostPath volume ['dev-net-tun']"], replicas 1 |
| `resilience.single-replica-in-prod.prod-app-t/app-t-ai` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-studio` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-t/app-t-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-s/app-s-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-y/app-y-admin` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-y/app-y-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-z-backend/app-z-pg-proxy` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-z-backend/app-ad` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-r/app-r-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-r/app-r-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-admin-frontend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-backend` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.prod-app-v/app-v-frontend` | fail | medium | replicas 1, no HPA |
| `resources.besteffort-in-prod.prod-app-z-backend/deploy/app-ad` | fail | medium | pod app-ad-79d68875b9-99csc: QoS BestEffort (neither request nor limit) |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-backend:backend` | fail | medium | pod app-z-backend-96ffd6ff7-hrbn6: 7d CPU p95 0.002 cores / request 0.50 cores = 0.00 |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | fail | medium | pod app-z-embedding-server-846dc84758-rkvzg: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00 |
| `resources.cpu-request-overprovisioned.prod-app-r/deploy/app-r-backend:backend` | fail | medium | pod app-r-backend-79b898dbbb-7r2kz: 7d CPU p95 0.001 cores / request 0.50 cores = 0.00 |
| `resources.jvm-heap-vs-limit.middleware/statefulset/kafka-controller:jmx-exporter` | fail | medium | middleware/statefulset/kafka-controller container jmx-exporter (jmx-exporter:0.20.0-debian-11-r4): -Xmx NoneMiB, MaxRAMPercentage 100.0, memory limit 128.0MiB -> heap/limit 1.0 (heap unset False) |
| `resources.krr-recommendation.monitoring/statefulset/loki-stack:loki` | fail | medium | memory request under by 295 MB: CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 551 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 929 MB: CPU request 0.2 → 0.146 cores, CPU limit 0.5 → none, memory request 800 → 1729 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/vm-single:vmsingle` | fail | medium | CPU request over by 0.29 cores: CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 287 MB, memory limit 1024 → 287 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-ai:ai` | fail | medium | memory request under by 385 MB: CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 641 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.prod-app-x/deployment/app-x-api:api` | fail | medium | memory request under by 791 MB, CPU request over by 0.49 cores: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 1024 → 1815 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.prod-app-s/deployment/app-s-frontend:frontend` | fail | medium | memory request under by 297 MB: CPU request 0.01 → 0.043 cores, CPU limit 0.2 → none, memory request 128 → 425 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-s/statefulset/app-s-backend-mysql:mysql` | fail | medium | memory request under by 406 MB, CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 1174 MB, memory limit 1536 → 1174 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.prod-app-y/deployment/app-y-ai:ai` | fail | medium | memory request over by 963 MB: CPU request 0.03 → 0.01 cores, CPU limit 1.0 → none, memory request 2048 → 1085 MB, memory limit 4096 → 1085 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-embedding-server:embedding` | fail | medium | memory request under by 2651 MB, CPU request over by 0.358 cores: CPU request 0.5 → 0.142 cores, CPU limit 2.0 → none, memory request 4096 → 6747 MB, memory limit 6144 → 6747 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-file-worker:file-worker` | fail | medium | CPU request over by 0.703 cores, memory request over by 337 MB: CPU request 1.0 → 0.297 cores, CPU limit 2.0 → none, memory request 2048 → 1711 MB, memory limit 4096 → 1711 MB. KRR severity CRITICAL (CPU req CRITICAL, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker` | fail | medium | CPU request over by 0.458 cores, memory request over by 670 MB: CPU request 1.0 → 0.542 cores, CPU limit 2.0 → none, memory request 2048 → 1378 MB, memory limit 6144 → 1378 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/statefulset/app-z-neo4j:neo4j` | fail | medium | CPU request over by 0.49 cores, memory request over by 2417 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 4096 → 1679 MB, memory limit 5120 → 1679 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-r/deployment/app-r-backend:backend` | fail | medium | CPU request over by 0.348 cores: CPU request 0.5 → 0.152 cores, CPU limit 2.0 → none, memory request 1024 → 866 MB, memory limit 2048 → 866 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.large-request-binpacking.prod-app-z-backend/deploy/app-z-embedding-server:embedding` | fail | medium | ['pod app-z-embedding-server-846dc84758-rkvzg: request is 58% of the median node allocatable', 'pod app-z-embedding-server-846dc84758-sc79l: request is 58% of the median node allocatable'] |
| `resources.large-request-binpacking.prod-app-z-backend/sts/app-z-neo4j:neo4j` | fail | medium | pod app-z-neo4j-0: request is 58% of the median node allocatable |
| `resources.no-memory-limit.prod-app-z-backend/app-ad` | fail | medium | containers without a limit: tailscale, forwarder |
| `resources.node-memory-request-usage-gap.node-1-65` | fail | medium | memory requests/allocatable 0.91, working set/allocatable 7d p95 0.26 (instant 0.26) |
| `resources.node-request-usage-gap.node-1-138` | fail | medium | CPU requests/allocatable 0.89, usage/allocatable 7d p95 0.03 (5m instant 0.03) |
| `resources.node-request-usage-gap.node-1-21` | fail | medium | CPU requests/allocatable 0.86, usage/allocatable 7d p95 0.06 (5m instant 0.06) |
| `resources.node-request-usage-gap.node-1-65` | fail | medium | CPU requests/allocatable 0.91, usage/allocatable 7d p95 0.01 (5m instant 0.01) |
| `resources.node-request-usage-gap.node-2-60` | fail | medium | CPU requests/allocatable 0.94, usage/allocatable 7d p95 0.06 (5m instant 0.04) |
| `security.networkpolicy-coverage.cluster` | fail | medium | 14 of 17 user namespaces have no NetworkPolicy, of which production ['prod-app-w', 'prod-app-s', 'prod-app-y', 'prod-app-z-backend', 'prod-app-v']; with: ['prod-app-t', 'prod-app-x', 'prod-app-r'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 80. Security danger workloads 62 (prod 27): per check {'dangerousCapabilities': 2, 'hostNetworkSet': 2, 'privilegeEscalationAllowed': 47, 'runAsPrivileged': 2, 'runAsRootAllowed': 46, 'sensitiveContainerEnvVar': 2, 'hostPIDSet': 1, 'rolebindingClusterAdminRole': 2 … |
| `storage.csi-snapshot-unavailable.cluster` | fail | medium | VolumeSnapshot CRD False, VolumeSnapshots 0 (0 in 7 days), VolumeSnapshotClasses 0, EBS snapshots in 30 days 2 {'pre-delete backup of dev-app-v/data-to': 1, 'pre-delete backup of dev-app-y/data-': 1}, prod PVCs 7 |
| `storage.no-volume-expansion.gp3` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2a` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `storage.no-volume-expansion.gp3-2c` | fail | medium | allowVolumeExpansion False, provisioner ebs.csi.aws.com |
| `tenancy.prod-boundary-missing.prod-app-w` | fail | medium | prod-app-w: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-s` | fail | medium | prod-app-s: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-y` | fail | medium | prod-app-y: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-z-backend` | fail | medium | prod-app-z-backend: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 1. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-v` | fail | medium | prod-app-v: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `traffic.ingress-p95-latency.prod-app-s/app-s-api` | fail | medium | ['canary-api-v1.lab-l.example', 'api.v1.lab-l.example']: p95 request-weighted 3.0652s, hourly average 11.5366s, 1h max 23.4161s, latest hour with requests 0.0023s on 160.0 requests at 2026-11-14T16:11, 380.0 requests/24h (source alb-cloudwatch) |
| `traffic.shared-alb-group.alb-group/app-u-prod-lb` | fail | medium | ALB group app-u-prod-lb: 30 ingresses, 37 hosts, 12 namespaces ['argocd', 'dev-app-s', 'middleware', 'monitoring', 'prod-app-w', 'prod-app-t', 'prod-app-x', 'prod-app-s', 'prod-app-y', 'prod-app-z-backend', 'prod-app-r', 'prod-app-v'], kinds ['dev', 'other' … |
| `vpccni.prefix-delegation-off.cluster` | fail | medium | ENABLE_PREFIX_DELEGATION false, nitro nodes 9/9. nodes above 50% IP usage ['node-1-21', 'node-2-249', 'node-1-116', 'node-2-60' … |
| `albctl.reconcile-errors.cluster` | warn | medium | reconcile errors since leader start 44, apiserver 429/503 responses 126, max workqueue depth 0.0, Ingresses without an LB address [], stale TargetGroupBindings [] |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL https://deploy.lab-k.example |
| `argocd.components-not-ha.cluster` | warn | medium | components (ready/replicas) {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}, not ready [], single replica (server, repo-server) ['repo-server', 'server'], version … |
| `controlplane.apiserver-latency.PATCH` | warn | medium | PATCH p99 0.926s |
| `controlplane.controller-error-repeat.disruption.go` | warn | medium | 24h E lines 6 times (disruption.go). Samples: summary.controlplane.controller_manager.errors_by_count |
| `controlplane.controller-error-repeat.horizontal.go` | warn | medium | 24h E lines 5 times (horizontal.go). Samples: summary.controlplane.controller_manager.errors_by_count |
| `controlplane.controller-error-repeat.type.go` | warn | medium | 24h W lines 34470 times (type.go). Samples: summary.controlplane.controller_manager.errors_by_count |
| `coredns.nxdomain-ratio-high.cluster` | warn | medium | NXDOMAIN share of responses in 1h 0.557, queries per second 5.93, NXDOMAIN share of queries forwarded upstream 0.434 (upstreams ['<ip>:53']), pods with default ndots (5) 137, autopath False, cache hit ratio 0.2137 |
| `ecr.dockerhub-dependency.ecr/registry/<account>` | warn | medium | registry distribution of container images {'602401143452.dkr.ecr.ap-northeast-2.amazonaws.com': 77, '<account>.dkr.ecr.ap-northeast-2.amazonaws.com': 44, 'docker.io': 33, 'quay.io': 25, 'ghcr.io': 9, 'public.ecr.aws': 7, 'registry.k8s.io': 3}, docker.io images 18 (e.g. ['alpine/socat:1.8.0.0' … |
| `eks.addon-outdated.coredns` | warn | medium | installed v1.11.3-eksbuild.1, latest available v1.11.4-eksbuild.104, default v1.11.4-eksbuild.104 |
| `eks.addon-outdated.kube-proxy` | warn | medium | installed v1.32.0-eksbuild.2, latest available v1.32.13-eksbuild.72, default v1.32.13-eksbuild.72 |
| `eso.controller-single-replica.cluster` | warn | medium | controller 1/1, webhook 1/1 (Fail policy ['validate.externalsecret.external-secrets.io', 'validate.secretstore.external-secrets.io', 'validate.clustersecretstore.external-secrets.io']), cert-controller 1/1, --concurrent 1 |
| `grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana` | warn | medium | responses per datasource (cumulative since start) [('Loki(loki)', 327, {'200': 317, '429': 10}), ('Prometheus(prometheus)', 47, {'200': 46, '301': 1}), ('VictoriaMetrics_onprem(prometheus)', 7303, {'200': 7303})], error rate 1% or more ['Loki(loki)'] (max 0.0306), Grafana API 5xx 0/49007 |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-cool-down:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.arc-runners/cronjob/arc-warm-up:kubectl` | warn | medium | image bitnami/kubectl:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.mutable-image-tag.middleware/deployment/redis-insight:redis-insight` | warn | medium | image redis/redisinsight:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.node-label-dependency.app-u.ai/role` | warn | medium | Label app-u.ai/role: 29 workloads (production 8) depend on it via nodeSelector/affinity, present on 5/9 nodes — e.g. ['argocd/deployment/argocd-applicationset-controller', 'argocd/deployment/argocd-dex-server', 'argocd/deployment/argocd-notifications-controller'] and 26 more |
| `hygiene.node-label-dependency.workload-type` | warn | medium | Label workload-type: 28 workloads (production 24) depend on it via nodeSelector/affinity, present on 4/9 nodes — e.g. ['dev-app-s/deployment/app-s-admin', 'dev-app-s/deployment/app-s-api', 'dev-app-s/deployment/app-s-backend'] and 25 more |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-cool-down` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.arc-runners/cronjob/arc-warm-up` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.polaris-reliability-danger.middleware/deployment/redis-insight` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'deploymentMissingReplicas', 'livenessProbeMissing', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet'] and 2 more. Security-category danger ['privilegeEscalationAllowed' … |
| `karpenter.consistency-errors.cluster` | warn | medium | cluster state synced True, consistency errors 3, reconcile errors {}, pod startup average 29.9s (9779 pods), node termination average 14.4s |
| `keda.components-single-replica.cluster` | warn | medium | operator 1/1, metrics-apiserver 1/1, APIService v1beta1.external.metrics Available True, PDB False, prod ScaledObject 3 |
| `keda.prod-external-trigger-no-fallback.cluster` | warn | medium | prod external-trigger ScaledObjects without fallback ['prod-app-y/scaledobject/app-y-ai-kafka-lag', 'prod-app-z-backend/scaledobject/app-z-file-worker', 'prod-app-z-backend/scaledobject/app-z-graph-worker'], trigger types {'kafka': 2, 'metrics-api': 2}, minimum pollingInterval 15s |
| `logs.signatures.ebs-csi.snapshot-crd-missing` | warn | medium | 1500 occurrences (2026-11-14T12:30:01Z ~ 2026-11-14T17:11:58Z), thresholds warn 1/fail 100. Files: ['logs/pods/ebs-csi/kube-system_ebs-csi-controller.log']. Samples: ['[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:01.661807592Z W1114 12:30:01.661676       1 … |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 8 occurrences (2026-11-13T22:48:26Z ~ 2026-11-14T03:04:56Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-13T22:48:26.038754342Z E1113 22:48:26.038622       1 scraper.go:149] … |
| `loki.request-errors.monitoring/statefulset/loki-stack` | warn | medium | 0 5xx out of 976631 requests since start (by route {}, excluding /ready 503 during startup), panics 0, WAL disk full 0, error log lines 5736, rejected {} |
| `node.kernel-net-mem-pressure.node-2-149` | warn | medium | kernel log (since boot (dmesg; journald does not hold 24 hours)) BUG/Oops/Call Trace 0, network pressure (TCP memory, SYN flooding, ARP table) 1, memory pressure (page allocation failure) 0, unstable clocksource 0. Samples: ['[Sun Nov  8 10:39:26 2026] TCP: request_sock_TCP: Possible SYN flooding … |
| `node.network-errors.10.0.1.65:9100:eth0` | warn | medium | Node <ip>:9100 device eth0: 408 RX+TX errors in 24h |
| `observability.alert-firing-stale.CPUThrottlingHigh/monitoring` | warn | medium | Firing for 5.5 days (ALERTS_FOR_STATE). Labels {'namespace': 'monitoring', 'pod': 'prometheus-kube-prometheus-stack-prometheus-0', 'severity': 'info'} |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 157 alert rules, 40 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AlertmanagerFailedReload', 'AlertmanagerMembersInconsistent', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerClusterDown' … |
| `observability.promtail-dropped.cluster` | warn | medium | Lines dropped in 1h None, non-2xx sends None, active targets total None -- promtail metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured |
| `observability.slo-without-burn-rate.cluster` | warn | medium | SLO tools [], 0 sli/slo recording rules, slo-labelled rules ['ImageInferenceE2ESuccessRateDrop', 'ImageInferenceEntitlementFailureSpike', 'LoraTrainingSuccessRateDrop', 'LoraTrainingDurationP95High', 'LoraTrainingCallbackTimeout'], 0 burn rate alerts |
| `resilience.db-probe-timeout.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | medium | dev-app-s/statefulset/app-s-backend-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe present |
| `resilience.db-probe-timeout.monitoring/statefulset/loki-stack:loki` | warn | medium | monitoring/statefulset/loki-stack container loki: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 95, 'system-cluster-critical': 9, 'system-node-critical': 27}, prod pods without a class 42 of 42, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.prod-app-t/statefulset/app-t-backend-postgresql` | warn | medium | statefulset app-t-backend-postgresql (Service app-t-backend-postgresql, app-t-backend-postgresql-hl, PVC data-app-t-backend-postgresql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-x/statefulset/app-x-postgresql` | warn | medium | statefulset app-x-postgresql (Service app-x-postgresql, app-x-postgresql-hl, PVC data-app-x-postgresql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-s/statefulset/app-s-backend-mysql` | warn | medium | statefulset app-s-backend-mysql (Service app-s-backend-mysql, app-s-backend-mysql-headless, PVC data-app-s-backend-mysql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-y/statefulset/app-y-backend-mysql` | warn | medium | statefulset app-y-backend-mysql (Service app-y-backend-mysql, app-y-backend-mysql-headless, PVC data-app-y-backend-mysql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-z-backend/statefulset/app-z-neo4j` | warn | medium | statefulset app-z-neo4j (Service app-z-neo4j, PVC data-app-z-neo4j-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-r/statefulset/app-r-postgresql` | warn | medium | statefulset app-r-postgresql (Service app-r-postgresql, app-r-postgresql-hl, PVC data-app-r-postgresql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.prod-app-v/statefulset/app-v-backend-prod-mysql` | warn | medium | statefulset app-v-backend-prod-mysql (Service app-v-backend-prod-mysql, app-v-backend-prod-mysql-headless, PVC data-app-v-backend-prod-mysql-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.recreate-strategy-serving.monitoring/deployment/vmauth` | warn | medium | strategy Recreate (justification none), replicas 1, preStop False, grace 30s |
| `resilience.shell-pid1-no-prestop.middleware/statefulset/redis-master` | warn | medium | Containers whose command is sh -c ['redis', 'metrics'], no preStop, terminationGracePeriodSeconds 30 |
| `resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | medium | pod argocd-repo-server-d487895cc-g4nzz: 7d CPU p95 0.002 cores / request 0.20 cores = 0.01 |
| `resources.cpu-request-overprovisioned.argocd/sts/argocd-application-controller:application-controller` | warn | medium | pod argocd-application-controller-0: 7d CPU p95 0.035 cores / request 0.20 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend` | warn | medium | pod app-s-backend-5c455594cd-s87gg: 7d CPU p95 0.017 cores / request 0.10 cores = 0.17 |
| `resources.cpu-request-overprovisioned.dev-app-s/sts/app-s-backend-mysql:mysql` | warn | medium | pod app-s-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10; database-like: keep the request |
| `resources.cpu-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | medium | ['pod karpenter-9769889bd-nphgs: 7d CPU p95 0.000 cores / request 0.20 cores = 0.00', 'pod karpenter-9769889bd-pkxd2: 7d CPU p95 0.020 cores / request 0.20 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-7fc99cdd4d-jpng8: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-c5b6f8b88-jp4kd: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-54ffcbbfd6-2wtvl: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/aws-load-balancer-controller:aws-load-balancer-controller` | warn | medium | ['pod aws-load-balancer-controller-dbcd6944f-svnmr: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02', 'pod aws-load-balancer-controller-dbcd6944f-psh2b: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | ['pod coredns-c7dbf4744-cb76h: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07', 'pod coredns-c7dbf4744-lz5fs: 7d CPU p95 0.007 cores / request 0.10 cores = 0.07'] |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-65d4b7df64-xxfjs: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05 |
| `resources.cpu-request-overprovisioned.kube-system/ds/kube-proxy:kube-proxy` | warn | medium | ['pod kube-proxy-89jgp: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-gqdmf: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00', 'pod kube-proxy-snbf9: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01', 'pod kube-proxy-6g9r6: 7d CPU p95 0.000 cores / request 0.10 cores = … |
| `resources.cpu-request-overprovisioned.middleware/deploy/kafka-ui:kafka-ui` | warn | medium | pod kafka-ui-7cb8bcb988-5gchp: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.middleware/sts/kafka-controller:kafka` | warn | medium | pod kafka-controller-0: 7d CPU p95 0.064 cores / request 0.20 cores = 0.32; database-like: keep the request |
| `resources.cpu-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana` | warn | medium | pod kube-prometheus-stack-grafana-5d7c56949c-qspbz: 7d CPU p95 0.006 cores / request 0.10 cores = 0.06 |
| `resources.cpu-request-overprovisioned.monitoring/sts/loki-stack:loki` | warn | medium | pod loki-stack-0: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08; database-like: keep the request |
| `resources.cpu-request-overprovisioned.monitoring/sts/vm-single:vmsingle` | warn | medium | pod vm-single-0: 7d CPU p95 0.009 cores / request 0.30 cores = 0.03; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-t/deploy/app-t-ai:ai` | warn | medium | pod app-t-ai-f69d6d448-7hpcq: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql` | warn | medium | pod app-t-backend-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-x/sts/app-x-postgresql:postgresql` | warn | medium | pod app-x-postgresql-0: 7d CPU p95 0.004 cores / request 0.10 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-s/sts/app-s-backend-mysql:mysql` | warn | medium | pod app-s-backend-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend` | warn | medium | ['pod app-y-backend-596479b6f8-ggksl: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod app-y-backend-596479b6f8-ppqmd: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10'] |
| `resources.cpu-request-overprovisioned.prod-app-y/sts/app-y-backend-mysql:mysql` | warn | medium | pod app-y-backend-mysql-0: 7d CPU p95 0.009 cores / request 0.20 cores = 0.04; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend` | warn | medium | pod app-z-frontend-6d58bbfcfc-z9qmc: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
| `resources.cpu-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j` | warn | medium | pod app-z-neo4j-0: 7d CPU p95 0.004 cores / request 0.50 cores = 0.01; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-r/sts/app-r-postgresql:postgresql` | warn | medium | pod app-r-postgresql-0: 7d CPU p95 0.005 cores / request 0.10 cores = 0.05; database-like: keep the request |
| `resources.cpu-request-overprovisioned.prod-app-v/sts/app-v-backend-prod-mysql:mysql` | warn | medium | pod app-v-backend-prod-mysql-0: 7d CPU p95 0.010 cores / request 0.20 cores = 0.05; database-like: keep the request |
| `resources.krr-recommendation.argocd/deployment/argocd-repo-server:repo-server` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 304 MB, memory limit 1024 → 304 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.argocd/statefulset/argocd-application-controller:application-controller` | warn | medium | memory request under by 227 MB, CPU request over by 0.144 cores: CPU request 0.2 → 0.056 cores, CPU limit 0.5 → none, memory request 384 → 611 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | medium | memory request under by 114 MB: CPU request 0.1 → 0.012 cores, CPU limit 0.5 → none, memory request 512 → 626 MB, memory limit 1024 → 626 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.karpenter/deployment/karpenter:controller` | warn | medium | memory request under by 189 MB, CPU request over by 0.177 cores: CPU request 0.2 → 0.023 cores, CPU limit 0.5 → none, memory request 256 → 445 MB. KRR severity WARNING (CPU req OK, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.middleware/statefulset/kafka-controller:kafka` | warn | medium | CPU request over by 0.131 cores: CPU request 0.2 → 0.069 cores, CPU limit 0.5 → none, memory request 1536 → 1487 MB, memory limit 2048 → 1487 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/daemonset/loki-stack-promtail:promtail` | warn | medium | memory request under by 117 MB: CPU request 0.05 → 0.018 cores, CPU limit 0.1 → none, memory request 128 → 245 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-backend:backend` | warn | medium | memory request under by 203 MB: CPU request 0.05 → 0.046 cores, CPU limit 0.5 → none, memory request 192 → 395 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-t/deployment/app-t-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-s/deployment/app-s-backend:backend` | warn | medium | memory request under by 224 MB: CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 352 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-y/deployment/app-y-backend:backend` | warn | medium | memory request over by 340 MB: CPU request 0.1 → 0.01 cores, CPU limit 2.0 → none, memory request 512 → 172 MB, memory limit 2048 → 172 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-y/statefulset/app-y-backend-mysql:mysql` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 1.0 → none, memory request 768 → 740 MB, memory limit 1536 → 740 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-backend:backend` | warn | medium | memory request over by 410 MB: CPU HPA detected, memory request 1024 → 614 MB, memory limit 2048 → 614 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.prod-app-z-backend/deployment/app-z-pg-proxy:forwarder` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-r/deployment/app-r-web:web` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.prod-app-v/deployment/app-v-backend:backend` | warn | medium | memory request under by 166 MB: CPU request 0.03 → 0.014 cores, CPU limit 0.5 → none, memory request 128 → 294 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-v/deployment/app-v-frontend:frontend` | warn | medium | memory request under by 106 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.2 → none, memory request 128 → 234 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | warn | medium | CPU request over by 0.189 cores: CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 814 MB, memory limit 1536 → 814 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.node-memory-request-usage-gap.node-1-116` | warn | medium | memory requests/allocatable 0.75, working set/allocatable 7d p95 0.42 (instant 0.43) |
| `resources.node-memory-request-usage-gap.node-1-138` | warn | medium | memory requests/allocatable 0.75, working set/allocatable 7d p95 0.31 (instant 0.26) |
| `resources.node-memory-request-usage-gap.node-2-149` | warn | medium | memory requests/allocatable 0.99, working set/allocatable 7d p95 0.36 (instant 0.36) |
| `resources.node-memory-request-usage-gap.node-2-249` | warn | medium | memory requests/allocatable 0.71, working set/allocatable 7d p95 0.29 (instant 0.27) |
| `resources.node-request-usage-gap.node-1-117` | warn | medium | CPU requests/allocatable 0.73, usage/allocatable 7d p95 0.10 (5m instant 0.09) |
| `resources.node-request-usage-gap.node-1-224` | warn | medium | CPU requests/allocatable 0.80, usage/allocatable 7d p95 0.00 (5m instant 0.00) |
| `resources.node-request-usage-gap.node-2-149` | warn | medium | CPU requests/allocatable 0.74, usage/allocatable 7d p95 0.04 (5m instant 0.04) |
| `scaling.hpa-flapping.dev-app-s/hpa/app-s-frontend` | warn | medium | 38 desired changes over 7 days |
| `security.no-certificate-manager.cluster` | warn | medium | no component of family certificates in inventory.components |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label [], prod without one ['prod-app-w', 'prod-app-t', 'prod-app-x', 'prod-app-s', 'prod-app-y', 'prod-app-z-backend', 'prod-app-r', 'prod-app-v']. Share of containers allowing root 0.59 (27 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 71/76, of which 27 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['prod-app-w/deployment/app-w', 'prod-app-t/deployment/app-t-ai', 'prod-app-t/deployment/app-t-backend' … |
| `storage.ebs-unencrypted.cluster` | warn | medium | 13 of 13 volumes unencrypted: ['vol-078adb8df155474d5', 'vol-014ddb2ea18fb9f56', 'vol-04d6da165847ff0c2', 'vol-0a599f6260d09b6a1', 'vol-00f082f394c11e743', 'vol-0d059a329425ff008', 'vol-0cd5d589fe93566d4', 'vol-0df02294ac2267514'] and 5 more |
| `storage.ebs-volume-io-saturated.cluster` | warn | medium | EBS volumes 22 (root 9): max hourly average queue length 0.8514, queue ≥1 [], busiest-hour IOPS/provisioned max 0.013, IOPS at 70% or more [], burst balance under 20% [] |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['prod-app-v/data-app-v-backend-prod-mysql-0', 'prod-app-s/data-app-s-backend-mysql-0', 'prod-app-z-backend/data-app-z-neo4j-0', 'prod-app-r/data-app-r-postgresql-0', 'prod-app-t/data-app-t-backend-postgresql-0' … |
| `tenancy.prod-boundary-missing.prod-app-t` | warn | medium | prod-app-t: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-x` | warn | medium | prod-app-x: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-boundary-missing.prod-app-r` | warn | medium | prod-app-r: ResourceQuota False, NetworkPolicies 1 (enforced by the cluster False), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 10 |
| `tenancy.prod-without-quota.arc-runners` | warn | medium | arc-runners (ci): no ResourceQuota. Pods 0, CPU requests total 0.0 cores, memory requests total 0.0GB, 7d CPU p95 0.398 cores (cluster share 0.334), memory p95 1.82GB, 7d max/median Nonex. Tenants in this cluster 10, shares nodes with prod False |
| `tenancy.prod-without-quota.dev-app-s` | warn | medium | dev-app-s (dev): no ResourceQuota. Pods 5, CPU requests total 0.4 cores, memory requests total 1.25GB, 7d CPU p95 0.057 cores (cluster share 0.048), memory p95 0.91GB, 7d max/median 1.8x. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-w` | warn | medium | prod-app-w (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.25GB, 7d CPU p95 0.004 cores (cluster share 0.004), memory p95 0.21GB, 7d max/median Nonex. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-t` | warn | medium | prod-app-t (prod): no ResourceQuota. Pods 5, CPU requests total 0.29 cores, memory requests total 0.84GB, 7d CPU p95 0.015 cores (cluster share 0.012), memory p95 0.81GB, 7d max/median Nonex. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-x` | warn | medium | prod-app-x (prod): no ResourceQuota. Pods 3, CPU requests total 1.1 cores, memory requests total 2.25GB, 7d CPU p95 0.007 cores (cluster share 0.006), memory p95 2.89GB, 7d max/median Nonex. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-s` | warn | medium | prod-app-s (prod): no ResourceQuota. Pods 8, CPU requests total 0.35 cores, memory requests total 1.62GB, 7d CPU p95 0.12 cores (cluster share 0.1), memory p95 1.89GB, 7d max/median 1.7x. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-y` | warn | medium | prod-app-y (prod): no ResourceQuota. Pods 8, CPU requests total 0.51 cores, memory requests total 8.0GB, 7d CPU p95 0.037 cores (cluster share 0.031), memory p95 3.43GB, 7d max/median 1.4x. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-z-backend` | warn | medium | prod-app-z-backend (prod): no ResourceQuota. Pods 9, CPU requests total 2.72 cores, memory requests total 14.53GB, 7d CPU p95 0.012 cores (cluster share 0.01), memory p95 11.29GB, 7d max/median 21.1x. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-r` | warn | medium | prod-app-r (prod): no ResourceQuota. Pods 3, CPU requests total 0.62 cores, memory requests total 1.28GB, 7d CPU p95 0.006 cores (cluster share 0.005), memory p95 0.72GB, 7d max/median Nonex. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.prod-without-quota.prod-app-v` | warn | medium | prod-app-v (prod): no ResourceQuota. Pods 4, CPU requests total 0.25 cores, memory requests total 1.12GB, 7d CPU p95 0.025 cores (cluster share 0.021), memory p95 1.13GB, 7d max/median 3.3x. Tenants in this cluster 10, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.node-2-249` | warn | medium | Node node-2-249 (pool system-ondemand): tenant kinds ['other', 'prod'], namespaces ['monitoring', 'argocd', 'external-secrets', 'keda', 'kube-system', 'middleware'] and 2 more. Memory limit total 5.2GB / allocatable 3.2GB = 1.63x, request total 2.0GB, containers … |
| `tenancy.tenant-without-limitrange.prod-app-z-backend` | warn | medium | prod-app-z-backend (prod): no LimitRange, containers without requests 2 / without a memory limit 2 (pods 9). 7d CPU p95 0.012 cores, memory p95 11.29GB |
| `traffic.alb-deregistration-vs-grace.argocd/argocd-server` | warn | medium | Target group k8s-argocd-argocdse-74c4dcbda2: deregistration_delay 300s, backends ['deployment/argocd-server'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.middleware/kafka-ui` | warn | medium | Target group k8s-middlewa-kafkaui-0a6256c8b2: deregistration_delay 300s, backends ['deployment/kafka-ui'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.middleware/redis-insight` | warn | medium | Target group k8s-middlewa-redisins-e7e7fd218a: deregistration_delay 300s, backends ['deployment/redis-insight'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.monitoring/kube-prometheus-stack-grafana` | warn | medium | Target group k8s-monitori-kubeprom-af0f3aa6c7: deregistration_delay 300s, backends ['deployment/kube-prometheus-stack-grafana'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.monitoring/vmauth` | warn | medium | Target group k8s-monitori-vmauth-e07e5153ee: deregistration_delay 300s, backends ['deployment/vmauth'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-w/app-w` | warn | medium | Target group k8s-prodcarp-carpenst-e238817282: deregistration_delay 300s, backends ['deployment/app-w'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-t/app-t-ai` | warn | medium | Target group k8s-prodcurt-curtainc-fc2d368787: deregistration_delay 300s, backends ['deployment/app-t-ai'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-t/app-t-backend` | warn | medium | Target group k8s-prodcurt-curtainc-bb495c72c8: deregistration_delay 300s, backends ['deployment/app-t-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-t/app-t-studio` | warn | medium | Target group k8s-prodcurt-curtainc-57e5adf3bf: deregistration_delay 300s, backends ['deployment/app-t-studio'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-t/app-t-web` | warn | medium | Target group k8s-prodcurt-curtainc-022a51fc31: deregistration_delay 300s, backends ['deployment/app-t-web'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-x/app-x-api` | warn | medium | Target group k8s-prodfand-apppa-754a9b50b2: deregistration_delay 300s, backends ['deployment/app-x-api'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-y/app-y-admin` | warn | medium | Target group k8s-prodinse-insertoo-37417ab44f: deregistration_delay 300s, backends ['deployment/app-y-admin'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-y/app-y-ai` | warn | medium | Target group k8s-prodinse-insertoo-b22674073c: deregistration_delay 300s, backends ['deployment/app-y-ai'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-y/app-y-backend` | warn | medium | Target group k8s-prodinse-insertoo-89a3732998: deregistration_delay 300s, backends ['deployment/app-y-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-y/app-y-frontend` | warn | medium | Target group k8s-prodinse-insertoo-032c25d752: deregistration_delay 300s, backends ['deployment/app-y-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-z-backend/app-z-backend` | warn | medium | Target group k8s-prodrhem-appnbac-8c88bb317a: deregistration_delay 300s, backends ['deployment/app-z-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-z-backend/app-z-frontend` | warn | medium | Target group k8s-prodrhem-appnfro-9726e5b1d3: deregistration_delay 300s, backends ['deployment/app-z-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-r/app-r-backend` | warn | medium | Target group k8s-prodsoro-appmba-f68effe430: deregistration_delay 300s, backends ['deployment/app-r-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-r/app-r-web` | warn | medium | Target group k8s-prodsoro-appmwe-194ae69849: deregistration_delay 300s, backends ['deployment/app-r-web'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-v/app-v-admin-frontend` | warn | medium | Target group k8s-prodtoot-appka-d0c066d282: deregistration_delay 300s, backends ['deployment/app-v-admin-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-v/app-v-backend` | warn | medium | Target group k8s-prodtoot-appkb-7df87a92cc: deregistration_delay 300s, backends ['deployment/app-v-backend'] terminationGracePeriod 30s, no preStop |
| `traffic.alb-deregistration-vs-grace.prod-app-v/app-v-frontend` | warn | medium | Target group k8s-prodtoot-appkf-36f816b829: deregistration_delay 300s, backends ['deployment/app-v-frontend'] terminationGracePeriod 30s, no preStop |
| `traffic.external-exposure.ingress/argocd/argocd-server` | warn | medium | ingress ['deploy.lab-k.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/dev-app-s/app-s-admin` | warn | medium | ingress ['admin-dev.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-s/app-s-admin` | warn | medium | ingress ['canary-admin.lab-l.example', 'admin.lab-l.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-y/app-y-admin` | warn | medium | ingress ['admin.lab-m.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.external-exposure.ingress/prod-app-v/app-v-admin-frontend` | warn | medium | ingress ['admin.lab-n.example']: exposure internet-facing, TLS True, no auth annotation. Whether the app has its own login (Argo CD, Grafana etc.) needs a manual check |
| `traffic.ingress-5xx-ratio.prod-app-s/app-s-admin` | warn | medium | ['canary-admin.lab-l.example', 'admin.lab-l.example']: 24h 5xx 1.0 of 4.0 requests = 25.00% (under 100 requests a day and under 10 errors: warn only) (source alb-cloudwatch), p95 max 0.0087s |
| `traffic.ingress-5xx-ratio.prod-app-v/app-v-backend` | warn | medium | ['api.lab-n.example']: 24h 5xx 3.0 of 1099.0 requests = 0.27% (source alb-cloudwatch), p95 max 0.3171s |
| `traffic.ingress-5xx-ratio.prod-app-v/app-v-frontend` | warn | medium | ['lab-n.example', 'www.lab-n.example']: 24h 5xx 30.0 of 9936.0 requests = 0.30% (source alb-cloudwatch), p95 max 0.5584s |
| `traffic.ingress-p95-latency.prod-app-t/app-t-ai` | warn | medium | ['app-t-ai.lab-k.example']: p95 request-weighted 2.5752s, hourly average 2.4951s, 1h max 2.594s, latest hour with requests 2.3962s on 2.0 requests at 2026-11-14T03:11, 13 hours before the newest hour, no requests since, 21.0 requests/24h (under 100 requests a day: warn only) (source … |
| `traffic.ingress-p95-latency.prod-app-t/app-t-backend` | warn | medium | ['app-t-api.lab-k.example']: p95 request-weighted 1.5415s, hourly average 0.9403s, 1h max 5.5776s, latest hour with requests 0.0385s on 263.0 requests at 2026-11-14T16:11, 6089.0 requests/24h (source alb-cloudwatch) |
| `vpccni.ec2-api-errors.node-1-21` | warn | medium | node node-1-21: EC2 API failures 11 (by API {'DeleteNetworkInterface': 11}), force-removed ENIs 0 / IPs 0 (cumulative since ipamd start, IMDS 404 excluded) |
| `vpccni.ec2-api-errors.node-2-149` | warn | medium | node node-2-149: EC2 API failures 4 (by API {'DeleteNetworkInterface': 4}), force-removed ENIs 0 / IPs 0 (cumulative since ipamd start, IMDS 404 excluded) |
| `coredns.cache-hit-low.cluster` | fail | low | cache hit ratio 0.2137 (1h), cache TTL 30s, queries per second 5.93, NXDOMAIN share of queries forwarded upstream 0.434 |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 1 of 97 (0.01), without one in prod 32. emptyDirs without sizeLimit 21 (prod: ['prod-app-t/statefulset/app-t-backend-postgresql', 'prod-app-x/statefulset/app-x-postgresql', 'prod-app-z-backend/deployment/app-z-embedding-server' … |
| `node.cgroup-v1.node-1-116` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-1-138` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-21` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-224` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-1-65` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.aarch64 |
| `node.cgroup-v1.node-2-149` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.cgroup-v1.node-2-249` | fail | low | /sys/fs/cgroup filesystem tmpfs (cgroup v1). OS Amazon Linux 2, kernel 5.10.245-245.983.amzn2.x86_64 |
| `node.os-not-collected.node-1-117` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `node.os-not-collected.node-2-60` | fail | low | node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore |
| `scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-backend` | fail | low | HPA prod-app-z-backend/app-z-backend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 0% / target 70%, metrics ['cpu'], last scale 29.2 days ago |
| `scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-frontend` | fail | low | HPA prod-app-z-backend/app-z-frontend: share of 15 days at min 1.00, min 2 max 3, current CPU utilization 1% / target 70%, metrics ['cpu'], last scale 96.5 days ago |
| `storage.legacy-intree-storageclass.gp2` | fail | low | provisioner kubernetes.io/aws-ebs, default False, parameters {'fsType': 'ext4', 'type': 'gp2'} |
| `albctl.aws-api-churn.cluster` | warn | low | AWS API calls since leader start 250342, top [['Elastic Load Balancing v2/DescribeTargetHealth', 78172], ['Elastic Load Balancing v2/DescribeTargetGroupAttributes', 45151], ['EC2/DescribeInstances', 40158], ['EC2/DescribeSecurityGroups', 25519], ['Elastic Load Balancing v2/RegisterTargets', 12125]] … |
| `albctl.target-group-without-tgb.cluster` | warn | low | target groups the controller does not own 1 (TargetGroupBindings 39, hand-made 7) |
| `alertmanager.single-instance.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | low | replicas 1 (ready 1), cluster disabled (peers 0), data storage emptyDir (silence/notification state preserved 120h) |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 8, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 8, apps whose targetRevision is a branch or HEAD 8 ['argocd/application/app-w-prod', 'argocd/application/app-t-prod', 'argocd/application/app-x-prod', 'argocd/application/app-s-prod', 'argocd/application/app-y-prod', 'argocd/application/app-z-backend-prod' … |
| `argocd.version-eol.cluster` | warn | low | Argo CD 2.13.0 (components {'applicationset-controller': '1/1', 'dex-server': '1/1', 'notifications-controller': '1/1', 'redis': '1/1', 'repo-server': '1/1', 'server': '1/1', 'application-controller': '1/1'}) — 3.0 was released 2025-05, only the three latest minors are supported (N-2) |
| `controlplane.apiserver-slow-traces.cluster` | warn | low | 24h Traces (requests over 500ms) 183: [{'op': 'List', 'count': 161}, {'op': 'Call conversion webhook', 'count': 12}, {'op': 'Patch', 'count': 4}, {'op': 'Get', 'count': 3}, {'op': 'Create', 'count': 2}, {'op': 'Update', 'count': 1}] |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.491, cluster IPv6 False, queries per second 5.93. The glibc resolver always asks A and AAAA as a pair |
| `cost.idle-load-balancer.cluster` | warn | low | Of 3 LBs (base charge 49.28 USD/month), zero requests and bytes in 24h: ['app-u-db-shared']. NAT gateways 1 (43.07 USD/month + data) |
| `cost.idle-node.node-1-224` | warn | low | Node node-1-224 (r8gd.medium, pool default): CPU p95 0.004292177133419504, memory p95 0.04600463673984627, 7.3 USD/month |
| `cost.idle-node.node-1-65` | warn | low | Node node-1-65 (m7g.large, pool default): CPU p95 0.006155694494005682, memory p95 0.2623382124185489, 24.16 USD/month |
| `ebscsi.controller-metrics-disabled.cluster` | warn | low | controller EC2 API request series 0, driver 1.37.0 (add-on v1.37.0-eksbuild.1). When enabled, shows EC2 API errors {} / throttles None |
| `ecr.no-lifecycle-policy.ecr/registry/<account>` | warn | low | repositories without a lifecycle policy ['app-v', 'bitnami/kafka', 'bitnami/mysql'] (total 10.4GiB), overall 33 repositories, 728 images, 389.0GiB ≈ 41.8 USD/month, untagged images 201 (excluding 159 attestations) |
| `ecr.no-replication.ecr/registry/<account>` | warn | low | replication rules 0, repositories used by prod 26, total 389.0GiB |
| `ecr.tag-mutable-prod.ecr/registry/<account>` | warn | low | MUTABLE repositories 32/33, used by prod 25: ['ecr-app-w-eks-prod', 'ecr-app-t-backend-eks-prod', 'ecr-app-t-web-eks-prod', 'ecr-app-r-postgresql-prod', 'ecr-app-s-admin-eks-prod', 'ecr-app-t-postgresql-prod', 'ecr-app-x-postgresql-prod' … |
| `ecr.untagged-images.ecr/registry/<account>` | warn | low | untagged images 201/728 (excluding 159 BuildKit attestation manifests), repositories 33 |
| `eso.version-old.cluster` | warn | low | external-secrets 0.9.13 (ExternalSecrets 36, PushSecrets 0) |
| `grafana.version-old.monitoring/deployment/kube-prometheus-stack-grafana` | warn | low | Grafana 10.2.3 (database ok), ingress ['monitor.lab-k.example'], dashboards 31 |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.17.2 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-eks-nodeagent` | warn | low | image 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon/aws-network-policy-agent:v1.1.5-eksbuild.1 (tag tag, imagePullPolicy Always, registry 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com) |
| `hygiene.always-pull-with-tag.kube-system/daemonset/aws-node:aws-vpc-cni-init` | warn | low | image 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon-k8s-cni-init:v1.19.0-eksbuild.1 (tag tag, imagePullPolicy Always, registry 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com) |
| `hygiene.old-replicasets.cluster` | warn | low | Of 351 ReplicaSets, 296 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 51, '3': 6} |
| `hygiene.unused-crds.cluster` | warn | low | 27 of 47 CRDs have zero objects (by group {'generators.external-secrets.io': 7, 'monitoring.coreos.com': 6, 'networking.k8s.aws': 4, 'eventing.keda.sh': 2, 'external-secrets.io': 3, 'keda.sh': 2, 'crd.k8s.amazonaws.com': 1, 'actions.github.com': 1, 'vpcresources.k8s.aws': 1}), 18 webhooks |
| `karpenter.spot-to-spot-consolidation-off.cluster` | warn | low | FEATURE_GATES {'Drift': 'true', 'SpotToSpotConsolidation': 'false'}, NodeClaims terminated by spot interruption 284, drift True |
| `keda.operator-metrics-disabled.cluster` | warn | low | --enable-prometheus-metrics False, operator keda_* metrics exposed False, scaler errors in logs (24h) 0 |
| `keda.scaledobject-never-active.cluster` | warn | low | inactive for more than 14 days ['prod-app-y/scaledobject/app-y-ai-kafka-lag'], not Ready [], fallback active [], scale-to-zero targets ['prod-app-z-backend/scaledobject/app-z-file-worker', 'prod-app-z-backend/scaledobject/app-z-graph-worker'] |
| `kubeproxy.conntrack-invalid-drops.cluster` | warn | low | conntrack INVALID drops over 1 hour 642 packets (sum over nodes), services with externalTrafficPolicy Local 0, Services with a Local traffic policy and no endpoint on the node (max over nodes) 0 |
| `logs.signatures.karpenter.spot-interruption` | warn | low | 6 occurrences (2026-11-13T22:47:26Z ~ 2026-11-14T03:04:07Z), thresholds warn 3/fail 50. Files: ['logs/pods/karpenter/karpenter_karpenter.log']. Samples: ['[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-13T22:47:26.757771911Z … |
| `loki.version-old.monitoring/statefulset/loki-stack` | warn | low | Loki 2.6.1, storage emptyDir, retention applied True(compactor 1.0) |
| `observability.alert-metric-without-dashboard.grafana` | warn | low | 31 dashboards (223 panel metrics) — 132 of 172 alert-rule metrics have no panel: ['aggregator_unavailable_apiservice', 'aggregator_unavailable_apiservice_total', 'alertmanager_cluster_members', 'alertmanager_config_hash', 'alertmanager_config_last_reload_successful' … |
| `observability.alerts-never-fired.cluster` | warn | low | 128 of 141 rules did not fire in 15 days (['AlertmanagerClusterCrashlooping', 'AlertmanagerClusterDown', 'AlertmanagerClusterFailedToSendAlerts', 'AlertmanagerConfigInconsistent', 'AlertmanagerFailedReload', 'AlertmanagerFailedToSendAlerts', 'AlertmanagerMembersInconsistent' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 18 of 30 ingress backends have no saturation metric (e.g. [('argocd', 'argocd-server'), ('prod-app-w', 'app-w'), ('prod-app-t', 'app-t-ai'), ('prod-app-t', 'app-t-backend'), ('prod-app-t', 'app-t-studio'), ('prod-app-t', 'app-t-web')] and 12 … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('slack-system', None), ('null', ['alertname="Watchdog"']), ('slack-sre', ['env="prod"', 'service="image-inference"', 'slo="img-inference"']), ('slack-sre', ['env="prod"', 'service="lora-training"', 'slo="lora-training"']), ('slack-sre', ['source="onprem"'])], receivers ['null' … |
| `observability.unclassified-errors.cluster` | warn | low | 35 unclassified error lines (20959 lines scanned, 30 files). Top: [('grafana \| logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 unam', 8), ('ebs-csi \| "Unexpected failure when attempting to remove node taint(s)" err="isAllocatableSet: driver', 4), ('kube-proxy \| … |
| `observability.unstructured-logs.argocd` | warn | low | Of 8745 lines in 1h, 0 parse as JSON (0.0) |
| `prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus StatefulSet replicas 1 (ready 1), restarts 3, started 2026-11-14T14:34:31.949234438Z |
| `prometheus.version-old.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | low | Prometheus 2.49.1 — 2.53 is the last 2.x LTS (2024-07), 3.0 was released 2024-11 |
| `resilience.exec-probe.dev-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.kube-system/daemonset/aws-node:aws-node` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/app/grpc-health-probe -addr=:50051 -connect-timeout=5s -rpc-timeout=5s', 'port': None, 'timeout_s': 10, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s' … |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node-windows:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar.exe --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.kube-system/daemonset/ebs-csi-node:node-driver-registrar` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': '/csi-node-driver-registrar --kubelet-registration-path=$(DRIVER_REG_SOCK_PATH) --mode=kubelet-registration-probe', 'port': None, 'timeout_s': 15, 'period_s': 90, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.middleware/statefulset/redis-master:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': 'sh -c /health/ping_liveness_local.sh 5', 'port': None, 'timeout_s': 6, 'period_s': 5, 'failure_threshold': 5, 'initial_delay_s': 20}, readiness {'type': 'exec' … |
| `resilience.exec-probe.prod-app-t/statefulset/app-t-backend-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-t" -d "dbname=app-t" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.prod-app-x/statefulset/app-x-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-x" -d "dbname=app-x" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.prod-app-s/statefulset/app-s-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-y/statefulset/app-y-backend-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-file-worker:file-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.FileWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-z-backend/deployment/app-z-graph-worker:graph-worker` | warn | low | ['liveness exec (forks a process)']. liveness {'type': 'exec', 'path': 'arq --check app.worker.GraphWorkerSettings', 'port': None, 'timeout_s': 10, 'period_s': 60, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness None |
| `resilience.exec-probe.prod-app-r/statefulset/app-r-postgresql:postgresql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)']. liveness {'type': 'exec', 'path': '/bin/sh -c exec pg_isready -U "app-r" -d "dbname=app-r" -h 127.0.0.1 -p 5432', 'port': None, 'timeout_s': 5, 'period_s': 10, 'failure_threshold': 6 … |
| `resilience.exec-probe.prod-app-v/statefulset/app-v-backend-prod-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/bash -ec … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-ai:ai` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-studio:studio` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 3000, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-t/deployment/app-t-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.liveness-dependency-path.prod-app-x/deployment/app-x-api:api` | warn | low | ['liveness and readiness share the same path (/api/v1/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/api/v1/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-admin:admin` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-api:api` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-backend:backend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-s/deployment/app-s-frontend:frontend` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 'http', 'timeout_s': 3, 'period_s': 10, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 'http' … |
| `resilience.liveness-dependency-path.prod-app-z-backend/deployment/app-z-backend:backend` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.prod-app-r/deployment/app-r-backend:backend` | warn | low | ['liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/healthz', 'port': 7860, 'timeout_s': 5, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/healthz' … |
| `resilience.liveness-dependency-path.prod-app-r/deployment/app-r-web:web` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 80, 'timeout_s': 3, 'period_s': 30, 'failure_threshold': 3, 'initial_delay_s': 10}, readiness {'type': 'httpGet', 'path': '/health', 'port' … |
| `resilience.no-prestop.prod-app-w/app-w` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-studio` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-t/app-t-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-x/app-x-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-admin` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-y/app-y-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-embedding-server` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-z-pg-proxy` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-z-backend/app-ad` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-r/app-r-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-r/app-r-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-admin-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-backend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.prod-app-v/app-v-frontend` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server` | warn | low | pod argocd-repo-server-d487895cc-g4nzz: 7d memory working set p95 96 MB / request 512 MB = 0.19 |
| `resources.memory-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend` | warn | low | pod app-s-backend-5c455594cd-s87gg: 7d memory working set p95 79 MB / request 256 MB = 0.31 |
| `resources.memory-request-overprovisioned.karpenter/deploy/karpenter:controller` | warn | low | pod karpenter-9769889bd-nphgs: 7d memory working set p95 25 MB / request 256 MB = 0.10 |
| `resources.memory-request-overprovisioned.middleware/sts/redis-master:redis` | warn | low | pod redis-master-0: 7d memory working set p95 7 MB / request 256 MB = 0.03; database-like: keep the request |
| `resources.memory-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana` | warn | low | pod kube-prometheus-stack-grafana-5d7c56949c-qspbz: 7d memory working set p95 103 MB / request 384 MB = 0.27 |
| `resources.memory-request-overprovisioned.prod-app-t/sts/app-t-backend-postgresql:postgresql` | warn | low | pod app-t-backend-postgresql-0: 7d memory working set p95 54 MB / request 256 MB = 0.21; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-x/sts/app-x-postgresql:postgresql` | warn | low | pod app-x-postgresql-0: 7d memory working set p95 33 MB / request 256 MB = 0.13; database-like: keep the request |
| `resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-ai:ai` | warn | low | ['pod app-y-ai-55b7448547-5g592: 7d memory working set p95 424 MB / request 2048 MB = 0.21', 'pod app-y-ai-55b7448547-tcvrf: 7d memory working set p95 426 MB / request 2048 MB = 0.21'] |
| `resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend` | warn | low | ['pod app-y-backend-596479b6f8-ppqmd: 7d memory working set p95 79 MB / request 512 MB = 0.15', 'pod app-y-backend-596479b6f8-ggksl: 7d memory working set p95 76 MB / request 512 MB = 0.15'] |
| `resources.memory-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend` | warn | low | pod app-z-frontend-6d58bbfcfc-z9qmc: 7d memory working set p95 71 MB / request 256 MB = 0.28 |
| `resources.memory-request-overprovisioned.prod-app-z-backend/sts/app-z-neo4j:neo4j` | warn | low | pod app-z-neo4j-0: 7d memory working set p95 956 MB / request 4096 MB = 0.23; database-like: keep the request |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: metrics ['cpu'], current CPU 0% / target 70% |
| `scaling.hpa-cpu-only-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: metrics ['cpu'], current CPU 1% / target 70% |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-admin` | warn | low | HPA dev-app-s/app-s-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 70%, metrics ['cpu'], last scale 177.9 days ago |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-api` | warn | low | HPA dev-app-s/app-s-api: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 207.6 days ago |
| `scaling.hpa-never-scaled.dev-app-s/deployment/app-s-backend` | warn | low | HPA dev-app-s/app-s-backend: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 16% / target 70%, metrics ['cpu'], last scale 78.4 days ago |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-backend` | warn | low | HPA prod-app-z-backend/app-z-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.prod-app-z-backend/deployment/app-z-frontend` | warn | low | HPA prod-app-z-backend/app-z-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 0.0 desired changes over 7 days |
| `scaling.no-hpa-serving-prod.prod-app-w/app-w` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-ai` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-studio` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-t/app-t-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-x/app-x-api` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-api` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-s/app-s-frontend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-admin` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-backend` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-y/app-y-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-z-backend/app-z-embedding-server` | warn | low | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-z-backend/app-ad` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-r/app-r-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-r/app-r-web` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-admin-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-backend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.prod-app-v/app-v-frontend` | warn | low | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `tenancy.dev-shares-prod-nodes.node-1-21` | warn | low | Node node-1-21 (pool default): prod pods 16 (['prod-app-w', 'prod-app-t', 'prod-app-s', 'prod-app-y', 'prod-app-z-backend', 'prod-app-r', 'prod-app-v']) together with dev pods 4 (['dev-app-s']). Memory limit total/allocatable 1.02 … |
| `tenancy.dev-shares-prod-nodes.node-2-60` | warn | low | Node node-2-60 (pool system_core-20251217040546303900000001): prod pods 2 (['prod-app-s', 'prod-app-v']) together with dev pods 1 (['dev-app-s']). Memory limit total/allocatable 1.35, CPU limit total/allocatable 2.18, containers without a memory … |
| `traffic.alb-protection-off.k8s-lab-kprodlb-b18a4555d7` | warn | low | ALB k8s-lab-kprodlb-b18a4555d7: deletion_protection False, access_logs False, target groups in the ingress group 30 |
| `vpccni.metrics-unreadable.cluster` | warn | low | 2 of 9 nodes without readable ipamd metrics (localhost:61678): ['node-1-117', 'node-2-60'] |
| `eks.audit-log-off.cluster` | fail | info | enabled logs ['api', 'authenticator', 'controllerManager', 'scheduler'], disabled logs ['audit'] |

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>controlplane.scheduler-unschedulable.prod-app-x/app-x-api</code></summary>

```json
{
 "count": 39,
 "workload": "prod-app-x/app-x-api"
}
```

</details>
<details><summary><code>controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-backend</code></summary>

```json
{
 "count": 26,
 "workload": "prod-app-z-backend/app-z-backend"
}
```

</details>
<details><summary><code>controlplane.scheduler-unschedulable.prod-app-z-backend/app-z-embedding-server</code></summary>

```json
{
 "count": 26,
 "workload": "prod-app-z-backend/app-z-embedding-server"
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
<details><summary><code>resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "container": "prometheus"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.3360254624163343,
  "cpu_throttle_ratio_5m": 0.33750711439954467
 }
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
  "instance": "<ip>:8080",
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
  "prod-app-t",
  "prod-app-x",
  "prod-app-r"
 ],
 "policies": 3,
 "policies_but_not_enforced": true
}
```

</details>
<details><summary><code>security.plaintext-secret-env.prod-app-z-backend/deployment/app-ad:tailscale</code></summary>

```json
{
 "container": "tailscale",
 "env_names": [
  "TS_KUBE_SECRET"
 ],
 "prod": true,
 "workload": "prod-app-z-backend/deployment/app-ad"
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
<details><summary><code>security.privileged-or-host-access.prod-app-z-backend/deployment/app-ad</code></summary>

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
 "workload": "prod-app-z-backend/deployment/app-ad"
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-t/app-t-backend</code></summary>

```json
{
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
 "lb_type": "application",
 "name": "k8s-prodcurt-curtainc-bb495c72c8",
 "port": 3000,
 "target": "prod-app-t/app-t-backend",
 "targets_healthy": 0,
 "targets_total": 1,
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [404]"
  }
 ],
 "unhealthy_max_24h": 1.0,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 1
 },
 "workloads": [
  "deployment/app-t-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-y/app-y-frontend</code></summary>

```json
{
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
 "lb_type": "application",
 "name": "k8s-prodinse-insertoo-032c25d752",
 "port": 3003,
 "target": "prod-app-y/app-y-frontend",
 "targets_healthy": 0,
 "targets_total": 1,
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3003,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ],
 "unhealthy_max_24h": 1.0,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "workloads": [
  "deployment/app-y-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-z-backend/app-z-backend</code></summary>

```json
{
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
 "lb_type": "application",
 "name": "k8s-prodrhem-appnbac-8c88bb317a",
 "port": 8000,
 "target": "prod-app-z-backend/app-z-backend",
 "targets_healthy": 0,
 "targets_total": 2,
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
 "unhealthy_max_24h": 2.0,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [404]": 2
 },
 "workloads": [
  "deployment/app-z-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-unhealthy-targets.prod-app-v/app-v-frontend</code></summary>

```json
{
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
 "lb_type": "application",
 "name": "k8s-prodtoot-appkf-36f816b829",
 "port": 3000,
 "target": "prod-app-v/app-v-frontend",
 "targets_healthy": 0,
 "targets_total": 1,
 "targets_unhealthy": [
  {
   "id": "<ip>",
   "port": 3000,
   "state": "unhealthy",
   "reason": "Target.ResponseCodeMismatch",
   "description": "Health checks failed with these codes: [307]"
  }
 ],
 "unhealthy_max_24h": 1.0,
 "unhealthy_reasons": {
  "Target.ResponseCodeMismatch: Health checks failed with these codes: [307]": 1
 },
 "workloads": [
  "deployment/app-v-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external</code></summary>

```json
{
 "allowed_sources": {
  "9094": 1
 },
 "hosts": [
  "<load-balancer>.elb.amazonaws.com"
 ],
 "name": "kafka-controller-0-external",
 "namespace": "middleware",
 "note": "DB port open to the internet by the security group",
 "open_ports": [
  9094
 ],
 "ports": [
  9094,
  443
 ],
 "scheme": "internet-facing",
 "sg_exposure": "open",
 "source_ranges": null,
 "target": "loadbalancer/middleware/kafka-controller-0-external",
 "type": "loadbalancer"
}
```

</details>
<details><summary><code>vpccni.no-available-ip.node-1-116</code></summary>

```json
{
 "instance_type": "t8i.small",
 "ip_max": 9,
 "ip_usage_ratio": 0.667,
 "ip_used": 6,
 "max_pods": 11,
 "metrics": {
  "available": true,
  "assigned": 6,
  "total": 9,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 9,
  "prefixes": 0,
  "no_available_ip_events": 1,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-03297a1039053cae6": 2,
   "eni-083fb74efc082a4d6": 1,
   "eni-0acbdc61ea843cf79": 3
  }
 },
 "metrics_available": true,
 "no_available_ip_events": 1,
 "node": "node-1-116",
 "pool": "system-ondemand"
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
<details><summary><code>eks.service-quota-near-limit.aws-account</code></summary>

```json
{
 "available": true,
 "near_limit": [],
 "over_60": [
  "VPCs 0.6"
 ],
 "quotas": 65,
 "watched_quotas": [
  [
   "VPCs",
   3.0,
   5.0,
   0.6
  ],
  [
   "listener rules per ALB",
   37.0,
   100.0,
   0.37
  ],
  [
   "certificates per ALB",
   9.0,
   25.0,
   0.36
  ],
  [
   "target groups per ALB",
   30.0,
   100.0,
   0.3
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
   42.0,
   3000.0,
   0.014
  ],
  [
   "on-demand standard instance vCPU",
   12.0,
   1152.0,
   0.01
  ],
  [
   "spot standard instance vCPU",
   7.0,
   1152.0,
   0.006
  ]
 ],
 "with_usage": 25
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
<details><summary><code>logs.signatures.karpenter.version-unsupported</code></summary>

```json
{
 "count": 1,
 "first": "2026-11-14T08:53:35Z",
 "last": "2026-11-14T08:53:35Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/karpenter/karpenter_karpenter.log": 1
 },
 "samples": [
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T08:53:35.259616003Z {\"level\":\"ERROR\",\"time\":\"2026-11-14T08:53:35.259Z\",\"logger\":\"controller\",\"message\":\"failed validating kubernetes version\",\"commit\":\"490ef94\",\"controller\":\"nodeclass.s"
 ]
}
```

</details>
<details><summary><code>node.disk-usage.10.0.1.138:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "<ip>:9100",
  "mountpoint": "/"
 },
 "value": 0.8020774825236099
}
```

</details>
<details><summary><code>node.disk-usage.10.0.1.21:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "<ip>:9100",
  "mountpoint": "/"
 },
 "value": 0.7601050663270497
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
 "head_series": 177943,
 "memory_limit": "1536Mi",
 "monitoring_oomkilled": [
  "prometheus-kube-prometheus-stack-prometheus-0/prometheus"
 ],
 "monitoring_restarts_7d": {
  "prometheus-kube-prometheus-stack-prometheus-0": 1,
  "loki-stack-0": 2
 },
 "oomkilled_at": "2026-11-14T14:34:30Z",
 "oomkilled_last": true,
 "present": true,
 "restarts": 3,
 "rss_vs_limit": 0.731,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.prod-app-w/deployment/app-w</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "prod-app-w/deployment/app-w",
 "zones": {
  "ap-northeast-2a": 2
 }
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
  "node-1-65": 1,
  "node-1-224": 1
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
<details><summary><code>resilience.replicas-same-node.prod-app-y/deployment/app-y-ai</code></summary>

```json
{
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 2
 },
 "prod": true,
 "replicas": 3,
 "running": 3,
 "single_eligible_node": false,
 "spread_declared": false,
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
 "all_same_node": false,
 "anti_affinity": null,
 "eligible_nodes": 4,
 "nodes": {
  "node-1-138": 1,
  "node-1-21": 1
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "spread_declared": false,
 "topology_spread": [],
 "workload": "prod-app-y/deployment/app-y-backend",
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
<details><summary><code>resources.cpu-throttling.prod-app-v/deploy/app-v-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-v",
  "pod": "app-v-frontend-64c9f4f4b5-cdzsr",
  "container": "frontend"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.10704777917892673
 }
}
```

</details>
<details><summary><code>resources.memory-limit-near-p95.monitoring/ds/loki-stack-promtail:promtail</code></summary>

```json
{
 "labels": {
  "container": "promtail",
  "namespace": "monitoring",
  "pod": "loki-stack-promtail-dc9mw"
 },
 "value": 0.8192543029785155
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.monitoring/sts/loki-stack:loki</code></summary>

```json
{
 "cadvisor_oom_events_7d": 0,
 "kernel_kills_24h": 1,
 "kernel_log_read": true,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_read": 1,
 "kernel_nodes_total": 1,
 "last_kill": null,
 "pods_now": [
  {
   "pod": "loki-stack-0",
   "created": "2026-11-13T07:04:17Z",
   "restarts": 2,
   "last_ended": "2026-11-13T07:28:48Z",
   "last_reason": "Completed",
   "last_exit_code": 0
  }
 ],
 "pods_oomkilled": 1,
 "pods_replaced": 0,
 "restarts_of_those_pods": 2,
 "target": "monitoring/sts/loki-stack:loki"
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "cadvisor_oom_events_7d": 1,
 "kernel_any_node_read": true,
 "kernel_kills_24h": 0,
 "kernel_log_read": false,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_total": 1,
 "pods_now": [
  {
   "pod": "prometheus-kube-prometheus-stack-prometheus-0",
   "created": "2026-09-08T12:47:49Z",
   "restarts": 3,
   "last_ended": "2026-11-14T14:34:30Z",
   "last_reason": "OOMKilled",
   "last_exit_code": 137
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
<details><summary><code>security.imds-hop-limit.cluster</code></summary>

```json
{
 "applicable": true,
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
 "imds_by_setting": {
  "hop=2 tokens=required": 9
 },
 "imds_hop_limit_gt1": [
  {
   "id": "i-0141cf1ef71b07012",
   "type": "m5.large",
   "name": "system_core",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0fce7d18322427934",
   "type": "m5.large",
   "name": "system_core",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0c1a18a5452a29a73",
   "type": "t8i.medium",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-03b528dce3253508c",
   "type": "m7i-flex.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0a193dd781e33420d",
   "type": "t8i.small",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0484da6c9a2e1ee19",
   "type": "r8gd.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-07b69fdad759cb5f3",
   "type": "r8gd.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-03e9220ec611a4f0c",
   "type": "r8gd.medium",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  },
  {
   "id": "i-0ac759ca1b0ab02a4",
   "type": "m7g.large",
   "name": "karpenter-node",
   "hop_limit": 2,
   "tokens": "required"
  }
 ],
 "instances": 9,
 "instances_source": "aws/ec2-instances-imds.json",
 "irsa_service_accounts": [
  "external-secrets/external-secrets",
  "karpenter/karpenter",
  "kube-system/aws-load-balancer-controller",
  "kube-system/ebs-csi-controller-sa",
  "kube-system/external-dns",
  "monitoring/loki"
 ],
 "pod_identity_associations": 0
}
```

</details>
<details><summary><code>traffic.db-exposed.nlb/app-u-db-shared</code></summary>

```json
{
 "allowed_sources": {
  "3307": 4,
  "3308": 4,
  "3309": 4,
  "3311": 4,
  "5432": 4,
  "5433": 4,
  "6379": 1,
  "7687": 4
 },
 "hosts": [
  "<load-balancer>.elb.amazonaws.com"
 ],
 "name": "app-u-db-shared",
 "namespace": null,
 "note": "NLB created outside Kubernetes; 7 TargetGroupBindings bind it to dev-app-s/app-s-backend-mysql, prod-app-t/app-t-backend-postgresql, prod-app-s/app-s-backend-mysql, prod-app-y/app-y-backend-mysql, prod-app-z-backend/app-z-neo4j, prod-app-z-backend/app-z-pg-proxy and 1 more. DB port on an external address, limited by the security group to listed addresses",
 "ports": [
  3307,
  3308,
  3309,
  3311,
  5432,
  5433,
  6379,
  7687
 ],
 "scheme": "internet-facing",
 "sg_exposure": "allow-list",
 "target": "nlb/app-u-db-shared",
 "type": "nlb (defined outside the cluster)",
 "widest_prefix": {
  "3307": 32,
  "3308": 32,
  "3309": 32,
  "3311": 32,
  "5432": 32,
  "5433": 32,
  "6379": 32,
  "7687": 32
 }
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-1-116</code></summary>

```json
{
 "eni_at_max": true,
 "instance_type": "t8i.small",
 "ip_headroom": 3,
 "ip_max": 9,
 "ip_usage_ratio": 0.667,
 "ip_used": 6,
 "max_pods": 11,
 "metrics": {
  "available": true,
  "assigned": 6,
  "total": 9,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 9,
  "prefixes": 0,
  "no_available_ip_events": 1,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-03297a1039053cae6": 2,
   "eni-083fb74efc082a4d6": 1,
   "eni-0acbdc61ea843cf79": 3
  }
 },
 "no_available_ip_events": 1,
 "node": "node-1-116",
 "pool": "system-ondemand",
 "prefix_delegation": false,
 "prod_pods": 1
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-1-21</code></summary>

```json
{
 "eni_at_max": true,
 "instance_type": "r8gd.large",
 "ip_max": 27,
 "ip_usage_ratio": 0.852,
 "ip_used": 23,
 "max_pods": 29,
 "metrics": {
  "available": true,
  "assigned": 23,
  "total": 27,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 27,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 11,
  "ec2_api_errors_by_api": {
   "DeleteNetworkInterface": 11
  },
  "per_eni": {
   "eni-00e1a821abf4624ce": 9,
   "eni-06014368296be1b31": 8,
   "eni-0bfe5017301402fd5": 6
  }
 },
 "no_available_ip_events": 0,
 "node": "node-1-21",
 "pool": "default",
 "prefix_delegation": false,
 "prod_pods": 16
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-1-224</code></summary>

```json
{
 "eni_at_max": true,
 "instance_type": "r8gd.medium",
 "ip_headroom": 3,
 "ip_max": 6,
 "ip_usage_ratio": 0.5,
 "ip_used": 3,
 "max_pods": 8,
 "metrics": {
  "available": true,
  "assigned": 3,
  "total": 6,
  "eni_allocated": 2,
  "eni_max": 2,
  "ip_max": 6,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 0,
  "ec2_api_errors_by_api": {},
  "per_eni": {
   "eni-00249e1048003b26c": 0,
   "eni-0a8dd3f86af1af1b6": 3
  }
 },
 "no_available_ip_events": 0,
 "node": "node-1-224",
 "pool": "default",
 "prefix_delegation": false,
 "prod_pods": 1
}
```

</details>
<details><summary><code>vpccni.node-ip-exhaustion.node-2-249</code></summary>

```json
{
 "eni_at_max": true,
 "instance_type": "t8i.medium",
 "ip_max": 15,
 "ip_usage_ratio": 0.8,
 "ip_used": 12,
 "max_pods": 17,
 "metrics": {
  "available": true,
  "assigned": 12,
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
   "eni-04ada45282509c504": 5,
   "eni-0b7e15048591732b5": 3,
   "eni-0e5b968423a9317a5": 4
  }
 },
 "no_available_ip_events": 0,
 "node": "node-2-249",
 "pool": "system-ondemand",
 "prefix_delegation": false,
 "prod_pods": 2
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 9,
 "applications_prod": 8,
 "default_project_apps": 9,
 "projects": 1,
 "wildcard_projects": [
  "default"
 ]
}
```

</details>
<details><summary><code>cost.idle-compute-high.cluster</code></summary>

```json
{
 "by_pool": {
  "system-ondemand": 154.26,
  "nodegroup:system_core-20251217040546303900000001": 172.28,
  "default": 106.06
 },
 "idle_monthly_usd": 409.74,
 "idle_ratio": 0.95,
 "monthly_usd": 432.61,
 "node_metrics_read": true,
 "pricing_read": true,
 "spot_node_share": 0.44,
 "spot_savings_monthly_usd": 289.48,
 "usd_per_core_month": 26.41
}
```

</details>
<details><summary><code>cost.request-waste.cluster</code></summary>

```json
{
 "krr_saving_cores": 6.24,
 "monthly_usd_est": 164.8,
 "recommended_cpu_total": 2.19,
 "requests_cpu_total": 8.43
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
<details><summary><code>ecr.scan-disabled.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "critical_high_findings": 0,
 "images": 728,
 "images_scanned": 0,
 "registry_scan_on_push": false,
 "repos_scan_off": [
  "ecr-app-w-eks-prod",
  "bitnami/kafka",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-frontend-prod",
  "ecr-app-s-frontend-dev",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-admin-dev",
  "ecr-app-s-backend-dev",
  "ecr-app-s-api-dev",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "repos_scan_off_prod": [
  "ecr-app-w-eks-prod",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "repositories": 33,
 "scan_rules": 0,
 "scan_type": "BASIC"
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
 "ami_old_180d": [
  "system_core-20251217040546303900000001"
 ],
 "ami_old_90d": [
  "system_core-20251217040546303900000001 341d"
 ],
 "available": true,
 "max_ami_age_days": 341,
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
  "instance_id": "i-0141cf1ef71b07012",
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
  "instance_id": "i-0fce7d18322427934",
  "node": "node-2-60"
 }
}
```

</details>
<details><summary><code>eso.provider-api-errors.cluster</code></summary>

```json
{
 "api_error_ratio": 0.0555,
 "api_errors": 168,
 "api_success": 2860,
 "metrics_available": true,
 "not_ready": [],
 "not_ready_oldest_refresh_h": null,
 "reconcile_errors_total": 168,
 "sync_calls_error": 168,
 "sync_calls_total": 6342
}
```

</details>
<details><summary><code>hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility</code></summary>

```json
{
 "category": "UPGRADE_READINESS",
 "k8s_version": "1.33",
 "name": "Amazon Linux 2 compatibility",
 "reason": "Amazon EKS stopped publishing EKS-optimized Amazon Linux 2 (AL2) AMIs on November 26, 2025. AL2023 and Bottlerocket based AMIs for Amazon EKS are available for all supported Kubernetes versions includ",
 "status": "ERROR"
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.prod-app-z-backend/deployment/app-ad:tailscale</code></summary>

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
 "workload": "prod-app-z-backend/deployment/app-ad"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.prod-app-z-backend/deployment/app-ad</code></summary>

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
  "runAsRootAllowed",
  "sensitiveContainerEnvVar"
 ],
 "target": "prod-app-z-backend/deployment/app-ad"
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
 "value": 67.18179373842699
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
 "value": 67.18173586805662
}
```

</details>
<details><summary><code>observability.alerts-always-firing.CPUThrottlingHigh</code></summary>

```json
{
 "alertname": "CPUThrottlingHigh",
 "samples_7d": 29714.0
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
<details><summary><code>observability.alerts-always-firing.KubePodNotReady</code></summary>

```json
{
 "alertname": "KubePodNotReady",
 "samples_7d": 71218.0
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
  "kube-system": 29,
  "monitoring": 24,
  "prod-app-z-backend": 5,
  "middleware": 4,
  "keda": 3,
  "prod-app-s": 3,
  "argocd": 2,
  "dev-app-s": 2,
  "karpenter": 2,
  "prod-app-y": 2,
  "prod-app-r": 2,
  "prod-app-v": 2,
  "arc-system": 1,
  "prod-app-t": 1,
  "prod-app-x": 1
 },
 "gap_ratio": 0.634,
 "nodes_all_missing": [],
 "pods_without_logs_1h": 83,
 "running_pods_over_1h": 131
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
<details><summary><code>resilience.no-readiness-probe.prod-app-z-backend/app-ad</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-ad",
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
<details><summary><code>resilience.replicas-same-zone.prod-app-w/deployment/app-w</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-w/deployment/app-w",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-x/deployment/app-x-api</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-65": 1,
  "node-1-224": 1
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
<details><summary><code>resilience.replicas-same-zone.prod-app-s/deployment/app-s-api</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-s/deployment/app-s-api",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-s/deployment/app-s-backend</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-s/deployment/app-s-backend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-s/deployment/app-s-frontend</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-138": 1,
  "node-1-21": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-s/deployment/app-s-frontend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-y/deployment/app-y-ai</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 2
 },
 "prod": true,
 "replicas": 3,
 "topology_spread": [],
 "workload": "prod-app-y/deployment/app-y-ai",
 "zones": {
  "ap-northeast-2a": 3
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-y/deployment/app-y-backend</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-138": 1,
  "node-1-21": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-y/deployment/app-y-backend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-138": 1,
  "node-1-65": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-z-backend/deployment/app-z-backend",
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
  "node-1-138": 1,
  "node-1-65": 1
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
<details><summary><code>resilience.replicas-same-zone.prod-app-z-backend/deployment/app-z-frontend</code></summary>

```json
{
 "all_same_node": false,
 "all_same_zone": true,
 "nodes": {
  "node-1-21": 1,
  "node-1-138": 1
 },
 "prod": true,
 "replicas": 2,
 "topology_spread": [],
 "workload": "prod-app-z-backend/deployment/app-z-frontend",
 "zones": {
  "ap-northeast-2a": 2
 }
}
```

</details>
<details><summary><code>resilience.single-node-dependency.prod-app-z-backend/deployment/app-ad</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "hostPath volume ['dev-net-tun']"
 ],
 "replicas": 1,
 "workload": "prod-app-z-backend/deployment/app-ad"
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
<details><summary><code>resilience.single-replica-in-prod.prod-app-s/app-s-admin</code></summary>

```json
{
 "namespace": "prod-app-s",
 "name": "app-s-admin",
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
<details><summary><code>resilience.single-replica-in-prod.prod-app-z-backend/app-ad</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-ad",
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
<details><summary><code>resources.besteffort-in-prod.prod-app-z-backend/deploy/app-ad</code></summary>

```json
{
 "labels": {
  "__name__": "kube_pod_status_qos_class",
  "container": "kube-state-metrics",
  "endpoint": "http",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "prod-app-z-backend",
  "pod": "app-ad-79d68875b9-99csc",
  "qos_class": "BestEffort",
  "service": "kube-prometheus-stack-kube-state-metrics",
  "uid": "3bdcd53a-4ffb-4a5f-9816-717797ddb10c"
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
  "pod": "app-z-backend-96ffd6ff7-hrbn6",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.004120605696120613,
  "cpu_p95_7d_cores": 0.0020603028480603064,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-embedding-server:embedding</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-embedding-server-846dc84758-rkvzg",
  "container": "embedding"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.0024304396697927754,
  "cpu_p95_7d_cores": 0.0012152198348963877,
  "container_cpu_request_cores": 0.5
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-r/deploy/app-r-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-r",
  "pod": "app-r-backend-79b898dbbb-7r2kz",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.0026881891689918423,
  "cpu_p95_7d_cores": 0.0013440945844959212,
  "container_cpu_request_cores": 0.5
 }
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
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/loki-stack:loki</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 295 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "loki-stack",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.021 cores, CPU limit 0.2 → none, memory request 256 → 551 MB",
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
 "kubegap_reason": "memory request under by 929 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.146 cores, CPU limit 0.5 → none, memory request 800 → 1729 MB",
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
 "kubegap_reason": "CPU request over by 0.29 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "OK",
 "name": "vm-single",
 "severity": "CRITICAL",
 "summary": "CPU request 0.3 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 287 MB, memory limit 1024 → 287 MB",
 "target": "monitoring/statefulset/vm-single:vmsingle"
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
 "kubegap_reason": "memory request under by 385 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "WARNING",
 "name": "app-t-ai",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.062 cores, CPU limit 1.0 → none, memory request 256 → 641 MB",
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
 "kubegap_reason": "memory request under by 791 MB, CPU request over by 0.49 cores",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "app-x-api",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 1024 → 1815 MB",
 "target": "prod-app-x/deployment/app-x-api:api"
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
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 297 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "app-s-frontend",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.043 cores, CPU limit 0.2 → none, memory request 128 → 425 MB",
 "target": "prod-app-s/deployment/app-s-frontend:frontend"
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
 "kubegap_reason": "memory request under by 406 MB, CPU request over by 0.189 cores",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "WARNING",
 "name": "app-s-backend-mysql",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 1174 MB, memory limit 1536 → 1174 MB",
 "target": "prod-app-s/statefulset/app-s-backend-mysql:mysql"
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
 "kubegap_reason": "memory request under by 2651 MB, CPU request over by 0.358 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-z-embedding-server",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.142 cores, CPU limit 2.0 → none, memory request 4096 → 6747 MB, memory limit 6144 → 6747 MB",
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
<details><summary><code>resources.large-request-binpacking.prod-app-z-backend/deploy/app-z-embedding-server:embedding</code></summary>

```json
[
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-z-backend",
   "pod": "app-z-embedding-server-846dc84758-rkvzg"
  },
  "value": 0.5771764055717568
 },
 {
  "labels": {
   "container": "embedding",
   "namespace": "prod-app-z-backend",
   "pod": "app-z-embedding-server-846dc84758-sc79l"
  },
  "value": 0.5771764055717568
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
 "value": 0.5771764055717568
}
```

</details>
<details><summary><code>resources.no-memory-limit.prod-app-z-backend/app-ad</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-ad",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-1-65</code></summary>

```json
{
 "labels": {
  "node": "node-1-65"
 },
 "values": {
  "node_memory_request_ratio": 0.9097292173757964,
  "node_memory_usage_ratio_p95_7d": 0.2623382124185489,
  "node_memory_usage_ratio": 0.2620862492803019
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-138</code></summary>

```json
{
 "labels": {
  "node": "node-1-138"
 },
 "values": {
  "node_cpu_request_ratio": 0.8860103626943008,
  "node_cpu_usage_ratio_p95_7d": 0.033620509671567225,
  "node_cpu_usage_ratio_5m": 0.03214470374992236
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-21</code></summary>

```json
{
 "labels": {
  "node": "node-1-21"
 },
 "values": {
  "node_cpu_request_ratio": 0.8601036269430055,
  "node_cpu_usage_ratio_p95_7d": 0.05750155727419649,
  "node_cpu_usage_ratio_5m": 0.055794562063379564
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-65</code></summary>

```json
{
 "labels": {
  "node": "node-1-65"
 },
 "values": {
  "node_cpu_request_ratio": 0.9067357512953369,
  "node_cpu_usage_ratio_p95_7d": 0.006155694494005682,
  "node_cpu_usage_ratio_5m": 0.005138233170239914
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
  "node_cpu_request_ratio": 0.9378238341968915,
  "node_cpu_usage_ratio_p95_7d": 0.0628325062698299,
  "node_cpu_usage_ratio_5m": 0.040090975397521836
 }
}
```

</details>
<details><summary><code>security.polaris-security-danger.cluster</code></summary>

```json
{
 "danger_check_counts": {
  "dangerousCapabilities": 2,
  "hostNetworkSet": 2,
  "privilegeEscalationAllowed": 47,
  "runAsPrivileged": 2,
  "runAsRootAllowed": 46,
  "sensitiveContainerEnvVar": 2,
  "hostPIDSet": 1,
  "rolebindingClusterAdminRole": 2,
  "rolebindingRolePodExecAttach": 2,
  "clusterrolebindingClusterAdmin": 2,
  "clusterrolebindingPodExecAttach": 4,
  "clusterrolePodExecAttach": 4,
  "rolePodExecAttach": 2
 },
 "danger_workloads": [
  "kube-system/daemonset/aws-node",
  "prod-app-z-backend/deployment/app-ad",
  "kube-system/daemonset/ebs-csi-node-windows",
  "kube-system/daemonset/ebs-csi-node",
  "middleware/deployment/redis-insight",
  "arc-runners/cronjob/arc-warm-up",
  "arc-runners/cronjob/arc-cool-down",
  "monitoring/daemonset/kube-prometheus-stack-prometheus-node-exporter",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "middleware/statefulset/kafka-controller",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "arc-system/deployment/arc-gha-rs-controller",
  "prod-app-v/deployment/app-v-frontend",
  "prod-app-y/deployment/app-y-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "monitoring/deployment/vmalert",
  "dev-app-s/deployment/app-s-backend",
  "dev-app-s/deployment/app-s-api",
  "dev-app-s/deployment/app-s-frontend",
  "prod-app-z-backend/deployment/app-z-file-worker",
  "dev-app-s/deployment/app-s-admin",
  "prod-app-z-backend/deployment/app-z-graph-worker",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-s/deployment/app-s-admin",
  "middleware/deployment/kafka-ui",
  "monitoring/deployment/vmauth",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-w/deployment/app-w",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-s/deployment/app-s-api",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-t/deployment/app-t-web",
  "prod-app-r/deployment/app-r-web",
  "prod-app-t/deployment/app-t-backend",
  "monitoring/statefulset/vm-single",
  "prod-app-x/deployment/app-x-api",
  "prod-app-z-backend/deployment/app-z-backend",
  "argocd/rolebinding/argocd-repo-server",
  "monitoring/rolebinding/kube-prometheus-stack-grafana",
  "/clusterrolebinding/argocd-application-controller",
  "/clusterrolebinding/eks:addon-cluster-admin",
  "middleware/statefulset/redis-master",
  "monitoring/daemonset/loki-stack-promtail",
  "monitoring/statefulset/loki-stack",
  "kube-system/daemonset/kube-proxy",
  "kube-system/deployment/coredns",
  "/clusterrole/argocd-application-controller",
  "/clusterrole/argocd-server",
  "/clusterrole/eks:extension-metrics-apiserver",
  "/clusterrole/keda-operator",
  "argocd/role/argocd-repo-server",
  "monitoring/role/kube-prometheus-stack-grafana",
  "/clusterrolebinding/argocd-server",
  "/clusterrolebinding/keda-operator"
 ],
 "danger_workloads_prod": [
  "prod-app-z-backend/deployment/app-ad",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "prod-app-y/deployment/app-y-frontend",
  "prod-app-y/deployment/app-y-admin",
  "prod-app-y/deployment/app-y-backend",
  "prod-app-y/deployment/app-y-ai",
  "prod-app-z-backend/deployment/app-z-pg-proxy",
  "prod-app-z-backend/deployment/app-z-file-worker",
  "prod-app-z-backend/deployment/app-z-graph-worker",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/app-z-frontend",
  "prod-app-s/deployment/app-s-admin",
  "prod-app-z-backend/statefulset/app-z-neo4j",
  "prod-app-s/deployment/app-s-backend",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-s/deployment/app-s-frontend",
  "prod-app-w/deployment/app-w",
  "prod-app-t/deployment/app-t-ai",
  "prod-app-s/deployment/app-s-api",
  "prod-app-t/deployment/app-t-studio",
  "prod-app-t/deployment/app-t-web",
  "prod-app-r/deployment/app-r-web",
  "prod-app-t/deployment/app-t-backend",
  "prod-app-x/deployment/app-x-api",
  "prod-app-z-backend/deployment/app-z-backend"
 ],
 "present": true,
 "score": 80
}
```

</details>
<details><summary><code>storage.csi-snapshot-unavailable.cluster</code></summary>

```json
{
 "ebs_snapshot_descriptions": {
  "pre-delete backup of dev-app-v/data-to": 1,
  "pre-delete backup of dev-app-y/data-": 1
 },
 "ebs_snapshots_30d": 2,
 "platform": "eks",
 "prod_pvcs": 7,
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
 "tenants_total": 10
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
 "tenants_total": 10
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
 "tenants_total": 10
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
 "rbac_subject_count": 1,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
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
 "tenants_total": 10
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-s/app-s-api</code></summary>

```json
{
 "hosts": [
  "canary-api-v1.lab-l.example",
  "api.v1.lab-l.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 380.0,
  "requests_24h_equiv": 380.0,
  "rps_avg": 0.004,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 23.4161,
  "p95_s_avg": 11.5366,
  "p95_s_weighted": 3.0652,
  "p95_s_last_1h": 0.0023,
  "p95_s_last_at": "2026-11-14T16:11:00+00:00",
  "requests_last_1h": 160.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-prodillu-appi-c50edbe2df"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-s/app-s-api"
}
```

</details>
<details><summary><code>traffic.shared-alb-group.alb-group/app-u-prod-lb</code></summary>

```json
{
 "group": "app-u-prod-lb",
 "hosts": 37,
 "ingress_count": 30,
 "kinds": [
  "dev",
  "other",
  "prod"
 ],
 "lb": [
  "k8s-lab-kprodlb-b18a4555d7-2062640887.ap-northeast-2.elb.amazonaws.com"
 ],
 "mixed_prod_nonprod": true,
 "namespace_count": 12,
 "namespaces": [
  "argocd",
  "dev-app-s",
  "middleware",
  "monitoring",
  "prod-app-w",
  "prod-app-t",
  "prod-app-x",
  "prod-app-s",
  "prod-app-y",
  "prod-app-z-backend",
  "prod-app-r",
  "prod-app-v"
 ],
 "prod": true,
 "target": "alb-group/app-u-prod-lb"
}
```

</details>
<details><summary><code>vpccni.prefix-delegation-off.cluster</code></summary>

```json
{
 "capacity_read": true,
 "nitro_nodes": 9,
 "nodes": 9,
 "nodes_near_ip_limit": [
  "node-1-21",
  "node-2-249",
  "node-1-116",
  "node-2-60",
  "node-1-138",
  "node-1-224"
 ],
 "nodes_no_available_ip": [
  "node-1-116"
 ],
 "policy": "whole_eni",
 "prefix_delegation": false
}
```

</details>
<details><summary><code>albctl.reconcile-errors.cluster</code></summary>

```json
{
 "ingresses_without_lb": [],
 "leader_found": true,
 "metrics_available": true,
 "reconcile_errors_total": 44,
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
 "applications_prod": 8,
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
<details><summary><code>controlplane.apiserver-latency.PATCH</code></summary>

```json
{
 "labels": {
  "verb": "PATCH"
 },
 "value": 0.9257508333024703
}
```

</details>
<details><summary><code>controlplane.controller-error-repeat.disruption.go</code></summary>

```json
{
 "count": 6,
 "level": "E",
 "source": "disruption.go"
}
```

</details>
<details><summary><code>controlplane.controller-error-repeat.horizontal.go</code></summary>

```json
{
 "count": 5,
 "level": "E",
 "source": "horizontal.go"
}
```

</details>
<details><summary><code>controlplane.controller-error-repeat.type.go</code></summary>

```json
{
 "count": 34470,
 "level": "W",
 "source": "type.go"
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "autopath": false,
 "cache_hit_ratio": 0.2137,
 "forward_nxdomain_ratio": 0.434,
 "metrics_available": true,
 "nxdomain_ratio": 0.557,
 "pods_default_ndots": 137,
 "qps_total": 5.93,
 "upstreams": [
  "<ip>:53"
 ]
}
```

</details>
<details><summary><code>ecr.dockerhub-dependency.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "dockerhub_images": 18,
 "dockerhub_sample": [
  "alpine/socat:1.8.0.0",
  "bitnami/kubectl:latest",
  "docker.io/bitnamilegacy/jmx-exporter:0.20.0-debian-11-r4",
  "docker.io/bitnamilegacy/kafka:3.6.1-debian-11-r3",
  "docker.io/bitnamilegacy/kubectl:1.32.4",
  "docker.io/bitnamilegacy/os-shell:11-debian-11-r95",
  "docker.io/danielqsj/kafka-exporter:v1.7.0",
  "docker.io/grafana/grafana:10.2.3",
  "docker.io/grafana/promtail:2.9.2",
  "docker.io/library/busybox:1.31.1",
  "docker.io/provectuslabs/kafka-ui:v0.7.1",
  "grafana/loki:2.6.1",
  "neo4j:2026.05.0-community",
  "redis/redisinsight:latest",
  "tailscale/tailscale:latest",
  "victoriametrics/victoria-metrics:v1.132.0",
  "victoriametrics/vmalert:v1.97.0",
  "victoriametrics/vmauth:v1.132.0"
 ],
 "images_by_registry": {
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com": 77,
  "<account>.dkr.ecr.ap-northeast-2.amazonaws.com": 44,
  "docker.io": 33,
  "quay.io": 25,
  "ghcr.io": 9,
  "public.ecr.aws": 7,
  "registry.k8s.io": 3
 },
 "pull_through_cache_rules": [],
 "replication_rules": 0
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
<details><summary><code>grafana.datasource-errors.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "api_5xx": 0,
 "api_requests": 49007,
 "datasource_error_max_ratio": 0.0306,
 "datasources": [
  {
   "datasource": "Loki(loki)",
   "requests": 327,
   "errors_5xx_429": 10,
   "error_ratio": 0.0306,
   "by_code": {
    "200": 317,
    "429": 10
   }
  },
  {
   "datasource": "Prometheus(prometheus)",
   "requests": 47,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 46,
    "301": 1
   }
  },
  {
   "datasource": "VictoriaMetrics_onprem(prometheus)",
   "requests": 7303,
   "errors_5xx_429": 0,
   "error_ratio": 0.0,
   "by_code": {
    "200": 7303
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
 "prod_workloads": 8,
 "well_known": false,
 "workload_count": 29,
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
  "prod-app-v/statefulset/app-v-backend-prod-mysql"
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
 "prod_workloads": 24,
 "well_known": false,
 "workload_count": 28,
 "workloads": [
  "dev-app-s/deployment/app-s-admin",
  "dev-app-s/deployment/app-s-api",
  "dev-app-s/deployment/app-s-backend",
  "dev-app-s/deployment/app-s-frontend",
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
  "prod-app-v/deployment/app-v-frontend"
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
 "node_termination_avg_s": 14.4,
 "pods_startup_avg_s": 29.9,
 "pods_startup_count": 9779,
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
  "kafka": 2,
  "metrics-api": 2
 }
}
```

</details>
<details><summary><code>logs.signatures.ebs-csi.snapshot-crd-missing</code></summary>

```json
{
 "count": 1500,
 "first": "2026-11-14T12:30:01Z",
 "last": "2026-11-14T17:11:58Z",
 "warn_at": 1,
 "fail_at": 100,
 "files": {
  "logs/pods/ebs-csi/kube-system_ebs-csi-controller.log": 1500
 },
 "samples": [
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:01.661807592Z W1114 12:30:01.661676       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:01.661849424Z E1114 12:30:01.661747       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:32.193221362Z W1114 12:30:32.193137       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotContent: the se",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:32.193268915Z E1114 12:30:32.193183       1 reflector.go:158] \"Unhandled Error\" err=\"k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: Failed to watch *v1.Volum",
  "[pod/ebs-csi-controller-85dcc64955-m7jp8/csi-snapshotter] 2026-11-14T12:30:54.686252319Z W1114 12:30:54.686153       1 reflector.go:561] k8s.io/client-go@v0.31.0/tools/cache/reflector.go:243: failed to list *v1.VolumeSnapshotClass: the serv"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metrics-server.scrape-failed</code></summary>

```json
{
 "count": 8,
 "first": "2026-11-13T22:48:26Z",
 "last": "2026-11-14T03:04:56Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/metrics-server/kube-system_metrics-server.log": 8
 },
 "samples": [
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-13T22:48:26.038754342Z E1113 22:48:26.038622       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-13T22:48:26.101048286Z E1113 22:48:26.100925       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal er",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-13T23:37:11.087960476Z E1113 23:37:11.087850       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-14T01:44:41.071275522Z E1114 01:44:41.071134       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal err",
  "[pod/metrics-server-65d4b7df64-xxfjs/metrics-server] 2026-11-14T02:26:41.037274591Z E1114 02:26:41.037135       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": remote error: tls: internal er"
 ]
}
```

</details>
<details><summary><code>loki.request-errors.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "discarded_by_reason": {},
 "log_error_messages": 5736,
 "metrics_available": true,
 "panics": 0,
 "present": true,
 "requests_5xx": 0,
 "requests_5xx_by_route": {},
 "requests_total": 976631,
 "target": "monitoring/statefulset/loki-stack",
 "wal_disk_full_failures": 0
}
```

</details>
<details><summary><code>node.kernel-net-mem-pressure.node-2-149</code></summary>

```json
{
 "collected": true,
 "kernel": {
  "source": "dmesg",
  "window": "since boot (dmesg; journald does not hold 24 hours)",
  "lines": 1153,
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
   "[Sun Nov  8 10:39:26 2026] TCP: request_sock_TCP: Possible SYN flooding on port 9095. Sending cookies.  Check SNMP counters."
  ],
  "oom_samples": [],
  "oom_section": true,
  "oom_kills": [],
  "total_events": 1
 },
 "node": "node-2-149"
}
```

</details>
<details><summary><code>node.network-errors.10.0.1.65:9100:eth0</code></summary>

```json
{
 "labels": {
  "device": "eth0",
  "instance": "<ip>:9100"
 },
 "value": 408.11089207584695
}
```

</details>
<details><summary><code>observability.alert-firing-stale.CPUThrottlingHigh/monitoring</code></summary>

```json
{
 "labels": {
  "alertname": "CPUThrottlingHigh",
  "container": "prometheus",
  "namespace": "monitoring",
  "pod": "prometheus-kube-prometheus-stack-prometheus-0",
  "severity": "info"
 },
 "value": 5.45086781250106
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
  "(none, 0)": 95,
  "system-cluster-critical": 9,
  "system-node-critical": 27
 },
 "preempted_events": 0,
 "prod_max_priority": 0,
 "prod_pods": 42,
 "prod_pods_without_class": 42,
 "user_classes": []
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-t/statefulset/app-t-backend-postgresql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-t-backend-postgresql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-t-backend-postgresql-0"
 ],
 "services": [
  "app-t-backend-postgresql",
  "app-t-backend-postgresql-hl"
 ],
 "target": "prod-app-t/statefulset/app-t-backend-postgresql"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-x/statefulset/app-x-postgresql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-x-postgresql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-x-postgresql-0"
 ],
 "services": [
  "app-x-postgresql",
  "app-x-postgresql-hl"
 ],
 "target": "prod-app-x/statefulset/app-x-postgresql"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-s/statefulset/app-s-backend-mysql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-s-backend-mysql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-s-backend-mysql-0"
 ],
 "services": [
  "app-s-backend-mysql",
  "app-s-backend-mysql-headless"
 ],
 "target": "prod-app-s/statefulset/app-s-backend-mysql"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-y/statefulset/app-y-backend-mysql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-y-backend-mysql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-y-backend-mysql-0"
 ],
 "services": [
  "app-y-backend-mysql",
  "app-y-backend-mysql-headless"
 ],
 "target": "prod-app-y/statefulset/app-y-backend-mysql"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-z-backend/statefulset/app-z-neo4j</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-z-neo4j",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-z-neo4j-0"
 ],
 "services": [
  "app-z-neo4j"
 ],
 "target": "prod-app-z-backend/statefulset/app-z-neo4j"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-r/statefulset/app-r-postgresql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-r-postgresql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-r-postgresql-0"
 ],
 "services": [
  "app-r-postgresql",
  "app-r-postgresql-hl"
 ],
 "target": "prod-app-r/statefulset/app-r-postgresql"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.prod-app-v/statefulset/app-v-backend-prod-mysql</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-v-backend-prod-mysql",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-v-backend-prod-mysql-0"
 ],
 "services": [
  "app-v-backend-prod-mysql",
  "app-v-backend-prod-mysql-headless"
 ],
 "target": "prod-app-v/statefulset/app-v-backend-prod-mysql"
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
<details><summary><code>resources.cpu-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server</code></summary>

```json
{
 "labels": {
  "namespace": "argocd",
  "pod": "argocd-repo-server-d487895cc-g4nzz",
  "container": "repo-server"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.01151867128613178,
  "cpu_p95_7d_cores": 0.002303734257226356,
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
  "cpu_request_p95_ratio_7d": 0.17313297429617092,
  "cpu_p95_7d_cores": 0.03462659485923419,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-backend-5c455594cd-s87gg",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1680692213810183,
  "cpu_p95_7d_cores": 0.01680692213810183,
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
  "cpu_request_p95_ratio_7d": 0.101990124067153,
  "cpu_p95_7d_cores": 0.0101990124067153,
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
   "pod": "karpenter-9769889bd-nphgs",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0022247060959686995,
   "cpu_p95_7d_cores": 0.0004449412191937399,
   "container_cpu_request_cores": 0.2
  }
 },
 {
  "labels": {
   "namespace": "karpenter",
   "pod": "karpenter-9769889bd-pkxd2",
   "container": "controller"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0980535537226606,
   "cpu_p95_7d_cores": 0.01961071074453212,
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
  "cpu_request_p95_ratio_7d": 0.0028009899973124256,
  "cpu_p95_7d_cores": 0.00028009899973124256,
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
  "pod": "keda-operator-metrics-apiserver-c5b6f8b88-jp4kd",
  "container": "keda-operator-metrics-apiserver"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.018841756388004748,
  "cpu_p95_7d_cores": 0.0018841756388004748,
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
  "cpu_request_p95_ratio_7d": 0.015883473773153522,
  "cpu_p95_7d_cores": 0.0015883473773153525,
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
   "cpu_request_p95_ratio_7d": 0.02340072209669465,
   "cpu_p95_7d_cores": 0.0023400722096694653,
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
   "cpu_request_p95_ratio_7d": 0.009649847626253592,
   "cpu_p95_7d_cores": 0.0009649847626253592,
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
   "pod": "coredns-c7dbf4744-cb76h",
   "container": "coredns"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.06614204139327245,
   "cpu_p95_7d_cores": 0.006614204139327245,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "coredns-c7dbf4744-lz5fs",
   "container": "coredns"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.07192089774039374,
   "cpu_p95_7d_cores": 0.007192089774039375,
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
  "cpu_request_p95_ratio_7d": 0.05461338318348344,
  "cpu_p95_7d_cores": 0.005461338318348344,
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
   "pod": "kube-proxy-89jgp",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.003452018010475839,
   "cpu_p95_7d_cores": 0.0003452018010475839,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-gqdmf",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.004594189389228078,
   "cpu_p95_7d_cores": 0.0004594189389228078,
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
   "cpu_request_p95_ratio_7d": 0.008356812020962017,
   "cpu_p95_7d_cores": 0.0008356812020962018,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-6g9r6",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.0035334490264746447,
   "cpu_p95_7d_cores": 0.0003533449026474645,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-l2l6n",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.004097469963514652,
   "cpu_p95_7d_cores": 0.00040974699635146526,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-d297j",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.007950262495401468,
   "cpu_p95_7d_cores": 0.0007950262495401469,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "kube-system",
   "pod": "kube-proxy-4qb22",
   "container": "kube-proxy"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.004132407376452996,
   "cpu_p95_7d_cores": 0.0004132407376452996,
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
  "pod": "kafka-ui-7cb8bcb988-5gchp",
  "container": "kafka-ui"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.011424912444048616,
  "cpu_p95_7d_cores": 0.0011424912444048616,
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
  "cpu_request_p95_ratio_7d": 0.32172392815634787,
  "cpu_p95_7d_cores": 0.06434478563126958,
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
  "pod": "kube-prometheus-stack-grafana-5d7c56949c-qspbz",
  "container": "grafana"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.056093333553593853,
  "cpu_p95_7d_cores": 0.005609333355359385,
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
  "cpu_request_p95_ratio_7d": 0.08296830640234061,
  "cpu_p95_7d_cores": 0.008296830640234062,
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
  "cpu_request_p95_ratio_7d": 0.03109273797948172,
  "cpu_p95_7d_cores": 0.009327821393844516,
  "container_cpu_request_cores": 0.3
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-t/deploy/app-t-ai:ai</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-t",
  "pod": "app-t-ai-f69d6d448-7hpcq",
  "container": "ai"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.015121853322314277,
  "cpu_p95_7d_cores": 0.0015121853322314278,
  "container_cpu_request_cores": 0.1
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
  "cpu_request_p95_ratio_7d": 0.05366971709939463,
  "cpu_p95_7d_cores": 0.005366971709939463,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-x/sts/app-x-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-x",
  "pod": "app-x-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.04467452305474044,
  "cpu_p95_7d_cores": 0.004467452305474045,
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
  "cpu_request_p95_ratio_7d": 0.05248573771909974,
  "cpu_p95_7d_cores": 0.01049714754381995,
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
   "pod": "app-y-backend-596479b6f8-ggksl",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.09821382721079264,
   "cpu_p95_7d_cores": 0.009821382721079264,
   "container_cpu_request_cores": 0.1
  }
 },
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-ppqmd",
   "container": "backend"
  },
  "values": {
   "cpu_request_p95_ratio_7d": 0.09968078951301339,
   "cpu_p95_7d_cores": 0.00996807895130134,
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
  "cpu_request_p95_ratio_7d": 0.044745232064782266,
  "cpu_p95_7d_cores": 0.008949046412956454,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-frontend-6d58bbfcfc-z9qmc",
  "container": "frontend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.007578259883672859,
  "cpu_p95_7d_cores": 0.000757825988367286,
  "container_cpu_request_cores": 0.1
 }
}
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
  "cpu_request_p95_ratio_7d": 0.008645776391195327,
  "cpu_p95_7d_cores": 0.0043228881955976635,
  "container_cpu_request_cores": 0.5
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
  "cpu_request_p95_ratio_7d": 0.04508021997824723,
  "cpu_p95_7d_cores": 0.004508021997824723,
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
  "cpu_request_p95_ratio_7d": 0.05080579762047695,
  "cpu_p95_7d_cores": 0.01016115952409539,
  "container_cpu_request_cores": 0.2
 }
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
 "memory_request_sev": "OK",
 "name": "argocd-repo-server",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 304 MB, memory limit 1024 → 304 MB",
 "target": "argocd/deployment/argocd-repo-server:repo-server"
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
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 227 MB, CPU request over by 0.144 cores",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "argocd-application-controller",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.056 cores, CPU limit 0.5 → none, memory request 384 → 611 MB",
 "target": "argocd/statefulset/argocd-application-controller:application-controller"
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
<details><summary><code>resources.krr-recommendation.karpenter/deployment/karpenter:controller</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 189 MB, CPU request over by 0.177 cores",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "OK",
 "name": "karpenter",
 "severity": "WARNING",
 "summary": "CPU request 0.2 → 0.023 cores, CPU limit 0.5 → none, memory request 256 → 445 MB",
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
 "kubegap_reason": "CPU request over by 0.131 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "kafka-controller",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.069 cores, CPU limit 0.5 → none, memory request 1536 → 1487 MB, memory limit 2048 → 1487 MB",
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
 "kubegap_reason": "memory request under by 117 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "OK",
 "name": "loki-stack-promtail",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.018 cores, CPU limit 0.1 → none, memory request 128 → 245 MB",
 "target": "monitoring/daemonset/loki-stack-promtail:promtail"
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
 "kubegap_reason": "memory request under by 203 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-t-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.046 cores, CPU limit 0.5 → none, memory request 192 → 395 MB",
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
<details><summary><code>resources.krr-recommendation.prod-app-s/deployment/app-s-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 224 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-s-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.03 → 0.037 cores, CPU limit 0.5 → none, memory request 128 → 352 MB",
 "target": "prod-app-s/deployment/app-s-backend:backend"
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
 "kubegap_reason": "memory request over by 340 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-y-backend",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.01 cores, CPU limit 2.0 → none, memory request 512 → 172 MB, memory limit 2048 → 172 MB",
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
<details><summary><code>resources.krr-recommendation.prod-app-v/deployment/app-v-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 166 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-v-backend",
 "severity": "WARNING",
 "summary": "CPU request 0.03 → 0.014 cores, CPU limit 0.5 → none, memory request 128 → 294 MB",
 "target": "prod-app-v/deployment/app-v-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.prod-app-v/deployment/app-v-frontend:frontend</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 106 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-v-frontend",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.2 → none, memory request 128 → 234 MB",
 "target": "prod-app-v/deployment/app-v-frontend:frontend"
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
 "summary": "CPU request 0.2 → 0.011 cores, CPU limit 1.0 → none, memory request 768 → 814 MB, memory limit 1536 → 814 MB",
 "target": "prod-app-v/statefulset/app-v-backend-prod-mysql:mysql"
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-1-116</code></summary>

```json
{
 "labels": {
  "node": "node-1-116"
 },
 "values": {
  "node_memory_request_ratio": 0.7530047471327918,
  "node_memory_usage_ratio_p95_7d": 0.4245136435810213,
  "node_memory_usage_ratio": 0.431003162031653
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-1-138</code></summary>

```json
{
 "labels": {
  "node": "node-1-138"
 },
 "values": {
  "node_memory_request_ratio": 0.75016147209442,
  "node_memory_usage_ratio_p95_7d": 0.3136632987271495,
  "node_memory_usage_ratio": 0.25504286267309273
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-2-149</code></summary>

```json
{
 "labels": {
  "node": "node-2-149"
 },
 "values": {
  "node_memory_request_ratio": 0.9925704751031879,
  "node_memory_usage_ratio_p95_7d": 0.35618424519188546,
  "node_memory_usage_ratio": 0.3598484016861333
 }
}
```

</details>
<details><summary><code>resources.node-memory-request-usage-gap.node-2-249</code></summary>

```json
{
 "labels": {
  "node": "node-2-249"
 },
 "values": {
  "node_memory_request_ratio": 0.7099221572409463,
  "node_memory_usage_ratio_p95_7d": 0.28540466105222095,
  "node_memory_usage_ratio": 0.2728016496100727
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
  "node_cpu_request_ratio": 0.7305699481865285,
  "node_cpu_usage_ratio_p95_7d": 0.10108454163660835,
  "node_cpu_usage_ratio_5m": 0.0866149256646185
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-1-224</code></summary>

```json
{
 "labels": {
  "node": "node-1-224"
 },
 "values": {
  "node_cpu_request_ratio": 0.7978723404255321,
  "node_cpu_usage_ratio_p95_7d": 0.004292177133419504,
  "node_cpu_usage_ratio_5m": 0.004104206678986662
 }
}
```

</details>
<details><summary><code>resources.node-request-usage-gap.node-2-149</code></summary>

```json
{
 "labels": {
  "node": "node-2-149"
 },
 "values": {
  "node_cpu_request_ratio": 0.7357512953367876,
  "node_cpu_usage_ratio_p95_7d": 0.043969090886141204,
  "node_cpu_usage_ratio_5m": 0.039889096574396314
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
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "dev-app-s",
  "pod": "kube-prometheus-stack-kube-state-metrics-8655798c4c-cqc8g",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 38.0
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
 "prod_without_psa": [
  "prod-app-w",
  "prod-app-t",
  "prod-app-x",
  "prod-app-s",
  "prod-app-y",
  "prod-app-z-backend",
  "prod-app-r",
  "prod-app-v"
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
  "prod-app-z-backend/deployment/app-ad",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/deployment/app-r-web",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/deployment/app-v-frontend",
  "prod-app-z-backend/statefulset/app-z-neo4j"
 ],
 "root_allowed_ratio": 0.59
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
 "automount_false_sa": 6,
 "service_accounts": 105,
 "token_mounted": 71,
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
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/deployment/app-r-web",
  "prod-app-v/deployment/app-v-admin-frontend",
  "prod-app-v/deployment/app-v-backend",
  "prod-app-v/statefulset/app-v-backend-prod-mysql",
  "prod-app-v/deployment/app-v-frontend"
 ],
 "workloads": 76
}
```

</details>
<details><summary><code>storage.ebs-unencrypted.cluster</code></summary>

```json
{
 "available": true,
 "unencrypted": [
  "vol-078adb8df155474d5",
  "vol-014ddb2ea18fb9f56",
  "vol-04d6da165847ff0c2",
  "vol-0a599f6260d09b6a1",
  "vol-00f082f394c11e743",
  "vol-0d059a329425ff008",
  "vol-0cd5d589fe93566d4",
  "vol-0df02294ac2267514",
  "vol-03dec435edcdbfeb2",
  "vol-0b9828b66a5d51c71",
  "vol-088f062f50986187b",
  "vol-077bead6fe444edce",
  "vol-0c083bfd01c5721b1"
 ],
 "volumes": 13
}
```

</details>
<details><summary><code>storage.ebs-volume-io-saturated.cluster</code></summary>

```json
{
 "available": true,
 "burst_low": [],
 "iops_near_limit": [],
 "max_iops_ratio": 0.013,
 "max_queue": 0.8514,
 "queue_high": [],
 "root_volumes": 9,
 "volumes": 22
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
  "prod-app-r/data-app-r-postgresql-0",
  "prod-app-t/data-app-t-backend-postgresql-0",
  "prod-app-y/data-app-y-backend-mysql-0",
  "prod-app-x/data-app-x-postgresql-0"
 ],
 "rows": [
  {
   "namespace": "monitoring",
   "name": "prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "target": "monitoring/prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.476,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.066,
   "days_to_full": 155,
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
   "days_to_full": 21869,
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
   "used_ratio": 0.078,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.001,
   "days_to_full": 7878,
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
   "growth_gb_per_day": 0.0,
   "days_to_full": 48296695907,
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
   "days_to_full": 346282,
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
   "growth_gb_per_day": 0.0,
   "days_to_full": 31768,
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
   "growth_gb_per_day": 0.001,
   "days_to_full": 14297,
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
   "days_to_full": null,
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
   "growth_gb_per_day": 0.006,
   "days_to_full": 1321,
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
   "namespace": "middleware",
   "name": "data-kafka-controller-0",
   "target": "middleware/data-kafka-controller-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 20.0,
   "capacity_gb": 19.5,
   "used_ratio": 0.007,
   "inode_ratio": 0.001,
   "growth_gb_per_day": -0.007,
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
   "days_to_full": 198047,
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
   "namespace": "monitoring",
   "name": "server-volume-vm-single-0",
   "target": "monitoring/server-volume-vm-single-0",
   "prod": false,
   "phase": "Bound",
   "storage_class": "gp3",
   "requested_gb": 50.0,
   "capacity_gb": 48.9,
   "used_ratio": 0.003,
   "inode_ratio": 0.0,
   "growth_gb_per_day": 0.012,
   "days_to_full": 4229,
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
   "growth_gb_per_day": 0.0,
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
 "tenants_total": 10
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
 "tenants_total": 10
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
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-runners</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": 0.398,
 "cpu_requests": 0.0,
 "cpu_share_of_cluster_p95": 0.334,
 "has_quota": false,
 "kind": "ci",
 "memory_p95_7d_gb": 1.82,
 "memory_requests_gb": 0.0,
 "namespace": "arc-runners",
 "pods": 0,
 "prod": false,
 "shares_nodes_with_prod": false,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.dev-app-s</code></summary>

```json
{
 "burst_ratio_7d": 1.8,
 "cpu_p95_7d": 0.057,
 "cpu_requests": 0.4,
 "cpu_share_of_cluster_p95": 0.048,
 "has_quota": false,
 "kind": "dev",
 "memory_p95_7d_gb": 0.91,
 "memory_requests_gb": 1.25,
 "namespace": "dev-app-s",
 "pods": 5,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-w</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.004,
 "cpu_requests": 0.1,
 "cpu_share_of_cluster_p95": 0.004,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.21,
 "memory_requests_gb": 0.25,
 "multi_org": false,
 "namespace": "prod-app-w",
 "pods": 2,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-t</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.015,
 "cpu_requests": 0.29,
 "cpu_share_of_cluster_p95": 0.012,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.81,
 "memory_requests_gb": 0.84,
 "multi_org": false,
 "namespace": "prod-app-t",
 "pods": 5,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-x</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.007,
 "cpu_requests": 1.1,
 "cpu_share_of_cluster_p95": 0.006,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 2.89,
 "memory_requests_gb": 2.25,
 "multi_org": false,
 "namespace": "prod-app-x",
 "pods": 3,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-s</code></summary>

```json
{
 "burst_ratio_7d": 1.7,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.12,
 "cpu_requests": 0.35,
 "cpu_share_of_cluster_p95": 0.1,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.89,
 "memory_requests_gb": 1.62,
 "multi_org": false,
 "namespace": "prod-app-s",
 "pods": 8,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-y</code></summary>

```json
{
 "burst_ratio_7d": 1.4,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.037,
 "cpu_requests": 0.51,
 "cpu_share_of_cluster_p95": 0.031,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 3.43,
 "memory_requests_gb": 8.0,
 "multi_org": false,
 "namespace": "prod-app-y",
 "pods": 8,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-z-backend</code></summary>

```json
{
 "burst_ratio_7d": 21.1,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.012,
 "cpu_requests": 2.72,
 "cpu_share_of_cluster_p95": 0.01,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 11.29,
 "memory_requests_gb": 14.53,
 "multi_org": false,
 "namespace": "prod-app-z-backend",
 "pods": 9,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-r</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.006,
 "cpu_requests": 0.62,
 "cpu_share_of_cluster_p95": 0.005,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.72,
 "memory_requests_gb": 1.28,
 "multi_org": false,
 "namespace": "prod-app-r",
 "pods": 3,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.prod-app-v</code></summary>

```json
{
 "burst_ratio_7d": 3.3,
 "cluster_saturated_7d": false,
 "cpu_p95_7d": 0.025,
 "cpu_requests": 0.25,
 "cpu_share_of_cluster_p95": 0.021,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.13,
 "memory_requests_gb": 1.12,
 "multi_org": false,
 "namespace": "prod-app-v",
 "pods": 4,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 10
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-2-249</code></summary>

```json
{
 "allocatable_memory_gb": 3.2,
 "containers_without_memory_limit": 1,
 "memory_limit_overcommit": 1.63,
 "memory_limits_gb": 5.2,
 "memory_requests_gb": 2.0,
 "namespaces": {
  "monitoring": 3,
  "argocd": 1,
  "external-secrets": 1,
  "keda": 1,
  "kube-system": 1,
  "middleware": 1,
  "prod-app-t": 1,
  "prod-app-x": 1
 },
 "node": "node-2-249",
 "pool": "system-ondemand",
 "prod_pods": 2,
 "tenant_count": 2,
 "tenant_kinds": [
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
 "cpu_p95_7d": 0.012,
 "has_limitrange": false,
 "kind": "prod",
 "memory_p95_7d_gb": 11.29,
 "multi_org": false,
 "namespace": "prod-app-z-backend",
 "pods": 9,
 "prod": true
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.argocd/argocd-server</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-argocd-argocdse-74c4dcbda2",
 "target": "argocd/argocd-server",
 "workloads": [
  "deployment/argocd-server"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.middleware/kafka-ui</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-middlewa-kafkaui-0a6256c8b2",
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
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-middlewa-redisins-e7e7fd218a",
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
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-monitori-kubeprom-af0f3aa6c7",
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
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-monitori-vmauth-e07e5153ee",
 "target": "monitoring/vmauth",
 "workloads": [
  "deployment/vmauth"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-w/app-w</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodcarp-carpenst-e238817282",
 "target": "prod-app-w/app-w",
 "workloads": [
  "deployment/app-w"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-t/app-t-ai</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodcurt-curtainc-fc2d368787",
 "target": "prod-app-t/app-t-ai",
 "workloads": [
  "deployment/app-t-ai"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-t/app-t-backend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodcurt-curtainc-bb495c72c8",
 "target": "prod-app-t/app-t-backend",
 "workloads": [
  "deployment/app-t-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-t/app-t-studio</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodcurt-curtainc-57e5adf3bf",
 "target": "prod-app-t/app-t-studio",
 "workloads": [
  "deployment/app-t-studio"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-t/app-t-web</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodcurt-curtainc-022a51fc31",
 "target": "prod-app-t/app-t-web",
 "workloads": [
  "deployment/app-t-web"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-x/app-x-api</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodfand-apppa-754a9b50b2",
 "target": "prod-app-x/app-x-api",
 "workloads": [
  "deployment/app-x-api"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-y/app-y-admin</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodinse-insertoo-37417ab44f",
 "target": "prod-app-y/app-y-admin",
 "workloads": [
  "deployment/app-y-admin"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-y/app-y-ai</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodinse-insertoo-b22674073c",
 "target": "prod-app-y/app-y-ai",
 "workloads": [
  "deployment/app-y-ai"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-y/app-y-backend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodinse-insertoo-89a3732998",
 "target": "prod-app-y/app-y-backend",
 "workloads": [
  "deployment/app-y-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-y/app-y-frontend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodinse-insertoo-032c25d752",
 "target": "prod-app-y/app-y-frontend",
 "workloads": [
  "deployment/app-y-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-z-backend/app-z-backend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodrhem-appnbac-8c88bb317a",
 "target": "prod-app-z-backend/app-z-backend",
 "workloads": [
  "deployment/app-z-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-z-backend/app-z-frontend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodrhem-appnfro-9726e5b1d3",
 "target": "prod-app-z-backend/app-z-frontend",
 "workloads": [
  "deployment/app-z-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-r/app-r-backend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodsoro-appmba-f68effe430",
 "target": "prod-app-r/app-r-backend",
 "workloads": [
  "deployment/app-r-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-r/app-r-web</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodsoro-appmwe-194ae69849",
 "target": "prod-app-r/app-r-web",
 "workloads": [
  "deployment/app-r-web"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-v/app-v-admin-frontend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodtoot-appka-d0c066d282",
 "target": "prod-app-v/app-v-admin-frontend",
 "workloads": [
  "deployment/app-v-admin-frontend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-v/app-v-backend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodtoot-appkb-7df87a92cc",
 "target": "prod-app-v/app-v-backend",
 "workloads": [
  "deployment/app-v-backend"
 ]
}
```

</details>
<details><summary><code>traffic.alb-deregistration-vs-grace.prod-app-v/app-v-frontend</code></summary>

```json
{
 "backend_grace_s": 30,
 "backend_prestop": false,
 "deregistration_delay_s": 300,
 "lb_type": "application",
 "name": "k8s-prodtoot-appkf-36f816b829",
 "target": "prod-app-v/app-v-frontend",
 "workloads": [
  "deployment/app-v-frontend"
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
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-s/app-s-admin</code></summary>

```json
{
 "hosts": [
  "canary-admin.lab-l.example",
  "admin.lab-l.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 4.0,
  "requests_24h_equiv": 4.0,
  "rps_avg": 0.0,
  "errors_5xx": 1.0,
  "errors_ratio": 0.25,
  "p95_s_max_1h": 0.0087,
  "p95_s_avg": 0.0057,
  "p95_s_weighted": 0.0072,
  "p95_s_last_1h": 0.0087,
  "p95_s_last_at": "2026-11-14T13:11:00+00:00",
  "requests_last_1h": 3.0,
  "hours_since_requests": 3,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-prodillu-appi-2bcc150443"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-s/app-s-admin"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-v/app-v-backend</code></summary>

```json
{
 "hosts": [
  "api.lab-n.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 1099.0,
  "requests_24h_equiv": 1099.0,
  "rps_avg": 0.013,
  "errors_5xx": 3.0,
  "errors_ratio": 0.00273,
  "p95_s_max_1h": 0.3171,
  "p95_s_avg": 0.1244,
  "p95_s_weighted": 0.1442,
  "p95_s_last_1h": 0.2106,
  "p95_s_last_at": "2026-11-14T16:11:00+00:00",
  "requests_last_1h": 248.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-prodtoot-appkb-7df87a92cc"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-v/app-v-backend"
}
```

</details>
<details><summary><code>traffic.ingress-5xx-ratio.prod-app-v/app-v-frontend</code></summary>

```json
{
 "hosts": [
  "lab-n.example",
  "www.lab-n.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 9936.0,
  "requests_24h_equiv": 9936.0,
  "rps_avg": 0.115,
  "errors_5xx": 30.0,
  "errors_ratio": 0.00302,
  "p95_s_max_1h": 0.5584,
  "p95_s_avg": 0.2248,
  "p95_s_weighted": 0.2291,
  "p95_s_last_1h": 0.1716,
  "p95_s_last_at": "2026-11-14T16:11:00+00:00",
  "requests_last_1h": 459.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 1.0,
  "unhealthy_now": 1,
  "target_groups": [
   "k8s-prodtoot-appkf-36f816b829"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-v/app-v-frontend"
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-t/app-t-ai</code></summary>

```json
{
 "hosts": [
  "app-t-ai.lab-k.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 21.0,
  "requests_24h_equiv": 21.0,
  "rps_avg": 0.0,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 2.594,
  "p95_s_avg": 2.4951,
  "p95_s_weighted": 2.5752,
  "p95_s_last_1h": 2.3962,
  "p95_s_last_at": "2026-11-14T03:11:00+00:00",
  "requests_last_1h": 2.0,
  "hours_since_requests": 13,
  "unhealthy_max_24h": 0,
  "unhealthy_now": 0,
  "target_groups": [
   "k8s-prodcurt-curtainc-fc2d368787"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-t/app-t-ai"
}
```

</details>
<details><summary><code>traffic.ingress-p95-latency.prod-app-t/app-t-backend</code></summary>

```json
{
 "hosts": [
  "app-t-api.lab-k.example"
 ],
 "metrics": {
  "source": "alb-cloudwatch",
  "window": "24h",
  "requests": 6089.0,
  "requests_24h_equiv": 6089.0,
  "rps_avg": 0.07,
  "errors_5xx": 0,
  "errors_ratio": 0.0,
  "p95_s_max_1h": 5.5776,
  "p95_s_avg": 0.9403,
  "p95_s_weighted": 1.5415,
  "p95_s_last_1h": 0.0385,
  "p95_s_last_at": "2026-11-14T16:11:00+00:00",
  "requests_last_1h": 263.0,
  "hours_since_requests": 0,
  "unhealthy_max_24h": 1.0,
  "unhealthy_now": 1,
  "target_groups": [
   "k8s-prodcurt-curtainc-bb495c72c8"
  ]
 },
 "metrics_read": true,
 "target": "prod-app-t/app-t-backend"
}
```

</details>
<details><summary><code>vpccni.ec2-api-errors.node-1-21</code></summary>

```json
{
 "ec2_api_errors": 11,
 "metrics": {
  "available": true,
  "assigned": 23,
  "total": 27,
  "eni_allocated": 3,
  "eni_max": 3,
  "ip_max": 27,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 11,
  "ec2_api_errors_by_api": {
   "DeleteNetworkInterface": 11
  },
  "per_eni": {
   "eni-00e1a821abf4624ce": 9,
   "eni-06014368296be1b31": 8,
   "eni-0bfe5017301402fd5": 6
  }
 },
 "metrics_available": true,
 "node": "node-1-21"
}
```

</details>
<details><summary><code>vpccni.ec2-api-errors.node-2-149</code></summary>

```json
{
 "ec2_api_errors": 4,
 "metrics": {
  "available": true,
  "assigned": 9,
  "total": 18,
  "eni_allocated": 2,
  "eni_max": 3,
  "ip_max": 27,
  "prefixes": 0,
  "no_available_ip_events": 0,
  "force_removed_enis": 0,
  "force_removed_ips": 0,
  "ec2_api_errors": 4,
  "ec2_api_errors_by_api": {
   "DeleteNetworkInterface": 4
  },
  "per_eni": {
   "eni-03f378d4fbf15ec6d": 8,
   "eni-087546f86141ca130": 1
  }
 },
 "metrics_available": true,
 "node": "node-2-149"
}
```

</details>
<details><summary><code>coredns.cache-hit-low.cluster</code></summary>

```json
{
 "cache_hit_ratio": 0.2137,
 "cache_ttl": 30,
 "forward_nxdomain_ratio": 0.434,
 "metrics_available": true,
 "qps_total": 5.93
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "containers": 97,
 "emptydir_without_sizelimit": 21,
 "emptydir_without_sizelimit_prod": [
  "prod-app-t/statefulset/app-t-backend-postgresql",
  "prod-app-x/statefulset/app-x-postgresql",
  "prod-app-z-backend/deployment/app-z-embedding-server",
  "prod-app-z-backend/deployment/app-ad",
  "prod-app-r/deployment/app-r-backend",
  "prod-app-r/statefulset/app-r-postgresql"
 ],
 "prod_without_request": 32,
 "request_ratio": 0.01,
 "with_request": 1
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-116</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-116",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 7.2,
  "loadavg": "0.04 0.08 0.02",
  "nproc": 2,
  "mem_total_gb": 1.9,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 80,
  "containerd_rss_mb": 59,
  "k3s_rss_mb": null
 },
 "node": "node-1-116"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-138</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-138",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 3.6,
  "loadavg": "0.26 0.14 0.10",
  "nproc": 2,
  "mem_total_gb": 15.3,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 1,
  "kubelet_rss_mb": 110,
  "containerd_rss_mb": 78,
  "k3s_rss_mb": null
 },
 "node": "node-1-138"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-21</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-21",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 2.7,
  "loadavg": "0.17 0.18 0.13",
  "nproc": 2,
  "mem_total_gb": 15.3,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 2,
  "kubelet_rss_mb": 111,
  "containerd_rss_mb": 87,
  "k3s_rss_mb": null
 },
 "node": "node-1-21"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-224</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-224",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 0.6,
  "loadavg": "0.02 0.07 0.03",
  "nproc": 1,
  "mem_total_gb": 7.6,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 91,
  "containerd_rss_mb": 62,
  "k3s_rss_mb": null
 },
 "node": "node-1-224"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-1-65</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-1-65",
  "kernel": "5.10.245-245.983.amzn2.aarch64",
  "os": "Amazon Linux 2",
  "uptime_days": 0.6,
  "loadavg": "0.03 0.07 0.06",
  "nproc": 2,
  "mem_total_gb": 7.6,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 96,
  "containerd_rss_mb": 65,
  "k3s_rss_mb": null
 },
 "node": "node-1-65"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-2-149</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-2-149",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 6.4,
  "loadavg": "0.02 0.07 0.08",
  "nproc": 2,
  "mem_total_gb": 7.6,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 106,
  "containerd_rss_mb": 80,
  "k3s_rss_mb": null
 },
 "node": "node-2-149"
}
```

</details>
<details><summary><code>node.cgroup-v1.node-2-249</code></summary>

```json
{
 "cgroup": {
  "fs": "tmpfs",
  "version": "v1",
  "controllers": null
 },
 "collected": true,
 "meta": {
  "root": true,
  "hostname": "node-2-249",
  "kernel": "5.10.245-245.983.amzn2.x86_64",
  "os": "Amazon Linux 2",
  "uptime_days": 7.2,
  "loadavg": "0.27 0.09 0.06",
  "nproc": 2,
  "mem_total_gb": 3.7,
  "containerd_version": "1.7.29",
  "k3s_version": null,
  "zombies": 0,
  "kubelet_rss_mb": 107,
  "containerd_rss_mb": 82,
  "k3s_rss_mb": null
 },
 "node": "node-2-249"
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
<details><summary><code>scaling.hpa-never-scaled.prod-app-z-backend/deployment/app-z-backend</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 0,
 "days_since_last_scale": 29.2,
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
 "days_since_last_scale": 96.5,
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
<details><summary><code>albctl.aws-api-churn.cluster</code></summary>

```json
{
 "aws_api_calls_total": 250342,
 "aws_api_ops_by_calls": [
  [
   "Elastic Load Balancing v2/DescribeTargetHealth",
   78172
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroupAttributes",
   45151
  ],
  [
   "EC2/DescribeInstances",
   40158
  ],
  [
   "EC2/DescribeSecurityGroups",
   25519
  ],
  [
   "Elastic Load Balancing v2/RegisterTargets",
   12125
  ],
  [
   "Elastic Load Balancing v2/DeregisterTargets",
   12015
  ],
  [
   "Elastic Load Balancing v2/DescribeTags",
   9507
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancers",
   3860
  ],
  [
   "Elastic Load Balancing v2/DescribeRules",
   3860
  ],
  [
   "ACM/DescribeCertificate",
   3619
  ],
  [
   "EC2/DescribeVpcs",
   3092
  ],
  [
   "Elastic Load Balancing v2/DescribeTargetGroups",
   1944
  ],
  [
   "Elastic Load Balancing v2/DescribeListeners",
   1930
  ],
  [
   "Elastic Load Balancing v2/DescribeLoadBalancerAttributes",
   1930
  ],
  [
   "Elastic Load Balancing v2/DescribeListenerCertificates",
   1326
  ],
  [
   "Shield/GetSubscriptionState",
   1260
  ],
  [
   "EC2/DescribeNetworkInterfaces",
   1080
  ],
  [
   "ACM/ListCertificates",
   682
  ],
  [
   "WAF Regional/GetWebACLForResource",
   665
  ],
  [
   "WAFV2/GetWebACLForResource",
   665
  ],
  [
   "Elastic Load Balancing v2/ModifyRule",
   626
  ],
  [
   "EC2/DescribeSubnets",
   604
  ],
  [
   "EC2/AuthorizeSecurityGroupIngress",
   203
  ],
  [
   "EC2/RevokeSecurityGroupIngress",
   202
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
   25
  ],
  [
   "Elastic Load Balancing v2/DeleteTargetGroup",
   25
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
   0.758
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
   "Elastic Load Balancing v2/ModifyRule",
   0.115
  ],
  [
   "Elastic Load Balancing v2/CreateRule",
   0.103
  ],
  [
   "Elastic Load Balancing v2/DeleteTargetGroup",
   0.102
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
   "Elastic Load Balancing v2/DeleteRule",
   0.077
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
<details><summary><code>albctl.target-group-without-tgb.cluster</code></summary>

```json
{
 "target_groups_read": true,
 "tgb_count": 39,
 "tgb_manual": [
  "dev-app-s/app-s-dev-mysql-tgb",
  "prod-app-t/app-t-prod-postgresql-tgb",
  "prod-app-s/app-s-prod-mysql-tgb",
  "prod-app-y/app-y-prod-mysql-tgb",
  "prod-app-z-backend/app-z-prod-neo4j-tgb",
  "prod-app-z-backend/app-z-prod-pg-proxy-tgb",
  "prod-app-v/app-v-prod-mysql-tgb"
 ],
 "traffic_target_groups_without_tgb": 1
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
 "applications_prod": 8,
 "notifications_configured": false,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "applications_prod": 8,
 "ignore_differences_apps": 2,
 "prod_tracking_moving_ref": [
  "argocd/application/app-w-prod",
  "argocd/application/app-t-prod",
  "argocd/application/app-x-prod",
  "argocd/application/app-s-prod",
  "argocd/application/app-y-prod",
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
<details><summary><code>controlplane.apiserver-slow-traces.cluster</code></summary>

```json
{
 "slow_traces": [
  {
   "op": "List",
   "count": 161
  },
  {
   "op": "Call conversion webhook",
   "count": 12
  },
  {
   "op": "Patch",
   "count": 4
  },
  {
   "op": "Get",
   "count": 3
  },
  {
   "op": "Create",
   "count": 2
  },
  {
   "op": "Update",
   "count": 1
  }
 ],
 "slow_traces_total": 183
}
```

</details>
<details><summary><code>coredns.aaaa-noise.cluster</code></summary>

```json
{
 "aaaa_ratio": 0.491,
 "cluster_ipv6": false,
 "metrics_available": true,
 "qps_total": 5.93
}
```

</details>
<details><summary><code>cost.idle-load-balancer.cluster</code></summary>

```json
{
 "idle_load_balancers": [
  "app-u-db-shared"
 ],
 "lb_monthly_usd_base": 49.28,
 "load_balancers": 3,
 "load_balancers_read": true,
 "nat_gateways": 1,
 "nat_monthly_usd_base": 43.07
}
```

</details>
<details><summary><code>cost.idle-node.node-1-224</code></summary>

```json
{
 "cpu_p95_ratio": 0.004292177133419504,
 "instance_type": "r8gd.medium",
 "memory_p95_ratio": 0.04600463673984627,
 "monthly_usd": 7.3,
 "node": "node-1-224",
 "pool": "default"
}
```

</details>
<details><summary><code>cost.idle-node.node-1-65</code></summary>

```json
{
 "cpu_p95_ratio": 0.006155694494005682,
 "instance_type": "m7g.large",
 "memory_p95_ratio": 0.2623382124185489,
 "monthly_usd": 24.16,
 "node": "node-1-65",
 "pool": "default"
}
```

</details>
<details><summary><code>ebscsi.controller-metrics-disabled.cluster</code></summary>

```json
{
 "addon_version": "v1.37.0-eksbuild.1",
 "api_errors_24h": {},
 "api_throttles_24h": null,
 "controller_metrics_enabled": false,
 "controller_metrics_series": 0,
 "controller_present": true,
 "version": "1.37.0"
}
```

</details>
<details><summary><code>ecr.no-lifecycle-policy.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "attestations": 159,
 "images": 728,
 "monthly_usd": 41.8,
 "repos_no_lifecycle": [
  "app-v",
  "bitnami/kafka",
  "bitnami/mysql"
 ],
 "repos_no_lifecycle_gib": 10.4,
 "repositories": 33,
 "total_gib": 389.0,
 "untagged": 201
}
```

</details>
<details><summary><code>ecr.no-replication.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "replication_rules": 0,
 "repos_mutable_prod": [
  "ecr-app-w-eks-prod",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-ai-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "repos_scan_off_prod": [
  "ecr-app-w-eks-prod",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "bitnami/mysql",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "total_gib": 389.0
}
```

</details>
<details><summary><code>ecr.tag-mutable-prod.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "digest_pinned": 2,
 "images_in_use": 81,
 "repos_mutable": [
  "app-v",
  "ecr-app-w-eks-prod",
  "bitnami/kafka",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-frontend-prod",
  "ecr-app-s-frontend-dev",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-admin-dev",
  "ecr-app-s-backend-dev",
  "ecr-app-s-api-dev",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-ai-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "repos_mutable_prod": [
  "ecr-app-w-eks-prod",
  "ecr-app-t-backend-eks-prod",
  "ecr-app-t-web-eks-prod",
  "ecr-app-r-postgresql-prod",
  "ecr-app-s-admin-eks-prod",
  "ecr-app-t-postgresql-prod",
  "ecr-app-x-postgresql-prod",
  "ecr-app-s-backend-eks-prod",
  "ecr-app-s-api-eks-prod",
  "ecr-app-y-frontend-eks-prod",
  "ecr-app-y-ai-prod",
  "ecr-app-y-admin-eks-prod",
  "ecr-app-z-embedding-eks-prod",
  "ecr-app-x-api-eks-prod",
  "app-v-admin-frontend-prod",
  "app-v-frontend-prod",
  "app-v-backend-prod",
  "ecr-app-s-frontend-eks-prod",
  "ecr-app-y-backend-eks-prod",
  "ecr-app-z-backend-eks-prod",
  "ecr-app-z-frontend-eks-prod",
  "ecr-app-t-ai-eks-prod",
  "ecr-app-t-studio-eks-prod",
  "ecr-app-r-web-eks-prod",
  "ecr-app-r-backend-eks-prod"
 ],
 "repos_with_latest_tag": [],
 "repositories": 33
}
```

</details>
<details><summary><code>ecr.untagged-images.ecr/registry/<account></code></summary>

```json
{
 "account": "<account>",
 "attestations": 159,
 "images": 728,
 "repositories": 33,
 "untagged": 201
}
```

</details>
<details><summary><code>eso.version-old.cluster</code></summary>

```json
{
 "externalsecrets": 36,
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
  "totals_dashboard": 31,
  "totals_datasource": 4,
  "total_users": 6,
  "active_users": 6,
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
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "replicasets_total": 351,
 "replicasets_zero": 296,
 "revision_history_limits": {
  "10": 51,
  "3": 6
 }
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
  "expiration": 9,
  "emptiness": 371,
  "interruption": 284,
  "consolidation": 344
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
  "prod-app-y/scaledobject/app-y-ai-kafka-lag"
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
 "ct_invalid_dropped_1h": 642,
 "external_traffic_local": 0,
 "metrics_available": true,
 "no_local_endpoint_services": 0
}
```

</details>
<details><summary><code>logs.signatures.karpenter.spot-interruption</code></summary>

```json
{
 "count": 6,
 "first": "2026-11-13T22:47:26Z",
 "last": "2026-11-14T03:04:07Z",
 "warn_at": 3,
 "fail_at": 50,
 "files": {
  "logs/pods/karpenter/karpenter_karpenter.log": 6
 },
 "samples": [
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-13T22:47:26.757771911Z {\"level\":\"INFO\",\"time\":\"2026-11-13T22:47:26.757Z\",\"logger\":\"controller\",\"message\":\"initiating delete from interruption message\",\"commit\":\"490ef94\",\"controller\":\"inter",
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-13T23:36:17.623108628Z {\"level\":\"INFO\",\"time\":\"2026-11-13T23:36:17.622Z\",\"logger\":\"controller\",\"message\":\"initiating delete from interruption message\",\"commit\":\"490ef94\",\"controller\":\"inter",
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T01:43:29.269677375Z {\"level\":\"INFO\",\"time\":\"2026-11-14T01:43:29.269Z\",\"logger\":\"controller\",\"message\":\"initiating delete from interruption message\",\"commit\":\"490ef94\",\"controller\":\"inter",
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T02:25:52.433219469Z {\"level\":\"INFO\",\"time\":\"2026-11-14T02:25:52.433Z\",\"logger\":\"controller\",\"message\":\"initiating delete from interruption message\",\"commit\":\"490ef94\",\"controller\":\"inter",
  "[pod/karpenter-9769889bd-pkxd2/controller] 2026-11-14T02:33:25.165765521Z {\"level\":\"INFO\",\"time\":\"2026-11-14T02:33:25.165Z\",\"logger\":\"controller\",\"message\":\"initiating delete from interruption message\",\"commit\":\"490ef94\",\"controller\":\"inter"
 ]
}
```

</details>
<details><summary><code>loki.version-old.monitoring/statefulset/loki-stack</code></summary>

```json
{
 "compactor_running": 1.0,
 "major": 2,
 "present": true,
 "retention_applied": true,
 "storage": "emptyDir",
 "target": "monitoring/statefulset/loki-stack",
 "version": "2.6.1"
}
```

</details>
<details><summary><code>observability.alert-metric-without-dashboard.grafana</code></summary>

```json
{
 "alert_metrics": 172,
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
  "app-s_failure_total",
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
  "reloader_last_reload_successful"
 ],
 "alert_metrics_without_panel_count": 132,
 "available": true,
 "panel_metrics": 223,
 "read": 31
}
```

</details>
<details><summary><code>observability.alerts-never-fired.cluster</code></summary>

```json
{
 "fired_15d": [
  "CPUThrottlingHigh",
  "InfoInhibitor",
  "KubeControllerManagerDown",
  "KubeDeploymentReplicasMismatch",
  "KubeHpaMaxedOut",
  "KubePodCrashLooping",
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
  "KubeContainerWaiting",
  "KubeDaemonSetMisScheduled",
  "KubeDaemonSetNotScheduled",
  "KubeDaemonSetRolloutStuck",
  "KubeDeploymentGenerationMismatch",
  "KubeDeploymentRolloutStuck",
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
 "never_fired_count": 128,
 "rules_total": 141
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "ingresses": 30,
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "latency": true,
   "traffic": true,
   "errors": true,
   "saturation": false,
   "source": "alb-cloudwatch",
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
   "ingress": "app-r-backend",
   "class": "alb",
   "hosts": [
    "app-r-api.lab-k.example"
   ],
   "services": [
    "app-r-backend"
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
   "ingress": "app-r-web",
   "class": "alb",
   "hosts": [
    "app-r.lab-k.example"
   ],
   "services": [
    "app-r-web"
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
   "namespace": "prod-app-v",
   "ingress": "app-v-admin-frontend",
   "class": "alb",
   "hosts": [
    "admin.lab-n.example"
   ],
   "services": [
    "app-v-admin-frontend"
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
   "namespace": "prod-app-v",
   "ingress": "app-v-backend",
   "class": "alb",
   "hosts": [
    "api.lab-n.example"
   ],
   "services": [
    "app-v-backend"
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
  "dev-app-s",
  "middleware",
  "monitoring",
  "prod-app-s"
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
  },
  {
   "depth": 1,
   "receiver": "slack-sre",
   "matchers": [
    "source=\"onprem\""
   ],
   "continue": false,
   "group_by": [
    "alertname",
    "host"
   ],
   "repeat_interval": null
  }
 ]
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "error_lines_unclassified": 35,
 "files_scanned": [
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
  "logs/pods/vpc-cni/kube-system_aws-node.log",
  "logs/node/node-1-224/containerd-24h.log",
  "logs/node/node-1-224/ipamd-24h.log",
  "logs/node/node-1-224/kubelet-24h.log",
  "logs/node/node-1-65/containerd-24h.log",
  "logs/node/node-1-65/ipamd-24h.log",
  "logs/node/node-1-65/kubelet-24h.log",
  "logs/node/node-2-249/containerd-24h.log",
  "logs/node/node-2-249/kubelet-24h.log"
 ],
 "lines_scanned": 20959,
 "unclassified_errors": [
  {
   "pattern": "grafana | logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=owner@lab-k.example fromAlert=false t=<ts> …",
   "count": 8,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 8
   },
   "sample": "[pod/kube-prometheus-stack-grafana-5d7c56949c-qspbz/grafana] 2026-11-13T17:13:00.725975323Z logger=tsdb.loki endpoint=queryData pluginId=loki dsName=Loki dsUID=P8E80F9AEF21F6940 uname=owner@lab-k.example fromAlert=false t=2026-11-13T17:13:0"
  },
  {
   "pattern": "ebs-csi | \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node …",
   "count": 4,
   "files": {
    "logs/pods/ebs-csi/kube-system_ebs-csi-node-windows.log": 2,
    "logs/pods/ebs-csi/kube-system_ebs-csi-node.log": 2
   },
   "sample": "[pod/ebs-csi-node-4k7gt/ebs-plugin] 2026-11-14T03:05:08.768288390Z E1114 03:05:08.768177       1 node.go:857] \"Unexpected failure when attempting to remove node taint(s)\" err=\"isAllocatableSet: driver not found on node node-1-65.ap-north"
  },
  {
   "pattern": "kube-proxy | \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted on all …",
   "count": 2,
   "files": {
    "logs/pods/kube-proxy/kube-system_kube-proxy.log": 2
   },
   "sample": "[pod/kube-proxy-5kf5j/kube-proxy] 2026-11-14T03:04:58.845969164Z E1114 03:04:58.845929       1 server.go:234] \"Kube-proxy configuration may be incomplete or incorrect\" err=\"nodePortAddresses is unset; NodePort connections will be accepted o"
  },
  {
   "pattern": "node:node-1-224 | time=\"<ts>\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods\" error=\"cni …",
   "count": 2,
   "files": {
    "logs/node/node-1-224/containerd-24h.log": 2
   },
   "sample": "2026-11-14T02:26:28+0000 node-1-224 containerd[850]: time=\"2026-11-14T02:26:28.609577497Z\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods\" error=\"cni config load failed:"
  },
  {
   "pattern": "node:node-1-224 | \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"ip-10-0-1-<n>.ap-northeast-2.compute.internal\\\" not …",
   "count": 2,
   "files": {
    "logs/node/node-1-224/kubelet-24h.log": 2
   },
   "sample": "2026-11-14T02:26:40+0000 node-1-224 kubelet[1497]: E1114 02:26:40.442279    1497 eviction_manager.go:292] \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"node-1-224."
  },
  {
   "pattern": "node:node-1-65 | time=\"<ts>\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods\" error=\"cni …",
   "count": 2,
   "files": {
    "logs/node/node-1-65/containerd-24h.log": 2
   },
   "sample": "2026-11-14T03:04:42+0000 node-1-65 containerd[822]: time=\"2026-11-14T03:04:42.409511861Z\" level=error msg=\"failed to load cni during init, please check CRI plugin status before setting up network for pods\""
  },
  {
   "pattern": "node:node-1-65 | \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"node-1-65\\\" not …",
   "count": 2,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 2
   },
   "sample": "2026-11-14T03:04:50+0000 node-1-65 kubelet[1505]: E1114 03:04:50.392394    1505 eviction_manager.go:292] \"Eviction manager: failed to get summary stats\" err=\"failed to get node info: node \\\"node-1-65.ap"
  },
  {
   "pattern": "node:node-1-224 | time=\"<ts>\" level=error msg=\"failed to reload cni configuration after receiving fs change event(WRITE         …",
   "count": 1,
   "files": {
    "logs/node/node-1-224/containerd-24h.log": 1
   },
   "sample": "2026-11-14T02:26:55+0000 node-1-224 containerd[1383]: time=\"2026-11-14T02:26:55.117894470Z\" level=error msg=\"failed to reload cni configuration after receiving fs change event(WRITE         \\\"/etc/cni/net."
  },
  {
   "pattern": "node:node-1-224 | {\"level\":\"error\",\"ts\":\"<ts>\",\"caller\":\"awsutils/awsutils.go:<n>\",\"msg\":\"r8gd.medium: instance type does not exist\"}",
   "count": 1,
   "files": {
    "logs/node/node-1-224/ipamd-24h.log": 1
   },
   "sample": "{\"level\":\"error\",\"ts\":\"2026-11-14T02:26:53.245Z\",\"caller\":\"awsutils/awsutils.go:1618\",\"msg\":\"r8gd.medium: instance type does not exist\"}"
  },
  {
   "pattern": "node:node-1-224 | \"RuntimeConfig from runtime service failed\" err=\"rpc error: code = Unimplemented desc = unknown method RuntimeConfig for service …",
   "count": 1,
   "files": {
    "logs/node/node-1-224/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T02:26:40+0000 node-1-224 kubelet[1497]: E1114 02:26:40.224657    1497 log.go:32] \"RuntimeConfig from runtime service failed\" err=\"rpc error: code = Unimplemented desc = unknown method RuntimeCon"
  },
  {
   "pattern": "node:node-1-224 | \"Error getting the current node from lister\" err=\"node \\\"ip-10-0-1-<n>.ap-northeast-2.compute.internal\\\" not found\"",
   "count": 1,
   "files": {
    "logs/node/node-1-224/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T02:26:40+0000 node-1-224 kubelet[1497]: E1114 02:26:40.352357    1497 kubelet_node_status.go:466] \"Error getting the current node from lister\" err=\"node \\\"node-1-224.ap-northeast-2.compute.in"
  },
  {
   "pattern": "node:node-1-224 | \"eviction manager: failed to check if we have separate container filesystem. Ignoring.\" err=\"no imagefs label for configured runtime\"",
   "count": 1,
   "files": {
    "logs/node/node-1-224/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T02:26:40+0000 node-1-224 kubelet[1497]: E1114 02:26:40.442256    1497 eviction_manager.go:267] \"eviction manager: failed to check if we have separate container filesystem. Ignoring.\" err=\"no ima"
  },
  {
   "pattern": "node:node-1-224 | \"Error updating node status, will retry\" err=\"error getting node \\\"ip-10-0-1-<n>.ap-northeast-2.compute.internal\\\": node …",
   "count": 1,
   "files": {
    "logs/node/node-1-224/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T02:26:40+0000 node-1-224 kubelet[1497]: E1114 02:26:40.824559    1497 kubelet_node_status.go:554] \"Error updating node status, will retry\" err=\"error getting node \\\"node-1-224.ap-northeast-2."
  },
  {
   "pattern": "node:node-1-65 | \"RuntimeConfig from runtime service failed\" err=\"rpc error: code = Unimplemented desc = unknown method RuntimeConfig for service …",
   "count": 1,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T03:04:50+0000 node-1-65 kubelet[1505]: E1114 03:04:50.256004    1505 log.go:32] \"RuntimeConfig from runtime service failed\" err=\"rpc error: code = Unimplemented desc = unknown method RuntimeConf"
  },
  {
   "pattern": "node:node-1-65 | \"Error getting the current node from lister\" err=\"node \\\"node-1-65\\\" not found\"",
   "count": 1,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T03:04:50+0000 node-1-65 kubelet[1505]: E1114 03:04:50.352906    1505 kubelet_node_status.go:466] \"Error getting the current node from lister\" err=\"node \\\"node-1-65.ap-northeast-2.compute.inte"
  },
  {
   "pattern": "node:node-1-65 | \"eviction manager: failed to check if we have separate container filesystem. Ignoring.\" err=\"no imagefs label for configured runtime\"",
   "count": 1,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T03:04:50+0000 node-1-65 kubelet[1505]: E1114 03:04:50.392008    1505 eviction_manager.go:267] \"eviction manager: failed to check if we have separate container filesystem. Ignoring.\" err=\"no imag"
  },
  {
   "pattern": "node:node-1-65 | \"Error updating node status, will retry\" err=\"error getting node \\\"node-1-65\\\": node …",
   "count": 1,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T03:04:50+0000 node-1-65 kubelet[1505]: E1114 03:04:50.860816    1505 kubelet_node_status.go:554] \"Error updating node status, will retry\" err=\"error getting node \\\"node-1-65.ap-northeast-2.co"
  },
  {
   "pattern": "node:node-1-65 | Error while processing event …",
   "count": 1,
   "files": {
    "logs/node/node-1-65/kubelet-24h.log": 1
   },
   "sample": "2026-11-14T03:04:51+0000 node-1-65 kubelet[1505]: W1114 03:04:51.317322    1505 watcher.go:93] Error while processing event (\"/sys/fs/cgroup/devices/kubepods.slice/kubepods-burstable.slice/kubepods-burstab"
  },
  {
   "pattern": "node:node-2-249 | time=\"<ts>\" level=error msg=\"ContainerStatus for \\\"903248a58add682ae3459b665f034b0b56f26badbe2df8fd793c2af4a420c744\\\" failed\" error=\"rpc …",
   "count": 1,
   "files": {
    "logs/node/node-2-249/containerd-24h.log": 1
   },
   "sample": "2026-11-13T17:26:28+0000 node-2-249 containerd[3609]: time=\"2026-11-13T17:26:28.517955629Z\" level=error msg=\"ContainerStatus for \\\"903248a58add682ae3459b665f034b0b56f26badbe2df8fd793c2af4a420c744\\\" failed\""
  },
  {
   "pattern": "node:node-2-249 | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container …",
   "count": 1,
   "files": {
    "logs/node/node-2-249/kubelet-24h.log": 1
   },
   "sample": "2026-11-13T17:26:28+0000 node-2-249 kubelet[3733]: E1113 17:26:28.518090    3733 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try t"
  }
 ]
}
```

</details>
<details><summary><code>observability.unstructured-logs.argocd</code></summary>

```json
{
 "json_lines_1h": 0,
 "json_ratio": 0.0,
 "lines_1h": 8745,
 "namespace": "argocd"
}
```

</details>
<details><summary><code>prometheus.single-replica.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "present": true,
 "ready": 1,
 "replicas": 1,
 "restarts": 3,
 "start_time": "2026-11-14T14:34:31.949234438Z",
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
<details><summary><code>resilience.no-prestop.prod-app-w/app-w</code></summary>

```json
{
 "namespace": "prod-app-w",
 "name": "app-w",
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
<details><summary><code>resilience.no-prestop.prod-app-z-backend/app-ad</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-ad",
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
<details><summary><code>resources.memory-request-overprovisioned.argocd/deploy/argocd-repo-server:repo-server</code></summary>

```json
{
 "labels": {
  "namespace": "argocd",
  "pod": "argocd-repo-server-d487895cc-g4nzz",
  "container": "repo-server"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.18751296997070313,
  "memory_p95_7d_bytes": 100670259.2,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.dev-app-s/deploy/app-s-backend:backend</code></summary>

```json
{
 "labels": {
  "namespace": "dev-app-s",
  "pod": "app-s-backend-5c455594cd-s87gg",
  "container": "backend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.30875244140625,
  "memory_p95_7d_bytes": 82880102.4,
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
  "memory_request_p95_ratio_7d": 0.0975341796875,
  "memory_p95_7d_bytes": 26181632.0,
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
  "memory_request_p95_ratio_7d": 0.0259246826171875,
  "memory_p95_7d_bytes": 6959104.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.monitoring/deploy/kube-prometheus-stack-grafana:grafana</code></summary>

```json
{
 "labels": {
  "namespace": "monitoring",
  "pod": "kube-prometheus-stack-grafana-5d7c56949c-qspbz",
  "container": "grafana"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.26830851236979164,
  "memory_p95_7d_bytes": 108035276.79999998,
  "container_memory_request_bytes": 402653184.0
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
  "memory_request_p95_ratio_7d": 0.2126922607421875,
  "memory_p95_7d_bytes": 57094144.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-x/sts/app-x-postgresql:postgresql</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-x",
  "pod": "app-x-postgresql-0",
  "container": "postgresql"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.1280517578125,
  "memory_p95_7d_bytes": 34373632.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-ai:ai</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-ai-55b7448547-5g592",
   "container": "ai"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.2071552276611328,
   "memory_p95_7d_bytes": 444862464.0,
   "container_memory_request_bytes": 2147483648.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-ai-55b7448547-tcvrf",
   "container": "ai"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.20787429809570312,
   "memory_p95_7d_bytes": 446406656.0,
   "container_memory_request_bytes": 2147483648.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-y/deploy/app-y-backend:backend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-ppqmd",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.15367965698242186,
   "memory_p95_7d_bytes": 82506137.6,
   "container_memory_request_bytes": 536870912.0
  }
 },
 {
  "labels": {
   "namespace": "prod-app-y",
   "pod": "app-y-backend-596479b6f8-ggksl",
   "container": "backend"
  },
  "values": {
   "memory_request_p95_ratio_7d": 0.14853668212890625,
   "memory_p95_7d_bytes": 79745024.0,
   "container_memory_request_bytes": 536870912.0
  }
 }
]
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.prod-app-z-backend/deploy/app-z-frontend:frontend</code></summary>

```json
{
 "labels": {
  "namespace": "prod-app-z-backend",
  "pod": "app-z-frontend-6d58bbfcfc-z9qmc",
  "container": "frontend"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.27606353759765623,
  "memory_p95_7d_bytes": 74105241.6,
  "container_memory_request_bytes": 268435456.0
 }
}
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
  "memory_request_p95_ratio_7d": 0.2334146499633789,
  "memory_p95_7d_bytes": 1002508288.0,
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
<details><summary><code>scaling.hpa-never-scaled.dev-app-s/deployment/app-s-admin</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 2,
 "days_since_last_scale": 177.9,
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
 "days_since_last_scale": 207.6,
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
 "current_cpu_utilization": 16,
 "days_since_last_scale": 78.4,
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
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-w/app-w</code></summary>

```json
{
 "namespace": "prod-app-w",
 "name": "app-w",
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
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-x/app-x-api</code></summary>

```json
{
 "namespace": "prod-app-x",
 "name": "app-x-api",
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
<details><summary><code>scaling.no-hpa-serving-prod.prod-app-z-backend/app-ad</code></summary>

```json
{
 "namespace": "prod-app-z-backend",
 "name": "app-ad",
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
<details><summary><code>tenancy.dev-shares-prod-nodes.node-1-21</code></summary>

```json
{
 "containers_without_memory_limit": 1,
 "cpu_limit_overcommit": 6.53,
 "dev_namespaces": [
  "dev-app-s"
 ],
 "dev_pods": 4,
 "memory_limit_overcommit": 1.02,
 "node": "node-1-21",
 "pool": "default",
 "prod_namespaces": [
  "prod-app-w",
  "prod-app-t",
  "prod-app-s",
  "prod-app-y",
  "prod-app-z-backend",
  "prod-app-r",
  "prod-app-v"
 ],
 "prod_pods": 16,
 "separation_possible": true,
 "shares_dev_prod": true
}
```

</details>
<details><summary><code>tenancy.dev-shares-prod-nodes.node-2-60</code></summary>

```json
{
 "containers_without_memory_limit": 2,
 "cpu_limit_overcommit": 2.18,
 "dev_namespaces": [
  "dev-app-s"
 ],
 "dev_pods": 1,
 "memory_limit_overcommit": 1.35,
 "node": "node-2-60",
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
<details><summary><code>traffic.alb-protection-off.k8s-lab-kprodlb-b18a4555d7</code></summary>

```json
{
 "access_logs": false,
 "deletion_protection": false,
 "name": "k8s-lab-kprodlb-b18a4555d7",
 "target_groups": 30,
 "type": "application"
}
```

</details>
<details><summary><code>vpccni.metrics-unreadable.cluster</code></summary>

```json
{
 "metrics_unavailable_nodes": [
  "node-1-117",
  "node-2-60"
 ],
 "nodes": 9
}
```

</details>

### 7-6. Tool notes (about kubegap itself)

1. traffic.db-exposed for middleware/kafka-controller-0-external says 'nothing in the cluster says' under declared in, yet the Service carries meta.helm.sh/release-name: kafka and helm list shows the release middleware/kafka (chart kafka-26.8.1). The Helm mark on a Service is not used when deciding where a resource is declared.
2. security.plaintext-secret-env flags TS_KUBE_SECRET of the tailscale container in prod-app-z-backend/app-ad. For Tailscale this variable holds the name of a Secret, not a credential; a name-based guess on the word SECRET catches it. An exception for TS_KUBE_SECRET, like the one for STAKATER_*, would remove the false positive.
3. resources.oomkilled for prometheus-kube-prometheus-stack-prometheus-0 prints 'restarts 3', the lifetime count of the pod, next to a 7-day window; resilience.oom_7d counts 1 restart in 7 days. The evidence reads as three recent OOM restarts.

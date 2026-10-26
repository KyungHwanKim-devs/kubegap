# default (k3s, nodes node-a and node-b) — full audit, 2026-10-26 16:27 KST

This cluster is the k3s v1.33.5 installation behind the kube context `default`: two nodes (node-a, a 6-CPU agent; node-b, a 12-CPU server with embedded etcd), 26 namespaces of which 7 are production, 152 pods, 23 detected components, profile `k3s`. Nothing is on fire right now. Both nodes are Ready, 0 pods are Pending, and the only pod that cannot run is `app-c-prod/app-c-coturn`, in a crash loop for 28 days. The one thing that changed since the 15:32 KST full run is that the HorizontalPodAutoscaler of `app-f-prod/app-f-api-server` scaled the Deployment from 2 to 5 replicas at 16:11 and 16:14 KST, the second time today, which puts the cluster back below the N+1 line. The five problems below are the same five as at 15:32 with the numbers of this snapshot; the HPA cycle has moved to the top. None of the actions has been started.

## The 5 problems to work on

### 1. app-f-api-server scaled 2 → 5 for the second time today on a 100m request, and the cluster no longer survives losing node-b
**Problem.** `app-f-prod/app-f-api-server` is the API behind the app-f app. Its HPA measures CPU against a request of 100m with a limit of 500m. When traffic rises the pods pass 60% of 100m within seconds, the HPA adds replicas, every new pod lands on node-a and is throttled by the 500m limit while it warms up, and when the burst ends the HPA steps back to 2. It did this between 13:35 and 14:17 KST, and again from 16:11 KST; at collection time the Deployment is still at 5 with CPU at 1% of request. The three extra pods add 300m of requests to node-a, so the total CPU requests of the cluster are now above what node-a alone can hold: if node-b fails, not everything comes back. Around the same mechanism, several other containers have CPU limits far below their burst need and stall for 31 to 44% of the time, and 13 database containers have liveness probes with a 1-second timeout that a throttled checkpoint can turn into a kill.

**Evidence.** The HPA scaled to 4 at 16:11:55 KST and to 5 at 16:14:40 KST with the reason "cpu resource utilization (percentage of request) above target" in events.json. The three new pods were throttled up to 73% at 16:18 KST and sit at 5% and 1% now in metrics/cpu_throttle_ratio_5m.json. CPU requests total 6.31 cores against 6.0 cores allocatable without node-b, so N+1 fails, in summary.json resilience.n_plus_one; it was 6.01 at 15:32. The HPA changed its desired count 20 times in 7 days in metrics/hpa_desired_changes_7d.json. app-e-postgres is throttled 44%, fluent-bit 33% and 31%, Elasticsearch 36%, Prometheus 41% measured during collection, in metrics/cpu_throttle_ratio_5m.json. 13 database containers have livenessProbe timeoutSeconds 1 in objects/statefulsets.apps.json and objects/deployments.json.

**Cause.** Confirmed for the scaling: the HPA divides usage by the request, and 100m is far below the real working point, so a small rise in traffic reads as a large percentage. Confirmed for the throttling: bursty processes carry CPU limits of 1.5 to 6 times their request and are cut by CFS bandwidth control. Likely: the traffic that started each burst cannot be named because the ingress controller exposes no request metrics (problem 5). Conflict resolution: the same containers are also flagged as CPU-over-requested; remove the limit first, read the new 7-day p95, then lower the request. app-f-api-server is the exception that needs a higher request, because the request is the HPA denominator. Memory limits are not removed; they are raised from the p95.

**Action.** ① app-f-api-server: requests.cpu 100m → 300m, delete limits.cpu, keep the 60% target. The HPA then scales only above a sustained 180m and new pods do not stall. Takes 15 minutes. ② app-e-postgres and the other 12 database containers: liveness and readiness timeoutSeconds 1 → 3, delete the CPU limit. Takes 30 minutes. ③ app-a-sandbox-watchdog CronJob: delete its CPU limit, delete the two failed Jobs 29853754 and 29881700 so KubeJobFailed resolves, and decide whether `*/5` is enough. Takes 30 minutes. ④ Prometheus limit 1 core with request 300m; Elasticsearch and fluent-bit limits at least 1 core. Takes 30 minutes. ⑤ app-a-postgres memory request 2Gi and limit 2.5Gi, app-a-backend request 1Gi, app-e-minio limit 1Gi, fluent-bit limit 256Mi. Takes 15 minutes. Expected effect: the HPA cycle stops, N+1 passes again, database probe kills stop, and three permanent alerts resolve.
```yaml
# Deployment app-f-api-server, container app
resources:
  requests: { cpu: 300m, memory: 1088Mi }   # 100m → 300m (HPA denominator)
- limits:   { cpu: 500m, memory: 2720Mi }
+ limits:   { memory: 2720Mi }               # CPU limit removed
```
```yaml
# StatefulSet app-e-postgres (same for the other 12 DB containers), container postgres
resources:
  requests: { cpu: 200m, memory: 128Mi }
- limits:   { cpu: 200m, memory: 384Mi }
+ limits:   { memory: 384Mi }
readinessProbe:
- timeoutSeconds: 1
+ timeoutSeconds: 3
livenessProbe:
- timeoutSeconds: 1
+ timeoutSeconds: 3
```

**Why this happens.**
- Principle: A CPU limit is enforced by the kernel's CFS bandwidth control once per 100 ms period. When the quota is used up the container waits for the rest of the period, which shows as latency and probe timeouts rather than as CPU usage. The HPA divides usage by the request, not the limit, so a small request with a low limit produces throttling and scale-out at the same time, and a 1-second probe turns a throttled checkpoint into a kill.
- Cases: The `resources.cpu-throttling` check definition cites Buffer 2020 (https://erickhun.com/posts/kubernetes-faster-services-no-cpu-limits/) and Omio 2020 (https://medium.com/omio-engineering/cpu-limits-and-aggressive-throttling-in-kubernetes-c5b20bd8a718). Both removed CPU limits to end throttling latency.
- Read next: "CFS bandwidth control (kernel sched-bwc.txt)", "Kubernetes docs: Resource Management for Pods and Containers (limits and QoS)", "Kubernetes docs: Horizontal Pod Autoscaling (algorithm details, utilization against requests)", "Kubernetes docs: Configure Liveness, Readiness and Startup Probes (timeoutSeconds)".

Evidence checks: `resilience.n-plus-one.cluster`, `resources.cpu-throttling.*` (fail 4, warn 2), `resilience.db-probe-timeout.*` (13), `resilience.exec-probe.*` (13), `resilience.liveness-dependency-path.*` (21), `resources.memory-limit-near-p95.*` (4), `resources.krr-recommendation.*` (30), `resources.cpu-request-overprovisioned.*` (18), `resources.memory-request-overprovisioned.*` (4), `traffic.pod-not-ready.app-f-prod/app-f-api-server` (→ pass), `traffic.pod-request-skew.app-f-prod/app-f-api-server`, `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog`, `observability.alert-firing-stale.CPUThrottlingHigh/monitoring`, `observability.alert-firing-stale.KubeJobFailed/app-a-prod`, `observability.alert-firing-stale.KubeCPUOvercommit`, `observability.alerts-always-firing.CPUThrottlingHigh`, `observability.alerts-always-firing.KubeJobFailed`, `observability.alerts-always-firing.KubeCPUOvercommit`, `scaling.hpa-flapping.app-f-prod/hpa/app-f-app-w`, `tenancy.burst-tenant-unbounded.app-f-prod`, `hygiene.change-correlation.cluster` (LLM)

### 2. 15 production apps can only run on node node-a because of a scheduling rule, and node-a rebooted yesterday without a shutdown
**Problem.** 15 Deployments in app-d-prod, app-f-prod, app-c-prod and app-g-prod carry a required nodeAffinity that says "avoid nodes labelled `role=observability`", and node-b carries exactly that label. They cannot move to node-b, so when node-a is down they stay down until node-a returns. app-d (2 replicas), app-f-app-x-client (2) and app-f-api-server (5 right now) declare a hostname topology spread with DoNotSchedule, but with one eligible node every replica lands on node-a, so adding replicas protects nothing. node-a came back without a shutdown sequence at 2026-10-25 13:21 KST, about 30 production pods were down for about 3 minutes, and the cause is still unknown. It has been up for 1.1 days since.

**Evidence.** 15 production Deployments have the single constraint `required nodeAffinity role NotIn [observability]` and `unavoidable pin reasons []` in summary.json resilience.placement. 4 workloads have all replicas on node-a: app-d 2/2, app-f-api-server 5/5, app-f-app-x-client 2/2 with "eligible nodes 1", and app-a-backend 2/2 with 2 eligible nodes and no spread declared, in findings-draft.json. 33 of 47 production pods are on node-a, 70%, in summary.json resilience.placement.prod_by_node; it was 30 of 44 at 15:32. node-b carries `role=observability` and `storage=node-b`, node-a has no label and there are no taints, in objects/nodes.json. 44 containers on node-a show exit 255 / Unknown and are classified "node reboot, not a crash" in summary.json resilience.restarts.by_cause. The 24-hour kernel log of node-a has 0 OOM, lockup or I/O error lines in summary.json nodeos.

**Cause.** Confirmed for the pin: the affinity was written to keep apps off the observability node, and with two nodes "not that node" became "only this node". The reboot cause is not in the snapshot: there is no previous-boot journal or `last -x` collector and the 24-hour kernel log of node-a is clean, so hardware, power and a manual reboot all remain open.

**Action.** ① Change `requiredDuringSchedulingIgnoredDuringExecution` to `preferredDuringSchedulingIgnoredDuringExecution` with weight 100 in the 15 Deployments, one Kustomize or Helm value, then a rolling restart. In normal operation they stay on node-a; when node-a fails they reschedule to node-b. Takes 30 minutes. ② Change the three DoNotSchedule spreads (app-d, app-f-app-x-client, app-f-api-server) to `whenUnsatisfiable: ScheduleAnyway` and add the same spread to app-a-backend. Takes 15 minutes. ③ On node-a run `sudo journalctl -b -1 -p err` and `last -x | head` to find the reboot cause and write it in the node notes. Takes 10 minutes. ④ Keep the pins that are really necessary (local-path PVs, app-f-embed's GPU, app-c-coturn's hostNetwork) and write the reason next to each.
```yaml
# spec.template.spec.affinity.nodeAffinity of each of the 15 Deployments — proposal
- requiredDuringSchedulingIgnoredDuringExecution:
-   nodeSelectorTerms:
-   - matchExpressions:
-     - { key: role, operator: NotIn, values: [observability] }
+ preferredDuringSchedulingIgnoredDuringExecution:
+ - weight: 100
+   preference:
+     matchExpressions:
+     - { key: role, operator: NotIn, values: [observability] }
```

**Why this happens.**
- Principle: Required node affinity is a hard filter in the scheduler's filtering phase and is applied before scoring and spreading. When the filter leaves one node, the replica count and topologySpreadConstraints cannot create any spread, and the availability of the workload equals the availability of that node. Preferred affinity is a score, so the same intent survives the loss of the preferred node.
- Cases: The `resilience.replicas-same-node` check definition records the Moonlight case, where two replicas on one node disappeared together when that node died. The year and URL are not in the check definition.
- Read next: "Kubernetes docs: Assigning Pods to Nodes (node affinity, required vs preferred)", "Kubernetes docs: Pod Topology Spread Constraints (whenUnsatisfiable)", "Google SRE Book ch. 3 Embracing Risk (availability as a product of dependencies)".

Evidence checks: `resilience.single-eligible-node.*` (15 avoidable), `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server`, `resilience.replicas-same-node.app-d-prod/deployment/app-d`, `resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client`, `resilience.replicas-same-node.app-a-prod/deployment/app-a-backend`, `hygiene.node-label-dependency.role`, `node.unclean-reboot.node-a`

### 3. The TURN server app-c-coturn in app-c-prod has been dead for 28 days and has restarted 7,896 times
**Problem.** `app-c-prod/app-c-coturn` is the TURN server that relays the app-c app's WebRTC calls across NAT. It exits with code 255 within one second of starting and sits in CrashLoopBackOff. The Deployment has 0 of 1 replicas available, so app-c calls that need relaying fail. This loop produces most of the cluster's noise: 250 BackOff events in 55 minutes, 2,983 kubelet "Error syncing pod" lines on node-a in 24 hours, 73 exited containers on node-a, and three alerts that have been firing for weeks and that nobody reads any more (KubePodCrashLooping, KubeDeploymentReplicasMismatch, and the app-c Argo CD app stuck in Progressing).

**Evidence.** The pod `app-c-coturn-549854dfcb-jgp4h` on node-a has 7,896 restarts, waiting reason CrashLoopBackOff, last termination Error exit 255 at 16:26:39 KST with start and finish in the same second, 0 Unhealthy events, in objects/pods.json; it had 7,885 at 15:32. BackOff events for this pod are cumulative 7,416 in events.json, 250 more than at 15:32. The 24-hour Ready ratio is 0.0003, 1,440 minutes not ready, in summary.json traffic.readiness.rows. logs/node/node-a/k3s-errors-24h.log holds 2,983 lines of `Error syncing pod … for "coturn" with CrashLoopBackOff`. KubePodCrashLooping has 20,160 firing samples in 7 days and 28.1 days of age, KubeDeploymentReplicasMismatch 20,005, both at the Watchdog level, in summary.json observability.alerts. The image is `coturn/coturn:latest`, a mutable tag, the container runs with hostNetwork pinned to node-a, CPU limit 200m, memory limit 128Mi, no probes, in objects/deployments.json.

**Cause.** Likely: a configuration or bind error at startup, since it exits 255 within one second with no probe involved. Candidates are a listening address or port that no longer exists on the host network, or a changed image behind the mutable tag. The container log was not collected because the pod never lives long enough for the log collector; the answer is in `kubectl logs --previous` of that pod.

**Action.** ① Read the last 20 lines with `kubectl -n app-c-prod logs deploy/app-c-coturn --previous`. Takes 2 minutes. ② Fix what it says (listening IP, port, realm or certificate path in the turnserver configuration), pin the image to a digest or fixed tag and redeploy. Takes 30 minutes. ③ If app-c no longer needs relaying, scale the Deployment to 0 in Git so Argo CD stops reporting Progressing and the two alerts resolve. Takes 5 minutes. Expected effect: the BackOff stream, the 2,983 kubelet error lines per day and the three permanent alerts disappear together.

**Why this happens.**
- Principle: CrashLoopBackOff is the kubelet's exponential restart delay for a container that exits on its own, from 10 seconds doubling to a 5-minute cap. The exit code tells the class of cause: OOMKilled 137 with a memory limit, a probe kill with Unhealthy events, or an application exit such as 255. Each class has a different fix. A Deployment with 0 available replicas is a full outage of that service regardless of the restart count.
- Cases: The `hygiene.mutable-image-tag` check definition records a home-cluster case in which a TURN server on `coturn/coturn:latest` crashed for 27 days, with an image change after a reboot as the likely cause. That record is this cluster.
- Read next: "Kubernetes docs: Container restart policy and CrashLoopBackOff", "coturn turnserver.conf listening-ip and relay-ip options", "Google SRE Book ch. 6 Monitoring Distributed Systems (alerts that page should require intelligent action)".

Evidence checks: `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `events.tracked-warning-reasons.BackOff`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `observability.alerts-always-firing.KubePodCrashLooping`, `observability.alerts-always-firing.KubeDeploymentReplicasMismatch`, `observability.alert-firing-stale.KubePodCrashLooping/app-c-prod`, `logs.signatures.kubelet.pod-sync-error`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `resilience.single-node-dependency.app-c-prod/deployment/app-c-coturn`, `node.cri-exited-containers.node-a`

### 4. Every backup lives on a node disk, and 7 Argo CD apps can prune a Namespace: two ways to lose data
**Problem.** All production databases run on local-path volumes, which are directories on a node disk, and the only copy of their data is a dump file written to the same kind of volume. Of the 7 dump CronJobs, 4 write to the same node as the database they dump and 3 to the other node; none sends a copy off the cluster. The k3s server's etcd snapshots are on node-b's own disk too. One failed node-b disk therefore removes 13 databases and their backups at once. Separately, 7 Argo CD Applications manage a Namespace object with automatic prune enabled. The day a Namespace manifest leaves Git (a directory move, a rename, a generator change), Argo CD deletes that Namespace with the PVCs inside it.

**Evidence.** No backup tool is present and the family `backup` is missing, with 5 local etcd snapshots and 7 backup-type CronJobs, in inventory.json. 4 CronJobs have dump PVC and source database both on node-b (app-d-postgres-backup, app-d-postgres-vn-backup, app-f-mysql-backup, app-g-postgres-backup) and 3 write to the other node (app-a-postgres-backup, app-d-postgres-mx-backup, app-e-postgres-backup), all 7 with `offsite_hint False`, in summary.json resilience.backup.rows. 2 production databases have no backup CronJob at all, app-c-postgres and app-i-postgres, in the same section. 19 production PVs have reclaim policy Delete, 0 VolumeSnapshot support, 26 node-pinned PVs, in findings-draft.json. 7 Applications with prune on manage a Namespace: app-a-prod, app-b-prod, acme-site, app-e-api, app-h, app-k, app-i-prod, in summary.json argocdctl.summary. node-b's local-path directories hold 138,272 MB across 19 PVs, of which `logging/data-elasticsearch-0` is 101,498 MB, in summary.json local_path.summary. Secrets are stored in etcd unencrypted, in findings-draft.json.

**Cause.** Confirmed: the backup CronJobs were written as "dump to a PVC" and a "copy elsewhere" step was never added. k3s was started without `--etcd-s3`. The Argo CD apps create their Namespace from a manifest and use the default `prune: true`.

**Action.** ① Add an off-node step to the 7 CronJobs: after the dump, `rclone copy` or `aws s3 cp` to object storage outside the cluster (MinIO on another machine, B2, S3), and add CronJobs for app-c-postgres and app-i-postgres. Takes 2 hours for all 9. ② Start k3s on node-b with `--etcd-s3 --etcd-s3-bucket … --etcd-snapshot-schedule-cron "0 */6 * * *"` pointing at the same storage, and enable `--secrets-encryption` in the same restart. Takes 30 minutes and one server k3s restart. ③ Annotate the 7 Namespaces with `argocd.argoproj.io/sync-options: Prune=false`, or create them with `syncOptions: [CreateNamespace=true]` and remove the Namespace manifests from Git. Takes 30 minutes. ④ Restore once from the off-node copy into a temporary namespace and write down how long it took. Takes 1 hour. Expected effect: a disk failure or a Git mistake costs one backup interval instead of everything.
```yaml
# Namespace manifests of the 7 pruning apps — proposal
metadata:
  annotations:
    argocd.argoproj.io/sync-options: Prune=false
```

**Why this happens.**
- Principle: A backup is a backup only if it survives the failure domain of the original (disk, node, cluster, account). A dump on the same disk shares every failure with the original, and a PV with reclaim policy Delete is removed with its PVC, so deleting a namespace deletes the data. GitOps prune turns "absent from Git" into "deleted from the cluster", and that includes a Namespace that owns PVCs.
- Cases: The `argocd.prune-manages-namespace-or-crd` check definition cites the Skyscanner 2021 incident, where an ApplicationSet generator change removed the apps and prune deleted everything they had managed.
- Read next: "k3s docs: Backup and Restore (etcd-s3 options)", "Argo CD docs: Sync Options (Prune=false, CreateNamespace)", "Kubernetes docs: Persistent Volumes, reclaim policy", "Google SRE Book ch. 26 Data Integrity".

Evidence checks: `resilience.no-backup.cluster`, `resilience.backup-same-node.*` (7), `resilience.prod-db-without-backup-cronjob.cluster`, `platform.k3s-etcd-snapshot-local-only.node-b`, `platform.k3s-secrets-encryption-off.node-b`, `argocd.prune-manages-namespace-or-crd.cluster`, `storage.prod-db-reclaim-delete.cluster`, `storage.local-path-prod-delete-reclaim.cluster`, `storage.local-path-node-pinned.cluster`, `resilience.single-eligible-node.*` (16 unavoidable local-path pins)

### 5. Traffic, errors and latency of 29 services are visible nowhere, and the 30 days of metrics that exist sit on emptyDir
**Problem.** The ingress controller's metrics are off, so for 29 Ingresses with 47 hosts there is no request rate, no 5xx ratio and no latency anywhere. That is why nobody can say what traffic started the two app-f-api-server scale-ups today. All 161 alert rules watch causes (CPU, disk, pod state); 0 watch symptoms (error ratio, p99 latency), and there is no SLO, a target such as "99.5% of requests succeed". When 15 production apps were down for 3 minutes yesterday, no alert fired because `KubeNodeNotReady` waits 15 minutes. On top of that, Prometheus, Alertmanager and Grafana keep their data on emptyDir, a directory that disappears with the pod, so one chart upgrade, one node-b drain or one eviction resets 30 days of metrics to zero. Prometheus has a 30-day time retention and no size cap.

**Evidence.** 0 `nginx_ingress_controller_requests` series in metrics/ingress_controller_requests.json, and all 29 Ingresses have no metric source in summary.json observability.golden_signals. Rules are 161 alerting: symptom 0, cause 153, app 8, with 0 SLO signals, in summary.json observability.rules and .slo. 135 of 145 rules never fired in 15 days while 6 fire every minute of the 7 days, in summary.json observability.alerts. Alertmanager has 1 replica on emptyDir and one receiver, with 27 notifications in 24 hours against 783 firing and resolved alerts received, in summary.json stackhealth.alertmanager. Prometheus TSDB is 24,175,488,463 bytes, 22.5 GiB, on emptyDir with retention 30d and size cap 0B, oldest sample 32.1 days, 144,937 active series, in summary.json stackhealth.prometheus. node-b's kubelet emptyDir usage is 24,808 MB, of which 23,131 MB is the Prometheus pod, in summary.json nodeos. CoreDNS runs 1 replica on node-b without a PDB at p99 142.7 ms in summary.json coredns.summary.

**Cause.** Confirmed: `controller.metrics.enabled` is off in the ingress-nginx Helm values, and the kube-prometheus-stack values have no `storageSpec` and no `retentionSize`. Without ingress metrics there is no material for symptom alerts or SLOs.

**Action.** ① ingress-nginx values: `controller.metrics.enabled: true`, `controller.metrics.serviceMonitor.enabled: true`. Takes 30 minutes. ② Prometheus CR: a `storageSpec.volumeClaimTemplate` of 40Gi on `local-path-node-b` and `retentionSize: 32GB`; Alertmanager `storage` and Grafana `persistence.enabled: true` the same way. Takes 1 hour and one Prometheus restart; copy the emptyDir contents first with `kubectl cp` or accept one reset. ③ Once ingress metrics flow, two symptom rules per host group: 5xx ratio above 1% for 5 minutes, p99 above 1 second for 10 minutes, severity page. Takes 1 hour. ④ One SLO per customer-facing service as Sloth or Pyrra recording rules, starting with app-f-api-server and app-d. Takes half a day. ⑤ Silence or disable the 6 always-firing rules until problems 1 and 3 are fixed so the discord channel carries signal again. Takes 15 minutes. ⑥ CoreDNS to 2 replicas with a PDB; the manifest is in details section 4, traffic. Takes 15 minutes.
```yaml
# kube-prometheus-stack values — proposal
prometheus:
  prometheusSpec:
    retentionSize: 32GB
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: local-path-node-b
          resources: { requests: { storage: 40Gi } }
alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: local-path-node-b
          resources: { requests: { storage: 2Gi } }
grafana:
  persistence: { enabled: true, storageClassName: local-path-node-b, size: 5Gi }
```
```yaml
# ingress-nginx values — proposal
controller:
  metrics:
    enabled: true
    serviceMonitor: { enabled: true }
```

**Why this happens.**
- Principle: Alerts should fire on symptoms the user feels (errors, latency) and causes (CPU, disk) belong on dashboards. Without the four golden signals per service there is no definition of "normal", and no way to tell which of 161 rules matters. A metrics store on emptyDir has a retention equal to the pod's lifetime regardless of the configured retention.
- Cases: Google SRE Book ch. 6 Monitoring Distributed Systems defines the four golden signals (latency, traffic, errors, saturation) and the rule "page on symptoms". The `prometheus.storage-risk` check definition records a home-cluster measurement of 30 days and 23.7 GiB on emptyDir and cites no vendor incident.
- Read next: "Google SRE Book ch. 6 Monitoring Distributed Systems", "Google SRE Workbook ch. 5 Alerting on SLOs (multi-window burn rate)", "Prometheus Operator docs: Prometheus storageSpec and retentionSize", "ingress-nginx docs: Monitoring (Prometheus metrics)".

Evidence checks: `observability.ingress-controller-metrics-missing.ingress-controller`, `observability.golden-signals-missing.*` (29), `observability.no-slo.cluster`, `observability.no-symptom-alerts.cluster`, `observability.page-severity-cause-alerts.cluster`, `observability.saturation-signal-missing.cluster`, `observability.alerts-never-fired.cluster`, `observability.severity-channels-not-separated.cluster`, `observability.alerts-always-firing.*` (6), `observability.alert-firing-stale.*` (5), `observability.stack-storage-emptydir.*` (3), `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`, `node.pod-dir-large.monitoring/prometheus-kube-prometheus-stack-prometheus-0`, `coredns.availability.cluster`, `traffic.coredns-latency.cluster`, `observability.failure-mode-uncovered.OOMKill`

Quick fix outside the list: raise the `persistentvolumeclaims` quota of `app-i-prod/app-i-prod-quota` from 2 to 4 or delete the line to end KubeQuotaFullyUsed after 117.3 days, and delete the 3 Failed pods (`app-a-prod/app-u`, `app-a-prod/app-a-experiment`, `app-f-prod/app-f-embed-67f6f74f6c-rlm8m`). Under 10 minutes together.

## Since the previous full run (2026-10-26 15:32)

The two full snapshots are 55 minutes apart and the only cluster change in between is the app-f-api-server HPA: it scaled the Deployment to 4 at 16:11:55 KST and to 5 at 16:14:40 KST because CPU went above 60% of the 100m request, the three new pods landed on node-a and became Ready after 91 seconds, and at collection time the Deployment is still at 5 with CPU at 1% of request, waiting out the scale-down stabilization. That one change brought N+1 back to fail, because CPU requests rose from 6.01 to 6.31 cores against the 6.0 cores node-a offers without node-b, and it produced two first-pass findings that I overturned, a 24-hour Ready ratio and a traffic skew computed over pods that are 13 to 16 minutes old. The only other object change is a normal rotation of the CI runner pod in arc-systems. Two "resolved" items, API server POST and PUT p99, were values measured during the 15:32 collection and are not an improvement; LIST 0.946 s and PATCH 0.854 s remain inside this run's collection window too. Two "new" throttling warns, app-d-postgres-mx at 10.5% and app-i-web at 10.7%, are the same containers that crossed the 10% threshold downward at 15:32 and upward again now with unchanged limits. Criteria change: rubric 0.1.50 renames the profile `small k3s cluster` to `k3s`, so the cost check is reported as resolved under the old name and new under the new one; nothing else in the rubric changed. Smaller movements: app-c-coturn restarts 7,885 → 7,896 with BackOff +250, Prometheus head series 157,769 → 144,937 after a head compaction, app-e-postgres throttling 31% → 44%, node-b disk 49.9% → 49.5%, node-a 78% unchanged.

Progress on the previous report's problems: problem 1 of 15:32 (nodeAffinity pin, now problem 2) not started, the 15 Deployments still carry `role NotIn [observability]` and 33 of 47 production pods are on node-a. Problem 2 (app-c-coturn, now problem 3) not started, restarts 7,885 → 7,896. Problem 3 (backups, now problem 4) not started, 7 CronJobs still local only, etcd snapshots still local, 7 pruning apps unchanged. Problem 4 (CPU limits and probes, now problem 1) not started, app-f-api-server still 100m/500m and scaled to 5 again, 13 probes still at 1 second, the 2 failed watchdog Jobs still present. Problem 5 (ingress metrics, Prometheus storage) not started, 0 ingress series, Prometheus emptyDir 23,131 MB.

## What this run could not see

The only component the profile expects and does not find is Loki; this cluster fills that role with Elasticsearch 7.10.2 and fluent-bit, so 5 Loki checks are skipped, and because there is no Elasticsearch collector the index health, thread-pool rejections and the real cause of the fluent-bit flush failures were not read. No tool is missing (13 of 13 present) and all 345 checks of full mode were evaluated or intentionally off (294 evaluated, 41 disabled by profile, 8 skipped, 0 errors). Two collection steps failed: the Argo CD repo-server metrics proxy returned 502, as in every run since 13:34, and the MetalLB speaker metrics proxy on node-a timed out after 20 seconds while the node SSH fallback read the same endpoint. Grafana dashboards and datasources were not read because config has no `grafana_api_token`. Measurements disturbed by collection itself: API server p99 LIST 0.946 s and PATCH 0.854 s, 503 ratio 0.0037/s from kubegap's own two proxy calls, and Prometheus CPU throttling 41%, all from the 16:27:22 to 16:31:57 KST window in which kubegap sent about 100 LISTs and 164 PromQL queries; none counted as user impact. The app-c-coturn container log is not in the snapshot because the pod never lives long enough, and node-a's previous-boot journal is not collected, so the 2026-10-25 reboot cause stays open. The N+1 `margin` field reads 0.02 for the third snapshot in a row while its inputs changed, so it cannot be used.

## Numbers

| Severity | fail | warn | vs. previous full run |
|---|---|---|---|
| critical | 2 | 1 | fail +1 (N+1 back below the line) / warn 0 |
| high | 34 | 5 | 0 / 0 |
| medium | 81 | 118 | fail 0 / warn +2 (app-d-postgres-mx and app-i-web throttling back above 10%) |
| low | 35 | 155 | fail 0 / warn +1 (app-f-api-server traffic skew, lowered from medium) |
| info | 0 | 6 | warn −2 (POST and PUT latency, measured during the 15:32 collection, gone) |

Counts by the session's final severity. 135 first-pass rows were changed (warn → fail 33, → pass 5, severity moved 97) and 3 were added; all are in details section 1-1. Final critical+high fail is 36 against a first pass of 35, inside the 3-item band of `history.csv`.

Details, every table and the full first-pass list: [`report-details.md`](report-details.md) · kubegap 0.1.0, rubric 0.1.50, signatures 1.0.15 · snapshot `~/.kubegap/snapshots/default/2026-10-26T16-27-22`

# my-cluster — full audit, 2026-11-03 11:17 KST

This is the EKS cluster `my-cluster` in us-east-1, audited through the kube context `my-cluster`. It runs Kubernetes 1.32.13 on 8 nodes with 145 pods and eight prod namespaces, under the prod profile. Nothing is down now, but `prod-app-q/app-q-ai` was OOM-killed three times during yesterday's rollout, and no alert told anyone. Of the last full report's five problems, only the evicted pods were cleaned up, and its claim of an open database load balancer was wrong.

## The 5 problems to work on

### 1. Seven production databases have no backup, and each volume is deleted together with its claim
**Problem.** Seven prod databases keep their data on EBS volumes with reclaim policy Delete. They are the MySQL databases of app-m, app-o and app-n, the PostgreSQL databases of app-q, app-p and app-s, and the Neo4j database of app-l. If someone deletes a namespace or a PVC by mistake, the volume goes with it, and there is no copy to restore. There is no backup tool, no backup CronJob, no AWS Backup plan and no DLM policy. DLM is the AWS service that takes scheduled EBS snapshots of volumes selected by tag. The only snapshots were taken by hand before old claims were deleted, and the newest is four weeks old.

**Evidence.** The cluster has 17 PersistentVolumes holding 280 GB. All of them have reclaim policy Delete, and none is encrypted. Source: summary.json storage.pv and storage.ebs. The account has 0 DLM policies, in aws/dlm-lifecycle-policies.json, and 0 backup plans, in aws/backup-plans.json. All 12 EBS snapshots of the last 30 days are named "pre-delete backup of orphan PVC", and the newest is from 2026-10-06. Source: aws/ec2-snapshots-30d.json. The VolumeSnapshot CRD is not installed, so the EBS CSI snapshot sidecar logged 1,500 errors in 4 hours 41 minutes. Source: summary.json logs.signatures. The largest prod database volume is app-o MySQL at 48.9 GB. Source: summary.json storage.pvcs.

**Cause.** The databases run on the default gp3 StorageClass, and no backup layer was added after they were deployed. The EBS CSI add-on ships the snapshot sidecar. The `snapshot-controller` add-on, which provides the CRD the sidecar needs, was never installed.

**Action.**
- ① Create one DLM policy that snapshots, daily, every volume tagged with a prod namespace, and keeps 14 snapshots. From tonight on there will be a copy of every database volume. Takes 1 hour.
- ② Patch the seven prod database PVs to `Retain`, so a deleted claim leaves its volume behind. Run `kubectl patch pv <pv-name> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'` once for each. Takes 10 minutes.
- ③ Add a nightly logical dump for each database to S3 from a CronJob, using mysqldump, pg_dump or `neo4j-admin database dump`. Then restore one dump into a scratch namespace to prove the path works. A DLM snapshot is a crash-consistent block copy, and a dump is what lets you restore single tables. Takes half a day.
- ④ Install the `snapshot-controller` EKS add-on and one VolumeSnapshotClass. That stops the sidecar errors and makes CSI snapshots possible. Takes 30 minutes.
- ⑤ After that, make an encrypted, expandable gp3 class the default. Move the volumes to encrypted copies during a restore test. The manifest is in report-details.md, section 4, Storage. Takes a day.

```json
{ "PolicyType": "EBS_SNAPSHOT_MANAGEMENT", "ResourceTypes": ["VOLUME"],
  "TargetTags": [
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-m"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-o"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-n"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-q"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-p"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "prod-app-l-backend"},
    {"Key": "kubernetes.io/created-for/pvc/namespace", "Value": "app-s-prod"} ],
  "Schedules": [{ "Name": "daily", "CopyTags": true,
    "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["18:00"]},
    "RetainRule": {"Count": 14} }] }
```

**Why this happens.**
- Principle: Kubernetes removes a PersistentVolume with reclaim policy Delete together with its claim, and deleting a namespace deletes every claim in it. A copy survives both a wrong `kubectl delete` and the loss of a volume only if it is taken on a schedule and stored outside the cluster.
- Cases: Spotify's 2019 talk about deleting its own production Kubernetes clusters by mistake is one of the public cases recorded for this check.
- Read next: the AWS documentation on Amazon Data Lifecycle Manager, the Kubernetes documentation on Persistent Volumes and their reclaim policy, and chapter 26, "Data Integrity: What You Read Is What You Wrote", of Google's Site Reliability Engineering book.

Evidence checks: `resilience.no-backup.cluster`, `eks.no-backup-policy.cluster`, `resilience.prod-db-without-backup-cronjob.cluster`, `storage.prod-db-reclaim-delete.cluster`, `storage.csi-snapshot-unavailable.cluster`, `logs.signatures.ebs-csi.snapshot-crd-missing`, `storage.ebs-unencrypted.cluster`, `ebscsi.storageclass-unencrypted.cluster`, `storage.no-volume-expansion.gp3`, `storage.no-volume-expansion.gp3-2a`, `storage.no-volume-expansion.gp3-2c`

### 2. app-q-ai was OOM-killed three times in yesterday's rollout, three public hosts answer in 3 seconds or more, and no alert reached anyone
**Problem.** On 2026-11-02 the new app-q-ai image was killed twice at startup and once 44 minutes later. Each time, its uvicorn process hit the 768 Mi memory limit. During the first two kills, the old pod was still serving. At 09:38 UTC the kill hit the only running replica, and the service was down until the restart finished. In the same 24 hours, three hosts had a p95 response time of 3 seconds or more:
- api.v1.example-b.ai, 20.5 seconds
- app-q-ai, 14.1 seconds
- app-l.my-cluster, 3.1 seconds, with one hour at 41.5 seconds

None of this raised an alert. Only app-m image inference and LoRA training have symptom alerts, and no rule covers OOM kills. Four prod target groups also mark every target unhealthy, so the load balancer would keep sending requests to a pod that has died.

**Evidence.** The kernel on `ip-10-0-1-62` logged "Memory cgroup out of memory: Killed process (uvicorn)" at 08:34, 08:35 and 09:38 UTC, with anon-rss of 771 to 773 MB. Source: logs/node/node-1-62/os.txt. The 24-hour p95 of app-q-ai.my-cluster went from 2.07 s to 14.09 s since 2026-10-27, and app-l.my-cluster went from 0.27 s to 3.14 s. Source: summary.json traffic.ingresses in both snapshots. Of 157 alert rules, 3 watch a user symptom, and all 3 are for app-m. Source: prometheus/rules.json. The health checks of app-q-backend, app-l-backend, app-o-frontend and app-n-frontend request `/` and get 404 or 307, and each of these target groups has 0 healthy targets. Source: aws/alb-metrics.json. `KubeControllerManagerDown` and `KubeSchedulerDown` have fired for 55.6 days. These two alerts can never clear on EKS, because the managed control plane is not scraped. Source: summary.json observability.alerts.

**Cause.** Most likely, the image deployed on 2026-11-02 needs more memory at start than its 768 Mi limit. KRR's 607 MB recommendation comes from the 14 days before that image. The alert rules are the kube-prometheus-stack defaults plus the app-m team's own rules. Nobody wrote rules on the ALB metrics the account already collects. The health-check path was left at `/` on apps that redirect or return 404 there. The snapshot cannot tell whether 20 seconds is normal for api.v1.example-b.ai. Its pods use 0.013 cores at the p95, so the time is spent waiting, most likely on image generation outside the pod.

**Action.**
- ① Give app-q-ai a 1Gi memory request, a 1536Mi limit and two replicas, and add a PDB with `minAvailable: 1`. The next OOM will not take the service down, and the next rollout will not hit the limit at start. Takes 15 minutes.
- ② Add the OOM rule below and route it to `slack-sre`. Takes 20 minutes.
- ③ For every public prod host, alert when the 5xx ratio stays above 1% for 5 minutes, and when the p95 stays above 3 seconds for 10 minutes. Until a CloudWatch exporter feeds Prometheus, CloudWatch alarms on `HTTPCode_Target_5XX_Count` and `TargetResponseTime` per target group do the same job. Takes half a day.
- ④ Set `alb.ingress.kubernetes.io/healthcheck-path` on the four prod ingresses to each app's health endpoint. Where the app redirects, set `success-codes: "200-399"`. Takes 20 minutes.
- ⑤ Set `kubeControllerManager.enabled`, `kubeScheduler.enabled` and `kubeEtcd.enabled` to `false` in the chart values. The two permanent alerts disappear. Takes 10 minutes.
- ⑥ Decide with the app-m team whether 20 seconds is the expected time for api.v1.example-b.ai. If it is, record it as that host's latency objective and alert on that number.

```yaml
# app-q chart values, ai
replicas: 2
resources:
  requests: { cpu: 100m, memory: 1Gi }
  limits: { cpu: "1", memory: 1536Mi }
---
# PrometheusRule
- alert: ContainerOOMKilled
  expr: |
    increase(kube_pod_container_status_restarts_total[10m]) > 0
    and on (namespace, pod, container)
    kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
  for: 0m
  labels: { severity: warning, env: prod }
```

**Why this happens.**
- Principle: The kernel enforces a container memory limit with the cgroup OOM killer at once. The process gets signal 9, and the kubelet restarts it, so the only traces are a restart count and a kernel line. Users feel errors and slow answers, not memory percentages. Alerts should therefore watch each public host's success rate and latency, and handle a cause such as OOM with one targeted rule.
- Cases: Zalando's January 2019 DNS outage postmortem, in its kubernetes-on-aws repository, is recorded as a public case for the OOM check.
- Measured when this check was written: on the cluster the health-check rule was developed on, a frontend whose targets were all unhealthy still served 17,213 requests. Six target groups failed with Target.ResponseCodeMismatch because `/` returned 404 or 307.
- Read next: chapter 6, "Monitoring Distributed Systems", of Google's Site Reliability Engineering book, the Kubernetes documentation on Resource Management for Pods and Containers, and the AWS documentation on health checks for Application Load Balancer target groups.

Evidence checks: `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai`, `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai`, `observability.failure-mode-uncovered.OOMKill`, `observability.failure-mode-uncovered.Scheduling failure`, `observability.failure-mode-uncovered.VPC CNI IP exhaustion`, `observability.no-symptom-alerts.cluster`, `observability.no-slo.cluster`, `observability.slo-without-burn-rate.cluster`, `traffic.ingress-p95-latency.prod-app-q/app-q-ai`, `traffic.ingress-p95-latency.prod-app-m/app-m-api`, `traffic.ingress-p95-latency.prod-app-l-backend/app-l-frontend`, `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend`, `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend`, `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend`, `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend`, `observability.alerts-always-firing.KubeControllerManagerDown`, `observability.alerts-always-firing.KubeSchedulerDown`, `observability.alert-firing-stale.KubeControllerManagerDown`, `observability.alert-firing-stale.KubeSchedulerDown`, `resilience.single-replica-in-prod.prod-app-q/app-q-ai`, `hygiene.change-correlation.cluster`

### 3. 33 of 42 prod pods run on two spot nodes in one zone, and the larger node is 10 days past its expiry because one annotation holds it
**Problem.** Application pods can only run on nodes labeled `workload-type=app`. Today those are two spot nodes, both in us-east-1. `ip-10-0-1-139` holds 20 prod pods of 15 workloads, and `ip-10-0-1-62` holds 13. AWS can reclaim a spot node with two minutes' notice. If it reclaims `ip-10-0-1-139`, its 31 app pods cannot move to `ip-10-0-1-62`, which has only 0.16 cores of CPU request room left. All of them would wait for Karpenter to start a new node. app-r, app-o-ai, app-o-backend and app-l-frontend have every replica on that node, so they would all go down together. The node should have been replaced on 2026-10-24. The `karpenter.sh/do-not-disrupt` annotation on the prod app-m-admin pod template blocks that, and the node's root disk is now 82% full. No app node was reclaimed in the last seven days, so this is a risk, not an incident.

**Evidence.** Prod pods: 20 on `ip-10-0-1-139` and 13 on `ip-10-0-1-62`, both spot nodes in us-east-1. Source: summary.json resilience.placement. CPU requests are 89% and 92% of allocatable on these two nodes, while their 7-day p95 use is 5.5% and 5.3%. Source: metrics/node_cpu_request_ratio.json and metrics/node_cpu_usage_ratio_p95_7d.json. Five pods request 0.5 cores each and use at most 0.002 cores: app-p-backend, two app-l-backend and two app-l-embedding-server. Source: objects/pods.json and metrics/cpu_p95_7d_cores.json. NodeClaim `default-n44bh` is 241.4 hours past its 720-hour expiry. Karpenter recorded 19,728 blocked disruptions caused by that one pod. Source: summary.json scaling.karpenter and events.json. Over 24 hours, new app nodes took 61 seconds at the median and 93 seconds at most to become ready. Source: logs/pods/AGGREGATED.json. The root disk has 9.2 GB free of 50 GB. Source: summary.json nodeos.

**Cause.** A few services request hundreds of times the CPU they use. The scheduler therefore sees the app nodes as full, and every scale-up needs a new node. Nothing spreads replicas across nodes or zones, so the scheduler puts them wherever the requests fit. The do-not-disrupt annotation sits in the Deployment template, so every new app-m-admin pod carries it again. The `default` NodePool allows spot and on-demand, and Karpenter chooses spot whenever both are allowed.

**Action.**
- ① Lower the CPU request of app-p-backend, app-l-backend and app-l-embedding-server from 500m to 100m. This frees 2.0 cores and takes the two app nodes to about 59% and 50% requested. KEDA workers can then start without a new node. Takes 30 minutes. Leave the requests of app-l-neo4j and the other databases as they are.
- ② Add hostname and zone topologySpreadConstraints to the shared prod chart for Deployments with two or more replicas. The fragment is in report-details.md, section 4, Resilience. Takes 1 to 2 hours through Argo CD.
- ③ After ① and ②, remove `karpenter.sh/do-not-disrupt` from the prod app-m-admin template. Karpenter then replaces the expired node, which also starts it on a fresh disk. Takes 10 minutes.
- ④ app-p-backend runs one replica with the Recreate strategy, and its spec changed 13 times in seven days. Each change was an outage. If the app can run two copies, switch to 2 replicas and RollingUpdate with `maxSurge: 1`, `maxUnavailable: 0`. Takes 20 minutes.
- ⑤ Keep at least one replica of each prod service on on-demand capacity. One way is a small on-demand NodePool that carries the `workload-type=app` label, combined with the zone spread from ②. Takes half a day.

```yaml
# prod app-m chart, admin Deployment
spec:
  template:
    metadata:
      annotations: {}   # drop karpenter.sh/do-not-disrupt: "true"
# app-p, app-l-backend, app-l-embedding-server charts
resources:
  requests: { cpu: 100m }
```

**Why this happens.**
- Principle: The scheduler places pods by their requests, not by their use, so requests far above use make an idle node look full. After a spot interruption, Karpenter starts a replacement sized for the pending pods. When no other node has request room, users wait for the node to start and the images to pull. Karpenter replaces an expired node only when every pod on it may be disrupted. One do-not-disrupt pod stops that indefinitely.
- Cases: Moonlight's 2019 outage post-mortem is the public case recorded for both the prod-concentration and the same-node checks.
- Measured when this check was written: on the cluster these checks were developed on, one spot reclaim took a production service down for 2 minutes 7 seconds. The node it hit held 27 production pods. Another node stayed more than 31 days because of one do-not-disrupt annotation, and its disk filled to 87%.
- Read next: the Kubernetes documentation on Pod Topology Spread Constraints, the Karpenter documentation on Disruption, and the AWS documentation on EC2 Spot Instance interruption notices.

Evidence checks: `resilience.prod-concentration.node-1-139`, `resilience.n-plus-one.cluster`, `resilience.replicas-same-node.prod-app-r/deployment/app-r`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server`, `scaling.karpenter-expired-not-replaced.default-n44bh`, `resources.node-request-usage-gap.node-1-139`, `resources.node-request-usage-gap.node-1-62`, `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-backend:backend`, `resources.cpu-request-overprovisioned.prod-app-l-backend/deploy/app-l-embedding-server:embedding`, `resources.krr-recommendation.prod-app-p/deployment/app-p-backend:backend`, `resources.large-request-binpacking.prod-app-l-backend/deploy/app-l-embedding-server:embedding`, `resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend`, `resilience.single-replica-in-prod.prod-app-p/app-p-backend`, `resilience.no-pdb.prod-app-o/app-o-ai`, `resilience.no-pdb.prod-app-o/app-o-backend`, `node.disk-usage.<ip>:9100:/`, `events.tracked-warning-reasons.FreeDiskSpaceFailed`, `events.tracked-warning-reasons.FailedScheduling`, `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-file-worker`, `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-graph-worker`, `karpenter.spot-to-spot-consolidation-off.cluster`, `resilience.priority-inversion.cluster`

### 4. Kafka's external listener accepts connections from the whole internet, the Argo CD admin login has no SSO, and the three NetworkPolicies are not enforced
**Problem.** The Kafka broker in `middleware` has an internet-facing NLB whose security group allows ports 9094 and 443 from 0.0.0.0/0, and real traffic passes through it. The snapshot does not show whether the listener requires authentication. Argo CD can deploy anything into every namespace. It is reachable at deploy.my-cluster with the built-in admin account, no SSO and an empty RBAC policy. All 12 of its applications sit in the `default` project, whose sources and destinations are `*`. The EKS API endpoint is open to 0.0.0.0/0. Inside the cluster, the NetworkPolicies in prod-app-q, prod-app-p and app-s-prod have no effect, because the VPC CNI policy agent is turned off. The shared database NLB is better than the last report said. Its security group admits four office addresses and nothing else.

**Evidence.** Security group `sg-kafka-nlb` on the Kafka NLB allows tcp 9094 and 443 from 0.0.0.0/0. Source: extra/nlb-security-groups.txt. That NLB processed 2.8 GB in 24 hours, with up to 441 concurrent flows. Source: aws/alb-metrics.json. In Argo CD, admin is enabled, SSO is not configured, policy.csv has 0 lines, and 12 of 12 applications are in `default`. Source: summary.json argocdctl. The EKS public access CIDR is 0.0.0.0/0. Source: inventory.json cluster.eks. `aws-eks-nodeagent` runs with `--enable-network-policy=false`, and there are 0 PolicyEndpoints. Source: summary.json security.networkpolicy. Security group `sg-db-shared-nlb` on `acme-db-shared` admits the database ports from four /32 addresses. Source: extra/nlb-security-groups.txt.

**Cause.** Most likely, the Kafka listener was opened for the on-premise consumers. The alert rules expect 16 members in the `on-premise` consumer group. Argo CD and the API endpoint still run with their installation defaults. Network policy enforcement is an opt-in setting of the VPC CNI add-on, and it was never turned on.

**Action.**
- ① Set `loadBalancerSourceRanges` on `middleware/kafka-controller-0-external` to the egress addresses of the on-premise consumers. Confirm that the external listener uses SASL over TLS, and check afterwards that `kafka_consumergroup_members{consumergroup="on-premise"}` stays at 16. Takes 30 minutes.
- ② Turn on SSO in Argo CD through Dex or OIDC. Set `admin.enabled: "false"` and `policy.default: role:readonly`, and move the applications into one AppProject per team. Takes half a day.
- ③ Restrict the EKS public endpoint to the office and CI addresses, or make it private. Takes 30 minutes.
- ④ Enable network policy in the VPC CNI add-on configuration with `{"enableNetworkPolicy": "true"}`. The three existing policies start blocking traffic at that moment, so read them first. Takes 1 hour.
- ⑤ Set the IMDS hop limit to 1 in the EC2NodeClass, so pods cannot reach the node's credentials. Six service accounts already use IRSA. Takes 20 minutes and applies to new nodes.

```yaml
# middleware/kafka-controller-0-external
spec:
  loadBalancerSourceRanges: ["<on-prem egress>/32"]
---
# argocd-cm
data: { admin.enabled: "false" }
---
# argocd-rbac-cm
data: { policy.default: role:readonly }
```

**Why this happens.**
- Principle: A load balancer's security group is the only filter between the internet and the service behind it. An open broker port lets anyone try credentials or known exploits against the broker. A tool that deploys into every namespace has the power of cluster-admin, so its login needs to be as strong as the cluster's. A NetworkPolicy is only an API object until a network plugin enforces it.
- Cases: Aqua Nautilus reported in 2023 that attackers used Kubernetes RBAC to backdoor clusters whose API servers were reachable from the internet. It is the case recorded for the public endpoint check.
- Read next: the Kubernetes documentation on Network Policies, the Argo CD documentation on User Management and RBAC Configuration, and the Amazon EKS documentation on cluster API server endpoint access.

Evidence checks: `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external`, `traffic.db-exposed.nlb/acme-db-shared`, `eks.public-endpoint-open.cluster`, `argocd.admin-account-no-sso.cluster`, `argocd.default-project-wildcard.cluster`, `traffic.external-exposure.ingress/argocd/argocd-server`, `security.networkpolicy-not-enforced.cluster`, `security.networkpolicy-coverage.cluster`, `security.imds-hop-limit.cluster`, `karpenter.ec2nodeclass-hardening.cluster`, `security.psa-not-enforced.cluster`

### 5. Kubernetes 1.32 left standard support 225 days ago, and AL2 nodes and Karpenter 0.37 block the upgrade
**Problem.** EKS 1.32 has been on extended support since 2026-03-23. Extended support ends on 2027-03-23, and after that AWS upgrades the control plane by itself. Two things block the upgrade to 1.33:
- The EC2NodeClass for every Karpenter node requests Amazon Linux 2, and Amazon stopped publishing AL2 EKS images on 2025-11-26. After an upgrade, new app nodes could not start.
- Karpenter 0.37.0 supports Kubernetes only up to 1.30. The component that handles every spot interruption already runs two versions outside its support range, and it logged a version validation error yesterday.

Four managed add-ons are behind as well.

**Evidence.** The server is v1.32.13. Standard support ended on 2026-03-23, and the support type is EXTENDED. Source: inventory.json cluster.eks. The EKS upgrade insight "Amazon Linux 2 compatibility" is ERROR for 1.33. Source: aws/list-insights.json. EC2NodeClass `default` uses amiFamily AL2 with no pinned AMI and a 50 GB unencrypted root volume. Source: summary.json karpenterctl. Karpenter logged "failed validating kubernetes version" at 2026-11-02T08:46:33Z. Source: summary.json logs.signatures. The EBS CSI driver is at v1.37.0 against v1.67.2 available, and VPC CNI at v1.19.0 against v1.23.2. Source: inventory.json cluster.eks.addons. The managed node group AMI is 329 days old. Source: summary.json eksplatform.nodegroups.

**Cause.** The cluster was built in December 2025 with the defaults of that time, and nobody has touched the platform layer since. Karpenter, the node image family and the add-ons are still at the versions they were installed with.

**Action.**
- ① Upgrade Karpenter from 0.37 to 1.x following the v1 migration guide. The NodePool and EC2NodeClass APIs move from v1beta1 to v1. Takes 2 to 3 hours, including a dry run on the dev applications.
- ② Change the EC2NodeClass to AL2023 with a pinned alias, IMDS hop limit 1 and an encrypted 100Gi root volume. Drift then replaces the six AL2 nodes one at a time. Do this after ① and ② of problem 3, so that pods spread as they move. Takes half a day.
- ③ Upgrade the four add-ons, enable prefix delegation in VPC CNI, and refresh the managed node group AMI. Takes 2 hours.
- ④ Upgrade EKS from 1.32 to 1.33 to 1.34, one minor version at a time, and dev first. Takes a day per minor version.

```yaml
# EC2NodeClass default, after Karpenter v1
spec:
  amiFamily: AL2023
  amiSelectorTerms: [{ alias: al2023@vYYYYMMDD }]   # pin the version you tested
  metadataOptions: { httpEndpoint: enabled, httpPutResponseHopLimit: 1, httpTokens: required }
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs: { volumeSize: 100Gi, volumeType: gp3, encrypted: true }
```

**Why this happens.**
- Principle: Each EKS minor version gets 14 months of standard support and 12 more months of paid extended support. After that, AWS upgrades the control plane automatically. Node images, the autoscaler and the CNI each publish their own compatibility table. An upgrade is possible only when all of them already support the target version.
- Cases: ZenML's 2025 incident, published on its status page, is the public case recorded for the version end-of-life check.
- Read next: the Amazon EKS documentation on the Kubernetes version lifecycle and extended support, the Karpenter documentation on upgrading to v1, and the Amazon EKS documentation on the EKS-optimized Amazon Linux 2023 AMIs.

Evidence checks: `platform.k8s-version-eol.cluster`, `eks.extended-support.cluster`, `platform.karpenter-version-compat.cluster`, `logs.signatures.karpenter.version-unsupported`, `karpenter.ec2nodeclass-al2.cluster`, `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility`, `eks.node-os-skew.cluster`, `eks.nodegroup-ami-old.nodegroups`, `eks.addon-outdated.aws-ebs-csi-driver`, `eks.addon-outdated.vpc-cni`, `eks.addon-outdated.coredns`, `eks.addon-outdated.kube-proxy`, `vpccni.prefix-delegation-off.cluster`, `argocd.version-eol.cluster`

Quick fix outside the list: the dev ExternalSecret `database/mysql-app-n-secret` has not read its key since December 2025, and it has failed 2,351 times. Create the key in Secrets Manager or delete the ExternalSecret. It takes 5 minutes and clears five findings.

## Since the previous full run (2026-10-27 15:30 KST)
The previous full snapshot is 6 days and 20 hours old, and nobody wrote a report for it. 16 Deployments received new images, and no replica, resource, strategy or placement field changed. The app-q-ai rollout on 2026-11-02 brought three OOM kills, and its p95 rose from 2.07 s to 14.09 s. app-l.my-cluster slowed from 0.27 s to 3.14 s after the app-l-backend rollout on 2026-10-30, but that link is only a correlation in time. Karpenter replaced the build node `ip-10-0-1-4` with `ip-10-0-2-144`, and no app node was reclaimed. The 20 pods evicted for disk pressure are gone, `KubePodNotReady` stopped firing, and the last `FreeDiskSpaceFailed` was on 2026-10-27. Some new findings come from criteria, not the cluster: the six Argo CD findings and the IMDS finding appear because the older summary lacked that data, and the rubric went from 0.1.51 to 0.1.63.

Progress on the previous report's problems, from the 2026-10-26 16:47 full report:
- Problem 1, prod on spot nodes: not started. `ip-10-0-1-139` holds 20 prod pods, down from 28 only through rescheduling. app-l-backend still requests 500m. app-p-backend is still at 1 replica with Recreate. The do-not-disrupt block count went from 14,171 to 19,728.
- Problem 2, the disk of `ip-10-0-1-139` and the evicted pods: started. Failed pods went from 12 to 0, and the disk from 87% to 82%. The node was not replaced, and the EC2NodeClass still has a 50 GB root volume.
- Problem 3, backups: not started. There are still 0 DLM policies, 0 backup plans, and 17 of 17 volumes unencrypted.
- Problem 4, symptom alerts and health checks: not started. The 157 rules are unchanged, the same four prod target groups are unhealthy, and `KubeControllerManagerDown` went from 47.8 to 55.6 days of firing.
- Problem 5, platform and exposure: not started. The cluster still runs 1.32.13, AL2 and Karpenter 0.37.0, and Argo CD admin has no SSO. The previous report's statement that the database NLB is open to the internet was wrong. It is limited to four office addresses.

## What this run could not see
The profile expects five component families that are absent: a backup tool, event retention, an SLO tool, in-cluster certificate management and progressive delivery. Of 365 checks, 358 were evaluated. Two are disabled on EKS, and three were skipped because fluent-bit and ingress-nginx are not installed. No tool was missing, and Helm data was read normally. 24 collection commands failed:
- 19 were node commands and controller metric reads on `ip-10-0-1-117` and `ip-10-0-2-60`. Those two managed nodes are not registered in SSM, so their OS state, kube-proxy mode and VPC CNI counters are unknown.
- 4 were ECR lifecycle lookups on repositories that have no policy.
- 1 was an ALB controller proxy timeout.

Grafana datasources and dashboards were skipped because no API token is configured, and KEDA operator metrics are turned off. The snapshot has only 24-hour aggregates per target group, so it cannot say when app-l.my-cluster had its 41.5-second hour. Container logs are outside kubegap's scope, so app-q-ai's own error output and the Kafka listener's authentication settings are unknown. The apiserver LIST and PATCH p99 of about 0.7 s were measured during collection and likely include kubegap's own requests, so they are not counted as user impact. The security groups of the two NLBs were read once more after collection, read-only, and saved in extra/nlb-security-groups.txt.

## Numbers
| Severity | fail | warn | vs. previous full run |
|---|---|---|---|
| critical | 2 | 0 | fail +1, warn −2 |
| high | 20 | 12 | fail −16, warn −11 |
| medium | 116 | 172 | fail +9, warn +2 |
| low | 20 | 150 | fail +2, warn +14 |
| info | 2 | 1 | fail ±0, warn +1 |

The 2026-10-27 run has no report, so the deltas compare against its first-pass counts. The final critical and high total is 34, 26 fewer than the first pass of 60. Most of the gap comes from lowering dev items, ended events and the database NLB, and the reasons are in report-details.md section 1-1. history.csv counts the first pass.

Details, every table and the full first-pass list: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.63 · snapshot `2026-11-03T11-17-15`

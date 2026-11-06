# my-cluster — full audit, 2026-11-05 17:18

Urgent now: no

Today's problems: ① No backups for 7 prod databases ② Prod pods piled on one spot node ③ Kafka listener open to the internet ④ 4 prod ALB health checks failing ⑤ Unsupported EKS, Karpenter and AL2

Since the last run: The 2026-11-03 full run had no report, so there is no way to tell whether its work was done.

Appeared: 7. They include the new idle spot node node-2-158 with 11 CreateNetworkInterface failures, node-1-62's root disk at 79%, and 80 5xx out of 54,991 requests in 24 hours (0.14%) on app-m-frontend. Most other status shifts, such as the new N+1 warning, come from changed rules, not from the cluster.

Went away: 5. They include node node-2-144 leaving the cluster, Promtail no longer sitting at its memory limit, and kafka-exporter no longer Not Ready, though it has restarted 5 times.

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 8 of 8 Ready |
| Pods | 139 running, 0 pending, 0 failed |
| Namespaces | 25, 8 production |
| Components | 23: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics and log stores | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## Coming up

| When | What | Source |
|---|---|---|
| 2026-11-07 21:31 KST | system-ondemand 풀 노드 node-1-241(NodeClaim system-ondemand-mxf5q)이 expireAfter 720h에 닿아 교체돼요. prod-app-p/app-p-postgresql-0(레플리카 1, us-east-1a 볼륨)이 다른 노드로 옮겨지는 동안 멈춰요. emptyDir에 있는 loki-stack-0의 로그도 사라져요. | summary.json |
| 2026-11-07 21:32 KST | 노드 node-2-218(NodeClaim system-ondemand-jvbnl)이 만료돼 교체돼요. prod-app-q/app-q-backend-postgresql-0(레플리카 1, us-east-1c 볼륨)과 emptyDir을 쓰는 Alertmanager가 옮겨져요. 풀 예산이 10%라 앞의 노드와 한 대씩 차례로 교체돼요. | summary.json |
| 2026-11-08 15:28 KST | 노드 node-2-135(NodeClaim system-ondemand-db9bj)가 만료돼 교체돼요. middleware/kafka-controller-0(브로커 1대)과 prod-app-l-backend/app-l-neo4j-0이 옮겨지는 동안 멈춰요. | summary.json |
| 2026-11-07 | 지난달 지운 고아 PVC를 지우기 전에 떠 둔 EBS 스냅샷 12개에 delete-after 2026-11-07 태그가 붙어 있어요. 자동으로 지우는 정책은 없지만, 이 날짜에 누가 지우면 그 데이터의 마지막 사본이 없어져요. | aws/ec2-snapshots-30d.json |
| 2026-12-03 | 쓰이지 않는 ACM 인증서 acmeai.kr이 만료돼요. 갱신 대상이 아니에요. | aws/acm-certificates.json |
| 2027-03-23 | EKS 1.32의 확장 지원이 끝나요. 표준 지원은 2026-03-23에 이미 끝나서 지금은 확장 지원 요금을 내고 있어요. | aws/describe-cluster-versions.json |

## 1. No backups for 7 prod databases

**What is happening.** All 7 prod databases run as a single replica, with their data on one EBS volume each. There are 3 MySQL, 3 PostgreSQL and 1 Neo4j, and nothing backs any of them up. If a volume breaks or gets deleted, there is no copy to restore. It is ongoing, and three of these pods move to new nodes when nodes expire on the night of 2026-11-07 and the afternoon of 2026-11-08.

- Affected: the 7 prod DBs below. All 7 have reclaimPolicy Delete.
  - prod-app-p/app-p-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1a. It runs on node-1-241, which expires 2026-11-07 21:31 KST.
  - prod-app-q/app-q-backend-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1c. It runs on node-2-218, which expires 2026-11-07 21:32 KST.
  - prod-app-l-backend/app-l-neo4j: vol-0123456789abcdef0, 20Gi, us-east-1c. It runs on node-2-135, which expires 2026-11-08 15:28 KST.
  - prod-app-o/app-o-backend-mysql: vol-0123456789abcdef0, 50Gi, us-east-1a, on node-1-117.
  - app-s-prod/app-s-backend-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1a, on node-1-117.
  - prod-app-m/app-m-backend-mysql: vol-0123456789abcdef0, 8Gi, us-east-1c, on node-2-60.
  - prod-app-n/app-n-backend-prod-mysql: vol-0123456789abcdef0, 8Gi, us-east-1c, on node-2-60.
  - Not among the 7, but also left out of steps ② and ③: the Kafka broker's volume middleware/data-kafka-controller-0 (vol-0123456789abcdef0, 20Gi, Delete) and another middleware PV (vol-0123456789abcdef0).
- Checked and healthy:
  - EBS volumes live apart from nodes, so a node expiry alone does not lose data.
  - The only snapshots are from 2026-10-06. They were taken before 12 orphan PVCs were deleted, and none are of live prod volumes. They carry a delete-after 2026-11-07 tag, and no policy deletes them automatically, but if someone deletes them on that date the last copy of that data is gone.
- Changed for another reason: Karpenter's 720h expiry replacement soon moves the DB pods on node-1-241, node-2-218 and node-2-135.
- Not checked:
  - whether dumps run outside the cluster
  - each DB's data size and write volume
  - whether anyone has ever restored from a volume

**Why.** Nothing in the account or the cluster makes backups, and the volumes got the dynamic-provisioning default, reclaimPolicy Delete. Confirmed.

**Suggested fix.**

① Make sure the account really has no snapshot policy and no backup plan.

```
aws dlm get-lifecycle-policies --profile acme --region us-east-1
```

```
aws backup list-backup-plans --profile acme --region us-east-1
```

These only read.

Check: if both return empty lists, there is no backup. These commands do not see backups in other accounts or regions, or dump scripts running outside the cluster.

② Before the node expiry at 2026-11-07 21:31 KST, take EBS snapshots of the 7 prod DB volumes.

```
for v in vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0; do aws ec2 create-snapshot --profile acme --region us-east-1 --volume-id "$v" --description "manual prod db backup 2026-11-06" --tag-specifications 'ResourceType=snapshot,Tags=[{Key=purpose,Value=manual-prod-db-backup}]'; done
```

This creates 7 snapshots. Pods and volumes stay as they are, nothing restarts, and snapshot storage is billed.

The DBs keep running during the snapshot, so it captures the disk as if the power had been cut. MySQL and PostgreSQL usually recover when they start. Whether Neo4j community opens from such a snapshot is unverified.

The volumes are not encrypted, so the snapshots are not either. No one has tried a restore. The two Kafka volumes are not in this loop.

Check: `aws ec2 describe-snapshots --profile acme --region us-east-1 --owner-ids self --filters Name=tag:purpose,Values=manual-prod-db-backup --query 'Snapshots[].[VolumeId,State]' --output table` shows 7 rows, all completed.

③ Set reclaimPolicy to Retain on the 7 prod DB PVs.

```
for pv in pvc-1a304f49-fa2e-43ed-a996-df104613c88c pvc-5cccf1df-7624-45a2-833d-2191c5490713 pvc-8d1f15c7-e0e6-4410-bd40-64d7332aef0d pvc-9f1aab56-d94c-499d-8df6-2def93e79427 pvc-a50dcc70-b062-457a-b0e3-07a3e6da2ec6 pvc-ebc5618b-a1af-40d3-b15d-4969ed13487e pvc-f226562f-a020-4027-a0d4-1494585c8b6f; do kubectl --context my-cluster patch pv "$pv" -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'; done
```

Only one line of each PV spec changes, and no pod restarts. From then on, a deleted PVC leaves its EBS volume behind.

PVs carry no Argo CD tracking label, so selfHeal does not revert this. A volume left behind keeps billing until someone deletes it by hand.

Check: `kubectl --context my-cluster get pv -o custom-columns=NAME:.metadata.name,CLAIM:.spec.claimRef.name,POLICY:.spec.persistentVolumeReclaimPolicy` shows Retain on all 7.

④ Set up a backup that runs every day. This step is a plan, so it has no command.

- Snapshot the volumes tagged KubernetesCluster=my-cluster every day with a DLM policy or an AWS Backup plan, and keep them 7 to 14 days.
- For each DB, add a CronJob that sends a mysqldump, pg_dump or neo4j-admin dump to S3.
- Restore one snapshot to a new volume and test that the DB opens.

Snapshots and dumps then pile up on a fixed schedule.

A dump CronJob that saves only to the same node's disk is lost with the node. Neo4j community has no online backup, so a dump may need the DB stopped. That is unverified.

Picking volumes by tag also snapshots other volumes, such as Prometheus and vm-single, which raises the bill.

Check: `aws dlm get-lifecycle-policies` shows one ENABLED policy, and 7 or more snapshots appear the next day.

**Rollback.** Delete a snapshot with `aws ec2 delete-snapshot --profile acme --region us-east-1 --snapshot-id <snapshot-id>`. Undo step ③ by running the same loop with Delete instead of Retain, and set a DLM policy to DISABLED or delete it. No step deletes data.

**Why this happens.**

- Principle: A volume survives its node dying. If it is wrongly deleted or broken, though, only a snapshot brings it back. With reclaimPolicy Delete, one namespace deletion or one Argo CD prune removes the volume at once.
- Case: In 2023 at InfluxData, automation produced a wrong Argo CD Application name and a whole production environment was deleted. Their volumes were Retain and their data was backed up, so they recovered without data loss in a little under 6 hours. Here, Argo CD also manages the 8 prod apps with prune and selfHeal, but the 7 prod DB volumes are Delete and have no backup.
- Read: the Amazon Data Lifecycle Manager user guide; the Kubernetes documentation on the Reclaim Policy of Persistent Volumes

**Evidence.**

| What | Value | Source |
|---|---|---|
| Backup CronJobs in the cluster, 7 days | 0 | summary.json |
| DLM lifecycle policies, us-east-1 | none | aws/dlm-lifecycle-policies.json |
| AWS Backup plans, us-east-1 | none | aws/backup-plans.json |
| Prod DBs with no backup CronJob | 7 | summary.json |
| DB workloads with a PVC, dev included | 17 | summary.json |
| Snapshots of live prod volumes, 30 days | 0 of 12 | aws/ec2-snapshots-30d.json |

## 2. Prod pods piled on one spot node

**What is happening.** Spot node node-1-139 (r8gd.xlarge, us-east-1a) holds 20 of the 42 prod pods, from 15 prod workloads. It is 301.9 hours past expireAfter 720h. Karpenter cannot replace it because prod-app-m/app-m-admin carries do-not-disrupt. One spot reclaim stops all of these services at once.

- Affected:
  - prod-app-o/app-o-ai: all 3 replicas are on this node, with no topologySpread, no PDB and no readiness probe.
  - prod-app-o/app-o-backend: both replicas are on this node, with no PDB and no readiness probe.
  - prod-app-r/app-r: both replicas are on this node, with PDB minAvailable 1.
  - prod-app-l-backend/app-l-frontend: both replicas are on this node, and its preferred podAntiAffinity is not honored. It has PDB minAvailable 1.
  - The node used all 4 of its ENIs and hit "no available IP" 4 times.
  - 6 single-replica prod workloads have their only pod here:
    - app-m-admin
    - app-o-admin
    - app-o-frontend
    - app-p-backend
    - app-n-admin-frontend
    - app-s-backend
- Checked and healthy:
  - prod-app-m api, backend and frontend are split across node-1-139 and node-1-62 by a required podAntiAffinity, though both nodes are in us-east-1a.
  - The 2 Karpenter controllers sit on two node group nodes and have a PDB.
  - No pods were Pending.
- Changed for another reason: 41 nodes left in 24 hours. Karpenter removed the nodes it had launched for the app-l workers once they were empty, or through consolidation.
- Not checked:
  - whether node-1-139 got a spot reclaim warning in the past 42 days
  - real user traffic on the single-replica services

**Why.** The do-not-disrupt annotation on the app-m-admin pod template stops Karpenter from emptying this node for expiry or consolidation. Prod Deployments have no topologySpreadConstraints, so the scheduler kept putting pods on the node with the most room. Confirmed. Why the annotation was added is unknown.

**Suggested fix.**

① See what is on the node.

```
kubectl --context my-cluster get pods -A -o wide --field-selector spec.nodeName=node-1-139
```

Then see why the replacement is blocked.

```
kubectl --context my-cluster get events -A --field-selector involvedObject.name=default-n44bh
```

These only read.

Check: the node has 38 pods, and the DisruptionBlocked event names the do-not-disrupt pod app-m-admin.

② In the IAC repo, add hostname topologySpreadConstraints to the pod templates of app-o-ai, app-o-backend, app-r and app-l-frontend. Add a PDB to app-o-ai and app-o-backend.

```yaml
# Add under Deployment spec.template.spec (app-o-ai shown; for the others change only matchLabels)
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/instance: app-o-prod
        app.kubernetes.io/name: ai
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-o-ai
  namespace: prod-app-o
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/instance: app-o-prod
      app.kubernetes.io/name: ai
```

When Argo CD syncs, the four Deployments roll. New pods go to node-1-62 or to a new app node from Karpenter. The scheduler counts only nodes labeled workload-type=app.

Argo CD selfHeal reverts kubectl changes, so make this change in the repo. Whether the chart value names match this snippet is unverified.

The app-o workloads have no readiness probe. New pods count as Ready at once, and requests can fail before the app is up.

app-o-ai requests 2Gi of memory per pod, and node-1-62 has 0.26 cores of CPU free, so a new node may be needed. maxUnavailable is 0, so old pods stay until the new ones are up.

Check: `kubectl --context my-cluster -n prod-app-o get pods -o wide` shows the ai and backend pods on two or more nodes. `kubectl --context my-cluster -n prod-app-o get pdb` lists app-o-ai and app-o-backend.

③ Once step ② is done, pick a low-traffic time. First ask whoever added the annotation why they added it. Then remove karpenter.sh/do-not-disrupt from app-m-admin's pod annotations in apps/prod/app-m in the IAC repo.

```yaml
# Remove this line from the app-m-admin pod template annotations (key name in the values file unverified)
karpenter.sh/do-not-disrupt: "true"
```

app-m-admin rolls with maxSurge 1, maxUnavailable 0 and readiness on /. The new pod has no annotation, so Karpenter replaces the expired node-1-139.

It launches a new node first, then evicts the 38 pods while honoring PDBs. The default pool budget is 10%, so nodes go one at a time.

The 6 single-replica prod workloads above stop until their new pod is Ready. app-o-admin, app-o-frontend, app-n-admin-frontend and app-s-backend have no readiness probe.

The external-secrets controller (1 replica) and 12 dev pods move too, and the new node may also be spot. If the annotation was protecting a long admin task, that task gets cut off.

Check: `kubectl --context my-cluster get nodeclaims` no longer shows default-n44bh, and `kubectl --context my-cluster get pods -A -o wide --field-selector spec.nodeName=node-1-139` returns an empty list.

④ Change the default NodePool setup so it stops packing pods onto one big node. This step is a plan, so it has no command.

- In the shared values of the prod app charts, add hostname and zone topologySpreadConstraints by default.
- Cap the instance size of NodePool default, or add a separate on-demand pool for prod.
- Turn on VPC CNI prefix delegation so nodes hit the ENI limit less often.

App pods then spread over several nodes, and losing one node leaves most services up.

Drift is on, so changing the NodePool requirements replaces default pool nodes one at a time. On-demand costs more.

Prefix delegation reaches existing nodes only once they are replaced.

Check: resilience.placement.prod_max_share in the summary drops below 0.3.

**Rollback.** Every change is a commit in the IAC repo. Revert it and Argo CD puts things back. A replaced node cannot be brought back, and there is no need to.

**Why this happens.**

- Principle: Two replicas exist so one can die while the other carries on. On the same node, both go with that node. Without a declared spread, the scheduler packs pods wherever there is room, and Karpenter consolidation packs them even harder. On spot, one reclaim is enough.
- Case: At Moonlight, Kubernetes sometimes put all 3 website pods on one node, which made it a single point of failure. Sustained 100% CPU caused kernel panics, and the pods moved and repeated the pattern, so the service went down on and off from January 18 to 22. They fixed it with anti-affinity rules. Here, app-o-ai's 3 replicas and the 2 replicas each of app-o-backend, app-r and app-l-frontend all sit on one spot node, node-1-139.
- Read: the Kubernetes documentation, Pod Topology Spread Constraints; the Karpenter documentation, Disruption

**Evidence.**

| What | Value | Source |
|---|---|---|
| Prod pods on node-1-139 | 20 | summary.json |
| Share of all 42 prod pods | 0.48 | summary.json |
| Hours past expireAfter, default-n44bh | 301.9 | summary.json |
| Replacements blocked by do-not-disrupt, cumulative | 21337 | summary.json |
| NodeClaims removed by spot reclaim since 2026-08-28 | 261 | summary.json |
| Free CPU on node-1-62 | 0.26 cores | summary.json |

## 3. Kafka listener open to the internet

**What is happening.** The Service middleware/kafka-controller-0-external created an internet-facing NLB. Its security group opens ports 9094 and 443 to 0.0.0.0/0, in front of a single broker. SASL users are set up, but whether the external listener uses TLS is unknown. The NLB carried about 2.87GB in 24 hours with up to 146 connections at once, so it is in real use.

- Affected: middleware/kafka-controller. Its external listener, container port 9095, is bound to NLB ports 9094 and 443, and the security group allows 0.0.0.0/0.
- Checked and healthy:
  - The shared DB NLB acme-db-shared opens each port to 4 or fewer /32 addresses.
  - Kafka has SASL client users set in KAFKA_CLIENT_USERS.
- Changed for another reason: none
- Not checked:
  - which outside addresses connect
  - whether the external listener uses TLS
  - auth failures in the broker log

**Why.** The external access setting of Helm release kafka (bitnami kafka 26.8.1) created an internet-facing NLB without limiting source addresses. So the AWS Load Balancer Controller opened the security group to 0.0.0.0/0. Confirmed.

**Suggested fix.**

① Read only the listener lines from the ConfigMap to see the external listener's protocol.

```
kubectl --context my-cluster -n middleware get configmap kafka-controller-configuration -o jsonpath='{.data.server\.properties}' | grep -E '^(listeners|advertised\.listeners|listener\.security\.protocol\.map)='
```

This only reads, and it prints only these three lines.

Check: if EXTERNAL is SASL_SSL in listener.security.protocol.map, the traffic is encrypted. If it is SASL_PLAINTEXT or PLAINTEXT, passwords and data cross the internet unencrypted.

② Find the outside clients. This step is a plan, so it has no command.

Ask the Kafka owner which systems connect from outside. If no one knows, turn on VPC Flow Logs on the NLB subnets for a day and collect the source addresses on 9094 and 443.

Logs then pile up in CloudWatch Logs or S3.

Log storage is billed, so remember to turn the logs off.

Check: you have a list of source addresses.

③ Once you know every client address, narrow loadBalancerSourceRanges on the external Service to those addresses in the Helm values.

```yaml
# Add to the values of the kafka helm_release (bitnami kafka 26.8.1) in the Terraform code that built the cluster. Key names are unverified.
externalAccess:
  controller:
    service:
      loadBalancerSourceRanges:
        - <client-ip>/32
        - <NAT 게이트웨이 EIP>/32  # when pods inside the cluster connect through the external address
```

Before you apply, run terraform plan. Confirm that nothing changes outside the kafka release and that the StatefulSet pod template stays the same.

The AWS Load Balancer Controller then replaces the 0.0.0.0/0 rule with those addresses. Connections from anywhere else are cut.

Terraform's helm provider manages this release. A manual helm upgrade gets reverted at the next terraform apply, so change it in the Terraform code.

If the plan shows a change to StatefulSet kafka-controller, the single broker restarts and all of Kafka stops.

Pods inside the cluster that use the NLB's external address arrive from the NAT gateway address. Leave that address out and those pods are cut off too, as is any client you missed.

The broker runs on node-2-135, which expires 2026-11-08 15:28 KST. It restarts then whether or not you make this change, so do not schedule this change for that time.

Check: `aws ec2 describe-security-groups --profile acme --region us-east-1 --group-ids sg-0123456789abcdef0 --query 'SecurityGroups[].IpPermissions[].IpRanges'` shows no 0.0.0.0/0. Leave sg-0123456789abcdef0 out of this check, since the prod ALB shares it.

**Rollback.** Revert the Terraform commit and run terraform apply again, and the security group opens again. Delete the flow logs to undo step ②.

**Why this happens.**

- Principle: When a DB or message queue port sits on an internet-facing load balancer, one password is all that guards the data. On AWS, the load balancer's security group decides who can connect. An internal scheme or a VPN is a safer shape.
- Read: the AWS Load Balancer Controller documentation on Service annotations and loadBalancerSourceRanges; the Apache Kafka documentation on Security

**Evidence.**

| What | Value | Source |
|---|---|---|
| Source of the 9094 inbound rule | 0.0.0.0/0 | summary.json |
| Bytes processed by the NLB, 24h | 2868958720 | summary.json |
| Peak concurrent connections, 24h | 146 | summary.json |
| Exposed port on kafka-controller-0-external | 9094 | summary.json |

## 4. 4 prod ALB health checks failing

**What is happening.** Every target in 4 prod target groups on the shared ALB acme-prod-lb is unhealthy. The health check goes to /, where the two backends answer 404 and the two frontends answer 307. When every target fails, the ALB sends traffic to all of them. So the services answer now, but a dead pod is not filtered out either.

- Affected:
  - prod-app-q/app-q-backend: 1 target unhealthy with Target.ResponseCodeMismatch [404]. The pod's readiness on /health, port 3000, passes.
  - prod-app-l-backend/app-l-backend: 2 targets unhealthy with [404]. Readiness on /health, port 8000, passes.
  - prod-app-o/app-o-frontend: 1 target unhealthy with [307], a redirect. It has no readiness probe.
  - prod-app-n/app-n-frontend: 1 target unhealthy with [307]. It has no readiness probe and had 1,482 4xx and 26 5xx in 24 hours.
- Checked and healthy:
  - app-q-ai, app-q-studio and app-q-web in prod-app-q already use healthcheck-path /health.
  - dev-app-n/app-n-frontend and dev-app-t/app-t-backend fail too, but they are dev.
- Changed for another reason: none
- Not checked:
  - which path returns 200 on the two frontends, and where their 307 points
  - whether /health returns 200 or a 3xx

**Why.** The four Ingresses have no alb.ingress.kubernetes.io/healthcheck-path, so the ALB checks /, and these apps do not answer / with 200. Confirmed.

**Suggested fix.**

① Look at the target health straight from AWS.

```
aws elbv2 describe-target-health --profile acme --region us-east-1 --target-group-arn $(aws elbv2 describe-target-groups --profile acme --region us-east-1 --names k8s-app-svc-36f816b829 --query 'TargetGroups[0].TargetGroupArn' --output text)
```

This only reads.

Check: State unhealthy with Reason Target.ResponseCodeMismatch. The other three target groups are k8s-app-svc-bb495c72c8, k8s-app-svc-8c88bb317a and k8s-app-svc-032c25d752.

② In the IAC repo, add healthcheck-path /health to the app-q-backend and app-l-backend Ingresses.

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/healthcheck-path: /health
```

The AWS Load Balancer Controller changes only the health check path of the two target groups, and no pod restarts. Once targets turn healthy, the ALB sends traffic only to healthy targets.

40 Ingresses share one ALB group, acme-prod-lb. A bad annotation on one Ingress can stall reconciling for the whole group.

Readiness counts 200 to 399 as success, but the ALB accepts only 200. If /health returns a 3xx, the check still fails.

If /health checks the DB, every target fails when the DB goes down, and the ALB goes back to sending traffic to all of them. Argo CD selfHeal is on, so change this in the repo.

Check: run the step ① command twice, with --names k8s-app-svc-bb495c72c8 and then k8s-app-svc-8c88bb317a. Every target shows State healthy.

③ Find a path that returns 200 on the two frontends. First open a port-forward.

```
kubectl --context my-cluster -n prod-app-n port-forward deploy/app-n-frontend 3000:3000
```

Then, in another terminal, check the status code.

```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
```

This opens only a local port-forward, and the cluster does not change.

Check: / returns 307 now, which fails the ALB's 200 matcher. Use `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n'` to see where it redirects, and try other paths until one returns 200. For app-o-frontend, do the same in prod-app-o on port 3003.

④ Once you have a 200 path, add it as healthcheck-path on both frontend Ingresses and as a readinessProbe on both Deployments.

```yaml
# Ingress
alb.ingress.kubernetes.io/healthcheck-path: <200-path>
# Deployment containers[0]
readinessProbe:
  httpGet:
    path: <200-path>
    port: http
  periodSeconds: 10
```

The Ingress change touches only the target group settings. The readinessProbe changes the pod template, so a rolling update runs.

Both Deployments have 1 replica, maxSurge 25% and maxUnavailable 25%, so the new pod starts first. If the path is wrong, the new pod never gets Ready and the rollout stalls.

After 600 seconds the rollout only gets marked ProgressDeadlineExceeded, and Kubernetes does not roll back by itself. The old pod keeps answering in the meantime.

Check: `kubectl --context my-cluster -n prod-app-n rollout status deploy/app-n-frontend` and `kubectl --context my-cluster -n prod-app-o rollout status deploy/app-o-frontend` both finish. Then the step ① command shows healthy with --names k8s-app-svc-36f816b829 and with k8s-app-svc-032c25d752.

**Rollback.** Every change is a repo commit. Revert it and Argo CD puts things back, with the health check on / again.

**Why this happens.**

- Principle: The ALB stops sending traffic to a target its own health check calls unhealthy. When all targets are unhealthy, it sends to all of them, so nothing looks broken, but the check filters out nothing. This check is separate from Kubernetes readiness, so a Ready pod can still be dropped by the ALB.
- Read: the AWS Load Balancer Controller documentation on Ingress annotations; the Elastic Load Balancing documentation on target group health checks

**Evidence.**

| What | Value | Source |
|---|---|---|
| app-n-frontend requests, 24h | 9938 | summary.json |
| app-n-frontend healthy targets | 0 of 1 | summary.json |
| app-q-backend requests, 24h | 5849 | summary.json |
| app-l-backend healthy targets | 0 of 2 | summary.json |
| app-o-frontend requests, 24h | 1258 | summary.json |

## 5. Unsupported EKS, Karpenter and AL2

**What is happening.** EKS 1.32's standard support ended on 2026-03-23, so the cluster now pays for extended support, which ends on 2027-03-23. Karpenter 0.37.0 supports Kubernetes only up to 1.30. Its EC2NodeClass default runs Amazon Linux 2, which has had no new EKS AMIs since 2025-11-26 and has none for 1.33. Unless the three are sorted out in order, new nodes may not come up at the next upgrade, and the node group AMI is already 331 days old.

- Affected: karpenter/karpenter logged "failed validating kubernetes version" once, at 2026-11-04 17:48 KST.
- Checked and healthy:
  - Karpenter still launches nodes. It has made 859 NodeClaims since its leader started, and 41 nodes got ready in 24 hours at a p50 of 58 seconds.
  - The 4 EKS add-ons are ACTIVE with 0 health issues.
- Changed for another reason: none
- Not checked:
  - whether the workloads run fine on cgroup v2 under AL2023
  - whether charts or manifests use APIs removed in 1.33

**Why.** Most likely, Karpenter and the EC2NodeClass were not upgraded when EKS went to 1.32. Likely: the cluster is on 1.32 while Karpenter is still 0.37 and the node class is still AL2.

**Suggested fix.**

① Look at the EKS upgrade insights for anything that blocks the upgrade.

```
aws eks list-insights --profile acme --region us-east-1 --cluster-name my-cluster --output table
```

This only reads.

Check: Amazon Linux 2 compatibility shows ERROR. Note down any other ERROR or WARNING items too.

② Move from AL2 to AL2023. This step is a plan, so it has no command.

Create a new AL2023 EC2NodeClass for the build-arm64 pool and test it with the CI runners first. If nothing breaks, change amiFamily on the default class to AL2023.

Drift is on, so changing the default class replaces the 6 Karpenter nodes one per pool at a time.

Every replacement moves the pods on that node, and single-replica services and DBs stop meanwhile.

node-1-139 also blocks drift replacement because of do-not-disrupt, as in problem 2. AL2023 uses cgroup v2, so older JVMs and runtimes may read memory limits differently.

Check: `kubectl --context my-cluster get nodes -o wide` shows Amazon Linux 2023 as OS-IMAGE on every node.

③ Once AL2023 is in place, problem 2 has replaced node-1-139, and no node is past 720h at upgrade time: upgrade Karpenter from 0.37 to 1.0. Then go on to a 1.x that supports 1.32 and 1.33. This step is a plan, so it has no command.

The API changes from v1beta1 to v1, so follow the order in the official upgrade guide. NodePool and EC2NodeClass move to the v1 API.

While the controller is down during the upgrade, no new node comes up. Workloads that scale from zero, such as the app-l workers, wait.

From v1, expiry is forced. An expired node is emptied at once, ignoring do-not-disrupt, and no replacement node is launched first.

Right after the upgrade, every pod on a node past 720h gets evicted at once, and single-replica services stop. Today that node is node-1-139, with 20 prod pods.

Without a terminationGracePeriod, a pod held by a PDB can keep its node around forever.

Check: `kubectl --context my-cluster -n karpenter get deploy karpenter -o jsonpath='{.spec.template.spec.containers[0].image}'` shows the new version, and "failed validating kubernetes version" no longer appears in the log.

④ Once Karpenter supports 1.33, upgrade EKS to 1.33 along with the system_core node group AMI and the 4 add-ons. This step is a plan, so it has no command. Finish before 2027-03-23.

The control plane, the 2 node group nodes and the add-ons move to new versions.

The two node group nodes run 3 prod MySQL, app-s PostgreSQL and argocd-application-controller, and these stop while their node is replaced. Take the snapshots from problem 1 before the upgrade.

Check: `aws eks describe-cluster --profile acme --region us-east-1 --name my-cluster --query cluster.version` returns 1.33.

**Rollback.** The EKS control plane version cannot be undone, so check the insights and backups before upgrading. The AMI and Karpenter can step back, but that gets hard once the Karpenter CRDs move to v1. That is why the snapshots in problem 1 come first.

**Why this happens.**

- Principle: A minor version out of support gets no security patches, and EKS charges for extended support. Outside its support table, Karpenter can fail to find an AMI and so cannot launch nodes. From 1.33 there are no AL2 AMIs at all.
- Case: In 2025 at ZenML, Terraform turned on KMS secret encryption during a production EKS upgrade. That dropped IAM permissions from the worker nodes, and pods were unreachable from outside the cluster for about 8 hours. They fixed it by rebuilding the node group, and an old Kubernetes version and AMI type were among the contributing factors. This cluster also runs 1.32 past standard support, on AL2 AMIs, with an unsupported Karpenter. Doing all the overdue upgrades at once stacks up the same kind of risk.
- Read: the Karpenter documentation, Upgrading to v1.0 and Compatibility; the Amazon EKS documentation, Kubernetes version lifecycle and moving to AL2023

**Evidence.**

| What | Value | Source |
|---|---|---|
| EKS support type | EXTENDED | inventory.json |
| End of extended support, 1.32 | 2027-03-23 | aws/describe-cluster-versions.json |
| Karpenter version | 0.37.0 | summary.json |
| Highest Kubernetes supported by Karpenter 0.37 | 1.30 | summary.json |
| AMI family of EC2NodeClass default | AL2 | summary.json |

## Since the previous full run

2026-11-03T11-17-15 full 점검이에요. 그 점검에는 리포트가 없어서, 시킨 일을 했는지는 따질 수 없어요.

Work the previous report asked for: none

**Appeared.**

- 노드 node-2-158(build-arm64 풀, c6gn.xlarge 스팟)이 2026-11-05 15:49 KST에 새로 떴어요. 7일 CPU p95가 0.02라 유휴 노드로 잡혔고, 이 노드에서 EC2 CreateNetworkInterface 실패가 11번 있었어요.
- 노드 node-1-62의 루트 디스크 사용률이 79%가 됐어요.
- prod-app-o/app-o-frontend가 하루 종일 CPU 스로틀링을 받아요. 지금 비율은 0.15예요.
- prod-app-l-backend의 app-l-file-worker는 CPU 요청이 1코어인데 krr 권장값은 0.128코어예요. app-l-graph-worker도 1코어 요청에 권장값 0.542코어예요. keda-hpa-app-l-file-worker는 7일 동안 원하는 레플리카 수가 48번 바뀌었어요.
- prod-app-m/app-m-frontend(www.example-b.ai)에서 24시간 동안 요청 54991건 중 5xx가 80건(0.14%) 났어요.
- Grafana(monitor.my-cluster)의 요청 가중 p95가 2.8초예요.
- API 서버가 초당 0.004건의 503을 냈어요. 수집 중에 잰 값이라 kubegap이 보낸 요청이 섞였을 수 있어요.

**Went away.**

- 노드 node-2-144가 클러스터를 떠났어요. 그 노드의 유휴 노드 경고와 cgroup v1 경고도 같이 없어졌어요.
- Promtail의 메모리 사용이 limit에 붙어 있던 문제가 없어졌어요.
- middleware/kafka-exporter의 Not Ready가 없어졌어요. 다만 파드 재시작 수는 5번이에요.
- 노드 <ip>와 <ip>의 네트워크 오류 경고가 없어졌어요.
- Prometheus의 OOM 기록(2026-10-06)이 30일이 지나 집계에서 빠졌어요.

**Changed because the checks changed, not the cluster.**

- 노드 하나를 잃었을 때 버티는지(N+1) 경고가 새로 생겼어요. 클러스터가 바뀐 게 아니라, app 노드에만 뜰 수 있는 파드를 그 노드들의 남은 자리로 따로 계산하도록 체크가 바뀐 결과예요(rubric 0.1.65).
- 외부 DB NLB acme-db-shared가 fail에서 warn으로 내려왔어요. 보안 그룹 규칙을 읽어서 /32 주소 목록으로만 열린 걸 보도록 체크가 바뀐 결과예요(rubric 0.1.64).
- prod-app-m/app-m-frontend 스로틀링이 fail에서 warn으로, Prometheus 스로틀링이 warn에서 fail로 바뀌었어요. 5분 비율 대신 24시간 비율로 보도록 체크가 바뀐 결과예요(rubric 0.1.66).
- prod-app-q/app-q-ai의 반복 OOM이 warn에서 fail로 올라갔어요. 살아 있는 파드만 보던 체크가 7일 동안 끝난 파드까지 세도록 바뀐 결과예요(rubric 0.1.66).
- app-q-ai의 p95 지연이 fail에서 warn으로, app-l-frontend의 지연 경고는 없어졌어요. 요청 가중 p95로 보도록 체크가 바뀐 결과예요(rubric 0.1.65).
- arc-runners 러너 파드의 큰 요청 경고는 러너 파드 이름이 바뀐 것이지 새로 생긴 게 아니에요.
- prod 네임스페이스 8개의 쿼터 없음과 prod-app-l-backend의 LimitRange 없음이 warn에서 fail로 바뀌었어요. ResourceQuota와 LimitRange 오브젝트는 두 점검 사이에 바뀌지 않았어요. 체크 기록에는 이 규칙이 바뀌었다는 설명이 없어서, 규칙 변경인지는 확인하지 못했어요.

## Serious, not today

- No symptom alerts and no SLOs. 0 of 157 alert rules watch user symptoms, and nothing alerts on OOM, scheduling failure or IP exhaustion. Nothing gets lost or exposed today, so this waits.
- The EKS public API endpoint is open to 0.0.0.0/0. IAM guards access, and narrowing it first needs the source addresses of CI and of people.
- 3 NetworkPolicies, in prod-app-q, prod-app-p and app-s-prod, block nothing because aws-eks-nodeagent runs with --enable-network-policy=false. Turning it on applies them at once and can cut traffic, so review the policies first.
- Monitoring data sits on emptyDir. Loki storage and Alertmanager data vanish when their pods move, and the upcoming node expiry can wipe Loki's logs. Loki died once from OOM on 2026-10-25. Prometheus uses 73% of its 1536Mi memory limit and has a CPU throttling ratio of 0.28.
- argocd/argocd-application-controller-0 restarted 42 times, last ending OOMKilled on 2026-10-30. It syncs every prod app, and its memory limit change is done separately.
- prod-app-q/app-q-ai lost 3 pods to OOM in 7 days and runs 1 replica now.
- Kubernetes events are not kept anywhere, so they vanish after about an hour.
- System nodes node-1-241 (t8i.small) and node-2-218 (t8i.medium) hit their ENI limit, with pod IPs at 6/9 and 13/15, and prefix delegation is off.
- prod-app-l-backend/tts-proxy runs as root with NET_ADMIN and a /dev/net/tun hostPath. It is a Tailscale sidecar, so it may need these.
- Root disks are at 81% on node-1-139 and 79% on node-1-62, and kubelet image GC failed twice on node-1-139. Replacing that node in problem 2 clears it.
- ExternalSecret database/mysql-app-n-secret has failed to sync since 2026-10-08, with 2556 UpdateFailed.
- Frontends are throttled on CPU all day: prod-app-m/app-m-frontend at 0.23–0.28 and prod-app-o/app-o-frontend at 0.15. Two dev frontends are the same.
- All 8 instances have IMDS hop limit 2, and EC2NodeClass default does not set root volume encryption.
- 115 Unhealthy probe events came from prod-app-m/app-m-backend pods, promtail and app-l-file-worker.

## Each area in one line

| Area | What |
|---|---|
| resources | 요청 과다 컨테이너 34개와 OOM 세 건이 있어요. 프론트엔드는 하루 종일 스로틀링을 받아요. |
| scaling | 만료를 넘긴 노드 하나와 곧 만료되는 노드 세 대가 있어요. HPA 대부분은 늘어난 적이 없어요. |
| observability | 증상 알림과 SLO가 없고, 잘못 잡힌 컨트롤플레인 알림이 57.8일째 울려요. |
| traffic | Kafka가 인터넷에 열려 있고, prod 헬스 체크 4개가 아무것도 걸러내지 못해요. |
| resilience | prod DB 백업이 없고, prod 파드 절반이 스팟 노드 한 대에 있어요. |
| hygiene | 변경과 장애의 시각을 맞출 재료가 없어요. 오래된 ReplicaSet이 353개 남아 있어요. |
| storage | prod DB 볼륨이 reclaimPolicy Delete이고 StorageClass 3개가 암호화되지 않았어요. |
| security | API 엔드포인트가 전체 공개이고 NetworkPolicy가 적용되지 않아요. |
| cost | 노드 비용의 95%가 유휴이고, 요청을 줄이면 월 162.65 USD쯤 줄어요. |
| tenancy | prod 네임스페이스 8개에 쿼터가 없지만, 7일 동안 이웃 영향의 근거는 없어요. |
| node OS | AL2 노드는 cgroup v1이고 노드 그룹 두 대는 읽지 못했어요. |
| platform | EKS, Karpenter, AMI가 모두 지원 범위 밖이거나 끝나 가요. |

## What this run could not see

- Inside node-1-117 and node-2-60, the two system_core node group nodes, because they are not registered in SSM. Disk, kernel log, kubelet and containerd journals, and VPC CNI IPAMD were not read, and these nodes run argocd-application-controller, 3 prod MySQL and app-s PostgreSQL. To see them, attach AmazonSSMManagedInstanceCore to the node group IAM role and confirm the SSM agent is online.
- Inside any node from the next run on, because the SSM document kubegap-node-read no longer matches the repo version. To fix it, run `kubegap setup --context my-cluster --install-ssm-document`.
- Grafana data sources and dashboards, because there is no read token. To see them, create a Viewer service account token in Grafana and put it in grafana_api_token in config.yaml yourself.
- Who changed what and when, because EKS audit logging is off. To see it, turn on audit in EKS control plane logging.
- Whether the Kafka external listener uses TLS, because only the length and shape of ConfigMap values were kept. To see it, run step ① of problem 3.
- Which addresses connect to the Kafka NLB and the DB NLB, because there are no NLB flow logs. To see them, turn on VPC Flow Logs on the NLB subnets for a day.
- Whether DB dumps run outside the cluster, such as on developer PCs or in jobs in other accounts. To find out, ask each service owner where their dumps are and when they last tested a restore.

## Numbers

| Severity | fail | warn | vs. previous full run |
|---|---|---|---|
| critical | 1 | 0 | fail 0, warn +1 |
| high | 25 | 24 | fail -1, warn +1 |
| medium | 126 | 166 | fail +9, warn -4 |
| low | 16 | 140 | fail 0, warn +1 |

Checks behind each problem:

- problem 1: `resilience.no-backup.cluster`, `eks.no-backup-policy.cluster`, `resilience.prod-db-without-backup-cronjob.cluster`, `storage.prod-db-reclaim-delete.cluster`, `storage.csi-snapshot-unavailable.cluster`, `logs.signatures.ebs-csi.snapshot-crd-missing`
- problem 2: `resilience.prod-concentration.node-1-139`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend`, `resilience.replicas-same-node.prod-app-r/deployment/app-r`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend`, `resilience.n-plus-one.cluster`, `scaling.karpenter-expired-not-replaced.default-n44bh`, `vpccni.node-ip-exhaustion.node-1-139`, `resilience.no-pdb.prod-app-o/app-o-ai`, `resilience.no-pdb.prod-app-o/app-o-backend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server`
- problem 3: `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external`, `traffic.db-exposed.nlb/acme-db-shared`
- problem 4: `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend`, `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend`, `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend`, `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend`
- problem 5: `platform.k8s-version-eol.cluster`, `eks.extended-support.cluster`, `platform.karpenter-version-compat.cluster`, `karpenter.ec2nodeclass-al2.cluster`, `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility`, `eks.node-os-skew.cluster`, `eks.nodegroup-ami-old.nodegroups`, `logs.signatures.karpenter.version-unsupported`, `node.cgroup-v1.node-2-158`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · snapshot `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`

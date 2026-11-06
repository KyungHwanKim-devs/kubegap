# my-cluster — daily audit, 2026-11-05 17:01

Urgent now: no

Today's problems: ① Prod pods stuck on one spot node ② Four prod ALB health checks failing ③ app-q-ai OOM kills, no OOM alert

Since the last run: No work from the 2026-10-27 report is recorded as done or still open.

Appeared, 7: the cluster no longer survives losing its largest node, 3 app-q-ai pods were OOM-killed, and argocd-application-controller-0 was OOM-killed again. Also new: 61 of 251 IPs free in subnet us-east-1c, a 79% full root disk on <ip>, app-l-file-worker and app-l-graph-worker not ready for about 180 and 160 minutes in 24 hours, and p95 latency of 2.32 s and 2.51 s on app-q-ai.my-cluster and monitor.my-cluster.

Gone, 5: FreeDiskSpaceFailed events stopped, and so did the long-firing KubePodNotReady alerts in four namespaces. Subnet us-east-1a is no longer short of IPs, and app-p-backend's ALB target group no longer reports unhealthy targets. Prod pods on node-1-139 fell from 62% to 45%. The audit rules changed between the runs, so some new and gone items may come from the rules, not the cluster.

Coming up: these NodeClaims reach their 720h expireAfter, and Karpenter then replaces each node and evicts its pods:

- system-ondemand-mxf5q (node-1-241) at 2026-11-07 12:31 UTC
- system-ondemand-jvbnl (node-2-218) at 2026-11-07 12:32 UTC
- system-ondemand-db9bj (node-2-135) at 2026-11-08 06:28 UTC
- default-zj4kx (spot node node-1-62) at 2026-11-25 05:17 UTC

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 10 of 10 Ready |
| Pods | 151 running, 0 pending, 0 failed |
| Namespaces | 25, 8 production |
| Components | 23: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics and log stores | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## Coming up

| When | What | Source |
|---|---|---|
| passed on 2026-10-24 | NodeClaim default-n44bh (node node-1-139) passed its 720h expireAfter; Karpenter cannot replace it while the do-not-disrupt pod runs there (problem 1). | objects/nodeclaims.karpenter.sh.json |
| 2026-11-07 12:31 UTC | NodeClaim system-ondemand-mxf5q (node node-1-241) reaches its 720h expireAfter; Karpenter replaces the node and evicts its pods. | objects/nodeclaims.karpenter.sh.json |
| 2026-11-07 12:32 UTC | NodeClaim system-ondemand-jvbnl (node node-2-218) reaches its 720h expireAfter. | objects/nodeclaims.karpenter.sh.json |
| 2026-11-08 06:28 UTC | NodeClaim system-ondemand-db9bj (node node-2-135) reaches its 720h expireAfter. | objects/nodeclaims.karpenter.sh.json |
| 2026-11-25 05:17 UTC | NodeClaim default-zj4kx (spot node node-1-62) reaches its 720h expireAfter. | objects/nodeclaims.karpenter.sh.json |
| passed on 2026-02-28 | Upstream end of life of Kubernetes 1.32; the EKS cluster is on extended support. | inventory.json |

## 1. Prod pods stuck on one spot node

**What is happening.** Spot node node-1-139 has run since 2026-09-24. It holds 20 of the 44 prod pods, from 15 prod workloads. Since 2026-10-06, Karpenter has refused to drain, consolidate or expire it, and it passed its 720h expireAfter on 2026-10-24.

If AWS takes the instance back, four prod Deployments lose every replica at once. The other app nodes have no room for the pods. App nodes are the workload-type=app nodes, the only ones prod Deployments may run on.

- Affected:
  - node-1-139: Karpenter reported 21327 times since 2026-10-06 that it cannot disrupt the node, naming the do-not-disrupt pod prod-app-m/app-m-admin
  - prod-app-o/app-o-ai: 3 of 3 pods on the node, no spread rule, no PodDisruptionBudget
  - prod-app-o/app-o-backend: 2 of 2 on the node, no spread rule, no PodDisruptionBudget
  - prod-app-r/app-r: 2 of 2 on the node, no spread rule, PodDisruptionBudget minAvailable 1
  - prod-app-l-backend/app-l-frontend: 2 of 2 on the node despite a preferred podAntiAffinity, PodDisruptionBudget minAvailable 1
  - six single-replica prod services with their only pod on the node and no PodDisruptionBudget: app-m-admin, app-o-admin, app-o-frontend, app-p-backend, app-n-admin-frontend, app-s-backend
- Checked and healthy:
  - No other pod and no node carries do-not-disrupt.
  - No pod on the node uses a PersistentVolumeClaim.
  - Karpenter has an interruption queue, my-cluster-karpenter.
  - No spot interruption of this node shows in the events. The node terminations on 2026-11-05 were consolidation and emptiness.
- Changed for another reason: app nodes node-2-59 and node-2-64. Karpenter created them on 2026-11-05 at 07:37 and 07:54 UTC for pending pods, while it consolidated five short-lived spot nodes.
- Not checked:
  - Why do-not-disrupt was added to app-m-admin. The git history of acme was not read.
  - How often AWS reclaims r8gd.xlarge spot capacity in us-east-1a.

**Why.** The app-m-admin Helm chart puts `karpenter.sh/do-not-disrupt: true` on its only pod, which runs on this node. No prod Deployment has a spread rule, so new pods and replicas keep landing on a node Karpenter cannot touch. Confirmed.

**Suggested fix.**

① Confirm that app-m-admin is the only thing blocking the node.

```
kubectl get events -A --field-selector reason=DisruptionBlocked -o custom-columns=OBJ:.involvedObject.name,COUNT:.count,MSG:.message | grep -v 'blocking budget'
```

Then, in a checkout of acme, find where the annotation is set.

```
grep -rn 'do-not-disrupt' apps/prod/app-m
```

Both commands only read.

Check: the events name only prod-app-m/app-m-admin for node-1-139, and grep shows the file that sets the annotation. The events command sees only the last hour of events, and grep sees only apps/prod/app-m.

② In acme, add a hostname spread rule to four pod templates: app-r, app-o-ai, app-o-backend and app-l-frontend. Use each Deployment's own selector labels. This example is for app-o-ai.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app.kubernetes.io/instance: app-o-prod
        app.kubernetes.io/name: ai
```

Argo CD syncs each application, and each Deployment rolls out new pods. The scheduler then prefers nodes that hold fewer pods of the same Deployment.

Risks:

- Each Deployment restarts all its pods once. app-r and app-l-frontend roll with maxSurge 1 and maxUnavailable 0, and they have readiness probes.
- app-o-ai and app-o-backend have no readiness probe. Kubernetes counts a new pod ready as soon as its container starts and stops an old pod right away. Requests can fail while a new pod is still starting.
- Because of that, roll these two at a quiet hour, or add a readinessProbe in the same commit.
- Each new app-o-ai pod requests 2Gi of memory, and the other app nodes have 8.61 GB free in total. Karpenter may have to add a node, and a new pod stays Pending until the node is up.
- ScheduleAnyway is only a preference, so pods can still land on node-1-139.
- Nobody has confirmed that the charts accept topologySpreadConstraints as a value.
- Argo CD selfHeal reverts kubectl changes, so make this change in git.

Check: this command shows the app-o-ai pods on more than one node.

```
kubectl get pods -n prod-app-o -l app.kubernetes.io/instance=app-o-prod,app.kubernetes.io/name=ai -o wide
```

Run the same for app-o-backend, app-r and app-l-frontend, each with its own selector. If any of them still runs entirely on node-1-139, the spread did not take.

③ Do this step only when two things are true. Step ② has spread all four Deployments over more than one node, and the app-m-admin owners have said why the annotation is there. Then remove the annotation from the app-m-admin pod template in acme apps/prod/app-m, at a quiet hour. Delete this line:

```
karpenter.sh/do-not-disrupt: "true"
```

Argo CD syncs, and app-m-admin rolls with maxSurge 1 and maxUnavailable 0. The new pod is up before the old one stops. After that, nothing blocks Karpenter. The node is already past expireAfter, so Karpenter can drain and replace it soon, at a time it chooses.

Risks:

- The drain evicts 33 pods: 20 prod, 12 dev and external-secrets. external-secrets has one replica, so ExternalSecret syncing stops until it runs elsewhere.
- Six single-replica prod services stop until their pod runs elsewhere:
  - app-m-admin
  - app-o-admin
  - app-o-frontend
  - app-p-backend, which uses Recreate and requests 1Gi
  - app-n-admin-frontend
  - app-s-backend
- Any app-o-ai and app-o-backend pods still on the node are evicted together. Their replacements get traffic before the app is ready.
- PodDisruptionBudgets with minAvailable 1 slow the eviction of these Deployments:
  - app-r
  - app-l-frontend
  - app-l-backend
  - app-l-embedding-server
  - app-m-api, app-m-backend and app-m-frontend
- The other app nodes cannot hold these pods, so Karpenter must launch a node first.
- Nobody has confirmed that Karpenter 0.37 starts the replacement node before it drains. Karpenter 0.37 is also not documented for Kubernetes 1.32.

Check: `kubectl get nodeclaims` shows default-n44bh replaced by a new claim. After the replacement, this command returns nothing.

```
kubectl get pods -A -o wide --field-selector status.phase=Pending
```

**Rollback.** Revert the commits of steps ② and ③, and Argo CD restores the earlier pod templates. The node replacement that step ③ allows cannot be undone, and there is no need to undo it.

**Why this happens.**

- Principle: Two replicas only help if they can fail separately. Without a spread rule, the scheduler packs pods onto whichever node has room, and Karpenter consolidation gathers them further. A do-not-disrupt pod keeps its node from being consolidated or expired, so that node keeps collecting new pods.
- Case: At Moonlight, Kubernetes sometimes scheduled all three website pods on the same node. From January 18 to 22, nodes hit 100% CPU and kernel-panicked, and rescheduling the crashed pods made it worse. They then added anti-affinity rules to all major deployments. Here, three app-o-ai pods and two pods each of app-r, app-o-backend and app-l-frontend share node-1-139.
- Read: the Kubernetes documentation, Pod Topology Spread Constraints. The Karpenter documentation, Disruption.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Prod pods on node-1-139 | 20 of 44 | summary.json |
| DisruptionBlocked events, 2026-10-06 to 2026-11-05 | 21327 | events.json |
| NodeClaim default-n44bh created, pool expireAfter 720h | 2026-09-24T01:01:07Z | objects/nodeclaims.karpenter.sh.json |
| CPU if the node is lost, 32 pods: needed vs free | 3.3 vs 1.62 cores | summary.json |
| Memory if the node is lost, 32 pods: needed vs free | 18.62 vs 8.61 GB | summary.json |
| Prod Deployments with every replica on the node | 4 | findings-draft.json |

## 2. Four prod ALB health checks failing

**What is happening.** Six ALB target groups have 0 healthy targets, four of them prod, as in the 2026-10-27 run. Users are still served. When every target is unhealthy, the ALB "fails open" and sends traffic to all of them. A dead or hung pod still gets requests, because the health check filters nothing.

- Affected: every check asks for / and expects 200.
  - prod-app-l-backend/app-l-backend: 0 of 2 healthy, both answer 404
  - prod-app-q/app-q-backend: 0 of 1 healthy, answers 404
  - prod-app-o/app-o-frontend: 0 of 1 healthy, answers 307
  - prod-app-n/app-n-frontend: 0 of 1 healthy, answers 307
  - dev-app-n/app-n-frontend and dev-app-t/app-t-backend: answer 307 and 404
- Checked and healthy:
  - app-q-ai, app-q-studio and app-q-web use /health and are not unhealthy.
  - The app-p-backend target group uses /healthz and is no longer unhealthy.
- Changed for another reason: none
- Not checked:
  - Request counts and 5xx per target group for the four prod services.
  - What /health answers when the ALB calls it rather than the kubelet.
  - Whether any target was actually dead while it got traffic.

**Why.** These six Ingresses set no `alb.ingress.kubernetes.io/healthcheck-path`, so the ALB checks / and expects 200. The backends answer 404, and the frontends redirect with 307. Confirmed.

**Suggested fix.**

① Read the health of one target group.

```
aws elbv2 describe-target-health --target-group-arn "$(aws elbv2 describe-target-groups --names k8s-app-svc-8c88bb317a --query 'TargetGroups[0].TargetGroupArn' --output text)"
```

This only reads.

Check: each target shows State unhealthy with Target.ResponseCodeMismatch. The command covers one target group. Run it with the other names to see the rest.

② In acme, set the health-check path of the app-q-backend and app-l-backend Ingresses to /health. Their readiness probes already use that path on the same port.

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/healthcheck-path: /health
```

Argo CD syncs the Ingress, and the AWS Load Balancer Controller changes the target group's health check. Targets turn healthy after two passing checks 15 seconds apart. Pods do not restart.

Risks:

- All 40 Ingresses share the group acme-prod-lb. That includes argocd-server, Grafana, vmauth, kafka-ui, redis-insight and the dev Ingresses.
- The controller reconciles the whole group together. A malformed annotation may hold back changes to all of them. This is unverified.
- If /health answers anything but 200, the targets stay unhealthy and the ALB keeps failing open, as it does today.
- Argo CD selfHeal reverts kubectl changes, so make this change in git.

Check: the step ① command shows State healthy for every target of k8s-app-svc-bb495c72c8 and k8s-app-svc-8c88bb317a.

③ Do this step once the owners of the two frontends say which path answers 200, or that a redirect is fine. Then, for app-o-frontend and app-n-frontend, set healthcheck-path to that path. To accept the 307 instead, widen the success codes.

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/success-codes: 200-399
```

The controller changes the target group's matcher, and the targets turn healthy after two checks. Pods do not restart.

Risks:

- With 200-399, a broken app still counts as healthy as long as it redirects.
- Both frontends run one replica with no readiness probe. Even a correct health check can only move traffic when there is somewhere else to send it.
- The same group-wide reconcile risk applies as in step ②.

Check: describe-target-health on k8s-app-svc-032c25d752 and k8s-app-svc-36f816b829 shows State healthy.

**Rollback.** Each step is an Ingress annotation in git. Revert the commit, and the health check goes back to /. Nothing restarts.

**Why this happens.**

- Principle: The ALB sends traffic only to targets its own health check marks healthy. When all targets are unhealthy, it sends traffic to all of them. The result is not an outage but a check that filters nothing. The check runs apart from Kubernetes readiness, so a pod can be Ready and still fail it.
- Read: the AWS Load Balancer Controller documentation, Ingress annotations. The Elastic Load Balancing documentation, Health checks for Application Load Balancer target groups.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Healthy targets, prod-app-l-backend/app-l-backend | 0 of 2 | summary.json |
| Healthy targets, prod-app-q/app-q-backend | 0 of 1 | summary.json |
| Healthy targets, prod-app-o/app-o-frontend | 0 of 1 | summary.json |
| Healthy targets, prod-app-n/app-n-frontend | 0 of 1 | summary.json |
| Health check path and matcher | /, 200 | summary.json |
| healthcheck-path annotation on the six Ingresses | none | objects/ingresses.networking.k8s.io.json |

## 3. app-q-ai OOM kills, no OOM alert

**What is happening.** In the 7 days before collection, three app-q-ai pods were OOM-killed against their 768Mi memory limit. They all came from the 2026-11-02 releases. The service runs one replica, so each kill stopped it until the container came back.

This has stopped for now. The pod of the 2026-11-04 release has run about 28 hours without a restart, at a working-set p95 of about 493 MiB. No alert fires on an OOM kill.

- Affected: prod-app-q/app-q-ai. Three pods ended OOMKilled, with 13 restarts among them:
  - app-q-ai-577d8cbd67-xvh58: 9 restarts
  - app-q-ai-59dcc49fb6-mwj6t: 2 restarts
  - app-q-ai-5df68778bf-gz2w8: 2 restarts
  
  13 is an upper bound, because a probe failure also restarts a container.

- Checked and healthy:
  - The current pod app-q-ai-59b948c9b5-6tchs has 0 restarts.
  - The Deployment reports 1 of 1 replica available.
- Changed for another reason: app-q-ai itself, through Argo CD rollouts from acme. It got ten new ReplicaSets between 2026-10-27 and 2026-11-04, revisions 27 to 36, each with a new image.
- Not checked:
  - The kernel OOM log of the nodes.
  - Memory peaks of the replaced pods. Their series were not kept per pod.
  - How many requests failed while the pod restarted.

**Why.** In the 2026-11-02 releases, the container needed more than its 768Mi limit. Likely: the OOM-killed pods belong to ReplicaSets 577d8cbd67, 59dcc49fb6 and 5df68778bf, all created on 2026-11-02. It is unknown whether a leak in those images or the load at the time caused it.

**Suggested fix.**

① Watch the current pod's memory peak against its limit.

```
max_over_time(container_memory_working_set_bytes{namespace="prod-app-q",container="ai"}[24h]) / (768*1024*1024)
```

Also watch its restart count.

```
kubectl get pods -n prod-app-q -l app.kubernetes.io/name=ai
```

Both only read.

Check: the ratio stays well under 1, and RESTARTS stays 0. This sees only the current pod, not the kernel log.

② If the 24-hour peak passes 90% of the limit, or another OOM kill appears, raise the limit. In acme apps/prod/app-q, set limits.memory to 1Gi and keep the request at 256Mi.

```yaml
resources:
  limits:
    cpu: "1"
    memory: 1Gi
  requests:
    cpu: 100m
    memory: 256Mi
```

Argo CD syncs, and the Deployment rolls out one new pod.

Risks:

- The rollout uses maxSurge 1 and maxUnavailable 0, so the new pod starts before the old one stops.
- The request stays the same, so the pod lands on an app node as before. That node can become more overcommitted.
- Argo CD selfHeal reverts kubectl changes, so make this change in git.

Check: this prints 1Gi, and the pod is Ready.

```
kubectl get deploy -n prod-app-q app-q-ai -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'
```

③ Add an alert on any OOM kill. Apply it as a PrometheusRule in monitoring, with the release label Prometheus selects.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: oomkill-alerts
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  groups:
    - name: oomkill
      rules:
        - alert: ContainerOOMKilled
          expr: (increase(kube_pod_container_status_restarts_total[15m]) > 0) and on (namespace, pod, container) (kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1)
          labels:
            severity: warning
          annotations:
            summary: "{{ $labels.namespace }}/{{ $labels.pod }} {{ $labels.container }} was OOM-killed"
```

The Prometheus operator loads the rule. When a container restarts after an OOM kill, the alert goes to Alertmanager.

Risks:

- Nothing restarts.
- Where Alertmanager sends warning alerts was not read, so the alert may reach no one.
- The other custom rules in monitoring were applied with kubectl, and Argo CD does not own them. Nothing reverts this rule.

Check: ContainerOOMKilled appears under Status > Rules in Prometheus.

**Rollback.** To undo the limit, revert the commit. To remove the alert rule, run this. Nothing is lost.

```
kubectl delete prometheusrule -n monitoring oomkill-alerts
```

**Why this happens.**

- Principle: A workload that rolls out several times a day loses the OOM history of its old pods. If you look only at the live pod, you miss the repeated kills. Repeated OOM kills across one workload's pods mean the limit is too small or there is a leak, and requests drop between restarts.
- Read: the Kubernetes documentation, Resource Management for Pods and Containers.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Pods ended by OOM kill, 7 days | 3 | summary.json |
| Restarts in those pods, upper bound | 13 | summary.json |
| Memory limit and request | 768Mi, 256Mi | objects/deployments.json |
| ReplicaSets of the killed pods | created 2026-11-02 | objects/replicasets.apps.json |
| Working-set p95, current pod | 516747264 bytes | metrics/memory_p95_7d_bytes.json |
| Start of the current pod | 2026-11-04T12:23:49Z | objects/pods.json |

## Since the previous daily run

daily run of 2026-10-27T15-58-44

Work the previous report asked for: none

**Appeared.**

- The cluster no longer survives the loss of its largest node: the 32 pods that may only run on the app nodes would need 3.3 cores and 18.62 GB on the other app nodes, which have 1.62 cores and 8.61 GB free.
- prod-app-q/app-q-ai: 3 pods ended by OOM kill in 7 days, 13 restarts in those pods.
- argocd/argocd-application-controller-0 was OOM-killed again on 2026-10-30; its restart count went from 41 to 42.
- Subnet acme-vpc-eks-private-us-east-1c has 61 of 251 IP addresses free.
- Root disk of node <ip> is 79% full.
- prod-app-l-backend/app-l-file-worker and app-l-graph-worker had a pod not ready for about 180 and 160 minutes in 24 hours.
- Ingress p95 latency 2.32 s on app-q-ai.my-cluster and 2.51 s on monitor.my-cluster.

**Went away.**

- No FreeDiskSpaceFailed events any more.
- The KubePodNotReady alerts that had been firing for days in dev-app-o, prod-app-r, prod-app-l-backend and app-s-prod stopped.
- Subnet acme-vpc-eks-private-us-east-1a is no longer short of IP addresses.
- The ALB target group of prod-app-p/app-p-backend no longer reports unhealthy targets.
- The share of prod pods on node node-1-139 went from 62% (26 of 42) to 45% (20 of 44).

**Changed because the checks changed, not the cluster.**

- none

## Serious, not today

- No backup of any kind: no backup tool, no backup CronJob that ran in 7 days, no VolumeSnapshot. This waits for a decision on what to back up.
- No SLO and no alert on a user symptom: 157 alert rules, none on 5xx or latency, none on scheduling failure or VPC CNI IP exhaustion.
- Kubernetes 1.32 is past its upstream end of life on 2026-02-28, and the EKS cluster runs on extended support.
- Karpenter 0.37.0 is documented for Kubernetes 1.23 to 1.30, but the cluster runs 1.32. Karpenter logged the unsupported version once.
- The Karpenter EC2NodeClass default still uses Amazon Linux 2 with an AMI that is not pinned. Nodes run a mix of AL2 and AL2023.
- The EKS API endpoint is public and open to 0.0.0.0/0.
- middleware/kafka-controller-0-external is an internet-facing load balancer, and its security group opens port 9094 to 0.0.0.0/0.
- prod-app-q, prod-app-p and app-s-prod each have a NetworkPolicy. Network policy enforcement is off in the VPC CNI, so none of them applies.
- prod-app-l-backend/tts-proxy mounts /dev/net/tun from the host and adds NET_ADMIN, and its containers may run as root.
- Alertmanager and Loki keep their data on emptyDir with one replica, so a rescheduled pod starts empty. Loki was also OOM-killed on 2026-10-25.
- Kubernetes events are not kept anywhere beyond the API server's own short window.
- argocd-application-controller, which syncs every prod application, was OOM-killed on 2026-10-30. It has 42 restarts in total.
- Prometheus is CPU-throttled 26% of the time over 24 hours and uses 67% of its 1536Mi memory limit. It was OOM-killed on 2026-10-06.
- dev-app-t/data-app-t-mysql-0 is 90% full, at 9.7 GB.
- 194 FailedScheduling events since 2026-10-25, the latest around 07:55 UTC on 2026-11-05 while Karpenter replaced app nodes. This is likely the same room shortage as problem 1.

7 more are in section 2 of report-details.md.

## What this run could not see

- Inside the nodes: disk, kernel OOM log and kubelet settings. The SSM document kubegap-node-read is outdated. Run `kubegap setup --context my-cluster --install-ssm-document`, then `/kubegap full`.
- Nodes node-1-117 and node-2-60 are not registered in SSM, so nothing reads them from the node side. Register them with an instance profile that has AmazonSSMManagedInstanceCore.
- Node OS, EKS control-plane logs, ECR, cost, add-on versions and backup plans. A daily run does not read them. Run `/kubegap full`.
- The Grafana datasource and dashboard lists, because there is no Grafana token. Create a Viewer service-account token in Grafana and add `grafana_api_token` to the config file.
- Which path of the prod-app-o and prod-app-n frontends answers 200, and what /health answers to the ALB. Ask the owning teams, or call the path from inside the VPC.

## Numbers

| Severity | fail | warn | vs. previous daily run |
|---|---|---|---|
| critical | 1 | 3 | fail 0, warn +1 |
| high | 27 | 20 | fail -3, warn +2 |
| medium | 99 | 134 | fail +12, warn -7 |
| low | 8 | 134 | fail -2, warn +1 |

Checks behind each problem:

- problem 1: `resilience.n-plus-one.cluster`, `resilience.prod-concentration.node-1-139`, `resilience.replicas-same-node.prod-app-r/deployment/app-r`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend`
- problem 2: `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend`, `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend`, `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend`, `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend`
- problem 3: `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai`, `observability.failure-mode-uncovered.OOMKill`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · snapshot `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`

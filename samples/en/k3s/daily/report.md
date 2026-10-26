# default (k3s, nodes node-a and node-b) — daily audit, 2026-10-26 16:18 KST

This cluster is a two-node k3s installation reached through the `default` context, server v1.33.5+k3s1, profile lab, with 26 namespaces of which 7 are production. Nothing is on fire right now. The one thing that changed since the 15:30 KST daily run is that the HorizontalPodAutoscaler of `app-f-prod/app-f-api-server` scaled the Deployment from 2 to 5 replicas at 16:11 and 16:14 KST, which brought back the CPU throttling and the N+1 shortfall that the 14:43 report had described and that disappeared only because the previous burst ended. The rubric moved from 0.1.49 to 0.1.50, and its only visible effect is that the profile is now called `k3s` instead of `small k3s cluster`. The last full run was today at 15:32 KST, so a full run is not due.

## The 3 problems to work on

### 1. `app-f-prod/app-f-api-server` scaled to 5 replicas again, the new pods are throttled up to 73%, and the cluster no longer survives losing `node-b`
**Problem.** The `app-f-api-server` Deployment in `app-f-prod` is the API behind the hosts `app-f-api-prod.acme.com`, `example-k.kr` and `www.example-k.kr`. Its HPA scaled it from 2 to 4 replicas at 16:11:55 KST and to 5 at 16:14:40 KST because CPU use went above 60% of the 100m request. Every new pod lands on `node-a`, the only node the Deployment may use, and the 500m CPU limit stalls each of them for half or more of its CPU periods while it starts, so a pod needs about 91 seconds to become Ready. With 5 replicas the CPU requests of the whole cluster exceed what `node-a` alone can hold, so if `node-b` failed now some pods would not restart. This is the third time today this cycle has run, and the limit removal proposed at 14:43 has not been done.

**Evidence.** Throttling ratio over 5 minutes is 0.733 for pod `app-f-api-server-5d6b56f78b-4rbzx`, 0.543 for `grwbw` and 0.461 for `vh2ct`, from `metrics/cpu_throttle_ratio_5m.json`. The two pods that existed before the burst are at 0.217 and 0.141 in the same file. HPA `app-f-api-server` has min 2, max 5, current 5, desired 5, current CPU utilization 1%, memory 46%, lastScaleTime 16:14:40 KST, from `objects/horizontalpodautoscalers.autoscaling.json`. SuccessfulRescale events read "New size: 4" and "New size: 5", both "cpu resource utilization (percentage of request) above target", from `events.json`. Pod `4rbzx` was created 16:14:40 and reached Ready at 16:16:11 KST, from `objects/pods.json`. N+1: CPU requests 6.31 cores against 6.0 cores allocatable without `node-b`, 6.01 cores at 15:30, from `summary.json resilience.n_plus_one`. Resources: requests cpu 100m and memory 1088Mi, limits cpu 500m and memory 2720Mi, from `objects/deployments.json`. `app-f-prod` is the cluster's only burst tenant with a 7-day burst ratio of 21.4, CPU max 0.712 cores against a median of 0.033, from `summary.json tenancy.noisy`.

**Cause.** Confirmed for the mechanism: the HPA divides CPU use by the 100m request, so a short spike above 60m per pod triggers a scale-out. Each new pod burns CPU while it starts, the 500m limit throttles that startup, and the pod stays not Ready for about a minute and a half; once the spike passes the HPA scales back after its 300-second stabilization window. Likely: the spike is a real request burst, because the trigger is CPU this time and not memory as at 13:35 KST. No request, error or latency metric exists for this service, so whether users noticed cannot be read from the cluster.

**Action.** ① Remove the CPU limit of container `app` and keep the 100m request. The effect is no throttling during scale-out and a faster startup, with no change to scheduling because requests stay. Takes 10 minutes through Git and Argo CD. ② Raise the readiness and liveness probe `timeoutSeconds` from 1 to 3 and give the liveness probe a path that does not share `/healthcheck` with readiness, so a slow start is not mistaken for a dead process. Takes 20 minutes. ③ Decide the HPA target with a week of data: if `hpa_desired_changes_7d` stays above 20, raise the CPU target to 80% or the request to 200m, so a short spike does not add three pods that each need 100m of N+1 headroom. Takes 30 minutes of reading. ④ Reduce requests of the 18 over-provisioned containers reported under `resources.cpu-request-overprovisioned`, but not the `app-f-api-server` request, because the HPA scales on it. Takes 1 hour.
```yaml
# app-f-prod/deployment/app-f-api-server, container app
resources:
  requests: {cpu: 100m, memory: 1088Mi}
  limits: {memory: 2720Mi}   # cpu limit removed
```

**Why this happens.**
- Principle: The kernel enforces a CPU limit as a quota per 100 ms period. A process that uses its quota early in the period stalls for the rest of it, so average CPU looks low while startup and latency get slower. The HPA scales on use divided by the request, not the limit, so a small request with a low limit gives throttling and scale-out at the same time, and each extra pod consumes N+1 headroom through its request.
- Cases: Buffer 2020 and Omio 2020, both recorded in the cpu-throttling check definition, found throttling-induced latency on services with low average CPU and removed CPU limits.
- Read next: "CFS bandwidth control (kernel sched-bwc)", "Kubernetes docs: HorizontalPodAutoscaler algorithm details", "Kubernetes docs: Resource Management for Pods and Containers".

Evidence checks: `resources.cpu-throttling.app-f-prod/deploy/app-f-api-server:app` (recurred), `resilience.n-plus-one.cluster` (recurred), `traffic.pod-not-ready.app-f-prod/app-f-api-server` (judged pass, startup only), `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server`, `resilience.single-eligible-node.app-f-prod/deployment/app-f-api-server`, `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-api-server:app`, `resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-api-server:app`, `observability.golden-signals-missing.app-f-prod/app-f-api-server-ingress`

### 2. `app-c-prod/app-c-coturn` has crashed 7,894 times and nobody has read the reason yet
**Problem.** The TURN server of the app-c app, which relays WebRTC calls across NAT, is in CrashLoopBackOff on node `node-a` in namespace `app-c-prod`. The Deployment has 0 of 1 replicas available, so app-c calls that need relaying fail. It has been problem 1 or 2 in every report since 2026-10-25 and no action has started.

**Evidence.** Restarts 7,894, up 9 since 15:30 KST, from `objects/pods.json`. BackOff warning events 7,166 to 7,371, 205 more in 48 minutes, all on this one pod, from `diff.json events.changed`. Last termination 16:16:15 KST with exit code 255, started and finished in the same second, from `objects/pods.json` lastState. Deployment `app-c-coturn` desired 1, available 0, from `summary.json objects.deployments.unavailable`. Image `coturn/coturn:latest`, CPU limit 200m, memory limit 128Mi, no probes, from `objects/deployments.json`.

**Cause.** Likely: a process that exits with 255 within one second fails at startup, most often a configuration error or a port bind failure. Container logs are outside kubegap's collection, so the exact message is unknown. The `:latest` tag means the binary may have changed at the node reboot of 2026-10-25 without any manifest change.

**Action.** ① Read the last crash message. Takes 10 minutes.
```bash
kubectl -n app-c-prod logs app-c-coturn-549854dfcb-jgp4h -c coturn --previous | tail -50
```
② If it is a port conflict, find the owner of 3478 on `node-a` with `ss -lunp | grep 3478`. Takes 5 minutes. ③ Fix the arguments, pin the image tag to a digest or version, and add a tcpSocket probe on 3478. Takes 30 minutes. The effect is working app-c calls, about 260 fewer BackOff events per hour, and the two always-firing alerts KubePodCrashLooping and KubeDeploymentReplicasMismatch going quiet. ④ If it cannot be fixed today, scaling the Deployment to 0 stops the event noise; that is your decision.

**Why this happens.**
- Principle: A restart has one of three causes: OOMKilled, a failed liveness probe, or the application exiting on its own. Exit 255 within one second with no probes is the third, so the only next step is the previous container's log. Raising limits or changing probes does not help here.
- Cases: No public case recorded for this check.
- Read next: "Kubernetes docs: Debug Running Pods, kubectl logs --previous", "CrashLoopBackOff backoff timing (kubelet)", "Kubernetes docs: Images, image tags versus digests".

Evidence checks: `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `events.tracked-warning-reasons.BackOff`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `observability.alerts-always-firing.KubePodCrashLooping`, `observability.alerts-always-firing.KubeDeploymentReplicasMismatch`, `resilience.single-replica-in-prod.app-c-prod/app-c-coturn`

### 3. The Argo CD repo-server liveness probe timed out again, this time while kubegap was polling it, and its metrics port still answers 502
**Problem.** `argocd/argocd-repo-server` renders the manifests of all Argo CD applications from Git. Its liveness probe on `/healthz?full=true` failed once more at 16:18:42 KST, the 33rd time since 2026-10-25, and this failure happened 31 seconds after kubegap started collecting. Three consecutive failures would make the kubelet restart the pod and pause synchronization of the 7 applications. In the same minute the API server proxy to port 8084 returned 502 to kubegap's metrics request, as it has in every run today.

**Evidence.** Unhealthy occurrences 32 to 33, last at 16:18:42 KST, message "Liveness probe failed: Get http://<pod IP>:8084/healthz?full=true: context deadline exceeded", from `events.json`. The collection window was 16:18:11 to 16:19:35 KST, from `run.log`. Probe: liveness `/healthz?full=true`, timeout 5 seconds, from `objects/deployments.json`. Collection failure `argocd.repo-server-metrics` with "proxy error while dialing <pod IP>:8084, code 502", from `summary.json run.failed`. Restarts 1, Ready since 2026-10-25 13:24 KST, from `objects/pods.json`.

**Cause.** Likely: the `full=true` health check includes repository access and sometimes exceeds the 5-second probe timeout. The coincidence with kubegap's collection suggests that any extra request on port 8084, including the metrics scrape kubegap attempts, slows the health handler, which would also explain why the proxy gets 502. This is not confirmed; a single overlap is not proof.

**Action.** ① Watch whether failures cluster around scrape or sync times. Takes 15 minutes.
```bash
kubectl -n argocd get events --field-selector reason=Unhealthy -w
```
② Raise the liveness `timeoutSeconds` to 15 and `failureThreshold` to 5 in the Argo CD Helm values or kustomize overlay. The effect is no unnecessary restart and no 503 in the repo-server log. Takes 20 minutes. ③ Check why port 8084 answers 502 through the API server proxy, with a port-forward and `curl -s localhost:8084/metrics | head`. Takes 10 minutes.

**Why this happens.**
- Principle: A liveness probe should answer only "is the process dead". When the path also checks dependencies, a short dependency delay makes the kubelet kill a healthy pod, and the restarted pod meets the same dependency again. Dependency checks belong in readiness, where a failure removes traffic instead of restarting.
- Cases: No public case recorded for this check.
- Read next: "Kubernetes docs: Configure Liveness, Readiness and Startup Probes", "Argo CD repo-server healthz full=true", "Google SRE Workbook ch. 10, Alerting on SLOs: cause-based versus symptom-based".

Evidence checks: `events.tracked-warning-reasons.Unhealthy`, `traffic.pod-not-ready.argocd/argocd-repo-server`, `controlplane.apiserver-5xx.cluster`

Quick fix outside the list: the three Postgres StatefulSets `app-d-prod/app-d-postgres`, `app-d-prod/app-d-postgres-mx` and `app-g-prod/app-g-postgres` still have a 150m CPU limit with a 7-day p95 near 5 millicores, from `objects/statefulsets.json`. Their throttling values moved between 7.9% and 10.2% this run, so the findings flip between resolved and new every run. Removing the limit takes 5 minutes each and ends the flapping.

## Since the previous daily run (2026-10-26 15:30 KST)
In the 48 minutes between the runs one object changed: the Deployment `app-f-prod/app-f-api-server` went from generation 31588 to 31590 because its HPA scaled it from 2 to 4 and then to 5 on CPU utilization above target, and the GitHub Actions runner pod in `arc-systems` was replaced as part of its normal cycle. The scale-out produced all three cluster-side new findings: CPU throttling of the new pods, the N+1 shortfall of 0.31 cores, and a readiness ratio finding that I judged pass because it measures 91 seconds of startup. Three CPU throttling findings on `app-d-postgres`, `app-g-postgres` and `app-i-web` show as resolved and one on `app-d-postgres-mx` as new, with no object change behind any of them; their values sit between 7.9% and 10.2% around the 10% threshold. The rubric moved to 0.1.50 and renamed the profile from `small k3s cluster` to `k3s`; the `cost.small k3s cluster-node-efficiency` finding shown as resolved and `cost.k3s-node-efficiency` shown as new are the same warn/low check under its new id, a criteria change and not a cluster change. `app-c-coturn` added 205 BackOff events and 9 restarts, and the repo-server liveness probe failed once more. 33 critical and high fail items persist unchanged, see details section 2.

Progress on the previous report's problems: (1) read the `app-c-coturn` crash log: not started, restarts 7,885 to 7,894. (2) adjust the `argocd-repo-server` probe: not started, Unhealthy 32 to 33 and the metrics proxy failed again with 502. (3) remove the Postgres CPU limits: not started, all three StatefulSets still show a 150m limit in `objects/statefulsets.json`. The quick fix of that report, removing the `app-f-api-server` CPU limit, is not started and is now problem 1.

## What this run could not see
Daily mode did not evaluate 56 of 345 checks, covering node OS, k3s journals, etcd, scheduler, kubelet, helm, krr, polaris, pluto and kubent; the last full run was today at 15:32 KST. Loki is not installed, so its 5 checks are skipped by design and logs come from Elasticsearch and fluent-bit. No tool is missing. No collection step failed, and 2 of 343 commands failed: the pod-proxy metrics request to `argocd-repo-server` with 502, and the first attempt at the MetalLB speaker metrics on `node-a` through the API server proxy, which timed out before the SSH fallback. The Grafana datasource and dashboard steps were skipped because `config.yaml` has no `grafana_api_token`. The API server 503 rate of 0.004 per second, LIST p99 of 0.949 seconds and PATCH p99 of 0.852 seconds were measured during collection and include kubegap's own LISTs and failed proxy calls, so they are not counted as user impact. Prometheus throttling of 41% was measured in the same window while kubegap sent 164 queries.

## Numbers
| Severity | fail | warn | vs. previous daily run |
|---|---|---|---|
| critical | 1 | 2 | fail 0 · warn 0 |
| high | 32 | 58 | fail +2 · warn −2 |
| medium | 55 | 101 | fail 0 · warn 0 |
| low | 9 | 107 | fail 0 · warn 0 |
| info | 0 | 3 | warn 0 |

The final critical plus high total of 93 is 4 below the first pass of 97: the API server 5xx warning went to info as a collection-time measurement, the Unhealthy event warning went to medium because the only new occurrence is non-production, and two cert-manager restart warnings were judged pass as runtime restarts. `history.csv` keeps the first-pass numbers.

Details, every table and the full first-pass list: [`report-details.md`](report-details.md) · kubegap 0.1.0, rubric 0.1.50 · snapshot `~/.kubegap/snapshots/default/2026-10-26T16-18-11`

# kubegap report details — default (`default`), full mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `llm/facts.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `default` / default (k3s, v1.33.5+k3s1) |
| Run time / mode | 2026-11-05T17:25:17+09:00 / full (collection 292.4 s, 0 steps skipped by mode, 0 failed) |
| Profile | `lab` (detected) |
| kubegap / rubric / signatures | 0.1.2 / 0.1.80 / 1.1.0 |
| Nodes / namespaces / pods / CRDs | 2 (Ready 2) / 26 / 153 / 64 |
| Components (23) | actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, prometheus, prometheus-operator, reloader |
| Metrics store | prometheus 3.7.3 retention 30d / size 0B via port-forward |
| Log store | none (Loki not found) |
| Node access | ssh (k3s: SSH); SSM unregistered 0 |
| Snapshot | `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 2 | 2 | fail +0 · warn +0 |
| high | 28 | 68 | fail +0 · warn +2 |
| medium | 73 | 135 | fail +2 · warn +0 |
| low | 9 | 121 | fail +0 · warn +1 |
| info | 0 | 0 | no previous run of this mode |

Checks 347: evaluated 294, disabled by profile 41, skipped 10, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

| Finding | First pass | Final | Reason |
|---|---|---|---|
| resilience.no-backup.cluster | warn critical | critical | Kept critical although it is a warn: the mitigating signals the check found (7 dump CronJobs, 5 etcd snapshots) were each opened and none leaves node-a or node-b, so the warn's mitigation does not hold (problem 2). |
| observability.no-symptom-alerts.cluster | warn critical | high | Severity rule for absences: a warn is high, because the check found 7 app-metric rules it assumes are symptoms. |
| security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts | fail high | low | The keys are names inside Python scripts; extra/configmap-secret-rhs-class.txt shows TOKEN and OPENAI_API_KEY are environment lookups and client_secret, resource_owner_secret are code expressions, so no literal secret was found. |
| security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts | fail high | low | Same as app-v-scripts: all six matched keys are environment lookups or code expressions (extra/configmap-secret-rhs-class.txt). |
| traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external | fail high | medium | On a small k3s cluster a NodePort is LAN exposure; the probes reached it from the LAN and the tailnet, and internet reachability was not shown. The same applies to app-d-postgres-mx-external, app-d-postgres-vn-external and app-g-postgres-external. |
| resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog | fail medium | pass | lastSuccessfulTime 2026-11-05T08:24:50Z is 27 seconds before collection; the '6.4h ago' comes from the evaluation clock (tool note 1). |
| controlplane.apiserver-5xx.cluster | warn high | low | 0.004 per second of 503 measured while collection ran its LIST and PromQL load; not counted as user impact. |
| controlplane.apiserver-latency.LIST | warn medium | low | LIST p99 0.745 s measured during collection. |
| resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller | warn high | low | Running now; the last termination is one event on 2026-10-28T19:25:01Z shared with cert-manager-cainjector and keda-operator. The event has ended; the same holds for those two. |
| storage.local-path-fs-near-full.cluster | warn high | medium | node-a has 24.3 GiB free and its 7-day trend is -0.48 GiB per day; node-b has 227.4 GiB free, 842 days at its trend. |
| node.disk-usage.<ip>:9100:/ | warn high | medium | Same disk as above: 77% used, shrinking over 7 days, images pruned nightly. |
| tenancy.quota-near-limit.app-i-prod/app-i-prod-quota | fail high | medium | Only the PVC count (2 of 2) is full; it refuses a third PVC and nothing pending needs one. |
| tenancy.ci-shares-prod-nodes.node-a | warn high | medium | Two-node lab cluster: there is no separate node to move the runners to. Same for node-b. |
| security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn | warn high | medium | hostNetwork is how this TURN server exposes its relay port range; part of problem 1. |
| events.tracked-warning-reasons.Unhealthy | warn high | medium | 7 Unhealthy events, all on app-e-api/app-e-postgres-0, a non-production database. |

### 1-2. Aggregates the LLM recounted

| Finding | First pass | Final | Reason |
|---|---|---|---|
| resilience.no-backup.cluster | 7 backup-like CronJobs | 7 local-only, 5 on the source database's node | Lengths of summary.json resilience.backup.local_only (7) and resilience.backup.same_node (5). |
| resilience.prod-db-without-backup-cronjob.cluster | list of 2 | 2 | Length of resilience.backup.prod_db_without_backup_cronjob. |
| observability.alerts-always-firing | 24.0083 notifications | 24 | metrics/am_notifications_1d.json value rounded to whole notifications. |
| resilience.single-eligible-node | 37 warns | 37 workloads | check_results counts.warn of resilience.single-eligible-node; one finding per workload. |
| resilience.backup-same-node | source_db lists every database in the namespace | app-d-postgres-backup dumps only app-d-postgres | The dump command connects to app-d-postgres.app-d-prod.svc only (objects/cronjobs.json); the per-namespace source list is wider than what each job copies (tool note 5). |

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `observability.no-slo.cluster` | critical |  | no SLO tool. Signals: sli/slo recording rules [], burn rate alerts [], slo-labelled rules [] known issue #15 |
| `resilience.n-plus-one.cluster` | critical |  | Allocatable without the largest node node-b (12.0 cores, 30.7GB): CPU 6.0 cores vs total requests 6.17 (short), memory 30.7GB vs 23.9GB (OK). Pods on that node 48 (prod 15). Pods that fit on no other node [{'namespace' … |
| `argocd.prune-manages-namespace-or-crd.cluster` | high | 8 | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/acme-site', 'argocd/application/app-e-api' … |
| `coredns.availability.cluster` | high | 8 | replicas 1, nodes with pods 1 of 2 ({'node-b': 1}), PDB [], spread declared (antiAffinity/topologySpread) True, restarts total 1 |
| `events.tracked-warning-reasons.BackOff` | high | 8 | Container keeps dying and the restart interval grows (CrashLoopBackOff). 193081 occurrences total (4 events, trend over 45 snapshots [124477, 124589, 124978, 125226, 125317, 126950, 127112, 127228, 128098, 128331, 800 … |
| `observability.failure-mode-uncovered.OOMKill` | high |  | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | high |  | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana` | high |  | emptyDir volumes: storage, sc-dashboard-volume, sc-datasources-volume, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus` | high |  | emptyDir volumes: config-out, prometheus-kube-prometheus-stack-prometheus-db, replicas 1 |
| `platform.k3s-datastore-slow.cluster` | high |  | datastore etcd (servers ['node-b']), warn lines in 24h 375 (hit the 200-line cap - there were more): slow apply 191 (max 1160.1ms, over 1s 1), slow fdatasync 1, leader changes 0, request stats 170, DB 594MB |
| `platform.k8s-version-eol.cluster` | high |  | server v1.33.5+k3s1: upstream end of life 2026-06-28, 130 days past |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-backup` | high |  | app-d-prod/app-d-postgres-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b') … |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup` | high |  | app-d-prod/app-d-postgres-vn-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-vn-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b') … |
| `resilience.backup-same-node.app-f-prod/app-f-mysql-backup` | high |  | app-f-prod/app-f-mysql-backup: schedule '50 2 * * *', dump PVCs ['mysql-backup-app-f-mysql-0'] → nodes ['node-b'], hostPath [], source DB [('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-mysql', 'node-b') … |
| `resilience.backup-same-node.app-g-prod/app-g-postgres-backup` | high |  | app-g-prod/app-g-postgres-backup: schedule '0 3 * * *', dump PVCs ['app-g-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-g-prod/statefulset/app-g-postgres', 'node-b')], off-node … |
| `resilience.replicas-same-node.app-d-prod/deployment/app-d` | high |  | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-admin` | high |  | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server` | high |  | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client` | high |  | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under … |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | high |  | 10715 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-05T08:24:01Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-e-api/sts/app-e-minio:minio` | high |  | pod app-e-minio-0: 7d memory working set p95 / limit = 0.98 |
| `security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts` | high |  | app-a-prod/configmap/app-v-scripts: keys ['discord_sales_bot.py:TOKEN', 'discord_sales_bot.py:OPENAI_API_KEY', 'app-v_autopost.py:client_secret', 'app-v_autopost.py:resource_owner_secret'] … |
| `security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts` | high |  | app-d-prod/configmap/app-d-app-v-scripts: keys ['app-d_ga4_digest.py:DISCORD_BOT_TOKEN', 'app-d_ga4_digest.py:token', 'app-d_policy_radar.py:OPENAI_API_KEY', 'app-d_policy_radar.py:DISCORD_BOT_TOKEN' … |
| `storage.local-path-over-capacity.app-a-prod/app-a-postgres-backup-pvc` | high |  | node node-a uses 5862MB / capacity 5120MB (1.14x). workloads ['app-a-prod/app-a-postgres-backup'] |
| `storage.local-path-over-capacity.logging/data-elasticsearch-0` | high |  | node node-b uses 103451MB / capacity 20480MB (5.05x). workloads ['logging/elasticsearch-0'] |
| `tenancy.quota-near-limit.app-i-prod/app-i-prod-quota` | high |  | app-i-prod/app-i-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi' … |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external` | high |  | nodeport app-d-prod/app-d-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external` | high |  | nodeport app-d-prod/app-d-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external` | high |  | nodeport app-d-prod/app-d-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external` | high |  | nodeport app-g-prod/app-g-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |

## 3. Changes since the previous run of this mode

Compared `2026-11-04T22-29-59` → `2026-11-05T17-25-17` (rubric 0.1.76 → 0.1.80).

- **New (3)**: `controlplane.apiserver-5xx.cluster` (warn/high), `coredns.forward-upstream-errors.cluster` (warn/medium), `observability.alert-firing-stale.CPUThrottlingHigh/logging` (warn/medium)
- **Resolved (0)**: none
- **Changed (2)**: `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn` (['warn', 'fail']/['medium', 'medium']), `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog` (['warn', 'fail']/['medium', 'medium'])
- **Rename suspects (0)**: none
- **Objects**: added 7, removed 3, changed 1: `deployments/app-f-prod/app-f-admin` spec.replicas
- **Warning events**: BackOff +5222 (Pod/app-c-prod/app-c-coturn-549854dfcb-jgp4h), Unhealthy +7 (Pod/app-e-api/app-e-postgres-0)

### 3-0. Criteria changes, not cluster changes

These findings appeared, disappeared or changed because the checks did, not the cluster, and they are kept out of the lists above. Taken from `diff.json` `findings.criteria_changes`; the report writes them as a criteria change and never as a tool defect.

- **Checks whose rule changed between the runs (4)**: `logs.signatures.cert-manager.challenge-failed` (new, warn/medium), `logs.signatures.common.too-many-open-files` (new, warn/high), `logs.signatures.metallb.speaker-peer-unreachable` (new, warn/low), `logs.signatures.metallb.speaker-error` (resolved, warn/medium)
- **Persisted (Toil)**: 424 findings present in all 8 runs checked, 428 in 3 or more; top checks: `resilience.single-eligible-node` 37, `observability.golden-signals-missing` 29, `resources.krr-recommendation` 29, `resilience.no-prestop` 22, `resilience.liveness-dependency-path` 21, `resources.cpu-request-overprovisioned` 18, `hygiene.mutable-image-tag` 15, `resilience.single-replica-in-prod` 15

### 3-1. Why things changed

The previous full run was 2026-11-04T22:29:59+09:00, about 19 hours earlier, and it wrote no problems, so nothing is marked done or not done. No node, namespace, component or store changed. The one workload change is app-f-prod/app-f-admin, whose spec.replicas moved three times (generation 889 to 892), the HPA scaling it. Seven objects appeared and three went away: k3s rotated one etcd snapshot (a new one at 2026-11-05T00:00Z replaced the oldest), cert-manager created renewal orders for argocd-tls, app-f-api-prod-tls, kibana-tls and the Grafana certificate, and two ARC runner pods replaced two others. The BackOff count on app-c-coturn grew by 5,222 occurrences and its Pulling count by 223: the crash loop simply continued. Seven Unhealthy events are new, all on app-e-api/app-e-postgres-0. Three findings are new for cluster reasons: apiserver 503s at 0.004 per second measured during collection, one failed CoreDNS upstream health check in the last hour, and an info-level CPUThrottlingHigh on elasticsearch-0. Two findings moved from warn to fail, app-c-coturn's unhealthy condition and the watchdog CronJob's staleness, but both durations were measured against the evaluation clock six hours after collection (tool note 1). Four log findings are new because the signature rules changed with the rubric update from 0.1.76 to 0.1.80, not because the cluster changed. CronJobs were not compared, because the two snapshots store them under different kind names (tool note 3).

## 4. Detail per area

### resources

18 CPU over-request warns and 30 KRR rows; KRR suggests 2.47 cores less CPU request across 58 containers and 3,442 MB more memory, so memory is short rather than long. Database-like containers (Postgres, MySQL, Redis, Qdrant, Elasticsearch) stay as they are: remove CPU limits where throttled, never cut their requests to the p95. app-e-minio sits at 98% of its memory limit (p95 7 days), fluent-bit at 82-84%. Throttled: Prometheus, Elasticsearch, app-e-postgres, fluent-bit.

### scaling

11 HPAs, all CPU-based; 6 never scaled in 15 days, app-f-api-server flaps. 11 serving production Deployments have no HPA, which on a two-node cluster without a node autoscaler matters little.

### observability

161 alert rules, none on a user symptom; 6 alerts fire continuously and 5 warnings reach Discord every 4 hours (problem 3). Prometheus, Alertmanager and Grafana run on emptyDir; Prometheus holds 21.4 GiB over 30 days. ingress-nginx exposes no metrics, so 29 ingress backends have no latency, traffic or error signal. No Loki; logs go to Elasticsearch through fluent-bit.

### traffic

Two ingress-nginx controllers behind MetalLB address <ip>; ingress-nginx 1.14.0 is retired upstream. Four Postgres NodePorts are open on both nodes (problem 5). CoreDNS has one replica on node-b; NXDOMAIN ratio is high and one upstream health check failed in the last hour. app-c-coturn has been not ready all day (problem 1).

### resilience

No dump or snapshot leaves the nodes (problem 2). node-b is the only server and the only node for the production databases; without it the cluster lacks 0.17 cores of requests and has no API. 15 production Deployments run one replica, 37 workloads can land on one node only, 22 lack a preStop hook and 13 database probes time out after 1 second. app-c-coturn crash-loops (problem 1).

### hygiene

15 containers use mutable tags, among them coturn:latest, which caused problem 1; 12 pull pinned tags with Always. Four Failed pods linger in app-a-prod and app-f-prod, the oldest 3,847 hours. Argo CD manages 18 apps; root is OutOfSync and app-c Progressing because of coturn.

### storage

26 local-path volumes, 19 on node-b. Elasticsearch uses 103,451 MB on a 20,480 MB claim and the app-a dump volume 5,862 MB on 5,120 MB; local-path does not enforce claims. All volumes use reclaimPolicy Delete. node-b has 227 GiB free, node-a 24.3 GiB.

### security

No literal secret was found in the app-v-script ConfigMaps (environment lookups); app-y-backend-config in default has secret-like key names and is unmounted. ELASTIC_PASSWORD is a literal env value in logging. No default-deny NetworkPolicy, no Pod Security admission enforced, k3s secrets encryption off, Argo CD admin without SSO. Four databases on NodePorts (problem 5).

### cost

Two owned machines, no cloud bill. CPU p95 use is 0.89 of 18 allocatable cores (4.9%) and requests are 6.51 cores, 7.3 times the use; neither node can be dropped, because node-b is the server and holds the databases.

### tenancy

7 production namespaces share both nodes with CI runners, logging and monitoring; 5 tenant namespaces have no ResourceQuota (arc-systems, app-c-prod, app-d-prod, app-f-prod, app-g-prod) and 3 quotas have no LimitRange. app-f-prod bursts to 22 times its median CPU. No node was CPU-saturated in 7 days, so there was no room for one tenant to starve another.

### node OS

Ubuntu 22.04.5 on both nodes, kernels 5.15.0-198 (node-a) and 5.15.0-185 (node-b); both need a reboot and have 52 pending updates (1 and 7 security). node-b hit the inotify instance limit of 128 during the nightly Jobs. No kubelet reserved resources or memory eviction threshold is set; swap is on for node-b; Docker and containerd both run on node-a. No kernel OOM, I/O or filesystem errors in 24 hours.

### platform

k3s v1.33.5+k3s1, past end of life (problem 4). One server with embedded etcd (594 MB, quota 2,048 MB) logs slow applies every hour, the slowest 1,160 ms, without leader changes. node-b's --server flag points at <ip>, which no node has. k3s certificates have 287 days left.

## 5. Absence list

| Finding | Status | Severity | Why it should exist | Proposal |
|---|---|---|---|---|
| `observability.no-slo.cluster` | fail | critical | Without an SLO there is no definition of "normal", and no basis for deciding which alerts matter or which finding comes first. | Define per-service availability and latency SLOs as recording rules with Sloth or Pyrra. Start with one service that has an Ingress. |
| `resilience.no-backup.cluster` | warn | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |

Expected families missing (inventory): backup, slo.

## 6. Suppressed, tool missing, not collected

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in full mode 0: none
- Skipped or errored 10: `observability.log-volume-change` (skip: summary.logs.loki.volume_change missing), `security.no-secrets-manager` (skip: profile lab does not require family secrets-manager), `scaling.no-node-autoscaler` (skip: profile lab does not require family node-autoscaler), `observability.log-coverage-gap` (skip: summary.logs.loki.coverage missing), `observability.loki-not-ready` (skip: nothing to judge: loki not present), `observability.loki-ingest-discarded` (skip: summary.logs.agents.loki_metrics missing), `observability.promtail-dropped` (skip: summary.logs.agents.promtail missing), `observability.log-error-ratio-high` (skip: summary.logs.loki.namespaces_1h missing), `observability.unstructured-logs` (skip: summary.logs.loki.namespaces_1h missing), `observability.alert-metric-without-dashboard` (skip: nothing to judge: dashboards json not available)
- Judged in part 0 (some targets lacked what the rule needs; those are not judged, not passed): none

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 |  | objects.dump-all (['configmaps', 'namespaces', 'nodes', 'pods', 'services', 'customresourcedefinitions.apiextensions.k8s.io', 'daemonsets.apps', 'deployments.apps', 'statefulsets.apps', 'cronjobs.batch', 'storageclasses.storage.k8s.io']) |
| k3s-platform | 8 |  |  |
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
| kube-proxy | 2 |  |  |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| local-path-provisioner | 1 |  |  |
| metallb | 1 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| reloader | 0 |  | no collect.yaml (collector not implemented) |

374 commands, 292.4 s. Failed steps: 0

Commands that failed inside a step that still succeeded (run.log): 2: `argocd.repo-server-metrics.argocd-repo-server-848dcbb4db-jz8xs` Error from server (ServiceUnavailable): error trying to reach service: proxy error from 127.0.0.1:6443 while dialing …; `metallb.metallb-speaker-metrics.speaker-xfxlv` Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers)

Deprecated-API tools: kubent 28 of 41 Lists answered (13 refused or not served); pluto 119 of 126 Lists answered (7 refused or not served).

### 7-2. Checks evaluated

347 checks: disabled 41, done 294, llm 2, skip 10. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.0, 24 files, 26732 lines scanned (components: alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, fluent-bit, grafana, ingress-nginx, keda, local-path-provisioner, metallb, metrics-server, prometheus, reloader). Unclassified error lines: 403.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| common.too-many-open-files | any | node | high | warn | 32 | 2026-11-05T03:30:04Z , 2026-11-05T04:17:00Z | time="2026-11-05T03:30:04.160019168Z" level=warning msg="error from *cgroupsv2.Manager.EventChan" error="failed to create inotify fd: too many open files" |
| fluent-bit.flush-failed | fluent-bit | observability | medium | warn | 14 | 2026-11-05T07:57:36Z , 2026-11-05T08:25:46Z | [pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:57:36.227818631+09:00 [2026/11/05 07:57:36] [ warn] [engine] failed to flush chunk … |
| fluent-bit.upstream-down | fluent-bit | observability | medium | warn | 11 | 2026-11-05T07:54:47Z , 2026-11-05T08:23:31Z | [pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:54:47.226478840+09:00 [2026/11/05 07:54:47] [error] [input:kubernetes_events:kubernetes_events.1] upstream … |
| cert-manager.challenge-failed | cert-manager | security | medium | warn | 10 | 2026-11-05T02:31:09Z , 2026-11-05T03:35:40Z | [pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.690144851Z E1105 02:31:09.689988       1 sync.go:190] "propagation check … |
| containerd.image-pull-failed | containerd | resilience | medium | warn | 4 | 2026-11-05T07:37:11Z , 2026-11-05T07:37:11Z | E1105 16:37:11.763079    1316 log.go:32] "PullImage from image service failed" err="rpc error: code = Unknown desc = failed to pull and unpack image … |
| kubelet.pod-sync-error | kubelet | resilience | low | warn | 2988 | 2026-11-04T21:34:47Z , 2026-11-05T08:25:20Z | E1105 06:34:47.751559    1316 pod_workers.go:1301] "Error syncing pod, skipping" err="failed to \"StartContainer\" for \"coturn\" with CrashLoopBackOff … |
| k3s.etcd-request-stats | k3s | platform | low | info | 2495 | 2026-11-04T12:27:12Z , 2026-11-05T08:23:24Z | {"level":"warn","ts":"2026-11-04T12:27:12.187120Z","caller":"etcdserver/util.go:170","msg":"apply request took too … |
| metallb.speaker-peer-unreachable | metallb | traffic | low | warn | 487 | 2026-11-05T05:05:40Z , 2026-11-05T08:26:40Z | [pod/speaker-xfxlv/speaker] 2026-11-05T14:35:35.218743637+09:00 {"caller":"speakerlist.go:259","error":"1 error occurred:\n\t* Failed to join … |
| k3s.proxy-websocket-closed | k3s | platform | low | info | 88 | 2026-11-04T03:33:25Z , 2026-11-04T23:25:21Z | E1104 12:33:25.885594  707592 upgradeaware.go:427] Error proxying data from client to backend: websocket: close 1006 (abnormal closure): unexpected EOF |
| cert-manager.orphan-tls-secret | cert-manager | hygiene | low | warn | 64 | 2026-11-04T15:18:56Z , 2026-11-05T00:57:19Z | [pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553816246Z E1104 15:18:56.553660       1 indexers.go:61] "unable to … |
| kubelet.cadvisor-partial | kubelet | node | low | info | 6 | 2026-11-04T21:42:00Z , 2026-11-05T07:17:00Z | E1105 06:42:00.573423    1316 cadvisor_stats_provider.go:525] "Partial failure issuing cadvisor.ContainerInfoV2" err="partial failures … |

| Normalized message | Count | Files |
|---|---|---|
| node:node-b \| "Unhandled Error" err="error syncing CronJobController app-a-prod/app-a-sandbox-watchdog, requeuing: Operation cannot be fulfilled | 317 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| time="" level=error msg="Sending HTTP/1.1 <n> response to <ip>: dial tcp <ip>: connect: connection refused" | 11 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| time="" level=error msg="Sending HTTP/1.1 <n> response to <ip>: dial tcp <ip>: connect: connection timed out" | 8 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| Error proxying data from client to backend: read tcp <ip>-><ip>: read: connection timed out | 4 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "ExecSync cmd from runtime service failed" err="rpc error: code = DeadlineExceeded desc = failed to exec in container: timeout < dur> exceede | 3 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| time="" level=error msg="ExecSync for \"0b66d9fcfd3dbb61490614810f48a23a191c244009b98b36c812fdb74020fa99\" failed" error="rpc error: code =  | 2 | logs/node/node-b/containerd-24h.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="argocd/argocd-tls" error="Operat | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="app-f-prod/app-f-api-prod-tls" error=" | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="monitoring/grafana-acme-com- | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="logging/kibana-tls" error="Opera | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| node:node-a \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"da0beb4b | 1 | logs/node/node-a/k3s-errors-24h.log |
| node:node-a \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"c2414111 | 1 | logs/node/node-a/k3s-errors-24h.log |
| node:node-a \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"254e8283 | 1 | logs/node/node-a/k3s-errors-24h.log |
| node:node-b \| time="" level=error msg="failed sending message on channel" error="write unix /run/containerd/s/502a7cdae0b1853444bdc08970d9345882432c64f7ba | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| time="" level=error msg="ttrpc: received message on inactive stream" stream=57 | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| time="" level=error msg="failed sending message on channel" error="write unix /run/containerd/s/94e056724f0b1e095480d58a186019d37347f72eb278 | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| time="" level=error msg="failed sending message on channel" error="write unix /run/containerd/s/143d0514d835e08baa43745f50d6fc7ffa234f2cddd8 | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| time="" level=error msg="ContainerStatus for \"de457b0eedeefcffe1474540cefc7d4c1e6a1000c6c32b3f546421187deb6b83\" failed" error="rpc error:  | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| time="" level=error msg="ContainerStatus for \"38223df47ee539e4feca8f73b0f0c9b7c8c08403fc00ca8958658232a64cbfaa\" failed" error="rpc error:  | 1 | logs/node/node-b/containerd-24h.log |
| node:node-b \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"117e51f7 | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"f6765151 | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "Unhandled Error" err="error syncing CronJobController app-a-prod/app-a-postgres-backup, requeuing: Operation cannot be fulfilled  | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "Unhandled Error" err="error syncing CronJobController app-d-prod/app-d-postgres-mx-backup, requeuing: Operation cannot be fulfilled on cronjo | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "Unhandled Error" err="error syncing CronJobController app-e-api/app-e-postgres-backup, requeuing: Operation cannot be fulfilled on cron | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "Unhandled Error" err="error syncing CronJobController registry/registry-gc, requeuing: Operation cannot be fulfilled on cronjobs.batch \"re | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"de457b0e | 1 | logs/node/node-b/k3s-errors-24h.log |
| node:node-b \| "ContainerStatus from runtime service failed" err="rpc error: code = NotFound desc = an error occurred when try to find container \"38223df4 | 1 | logs/node/node-b/k3s-errors-24h.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="argocd/argocd-tls-7" erro | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'argocd/cm-acme-http-solver-zznj7' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="argocd-tls-7-<n>" resource_namespace="argocd" resource_kind="Order" re | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |

### 7-4. Raw files the LLM read directly

- `inventory.json`
- `findings-draft.json`
- `summary.json`
- `diff.json`
- `events.json`
- `collect-result.json`
- `objects/deployments.json`
- `objects/pods.json`
- `objects/statefulsets.json`
- `objects/services.json`
- `objects/cronjobs.json`
- `objects/jobs.batch.json`
- `objects/configmaps.json`
- `objects/applications.argoproj.io.json`
- `objects/ingresses.networking.k8s.io.json`
- `objects/nodes.json`
- `objects/helmcharts.helm.cattle.io.json`
- `metrics/am_notifications_1d.json`
- `metrics/alertmanager_notifications_failed_1d.json`
- `metrics/am_received_1d.json`
- `metrics/alerts_firing_stale_days.json`
- `extra/coturn-previous-head.txt`
- `extra/coturn-previous-grep.txt`
- `extra/coturn-usage-options.txt`
- `extra/configmap-secret-rhs-class.txt`
- `extra/node-port-probe.txt`
- `extra/node-port-probe-lan.txt`
- `extra/registry-v2-probe.txt`
- `extra/diff-vs-2026-11-05T02-07-16.json`
- `~/.kubegap/snapshots/default/2026-11-04T22-29-59/report-details.md`

Read-only commands run outside the snapshot:

| Command | Saved as |
|---|---|
| `(saved in extra/ before this analysis) kubectl -n app-c-prod logs app-c-coturn-549854dfcb-jgp4h --previous \\| head` | `extra/coturn-previous-head.txt` |
| `(saved in extra/ before this analysis) turnserver usage text of the running image, filtered for the dtls, tls and cli options` | `extra/coturn-usage-options.txt` |
| `(saved in extra/ before this analysis) classification of the right-hand side of the secret-like keys in the two app-v-script ConfigMaps, values not printed` | `extra/configmap-secret-rhs-class.txt` |
| `(saved in extra/ before this analysis) TCP connect probes to NodePorts 30432-30435 and control ports over the LAN and over Tailscale` | `extra/node-port-probe.txt` |
| `(saved in extra/ before this analysis) TCP connect probes between the nodes over br0` | `extra/node-port-probe-lan.txt` |

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
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
| `platform.k3s-datastore-slow.cluster` | fail | high | datastore etcd (servers ['node-b']), warn lines in 24h 375 (hit the 200-line cap - there were more): slow apply 191 (max 1160.1ms, over 1s 1), slow fdatasync 1, leader changes 0, request stats 170, DB 594MB |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.33.5+k3s1: upstream end of life 2026-06-28, 130 days past |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-backup` | fail | high | app-d-prod/app-d-postgres-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-mx', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-vn', 'node-b') … |
| `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup` | fail | high | app-d-prod/app-d-postgres-vn-backup: schedule '30 3 * * *', dump PVCs ['app-d-postgres-vn-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-d-prod/statefulset/app-d-postgres', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-mx', 'node-b'), ('app-d-prod/statefulset/app-d-postgres-vn', 'node-b') … |
| `resilience.backup-same-node.app-f-prod/app-f-mysql-backup` | fail | high | app-f-prod/app-f-mysql-backup: schedule '50 2 * * *', dump PVCs ['mysql-backup-app-f-mysql-0'] → nodes ['node-b'], hostPath [], source DB [('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-mysql', 'node-b'), ('app-f-prod/statefulset/app-f-qdrant', 'node-a')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-g-prod/app-g-postgres-backup` | fail | high | app-g-prod/app-g-postgres-backup: schedule '0 3 * * *', dump PVCs ['app-g-postgres-backup-pvc'] → nodes ['node-b'], hostPath [], source DB [('app-g-prod/statefulset/app-g-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.replicas-same-node.app-d-prod/deployment/app-d` | fail | high | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-admin` | fail | high | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server` | fail | high | replicas 3 (Running 3), node distribution {'node-a': 3}, AZ distribution {'null': 3}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client` | fail | high | replicas 2 (Running 2), node distribution {'node-a': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 1 — only one eligible node, so a spread declaration still … |
| `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn` | fail | high | 10715 restarts, state CrashLoopBackOff, last termination Error (exit 255) 2026-11-05T08:24:01Z, cause class crash (exit 255), Unhealthy events 0, node reboot time None |
| `resources.memory-limit-near-p95.app-e-api/sts/app-e-minio:minio` | fail | high | pod app-e-minio-0: 7d memory working set p95 / limit = 0.98 |
| `security.plaintext-configmap-secret.app-a-prod/configmap/app-v-scripts` | fail | high | app-a-prod/configmap/app-v-scripts: keys ['discord_sales_bot.py:TOKEN', 'discord_sales_bot.py:OPENAI_API_KEY', 'app-v_autopost.py:client_secret', 'app-v_autopost.py:resource_owner_secret'], mounted/referenced by ['app-a-prod/cronjob/app-v-autopost-en' … |
| `security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts` | fail | high | app-d-prod/configmap/app-d-app-v-scripts: keys ['app-d_ga4_digest.py:DISCORD_BOT_TOKEN', 'app-d_ga4_digest.py:token', 'app-d_policy_radar.py:OPENAI_API_KEY', 'app-d_policy_radar.py:DISCORD_BOT_TOKEN', 'app-d_sales_bot.py:TOKEN', 'app-d_sales_bot.py:OPENAI_API_KEY'], mounted/referenced by … |
| `storage.local-path-over-capacity.app-a-prod/app-a-postgres-backup-pvc` | fail | high | node node-a uses 5862MB / capacity 5120MB (1.14x). workloads ['app-a-prod/app-a-postgres-backup'] |
| `storage.local-path-over-capacity.logging/data-elasticsearch-0` | fail | high | node node-b uses 103451MB / capacity 20480MB (5.05x). workloads ['logging/elasticsearch-0'] |
| `tenancy.quota-near-limit.app-i-prod/app-i-prod-quota` | fail | high | app-i-prod/app-i-prod-quota: near limit ['persistentvolumeclaims'] (max ratio 1.0). hard {'limits.cpu': '4', 'limits.memory': '8Gi', 'persistentvolumeclaims': '2', 'requests.cpu': '2', 'requests.memory': '4Gi', 'requests.storage': '30Gi'}, used {'limits.cpu': '1800m', 'limits.memory': '2Gi' … |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external` | fail | high | nodeport app-d-prod/app-d-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external` | fail | high | nodeport app-d-prod/app-d-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external` | fail | high | nodeport app-d-prod/app-d-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external` | fail | high | nodeport app-g-prod/app-g-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `events.tracked-warning-reasons.Unhealthy` | warn | high | Probe failure. Readiness removes it from traffic, liveness restarts it. 265 occurrences total (28 events, trend over 45 snapshots [0, 0, 0, 0, 7, 0, 0, 8, 0, 33, 0, 0, 5, 6, 6, 0, 7, 7, 9, 9, 9, 0, 0, 12, 16, 0, 27, 28, 30, 31, 31, 32, 32, 33, 33, 33, 34, 62, 62, 74, 0, 0, 0, 7, 7], flat), first … |
| `logs.signatures.common.too-many-open-files` | warn | high | 32 occurrences (2026-11-05T03:30:04Z ~ 2026-11-05T04:17:00Z), thresholds warn 1/fail 10. Files: ['logs/node/node-b/containerd-24h.log']. Samples: ['time="2026-11-05T03:30:04.160019168Z" level=warning msg="error from *cgroupsv2.Manager.EventChan" error="failed to create inotify fd: too many open … |
| `node.disk-usage.<ip>:9100:/` | warn | high | usage 0.77 |
| `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | storage emptyDir (PVC None), PVC usage None, TSDB 21.4GiB, retention 30d (size cap 0B), actual oldest sample 30.9 days, failed compactions over 7 days 0, WAL corruptions 0, corruptions at startup 0 |
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
| `resources.cpu-throttling.app-e-api/sts/app-e-postgres:postgres` | warn | high | pod app-e-postgres-0: throttling ratio now 0.45, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-c7fr8: throttling ratio now 0.28, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most', 'pod fluent-bit-nnsb5: throttling ratio now 0.27, no 24-hour value: under 0.001 through the day or the query was not collected … |
| `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` | warn | high | pod elasticsearch-0: throttling ratio now 0.41, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | warn | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.52, no 24-hour value: under 0.001 through the day or the query was not collected, so this is a spike this moment at most |
| `resources.memory-limit-near-p95.logging/ds/fluent-bit:fluent-bit` | warn | high | ['pod fluent-bit-c7fr8: 7d memory working set p95 / limit = 0.84', 'pod fluent-bit-nnsb5: 7d memory working set p95 / limit = 0.82'] |
| `security.plaintext-configmap-secret.default/configmap/app-y-backend-config` | warn | high | default/configmap/app-y-backend-config: keys ['JWT_RELAY_SECRET', 'JWT_SECRET', 'TWITTER_CLIENT_SECRET', 'TWITTER_CLIENT_SECRET_RELAY'], mounted/referenced by [] |
| `security.plaintext-secret-env.logging/cronjob/es-index-retention:retention` | warn | high | Container retention env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/deployment/kibana:kibana` | warn | high | Container kibana env ['ELASTICSEARCH_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch` | warn | high | Container elasticsearch env ['ELASTIC_PASSWORD'] is a literal value rather than a secretKeyRef (value not recorded) |
| `security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn` | warn | high | ['hostNetwork'], containers allowing root ['coturn'] |
| `storage.local-path-fs-near-full.cluster` | warn | high | root filesystem per node {'node-a': {'avail_ratio': 0.228, 'size_gib': 106.7, 'growth_gib_per_day': -0.48, 'avail_gib': 24.3, 'days_to_full': None, 'volumes_gib': 6.0}, 'node-b': {'avail_ratio': 0.5, 'size_gib': 454.9, 'growth_gib_per_day': 0.27, 'avail_gib': 227.4, 'days_to_full': 842, 'volumes_gib' … |
| `tenancy.ci-shares-prod-nodes.node-a` | warn | high | Node node-a (pool (no-pool)): prod pods 32 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']) together with CI pods 1 (['arc-actions-runner-controller-5c9d9ffd65-766b6']). Heavy runners True, minutes above 90% node CPU in 7d 0.0, memory … |
| `tenancy.ci-shares-prod-nodes.node-b` | warn | high | Node node-b (pool (no-pool)): prod pods 15 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']) together with CI pods 2 (['ci-runner-8tt2w-4w6rk', 'ci-runner-8tt2w-d9kmt']). Heavy runners True, minutes above 90% node CPU in 7d … |
| `tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota` | warn | high | app-a-prod/app-a-prod-quota: requests entries in hard ['requests.memory'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota` | warn | high | app-b-prod/app-b-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-i-prod/app-i-prod-quota` | warn | high | app-i-prod/app-i-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `controlplane.etcd-slow.cluster` | fail | medium | 24h 'apply request took too long' 191 times, slow request stats 170, ReadIndex delays 13, leader changes 0, max 1160ms (if the 200-line log cap was hit, the real count is higher) |
| `coredns.nxdomain-ratio-high.cluster` | fail | medium | NXDOMAIN share of responses in 1h 0.698, queries per second 31.22, NXDOMAIN share of queries forwarded upstream 0.825 (upstreams ['1.1.1.1:53', '8.8.8.8:53']), pods with default ndots (5) 153, autopath False, cache hit ratio 0.85 |
| `eso.store-static-credentials.cluster` | fail | medium | stores with static key auth ['ClusterSecretStore/aws-secret-store'] (all auth methods {'ClusterSecretStore/aws-secret-store': 'static-key(Secret)'}), providers ['aws'], ExternalSecrets 39 (prod 33) |
| `hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix` | fail | medium | image arizephoenix/phoenix:latest (tag latest, imagePullPolicy IfNotPresent, registry docker.io) |
| `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn` | fail | medium | image coturn/coturn:latest (tag latest, imagePullPolicy Always, registry docker.io) |
| `hygiene.polaris-reliability-danger.app-a-prod/daemonset/app-a-sandbox-prepull` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['livenessProbeMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet', 'readinessProbeMissing', 'topologySpreadConstraint']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in the security … |
| `hygiene.polaris-reliability-danger.app-a-prod/deployment/app-a-phoenix` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['deploymentMissingReplicas', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet', 'pullPolicyNotAlways', 'topologySpreadConstraint']. Security-category danger ['privilegeEscalationAllowed' … |
| `hygiene.polaris-reliability-danger.app-c-prod/deployment/app-c-coturn` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['deploymentMissingReplicas', 'livenessProbeMissing', 'metadataAndInstanceMismatched', 'missingPodDisruptionBudget', 'priorityClassNotSet', 'readinessProbeMissing']. Security-category danger ['hostNetworkSet' … |
| `node.kubelet-reserved-missing.node-a` | fail | medium | configz kubeReserved {}, systemReserved {}, enforceNodeAllocatable ['pods'], maxPods 110. Node memory 31.3GB |
| `node.kubelet-reserved-missing.node-b` | fail | medium | configz kubeReserved {}, systemReserved {}, enforceNodeAllocatable ['pods'], maxPods 110. Node memory 30.7GB |
| `node.pod-dir-large.monitoring/prometheus-kube-prometheus-stack-prometheus-0` | fail | medium | node node-b /var/lib/kubelet/pods/2575bb27-9b7a-46a3-883d-62e65510c895/volumes/kubernetes.io~empty-dir 22004MB (prometheus-kube-prometheus-stack-prometheus-0) |
| `observability.alert-firing-stale.CPUThrottlingHigh/monitoring` | fail | medium | Firing for 73.1 days (ALERTS_FOR_STATE). Labels {'namespace': 'monitoring', 'pod': 'prometheus-kube-prometheus-stack-prometheus-0', 'severity': 'info'} |
| `observability.alert-firing-stale.KubeCPUOvercommit` | fail | medium | Firing for 30.6 days (ALERTS_FOR_STATE). Labels {'severity': 'warning'} |
| `observability.alert-firing-stale.KubeJobFailed/app-a-prod` | fail | medium | ["Firing for 11.2 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-a-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'warning'}", "Firing for 7.4 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace' … |
| `observability.alert-firing-stale.KubePodCrashLooping/app-c-prod` | fail | medium | Firing for 38.1 days (ALERTS_FOR_STATE). Labels {'job': 'kube-state-metrics', 'namespace': 'app-c-prod', 'pod': 'app-c-coturn-549854dfcb-jgp4h', 'severity': 'warning'} |
| `observability.alert-firing-stale.KubeQuotaFullyUsed/app-i-prod` | fail | medium | Firing for 127.4 days (ALERTS_FOR_STATE). Labels {'namespace': 'app-i-prod', 'pod': 'kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2', 'severity': 'info'} |
| `observability.alerts-always-firing.CPUThrottlingHigh` | fail | medium | 7d firing samples 86821 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeCPUOvercommit` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeDeploymentReplicasMismatch` | fail | medium | 7d firing samples 20098 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeJobFailed` | fail | medium | 7d firing samples 40320 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubePodCrashLooping` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeQuotaFullyUsed` | fail | medium | 7d firing samples 20160 (same level as Watchdog = never stops firing) |
| `observability.ingress-controller-metrics-missing.ingress-controller` | fail | medium | 29 ingresses, 0 ingress-controller request metric series, namespaces with app http_* metrics [], ALB CloudWatch False — per-backend gaps are the 29 golden-signals-missing (warn) findings |
| `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn` | fail | medium | Available=False (MinimumReplicasUnavailable) for 6.7 hours: Deployment does not have minimum availability. |
| `platform.k3s-etcd-snapshot-local-only.node-b` | fail | medium | all 5 snapshots at file:///var/lib/rancher/k3s/server/db/snapshots (same node, same disk). No S3 config (--etcd-s3) |
| `platform.k3s-secrets-encryption-off.node-b` | fail | medium | k3s secrets-encrypt status: Disabled, no configuration file found. Datastore etcd 594MB |
| `resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog` | fail | medium | schedule '* * * * *' (about every 0.016666666666666666h), last success 2026-11-05T08:24:50Z (6.4h ago), last schedule 2026-11-05T08:25:00Z, active Jobs 1, failed Jobs ['app-a-sandbox-watchdog-29881700', 'app-a-sandbox-watchdog-29887083'], suspend False |
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
| `resources.krr-recommendation.app-a-prod/deployment/app-a-backend:backend` | fail | medium | memory request under by 890 MB: CPU HPA detected, memory request 256 → 1146 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req CRITICAL, memory limit OK). cpu: HPA detected |
| `resources.krr-recommendation.app-a-prod/deployment/app-a-umami:umami` | fail | medium | memory request under by 369 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 497 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/statefulset/app-a-postgres:postgres` | fail | medium | memory request under by 1587 MB, CPU request over by 0.138 cores: CPU request 0.2 → 0.062 cores, CPU limit 1.0 → none, memory request 512 → 2099 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req CRITICAL, memory limit GOOD) |
| `resources.krr-recommendation.app-e-api/statefulset/app-e-minio:minio` | fail | medium | memory request under by 454 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 582 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.app-f-prod/deployment/app-f-embed:app` | fail | medium | CPU request over by 0.49 cores, memory request over by 1301 MB: CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 2048 → 747 MB, memory limit 4096 → 747 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.logging/statefulset/elasticsearch:elasticsearch` | fail | medium | memory request under by 773 MB: CPU request 0.2 → 0.296 cores, CPU limit 0.6 → none, memory request 2048 → 2821 MB, memory limit 3072 → 2821 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit WARNING) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 520 MB: CPU request 0.2 → 0.109 cores, CPU limit 0.3 → none, memory request 1024 → 1544 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit GOOD) |
| `security.networkpolicy-coverage.cluster` | fail | medium | 20 of 22 user namespaces have no NetworkPolicy, of which production ['app-b-prod', 'app-c-prod', 'app-d-prod', 'app-f-prod', 'app-g-prod', 'app-i-prod']; with: ['app-a-prod', 'argocd'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 75. Security danger workloads 102 (prod 68): per check {'privilegeEscalationAllowed': 87, 'runAsRootAllowed': 82, 'sensitiveContainerEnvVar': 12, 'hostNetworkSet': 3, 'hostPIDSet': 3, 'runAsPrivileged': 2, 'clusterrolebindingClusterAdmin': 1, 'clusterrolebindingPodExecAttach': 3 … |
| `tenancy.prod-boundary-missing.app-c-prod` | fail | medium | app-c-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-d-prod` | fail | medium | app-d-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-f-prod` | fail | medium | app-f-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `tenancy.prod-boundary-missing.app-g-prod` | fail | medium | app-g-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 12 |
| `traffic.pod-not-ready.app-c-prod/app-c-coturn` | fail | medium | 24h minimum Ready ratio 0.0 (pod app-c-coturn-549854dfcb-jgp4h, about 1440 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL None |
| `argocd.app-out-of-sync-or-unhealthy.cluster` | warn | medium | Applications 18 (prod 10), OutOfSync ['argocd/application/root'] (prod []), Degraded/Missing/Unknown [] (prod []), Progressing (rolling out, not abnormal) ['argocd/application/app-c'], apps with conditions ['ExcludedResourceWarning']: ['argocd/application/app-k'], last operation failed [] |
| `argocd.default-project-wildcard.cluster` | warn | medium | AppProjects 2, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 4/18 (prod 10) |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.745s |
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
| `hygiene.polaris-reliability-danger.registry/cronjob/registry-tag-cleanup` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.pvc-unbound-or-unused.cluster` | warn | medium | Non-Bound PVCs [], Released/Failed PVs [], Bound PVCs used by no pod [('default', 'data-app-z-db-0')] |
| `logs.signatures.cert-manager.challenge-failed` | warn | medium | 10 occurrences (2026-11-05T02:31:09Z ~ 2026-11-05T03:35:40Z), thresholds warn 5/fail 100. Files: ['logs/pods/cert-manager/cert-manager_cert-manager.log']. Samples: ['[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-05T02:31:09.690144851Z E1105 02:31:09.689988       1 sync.go:190] … |
| `logs.signatures.containerd.image-pull-failed` | warn | medium | 4 occurrences (2026-11-05T07:37:11Z ~ 2026-11-05T07:37:11Z), thresholds warn 1/fail 10. Files: ['logs/node/node-a/k3s-errors-24h.log']. Samples: ['E1105 16:37:11.763079    1316 log.go:32] "PullImage from image service failed" err="rpc error: code = Unknown desc = failed to pull and unpack image … |
| `logs.signatures.fluent-bit.flush-failed` | warn | medium | 14 occurrences (2026-11-05T07:57:36Z ~ 2026-11-05T08:25:46Z), thresholds warn 10/fail 500. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ["[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:57:36.227818631+09:00 [2026/11/05 07:57:36] [ warn] [engine] failed to flush chunk … |
| `logs.signatures.fluent-bit.upstream-down` | warn | medium | 11 occurrences (2026-11-05T07:54:47Z ~ 2026-11-05T08:23:31Z), thresholds warn 5/fail 200. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ['[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:54:47.226478840+09:00 [2026/11/05 07:54:47] [error] … |
| `node.container-writable-layer-large.node-b` | warn | medium | Node node-b: top writable layers [('logging/elasticsearch-0', 'elasticsearch', 2220), ('app-a-prod/app-v-radar-japan-noon', 'radar', 989), ('app-a-prod/app-v-radar-global-eu', 'radar', 968), ('app-a-prod/app-v-radar-japan', 'radar', 965) … |
| `node.cri-exited-containers.node-a` | warn | medium | crictl ps -a: Running 55, Exited 69, Unknown 0. 54 images, 29.5 GiB |
| `node.cri-exited-containers.node-b` | warn | medium | crictl ps -a: Running 69, Exited 93, Unknown 0. 61 images, 25.5 GiB |
| `node.kubelet-eviction-memory-missing.node-a` | warn | medium | configz evictionHard {'imagefs.available': '5%', 'nodefs.available': '5%'}, evictionSoft {}, imageGC 80~85% |
| `node.kubelet-eviction-memory-missing.node-b` | warn | medium | configz evictionHard {'imagefs.available': '5%', 'nodefs.available': '5%'}, evictionSoft {}, imageGC 80~85% |
| `node.service-restarts.node-b` | warn | medium | systemd NRestarts {'kubelet': 0, 'containerd': 0, 'k3s': 5} (uptime 117.3 days, automatic restarts only. Unit states [('kubelet', 'inactive', 'n/a'), ('containerd', 'inactive', 'n/a'), ('k3s', 'active', 'Wed 2026-10-28 19:25:12 UTC')]) |
| `node.sysctl-tuning.node-a` | warn | medium | ["fs.inotify.max_user_instances=128 (recommended ≥ 512, k3s docs 8192; nodes with many pods/log collectors hit 'too many open files')", 'fs.inotify.max_user_watches=247744 (recommended ≥ 524288)'] |
| `node.sysctl-tuning.node-b` | warn | medium | ["fs.inotify.max_user_instances=128 (recommended ≥ 512, k3s docs 8192; nodes with many pods/log collectors hit 'too many open files')", 'fs.inotify.max_user_watches=244476 (recommended ≥ 524288)', 'vm.max_map_count=65530 (Elasticsearch/OpenSearch runs in this cluster; requires 262144. Without an … |
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
| `resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog` | warn | medium | app-a-prod/app-a-sandbox-watchdog: schedule '* * * * *' (about 0.016666666666666666h), recent Job max 50s / median 50s = 0.83x the interval (1 measured), concurrencyPolicy Forbid, active Jobs 1 |
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
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/deployment/app-a-frontend:frontend` | warn | medium | memory request under by 182 MB: CPU HPA detected, memory request 128 → 310 MB. KRR severity OK (CPU req UNKNOWN, CPU limit UNKNOWN, memory req OK, memory limit OK). cpu: HPA detected |
| `resources.krr-recommendation.app-a-prod/statefulset/app-a-redis:redis` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.acme-site/deployment/acme-site:nginx` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.1 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-d-prod/statefulset/app-d-redis:redis` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-f-prod/deployment/app-f-excel-agent:app` | warn | medium | memory request under by 250 MB: CPU request 0.05 → 0.01 cores, CPU limit 1.0 → none, memory request 256 → 506 MB, memory limit 1024 → 506 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.app-f-prod/statefulset/app-f-mysql:mysql` | warn | medium | CPU request over by 0.173 cores: CPU request 0.2 → 0.027 cores, CPU limit 1.5 → none, memory request 1600 → 1370 MB, memory limit 3200 → 1370 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller` | warn | medium | memory request under by 228 MB: CPU request 0.1 → 0.01 cores, memory request 90 → 318 MB, memory limit None → 318 MB. KRR severity WARNING (CPU req GOOD, CPU limit GOOD, memory req OK, memory limit WARNING) |
| `resources.krr-recommendation.logging/daemonset/fluent-bit:fluent-bit` | warn | medium | memory request under by 94 MB: CPU request 0.05 → 0.062 cores, CPU limit 0.1 → none, memory request 50 → 144 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.logging/deployment/kibana:kibana` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 446 MB, memory limit 1024 → 446 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.registry/statefulset/registry:registry` | warn | medium | memory request under by 155 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 128 → 283 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.app-i-prod/deployment/app-i-web:web` | warn | medium | memory request under by 76 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 204 MB, memory limit 512 → 204 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `scaling.hpa-flapping.app-f-prod/hpa/app-f-api-server` | warn | medium | 33 desired changes over 7 days |
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
| `traffic.coredns-latency.cluster` | warn | medium | 1h DNS request p99 0.1396s, SERVFAIL ratio 0.0 |
| `traffic.ingress-nginx-retired.cluster` | warn | medium | ingress-nginx 1.14.0 (Deployment ingress-nginx/nginx-ingress-ingress-nginx-controller); ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes; admission webhook on |
| `hygiene.no-standard-labels.cluster` | fail | low | Of 110 workloads, share with standard labels 0.23. prod workloads without: ['app-a-prod/deployment/app-a-backend', 'app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix' … |
| `node.swap-enabled.<ip>:9100` | fail | low | swap 8.0 GiB |
| `platform.k3s-server-url-stale.node-b` | fail | low | host <ip> of --server https://<ip>:6443 is not among current node IPs or names |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend` | fail | low | HPA app-a-prod/app-a-backend: share of 15 days at min 1.00, min 2 max 6, current CPU utilization 3% / target 70%, metrics ['cpu'], last scale 3.3 days ago |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend` | fail | low | HPA app-a-prod/app-a-frontend: share of 15 days at min 1.00, min 2 max 4, current CPU utilization 3% / target 70%, metrics ['cpu'], last scale 1.2 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d` | fail | low | HPA app-d-prod/app-d: share of 15 days at min 1.00, min 2 max 5, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.7 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d-mx` | fail | low | HPA app-d-prod/app-d-mx: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.7 days ago |
| `scaling.hpa-never-scaled.app-d-prod/deployment/app-d-vn` | fail | low | HPA app-d-prod/app-d-vn: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 7.7 days ago |
| `scaling.hpa-never-scaled.app-g-prod/deployment/app-g` | fail | low | HPA app-g-prod/app-g: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 2% / target 60%, metrics ['cpu', 'memory'], last scale 7.7 days ago |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 10, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 10, apps whose targetRevision is a branch or HEAD 10 ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-c', 'argocd/application/app-d-kr', 'argocd/application/app-d-mx', 'argocd/application/app-d-shared', 'argocd/application/app-d-vn' … |
| `certmanager.controller-errors.cluster` | warn | low | sync calls since controller start 2454 / errors 233, ACME requests 117 by status {'200': 105, '201': 7, '400': 5} (4xx/5xx 5, ratio 0.0427), Ready False metric 0 |
| `certmanager.version-old.cluster` | warn | low | cert-manager 1.14.4 (components {'controller': '1/1', 'cainjector': '1/1', 'webhook': '1/1'}), webhooks with Fail 2 / webhook replicas 1 |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.487, cluster IPv6 False, queries per second 31.22. The glibc resolver always asks A and AAAA as a pair |
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
| `hygiene.failed-pods-lingering.cluster` | warn | low | Failed pods 4 (prod 4), reasons {'Failed': 2, 'UnexpectedAdmissionError': 2}, namespaces {'app-a-prod': 2, 'app-f-prod': 2}, oldest 3847.0h. Example: ['app-a-prod/app-u', 'app-a-prod/app-a-experiment', 'app-f-prod/app-f-embed-67f6f74f6c-rlm8m', 'app-f-prod/app-f-embed-67f6f74f6c-b6kdt'] |
| `hygiene.no-ephemeral-storage-requests.cluster` | warn | low | Containers with an ephemeral-storage request 0 of 126 (0.0), without one in prod 63. emptyDirs without sizeLimit 11 (prod: []) |
| `hygiene.old-replicasets.cluster` | warn | low | Of 292 ReplicaSets, 235 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 54, '0': 3, '3': 1, '2': 1} |
| `hygiene.orphan-secrets.cluster` | warn | low | Of 139 Secrets (metric kube_secret_info), 9 unreferenced candidates: [('argocd', 'ghcr-auth-secret', 'kubernetes.io/dockerconfigjson'), ('argocd', 'ghcr-pull-secret', 'kubernetes.io/dockerconfigjson'), ('default', 'app-d-prod-tls', 'kubernetes.io/tls'), ('default', 'app-z-auth-secret', 'Opaque') … |
| `hygiene.unused-crds.cluster` | warn | low | 42 of 64 CRDs have zero objects (by group {'generators.external-secrets.io': 17, 'monitoring.coreos.com': 6, 'metallb.io': 5, 'acme.cert-manager.io': 1, 'eventing.keda.sh': 2, 'external-secrets.io': 4, 'keda.sh': 4, 'helm.cattle.io': 2, 'actions.summerwind.dev': 1}), 28 webhooks |
| `keda.unused.cluster` | warn | low | KEDA v2.19.0 operator 1/1, metrics-apiserver 1/1, webhooks 1/1 — ScaledObject 0, ScaledJob 0 |
| `logs.signatures.cert-manager.orphan-tls-secret` | warn | low | 64 occurrences (2026-11-04T15:18:56Z ~ 2026-11-05T00:57:19Z), thresholds warn 1/fail 1000. Files: ['logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log']. Samples: ['[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-04T15:18:56.553816246Z E1104 … |
| `logs.signatures.kubelet.pod-sync-error` | warn | low | 2988 occurrences (2026-11-04T21:34:47Z ~ 2026-11-05T08:25:20Z), thresholds warn 50/fail 1000. Files: ['logs/node/node-a/k3s-errors-24h.log']. Samples: ['E1105 06:34:47.751559    1316 pod_workers.go:1301] "Error syncing pod, skipping" err="failed to \\"StartContainer\\" for \\"coturn\\" with … |
| `logs.signatures.metallb.speaker-peer-unreachable` | warn | low | 487 occurrences (2026-11-05T05:05:40Z ~ 2026-11-05T08:26:40Z), thresholds warn 60/fail 2000. Files: ['logs/pods/metallb/metallb-system_speaker.log']. Samples: ['[pod/speaker-xfxlv/speaker] 2026-11-05T14:35:35.218743637+09:00 {"caller":"speakerlist.go:259","error":"1 error occurred:\\n\\t* Failed to … |
| `node.docker-and-containerd.node-a` | warn | low | Node node-a: active runtimes ['containerd', 'k3s-agent', 'docker'], kubelet runtime containerd, /var/lib/docker 1MB |
| `node.large-images.node-a` | warn | low | Node node-a: images of 3 GiB or more 1 — registry.acme.com/app-f-embed:prod-67527dae60678e93822bf8eb71d8448f586fa0fe (largest 3977 MiB) |
| `node.os-updates-pending.node-a` | warn | low | 52 updates pending, 1 of them security (per Ubuntu update-notifier). OS Ubuntu 22.04.5 LTS |
| `node.os-updates-pending.node-b` | warn | low | 52 updates pending, 7 of them security (per Ubuntu update-notifier). OS Ubuntu 22.04.5 LTS |
| `node.reboot-required.node-a` | warn | low | reboot-required True, uptime 7.4 days, running kernel 5.15.0-198-generic, pending updates 52 (security 1) |
| `node.reboot-required.node-b` | warn | low | reboot-required True, uptime 117.3 days, running kernel 5.15.0-185-generic, pending updates 52 (security 7) |
| `node.smartmontools-missing.node-a` | warn | low | smartctl missing. Disks ['sda disk 111.8G 0 WDC WDS120G2G0A-'] |
| `node.smartmontools-missing.node-b` | warn | low | smartctl missing. Disks ['sda disk 465.8G 0 Samsung SSD 870'] |
| `observability.alerts-never-fired.cluster` | warn | low | 135 of 145 rules did not fire in 15 days (['AppAClusterCPU50', 'AppAClusterCPU80', 'AppAClusterMem50', 'AppAClusterMem80', 'AppAFrontendDown', 'AppAGatewayDown', 'AppAGatewayErrorRateHigh', 'AppAGatewayHighCost', 'AppAGatewayUpstreamRejecting' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 28 of 29 ingress backends have no saturation metric (e.g. [('app-a-prod', 'app-a-backend'), ('app-a-prod', 'app-a-frontend'), ('app-a-prod', 'app-a-phoenix'), ('app-a-prod', 'app-a-umami'), ('argocd', 'argocd-server-ingress'), ('app-b-prod' … |
| `observability.severity-channels-not-separated.cluster` | warn | low | routes [('discord', None), ('null', ['severity=~"info\|none"'])], receivers ['null', 'discord'], default receiver discord |
| `observability.unclassified-errors.cluster` | warn | low | 403 unclassified error lines (26732 lines scanned, 24 files). Top: [('node:node-b \| "Unhandled Error" err="error syncing CronJobController app-a-prod/app-a-sandbo', 317), ('node:node-b \| time="" level=error msg="Sending HTTP/1.1 <n> response to <ip>: dial tcp <ip>: connect: ', 11) … |
| `platform.k3s-apiserver-bind-all.cluster` | warn | low | servers binding 6443 to *: ['node-b'], --tls-san ['<ip>', '<ip>'], node-external-ip ['<ip>', '<ip>'] |
| `platform.k3s-check-config-missing.cluster` | warn | low | missing: ['CONFIG_INET_XFRM_MODE_TRANSPORT', 'CONFIG_RT_GROUP_SCHED'] |
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
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: metrics ['cpu'], current CPU 3% / target 70% |
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
| `storage.local-path-node-pinned.cluster` | warn | low | 26 local-path PVs, by node {'node-a': 7, 'node-b': 19}, node disk used {'node-a': 6193, 'node-b': 140321}MB. top: [('logging', 'data-elasticsearch-0', 'node-b', 103451, ['logging/elasticsearch-0']), ('registry', 'registry-data-registry-0', 'node-b', 32732, ['registry/registry-0']), ('app-a-prod' … |
| `storage.local-path-prod-delete-reclaim.cluster` | warn | low | 19 of 19 prod PVs are Delete ['app-i-prod/app-i-postgres-data', 'app-d-prod/app-d-postgres-mx-backup-pvc', 'app-g-prod/app-g-postgres-backup-pvc', 'app-d-prod/app-d-postgres-vn-data-app-d-postgres-vn-0', 'app-b-prod/app-b-artifacts' … |
| `traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller` | warn | low | Service ingress-nginx/nginx-ingress-ingress-nginx-controller: externalTrafficPolicy Local, ports [80, 443], addresses ['<ip>'] |
| `traffic.metallb-single-lb-service.cluster` | warn | low | mode layer2, 1 LoadBalancer services, pool used 1/10, leader node-b (1.0), pinned by nodeSelectors False, 2 nodes |

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>resilience.n-plus-one.cluster</code></summary>

```json
{
 "pods_on_largest_node": 48,
 "memory_ok": true,
 "allocatable_memory_gb_without_largest": 30.7,
 "prod_pods_on_largest_node": 15,
 "requests_cpu_total": 6.17,
 "allocatable_cpu_without_largest": 6.0,
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
 "largest_node_memory_gb": 30.7,
 "requests_memory_gb_total": 23.9,
 "ok": false,
 "tight": false,
 "largest_node_cpu": 12.0,
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
 "cpu_ok": false,
 "available": true,
 "largest_node": "node-b",
 "autoscaler": false,
 "karpenter": false
}
```

</details>
<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "symptom_rules": [],
 "by_class": {
  "cause": 153,
  "app-cause": 1,
  "app": 7
 },
 "symptom_ratio": 0.0,
 "alerting": 161
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
 "nodes_with_pods": 1,
 "restarts_total": 1,
 "replicas": 1,
 "pdb": [],
 "nodes_total": 2,
 "spread_declared": true,
 "single_replica": true,
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
 "last": "2026-11-05T08:21:42Z",
 "trend": "up",
 "type": "Warning",
 "occurrences": 193081,
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
 "meaning": "Container keeps dying and the restart interval grows (CrashLoopBackOff)",
 "reason": "BackOff",
 "first": "2026-10-05T18:39:29Z",
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
 "severity_hint": "high"
}
```

</details>
<details><summary><code>observability.failure-mode-uncovered.OOMKill</code></summary>

```json
{
 "mode": "OOMKill",
 "symptom": "pods die and requests fail or slow down",
 "importance": "critical"
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
<details><summary><code>platform.k3s-datastore-slow.cluster</code></summary>

```json
{
 "db_mb": 594,
 "servers": [
  "node-b"
 ],
 "capped": true,
 "fdatasync_slow": 1,
 "apply_slow": 191,
 "request_stats": 170,
 "kind": "etcd",
 "lines_24h": 375,
 "leader_changes": 0,
 "apply_over_1s": 1,
 "max_apply_ms": 1160.1
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "prod": true,
 "schedule": "30 3 * * *",
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
 "dest_nodes": [
  "node-b"
 ],
 "dest_pvcs": [
  "app-d-postgres-backup-pvc"
 ],
 "same_node_as_source": true,
 "offsite_hint": false,
 "target": "app-d-prod/app-d-postgres-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "prod": true,
 "schedule": "30 3 * * *",
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
 "dest_nodes": [
  "node-b"
 ],
 "dest_pvcs": [
  "app-d-postgres-vn-backup-pvc"
 ],
 "same_node_as_source": true,
 "offsite_hint": false,
 "target": "app-d-prod/app-d-postgres-vn-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-f-prod/app-f-mysql-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "prod": true,
 "schedule": "50 2 * * *",
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
 "dest_nodes": [
  "node-b"
 ],
 "dest_pvcs": [
  "mysql-backup-app-f-mysql-0"
 ],
 "same_node_as_source": true,
 "offsite_hint": false,
 "target": "app-f-prod/app-f-mysql-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-g-prod/app-g-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "prod": true,
 "schedule": "0 3 * * *",
 "source_db": [
  {
   "workload": "app-g-prod/statefulset/app-g-postgres",
   "pvc": "app-g-postgres-data-app-g-postgres-0",
   "node": "node-b"
  }
 ],
 "dest_nodes": [
  "node-b"
 ],
 "dest_pvcs": [
  "app-g-postgres-backup-pvc"
 ],
 "same_node_as_source": true,
 "offsite_hint": false,
 "target": "app-g-prod/app-g-postgres-backup"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-d-prod/deployment/app-d</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": true,
 "workload": "app-d-prod/deployment/app-d",
 "nodes": {
  "node-a": 2
 },
 "prod": true,
 "all_same_node": true,
 "replicas": 2,
 "eligible_nodes": 1,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ]
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": true,
 "workload": "app-f-prod/deployment/app-f-admin",
 "nodes": {
  "node-a": 3
 },
 "prod": true,
 "all_same_node": true,
 "replicas": 3,
 "eligible_nodes": 1,
 "running": 3,
 "zones": {
  "null": 3
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ]
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": true,
 "workload": "app-f-prod/deployment/app-f-api-server",
 "nodes": {
  "node-a": 3
 },
 "prod": true,
 "all_same_node": true,
 "replicas": 3,
 "eligible_nodes": 1,
 "running": 3,
 "zones": {
  "null": 3
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ]
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f-app-x-client</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": true,
 "workload": "app-f-prod/deployment/app-f-app-x-client",
 "nodes": {
  "node-a": 2
 },
 "prod": true,
 "all_same_node": true,
 "replicas": 2,
 "eligible_nodes": 1,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": [
  {
   "key": "kubernetes.io/hostname",
   "max_skew": 1,
   "when": "DoNotSchedule"
  }
 ]
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn</code></summary>

```json
{
 "crashloop": true,
 "rebooted": false,
 "pod": "app-c-coturn-549854dfcb-jgp4h",
 "waiting": "CrashLoopBackOff",
 "namespace": "app-c-prod",
 "restarts": 10715,
 "last_reason": "Error",
 "exit_code": 255,
 "node_rebooted_at": null,
 "unhealthy_events": 0,
 "container": "coturn",
 "cause": "crash (exit 255)",
 "last_finished": "2026-11-05T08:24:01Z"
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
 "prod": true,
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
 "target": "app-a-prod/configmap/app-v-scripts"
}
```

</details>
<details><summary><code>security.plaintext-configmap-secret.app-d-prod/configmap/app-d-app-v-scripts</code></summary>

```json
{
 "prod": true,
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
 "target": "app-d-prod/configmap/app-d-app-v-scripts"
}
```

</details>
<details><summary><code>storage.local-path-over-capacity.app-a-prod/app-a-postgres-backup-pvc</code></summary>

```json
{
 "used_ratio": 1.14,
 "pvc": "app-a-postgres-backup-pvc",
 "namespace": "app-a-prod",
 "workloads": [
  "app-a-prod/app-a-postgres-backup"
 ],
 "node": "node-a",
 "capacity_mb": 5120,
 "used_mb": 5862
}
```

</details>
<details><summary><code>storage.local-path-over-capacity.logging/data-elasticsearch-0</code></summary>

```json
{
 "used_ratio": 5.05,
 "pvc": "data-elasticsearch-0",
 "namespace": "logging",
 "workloads": [
  "logging/elasticsearch-0"
 ],
 "node": "node-b",
 "capacity_mb": 20480,
 "used_mb": 103451
}
```

</details>
<details><summary><code>tenancy.quota-near-limit.app-i-prod/app-i-prod-quota</code></summary>

```json
{
 "near_limit": [
  "persistentvolumeclaims"
 ],
 "max_ratio": 1.0,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "30Gi"
 },
 "used": {
  "limits.cpu": "1800m",
  "limits.memory": "2Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "200m",
  "requests.memory": "512Mi",
  "requests.storage": "20Gi"
 },
 "target": "app-i-prod/app-i-prod-quota"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external</code></summary>

```json
{
 "allowed_sources": {},
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "name": "app-d-postgres-external",
 "source_ranges": null,
 "type": "nodeport",
 "namespace": "app-d-prod",
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "hosts": [],
 "target": "nodeport/app-d-prod/app-d-postgres-external"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external</code></summary>

```json
{
 "allowed_sources": {},
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "name": "app-d-postgres-mx-external",
 "source_ranges": null,
 "type": "nodeport",
 "namespace": "app-d-prod",
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "hosts": [],
 "target": "nodeport/app-d-prod/app-d-postgres-mx-external"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external</code></summary>

```json
{
 "allowed_sources": {},
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "name": "app-d-postgres-vn-external",
 "source_ranges": null,
 "type": "nodeport",
 "namespace": "app-d-prod",
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "hosts": [],
 "target": "nodeport/app-d-prod/app-d-postgres-vn-external"
}
```

</details>
<details><summary><code>traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external</code></summary>

```json
{
 "allowed_sources": {},
 "note": "DB port open on an external address",
 "ports": [
  5432
 ],
 "name": "app-g-postgres-external",
 "source_ranges": null,
 "type": "nodeport",
 "namespace": "app-g-prod",
 "scheme": "node-ip (all node interfaces)",
 "sg_exposure": null,
 "hosts": [],
 "target": "nodeport/app-g-prod/app-g-postgres-external"
}
```

</details>
<details><summary><code>controlplane.apiserver-5xx.cluster</code></summary>

```json
{
 "labels": {
  "code": "503"
 },
 "value": 0.003704609274859781
}
```

</details>
<details><summary><code>events.tracked-warning-reasons.Unhealthy</code></summary>

```json
{
 "events": 28,
 "last": "2026-11-05T07:53:09Z",
 "trend": "flat",
 "type": "Warning",
 "occurrences": 265,
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
 "meaning": "Probe failure. Readiness removes it from traffic, liveness restarts it",
 "reason": "Unhealthy",
 "first": "2026-10-21T02:04:50Z",
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
 "severity_hint": "medium"
}
```

</details>
<details><summary><code>logs.signatures.common.too-many-open-files</code></summary>

```json
{
 "count": 32,
 "first": "2026-11-05T03:30:04Z",
 "last": "2026-11-05T04:17:00Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/node/node-b/containerd-24h.log": 32
 },
 "samples": [
  "time=\"2026-11-05T03:30:04.160019168Z\" level=warning msg=\"error from *cgroupsv2.Manager.EventChan\" error=\"failed to create inotify fd: too many open files\"",
  "time=\"2026-11-05T03:30:04.176004100Z\" level=warning msg=\"error from *cgroupsv2.Manager.EventChan\" error=\"failed to create inotify fd: too many open files\"",
  "time=\"2026-11-05T03:30:04.302653199Z\" level=warning msg=\"error from *cgroupsv2.Manager.EventChan\" error=\"failed to create inotify fd: too many open files\"",
  "time=\"2026-11-05T03:30:04.332939430Z\" level=warning msg=\"error from *cgroupsv2.Manager.EventChan\" error=\"failed to create inotify fd: too many open files\"",
  "time=\"2026-11-05T03:50:00.718678342Z\" level=warning msg=\"error from *cgroupsv2.Manager.EventChan\" error=\"failed to create inotify fd: too many open files\""
 ]
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
 "value": 0.772499245476325
}
```

</details>
<details><summary><code>prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "corruption_count": 0,
 "wal_corruptions": 0,
 "storage": "emptyDir",
 "pvc_size": null,
 "retention_time": "30d",
 "retention_size": "0B",
 "compactions_failed_7d": 0,
 "oldest_sample_days": 30.9,
 "present": true,
 "retention_shortfall": false,
 "pvc_used_ratio": null,
 "tsdb_bytes": 22938841758.0,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-a-prod/app-a-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "schedule": "15 3 * * *",
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
 "local_only": true,
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-a-postgres-backup-pvc"
 ],
 "same_node_as_source": false,
 "offsite_hint": false,
 "target": "app-a-prod/app-a-postgres-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup</code></summary>

```json
{
 "host_paths": [],
 "suspend": false,
 "schedule": "30 3 * * *",
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
 "local_only": true,
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-d-postgres-mx-backup-pvc"
 ],
 "same_node_as_source": false,
 "offsite_hint": false,
 "target": "app-d-prod/app-d-postgres-mx-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-e-api/app-e-postgres-backup</code></summary>

```json
{
 "host_paths": [],
 "prod": false,
 "suspend": false,
 "schedule": "50 3 * * *",
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
 "local_only": true,
 "dest_nodes": [
  "node-b"
 ],
 "dest_pvcs": [
  "app-e-postgres-backup-pvc"
 ],
 "same_node_as_source": true,
 "offsite_hint": false,
 "target": "app-e-api/app-e-postgres-backup"
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": false,
 "workload": "app-a-prod/deployment/app-a-backend",
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "prod": true,
 "all_same_node": false,
 "replicas": 2,
 "spread_declared": false,
 "eligible_nodes": 2,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": []
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": false,
 "workload": "app-a-prod/deployment/app-a-frontend",
 "nodes": {
  "node-b": 1,
  "node-a": 1
 },
 "prod": true,
 "all_same_node": false,
 "replicas": 2,
 "spread_declared": false,
 "eligible_nodes": 2,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": []
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": false,
 "workload": "app-a-prod/deployment/app-a-gateway",
 "nodes": {
  "node-a": 1,
  "node-b": 1
 },
 "prod": true,
 "all_same_node": false,
 "replicas": 2,
 "spread_declared": false,
 "eligible_nodes": 2,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": []
}
```

</details>
<details><summary><code>resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "anti_affinity": null,
 "single_eligible_node": false,
 "workload": "ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller",
 "nodes": {
  "node-b": 2
 },
 "prod": false,
 "all_same_node": true,
 "replicas": 2,
 "eligible_nodes": 2,
 "running": 2,
 "zones": {
  "null": 2
 },
 "topology_spread": []
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-7c4b5b58df-4v7td:cert-manager-controller</code></summary>

```json
{
 "crashloop": false,
 "rebooted": false,
 "pod": "cert-manager-7c4b5b58df-4v7td",
 "waiting": null,
 "namespace": "cert-manager",
 "restarts": 12,
 "last_reason": "Unknown",
 "exit_code": 255,
 "node_rebooted_at": null,
 "unhealthy_events": 0,
 "container": "cert-manager-controller",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.cert-manager/cert-manager-cainjector-7bf5c557bb-kbtv7:cert-manager-cainjector</code></summary>

```json
{
 "crashloop": false,
 "rebooted": false,
 "pod": "cert-manager-cainjector-7bf5c557bb-kbtv7",
 "waiting": null,
 "namespace": "cert-manager",
 "restarts": 14,
 "last_reason": "Unknown",
 "exit_code": 255,
 "node_rebooted_at": null,
 "unhealthy_events": 0,
 "container": "cert-manager-cainjector",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z"
}
```

</details>
<details><summary><code>resilience.restarts-crashloop.keda/keda-operator-85ff5bb446-lwkl6:keda-operator</code></summary>

```json
{
 "crashloop": false,
 "rebooted": false,
 "pod": "keda-operator-85ff5bb446-lwkl6",
 "waiting": null,
 "namespace": "keda",
 "restarts": 10,
 "last_reason": "Unknown",
 "exit_code": 255,
 "node_rebooted_at": null,
 "unhealthy_events": 0,
 "container": "keda-operator",
 "cause": "Unknown",
 "last_finished": "2026-10-28T19:25:01Z"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres</code></summary>

```json
{
 "workload": "app-a-prod/statefulset/app-a-postgres",
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis</code></summary>

```json
{
 "workload": "app-a-prod/statefulset/app-a-redis",
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "workload": "app-c-prod/deployment/app-c-coturn",
 "pin_reasons": [
  "hostNetwork"
 ],
 "prod": true,
 "serves_traffic": false,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-signaling</code></summary>

```json
{
 "workload": "app-c-prod/deployment/app-c-signaling",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/deployment/app-c-web</code></summary>

```json
{
 "workload": "app-c-prod/deployment/app-c-web",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "pin_reasons": [
  "local-path volumeClaimTemplate postgres-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 2,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-admin</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-admin",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-mx</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-mx",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-mx-worker</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-mx-worker",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": false,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-vn</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-vn",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-vn-worker</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-vn-worker",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": false,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/deployment/app-d-worker</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-worker",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": false,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-mx</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres-mx",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-mx-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-postgres-vn</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres-vn",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-postgres-vn-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-d-prod/statefulset/app-d-redis</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-redis",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-d-redis-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-e-api/statefulset/app-e-minio</code></summary>

```json
{
 "workload": "app-e-api/statefulset/app-e-minio",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-e-minio-data"
 ],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-e-api/statefulset/app-e-postgres</code></summary>

```json
{
 "workload": "app-e-api/statefulset/app-e-postgres",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-e-postgres-data"
 ],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-admin",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 3,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-api-server</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-api-server",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 3,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-app-x-client</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-app-x-client",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 2,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-embed</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-embed",
 "pin_reasons": [
  "extended resource nvidia.com/gpu"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-excel-agent</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-excel-agent",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/deployment/app-f-app-w</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-app-w",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-mysql</code></summary>

```json
{
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "pin_reasons": [
  "local-path volumeClaimTemplate mysql-backup",
  "local-path volumeClaimTemplate mysql-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-f-prod/statefulset/app-f-qdrant</code></summary>

```json
{
 "workload": "app-f-prod/statefulset/app-f-qdrant",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-f-qdrant-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-a'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/deployment/kibana</code></summary>

```json
{
 "workload": "logging/deployment/kibana",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.logging/statefulset/elasticsearch</code></summary>

```json
{
 "workload": "logging/statefulset/elasticsearch",
 "pin_reasons": [
  "local-path volumeClaimTemplate data"
 ],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-prod/deployment/app-g</code></summary>

```json
{
 "workload": "app-g-prod/deployment/app-g",
 "pin_reasons": [],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-a"
 ],
 "constraints": [
  "required nodeAffinity [{\"matchExpressions\": [{\"key\": \"role\", \"operator\": \"NotIn\", \"values\": [\"observability\"]}]}]"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-g-prod/statefulset/app-g-postgres</code></summary>

```json
{
 "workload": "app-g-prod/statefulset/app-g-postgres",
 "pin_reasons": [
  "local-path volumeClaimTemplate app-g-postgres-data"
 ],
 "prod": true,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'storage': 'node-b'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana</code></summary>

```json
{
 "workload": "monitoring/deployment/kube-prometheus-stack-grafana",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics</code></summary>

```json
{
 "workload": "monitoring/deployment/kube-prometheus-stack-kube-state-metrics",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator</code></summary>

```json
{
 "workload": "monitoring/deployment/kube-prometheus-stack-operator",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager</code></summary>

```json
{
 "workload": "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "workload": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "pin_reasons": [],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'role': 'observability'}"
 ]
}
```

</details>
<details><summary><code>resilience.single-eligible-node.registry/statefulset/registry</code></summary>

```json
{
 "workload": "registry/statefulset/registry",
 "pin_reasons": [
  "local-path volumeClaimTemplate registry-data"
 ],
 "prod": false,
 "serves_traffic": true,
 "replicas": 1,
 "nodes_total": 2,
 "eligible_nodes": [
  "node-b"
 ],
 "constraints": [
  "nodeSelector {'kubernetes.io/hostname': 'node-b'}"
 ]
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
  "cpu_throttle_ratio_5m": 0.4470046082949309
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
   "cpu_throttle_ratio_5m": 0.28493150684931506
  }
 },
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-nnsb5",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_5m": 0.2735321528424977
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
  "cpu_throttle_ratio_5m": 0.4079372404245501
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
  "cpu_throttle_ratio_5m": 0.5207823960880196
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
 "prod": false,
 "mounted_by": [],
 "keys": [
  "JWT_RELAY_SECRET",
  "JWT_SECRET",
  "TWITTER_CLIENT_SECRET",
  "TWITTER_CLIENT_SECRET_RELAY"
 ],
 "target": "default/configmap/app-y-backend-config"
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/cronjob/es-index-retention:retention</code></summary>

```json
{
 "prod": false,
 "container": "retention",
 "workload": "logging/cronjob/es-index-retention",
 "env_names": [
  "ELASTIC_PASSWORD"
 ]
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/deployment/kibana:kibana</code></summary>

```json
{
 "prod": false,
 "container": "kibana",
 "workload": "logging/deployment/kibana",
 "env_names": [
  "ELASTICSEARCH_PASSWORD"
 ]
}
```

</details>
<details><summary><code>security.plaintext-secret-env.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "prod": false,
 "container": "elasticsearch",
 "workload": "logging/statefulset/elasticsearch",
 "env_names": [
  "ELASTIC_PASSWORD"
 ]
}
```

</details>
<details><summary><code>security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "system": false,
 "flags": [
  "hostNetwork"
 ],
 "workload": "app-c-prod/deployment/app-c-coturn",
 "root_allowed_containers": [
  "coturn"
 ],
 "host_access": true,
 "severe": false
}
```

</details>
<details><summary><code>storage.local-path-fs-near-full.cluster</code></summary>

```json
{
 "fs_min_days_to_full": 842,
 "fs": {
  "node-a": {
   "avail_ratio": 0.228,
   "size_gib": 106.7,
   "growth_gib_per_day": -0.48,
   "avail_gib": 24.3,
   "days_to_full": null,
   "volumes_gib": 6.0
  },
  "node-b": {
   "avail_ratio": 0.5,
   "size_gib": 454.9,
   "growth_gib_per_day": 0.27,
   "avail_gib": 227.4,
   "days_to_full": 842,
   "volumes_gib": 137.0
  }
 },
 "over_capacity_count": 2,
 "fs_min_avail_ratio": 0.228,
 "by_node": {
  "node-a": 7,
  "node-b": 19
 },
 "metrics_available": true,
 "pv_count": 26
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-a</code></summary>

```json
{
 "ci_heavy": true,
 "ci_pods": 1,
 "prod_pods": 32,
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "cpu_saturated_minutes_7d": 0.0,
 "node": "node-a",
 "shares_ci_prod": true,
 "memory_limit_overcommit": 1.04,
 "separation_possible": false,
 "pool": "(no-pool)",
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
 "ci_heavy": true,
 "ci_pods": 2,
 "prod_pods": 15,
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ],
 "cpu_saturated_minutes_7d": 0.0,
 "node": "node-b",
 "shares_ci_prod": true,
 "memory_limit_overcommit": 0.99,
 "separation_possible": false,
 "pool": "(no-pool)",
 "ci_pod_list": [
  {
   "pod": "ci-runner-8tt2w-4w6rk",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  },
  {
   "pod": "ci-runner-8tt2w-d9kmt",
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
 "has_limitrange": false,
 "limitrange_default_request": false,
 "hard": {
  "count/pods": "200",
  "limits.memory": "80Gi",
  "requests.memory": "60Gi"
 },
 "requires_requests": true,
 "containers_without_requests": 0,
 "target": "app-a-prod/app-a-prod-quota"
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota</code></summary>

```json
{
 "has_limitrange": false,
 "limitrange_default_request": false,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "20Gi"
 },
 "requires_requests": true,
 "containers_without_requests": 0,
 "target": "app-b-prod/app-b-prod-quota"
}
```

</details>
<details><summary><code>tenancy.quota-without-limitrange.app-i-prod/app-i-prod-quota</code></summary>

```json
{
 "has_limitrange": false,
 "limitrange_default_request": false,
 "hard": {
  "limits.cpu": "4",
  "limits.memory": "8Gi",
  "persistentvolumeclaims": "2",
  "requests.cpu": "2",
  "requests.memory": "4Gi",
  "requests.storage": "30Gi"
 },
 "requires_requests": true,
 "containers_without_requests": 0,
 "target": "app-i-prod/app-i-prod-quota"
}
```

</details>
<details><summary><code>controlplane.etcd-slow.cluster</code></summary>

```json
{
 "max_ms": 1160.074888,
 "readindex_slow": 13,
 "leader_changed": 0,
 "apply_took_too_long": 191,
 "request_stats_slow": 170
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "upstreams": [
  "1.1.1.1:53",
  "8.8.8.8:53"
 ],
 "forward_nxdomain_ratio": 0.825,
 "pods_default_ndots": 153,
 "cache_hit_ratio": 0.85,
 "qps_total": 31.22,
 "nxdomain_ratio": 0.698,
 "metrics_available": true,
 "autopath": false
}
```

</details>
<details><summary><code>eso.store-static-credentials.cluster</code></summary>

```json
{
 "externalsecrets": 39,
 "externalsecrets_prod": 33,
 "stores_auth": {
  "ClusterSecretStore/aws-secret-store": "static-key(Secret)"
 },
 "stores_static_key": [
  "ClusterSecretStore/aws-secret-store"
 ],
 "providers": [
  "aws"
 ]
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "image": "arizephoenix/phoenix:latest",
 "pull_policy": "IfNotPresent",
 "workload": "app-a-prod/deployment/app-a-phoenix",
 "mutable": true,
 "prod": true,
 "registry": "docker.io",
 "container": "phoenix",
 "tag_kind": "latest",
 "holder": false
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn</code></summary>

```json
{
 "image": "coturn/coturn:latest",
 "pull_policy": "Always",
 "workload": "app-c-prod/deployment/app-c-coturn",
 "mutable": true,
 "prod": true,
 "registry": "docker.io",
 "container": "coturn",
 "tag_kind": "latest",
 "holder": false
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.app-a-prod/daemonset/app-a-sandbox-prepull</code></summary>

```json
{
 "prod": true,
 "non_security_warning": [
  "livenessProbeMissing",
  "metadataAndInstanceMismatched",
  "priorityClassNotSet",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.app-a-prod/deployment/app-a-phoenix</code></summary>

```json
{
 "prod": true,
 "non_security_warning": [
  "deploymentMissingReplicas",
  "metadataAndInstanceMismatched",
  "missingPodDisruptionBudget",
  "priorityClassNotSet",
  "pullPolicyNotAlways",
  "topologySpreadConstraint"
 ],
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "app-a-prod/deployment/app-a-phoenix"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.app-c-prod/deployment/app-c-coturn</code></summary>

```json
{
 "prod": true,
 "non_security_warning": [
  "deploymentMissingReplicas",
  "livenessProbeMissing",
  "metadataAndInstanceMismatched",
  "missingPodDisruptionBudget",
  "priorityClassNotSet",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "security_danger": [
  "hostNetworkSet",
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "app-c-prod/deployment/app-c-coturn"
}
```

</details>
<details><summary><code>node.kubelet-reserved-missing.node-a</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-a",
  "kernel": "5.15.0-198-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 7.4,
  "loadavg": "0.33 0.48 0.51",
  "nproc": 6,
  "mem_total_gb": 31.3,
  "containerd_version": null,
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 45,
  "k3s_rss_mb": 259
 },
 "kubelet": {
  "available": true,
  "eviction_hard": {
   "imagefs.available": "5%",
   "nodefs.available": "5%"
  },
  "eviction_soft": {},
  "kube_reserved": {},
  "system_reserved": {},
  "kube_api_qps": 50,
  "kube_api_burst": 100,
  "max_pods": 110,
  "serialize_image_pulls": false,
  "reserved_missing": true,
  "eviction_memory_missing": true,
  "eviction_hard_empty": false,
  "container_log_max_size": "10Mi",
  "container_log_max_files": 5,
  "log_cap_mb": 50,
  "cgroup_driver": "systemd",
  "image_gc_high": 85,
  "image_gc_low": 80,
  "fail_swap_on": false,
  "pod_pids_limit": -1,
  "shutdown_grace_period": "0s",
  "enforce_node_allocatable": [
   "pods"
  ]
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.kubelet-reserved-missing.node-b</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-b",
  "kernel": "5.15.0-185-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 117.3,
  "loadavg": "1.47 1.74 1.56",
  "nproc": 12,
  "mem_total_gb": 30.7,
  "containerd_version": "v2.1.4-k3s1",
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 243,
  "k3s_rss_mb": 1743
 },
 "kubelet": {
  "available": true,
  "eviction_hard": {
   "imagefs.available": "5%",
   "nodefs.available": "5%"
  },
  "eviction_soft": {},
  "kube_reserved": {},
  "system_reserved": {},
  "kube_api_qps": 50,
  "kube_api_burst": 100,
  "max_pods": 110,
  "serialize_image_pulls": false,
  "reserved_missing": true,
  "eviction_memory_missing": true,
  "eviction_hard_empty": false,
  "container_log_max_size": "10Mi",
  "container_log_max_files": 5,
  "log_cap_mb": 50,
  "cgroup_driver": "systemd",
  "image_gc_high": 85,
  "image_gc_low": 80,
  "fail_swap_on": false,
  "pod_pids_limit": -1,
  "shutdown_grace_period": "0s",
  "enforce_node_allocatable": [
   "pods"
  ]
 },
 "node": "node-b"
}
```

</details>
<details><summary><code>node.pod-dir-large.monitoring/prometheus-kube-prometheus-stack-prometheus-0</code></summary>

```json
{
 "workload": "monitoring/prometheus-kube-prometheus-stack-prometheus-0",
 "uid": "2575bb27-9b7a-46a3-883d-62e65510c895",
 "pod": "prometheus-kube-prometheus-stack-prometheus-0",
 "mb": 22004,
 "node": "node-b"
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
 "value": 73.11343141203677
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
 "value": 30.573153634258993
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
  "value": 11.167899004629366
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
  "value": 7.42970456018492
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
 "value": 38.14394067129603
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
 "value": 127.37766752314788
}
```

</details>
<details><summary><code>observability.alerts-always-firing.CPUThrottlingHigh</code></summary>

```json
{
 "samples_7d": 86821.0,
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
 "ingresses": 29,
 "ingress_controller_metric_series": 0,
 "namespaces_with_app_http_metrics": [],
 "alb_cloudwatch_available": false,
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
 ]
}
```

</details>
<details><summary><code>operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn</code></summary>

```json
{
 "age_hours": 6.7,
 "status": "False",
 "name": "app-c-coturn",
 "condition": "Available",
 "namespace": "app-c-prod",
 "kind": "deployments",
 "reason": "MinimumReplicasUnavailable",
 "message": "Deployment does not have minimum availability."
}
```

</details>
<details><summary><code>platform.k3s-etcd-snapshot-local-only.node-b</code></summary>

```json
{
 "server": {
  "secrets_encryption": "Disabled, no configuration file found",
  "db_mb": 594,
  "db_kind": "etcd",
  "etcd_snapshots": [
   {
    "name": "etcd-snapshot-node-b-1793664001",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793664001",
    "size_mb": 37.6,
    "created": "2026-11-03T00:00:01Z",
    "age_h": 62.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793707204",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793707204",
    "size_mb": 37.7,
    "created": "2026-11-03T12:00:04Z",
    "age_h": 50.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793750403",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793750403",
    "size_mb": 37.8,
    "created": "2026-11-04T00:00:03Z",
    "age_h": 38.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793793600",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793793600",
    "size_mb": 37.8,
    "created": "2026-11-04T12:00:00Z",
    "age_h": 26.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793836804",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793836804",
    "size_mb": 37.9,
    "created": "2026-11-05T00:00:04Z",
    "age_h": 14.8,
    "offsite": false
   }
  ],
  "certificates": [
   {
    "file": "client-k3s-cloud-controller.crt",
    "name": "k3s-cloud-controller-manager",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-k3s-cloud-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-scheduler.crt",
    "name": "system:kube-scheduler",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-scheduler.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "kube-scheduler.crt",
    "name": "kube-scheduler",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "kube-scheduler.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-k3s-controller.crt",
    "name": "system:k3s-controller",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-k3s-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kube-apiserver.crt",
    "name": "system:apiserver",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-kube-apiserver.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "serving-kube-apiserver.crt",
    "name": "kube-apiserver",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "serving-kube-apiserver.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-admin.crt",
    "name": "system:admin",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-admin.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-controller.crt",
    "name": "system:kube-controller-manager",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "kube-controller-manager.crt",
    "name": "kube-controller-manager",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "kube-controller-manager.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client.crt",
    "name": "etcd-client",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client.crt",
    "name": "etcd-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "server-client.crt",
    "name": "etcd-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "peer-server-client.crt",
    "name": "etcd-peer-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-supervisor.crt",
    "name": "system:k3s-supervisor",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-supervisor.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kube-proxy.crt",
    "name": "system:kube-proxy",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-kube-proxy.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kubelet.crt",
    "name": "system:node:node-b",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-kubelet.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "serving-kubelet.crt",
    "name": "node-b",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "serving-kubelet.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-auth-proxy.crt",
    "name": "system:auth-proxy",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-auth-proxy.crt",
    "name": "k3s-request-header-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   }
  ],
  "certificates_expiring_90d": [],
  "certificates_raw_lines": 34,
  "snapshot_latest_age_h": 14.8,
  "snapshot_interval_h": 12.0,
  "snapshots_offsite": false,
  "certificates_min_days_left": 287
 },
 "role": "server",
 "node": "node-b"
}
```

</details>
<details><summary><code>platform.k3s-secrets-encryption-off.node-b</code></summary>

```json
{
 "server": {
  "secrets_encryption": "Disabled, no configuration file found",
  "db_mb": 594,
  "db_kind": "etcd",
  "etcd_snapshots": [
   {
    "name": "etcd-snapshot-node-b-1793664001",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793664001",
    "size_mb": 37.6,
    "created": "2026-11-03T00:00:01Z",
    "age_h": 62.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793707204",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793707204",
    "size_mb": 37.7,
    "created": "2026-11-03T12:00:04Z",
    "age_h": 50.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793750403",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793750403",
    "size_mb": 37.8,
    "created": "2026-11-04T00:00:03Z",
    "age_h": 38.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793793600",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793793600",
    "size_mb": 37.8,
    "created": "2026-11-04T12:00:00Z",
    "age_h": 26.8,
    "offsite": false
   },
   {
    "name": "etcd-snapshot-node-b-1793836804",
    "location": "file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-node-b-1793836804",
    "size_mb": 37.9,
    "created": "2026-11-05T00:00:04Z",
    "age_h": 14.8,
    "offsite": false
   }
  ],
  "certificates": [
   {
    "file": "client-k3s-cloud-controller.crt",
    "name": "k3s-cloud-controller-manager",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-k3s-cloud-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-scheduler.crt",
    "name": "system:kube-scheduler",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-scheduler.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "kube-scheduler.crt",
    "name": "kube-scheduler",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "kube-scheduler.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-k3s-controller.crt",
    "name": "system:k3s-controller",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-k3s-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kube-apiserver.crt",
    "name": "system:apiserver",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-kube-apiserver.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "serving-kube-apiserver.crt",
    "name": "kube-apiserver",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "serving-kube-apiserver.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-admin.crt",
    "name": "system:admin",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-admin.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-controller.crt",
    "name": "system:kube-controller-manager",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-controller.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "kube-controller-manager.crt",
    "name": "kube-controller-manager",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "kube-controller-manager.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client.crt",
    "name": "etcd-client",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client.crt",
    "name": "etcd-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "server-client.crt",
    "name": "etcd-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "peer-server-client.crt",
    "name": "etcd-peer-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-supervisor.crt",
    "name": "system:k3s-supervisor",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-supervisor.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kube-proxy.crt",
    "name": "system:kube-proxy",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-kube-proxy.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-kubelet.crt",
    "name": "system:node:node-b",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "client-kubelet.crt",
    "name": "k3s-client-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "serving-kubelet.crt",
    "name": "node-b",
    "usage": "ServerAuth",
    "status": "is ok",
    "expires": "2027-10-28T19:24:59Z",
    "days_left": 357
   },
   {
    "file": "serving-kubelet.crt",
    "name": "k3s-server-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   },
   {
    "file": "client-auth-proxy.crt",
    "name": "system:auth-proxy",
    "usage": "ClientAuth",
    "status": "is ok",
    "expires": "2027-08-19T20:43:51Z",
    "days_left": 287
   },
   {
    "file": "client-auth-proxy.crt",
    "name": "k3s-request-header-ca@1762754399",
    "usage": "CertSign",
    "status": "is ok",
    "expires": "2035-11-08T05:59:59Z",
    "days_left": 3290
   }
  ],
  "certificates_expiring_90d": [],
  "certificates_raw_lines": 34,
  "snapshot_latest_age_h": 14.8,
  "snapshot_interval_h": 12.0,
  "snapshots_offsite": false,
  "certificates_min_days_left": 287
 },
 "role": "server",
 "node": "node-b"
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
 "stale": true,
 "suspend": false,
 "schedule": "* * * * *",
 "interval_h": 0.016666666666666666,
 "hours_since_success": 6.4,
 "last_success": "2026-11-05T08:24:50Z",
 "last_schedule": "2026-11-05T08:25:00Z",
 "target": "app-a-prod/app-a-sandbox-watchdog"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "workload": "app-a-prod/statefulset/app-a-postgres",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "workload": "app-a-prod/statefulset/app-a-redis",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "db_probe_timeout_1s": true,
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-mx:postgres</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres-mx",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres-vn:postgres</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres-vn",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-postgres:postgres</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-postgres",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-d-prod/statefulset/app-d-redis:redis</code></summary>

```json
{
 "workload": "app-d-prod/statefulset/app-d-redis",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "db_probe_timeout_1s": true,
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-mysql:mysql</code></summary>

```json
{
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-f-prod/statefulset/app-f-qdrant:qdrant</code></summary>

```json
{
 "workload": "app-f-prod/statefulset/app-f-qdrant",
 "startup": null,
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
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": "http",
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "qdrant"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-g-prod/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "workload": "app-g-prod/statefulset/app-g-postgres",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-i-prod/deployment/app-i-postgres:postgres</code></summary>

```json
{
 "workload": "app-i-prod/deployment/app-i-postgres",
 "startup": null,
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
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
 "workload": "app-c-prod/deployment/app-c-coturn",
 "replicas": 1
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
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/deployment/app-f-embed</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "workload": "app-f-prod/deployment/app-f-embed",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/statefulset/app-f-mysql</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-b"
 ],
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "replicas": 1
}
```

</details>
<details><summary><code>resilience.single-node-dependency.app-f-prod/statefulset/app-f-qdrant</code></summary>

```json
{
 "prod": true,
 "reasons": [
  "nodeSelector kubernetes.io/hostname=node-a"
 ],
 "workload": "app-f-prod/statefulset/app-f-qdrant",
 "replicas": 1
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
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-backend:backend</code></summary>

```json
{
 "summary": "CPU HPA detected, memory request 256 → 1146 MB",
 "kubegap_reason": "memory request under by 890 MB",
 "name": "app-a-backend",
 "severity": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "memory_limit_sev": "OK",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "cpu_request_sev": "UNKNOWN",
 "cpu_limit_sev": "UNKNOWN",
 "kubegap_level": "fail",
 "target": "app-a-prod/deployment/app-a-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-umami:umami</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 497 MB",
 "kubegap_reason": "memory request under by 369 MB",
 "name": "app-a-umami",
 "severity": "WARNING",
 "memory_request_sev": "WARNING",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "app-a-prod/deployment/app-a-umami:umami"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "summary": "CPU request 0.2 → 0.062 cores, CPU limit 1.0 → none, memory request 512 → 2099 MB",
 "kubegap_reason": "memory request under by 1587 MB, CPU request over by 0.138 cores",
 "name": "app-a-postgres",
 "severity": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "OK",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "app-a-prod/statefulset/app-a-postgres:postgres"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-e-api/statefulset/app-e-minio:minio</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 582 MB",
 "kubegap_reason": "memory request under by 454 MB",
 "name": "app-e-minio",
 "severity": "WARNING",
 "memory_request_sev": "WARNING",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "app-e-api/statefulset/app-e-minio:minio"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-f-prod/deployment/app-f-embed:app</code></summary>

```json
{
 "summary": "CPU request 0.5 → 0.01 cores, CPU limit 2.0 → none, memory request 2048 → 747 MB, memory limit 4096 → 747 MB",
 "kubegap_reason": "CPU request over by 0.49 cores, memory request over by 1301 MB",
 "name": "app-f-embed",
 "severity": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "memory_limit_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "WARNING",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "app-f-prod/deployment/app-f-embed:app"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "summary": "CPU request 0.2 → 0.296 cores, CPU limit 0.6 → none, memory request 2048 → 2821 MB, memory limit 3072 → 2821 MB",
 "kubegap_reason": "memory request under by 773 MB",
 "name": "elasticsearch",
 "severity": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "memory_limit_sev": "WARNING",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "logging/statefulset/elasticsearch:elasticsearch"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus</code></summary>

```json
{
 "summary": "CPU request 0.2 → 0.109 cores, CPU limit 0.3 → none, memory request 1024 → 1544 MB",
 "kubegap_reason": "memory request under by 520 MB",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "severity": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "fail",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus"
}
```

</details>
<details><summary><code>security.polaris-security-danger.cluster</code></summary>

```json
{
 "present": true,
 "score": 75,
 "danger_check_counts": {
  "privilegeEscalationAllowed": 87,
  "runAsRootAllowed": 82,
  "sensitiveContainerEnvVar": 12,
  "hostNetworkSet": 3,
  "hostPIDSet": 3,
  "runAsPrivileged": 2,
  "clusterrolebindingClusterAdmin": 1,
  "clusterrolebindingPodExecAttach": 3,
  "rolebindingClusterAdminRole": 1,
  "rolebindingRolePodExecAttach": 2,
  "sensitiveConfigmapContent": 1,
  "clusterrolePodExecAttach": 3,
  "rolePodExecAttach": 2
 },
 "danger_workloads": [
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-d-prod/deployment/app-d",
  "arc-systems/deployment/arc-actions-runner-controller",
  "app-d-prod/deployment/app-d-mx",
  "app-c-prod/deployment/app-c-coturn",
  "app-d-prod/deployment/app-d-vn",
  "kube-system/cronjob/containerd-cleanup-node-b",
  "kube-system/cronjob/containerd-cleanup-node-a",
  "logging/cronjob/es-index-retention",
  "monitoring/daemonset/kube-prometheus-stack-prometheus-node-exporter",
  "logging/job/es-ensure-k3s-template",
  "logging/deployment/kibana",
  "registry/cronjob/registry-tag-cleanup",
  "app-a-prod/deployment/app-a-phoenix",
  "app-a-prod/pod/app-a-experiment",
  "metallb-system/daemonset/speaker",
  "app-g-prod/deployment/app-g",
  "app-a-prod/deployment/app-a-backend",
  "kube-system/deployment/local-path-provisioner",
  "app-a-prod/deployment/app-v-sales-bot",
  "app-d-prod/deployment/app-d-sales-bot",
  "acme-site/deployment/acme-site",
  "app-e-api/cronjob/app-e-postgres-backup",
  "registry/cronjob/registry-gc",
  "logging/daemonset/fluent-bit",
  "app-g-prod/job/app-g-postgres-manual-backup",
  "app-e-api/deployment/app-e-api",
  "app-h/deployment/app-h",
  "app-i-prod/deployment/app-i-api",
  "app-b-prod/deployment/app-b-backend",
  "app-d-prod/deployment/app-d-mx-worker",
  "app-d-prod/deployment/app-d-worker",
  "app-i-prod/deployment/app-i-postgres",
  "app-d-prod/deployment/app-d-admin",
  "app-h/deployment/app-h-postgres",
  "app-a-prod/deployment/app-a-umami",
  "app-f-prod/deployment/app-f-excel-agent",
  "app-d-prod/deployment/app-d-vn-worker",
  "app-f-prod/deployment/app-f-embed",
  "app-c-prod/deployment/app-c-signaling",
  "app-e-api/statefulset/app-e-minio",
  "app-f-prod/deployment/app-f-app-w",
  "app-a-prod/deployment/app-a-gateway",
  "app-c-prod/deployment/app-c-web",
  "app-a-prod/statefulset/app-a-redis",
  "app-a-prod/statefulset/app-a-postgres",
  "registry/statefulset/registry",
  "app-d-prod/statefulset/app-d-postgres",
  "app-e-api/statefulset/app-e-postgres",
  "app-c-prod/statefulset/app-c-postgres",
  "app-f-prod/statefulset/app-f-qdrant",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "logging/statefulset/elasticsearch",
  "app-d-prod/statefulset/app-d-redis",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-g-prod/statefulset/app-g-postgres",
  "app-f-prod/statefulset/app-f-mysql",
  "app-f-prod/deployment/app-f-app-x-client",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-api-server",
  "app-a-prod/cronjob/umami-report-month",
  "app-d-prod/cronjob/app-d-postgres-mx-backup",
  "app-a-prod/cronjob/app-v-autopost-ja",
  "app-a-prod/cronjob/umami-report-week",
  "app-a-prod/cronjob/app-v-radar-japan-noon",
  "app-a-prod/cronjob/app-v-digest-day",
  "app-g-prod/cronjob/app-g-postgres-backup",
  "app-a-prod/cronjob/app-v-autopost-en",
  "app-d-prod/cronjob/app-d-postgres-vn-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-d-prod/cronjob/app-d-postgres-backup",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-d-prod/cronjob/app-d-ga4-digest-week",
  "app-a-prod/cronjob/app-v-digest-week",
  "app-a-prod/cronjob/app-v-radar-global",
  "app-d-prod/cronjob/app-d-ga4-digest-month",
  "app-f-prod/cronjob/app-f-mysql-backup",
  "app-d-prod/cronjob/app-d-policy-radar",
  "app-a-prod/cronjob/umami-report-day",
  "app-d-prod/cronjob/app-d-ga4-digest-day",
  "app-a-prod/cronjob/app-v-digest-month",
  "app-a-prod/cronjob/app-v-radar-global-eu",
  "app-a-prod/cronjob/app-v-radar-japan",
  "app-a-prod/job/app-a-backend-migrate",
  "/clusterrolebinding/argocd-application-controller",
  "monitoring/rolebinding/kube-prometheus-stack-grafana",
  "reloader/deployment/reloader-reloader",
  "kube-system/daemonset/nvidia-device-plugin",
  "metallb-system/deployment/controller",
  "app-b-prod/deployment/app-b-frontend",
  "app-i-prod/deployment/app-i-web",
  "app-a-prod/deployment/app-a-frontend",
  "kube-system/deployment/coredns",
  "/clusterrolebinding/argocd-server",
  "/clusterrolebinding/keda-operator",
  "default/configmap/app-y-backend-config",
  "app-a-prod/rolebinding/app-a-sandbox-manager",
  "/clusterrole/argocd-application-controller",
  "/clusterrole/argocd-server",
  "/clusterrole/keda-operator",
  "app-a-prod/role/app-a-sandbox-manager",
  "monitoring/role/kube-prometheus-stack-grafana"
 ],
 "danger_workloads_prod": [
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-d-prod/deployment/app-d",
  "app-d-prod/deployment/app-d-mx",
  "app-c-prod/deployment/app-c-coturn",
  "app-d-prod/deployment/app-d-vn",
  "app-a-prod/deployment/app-a-phoenix",
  "app-a-prod/pod/app-a-experiment",
  "app-g-prod/deployment/app-g",
  "app-a-prod/deployment/app-a-backend",
  "app-a-prod/deployment/app-v-sales-bot",
  "app-d-prod/deployment/app-d-sales-bot",
  "app-g-prod/job/app-g-postgres-manual-backup",
  "app-i-prod/deployment/app-i-api",
  "app-b-prod/deployment/app-b-backend",
  "app-d-prod/deployment/app-d-mx-worker",
  "app-d-prod/deployment/app-d-worker",
  "app-i-prod/deployment/app-i-postgres",
  "app-d-prod/deployment/app-d-admin",
  "app-a-prod/deployment/app-a-umami",
  "app-f-prod/deployment/app-f-excel-agent",
  "app-d-prod/deployment/app-d-vn-worker",
  "app-f-prod/deployment/app-f-embed",
  "app-c-prod/deployment/app-c-signaling",
  "app-f-prod/deployment/app-f-app-w",
  "app-a-prod/deployment/app-a-gateway",
  "app-c-prod/deployment/app-c-web",
  "app-a-prod/statefulset/app-a-redis",
  "app-a-prod/statefulset/app-a-postgres",
  "app-d-prod/statefulset/app-d-postgres",
  "app-c-prod/statefulset/app-c-postgres",
  "app-f-prod/statefulset/app-f-qdrant",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "app-d-prod/statefulset/app-d-redis",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-g-prod/statefulset/app-g-postgres",
  "app-f-prod/statefulset/app-f-mysql",
  "app-f-prod/deployment/app-f-app-x-client",
  "app-f-prod/deployment/app-f-admin",
  "app-f-prod/deployment/app-f-api-server",
  "app-a-prod/cronjob/umami-report-month",
  "app-d-prod/cronjob/app-d-postgres-mx-backup",
  "app-a-prod/cronjob/app-v-autopost-ja",
  "app-a-prod/cronjob/umami-report-week",
  "app-a-prod/cronjob/app-v-radar-japan-noon",
  "app-a-prod/cronjob/app-v-digest-day",
  "app-g-prod/cronjob/app-g-postgres-backup",
  "app-a-prod/cronjob/app-v-autopost-en",
  "app-d-prod/cronjob/app-d-postgres-vn-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-d-prod/cronjob/app-d-postgres-backup",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-d-prod/cronjob/app-d-ga4-digest-week",
  "app-a-prod/cronjob/app-v-digest-week",
  "app-a-prod/cronjob/app-v-radar-global",
  "app-d-prod/cronjob/app-d-ga4-digest-month",
  "app-f-prod/cronjob/app-f-mysql-backup",
  "app-d-prod/cronjob/app-d-policy-radar",
  "app-a-prod/cronjob/umami-report-day",
  "app-d-prod/cronjob/app-d-ga4-digest-day",
  "app-a-prod/cronjob/app-v-digest-month",
  "app-a-prod/cronjob/app-v-radar-global-eu",
  "app-a-prod/cronjob/app-v-radar-japan",
  "app-a-prod/job/app-a-backend-migrate",
  "app-b-prod/deployment/app-b-frontend",
  "app-i-prod/deployment/app-i-web",
  "app-a-prod/deployment/app-a-frontend",
  "app-a-prod/rolebinding/app-a-sandbox-manager",
  "app-a-prod/role/app-a-sandbox-manager"
 ]
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-c-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 4,
 "has_quota": false,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-c-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-d-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 12,
 "has_quota": false,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-d-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-f-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 13,
 "has_quota": false,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-f-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-g-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 2,
 "has_quota": false,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-g-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>traffic.pod-not-ready.app-c-prod/app-c-coturn</code></summary>

```json
{
 "pods_below_99": 1,
 "worst_pod": "app-c-coturn-549854dfcb-jgp4h",
 "workload": "app-c-prod/app-c-coturn",
 "prod": true,
 "not_ready_minutes_24h": 1440,
 "min_ready_ratio_24h": 0.0,
 "unhealthy_events": 0
}
```

</details>
<details><summary><code>argocd.admin-account-no-sso.cluster</code></summary>

```json
{
 "sso_configured": false,
 "anonymous_enabled": false,
 "admin_enabled": true,
 "rbac_policy_default": "",
 "exec_enabled": false,
 "rbac_policy_csv_lines": 0,
 "url": null
}
```

</details>
<details><summary><code>argocd.app-out-of-sync-or-unhealthy.cluster</code></summary>

```json
{
 "applications": 18,
 "out_of_sync_prod": [],
 "last_op_failed": [],
 "conditions": [
  "ExcludedResourceWarning"
 ],
 "out_of_sync": [
  "argocd/application/root"
 ],
 "apps_with_conditions": [
  "argocd/application/app-k"
 ],
 "degraded": [],
 "unhealthy": [],
 "unhealthy_prod": [],
 "applications_prod": 10,
 "progressing": [
  "argocd/application/app-c"
 ]
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 18,
 "wildcard_projects": [
  "default"
 ],
 "projects": 2,
 "applications_prod": 10,
 "default_project_apps": 4
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.LIST</code></summary>

```json
{
 "labels": {
  "verb": "LIST"
 },
 "value": 0.7451999999999983
}
```

</details>
<details><summary><code>coredns.forward-upstream-errors.cluster</code></summary>

```json
{
 "forward_healthcheck_failures_1h": 1.0084,
 "forward_servfail_ratio": 0.0,
 "forward_servfail_1h": 0,
 "servfail_ratio": 0.0,
 "upstreams": [
  "1.1.1.1:53",
  "8.8.8.8:53"
 ],
 "max_concurrent_rejects_1h": 0.0,
 "metrics_available": true
}
```

</details>
<details><summary><code>eso.controller-single-replica.cluster</code></summary>

```json
{
 "webhook_replicas": 1,
 "cert_controller_replicas": 1,
 "webhook_ready": 1,
 "concurrent": "1",
 "cert_controller_ready": 1,
 "controller_replicas": 1,
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
 "image": "registry.acme.com/app-a-sandbox-adk:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-adk",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-c:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-c",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-express:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-express",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-go:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-go",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-nestjs:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-nestjs",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-network:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-network",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-nextjs:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-nextjs",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-python:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-python",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-python-ml:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-python-ml",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-spring:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-spring",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-sql:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-sql",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo</code></summary>

```json
{
 "image": "registry.acme.com/app-a-sandbox-todo:latest",
 "pull_policy": "Always",
 "workload": "app-a-prod/daemonset/app-a-sandbox-prepull",
 "mutable": true,
 "prod": true,
 "registry": "registry.acme.com",
 "container": "hold-todo",
 "tag_kind": "latest",
 "holder": true
}
```

</details>
<details><summary><code>hygiene.mutable-image-tag.registry/cronjob/registry-tag-cleanup:tag-cleanup</code></summary>

```json
{
 "image": "curlimages/curl:latest",
 "pull_policy": "Always",
 "workload": "registry/cronjob/registry-tag-cleanup",
 "mutable": true,
 "prod": false,
 "registry": "docker.io",
 "container": "tag-cleanup",
 "tag_kind": "latest"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.role</code></summary>

```json
{
 "prod_workloads": 0,
 "nodes_total": 2,
 "workloads": [
  "logging/deployment/kibana",
  "monitoring/deployment/kube-prometheus-stack-grafana",
  "monitoring/deployment/kube-prometheus-stack-kube-state-metrics",
  "monitoring/deployment/kube-prometheus-stack-operator",
  "logging/statefulset/elasticsearch",
  "monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager",
  "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
 ],
 "workload_count": 7,
 "well_known": false,
 "nodes_with_label": 1,
 "key": "role"
}
```

</details>
<details><summary><code>hygiene.node-label-dependency.storage</code></summary>

```json
{
 "prod_workloads": 7,
 "nodes_total": 2,
 "workloads": [
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-d-prod/statefulset/app-d-postgres",
  "app-d-prod/statefulset/app-d-postgres-mx",
  "app-d-prod/statefulset/app-d-postgres-vn",
  "app-d-prod/statefulset/app-d-redis",
  "app-e-api/statefulset/app-e-minio",
  "app-e-api/statefulset/app-e-postgres"
 ],
 "workload_count": 10,
 "well_known": false,
 "nodes_with_label": 1,
 "key": "storage"
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.registry/cronjob/registry-tag-cleanup</code></summary>

```json
{
 "prod": false,
 "non_security_warning": [
  "cpuLimitsMissing",
  "cpuRequestsMissing",
  "memoryLimitsMissing",
  "memoryRequestsMissing",
  "metadataAndInstanceMismatched",
  "priorityClassNotSet"
 ],
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "registry/cronjob/registry-tag-cleanup"
}
```

</details>
<details><summary><code>hygiene.pvc-unbound-or-unused.cluster</code></summary>

```json
{
 "pvc_unbound": [],
 "pv_released": [],
 "pvc_unused": [
  {
   "namespace": "default",
   "name": "data-app-z-db-0",
   "prod": false
  }
 ]
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
<details><summary><code>logs.signatures.containerd.image-pull-failed</code></summary>

```json
{
 "count": 4,
 "first": "2026-11-05T07:37:11Z",
 "last": "2026-11-05T07:37:11Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/node/node-a/k3s-errors-24h.log": 4
 },
 "samples": [
  "E1105 16:37:11.763079    1316 log.go:32] \"PullImage from image service failed\" err=\"rpc error: code = Unknown desc = failed to pull and unpack image \\\"docker.io/coturn/coturn:latest\\\": failed to resolve reference \\\"docker.io/coturn/coturn:l",
  "E1105 16:37:11.763137    1316 kuberuntime_image.go:42] \"Failed to pull image\" err=\"failed to pull and unpack image \\\"docker.io/coturn/coturn:latest\\\": failed to resolve reference \\\"docker.io/coturn/coturn:latest\\\": failed to do request: Hea",
  "E1105 16:37:11.763270    1316 kuberuntime_manager.go:1358] \"Unhandled Error\" err=\"container &Container{Name:coturn,Image:coturn/coturn:latest,Command:[],Args:[-n --log-file=stdout --listening-port=3478 --realm=app-c.acme.com --no-tls --no",
  "E1105 16:37:11.764405    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with ErrImagePull: \\\"failed to pull and unpack image \\\\\\\"docker.io/coturn/coturn:latest\\\\\\\": failed to resolve"
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.flush-failed</code></summary>

```json
{
 "count": 14,
 "first": "2026-11-05T07:57:36Z",
 "last": "2026-11-05T08:25:46Z",
 "warn_at": 10,
 "fail_at": 500,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 14
 },
 "samples": [
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:57:36.227818631+09:00 [2026/11/05 07:57:36] [ warn] [engine] failed to flush chunk '1-1793865445.937398232.flb', retry in 6 seconds: task_id=6, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:59:41.226279321+09:00 [2026/11/05 07:59:41] [ warn] [engine] failed to flush chunk '1-1793865568.188762065.flb', retry in 9 seconds: task_id=2, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:02:36.228455173+09:00 [2026/11/05 08:02:36] [ warn] [engine] failed to flush chunk '1-1793865745.401564306.flb', retry in 9 seconds: task_id=3, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:02:36.228470452+09:00 [2026/11/05 08:02:36] [ warn] [engine] failed to flush chunk '1-1793865746.551229232.flb', retry in 9 seconds: task_id=5, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:04:52.227523586+09:00 [2026/11/05 08:04:52] [ warn] [engine] failed to flush chunk '1-1793865881.772589890.flb', retry in 7 seconds: task_id=8, input=tail.0 > output=es.0 (out_id=0)"
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.upstream-down</code></summary>

```json
{
 "count": 11,
 "first": "2026-11-05T07:54:47Z",
 "last": "2026-11-05T08:23:31Z",
 "warn_at": 5,
 "fail_at": 200,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 11
 },
 "samples": [
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T16:54:47.226478840+09:00 [2026/11/05 07:54:47] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:02:06.226190897+09:00 [2026/11/05 08:02:06] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:02:36.226218757+09:00 [2026/11/05 08:02:36] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:03:42.226325992+09:00 [2026/11/05 08:03:42] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-nnsb5/fluent-bit] 2026-11-05T17:03:52.226277122+09:00 [2026/11/05 08:03:52] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error"
 ]
}
```

</details>
<details><summary><code>node.container-writable-layer-large.node-b</code></summary>

```json
{
 "collected": true,
 "writable_layer_max_mb": 2220,
 "writable_layers_top": [
  {
   "namespace": "logging",
   "pod": "elasticsearch-0",
   "container": "elasticsearch",
   "workload": "logging/elasticsearch-0",
   "mb": 2220
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-v-radar-japan-noon-29744817-s6d97",
   "container": "radar",
   "workload": "app-a-prod/app-v-radar-japan-noon",
   "mb": 989
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-v-radar-global-eu-29743617-lmbkc",
   "container": "radar",
   "workload": "app-a-prod/app-v-radar-global-eu",
   "mb": 968
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-v-radar-japan-29743827-l4hhn",
   "container": "radar",
   "workload": "app-a-prod/app-v-radar-japan",
   "mb": 965
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-v-radar-global-29743947-k89fp",
   "container": "radar",
   "workload": "app-a-prod/app-v-radar-global",
   "mb": 965
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-a-phoenix-56ddc584cf-znjvs",
   "container": "phoenix",
   "workload": "app-a-prod/app-a-phoenix",
   "mb": 102
  },
  {
   "namespace": "app-a-prod",
   "pod": "app-a-phoenix-56ddc584cf-znjvs",
   "container": "phoenix",
   "workload": "app-a-prod/app-a-phoenix",
   "mb": 102
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-ga4-digest-week-29892965-xbwhg",
   "container": "digest",
   "workload": "app-d-prod/app-d-ga4-digest-week",
   "mb": 42
  },
  {
   "namespace": "app-d-prod",
   "pod": "app-d-ga4-digest-month-29891530-xf7v6",
   "container": "digest",
   "workload": "app-d-prod/app-d-ga4-digest-month",
   "mb": 42
  },
  {
   "namespace": "app-a-prod",
   "pod": "umami-report-week-29892960-v5hgq",
   "container": "report",
   "workload": "app-a-prod/umami-report-week",
   "mb": 37
  }
 ],
 "node": "node-b"
}
```

</details>
<details><summary><code>node.cri-exited-containers.node-a</code></summary>

```json
{
 "collected": true,
 "cri": {
  "available": true,
  "cmd": "sudo -n /usr/local/bin/k3s crictl",
  "runtime": "containerd",
  "version": "v2.1.4-k3s1",
  "states": {
   "Running": 55,
   "Exited": 69,
   "Created": 0,
   "Unknown": 0
  },
  "images": 54,
  "imagefs_used_gb": 29.5,
  "imagefs_inodes": 800040,
  "imagefs_mount": "/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs",
  "conditions": {
   "RuntimeReady": true,
   "NetworkReady": true,
   "ContainerdHasNoDeprecationWarnings": false
  },
  "not_ready": [],
  "images_top": [
   {
    "image": "registry.acme.com/app-f-embed:prod-67527dae60678e93822bf8eb71d8448f586fa0fe",
    "size_mb": 3977
   },
   {
    "image": "registry.acme.com/app-d-mexico:prod-5cd7d78054b8dcfe9f3a76cb5e3fa5bff6bada2a",
    "size_mb": 804
   },
   {
    "image": "ghcr.io/team-acme/app-d-mexico:prod-5cd7d78054b8dcfe9f3a76cb5e3fa5bff6bada2a",
    "size_mb": 804
   },
   {
    "image": "registry.acme.com/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
    "size_mb": 802
   },
   {
    "image": "ghcr.io/team-acme/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
    "size_mb": 802
   },
   {
    "image": "registry.acme.com/app-d:prod-c24abd1b7544dbf4998cdd19540e537f7a2ccdfd",
    "size_mb": 796
   },
   {
    "image": "registry.acme.com/app-a-sandbox-spring:latest",
    "size_mb": 567
   },
   {
    "image": "registry.acme.com/app-a-sandbox-todo:latest",
    "size_mb": 502
   },
   {
    "image": "registry.acme.com/app-a-sandbox-go:latest",
    "size_mb": 383
   },
   {
    "image": "registry.acme.com/app-c-web:prod-f7b662b3f5487d4cf443a654edb0526503f7db95",
    "size_mb": 335
   },
   {
    "image": "registry.acme.com/app-a-sandbox-sql:latest",
    "size_mb": 331
   },
   {
    "image": "registry.acme.com/app-a-sandbox-python-ml:latest",
    "size_mb": 330
   },
   {
    "image": "registry.acme.com/app-a-sandbox-c:latest",
    "size_mb": 307
   },
   {
    "image": "registry.acme.com/app-a-sandbox-nextjs:latest",
    "size_mb": 302
   },
   {
    "image": "ghcr.io/umami-software/umami:postgresql-latest",
    "size_mb": 255
   }
  ],
  "largest_image_mb": 3977,
  "images_over_3gb": [
   "registry.acme.com/app-f-embed:prod-67527dae60678e93822bf8eb71d8448f586fa0fe"
  ],
  "writable_layers_top": [
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-day-29895840-xmmd7",
    "container": "report",
    "workload": "app-a-prod/umami-report-day",
    "mb": 79
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-mx-7f466df4fb-dsdpw",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d-mx",
    "mb": 44
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-vn-766644b56d-dhklj",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d-vn",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-ga4-digest-day-29897280-544h5",
    "container": "digest",
    "workload": "app-d-prod/app-d-ga4-digest-day",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-5fc9656f46-r5stq",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-5fc9656f46-dr4nw",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d",
    "mb": 42
   },
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-month-29846880-rcgdq",
    "container": "report",
    "workload": "app-a-prod/umami-report-month",
    "mb": 37
   },
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-day-29897280-8mgj4",
    "container": "report",
    "workload": "app-a-prod/umami-report-day",
    "mb": 37
   },
   {
    "namespace": "app-f-prod",
    "pod": "app-f-app-x-client-7599c7f5f-79njd",
    "container": "app",
    "workload": "app-f-prod/app-f-app-x-client",
    "mb": 15
   },
   {
    "namespace": "app-f-prod",
    "pod": "app-f-app-x-client-7599c7f5f-s2b62",
    "container": "app",
    "workload": "app-f-prod/app-f-app-x-client",
    "mb": 13
   }
  ],
  "writable_layers_total_mb_top10": 393,
  "writable_layers_error": null,
  "writable_layers_available": true,
  "deprecation_warnings": true,
  "systemd_cgroup": "true",
  "snapshotter": null,
  "sandbox_image": null,
  "cni_error": null
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.cri-exited-containers.node-b</code></summary>

```json
{
 "collected": true,
 "cri": {
  "available": true,
  "cmd": "sudo -n /usr/local/bin/k3s crictl",
  "runtime": "containerd",
  "version": "v2.1.4-k3s1",
  "states": {
   "Running": 69,
   "Exited": 93,
   "Created": 0,
   "Unknown": 0
  },
  "images": 61,
  "imagefs_used_gb": 25.5,
  "imagefs_inodes": 738647,
  "imagefs_mount": "/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs",
  "conditions": {
   "RuntimeReady": true,
   "NetworkReady": true,
   "ContainerdHasNoDeprecationWarnings": false
  },
  "not_ready": [],
  "images_top": [
   {
    "image": "registry.acme.com/app-a-sandbox-spring:latest",
    "size_mb": 567
   },
   {
    "image": "registry.acme.com/app-a-sandbox-todo:latest",
    "size_mb": 502
   },
   {
    "image": "docker.elastic.co/elasticsearch/elasticsearch:7.10.2",
    "size_mb": 435
   },
   {
    "image": "docker.io/summerwind/actions-runner:latest",
    "size_mb": 428
   },
   {
    "image": "docker.elastic.co/kibana/kibana:7.10.2",
    "size_mb": 417
   },
   {
    "image": "registry.acme.com/app-a-sandbox-go:latest",
    "size_mb": 383
   },
   {
    "image": "registry.acme.com/app-h:prod-76ad4be247b5cdcd0b8abf0c41f192c43d7aa6a7",
    "size_mb": 374
   },
   {
    "image": "registry.acme.com/app-a-sandbox-sql:latest",
    "size_mb": 331
   },
   {
    "image": "registry.acme.com/app-a-sandbox-python-ml:latest",
    "size_mb": 330
   },
   {
    "image": "registry.acme.com/app-a-sandbox-c:latest",
    "size_mb": 307
   },
   {
    "image": "docker.io/arizephoenix/phoenix:latest",
    "size_mb": 306
   },
   {
    "image": "registry.acme.com/app-a-sandbox-nextjs:latest",
    "size_mb": 302
   },
   {
    "image": "registry.acme.com/app-a-sandbox-adk:latest",
    "size_mb": 254
   },
   {
    "image": "registry.acme.com/app-a-sandbox-python:latest",
    "size_mb": 251
   },
   {
    "image": "registry.acme.com/app-a-sandbox-network:latest",
    "size_mb": 250
   }
  ],
  "largest_image_mb": 567,
  "images_over_3gb": [],
  "writable_layers_top": [
   {
    "namespace": "logging",
    "pod": "elasticsearch-0",
    "container": "elasticsearch",
    "workload": "logging/elasticsearch-0",
    "mb": 2220
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-v-radar-japan-noon-29744817-s6d97",
    "container": "radar",
    "workload": "app-a-prod/app-v-radar-japan-noon",
    "mb": 989
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-v-radar-global-eu-29743617-lmbkc",
    "container": "radar",
    "workload": "app-a-prod/app-v-radar-global-eu",
    "mb": 968
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-v-radar-japan-29743827-l4hhn",
    "container": "radar",
    "workload": "app-a-prod/app-v-radar-japan",
    "mb": 965
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-v-radar-global-29743947-k89fp",
    "container": "radar",
    "workload": "app-a-prod/app-v-radar-global",
    "mb": 965
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-a-phoenix-56ddc584cf-znjvs",
    "container": "phoenix",
    "workload": "app-a-prod/app-a-phoenix",
    "mb": 102
   },
   {
    "namespace": "app-a-prod",
    "pod": "app-a-phoenix-56ddc584cf-znjvs",
    "container": "phoenix",
    "workload": "app-a-prod/app-a-phoenix",
    "mb": 102
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-ga4-digest-week-29892965-xbwhg",
    "container": "digest",
    "workload": "app-d-prod/app-d-ga4-digest-week",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-ga4-digest-month-29891530-xf7v6",
    "container": "digest",
    "workload": "app-d-prod/app-d-ga4-digest-month",
    "mb": 42
   },
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-week-29892960-v5hgq",
    "container": "report",
    "workload": "app-a-prod/umami-report-week",
    "mb": 37
   }
  ],
  "writable_layers_total_mb_top10": 6432,
  "writable_layers_error": null,
  "writable_layers_available": true,
  "deprecation_warnings": true,
  "systemd_cgroup": "true",
  "snapshotter": null,
  "sandbox_image": null,
  "cni_error": null
 },
 "node": "node-b"
}
```

</details>
<details><summary><code>node.kubelet-eviction-memory-missing.node-a</code></summary>

```json
{
 "collected": true,
 "kubelet": {
  "available": true,
  "eviction_hard": {
   "imagefs.available": "5%",
   "nodefs.available": "5%"
  },
  "eviction_soft": {},
  "kube_reserved": {},
  "system_reserved": {},
  "kube_api_qps": 50,
  "kube_api_burst": 100,
  "max_pods": 110,
  "serialize_image_pulls": false,
  "reserved_missing": true,
  "eviction_memory_missing": true,
  "eviction_hard_empty": false,
  "container_log_max_size": "10Mi",
  "container_log_max_files": 5,
  "log_cap_mb": 50,
  "cgroup_driver": "systemd",
  "image_gc_high": 85,
  "image_gc_low": 80,
  "fail_swap_on": false,
  "pod_pids_limit": -1,
  "shutdown_grace_period": "0s",
  "enforce_node_allocatable": [
   "pods"
  ]
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.kubelet-eviction-memory-missing.node-b</code></summary>

```json
{
 "collected": true,
 "kubelet": {
  "available": true,
  "eviction_hard": {
   "imagefs.available": "5%",
   "nodefs.available": "5%"
  },
  "eviction_soft": {},
  "kube_reserved": {},
  "system_reserved": {},
  "kube_api_qps": 50,
  "kube_api_burst": 100,
  "max_pods": 110,
  "serialize_image_pulls": false,
  "reserved_missing": true,
  "eviction_memory_missing": true,
  "eviction_hard_empty": false,
  "container_log_max_size": "10Mi",
  "container_log_max_files": 5,
  "log_cap_mb": 50,
  "cgroup_driver": "systemd",
  "image_gc_high": 85,
  "image_gc_low": 80,
  "fail_swap_on": false,
  "pod_pids_limit": -1,
  "shutdown_grace_period": "0s",
  "enforce_node_allocatable": [
   "pods"
  ]
 },
 "node": "node-b"
}
```

</details>
<details><summary><code>node.service-restarts.node-b</code></summary>

```json
{
 "meta": {
  "root": false,
  "hostname": "node-b",
  "kernel": "5.15.0-185-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 117.3,
  "loadavg": "1.47 1.74 1.56",
  "nproc": 12,
  "mem_total_gb": 30.7,
  "containerd_version": "v2.1.4-k3s1",
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 243,
  "k3s_rss_mb": 1743
 },
 "service_restarts_max": 5,
 "node": "node-b",
 "service_restarts": {
  "kubelet": 0,
  "containerd": 0,
  "k3s": 5
 },
 "services": [
  {
   "unit": "kubelet",
   "active": "inactive",
   "restarts": 0,
   "since": "n/a"
  },
  {
   "unit": "containerd",
   "active": "inactive",
   "restarts": 0,
   "since": "n/a"
  },
  {
   "unit": "k3s",
   "active": "active",
   "restarts": 5,
   "since": "Wed 2026-10-28 19:25:12 UTC"
  }
 ],
 "collected": true
}
```

</details>
<details><summary><code>node.sysctl-tuning.node-a</code></summary>

```json
{
 "collected": true,
 "sysctl": {
  "values": {
   "net.netfilter.nf_conntrack_max": "196608",
   "net.netfilter.nf_conntrack_count": "2010",
   "net.netfilter.nf_conntrack_tcp_timeout_established": "86400",
   "fs.inotify.max_user_watches": "247744",
   "fs.inotify.max_user_instances": "128",
   "fs.file-max": "9223372036854775807",
   "fs.file-nr": "6048 0 9223372036854775807",
   "fs.aio-max-nr": "65536",
   "net.core.somaxconn": "4096",
   "net.core.netdev_max_backlog": "1000",
   "net.ipv4.ip_local_port_range": "32768 60999",
   "net.ipv4.tcp_max_syn_backlog": "2048",
   "net.ipv4.tcp_tw_reuse": "2",
   "net.ipv4.ip_forward": "1",
   "net.bridge.bridge-nf-call-iptables": "1",
   "net.ipv4.neigh.default.gc_thresh3": "1024",
   "vm.max_map_count": "262144",
   "vm.swappiness": "60",
   "vm.overcommit_memory": "1",
   "vm.panic_on_oom": "0",
   "kernel.panic": "10",
   "kernel.panic_on_oops": "1",
   "kernel.pid_max": "4194304",
   "kernel.threads-max": "253293",
   "kernel.dmesg_restrict": "1"
  },
  "issues": [
   "fs.inotify.max_user_instances=128 (recommended ≥ 512, k3s docs 8192; nodes with many pods/log collectors hit 'too many open files')",
   "fs.inotify.max_user_watches=247744 (recommended ≥ 524288)"
  ]
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.sysctl-tuning.node-b</code></summary>

```json
{
 "collected": true,
 "sysctl": {
  "values": {
   "net.netfilter.nf_conntrack_max": "393216",
   "net.netfilter.nf_conntrack_count": "3931",
   "net.netfilter.nf_conntrack_tcp_timeout_established": "86400",
   "fs.inotify.max_user_watches": "244476",
   "fs.inotify.max_user_instances": "128",
   "fs.file-max": "9223372036854775807",
   "fs.file-nr": "10592 0 9223372036854775807",
   "fs.aio-max-nr": "65536",
   "net.core.somaxconn": "4096",
   "net.core.netdev_max_backlog": "1000",
   "net.ipv4.ip_local_port_range": "32768 60999",
   "net.ipv4.tcp_max_syn_backlog": "2048",
   "net.ipv4.tcp_tw_reuse": "2",
   "net.ipv4.ip_forward": "1",
   "net.bridge.bridge-nf-call-iptables": "1",
   "net.ipv4.neigh.default.gc_thresh3": "1024",
   "vm.max_map_count": "65530",
   "vm.swappiness": "60",
   "vm.overcommit_memory": "1",
   "vm.panic_on_oom": "0",
   "kernel.panic": "10",
   "kernel.panic_on_oops": "1",
   "kernel.pid_max": "4194304",
   "kernel.threads-max": "250685",
   "kernel.dmesg_restrict": "1"
  },
  "issues": [
   "fs.inotify.max_user_instances=128 (recommended ≥ 512, k3s docs 8192; nodes with many pods/log collectors hit 'too many open files')",
   "fs.inotify.max_user_watches=244476 (recommended ≥ 524288)",
   "vm.max_map_count=65530 (Elasticsearch/OpenSearch runs in this cluster; requires 262144. Without an init container raising it, bootstrap checks fail or it falls back to single-node mode)"
  ]
 },
 "node": "node-b"
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
 "value": 3.145028634258994
}
```

</details>
<details><summary><code>observability.fluentbit-output-errors.cluster</code></summary>

```json
{
 "records_in_1h": null,
 "retries_failed_1h": null,
 "output_errors_1h": null,
 "metrics_scraped": false,
 "dropped_records_1h": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-backend</code></summary>

```json
{
 "ingress": "app-a-backend",
 "namespace": "app-a-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "api.app-a.acme.com",
  "api.example-a.dev"
 ],
 "services": [
  "app-a-backend"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-frontend</code></summary>

```json
{
 "ingress": "app-a-frontend",
 "namespace": "app-a-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-a.acme.com",
  "example-a.dev",
  "www.example-a.dev"
 ],
 "services": [
  "app-a-frontend"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-phoenix</code></summary>

```json
{
 "ingress": "app-a-phoenix",
 "namespace": "app-a-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "obs.example-a.dev"
 ],
 "services": [
  "app-a-phoenix"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-a-prod/app-a-umami</code></summary>

```json
{
 "ingress": "app-a-umami",
 "namespace": "app-a-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "umami.example-a.dev",
  "umami.example-l.com"
 ],
 "services": [
  "app-a-umami"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.argocd/argocd-server-ingress</code></summary>

```json
{
 "ingress": "argocd-server-ingress",
 "namespace": "argocd",
 "source": null,
 "hosts": [
  "argocd.acme.com"
 ],
 "services": [
  "argocd-server"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-backend</code></summary>

```json
{
 "ingress": "app-b-backend",
 "namespace": "app-b-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-b-api.acme.com"
 ],
 "services": [
  "app-b-backend"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-b-prod/app-b-frontend</code></summary>

```json
{
 "ingress": "app-b-frontend",
 "namespace": "app-b-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-b.acme.com"
 ],
 "services": [
  "app-b-frontend"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-signaling-ingress</code></summary>

```json
{
 "ingress": "app-c-signaling-ingress",
 "namespace": "app-c-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.acme.com",
  "example-h.space",
  "www.example-h.space"
 ],
 "services": [
  "app-c-signaling-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-c-prod/app-c-web-ingress</code></summary>

```json
{
 "ingress": "app-c-web-ingress",
 "namespace": "app-c-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-c.acme.com",
  "example-h.space",
  "www.example-h.space"
 ],
 "services": [
  "app-c-web-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.acme-site/acme-site</code></summary>

```json
{
 "ingress": "acme-site",
 "namespace": "acme-site",
 "source": null,
 "hosts": [
  "acme.com"
 ],
 "services": [
  "acme-site"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-admin-ingress</code></summary>

```json
{
 "ingress": "app-d-admin-ingress",
 "namespace": "app-d-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "admin.example-e.com"
 ],
 "services": [
  "app-d-admin-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-ingress</code></summary>

```json
{
 "ingress": "app-d-ingress",
 "namespace": "app-d-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app.example-e.com"
 ],
 "services": [
  "app-d-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-mx-ingress</code></summary>

```json
{
 "ingress": "app-d-mx-ingress",
 "namespace": "app-d-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "mx.example-e.com"
 ],
 "services": [
  "app-d-mx-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-d-prod/app-d-vn-ingress</code></summary>

```json
{
 "ingress": "app-d-vn-ingress",
 "namespace": "app-d-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "vn.example-e.com"
 ],
 "services": [
  "app-d-vn-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-e-api/app-e-api</code></summary>

```json
{
 "ingress": "app-e-api",
 "namespace": "app-e-api",
 "source": null,
 "hosts": [
  "app-e-api.acme.com",
  "app-e-cdn.acme.com"
 ],
 "services": [
  "app-e-api",
  "app-e-minio"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-admin-ingress</code></summary>

```json
{
 "ingress": "app-f-admin-ingress",
 "namespace": "app-f-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-admin-prod.acme.com",
  "example-f.com",
  "www.example-f.com"
 ],
 "services": [
  "app-f-admin-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-api-server-ingress</code></summary>

```json
{
 "ingress": "app-f-api-server-ingress",
 "namespace": "app-f-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-api-prod.acme.com"
 ],
 "services": [
  "app-f-api-server-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-api-server-oauth-ingress</code></summary>

```json
{
 "ingress": "app-f-api-server-oauth-ingress",
 "namespace": "app-f-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "example-k.kr",
  "www.example-k.kr"
 ],
 "services": [
  "app-f-api-server-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-app-x-client-ingress</code></summary>

```json
{
 "ingress": "app-f-app-x-client-ingress",
 "namespace": "app-f-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-app-x-client-prod.acme.com",
  "example-k.kr",
  "www.example-k.kr"
 ],
 "services": [
  "app-f-app-x-client-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-f-prod/app-f-app-w-ingress</code></summary>

```json
{
 "ingress": "app-f-app-w-ingress",
 "namespace": "app-f-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-f-app-w-prod.acme.com",
  "example-g.com",
  "www.example-g.com"
 ],
 "services": [
  "app-f-app-w-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.logging/kibana</code></summary>

```json
{
 "ingress": "kibana",
 "namespace": "logging",
 "source": null,
 "hosts": [
  "kibana.acme.com"
 ],
 "services": [
  "kibana"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-g-prod/app-g-ingress</code></summary>

```json
{
 "ingress": "app-g-ingress",
 "namespace": "app-g-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "app-g.acme.com",
  "example-j.com",
  "www.example-j.com"
 ],
 "services": [
  "app-g-svc"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.monitoring/monitoring-grafana-ingress</code></summary>

```json
{
 "ingress": "monitoring-grafana-ingress",
 "namespace": "monitoring",
 "source": null,
 "hosts": [
  "grafana.acme.com"
 ],
 "services": [
  "kube-prometheus-stack-grafana"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-h/app-h</code></summary>

```json
{
 "ingress": "app-h",
 "namespace": "app-h",
 "source": null,
 "hosts": [
  "app-h.acme.com"
 ],
 "services": [
  "app-h"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.registry/registry</code></summary>

```json
{
 "ingress": "registry",
 "namespace": "registry",
 "source": null,
 "hosts": [
  "registry.acme.com"
 ],
 "services": [
  "registry"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-k/app-k</code></summary>

```json
{
 "ingress": "app-k",
 "namespace": "app-k",
 "source": null,
 "hosts": [
  "app-k.acme.com"
 ],
 "services": [
  "app-k-workstation"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-k/app-k-auth</code></summary>

```json
{
 "ingress": "app-k-auth",
 "namespace": "app-k",
 "source": null,
 "hosts": [
  "app-k.acme.com"
 ],
 "services": [
  "app-k-workstation"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-i-prod/app-i-api</code></summary>

```json
{
 "ingress": "app-i-api",
 "namespace": "app-i-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "api.example-i.dev"
 ],
 "services": [
  "app-i-api"
 ]
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-i-prod/app-i-web</code></summary>

```json
{
 "ingress": "app-i-web",
 "namespace": "app-i-prod",
 "source": null,
 "cluster_ic_metrics": false,
 "hosts": [
  "example-i.dev"
 ],
 "services": [
  "app-i-web"
 ]
}
```

</details>
<details><summary><code>observability.page-severity-cause-alerts.cluster</code></summary>

```json
{
 "by_class": {
  "cause": 153,
  "app-cause": 1,
  "app": 7
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
 ],
 "alerting": 161,
 "by_severity": {
  "warning": 106,
  "critical": 46,
  "none": 2,
  "info": 7
 }
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-backup</code></summary>

```json
{
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "backoff_limit": null,
 "active_deadline_s": null,
 "starting_deadline_s": null,
 "pod_failure_policy": false,
 "prod": true,
 "suspend": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "concurrency_policy": "Allow",
 "target": "app-d-prod/app-d-postgres-backup"
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-mx-backup</code></summary>

```json
{
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "backoff_limit": null,
 "active_deadline_s": null,
 "starting_deadline_s": null,
 "pod_failure_policy": false,
 "prod": true,
 "suspend": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "concurrency_policy": "Allow",
 "target": "app-d-prod/app-d-postgres-mx-backup"
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-d-prod/app-d-postgres-vn-backup</code></summary>

```json
{
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "backoff_limit": null,
 "active_deadline_s": null,
 "starting_deadline_s": null,
 "pod_failure_policy": false,
 "prod": true,
 "suspend": false,
 "schedule": "30 3 * * *",
 "ttl_s": null,
 "concurrency_policy": "Allow",
 "target": "app-d-prod/app-d-postgres-vn-backup"
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-f-prod/app-f-mysql-backup</code></summary>

```json
{
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "backoff_limit": null,
 "active_deadline_s": null,
 "starting_deadline_s": null,
 "pod_failure_policy": false,
 "prod": true,
 "suspend": false,
 "schedule": "50 2 * * *",
 "ttl_s": null,
 "concurrency_policy": "Allow",
 "target": "app-f-prod/app-f-mysql-backup"
}
```

</details>
<details><summary><code>resilience.cronjob-policy.app-g-prod/app-g-postgres-backup</code></summary>

```json
{
 "active_jobs": 0,
 "policy_gaps": [
  "concurrencyPolicy Allow (overlap allowed)",
  "activeDeadlineSeconds missing (a stuck Job runs forever)",
  "backoffLimit default 6 and no podFailurePolicy",
  "startingDeadlineSeconds missing (the controller stops after 100 missed schedules)"
 ],
 "backoff_limit": null,
 "active_deadline_s": null,
 "starting_deadline_s": null,
 "pod_failure_policy": false,
 "prod": true,
 "suspend": false,
 "schedule": "0 3 * * *",
 "ttl_s": null,
 "concurrency_policy": "Allow",
 "target": "app-g-prod/app-g-postgres-backup"
}
```

</details>
<details><summary><code>resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog</code></summary>

```json
{
 "active_jobs": 1,
 "median_job_duration_s": 50,
 "suspend": false,
 "schedule": "* * * * *",
 "interval_h": 0.016666666666666666,
 "runtime_over_interval": 0.83,
 "jobs_timed": 1,
 "max_job_duration_s": 50,
 "concurrency_policy": "Forbid",
 "target": "app-a-prod/app-a-sandbox-watchdog"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-e-api/statefulset/app-e-postgres:postgres</code></summary>

```json
{
 "workload": "app-e-api/statefulset/app-e-postgres",
 "startup": null,
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-h/deployment/app-h-postgres:postgres</code></summary>

```json
{
 "workload": "app-h/deployment/app-h-postgres",
 "startup": null,
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "db_probe_timeout_1s": true,
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.priority-inversion.cluster</code></summary>

```json
{
 "nonprod_max_priority": 0,
 "user_classes": [],
 "preempted_events": 0,
 "inversion": [],
 "prod_max_priority": 0,
 "prod_pods": 49,
 "no_user_classes_with_prod": true,
 "pods_by_class": {
  "(none, 0)": 92,
  "system-cluster-critical": 1,
  "system-node-critical": 3
 },
 "prod_pods_without_class": 49
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.cluster</code></summary>

```json
{
 "prod_db_without_backup_cronjob": [
  "app-c-prod/statefulset/app-c-postgres",
  "app-i-prod/deployment/app-i-postgres"
 ],
 "count": 7,
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
 ],
 "db_workloads_with_pvc": 16
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
 "workload": "registry/statefulset/registry",
 "replicas": 1
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
   "cpu_request_p95_ratio_7d": 0.02092298593595122,
   "cpu_p95_7d_cores": 0.002092298593595122,
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
   "cpu_request_p95_ratio_7d": 0.15089379258227706,
   "cpu_p95_7d_cores": 0.015089379258227707,
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
  "cpu_request_p95_ratio_7d": 0.00313948484828899,
  "cpu_p95_7d_cores": 0.000313948484828899,
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
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-c"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-express"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-go"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-network"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-python"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-frontend:frontend</code></summary>

```json
{
 "summary": "CPU HPA detected, memory request 128 → 310 MB",
 "kubegap_reason": "memory request under by 182 MB",
 "name": "app-a-frontend",
 "severity": "OK",
 "memory_request_sev": "OK",
 "memory_limit_sev": "OK",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "cpu_request_sev": "UNKNOWN",
 "cpu_limit_sev": "UNKNOWN",
 "kubegap_level": "warn",
 "target": "app-a-prod/deployment/app-a-frontend:frontend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB",
 "kubegap_reason": "memory request under by 68 MB",
 "name": "app-a-redis",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-a-prod/statefulset/app-a-redis:redis"
}
```

</details>
<details><summary><code>resources.krr-recommendation.acme-site/deployment/acme-site:nginx</code></summary>

```json
{
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.1 → none, memory request 16 → 100 MB",
 "kubegap_reason": "memory request under by 84 MB",
 "name": "acme-site",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "acme-site/deployment/acme-site:nginx"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-d-prod/statefulset/app-d-redis:redis</code></summary>

```json
{
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB",
 "kubegap_reason": "memory request under by 68 MB",
 "name": "app-d-redis",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-d-prod/statefulset/app-d-redis:redis"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-f-prod/deployment/app-f-excel-agent:app</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 1.0 → none, memory request 256 → 506 MB, memory limit 1024 → 506 MB",
 "kubegap_reason": "memory request under by 250 MB",
 "name": "app-f-excel-agent",
 "severity": "CRITICAL",
 "memory_request_sev": "WARNING",
 "memory_limit_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-f-prod/deployment/app-f-excel-agent:app"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-f-prod/statefulset/app-f-mysql:mysql</code></summary>

```json
{
 "summary": "CPU request 0.2 → 0.027 cores, CPU limit 1.5 → none, memory request 1600 → 1370 MB, memory limit 3200 → 1370 MB",
 "kubegap_reason": "CPU request over by 0.173 cores",
 "name": "app-f-mysql",
 "severity": "CRITICAL",
 "memory_request_sev": "OK",
 "memory_limit_sev": "CRITICAL",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "OK",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-f-prod/statefulset/app-f-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller</code></summary>

```json
{
 "summary": "CPU request 0.1 → 0.01 cores, memory request 90 → 318 MB, memory limit None → 318 MB",
 "kubegap_reason": "memory request under by 228 MB",
 "name": "nginx-ingress-ingress-nginx-controller",
 "severity": "WARNING",
 "memory_request_sev": "OK",
 "memory_limit_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "GOOD",
 "kubegap_level": "warn",
 "target": "ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/daemonset/fluent-bit:fluent-bit</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.062 cores, CPU limit 0.1 → none, memory request 50 → 144 MB",
 "kubegap_reason": "memory request under by 94 MB",
 "name": "fluent-bit",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "logging/daemonset/fluent-bit:fluent-bit"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/deployment/kibana:kibana</code></summary>

```json
{
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 446 MB, memory limit 1024 → 446 MB",
 "kubegap_reason": "CPU request over by 0.19 cores",
 "name": "kibana",
 "severity": "CRITICAL",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "OK",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "logging/deployment/kibana:kibana"
}
```

</details>
<details><summary><code>resources.krr-recommendation.registry/statefulset/registry:registry</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 128 → 283 MB",
 "kubegap_reason": "memory request under by 155 MB",
 "name": "registry",
 "severity": "WARNING",
 "memory_request_sev": "OK",
 "memory_limit_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "registry/statefulset/registry:registry"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-i-prod/deployment/app-i-web:web</code></summary>

```json
{
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 204 MB, memory limit 512 → 204 MB",
 "kubegap_reason": "memory request under by 76 MB",
 "name": "app-i-web",
 "severity": "WARNING",
 "memory_request_sev": "GOOD",
 "memory_limit_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "cpu_request_sev": "GOOD",
 "cpu_limit_sev": "WARNING",
 "kubegap_level": "warn",
 "target": "app-i-prod/deployment/app-i-web:web"
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
 "value": 33.0
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
 "default_deny_ingress_namespaces": [],
 "enforced": true
}
```

</details>
<details><summary><code>security.psa-not-enforced.cluster</code></summary>

```json
{
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
 "psa_enforced_namespaces": [
  "metallb-system"
 ],
 "root_allowed_ratio": 0.71,
 "prod_without_psa": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-d-prod",
  "app-f-prod",
  "app-g-prod",
  "app-i-prod"
 ]
}
```

</details>
<details><summary><code>security.rbac-wildcard.argocd-application-controller</code></summary>

```json
{
 "prod": false,
 "clusterrole": "argocd-application-controller",
 "bound": true,
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
 "automount_false_sa": 1,
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
 "workloads": 82,
 "token_mounted": 80,
 "service_accounts": 91
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
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
 ],
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
   "used_ratio": 0.727,
   "inode_ratio": 0.166,
   "growth_gb_per_day": -0.469,
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
   "used_ratio": 0.727,
   "inode_ratio": 0.166,
   "growth_gb_per_day": -0.47,
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
 ]
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.app-f-prod</code></summary>

```json
{
 "system": false,
 "burst_ratio_7d": 22.1,
 "cpu_p95_7d": 0.059,
 "nodes": {
  "node-a": 12,
  "node-b": 1
 },
 "shares_nodes_with_prod": true,
 "has_quota": false,
 "cpu_median_7d": 0.027,
 "cpu_limits": 8.2,
 "namespace": "app-f-prod",
 "cpu_max_7d": 0.589,
 "kind": "prod"
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-b-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 2,
 "has_quota": true,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-b-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-i-prod</code></summary>

```json
{
 "tenants_total": 12,
 "rbac_subject_count": 0,
 "prod": true,
 "pods": 3,
 "has_quota": true,
 "has_limitrange": false,
 "shares_nodes_with_prod": true,
 "networkpolicies": 0,
 "namespace": "app-i-prod",
 "networkpolicy_enforced": true,
 "psa_enforce": null
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-systems</code></summary>

```json
{
 "tenants_total": 12,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.003,
 "cpu_p95_7d": 0.004,
 "cpu_requests": 1.0,
 "prod": false,
 "pods": 3,
 "has_quota": false,
 "shares_nodes_with_prod": true,
 "namespace": "arc-systems",
 "kind": "ci",
 "memory_requests_gb": 2.0,
 "memory_p95_7d_gb": 0.36
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-c-prod</code></summary>

```json
{
 "tenants_total": 12,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.01,
 "cpu_p95_7d": 0.01,
 "cpu_requests": 0.17,
 "prod": true,
 "pods": 4,
 "has_quota": false,
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "namespace": "app-c-prod",
 "cluster_saturated_7d": false,
 "kind": "prod",
 "memory_requests_gb": 0.66,
 "memory_p95_7d_gb": 0.23
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-d-prod</code></summary>

```json
{
 "tenants_total": 12,
 "burst_ratio_7d": 1.6,
 "cpu_share_of_cluster_p95": 0.025,
 "cpu_p95_7d": 0.028,
 "cpu_requests": 0.49,
 "prod": true,
 "pods": 12,
 "has_quota": false,
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "namespace": "app-d-prod",
 "cluster_saturated_7d": false,
 "kind": "prod",
 "memory_requests_gb": 3.91,
 "memory_p95_7d_gb": 1.66
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-f-prod</code></summary>

```json
{
 "tenants_total": 12,
 "burst_ratio_7d": 22.1,
 "cpu_share_of_cluster_p95": 0.054,
 "cpu_p95_7d": 0.059,
 "cpu_requests": 1.28,
 "prod": true,
 "pods": 13,
 "has_quota": false,
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "namespace": "app-f-prod",
 "cluster_saturated_7d": false,
 "kind": "prod",
 "memory_requests_gb": 8.12,
 "memory_p95_7d_gb": 4.73
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-g-prod</code></summary>

```json
{
 "tenants_total": 12,
 "burst_ratio_7d": null,
 "cpu_share_of_cluster_p95": 0.005,
 "cpu_p95_7d": 0.006,
 "cpu_requests": 0.1,
 "prod": true,
 "pods": 2,
 "has_quota": false,
 "shares_nodes_with_prod": true,
 "multi_org": false,
 "namespace": "app-g-prod",
 "cluster_saturated_7d": false,
 "kind": "prod",
 "memory_requests_gb": 0.28,
 "memory_p95_7d_gb": 0.14
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-systems</code></summary>

```json
{
 "cpu_p95_7d": 0.004,
 "prod": false,
 "has_limitrange": false,
 "pods": 3,
 "namespace": "arc-systems",
 "kind": "ci",
 "containers_without_requests": 4,
 "memory_p95_7d_gb": 0.36,
 "containers_without_memory_limit": 4
}
```

</details>
<details><summary><code>traffic.coredns-latency.cluster</code></summary>

```json
{
 "servfail_ratio_1h": 0.0,
 "p99_s_1h": 0.1396
}
```

</details>
<details><summary><code>traffic.ingress-nginx-retired.cluster</code></summary>

```json
{
 "retired_note": "ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes",
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
 "version": "1.14.0",
 "present": true,
 "retired": true,
 "admission_webhook": true
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
 "host": "<ip>",
 "server_url": "https://<ip>:6443",
 "node": "node-b"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9981481481481481,
 "days_since_last_scale": 3.3,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-a-backend",
 "max": 6,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "namespace": "app-a-prod",
 "keda_owned": false,
 "current_cpu_utilization": 3,
 "target_cpu_utilization": 70,
 "target": "app-a-prod/deployment/app-a-backend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9979166666666667,
 "days_since_last_scale": 1.2,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-a-frontend",
 "max": 4,
 "metric_types": [
  "cpu"
 ],
 "min": 2,
 "namespace": "app-a-prod",
 "keda_owned": false,
 "current_cpu_utilization": 3,
 "target_cpu_utilization": 70,
 "target": "app-a-prod/deployment/app-a-frontend"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "days_since_last_scale": 7.7,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-d",
 "max": 5,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 2,
 "namespace": "app-d-prod",
 "keda_owned": false,
 "current_cpu_utilization": 4,
 "target_cpu_utilization": 60,
 "target": "app-d-prod/deployment/app-d"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d-mx</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "days_since_last_scale": 7.7,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-d-mx",
 "max": 4,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "namespace": "app-d-prod",
 "keda_owned": false,
 "current_cpu_utilization": 4,
 "target_cpu_utilization": 60,
 "target": "app-d-prod/deployment/app-d-mx"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-d-prod/deployment/app-d-vn</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "days_since_last_scale": 7.7,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-d-vn",
 "max": 4,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "namespace": "app-d-prod",
 "keda_owned": false,
 "current_cpu_utilization": 4,
 "target_cpu_utilization": 60,
 "target": "app-d-prod/deployment/app-d-vn"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-g-prod/deployment/app-g</code></summary>

```json
{
 "at_min_ratio_15d": 0.999537037037037,
 "days_since_last_scale": 7.7,
 "never_scaled_15d": true,
 "prod": true,
 "name": "app-g",
 "max": 3,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "namespace": "app-g-prod",
 "keda_owned": false,
 "current_cpu_utilization": 2,
 "target_cpu_utilization": 60,
 "target": "app-g-prod/deployment/app-g"
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "notifications_triggers": 0,
 "notifications_configured": false,
 "applications_prod": 10
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "ignore_differences_apps": 16,
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
 ],
 "applications_prod": 10
}
```

</details>
<details><summary><code>certmanager.controller-errors.cluster</code></summary>

```json
{
 "metrics_available": true,
 "acme_errors": 5,
 "not_ready_metric": 0,
 "acme_error_ratio": 0.0427,
 "acme_requests": 117,
 "sync_calls": 2454,
 "acme_by_status": {
  "200": 105,
  "201": 7,
  "400": 5
 },
 "sync_errors": 233
}
```

</details>
<details><summary><code>certmanager.version-old.cluster</code></summary>

```json
{
 "version": "1.14.4",
 "webhook_replicas": 1,
 "components": {
  "controller": "1/1",
  "cainjector": "1/1",
  "webhook": "1/1"
 },
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
 "qps_total": 31.22,
 "metrics_available": true,
 "cluster_ipv6": false
}
```

</details>
<details><summary><code>cost.k3s-node-efficiency.cluster</code></summary>

```json
{
 "nodes": 2,
 "requested_cpu": 6.51,
 "allocatable_cpu": 18.0,
 "can_drop_largest_node": false,
 "request_over_usage": 7.3,
 "p95_used_cpu": 0.89,
 "p95_util_ratio": 0.049
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-applicationset-controller",
 "registry": "quay.io",
 "container": "argocd-applicationset-controller",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-dex-server",
 "registry": "quay.io",
 "container": "copyutil",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex</code></summary>

```json
{
 "image": "ghcr.io/dexidp/dex:v2.43.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-dex-server",
 "registry": "ghcr.io",
 "container": "dex",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-notifications-controller",
 "registry": "quay.io",
 "container": "argocd-notifications-controller",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis</code></summary>

```json
{
 "image": "public.ecr.aws/docker/library/redis:8.2.2-alpine",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-redis",
 "registry": "public.ecr.aws",
 "container": "redis",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-repo-server",
 "registry": "quay.io",
 "container": "argocd-repo-server",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/deployment/argocd-server",
 "registry": "quay.io",
 "container": "argocd-server",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller</code></summary>

```json
{
 "image": "quay.io/argoproj/argocd:v3.2.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "argocd/statefulset/argocd-application-controller",
 "registry": "quay.io",
 "container": "argocd-application-controller",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.app-d-prod/deployment/app-d-vn:db-migrate</code></summary>

```json
{
 "image": "registry.acme.com/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "app-d-prod/deployment/app-d-vn",
 "registry": "registry.acme.com",
 "container": "db-migrate",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks</code></summary>

```json
{
 "image": "ghcr.io/kedacore/keda-admission-webhooks:2.19.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-admission-webhooks",
 "registry": "ghcr.io",
 "container": "keda-admission-webhooks",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver</code></summary>

```json
{
 "image": "ghcr.io/kedacore/keda-metrics-apiserver:2.19.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator-metrics-apiserver",
 "registry": "ghcr.io",
 "container": "keda-operator-metrics-apiserver",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator</code></summary>

```json
{
 "image": "ghcr.io/kedacore/keda:2.19.0",
 "pull_policy": "Always",
 "always_pull_with_tag": true,
 "workload": "keda/deployment/keda-operator",
 "registry": "ghcr.io",
 "container": "keda-operator",
 "tag_kind": "tag"
}
```

</details>
<details><summary><code>hygiene.failed-pods-lingering.cluster</code></summary>

```json
{
 "count": 4,
 "prod": 4,
 "by_namespace": {
  "app-a-prod": 2,
  "app-f-prod": 2
 },
 "sample": [
  "app-a-prod/app-u",
  "app-a-prod/app-a-experiment",
  "app-f-prod/app-f-embed-67f6f74f6c-rlm8m",
  "app-f-prod/app-f-embed-67f6f74f6c-b6kdt"
 ],
 "oldest_h": 3847.0,
 "by_reason": {
  "Failed": 2,
  "UnexpectedAdmissionError": 2
 }
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "request_ratio": 0.0,
 "containers": 126,
 "emptydir_without_sizelimit_prod": [],
 "prod_without_request": 63,
 "with_request": 0,
 "emptydir_without_sizelimit": 11
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
 "secrets_total": 139,
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
 ]
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "webhooks": 28,
 "zero_object_count": 42,
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
 "count": 64
}
```

</details>
<details><summary><code>keda.unused.cluster</code></summary>

```json
{
 "operator_replicas": 1,
 "unused": true,
 "version": "2.19.0",
 "scaledjobs": 0,
 "webhooks_replicas": 1,
 "operator_ready": 1,
 "webhooks_ready": 1,
 "scaledobjects": 0,
 "metrics_apiserver_replicas": 1,
 "metrics_apiserver_ready": 1
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
<details><summary><code>logs.signatures.kubelet.pod-sync-error</code></summary>

```json
{
 "count": 2988,
 "first": "2026-11-04T21:34:47Z",
 "last": "2026-11-05T08:25:20Z",
 "warn_at": 50,
 "fail_at": 1000,
 "files": {
  "logs/node/node-a/k3s-errors-24h.log": 2988
 },
 "samples": [
  "E1105 06:34:47.751559    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with CrashLoopBackOff: \\\"back-off 5m0s restarting failed container=coturn pod=app-c-coturn-549854dfcb-jgp4h_app-c-",
  "E1105 06:34:58.752121    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with CrashLoopBackOff: \\\"back-off 5m0s restarting failed container=coturn pod=app-c-coturn-549854dfcb-jgp4h_app-c-",
  "E1105 06:35:14.281099    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with CrashLoopBackOff: \\\"back-off 5m0s restarting failed container=coturn pod=app-c-coturn-549854dfcb-jgp4h_app-c-",
  "E1105 06:35:27.751594    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with CrashLoopBackOff: \\\"back-off 5m0s restarting failed container=coturn pod=app-c-coturn-549854dfcb-jgp4h_app-c-",
  "E1105 06:35:39.754566    1316 pod_workers.go:1301] \"Error syncing pod, skipping\" err=\"failed to \\\"StartContainer\\\" for \\\"coturn\\\" with CrashLoopBackOff: \\\"back-off 5m0s restarting failed container=coturn pod=app-c-coturn-549854dfcb-jgp4h_app-c-"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metallb.speaker-peer-unreachable</code></summary>

```json
{
 "count": 487,
 "first": "2026-11-05T05:05:40Z",
 "last": "2026-11-05T08:26:40Z",
 "warn_at": 60,
 "fail_at": 2000,
 "files": {
  "logs/pods/metallb/metallb-system_speaker.log": 487
 },
 "samples": [
  "[pod/speaker-xfxlv/speaker] 2026-11-05T14:35:35.218743637+09:00 {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":",
  "[pod/speaker-xfxlv/speaker] 2026-11-05T14:36:13.874442108+09:00 {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":",
  "[pod/speaker-xfxlv/speaker] 2026-11-05T14:36:35.218634805+09:00 {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":",
  "[pod/speaker-xfxlv/speaker] 2026-11-05T14:37:35.219575427+09:00 {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":",
  "[pod/speaker-xfxlv/speaker] 2026-11-05T14:38:35.218957608+09:00 {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":"
 ]
}
```

</details>
<details><summary><code>node.docker-and-containerd.node-a</code></summary>

```json
{
 "collected": true,
 "runtimes": {
  "active": [
   "containerd",
   "k3s-agent",
   "docker"
  ],
  "docker_and_containerd": true,
  "docker_mb": 1,
  "kubelet_runtime": "containerd"
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.large-images.node-a</code></summary>

```json
{
 "collected": true,
 "cri": {
  "available": true,
  "cmd": "sudo -n /usr/local/bin/k3s crictl",
  "runtime": "containerd",
  "version": "v2.1.4-k3s1",
  "states": {
   "Running": 55,
   "Exited": 69,
   "Created": 0,
   "Unknown": 0
  },
  "images": 54,
  "imagefs_used_gb": 29.5,
  "imagefs_inodes": 800040,
  "imagefs_mount": "/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs",
  "conditions": {
   "RuntimeReady": true,
   "NetworkReady": true,
   "ContainerdHasNoDeprecationWarnings": false
  },
  "not_ready": [],
  "images_top": [
   {
    "image": "registry.acme.com/app-f-embed:prod-67527dae60678e93822bf8eb71d8448f586fa0fe",
    "size_mb": 3977
   },
   {
    "image": "registry.acme.com/app-d-mexico:prod-5cd7d78054b8dcfe9f3a76cb5e3fa5bff6bada2a",
    "size_mb": 804
   },
   {
    "image": "ghcr.io/team-acme/app-d-mexico:prod-5cd7d78054b8dcfe9f3a76cb5e3fa5bff6bada2a",
    "size_mb": 804
   },
   {
    "image": "registry.acme.com/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
    "size_mb": 802
   },
   {
    "image": "ghcr.io/team-acme/app-d-vietnam:prod-af6a0983909b58cd53a1c2dbf3aadb3062aec673",
    "size_mb": 802
   },
   {
    "image": "registry.acme.com/app-d:prod-c24abd1b7544dbf4998cdd19540e537f7a2ccdfd",
    "size_mb": 796
   },
   {
    "image": "registry.acme.com/app-a-sandbox-spring:latest",
    "size_mb": 567
   },
   {
    "image": "registry.acme.com/app-a-sandbox-todo:latest",
    "size_mb": 502
   },
   {
    "image": "registry.acme.com/app-a-sandbox-go:latest",
    "size_mb": 383
   },
   {
    "image": "registry.acme.com/app-c-web:prod-f7b662b3f5487d4cf443a654edb0526503f7db95",
    "size_mb": 335
   },
   {
    "image": "registry.acme.com/app-a-sandbox-sql:latest",
    "size_mb": 331
   },
   {
    "image": "registry.acme.com/app-a-sandbox-python-ml:latest",
    "size_mb": 330
   },
   {
    "image": "registry.acme.com/app-a-sandbox-c:latest",
    "size_mb": 307
   },
   {
    "image": "registry.acme.com/app-a-sandbox-nextjs:latest",
    "size_mb": 302
   },
   {
    "image": "ghcr.io/umami-software/umami:postgresql-latest",
    "size_mb": 255
   }
  ],
  "largest_image_mb": 3977,
  "images_over_3gb": [
   "registry.acme.com/app-f-embed:prod-67527dae60678e93822bf8eb71d8448f586fa0fe"
  ],
  "writable_layers_top": [
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-day-29895840-xmmd7",
    "container": "report",
    "workload": "app-a-prod/umami-report-day",
    "mb": 79
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-mx-7f466df4fb-dsdpw",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d-mx",
    "mb": 44
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-vn-766644b56d-dhklj",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d-vn",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-ga4-digest-day-29897280-544h5",
    "container": "digest",
    "workload": "app-d-prod/app-d-ga4-digest-day",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-5fc9656f46-r5stq",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d",
    "mb": 42
   },
   {
    "namespace": "app-d-prod",
    "pod": "app-d-5fc9656f46-dr4nw",
    "container": "db-migrate",
    "workload": "app-d-prod/app-d",
    "mb": 42
   },
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-month-29846880-rcgdq",
    "container": "report",
    "workload": "app-a-prod/umami-report-month",
    "mb": 37
   },
   {
    "namespace": "app-a-prod",
    "pod": "umami-report-day-29897280-8mgj4",
    "container": "report",
    "workload": "app-a-prod/umami-report-day",
    "mb": 37
   },
   {
    "namespace": "app-f-prod",
    "pod": "app-f-app-x-client-7599c7f5f-79njd",
    "container": "app",
    "workload": "app-f-prod/app-f-app-x-client",
    "mb": 15
   },
   {
    "namespace": "app-f-prod",
    "pod": "app-f-app-x-client-7599c7f5f-s2b62",
    "container": "app",
    "workload": "app-f-prod/app-f-app-x-client",
    "mb": 13
   }
  ],
  "writable_layers_total_mb_top10": 393,
  "writable_layers_error": null,
  "writable_layers_available": true,
  "deprecation_warnings": true,
  "systemd_cgroup": "true",
  "snapshotter": null,
  "sandbox_image": null,
  "cni_error": null
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.os-updates-pending.node-a</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-a",
  "kernel": "5.15.0-198-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 7.4,
  "loadavg": "0.33 0.48 0.51",
  "nproc": 6,
  "mem_total_gb": 31.3,
  "containerd_version": null,
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 45,
  "k3s_rss_mb": 259
 },
 "updates": {
  "reboot_required": true,
  "updates_total": 52,
  "security_updates": 1,
  "needs_restarting_rc": null,
  "ami_release": null
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.os-updates-pending.node-b</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-b",
  "kernel": "5.15.0-185-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 117.3,
  "loadavg": "1.47 1.74 1.56",
  "nproc": 12,
  "mem_total_gb": 30.7,
  "containerd_version": "v2.1.4-k3s1",
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 243,
  "k3s_rss_mb": 1743
 },
 "updates": {
  "reboot_required": true,
  "updates_total": 52,
  "security_updates": 7,
  "needs_restarting_rc": null,
  "ami_release": null
 },
 "node": "node-b"
}
```

</details>
<details><summary><code>node.reboot-required.node-a</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-a",
  "kernel": "5.15.0-198-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 7.4,
  "loadavg": "0.33 0.48 0.51",
  "nproc": 6,
  "mem_total_gb": 31.3,
  "containerd_version": null,
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 45,
  "k3s_rss_mb": 259
 },
 "updates": {
  "reboot_required": true,
  "updates_total": 52,
  "security_updates": 1,
  "needs_restarting_rc": null,
  "ami_release": null
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.reboot-required.node-b</code></summary>

```json
{
 "collected": true,
 "meta": {
  "root": false,
  "hostname": "node-b",
  "kernel": "5.15.0-185-generic",
  "os": "Ubuntu 22.04.5 LTS",
  "uptime_days": 117.3,
  "loadavg": "1.47 1.74 1.56",
  "nproc": 12,
  "mem_total_gb": 30.7,
  "containerd_version": "v2.1.4-k3s1",
  "k3s_version": "k3s version v1.33.5+k3s1 (fab4a5c3)",
  "zombies": 0,
  "kubelet_rss_mb": null,
  "containerd_rss_mb": 243,
  "k3s_rss_mb": 1743
 },
 "updates": {
  "reboot_required": true,
  "updates_total": 52,
  "security_updates": 7,
  "needs_restarting_rc": null,
  "ami_release": null
 },
 "node": "node-b"
}
```

</details>
<details><summary><code>node.smartmontools-missing.node-a</code></summary>

```json
{
 "collected": true,
 "smartctl": false,
 "disks": {
  "devices": [
   "sda disk 111.8G 0 WDC WDS120G2G0A-"
  ],
  "smart": []
 },
 "node": "node-a"
}
```

</details>
<details><summary><code>node.smartmontools-missing.node-b</code></summary>

```json
{
 "collected": true,
 "smartctl": false,
 "disks": {
  "devices": [
   "sda disk 465.8G 0 Samsung SSD 870"
  ],
  "smart": []
 },
 "node": "node-b"
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
 "ingresses": 29,
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
 ]
}
```

</details>
<details><summary><code>observability.severity-channels-not-separated.cluster</code></summary>

```json
{
 "receivers": {
  "null": [],
  "discord": [
   "slack"
  ]
 },
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
 ]
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "error_lines_unclassified": 403,
 "lines_scanned": 26732,
 "files_scanned": [
  "logs/node/node-a/k3s-errors-24h.log",
  "logs/node/node-b/containerd-24h.log",
  "logs/node/node-b/k3s-errors-24h.log",
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
 ],
 "unclassified_errors": [
  {
   "pattern": "node:node-b | \"Unhandled Error\" err=\"error syncing CronJobController app-a-prod/app-a-sandbox-watchdog, requeuing: Operation cannot be fulfilled",
   "count": 317,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 317
   },
   "sample": "E1104 12:27:50.527082  707592 cronjob_controllerv2.go:174] \"Unhandled Error\" err=\"error syncing CronJobController app-a-prod/app-a-sandbox-watchdog, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"app-a-sandbox-w"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"Sending HTTP/1.1 <n> response to <ip>: dial tcp <ip>: connect: connection refused\"",
   "count": 11,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 11
   },
   "sample": "time=\"2026-11-04T13:30:03Z\" level=error msg=\"Sending HTTP/1.1 502 response to 127.0.0.1:44914: dial tcp <ip>:8084: connect: connection refused\""
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"Sending HTTP/1.1 <n> response to <ip>: dial tcp <ip>: connect: connection timed out\"",
   "count": 8,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 8
   },
   "sample": "time=\"2026-11-04T13:32:15Z\" level=error msg=\"Sending HTTP/1.1 502 response to 127.0.0.1:45000: dial tcp <ip>:7472: connect: connection timed out\""
  },
  {
   "pattern": "node:node-b | Error proxying data from client to backend: read tcp <ip>-><ip>: read: connection timed out",
   "count": 4,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 4
   },
   "sample": "E1104 23:16:46.146848  707592 upgradeaware.go:427] Error proxying data from client to backend: read tcp <ip>:6443-><ip>:65357: read: connection timed out"
  },
  {
   "pattern": "node:node-b | \"ExecSync cmd from runtime service failed\" err=\"rpc error: code = DeadlineExceeded desc = failed to exec in container: timeout <dur> exceede",
   "count": 3,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 3
   },
   "sample": "E1105 00:00:19.187937  707592 log.go:32] \"ExecSync cmd from runtime service failed\" err=\"rpc error: code = DeadlineExceeded desc = failed to exec in container: timeout 1s exceeded: context deadline exceeded\" containerID=\"0b66d9fcfd3dbb61490"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"ExecSync for \\\"0b66d9fcfd3dbb61490614810f48a23a191c244009b98b36c812fdb74020fa99\\\" failed\" error=\"rpc error: code = ",
   "count": 2,
   "files": {
    "logs/node/node-b/containerd-24h.log": 2
   },
   "sample": "time=\"2026-11-05T07:53:07.481296337Z\" level=error msg=\"ExecSync for \\\"0b66d9fcfd3dbb61490614810f48a23a191c244009b98b36c812fdb74020fa99\\\" failed\" error=\"rpc error: code = DeadlineExceeded desc = failed to exec in container: timeout 1s exceed"
  },
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
   "pattern": "node:node-a | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"da0beb4b",
   "count": 1,
   "files": {
    "logs/node/node-a/k3s-errors-24h.log": 1
   },
   "sample": "E1105 12:08:18.815213    1316 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"da0beb4be3eea11ae30568883e11542a77c4bcc7a3f4746f5cebd9184f98a50b\\\":"
  },
  {
   "pattern": "node:node-a | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"c2414111",
   "count": 1,
   "files": {
    "logs/node/node-a/k3s-errors-24h.log": 1
   },
   "sample": "E1105 12:21:13.991606    1316 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"c2414111b817b615eb04416ca12eb1698d0bbf470f3099fa59984ccaaed5ea9c\\\":"
  },
  {
   "pattern": "node:node-a | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"254e8283",
   "count": 1,
   "files": {
    "logs/node/node-a/k3s-errors-24h.log": 1
   },
   "sample": "E1105 13:17:46.632594    1316 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"254e82830d57e3d746ac5e61ee07b95596791c7cc6969861df84023eb25b8cd5\\\":"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/502a7cdae0b1853444bdc08970d9345882432c64f7ba",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T03:50:05.032821882Z\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/502a7cdae0b1853444bdc08970d9345882432c64f7bab7d71d400a470d4af128->@: write: broken pipe\" runtime=io.containerd.run"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"ttrpc: received message on inactive stream\" stream=57",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T04:02:38.307774904Z\" level=error msg=\"ttrpc: received message on inactive stream\" stream=57"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/94e056724f0b1e095480d58a186019d37347f72eb278",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T04:05:39.279465918Z\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/94e056724f0b1e095480d58a186019d37347f72eb278fbb0c94991fb14423e98->@: write: broken pipe\" runtime=io.containerd.run"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/143d0514d835e08baa43745f50d6fc7ffa234f2cddd8",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T04:17:37.171883062Z\" level=error msg=\"failed sending message on channel\" error=\"write unix /run/containerd/s/143d0514d835e08baa43745f50d6fc7ffa234f2cddd8c27b257711e03651fd5e->@: write: broken pipe\" runtime=io.containerd.run"
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"ContainerStatus for \\\"de457b0eedeefcffe1474540cefc7d4c1e6a1000c6c32b3f546421187deb6b83\\\" failed\" error=\"rpc error: ",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T08:04:25.998148853Z\" level=error msg=\"ContainerStatus for \\\"de457b0eedeefcffe1474540cefc7d4c1e6a1000c6c32b3f546421187deb6b83\\\" failed\" error=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\""
  },
  {
   "pattern": "node:node-b | time=\"\" level=error msg=\"ContainerStatus for \\\"38223df47ee539e4feca8f73b0f0c9b7c8c08403fc00ca8958658232a64cbfaa\\\" failed\" error=\"rpc error: ",
   "count": 1,
   "files": {
    "logs/node/node-b/containerd-24h.log": 1
   },
   "sample": "time=\"2026-11-05T08:04:25.998358729Z\" level=error msg=\"ContainerStatus for \\\"38223df47ee539e4feca8f73b0f0c9b7c8c08403fc00ca8958658232a64cbfaa\\\" failed\" error=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\""
  },
  {
   "pattern": "node:node-b | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"117e51f7",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 00:46:43.546203  707592 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"117e51f7a31295b5f1e8a57d33d3b65eb59a3d4073e790be336a8829553bb66d\\\":"
  },
  {
   "pattern": "node:node-b | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"f6765151",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 00:46:43.546474  707592 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"f6765151f5cfc76fc254198b3f1a33fc04890445c62f50afde71402dfa770751\\\":"
  },
  {
   "pattern": "node:node-b | \"Unhandled Error\" err=\"error syncing CronJobController app-a-prod/app-a-postgres-backup, requeuing: Operation cannot be fulfilled ",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 03:24:02.691325  707592 cronjob_controllerv2.go:174] \"Unhandled Error\" err=\"error syncing CronJobController app-a-prod/app-a-postgres-backup, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"app-a-postgres-b"
  },
  {
   "pattern": "node:node-b | \"Unhandled Error\" err=\"error syncing CronJobController app-d-prod/app-d-postgres-mx-backup, requeuing: Operation cannot be fulfilled on cronjo",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 03:30:03.312651  707592 cronjob_controllerv2.go:174] \"Unhandled Error\" err=\"error syncing CronJobController app-d-prod/app-d-postgres-mx-backup, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"app-d-postgres-mx-backup\\\": the"
  },
  {
   "pattern": "node:node-b | \"Unhandled Error\" err=\"error syncing CronJobController app-e-api/app-e-postgres-backup, requeuing: Operation cannot be fulfilled on cron",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 03:50:06.109726  707592 cronjob_controllerv2.go:174] \"Unhandled Error\" err=\"error syncing CronJobController app-e-api/app-e-postgres-backup, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"app-e-postgres-backup\\\": t"
  },
  {
   "pattern": "node:node-b | \"Unhandled Error\" err=\"error syncing CronJobController registry/registry-gc, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"re",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 04:00:05.713233  707592 cronjob_controllerv2.go:174] \"Unhandled Error\" err=\"error syncing CronJobController registry/registry-gc, requeuing: Operation cannot be fulfilled on cronjobs.batch \\\"registry-gc\\\": the object has been modified"
  },
  {
   "pattern": "node:node-b | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"de457b0e",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 08:04:25.998225  707592 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"de457b0eedeefcffe1474540cefc7d4c1e6a1000c6c32b3f546421187deb6b83\\\":"
  },
  {
   "pattern": "node:node-b | \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"38223df4",
   "count": 1,
   "files": {
    "logs/node/node-b/k3s-errors-24h.log": 1
   },
   "sample": "E1105 08:04:25.998433  707592 log.go:32] \"ContainerStatus from runtime service failed\" err=\"rpc error: code = NotFound desc = an error occurred when try to find container \\\"38223df47ee539e4feca8f73b0f0c9b7c8c08403fc00ca8958658232a64cbfaa\\\":"
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
  }
 ]
}
```

</details>
<details><summary><code>platform.k3s-apiserver-bind-all.cluster</code></summary>

```json
{
 "apiserver": {
  "bind_all_nodes": [
   "node-b"
  ],
  "tls_san": [
   "<ip>",
   "<ip>"
  ],
  "external_ips": [
   "<ip>",
   "<ip>"
  ]
 }
}
```

</details>
<details><summary><code>platform.k3s-check-config-missing.cluster</code></summary>

```json
{
 "check_config_missing": [
  "CONFIG_INET_XFRM_MODE_TRANSPORT",
  "CONFIG_RT_GROUP_SCHED"
 ]
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-a-prod/statefulset/app-a-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-a-prod/statefulset/app-a-redis",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-c-prod/statefulset/app-c-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-c",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-mx:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres-mx",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres-vn:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres-vn",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-d-prod/statefulset/app-d-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-d-prod/statefulset/app-d-redis:redis</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-d-prod/statefulset/app-d-redis",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "exec",
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "container": "redis"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-e-api/statefulset/app-e-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-e-api/statefulset/app-e-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-f-prod/statefulset/app-f-mysql:mysql</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-f-prod/statefulset/app-f-mysql",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "mysql"
}
```

</details>
<details><summary><code>resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "readiness exec timeout 1s (false failures when the node is busy)"
 ],
 "workload": "logging/statefulset/elasticsearch",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'\n",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "liveness": {
  "type": "exec",
  "path": "sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'\n",
  "port": null,
  "timeout_s": 10,
  "period_s": 30,
  "failure_threshold": 10,
  "initial_delay_s": 90
 },
 "container": "elasticsearch"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-g-prod/statefulset/app-g-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-g-prod/statefulset/app-g-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-h/deployment/app-h-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-h/deployment/app-h-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app_h -d app_h",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-i-prod/deployment/app-i-postgres:postgres</code></summary>

```json
{
 "flags": [
  "liveness exec (forks a process)",
  "readiness exec (forks a process every period, node load)",
  "liveness exec timeout 1s (false failures when the node is busy)",
  "readiness exec timeout 1s (false failures when the node is busy)",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "workload": "app-i-prod/deployment/app-i-postgres",
 "exec_probe": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-i -d app-i",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "container": "postgres"
}
```

</details>
<details><summary><code>resilience.finished-jobs-accumulating.cluster</code></summary>

```json
{
 "failed": 3,
 "failed_pods": 4,
 "finished_without_ttl": 56,
 "total": 58,
 "succeeded_pods": 53
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-frontend:frontend</code></summary>

```json
{
 "workload": "app-a-prod/deployment/app-a-frontend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "dependency_liveness": false,
 "container": "frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-gateway:gateway</code></summary>

```json
{
 "workload": "app-a-prod/deployment/app-a-gateway",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 2
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "dependency_liveness": false,
 "container": "gateway"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-phoenix:phoenix</code></summary>

```json
{
 "workload": "app-a-prod/deployment/app-a-phoenix",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 6006,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 6006,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 40
 },
 "dependency_liveness": false,
 "container": "phoenix"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-a-prod/deployment/app-a-umami:umami</code></summary>

```json
{
 "workload": "app-a-prod/deployment/app-a-umami",
 "flags": [
  "liveness and readiness share the same path (/api/heartbeat) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/api/heartbeat",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "liveness": {
  "type": "httpGet",
  "path": "/api/heartbeat",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 30,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "umami"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-backend:backend</code></summary>

```json
{
 "workload": "app-b-prod/deployment/app-b-backend",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "dependency_liveness": false,
 "container": "backend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-b-prod/deployment/app-b-frontend:frontend</code></summary>

```json
{
 "workload": "app-b-prod/deployment/app-b-frontend",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "dependency_liveness": false,
 "container": "frontend"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-signaling:app</code></summary>

```json
{
 "workload": "app-c-prod/deployment/app-c-signaling",
 "flags": [
  "liveness and readiness share the same path (/ws/socket.io/?EIO=4&transport=polling) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/ws/socket.io/?EIO=4&transport=polling",
  "port": 3001,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-c-prod/deployment/app-c-web:app</code></summary>

```json
{
 "workload": "app-c-prod/deployment/app-c-web",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-admin:app</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-admin",
 "flags": [
  "liveness and readiness share the same path (/login) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 12,
  "initial_delay_s": 10
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/login",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 15
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-mx:app</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-mx",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d-vn:app</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d-vn",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-d-prod/deployment/app-d:app</code></summary>

```json
{
 "workload": "app-d-prod/deployment/app-d",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-admin:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-admin",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 30
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-api-server:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-api-server",
 "flags": [
  "liveness and readiness share the same path (/healthcheck) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 30,
  "initial_delay_s": 90
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 5,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthcheck",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 5,
  "initial_delay_s": 60
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-x-client:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-app-x-client",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-embed:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-embed",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 30,
  "initial_delay_s": 15
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 0
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 60
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-excel-agent:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-excel-agent",
 "flags": [
  "liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 18,
  "initial_delay_s": 10
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/health",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-f-prod/deployment/app-f-app-w:app</code></summary>

```json
{
 "workload": "app-f-prod/deployment/app-f-app-w",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 25
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-g-prod/deployment/app-g:app</code></summary>

```json
{
 "workload": "app-g-prod/deployment/app-g",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 12,
  "initial_delay_s": 20
 },
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "dependency_liveness": false,
 "container": "app"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-i-prod/deployment/app-i-api:api</code></summary>

```json
{
 "workload": "app-i-prod/deployment/app-i-api",
 "flags": [
  "liveness and readiness share the same path (/healthz) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/healthz",
  "port": 8080,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "dependency_liveness": false,
 "container": "api"
}
```

</details>
<details><summary><code>resilience.liveness-dependency-path.app-i-prod/deployment/app-i-web:web</code></summary>

```json
{
 "workload": "app-i-prod/deployment/app-i-web",
 "flags": [
  "liveness and readiness share the same path (/) — a dependency outage becomes a restart loop"
 ],
 "startup": null,
 "same_path": true,
 "prod": true,
 "serves_traffic": true,
 "readiness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "liveness": {
  "type": "httpGet",
  "path": "/",
  "port": 3000,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 20
 },
 "dependency_liveness": false,
 "container": "web"
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
  "memory_request_p95_ratio_7d": 0.20265884399414064,
  "memory_p95_7d_bytes": 54400819.2,
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
  "memory_request_p95_ratio_7d": 0.1919097900390625,
  "memory_p95_7d_bytes": 51515392.0,
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
 "prod": true,
 "name": "app-a-backend",
 "metric_types": [
  "cpu"
 ],
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-backend",
 "current_cpu_utilization": 3,
 "target_cpu_utilization": 70,
 "cpu_only": true
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "prod": true,
 "name": "app-a-frontend",
 "metric_types": [
  "cpu"
 ],
 "namespace": "app-a-prod",
 "target": "app-a-prod/deployment/app-a-frontend",
 "current_cpu_utilization": 3,
 "target_cpu_utilization": 70,
 "cpu_only": true
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "has_behavior": false,
 "prod": true,
 "name": "app-a-backend",
 "max": 6,
 "min": 2,
 "namespace": "app-a-prod",
 "desired_changes_7d": 3.0,
 "keda_owned": false,
 "target": "app-a-prod/deployment/app-a-backend"
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend</code></summary>

```json
{
 "has_behavior": false,
 "prod": true,
 "name": "app-a-frontend",
 "max": 4,
 "min": 2,
 "namespace": "app-a-prod",
 "desired_changes_7d": 4.0,
 "keda_owned": false,
 "target": "app-a-prod/deployment/app-a-frontend"
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
<details><summary><code>storage.local-path-node-pinned.cluster</code></summary>

```json
{
 "pinned": [
  {
   "pv": "pvc-db50eb33-8393-45cd-93b3-042e019e1186",
   "namespace": "logging",
   "pvc": "data-elasticsearch-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 20480,
   "used_mb": 103451,
   "used_ratio": 5.05,
   "workloads": [
    "logging/elasticsearch-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-1a2c9674-3fcb-4205-85f2-3f2d08fd1c92",
   "namespace": "registry",
   "pvc": "registry-data-registry-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 51200,
   "used_mb": 32732,
   "used_ratio": 0.64,
   "workloads": [
    "registry/registry-0",
    "registry/registry-gc"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-ff3e86cb-38ac-461e-93ea-fc0c6f0fadda",
   "namespace": "app-a-prod",
   "pvc": "app-a-postgres-backup-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": 5862,
   "used_ratio": 1.14,
   "workloads": [
    "app-a-prod/app-a-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-d82daba5-58bf-4f2b-aa68-94278a5a33fd",
   "namespace": "app-a-prod",
   "pvc": "data-app-a-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 2217,
   "used_ratio": 0.22,
   "workloads": [
    "app-a-prod/app-a-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-d15ad7cd-aea4-482d-8b3e-f0386a4f73a1",
   "namespace": "app-f-prod",
   "pvc": "mysql-data-app-f-mysql-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 20480,
   "used_mb": 779,
   "used_ratio": 0.04,
   "workloads": [
    "app-f-prod/app-f-mysql-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-b31ee6ea-3238-4ecc-a34d-877a14177ad5",
   "namespace": "app-e-api",
   "pvc": "app-e-minio-data-app-e-minio-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 51200,
   "used_mb": 508,
   "used_ratio": 0.01,
   "workloads": [
    "app-e-api/app-e-minio-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-b6f729e1-b443-4ed2-866f-8fc9825078ae",
   "namespace": "app-e-api",
   "pvc": "app-e-postgres-data-app-e-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 164,
   "used_ratio": 0.02,
   "workloads": [
    "app-e-api/app-e-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-291c9301-e481-4b69-9234-bb77f18d6faf",
   "namespace": "app-i-prod",
   "pvc": "app-i-postgres-data",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 138,
   "used_ratio": 0.01,
   "workloads": [
    "app-i-prod/app-i-postgres"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-c66c539e-96b8-4cb2-ba16-90df9d05a84f",
   "namespace": "app-i-prod",
   "pvc": "app-i-artifacts",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 124,
   "used_ratio": 0.01,
   "workloads": [
    "app-i-prod/app-i-api"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-fedc8d18-9f78-48d0-91be-54dcece66bab",
   "namespace": "app-c-prod",
   "pvc": "postgres-data-app-c-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": 87,
   "used_ratio": 0.02,
   "workloads": [
    "app-c-prod/app-c-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-d3dc33a5-26ca-4c1a-a9e7-526e2c0a0e7a",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-data-app-d-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 70,
   "used_ratio": 0.01,
   "workloads": [
    "app-d-prod/app-d-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-5bef8ef5-dc76-48cf-8642-05c4099a8d95",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-vn-data-app-d-postgres-vn-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 67,
   "used_ratio": 0.01,
   "workloads": [
    "app-d-prod/app-d-postgres-vn-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-c57619eb-bdde-45d0-b9c0-0845856203af",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-mx-data-app-d-postgres-mx-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 64,
   "used_ratio": 0.01,
   "workloads": [
    "app-d-prod/app-d-postgres-mx-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-8729556f-dbf5-40ce-a48b-57eb4e27edc6",
   "namespace": "app-g-prod",
   "pvc": "app-g-postgres-data-app-g-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 30720,
   "used_mb": 63,
   "used_ratio": 0.0,
   "workloads": [
    "app-g-prod/app-g-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-a9a03cde-f245-4987-b4b8-e61763da9993",
   "namespace": "app-f-prod",
   "pvc": "mysql-backup-app-f-mysql-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 60,
   "used_ratio": 0.01,
   "workloads": [
    "app-f-prod/app-f-mysql-0",
    "app-f-prod/app-f-mysql-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-123d97df-e04a-495f-9283-69147d9a8679",
   "namespace": "app-h",
   "pvc": "app-h-postgres-data",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": 47,
   "used_ratio": 0.01,
   "workloads": [
    "app-h/app-h-postgres"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-8548aa25-05f2-4388-8c7e-872d080f2a0c",
   "namespace": "default",
   "pvc": "data-app-z-db-0",
   "node": "node-b",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": 47,
   "used_ratio": 0.0,
   "workloads": [],
   "phase": "Bound"
  },
  {
   "pv": "pvc-76f7091e-04fe-4abb-98b6-e814163b9ee6",
   "namespace": "app-f-prod",
   "pvc": "app-f-qdrant-data-app-f-qdrant-0",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": 25,
   "used_ratio": 0.0,
   "workloads": [
    "app-f-prod/app-f-qdrant-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-228da581-f434-4f84-ba50-d91df7133690",
   "namespace": "app-e-api",
   "pvc": "app-e-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": 17,
   "used_ratio": 0.0,
   "workloads": [
    "app-e-api/app-e-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-e8064a22-b689-4d23-adef-de705d889c95",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": 2,
   "used_ratio": 0.0,
   "workloads": [
    "app-d-prod/app-d-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-378c5351-e088-4317-9671-7f05346e9531",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-mx-backup-pvc",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-d-prod/app-d-postgres-mx-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-4ce85409-5052-4afb-8c7c-fa0a912f7e09",
   "namespace": "app-g-prod",
   "pvc": "app-g-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-g-prod/app-g-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-5e9317ac-0de1-4afb-b312-8244dbebd7bd",
   "namespace": "app-b-prod",
   "pvc": "app-b-artifacts",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-b-prod/app-b-backend"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-645a9c5d-9faa-4441-b506-436861a32ebf",
   "namespace": "app-a-prod",
   "pvc": "data-app-a-redis-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 1024,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-a-prod/app-a-redis-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-76170548-ef10-4112-9aaf-5332ae1eeeaa",
   "namespace": "app-d-prod",
   "pvc": "app-d-postgres-vn-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-d-prod/app-d-postgres-vn-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-9fad0f20-f5fa-49ff-89f8-af0aaf8d55bd",
   "namespace": "app-d-prod",
   "pvc": "app-d-redis-data-app-d-redis-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 1024,
   "used_mb": 1,
   "used_ratio": 0.0,
   "workloads": [
    "app-d-prod/app-d-redis-0"
   ],
   "phase": "Bound"
  }
 ],
 "node_total_mb": {
  "node-a": 6193,
  "node-b": 140321
 },
 "pv_count": 26,
 "by_node": {
  "node-a": 7,
  "node-b": 19
 }
}
```

</details>
<details><summary><code>storage.local-path-prod-delete-reclaim.cluster</code></summary>

```json
{
 "prod_pvs_delete_reclaim": [
  "app-i-prod/app-i-postgres-data",
  "app-d-prod/app-d-postgres-mx-backup-pvc",
  "app-g-prod/app-g-postgres-backup-pvc",
  "app-d-prod/app-d-postgres-vn-data-app-d-postgres-vn-0",
  "app-b-prod/app-b-artifacts",
  "app-a-prod/data-app-a-redis-0",
  "app-d-prod/app-d-postgres-vn-backup-pvc",
  "app-f-prod/app-f-qdrant-data-app-f-qdrant-0",
  "app-g-prod/app-g-postgres-data-app-g-postgres-0",
  "app-d-prod/app-d-redis-data-app-d-redis-0",
  "app-f-prod/mysql-backup-app-f-mysql-0",
  "app-d-prod/app-d-postgres-mx-data-app-d-postgres-mx-0",
  "app-i-prod/app-i-artifacts",
  "app-f-prod/mysql-data-app-f-mysql-0",
  "app-d-prod/app-d-postgres-data-app-d-postgres-0",
  "app-a-prod/data-app-a-postgres-0",
  "app-d-prod/app-d-postgres-backup-pvc",
  "app-c-prod/postgres-data-app-c-postgres-0",
  "app-a-prod/app-a-postgres-backup-pvc"
 ],
 "reclaim_policies": {
  "local-path": "Delete",
  "local-path-node-b": "Delete"
 },
 "prod_pvs": 19,
 "default_class": "local-path"
}
```

</details>
<details><summary><code>traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "external_traffic_policy": "Local",
 "ports": [
  80,
  443
 ],
 "name": "nginx-ingress-ingress-nginx-controller",
 "namespace": "ingress-nginx",
 "hosts": [
  "<ip>"
 ],
 "target": "loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller"
}
```

</details>
<details><summary><code>traffic.metallb-single-lb-service.cluster</code></summary>

```json
{
 "leader_share": 1.0,
 "l2_available": true,
 "pinned_by_selector": false,
 "leader_node": "node-b",
 "mode": "layer2",
 "nodes_total": 2,
 "total_ips": 10,
 "lb_services": 1,
 "used": 1
}
```

</details>

### 7-6. Tool notes (about kubegap itself)

1. Time-based checks use the evaluation clock, not taken_at: findings-draft.json generated_at is 2026-11-05T23:48:41+09:00, 6 h 23 min after taken_at 17:25:17+09:00. resilience.cronjob-stale.app-a-prod/app-a-sandbox-watchdog reports 'last success 6.4h ago' although status.lastSuccessfulTime 2026-11-05T08:24:50Z is 27 s before collection, and operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn reports 6.7 hours for a condition that was 17 minutes old at collection. Both show up in diff.json as warn to fail.
2. Literal env values and container args stay in plain text in objects/*.json: objects/cronjobs.json logging/es-index-retention keeps the ELASTIC_PASSWORD value (10 characters), and objects/deployments.json app-c-prod/app-c-coturn keeps the --user=< redacted> argument, while summary.json security.secrets says 'value not recorded'. The snapshot holds credentials the scrubber does not remove.
3. diff.json could not compare CronJobs: objects.kinds_only_in_a is ['cronjobs.batch'] and kinds_only_in_b is ['cronjobs'], so a CronJob change between 2026-11-04T22-29-59 and this snapshot would not appear.
4. security.plaintext-configmap-secret fails on key names found inside script files: for app-a-prod/app-v-scripts and app-d-prod/app-d-app-v-scripts every matched key is an environment lookup or code expression (extra/configmap-secret-rhs-class.txt), yet both are fail high. Classifying the right-hand side, as that file does, would remove the false positive.
5. resilience.backup rows list every database in the namespace as source_db (app-d-postgres-backup lists app-d-postgres, -mx, -vn and app-d-redis) although the dump command connects to one host only; same_node_as_source can therefore be true or false for the wrong database.

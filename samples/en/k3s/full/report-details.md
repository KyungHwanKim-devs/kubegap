# kubegap report details — default (`default`), full mode

Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `report/outline.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English.

| Item | Value |
|---|---|
| kube context / cluster | `default` / default (k3s, v1.33.5+k3s1) |
| Run time / mode | 2026-11-15T01:02:12+09:00 / full (collection 285.9 s, 0 steps skipped by mode, 0 failed) |
| Scale | `small` (answered) |
| kubegap / rubric / signatures | 0.2.0 / 0.1.94 / 1.1.1 |
| Verified against | Kubernetes v1.33.5+k3s1 (verified 1.30 to 1.37) · Prometheus 3.7.3 (verified 2.49 to 3.15) · Alertmanager 0.29.0 (verified 0.26 to 0.34) · Grafana 12.2.1 (verified 10.2 to 13.3) |
| Nodes / namespaces / pods / CRDs | 2 (Ready 2) / 28 / 145 / 87 |
| Components (26) | actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, istio, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, opentelemetry-collector, prometheus, prometheus-operator, reloader, tempo-jaeger |
| Metrics store | prometheus 3.7.3 retention 30d / size 0B via port-forward |
| Log store | none (Loki not found) |
| Node access | none (k3s: reading nodes over SSH was skipped at the first-run question; `/kubegap setup` asks again); SSM unregistered 0 |
| Snapshot | `~/.kubegap/snapshots/<context>/2026-11-15T01-02-12` |

## 1. Counts (first pass) and the LLM's adjustments

| Severity (default) | fail | warn | vs. previous run of this mode |
|---|---|---|---|
| critical | 0 | 2 | no previous run of this mode |
| high | 15 | 23 | no previous run of this mode |
| medium | 93 | 173 | no previous run of this mode |
| low | 13 | 115 | no previous run of this mode |
| info | 0 | 17 | no previous run of this mode |

Checks 349: evaluated 263, not run on this platform or at this scale 44, skipped 40, not collected in this mode 0, errors 0, tool missing 0, LLM-judged 2. Suppressed findings 0.

### 1-1. Final judgment vs. first pass (adjustments)

(not written this run)

### 1-2. Aggregates the LLM recounted

(not written this run)

## 2. Critical and high failing now (first pass)

| Finding | Severity | Consecutive runs | Evidence |
|---|---|---|---|
| `argocd.prune-manages-namespace-or-crd.cluster` | high |  | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-d', 'argocd/application/app-g-api' … |
| `observability.alertmanager-notification-failed.slack` | high |  | 8 of 60 notifications failed in 24h, the other 52 were delivered (integration slack, which is how the receiver is configured and not necessarily where it delivers: a Discord webhook is often called through the slack … |
| `platform.k8s-version-eol.cluster` | high |  | server v1.33.5+k3s1: upstream end of life 2026-06-28, 140 days past |
| `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | high |  | storage emptyDir (PVC None), PVC usage None, TSDB 22.3GiB, retention 30d (size cap 0B), actual oldest sample 31.2 days, failed compactions over 7 days 0, WAL corruptions 1, corruptions at startup 1 |
| `resources.cpu-throttling.app-a-prod/ds/app-a-sandbox-prepull:hold-python` | high |  | pod app-a-sandbox-prepull-8xvrq: throttling ratio now 0.00, 24 h or the pod's life 0.33: throttled through the day; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.app-g-api/sts/app-g-postgres:postgres` | high |  | pod app-g-postgres-0: throttling ratio now 0.16, 24 h or the pod's life 0.26: throttled through the day |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-admin:app` | high |  | ["pod app-h-admin-6789875894-2qz6d: throttling ratio now 0.46, 24 h or the pod's life 0.46: throttled through the day", "pod app-h-admin-6789875894-pwhh4: throttling ratio now 0.52, 24 h or the pod's life 0.05: throttled this … |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-api-server:app` | high |  | ["pod app-h-api-server-7ccdccd9f8-7wvxl: throttling ratio now 0.00, 24 h or the pod's life 0.61: throttled through the day; no 5-minute value, under 0.01 now", "pod app-h-api-server-7ccdccd9f8-r6xdr: throttling ratio now … |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-app-q-client:app` | high |  | ["pod app-h-app-q-client-754b8c5b59-nszv9: throttling ratio now 0.00, 24 h or the pod's life 0.30: throttled through the day; no 5-minute value, under 0.01 now", "pod app-h-app-q-client-754b8c5b59-g8x5q: throttling ratio now … |
| `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` | high |  | ["pod fluent-bit-bmdwx: throttling ratio now 0.27, 24 h or the pod's life 0.31: throttled through the day", "pod fluent-bit-wzbvh: throttling ratio now 0.32, 24 h or the pod's life 0.42: throttled through the day"] |
| `resources.cpu-throttling.logging/pod/fluent-bit-qcjbv:fluent-bit` | high |  | pod fluent-bit-qcjbv: throttling ratio now 0.00, 24 h or the pod's life 0.28: throttled through the day; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` | high |  | pod elasticsearch-0: throttling ratio now 0.34, 24 h or the pod's life 0.37: throttled through the day |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | high |  | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.61, 24 h or the pod's life 0.45: throttled through the day |
| `resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio` | high |  | pod app-g-minio-0: 7d memory working set p95 / limit = 0.95 |
| `resources.oomkilled-repeated.monitoring/sts/tempo:tempo` | high |  | kernel log not read in this mode. Prometheus: 1 pod ended by OOM in 7 days, 1 already replaced, 163 restarts in those pods (none of those pods is running now). cAdvisor counter 0. Running now: tempo-0 (created … |

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
| `resilience.no-backup.cluster` | warn | critical | There is no way to recover cluster state (objects) and PV data. Deleting a namespace by mistake or a broken etcd or PV is the end. A CronJob dump without a tool is often "a backup kept on the same … | Velero (plus EBS snapshots or PV backup). On EKS at least a DLM snapshot policy. In a small k3s cluster, k3s etcd-snapshot or a state.db copy plus PV directory backup. Test a restore; a dump that was … |

Expected families missing (inventory): backup.

## 6. Suppressed, tool missing, not collected

- Suppressed 0: none
- Suppression expired 0: none
- Tool missing 0: none
- Not collected in full mode 0: none
- Skipped or errored 40: `observability.log-volume-change` (skip: summary.logs.loki.volume_change missing), `node.kernel-oom-node-level` (skip: nothing to judge: node not read (2)), `node.kernel-lockup` (skip: nothing to judge: node not read (2)), `node.kernel-io-fs-errors` (skip: nothing to judge: node not read (2)), `node.kernel-nic-events` (skip: nothing to judge: node not read (2)), `node.conntrack-table-full` (skip: nothing to judge: node not read (2)), `node.kernel-net-mem-pressure` (skip: nothing to judge: node not read (2)), `node.cgroup-v1` (skip: nothing to judge: node not read (2)), `node.sysctl-tuning` (skip: nothing to judge: node not read (2)), `node.cri-not-ready` (skip: nothing to judge: node not read, or cri not read (2)), `node.cri-exited-containers` (skip: nothing to judge: node not read (2)), `node.pod-logs-large` (skip: summary.nodeos.pod_logs missing), `node.pod-dir-large` (skip: summary.nodeos.pod_dirs missing), `node.service-restarts` (skip: nothing to judge: node not read (2)), `node.reboot-required` (skip: nothing to judge: node not read (2)), `node.os-updates-pending` (skip: nothing to judge: node not read (2)), `node.kubelet-reserved-missing` (skip: nothing to judge: node not read, or kubelet not read (2)), `node.kubelet-eviction-memory-missing` (skip: nothing to judge: node not read, or kubelet not read (2)), `node.clock-unsynced-os` (skip: nothing to judge: node not read (2)), `node.zombie-processes` (skip: nothing to judge: node not read (2)), `observability.log-coverage-gap` (skip: summary.logs.loki.coverage missing), `observability.loki-not-ready` (skip: nothing to judge: loki not present), `observability.loki-ingest-discarded` (skip: summary.logs.agents.loki_metrics missing), `observability.promtail-dropped` (skip: summary.logs.agents.promtail missing), `observability.log-error-ratio-high` (skip: summary.logs.loki.namespaces_1h missing), `observability.unstructured-logs` (skip: summary.logs.loki.namespaces_1h missing), `node.kubelet-api-qps-low` (skip: nothing to judge: node not read, or kubelet not read (2)), `traffic.ingress-5xx-ratio` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (31)), `traffic.ingress-p95-latency` (skip: nothing to judge: ingress metrics not read (ALB CloudWatch metrics or the ingress controller's Prometheus series) (31)), `node.docker-and-containerd` (skip: nothing to judge: node not read (2)), `node.container-writable-layer-large` (skip: nothing to judge: node not read (2)), `node.large-images` (skip: nothing to judge: node not read (2)), `platform.k3s-check-config-missing` (skip: nothing to judge: no k3s server's platform file read (logs/node/<node>/k3s-platform.txt)), `platform.k3s-apiserver-bind-all` (skip: nothing to judge: no k3s server's platform file read (logs/node/<node>/k3s-platform.txt)), `node.smartmontools-missing` (skip: nothing to judge: nodes not collected (2)), `platform.k3s-datastore-slow` (skip: nothing to judge: k3s datastore not read (no server node's k3s-platform.txt)), `storage.local-path-over-capacity` (skip: node directory sizes not read (the k3s-platform node step's du section: no node access)), `traffic.metallb-l2-leader-concentration` (skip: nothing to judge: no L2 announcement to judge, or L2 leaders not read or read from only some speakers (metrics over TLS with authentication and no status resources)), `traffic.metallb-single-lb-service` (skip: nothing to judge: L2 leaders not read, or read from only some speakers), `traffic.metallb-service-ip-not-announced` (skip: nothing to judge: the announcing nodes were not read (speaker metrics from only some speakers, status objects not written before 0.14.6, ServiceBGPStatus not before 0.15.0) and the pool has an advertisement or the IP is in no IPAddressPool, so the config alone does not decide)
- Judged in part 2 (some targets lacked what the rule needs; those are not judged, not passed): `platform.k3s-secrets-encryption-off` (1 not judged: k3s server platform file not read (logs/node/<node>/k3s-platform.txt)), `platform.k3s-etcd-snapshot-local-only` (1 not judged: k3s server platform file not read (logs/node/<node>/k3s-platform.txt))
- Query returned no series 7 (every metric name the query reads has series, so nothing happened; a name with no series would be a skip): `resources.oomkilled`, `resources.large-request-binpacking`, `observability.scrape-targets-down`, `observability.alert-firing-stale`, `node.network-errors`, `controlplane.apiserver-401-rate`, `scaling.pod-pending-long`

## 7. Appendix

### 7-1. Collectors and steps run

| Collector | Steps | Failed | Skipped (reason) |
|---|---|---|---|
| core | 13 |  | node-os (no node command backend) |
| k3s-platform | 8 |  | k3s-journal-errors (no node command backend); k3s-journal-stats (no node command backend); k3s-scheduler-unschedulable (no node command backend); k3s-webhook-failures (no node command backend); k3s-etcd-slow (no node command backend); kubelet-pleg (no node command backend); k3s-node (no node command backend); containerd-log (no node command backend) |
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
| istio | 0 |  | no collect.yaml (collector not implemented) |
| keda | 2 |  | operator-metrics (container arg --enable-prometheus-metrics=false: no metrics is expected) |
| kube-proxy | 2 |  | proxy-mode (no node command backend) |
| kube-state-metrics | 0 |  | no collect.yaml (collector not implemented) |
| local-path-provisioner | 1 |  |  |
| metallb | 2 |  |  |
| metrics-server | 0 |  | no collect.yaml (collector not implemented) |
| node-exporter | 0 |  | no collect.yaml (collector not implemented) |
| opentelemetry-collector | 0 |  | no collect.yaml (collector not implemented) |
| prometheus | 7 |  |  |
| prometheus-operator | 0 |  | no collect.yaml (collector not implemented) |
| reloader | 0 |  | no collect.yaml (collector not implemented) |
| tempo-jaeger | 0 |  | no collect.yaml (collector not implemented) |

Kinds this cluster does not serve (8; a check that needs one of them is skipped, not passed): `autoscalingrunnersets.actions.github.com`, `configurationstates.metallb.io`, `nodeclaims.karpenter.sh`, `nodepools.karpenter.sh`, `servicebgpstatuses.metallb.io`, `targetgroupbindings.elbv2.k8s.aws`, `volumesnapshotclasses.snapshot.storage.k8s.io`, `volumesnapshots.snapshot.storage.k8s.io`

388 commands, 285.9 s. Failed steps: 0

Commands that failed inside a step that still succeeded (run.log): 1: `metallb.metallb-speaker-metrics.speaker-spdvw` Unable to connect to the server: context deadline exceeded

Deprecated-API tools: kubent 28 of 41 Lists answered (13 refused or not served); pluto 136 of 136 object kinds saved (0 not permitted or failed); kubent had 201 objects with a last-applied annotation to judge; pluto had 386 objects with a last-applied annotation to judge.

### 7-2. Checks evaluated

349 checks: disabled 44, done 263, llm 2, skip 40. Load errors: none.

### 7-3. Signature matches and unclassified errors

Signature catalog 1.1.1, 32 files, 22307 lines scanned (components: alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, fluent-bit, grafana, ingress-nginx, istio, keda, local-path-provisioner, metallb, metrics-server, opentelemetry-collector, prometheus, reloader, tempo-jaeger). Unclassified error lines: 593.

| Signature | Component | Area | Severity | Status | Count | First, last | Sample |
|---|---|---|---|---|---|---|---|
| prometheus.wal-corrupt | prometheus | observability | critical | warn | 2 | 2026-11-14T01:14:32Z , 2026-11-14T01:14:32Z | [pod/prometheus-kube-prometheus-stack-prometheus-0/prometheus] 2026-11-14T01:14:32.965707214Z time=2026-11-14T01:14:32.965Z level=WARN source=db.go:1019 … |
| fluent-bit.flush-failed | fluent-bit | observability | medium | warn | 19 | 2026-11-14T15:32:37Z , 2026-11-14T16:00:37Z | [pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:32:37.046394759+09:00 [2026/11/14 15:32:37] [ warn] [engine] failed to flush chunk … |
| metrics-server.scrape-failed | metrics-server | scaling | medium | warn | 12 | 2026-11-14T04:20:27Z , 2026-11-14T05:16:26Z | [pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:20:27.001662164Z E1114 04:20:27.001301       1 scraper.go:147] "Failed to scrape node … |
| fluent-bit.upstream-down | fluent-bit | observability | medium | warn | 6 | 2026-11-14T15:34:47Z , 2026-11-14T16:02:42Z | [pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:34:47.046295347+09:00 [2026/11/14 15:34:47] [error] [input:kubernetes_events:kubernetes_events.1] upstream … |
| cert-manager.challenge-failed | cert-manager | security | medium | info | 2 | 2026-11-14T02:32:10Z , 2026-11-14T02:32:10Z | [pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:10.835366346Z E1114 02:32:10.835319       1 sync.go:190] "propagation check … |
| metallb.speaker-peer-unreachable | metallb | traffic | low | warn | 545 | 2026-11-14T12:24:07Z , 2026-11-14T16:03:17Z | [pod/speaker-lqmcg/speaker] 2026-11-14T12:43:57.490323576Z {"caller":"speakerlist.go:259","error":"1 error occurred:\n\t* Failed to join <ip>:7946 … |
| common.context-deadline | any | traffic | low | info | 16 | 2026-11-14T01:13:27Z , 2026-11-14T01:14:21Z | [pod/argocd-server-d5888bf9-l9bkc/argocd-server] 2026-11-14T01:13:27.438970721Z {"level":"warning","msg":"Failed to resync revoked tokens. retrying again in 1 … |
| cert-manager.orphan-tls-secret | cert-manager | hygiene | low | warn | 16 | 2026-11-14T01:14:00Z , 2026-11-14T01:14:00Z | [pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701159812Z E1114 01:14:00.701036       1 indexers.go:61] "unable to … |
| common.connection-refused | any | traffic | low | info | 1 | 2026-11-14T01:13:16Z , 2026-11-14T01:13:16Z | [pod/prometheus-kube-prometheus-stack-prometheus-0/config-reloader] 2026-11-14T01:13:16.842997721Z level=error ts=2026-11-14T01:13:16.84285723Z … |

| Normalized message | Count | Files |
|---|---|---|
| cert-manager \| "re-queuing item due to error processing" err="ACME client for issuer not initialised/available" logger="cert-manager.orders" … | 390 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:43 +<n>] "GET … | 5 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:42 +<n>] "GET … | 4 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:44 +<n>] "GET … | 3 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-key-manager" key="app-c-prod/app-c-tls" … | 2 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:45:46 +<n>] "GET … | 2 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:45:51 +<n>] "GET … | 2 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:41 +<n>] "GET … | 2 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:55:34 +<n>] "GET … | 2 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| argocd \| 1:M 14 Nov <n> 01:13:23.<n> * < bf> 	{ bf-error-rate       :      0.01 } | 1 | logs/pods/argocd/argocd_argocd-redis.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificaterequests-issuer-acme" key="app-c-prod/app-c-tls-5" … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| ingress 'app-c-prod/cm-acme-http-solver-7tc6d' in work queue no longer exists | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "failed to update status" logger="cert-manager.orders" resource_name="app-c-tls-5-<n>" resource_namespace="app-c-prod" resource_kind="Order" … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.orders" key="app-c-prod/app-c-tls-5-<n>" error="Operation cannot … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "challenge in work queue no longer exists" err="challenge.acme.cert-manager.io \"app-c-tls-5-<n>-<n>\" not found" … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-readiness" key="app-c-prod/app-c-tls" … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| cert-manager \| "re-queuing item due to optimistic locking on resource" logger="cert-manager.certificates-issuing" key="app-c-prod/app-c-tls" error="Operation … | 1 | logs/pods/cert-manager/cert-manager_cert-manager.log |
| elasticsearch-opensearch \| [<ts>][ERROR][o.o.p.c.c.PluginSettings ] [app-ac-opensearch-0] Loading config file … | 1 | logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log |
| elasticsearch-opensearch \| [<ts>][ERROR][o.o.p.c.c.StatsCollector ] [app-ac-opensearch-0] Error in loading metadata for folderLocation: … | 1 | logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log |
| elasticsearch-opensearch \| [<ts>][WARN ][stderr                   ] [app-ac-opensearch-0] SLF4J: Failed to load class "org.slf4j.impl.StaticLoggerBinder". | 1 | logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log |
| elasticsearch-opensearch \| [<ts>][WARN ][o.o.s.SecurityAnalyticsPlugin] [app-ac-opensearch-0] Failed to initialize LogType config index and builtin log types | 1 | logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log |
| grafana \| logger=infra.usagestats.collector t=<ts> level=error msg="Failed to read all Amazon Prometheus data sources" error="plugin … | 1 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| grafana \| logger=infra.usagestats t=<ts> level=error msg="Failed to fetch usage stats from provider" error="plugin … | 1 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| grafana \| logger=infra.usagestats.collector t=<ts> level=error msg="Failed to get advisor usage stats" error="the server could not find the requested … | 1 | logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:17:03 +<n>] "GET /app-ac/app/factors/single-point-of-failure HTTP/2.0" <n> <n> "-" "Mozilla/5.0 … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:23:33 +<n>] "GET /app-ac/app?symptom=autoscaler-scale-up-failed HTTP/2.0" <n> <n> "-" "Mozilla/5.0 … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:25:29 +<n>] "GET /app-ac/app?root_cause=capacity&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0" <n> <n> … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:25:30 +<n>] "GET /app-ac/app?root_cause=capacity&factor=single-point-of-failure&_rsc=eqsiq HTTP/2.0" <n> <n> … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:41 +<n>] "GET /app-ac/app/cases/IL-<n>?_rsc=eqsiq HTTP/2.0" <n> <n> … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |
| ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:42 +<n>] "GET /app-ac/app/ko?root_cause=software-bug&component=conntrack&symptom=high-error-rate&_rsc=eqsiq … | 1 | logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log |

### 7-4. Raw files the LLM read directly

(not written this run)

### 7-5. Full first-pass status (every fail and warn, code results as-is)

| id | Status | Default severity | Evidence |
|---|---|---|---|
| `logs.signatures.prometheus.wal-corrupt` | warn | critical | 2 occurrences (2026-11-14T01:14:32Z ~ 2026-11-14T01:14:32Z), thresholds warn 1/fail 10. Files: ['logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log']. Samples: ['[pod/prometheus-kube-prometheus-stack-prometheus-0/prometheus] 2026-11-14T01:14:32.965707214Z … |
| `resilience.no-backup.cluster` | warn | critical | no backup tool (family backup). Alternative signals: etcd snapshots 5, backup-like CronJobs that ran in the last 7 days ['app-a-prod/app-a-postgres-backup', 'app-f-prod/app-f-postgres-backup', 'app-f-prod/app-f-postgres-mx-backup', 'app-f-prod/app-f-postgres-vn-backup' … |
| `argocd.prune-manages-namespace-or-crd.cluster` | fail | high | apps with prune enabled that manage a Namespace or CRD as a resource ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-d', 'argocd/application/app-g-api', 'argocd/application/app-ac-prod', 'argocd/application/istio' … |
| `observability.alertmanager-notification-failed.slack` | fail | high | 8 of 60 notifications failed in 24h, the other 52 were delivered (integration slack, which is how the receiver is configured and not necessarily where it delivers: a Discord webhook is often called through the slack integration) |
| `platform.k8s-version-eol.cluster` | fail | high | server v1.33.5+k3s1: upstream end of life 2026-06-28, 140 days past |
| `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | fail | high | storage emptyDir (PVC None), PVC usage None, TSDB 22.3GiB, retention 30d (size cap 0B), actual oldest sample 31.2 days, failed compactions over 7 days 0, WAL corruptions 1, corruptions at startup 1 |
| `resources.cpu-throttling.app-a-prod/ds/app-a-sandbox-prepull:hold-python` | fail | high | pod app-a-sandbox-prepull-8xvrq: throttling ratio now 0.00, 24 h or the pod's life 0.33: throttled through the day; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.app-g-api/sts/app-g-postgres:postgres` | fail | high | pod app-g-postgres-0: throttling ratio now 0.16, 24 h or the pod's life 0.26: throttled through the day |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-admin:app` | fail | high | ["pod app-h-admin-6789875894-2qz6d: throttling ratio now 0.46, 24 h or the pod's life 0.46: throttled through the day", "pod app-h-admin-6789875894-pwhh4: throttling ratio now 0.52, 24 h or the pod's life 0.05: throttled this moment, not through the day"] |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-api-server:app` | fail | high | ["pod app-h-api-server-7ccdccd9f8-7wvxl: throttling ratio now 0.00, 24 h or the pod's life 0.61: throttled through the day; no 5-minute value, under 0.01 now", "pod app-h-api-server-7ccdccd9f8-r6xdr: throttling ratio now 0.00, 24 h or the pod's life 0.55: throttled through the day; no 5-minute value … |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-app-q-client:app` | fail | high | ["pod app-h-app-q-client-754b8c5b59-nszv9: throttling ratio now 0.00, 24 h or the pod's life 0.30: throttled through the day; no 5-minute value, under 0.01 now", "pod app-h-app-q-client-754b8c5b59-g8x5q: throttling ratio now 0.00, 24 h or the pod's life 0.27: throttled through the day; no 5-minute value … |
| `resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit` | fail | high | ["pod fluent-bit-bmdwx: throttling ratio now 0.27, 24 h or the pod's life 0.31: throttled through the day", "pod fluent-bit-wzbvh: throttling ratio now 0.32, 24 h or the pod's life 0.42: throttled through the day"] |
| `resources.cpu-throttling.logging/pod/fluent-bit-qcjbv:fluent-bit` | fail | high | pod fluent-bit-qcjbv: throttling ratio now 0.00, 24 h or the pod's life 0.28: throttled through the day; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.logging/sts/elasticsearch:elasticsearch` | fail | high | pod elasticsearch-0: throttling ratio now 0.34, 24 h or the pod's life 0.37: throttled through the day |
| `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | high | pod prometheus-kube-prometheus-stack-prometheus-0: throttling ratio now 0.61, 24 h or the pod's life 0.45: throttled through the day |
| `resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio` | fail | high | pod app-g-minio-0: 7d memory working set p95 / limit = 0.95 |
| `resources.oomkilled-repeated.monitoring/sts/tempo:tempo` | fail | high | kernel log not read in this mode. Prometheus: 1 pod ended by OOM in 7 days, 1 already replaced, 163 restarts in those pods (none of those pods is running now). cAdvisor counter 0. Running now: tempo-0 (created 2026-11-12T16:12:17Z, 1 restart of this container since) |
| `controlplane.apiserver-5xx.cluster` | warn | high | 5xx per second 0.004 (code 503) |
| `node.disk-usage.192.168.90.101:9100:/` | warn | high | usage 0.75 |
| `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | high | working set / limit 0.752 (limit 1536Mi), active series 174075, Prometheus container last terminated OOMKilled False (None), restarts 6, OOMKilled containers in the monitoring namespace [], restarts over 7 days {'kube-prometheus-stack-prometheus-node-exporter-5wh9f': 2 … |
| `resilience.backup-same-node.app-a-prod/app-a-postgres-backup` | warn | high | app-a-prod/app-a-postgres-backup: schedule '15 3 * * *', dump PVCs ['app-a-postgres-backup-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-a-prod/statefulset/app-a-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-f-prod/app-f-postgres-backup` | warn | high | app-f-prod/app-f-postgres-backup: schedule '30 3 * * *', dump PVCs ['app-f-postgres-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-f-prod/statefulset/app-f-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-f-prod/app-f-postgres-mx-backup` | warn | high | app-f-prod/app-f-postgres-mx-backup: schedule '30 3 * * *', dump PVCs ['app-f-postgres-mx-backup-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-f-prod/statefulset/app-f-postgres-mx', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-f-prod/app-f-postgres-vn-backup` | warn | high | app-f-prod/app-f-postgres-vn-backup: schedule '30 3 * * *', dump PVCs ['app-f-postgres-vn-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-f-prod/statefulset/app-f-postgres-vn', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-g-api/app-g-postgres-backup` | warn | high | app-g-api/app-g-postgres-backup: schedule '50 3 * * *', dump PVCs ['app-g-postgres-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-g-api/statefulset/app-g-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-h-prod/app-h-mysql-backup` | warn | high | app-h-prod/app-h-mysql-backup: schedule '50 2 * * *', dump PVCs ['app-h-mysql-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-h-prod/statefulset/app-h-mysql', 'node-b'), ('app-h-prod/statefulset/app-h-mysql', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.kube-system/etcd-snapshot-backup` | warn | high | kube-system/etcd-snapshot-backup: schedule '30 0,12 * * *', dump PVCs ['etcd-snapshot-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [], off-node copy hint (s3, rclone, restic) False |
| `resilience.backup-same-node.app-i-prod/app-i-postgres-backup` | warn | high | app-i-prod/app-i-postgres-backup: schedule '0 3 * * *', dump PVCs ['app-i-postgres-backup-node-a-pvc'] → nodes ['node-a'], hostPath [], source DB [('app-i-prod/statefulset/app-i-postgres', 'node-b')], off-node copy hint (s3, rclone, restic) False |
| `resources.cpu-throttling.app-a-prod/deploy/app-a-frontend:frontend` | warn | high | ["pod app-a-frontend-799cb7b64c-pxbj6: throttling ratio now 0.00, 24 h or the pod's life 0.15: throttled through the day, below the fail line; no 5-minute value, under 0.01 now", "pod app-a-frontend-799cb7b64c-zq69f: throttling ratio now 0.00, 24 h or the pod's life 0.20: throttled … |
| `resources.cpu-throttling.app-a-prod/pod/app-a-backend-migrate-8shv7:migrate` | warn | high | pod app-a-backend-migrate-8shv7: throttling ratio now 0.00, 24 h or the pod's life 0.16: throttled through the day, below the fail line; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-8bxwr:runner` | warn | high | pod lab-a-runner-g55w4-8bxwr: throttling ratio now 0.00, 24 h or the pod's life 0.14: throttled through the day, below the fail line; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-c7j6m:runner` | warn | high | pod lab-a-runner-g55w4-c7j6m: throttling ratio now 0.00, 24 h or the pod's life 0.12: throttled through the day, below the fail line; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-fzj9v:runner` | warn | high | pod lab-a-runner-g55w4-fzj9v: throttling ratio now 0.00, 24 h or the pod's life 0.11: throttled through the day, below the fail line; no 5-minute value, under 0.01 now |
| `resources.cpu-throttling.app-f-prod/sts/app-f-postgres-mx:postgres` | warn | high | pod app-f-postgres-mx-0: throttling ratio now 0.15, 24 h or the pod's life 0.12: throttled through the day, below the fail line |
| `resources.cpu-throttling.app-h-prod/deploy/app-h-app-p:app` | warn | high | ["pod app-h-app-p-7c8bbfbcc6-wj8sd: throttling ratio now 0.00, 24 h or the pod's life 0.21: throttled through the day, below the fail line; no 5-minute value, under 0.01 now", "pod app-h-app-p-7c8bbfbcc6-wf242: throttling ratio now 0.00, 24 h or the pod's life 0.17: throttled through the day, below … |
| `resources.oomkilled-repeated.app-ac-prod/deploy/app-ac-ai:ai` | warn | high | kernel log not read in this mode. Prometheus: 1 pod ended by OOM in 7 days, 1 already replaced, 1 restarts in those pods (none of those pods is running now). cAdvisor counter 0. Running now: app-ac-ai-74b95b458b-qzrtl (created 2026-11-14T04:23:03Z, 0 restarts of this container since) |
| `security.plaintext-configmap-secret.default/configmap/app-ai-backend-config` | warn | high | default/configmap/app-ai-backend-config: keys ['JWT_RELAY_SECRET', 'JWT_SECRET', 'TWITTER_CLIENT_SECRET', 'TWITTER_CLIENT_SECRET_RELAY'], mounted/referenced by [] |
| `storage.local-path-fs-near-full.cluster` | warn | high | root filesystem per node {'node-a': {'avail_ratio': 0.247, 'size_gib': 106.7, 'growth_gib_per_day': 0.91, 'avail_gib': 26.4, 'days_to_full': 29, 'volumes_gib': 0.0}, 'node-b': {'avail_ratio': 0.414, 'size_gib': 454.9, 'growth_gib_per_day': 2.31, 'avail_gib': 188.3, 'days_to_full': 82, 'volumes_gib' … |
| `traffic.metallb-config-stale.cluster` | warn | high | source metrics: components with stale/unloaded config [], errors [], not reported ['speaker-spdvw'], k8s client update errors 0, ARP requests/responses 0/0, gratuitous ARP 24, BGP sessions up 0/0 |
| `traffic.metallb-speaker-not-ready.cluster` | warn | high | 1 LoadBalancer services, speaker ready 2/2 (2 nodes, all nodes True, nodes it can run on 2), controller 1/1, speakers with metrics read 1, unreadable [{'pod': 'speaker-spdvw', 'node': 'node-a', 'error': 'Unable to connect to the server: context deadline exceeded'}], version 0.14.5, mode layer2 |
| `controlplane.apiserver-latency.PATCH` | fail | medium | PATCH p99 1.720s |
| `coredns.availability.cluster` | fail | medium | replicas 1, nodes with pods 1 of 2 ({'node-b': 1}), PDB [], spread declared (antiAffinity/topologySpread) True, restarts total 2 |
| `coredns.nxdomain-ratio-high.cluster` | fail | medium | NXDOMAIN share of responses in 1h 0.699, queries per second 31.75, NXDOMAIN share of queries forwarded upstream 0.849 (upstreams ['1.1.1.1:53', '8.8.8.8:53']), pods with default ndots (5) 145, autopath False, cache hit ratio 0.8453 |
| `eso.store-static-credentials.cluster` | fail | medium | stores with static key auth ['ClusterSecretStore/aws-secret-store'] (all auth methods {'ClusterSecretStore/aws-secret-store': 'static-key(Secret)'}), providers ['aws'], ExternalSecrets 44 (prod 36) |
| `hygiene.polaris-reliability-danger.app-a-prod/daemonset/app-a-sandbox-prepull` | fail | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['livenessProbeMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet', 'readinessProbeMissing', 'topologySpreadConstraint']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in the security … |
| `observability.alerts-always-firing.CPUThrottlingHigh` | fail | medium | 7d firing samples 56248 (same level as Watchdog = never stops firing) |
| `observability.alerts-always-firing.KubeJobFailed` | fail | medium | 7d firing samples 31855 (same level as Watchdog = never stops firing) |
| `observability.failure-mode-uncovered.OOMKill` | fail | medium | user symptom: pods die and requests fail or slow down. No alert rule covers this failure mode |
| `observability.ingress-controller-metrics-missing.ingress-controller` | fail | medium | 31 ingresses, 0 ingress-controller request metric series, namespaces with app http_* metrics ['istio-system'], ALB CloudWatch False — per-backend gaps are the 31 golden-signals-missing (warn) findings |
| `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager` | fail | medium | emptyDir volumes: config-out, alertmanager-kube-prometheus-stack-alertmanager-db, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana` | fail | medium | emptyDir volumes: storage, sc-dashboard-volume, sc-datasources-volume, replicas 1 |
| `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus` | fail | medium | emptyDir volumes: config-out, prometheus-kube-prometheus-stack-prometheus-db, replicas 1 |
| `operators.webhook-self-lock.istiod-default-validator:validation.istio.io` | fail | medium | Validating, failurePolicy Fail, targets ['*'], namespaceSelector None does not exclude its own namespace istio-system |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-postgres:postgres` | fail | medium | app-a-prod/statefulset/app-a-postgres container postgres: liveness exec timeout 1s, period 15s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-a-prod/statefulset/app-a-redis:redis` | fail | medium | app-a-prod/statefulset/app-a-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-c-prod/statefulset/app-c-postgres:postgres` | fail | medium | app-c-prod/statefulset/app-c-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-mx:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres-mx container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres-vn:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres-vn container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-postgres:postgres` | fail | medium | app-f-prod/statefulset/app-f-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-f-prod/statefulset/app-f-redis:redis` | fail | medium | app-f-prod/statefulset/app-f-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-h-prod/statefulset/app-h-mysql:mysql` | fail | medium | app-h-prod/statefulset/app-h-mysql container mysql: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-h-prod/statefulset/app-h-qdrant:qdrant` | fail | medium | app-h-prod/statefulset/app-h-qdrant container qdrant: liveness httpGet timeout 1s, period 10s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-neo4j:neo4j` | fail | medium | app-ac-prod/statefulset/app-ac-neo4j container neo4j: liveness tcpSocket timeout 1s, period 20s, failureThreshold 3, readiness tcpSocket timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-opensearch:opensearch` | fail | medium | app-ac-prod/statefulset/app-ac-opensearch container opensearch: liveness httpGet timeout 1s, period 20s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-postgres:postgres` | fail | medium | app-ac-prod/statefulset/app-ac-postgres container postgres: liveness exec timeout 1s, period 15s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-redis:redis` | fail | medium | app-ac-prod/statefulset/app-ac-redis container redis: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-i-prod/statefulset/app-i-postgres:postgres` | fail | medium | app-i-prod/statefulset/app-i-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-l-prod/deployment/app-l-postgres:postgres` | fail | medium | app-l-prod/deployment/app-l-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.n-plus-one.cluster` | fail | medium | Allocatable without the largest node node-b (12.0 cores, 30.7GB): CPU 6.0 cores vs total requests 7.69 (short), memory 30.7GB vs 31.1GB (OK). Pods on that node 80 (prod 39). Pods that fit on no other node [{'namespace': 'app-a-prod', 'pod': 'app-a-postgres-0', 'node': 'node-b', 'cpu': 0.2 … |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-backend` | fail | medium | replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway` | fail | medium | replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.app-f-prod/deployment/app-f` | fail | medium | replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [{'key': 'kubernetes.io/hostname', 'max_skew': 1, 'when': 'DoNotSchedule'}], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.shell-pid1-no-prestop.app-ac-prod/statefulset/app-ac-redis` | fail | medium | Containers whose command is sh -c ['redis'], no preStop, terminationGracePeriodSeconds 30 |
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
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-ai` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-api` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-istio` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-mcp` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-projector` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-ac-prod/app-ac-web` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-api` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-postgres` | fail | medium | replicas 1, no HPA |
| `resilience.single-replica-in-prod.app-l-prod/app-l-web` | fail | medium | replicas 1, no HPA |
| `resources.krr-recommendation.app-a-prod/deployment/app-a-backend:backend` | fail | medium | memory request under by 890 MB: CPU HPA detected, memory request 256 → 1146 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req CRITICAL, memory limit OK). cpu: HPA detected |
| `resources.krr-recommendation.app-a-prod/deployment/app-a-umami:umami` | fail | medium | memory request under by 369 MB: CPU request 0.05 → 0.067 cores, CPU limit 0.3 → none, memory request 128 → 497 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.app-a-prod/statefulset/app-a-postgres:postgres` | fail | medium | memory request under by 1546 MB, CPU request over by 0.138 cores: CPU request 0.2 → 0.062 cores, CPU limit 1.0 → none, memory request 512 → 2058 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req CRITICAL, memory limit GOOD) |
| `resources.krr-recommendation.app-g-api/statefulset/app-g-minio:minio` | fail | medium | memory request under by 454 MB: CPU request 0.05 → 0.012 cores, CPU limit 0.3 → none, memory request 128 → 582 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit GOOD) |
| `resources.krr-recommendation.app-h-prod/deployment/app-h-embed:app` | fail | medium | CPU request over by 0.488 cores, memory request over by 1168 MB: CPU request 0.5 → 0.012 cores, CPU limit 2.0 → none, memory request 2048 → 880 MB, memory limit 4096 → 880 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.app-ac-prod/deployment/app-ac-ai:ai` | fail | medium | memory request under by 3579 MB, CPU request under by 5.262 cores: CPU request 0.5 → 5.762 cores, memory request 3072 → 6651 MB, memory limit 6144 → 6651 MB. KRR severity CRITICAL (CPU req CRITICAL, CPU limit GOOD, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.app-ac-prod/deployment/app-ac-api:api` | fail | medium | memory request under by 623 MB, CPU request under by 0.366 cores: CPU request 0.1 → 0.466 cores, memory request 256 → 879 MB. KRR severity CRITICAL (CPU req WARNING, CPU limit GOOD, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.app-ac-prod/statefulset/app-ac-opensearch:opensearch` | fail | medium | memory request under by 522 MB, CPU request over by 0.152 cores: CPU request 0.2 → 0.048 cores, CPU limit 2.0 → none, memory request 1536 → 2058 MB, memory limit 2560 → 2058 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req CRITICAL, memory limit CRITICAL) |
| `resources.krr-recommendation.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller` | fail | medium | memory request under by 431 MB: CPU request 0.1 → 0.01 cores, memory request 90 → 521 MB, memory limit None → 521 MB. KRR severity WARNING (CPU req GOOD, CPU limit GOOD, memory req WARNING, memory limit WARNING) |
| `resources.krr-recommendation.logging/statefulset/elasticsearch:elasticsearch` | fail | medium | memory request under by 766 MB: CPU request 0.2 → 0.31 cores, CPU limit 0.6 → none, memory request 2048 → 2814 MB, memory limit 3072 → 2814 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req CRITICAL, memory limit WARNING) |
| `resources.krr-recommendation.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus` | fail | medium | memory request under by 625 MB: CPU request 0.2 → 0.12 cores, CPU limit 0.3 → none, memory request 1024 → 1649 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req CRITICAL, memory limit OK) |
| `resources.krr-recommendation.monitoring/statefulset/tempo:tempo` | fail | medium | memory request under by 629 MB: CPU request 0.05 → 0.019 cores, memory request 1024 → 1653 MB, memory limit 2048 → 1653 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit GOOD, memory req CRITICAL, memory limit WARNING) |
| `scaling.hpa-flapping.app-h-prod/hpa/app-h-api-server` | fail | medium | 64 desired changes over 7 days |
| `security.networkpolicy-coverage.cluster` | fail | medium | 21 of 24 user namespaces have no NetworkPolicy, of which production ['app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-ac-prod', 'app-i-prod', 'app-l-prod']; with: ['app-a-prod', 'argocd', 'istio-system'] |
| `security.polaris-security-danger.cluster` | fail | medium | Polaris score 75. Security danger workloads 115 (prod 78): per check {'privilegeEscalationAllowed': 100, 'runAsRootAllowed': 94, 'runAsPrivileged': 3, 'sensitiveContainerEnvVar': 8, 'hostPIDSet': 3, 'hostNetworkSet': 3, 'rolebindingClusterAdminRole': 1, 'rolebindingRolePodExecAttach': 2 … |
| `security.privileged-or-host-access.app-ac-prod/statefulset/app-ac-opensearch` | fail | medium | ['privileged:sysctl'], containers allowing root ['opensearch', 'sysctl'] |
| `security.secrets-read-permission.istio-reader-clusterrole-istio-system` | fail | medium | ClusterRole istio-reader-clusterrole-istio-system: secrets get/list, bound subjects [('ServiceAccount', 'istio-system', 'istio-reader-service-account')] |
| `security.secrets-read-permission.istiod-clusterrole-istio-system` | fail | medium | ClusterRole istiod-clusterrole-istio-system: secrets get/list, bound subjects [('ServiceAccount', 'istio-system', 'istiod')] |
| `security.secrets-read-permission.kiali` | fail | medium | ClusterRole kiali: secrets get/list, bound subjects [('ServiceAccount', 'istio-system', 'kiali')] |
| `tenancy.burst-tenant-unbounded.app-ac-prod` | fail | medium | app-ac-prod (prod): 7d CPU median 0.06 cores, p95 0.918 cores, max 5.833 cores = 96.7x the median. No quota, shares nodes with prod True, nodes {'node-a': 5, 'node-b': 5}, CPU limit total 10.2 cores |
| `tenancy.prod-boundary-missing.app-c-prod` | fail | medium | app-c-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 1. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-boundary-missing.app-f-prod` | fail | medium | app-f-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-boundary-missing.app-h-prod` | fail | medium | app-h-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-boundary-missing.app-ac-prod` | fail | medium | app-ac-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-boundary-missing.app-i-prod` | fail | medium | app-i-prod: ResourceQuota False, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-without-quota.app-c-prod` | fail | medium | app-c-prod (prod): no ResourceQuota. Pods 4, CPU requests total 0.17 cores, memory requests total 0.66GB, 7d CPU p95 0.013 cores (cluster share 0.005), memory p95 0.23GB, 7d max/median Nonex. Tenants in this cluster 13, shares nodes with prod True |
| `tenancy.prod-without-quota.app-f-prod` | fail | medium | app-f-prod (prod): no ResourceQuota. Pods 12, CPU requests total 0.49 cores, memory requests total 3.91GB, 7d CPU p95 0.03 cores (cluster share 0.012), memory p95 1.69GB, 7d max/median 3.0x. Tenants in this cluster 13, shares nodes with prod True |
| `tenancy.prod-without-quota.app-h-prod` | fail | medium | app-h-prod (prod): no ResourceQuota. Pods 10, CPU requests total 1.12 cores, memory requests total 6.75GB, 7d CPU p95 0.094 cores (cluster share 0.037), memory p95 4.84GB, 7d max/median 30.8x. Tenants in this cluster 13, shares nodes with prod True |
| `tenancy.prod-without-quota.app-ac-prod` | fail | medium | app-ac-prod (prod): no ResourceQuota. Pods 10, CPU requests total 1.62 cores, memory requests total 7.19GB, 7d CPU p95 0.918 cores (cluster share 0.362), memory p95 4.76GB, 7d max/median 96.7x. Tenants in this cluster 13, shares nodes with prod True |
| `tenancy.prod-without-quota.app-i-prod` | fail | medium | app-i-prod (prod): no ResourceQuota. Pods 2, CPU requests total 0.1 cores, memory requests total 0.28GB, 7d CPU p95 0.006 cores (cluster share 0.003), memory p95 0.25GB, 7d max/median Nonex. Tenants in this cluster 13, shares nodes with prod True |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-external` | fail | medium | nodeport app-f-prod/app-f-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-mx-external` | fail | medium | nodeport app-f-prod/app-f-postgres-mx-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-f-prod/app-f-postgres-vn-external` | fail | medium | nodeport app-f-prod/app-f-postgres-vn-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `traffic.db-exposed.nodeport/app-i-prod/app-i-postgres-external` | fail | medium | nodeport app-i-prod/app-i-postgres-external: ports [5432], exposure node-ip (all node interfaces), addresses [], sourceRanges None, security group not applicable. DB port open on an external address |
| `argocd.admin-account-no-sso.cluster` | warn | medium | admin.enabled True, SSO (dex/oidc) False, anonymous False, RBAC policy.default '' / policy.csv 0 lines, exec.enabled False, URL None |
| `argocd.app-out-of-sync-or-unhealthy.cluster` | warn | medium | Applications 22 (prod 11), OutOfSync ['argocd/application/root'] (prod []), Degraded/Missing/Unknown [] (prod []), Progressing (rolling out, not abnormal) [], apps with conditions ['ExcludedResourceWarning']: ['argocd/application/app-n'], last operation failed [] |
| `argocd.default-project-wildcard.cluster` | warn | medium | AppProjects 2, projects whose sourceRepos and destinations are all * ['default'], apps bound to the default project 7/22 (prod 11) |
| `controlplane.apiserver-latency.LIST` | warn | medium | LIST p99 0.823s |
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
| `hygiene.node-label-dependency.storage` | warn | medium | Label storage: 14 workloads (production 11) depend on it via nodeSelector/affinity, present on 1/2 nodes — e.g. ['app-a-prod/statefulset/app-a-postgres', 'app-a-prod/statefulset/app-a-redis', 'app-f-prod/statefulset/app-f-postgres'] and 11 more |
| `hygiene.polaris-reliability-danger.registry/cronjob/registry-tag-cleanup` | warn | medium | Polaris danger (Reliability, Efficiency) ['tagNotSpecified'], warning ['cpuLimitsMissing', 'cpuRequestsMissing', 'memoryLimitsMissing', 'memoryRequestsMissing', 'metadataAndInstanceMismatched', 'priorityClassNotSet']. Security-category danger ['privilegeEscalationAllowed', 'runAsRootAllowed'] is in … |
| `hygiene.pvc-unbound-or-unused.cluster` | warn | medium | Non-Bound PVCs [], Released/Failed PVs [], Bound PVCs used by no pod [('default', 'data-app-ah-db-0')] |
| `logs.signatures.fluent-bit.flush-failed` | warn | medium | 19 occurrences (2026-11-14T15:32:37Z ~ 2026-11-14T16:00:37Z), thresholds warn 10/fail 500. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ["[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:32:37.046394759+09:00 [2026/11/14 15:32:37] [ warn] [engine] failed to flush chunk … |
| `logs.signatures.fluent-bit.upstream-down` | warn | medium | 6 occurrences (2026-11-14T15:34:47Z ~ 2026-11-14T16:02:42Z), thresholds warn 5/fail 200. Files: ['logs/pods/fluent-bit/logging_fluent-bit.log']. Samples: ['[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:34:47.046295347+09:00 [2026/11/14 15:34:47] [error] … |
| `logs.signatures.metrics-server.scrape-failed` | warn | medium | 12 occurrences (2026-11-14T04:20:27Z ~ 2026-11-14T05:16:26Z), thresholds warn 5/fail 100. Files: ['logs/pods/metrics-server/kube-system_metrics-server.log']. Samples: ['[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:20:27.001662164Z E1114 04:20:27.001301       1 scraper.go:147] … |
| `observability.fluentbit-output-errors.cluster` | warn | medium | Output errors in 1h None, failed retries (dropped) None, dropped records None, input records None -- fluent-bit metrics are not in Prometheus (no ServiceMonitor). The numbers above were not measured, so they are not really 0 |
| `observability.golden-signals-missing.app-a-prod/app-a-backend` | warn | medium | hosts ['api.app-a.lab-a.example', 'api.lab-b.example'], backends ['app-a-backend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-frontend` | warn | medium | hosts ['app-a.lab-a.example', 'lab-b.example', 'www.lab-b.example'], backends ['app-a-frontend'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-phoenix` | warn | medium | hosts ['obs.lab-b.example'], backends ['app-a-phoenix'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-a-prod/app-a-umami` | warn | medium | hosts ['umami.lab-b.example', 'umami.lab-j.example'], backends ['app-a-umami'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.argocd/argocd-server-ingress` | warn | medium | hosts ['argocd.lab-a.example'], backends ['argocd-server'], no app http_* metrics, no ingress controller metrics, source none |
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
| `observability.golden-signals-missing.app-h-prod/app-h-app-q-client-ingress` | warn | medium | hosts ['app-h-app-q-client-prod.lab-a.example', 'lab-d.example', 'www.lab-d.example'], backends ['app-h-app-q-client-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-h-prod/app-h-app-p-ingress` | warn | medium | hosts ['app-h-app-p-prod.lab-a.example', 'lab-g.example', 'www.lab-g.example'], backends ['app-h-app-p-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-ac-prod/app-ac` | warn | medium | hosts ['app-ac.lab-j.example'], backends ['app-ac-istio'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-ac-prod/app-ac-machine` | warn | medium | hosts ['app-ac-api.lab-j.example', 'app-ac-mcp.lab-j.example'], backends ['app-ac-istio'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.logging/kibana` | warn | medium | hosts ['kibana.lab-a.example'], backends ['kibana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-i-prod/app-i-ingress` | warn | medium | hosts ['app-j.lab-a.example', 'lab-e.example', 'www.lab-e.example'], backends ['app-i-svc'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.monitoring/monitoring-grafana-ingress` | warn | medium | hosts ['grafana.lab-a.example'], backends ['kube-prometheus-stack-grafana'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-k/app-k` | warn | medium | hosts ['app-k.lab-a.example'], backends ['app-k'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.registry/registry` | warn | medium | hosts ['registry.lab-a.example'], backends ['registry'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-n/app-n` | warn | medium | hosts ['app-o.lab-a.example'], backends ['app-n-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-n/app-n-auth` | warn | medium | hosts ['app-o.lab-a.example'], backends ['app-n-workstation'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-l-prod/app-l-api` | warn | medium | hosts ['api.lab-f.example'], backends ['app-l-api'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.golden-signals-missing.app-l-prod/app-l-web` | warn | medium | hosts ['lab-f.example'], backends ['app-l-web'], no app http_* metrics, no ingress controller metrics, source none |
| `observability.no-symptom-alerts.cluster` | warn | medium | 163 alert rules: symptom 0, cause 155, app metrics (assumed symptom) 7. Symptom ratio 0.0. Symptom rules: [] |
| `observability.page-severity-cause-alerts.cluster` | warn | medium | of 163 alert rules, 45 are critical/page severity yet look only at cause metrics (container_*, node_*, kube_*) (e.g. ['AppQClusterCPU80', 'AppQClusterMem80', 'AppQBackendDown', 'AppQFrontendDown', 'AppQPostgresDown', 'AppQGatewayDown'] and 39 more), classes … |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-mx-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-f-prod/app-f-postgres-vn-backup` | warn | medium | schedule '30 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-h-prod/app-h-mysql-backup` | warn | medium | schedule '50 2 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-policy.app-i-prod/app-i-postgres-backup` | warn | medium | schedule '0 3 * * *', concurrencyPolicy Allow, activeDeadlineSeconds None, backoffLimit None, podFailurePolicy False, startingDeadlineSeconds None, ttl None, active Jobs 0. Gaps: ['concurrencyPolicy Allow (overlap allowed)', 'activeDeadlineSeconds missing (a stuck Job runs forever)', 'backoffLimit … |
| `resilience.cronjob-runtime-exceeds-interval.app-a-prod/app-a-sandbox-watchdog` | warn | medium | app-a-prod/app-a-sandbox-watchdog: schedule '* * * * *' (about 0.016666666666666666h), recent Job max 53s / median 53s = 0.88x the interval (1 measured), concurrencyPolicy Forbid, active Jobs 1 |
| `resilience.db-probe-timeout.app-g-api/statefulset/app-g-postgres:postgres` | warn | medium | app-g-api/statefulset/app-g-postgres container postgres: liveness exec timeout 1s, period 10s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.monitoring/statefulset/tempo:tempo` | warn | medium | monitoring/statefulset/tempo container tempo: liveness httpGet timeout 1s, period 20s, failureThreshold 3, readiness httpGet timeout 1s, startupProbe absent |
| `resilience.db-probe-timeout.app-k/deployment/app-k-postgres:postgres` | warn | medium | app-k/deployment/app-k-postgres container postgres: liveness exec timeout 1s, period 20s, failureThreshold 3, readiness exec timeout 1s, startupProbe absent |
| `resilience.priority-inversion.cluster` | warn | medium | User-defined PriorityClasses [], pod distribution {'(none, 0)': 103, 'system-cluster-critical': 1, 'system-node-critical': 3}, prod pods without a class 56 of 56, prod max priority 0, non-prod max 0, inversions [], Preempted events 0 |
| `resilience.prod-db-without-backup-cronjob.app-c-prod/statefulset/app-c-postgres` | warn | medium | statefulset app-c-postgres (Service app-c-postgres, PVC postgres-data-app-c-postgres-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.app-h-prod/statefulset/app-h-qdrant` | warn | medium | statefulset app-h-qdrant (Service app-h-qdrant, PVC app-h-qdrant-data-app-h-qdrant-0): no backup CronJob names it; the namespace's backup CronJobs dump other databases: app-h-mysql-backup -> app-h-mysql |
| `resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-neo4j` | warn | medium | statefulset app-ac-neo4j (Service app-ac-neo4j, PVC data-app-ac-neo4j-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-opensearch` | warn | medium | statefulset app-ac-opensearch (Service app-ac-opensearch, PVC data-app-ac-opensearch-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-postgres` | warn | medium | statefulset app-ac-postgres (Service app-ac-postgres, PVC data-app-ac-postgres-0): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.prod-db-without-backup-cronjob.app-l-prod/deployment/app-l-postgres` | warn | medium | deployment app-l-postgres (Service app-l-postgres, PVC app-l-postgres-data): no backup CronJob names it; the namespace has no backup CronJob |
| `resilience.replicas-same-node.app-a-prod/deployment/app-a-frontend` | warn | medium | replicas 2 (Running 2), node distribution {'node-b': 1, 'node-a': 1}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.replicas-same-node.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller` | warn | medium | replicas 2 (Running 2), node distribution {'node-b': 2}, AZ distribution {'null': 2}, topologySpread [], podAntiAffinity None, nodes eligible under scheduling constraints 2 |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-postgres` | warn | medium | app-a-prod/statefulset/app-a-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-a-prod/statefulset/app-a-redis` | warn | medium | app-a-prod/statefulset/app-a-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-c-prod/deployment/app-c-coturn` | warn | medium | app-c-prod/deployment/app-c-coturn: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['hostNetwork'], replicas 1, serves traffic False |
| `resilience.single-eligible-node.app-c-prod/statefulset/app-c-postgres` | warn | medium | app-c-prod/statefulset/app-c-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres` | warn | medium | app-f-prod/statefulset/app-f-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-mx` | warn | medium | app-f-prod/statefulset/app-f-postgres-mx: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-mx-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-postgres-vn` | warn | medium | app-f-prod/statefulset/app-f-postgres-vn: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-postgres-vn-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-f-prod/statefulset/app-f-redis` | warn | medium | app-f-prod/statefulset/app-f-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-f-redis-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-api/statefulset/app-g-minio` | warn | medium | app-g-api/statefulset/app-g-minio: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-g-minio-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-g-api/statefulset/app-g-postgres` | warn | medium | app-g-api/statefulset/app-g-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-g-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/deployment/app-h-embed` | warn | medium | app-h-prod/deployment/app-h-embed: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['extended resource nvidia.com/gpu'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/statefulset/app-h-mysql` | warn | medium | app-h-prod/statefulset/app-h-mysql: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate mysql-backup', 'local-path volumeClaimTemplate mysql-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-h-prod/statefulset/app-h-qdrant` | warn | medium | app-h-prod/statefulset/app-h-qdrant: eligible nodes ['node-a'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-a'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-h-qdrant-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-neo4j` | warn | medium | app-ac-prod/statefulset/app-ac-neo4j: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-opensearch` | warn | medium | app-ac-prod/statefulset/app-ac-opensearch: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-postgres` | warn | medium | app-ac-prod/statefulset/app-ac-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-redis` | warn | medium | app-ac-prod/statefulset/app-ac-redis: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/deployment/kibana` | warn | medium | logging/deployment/kibana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.logging/statefulset/elasticsearch` | warn | medium | logging/statefulset/elasticsearch: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.app-i-prod/statefulset/app-i-postgres` | warn | medium | app-i-prod/statefulset/app-i-postgres: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate app-i-postgres-data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-grafana` | warn | medium | monitoring/deployment/kube-prometheus-stack-grafana: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-kube-state-metrics` | warn | medium | monitoring/deployment/kube-prometheus-stack-kube-state-metrics: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/deployment/kube-prometheus-stack-operator` | warn | medium | monitoring/deployment/kube-prometheus-stack-operator: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager` | warn | medium | monitoring/statefulset/alertmanager-kube-prometheus-stack-alertmanager: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus` | warn | medium | monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'role': 'observability'}"], unavoidable pin reasons [], replicas 1, serves traffic True |
| `resilience.single-eligible-node.monitoring/statefulset/tempo` | warn | medium | monitoring/statefulset/tempo: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'storage': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate data'], replicas 1, serves traffic True |
| `resilience.single-eligible-node.registry/statefulset/registry` | warn | medium | registry/statefulset/registry: eligible nodes ['node-b'] (of 2 nodes), constraints ["nodeSelector {'kubernetes.io/hostname': 'node-b'}"], unavoidable pin reasons ['local-path volumeClaimTemplate registry-data'], replicas 1, serves traffic True |
| `resilience.single-node-dependency.registry/statefulset/registry` | warn | medium | ['nodeSelector kubernetes.io/hostname=node-b'], replicas 1 |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-backend:backend` | warn | medium | pod app-a-backend-79c97cbbd6-kkc2d: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-gateway:gateway` | warn | medium | pod app-a-gateway-644c97fbc-q7wd8: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.app-a-prod/sts/app-a-postgres:postgres` | warn | medium | pod app-a-postgres-0: 7d CPU p95 0.058 cores / request 0.20 cores = 0.29; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-api-server:app` | warn | medium | pod app-h-api-server-7ccdccd9f8-46gdp: 7d CPU p95 0.013 cores / request 0.10 cores = 0.13 |
| `resources.cpu-request-overprovisioned.app-h-prod/sts/app-h-mysql:mysql` | warn | medium | pod app-h-mysql-0: 7d CPU p95 0.016 cores / request 0.20 cores = 0.08; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-ac-prod/sts/app-ac-opensearch:opensearch` | warn | medium | pod app-ac-opensearch-0: 7d CPU p95 0.048 cores / request 0.20 cores = 0.24; database-like: keep the request |
| `resources.cpu-request-overprovisioned.app-ac-prod/sts/app-ac-postgres:postgres` | warn | medium | pod app-ac-postgres-0: 7d CPU p95 0.015 cores / request 0.10 cores = 0.15; database-like: keep the request |
| `resources.cpu-request-overprovisioned.ingress-nginx/deploy/nginx-ingress-ingress-nginx-controller:controller` | warn | medium | ['pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10', 'pod nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq: 7d CPU p95 0.011 cores / request 0.10 cores = 0.11'] |
| `resources.cpu-request-overprovisioned.istio-system/deploy/istiod:discovery` | warn | medium | pod istiod-6f6d996c58-ggwp2: 7d CPU p95 0.003 cores / request 0.20 cores = 0.02 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-admission-webhooks:keda-admission-webhooks` | warn | medium | pod keda-admission-webhooks-5d67c9bcfb-8fcdl: 7d CPU p95 0.000 cores / request 0.10 cores = 0.00 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | medium | pod keda-operator-metrics-apiserver-7ff5758fd7-gq7g7: 7d CPU p95 0.003 cores / request 0.10 cores = 0.03 |
| `resources.cpu-request-overprovisioned.keda/deploy/keda-operator:keda-operator` | warn | medium | pod keda-operator-85ff5bb446-lwkl6: 7d CPU p95 0.002 cores / request 0.10 cores = 0.02 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/coredns:coredns` | warn | medium | pod coredns-59d4d457d-qjng8: 7d CPU p95 0.010 cores / request 0.10 cores = 0.10 |
| `resources.cpu-request-overprovisioned.kube-system/deploy/metrics-server:metrics-server` | warn | medium | pod metrics-server-7bfffcd44-fkpfm: 7d CPU p95 0.008 cores / request 0.10 cores = 0.08 |
| `resources.cpu-request-overprovisioned.logging/deploy/kibana:kibana` | warn | medium | pod kibana-6bcf6d579b-p2rgv: 7d CPU p95 0.005 cores / request 0.20 cores = 0.03 |
| `resources.cpu-request-overprovisioned.app-k/deploy/app-k:web` | warn | medium | pod app-k-54c94979b5-b65b5: 7d CPU p95 0.001 cores / request 0.10 cores = 0.01 |
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
| `resources.krr-recommendation.app-a-prod/deployment/app-a-frontend:frontend` | warn | medium | memory request under by 174 MB: CPU HPA detected, memory request 128 → 302 MB. KRR severity OK (CPU req UNKNOWN, CPU limit UNKNOWN, memory req OK, memory limit OK). cpu: HPA detected |
| `resources.krr-recommendation.app-a-prod/statefulset/app-a-redis:redis` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-c-prod/deployment/app-c-coturn:coturn` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-d/deployment/app-d:nginx` | warn | medium | memory request under by 84 MB: CPU request 0.01 → 0.01 cores, CPU limit 0.1 → none, memory request 16 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-f-prod/deployment/app-f-vn-worker:worker` | warn | medium | memory request over by 259 MB: CPU request 0.03 → 0.046 cores, CPU limit 0.2 → none, memory request 576 → 317 MB, memory limit 1408 → 317 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.app-f-prod/statefulset/app-f-redis:redis` | warn | medium | memory request under by 68 MB: CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.app-h-prod/deployment/app-h-excel-agent:app` | warn | medium | memory request under by 250 MB: CPU request 0.05 → 0.01 cores, CPU limit 1.0 → none, memory request 256 → 506 MB, memory limit 1024 → 506 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.app-h-prod/statefulset/app-h-mysql:mysql` | warn | medium | CPU request over by 0.176 cores: CPU request 0.2 → 0.024 cores, CPU limit 1.5 → none, memory request 1600 → 1433 MB, memory limit 3200 → 1433 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.app-ac-prod/deployment/app-ac-istio:istio-proxy` | warn | medium | memory request under by 69 MB: CPU request 0.05 → 0.011 cores, CPU limit 1.0 → none, memory request 64 → 133 MB, memory limit 512 → 133 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `resources.krr-recommendation.app-ac-prod/deployment/app-ac-web:web` | warn | medium | memory request under by 90 MB, CPU request under by 0.784 cores: CPU request 0.1 → 0.884 cores, memory request 256 → 346 MB, memory limit 1024 → 346 MB. KRR severity CRITICAL (CPU req CRITICAL, CPU limit GOOD, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.app-ac-prod/statefulset/app-ac-neo4j:neo4j` | warn | medium | memory request under by 108 MB: CPU request 0.1 → 0.075 cores, CPU limit 1.0 → none, memory request 1024 → 1132 MB, memory limit 2048 → 1132 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit CRITICAL) |
| `resources.krr-recommendation.istio-system/deployment/istiod:discovery` | warn | medium | memory request over by 391 MB: CPU HPA detected, memory request 512 → 121 MB, memory limit 1024 → 121 MB. KRR severity CRITICAL (CPU req UNKNOWN, CPU limit UNKNOWN, memory req WARNING, memory limit CRITICAL). cpu: HPA detected |
| `resources.krr-recommendation.logging/daemonset/fluent-bit:fluent-bit` | warn | medium | memory request under by 86 MB: CPU request 0.05 → 0.085 cores, CPU limit 0.1 → none, memory request 50 → 136 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit GOOD) |
| `resources.krr-recommendation.logging/deployment/kibana:kibana` | warn | medium | CPU request over by 0.19 cores: CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 446 MB, memory limit 1024 → 446 MB. KRR severity CRITICAL (CPU req OK, CPU limit WARNING, memory req GOOD, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/deployment/kube-prometheus-stack-grafana:grafana` | warn | medium | memory request over by 258 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.15 → none, memory request 512 → 254 MB, memory limit 768 → 254 MB. KRR severity CRITICAL (CPU req GOOD, CPU limit WARNING, memory req WARNING, memory limit CRITICAL) |
| `resources.krr-recommendation.monitoring/deployment/opentelemetry-collector:opentelemetry-collector` | warn | medium | memory request under by 255 MB: CPU request 0.05 → 0.015 cores, memory request 128 → 383 MB. KRR severity WARNING (CPU req GOOD, CPU limit GOOD, memory req WARNING, memory limit OK) |
| `resources.krr-recommendation.registry/statefulset/registry:registry` | warn | medium | memory request under by 224 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 128 → 352 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req OK, memory limit OK) |
| `resources.krr-recommendation.app-l-prod/deployment/app-l-web:web` | warn | medium | memory request under by 81 MB: CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 209 MB, memory limit 512 → 209 MB. KRR severity WARNING (CPU req GOOD, CPU limit WARNING, memory req GOOD, memory limit WARNING) |
| `scaling.hpa-flapping.app-h-prod/hpa/app-h-admin` | warn | medium | 34 desired changes over 7 days |
| `security.no-default-deny.cluster` | warn | medium | Namespaces with default-deny (ingress, empty podSelector) [], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-ac-prod', 'app-i-prod', 'app-l-prod']. Enforced True |
| `security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn` | warn | medium | ['hostNetwork'], containers allowing root ['coturn'] |
| `security.psa-not-enforced.cluster` | warn | medium | Namespaces with an enforce label ['metallb-system'], prod without one ['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-ac-prod', 'app-i-prod', 'app-l-prod']. Share of containers allowing root 0.71 (67 prod workloads) |
| `security.rbac-wildcard.argocd-application-controller` | warn | medium | ClusterRole argocd-application-controller: * in verbs and resources, bound subjects [('ServiceAccount', 'argocd', 'argocd-application-controller')] |
| `security.sa-token-mounted-without-rbac.cluster` | warn | medium | Workloads with token mounted 94/96, of which 47 prod workloads whose SA has no RoleBinding or ClusterRoleBinding at all: ['app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix' … |
| `storage.prod-db-reclaim-delete.cluster` | warn | medium | DB-like prod PVCs whose PV reclaimPolicy is Delete: ['app-f-prod/app-f-postgres-backup-node-a-pvc', 'app-f-prod/app-f-postgres-vn-backup-node-a-pvc', 'app-h-prod/app-h-mysql-backup-node-a-pvc', 'app-i-prod/app-i-postgres-backup-node-a-pvc'] (4 in total / 28 prod PVCs) |
| `tenancy.burst-tenant-unbounded.app-h-prod` | warn | medium | app-h-prod (prod): 7d CPU median 0.023 cores, p95 0.094 cores, max 0.704 cores = 30.8x the median. No quota, shares nodes with prod True, nodes {'node-b': 6, 'node-a': 4}, CPU limit total 7.3 cores |
| `tenancy.prod-boundary-missing.app-b-prod` | warn | medium | app-b-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-boundary-missing.app-l-prod` | warn | medium | app-l-prod: ResourceQuota True, NetworkPolicies 0 (enforced by the cluster True), PSA enforce None, LimitRange False, RoleBinding subjects 0. Other tenants on the same nodes: True, tenants 13 |
| `tenancy.prod-without-quota.arc-systems` | warn | medium | arc-systems (ci): no ResourceQuota. Pods 3, CPU requests total 1.0 cores, memory requests total 2.0GB, 7d CPU p95 0.339 cores (cluster share 0.133), memory p95 0.78GB, 7d max/median Nonex. Tenants in this cluster 13, shares nodes with prod True |
| `tenancy.shared-node-limit-overcommit.node-b` | warn | medium | Node node-b (pool (no-pool)): tenant kinds ['ci', 'other', 'prod'], namespaces ['app-f-prod', 'app-a-prod', 'argocd', 'monitoring', 'app-h-prod', 'app-ac-prod'] and 18 more. Memory limit total 51.0GB / allocatable 30.7GB = 1.66x, request total 20.8GB, containers without a limit 27 |
| `tenancy.tenant-without-limitrange.arc-systems` | warn | medium | arc-systems (ci): no LimitRange, containers without requests 4 / without a memory limit 4 (pods 3). 7d CPU p95 0.339 cores, memory p95 0.78GB |
| `traffic.coredns-latency.cluster` | warn | medium | 1h DNS request p99 0.1325s, SERVFAIL ratio 0.0 |
| `traffic.ingress-nginx-retired.cluster` | warn | medium | ingress-nginx 1.14.0 (Deployment ingress-nginx/nginx-ingress-ingress-nginx-controller); ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes; admission webhook on |
| `traffic.pod-not-ready.app-a-prod/app-a-sandbox-prepull` | warn | medium | 24h minimum Ready ratio 0.9833 (pod app-a-sandbox-prepull-8xvrq, about 24 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.app-h-prod/app-h-qdrant-0` | warn | medium | 24h minimum Ready ratio 0.9833 (pod app-h-qdrant-0, about 15 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.app-ac-prod/app-ac-mcp` | warn | medium | 24h minimum Ready ratio 0.9851 (pod app-ac-mcp-6687b545b6-x5zm7, about 11 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.kube-system/nvidia-device-plugin` | warn | medium | 24h minimum Ready ratio 0.9833 (pod nvidia-device-plugin-fpfbs, about 24 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.logging/fluent-bit` | warn | medium | 24h minimum Ready ratio 0.9833 (pod fluent-bit-bmdwx, about 24 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.metallb-system/speaker` | warn | medium | 24h minimum Ready ratio 0.9833 (pod speaker-spdvw, about 24 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `traffic.pod-not-ready.monitoring/kube-prometheus-stack-prometheus-node-exporter` | warn | medium | 24h minimum Ready ratio 0.9833 (pod kube-prometheus-stack-prometheus-node-exporter-5wh9f, about 24 min not ready), pods below 0.99 1, Unhealthy events 0 |
| `hygiene.no-ephemeral-storage-requests.cluster` | fail | low | Containers with an ephemeral-storage request 2 of 141 (0.014), without one in prod 71. emptyDirs without sizeLimit 12 (prod: ['app-ac-prod/deployment/app-ac-istio']) |
| `hygiene.no-standard-labels.cluster` | fail | low | Of 125 workloads, share with standard labels 0.22. prod workloads without: ['app-a-prod/deployment/app-a-backend', 'app-a-prod/deployment/app-a-frontend', 'app-a-prod/deployment/app-a-gateway', 'app-a-prod/deployment/app-a-phoenix' … |
| `hygiene.old-replicasets.cluster` | fail | low | Of 382 ReplicaSets, 316 have 0 replicas. Deployment revisionHistoryLimit distribution {'10': 63, '0': 3, '3': 1, '2': 1} |
| `node.os-not-collected.node-a` | fail | low | os.txt missing |
| `node.os-not-collected.node-b` | fail | low | os.txt missing |
| `node.swap-enabled.192.168.90.102:9100` | fail | low | swap 8.0 GiB |
| `platform.k3s-server-url-stale.node-b` | fail | low | host <ip> of --server https://<ip>:6443 is not among current node IPs or names |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend` | fail | low | HPA app-a-prod/app-a-backend: share of 15 days at min 1.00, min 2 max 6, current CPU utilization 3% / target 70%, metrics ['cpu'], last scale 0.6 days ago |
| `scaling.hpa-never-scaled.app-a-prod/deployment/app-a-frontend` | fail | low | HPA app-a-prod/app-a-frontend: share of 15 days at min 1.00, min 2 max 4, current CPU utilization 12% / target 70%, metrics ['cpu'], last scale 0.5 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f` | fail | low | HPA app-f-prod/app-f: share of 15 days at min 1.00, min 2 max 5, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 4.4 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f-admin` | fail | low | HPA app-f-prod/app-f-admin: share of 15 days at min 1.00, min 1 max 3, current CPU utilization 3% / target 60%, metrics ['cpu', 'memory'], last scale 4.4 days ago |
| `scaling.hpa-never-scaled.app-f-prod/deployment/app-f-mx` | fail | low | HPA app-f-prod/app-f-mx: share of 15 days at min 1.00, min 1 max 4, current CPU utilization 4% / target 60%, metrics ['cpu', 'memory'], last scale 4.4 days ago |
| `scaling.hpa-never-scaled.app-h-prod/deployment/app-h-app-p` | fail | low | HPA app-h-prod/app-h-app-p: share of 15 days at min 0.99, min 1 max 4, current CPU utilization 3% / target 70%, metrics ['cpu', 'memory'], last scale 0.2 days ago |
| `argocd.notifications-not-configured.cluster` | warn | low | service.* in argocd-notifications-cm False (triggers 0), prod apps 11, and no Argo CD metrics flow to Alertmanager either (no ServiceMonitor) |
| `argocd.prod-tracks-moving-ref.cluster` | warn | low | prod apps 11, apps whose targetRevision is a branch or HEAD 11 ['argocd/application/app-a-prod', 'argocd/application/app-b-prod', 'argocd/application/app-c', 'argocd/application/app-f-kr', 'argocd/application/app-f-mx', 'argocd/application/app-f-shared', 'argocd/application/app-f-vn' … |
| `certmanager.controller-errors.cluster` | warn | low | sync calls since controller start 1757 / errors 390, ACME requests 25 by status {'200': 24, '201': 1} (4xx/5xx 0, ratio 0.0), Ready False metric 0 |
| `certmanager.version-old.cluster` | warn | low | cert-manager 1.14.4 (components {'controller': '1/1', 'cainjector': '1/1', 'webhook': '1/1'}), webhooks with Fail 2 / webhook replicas 1 |
| `coredns.aaaa-noise.cluster` | warn | low | AAAA share of request types 0.485, cluster IPv6 False, queries per second 31.75. The glibc resolver always asks A and AAAA as a pair |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-applicationset-controller:argocd-applicationset-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:copyutil` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-dex-server:dex` | warn | low | image ghcr.io/dexidp/dex:v2.43.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-notifications-controller:argocd-notifications-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-redis:redis` | warn | low | image public.ecr.aws/docker/library/redis:8.2.2-alpine (tag tag, imagePullPolicy Always, registry public.ecr.aws) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-repo-server:argocd-repo-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/deployment/argocd-server:argocd-server` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.argocd/statefulset/argocd-application-controller:argocd-application-controller` | warn | low | image quay.io/argoproj/argocd:v3.2.0 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.app-f-prod/deployment/app-f-vn:db-migrate` | warn | low | image registry.lab-a.example/app-f-vietnam:prod-2ff89792201f2e1d05e20b51243945ef85af35e4 (tag tag, imagePullPolicy Always, registry registry.lab-a.example) |
| `hygiene.always-pull-with-tag.istio-system/deployment/kiali:kiali` | warn | low | image quay.io/kiali/kiali:v2.34.1 (tag tag, imagePullPolicy Always, registry quay.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-admission-webhooks:keda-admission-webhooks` | warn | low | image ghcr.io/kedacore/keda-admission-webhooks:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator-metrics-apiserver:keda-operator-metrics-apiserver` | warn | low | image ghcr.io/kedacore/keda-metrics-apiserver:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.always-pull-with-tag.keda/deployment/keda-operator:keda-operator` | warn | low | image ghcr.io/kedacore/keda:2.19.0 (tag tag, imagePullPolicy Always, registry ghcr.io) |
| `hygiene.failed-pods-lingering.cluster` | warn | low | Failed pods 3 (prod 3), reasons {'Failed': 1, 'UnexpectedAdmissionError': 2}, namespaces {'app-a-prod': 1, 'app-h-prod': 1, 'app-ac-prod': 1}, oldest 3347.1h. Example: ['app-a-prod/app-a-experiment', 'app-h-prod/app-h-embed-768cf69449-99swc' … |
| `hygiene.helm-release-stale.cert-manager/cert-manager` | warn | low | Release cert-manager/cert-manager: chart cert-manager-v1.14.4 (app v1.14.4), last changed 369 days ago |
| `hygiene.helm-release-stale.ingress-nginx/nginx-ingress` | warn | low | Release ingress-nginx/nginx-ingress: chart ingress-nginx-4.14.0 (app 1.14.0), last changed 369 days ago |
| `hygiene.orphan-configmaps.cluster` | warn | low | Of 154 ConfigMaps, 29 unreferenced candidates: [('app-a-prod', 'app-a-sandbox-codex-config'), ('app-a-prod', 'istio-ca-crl'), ('arc-systems', 'istio-ca-crl'), ('argocd', 'istio-ca-crl'), ('cert-manager', 'istio-ca-crl'), ('app-b-prod', 'istio-ca-crl'), ('app-c-prod' … |
| `hygiene.orphan-secrets.cluster` | warn | low | Of 147 Secrets (metric kube_secret_info), 10 unreferenced candidates: [('argocd', 'ghcr-auth-secret', 'kubernetes.io/dockerconfigjson'), ('argocd', 'ghcr-pull-secret', 'kubernetes.io/dockerconfigjson'), ('default', 'app-f-prod-tls', 'kubernetes.io/tls'), ('default', 'app-ah-auth-secret', 'Opaque') … |
| `hygiene.unused-crds.cluster` | warn | low | 57 of 87 CRDs have zero objects (by group {'generators.external-secrets.io': 17, 'monitoring.coreos.com': 5, 'security.istio.io': 2, 'gateway.networking.k8s.io': 5, 'metallb.io': 5, 'acme.cert-manager.io': 1, 'eventing.keda.sh': 2, 'external-secrets.io': 4, 'keda.sh': 4, 'networking.istio.io': 7 … |
| `keda.unused.cluster` | warn | low | KEDA v2.19.0 operator 1/1, metrics-apiserver 1/1, webhooks 1/1 — ScaledObject 0, ScaledJob 0 |
| `kubeproxy.node-cmd-unavailable.cluster` | warn | low | 2 of 2 nodes could not read /proxyMode or /healthz. Mode from the config file: None |
| `logs.signatures.cert-manager.orphan-tls-secret` | warn | low | 16 occurrences (2026-11-14T01:14:00Z ~ 2026-11-14T01:14:00Z), thresholds warn 1/fail 1000. Files: ['logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log']. Samples: ['[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701159812Z E1114 … |
| `logs.signatures.metallb.speaker-peer-unreachable` | warn | low | 545 occurrences (2026-11-14T12:24:07Z ~ 2026-11-14T16:03:17Z), thresholds warn 60/fail 2000. Files: ['logs/pods/metallb/metallb-system_speaker.log']. Samples: ['[pod/speaker-lqmcg/speaker] 2026-11-14T12:43:57.490323576Z {"caller":"speakerlist.go:259","error":"1 error occurred:\\n\\t* Failed to join … |
| `observability.alert-metric-without-dashboard.grafana` | warn | low | 25 dashboards (170 panel metrics) — 138 of 172 alert-rule metrics have no panel: ['aggregator_unavailable_apiservice', 'aggregator_unavailable_apiservice_total', 'alertmanager_cluster_members', 'alertmanager_config_hash', 'alertmanager_config_last_reload_successful' … |
| `observability.alerts-never-fired.cluster` | warn | low | 118 of 147 rules did not fire in 15 days (['AppQBackendDown', 'AppQClusterCPU50', 'AppQClusterCPU80', 'AppQClusterMem80', 'AppQGatewayDown', 'AppQGatewayErrorRateHigh', 'AppQGatewayHighCost', 'AppQGatewayUpstreamRejecting' … |
| `observability.saturation-signal-missing.cluster` | warn | low | 30 of 31 ingress backends have no saturation metric (e.g. [('app-a-prod', 'app-a-backend'), ('app-a-prod', 'app-a-frontend'), ('app-a-prod', 'app-a-phoenix'), ('app-a-prod', 'app-a-umami'), ('argocd', 'argocd-server-ingress'), ('app-b-prod' … |
| `observability.unclassified-errors.cluster` | warn | low | 593 unclassified error lines (22307 lines scanned, 32 files). Top: [('cert-manager \| "re-queuing item due to error processing" err="ACME client for issuer not initialised', 390), ('ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:43 +<n>] "GET …', 5), ('ingress-nginx \| <ip> - - [14/Nov/<n>:15:29:42 +<n>] … |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-a' … |
| `resilience.exec-probe.app-a-prod/statefulset/app-a-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'redis-cli ping', 'port': None … |
| `resilience.exec-probe.app-c-prod/statefulset/app-c-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U damta', 'port' … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-mx:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres-vn:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-f-prod/statefulset/app-f-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'redis-cli ping', 'port': None … |
| `resilience.exec-probe.app-g-api/statefulset/app-g-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-h-prod/statefulset/app-h-mysql:mysql` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'mysqladmin ping -h localhost' … |
| `resilience.exec-probe.app-ac-prod/statefulset/app-ac-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-ac' … |
| `resilience.exec-probe.app-ac-prod/statefulset/app-ac-redis:redis` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'sh -c redis-cli ping \| grep -q … |
| `resilience.exec-probe.logging/statefulset/elasticsearch:elasticsearch` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'sh -c curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health?local=true \| … |
| `resilience.exec-probe.app-i-prod/statefulset/app-i-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': '/bin/sh -c pg_isready -U … |
| `resilience.exec-probe.app-k/deployment/app-k-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U platform_admin -d … |
| `resilience.exec-probe.app-l-prod/deployment/app-l-postgres:postgres` | warn | low | ['liveness exec (forks a process)', 'readiness exec (forks a process every period, node load)', 'liveness exec timeout 1s (false failures when the node is busy)', 'readiness exec timeout 1s (false failures when the node is busy)']. liveness {'type': 'exec', 'path': 'pg_isready -U app-l -d … |
| `resilience.finished-jobs-accumulating.cluster` | warn | low | 60 Jobs (1 failed), 57 finished Jobs without ttl, 35 Succeeded pods, 3 Failed pods |
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
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-q-client:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-embed:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 60}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-excel-agent:app` | warn | low | ['liveness and readiness share the same path (/health) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/health', 'port': 8080, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/health' … |
| `resilience.liveness-dependency-path.app-h-prod/deployment/app-h-app-p:app` | warn | low | ['liveness and readiness share the same path (/) — a dependency outage becomes a restart loop']. liveness {'type': 'httpGet', 'path': '/', 'port': 3000, 'timeout_s': 1, 'period_s': 20, 'failure_threshold': 3, 'initial_delay_s': 30}, readiness {'type': 'httpGet', 'path': '/', 'port': 3000 … |
| `resilience.liveness-dependency-path.app-ac-prod/statefulset/app-ac-opensearch:opensearch` | warn | low | ['liveness and readiness share the same path (/_cluster/health) — a dependency outage becomes a restart loop', 'DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)']. liveness {'type': 'httpGet', 'path': '/_cluster/health', 'port': 9200, 'timeout_s': 1 … |
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
| `resilience.no-prestop.app-h-prod/app-h-app-q-client` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-embed` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-excel-agent` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-h-prod/app-h-app-p` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-ai` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-istio` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-mcp` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-projector` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-ac-prod/app-ac-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-i-prod/app-i` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-api` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-postgres` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resilience.no-prestop.app-l-prod/app-l-web` | warn | low | no preStop, terminationGracePeriodSeconds 30 |
| `resources.memory-request-overprovisioned.app-c-prod/sts/app-c-postgres:postgres` | warn | low | pod app-c-postgres-0: 7d memory working set p95 54 MB / request 256 MB = 0.21; database-like: keep the request |
| `resources.memory-request-overprovisioned.app-ac-prod/sts/app-ac-postgres:postgres` | warn | low | pod app-ac-postgres-0: 7d memory working set p95 74 MB / request 256 MB = 0.29; database-like: keep the request |
| `resources.memory-request-overprovisioned.istio-system/deploy/istiod:discovery` | warn | low | pod istiod-6f6d996c58-ggwp2: 7d memory working set p95 91 MB / request 512 MB = 0.18 |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: metrics ['cpu'], current CPU 3% / target 70% |
| `scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: metrics ['cpu'], current CPU 12% / target 70% |
| `scaling.hpa-never-scaled.istio-system/deployment/istiod` | warn | low | HPA istio-system/istiod: share of 15 days at min 1.00, min 1 max 5, current CPU utilization 1% / target 80%, metrics ['cpu'], last scale None days ago |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend` | warn | low | HPA app-a-prod/app-a-backend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 1.0 desired changes over 7 days |
| `scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-frontend` | warn | low | HPA app-a-prod/app-a-frontend: no behavior (defaults: scaleDown 300s, scaleUp immediate), 4.0 desired changes over 7 days |
| `storage.local-path-node-pinned.cluster` | warn | low | 38 local-path PVs, by node {'node-a': 14, 'node-b': 24}, node disk used {'node-a': None, 'node-b': None}MB. top: [('app-g-api', 'app-g-postgres-backup-node-a-pvc', 'node-a', None, "['app-g-api/app-g-postgres-backup']"), ('app-k', 'app-k-postgres-data', 'node-a', None … |
| `storage.local-path-prod-delete-reclaim.cluster` | warn | low | 4 of 28 prod PVs are Delete ['app-f-prod/app-f-postgres-backup-node-a-pvc', 'app-i-prod/app-i-postgres-backup-node-a-pvc', 'app-h-prod/app-h-mysql-backup-node-a-pvc', 'app-f-prod/app-f-postgres-vn-backup-node-a-pvc'], StorageClass reclaim {'local-path': 'Delete', 'local-path-node-b': 'Delete'}, default class … |
| `tenancy.ci-shares-prod-nodes.node-a` | warn | low | Node node-a (pool (no-pool)): prod pods 15 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-h-prod', 'app-ac-prod', 'app-l-prod']) together with CI pods 2 (['lab-a-runner-g55w4-288vf', 'lab-a-runner-g55w4-gnkcc']). Heavy runners True, minutes above 90% node CPU in 7d 65.0 … |
| `tenancy.ci-shares-prod-nodes.node-b` | warn | low | Node node-b (pool (no-pool)): prod pods 39 (['app-a-prod', 'app-b-prod', 'app-c-prod', 'app-f-prod', 'app-h-prod', 'app-ac-prod', 'app-i-prod', 'app-l-prod']) together with CI pods 1 (['arc-actions-runner-controller-6cd54f9566-vxmrc']). Heavy runners True, minutes above 90% node … |
| `tenancy.quota-without-limitrange.app-a-prod/app-a-prod-quota` | warn | low | app-a-prod/app-a-prod-quota: requests entries in hard ['requests.memory'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-b-prod/app-b-prod-quota` | warn | low | app-b-prod/app-b-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `tenancy.quota-without-limitrange.app-l-prod/app-l-prod-quota` | warn | low | app-l-prod/app-l-prod-quota: requests entries in hard ['requests.cpu', 'requests.memory', 'requests.storage'], LimitRange False (default request False), containers without requests right now 0 |
| `traffic.flannel-node-data-missing.cluster` | warn | low | nodes 2, nodes with the flannel section read [], nodes not read [], node-exporter metrics True |
| `traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller` | warn | low | Service ingress-nginx/nginx-ingress-ingress-nginx-controller: externalTrafficPolicy Local, ports [80, 443], addresses ['<ip>'] |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-gateway` | warn | info | replicas 2, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-phoenix` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-a-prod/app-a-umami` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-backend` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-b-prod/app-b-frontend` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-signaling` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-c-prod/app-c-web` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-h-prod/app-h-embed` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-h-prod/app-h-excel-agent` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-ai` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-api` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-istio` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-mcp` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-projector` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-ac-prod/app-ac-web` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-l-prod/app-l-api` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |
| `scaling.no-hpa-serving-prod.app-l-prod/app-l-web` | warn | info | replicas 1, has container ports and a Service, no HPA or ScaledObject |

The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.

<details><summary><code>logs.signatures.prometheus.wal-corrupt</code></summary>

```json
{
 "count": 2,
 "first": "2026-11-14T01:14:32Z",
 "last": "2026-11-14T01:14:32Z",
 "warn_at": 1,
 "fail_at": 10,
 "files": {
  "logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log": 2
 },
 "samples": [
  "[pod/prometheus-kube-prometheus-stack-prometheus-0/prometheus] 2026-11-14T01:14:32.965707214Z time=2026-11-14T01:14:32.965Z level=WARN source=db.go:1019 msg=\"Encountered WAL read error, attempting repair\" component=tsdb err=\"read records: c",
  "[pod/prometheus-kube-prometheus-stack-prometheus-0/prometheus] 2026-11-14T01:14:32.965745795Z time=2026-11-14T01:14:32.965Z level=WARN source=wlog.go:413 msg=\"Starting corruption repair\" component=tsdb segment=8483 offset=19763238"
 ]
}
```

</details>
<details><summary><code>argocd.prune-manages-namespace-or-crd.cluster</code></summary>

```json
{
 "applications_prod": 11,
 "prune_with_namespace_or_crd": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/app-d",
  "argocd/application/app-g-api",
  "argocd/application/app-ac-prod",
  "argocd/application/istio",
  "argocd/application/app-k",
  "argocd/application/app-n",
  "argocd/application/app-l-prod"
 ]
}
```

</details>
<details><summary><code>observability.alertmanager-notification-failed.slack</code></summary>

```json
{
 "labels": {
  "integration": "slack"
 },
 "values": {
  "alertmanager_notifications_failed_1d": 8.00661787085114,
  "am_notifications_1d": 60.0364320477694
 }
}
```

</details>
<details><summary><code>prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "compactions_failed_7d": 0,
 "corruption_count": 1,
 "oldest_sample_days": 31.2,
 "present": true,
 "pvc_size": null,
 "pvc_used_ratio": null,
 "retention_size": "0B",
 "retention_time": "30d",
 "storage": "emptyDir",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus",
 "tsdb_bytes": 23906601854.0,
 "wal_corruptions": 1
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-a-prod/ds/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-sandbox-prepull-8xvrq",
  "container": "hold-python"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.3333333333333333
 }
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
  "cpu_throttle_ratio_24h": 0.26134703758653755,
  "cpu_throttle_ratio_5m": 0.1596638655462185
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-h-prod/deploy/app-h-admin:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-admin-6789875894-2qz6d",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.4642857142857143,
   "cpu_throttle_ratio_5m": 0.4642857142857143
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-admin-6789875894-pwhh4",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.04735258034680939,
   "cpu_throttle_ratio_5m": 0.5233644859813085
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.app-h-prod/deploy/app-h-api-server:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-7ccdccd9f8-7wvxl",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.6114285714285714
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-7ccdccd9f8-r6xdr",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.5463414634146341
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-7ccdccd9f8-nj4kr",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.26475077813949
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-7ccdccd9f8-w5lp7",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.6254716981132076
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-api-server-7ccdccd9f8-vtltg",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.6302032913843175
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.app-h-prod/deploy/app-h-app-q-client:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-q-client-754b8c5b59-nszv9",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.30303030303030304
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-q-client-754b8c5b59-g8x5q",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.265625
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.logging/ds/fluent-bit:fluent-bit</code></summary>

```json
[
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-bmdwx",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.30837542297459847,
   "cpu_throttle_ratio_5m": 0.2740576496674058
  }
 },
 {
  "labels": {
   "namespace": "logging",
   "pod": "fluent-bit-wzbvh",
   "container": "fluent-bit"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.41794392601511804,
   "cpu_throttle_ratio_5m": 0.3153225806451613
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.logging/pod/fluent-bit-qcjbv:fluent-bit</code></summary>

```json
{
 "labels": {
  "namespace": "logging",
  "pod": "fluent-bit-qcjbv",
  "container": "fluent-bit"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.2812247533100726
 }
}
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
  "cpu_throttle_ratio_24h": 0.37376291443089865,
  "cpu_throttle_ratio_5m": 0.3409198672356567
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
  "cpu_throttle_ratio_24h": 0.4452591898756476,
  "cpu_throttle_ratio_5m": 0.6100104275286757
 }
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
 "value": 0.9506980895996093
}
```

</details>
<details><summary><code>resources.oomkilled-repeated.monitoring/sts/tempo:tempo</code></summary>

```json
{
 "cadvisor_oom_events_7d": 0,
 "kernel_any_node_read": false,
 "kernel_kills_24h": 0,
 "kernel_log_read": false,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_total": 1,
 "pods_now": [
  {
   "pod": "tempo-0",
   "created": "2026-11-12T16:12:17Z",
   "restarts": 1
  }
 ],
 "pods_oomkilled": 1,
 "pods_replaced": 1,
 "restarts_of_those_pods": 163,
 "target": "monitoring/sts/tempo:tempo"
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
<details><summary><code>node.disk-usage.192.168.90.101:9100:/</code></summary>

```json
{
 "labels": {
  "instance": "<ip>:9100",
  "mountpoint": "/"
 },
 "value": 0.7528491757570507
}
```

</details>
<details><summary><code>prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus</code></summary>

```json
{
 "head_series": 174075,
 "memory_limit": "1536Mi",
 "monitoring_oomkilled": [],
 "monitoring_restarts_7d": {
  "kube-prometheus-stack-prometheus-node-exporter-5wh9f": 2,
  "opentelemetry-collector-6dcb785647-plkfv": 1,
  "tempo-0": 163
 },
 "oomkilled_at": null,
 "oomkilled_last": false,
 "present": true,
 "restarts": 6,
 "rss_vs_limit": 0.752,
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-a-prod/app-a-postgres-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-a-postgres-backup-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "15 3 * * *",
 "source_db": [
  {
   "workload": "app-a-prod/statefulset/app-a-postgres",
   "pvc": "data-app-a-postgres-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-a-prod/app-a-postgres-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-f-prod/app-f-postgres-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-f-postgres-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "30 3 * * *",
 "source_db": [
  {
   "workload": "app-f-prod/statefulset/app-f-postgres",
   "pvc": "app-f-postgres-data-app-f-postgres-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-f-prod/app-f-postgres-mx-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-f-postgres-mx-backup-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "30 3 * * *",
 "source_db": [
  {
   "workload": "app-f-prod/statefulset/app-f-postgres-mx",
   "pvc": "app-f-postgres-mx-data-app-f-postgres-mx-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-mx-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-f-prod/app-f-postgres-vn-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-f-postgres-vn-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "30 3 * * *",
 "source_db": [
  {
   "workload": "app-f-prod/statefulset/app-f-postgres-vn",
   "pvc": "app-f-postgres-vn-data-app-f-postgres-vn-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-f-prod/app-f-postgres-vn-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-g-api/app-g-postgres-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-g-postgres-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "50 3 * * *",
 "source_db": [
  {
   "workload": "app-g-api/statefulset/app-g-postgres",
   "pvc": "app-g-postgres-data-app-g-postgres-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-g-api/app-g-postgres-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-h-prod/app-h-mysql-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-h-mysql-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "50 2 * * *",
 "source_db": [
  {
   "workload": "app-h-prod/statefulset/app-h-mysql",
   "pvc": "mysql-backup-app-h-mysql-0",
   "node": "node-b"
  },
  {
   "workload": "app-h-prod/statefulset/app-h-mysql",
   "pvc": "mysql-data-app-h-mysql-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-h-prod/app-h-mysql-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.kube-system/etcd-snapshot-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "etcd-snapshot-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "30 0,12 * * *",
 "source_db": [],
 "suspend": false,
 "target": "kube-system/etcd-snapshot-backup"
}
```

</details>
<details><summary><code>resilience.backup-same-node.app-i-prod/app-i-postgres-backup</code></summary>

```json
{
 "dest_nodes": [
  "node-a"
 ],
 "dest_pvcs": [
  "app-i-postgres-backup-node-a-pvc"
 ],
 "host_paths": [],
 "local_only": true,
 "offsite_hint": false,
 "same_node_as_source": false,
 "schedule": "0 3 * * *",
 "source_db": [
  {
   "workload": "app-i-prod/statefulset/app-i-postgres",
   "pvc": "app-i-postgres-data-app-i-postgres-0",
   "node": "node-b"
  }
 ],
 "suspend": false,
 "target": "app-i-prod/app-i-postgres-backup"
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-a-prod/deploy/app-a-frontend:frontend</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-frontend-799cb7b64c-pxbj6",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.1516488419961712
  }
 },
 {
  "labels": {
   "namespace": "app-a-prod",
   "pod": "app-a-frontend-799cb7b64c-zq69f",
   "container": "frontend"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.20391177694548482
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-throttling.app-a-prod/pod/app-a-backend-migrate-8shv7:migrate</code></summary>

```json
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-backend-migrate-8shv7",
  "container": "migrate"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.16363636363636364
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-8bxwr:runner</code></summary>

```json
{
 "labels": {
  "namespace": "arc-systems",
  "pod": "lab-a-runner-g55w4-8bxwr",
  "container": "runner"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.1392988929889299
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-c7j6m:runner</code></summary>

```json
{
 "labels": {
  "namespace": "arc-systems",
  "pod": "lab-a-runner-g55w4-c7j6m",
  "container": "runner"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.12394705174488568
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.arc-systems/pod/lab-a-runner-g55w4-fzj9v:runner</code></summary>

```json
{
 "labels": {
  "namespace": "arc-systems",
  "pod": "lab-a-runner-g55w4-fzj9v",
  "container": "runner"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.11029695333590434
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-f-prod/sts/app-f-postgres-mx:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-f-prod",
  "pod": "app-f-postgres-mx-0",
  "container": "postgres"
 },
 "values": {
  "cpu_throttle_ratio_24h": 0.12379876622718865,
  "cpu_throttle_ratio_5m": 0.15337423312883436
 }
}
```

</details>
<details><summary><code>resources.cpu-throttling.app-h-prod/deploy/app-h-app-p:app</code></summary>

```json
[
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-p-7c8bbfbcc6-wj8sd",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.2116788321167883
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-p-7c8bbfbcc6-wf242",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.16774193548387095
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-p-7c8bbfbcc6-fzmzl",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.18604651162790697
  }
 },
 {
  "labels": {
   "namespace": "app-h-prod",
   "pod": "app-h-app-p-7c8bbfbcc6-wx5qm",
   "container": "app"
  },
  "values": {
   "cpu_throttle_ratio_24h": 0.208955223880597
  }
 }
]
```

</details>
<details><summary><code>resources.oomkilled-repeated.app-ac-prod/deploy/app-ac-ai:ai</code></summary>

```json
{
 "cadvisor_oom_events_7d": 0,
 "kernel_any_node_read": false,
 "kernel_kills_24h": 0,
 "kernel_log_read": false,
 "kernel_nodes_old_script": 0,
 "kernel_nodes_total": 1,
 "pods_now": [
  {
   "pod": "app-ac-ai-74b95b458b-qzrtl",
   "created": "2026-11-14T04:23:03Z",
   "restarts": 0
  }
 ],
 "pods_oomkilled": 1,
 "pods_replaced": 1,
 "restarts_of_those_pods": 1,
 "target": "app-ac-prod/deploy/app-ac-ai:ai"
}
```

</details>
<details><summary><code>security.plaintext-configmap-secret.default/configmap/app-ai-backend-config</code></summary>

```json
{
 "keys": [
  "JWT_RELAY_SECRET",
  "JWT_SECRET",
  "TWITTER_CLIENT_SECRET",
  "TWITTER_CLIENT_SECRET_RELAY"
 ],
 "mounted_by": [],
 "prod": false,
 "target": "default/configmap/app-ai-backend-config"
}
```

</details>
<details><summary><code>storage.local-path-fs-near-full.cluster</code></summary>

```json
{
 "by_node": {
  "node-a": 14,
  "node-b": 24
 },
 "fs": {
  "node-a": {
   "avail_ratio": 0.247,
   "size_gib": 106.7,
   "growth_gib_per_day": 0.91,
   "avail_gib": 26.4,
   "days_to_full": 29,
   "volumes_gib": 0.0
  },
  "node-b": {
   "avail_ratio": 0.414,
   "size_gib": 454.9,
   "growth_gib_per_day": 2.31,
   "avail_gib": 188.3,
   "days_to_full": 82,
   "volumes_gib": 0.0
  }
 },
 "fs_min_avail_ratio": 0.247,
 "fs_min_days_to_full": 29,
 "metrics_available": true,
 "over_capacity_count": 0,
 "pv_count": 38
}
```

</details>
<details><summary><code>traffic.metallb-config-stale.cluster</code></summary>

```json
{
 "arp_requests_total": 0,
 "arp_responses_total": 0,
 "bgp_sessions": 0,
 "bgp_sessions_up": 0,
 "config_errors": [],
 "config_not_reported": [
  "speaker-spdvw"
 ],
 "config_read": true,
 "config_source": "metrics",
 "config_stale_pods": [],
 "gratuitous_total": 24,
 "update_errors_read": true,
 "update_errors_total": 0
}
```

</details>
<details><summary><code>traffic.metallb-speaker-not-ready.cluster</code></summary>

```json
{
 "controller_ready": 1,
 "controller_replicas": 1,
 "lb_services": 1,
 "mode": "layer2",
 "nodes_total": 2,
 "speaker_all_nodes": true,
 "speaker_desired": 2,
 "speaker_eligible": 2,
 "speaker_ready": 2,
 "speakers_read": 1,
 "speakers_unreadable": [
  {
   "pod": "speaker-spdvw",
   "node": "node-a",
   "error": "Unable to connect to the server: context deadline exceeded"
  }
 ],
 "version": "0.14.5"
}
```

</details>
<details><summary><code>controlplane.apiserver-latency.PATCH</code></summary>

```json
{
 "labels": {
  "verb": "PATCH"
 },
 "value": 1.7199999999999798
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
 "restarts_total": 2,
 "single_replica": true,
 "spread_declared": true
}
```

</details>
<details><summary><code>coredns.nxdomain-ratio-high.cluster</code></summary>

```json
{
 "autopath": false,
 "cache_hit_ratio": 0.8453,
 "forward_nxdomain_ratio": 0.849,
 "metrics_available": true,
 "nxdomain_ratio": 0.699,
 "pods_default_ndots": 145,
 "qps_total": 31.75,
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
 "externalsecrets": 44,
 "externalsecrets_prod": 36,
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
<details><summary><code>hygiene.polaris-reliability-danger.app-a-prod/daemonset/app-a-sandbox-prepull</code></summary>

```json
{
 "non_security_danger": [
  "tagNotSpecified"
 ],
 "non_security_warning": [
  "livenessProbeMissing",
  "metadataAndInstanceMismatched",
  "priorityClassNotSet",
  "readinessProbeMissing",
  "topologySpreadConstraint"
 ],
 "prod": true,
 "security_danger": [
  "privilegeEscalationAllowed",
  "runAsRootAllowed"
 ],
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull"
}
```

</details>
<details><summary><code>observability.alerts-always-firing.CPUThrottlingHigh</code></summary>

```json
{
 "alertname": "CPUThrottlingHigh",
 "samples_7d": 56248.0
}
```

</details>
<details><summary><code>observability.alerts-always-firing.KubeJobFailed</code></summary>

```json
{
 "alertname": "KubeJobFailed",
 "samples_7d": 31855.0
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
 "ingresses": 31,
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
   "namespace": "app-ac-prod",
   "ingress": "app-ac",
   "class": "nginx",
   "hosts": [
    "app-ac.lab-j.example"
   ],
   "services": [
    "app-ac-istio"
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
   "namespace": "app-ac-prod",
   "ingress": "app-ac-machine",
   "class": "nginx",
   "hosts": [
    "app-ac-api.lab-j.example",
    "app-ac-mcp.lab-j.example"
   ],
   "services": [
    "app-ac-istio"
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
 "namespaces_with_app_http_metrics": [
  "istio-system"
 ]
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
<details><summary><code>operators.webhook-self-lock.istiod-default-validator:validation.istio.io</code></summary>

```json
{
 "config": "istiod-default-validator",
 "kind": "Validating",
 "namespace_selector": null,
 "resources": [
  "*"
 ],
 "service": "istio-system/istiod",
 "webhook": "validation.istio.io"
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
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
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
  "path": "pg_isready -U damta",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U damta",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
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
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
<details><summary><code>resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-neo4j:neo4j</code></summary>

```json
{
 "container": "neo4j",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "tcpSocket",
  "path": null,
  "port": 7687,
  "timeout_s": 1,
  "period_s": 20,
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
  "initial_delay_s": 30
 },
 "startup": null,
 "workload": "app-ac-prod/statefulset/app-ac-neo4j"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-opensearch:opensearch</code></summary>

```json
{
 "container": "opensearch",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "httpGet",
  "path": "/_cluster/health",
  "port": 9200,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 90
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/_cluster/health",
  "port": 9200,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "startup": null,
 "workload": "app-ac-prod/statefulset/app-ac-opensearch"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-postgres:postgres</code></summary>

```json
{
 "container": "postgres",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "pg_isready -U app-ac",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-ac",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "app-ac-prod/statefulset/app-ac-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.app-ac-prod/statefulset/app-ac-redis:redis</code></summary>

```json
{
 "container": "redis",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "exec",
  "path": "sh -c redis-cli ping | grep -q PONG",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "sh -c redis-cli ping | grep -q PONG",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "startup": null,
 "workload": "app-ac-prod/statefulset/app-ac-redis"
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
  "path": "pg_isready -U app-l -d app-l",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": true,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-l -d app-l",
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
   "namespace": "app-ac-prod",
   "pod": "app-ac-neo4j-0",
   "node": "node-b",
   "cpu": 0.1,
   "memory_gb": 1.0,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-ac-prod",
   "pod": "app-ac-opensearch-0",
   "node": "node-b",
   "cpu": 0.2,
   "memory_gb": 1.5,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-ac-prod",
   "pod": "app-ac-postgres-0",
   "node": "node-b",
   "cpu": 0.1,
   "memory_gb": 0.25,
   "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node",
   "eligible_nodes": []
  },
  {
   "namespace": "app-ac-prod",
   "pod": "app-ac-redis-0",
   "node": "node-b",
   "cpu": 0.02,
   "memory_gb": 0.06,
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
   "pod": "kibana-6bcf6d579b-p2rgv",
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
   "namespace": "monitoring",
   "pod": "tempo-0",
   "node": "node-b",
   "cpu": 0.05,
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
 "cpu_ok": false,
 "karpenter": false,
 "largest_node": "node-b",
 "largest_node_cpu": 12.0,
 "largest_node_memory_gb": 30.7,
 "memory_ok": true,
 "ok": false,
 "pods_on_largest_node": 80,
 "pools_short": [
  {
   "eligible_nodes": [],
   "pods": 24,
   "needed_cpu": 1.96,
   "free_cpu": 0,
   "needed_memory_gb": 11.23,
   "free_memory_gb": 0.0
  }
 ],
 "prod_pods_on_largest_node": 39,
 "requests_cpu_total": 7.69,
 "requests_memory_gb_total": 31.1,
 "tight": false
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "app-a-prod/deployment/app-a-backend",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-a-prod/deployment/app-a-gateway</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
 "topology_spread": [],
 "workload": "app-a-prod/deployment/app-a-gateway",
 "zones": {
  "null": 2
 }
}
```

</details>
<details><summary><code>resilience.replicas-same-node.app-f-prod/deployment/app-f</code></summary>

```json
{
 "all_same_node": true,
 "anti_affinity": null,
 "eligible_nodes": 2,
 "nodes": {
  "node-b": 2
 },
 "prod": true,
 "replicas": 2,
 "running": 2,
 "single_eligible_node": false,
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
<details><summary><code>resilience.shell-pid1-no-prestop.app-ac-prod/statefulset/app-ac-redis</code></summary>

```json
{
 "grace_s": 30,
 "prestop": false,
 "prod": true,
 "shell_pid1_containers": [
  "redis"
 ],
 "workload": "app-ac-prod/statefulset/app-ac-redis"
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
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-ai</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-api</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-istio</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-istio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-mcp</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-mcp",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-projector</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-projector",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.single-replica-in-prod.app-ac-prod/app-ac-web</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-web",
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
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-backend:backend</code></summary>

```json
{
 "cpu_limit_sev": "UNKNOWN",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 890 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "app-a-backend",
 "severity": "CRITICAL",
 "summary": "CPU HPA detected, memory request 256 → 1146 MB",
 "target": "app-a-prod/deployment/app-a-backend:backend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-umami:umami</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 369 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "app-a-umami",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.067 cores, CPU limit 0.3 → none, memory request 128 → 497 MB",
 "target": "app-a-prod/deployment/app-a-umami:umami"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/statefulset/app-a-postgres:postgres</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 1546 MB, CPU request over by 0.138 cores",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "CRITICAL",
 "name": "app-a-postgres",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.062 cores, CPU limit 1.0 → none, memory request 512 → 2058 MB",
 "target": "app-a-prod/statefulset/app-a-postgres:postgres"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-g-api/statefulset/app-g-minio:minio</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 454 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "WARNING",
 "name": "app-g-minio",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.012 cores, CPU limit 0.3 → none, memory request 128 → 582 MB",
 "target": "app-g-api/statefulset/app-g-minio:minio"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-h-prod/deployment/app-h-embed:app</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "CPU request over by 0.488 cores, memory request over by 1168 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-h-embed",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 0.012 cores, CPU limit 2.0 → none, memory request 2048 → 880 MB, memory limit 4096 → 880 MB",
 "target": "app-h-prod/deployment/app-h-embed:app"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/deployment/app-ac-ai:ai</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 3579 MB, CPU request under by 5.262 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-ac-ai",
 "severity": "CRITICAL",
 "summary": "CPU request 0.5 → 5.762 cores, memory request 3072 → 6651 MB, memory limit 6144 → 6651 MB",
 "target": "app-ac-prod/deployment/app-ac-ai:ai"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/deployment/app-ac-api:api</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "WARNING",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 623 MB, CPU request under by 0.366 cores",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "app-ac-api",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.466 cores, memory request 256 → 879 MB",
 "target": "app-ac-prod/deployment/app-ac-api:api"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/statefulset/app-ac-opensearch:opensearch</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 522 MB, CPU request over by 0.152 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "CRITICAL",
 "name": "app-ac-opensearch",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.048 cores, CPU limit 2.0 → none, memory request 1536 → 2058 MB, memory limit 2560 → 2058 MB",
 "target": "app-ac-prod/statefulset/app-ac-opensearch:opensearch"
}
```

</details>
<details><summary><code>resources.krr-recommendation.ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 431 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "WARNING",
 "name": "nginx-ingress-ingress-nginx-controller",
 "severity": "WARNING",
 "summary": "CPU request 0.1 → 0.01 cores, memory request 90 → 521 MB, memory limit None → 521 MB",
 "target": "ingress-nginx/deployment/nginx-ingress-ingress-nginx-controller:controller"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/statefulset/elasticsearch:elasticsearch</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 766 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "CRITICAL",
 "name": "elasticsearch",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.31 cores, CPU limit 0.6 → none, memory request 2048 → 2814 MB, memory limit 3072 → 2814 MB",
 "target": "logging/statefulset/elasticsearch:elasticsearch"
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
 "kubegap_reason": "memory request under by 625 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "CRITICAL",
 "name": "prometheus-kube-prometheus-stack-prometheus",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.12 cores, CPU limit 0.3 → none, memory request 1024 → 1649 MB",
 "target": "monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus:prometheus"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/statefulset/tempo:tempo</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "fail",
 "kubegap_reason": "memory request under by 629 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "CRITICAL",
 "name": "tempo",
 "severity": "CRITICAL",
 "summary": "CPU request 0.05 → 0.019 cores, memory request 1024 → 1653 MB, memory limit 2048 → 1653 MB",
 "target": "monitoring/statefulset/tempo:tempo"
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
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "app-h-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 64.0
}
```

</details>
<details><summary><code>security.polaris-security-danger.cluster</code></summary>

```json
{
 "danger_check_counts": {
  "privilegeEscalationAllowed": 100,
  "runAsRootAllowed": 94,
  "runAsPrivileged": 3,
  "sensitiveContainerEnvVar": 8,
  "hostPIDSet": 3,
  "hostNetworkSet": 3,
  "rolebindingClusterAdminRole": 1,
  "rolebindingRolePodExecAttach": 2,
  "clusterrolebindingClusterAdmin": 1,
  "clusterrolebindingPodExecAttach": 3,
  "clusterrolePodExecAttach": 3,
  "rolePodExecAttach": 2,
  "sensitiveConfigmapContent": 1
 },
 "danger_workloads": [
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-ac-prod/statefulset/app-ac-opensearch",
  "app-f-prod/deployment/app-f",
  "arc-systems/deployment/arc-actions-runner-controller",
  "app-ac-prod/deployment/app-ac-ai",
  "app-f-prod/deployment/app-f-mx",
  "app-f-prod/deployment/app-f-vn",
  "kube-system/cronjob/containerd-cleanup-node-a",
  "kube-system/cronjob/containerd-cleanup-node-b",
  "app-c-prod/deployment/app-c-coturn",
  "monitoring/daemonset/kube-prometheus-stack-prometheus-node-exporter",
  "registry/cronjob/registry-tag-cleanup",
  "app-a-prod/pod/app-a-experiment",
  "app-a-prod/deployment/app-a-backend",
  "app-i-prod/deployment/app-i",
  "metallb-system/daemonset/speaker",
  "kube-system/deployment/local-path-provisioner",
  "app-d/deployment/app-d",
  "app-f-prod/deployment/app-f-sales-bot",
  "app-a-prod/deployment/app-m",
  "registry/cronjob/registry-gc",
  "app-g-api/cronjob/app-g-postgres-backup",
  "logging/cronjob/es-index-retention",
  "kube-system/cronjob/etcd-snapshot-backup",
  "logging/deployment/kibana",
  "app-ac-prod/deployment/app-ac-web",
  "app-ac-prod/deployment/app-ac-mcp",
  "app-ac-prod/deployment/app-ac-api",
  "app-ac-prod/deployment/app-ac-projector",
  "app-g-api/deployment/app-g-api",
  "app-i-prod/job/app-i-postgres-manual-backup",
  "logging/job/es-ensure-k3s-template",
  "logging/daemonset/fluent-bit",
  "app-h-prod/deployment/app-h-excel-agent",
  "app-c-prod/deployment/app-c-signaling",
  "app-a-prod/deployment/app-a-umami",
  "app-k/deployment/app-k",
  "app-l-prod/deployment/app-l-api",
  "app-l-prod/deployment/app-l-postgres",
  "monitoring/deployment/opentelemetry-collector",
  "app-f-prod/deployment/app-f-vn-worker",
  "app-k/deployment/app-k-postgres",
  "app-a-prod/deployment/app-a-phoenix",
  "app-h-prod/deployment/app-h-embed",
  "app-f-prod/deployment/app-f-worker",
  "app-b-prod/deployment/app-b-backend",
  "app-f-prod/deployment/app-f-mx-worker",
  "app-f-prod/deployment/app-f-admin",
  "app-g-api/statefulset/app-g-minio",
  "app-a-prod/deployment/app-a-gateway",
  "app-h-prod/deployment/app-h-app-q-client",
  "app-h-prod/deployment/app-h-app-p",
  "app-h-prod/deployment/app-h-admin",
  "app-c-prod/deployment/app-c-web",
  "app-f-prod/statefulset/app-f-redis",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-ac-prod/statefulset/app-ac-postgres",
  "app-a-prod/statefulset/app-a-postgres",
  "app-g-api/statefulset/app-g-postgres",
  "app-ac-prod/statefulset/app-ac-redis",
  "app-i-prod/statefulset/app-i-postgres",
  "registry/statefulset/registry",
  "app-ac-prod/statefulset/app-ac-neo4j",
  "app-h-prod/statefulset/app-h-mysql",
  "app-h-prod/statefulset/app-h-qdrant",
  "app-a-prod/statefulset/app-a-redis",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres",
  "app-c-prod/statefulset/app-c-postgres",
  "app-h-prod/deployment/app-h-api-server",
  "app-a-prod/cronjob/umami-report-day",
  "app-a-prod/cronjob/app-ae-en",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-f-prod/cronjob/app-f-policy-radar",
  "app-a-prod/cronjob/app-ag-japan",
  "app-a-prod/cronjob/app-ag-global",
  "app-f-prod/cronjob/app-f-ga4-digest-day",
  "app-a-prod/cronjob/app-af-day",
  "app-a-prod/cronjob/app-ag-japan-noon",
  "app-f-prod/cronjob/app-f-postgres-backup",
  "app-a-prod/cronjob/app-af-month",
  "app-a-prod/cronjob/umami-report-week",
  "app-a-prod/cronjob/app-ag-global-eu",
  "app-a-prod/cronjob/app-af-week",
  "app-i-prod/cronjob/app-i-postgres-backup",
  "app-f-prod/cronjob/app-f-ga4-digest-week",
  "app-a-prod/cronjob/app-ae-ja",
  "app-h-prod/cronjob/app-h-mysql-backup",
  "app-f-prod/cronjob/app-f-postgres-mx-backup",
  "app-a-prod/cronjob/umami-report-month",
  "app-f-prod/cronjob/app-f-postgres-vn-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-f-prod/cronjob/app-f-ga4-digest-month",
  "app-a-prod/job/app-a-backend-migrate",
  "app-c-prod/job/startup-log-check",
  "monitoring/rolebinding/kube-prometheus-stack-grafana",
  "/clusterrolebinding/argocd-application-controller",
  "reloader/deployment/reloader-reloader",
  "kube-system/daemonset/nvidia-device-plugin",
  "metallb-system/deployment/controller",
  "app-l-prod/deployment/app-l-web",
  "app-b-prod/deployment/app-b-frontend",
  "monitoring/statefulset/tempo",
  "app-a-prod/deployment/app-a-frontend",
  "logging/statefulset/elasticsearch",
  "kube-system/deployment/coredns",
  "app-a-prod/rolebinding/app-a-sandbox-manager",
  "/clusterrole/argocd-application-controller",
  "/clusterrole/argocd-server",
  "/clusterrole/keda-operator",
  "app-a-prod/role/app-a-sandbox-manager",
  "monitoring/role/kube-prometheus-stack-grafana",
  "/clusterrolebinding/argocd-server",
  "/clusterrolebinding/keda-operator",
  "default/configmap/app-ai-backend-config"
 ],
 "danger_workloads_prod": [
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-ac-prod/statefulset/app-ac-opensearch",
  "app-f-prod/deployment/app-f",
  "app-ac-prod/deployment/app-ac-ai",
  "app-f-prod/deployment/app-f-mx",
  "app-f-prod/deployment/app-f-vn",
  "app-c-prod/deployment/app-c-coturn",
  "app-a-prod/pod/app-a-experiment",
  "app-a-prod/deployment/app-a-backend",
  "app-i-prod/deployment/app-i",
  "app-f-prod/deployment/app-f-sales-bot",
  "app-a-prod/deployment/app-m",
  "app-ac-prod/deployment/app-ac-web",
  "app-ac-prod/deployment/app-ac-mcp",
  "app-ac-prod/deployment/app-ac-api",
  "app-ac-prod/deployment/app-ac-projector",
  "app-i-prod/job/app-i-postgres-manual-backup",
  "app-h-prod/deployment/app-h-excel-agent",
  "app-c-prod/deployment/app-c-signaling",
  "app-a-prod/deployment/app-a-umami",
  "app-l-prod/deployment/app-l-api",
  "app-l-prod/deployment/app-l-postgres",
  "app-f-prod/deployment/app-f-vn-worker",
  "app-a-prod/deployment/app-a-phoenix",
  "app-h-prod/deployment/app-h-embed",
  "app-f-prod/deployment/app-f-worker",
  "app-b-prod/deployment/app-b-backend",
  "app-f-prod/deployment/app-f-mx-worker",
  "app-f-prod/deployment/app-f-admin",
  "app-a-prod/deployment/app-a-gateway",
  "app-h-prod/deployment/app-h-app-q-client",
  "app-h-prod/deployment/app-h-app-p",
  "app-h-prod/deployment/app-h-admin",
  "app-c-prod/deployment/app-c-web",
  "app-f-prod/statefulset/app-f-redis",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-ac-prod/statefulset/app-ac-postgres",
  "app-a-prod/statefulset/app-a-postgres",
  "app-ac-prod/statefulset/app-ac-redis",
  "app-i-prod/statefulset/app-i-postgres",
  "app-ac-prod/statefulset/app-ac-neo4j",
  "app-h-prod/statefulset/app-h-mysql",
  "app-h-prod/statefulset/app-h-qdrant",
  "app-a-prod/statefulset/app-a-redis",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres",
  "app-c-prod/statefulset/app-c-postgres",
  "app-h-prod/deployment/app-h-api-server",
  "app-a-prod/cronjob/umami-report-day",
  "app-a-prod/cronjob/app-ae-en",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-f-prod/cronjob/app-f-policy-radar",
  "app-a-prod/cronjob/app-ag-japan",
  "app-a-prod/cronjob/app-ag-global",
  "app-f-prod/cronjob/app-f-ga4-digest-day",
  "app-a-prod/cronjob/app-af-day",
  "app-a-prod/cronjob/app-ag-japan-noon",
  "app-f-prod/cronjob/app-f-postgres-backup",
  "app-a-prod/cronjob/app-af-month",
  "app-a-prod/cronjob/umami-report-week",
  "app-a-prod/cronjob/app-ag-global-eu",
  "app-a-prod/cronjob/app-af-week",
  "app-i-prod/cronjob/app-i-postgres-backup",
  "app-f-prod/cronjob/app-f-ga4-digest-week",
  "app-a-prod/cronjob/app-ae-ja",
  "app-h-prod/cronjob/app-h-mysql-backup",
  "app-f-prod/cronjob/app-f-postgres-mx-backup",
  "app-a-prod/cronjob/umami-report-month",
  "app-f-prod/cronjob/app-f-postgres-vn-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-f-prod/cronjob/app-f-ga4-digest-month",
  "app-a-prod/job/app-a-backend-migrate",
  "app-c-prod/job/startup-log-check",
  "app-l-prod/deployment/app-l-web",
  "app-b-prod/deployment/app-b-frontend",
  "app-a-prod/deployment/app-a-frontend",
  "app-a-prod/rolebinding/app-a-sandbox-manager",
  "app-a-prod/role/app-a-sandbox-manager"
 ],
 "present": true,
 "score": 75
}
```

</details>
<details><summary><code>security.privileged-or-host-access.app-ac-prod/statefulset/app-ac-opensearch</code></summary>

```json
{
 "flags": [
  "privileged:sysctl"
 ],
 "root_allowed_containers": [
  "opensearch",
  "sysctl"
 ],
 "severe": true,
 "system": false,
 "workload": "app-ac-prod/statefulset/app-ac-opensearch"
}
```

</details>
<details><summary><code>security.secrets-read-permission.istio-reader-clusterrole-istio-system</code></summary>

```json
{
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "istio-system",
   "name": "istio-reader-service-account"
  }
 ],
 "clusterrole": "istio-reader-clusterrole-istio-system"
}
```

</details>
<details><summary><code>security.secrets-read-permission.istiod-clusterrole-istio-system</code></summary>

```json
{
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "istio-system",
   "name": "istiod"
  }
 ],
 "clusterrole": "istiod-clusterrole-istio-system"
}
```

</details>
<details><summary><code>security.secrets-read-permission.kiali</code></summary>

```json
{
 "bound_subjects": [
  {
   "kind": "ServiceAccount",
   "namespace": "istio-system",
   "name": "kiali"
  }
 ],
 "clusterrole": "kiali"
}
```

</details>
<details><summary><code>tenancy.burst-tenant-unbounded.app-ac-prod</code></summary>

```json
{
 "burst_ratio_7d": 96.7,
 "cpu_limits": 10.2,
 "cpu_max_7d": 5.833,
 "cpu_median_7d": 0.06,
 "cpu_metrics_read": true,
 "cpu_p95_7d": 0.918,
 "has_quota": false,
 "kind": "prod",
 "namespace": "app-ac-prod",
 "nodes": {
  "node-a": 5,
  "node-b": 5
 },
 "shares_nodes_with_prod": true,
 "system": false
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
 "rbac_subject_count": 1,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
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
 "tenants_total": 13
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
 "pods": 10,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-boundary-missing.app-ac-prod</code></summary>

```json
{
 "has_limitrange": false,
 "has_quota": false,
 "namespace": "app-ac-prod",
 "networkpolicies": 0,
 "networkpolicy_enforced": true,
 "pods": 10,
 "prod": true,
 "psa_enforce": null,
 "rbac_subject_count": 0,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
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
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-c-prod</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.013,
 "cpu_requests": 0.17,
 "cpu_share_of_cluster_p95": 0.005,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.23,
 "memory_requests_gb": 0.66,
 "multi_org": false,
 "namespace": "app-c-prod",
 "pods": 4,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-f-prod</code></summary>

```json
{
 "burst_ratio_7d": 3.0,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.03,
 "cpu_requests": 0.49,
 "cpu_share_of_cluster_p95": 0.012,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 1.69,
 "memory_requests_gb": 3.91,
 "multi_org": false,
 "namespace": "app-f-prod",
 "pods": 12,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-h-prod</code></summary>

```json
{
 "burst_ratio_7d": 30.8,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.094,
 "cpu_requests": 1.12,
 "cpu_share_of_cluster_p95": 0.037,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 4.84,
 "memory_requests_gb": 6.75,
 "multi_org": false,
 "namespace": "app-h-prod",
 "pods": 10,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-ac-prod</code></summary>

```json
{
 "burst_ratio_7d": 96.7,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.918,
 "cpu_requests": 1.62,
 "cpu_share_of_cluster_p95": 0.362,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 4.76,
 "memory_requests_gb": 7.19,
 "multi_org": false,
 "namespace": "app-ac-prod",
 "pods": 10,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.app-i-prod</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cluster_saturated_7d": true,
 "cpu_p95_7d": 0.006,
 "cpu_requests": 0.1,
 "cpu_share_of_cluster_p95": 0.003,
 "has_quota": false,
 "kind": "prod",
 "memory_p95_7d_gb": 0.25,
 "memory_requests_gb": 0.28,
 "multi_org": false,
 "namespace": "app-i-prod",
 "pods": 2,
 "prod": true,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
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
 "applications": 22,
 "applications_prod": 11,
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
 "progressing": [],
 "unhealthy": [],
 "unhealthy_prod": []
}
```

</details>
<details><summary><code>argocd.default-project-wildcard.cluster</code></summary>

```json
{
 "applications": 22,
 "applications_prod": 11,
 "default_project_apps": 7,
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
 "value": 0.8226307692307692
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
 "prod_workloads": 11,
 "well_known": false,
 "workload_count": 14,
 "workloads": [
  "app-a-prod/statefulset/app-a-postgres",
  "app-a-prod/statefulset/app-a-redis",
  "app-f-prod/statefulset/app-f-postgres",
  "app-f-prod/statefulset/app-f-postgres-mx",
  "app-f-prod/statefulset/app-f-postgres-vn",
  "app-f-prod/statefulset/app-f-redis",
  "app-g-api/statefulset/app-g-minio",
  "app-g-api/statefulset/app-g-postgres",
  "app-ac-prod/statefulset/app-ac-neo4j",
  "app-ac-prod/statefulset/app-ac-opensearch",
  "app-ac-prod/statefulset/app-ac-postgres",
  "app-ac-prod/statefulset/app-ac-redis",
  "app-i-prod/statefulset/app-i-postgres",
  "monitoring/statefulset/tempo"
 ]
}
```

</details>
<details><summary><code>hygiene.polaris-reliability-danger.registry/cronjob/registry-tag-cleanup</code></summary>

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
 "target": "registry/cronjob/registry-tag-cleanup"
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
   "name": "data-app-ah-db-0",
   "prod": false
  }
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.flush-failed</code></summary>

```json
{
 "count": 19,
 "first": "2026-11-14T15:32:37Z",
 "last": "2026-11-14T16:00:37Z",
 "warn_at": 10,
 "fail_at": 500,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 19
 },
 "samples": [
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:32:37.046394759+09:00 [2026/11/14 15:32:37] [ warn] [engine] failed to flush chunk '1-1794670343.846799286.flb', retry in 8 seconds: task_id=2, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:32:37.046483649+09:00 [2026/11/14 15:32:37] [ warn] [engine] failed to flush chunk '1-1794670344.246921521.flb', retry in 10 seconds: task_id=4, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:34:47.046381000+09:00 [2026/11/14 15:34:47] [ warn] [engine] failed to flush chunk '1-1794670476.972759287.flb', retry in 8 seconds: task_id=6, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:34:57.046352489+09:00 [2026/11/14 15:34:57] [ warn] [engine] failed to flush chunk '1-1794670486.753325596.flb', retry in 6 seconds: task_id=7, input=tail.0 > output=es.0 (out_id=0)",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:35:37.047387285+09:00 [2026/11/14 15:35:37] [ warn] [engine] failed to flush chunk '1-1794670523.848911706.flb', retry in 10 seconds: task_id=2, input=tail.0 > output=es.0 (out_id=0)"
 ]
}
```

</details>
<details><summary><code>logs.signatures.fluent-bit.upstream-down</code></summary>

```json
{
 "count": 6,
 "first": "2026-11-14T15:34:47Z",
 "last": "2026-11-14T16:02:42Z",
 "warn_at": 5,
 "fail_at": 200,
 "files": {
  "logs/pods/fluent-bit/logging_fluent-bit.log": 6
 },
 "samples": [
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:34:47.046295347+09:00 [2026/11/14 15:34:47] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:36:32.046250145+09:00 [2026/11/14 15:36:32] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:43:42.046228422+09:00 [2026/11/14 15:43:42] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:44:57.046450753+09:00 [2026/11/14 15:44:57] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error",
  "[pod/fluent-bit-bmdwx/fluent-bit] 2026-11-15T00:56:47.046270045+09:00 [2026/11/14 15:56:47] [error] [input:kubernetes_events:kubernetes_events.1] upstream connection initialization error"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metrics-server.scrape-failed</code></summary>

```json
{
 "count": 12,
 "first": "2026-11-14T04:20:27Z",
 "last": "2026-11-14T05:16:26Z",
 "warn_at": 5,
 "fail_at": 100,
 "files": {
  "logs/pods/metrics-server/kube-system_metrics-server.log": 12
 },
 "samples": [
  "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:20:27.001662164Z E1114 04:20:27.001301       1 scraper.go:147] \"Failed to scrape node, timeout to access kubelet\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": c",
  "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:20:42.003816815Z E1114 04:20:42.003679       1 scraper.go:147] \"Failed to scrape node, timeout to access kubelet\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": c",
  "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:20:47.040046597Z E1114 04:20:47.039899       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": http2: client connection los",
  "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:21:01.990903128Z E1114 04:21:01.990772       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": dial tcp <ip>:10250",
  "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T04:21:16.997815336Z E1114 04:21:16.997665       1 scraper.go:149] \"Failed to scrape node\" err=\"Get \\\"https://<ip>:10250/metrics/resource\\\": dial tcp <ip>:10250"
 ]
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
<details><summary><code>observability.golden-signals-missing.app-ac-prod/app-ac</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-ac.lab-j.example"
 ],
 "ingress": "app-ac",
 "namespace": "app-ac-prod",
 "services": [
  "app-ac-istio"
 ],
 "source": null
}
```

</details>
<details><summary><code>observability.golden-signals-missing.app-ac-prod/app-ac-machine</code></summary>

```json
{
 "cluster_ic_metrics": false,
 "hosts": [
  "app-ac-api.lab-j.example",
  "app-ac-mcp.lab-j.example"
 ],
 "ingress": "app-ac-machine",
 "namespace": "app-ac-prod",
 "services": [
  "app-ac-istio"
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
<details><summary><code>observability.no-symptom-alerts.cluster</code></summary>

```json
{
 "alerting": 163,
 "by_class": {
  "cause": 155,
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
 "alerting": 163,
 "by_class": {
  "cause": 155,
  "app-cause": 1,
  "app": 7
 },
 "by_severity": {
  "warning": 106,
  "critical": 49,
  "none": 2,
  "info": 6
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
  "PrometheusErrorSendingAlertsToAnyAlertmanager",
  "NodeRootDiskCritical",
  "PublicDeploymentUnavailable",
  "PublicStatefulSetUnavailable"
 ]
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
 "max_job_duration_s": 53,
 "median_job_duration_s": 53,
 "runtime_over_interval": 0.88,
 "schedule": "* * * * *",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
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
 "startup": null,
 "workload": "app-g-api/statefulset/app-g-postgres"
}
```

</details>
<details><summary><code>resilience.db-probe-timeout.monitoring/statefulset/tempo:tempo</code></summary>

```json
{
 "container": "tempo",
 "db_probe_timeout_1s": true,
 "liveness": {
  "type": "httpGet",
  "path": "/ready",
  "port": 3200,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": false,
 "readiness": {
  "type": "httpGet",
  "path": "/ready",
  "port": 3200,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "startup": null,
 "workload": "monitoring/statefulset/tempo"
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
  "path": "pg_isready -U platform_admin -d platform_admin",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "prod": false,
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U platform_admin -d platform_admin",
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
  "(none, 0)": 103,
  "system-cluster-critical": 1,
  "system-node-critical": 3
 },
 "preempted_events": 0,
 "prod_max_priority": 0,
 "prod_pods": 56,
 "prod_pods_without_class": 56,
 "user_classes": []
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-c-prod/statefulset/app-c-postgres</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-c-postgres",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "postgres-data-app-c-postgres-0"
 ],
 "services": [
  "app-c-postgres"
 ],
 "target": "app-c-prod/statefulset/app-c-postgres"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-h-prod/statefulset/app-h-qdrant</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-h-qdrant",
 "other_backup_cronjobs_in_namespace": [
  {
   "name": "app-h-mysql-backup",
   "suspend": false,
   "targets_db": [
    "app-h-prod/statefulset/app-h-mysql"
   ]
  }
 ],
 "prod": true,
 "pvcs": [
  "app-h-qdrant-data-app-h-qdrant-0"
 ],
 "services": [
  "app-h-qdrant"
 ],
 "target": "app-h-prod/statefulset/app-h-qdrant"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-neo4j</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-ac-neo4j",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-ac-neo4j-0"
 ],
 "services": [
  "app-ac-neo4j"
 ],
 "target": "app-ac-prod/statefulset/app-ac-neo4j"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-opensearch</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-ac-opensearch",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-ac-opensearch-0"
 ],
 "services": [
  "app-ac-opensearch"
 ],
 "target": "app-ac-prod/statefulset/app-ac-opensearch"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-ac-prod/statefulset/app-ac-postgres</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "statefulset",
 "name": "app-ac-postgres",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "data-app-ac-postgres-0"
 ],
 "services": [
  "app-ac-postgres"
 ],
 "target": "app-ac-prod/statefulset/app-ac-postgres"
}
```

</details>
<details><summary><code>resilience.prod-db-without-backup-cronjob.app-l-prod/deployment/app-l-postgres</code></summary>

```json
{
 "backup_cronjobs": [],
 "kind": "deployment",
 "name": "app-l-postgres",
 "other_backup_cronjobs_in_namespace": [],
 "prod": true,
 "pvcs": [
  "app-l-postgres-data"
 ],
 "services": [
  "app-l-postgres"
 ],
 "target": "app-l-prod/deployment/app-l-postgres"
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
<details><summary><code>resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-neo4j</code></summary>

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
 "workload": "app-ac-prod/statefulset/app-ac-neo4j"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-opensearch</code></summary>

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
 "workload": "app-ac-prod/statefulset/app-ac-opensearch"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-postgres</code></summary>

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
 "workload": "app-ac-prod/statefulset/app-ac-postgres"
}
```

</details>
<details><summary><code>resilience.single-eligible-node.app-ac-prod/statefulset/app-ac-redis</code></summary>

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
 "workload": "app-ac-prod/statefulset/app-ac-redis"
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
<details><summary><code>resilience.single-eligible-node.monitoring/statefulset/tempo</code></summary>

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
 "prod": false,
 "replicas": 1,
 "serves_traffic": true,
 "workload": "monitoring/statefulset/tempo"
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
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-backend-79c97cbbd6-kkc2d",
  "container": "backend"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.029420458198712297,
  "cpu_p95_7d_cores": 0.00294204581987123,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-a-prod/deploy/app-a-gateway:gateway</code></summary>

```json
{
 "labels": {
  "namespace": "app-a-prod",
  "pod": "app-a-gateway-644c97fbc-q7wd8",
  "container": "gateway"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.0018810182462118017,
  "cpu_p95_7d_cores": 0.00018810182462118018,
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
  "cpu_request_p95_ratio_7d": 0.2903227018106076,
  "cpu_p95_7d_cores": 0.058064540362121525,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-h-prod/deploy/app-h-api-server:app</code></summary>

```json
{
 "labels": {
  "namespace": "app-h-prod",
  "pod": "app-h-api-server-7ccdccd9f8-46gdp",
  "container": "app"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.13471973835030668,
  "cpu_p95_7d_cores": 0.013471973835030668,
  "container_cpu_request_cores": 0.1
 }
}
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
  "cpu_request_p95_ratio_7d": 0.07862836858398625,
  "cpu_p95_7d_cores": 0.015725673716797253,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-ac-prod/sts/app-ac-opensearch:opensearch</code></summary>

```json
{
 "labels": {
  "namespace": "app-ac-prod",
  "pod": "app-ac-opensearch-0",
  "container": "opensearch"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.24160177375793823,
  "cpu_p95_7d_cores": 0.04832035475158765,
  "container_cpu_request_cores": 0.2
 }
}
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.app-ac-prod/sts/app-ac-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-ac-prod",
  "pod": "app-ac-postgres-0",
  "container": "postgres"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.1468951441725167,
  "cpu_p95_7d_cores": 0.014689514417251671,
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
   "cpu_request_p95_ratio_7d": 0.10289135708458158,
   "cpu_p95_7d_cores": 0.010289135708458158,
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
   "cpu_request_p95_ratio_7d": 0.11252243836821739,
   "cpu_p95_7d_cores": 0.011252243836821739,
   "container_cpu_request_cores": 0.1
  }
 }
]
```

</details>
<details><summary><code>resources.cpu-request-overprovisioned.istio-system/deploy/istiod:discovery</code></summary>

```json
{
 "labels": {
  "namespace": "istio-system",
  "pod": "istiod-6f6d996c58-ggwp2",
  "container": "discovery"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.016743575499933838,
  "cpu_p95_7d_cores": 0.0033487150999867675,
  "container_cpu_request_cores": 0.2
 }
}
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
  "cpu_request_p95_ratio_7d": 0.003043038328759266,
  "cpu_p95_7d_cores": 0.0003043038328759266,
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
  "cpu_request_p95_ratio_7d": 0.03172111008893534,
  "cpu_p95_7d_cores": 0.0031721110088935344,
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
  "cpu_request_p95_ratio_7d": 0.017902226820237763,
  "cpu_p95_7d_cores": 0.0017902226820237766,
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
  "cpu_request_p95_ratio_7d": 0.10130918196239645,
  "cpu_p95_7d_cores": 0.010130918196239645,
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
  "cpu_request_p95_ratio_7d": 0.08214171728838796,
  "cpu_p95_7d_cores": 0.008214171728838796,
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
  "pod": "kibana-6bcf6d579b-p2rgv",
  "container": "kibana"
 },
 "values": {
  "cpu_request_p95_ratio_7d": 0.025921753518403378,
  "cpu_p95_7d_cores": 0.005184350703680676,
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
  "cpu_request_p95_ratio_7d": 0.01256320501965153,
  "cpu_p95_7d_cores": 0.001256320501965153,
  "container_cpu_request_cores": 0.1
 }
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-adk"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-c</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-c"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-express</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-express"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-go</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-go"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-nestjs"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-network</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-network"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-nextjs"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-python"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-python-ml"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-spring"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-sql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-sandbox-prepull",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.05 → none, memory request 16 → 100 MB",
 "target": "app-a-prod/daemonset/app-a-sandbox-prepull:hold-todo"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/deployment/app-a-frontend:frontend</code></summary>

```json
{
 "cpu_limit_sev": "UNKNOWN",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 174 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "app-a-frontend",
 "severity": "OK",
 "summary": "CPU HPA detected, memory request 128 → 302 MB",
 "target": "app-a-prod/deployment/app-a-frontend:frontend"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-a-prod/statefulset/app-a-redis:redis</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 68 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-a-redis",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB",
 "target": "app-a-prod/statefulset/app-a-redis:redis"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-c-prod/deployment/app-c-coturn:coturn</code></summary>

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
 "name": "app-c-coturn",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.2 → none, memory request 32 → 100 MB",
 "target": "app-c-prod/deployment/app-c-coturn:coturn"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-d/deployment/app-d:nginx</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 84 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-d",
 "severity": "WARNING",
 "summary": "CPU request 0.01 → 0.01 cores, CPU limit 0.1 → none, memory request 16 → 100 MB",
 "target": "app-d/deployment/app-d:nginx"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-f-prod/deployment/app-f-vn-worker:worker</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 259 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-f-vn-worker",
 "severity": "CRITICAL",
 "summary": "CPU request 0.03 → 0.046 cores, CPU limit 0.2 → none, memory request 576 → 317 MB, memory limit 1408 → 317 MB",
 "target": "app-f-prod/deployment/app-f-vn-worker:worker"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-f-prod/statefulset/app-f-redis:redis</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 68 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "app-f-redis",
 "severity": "WARNING",
 "summary": "CPU request 0.02 → 0.01 cores, CPU limit 0.1 → none, memory request 32 → 100 MB",
 "target": "app-f-prod/statefulset/app-f-redis:redis"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-h-prod/deployment/app-h-excel-agent:app</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 250 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "app-h-excel-agent",
 "severity": "CRITICAL",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 1.0 → none, memory request 256 → 506 MB, memory limit 1024 → 506 MB",
 "target": "app-h-prod/deployment/app-h-excel-agent:app"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-h-prod/statefulset/app-h-mysql:mysql</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.176 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "OK",
 "name": "app-h-mysql",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.024 cores, CPU limit 1.5 → none, memory request 1600 → 1433 MB, memory limit 3200 → 1433 MB",
 "target": "app-h-prod/statefulset/app-h-mysql:mysql"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/deployment/app-ac-istio:istio-proxy</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 69 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "GOOD",
 "name": "app-ac-istio",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.011 cores, CPU limit 1.0 → none, memory request 64 → 133 MB, memory limit 512 → 133 MB",
 "target": "app-ac-prod/deployment/app-ac-istio:istio-proxy"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/deployment/app-ac-web:web</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "CRITICAL",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 90 MB, CPU request under by 0.784 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "app-ac-web",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.884 cores, memory request 256 → 346 MB, memory limit 1024 → 346 MB",
 "target": "app-ac-prod/deployment/app-ac-web:web"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-ac-prod/statefulset/app-ac-neo4j:neo4j</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 108 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "OK",
 "name": "app-ac-neo4j",
 "severity": "CRITICAL",
 "summary": "CPU request 0.1 → 0.075 cores, CPU limit 1.0 → none, memory request 1024 → 1132 MB, memory limit 2048 → 1132 MB",
 "target": "app-ac-prod/statefulset/app-ac-neo4j:neo4j"
}
```

</details>
<details><summary><code>resources.krr-recommendation.istio-system/deployment/istiod:discovery</code></summary>

```json
{
 "cpu_limit_sev": "UNKNOWN",
 "cpu_request_sev": "UNKNOWN",
 "info": {
  "cpu": "HPA detected"
 },
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 391 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "istiod",
 "severity": "CRITICAL",
 "summary": "CPU HPA detected, memory request 512 → 121 MB, memory limit 1024 → 121 MB",
 "target": "istio-system/deployment/istiod:discovery"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/daemonset/fluent-bit:fluent-bit</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "DaemonSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 86 MB",
 "memory_limit_sev": "GOOD",
 "memory_request_sev": "GOOD",
 "name": "fluent-bit",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.085 cores, CPU limit 0.1 → none, memory request 50 → 136 MB",
 "target": "logging/daemonset/fluent-bit:fluent-bit"
}
```

</details>
<details><summary><code>resources.krr-recommendation.logging/deployment/kibana:kibana</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "OK",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "CPU request over by 0.19 cores",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "GOOD",
 "name": "kibana",
 "severity": "CRITICAL",
 "summary": "CPU request 0.2 → 0.01 cores, CPU limit 0.5 → none, memory request 512 → 446 MB, memory limit 1024 → 446 MB",
 "target": "logging/deployment/kibana:kibana"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/deployment/kube-prometheus-stack-grafana:grafana</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request over by 258 MB",
 "memory_limit_sev": "CRITICAL",
 "memory_request_sev": "WARNING",
 "name": "kube-prometheus-stack-grafana",
 "severity": "CRITICAL",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.15 → none, memory request 512 → 254 MB, memory limit 768 → 254 MB",
 "target": "monitoring/deployment/kube-prometheus-stack-grafana:grafana"
}
```

</details>
<details><summary><code>resources.krr-recommendation.monitoring/deployment/opentelemetry-collector:opentelemetry-collector</code></summary>

```json
{
 "cpu_limit_sev": "GOOD",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 255 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "WARNING",
 "name": "opentelemetry-collector",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.015 cores, memory request 128 → 383 MB",
 "target": "monitoring/deployment/opentelemetry-collector:opentelemetry-collector"
}
```

</details>
<details><summary><code>resources.krr-recommendation.registry/statefulset/registry:registry</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "StatefulSet",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 224 MB",
 "memory_limit_sev": "OK",
 "memory_request_sev": "OK",
 "name": "registry",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.5 → none, memory request 128 → 352 MB",
 "target": "registry/statefulset/registry:registry"
}
```

</details>
<details><summary><code>resources.krr-recommendation.app-l-prod/deployment/app-l-web:web</code></summary>

```json
{
 "cpu_limit_sev": "WARNING",
 "cpu_request_sev": "GOOD",
 "info": {},
 "kind": "Deployment",
 "kubegap_level": "warn",
 "kubegap_reason": "memory request under by 81 MB",
 "memory_limit_sev": "WARNING",
 "memory_request_sev": "GOOD",
 "name": "app-l-web",
 "severity": "WARNING",
 "summary": "CPU request 0.05 → 0.01 cores, CPU limit 0.3 → none, memory request 128 → 209 MB, memory limit 512 → 209 MB",
 "target": "app-l-prod/deployment/app-l-web:web"
}
```

</details>
<details><summary><code>scaling.hpa-flapping.app-h-prod/hpa/app-h-admin</code></summary>

```json
{
 "labels": {
  "container": "kube-state-metrics",
  "endpoint": "http",
  "horizontalpodautoscaler": "app-h-admin",
  "instance": "<ip>:8080",
  "job": "kube-state-metrics",
  "namespace": "app-h-prod",
  "pod": "kube-prometheus-stack-kube-state-metrics-74b875c9c-vwtq2",
  "service": "kube-prometheus-stack-kube-state-metrics"
 },
 "value": 34.0
}
```

</details>
<details><summary><code>security.no-default-deny.cluster</code></summary>

```json
{
 "default_deny_ingress_namespaces": [],
 "enforced": true,
 "policies": 9,
 "prod_without_default_deny": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-f-prod",
  "app-h-prod",
  "app-ac-prod",
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
  "app-ac-prod",
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
  "app-ac-prod/deployment/app-ac-ai",
  "app-ac-prod/deployment/app-ac-api",
  "app-ac-prod/deployment/app-ac-mcp",
  "app-ac-prod/deployment/app-ac-projector",
  "app-ac-prod/deployment/app-ac-web",
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
  "app-ac-prod/statefulset/app-ac-neo4j",
  "app-ac-prod/statefulset/app-ac-opensearch",
  "app-ac-prod/statefulset/app-ac-postgres",
  "app-ac-prod/statefulset/app-ac-redis",
  "app-i-prod/statefulset/app-i-postgres",
  "app-a-prod/daemonset/app-a-sandbox-prepull",
  "app-a-prod/cronjob/app-a-postgres-backup",
  "app-a-prod/cronjob/app-a-sandbox-watchdog",
  "app-a-prod/cronjob/app-ae-en",
  "app-a-prod/cronjob/app-ae-ja",
  "app-a-prod/cronjob/app-af-day",
  "app-a-prod/cronjob/app-af-month",
  "app-a-prod/cronjob/app-af-week",
  "app-a-prod/cronjob/app-ag-global",
  "app-a-prod/cronjob/app-ag-global-eu",
  "app-a-prod/cronjob/app-ag-japan",
  "app-a-prod/cronjob/app-ag-japan-noon",
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
 "service_accounts": 99,
 "token_mounted": 94,
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
  "app-ac-prod/deployment/app-ac-ai",
  "app-ac-prod/deployment/app-ac-api",
  "app-ac-prod/deployment/app-ac-istio",
  "app-ac-prod/deployment/app-ac-mcp",
  "app-ac-prod/statefulset/app-ac-neo4j",
  "app-ac-prod/statefulset/app-ac-opensearch",
  "app-ac-prod/statefulset/app-ac-postgres",
  "app-ac-prod/deployment/app-ac-projector",
  "app-ac-prod/statefulset/app-ac-redis",
  "app-ac-prod/deployment/app-ac-web",
  "app-i-prod/deployment/app-i",
  "app-i-prod/statefulset/app-i-postgres",
  "app-l-prod/deployment/app-l-api",
  "app-l-prod/deployment/app-l-postgres",
  "app-l-prod/deployment/app-l-web"
 ],
 "workloads": 96
}
```

</details>
<details><summary><code>storage.prod-db-reclaim-delete.cluster</code></summary>

```json
{
 "prod_db_delete_reclaim": [
  "app-f-prod/app-f-postgres-backup-node-a-pvc",
  "app-f-prod/app-f-postgres-vn-backup-node-a-pvc",
  "app-h-prod/app-h-mysql-backup-node-a-pvc",
  "app-i-prod/app-i-postgres-backup-node-a-pvc"
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
   "used_ratio": 0.707,
   "inode_ratio": 0.119,
   "growth_gb_per_day": 0.991,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "statefulset/app-h-qdrant"
   ],
   "db_like": true,
   "pv": "pvc-76f7091e-04fe-4abb-98b6-e814163b9ee6",
   "zone": null,
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ac-prod",
   "name": "app-ac-ai-models",
   "target": "app-ac-prod/app-ac-ai-models",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 15.0,
   "capacity_gb": 106.7,
   "used_ratio": 0.707,
   "inode_ratio": 0.119,
   "growth_gb_per_day": 2.049,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "deployment/app-ac-ai"
   ],
   "db_like": false,
   "pv": "pvc-4a73f987-9759-4cfe-9d4c-d3b672e20847",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "used_ratio": 0.707,
   "inode_ratio": 0.119,
   "growth_gb_per_day": 0.988,
   "days_to_full": null,
   "metrics": true,
   "host_fs": true,
   "workloads": [
    "deployment/app-k-postgres"
   ],
   "db_like": true,
   "pv": "pvc-123d97df-e04a-495f-9283-69147d9a8679",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "growth_gb_per_day": 1.74,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-a-postgres-backup-29910435"
   ],
   "db_like": true,
   "pv": "pvc-ff3e86cb-38ac-461e-93ea-fc0c6f0fadda",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "default",
   "name": "data-app-ah-db-0",
   "target": "default/data-app-ah-db-0",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-f-prod",
   "name": "app-f-postgres-backup-node-a-pvc",
   "target": "app-f-prod/app-f-postgres-backup-node-a-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": 0.514,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-f-postgres-backup-29910450"
   ],
   "db_like": true,
   "pv": "pvc-577a8c2b-efa5-4d04-8def-695ebf1a7780",
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
    "job/app-f-postgres-backup-29907570"
   ],
   "db_like": true,
   "pv": "pvc-e8064a22-b689-4d23-adef-de705d889c95",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
    "job/app-f-postgres-mx-backup-29910450"
   ],
   "db_like": true,
   "pv": "pvc-378c5351-e088-4317-9671-7f05346e9531",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-f-prod",
   "name": "app-f-postgres-vn-backup-node-a-pvc",
   "target": "app-f-prod/app-f-postgres-vn-backup-node-a-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": 0.0,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-f-postgres-vn-backup-29910450"
   ],
   "db_like": true,
   "pv": "pvc-cfc6cc02-2095-4abc-b14c-76b9f555ce94",
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
    "job/app-f-postgres-vn-backup-29907570"
   ],
   "db_like": true,
   "pv": "pvc-76170548-ef10-4112-9aaf-5332ae1eeeaa",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-g-api",
   "name": "app-g-postgres-backup-node-a-pvc",
   "target": "app-g-api/app-g-postgres-backup-node-a-pvc",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-g-postgres-backup-29910470"
   ],
   "db_like": true,
   "pv": "pvc-104d7c05-194e-4ffd-adda-7c6a19d1620e",
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
    "job/app-g-postgres-backup-29907590"
   ],
   "db_like": true,
   "pv": "pvc-228da581-f434-4f84-ba50-d91df7133690",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-h-prod",
   "name": "app-h-mysql-backup-node-a-pvc",
   "target": "app-h-prod/app-h-mysql-backup-node-a-pvc",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 10.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": 172.122,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/app-h-mysql-backup-29910410"
   ],
   "db_like": true,
   "pv": "pvc-b1675e87-c0b0-474a-ad0a-20715dbb3dff",
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
    "job/app-h-mysql-backup-29907530",
    "statefulset/app-h-mysql"
   ],
   "db_like": true,
   "pv": "pvc-a9a03cde-f245-4987-b4b8-e61763da9993",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ac-prod",
   "name": "data-app-ac-neo4j-0",
   "target": "app-ac-prod/data-app-ac-neo4j-0",
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
    "statefulset/app-ac-neo4j"
   ],
   "db_like": true,
   "pv": "pvc-527a0666-8b34-4a7b-90ad-9021acfe8c51",
   "zone": null,
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ac-prod",
   "name": "data-app-ac-opensearch-0",
   "target": "app-ac-prod/data-app-ac-opensearch-0",
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
    "statefulset/app-ac-opensearch"
   ],
   "db_like": true,
   "pv": "pvc-51f46ef0-5ef3-4879-86c6-dffb5fed8ac0",
   "zone": null,
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ac-prod",
   "name": "data-app-ac-postgres-0",
   "target": "app-ac-prod/data-app-ac-postgres-0",
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
    "statefulset/app-ac-postgres"
   ],
   "db_like": true,
   "pv": "pvc-449bc551-0e92-441c-9f9f-9c069efca0c7",
   "zone": null,
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "app-ac-prod",
   "name": "data-app-ac-redis-0",
   "target": "app-ac-prod/data-app-ac-redis-0",
   "prod": true,
   "phase": "Bound",
   "storage_class": "local-path-node-b",
   "requested_gb": 2.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": null,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "statefulset/app-ac-redis"
   ],
   "db_like": true,
   "pv": "pvc-88ebc552-2d81-4a82-a0f3-e2880ff9726c",
   "zone": null,
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "kube-system",
   "name": "etcd-snapshot-backup-node-a-pvc",
   "target": "kube-system/etcd-snapshot-backup-node-a-pvc",
   "prod": false,
   "phase": "Bound",
   "storage_class": "local-path",
   "requested_gb": 5.0,
   "capacity_gb": null,
   "used_ratio": null,
   "inode_ratio": null,
   "growth_gb_per_day": -6.157,
   "days_to_full": null,
   "metrics": false,
   "host_fs": true,
   "workloads": [
    "job/etcd-snapshot-backup-29910990"
   ],
   "db_like": true,
   "pv": "pvc-ca88c78c-e3bb-4de5-92e3-6e237ee7fd12",
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
   "name": "app-i-postgres-backup-node-a-pvc",
   "target": "app-i-prod/app-i-postgres-backup-node-a-pvc",
   "prod": true,
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
   "workloads": [
    "job/app-i-postgres-backup-29910420"
   ],
   "db_like": true,
   "pv": "pvc-9d51b8ad-9c71-469f-957c-949fe5e00b9e",
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
    "job/app-i-postgres-backup-29907540"
   ],
   "db_like": true,
   "pv": "pvc-4ce85409-5052-4afb-8c7c-fa0a912f7e09",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
   "access_modes": [
    "ReadWriteOnce"
   ]
  },
  {
   "namespace": "monitoring",
   "name": "data-tempo-0",
   "target": "monitoring/data-tempo-0",
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
    "statefulset/tempo"
   ],
   "db_like": true,
   "pv": "pvc-4a98fd0d-2d0d-43d6-9652-78e0181f6632",
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
    "job/registry-gc-29907600",
    "job/registry-gc-29909040",
    "job/registry-gc-29910480",
    "statefulset/registry"
   ],
   "db_like": true,
   "pv": "pvc-1a2c9674-3fcb-4205-85f2-3f2d08fd1c92",
   "zone": null,
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
   "reclaim_policy": "Retain",
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
 "burst_ratio_7d": 30.8,
 "cpu_limits": 7.3,
 "cpu_max_7d": 0.704,
 "cpu_median_7d": 0.023,
 "cpu_metrics_read": true,
 "cpu_p95_7d": 0.094,
 "has_quota": false,
 "kind": "prod",
 "namespace": "app-h-prod",
 "nodes": {
  "node-b": 6,
  "node-a": 4
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
 "tenants_total": 13
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
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.prod-without-quota.arc-systems</code></summary>

```json
{
 "burst_ratio_7d": null,
 "cpu_p95_7d": 0.339,
 "cpu_requests": 1.0,
 "cpu_share_of_cluster_p95": 0.133,
 "has_quota": false,
 "kind": "ci",
 "memory_p95_7d_gb": 0.78,
 "memory_requests_gb": 2.0,
 "namespace": "arc-systems",
 "pods": 3,
 "prod": false,
 "shares_nodes_with_prod": true,
 "tenants_total": 13
}
```

</details>
<details><summary><code>tenancy.shared-node-limit-overcommit.node-b</code></summary>

```json
{
 "allocatable_memory_gb": 30.7,
 "containers_without_memory_limit": 27,
 "memory_limit_overcommit": 1.66,
 "memory_limits_gb": 51.0,
 "memory_requests_gb": 20.8,
 "namespaces": {
  "app-f-prod": 12,
  "app-a-prod": 9,
  "argocd": 7,
  "monitoring": 7,
  "app-h-prod": 6,
  "app-ac-prod": 5,
  "cert-manager": 3,
  "app-c-prod": 3,
  "external-secrets": 3,
  "app-g-api": 3,
  "keda": 3,
  "kube-system": 3,
  "ingress-nginx": 2,
  "istio-system": 2,
  "logging": 2,
  "app-i-prod": 2,
  "arc-systems": 1,
  "app-b-prod": 1,
  "app-d": 1,
  "metallb-system": 1,
  "app-k": 1,
  "registry": 1,
  "reloader": 1,
  "app-l-prod": 1
 },
 "node": "node-b",
 "pool": "(no-pool)",
 "prod_pods": 39,
 "tenant_count": 3,
 "tenant_kinds": [
  "ci",
  "other",
  "prod"
 ]
}
```

</details>
<details><summary><code>tenancy.tenant-without-limitrange.arc-systems</code></summary>

```json
{
 "containers_without_memory_limit": 4,
 "containers_without_requests": 4,
 "cpu_p95_7d": 0.339,
 "has_limitrange": false,
 "kind": "ci",
 "memory_p95_7d_gb": 0.78,
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
 "p99_s_1h": 0.1325,
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
<details><summary><code>traffic.pod-not-ready.app-a-prod/app-a-sandbox-prepull</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 24,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "app-a-prod/app-a-sandbox-prepull",
 "worst_pod": "app-a-sandbox-prepull-8xvrq"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.app-h-prod/app-h-qdrant-0</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 15,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "app-h-prod/app-h-qdrant-0",
 "worst_pod": "app-h-qdrant-0"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.app-ac-prod/app-ac-mcp</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9851,
 "not_ready_minutes_24h": 11,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "app-ac-prod/app-ac-mcp",
 "worst_pod": "app-ac-mcp-6687b545b6-x5zm7"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.kube-system/nvidia-device-plugin</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 24,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "kube-system/nvidia-device-plugin",
 "worst_pod": "nvidia-device-plugin-fpfbs"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.logging/fluent-bit</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 24,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "logging/fluent-bit",
 "worst_pod": "fluent-bit-bmdwx"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.metallb-system/speaker</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 24,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "metallb-system/speaker",
 "worst_pod": "speaker-spdvw"
}
```

</details>
<details><summary><code>traffic.pod-not-ready.monitoring/kube-prometheus-stack-prometheus-node-exporter</code></summary>

```json
{
 "min_ready_ratio_24h": 0.9833,
 "not_ready_minutes_24h": 24,
 "pods_below_99": 1,
 "unhealthy_events": 0,
 "workload": "monitoring/kube-prometheus-stack-prometheus-node-exporter",
 "worst_pod": "kube-prometheus-stack-prometheus-node-exporter-5wh9f"
}
```

</details>
<details><summary><code>hygiene.no-ephemeral-storage-requests.cluster</code></summary>

```json
{
 "containers": 141,
 "emptydir_without_sizelimit": 12,
 "emptydir_without_sizelimit_prod": [
  "app-ac-prod/deployment/app-ac-istio"
 ],
 "prod_without_request": 71,
 "request_ratio": 0.014,
 "with_request": 2
}
```

</details>
<details><summary><code>hygiene.no-standard-labels.cluster</code></summary>

```json
{
 "standard_label_ratio": 0.22,
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
   "workload": "app-ac-prod/deployment/app-ac-ai",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/deployment/app-ac-api",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/deployment/app-ac-istio",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {
    "gateway.istio.io/managed": "istio.io-gateway-controller",
    "gateway.networking.k8s.io/gateway-class-name": "istio",
    "gateway.networking.k8s.io/gateway-name": "app-ac"
   }
  },
  {
   "workload": "app-ac-prod/deployment/app-ac-mcp",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/deployment/app-ac-projector",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/deployment/app-ac-web",
   "namespace": "app-ac-prod",
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
   "workload": "app-ac-prod/statefulset/app-ac-neo4j",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/statefulset/app-ac-opensearch",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/statefulset/app-ac-postgres",
   "namespace": "app-ac-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-ac-prod/statefulset/app-ac-redis",
   "namespace": "app-ac-prod",
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
   "workload": "monitoring/statefulset/tempo",
   "namespace": "monitoring",
   "prod": false,
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
   "workload": "app-a-prod/cronjob/app-ae-en",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-ae-ja",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-af-day",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-af-month",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-af-week",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-ag-global",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-ag-global-eu",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-ag-japan",
   "namespace": "app-a-prod",
   "prod": true,
   "labels": {}
  },
  {
   "workload": "app-a-prod/cronjob/app-ag-japan-noon",
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
   "workload": "kube-system/cronjob/etcd-snapshot-backup",
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
 "workloads": 125
}
```

</details>
<details><summary><code>hygiene.old-replicasets.cluster</code></summary>

```json
{
 "replicasets_total": 382,
 "replicasets_zero": 316,
 "revision_history_limits": {
  "10": 63,
  "0": 3,
  "3": 1,
  "2": 1
 }
}
```

</details>
<details><summary><code>node.os-not-collected.node-a</code></summary>

```json
{
 "node": "node-a",
 "reason": "os.txt missing"
}
```

</details>
<details><summary><code>node.os-not-collected.node-b</code></summary>

```json
{
 "node": "node-b",
 "reason": "os.txt missing"
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
 "node": "node-b",
 "server_url": "https://<ip>:6443"
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "at_min_ratio_15d": 0.9993053947673073,
 "current_cpu_utilization": 3,
 "days_since_last_scale": 0.6,
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
 "at_min_ratio_15d": 0.9979161843019217,
 "current_cpu_utilization": 12,
 "days_since_last_scale": 0.5,
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
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 4,
 "days_since_last_scale": 4.4,
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
<details><summary><code>scaling.hpa-never-scaled.app-f-prod/deployment/app-f-admin</code></summary>

```json
{
 "at_min_ratio_15d": 0.9997684649224358,
 "current_cpu_utilization": 3,
 "days_since_last_scale": 4.4,
 "keda_owned": false,
 "max": 3,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "name": "app-f-admin",
 "namespace": "app-f-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-f-prod/deployment/app-f-admin",
 "target_cpu_utilization": 60
}
```

</details>
<details><summary><code>scaling.hpa-never-scaled.app-f-prod/deployment/app-f-mx</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 4,
 "days_since_last_scale": 4.4,
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
<details><summary><code>scaling.hpa-never-scaled.app-h-prod/deployment/app-h-app-p</code></summary>

```json
{
 "at_min_ratio_15d": 0.9912016670525584,
 "current_cpu_utilization": 3,
 "days_since_last_scale": 0.2,
 "keda_owned": false,
 "max": 4,
 "metric_types": [
  "cpu",
  "memory"
 ],
 "min": 1,
 "name": "app-h-app-p",
 "namespace": "app-h-prod",
 "never_scaled_15d": true,
 "prod": true,
 "target": "app-h-prod/deployment/app-h-app-p",
 "target_cpu_utilization": 70
}
```

</details>
<details><summary><code>argocd.notifications-not-configured.cluster</code></summary>

```json
{
 "applications_prod": 11,
 "notifications_configured": false,
 "notifications_triggers": 0
}
```

</details>
<details><summary><code>argocd.prod-tracks-moving-ref.cluster</code></summary>

```json
{
 "applications_prod": 11,
 "ignore_differences_apps": 18,
 "prod_tracking_moving_ref": [
  "argocd/application/app-a-prod",
  "argocd/application/app-b-prod",
  "argocd/application/app-c",
  "argocd/application/app-f-kr",
  "argocd/application/app-f-mx",
  "argocd/application/app-f-shared",
  "argocd/application/app-f-vn",
  "argocd/application/app-h",
  "argocd/application/app-ac-prod",
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
  "200": 24,
  "201": 1
 },
 "acme_error_ratio": 0.0,
 "acme_errors": 0,
 "acme_requests": 25,
 "metrics_available": true,
 "not_ready_metric": 0,
 "sync_calls": 1757,
 "sync_errors": 390
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
 "aaaa_ratio": 0.485,
 "cluster_ipv6": false,
 "metrics_available": true,
 "qps_total": 31.75
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
<details><summary><code>hygiene.always-pull-with-tag.app-f-prod/deployment/app-f-vn:db-migrate</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "db-migrate",
 "image": "registry.lab-a.example/app-f-vietnam:prod-2ff89792201f2e1d05e20b51243945ef85af35e4",
 "pull_policy": "Always",
 "registry": "registry.lab-a.example",
 "tag_kind": "tag",
 "workload": "app-f-prod/deployment/app-f-vn"
}
```

</details>
<details><summary><code>hygiene.always-pull-with-tag.istio-system/deployment/kiali:kiali</code></summary>

```json
{
 "always_pull_with_tag": true,
 "container": "kiali",
 "image": "quay.io/kiali/kiali:v2.34.1",
 "pull_policy": "Always",
 "registry": "quay.io",
 "tag_kind": "tag",
 "workload": "istio-system/deployment/kiali"
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
  "app-a-prod": 1,
  "app-h-prod": 1,
  "app-ac-prod": 1
 },
 "by_reason": {
  "Failed": 1,
  "UnexpectedAdmissionError": 2
 },
 "count": 3,
 "oldest_h": 3347.1,
 "prod": 3,
 "sample": [
  "app-a-prod/app-a-experiment",
  "app-h-prod/app-h-embed-768cf69449-99swc",
  "app-ac-prod/app-ac-ai-74b95b458b-jt8ll"
 ]
}
```

</details>
<details><summary><code>hygiene.helm-release-stale.cert-manager/cert-manager</code></summary>

```json
{
 "age_days": 369,
 "app_version": "v1.14.4",
 "chart": "cert-manager-v1.14.4",
 "name": "cert-manager",
 "namespace": "cert-manager",
 "target": "cert-manager/cert-manager"
}
```

</details>
<details><summary><code>hygiene.helm-release-stale.ingress-nginx/nginx-ingress</code></summary>

```json
{
 "age_days": 369,
 "app_version": "1.14.0",
 "chart": "ingress-nginx-4.14.0",
 "name": "nginx-ingress",
 "namespace": "ingress-nginx",
 "target": "ingress-nginx/nginx-ingress"
}
```

</details>
<details><summary><code>hygiene.orphan-configmaps.cluster</code></summary>

```json
{
 "configmaps_total": 154,
 "orphan_configmaps": [
  {
   "namespace": "app-a-prod",
   "name": "app-a-sandbox-codex-config",
   "prod": true,
   "keys": [
    "config.toml"
   ],
   "age_days": 170
  },
  {
   "namespace": "app-a-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "arc-systems",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "argocd",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "cert-manager",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-b-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-c-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "default",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "default",
   "name": "app-ai-backend-config",
   "prod": false,
   "keys": [
    "AWS_REGION",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "DETECTION_FALLBACK_TO_FULL",
    "DETECTION_IOU",
    "DETECTION_MAX_DETECTIONS",
    "DETECTION_MIN_CONFIDENCE",
    "DETECTION_MIN_SIZE",
    "DETECTION_SERVICE_URL",
    "DETECTION_TIMEOUT_MS",
    "EMBEDDING_MODE",
    "JINA_EMBEDDING_DIMENSION",
    "JINA_EMBEDDING_MODELS",
    "JINA_IMAGE_EMBEDDING_MODEL",
    "JWT_EXPIRES_IN",
    "JWT_RELAY_EXPIRES_IN",
    "JWT_RELAY_SECRET",
    "JWT_SECRET",
    "NODE_ENV",
    "PORT",
    "PUBLIC_ASSET_BASE_URL",
    "QDRANT_API_KEY",
    "QDRANT_COLLECTION",
    "QDRANT_DEFAULT_LIMIT",
    "QDRANT_SCORE_THRESHOLD",
    "QDRANT_URL",
    "QDRANT_VECTOR_SIZE",
    "RUN_SCHEMA_SYNC",
    "S3_BUCKET",
    "S3_UPLOAD_PREFIX",
    "TWITTER_CLIENT_ID",
    "TWITTER_CLIENT_ID_RELAY",
    "TWITTER_CLIENT_SECRET",
    "TWITTER_CLIENT_SECRET_RELAY",
    "TWITTER_REDIRECT_URI",
    "TWITTER_REDIRECT_URI_RELAY",
    "TWITTER_SCOPES",
    "TWITTER_SCOPES_RELAY",
    "UPLOAD_URL_TTL"
   ],
   "age_days": 318
  },
  {
   "namespace": "app-d",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-f-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "external-secrets",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-g-api",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-h-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "ingress-nginx",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "istio-system",
   "name": "istio",
   "prod": false,
   "keys": [
    "mesh",
    "meshNetworks"
   ],
   "age_days": 7
  },
  {
   "namespace": "istio-system",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "istio-system",
   "name": "istio-sidecar-injector",
   "prod": false,
   "keys": [
    "config",
    "values"
   ],
   "age_days": 7
  },
  {
   "namespace": "istio-system",
   "name": "values",
   "prod": false,
   "keys": [
    "merged-values",
    "original-values"
   ],
   "age_days": 7
  },
  {
   "namespace": "keda",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "logging",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "metallb-system",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-i-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "monitoring",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-k",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "registry",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "reloader",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-n",
   "name": "istio-ca-crl",
   "prod": false,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  },
  {
   "namespace": "app-l-prod",
   "name": "istio-ca-crl",
   "prod": true,
   "keys": [
    "ca-crl.pem"
   ],
   "age_days": 7
  }
 ]
}
```

</details>
<details><summary><code>hygiene.orphan-secrets.cluster</code></summary>

```json
{
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
   "name": "app-f-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-ah-auth-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-ah-aws-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-ah-db-secret",
   "type": "Opaque",
   "prod": false
  },
  {
   "namespace": "default",
   "name": "app-ah-tls",
   "type": "kubernetes.io/tls",
   "prod": false
  },
  {
   "namespace": "app-f-prod",
   "name": "app-f-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  },
  {
   "namespace": "app-h-prod",
   "name": "app-h-app-aj-prod-tls",
   "type": "kubernetes.io/tls",
   "prod": true
  },
  {
   "namespace": "istio-system",
   "name": "istio-ca-secret",
   "type": "istio.io/ca-root",
   "prod": false
  }
 ],
 "secrets_read": true,
 "secrets_total": 147
}
```

</details>
<details><summary><code>hygiene.unused-crds.cluster</code></summary>

```json
{
 "count": 87,
 "webhooks": 34,
 "zero_by_group": {
  "generators.external-secrets.io": 17,
  "monitoring.coreos.com": 5,
  "security.istio.io": 2,
  "gateway.networking.k8s.io": 5,
  "metallb.io": 5,
  "acme.cert-manager.io": 1,
  "eventing.keda.sh": 2,
  "external-secrets.io": 4,
  "keda.sh": 4,
  "networking.istio.io": 7,
  "helm.cattle.io": 2,
  "actions.summerwind.dev": 1,
  "extensions.istio.io": 2
 },
 "zero_object_count": 57
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
<details><summary><code>kubeproxy.node-cmd-unavailable.cluster</code></summary>

```json
{
 "mode": null,
 "node_cmd_unavailable": [
  "node-a",
  "node-b"
 ],
 "nodes_total": 2
}
```

</details>
<details><summary><code>logs.signatures.cert-manager.orphan-tls-secret</code></summary>

```json
{
 "count": 16,
 "first": "2026-11-14T01:14:00Z",
 "last": "2026-11-14T01:14:00Z",
 "warn_at": 1,
 "fail_at": 1000,
 "files": {
  "logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log": 16
 },
 "samples": [
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701159812Z E1114 01:14:00.701036       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-f-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701225685Z E1114 01:14:00.701193       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-ah",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701252896Z E1114 01:14:00.701230       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-h-poc",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701423094Z E1114 01:14:00.701389       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-f-p",
  "[pod/cert-manager-cainjector-7bf5c557bb-kbtv7/cert-manager-cainjector] 2026-11-14T01:14:00.701907440Z E1114 01:14:00.701874       1 indexers.go:61] \"unable to fetch certificate that owns the secret\" err=\"Certificate.cert-manager.io \\\"app-f-p"
 ]
}
```

</details>
<details><summary><code>logs.signatures.metallb.speaker-peer-unreachable</code></summary>

```json
{
 "count": 545,
 "first": "2026-11-14T12:24:07Z",
 "last": "2026-11-14T16:03:17Z",
 "warn_at": 60,
 "fail_at": 2000,
 "files": {
  "logs/pods/metallb/metallb-system_speaker.log": 545
 },
 "samples": [
  "[pod/speaker-lqmcg/speaker] 2026-11-14T12:43:57.490323576Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-14T12:44:07.491529235Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-14T12:44:58.100766261Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-14T12:45:58.101760466Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro",
  "[pod/speaker-lqmcg/speaker] 2026-11-14T12:46:58.101117206Z {\"caller\":\"speakerlist.go:259\",\"error\":\"1 error occurred:\\n\\t* Failed to join <ip>:7946: dial tcp <ip>:7946: i/o timeout\\n\\n\",\"expected\":1,\"joined\":0,\"level\":\"erro"
 ]
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
  "gateway_cost_usd_total",
  "gateway_requests_total",
  "grpc_server_handling_seconds_bucket",
  "kube_cronjob_status_last_successful_time",
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
  "kube_statefulset_status_replicas_available",
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
 "alert_metrics_without_panel_count": 138,
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
  "AppQClusterMem50",
  "AppQFrontendDown",
  "AppQWatchdogFailing",
  "AlertmanagerFailedToSendAlerts",
  "CPUThrottlingHigh",
  "InfoInhibitor",
  "KubeCPUOvercommit",
  "KubeDaemonSetMisScheduled",
  "KubeDaemonSetRolloutStuck",
  "KubeDeploymentReplicasMismatch",
  "KubeDeploymentRolloutStuck",
  "KubeHpaMaxedOut",
  "KubeJobFailed",
  "KubeMemoryOvercommit",
  "KubeNodeEviction",
  "KubeNodeNotReady",
  "KubeNodePressure",
  "KubeNodeUnreachable",
  "KubePersistentVolumeFillingUp",
  "KubePodCrashLooping",
  "KubePodNotReady",
  "KubeQuotaFullyUsed",
  "KubeStatefulSetReplicasMismatch",
  "KubeStatefulSetUpdateNotRolledOut",
  "NodeCPUHighUsage",
  "NodeDiskIOSaturation",
  "NodeFilesystemSpaceFillingUp",
  "NodeRootDiskLow",
  "PublicDeploymentUnavailable",
  "PublicStatefulSetUnavailable",
  "TargetDown",
  "Watchdog"
 ],
 "never_fired_15d": [
  "AppQBackendDown",
  "AppQClusterCPU50",
  "AppQClusterCPU80",
  "AppQClusterMem80",
  "AppQGatewayDown",
  "AppQGatewayErrorRateHigh",
  "AppQGatewayHighCost",
  "AppQGatewayUpstreamRejecting",
  "AppQLLMQuotaExhausted",
  "AppQPostgresDown",
  "AppQSandboxProvisionFailing",
  "AppQTooManySandboxes",
  "AlertmanagerClusterCrashlooping",
  "AlertmanagerClusterDown",
  "AlertmanagerClusterFailedToSendAlerts",
  "AlertmanagerConfigInconsistent",
  "AlertmanagerFailedReload",
  "AlertmanagerMembersInconsistent",
  "BackupCronJobStale",
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
  "KubeDaemonSetNotScheduled",
  "KubeDeploymentGenerationMismatch",
  "KubeHpaReplicasMismatch",
  "KubeJobNotCompleted",
  "KubeMemoryQuotaOvercommit",
  "KubeNodeReadinessFlapping",
  "KubePdbNotEnoughHealthyPods",
  "KubePersistentVolumeErrors",
  "KubePersistentVolumeInodesFillingUp",
  "KubeQuotaAlmostFull",
  "KubeQuotaExceeded",
  "KubeStateMetricsListErrors",
  "KubeStateMetricsShardingMismatch",
  "KubeStateMetricsShardsMissing",
  "KubeStateMetricsWatchErrors",
  "KubeStatefulSetGenerationMismatch",
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
  "NodeClockNotSynchronising",
  "NodeClockSkewDetected",
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
  "NodeRootDiskCritical",
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
 "never_fired_count": 118,
 "rules_total": 147
}
```

</details>
<details><summary><code>observability.saturation-signal-missing.cluster</code></summary>

```json
{
 "ingresses": 31,
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
   "namespace": "app-ac-prod",
   "ingress": "app-ac",
   "class": "nginx",
   "hosts": [
    "app-ac.lab-j.example"
   ],
   "services": [
    "app-ac-istio"
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
   "namespace": "app-ac-prod",
   "ingress": "app-ac-machine",
   "class": "nginx",
   "hosts": [
    "app-ac-api.lab-j.example",
    "app-ac-mcp.lab-j.example"
   ],
   "services": [
    "app-ac-istio"
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
  "monitoring"
 ]
}
```

</details>
<details><summary><code>observability.unclassified-errors.cluster</code></summary>

```json
{
 "error_lines_unclassified": 593,
 "files_scanned": [
  "logs/pods/alertmanager/monitoring_alertmanager-kube-prometheus-stack-alertmanager.log",
  "logs/pods/argocd/argocd_argocd-application-controller.log",
  "logs/pods/argocd/argocd_argocd-applicationset-controller.log",
  "logs/pods/argocd/argocd_argocd-dex-server.log",
  "logs/pods/argocd/argocd_argocd-notifications-controller.log",
  "logs/pods/argocd/argocd_argocd-redis.log",
  "logs/pods/argocd/argocd_argocd-repo-server.log",
  "logs/pods/argocd/argocd_argocd-server.log",
  "logs/pods/cert-manager/cert-manager_cert-manager-cainjector.log",
  "logs/pods/cert-manager/cert-manager_cert-manager-webhook.log",
  "logs/pods/cert-manager/cert-manager_cert-manager.log",
  "logs/pods/coredns/kube-system_coredns.log",
  "logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log",
  "logs/pods/elasticsearch-opensearch/logging_elasticsearch.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-cert-controller.log",
  "logs/pods/external-secrets/external-secrets_external-secrets-webhook.log",
  "logs/pods/external-secrets/external-secrets_external-secrets.log",
  "logs/pods/fluent-bit/logging_fluent-bit.log",
  "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log",
  "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log",
  "logs/pods/istio/istio-system_istiod.log",
  "logs/pods/keda/keda_keda-admission-webhooks.log",
  "logs/pods/keda/keda_keda-operator-metrics-apiserver.log",
  "logs/pods/keda/keda_keda-operator.log",
  "logs/pods/local-path-provisioner/kube-system_local-path-provisioner.log",
  "logs/pods/metallb/metallb-system_controller.log",
  "logs/pods/metallb/metallb-system_speaker.log",
  "logs/pods/metrics-server/kube-system_metrics-server.log",
  "logs/pods/opentelemetry-collector/monitoring_opentelemetry-collector.log",
  "logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log",
  "logs/pods/reloader/reloader_reloader-reloader.log",
  "logs/pods/tempo-jaeger/monitoring_tempo.log"
 ],
 "lines_scanned": 22307,
 "unclassified_errors": [
  {
   "pattern": "cert-manager | \"re-queuing item due to error processing\" err=\"ACME client for issuer not initialised/available\" logger=\"cert-manager.orders\" …",
   "count": 390,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 390
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T01:12:54.799178861Z E1114 01:12:54.798873       1 controller.go:167] \"re-queuing item due to error processing\" err=\"ACME client for issuer not initialised/available\" log"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:43 +<n>] \"GET …",
   "count": 5,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 5
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:43.259694688Z 162.159.106.217 - - [14/Nov/2026:15:29:43 +0000] \"GET /app-ac/app?root_cause=software-bug&component=coordination-store&symptom=high"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:42 +<n>] \"GET …",
   "count": 4,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 4
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:42.345063213Z 162.159.106.213 - - [14/Nov/2026:15:29:42 +0000] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&symptom=high-error-ra"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET …",
   "count": 3,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 3
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:44.220259715Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app/graph?root_cause=software-bug&component=conntrack&symptom=high-er"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manager\" key=\"app-c-prod/app-c-tls\" …",
   "count": 2,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 2
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:06.063472980Z I1114 02:32:06.063344       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-key-manage"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:46 +<n>] \"GET …",
   "count": 2,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 2
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:46.307428038Z 172.70.134.18 - - [14/Nov/2026:15:45:46 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&component=rbac-service-account&sympto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:51 +<n>] \"GET …",
   "count": 2,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 2
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:51.129653845Z 104.23.211.29 - - [14/Nov/2026:15:45:51 +0000] \"GET /app-ac/app?component=rbac-service-account&symptom=credentials-unavailable&fact"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:41 +<n>] \"GET …",
   "count": 2,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 2
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:41.866867731Z 162.159.106.213 - - [14/Nov/2026:15:29:41 +0000] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&symptom=high-error-ra"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:34 +<n>] \"GET …",
   "count": 2,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 2
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:55:34.233765263Z 172.68.27.67 - - [14/Nov/2026:15:55:34 +0000] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=monitoring-blind-"
  },
  {
   "pattern": "argocd | 1:M 14 Nov <n> 01:13:23.<n> * <bf> \t{ bf-error-rate       :      0.01 }",
   "count": 1,
   "files": {
    "logs/pods/argocd/argocd_argocd-redis.log": 1
   },
   "sample": "[pod/argocd-redis-5879fc7796-7qhvg/redis] 2026-11-14T01:13:23.955050152Z 1:M 14 Nov 2026 01:13:23.954 * <bf> \t{ bf-error-rate       :      0.01 }"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-issuer-acme\" key=\"app-c-prod/app-c-tls-5\" …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:06.155077356Z I1114 02:32:06.154963       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificaterequests-iss"
  },
  {
   "pattern": "cert-manager | ingress 'app-c-prod/cm-acme-http-solver-7tc6d' in work queue no longer exists",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:32.176613805Z E1114 02:32:32.176549       1 controller.go:98] ingress 'app-c-prod/cm-acme-http-solver-7tc6d' in work queue no longer exists"
  },
  {
   "pattern": "cert-manager | \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"app-c-tls-5-<n>\" resource_namespace=\"app-c-prod\" resource_kind=\"Order\" …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:32.845463516Z E1114 02:32:32.842005       1 sync.go:73] \"failed to update status\" logger=\"cert-manager.orders\" resource_name=\"app-c-tls-5-3345871740\" resource_namesp"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"app-c-prod/app-c-tls-5-<n>\" error=\"Operation cannot …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:32.845505626Z I1114 02:32:32.842053       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.orders\" key=\"app-c-prod/d"
  },
  {
   "pattern": "cert-manager | \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"app-c-tls-5-<n>-<n>\\\" not found\" …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:33.947655914Z E1114 02:32:33.947533       1 controller.go:208] \"challenge in work queue no longer exists\" err=\"challenge.acme.cert-manager.io \\\"app-c-tls-5-334587174"
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\" key=\"app-c-prod/app-c-tls\" …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:33.977228605Z I1114 02:32:33.977161       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-readiness\""
  },
  {
   "pattern": "cert-manager | \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" key=\"app-c-prod/app-c-tls\" error=\"Operation …",
   "count": 1,
   "files": {
    "logs/pods/cert-manager/cert-manager_cert-manager.log": 1
   },
   "sample": "[pod/cert-manager-7c4b5b58df-4v7td/cert-manager-controller] 2026-11-14T02:32:33.982322410Z I1114 02:32:33.982168       1 controller.go:162] \"re-queuing item due to optimistic locking on resource\" logger=\"cert-manager.certificates-issuing\" k"
  },
  {
   "pattern": "elasticsearch-opensearch | [<ts>][ERROR][o.o.p.c.c.PluginSettings ] [app-ac-opensearch-0] Loading config file …",
   "count": 1,
   "files": {
    "logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log": 1
   },
   "sample": "[pod/app-ac-opensearch-0/opensearch] 2026-11-14T01:13:43.934794954Z [2026-11-14T01:13:43,918][ERROR][o.o.p.c.c.PluginSettings ] [app-ac-opensearch-0] Loading config file /usr/share/opensearch/config/opensearch-performance-analyzer"
  },
  {
   "pattern": "elasticsearch-opensearch | [<ts>][ERROR][o.o.p.c.c.StatsCollector ] [app-ac-opensearch-0] Error in loading metadata for folderLocation: …",
   "count": 1,
   "files": {
    "logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log": 1
   },
   "sample": "[pod/app-ac-opensearch-0/opensearch] 2026-11-14T01:13:44.372169170Z [2026-11-14T01:13:44,369][ERROR][o.o.p.c.c.StatsCollector ] [app-ac-opensearch-0] Error in loading metadata for folderLocation: /usr/share/opensearch/config/opens"
  },
  {
   "pattern": "elasticsearch-opensearch | [<ts>][WARN ][stderr                   ] [app-ac-opensearch-0] SLF4J: Failed to load class \"org.slf4j.impl.StaticLoggerBinder\".",
   "count": 1,
   "files": {
    "logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log": 1
   },
   "sample": "[pod/app-ac-opensearch-0/opensearch] 2026-11-14T01:13:49.425291331Z [2026-11-14T01:13:49,424][WARN ][stderr                   ] [app-ac-opensearch-0] SLF4J: Failed to load class \"org.slf4j.impl.StaticLoggerBinder\"."
  },
  {
   "pattern": "elasticsearch-opensearch | [<ts>][WARN ][o.o.s.SecurityAnalyticsPlugin] [app-ac-opensearch-0] Failed to initialize LogType config index and builtin log types",
   "count": 1,
   "files": {
    "logs/pods/elasticsearch-opensearch/app-ac-prod_app-ac-opensearch.log": 1
   },
   "sample": "[pod/app-ac-opensearch-0/opensearch] 2026-11-14T01:14:05.969124398Z [2026-11-14T01:14:05,968][WARN ][o.o.s.SecurityAnalyticsPlugin] [app-ac-opensearch-0] Failed to initialize LogType config index and builtin log types"
  },
  {
   "pattern": "grafana | logger=infra.usagestats.collector t=<ts> level=error msg=\"Failed to read all Amazon Prometheus data sources\" error=\"plugin …",
   "count": 1,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 1
   },
   "sample": "[pod/kube-prometheus-stack-grafana-74c84c99-g4grd/grafana] 2026-11-14T06:11:06.061582409Z logger=infra.usagestats.collector t=2026-11-14T06:11:06.06142378Z level=error msg=\"Failed to read all Amazon Prometheus data sources\" error=\"plugin gr"
  },
  {
   "pattern": "grafana | logger=infra.usagestats t=<ts> level=error msg=\"Failed to fetch usage stats from provider\" error=\"plugin …",
   "count": 1,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 1
   },
   "sample": "[pod/kube-prometheus-stack-grafana-74c84c99-g4grd/grafana] 2026-11-14T06:11:06.061638405Z logger=infra.usagestats t=2026-11-14T06:11:06.061469506Z level=error msg=\"Failed to fetch usage stats from provider\" error=\"plugin grafana-amazonprome"
  },
  {
   "pattern": "grafana | logger=infra.usagestats.collector t=<ts> level=error msg=\"Failed to get advisor usage stats\" error=\"the server could not find the requested …",
   "count": 1,
   "files": {
    "logs/pods/grafana/monitoring_kube-prometheus-stack-grafana.log": 1
   },
   "sample": "[pod/kube-prometheus-stack-grafana-74c84c99-g4grd/grafana] 2026-11-14T06:11:06.361277667Z logger=infra.usagestats.collector t=2026-11-14T06:11:06.361190994Z level=error msg=\"Failed to get advisor usage stats\" error=\"the server could not fin"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:17:03 +<n>] \"GET /app-ac/app/factors/single-point-of-failure HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:17:03.668560711Z 104.22.104.133 - - [14/Nov/2026:15:17:03 +0000] \"GET /app-ac/app/factors/single-point-of-failure HTTP/2.0\" 200 33564 \"-\" \"Mozilla/5"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:23:33 +<n>] \"GET /app-ac/app?symptom=autoscaler-scale-up-failed HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:23:33.137742883Z 172.71.191.58 - - [14/Nov/2026:15:23:33 +0000] \"GET /app-ac/app?symptom=autoscaler-scale-up-failed HTTP/2.0\" 200 155070 \"-\" \"Mozill"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:25:29 +<n>] \"GET /app-ac/app?root_cause=capacity&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:25:29.011504255Z 104.22.182.67 - - [14/Nov/2026:15:25:29 +0000] \"GET /app-ac/app?root_cause=capacity&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0\" 20"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:25:30 +<n>] \"GET /app-ac/app?root_cause=capacity&factor=single-point-of-failure&_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:25:30.817500347Z 104.22.182.67 - - [14/Nov/2026:15:25:30 +0000] \"GET /app-ac/app?root_cause=capacity&factor=single-point-of-failure&_rsc=eqsiq HTTP/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:41 +<n>] \"GET /app-ac/app/cases/IL-<n>?_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:41.838270492Z 162.159.106.213 - - [14/Nov/2026:15:29:41 +0000] \"GET /app-ac/app/cases/IL-0277?_rsc=eqsiq HTTP/2.0\" 200 256 \"https://lab-j.example/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:42 +<n>] \"GET /app-ac/app/ko?root_cause=software-bug&component=conntrack&symptom=high-error-rate&_rsc=eqsiq …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:42.306147787Z 162.159.106.213 - - [14/Nov/2026:15:29:42 +0000] \"GET /app-ac/app/ko?root_cause=software-bug&component=conntrack&symptom=high-error"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:44.149029133Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&_rsc=eqsiq HTTP/2.0\" "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET /app-ac/app?_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:44.245752834Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app?_rsc=eqsiq HTTP/2.0\" 200 223 \"https://lab-j.example/app-ac/ap"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET /app-ac/app/docs?_rsc=18mtl HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:29:44.245788301Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app/docs?_rsc=18mtl HTTP/2.0\" 200 1825 \"https://lab-j.example/incident"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:30:01 +<n>] \"GET /app-ac/app?org=discord&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:30:01.036555423Z 104.23.195.13 - - [14/Nov/2026:15:30:01 +0000] \"GET /app-ac/app?org=discord&root_cause=software-bug&symptom=high-error-rate HTTP/2."
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:30:25 +<n>] \"GET /app-ac/app?org=github&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:30:25.860736996Z 172.69.90.139 - - [14/Nov/2026:15:30:25 +0000] \"GET /app-ac/app?org=github&root_cause=software-bug&symptom=high-error-rate HTTP/2.0"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:30:26 +<n>] \"GET /app-ac/app?org=slack&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:30:26.779609711Z 172.71.98.183 - - [14/Nov/2026:15:30:26 +0000] \"GET /app-ac/app?org=slack&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\""
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:44:28 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:44:28.689156616Z 104.22.64.197 - - [14/Nov/2026:15:44:28 +0000] \"GET /app-ac/app?component=dns-resolver&symptom=dns-resolution-failures&factor=singl"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:44:32 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:44:32.735532514Z 104.22.64.197 - - [14/Nov/2026:15:44:32 +0000] \"GET /app-ac/app?root_cause=capacity&component=dns-resolver&symptom=dns-resolution-f"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:44:33 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:44:33.866852411Z 172.70.126.46 - - [14/Nov/2026:15:44:33 +0000] \"GET /app-ac/app?component=dns-resolver&symptom=dns-resolution-failures&factor=singl"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:44:59 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:44:59.142976547Z 104.22.64.197 - - [14/Nov/2026:15:44:59 +0000] \"GET /app-ac/app?component=gke-control-plane&symptom=credentials-unavailable&factor="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:14 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:14.293022921Z 104.22.64.197 - - [14/Nov/2026:15:45:14 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&component=gke-control-plane&symptom=c"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:15 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:15.332360202Z 172.70.126.46 - - [14/Nov/2026:15:45:15 +0000] \"GET /app-ac/app/ko?component=gke-control-plane&symptom=control-plane-unresponsive&f"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:20 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:20.873507608Z 172.70.134.18 - - [14/Nov/2026:15:45:20 +0000] \"GET /app-ac/app/graph?component=gke-control-plane&symptom=control-plane-unresponsiv"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:21 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:21.276104022Z 104.23.211.29 - - [14/Nov/2026:15:45:21 +0000] \"GET /app-ac/app/ko?root_cause=certificate-expiry&symptom=control-plane-unresponsive"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:25 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:25.056382768Z 172.69.138.16 - - [14/Nov/2026:15:45:25 +0000] \"GET /app-ac/app?component=interconnect&org=slack&root_cause=cloud-provider&symptom="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:37 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:37.937710410Z 104.23.211.29 - - [14/Nov/2026:15:45:37 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&component=kube-apiserver&symptom=cont"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:42 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:42.227876624Z 172.70.134.18 - - [14/Nov/2026:15:45:42 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&symptom=credentials-unavailable&facto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:44 +<n>] \"GET /app-ac/app?root_cause=certificate-expiry&factor=single-point-of-failure&org=webhook-relay …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:44.608652441Z 172.70.134.18 - - [14/Nov/2026:15:45:44 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&factor=single-point-of-failure&org=we"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:48 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:48.787929109Z 172.70.134.18 - - [14/Nov/2026:15:45:48 +0000] \"GET /app-ac/app/graph?root_cause=certificate-expiry&symptom=control-plane-unrespons"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:53 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:53.365073558Z 104.23.211.29 - - [14/Nov/2026:15:45:53 +0000] \"GET /app-ac/app/graph?component=rbac-service-account&symptom=control-plane-unrespon"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:54 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:54.369741256Z 172.70.134.18 - - [14/Nov/2026:15:45:54 +0000] \"GET /app-ac/app?component=kube-apiserver&symptom=credentials-unavailable&factor=sin"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:55 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:55.354380252Z 104.23.211.29 - - [14/Nov/2026:15:45:55 +0000] \"GET /app-ac/app/graph?component=kube-apiserver&symptom=control-plane-unresponsive&f"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:56 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:56.335233639Z 172.70.134.18 - - [14/Nov/2026:15:45:56 +0000] \"GET /app-ac/app/ko?component=kube-apiserver&symptom=control-plane-unresponsive&fact"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:57 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:57.338730046Z 104.23.211.29 - - [14/Nov/2026:15:45:57 +0000] \"GET /app-ac/app/ko/graph?symptom=control-plane-unresponsive&factor=single-point-of-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:58 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:58.343637083Z 172.70.134.18 - - [14/Nov/2026:15:45:58 +0000] \"GET /app-ac/app/ko?symptom=credentials-unavailable&factor=single-point-of-failure&o"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:45:59 +<n>] \"GET /app-ac/app/ko?factor=single-point-of-failure&org=webhook-relay HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:45:59.403808765Z 104.23.211.29 - - [14/Nov/2026:15:45:59 +0000] \"GET /app-ac/app/ko?factor=single-point-of-failure&org=webhook-relay HTTP/2.0\" 200 1"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:46:00 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:46:00.428241491Z 172.70.134.18 - - [14/Nov/2026:15:46:00 +0000] \"GET /app-ac/app/graph?symptom=credentials-unavailable&factor=single-point-of-failur"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:46:01 +<n>] \"GET /app-ac/app/graph?factor=single-point-of-failure&org=webhook-relay HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:46:01.329289588Z 104.23.211.29 - - [14/Nov/2026:15:46:01 +0000] \"GET /app-ac/app/graph?factor=single-point-of-failure&org=webhook-relay HTTP/2.0\" 20"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:47:44 +<n>] \"GET /app-ac/app?org=stripe&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 (Macintosh; …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:47:44.200069144Z 172.70.140.252 - - [14/Nov/2026:15:47:44 +0000] \"GET /app-ac/app?org=stripe&symptom=high-error-rate HTTP/2.0\" 200 127171 \"-\" \"Mozil"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:09 +<n>] \"GET /app-ac/app?org=discord&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:09.076972492Z 104.22.182.67 - - [14/Nov/2026:15:48:09 +0000] \"GET /app-ac/app?org=discord&symptom=high-error-rate HTTP/2.0\" 200 125908 \"-\" \"Mozil"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:30 +<n>] \"GET /app-ac/app?root_cause=hardware-failure&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:30.951716831Z 172.69.138.16 - - [14/Nov/2026:15:48:30 +0000] \"GET /app-ac/app?root_cause=hardware-failure&symptom=high-error-rate HTTP/2.0\" 200 1"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/2urr6-fm2smyv.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.332114694Z 172.71.227.162 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/2urr6-fm2smyv.js HTTP/2.0\" 200 8688 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/310vm2bl3xxpt.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.332868695Z 172.71.227.172 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/310vm2bl3xxpt.js HTTP/2.0\" 200 1970 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/3gzfvbmbz4rlr.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.345146086Z 172.71.227.146 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/3gzfvbmbz4rlr.js HTTP/2.0\" 200 35889 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/turbopack-0ompzw0i7uknd.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.349481537Z 172.71.227.172 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/turbopack-0ompzw0i7uknd.js HTTP/2.0\" 200 3918 "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/41m9eb0bmovqy.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.351994442Z 172.71.227.130 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/41m9eb0bmovqy.js HTTP/2.0\" 200 14219 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/167agcgm3iqyl.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.353874375Z 172.71.227.174 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/167agcgm3iqyl.js HTTP/2.0\" 200 9571 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/16ln86kt5sdql.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.355791468Z 172.71.227.180 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/16ln86kt5sdql.js HTTP/2.0\" 200 15490 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/3mo9u585d4_v4.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.359549501Z 172.71.227.136 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/3mo9u585d4_v4.js HTTP/2.0\" 200 17473 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/0qn0l2i-7k-oi.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.366813373Z 172.71.227.166 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/0qn0l2i-7k-oi.js HTTP/2.0\" 200 11184 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/0cz1d0mv5g_q7.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.370326453Z 172.71.227.148 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/0cz1d0mv5g_q7.js HTTP/2.0\" 200 39627 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/39_j1bdzreq0m.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:34.371206421Z 172.71.227.164 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/39_j1bdzreq0m.js HTTP/2.0\" 200 71752 \"https://"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:53 +<n>] \"GET /app-ac/app/ko?symptom=cloud-api-rate-limited&factor=single-point-of-failure HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:48:53.830506017Z 172.70.134.18 - - [14/Nov/2026:15:48:53 +0000] \"GET /app-ac/app/ko?symptom=cloud-api-rate-limited&factor=single-point-of-failure HT"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:19 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:19.381799706Z 104.22.101.108 - - [14/Nov/2026:15:51:19 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=object-storage&factor=limi"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:20 +<n>] \"GET /app-ac/app?component=object-storage&symptom=training-job-failed&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:20.638158185Z 104.23.213.74 - - [14/Nov/2026:15:51:20 +0000] \"GET /app-ac/app?component=object-storage&symptom=training-job-failed&factor=limited"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:32 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=gpu-hardware&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:32.638147128Z 104.23.213.74 - - [14/Nov/2026:15:51:32 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=gpu-hardware&factor=limited"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:33 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:33.382399745Z 104.22.101.108 - - [14/Nov/2026:15:51:33 +0000] \"GET /app-ac/app?root_cause=dependency-failure&symptom=training-job-failed&factor=l"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:34 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=infiniband&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:34.433953950Z 104.23.213.74 - - [14/Nov/2026:15:51:34 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=infiniband&factor=limited-d"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:35 +<n>] \"GET /app-ac/app/graph?root_cause=dependency-failure&factor=limited-debug-access HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:35.646733516Z 104.22.101.108 - - [14/Nov/2026:15:51:35 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&factor=limited-debug-access HT"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:36 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&factor=limited-debug-access&org=meta-ai HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:36.722884788Z 104.23.213.74 - - [14/Nov/2026:15:51:36 +0000] \"GET /app-ac/app?root_cause=dependency-failure&factor=limited-debug-access&org=meta-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:41 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=nccl&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:41.360311204Z 104.22.64.197 - - [14/Nov/2026:15:51:41 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=nccl&factor=limited-debug-a"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:43 +<n>] \"GET /app-ac/app?symptom=training-job-failed&factor=limited-debug-access&org=bigscience HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:43.604203743Z 172.69.6.42 - - [14/Nov/2026:15:51:43 +0000] \"GET /app-ac/app?symptom=training-job-failed&factor=limited-debug-access&org=bigscienc"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:47 +<n>] \"GET /app-ac/app?root_cause=hardware-failure&factor=limited-debug-access&org=bigscience HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:47.430057177Z 172.69.6.42 - - [14/Nov/2026:15:51:47 +0000] \"GET /app-ac/app?root_cause=hardware-failure&factor=limited-debug-access&org=bigscienc"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:50 +<n>] \"GET /app-ac/app?component=infiniband&symptom=training-job-failed&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:50.421794219Z 104.22.64.197 - - [14/Nov/2026:15:51:50 +0000] \"GET /app-ac/app?component=infiniband&symptom=training-job-failed&factor=limited-deb"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:54 +<n>] \"GET /app-ac/app?root_cause=hardware-failure&component=nccl&factor=limited-debug-access HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:54.511092537Z 104.22.64.197 - - [14/Nov/2026:15:51:54 +0000] \"GET /app-ac/app?root_cause=hardware-failure&component=nccl&factor=limited-debug-acc"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:55 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:55.508364246Z 172.69.6.42 - - [14/Nov/2026:15:51:55 +0000] \"GET /app-ac/app?root_cause=hardware-failure&symptom=training-job-failed&factor=limite"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:56 +<n>] \"GET /app-ac/app?root_cause=hardware-failure&component=pytorch&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:56.474952678Z 104.22.64.197 - - [14/Nov/2026:15:51:56 +0000] \"GET /app-ac/app?root_cause=hardware-failure&component=pytorch&factor=limited-debug-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:57 +<n>] \"GET /app-ac/app/graph?root_cause=hardware-failure&factor=limited-debug-access HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:57.517233329Z 172.69.6.42 - - [14/Nov/2026:15:51:57 +0000] \"GET /app-ac/app/graph?root_cause=hardware-failure&factor=limited-debug-access HTTP/2."
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:51:58 +<n>] \"GET /app-ac/app?root_cause=hardware-failure&component=slurm&factor=limited-debug-access HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:51:58.497928204Z 104.22.64.197 - - [14/Nov/2026:15:51:58 +0000] \"GET /app-ac/app?root_cause=hardware-failure&component=slurm&factor=limited-debug-ac"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:00 +<n>] \"GET /app-ac/app?component=slurm&symptom=training-job-failed&factor=limited-debug-access HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:00.502132620Z 104.22.64.197 - - [14/Nov/2026:15:52:00 +0000] \"GET /app-ac/app?component=slurm&symptom=training-job-failed&factor=limited-debug-ac"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:08 +<n>] \"GET /app-ac/app?component=gpu-hardware&symptom=training-job-failed&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:08.811268881Z 172.69.6.42 - - [14/Nov/2026:15:52:08 +0000] \"GET /app-ac/app?component=gpu-hardware&symptom=training-job-failed&factor=limited-deb"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:17 +<n>] \"GET /app-ac/app?symptom=training-job-failed&factor=limited-debug-access&org=meta-ai HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:17.854516408Z 172.69.6.42 - - [14/Nov/2026:15:52:17 +0000] \"GET /app-ac/app?symptom=training-job-failed&factor=limited-debug-access&org=meta-ai H"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:21 +<n>] \"GET /app-ac/app/graph?symptom=autoscaler-scale-up-failed&factor=limited-debug-access HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:21.860577421Z 172.69.6.42 - - [14/Nov/2026:15:52:21 +0000] \"GET /app-ac/app/graph?symptom=autoscaler-scale-up-failed&factor=limited-debug-access "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:24 +<n>] \"GET /app-ac/app?component=pytorch&symptom=training-job-failed&factor=limited-debug-access …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:24.828717698Z 104.22.64.197 - - [14/Nov/2026:15:52:24 +0000] \"GET /app-ac/app?component=pytorch&symptom=training-job-failed&factor=limited-debug-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:28 +<n>] \"GET /app-ac/app/graph?symptom=training-job-failed&factor=limited-debug-access HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:28.862428956Z 104.22.64.197 - - [14/Nov/2026:15:52:28 +0000] \"GET /app-ac/app/graph?symptom=training-job-failed&factor=limited-debug-access HTTP/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:29 +<n>] \"GET /app-ac/app?component=nccl&symptom=training-job-failed&factor=limited-debug-access HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:29.926979946Z 172.69.6.42 - - [14/Nov/2026:15:52:29 +0000] \"GET /app-ac/app?component=nccl&symptom=training-job-failed&factor=limited-debug-acces"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:52:30 +<n>] \"GET /app-ac/app?symptom=training-job-failed&factor=no-spare-capacity HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:52:30.850655720Z 104.22.64.197 - - [14/Nov/2026:15:52:30 +0000] \"GET /app-ac/app?symptom=training-job-failed&factor=no-spare-capacity HTTP/2.0\" 200 "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:53:37 +<n>] \"GET /app-ac/app/graph?symptom=cloud-api-rate-limited&factor=single-point-of-failure HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:53:37.790287542Z 104.22.17.37 - - [14/Nov/2026:15:53:37 +0000] \"GET /app-ac/app/graph?symptom=cloud-api-rate-limited&factor=single-point-of-failure "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:55 +<n>] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=review-missed&org=influxdata …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:55:55.314073470Z 104.22.104.133 - - [14/Nov/2026:15:55:55 +0000] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=review-missed&o"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:55 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:55:55.927090001Z 104.22.100.134 - - [14/Nov/2026:15:55:55 +0000] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=no-safeguard-on"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:57 +<n>] \"GET /app-ac/app/ko/graph?component=argocd&symptom=high-error-rate&org=influxdata HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:55:57.973294774Z 104.22.100.134 - - [14/Nov/2026:15:55:57 +0000] \"GET /app-ac/app/ko/graph?component=argocd&symptom=high-error-rate&org=influxdata H"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:58 +<n>] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=no-runbook&org=influxdata …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:55:58.791747670Z 104.22.104.133 - - [14/Nov/2026:15:55:58 +0000] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=no-runbook&org="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:03 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:03.985436165Z 104.22.100.134 - - [14/Nov/2026:15:56:03 +0000] \"GET /app-ac/app?root_cause=config-change&component=argocd&symptom=high-error-rate&"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:07 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:07.786988064Z 104.22.104.133 - - [14/Nov/2026:15:56:07 +0000] \"GET /app-ac/app?root_cause=config-change&component=argocd&symptom=high-error-rate&"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:09 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:09.933811430Z 104.22.100.134 - - [14/Nov/2026:15:56:09 +0000] \"GET /app-ac/app?root_cause=config-change&component=argocd&symptom=high-error-rate&"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:10 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:10.837814845Z 104.22.104.133 - - [14/Nov/2026:15:56:10 +0000] \"GET /app-ac/app?root_cause=config-change&component=argocd&symptom=high-error-rate&"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:13 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:13.362697067Z 104.22.100.134 - - [14/Nov/2026:15:56:13 +0000] \"GET /app-ac/app?root_cause=config-change&component=argocd&symptom=high-error-rate&"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:14 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:14.381285542Z 104.22.104.133 - - [14/Nov/2026:15:56:14 +0000] \"GET /app-ac/app/graph?root_cause=config-change&component=argocd&symptom=high-error"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:42 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:42.272858289Z 104.22.100.134 - - [14/Nov/2026:15:56:42 +0000] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=no-safeguard"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:43 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:43.316442563Z 104.22.104.133 - - [14/Nov/2026:15:56:43 +0000] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=automation-a"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:44 +<n>] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=no-runbook&org=influxdata …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:44.315460342Z 104.22.100.134 - - [14/Nov/2026:15:56:44 +0000] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=no-runbook&o"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:45 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:45.284083594Z 104.22.104.133 - - [14/Nov/2026:15:56:45 +0000] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=review-misse"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:46 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:46.847754172Z 104.22.100.134 - - [14/Nov/2026:15:56:46 +0000] \"GET /app-ac/app/graph?component=argocd&symptom=high-error-rate&factor=monitoring-b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:53 +<n>] \"GET /app-ac/app/ko?root_cause=dependency-failure&org=yonghyun-kim HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:53.512842374Z 104.22.104.133 - - [14/Nov/2026:15:56:53 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&org=yonghyun-kim HTTP/2.0\" 200 12"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:59 +<n>] \"GET /app-ac/app/graph?root_cause=dependency-failure&org=yonghyun-kim HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:56:59.641947977Z 172.70.174.203 - - [14/Nov/2026:15:56:59 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&org=yonghyun-kim HTTP/2.0\" 200"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:57:43 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:57:43.638593144Z 172.70.174.203 - - [14/Nov/2026:15:57:43 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&symptom=service-unavailable&facto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:57:45 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:57:45.618692813Z 172.70.174.203 - - [14/Nov/2026:15:57:45 +0000] \"GET /app-ac/app?root_cause=dependency-failure&symptom=readiness-probe-failures&fac"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:57:47 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:57:47.152590873Z 172.70.174.203 - - [14/Nov/2026:15:57:47 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&symptom=service-unavailable&fa"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:21 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:21.715638645Z 104.23.245.136 - - [14/Nov/2026:15:58:21 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&symptom=servi"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:25 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:25.637857309Z 104.23.245.136 - - [14/Nov/2026:15:58:25 +0000] \"GET /app-ac/app?root_cause=dependency-failure&symptom=crash-loop&factor=blast-radi"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:33 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:33.758403220Z 104.23.245.136 - - [14/Nov/2026:15:58:33 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&symptom=service-unavailable&fa"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:37 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:37.677791794Z 104.23.245.136 - - [14/Nov/2026:15:58:37 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&component=health-probe&symptom=se"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:39 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:39.725776239Z 104.23.245.136 - - [14/Nov/2026:15:58:39 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&component=health-probe&symptom"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:45 +<n>] \"GET /app-ac/app/ko?root_cause=dependency-failure&symptom=crash-loop&org=yonghyun-kim HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:45.800792396Z 104.23.245.136 - - [14/Nov/2026:15:58:45 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&symptom=crash-loop&org=yonghyun-k"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:47 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:47.750081036Z 104.23.245.136 - - [14/Nov/2026:15:58:47 +0000] \"GET /app-ac/app/ko/graph?root_cause=dependency-failure&symptom=service-unavailable"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:51 +<n>] \"GET /app-ac/app/graph?root_cause=dependency-failure&symptom=crash-loop&org=yonghyun-kim HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:51.981460057Z 104.23.245.136 - - [14/Nov/2026:15:58:51 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&symptom=crash-loop&org=yonghyu"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:53 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:58:53.936934387Z 104.23.245.136 - - [14/Nov/2026:15:58:53 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&symptom=readiness-probe-failur"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:37 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:59:37.150329467Z 162.158.166.213 - - [14/Nov/2026:15:59:37 +0000] \"GET /app-ac/app/ko?component=managed-control-plane&symptom=high-error-rate&factor"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:48 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:59:48.134343263Z 162.158.166.213 - - [14/Nov/2026:15:59:48 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&component=managed-control-plane&sym"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:51 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T15:59:51.135700883Z 162.158.166.213 - - [14/Nov/2026:15:59:51 +0000] \"GET /app-ac/app/graph?root_cause=certificate-expiry&component=managed-control-pla"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:00 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:00.354898295Z 162.158.166.213 - - [14/Nov/2026:16:00:00 +0000] \"GET /app-ac/app?root_cause=certificate-expiry&component=cluster-autoscaler&sympto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:05 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:05.791494425Z 104.22.14.232 - - [14/Nov/2026:16:00:05 +0000] \"GET /app-ac/app/ko?component=cluster-autoscaler&symptom=high-error-rate&factor=dela"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:06 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:06.260980780Z 162.159.99.98 - - [14/Nov/2026:16:00:06 +0000] \"GET /app-ac/app/graph?component=cluster-autoscaler&symptom=high-error-rate&factor=d"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:07 +<n>] \"GET /app-ac/app/ko/graph?symptom=high-error-rate&factor=delayed-effect-change&org=linode …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:07.530171887Z 104.22.14.134 - - [14/Nov/2026:16:00:07 +0000] \"GET /app-ac/app/ko/graph?symptom=high-error-rate&factor=delayed-effect-change&org=l"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:08 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:08.438650093Z 162.159.99.98 - - [14/Nov/2026:16:00:08 +0000] \"GET /app-ac/app/ko?root_cause=certificate-expiry&symptom=high-error-rate&factor=del"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:10 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:10.351005889Z 104.22.14.232 - - [14/Nov/2026:16:00:10 +0000] \"GET /app-ac/app/graph?root_cause=certificate-expiry&symptom=high-error-rate&factor="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:11 +<n>] \"GET /app-ac/app/ko/graph?root_cause=certificate-expiry&symptom=high-error-rate&org=linode …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:11.318589306Z 162.159.99.98 - - [14/Nov/2026:16:00:11 +0000] \"GET /app-ac/app/ko/graph?root_cause=certificate-expiry&symptom=high-error-rate&org="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:14 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:14.545091620Z 162.159.99.98 - - [14/Nov/2026:16:00:14 +0000] \"GET /app-ac/app/ko?root_cause=certificate-expiry&component=cluster-autoscaler&sympt"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:17 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:17.091842454Z 104.22.14.232 - - [14/Nov/2026:16:00:17 +0000] \"GET /app-ac/app/graph?root_cause=certificate-expiry&component=cluster-autoscaler&sy"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:19 +<n>] \"GET /app-ac/app/ko/graph?component=cluster-autoscaler&symptom=high-error-rate&org=linode …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:19.970577165Z 162.159.99.98 - - [14/Nov/2026:16:00:19 +0000] \"GET /app-ac/app/ko/graph?component=cluster-autoscaler&symptom=high-error-rate&org=l"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:24 +<n>] \"GET /app-ac/app/ko?root_cause=dependency-failure&org=linode HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:24.525793033Z 104.22.14.232 - - [14/Nov/2026:16:00:24 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&org=linode HTTP/2.0\" 200 128927 \"-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:45 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&factor=limit-unknown&org=linode HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:45.556892579Z 104.22.14.232 - - [14/Nov/2026:16:00:45 +0000] \"GET /app-ac/app?root_cause=dependency-failure&factor=limit-unknown&org=linode HTTP/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:46 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=vpc-dns-resolver&org=linode HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:46.610003189Z 162.159.99.98 - - [14/Nov/2026:16:00:46 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=vpc-dns-resolver&org=linode"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:47 +<n>] \"GET /app-ac/app/graph?root_cause=dependency-failure&org=linode HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:47.603645087Z 104.22.14.232 - - [14/Nov/2026:16:00:47 +0000] \"GET /app-ac/app/graph?root_cause=dependency-failure&org=linode HTTP/2.0\" 200 125934"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:48 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=registry&org=linode HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:48.603726855Z 162.159.99.98 - - [14/Nov/2026:16:00:48 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=registry&org=linode HTTP/2."
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:00:49 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=dns-server&org=linode HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-6kgsq/controller] 2026-11-14T16:00:49.588979799Z 104.22.14.232 - - [14/Nov/2026:16:00:49 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=dns-server&org=linode HTTP/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:16:12 +<n>] \"GET /app-ac/app?component=etcd&factor=single-point-of-failure&symptom=monitoring-down HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:16:12.114520419Z 172.70.34.31 - - [14/Nov/2026:15:16:12 +0000] \"GET /app-ac/app?component=etcd&factor=single-point-of-failure&symptom=monitoring-dow"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:28:07 +<n>] \"GET /app-ac/app/ko?symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 (compatible; …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:28:07.185388615Z 172.64.209.10 - - [14/Nov/2026:15:28:07 +0000] \"GET /app-ac/app/ko?symptom=high-error-rate HTTP/2.0\" 200 248020 \"-\" \"Mozilla/5.0 (c"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:37 +<n>] \"GET /app-ac/app?component=conntrack&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:37.790354199Z 162.158.170.128 - - [14/Nov/2026:15:29:37 +0000] \"GET /app-ac/app?component=conntrack&root_cause=software-bug&symptom=high-error-ra"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:38 +<n>] \"GET /app-ac/app?after=cmFuazoxNw&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:38.218148414Z 104.22.224.130 - - [14/Nov/2026:15:29:38 +0000] \"GET /app-ac/app?after=cmFuazoxNw&root_cause=software-bug&symptom=high-error-rate H"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:38 +<n>] \"GET /app-ac/app?org=stripe&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:38.271016201Z 172.68.82.136 - - [14/Nov/2026:15:29:38 +0000] \"GET /app-ac/app?org=stripe&root_cause=software-bug&symptom=high-error-rate HTTP/2.0"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:38 +<n>] \"GET /app-ac/app?component=haproxy&root_cause=software-bug&symptom=high-error-rate HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:38.313755169Z 172.69.155.17 - - [14/Nov/2026:15:29:38 +0000] \"GET /app-ac/app?component=haproxy&root_cause=software-bug&symptom=high-error-rate H"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:41 +<n>] \"GET /app-ac/app/docs?_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:41.867448052Z 162.159.106.213 - - [14/Nov/2026:15:29:41 +0000] \"GET /app-ac/app/docs?_rsc=eqsiq HTTP/2.0\" 200 240 \"https://lab-j.example/incidentl"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:42 +<n>] \"GET /app-ac/app?root_cause=software-bug&component=linux-kernel&symptom=high-error-rate&_rsc=eqsiq …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:42.802717705Z 162.159.106.213 - - [14/Nov/2026:15:29:42 +0000] \"GET /app-ac/app?root_cause=software-bug&component=linux-kernel&symptom=high-error"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:43 +<n>] \"GET /app-ac/app?root_cause=software-bug&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:43.297171782Z 162.159.106.213 - - [14/Nov/2026:15:29:43 +0000] \"GET /app-ac/app?root_cause=software-bug&symptom=high-error-rate&_rsc=eqsiq HTTP/2"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:43 +<n>] \"GET /app-ac/app?component=conntrack&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:43.685817743Z 162.159.106.213 - - [14/Nov/2026:15:29:43 +0000] \"GET /app-ac/app?component=conntrack&symptom=high-error-rate&_rsc=eqsiq HTTP/2.0\" "
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:43 +<n>] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&symptom=node-kernel-panic&_rsc=eqsiq …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:43.732142891Z 162.159.106.217 - - [14/Nov/2026:15:29:43 +0000] \"GET /app-ac/app?root_cause=software-bug&component=conntrack&symptom=node-kernel-p"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET /app-ac/app/ko?_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:44.819336342Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app/ko?_rsc=eqsiq HTTP/2.0\" 200 225 \"https://lab-j.example/app-ac"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:44 +<n>] \"GET /app-ac/app/cases/IL-<n>?_rsc=1a28h HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:44.947615121Z 162.159.106.213 - - [14/Nov/2026:15:29:44 +0000] \"GET /app-ac/app/cases/IL-0277?_rsc=1a28h HTTP/2.0\" 200 982 \"https://lab-j.example/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:29:45 +<n>] \"GET /app-ac/app/graph?_rsc=eqsiq HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:29:45.417132117Z 162.159.106.213 - - [14/Nov/2026:15:29:45 +0000] \"GET /app-ac/app/graph?_rsc=eqsiq HTTP/2.0\" 200 236 \"https://lab-j.example/incident"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:32:23 +<n>] \"GET /app-ac/app/symptoms/autoscaler-scale-up-failed HTTP/2.0\" <n> <n> \"https://lab-j.example/\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:32:23.698270118Z 104.22.224.130 - - [14/Nov/2026:15:32:23 +0000] \"GET /app-ac/app/symptoms/autoscaler-scale-up-failed HTTP/2.0\" 200 17447 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:47:20 +<n>] \"GET /app-ac/app?org=37signals&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:47:20.348386783Z 162.158.102.24 - - [14/Nov/2026:15:47:20 +0000] \"GET /app-ac/app?org=37signals&symptom=high-error-rate HTTP/2.0\" 200 127134 \"-\" \"Mo"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:47:45 +<n>] \"GET /app-ac/app?org=spotify&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:47:45.153977222Z 104.22.10.124 - - [14/Nov/2026:15:47:45 +0000] \"GET /app-ac/app?org=spotify&symptom=high-error-rate HTTP/2.0\" 200 124788 \"-\" \"Mozil"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:47:45 +<n>] \"GET /app-ac/app?org=cloudflare&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:47:45.870186074Z 172.69.178.44 - - [14/Nov/2026:15:47:45 +0000] \"GET /app-ac/app?org=cloudflare&symptom=high-error-rate HTTP/2.0\" 200 145713 \"-\" \"Mo"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:47:59 +<n>] \"GET /app-ac/app/ko?symptom=autoscaler-scale-up-failed&factor=limited-debug-access HTTP/2.0\" <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:47:59.834094129Z 162.159.104.132 - - [14/Nov/2026:15:47:59 +0000] \"GET /app-ac/app/ko?symptom=autoscaler-scale-up-failed&factor=limited-debug-access"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:03 +<n>] \"GET /app-ac/app/ko?symptom=training-job-failed&factor=limited-debug-access HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:03.807696329Z 162.159.104.132 - - [14/Nov/2026:15:48:03 +0000] \"GET /app-ac/app/ko?symptom=training-job-failed&factor=limited-debug-access HTTP/2"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:07 +<n>] \"GET /app-ac/app?component=database-proxy&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:07.233985119Z 172.71.124.210 - - [14/Nov/2026:15:48:07 +0000] \"GET /app-ac/app?component=database-proxy&symptom=high-error-rate HTTP/2.0\" 200 139"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:09 +<n>] \"GET /app-ac/app/ko?root_cause=dependency-failure&factor=limited-debug-access HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:09.192057519Z 172.71.167.178 - - [14/Nov/2026:15:48:09 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&factor=limited-debug-access HTTP/"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:20 +<n>] \"GET /app-ac/app/ko?root_cause=hardware-failure&factor=limited-debug-access HTTP/2.0\" <n> <n> \"-\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:20.764473147Z 172.71.167.178 - - [14/Nov/2026:15:48:20 +0000] \"GET /app-ac/app/ko?root_cause=hardware-failure&factor=limited-debug-access HTTP/2."
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/3yll8w3l1pmeb.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:34.355863834Z 172.71.227.132 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/3yll8w3l1pmeb.js HTTP/2.0\" 200 2782 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/3zt_16xndew4w.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:34.360217130Z 172.71.227.140 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/3zt_16xndew4w.js HTTP/2.0\" 200 3302 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/3rmej2m0vkll4.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:34.362476859Z 172.71.227.152 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/3rmej2m0vkll4.js HTTP/2.0\" 200 9961 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:48:34 +<n>] \"GET /app-ac/app/_next/static/chunks/1xuuz1nta_f1t.js HTTP/2.0\" <n> <n> …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:48:34.371888647Z 172.71.227.150 - - [14/Nov/2026:15:48:34 +0000] \"GET /app-ac/app/_next/static/chunks/1xuuz1nta_f1t.js HTTP/2.0\" 200 4895 \"https://b"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:49:41 +<n>] \"GET /app-ac/app?after=cmFuazo1NQ&symptom=high-error-rate HTTP/2.0\" <n> <n> \"-\" \"Mozilla/5.0 …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:49:41.910539819Z 104.22.10.124 - - [14/Nov/2026:15:49:41 +0000] \"GET /app-ac/app?after=cmFuazo1NQ&symptom=high-error-rate HTTP/2.0\" 200 229841 \"-\" \""
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:55:19 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:55:19.784447581Z 172.68.27.67 - - [14/Nov/2026:15:55:19 +0000] \"GET /app-ac/app/ko?component=argocd&symptom=high-error-rate&factor=automation-amplif"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:56:59 +<n>] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&org=yonghyun-kim HTTP/2.0\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:56:59.819415262Z 104.23.209.169 - - [14/Nov/2026:15:56:59 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&org=yonghyun-"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:57:39 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:57:39.624555748Z 104.23.209.169 - - [14/Nov/2026:15:57:39 +0000] \"GET /app-ac/app?root_cause=dependency-failure&symptom=crash-loop&factor=automation"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:57:44 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:57:44.884449380Z 104.23.209.169 - - [14/Nov/2026:15:57:44 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&symptom=servi"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:30 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:58:30.695092136Z 104.22.24.86 - - [14/Nov/2026:15:58:30 +0000] \"GET /app-ac/app?root_cause=dependency-failure&symptom=readiness-probe-failures&facto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:32 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:58:32.632439034Z 104.22.24.86 - - [14/Nov/2026:15:58:32 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&symptom=service-unavailable&factor="
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:38 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:58:38.721035235Z 104.22.24.86 - - [14/Nov/2026:15:58:38 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&symptom=crash-l"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:40 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:58:40.751735698Z 104.22.24.86 - - [14/Nov/2026:15:58:40 +0000] \"GET /app-ac/app?root_cause=dependency-failure&component=health-probe&symptom=readine"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:58:44 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:58:44.857259617Z 104.22.24.86 - - [14/Nov/2026:15:58:44 +0000] \"GET /app-ac/app/ko?root_cause=dependency-failure&symptom=readiness-probe-failures&or"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:36 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:59:36.281651499Z 172.69.135.52 - - [14/Nov/2026:15:59:36 +0000] \"GET /app-ac/app/ko?root_cause=certificate-expiry&component=managed-control-plane&sy"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:38 +<n>] \"GET /app-ac/app/ko/graph?component=managed-control-plane&symptom=high-error-rate&org=linode …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:59:38.515816787Z 172.69.135.52 - - [14/Nov/2026:15:59:38 +0000] \"GET /app-ac/app/ko/graph?component=managed-control-plane&symptom=high-error-rate&or"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:15:59:47 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T15:59:47.643322264Z 172.69.135.52 - - [14/Nov/2026:15:59:47 +0000] \"GET /app-ac/app/graph?component=managed-control-plane&symptom=high-error-rate&facto"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:01:32 +<n>] \"GET /app-ac/app/factors/single-point-of-failure HTTP/2.0\" <n> <n> \"https://lab-j.example/\" …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T16:01:32.811550363Z 162.158.163.209 - - [14/Nov/2026:16:01:32 +0000] \"GET /app-ac/app/factors/single-point-of-failure HTTP/2.0\" 200 33564 \"https://benc"
  },
  {
   "pattern": "ingress-nginx | <ip> - - [14/Nov/<n>:16:03:25 +<n>] \"GET …",
   "count": 1,
   "files": {
    "logs/pods/ingress-nginx/ingress-nginx_nginx-ingress-ingress-nginx-controller.log": 1
   },
   "sample": "[pod/nginx-ingress-ingress-nginx-controller-86f8b99dfd-lkdwm/controller] 2026-11-14T16:03:25.382388807Z 172.70.111.159 - - [14/Nov/2026:16:03:25 +0000] \"GET /app-ac/app?root_cause=software-bug&component=persistent-volume&symptom=data-l"
  },
  {
   "pattern": "metrics-server | \"Failed probe\" probe=\"metric-storage-ready\" err=\"no metrics to serve\"",
   "count": 1,
   "files": {
    "logs/pods/metrics-server/kube-system_metrics-server.log": 1
   },
   "sample": "[pod/metrics-server-7bfffcd44-fkpfm/metrics-server] 2026-11-14T01:13:02.026413969Z I1114 01:13:02.026346       1 server.go:192] \"Failed probe\" probe=\"metric-storage-ready\" err=\"no metrics to serve\""
  },
  {
   "pattern": "tempo-jaeger | level=error ts=<ts> caller=poller.go:<n> msg=\"failed to poll or create index for tenant\" tenant=single-tenant err=\"failed to poll tenant …",
   "count": 1,
   "files": {
    "logs/pods/tempo-jaeger/monitoring_tempo.log": 1
   },
   "sample": "[pod/tempo-0/tempo] 2026-11-14T13:53:17.167872801Z level=error ts=2026-11-14T13:53:17.167809702Z caller=poller.go:215 msg=\"failed to poll or create index for tenant\" tenant=single-tenant err=\"failed to poll tenant blocks: failed listing ten"
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
  "path": "pg_isready -U app-a",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-a",
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
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
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
  "path": "pg_isready -U damta",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U damta",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
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
  "path": "redis-cli ping",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "redis-cli ping",
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
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
  "path": "mysqladmin ping -h localhost",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "mysqladmin ping -h localhost",
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
<details><summary><code>resilience.exec-probe.app-ac-prod/statefulset/app-ac-postgres:postgres</code></summary>

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
  "path": "pg_isready -U app-ac",
  "port": null,
  "timeout_s": 1,
  "period_s": 15,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-ac",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "workload": "app-ac-prod/statefulset/app-ac-postgres"
}
```

</details>
<details><summary><code>resilience.exec-probe.app-ac-prod/statefulset/app-ac-redis:redis</code></summary>

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
  "path": "sh -c redis-cli ping | grep -q PONG",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 10
 },
 "readiness": {
  "type": "exec",
  "path": "sh -c redis-cli ping | grep -q PONG",
  "port": null,
  "timeout_s": 1,
  "period_s": 5,
  "failure_threshold": 3,
  "initial_delay_s": 5
 },
 "workload": "app-ac-prod/statefulset/app-ac-redis"
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
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
  "port": null,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "/bin/sh -c pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"",
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
  "path": "pg_isready -U platform_admin -d platform_admin",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U platform_admin -d platform_admin",
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
  "path": "pg_isready -U app-l -d app-l",
  "port": null,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "readiness": {
  "type": "exec",
  "path": "pg_isready -U app-l -d app-l",
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
<details><summary><code>resilience.finished-jobs-accumulating.cluster</code></summary>

```json
{
 "failed": 1,
 "failed_pods": 3,
 "finished_without_ttl": 57,
 "succeeded_pods": 35,
 "total": 60
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
<details><summary><code>resilience.liveness-dependency-path.app-ac-prod/statefulset/app-ac-opensearch:opensearch</code></summary>

```json
{
 "container": "opensearch",
 "dependency_liveness": false,
 "flags": [
  "liveness and readiness share the same path (/_cluster/health) — a dependency outage becomes a restart loop",
  "DB container liveness timeout 1s (a 1s fsync/checkpoint stall restarts the DB → recovery loop)"
 ],
 "liveness": {
  "type": "httpGet",
  "path": "/_cluster/health",
  "port": 9200,
  "timeout_s": 1,
  "period_s": 20,
  "failure_threshold": 3,
  "initial_delay_s": 90
 },
 "prod": true,
 "readiness": {
  "type": "httpGet",
  "path": "/_cluster/health",
  "port": 9200,
  "timeout_s": 1,
  "period_s": 10,
  "failure_threshold": 3,
  "initial_delay_s": 30
 },
 "same_path": true,
 "serves_traffic": true,
 "startup": null,
 "workload": "app-ac-prod/statefulset/app-ac-opensearch"
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
<details><summary><code>resilience.no-prestop.app-h-prod/app-h-app-p</code></summary>

```json
{
 "namespace": "app-h-prod",
 "name": "app-h-app-p",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-ai</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-api</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-istio</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-istio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-mcp</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-mcp",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-projector</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-projector",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>resilience.no-prestop.app-ac-prod/app-ac-web</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-web",
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
  "memory_request_p95_ratio_7d": 0.209564208984375,
  "memory_p95_7d_bytes": 56254464.0,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.app-ac-prod/sts/app-ac-postgres:postgres</code></summary>

```json
{
 "labels": {
  "namespace": "app-ac-prod",
  "pod": "app-ac-postgres-0",
  "container": "postgres"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.2874801635742187,
  "memory_p95_7d_bytes": 77169868.79999998,
  "container_memory_request_bytes": 268435456.0
 }
}
```

</details>
<details><summary><code>resources.memory-request-overprovisioned.istio-system/deploy/istiod:discovery</code></summary>

```json
{
 "labels": {
  "namespace": "istio-system",
  "pod": "istiod-6f6d996c58-ggwp2",
  "container": "discovery"
 },
 "values": {
  "memory_request_p95_ratio_7d": 0.1779003143310547,
  "memory_p95_7d_bytes": 95509504.0,
  "container_memory_request_bytes": 536870912.0
 }
}
```

</details>
<details><summary><code>scaling.hpa-cpu-only-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "cpu_only": true,
 "current_cpu_utilization": 3,
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
 "current_cpu_utilization": 12,
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
<details><summary><code>scaling.hpa-never-scaled.istio-system/deployment/istiod</code></summary>

```json
{
 "at_min_ratio_15d": 1.0,
 "current_cpu_utilization": 1,
 "days_since_last_scale": null,
 "keda_owned": false,
 "max": 5,
 "metric_types": [
  "cpu"
 ],
 "min": 1,
 "name": "istiod",
 "namespace": "istio-system",
 "never_scaled_15d": true,
 "prod": false,
 "target": "istio-system/deployment/istiod",
 "target_cpu_utilization": 80
}
```

</details>
<details><summary><code>scaling.hpa-no-behavior-prod.app-a-prod/deployment/app-a-backend</code></summary>

```json
{
 "desired_changes_7d": 1.0,
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
 "desired_changes_7d": 4.0,
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
<details><summary><code>storage.local-path-node-pinned.cluster</code></summary>

```json
{
 "by_node": {
  "node-a": 14,
  "node-b": 24
 },
 "node_total_mb": {
  "node-a": null,
  "node-b": null
 },
 "pinned": [
  {
   "pv": "pvc-104d7c05-194e-4ffd-adda-7c6a19d1620e",
   "namespace": "app-g-api",
   "pvc": "app-g-postgres-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-g-api/app-g-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-123d97df-e04a-495f-9283-69147d9a8679",
   "namespace": "app-k",
   "pvc": "app-k-postgres-data",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-k/app-k-postgres"
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
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "registry/registry-0",
    "registry/registry-gc"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-228da581-f434-4f84-ba50-d91df7133690",
   "namespace": "app-g-api",
   "pvc": "app-g-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-g-api/app-g-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-291c9301-e481-4b69-9234-bb77f18d6faf",
   "namespace": "app-l-prod",
   "pvc": "app-l-postgres-data",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-l-prod/app-l-postgres"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-378c5351-e088-4317-9671-7f05346e9531",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-mx-backup-pvc",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-mx-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-449bc551-0e92-441c-9f9f-9c069efca0c7",
   "namespace": "app-ac-prod",
   "pvc": "data-app-ac-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-ac-prod/app-ac-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-4a73f987-9759-4cfe-9d4c-d3b672e20847",
   "namespace": "app-ac-prod",
   "pvc": "app-ac-ai-models",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 15360,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-ac-prod/app-ac-ai"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-4a98fd0d-2d0d-43d6-9652-78e0181f6632",
   "namespace": "monitoring",
   "pvc": "data-tempo-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "monitoring/tempo-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-4ce85409-5052-4afb-8c7c-fa0a912f7e09",
   "namespace": "app-i-prod",
   "pvc": "app-i-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-i-prod/app-i-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-51f46ef0-5ef3-4879-86c6-dffb5fed8ac0",
   "namespace": "app-ac-prod",
   "pvc": "data-app-ac-opensearch-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-ac-prod/app-ac-opensearch-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-527a0666-8b34-4a7b-90ad-9021acfe8c51",
   "namespace": "app-ac-prod",
   "pvc": "data-app-ac-neo4j-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-ac-prod/app-ac-neo4j-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-577a8c2b-efa5-4d04-8def-695ebf1a7780",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-5bef8ef5-dc76-48cf-8642-05c4099a8d95",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-vn-data-app-f-postgres-vn-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-vn-0"
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
   "used_mb": null,
   "used_ratio": null,
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
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-a-prod/app-a-redis-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-76170548-ef10-4112-9aaf-5332ae1eeeaa",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-vn-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-vn-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-76f7091e-04fe-4abb-98b6-e814163b9ee6",
   "namespace": "app-h-prod",
   "pvc": "app-h-qdrant-data-app-h-qdrant-0",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-h-prod/app-h-qdrant-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-8548aa25-05f2-4388-8c7e-872d080f2a0c",
   "namespace": "default",
   "pvc": "data-app-ah-db-0",
   "node": "node-b",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [],
   "phase": "Bound"
  },
  {
   "pv": "pvc-8729556f-dbf5-40ce-a48b-57eb4e27edc6",
   "namespace": "app-i-prod",
   "pvc": "app-i-postgres-data-app-i-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 30720,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-i-prod/app-i-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-88ebc552-2d81-4a82-a0f3-e2880ff9726c",
   "namespace": "app-ac-prod",
   "pvc": "data-app-ac-redis-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 2048,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-ac-prod/app-ac-redis-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-9d51b8ad-9c71-469f-957c-949fe5e00b9e",
   "namespace": "app-i-prod",
   "pvc": "app-i-postgres-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-i-prod/app-i-postgres-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-9fad0f20-f5fa-49ff-89f8-af0aaf8d55bd",
   "namespace": "app-f-prod",
   "pvc": "app-f-redis-data-app-f-redis-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 1024,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-redis-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-a9a03cde-f245-4987-b4b8-e61763da9993",
   "namespace": "app-h-prod",
   "pvc": "mysql-backup-app-h-mysql-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-h-prod/app-h-mysql-0",
    "app-h-prod/app-h-mysql-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-b1675e87-c0b0-474a-ad0a-20715dbb3dff",
   "namespace": "app-h-prod",
   "pvc": "app-h-mysql-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-h-prod/app-h-mysql-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-b31ee6ea-3238-4ecc-a34d-877a14177ad5",
   "namespace": "app-g-api",
   "pvc": "app-g-minio-data-app-g-minio-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 51200,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-g-api/app-g-minio-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-b6f729e1-b443-4ed2-866f-8fc9825078ae",
   "namespace": "app-g-api",
   "pvc": "app-g-postgres-data-app-g-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-g-api/app-g-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-c57619eb-bdde-45d0-b9c0-0845856203af",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-mx-data-app-f-postgres-mx-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-mx-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-c66c539e-96b8-4cb2-ba16-90df9d05a84f",
   "namespace": "app-l-prod",
   "pvc": "app-l-artifacts",
   "node": "node-a",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-l-prod/app-l-api"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-ca88c78c-e3bb-4de5-92e3-6e237ee7fd12",
   "namespace": "kube-system",
   "pvc": "etcd-snapshot-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "kube-system/etcd-snapshot-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-cfc6cc02-2095-4abc-b14c-76b9f555ce94",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-vn-backup-node-a-pvc",
   "node": "node-a",
   "storage_class": "local-path",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-vn-backup"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-d15ad7cd-aea4-482d-8b3e-f0386a4f73a1",
   "namespace": "app-h-prod",
   "pvc": "mysql-data-app-h-mysql-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 20480,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-h-prod/app-h-mysql-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-d3dc33a5-26ca-4c1a-a9e7-526e2c0a0e7a",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-data-app-f-postgres-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 10240,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-0"
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
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-a-prod/app-a-postgres-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-db50eb33-8393-45cd-93b3-042e019e1186",
   "namespace": "logging",
   "pvc": "data-elasticsearch-0",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 20480,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "logging/elasticsearch-0"
   ],
   "phase": "Bound"
  },
  {
   "pv": "pvc-e8064a22-b689-4d23-adef-de705d889c95",
   "namespace": "app-f-prod",
   "pvc": "app-f-postgres-backup-pvc",
   "node": "node-b",
   "storage_class": "local-path-node-b",
   "capacity_mb": 5120,
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-f-prod/app-f-postgres-backup"
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
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-c-prod/app-c-postgres-0"
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
   "used_mb": null,
   "used_ratio": null,
   "workloads": [
    "app-a-prod/app-a-postgres-backup"
   ],
   "phase": "Bound"
  }
 ],
 "pv_count": 38
}
```

</details>
<details><summary><code>storage.local-path-prod-delete-reclaim.cluster</code></summary>

```json
{
 "default_class": "local-path",
 "prod_pvs": 28,
 "prod_pvs_delete_reclaim": [
  "app-f-prod/app-f-postgres-backup-node-a-pvc",
  "app-i-prod/app-i-postgres-backup-node-a-pvc",
  "app-h-prod/app-h-mysql-backup-node-a-pvc",
  "app-f-prod/app-f-postgres-vn-backup-node-a-pvc"
 ],
 "reclaim_policies": {
  "local-path": "Delete",
  "local-path-node-b": "Delete"
 }
}
```

</details>
<details><summary><code>tenancy.ci-shares-prod-nodes.node-a</code></summary>

```json
{
 "ci_heavy": true,
 "ci_pod_list": [
  {
   "pod": "lab-a-runner-g55w4-288vf",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  },
  {
   "pod": "lab-a-runner-g55w4-gnkcc",
   "namespace": "arc-systems",
   "owner_kind": "Runner",
   "cpu_request": 0.5,
   "heavy": true
  }
 ],
 "ci_pods": 2,
 "cpu_saturated_minutes_7d": 65.0,
 "memory_limit_overcommit": 0.99,
 "node": "node-a",
 "pool": "(no-pool)",
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-h-prod",
  "app-ac-prod",
  "app-l-prod"
 ],
 "prod_pods": 15,
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
   "pod": "arc-actions-runner-controller-6cd54f9566-vxmrc",
   "namespace": "arc-systems",
   "owner_kind": "ReplicaSet",
   "cpu_request": 0.0,
   "heavy": true
  }
 ],
 "ci_pods": 1,
 "cpu_saturated_minutes_7d": 0.0,
 "memory_limit_overcommit": 1.66,
 "node": "node-b",
 "pool": "(no-pool)",
 "prod_namespaces": [
  "app-a-prod",
  "app-b-prod",
  "app-c-prod",
  "app-f-prod",
  "app-h-prod",
  "app-ac-prod",
  "app-i-prod",
  "app-l-prod"
 ],
 "prod_pods": 39,
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
  "persistentvolumeclaims": "4",
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
<details><summary><code>traffic.flannel-node-data-missing.cluster</code></summary>

```json
{
 "metrics_available": true,
 "nodes": 2,
 "nodes_missing_data": [],
 "nodes_with_data": []
}
```

</details>
<details><summary><code>traffic.lb-external-traffic-local.loadbalancer/ingress-nginx/nginx-ingress-ingress-nginx-controller</code></summary>

```json
{
 "external_traffic_policy": "Local",
 "hosts": [
  "<ip>"
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
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-ai</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-ai",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-api</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-api",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-istio</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-istio",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-mcp</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-mcp",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-projector</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-projector",
 "kind": "Deployment"
}
```

</details>
<details><summary><code>scaling.no-hpa-serving-prod.app-ac-prod/app-ac-web</code></summary>

```json
{
 "namespace": "app-ac-prod",
 "name": "app-ac-web",
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

### 7-6. Tool notes (about kubegap itself)

1. observability.alertmanager-notification-failed names the target `slack` after the integration while the receivers are called discord and discord-critical; the evidence explains it, but the target name alone reads as if a Slack receiver existed.
2. full-en.md asks to give the repository named by the `declared in` line, but assemble refuses that address because no learn topic carries it; the repository was written as owner/name without the URL.

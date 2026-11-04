# Facts read from other projects' sources

Every fact about another program that kubegap relies on, with where kubegap relies on it and the line of the project's source that states it, at the version kubegap pins in `lib/tools.py` (or supports). `references/development.md` says why: a sentence written from `--help`, from one cluster or from memory has already been wrong in this repository. `tests/test_sources.py` checks that every row has a `file:line@version` citation and that the kubegap location exists.

How to read a row: *Fact* is what kubegap assumes; *kubegap* is the function, step or check that assumes it; *Source* is the file and line at the tag, as `path:line@tag`; *Holds for* says which other versions were checked. A fact that could not be found in source is marked **unverified** with the reason. "Observed" in a row means it was also seen in a real run; a fact marked only observed is not verified.

Sources are fetched with `curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/<tag>/<path>` into a scratch folder that is never executed.

## Tool output files (`type: tool` steps of `collectors/core/collect.yaml`, issue #119)

### krr (robusta-dev/krr, tag `v1.31.1`)

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| `-c/--context`, `-p/--prometheus-url`, `-f/--formatter`, `-q/--quiet`, `--logtostderr`, `--fileoutput`, `--max-workers` exist | step `core.krr` | `robusta_krr/main.py:78-80, 113-114, 249-250, 269-270, 272-273, 282-283, 217-218@v1.31.1` | v1.31.1 |
| `--fileoutput <path>` writes the formatted result to that file (the step uses `writes_out`) | step `core.krr` | `robusta_krr/core/runner.py:121-135@v1.31.1` | v1.31.1 |
| `-f json` is `Result.json(indent=2)` | `lib/resources.py:analyze_krr` | `robusta_krr/formatters/json.py:5-7@v1.31.1` | v1.31.1 |
| Top level: `scans[]`, `score`, `resources`, `description`, `strategy{name, settings}`, `errors[]`, `clusterSummary{}`, `config{}` | `analyze_krr` | `robusta_krr/core/models/result.py:62-70@v1.31.1` | v1.31.1 |
| A scan is `{object, recommended, severity}`; `recommended` is `{requests{cpu, memory}, limits{cpu, memory}, info{cpu, memory}}` and each entry `{value, severity}` | `analyze_krr` | `result.py:14-28@v1.31.1` | v1.31.1 |
| `object` is `{cluster, name, container, pods[{name, deleted}], hpa, namespace, kind, allocations{requests, limits, info}, warnings[], labels, annotations}` | `analyze_krr` (pods_live, hpa, warnings) | `robusta_krr/core/models/objects.py:48-60, 24-26@v1.31.1` | v1.31.1 |
| `kind` is one of Deployment, DaemonSet, StatefulSet, Job, CronJob, Rollout, DeploymentConfig, StrimziPodSet, GroupedJob | check `resources.krr-recommendation` (excludes Job and CronJob) | `objects.py:11-21@v1.31.1` | v1.31.1 |
| A value is a float, the string `"?"` or null (`_num` keeps only the float) | `analyze_krr` `_num` | `robusta_krr/core/models/allocations.py:23@v1.31.1` | v1.31.1 |
| Severity is one of UNKNOWN, GOOD, OK, WARNING, CRITICAL | `analyze_krr` SEV_ORDER | `robusta_krr/core/models/severity.py:17-21@v1.31.1` | v1.31.1 |
| CPU severity by absolute difference: ≥ 0.5 cores CRITICAL, ≥ 0.25 WARNING, ≥ 0.1 OK, else GOOD; memory: ≥ 500 MiB CRITICAL, ≥ 250 WARNING, ≥ 100 OK; one side missing → WARNING, both missing → GOOD; `"?"` on either side → UNKNOWN. The same rule for limits and requests, which is why kubegap keeps its own `kubegap_level` | `analyze_krr` (comment on kubegap_level) | `severity.py:34-40, 93-130@v1.31.1` | v1.31.1 |
| `score` = (scans − CRITICAL·1 − WARNING·0.7) / scans · 100, 0 with no scans | `analyze_krr` (score) | `result.py:90-101@v1.31.1` | v1.31.1 |
| simple strategy: CPU request = the `cpu_percentile` (95) percentile, CPU limit unset, memory request = limit = max + `memory_buffer_percentage` (15) %; `history_duration` is in hours (336 = 14 days), `timeframe_duration` in minutes | `analyze_krr` docstring, history_hours | `robusta_krr/strategies/simple.py:28-34, 93-98, 138, 181@v1.31.1`; `robusta_krr/core/abstract/strategies.py:47-50@v1.31.1` (the hour and minute defaults) | v1.31.1 |
| `config` is krr's full Config: `kubeconfig`, `prometheus_url`, `file_output`, the EKS fields; `eks_access_key` is a plain `str`, while `prometheus_auth_header`, `prometheus_other_headers`, `eks_secret_key` and `coralogix_token` are `SecretStr` and serialise masked. kubegap drops the key after the run | `lib/collect.py:_run_tool_step` | `result.py:70@v1.31.1`; `robusta_krr/core/models/config.py:27, 39-52, 87@v1.31.1` | v1.31.1 |
| `krr version` prints `__version__`, which is `"dev"` in the tagged source (a release build patches it), and then `git describe --tags` of the current directory | `lib/tools.py:tool_version` (runs the probe outside the repository and reports the install tag) | `robusta_krr/__init__.py:3@v1.31.1`; `robusta_krr/utils/version.py:13-24@v1.31.1`; `pyproject.toml:3@v1.31.1` (`1.8.2-dev`) | v1.31.1; observed: inside this repository it printed kubegap's own tag |

### polaris (FairwindsOps/polaris, tag `v10.2.6`)

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| `--context/-x` is a root flag and `--format/-f json` an audit flag; no flag of either command is a kubeconfig path (the loader reads `KUBECONFIG`, #104) | step `core.polaris` | `cmd/polaris/root.go:45-52@v10.2.6`; `cmd/polaris/audit.go:56-72@v10.2.6` | v10.2.6 |
| Exit code 0 unless `--set-exit-code-on-danger` (3) or `--set-exit-code-below-score` (4) | step `core.polaris` | `audit.go:57, 59, 127-134@v10.2.6` | v10.2.6 |
| Top level `{PolarisOutputVersion, AuditTime, SourceType, SourceName, DisplayName, ClusterInfo{Version, Nodes, Pods, Namespaces, Controllers}, Results[], Score}` | `lib/hygiene.py:_polaris` | `pkg/validator/output.go:45-54, 95-101@v10.2.6` | v10.2.6 |
| A result is `{Name, Namespace, Kind, Results, PodResult, CreatedTime}`; `PodResult` is `{Name, Results, ContainerResults[{Name, Results}]}` or null; `Results` maps check id → `{ID, Message, Details, Success, Severity, Category, Mutations}` | `_polaris` `take()` | `output.go:151-158, 188-192, 222-225, 104-115@v10.2.6` | v10.2.6 |
| Severity values: `ignore`, `warning`, `danger` | `_polaris` (danger/warning counts), checks `hygiene.polaris-reliability-danger`, `security.polaris-security-danger` | `pkg/config/severity.go:22-28@v10.2.6` | v10.2.6 |
| Categories of the 44 built-in checks: Security 27, Reliability 13, Efficiency 4 (`SECURITY_CATEGORY = "Security"`) | `_polaris`, `lib/security.py` | `pkg/config/checks/runAsRootAllowed.yaml:3@v10.2.6` and the `category:` line of the other 43 check files | v10.2.6 |
| `Score` = successes·2 / (successes·2 + warnings + dangers·2) · 100, computed over every check before the output filter | `_polaris` (score) | `pkg/validator/summary.go:35-42@v10.2.6`; `pkg/validator/fullaudit.go:59@v10.2.6`; `audit.go:119-125@v10.2.6` | v10.2.6 |
| `--only-show-failed-tests` removes successful checks and then every object whose result set is empty, and for a controller it looks only at `PodResult`, so a controller whose only failures are controller-level checks (missingPodDisruptionBudget, deploymentMissingReplicas …) disappears. kubegap does not pass the flag and skips `Success: true` itself; `len(Results)` is then every audited object of any kind and `ClusterInfo.Controllers` the audited controllers | step `core.polaris`, `_polaris` (audited, with_failures, controllers) | `output.go:77-91, 160-186@v10.2.6`; `pkg/validator/schema.go:245-249@v10.2.6` (every controller gets a PodResult); `pkg/validator/fullaudit.go:55@v10.2.6` | v10.2.6; observed with the flag: `Results` (131, 160) exceeded `Controllers` (113, 93) on the two clusters |

### pluto (FairwindsOps/pluto, tag `v5.24.5`)

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| `--kube-context`, `-o/--output`, `-t/--target-versions`, `--ignore-deprecations`, `--ignore-removals`, `--ignore-unavailable-replacements` exist; `-v` is klog's flag added to the root command | step `core.pluto` | `cmd/root.go:109, 94, 93, 87-89, 119-120@v5.24.5` | v5.24.5; observed: `-v=2` accepted after the subcommand |
| Exit 2 with deprecations, 3 with removals, 4 with unavailable replacements unless the `--ignore-*` flag is set; the flags do not filter the items | step `core.pluto` (#131) | `pkg/api/output.go:333-341, 159-181@v5.24.5`; `cmd/root.go:353, 167@v5.24.5` | v5.24.5; observed on `detect-files` |
| Top level `{items[], target-versions{}}`, both `omitempty`: nothing deprecated means no `items` key | `lib/hygiene.py:_deprecated` | `pkg/api/output.go:57-66@v5.24.5` | v5.24.5; observed on both clusters |
| An item is `{name, filePath, namespace (omitempty), api{version, kind, deprecated-in, removed-in, replacement-api, replacement-available-in, component}, deprecated, removed, replacementAvailable}`; `deprecated`/`removed` are judged against the target | `_deprecated` | `output.go:28-55, 162-163@v5.24.5`; `pkg/api/versions.go:60-76@v5.24.5` | v5.24.5 |
| In-cluster detection reads only objects carrying the `kubectl.kubernetes.io/last-applied-configuration` annotation; a List that fails is skipped silently; an empty List logs `No annotations for ResourceVer` at `-v=2`; `Result from resources` is always 0 | `lib/collect.py:_run_tool_step` (api_read, #131) | `pkg/discovery-api/discovery_api.go:107-168@v5.24.5` | v5.24.5 |
| `detect-all-in-cluster` also runs the Helm detection, which lists release Secrets | step comment | `cmd/root.go:358-368@v5.24.5` | v5.24.5 |

### kubent (doitintl/kube-no-trouble, tag `0.7.3`)

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| `-x/--context`, `-o/--output json`, `-t/--target-version`, `--helm3`, `-l/--log-level` exist; the default log level is Info | step `core.kubent` | `pkg/config/config.go:38, 45, 48, 51, 53, 54@0.7.3` | 0.7.3 |
| `-o json` is `json.Encoder.Encode([]judge.Result)`: an empty result prints `[]` | `lib/hygiene.py:_deprecated` | `pkg/printer/json.go:32-40@0.7.3` | 0.7.3; observed on both clusters |
| A result is `{Name, Namespace, Kind, ApiVersion, RuleSet, ReplaceWith, Since}`; `Since` serialises as text with three segments (`1.21.0`: the wrapped hashicorp go-version pads the string), empty when nil | `_deprecated` | `pkg/judge/judge.go:3-11@0.7.3`; `pkg/judge/version.go:12-14, 24-29@0.7.3`; go-version `version.go:83-85, 384-401@v1.7.0` (kubent `go.mod:7`) | 0.7.3 |
| `Since` is the minor in which the API was deprecated; the removal minor is only in the `RuleSet` text (`Deprecated APIs removed in 1.25`, or `Deprecated APIs to be removed in future`) | `_deprecated` (removed_in, removed) | `pkg/rules/rego/deprecated-1-25.rego:13-33@0.7.3` (PodDisruptionBudget policy/v1beta1: `since 1.21` in the 1.25 rule set); `deprecated-future.rego:13@0.7.3` | 0.7.3 |
| `-t` keeps the results whose `Since` ≤ target, and those without a `Since` | `_deprecated` | `pkg/printer/filter.go:7-21@0.7.3` | 0.7.3 |
| The rules write `"<undefined>"` for a missing name or namespace (so for every cluster-scoped object) and `"<removed>"` for an API with no successor | `_deprecated` (maps the three to null) | `pkg/rules/rego/deprecated-1-25.rego:7-9, 34-37@0.7.3` (every rule set has the same head); `pkg/judge/rego.go:61-64@0.7.3` is only the fallback | 0.7.3 |
| The cluster collector lists 40 resource types and keeps only objects with a `last-applied-configuration` annotation; a failed List is logged at Debug and skipped; the Info line `Retrieved N resources from collector name=Cluster` follows; an init failure logs `Failed to initialize collector` and the run still exits 0 | `lib/collect.py:_run_tool_step` (api_read, #131) | `pkg/collector/cluster.go:119-142@0.7.3`; `cmd/kubent/main.go:49-56, 180@0.7.3` | 0.7.3; observed |
| Logs go to stderr through zerolog's ConsoleWriter with colours (`\x1b[36mname=\x1b[0mCluster`) | `_run_tool_step` (strips SGR) | `cmd/kubent/main.go:180@0.7.3` | 0.7.3; observed |
| Exit 0 even with findings unless `-e/--exit-error`; 100 when a collector fails to retrieve | step `core.kubent` | `pkg/config/config.go:46@0.7.3`; `cmd/kubent/main.go:30-34, 128, 164-167@0.7.3` | 0.7.3 |

### helm (helm/helm, tag `v4.3.1`; compared with `v3.22.1`)

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| `list -A -o json --kube-context <ctx> --deployed --failed --pending --uninstalling --uninstalled`: every flag exists | step `core.helm-list` | `pkg/cmd/list.go:126-132@v4.3.1`; `pkg/cli/environment.go:155@v4.3.1` | v4.3.1; v3.22.1 (`cmd/helm/list.go:119-125`) |
| A row is `{name, namespace, revision, updated, status, chart, app_version}`; an empty list prints `[]` | `lib/hygiene.py:_helm`, `lib/scaling.py` (Karpenter version from app_version/chart) | `pkg/cmd/list.go:142-150, 158-181@v4.3.1` | v4.3.1; identical in v3.22.1 (`cmd/helm/list.go:135-173`) |
| `updated` is Go `time.Time.String()` (`2025-12-29 02:07:42.385466 +0900 KST`) unless `--time-format` | `_helm` via `_ts` | `pkg/cmd/list.go:171-179@v4.3.1` | v4.3.1; v3.22.1 (`cmd/helm/list.go:163-171`) |
| `status` is one of unknown, deployed, uninstalled, superseded, failed, uninstalling, pending-install, pending-upgrade, pending-rollback | check `hygiene.helm-release-not-deployed` | `pkg/release/common/status.go:25-41@v4.3.1` | v4.3.1; v3.22.1 (`pkg/release/status.go:25-41`) |
| `chart` is `<name>-<version>` and `app_version` the chart's appVersion | `_helm` (chart_name, chart_version) | `pkg/cmd/list.go:167-168@v4.3.1` (`formatChartName`, `formatAppVersion`) | v4.3.1 |
| Helm 4 dropped `--all` and lists every status by default, where Helm 3 listed deployed and failed; kubegap names the statuses explicitly, so the output is the same | step comment in `lib/tools.py` | `cmd/helm/list.go:37-39, 118, 122@v3.22.1`; `pkg/cmd/list.go:40-43@v4.3.1` | — |
| `helm list` reads release records stored as Secrets, so the shipped ClusterRole makes it fail | `_helm_missing_note` | **unverified in source**: observed on the EKS cluster (`secrets is forbidden`); the storage driver is `pkg/storage/driver/secrets.go` | — |

## Pod /metrics names of the components kubegap scrapes itself (`type: pod-metrics` steps, issue #120)

The names, labels, version ranges and `file:line@tag` of every metric a pod-metrics step collects and a parser reads live next to the step, in `collectors/<area>/pod-metrics.yaml`, and `lib/podmetrics.py` reads them: a parser asks for a logical key and gets the first spelling the running version emits. `tests/test_sources.py` requires a citation on every spelling, a well-formed `since`/`before`, a `source:` on every pod-metrics step, and that no parser spells a metric outside its table; `tests/test_podmetrics.py` checks that every name passes the step's `keep` filter and that a renamed metric is read under either spelling, never both. The rows below are the facts that are not per-name.

| Fact | kubegap | Source | Holds for |
|---|---|---|---|
| Karpenter 1.0.0 renamed or removed most metrics in one step and no release emits both spellings: `_total` suffixes on counters, `nodepool` → `nodepools`, `disruption` → `voluntary_disruption`, `provisioner_scheduling` → `scheduler`, `*_time_seconds` → `*_duration_seconds`; `karpenter_interruption_actions_performed` and `karpenter_consistency_errors` have no successor | `collectors/karpenter/pod-metrics.yaml`, `lib/karpenterctl.py:_pod_metrics` | `kubernetes-sigs/karpenter pkg/metrics/metrics.go:31-125@v0.37.0` against `:33-58@v1.0.0` and `:35-113@v1.15.1`; `aws/karpenter-provider-aws pkg/controllers/interruption/metrics.go:33-59@v0.37.0` against `:31-48@v1.0.0` | v0.37.0, v1.0.0, v1.1.0, v1.15.1 read |
| Karpenter 0.x `karpenter_nodeclaims_disrupted` carries `type` and `nodepool`, not `reason`; 1.x `karpenter_nodeclaims_terminated_total` carries no `reason` | `lib/karpenterctl.py:_pod_metrics` (label fallbacks) | `kubernetes-sigs/karpenter pkg/metrics/metrics.go:90-96@v0.37.0`; `:50-56@v1.15.1` | observed: the 0.37.0 cluster grouped every disruption under `-` until #120 |
| KEDA removed `keda_scaler_errors_total` and `keda_scaler_errors` in 2.17.0; `keda_scaled_object_errors_total` and `keda_scaler_detail_errors_total` exist since 2.14.0 | `collectors/keda/pod-metrics.yaml`, `lib/kedactl.py` | `kedacore/keda pkg/metricscollector/prommetrics.go:107@v2.16.0` present, absent at `:91-102@v2.17.0`; `:116, 134@v2.14.0` | v2.12.0 … v2.21.0 read |
| KEDA's gRPC client counters are go-grpc-middleware's with the namespace `keda_internal_metricsservice` | `lib/kedactl.py` | `kedacore/keda cmd/adapter/main.go:146@v2.17.2, :147@v2.19.0, :149@v2.21.0`; `grpc-ecosystem/go-grpc-middleware providers/prometheus/client_metrics.go:37-45@providers/prometheus/v1.0.1` | v2.17.2, v2.19.0, v2.21.0 |
| Grafana's user total is `grafana_stat_total_users` (singular); the plural spelling kubegap read until #120 never existed | `collectors/grafana/pod-metrics.yaml`, `lib/stackhealth.py:_grafana` | `grafana/grafana pkg/infra/metrics/metrics.go:465@v10.2.3, :495@v12.2.1, :490@v13.3.0` | v10.2.3, v12.2.1, v13.3.0 |
| Between 10.2.3 and 12.2.1 (the exact release was not read) Grafana added `secure_socks_ds_proxy_enabled` to `grafana_datasource_request_total`; the labels kubegap reads (`datasource`, `datasource_type`, `code`) are unchanged | `lib/stackhealth.py:_grafana` | `grafana/grafana pkg/infra/httpclient/httpclientprovider/datasource_metrics_middleware.go:21@v10.2.3, :22@v12.2.1 and @v13.3.0` | — |
| Argo CD 3.x added labels (`dry_run` on `argocd_app_sync_total` and `argocd_app_k8s_request_total`, `command` on `argocd_redis_request_total`); the labels kubegap reads are unchanged | `lib/argocdctl.py` | `argoproj/argo-cd controller/metrics/metrics.go:92-104@v2.13.0` against `:73-95@v3.6.0`; `server/metrics/metrics.go:28-33@v2.13.0` against `:30-35@v3.6.0` | v2.13.0, v3.2.0, v3.6.0 |
| cert-manager 1.21 moved the certificate gauges into a collector and renamed the ACME request label `path` to `action`; kubegap reads `status` only | `lib/certmanager.py` | `cert-manager/cert-manager pkg/metrics/metrics.go:133@v1.14.4` against `:114-123@v1.21.3`; `internal/collectors/certificate_collector.go:30-34@v1.21.3` | v1.14.4, v1.21.3 |
| The ALB controller's `aws_api_calls_total` carries `status_code` and `error_code`; the step keeps only the duration and retry histograms and derives the call count from `aws_api_call_duration_seconds_count` | step `alb-controller.controller-metrics`, `lib/albctl.py:_pod_metrics` | `kubernetes-sigs/aws-load-balancer-controller pkg/aws/metrics/instruments.go:36-39@v2.7.2`; `pkg/metrics/aws/instruments.go:46-49@v3.6.2` | v2.7.2, v3.6.2 |
| controller-runtime 0.24 adds a `controller` label to `workqueue_depth`; kubegap reads the values only | `lib/albctl.py:_pod_metrics` | `kubernetes-sigs/controller-runtime pkg/metrics/workqueue.go:41@v0.14.6` against `:21-22@v0.24.1` | — |
| A Prometheus counter vector has no series until its first increment, so a name defined in the source can be absent from a scrape | `lib/podmetrics.py:removed` (tells a removed metric from a missing series) | **unverified in source** (client_golang's `MetricVec`); observed: `grafana_datasource_request_total` absent on an idle Grafana 12.2.1, `keda_internal_metricsservice_grpc_client_*` absent on an idle KEDA 2.19.0 | — |
| The pod-metrics ports (8080, 8082-8084, 9402, 8000, 3000, 7472) and the pod selectors | every pod-metrics step | **unverified in source**: observed on the two clusters; the components' default listen addresses are not read in this issue | — |

## Log signatures (#129)

`logs.signatures` matches the patterns in `collectors/*/signatures.yaml` and `signatures/catalog.yaml` against the component pod logs (`lib/logs.py` `scan`). A pattern the component never prints never matches and the signature stays silent.

Covered so far: CoreDNS. The other collectors and `signatures/catalog.yaml` are not yet read.

### CoreDNS

Versions read: v1.11.3 (EKS add-on `v1.11.3-eksbuild.1` on the EKS cluster), v1.12.3 (the image in `manifests/coredns.yaml@v1.33.5+k3s1`, the k3s cluster), v1.15.0 (newest release). Go strings were read at go1.21.0 (the `go` line of `go.mod@v1.11.3`) and go1.26.0 (`go.mod@v1.15.0`).

How a CoreDNS line looks. Text format is the default: the level as `[ERROR] `, `[WARNING] `, `[INFO] ` or `[FATAL] ` (`plugin/pkg/log/log.go:101@v1.11.3`), then `plugin/<name>: ` for a plugin logger (`plugin/pkg/log/plugin.go:15@v1.11.3`, `:15@v1.12.3`, `:16@v1.15.0`), then the message. v1.15.0 added `-log-format json` (`coremain/run.go:33@v1.15.0`); in JSON mode the plugin name goes into a `"plugin"` field (`plugin/pkg/log/json.go:105@v1.15.0`) and `plugin/<name>: ` is not in the line, so `coredns.loop` and the `plugin/errors` parts of the patterns below do not match JSON logs. Neither cluster's manifest passes the flag (`manifests/coredns.yaml:137@v1.33.5+k3s1` passes only `-conf`). The EKS add-on's arguments were observed on the cluster, not read in source: the add-on manifest is not published.

| Signature | What kubegap relies on | Source | Holds for |
|---|---|---|---|
| `coredns.servfail` | A SERVFAIL that CoreDNS itself returns is logged by the `errors` plugin as `plugin/errors: 2 <name> <type>: <error>`: the rcode is printed as a number, `%d` | `plugin/errors/errors.go:97@v1.11.3`, `:97@v1.12.3`, `:118@v1.15.0` | all three |
| | The `forward` plugin returns `dns.RcodeServerFailure` (2) with the upstream error, or with `no healthy proxies` when every upstream is down, so upstream failures reach the `errors` line above | `plugin/forward/forward.go:202,205@v1.11.3`, `:223,226@v1.12.3`, `:294,297@v1.15.0` | all three |
| | The word `SERVFAIL` appears only in the query log of the `log` plugin, whose `{rcode}` is the rcode name (`plugin/pkg/replacer/replacer.go:67`, `plugin/log/log.go:69@v1.11.3`, `:89@v1.15.0`). The `log` plugin is not in the k3s default Corefile (`manifests/coredns.yaml:55-77@v1.33.5+k3s1`). For EKS this is **unverified**: the add-on's default Corefile is not published in a source repository; a run records whether the cluster's Corefile has `log` in `coredns.summary` `config.log` (`lib/coredns.py:79`) | as listed | all three |
| `coredns.upstream-timeout` | The upstream error text reaches the `errors` line (rows above). A read deadline prints `i/o timeout` (`src/internal/poll/fd.go:60@go1.21.0`, `@go1.26.0`) inside `read udp <src>-><dst>: ` from `net.OpError` (`src/net/net.go:469@go1.21.0`, `:501@go1.26.0`); `unreachable` comes from errno 101 `network is unreachable` (`src/syscall/zerrors_linux_amd64.go:1458@go1.21.0`, `:1456@go1.26.0`) | as listed | all three |
| `coredns.loop` | The `loop` plugin logs `Loop (<src> -> <dst>) detected for zone "<zone>"` with `Fatalf`, so the process exits and the pod restarts; the line reads `[FATAL] plugin/loop: Loop (` | `plugin/loop/loop.go:53@v1.11.3`, `:53@v1.12.3`, `:52@v1.15.0` | all three, text format |
| `coredns.reload-failed` | The `reload` plugin logs `Corefile parse failed: <err>` (warning) when the new Corefile does not parse and `Corefile changed but reload failed: <err>` (error) when the restart fails; both lines start `plugin/reload: ` | `plugin/reload/reload.go:97,111@v1.11.3`, `:97,111@v1.12.3`, `:116,134@v1.15.0` | all three |
| | A directive error inside `<err>` reads `<file>:<line> - Error during parsing: <msg>`, from CoreDNS's fork of the Caddy parser | `coredns/caddy caddyfile/dispenser.go:229@v1.1.1` (`go.mod@v1.11.3`), `:238@8de985351a98` (`go.mod@v1.12.3`), `:238@v1.1.4` (`go.mod@v1.15.0`) | all three |

Notes that do not change a pattern:

- v1.15.0 can consolidate repeated errors (`errors { consolidate ... }`, `plugin/errors/errors.go:53-80@v1.15.0`), in which case the individual `plugin/errors: 2 ...` lines are replaced by a summary line. Neither default Corefile configures it.
- `Error during parsing` also appears when a pod starts with a broken Corefile; there the process exits instead of keeping the old configuration. `coredns.reload-failed` counts both.
- A timeout line also contains `plugin/errors: 2 `, so it counts under both `coredns.upstream-timeout` and `coredns.servfail`. Both describe the same event from two sides: the cause, and the answer the client got.

Corrections found in source:

- `coredns.servfail` matched only ` SERVFAIL `, which only the `log` plugin prints. With the k3s default Corefile, or any Corefile without `log`, it could never match, so the signature stayed silent through upstream outages. The pattern now also matches `plugin/errors: 2 `, the line CoreDNS writes when it answers SERVFAIL itself. `tests/test_sources.py` holds lines built from the format strings above.

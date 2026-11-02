# Changelog

All notable changes to kubegap are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `vpccni.external-snat-off-with-private-routes`: warns when the VPC CNI keeps its default of SNATing pod traffic that leaves the VPC while the cluster VPC has routes to a peering connection, a transit gateway or a VPN. On those paths the destination sees the node IP instead of the pod IP, which is what cost MindTickle a month of lost packets in 2020. The full run now collects the VPC route tables, `aws/describe-route-tables.json`, through the `ec2:Describe*` permission the IAM policy already grants. Rubric 0.1.54, 403 checks. ([#43](https://github.com/KyungHwanKim-devs/kubegap/issues/43))

### Changed

- 108 checks now carry `cases`, public incident write-ups whose root cause is the condition the check detects, 203 links in all; before, 2 checks did. The sources are the 59 stories on k8s.af, read one by one, including the conference talks through their captions, and 24 write-ups from 2023 onward. Companies cited with a year in `why` but without a link now have one or were removed, and two webhook checks no longer cite a Skyscanner incident that was about Argo CD pruning. `docs/CHECKS.md` lists every case and says how many checks have one. Rubric 0.1.53. ([#28](https://github.com/KyungHwanKim-devs/kubegap/issues/28))

## [0.1.1] - 2026-11-02

The first milestone, permissions and the read-only claim, is complete: issues #1 to #5. Contributors to this release: [@junhoeKu](https://github.com/junhoeKu) (#31) and [@Rapil3090](https://github.com/Rapil3090) (#34).

### Removed

- The `helm-values` collection step and the check `hygiene.helm-release-pure-defaults`. `helm get values` reads Helm's release Secrets and the values often hold credentials; they were stored raw in the snapshot. `helm list` stays, and the READMEs now say that it reads Helm's release records, which Helm keeps in Secrets, and that only their metadata is stored. When `helm list` fails for lack of secrets permission, the summary says so instead of "helm not installed". Rubric 0.1.52, 402 checks. ([#3](https://github.com/KyungHwanKim-devs/kubegap/issues/3))

### Changed

- Node SSH connections check host keys strictly (`StrictHostKeyChecking=yes`): only nodes already in `~/.ssh/known_hosts` are reached, and a refused key is reported with a hint. `ssh.accept_new_hosts: true` in config.yaml restores the earlier `accept-new` behaviour. `deploy/node-access/README.md` describes the preparation. ([#4](https://github.com/KyungHwanKim-devs/kubegap/issues/4))
- EKS node commands run through a custom SSM document, `kubegap-node-read` (`deploy/permissions/ssm-document.yaml`), instead of `AWS-RunShellScript`. The document embeds every read command and takes no free command text; kubegap compares its sha256 with the account copy before sending and `kubegap setup` uploads it with consent (`--install-ssm-document`, config `ssm_document`). The IAM policy allows `ssm:SendCommand` only on that document and only on instances tagged `kubernetes.io/cluster/<CLUSTER_NAME>=owned`. ([#1](https://github.com/KyungHwanKim-devs/kubegap/issues/1))
- `kubegap nodes --cmd` is no longer available on the SSM backend; `--step <name>` runs one documented step instead.

- ConfigMap values are no longer written to the snapshot. `objects/configmaps.json` keeps each key's length and shape, the real value only for the configuration keys kubegap parses (`KEEP_VALUES` in `lib/scrub.py`), and a `kubegap_scrub` record with the secret-like key names that `security.plaintext-configmap-secret` now reads. ([#2](https://github.com/KyungHwanKim-devs/kubegap/issues/2))
- Component pod logs are deleted from the snapshot after `summarize` has aggregated them; `logs/pods/REMOVED.txt` marks it and `logs/pods/AGGREGATED.json` keeps the log-derived results so a rerun of `summarize` gives the same summary. Sample lines kept in `summary.logs` are masked. `keep_component_logs: true` in config.yaml keeps the raw logs. ([#2](https://github.com/KyungHwanKim-devs/kubegap/issues/2))

### Fixed

- The DaemonSet node backend (`deploy/node-access/daemonset.yaml`) was never used by collection: the node step gate and the pod-metrics node-curl fallback accepted only `ssh` and `ssm`, so every node step was skipped as "no node command backend". Both now accept `daemonset`. `node_access: daemonset` in config.yaml is applied like the other values and says so when no reader pod is Running. The `get` and `create` permissions on `pods/exec` that `kubectl exec` needs are in a new, namespaced `deploy/permissions/role-daemonset-exec.yaml`. ([#5](https://github.com/KyungHwanKim-devs/kubegap/issues/5))
- The embedded test cases of `platform.k8s-version-eol` compared against the real date and began failing once Kubernetes 1.34 passed its end-of-support date, which turned CI red for every pull request. Test cases can now pin the date with `today` in their inventory; `days_until` reads it.
- The adjustment table in `llm/adjustments.md` now also records every aggregate the agent recounted against the first pass, in its own `Recounted aggregates` table, so a number in the report that differs from `findings-draft.json` always has a reason next to it. Reported and fixed by [@junhoeKu](https://github.com/junhoeKu) in [#31](https://github.com/KyungHwanKim-devs/kubegap/pull/31). ([#13](https://github.com/KyungHwanKim-devs/kubegap/issues/13))
- The password-line pattern of `security.plaintext-configmap-secret` missed lines whose key is the bare word, such as `password = ...`; it required one leading character.

### Added

- `scripts/kubegap prune --keep-daily N --keep-full M` removes old snapshot folders of a context, with defaults from `retention` in config.yaml and `--dry-run` to list first. The latest complete daily and full snapshots always stay because they are the diff baselines; interrupted collections are removed unless one is still running. ([#20](https://github.com/KyungHwanKim-devs/kubegap/issues/20))
- `deploy/node-access/COMMANDS.md`, the complete list of commands kubegap runs on nodes per backend, generated by `scripts/kubegap node-commands --markdown` and kept current by a test.

## [0.1.0] - 2026-10-27

### Added

- First release.
- Read-only audit of a Kubernetes cluster against 403 checks in 12 areas, defined as data in `collectors/*/checks.yaml` with embedded test cases.
- Two modes: `daily` with a reduced collection, compared with the previous daily run, and `full` with everything, compared with the previous full run.
- Two report files: `report.md` written for a person, with the top problems and why each happens, and `report-details.md` assembled from the snapshot.
- EKS as the baseline platform and k3s as a variant, with node access through SSM, SSH or a DaemonSet.
- Expectation profiles `prod`, `lab`, `small-prod`, `multi-az-prod` and `dev`.
- English and Korean README and sample reports.

[Unreleased]: https://github.com/KyungHwanKim-devs/kubegap/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/KyungHwanKim-devs/kubegap/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/KyungHwanKim-devs/kubegap/releases/tag/v0.1.0

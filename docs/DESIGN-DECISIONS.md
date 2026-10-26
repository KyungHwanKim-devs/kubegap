# Design decisions

The choices that shape kubegap and the reason for each. A change that reverses one of them should add or edit the entry here.

## 1. The problem is what dashboards cannot show

A cluster can be running and still be inefficient, under-observed or one failure away from an outage. Dashboards show the metrics that are already collected, not what is missing or never installed. Asking a coding agent to "look at the cluster" gives a different view every time, so two runs cannot be compared.

kubegap fixes three things and lets the LLM work on top of them: the list of commands that collect data, the raw output saved in a dated snapshot, and a rubric that says per check what is examined, when it is a problem and why. Code marks each check pass, warn or fail. The LLM makes the final call and writes the report.

## 2. Numbers belong to code, judgement belongs to the LLM

The first design was a batch pipeline that produced the whole report from thresholds, weights and a per-area score, with the LLM optional at the end and never shown raw data. It was dropped.

Code does deterministic collection and a first pass. The LLM reads the summary, opens raw snapshot files when something looks off, decides the final severity, orders the problems and writes the prose. When it overrides a first-pass verdict it writes the reason in the report, in a table the reader can check.

Thresholds alone cannot tell an idle staging namespace from a production one, or a one-off spike from a trend. Making the LLM accountable for its overrides keeps the judgement inspectable without pretending a formula could make it.

## 3. No score

The report never gives the cluster a number out of 100. It gives counts by severity and the change since the previous run of the same mode. A score invites optimising the score. A list of concrete problems with evidence invites fixing them.

## 4. Read-only, and Secret values are never read

kubegap runs no command that changes a cluster. Secret objects are collected with their `data` and `stringData` fields removed before anything is written to disk. The ClusterRole in `deploy/permissions/` excludes `secrets` entirely; Secret metadata comes from kube-state-metrics instead.

A tool that one person points at production without a review board must be safe to run by construction, not by convention.

## 5. The rubric is data, with a version

Checks live in `collectors/<name>/checks.yaml` with their thresholds, rationale, public cases and embedded test cases. `rubric/version` changes whenever a check changes and is printed in every report.

When the number of findings moves between two runs, the reader needs to know whether the cluster changed or the criteria did. The version makes the two distinguishable, and a report can say that a finding disappeared because a rule changed, which is not a fix.

## 6. Absence is a finding

A separate check type, `absence`, fails when something the profile expects is not installed at all: a metrics store, a log store, alert routing, backups, event retention, SLO definitions. The most expensive gaps in small operations are the things nobody set up, and no metric can show that because the metric does not exist.

## 7. EKS is the baseline, k3s is the variant, built together

Every collector is written for EKS first and run on a small k3s cluster in the same step. Platform-specific collectors are gated by the detected platform; everything else is plain Kubernetes. Building for one platform and porting later leaves the port half done. Building both at once forces every check to say which platform it applies to.

## 8. Node access through one interface, backend chosen by platform

Kernel logs, containerd state and sysctl values are read inside nodes through one function. On EKS the backend is SSM `send-command`; on bare metal it is SSH; a privileged DaemonSet is the third option for environments with neither. Nodes that cannot be reached produce a finding, and their node-level checks are marked skipped, never silently passed.

kubelet and node-exporter cannot show OOM-killer lines, soft lockups or NIC resets. Those are the problems that look like application bugs until someone reads `dmesg`.

## 9. Node preparation is the user's one-time job; the tool only checks it

On SSH nodes kubegap modifies nothing. The user adds the login user to the log-reading groups once and, optionally, installs a sudoers file that allows a fixed list of read commands. `kubegap nodes` reports per node which reads are possible, and checks that need a missing read are marked "no node permission". A read-only tool that edits node configuration to make itself work is no longer read-only.

## 10. Final severity in the report, first-pass severity in history

`history.csv` counts the code's first-pass severity. The LLM's final severity lives in the report. When the two differ by three or more at critical plus high, the report says so. History must be reproducible to be a trend; the LLM's judgement is the useful one for today, but it is the one that can vary.

## 11. Tools are offered, not assumed; the kube context is confirmed

Missing tools are listed with the reason each is needed. The user is asked once and can decline, in which case only the checks that need that tool are marked "tool missing". At the start of a run the current kube context is shown and confirmed unless the configuration says not to ask. Running an audit against the wrong cluster is the most likely operator mistake; installing binaries without asking is the most likely trust mistake.

## 12. Snapshots and personal configuration live outside the repository

Raw data goes to `~/.kubegap/snapshots/` and personal settings to `~/.kubegap/config.yaml`, never inside the skill folder. Cluster data mixed into a skill repository makes the repository impossible to publish or contribute to.

## 13. Coverage is traced before verdicts are tuned

Before any threshold was adjusted, every intended check from the design notes was mapped to a check id in `references/coverage.md`. Gaps were implemented; items that could not be measured were listed as excluded with the reason. Looking only at the checks that fired cannot reveal the checks that were never written.

## 14. Verdicts are reviewed against real clusters and corrected

Every check that produced a warn or fail on real clusters was reviewed by a person, area by area, and the noisy ones were changed. The corrections that recurred: transient workloads such as Jobs, CronJobs and CI runners are excluded from resource checks; findings older than 30 days are dropped; single-count triggers became count-or-ratio thresholds; checks whose failures were already covered by another check were lowered to warn; platform defaults that are not misconfigurations were lowered to warn; many fails with one root cause became one cluster-level check.

A check that is right in theory and noisy in practice gets suppressed, and then it is useless. This review is the part of the repository that could not have been generated.

## 15. Two modes, daily by default, compared with the same mode

`daily` collects a reduced set, evaluates the checks that make sense on it, and compares with the previous daily run. `full` collects everything and compares with the previous full run. Checks that need data a daily run does not collect are reported as not collected, not as passed. A daily run has to be short enough to happen every day, and comparing a daily run with a full run produces false "resolved" findings by the hundred.

## 16. Collection runs in parallel, with low concurrency

Collectors, items within a collector and PromQL queries run concurrently with small fixed worker counts. Serial collection on a mid-sized cluster takes long enough that the daily run stops being daily. The worker counts are low so that a read-only audit never becomes measurable load on the API server or Prometheus.

## 17. Two report files: one for a person, one for the record

`report.md` is written by the LLM for a person: the top problems, each with the problem, the evidence, the cause, the action, why this happens, and the checks it rests on. `report-details.md` is assembled by code from the snapshot: every table, every first-pass result, every adjustment the LLM made.

The first version was one long file, and the parts a person needs were buried under the parts an agent needs. Splitting them also makes the code-assembled half reproducible by construction.

## 18. Profiles are expectation levels, not platforms

A profile says how strict to be: `prod`, `lab`, `small-prod`, `multi-az-prod`, `dev`. The platform is detected separately and gates platform collectors. Earlier profile names that mixed the two are kept as aliases. A production k3s cluster and a lab EKS cluster both exist; naming profiles after platforms judged the first too gently and the second too harshly.

## 19. English is the repository language; the report language is asked for

Code, checks, documentation and samples are in English. The report is written in the language the user chooses when asked; a Korean README and Korean samples are provided. The checks and their rationale are the part worth contributing to, and that needs one language. The report is read by one operator, and it should be in theirs.

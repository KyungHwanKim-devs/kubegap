<!--
kubegap human report, saved as <snapshot>/report.md.
`scripts/kubegap write-report` assembles it (lib/output/writer.py `assemble`): agents write the sections marked "agent" from llm/facts.json
in the language's guides (references/write-overview-<language>.md, references/write-problem-<language>.md); code writes every other section
from the snapshot and the facts. The reference half (every table, every automatic verdict, the analysis record) is report-details.md.

What it is. A diagnosis the reader learns from: what already happened, the largest problems and why each comes about, how each is watched
and how it is solved in practice at the scale the cluster is run at. It is not a list of commands to type; the reader acts through their
own process. A daily report carries what happened and what changed and picks no problems (the rows marked "full").
-->
# {{cluster_name}} — {{mode}} audit, {{date}}

<!-- code, from the titles in the facts -->
Broken now: {{titles | none}}
The N largest problems: ① {{title}} ② {{title}} …          <!-- daily: the titles of the last full report, with its date -->
What already happened: {{titles | none}}
Scale: {{small | medium | large}}

## The cluster at a glance                                   <!-- code -->

## Broken now                                                <!-- agent; the section is absent when nothing is broken -->
### {{title}}

## What already happened                                     <!-- agent; the first line (the period covered) is code -->
This covers {{start}} to {{end}}.
### {{incident title}}
<!-- What happened and when, that it is over, why (with how sure), and the problem it exposed by number and title. -->

## 1. {{problem title}}                                      <!-- agent, one per problem; full only -->
<!-- A title is a subject and a short statement ("Backups stay inside the cluster"), never a long modifier in front of a noun. -->
**Why it was picked.** {{what is lost when it happens, in one line}}
### What is the matter
### Why it comes about
<!-- The cause in this cluster with how sure it is; then the mechanism at length; then public cases, each linked. This is where the reader learns. -->
### How to watch it
<!-- A metric, an alert rule or a dashboard first, saying whether the cluster has it; a command only as an example. -->
### How it is solved
<!-- What practitioners do, the option that fits this cluster's scale first, with what it costs; where it is declared, named only from the
     snapshot's evidence; what to be careful about when applying it here. An example shows a shape. No numbered steps, no per-step check, no rollback procedure. -->
### Evidence
| What | Value | Source |
|---|---|---|
### Further reading
<!-- Three to five, each linked, each with why it is worth reading. -->

## The next largest problems                                 <!-- agent; daily: "Serious and still there" -->

## Findings you decided not to fix                           <!-- code: the suppressions of the config file, nothing else; no section when there are none -->

## Since the previous report                                 <!-- code -->
| What the previous report advised | State | Proof |
|---|---|---|
**Appeared** / **Went away** / **The cluster is the same; these differ because what kubegap checks changed**

## Coming up                                                 <!-- code -->

## Each area in one line                                     <!-- code; full only -->

## Limits of this run                                        <!-- code -->
**Not judged because the cluster does not hold the data** / **Not read by kubegap yet** / **What you answered not to read at the first-run questions**
<!-- Each with the conclusion it weakens. -->

## Numbers                                                   <!-- code -->
<!-- The scale the severities are for, the one baseline (the last run of this mode that has a report), then per severity: fail, warn, failures resolved since, failures new since. -->

Checks behind each entry: … <!-- code -->

Details and every table: [`report-details.md`](report-details.md) · kubegap {{version}}, rubric {{rubric}} · snapshot `{{path}}`

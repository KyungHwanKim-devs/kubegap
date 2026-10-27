<!--
kubegap human report. Written entirely by the LLM, saved as <snapshot>/report.md, in both modes (daily: Top 3, full: Top 5).
The reference half (every table, the full first-pass list, tool notes) is report-details.md, produced by `scripts/kubegap render-details`
from the snapshot plus the fragments in <snapshot>/llm/. This file never repeats those tables; it links to them.

Rules for this file:
- Written for a person who runs the cluster and reads this once, top to bottom, in five minutes (daily) or fifteen (full). A busy reader stops after the Top N.
- Speak about things, not about checks: name the namespace, workload, node. Check ids appear only on the one "Evidence checks" line under each problem.
- Each problem has six parts in this order: Problem, Evidence, Cause, Action, Why this happens (principle / cases / read next), Evidence checks.
- Tone follows the report tone rules in references/report-writing.md section 8: conclusion first, one idea per sentence, plain words, polite register, numbers with units, no parenthetical asides.
- No analogies. No invention: every number comes from the snapshot, every source in a learning point comes from the check definition or a primary document.
- {{...}} are slots. <!-- --> comments are instructions; delete them before saving. Headings are English in the template; translate them when the report language is Korean, keep ids, paths, commands and names as they are.
- Right before saving, run `scripts/kubegap mask` on this file and report-details.md.
-->
# {{cluster_name}} — {{mode_word}} audit, {{date}}

{{opening_paragraph}}
<!-- Three to five sentences: what this cluster is (platform, size, profile), whether anything is on fire right now, the one thing that changed since the previous run of this mode, and whether a full run is due (daily only). No numbers table here. -->

## The {{n_top}} problems to work on
<!-- daily: 3, chosen as new or recurred first, then the persisting critical/high items with the largest impact. full: 5, chosen by severity × impact × difficulty; with an SLO, by error-budget burn. Dozens of findings with one cause are one problem. Order 1 = most urgent. -->

### 1. {{problem_1_title}}
<!-- Title is a plain sentence about the thing, e.g. "15 prod apps can only run on one node, and that node rebooted yesterday" -->
**Problem.** {{problem_1_what}} <!-- what is wrong, how, and the impact on users or operations right now. Two or three sentences. -->

**Evidence.** {{problem_1_evidence}} <!-- the three to six numbers that carry the problem, each in its own short sentence with its source file named after the number, not in parentheses. Everything else is in report-details.md; do not pile every value in here. Measured during collection? say so. A number here that differs from the first-pass aggregate for that check (its note, value or item count in findings-draft.json) must have a row in llm/adjustments.md with the reason. -->

**Cause.** {{problem_1_cause}} <!-- why it came to this. When not certain, start with "Most likely," -->

**Action.** {{problem_1_action}} <!-- in order ①②③; what to change, the expected effect, and the effort as plain words at the end of the sentence, such as "Takes 30 minutes." A manifest fragment or exact command where possible. -->

**Why this happens.**
- Principle: {{problem_1_theory}} <!-- the principle behind it in one or two sentences (how the mechanism works, which operating rule it breaks: e.g. CPU limits are a ceiling enforced per 100 ms CFS period; HPA scales on request, not limit). No analogies. -->
- Cases: {{problem_1_experience}} <!-- a public case, named with year and taken from the check's `cases`/`why`/`notes` or a primary document (Kubernetes docs, Google SRE Book chapter, a vendor postmortem). If the check definition carries none, write "No public case recorded for this check." Never invent a source or a URL. -->
- Read next: {{problem_1_study}} <!-- two or three search terms or document sections a reader can look up to go deeper, e.g. "CFS quota and throttling (kernel sched-bwc), Kubernetes docs: Resource Management for Pods, Google SRE Book ch. 4 Service Level Objectives". Terms, not links, unless the link is in the check definition. -->

Evidence checks: `{{problem_1_findings}}`

### 2. {{problem_2_title}}
**Problem.** …
**Evidence.** …
**Cause.** …
**Action.** …
**Why this happens.**
- Principle: …
- Cases: …
- Read next: …

Evidence checks: …

### 3. {{problem_3_title}}
…

<!-- full mode only: problems 4 and 5 in the same shape -->

<!-- Optional, one line, when something outside the Top N takes under 30 minutes to fix: "Quick fix outside the list: …" -->

## Since the previous {{mode_word}} run ({{previous_date_or_none}})
<!-- From diff.json, as prose, not a list of ids: what appeared, what went away, what came back, what objects changed and why (deploy, scale, config). Five to eight sentences.
     A finding that exists only because the rubric changed is a "criteria change", written apart from cluster changes.
     If there is no earlier snapshot of this mode, this section is exactly one sentence: "No earlier {{mode_word}} snapshot to compare with." -->
{{changes_paragraph}}

Progress on the previous report's problems: {{previous_actions_progress}} <!-- one sentence per previous Top N item: started / done / not started, with the number that proves it. Omit the whole line when there is no previous report of this mode. -->

## What this run could not see
<!-- One paragraph. Absent components the profile expects (section 5 of details), checks not evaluated in this mode with the count and the last full run date (daily), tools missing, collection steps that failed, and measurements that collection itself disturbed. Not a list of ids. -->
{{blind_spots_paragraph}}

## Numbers
| Severity | fail | warn | vs. previous {{mode_word}} run |
|---|---|---|---|
| critical | {{n_critical}} | {{w_critical}} | {{d_critical}} |
| high | {{n_high}} | {{w_high}} | {{d_high}} |
| medium | {{n_medium}} | {{w_medium}} | {{d_medium}} |
| low | {{n_low}} | {{w_low}} | {{d_low}} |
<!-- Counts by the LLM's final severity. One sentence under the table when the final critical+high differs from the first pass by 3 or more. -->

Details, every table and the full first-pass list: [`report-details.md`](report-details.md) · kubegap {{kubegap_version}}, rubric {{rubric_version}} · snapshot `{{snapshot_path}}`

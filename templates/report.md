<!--
kubegap human report, saved as <snapshot>/report.md, in both modes (daily: 3 problems, full: 5).
`scripts/kubegap write-report` writes it from llm/facts.json: a writer agent writes the body from the facts, in the language's guide
(references/writing-<language>.md); code adds the title line, the numbers table, the check ids and the tail.
The reference half (every table, every automatic verdict, the analysis record) is report-details.md, produced by `scripts/kubegap render-details`
from the snapshot plus the `analysis` block of the facts. This file never repeats those tables; it links to them.

Shape. The reader is the person who runs the cluster. They read it in the morning, decide what to do today, and run it on production.
So the first screen settles the decision, every problem ends in steps with a check and a way back, and nothing is said about an entity
that was not looked at.
-->
# {{cluster_name}} — {{mode_word}} audit, {{date}}

{{first_screen}}
<!-- Five lines at most, no heading:
     Urgent now: yes — <what is broken, in one sentence> / no
     Today's problems: ① <title> ② <title> ③ <title>          ← the titles of the sections below, nothing more
     Since the last {{mode_word}} run: <what the previous report asked for and whether it was done> <what appeared, what went away>, with the numbers.
     With no earlier run of this mode: "No earlier {{mode_word}} run to compare with." -->

<!-- Code writes the next two sections from the snapshot and the facts. -->
## The cluster at a glance
| What | Value |
|---|---|
| Nodes | {{ready}} of {{count}} Ready |
| Pods | … running, … pending, … failed |
| Namespaces | …, … production |
| Components | … |
| Metrics and log stores | … |
| Kubernetes | … |

## Coming up
| When | What | Source |
|---|---|---|
<!-- From `upcoming` in the facts: node expiries, certificate expiries, end of support, cleanup jobs, quotas about to fill. "none" when the facts carry nothing. -->

## 1. {{problem_1_title}}
<!-- A noun phrase that names the thing that is wrong, e.g. "15 prod apps that can only run on one node". Never a sentence. -->

**What is happening.** {{situation}}
<!-- What is wrong, since when, and what the reader feels now. Numbers with unit, scope and period. If it is over, say so.
     Then impact, by what was actually looked at: affected (each with its own evidence) · checked and healthy · changed in the window for another reason (and by what) · not checked. Nothing is affected by inference. -->

**Why.** {{cause}}
<!-- One sentence, then "confirmed", "likely" or "unknown". A likely cause gets its evidence in one line. Never stronger than the facts. -->

**Suggested fix.**
① {{step}} <!-- If a condition applies, it comes first: "If A, …". Then what to do in one sentence. -->
```
{{command}}
```
<!-- One command per block, exactly as in the facts, nothing to edit after copying. A manifest fragment is its own block.
     Then, as sentences: what the cluster does when this runs, and the risk: what restarts, what goes down and for how long, who reverts a by-hand change, what can be lost. Only the ones that apply.
     Check: how the reader sees it worked, a command or a value. -->
② …
③ …

**Rollback.** {{rollback}}
<!-- How to undo what the steps changed. When something cannot be undone, say so and which step backs up first. -->

**Why this happens.** {{principle}} {{case}} {{reading}}
<!-- Two or three sentences on the mechanism, from the check's why or a document that was read. One public case with the same mechanism if the facts carry one, what happened and what matches here; no case means no case line. One or two documents to read next, named. -->

**Evidence.**
| What | Value | Source |
|---|---|---|
<!-- Six rows at most; the file name goes in this column and nowhere else in the problem. With two numbers or fewer, one sentence instead of a table. -->

## 2. {{problem_2_title}}
…

## 3. {{problem_3_title}}
…
<!-- full mode: problems 4 and 5 in the same shape -->

<!-- Code writes this section from `since_last` in the facts. -->
## Since the previous {{mode_word}} run
| Work the previous report asked for | State | Proof |
|---|---|---|
**Appeared.** / **Went away.** / **Changed because the checks changed, not the cluster.** as lists. With no earlier run: "No earlier {{mode_word}} run to compare with."

## Serious, not today
<!-- Every critical or high item that is not among today's problems, items with one cause as one line, fifteen lines at most by severity, then "N more are in section 2 of report-details.md." -->

<!-- full mode only, written by code from `analysis.area_summary`: -->
## Each area in one line
| Area | What |
|---|---|

## What this run could not see
<!-- One line per item: what was not seen, and what the reader does to see it (a full run, a token, a question `/kubegap setup` asks again). -->

<!-- From here on, code writes it. -->
## Numbers
| Severity | fail | warn | vs. previous {{mode_word}} run |
|---|---|---|---|
| critical | {{n_critical}} | {{w_critical}} | {{d_critical}} |
| high | {{n_high}} | {{w_high}} | {{d_high}} |
| medium | {{n_medium}} | {{w_medium}} | {{d_medium}} |
| low | {{n_low}} | {{w_low}} | {{d_low}} |

Checks behind each problem: 1 → `{{finding_ids}}` …

Details and every table: [`report-details.md`](report-details.md) · kubegap {{kubegap_version}}, rubric {{rubric_version}} · snapshot `{{snapshot_path}}`

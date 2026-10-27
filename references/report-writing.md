# Report writing — `report.md` (for people) and `report-details.md` (for the next run and for digging)

This file is step 7 and step 8 of `SKILL.md`. Read it fully before writing the first line of any report file, and follow every rule in it; it is not optional. The language decided in `SKILL.md` section 0 applies to everything written here.

## 7. Writing the report

A run produces two files in `$SNAP/`, in both modes:

| File | Reader | Who writes it | Shape |
|---|---|---|---|
| `report.md` | a person who runs the cluster | the LLM, from `$KUBEGAP/templates/report.md` | opening paragraph · Top N problems (daily 3, full 5), each with Problem / Evidence / Cause / Action / Why this happens / Evidence checks · since the previous run (prose) · what this run could not see · numbers table · link to details |
| `report-details.md` | the next run's agent, and anyone who wants every number | `scripts/kubegap render-details`, from the snapshot plus the fragments you write into `$SNAP/llm/` | counts, critical/high list, structured changes, absence, suppressed/tool missing/not collected, collectors run, checks evaluated, signature matches, the full first-pass table, and your fragments: adjustments, why things changed, per-area detail (full), files read, tool notes |

Order of work: analyse → write the fragments (small files) → write `report.md` → run `render-details` → run `mask` on both files → tell the user.

11. **Fragments first (`$SNAP/llm/*.md`).** Write each as a small Markdown file with a heredoc. Every fragment is in the report language. A fragment you have nothing for is still written, with one line saying so (`none` / `no adjustments`), so the next run can tell "nothing" from "forgotten".
    - `adjustments.md` — two tables, each `| finding id | first pass | final | reason |`. The first, under `### Severities`, has every status or severity you changed against the first pass (fail→pass, two or more levels, raised by a symptom or a recurrence, lowered by profile context). The second, under `### Recounted aggregates`, has **every aggregate you recounted**: whenever a number in `report.md` differs from the count, sum or list size the first pass carries for that check (its `note`, `value` or `items` in `findings-draft.json`, or the matching field in `summary.json`), write a row with the first-pass number under `first pass`, the number you wrote under `final`, and the reason you recounted (e.g. `observability.no-symptom-alerts | 19 symptom alerts | 0 | the 19 are application-metric alerts with no user-facing symptom`). A number that differs from the first pass without a row here is an error. Keep the two apart: the next run reads the first table as "the LLM's final severities" and the second as "numbers the LLM recounted, not changes in the cluster". A table with nothing in it still gets its heading and one line `none`.
    - `changes.md` — why things changed since the previous run of this mode: deploys, scale events, config changes, rubric changes ("criteria change", written apart from cluster changes), traced through `events.json` and the changed object fields. Prose, five to fifteen sentences. If there is no earlier snapshot of this mode: exactly "No earlier <mode> snapshot to compare with."
    - `areas.md` — **full mode only.** The 12 areas (resources, scaling, observability, traffic, resilience, hygiene, storage, security, cost, tenancy, node OS, platform) as `###` sections; an area with nothing to say gets one line "No findings this run (N checks pass)". Findings with one cause are one item (the grouping list is [report-grouping.md](report-grouping.md); read it once before writing). For a check with dozens of warns give the count and the top 5 — the full list is produced by code in details 7-5, so you never retype it. Where a proposal has a manifest, include the YAML fragment here. Daily mode does not write this fragment.
    - `files-read.md` — every raw path you opened directly (`objects/…`, `metrics/…`, `events.json`, `logs/…`, `tools/…`, `extra/…`), one per line.
    - `tool-notes.md` — defects or doubts about kubegap itself found in this run (false positives, summary mistakes, masker false positives, read-only commands that should become a collector), numbered, each with reproduction evidence (file, value). Continue the numbering of the previous report's tool notes (read them in the previous `report-details.md` section 7-6) and say which earlier notes are still open. A finding that disappeared because the rubric version changed is **not** a tool note (it is a criteria change in `changes.md`). A report session never fixes kubegap code (`SKILL.md` section 9).
12. **`report.md` — the Top N problems.** Pick "problems", not "actions": daily 3, full 5. Choose by severity × impact × difficulty; with an SLO, by error-budget burn. In daily mode prefer what is new or recurred, then the persisting critical/high with the largest impact. Dozens of findings with one cause are one problem ("15 prod Deployments can only land on one node" is one problem, not 15). Each problem has six parts, in this order, each one paragraph:
    - **Problem** — what is wrong, how, and the impact on users or operations right now. Name the namespace, workload and node; no check ids here.
    - **Evidence** — the three to six numbers that carry the problem, each in its own short sentence, with the source file named after the number and never in parentheses. Everything else lives in `report-details.md`; do not pile every value into this paragraph. If a value was measured while collection was running, say so.
    - **Cause** — why it came to this. When not certain, start with "Most likely," (Korean: "추정입니다.").
    - **Action** — in order ①②③; what to change, the expected effect, the effort in minutes/hours/days; a manifest fragment or the exact command where possible.
    - **Why this happens** — three short bullets, see rule 12-1.
    - **Evidence checks** — the finding ids, on one line. This is the only place ids appear in `report.md`.
12-1. **Why this happens: principle, cases, read next.** Its purpose is that the reader understands the mechanism well enough to recognize the next instance without kubegap.
    - *Principle*: the mechanism in one or two sentences — how the mechanism works and which operating rule it breaks (e.g. "A CPU limit is enforced per 100 ms scheduler period: once the quota is used the container waits for the rest of the period, which shows up as latency, not as CPU usage. The HPA scales on request, not limit, so a small request with a low limit gives you throttling and scale-out at the same time."). No analogies.
    - *Cases*: one public case, named with its year, **taken only from the check definition** (`cases`, `why`, `notes` of the related checks in `collectors/*/checks.yaml`, visible in `findings-draft.json` as `cases`/`why`/`notes`) **or from a primary document** (Kubernetes documentation, the Google SRE Book / Workbook with chapter, a cloud provider's documentation, a vendor postmortem the check cites). If none of the related checks carries a case, write "No public case recorded for this check." Never invent a source, a year or a URL; write a URL only when it is in the check definition.
    - *Read next*: two or three documents or sections the reader can look up, written as a sentence, for example: the kernel documentation on CFS bandwidth control, the Kubernetes docs on Resource Management for Pods and Containers, and chapter 4 of Google's Site Reliability Engineering book. Named documents, not links and not a quoted list.
13. **"Since the previous run" is prose, not a list.** Five to eight sentences on what appeared, went away or came back, which objects changed and why (deploy, scale, config), and one sentence per previous Top N problem saying started / done / not started with the number that proves it (the previous `report.md` of the same mode is the source). Rubric-driven appearances are named as criteria changes. With no earlier snapshot of this mode the section is the single sentence "No earlier <mode> snapshot to compare with." — no other first-run disclaimer anywhere.
14. **"What this run could not see" is one paragraph**: absent components the profile expects, checks not evaluated in this mode (daily: the count and the date of the last full run), tools missing, collection steps that failed, and measurements collection itself disturbed. Not a list of ids; the lists are in details sections 5 and 6.
15. **Numbers table** by your final severity (fail and warn columns, delta against the previous run of this mode). If final critical+high differs from the first pass by 3 or more, one sentence under the table (`history.csv` is first-pass based).
16. **Render the details.** After the fragments and `report.md` exist:
    ```bash
    $KUBEGAP/scripts/kubegap render-details --context <name> --snapshot "$SNAP"
    ```
    It prints which fragments were missing; write any you forgot and run it again. Do not edit `report-details.md` by hand — change the fragment and re-render.
17. **Save and mask — always the last command.** Both files, after rendering, after every edit:
    ```bash
    $KUBEGAP/scripts/kubegap mask "$SNAP/report.md" "$SNAP/report-details.md"
    ```
    If the reported count is not 0, check where `<masked>` remains. If you edit either file afterwards for any reason, run `mask` again. Internal IPs only individually where a finding needs them, never as a list; AWS account ids become `<account>`; Secret values appear nowhere, in no file, not even key names with values.
18. **What to show the user.** In the conversation: the two paths, which context and cluster, the numbers table with deltas, and the title plus a one-line action for each Top N problem. Do not repeat the report body. One line on tool notes if any were written. One line with commands usable next time (`/kubegap explain <id>`, `/kubegap --snapshot <date>`, `/kubegap full` when in daily mode).

## 8. Writing rules

**Tone follows the report tone rules:** state the conclusion first, one idea per sentence, plain words, make the next step obvious to the reader, and use a polite conversational register. Applied to this report:
- **No parenthetical asides.** Do not put explanations, examples, qualifiers or effort estimates in parentheses. If a term needs explaining, explain it in its own sentence, and only when a person who runs a cluster would not know it: explain "TURN server" or "CFS quota", not "Deployment", "liveness probe" or "PDB". Effort goes at the end of the action sentence as plain words: "Takes 30 minutes." Source files go after the number without parentheses: "restart count 7,876 in objects/pods.json" or as a trailing sentence "Source: objects/pods.json, events.json." Parentheses stay only inside code, ids, YAML and quoted log lines.
- When writing in Korean, end sentences in the polite conversational (haeyo) style, not the plain declarative (handa) style. When writing in English, use plain sentences addressed to the reader. Short table values, finding ids, commands and YAML stay as they are.
- Conclusion first. Describe a problem in the order "what happened → what the impact is now → what to do".
- Short sentences, one idea each. Do not chain three things with commas.
- Numbers with units, ratios as %, as in "the disk is 87% full".
- No blaming, no exclamations, no analogies. Facts and actions only.
- **English register.** US spelling (labeled, behavior, center). Money as `$365 a month`, not `365 USD`. Start an uncertain cause with "Most likely," or "Probably", never with the label "Likely:". The opening paragraph is at most four sentences; a sentence longer than about 30 words is split. No semicolons inside parentheses, no parentheses at all outside code (section above). Avoid colloquial phrasing such as "lie around" or "a shell gateway"; say "are still present", "exposes a shell".
- In `report.md` speak about things (namespace/workload/node), not about checks. Check ids live on the "Evidence checks" line and in details.

Content rules:
- No summarizing, no omissions in details: every item found in logs and code is in `report-details.md` (code produces the full lists; your fragments must not say "etc.", "…" or "and N more"). In `report.md`, selection is the point — but what is selected is written completely.
- Context first so a first-time reader understands. A term that a cluster operator would not know gets its own short sentence the first time it appears; everything else is used as is.
- No invention. Only numbers that are in the snapshot, with the source file named. Only sources that are in the check definition or a primary document.
- Write "confirmed" only for what was verified. Guesses about raw data not opened are written as "likely".
- Language (decided in `SKILL.md` section 0): if Korean was chosen, write `report.md`, every fragment and every message to the user in Korean following section 9 below, and pass `--language ko` to `render-details` so its headings and labels are Korean too; keep check ids, file paths, commands, metric names and resource names untouched. Data inside code-produced tables (evidence strings, ids, numbers) stays English. If English was chosen, write everything in English.

## Daily mode

The daily run exists so that the same person can read `report.md` every morning in five minutes. Everything above applies, with these differences:
- Top 3, not Top 5. New or recurred first, then the persisting critical/high with the largest impact.
- Fragments: `adjustments.md`, `changes.md`, `files-read.md`, `tool-notes.md`. No `areas.md`.
- Comparison is with the previous **daily** snapshot only (`diff` does this by itself). The persisting critical/high list is in details section 2; `report.md` mentions it in one sentence ("N critical/high items persist unchanged, see details").
- Checks with status `not-collected` are one sentence in "What this run could not see" with the count and the date of the last full run. They are not findings, not "tool missing", not tool notes.
- `logs.signatures` sees fewer sources in daily mode (no node journals); do not report the difference as a regression.


## 9. Writing in Korean

Korean is written, not translated. Think of the sentence a Korean SRE would say to a colleague, then write that. The template headings have fixed Korean forms (table below), the check `why`/`suggest` texts are material to rephrase, not to translate word by word, and every rule in section 8 applies unchanged (haeyo register, no parentheses anywhere in prose, no analogies). A Google reference is written in full: "Google 이 낸 『Site Reliability Engineering』 4장", never "SRE 책".

**Headings and labels.**

| English | Korean |
|---|---|
| daily audit / full audit | daily 점검 / full 점검 |
| check (the unit of the rubric) | 점검 항목. "체크" 는 id 를 인용할 때만 |
| The N problems to work on | 지금 손봐야 할 문제 N개 |
| Problem / Evidence / Cause / Action | 문제 / 근거 / 원인 / 조치 |
| Why this happens: Principle / Cases / Read next | 왜 이런 일이 생기나: 원리 / 사례 / 더 알아보기 |
| Evidence checks | 근거 체크 |
| Since the previous daily run | 지난 daily 점검 이후 |
| Progress on the previous report's problems | 지난 리포트 문제의 진행 |
| What this run could not see | 이번에 보지 못한 것 |
| Numbers | 숫자 |
| Quick fix outside the list | 목록 밖의 빠른 조치 |
| not started / started / done | 아직 손대지 않음 / 진행 중 / 끝남 |
| Nothing is on fire | 급한 장애는 없습니다 |
| first pass / final | 1차 결과 / 최종 결과 |
| expected effect | 효과 |
| measured during collection | 수집 중에 측정된 값 |

**Terms.** Use the word Korean Kubernetes engineers use, which is usually the English term in Korean letters or the English word itself. Never the dictionary translation.

| Write | Not |
|---|---|
| 오브젝트, 리소스, 레플리카, 컴포넌트, 메트릭, 임계값 | 객체, 자원, 복제본, 구성 요소, 지표, 문턱 |
| requests, limits, liveness 프로브, readiness 프로브, desired, available, Ready | 요청값, 제한값, 라이브니스, 레디니스, 원함, 가용 |
| 노드, 파드, 네임스페이스, 워크로드, 디플로이먼트 또는 Deployment, 스테이트풀셋 또는 StatefulSet | 노드 외의 번역어 |
| 스케줄링, 스로틀링, 재시작, 이벤트, 알림, 알림 규칙 | 일정 잡기, 조절, 경보(alert 는 알림) |
| 점검, 조치, 발견 사항 또는 문제, 임계값을 넘었습니다 | 감사, 액션, 판정, 문턱을 넘었어요 |
| 적용됩니다, 응답합니다, 머물러 있습니다, 올라가 있는 노드 | 집행돼요, 돌려줘요, 앉아 있어요, 품은 노드 |

**More terms, from real reports.** Write "크래시 로그를 보다", not "이유를 읽다". Write "desired 1, available 0", not "원함 1, 가용 0". Write "의존 서비스가 느려지면", not "의존을 만나요". A case is not a subject: "Buffer(2020) 사례에서는 … CPU 제한을 뺐어요", not "사례는 … 발견하고 제거했어요". Write "적용돼요" or "막아요", not "집행돼요". Write "CPU 를 순간적으로 몰아 쓰는 구간", not "폭주". Write "운영자", not "유저". Write "수집하던 시간대", not "수집 창". Write "원래 건너뛰게 되어 있어요", not "설계상 건너뛰어요". Write "CFS 주기", not "스케줄러 주기". Effects are a sentence, not a list after a colon: "이렇게 하면 쓸데없는 재시작이 없어지고 503 로그도 사라져요", never "기대 효과: 재시작 없음, 503 로그 사라짐". Section titles: "이번에 확인 못 한 것" for "What this run could not see", "번외로 금방 끝나는 것 하나" for "Quick fix outside the list".

**Do not write.** Literal English idioms ("불타는 곳", "길이 두 갈래", "소음을 만들어요"); passive calques ("~에 의해 수행된다", "~되어진다"); "~하는 것이 가능해요"; "~에 대해" where a particle does the job; sentence-initial "그러나/하지만" chains; metaphors of any kind. Numbers keep units and the Korean counter: 파드 27개, 노드 2대, 2분 7초, 87%.

**Example of the register (problem 1 of a daily report).**

> ### 1. `app-c-prod/app-c-coturn` 이 7,876번 죽었는데, 아직 아무도 크래시 로그를 안 봤습니다
> **문제.** app-c 의 TURN 서버가 노드 `node-a` 에서 CrashLoopBackOff 상태입니다. TURN 서버는 WebRTC 통화가 NAT 를 넘도록 중계하는 서버입니다. Deployment 의 available 이 0 이라 중계가 필요한 app-c 통화는 실패합니다. 2026-10-25 이후 모든 리포트에서 1번 문제였고 조치는 아직 손대지 않았습니다.
> **근거.** 재시작 7,876회, 13:34 이후 14회 늘었습니다. 출처는 objects/pods.json 입니다. BackOff 이벤트가 70분에 320건 더 쌓였고 전부 이 파드 하나입니다. 출처는 events.json 입니다. 마지막 종료는 14:43:21 KST, 종료 코드 255, 시작과 종료가 같은 초입니다.
> **원인.** 추정입니다. 1초 안에 255 로 끝나니 시작 시 설정 오류나 포트 바인딩 실패일 가능성이 큽니다. 컨테이너 로그는 kubegap 수집 범위 밖이라 정확한 메시지는 모릅니다.
> **조치.** ① 마지막 크래시 메시지를 읽습니다. `kubectl -n app-c-prod logs app-c-coturn-549854dfcb-jgp4h -c coturn --previous | tail -50`. 10분 걸립니다. ② 포트 충돌이면 `node-a` 에서 `ss -lunp | grep 3478` 로 3478 을 쓰는 프로세스를 확인합니다. 5분 걸립니다. ③ 인자를 고치고 이미지 태그를 고정하고 3478 에 tcpSocket 프로브를 붙입니다. 30분 걸립니다. 효과는 app-c 통화 복구와 시간당 약 260건의 BackOff 이벤트 중단입니다.

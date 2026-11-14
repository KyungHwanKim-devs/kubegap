# Contributing

kubegap is a read-only audit of a Kubernetes cluster: `collect` writes a snapshot, `summarize` turns it into summary.json, `evaluate` judges the checks of `collectors/*/checks.yaml`, and the report is written from that. Code lives in `lib/` in six layer packages (`foundations`, `collection`, `summaries`, `judgement`, `output`, `commands`); what to collect and what counts as a problem lives in data files next to it (`collectors/*/*.yaml`, `rubric/`, `signatures/`, `references/*.yaml`). This file is the procedure, the rules and the review checklist. The mechanics behind them, such as what the regression harness compares, what collection units and modes are, how tools are pinned, which helper lives where and how the layers may import each other, are in [`references/development.md`](references/development.md).

한국어는 아래에 있습니다. [Korean follows the English.](#기여하기)

## Adding or changing a check, end to end

1. **Write the check as data.** One entry in `collectors/<area>/checks.yaml` with `id` (`<area>.<name>`), `name`, `area`, `type` (`metric`, `summary`, `object`, `inventory`, `aws`, `absence`, `signature` or `llm`), `rule` (`expr` is true on fail, `warn_expr` on warn, `threshold` and `warn_threshold` as numbers, or a mapping with `default` and the platforms (`eks`, `k3s`, `other`) or scales (`small`, `medium`, `large`) that differ; a warn-only check writes `warn_expr` and omits `expr`), `target`, `evidence`, `severity_default` (one level, or one per scale as `{ small: …, medium: …, large: … }` when the finding weighs differently for a personal cluster and an SLA team), `nature: occurrence` when a finding is something counted over a window that may already be over (events, log lines, restarts; left out, a finding is a state the cluster is in now), `overdue: true` when a failure is a date already passed that grows while it waits (a version past its end of support), `why`, `cases` (public write-ups only) and, when you measured something on your own cluster, `measured`. The expressions are Python evaluated over the names in `lib/judgement/evaluate/context.py` `helpers()`: review them like code, and when an evidence sentence passes 500 characters put it in `lib/judgement/evaluate/evidence.py` as a helper the expression calls (a test enforces the limit).
2. **Give it its input.** A `metric` check reads a query of `collectors/<area>/metrics.yaml`; every query cites the metric names it reads in `source:` lines (`owner/repo path:line@tag` where the name is defined), and an empty result is judged by `lib/judgement/evaluate` from `metrics/series-present.json`, never counted as a pass by itself. A `summary` check reads a key of summary.json: add it in the summary module of `lib/summaries/`, document it in `references/summary-shape.md`, and when the input may be absent write `null` plus a `skip_reason` on the parent, or a read flag per row that `rule.needs` tests (`needs_reason` says what was not read). A missing input is never `0`, `false` or `[]`.
3. **Cite every fact about other software from its source.** What a tool prints, which flag it reads, what a field or metric means: find the line in the project's source at the version kubegap pins or supports, cite it as `file:line@tag` in the code comment, the YAML or the test, add the row to `references/sources.md`, and add the tag to the component's `read` list in `references/verified-versions.yaml` (then regenerate README's table: `scripts/kubegap verified --markdown` and `--language ko`, pasted between the `verified-table` markers). `--help` output, what one cluster showed and memory of how such tools usually behave are observations, and each has produced a wrong sentence here before.
4. **Write the test cases with the check.** `test.cases` holds one case per outcome (fail, warn, pass, and `expect: skip` for the missing-input shape); a `metric` check with a numeric threshold has one case exactly at the threshold; a check that compares with today's date sets `today:` in the case's `inventory` so the verdict does not move with the calendar. `scripts/kubegap selftest` builds a snapshot from each case and runs the evaluator on it.
   A check whose severity is critical or high at any scale also belongs to a learn topic, `rubric/learn/<topic>.yaml`: how the thing works (`mechanism`, with the `sources` it was read from), how the state is watched (`detect`: a metric or an alert first), how it is solved at each scale (`solutions`), public `cases`, and `reading`. Add the check to an existing topic's `checks` or write a new file; every address in it is a page you opened, and nothing is written from memory. `tests/test_learn.py` fails for a serious check without a topic.
5. **Bump what the check changes.** A new or changed check, query or summary key bumps `rubric/version` and the `rubric_version` line of `SKILL.md` (a changed log signature bumps `signatures/version` instead), regenerates `docs/CHECKS.md` (`scripts/kubegap checks --markdown > docs/CHECKS.md`), updates the check counts in `README.md` and `README.ko.md` (a test compares), and when a committed snapshot's summary, verdict or report is meant to change, runs `scripts/kubegap regress --update` and commits the new expectation so the diff shows the reviewer what moved. One line under `Unreleased` in `CHANGELOG.md` with the issue number.

## The commands and what each proves

```bash
uvx ruff check . && uvx ruff format --check .   # style and unused names; line length is 240 on purpose (one dict per line in summary modules)
uvx pytest -q                                   # the unit tests of lib/ and the structure tests (layers, helper homes, write paths, this file)
scripts/kubegap selftest                        # every check's test cases give the expected status: 0 failures, 0 checks without a test section
scripts/kubegap regress                         # the committed snapshots in tests/fixtures/ give the committed summaries, findings and report details
scripts/kubegap selftest --snapshot <snapshot>  # optional, with a real snapshot: the keys the expressions read exist in its summary.json
uvx --from skills-ref agentskills validate "$PWD"  # the skill folder is valid; run it from the parent folder when yours is not named kubegap
```

CI runs the first four on Python 3.11, 3.12, 3.13 and 3.14 (`pyproject.toml` says 3.11 or newer; only the standard library is used) and validates the skill folder with `agentskills validate`. All of them pass before a pull request is opened.

## Pull requests

- One topic per pull request, at most two issues, each named in the body and the last line `Closes #<number>`.
- The title is `English / 한국어` and the body is English first; the maintainer writes the Korean half below it, a contributor may. The body has four parts: the problem, what changed, the result, what was verified. Write what you found before what you changed: which file and line, what the issue got right or wrong, and what you ran. If you ran it against a real cluster, say which kind and what you saw.
- Data (`collectors/`, `rubric/`, `signatures/`, `references/*.yaml`), code and documentation go in separate commits when a change touches more than one; it makes the review easier and the history stays on the pull request page. Pull requests are squash-merged into one commit on `main`, titled after the pull request, and your commit identity is kept as the author.
- Pick an open issue and say so in a comment, so two people do not start the same one; issues labelled `good first issue` need no cluster. Branch name `fix/<issue number>-<a few words>`.
- The first pull request from a fork does not run CI by itself: GitHub waits for a maintainer to approve the workflow run. Run the commands above locally; the maintainer approves and runs CI before merging, and may push a small follow-up commit onto your branch.

## Facts, helpers and boundaries

- **Facts come from source at the pinned version** (step 3 above); what cannot be found is marked unverified with the reason.
- **Before adding a helper, look for it.** Every small job has one home under `lib/foundations/`; the list of homes by job is the "Before adding a helper" paragraph of `references/development.md`, and `tests/test_helper_homes.py` fails on a second copy of a job that has one.
- **Layers import downward only.** A module imports its own layer package and the ones below it as `references/development.md` states, a `summaries` module never a sibling, a sub-package part never its `__init__`; `tests/test_boundaries.py` fails on an import against this.
- **Interfaces change without aliases.** A summary key, a config key or a metric query id that is renamed or removed keeps the new form only: no alias, no deprecation period; the rubric version moves and the CHANGELOG names the old and the new spelling. A renamed or removed snapshot file, or a key a reader starts to require, bumps `SCHEMA_VERSION` in `lib/foundations/paths.py`, and a snapshot of another version is refused and collected again.
- **Generated files are regenerated, not edited:** `docs/CHECKS.md`, the `verified-table` blocks of `README.md` and `README.ko.md`, the `tools-table` blocks of `docs/SETUP.md` and `docs/ko/SETUP.md`, `deploy/node-access/COMMANDS.md` and `deploy/permissions/ssm-document.yaml` (`scripts/kubegap checks --markdown`, `scripts/kubegap verified --markdown`, `scripts/kubegap tools --markdown`, `scripts/kubegap node-commands --markdown` and `--ssm-document`; the README and SETUP blocks take `--language ko` for the Korean one); a test fails when one is stale. A tool entry of `lib/commands/tools.py` names the checks it feeds as `<area>.<id>`, `<area>.*`, `<area>.*@full` (the full-mode-only checks of that area) or `*`, and a change to a tool regenerates the two SETUP tables. When a parser needs a ConfigMap value, add the key to `KEEP_VALUES` in `lib/foundations/scrub.py`; every other value is replaced by its length and shape before the snapshot is written.

## Review checklist

Maintainers and the review agent go through the same list, in this order, and the review says what was checked and how.

1. **Project intent:** read-only (no apply, delete, scale, patch or exec), no Secret value read or recorded, deterministic (every age from the snapshot's time, no wall clock in a summary), never a false pass (an unread input skips with a reason, an empty metric result is judged against `series-present.json`), standard library only.
2. **User intent of the issue:** what the issue asked for in its own words, and whether the change does that and not something nearby.
3. **Root cause, not a patch:** the change removes the cause, not the symptom; no special case, alias, fallback or "older snapshot" branch added to keep something working.
4. **Issue text verified:** the numbers, file names and claims in the issue were measured against the code, and the pull request says where the issue was wrong.
5. **What the change does not do:** stated in the pull request, so the reader does not assume it.
6. **Every external claim cited:** `file:line@tag` at the pinned or supported version, a row in `references/sources.md`, the tag in `references/verified-versions.yaml`; nothing stated from `--help` output, one cluster's behaviour or memory.
7. **Tests the reviewer ran:** the five commands above, and the regression diff read when the expectation changed.
8. **Existing helper reused or the new one justified:** the home list above was searched; a new helper has one home, a test and no duplicate.
9. **No boundary crossed:** no import against the layer rule, no part importing its sub-package's `__init__`.
10. **No interface changed silently:** a summary key, config key, query id, snapshot file or check that changed is in the CHANGELOG with its version bump.

## Rules

- kubegap is read-only. Do not add commands that change the cluster.
- Secret values are never read or recorded anywhere; names, types and key names only. The one exception is `helm list`, which reads Helm's own release records stored in Secrets; only release metadata is kept, and `helm get values` is never run. Raw component logs are deleted once `summarize` has aggregated them.
- Raw cluster data (snapshots), personal configuration (`config.yaml`) and tool binaries (`.tools/`) are not committed (`.gitignore`).
- The YAML files are read by `lib/foundations/yamlite.py`, which supports only a subset of YAML, listed at the top of that file: no anchors, aliases or tags, and a plain string stays on one line (use a `>` block or quotes for long text).
- README.md and README.ko.md do not use parentheses for asides; write a second sentence instead. The same rule applies to the reports.
- Commit messages: at least one line in English saying what changed and why.
- The code and documentation here were written with coding agents. What to collect, what counts as a problem, and which verdicts were wrong on real clusters were decided by the author. Contributions made the same way are welcome; the review bar is the same either way.

---

# 기여하기

kubegap 은 Kubernetes 클러스터를 읽기 전용으로 점검합니다. `collect` 가 스냅샷을 쓰고, `summarize` 가 summary.json 으로 바꾸고, `evaluate` 가 `collectors/*/checks.yaml` 의 체크를 판정하고, 그 결과로 리포트를 씁니다. 코드는 `lib/` 의 층 패키지 여섯(`foundations`·`collection`·`summaries`·`judgement`·`output`·`commands`)에 있고, 무엇을 모으고 무엇을 문제로 치는지는 그 옆의 데이터 파일(`collectors/*/*.yaml`·`rubric/`·`signatures/`·`references/*.yaml`)에 있습니다. 이 파일은 절차와 규칙과 리뷰 체크리스트입니다. 그 뒤의 기계적인 것, 곧 회귀 하네스가 무엇을 비교하는지, 수집 단위와 모드가 무엇인지, 도구를 어떻게 고정하는지, 어느 헬퍼가 어디 사는지, 층이 서로 무엇을 import 해도 되는지는 [`references/development.md`](references/development.md) 에 있습니다.

## 체크를 더하거나 고치는 절차, 끝까지

1. **체크를 데이터로 씁니다.** `collectors/<area>/checks.yaml` 에 항목 하나: `id`(`<area>.<name>`), `name`, `area`, `type`(`metric`·`summary`·`object`·`inventory`·`aws`·`absence`·`signature`·`llm`), `rule`(`expr` 가 참이면 fail, `warn_expr` 가 참이면 warn, `threshold`·`warn_threshold` 는 숫자, 또는 `default` 와 값이 다른 플랫폼(`eks`·`k3s`·`other`)이나 규모(`small`·`medium`·`large`)를 적은 맵; warn 만 내는 체크는 `warn_expr` 만 쓰고 `expr` 를 뺍니다), `target`, `evidence`, `severity_default`(한 단계, 또는 개인 클러스터와 SLA 가 있는 팀에서 무게가 다른 항목이면 `{ small: …, medium: …, large: … }` 로 규모별), `nature: occurrence`(이벤트·로그 줄·재시작처럼 기간 안에 센 것이라 이미 끝났을 수 있는 항목일 때; 적지 않으면 지금 클러스터가 놓인 상태), `overdue: true`(fail 이 이미 지난 기한이고 기다릴수록 커지는 항목일 때: 지원이 끝난 버전), `why`, `cases`(공개된 사고 기록만), 그리고 자기 클러스터에서 잰 것이 있으면 `measured`. 식은 `lib/judgement/evaluate/context.py` 의 `helpers()` 이름들 위에서 평가되는 Python 입니다. 코드처럼 리뷰하고, 근거 문장이 500자를 넘으면 `lib/judgement/evaluate/evidence.py` 에 헬퍼로 두고 식에서는 부르기만 합니다(테스트가 상한을 지킵니다).
2. **입력을 줍니다.** `metric` 체크는 `collectors/<area>/metrics.yaml` 의 질의를 읽습니다. 질의마다 읽는 메트릭 이름을 `source:` 줄(`owner/repo path:line@tag`, 그 이름이 정의된 줄)로 인용하고, 빈 결과는 `lib/judgement/evaluate` 가 `metrics/series-present.json` 으로 판단하지 그 자체로 pass 가 되지 않습니다. `summary` 체크는 summary.json 의 키를 읽습니다. `lib/summaries/` 의 요약 모듈에 키를 더하고 `references/summary-shape.md` 에 적으며, 입력이 없을 수 있으면 부모에 `null` 과 `skip_reason` 을, 또는 행마다 읽음 플래그를 두고 `rule.needs` 가 그것을 봅니다(`needs_reason` 이 무엇을 못 읽었는지 말합니다). 없는 입력은 절대 `0`·`false`·`[]` 가 아닙니다.
3. **다른 소프트웨어에 대한 사실은 전부 소스에서 인용합니다.** 도구가 무엇을 찍는지, 어느 플래그를 읽는지, 필드나 메트릭이 무엇을 뜻하는지: kubegap 이 고정하거나 지원하는 버전의 소스에서 그 줄을 찾아 코드 주석·YAML·테스트에 `file:line@tag` 로 적고, `references/sources.md` 에 행을 더하고, `references/verified-versions.yaml` 의 그 구성 요소 `read` 목록에 태그를 더합니다(그 뒤 README 표 재생성: `scripts/kubegap verified --markdown` 과 `--language ko`, `verified-table` 표시 사이에 붙여 넣기). `--help` 출력, 클러스터 하나에서 본 것, 보통 이렇게 동작한다는 기억은 관찰이고, 각각 여기서 틀린 문장을 낸 적이 있습니다.
4. **테스트 케이스를 체크와 함께 씁니다.** `test.cases` 는 결과마다 하나(fail, warn, pass, 입력 없는 모양은 `expect: skip`); 숫자 임계값이 있는 `metric` 체크는 정확히 임계값인 케이스 하나; 오늘 날짜와 비교하는 체크는 케이스의 `inventory` 에 `today:` 를 두어 달력이 가도 판정이 안 움직이게 합니다. `scripts/kubegap selftest` 가 케이스마다 스냅샷을 만들어 평가기를 돌립니다.
   어느 규모에서든 심각도가 critical 이나 high 인 체크는 배우는 주제 `rubric/learn/<topic>.yaml` 하나에 들어가야 합니다. 주제에는 어떻게 움직이는지(`mechanism` 과 그것을 읽은 `sources`), 무엇으로 지켜보는지(`detect`: 메트릭이나 알림이 먼저), 규모별로 어떻게 푸는지(`solutions`), 공개 사례(`cases`), 더 읽을 것(`reading`)을 적습니다. 기존 주제의 `checks` 에 체크를 더하거나 새 파일을 씁니다. 적는 주소는 전부 직접 열어 읽은 페이지이고 기억으로 쓰지 않습니다. 주제가 없는 심각한 체크는 `tests/test_learn.py` 가 잡습니다.
5. **체크가 바꾸는 것을 올립니다.** 새 체크나 바뀐 체크·질의·요약 키는 `rubric/version` 과 `SKILL.md` 의 `rubric_version` 줄을 올리고(로그 시그니처가 바뀌면 대신 `signatures/version`), `docs/CHECKS.md` 를 다시 만들고(`scripts/kubegap checks --markdown > docs/CHECKS.md`), `README.md`·`README.ko.md` 의 체크 수를 고치며(테스트가 대조), 커밋된 스냅샷의 요약·판정·리포트가 바뀌어야 하는 변경이면 `scripts/kubegap regress --update` 를 돌려 새 기대값을 같이 커밋해 diff 가 리뷰어에게 무엇이 움직였는지 보여 줍니다. `CHANGELOG.md` 의 `Unreleased` 에 이슈 번호와 함께 한 줄.

## 명령 다섯과 각각이 증명하는 것

```bash
uvx ruff check . && uvx ruff format --check .   # 스타일과 안 쓰는 이름; 줄 길이 240 은 일부러(요약 모듈은 한 줄에 dict 하나)
uvx pytest -q                                   # lib/ 의 단위 테스트와 구조 테스트(층, 헬퍼의 집, 쓰기 경로, 이 파일)
scripts/kubegap selftest                        # 모든 체크의 테스트 케이스가 기대한 상태를 냄: 실패 0, 테스트 절 없는 체크 0
scripts/kubegap regress                         # tests/fixtures/ 의 커밋된 스냅샷이 커밋된 요약·판정·리포트 상세를 냄
scripts/kubegap selftest --snapshot <snapshot>  # 선택, 실제 스냅샷으로: 식이 읽는 키가 그 summary.json 에 있는지
uvx --from skills-ref agentskills validate "$PWD"  # 스킬 폴더가 유효한지; 폴더 이름이 kubegap 이 아니면 부모 폴더에서 돌립니다
```

CI 는 앞의 넷을 Python 3.11·3.12·3.13·3.14 에서 돌리고(`pyproject.toml` 은 3.11 이상, 표준 라이브러리만) 스킬 폴더를 `agentskills validate` 로 검증합니다. 전부 통과한 뒤 pull request 를 엽니다.

## Pull request

- PR 하나에 주제 하나, 이슈는 둘까지, 본문에 각각 적고 마지막 줄은 `Closes #<번호>`.
- 제목은 `English / 한국어`, 본문은 영어 먼저. 그 아래 한국어는 유지관리자가 쓰고 기여자는 써도 됩니다. 본문은 네 부분: 문제, 바뀐 것, 결과, 확인한 것. 고친 것보다 찾은 것을 먼저 씁니다: 어느 파일 어느 줄, 이슈가 맞고 틀린 것, 무엇을 돌렸는지. 실제 클러스터에서 돌렸으면 어떤 종류였고 무엇을 봤는지.
- 데이터(`collectors/`·`rubric/`·`signatures/`·`references/*.yaml`)·코드·문서는 한 변경이 둘 이상에 걸치면 커밋을 나눕니다. 리뷰가 쉬워지고 이력은 PR 페이지에 남습니다. PR 은 `main` 에 커밋 하나로 squash 머지되고 제목은 PR 제목을 따르며, 기여자의 커밋 신원이 저자로 남습니다.
- 열린 이슈를 고르고 댓글로 말해 두 사람이 같은 일을 시작하지 않게 합니다. `good first issue` 라벨이 붙은 이슈는 클러스터가 필요 없습니다. 브랜치 이름은 `fix/<이슈 번호>-<몇 단어>`.
- fork 에서 온 첫 PR 은 CI 가 저절로 돌지 않습니다. GitHub 이 유지관리자의 워크플로 승인을 기다립니다. 위 명령을 로컬에서 돌리세요. 유지관리자가 승인해 CI 를 돌린 뒤 머지하고, 브랜치에 작은 후속 커밋을 올릴 수 있습니다.

## 사실, 헬퍼, 경계

- **사실은 고정 버전의 소스에서**(위 3번). 못 찾은 것은 이유와 함께 unverified 로 표시합니다.
- **헬퍼를 더하기 전에 찾습니다.** 작은 일마다 `lib/foundations/` 에 집이 하나 있습니다. 일마다의 집 목록은 `references/development.md` 의 "Before adding a helper" 문단에 있고, 집이 있는 일의 둘째 사본은 `tests/test_helper_homes.py` 가 잡습니다.
- **층은 아래로만 import 합니다.** 모듈은 `references/development.md` 가 적은 대로 자기 층 패키지와 그 아래만 import 하고, `summaries` 모듈은 형제를, 하위 패키지의 조각은 `__init__` 을 import 하지 않습니다. 이를 거스르는 import 는 `tests/test_boundaries.py` 가 잡습니다.
- **인터페이스는 별칭 없이 바뀝니다.** 이름이 바뀌거나 없어진 요약 키·설정 키·메트릭 질의 id 는 새 꼴만 남습니다. 별칭 없음, 유예 기간 없음. 룰 버전이 오르고 CHANGELOG 가 옛 이름과 새 이름을 적습니다. 스냅샷 파일이 바뀌거나 없어지거나 리더가 키를 요구하기 시작하면 `lib/foundations/paths.py` 의 `SCHEMA_VERSION` 을 올리고, 다른 버전의 스냅샷은 거부되어 다시 수집됩니다.
- **생성 파일은 손으로 고치지 않고 다시 만듭니다:** `docs/CHECKS.md`, `README.md`·`README.ko.md` 의 `verified-table` 블록, `docs/SETUP.md`·`docs/ko/SETUP.md` 의 `tools-table` 블록, `deploy/node-access/COMMANDS.md`, `deploy/permissions/ssm-document.yaml`(`scripts/kubegap checks --markdown`·`scripts/kubegap verified --markdown`·`scripts/kubegap tools --markdown`·`scripts/kubegap node-commands --markdown` 과 `--ssm-document`; README 와 SETUP 블록의 한국어는 `--language ko`). 낡으면 테스트가 실패합니다. `lib/commands/tools.py` 의 도구 항목은 먹이는 체크를 `<area>.<id>`·`<area>.*`·`<area>.*@full`(그 영역의 full 모드 전용 체크)·`*` 로 적고, 도구가 바뀌면 SETUP 표 둘을 다시 만듭니다. 파서가 ConfigMap 값을 읽어야 하면 `lib/foundations/scrub.py` 의 `KEEP_VALUES` 에 키를 더합니다. 다른 모든 값은 스냅샷에 쓰기 전에 길이와 모양으로 바뀝니다.

## 리뷰 체크리스트

유지관리자와 리뷰 에이전트가 같은 목록을 같은 순서로 보고, 리뷰는 무엇을 어떻게 확인했는지 적습니다.

1. **프로젝트 의도:** 읽기 전용(apply·delete·scale·patch·exec 없음), Secret 값을 읽거나 기록하지 않음, 결정론(모든 나이는 스냅샷 시각 기준, 요약에 벽시계 없음), 거짓 pass 없음(못 읽은 입력은 이유와 함께 skip, 빈 메트릭 결과는 `series-present.json` 으로 판단), 표준 라이브러리만.
2. **이슈의 유저 의도:** 이슈가 자기 말로 요구한 것, 그리고 변경이 옆의 다른 것이 아니라 그것을 하는지.
3. **땜질이 아니라 원인:** 증상이 아니라 원인을 없앴는지, 무언가를 살리려고 특수 분기·별칭·폴백·"옛 스냅샷" 분기를 더하지 않았는지.
4. **이슈 본문 검증:** 이슈의 숫자·파일명·주장을 코드에 대조했고 PR 이 이슈가 틀린 곳을 말하는지.
5. **하지 않은 것:** PR 에 적혀 있어 읽는 사람이 짐작하지 않아도 되는지.
6. **외부 주장은 전부 인용:** 고정 또는 지원 버전의 `file:line@tag`, `references/sources.md` 행, `references/verified-versions.yaml` 의 태그. `--help` 출력·클러스터 하나의 동작·기억으로 적은 것 없음.
7. **리뷰어가 돌린 테스트:** 위 명령 다섯, 그리고 기대값이 바뀌었으면 회귀 diff 를 읽었는지.
8. **기존 헬퍼 재사용 또는 새 헬퍼의 근거:** 위 집 목록을 찾아봤는지, 새 헬퍼는 집 하나·테스트·중복 없음인지.
9. **경계를 넘지 않음:** 층 규칙을 거스르는 import 없음, 하위 패키지의 조각이 `__init__` 을 import 하지 않음.
10. **인터페이스가 조용히 바뀌지 않음:** 바뀐 요약 키·설정 키·질의 id·스냅샷 파일·체크가 버전 올림과 함께 CHANGELOG 에 있는지.

## 규칙

- kubegap 은 읽기 전용입니다. 클러스터를 바꾸는 명령을 더하지 않습니다.
- Secret 값은 어디에도 읽거나 기록하지 않습니다. 이름·종류·키 이름만. 유일한 예외는 Helm 이 Secret 에 두는 자기 릴리스 기록을 읽는 `helm list` 이고, 릴리스 메타데이터만 남기며 `helm get values` 는 돌리지 않습니다. 원본 컴포넌트 로그는 `summarize` 가 집계한 뒤 지웁니다.
- 원본 클러스터 데이터(스냅샷), 개인 설정(`config.yaml`), 도구 바이너리(`.tools/`)는 커밋하지 않습니다(`.gitignore`).
- YAML 파일은 `lib/foundations/yamlite.py` 가 읽고 YAML 의 일부만 지원합니다. 그 파일 머리에 목록이 있습니다: 앵커·별칭·태그 없음, 평문 문자열은 한 줄에(긴 글은 `>` 블록이나 따옴표).
- README.md 와 README.ko.md 는 괄호로 덧말을 달지 않고 문장을 하나 더 씁니다. 리포트도 같습니다.
- 커밋 메시지: 무엇을 왜 바꿨는지 영어 한 줄 이상.
- 여기의 코드와 문서는 코딩 에이전트와 함께 썼습니다. 무엇을 모을지, 무엇을 문제로 칠지, 어떤 판정이 실제 클러스터에서 틀렸는지는 저자가 정했습니다. 같은 방식의 기여를 환영하며 리뷰 기준은 어느 쪽이든 같습니다.

"""Render `report-details.md`: the reference half of a report, assembled by code from the snapshot files plus the `analysis` block of the facts.

A report has two files. `report.md` is for people: `scripts/kubegap write-report` writes it from `llm/facts.json` with separate agents. `report-details.md`
is for the next run's agent and for anyone who wants to dig: every table that can be produced mechanically is produced here (counts, critical/high list,
absence, suppressed, collectors run, checks evaluated, signature matches, the full first-pass table), and the parts that need judgment come from the
`analysis` block the LLM wrote into `llm/facts.json` (references/facts-<language>.md):

  analysis.severity_changes   final severity/status changes against the first pass, with reasons
  analysis.recounts           every aggregate the LLM recounted against the first pass, with reasons
  analysis.why_changed        why things changed since the previous run of the same mode (narrative)
  analysis.areas              per-area detail (full mode), one entry per area
  analysis.files_read         raw files the LLM opened directly, and commands_outside_snapshot
  analysis.tool_notes         defects or doubts about kubegap itself, with reproduction evidence

An empty field renders as "(not written this run)" so the file is always complete and the next run can tell what was skipped.
Headings, labels, table headers and fixed sentences follow the report language (`--language`); evidence strings and check texts inside tables
stay English because they come from the check definitions. A cell cut to fit a table ends at a word (`_cut`). Masking (`scripts/kubegap mask`) runs after rendering.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import re
from pathlib import Path

from . import __version__, paths
from .snapshot import load_json, write_private

SEVERITIES = ("critical", "high", "medium", "low", "info")
ANALYSIS_FIELDS = ("severity_changes", "recounts", "why_changed", "areas", "files_read", "tool_notes")
AREAS = ("resources", "scaling", "observability", "traffic", "resilience", "hygiene", "storage", "security", "cost", "tenancy", "node OS", "platform")

# Headings and fixed phrases per language. English is the key; a language without an entry falls back to the key.
LABELS: dict[str, dict[str, str]] = {
    "en": {},
    "ko": {
        "title": "# kubegap 상세 리포트 — {cluster} (`{context}`), {mode} 점검",
        "intro": "사람이 먼저 읽을 리포트는 옆의 `report.md`예요. 이 파일에는 판정 전체와 표가 있고, `scripts/kubegap render-details`가 수집 자료와 에이전트가 사실 파일에 쓴 분석 기록을 모아 만들어요. 다음 점검의 에이전트도 이 파일을 읽어요. 점검 항목 id와 근거 문장은 정의에서 그대로 가져와서 영어예요.",
        "Item": "항목",
        "Value": "값",
        "kube context / cluster": "kube context / 클러스터",
        "Run time / mode": "실행 시각 / 모드",
        "Profile": "프로파일",
        "kubegap / rubric / signatures": "kubegap / 점검 항목 버전 / 로그 시그니처 버전",
        "Verified against": "검증한 버전 범위",
        "(no component version read)": "(읽은 구성 요소 버전 없음)",
        "Nodes / namespaces / pods / CRDs": "노드 / 네임스페이스 / 파드 / CRD",
        "Components": "컴포넌트",
        "Metrics store": "메트릭 저장소",
        "Log store": "로그 저장소",
        "Node access": "노드 접속",
        "Snapshot": "수집 폴더",
        "(collection {seconds} s, {skipped} steps skipped by mode, {failed} failed)": "(수집 {seconds}초, 모드 때문에 건너뛴 단계 {skipped}개, 실패 {failed}개)",
        "none (Loki not found)": "없음 (Loki를 찾지 못했어요)",
        "none": "없음",
        "SSM unregistered {n}": "SSM 미등록 {n}대",
        "## 1. Counts (first pass) and the LLM's adjustments": "## 1. 자동 판정 집계와 에이전트 조정",
        "Severity (default)": "심각도(기본값)",
        "vs. previous run of this mode": "같은 모드의 지난 점검 대비",
        "no previous run of this mode": "같은 모드의 지난 점검 없음",
        "Checks {total}: evaluated {done}, disabled by profile {disabled}, skipped {skip}, not collected in this mode {nc}, errors {error}, tool missing {tool}, LLM-judged {llm}. Suppressed findings {suppressed}.": "점검 항목 {total}개 중 판정 {done}개, 프로파일에서 끈 것 {disabled}개, 건너뜀 {skip}개, 이 모드에서 수집 안 함 {nc}개, 오류 {error}개, 도구 없음 {tool}개, 에이전트 판정 {llm}개예요. 숨긴 항목은 {suppressed}개예요.",
        "### 1-1. Final judgment vs. first pass (adjustments)": "### 1-1. 자동 판정과 최종 판정이 다른 곳",
        "## 2. Critical and high failing now (first pass)": "## 2. 지금 fail인 critical과 high (자동 판정)",
        "Finding": "항목",
        "Severity": "심각도",
        "Consecutive runs": "연속 횟수",
        "Evidence": "근거",
        "(consecutive-run counts need diff.json; none for this snapshot)": "(연속 횟수는 diff.json이 있어야 나와요. 이번 점검에는 없어요)",
        "## 3. Changes since the previous run of this mode": "## 3. 같은 모드의 지난 점검 이후 변화",
        "Compared `{a}` → `{b}` (rubric {ra} → {rb}).": "`{a}`와 `{b}`를 비교했어요. 점검 항목 버전은 {ra}에서 {rb}로 바뀌었어요.",
        "New": "새로 생김",
        "Resolved": "해결됨",
        "Changed": "바뀜",
        "Rename suspects": "이름이 바뀐 것으로 보임",
        "Objects": "오브젝트",
        "added {a}, removed {r}, changed {c}": "추가 {a}개, 삭제 {r}개, 변경 {c}개",
        "Warning events": "Warning 이벤트",
        "no change": "변화 없음",
        "Persisted (Toil)": "계속 남아 있는 항목",
        "{all} findings present in all {runs} runs checked, {three} in 3 or more; top checks: ": "최근 {runs}번 모두 나온 항목 {all}개, 3번 이상 나온 항목 {three}개예요. 많이 나온 점검 항목: ",
        "### 3-1. Why things changed": "### 3-1. 왜 바뀌었나",
        "## 4. Detail per area": "## 4. 영역별 상세",
        "## 5. Absence list": "## 5. 없는 것 목록",
        "Status": "상태",
        "Why it should exist": "필요한 이유",
        "Proposal": "제안",
        "Expected families missing (inventory): {families}.": "있어야 하는데 없는 도구 종류: {families}.",
        "## 6. Suppressed, tool missing, not collected": "## 6. 숨긴 항목, 도구 없음, 수집 안 함",
        "Suppressed": "숨긴 항목",
        "Suppression expired": "숨김 기한이 지난 항목",
        "Tool missing": "도구 없음",
        "Not collected in {mode} mode": "{mode} 모드에서 수집 안 함",
        "Skipped or errored": "건너뛰었거나 오류가 난 점검 항목",
        "Judged in part": "일부만 판정한 점검 항목",
        "some targets lacked what the rule needs; those are not judged, not passed": "판정에 필요한 자료가 없는 대상은 판정하지 않았고 통과로 세지 않았어요",
        "until": "기한",
        "not judged": "판정 안 함",
        "Query returned no series": "질의 결과가 빈 항목",
        "every metric name the query reads has series, so nothing happened; a name with no series would be a skip": "질의가 읽는 메트릭 이름이 모두 있으므로 그런 일이 없었다는 뜻이에요. 이름 자체가 없으면 건너뜀으로 처리해요",
        "## 7. Appendix": "## 7. 부록",
        "### 7-1. Collectors and steps run": "### 7-1. 실행한 수집기와 단계",
        "Collector": "수집기",
        "Steps": "단계",
        "Failed": "실패",
        "Skipped (reason)": "건너뜀 (이유)",
        "Kinds the ClusterRole does not grant ({n}; a check that needs one of them is skipped, not passed): ": "ClusterRole에 없는 종류 {n}개예요. 이 종류가 필요한 점검 항목은 통과가 아니라 건너뜀으로 처리해요: ",
        "Kinds this cluster does not serve ({n}; a check that needs one of them is skipped, not passed): ": "이 클러스터가 제공하지 않는 종류 {n}개예요. 이 종류가 필요한 점검 항목은 통과가 아니라 건너뜀으로 처리해요: ",
        "Kinds this cluster serves but the snapshot has no file for ({n}; kubegap looked for the wrong file name, a kubegap defect, and the checks that read them judged nothing): ": "이 클러스터가 제공하는데 수집 폴더에 파일이 없는 종류 {n}개예요. kubegap이 파일 이름을 잘못 찾은 kubegap 결함이고, 그 파일을 읽는 점검 항목은 아무것도 판단하지 않았어요: ",
        "{commands} commands, {seconds} s. Failed steps: {n}": "명령 {commands}개, {seconds}초. 실패한 단계 {n}개",
        "Commands that failed inside a step that still succeeded (run.log): {n}: ": "단계는 성공했지만 그 안에서 실패한 명령 {n}개 (run.log): ",
        "{tool} {ok} of {total} Lists answered ({failed} refused or not served)": "{tool} List {total}번 중 {ok}번 응답 ({failed}번은 거부되었거나 없는 API)",
        "{tool} {ok} of {total} object kinds saved ({failed} not permitted or failed)": "{tool} 오브젝트 종류 {total}개 중 {ok}개 저장 ({failed}개는 권한이 없거나 실패)",
        "Deprecated-API tools: ": "지원 종료 API 도구: ",
        "### 7-2. Checks evaluated": "### 7-2. 판정한 점검 항목",
        "{total} checks: {counts}. Load errors: {errors}.": "점검 항목 {total}개: {counts}. 불러오기 오류: {errors}.",
        "### 7-3. Signature matches and unclassified errors": "### 7-3. 로그 시그니처 일치와 분류 안 된 오류",
        "Signature catalog {version}, {files} files, {lines} lines scanned (components: {components}). Unclassified error lines: {unclassified}.": "로그 시그니처 {version}으로 파일 {files}개, {lines}줄을 읽었어요 (컴포넌트: {components}). 분류 안 된 오류는 {unclassified}줄이에요.",
        "Signature": "시그니처",
        "Component": "컴포넌트",
        "Area": "영역",
        "Count": "횟수",
        "First, last": "처음, 마지막",
        "Sample": "샘플",
        "Normalized message": "메시지 형태",
        "Files": "파일",
        "### 7-4. Raw files the LLM read directly": "### 7-4. 에이전트가 직접 읽은 원본 파일",
        "### 7-5. Full first-pass status (every fail and warn, code results as-is)": "### 7-5. 자동 판정 전체 (모든 fail과 warn, 코드 결과 그대로)",
        "Default severity": "기본 심각도",
        "### 7-6. Tool notes (about kubegap itself)": "### 7-6. 도구 메모 (kubegap 자체에 대한 것)",
        "(not written this run)": "(이번 점검에서 쓰지 않음)",
        "First pass": "자동 판정",
        "Final": "최종",
        "Reason": "이유",
        "### 1-2. Aggregates the LLM recounted": "### 1-2. 에이전트가 다시 센 숫자",
        "Command": "명령",
        "Saved as": "저장 파일",
        "Read-only commands run outside the snapshot": "스냅샷 밖에서 실행한 읽기 전용 명령",
        "still open from note {n}": "메모 {n}에서 이어짐",
        "(daily mode: no per-area detail; see section 2 and `report.md`)": "(daily 점검에는 영역별 상세가 없어요. 2절과 `report.md`를 보세요)",
        "No earlier {mode} snapshot to compare with.": "비교할 이전 {mode} 점검이 없어요.",
        "### 3-0. Criteria changes, not cluster changes": "### 3-0. 클러스터가 아니라 점검 항목이 바뀐 것",
        "These findings appeared, disappeared or changed because the checks did, not the cluster, and they are kept out of the lists above. Taken from `diff.json` `findings.criteria_changes`; the report writes them as a criteria change and never as a tool defect.": "클러스터가 아니라 점검 항목이 바뀌어서 생기거나 사라진 결과예요. 위 목록에서는 뺐어요. `diff.json`의 `findings.criteria_changes`에서 가져왔고, 리포트에서는 기준 변경으로 다뤄요.",
        "Checks absent or gated off in the previous run": "지난 점검에 없었거나 돌지 않은 항목",
        "Checks absent or gated off in this run": "이번 점검에 없거나 돌지 않은 항목",
        "Checks whose rule changed between the runs": "두 점검 사이에 판정 규칙이 바뀐 항목",
        "Checks whose thresholds in force changed": "적용된 임계값이 바뀐 항목",
        "The two runs were made with different versions ({changes}); a key or a query renamed between them is a difference of the tool, not of the cluster.": "두 점검을 만든 버전이 달라요({changes}). 그 사이에 이름이 바뀐 키나 질의는 클러스터가 아니라 도구가 달라진 거예요.",
        "Metric queries only in the previous run": "지난 점검에만 있는 메트릭 질의",
        "Metric queries only in this run": "이번 점검에만 있는 메트릭 질의",
        "The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`.": "표의 근거는 칸에 맞게 줄였어요. 판정에 쓴 자료 전체는 아래에 항목별로 접혀 있고, `findings-draft.json`의 `details`와 같아요.",
    },
}


def _cut(text, limit: int) -> str:
    """Text for a table cell, cut at the last word that fits so a cell never ends in the middle of a word. The full text stays in the folded details or the check definition."""
    s = str(text or "")
    if len(s) <= limit:
        return s
    head = s[:limit]
    return (head.rsplit(" ", 1)[0] if " " in head else head).rstrip(" ,;:") + " …"


def _evidence(f: dict, limit: int) -> str:
    """The evidence cell: the check's text cut for the table, then the open tracker issues of the check, so a reader sees `known issue #15` next to the finding."""
    ev = f.get("evidence") or ""
    ev = ev if isinstance(ev, str) else str(ev)
    tag = ", ".join(f"#{k.get('issue')}" for k in (f.get("known_issues") or []) if isinstance(k, dict))
    return _cut(ev, limit) + (f" known issue {tag}" if tag else "")


# `<masked>`, `<account>`, `<ip>` are what lib/mask.py writes into log samples; `<none>`, `<unknown>`, `<unset>`, `<nil>`, `<invalid>` are what kubectl prints for an empty value. Any other `<` that starts a tag or an autolink gets a space after it
_TAG_START = re.compile(r"<(?!(?:masked|account|ip|none|unknown|unset|nil|invalid|n|ts|id|uuid|hex|addr)>)(?=[A-Za-z/!?])")


def cell(v) -> str:
    """A table cell from a cluster string, for every Markdown table code writes (lib/writer uses it too). No code path writes Markdown in a cell, so every piece of syntax that could make the cell live in a viewer is
    broken: pipes and newlines (the table itself), `[x](target)` links and `![x](target)` images whatever the target (javascript:, file:, data:, a
    remote image a viewer would fetch), and `<` starting a tag or an autolink (`<a href=…>`, `<script>`, `<javascript:…>`). A bare https://… stays
    plain text, which GFM viewers autolink on their own; the placeholders that mask.py and kubectl write in angle brackets are kept as they are."""
    s = str(v if v is not None else "")
    s = s.replace("|", "\\|").replace("\n", " ")
    s = s.replace("](", "] (").replace("![", "! [")
    return _TAG_START.sub("< ", s)


def _fence(text: str) -> str:
    """The backtick run that opens and closes a code block around `text`: one longer than the longest run inside it, at least three, so a pod
    name, annotation or log sample holding three backticks cannot close the block early and turn the rest of the file into Markdown."""
    longest = max((len(m.group(0)) for m in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def table(headers: list[str], rows: list[list], none: str = "none") -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out) if rows else "\n".join(out) + f"\n| ({none}) |" + " |" * (len(headers) - 1)


def analysis_block(snap: Path) -> dict:
    """The `analysis` block of `llm/facts.json`, or an empty dict when the facts are missing or hold none."""
    facts = load_json(snap / "llm" / "facts.json") or {}
    a = facts.get("analysis") if isinstance(facts, dict) else None
    return a if isinstance(a, dict) else {}


def empty_analysis_fields(snap: Path, mode: str) -> list[str]:
    """The analysis fields the LLM left empty, named so `render-details` can say which ones."""
    a = analysis_block(snap)
    return [f for f in ANALYSIS_FIELDS if not a.get(f) and not (f == "areas" and mode != "full")]


def _rows_table(rows, headers: list[str], keys: list[str], missing: str, table) -> str:
    """A table from a list of dicts, or the missing marker when there are none."""
    rows = [r for r in rows or [] if isinstance(r, dict)]
    return table(headers, [[r.get(k, "") for k in keys] for r in rows]) if rows else missing


def _sev_counts(findings: list[dict], status: str) -> dict[str, int]:
    out = dict.fromkeys(SEVERITIES, 0)
    for f in findings:
        if f.get("status") == status:
            sev = f.get("severity_default", "info")
            out[sev] = out.get(sev, 0) + 1
    return out


def _persisted(diff: dict | None) -> dict[str, int]:
    """finding id -> number of consecutive same-mode runs it has appeared in (diff.json findings.persisted.rows)."""
    p = ((diff or {}).get("findings") or {}).get("persisted") or {}
    return {r["id"]: int(r["runs"]) for r in (p.get("rows") or []) if isinstance(r, dict) and "id" in r and isinstance(r.get("runs"), int | float)}


def keep_report(snap: Path, now: _dt.datetime | None = None) -> Path | None:
    """Move an existing report out of the way before another one is written from the same snapshot, for example in the other language.
    `report.md`, `report-details.md` and `llm/` have one path each, so without this the second report replaces the first. The earlier report goes to
    `earlier-reports/<time>/` in the snapshot. Returns that folder, or None when there is nothing to keep."""
    names = [n for n in ("report.md", "report-details.md", "llm") if (snap / n).exists()]
    if not names:
        return None
    stamp = (now or _dt.datetime.now().astimezone()).strftime("%Y-%m-%dT%H-%M-%S")
    dest = snap / "earlier-reports" / stamp
    n = 1
    while dest.exists():
        n += 1
        dest = snap / "earlier-reports" / f"{stamp}-{n}"
    paths.ensure_private_dir(dest, base=snap)
    for name in names:
        (snap / name).rename(dest / name)
    return dest


def _verified_notes(inv: dict, language: str) -> list[tuple[str, str]]:
    """The audited cluster's component versions next to the range kubegap's facts were read at (references/verified-versions.yaml, #146): the API server and
    the four stores, the versions inventory.json carries."""
    from . import verified

    out = []
    pairs = [("Kubernetes", (inv.get("cluster") or {}).get("server_version"))] + [
        (name, ((inv.get("stores") or {}).get(key) or {}).get("version")) for name, key in (("Prometheus", "prometheus"), ("Alertmanager", "alertmanager"), ("Loki", "loki"), ("Grafana", "grafana"))
    ]
    for name, version in pairs:
        note = verified.range_note(name, version, language)
        if note:
            out.append((name, note))
    return out


def render_details(snap: Path, language: str = "en") -> Path:
    lab = LABELS.get(language) or {}

    def L(text: str, **values) -> str:
        phrase = lab.get(text, text)
        return phrase.format(**values) if values else phrase

    none = L("none")

    def ltable(headers: list[str], rows: list[list]) -> str:
        return table([L(h) for h in headers], rows, none=none)

    missing = L("(not written this run)")
    inv = load_json(snap / "inventory.json") or {}
    summary = load_json(snap / "summary.json") or {}
    fd = load_json(snap / "findings-draft.json") or {}
    diff = load_json(snap / "diff.json")
    cr = load_json(snap / "collect-result.json") or {}
    findings = fd.get("findings") or []
    results = fd.get("check_results") or []
    mode = paths.snapshot_mode(snap)
    cluster = inv.get("cluster") or {}
    nodes = inv.get("nodes") or {}
    stores = inv.get("stores") or {}
    na = inv.get("node_access") or {}
    coll = summary.get("collection") or {}
    out: list[str] = []
    w = out.append

    # ---- header
    title = lab.get("title") or "# kubegap report details — {cluster} (`{context}`), {mode} mode"
    w(title.format(cluster=cluster.get("cluster_name") or inv.get("context"), context=inv.get("context"), mode=mode))
    w("")
    w(
        lab.get("intro")
        or "Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the analysis block of `llm/facts.json`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English."
    )
    w("")
    prom = stores.get("prometheus") or {}
    logs = stores.get("loki") or {}
    w(
        ltable(
            ["Item", "Value"],
            [
                [L("kube context / cluster"), f"`{inv.get('context')}` / {cluster.get('cluster_name')} ({cluster.get('platform')}, {cluster.get('server_version')})"],
                [
                    L("Run time / mode"),
                    f"{inv.get('taken_at')} / {mode} "
                    + L("(collection {seconds} s, {skipped} steps skipped by mode, {failed} failed)", seconds=coll.get("seconds_total"), skipped=len(coll.get("mode_skipped_steps") or []), failed=len(coll.get("failed_steps") or [])),
                ],
                [L("Profile"), f"`{(inv.get('profile') or {}).get('name')}` ({(inv.get('profile') or {}).get('source')})"],
                [L("kubegap / rubric / signatures"), f"{fd.get('kubegap') or __version__} / {fd.get('rubric_version')} / {inv.get('signatures_version')}"],
                [L("Verified against"), " · ".join(f"{name} {note}" for name, note in _verified_notes(inv, language)) or L("(no component version read)")],
                [L("Nodes / namespaces / pods / CRDs"), f"{nodes.get('count')} (Ready {nodes.get('ready')}) / {(inv.get('namespaces') or {}).get('count')} / {(inv.get('pods') or {}).get('count')} / {(inv.get('crds') or {}).get('count')}"],
                [f"{L('Components')} ({len(inv.get('components_present') or [])})", ", ".join(inv.get("components_present") or [])],
                [
                    L("Metrics store"),
                    f"{prom.get('kind') or none} {prom.get('version') or ''} retention {(prom.get('retention') or {}).get('time')} / size {(prom.get('retention') or {}).get('size')} via {prom.get('access')}" if prom else none,
                ],
                [L("Log store"), f"{logs.get('kind') or none} {logs.get('version') or ''}".strip() if logs.get("ok") else L("none (Loki not found)")],
                [L("Node access"), f"{na.get('method')} ({', '.join(na.get('reasons') or [])}); " + L("SSM unregistered {n}", n=len(na.get("ssm_unregistered") or []))],
                [L("Snapshot"), f"`{snap}`"],
            ],
        )
    )
    w("")

    # ---- 1. counts
    w(L("## 1. Counts (first pass) and the LLM's adjustments"))
    w("")
    fails, warns = _sev_counts(findings, "fail"), _sev_counts(findings, "warn")
    before = ((diff or {}).get("findings") or {}).get("counts_before") or {}
    rows = []
    for s in SEVERITIES:
        bf, bw = (before.get("fail") or {}).get(s), (before.get("warn") or {}).get(s)
        rows.append([s, fails[s], warns[s], f"fail {fails[s] - bf:+d} · warn {warns[s] - bw:+d}" if isinstance(bf, int) and isinstance(bw, int) else L("no previous run of this mode")])
    w(ltable(["Severity (default)", "fail", "warn", "vs. previous run of this mode"], rows))
    w("")
    bs = (fd.get("checks") or {}).get("by_status") or {}
    w(
        L(
            "Checks {total}: evaluated {done}, disabled by profile {disabled}, skipped {skip}, not collected in this mode {nc}, errors {error}, tool missing {tool}, LLM-judged {llm}. Suppressed findings {suppressed}.",
            total=(fd.get("checks") or {}).get("total"),
            done=bs.get("done", 0),
            disabled=bs.get("disabled", 0),
            skip=bs.get("skip", 0),
            nc=bs.get("not-collected", 0),
            error=bs.get("error", 0),
            tool=bs.get("tool-missing", 0),
            llm=bs.get("llm", 0),
            suppressed=len(fd.get("suppressed") or []),
        )
    )
    w("")
    analysis = analysis_block(snap)
    w(L("### 1-1. Final judgment vs. first pass (adjustments)"))
    w("")
    w(_rows_table(analysis.get("severity_changes"), ["Finding", "First pass", "Final", "Reason"], ["finding", "first_pass", "final", "reason"], missing, table))
    w("")
    w(L("### 1-2. Aggregates the LLM recounted"))
    w("")
    w(_rows_table(analysis.get("recounts"), ["Finding", "First pass", "Final", "Reason"], ["finding", "first_pass", "final", "reason"], missing, table))
    w("")

    # ---- 2. critical and high now
    w(L("## 2. Critical and high failing now (first pass)"))
    w("")
    persisted = _persisted(diff)
    ch = [f for f in findings if f.get("status") == "fail" and f.get("severity_default") in ("critical", "high")]
    w(ltable(["Finding", "Severity", "Consecutive runs", "Evidence"], [[f"`{f['id']}`", f.get("severity_default"), persisted.get(f["id"], "") or "", _evidence(f, 220)] for f in ch]))
    if not persisted:
        w("")
        w(L("(consecutive-run counts need diff.json; none for this snapshot)"))
    w("")

    # ---- 3. changes
    w(L("## 3. Changes since the previous run of this mode"))
    w("")
    if diff:
        df = diff.get("findings") or {}
        rv = df.get("rubric_version")
        w(L("Compared `{a}` → `{b}` (rubric {ra} → {rb}).", a=diff.get("a_name"), b=diff.get("b_name"), ra=rv[0] if isinstance(rv, list) and rv else rv, rb=rv[1] if isinstance(rv, list) and len(rv) > 1 else rv))
        differing = [f"{k} {v[0]} → {v[1]}" for k, v in (diff.get("versions") or {}).items() if isinstance(v, list) and len(v) == 2 and v[0] != v[1]]
        if differing:
            w(L("The two runs were made with different versions ({changes}); a key or a query renamed between them is a difference of the tool, not of the cluster.", changes=", ".join(differing)))
        mq = diff.get("metrics_queries") or {}
        for key, label in (("only_in_a", "Metric queries only in the previous run"), ("only_in_b", "Metric queries only in this run")):
            if mq.get(key):
                w(f"- {L(label)} ({len(mq[key])}): " + ", ".join(f"`{q}`" for q in mq[key]))
        w("")
        for key, label in (("new", "New"), ("resolved", "Resolved"), ("changed", "Changed"), ("rename_suspects", "Rename suspects")):
            items = df.get(key) or []
            w(
                f"- **{L(label)} ({len(items)})**: "
                + (", ".join(f"`{i.get('id') if isinstance(i, dict) else i}`" + (f" ({i.get('status')}/{i.get('severity_default')})" if isinstance(i, dict) and i.get("status") else "") for i in items) if items else none)
            )
        ob = diff.get("objects") or {}
        w(
            f"- **{L('Objects')}**: "
            + L("added {a}, removed {r}, changed {c}", a=len(ob.get("added") or []), r=len(ob.get("removed") or []), c=len(ob.get("changed") or []))
            + (": " + ", ".join(f"`{c.get('kind')}/{c.get('name')}` {','.join(c.get('changed_fields') or [])}" for c in (ob.get("changed") or [])[:12]) if ob.get("changed") else "")
        )
        evc = [e for e in ((diff.get("events") or {}).get("changed") or []) if e.get("type") == "Warning"]
        w(f"- **{L('Warning events')}**: " + (", ".join(f"{cell(e.get('reason'))} {e.get('delta'):+d} ({cell((e.get('objects_top_after') or [''])[0])})" for e in evc[:10]) if evc else L("no change")))
        crit = df.get("criteria_changes") or {}
        n_crit = sum(len(v) for k, v in crit.items() if isinstance(v, list))
        if n_crit:
            w("")
            w(L("### 3-0. Criteria changes, not cluster changes"))
            w("")
            w(
                L(
                    "These findings appeared, disappeared or changed because the checks did, not the cluster, and they are kept out of the lists above. Taken from `diff.json` `findings.criteria_changes`; the report writes them as a criteria change and never as a tool defect."
                )
            )
            w("")
            for key, label in (
                ("new_checks", "Checks absent or gated off in the previous run"),
                ("dropped_checks", "Checks absent or gated off in this run"),
                ("rule_changed", "Checks whose rule changed between the runs"),
                ("thresholds_changed", "Checks whose thresholds in force changed"),
            ):
                rows = crit.get(key) or []
                if rows:
                    w(f"- **{L(label)} ({len(rows)})**: " + ", ".join(f"`{r.get('id')}` ({r.get('kind')}, {r.get('status')}/{r.get('severity_default')})" for r in rows))
        pers = df.get("persisted") or {}
        if pers:
            w(
                f"- **{L('Persisted (Toil)')}**: "
                + L("{all} findings present in all {runs} runs checked, {three} in 3 or more; top checks: ", all=pers.get("persisted_all"), runs=pers.get("runs_checked"), three=pers.get("persisted_3plus"))
                + ", ".join(f"`{k}` {v}" for k, v in list((pers.get("toil_candidates_by_check") or {}).items())[:8])
            )
    else:
        w(L("No earlier {mode} snapshot to compare with.", mode=mode))
    w("")
    w(L("### 3-1. Why things changed"))
    w("")
    w(str(analysis.get("why_changed") or "").strip() or missing)
    w("")

    # ---- 4. areas (fragment)
    w(L("## 4. Detail per area"))
    w("")
    if mode == "full":
        areas = analysis.get("areas") if isinstance(analysis.get("areas"), dict) else {}
        w("\n\n".join(f"### {name}\n\n{str(areas.get(name) or '').strip() or missing}" for name in AREAS) if areas else missing)
    else:
        w(L("(daily mode: no per-area detail; see section 2 and `report.md`)"))
    w("")

    # ---- 5. absence
    w(L("## 5. Absence list"))
    w("")
    absent = [f for f in findings if f.get("type") == "absence" and f.get("status") in ("fail", "warn")]
    w(ltable(["Finding", "Status", "Severity", "Why it should exist", "Proposal"], [[f"`{f['id']}`", f.get("status"), f.get("severity_default"), _cut(f.get("why"), 200), _cut(f.get("suggest"), 200)] for f in absent]))
    w("")
    w(L("Expected families missing (inventory): {families}.", families=", ".join(inv.get("missing_families") or []) or none))
    w("")

    # ---- 6. suppressed, tool missing, not collected
    w(L("## 6. Suppressed, tool missing, not collected"))
    w("")
    sup = fd.get("suppressed") or []
    w(f"- {L('Suppressed')} {len(sup)}: " + (", ".join(f"`{s['id']}` ({(s.get('suppressed_by') or {}).get('reason')}, {L('until')} {(s.get('suppressed_by') or {}).get('until')})" for s in sup) if sup else none))
    exp = fd.get("expired_suppressions") or []
    w(f"- {L('Suppression expired')} {len(exp)}: " + (", ".join(f"`{e.get('id')}`" for e in exp) if exp else none))
    tm = [r for r in results if r.get("status") == "tool-missing"]
    w(f"- {L('Tool missing')} {len(tm)}: " + (", ".join(f"`{r['id']}` ({r.get('reason')})" for r in tm) if tm else none))
    nc = [r for r in results if r.get("status") == "not-collected"]
    w(f"- {L('Not collected in {mode} mode', mode=mode)} {len(nc)}: " + (", ".join(f"`{r['id']}`" for r in nc) if nc else none))
    sk = [r for r in results if r.get("status") in ("skip", "error")]
    w(f"- {L('Skipped or errored')} {len(sk)}: " + (", ".join(f"`{r['id']}` ({r.get('status')}: {r.get('reason')})" for r in sk) if sk else none))
    part = [r for r in results if r.get("status") == "done" and r.get("skipped_reason")]
    w(
        f"- {L('Judged in part')} {len(part)} ({L('some targets lacked what the rule needs; those are not judged, not passed')}): "
        + (", ".join(f"`{r['id']}` ({(r.get('counts') or {}).get('skipped')} {L('not judged')}: {r['skipped_reason']})" for r in part) if part else none)
    )
    emp = [r for r in results if r.get("status") == "done" and (r.get("counts") or {}).get("empty")]
    w(f"- {L('Query returned no series')} {len(emp)} ({L('every metric name the query reads has series, so nothing happened; a name with no series would be a skip')}): " + (", ".join(f"`{r['id']}`" for r in emp) if emp else none))
    w("")

    # ---- 7. appendix
    w(L("## 7. Appendix"))
    w("")
    w(L("### 7-1. Collectors and steps run"))
    w("")
    rows = []
    # The one list of failed steps is `_summary.failed`, written by lib/collect.py (ok false and not skipped); the header row reads it through
    # summary.collection.failed_steps, and the Failed column and the count below it read it here, so no second copy of the predicate exists (#132).
    sm = cr.get("_summary") or {}
    failed_ids = [str(x) for x in sm.get("failed") or []]
    failed_steps: list[tuple[str, str]] = []
    for name, c in cr.items():
        if name.startswith("_") or not isinstance(c, dict):
            continue
        steps = c.get("steps") or {}
        failed = [fid[len(name) + 1 :] for fid in failed_ids if fid.startswith(name + ".")]
        failed_steps += [(f"{name}.{sid}", str((steps.get(sid) or {}).get("error") or "")) for sid in failed]
        skipped = [f"{sid} ({st.get('note') if st.get('skipped') is True else st.get('skipped')})" for sid, st in steps.items() if isinstance(st, dict) and st.get("skipped")]  # True: a snapshot taken before the step wrote its reason here
        rows.append([name, len(steps), ", ".join(failed) or "", "; ".join(skipped) or (c.get("skipped") or "")])
    w(ltable(["Collector", "Steps", "Failed", "Skipped (reason)"], rows))
    npk = ((cr.get("core") or {}).get("steps") or {}).get("objects.dump-all", {}).get("not_permitted") or []
    if npk:
        w("")
        w(L("Kinds the ClusterRole does not grant ({n}; a check that needs one of them is skipped, not passed): ", n=len(npk)) + ", ".join(f"`{k}`" for k in npk))
    # summary.collection.object_files (#160): every objects/<stem>.json a summary module asked for and why it is missing when it is
    object_files = coll.get("object_files") or {}
    for status, text in (
        ("not-served", "Kinds this cluster does not serve ({n}; a check that needs one of them is skipped, not passed): "),
        ("unlisted", "Kinds this cluster serves but the snapshot has no file for ({n}; kubegap looked for the wrong file name, a kubegap defect, and the checks that read them judged nothing): "),
    ):
        stems = sorted(k for k, v in object_files.items() if v == status)
        if stems:
            w("")
            w(L(text, n=len(stems)) + ", ".join(f"`{k}`" for k in stems))
    run = summary.get("run") or {}
    w("")
    # Until #132 this line counted run.log exit codes while the table above read collect-result.json, and the two disagreed for a tool that exits 0 without
    # reading the cluster (kubent, pluto): the step is failed, its command is not.
    w(
        L("{commands} commands, {seconds} s. Failed steps: {n}", commands=run.get("commands") or "?", seconds=sm.get("seconds_total"), n=len(failed_steps))
        + (": " + "; ".join(f"`{sid}` {cell(_cut(err, 120))}" for sid, err in failed_steps[:20]) if failed_steps else "")
    )
    # A command can fail inside a step that still succeeded (one pod of a per-pod metrics step, one release of `helm get values`); run.log has it and the step does not.
    failed_ids = {sid for sid, _ in failed_steps}
    inside = [f for f in run.get("failed") or [] if str(f.get("id")) not in failed_ids and not any(str(f.get("id")).startswith(sid + ".") for sid in failed_ids)]
    if inside:
        w("")
        w(L("Commands that failed inside a step that still succeeded (run.log): {n}: ", n=len(inside)) + "; ".join(f"`{f.get('id')}` {cell(_cut(f.get('error'), 120))}" for f in inside[:20]))
    # How much of the API the deprecated-API tools saw (#132). kubent swallows a forbidden List, so its Lists answered and refused are counted from its log; pluto reads the saved objects, so what it saw is what objects.dump-all saved.
    dep = (summary.get("hygiene") or {}).get("deprecated") or {}
    wording = {"kubent": ("Lists answered", "refused or not served"), "pluto": ("Lists answered", "refused or not served")}
    if "manifests" in (((cr.get("core") or {}).get("steps") or {}).get("pluto") or {}):  # older snapshots: pluto made its own Lists
        wording["pluto"] = ("object kinds saved", "not permitted or failed")
    seen = [
        L(
            "{tool} {ok} of {total} Lists answered ({failed} refused or not served)" if wording[tool][0] == "Lists answered" else "{tool} {ok} of {total} object kinds saved ({failed} not permitted or failed)",
            tool=tool,
            ok=dep[f"{tool}_lists_ok"],
            total=dep[f"{tool}_lists_ok"] + dep[f"{tool}_lists_failed"],
            failed=dep[f"{tool}_lists_failed"],
        )
        for tool in ("kubent", "pluto")
        if isinstance(dep.get(f"{tool}_lists_ok"), int) and isinstance(dep.get(f"{tool}_lists_failed"), int)
    ]
    seen += [f"{tool} had {dep[f'{tool}_manifests']} objects with a last-applied annotation to judge" for tool in ("kubent", "pluto") if dep.get(f"{tool}_read") and isinstance(dep.get(f"{tool}_manifests"), int)]
    if seen:
        w("")
        w(L("Deprecated-API tools: ") + "; ".join(seen) + ".")
    w("")
    w(L("### 7-2. Checks evaluated"))
    w("")
    w(
        L(
            "{total} checks: {counts}. Load errors: {errors}.",
            total=(fd.get("checks") or {}).get("total"),
            counts=", ".join(f"{k} {v}" for k, v in sorted(bs.items())),
            errors=", ".join((fd.get("checks") or {}).get("load_errors") or []) or none,
        )
    )
    w("")
    w(L("### 7-3. Signature matches and unclassified errors"))
    w("")
    lg = summary.get("logs") or {}
    w(
        L(
            "Signature catalog {version}, {files} files, {lines} lines scanned (components: {components}). Unclassified error lines: {unclassified}.",
            version=lg.get("signatures_version"),
            files=len(lg.get("files_scanned") or []),
            lines=lg.get("lines_scanned"),
            components=", ".join(lg.get("components_with_logs") or []),
            unclassified=lg.get("error_lines_unclassified"),
        )
    )
    w("")
    sigs = lg.get("signatures") or []
    w(
        ltable(
            ["Signature", "Component", "Area", "Severity", "Status", "Count", "First, last", "Sample"],
            [[s.get("id"), s.get("component"), s.get("area"), s.get("severity"), s.get("status"), s.get("count"), f"{s.get('first') or ''} , {s.get('last') or ''}", _cut((s.get("samples") or [""])[0], 160)] for s in sigs],
        )
    )
    w("")
    un = lg.get("unclassified_errors") or []
    w(ltable(["Normalized message", "Count", "Files"], [[_cut(u.get("pattern"), 200), u.get("count"), ", ".join(list((u.get("files") or {}).keys())[:3]) if isinstance(u.get("files"), dict) else ""] for u in un[:30]]))
    w("")
    w(L("### 7-4. Raw files the LLM read directly"))
    w("")
    files_read = [str(f) for f in analysis.get("files_read") or []]
    w("\n".join(f"- `{cell(f)}`" for f in files_read) if files_read else missing)
    outside = [c for c in analysis.get("commands_outside_snapshot") or [] if isinstance(c, dict)]
    if outside:
        w("")
        w(L("Read-only commands run outside the snapshot") + ":")
        w("")
        w(ltable(["Command", "Saved as"], [[f"`{cell(c.get('command'))}`", f"`{cell(c.get('saved_as'))}`"] for c in outside]))
    w("")
    w(L("### 7-5. Full first-pass status (every fail and warn, code results as-is)"))
    w("")
    fw = sorted((f for f in findings if f.get("status") in ("fail", "warn")), key=lambda f: (SEVERITIES.index(f.get("severity_default", "info")) if f.get("severity_default") in SEVERITIES else 9, f.get("status") != "fail", f.get("id", "")))
    w(ltable(["id", "Status", "Default severity", "Evidence"], [[f"`{f['id']}`", f.get("status"), f.get("severity_default"), _evidence(f, 300)] for f in fw]))
    w("")
    w(L("The table cuts each evidence at 300 characters and a check may cut a list in its evidence; nothing is lost. Every finding below carries, folded, the material its rule judged, taken from `findings-draft.json` `details`."))
    w("")
    for f in fw:
        if f.get("details") is None:
            continue
        body = json.dumps(f["details"], ensure_ascii=False, indent=1, default=str)
        fence = _fence(body)
        w(f"<details><summary><code>{html.escape(str(f['id']))}</code></summary>")
        w("")
        w(fence + "json")
        w(body)
        w(fence)
        w("")
        w("</details>")
    w("")
    w(L("### 7-6. Tool notes (about kubegap itself)"))
    w("")
    tool_notes = [t for t in analysis.get("tool_notes") or [] if isinstance(t, dict) and t.get("text")]
    w("\n".join(f"{t.get('n', i + 1)}. {cell(t['text'])}" + (" (" + L("still open from note {n}", n=t["still_open_from"]) + ")" if t.get("still_open_from") else "") for i, t in enumerate(tool_notes)) if tool_notes else missing)
    w("")
    p = snap / "report-details.md"
    write_private(p, "\n".join(out))
    return p

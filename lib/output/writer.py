"""`kubegap write-report`: turn the analysis facts into the report, with separate agents.

The analysis ends in `llm/facts.json` (references/facts-<language>.md; its text fields are in the report language, its keys and numbers the same in both). From there, four agents at most, each started headless with the CLI of the host and
each from a clean start:

    check the steps (snapshot open) -> write -> check the text against the facts and the snapshot (snapshot open) -> replace the wrong sentences

The step checker runs first and sees only the steps and the impact, never the analysis text, so it cannot repeat the analysis's mistakes; code merges
its verdicts into the facts, and the writer gets the merged facts. The writer and the replacer get no tools at all: input on stdin, text on
stdout, so cluster strings in the facts cannot lead to a command. The two checkers can only read files. There is no language reviewer, no editor
and no whole rewrite: a second pass by the same model with no new evidence does not make the text truer, and every rewrite loses something.
The prompts are files, one set per language and nothing shared: references/check-actions-<language>.md, writing-<language>.md,
check-facts-<language>.md, replace-<language>.md. Code adds what no agent should be trusted with: the title line, the cluster at a glance, what is
coming, the since-last-run table, the one line per area in full mode, the numbers table and the check ids; it puts a blank line between blocks so
a viewer shows them as written; and it refuses a replacement that drops a command, a step or a problem.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Callable
from pathlib import Path

from ..foundations import paths, shell
from ..foundations.snapshot import load_json, write_private
from .render import table

REFERENCES = paths.ROOT / "references"
HOSTS = ("claude", "codex")
CALL_TIMEOUT = 1800  # the step check of a full report reads objects for a quarter of an hour
READ_ONLY_TOOLS = "Read,Grep,Glob"
AREAS = ("resources", "scaling", "observability", "traffic", "resilience", "hygiene", "storage", "security", "cost", "tenancy", "node OS", "platform")
HEADINGS = {
    "en": {
        "audit": "audit",
        "numbers": "Numbers",
        "severity": "Severity",
        "vs": "vs. previous {mode} run",
        "details": "Details and every table",
        "snapshot": "snapshot",
        "checks": "Checks behind each problem",
        "problem": "problem",
        "glance": "The cluster at a glance",
        "upcoming": "Coming up",
        "since": "Since the previous {mode} run",
        "areas": "Each area in one line",
        "serious": "## Serious, not today",
        "not_seen": "## What this run could not see",
        "item": "What",
        "value": "Value",
        "source": "Source",
        "when": "When",
        "what": "What",
        "area": "Area",
        "nodes": "Nodes",
        "pods": "Pods",
        "namespaces": "Namespaces",
        "components": "Components",
        "stores": "Metrics and log stores",
        "versions": "Kubernetes",
        "ready": "{ready} of {count} Ready",
        "pods_v": "{running} running, {pending} pending, {failed} failed",
        "ns_v": "{count}, {prod} production",
        "no_store": "none",
        "prev_work": "Work the previous report asked for",
        "state": "State",
        "proof": "Proof",
        "done": "done",
        "not_done": "not done",
        "appeared": "Appeared",
        "gone": "Went away",
        "criteria": "Changed because the checks changed, not the cluster",
        "no_compare": "No earlier {mode} run to compare with.",
        "crit_new": "Checks that did not run last time, so these findings are new to the audit, not to the cluster",
        "crit_dropped": "Checks that did not run this time",
        "crit_rule": "Checks whose rule changed between the runs",
        "crit_thresholds": "Checks whose thresholds changed between the runs",
        "crit_severity": "Checks whose severity changed between the runs because the scale of the cluster or the check did",
        "none": "none",
    },
    "ko": {
        "audit": "점검",
        "numbers": "숫자",
        "severity": "심각도",
        "vs": "지난 {mode} 점검 대비",
        "details": "자세한 내용과 모든 표",
        "snapshot": "수집 자료",
        "checks": "문제별 체크",
        "problem": "문제",
        "glance": "클러스터 한눈에",
        "upcoming": "다가오는 일",
        "since": "지난 {mode} 점검 이후",
        "areas": "영역별 한 줄",
        "serious": "## 오늘은 안 하지만 심각한 것",
        "not_seen": "## 이번에 못 본 것",
        "item": "항목",
        "value": "값",
        "source": "출처",
        "when": "언제",
        "what": "무엇",
        "area": "영역",
        "nodes": "노드",
        "pods": "파드",
        "namespaces": "네임스페이스",
        "components": "컴포넌트",
        "stores": "메트릭·로그 저장소",
        "versions": "Kubernetes",
        "ready": "{count}대 중 Ready {ready}대",
        "pods_v": "실행 {running}, 대기 {pending}, 실패 {failed}",
        "ns_v": "{count}개, 프로덕션 {prod}개",
        "no_store": "없음",
        "prev_work": "지난 리포트가 시킨 일",
        "state": "상태",
        "proof": "근거",
        "done": "했음",
        "not_done": "안 했음",
        "appeared": "새로 생긴 것",
        "gone": "사라진 것",
        "criteria": "클러스터가 아니라 점검 기준이 바뀌어서 달라진 것",
        "no_compare": "비교할 이전 {mode} 점검이 없어요.",
        "crit_new": "지난번에는 돌지 않은 점검 항목이라 클러스터가 아니라 점검에 새로 보인 것",
        "crit_dropped": "이번에 돌지 않은 점검 항목",
        "crit_rule": "두 점검 사이에 판정 규칙이 바뀐 항목",
        "crit_thresholds": "두 점검 사이에 임계값이 바뀐 항목",
        "crit_severity": "두 점검 사이에 운영 규모나 점검 기준이 바뀌어 심각도가 달라진 항목",
        "none": "없음",
    },
}


class WriterError(Exception):
    """A step could not run. The message says which one and what to do."""


def detect_host() -> str | None:
    """The CLI to start agents with: the one this session runs in, else the one installed."""
    if os.environ.get("CLAUDECODE"):
        return "claude"
    if any(k.startswith("CODEX_") for k in os.environ):
        return "codex"
    return next((h for h in HOSTS if shell.which(h)), None)


def agent_command(host: str, guide: Path, *, read_files: bool) -> tuple[list[str], str]:
    """The command line of one agent, and the text to put before its input. Claude takes the guide as its system prompt; `codex exec` has no such
    flag, so the guide goes in front of the input. `--setting-sources ""` keeps the user's own instructions out of the agent."""
    if host == "claude":
        tools = READ_ONLY_TOOLS if read_files else ""
        cmd = ["claude", "-p", "--tools", tools, "--setting-sources", "", "--no-session-persistence", "--system-prompt-file", str(guide)]
        return ([*cmd, "--allowedTools", READ_ONLY_TOOLS] if read_files else cmd), ""
    if host == "codex":
        return ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "-"], guide.read_text(encoding="utf-8") + "\n\n"
    raise WriterError(f"unknown host {host}")


def call(host: str, guide: Path, text: str, cwd: Path, *, read_files: bool = False, run: Callable = shell.run, timeout: float = CALL_TIMEOUT) -> str:
    cmd, prefix = agent_command(host, guide, read_files=read_files)
    r = run(cmd, stdin=prefix + text, cwd=cwd, timeout=timeout)
    if not r.ok or not r.stdout.strip():
        raise WriterError(f"{host} agent with {guide.name} failed: {(r.error or r.stderr or 'empty output').strip()[-300:]}")
    return r.stdout.strip() + "\n"


def _tagged(**parts: str) -> str:
    """Input for an agent: each part in its own tag, so instructions and data cannot be confused (`<facts>…</facts>`)."""
    return "\n\n".join(f"<{k}>\n{v.strip()}\n</{k}>" for k, v in parts.items() if v is not None)


# ---------- numbers against the snapshot


def _resolve(doc, path: str):
    """The value at `a.b[0].c`. Raises KeyError or IndexError or TypeError when the path does not exist."""
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        doc = doc[int(part[1:-1])] if part.startswith("[") else doc[part]
    return doc


def _numbered(facts: dict):
    """Every entry that carries a source: (label, entry) for the numbers of each problem and for the upcoming list."""
    for p in facts.get("problems") or []:
        for n in (p.get("situation") or {}).get("numbers") or []:
            yield f"problem {p.get('id')}: {n.get('what')}", n
    for u in facts.get("upcoming") or []:
        if isinstance(u, dict):
            yield f"upcoming: {u.get('what')}", {**u, "value": u.get("when")}


def verify_numbers(snap: Path, facts: dict) -> list[str]:
    """Numbers whose source does not say what the facts say. A number marked `derived` was recounted and is left to the fact checker; a path with `*` or `...` is too."""
    out: list[str] = []
    docs: dict[str, object] = {}
    for label, n in _numbered(facts):
        src, path = n.get("source_file"), str(n.get("json_path") or "")
        if n.get("derived"):
            continue
        f = snap / str(src or "")
        if not src or not f.is_file():
            out.append(f"{label}: source file {src} does not exist")
            continue
        if not path or "*" in path or "..." in path or not src.endswith(".json"):
            continue
        try:
            doc = docs.setdefault(src, json.loads(f.read_text(encoding="utf-8")))
            found = _resolve(doc, path)
        except (KeyError, IndexError, TypeError, ValueError):
            out.append(f"{label}: {path} is not in {src}")
            continue
        value = n.get("value")
        wanted = [str(v) for v in value] if isinstance(value, list) else [str(value)]
        if not all(w in json.dumps(found, ensure_ascii=False, default=str) for w in wanted):
            out.append(f"{label}: facts say {value}, {src} {path} says {str(found)[:120]}")
    return out


# ---------- the step check and how its verdicts go into the facts


def steps_for_check(facts: dict) -> str:
    """What the step checker gets: the steps and the impact of every problem, nothing the analysis wrote about them."""
    rows = [{"id": p.get("id"), "title": p.get("title"), "targets": p.get("targets") or [], "steps": p.get("steps") or [], "impact": (p.get("situation") or {}).get("impact") or {}} for p in facts.get("problems") or []]
    return json.dumps({"problems": rows}, ensure_ascii=False, indent=1)


def parse_json(text: str) -> dict:
    """The one JSON object in an agent's answer, with or without a code fence around it."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.MULTILINE).strip()
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end < 0:
        raise WriterError("the step check did not answer with a JSON object")
    try:
        doc = json.loads(s[start : end + 1])
    except ValueError as e:
        raise WriterError(f"the step check answered with broken JSON: {e}") from e
    if not isinstance(doc, dict):
        raise WriterError("the step check did not answer with a JSON object")
    return doc


SET_FIELDS = ("when", "do", "command", "changes", "risk", "check", "rollback")


def apply_action_check(facts: dict, result: dict) -> tuple[dict, list[str]]:
    """The checker's verdicts written into a copy of the facts, and one line per change for the run log. A harm step is removed, a hold step
    gets its condition, a fix step gets the corrected fields, every step keeps its verdict; missing risks and impact corrections go to the problem."""
    out = copy.deepcopy(facts)
    notes: list[str] = []
    by_id = {str(p.get("id")): p for p in out.get("problems") or []}
    removals: dict[str, list[int]] = {}
    for a in result.get("actions") or []:
        p = by_id.get(str(a.get("problem")))
        steps = (p or {}).get("steps") or []
        i = a.get("step")
        if p is None or not isinstance(i, int) or not 0 <= i < len(steps):
            notes.append(f"step check named a step that does not exist: problem {a.get('problem')} step {i}")
            continue
        verdict = str(a.get("verdict") or "ok").lower()
        step = steps[i]
        step["verdict"] = verdict
        chosen = {k: v for k, v in (a.get("set") or {}).items() if k in SET_FIELDS and v not in (None, "")}
        if verdict == "harm":
            removals.setdefault(str(p.get("id")), []).append(i)
            notes.append(f"problem {p.get('id')} step {i + 1} removed as harm: {a.get('reason')}")
            continue
        if verdict == "hold" and "when" not in chosen and a.get("reason"):
            chosen["when"] = str(a["reason"])
        if verdict == "fix" and not chosen and a.get("reason"):
            chosen["risk"] = ((step.get("risk") or "") + " " + str(a["reason"])).strip()
        step.update(chosen)
        if verdict != "ok":
            notes.append(f"problem {p.get('id')} step {i + 1} {verdict}: {a.get('reason')}")
    for pid, idx in removals.items():
        p = by_id[pid]
        p["steps"] = [s for n, s in enumerate(p.get("steps") or []) if n not in set(idx)]
    for m in result.get("missing") or []:
        p = by_id.get(str(m.get("problem")))
        if p is None or not m.get("what"):
            continue
        files = ", ".join(m.get("files") or [])
        p.setdefault("missing_risks", []).append(f"{m['what']}" + (f" ({files})" if files else ""))
        notes.append(f"problem {pid_of(p)} missing risk: {m['what']}")
    for im in result.get("impact") or []:
        p = by_id.get(str(im.get("problem")))
        if p is None:
            continue
        impact = p.setdefault("situation", {}).setdefault("impact", {})
        for k in ("affected", "checked_healthy", "changed_other_reason", "not_checked"):
            if k in im and isinstance(im[k], list):
                impact[k] = im[k]
        notes.append(f"problem {pid_of(p)} impact corrected")
    return out, notes


def pid_of(p: dict) -> str:
    return str(p.get("id"))


# ---------- what code writes, and what it refuses


def _delta(row: dict) -> str:
    """`fail +2, warn -1` from the numbers in `delta`. The cell is the same in every language, which is why the analysis gives numbers and no words."""
    d = row.get("delta")
    return ", ".join(f"{k} {d[k]:+d}" if d[k] else f"{k} 0" for k in ("fail", "warn") if isinstance(d.get(k), int)) if isinstance(d, dict) else ""


def _numbers_table(facts: dict, h: dict, mode: str) -> str:
    counts = facts.get("counts") or {}
    rows = [[s, (counts.get(s) or {}).get("fail", 0), (counts.get(s) or {}).get("warn", 0), _delta(counts.get(s) or {})] for s in ("critical", "high", "medium", "low")]
    return table([h["severity"], "fail", "warn", h["vs"].format(mode=mode)], rows)


def _check_ids(facts: dict, h: dict) -> str:
    """The ids `/kubegap explain` takes, printed by code so no agent can leave them out."""
    rows = [f"- {h['problem']} {p.get('id')}: " + ", ".join(f"`{i}`" for i in p["finding_ids"]) for p in facts.get("problems") or [] if p.get("finding_ids")]
    return f"{h['checks']}:\n\n" + "\n".join(rows) + "\n\n" if rows else ""


def glance(snap: Path, h: dict) -> str:
    """The cluster at a glance, from the snapshot files: nodes, pods, namespaces, components, stores, version. A reader sees the size of the
    cluster before the problems, and nothing here is written by an agent."""
    inv = load_json(snap / "inventory.json") or {}
    nodes, pods, ns = inv.get("nodes") or {}, inv.get("pods") or {}, inv.get("namespaces") or {}
    phase = pods.get("by_phase") or {}
    stores = inv.get("stores") or {}
    prom, loki = stores.get("prometheus") or {}, stores.get("loki") or {}
    cluster = inv.get("cluster") or {}
    rows = [
        [h["nodes"], h["ready"].format(count=nodes.get("count", 0), ready=nodes.get("ready", 0))],
        [h["pods"], h["pods_v"].format(running=phase.get("Running", 0), pending=phase.get("Pending", 0), failed=phase.get("Failed", 0))],
        [h["namespaces"], h["ns_v"].format(count=ns.get("count", 0), prod=len(ns.get("prod_like") or []))],
        [h["components"], f"{len(inv.get('components_present') or [])}: " + ", ".join(inv.get("components_present") or [])],
        [h["stores"], f"{prom.get('kind') or h['no_store']} {prom.get('version') or ''}".strip() + " / " + (f"{loki.get('kind') or ''} {loki.get('version') or ''}".strip() if loki.get("ok") else h["no_store"])],
        [h["versions"], f"{cluster.get('server_version') or ''} ({cluster.get('platform') or ''})".strip()],
    ]
    return f"## {h['glance']}\n\n" + table([h["item"], h["value"]], rows)


def upcoming(facts: dict, h: dict) -> str:
    rows = [[u.get("when"), u.get("what"), u.get("source_file") or ""] for u in facts.get("upcoming") or [] if isinstance(u, dict) and u.get("what")]
    return f"## {h['upcoming']}\n\n" + (table([h["when"], h["what"], h["source"]], rows) if rows else h["none"])


def criteria_changes(snap: Path, h: dict) -> list[str]:
    """Lines for the findings that appeared or went away because the checks changed, read by code from diff.json so that no agent can present
    them as changes in the cluster. Each bucket of `findings.criteria_changes` becomes one label and the ids under it."""
    diff = load_json(snap / "diff.json") or {}
    crit = ((diff.get("findings") or {}).get("criteria_changes")) or {}
    out: list[str] = []
    for key, label in (("new_checks", "crit_new"), ("dropped_checks", "crit_dropped"), ("rule_changed", "crit_rule"), ("thresholds_changed", "crit_thresholds"), ("severity_changed", "crit_severity")):
        rows = [r for r in crit.get(key) or [] if isinstance(r, dict) and r.get("id")]
        if rows:
            out += [f"**{h[label]}.**", *(f"- `{r['id']}` ({r.get('status')}/{r.get('severity_default')})" for r in rows), ""]
    return out


def since_last(facts: dict, h: dict, mode: str, snap: Path | None = None) -> str:
    s = facts.get("since_last") or {}
    title = f"## {h['since'].format(mode=mode)}"
    if not s.get("compared_with") and not any(s.get(k) for k in ("done", "not_done", "appeared", "gone", "criteria_changed")):
        return f"{title}\n\n{h['no_compare'].format(mode=mode)}"
    out = [title, ""]
    if s.get("compared_with"):
        out += [str(s["compared_with"]), ""]
    work = [[w.get("problem"), h["done"], w.get("proof") or ""] for w in s.get("done") or [] if isinstance(w, dict)]
    work += [[w.get("problem"), h["not_done"], w.get("proof") or ""] for w in s.get("not_done") or [] if isinstance(w, dict)]
    out += [table([h["prev_work"], h["state"], h["proof"]], work) if work else f"{h['prev_work']}: {h['none']}", ""]
    for key, label in (("appeared", "appeared"), ("gone", "gone"), ("criteria_changed", "criteria")):
        items = [str(x) for x in s.get(key) or []]
        out += [f"**{h[label]}.**", *(f"- {x}" for x in items or [h["none"]]), ""]
    if snap is not None:
        out += criteria_changes(snap, h)
    return "\n".join(out).rstrip()


def area_lines(facts: dict, h: dict) -> str:
    summary = (facts.get("analysis") or {}).get("area_summary") or {}
    rows = [[a, summary.get(a) or h["none"]] for a in AREAS] if isinstance(summary, dict) and summary else []
    return f"## {h['areas']}\n\n" + (table([h["area"], h["what"]], rows) if rows else h["none"])


def insert_sections(body: str, snap: Path, facts: dict, language: str, mode: str) -> str:
    """The code-made sections put into the writer's body at fixed places: the glance and what is coming before the first problem, the since-last
    section before "Serious, not today", the area lines before "What this run could not see" in full mode. A missing anchor puts the section at the end."""
    h = HEADINGS[language]
    head = f"{glance(snap, h)}\n\n{upcoming(facts, h)}\n\n"
    m = re.search(r"^## \d+\. ", body, re.MULTILINE)
    body = body[: m.start()] + head + body[m.start() :] if m else body + "\n\n" + head
    i = body.find(h["serious"])
    since = since_last(facts, h, mode, snap)
    body = body[:i] + since + "\n\n" + body[i:] if i >= 0 else body + "\n\n" + since
    if mode == "full":
        i = body.find(h["not_seen"])
        body = body[:i] + area_lines(facts, h) + "\n\n" + body[i:] if i >= 0 else body + "\n\n" + area_lines(facts, h)
    return body


_FENCE = re.compile(r"^```.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_STEP = re.compile(r"^[①-⑩]", re.MULTILINE)
_PROBLEM = re.compile(r"^## \d+\. ", re.MULTILINE)


def gate(before: str, after: str) -> list[str]:
    """What a replacement may not do: drop or change a command block, or change the number of problems or numbered steps."""
    out = [f"this command block is gone or changed: {f.splitlines()[1] if f.count(chr(10)) > 1 else f}" for f in _FENCE.findall(before) if f not in after]
    if len(_PROBLEM.findall(before)) != len(_PROBLEM.findall(after)):
        out.append("the number of problems changed")
    if len(_STEP.findall(before)) != len(_STEP.findall(after)):
        out.append("the number of numbered steps changed")
    return out


_ROW = re.compile(r"^\s*\|")
_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def space_blocks(text: str) -> str:
    """A blank line between consecutive lines of prose, so a Markdown viewer shows each line as its own paragraph instead of joining the first screen,
    a label line and a list into one block. List items stay together, table rows stay together, code blocks are left as they are."""
    out: list[str] = []
    fence = False
    prev = ""
    for ln in text.splitlines():
        if ln.strip().startswith("```"):
            if not fence and prev.strip():
                out.append("")
            fence = not fence
        elif not fence and ln.strip() and prev.strip():
            same_list = _ITEM.match(ln) and _ITEM.match(prev)
            same_table = _ROW.match(ln) and _ROW.match(prev)
            if not (same_list or same_table):
                out.append("")
        out.append(ln)
        prev = ln
    return "\n".join(out)


def assemble(snap: Path, facts: dict, body: str, language: str, rubric: str, version: str) -> str:
    """The report: title line from code, the body from the writer, then the numbers table, the check ids and the tail from code."""
    h = HEADINGS[language]
    c = facts.get("cluster") or {}
    mode = paths.snapshot_mode(snap)
    title = f"# {c.get('name') or c.get('context')} — {mode} {h['audit']}, {str(c.get('taken_at') or snap.name)[:16].replace('T', ' ')}"
    tail = f"{h['details']}: [`report-details.md`](report-details.md) · kubegap {version}, rubric {rubric} · {h['snapshot']} `{snap}`"
    body = insert_sections(body.strip(), snap, facts, language, mode)
    return f"{title}\n\n{space_blocks(body)}\n\n## {h['numbers']}\n\n{_numbers_table(facts, h, mode)}\n\n{_check_ids(facts, h)}{tail}\n"


# ---------- the run


def write_report(snap: Path, language: str, host: str, rubric: str, version: str, *, say: Callable = print, run: Callable = shell.run) -> Path:
    """Write `report.md` from `llm/facts.json`. Each agent's text stays in `llm/writing/` so a poor result can be traced; the facts as the analysis
    wrote them stay in `llm/facts-analysis.json` and `llm/facts.json` holds them with the step check merged in."""
    facts_path = snap / "llm" / "facts.json"
    if not facts_path.is_file():
        raise WriterError(f"{facts_path} does not exist. The analysis writes it first (references/facts-{language}.md)")
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    if not facts.get("problems"):
        raise WriterError("llm/facts.json has no problems")
    if language not in HEADINGS:
        raise WriterError(f"no prompts for language {language}")
    guides = {name: REFERENCES / f"{name}-{language}.md" for name in ("check-actions", "writing", "check-facts", "replace")}
    work = snap / "llm" / "writing"
    paths.ensure_private_dir(work, base=snap)

    def keep(name: str, text: str) -> str:
        write_private(work / name, text)
        return text

    flagged = verify_numbers(snap, facts)
    if flagged:
        say(f"facts: {len(flagged)} numbers do not match the snapshot; the fact checker gets the list")
    notes = "\n".join(flagged) or "none"

    say("writing: step check")
    answer = keep("actions.json", call(host, guides["check-actions"], steps_for_check(facts), snap, read_files=True, run=run))
    facts, changes = apply_action_check(facts, parse_json(answer))
    for line in changes:
        say(f"  {line}")
    if not (snap / "llm" / "facts-analysis.json").exists():
        write_private(snap / "llm" / "facts-analysis.json", facts_path.read_text(encoding="utf-8"))
    facts_text = json.dumps(facts, ensure_ascii=False, indent=1)
    write_private(facts_path, facts_text)

    say("writing: draft")
    draft = keep("draft.md", call(host, guides["writing"], facts_text, snap, run=run))

    say("writing: fact check")
    wrong = keep("facts-check.md", call(host, guides["check-facts"], _tagged(notes=notes, report=draft), snap, read_files=True, run=run))
    text = draft
    if wrong.strip() != "none":
        say("writing: replacing the sentences the fact check named")
        replaced = keep("replaced.md", call(host, guides["replace"], _tagged(facts=facts_text, report=draft, wrong=wrong), snap, run=run))
        problems = gate(draft, replaced)
        if problems:
            say(f"writing: the replacement was dropped: {'; '.join(problems)[:300]}")
        else:
            text = replaced

    report = snap / "report.md"
    write_private(report, assemble(snap, facts, text, language, rubric, version))
    return report

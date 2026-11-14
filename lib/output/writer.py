"""`kubegap write-report`: turn the analysis facts into the report, with separate agents.

The analysis ends in `llm/facts.json` (references/facts-<language>.md, schema 2). From there:

    check the facts (code) -> check the solutions (snapshot open) -> complete the facts (code)
      -> write: one agent for the overview sections, one per problem, side by side
      -> check the text against the facts and the snapshot (snapshot open) -> replace the sentences that were named -> assemble (code)

Code refuses facts that break the contract before any agent runs (lib/output/facts.check). The solution checker sees only the targets, the
scope and the solutions, never the analysis text, so it cannot repeat the analysis's mistakes; code merges what it found into the facts.
Each problem has its own writer because a problem is explained at length (how it comes about, cases, how it is watched, how it is solved in
practice) and one agent writing five of them shortens each. The writers and the replacer get no tools at all: input on stdin, text on
stdout, so cluster strings in the facts cannot lead to a command. The two checkers can only read files.
The prompts are files, one set per language and nothing shared: references/check-solutions-<language>.md, write-overview-<language>.md,
write-problem-<language>.md, check-facts-<language>.md, replace-<language>.md, and the glossary references/glossary-<language>.yaml.
Code writes what no agent should be trusted with: the title, the first screen, the cluster at a glance, the period, what the user decided
not to do, the since-last-report section, what is coming, the line per area, the limits of the run, the numbers and the check ids. It
refuses a replacement that drops a problem, a section, a code block or adds an address the facts do not hold.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..foundations import paths, shell
from ..foundations.snapshot import load_json, write_private
from . import facts as _facts
from . import glossary as _glossary
from . import sections as _sections
from .render import table

REFERENCES = paths.ROOT / "references"
HOSTS = ("claude", "codex")
CALL_TIMEOUT = 1800  # the solution check of a full report reads objects for a quarter of an hour
READ_ONLY_TOOLS = "Read,Grep,Glob"
WRITERS_AT_ONCE = 3
GUIDES = ("check-solutions", "write-overview", "write-problem", "check-facts", "replace")
AREAS = ("resources", "scaling", "observability", "traffic", "resilience", "hygiene", "storage", "security", "cost", "tenancy", "node OS", "platform")
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
HEADINGS = {
    "en": {
        "audit": "audit",
        "details": "Details and every table",
        "snapshot": "snapshot",
        "checks": "Checks behind each entry",
        "problem": "problem",
        "incident": "incident",
        "glance": "The cluster at a glance",
        "upcoming": "Coming up",
        "since": "Since the previous report",
        "areas": "Each area in one line",
        "broken": "Broken now",
        "happened": "What already happened",
        "next": "The next largest problems",
        "next_daily": "Serious and still there",
        "first_broken": "Broken now",
        "first_problems": "The {n} largest problems",
        "first_problems_from": "The largest problems (full run of {when})",
        "first_happened": "What already happened",
        "first_scale": "Scale",
        "period": "This covers {start} to {end}.",
        "period_none": "There is no earlier run to compare with, so this covers only what this run collected.",
        "sections": ["What is the matter", "Why it comes about", "How to watch it", "How it is solved", "Evidence", "Further reading"],
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
        "prev_work": "What the previous report advised",
        "state": "State",
        "proof": "Proof",
        "done": "done",
        "not_done": "still there",
        "appeared": "Appeared",
        "gone": "Went away",
        "no_report": "No earlier run of this mode has a report, so there is no advice to follow up.",
        "crit_new": "Checks that did not run last time, so these findings are new to the audit, not to the cluster",
        "crit_dropped": "Checks that did not run this time",
        "crit_rule": "Checks whose rule changed between the runs",
        "crit_thresholds": "Checks whose thresholds changed between the runs",
        "crit_severity": "Checks whose severity changed between the runs because the scale of the cluster or the check did",
        "none": "none",
    },
    "ko": {
        "audit": "점검",
        "details": "자세한 내용과 모든 표",
        "snapshot": "수집 자료",
        "checks": "항목별 체크",
        "problem": "문제",
        "incident": "사건",
        "glance": "클러스터 한눈에",
        "upcoming": "다가오는 일",
        "since": "지난 리포트 이후",
        "areas": "영역별 한 줄",
        "broken": "지금 깨져 있는 것",
        "happened": "이미 일어난 일",
        "next": "그다음으로 큰 문제",
        "next_daily": "지금 남아 있는 심각한 문제",
        "first_broken": "지금 깨져 있는 것",
        "first_problems": "가장 큰 문제 {n}개",
        "first_problems_from": "가장 큰 문제 ({when} full 점검)",
        "first_happened": "이미 일어난 일",
        "first_scale": "운영 규모",
        "period": "{start}부터 {end}까지 본 것이에요.",
        "period_none": "비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤어요.",
        "sections": ["무슨 일인가", "왜 생기나", "추천 점검 방법", "추천 해결 방안", "근거", "더 읽을 것"],
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
        "prev_work": "지난 리포트의 권고",
        "state": "상태",
        "proof": "근거",
        "done": "반영됨",
        "not_done": "남아 있음",
        "appeared": "새로 생긴 것",
        "gone": "없어진 것",
        "no_report": "리포트가 있는 이전 점검이 없어서 이어서 볼 권고가 없어요.",
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


def _entries(facts: dict):
    """(label, entry) for everything the report describes at length: what is broken now, the incidents, the problems."""
    for b in facts.get("broken_now") or []:
        yield f"broken {b.get('id')}", b
    for i in (facts.get("happened") or {}).get("incidents") or []:
        yield f"incident {i.get('id')}", i
    for p in facts.get("problems") or []:
        yield f"problem {p.get('id')}", p


def _numbered(facts: dict):
    """Every entry that carries a source: the numbers of each entry and the upcoming list."""
    for label, e in _entries(facts):
        for n in e.get("facts") or []:
            if isinstance(n, dict):
                yield f"{label}: {n.get('what')}", n
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


# ---------- the solution check and how what it found goes into the facts


def solutions_for_check(facts: dict, scale: dict | None) -> str:
    """What the solution checker gets: targets, scope and solutions of every problem, nothing the analysis wrote to explain them."""
    rows = [{"id": p.get("id"), "title": p.get("title"), "targets": p.get("targets") or [], "scope": p.get("scope") or {}, "solutions": p.get("solutions") or []} for p in facts.get("problems") or []]
    return json.dumps({"scale": (scale or {}).get("name"), "problems": rows}, ensure_ascii=False, indent=1)


def parse_json(text: str) -> dict:
    """The one JSON object in an agent's answer, with or without a code fence around it."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.MULTILINE).strip()
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end < 0:
        raise WriterError("the solution check did not answer with a JSON object")
    try:
        doc = json.loads(s[start : end + 1])
    except ValueError as e:
        raise WriterError(f"the solution check answered with broken JSON: {e}") from e
    if not isinstance(doc, dict):
        raise WriterError("the solution check did not answer with a JSON object")
    return doc


def apply_solution_check(facts: dict, result: dict) -> tuple[dict, list[str]]:
    """What the checker found, written into a copy of the facts, and one line per change for the run log. A caution is added to its solution,
    a dropped solution is removed with the reason kept on the problem, a corrected scope replaces the analysis's."""
    out = copy.deepcopy(facts)
    notes: list[str] = []
    by_id = {str(p.get("id")): p for p in out.get("problems") or []}

    def solution(entry: dict):
        p = by_id.get(str(entry.get("problem")))
        i = entry.get("solution")
        sols = (p or {}).get("solutions") or []
        return (p, sols[i]) if p is not None and isinstance(i, int) and 0 <= i < len(sols) else (p, None)

    for c in result.get("cautions") or []:
        p, s = solution(c)
        if s is None or not c.get("what"):
            notes.append(f"solution check named a solution that does not exist: problem {c.get('problem')} solution {c.get('solution')}")
            continue
        s.setdefault("cautions", []).append({"what": str(c["what"]), "read": c.get("read") or [], "from": "solution check"})
        notes.append(f"problem {p.get('id')} solution {c['solution'] + 1} caution: {c['what']}")
    drops: dict[str, set[int]] = {}
    for d in result.get("drop") or []:
        p, s = solution(d)
        if s is None:
            continue
        drops.setdefault(str(p.get("id")), set()).add(d["solution"])
        p.setdefault("dropped_solutions", []).append({"approach": s.get("approach"), "reason": d.get("reason")})
        notes.append(f"problem {p.get('id')} solution {d['solution'] + 1} dropped: {d.get('reason')}")
    for pid, idx in drops.items():
        p = by_id[pid]
        kept = [s for n, s in enumerate(p.get("solutions") or []) if n not in idx]
        if kept:
            p["solutions"] = kept
        else:  # a problem is never left without a way out: the last solution stays, with the reason as a caution the reader must see
            last = p["solutions"][-1]
            last.setdefault("cautions", []).append({"what": str(p["dropped_solutions"][-1].get("reason")), "read": [], "from": "solution check"})
            p["solutions"] = [last]
            notes.append(f"problem {pid}: every solution was dropped; the last one is kept with the reason as a caution")
    for sc in result.get("scope") or []:
        p = by_id.get(str(sc.get("problem")))
        if p is None:
            continue
        scope = p.setdefault("scope", {})
        for k in ("affected", "healthy", "not_checked"):
            if isinstance(sc.get(k), list):
                scope[k] = sc[k]
        notes.append(f"problem {p.get('id')} scope corrected")
    return out, notes


# ---------- what code writes


def _when(ts: str | None) -> str:
    return str(ts or "")[:16].replace("T", " ")


def _check_ids(facts: dict, h: dict) -> str:
    """The ids `/kubegap explain` takes, printed by code so no agent can leave them out."""
    rows = [f"- {h['incident'] if label.startswith('incident') else h['problem']} {e.get('id')}: " + ", ".join(f"`{i}`" for i in e["finding_ids"]) for label, e in _entries(facts) if e.get("finding_ids")]
    return f"{h['checks']}:\n\n" + "\n".join(rows) + "\n\n" if rows else ""


def last_full_problems(snap: Path) -> tuple[str, list[str]] | None:
    """(when, titles) of the problems the latest earlier full run of this cluster picked: a daily report shows them and picks none itself."""
    for s in sorted((p for p in snap.parent.iterdir() if p.is_dir() and p.name < snap.name and paths.snapshot_mode(p) == "full"), reverse=True):
        f = load_json(s / "llm" / "facts.json") or {}
        titles = [str(p.get("title")) for p in f.get("problems") or [] if isinstance(p, dict) and p.get("title")]
        if f.get("schema") == _facts.SCHEMA and titles and (s / "report.md").is_file():
            return _when((load_json(s / "inventory.json") or {}).get("taken_at")) or s.name, titles
    return None


def first_screen(snap: Path, facts: dict, language: str, mode: str) -> str:
    """The lines a reader sees first, all from the facts' titles: what is broken now, the largest problems, what happened, and the scale the
    severities are for. No agent writes a summary of its own text here."""
    h = HEADINGS[language]
    broken = [str(b.get("title")) for b in facts.get("broken_now") or [] if b.get("title")]
    incidents = [str(i.get("title")) for i in (facts.get("happened") or {}).get("incidents") or [] if i.get("title")]
    problems = [str(p.get("title")) for p in facts.get("problems") or [] if p.get("title")]
    lines = [f"{h['first_broken']}: " + (" · ".join(broken) or h["none"])]
    if mode == "full":
        lines.append(f"{h['first_problems'].format(n=len(problems))}: " + " ".join(f"{CIRCLED[i]} {t}" for i, t in enumerate(problems[: len(CIRCLED)])))
    else:
        last = last_full_problems(snap)
        if last:
            lines.append(f"{h['first_problems_from'].format(when=last[0])}: " + " ".join(f"{CIRCLED[i]} {t}" for i, t in enumerate(last[1][: len(CIRCLED)])))
    lines.append(f"{h['first_happened']}: " + (" · ".join(incidents) or h["none"]))
    scale = facts.get("scale") or {}
    if scale.get("name"):
        lines.append(f"{h['first_scale']}: {_sections.SCALE_WORD[language].get(scale['name'], scale['name'])}")
    return "\n".join(lines)


def period_line(facts: dict, h: dict) -> str:
    p = facts.get("period") or {}
    return h["period"].format(start=_when(p.get("from")), end=_when(p.get("to"))) if p.get("from") and p.get("to") else h["period_none"]


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
    """Lines for the findings that appeared, went away or changed level because the checks or the scale changed, read by code from diff.json so
    that no agent can present them as changes in the cluster. One line per bucket of `findings.criteria_changes`, counted per check: the first
    report after the scale question re-levels a hundred findings, and their ids belong in report-details.md, not here."""
    diff = load_json(snap / "diff.json") or {}
    crit = ((diff.get("findings") or {}).get("criteria_changes")) or {}
    out: list[str] = []
    for key, label in (("new_checks", "crit_new"), ("dropped_checks", "crit_dropped"), ("rule_changed", "crit_rule"), ("thresholds_changed", "crit_thresholds"), ("severity_changed", "crit_severity")):
        per_check: dict[str, int] = {}
        for r in crit.get(key) or []:
            if isinstance(r, dict) and r.get("id"):
                check_id = str(r.get("check") or r["id"])
                per_check[check_id] = per_check.get(check_id, 0) + 1
        if per_check:
            out += [f"**{h[label]}**", "", *(f"- `{c}` {n}" for c, n in sorted(per_check.items())), ""]
    return out


def since_section(facts: dict, h: dict, snap: Path, written: str | None) -> str:
    """ "Since the previous report": what the previous report advised and whether it was taken up, what appeared and what went away, as the
    overview writer wrote them from `since_last`, then the criteria changes from diff.json, which code writes. Without a baseline there is
    nothing to compare and code says so. The baseline itself is named once, in the numbers section; both use the same one."""
    out = [f"## {h['since']}", ""]
    if not (facts.get("period") or {}).get("baseline"):
        return "\n".join([*out, h["period_none"]])
    out += [(written or h["none"]).strip(), ""]
    out += criteria_changes(snap, h)
    return "\n".join(out).rstrip()


def area_lines(facts: dict, h: dict) -> str:
    summary = (facts.get("analysis") or {}).get("area_summary") or {}
    rows = [[a, summary.get(a) or h["none"]] for a in AREAS] if isinstance(summary, dict) and summary else []
    return f"## {h['areas']}\n\n" + (table([h["area"], h["what"]], rows) if rows else h["none"])


# ---------- what an agent's text must hold, and what a replacement may not do

_FENCE = re.compile(r"^```.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_PROBLEM = re.compile(r"^## \d+\. ", re.MULTILINE)
_H3 = re.compile(r"^### (.+?)\s*$", re.MULTILINE)
_URL = re.compile(r"https?://[^\s)>\]\"'`]+")


def _urls(text: str) -> set[str]:
    return {u.rstrip(".,;:") for u in _URL.findall(text)}


def allowed_urls(facts: dict) -> set[str]:
    """Every address the facts hold. An address in the report that is not among them was written from memory."""
    return _urls(json.dumps(facts, ensure_ascii=False))


def problem_issues(text: str, number: int, problem: dict, language: str, allowed: set[str]) -> list[str]:
    """What is wrong with the shape of one problem's text, as lines for the replacer: the title line, the six sections in order, addresses the
    facts do not hold. An example block is data and its addresses are not read."""
    h = HEADINGS[language]
    out = []
    if not text.lstrip().startswith(f"## {number}. "):
        out.append(f"- MISSING: problem {number} must start with the line `## {number}. {problem.get('title')}`")
    found = [x for x in _H3.findall(_FENCE.sub("", text)) if x in h["sections"]]
    if found != h["sections"]:
        out.append(f"- MISSING: problem {number} needs these sections in this order: {', '.join(h['sections'])} (found: {', '.join(found) or 'none'})")
    for u in sorted(_urls(_FENCE.sub("", text)) - allowed):
        out.append(f'- quote: "{u}"\n  fact: this address is not in the facts; remove the link or the sentence that depends on it')
    return out


def gate(before: str, after: str, allowed: set[str]) -> list[str]:
    """What a replacement may not do: drop or change a code block, change the number of problems, lose a section, or add an address the facts do not hold."""
    out = [f"this code block is gone or changed: {f.splitlines()[1] if f.count(chr(10)) > 1 else f}" for f in _FENCE.findall(before) if f not in after]
    if len(_PROBLEM.findall(before)) != len(_PROBLEM.findall(after)):
        out.append("the number of problems changed")
    if len(_H3.findall(_FENCE.sub("", before))) > len(_H3.findall(_FENCE.sub("", after))):  # a section may be added (one the shape check asked for), never lost
        out.append("a section is gone")
    added = _urls(_FENCE.sub("", after)) - _urls(_FENCE.sub("", before)) - allowed
    if added:
        out.append(f"an address the facts do not hold was added: {min(added)}")
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


def _split_overview(text: str, h: dict) -> dict[str, str]:
    """The overview writer's text cut at its headings: {"broken": …, "happened": …, "next": …, "since": …}, each without its heading line."""
    marks = [(k, m.start(), m.end()) for k in ("broken", "happened", "next", "since") for m in [re.search(rf"^## {re.escape(h[k])}[ \t]*$", text, re.MULTILINE)] if m]
    marks.sort(key=lambda x: x[1])
    return {k: text[end : (marks[i + 1][1] if i + 1 < len(marks) else len(text))].strip() for i, (k, _start, end) in enumerate(marks)}


def assemble(snap: Path, facts: dict, overview: str, problems: list[str], language: str, rubric: str, version: str, skipped: list[dict] | None = None) -> str:
    """The report in its fixed order. Code writes the title, the first screen and every section that can be computed; the agents' text fills
    what is broken now, what happened, the problems and the next largest ones."""
    h = HEADINGS[language]
    inv = load_json(snap / "inventory.json") or {}
    cluster = inv.get("cluster") or {}
    mode = paths.snapshot_mode(snap)
    parts = _split_overview(overview, h)
    title = f"# {cluster.get('cluster_name') or inv.get('context') or snap.parent.name} — {mode} {h['audit']}, {_when(inv.get('taken_at')) or snap.name}"
    out = [title, first_screen(snap, facts, language, mode), glance(snap, h)]
    if parts.get("broken"):
        out.append(f"## {h['broken']}\n\n{parts['broken']}")
    out.append(f"## {h['happened']}\n\n{period_line(facts, h)}\n\n{parts.get('happened') or h['none']}")
    out += [p.strip() for p in problems]
    out.append(f"## {h['next'] if mode == 'full' else h['next_daily']}\n\n{parts.get('next') or h['none']}")
    out += [_sections.declined(snap, language), since_section(facts, h, snap, parts.get("since")), upcoming(facts, h)]
    if mode == "full":
        out.append(area_lines(facts, h))
    out += [_sections.limits(facts, snap, language, skipped), _sections.numbers(snap, language)]
    tail = f"{h['details']}: [`report-details.md`](report-details.md) · kubegap {version}, rubric {rubric} · {h['snapshot']} `{snap}`"
    return space_blocks("\n\n".join(out)) + f"\n\n{_check_ids(facts, h)}{tail}\n"


# ---------- the run


def write_report(snap: Path, language: str, host: str, rubric: str, version: str, *, skipped: list[dict] | None = None, say: Callable = print, run: Callable = shell.run) -> Path:
    """Write `report.md` from `llm/facts.json`. Each agent's text stays in `llm/writing/` so a poor result can be traced; the facts as the
    analysis wrote them stay in `llm/facts-analysis.json` and `llm/facts.json` holds them with the solution check merged in and the computed
    parts added. `skipped` is the first-run questions the user skipped (lib/commands/firstrun.skipped), for the limits section."""
    facts_path = snap / "llm" / "facts.json"
    if not facts_path.is_file():
        raise WriterError(f"{facts_path} does not exist. The analysis writes it first (references/facts-{language}.md)")
    if language not in HEADINGS:
        raise WriterError(f"no prompts for language {language}")
    guides = {name: REFERENCES / f"{name}-{language}.md" for name in GUIDES}
    absent = [g.name for g in guides.values() if not g.is_file()]
    if absent:
        raise WriterError(f"the guides for language {language} are not written yet ({', '.join(absent)}); the Korean report is settled first and the English one follows")
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    mode = paths.snapshot_mode(snap)
    broken = _facts.check(facts, snap, mode)
    if broken:
        raise WriterError(f"llm/facts.json breaks {len(broken)} rules of the contract; fix them and run `kubegap check-facts` until it prints none:\n" + "\n".join(f"- {b}" for b in broken[:20]))
    work = snap / "llm" / "writing"
    paths.ensure_private_dir(work, base=snap)
    h = HEADINGS[language]

    def keep(name: str, text: str) -> str:
        write_private(work / name, text)
        return text

    flagged = verify_numbers(snap, facts)
    if flagged:
        say(f"facts: {len(flagged)} numbers do not match the snapshot; the fact checker gets the list")

    if not (snap / "llm" / "facts-analysis.json").exists():
        write_private(snap / "llm" / "facts-analysis.json", facts_path.read_text(encoding="utf-8"))
    scale = (load_json(snap / "findings-draft.json") or {}).get("scale")
    if facts.get("problems"):
        say("writing: solution check")
        answer = keep("solutions.json", call(host, guides["check-solutions"], solutions_for_check(facts, scale), snap, read_files=True, run=run))
        facts, changes = apply_solution_check(facts, parse_json(answer))
        for line in changes:
            say(f"  {line}")
    facts = _facts.complete(facts, snap)
    facts_text = json.dumps(facts, ensure_ascii=False, indent=1)
    write_private(facts_path, facts_text)

    terms = _glossary.load(language)
    glossary_text = _glossary.as_text(terms) or h["none"]
    inv = load_json(snap / "inventory.json") or {}
    cluster = json.dumps(
        {"name": (inv.get("cluster") or {}).get("cluster_name") or inv.get("context"), "platform": (inv.get("cluster") or {}).get("platform"), "scale": facts.get("scale"), "period": facts.get("period"), "mode": mode}, ensure_ascii=False
    )
    overview_facts = {k: facts.get(k) for k in ("broken_now", "happened", "next", "since_last")}
    overview_facts["problems"] = [{"id": p.get("id"), "title": p.get("title")} for p in facts.get("problems") or []]  # only so an incident can name the problem it exposed
    problems = facts.get("problems") or []

    def write_overview() -> str:
        return call(host, guides["write-overview"], _tagged(cluster=cluster, glossary=glossary_text, facts=json.dumps(overview_facts, ensure_ascii=False, indent=1)), snap, run=run)

    def write_problem(n: int, p: dict) -> str:
        return call(host, guides["write-problem"], _tagged(number=str(n), cluster=cluster, glossary=glossary_text, problem=json.dumps(p, ensure_ascii=False, indent=1)), snap, run=run)

    say(f"writing: the overview and {len(problems)} problems")
    with ThreadPoolExecutor(max_workers=WRITERS_AT_ONCE) as pool:
        f_over = pool.submit(write_overview)
        f_probs = [pool.submit(write_problem, n, p) for n, p in enumerate(problems, 1)]
        overview = keep("overview.md", f_over.result())
        texts = [keep(f"problem-{n}.md", f.result()) for n, f in enumerate(f_probs, 1)]

    allowed = allowed_urls(facts)
    shape = [x for n, (p, t) in enumerate(zip(problems, texts, strict=True), 1) for x in problem_issues(t, n, p, language, allowed)]
    draft = keep("draft.md", "\n\n".join([overview.strip(), *(t.strip() for t in texts)]) + "\n")

    say("writing: fact check")
    notes = "\n".join(flagged) or "none"
    wrong = keep("facts-check.md", call(host, guides["check-facts"], _tagged(notes=notes, report=draft), snap, read_files=True, run=run))
    to_fix = [] if wrong.strip() == "none" else [wrong.strip()]
    to_fix += shape + _glossary.find(draft, terms)
    text = draft
    if to_fix:
        say(f"writing: replacing what the checks named ({len(shape)} shape, {len(_glossary.find(draft, terms))} terms{', facts' if wrong.strip() != 'none' else ''})")
        replaced = keep("replaced.md", call(host, guides["replace"], _tagged(facts=facts_text, glossary=glossary_text, report=draft, wrong="\n".join(to_fix)), snap, run=run))
        refused = gate(draft, replaced, allowed)
        if refused:
            say(f"writing: the replacement was dropped: {'; '.join(refused)[:300]}")
        else:
            text = replaced
    left = _glossary.find(text, terms)
    if left:
        say(f"writing: {len(left)} sentences still use a spelling the glossary avoids (llm/writing/glossary-left.txt)")
        keep("glossary-left.txt", "\n".join(left) + "\n")

    first = _PROBLEM.search(text)
    overview_text, problem_text = (text[: first.start()], text[first.start() :]) if first else (text, "")
    parts = [p for p in re.split(r"(?=^## \d+\. )", problem_text, flags=re.MULTILINE) if p.strip()]
    report = snap / "report.md"
    write_private(report, assemble(snap, facts, overview_text, parts, language, rubric, version, skipped))
    return report

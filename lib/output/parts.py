"""The parts of a report that code writes, shared by the full and the daily report: the headings in each language, the cluster at a glance,
the findings that differ because kubegap's own criteria changed, and how blocks are spaced. No agent writes these, so they cannot drift from
the snapshot."""

from __future__ import annotations

import re
from pathlib import Path

from ..foundations.snapshot import load_json
from .render import table

AREA_WORD = {
    "영역별 한 줄": {
        "resources": "리소스",
        "scaling": "스케일링",
        "observability": "모니터링",
        "traffic": "트래픽",
        "resilience": "가용성",
        "hygiene": "설정 관리",
        "storage": "스토리지",
        "security": "보안",
        "cost": "비용",
        "tenancy": "멀티테넌시",
        "node OS": "노드 OS",
        "platform": "플랫폼",
    }
}


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
        "first_broken": "Broken now",
        "first_problems": "The {n} largest problems",
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
        "count": "{n}",
        "stores": "Metrics and log stores",
        "versions": "Kubernetes",
        "ready": "{ready} of {count} Ready",
        "pods_v": "{running} running, {pending} pending, {failed} failed",
        "ns_v": "{count}, {prod} production",
        "no_store": "none",
        "no_loki": "no Loki",
        "prev_work": "What the previous report advised",
        "state": "State",
        "proof": "Proof",
        "done": "done",
        "not_done": "still there",
        "appeared": "Appeared",
        "gone": "Went away",
        "no_report": "No earlier run of this mode has a report, so there is no advice to follow up.",
        "crit_head": "The cluster is the same; these differ because what kubegap checks changed",
        "crit_new": "Checks that ran for the first time",
        "crit_dropped": "Checks that did not run this time",
        "crit_rule": "Checks whose rule changed",
        "crit_thresholds": "Checks whose thresholds changed",
        "crit_severity": "Checks whose severity changed because the scale or the check did",
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
        "first_broken": "지금 깨져 있는 것",
        "first_problems": "가장 큰 문제 {n}개",
        "first_happened": "이미 일어난 일",
        "first_scale": "운영 규모",
        "period": "{start}부터 {end}까지 본 것입니다.",
        "period_none": "비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.",
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
        "count": "{n}개",
        "stores": "메트릭·로그 저장소",
        "versions": "Kubernetes",
        "ready": "{count}대 중 Ready {ready}대",
        "pods_v": "실행 {running}, 대기 {pending}, 실패 {failed}",
        "ns_v": "{count}개, 프로덕션 {prod}개",
        "no_store": "없음",
        "no_loki": "Loki 없음",
        "prev_work": "지난 리포트의 권고",
        "state": "상태",
        "proof": "근거",
        "done": "반영됨",
        "not_done": "남아 있음",
        "appeared": "새로 생긴 것",
        "gone": "없어진 것",
        "no_report": "리포트가 있는 이전 점검이 없어서 이어서 볼 권고가 없습니다.",
        "crit_head": "클러스터는 그대로인데 kubegap의 기준이 바뀌어 달라진 것",
        "crit_new": "이번에 처음 실행한 점검",
        "crit_dropped": "이번에 실행하지 않은 점검",
        "crit_rule": "판정 기준이 바뀐 점검",
        "crit_thresholds": "임계값이 바뀐 점검",
        "crit_severity": "운영 규모나 기준이 바뀌어 심각도가 달라진 점검",
        "none": "없음",
    },
}


def _when(ts: str | None) -> str:
    return str(ts or "")[:16].replace("T", " ")


def glance(snap: Path, h: dict, *, names: bool = True) -> str:
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
        [h["components"], f"{len(inv.get('components_present') or [])}: " + ", ".join(inv.get("components_present") or []) if names else h["count"].format(n=len(inv.get("components_present") or []))],
        [h["stores"], f"{prom.get('kind') or h['no_store']} {prom.get('version') or ''}".strip() + " / " + (f"{loki.get('kind') or ''} {loki.get('version') or ''}".strip() if loki.get("ok") else h["no_loki"])],
        [h["versions"], f"{cluster.get('server_version') or ''} ({cluster.get('platform') or ''})".strip()],
    ]
    return f"## {h['glance']}\n\n" + table([h["item"], h["value"]], rows)


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
            out += [f"{h[label]}:", "", *(f"- `{c}` {n}" for c, n in sorted(per_check.items())), ""]
    return [f"**{h['crit_head']}**", "", *out] if out else out


_FENCE = re.compile(r"^```.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)


_H3 = re.compile(r"^### (.+?)\s*$", re.MULTILINE)


_URL = re.compile(r"https?://[^\s)>\]\"'`]+")


def _urls(text: str) -> set[str]:
    return {u.rstrip(".,;:") for u in _URL.findall(text)}


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

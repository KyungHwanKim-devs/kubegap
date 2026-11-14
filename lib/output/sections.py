"""The sections of report.md that code writes from the snapshot, so no agent can get them wrong: the numbers and what they are compared
with, what the user decided not to do, and what this run could not judge.

Each takes the snapshot (and the facts where the analysis adds entries) and returns Markdown. The headings are per language; the Korean ones
are written as Korean, not translated.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..foundations import paths
from ..foundations.snapshot import load_json
from .render import table

SEVERITIES = ("critical", "high", "medium", "low")
PLATFORM_COMPONENTS = ("k3s", "rke2", "eks-managed-addons")  # the platform itself: its checks live in the platform collector, not in a folder of that name

TEXT = {
    "en": {
        "numbers": "Numbers",
        "severity": "Severity",
        "resolved": "fail resolved since",
        "new": "fail new since",
        "baseline": "Compared with the {mode} run of {when}, the last one that has a report.",
        "baseline_unreported": "Compared with the {mode} run of {when}. No earlier run has a report, so there is no list of work to follow up.",
        "no_baseline": "No earlier {mode} run to compare with.",
        "criteria": "{n} findings differ because the checks or the scale changed, not the cluster; they are not counted in the two columns on the right.",
        "scale": "Severity is for a cluster run at scale {scale}{source}.",
        "guessed": " (nobody answered the question, so this is a guess from {nodes} nodes; `/kubegap setup` asks)",
        "declined": "Decided not to do",
        "declined_none": "Nothing is recorded. A decision not to act on a finding goes into `suppress` in the config file with its reason, and is listed here.",
        "until": "until {until}",
        "no_reason": "no reason recorded",
        "limits": "Limits of this run",
        "no-data": "Not judged because the cluster does not hold the data",
        "unsupported": "Not read by kubegap yet",
        "skipped": "Left out by choice",
        "weakens": "Weaker for it",
        "to_see": "To see it",
        "components": "{n} components were read only through their objects and metrics; kubegap has no checks of their own for them: {names}.",
        "components_weakens": "a fault inside one of these components is not in this report",
        "skipped_to_see": "`/kubegap setup` asks the question again",
        "none": "none",
    },
    "ko": {
        "numbers": "숫자",
        "severity": "심각도",
        "resolved": "지난 리포트 이후 해결된 fail",
        "new": "지난 리포트 이후 새로 생긴 fail",
        "baseline": "비교 기준은 {when} {mode} 점검이에요. 리포트가 있는 가장 최근 점검이에요.",
        "baseline_unreported": "비교 기준은 {when} {mode} 점검이에요. 리포트가 있는 이전 점검이 없어서 이어서 볼 권고 목록은 없어요.",
        "no_baseline": "비교할 이전 {mode} 점검이 없어요.",
        "criteria": "{n}건은 클러스터가 아니라 점검 기준이나 운영 규모가 바뀌어서 달라진 것이라 오른쪽 두 칸에 세지 않았어요.",
        "scale": "심각도는 운영 규모 {scale} 기준이에요{source}.",
        "guessed": " (규모를 묻지 못해 노드 {nodes}대로 짐작했어요. `/kubegap setup`에서 고를 수 있어요)",
        "declined": "하지 않기로 한 것",
        "declined_none": "기록된 것이 없어요. 어떤 항목을 조치하지 않기로 정했다면 설정 파일의 `suppress`에 이유와 함께 적어 주세요. 그러면 여기에 나와요.",
        "until": "{until}까지",
        "no_reason": "이유가 적혀 있지 않아요",
        "limits": "이번 점검의 한계",
        "no-data": "클러스터에 데이터가 없어서 판단하지 못한 것",
        "unsupported": "kubegap이 아직 읽지 못하는 것",
        "skipped": "보지 않기로 고른 것",
        "weakens": "약해지는 결론",
        "to_see": "보려면",
        "components": "컴포넌트 {n}개는 오브젝트와 메트릭으로만 읽었어요. kubegap에 전용 점검 항목이 없어요: {names}.",
        "components_weakens": "이 컴포넌트 안에서 생긴 이상은 이 리포트에 나오지 않아요",
        "skipped_to_see": "`/kubegap setup`에서 다시 고르기",
        "none": "없음",
    },
}
SCALE_WORD = {"en": {"small": "small", "medium": "medium", "large": "large"}, "ko": {"small": "소형", "medium": "중형", "large": "대형"}}
MODE_WORD = {"en": {"daily": "daily", "full": "full"}, "ko": {"daily": "daily", "full": "full"}}


def _when(taken_at: str | None, name: str) -> str:
    return str(taken_at or name)[:16].replace("T", " ")


def numbers(snap: Path, language: str) -> str:
    """Fail and warn per severity as the first pass counted them, and against one baseline: how many failures went away and how many are new.
    A net change hides both ("four things were fixed and the failures only went up"), so the two are shown apart. The baseline is the one
    `diff` used (paths.previous_snapshot: the last run of this mode that has a report)."""
    t = TEXT[language]
    fd = load_json(snap / "findings-draft.json") or {}
    diff = load_json(snap / "diff.json") or {}
    mode = MODE_WORD[language][paths.snapshot_mode(snap)]
    found = list(fd.get("findings") or [])
    fail = Counter(f["severity_default"] for f in found if f.get("status") == "fail")
    warn = Counter(f["severity_default"] for f in found if f.get("status") == "warn")
    df = diff.get("findings") or {}
    has_base = bool(diff.get("a")) and "missing" not in df
    resolved = Counter(r.get("severity_default") for r in df.get("resolved") or [] if r.get("status") == "fail")
    new = Counter(r.get("severity_default") for r in df.get("new") or [] if r.get("status") == "fail")
    # a finding that went from warn to fail is a new failure and one that went from fail to warn or below is a resolved one
    for c in df.get("changed") or []:
        st, sev = c.get("status") or [None, None], c.get("severity_default") or [None, None]
        if st[0] != "fail" and st[1] == "fail":
            new[sev[1]] += 1
        if st[0] == "fail" and st[1] != "fail":
            resolved[sev[0]] += 1
    rows = [[s, fail.get(s, 0), warn.get(s, 0), *([resolved.get(s, 0), new.get(s, 0)] if has_base else [])] for s in SEVERITIES]
    head = [t["severity"], "fail", "warn", *([t["resolved"], t["new"]] if has_base else [])]
    lines = [f"## {t['numbers']}", ""]
    scale = fd.get("scale") or {}
    if scale.get("name"):
        source = t["guessed"].format(nodes=scale.get("nodes")) if scale.get("source") == "guessed" else ""
        lines += [t["scale"].format(scale=SCALE_WORD[language].get(scale["name"], scale["name"]), source=source), ""]
    if has_base:
        a = Path(diff["a"])
        a_inv = load_json(a / "inventory.json") or {}
        key = "baseline" if (a / "report.md").is_file() else "baseline_unreported"
        lines += [t[key].format(when=_when(a_inv.get("taken_at"), a.name), mode=mode), ""]
    else:
        lines += [t["no_baseline"].format(mode=mode), ""]
    lines.append(table(head, rows))
    n_crit = sum(len(v) for k, v in (df.get("criteria_changes") or {}).items() if isinstance(v, list))
    if has_base and n_crit:
        lines += ["", t["criteria"].format(n=n_crit)]
    return "\n".join(lines)


def declined(snap: Path, language: str) -> str:
    """What the user decided not to act on: the suppressions of the config file, with the reason and the date they wrote. Nothing else is a
    decision: a sentence in a report that says "as decided" must be traceable to a line the user can read and change."""
    t = TEXT[language]
    fd = load_json(snap / "findings-draft.json") or {}
    groups: dict[tuple, list[str]] = {}
    for f in fd.get("suppressed") or []:
        by = f.get("suppressed_by") or {}
        groups.setdefault((f.get("check"), by.get("reason"), by.get("until")), []).append(f.get("target"))
    lines = [f"## {t['declined']}", ""]
    if not groups:
        return "\n".join([*lines, t["declined_none"]])
    for (check_id, reason, until), targets in sorted(groups.items(), key=lambda kv: str(kv[0][0])):
        tail = f" ({t['until'].format(until=until)})" if until else ""
        lines.append(f"- `{check_id}` — {', '.join(str(x) for x in targets[:8])}{' …' if len(targets) > 8 else ''}: {reason or t['no_reason']}{tail}")
    return "\n".join(lines)


def unsupported_components(snap: Path) -> list[str]:
    """Installed components kubegap has no collector folder for: detected and read through the generic object and metric steps, never through checks of their own."""
    inv = load_json(snap / "inventory.json") or {}
    return sorted(c for c in inv.get("components_present") or [] if c not in PLATFORM_COMPONENTS and not (paths.COLLECTORS_DIR / c / "checks.yaml").is_file())


def limits(facts: dict, snap: Path, language: str, skipped: list[dict] | None = None) -> str:
    """What this run could not judge, in three groups that mean different things to the reader: the cluster does not hold the data (turn it on
    and the next run sees it), kubegap does not read it yet, or the user chose to leave it out. Code adds what it knows itself: the components
    without checks of their own and the first-run questions that were skipped (`skipped`, from lib/commands/firstrun.skipped, passed in by the
    command). Each line says which conclusion of the report is weaker for it; an item that weakens nothing is not a limit."""
    t = TEXT[language]
    groups: dict[str, list[str]] = {k: [] for k in ("no-data", "unsupported", "skipped")}

    def line(what: str, weakens: str, to_see: str | None) -> str:
        return f"- {what}\n  - {t['weakens']}: {weakens}." + (f"\n  - {t['to_see']}: {to_see}." if to_see else "")

    for lim in facts.get("limits") or []:
        if isinstance(lim, dict) and lim.get("kind") in groups and lim.get("what") and lim.get("weakens"):
            groups[lim["kind"]].append(line(str(lim["what"]), str(lim["weakens"]).rstrip("."), str(lim["to_see"]).rstrip(".") if lim.get("to_see") else None))
    comps = unsupported_components(snap)
    if comps:
        groups["unsupported"].append(line(t["components"].format(n=len(comps), names=", ".join(comps)), t["components_weakens"], None))
    for s in skipped or []:
        groups["skipped"].append(line(f"{s.get('header')}.", "; ".join(s.get("gain") or []).rstrip("."), t["skipped_to_see"].rstrip(".")))
    out = [f"## {t['limits']}", ""]
    for kind in ("no-data", "unsupported", "skipped"):
        out += [f"**{t[kind]}**", "", *(groups[kind] or [f"- {t['none']}"]), ""]
    return "\n".join(out).rstrip()

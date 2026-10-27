"""Render `report-details.md`: the reference half of a report, assembled by code from snapshot files plus the fragments the LLM wrote.

A report has two files. `report.md` is for people and is written entirely by the LLM (Top N problems with evidence, cause, action and
learning points; what changed; what the run could not see). `report-details.md` is for the next run's agent and for anyone who wants to
dig: every table that can be produced mechanically is produced here (counts, critical/high list, absence, suppressed, collectors run,
checks evaluated, signature matches, the full first-pass table), and the parts that need judgment come from small Markdown fragments the
LLM drops into `<snapshot>/llm/` before calling `scripts/kubegap render-details`:

  llm/adjustments.md   final severity/status changes and recounted aggregates against the first pass, with reasons (two tables: Severities, Recounted aggregates)
  llm/changes.md       why things changed since the previous run of the same mode (narrative)
  llm/areas.md         per-area detail (full mode)
  llm/files-read.md    raw files the LLM opened directly
  llm/tool-notes.md    defects or doubts about kubegap itself, with reproduction evidence

A missing fragment renders as "(not written this run)" so the file is always complete and the next run can tell what was skipped.
Headings and fixed phrases follow the report language (`--language`); data inside tables (check ids, evidence strings, numbers) stays
English because it comes from the check definitions. Masking (`scripts/kubegap mask`) runs after rendering.
"""

from __future__ import annotations

from pathlib import Path

from . import __version__, paths
from .snapshot import load_json

SEVERITIES = ("critical", "high", "medium", "low", "info")
FRAGMENTS = ("adjustments", "changes", "areas", "files-read", "tool-notes")

# Headings and fixed phrases per language. English is the key; a language without an entry falls back to the key.
LABELS: dict[str, dict[str, str]] = {
    "en": {},
    "ko": {
        "title": "# kubegap 리포트 세부 — {cluster} (`{context}`), {mode} 모드",
        "intro": "리포트의 참조용 절반입니다. `scripts/kubegap render-details` 가 스냅샷 파일과 `llm/` 의 LLM 조각으로 조립했습니다. 사람이 읽는 리포트는 옆의 `report.md` 입니다. 표 안의 데이터, 즉 체크 id·근거 문장·숫자는 영어 그대로입니다.",
        "Item": "항목",
        "Value": "값",
        "kube context / cluster": "kube 컨텍스트 / 클러스터",
        "Run time / mode": "실행 시각 / 모드",
        "Profile": "프로파일",
        "kubegap / rubric / signatures": "kubegap / 룰 / 서명 카탈로그",
        "Nodes / namespaces / pods / CRDs": "노드 / 네임스페이스 / 파드 / CRD",
        "Components": "컴포넌트",
        "Metrics store": "메트릭 저장소",
        "Log store": "로그 저장소",
        "Node access": "노드 접근",
        "Snapshot": "스냅샷",
        "## 1. Counts (first pass) and the LLM's adjustments": "## 1. 1차 결과 집계와 최종 조정",
        "Severity (default)": "심각도(기본)",
        "vs. previous run of this mode": "같은 모드의 지난 실행 대비",
        "no previous run of this mode": "같은 모드의 지난 실행 없음",
        "### 1-1. Final judgment vs. first pass (adjustments)": "### 1-1. 1차 결과와 최종 결과의 차이",
        "## 2. Critical and high failing now (first pass)": "## 2. 지금 fail 인 critical·high, 1차 결과",
        "Finding": "발견 사항",
        "Severity": "심각도",
        "Consecutive runs": "연속 실행 수",
        "Evidence": "근거",
        "## 3. Changes since the previous run of this mode": "## 3. 같은 모드의 지난 실행 이후 변화",
        "### 3-1. Why things changed": "### 3-1. 왜 바뀌었나",
        "## 4. Detail per area": "## 4. 영역별 세부",
        "## 5. Absence list": "## 5. 없는 것 목록",
        "## 6. Suppressed, tool missing, not collected": "## 6. 억제, 도구 없음, 미수집",
        "## 7. Appendix": "## 7. 부록",
        "### 7-1. Collectors and steps run": "### 7-1. 실행한 수집기와 스텝",
        "### 7-2. Checks evaluated": "### 7-2. 평가한 체크",
        "### 7-3. Signature matches and unclassified errors": "### 7-3. 서명 일치와 미분류 오류",
        "### 7-4. Raw files the LLM read directly": "### 7-4. LLM 이 직접 읽은 원본 파일",
        "### 7-5. Full first-pass status (every fail and warn, code results as-is)": "### 7-5. 1차 결과 전체, 모든 fail 과 warn 을 코드 결과 그대로",
        "### 7-6. Tool notes (about kubegap itself)": "### 7-6. 도구 메모, kubegap 자체에 대한 것",
        "(not written this run)": "(이번 실행에서 쓰지 않음)",
        "(daily mode: no per-area detail; see section 2 and `report.md`)": "(daily 모드에는 영역별 세부가 없습니다. 2절과 `report.md` 를 보세요)",
        "No earlier {mode} snapshot to compare with.": "비교할 이전 {mode} 스냅샷이 없습니다.",
    },
}


def _cell(v) -> str:
    s = str(v if v is not None else "")
    return s.replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out) if rows else "\n".join(out) + "\n| (none) |" + " |" * (len(headers) - 1)


def _fragment(snap: Path, name: str, missing: str) -> str:
    p = snap / "llm" / f"{name}.md"
    try:
        text = p.read_text(encoding="utf-8").strip()
    except OSError:
        return missing
    return text or missing


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


def render_details(snap: Path, language: str = "en") -> Path:
    lab = LABELS.get(language) or {}

    def L(text: str) -> str:
        return lab.get(text, text)

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
        or "Reference half of the report, assembled by `scripts/kubegap render-details` from the snapshot files plus the LLM's fragments in `llm/`. The human report is `report.md` next to this file. Headings follow the report language; data inside tables is English."
    )
    w("")
    prom = stores.get("prometheus") or {}
    logs = stores.get("loki") or {}
    w(
        _table(
            [L("Item"), L("Value")],
            [
                [L("kube context / cluster"), f"`{inv.get('context')}` / {cluster.get('cluster_name')} ({cluster.get('platform')}, {cluster.get('server_version')})"],
                [L("Run time / mode"), f"{inv.get('taken_at')} / {mode} (collection {coll.get('seconds_total')} s, {len(coll.get('mode_skipped_steps') or [])} steps skipped by mode, {len(coll.get('failed_steps') or [])} failed)"],
                [L("Profile"), f"`{(inv.get('profile') or {}).get('name')}` ({(inv.get('profile') or {}).get('source')})"],
                [L("kubegap / rubric / signatures"), f"{fd.get('kubegap') or __version__} / {fd.get('rubric_version')} / {inv.get('signatures_version')}"],
                [L("Nodes / namespaces / pods / CRDs"), f"{nodes.get('count')} (Ready {nodes.get('ready')}) / {(inv.get('namespaces') or {}).get('count')} / {(inv.get('pods') or {}).get('count')} / {(inv.get('crds') or {}).get('count')}"],
                [f"{L('Components')} ({len(inv.get('components_present') or [])})", ", ".join(inv.get("components_present") or [])],
                [
                    L("Metrics store"),
                    f"{prom.get('kind') or 'none'} {prom.get('version') or ''} retention {(prom.get('retention') or {}).get('time')} / size {(prom.get('retention') or {}).get('size')} via {prom.get('access')}" if prom else "none",
                ],
                [L("Log store"), f"{logs.get('kind') or 'none'} {logs.get('version') or ''}".strip() if logs.get("ok") else "none (Loki not found)"],
                [L("Node access"), f"{na.get('method')} ({', '.join(na.get('reasons') or [])}); SSM unregistered {len(na.get('ssm_unregistered') or [])}"],
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
    w(_table([L("Severity (default)"), "fail", "warn", L("vs. previous run of this mode")], rows))
    w("")
    bs = (fd.get("checks") or {}).get("by_status") or {}
    w(
        f"Checks {(fd.get('checks') or {}).get('total')}: evaluated {bs.get('done', 0)}, disabled by profile {bs.get('disabled', 0)}, skipped {bs.get('skip', 0)}, not collected in this mode {bs.get('not-collected', 0)}, errors {bs.get('error', 0)}, tool missing {bs.get('tool-missing', 0)}, LLM-judged {bs.get('llm', 0)}. Suppressed findings {len(fd.get('suppressed') or [])}."
    )
    w("")
    w(L("### 1-1. Final judgment vs. first pass (adjustments)"))
    w("")
    w(_fragment(snap, "adjustments", missing))
    w("")

    # ---- 2. critical and high now
    w(L("## 2. Critical and high failing now (first pass)"))
    w("")
    persisted = _persisted(diff)
    ch = [f for f in findings if f.get("status") == "fail" and f.get("severity_default") in ("critical", "high")]
    w(_table([L("Finding"), L("Severity"), L("Consecutive runs"), L("Evidence")], [[f"`{f['id']}`", f.get("severity_default"), persisted.get(f["id"], "") or "", (f.get("evidence") or "")[:220]] for f in ch]))
    if not persisted:
        w("")
        w("(consecutive-run counts need diff.json; none for this snapshot)")
    w("")

    # ---- 3. changes
    w(L("## 3. Changes since the previous run of this mode"))
    w("")
    if diff:
        df = diff.get("findings") or {}
        rv = df.get("rubric_version")
        w(f"Compared `{diff.get('a_name')}` → `{diff.get('b_name')}` (rubric {rv[0] if isinstance(rv, list) and rv else rv} → {rv[1] if isinstance(rv, list) and len(rv) > 1 else rv}).")
        w("")
        for key, label in (("new", "New"), ("resolved", "Resolved"), ("changed", "Changed"), ("rename_suspects", "Rename suspects")):
            items = df.get(key) or []
            w(
                f"- **{label} ({len(items)})**: "
                + (", ".join(f"`{i.get('id') if isinstance(i, dict) else i}`" + (f" ({i.get('status')}/{i.get('severity_default')})" if isinstance(i, dict) and i.get("status") else "") for i in items) if items else "none")
            )
        ob = diff.get("objects") or {}
        w(
            f"- **Objects**: added {len(ob.get('added') or [])}, removed {len(ob.get('removed') or [])}, changed {len(ob.get('changed') or [])}"
            + (": " + ", ".join(f"`{c.get('kind')}/{c.get('name')}` {','.join(c.get('changed_fields') or [])}" for c in (ob.get("changed") or [])[:12]) if ob.get("changed") else "")
        )
        evc = [e for e in ((diff.get("events") or {}).get("changed") or []) if e.get("type") == "Warning"]
        w("- **Warning events**: " + (", ".join(f"{e.get('reason')} {e.get('delta'):+d} ({(e.get('objects_top_after') or [''])[0]})" for e in evc[:10]) if evc else "no change"))
        pers = df.get("persisted") or {}
        if pers:
            w(
                f"- **Persisted (Toil)**: {pers.get('persisted_all')} findings present in all {pers.get('runs_checked')} runs checked, {pers.get('persisted_3plus')} in 3 or more; top checks: "
                + ", ".join(f"`{k}` {v}" for k, v in list((pers.get("toil_candidates_by_check") or {}).items())[:8])
            )
    else:
        w(L("No earlier {mode} snapshot to compare with.").format(mode=mode))
    w("")
    w(L("### 3-1. Why things changed"))
    w("")
    w(_fragment(snap, "changes", missing))
    w("")

    # ---- 4. areas (fragment)
    w(L("## 4. Detail per area"))
    w("")
    w(_fragment(snap, "areas", missing) if mode == "full" else L("(daily mode: no per-area detail; see section 2 and `report.md`)"))
    w("")

    # ---- 5. absence
    w(L("## 5. Absence list"))
    w("")
    absent = [f for f in findings if f.get("type") == "absence" and f.get("status") in ("fail", "warn")]
    w(_table(["Finding", "Status", "Severity", "Why it should exist", "Proposal"], [[f"`{f['id']}`", f.get("status"), f.get("severity_default"), (f.get("why") or "")[:200], (f.get("suggest") or "")[:200]] for f in absent]))
    w("")
    w(f"Expected families missing (inventory): {', '.join(inv.get('missing_families') or []) or 'none'}.")
    w("")

    # ---- 6. suppressed, tool missing, not collected
    w(L("## 6. Suppressed, tool missing, not collected"))
    w("")
    sup = fd.get("suppressed") or []
    w(f"- Suppressed {len(sup)}: " + (", ".join(f"`{s['id']}` ({(s.get('suppressed_by') or {}).get('reason')}, until {(s.get('suppressed_by') or {}).get('until')})" for s in sup) if sup else "none"))
    exp = fd.get("expired_suppressions") or []
    w(f"- Suppression expired {len(exp)}: " + (", ".join(f"`{e.get('id')}`" for e in exp) if exp else "none"))
    tm = [r for r in results if r.get("status") == "tool-missing"]
    w(f"- Tool missing {len(tm)}: " + (", ".join(f"`{r['id']}` ({r.get('reason')})" for r in tm) if tm else "none"))
    nc = [r for r in results if r.get("status") == "not-collected"]
    w(f"- Not collected in {mode} mode {len(nc)}: " + (", ".join(f"`{r['id']}`" for r in nc) if nc else "none"))
    sk = [r for r in results if r.get("status") in ("skip", "error")]
    w(f"- Skipped or errored {len(sk)}: " + (", ".join(f"`{r['id']}` ({r.get('status')}: {r.get('reason')})" for r in sk) if sk else "none"))
    w("")

    # ---- 7. appendix
    w(L("## 7. Appendix"))
    w("")
    w(L("### 7-1. Collectors and steps run"))
    w("")
    rows = []
    for name, c in cr.items():
        if name.startswith("_") or not isinstance(c, dict):
            continue
        steps = c.get("steps") or {}
        failed = [sid for sid, st in steps.items() if isinstance(st, dict) and st.get("ok") is False and not st.get("skipped")]
        skipped = [f"{sid} ({st.get('skipped')})" for sid, st in steps.items() if isinstance(st, dict) and st.get("skipped")]
        rows.append([name, len(steps), ", ".join(failed) or "", "; ".join(skipped) or (c.get("skipped") or "")])
    w(_table(["Collector", "Steps", "Failed", "Skipped (reason)"], rows))
    sm = cr.get("_summary") or {}
    run = summary.get("run") or {}
    w("")
    w(
        f"{run.get('commands') or '?'} commands, {sm.get('seconds_total')} s. Failed commands (run.log): {len(run.get('failed') or [])}"
        + (": " + "; ".join(f"`{f.get('id')}` {str(f.get('error') or '')[:120]}" for f in (run.get("failed") or [])[:20]) if run.get("failed") else "")
    )
    w("")
    w(L("### 7-2. Checks evaluated"))
    w("")
    w(f"{(fd.get('checks') or {}).get('total')} checks: " + ", ".join(f"{k} {v}" for k, v in sorted(bs.items())) + f". Load errors: {', '.join((fd.get('checks') or {}).get('load_errors') or []) or 'none'}.")
    w("")
    w(L("### 7-3. Signature matches and unclassified errors"))
    w("")
    lg = summary.get("logs") or {}
    w(
        f"Signature catalog {lg.get('signatures_version')}, {lg.get('files_scanned')} files, {lg.get('lines_scanned')} lines scanned (components: {', '.join(lg.get('components_with_logs') or [])}). Unclassified error lines: {lg.get('error_lines_unclassified')}."
    )
    w("")
    sigs = lg.get("signatures") or []
    w(
        _table(
            ["Signature", "Component", "Area", "Severity", "Status", "Count", "First ~ last", "Sample"],
            [[s.get("id"), s.get("component"), s.get("area"), s.get("severity"), s.get("status"), s.get("count"), f"{s.get('first') or ''} ~ {s.get('last') or ''}", ((s.get("samples") or [""])[0] or "")[:160]] for s in sigs],
        )
    )
    w("")
    un = lg.get("unclassified_errors") or []
    w(_table(["Normalized message", "Count", "Files"], [[(u.get("pattern") or "")[:200], u.get("count"), ", ".join(list((u.get("files") or {}).keys())[:3]) if isinstance(u.get("files"), dict) else ""] for u in un[:30]]))
    w("")
    w(L("### 7-4. Raw files the LLM read directly"))
    w("")
    w(_fragment(snap, "files-read", missing))
    w("")
    w(L("### 7-5. Full first-pass status (every fail and warn, code results as-is)"))
    w("")
    fw = sorted((f for f in findings if f.get("status") in ("fail", "warn")), key=lambda f: (SEVERITIES.index(f.get("severity_default", "info")) if f.get("severity_default") in SEVERITIES else 9, f.get("status") != "fail", f.get("id", "")))
    w(_table(["id", "Status", "Default severity", "Evidence"], [[f"`{f['id']}`", f.get("status"), f.get("severity_default"), (f.get("evidence") or "")[:300]] for f in fw]))
    w("")
    w(L("### 7-6. Tool notes (about kubegap itself)"))
    w("")
    w(_fragment(snap, "tool-notes", missing))
    w("")
    p = snap / "report-details.md"
    p.write_text("\n".join(out), encoding="utf-8")
    return p

"""`llm/facts.json`: what the analysis hands over, checked and completed by code before anyone writes a sentence from it.

The analysis decides what cannot be computed: which findings are one problem, what caused it, what an incident was, what is still unknown.
Everything that can be computed is computed here, so the report cannot contradict the snapshot on it:

- `check(facts, snap)`: what is wrong with the facts, as lines the analysis can act on. Nothing is written while this list is not empty.
- `complete(facts, snap)`: the same facts with the computed parts added: each problem's severity, who declares each target (from the
  snapshot's own evidence, never from a path on the machine that runs the audit), the period the run covers.

The contract itself is references/facts-<language>.md. The rules checked here are the ones a report of 2026-11-14 broke: five "problems" of
which four were one incident of that morning while two critical findings sat in a list below; a repository path taken from a clone on the
analyst's machine; work "done" against one earlier run and numbers compared with another.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..foundations.snapshot import load_json

SCHEMA = 2
SEVERITIES = ("critical", "high", "medium", "low", "info")
# What is lost when the problem happens, worst first. A problem that can lose data for good outranks one that takes the service down for a
# while at the same severity; "how hard is the fix" and "can it be done today" are not part of the order.
LOSSES = ("irreversible", "outage", "partial", "degraded")
CERTAINTY = ("confirmed", "likely", "unknown")
LIMIT_KINDS = ("no-data", "unsupported", "skipped")
METHOD_KINDS = ("metric", "alert", "dashboard", "log", "command")
PROBLEMS_FULL = 5


def _ids(entry: dict) -> list[str]:
    return [str(i) for i in entry.get("finding_ids") or []]


def _matches(patterns: list[str], finding_id: str) -> bool:
    """A finding id, or a prefix ending in `*` for the many findings of one check (`resilience.single-eligible-node.*`)."""
    return any(p == finding_id or (p.endswith("*") and fnmatch.fnmatchcase(finding_id, p)) for p in patterns)


def final_severities(facts: dict, findings: list[dict]) -> dict[str, str]:
    """finding id -> severity after the analysis: the first-pass level unless `analysis.severity_changes` names the finding."""
    changes = [c for c in (facts.get("analysis") or {}).get("severity_changes") or [] if isinstance(c, dict) and c.get("final") in SEVERITIES]
    out = {}
    for f in findings:
        hit = next((c for c in changes if _matches([str(c.get("finding_id") or "")], f["id"])), None)
        out[f["id"]] = hit["final"] if hit else f["severity_default"]
    return out


def _worst(levels: list[str]) -> str | None:
    return min(levels, key=SEVERITIES.index) if levels else None


def problem_severity(entry: dict, final: dict[str, str]) -> str | None:
    return _worst([sev for fid, sev in final.items() if _matches(_ids(entry), fid)])


def _inside(snap: Path, name: str) -> bool:
    """A source the report may cite: a file of this snapshot, or of an earlier snapshot of the same cluster. Never a path elsewhere on the machine."""
    p = Path(name)
    if not p.is_absolute():
        return ".." not in p.parts
    try:
        p.resolve().relative_to(snap.parent.resolve())
        return True
    except ValueError:
        return False


def check(facts: dict, snap: Path, mode: str) -> list[str]:
    """Every rule the facts break, one line each, worded for the analysis that has to fix it."""
    out: list[str] = []
    if facts.get("schema") != SCHEMA:
        return [f"schema is {facts.get('schema')!r}; this kubegap reads facts of schema {SCHEMA} (references/facts-<language>.md)"]
    fd = load_json(snap / "findings-draft.json") or {}
    findings = [f for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")]
    known = {f["id"] for f in findings}
    final = final_severities(facts, findings)
    problems = [p for p in facts.get("problems") or [] if isinstance(p, dict)]
    incidents = [i for i in ((facts.get("happened") or {}).get("incidents")) or [] if isinstance(i, dict)]
    broken = [b for b in facts.get("broken_now") or [] if isinstance(b, dict)]
    rest = [n for n in facts.get("next") or [] if isinstance(n, dict)]

    for kind, entries in (("problem", problems), ("incident", incidents), ("broken_now", broken), ("next", rest)):
        for e in entries:
            label = f"{kind} {e.get('id') or e.get('title')!r}"
            if not e.get("title"):
                out.append(f"{label}: no title")
            if not _ids(e):
                out.append(f"{label}: no finding_ids; every entry names the findings it stands for")
            for pat in _ids(e):
                if not any(_matches([pat], k) for k in known):
                    out.append(f"{label}: finding id {pat} is not in findings-draft.json")

    # what happened is not what is wrong: an occurrence that is over belongs to `happened`
    nature = {f["id"]: f.get("nature", "state") for f in findings}
    for p in problems:
        own = [fid for fid in known if _matches(_ids(p), fid)]
        if own and all(nature[f] == "occurrence" for f in own) and (p.get("state") or "ongoing") == "ended":
            out.append(f"problem {p.get('id')}: every finding is something that occurred and it is marked ended; move it to happened.incidents and name the problem it exposed")
    for i in incidents:
        if i.get("state") not in ("ended", "ongoing"):
            out.append(f"incident {i.get('id')}: state must be ended or ongoing")
        if i.get("state") == "ongoing":
            out.append(f"incident {i.get('id')}: still going on; it belongs in broken_now")
        for pid in i.get("exposed") or []:
            if str(pid) not in {str(p.get("id")) for p in problems} | {str(n.get("id")) for n in rest}:
                out.append(f"incident {i.get('id')}: exposed names {pid}, which is neither a problem nor an entry of next")

    if mode == "full":
        if not problems:
            out.append("problems is empty; a full run names the largest problems, up to five")
        if len(problems) > PROBLEMS_FULL:
            out.append(f"{len(problems)} problems; a full report carries {PROBLEMS_FULL} and the rest go to next")
    elif problems:
        out.append("a daily run does not pick problems; it reports what happened and what changed (the largest problems are picked by a full run)")

    rank: list[tuple[int, int]] = []
    for p in problems:
        pid = p.get("id")
        picked = p.get("picked") or {}
        if picked.get("loss") not in LOSSES:
            out.append(f"problem {pid}: picked.loss must be one of {', '.join(LOSSES)}")
        if not picked.get("reason"):
            out.append(f"problem {pid}: picked.reason is empty; the report says in one line why this is among the largest")
        if (p.get("cause") or {}).get("certainty") not in CERTAINTY:
            out.append(f"problem {pid}: cause.certainty must be one of {', '.join(CERTAINTY)}")
        if not p.get("check_methods"):
            out.append(f"problem {pid}: no check_methods; say what shows the state of this problem (a metric, an alert rule, a dashboard; a command only as an example)")
        for m in p.get("check_methods") or []:
            if not isinstance(m, dict) or m.get("kind") not in METHOD_KINDS:
                out.append(f"problem {pid}: check_methods kind must be one of {', '.join(METHOD_KINDS)}")
        if p.get("check_methods") and all(isinstance(m, dict) and m.get("kind") == "command" for m in p["check_methods"]):
            out.append(f"problem {pid}: check_methods are commands only; name the metric, alert or dashboard that shows it, and keep a command as an example")
        if not p.get("solutions"):
            out.append(f"problem {pid}: no solutions")
        for s in p.get("solutions") or []:
            if not isinstance(s, dict) or not s.get("approach"):
                out.append(f"problem {pid}: a solution without an approach")
        sev = problem_severity(p, final)
        if sev and picked.get("loss") in LOSSES:
            rank.append((SEVERITIES.index(sev), LOSSES.index(picked["loss"])))
    if rank != sorted(rank):
        out.append("problems are not in order: severity first (scale already applied), then what is lost (irreversible, outage, partial, degraded)")

    # nothing serious is left out: every critical or high failure is in one of the lists
    placed = [pat for e in problems + incidents + broken + rest for pat in _ids(e)]
    lost = sorted(f["id"] for f in findings if f["status"] == "fail" and final[f["id"]] in ("critical", "high") and not _matches(placed, f["id"]))
    if lost:
        out.append(f"{len(lost)} critical or high failures are in no list (problems, happened, broken_now, next): {', '.join(lost[:12])}{' …' if len(lost) > 12 else ''}")
    if problems and rest:
        worst_rest = _worst([s for n in rest for s in [problem_severity(n, final)] if s])
        last = problem_severity(problems[-1], final)
        if worst_rest and last and SEVERITIES.index(worst_rest) < SEVERITIES.index(last):
            out.append(f"next holds a {worst_rest} entry while problem {problems[-1].get('id')} is {last}; the more severe one is the problem")

    for c in (facts.get("analysis") or {}).get("severity_changes") or []:
        if not isinstance(c, dict) or not c.get("finding_id") or c.get("final") not in SEVERITIES or not c.get("reason"):
            out.append("analysis.severity_changes: each entry needs finding_id (an id, or a prefix ending in *), final (a severity) and reason")

    for lim in facts.get("limits") or []:
        if not isinstance(lim, dict) or lim.get("kind") not in LIMIT_KINDS:
            out.append(f"limits: kind must be one of {', '.join(LIMIT_KINDS)} ({(lim or {}).get('what') if isinstance(lim, dict) else lim!r})")
        elif not lim.get("what") or not lim.get("weakens"):
            out.append(f"limits: {lim.get('what')!r} needs what and weakens (which conclusion of this report is weaker for it)")

    for label, src in _sources(facts):
        if not _inside(snap, src):
            out.append(f"{label}: source {src} is outside the snapshot; the report cites only what the audit collected (an Argo CD or Helm source is named by code from the snapshot)")
    return out


def _sources(facts: dict):
    for kind, entries in (("problem", facts.get("problems") or []), ("incident", (facts.get("happened") or {}).get("incidents") or []), ("broken_now", facts.get("broken_now") or [])):
        for e in entries:
            if not isinstance(e, dict):
                continue
            for n in e.get("facts") or []:
                if isinstance(n, dict) and n.get("source_file"):
                    yield f"{kind} {e.get('id')}: {n.get('what')}", str(n["source_file"])
            for ev in (e.get("cause") or {}).get("evidence") or []:
                if isinstance(ev, str) and ("/" in ev and not ev.startswith("http")) and " " not in ev:
                    yield f"{kind} {e.get('id')}: cause evidence", ev
    for u in facts.get("upcoming") or []:
        if isinstance(u, dict) and u.get("source_file"):
            yield f"upcoming: {u.get('what')}", str(u["source_file"])
    for f in (facts.get("analysis") or {}).get("files_read") or []:
        yield "analysis.files_read", str(f)


def owners(snap: Path) -> dict[str, dict]:
    """workload (`<ns>/<kind>/<name>`, kind lowercase) -> who declares it, from summary.json: the Argo CD Application with its repository and path,
    the Helm release. Only what the cluster itself says; a workload nothing declares is not in the map."""
    summary = load_json(snap / "summary.json") or {}
    apps = {a.get("name"): a for a in (((summary.get("argocdctl") or {}).get("applications") or {}).get("rows")) or [] if isinstance(a, dict)}
    out = {}
    for r in ((summary.get("hygiene") or {}).get("templating") or {}).get("owners") or []:
        row = {"managed_by": r.get("managed_by")}
        app = apps.get(r.get("argocd_app"))
        if r.get("argocd_app"):
            row["argocd_app"] = r["argocd_app"]
        if app:
            row.update({k: app[k] for k in ("repo_url", "path", "chart", "target_revision") if app.get(k)})
            row["self_heal"] = bool(app.get("self_heal"))
        if r.get("helm_release"):
            row["helm_release"] = r["helm_release"]
        out[r["workload"]] = row
    return out


def _owner_of(target: str, who: dict[str, dict]) -> dict | None:
    """The owner of a target written as `<ns>/<kind>/<name>` or, as people write it, `<ns>/<name>` (then the one workload of that name in the namespace)."""
    parts = str(target).split("/")
    if len(parts) == 3:
        return who.get(f"{parts[0]}/{parts[1].lower()}/{parts[2]}")
    if len(parts) == 2:
        hits = [v for k, v in who.items() if k.split("/")[0] == parts[0] and k.split("/")[-1] == parts[1]]
        return hits[0] if len(hits) == 1 else None
    return None


def complete(facts: dict, snap: Path) -> dict:
    """The facts with what code knows added. The analysis's own entries are not changed."""
    import copy

    out = copy.deepcopy(facts)
    fd = load_json(snap / "findings-draft.json") or {}
    inv = load_json(snap / "inventory.json") or {}
    diff = load_json(snap / "diff.json") or {}
    findings = [f for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")]
    final = final_severities(out, findings)
    who = owners(snap)
    for e in (out.get("problems") or []) + (out.get("next") or []) + (out.get("broken_now") or []):
        if not isinstance(e, dict):
            continue
        e["severity"] = problem_severity(e, final)
        # every target gets an answer, so the writer never fills the gap from a guess: named evidence, or None for "nothing in the cluster says who declares it"
        e["declared_in"] = {str(t): _owner_of(t, who) for t in e.get("targets") or []}
    a_inv = load_json(Path(diff["a"]) / "inventory.json") if diff.get("a") else None
    out["scale"] = fd.get("scale") or inv.get("scale")
    out["period"] = {"from": (a_inv or {}).get("taken_at"), "to": inv.get("taken_at"), "baseline": Path(diff["a"]).name if diff.get("a") else None, "baseline_has_report": bool(diff.get("a")) and (Path(diff["a"]) / "report.md").is_file()}
    return out

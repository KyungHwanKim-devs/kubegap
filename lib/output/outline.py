"""The outline of a report: the short file in which the agent that analysed a run says what it puts where.

A report is written by the agent that read the findings, in its own words. Code cannot judge the words, but it can hold three promises
about what the report covers, and for that it needs to know which findings stand behind which entry:

    {"broken_now": [{"title": "", "finding_ids": []}],
     "happened":   [{"title": "", "state": "ended|ongoing|unknown", "finding_ids": []}],
     "problems":   [{"title": "", "loss": "irreversible|outage|partial|degraded", "finding_ids": []}],   # five at most, the largest first
     "next":       [{"title": "", "finding_ids": []}],
     "severity_changes": [{"finding_id": "", "final": "", "reason": ""}],
     "since_last": {"done": [{"problem": "", "proof": ""}], "not_done": [{"problem": "", "proof": ""}]},
     "upcoming":   [{"when": "", "what": "", "source": ""}],
     "area_summary": {"resources": "", …},
     "limits":     [{"kind": "no-data|unsupported", "what": "", "weakens": "", "to_see": ""}],
     "analysis":   {…}}                                                                              # what report-details.md prints

`check` holds the promises: nothing critical or high is left out, the problems are in order (severity at this scale, then what is lost),
and every id named is a finding of this run. The titles are the report's titles: `lib/output/report.py` refuses a report whose headings
differ from them, so the first screen, the headings and the ids at the end cannot say different things.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..foundations.snapshot import load_json

SEVERITIES = ("critical", "high", "medium", "low", "info")


def must_be_placed(finding: dict, severity: str) -> bool:
    """Whether a finding may not be left out of a report: a failure that is critical or high, and a warning that is critical. A check that can only
    warn (the absence of any backup tool, of any alert route) is as serious as its severity says; the first English full report left "no backup
    leaves the cluster" out altogether because only failures were required (2026-11-15). High warnings stay a matter of judgement: there are many."""
    return (finding.get("status") == "fail" and severity in ("critical", "high")) or (finding.get("status") == "warn" and severity == "critical")


# What is lost when the problem happens, worst first. A problem that can lose data for good outranks one that takes the service down for a
# while at the same severity; "how hard is the fix" and "can it be done today" are not part of the order.
LOSSES = ("irreversible", "outage", "partial", "degraded")
STATES = ("ended", "ongoing", "unknown")
LIMIT_KINDS = ("no-data", "unsupported")
PROBLEMS_FULL = 5
AREAS = ("resources", "scaling", "observability", "traffic", "resilience", "hygiene", "storage", "security", "cost", "tenancy", "node OS", "platform")
PATH = Path("report") / "outline.json"
SHORT_KINDS = {"deploy": "deployment", "sts": "statefulset", "ds": "daemonset", "cj": "cronjob", "rs": "replicaset"}


def _ids(entry: dict) -> list[str]:
    return [str(i) for i in entry.get("finding_ids") or []]


def _matches(patterns: list[str], finding_id: str) -> bool:
    """A finding id, or a prefix ending in `*` for the many findings of one check (`resilience.single-eligible-node.*`)."""
    return any(p == finding_id or (p.endswith("*") and fnmatch.fnmatchcase(finding_id, p)) for p in patterns)


def final_severities(facts: dict, findings: list[dict]) -> dict[str, str]:
    """finding id -> severity after the analysis: the first-pass level unless `analysis.severity_changes` names the finding."""
    changes = [c for c in (facts.get("severity_changes") or []) if isinstance(c, dict) and c.get("final") in SEVERITIES]
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


def declared_in(owners_: dict[str, dict], target: str) -> dict | None:
    """Who declares `target` according to the cluster itself: an entry of `owners`, found by `<ns>/<kind>/<name>` or, when the kind is left
    out, by namespace and name. None when nothing in the snapshot says: the report then names the resource and does not guess a repository."""
    target = str(target).split(":")[0]  # a finding of a container names it after the workload: `ns/sts/name:container`
    parts = target.split("/")
    if len(parts) == 3:  # findings shorten the kind where `kubectl` does
        target = "/".join((parts[0], SHORT_KINDS.get(parts[1], parts[1]), parts[2]))
    if target in owners_:
        return owners_[target]
    if len(parts) == 2:
        return next((v for k, v in owners_.items() if k.split("/")[0] == parts[0] and k.split("/")[-1] == parts[1]), None)
    return None


def declared_by_marks(snap: Path, target: str) -> dict | None:
    """Who declares an object that is not a workload (a Service behind a load balancer, an Ingress, a ConfigMap), read from the marks the object
    itself carries: Helm's `app.kubernetes.io/managed-by: Helm` with `meta.helm.sh/release-name`, Argo CD's tracking annotation or instance label.
    `target` ends in `<namespace>/<name>`; whatever stands before it is how the finding names the kind. A Service of a Helm release was once
    reported as declared nowhere because only workloads were looked up."""
    parts = str(target).split(":")[0].split("/")
    if len(parts) < 2:
        return None
    ns, name = parts[-2], parts[-1]
    apps = {a.get("name"): a for a in ((((load_json(snap / "summary.json") or {}).get("argocdctl") or {}).get("applications") or {}).get("rows")) or [] if isinstance(a, dict)}
    for f in sorted((snap / "objects").glob("*.json")) if (snap / "objects").is_dir() else []:
        for o in (load_json(f) or {}).get("items") or []:
            md = o.get("metadata") or {}
            if md.get("name") != name or (md.get("namespace") or "") != ns:
                continue
            labels, ann = md.get("labels") or {}, md.get("annotations") or {}
            row: dict = {}
            if labels.get("app.kubernetes.io/managed-by") == "Helm" and ann.get("meta.helm.sh/release-name"):
                row.update(managed_by="helm", helm_release=f"{ann.get('meta.helm.sh/release-namespace') or ns}/{ann['meta.helm.sh/release-name']}")
            app = str(ann.get("argocd.argoproj.io/tracking-id") or "").split(":")[0] or labels.get("argocd.argoproj.io/instance")
            if app and (app in apps or ann.get("argocd.argoproj.io/tracking-id")):
                row.update(managed_by="argocd", argocd_app=app)
                if app in apps:
                    row.update({k: apps[app][k] for k in ("repo_url", "path", "chart", "target_revision") if apps[app].get(k)})
                    row["self_heal"] = bool(apps[app].get("self_heal"))
            if row:
                row["read_from"] = f"the marks on {f.stem} {ns}/{name}"
                return row
    return None


def load(snap: Path) -> dict:
    return load_json(snap / PATH) or {}


def check(outline: dict, snap: Path) -> list[str]:
    """Every promise the outline of a full report breaks, one line each, worded for the agent that has to fix it."""
    out: list[str] = []
    fd = load_json(snap / "findings-draft.json") or {}
    findings = [f for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")]
    known = {f["id"] for f in findings}
    final = final_severities(outline, findings)
    lists = {k: [e for e in outline.get(k) or [] if isinstance(e, dict)] for k in ("broken_now", "happened", "problems", "next")}
    for kind, entries in lists.items():
        for e in entries:
            label = f"{kind} {e.get('title')!r}"
            if not e.get("title"):
                out.append(f"{kind}: an entry without a title")
            if not _ids(e):
                out.append(f"{label}: no finding_ids; every entry names the findings it stands for")
            for pat in _ids(e):
                if not any(_matches([pat], k) for k in known):
                    out.append(f"{label}: finding id {pat} is not in findings-draft.json (kubegap show findings)")
    for i in lists["happened"]:
        if i.get("state") not in STATES:
            out.append(f"happened {i.get('title')!r}: state must be one of {', '.join(STATES)}")
    problems = lists["problems"]
    if not problems:
        out.append("problems is empty; a full report explains the largest problems, up to five")
    if len(problems) > PROBLEMS_FULL:
        out.append(f"{len(problems)} problems; a full report explains {PROBLEMS_FULL} and the rest go to next")
    rank: list[tuple[int, int]] = []
    for p in problems:
        if p.get("loss") not in LOSSES:
            out.append(f"problem {p.get('title')!r}: loss must be one of {', '.join(LOSSES)}")
            continue
        sev = problem_severity(p, final)
        if sev:
            late = any(f.get("overdue") and f["status"] == "fail" and _matches(_ids(p), f["id"]) for f in findings)
            rank.append((SEVERITIES.index(sev), max(LOSSES.index(p["loss"]) - (1 if late else 0), 0)))
    if rank != sorted(rank):
        out.append(
            "problems are not in order: severity first (scale already applied), then what is lost (irreversible, outage, partial, degraded; a problem with an `overdue` failure, such as a version past its end of support, counts one step higher in what is lost)"
        )
    placed = [pat for entries in lists.values() for e in entries for pat in _ids(e)]
    lost = sorted(f["id"] for f in findings if must_be_placed(f, final[f["id"]]) and not _matches(placed, f["id"]))
    if lost:
        out.append(f"{len(lost)} critical or high failures or critical warnings are in no list (problems, happened, broken_now, next): {', '.join(lost[:12])}{' …' if len(lost) > 12 else ''}")
    if problems and lists["next"]:
        worst_rest = _worst([s for n in lists["next"] for s in [problem_severity(n, final)] if s])
        last = problem_severity(problems[-1], final)
        if worst_rest and last and SEVERITIES.index(worst_rest) < SEVERITIES.index(last):
            out.append(f"next holds a {worst_rest} entry while the last problem is {last}; the more severe one is the problem")
    for c in outline.get("severity_changes") or []:
        if not isinstance(c, dict) or not c.get("finding_id") or c.get("final") not in SEVERITIES or not c.get("reason"):
            out.append("severity_changes: each entry needs finding_id (an id, or a prefix ending in *), final (a severity) and reason")
    extra = set(outline.get("area_summary") or {}) - set(AREAS)
    if extra:
        out.append(f"area_summary: unknown area {sorted(extra)}; the areas are {', '.join(AREAS)}")
    missing = [a for a in AREAS if not (outline.get("area_summary") or {}).get(a)]
    if missing:
        out.append(f"area_summary: no line for {', '.join(missing)}; an area with nothing found says so, an area not looked at says why")
    for lim in outline.get("limits") or []:
        if not isinstance(lim, dict) or lim.get("kind") not in LIMIT_KINDS or not lim.get("what") or not lim.get("weakens"):
            out.append(f"limits: each entry needs kind ({', '.join(LIMIT_KINDS)}), what and weakens (which conclusion of this report is weaker for it)")
    return out

"""First-pass evaluation (evaluate).

Applies the expressions and thresholds in checks.yaml to the snapshot (summary.json, metrics/, objects/, inventory.json, aws/)
and writes per-check pass/warn/fail plus a default severity to `findings-draft.json`. Checks without an expression (type: llm)
are marked "LLM judgment". This is where the script stops; final severity, priority and conflict resolution are done by the LLM.
Finding ids are `<area>.<check id>.<ns>/<resource>` or `.cluster`.

Check expressions (`expr`, `warn_expr`, `target`, `evidence`) are Python evaluated with `eval` over a restricted builtins dict (SAFE_BUILTINS);
that restriction only keeps honest expressions small and is NOT a sandbox against malicious input. Expressions therefore come only from the
repository's own checks.yaml and rubric profiles, never from user config: config.yaml can set thresholds, profile names and suppressions, not code.
"""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from ... import __version__
from ...foundations import paths, rubric
from ...foundations.config import Config
from ...foundations.snapshot import load_json, write_private
from .context import Context
from .rules import Run
from .types import eval_absence, eval_inventory, eval_llm, eval_metric, eval_object, eval_signature, eval_summary

# check type -> handler. All handlers share the signature (cx, check, run) -> result dict; adding a type is one function plus one row here.
HANDLERS: dict[str, Callable[[Context, dict, Run], dict]] = {
    "signature": eval_signature,
    "llm": eval_llm,
    "absence": eval_absence,
    "metric": eval_metric,
    "object": eval_object,
    "summary": eval_summary,
    "inventory": eval_inventory,
    "aws": eval_inventory,
}


def evaluate_check(check: dict, cx: Context, thresholds: dict) -> dict:
    """Evaluate one check and return {status, counts, findings[], reason?}. Namespace profiles come from `cx.ns_profiles`."""
    handler = HANDLERS.get(check["type"])
    if handler is None:
        return Run.skip(f"unknown type {check['type']}")
    return handler(cx, check, Run(check, cx, thresholds))


def evaluate(snap: Path, cfg: Config, *, profile_override: str | None = None, tools_present: set[str] | None = None, echo=print) -> dict:
    inv = load_json(snap / "inventory.json") or {}
    summary = load_json(snap / "summary.json") or {}
    pname = profile_override or cfg.get("profile") or (inv.get("profile") or {}).get("name") or "prod"
    profile = rubric.load_profile(pname)
    collectors = inv.get("collectors_enabled") or ["core"]
    checks, errors = rubric.load_checks(collectors)
    ns_profiles = {pat: rubric.load_profile(str(name)) for pat, name in (cfg.get("namespace_profiles") or {}).items()}  # namespace-level profiles
    cx = Context(snap, inv, summary, profile, ns_profiles)
    mode = paths.snapshot_mode(
        snap
    )  # daily or full. A check marked `modes: [full]` needs inputs the daily run does not collect, so it is reported as not-collected instead of being evaluated on missing data (which would turn "file absent" into false absence findings)
    active_sup, expired_sup = rubric.active_suppressions(cfg.get("suppress"), cx.today)
    overrides = cfg.get("overrides") or {}

    results: list[dict] = []
    findings: list[dict] = []
    suppressed: list[dict] = []
    known, known_errors = rubric.load_known_issues()
    errors = list(errors) + known_errors
    catalog = rubric.catalog_hash()
    for c in checks:
        rec = {
            "id": c["id"],
            "name": c["name"],
            "area": c["area"],
            "type": c["type"],
            "collector": c["collector"],
            "severity_default": c["severity_default"],
            "rule_hash": rubric.rule_hash(c, extra=catalog if c["type"] == "signature" else None),
        }
        if c["id"] in known:
            rec["known_issues"] = known[c["id"]]  # open defects of kubegap that affect this check; the finding carries them too, so a tool note cites the number instead of describing the defect again
        applies = pname in (c.get("profiles") or []) or (profile.get("base") in (c.get("profiles") or []))  # derived profiles (small-prod, multi-az-prod, dev) inherit the check set of their base profile
        if not applies or c["id"] in (profile.get("disabled_checks") or []):
            rec.update(status="disabled", reason=f"disabled in profile {pname}")
            results.append(rec)
            continue
        if c.get("modes") and mode not in c["modes"]:
            rec.update(status="not-collected", reason=f"inputs not collected in {mode} mode (collected by: {', '.join(c['modes'])})")
            results.append(rec)
            continue
        req_tool = c.get("requires_tool")
        if req_tool and tools_present is not None and req_tool not in tools_present:
            rec.update(status="tool-missing", reason=f"tool {req_tool} missing")
            results.append(rec)
            continue
        thresholds = rubric.resolve_thresholds(c, profile, overrides)
        try:
            r = evaluate_check(c, cx, thresholds)
        except Exception as e:  # A bug in one check must not stop the whole run. Recorded in the report appendix
            rec.update(status="error", reason=f"{type(e).__name__}: {e}")
            results.append(rec)
            continue
        rec.update(status=r["status"], counts=r.get("counts"), reason=r.get("reason"), thresholds=thresholds)
        if r.get("skipped_reason"):
            rec["skipped_reason"] = r["skipped_reason"]
        if r.get("gone_nodes"):
            rec["gone_nodes"] = r["gone_nodes"]  # node series the inventory no longer lists: left within the metric window, not judged
        for f in r["findings"]:
            f["thresholds"] = thresholds
            for k in ("why", "suggest", "verify", "cases", "measured", "notes"):
                f.setdefault(k, c.get(k))  # signature checks already carry the signature's description
            if c["id"] in known:
                f["known_issues"] = known[c["id"]]  # the evidence is left as the check wrote it; render appends "known issue #N" in its tables
            sup = next((s for s in active_sup if s.get("id") == c["id"] and (not s.get("namespaces") or f["target"].split("/")[0] in s["namespaces"])), None)
            if sup:
                f["status"] = "suppressed"
                f["suppressed_by"] = {"reason": sup.get("reason"), "until": sup.get("until")}
                suppressed.append(f)
            else:
                findings.append(f)
        results.append(rec)

    def counts_by(key, items):
        return dict(Counter(x[key] for x in items))

    out = {
        "kubegap": __version__,
        "schema": paths.SCHEMA_VERSION,
        "rubric_version": paths.rubric_version(),
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "snapshot": str(snap),
        "mode": mode,
        "context": inv.get("context"),
        "profile": {"name": pname, "source": "override" if profile_override else (inv.get("profile") or {}).get("source"), "missing_file": profile.get("missing", False)},
        "checks": {"total": len(checks), "by_status": counts_by("status", results), "load_errors": errors},
        "severity_rules": rubric.load_severity_rules(),
        "findings": sorted(findings, key=lambda f: (["critical", "high", "medium", "low", "info"].index(f["severity_default"]), f["status"] != "fail", f["id"])),
        "findings_count": {
            "by_status": counts_by("status", findings),
            "by_severity_default": counts_by("severity_default", [f for f in findings if f["status"] == "fail"]),
            "warn_by_severity_default": counts_by("severity_default", [f for f in findings if f["status"] == "warn"]),
        },
        "suppressed": suppressed,
        "expired_suppressions": expired_sup,
        "llm_checks": [f for f in findings if f["status"] == "llm"],
        "check_results": results,
    }
    write_private(snap / "findings-draft.json", json.dumps(out, ensure_ascii=False, indent=1, default=str))
    if echo:
        bs = out["checks"]["by_status"]
        echo(
            f"profile {pname}, mode {mode}, {len(checks)} checks: evaluated {bs.get('done', 0)}, disabled {bs.get('disabled', 0)}, skipped {bs.get('skip', 0)}, not collected in this mode {bs.get('not-collected', 0)}, errors {bs.get('error', 0)}, tool missing {bs.get('tool-missing', 0)}"
        )
        if errors:
            echo("load errors: " + "; ".join(errors))
        fc = out["findings_count"]
        echo(f"findings: fail {fc['by_status'].get('fail', 0)} (severity {fc['by_severity_default']}), warn {fc['by_status'].get('warn', 0)}, suppressed {len(suppressed)}")
        for r in results:
            if r["status"] == "error":
                echo(f"  error {r['id']}: {r['reason']}")
        echo(f"saved: {snap / 'findings-draft.json'}")
    return out

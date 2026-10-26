"""Check self-test (`scripts/kubegap selftest`). Exists because too many check code paths were never exercised.

Builds a temporary snapshot from the fake inputs in each check's `test:` section (summary items, metric series, objects), runs evaluate_check
for real, and verifies that the expected status (fail/warn/pass/none) comes out, that the expression finishes without an exception, and that an
evidence sentence is produced. The goal is to catch key typos, type errors and NameErrors on fail paths that never run on a healthy cluster,
before they cause an outage.

Shape of the `test:` section:
  test:
    profile: eks            # defaults to the first value of profiles
    cases:
      - expect: fail        # fail | warn | pass | none (zero findings)
        item: {…}           # type summary: one item to place at the `each` path (for cluster_level, the dict itself)
        metric:             # type metric: list of series per input query id
          <qid>:
            - labels: {…}
              value: 0.9
        objects:            # type object: items of objects/<stem>.json
          deployments: [ {…} ]
        inventory: {…}      # inventory.json override (optional). absence checks decide presence from families_present/components_present
        summary: {…}        # sections merged into summary.json as-is (logs.signatures for signature checks, observability.slo read by absence warn_expr, etc.)
        aws: {filename: {…}} # aws/<file>.json (aws_file of inventory-type checks)
        objects should also include the other stems read by helpers (hpa_covers, pdb_covers, serves_traffic, backup_signals, karpenter_pool_nodes)
"""

from __future__ import annotations

import json
import re
import tempfile
import traceback
from pathlib import Path

from . import evaluate as _ev
from . import rubric

BASE_INV = {
    "context": "selftest",
    "cluster": {"platform": "eks", "server_version": "v1.32.0", "eks": {}},
    "profile": {"name": "prod"},
    "namespaces": {"count": 2, "names": ["prod-a", "dev-a"], "prod_like": ["prod-a"], "dev_like": ["dev-a"]},
    "nodes": {"count": 0, "nodes": []},
    "components": {},
    "components_present": [],
    "families_present": [],
    "missing_families": [],
    "node_access": {"method": "none", "ssm_registered": [], "ssm_unregistered": []},
    "stores": {},
    "collectors_enabled": ["core"],
}


def _set_path(d: dict, path: str, value):
    parts = path.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def _build_snapshot(root: Path, check: dict, case: dict, profile_name: str):
    (root / "objects").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(exist_ok=True)
    inv = json.loads(json.dumps(BASE_INV))
    inv["cluster"]["platform"] = "k3s" if profile_name == "lab" else "eks"
    inv["profile"]["name"] = profile_name
    for k, v in (case.get("inventory") or {}).items():
        inv[k] = v
    summary: dict = json.loads(json.dumps(case.get("summary") or {}))
    for name, body in (case.get("aws") or {}).items():
        (root / "aws").mkdir(exist_ok=True)
        (root / "aws" / name).write_text(json.dumps(body), encoding="utf-8")
    if check["type"] == "summary":
        item = case.get("item")
        if item is None and case.get("expect") == "none":
            _set_path(summary, check["each"], {} if check.get("cluster_level") else [])
        else:
            _set_path(summary, check["each"], item if check.get("cluster_level") else [item])
    for qid, series in (case.get("metric") or {}).items():
        (root / "metrics" / f"{qid}.json").write_text(json.dumps({"id": qid, "ok": True, "resultType": "vector", "result": [{"metric": s.get("labels") or {}, "value": [0, str(s.get("value"))]} for s in series]}), encoding="utf-8")
    for stem, items in (case.get("objects") or {}).items():
        (root / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    (root / "inventory.json").write_text(json.dumps(inv), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return inv, summary


KEY_HARD_RE = re.compile(r"item\['([^']+)'\]")
KEY_SOFT_RE = re.compile(r"item\.get\('([^']+)'")


def audit_against_snapshot(checks: list[dict], snap: Path) -> list[dict]:
    """Compensates for the limits of fake inputs: verifies that keys referenced by summary-type check expressions exist in the items of a real snapshot's summary.json.
    If a summary module renames a key, the check and its test section still agree and pass, but real evaluation breaks; this catches that gap.
    item['key'] fails when missing; item.get('key') fails only when no real item has it (optional keys may exist on only some items)."""
    summary = json.loads((snap / "summary.json").read_text(encoding="utf-8"))
    inv = json.loads((snap / "inventory.json").read_text(encoding="utf-8")) if (snap / "inventory.json").is_file() else {}
    profile = ((inv.get("profile") or {}).get("name")) or "prod"
    out = []
    for c in checks:
        if c["type"] != "summary" or not c.get("each"):
            continue
        if profile not in (c.get("profiles") or []):
            continue  # check disabled for this snapshot's profile (e.g. Karpenter checks on a small k3s cluster)
        seq = _ev._get_path(summary, c["each"])
        if seq is None:
            continue  # this snapshot has no such section; cannot judge
        items = [seq] if (c.get("cluster_level") or isinstance(seq, dict)) else list(seq)
        items = [i for i in items if isinstance(i, dict) and i.get("present") is not False and i.get("available") is not False]  # absent targets (no Loki, etc.) legitimately have empty keys
        if not items:
            continue
        texts = " ".join(str(c.get(k) or "") for k in ("rule", "target", "evidence"))
        for key in sorted(set(KEY_HARD_RE.findall(texts))):
            if not any(key in it for it in items):
                out.append({"case": f"{c['id']} ↔ {snap.name}", "reason": f"item['{key}'] in the expression is missing from the real summary.{c['each']} items"})
        for key in sorted(set(KEY_SOFT_RE.findall(texts))):
            if not any(key in it for it in items):
                out.append({"case": f"{c['id']} ↔ {snap.name}", "reason": f"item.get('{key}') in the expression is missing from every real summary.{c['each']} item"})
    return out


_THRESHOLD_VAR_RE = re.compile(r"v\.get\('([^']+)'[^)]*\)\s*(?:>=|<=|>|<)\s*threshold\b")
_THRESHOLD_LITERAL_RE = re.compile(r"\bvalue\s*(?:>=|<=|>|<)\s*([0-9][0-9.]*(?:\s*\*\*?\s*[0-9.]+)*)")


def metric_boundary(check: dict, thresholds: dict) -> tuple[str | None, float] | None:
    """The fail boundary of a metric check: (query id whose series value is compared, or None for the primary `value`, threshold number).

    The `>=` versus `>` choice at the threshold is where off-by-one verdicts hide, so every metric check should carry a test case at exactly this
    value. Resolved from `rule.threshold` when the expression compares against `threshold`, else from a numeric literal compared with `value`
    (`value >= 1000`, `value >= 6 * 1024**3`). Equality rules (`value == 1`) and rules without a number have no boundary and return None."""
    expr = str((check.get("rule") or {}).get("expr") or "")
    if not expr:
        return None
    if re.search(r"\bthreshold\b", expr):
        t = thresholds.get("threshold")
        if not isinstance(t, (int, float)) or isinstance(t, bool):
            return None
        m = _THRESHOLD_VAR_RE.search(expr)
        return (m.group(1) if m else None, float(t))
    m = _THRESHOLD_LITERAL_RE.search(expr)
    if not m:
        return None
    return (None, float(eval(m.group(1), {"__builtins__": {}}, {})))  # digits and * / ** only, matched by the regex above


def _case_values(check: dict, case: dict, qid: str | None) -> list[float]:
    inputs = check.get("inputs") or []
    qid = qid or (inputs[0] if inputs else None)
    out = []
    for s in ((case.get("metric") or {}).get(qid) or []) if qid else []:
        try:
            out.append(float(s.get("value")))
        except (TypeError, ValueError):
            continue
    return out


def audit_metric_boundaries(checks: list[dict]) -> list[dict]:
    """Note (not a failure) for every metric check with a numeric fail threshold whose test cases never place a value exactly at that threshold."""
    out = []
    for c in checks:
        if c["type"] != "metric":
            continue
        t = c.get("test") or {}
        profile = rubric.load_profile(t.get("profile") or (c.get("profiles") or ["prod"])[0])
        b = metric_boundary(c, rubric.resolve_thresholds(c, profile, {}))
        if b is None:
            continue
        qid, threshold = b
        if not any(threshold in _case_values(c, case, qid) for case in t.get("cases") or []):
            out.append({"case": c["id"], "reason": f"no test case with {qid or 'value'} exactly at the fail threshold {threshold:g} (note, not a failure)", "note_only": True})
    return out


def audit_each_paths(checks: list[dict], snaps: list[Path]) -> list[dict]:
    """A summary-type check fails when its `each` path exists in none of the snapshots for its profile: a path typo is silently skipped during evaluation and never
    produces a finding (observed once: a `hygiene.resources.*` typo passed the self-test). A section for an absent component (`{"present": false}`) passes because the path exists."""
    loaded = []
    for snap in snaps:
        try:
            summary = json.loads((snap / "summary.json").read_text(encoding="utf-8"))
            inv = json.loads((snap / "inventory.json").read_text(encoding="utf-8")) if (snap / "inventory.json").is_file() else {}
        except (OSError, json.JSONDecodeError):
            continue
        loaded.append((snap, ((inv.get("profile") or {}).get("name")) or "prod", summary))
    out = []
    for c in checks:
        if c["type"] != "summary" or not c.get("each"):
            continue
        applicable = [(sn, sm) for sn, prof, sm in loaded if prof in (c.get("profiles") or [])]
        if not applicable:
            continue
        if all(_ev._get_path(sm, c["each"]) is None for _, sm in applicable):
            if len(applicable) < 2:
                # with a single snapshot this may be an optional component absent from that environment (e.g. no Loki on a small k3s cluster), so it is a note, not a failure
                out.append(
                    {
                        "case": c["id"],
                        "reason": f"each path summary.{c['each']} is missing from snapshot {applicable[0][0].name}; with one snapshot it is impossible to tell an absent component from a typo (note, not a failure)",
                        "note_only": True,
                    }
                )
                continue
            out.append({"case": c["id"], "reason": f"each path summary.{c['each']} is missing from every snapshot of this profile {[sn.name for sn, _ in applicable]} (possible path typo)"})
    return out


def run(check_ids: list[str] | None = None, echo=print, snapshots: list[Path] | None = None) -> dict:
    collectors = sorted(p.name for p in rubric_collectors())
    checks, load_errors = rubric.load_checks(collectors)
    results = {"passed": [], "failed": [], "untested": [], "load_errors": load_errors, "audit_failed": []}
    for snap in snapshots or []:
        results["audit_failed"] += audit_against_snapshot([c for c in checks if not check_ids or c["id"] in check_ids], Path(snap))
    if snapshots:
        audit = audit_each_paths([c for c in checks if not check_ids or c["id"] in check_ids], [Path(s) for s in snapshots])
        results["audit_failed"] += [a for a in audit if not a.get("note_only")]
        results["audit_notes"] = [a for a in audit if a.get("note_only")]
    results["audit_notes"] = (results.get("audit_notes") or []) + audit_metric_boundaries([c for c in checks if not check_ids or c["id"] in check_ids])
    for c in checks:
        if check_ids and c["id"] not in check_ids:
            continue
        t = c.get("test")
        if not t or not t.get("cases"):
            results["untested"].append(c["id"])
            continue
        profile_name = t.get("profile") or (c.get("profiles") or ["prod"])[0]
        profile = rubric.load_profile(profile_name)
        for i, case in enumerate(t["cases"]):
            expect = case.get("expect", "fail")
            label = f"{c['id']} #{i + 1} expect={expect}"
            try:
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    inv, summary = _build_snapshot(root, c, case, profile_name)
                    cx = _ev.Context(root, inv, summary, profile)
                    thresholds = rubric.resolve_thresholds(c, profile, {})
                    r = _ev.evaluate_check(c, cx, thresholds)
            except Exception as e:  # an exception inside the expression is exactly what this test is looking for
                results["failed"].append({"case": label, "reason": f"exception {type(e).__name__}: {e}", "trace": traceback.format_exc(limit=3)})
                continue
            if c["type"] == "llm":
                # check without a rule: the evaluator must mark status llm and emit one finding whose evidence is the why text
                f0 = (r.get("findings") or [{}])[0]
                if expect != "llm":
                    results["failed"].append({"case": label, "reason": "expect must be llm for a type: llm check"})
                elif r.get("status") != "llm" or not str(f0.get("evidence") or "").strip() or not f0.get("target"):
                    results["failed"].append({"case": label, "reason": f"status {r.get('status')}, finding {f0}"})
                else:
                    results["passed"].append(label)
                continue
            if r.get("status") != "done":
                results["failed"].append({"case": label, "reason": f"status {r.get('status')}: {r.get('reason')}"})
                continue
            counts = r.get("counts") or {}
            got = "fail" if counts.get("fail") else ("warn" if counts.get("warn") else ("pass" if counts.get("pass") else "none"))
            if got != expect:
                results["failed"].append({"case": label, "reason": f"expected {expect}, got {got} (counts {counts})"})
                continue
            if expect in ("fail", "warn"):
                f = r["findings"][0]
                ev = f.get("evidence")
                if ev is None or str(ev).strip() in ("", "None"):
                    results["failed"].append({"case": label, "reason": "evidence is empty"})
                    continue
                if not f.get("target") or f["target"].startswith("{") or f["target"].startswith("["):
                    results["failed"].append({"case": label, "reason": f"target is empty or still the default: {f.get('target')!r}"})
                    continue
            results["passed"].append(label)
    if echo:
        echo(
            f"selftest: passed {len(results['passed'])}, failed {len(results['failed'])}, checks without a test section {len(results['untested'])}, load errors {len(load_errors)}"
            + (f", key mismatches against real snapshots {len(results['audit_failed'])}" if snapshots else "")
        )
        for f in results["audit_failed"]:
            echo(f"  key mismatch {f['case']}: {f['reason']}")
        for f in results.get("audit_notes") or []:
            echo(f"  note {f['case']}: {f['reason']}")
        for f in results["failed"]:
            echo(f"  failed {f['case']}: {f['reason']}")
            if f.get("trace"):
                echo("    " + f["trace"].strip().splitlines()[-1])
        if results["untested"]:
            echo("  no test section: " + ", ".join(results["untested"]))
    return results


def rubric_collectors():
    from . import paths

    return [p for p in paths.COLLECTORS_DIR.iterdir() if p.is_dir() and (p / "checks.yaml").is_file()]

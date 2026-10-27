"""Snapshot comparison (diff).

Compare two snapshots A (before) and B (after), write `diff.json` into B's folder, and append one line with B's per-severity counts to the context folder's `history.csv`.
The LLM uses this as input for the "what changed since the last run" section (why a change happened is traced by the LLM through events and object change times).

What is compared:
- Objects: per kind, additions/removals keyed by (namespace, name), plus items whose spec (or data/rules body) hash changed.
  Kinds that change constantly (Pods, ReplicaSets, Jobs, Endpoints, EndpointSlices, Leases, Events) only get a count delta.
- First-pass status (findings-draft.json): new findings, resolved findings, findings whose status (warn<->fail) or evidence changed.
- Inventory: platform, version, node count, namespaces, components, store retention changes.
- Events: change in cumulative occurrences per Warning Reason.
- Metrics: top value changes for the same label set.
"""

from __future__ import annotations

import contextlib
import csv
import datetime as _dt
import hashlib
import json
from collections import Counter
from pathlib import Path

from . import __version__, paths
from .snapshot import items, load_json

COUNT_ONLY_KINDS = {
    "pods",
    "replicasets.apps",
    "jobs.batch",
    "endpoints",
    "endpointslices.discovery.k8s.io",
    "leases.coordination.k8s.io",
    "events",
    "controllerrevisions.apps",
    "nodeclaims.karpenter.sh",
    "certificaterequests.cert-manager.io",
    "ephemeralrunners.actions.github.com",
    "ephemeralrunnersets.actions.github.com",
}
BODY_KEYS = ("spec", "data", "binaryData", "rules", "subjects", "roleRef", "webhooks", "provisioner", "parameters", "reclaimPolicy", "allowVolumeExpansion", "stringData", "secrets", "automountServiceAccountToken", "value", "globalDefault")
METRIC_DELTA_LABELS = ("node", "instance", "mountpoint", "namespace", "pod", "container", "horizontalpodautoscaler", "qos_class", "device")


def _key(o: dict) -> str:
    m = o.get("metadata") or {}
    return f"{m.get('namespace')}/{m.get('name')}" if m.get("namespace") else m.get("name", "?")


def _body_hash(o: dict) -> str:
    if o.get("kind") == "ConfigMap":
        # Values are not in the snapshot (lib/scrub.py keeps {len, shape}); a change that keeps length and shape would be invisible, so compare the server's resourceVersion instead. No value hash: a short password would be guessable from it.
        return f"rv:{(o.get('metadata') or {}).get('resourceVersion')}"
    body = {k: o.get(k) for k in BODY_KEYS if k in o}
    if not body:
        body = {k: v for k, v in o.items() if k not in ("metadata", "status", "kind", "apiVersion")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def diff_objects(a: Path, b: Path) -> dict:
    out: dict = {"kinds_compared": 0, "added": [], "removed": [], "changed": [], "count_only": {}, "kinds_only_in_a": [], "kinds_only_in_b": []}
    fa = {p.stem: p for p in (a / "objects").glob("*.json")} if (a / "objects").is_dir() else {}
    fb = {p.stem: p for p in (b / "objects").glob("*.json")} if (b / "objects").is_dir() else {}
    out["kinds_only_in_a"] = sorted(set(fa) - set(fb))
    out["kinds_only_in_b"] = sorted(set(fb) - set(fa))
    for kind in sorted(set(fa) & set(fb)):
        ia, ib = items(load_json(fa[kind])), items(load_json(fb[kind]))
        if kind in COUNT_ONLY_KINDS:
            if len(ia) != len(ib):
                out["count_only"][kind] = {"before": len(ia), "after": len(ib), "delta": len(ib) - len(ia)}
            continue
        out["kinds_compared"] += 1
        ma = {_key(o): o for o in ia}
        mb = {_key(o): o for o in ib}
        for k in sorted(set(mb) - set(ma)):
            out["added"].append({"kind": kind, "name": k})
        for k in sorted(set(ma) - set(mb)):
            out["removed"].append({"kind": kind, "name": k})
        for k in sorted(set(ma) & set(mb)):
            ha, hb = _body_hash(ma[k]), _body_hash(mb[k])
            if ha != hb:
                ga = (ma[k].get("metadata") or {}).get("generation")
                gb = (mb[k].get("metadata") or {}).get("generation")
                out["changed"].append({"kind": kind, "name": k, "generation": [ga, gb], "changed_fields": ["metadata.resourceVersion"] if ma[k].get("kind") == "ConfigMap" else _changed_fields(ma[k], mb[k])})
    out["summary"] = {"added": len(out["added"]), "removed": len(out["removed"]), "changed": len(out["changed"])}
    return out


def _changed_fields(a: dict, b: dict, prefix: str = "", depth: int = 0, limit: int = 12) -> list[str]:
    """Record a few changed top-level and second-level field paths (so the LLM knows where to look)."""
    out: list[str] = []
    keys = [k for k in BODY_KEYS if k in a or k in b] or [k for k in set(a) | set(b) if k not in ("metadata", "status", "kind", "apiVersion")]
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if va == vb:
            continue
        if isinstance(va, dict) and isinstance(vb, dict) and depth < 2:
            sub = [f"{k}.{x}" for x in sorted(set(va) | set(vb)) if va.get(x) != vb.get(x)]
            out.extend(sub[:limit])
        else:
            out.append(k)
    return out[:limit]


def diff_findings(a: Path, b: Path) -> dict:
    da, db = load_json(a / "findings-draft.json"), load_json(b / "findings-draft.json")
    if not da or not db:
        return {"missing": "findings-draft.json missing on one side (run evaluate first)", "a": bool(da), "b": bool(db)}
    fa = {f["id"]: f for f in da.get("findings", [])}
    fb = {f["id"]: f for f in db.get("findings", [])}
    new = [fb[i] for i in sorted(set(fb) - set(fa))]
    resolved = [fa[i] for i in sorted(set(fa) - set(fb))]
    changed = []
    for i in sorted(set(fa) & set(fb)):
        x, y = fa[i], fb[i]
        if x["status"] != y["status"] or x["severity_default"] != y["severity_default"]:
            changed.append({"id": i, "status": [x["status"], y["status"]], "severity_default": [x["severity_default"], y["severity_default"]]})
    # Rename suspects: within the same check and namespace one finding disappeared and one appeared
    rename_suspects = []
    for r in resolved:
        ns = r["target"].split("/")[0]
        cand = [n for n in new if n["check"] == r["check"] and n["target"].split("/")[0] == ns]
        if cand:
            rename_suspects.append({"resolved": r["id"], "new_candidates": [c["id"] for c in cand][:3]})

    def sev(d, st):
        return dict(Counter(f["severity_default"] for f in d.get("findings", []) if f["status"] == st))

    return {
        "rubric_version": [da.get("rubric_version"), db.get("rubric_version")],
        "profile": [(da.get("profile") or {}).get("name"), (db.get("profile") or {}).get("name")],
        "counts_before": {"fail": sev(da, "fail"), "warn": sev(da, "warn")},
        "counts_after": {"fail": sev(db, "fail"), "warn": sev(db, "warn")},
        "new": [{"id": f["id"], "status": f["status"], "severity_default": f["severity_default"], "evidence": f.get("evidence")} for f in new],
        "resolved": [{"id": f["id"], "status": f["status"], "severity_default": f["severity_default"]} for f in resolved],
        "changed": changed,
        "rename_suspects": rename_suspects,
        "summary": {"new": len(new), "resolved": len(resolved), "changed": len(changed)},
    }


def diff_inventory(a: Path, b: Path) -> dict:
    ia, ib = load_json(a / "inventory.json") or {}, load_json(b / "inventory.json") or {}
    if not ia or not ib:
        return {"missing": "inventory.json missing on one side"}
    ca, cb = set(ia.get("components_present") or []), set(ib.get("components_present") or [])
    na, nb = set((ia.get("namespaces") or {}).get("names") or []), set((ib.get("namespaces") or {}).get("names") or [])
    nodes_a = {n["name"] for n in (ia.get("nodes") or {}).get("nodes", [])}
    nodes_b = {n["name"] for n in (ib.get("nodes") or {}).get("nodes", [])}
    stores = {}
    for k in ("prometheus", "loki", "alertmanager", "grafana"):
        sa, sb = (ia.get("stores") or {}).get(k) or {}, (ib.get("stores") or {}).get(k) or {}
        if (sa.get("ok"), sa.get("version"), sa.get("retention")) != (sb.get("ok"), sb.get("version"), sb.get("retention")):
            stores[k] = {"before": {"ok": sa.get("ok"), "version": sa.get("version"), "retention": sa.get("retention")}, "after": {"ok": sb.get("ok"), "version": sb.get("version"), "retention": sb.get("retention")}}
    eks_a, eks_b = (ia.get("cluster") or {}).get("eks") or {}, (ib.get("cluster") or {}).get("eks") or {}
    eks_changes = {k: [eks_a.get(k), eks_b.get(k)] for k in ("version", "platform_version", "control_plane_logging", "public_access_cidrs", "support_type", "addons") if eks_a.get(k) != eks_b.get(k)} if (eks_a or eks_b) else {}
    return {
        "taken_at": [ia.get("taken_at"), ib.get("taken_at")],
        "server_version": [(ia.get("cluster") or {}).get("server_version"), (ib.get("cluster") or {}).get("server_version")],
        "profile": [(ia.get("profile") or {}).get("name"), (ib.get("profile") or {}).get("name")],
        "node_count": [(ia.get("nodes") or {}).get("count"), (ib.get("nodes") or {}).get("count")],
        "nodes_added": sorted(nodes_b - nodes_a),
        "nodes_removed": sorted(nodes_a - nodes_b),
        "kubelet_versions": [(ia.get("nodes") or {}).get("kubelet_versions"), (ib.get("nodes") or {}).get("kubelet_versions")],
        "components_added": sorted(cb - ca),
        "components_removed": sorted(ca - cb),
        "namespaces_added": sorted(nb - na),
        "namespaces_removed": sorted(na - nb),
        "missing_families": [ia.get("missing_families"), ib.get("missing_families")],
        "stores_changed": stores,
        "eks_changed": eks_changes,
    }


def diff_events(a: Path, b: Path) -> dict:
    sa, sb = load_json(a / "summary.json") or {}, load_json(b / "summary.json") or {}
    ra = {r["reason"]: r for r in (sa.get("events") or {}).get("reasons", [])}
    rb = {r["reason"]: r for r in (sb.get("events") or {}).get("reasons", [])}
    rows = []
    for reason in sorted(set(ra) | set(rb)):
        x, y = ra.get(reason), rb.get(reason)
        typ = (y or x or {}).get("type")
        oa, ob = (x or {}).get("occurrences", 0), (y or {}).get("occurrences", 0)
        if oa != ob or (x is None) != (y is None):
            # A count that dropped to 0 after the retention window (default 1 hour) is expiry, not a cluster change (seen on a real cluster: SuccessfullyReconciled 38,473 -> 0)
            kind = "expired" if (oa > 0 and ob == 0) else ("new" if (oa == 0 and ob > 0) else "changed")
            rows.append({"reason": reason, "type": typ, "occurrences": [oa, ob], "delta": ob - oa, "kind": kind, "objects_top_after": (y or {}).get("objects_top", [])[:3]})
    rows.sort(key=lambda r: (r["type"] != "Warning", -abs(r["delta"])))
    return {
        "changed": rows[:40],
        "warning_reasons_new": [r["reason"] for r in rows if r["type"] == "Warning" and r["occurrences"][0] == 0],
        "expired": [r["reason"] for r in rows if r["kind"] == "expired"],
        "note": "kind=expired means the event retention window expired (not a change); new means the Reason appeared for the first time",
    }


def diff_metrics(a: Path, b: Path, top: int = 10) -> dict:
    out: dict = {}
    ma = {p.stem: p for p in (a / "metrics").glob("*.json")} if (a / "metrics").is_dir() else {}
    mb = {p.stem: p for p in (b / "metrics").glob("*.json")} if (b / "metrics").is_dir() else {}
    for qid in sorted(set(ma) & set(mb)):
        da, db = load_json(ma[qid]) or {}, load_json(mb[qid]) or {}
        if not da.get("ok") or not db.get("ok"):
            continue

        def table(d):
            t = {}
            for s in d.get("result", []):
                lab = tuple((k, v) for k, v in sorted(s.get("metric", {}).items()) if k in METRIC_DELTA_LABELS)
                with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
                    t[lab] = float(s["value"][1])
            return t

        ta, tb = table(da), table(db)
        deltas = []
        for lab in set(ta) & set(tb):
            if ta[lab] != tb[lab]:
                deltas.append({"labels": dict(lab), "before": ta[lab], "after": tb[lab], "delta": tb[lab] - ta[lab]})
        deltas.sort(key=lambda r: -abs(r["delta"]))
        rec = {"series": [len(ta), len(tb)], "appeared": len(set(tb) - set(ta)), "disappeared": len(set(ta) - set(tb)), "top_deltas": deltas[:top]}
        if rec["appeared"] or rec["disappeared"] or deltas:
            out[qid] = rec
    return out


def diff(a: Path, b: Path, write: bool = True) -> dict:
    d = {
        "kubegap": __version__,
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "a": str(a),
        "b": str(b),
        "a_name": a.name,
        "b_name": b.name,
        "inventory": diff_inventory(a, b),
        "objects": diff_objects(a, b),
        "findings": {**diff_findings(a, b), "persisted": persisted_findings(b)},
        "events": diff_events(a, b),
        "metrics": diff_metrics(a, b),
    }
    if write:
        (b / "diff.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return d


def persisted_findings(b: Path, lookback: int = 10) -> dict:
    """Walk the same context's previous snapshots backwards (up to lookback, skipping INCOMPLETE ones and ones without inventory) and count how many consecutive runs each current finding appeared in. SRE lens: Toil. An item that shows up every run and is fixed by hand every time is an automation priority."""
    cur = load_json(b / "findings-draft.json") or {}
    ids = {f["id"]: f for f in cur.get("findings", [])}
    if not ids:
        return {"runs_checked": 0, "rows": []}
    mode = paths.snapshot_mode(b)  # daily runs are counted against daily runs only; a full-only finding would otherwise look like it "disappeared" on every daily run
    prev = sorted((p for p in b.parent.iterdir() if p.is_dir() and p.name < b.name and (p / "inventory.json").is_file() and not (p / "INCOMPLETE").is_file() and paths.snapshot_mode(p) == mode), reverse=True)[:lookback]
    runs = dict.fromkeys(ids, 1)
    alive = set(ids)
    checked = 0
    for p in prev:
        fd = load_json(p / "findings-draft.json")
        if not fd:
            continue
        checked += 1
        present = {f["id"] for f in fd.get("findings", [])}
        for i in list(alive):
            if i in present:
                runs[i] += 1
            else:
                alive.discard(i)
        if not alive:
            break
    rows = sorted(({"id": i, "runs": r, "check": ids[i]["check"], "status": ids[i]["status"], "severity_default": ids[i].get("severity_default")} for i, r in runs.items()), key=lambda x: (-x["runs"], x["id"]))
    by_check: Counter = Counter()
    for x in rows:
        if x["runs"] >= 3:
            by_check[x["check"]] += 1
    return {
        "runs_checked": checked + 1,
        "max_runs": rows[0]["runs"] if rows else 0,
        "persisted_3plus": sum(1 for x in rows if x["runs"] >= 3),
        "persisted_all": sum(1 for x in rows if x["runs"] >= checked + 1 and checked >= 2),
        "toil_candidates_by_check": dict(by_check.most_common(15)),
        "rows": rows[:60],
        "note": "runs = consecutive appearances including this one. Short run intervals (several per day) inflate the count, so read it together with the taken_at spacing",
    }


# ---------- history.csv ----------

HISTORY_COLUMNS = ["snapshot", "taken_at", "context", "profile", "rubric_version", "signatures_version", "critical", "high", "medium", "low", "info", "warn", "suppressed", "checks_evaluated", "nodes", "components"]


def append_history(snap: Path) -> Path | None:
    """Write one history.csv line from the snapshot's findings-draft.json and inventory.json. Replaces an existing line for the same snapshot."""
    fd, inv = load_json(snap / "findings-draft.json"), load_json(snap / "inventory.json")
    if not fd or not inv:
        return None
    fails = Counter(f["severity_default"] for f in fd.get("findings", []) if f["status"] == "fail")
    warns = sum(1 for f in fd.get("findings", []) if f["status"] == "warn")
    row = {
        "snapshot": snap.name,
        "taken_at": inv.get("taken_at"),
        "context": inv.get("context"),
        "profile": (fd.get("profile") or {}).get("name"),
        "rubric_version": fd.get("rubric_version"),
        "signatures_version": inv.get("signatures_version"),
        **{k: fails.get(k, 0) for k in ("critical", "high", "medium", "low", "info")},
        "warn": warns,
        "suppressed": len(fd.get("suppressed") or []),
        "checks_evaluated": (fd.get("checks") or {}).get("by_status", {}).get("done", 0),
        "nodes": (inv.get("nodes") or {}).get("count"),
        "components": len(inv.get("components_present") or []),
    }
    path = snap.parent / "history.csv"
    rows = []
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("snapshot") != snap.name]
    rows.append({k: ("" if row.get(k) is None else row.get(k)) for k in HISTORY_COLUMNS})
    rows.sort(key=lambda r: r["snapshot"])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def print_summary(d: dict, echo=print) -> None:
    inv, ob, fi, ev, me = d["inventory"], d["objects"], d["findings"], d["events"], d["metrics"]
    echo(f"A {d['a_name']} → B {d['b_name']}")
    if "missing" not in inv:
        echo(
            f"Inventory: server {inv['server_version'][0]} → {inv['server_version'][1]}, nodes {inv['node_count'][0]} → {inv['node_count'][1]}"
            f"{' (+' + ', '.join(inv['nodes_added']) + ')' if inv['nodes_added'] else ''}{' (-' + ', '.join(inv['nodes_removed']) + ')' if inv['nodes_removed'] else ''}, "
            f"components +{inv['components_added'] or '-'} -{inv['components_removed'] or '-'}, namespaces +{inv['namespaces_added'] or '-'} -{inv['namespaces_removed'] or '-'}"
            f"{', stores changed ' + ', '.join(inv['stores_changed']) if inv['stores_changed'] else ''}{', EKS changed ' + ', '.join(inv['eks_changed']) if inv['eks_changed'] else ''}"
        )
    count_only = ", ".join(f"{k} {v['before']}→{v['after']}" for k, v in ob["count_only"].items()) or "none"
    echo(f"Objects: {ob['kinds_compared']} kinds compared, added {ob['summary']['added']}, removed {ob['summary']['removed']}, changed {ob['summary']['changed']}; count-only kinds changed: {count_only}")
    for c in ob["changed"][:8]:
        echo(f"  changed {c['kind']} {c['name']}: {', '.join(c['changed_fields']) or '(body)'}")
    for x in ob["added"][:5]:
        echo(f"  added {x['kind']} {x['name']}")
    for x in ob["removed"][:5]:
        echo(f"  removed {x['kind']} {x['name']}")
    if "missing" in fi:
        echo(f"First-pass status: {fi['missing']}")
    else:
        echo(
            f"First-pass status: fail {fi['counts_before']['fail']} → {fi['counts_after']['fail']}; new {fi['summary']['new']}, resolved {fi['summary']['resolved']}, changed {fi['summary']['changed']}, rename suspects {len(fi['rename_suspects'])}"
        )
        for f in fi["new"][:6]:
            echo(f"  new [{f['status']}/{f['severity_default']}] {f['id']}")
        for f in fi["resolved"][:6]:
            echo(f"  resolved [{f['status']}/{f['severity_default']}] {f['id']}")
        for f in fi["changed"][:6]:
            echo(f"  changed {f['id']}: {f['status'][0]}→{f['status'][1]}")
    warn_rows = [r for r in ev["changed"] if r["type"] == "Warning"]
    echo(f"Events: {len(warn_rows)} Warning Reasons changed" + (", new Warning " + ", ".join(ev["warning_reasons_new"]) if ev["warning_reasons_new"] else ""))
    for r in warn_rows[:5]:
        echo(f"  {r['reason']} {r['occurrences'][0]} → {r['occurrences'][1]} ({r['delta']:+d}) {r['objects_top_after'][:1]}")
    echo(f"Metrics: {len(me)} queries with changed values")
    for qid in ("disk_usage_ratio", "node_memory_available_ratio", "node_cpu_request_ratio", "conntrack_ratio", "cpu_throttle_ratio_5m"):
        if qid in me and me[qid]["top_deltas"]:
            t = me[qid]["top_deltas"][0]
            echo(f"  {qid}: largest change {t['labels']} {t['before']:.3f} → {t['after']:.3f}")

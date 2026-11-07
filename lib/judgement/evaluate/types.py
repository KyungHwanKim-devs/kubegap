"""One handler per check type (signature, llm, absence, metric, object, summary, inventory/aws), all with the signature `(cx, check, run) -> result`.

Part of the evaluator (lib/judgement/evaluate).
"""

from __future__ import annotations

from pathlib import Path

from ...foundations.snapshot import metric_sample
from .context import Context, get_path
from .rules import ItemRecorder, Run, eval_expr, excluded, finding


def eval_signature(cx: Context, check: dict, run: Run) -> dict:
    """Log signatures: one finding per match in summary.logs.signatures. Area, severity and description come from the signature, not the check."""
    for sig in get_path(cx.summary, "logs.signatures") or []:
        st = sig.get("status")
        if st not in ("fail", "warn"):
            run.counts["pass"] += 1
            continue
        if excluded(check["id"], sig["id"], cx.profile):
            run.counts["excluded"] += 1
            continue
        run.counts[st] += 1
        ev = (
            f"{sig['count']} occurrences" + (f" ({sig.get('first')} ~ {sig.get('last')})" if sig.get("first") else "") + f", thresholds warn {sig['warn_at']}/fail {sig['fail_at']}"
            f". Files: {list(sig.get('files') or {})[:3]}. Samples: {[x[:160] for x in (sig.get('samples') or [])[:2]]}"
        )
        f = finding(
            check,
            sig["id"],
            st,
            ev,
            "summary.json:logs.signatures",
            {
                "signature": sig["id"],
                "component": sig["component"],
                "details": {k: sig.get(k) for k in ("count", "first", "last", "warn_at", "fail_at", "files", "samples") if k in sig},
            },  # the evidence cuts files and samples; details keeps them
        )
        f.update(
            area=sig["area"],
            severity_default=sig["severity"],
            name=f"[log] {sig['name']}",
            symptom_linked=sig["area"] in ("traffic", "resilience"),
            why=sig.get("meaning"),
            suggest=sig.get("cause"),
            verify=[sig["verify"]] if sig.get("verify") else None,
            notes="signatures/catalog.yaml " + sig["id"],
        )
        run.findings.append(f)
    return run.done()


def eval_llm(cx: Context, check: dict, run: Run) -> dict:
    """No rule: the LLM judges from the listed inputs. One placeholder finding so the report knows to look."""
    return {"status": "llm", "counts": {}, "findings": [finding(check, "cluster", "llm", check.get("why"), check.get("inputs") or "", {})]}


def eval_absence(cx: Context, check: dict, run: Run) -> dict:
    fam, comp = check.get("family"), check.get("component")
    present = set(cx.inv.get("families_present") or [])
    comps = set(cx.inv.get("components_present") or [])
    expected = cx.profile.get("expected_families")
    if fam and expected is not None and fam not in expected:
        return run.skip(f"profile {cx.profile.get('name')} does not require family {fam}")
    missing = (fam and fam not in present) or (comp and comp not in comps)
    if not missing:
        run.counts["pass"] += 1
        return run.done()
    st = "fail"
    ev = f"no component of family {fam or comp} in inventory.components"
    # Even for absence, if rule.warn_expr exists and is true (a substitute signal), downgrade to warn. Example: no backup tool, but etcd snapshots or dump CronJobs exist
    if run.rule.get("warn_expr") and eval_expr(run.rule["warn_expr"], run.base_env):
        st = "warn"
    if check.get("evidence"):
        ev = eval_expr(check["evidence"], run.base_env)
    run.findings.append(finding(check, "cluster", st, ev, "inventory.json"))
    run.counts[st] += 1
    return run.done()


def metric_target(cx: Context, labels: dict, fallback: str) -> str:
    """Pod series are attributed to their owning workload (stable id across restarts); other series to namespace/node."""
    if labels.get("pod"):
        return cx.workload(labels) + (":" + labels["container"] if labels.get("container") else "")
    return fallback


def empty_result(cx: Context, check: dict, run: Run, qids: list[str]) -> dict:
    """A query that answered with no series (#141). "The situation did not occur" and "the series does not exist" look the same in the result, so the
    verdict comes from elsewhere: the names the query cites (its `source:` entries) against metrics/series-present.json. A name with no series at all is
    not scraped, renamed or removed, and the check is skipped with the name; every name present is a pass with nothing to show, counted as `empty`
    so section 7-5 can say so. `rule.empty: skip` makes a check skip on any empty result (`empty_reason` says why); `rule.empty: pass` makes it a pass
    whatever the names say, for a counter that has no series until its first event (the kube-proxy restore-failure counters since 1.33)."""
    if run.rule.get("empty") == "skip":
        return run.skip(run.rule.get("empty_reason") or "the query returned no series")
    missing = cx.names_without_series(qids) if run.rule.get("empty") != "pass" else []
    if missing is None:
        return run.skip("the query returned no series and the series presence was not recorded (metrics/series-present.json missing: the promql.series-present query failed or did not run)")
    if missing:
        return run.skip("no series of " + ", ".join(f"`{n}`" for n in missing) + " (not scraped, or the exporter renamed or removed it)")
    run.counts["empty"] += 1
    return run.done()


def eval_metric(cx: Context, check: dict, run: Run) -> dict:
    inputs = check.get("inputs") or []
    if len(inputs) == 1:
        m = cx.metric(inputs[0])
        if not m:
            return run.skip(f"metrics/{inputs[0]}.json missing (not collected or no Prometheus)")
        if not m.get("ok"):
            return run.skip(f"query failed: {m.get('error')}")
        if not m.get("result"):
            return empty_result(cx, check, run, inputs)
        for s in m.get("result", []):
            value = metric_sample(s)  # NaN stays NaN: a check says `value == value` when it wants to pass over one
            if value is None:
                continue
            labels = s.get("metric", {})
            if gone := cx.node_gone(labels, check.get("area")):
                run.gone_node(gone)
                continue
            env = {**run.base_env, "value": value, "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
            default_target = metric_target(cx, labels, "/".join(x for x in (labels.get("namespace"), labels.get("node") or labels.get("instance")) if x) or "cluster")
            if check.get("exclude_transient") and labels.get("pod") and cx.is_transient(labels):
                run.counts["excluded"] += 1
                continue
            run.emit(env, default_target, f"metrics/{inputs[0]}.json")
        return run.done()
    key = check.get("join_on") or "node"
    keys = list(key) if isinstance(key, list) else [key]  # join_on is one label or a list ([namespace, pod, container])
    primary = inputs[0]  # Series absent from the first input are not judged (secondary inputs only supply evidence numbers) unless the check says `join_any: true`, where a series in any input is judged and the rule reads `v` with .get()
    join_any = bool(check.get("join_any"))
    joined: dict[tuple, dict] = {}
    present = []
    for qid in inputs:
        m = cx.metric(qid)
        if not m or not m.get("ok"):
            if qid == primary and not join_any:
                return run.skip(f"metrics/{qid}.json missing or failed")
            continue
        present.append(qid)
        for s in m.get("result", []):
            lab = s.get("metric", {})
            k = tuple(lab.get(x) for x in keys)
            if any(x is None for x in k):
                continue
            if (v := metric_sample(s)) is not None:
                joined.setdefault(k, {})[qid] = v
    if join_any and not present:
        return run.skip("metrics/" + ",".join(inputs) + " all missing or failed")
    if not joined:
        return empty_result(cx, check, run, present)
    for k, v in joined.items():
        if primary not in v and not join_any:
            continue
        labels = dict(zip(keys, k, strict=False))
        if gone := cx.node_gone(labels, check.get("area")):
            run.gone_node(gone)
            continue
        env = {**run.base_env, "v": v, "value": v.get(primary, next(iter(v.values()))), "labels": labels, "prod": cx.is_prod(labels.get("namespace")), "pod": labels.get("pod")}
        default_target = metric_target(cx, labels, "/".join(str(x) for x in k))
        if check.get("exclude_transient") and labels.get("pod") and cx.is_transient(labels):
            run.counts["excluded"] += 1
            continue
        run.emit(env, default_target, "metrics/" + ",".join(inputs))
    return run.done()


# Object stems that helpers read (pdb_covers, hpa_covers, has_service) but that are never the judged objects of an object-type check
HELPER_ONLY_STEMS = ("poddisruptionbudgets.policy", "horizontalpodautoscalers.autoscaling", "services")


def eval_object(cx: Context, check: dict, run: Run) -> dict:
    inputs = check.get("inputs") or []
    stems = [Path(i).stem for i in inputs if i.startswith("objects/")]
    if check.get("cluster_level"):
        objs = []
        for st in stems:
            objs += cx.objects(st)
        if not stems:
            return run.skip(f"{inputs[0] if inputs else 'input'} missing")
        if not (cx.snap / "objects" / f"{stems[0]}.json").is_file():
            return run.skip(cx.missing_object_file(stems[0]))
        run.emit({**run.base_env, "objs": objs, "prod": False}, "cluster", ", ".join(inputs))
        return run.done()
    any_file = False
    for st in (st for st in stems if st not in HELPER_ONLY_STEMS):
        if not (cx.snap / "objects" / f"{st}.json").is_file():
            continue
        any_file = True
        for obj in cx.objects(st):
            ns, name = obj["metadata"].get("namespace") or "", obj["metadata"]["name"]
            env = {**run.base_env, "obj": obj, "ns": ns, "name": name, "spec": obj.get("spec") or {}, "prod": cx.is_prod(ns)}
            run.emit(env, f"{ns}/{name}" if ns else name, f"objects/{st}.json")
    if not any_file:
        return run.skip("; ".join(cx.missing_object_file(st) for st in stems if st not in HELPER_ONLY_STEMS) or f"{', '.join(inputs)} missing")
    return run.done()


def eval_summary(cx: Context, check: dict, run: Run) -> dict:
    seq = get_path(cx.summary, check["each"]) if check.get("each") else None
    if seq is None:
        path = str(check.get("each"))
        while "." in path:  # the nearest ancestor that says why its part of the summary is missing (a section set to None by its module, #141)
            path = path.rpartition(".")[0]
            parent = get_path(cx.summary, path)
            if isinstance(parent, dict) and parent.get("skip_reason"):
                return run.skip(parent["skip_reason"])
        return run.skip(f"summary.{check.get('each')} missing")
    if check.get("cluster_level") or isinstance(seq, dict):
        seq = [seq]  # If the path is a single dict, it is the one item (cluster level)
    for item in seq:
        default_target = str(item)[:60]
        rec = ItemRecorder(item) if isinstance(item, dict) else item  # after the default target is formed, so forming it does not count as reading every key
        env = {**run.base_env, "item": rec, "prod": cx.is_prod((item or {}).get("namespace")) if isinstance(item, dict) else False}
        run.emit(env, default_target, "summary.json:" + check["each"])
    return run.done()


def eval_inventory(cx: Context, check: dict, run: Run) -> dict:
    """Types `inventory` and `aws` share this handler: both read inventory.json (aws checks reach aws/ files through the aws_file helper)."""
    if check.get("each"):
        seq = get_path(cx.inv, check["each"])
        if seq is None:
            return run.skip(f"inventory.{check['each']} missing")
        pairs = list(seq.items()) if isinstance(seq, dict) else [(None, x) for x in seq]
        for key, item in pairs:
            default_target = str(key if key is not None else item)[:60]
            rec = ItemRecorder(item) if isinstance(item, dict) else item
            run.emit({**run.base_env, "item": rec, "key": key, "prod": False}, default_target, "inventory.json:" + check["each"])
        return run.done()
    eks = (cx.inv.get("cluster") or {}).get("eks")
    if check["type"] == "inventory" and check["id"].startswith("eks."):
        if not eks:
            return run.skip("not EKS")
        if isinstance(eks, dict) and eks.get("error"):
            return run.skip(f"EKS facts not read (eks describe-cluster: {str(eks['error'])[:120]})")  # discover keeps name, region and the error only; a rule on those facts would judge nothing
    run.emit({**run.base_env, "prod": False}, "cluster", "inventory.json")
    return run.done()

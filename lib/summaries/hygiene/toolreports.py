"""What the external tools reported: Polaris failures, pluto and kubent deprecated APIs, Helm releases from `helm list`.

Part of the hygiene section (lib/summaries/hygiene): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import Counter
from pathlib import Path

from ...foundations import versions
from ...foundations.snapshot import load_json, metric_rows, parse_ts

SECURITY_CATEGORY = "Security"


def polaris(cx) -> dict:
    # source: polaris v10.2.6 pkg/validator/output.go:45-54 AuditData{PolarisOutputVersion, AuditTime, SourceType, SourceName, DisplayName, ClusterInfo, Results, Score},
    # :95-101 ClusterInfo{Version, Nodes, Pods, Namespaces, Controllers}, :151-158 Result{Name, Namespace, Kind, Results, PodResult, CreatedTime}, :188-192 PodResult{Name, Results,
    # ContainerResults}, :222-225 ContainerResult{Name, Results}, :104-112 ResultMessage{ID, Message, Details, Success, Severity, Category, Mutations}; pkg/config/severity.go:22-28
    # severities ignore|warning|danger; pkg/config/checks/*.yaml categories Security (27), Reliability (13), Efficiency (4). The step runs without --only-show-failed-tests:
    # that filter keeps a controller only when its PodResult is non-empty (output.go:180-185; schema.go:245-249 always sets one), so a controller whose only failures are
    # controller-level checks vanished. The successes are skipped here instead. len(Results) is every audited object of every kind (controllers, Ingresses, Namespaces,
    # bindings …) and ClusterInfo.Controllers (pkg/validator/fullaudit.go:55, GetNumberOfControllers) the audited controllers.
    d = load_json(cx.snap / "tools" / "polaris.json")
    if not d:
        return {"present": False, "note": "tools/polaris.json missing (polaris not installed or not collected yet)"}
    by_check: Counter = Counter()
    sev_of: dict[str, str] = {}
    cat_of: dict[str, str] = {}
    rows = []
    for r in d.get("Results") or []:
        failed = []

        def take(res: dict, where: str):
            for cid, v in (res or {}).items():
                if v.get("Success"):
                    continue
                failed.append({"check": cid, "severity": v.get("Severity"), "category": v.get("Category"), "where": where, "message": v.get("Message")})
                by_check[cid] += 1
                sev_of[cid] = v.get("Severity")
                cat_of[cid] = v.get("Category")

        take(r.get("Results"), "controller")
        pr = r.get("PodResult") or {}
        take(pr.get("Results"), "pod")
        for cr in pr.get("ContainerResults") or []:
            take(cr.get("Results"), f"container:{cr.get('Name')}")
        if not failed:
            continue
        ns = r.get("Namespace") or ""
        rows.append(
            {
                "namespace": ns,
                "name": r.get("Name"),
                "kind": r.get("Kind"),
                "target": f"{ns}/{str(r.get('Kind')).lower()}/{r.get('Name')}",
                "prod": ns in cx.prod,
                "danger": sum(1 for f in failed if f["severity"] == "danger"),
                "warning": sum(1 for f in failed if f["severity"] == "warning"),
                "danger_checks": sorted({f["check"] for f in failed if f["severity"] == "danger"}),
                "non_security_danger": sorted({f["check"] for f in failed if f["severity"] == "danger" and f["category"] != SECURITY_CATEGORY}),
                "non_security_warning": sorted({f["check"] for f in failed if f["severity"] == "warning" and f["category"] != SECURITY_CATEGORY}),
                "security_danger": sorted({f["check"] for f in failed if f["severity"] == "danger" and f["category"] == SECURITY_CATEGORY}),
                "security_warning": sorted({f["check"] for f in failed if f["severity"] == "warning" and f["category"] == SECURITY_CATEGORY}),
                "failed": failed,
            }
        )
    rows.sort(key=lambda r: (-r["danger"], -r["warning"]))
    checks = [{"check": c, "severity": sev_of[c], "category": cat_of[c], "count": n} for c, n in by_check.most_common()]
    return {
        "present": True,
        "source": "tools/polaris.json",
        "score": d.get("Score"),
        "audited": len(d.get("Results") or []),
        "with_failures": len(rows),
        "controllers": (d.get("ClusterInfo") or {}).get("Controllers"),
        "cluster_info": d.get("ClusterInfo"),
        "version": d.get("PolarisOutputVersion"),
        "checks": checks,
        "by_category": {f"{k[0]}/{k[1]}": v for k, v in Counter((cat_of[c], sev_of[c]) for c in by_check.elements()).items()} if by_check else {},
        "workloads": rows,
        "non_security_danger_workloads": [r["target"] for r in rows if r["non_security_danger"]],
        "security_danger_workloads": [r["target"] for r in rows if r["security_danger"]],
    }


def merge_tool_rows(items: list[dict]) -> list[dict]:
    """One row per object and API when pluto and kubent both report it (#164). pluto names the namespace of the saved object; kubent names the manifest's, which is
    `<undefined>` (None here) when the manifest had none, so the two targets differed and the report counted one problem twice. Rows with the same kind, name and
    API merge when their namespaces agree or one side has none; a kubent row without a namespace stays apart, with a note, when pluto saw that name in more than
    one namespace. A cluster-scoped object has no namespace on either side and merges on the name alone."""
    by_key: dict[tuple, list[dict]] = {}
    for it in items:
        by_key.setdefault((str(it.get("kind") or "").lower(), it.get("name"), it.get("api")), []).append(it)
    out: list[dict] = []
    for rows in by_key.values():
        named = {r["namespace"] for r in rows if r.get("namespace")}
        groups: dict[str | None, list[dict]] = {}
        for r in rows:
            ns = r.get("namespace")
            if ns is None and len(named) == 1:
                ns = next(iter(named))  # the one namespace pluto saw the object in
            groups.setdefault(ns, []).append(r)
        for ns, grp in groups.items():
            first = dict(grp[0])
            first["namespace"] = ns
            first["tools"] = sorted({r["source"] for r in grp})
            for k in ("deprecated_in", "removed_in", "replacement", "rule"):
                vals = [r.get(k) for r in grp if r.get(k) is not None]
                if vals:
                    first[k] = vals[0]
            first["deprecated"] = any(r.get("deprecated") for r in grp)
            first["removed"] = any(r.get("removed") for r in grp)
            first["source"] = "+".join(first["tools"])
            if ns is None and len(named) > 1:
                first["note"] = f"kubent gives no namespace for this object and pluto saw the name in {len(named)} namespaces ({', '.join(sorted(named))}); not merged"
            out.append(first)
    return out


def next_minor(server_version, pluto_target: dict | None) -> str | None:
    """The minor the two tools were asked about: the one after the server's (what collect passes as {k8s_next_minor}), else pluto's recorded k8s target."""
    return versions.next_minor_text(server_version) or versions.minor_text((pluto_target or {}).get("k8s"))


def deprecated(cx) -> dict:
    steps = ((load_json(cx.snap / "collect-result.json") or {}).get("core") or {}).get("steps") or {}
    read = {f"{tool}_read": bool((steps.get(tool) or {}).get("ok") and (steps.get(tool) or {}).get("api_read")) for tool in ("pluto", "kubent")}
    # How much of the API each tool saw, counted by lib/collection/collect (#132): kubent's successful and failed Lists from its log, for pluto the kinds objects.dump-all saved and the kinds it could not. None for a snapshot taken before the counts existed.
    lists = {f"{tool}_lists_{k}": (steps.get(tool) or {}).get(f"lists_{k}") for tool in ("pluto", "kubent") for k in ("ok", "failed")}
    # Both tools judge an object only through its last-applied annotation, so what they could judge is the objects carrying one: pluto gets exactly those, kubent logs `Retrieved N resources` (cmd/kubent/main.go:49@0.7.3). None for an older snapshot.
    manifests = {f"{tool}_manifests": (steps.get(tool) or {}).get("manifests") for tool in ("pluto", "kubent")}
    items = []
    # source: pluto v5.24.5 pkg/api/output.go:35-54 Output{name, filePath, namespace (omitempty), api, deprecated, removed, replacementAvailable}, :57-59 Instance{items (omitempty),
    # target-versions}, pkg/api/versions.go:60-76 Version{version, kind, deprecated-in, removed-in, replacement-api, replacement-available-in, component}; deprecated and removed are
    # judged against the target in FilterOutput (output.go:162-163). A cluster-scoped object has no namespace key.
    pl = load_json(cx.snap / "tools" / "pluto.json") or {}
    for it in (pl.get("items") or []) if read["pluto_read"] else []:
        items.append(
            {
                "source": "pluto",
                "kind": (it.get("api") or {}).get("kind") if isinstance(it.get("api"), dict) else it.get("kind"),  # pluto's Output has no kind of its own, it is api.kind (pkg/api/output.go:35-54, versions.go:60-76)
                "name": it.get("name"),
                "namespace": it.get("namespace"),
                "api": it.get("api", {}).get("version") if isinstance(it.get("api"), dict) else it.get("api"),
                "deprecated_in": (it.get("api") or {}).get("deprecated-in") if isinstance(it.get("api"), dict) else it.get("deprecated-in"),
                "removed_in": (it.get("api") or {}).get("removed-in") if isinstance(it.get("api"), dict) else it.get("removed-in"),
                "replacement": (it.get("api") or {}).get("replacement-api") if isinstance(it.get("api"), dict) else it.get("replacement-api"),
                "deprecated": bool(it.get("deprecated")),
                "removed": bool(it.get("removed")),
            }
        )
    # source: kubent 0.7.3 pkg/printer/json.go:32-40 encodes []judge.Result; pkg/judge/judge.go:3-11 Result{Name, Namespace, Kind, ApiVersion, RuleSet, ReplaceWith, Since}, Since as
    # text with three segments, "1.21.0" (judge/version.go:12-14 wraps hashicorp go-version, which pads). Since is the minor in which the API was deprecated, not removed:
    # pkg/rules/rego/deprecated-1-25.rego:13-33 gives PodDisruptionBudget policy/v1beta1
    # `since: 1.21` inside the rule set "Deprecated APIs removed in 1.25", so the removal minor exists only in the RuleSet text ("Deprecated APIs to be removed in future" for the ones
    # without a date, deprecated-future.rego:13). `-t` keeps the rows whose Since <= target or is empty (pkg/printer/filter.go:12). The rules write "<undefined>" for a missing
    # name or namespace (deprecated-1-25.rego:7-9; rego.go:61-64 is the fallback) and "<removed>" for an API with no successor (deprecated-1-25.rego:34-37).
    target = next_minor(cx.server_version, pl.get("target-versions"))
    kb = load_json(cx.snap / "tools" / "kubent.json")
    for it in kb if read["kubent_read"] and isinstance(kb, list) else []:
        m = re.search(r"removed in (\d+\.\d+)", str(it.get("RuleSet") or ""))
        removed_in = m.group(1) if m else None
        ns = it.get("Namespace")
        rep = it.get("ReplaceWith")
        nm = it.get("Name")
        items.append(
            {
                "source": "kubent",
                "kind": it.get("Kind"),
                "name": None if nm == "<undefined>" else nm,
                "namespace": None if ns == "<undefined>" else ns,
                "api": it.get("ApiVersion"),
                "deprecated_in": it.get("Since"),
                "removed_in": removed_in,
                "replacement": None if rep == "<removed>" else rep,
                "deprecated": True,
                "removed": bool(removed_in and target and versions.major_minor(removed_in) <= versions.major_minor(target)),
                "rule": it.get("RuleSet"),
            }
        )
    called = [{"group": ln.get("group"), "version": ln.get("version"), "resource": ln.get("resource"), "removed_release": ln.get("removed_release"), "calls": v} for ln, v in metric_rows(cx.snap, "apiserver_requested_deprecated_apis")]
    insights = []
    ins = load_json(cx.snap / "aws" / "list-insights.json")
    insights_read = ins is not None  # eks:ListInsights answered; refused, the list means nothing (#141)
    for i in (ins or {}).get("insights") or []:
        insights.append(
            {
                "name": i.get("name"),
                "category": i.get("category"),
                "status": (i.get("insightStatus") or {}).get("status"),
                "reason": ((i.get("insightStatus") or {}).get("reason") or "")[:200],
                "k8s_version": i.get("kubernetesVersion"),
                "last_transition": i.get("lastTransitionTime"),
            }
        )
    items = merge_tool_rows(items)
    for item in items:
        item.update(read)
    seen = [manifests[f"{tool}_manifests"] for tool in ("pluto", "kubent") if read[f"{tool}_read"]]
    judged = any(read.values()) and not (seen and all(n == 0 for n in seen))  # a cluster deployed only by Helm or server-side apply gives the tools nothing to judge: no finding is not a pass
    return {
        **read,
        **lists,
        **manifests,
        "objects_judged": judged,
        "skip_reason": None if judged or not any(read.values()) else "no object has a last-applied annotation, so pluto and kubent had nothing to judge",
        # None makes the existing evaluator skip even when there are no rows on which to test rule.needs.
        "items": items if judged else None,
        "count": len(items) if judged else None,
        "removed_next": [i for i in items if i["removed"]],
        "pluto_present": (cx.snap / "tools" / "pluto.json").is_file(),
        "kubent_present": (cx.snap / "tools" / "kubent.json").is_file(),
        "called_deprecated_apis": called,
        "eks_insights": {
            "read": insights_read,
            "rows": insights if insights_read else None,
            "failing": [i for i in insights if i["status"] in ("ERROR", "WARNING")] if insights_read else None,
            "skip_reason": None if insights_read else "EKS upgrade insights not read (aws/list-insights.json missing: eks:ListInsights refused or not an EKS cluster)",
        },
        "target": pl.get("target-versions"),
        "target_minor": target,
    }


def helm_missing_note(snap: Path) -> str:
    """Why tools/helm-list.json is absent. Helm reads release records from Secrets, so the shipped ClusterRole (no secrets) makes `helm list` fail; tell that apart from helm not being installed."""
    step = (((load_json(snap / "collect-result.json") or {}).get("core") or {}).get("steps") or {}).get("helm-list") or {}
    err = str(step.get("error") or "")
    if step.get("tool_missing"):
        return "helm is not installed; the Helm checks are skipped (kubegap setup --install-only helm)"
    if step.get("mode_skipped"):
        return "helm list is not collected in daily mode; the Helm checks run in a full run"
    if "forbidden" in err.lower() and "secret" in err.lower():
        return "helm list failed: Helm stores release records in Secrets and the credentials used have no secrets read permission (the shipped kubegap ClusterRole leaves it out on purpose). The Helm checks are skipped"
    if err:
        return f"helm list failed: {err[:200]}"
    return "tools/helm-list.json missing (helm not installed or not collected yet)"


def helm(cx, now: _dt.datetime) -> dict:
    # source: helm v4.3.1 pkg/cmd/list.go:142-150 releaseElement{name, namespace, revision, updated, status, chart, app_version}, :158-181 (an empty list prints `[]`, updated is
    # Go time.String() unless --time-format), pkg/release/common/status.go:25-41 the nine status values; identical in helm v3.22.1 cmd/helm/list.go:135-173 and pkg/release/status.go:25-41.
    d = load_json(cx.snap / "tools" / "helm-list.json")
    if d is None:
        return {"present": False, "note": helm_missing_note(cx.snap)}
    rows = []
    for r in d if isinstance(d, list) else []:
        upd = parse_ts(r.get("updated"))
        chart = r.get("chart") or ""
        m = re.match(r"(.+)-(v?\d[\w.\-]*)$", chart)
        rows.append(
            {
                "namespace": r.get("namespace"),
                "name": r.get("name"),
                "target": f"{r.get('namespace')}/{r.get('name')}",
                "status": r.get("status"),
                "revision": r.get("revision"),
                "chart": chart,
                "chart_name": m.group(1) if m else chart,
                "chart_version": m.group(2) if m else None,
                "app_version": r.get("app_version"),
                "updated": r.get("updated"),
                "age_days": round((now - upd).total_seconds() / 86400) if upd else None,
                "prod": (r.get("namespace") in cx.prod),
            }
        )
    # User values (`helm get values`) are deliberately not collected: they often carry credentials (issue #3). Only the list metadata above is known.
    return {
        "present": True,
        "count": len(rows),
        "releases": rows,
        "not_deployed": [r for r in rows if r["status"] != "deployed"],
        "by_status": dict(Counter(r["status"] for r in rows)),
        "stale_365d": [r["target"] for r in rows if (r["age_days"] or 0) >= 365],
    }

"""CronJobs: policy, last success against the run interval, active Job count.

Part of the resilience section (lib/summaries/resilience): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import defaultdict

from ...foundations.snapshot import objects, parse_ts


def cron_interval_h(expr: str | None) -> float | None:
    """Approximate run interval (hours) from a cron expression. None if unknown."""
    if not expr:
        return None
    f = expr.split()
    if len(f) != 5:
        return None
    minute, hour, dom, _mon, dow = f
    if minute == "*" and hour == "*":
        return 1 / 60
    m = re.match(r"\*/(\d+)$", minute)
    if m:
        return int(m.group(1)) / 60  # even with an hour range (7-15), this is the interval within that window
    m = re.match(r"\*/(\d+)$", hour)
    if m:
        return float(m.group(1))
    if hour == "*" and minute.isdigit():
        return 1.0
    if hour.isdigit() or re.match(r"^\d+(,\d+)*$", hour):
        n = len(hour.split(","))
        if dom == "*" and dow == "*":
            return 24.0 / n
        if dow != "*":
            days = len(dow.split(",")) if "-" not in dow else (int(dow.split("-")[1]) - int(dow.split("-")[0]) + 1)
            return 24.0 * 7 / max(days * n, 1)
        return 24.0 * 30 / n
    return None


def cronjobs(cx, now: _dt.datetime) -> dict:
    jobs = objects(cx.snap, "jobs.batch")
    jobs_by_owner: dict[tuple, list] = defaultdict(list)
    for j in jobs:
        own = next((x for x in j["metadata"].get("ownerReferences") or []), None)
        if own and own.get("kind") == "CronJob":
            jobs_by_owner[(j["metadata"]["namespace"], own.get("name"))].append(j)
    rows = []
    for cj in objects(cx.snap, "cronjobs"):
        md, sp, st = cj["metadata"], cj.get("spec") or {}, cj.get("status") or {}
        ns = md["namespace"]
        jt = (sp.get("jobTemplate") or {}).get("spec") or {}
        interval = cron_interval_h(sp.get("schedule"))
        last_ok = parse_ts(st.get("lastSuccessfulTime"))
        last_sched = parse_ts(st.get("lastScheduleTime"))
        age_ok = round((now - last_ok).total_seconds() / 3600, 1) if last_ok else None
        myjobs = jobs_by_owner.get((ns, md["name"]), [])
        failed = [j["metadata"]["name"] for j in myjobs if (j.get("status") or {}).get("failed")]
        durs = []
        for j in myjobs:
            js = j.get("status") or {}
            a, b = parse_ts(js.get("startTime")), parse_ts(js.get("completionTime"))
            if a and b:
                durs.append((b - a).total_seconds())
        durs.sort()
        max_dur = durs[-1] if durs else None
        med_dur = durs[len(durs) // 2] if durs else None
        runtime_ratio = round(max_dur / (interval * 3600), 2) if (max_dur is not None and interval) else None
        gaps = []
        if (sp.get("concurrencyPolicy") or "Allow") == "Allow":
            gaps.append("concurrencyPolicy Allow (overlap allowed)")
        if jt.get("activeDeadlineSeconds") is None:
            gaps.append("activeDeadlineSeconds missing (a stuck Job runs forever)")
        if jt.get("backoffLimit") is None and not jt.get("podFailurePolicy"):
            gaps.append("backoffLimit default 6 and no podFailurePolicy")
        if jt.get("ttlSecondsAfterFinished") is None and (sp.get("successfulJobsHistoryLimit", 3) or 0) > 10:
            gaps.append("many finished Jobs retained")
        if sp.get("startingDeadlineSeconds") is None:
            gaps.append("startingDeadlineSeconds missing (the controller stops after 100 missed schedules)")
        stale = (not sp.get("suspend") and bool(interval and age_ok is not None and age_ok > max(interval * 3, 3))) or (last_ok is None and last_sched is not None and (now - last_sched).total_seconds() > 86400 and not sp.get("suspend"))
        rows.append(
            {
                "namespace": ns,
                "name": md["name"],
                "target": f"{ns}/{md['name']}",
                "schedule": sp.get("schedule"),
                "interval_h": interval,
                "suspend": bool(sp.get("suspend")),
                "concurrency_policy": sp.get("concurrencyPolicy") or "Allow",
                "starting_deadline_s": sp.get("startingDeadlineSeconds"),
                "backoff_limit": jt.get("backoffLimit"),
                "active_deadline_s": jt.get("activeDeadlineSeconds"),
                "ttl_s": jt.get("ttlSecondsAfterFinished"),
                "pod_failure_policy": bool(jt.get("podFailurePolicy")),
                "history_limits": [sp.get("successfulJobsHistoryLimit", 3), sp.get("failedJobsHistoryLimit", 1)],
                "last_schedule": st.get("lastScheduleTime"),
                "last_success": st.get("lastSuccessfulTime"),
                "hours_since_success": age_ok,
                "active_jobs": len(st.get("active") or []),
                "jobs_total": len(myjobs),
                "failed_jobs": failed,
                "stale": stale,
                "policy_gaps": gaps,
                "prod": ns in cx.prod,
                "jobs_timed": len(durs),
                "max_job_duration_s": round(max_dur) if max_dur is not None else None,
                "median_job_duration_s": round(med_dur) if med_dur is not None else None,
                "runtime_over_interval": runtime_ratio,
            }
        )
    finished_no_ttl = [j for j in jobs if ((j.get("status") or {}).get("succeeded") or (j.get("status") or {}).get("failed")) and (j.get("spec") or {}).get("ttlSecondsAfterFinished") is None]
    succeeded_pods = sum(1 for p in cx.pods if p["status"].get("phase") == "Succeeded")
    failed_pods = sum(1 for p in cx.pods if p["status"].get("phase") == "Failed")
    return {
        "count": len(rows),
        "rows": rows,
        "stale": [r["target"] for r in rows if r["stale"]],
        "stacking": [r["target"] for r in rows if r["active_jobs"] >= 3],
        "runtime_exceeds_interval": [r["target"] for r in rows if (r["runtime_over_interval"] or 0) >= 1.0],
        "jobs": {"total": len(jobs), "failed": sum(1 for j in jobs if (j.get("status") or {}).get("failed")), "finished_without_ttl": len(finished_no_ttl), "succeeded_pods": succeeded_pods, "failed_pods": failed_pods},
    }

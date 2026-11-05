"""Cumulative event analysis.

Kubernetes events are kept for only 1 hour by default. So every run's `events.json` is gathered from all snapshots in the context folder
to build a per-Reason trend. The same event object (metadata.uid) appearing in several snapshots means its count grew, so only the
largest count per uid is kept (no double counting). Results: summary.json events.history and events-history.json in the context folder.

The tracked Reason list is TRACKED, with each Reason's "what is this a signal of" and default severity. The first-pass check
`events.tracked-warning-reasons` in core uses it.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .snapshot import load_json, write_private

# reason: (meaning, default severity)
TRACKED: dict[str, tuple[str, str]] = {
    "FailedScheduling": ("No node for the pod (resources, taints, affinity, PVC). Signal that scaling is blocked", "high"),
    "BackOff": ("Container keeps dying and the restart interval grows (CrashLoopBackOff)", "high"),
    "Unhealthy": ("Probe failure. Readiness removes it from traffic, liveness restarts it", "medium"),
    "FailedMount": ("Volume mount failed. Pod stuck in ContainerCreating", "high"),
    "FailedAttachVolume": ("Volume attach failed. Typical of delayed StatefulSet recovery after node replacement", "high"),
    "Evicted": ("kubelet evicted the pod due to node pressure (disk, memory, PID)", "high"),
    "Failed": ("Image pull failure (ErrImagePull, ImagePullBackOff) or container start failure", "medium"),
    "ErrImagePull": ("Image pull failure", "medium"),
    "ImagePullBackOff": ("Repeated image pull failures", "medium"),
    "NodeHasDiskPressure": ("Node disk pressure", "high"),
    "NodeHasMemoryPressure": ("Node memory pressure", "high"),
    "NodeHasPIDPressure": ("Node PID pressure (zombies, fork storm)", "high"),
    "FailedCreatePodSandBox": ("Pod network sandbox creation failed. Where VPC CNI IP exhaustion first shows up", "high"),
    "Preempted": ("Evicted because a higher-priority pod took the slot", "medium"),
    "OOMKilling": ("Node kernel OOM killer killed a process (SystemOOM)", "high"),
    "Rebooted": ("Node rebooted", "medium"),
    "FailedBinding": ("PVC could not get a PV (StorageClass, capacity, node affinity)", "high"),
    "NodeNotReady": ("Node NotReady", "critical"),
    "Killing": ("Container termination. Mixed with forced kills after terminationGracePeriod it signals missing graceful shutdown", "info"),
    "FailedKillPod": ("Pod termination failed. Runtime problem", "medium"),
    "FreeDiskSpaceFailed": ("kubelet image GC could not free space. Disk is full of in-use images and logs", "high"),
    "UpdateFailed": ("Operator reconcile failure (ExternalSecret etc.)", "medium"),
    "DisruptionBlocked": ("Karpenter tried to disrupt a node (replace, consolidate) but was blocked by budgets or PDBs", "low"),
    "SystemOOM": ("Node kernel OOM", "high"),
    # The two below were log-signature phrases until #129 found that the components only emit them as Events (MetalLB: controller/service.go:144@v0.14.5;
    # kubelet: pkg/kubelet/kubelet.go:1553@v1.32.13 `Eventf(..., events.ImageGCFailed, ...)` through the recorder, logged only at --v=3).
    "AllocationFailed": ("MetalLB could not assign an IP to a LoadBalancer Service (pool exhausted, no pool matches). The Service stays at EXTERNAL-IP Pending", "high"),
    "ImageGCFailed": ("kubelet image garbage collection could not free the required disk; disk-pressure eviction is next", "medium"),
}


def _snapshots(context_root: Path) -> list[Path]:
    return sorted(p for p in context_root.iterdir() if p.is_dir() and (p / "events.json").is_file())


def _event_key(e: dict) -> str:
    return (e.get("metadata") or {}).get("uid") or f"{e.get('reason')}|{(e.get('involvedObject') or {}).get('uid')}|{e.get('firstTimestamp')}"


def count_of(e: dict) -> int:
    """How many times the Event happened: `count` for events written through the legacy recorder, `series.count` for events written through the
    events.k8s.io recorder (the scheduler's `Scheduled`, `FailedScheduling`, `Preempted`), which has no `count` in the core/v1 view and keeps the repeats in
    `series.count` (kubernetes/kubernetes pkg/apis/events/v1/conversion.go:40-42@v1.37.2; staging/src/k8s.io/client-go/tools/events/event_broadcaster.go:181@v1.37.2); 1 when neither is there."""
    c = e.get("count") or ((e.get("series") or {}).get("count")) or 1
    return int(c) if isinstance(c, (int, float)) else 1


_count = count_of


def _obj(e: dict) -> str:
    inv = e.get("involvedObject") or {}
    ns = inv.get("namespace")
    return f"{inv.get('kind', '?')}/{ns + '/' if ns else ''}{inv.get('name', '?')}"


def build_history(context_root: Path, current: Path | None = None) -> dict:
    """Merge events.json from every snapshot in the context folder into per-Reason trends and uid-deduplicated totals."""
    snaps = _snapshots(context_root)
    per_uid: dict[str, dict] = {}  # uid → {reason, type, obj, max_count, first, last, snapshots[]}
    per_snapshot: dict[str, dict] = {}  # snapshot -> {reason: occurrences (sum of counts at that time)}
    for sp in snaps:
        items = (load_json(sp / "events.json") or {}).get("items", []) or []
        by_reason: dict[str, int] = defaultdict(int)
        for e in items:
            k = _event_key(e)
            c = _count(e)
            reason = e.get("reason") or "?"
            by_reason[reason] += c
            first = e.get("firstTimestamp") or e.get("eventTime") or (e.get("metadata") or {}).get("creationTimestamp")
            last = e.get("lastTimestamp") or ((e.get("series") or {}).get("lastObservedTime")) or first
            rec = per_uid.setdefault(k, {"reason": reason, "type": e.get("type"), "object": _obj(e), "max_count": 0, "first": first, "last": last, "snapshots": [], "message": (e.get("message") or "")[:200]})
            rec["max_count"] = max(rec["max_count"], c)
            if first and (rec["first"] is None or first < rec["first"]):
                rec["first"] = first
            if last and (rec["last"] is None or last > rec["last"]):
                rec["last"] = last
            rec["snapshots"].append(sp.name)
        per_snapshot[sp.name] = dict(by_reason)

    # Per-Reason totals (uid-deduplicated) and trend
    reasons: dict[str, dict] = {}
    for rec in per_uid.values():
        r = reasons.setdefault(
            rec["reason"],
            {
                "reason": rec["reason"],
                "type": rec["type"],
                "tracked": rec["reason"] in TRACKED,
                "meaning": TRACKED.get(rec["reason"], ("", ""))[0],
                "severity_hint": TRACKED.get(rec["reason"], ("", ""))[1],
                "events": 0,
                "occurrences": 0,
                "first": rec["first"],
                "last": rec["last"],
                "objects": defaultdict(int),
            },
        )
        r["events"] += 1
        r["occurrences"] += rec["max_count"]
        r["objects"][rec["object"]] += rec["max_count"]
        if rec["first"] and (r["first"] is None or rec["first"] < r["first"]):
            r["first"] = rec["first"]
        if rec["last"] and (r["last"] is None or rec["last"] > r["last"]):
            r["last"] = rec["last"]
    out_reasons = []
    for r in reasons.values():
        series = [per_snapshot.get(sp.name, {}).get(r["reason"], 0) for sp in snaps]
        top = sorted(r["objects"].items(), key=lambda kv: -kv[1])[:5]
        trend = "flat"
        if len(series) >= 2:
            if series[-1] > series[-2]:
                trend = "up"
            elif series[-1] < series[-2]:
                trend = "down"
            if series[-1] > 0 and all(x == 0 for x in series[:-1]):
                trend = "new"
            if len(series) >= 3 and series[-1] == 0 and series[-2] == 0 and sum(series) > 0:
                trend = "quiet"  # zero in the last two snapshots — only past incidents remain (e.g. Unhealthy at 0 but flagged warn/high)
        out_reasons.append({**{k: v for k, v in r.items() if k != "objects"}, "objects_top": [{"object": o, "occurrences": n} for o, n in top], "per_snapshot": series, "trend": trend})
    out_reasons.sort(key=lambda r: (r["type"] != "Warning", -r["occurrences"]))

    tracked_hits = [r for r in out_reasons if r["tracked"] and r["occurrences"] > 0]
    tracked_silent = sorted(set(TRACKED) - {r["reason"] for r in tracked_hits})
    hist = {
        "context_root": str(context_root),
        "snapshots": [sp.name for sp in snaps],
        "snapshot_count": len(snaps),
        "unique_events": len(per_uid),
        "reasons": out_reasons,
        "tracked_hits": tracked_hits,
        "tracked_silent": tracked_silent,
        "note": "The same event (uid) grows its count across snapshots, so only the largest count is kept. Event TTL is 1 hour, so most events between runs are lost (see the event-retention absence check)",
    }
    write_private(context_root / "events-history.json", json.dumps(hist, ensure_ascii=False, indent=1, default=str))
    return hist

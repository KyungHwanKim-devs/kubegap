"""OOM history per workload over seven days: Prometheus restarts and kube-state-metrics reasons joined with the kernel's oom-kill lines of every node.

Part of the resilience section (lib/summaries/resilience): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

import datetime as _dt
import re

from ...foundations.nodetext import kernel_oom_kills
from ...foundations.snapshot import metric_doc, metric_rows


def node_boot_times(cx) -> dict[str, _dt.datetime]:
    """node_boot_time_seconds (node-exporter, instance=IP:9100) → node name. The baseline for separating reboot-induced restarts and post-boot logs."""
    ip_to_node = {}
    for n in cx.nodes:
        for a in (n.get("status") or {}).get("addresses") or []:
            if a.get("type") == "InternalIP":
                ip_to_node[a.get("address")] = n["metadata"]["name"]
    out = {}
    for lab, v in metric_rows(cx.snap, "node_boot_time"):
        inst = lab.get("instance", "").split(":")[0]
        node = ip_to_node.get(inst) or lab.get("node")
        if node:
            out[node] = _dt.datetime.fromtimestamp(v, tz=_dt.UTC)
    return out


_KIND_SHORT = {"Deployment": "deploy", "StatefulSet": "sts", "DaemonSet": "ds", "Job": "job", "CronJob": "cronjob", "ReplicaSet": "rs", "ReplicationController": "rc"}


def owner_of_pod(cx, ns: str, pod: str, created_by: tuple[str | None, str | None] | None) -> str:
    """`deploy/<name>`, `sts/<name>`, `cronjob/<name>` … for a pod, the same shape lib.judgement.evaluate.Context.workload gives a metric series. A live pod is read from its ownerReferences;
    a pod that is already gone is read from kube_pod_info's created_by, and a ReplicaSet is resolved to its Deployment through the ReplicaSets still in the snapshot, else by stripping the hash with a `?` mark."""
    obj = cx.pod_by_name.get((ns, pod))
    if obj is not None:
        own = next(iter(obj["metadata"].get("ownerReferences") or []), None)
        if own:
            created_by = (own.get("kind"), own.get("name"))
    kind, name = created_by or (None, None)
    if not kind or not name:
        return f"pod/{pod}"
    if kind == "ReplicaSet":
        parent = cx.rs_owner.get((ns, name))
        if parent:
            kind, name = parent
        elif (ns, name) in cx.rs_names:
            return f"rs/{name}"  # a ReplicaSet of its own, no Deployment above it
        else:
            # the ReplicaSet is gone too: strip the hash, and drop the guess mark when a Deployment of that name exists in the namespace, as lib.judgement.evaluate.Context.workload does
            name = name.rsplit("-", 1)[0]
            confirmed = any(k == "Deployment" and o["metadata"]["namespace"] == ns and o["metadata"]["name"] == name for k, o in cx.workloads) or ("Deployment", name) in {v for (n, _), v in cx.rs_owner.items() if n == ns}
            return f"{'deploy' if confirmed else 'deploy?'}/{name}"
    elif kind == "Job":
        parent = cx.job_owner.get((ns, name))
        if parent:
            kind, name = parent
        elif (ns, name) not in cx.job_names and re.search(r"-\d{6,}$", name):
            # a finished CronJob run whose Job is gone: <cronjob>-<schedule id>. One target per CronJob, as lib.judgement.evaluate.Context.workload gives it
            base = name.rsplit("-", 1)[0]
            return f"{'cronjob' if (ns, base) in cx.cronjob_names else 'cronjob?'}/{base}"
    return f"{_KIND_SHORT.get(kind, kind.lower())}/{name}"


def oom_7d(cx) -> dict:
    """OOM history per workload and container over 7 days, pods a rollout has replaced included.

    Two sources that measure different things, both kept and both named in the row:
    - Prometheus (`metrics/oom_pods_7d.json`, `metrics/pod_info_7d.json`, both modes): every pod that ended with OOMKilled at any time in 7 days, with that pod's 7-day restart increase.
      The restarts are an upper bound of its OOM kills, since a probe failure restarts a container too; the number of pods is the number of distinct lives of the workload that died of OOM at least once.
    - Kernel log (`logs/node/<node>/os.txt`, full mode, nodes the node backend reached): one entry per `oom-kill:` line, attributed through the pod uid in the cgroup path. Exact count, 24-hour window.
      `kernel_nodes_read` says how many of the nodes the workload's pods ran on had a kernel log, so a 0 is "none seen" only when every node was read.
    cAdvisor's `container_oom_events_total` (`metrics/oom_events_7d.json`) is carried as `cadvisor_oom_events_7d` for the evidence only: on cgroup v2 nodes it stayed at 0 through five kernel kills."""
    rows: dict[str, dict] = {}
    info: dict[tuple[str, str], dict] = {}
    for lab, _v in metric_rows(cx.snap, "pod_info_7d"):
        info[(lab.get("namespace"), lab.get("pod"))] = lab
    by_uid: dict[str, tuple[str, str]] = {}
    for p in cx.pods:
        if p["metadata"].get("uid"):
            by_uid[p["metadata"]["uid"]] = (p["metadata"]["namespace"], p["metadata"]["name"])
    for (ns, pod), lab in info.items():
        if lab.get("uid"):
            by_uid.setdefault(lab["uid"], (ns, pod))
    live = {(p["metadata"]["namespace"], p["metadata"]["name"]) for p in cx.pods}
    pod_nodes: dict[tuple[str, str], str | None] = {}

    def row_for(ns: str, pod: str, container: str | None) -> dict:
        lab = info.get((ns, pod)) or {}
        wl = owner_of_pod(cx, ns, pod, (lab.get("created_by_kind"), lab.get("created_by_name")))
        key = f"{ns}/{wl}" + (f":{container}" if container else "")
        obj = cx.pod_by_name.get((ns, pod))
        pod_nodes[(ns, pod)] = (obj or {}).get("spec", {}).get("nodeName") if obj else lab.get("node")
        return rows.setdefault(
            key,
            {
                "target": key,
                "namespace": ns,
                "workload": wl,
                "container": container,
                "prod": ns in cx.prod,
                "pods": [],
                "pods_oomkilled": 0,
                "pods_replaced": 0,
                "restarts_of_those_pods": 0,
                "live_pod_restarts_max": 0,
                "cadvisor_oom_events_7d": 0,
                "kernel_kills_24h": 0,
                "kernel_kill_times": [],
                "kernel_nodes_read": 0,
                "kernel_nodes_total": 0,
                "kernel_log_read": False,
                "kernel_any_node_read": False,
                "kernel_nodes_old_script": 0,
                "kernel_cgroup_ooms_on_nodes": 0,
                "nodes": [],
            },
        )

    for lab, v in metric_rows(cx.snap, "oom_pods_7d"):
        ns, pod, c = lab.get("namespace"), lab.get("pod"), lab.get("container")
        if not ns or not pod:
            continue
        rc = round(v)
        if rc < 1:
            continue  # the OOMKilled reason label outlives the window; a kill inside 7 days always leaves a restart in it
        r = row_for(ns, pod, c)
        # a StatefulSet pod keeps its name when it is recreated: the series of the earlier pod differs in `uid`, and its restarts are history, not what the pod there now does
        now = cx.pod_by_name.get((ns, pod))
        is_live = (ns, pod) in live and (not lab.get("uid") or not now or lab["uid"] == (now.get("metadata") or {}).get("uid"))
        r["pods"].append({"pod": pod, "restarts_7d": rc, "live": is_live, "node": pod_nodes.get((ns, pod))})
        r["pods_oomkilled"] += 1
        r["restarts_of_those_pods"] += rc
        if is_live:
            r["live_pod_restarts_max"] = max(r["live_pod_restarts_max"], rc)
        else:
            r["pods_replaced"] += 1
    for lab, v in metric_rows(cx.snap, "oom_events_7d"):
        ns, pod, c = lab.get("namespace"), lab.get("pod"), lab.get("container")
        if ns and pod and v > 0:
            row_for(ns, pod, c)["cadvisor_oom_events_7d"] += round(v)
    # kernel kills: uid → pod → row. A kill in a pod that has no OOM row in Prometheus (kube-state-metrics missed the termination, or the pod was deleted before its next scrape) still opens a row
    node_names = [n["metadata"]["name"] for n in cx.nodes]
    kernel = kernel_oom_kills(cx.snap, node_names)
    kills_unmapped = 0
    for node, rec in kernel.items():
        for k in rec["kills"]:
            tgt = by_uid.get(k["pod_uid"] or "")
            if not tgt:
                kills_unmapped += 1
                continue
            ns, pod = tgt
            # the kernel names the task, not the container; a pod with one app container gets it, a multi-container pod is counted on the pod
            obj = cx.pod_by_name.get(tgt)
            containers = [c.get("name") for c in ((obj or {}).get("spec") or {}).get("containers") or []]
            known = [r for r in rows.values() if any(p["pod"] == pod for p in r["pods"]) and r["namespace"] == ns]
            if len(known) == 1:
                r = known[0]
            elif known:
                # several containers of this pod ended by OOM: the kernel names the task, not the container, so the kill goes to the container that restarted most, the one most likely dying
                r = max(known, key=lambda x: sum(p["restarts_7d"] for p in x["pods"] if p["pod"] == pod))
            elif len(containers) == 1:
                r = row_for(ns, pod, containers[0])
            else:
                r = row_for(ns, pod, None)
            r["kernel_kills_24h"] += 1
            if k.get("time"):
                r["kernel_kill_times"].append(k["time"])
            if node not in r["nodes"]:
                r["nodes"].append(node)
    for r in rows.values():
        nodes = {p.get("node") for p in r["pods"] if p.get("node")} | set(r["nodes"])
        r["nodes"] = sorted(nodes)
        r["kernel_nodes_total"] = len(nodes)
        read = [n for n in nodes if n in kernel and kernel[n]["source"] in ("journalctl", "dmesg")]
        r["kernel_nodes_read"] = sum(1 for n in read if kernel[n]["oom_section"])
        r["kernel_nodes_old_script"] = sum(1 for n in read if not kernel[n]["oom_section"])  # the log was read, but by a node script that kept no oom-kill lines: a 0 from it means "unknown", not "none"
        r["kernel_cgroup_ooms_on_nodes"] = sum(kernel[n]["oom_cgroup_count"] for n in read if not kernel[n]["oom_section"])
        r["kernel_log_read"] = r["kernel_nodes_read"] > 0
        r["kernel_any_node_read"] = any(rec["source"] in ("journalctl", "dmesg") for rec in kernel.values())  # False in daily mode, where no node log is collected at all
        r["kernel_kill_times"] = sorted(r["kernel_kill_times"])
        r["last_kill"] = r["kernel_kill_times"][-1] if r["kernel_kill_times"] else None
        r["pods"].sort(key=lambda p: (-p["restarts_7d"], p["pod"]))
    out_rows = sorted(rows.values(), key=lambda r: (-r["kernel_kills_24h"], -r["pods_oomkilled"], -r["restarts_of_those_pods"], r["target"]))
    prometheus_read = bool((metric_doc(cx.snap, "oom_pods_7d") or {}).get("ok"))
    return {
        "source": "metrics/oom_pods_7d.json + metrics/pod_info_7d.json + metrics/oom_events_7d.json + logs/node/<node>/os.txt oom_samples + objects/pods.json",
        "prometheus_read": prometheus_read,
        "kernel_nodes_read": sorted(n for n, rec in kernel.items() if rec["source"] in ("journalctl", "dmesg") and rec["oom_section"]),
        "kernel_nodes_old_script": sorted(n for n, rec in kernel.items() if rec["source"] in ("journalctl", "dmesg") and not rec["oom_section"]),
        "kernel_kills_unmapped": kills_unmapped,  # oom-kill lines whose pod uid no live pod and no 7-day Prometheus pod carries: a pod deleted before kube-state-metrics saw its last state
        # rows is None when the Prometheus side was not collected (a snapshot from before rubric 0.1.66, or no Prometheus): the check then skips instead of passing on an empty table
        "rows": out_rows if prometheus_read else None,
        "repeated": [r["target"] for r in out_rows if r["kernel_kills_24h"] >= 3 or r["restarts_of_those_pods"] >= 3] if prometheus_read else [],
    }

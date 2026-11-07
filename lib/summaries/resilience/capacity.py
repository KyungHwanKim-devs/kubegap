"""The N+1 capacity model: does the cluster keep every workload running when its largest node is lost?

Part of the resilience section (lib/summaries/resilience): `analyze` in the package's __init__ builds the `Ctx` of loaded objects and calls this module;
this module imports the foundations only and takes the context as an argument.
"""

from __future__ import annotations

from ...foundations.quantity import parse as quantity
from ...foundations.workload import eligible_nodes


def n_plus_one(cx) -> dict:
    nodes = []
    for n in cx.nodes:
        if (n.get("spec") or {}).get("unschedulable"):
            continue
        alloc = (n.get("status") or {}).get("allocatable") or {}
        nodes.append(
            {
                "name": n["metadata"]["name"],
                "cpu": quantity(alloc.get("cpu")),
                "memory": quantity(alloc.get("memory")),
                "role": "control-plane" if any(k.startswith(("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/master")) for k in (n["metadata"].get("labels") or {})) else "worker",
            }
        )
    if not nodes:
        return {"available": False}
    req_cpu = req_mem = 0.0
    per_pod = []
    for p in cx.pods:
        if p["status"].get("phase") != "Running":
            continue
        own = next((x.get("kind") for x in p["metadata"].get("ownerReferences") or []), None)
        if own == "DaemonSet":
            continue  # a DaemonSet runs one per node and is not a candidate to move
        c = m = 0.0
        for cont in p["spec"].get("containers") or []:
            r = (cont.get("resources") or {}).get("requests") or {}
            c += quantity(r.get("cpu"))
            m += quantity(r.get("memory"))
        req_cpu += c
        req_mem += m
        per_pod.append((p["metadata"]["namespace"], p["metadata"]["name"], p["spec"].get("nodeName"), c, m))
    total_cpu, total_mem = sum(n["cpu"] for n in nodes), sum(n["memory"] for n in nodes)
    big = max(nodes, key=lambda n: n["cpu"])
    rest_cpu, rest_mem = total_cpu - big["cpu"], total_mem - max(n["memory"] for n in nodes)
    # pods that cannot fit on any remaining node when the one (largest) node is lost (request larger than the remaining nodes' allocatable)
    others = [n for n in nodes if n["name"] != big["name"]]
    # scheduling constraints (nodeSelector, required nodeAffinity, taints) are considered too, not just resources — on a small k3s cluster 30 prod pods could only go to one node via nodeAffinity yet "cannot fit: []" was reported
    node_objs = {n["metadata"]["name"]: n for n in cx.nodes}
    pod_spec_by = {(p["metadata"]["namespace"], p["metadata"]["name"]): p["spec"] for p in cx.pods}
    cannot_fit = []
    for ns, pod, nd, c, m in per_pod:
        if nd != big["name"]:
            continue
        spec = pod_spec_by.get((ns, pod)) or {}
        elig = [e for e in eligible_nodes(spec, [node_objs[n["name"]] for n in others if n["name"] in node_objs], ignore_node_name=True) if e != big["name"]]
        if not elig:
            cannot_fit.append(
                {"namespace": ns, "pod": pod, "node": nd, "cpu": round(c, 2), "memory_gb": round(m / 1024**3, 2), "reason": "scheduling constraints (nodeSelector, nodeAffinity, taints) prevent moving to another node", "eligible_nodes": []}
            )
            continue
        elig_cpu = max(n["cpu"] for n in others if n["name"] in elig)
        elig_mem = max(n["memory"] for n in others if n["name"] in elig)
        if c > elig_cpu or m > elig_mem:
            cannot_fit.append({"namespace": ns, "pod": pod, "node": nd, "cpu": round(c, 2), "memory_gb": round(m / 1024**3, 2), "reason": "request exceeds the allocatable of every eligible node", "eligible_nodes": elig})
    on_big = [x for x in per_pod if x[2] == big["name"]]
    # N+1 per pool of eligible nodes: pods that may only land on some nodes (nodeSelector, nodeAffinity, taints) must fit into the free room of those nodes alone;
    # the cluster-wide sum says they fit while the labelled nodes are full. The free room of a node is its allocatable minus the requests already running there.
    used_cpu: dict[str, float] = {}
    used_mem: dict[str, float] = {}
    for p in cx.pods:  # every running pod, DaemonSets included: their requests occupy the room the moving pods would need
        if p["status"].get("phase") != "Running" or not p["spec"].get("nodeName"):
            continue
        nd = p["spec"]["nodeName"]
        for cont in p["spec"].get("containers") or []:
            r = (cont.get("resources") or {}).get("requests") or {}
            used_cpu[nd] = used_cpu.get(nd, 0.0) + quantity(r.get("cpu"))
            used_mem[nd] = used_mem.get(nd, 0.0) + quantity(r.get("memory"))
    pools: dict[tuple, dict] = {}
    for ns, pod, _nd, c, m in on_big:
        spec = pod_spec_by.get((ns, pod)) or {}
        elig = tuple(sorted(e for e in eligible_nodes(spec, [node_objs[n["name"]] for n in others if n["name"] in node_objs], ignore_node_name=True) if e != big["name"]))
        pl = pools.setdefault(elig, {"eligible_nodes": list(elig), "pods": 0, "prod_pods": 0, "needed_cpu": 0.0, "needed_memory": 0.0})
        pl["pods"] += 1
        pl["prod_pods"] += 1 if ns in cx.prod else 0
        pl["needed_cpu"] += c
        pl["needed_memory"] += m
    pool_rows = []
    for elig, pl in pools.items():
        free_cpu = sum(max(n["cpu"] - used_cpu.get(n["name"], 0.0), 0.0) for n in others if n["name"] in elig)
        free_mem = sum(max(n["memory"] - used_mem.get(n["name"], 0.0), 0.0) for n in others if n["name"] in elig)
        ok_pool = pl["needed_cpu"] <= free_cpu and pl["needed_memory"] <= free_mem
        within_margin = not ok_pool and pl["needed_cpu"] <= free_cpu * 1.02 and pl["needed_memory"] <= free_mem * 1.02
        pool_rows.append(
            {
                **pl,
                "needed_cpu": round(pl["needed_cpu"], 2),
                "needed_memory_gb": round(pl["needed_memory"] / 1024**3, 2),
                "free_cpu": round(free_cpu, 2),
                "free_memory_gb": round(free_mem / 1024**3, 2),
                "ok": ok_pool or within_margin,
                "tight": within_margin,  # fits only inside the 2% flapping margin: pass, but the report says so
            }
        )
        pool_rows[-1].pop("needed_memory", None)
    pools_ok = all(r["ok"] for r in pool_rows)
    short = [r for r in pool_rows if not r["ok"]]
    ok_total = req_cpu <= rest_cpu * 1.02 and req_mem <= rest_mem * 1.02
    return {
        "available": True,
        "nodes": len(nodes),
        "largest_node": big["name"],
        "largest_node_cpu": big["cpu"],
        "largest_node_memory_gb": round(big["memory"] / 1024**3, 1),
        "allocatable_cpu_total": round(total_cpu, 2),
        "allocatable_cpu_without_largest": round(rest_cpu, 2),
        "requests_cpu_total": round(req_cpu, 2),
        "allocatable_memory_gb_total": round(total_mem / 1024**3, 1),
        "allocatable_memory_gb_without_largest": round(rest_mem / 1024**3, 1),
        "requests_memory_gb_total": round(req_mem / 1024**3, 1),
        "cpu_ok": req_cpu <= rest_cpu * 1.02,
        "memory_ok": req_mem <= rest_mem * 1.02,
        "ok": ok_total and pools_ok,
        "total_ok": ok_total,
        "pools": pool_rows,
        "pools_short": [{"eligible_nodes": r["eligible_nodes"], "pods": r["pods"], "needed_cpu": r["needed_cpu"], "free_cpu": r["free_cpu"], "needed_memory_gb": r["needed_memory_gb"], "free_memory_gb": r["free_memory_gb"]} for r in short],
        "tight": any(r["tight"] for r in pool_rows) or (ok_total and not (req_cpu <= rest_cpu and req_mem <= rest_mem)),
        "margin": 0.02,  # 2% margin: a single minute-level CronJob pod (0.01 cores) used to flip pass/fail back and forth; inside the margin the result is ok and tight
        "pods_on_largest_node": len(on_big),
        "prod_pods_on_largest_node": sum(1 for x in on_big if x[0] in cx.prod),
        "cannot_fit_elsewhere": cannot_fit,
        "cannot_fit_prod": [f"{x['namespace']}/{x['pod']}" for x in cannot_fit if x["namespace"] in cx.prod],
        "karpenter": cx.karpenter,
        "autoscaler": cx.autoscaler,
        "autoscaler_name": cx.autoscaler_name,
        "note": "With a node autoscaler, Karpenter or cluster-autoscaler, pods only fail to start until a new node comes up (Karpenter measured p50 62 seconds). Without one, this is the list of pods that can never start again if one node dies. pools_short lists the groups of pods whose eligible nodes alone have no room for them",
    }

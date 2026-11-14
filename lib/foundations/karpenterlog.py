"""What the Karpenter controller's log says about the last 24 hours: how long nodes took to come up, which it removed and why, which launches
failed. Counted from the text `kubectl logs` returned while the component logs are collected (lib/collection/collect); the log is not stored.
lib/summaries/scaling.py puts the result into the scaling section."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .snapshot import parse_ts

LOG_KEYS = ("latency_24h", "nodeclaims_launched_24h", "disruptions_24h", "disrupted_24h", "launch_failures_24h")

# The Karpenter disruption line, in the three shapes it has had (references/sources.md, "lib/summaries/scaling.py Karpenter log facts"; kubernetes-sigs/karpenter):
# - through 0.37: `"message":"disrupting via <reason> <decision>, terminating N nodes (M pods) <node>/<type>/<capacity>, …"` (pkg/controllers/disruption/controller.go:188@v0.37.0,
#   Command.String() types.go:184-194@v0.37.0);
# - 1.0.0 to 1.2.x: `"message":"disrupting nodeclaim(s) via <decision>, terminating N nodes (M pods) …"` with the reason as a field (controller.go:188@v1.0.0, types.go:141-151@v1.0.0);
# - from 1.3.0: `"message":"disrupting node(s)"` with structured values `decision`, `disrupted-node-count`, `pod-count`, `disrupted-nodes` (a list of {Node, NodeClaim, instance-type,
#   capacity-type}) and the reason as a `reason` field (controller.go:205@v1.3.0, queue.go:295@v1.6.0; types.go:143-176@v1.3.0, :167-200@v1.6.0) or, at 1.15.1, as the first
#   token of the `command` field `<reason>/<id>: <decision>: nodepools=[…]: [nodes] …` (queue.go:388-390@v1.15.1, types.go:350-380,449-487@v1.15.1).
_DISRUPT_037 = re.compile(r'"message":"disrupting via (\w+) (\w+), terminating (\d+) nodes \((\d+) pods\) ([^"]+)"')
_DISRUPT_10 = re.compile(r'"message":"disrupting nodeclaim\(s\) via (\w+), terminating (\d+) nodes \((\d+) pods\) ([^"]+)"')
_DISRUPT_13 = re.compile(r'"message":"disrupting node\(s\)"')
# The launch failure: the lifecycle controller's own ERROR line (`launching nodeclaim`/`creating nodeclaim`, pkg/controllers/nodeclaim/lifecycle/launch.go:84-86,100,103@v0.37.0,
# :99,113,132@v1.15.1), controller-runtime's `"msg":"Reconciler error"` whose `"error"` starts `launching nodeclaim, creating instance, …` for IAM and parameter failures, and the
# EC2 codes the provider relays (aws/karpenter-provider-aws pkg/providers/instance/instance.go@v0.37.0, @v1.15.1). The level is spelled ERROR at every version
# (pkg/operator/logging/logging.go:64-74@v0.37.0, :42-71@v1.15.1, CapitalLevelEncoder).
_LAUNCH_FAIL = re.compile(r'"level":"ERROR".*(launching|creating) nodeclaim|"error":"launching nodeclaim,|InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity')
_LAUNCH_CODE = re.compile(r"(InsufficientInstanceCapacity|insufficient capacity|MaxSpotInstanceCountExceeded|UnfulfillableCapacity)")
_LAUNCH_PHRASE = re.compile(r"(launching nodeclaim|creating nodeclaim)")


def disruption_line(line: str) -> tuple[str, str, int, int, str] | None:
    """(reason, decision, nodes, pods, node names) of a Karpenter disruption log line in any of its three shapes, else None."""
    m = _DISRUPT_037.search(line)
    if m:
        return m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
    m = _DISRUPT_10.search(line)
    if m:
        r = re.search(r'"reason":"(\w+)"', line)
        return (r.group(1) if r else "?"), m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    if _DISRUPT_13.search(line):
        r = re.search(r'"reason":"(\w+)"', line) or re.search(r'"command":"(\w+)/', line)
        d = re.search(r'"decision":"(\w+)"', line)
        n = re.search(r'"disrupted-node-count":(\d+)', line)
        p = re.search(r'"pod-count":(\d+)', line)
        names = ", ".join(re.findall(r'"Node":\{"name":"([^"]+)"', line))  # only disrupted-nodes entries carry a Node
        # 1.15.1 writes the reason capitalised inside `command` (`DisruptionReason` constants, pkg/apis/v1/nodepool.go:184-189@v1.15.1); 1.3 to 1.6 lower-case it
        return (r.group(1).lower() if r else "?"), (d.group(1).lower() if d else "?"), int(n.group(1)) if n else 0, int(p.group(1)) if p else 0, names
    return None


def launch_failure_key(line: str) -> str | None:
    """The failure kind of a Karpenter launch-failure log line (the EC2 code or the controller phrase), else None."""
    if _LAUNCH_FAIL.search(line):
        m = _LAUNCH_CODE.search(line) or _LAUNCH_PHRASE.search(line)  # the EC2 code names the cause; the controller phrase only says a launch failed
        return m.group(1) if m else None
    return None


def facts(texts: list[str]) -> dict:
    """The LOG_KEYS from the controller's log texts."""
    lat: dict[str, dict] = defaultdict(dict)
    disruptions: Counter = Counter()
    disrupted_nodes = []
    launch_failures: Counter = Counter()
    created_24h = 0
    for text in texts:
        for line in text.splitlines():
            if '"logger":"controller"' not in line and "level=" not in line:
                continue
            ts = parse_ts(line)
            m = re.search(r'"message":"(launched|registered|initialized) nodeclaim".*?"NodeClaim":\{"name":"([^"]+)"', line)
            if m and ts:
                lat[m.group(2)][m.group(1)] = ts
                if m.group(1) == "launched":
                    created_24h += 1
                continue
            d = disruption_line(line)
            if d:
                reason, decision, n_nodes, n_pods, names = d
                disruptions[f"{reason} {decision}"] += n_nodes
                disrupted_nodes.append({"time": ts.isoformat() if ts else None, "reason": f"{reason} {decision}", "nodes": names, "pods": n_pods})
                continue
            key = launch_failure_key(line)
            if key:
                launch_failures[key] += 1
    lat_rows = []
    for name, d in lat.items():
        if "launched" in d and "initialized" in d:
            lat_rows.append(
                {
                    "nodeclaim": name,
                    "launched_to_initialized_s": round((d["initialized"] - d["launched"]).total_seconds()),
                    "launched_to_registered_s": round((d["registered"] - d["launched"]).total_seconds()) if "registered" in d else None,
                }
            )
    lat_vals = sorted(r["launched_to_initialized_s"] for r in lat_rows)
    lat_stats = {"n": len(lat_vals), "p50_s": lat_vals[len(lat_vals) // 2] if lat_vals else None, "max_s": lat_vals[-1] if lat_vals else None, "slowest": sorted(lat_rows, key=lambda r: -r["launched_to_initialized_s"])}
    return {"latency_24h": lat_stats, "nodeclaims_launched_24h": created_24h, "disruptions_24h": dict(disruptions), "disrupted_24h": disrupted_nodes, "launch_failures_24h": dict(launch_failures)}

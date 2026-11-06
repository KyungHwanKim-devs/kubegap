"""MetalLB summary (collectors/metallb). Runs on every platform: MetalLB does not depend on k3s, and until #155 the pool and L2 data was built inside lib/k3s.py, so a kubeadm or Talos cluster got none of it.

Inputs: objects (ipaddresspools, services, l2advertisements, bgppeers, daemonsets speaker, deployments controller, validatingwebhookconfigurations, and the status resources below), metrics/pod/metallb-speaker/*.prom
(speaker metrics: config load/stale, k8s client update errors, layer2 ARP responses/gratuitous, BGP sessions). What we look at: pool remaining and Pending, L2 leader concentration, whether speaker runs on every node and whether its state was read, speakers with stale config.
Output: the `metallb` section of summary.json. Shape documented in references/summary-shape.md.

From 0.16 the speaker serves /metrics only over TLS with authentication (metallb/metallb speaker/main.go:99@v0.16.2, internal/k8s/k8s.go:159-163@v0.16.2; plain HTTP through speaker/main.go:86@v0.15.3). The API server
drops the client's Authorization header before the pod proxy (kubernetes/kubernetes staging/src/k8s.io/apiserver/pkg/endpoints/filters/authentication.go:90@v1.37.2, :87@v1.30.14) and kubegap sends no credential of the user to a pod, so
the step skips. What the checks need is published as objects anyway, readable with the ClusterRole's metallb.io rule:
- ServiceL2Status and ServiceBGPStatus: the node announcing a service (api/v1beta1/servicel2status_types.go:29,32,35@v0.16.2, servicebgpstatus_types.go:29,33,37@v0.16.2), one object per announcing node. Written only while the node announces
  (internal/k8s/controllers/layer2_status_controller.go:85-94@v0.16.2, bgp_status_controller.go:76-87@v0.16.2). ServiceL2Status was behind a flag that defaults to off at v0.14.5 (speaker/main.go:90@v0.14.5), so an empty list says nothing before 0.16.
- ConfigurationState: one object per component with `status.result` Valid, Invalid or Unknown and `status.errorSummary` (api/v1beta1/configurationstate_types.go:29,31,33,40,45@v0.16.2). First in v0.15.3.
Metrics stay the source for what they say when every speaker was read; the objects answer for a speaker that was not, and an Invalid state counts either way. Lost on 0.16+: the update error counter and the ARP and BGP counters, which exist only in /metrics: they are null, not 0, `metrics_not_read` names them and the step's skip reason says so in the report.
"""

from __future__ import annotations

import contextlib
import ipaddress
import re
from collections import Counter
from pathlib import Path

from . import versions
from .mask import strip_control
from .promtext import parse as _parse_prom
from .resilience import eligible_nodes
from .snapshot import load_json, objects

HTTPS_ONLY_SINCE = (0, 16, 0)
L2_STATUS, BGP_STATUS, CONFIG_STATE = "servicel2statuses.metallb.io", "servicebgpstatuses.metallb.io", "configurationstates.metallb.io"
COUNTERS = {"update_errors_total": "update_errors", "arp_requests_total": "arp_requests", "arp_responses_total": "arp_responses", "gratuitous_total": "gratuitous", "bgp_sessions": "bgp_sessions", "bgp_sessions_up": "bgp_sessions_up"}
METRICS_NOT_READ = ["metallb_k8s_client_update_errors_total", "metallb_layer2_requests_received", "metallb_layer2_responses_sent", "metallb_layer2_gratuitous_sent", "metallb_bgp_session_up"]


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _container(d: dict, role: str) -> dict:
    """The container named `role`, else the one whose image names it, else the first. `metallb-frr.yaml` puts `frr` before `speaker` (config/manifests/metallb-frr.yaml:2411,2513@v0.16.2, :1904,1993@v0.14.9),
    and reading the first gave the FRR version, which decides here which source is read."""
    containers = ((((d.get("spec") or {}).get("template") or {}).get("spec") or {}).get("containers")) or [{}]
    return next((c for c in containers if c.get("name") == role), next((c for c in containers if role in (c.get("image") or "")), containers[0]))


def _workload(found: list[dict], role: str) -> dict | None:
    """Of the workloads whose name fits, the one running a MetalLB image: any DaemonSet can be called `x-speaker`."""
    return next((d for d in found if "metallb" in (_container(d, role).get("image") or "")), found[0] if found else None)


def _lb_class(*containers: dict) -> str:
    """The --lb-class the controller or speaker runs with, "" without one."""
    for c in containers:
        args = [str(a) for a in c.get("args") or []]
        for i, a in enumerate(args):
            if a.startswith("--lb-class="):
                return a.split("=", 1)[1]
            if a == "--lb-class" and i + 1 < len(args):
                return args[i + 1]
    return ""


def _metric_texts(snap: Path) -> dict[str, str]:
    """pod -> text of the speaker metric files that hold a series only the speaker has. A file without one was read from the wrong port (a configured `metrics_port`, or the FRR sidecar, which also
    prints metallb_bgp_session_up: frr-tools/metrics/collector/bgp.go:21@v0.14.9): it says nothing about the speaker, and counting it passed every check on nothing. metallb_k8s_client_config_loaded_bool
    is a plain gauge registered at start (internal/k8s/controllers/stats.go:25,43@v0.16.2), so a healthy speaker always prints it."""
    d = snap / "metrics" / "pod" / "metallb-speaker"
    texts = {f.stem: f.read_text(encoding="utf-8", errors="replace") for f in sorted(d.glob("*.prom"))} if d.is_dir() else {}
    return {pod: text for pod, text in texts.items() if re.search(r"^metallb_k8s_client_", text, re.MULTILINE)}


def _step(snap: Path) -> dict:
    """The metallb-speaker-metrics step of collect-result.json; it moved here from k3s-platform (compatibility with older snapshots)."""
    cr = load_json(snap / "collect-result.json") or {}
    return (((cr.get("metallb") or {}).get("steps") or {}).get("metallb-speaker-metrics")) or (((cr.get("k3s-platform") or {}).get("steps") or {}).get("metallb-speaker-metrics")) or {}


def _pools(snap: Path, lb_class: str = "") -> dict:
    """Pools (size, used, free), the LoadBalancer Services MetalLB handles and the Pending ones. MetalLB takes a Service only when its spec.loadBalancerClass equals --lb-class, both unset included
    (internal/k8s/controllers/service_controller.go:159-175@v0.16.2), so a Service of another implementation has no address from these pools and is not waiting for one."""
    pools = []
    total_ips = 0
    for p in objects(snap, "ipaddresspools.metallb.io"):
        n = 0
        for a in (p.get("spec") or {}).get("addresses", []) or []:
            if "-" in a:
                lo, hi = a.split("-", 1)
                with contextlib.suppress(ValueError):
                    n += int(ipaddress.ip_address(hi.strip())) - int(ipaddress.ip_address(lo.strip())) + 1
            else:
                with contextlib.suppress(ValueError):
                    n += ipaddress.ip_network(a.strip(), strict=False).num_addresses
        total_ips += n
        pools.append({"name": p["metadata"]["name"], "addresses": (p.get("spec") or {}).get("addresses"), "size": n, "auto_assign": (p.get("spec") or {}).get("autoAssign", True)})
    lb = []
    other_class = 0
    for s in objects(snap, "services"):
        if (s.get("spec") or {}).get("type") == "LoadBalancer":
            if ((s.get("spec") or {}).get("loadBalancerClass") or "") != lb_class:
                other_class += 1
                continue
            ingress = ((s.get("status") or {}).get("loadBalancer") or {}).get("ingress", []) or []
            ips = [i.get("ip") for i in ingress if i.get("ip")]
            lb.append({"namespace": s["metadata"]["namespace"], "name": s["metadata"]["name"], "ips": ips, "pending": not ingress})
    used = len({ip for s in lb for ip in s["ips"]})
    return {"present": bool(pools), "pools": pools, "total_ips": total_ips, "used": used, "free": (total_ips - used) if pools else None, "services": lb, "other_class_services": other_class, "pending": [s for s in lb if s["pending"]]}


def _announced_from_metrics(texts: dict[str, str]) -> list[dict]:
    """metallb_speaker_announced{ip,node,protocol,service} with a value of 1 or more."""
    announced = []
    for text in texts.values():
        for ln in text.splitlines():
            if not ln.startswith("metallb_speaker_announced{"):
                continue
            m = re.match(r"metallb_speaker_announced\{([^}]*)\}\s+([0-9.e+-]+)", ln)
            if not m or float(m.group(2)) < 1:
                continue
            labels = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            announced.append({"ip": labels.get("ip"), "node": labels.get("node"), "protocol": labels.get("protocol"), "service": labels.get("service")})
    return announced


def _announced_from_status(snap: Path, lb: list[dict], node_names: list[str]) -> list[dict]:
    """The same rows from the status resources. They name the service, not the IP, so one row per IP of that Service keeps the counts in IPs as the metric has them
    (a node leads every IP of a service: multiple advertisements "share all fields except lb ip", layer2_status_controller.go:246@v0.16.2). Left out, because the metric would have no row:
    a status created a moment ago has no node yet (the status follows the create, :153), a Service that is gone or Pending has no IP to announce, and a node that is gone leaves its ServiceBGPStatus
    behind until its Pod object is collected (bgp_status_controller.go:76-87@v0.16.2 removes only the node's own; a new L2 leader removes the old one, layer2_status_controller.go:113@v0.16.2)."""
    ips = {f"{s['namespace']}/{s['name']}": s["ips"] for s in lb}
    rows = []
    for stem, protocol in ((L2_STATUS, "layer2"), (BGP_STATUS, "bgp")):
        for o in objects(snap, stem):
            st = o.get("status") or {}
            if st.get("node") and st.get("serviceName") and (not node_names or st["node"] in node_names):
                service = f"{st.get('serviceNamespace')}/{st['serviceName']}"
                rows += [{"ip": ip, "node": st["node"], "protocol": protocol, "service": service} for ip in ips.get(service) or []]
    return rows


def _l2(snap: Path, lb: list[dict], node_names: list[str], texts: dict[str, str], step: dict, tls_only: bool, https_only_version: bool) -> dict:
    """Which node advertises (leads) which service IP in L2 mode, from the speaker metrics when they were read, else from the status resources. available is false when neither says.
    An empty status list is an answer only where the resources are always written and were saved: 0.16+ with the file in the snapshot, and a BGP row says nothing about L2. L2Advertisement nodeSelectors are included too."""
    errors = []
    if not tls_only:
        for pod, r in (step.get("pods") or {}).items():
            if not r.get("ok"):
                errors.append({"pod": pod, "node": r.get("node"), "error": (r.get("error") or r.get("skipped") or "")[:160]})
            elif pod not in texts:
                errors.append({"pod": pod, "node": r.get("node"), "error": f"port {(step.get('target') or {}).get('port')} answered with no MetalLB series"})
    announced, source = [], None
    status_rows = _announced_from_status(snap, lb, node_names)
    status_source = f"objects/{L2_STATUS}.json, {BGP_STATUS}.json"
    if texts and not (errors and status_rows):  # the leaders one speaker printed do not stand for the speakers nobody read, when the status resources name them all
        announced, source = _announced_from_metrics(texts), "metrics/pod/metallb-speaker/*.prom (pod proxy GET)"
    else:
        announced = status_rows
        if any(r["protocol"] == "layer2" for r in announced) or (https_only_version and (snap / "objects" / f"{L2_STATUS}.json").is_file()):
            source = status_source
    advs = []
    for a in objects(snap, "l2advertisements.metallb.io"):
        sp = a.get("spec") or {}
        advs.append({"name": a["metadata"]["name"], "pools": sp.get("ipAddressPools"), "node_selectors": sp.get("nodeSelectors"), "interfaces": sp.get("interfaces")})
    # The leader is a Layer 2 idea: over BGP every eligible node announces the same IP, and one node carrying both protocols is two rows for one IP (protocol is "bgp" or "layer2", internal/config/config.go:91-92@v0.16.2)
    l2_rows = [r for r in announced if r["protocol"] == "layer2"]
    by_node: Counter = Counter(r["node"] for r in l2_rows if r["node"])
    total = len(l2_rows)
    leader = by_node.most_common(1)[0] if by_node else (None, 0)
    return {
        "available": source is not None,
        "source": source,
        "metrics_tls_only": tls_only,
        "speakers": len(texts),
        "speakers_unreadable": errors,
        "announced": announced,
        "announced_total": total,
        "lb_services": len([s for s in lb if not s["pending"]]),
        "by_node": dict(by_node),
        "leader_node": leader[0],
        "leader_share": round(leader[1] / total, 2) if total else None,
        "nodes_total": len(node_names),
        "advertisements": advs,
        "pinned_by_selector": any(a.get("node_selectors") for a in advs),
        "note": "In L2 mode one node advertises each service IP. If a single node advertises every IP, its NIC receives all external traffic, and when it dies everything is cut off during failover (about 10 seconds). Intended if pinned with nodeSelectors",
    }


def _config_states(snap: Path) -> list[dict]:
    """One row per ConfigurationState: the controller and each speaker (labels metallb.io/component-type and metallb.io/node-name)."""
    rows = []
    for o in objects(snap, CONFIG_STATE):
        st = o.get("status") or {}
        labels = (o.get("metadata") or {}).get("labels") or {}
        rows.append(
            {"name": o["metadata"]["name"], "component": labels.get("metallb.io/component-type"), "node": labels.get("metallb.io/node-name"), "result": st.get("result"), "error": strip_control(st.get("errorSummary") or "")[0][:200]}
        )
    return rows


def _not_reported(states: list[dict], speakers_desired: int | None, controller_desired: int | None) -> list[str]:
    """What the ConfigurationState list does not vouch for: a component still Unknown, and speakers or a controller with no object at all. One Valid object must not stand for the whole cluster."""
    judged = ("Valid", "Invalid")
    out = [s["name"] for s in states if s["result"] not in judged]
    seen = sum(1 for s in states if s["component"] == "speaker")
    if speakers_desired and seen < speakers_desired:
        out.append(f"{speakers_desired - seen} of {speakers_desired} speakers")
    if controller_desired and not any(s["component"] == "controller" for s in states):
        out.append("controller")
    return out


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    speaker = _workload([d for d in objects(snap, "daemonsets") if d["metadata"]["name"] in ("speaker", "metallb-speaker") or d["metadata"]["name"].endswith("-speaker")], "speaker")
    # The chart's fullname is the release name when that name holds `metallb` (charts/metallb/templates/_helpers.tpl:14-20@v0.16.2), so release metallb-prod gives metallb-prod-controller. `*-controller` alone is any operator, so past the fixed names the image decides.
    deployments = objects(snap, "deployments")
    named = [d for d in deployments if d["metadata"]["name"] in ("controller", "metallb-controller") or d["metadata"]["name"].endswith("metallb-controller")]
    by_image = [d for d in deployments if d["metadata"]["name"].endswith("-controller") and "metallb" in (_container(d, "controller").get("image") or "") and d not in named]
    controller = _workload(named + by_image, "controller")
    base = _pools(snap, _lb_class(*[_container(d, role) for d, role in ((controller, "controller"), (speaker, "speaker")) if d]))
    if not base.get("present") and speaker is None and controller is None:
        return {"present": False}
    nodes_total = (inv.get("nodes") or {}).get("count") or len((inv.get("nodes") or {}).get("nodes") or [])

    def wl(d, role):
        if not d:
            return {"present": False}
        sp, st = d.get("spec") or {}, d.get("status") or {}
        c0 = _container(d, role)
        return {
            "present": True,
            "namespace": d["metadata"]["namespace"],
            "name": d["metadata"]["name"],
            "version": _ver(c0.get("image")),
            "desired": st.get("desiredNumberScheduled", sp.get("replicas")),
            "ready": st.get("numberReady", st.get("readyReplicas")) or 0,
            "args": [str(a) for a in (c0.get("args") or [])],
        }

    sp_, ct_ = wl(speaker, "speaker"), wl(controller, "controller")
    ns = sp_.get("namespace") or ct_.get("namespace") or "metallb-system"
    webhooks = [{"name": h.get("name"), "failure_policy": h.get("failurePolicy")} for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io") if "metallb" in w["metadata"]["name"] for h in w.get("webhooks") or []]
    bgp_peers = objects(snap, "bgppeers.metallb.io")
    mode = "bgp" if bgp_peers else ("layer2" if objects(snap, "l2advertisements.metallb.io") else None)
    # --- what the speaker can be asked: an https metrics port (the step skipped and says why), or a version with nothing else (a disabled port, `--port=0`, speaker/main.go:99@v0.16.2, leaves no port to find)
    version = sp_.get("version") or ct_.get("version")
    step = _step(snap)
    https_only_version = (versions.triple(version) or (0, 0, 0)) >= HTTPS_ONLY_SINCE
    tls_only = https_only_version or bool(step.get("skipped") and (step.get("target") or {}).get("skip"))
    texts = _metric_texts(snap)
    base["l2"] = _l2(snap, base["services"], [n["name"] for n in (inv.get("nodes") or {}).get("nodes") or []], texts, step, tls_only, https_only_version)
    # --- speaker metrics
    per_pod = {}
    for pod, text in texts.items():
        pm = _parse_prom(text)
        s = pm["single"]
        per_pod[pod] = {
            "config_loaded": s.get("metallb_k8s_client_config_loaded_bool"),
            "config_stale": s.get("metallb_k8s_client_config_stale_bool"),
            "update_errors": int(s.get("metallb_k8s_client_update_errors_total", 0)),
            "updates": int(s.get("metallb_k8s_client_updates_total", 0)),
            "arp_requests": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_requests_received", [])),
            "arp_responses": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_responses_sent", [])),
            "gratuitous": sum(int(v) for _, v in pm["labeled"].get("metallb_layer2_gratuitous_sent", [])),
            "bgp_sessions_up": sum(int(v) for _, v in pm["labeled"].get("metallb_bgp_session_up", [])),
            "bgp_sessions": len(pm["labeled"].get("metallb_bgp_session_up", [])),
            "announced": sum(1 for _, v in pm["labeled"].get("metallb_speaker_announced", []) if v >= 1),
        }
    l2 = base["l2"]
    states = _config_states(snap)
    judged = [s for s in states if s["result"] in ("Valid", "Invalid")]
    # With some speakers unread, their ConfigurationState answers for them; a speaker neither source answers for is not reported. An Invalid state counts whichever source was read: the answer is in the snapshot.
    unread = l2.get("speakers_unreadable") if texts else []
    answered = {s["node"] for s in judged if s["component"] == "speaker"}
    no_answer = [e["pod"] for e in unread or [] if e["node"] not in answered]
    # In FRR mode the session gauge is the frr-metrics sidecar's, the speaker registers it only in native mode (internal/bgp/native/stats.go:51@v0.16.2): peers with no series read is unknown, not 0 sessions up
    bgp_unread = bool(texts and bgp_peers and not any(v["bgp_sessions"] for v in per_pod.values()))
    counters = {key: (sum(v[field] for v in per_pod.values()) if texts else None) for key, field in COUNTERS.items()}
    if bgp_unread:
        counters.update(bgp_sessions=None, bgp_sessions_up=None)
        for v in per_pod.values():
            v.update(bgp_sessions=None, bgp_sessions_up=None)
    # Where this DaemonSet can run answers "are speakers missing", whatever keeps it off a node: a selector, required affinity, a taint it does not tolerate, an OS. A cordoned node counts as not eligible, which only makes the comparison lenient.
    nodes = objects(snap, "nodes")
    template = ((speaker or {}).get("spec") or {}).get("template", {}).get("spec") or {}
    eligible = len(eligible_nodes(template, nodes)) if speaker and nodes else None
    summary = {
        "present": True,
        "mode": mode,
        "version": version,
        "namespace": ns,
        "speaker_desired": sp_.get("desired"),
        "speaker_ready": sp_.get("ready"),
        "speaker_all_nodes": (sp_.get("ready") or 0) >= nodes_total if sp_.get("present") else None,
        "speaker_eligible": eligible,
        "speakers_pinned": eligible is not None and eligible < nodes_total,  # kept off some nodes on purpose: fewer speakers than nodes is the design, as L2Advertisement nodeSelectors are for leaders
        "nodes_total": nodes_total,
        "controller_replicas": ct_.get("desired"),
        "controller_ready": ct_.get("ready"),
        "pools": len(base.get("pools") or []),
        "total_ips": base.get("total_ips"),
        "used": base.get("used"),
        "free": base.get("free"),
        "pending": [f"{s['namespace']}/{s['name']}" for s in base.get("pending") or []],
        "lb_services": len(base.get("services") or []),
        "lb_services_other_class": base.get("other_class_services") or 0,
        "l2_available": l2.get("available"),
        "speakers_read": len(texts),
        "speakers_unreadable": l2.get("speakers_unreadable") or [],
        "leader_node": l2.get("leader_node"),
        "leader_share": l2.get("leader_share"),
        "pinned_by_selector": l2.get("pinned_by_selector"),
        "config_read": bool(texts or judged),
        "config_source": ("metrics and configurationstates" if unread and judged else "metrics") if texts else ("configurationstates" if judged else None),
        "config_stale_pods": [p for p, v in per_pod.items() if v["config_stale"] == 1 or v["config_loaded"] == 0] + [s["name"] for s in judged if s["result"] == "Invalid"],
        "config_errors": sorted({s["error"] for s in judged if s["error"]}),
        "config_not_reported": no_answer if texts else (_not_reported(states, sp_.get("desired"), ct_.get("desired")) if judged else [s["name"] for s in states]),
        "update_errors_read": bool(texts),
        **counters,  # null when not read: a counter nobody read is not a measured zero
        "bgp_peers": len(bgp_peers),
        "webhooks_fail": [w["name"] for w in webhooks if w["failure_policy"] == "Fail"],
        "webhooks": len(webhooks),
        "metrics_available": bool(texts),
        "metrics_tls_only": tls_only,
        "metrics_not_read": METRICS_NOT_READ if not texts else (["metallb_bgp_session_up"] if bgp_unread else []),
    }
    return {
        "present": True,
        "speaker": sp_,
        "controller": ct_,
        "webhooks": webhooks,
        "pools": base,
        "l2": l2,
        "speaker_metrics": per_pod,
        "config_states": states,
        "summary": summary,
        "note": "L2 leaders and config state come from the speaker metrics when read (pod proxy or node curl, metrics/pod/metallb-speaker), else from ServiceL2Status, ServiceBGPStatus and ConfigurationState. The webhook only blocks creation of MetalLB CRs (pools, advertisements), not ordinary Services",
    }

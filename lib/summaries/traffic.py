"""Traffic area summary.

Inputs: objects/ingresses, services, endpointslices, targetgroupbindings (elbv2), deployments, statefulsets, daemonsets, aws/alb-metrics.json (lib/collection/albmetrics.py),
metrics/pod_network_rx_bytes_1h·pod_ready_ratio_24h·ingress_nginx_*·coredns_*·endpoint_not_ready_addresses, events.json(Unhealthy).

Output is the `traffic` section of summary.json: ingresses (per Ingress: backends, TLS, timeouts, auth hints, LTE metrics), alb (LBs, target groups, 24h totals, unhealthy targets), nginx, exposure (externally exposed endpoints),
lb_services, pod_skew (traffic skew between pods of a workload), readiness (24h Ready ratio, Unhealthy events), coredns, endpoints_not_ready. Shape is documented in SKILL.md.
"""

from __future__ import annotations

import contextlib
import ipaddress
import re
from collections import Counter, defaultdict
from pathlib import Path

from ..foundations import versions as _versions  # `versions` is a local name in this module
from ..foundations.snapshot import event_count, load_json, metric_doc, metric_rows, objects
from ..foundations.workload import workload_of

ADMIN_HOST_RE = re.compile(r"(^|[.-])(admin|grafana|argocd|argo|deploy|kibana|prometheus|alertmanager|minio|registry|pgadmin|phpmyadmin|console|dashboard|jenkins|vault|keycloak|portainer|longhorn|traefik)([.-]|$)", re.IGNORECASE)
DB_PORTS = {5432, 3306, 6379, 27017, 9200, 9300, 5672, 9092, 9094, 11211, 7687, 2379, 1433, 1521, 8086, 9000}
AUTH_ANN = (
    "alb.ingress.kubernetes.io/auth-type",
    "nginx.ingress.kubernetes.io/auth-url",
    "nginx.ingress.kubernetes.io/auth-type",
    "nginx.ingress.kubernetes.io/auth-tls-secret",
    "nginx.ingress.kubernetes.io/whitelist-source-range",
    "nginx.ingress.kubernetes.io/allowlist-source-range",  # the current name; whitelist-source-range is its deprecated alias (kubernetes/ingress-nginx internal/ingress/annotations/ipallowlist/main.go:34-35@controller-v1.12.1) (#124 K3-3)
    "nginx.ingress.kubernetes.io/auth-signin",
    "traefik.ingress.kubernetes.io/router.middlewares",
    "ingress.kubernetes.io/auth-type",
    "alb.ingress.kubernetes.io/inbound-cidrs",
)


def _selector_match(sel: dict, labels: dict) -> bool:
    return bool(sel) and all(labels.get(k) == v for k, v in sel.items())


class _Objects:
    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        self.prod = set(((inv or {}).get("namespaces") or {}).get("prod_like") or [])
        self.platform = ((inv or {}).get("cluster") or {}).get("platform")
        self.services = {(s["metadata"]["namespace"], s["metadata"]["name"]): s for s in objects(snap, "services")}
        self.workloads = []
        for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet")):
            for o in objects(snap, stem):
                tpl = (o.get("spec") or {}).get("template") or {}
                self.workloads.append(
                    {
                        "kind": kind,
                        "namespace": o["metadata"]["namespace"],
                        "name": o["metadata"]["name"],
                        "labels": (tpl.get("metadata") or {}).get("labels") or {},
                        "grace_s": (tpl.get("spec") or {}).get("terminationGracePeriodSeconds", 30),
                        "replicas": (o.get("spec") or {}).get("replicas"),
                        "prestop": any((c.get("lifecycle") or {}).get("preStop") for c in (tpl.get("spec") or {}).get("containers") or []),
                    }
                )
        self.tgb = {}
        for t in objects(snap, "targetgroupbindings.elbv2.k8s.aws"):
            sp = t.get("spec") or {}
            rec = {"namespace": t["metadata"]["namespace"], "service": (sp.get("serviceRef") or {}).get("name"), "port": (sp.get("serviceRef") or {}).get("port"), "target_type": sp.get("targetType")}
            # `spec.targetGroupARN` is optional from aws-load-balancer-controller 3.0.0, where `spec.targetGroupName` may name the group instead and the controller never writes the ARN back
            # (kubernetes-sigs/aws-load-balancer-controller apis/elbv2/v1beta1/targetgroupbinding_types.go:129,133@v3.6.2); keyed by both (#124 K3-4)
            if sp.get("targetGroupARN"):
                self.tgb[sp["targetGroupARN"]] = rec
            if sp.get("targetGroupName"):
                self.tgb["name:" + sp["targetGroupName"]] = rec
        self.endpoints_ready = {}
        for es in objects(snap, "endpointslices.discovery.k8s.io"):
            svc = (es["metadata"].get("labels") or {}).get("kubernetes.io/service-name")
            if not svc:
                continue
            key = (es["metadata"]["namespace"], svc)
            eps = es.get("endpoints") or []
            r = self.endpoints_ready.setdefault(key, {"ready": 0, "not_ready": 0})
            for e in eps:
                if (e.get("conditions") or {}).get("ready", True):
                    r["ready"] += 1
                else:
                    r["not_ready"] += 1

    def backend_workloads(self, ns: str, svc_name: str) -> list[dict]:
        s = self.services.get((ns, svc_name))
        if not s:
            return []
        sel = (s.get("spec") or {}).get("selector") or {}
        return [w for w in self.workloads if w["namespace"] == ns and _selector_match(sel, w["labels"])]


OPEN_CIDRS = ("0.0.0.0/0", "::/0")


def _prefix_len(cidr: str) -> int | None:
    """Prefix length of a CIDR, None when the string is not one. A hand-typed loadBalancerSourceRanges entry can be anything."""
    try:
        return ipaddress.ip_network(cidr, strict=False).prefixlen
    except ValueError:
        return None


def _covers_everything(cidrs: set[str]) -> bool:
    """True when the CIDRs together cover the whole IPv4 or IPv6 space, 0.0.0.0/0 itself or a pair such as 0.0.0.0/1 and 128.0.0.0/1."""
    nets = []
    for c in cidrs:
        with contextlib.suppress(ValueError):
            nets.append(ipaddress.ip_network(c, strict=False))
    for version in (4, 6):
        same = [n for n in nets if n.version == version]
        if same and any(n.prefixlen == 0 for n in ipaddress.collapse_addresses(same)):
            return True
    return False


def _rule_covers(rule: dict, port: int) -> bool:
    """TCP and all-protocol rules only: the listeners this check judges are TCP, so a UDP rule on the same port opens nothing."""
    if rule.get("protocol") == "-1":
        return True
    if str(rule.get("protocol")).lower() not in ("tcp", "6"):
        return False
    lo, hi = rule.get("from_port"), rule.get("to_port")
    return lo is not None and hi is not None and lo <= port <= hi


def sg_exposure(lb: dict | None, ports: list[int]) -> dict:
    """What the load balancer's security groups let in on these listener ports, as counts and prefix lengths, never the addresses themselves.
    `open`: some port is reachable from everywhere, through 0.0.0.0/0, ::/0 or CIDRs that together cover the whole space. `allow-list`: every reachable port is limited to listed CIDRs,
    prefix lists or security groups. `blocked`: no inbound rule covers any of the ports. `no-security-group`: the load balancer has none, so only the targets' groups filter it.
    `not-read`: the groups could not be described. `allowed_sources` counts the distinct sources per port, CIDRs, prefix lists and referenced security groups alike; `widest_prefix` is the
    shortest prefix length among the port's CIDRs, so /32 means single addresses and /8 a whole block, and None when a prefix list or a security group reference hides the width; `open_ports` lists the ports open to everyone.
    Pass only the ports that matter for the verdict: for a database exposure, the database ports, so an open 443 next to an allow-listed 5432 does not make the row open. No port at all is None, not applicable."""
    empty = {"allowed_sources": {}, "widest_prefix": {}, "open_ports": []}
    ports = [p for p in ports if isinstance(p, int)]
    if not lb or not ports:
        return {"sg_exposure": None, **empty}
    if not lb.get("security_groups"):
        return {"sg_exposure": "no-security-group", **empty}
    if not lb.get("security_groups_read"):
        return {"sg_exposure": "not-read", **empty}
    allowed: dict[str, int] = {}
    widest: dict[str, int | None] = {}
    open_ports: list[int] = []
    for port in ports:
        cidrs: set[str] = set()
        hidden = 0
        for r in lb.get("_inbound_rules") or lb.get("inbound_rules") or []:  # `inbound_rules` as a fallback only for tests that build the row by hand; the summary row carries prefix lengths, not addresses
            if _rule_covers(r, port):
                cidrs |= set(r.get("cidrs") or []) | set(r.get("cidrs_v6") or [])
                hidden += len(r.get("prefix_lists") or []) + len(r.get("security_groups") or [])
        if cidrs & set(OPEN_CIDRS) or _covers_everything(cidrs):
            open_ports.append(port)
        allowed[str(port)] = len(cidrs) + hidden
        widest[str(port)] = None if hidden else min((n for n in (_prefix_len(c) for c in cidrs) if n is not None), default=None)
    state = "open" if open_ports else ("allow-list" if any(allowed.values()) else "blocked")
    return {"sg_exposure": state, "allowed_sources": allowed, "widest_prefix": widest, "open_ports": sorted(open_ports)}


def _ranges_exposure(ranges: list[str], ports: list[int]) -> dict:
    """The same shape from a Service's loadBalancerSourceRanges, for a load balancer that has no security group of its own: the controller writes those ranges into the node groups, which the check does not read."""
    cidrs = {str(c) for c in ranges if c and _prefix_len(str(c)) is not None}  # entries that are not a CIDR are ignored
    ports = [p for p in ports if isinstance(p, int)]
    if not cidrs or not ports:
        return {}
    opened = bool(cidrs & set(OPEN_CIDRS)) or _covers_everything(cidrs)
    widest = min(_prefix_len(c) for c in cidrs)
    return {"sg_exposure": "open" if opened else "allow-list", "allowed_sources": {str(p): len(cidrs) for p in ports}, "widest_prefix": {str(p): widest for p in ports}, "open_ports": ports if opened else []}


def _latest_hour(p95: dict | None, req: dict | None) -> dict:
    """Join the hourly p95 and request series of one target group or load balancer. Returns the request-weighted p95 over the window, the newest hour that carried
    requests with its p95 and request count, and how many hours ago that was relative to the newest request datapoint (0 when it is the latest hour)."""
    ps = {pt["t"]: pt["v"] for pt in (p95 or {}).get("series") or []}
    rs = [(pt["t"], pt["v"]) for pt in (req or {}).get("series") or []]
    if not rs:
        return {"p95_s_weighted": (p95 or {}).get("avg"), "p95_s_last_1h": (p95 or {}).get("last"), "p95_s_last_at": (p95 or {}).get("last_at"), "requests_last_1h": None, "hours_since_requests": None}
    total = sum(v for _, v in rs)
    weighted = round(sum(ps[t] * v for t, v in rs if t in ps) / sum(v for t, v in rs if t in ps), 4) if total and any(t in ps for t, v in rs if v) else (p95 or {}).get("avg")
    newest = rs[0][0]
    hours_since = None
    last_t = last_v = last_req = None
    for i, (t, v) in enumerate(rs):  # newest first
        if v > 0:
            last_t, last_req = t, v
            last_v = ps.get(t)
            hours_since = i
            break
    return {
        "p95_s_weighted": weighted,
        "p95_s_last_1h": last_v if last_v is not None else (p95 or {}).get("last"),
        "p95_s_last_at": last_t or (p95 or {}).get("last_at"),
        "requests_last_1h": last_req if last_req is not None else 0,
        "hours_since_requests": hours_since,
        "newest_hour": newest,
    }


def _alb(snap: Path, objs: _Objects) -> dict:
    d = load_json(snap / "aws" / "alb-metrics.json")
    if not d:
        return {"available": False, "note": "aws/alb-metrics.json missing (not EKS, or not collected yet)"}
    lbm, tgm = (d.get("metrics") or {}).get("lb", {}), (d.get("metrics") or {}).get("tg", {})
    lbs = []
    for lb in d.get("lbs") or []:
        m = lbm.get(lb["dim"], {})

        def g(k, f="sum"):
            return (m.get(k) or {}).get(f)

        row = {**{k: lb.get(k) for k in ("name", "dns", "type", "scheme", "idle_timeout_s", "deletion_protection", "access_logs", "drop_invalid_headers", "azs", "created")}, "target_groups": len(lb.get("target_groups") or [])}
        row["security_groups"] = lb.get("security_groups") or []
        row["listeners"] = lb.get("listeners") or []
        sgmap = d.get("security_groups") or {}
        row["_inbound_rules"] = [r for g in row["security_groups"] for r in (sgmap.get(g) or {}).get("inbound") or []]  # with the addresses; dropped before the summary is written
        row["inbound_rules"] = [
            {
                **{k: r.get(k) for k in ("protocol", "from_port", "to_port", "prefix_lists", "security_groups")},
                "cidr_prefixes": sorted(n for n in (_prefix_len(c) for c in r.get("cidrs") or []) if n is not None),
                "cidr_v6_prefixes": sorted(n for n in (_prefix_len(c) for c in r.get("cidrs_v6") or []) if n is not None),
            }
            for r in row["_inbound_rules"]
        ]
        row["security_groups_read"] = (bool(d.get("security_groups_read")) and all(g in sgmap for g in row["security_groups"])) if row["security_groups"] else None
        if lb.get("type") == "application":
            req = g("RequestCount_Sum") or 0
            row.update(
                {
                    "requests_24h": req,
                    "elb_5xx_24h": g("HTTPCode_ELB_5XX_Count_Sum") or 0,
                    "elb_4xx_24h": g("HTTPCode_ELB_4XX_Count_Sum") or 0,
                    "target_5xx_24h": g("HTTPCode_Target_5XX_Count_Sum") or 0,
                    "target_4xx_24h": g("HTTPCode_Target_4XX_Count_Sum") or 0,
                    "target_5xx_ratio_24h": round((g("HTTPCode_Target_5XX_Count_Sum") or 0) / req, 5) if req else None,
                    "elb_5xx_ratio_24h": round((g("HTTPCode_ELB_5XX_Count_Sum") or 0) / req, 5) if req else None,
                    "p95_s_max_1h": g("TargetResponseTime_p95", "max"),
                    "p95_s_avg": g("TargetResponseTime_p95", "avg"),
                    **_latest_hour(m.get("TargetResponseTime_p95"), m.get("RequestCount_Sum")),
                    "p99_s_max_1h": g("TargetResponseTime_p99", "max"),
                    "rejected_connections_24h": g("RejectedConnectionCount_Sum") or 0,
                    "requests_peak_1h": g("RequestCount_Sum", "max"),
                }
            )
        else:
            row.update({"processed_bytes_24h": g("ProcessedBytes_Sum"), "active_flows_max": g("ActiveFlowCount_Maximum", "max"), "tcp_elb_resets_24h": g("TCP_ELB_Reset_Count_Sum"), "tcp_target_resets_24h": g("TCP_Target_Reset_Count_Sum")})
        lbs.append(row)
    tgs = []
    for tg in d.get("target_groups") or []:
        m = tgm.get(tg["dim"], {})

        def g(k, f="sum"):
            return (m.get(k) or {}).get(f)

        b = objs.tgb.get(tg["arn"]) or objs.tgb.get("name:" + str(tg.get("name"))) or {}
        wls = objs.backend_workloads(b.get("namespace"), b.get("service")) if b else []
        req = g("RequestCount_Sum")
        grace = min((w["grace_s"] for w in wls), default=None)
        row = {
            "name": tg["name"],
            "lb": tg["lb"],
            "lb_type": tg["lb_type"],
            "port": tg["port"],
            "protocol": tg["protocol"],
            "target_type": tg["target_type"],
            "namespace": b.get("namespace"),
            "service": b.get("service"),
            "workloads": [f"{w['kind'].lower()}/{w['name']}" for w in wls],
            "health_check": tg.get("health_check"),
            "deregistration_delay_s": tg.get("deregistration_delay_s"),
            "slow_start_s": tg.get("slow_start_s"),
            "backend_grace_s": grace,
            "backend_prestop": any(w["prestop"] for w in wls) if wls else None,
            "targets_total": tg.get("targets_total"),
            "targets_healthy": tg.get("targets_healthy"),
            "targets_unhealthy": tg.get("targets_unhealthy") or [],
            "unhealthy_reasons": dict(Counter(f"{t.get('reason')}: {t.get('description')}" for t in tg.get("targets_unhealthy") or [])),
            "requests_24h": req,
            "target_5xx_24h": g("HTTPCode_Target_5XX_Count_Sum"),
            "target_4xx_24h": g("HTTPCode_Target_4XX_Count_Sum"),
            "target_5xx_ratio_24h": round((g("HTTPCode_Target_5XX_Count_Sum") or 0) / req, 5) if req else None,
            "p95_s_max_1h": g("TargetResponseTime_p95", "max"),
            "p95_s_avg": g("TargetResponseTime_p95", "avg"),
            **_latest_hour(m.get("TargetResponseTime_p95"), m.get("RequestCount_Sum")),
            "unhealthy_max_24h": g("UnHealthyHostCount_Maximum", "max"),
            "healthy_min_24h": g("HealthyHostCount_Minimum", "min"),
            "requests_per_target_24h": g("RequestCountPerTarget_Sum"),
        }
        row["target"] = f"{b.get('namespace')}/{b.get('service')}" if b else tg["name"]
        row["prod"] = (b.get("namespace") in objs.prod) if b else False
        tgs.append(row)
    return {
        "available": True,
        "source": "aws/alb-metrics.json",
        "window_hours": d.get("window_hours"),
        "lbs": lbs,
        "target_groups": tgs,
        "errors": d.get("errors") or [],
        "unhealthy_target_groups": [t for t in tgs if t["targets_unhealthy"] or (t["unhealthy_max_24h"] or 0) > 0],
        "target_groups_without_tgb": [t["name"] for t in tgs if not t["namespace"]],
        "target_groups_no_requests_24h": [t["target"] for t in tgs if t["lb_type"] == "application" and not t["requests_24h"]],
        "internet_facing_nlbs": [ln["name"] for ln in lbs if ln["type"] == "network" and ln["scheme"] == "internet-facing"],
    }


def _ingresses(snap: Path, objs: _Objects, alb: dict) -> list[dict]:
    nginx_rps = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in metric_rows(snap, "ingress_nginx_rps_1h")}
    nginx_5xx = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in metric_rows(snap, "ingress_nginx_5xx_ratio_1h")}
    nginx_p95 = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in metric_rows(snap, "ingress_nginx_p95_1h")}
    tg_by_svc: dict[tuple, list] = defaultdict(list)
    for t in alb.get("target_groups") or []:
        if t.get("namespace"):
            tg_by_svc[(t["namespace"], t["service"])].append(t)
    lb_by_name = {ln["name"]: ln for ln in (alb.get("lbs") or [])}
    rows = []
    for ing in objects(snap, "ingresses.networking.k8s.io"):
        md, sp = ing["metadata"], ing.get("spec") or {}
        ns, name = md["namespace"], md["name"]
        ann = md.get("annotations") or {}
        cls = sp.get("ingressClassName") or ann.get("kubernetes.io/ingress.class")
        hosts = [r.get("host") for r in sp.get("rules") or [] if r.get("host")]
        services = sorted({((p.get("backend") or {}).get("service") or {}).get("name") for r in sp.get("rules") or [] for p in ((r.get("http") or {}).get("paths") or []) if (p.get("backend") or {}).get("service")})
        tls = bool(sp.get("tls")) or bool(ann.get("alb.ingress.kubernetes.io/certificate-arn")) or ("443" in (ann.get("alb.ingress.kubernetes.io/listen-ports") or ""))
        auth = {k.split("/")[-1]: v[:80] for k, v in ann.items() if k in AUTH_ANN}
        timeouts = {k.split("/")[-1]: v for k, v in ann.items() if "timeout" in k}
        lb_attrs = ann.get("alb.ingress.kubernetes.io/load-balancer-attributes") or ""
        m = re.search(r"idle_timeout\.timeout_seconds=(\d+)", lb_attrs)
        if m:
            timeouts["alb_idle_timeout_s(annotation)"] = int(m.group(1))
        scheme = ann.get("alb.ingress.kubernetes.io/scheme")
        lb_hosts = [i.get("hostname") or i.get("ip") for i in ((ing.get("status") or {}).get("loadBalancer") or {}).get("ingress") or []]
        alb_lb = next((ln for ln in lb_by_name.values() if ln.get("dns") in lb_hosts), None)
        if alb_lb and alb_lb.get("idle_timeout_s") is not None:
            timeouts["alb_idle_timeout_s"] = alb_lb["idle_timeout_s"]
            scheme = scheme or alb_lb.get("scheme")
        if not scheme:
            scheme = "lan" if any(h and re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", str(h)) for h in lb_hosts) else ("internet-facing" if lb_hosts else "unknown")
        wls = sorted({f"{w['kind'].lower()}/{w['name']}" for s in services for w in objs.backend_workloads(ns, s)})
        tgs = [t for s in services for t in tg_by_svc.get((ns, s), [])]
        metrics = {"source": None}
        if tgs:
            req = sum(t.get("requests_24h") or 0 for t in tgs)
            e5 = sum(t.get("target_5xx_24h") or 0 for t in tgs)
            busiest = max(tgs, key=lambda t: t.get("requests_24h") or 0)  # the latest hour is read from the target group that carries the traffic
            metrics = {
                "source": "alb-cloudwatch",
                "window": "24h",
                "requests": req,
                "requests_24h_equiv": req,
                "rps_avg": round(req / 86400, 3),
                "errors_5xx": e5,
                "errors_ratio": round(e5 / req, 5) if req else None,
                "p95_s_max_1h": max((t.get("p95_s_max_1h") or 0) for t in tgs) or None,
                "p95_s_avg": max((t.get("p95_s_avg") or 0) for t in tgs) or None,
                "p95_s_weighted": max((t.get("p95_s_weighted") or 0) for t in tgs) or None,
                "p95_s_last_1h": busiest.get("p95_s_last_1h"),
                "p95_s_last_at": busiest.get("p95_s_last_at"),
                "requests_last_1h": busiest.get("requests_last_1h"),
                "hours_since_requests": busiest.get("hours_since_requests"),
                "unhealthy_max_24h": max((t.get("unhealthy_max_24h") or 0) for t in tgs),
                "unhealthy_now": sum(len(t.get("targets_unhealthy") or []) for t in tgs),
                "target_groups": [t["name"] for t in tgs],
            }
        elif (ns, name) in nginx_rps or (ns, name) in nginx_5xx:
            rps = nginx_rps.get((ns, name))
            metrics = {
                "source": "ingress-nginx",
                "window": "1h",
                "rps_avg": round(rps, 3) if rps is not None else None,
                "requests": round(rps * 3600) if rps else None,
                "requests_24h_equiv": round(rps * 86400) if rps else None,  # the same request rate over the 24-hour window the ALB counts use, so one threshold serves both sources
                "errors_ratio": round(nginx_5xx.get((ns, name), 0), 5),
                "errors_5xx": round(rps * 3600 * nginx_5xx.get((ns, name), 0)) if rps else None,
                "p95_s_avg": nginx_p95.get((ns, name)),
                "p95_s_weighted": nginx_p95.get((ns, name)),
                "p95_s_max_1h": nginx_p95.get((ns, name)),
                "p95_s_last_1h": nginx_p95.get((ns, name)),
                "p95_s_last_at": None,
                "requests_last_1h": round(rps * 3600) if rps else None,
                "hours_since_requests": 0 if rps else None,
            }
        ep = [objs.endpoints_ready.get((ns, s)) for s in services]
        rows.append(
            {
                "namespace": ns,
                "name": name,
                "target": f"{ns}/{name}",
                "class": cls,
                "hosts": hosts,
                "services": services,
                "workloads": wls,
                "alb_group": ann.get("alb.ingress.kubernetes.io/group.name"),
                "tls": tls,
                "scheme": scheme,
                "lb": lb_hosts[:2],
                "auth_hint": auth,
                "has_auth_hint": bool(auth),
                "admin_like": any(ADMIN_HOST_RE.search(h or "") for h in hosts),
                "timeouts": timeouts,
                "healthcheck_path": ann.get("alb.ingress.kubernetes.io/healthcheck-path"),
                "success_codes": ann.get("alb.ingress.kubernetes.io/success-codes"),
                "rate_limit": {k.split("/")[-1]: v for k, v in ann.items() if "limit-" in k} or None,
                "body_size": ann.get("nginx.ingress.kubernetes.io/proxy-body-size"),
                "endpoints_ready": sum((e or {}).get("ready", 0) for e in ep),
                "endpoints_not_ready": sum((e or {}).get("not_ready", 0) for e in ep),
                "prod": ns in objs.prod,
                "metrics": metrics,
                "metrics_read": metrics.get("source") is not None,  # ALB CloudWatch metrics or the ingress controller's series reached this Ingress; without them its traffic checks skip (#141)
            }
        )
    rows.sort(key=lambda r: (-(r["metrics"].get("errors_ratio") or 0), -(r["metrics"].get("requests") or 0)))
    return rows


def _exposure(snap: Path, objs: _Objects, ingresses: list[dict], alb: dict) -> list[dict]:
    rows = []
    for r in ingresses:
        rows.append(
            {
                "type": "ingress",
                "namespace": r["namespace"],
                "name": r["name"],
                "target": f"ingress/{r['namespace']}/{r['name']}",
                "hosts": r["hosts"],
                "ports": [443 if r["tls"] else 80],
                "scheme": r["scheme"],
                "tls": r["tls"],
                "auth_hint": r["auth_hint"],
                "has_auth_hint": r["has_auth_hint"],
                "admin_like": r["admin_like"],
                "db_port": False,
                "prod": r["prod"],
                "note": "no auth annotation; verify manually whether the app has its own login" if (r["admin_like"] and not r["has_auth_hint"]) else None,
            }
        )
    lb_dns = {ln.get("dns"): ln for ln in (alb.get("lbs") or [])}
    for (ns, name), s in objs.services.items():
        sp = s.get("spec") or {}
        t = sp.get("type")
        if t not in ("LoadBalancer", "NodePort"):
            continue
        ann = s["metadata"].get("annotations") or {}
        ports = [p.get("port") for p in sp.get("ports") or []]
        node_ports = [p.get("nodePort") for p in sp.get("ports") or [] if p.get("nodePort")]
        tports = [p.get("targetPort") for p in sp.get("ports") or []]
        db = any((p in DB_PORTS) or (isinstance(tp, int) and tp in DB_PORTS) for p, tp in zip(ports, tports, strict=False))
        ing = ((s.get("status") or {}).get("loadBalancer") or {}).get("ingress") or []
        addrs = [i.get("hostname") or i.get("ip") for i in ing]
        scheme = ann.get("service.beta.kubernetes.io/aws-load-balancer-scheme")
        if not scheme and t == "LoadBalancer":
            ln = next((lb_dns[a] for a in addrs if a in lb_dns), None)
            scheme = ln.get("scheme") if ln else ("lan" if any(re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", str(a)) for a in addrs) else ("internet-facing" if addrs else "unknown"))
        if t == "NodePort":
            scheme = "node-ip (all node interfaces)"
        lb_row = next((lb_dns[a] for a in addrs if a in lb_dns), None) if t == "LoadBalancer" else None
        judged = [p for p, tp in zip(ports, tports, strict=False) if isinstance(p, int) and (not db or p in DB_PORTS or (isinstance(tp, int) and tp in DB_PORTS))]
        sg = sg_exposure(lb_row, judged)
        sg_from_ranges = False
        if t == "LoadBalancer" and lb_row is None and judged:
            if alb.get("lbs"):
                sg["sg_exposure"] = "unmatched"  # the Service's address is among no described load balancer: another account, a stale status, or alb-metrics older than the Service
            elif alb.get("available") or objs.platform == "eks":
                sg["sg_exposure"] = "not-read"  # nothing was described: the call failed, or the file is missing on an EKS run
        if sg.get("sg_exposure") == "no-security-group" and sp.get("loadBalancerSourceRanges"):
            # an NLB without groups of its own: the controller wrote the Service's sourceRanges into the node groups, which are not read; the ranges are the best statement of the AWS-layer control
            ranged = _ranges_exposure(sp.get("loadBalancerSourceRanges") or [], judged)
            if ranged:
                sg = {**sg, **ranged}
                sg_from_ranges = True
        rows.append(
            {
                "type": t.lower(),
                "namespace": ns,
                "name": name,
                "target": f"{t.lower()}/{ns}/{name}",
                "hosts": addrs[:2],
                "ports": ports,
                "node_ports": node_ports,
                "scheme": scheme,
                "tls": False,
                "auth_hint": {},
                "has_auth_hint": False,
                "admin_like": bool(ADMIN_HOST_RE.search(name)),
                "db_port": db,
                "prod": ns in objs.prod,
                "external_traffic_policy": sp.get("externalTrafficPolicy"),
                "source_ranges": sp.get("loadBalancerSourceRanges"),
                **sg,
                "note": _db_note(db, scheme, sg["sg_exposure"], from_ranges=sg_from_ranges),
            }
        )
    # LBs created outside Kubernetes (no TGB) also go in the exposure list (e.g. a shared DB NLB)
    for ln in alb.get("lbs") or []:
        if ln["type"] == "network" and ln.get("scheme") == "internet-facing" and not any(ln.get("dns") in (r.get("hosts") or []) for r in rows):
            tgs = [t for t in alb.get("target_groups") or [] if t["lb"] == ln["name"]]
            bound = sorted({f"{t['namespace']}/{t['service']}" for t in tgs if t.get("namespace")})
            listener_ports = sorted({li["port"] for li in ln.get("listeners") or [] if isinstance(li.get("port"), int)})
            tg_ports = sorted({t["port"] for t in tgs if isinstance(t.get("port"), int)})
            nlb_ports = listener_ports or tg_ports  # the security group filters the listener port; the target group port is what the pod listens on
            tg_port_by_name = {t["name"]: t.get("port") for t in tgs}
            db_listeners = sorted({li["port"] for li in ln.get("listeners") or [] if isinstance(li.get("port"), int) and (li["port"] in DB_PORTS or any(tg_port_by_name.get(n) in DB_PORTS for n in li.get("target_groups") or []))})
            judged = db_listeners or [p for p in nlb_ports if p in DB_PORTS] or nlb_ports  # only the database listeners decide; a public 443 next to them does not
            sg = sg_exposure(ln, judged)
            db = any(p in DB_PORTS for p in nlb_ports + tg_ports)
            rows.append(
                {
                    "type": "nlb (defined outside the cluster)",
                    "namespace": None,
                    "name": ln["name"],
                    "target": f"nlb/{ln['name']}",
                    "hosts": [ln.get("dns")],
                    "ports": nlb_ports,
                    "scheme": ln["scheme"],
                    "tls": None,
                    "auth_hint": {},
                    "has_auth_hint": False,
                    "admin_like": False,
                    "db_port": db,
                    "prod": any(t.get("prod") for t in tgs) or not bound,
                    "bound_services": bound,
                    "target_group_ports": tg_ports,
                    **sg,
                    "note": (
                        "NLB created outside Kubernetes; "
                        + (
                            f"{len(bound)} TargetGroupBinding{'s bind' if len(bound) != 1 else ' binds'} it to {', '.join(bound[:6])}" + (f" and {len(bound) - 6} more" if len(bound) > 6 else "")
                            if bound
                            else "no TargetGroupBinding, DB inferred from the target group port"
                        )
                        + (". " + _db_note(db, ln["scheme"], sg["sg_exposure"]) if db else "")
                    ),
                }
            )
    return rows


def _db_note(db: bool, scheme, sg_state: str | None, *, from_ranges: bool = False) -> str | None:
    if not (db and scheme and "internal" not in str(scheme)):
        return None
    if from_ranges:
        return {
            "open": "DB port open to the internet by the Service's sourceRanges; the load balancer has no security group of its own",
            "allow-list": "DB port on an external address, limited by the Service's sourceRanges; the load balancer has no security group of its own and the node groups are not read",
        }.get(sg_state)
    return {
        "open": "DB port open to the internet by the security group",
        "no-security-group": "DB port on an external address with no security group on the load balancer; only the targets' security groups filter it, which this check does not read",
        "not-read": "DB port on an external address; the security group could not be read",
        "unmatched": "DB port on an external address; no described load balancer matched the Service's address, so its security group is unknown",
        "allow-list": "DB port on an external address, limited by the security group to listed addresses",
        "blocked": "DB port on an external address, but no inbound rule of the security group covers it",
    }.get(sg_state, "DB port open on an external address")


def _pod_skew(snap: Path, objs: _Objects) -> dict:
    ds = {f"{w['namespace']}/{w['name']}" for w in objs.workloads if w["kind"] == "DaemonSet"}  # DaemonSets are excluded: node size differences show up as skew (node-exporter measured at 20x)
    by_wl: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for lab, v in metric_rows(snap, "pod_network_rx_bytes_1h"):
        ns, pod = lab.get("namespace"), lab.get("pod")
        if ns and pod and workload_of(f"{ns}/{pod}") not in ds:
            by_wl[workload_of(f"{ns}/{pod}")].append((pod, v))
    rows = []
    for wl, pods in by_wl.items():
        if len(pods) < 2:
            continue
        vals = [v for _, v in pods]
        mean = sum(vals) / len(vals)
        if mean < 10_000:  # below 10 KB/s skew is meaningless
            continue
        mx = max(pods, key=lambda x: x[1])
        mn = min(pods, key=lambda x: x[1])
        rows.append(
            {
                "workload": wl,
                "namespace": wl.split("/")[0],
                "pods": len(pods),
                "mean_bytes_s": round(mean),
                "max_pod": mx[0],
                "max_bytes_s": round(mx[1]),
                "min_pod": mn[0],
                "min_bytes_s": round(mn[1]),
                "skew_ratio": round(mx[1] / mean, 2) if mean else None,
                "max_over_min": round(mx[1] / mn[1], 1) if mn[1] else None,
                "prod": wl.split("/")[0] in objs.prod,
            }
        )
    rows.sort(key=lambda r: -(r["skew_ratio"] or 0))
    return {"available": metric_doc(snap, "pod_network_rx_bytes_1h") is not None, "workloads_measured": len(rows), "rows": rows[:30]}


def _readiness(snap: Path, objs: _Objects) -> dict:
    unhealthy: Counter = Counter()
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        if e.get("reason") == "Unhealthy":
            io = e.get("involvedObject") or {}
            if io.get("kind") == "Pod":
                unhealthy[workload_of(f"{io.get('namespace', '')}/{io.get('name', '')}")] += event_count(e)
    by_wl: dict[str, list] = defaultdict(list)
    for lab, v in metric_rows(snap, "pod_ready_ratio_24h"):
        ns, pod = lab.get("namespace"), lab.get("pod")
        if ns and pod:
            by_wl[workload_of(f"{ns}/{pod}")].append((pod, v))
    rows = []
    for wl, pods in by_wl.items():
        worst = min(pods, key=lambda x: x[1])
        rows.append(
            {
                "workload": wl,
                "namespace": wl.split("/")[0],
                "pods_below_99": len(pods),
                "min_ready_ratio_24h": round(worst[1], 4),
                "worst_pod": worst[0],
                "not_ready_minutes_24h": round((1 - worst[1]) * 1440),
                "unhealthy_events": unhealthy.get(wl, 0),
                "prod": wl.split("/")[0] in objs.prod,
            }
        )
    for wl, n in unhealthy.items():
        if wl not in by_wl:
            rows.append({"workload": wl, "namespace": wl.split("/")[0], "pods_below_99": 0, "min_ready_ratio_24h": None, "worst_pod": None, "not_ready_minutes_24h": None, "unhealthy_events": n, "prod": wl.split("/")[0] in objs.prod})
    rows.sort(key=lambda r: (r["min_ready_ratio_24h"] if r["min_ready_ratio_24h"] is not None else 1, -r["unhealthy_events"]))
    not_ready_eps = [{"namespace": ln.get("namespace"), "endpoint": ln.get("endpoint"), "not_ready_addresses": int(v)} for ln, v in metric_rows(snap, "endpoint_not_ready_addresses")]
    available = bool((metric_doc(snap, "pod_ready_ratio_24h") or {}).get("ok"))
    return {
        "available": available,
        "rows": rows[:40] if available else None,  # None, not []: without the readiness ratio the rows judge nothing (#141)
        "skip_reason": None if available else "pod readiness ratio not read (metrics/pod_ready_ratio_24h.json missing or failed)",
        "unhealthy_events_total": sum(unhealthy.values()),
        "endpoints_not_ready": not_ready_eps,
    }


def _coredns(snap: Path) -> dict:
    sf = metric_rows(snap, "coredns_servfail_ratio_1h")
    p99 = metric_rows(snap, "coredns_p99_1h")
    return {"available": bool(sf or p99), "servfail_ratio_1h": round(sf[0][1], 5) if sf else None, "p99_s_1h": round(p99[0][1], 4) if p99 else None}


def _alb_groups(ingresses: list[dict]) -> list[dict]:
    """Groups of Ingresses sharing one ALB via alb.ingress.kubernetes.io/group.name. One group = one ALB = 100 listener rules, one security group, one access log.
    If prod and dev share a group, a rule or certificate mistake in dev becomes a change to the prod ALB."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in ingresses:
        if r.get("alb_group"):
            groups[r["alb_group"]].append(r)
    out = []
    for g, lst in sorted(groups.items()):
        nss = sorted({r["namespace"] for r in lst})
        kinds = sorted({"prod" if r["prod"] else ("dev" if r["namespace"].startswith(("dev-", "dev", "stg", "staging")) or "-dev" in r["namespace"] else "other") for r in lst})
        out.append(
            {
                "group": g,
                "target": f"alb-group/{g}",
                "ingresses": [r["target"] for r in lst],
                "ingress_count": len(lst),
                "namespaces": nss,
                "namespace_count": len(nss),
                "kinds": kinds,
                "mixed_prod_nonprod": "prod" in kinds and len(kinds) > 1,
                "hosts": sum(len(r.get("hosts") or []) for r in lst),
                "prod": any(r["prod"] for r in lst),
                "lb": next((r["lb"] for r in lst if r.get("lb")), []),
            }
        )
    return out


# ---------- ingress-nginx controller ----------
# The project retired: best-effort maintenance ended in March 2026, the repository was archived on 2026-03-24, and no further release or security fix
# will come. IngressNightmare (CVE-2025-1974, CVSS 9.8, with four more CVEs, March 2025) is fixed in 1.12.1 and 1.11.5: below that, any pod that can reach the
# admission webhook can run code in the controller and read every Secret.
NGINX_FIXED = ((1, 11, 5), (1, 12, 1))


def nginx_vulnerable(version: str | None) -> bool | None:
    """True below the IngressNightmare fix of its line: 1.11.x below 1.11.5, everything else below 1.12.1. None when the version is unknown."""
    t = _versions.triple(version)
    if t is None:
        return None
    if t[:2] == (1, 11):
        return t < NGINX_FIXED[0]
    return t < NGINX_FIXED[1]


def _webhook_netpol(snap: Path, rows: list[dict], netpol: dict | None) -> dict:
    """Is the controller's admission webhook port closed to pods by a NetworkPolicy that the CNI enforces? A policy counts when it selects the controller pods
        (matchLabels inside the controller's pod template labels), has Ingress in policyTypes or ingress rules, and every ingress rule that opens port 8443 (or the
        webhook port) names a source: no rule with an empty `from`. Enforcement comes from the security summary written earlier in the same run when present,
    read the way lib/summaries/security.py reads it: the VPC CNI node agent's flag on EKS, kube-router on k3s; a policy mitigates only when enforcement is known to be on."""
    tpl_labels = {}
    for stem in ("deployments", "daemonsets"):
        for o in objects(snap, stem):
            if any(o["metadata"]["namespace"] == r["namespace"] and o["metadata"]["name"] == r["name"] for r in rows):
                tpl_labels[(o["metadata"]["namespace"], o["metadata"]["name"])] = (((o.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}
    policies = []
    for np in objects(snap, "networkpolicies.networking.k8s.io"):
        ns = np["metadata"]["namespace"]
        sel = ((np.get("spec") or {}).get("podSelector") or {}).get("matchLabels") or {}
        targets = [k for k, labels in tpl_labels.items() if k[0] == ns and all(labels.get(a) == b for a, b in sel.items())]
        if not targets:
            continue
        spec = np.get("spec") or {}
        types = spec.get("policyTypes") or (["Ingress"] if "ingress" in spec else [])
        if "Ingress" not in types:
            continue
        open_to_all = False
        for rule in spec.get("ingress") or []:
            ports = [p.get("port") for p in rule.get("ports") or []]
            covers_webhook = not ports or any(str(p) in ("8443", "webhook", "https-webhook") for p in ports)
            everyone = not rule.get("from") or any(
                set(f) == {"namespaceSelector"} and not (f.get("namespaceSelector") or {}).get("matchLabels") and not (f.get("namespaceSelector") or {}).get("matchExpressions") for f in rule.get("from") or []
            )
            if covers_webhook and everyone:
                open_to_all = True  # no source, or every namespace: the webhook stays reachable from any pod
        if not open_to_all:
            policies.append(f"{ns}/{np['metadata']['name']}")
    enforced, how = (netpol or {}).get("enforced"), (netpol or {}).get("enforcement")  # summary.security.networkpolicy, built before this section
    return {"policies": policies, "enforced": enforced, "enforcement": how, "mitigated": bool(policies) and enforced is True}


def _nginx(snap: Path, ingresses: list, inv: dict | None = None, netpol: dict | None = None) -> dict | None:
    """The ingress-nginx controller(s): image version, replicas, and whether the admission webhook is on. None when ingress-nginx is not deployed."""
    rows = []
    for stem, kind in (("deployments", "Deployment"), ("daemonsets", "DaemonSet")):
        for o in objects(snap, stem):
            tpl = ((o.get("spec") or {}).get("template") or {}).get("spec") or {}
            for c in tpl.get("containers") or []:
                img = str(c.get("image") or "")
                if "ingress-nginx/controller" not in img and "nginx-ingress-controller" not in img:
                    continue
                tag = img.split("@")[0].rsplit(":", 1)[-1] if ":" in img.split("@")[0].rsplit("/", 1)[-1] else ""
                m = re.search(r"(?<![\d.])v?(\d+\.\d+\.\d+)(?![\d])", tag)  # the version anywhere in the tag: v1.12.1, nginx-1.2.1-rancher1, 1.11.5-hardened
                st = o.get("status") or {}
                rows.append(
                    {
                        "kind": kind,
                        "namespace": o["metadata"]["namespace"],
                        "name": o["metadata"]["name"],
                        "image": img.split("@")[0],
                        "version": m.group(1) if m else None,
                        "replicas": (o.get("spec") or {}).get("replicas") if kind == "Deployment" else st.get("desiredNumberScheduled"),
                        "ready": st.get("readyReplicas") if kind == "Deployment" else st.get("numberReady"),
                        "webhook_arg": any(str(a).startswith("--validating-webhook") for a in (c.get("args") or []) + (c.get("command") or [])),
                    }
                )
                break
    if not rows:
        return None
    vwc = []
    for w in objects(snap, "validatingwebhookconfigurations.admissionregistration.k8s.io"):
        for h in w.get("webhooks") or []:
            if "nginx.ingress.kubernetes.io" in str(h.get("name") or ""):
                vwc.append({"configuration": w["metadata"]["name"], "failure_policy": h.get("failurePolicy")})
    versions = [r["version"] for r in rows if r["version"]]
    oldest = min(versions, key=lambda v: _versions.triple(v) or (0, 0, 0)) if versions else None
    mitigated = _webhook_netpol(snap, rows, netpol)
    unknown = [f"{r['namespace']}/{r['name']} ({r['image']})" for r in rows if not r["version"]]
    # A controller whose image tag carries no version (digest only, a prefixed tag the regex misses) cannot be cleared: vulnerable stays None for the whole set
    vulnerable = None if unknown else nginx_vulnerable(oldest)
    return {
        "present": True,
        "controllers": rows,
        "version": oldest,
        "versions": sorted(set(versions)),
        "unknown_version_controllers": unknown,
        "admission_webhook": bool(vwc) or any(r["webhook_arg"] for r in rows),
        "admission_webhooks": vwc,
        "webhook_network_policy": mitigated,
        "vulnerable": vulnerable,
        "fixed_versions": ["1.12.1", "1.11.5"],
        "retired": True,
        "retired_note": "ingress-nginx: best-effort maintenance ended March 2026, repository archived 2026-03-24, no further security fixes",
        "metrics_available": any(r["metrics"].get("source") == "ingress-nginx" for r in ingresses),
    }


def analyze(snap: Path, inv: dict | None, security_summary: dict | None = None) -> dict:
    objs = _Objects(snap, inv)
    alb = _alb(snap, objs)
    try:
        alb["covered_services"] = sorted(list(x) for x in alb_covered_services(snap))  # (namespace, service) pairs with ALB request metrics; observability's golden-signal table reads them from this section
    except Exception as e:  # a broken aws/alb-metrics.json must not stop the traffic section; observability shows the error in its table
        alb["covered_services"] = None
        alb["covered_services_error"] = f"{type(e).__name__}: {e}"
    ingresses = _ingresses(snap, objs, alb)
    exposure = _exposure(snap, objs, ingresses, alb)
    for lb in alb.get("lbs") or []:
        lb.pop("_inbound_rules", None)  # the addresses stay in aws/alb-metrics.json
    lb_services = [r for r in exposure if r["type"] == "loadbalancer"]
    return {
        "ingresses": ingresses,
        "ingress_count": len(ingresses),
        "alb_groups": _alb_groups(ingresses),
        "ingress_metrics_source": dict(Counter(r["metrics"].get("source") or "none" for r in ingresses)),
        "alb": alb,
        "nginx": _nginx(snap, ingresses, inv, (security_summary or {}).get("networkpolicy")),
        "exposure": exposure,
        "exposure_counts": dict(Counter(r["type"] for r in exposure)),
        "db_exposed": [r for r in exposure if r["db_port"] and "internal" not in str(r.get("scheme"))],
        "admin_without_auth_hint": [r["target"] for r in exposure if r["admin_like"] and not r["has_auth_hint"]],
        "lb_services": lb_services,
        "lb_external_traffic_local": [r["target"] for r in lb_services if r.get("external_traffic_policy") == "Local"],
        "pod_skew": _pod_skew(snap, objs),
        "readiness": _readiness(snap, objs),
        "coredns": _coredns(snap),
    }


def alb_covered_services(snap: Path) -> set[tuple[str, str]]:
    """For observability golden signals: (namespace, service) pairs that have LTE metrics via ALB CloudWatch."""
    d = load_json(snap / "aws" / "alb-metrics.json")
    if not d:
        return set()
    tgm = (d.get("metrics") or {}).get("tg", {})
    dim_by_name = {tg.get("name"): tg.get("dim") for tg in d.get("target_groups") or [] if tg.get("name")}
    out = set()
    for t in objects(snap, "targetgroupbindings.elbv2.k8s.aws"):
        sp = t.get("spec") or {}
        arn = sp.get("targetGroupARN") or ""
        dim = (arn.split(":", 5)[5] if arn.count(":") >= 5 else arn) or dim_by_name.get(sp.get("targetGroupName"))  # a name-only binding (controller 3.x, #124 K3-4)
        if (tgm.get(dim) or {}).get("RequestCount_Sum", {}).get("points"):
            out.add((t["metadata"]["namespace"], (sp.get("serviceRef") or {}).get("name")))
    return out

"""Traffic area summary.

Inputs: objects/ingresses, services, endpointslices, targetgroupbindings (elbv2), deployments, statefulsets, daemonsets, aws/alb-metrics.json (lib/albmetrics.py),
metrics/pod_network_rx_bytes_1h·pod_ready_ratio_24h·ingress_nginx_*·coredns_*·endpoint_not_ready_addresses, events.json(Unhealthy).

Output is the `traffic` section of summary.json: ingresses (per Ingress: backends, TLS, timeouts, auth hints, LTE metrics), alb (LBs, target groups, 24h totals, unhealthy targets), nginx, exposure (externally exposed endpoints),
lb_services, pod_skew (traffic skew between pods of a workload), readiness (24h Ready ratio, Unhealthy events), coredns, endpoints_not_ready. Shape is documented in SKILL.md.
"""

from __future__ import annotations

import contextlib
import re
from collections import Counter, defaultdict
from pathlib import Path

from .controlplane import workload_of
from .snapshot import load_json, objects

ADMIN_HOST_RE = re.compile(r"(^|[.-])(admin|grafana|argocd|argo|deploy|kibana|prometheus|alertmanager|minio|registry|pgadmin|phpmyadmin|console|dashboard|jenkins|vault|keycloak|portainer|longhorn|traefik)([.-]|$)", re.IGNORECASE)
DB_PORTS = {5432, 3306, 6379, 27017, 9200, 9300, 5672, 9092, 9094, 11211, 7687, 2379, 1433, 1521, 8086, 9000}
AUTH_ANN = (
    "alb.ingress.kubernetes.io/auth-type",
    "nginx.ingress.kubernetes.io/auth-url",
    "nginx.ingress.kubernetes.io/auth-type",
    "nginx.ingress.kubernetes.io/auth-tls-secret",
    "nginx.ingress.kubernetes.io/whitelist-source-range",
    "nginx.ingress.kubernetes.io/auth-signin",
    "traefik.ingress.kubernetes.io/router.middlewares",
    "ingress.kubernetes.io/auth-type",
    "alb.ingress.kubernetes.io/inbound-cidrs",
)


def _metric_rows(snap: Path, qid: str) -> list[tuple[dict, float]]:
    m = load_json(snap / "metrics" / f"{qid}.json")
    out = []
    for s in (m or {}).get("result") or []:
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out.append((s.get("metric") or {}, float(s["value"][1])))
    return out


def _wl(ns: str, pod: str) -> str:
    return workload_of(f"{ns}/{pod}")


def _selector_match(sel: dict, labels: dict) -> bool:
    return bool(sel) and all(labels.get(k) == v for k, v in sel.items())


class _Objects:
    def __init__(self, snap: Path, inv: dict | None):
        self.snap = snap
        self.prod = set(((inv or {}).get("namespaces") or {}).get("prod_like") or [])
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
            self.tgb[sp.get("targetGroupARN")] = {"namespace": t["metadata"]["namespace"], "service": (sp.get("serviceRef") or {}).get("name"), "port": (sp.get("serviceRef") or {}).get("port"), "target_type": sp.get("targetType")}
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

        b = objs.tgb.get(tg["arn"]) or {}
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
    nginx_rps = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in _metric_rows(snap, "ingress_nginx_rps_1h")}
    nginx_5xx = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in _metric_rows(snap, "ingress_nginx_5xx_ratio_1h")}
    nginx_p95 = {(ln.get("exported_namespace") or ln.get("namespace"), ln.get("ingress")): v for ln, v in _metric_rows(snap, "ingress_nginx_p95_1h")}
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
            metrics = {
                "source": "alb-cloudwatch",
                "window": "24h",
                "requests": req,
                "rps_avg": round(req / 86400, 3),
                "errors_5xx": e5,
                "errors_ratio": round(e5 / req, 5) if req else None,
                "p95_s_max_1h": max((t.get("p95_s_max_1h") or 0) for t in tgs) or None,
                "p95_s_avg": max((t.get("p95_s_avg") or 0) for t in tgs) or None,
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
                "errors_ratio": round(nginx_5xx.get((ns, name), 0), 5),
                "p95_s_avg": nginx_p95.get((ns, name)),
                "p95_s_max_1h": nginx_p95.get((ns, name)),
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
                "note": "DB port open on an external address" if db and scheme and "internal" not in str(scheme) else None,
            }
        )
    # LBs created outside Kubernetes (no TGB) also go in the exposure list (e.g. a shared DB NLB)
    for ln in alb.get("lbs") or []:
        if ln["type"] == "network" and ln.get("scheme") == "internet-facing" and not any(ln.get("dns") in (r.get("hosts") or []) for r in rows):
            tgs = [t for t in alb.get("target_groups") or [] if t["lb"] == ln["name"]]
            rows.append(
                {
                    "type": "nlb (defined outside the cluster)",
                    "namespace": None,
                    "name": ln["name"],
                    "target": f"nlb/{ln['name']}",
                    "hosts": [ln.get("dns")],
                    "ports": sorted({t["port"] for t in tgs}),
                    "scheme": ln["scheme"],
                    "tls": None,
                    "auth_hint": {},
                    "has_auth_hint": False,
                    "admin_like": False,
                    "db_port": any(t["port"] in DB_PORTS for t in tgs),
                    "prod": True,
                    "note": "no TargetGroupBinding; NLB created outside Kubernetes (Terraform etc.). DB inferred from the target group port" if any(t["port"] in DB_PORTS for t in tgs) else "no TargetGroupBinding",
                }
            )
    return rows


def _pod_skew(snap: Path, objs: _Objects) -> dict:
    ds = {f"{w['namespace']}/{w['name']}" for w in objs.workloads if w["kind"] == "DaemonSet"}  # DaemonSets are excluded: node size differences show up as skew (node-exporter measured at 20x)
    by_wl: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for lab, v in _metric_rows(snap, "pod_network_rx_bytes_1h"):
        ns, pod = lab.get("namespace"), lab.get("pod")
        if ns and pod and _wl(ns, pod) not in ds:
            by_wl[_wl(ns, pod)].append((pod, v))
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
    return {"available": (snap / "metrics" / "pod_network_rx_bytes_1h.json").is_file(), "workloads_measured": len(rows), "rows": rows[:30]}


def _readiness(snap: Path, objs: _Objects) -> dict:
    unhealthy: Counter = Counter()
    for e in (load_json(snap / "events.json") or {}).get("items") or []:
        if e.get("reason") == "Unhealthy":
            io = e.get("involvedObject") or {}
            if io.get("kind") == "Pod":
                unhealthy[_wl(io.get("namespace", ""), io.get("name", ""))] += int(e.get("count") or 1)
    by_wl: dict[str, list] = defaultdict(list)
    for lab, v in _metric_rows(snap, "pod_ready_ratio_24h"):
        ns, pod = lab.get("namespace"), lab.get("pod")
        if ns and pod:
            by_wl[_wl(ns, pod)].append((pod, v))
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
    not_ready_eps = [{"namespace": ln.get("namespace"), "endpoint": ln.get("endpoint"), "not_ready_addresses": int(v)} for ln, v in _metric_rows(snap, "endpoint_not_ready_addresses")]
    return {"available": (snap / "metrics" / "pod_ready_ratio_24h.json").is_file(), "rows": rows[:40], "unhealthy_events_total": sum(unhealthy.values()), "endpoints_not_ready": not_ready_eps}


def _coredns(snap: Path) -> dict:
    sf = _metric_rows(snap, "coredns_servfail_ratio_1h")
    p99 = _metric_rows(snap, "coredns_p99_1h")
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


def analyze(snap: Path, inv: dict | None) -> dict:
    objs = _Objects(snap, inv)
    alb = _alb(snap, objs)
    ingresses = _ingresses(snap, objs, alb)
    exposure = _exposure(snap, objs, ingresses, alb)
    lb_services = [r for r in exposure if r["type"] == "loadbalancer"]
    return {
        "ingresses": ingresses,
        "ingress_count": len(ingresses),
        "alb_groups": _alb_groups(ingresses),
        "ingress_metrics_source": dict(Counter(r["metrics"].get("source") or "none" for r in ingresses)),
        "alb": alb,
        "nginx": {"metrics_available": any(r["metrics"].get("source") == "ingress-nginx" for r in ingresses)},
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
    out = set()
    for t in objects(snap, "targetgroupbindings.elbv2.k8s.aws"):
        sp = t.get("spec") or {}
        arn = sp.get("targetGroupARN") or ""
        dim = arn.split(":", 5)[5] if arn.count(":") >= 5 else arn
        if (tgm.get(dim) or {}).get("RequestCount_Sum", {}).get("points"):
            out.add((t["metadata"]["namespace"], (sp.get("serviceRef") or {}).get("name")))
    return out

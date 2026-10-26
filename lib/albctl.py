"""AWS Load Balancer Controller summary (collector collectors/alb-controller).

CloudWatch metrics for the ALBs and target groups (5xx, unhealthy hosts, p95, idle timeout, group sharing) belong to the traffic section (lib/traffic.py, alb-metrics step). Here we look at the controller itself:
the Deployment (replicas, node spread, PDB, version, args), the ServiceAccount's IRSA/Pod Identity, webhooks (failurePolicy, timeout, service endpoints), IngressClass/IngressClassParams,
TargetGroupBindings (count, targetType, observedGeneration lag, Service existence), whether LoadBalancer Services are owned by the controller (vs. legacy in-tree), controller metrics (metrics/pod/alb-controller/*.prom:
leader, reconcile errors, webhook response codes, AWS API call count/latency/retries, apiserver 429/503).

Result: the `albctl` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .promtext import parse as _parse_prom
from .snapshot import load_json, objects


def _ver(image: str | None):
    m = re.search(r":v?([0-9]+\.[0-9]+\.[0-9]+)", image or "")
    return m.group(1) if m else None


def _r(x, n=3):
    return None if x is None else round(x, n)


def _pod_metrics(snap: Path) -> dict:
    """Summarize metrics/pod/alb-controller/<pod>.prom per pod. Only the leader pod emits reconcile metrics."""
    d = snap / "metrics" / "pod" / "alb-controller"
    pods = {}
    for f in [x for x in sorted(d.glob("*.prom")) if x.stat().st_size > 0] if d.is_dir() else []:
        pm = _parse_prom(f.read_text(encoding="utf-8", errors="replace"))
        sg, lb = pm["single"], pm["labeled"]
        leader = any(v >= 1 for _, v in lb.get("leader_election_master_status", []))
        api_calls: dict[str, int] = {}
        api_dur: dict[str, float] = {}
        for labels, v in lb.get("aws_api_call_duration_seconds_count", []):
            k = f"{labels.get('service')}/{labels.get('operation')}"
            api_calls[k] = api_calls.get(k, 0) + int(v)
        for labels, v in lb.get("aws_api_call_duration_seconds_sum", []):
            k = f"{labels.get('service')}/{labels.get('operation')}"
            api_dur[k] = api_dur.get(k, 0.0) + v
        retries_sum = sum(v for _, v in lb.get("aws_api_call_retries_sum", []))
        retries_cnt = sum(v for _, v in lb.get("aws_api_call_retries_count", []))
        webhook: dict[str, dict] = {}
        for labels, v in lb.get("controller_runtime_webhook_requests_total", []):
            w = webhook.setdefault(labels.get("webhook"), {})
            w[labels.get("code")] = w.get(labels.get("code"), 0) + int(v)
        rest: dict[str, int] = {}
        for labels, v in lb.get("rest_client_requests_total", []):
            rest[labels.get("code")] = rest.get(labels.get("code"), 0) + int(v)
        recon: dict[str, int] = {}
        for labels, v in lb.get("controller_runtime_reconcile_total", []):
            recon[labels.get("result")] = recon.get(labels.get("result"), 0) + int(v)
        recon_err: dict[str, int] = {}
        for labels, v in lb.get("controller_runtime_reconcile_errors_total", []):
            recon_err[labels.get("controller")] = recon_err.get(labels.get("controller"), 0) + int(v)
        wq = {labels.get("name"): v for labels, v in lb.get("workqueue_depth", [])}
        total_calls = sum(api_calls.values())
        slow_ops = sorted(((k, round(api_dur[k] / api_calls[k], 3)) for k in api_calls if api_calls[k] >= 20 and k in api_dur), key=lambda kv: -kv[1])[:5]
        top_ops = sorted(api_calls.items(), key=lambda kv: -kv[1])[:8]
        start = sg.get("process_start_time_seconds")
        pods[f.stem] = {
            "leader": leader,
            "process_start": start,
            "aws_api_calls_total": total_calls,
            "aws_api_top_ops": top_ops,
            "aws_api_slow_ops_avg_s": slow_ops,
            "aws_api_retries_avg": _r(retries_sum / retries_cnt, 3) if retries_cnt else None,
            "aws_api_retries_total": int(retries_sum),
            "webhook_requests": webhook,
            "webhook_5xx": sum(c for w in webhook.values() for code, c in w.items() if str(code).startswith("5")),
            "rest_client_by_code": rest,
            "rest_client_429_503": rest.get("429", 0) + rest.get("503", 0),
            "reconcile_by_result": recon,
            "reconcile_errors_by_controller": recon_err,
            "reconcile_errors_total": sum(recon_err.values()),
            "workqueue_depth": wq,
            "rss_mb": round(sg.get("process_resident_memory_bytes", 0) / 1024**2) if sg.get("process_resident_memory_bytes") else None,
        }
    return pods


def analyze(snap: Path, inv: dict | None, traffic: dict | None = None) -> dict:
    inv = inv or {}
    dep = next((d for d in objects(snap, "deployments") if d["metadata"]["name"] == "aws-load-balancer-controller"), None)
    if not dep:
        return {"present": False}
    sp, st = dep.get("spec") or {}, dep.get("status") or {}
    tpl = (sp.get("template") or {}).get("spec") or {}
    c0 = (tpl.get("containers") or [{}])[0]
    args = [str(a) for a in (c0.get("args") or [])]

    def arg(name, default=None):
        return next((a.split("=", 1)[1] for a in args if a.startswith(f"--{name}=")), default)

    sel = (sp.get("selector") or {}).get("matchLabels") or {}
    pods = [p for p in objects(snap, "pods") if p["metadata"]["namespace"] == dep["metadata"]["namespace"] and all((p["metadata"].get("labels") or {}).get(k) == v for k, v in sel.items())]
    by_node = Counter(p["spec"].get("nodeName") for p in pods if (p.get("status") or {}).get("phase") == "Running")
    pdbs = [
        b["metadata"]["name"]
        for b in objects(snap, "poddisruptionbudgets.policy")
        if b["metadata"]["namespace"] == dep["metadata"]["namespace"] and all(((b.get("spec") or {}).get("selector") or {}).get("matchLabels", {}).get(k) == v for k, v in sel.items()) and (b.get("spec") or {}).get("selector")
    ]
    sa_name = tpl.get("serviceAccountName") or "aws-load-balancer-controller"
    sa = next((s for s in objects(snap, "serviceaccounts") if s["metadata"]["namespace"] == dep["metadata"]["namespace"] and s["metadata"]["name"] == sa_name), None)
    irsa = ((sa or {}).get("metadata") or {}).get("annotations", {}).get("eks.amazonaws.com/role-arn")
    pia = load_json(snap / "aws" / "pod-identity-associations.json") or {}
    pod_identity = any(a.get("serviceAccount") == sa_name for a in (pia.get("associations") or []))
    controller = {
        "namespace": dep["metadata"]["namespace"],
        "replicas": sp.get("replicas"),
        "ready": st.get("readyReplicas") or 0,
        "version": _ver(c0.get("image")),
        "image": c0.get("image"),
        "args": args,
        "cluster_name": arg("cluster-name"),
        "ingress_class": arg("ingress-class", "alb"),
        "aws_region": arg("aws-region"),
        "enable_shield": arg("enable-shield"),
        "enable_waf": arg("enable-waf"),
        "enable_wafv2": arg("enable-wafv2"),
        "default_target_type": arg("default-target-type"),
        "pods_by_node": dict(by_node),
        "all_same_node": (sp.get("replicas") or 0) >= 2 and len(by_node) == 1,
        "anti_affinity": bool((tpl.get("affinity") or {}).get("podAntiAffinity")),
        "pdb": pdbs,
        "has_pdb": bool(pdbs),
        "priority_class": tpl.get("priorityClassName"),
        "service_account": sa_name,
        "irsa_role": irsa,
        "pod_identity": pod_identity,
        "has_dedicated_role": bool(irsa or pod_identity),
        "resources": c0.get("resources") or {},
    }
    # --- webhooks
    webhooks = []
    ep_ready = {}
    for e in objects(snap, "endpointslices.discovery.k8s.io"):
        svc = (e["metadata"].get("labels") or {}).get("kubernetes.io/service-name")
        if svc:
            ep_ready[(e["metadata"]["namespace"], svc)] = ep_ready.get((e["metadata"]["namespace"], svc), 0) + sum(1 for x in (e.get("endpoints") or []) if ((x.get("conditions") or {}).get("ready") is not False))
    for stem, kind in (("mutatingwebhookconfigurations.admissionregistration.k8s.io", "mutating"), ("validatingwebhookconfigurations.admissionregistration.k8s.io", "validating")):
        for w in objects(snap, stem):
            if "aws-load-balancer" not in w["metadata"]["name"] and "elbv2" not in w["metadata"]["name"]:
                continue
            for h in w.get("webhooks") or []:
                svc = (h.get("clientConfig") or {}).get("service") or {}
                webhooks.append(
                    {
                        "kind": kind,
                        "name": h.get("name"),
                        "failure_policy": h.get("failurePolicy"),
                        "timeout_s": h.get("timeoutSeconds"),
                        "service": svc.get("name"),
                        "service_ready_endpoints": ep_ready.get((svc.get("namespace") or dep["metadata"]["namespace"], svc.get("name"))),
                        "scopes_pods": any("pods" in (r.get("resources") or []) for r in (h.get("rules") or [])),
                        "namespace_selector": bool(h.get("namespaceSelector")),
                        "object_selector": bool(h.get("objectSelector")),
                    }
                )
    # --- IngressClass / Params
    classes = [
        {
            "name": c["metadata"]["name"],
            "controller": (c.get("spec") or {}).get("controller"),
            "default": (c["metadata"].get("annotations") or {}).get("ingressclass.kubernetes.io/is-default-class") == "true",
            "params": (c.get("spec") or {}).get("parameters"),
        }
        for c in objects(snap, "ingressclasses.networking.k8s.io")
        if (c.get("spec") or {}).get("controller") == "ingress.k8s.aws/alb"
    ]
    params = [{"name": p["metadata"]["name"], "spec": p.get("spec")} for p in objects(snap, "ingressclassparams.elbv2.k8s.aws")]
    # --- Ingress
    ings = objects(snap, "ingresses.networking.k8s.io")
    alb_ings = [i for i in ings if ((i.get("spec") or {}).get("ingressClassName") or (i["metadata"].get("annotations") or {}).get("kubernetes.io/ingress.class")) in {c["name"] for c in classes} | {"alb"}]
    no_lb = [f"{i['metadata']['namespace']}/{i['metadata']['name']}" for i in alb_ings if not (((i.get("status") or {}).get("loadBalancer") or {}).get("ingress"))]
    ann_counter: Counter = Counter()
    for i in alb_ings:
        for k in i["metadata"].get("annotations") or {}:
            if k.startswith("alb.ingress.kubernetes.io/"):
                ann_counter[k.split("/")[-1]] += 1
    # --- TargetGroupBinding
    svc_names = {(s["metadata"]["namespace"], s["metadata"]["name"]) for s in objects(snap, "services")}
    tgbs = objects(snap, "targetgroupbindings.elbv2.k8s.aws")
    tgb_rows = []
    for t in tgbs:
        ns = t["metadata"]["namespace"]
        spec = t.get("spec") or {}
        stt = t.get("status") or {}
        ref = spec.get("serviceRef") or {}
        tgb_rows.append(
            {
                "namespace": ns,
                "name": t["metadata"]["name"],
                "target_type": spec.get("targetType"),
                "service": ref.get("name"),
                "port": ref.get("port"),
                "service_exists": (ns, ref.get("name")) in svc_names,
                "generation": t["metadata"].get("generation"),
                "observed_generation": stt.get("observedGeneration"),
                "stale": (t["metadata"].get("generation") or 0) > (stt.get("observedGeneration") or 0),
                "managed": (t["metadata"].get("labels") or {}).get("ingress.k8s.aws/stack") is not None or t["metadata"]["name"].startswith("k8s-"),
                "arn": (spec.get("targetGroupARN") or "")[-24:],
            }
        )
    # --- LoadBalancer Services (controller-owned vs in-tree)
    lb_svcs = []
    for s in objects(snap, "services"):
        if (s.get("spec") or {}).get("type") != "LoadBalancer":
            continue
        ann = s["metadata"].get("annotations") or {}
        lbt = ann.get("service.beta.kubernetes.io/aws-load-balancer-type")
        lbc = (s.get("spec") or {}).get("loadBalancerClass")
        lb_svcs.append(
            {
                "namespace": s["metadata"]["namespace"],
                "name": s["metadata"]["name"],
                "lb_type_annotation": lbt,
                "load_balancer_class": lbc,
                "controller_owned": lbt in ("external", "nlb-ip") or lbc == "service.k8s.aws/nlb",
                "scheme": ann.get("service.beta.kubernetes.io/aws-load-balancer-scheme"),
                "target_type": ann.get("service.beta.kubernetes.io/aws-load-balancer-nlb-target-type"),
                "external_traffic_policy": (s.get("spec") or {}).get("externalTrafficPolicy"),
            }
        )
    # --- metrics
    pm = _pod_metrics(snap)
    leader = next((p for p, d in pm.items() if d["leader"]), None)
    ld = pm.get(leader) if leader else None
    metrics = {
        "available": bool(pm),
        "pods": pm,
        "leader_pod": leader,
        "leader_found": leader is not None,
        "reconcile_errors_total": (ld or {}).get("reconcile_errors_total"),
        "reconcile_by_result": (ld or {}).get("reconcile_by_result"),
        "aws_api_calls_total": sum(d["aws_api_calls_total"] for d in pm.values()),
        "aws_api_top_ops": (ld or {}).get("aws_api_top_ops"),
        "aws_api_slow_ops_avg_s": (ld or {}).get("aws_api_slow_ops_avg_s"),
        "aws_api_retries_avg": (ld or {}).get("aws_api_retries_avg"),
        "webhook_5xx": sum(d["webhook_5xx"] for d in pm.values()),
        "rest_client_429_503": sum(d["rest_client_429_503"] for d in pm.values()),
        "workqueue_depth_max": max([v for d in pm.values() for v in d["workqueue_depth"].values()], default=None),
    }
    traffic_alb = (traffic or {}).get("alb") or {}
    summary = {
        "present": True,
        "version": controller["version"],
        "replicas": controller["replicas"],
        "ready": controller["ready"],
        "all_same_node": controller["all_same_node"],
        "has_pdb": controller["has_pdb"],
        "anti_affinity": controller["anti_affinity"],
        "has_dedicated_role": controller["has_dedicated_role"],
        "irsa_role": irsa,
        "pod_identity": pod_identity,
        "nodes_total": len((inv.get("nodes") or {}).get("nodes") or []),
        "webhooks": len(webhooks),
        "webhooks_fail_policy": sum(1 for w in webhooks if w["failure_policy"] == "Fail"),
        "webhook_pod_scope_fail": any(w["scopes_pods"] and w["failure_policy"] == "Fail" and not w["namespace_selector"] and not w["object_selector"] for w in webhooks),
        "webhook_no_endpoints": [w["name"] for w in webhooks if (w["service_ready_endpoints"] or 0) == 0],
        "webhook_5xx": metrics["webhook_5xx"],
        "ingress_classes": [c["name"] for c in classes],
        "ingress_class_default": any(c["default"] for c in classes),
        "ingress_class_params": len(params),
        "alb_ingresses": len(alb_ings),
        "ingresses_without_lb": no_lb,
        "ingress_annotations_top": dict(ann_counter.most_common(8)),
        "tgb_count": len(tgb_rows),
        "tgb_by_target_type": dict(Counter(t["target_type"] for t in tgb_rows)),
        "tgb_stale": [f"{t['namespace']}/{t['name']}" for t in tgb_rows if t["stale"]],
        "tgb_service_missing": [f"{t['namespace']}/{t['name']}" for t in tgb_rows if not t["service_exists"]],
        "tgb_manual": [f"{t['namespace']}/{t['name']}" for t in tgb_rows if not t["managed"]],
        "lb_services": len(lb_svcs),
        "lb_services_intree": [f"{s['namespace']}/{s['name']}" for s in lb_svcs if not s["controller_owned"]],
        "metrics_available": metrics["available"],
        "leader_found": metrics["leader_found"],
        "reconcile_errors_total": metrics["reconcile_errors_total"],
        "aws_api_calls_total": metrics["aws_api_calls_total"],
        "aws_api_retries_avg": metrics["aws_api_retries_avg"],
        "aws_api_slow_ops_avg_s": metrics["aws_api_slow_ops_avg_s"],
        "aws_api_top_ops": metrics["aws_api_top_ops"],
        "rest_client_429_503": metrics["rest_client_429_503"],
        "workqueue_depth_max": metrics["workqueue_depth_max"],
        "traffic_target_groups_without_tgb": len(traffic_alb.get("target_groups_without_tgb") or []),
        "traffic_unhealthy_target_groups": len(traffic_alb.get("unhealthy_target_groups") or []),
        "cluster_name_arg": controller["cluster_name"],
    }
    return {
        "present": True,
        "controller": controller,
        "webhooks": webhooks,
        "ingress_classes": classes,
        "ingress_class_params": params,
        "ingresses": {"alb": len(alb_ings), "without_lb": no_lb, "annotations_top": dict(ann_counter.most_common(12))},
        "target_group_bindings": {"count": len(tgb_rows), "rows": tgb_rows[:60]},
        "lb_services": lb_svcs,
        "metrics": metrics,
        "summary": summary,
    }

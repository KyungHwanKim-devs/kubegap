"""Observability coverage analysis. Called by summarize to build the observability section of summary.json.

Inputs: prometheus/rules.json (API), prometheus/targets.json, metrics/alerts_*.json, http_metric_namespaces etc., alertmanager/status.json, silences.json, alerts.json,
grafana/*.json, objects/ingresses.networking.k8s.io.json, services.json, inventory.json (components). Missing inputs are recorded as "none" and processing continues.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import re
from collections import Counter
from pathlib import Path

from . import yamlite
from .snapshot import items, load_json

# Symptom/cause classification heuristic. If the expr has any symptom metric it is a symptom; if every metric is infrastructure it is a cause; otherwise (the app's own metrics) it is "app (assumed symptom)".
SYMPTOM_RE = re.compile(
    r"\b(http_[a-z_]+|grpc_server_[a-z_]+|nginx_ingress_controller_[a-z_]+|traefik_[a-z_]+|aws_applicationelb_[a-z_]+|probe_[a-z_]+|sli:[a-z_:]+|slo:[a-z_:]+|[a-z_:]*error_budget[a-z_:]*|[a-z_:]*burn_?rate[a-z_:]*|haproxy_[a-z_]+|envoy_[a-z_]+|istio_requests_total)"
)
INFRA_RE = re.compile(r"\b(container_|node_|kube_|apiserver_|etcd_|kubelet_|prometheus_|alertmanager_|coredns_|kubeproxy_|scheduler_|workqueue_|rest_client_|go_|process_|up\b|ALERTS|vector\(|absent\()")
METRIC_NAME_RE = re.compile(r"\b([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{|\[|\s*[<>=!]|\)|$|\s+(?:by|on|without|ignoring|group_left|group_right|and|or|unless)\b)")

# Failure mode matrix (16 modes). Each mode: (user symptom, importance, alert expr/name pattern)
FAILURE_MODES: list[tuple[str, str, str, str]] = [
    ("OOMKill", "pods die and requests fail or slow down", "critical", r"OOMKill|oom_kill|last_terminated_reason.*OOMKilled|container_oom"),
    ("CrashLoopBackOff", "part or all of a service is down", "critical", r"CrashLoop|restarts_total|KubePodCrashLooping|waiting_reason"),
    ("Node NotReady", "every pod on that node stops", "critical", r"NotReady|KubeNodeNotReady|kube_node_status_condition"),
    ("Disk/PVC full", "write failures, DB outage", "critical", r"filesystem_avail|FilesystemSpace|kubelet_volume_stats|PersistentVolume|DiskPressure|volume_stats_available"),
    ("inode exhaustion", "file creation fails", "high", r"filesystem_files|FilesystemFiles|inode"),
    ("Certificate expiry", "TLS failure blocks all access", "critical", r"certmanager_certificate|CertificateExpir|CertManagerCert|x509|certificate_expir|probe_ssl_earliest"),
    ("5xx surge", "users see error pages", "critical", r"5\.\.|5xx|code=~\"5|status=~\"5|HTTPCode_(Target|ELB)_5XX|http_requests_total.*5|ErrorRate|error_rate|errors:ratio"),
    ("Latency p99 exceeded", "slowness", "high", r"histogram_quantile\(0\.9|duration_seconds_bucket|latency|Latency|p99|TargetResponseTime"),
    ("Backup failure", "unrecoverable", "high", r"velero_backup|backup_last|Backup|k8up|snapshot_"),
    ("HPA at max", "cannot scale further, overload", "high", r"HpaMaxedOut|spec_max_replicas|KubeHpaMaxedOut|horizontalpodautoscaler_status_current_replicas"),
    ("Pod stuck Pending", "deploys and scaling stall", "high", r"KubePodNotReady|phase=\"Pending\"|Pending|KubePodNotScheduled|FailedScheduling"),
    ("Scheduling failure", "new pods do not start", "high", r"FailedScheduling|unschedulable|KubePodNotScheduled|scheduler_pending_pods|scheduler_schedule_attempts"),
    ("Image pull failure", "deploys stall", "medium", r"ImagePull|ErrImagePull|KubeContainerWaiting|waiting_reason"),
    ("DNS error rate", "every call fails intermittently", "high", r"coredns_dns_responses_total|SERVFAIL|CoreDNS|coredns_"),
    ("VPC CNI IP exhaustion", "pods Pending without network", "high", r"awscni_|ip_addresses|FailedCreatePodSandBox|eni_|CNI"),
    ("Karpenter/node provisioning failure", "cannot scale out", "high", r"karpenter_|launch|NodeClaim|cluster_autoscaler_|ClusterAutoscaler|InsufficientCapacity"),
]
EXPECTED_ALWAYS_FIRING = {"Watchdog", "InfoInhibitor"}


PROMQL_KEYWORDS = {
    "by",
    "on",
    "sum",
    "rate",
    "increase",
    "max",
    "min",
    "avg",
    "count",
    "and",
    "or",
    "unless",
    "absent",
    "vector",
    "time",
    "bool",
    "without",
    "ignoring",
    "group_left",
    "group_right",
    "label_replace",
    "label_join",
    "histogram_quantile",
    "topk",
    "bottomk",
    "changes",
    "delta",
    "deriv",
    "predict_linear",
    "abs",
    "round",
    "clamp_min",
    "clamp_max",
    "clamp",
    "quantile",
    "stddev",
    "stdvar",
    "irate",
    "idelta",
    "offset",
    "scalar",
    "ceil",
    "floor",
    "sort",
    "sort_desc",
    "day_of_week",
    "day_of_month",
    "hour",
    "minute",
    "month",
    "year",
    "count_values",
    "count_over_time",
    "sum_over_time",
    "avg_over_time",
    "max_over_time",
    "min_over_time",
    "quantile_over_time",
    "last_over_time",
    "present_over_time",
    "absent_over_time",
    "rate_over_time",
    "resets",
    "sgn",
    "exp",
    "ln",
    "log2",
    "log10",
    "sqrt",
    "timestamp",
    "e",
    "s",
    "m",
    "h",
    "d",
    "w",
    "y",
    "ms",
    "Inf",
    "NaN",
    "nan",
    "inf",
    "true",
    "false",
}
INFRA_PREFIXES = (
    "container_",
    "node_",
    "kube_",
    "apiserver_",
    "etcd_",
    "kubelet_",
    "prometheus_",
    "alertmanager_",
    "coredns_",
    "kubeproxy_",
    "scheduler_",
    "workqueue_",
    "rest_client_",
    "go_",
    "process_",
    "up",
    "ALERTS",
    "machine_",
    "cadvisor_",
    "kubernetes_build_info",
    "aggregator_",
    "volume_manager_",
    "storage_operation_",
    "namespace_",
    "cluster:",
    "instance:",
    "node:",
    "code:",
    "cluster_quantile:",
    "mixin_",
    "kube:",
    "apiserver_request:",
)


def metric_names(expr: str) -> set[str]:
    """Extract only the metric names from a PromQL expression. Drops label matchers {…}, strings, function names, keywords and durations."""
    e = re.sub(r'"(?:[^"\\]|\\.)*"', "", expr or "")
    e = re.sub(r"\{[^}]*\}", "", e)
    e = re.sub(r"\[[^\]]*\]", "", e)
    e = re.sub(r"\b(by|without|on|ignoring|group_left|group_right)\s*\([^)]*\)", " ", e)  # aggregation/matching label lists are not metrics
    names = set()
    for m in re.finditer(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(\()?", e):
        tok, paren = m.group(1), m.group(2)
        if paren or tok in PROMQL_KEYWORDS or re.fullmatch(r"\d+[smhdwy]", tok):
            continue
        names.add(tok)
    return names


def classify_expr(expr: str) -> str:
    names = metric_names(expr)
    all_infra = bool(names) and all(n.startswith(INFRA_PREFIXES) or n == "up" for n in names)
    platform_grpc = bool(re.search(r'job\s*=~?\s*"[^"]*(etcd|apiserver|kube)', expr or "")) and not re.search(r"\bhttp_", expr or "")
    if SYMPTOM_RE.search(expr or "") and not all_infra and not platform_grpc:
        return "symptom"  # grpc/latency of etcd_*/apiserver_* is platform-internal and not counted as a user symptom
    if not names or all_infra:
        return "cause"
    return "app"


def _rules_from_api(snap: Path) -> tuple[list[dict], list[dict], str | None]:
    """(alerting[], recording[], source). Uses the API result (prometheus/rules.json) when present, otherwise PrometheusRule objects."""
    api = load_json(snap / "prometheus" / "rules.json")
    alerting, recording = [], []
    if api and api.get("status") == "success":
        for g in (api.get("data") or {}).get("groups", []):
            for r in g.get("rules", []):
                rec = {"group": g.get("name"), "file": (g.get("file") or "").rsplit("/", 1)[-1], "name": r.get("name"), "expr": r.get("query") or r.get("expr"), "health": r.get("health"), "last_error": r.get("lastError") or None}
                if r.get("type") == "alerting":
                    rec.update(
                        {
                            "severity": (r.get("labels") or {}).get("severity"),
                            "for": r.get("duration"),
                            "state": r.get("state"),
                            "active_alerts": len(r.get("alerts") or []),
                            "labels": r.get("labels") or {},
                            "summary": ((r.get("annotations") or {}).get("summary") or (r.get("annotations") or {}).get("description") or "")[:160],
                        }
                    )
                    alerting.append(rec)
                else:
                    recording.append(rec)
        return alerting, recording, "prometheus/rules.json"
    for pr in items(load_json(snap / "objects" / "prometheusrules.monitoring.coreos.com.json")):
        for g in (pr.get("spec") or {}).get("groups") or []:
            for r in g.get("rules") or []:
                rec = {"group": g.get("name"), "file": f"{pr['metadata']['namespace']}/{pr['metadata']['name']}", "expr": str(r.get("expr") or ""), "health": None}
                if r.get("alert"):
                    rec.update(
                        {
                            "name": r["alert"],
                            "severity": (r.get("labels") or {}).get("severity"),
                            "for": r.get("for"),
                            "state": None,
                            "active_alerts": None,
                            "labels": r.get("labels") or {},
                            "summary": ((r.get("annotations") or {}).get("summary") or "")[:160],
                        }
                    )
                    alerting.append(rec)
                elif r.get("record"):
                    rec["name"] = r["record"]
                    recording.append(rec)
    return alerting, recording, "objects/prometheusrules.monitoring.coreos.com.json" if alerting or recording else None


def _metric_rows(snap: Path, qid: str) -> list[dict]:
    d = load_json(snap / "metrics" / f"{qid}.json") or {}
    return d.get("result", []) if d.get("ok") else []


def _walk_routes(route: dict, depth: int = 0, acc: list | None = None) -> list[dict]:
    acc = [] if acc is None else acc
    acc.append(
        {
            "depth": depth,
            "receiver": route.get("receiver"),
            "matchers": route.get("matchers") or route.get("match") or route.get("match_re"),
            "continue": route.get("continue"),
            "group_by": route.get("group_by"),
            "repeat_interval": route.get("repeat_interval"),
        }
    )
    for r in route.get("routes") or []:
        _walk_routes(r, depth + 1, acc)
    return acc


def _rules(alerting: list[dict], recording: list[dict], src: str | None) -> dict:
    """Rule classification (symptom/cause/app), severity counts and unhealthy rules; sets r["class"] on each alerting rule. Reads nothing (rules come from _rules_from_api)."""
    for r in alerting:
        r["class"] = classify_expr(r.get("expr") or "")
    cls = Counter(r["class"] for r in alerting)
    sev = Counter(r.get("severity") or "none" for r in alerting)
    unhealthy_rules = [{"name": r["name"], "group": r["group"], "health": r["health"], "error": (r.get("last_error") or "")[:160]} for r in alerting + recording if r.get("health") not in (None, "ok")]
    return {
        "source": src,
        "alerting": len(alerting),
        "recording": len(recording),
        "by_class": dict(cls),
        "by_severity": dict(sev),
        "symptom_ratio": round(cls.get("symptom", 0) / len(alerting), 3) if alerting else None,
        "symptom_rules": [r["name"] for r in alerting if r["class"] == "symptom"][:40],
        "app_rules": [r["name"] for r in alerting if r["class"] == "app"][:60],
        "unhealthy": unhealthy_rules,
        "page_severity_cause": [r["name"] for r in alerting if r["class"] == "cause" and (r.get("severity") or "") == "critical"][:40],
    }


def _alerts(snap: Path, alerting: list[dict]) -> dict:
    """Firing history: never-fired rules, always-firing rules, what fires now. Reads metrics/alerts_fired_15d, alerts_firing_samples_7d, alerts_firing_now."""
    fired = {row["metric"].get("alertname") for row in _metric_rows(snap, "alerts_fired_15d")}
    names = {r["name"] for r in alerting}
    never = sorted(n for n in names - fired - EXPECTED_ALWAYS_FIRING)
    samples = []
    for row in _metric_rows(snap, "alerts_firing_samples_7d"):
        with contextlib.suppress(KeyError, ValueError, IndexError):
            samples.append({"alertname": row["metric"].get("alertname"), "samples_7d": float(row["value"][1])})
    samples.sort(key=lambda r: -r["samples_7d"])
    # evaluation interval estimate: Watchdog sample count = a value that fired for all 7 days
    wd = next((s["samples_7d"] for s in samples if s["alertname"] == "Watchdog"), None)
    always = [s for s in samples if wd and s["samples_7d"] >= 0.95 * wd and s["alertname"] not in EXPECTED_ALWAYS_FIRING]
    firing_now = []
    for row in _metric_rows(snap, "alerts_firing_now"):
        m = row["metric"]
        firing_now.append({"alertname": m.get("alertname"), "severity": m.get("severity"), "namespace": m.get("namespace"), "pod": m.get("pod")})
    return {
        "fired_15d": sorted(fired - {None}),
        "never_fired_15d": never,
        "never_fired_count": len(never),
        "rules_total": len(names),
        "firing_now": firing_now,
        "firing_now_by_name": dict(Counter(a["alertname"] for a in firing_now)),
        "top_firing_7d": samples[:15],
        "always_firing_7d": always,
        "watchdog_samples_7d": wd,
        "note": "always_firing = 7-day sample count at or above 95% of Watchdog (always firing). On EKS, KubeControllerManagerDown and KubeSchedulerDown fire forever because the control plane is invisible — false positives",
    }


def _failure_modes(alerting: list[dict], comps: set, platform: str | None) -> dict:
    """Failure mode matrix: which of the 16 modes has an alert rule, and which modes apply to this platform/components. Reads nothing (alert rules and inventory are passed in)."""
    matrix = []
    for mode, symptom, importance, pat in FAILURE_MODES:
        rx = re.compile(pat, re.IGNORECASE)
        hits = [r["name"] for r in alerting if rx.search(r.get("expr") or "") or rx.search(r.get("name") or "")]
        applicable = True
        if mode == "VPC CNI IP exhaustion" and platform != "eks":
            applicable = False
        if mode == "Karpenter/node provisioning failure" and not ({"karpenter", "cluster-autoscaler"} & comps):
            applicable = False
        if mode == "Backup failure" and not ({"velero", "k8up"} & comps):
            applicable = applicable and True  # without a backup tool there is no alert either; that itself is handled by the absence check. Here it is "not applicable"
            applicable = bool({"velero", "k8up"} & comps)
        matrix.append({"mode": mode, "symptom": symptom, "importance": importance, "applicable": applicable, "covered": bool(hits), "rules": hits[:6]})
    return {
        "matrix": matrix,
        "uncovered": [m for m in matrix if m["applicable"] and not m["covered"]],
        "covered_count": sum(1 for m in matrix if m["applicable"] and m["covered"]),
        "applicable_count": sum(1 for m in matrix if m["applicable"]),
    }


def _slo(alerting: list[dict], recording: list[dict], comps: set) -> dict:
    """SLO signals: SLO tools present, sli/slo recording rules, burn-rate alerts, slo-labelled rules. Reads nothing (rules and inventory are passed in)."""
    sli_rules = [r["name"] for r in recording if re.match(r"^(sli|slo)[:_]", r["name"] or "")]
    burn = [
        r["name"] for r in alerting if re.search(r"burn|14\.4|error_budget|errorbudget", (r.get("expr") or "") + (r.get("name") or ""), re.IGNORECASE) and not (r.get("name") or "").startswith("KubeAPIErrorBudgetBurn")
    ]  # kube-prometheus defaults (apiserver SLO) are not service SLO signals
    return {
        "tools": sorted({"sloth", "pyrra"} & comps),
        "sli_recording_rules": sli_rules[:30],
        "burn_rate_alerts": burn[:30],
        "slo_labelled_rules": [r["name"] for r in alerting if (r.get("labels") or {}).get("slo")][:30],
        "any_signal": bool(({"sloth", "pyrra"} & comps) or sli_rules or burn or [r for r in alerting if (r.get("labels") or {}).get("slo")]),
    }


def _am_config(snap: Path) -> dict:
    """Alertmanager routing tree and receivers from the running config, or config_error/config_head (plus config_parse_error with the exception) when it cannot be read. Reads alertmanager/status.json."""
    st = load_json(snap / "alertmanager" / "status.json") or {}
    cfg_text = ((st.get("config") or {}).get("original")) or ""
    cfg, parse_error = None, None
    if cfg_text:
        try:
            cfg = yamlite.load(cfg_text)
        except Exception as e:  # surfaced below so the report's tool notes show why the routing tree is missing
            parse_error = f"{type(e).__name__}: {e}"
    if not cfg:
        out = {"config_error": "status.json missing or config parse failure" if not cfg_text else "config YAML parse failure (syntax unsupported by yamlite)", "config_head": cfg_text[:300]}
        if parse_error:
            out["config_parse_error"] = parse_error
        return out
    route = cfg.get("route") or {}
    receivers = cfg.get("receivers") or []
    recv_kinds = {}
    for rcv in receivers:
        kinds = [k.replace("_configs", "") for k in rcv if k.endswith("_configs") and rcv.get(k)]
        recv_kinds[rcv.get("name")] = kinds
    routes = _walk_routes(route)
    used = {r["receiver"] for r in routes}
    return {
        "default_receiver": route.get("receiver"),
        "default_receiver_kinds": recv_kinds.get(route.get("receiver"), []),
        "default_is_null": not recv_kinds.get(route.get("receiver")),
        "receivers": recv_kinds,
        "null_receivers": [n for n, k in recv_kinds.items() if not k],
        "routes": routes,
        "route_count": len(routes) - 1,
        "unused_receivers": sorted(set(recv_kinds) - used),
        "inhibit_rules": len(cfg.get("inhibit_rules") or []),
        "repeat_interval": route.get("repeat_interval"),
        "group_by": route.get("group_by"),
        "severity_routed": sorted({str(m) for r in routes for m in (r["matchers"] or []) if "severity" in str(m)}),
    }


def _alertmanager(snap: Path) -> dict:
    """Alertmanager section: config (via _am_config), silences and forgotten silences, alert states, failed notifications. Reads alertmanager/silences.json, alerts.json, metrics/alertmanager_notifications_failed_1d."""
    am = {"source": "alertmanager/status.json, silences.json, alerts.json"}
    am.update(_am_config(snap))
    sil = load_json(snap / "alertmanager" / "silences.json") or []
    now = _dt.datetime.now(_dt.UTC)
    sil_rows = []
    for s_ in sil if isinstance(sil, list) else []:
        try:
            ends = _dt.datetime.fromisoformat(str(s_.get("endsAt")))
            starts = _dt.datetime.fromisoformat(str(s_.get("startsAt")))
        except ValueError:
            ends = starts = None
        sil_rows.append(
            {
                "state": (s_.get("status") or {}).get("state"),
                "comment": (s_.get("comment") or "")[:120],
                "created_by": s_.get("createdBy"),
                "matchers": [f"{m.get('name')}{'=~' if m.get('isRegex') else '='}{m.get('value')}" for m in (s_.get("matchers") or [])][:5],
                "ends_at": s_.get("endsAt"),
                "age_days": round((now - starts).days, 1) if starts else None,
                "remaining_days": round((ends - now).total_seconds() / 86400, 1) if ends else None,
            }
        )
    am["silences"] = sil_rows
    am["silences_active"] = [s_ for s_ in sil_rows if s_["state"] == "active"]
    am["silences_forgotten"] = [s_ for s_ in am["silences_active"] if (s_["age_days"] or 0) >= 7 or (s_["remaining_days"] or 0) >= 30]
    alerts = load_json(snap / "alertmanager" / "alerts.json") or []
    if isinstance(alerts, list):
        am["alerts_total"] = len(alerts)
        am["alerts_by_state"] = dict(Counter((a.get("status") or {}).get("state") for a in alerts))
        am["alerts_suppressed"] = [
            {"alertname": (a.get("labels") or {}).get("alertname"), "by": ((a.get("status") or {}).get("inhibitedBy") or []) + ((a.get("status") or {}).get("silencedBy") or [])}
            for a in alerts
            if (a.get("status") or {}).get("state") == "suppressed"
        ][:20]
        am["alerts_active_by_receiver"] = dict(Counter(r.get("name") for a in alerts if (a.get("status") or {}).get("state") == "active" for r in (a.get("receivers") or [])))
    failed = _metric_rows(snap, "alertmanager_notifications_failed_1d")
    am["notifications_failed_1d"] = [{"integration": r["metric"].get("integration"), "count": float(r["value"][1])} for r in failed]
    return am


def _golden_signals(snap: Path, comps: set, platform: str | None) -> dict:
    """Golden signals per ingress backend: whether latency/traffic/errors and saturation metrics exist and from which source. Reads metrics/http_metric_namespaces, saturation_metric_namespaces, ingress_controller_requests, objects/ingresses.networking.k8s.io.json, aws/alb-metrics.json (via traffic)."""
    http_ns = {r["metric"].get("namespace") for r in _metric_rows(snap, "http_metric_namespaces")}
    sat_ns = {r["metric"].get("namespace") for r in _metric_rows(snap, "saturation_metric_namespaces")}
    ic_rows = _metric_rows(snap, "ingress_controller_requests")
    ic_keys = {(r["metric"].get("exported_namespace") or r["metric"].get("namespace"), r["metric"].get("ingress") or r["metric"].get("service")) for r in ic_rows}
    alb_cloudwatch = platform == "eks" and "alb-controller" in comps
    alb_error = None
    try:
        from .traffic import alb_covered_services

        alb_covered = alb_covered_services(snap)  # (ns, service) pairs that have RequestCount in aws/alb-metrics.json
    except Exception as e:  # a broken aws/alb-metrics.json must not stop the golden-signal table; the error is surfaced below
        alb_covered = set()
        alb_error = f"{type(e).__name__}: {e}"
    rows = []
    for ing in items(load_json(snap / "objects" / "ingresses.networking.k8s.io.json")):
        ns, name = ing["metadata"]["namespace"], ing["metadata"]["name"]
        cls_ = (ing.get("spec") or {}).get("ingressClassName") or (ing["metadata"].get("annotations") or {}).get("kubernetes.io/ingress.class")
        hosts = [r.get("host") for r in ((ing.get("spec") or {}).get("rules") or []) if r.get("host")]
        services = sorted({(p.get("backend") or {}).get("service", {}).get("name") for r in ((ing.get("spec") or {}).get("rules") or []) for p in ((r.get("http") or {}).get("paths") or []) if (p.get("backend") or {}).get("service")})
        app_metrics = ns in http_ns
        ic_metrics = (ns, name) in ic_keys or any((ns, s) in ic_keys for s in services)
        alb_metrics = any((ns, s) in alb_covered for s in services)
        lte = app_metrics or ic_metrics or alb_metrics  # latency, traffic and errors come from the same metric family
        rows.append(
            {
                "namespace": ns,
                "ingress": name,
                "class": cls_,
                "hosts": hosts[:3],
                "services": services[:4],
                "latency": lte,
                "traffic": lte,
                "errors": lte,
                "saturation": ns in sat_ns,
                "source": "app" if app_metrics else ("ingress-controller" if ic_metrics else ("alb-cloudwatch" if alb_metrics else ("alb-cloudwatch (not collected)" if alb_cloudwatch else None))),
                "missing_all_lte": not lte,
                "cluster_ic_metrics": bool(ic_rows),  # whether the cluster has any ingress controller metrics at all (if none, the cause is a single one — ingress-controller-metrics-missing)
            }
        )
    return {
        "ingresses": len(rows),
        "rows": rows,
        "namespaces_with_app_http_metrics": sorted(n for n in http_ns if n),
        "namespaces_with_saturation_metrics": sorted(n for n in sat_ns if n),
        "ingress_controller_metric_series": len(ic_rows),
        "alb_cloudwatch_available": alb_cloudwatch,
        "alb_cloudwatch_collected": bool(alb_covered),
        **({"alb_error": alb_error} if alb_error else {}),
        "missing_lte": [r for r in rows if r["missing_all_lte"]],
        "missing_saturation": [r for r in rows if not r["saturation"]],
    }


def _targets(snap: Path) -> dict:
    """Prometheus scrape targets: active/down/dropped counts and job names. Reads prometheus/targets.json."""
    tg = load_json(snap / "prometheus" / "targets.json") or {}
    active = ((tg.get("data") or {}).get("activeTargets")) or []
    dropped = ((tg.get("data") or {}).get("droppedTargets")) or []
    down = [{"job": t.get("labels", {}).get("job"), "instance": t.get("labels", {}).get("instance"), "error": (t.get("lastError") or "")[:140]} for t in active if t.get("health") != "up"]
    return {"active": len(active), "down": down, "down_by_job": dict(Counter(d["job"] for d in down)), "dropped": len(dropped), "jobs": sorted({t.get("labels", {}).get("job") for t in active} - {None})}


def _grafana(snap: Path, alerting: list[dict]) -> dict:
    """Grafana health, datasources, dashboard count and the alert-metric-without-panel comparison. Reads grafana/health.json, datasources.json, dashboards.json, grafana/dashboards/*.json."""
    gh = load_json(snap / "grafana" / "health.json") or {}
    ds = load_json(snap / "grafana" / "datasources.json")
    db = load_json(snap / "grafana" / "dashboards.json")
    out = {
        "version": gh.get("version"),
        "database": gh.get("database"),
        "datasources": [{"name": d.get("name"), "type": d.get("type"), "url": d.get("url"), "default": d.get("isDefault")} for d in ds] if isinstance(ds, list) else "no auth (config.yaml grafana_api_token)",
        "dashboards": len(db) if isinstance(db, list) else "no auth (config.yaml grafana_api_token)",
    }
    # metrics drawn by dashboard panels ↔ metrics used by alert rules — metrics that alert but have no graph to look at. Only when grafana/dashboards/<uid>.json exists (token required)
    ddir = snap / "grafana" / "dashboards"
    dfiles = sorted(ddir.glob("*.json")) if ddir.is_dir() else []
    panel_metrics: set[str] = set()
    dash_rows = []
    for f in dfiles:
        d = load_json(f) or {}
        dash = d.get("dashboard") or {}
        exprs: list[str] = []

        def walk(panels):
            for pn in panels or []:
                for t in pn.get("targets") or []:
                    if isinstance(t.get("expr"), str):
                        exprs.append(t["expr"])
                walk(pn.get("panels"))

        walk(dash.get("panels"))
        for row in dash.get("rows") or []:  # old schema
            walk(row.get("panels"))
        names: set[str] = set()
        for e in exprs:
            names |= metric_names(e)
        panel_metrics |= names
        dash_rows.append({"uid": dash.get("uid") or f.stem, "title": dash.get("title"), "panels_with_expr": len(exprs), "metrics": len(names), "folder": (d.get("meta") or {}).get("folderTitle")})
    if dfiles:
        alert_metrics: set[str] = set()
        for r in alerting:
            alert_metrics |= metric_names(r.get("expr") or "")
        alert_metrics = {m for m in alert_metrics if not m.startswith(("ALERTS", "up"))}
        without = sorted(alert_metrics - panel_metrics)
        out["dashboards_json"] = {
            "read": len(dfiles),
            "rows": dash_rows[:200],
            "panel_metrics": len(panel_metrics),
            "alert_metrics": len(alert_metrics),
            "alert_metrics_without_panel": without[:80],
            "alert_metrics_without_panel_count": len(without),
            "empty_dashboards": [r["uid"] for r in dash_rows if r["panels_with_expr"] == 0],
            "available": True,
        }
    else:
        out["dashboards_json"] = {"available": False, "note": "grafana/dashboards/*.json missing — with grafana_api_token the dashboards-json step fills it"}
    return out


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    comps = set(inv.get("components_present") or [])
    platform = (inv.get("cluster") or {}).get("platform")
    alerting, recording, src = _rules_from_api(snap)
    return {
        "source": "prometheus/, alertmanager/, grafana/, metrics/alerts_*.json, objects/ingresses*.json",
        "rules": _rules(alerting, recording, src),
        "alerts": _alerts(snap, alerting),
        "failure_modes": _failure_modes(alerting, comps, platform),
        "slo": _slo(alerting, recording, comps),
        "alertmanager": _alertmanager(snap),
        "golden_signals": _golden_signals(snap, comps, platform),
        "targets": _targets(snap),
        "grafana": _grafana(snap, alerting),
    }

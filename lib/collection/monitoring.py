"""Find the Prometheus, Loki, Alertmanager and Grafana services and verify connectivity.

Rules (measured on real clusters running kube-prometheus-stack + loki-stack):
- prometheus:   port 9090, name contains prometheus. Prefer the chart Service over `prometheus-operated` (the operator's headless Service)
- alertmanager: port 9093, name contains alertmanager. Same preference
- loki:         port 3100, name contains loki. Exclude `-headless` and `-memberlist`; prefer `gateway` when present
- grafana:      label app.kubernetes.io/name=grafana or name contains grafana, port 80 or 3000
If the config file provides a URL (`prometheus_url` etc.), discovery is skipped and that URL is used.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from ..foundations import http, yamlite
from . import kube
from .portfwd import PortForward

TARGETS = ("prometheus", "alertmanager", "loki", "grafana")


@dataclass
class Service:
    kind: str
    namespace: str
    name: str
    port: int
    cluster_ip: str | None = None

    def to_dict(self):
        return asdict(self)


def _ports(svc) -> list[int]:
    return [p.get("port") for p in svc.get("spec", {}).get("ports", []) if isinstance(p.get("port"), int)]


def _score(kind: str, name: str) -> int:
    s = 0
    if name.endswith("-operated"):
        s -= 5
    if name.endswith(("-headless", "-memberlist")):
        s -= 100
    if kind == "loki" and "gateway" in name:
        s += 5
    if kind == "loki" and ("canary" in name or "promtail" in name):
        s -= 100
    return s


def find_services(context: str | None, kubeconfig: str | None = None, log=None) -> tuple[dict[str, Service | None], str | None]:
    data, r = kube.kubectl_json(["get", "svc", "-A"], context=context, timeout=60, id="setup.get-svc", log=log, kubeconfig=kubeconfig)
    if data is None:
        return dict.fromkeys(TARGETS), r.error or r.stderr.strip()[-300:] or "kubectl get svc failed"
    best: dict[str, tuple[int, Service]] = {}
    for svc in data.get("items", []):
        name = svc["metadata"]["name"]
        ns = svc["metadata"]["namespace"]
        labels = svc["metadata"].get("labels", {}) or {}
        ports = _ports(svc)
        lname = name.lower()
        candidates: list[tuple[str, int]] = []
        if "prometheus" in lname and 9090 in ports and "operator" not in lname:
            candidates.append(("prometheus", 9090))
        if "alertmanager" in lname and 9093 in ports:
            candidates.append(("alertmanager", 9093))
        if "loki" in lname and 3100 in ports:
            candidates.append(("loki", 3100))
        if (labels.get("app.kubernetes.io/name") == "grafana" or "grafana" in lname) and (80 in ports or 3000 in ports):
            candidates.append(("grafana", 80 if 80 in ports else 3000))
        for kind, port in candidates:
            sc = _score(kind, lname)
            if kind not in best or sc > best[kind][0]:
                best[kind] = (sc, Service(kind, ns, name, port, svc.get("spec", {}).get("clusterIP")))
    return {k: (best[k][1] if k in best else None) for k in TARGETS}, None


# ---------- connectivity check ----------


def _loki_retention(text: str) -> tuple[str | None, str | None, str]:
    """(limits_config.retention_period, compactor.retention_enabled, how they were read) from Loki's /config text.

    The dump is go-yaml output with plain scalars folded at 80 columns; after `yamlite.unfold_plain_scalars` the whole of a real 2.6.1 dump loads,
    and the keys are read from the structure ("parsed"). When `load` still refuses the text (a construct outside yamlite's subset) the two keys are
    read inside their own sections with `yamlite.mapping_value` ("section"): still never a `retention_period` of another section, which the
    whole-text regular expression used until #126 could return. Booleans come back as the lower-case words the old reader returned."""
    try:
        cfg = yamlite.load(yamlite.unfold_plain_scalars(text))
    except Exception:
        cfg = None
    if isinstance(cfg, dict):
        period = ((cfg.get("limits_config") or {}) if isinstance(cfg.get("limits_config"), dict) else {}).get("retention_period")
        enabled = ((cfg.get("compactor") or {}) if isinstance(cfg.get("compactor"), dict) else {}).get("retention_enabled")
        norm = lambda v: None if v is None else (str(v).lower() if isinstance(v, bool) else str(v))  # noqa: E731
        return norm(period), norm(enabled), "parsed"
    return yamlite.mapping_value(text, "limits_config", "retention_period"), yamlite.mapping_value(text, "compactor", "retention_enabled"), "section"


def _retention_from_flags(flags: dict | None) -> dict:
    out = {}
    if not flags:
        return out
    for k in ("storage.tsdb.retention.time", "storage.tsdb.retention.size"):
        v = flags.get(k)
        if v:
            out[k.rsplit(".", 1)[-1]] = v
    return out


def probe(kind: str, base: str) -> dict:
    """Call each store's status API once and collect version, retention and status."""
    base = base.rstrip("/")
    info: dict = {"kind": kind, "url": base, "ok": False}
    if kind == "prometheus":
        b = http.get(f"{base}/api/v1/status/buildinfo")
        info["ok"] = b.ok
        if b.ok:
            info["version"] = (b.json() or {}).get("data", {}).get("version")
            f = http.get(f"{base}/api/v1/status/flags")
            info["retention"] = _retention_from_flags((f.json() or {}).get("data") if f.ok else None)
            t = http.get(f"{base}/api/v1/status/tsdb")
            if t.ok:
                head = ((t.json() or {}).get("data") or {}).get("headStats") or {}
                info["head_series"] = head.get("numSeries")
        else:
            info["error"] = b.error
    elif kind == "alertmanager":
        s = http.get(f"{base}/api/v2/status")
        info["ok"] = s.ok
        if s.ok:
            j = s.json() or {}
            info["version"] = (j.get("versionInfo") or {}).get("version")
            info["cluster_status"] = (j.get("cluster") or {}).get("status")
        else:
            info["error"] = s.error
    elif kind == "loki":
        r = http.get(f"{base}/ready", headers={"Accept": "text/plain"})
        info["ok"] = r.ok
        b = http.get(f"{base}/loki/api/v1/status/buildinfo")
        if b.ok:
            info["version"] = (b.json() or {}).get("version")
        if r.ok:
            c = http.get(f"{base}/config", headers={"Accept": "text/plain"})
            if c.ok:
                # The running configuration as YAML (pkg/loki/config_handler.go). Read by section: limits_config.retention_period is the global retention,
                # compactor.retention_enabled whether it is applied; a regular expression over the whole text took the first `retention_period:` and
                # table_manager carries one too (0s on the EKS cluster). lib/foundations/yamlite.load cannot take the dump (multi-line plain scalars), so the
                # section reader of yamlite is used instead of a full parse (#126, #148).
                period, enabled, source = _loki_retention(c.body)
                info["retention"] = {"time": period} if period else {}
                if enabled is not None:
                    info["retention"]["enabled"] = enabled
                info["retention_source"] = source
        else:
            info["error"] = r.error or f"HTTP {r.status}"
    elif kind == "grafana":
        h = http.get(f"{base}/api/health")
        info["ok"] = h.ok
        if h.ok:
            info["version"] = (h.json() or {}).get("version")
        else:
            info["error"] = h.error
    return info


def connect_and_probe(kind: str, svc: Service | None, configured_url: str | None, context: str | None, kubeconfig: str | None = None) -> dict:
    """Probe via the configured URL if present, otherwise open a short-lived port-forward. Records the access method in the result."""
    if configured_url:
        info = probe(kind, configured_url)
        info["access"] = "config"
        return info
    if svc is None:
        return {"kind": kind, "ok": False, "access": None, "error": "service not found"}
    pf = PortForward(context, svc.namespace, svc.name, svc.port, kubeconfig=kubeconfig)
    if not pf.start():
        return {"kind": kind, "ok": False, "access": "port-forward", "service": svc.to_dict(), "error": pf.error}
    try:
        info = probe(kind, pf.url)
    finally:
        pf.stop()
    info["access"] = "port-forward"
    info["service"] = svc.to_dict()
    info.pop("url", None)
    return info


# ---------- what Grafana shows without a token ----------

# The Grafana chart's sidecars load dashboards and datasources from ConfigMaps carrying these labels (grafana/helm-charts
# charts/grafana/values.yaml:951 `sidecar.dashboards.label: grafana_dashboard` and :1028 `sidecar.datasources.label: grafana_datasource`
# @grafana-8.5.0; kube-prometheus-stack sets the same labels on the ConfigMaps it ships). A chart installed with another label is not seen here.
DASHBOARD_LABEL = "grafana_dashboard"
DATASOURCE_LABEL = "grafana_datasource"
TOTAL_DASHBOARDS_METRIC = "grafana_stat_totals_dashboard"  # grafana/grafana pkg/infra/metrics/metrics.go:483@v12.2.1 (collectors/grafana/pod-metrics.yaml)
_TOTAL_RE = re.compile(r"^" + TOTAL_DASHBOARDS_METRIC + r"(?:\{[^}]*\})?\s+(\S+)", re.MULTILINE)


def _total_from_text(text: str) -> int | None:
    m = _TOTAL_RE.search(text or "")
    try:
        return int(float(m.group(1))) if m else None
    except ValueError:
        return None


def grafana_provisioned(context: str | None, kubeconfig: str | None, grafana: dict, grafana_url: str | None, prometheus: dict, prometheus_url: str | None, log=None) -> dict:
    """{dashboards, datasources, total_dashboards, total_source, error}: the ConfigMaps the Grafana sidecars load (names only, counted) and the
    number of dashboards Grafana itself reports. The total comes from Grafana's own `/metrics`, which the same port-forward or URL as the
    audit reaches and which needs no login unless `[metrics] basic_auth_username` is set (grafana/grafana conf/defaults.ini:1728-1738@v12.2.1:
    `enabled = true`, the two basic_auth keys empty); when that fails, from a Prometheus that scrapes Grafana. None when neither answers.
    Nothing here needs a Grafana login."""
    out: dict = {"dashboards": 0, "datasources": 0, "total_dashboards": None, "total_source": None, "error": None}
    for key, label in (("dashboards", DASHBOARD_LABEL), ("datasources", DATASOURCE_LABEL)):
        data, r = kube.kubectl_json(["get", "configmaps", "-A", "-l", label, "--ignore-not-found"], context=context, timeout=60, id=f"setup.grafana-{key}", log=log, kubeconfig=kubeconfig)
        if data is None:
            out["error"] = r.error or r.stderr.strip()[-200:] or "kubectl get configmaps failed"
            continue
        out[key] = len(data.get("items") or [])
    svc = grafana.get("service") or {}
    if grafana.get("ok") and (grafana_url or svc):
        text = _read(context, kubeconfig, grafana_url, svc, "/metrics", {"Accept": "text/plain"})
        total = _total_from_text(text)
        if total is not None:
            out["total_dashboards"], out["total_source"] = total, "grafana /metrics"
            return out
    psvc = prometheus.get("service") or {}
    if prometheus.get("ok") and (prometheus_url or psvc):
        body = _read(context, kubeconfig, prometheus_url, psvc, "/api/v1/query?query=max(" + TOTAL_DASHBOARDS_METRIC + ")", None)
        try:
            rows = ((json.loads(body or "null") or {}).get("data") or {}).get("result") or []
            if rows:
                out["total_dashboards"], out["total_source"] = int(float(rows[0]["value"][1])), "prometheus"
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    return out


def _read(context, kubeconfig, url: str | None, svc: dict, path: str, headers: dict | None) -> str | None:
    """GET `path` on a store through its configured URL or a short port-forward to its Service; the body, or None."""
    if url:
        r = http.get(url.rstrip("/") + path, headers=headers)
        return r.body if r.ok else None
    pf = PortForward(context, svc["namespace"], svc["name"], svc["port"], kubeconfig=kubeconfig)
    if not pf.start():
        return None
    try:
        r = http.get(pf.url + path, headers=headers)
        return r.body if r.ok else None
    finally:
        pf.stop()


def describe_provisioned(p: dict) -> str:
    """The setup line for the provisioned counts."""
    if not p.get("dashboards") and not p.get("datasources"):
        return "no dashboard or datasource ConfigMaps for the sidecars" + (f" ({p['error']})" if p.get("error") else "") + "; the lists need grafana_api_token"
    total = p.get("total_dashboards")
    if isinstance(total, int):
        more = total - (p.get("dashboards") or 0)
        tail = f"; Grafana counts {total}, so {more} made in Grafana itself need a token to be listed" if more > 0 else f"; Grafana counts {total}, nothing missing"
    else:
        tail = "; Grafana's own count was not readable (its /metrics, or a Prometheus that scrapes it)"
    return f"read without a token: {p.get('dashboards') or 0} dashboard and {p.get('datasources') or 0} datasource ConfigMaps{tail}"

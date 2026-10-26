"""Find the Prometheus, Loki, Alertmanager and Grafana services and verify connectivity.

Rules (measured on real clusters running kube-prometheus-stack + loki-stack):
- prometheus:   port 9090, name contains prometheus. Prefer the chart Service over `prometheus-operated` (the operator's headless Service)
- alertmanager: port 9093, name contains alertmanager. Same preference
- loki:         port 3100, name contains loki. Exclude `-headless` and `-memberlist`; prefer `gateway` when present
- grafana:      label app.kubernetes.io/name=grafana or name contains grafana, port 80 or 3000
If the config file provides a URL (`prometheus_url` etc.), discovery is skipped and that URL is used.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from . import http, kube
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
                m = re.search(r"retention_period:\s*(\S+)", c.body)
                info["retention"] = {"time": m.group(1)} if m else {}
                m2 = re.search(r"retention_enabled:\s*(\S+)", c.body)
                if m2:
                    info["retention"]["enabled"] = m2.group(1)
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

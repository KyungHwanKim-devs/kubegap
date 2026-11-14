"""Where this cluster's logs go, read at setup time, so the first-run question about Loki is asked only when Loki could be the answer (#174).

The `stores` question asked "Not found in the cluster: loki. Is it installed somewhere else?" on every cluster without a Loki Service. A cluster that
ships its logs to Elasticsearch, OpenSearch or CloudWatch Logs has nothing to answer: the log shipper's own configuration says where the logs go.
This module reads that configuration, names only, and the result lets lib/commands/firstrun.py leave Loki out of the question, or pre-fill the address of
a Loki that lives outside the cluster.

What is read (all `get`/`list`, nothing else):
- the DaemonSets of the cluster, by name, to find the shipper and its namespace: fluent-bit and fluentd (fluent/helm-charts
  charts/fluent-bit/templates/daemonset.yaml:3,5@fluent-bit-0.58.3, charts/fluentd/templates/daemonset.yaml:3,5@fluentd-0.6.0), promtail
  (grafana/helm-charts charts/promtail/values.yaml:425-426@promtail-6.16.6 names its Loki in `config.clients[].url`), vector and alloy;
- the ConfigMaps of the shipper's namespace, for the output sections. fluent-bit classic format: `[OUTPUT]` blocks with `Name` and `Host`
  (fluent/helm-charts charts/fluent-bit/values.yaml:425-429@fluent-bit-0.58.3 is the chart's example; the plugin names are the `.name` of each
  output plugin: fluent/fluent-bit plugins/out_es/es.c:1293, out_opensearch/opensearch.c:1276, out_cloudwatch_logs/cloudwatch_logs.c:698,
  out_loki/loki.c:2167, out_forward/forward.c:1805@v3.2.10). fluent-bit YAML format: an `outputs:` list with `name:` and `host:`
  (src/config_format/flb_cf_yaml.c:1514@v3.2.10 reads the `outputs` section). fluentd: `<match>` sections with `@type elasticsearch|cloudwatch_logs|loki`
  (uken/fluent-plugin-elasticsearch lib/fluent/plugin/out_elasticsearch.rb:67,77@v5.4.3; fluent-plugins-nursery/fluent-plugin-cloudwatch-logs
  lib/fluent/plugin/out_cloudwatch_logs.rb:8@v0.14.3; grafana/loki clients/cmd/fluentd/lib/fluent/plugin/out_loki.rb:28,39@v3.4.2). promtail:
  `clients:` entries with `url:` (grafana/loki clients/pkg/promtail/client/config.go:31@v3.4.2);
- the Services of the cluster, to find a log store that serves HTTP on 9200: Elasticsearch (elastic/helm-charts elasticsearch/templates/service.yaml:29-31
  and elasticsearch/values.yaml:191@v8.5.1) and OpenSearch (opensearch-project/helm-charts charts/opensearch/templates/service.yaml:26-28 and
  charts/opensearch/values.yaml:282@opensearch-2.39.0).

ConfigMap values of the shipper's namespace are read here and not kept: only the plugin name, host and port of each output land in setup.json.
"""

from __future__ import annotations

import re

from . import kube

SHIPPERS = ("fluent-bit", "fluentd", "promtail", "vector", "alloy")
# output plugin name -> the store it means. `forward` goes to another shipper and says nothing about the store.
PLUGIN_STORE = {
    "es": "elasticsearch",
    "elasticsearch": "elasticsearch",
    "opensearch": "opensearch",
    "cloudwatch_logs": "cloudwatch-logs",
    "cloudwatch": "cloudwatch-logs",
    "loki": "loki",
    "kafka": "kafka",
    "splunk": "splunk",
    "datadog": "datadog",
    "s3": "s3",
    "stdout": None,
    "null": None,
    "forward": None,
}
_CLASSIC_SECTION = re.compile(r"^\s*\[(\w+)\]\s*$")
_CLASSIC_KEY = re.compile(r"^\s*(\w+)\s+(.+?)\s*$")
_FLUENTD_MATCH = re.compile(r"<match\b[^>]*>(.*?)</match>", re.DOTALL | re.IGNORECASE)
_FLUENTD_KEY = re.compile(r"^\s*(@type|host|hosts|port|url|log_group_name)\s+(\S+)", re.MULTILINE)
_YAML_OUTPUT = re.compile(r"^(\s*)-\s*name:\s*(\S+)\s*$((?:\n\1\s+\S.*)*)", re.MULTILINE)
_YAML_KEY = re.compile(r"^\s*(host|port|url):\s*(\S+)", re.MULTILINE)
_PROMTAIL_URL = re.compile(r"^\s*-\s*url:\s*(\S+)", re.MULTILINE)


def _shipper_kind(name: str) -> str | None:
    n = name.lower()
    for k in SHIPPERS:
        if k in n or k.replace("-", "") in n:
            return k
    return None


def parse_outputs(text: str, kind: str) -> list[dict]:
    """The output sections of one configuration text: [{plugin, host, port, url}]. `kind` is the shipper, which decides the syntax."""
    out: list[dict] = []
    if kind in ("fluent-bit", "vector", "alloy") or (kind == "fluentd" and "[OUTPUT]" in text.upper()):
        section = None
        cur: dict | None = None
        for line in text.splitlines():
            m = _CLASSIC_SECTION.match(line)
            if m:
                section = m.group(1).upper()
                cur = {"plugin": None, "host": None, "port": None, "url": None} if section == "OUTPUT" else None
                if cur is not None:
                    out.append(cur)
                continue
            if cur is None:
                continue
            k = _CLASSIC_KEY.match(line)
            if not k:
                continue
            key, val = k.group(1).lower(), k.group(2).strip()
            if key == "name":
                cur["plugin"] = val.lower()
            elif key == "host":
                cur["host"] = val
            elif key == "port" and val.isdigit():
                cur["port"] = int(val)
        if "outputs:" in text:  # fluent-bit YAML format
            for m in _YAML_OUTPUT.finditer(text):
                block = m.group(3) or ""
                keys = {k.lower(): v for k, v in _YAML_KEY.findall(block)}
                out.append({"plugin": m.group(2).lower(), "host": keys.get("host"), "port": int(keys["port"]) if keys.get("port", "").isdigit() else None, "url": keys.get("url")})
    if kind == "fluentd":
        for m in _FLUENTD_MATCH.finditer(text):
            keys = {k.lower(): v for k, v in _FLUENTD_KEY.findall(m.group(1))}
            if keys.get("@type"):
                out.append({"plugin": keys["@type"].lower(), "host": keys.get("host") or keys.get("hosts"), "port": int(keys["port"]) if keys.get("port", "").isdigit() else None, "url": keys.get("url")})
    if kind == "promtail":
        for url in _PROMTAIL_URL.findall(text):
            out.append({"plugin": "loki", "host": None, "port": None, "url": url})
    return [o for o in out if o["plugin"] and o["plugin"] not in ("stdout", "null")]


def _store_of(output: dict) -> str | None:
    return PLUGIN_STORE.get(output["plugin"], output["plugin"])


def detect(context: str | None, kubeconfig: str | None = None, log=None) -> dict:
    """{shippers, outputs, stores, logs_go_to, loki_outside, error}. Every list is empty when nothing was found; `error` says why a read failed."""
    result: dict = {"shippers": [], "outputs": [], "stores": [], "logs_go_to": [], "loki_outside": None, "error": None}
    ds, r = kube.kubectl_json(["get", "daemonsets", "-A"], context=context, timeout=60, id="setup.get-daemonsets", log=log, kubeconfig=kubeconfig)
    if ds is None:
        result["error"] = r.error or r.stderr.strip()[-200:] or "kubectl get daemonsets failed"
        return result
    for it in ds.get("items") or []:
        name = it["metadata"]["name"]
        kind = _shipper_kind(name)
        if kind:
            result["shippers"].append({"namespace": it["metadata"]["namespace"], "name": name, "kind": kind})
    for ns in sorted({s["namespace"] for s in result["shippers"]}):
        kinds = [s["kind"] for s in result["shippers"] if s["namespace"] == ns]
        cms, r = kube.kubectl_json(["get", "configmaps", "-n", ns], context=context, timeout=60, id=f"setup.get-configmaps.{ns}", log=log, kubeconfig=kubeconfig)
        if cms is None:
            result["error"] = r.error or r.stderr.strip()[-200:] or f"kubectl get configmaps -n {ns} failed"
            continue
        for cm in cms.get("items") or []:
            for key, text in (cm.get("data") or {}).items():
                if not isinstance(text, str):
                    continue
                for kind in dict.fromkeys(kinds):
                    for o in parse_outputs(text, kind):
                        o["shipper"] = kind
                        o["source"] = f"configmap {ns}/{cm['metadata']['name']}:{key}"
                        result["outputs"].append(o)
    svcs, r = kube.kubectl_json(["get", "svc", "-A"], context=context, timeout=60, id="setup.get-svc-logstores", log=log, kubeconfig=kubeconfig)
    for svc in (svcs or {}).get("items") or []:
        name = svc["metadata"]["name"].lower()
        ports = [p.get("port") for p in (svc.get("spec") or {}).get("ports") or [] if isinstance(p.get("port"), int)]
        if 9200 in ports and ("elasticsearch" in name or "opensearch" in name) and "headless" not in name:
            result["stores"].append({"kind": "opensearch" if "opensearch" in name else "elasticsearch", "namespace": svc["metadata"]["namespace"], "name": svc["metadata"]["name"], "port": 9200})
    goes = []
    for o in result["outputs"]:
        store = _store_of(o)
        if store and store not in goes:
            goes.append(store)
    for s in result["stores"]:
        if s["kind"] not in goes and not result["outputs"]:
            goes.append(s["kind"])
    result["logs_go_to"] = goes
    loki = [o for o in result["outputs"] if _store_of(o) == "loki"]
    if loki:
        o = loki[0]
        result["loki_outside"] = o.get("url") or (f"http://{o['host']}:{o['port'] or 3100}" if o.get("host") else None)
    return result


def explain(sinks: dict, language: str = "en") -> str | None:
    """One line for the setup output and the report: where the logs go, with the evidence, or None when nothing was found."""
    if not sinks or not sinks.get("logs_go_to"):
        return None
    ko = language == "ko"
    parts = []
    for store in sinks["logs_go_to"]:
        ev = [o for o in sinks["outputs"] if _store_of(o) == store]
        if ev:
            o = ev[0]
            where = o.get("url") or (f"{o['host']}:{o['port']}" if o.get("host") and o.get("port") else o.get("host")) or ""
            parts.append(f"{store} ({o['shipper']} {'출력' if ko else 'output'} {o['plugin']}{' → ' + where if where else ''}, {o['source']})")
        else:
            s = next((s for s in sinks["stores"] if s["kind"] == store), None)
            parts.append(f"{store} (service {s['namespace']}/{s['name']}:{s['port']})" if s else store)
    return ("로그는 " + "; ".join(parts) + "로 갑니다") if ko else ("logs go to " + "; ".join(parts))

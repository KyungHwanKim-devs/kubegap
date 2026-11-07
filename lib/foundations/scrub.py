"""What is dropped from objects before they are written to the snapshot.

The snapshot is read by the agent, and what the agent reads goes to its model API. So the rule is: a value that may hold a
credential is not written to disk at all. Masking after the fact only catches shapes we know; not storing catches everything.

- Secret, SecretList: `data` and `stringData` are removed (names and types stay).
- ConfigMap: every value in `data` is replaced by its length and shape, and `binaryData` by its length. The exceptions are the
  configuration keys kubegap's own parsers read (CoreDNS Corefile, kube-proxy config, local-path-provisioner paths, a few
  Argo CD flags), listed in KEEP_VALUES below. Two Argo CD keys that can carry a client secret are reduced to "present";
  the RBAC policy to its line count. Before the values go, they are inspected once for secret-like keys (the rule of
  `security.plaintext-configmap-secret`) and the resulting key names are stored under `kubegap_scrub`, so the check works
  without the values. Two annotations carry a copy of the whole object, `data` included: kubectl's
  `kubectl.kubernetes.io/last-applied-configuration` (plain JSON) and the k3s helm-controller's `objectset.rio.cattle.io/applied`
  (gzip, base64). Their values are replaced by length and shape too; the keys stay, so "applied with kubectl" remains visible.
  A gzip copy is expanded up to GZIP_MAX_BYTES (8 MiB) and inspected no further beyond that: etcd caps an object at about 1.5 MiB, but
  gzip expands up to about a thousand times, so one crafted annotation could otherwise ask for a gigabyte. The annotation is replaced by
  length and shape either way, so nothing of it reaches the snapshot.
  Component detection in lib/collection/discover runs on the in-memory objects before this scrub.

The three writers of kubectl JSON go through `scrub_or_error`: lib/collection/discover for the kinds it fetches, lib/collection/collect dump-all for the rest, and
the `type: kubectl` steps through `json_scrubber`, which lib/foundations/shell applies before the file exists. A scrub that raises writes nothing and fails the step.
"""

from __future__ import annotations

import json
import re

from . import shell, yamlite
from .components import match_name

SECRET_KINDS = {"Secret", "SecretList"}
GZIP_MAX_BYTES = 8 * 1024 * 1024  # how far a gzip+base64 applied copy is expanded for inspection
CONFIGMAP_KINDS = {"ConfigMap"}
MARK = "kubegap_scrub"

# (namespace glob, name glob, keys whose values stay as they are). Only configuration that a kubegap parser reads.
KEEP_VALUES: list[tuple[str, str, tuple[str, ...]]] = [
    ("kube-system", "coredns", ("Corefile", "NodeHosts")),  # lib/summaries/coredns.py
    ("kube-system", "kube-proxy-config", ("config",)),  # lib/summaries/kubeproxy.py (EKS)
    ("kube-system", "kube-proxy", ("config",)),  # lib/summaries/kubeproxy.py
    ("*", "local-path-config", ("config.json",)),  # lib/summaries/localpath.py
    ("argocd", "argocd-cm", ("url", "admin.enabled", "timeout.reconciliation", "exec.enabled", "users.anonymous.enabled")),  # lib/summaries/argocdctl.py
    ("argocd", "argocd-cmd-params-cm", ("controller.status.processors", "controller.operation.processors", "application.namespaces", "server.insecure")),
    ("argocd", "argocd-rbac-cm", ("policy.default",)),
]
# ConfigMaps the Grafana sidecars load (label names: grafana/helm-charts charts/grafana/values.yaml:951,1028@grafana-8.5.0). A dashboard ConfigMap
# keeps its data: the value is the dashboard's JSON model, which the alert-metric-without-dashboard comparison reads (lib/summaries/observability.py).
# A datasource ConfigMap is a provisioning file that may carry a password or a header value (grafana/grafana
# pkg/services/provisioning/datasources/types.go:32-45@v12.2.1: basicAuthPassword, secureJsonData), so only name, type, url and isDefault of
# each datasource are kept, parsed here before the value is dropped.
KEEP_BY_LABEL = {"grafana_dashboard": "dashboard", "grafana_datasource": "datasource"}
# Keys whose value is reduced to the string "present" (they can embed an OIDC client secret) or to "<n lines>".
PRESENCE_ONLY = [("argocd", "argocd-cm", ("dex.config", "oidc.config"))]
LINE_COUNT_ONLY = [("argocd", "argocd-rbac-cm", ("policy.csv",))]
# Annotations whose value is a copy of the object, so a ConfigMap's data would survive in them after `data` is scrubbed.
LAST_APPLIED = "kubectl.kubernetes.io/last-applied-configuration"
COPY_ANNOTATIONS = (LAST_APPLIED, "objectset.rio.cattle.io/applied")

# Secret-like key detection, moved here from lib/summaries/security.py so it can run before the values are dropped.
SECRET_ENV_RE = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_KEY|CLIENT_SECRET|DSN|CONNECTION_STRING)", re.IGNORECASE)
ENV_SKIP_RE = re.compile(r"(_FILE|_PATH|_DIR|_NAME|_KEY_ID|_REF|_ENABLED|_URL|_HEADER|_TTL|_LENGTH|_EXPIRY|_TIMEOUT)$", re.IGNORECASE)
# A line inside a config file such as `HTTP_Passwd xxx`, `password: xxx`, `DB_PASSWORD=xxx`. The key may start with the secret word itself (the earlier form required one leading character and missed a bare `password = ...`).
_LINE_RE = re.compile(r"(?im)^\s*([A-Za-z0-9_.-]*(?:passw(?:or)?d|secret|token|api[_-]?key)[A-Za-z0-9_.-]*)\s*[:= ]\s*(\S{8,})\s*$")
_URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


def _keys_for(table: list[tuple[str, str, tuple[str, ...]]], ns: str, name: str) -> set[str]:
    out: set[str] = set()
    for pns, pname, keys in table:
        if match_name(f"{pns}/{pname}", ns, name):
            out |= set(keys)
    return out


def secret_like_keys(data: dict, limit: int = 8) -> list[str]:
    """Key names (or `key:line-key` inside config files) whose value looks like a credential. Values are inspected but never returned."""
    keys: list[str] = []
    for k, v in (data or {}).items():
        v = str(v)
        if SECRET_ENV_RE.search(k) and not ENV_SKIP_RE.search(k) and len(v) >= 8 and not v.isdigit() and not v.startswith("/") and v.lower() not in ("true", "false") and "\n" not in v:
            keys.append(k)
        elif "\n" in v and len(v) <= 1_048_576:  # etcd caps an object at 1 MiB, so this scans every value; the old 20,000-character cap left large config files unchecked
            for m in _LINE_RE.finditer(v):
                val = m.group(2).strip("\"'")
                if val.startswith(("${", "$(", "/", "<", "{{")) or val.lower() in ("changeme", "password", "null", "none") or "secretkeyref" in val.lower():
                    continue
                keys.append(f"{k}:{m.group(1)}")
                if len(keys) >= limit:
                    break
        if len(keys) >= limit:
            break
    return list(dict.fromkeys(keys))[:limit]  # dedupe (the same password line can appear in several blocks) while keeping order


def shape(v) -> str:
    """A coarse description of a value, enough for a reader to know what kind of thing was there."""
    s = str(v)
    if s == "":
        return "empty"
    if "\n" in s:
        return "multiline"
    if s.isdigit():
        return "number"
    if s.lower() in ("true", "false"):
        return "bool"
    if s.startswith("/"):
        return "path"
    if _URL_RE.match(s):
        return "url"
    if " " in s.strip():
        return "text"
    return "word"


def scrub_configmap(cm: dict) -> dict:
    """Replace the values of one ConfigMap in place (see module docstring) and record what was there under `kubegap_scrub`."""
    if MARK in cm:
        return cm
    meta = cm.get("metadata") or {}
    ns, name = meta.get("namespace") or "", meta.get("name") or ""
    data = cm.get("data") or {}
    binary = cm.get("binaryData") or {}
    keep = _keys_for(KEEP_VALUES, ns, name)
    presence = _keys_for(PRESENCE_ONLY, ns, name)
    lines = _keys_for(LINE_COUNT_ONLY, ns, name)
    chars = sum(len(str(v)) for v in data.values()) + sum(len(str(v)) for v in binary.values())
    found = secret_like_keys(data)
    ann = meta.get("annotations") or {}
    dropped_ann = []
    for k in COPY_ANNOTATIONS:
        if k in ann:
            found = list(dict.fromkeys(found + _secret_like_in_applied(ann[k])))[:8]
            ann[k] = {"len": len(str(ann[k])), "shape": shape(ann[k])}
            dropped_ann.append(k)
    labels = meta.get("labels") or {}
    sidecar = next((role for label, role in KEEP_BY_LABEL.items() if label in labels), None)
    new_data: dict = {}
    for k, v in data.items():
        if sidecar == "dashboard" and isinstance(v, str) and v.lstrip().startswith("{"):
            new_data[k] = v
            keep = keep | {k}
        elif sidecar == "datasource" and isinstance(v, str):
            new_data[k] = {"datasources": datasource_entries(v), "len": len(v), "shape": shape(v)}
        elif k in keep:
            new_data[k] = v
        elif k in presence:
            new_data[k] = {"present": len(str(v).strip()) > 0, "len": len(str(v))}
        elif k in lines:
            new_data[k] = {"lines": len([ln for ln in str(v).splitlines() if ln.strip()]), "len": len(str(v))}
        else:
            new_data[k] = {"len": len(str(v)), "shape": shape(v)}
    if "data" in cm or new_data:
        cm["data"] = new_data
    if binary:
        cm["binaryData"] = {k: {"len": len(str(v))} for k, v in binary.items()}
    cm[MARK] = {"values_dropped": True, "kept_keys": sorted(k for k in data if k in keep), "data_chars": chars, "secret_like_keys": found, "annotations_dropped": dropped_ann}
    return cm


def datasource_entries(text: str) -> list[dict]:
    """name, type, url and isDefault of each datasource in a Grafana provisioning file (`datasources:` list, grafana/grafana
    pkg/services/provisioning/datasources/types.go:19-23,32-45@v12.2.1). Nothing else of the file is kept."""
    try:
        doc = yamlite.load(text)
    except Exception:
        return []
    rows = (doc or {}).get("datasources") if isinstance(doc, dict) else None
    out = []
    for d in rows or []:
        if isinstance(d, dict) and d.get("name"):
            out.append({"name": str(d.get("name")), "type": d.get("type"), "url": d.get("url"), "isDefault": bool(d.get("isDefault"))})
    return out


def _secret_like_in_applied(value) -> list[str]:
    """Secret-like keys in the `data` of an applied-object copy (plain JSON, or gzip+base64 as the k3s helm-controller writes it). Values are inspected, never returned."""
    import base64
    import gzip
    import io
    import json

    text = str(value)
    if text.startswith("H4sI"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(text))) as gz:
                raw = gz.read(GZIP_MAX_BYTES + 1)
            if len(raw) > GZIP_MAX_BYTES:  # too large to inspect; the caller still replaces the annotation by length and shape
                return []
            text = raw.decode("utf-8", "replace")
        except Exception:
            return []
    try:
        obj = json.loads(text)
    except ValueError:
        return []
    d = obj.get("data") if isinstance(obj, dict) else None
    return secret_like_keys(d if isinstance(d, dict) else {})


class ScrubFailed(shell._NamedError):
    """Scrubbing raised, so the text must not be written. The message starts with "scrub failed:"."""


def scrub_or_error(obj) -> str | None:
    """Scrub `obj` in place. None on success; on any exception the message "scrub failed: <type>: <text>" and the caller writes nothing."""
    try:
        scrub_objects(obj)
    except Exception as e:
        return f"scrub failed: {type(e).__name__}: {e}"
    return None


def json_scrubber():
    """A `shell.run` transform for kubectl JSON output plus the item count it saw.

    Returns (fn, info). `fn(text)` parses the JSON, scrubs it and returns the scrubbed JSON text; text that is not JSON is returned unchanged,
    because the scrubber would find no Secret in it. If scrubbing raises, `fn` raises ScrubFailed and `shell.run` writes nothing.
    `info["items"]` holds the number of items of the parsed List, None when the text was not a JSON object.
    """
    info: dict = {"items": None}

    def fn(text: str) -> str:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        except Exception as e:
            raise ScrubFailed(f"scrub failed: {type(e).__name__}: {e}") from e
        err = scrub_or_error(data)
        if err:
            raise ScrubFailed(err)
        try:
            info["items"] = len(data.get("items", []) or []) if isinstance(data, dict) else None
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            raise ScrubFailed(f"scrub failed: {type(e).__name__}: {e}") from e

    return fn, info


def scrub_objects(obj):
    """Walk kubectl JSON (a single object or a List) and apply the Secret and ConfigMap rules in place. Returns the same object."""
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if isinstance(kind, str) and kind in SECRET_KINDS:
            obj.pop("data", None)
            obj.pop("stringData", None)
            ann = (obj.get("metadata") or {}).get("annotations") or {}
            for k in COPY_ANNOTATIONS:  # a kubectl-applied Secret would keep its values in the copy annotation; Secrets are never fetched, this is the defensive path
                if k in ann:
                    ann[k] = {"len": len(str(ann[k])), "shape": shape(ann[k])}
        elif isinstance(kind, str) and kind in CONFIGMAP_KINDS:
            scrub_configmap(obj)
            return obj
        for v in obj.values():
            scrub_objects(v)
    elif isinstance(obj, list):
        for v in obj:
            scrub_objects(v)
    return obj


def configmap_chars(cm: dict) -> int:
    """Character count of data+binaryData as it was before scrubbing (for the large-ConfigMap check). Falls back to counting the current values on an unscrubbed object."""
    mark = cm.get(MARK)
    if isinstance(mark, dict) and isinstance(mark.get("data_chars"), int):
        return mark["data_chars"]
    return sum(len(str(v)) for v in (cm.get("data") or {}).values()) + sum(len(str(v)) for v in (cm.get("binaryData") or {}).values())


def configmap_secret_like_keys(cm: dict) -> list[str]:
    """The detection recorded on the ConfigMap when it was scrubbed (`kubegap_scrub.secret_like_keys`); every ConfigMap in a snapshot went through scrub_configmap."""
    mark = cm.get(MARK)
    return list(mark["secret_like_keys"]) if isinstance(mark, dict) and isinstance(mark.get("secret_like_keys"), list) else []

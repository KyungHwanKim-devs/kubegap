"""What is dropped from objects before they are written to the snapshot.

The snapshot is read by the agent, and what the agent reads goes to its model API. So the rule is: a value that may hold a
credential is not written to disk at all. Masking after the fact only catches shapes we know; not storing catches everything.

- Secret, SecretList: `data` and `stringData` are removed (names and types stay).
- ConfigMap: every value in `data` is replaced by its length and shape, and `binaryData` by its length. The exceptions are the
  configuration keys kubegap's own parsers read (CoreDNS Corefile, kube-proxy config, local-path-provisioner paths, a few
  Argo CD flags), listed in KEEP_VALUES below. Two Argo CD keys that can carry a client secret are reduced to "present";
  the RBAC policy to its line count. Before the values go, they are inspected once for secret-like keys (the rule of
  `security.plaintext-configmap-secret`) and the resulting key names are stored under `kubegap_scrub`, so the check works
  without the values. Component detection in lib/discover runs on the in-memory objects before this scrub.

Both writers (lib/discover for the kinds it fetches, lib/collect dump-all for the rest) call `scrub_objects`.
"""

from __future__ import annotations

import fnmatch
import re

SECRET_KINDS = {"Secret", "SecretList"}
CONFIGMAP_KINDS = {"ConfigMap"}
MARK = "kubegap_scrub"

# (namespace glob, name glob, keys whose values stay as they are). Only configuration that a kubegap parser reads.
KEEP_VALUES: list[tuple[str, str, tuple[str, ...]]] = [
    ("kube-system", "coredns", ("Corefile", "NodeHosts")),  # lib/coredns.py
    ("kube-system", "kube-proxy-config", ("config",)),  # lib/kubeproxy.py (EKS)
    ("kube-system", "kube-proxy", ("config",)),  # lib/kubeproxy.py
    ("*", "local-path-config", ("config.json",)),  # lib/localpath.py
    ("argocd", "argocd-cm", ("url", "admin.enabled", "timeout.reconciliation", "exec.enabled", "users.anonymous.enabled")),  # lib/argocdctl.py
    ("argocd", "argocd-cmd-params-cm", ("controller.status.processors", "controller.operation.processors", "application.namespaces", "server.insecure")),
    ("argocd", "argocd-rbac-cm", ("policy.default",)),
]
# Keys whose value is reduced to the string "present" (they can embed an OIDC client secret) or to "<n lines>".
PRESENCE_ONLY = [("argocd", "argocd-cm", ("dex.config", "oidc.config"))]
LINE_COUNT_ONLY = [("argocd", "argocd-rbac-cm", ("policy.csv",))]

# Secret-like key detection, moved here from lib/security.py so it can run before the values are dropped.
SECRET_ENV_RE = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_KEY|CLIENT_SECRET|DSN|CONNECTION_STRING)", re.IGNORECASE)
ENV_SKIP_RE = re.compile(r"(_FILE|_PATH|_DIR|_NAME|_KEY_ID|_REF|_ENABLED|_URL|_HEADER|_TTL|_LENGTH|_EXPIRY|_TIMEOUT)$", re.IGNORECASE)
# A line inside a config file such as `HTTP_Passwd xxx`, `password: xxx`, `DB_PASSWORD=xxx`. The key may start with the secret word itself (the earlier form required one leading character and missed a bare `password = ...`).
_LINE_RE = re.compile(r"(?im)^\s*([A-Za-z0-9_.-]*(?:passw(?:or)?d|secret|token|api[_-]?key)[A-Za-z0-9_.-]*)\s*[:= ]\s*(\S{8,})\s*$")
_URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


def _keys_for(table: list[tuple[str, str, tuple[str, ...]]], ns: str, name: str) -> set[str]:
    out: set[str] = set()
    for pns, pname, keys in table:
        if fnmatch.fnmatchcase(ns, pns) and fnmatch.fnmatchcase(name, pname):
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
    new_data: dict = {}
    for k, v in data.items():
        if k in keep:
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
    cm[MARK] = {"values_dropped": True, "kept_keys": sorted(k for k in data if k in keep), "data_chars": chars, "secret_like_keys": found}
    return cm


def scrub_objects(obj):
    """Walk kubectl JSON (a single object or a List) and apply the Secret and ConfigMap rules in place. Returns the same object."""
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if isinstance(kind, str) and kind in SECRET_KINDS:
            obj.pop("data", None)
            obj.pop("stringData", None)
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
    """The recorded detection on a scrubbed ConfigMap; computed on the spot for an unscrubbed one (older snapshots)."""
    mark = cm.get(MARK)
    if isinstance(mark, dict) and isinstance(mark.get("secret_like_keys"), list):
        return list(mark["secret_like_keys"])
    return secret_like_keys(cm.get("data") or {})

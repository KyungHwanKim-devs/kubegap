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
- A container environment variable whose name looks like a credential (SECRET_ENV_RE, not ENV_SKIP_RE), wherever an `env` list
  appears (Pods, workload templates, ControllerRevision data, Jobs): its `value` is removed and replaced by `kubegap_scrub` with
  the value's length and shape and the verdict of `security.plaintext-env-secret` (env_secret_like), worked out before the value goes.
  Variables of other names keep their values, which readers such as lib/summaries/karpenterctl parse.
- Every other object's `kubectl.kubernetes.io/last-applied-configuration` holds a copy of the manifest, environment values included.
  It is reduced to the JSON of its apiVersion and kind, which is all lib/foundations/lastapplied hands to pluto.

The three writers of kubectl JSON go through `scrub_or_error`: lib/collection/discover for the kinds it fetches, lib/collection/collect dump-all for the rest, and
the `type: kubectl` steps through `json_scrubber`, which lib/foundations/shell applies before the file exists. A scrub that raises writes nothing and fails the step.
"""

from __future__ import annotations

import hashlib
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
# AUTH at the end of a name is a credential in the images that take one that way, e.g. NEO4J_AUTH="neo4j/<password>" (neo4j docker image).
SECRET_ENV_RE = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_KEY|CLIENT_SECRET|DSN|CONNECTION_STRING|AUTH$)", re.IGNORECASE)
ENV_SKIP_RE = re.compile(r"(_FILE|_PATH|_DIR|_NAME|_KEY_ID|_REF|_ENABLED|_URL|_HEADER|_TTL|_LENGTH|_EXPIRY|_TIMEOUT)$", re.IGNORECASE)
# A line inside a config file such as `HTTP_Passwd xxx`, `password: xxx`, `DB_PASSWORD=xxx`. The key may start with the secret word itself (the earlier form required one leading character and missed a bare `password = ...`).
_LINE_RE = re.compile(r"(?im)^\s*([A-Za-z0-9_.-]*(?:passw(?:or)?d|secret|token|api[_-]?key)[A-Za-z0-9_.-]*)\s*[:= ]\s*(\S{8,})\s*$")
_URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
# The right-hand side of a line of code that reads the value from somewhere else: a name, optionally dotted, called or indexed
# (`os.environ["DISCORD_BOT_TOKEN"]`, `os.getenv("X")`, `env("x_secret"),`, `load_token()`). A credential written into the file is a literal,
# and a literal does not start with a name that is then called or indexed and closed.
_CODE_READ_RE = re.compile(r"^[A-Za-z_][\w.]*[(\[].*[)\]][,;]?$")
_ENV_REF_RE = re.compile(r"\$\([A-Za-z_][A-Za-z0-9_]*\)")  # dependent environment variable syntax: the value is another variable's


def _keys_for(table: list[tuple[str, str, tuple[str, ...]]], ns: str, name: str) -> set[str]:
    out: set[str] = set()
    for pns, pname, keys in table:
        if match_name(f"{pns}/{pname}", ns, name):
            out |= set(keys)
    return out


def secret_like_keys(data: dict) -> list[str]:
    """Key names (or `key:line-key` inside config files) whose value looks like a credential, all of them. Values are inspected but never returned."""
    keys: list[str] = []
    for k, v in (data or {}).items():
        v = str(v)
        if SECRET_ENV_RE.search(k) and not ENV_SKIP_RE.search(k) and len(v) >= 8 and not v.isdigit() and not v.startswith("/") and v.lower() not in ("true", "false") and "\n" not in v:
            keys.append(k)
        elif "\n" in v and len(v) <= 1_048_576:  # etcd caps an object at 1 MiB, so this scans every value; the old 20,000-character cap left large config files unchecked
            for m in _LINE_RE.finditer(v):
                if _CODE_READ_RE.match(m.group(2)):
                    continue
                val = m.group(2).strip("\"'")
                if val.startswith(("${", "$(", "/", "<", "{{")) or val.lower() in ("changeme", "password", "null", "none") or "secretkeyref" in val.lower():
                    continue
                if ENV_SKIP_RE.search(m.group(1)) or m.group(1).lower().endswith(("name", "ref", "path", "file")):  # secretName, tokenPath: where a secret is, not the secret (istio-sidecar-injector's template)
                    continue
                keys.append(f"{k}:{m.group(1)}")
    return list(dict.fromkeys(keys))  # dedupe (the same password line can appear in several blocks) while keeping order


def env_name_secret_like(name: str) -> bool:
    """A variable name that may carry a credential, so its value is not written (the name rule of security.plaintext-env-secret)."""
    return bool(SECRET_ENV_RE.search(name)) and not ENV_SKIP_RE.search(name)


def env_secret_like(name: str, value) -> bool:
    """Whether an env entry's literal value looks like a credential. Numeric limits (TOKEN_CAP), flags (ALLOW_EMPTY_PASSWORD=yes), paths and
    short values are not; neither is Reloader's STAKATER_* variable, which names a Secret to watch."""
    v = str(value)
    if not v or v == "None" or v.startswith("/") or v.isdigit() or v.lower() in ("true", "false", "yes", "no", "on", "off") or len(v) < 8:
        return False
    if name.startswith("STAKATER_"):
        return False
    if _ENV_REF_RE.fullmatch(v):  # `$(REDIS_PASSWORD)`: Kubernetes expands it from another variable of the container, which may come from a Secret
        return False
    return env_name_secret_like(name)


# Namespaces of the platform and its add-ons. A run that does not collect the unit app-settings (collectors/units.yaml; the daily run) keeps command,
# args, literal environment values and ConfigMap keys only here: the checks that read one read it from a component (Karpenter feature gates, VPC CNI
# warm targets, MetalLB speaker settings, the flags of a controller), and an application's configuration is the user's own.
SYSTEM_NS_PREFIX = ("kube-", "karpenter", "monitoring", "cert-manager", "external-secrets", "ingress-nginx", "metallb-system", "keda", "argocd", "arc-system", "arc-systems", "logging", "reloader")


def system_namespace(ns) -> bool:
    return isinstance(ns, str) and ns.startswith(SYSTEM_NS_PREFIX)


# What a check asks of a command without reading it: whether it is a shell running a script (`sh -c …`: the shell is PID 1 and does not pass SIGTERM on)
# and whether it only holds the container open (a prepull DaemonSet that sleeps). Worked out before a command is dropped and kept under MARK, as the
# verdict of a credential-like variable is, so the checks give the same answer when the command itself is not written.
SHELLS = ("sh", "/bin/sh", "bash", "/bin/bash", "/usr/bin/bash", "ash", "/bin/ash")
_HOLDER_RE = re.compile(r"\b(sleep|pause|tail -f)\b")


def command_shape(c: dict) -> dict:
    """`{"shell": bool, "holder": bool, "digest": str | None}` of a container's (or an exec probe's) command and args: from the lists when they are
    there, from what the scrub recorded when it dropped them. The digest tells two commands apart, and the same command in two runs, without the text."""
    mark = c.get(MARK)
    if isinstance(mark, dict) and isinstance(mark.get("command_shape"), dict):
        return dict(mark["command_shape"])
    command, args = [str(a) for a in c.get("command") or []], [str(a) for a in c.get("args") or []]
    if not command and not args:
        return {"shell": False, "holder": False, "digest": None}
    digest = hashlib.sha256(json.dumps([command, args], ensure_ascii=False).encode()).hexdigest()[:16]
    return {"shell": bool(command) and command[0] in SHELLS and "-c" in command + args, "holder": bool(_HOLDER_RE.search(" ".join(command + args))), "digest": digest}


def scrub_env(env: list, *, every: bool = False) -> None:
    """Drop the value of each credential-like variable of one `env` list, keeping its length, shape and verdict under MARK. With `every` (a daily
    run, outside the system namespaces) every literal value is dropped, whatever the name."""
    for e in env:
        if isinstance(e, dict) and "value" in e and isinstance(e.get("name"), str) and (every or env_name_secret_like(e["name"])):
            v = e.pop("value")
            e[MARK] = {"len": len(str(v)), "shape": shape(v), "secret_like": env_secret_like(e["name"], v)}


def entry_secret_like(e: dict) -> bool:
    """The verdict recorded for one env entry when its value was dropped. An entry without MARK has a name that is not credential-like."""
    mark = e.get(MARK)
    return isinstance(mark, dict) and bool(mark.get("secret_like"))


def _reduce_applied(ann: dict) -> None:
    """Keep only apiVersion and kind of a last-applied copy, as JSON text, so lib/foundations/lastapplied reads it as before."""
    text = ann.get(LAST_APPLIED)
    if not isinstance(text, str):
        return
    try:
        manifest = json.loads(text)
    except ValueError:
        manifest = None
    if isinstance(manifest, dict):
        ann[LAST_APPLIED] = json.dumps({"apiVersion": manifest.get("apiVersion"), "kind": manifest.get("kind")}, separators=(",", ":"))
    else:
        ann[LAST_APPLIED] = {"len": len(text), "shape": shape(text)}


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


def scrub_configmap(cm: dict, *, app_settings: bool = True) -> dict:
    """Replace the values of one ConfigMap in place (see module docstring) and record what was there under `kubegap_scrub`. Without `app_settings`
    a ConfigMap outside the system namespaces keeps no key either: its name, labels and size are what a daily run knows of it."""
    if MARK in cm:
        return cm
    meta = cm.get("metadata") or {}
    ns, name = meta.get("namespace") or "", meta.get("name") or ""
    data = cm.get("data") or {}
    binary = cm.get("binaryData") or {}
    if not app_settings and not system_namespace(ns):
        ann = meta.get("annotations") or {}
        dropped_ann = [k for k in COPY_ANNOTATIONS if k in ann]
        for k in dropped_ann:
            ann[k] = {"len": len(str(ann[k])), "shape": shape(ann[k])}
        chars = sum(len(str(v)) for v in data.values()) + sum(len(str(v)) for v in binary.values())
        cm.pop("data", None)
        cm.pop("binaryData", None)
        cm[MARK] = {"values_dropped": True, "keys_dropped": len(data) + len(binary), "data_chars": chars, "annotations_dropped": dropped_ann}
        return cm
    keep = _keys_for(KEEP_VALUES, ns, name)
    presence = _keys_for(PRESENCE_ONLY, ns, name)
    lines = _keys_for(LINE_COUNT_ONLY, ns, name)
    chars = sum(len(str(v)) for v in data.values()) + sum(len(str(v)) for v in binary.values())
    found = secret_like_keys(data)
    ann = meta.get("annotations") or {}
    dropped_ann = []
    for k in COPY_ANNOTATIONS:
        if k in ann:
            found = list(dict.fromkeys(found + _secret_like_in_applied(ann[k])))
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


def scrub_or_error(obj, *, app_settings: bool = True) -> str | None:
    """Scrub `obj` in place. None on success; on any exception the message "scrub failed: <type>: <text>" and the caller writes nothing."""
    try:
        scrub_objects(obj, app_settings=app_settings)
    except Exception as e:
        return f"scrub failed: {type(e).__name__}: {e}"
    return None


def json_scrubber(*, app_settings: bool = True):
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
        err = scrub_or_error(data, app_settings=app_settings)
        if err:
            raise ScrubFailed(err)
        try:
            info["items"] = len(data.get("items", []) or []) if isinstance(data, dict) else None
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            raise ScrubFailed(f"scrub failed: {type(e).__name__}: {e}") from e

    return fn, info


def scrub_objects(obj, *, app_settings: bool = True, _ns=None):
    """Walk kubectl JSON (a single object or a List) and apply the Secret and ConfigMap rules in place. Returns the same object. With
    `app_settings` false (the run does not collect that unit) nothing an application is configured with is kept outside the system namespaces:
    every literal environment value goes, not only the credential-like ones, and so does every `command` and `args` list, of a container, a
    probe or a hook; the number of items and `command_shape` stay under `kubegap_scrub`, so "has a command", "is a shell script", "only sleeps"
    and "the same command as before" remain readable."""
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if isinstance(kind, str) and isinstance(obj.get("metadata"), dict):
            _ns = obj["metadata"].get("namespace") or _ns
        if isinstance(kind, str) and kind in SECRET_KINDS:
            obj.pop("data", None)
            obj.pop("stringData", None)
            ann = (obj.get("metadata") or {}).get("annotations") or {}
            for k in COPY_ANNOTATIONS:  # a kubectl-applied Secret would keep its values in the copy annotation; Secrets are never fetched, this is the defensive path
                if k in ann:
                    ann[k] = {"len": len(str(ann[k])), "shape": shape(ann[k])}
        elif isinstance(kind, str) and kind in CONFIGMAP_KINDS:
            scrub_configmap(obj, app_settings=app_settings)
            return obj
        meta = obj.get("metadata")
        if isinstance(kind, str) and isinstance(meta, dict) and isinstance(meta.get("annotations"), dict):
            _reduce_applied(meta["annotations"])
        bare = not app_settings and not system_namespace(_ns)
        env = obj.get("env")
        if isinstance(env, list):
            scrub_env(env, every=bare)
        if bare and (isinstance(obj.get("command"), list) or isinstance(obj.get("args"), list)):
            shape_ = command_shape(obj)
            gone = {k: len(obj.pop(k)) for k in ("command", "args") if isinstance(obj.get(k), list)}
            obj[MARK] = {**(obj.get(MARK) if isinstance(obj.get(MARK), dict) else {}), "items_dropped": gone, "command_shape": shape_}
        for v in obj.values():
            scrub_objects(v, app_settings=app_settings, _ns=_ns)
    elif isinstance(obj, list):
        for v in obj:
            scrub_objects(v, app_settings=app_settings, _ns=_ns)
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

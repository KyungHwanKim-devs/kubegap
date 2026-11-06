"""`kubegap grafana-token --create`: make the read-only Grafana token once, when the user picked that at the first-run question (#173 follow-up).

Until now the Grafana datasource and dashboard lists needed a token the user created by hand: a service account in the Grafana UI, a token, a line
in config.yaml. The first-run question offered "Show how" and most people skipped it. This module does those three steps, once, and only when
the user chose "Create now" in the choice window. It is the one place in kubegap that departs from two rules, and it says so in the docs:

1. It reads one Secret value: the Grafana admin password, from the Secret the Grafana workload itself names in `GF_SECURITY_ADMIN_PASSWORD`
   (grafana/helm-charts charts/grafana/templates/_pod.tpl:378-383@grafana-8.5.0: `secretKeyRef` to `admin.existingSecret` or the release's
   own Secret, key `admin.passwordKey`, default `admin-password`; the user name the same way from :371-376, key `admin-user`). The value
   stays in this process and is written nowhere: not in setup.json, not in a log, not on stdout.
2. It writes to Grafana, not to Kubernetes: `POST /api/serviceaccounts` with role Viewer and `POST /api/serviceaccounts/<id>/tokens`
   (grafana/grafana pkg/services/serviceaccounts/api/api.go:59,61,66@v12.2.1, the same two routes at :59,64@v10.2.3; the request bodies are
   `CreateServiceAccountForm{name, role}` and `AddServiceAccountTokenCommand{name, secondsToLive}` in pkg/services/serviceaccounts/models.go:54-58,
   107-111@v12.2.1; the token value comes back as `key` of the token handler's response, api/token.go:128,182@v12.2.1). A Viewer service
   account can read and nothing else.

The token goes into config.yaml as `grafana_api_token`, the file mode 0600, through `configedit.set_secret_key` (never through a command
line or the agent's chat). From then on collection uses the token and the admin Secret is not read again. Removing the service account in
Grafana ends the token.

What stops it, each reported with its reason and the "Show how" way out: no `secretKeyRef` on the Grafana workload (the password is set another
way), the kubeconfig user may not read that Secret (the shipped ClusterRole excludes Secrets on purpose; an admin kubeconfig usually may),
Grafana refuses the admin login (a password changed since first start, so the Secret is stale; external auth), or the service account route is not there. Seen on the maintainer's k3s cluster: Grafana 12.2.1 answered 401 "invalid password" to the Secret's value, nothing was created and nothing written.
"""

from __future__ import annotations

import base64
import datetime as _dt
import json
import re
from pathlib import Path

from . import configedit, http, kube
from .portfwd import PortForward

ENV_PASSWORD = "GF_SECURITY_ADMIN_PASSWORD"
ENV_USER = "GF_SECURITY_ADMIN_USER"


def admin_ref(context: str | None, namespace: str, kubeconfig: str | None = None, log=None) -> dict | None:
    """Where the Grafana admin password lives, read from the Grafana workload's env (names only): {workload, container, secret, password_key,
    user_key, user_value}. None when no container in the namespace takes GF_SECURITY_ADMIN_PASSWORD from a Secret."""
    for kind in ("deployments", "statefulsets"):
        items, _r = kube.kubectl_json(["get", kind, "-n", namespace], context=context, timeout=60, id=f"setup.grafana-{kind}", log=log, kubeconfig=kubeconfig)
        for it in (items or {}).get("items") or []:
            spec = ((it.get("spec") or {}).get("template") or {}).get("spec") or {}
            for c in spec.get("containers") or []:
                env = {e.get("name"): e for e in c.get("env") or [] if isinstance(e, dict)}
                pw = ((env.get(ENV_PASSWORD) or {}).get("valueFrom") or {}).get("secretKeyRef") or {}
                if not pw.get("name") or not pw.get("key"):
                    continue
                user = env.get(ENV_USER) or {}
                user_ref = (user.get("valueFrom") or {}).get("secretKeyRef") or {}
                return {
                    "workload": f"{kind[:-1]}/{it['metadata']['name']}",
                    "container": c.get("name"),
                    "secret": pw["name"],
                    "password_key": pw["key"],
                    "user_key": user_ref.get("key") if user_ref.get("name") == pw["name"] else None,
                    "user_value": user.get("value") if "value" in user else None,
                }
    return None


def _read_admin(context: str | None, namespace: str, ref: dict, kubeconfig: str | None, log) -> tuple[str, str] | str:
    """(user, password) from the Secret, or the reason it could not be read. The one Secret read in kubegap; the values never leave this process."""
    sec, r = kube.kubectl_json(["get", "secret", "-n", namespace, ref["secret"]], context=context, timeout=30, id="grafana-token.get-secret", log=log, kubeconfig=kubeconfig)
    if sec is None:
        err = (r.error or r.stderr.strip()[-300:] or "kubectl get secret failed").replace("\n", " ")
        if "forbidden" in err.lower() or "cannot get" in err.lower():
            return f"your kubeconfig user may not read Secret {namespace}/{ref['secret']} ({err}). The shipped ClusterRole excludes Secrets on purpose; run this once with a kubeconfig that may, or pick Show how"
        return f"could not read Secret {namespace}/{ref['secret']}: {err}"
    data = sec.get("data") or {}
    try:
        password = base64.b64decode(data[ref["password_key"]]).decode("utf-8")
    except (KeyError, ValueError, UnicodeDecodeError):
        return f"Secret {namespace}/{ref['secret']} has no readable key {ref['password_key']!r}"
    if ref.get("user_key") and ref["user_key"] in data:
        user = base64.b64decode(data[ref["user_key"]]).decode("utf-8", "replace")
    else:
        user = ref.get("user_value") or "admin"
    return user, password


def _basic(user: str, password: str) -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")}


def create_via_api(base: str, user: str, password: str, account_name: str) -> dict:
    """Create the Viewer service account and one token. Returns {ok, service_account, id, token, error}. The token is in the result for the
    caller to write to the config file and must not be printed."""
    base = base.rstrip("/")
    auth = _basic(user, password)
    name = account_name
    for attempt in range(3):
        r = http.post_json(f"{base}/api/serviceaccounts", {"name": name, "role": "Viewer", "isDisabled": False}, headers=auth)
        if r.status == 409:  # a service account of that name exists: another kubegap run on this machine or another one
            name = f"{account_name}-{attempt + 2}"
            continue
        break
    if not r.ok:
        why = (
            "Grafana refused the admin login: the password in the Secret is not the one Grafana uses. Grafana takes GF_SECURITY_ADMIN_PASSWORD only when it creates the admin user at first start; a password changed in Grafana since, or a Secret regenerated while Grafana kept its database, leaves the Secret stale. Either set Grafana's admin password back to the Secret's value yourself (`grafana cli admin reset-admin-password` in the Grafana pod) and pick Create now again, or pick Show how"
            if r.status in (401, 403)
            else (r.error or f"HTTP {r.status}")
        )
        return {"ok": False, "error": f"POST /api/serviceaccounts: {why}"}
    sa = r.json() or {}
    sa_id = sa.get("id")
    if not isinstance(sa_id, int):
        return {"ok": False, "error": "POST /api/serviceaccounts answered without an id"}
    t = http.post_json(f"{base}/api/serviceaccounts/{sa_id}/tokens", {"name": "kubegap", "secondsToLive": 0}, headers=auth)
    if not t.ok:
        return {"ok": False, "error": f"POST /api/serviceaccounts/{sa_id}/tokens: {t.error or f'HTTP {t.status}'}", "service_account": name, "id": sa_id}
    key = (t.json() or {}).get("key")
    if not isinstance(key, str) or not key:
        return {"ok": False, "error": "the token call answered without a key", "service_account": name, "id": sa_id}
    return {"ok": True, "service_account": name, "id": sa_id, "token": key}


def create(context: str | None, grafana: dict, ref: dict, cfg_path: Path, *, configured_url: str | None = None, kubeconfig: str | None = None, log=None) -> dict:
    """The whole step: read the admin Secret once, reach Grafana (configured URL or a port-forward to the Service setup found), create the
    account and token, write the token to the config file. Returns {ok, service_account, id, config, error}; never the token."""
    svc = grafana.get("service") or {}
    ns = svc.get("namespace")
    if not ns and not configured_url:
        return {"ok": False, "error": "setup did not record a Grafana Service; run `kubegap setup` first"}
    admin = _read_admin(context, ns or ref.get("namespace"), ref, kubeconfig, log)
    if isinstance(admin, str):
        return {"ok": False, "error": admin}
    user, password = admin
    account = "kubegap-" + re.sub(r"[^a-z0-9-]+", "-", (context or "cluster").lower()).strip("-")[:40] + "-" + _dt.date.today().isoformat()
    if configured_url:
        made = create_via_api(configured_url, user, password, account)
    else:
        pf = PortForward(context, ns, svc["name"], svc["port"], kubeconfig=kubeconfig)
        if not pf.start():
            return {"ok": False, "error": f"port-forward to {ns}/{svc['name']}:{svc['port']} failed: {pf.error}"}
        try:
            made = create_via_api(pf.url, user, password, account)
        finally:
            pf.stop()
    del password
    if not made.get("ok"):
        return {"ok": False, "error": made.get("error"), "service_account": made.get("service_account"), "id": made.get("id")}
    try:
        configedit.set_secret_key(cfg_path, "grafana_api_token", made["token"])
    except configedit.ConfigEditError as e:
        return {
            "ok": False,
            "error": f"the token was created (service account {made['service_account']}) but could not be written to {cfg_path}: {e}. Add the line yourself and chmod 600 the file",
            "service_account": made["service_account"],
            "id": made["id"],
        }
    return {"ok": True, "service_account": made["service_account"], "id": made["id"], "config": str(cfg_path)}


def describe(result: dict) -> str:
    if result.get("ok"):
        return f"created Grafana service account {result['service_account']} (Viewer, id {result['id']}) and wrote grafana_api_token to {result['config']} (mode 0600). The admin Secret was read once and not kept. To revoke: delete that service account in Grafana"
    return "not created: " + str(result.get("error")) + (f" (service account {result['service_account']} was created; delete it in Grafana or keep it)" if result.get("service_account") else "")


def _json(obj) -> str:  # for tests and --json
    return json.dumps(obj, ensure_ascii=False)

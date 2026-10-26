"""Minimal kubectl wrapper: find the current context and run kubectl.

The detection and collection steps add more commands, but the entry point needs the context name
before it can name the snapshot folder, so these two live here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import shell
from .runlog import RunLog


def current_context(kubeconfig: str | None = None) -> str | None:
    cmd = ["kubectl", "config", "current-context"]
    if kubeconfig:
        cmd += ["--kubeconfig", kubeconfig]
    r = shell.run(cmd, timeout=10)
    return r.stdout.strip() if r.ok and r.stdout.strip() else None


def kubectl(args: list[str], *, context: str | None, timeout: float = 60, id: str | None = None, log: RunLog | None = None, out_path: Path | None = None, collector: str | None = None, kubeconfig: str | None = None) -> shell.Result:
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    if kubeconfig:
        cmd += ["--kubeconfig", kubeconfig]
    cmd += ["--request-timeout", f"{int(timeout)}s"]
    cmd += args
    return shell.run(cmd, timeout=timeout + 5, id=id, log=log, out_path=out_path, collector=collector)


def kubectl_json(args: list[str], *, context: str | None, timeout: float = 60, **kw) -> tuple[dict | list | None, shell.Result]:
    r = kubectl([*args, "-o", "json"], context=context, timeout=timeout, **kw)
    if not r.ok:
        return None, r
    try:
        return json.loads(r.stdout), r
    except json.JSONDecodeError as e:
        r.error = f"invalid json: {e}"
        return None, r


def context_info(context: str | None, kubeconfig: str | None = None) -> dict:
    """Read the server address, cluster name and auth method of a context from kubeconfig. Primary evidence for EKS detection.

    An EKS kubeconfig has a server matching `*.eks.amazonaws.com`, a cluster name like `arn:aws:eks:<region>:<account>:cluster/<name>`,
    and user auth via the `aws eks get-token` exec plugin (AWS_PROFILE in env). Any one of the three counts as EKS.
    """
    args = ["config", "view", "--minify", "--raw=false"]
    if context:
        args += ["--context", context]
    data, r = kubectl_json(args, context=None, timeout=10, kubeconfig=kubeconfig)
    info: dict = {"context": context, "server": None, "cluster_name": None, "is_eks": False, "eks": None, "auth": None, "error": None}
    if data is None:
        info["error"] = r.error or r.stderr.strip()[-300:]
        return info
    clusters = data.get("clusters") or []
    users = data.get("users") or []
    if clusters:
        c = clusters[0]
        info["server"] = (c.get("cluster") or {}).get("server")
        info["cluster_name"] = c.get("name")
    if users:
        u = users[0].get("user") or {}
        ex = u.get("exec")
        if ex:
            env = {e.get("name"): e.get("value") for e in (ex.get("env") or []) if isinstance(e, dict)}
            info["auth"] = {"type": "exec", "command": ex.get("command"), "args": ex.get("args") or [], "env": env}
        elif u.get("token") or u.get("client-certificate-data") or u.get("client-certificate"):
            info["auth"] = {"type": "token" if u.get("token") else "client-cert"}
    server = info["server"] or ""
    name = info["cluster_name"] or ""
    eks: dict = {}
    m = re.match(r"arn:aws:eks:([a-z0-9-]+):(\d+):cluster/(.+)$", name)
    if m:
        eks = {"region": m.group(1), "account": m.group(2), "name": m.group(3)}
    auth = info["auth"] or {}
    a = auth.get("args") or []
    if "get-token" in a and "eks" in a:
        if "--cluster-name" in a:
            eks.setdefault("name", a[a.index("--cluster-name") + 1])
        if "--region" in a:
            eks.setdefault("region", a[a.index("--region") + 1])
        prof = (auth.get("env") or {}).get("AWS_PROFILE")
        if "--profile" in a:
            prof = a[a.index("--profile") + 1]
        if prof:
            eks["profile"] = prof
    if ".eks.amazonaws.com" in server or eks:
        info["is_eks"] = True
        info["eks"] = eks or {}
    return info

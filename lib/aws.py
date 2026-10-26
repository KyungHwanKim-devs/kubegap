"""AWS CLI wrapper and permission checks. Used only with the EKS profile. No write calls."""

from __future__ import annotations

import json

from . import shell
from .runlog import RunLog


def aws(args: list[str], *, profile: str | None, region: str | None, timeout: float = 60, id: str | None = None, log: RunLog | None = None, out_path=None, collector: str | None = None) -> shell.Result:
    cmd = ["aws", "--output", "json", "--no-cli-pager"]
    if profile:
        cmd += ["--profile", profile]
    if region:
        cmd += ["--region", region]
    cmd += args
    return shell.run(cmd, timeout=timeout, id=id, log=log, out_path=out_path, collector=collector)


def aws_json(args: list[str], **kw) -> tuple[dict | list | None, shell.Result]:
    r = aws(args, **kw)
    if not r.ok:
        return None, r
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}, r
    except json.JSONDecodeError as e:
        r.error = f"invalid json: {e}"
        return None, r


def _why(r: shell.Result) -> str:
    text = (r.error or "") + " " + (r.stderr or "")
    t = text.strip()
    if "AccessDenied" in t or "not authorized" in t or "UnauthorizedOperation" in t:
        return "no permission (AccessDenied)"
    if "ExpiredToken" in t or "expired" in t.lower():
        return "credentials expired"
    if "could not be found" in t or "Unable to locate credentials" in t or ("profile" in t.lower() and "not" in t.lower()):
        return "profile or credentials not found"
    return t[-300:] or "failed"


def check_permissions(profile: str | None, region: str | None, cluster_name: str | None, log: RunLog | None = None) -> dict:
    """Verify permissions with four read calls. Each entry holds ok/why and, on success, one key value.

    1. sts get-caller-identity          - the credentials themselves: account id, caller
    2. eks describe-cluster             - eks:Describe*: version, status, control plane logging settings
    3. ssm describe-instance-information - ssm:DescribeInstanceInformation: number of instances registered in SSM (node OS access)
    4. logs describe-log-groups          - logs:DescribeLogGroups: existence of the /aws/eks/<name>/cluster log group (control plane log collection)
    """
    out: dict = {"profile": profile, "region": region, "cluster_name": cluster_name, "checks": {}}
    kw = {"profile": profile, "region": region, "log": log}

    d, r = aws_json(["sts", "get-caller-identity"], id="setup.aws.sts", **kw)
    out["checks"]["sts:GetCallerIdentity"] = {"ok": d is not None, "why": None if d is not None else _why(r), "account": (d or {}).get("Account"), "arn": (d or {}).get("Arn")}
    if d is None:
        out["usable"] = False
        return out

    if cluster_name:
        d, r = aws_json(["eks", "describe-cluster", "--name", cluster_name], id="setup.aws.describe-cluster", **kw)
        c = (d or {}).get("cluster") or {}
        logging_types = []
        for cl in (c.get("logging") or {}).get("clusterLogging") or []:
            if cl.get("enabled"):
                logging_types += cl.get("types") or []
        out["checks"]["eks:DescribeCluster"] = {
            "ok": d is not None,
            "why": None if d is not None else _why(r),
            "version": c.get("version"),
            "status": c.get("status"),
            "platform_version": c.get("platformVersion"),
            "control_plane_logging": logging_types,
        }
    else:
        out["checks"]["eks:DescribeCluster"] = {"ok": False, "why": "cluster name not found in kubeconfig"}

    d, r = aws_json(["ssm", "describe-instance-information", "--max-results", "50"], id="setup.aws.ssm", **kw)
    infos = (d or {}).get("InstanceInformationList") or []
    out["checks"]["ssm:DescribeInstanceInformation"] = {
        "ok": d is not None,
        "why": None if d is not None else _why(r),
        "registered_instances": len(infos) if d is not None else None,
        "online": sum(1 for i in infos if i.get("PingStatus") == "Online") if d is not None else None,
    }

    prefix = f"/aws/eks/{cluster_name}/cluster" if cluster_name else "/aws/eks/"
    d, r = aws_json(["logs", "describe-log-groups", "--log-group-name-prefix", prefix], id="setup.aws.logs", **kw)
    groups = (d or {}).get("logGroups") or []
    out["checks"]["logs:DescribeLogGroups"] = {
        "ok": d is not None,
        "why": None if d is not None else _why(r),
        "log_group_exists": bool(groups) if d is not None else None,
        "retention_days": groups[0].get("retentionInDays") if groups else None,
    }

    out["usable"] = all(v.get("ok") for k, v in out["checks"].items() if k.startswith(("sts", "eks")))
    return out

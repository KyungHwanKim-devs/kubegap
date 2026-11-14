"""The AWS steps: aws CLI calls with their placeholders and for_each lists, CloudWatch Logs Insights, ALB and CloudWatch metrics. Read-only; EKS only.

Part of the collector (lib/collection/collect): the runner in the package's __init__ dispatches each collect.yaml step to a handler here through
STEP_HANDLERS; every handler has the signature `(ctx: StepContext, st: dict) -> dict`, the per-step entry of collect-result.json.
"""

from __future__ import annotations

from pathlib import Path

from ...foundations.config import Config
from ...foundations.runlog import RunLog
from .. import aws as _aws
from .context import StepContext, parallel


def aws_vars(eks: dict) -> dict:
    import datetime as _dt

    today = _dt.datetime.now(_dt.UTC).date()
    return {
        "cluster": eks.get("name"),
        "region": eks.get("region"),
        "account": eks.get("account"),
        "k8s_version": eks.get("version"),
        "vpc_id": eks.get("vpc_id"),
        "date_30d_ago": (today - _dt.timedelta(days=30)).isoformat(),
        "date_7d_ago": (today - _dt.timedelta(days=7)).isoformat(),
        "date_today": today.isoformat(),
        "date_tomorrow": (today + _dt.timedelta(days=1)).isoformat(),
    }


def aws_lists(eks: dict, inv: dict | None = None) -> dict:
    types = sorted({n.get("instance_type") for n in ((inv or {}).get("nodes") or {}).get("nodes", []) if n.get("instance_type")})
    return {
        "subnet_ids": list(eks.get("subnet_ids") or []),
        "security_groups": list(eks.get("security_groups") or []),
        "nodegroups": list(eks.get("nodegroups") or []),
        "addons": list((eks.get("addons") or {}).keys()),
        "instance_types": types,
        "ecr_repositories": list(eks.get("ecr_repositories") or []),
        "service_codes": ["ec2", "vpc", "elasticloadbalancing", "ebs"],  # service-quotas step
        "instance_ids": sorted(
            {str(n.get("provider_id") or "").rsplit("/", 1)[-1] for n in ((inv or {}).get("nodes") or {}).get("nodes", []) if str(n.get("provider_id") or "").startswith("aws:///")}
        ),  # node EC2 instance ids (for root volume lookup)
    }


def expand_args(template: list, vars_: dict, lists: dict) -> list[str]:
    """Plural placeholders like `{subnet_ids}` expand a list into several arguments; the rest are filled with format."""
    out: list[str] = []
    for a in template:
        a = str(a)
        key = a[1:-1] if a.startswith("{") and a.endswith("}") else None
        if key in lists:
            out.extend(str(x) for x in lists[key])
        else:
            # str.format conflicts with JMESPath braces (--query "Volumes[].{id:VolumeId}"), so only known placeholders are substituted (otherwise every aws step fails with "placeholder has no value")
            for k, v in vars_.items():
                a = a.replace("{" + k + "}", str(v))
            for k, v in lists.items():  # plural placeholders embedded in a string are joined with commas — "Name=attachment.instance-id,Values={instance_ids}"
                if "{" + k + "}" in a:
                    a = a.replace("{" + k + "}", ",".join(str(x) for x in v))
            out.append(a)
    return out


def run_aws_step(st: dict, sid: str, name: str, eks: dict, cfg: Config, snap: Path, log: RunLog, timeout: float, echo, inv: dict | None = None) -> dict:
    vars_ = aws_vars(eks)
    lists = aws_lists(eks, inv)
    prof = cfg.get("aws_profile") or eks.get("profile")
    region = st.get("region") or cfg.get("aws_region") or eks.get("region")  # the pricing API exists only in us-east-1, so a step may pin the region
    items: list = [None]
    if st.get("for_each"):
        src = str(st["for_each"]).split(".")[-1]
        items = lists.get(src, [])
        if not items:
            if echo:
                echo(f"    skipped: {st['for_each']} is empty")
            return {"ok": True, "runs": 0, "note": f"{st['for_each']} is empty"}

    def one(item):
        v = {**vars_, "item": item, "item_safe": str(item).replace("/", "__") if item is not None else ""}  # for file names (ECR repository names contain /: bitnami/kafka)
        if any(k in str(st["args"]) for k in ("{subnet_ids}", "{security_groups}")) and not any(lists[k] for k in ("subnet_ids", "security_groups") if "{" + k + "}" in str(st["args"])):
            return item or sid, {"ok": False, "error": "list is empty"}, None
        missing = [k for k, val in vars_.items() if val in (None, "") and "{" + k + "}" in str(st["args"])]  # e.g. {vpc_id} from an inventory written before it was recorded: AWS would accept Values=None and return an empty list
        if missing:
            return item or sid, {"ok": False, "error": f"placeholder {missing[0]} has no value in the inventory"}, None
        try:
            args = expand_args(st["args"], v, lists)
            out = snap / str(st["out"]).format(**v)
        except KeyError as e:
            return item or sid, {"ok": False, "error": f"placeholder {e} has no value"}, None
        r = _aws.aws(args, profile=prof, region=region, timeout=timeout, id=f"{name}.{sid}" + (f".{item}" if item else ""), log=log, out_path=out, collector=name)
        if not r.ok and st.get("tolerate_errors") and "NotFound" in ((r.stderr or "") + (r.error or "")):
            return item or sid, {"ok": True, "out": None, "error": None, "note": "none (NotFound — normal response)"}, None  # ecr get-lifecycle-policy's LifecyclePolicyNotFoundException means "no policy", not a failure
        rec = {"ok": r.ok, "out": str(out.relative_to(snap)) if r.ok else None, "error": None if r.ok else (r.error or r.stderr.strip()[-200:])}
        if r.ok and _aws.more_to_read(r.stdout):
            rec["at_limit"] = True  # the response carries a token for the next page: the list in the file is not all there is
        line = None if (st.get("tolerate_errors") and not r.ok) else f"    {'saved ' + str(out.relative_to(snap)) if r.ok else 'failed' + (f' ({item})' if item else '') + ': ' + str(rec['error'])[:120]}"
        return item or sid, rec, line

    runs: dict = {}
    for key, rec, line in parallel(one, items):  # for_each items (nodegroups, ECR repositories, instance types) are independent calls
        runs[key] = rec
        if echo and line:
            echo(line)
    # tolerate_errors: for calls where a per-item failure is a normal response (ecr get-lifecycle-policy's LifecyclePolicyNotFoundException = no policy), the step is ok if any item succeeded
    ok = any(x["ok"] for x in runs.values()) if st.get("tolerate_errors") else all(x["ok"] for x in runs.values())
    return {"ok": ok, "runs": len(runs), "failed": sum(1 for x in runs.values() if not x["ok"]), "detail": runs, "at_limit": sorted(str(k) for k, x in runs.items() if x.get("at_limit"))}


def step_cwlogs(ctx: StepContext, st: dict) -> dict:
    from .. import cwlogs as _cw

    eks = ctx.eks
    return _cw.run_file(
        ctx.folder / st["file"],
        ctx.snap / "logs" / "cloudwatch",
        cluster=eks.get("name"),
        profile=ctx.cfg.get("aws_profile") or eks.get("profile"),
        region=ctx.cfg.get("aws_region") or eks.get("region"),
        log=ctx.log,
        collector=ctx.name,
        echo=ctx.echo,
        default_hours=float(st.get("hours", 24)),
    )


def step_alb_metrics(ctx: StepContext, st: dict) -> dict:
    from .. import albmetrics as _alb

    eks = ctx.eks
    return _alb.collect(
        ctx.snap,
        st["out"],
        profile=ctx.cfg.get("aws_profile") or eks.get("profile"),
        region=ctx.cfg.get("aws_region") or eks.get("region"),
        log=ctx.log,
        collector=ctx.name,
        timeout=float(st.get("timeout", 60)),
        hours=int(st.get("hours", 24)),
        echo=ctx.echo,
    )


def step_cw_metrics(ctx: StepContext, st: dict) -> dict:
    from .. import cwmetrics as _cw

    eks = ctx.eks
    return _cw.collect(
        ctx.snap, {**st, "id": st["id"]}, profile=ctx.cfg.get("aws_profile") or eks.get("profile"), region=ctx.cfg.get("aws_region") or eks.get("region"), log=ctx.log, collector=ctx.name, timeout=float(st.get("timeout", 60)), echo=ctx.echo
    )


def step_aws(ctx: StepContext, st: dict) -> dict:
    return run_aws_step(st, st["id"], ctx.name, ctx.eks, ctx.cfg, ctx.snap, ctx.log, float(st.get("timeout", 60)), ctx.echo, inv=ctx.inv)

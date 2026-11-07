"""The node step: a script run on every node through the node command backend (SSM or SSH).

Part of the collector (lib/collection/collect): the runner in the package's __init__ dispatches each collect.yaml step to a handler here through
STEP_HANDLERS; every handler has the signature `(ctx: StepContext, st: dict) -> dict`, the per-step entry of collect-result.json.
"""

from __future__ import annotations

from pathlib import Path

from ...foundations import paths
from ...foundations.config import Config
from ...foundations.runlog import RunLog
from ...foundations.snapshot import write_private
from .context import NODE_BACKENDS, NodeRunner, StepContext, parallel


def run_node_step(st: dict, sid: str, name: str, inv: dict, cfg: Config, snap: Path, log: RunLog, runner: NodeRunner | None, timeout: float, echo) -> dict:
    if runner is None or runner.na.method not in NODE_BACKENDS:
        log.skip(id=f"{name}.{sid}", reason=f"no node command backend ({runner.na.method if runner else '-'})", collector=name)
        if echo:
            echo("    skipped: no node command backend")
        return {"ok": False, "skipped": "no node command backend"}
    req = st.get("requires")
    caps = runner.caps()
    if st.get("script"):
        # Script files (collectors/<collector>/<file>) are sent as is because their line structure matters. SSM takes line-by-line commands, SSH one argument.
        cmd = (paths.COLLECTORS_DIR / name / str(st["script"])).read_text(encoding="utf-8")
    else:
        cmd = " ".join(str(st["cmd"]).split())

    def one(node: str):
        cap = ((caps.get(node) or {}).get("caps") or {}) if caps else {}
        if req and caps and cap.get(req) not in ("yes", "sudo"):
            rec = {"ok": False, "skipped": f"node permission missing ({req}={cap.get(req, '?')}). See deploy/node-access/README.md"}
            log.skip(id=f"{name}.{sid}.{node}", reason=rec["skipped"], collector=name)
            return node, rec, f"    {node}: skipped — {rec['skipped']}"
        r = runner.na.run_on_node(node, cmd, timeout=timeout, id=f"{name}.{sid}", collector=name, step=f"{name}/{sid}")
        if "---Output truncated---" in r.stdout:
            r.stdout += "\n### truncated\n"
        out = snap / str(st["out"]).format(node=node)
        if r.ok or r.stdout:
            write_private(out, r.stdout)
        lines = r.stdout.count("\n")
        rec = {"ok": r.ok, "lines": lines, "out": str(out.relative_to(snap)) if (r.ok or r.stdout) else None, "error": r.error}
        return node, rec, f"    {node}: {'saved ' + rec['out'] + f' ({lines} lines)' if rec['out'] else 'failed: ' + str(r.error)[:120]}"

    runs: dict = {}
    for node, rec, line in parallel(one, runner.select(st.get("nodes", "all"))):  # nodes are independent; SSM/SSH sessions run side by side
        runs[node] = rec
        if echo:
            echo(line)
    return {"ok": all(x.get("ok") for x in runs.values()) if runs else False, "nodes": runs}


def step_node(ctx: StepContext, st: dict) -> dict:
    return run_node_step(st, st["id"], ctx.name, ctx.inv, ctx.cfg, ctx.snap, ctx.log, ctx.node_access, float(st.get("timeout", 60)), ctx.echo)

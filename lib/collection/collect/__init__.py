"""Collection (collect).

For every collector folder listed in `collectors_enabled` of `inventory.json`, read its `collect.yaml` and run the commands.
Each command has a timeout and failure handling; on failure it is logged to run.log and we move on. The LLM is not involved in this stage.
Secrets are never fetched through kubectl. If Secrets are mixed into fetched objects, data and stringData are stripped (defensive). The one tool that touches Secrets is `helm list` (Helm keeps release records there); only its metadata output is stored.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time as _time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ...foundations import paths, yamlite
from ...foundations.config import Config
from ...foundations.runlog import RunLog
from ...foundations.snapshot import remove_stale_temp, write_private
from ..prom import Prometheus
from .cloud_steps import step_alb_metrics, step_aws, step_cw_metrics, step_cwlogs
from .context import CollectState, NodeRunner, StepContext, Stores, step_in_mode
from .http_steps import step_http, step_promql
from .k8s_steps import step_component_logs, step_kubectl, step_kubectl_dump_all, step_pod_metrics
from .node_steps import step_node
from .tool_steps import step_tool

COLLECTOR_WORKERS = 3  # collectors run concurrently; capped so that kubegap's own ~100 LISTs and ~170 PromQL queries do not show up as an apiserver/Prometheus latency spike in the data it is collecting
# ---------- step handlers. Signature: (ctx: StepContext, st: dict) -> dict (the per-step entry in collect-result.json) ----------


# Dispatch table: collect.yaml `type` -> handler. A new step type is one function plus one entry here.
STEP_HANDLERS: dict[str, Callable[[StepContext, dict], dict]] = {
    "kubectl-dump-all": step_kubectl_dump_all,
    "kubectl": step_kubectl,
    "pod-metrics": step_pod_metrics,
    "promql": step_promql,
    "http": step_http,
    "cwlogs": step_cwlogs,
    "node": step_node,
    "alb-metrics": step_alb_metrics,
    "cw-metrics": step_cw_metrics,
    "tool": step_tool,
    "component-logs": step_component_logs,
    "aws": step_aws,
}

# Step types that call a cloud provider API and are only meaningful when the inventory says the cluster runs on that cloud.
# This is the single place where a cloud is gated: a GKE or AKS step type would be registered here with its own cloud key, and
# `_cloud_available` would learn to read that cloud's inventory block (today only `cluster.eks` exists).
CLOUD_STEP_TYPES: dict[str, str] = {"aws": "aws", "cwlogs": "aws", "alb-metrics": "aws", "cw-metrics": "aws"}
_CLOUD_SKIP_REASON = {"aws": "not EKS"}


def _cloud_available(inv: dict, cloud: str) -> bool:
    """Whether the inventory carries the facts a cloud-API step needs (for aws: the `cluster.eks` dict written by discover on EKS)."""
    if cloud == "aws":
        return bool((inv.get("cluster") or {}).get("eks"))
    return False


def run_collector(
    name: str,
    context: str | None,
    cfg: Config,
    inv: dict,
    snap: Path,
    log: RunLog,
    kubeconfig: str | None = None,
    prom: Prometheus | None = None,
    stores: Stores | None = None,
    node_access: NodeRunner | None = None,
    echo=None,
    state: CollectState | None = None,
    mode: str = paths.DEFAULT_MODE,
) -> dict:
    folder = paths.COLLECTORS_DIR / name
    spec_path = folder / "collect.yaml"
    result: dict = {"collector": name, "steps": {}}
    if not spec_path.is_file():
        result["skipped"] = "no collect.yaml (collector not implemented)"
        log.skip(id=f"collector.{name}", reason=result["skipped"], collector=name)
        return result
    steps = yamlite.load_file(spec_path) or []
    ctx = StepContext(name, folder, context, cfg, inv, snap, log, kubeconfig, prom, stores, node_access, echo, state if state is not None else CollectState(), mode)
    for st in steps:
        sid, typ = st["id"], st["type"]
        if echo:
            echo(f"  [{name}] {sid}")
        if not step_in_mode(st, mode):
            result["steps"][sid] = ctx.skip(sid, f"not collected in {mode} mode", {"ok": True, "skipped": f"not collected in {mode} mode", "mode_skipped": True, "out": st.get("out") or st.get("file")})
            continue
        handler = STEP_HANDLERS.get(typ)
        if handler is None:
            result["steps"][sid] = ctx.skip(sid, f"unknown type {typ} (known: {', '.join(STEP_HANDLERS)})")
            continue
        cloud = CLOUD_STEP_TYPES.get(typ)
        if cloud and not _cloud_available(inv, cloud):
            result["steps"][sid] = ctx.skip(sid, _CLOUD_SKIP_REASON[cloud])
            continue
        result["steps"][sid] = handler(ctx, st)
    return result


class Progress:
    """Counts finished collectors and renders the one-line progress text that `collect` prints and writes into INCOMPLETE."""

    def __init__(self, total: int, t_start: float):
        self.total = total
        self.t_start = t_start
        self.finished = 0
        self.last: tuple[str, float] | None = None

    def done(self, name: str, seconds: float, running: list[str]) -> str:
        self.finished += 1
        self.last = (name, seconds)
        return self.text(running)

    def text(self, running: list[str]) -> str:
        elapsed = _time.monotonic() - self.t_start
        return progress_line(self.finished, self.total, elapsed, self.last, running)


def progress_line(finished: int, total: int, elapsed: float, last: tuple[str, float] | None, running: list[str]) -> str:
    """`progress: 7/21 collectors done, elapsed 61 s, last eks-platform 42 s, running core, karpenter`. Stable prefix so a reader can grep it."""
    parts = [f"progress: {finished}/{total} collectors done", f"elapsed {elapsed:.0f} s"]
    if last:
        parts.append(f"last {last[0]} {last[1]:.0f} s")
    if running:
        parts.append("running " + ", ".join(running))
    return ", ".join(parts)


def _write_incomplete(snap: Path, line: str) -> None:
    """INCOMPLETE marks a collection that has not finished; its text is the latest progress line so a waiting session can read how far the run is."""
    write_private(snap / "INCOMPLETE", line + "\nIf this file remains, the snapshot was interrupted.\n")


def step_summary(results: dict, mode: str, seconds_total: float) -> dict:
    """The `_summary` of collect-result.json from the per-collector step records. The key is not a collector name, so consumers skip keys starting with '_'.
    lib/commands/regress rebuilds it after it rewrites step records for the degraded fixture variant."""
    steps = [(cn, sid, st) for cn, cr in results.items() if not cn.startswith("_") for sid, st in ((cr or {}).get("steps") or {}).items()]
    return {
        "mode": mode,
        "collectors": [c for c in results if not c.startswith("_")],
        "steps": len(steps),
        "mode_skipped": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("mode_skipped")],
        "failed": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("ok") is False and not st.get("skipped")],
        "skipped": [f"{cn}.{sid}" for cn, sid, st in steps if isinstance(st, dict) and st.get("skipped") and not st.get("mode_skipped")],
        "seconds_total": seconds_total,
    }


def collect(context: str, cfg: Config, inv: dict, snap: Path, log: RunLog, *, kubeconfig: str | None = None, only: list[str] | None = None, mode: str = paths.DEFAULT_MODE, echo=print) -> dict:
    if mode not in paths.MODES:
        raise ValueError(f"unknown collection mode {mode!r} (expected one of {', '.join(paths.MODES)})")
    log.stage("collect", "start", mode=mode)
    remove_stale_temp(snap)
    write_private(snap / "MODE", mode + "\n")  # read back by paths.snapshot_mode: latest/previous selection stays within one mode
    enabled = inv.get("collectors_enabled") or ["core"]
    if only:
        enabled = [c for c in enabled if c in only]
    results = {}
    t_start = _time.monotonic()
    _write_incomplete(snap, f"progress: 0/{len(enabled)} collectors done, elapsed 0 s")
    prom = Prometheus.connect(context, cfg.url("prometheus"), kubeconfig, log=log)
    if prom is None:
        echo("  Could not connect to Prometheus; all PromQL steps are skipped")
    stores = Stores(context, cfg, inv, kubeconfig, log)
    node_runner = NodeRunner(inv, cfg, log)
    state = CollectState()
    print_lock = threading.Lock()

    running: list[str] = []
    progress = Progress(len(enabled), t_start)

    def run_one(name: str) -> tuple[str, dict, float]:
        # Collectors are independent of each other (a step only reads outputs of earlier steps in the same collector), so they run concurrently.
        # Output lines are buffered per collector and printed as one block when it finishes, so the log stays readable.
        with print_lock:
            running.append(name)
        t_one = _time.monotonic()
        buf: list[str] = []
        res = run_collector(name, context, cfg, inv, snap, log, kubeconfig=kubeconfig, prom=prom, stores=stores, node_access=node_runner, echo=buf.append if echo else None, state=state, mode=mode)
        seconds = _time.monotonic() - t_one
        with print_lock:
            running.remove(name)
            if echo:
                for line in buf:
                    echo(line)
        return name, res, seconds

    try:
        # `core` is submitted first: it is the longest collector (object dump, events, the PromQL list), so starting it first keeps it from becoming the tail of the run
        order = [c for c in enabled if c == "core"] + [c for c in enabled if c != "core"]
        _write_incomplete(snap, progress.text(list(running)))
        with ThreadPoolExecutor(max_workers=COLLECTOR_WORKERS, thread_name_prefix="collector") as pool:
            futures = [pool.submit(run_one, name) for name in order]
            for fut in as_completed(futures):
                name, res, seconds = fut.result()
                results[name] = res
                # One progress line per finished collector, and the same text in INCOMPLETE: whoever waits for the file to disappear reads it to learn how far the run is
                with print_lock:
                    line = progress.done(name, seconds, list(running))
                    _write_incomplete(snap, line)
                    if echo:
                        echo(line)
        results = {name: results[name] for name in enabled}  # keep collect-result.json in the inventory's collector order
    finally:
        if prom:
            prom.close()
        stores.close()
    results["_summary"] = step_summary(results, mode, round(_time.monotonic() - t_start, 1))
    write_private(snap / "collect-result.json", json.dumps(results, ensure_ascii=False, indent=1, default=str))
    with contextlib.suppress(OSError):
        (snap / "INCOMPLETE").unlink()
    log.stage("collect", "end", collectors=len(results) - 1)
    return results

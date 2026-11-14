"""What every step of a collection run shares: the run state, the store connections, the node command runner, the per-collector StepContext, the small thread pool and the mode test.

Part of the collector (lib/collection/collect); the step modules import this and the runner in the package's __init__ builds it.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ...foundations import paths, units
from ...foundations.config import Config
from ...foundations.runlog import RunLog
from ..portfwd import PortForward
from ..prom import Prometheus

ITEM_WORKERS = 4  # parallel items inside one step: AWS for_each calls, per-node commands (PromQL has its own cap, prom.PROMQL_WORKERS)


@dataclass
class CollectState:
    """Mutable state of one collection run, shared by all collectors of that run.

    Kept on an object that `collect()` creates (not a module global) so that two collections in one process — tests, or a
    future multi-context run — do not leak state into each other."""

    proxy_blocked: set = field(default_factory=set)  # contexts where the apiserver pod proxy timed out in this run (pod-metrics goes straight to node curl)
    objects_dump: dict | None = None  # the result of the objects.dump-all step of this run, which is what the pluto step reads and how much of the API that is


class Stores:
    """Open each store (prometheus, alertmanager, loki, grafana) endpoint once and reuse it during collection. A configured URL is used directly without port-forwarding."""

    def __init__(self, context: str | None, cfg: Config, inv: dict, kubeconfig: str | None, log: RunLog):
        self.context, self.cfg, self.kubeconfig, self.log = context, cfg, kubeconfig, log
        self._pf: dict[str, PortForward] = {}
        self._lock = threading.Lock()  # several collectors may ask for the same store at once
        self._url: dict[str, str] = {}
        self._svc = {}
        self.warned_plain_http: set[str] = set()  # hosts already warned about a token over plain http, once per run
        for kind, info in (inv.get("stores") or {}).items():
            if info.get("service"):
                self._svc[kind] = info["service"]

    def url(self, kind: str) -> str | None:
        with self._lock:
            return self._url_locked(kind)

    def _url_locked(self, kind: str) -> str | None:
        if kind in self._url:
            return self._url[kind]
        u = self.cfg.url(kind)
        if u:
            self._url[kind] = u
            return u
        svc = self._svc.get(kind)
        if not svc:
            return None
        pf = PortForward(self.context, svc["namespace"], svc["name"], svc["port"], kubeconfig=self.kubeconfig)
        if not pf.start():
            self.log.note(f"{kind} port-forward failed", error=pf.error)
            return None
        self._pf[kind] = pf
        self._url[kind] = pf.url
        return pf.url

    def close(self):
        for pf in self._pf.values():
            pf.stop()


# The node command backends that collection sends node steps to. `none` is the absence of one.
NODE_BACKENDS = ("ssh", "ssm")


class NodeRunner:
    """For node command steps. Builds the NodeAccess and the capabilities table once and reuses them."""

    def __init__(self, inv: dict, cfg: Config, log: RunLog):
        from ..node import NodeAccess

        self.na = NodeAccess(inv, cfg, log)
        self._caps: dict | None = None
        self.nodes = {n["name"]: n for n in (inv.get("nodes") or {}).get("nodes", [])}

    def caps(self) -> dict:
        if self._caps is None:
            self._caps = self.na.capabilities() if self.na.method == "ssh" else {}
        return self._caps

    def select(self, which: str) -> list[str]:
        names = list(self.nodes)
        if which == "server":
            return [n for n in names if any(r in ("control-plane", "master") for r in self.nodes[n].get("roles", []))] or names[:1]
        if which == "agent":
            return [n for n in names if not any(r in ("control-plane", "master") for r in self.nodes[n].get("roles", []))]
        return names


@dataclass
class StepContext:
    """Everything a step handler may need, bundled so that all `_step_<type>` handlers share one signature `(ctx, st) -> dict`.

    One StepContext is built per collector (`name`, `folder`), and the connections (`prom`, `stores`, `node_access`) and the
    per-run `state` are shared across collectors by `collect()`."""

    name: str
    folder: Path
    context: str | None
    cfg: Config
    inv: dict
    snap: Path
    log: RunLog
    kubeconfig: str | None
    prom: Prometheus | None
    stores: Stores | None
    node_access: NodeRunner | None
    echo: Callable | None
    state: CollectState
    mode: str = paths.DEFAULT_MODE

    def collects(self, unit: str) -> bool:
        """Whether this run's mode collects a unit (collectors/units.yaml). A step that writes more when a second unit is collected asks here."""
        return units.collected(self.mode, unit)

    @property
    def eks(self) -> dict:
        return (self.inv.get("cluster") or {}).get("eks") or {}

    def node_backend_ok(self) -> bool:
        """True when a node command backend exists (NODE_BACKENDS), the precondition for the pod-metrics node-curl fallback."""
        return self.node_access is not None and getattr(getattr(self.node_access, "na", None), "method", None) in NODE_BACKENDS

    def skip(self, sid: str, reason: str, result: dict | None = None) -> dict:
        self.log.skip(id=f"{self.name}.{sid}", reason=reason, collector=self.name)
        return result if result is not None else {"ok": False, "error": reason}


def parallel(fn, items, workers: int | None = None) -> list:
    """Run fn over items in a small thread pool and return the results in input order (collect-result.json stays deterministic). One item → no pool."""
    items = list(items)
    if len(items) <= 1:
        return [fn(it) for it in items]
    with ThreadPoolExecutor(max_workers=min(workers or ITEM_WORKERS, len(items)), thread_name_prefix="step") as pool:
        return list(pool.map(fn, items))

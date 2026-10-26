"""`kubegap setup`: checks dependency tools, context access, Prometheus/Loki/Alertmanager/Grafana connectivity
and AWS permissions (EKS only), and writes the result to `snapshots/<context>/setup.json`.

SKILL.md runs this first every time `/kubegap` is invoked; it can also be run by hand. Exit codes:
0 = collection can proceed, 1 = a required tool is missing or the cluster is unreachable (cannot collect).
"""

from __future__ import annotations

import datetime as _dt
import json
import platform
from pathlib import Path

from . import __version__, aws, kube, monitoring, paths, tools
from . import discover as _discover
from .config import Config
from .runlog import RunLog


def _p(msg: str = "") -> None:
    print(msg, flush=True)


def run_setup(context: str | None, cfg: Config, *, kubeconfig: str | None = None, install: bool | list[str] = False, snapshots_root: Path | None = None, verbose: bool = False) -> tuple[int, dict]:
    """install=False: check only (default). True: install everything missing. List of names: install only those. The install policy is decided by the caller (scripts/kubegap) from config and arguments."""
    started = _dt.datetime.now().astimezone()
    result: dict = {
        "kubegap": __version__,
        "started": started.isoformat(timespec="seconds"),
        "machine": {"os": platform.system(), "release": platform.release(), "python": platform.python_version()},
        "config": {"path": str(cfg.path) if cfg.path else None, "loaded": cfg.loaded, "warnings": cfg.warnings},
    }
    ctx_dir = paths.context_root(context, snapshots_root) if context else None
    log = RunLog((ctx_dir / "setup.log") if ctx_dir else None, echo=verbose)
    if ctx_dir:
        ctx_dir.mkdir(parents=True, exist_ok=True)
        if (ctx_dir / "setup.log").exists():
            (ctx_dir / "setup.log").unlink()
    log.stage("setup", "start", context=context)

    # 1. tools -----------------------------------------------------------------------------------------------
    _p("== 1/4 dependency tools")
    status = tools.check_tools()
    missing = [t for t in status if not t["present"]]
    installs: list[dict] = []
    wanted = [t for t in missing if install is True or (isinstance(install, list) and t["name"] in install)]
    if missing and not wanted:
        # check only: for each missing tool show its role, the checks that would be skipped and how it would be installed. SKILL.md shows this table to the user and asks for consent
        _p("  missing tools (to install: `kubegap setup --install` or `--install-only name,name`):")
        for t in missing:
            tool = tools.by_name(t["name"])
            _p(f"  - {t['name']}{' [required]' if t['required'] else ''}: {t['role']}")
            _p(f"      checks skipped without it: {', '.join(t['checks'])}")
            _p(f"      install method: {tools.install_plan(tool)}")
        _p("")
    for t in wanted:
        tool = tools.by_name(t["name"])
        if not t["installable"]:
            installs.append({"name": t["name"], "method": None, "ok": False, "error": t["note"] or "no install method"})
            _p(f"  - {t['name']}: no install method. {t['note']}")
            continue
        _p(f"  - installing {t['name']}: {tools.install_plan(tool)} ...")
        res = tools.install_tool(tool, log=log)
        installs.append(res)
        _p(f"    {'done (' + str(res.get('method')) + ')' if res['ok'] else 'failed: ' + str(res['error'])[:300]}")
    if wanted:
        status = tools.check_tools()
    result["tools"] = status
    result["installs"] = installs
    result["install_mode"] = "all" if install is True else ("selected" if isinstance(install, list) else "check-only")
    for t in status:
        mark = "present" if t["present"] else ("missing (required)" if t["required"] else "missing")
        ver = f" {t['version']}" if t.get("version") else ""
        _p(f"  {t['name']:<9} {mark}{ver}  — {t['role']}")
    required_missing = [t["name"] for t in status if t["required"] and not t["present"]]
    optional_missing = [t["name"] for t in status if not t["required"] and not t["present"]]
    if optional_missing:
        affected = sorted({c for t in status if t["name"] in optional_missing for c in t["checks"]})
        _p(f"  -> missing optional tools {', '.join(optional_missing)}: their checks ({', '.join(affected)}) will be marked 'tool missing'; everything else proceeds")
    result["required_missing"] = required_missing
    result["optional_missing"] = optional_missing

    # 2. context -------------------------------------------------------------------------------------------
    _p("\n== 2/4 kube context")
    cluster: dict = {"context": context}
    result["cluster"] = cluster
    if not context or "kubectl" in required_missing:
        cluster["reachable"] = False
        cluster["error"] = "no context" if not context else "kubectl missing"
        _p(f"  unreachable: {cluster['error']}")
    else:
        info = kube.context_info(context, kubeconfig)
        cluster.update(info)
        ver, _r = kube.kubectl_json(["version"], context=context, timeout=20, id="setup.version", log=log, kubeconfig=kubeconfig)
        cluster["server_version"] = ((ver or {}).get("serverVersion") or {}).get("gitVersion")
        nodes, r2 = kube.kubectl_json(["get", "nodes"], context=context, timeout=30, id="setup.get-nodes", log=log, kubeconfig=kubeconfig)
        if nodes is None:
            cluster["reachable"] = False
            cluster["error"] = r2.error or r2.stderr.strip()[-300:]
            _p(f"  {context}: access failed: {cluster['error']}")
        else:
            items = nodes.get("items", [])
            versions = sorted({(n.get("status", {}).get("nodeInfo", {}) or {}).get("kubeletVersion", "?") for n in items})
            cluster["reachable"] = True
            cluster["node_count"] = len(items)
            cluster["kubelet_versions"] = versions
            can = kube.kubectl(["auth", "can-i", "list", "pods", "-A"], context=context, timeout=15, id="setup.can-i", log=log, kubeconfig=kubeconfig)
            cluster["can_list_pods"] = can.ok and can.stdout.strip() == "yes"
            # Same platform rule as discover (kubeconfig + node providerID + kubelet version), so setup and inventory.json never disagree. Only the nodes are known here, which that rule allows.
            objs = {"nodes": nodes}
            cluster["platform"], cluster["platform_reasons"] = _discover.detect_platform(info, _discover._node_summary(items), _discover.detect_components(objs, None), objs)
            cluster["is_k3s"] = cluster["platform"] == "k3s"
            _p(f"  {context}: server {cluster.get('server_version')}, {len(items)} nodes ({', '.join(versions)}), detected platform {cluster['platform']}, pods list permission {'yes' if cluster['can_list_pods'] else 'no'}")
            if cluster.get("is_eks"):
                e = cluster.get("eks") or {}
                _p(f"  EKS: name {e.get('name')}, region {e.get('region')}, account {e.get('account')}, AWS profile {e.get('profile')}")

    # 3. monitoring stores --------------------------------------------------------------------------------------
    _p("\n== 3/4 Prometheus · Alertmanager · Loki · Grafana")
    mon: dict = {}
    result["monitoring"] = mon
    if cluster.get("reachable"):
        svcs, err = monitoring.find_services(context, kubeconfig, log=log)
        if err:
            _p(f"  could not list services: {err}")
            mon["error"] = err
        for kind in monitoring.TARGETS:
            cfg_url = cfg.url(kind)
            info = monitoring.connect_and_probe(kind, svcs.get(kind), cfg_url, context, kubeconfig)
            mon[kind] = info
            if info.get("ok"):
                where = cfg_url if info.get("access") == "config" else f"{info['service']['namespace']}/{info['service']['name']}:{info['service']['port']} (port-forward)"
                extra = ""
                if info.get("retention"):
                    extra = f", retention {info['retention']}"
                if info.get("head_series") is not None:
                    extra += f", active series {info['head_series']:,}"
                _p(f"  {kind:<12} connected v{info.get('version')} at {where}{extra}")
            else:
                _p(f"  {kind:<12} missing/failed: {info.get('error')}")
        log.note("monitoring", **dict(mon.items()))
    else:
        _p("  (skipped: cluster unreachable)")

    # 4. AWS ------------------------------------------------------------------------------------------------
    _p("\n== 4/4 AWS permissions (EKS only)")
    if cluster.get("is_eks"):
        if "aws" in [t["name"] for t in status if not t["present"]]:
            result["aws"] = {"usable": False, "why": "aws CLI missing"}
            _p("  aws CLI missing; cannot verify. eks-platform, control plane log and SSM checks will be marked 'tool missing'")
        else:
            e = cluster.get("eks") or {}
            prof = cfg.get("aws_profile") or e.get("profile")
            region = cfg.get("aws_region") or e.get("region")
            a = aws.check_permissions(prof, region, e.get("name"), log=log)
            result["aws"] = a
            for name, c in a["checks"].items():
                detail = {k: v for k, v in c.items() if k not in ("ok", "why") and v not in (None, [], "")}
                _p(f"  {name:<34} {'OK ' if c['ok'] else 'FAIL'} {c['why'] or ''} {json.dumps(detail, ensure_ascii=False) if detail else ''}")
    else:
        result["aws"] = None
        _p("  not EKS; skipped")

    # conclusion ---------------------------------------------------------------------------------------------------
    ok = not required_missing and bool(cluster.get("reachable")) and bool(cluster.get("can_list_pods", True))
    result["ready"] = ok
    result["finished"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    if ctx_dir:
        (ctx_dir / "setup.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        result["path"] = str(ctx_dir / "setup.json")
    log.stage("setup", "end", ready=ok)
    _p("")
    if ok:
        _p(f"Ready. Collection can proceed. Result: {result.get('path')}")
    else:
        why = []
        if required_missing:
            why.append(f"required tools missing: {', '.join(required_missing)}")
        if not cluster.get("reachable"):
            why.append(f"cluster access failed: {cluster.get('error')}")
        elif not cluster.get("can_list_pods", True):
            why.append("no permission to list pods")
        _p(
            "Not ready: " + "; ".join(why),
        )
    return (0 if ok else 1), result

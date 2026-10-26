"""k3s platform summary. Called by summarize to build the k3s section of summary.json. {present: False} when the platform is not k3s.

Inputs:
- objects/nodes.json : annotation k3s.io/node-args (k3s masks tokens as ********) → server/agent arguments (--disable, --tls-san, --node-ip, --server). Readable without node access.
- logs/node/<node>/k3s-platform.txt : section-by-section output of collectors/k3s-platform/k3s-node.sh (unit, check-config, ports, flannel, journald, server, registries, containerd, local-path, disks, thermal)
- objects/pods.json, persistentvolumes.json, services.json, ipaddresspools.metallb.io.json, deployments.json : pod CIDR usage, local-path node-pinned workloads, MetalLB pool remaining, embedded component images
Sections that are empty for lack of permission are recorded in gaps (sudoers stage 2: deploy/node-access/README.md).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import ipaddress
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .controlplane import workload_of
from .nodeos import _int, _kv, _num, parse_sections
from .snapshot import items, load_json

CERT_RE = re.compile(r'msg="([^:"]+): certificate ([^ ]+) \(([A-Za-z]+)\) (is ok|[^,"]+), expires at ([0-9T:Z-]+)"')
LOCAL_PATH_DIR_RE = re.compile(r"/storage/pvc-([0-9a-f-]{36})_([a-z0-9-]+)_(.+)$")
SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)([KMGT]i?)?$")


def _size_mb(s: str | None) -> float | None:
    if not s:
        return None
    m = SIZE_RE.match(str(s).strip())
    if not m:
        return None
    n = float(m.group(1))
    u = m.group(2) or ""
    mult = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024**2, "K": 1 / 1000, "M": 1, "G": 1000, "T": 1000**2, "": 1 / 1024**2}
    return n * mult.get(u, 1)


def _parse_args(args: list[str]) -> dict:
    """k3s argument list → {role, disable[], tls_san[], node_ip, node_external_ip, server_url, flags{}}"""
    out: dict = {"role": args[0] if args else None, "disable": [], "tls_san": [], "node_ip": None, "node_external_ip": None, "server_url": None, "flags": {}}
    i = 1
    while i < len(args):
        a = args[i]
        val = None
        if "=" in a and a.startswith("--"):
            a, val = a.split("=", 1)
        elif i + 1 < len(args) and not str(args[i + 1]).startswith("--"):
            val = args[i + 1]
            i += 1
        i += 1
        if a == "--disable":
            out["disable"] += [x.strip() for x in str(val).split(",") if x.strip()]
        elif a == "--tls-san":
            out["tls_san"].append(val)
        elif a == "--node-ip":
            out["node_ip"] = val
        elif a == "--node-external-ip":
            out["node_external_ip"] = val
        elif a == "--server":
            out["server_url"] = val
        elif a == "--token":
            continue
        else:
            out["flags"].setdefault(a, []).append(val)
    return out


def _parse_server(lines: list[str]) -> dict:
    kv = _kv([ln for ln in lines if "=" in ln and not ln.startswith(" ") and ":" not in ln.split("=")[0]])
    out: dict = {
        "secrets_encryption": kv.get("secrets_encrypt") or None,
        "db_mb": _int(kv.get("db_mb"), None) if kv.get("db_mb") else None,
        "db_kind": kv.get("db_kind") or None,
        "etcd_snapshots": [],
        "certificates": [],
        "certificates_expiring_90d": [],
        "certificates_raw_lines": 0,
    }
    mode = None
    now = _dt.datetime.now(_dt.UTC)
    for ln in lines:
        s = ln.strip()
        if s == "etcd_snapshots:":
            mode = "snap"
            continue
        if s == "db_ls:":
            mode = "ls"
            continue
        if s == "certificates:":
            mode = "cert"
            continue
        if "=" in s and mode != "cert" and not s.startswith("etcd-snapshot"):
            mode = None
        if mode == "snap" and s.startswith("etcd-snapshot"):
            parts = s.split()
            if len(parts) >= 4:
                try:
                    created = _dt.datetime.fromisoformat(parts[3])
                    age_h = round((now - created).total_seconds() / 3600, 1)
                except ValueError:
                    created, age_h = None, None
                out["etcd_snapshots"].append({"name": parts[0], "location": parts[1], "size_mb": round(_int(parts[2]) / 1024**2, 1), "created": parts[3], "age_h": age_h, "offsite": not parts[1].startswith("file://")})
        elif mode == "cert":
            out["certificates_raw_lines"] += 1
            m = CERT_RE.search(s)
            if m:
                try:
                    exp = _dt.datetime.fromisoformat(m.group(5))
                    days = round((exp - now).total_seconds() / 86400)
                except ValueError:
                    days = None
                rec = {"file": m.group(1), "name": m.group(2), "usage": m.group(3), "status": m.group(4), "expires": m.group(5), "days_left": days}
                out["certificates"].append(rec)
                if days is not None and days < 90:
                    out["certificates_expiring_90d"].append(rec)
    snaps = out["etcd_snapshots"]
    if snaps:
        snaps.sort(key=lambda x: x["created"])
        out["snapshot_latest_age_h"] = snaps[-1]["age_h"]
        if len(snaps) >= 2:
            try:
                t = [_dt.datetime.fromisoformat(x["created"]) for x in snaps[-2:]]
                out["snapshot_interval_h"] = round((t[1] - t[0]).total_seconds() / 3600, 1)
            except ValueError:
                pass
        out["snapshots_offsite"] = any(x["offsite"] for x in snaps)
    out["certificates_min_days_left"] = min((c["days_left"] for c in out["certificates"] if c["days_left"] is not None), default=None)
    return out


def _parse_local_path(lines: list[str]) -> dict:
    kv = _kv(lines)
    vols = []
    for ln in lines:
        parts = ln.strip().split("\t") if "\t" in ln else ln.strip().split(None, 1)
        if len(parts) == 2 and _num(parts[0]) is not None and "/storage/" in parts[1]:
            m = LOCAL_PATH_DIR_RE.search(parts[1])
            if m:
                vols.append({"pv": "pvc-" + m.group(1), "namespace": m.group(2), "pvc": m.group(3), "mb": _int(parts[0])})
    return {"total_mb": _int(kv.get("total_mb"), None) if kv.get("total_mb") else None, "volumes": vols}


def _parse_flannel(kv: dict) -> dict:
    st = kv.get("stats", "")
    rx = re.search(r"rx: (\d+) (\d+) (\d+) (\d+)", st)
    tx = re.search(r"tx: (\d+) (\d+) (\d+) (\d+)", st)
    vx = re.search(r"local ([0-9.]+) dev ([a-z0-9]+)", kv.get("vxlan", ""))
    mtu, under = _int(kv.get("mtu"), None) if kv.get("mtu") else None, _int(kv.get("underlay_mtu"), None) if kv.get("underlay_mtu") else None
    return {
        "mtu": mtu,
        "underlay_mtu": under,
        "mtu_ok": (under - mtu == 50) if (mtu and under) else None,
        "local_ip": vx.group(1) if vx else None,
        "underlay_dev": vx.group(2) if vx else None,
        "rx_errors": _int(rx.group(3)) if rx else None,
        "rx_dropped": _int(rx.group(4)) if rx else None,
        "tx_errors": _int(tx.group(3)) if tx else None,
        "tx_dropped": _int(tx.group(4)) if tx else None,
        "ip_forward": kv.get("ip_forward"),
        "br_netfilter": kv.get("br_netfilter"),
        "addrs": kv.get("addrs"),
    }


def _metallb_l2(snap: Path, lb_services: list[dict], node_names: list[str]) -> dict:
    """Which node advertises (leads) which service IP in L2 mode. Input = speaker /metrics read through the pod proxy (metrics/pod/metallb-speaker/*.prom),
    metallb_speaker_announced{ip,node,protocol,service}. available is false when speaker metrics are missing. L2Advertisement nodeSelectors are included too."""
    d = snap / "metrics" / "pod" / "metallb-speaker"
    announced = []
    files = sorted(d.glob("*.prom")) if d.is_dir() else []
    for f in files:
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not ln.startswith("metallb_speaker_announced{"):
                continue
            m = re.match(r"metallb_speaker_announced\{([^}]*)\}\s+([0-9.e+-]+)", ln)
            if not m or float(m.group(2)) < 1:
                continue
            labels = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            announced.append({"ip": labels.get("ip"), "node": labels.get("node"), "protocol": labels.get("protocol"), "service": labels.get("service")})
    errors = []
    cr = load_json(snap / "collect-result.json") or {}
    step = (
        (((cr.get("metallb") or {}).get("steps") or {}).get("metallb-speaker-metrics")) or (((cr.get("k3s-platform") or {}).get("steps") or {}).get("metallb-speaker-metrics")) or {}
    )  # the step moved to the metallb collector (compatibility with older snapshots)
    for pod, r in (step.get("pods") or {}).items():
        if not r.get("ok"):
            errors.append({"pod": pod, "node": r.get("node"), "error": (r.get("error") or "")[:160]})
    advs = []
    for a in items(load_json(snap / "objects" / "l2advertisements.metallb.io.json")):
        sp = a.get("spec") or {}
        advs.append({"name": a["metadata"]["name"], "pools": sp.get("ipAddressPools"), "node_selectors": sp.get("nodeSelectors"), "interfaces": sp.get("interfaces")})
    by_node: Counter = Counter(r["node"] for r in announced if r["node"])
    total = len(announced)
    leader = by_node.most_common(1)[0] if by_node else (None, 0)
    lb_total = len([s for s in lb_services if not s["pending"]])
    return {
        "available": bool(files),
        "source": "metrics/pod/metallb-speaker/*.prom (pod proxy GET)" if files else None,
        "speakers": len(files),
        "speakers_unreadable": errors,
        "announced": announced,
        "announced_total": total,
        "lb_services": lb_total,
        "by_node": dict(by_node),
        "leader_node": leader[0],
        "leader_share": round(leader[1] / total, 2) if total else None,
        "nodes_total": len(node_names),
        "advertisements": advs,
        "pinned_by_selector": any(a.get("node_selectors") for a in advs),
        "note": "In L2 mode one node advertises each service IP. If a single node advertises every IP, its NIC receives all external traffic, and when it dies everything is cut off during failover (about 10 seconds). Intended if pinned with nodeSelectors",
    }


ETCD_TOOK_RE = re.compile(r'"took":"([0-9.]+)(ms|s|µs)"')


def _parse_etcd_slow(path: Path) -> dict | None:
    """Aggregate logs/node/<server>/k3s-etcd-slow-24h.log (k3s-platform collect `k3s-etcd-slow`: 24-hour etcd/kine warn lines, tail 200). Small k3s cluster kine/etcd row."""
    if not path.exists():
        return None
    lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    apply_slow = [ln for ln in lines if "apply request took too long" in ln]
    took_ms = []
    for ln in apply_slow:
        m = ETCD_TOOK_RE.search(ln)
        if m:
            v = float(m.group(1))
            u = m.group(2)
            took_ms.append(v * 1000 if u == "s" else (v / 1000 if u == "µs" else v))
    hours = Counter(ln[:9] for ln in lines)  # "Oct 25 11" — lines per hour (the collect step samples 15 lines per hour; 15 means that hour had more)
    return {
        "lines_24h": len(lines),
        "capped": len(lines) >= 200 or any(v >= 15 for v in hours.values()),
        "hours_with_warn": len(hours),
        "hours_saturated": sorted(h for h, v in hours.items() if v >= 15),
        "by_hour": dict(sorted(hours.items())),
        "apply_slow": len(apply_slow),
        "max_apply_ms": round(max(took_ms), 1) if took_ms else None,
        "apply_over_1s": sum(1 for t in took_ms if t >= 1000),
        "fdatasync_slow": sum(1 for ln in lines if "slow fdatasync" in ln),
        "leader_changes": sum(1 for ln in lines if "leader changed" in ln),
        "request_stats": sum(1 for ln in lines if '"request stats"' in ln),
        "first": lines[0][:15] if lines else None,
        "last": lines[-1][:15] if lines else None,
    }


def _datastore(snap: Path, servers: list[dict]) -> dict:
    """k3s datastore summary (embedded etcd or kine+SQLite): kind, DB size, 24-hour slow request log. The etcd default quota is 2GiB (--etcd-arg quota-backend-bytes)."""
    kinds = {(r.get("server") or {}).get("db_kind") for r in servers if r.get("server")}
    kind = "etcd" if "etcd" in kinds else ("sqlite" if kinds - {None} else None)
    db_mb = max([(r.get("server") or {}).get("db_mb") or 0 for r in servers], default=0) or None
    slow = {}
    for r in servers:
        d = _parse_etcd_slow(snap / "logs" / "node" / r["node"] / "k3s-etcd-slow-24h.log")
        if d:
            slow[r["node"]] = d
    agg = {k: sum((d.get(k) or 0) for d in slow.values()) for k in ("lines_24h", "apply_slow", "apply_over_1s", "fdatasync_slow", "leader_changes", "request_stats", "hours_with_warn")}
    agg["hours_saturated"] = sorted({h for d in slow.values() for h in (d.get("hours_saturated") or [])})
    quota_mb = 2048 if kind == "etcd" else None
    return {
        "kind": kind,
        "servers": [r["node"] for r in servers],
        "db_mb": db_mb,
        "quota_mb": quota_mb,
        "db_ratio": round(db_mb / quota_mb, 3) if (db_mb and quota_mb) else None,
        "slow_by_node": slow,
        "slow_log_nodes": sorted(slow),
        "capped": any(d.get("capped") for d in slow.values()),
        "max_apply_ms": max([d.get("max_apply_ms") or 0 for d in slow.values()], default=None) or None,
        **agg,
        "note": "The slow request log is journalctl -u k3s warn lines over 24 hours, sampled 15 lines per hour (hours_saturated = hours that had more, hours_with_warn = number of hours with any warn — if they cluster around the kubegap collection time, it is our own load). etcd expects apply within 100ms. DB size is du of /var/lib/rancher/k3s/server/db",
    }


def _node_base(n: dict, o: dict, node_ips: set[str]) -> dict:
    """Node record from the k3s.io/node-args annotation (role, --disable, --tls-san, IPs, server URL); adds the node's addresses to node_ips. Reads objects/nodes.json (passed in)."""
    ann = (o.get("metadata") or {}).get("annotations") or {}
    try:
        args = json.loads(ann.get("k3s.io/node-args") or "[]")
    except json.JSONDecodeError:
        args = []
    parsed = _parse_args(args)
    for a in (o.get("status") or {}).get("addresses", []) or []:
        if a.get("type") in ("InternalIP", "ExternalIP") and a.get("address"):
            node_ips.add(a["address"])
    return {
        "node": n["name"],
        "roles": n.get("roles") or [],
        "role": parsed["role"],
        "args": [("--token", "********") and x for x in args],
        "disable": parsed["disable"],
        "tls_san": parsed["tls_san"],
        "node_ip": parsed["node_ip"],
        "node_external_ip": parsed["node_external_ip"],
        "server_url": parsed["server_url"],
        "flags": parsed["flags"],
        "pod_cidr": (o.get("spec") or {}).get("podCIDR"),
        "kubelet_version": ((o.get("status") or {}).get("nodeInfo") or {}).get("kubeletVersion"),
        "gaps": [],
    }


def _node_runtime(rec: dict, sec: dict) -> None:
    """Fills rec from the meta, unit, check-config, ports, flannel and journald sections of logs/node/<node>/k3s-platform.txt."""
    meta = _kv(sec.get("meta", []))
    rec["version"] = meta.get("version") or None
    rec["config_file"] = meta.get("config_file")
    rec["smartctl"] = meta.get("smartctl") == "yes"
    rec["sensors"] = meta.get("sensors") == "yes"
    unit = [ln for ln in sec.get("unit", []) if ln.startswith("unit:")]
    rec["unit"] = {}
    for ln in unit:
        m = re.match(r"unit:(\S+) NRestarts=(\d+) ActiveEnterTimestamp=(.*)", ln.strip())
        if m:
            rec["unit"] = {"name": m.group(1), "restarts": int(m.group(2)), "since": m.group(3).strip()}
    cc = [ln.strip() for ln in sec.get("check-config", []) if ln.strip()]
    rec["check_config"] = {"missing": [ln.split(":")[0].lstrip("- ").strip() for ln in cc if "missing" in ln], "status": next((ln.split(":", 1)[1].strip() for ln in cc if ln.startswith("STATUS")), None)}
    ports = []
    for ln in sec.get("ports", []):
        parts = ln.strip().split()
        if parts:
            addr, _, port = parts[0].rpartition(":")
            ports.append({"addr": addr, "port": _int(port), "proc": parts[1] if len(parts) > 1 else None})
    rec["ports"] = ports
    rec["apiserver_bind"] = sorted({p["addr"] for p in ports if p["port"] == 6443}) or None
    rec["etcd_bind"] = sorted({p["addr"] for p in ports if p["port"] in (2379, 2380)}) or None
    rec["flannel"] = _parse_flannel(_kv(sec.get("flannel", [])))
    jd = _kv(sec.get("journald", []))
    disk = jd.get("disk", "")
    mdisk = re.match(r"([0-9.]+)([KMG])", disk)
    rec["journald"] = {
        "disk_mb": round(float(mdisk.group(1)) * {"K": 1 / 1024, "M": 1, "G": 1024}[mdisk.group(2)]) if mdisk else None,
        "conf": jd.get("conf") or None,
        "k3s_lines_24h": _int(jd.get("k3s_lines_24h"), None) if jd.get("k3s_lines_24h") else None,
        "bounded": bool(jd.get("conf")),
    }


def _node_server_storage(rec: dict, sec: dict) -> None:
    """Fills rec from the server, registries, containerd, local-path, disks and thermal sections of logs/node/<node>/k3s-platform.txt and records sudoers gaps."""
    srv = sec.get("server", [])
    rec["server"] = _parse_server(srv) if any(ln.strip() for ln in srv) else None
    if rec["role"] == "server" and rec["server"]:
        if not rec["server"].get("secrets_encryption"):
            rec["gaps"].append("k3s secrets-encrypt status (sudoers)")
        if not rec["server"]["etcd_snapshots"] and rec["server"].get("db_kind") in (None, "etcd"):
            rec["gaps"].append("k3s etcd-snapshot ls (no sudoers entry or no snapshots)")
        if rec["server"]["certificates_raw_lines"] == 0:
            rec["gaps"].append("k3s certificate check (sudoers)")
    reg = [ln.rstrip() for ln in sec.get("registries", [])]
    rec["registries"] = {
        "mirrors": [ln.strip().rstrip(":") for i, ln in enumerate(reg) if ln.startswith("  ") and not ln.startswith("    ") and i > 0 and "mirrors" in "".join(reg[:i]) and "configs" not in "".join(reg[:i])],
        "auth_configs": [ln.strip().rstrip(":") for i, ln in enumerate(reg) if ln.startswith("  ") and not ln.startswith("    ") and "configs" in "".join(reg[:i])],
        "present": bool(reg),
    }
    ct = _kv([ln.strip().replace(" = ", "=") for ln in sec.get("containerd", []) if "=" in ln])
    rec["containerd"] = {"snapshotter": (ct.get("snapshotter") or "").strip('"') or None, "systemd_cgroup": ct.get("SystemdCgroup"), "private_registry_auth": any("registry.configs" in ln for ln in sec.get("containerd", []))}
    lp = _parse_local_path(sec.get("local-path", []))
    if lp["total_mb"] is None:
        rec["gaps"].append("du /var/lib/rancher/k3s/storage (sudoers)")
    rec["local_path"] = lp
    disks = [ln.strip() for ln in sec.get("disks", []) if ln.strip()]
    rec["disks"] = {"devices": [ln for ln in disks if not ln.startswith("smart:")], "smart": [ln for ln in disks if ln.startswith("smart:")]}
    if not rec["smartctl"]:
        rec["gaps"].append("smartmontools not installed (disk SMART status unavailable)")
    th = {}
    for ln in sec.get("thermal", []):
        m = re.match(r"zone:(\S+)=(\d+)", ln.strip())
        if m:
            th[m.group(1)] = round(int(m.group(2)) / 1000, 1)
    rec["thermal_c"] = th
    rec["thermal_max_c"] = max(th.values(), default=None)


def _nodes(snap: Path, nodes_inv: list[dict]) -> tuple[list[dict], set[str], Counter]:
    """(node records, node IPs, kubelet version counter). Reads objects/nodes.json and logs/node/<node>/k3s-platform.txt per node."""
    node_objs = {n["metadata"]["name"]: n for n in items(load_json(snap / "objects" / "nodes.json"))}
    node_ips: set[str] = set()
    versions: Counter = Counter()
    recs = []
    for n in nodes_inv:
        name = n["name"]
        rec = _node_base(n, node_objs.get(name) or {}, node_ips)
        versions[rec["kubelet_version"] or "?"] += 1
        path = snap / "logs" / "node" / name / "k3s-platform.txt"
        if not path.is_file():
            rec["collected"] = False
            rec["gaps"].append("k3s-platform.txt missing (node access failed or step not run)")
            recs.append(rec)
            continue
        rec["collected"] = True
        sec = parse_sections(path.read_text(encoding="utf-8", errors="replace"))
        _node_runtime(rec, sec)
        _node_server_storage(rec, sec)
        recs.append(rec)
    return recs, node_ips, versions


def _podcidr(recs: list[dict], pods: list[dict]) -> list[dict]:
    """Per-node pod CIDR usage (running non-hostNetwork pods vs usable addresses). Reads objects/pods.json (passed in)."""
    pods_by_node: Counter = Counter(p["spec"].get("nodeName") for p in pods if (p.get("status") or {}).get("phase") == "Running" and not (p["spec"].get("hostNetwork")))
    podcidr = []
    for r in recs:
        if r.get("pod_cidr"):
            try:
                size = ipaddress.ip_network(r["pod_cidr"]).num_addresses - 2
            except ValueError:
                size = None
            podcidr.append({"node": r["node"], "cidr": r["pod_cidr"], "usable": size, "pods": pods_by_node.get(r["node"], 0), "ratio": round(pods_by_node.get(r["node"], 0) / size, 3) if size else None})
    return podcidr


def _stale_server_urls(servers: list[dict], node_ips: set[str], node_names: set[str]) -> list[dict]:
    """Servers whose --server URL points at a host that is no longer a node. Reads nothing (node records are passed in)."""
    stale = []
    for r in servers:
        u = r.get("server_url")
        if u:
            host = re.sub(r"^https?://", "", u).split(":")[0]
            if host not in node_ips and host not in node_names:
                stale.append({"node": r["node"], "server_url": u, "host": host})
    return stale


def _metallb(snap: Path, inv: dict) -> dict:
    """MetalLB pools (size, used, free), LoadBalancer services, pending ones and L2 leadership. Reads objects/ipaddresspools.metallb.io.json, services.json and speaker metrics via _metallb_l2."""
    pools = []
    total_ips = 0
    for p in items(load_json(snap / "objects" / "ipaddresspools.metallb.io.json")):
        n = 0
        for a in (p.get("spec") or {}).get("addresses", []) or []:
            if "-" in a:
                lo, hi = a.split("-", 1)
                with contextlib.suppress(ValueError):
                    n += int(ipaddress.ip_address(hi.strip())) - int(ipaddress.ip_address(lo.strip())) + 1
            else:
                with contextlib.suppress(ValueError):
                    n += ipaddress.ip_network(a.strip(), strict=False).num_addresses
        total_ips += n
        pools.append({"name": p["metadata"]["name"], "addresses": (p.get("spec") or {}).get("addresses"), "size": n, "auto_assign": (p.get("spec") or {}).get("autoAssign", True)})
    lb = []
    for s in items(load_json(snap / "objects" / "services.json")):
        if (s.get("spec") or {}).get("type") == "LoadBalancer":
            ips = [i.get("ip") for i in ((s.get("status") or {}).get("loadBalancer") or {}).get("ingress", []) or [] if i.get("ip")]
            lb.append({"namespace": s["metadata"]["namespace"], "name": s["metadata"]["name"], "ips": ips, "pending": not ips})
    used = len({ip for s in lb for ip in s["ips"]})
    metallb = {"present": bool(pools), "pools": pools, "total_ips": total_ips, "used": used, "free": (total_ips - used) if pools else None, "services": lb, "pending": [s for s in lb if s["pending"]]}
    metallb["l2"] = _metallb_l2(snap, lb, [n["name"] for n in (inv.get("nodes") or {}).get("nodes") or []])
    return metallb


def _local_path(snap: Path, recs: list[dict], pods: list[dict]) -> dict:
    """local-path PVs: which node each is pinned to, usage vs capacity (from the du section), consuming workloads. Reads objects/persistentvolumes.json and objects/pods.json (passed in)."""
    pvc_pods: dict[tuple[str, str], set[str]] = defaultdict(set)
    for p in pods:
        for v in p["spec"].get("volumes") or []:
            c = (v.get("persistentVolumeClaim") or {}).get("claimName")
            if c:
                pvc_pods[(p["metadata"]["namespace"], c)].add(workload_of(f"{p['metadata']['namespace']}/{p['metadata']['name']}"))
    used_mb: dict[tuple[str, str], tuple[int, str]] = {}
    for r in recs:
        for v in (r.get("local_path") or {}).get("volumes", []):
            used_mb[(v["namespace"], v["pvc"])] = (v["mb"], r["node"])
    pinned = []
    over = []
    by_node: Counter = Counter()
    for pv in items(load_json(snap / "objects" / "persistentvolumes.json")):
        spec = pv.get("spec") or {}
        if not (spec.get("hostPath") or spec.get("local") or str(spec.get("storageClassName", "")).startswith("local-path")):
            continue
        cr = spec.get("claimRef") or {}
        node = None
        for t in ((spec.get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms", []) or []:
            for e in t.get("matchExpressions", []) or []:
                if e.get("key") == "kubernetes.io/hostname" and e.get("values"):
                    node = e["values"][0]
        cap_mb = _size_mb((spec.get("capacity") or {}).get("storage"))
        um = used_mb.get((cr.get("namespace"), cr.get("name")))
        rec = {
            "pv": pv["metadata"]["name"],
            "namespace": cr.get("namespace"),
            "pvc": cr.get("name"),
            "node": node,
            "storage_class": spec.get("storageClassName"),
            "capacity_mb": round(cap_mb) if cap_mb else None,
            "used_mb": um[0] if um else None,
            "used_ratio": round(um[0] / cap_mb, 2) if (um and cap_mb) else None,
            "workloads": sorted(pvc_pods.get((cr.get("namespace"), cr.get("name")), [])),
            "phase": (pv.get("status") or {}).get("phase"),
        }
        if um and cap_mb and um[0] > cap_mb:
            over.append(rec)
        pinned.append(rec)
        by_node[node] += 1
    return {
        "pv_count": len(pinned),
        "by_node": dict(by_node),
        "pinned": sorted(pinned, key=lambda x: -(x["used_mb"] or 0)),
        "over_capacity": over,
        "node_total_mb": {r["node"]: (r.get("local_path") or {}).get("total_mb") for r in recs},
    }


def _builtin_images(snap: Path) -> dict:
    """Images of the embedded kube-system components (coredns, local-path, metrics-server, traefik, svclb). Reads objects/deployments.json and daemonsets.json."""
    builtin = {}
    for kind in ("deployments", "daemonsets"):
        for d in items(load_json(snap / "objects" / f"{kind}.json")):
            if d["metadata"]["namespace"] == "kube-system":
                nm = d["metadata"]["name"]
                if any(k in nm for k in ("coredns", "local-path", "metrics-server", "traefik", "svclb")):
                    builtin[nm] = [c.get("image") for c in ((d.get("spec", {}).get("template", {}).get("spec", {}) or {}).get("containers") or [])]
    return builtin


def _disabled_without_replacement(disabled: list[str], comps: set) -> list[str]:
    """Built-ins disabled with --disable that no detected component replaces. Reads inventory components_present (passed in)."""
    replacement = {
        "traefik": [c for c in ("ingress-nginx", "alb-controller", "istio") if c in comps],
        "servicelb": [c for c in ("metallb",) if c in comps],
        "coredns": [],
        "local-storage": [c for c in ("longhorn", "nfs-provisioner", "rook-ceph") if c in comps],
        "metrics-server": [],
    }
    return [d for d in disabled if d in replacement and not replacement[d] and d not in ("coredns", "metrics-server")]


def _cluster(snap: Path, inv: dict, recs: list[dict], node_ips: set[str], versions: Counter) -> dict:
    """Cluster-level view: servers/agents, version skew, apiserver binding, stale server URLs, disabled built-ins, pod CIDRs, MetalLB, local-path, flannel, datastore, journald, gaps. Reads objects/pods.json plus what the sub-helpers read."""
    servers = [r for r in recs if r["role"] == "server" or any(x in ("control-plane", "master") for x in r["roles"])]
    agents = [r for r in recs if r not in servers]
    pods = items(load_json(snap / "objects" / "pods.json"))
    disabled = sorted({d for r in servers for d in r.get("disable", [])})
    return {
        "servers": [r["node"] for r in servers],
        "agents": [r["node"] for r in agents],
        "versions": dict(versions),
        "version_skew": len(versions) > 1,
        "embedded_etcd": any((r.get("server") or {}).get("db_kind") == "etcd" for r in servers) or any("--cluster-init" in " ".join(map(str, r.get("args") or [])) for r in servers),
        "apiserver": {
            "bind_all_nodes": [r["node"] for r in servers if r.get("apiserver_bind") and any(a in ("*", "0.0.0.0", "[::]", "") for a in r["apiserver_bind"])],
            "tls_san": sorted({s for r in servers for s in r.get("tls_san", [])}),
            "external_ips": sorted({r["node_external_ip"] for r in recs if r.get("node_external_ip")}),
        },
        "server_url_stale": _stale_server_urls(servers, node_ips, {r["node"] for r in recs}),
        "disabled_builtins": disabled,
        "disabled_without_replacement": _disabled_without_replacement(disabled, set(inv.get("components_present") or [])),
        "builtin_images": _builtin_images(snap),
        "podcidr": _podcidr(recs, pods),
        "metallb": _metallb(snap, inv),
        "local_path": _local_path(snap, recs, pods),
        "flannel": {r["node"]: r.get("flannel") for r in recs if r.get("flannel")},
        "datastore": _datastore(snap, servers),
        "journald_total_mb": sum((r.get("journald") or {}).get("disk_mb") or 0 for r in recs),
        "check_config_missing": sorted({m for r in recs for m in (r.get("check_config") or {}).get("missing", [])}),
        "gaps": {r["node"]: r["gaps"] for r in recs if r.get("gaps")},
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    platform = (inv.get("cluster") or {}).get("platform")
    if platform not in ("k3s", "rke2"):
        return {"present": False, "note": f"platform {platform}: not k3s"}
    recs, node_ips, versions = _nodes(snap, (inv.get("nodes") or {}).get("nodes", []))
    return {
        "present": True,
        "source": "objects/nodes.json(k3s.io/node-args) + logs/node/<node>/k3s-platform.txt + objects/*",
        "nodes": recs,  # checks' each expects a list (a dict would be treated as a single cluster-level item)
        "cluster": _cluster(snap, inv, recs, node_ips, versions),
    }

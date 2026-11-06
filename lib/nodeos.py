"""Node OS summary. Called by summarize to build the nodeos section of summary.json.

Inputs: logs/node/<node>/os.txt ("### section" text produced on the node by collectors/core/node-os.sh) + logs/node/<node>/kubelet-configz.json
(effective kubelet config read through the apiserver node proxy) + collect-result.json (per-node collection success) + objects/pods.json (pod uid → name).
One record per node. Sections empty for lack of permission go to permission_gaps; SSM 24,000-character truncation is marked truncated. Missing inputs are recorded as "none" and processing continues.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .controlplane import workload_of
from .snapshot import load_json

# `stat -fc %T /sys/fs/cgroup`: cgroup2fs is the unified hierarchy, tmpfs the v1 mount systemd makes; coreutils before 8.26 (Amazon Linux 2 ships 8.22) has no name for the cgroup2 magic and prints it as UNKNOWN (references/sources.md, #127)
CGROUP_FS = {"cgroup2fs": "v2", "tmpfs": "v1", "UNKNOWN (0x63677270)": "v2"}

# source: kubegap's own format, written by collectors/core/node-os.sh (`### <section>` and `key=value` lines)
SECTION_RE = re.compile(r"^### (\S+)\s*$")
# source: kubegap's own format, written by collectors/core/node-os.sh (`### <section>` and `key=value` lines)
KV_RE = re.compile(r"^([A-Za-z0-9_.:-]+)=(.*)$")
# source: kubernetes/kubernetes pkg/kubelet/kuberuntime/helpers.go:198-200@v1.30.14; :223-225@v1.37.2 (a pod's log directory is `<namespace>_<name>_<uid>` under /var/log/pods)
POD_LOG_DIR_RE = re.compile(r"^([a-z0-9-]+)_([a-z0-9.-]+)_([0-9a-f-]{36})$")


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v, default=0) -> int:
    f = _num(v)
    return int(f) if f is not None else default


def parse_sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    cur = "_head"
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
            continue
        out[cur].append(line.rstrip("\n"))
    return dict(out)


def _kv(lines: list[str]) -> dict[str, str]:
    d = {}
    for ln in lines:
        m = KV_RE.match(ln.strip())
        if m:
            d[m.group(1)] = m.group(2).strip()
    return d


# The kernel's oom-kill summary line (mm/oom_kill.c dump_oom_summary): `oom-kill:constraint=CONSTRAINT_MEMCG,...,oom_memcg=/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod<uid>.slice,...,task=<comm>,pid=<n>,uid=<n>`
# cgroup v2 writes the pod uid with underscores inside the slice name; cgroup v1 writes `/kubepods/burstable/pod<uid>/<container id>` with dashes.
# source: torvalds/linux mm/oom_kill.c:441-451@v5.10; :443-453@v6.12 (dump_oom_summary: `oom-kill:constraint=%s,nodemask=%*pbl,cpuset=%s,mems_allowed=%*pbl,oom_memcg=<path>,task_memcg=<path>,task=%s,pid=%d,uid=%d`; `global_oom` in place of oom_memcg for a node-level kill)
_OOM_KILL_RE = re.compile(r"oom-kill:(?P<fields>.*)")
# source: kubernetes/kubernetes pkg/kubelet/cm/cgroup_manager_linux.go:73-74, 86@v1.30.14; :70-71, 83@v1.37.2 (the systemd driver writes `-` of the pod uid as `_` in the slice name); pkg/kubelet/cm/pod_container_manager_linux.go:37@v1.30.14; :38@v1.37.2 (the `pod` prefix)
_OOM_POD_UID_RE = re.compile(r"pod(?P<uid>[0-9a-f]{8}[_-][0-9a-f]{4}[_-][0-9a-f]{4}[_-][0-9a-f]{4}[_-][0-9a-f]{12})")
# source: torvalds/linux mm/oom_kill.c:441-451@v5.10; :443-453@v6.12 (comma-separated key=value fields; nodemask and mems_allowed may hold commas themselves, which only splits those two)
_OOM_FIELD_RE = re.compile(r"(?P<k>[a-z_]+)=(?P<v>[^,]*)")
# source: systemd/systemd src/shared/logs-show.c:379@v249; :404@v252 (`journalctl -o short-iso` starts the line with `%Y-%m-%dT%H:%M:%S%z`; a `dmesg -T` fallback line has a bracketed ctime instead, so the time stays None)
_OOM_TS_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{4}|Z)?)")


def parse_oom_kill(line: str) -> dict | None:
    """One kernel `oom-kill:` line → {time, pod_uid, task, constraint, memcg}. None for any other line. The pod uid comes from oom_memcg, the cgroup that ran out, so a kill inside a pod's cgroup is attributed to that pod even when the victim task name says nothing about it."""
    m = _OOM_KILL_RE.search(line)
    if not m:
        return None
    fields = dict(_OOM_FIELD_RE.findall(m.group("fields")))
    memcg = fields.get("oom_memcg") or fields.get("task_memcg") or ""
    um = _OOM_POD_UID_RE.search(memcg)
    ts = _OOM_TS_RE.match(line.strip())
    return {
        "time": ts.group("ts") if ts else None,
        "pod_uid": um.group("uid").replace("_", "-") if um else None,
        "task": fields.get("task"),
        "constraint": fields.get("constraint"),
        "node_level": fields.get("constraint") not in (None, "CONSTRAINT_MEMCG"),  # CONSTRAINT_NONE is the whole node running out, the subject of node.kernel-oom-node-level
    }


def _parse_kernel(lines: list[str]) -> dict:
    stripped = [ln.strip() for ln in lines]
    kv = _kv([ln for ln in lines if not ln.startswith(" ") and "samples:" not in ln])
    counts = {k[2:]: _int(v) for k, v in kv.items() if k.startswith("c:")}
    samples: list[str] = []
    oom_samples: list[str] = []
    if "samples:" in stripped:
        idx = stripped.index("samples:")
        end = stripped.index("oom_samples:") if "oom_samples:" in stripped else len(lines)
        samples = [ln for ln in lines[idx + 1 : end] if ln.strip()]
    if "oom_samples:" in stripped:
        idx = stripped.index("oom_samples:")
        oom_samples = [ln for ln in lines[idx + 1 :] if ln.strip()]
    src = kv.get("source")
    window = "24 hours (journalctl -k)" if src == "journalctl" else ("since boot (dmesg; journald does not hold 24 hours)" if src == "dmesg" else "unreadable")
    kills = [k for k in (parse_oom_kill(ln) for ln in oom_samples) if k]
    return {
        "source": src,
        "window": window,
        "lines": _int(kv.get("lines")),
        "counts": counts,
        "samples": samples[-40:],
        "oom_samples": oom_samples[-60:],
        "oom_section": "oom_samples:" in stripped,  # False for an os.txt written by the node script before rubric 0.1.66, which kept no oom-kill lines
        "oom_kills": kills,  # one entry per kernel oom-kill line, with the pod uid when the cgroup path carries one. An older node script has no oom_samples section, so this stays empty and the counts above are all there is
        "total_events": sum(v for k, v in counts.items() if k != "oom_cgroup"),
    }


def kernel_oom_kills(snap: Path, nodes: list[str]) -> dict:
    """The container-level OOM kills of the kernel logs of every node whose os.txt was collected: {node: {source, kills[]}}. Shared with lib.resilience, which maps the pod uids to workloads."""
    out: dict = {}
    for name in nodes:
        path = snap / "logs" / "node" / name / "os.txt"
        if not path.is_file():
            continue
        sec = parse_sections(path.read_text(encoding="utf-8", errors="replace"))
        kern = _parse_kernel(sec.get("kernel", []))
        out[name] = {
            "source": kern["source"],
            "window": kern["window"],
            "oom_section": kern["oom_section"],
            "oom_cgroup_count": kern["counts"].get("oom_cgroup") or 0,  # the count the older script already had, for nodes whose lines cannot be attributed
            "kills": [k for k in kern["oom_kills"] if not k["node_level"]],
        }
    return out


def _sysctl_issues(v: dict[str, str], has_search_engine: bool) -> list[str]:
    issues = []
    inst = _int(v.get("fs.inotify.max_user_instances"), -1)
    if 0 <= inst < 512:
        issues.append(f"fs.inotify.max_user_instances={inst} (recommended ≥ 512, k3s docs 8192; nodes with many pods/log collectors hit 'too many open files')")
    watches = _int(v.get("fs.inotify.max_user_watches"), -1)
    if 0 <= watches < 524288:
        issues.append(f"fs.inotify.max_user_watches={watches} (recommended ≥ 524288)")
    som = _int(v.get("net.core.somaxconn"), -1)
    if 0 <= som < 1024:
        issues.append(f"net.core.somaxconn={som} (recommended ≥ 1024; kernel 5.4+ default 4096)")
    pr = (v.get("net.ipv4.ip_local_port_range") or "").split()
    if len(pr) == 2 and _int(pr[1]) - _int(pr[0]) < 28000:
        issues.append(f"net.ipv4.ip_local_port_range={' '.join(pr)} (range {_int(pr[1]) - _int(pr[0])}, recommended ≥ 28000)")
    nr = (v.get("fs.file-nr") or "").split()
    if len(nr) == 3 and _int(nr[2]) > 0 and _int(nr[0]) / _int(nr[2]) > 0.5:
        issues.append(f"fs.file-nr in use {_int(nr[0])}/{_int(nr[2])} ({_int(nr[0]) * 100 // _int(nr[2])}%)")
    mm = _int(v.get("vm.max_map_count"), -1)
    if has_search_engine and 0 <= mm < 262144:
        issues.append(f"vm.max_map_count={mm} (Elasticsearch/OpenSearch runs in this cluster; requires 262144. Without an init container raising it, bootstrap checks fail or it falls back to single-node mode)")
    if v.get("net.ipv4.ip_forward") not in (None, "absent", "1"):
        issues.append(f"net.ipv4.ip_forward={v.get('net.ipv4.ip_forward')} (0 means pod traffic is not routed. Severe)")
    if v.get("net.bridge.bridge-nf-call-iptables") == "0":
        issues.append("net.bridge.bridge-nf-call-iptables=0 (with a bridge CNI such as flannel cni0, same-node Service traffic bypasses iptables/kube-proxy)")
    if v.get("kernel.panic") == "0":
        issues.append("kernel.panic=0 (no automatic reboot after a kernel panic; EKS and k3s default to 10s)")
    return issues


def _parse_cri(lines: list[str]) -> dict:
    kv = _kv(lines)
    cmd = kv.get("cmd", "none")
    out: dict = {"available": cmd != "none", "cmd": cmd}
    if cmd == "none":
        return out
    ver = kv.get("version", "")
    m = re.search(r"RuntimeName:\s*(\S+)\s+RuntimeVersion:\s*(\S+)", ver)
    out["runtime"] = m.group(1) if m else None
    out["version"] = m.group(2) if m else None
    cv = re.search(r"v?(\d+\.\d+\.\d+)", kv.get("crictl", ""))  # `crictl version v1.33.0`, the binary; absent from an os.txt written before rubric 0.1.82
    out["crictl_version"] = cv.group(1) if cv else None
    out["states"] = {k[6:]: _int(v) for k, v in kv.items() if k.startswith("state:")}
    out["images"] = _int(kv.get("images"))
    fs = _load_json_str(kv.get("imagefs"))
    try:
        ifs = (fs or {}).get("status", {}).get("imageFilesystems", [])[0]
        out["imagefs_used_gb"] = round(_int(ifs.get("usedBytes", {}).get("value")) / 1024**3, 1)
        out["imagefs_inodes"] = _int(ifs.get("inodesUsed", {}).get("value"))
        out["imagefs_mount"] = ifs.get("fsId", {}).get("mountpoint")
    except (IndexError, AttributeError, TypeError):
        pass
    conds: dict[str, bool] = {}
    for m in re.finditer(r'"type":"([A-Za-z]+)","status":(true|false)|"status":(true|false),"type":"([A-Za-z]+)"', kv.get("conditions", "")):
        t = m.group(1) or m.group(4)
        s = m.group(2) or m.group(3)
        conds[t] = s == "true"
    out["conditions"] = conds
    out["not_ready"] = [t for t, ok in conds.items() if not ok and t in ("RuntimeReady", "NetworkReady")]
    # top image sizes (node-os.sh images_top: section, "1.23GB<TAB>repo/image:tag")
    imgs = []
    in_imgs = False
    for ln in lines:
        s_ = ln.strip()
        if s_ == "images_top:":
            in_imgs = True
            continue
        if in_imgs:
            if "\t" not in ln or s_.startswith("writable_layers") or "=" in s_.split("\t")[0]:
                in_imgs = False
                continue
            size_s, img = ln.strip().split("\t", 1)
            m2 = re.match(r"([0-9.]+)\s*([kKMGT]?i?B)", size_s)
            if m2:
                n, u = float(m2.group(1)), m2.group(2)
                base = 1024 if "i" in u else 1000  # crictl prints go-units HumanSize: B/kB/MB/GB/TB are decimal, KiB/MiB/GiB/TiB binary
                exp = {"b": 0, "k": 1, "m": 2, "g": 3, "t": 4}[u[0].lower()]
                imgs.append({"image": img, "size_mb": round(n * base**exp / 1024**2)})
    out["images_top"] = imgs
    out["largest_image_mb"] = max([i["size_mb"] for i in imgs], default=None)
    out["images_over_3gb"] = [i["image"] for i in imgs if i["size_mb"] >= 3072]
    layers = []
    mode = False
    for ln in lines:
        s = ln.strip()
        if s == "writable_layers:":
            mode = True
            continue
        if mode:
            parts = s.split("\t") if "\t" in s else s.split(None, 1)
            if len(parts) == 2 and _num(parts[0]) is not None and parts[1].count("/") == 2:
                ns, pod, c = parts[1].split("/")
                layers.append({"namespace": ns, "pod": pod, "container": c, "workload": workload_of(f"{ns}/{pod}"), "mb": _int(parts[0])})
            elif "=" in s:
                mode = False
    out["writable_layers_top"] = layers
    out["writable_layers_total_mb_top10"] = sum(ln["mb"] for ln in layers)
    out["writable_layers_error"] = kv.get("writable_layers_error") or None
    out["writable_layers_available"] = "writable_layers:" in [ln.strip() for ln in lines]
    out["deprecation_warnings"] = conds.get("ContainerdHasNoDeprecationWarnings") is False
    out["systemd_cgroup"] = kv.get("systemd_cgroup") or None
    # containerd 2.x does not print the snapshotter in `crictl info` (the setting moved to the images plugin); the image filesystem mount point names the snapshotter plugin instead:
    # <root>/io.containerd.snapshotter.v1.<name> (containerd/containerd plugin/plugin.go:143@v1.7.29 and containerd/plugin plugin.go:97@v1.0.0 for the URI, services/server/server.go:230@v1.7.29 and cmd/containerd/server/server.go:265, 273@v2.1.4 for the root directory)
    snap_m = re.search(r"io\.containerd\.snapshotter\.v1\.([a-z0-9]+)", out.get("imagefs_mount") or "")
    out["snapshotter"] = kv.get("snapshotter") or (snap_m.group(1) if snap_m else None)
    out["sandbox_image"] = kv.get("sandbox_image") or None
    out["cni_error"] = None if kv.get("cni_error", "OK") in ("OK", "") else kv.get("cni_error")
    return out


def _load_json_str(s: str | None):
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _parse_disk(lines: list[str], uid_to_pod: dict[str, str]) -> tuple[dict, list[dict], list[dict]]:
    mounts: dict[str, dict] = {}
    pod_logs: list[dict] = []
    pod_dirs: list[dict] = []
    mode = None
    containerd_mb = None
    docker_mb = None
    docker_du_denied = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("fs:"):
            kv = dict(p.split("=", 1) for p in s.split()[1:] if "=" in p)
            mnt = kv.get("mount")
            if mnt and mnt not in mounts:
                mounts[mnt] = {
                    "mount": mnt,
                    "dev": kv.get("dev"),
                    "size_gb": round(_int(kv.get("size_kb")) / 1024**2, 1),
                    "avail_gb": round(_int(kv.get("avail_kb")) / 1024**2, 1),
                    "used_pct": _int((kv.get("use") or "").rstrip("%")),
                    "paths": [s.split()[0][3:]],
                }
            elif mnt:
                mounts[mnt]["paths"].append(s.split()[0][3:])
            continue
        if s.startswith("inode:"):
            kv = dict(p.split("=", 1) for p in s.split()[1:] if "=" in p)
            for m in mounts.values():
                if s.split()[0][6:] in m["paths"] and "inode_pct" not in m:
                    m["inode_pct"] = _int((kv.get("iuse") or "").rstrip("%"))
            continue
        if s == "pod_logs_mb:":
            mode = "logs"
            continue
        if s in ("kubelet_pods_mb:", "emptydir_mb:"):
            mode = "dirs"
            continue
        if s.startswith("containerd_mb="):
            containerd_mb = _int(s.split("=", 1)[1], None) if s.split("=", 1)[1] else None
            mode = None
            continue
        if s.startswith("docker_mb="):
            v = s.split("=", 1)[1]
            docker_mb = None if v in ("", "?") else _int(v, None)
            docker_du_denied = v == "?"
            mode = None
            continue
        parts = s.split("\t") if "\t" in s else s.split(None, 1)
        if mode and len(parts) == 2 and _num(parts[0]) is not None:
            mb, path = _int(parts[0]), parts[1]
            base = path.rstrip("/").rsplit("/", 1)[-1]
            if mode == "logs":
                if path.rstrip("/") == "/var/log/pods":
                    mounts.setdefault("_totals", {})["pod_logs_total_mb"] = mb
                    continue
                m = POD_LOG_DIR_RE.match(base)
                if m:
                    pod_logs.append({"namespace": m.group(1), "pod": m.group(2), "uid": m.group(3), "workload": workload_of(f"{m.group(1)}/{m.group(2)}"), "mb": mb})
            else:
                if path.rstrip("/") == "/var/lib/kubelet/pods":
                    mounts.setdefault("_totals", {})["kubelet_pods_total_mb"] = mb
                    continue
                m = re.search(r"/var/lib/kubelet/pods/([0-9a-f-]{36})/volumes/kubernetes\.io~empty-dir$", path)
                base = m.group(1) if m else base
                mounts.setdefault("_totals", {})["emptydir_total_mb"] = mounts.setdefault("_totals", {}).get("emptydir_total_mb", 0) + mb
                ref = uid_to_pod.get(base)
                ns, _, pod = (ref or "/").partition("/")
                pod_dirs.append({"uid": base, "namespace": ns or None, "pod": pod or None, "workload": workload_of(ref) if ref else None, "mb": mb})
    totals = mounts.pop("_totals", {})
    disk = {"mounts": list(mounts.values()), "containerd_mb": containerd_mb, "docker_mb": docker_mb, "docker_du_denied": docker_du_denied, **totals}
    return disk, pod_logs, pod_dirs


def _parse_services(lines: list[str]) -> list[dict]:
    out = []
    for ln in lines:
        parts = ln.strip().split(" ", 1)
        if len(parts) != 2 or "active=" not in parts[1]:
            continue
        kv = {}
        for tok in re.findall(r"(\w+)=((?:(?!\s\w+=).)*)", parts[1]):
            kv[tok[0]] = tok[1].strip()
        since = kv.get("since") or None
        out.append({"unit": parts[0], "active": kv.get("active"), "restarts": _int(kv.get("restarts"), None) if kv.get("restarts", "?") != "?" else None, "since": None if since == "n/a" else since})
    return out


def _parse_updates(lines: list[str]) -> dict:
    kv = _kv(lines)
    upd = kv.get("ubuntu_updates", "")
    total = re.search(r"(\d+) updates? can be applied", upd)
    sec = re.search(r"(\d+) of these updates (?:are|is) (?:a )?standard security", upd)
    rc = kv.get("needs_restarting_rc")
    return {
        "reboot_required": kv.get("reboot_required") == "yes" or rc == "1",
        "updates_total": _int(total.group(1)) if total else None,
        "security_updates": _int(sec.group(1)) if sec else None,
        "needs_restarting_rc": _int(rc, None) if rc else None,
        "ami_release": kv.get("ami_release") or None,
    }


def _parse_time(lines: list[str]) -> dict:
    sync = None
    ntp = None
    for ln in lines:
        s = ln.strip()
        if "synchronized:" in s:
            sync = s.split(":", 1)[1].strip().lower() == "yes"
        elif s.startswith(("NTP service:", "NTP enabled:")):
            ntp = s.split(":", 1)[1].strip()
    kv = _kv(lines)
    return {"synchronized": sync, "ntp": ntp, "chrony": kv.get("chrony") or None}


def _kubelet(path: Path) -> dict:
    d = load_json(path)
    cfg = (d or {}).get("kubeletconfig") if isinstance(d, dict) else None
    if not cfg:
        return {"available": False}
    eh = cfg.get("evictionHard") or {}
    kr, sr = cfg.get("kubeReserved") or {}, cfg.get("systemReserved") or {}
    size = str(cfg.get("containerLogMaxSize") or "10Mi")
    files = _int(cfg.get("containerLogMaxFiles"), 5)
    m = re.match(r"(\d+)(Mi|Gi|Ki)?", size)
    size_mb = _int(m.group(1)) * {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, None: 1}[m.group(2)] if m else 10
    return {
        "available": True,
        "eviction_hard": eh,
        "eviction_soft": cfg.get("evictionSoft") or {},
        "kube_reserved": kr,
        "system_reserved": sr,
        "kube_api_qps": cfg.get("kubeAPIQPS"),
        "kube_api_burst": cfg.get("kubeAPIBurst"),
        "max_pods": cfg.get("maxPods"),
        "serialize_image_pulls": cfg.get("serializeImagePulls"),
        "reserved_missing": not kr and not sr,
        "eviction_memory_missing": "memory.available" not in eh,
        "eviction_hard_empty": not eh,
        "container_log_max_size": size,
        "container_log_max_files": files,
        "log_cap_mb": round(size_mb * files),
        "cgroup_driver": cfg.get("cgroupDriver"),
        "image_gc_high": cfg.get("imageGCHighThresholdPercent"),
        "image_gc_low": cfg.get("imageGCLowThresholdPercent"),
        "fail_swap_on": cfg.get("failSwapOn"),
        "pod_pids_limit": cfg.get("podPidsLimit"),
        "shutdown_grace_period": cfg.get("shutdownGracePeriod"),
        "enforce_node_allocatable": cfg.get("enforceNodeAllocatable"),
    }


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    nodes_inv = (inv.get("nodes") or {}).get("nodes", [])
    cr = load_json(snap / "collect-result.json") or {}
    step = ((cr.get("core") or {}).get("steps") or {}).get("node-os") or {}
    runs = step.get("nodes") or {}
    pods = load_json(snap / "objects" / "pods.json") or {}
    uid_to_pod = {p["metadata"].get("uid"): f"{p['metadata']['namespace']}/{p['metadata']['name']}" for p in pods.get("items", []) if p.get("metadata", {}).get("uid")}
    has_search = bool(re.search(r"elasticsearch|opensearch", json.dumps(inv.get("components_present") or [])))
    out: dict = {
        "source": "logs/node/<node>/os.txt (collectors/core/node-os.sh) + kubelet-configz.json + collect-result.json",
        "nodes_total": len(nodes_inv),
        "collected": [],
        "not_collected": [],
        "nodes": [],
        "pod_logs": [],
        "pod_dirs": [],
    }
    if not nodes_inv:
        out["note"] = "no nodes in inventory"
        return out
    if not step:
        out["note"] = "node-os step did not run (absent from collect-result.json). Either no node command backend or an older collection version"
    cgroup_v = defaultdict(list)
    containerd_v = defaultdict(list)
    kernel_v = defaultdict(list)
    reboot: list[str] = []
    unsynced: list[str] = []
    truncated: list[str] = []
    gaps: dict[str, list[str]] = {}
    ev_total: Counter = Counter()
    sysctl_vals: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for n in nodes_inv:
        name = n["name"]
        path = snap / "logs" / "node" / name / "os.txt"
        run = runs.get(name) or {}
        if not path.is_file():
            reason = run.get("skipped") or run.get("error") or ("node-os step not run" if not step else "os.txt missing")
            out["not_collected"].append({"node": name, "reason": str(reason)[:200]})
            out["nodes"].append({"node": name, "collected": False, "reason": str(reason)[:200]})  # the row stays so the node checks skip this node by name (rule.needs) instead of seeing no node at all
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        sec = parse_sections(text)
        meta = _kv(sec.get("meta", []))
        kern = _parse_kernel(sec.get("kernel", []))
        sysv = _kv(sec.get("sysctl", []))
        cri = _parse_cri(sec.get("cri", []))
        cg = _kv(sec.get("cgroup", []))
        cg_ver = CGROUP_FS.get(cg.get("fs", ""), "unknown")
        disk, pod_logs, pod_dirs = _parse_disk(sec.get("disk", []), uid_to_pod)
        services = _parse_services(sec.get("services", []))
        upd = _parse_updates(sec.get("updates", []))
        tm = _parse_time(sec.get("time", []))
        kubelet = _kubelet(snap / "logs" / "node" / name / "kubelet-configz.json")
        is_root = meta.get("uid") == "0"
        node_gaps = []
        if kern["source"] in (None, "none"):
            node_gaps.append("kernel log (neither journalctl -k nor dmesg allowed)")
        if not cri["available"]:
            node_gaps.append("crictl (containerd state, container count, image size)")
        if "pod_logs_total_mb" not in disk and not is_root:
            node_gaps.append("du /var/log/pods (sudoers step 2)")
        if "emptydir_total_mb" not in disk and not is_root and not pod_dirs:
            node_gaps.append("du /var/lib/kubelet/pods (sudoers step 2)")
        if disk.get("containerd_mb") is None and not is_root:
            node_gaps.append("du of the containerd data path (sudoers step 2)")
        if not kubelet["available"]:
            node_gaps.append("kubelet configz (node proxy permission or kubelet not responding)")
        if cri["available"] and not cri.get("writable_layers_available"):
            node_gaps.append("crictl stats -a (container writable layers — add `k3s crictl stats -a` to sudoers)")
        if disk.get("docker_du_denied"):
            node_gaps.append("du /var/lib/docker (docker is active on this node — add to sudoers)")
        restarts = {s["unit"]: s["restarts"] for s in services if s.get("restarts") is not None}
        active_units = [s["unit"] for s in services if s.get("active") == "active"]
        runtimes = {
            "active": [u for u in active_units if u in ("containerd", "docker", "crio", "k3s", "k3s-agent")],
            "docker_and_containerd": "docker" in active_units and any(u in active_units for u in ("containerd", "k3s", "k3s-agent")),
            "docker_mb": disk.get("docker_mb"),
            "kubelet_runtime": cri.get("runtime"),
        }
        rec = {
            "collected": True,
            "node": name,
            "roles": n.get("roles") or [],
            "backend": run.get("backend") or (inv.get("node_access") or {}).get("method"),
            "meta": {
                "root": is_root,
                "hostname": meta.get("hostname"),
                "kernel": meta.get("kernel"),
                "os": meta.get("os"),
                "uptime_days": round(_num(meta.get("uptime_s"), 0) / 86400, 1),
                "loadavg": meta.get("loadavg"),
                "nproc": _int(meta.get("nproc"), None),
                "mem_total_gb": round(_int(meta.get("mem_total_kb")) / 1024**2, 1),
                # `containerd github.com/containerd/containerd 1.7.29 <sha>` (an rpm build) or `containerd github.com/containerd/containerd/v2 v2.1.4-k3s1 <sha>` (git describe keeps the v)
                "containerd_version": (re.search(r"(?<![\w.])v?(\d+\.\d+\.\d+)", meta.get("containerd", "")) or [None, None])[1] if meta.get("containerd") else cri.get("version"),
                "k3s_version": meta.get("k3s") or None,
                "zombies": _int(meta.get("zombies")),
                "kubelet_rss_mb": round(_int(meta.get("kubelet_rss_kb")) / 1024) if meta.get("kubelet_rss_kb") else None,
                "containerd_rss_mb": round(_int(meta.get("containerd_rss_kb")) / 1024) if meta.get("containerd_rss_kb") else None,
                "k3s_rss_mb": round(_int(meta.get("k3s_rss_kb")) / 1024) if meta.get("k3s_rss_kb") else None,
            },
            "kernel": kern,
            "sysctl": {"values": sysv, "issues": _sysctl_issues(sysv, has_search)},
            "cri": cri,
            "cgroup": {"fs": cg.get("fs"), "version": cg_ver, "controllers": cg.get("controllers") or None},
            "time": tm,
            "disk": disk,
            "services": services,
            "service_restarts": restarts,
            "service_restarts_max": max(restarts.values(), default=0),
            "runtimes": runtimes,
            "writable_layers_top": cri.get("writable_layers_top") or [],
            "writable_layer_max_mb": max((ln["mb"] for ln in cri.get("writable_layers_top") or []), default=None),
            "updates": upd,
            "kubelet": kubelet,
            "permission_gaps": node_gaps,
            "truncated": "### truncated" in text,
        }
        out["nodes"].append(rec)
        out["collected"].append(name)
        for e in pod_logs:
            out["pod_logs"].append({"node": name, **e, "log_cap_mb": kubelet.get("log_cap_mb")})
        for e in pod_dirs:
            out["pod_dirs"].append({"node": name, **e})
        cgroup_v[cg_ver].append(name)
        if rec["meta"]["containerd_version"]:
            containerd_v[rec["meta"]["containerd_version"]].append(name)
        kernel_v[meta.get("kernel") or "?"].append(name)
        if upd["reboot_required"]:
            reboot.append(name)
        if tm["synchronized"] is False:
            unsynced.append(name)
        if rec["truncated"]:
            truncated.append(name)
        if node_gaps:
            gaps[name] = node_gaps
        ev_total.update(kern["counts"])
        for k, v in sysv.items():
            sysctl_vals[k][v].append(name)
    out["pod_logs"].sort(key=lambda e: -e["mb"])
    out["pod_dirs"].sort(key=lambda e: -e["mb"])
    # the two lists hold the largest items found on the nodes that were read; when no node was read they hold nothing, which is not "nothing large": None makes the two checks skip
    out["pod_logs"] = out["pod_logs"][:40] if out["collected"] else None
    out["pod_dirs"] = out["pod_dirs"][:40] if out["collected"] else None
    out["cluster"] = {
        "collected": len(out["collected"]),
        "not_collected": len(out["not_collected"]),
        "cgroup": dict(cgroup_v),
        "containerd_versions": dict(containerd_v),
        "kernel_versions": dict(kernel_v),
        "reboot_required": reboot,
        "clock_unsynced": unsynced,
        "truncated": truncated,
        "permission_gaps": gaps,
        "kernel_events_total": dict(ev_total),
        "sysctl_skew": {
            k: dict(vals.items())
            for k, vals in sysctl_vals.items()
            if len(vals) > 1
            and k
            not in ("net.netfilter.nf_conntrack_count", "fs.file-nr", "kernel.threads-max", "fs.file-max", "net.netfilter.nf_conntrack_max", "net.ipv4.neigh.default.gc_thresh3", "net.ipv4.tcp_max_syn_backlog", "fs.inotify.max_user_watches")
        },
    }
    return out

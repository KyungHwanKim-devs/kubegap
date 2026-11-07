"""The text the node script writes and the kernel log lines inside it: `### section` blocks of `key=value` lines (collectors/core/node-os.sh),
the kernel's `oom-kill:` summary line, and the per-node reader of `logs/node/<node>/os.txt` that lib/nodeos and lib/resilience both need (#150).

A parser of a text format, like lib/promtext; the file itself comes from lib/snapshot.node_os_text.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .quantity import to_int
from .snapshot import node_os_text

# source: kubegap's own format, written by collectors/core/node-os.sh (`### <section>` and `key=value` lines)
SECTION_RE = re.compile(r"^### (\S+)\s*$")
# source: kubegap's own format, written by collectors/core/node-os.sh (`### <section>` and `key=value` lines)
KV_RE = re.compile(r"^([A-Za-z0-9_.:-]+)=(.*)$")


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


def key_values(lines: list[str]) -> dict[str, str]:
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


def parse_kernel(lines: list[str]) -> dict:
    stripped = [ln.strip() for ln in lines]
    kv = key_values([ln for ln in lines if not ln.startswith(" ") and "samples:" not in ln])
    counts = {k[2:]: to_int(v) for k, v in kv.items() if k.startswith("c:")}
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
        "lines": to_int(kv.get("lines")),
        "counts": counts,
        "samples": samples[-40:],
        "oom_samples": oom_samples[-60:],
        "oom_section": "oom_samples:" in stripped,  # False for an os.txt written by the node script before rubric 0.1.66, which kept no oom-kill lines
        "oom_kills": kills,  # one entry per kernel oom-kill line, with the pod uid when the cgroup path carries one. An older node script has no oom_samples section, so this stays empty and the counts above are all there is
        "total_events": sum(v for k, v in counts.items() if k != "oom_cgroup"),
    }


def kernel_oom_kills(snap: Path, nodes: list[str]) -> dict:
    """The container-level OOM kills of the kernel logs of every node whose os.txt was collected: {node: {source, kills[]}}. lib/nodeos and lib/resilience read it; resilience maps the pod uids to workloads."""
    out: dict = {}
    for name in nodes:
        text = node_os_text(snap, name)
        if text is None:
            continue
        sec = parse_sections(text)
        kern = parse_kernel(sec.get("kernel", []))
        out[name] = {
            "source": kern["source"],
            "window": kern["window"],
            "oom_section": kern["oom_section"],
            "oom_cgroup_count": kern["counts"].get("oom_cgroup") or 0,  # the count the older script already had, for nodes whose lines cannot be attributed
            "kills": [k for k in kern["oom_kills"] if not k["node_level"]],
        }
    return out

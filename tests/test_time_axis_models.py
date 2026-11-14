"""The time axis behind three checks (#62, #74, #75): the 24-hour throttling ratio next to the 5-minute one, the 7-day OOM history per workload with replaced pods and kernel kills, and node series of nodes that left the cluster."""

from __future__ import annotations

import json

from lib.foundations import nodetext
from lib.judgement.evaluate import Context
from lib.judgement.evaluate.evidence import oom_text
from lib.judgement.evaluate.rules import Run
from lib.judgement.evaluate.types import eval_metric
from lib.summaries import resilience, summarize

KERNEL_LINE = (
    "2026-11-02T08:34:08+0000 ip-10-0-9-9.internal kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=cri-containerd-f00.scope,mems_allowed=0,"
    "oom_memcg=/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod7605475d_cd56_4f83_a9a0_7fd8b226532c.slice,task_memcg=/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod7605475d_cd56_4f83_a9a0_7fd8b226532c.slice/cri-containerd-f00.scope,task=uvicorn,pid=3517082,uid=10001"
)
KILLED_LINE = "2026-11-02T08:34:08+0000 ip-10-0-9-9.internal kernel: Memory cgroup out of memory: Killed process 3517082 (uvicorn) total-vm:1907380kB, anon-rss:771336kB"
NODE_LEVEL_LINE = "2026-11-02T10:00:00+0000 ip-10-0-9-9.internal kernel: oom-kill:constraint=CONSTRAINT_NONE,nodemask=(null),cpuset=/,mems_allowed=0,global_oom,task_memcg=/system.slice/kubelet.service,task=kubelet,pid=1,uid=0"
V1_LINE = "2026-11-02T08:34:08+0000 n1 kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),oom_memcg=/kubepods/burstable/pod2a2e36d9-6307-40b4-ab46-f44f16f5327b/abc,task=java,pid=5,uid=0"


# ---------- kernel oom-kill lines ----------


def test_oom_kill_line_gives_pod_uid_time_and_task():
    k = nodetext.parse_oom_kill(KERNEL_LINE)
    assert k == {"time": "2026-11-02T08:34:08+0000", "pod_uid": "7605475d-cd56-4f83-a9a0-7fd8b226532c", "task": "uvicorn", "constraint": "CONSTRAINT_MEMCG", "node_level": False}
    assert nodetext.parse_oom_kill(V1_LINE)["pod_uid"] == "2a2e36d9-6307-40b4-ab46-f44f16f5327b"  # cgroup v1 path, dashes
    assert nodetext.parse_oom_kill(NODE_LEVEL_LINE)["node_level"] is True and nodetext.parse_oom_kill(NODE_LEVEL_LINE)["pod_uid"] is None
    assert nodetext.parse_oom_kill(KILLED_LINE) is None


def test_kernel_section_splits_samples_from_oom_samples():
    lines = ["source=journalctl", "lines=10", "c:oom_cgroup=1", "samples:", KILLED_LINE[:200], "oom_samples:", KERNEL_LINE, KILLED_LINE]
    kern = nodetext.parse_kernel(lines)
    assert kern["samples"] == [KILLED_LINE[:200]]
    assert kern["oom_samples"] == [KERNEL_LINE, KILLED_LINE]
    assert [k["pod_uid"] for k in kern["oom_kills"]] == ["7605475d-cd56-4f83-a9a0-7fd8b226532c"]


def test_old_node_script_without_oom_samples_still_parses():
    kern = nodetext.parse_kernel(["source=journalctl", "lines=3", "c:oom_cgroup=2", "samples:", KILLED_LINE])
    assert kern["samples"] == [KILLED_LINE] and kern["oom_samples"] == [] and kern["oom_kills"] == [] and kern["oom_section"] is False


# ---------- the 7-day OOM table ----------


def _metric(root, qid, rows):
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    (root / "metrics" / f"{qid}.json").write_text(json.dumps({"id": qid, "ok": True, "result": [{"metric": m, "value": [0, str(v)]} for m, v in rows]}))


def _pod(ns, name, uid, node, rs, phase="Running"):
    return {"metadata": {"namespace": ns, "name": name, "uid": uid, "ownerReferences": [{"kind": "ReplicaSet", "name": rs}]}, "spec": {"nodeName": node, "containers": [{"name": "ai"}]}, "status": {"phase": phase, "containerStatuses": []}}


def _write_objects(root, stem, items):
    (root / "objects").mkdir(parents=True, exist_ok=True)
    (root / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}))


def _os_txt(root, node, oom_lines, source="journalctl"):
    d = root / "logs" / "node" / node
    d.mkdir(parents=True, exist_ok=True)
    body = f"### meta\nuid=0\n### kernel\nsource={source}\nlines=100\nc:oom_cgroup={len(oom_lines)}\nsamples:\noom_samples:\n" + "\n".join(oom_lines) + "\n"
    (d / "os.txt").write_text(body)


def _oom_fixture(tmp_path, *, kernel=True):
    live_uid, gone_uid = "2a2e36d9-6307-40b4-ab46-f44f16f5327b", "7605475d-cd56-4f83-a9a0-7fd8b226532c"
    _write_objects(tmp_path, "pods", [_pod("prod-a", "api-577d8cbd67-xvh58", live_uid, "n1", "api-577d8cbd67")])
    _write_objects(tmp_path, "nodes", [{"metadata": {"name": "n1"}}, {"metadata": {"name": "n2"}}])
    _write_objects(tmp_path, "replicasets.apps", [{"metadata": {"namespace": "prod-a", "name": "api-577d8cbd67", "ownerReferences": [{"kind": "Deployment", "name": "api"}]}}])
    # the replaced pod's ReplicaSet is gone too, so its owner is guessed from the hash shape
    _metric(tmp_path, "oom_pods_7d", [({"namespace": "prod-a", "pod": "api-577d8cbd67-xvh58", "container": "ai"}, 9.0), ({"namespace": "prod-a", "pod": "api-59dcc49fb6-mwj6t", "container": "ai"}, 2.006)])
    _metric(
        tmp_path,
        "pod_info_7d",
        [
            ({"namespace": "prod-a", "pod": "api-59dcc49fb6-mwj6t", "uid": gone_uid, "node": "n2", "created_by_kind": "ReplicaSet", "created_by_name": "api-59dcc49fb6"}, 1.0),
            ({"namespace": "prod-a", "pod": "api-577d8cbd67-xvh58", "uid": live_uid, "node": "n1", "created_by_kind": "ReplicaSet", "created_by_name": "api-577d8cbd67"}, 1.0),
        ],
    )
    _metric(tmp_path, "oom_events_7d", [({"namespace": "prod-a", "pod": "api-577d8cbd67-xvh58", "container": "ai"}, 1.0)])
    if kernel:

        def line(t, n, uid):
            return f"2026-11-02T{t}+0000 {n} kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),oom_memcg=/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod{uid.replace('-', '_')}.slice,task=uvicorn,pid=1,uid=0"

        _os_txt(tmp_path, "n2", [line("08:34:08", "n2", gone_uid), line("08:35:05", "n2", gone_uid)])
        _os_txt(tmp_path, "n1", [line("09:38:06", "n1", live_uid), line("09:40:00", "n1", "ffffffff-ffff-ffff-ffff-ffffffffffff")])
    return tmp_path


def test_oom_7d_counts_replaced_pods_and_kernel_kills_per_workload(tmp_path):
    snap = _oom_fixture(tmp_path)
    out = resilience.oom_7d(resilience.Ctx(snap, {"namespaces": {"prod_like": ["prod-a"]}}))
    assert [r["target"] for r in out["rows"]] == ["prod-a/deploy/api:ai"]  # the gone pod's hash-stripped guess resolves to the confirmed Deployment name
    r = out["rows"][0]
    assert (r["pods_oomkilled"], r["pods_replaced"], r["restarts_of_those_pods"], r["live_pod_restarts_max"]) == (2, 1, 11, 9)
    assert r["kernel_kills_24h"] == 3 and r["kernel_nodes_read"] == 2 and r["kernel_nodes_total"] == 2 and r["kernel_log_read"] is True
    assert r["last_kill"] == "2026-11-02T09:38:06+0000" and r["cadvisor_oom_events_7d"] == 1 and r["prod"] is True
    assert out["kernel_kills_unmapped"] == 1  # a uid of a pod nobody knows any more
    assert out["repeated"] == ["prod-a/deploy/api:ai"]


def test_oom_7d_old_node_script_counts_nothing_as_known(tmp_path):
    snap = _oom_fixture(tmp_path, kernel=False)
    for node in ("n1", "n2"):
        d = snap / "logs" / "node" / node
        d.mkdir(parents=True, exist_ok=True)
        (d / "os.txt").write_text("### meta\nuid=0\n### kernel\nsource=journalctl\nlines=5\nc:oom_cgroup=2\nsamples:\n" + KILLED_LINE + "\n### sysctl\n")
    r = resilience.oom_7d(resilience.Ctx(snap, {}))["rows"][0]
    assert r["kernel_log_read"] is False and r["kernel_nodes_old_script"] == 2 and r["kernel_cgroup_ooms_on_nodes"] == 4 and r["kernel_kills_24h"] == 0
    assert oom_text(r).startswith("kernel log read on 2 nodes with the older node script, which keeps no oom-kill lines, so kills are not attributed; 4 container OOMs counted")


def test_oom_7d_is_null_without_the_prometheus_side(tmp_path):
    _write_objects(tmp_path, "pods", [])
    _write_objects(tmp_path, "nodes", [])
    assert resilience.oom_7d(resilience.Ctx(tmp_path, {}))["rows"] is None


def test_oom_7d_without_node_logs_keeps_the_prometheus_side(tmp_path):
    snap = _oom_fixture(tmp_path, kernel=False)
    r = resilience.oom_7d(resilience.Ctx(snap, {}))["rows"][0]
    assert r["kernel_kills_24h"] == 0 and r["kernel_log_read"] is False and r["kernel_nodes_total"] == 2 and r["pods_oomkilled"] == 2
    assert oom_text(r).startswith("kernel log not read in this mode. Prometheus: 2 pods ended by OOM in 7 days, 1 already replaced, 11 restarts in those pods")


def test_oom_text_names_both_sources_with_windows():
    row = {
        "kernel_log_read": True,
        "kernel_kills_24h": 5,
        "kernel_nodes_read": 2,
        "kernel_nodes_total": 2,
        "last_kill": "2026-11-02T09:38:06+0000",
        "pods_oomkilled": 3,
        "pods_replaced": 2,
        "restarts_of_those_pods": 13,
        "cadvisor_oom_events_7d": 0,
    }
    assert oom_text(row) == "kernel log: 5 kills in 24 h on 2 of 2 nodes read, last 2026-11-02T09:38:06+0000. Prometheus: 3 pods ended by OOM in 7 days, 2 already replaced, 13 restarts in those pods. cAdvisor counter 0"


# ---------- nodes that left ----------


def _inv_with_nodes():
    return {"nodes": {"nodes": [{"name": "ip-10-0-1-62.internal", "internal_ip": "10.0.1.62"}, {"name": "ip-10-0-1-139.internal", "internal_ip": "10.0.1.139"}]}}


def test_node_gone_compares_instance_ip_and_node_name_against_inventory():
    cx = Context(None, _inv_with_nodes(), {}, "large")
    assert cx.node_gone({"instance": "10.0.1.203:9100", "device": "eth0"}, "node") == "10.0.1.203"
    assert cx.node_gone({"instance": "10.0.1.62:9100"}, "node") is None
    assert cx.node_gone({"node": "ip-10-0-1-139.internal"}) is None
    assert cx.node_gone({"node": "ip-10-0-1-203.internal"}) == "ip-10-0-1-203.internal"
    assert cx.node_gone({"instance": "10.0.1.203:9100", "pod": "node-exporter-abc", "namespace": "monitoring"}, "node") == "10.0.1.203"  # the operator's pod label on an exporter series
    assert cx.node_gone({"instance": "10.0.1.149:443"}, "controlplane") is None  # an apiserver instance is not a node
    assert cx.node_gone({"instance": "10.0.1.203:8080", "pod": "ksm-1", "namespace": "monitoring"}, "resources") is None  # kube-state-metrics' own series
    assert cx.node_gone({"instance": "[fd00::7]:9100"}, "node") == "fd00::7"
    assert Context(None, {}, {}, "large").node_gone({"instance": "10.0.1.203:9100"}, "node") is None  # no node list, as in the embedded cases


def test_metric_check_skips_gone_node_and_records_it(tmp_path):
    _metric(tmp_path, "node_network_errors_1d", [({"instance": "10.0.1.203:9100", "device": "eth0"}, 317.0), ({"instance": "10.0.1.62:9100", "device": "eth0"}, 4.0)])
    cx = Context(tmp_path, _inv_with_nodes(), {}, "large")
    check = {
        "id": "node.network-errors",
        "name": "n",
        "area": "node",
        "type": "metric",
        "inputs": ["node_network_errors_1d"],
        "rule": {"expr": "value >= 1000", "warn_expr": "value >= 1"},
        "target": "labels.get('instance') + ':' + labels.get('device')",
        "evidence": 'f"{value:.0f}"',
        "severity_default": "medium",
    }
    run = Run(check, cx, {})
    r = eval_metric(cx, check, run)
    assert [f["target"] for f in r["findings"]] == ["10.0.1.62:9100:eth0"]
    assert r["gone_nodes"] == ["10.0.1.203"] and r["counts"]["gone_node"] == 1


def test_nodes_gone_24h_from_node_uname_info(tmp_path):
    _metric(tmp_path, "nodes_seen_1d", [({"instance": "10.0.1.203:9100", "nodename": "ip-10-0-1-203.internal"}, 1793650000.0), ({"instance": "10.0.1.62:9100", "nodename": "ip-10-0-1-62.internal"}, 1793672000.0)])
    nodes = [{"metadata": {"name": "ip-10-0-1-62.internal"}, "status": {"addresses": [{"type": "InternalIP", "address": "10.0.1.62"}]}}]
    out = summarize._nodes_gone_24h(tmp_path, nodes)
    assert out["seen_24h"] == 2
    assert out["gone_24h"] == [{"node": "ip-10-0-1-203.internal", "internal_ip": "10.0.1.203", "last_seen": "2026-11-02T20:06:40+00:00"}]
    assert summarize._nodes_gone_24h(tmp_path / "nowhere", nodes) == {"gone_24h": None, "seen_24h": None}


def test_nodes_gone_24h_gives_up_when_the_exporter_is_not_on_the_host_network(tmp_path):
    _metric(tmp_path, "nodes_seen_1d", [({"instance": "10.244.1.5:9100", "nodename": "node-exporter-abc"}, 1.0), ({"instance": "10.244.2.7:9100", "nodename": "node-exporter-def"}, 1.0)])
    nodes = [{"metadata": {"name": "n1"}, "status": {"addresses": [{"type": "InternalIP", "address": "10.0.1.62"}]}}]
    out = summarize._nodes_gone_24h(tmp_path, nodes)
    assert out["gone_24h"] is None and out["seen_24h"] == 2 and "host network" in out["note"]


def test_join_any_judges_a_series_present_in_one_input_only(tmp_path):
    _metric(tmp_path, "cpu_throttle_ratio_5m", [({"namespace": "a", "pod": "w-6d7ff4dcdb-abcde", "container": "c"}, 0.6)])
    cx = Context(tmp_path, {}, {}, "large")
    check = {
        "id": "resources.cpu-throttling",
        "name": "n",
        "area": "resources",
        "type": "metric",
        "inputs": ["cpu_throttle_ratio_24h", "cpu_throttle_ratio_5m"],
        "join_on": ["namespace", "pod", "container"],
        "join_any": True,
        "rule": {"expr": "v.get('cpu_throttle_ratio_24h', 0) >= 0.25", "warn_expr": "v.get('cpu_throttle_ratio_5m', 0) >= 0.25"},
        "target": "labels['pod']",
        "evidence": "str(sorted(v))",
        "severity_default": "high",
    }
    run = Run(check, cx, {})
    r = eval_metric(cx, check, run)
    assert r["status"] == "done" and [f["status"] for f in r["findings"]] == ["warn"] and r["findings"][0]["evidence"] == "['cpu_throttle_ratio_5m']"

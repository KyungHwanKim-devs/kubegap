"""Each 'no available IP' answer of ipamd is placed in time from the 24-hour ipamd log and the aws-node container's start (#209): inside the start-up
window it is the race of a new node's first seconds, after it a shortage; counts the log does not hold stay unexplained."""

from __future__ import annotations

import json

from lib.judgement.evaluate import evidence
from lib.summaries import vpccni

PROM = "awscni_assigned_ip_addresses 6\nawscni_total_ip_addresses 9\nawscni_eni_allocated 3\nawscni_eni_max 3\nawscni_ip_max 9\nawscni_no_available_ip_addresses {n}\n"
NO_IP = '{{"level":"error","ts":"{ts}","caller":"datastore/data_store.go:734","msg":"DataStore has no available IP/Prefix addresses"}}'
OTHER = '{"level":"warn","ts":"2026-11-07T12:40:00.000Z","caller":"awssession/session.go:66","msg":"HTTP_TIMEOUT env is not set or set to less than 10 seconds, defaulting to httpTimeout to 10sec"}'


def _pod(name, node, started, previous=None, host=False, ds="aws-node", phase="Running"):
    cs = {"name": "aws-node", "state": {"running": {"startedAt": started}}, "lastState": {"terminated": {"startedAt": previous}} if previous else {}}
    return {
        "metadata": {"name": name, "namespace": "kube-system", "ownerReferences": [{"kind": "DaemonSet", "name": ds}]},
        "spec": {"nodeName": node, "hostNetwork": host},
        "status": {"phase": phase, "containerStatuses": [cs]},
    }


def _snapshot(tmp_path, *, counter=1, log=None, started="2026-11-07T12:32:31Z", previous=None, env=None, step_ok=True, taken="2026-11-15T01:51:00Z"):
    (tmp_path / "objects").mkdir()
    ds = {
        "metadata": {"name": "aws-node", "namespace": "kube-system"},
        "spec": {"template": {"spec": {"containers": [{"name": "aws-node", "image": "x/amazon-k8s-cni:v1.19.0", "env": [{"name": k, "value": v} for k, v in (env or {}).items()]}]}}},
        "status": {},
    }
    (tmp_path / "objects" / "daemonsets.json").write_text(json.dumps({"items": [ds]}), encoding="utf-8")
    pods = [_pod("aws-node-a", "n1", started, previous, host=True), _pod("kube-proxy-a", "n1", started, host=True, ds="kube-proxy"), _pod("exporter-a", "n1", started, host=True, ds="exporter"), _pod("app-a", "n1", started, ds="app")]
    (tmp_path / "objects" / "pods.json").write_text(json.dumps({"items": pods}), encoding="utf-8")
    d = tmp_path / "logs" / "node" / "n1"
    d.mkdir(parents=True)
    (d / "awscni.prom").write_text(PROM.format(n=counter), encoding="utf-8")
    if log is not None:
        (d / "ipamd-24h.log").write_text("".join(line + "\n" for line in log), encoding="utf-8")
        rec = {"ok": step_ok, "lines": len(log), "out": "logs/node/n1/ipamd-24h.log", "error": None, "line_limit": 3000, "at_limit": False}
        (tmp_path / "collect-result.json").write_text(json.dumps({"vpc-cni": {"steps": {"ipamd-log": {"nodes": {"n1": rec}}}}}), encoding="utf-8")
    return {"taken_at": taken, "nodes": {"nodes": [{"name": "n1", "instance_type": "t3.small", "allocatable": {"pods": "11"}}]}}


def _node(tmp_path, **kw):
    return vpccni.analyze(tmp_path, _snapshot(tmp_path, **kw))["nodes"][0]


def test_an_answer_in_the_start_up_window_is_the_race_and_explains_the_counter(tmp_path):
    # the measured case of #209: ipamd's container started at :31 and the one answer came 9.9 s later
    n = _node(tmp_path, counter=1, log=[NO_IP.format(ts="2026-11-14T12:32:40.926Z"), OTHER], started="2026-11-14T12:32:31Z")
    assert (n["ipamd_log_read"], n["no_available_ip_startup_24h"], n["no_available_ip_shortage_24h"], n["no_available_ip_unexplained"]) == (True, 1, 0, 0)
    assert n["ipamd_started_at"] == "2026-11-14T12:32:31Z" and n["no_available_ip_last_shortage"] is None


def test_an_answer_after_the_window_is_a_shortage_with_its_time(tmp_path):
    later = "2026-11-14T12:34:32.000Z"  # 121 s after the start
    n = _node(tmp_path, counter=2, log=[NO_IP.format(ts="2026-11-14T12:32:40.926Z"), NO_IP.format(ts=later)], started="2026-11-14T12:32:31Z")
    assert (n["no_available_ip_startup_24h"], n["no_available_ip_shortage_24h"], n["no_available_ip_last_shortage"], n["no_available_ip_unexplained"]) == (1, 1, later, 0)


def test_an_old_count_with_an_empty_log_stays_unexplained(tmp_path):
    n = _node(tmp_path, counter=1, log=[], started="2026-11-07T12:32:31Z")
    assert (n["ipamd_log_read"], n["no_available_ip_startup_24h"], n["no_available_ip_shortage_24h"], n["no_available_ip_unexplained"]) == (True, 0, 0, 1)
    assert n["ipamd_uptime_hours"] == 181.3
    assert (n["host_network_pods"], n["ip_pods_max"], n["ip_max"], n["ip_pods_max_fits"]) == (3, 8, 9, True)


def test_the_previous_container_start_places_the_race_of_a_restart_and_its_lines_are_not_in_the_counter(tmp_path):
    # aws-node restarted at 10:00; the old process raced at its own start at 02:00:09, the new one has counted nothing yet
    n = _node(tmp_path, counter=0, log=[NO_IP.format(ts="2026-11-14T02:00:09.000Z")], started="2026-11-14T10:00:00Z", previous="2026-11-14T02:00:00Z")
    assert (n["no_available_ip_startup_24h"], n["no_available_ip_shortage_24h"], n["no_available_ip_unexplained"]) == (1, 0, 0)


def test_the_log_is_not_read_when_the_step_failed_or_ipamd_writes_elsewhere(tmp_path):
    n = _node(tmp_path, counter=3, log=None)
    assert (n["ipamd_log_read"], n["no_available_ip_shortage_24h"], n["no_available_ip_unexplained"]) == (False, None, 3)
    (tmp_path / "x").mkdir()
    n = _node(tmp_path / "x", counter=3, log=[], env={"AWS_VPC_K8S_CNI_LOG_FILE": "stdout"})
    assert (n["ipamd_log_read"], n["no_available_ip_shortage_24h"]) == (False, None), "with the log on stdout the file the step reads is not ipamd's"
    (tmp_path / "y").mkdir()
    n = _node(tmp_path / "y", counter=3, log=[], step_ok=False)
    assert n["ipamd_log_read"] is False


def test_without_a_known_start_every_line_is_a_shortage(tmp_path):
    inv = _snapshot(tmp_path, counter=1, log=[NO_IP.format(ts="2026-11-14T12:32:40.926Z")])
    (tmp_path / "objects" / "pods.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    n = vpccni.analyze(tmp_path, inv)["nodes"][0]
    assert (n["ipamd_started_at"], n["no_available_ip_startup_24h"], n["no_available_ip_shortage_24h"]) == (None, 0, 1)


def test_the_cluster_lists_name_only_nodes_with_a_shortage(tmp_path):
    out = vpccni.analyze(tmp_path, _snapshot(tmp_path, counter=1, log=[NO_IP.format(ts="2026-11-14T12:32:40.926Z")], started="2026-11-14T12:32:31Z"))
    assert out["nodes_ip_shortage_24h"] == [] and out["summary"]["nodes_ip_shortage_24h"] == [] and out["warm"]["summary"]["nodes_ip_shortage_24h"] == []
    assert out["ipamd_startup_window_seconds"] == vpccni.IPAMD_STARTUP_WINDOW_S == 120


def test_no_ip_unexplained_text_says_what_the_log_can_and_cannot_tell():
    base = {
        "node": "n1",
        "instance_type": "t3.small",
        "pool": "system",
        "no_available_ip_events": 1,
        "ipamd_started_at": "2026-11-07T12:32:31Z",
        "ipamd_uptime_hours": 181.3,
        "ipamd_log_read": True,
        "no_available_ip_startup_24h": 0,
        "no_available_ip_unexplained": 1,
        "max_pods": 11,
        "host_network_pods": 3,
        "ip_pods_max": 8,
        "ip_max": 9,
        "ip_pods_max_fits": True,
    }
    t = evidence.no_ip_unexplained_text(base)
    assert "1 of them are older than its log of the last 24 h" in t and "cannot be told" in t and "max-pods 11 - 3 hostNetwork = 8, against 9 pod IPs: fits" in t
    assert "its log was not read" in evidence.no_ip_unexplained_text({**base, "ipamd_log_read": False})
    assert "does not fit" in evidence.no_ip_unexplained_text({**base, "ip_pods_max_fits": False})
    assert "IP capacity unknown" in evidence.no_ip_unexplained_text({**base, "ip_pods_max_fits": None})

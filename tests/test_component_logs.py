"""Component logs are counted while they are collected and never written: the snapshot holds logs/pods/AGGREGATED.json, the summary reads it, and
summarizing changes nothing in the snapshot."""

from __future__ import annotations

import json

from lib.collection import collect
from lib.foundations import snapshot
from lib.summaries import summarize

LINE = "2026-10-27T10:00:00Z [ERROR] plugin/errors: 2 example.com. A: read udp: i/o timeout token=abcdef1234567890\n"
INV = {
    "collectors_enabled": ["core", "coredns"],
    "cluster": {"platform": "k3s"},
    "scale": {"name": "small", "source": "guessed"},
    "node_access": {"method": "none"},
    "nodes": {"count": 1},
    "namespaces": {"count": 1},
    "crds": {"count": 0},
    "taken_at": "2026-10-27T19:10:00+09:00",
}


def _snapshot(tmp_path, *, keep_lines=True, mode="full"):
    agg = collect.k8s_steps.component_logs_aggregate({"logs/pods/coredns/kube-system_coredns.log": LINE * 3}, INV, keep_lines=keep_lines, capped=[])
    (tmp_path / "logs" / "pods").mkdir(parents=True)
    (tmp_path / "logs" / "pods" / "AGGREGATED.json").write_text(json.dumps(agg), encoding="utf-8")
    (tmp_path / "inventory.json").write_text(json.dumps(INV), encoding="utf-8")
    (tmp_path / "MODE").write_text(mode + "\n")
    return tmp_path


def test_the_summary_reads_the_counts_and_leaves_the_snapshot_as_it_was(tmp_path):
    snap = _snapshot(tmp_path)
    before = {str(p.relative_to(snap)): p.read_bytes() for p in snap.rglob("*") if p.is_file()}
    s1 = summarize.summarize(snap, echo=None)
    assert s1["logs"]["lines_scanned"] == 3 and s1["logs"]["components_with_logs"] == ["coredns"] and s1["logs"]["component_log_lines"] == {"logs/pods/coredns/kube-system_coredns.log": 3}
    assert s1["logs"]["component_logs"].startswith("counted while they were collected")
    for u in s1["logs"]["unclassified_errors"]:
        assert "abcdef1234567890" not in (u.get("sample") or "")  # a sample is masked before it is kept
    assert {str(p.relative_to(snap)): p.read_bytes() for p in snap.rglob("*") if p.is_file() and str(p.relative_to(snap)) in before} == before  # nothing changed or removed
    s2 = summarize.summarize(snap, echo=None)
    assert s2["logs"] == s1["logs"]  # and so a second summary is the same


def test_no_line_of_a_component_log_is_in_a_snapshot_of_either_mode(tmp_path):
    full = _snapshot(tmp_path / "f")
    text = "".join(p.read_text(encoding="utf-8") for p in full.rglob("*") if p.is_file())
    assert "abcdef1234567890" not in text and not list(full.rglob("*.log"))  # a full run keeps masked samples, never the line as it was
    daily = _snapshot(tmp_path / "d", keep_lines=False, mode="daily")
    agg = snapshot.component_logs_aggregate(daily)
    assert agg["log_scan"]["lines_scanned"] == 3 and agg["log_scan"]["lines_kept"] is False
    assert agg["log_scan"]["unclassified_errors"] == [] and all(r["samples"] == [] for r in agg["log_scan"]["signatures"])
    assert "example.com" not in json.dumps(agg)  # a daily run keeps counts and no text of any line


def test_without_the_counts_file_the_summary_says_the_component_logs_were_not_counted(tmp_path):
    snap = _snapshot(tmp_path)
    (snap / "logs" / "pods" / "AGGREGATED.json").unlink()
    s = summarize.summarize(snap, echo=None)
    assert s["logs"]["lines_scanned"] == 0 and s["logs"]["component_logs"].startswith("not counted")


def test_node_logs_and_component_logs_add_up(tmp_path):
    from lib.foundations import logscan, signatures

    sigs, _ = signatures.load(["core", "coredns"])
    a = logscan.scan_texts([("logs/pods/coredns/kube-system_coredns.log", LINE * 3)], sigs, taken=snapshot.taken_at(INV))
    b = logscan.scan_texts([("logs/pods/coredns/kube-system_coredns-b.log", LINE * 2)], sigs, taken=snapshot.taken_at(INV))
    m = logscan.merge([a, b], sigs)
    assert m["lines_scanned"] == 5 and len(m["files_scanned"]) == 2
    both = logscan.scan_texts([("logs/pods/coredns/kube-system_coredns.log", LINE * 3), ("logs/pods/coredns/kube-system_coredns-b.log", LINE * 2)], sigs, taken=snapshot.taken_at(INV))
    assert [(r["id"], r["count"], r["targets"], r["status"]) for r in m["signatures"]] == [(r["id"], r["count"], r["targets"], r["status"]) for r in both["signatures"]]
    assert [(u["pattern"], u["count"]) for u in m["unclassified_errors"]] == [(u["pattern"], u["count"]) for u in both["unclassified_errors"]]


def test_logs_step_finds_the_workloads_of_present_components_with_the_shared_matcher(tmp_path, monkeypatch):
    """The step matches the detection rules' name patterns against the object dump through lib.foundations.components.match_name (the one matcher since #136; until then it
    imported a private one from lib.collection.discover inside the function, which no test ran, and the k3s full run of 2026-11-05 crashed on the stale import)."""
    from lib.foundations import shell
    from lib.foundations.runlog import RunLog

    (tmp_path / "objects").mkdir()
    dep = {
        "metadata": {"namespace": "gitops", "name": "argo-cd-argocd-server"},
        "spec": {"selector": {"matchLabels": {"app.kubernetes.io/name": "argocd-server"}}, "template": {"spec": {"containers": [{"image": "quay.io/argoproj/argocd:v3.6.0"}]}}},
    }
    (tmp_path / "objects" / "deployments.json").write_text(json.dumps({"items": [dep]}))
    for k in ("daemonsets", "statefulsets"):
        (tmp_path / "objects" / f"{k}.json").write_text(json.dumps({"items": []}))
    calls = []

    def fake_kubectl(args, **kw):
        calls.append(args)
        assert not kw.get("out_path"), "a component log is never written as a file"
        return shell.Result(cmd=["kubectl"], code=0, stdout="[pod/argocd-server-1/server] line\n" * 3)

    monkeypatch.setattr(collect.k8s_steps.kube, "kubectl", fake_kubectl)
    step = {"id": "component-logs", "type": "component-logs", "tail": 3}
    res = collect.k8s_steps.run_component_logs_step(step, "component-logs", "core", {"components_present": ["argocd"], "taken_at": "2026-11-05T10:00:00+09:00"}, None, None, tmp_path, RunLog(None), 10, None, keep_lines=True)
    assert res["targets"] == 1 and res["components"]["argocd"]["gitops/argo-cd-argocd-server"]["ok"] is True
    # the container returned exactly the tail limit: its log was cut there, and the record says so
    assert res["components"]["argocd"]["gitops/argo-cd-argocd-server"]["capped_streams"] == 1 and res["capped"] == ["argocd: gitops/argo-cd-argocd-server"]
    assert not list(tmp_path.rglob("*.log")) and json.loads((tmp_path / "logs" / "pods" / "AGGREGATED.json").read_text())["log_scan"]["lines_scanned"] == 3
    assert calls[0][:5] == ["logs", "-n", "gitops", "-l", "app.kubernetes.io/name=argocd-server"]

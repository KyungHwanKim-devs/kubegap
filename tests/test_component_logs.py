"""Component pod logs are deleted after summarize, their aggregates saved to logs/pods/AGGREGATED.json, and a rerun of summarize gives the same logs and scaling sections."""

from __future__ import annotations

import json

from lib import summarize


def test_component_logs_are_removed_and_marker_left(tmp_path):
    d = tmp_path / "logs" / "pods" / "coredns"
    d.mkdir(parents=True)
    (d / "kube-system_coredns.log").write_text("line with token=abcdef123456\n", encoding="utf-8")
    assert summarize.remove_component_logs(tmp_path) == 1
    assert not (d / "kube-system_coredns.log").exists()
    assert summarize.component_logs_removed(tmp_path)
    assert "keep_component_logs" in (tmp_path / "logs" / "pods" / summarize.COMPONENT_LOGS_MARKER).read_text(encoding="utf-8")
    assert summarize.remove_component_logs(tmp_path) == 0  # second call: nothing to remove, marker stays
    assert summarize.component_logs_removed(tmp_path)


def test_remove_without_logs_dir_is_a_noop(tmp_path):
    assert summarize.remove_component_logs(tmp_path) == 0
    assert not summarize.component_logs_removed(tmp_path)


def _fake_snapshot(tmp_path):
    d = tmp_path / "logs" / "pods" / "coredns"
    d.mkdir(parents=True)
    (d / "kube-system_coredns.log").write_text("2026-10-27T10:00:00Z [ERROR] plugin/errors: 2 example.com. A: read udp: i/o timeout token=abcdef1234567890\n" * 3, encoding="utf-8")
    (tmp_path / "inventory.json").write_text(
        json.dumps({"collectors_enabled": ["core", "coredns"], "cluster": {"platform": "k3s"}, "profile": {"name": "lab"}, "node_access": {"method": "none"}, "nodes": {"count": 1}, "namespaces": {"count": 1}, "crds": {"count": 0}}),
        encoding="utf-8",
    )
    return tmp_path


def test_summarize_deletes_logs_writes_aggregate_and_rerun_is_identical(tmp_path):
    from lib import snapshot

    snap = _fake_snapshot(tmp_path)
    s1 = summarize.summarize(snap, echo=None)
    assert s1["logs"]["component_logs_removed"] is True
    assert s1["logs"]["lines_scanned"] == 3
    assert not list((snap / "logs" / "pods").rglob("*.log"))
    agg = snapshot.component_logs_aggregate(snap)
    assert agg and agg["log_scan"]["lines_scanned"] == 3 and agg["files_removed"] == ["logs/pods/coredns/kube-system_coredns.log"]
    for u in s1["logs"]["unclassified_errors"]:
        assert "abcdef1234567890" not in (u.get("sample") or "")  # samples are masked before they are kept
    s2 = summarize.summarize(snap, echo=None)
    scan_keys = [k for k in s1["logs"] if k != "source_note"]
    assert {k: s2["logs"].get(k) for k in scan_keys} == {k: s1["logs"].get(k) for k in scan_keys}
    assert "AGGREGATED.json" in s2["logs"]["source_note"]
    assert "scan_incomplete" not in s2["logs"]
    # keep_component_logs flipped on after the deletion: the flag still tells the truth
    s3 = summarize.summarize(snap, echo=None, keep_component_logs=True)
    assert s3["logs"]["component_logs_removed"] is True


def test_summarize_marker_without_aggregate_is_flagged(tmp_path):
    snap = _fake_snapshot(tmp_path)
    summarize.summarize(snap, echo=None)
    (snap / "logs" / "pods" / "AGGREGATED.json").unlink()
    s = summarize.summarize(snap, echo=None)
    assert s["logs"]["scan_incomplete"] is True
    assert s["logs"]["lines_scanned"] == 0


def test_summarize_keep_component_logs(tmp_path):
    snap = _fake_snapshot(tmp_path)
    s = summarize.summarize(snap, echo=None, keep_component_logs=True)
    assert s["logs"]["component_logs_removed"] is False
    assert list((snap / "logs" / "pods").rglob("*.log"))
    assert not summarize.component_logs_removed(snap)

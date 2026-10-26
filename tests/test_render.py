"""report-details.md rendering: code tables from a tiny snapshot plus LLM fragments, with missing fragments marked."""

from __future__ import annotations

import json

from lib import render


def _snap(tmp_path, with_fragments: bool):
    s = tmp_path / "2026-10-26T10-00-00"
    s.mkdir()
    (s / "MODE").write_text("daily\n")
    (s / "inventory.json").write_text(
        json.dumps(
            {
                "context": "c",
                "taken_at": "2026-10-26T10:00:00+09:00",
                "signatures_version": "1.0.0",
                "cluster": {"platform": "k3s", "server_version": "v1.33.0+k3s1", "cluster_name": "lab"},
                "profile": {"name": "lab", "source": "detected"},
                "nodes": {"count": 2, "ready": 2},
                "namespaces": {"count": 3},
                "pods": {"count": 10},
                "crds": {"count": 1},
                "components_present": ["coredns"],
                "stores": {},
                "node_access": {"method": "ssh", "reasons": ["k3s: SSH"]},
                "missing_families": ["slo"],
            }
        )
    )
    (s / "summary.json").write_text(
        json.dumps(
            {
                "collection": {"mode": "daily", "mode_skipped_steps": ["core.krr"], "failed_steps": [], "seconds_total": 60},
                "run": {"commands": 5, "failed": []},
                "logs": {"signatures_version": "1.0.0", "files_scanned": 1, "lines_scanned": 10, "components_with_logs": ["coredns"], "error_lines_unclassified": 0, "signatures": [], "unclassified_errors": []},
            }
        )
    )
    findings = [
        {"id": "a.b.ns/x", "check": "a.b", "type": "metric", "status": "fail", "severity_default": "high", "evidence": "value 0.9 | pipe"},
        {"id": "a.c.cluster", "check": "a.c", "type": "absence", "status": "fail", "severity_default": "critical", "evidence": "no slo", "why": "why", "suggest": "do"},
        {"id": "a.d.ns/y", "check": "a.d", "type": "summary", "status": "warn", "severity_default": "low", "evidence": "near"},
    ]
    (s / "findings-draft.json").write_text(
        json.dumps(
            {
                "kubegap": "0.1.0",
                "rubric_version": "0.1.48",
                "checks": {"total": 4, "by_status": {"done": 3, "not-collected": 1}, "load_errors": []},
                "findings": findings,
                "suppressed": [],
                "expired_suppressions": [],
                "check_results": [{"id": "a.b", "status": "done"}, {"id": "a.e", "status": "not-collected", "reason": "daily"}],
            }
        )
    )
    (s / "diff.json").write_text(
        json.dumps(
            {
                "a_name": "2026-10-25T10-00-00",
                "b_name": s.name,
                "findings": {
                    "rubric_version": ["0.1.48", "0.1.48"],
                    "counts_before": {"fail": {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0}, "warn": {"critical": 0, "high": 0, "medium": 0, "low": 1, "info": 0}},
                    "new": [{"id": "a.b.ns/x", "status": "fail", "severity_default": "high"}],
                    "resolved": [],
                    "changed": [],
                    "rename_suspects": [],
                    "persisted": {"runs_checked": 2, "persisted_3plus": 0, "persisted_all": 1, "toil_candidates_by_check": {}, "rows": [{"id": "a.c.cluster", "runs": 2}]},
                },
                "objects": {"added": [], "removed": [], "changed": [{"kind": "deployments", "name": "ns/x", "changed_fields": ["spec.replicas"]}]},
                "events": {"changed": [{"reason": "BackOff", "type": "Warning", "delta": 3, "objects_top_after": ["Pod/ns/x-1"]}]},
            }
        )
    )
    (s / "collect-result.json").write_text(
        json.dumps(
            {
                "_summary": {"mode": "daily", "seconds_total": 60},
                "core": {"collector": "core", "steps": {"events": {"ok": True}, "krr": {"ok": True, "skipped": "not collected in daily mode", "mode_skipped": True}, "top": {"ok": False, "error": "boom"}}},
            }
        )
    )
    if with_fragments:
        (s / "llm").mkdir()
        (s / "llm" / "adjustments.md").write_text("| id | first | final | reason |\n|---|---|---|---|\n| a.b.ns/x | fail/high | fail/medium | lab |\n")
        (s / "llm" / "tool-notes.md").write_text("1. none\n")
    return s


def test_render_with_fragments(tmp_path):
    s = _snap(tmp_path, True)
    out = render.render_details(s)
    text = out.read_text()
    assert out.name == "report-details.md"
    assert "daily mode" in text.splitlines()[0]
    assert "| critical | 1 | 0 | fail +0 · warn +0 |" in text  # counts vs. previous run
    assert "| high | 1 | 0 | fail +1 · warn +0 |" in text
    assert "`a.c.cluster` | critical | 2 |" in text  # consecutive runs from persisted rows
    assert "value 0.9 \\| pipe" in text  # pipes escaped in table cells
    assert "fail/medium | lab" in text  # adjustments fragment inlined
    assert "(daily mode: no per-area detail" in text
    assert "Not collected in daily mode 1: `a.e`" in text
    assert "| core | 3 | top | krr (not collected in daily mode) |" in text
    assert "BackOff +3 (Pod/ns/x-1)" in text
    assert text.count("(not written this run)") == 2  # changes, files-read missing; tool-notes and adjustments present; areas replaced by the daily note


def test_render_korean_headings(tmp_path):
    s = _snap(tmp_path, False)
    text = render.render_details(s, language="ko").read_text()
    assert text.startswith("# kubegap 리포트 세부 — lab (`c`), daily 모드")
    assert "## 1. 1차 결과 집계와 최종 조정" in text
    assert "(이번 실행에서 쓰지 않음)" in text
    assert "`a.b.ns/x`" in text  # data inside tables stays as it is


def test_render_without_fragments_and_without_diff(tmp_path):
    s = _snap(tmp_path, False)
    (s / "diff.json").unlink()
    text = render.render_details(s).read_text()
    assert "No earlier daily snapshot to compare with." in text
    assert "no previous run of this mode" in text
    assert text.count("(not written this run)") == 4

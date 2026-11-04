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
                "_summary": {"mode": "daily", "seconds_total": 60, "failed": ["core.top"]},
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


# ---------- cluster strings cannot change how report-details.md renders (#92) ----------


def test_fence_is_longer_than_any_backtick_run_inside():
    assert render._fence("plain") == "```"
    assert render._fence("a ``` b") == "````"
    assert render._fence("`````") == "``````"
    assert render._fence("") == "```"


def test_details_with_three_backticks_render_inside_a_longer_fence(tmp_path):
    s = _snap(tmp_path, False)
    draft = json.loads((s / "findings-draft.json").read_text())
    draft["findings"][0]["details"] = {"sample": "x ``` \n# not a heading\n</details> after", "pod": "p-1"}
    draft["findings"][0]["id"] = "a.b.ns/x<b>"
    (s / "findings-draft.json").write_text(json.dumps(draft))
    text = render.render_details(s).read_text()
    i = text.index("````json")
    block = text[i:]
    assert block.splitlines()[0] == "````json" and "\n````\n" in block
    assert "<details><summary><code>a.b.ns/x&lt;b&gt;</code></summary>" in text, "the summary id is HTML-escaped"
    fences = [ln for ln in text.splitlines() if ln.startswith("```")]
    assert len(fences) % 2 == 0, fences
    for opener, closer in zip(fences[0::2], fences[1::2], strict=True):
        assert closer == opener.rstrip("json"), (opener, closer)


def test_cell_breaks_every_link_image_and_tag_but_keeps_placeholders():
    assert render._cell("[x](javascript:alert(1))") == "[x] (javascript:alert(1))"
    assert render._cell("[x](file:///etc/passwd)") == "[x] (file:///etc/passwd)"
    assert render._cell("[x](../relative)") == "[x] (../relative)"
    assert render._cell("[x](https://ok)") == "[x] (https://ok)", "no code path writes a link into a cell; a remote target is a beacon in viewers that fetch"
    assert render._cell("![img](https://host/p.png)") == "! [img] (https://host/p.png)"
    assert render._cell("![img](data:image/svg+xml;base64,AAAA)") == "! [img] (data:image/svg+xml;base64,AAAA)"
    assert render._cell("<javascript:alert(1)>") == "< javascript:alert(1)>"
    assert render._cell('<a href="javascript:alert(1)">x</a>') == '< a href="javascript:alert(1)">x< /a>'
    assert render._cell("<img src=x onerror=alert(1)>") == "< img src=x onerror=alert(1)>"
    assert render._cell("<script>alert(1)</script>") == "< script>alert(1)< /script>"
    assert render._cell("<!-- c --> <?xml?>") == "< !-- c --> < ?xml?>"
    assert render._cell("<https://ok>") == "< https://ok>"
    assert render._cell("<masked> <account> <ip> <none> <unknown> <unset> <nil> <invalid> a<b>c 1 < 2 <3") == "<masked> <account> <ip> <none> <unknown> <unset> <nil> <invalid> a< b>c 1 < 2 <3"
    assert render._cell("https://plain.example/path stays") == "https://plain.example/path stays"
    assert render._cell("a|b\nc") == "a\\|b c"
    assert render._cell(None) == "" and render._cell(3) == "3"


def test_event_reason_and_failed_command_error_lines_cannot_open_a_block(tmp_path):
    s = _snap(tmp_path, True)
    diff = json.loads((s / "diff.json").read_text())
    diff["events"]["changed"][0]["reason"] = "BackOff\n```\n[x]: javascript:alert(1)"
    (s / "diff.json").write_text(json.dumps(diff))
    cr = json.loads((s / "collect-result.json").read_text())
    cr["core"]["steps"]["top"]["error"] = "error from server\n```\n<script>x</script>"
    (s / "collect-result.json").write_text(json.dumps(cr))
    text = render.render_details(s).read_text()
    assert "BackOff ``` [x]: javascript:alert(1) +3" in text
    assert "`core.top` error from server ``` < script>x< /script>" in text
    assert not any(ln.startswith("```") for ln in text.splitlines()), "no fence opened by a cluster string (this snapshot has no details block)"


def test_failed_steps_are_counted_from_collect_result_not_from_exit_codes(tmp_path):
    """#132: kubent and pluto exit 0 when their read is not confirmed, so run.log lists no failed command while collect-result.json has the failed step.
    The header row, the Failed column and the count under the table read the same list."""
    s = _snap(tmp_path, False)
    cr = json.loads((s / "collect-result.json").read_text())
    cr["core"]["steps"]["kubent"] = {"ok": False, "api_read": False, "lists_ok": 0, "lists_failed": 2, "error": "kubent: API resources not confirmed read; DBG Failed to retrieve: x"}
    cr["_summary"]["failed"] = ["core.top", "core.kubent"]
    (s / "collect-result.json").write_text(json.dumps(cr))
    summ = json.loads((s / "summary.json").read_text())
    summ["hygiene"] = {"deprecated": {"kubent_lists_ok": 0, "kubent_lists_failed": 2, "pluto_lists_ok": 119, "pluto_lists_failed": 7}}
    summ["run"] = {
        "commands": 5,
        "failed": [{"id": "core.top", "collector": "core", "error": "exit 1"}, {"id": "core.kubent.extra", "error": "x"}, {"id": "metallb.speaker-metrics.speaker-abc", "collector": "metallb", "error": "502 Bad Gateway"}],
    }
    (s / "summary.json").write_text(json.dumps(summ))
    text = render.render_details(s).read_text()
    assert "| core | 4 | top, kubent | krr (not collected in daily mode) |" in text
    assert "5 commands, 60 s. Failed steps: 2: `core.top` boom; `core.kubent` kubent: API resources not confirmed read; DBG Failed to retrieve: x" in text
    # run.log's failures are not a second count of the same thing: the ones that belong to a failed step are not repeated, the one inside a step that succeeded is shown as such
    assert "Commands that failed inside a step that still succeeded (run.log): 1: `metallb.speaker-metrics.speaker-abc` 502 Bad Gateway" in text
    assert text.count("`core.top`") == 1 and "core.kubent.extra" not in text  # the failed step once, not again as a run.log command
    assert "Deprecated-API tools: kubent 0 of 2 Lists answered (2 refused or not served); pluto 119 of 126 Lists answered (7 refused or not served)." in text


def test_a_snapshot_without_list_counts_prints_no_tool_line(tmp_path):
    s = _snap(tmp_path, False)
    summ = json.loads((s / "summary.json").read_text())
    summ["hygiene"] = {"deprecated": {"kubent_lists_ok": None, "kubent_lists_failed": None}}
    (s / "summary.json").write_text(json.dumps(summ))
    assert "Deprecated-API tools" not in render.render_details(s).read_text()

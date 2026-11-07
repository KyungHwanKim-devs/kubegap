"""README's "Verified against" table is generated from references/verified-versions.yaml and every citation's tag is in that file (#146)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.output import render, verified

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "<!-- verified-table:begin -->\n", "<!-- verified-table:end -->\n"


@pytest.mark.parametrize(("language", "doc"), [("en", "README.md"), ("ko", "README.ko.md")])
def test_the_readme_table_is_current(language, doc):
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert BEGIN in text and END in text, f"{doc} lost the verified-table markers"
    between = text.split(BEGIN, 1)[1].split(END, 1)[0]
    assert between == verified.render_table(language), f"regenerate: scripts/kubegap verified --markdown --language {language}, pasted between the markers of {doc}"


def test_every_citation_names_a_tag_the_file_knows():
    """A version added to a `source:` entry, a signature or sources.md without the table fails here."""
    assert verified.uncited_tags() == []


def test_the_citation_scan_reads_continuations_and_skips_api_groups(monkeypatch):
    lines = [
        "x: kubernetes/kubernetes pkg/a.go:1@v1.30.0, :2@v1.31.0; google/cadvisor metrics/p.go:3@v0.51.0, lib/q.go:4@v0.60.5 (kubernetes/kubernetes go.mod pins: :38@v1.32.13)",
        "storage.k8s.io/v1 is served :10@v1.37.2",
        "containerd/containerd api/next.pb.txt:5@api/v1.8.0",
    ]
    monkeypatch.setattr(verified, "_lines", lambda: lines)
    verified.full_citations.cache_clear()
    verified.cited_tags.cache_clear()
    try:
        assert verified.full_citations() == {"kubernetes/kubernetes": {"v1.30.0"}, "google/cadvisor": {"v0.51.0"}, "containerd/containerd": {"api/v1.8.0"}}
        assert verified.cited_tags() == {"kubernetes/kubernetes": {"v1.30.0", "v1.31.0", "v1.32.13"}, "google/cadvisor": {"v0.51.0", "v0.60.5"}, "containerd/containerd": {"api/v1.8.0"}}
    finally:
        verified.full_citations.cache_clear()
        verified.cited_tags.cache_clear()


def test_every_component_is_complete():
    names = set()
    for c in verified.components():
        assert c.get("name") and c.get("repos") and isinstance(c.get("read"), list), c
        assert c["name"] not in names, f"duplicate component {c['name']}"
        names.add(c["name"])
        assert verified.version_range(c) or c.get("newest"), f"{c['name']}: no version to show"
    assert len(verified.components()) >= 30
    repos = [r for c in verified.components() for r in c["repos"]]
    assert len(repos) == len(set(repos)), "a repository belongs to one component"
    assert not set(repos) & verified.libraries(), "a repository is a component's or a library, not both"


def test_the_range_note_reads_the_primary_repository_only():
    assert verified.range_note("Kubernetes", "v1.33.5+k3s1") == "v1.33.5+k3s1 (verified 1.30 to 1.37)"  # klog and apimachinery tags inside the component do not widen it
    assert verified.range_note("Prometheus", "3.7.3") == "3.7.3 (verified 2.49 to 3.15)"
    assert verified.range_note("Loki", "1.8") == "1.8 (outside the verified range 2.6 to 3.7)"
    assert verified.range_note("Loki", None) is None and verified.range_note("No such component", "1.0") is None
    assert verified.range_note("Loki", "1.8", "ko") == "1.8 (검증 범위 밖 2.6 ~ 3.7)"
    assert verified.range_note("Loki", "2.6.1") == "2.6.1 (verified 2.6 to 3.7)"  # the chart tags in grafana/loki (`helm-loki-7.5.0`) stay out through `tag_prefix`


def test_the_report_header_names_the_versions_next_to_the_range(tmp_path):
    inv = {
        "context": "c",
        "schema": 1,
        "cluster": {"platform": "k3s", "server_version": "v1.33.5+k3s1", "cluster_name": "c"},
        "profile": {"name": "lab", "source": "detected"},
        "stores": {"prometheus": {"version": "3.7.3"}, "loki": {"version": "1.8"}},
        "nodes": {},
        "node_access": {"method": "none"},
    }
    (tmp_path / "inventory.json").write_text(json.dumps(inv))
    (tmp_path / "MODE").write_text("daily")
    (tmp_path / "summary.json").write_text(json.dumps({"collection": {"mode": "daily"}}))
    (tmp_path / "findings-draft.json").write_text(json.dumps({"findings": [], "check_results": []}))
    (tmp_path / "collect-result.json").write_text(json.dumps({"_summary": {"failed": [], "skipped": []}}))
    text = render.render_details(tmp_path).read_text()
    assert "| Verified against | Kubernetes v1.33.5+k3s1 (verified 1.30 to 1.37) · Prometheus 3.7.3 (verified 2.49 to 3.15) · Loki 1.8 (outside the verified range 2.6 to 3.7) |" in text


def test_the_unverified_count_is_what_sources_md_marks():
    rows = [line for line in (ROOT / "references" / "sources.md").read_text(encoding="utf-8").splitlines() if line.startswith("|") and "**unverified" in line]
    assert verified.unverified_count() == len(rows) and 0 < len(rows) < 200
    assert f"{verified.unverified_count()} facts" in verified.render_table("en")

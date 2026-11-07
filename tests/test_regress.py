"""End-to-end regression (#145): summarize → evaluate → render on the committed snapshot fixtures gives the committed expectation, on every
variant, and the pieces that once made two runs of the same input differ stay fixed."""

from __future__ import annotations

import gzip
import json
import math
import re

import pytest

from lib import evaluate, regress, summarize

VARIANTS = regress.variants()
RUNS: dict[str, dict[str, str]] = {}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """One pipeline run per variant for the whole module (about a second each)."""
    if not RUNS:
        for variant, fixture, mutate in VARIANTS:
            RUNS[variant] = regress.run(regress.stage(fixture, tmp_path_factory.mktemp(variant), mutate))
    return RUNS


def test_there_is_at_least_one_fixture():
    assert [f.name for f in regress.fixtures()], "tests/fixtures/snapshot-<name>/ holds the committed snapshots"


@pytest.mark.parametrize("variant", [v for v, _, _ in VARIANTS])
def test_the_pipeline_gives_the_committed_expectation(runs, variant):
    diffs = regress.compare(variant, runs[variant])
    assert not diffs, "\n\n".join(diffs) + "\n\nIf the change is intended: scripts/kubegap regress --update, and commit the expectation with the change."


@pytest.mark.parametrize("variant", [v for v, _, _ in VARIANTS if v.endswith("-degraded")])
def test_a_degraded_run_skips_with_a_reason_and_records_the_loss(runs, variant):
    full = json.loads(runs[variant.removesuffix("-degraded")]["findings.json"])
    degraded = json.loads(runs[variant]["findings.json"])
    before = {r["id"]: r for r in full["check_results"]}
    after = {r["id"]: r for r in degraded["check_results"]}
    changed = {cid for cid in before if before[cid]["status"] != after[cid]["status"]}
    assert changed, "taking inputs away changes some statuses"
    for cid in changed:
        assert after[cid]["status"] == "skip", f"{cid}: {before[cid]['status']} became {after[cid]['status']}, not skip"
        assert after[cid].get("reason"), f"{cid}: a skip names what was missing"
    # the forbidden List, the denied kind, the missing stores and the missing node backend each leave their mark where collect leaves it
    summary = json.loads(runs[variant]["summary.json"])
    assert summary["events"]["missing"].startswith("events.json missing")
    assert summary["collection"]["object_files"][regress.DENIED_STEM] == "denied"
    assert "core.events" in summary["collection"]["failed_steps"]
    assert "core.metrics.core" in summary["collection"]["failed_steps"], "a promql step without Prometheus is a failed step (error: no Prometheus connection)"
    reasons = " ".join(r.get("reason") or "" for r in after.values())
    assert "no Prometheus" in reasons and "the ClusterRole does not grant list on this kind" in reasons
    details = runs[variant]["report-details.en.md"]
    section = details.split("### 7-1")[1].split("###")[0]
    assert re.search(r"^\| core \| \d+ \| events, metrics.core \|", section, re.MULTILINE), "section 7-1 lists the forbidden List and the promql step in the Failed column"
    assert "no prometheus connection" in section and "no node command backend" in section, "the http steps of the gone store and the node steps are skipped with the reason collect writes"


def test_summary_shape_doc_matches_the_summaries(runs):
    summaries = [json.loads(runs[v]["summary.json"]) for v, _, _ in VARIANTS if not v.endswith("-degraded")]
    assert regress.shape_mismatches(summaries) == []


@pytest.mark.parametrize("fixture", regress.fixtures(), ids=lambda p: p.name)
def test_a_fixture_stays_within_the_budget(fixture):
    files = [p for p in fixture.rglob("*") if p.is_file()]
    for name in ("summary.json", "findings-draft.json", "report.md", "report-details.md", "diff.json", "INCOMPLETE"):
        assert not (fixture / name).exists(), f"{name} is an output, not an input"
    assert not any(p.parent.name in ("llm", "earlier-reports", "extra") for p in files)
    packed = sum(len(gzip.compress(p.read_bytes(), 6)) for p in files)
    assert packed <= 2_000_000, f"{fixture.name}: {packed} bytes compressed; scripts/make-fixture.py trims a snapshot to this budget"
    for p in files:
        if p.suffix == ".json":
            json.loads(p.read_text(encoding="utf-8"))  # strict: no NaN tokens, no broken replacement


# ---------- what once made two runs of the same input differ ----------


def test_details_keys_are_sorted_whatever_the_hash_seed():
    rec = evaluate.ItemRecorder({"zeta": 1, "alpha": 2, "mid": 3, "unused": 4})
    rec["zeta"], rec.get("mid"), "alpha" in rec
    assert list(rec.kept()) == ["alpha", "mid", "zeta"]


def test_the_mean_of_samples_has_the_same_digits_on_every_python(tmp_path):
    """sum() of floats changed in Python 3.12 (Neumaier summation); math.fsum gives the correctly rounded sum on every version."""
    (tmp_path / "metrics").mkdir()
    values = [0.1] * 10 + [1e16, 1.0, -1e16]
    (tmp_path / "metrics" / "q.json").write_text(json.dumps({"ok": True, "result": [{"metric": {"i": str(i)}, "value": [0, str(v)]} for i, v in enumerate(values)]}))
    assert summarize.summarize_metrics(tmp_path)["q"]["stats"]["mean"] == math.fsum(values) / len(values) == 2.0 / 13


def test_a_nan_sample_is_null_not_a_nan_token(tmp_path):
    (tmp_path / "metrics").mkdir()
    (tmp_path / "metrics" / "q.json").write_text(json.dumps({"ok": True, "result": [{"metric": {"verb": "GET"}, "value": [0, "NaN"]}, {"metric": {"verb": "LIST"}, "value": [0, "0.5"]}]}))
    out = summarize.summarize_metrics(tmp_path)["q"]
    assert [r["value"] for r in out["top"]] == [0.5, None] and out["stats"] == {"min": 0.5, "max": 0.5, "mean": 0.5, "n": 1}
    assert not any(isinstance(r["value"], float) and math.isnan(r["value"]) for r in out["top"])
    json.loads(json.dumps(out), parse_constant=lambda c: pytest.fail(f"non-JSON token {c}"))


def test_the_normalisation_hides_only_the_path_the_clock_and_the_version(tmp_path):
    from lib import __version__

    text = f'"snapshot": "{tmp_path}", "generated_at": "2026-11-07T10:00:00+09:00", "kubegap": "{__version__}", "rubric_version": "0.1.83", "instance": "10.{__version__}2:9100"\n| kubegap / rubric / signatures | {__version__} / 0.1.83 / 1.1.0 |'
    assert (
        regress.normalise(text, tmp_path)
        == f'"snapshot": "<snapshot>", "generated_at": "<generated_at>", "kubegap": "<kubegap>", "rubric_version": "0.1.83", "instance": "10.{__version__}2:9100"\n| kubegap / rubric / signatures | <kubegap> / 0.1.83 / 1.1.0 |'
    )

"""End-to-end regression (#145): summarize → evaluate → render on the committed snapshot fixtures gives the committed expectation, on every
variant, and the pieces that once made two runs of the same input differ stay fixed."""

from __future__ import annotations

import gzip
import json
import math
import re

import pytest

from lib.commands import regress
from lib.judgement import evaluate
from lib.summaries import summarize

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


@pytest.mark.parametrize("variant", [v for v, _, _ in VARIANTS if v.endswith("-degraded")])
def test_a_degraded_run_never_turns_a_fail_or_warn_into_a_pass(runs, variant):
    """The verdict level (#98, #141): a check that still ran (`done`) on the degraded copy and lost fail or warn findings must have skipped the targets it could not
    judge (`skipped_reason`, counted in section 7-5). One check loses findings for a reason that is not a missing judgement and is named here with it:
    `logs.signatures` scans fewer lines when the node logs are gone."""
    full = json.loads(runs[variant.removesuffix("-degraded")]["findings.json"])
    degraded = json.loads(runs[variant]["findings.json"])
    before = {r["id"]: r for r in full["check_results"]}
    after = {r["id"]: r for r in degraded["check_results"]}
    lost_without_a_word = []
    for cid in before:
        if before[cid]["status"] != "done" or after[cid]["status"] != "done":
            continue
        fw_before = sum(1 for f in full["findings"] if f["check"] == cid and f["status"] in ("fail", "warn"))
        fw_after = sum(1 for f in degraded["findings"] if f["check"] == cid and f["status"] in ("fail", "warn"))
        if fw_after < fw_before and not after[cid].get("skipped_reason") and cid != "logs.signatures":
            lost_without_a_word.append((cid, fw_before, fw_after))
    assert lost_without_a_word == [], lost_without_a_word


# Checks that keep judging in a daily run on part of what a full run gives them, and so find less. Each is named with the part it loses.
PARTIAL_IN_DAILY = {
    "logs.signatures": "the failure patterns of node logs (kubelet, containerd, kernel) are counted from node-os; the patterns of component logs are counted in every run",
    "resources.oomkilled-repeated": "kernel out-of-memory kills are read from the node's kernel log (node-os); kills the kubelet reported on the pod are read in every run",
    "resilience.liveness-dependency-path": "an exec probe's command is not kept without app-settings, so only HTTP probe paths are read for a dependency",
}


@pytest.mark.parametrize("variant", [v for v, _, _ in VARIANTS if v.endswith("-daily")])
def test_a_daily_run_judges_as_a_full_run_does_or_says_it_did_not_judge(runs, variant):
    """The daily run reads less (collectors/units.yaml). A check either gives the verdicts the full run gives on the same cluster, or it does not judge:
    `not-collected`, because it names under `needs` a unit the daily run leaves out, or `skip` with the reason, when only this cluster's data was
    missing (an ingress latency read from ALB metrics on EKS and from the controller's metrics elsewhere). A check that judged and found something
    else has read data that was not there: it needs the unit. The first run of this test found seven such checks, two of which reported
    databases as having no backup because the CronJob commands that name them are not kept by a daily run."""
    full = json.loads(runs[variant.removesuffix("-daily")]["findings.json"])
    daily = json.loads(runs[variant]["findings.json"])
    before = {r["id"]: r for r in full["check_results"]}
    after = {r["id"]: r for r in daily["check_results"]}

    def verdicts(doc, cid):
        return sorted((f["target"], f["status"]) for f in doc["findings"] if f["check"] == cid)

    wrong = []
    for cid, was in before.items():
        now = after[cid]
        if now["status"] == "not-collected" or cid in PARTIAL_IN_DAILY:
            continue
        if now["status"] == "skip" and was["status"] != "skip":
            assert now.get("reason"), f"{cid}: a skip names what was missing"
            continue
        if now["status"] != was["status"] or verdicts(daily, cid) != verdicts(full, cid):
            wrong.append((cid, was["status"], now["status"], len(verdicts(full, cid)), len(verdicts(daily, cid))))
    assert wrong == [], wrong
    assert any(r["status"] == "not-collected" for r in after.values())
    for cid in PARTIAL_IN_DAILY:
        assert len(verdicts(daily, cid)) <= len(verdicts(full, cid)), f"{cid} finds more in a daily run than in a full one"


@pytest.mark.parametrize("variant", [v for v, _, _ in VARIANTS if v.endswith("-daily")])
def test_a_daily_snapshot_holds_nothing_an_application_is_configured_with(tmp_path, variant):
    """After the daily mutation no object outside the system namespaces carries a command, args, a literal environment value or a ConfigMap key, and
    the files of the units the daily run leaves out are not there."""
    from lib.foundations import scrub

    _, fixture, mutate = next(v for v in VARIANTS if v[0] == variant)
    snap = regress.stage(fixture, tmp_path, mutate)
    assert not (snap / "aws").exists() and not (snap / "logs" / "node").exists() and not (snap / "logs" / "cloudwatch").exists() and not list((snap / "tools").glob("*.json"))

    def walk(o, ns):
        if isinstance(o, dict):
            if isinstance(o.get("kind"), str) and isinstance(o.get("metadata"), dict):
                ns = o["metadata"].get("namespace") or ns
            if not scrub.system_namespace(ns) and ns:
                assert not isinstance(o.get("command"), list) and not isinstance(o.get("args"), list), (ns, o.get("name"))
                assert not any(isinstance(e, dict) and "value" in e for e in o.get("env") or [] if isinstance(o.get("env"), list)), (ns, o.get("name"))
                if o.get("kind") == "ConfigMap":
                    assert "data" not in o and "binaryData" not in o, (ns, o["metadata"].get("name"))
            for v in o.values():
                walk(v, ns)
        elif isinstance(o, list):
            for v in o:
                walk(v, ns)

    seen = 0
    for f in sorted((snap / "objects").glob("*.json")):
        walk(json.loads(f.read_text(encoding="utf-8")), None)
        seen += 1
    assert seen > 10
    # A key name must not survive anywhere in its own ConfigMap: on a live cluster the keys were found in metadata.managedFields
    # (`fieldsV1.f:data.f:<key>`), which the walk above does not read (2026-11-14).
    keys = {(o["metadata"]["namespace"], o["metadata"]["name"]): set(o.get("data") or {}) for o in json.loads((fixture / "objects" / "configmaps.json").read_text(encoding="utf-8"))["items"]}
    checked = 0
    for o in json.loads((snap / "objects" / "configmaps.json").read_text(encoding="utf-8"))["items"]:
        ns, name = o["metadata"]["namespace"], o["metadata"]["name"]
        if scrub.system_namespace(ns):
            continue
        text = json.dumps(o)
        assert not [k for k in keys[(ns, name)] if f'"f:{k}"' in text or f'"{k}"' in text], (ns, name)
        checked += len(keys[(ns, name)])
    assert checked > 20


def test_summary_shape_doc_matches_the_summaries(runs):
    summaries = [json.loads(runs[v]["summary.json"]) for v, _, _ in VARIANTS if not v.endswith(("-degraded", "-daily"))]
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
    rec = evaluate.rules.ItemRecorder({"zeta": 1, "alpha": 2, "mid": 3, "unused": 4})
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
    assert [r["value"] for r in out["rows"]] == [0.5, None] and out["stats"] == {"min": 0.5, "max": 0.5, "mean": 0.5, "n": 1}
    assert not any(isinstance(r["value"], float) and math.isnan(r["value"]) for r in out["rows"])
    json.loads(json.dumps(out), parse_constant=lambda c: pytest.fail(f"non-JSON token {c}"))


def test_the_normalisation_hides_only_the_path_the_clock_and_the_version(tmp_path):
    from lib import __version__

    text = f'"snapshot": "{tmp_path}", "generated_at": "2026-11-07T10:00:00+09:00", "kubegap": "{__version__}", "rubric_version": "0.1.83", "instance": "10.{__version__}2:9100"\n| kubegap / rubric / signatures | {__version__} / 0.1.83 / 1.1.0 |\n| kubegap / 점검 항목 버전 / 로그 시그니처 버전 | {__version__} / 0.1.83 / 1.1.0 |'
    assert (
        regress.normalise(text, tmp_path)
        == f'"snapshot": "<snapshot>", "generated_at": "<generated_at>", "kubegap": "<kubegap>", "rubric_version": "0.1.83", "instance": "10.{__version__}2:9100"\n| kubegap / rubric / signatures | <kubegap> / 0.1.83 / 1.1.0 |\n| kubegap / 점검 항목 버전 / 로그 시그니처 버전 | <kubegap> / 0.1.83 / 1.1.0 |'
    )

"""#160: a reader of a missing `objects/<stem>.json` is told why the file is missing, so a wrong file name cannot pass as "the cluster has none".

The dump-all step records what the API served and what it wrote; `snapshot.object_file_status` judges a stem against that record; summarize writes
`collection.object_files`, run.log and report section 7-1 name the stems whose name is wrong, and an object check skips with the reason. The two
fixtures under tests/fixtures/api-resources/ hold the served kinds and the saved files of the EKS and the k3s reference clusters, so every literal
stem a reader spells is checked against two real API surfaces."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib.collection import collect
from lib.foundations import rubric, snapshot
from lib.foundations.runlog import RunLog, read_runlog
from lib.judgement import evaluate
from lib.output import render
from lib.summaries import summarize

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = sorted((ROOT / "tests" / "fixtures" / "api-resources").glob("*.json"))
STEM_RES = (
    re.compile(r'objects\((?:[\w.]+, *)?"([\w.-]+)"\)'),  # objects(snap, "pods"), cx.objects("pods")
    re.compile(r'"objects"\s*/\s*"([\w.-]+)\.json"'),  # snap / "objects" / "pods.json"
    re.compile(r"objects/([\w.-]+)\.json"),  # inputs: [objects/pods.json], source strings
)


def literal_stems() -> set[str]:
    """Every object file name lib/*.py and the checks spell out."""
    stems: set[str] = set()
    for f in [*(ROOT / "lib").rglob("*.py"), *(ROOT / "collectors").glob("*/checks.yaml")]:
        text = f.read_text(encoding="utf-8")
        for rx in STEM_RES:
            stems.update(rx.findall(text))
    return stems


def _record(served: list[str], **more) -> dict:
    return {"kinds": 0, "items": 0, "written": [], "served": served, "fetched_by_discovery": [], "failed": {}, "excluded": [], "not_permitted": [], "discovery_error": None, **more}


def _snap(tmp_path: Path, rec: dict | None, files: list[str] = ()) -> Path:
    (tmp_path / "objects").mkdir(parents=True, exist_ok=True)
    for stem in files:
        (tmp_path / "objects" / f"{stem}.json").write_text('{"items": []}', encoding="utf-8")
    if rec is not None:
        (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"collector": "core", "steps": {"objects.dump-all": rec}}, "_summary": {"mode": "full"}}), encoding="utf-8")
    return tmp_path


def _replay(tmp_path: Path, fx: dict) -> Path:
    """A snapshot folder with the files and the dump-all record of a fixture cluster."""
    rec = _record(fx["served"], fetched_by_discovery=fx["fetched_by_discovery"], excluded=fx["excluded"], not_permitted=fx["not_permitted"], written=[f for f in fx["files"] if "." in f])
    return _snap(tmp_path, rec, fx["files"])


# ---------- the status of one file ----------


def test_object_file_status_names_every_reason(tmp_path):
    rec = _record(
        ["pods", "jobs.batch", "cronjobs.batch", "deployments.apps", "secrets", "nodes.metrics.k8s.io", "leases.coordination.k8s.io", "bgppeers.metallb.io"],
        fetched_by_discovery=["deployments.apps", "cronjobs.batch"],
        excluded=["secrets"],
        not_permitted=["leases.coordination.k8s.io"],
        failed={"nodes.metrics.k8s.io": "timeout"},
    )
    snap = _snap(tmp_path, rec, ["pods", "jobs.batch", "deployments", "cronjobs"])
    st = lambda stem: snapshot.object_file_status(snap, stem, snapshot.dump_record(snap))  # noqa: E731
    assert st("pods") == "ok" and st("jobs.batch") == "ok" and st("deployments") == "ok"
    assert st("ipaddresspools.metallb.io") == "not-served", "a CRD that is not installed: the normal reason"
    assert st("secrets") == "excluded"
    assert st("leases.coordination.k8s.io") == "denied"
    assert st("nodes.metrics.k8s.io") == "failed"
    assert st("bgppeers.metallb.io") == "unlisted", "served, not excluded, not denied, not failed, and no file: the reader's name and the file name disagree"
    assert st("cronjobs.batch") == "unlisted", "#124: discovery wrote cronjobs.json; the readers opened cronjobs.batch.json and passed on nothing for a day"
    assert st("jobs") == "unlisted", "the short name of a served kind outside the core group: the reader must spell jobs.batch"
    assert st("cronjobs") == "ok" and snapshot.object_file_status(_snap(tmp_path / "b", rec, ["pods"]), "cronjobs", rec) == "unlisted", "the discovery kind by its short name"
    assert set(snapshot.OBJECT_FILE_STATUS) == {"ok", "not-served", "excluded", "denied", "failed", "unlisted", "no-record"}


def test_a_snapshot_without_a_dump_record_says_so(tmp_path):
    snap = _snap(tmp_path, None, ["pods"])
    assert snapshot.object_file_status(snap, "pods", snapshot.dump_record(snap)) == "ok"
    assert snapshot.object_file_status(snap, "jobs.batch", snapshot.dump_record(snap)) == "no-record"
    assert snapshot.object_file_status(snap, "jobs.batch", _record([], discovery_error="kubectl api-resources: timed out after 60s")) == "no-record", "a failed discovery lists nothing; not-served would be a lie"
    assert snapshot.object_file_status(snap, "jobs.batch", _record(["pods"], discovery_error="metrics.k8s.io: the server is currently unable to handle the request")) == "not-served", "a partial discovery still lists what it saw"
    assert snapshot.missing_reason("jobs.batch", "no-record") == "objects/jobs.batch.json missing: the snapshot has no dump-all record, or its API discovery failed"


def test_objects_records_what_it_was_asked_for(tmp_path):
    snap = _snap(tmp_path, _record(["pods", "cronjobs.batch"], fetched_by_discovery=["cronjobs.batch"]), ["pods", "cronjobs"])
    snapshot.forget_reads(snap)
    assert snapshot.objects(snap, "pods") == [] and snapshot.objects(snap, "cronjobs.batch") == [] and snapshot.objects(snap, "bgppeers.metallb.io") == []
    assert snapshot.object_files(snap) == {"bgppeers.metallb.io": "not-served", "cronjobs.batch": "unlisted", "pods": "ok"}
    snapshot.forget_reads(snap)
    assert snapshot.object_files(snap) == {}


# ---------- the dump-all step writes the record ----------


def test_dump_all_records_served_and_written(tmp_path, monkeypatch):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "pods.json").write_text('{"items": []}')
    res = [
        {"name": "pods", "full": "pods", "namespaced": True, "kind": "Pod", "apiversion": "v1"},
        {"name": "cronjobs", "full": "cronjobs.batch", "namespaced": True, "kind": "CronJob", "apiversion": "batch/v1"},
        {"name": "jobs", "full": "jobs.batch", "namespaced": True, "kind": "Job", "apiversion": "batch/v1"},
        {"name": "secrets", "full": "secrets", "namespaced": True, "kind": "Secret", "apiversion": "v1"},
        {"name": "leases", "full": "leases.coordination.k8s.io", "namespaced": True, "kind": "Lease", "apiversion": "coordination.k8s.io/v1"},
    ]
    monkeypatch.setattr(collect, "api_resources", lambda *a: (res, None))

    class R:
        def __init__(self, err):
            self.stderr, self.error = err, err

    def fake_json(args, **k):
        if args[1] == "leases.coordination.k8s.io":
            return None, R('Error from server (Forbidden): leases.coordination.k8s.io is forbidden: User "x" cannot list resource')
        return {"items": []}, None

    monkeypatch.setattr(collect.kube, "kubectl_json", fake_json)
    out = collect.dump_all("ctx", None, tmp_path, [], 10, RunLog(None), "core")
    assert out["served"] == ["pods", "cronjobs.batch", "jobs.batch", "secrets", "leases.coordination.k8s.io"]
    assert out["written"] == ["cronjobs", "jobs.batch"] and out["fetched_by_discovery"] == ["pods"], "discovery did not save CronJobs this time; the dump saves them under the one name every reader spells"
    assert (tmp_path / "objects" / "cronjobs.json").is_file() and not (tmp_path / "objects" / "cronjobs.batch.json").exists()
    assert snapshot.object_file_status(tmp_path, "cronjobs", out) == "ok" and out["excluded"] == ["secrets"] and out["not_permitted"] == ["leases.coordination.k8s.io"]
    assert snapshot.object_file_status(tmp_path, "jobs.batch", out) == "ok" and snapshot.object_file_status(tmp_path, "leases.coordination.k8s.io", out) == "denied"


# ---------- summarize, evaluate and the report carry it ----------


def test_summarize_writes_object_files_and_notes_the_wrong_names(tmp_path):
    snap = _snap(tmp_path, _record(["pods", "cronjobs.batch", "deployments.apps"], fetched_by_discovery=["cronjobs.batch", "deployments.apps"]), ["pods", "cronjobs", "deployments"])
    (snap / "inventory.json").write_text(
        json.dumps(
            {
                "context": "c",
                "taken_at": "2026-11-05T17:25:17+09:00",
                "cluster": {"platform": "k3s"},
                "profile": {"name": "lab"},
                "nodes": {"count": 0, "nodes": []},
                "namespaces": {"count": 0, "prod_like": []},
                "crds": {"count": 0},
                "node_access": {"method": "none"},
                "collectors_enabled": ["core"],
            }
        )
    )
    s = summarize.summarize(snap, echo=None)
    of = s["collection"]["object_files"]
    assert of["pods"] == "ok" and of["cronjobs"] == "ok" and of["deployments"] == "ok"
    assert "unlisted" not in of.values(), {k: v for k, v in of.items() if v == "unlisted"}
    assert all(v in ("ok", "not-served") for v in of.values()), of
    assert not [r for r in read_runlog(snap / "run.log") if r.get("kind") == "note" and r.get("stems")]
    # a reader that spells a served kind differently is named in run.log
    snapshot.forget_reads(snap)
    (snap / "objects" / "cronjobs.json").unlink()
    s = summarize.summarize(snap, echo=None)
    assert s["collection"]["object_files"]["cronjobs"] == "unlisted"
    notes = [r for r in read_runlog(snap / "run.log") if r.get("kind") == "note" and r.get("stems")]
    assert notes and notes[-1]["stems"] == ["cronjobs"], notes


def test_object_checks_skip_with_the_reason(tmp_path):
    """`scaling.karpenter-budget-zero` reads objects/nodepools.karpenter.sh.json and `security.networkpolicy-coverage` (cluster level) objects/networkpolicies.networking.k8s.io.json."""
    inv = {
        "context": "c",
        "taken_at": "2026-11-05T17:25:17+09:00",
        "cluster": {"platform": "eks"},
        "profile": {"name": "prod"},
        "nodes": {"count": 0, "nodes": []},
        "namespaces": {"count": 0, "prod_like": []},
        "crds": {"count": 0},
        "node_access": {"method": "none"},
        "collectors_enabled": ["core"],
    }
    snap = _snap(tmp_path, _record(["pods", "networkpolicies.networking.k8s.io"], not_permitted=["networkpolicies.networking.k8s.io"]), ["pods"])
    (snap / "inventory.json").write_text(json.dumps(inv))
    (snap / "MODE").write_text("full")
    out = evaluate.evaluate(snap, {}, echo=None)
    by_id = {r["id"]: r for r in out["check_results"]}
    assert by_id["scaling.karpenter-budget-zero"]["status"] == "skip" and by_id["scaling.karpenter-budget-zero"]["reason"] == "objects/nodepools.karpenter.sh.json missing: the cluster does not serve this kind"
    assert by_id["security.networkpolicy-coverage"]["status"] == "skip" and by_id["security.networkpolicy-coverage"]["reason"] == "objects/networkpolicies.networking.k8s.io.json missing: the ClusterRole does not grant list on this kind"
    (snap / "collect-result.json").unlink()
    out = evaluate.evaluate(snap, {}, echo=None)
    assert {r["id"]: r for r in out["check_results"]}["scaling.karpenter-budget-zero"]["reason"] == "objects/nodepools.karpenter.sh.json missing: the snapshot has no dump-all record, or its API discovery failed"


def test_report_section_7_1_names_the_stems(tmp_path):
    from tests.test_render import _snap as render_snap

    s = render_snap(tmp_path, False)
    summ = json.loads((s / "summary.json").read_text())
    summ["collection"]["object_files"] = {"pods": "ok", "bgppeers.metallb.io": "not-served", "ipaddresspools.metallb.io": "not-served", "cronjobs.batch": "unlisted"}
    (s / "summary.json").write_text(json.dumps(summ))
    text = render.render_details(s).read_text()
    assert "Kinds this cluster does not serve (2; a check that needs one of them is skipped, not passed): `bgppeers.metallb.io`, `ipaddresspools.metallb.io`" in text
    assert "Kinds this cluster serves but the snapshot has no file for (1; kubegap looked for the wrong file name, a kubegap defect, and the checks that read them judged nothing): `cronjobs.batch`" in text
    assert "`pods`" not in text.split("### 7-1")[1].split("###")[0]
    ko = render.render_details(s, language="ko").read_text()
    assert "이 클러스터가 제공하는데 수집 폴더에 파일이 없는 종류 1개예요" in ko and "`cronjobs.batch`" in ko


# ---------- every literal stem against two real clusters ----------


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_every_literal_stem_is_spelled_as_the_cluster_serves_it(fixture):
    """A stem whose resource name a cluster serves must be that cluster's full name (`jobs.batch`), or the short name of a kind discovery fetches (`cronjobs`).
    `cronjobs.batch` (#124) fails here: the kind is served as `cronjobs.batch` and discovery fetched it, so the file is `cronjobs.json`."""
    fx = json.loads(fixture.read_text(encoding="utf-8"))
    by_name: dict[str, set[str]] = {}
    for full in fx["served"]:
        by_name.setdefault(full.split(".", 1)[0], set()).add(full)
    discovery_short = {f.split(".", 1)[0] for f in fx["fetched_by_discovery"]}
    bad = []
    for stem in sorted(literal_stems()):
        name = stem.split(".", 1)[0]
        if name not in by_name:
            continue  # this cluster does not serve the kind; the other fixture or a later one checks it
        if not (stem in by_name[name] or (stem == name and name in discovery_short)):
            bad.append((stem, sorted(by_name[name])))
    assert not bad, f"{fixture.stem}: the reader's stem is not the file name: {bad}"
    assert "cronjobs" in discovery_short and "cronjobs.batch" in by_name["cronjobs"], "the fixture shows the #124 shape"


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_no_literal_stem_is_unlisted_on_a_reference_snapshot(tmp_path, fixture):
    """Replaying a reference snapshot's files and dump-all record: every stem a reader spells is on disk or a kind that cluster does not serve, never `unlisted`."""
    fx = json.loads(fixture.read_text(encoding="utf-8"))
    snap = _replay(tmp_path, fx)
    rec = snapshot.dump_record(snap)
    statuses = {stem: snapshot.object_file_status(snap, stem, rec) for stem in sorted(literal_stems())}
    wrong = {k: v for k, v in statuses.items() if v not in ("ok", "not-served")}
    assert not wrong, f"{fixture.stem}: {wrong}"
    assert statuses["pods"] == "ok" and statuses["cronjobs"] == "ok"
    assert snapshot.object_file_status(snap, "cronjobs.batch", rec) == "unlisted", "the #124 spelling is caught on this cluster"
    assert statuses["bgppeers.metallb.io"] == ("ok" if fx["platform"] == "k3s" else "not-served")


def test_fixtures_are_resource_names_only():
    for f in FIXTURES:
        fx = json.loads(f.read_text(encoding="utf-8"))
        assert set(fx) == {"note", "platform", "server_version", "served", "files", "fetched_by_discovery", "excluded", "not_permitted"}, f.name
        for key in ("served", "files", "fetched_by_discovery", "excluded", "not_permitted"):
            assert all(re.fullmatch(r"[a-z0-9.-]+", x) for x in fx[key]), (f.name, key)
        assert set(fx["excluded"]) >= {"secrets", "events"}, f.name
        assert not [s for s in fx["served"] if s not in fx["files"] and s.split(".", 1)[0] not in fx["files"] and s not in fx["excluded"] and s not in fx["not_permitted"] and s not in fx["fetched_by_discovery"]], (
            f"{f.name}: a served kind the snapshot did not save"
        )


def test_object_type_checks_read_files_the_fixtures_know():
    """Every `type: object` check's inputs are literal stems the two fixtures can judge (served by at least one of the two clusters)."""
    served = set()
    for f in FIXTURES:
        served.update(json.loads(f.read_text(encoding="utf-8"))["served"])
    short = {s.split(".", 1)[0] for s in served}
    for c in rubric.catalog():
        if c.get("type") != "object":
            continue
        for i in c.get("inputs") or []:
            stem = Path(i).stem
            assert stem in served or stem in short, (c["id"], stem)

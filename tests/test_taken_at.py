"""#165: every age, window and expiry a summary or a check computes is measured from the snapshot's `taken_at`, never from the wall clock, so the same
snapshot gives the same findings whenever it is read. `lib/foundations/snapshot.parse_ts` is the one timestamp reader and `lib/foundations/snapshot.taken_at` the one clock."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from lib.foundations import rubric, snapshot
from lib.judgement import evaluate
from lib.judgement.evaluate import Context
from lib.summaries import hygiene, k3s, summarize

ROOT = Path(__file__).resolve().parent.parent
TAKEN = "2026-11-05T17:25:17+09:00"  # the k3s reference snapshot
INV = {
    "context": "default",
    "taken_at": TAKEN,
    "cluster": {"platform": "k3s"},
    "profile": {"name": "lab"},
    "nodes": {"count": 1, "nodes": [{"name": "kkh2", "roles": ["control-plane", "etcd", "master"]}]},
    "namespaces": {"count": 0, "prod_like": []},
    "crds": {"count": 0},
    "node_access": {"method": "ssh"},
    "collectors_enabled": ["core", "k3s-platform"],
}
PLATFORM_TXT = """### meta
node=kkh2
### server
secrets_encrypt=Disabled, no configuration file found
db_kind=etcd
etcd_snapshots:
etcd-snapshot-kkh2-1793793600 file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-kkh2-1793793600 39608352 2026-11-04T12:00:00Z
etcd-snapshot-kkh2-1793836804 file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-kkh2-1793836804 39780384 2026-11-05T00:00:04Z
db_mb=594
### end
"""


# ---------- the readers ----------


def test_parse_ts_reads_every_form_the_snapshot_holds():
    assert snapshot.parse_ts("2026-11-05T08:25:17Z") == dt.datetime(2026, 11, 5, 8, 25, 17, tzinfo=dt.UTC)  # kubectl creationTimestamp
    assert snapshot.parse_ts(TAKEN) == dt.datetime(2026, 11, 5, 17, 25, 17, tzinfo=dt.timezone(dt.timedelta(hours=9)))  # inventory taken_at
    assert snapshot.parse_ts("2026-11-05T08:25:17.123456Z").microsecond == 123456
    assert snapshot.parse_ts("2025-12-29 02:07:42.385466 +0900 KST") == dt.datetime(2025, 12, 29, 2, 7, 42, tzinfo=dt.timezone(dt.timedelta(hours=9)))  # helm list `updated`
    assert snapshot.parse_ts('{"level":"INFO","time":"2026-11-04T15:24:35.000Z","message":"launched nodeclaim"}') == dt.datetime(2026, 11, 4, 15, 24, 35, tzinfo=dt.UTC)  # inside a log line
    assert snapshot.parse_ts("2026-11-05T08:25:17").tzinfo is dt.UTC, "no offset reads as UTC so every value compares with every other"
    assert snapshot.parse_ts(None) is None and snapshot.parse_ts("") is None and snapshot.parse_ts("not a time") is None and snapshot.parse_ts(0) is None


def test_taken_at_is_the_inventory_time():
    assert snapshot.taken_at(INV) == snapshot.parse_ts(TAKEN)
    assert snapshot.taken_at({}) is not None and snapshot.taken_at(None) is not None, "an inventory a test builds without the key gets the wall clock"


def test_no_summary_module_reads_the_wall_clock():
    """A sweep of `datetime.now`, `date.today`, `time.time` (also behind `__import__("time")`) and `monotonic` in lib/. What stays is the time a collection or a report *ran*
    (a stamp, a query window, a timeout), never an age a check judges. lib/summaries/karpenterctl.py measured the controller's uptime with `__import__("time").time()` until #145."""
    collection_time = {
        "albmetrics.py",
        "cwlogs.py",
        "cwmetrics.py",
        "discover.py",
        "firstrun.py",
        "prom.py",
        "runlog.py",
        "setup.py",
        "paths.py",
        "diff.py",
        "render.py",
        "prune.py",
        "node.py",
        "portfwd.py",
        "shell.py",
    }  # the last three time a command or a wait
    clock = re.compile(r"datetime\.now\(|date\.today\(|utcnow\(|time\.time\(|__import__\(\"time\"\)|monotonic\(")
    left = []
    for f in sorted((ROOT / "lib").rglob("*.py")):
        if f.name in collection_time or f.parent.name == "collect":
            continue  # lib/collection/collect/: the runner and its steps time commands and the AWS date placeholders, collection-time by nature
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not clock.search(line):
                continue
            if (f.name == "summarize.py" or f.parent.name == "evaluate") and ("generated_at" in line or "removed_at" in line):
                continue  # when this file was written
            if f.name == "snapshot.py" and "taken_at" in line:
                continue  # the one fallback, for an inventory without the key
            left.append(f"{f.name}:{n}: {line.strip()}")
    assert not left, left


# ---------- the same snapshot gives the same result whenever it is read ----------


def _k3s_snapshot(snap: Path) -> None:
    (snap / "objects").mkdir(parents=True)
    (snap / "inventory.json").write_text(json.dumps(INV), encoding="utf-8")
    (snap / "MODE").write_text("full", encoding="utf-8")
    node = {
        "metadata": {"name": "kkh2", "annotations": {"k3s.io/node-args": json.dumps(["server", "--disable", "traefik"])}, "labels": {}},
        "status": {"addresses": [{"type": "InternalIP", "address": "10.0.0.2"}], "nodeInfo": {"kubeletVersion": "v1.33.5+k3s1"}},
        "spec": {},
    }
    (snap / "objects" / "nodes.json").write_text(json.dumps({"items": [node]}), encoding="utf-8")
    (snap / "logs" / "node" / "kkh2").mkdir(parents=True)
    (snap / "logs" / "node" / "kkh2" / "k3s-platform.txt").write_text(PLATFORM_TXT, encoding="utf-8")


def _clock_at(monkeypatch, when: dt.datetime) -> None:
    """Move the process clock: every `datetime.now()` and `date.today()` in lib returns `when`."""

    class _Date(dt.date):
        @classmethod
        def today(cls):
            return cls(when.year, when.month, when.day)

    class _Datetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return when.astimezone(tz) if tz else when.replace(tzinfo=None)

    monkeypatch.setattr(dt, "datetime", _Datetime)
    monkeypatch.setattr(dt, "date", _Date)


def test_etcd_snapshot_age_is_measured_from_the_snapshot_time(tmp_path, monkeypatch):
    """The issue's observation: a k3s snapshot summarized 10 hours later said `latest 27.1h ago` and failed platform.k3s-etcd-snapshot-stale."""
    _k3s_snapshot(tmp_path)
    taken = snapshot.parse_ts(TAKEN)
    results = []
    for later in (dt.timedelta(0), dt.timedelta(hours=10), dt.timedelta(days=40)):
        _clock_at(monkeypatch, taken + later)
        s = summarize.summarize(tmp_path, echo=None)
        e = evaluate.evaluate(tmp_path, {}, echo=None)
        server = s["k3s"]["nodes"][0]["server"]
        assert server["etcd_snapshots"][-1]["age_h"] == 8.4, "17:25:17+09:00 minus 00:00:04Z"
        assert server["snapshot_latest_age_h"] == 8.4
        stale = next(r for r in e["check_results"] if r["id"] == "platform.k3s-etcd-snapshot-stale")
        assert stale["status"] == "done" and stale["counts"] == {"pass": 1}, stale
        s.pop("generated_at")
        s.pop("run")  # run.log grows with every summarize
        e.pop("generated_at")
        results.append((s, e["findings"], e["checks"]["by_status"]))
    assert results[0] == results[1] == results[2], "summarize and evaluate on one snapshot give the same result whenever they run"


def test_configmap_age_is_measured_from_the_snapshot_time(tmp_path):
    (tmp_path / "objects").mkdir()
    created = (snapshot.parse_ts(TAKEN) - dt.timedelta(days=30)).astimezone(dt.UTC).isoformat().replace("+00:00", "Z")
    for stem, objs in (
        ("configmaps", [{"metadata": {"namespace": "p", "name": "old", "creationTimestamp": created, "labels": {}, "annotations": {}}, "data": {"k": "v"}}]),
        ("pods", []),
        ("deployments", []),
        ("statefulsets", []),
        ("daemonsets", []),
        ("cronjobs", []),
        ("jobs.batch", []),
        ("services", []),
        ("serviceaccounts", []),
        ("persistentvolumeclaims", []),
    ):
        (tmp_path / "objects" / f"{stem}.json").write_text(json.dumps({"items": objs}), encoding="utf-8")
    cx = hygiene.Ctx(tmp_path, {"taken_at": TAKEN, "namespaces": {"prod_like": ["p"]}})
    assert cx.now == snapshot.parse_ts(TAKEN)
    row = next(r for r in hygiene._orphans(cx)["orphan_configmaps"] if r["name"] == "old")
    assert row["age_days"] == 30


def test_evaluate_today_is_the_snapshot_date():
    cx = Context(Path("/nonexistent"), {"taken_at": TAKEN}, {}, {"name": "prod"})
    assert cx.today == dt.date(2026, 11, 5), "the operator's calendar date of the snapshot (+09:00), not UTC"
    assert cx.days_until("2026-11-15") == 10
    assert Context(Path("/nonexistent"), {"taken_at": TAKEN, "today": "2026-10-25"}, {}, {"name": "prod"}).today == dt.date(2026, 10, 25), "the embedded test cases pin `today` and win"


def test_suppressions_expire_against_the_snapshot_date():
    sup = [{"check": "a", "until": "2026-11-04"}, {"check": "b", "until": "2026-11-05"}, {"check": "c"}]
    active, expired = rubric.active_suppressions(sup, dt.date(2026, 11, 5))
    assert [s["check"] for s in active] == ["b", "c"] and [s["check"] for s in expired] == ["a"]
    with pytest.raises(TypeError):
        rubric.active_suppressions(sup)  # no default: the caller passes `Context.today`


def test_k3s_now_reaches_the_parser():
    out = k3s._parse_server(PLATFORM_TXT.splitlines()[3:-1], snapshot.parse_ts(TAKEN))
    assert [s["age_h"] for s in out["etcd_snapshots"]] == [20.4, 8.4]

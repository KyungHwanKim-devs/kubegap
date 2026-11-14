"""`kubegap show` (lib/output/show.py): what an agent reads a snapshot through. Every view says the whole before it shows a part."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lib.commands import regress
from lib.output import show


@pytest.fixture(scope="module")
def snap():
    fixture = next(f for f in regress.fixtures() if f.name.endswith("-k3s"))
    with tempfile.TemporaryDirectory() as d:
        s = regress.stage(fixture, Path(d))
        regress.run(s)
        yield s


def test_findings_start_with_the_totals_and_a_long_target_list_says_how_many_more(snap):
    fd = json.loads((snap / "findings-draft.json").read_text())
    found = [f for f in fd["findings"] if f["status"] in ("fail", "warn")]
    text = show.findings(snap)
    assert text.splitlines()[0].startswith(f"findings of {snap.name} (scale ") and f"fail {sum(1 for f in found if f['status'] == 'fail')} (" in text.splitlines()[0]
    big = max({f["check"] for f in found}, key=lambda c: sum(1 for f in found if f["check"] == c))
    n = sum(1 for f in found if f["check"] == big)
    line = text.split(f"\n{big}  [")[1].split("\n")[1]
    assert line.startswith(f"  targets {n}: ") and f"… and {n - show.INLINE} more (kubegap show finding '{big}.*')" in line
    high = show.findings(snap, severity="high", status="fail")
    assert "filter: severity high, status fail → " in high and f" of {len(found)}" in high


def test_one_finding_shows_everything_the_rule_saw_and_where_to_look_next(snap):
    fd = json.loads((snap / "findings-draft.json").read_text())
    f = next(x for x in fd["findings"] if x["check"] == "security.plaintext-configmap-secret" and x["status"] == "fail")
    text = show.finding(snap, f["id"])
    assert text.startswith("1 finding match") and f"== {f['id']}" in text and "judged from (everything the rule saw):" in text
    for name in f["details"]["mounted_by"]:  # the whole list, not the first few
        assert name in text
    assert "kubegap show table security.secrets.plaintext_configmap" in text and "learn topic: secrets-in-plain-text" in text
    many = show.finding(snap, "resilience.single-replica-in-prod")
    total = sum(1 for x in fd["findings"] if x["check"] == "resilience.single-replica-in-prod")
    assert many.startswith(f"{total} findings match") and "showing the first 5 (--all for every one)" in many
    with pytest.raises(show.ShowError, match="no finding matches"):
        show.finding(snap, "no.such-check")


def test_a_table_says_how_many_rows_before_it_shows_some(snap):
    summary = json.loads((snap / "summary.json").read_text())
    rows = summary["resilience"]["backup"]["rows"]
    text = show.table(snap, "resilience.backup.rows", limit=2)
    assert text.startswith(f"resilience.backup.rows: {len(rows)} rows; showing 1–2 of {len(rows)} (--offset 2 for the next, --all for every row)")
    assert len([ln for ln in text.splitlines() if ln.startswith("- ")]) == 2
    everything = show.table(snap, "resilience.backup.rows", all_=True)
    assert "showing" not in everything.splitlines()[0] and len([ln for ln in everything.splitlines() if ln.startswith("- ")]) == len(rows)
    cm = summary["security"]["secrets"]["plaintext_configmap"][0]
    one = show.table(snap, "security.secrets.plaintext_configmap", where=[f"name={cm['name']}"], field="mounted_by")
    assert f"where name={cm['name']}: 1 of " in one and f"mounted_by (list of {len(cm['mounted_by'])}): " in one and cm["mounted_by"][-1] in one
    with pytest.raises(show.ShowError, match="is not in 'security"):
        show.table(snap, "security.nope")


def test_a_list_inside_a_row_is_shortened_only_with_its_count():
    assert show.brief(list(range(3))) == "[0, 1, 2]"
    assert show.brief(list(range(12))) == "12 items: [0, 1, 2, 3, 4, … and 7 more]"
    assert show.brief({"a": 1, "b": list(range(9))}) == "{a: 1, b: 9 items: [0, 1, 2, … and 6 more]}"


def test_a_raw_object_and_the_sections_and_a_learn_topic(snap):
    cj = json.loads((snap / "objects" / "cronjobs.json").read_text())["items"][0]["metadata"]
    text = show.object_(snap, "cronjob", f"{cj['namespace']}/{cj['name']}")
    assert text.startswith(f"cronjobs {cj['namespace']}/{cj['name']} (") and '"kind": "CronJob"' in text
    with pytest.raises(show.ShowError, match="objects of that kind"):
        show.object_(snap, "cronjob", "nope/x")
    assert "resilience.backup.rows: list of " in show.tables(snap)
    assert '"topic": "backup-off-cluster"' in show.learn(None, "resilience.no-backup")

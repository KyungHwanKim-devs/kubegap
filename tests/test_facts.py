"""llm/facts.json is checked and completed by code before a sentence is written from it (lib/output/facts.py), and the sections no agent
writes come from the snapshot (lib/output/sections.py). Each rule here is one a report of 2026-11-14 broke."""

from __future__ import annotations

import json
from pathlib import Path

from lib.output import facts as F
from lib.output import sections as S


def _finding(check, target, sev="high", status="fail", nature="state"):
    return {"id": f"{check}.{target}", "check": check, "target": target, "status": status, "severity_default": sev, "nature": nature}


FINDINGS = [
    _finding("resilience.no-backup", "cluster", "critical"),
    _finding("resilience.replicas-same-node", "prod/deployment/api", "high"),
    _finding("observability.alertmanager-notification-failed", "slack", "high", nature="occurrence"),
    _finding("traffic.pod-not-ready", "prod/web", "medium", nature="occurrence"),
    _finding("hygiene.x", "prod/a", "low"),
]


def _snap(tmp_path: Path, findings=FINDINGS, suppressed=(), mode="full", scale=None) -> Path:
    snap = tmp_path / "c" / "2026-11-14T12-00-00"
    snap.mkdir(parents=True)
    (snap / "MODE").write_text(mode)
    fd = {"findings": list(findings), "suppressed": list(suppressed), "scale": scale or {"name": "small", "source": "answered"}}
    (snap / "findings-draft.json").write_text(json.dumps(fd))
    (snap / "inventory.json").write_text(json.dumps({"taken_at": "2026-11-14T12:00:00+09:00", "components_present": ["coredns", "istio", "k3s", "reloader"]}))
    return snap


def _problem(pid, ids, loss="outage", **over):
    p = {
        "id": pid,
        "title": "t",
        "finding_ids": ids,
        "targets": [],
        "picked": {"loss": loss, "reason": "r"},
        "cause": {"statement": "s", "certainty": "confirmed", "evidence": []},
        "check_methods": [{"kind": "metric", "what": "m"}],
        "solutions": [{"approach": "a"}],
    }
    p.update(over)
    return p


def _facts(**over):
    f = {
        "schema": 2,
        "problems": [_problem("1", ["resilience.no-backup.cluster"], "irreversible"), _problem("2", ["resilience.replicas-same-node.*"])],
        "happened": {"incidents": [{"id": "A", "title": "alerts dropped", "state": "ended", "finding_ids": ["observability.alertmanager-notification-failed.slack", "traffic.pod-not-ready.*"], "exposed": ["2"]}]},
        "next": [],
        "limits": [],
        "analysis": {},
    }
    f.update(over)
    return f


def test_facts_that_follow_the_contract_pass(tmp_path):
    assert F.check(_facts(), _snap(tmp_path), "full") == []


def test_an_older_shape_is_refused_by_its_schema(tmp_path):
    assert "schema" in F.check({"problems": []}, _snap(tmp_path), "full")[0]


def test_a_serious_failure_left_in_no_list_is_named(tmp_path):
    out = F.check(_facts(problems=[_problem("2", ["resilience.replicas-same-node.*"])]), _snap(tmp_path), "full")
    assert any("in no list" in e and "resilience.no-backup.cluster" in e for e in out)


def test_something_that_occurred_and_is_over_is_not_a_problem(tmp_path):
    ended = _problem("3", ["observability.alertmanager-notification-failed.slack"], state="ended")
    out = F.check(_facts(problems=[*_facts()["problems"], ended], happened={"incidents": []}), _snap(tmp_path), "full")
    assert any("problem 3" in e and "happened.incidents" in e for e in out)


def test_problems_are_ordered_by_severity_then_by_what_is_lost(tmp_path):
    f = _facts()
    f["problems"].reverse()
    assert any("not in order" in e for e in F.check(f, _snap(tmp_path), "full"))
    same = [_finding("a.x", "t", "high"), _finding("b.y", "t", "high")]
    f = _facts(problems=[_problem("1", ["a.x.t"], "degraded"), _problem("2", ["b.y.t"], "irreversible")], happened={"incidents": []})
    assert any("not in order" in e for e in F.check(f, _snap(tmp_path / "s", same), "full"))


def test_a_problem_says_why_it_was_picked_how_to_see_it_and_what_to_do(tmp_path):
    bad = _problem("1", ["resilience.no-backup.cluster"], "irreversible", picked={"loss": "big"}, check_methods=[{"kind": "command", "what": "kubectl"}], solutions=[])
    out = "\n".join(F.check(_facts(problems=[bad, _facts()["problems"][1]]), _snap(tmp_path), "full"))
    for part in ("picked.loss", "picked.reason", "commands only", "no solutions"):
        assert part in out, part


def test_severity_follows_the_recorded_changes_and_a_more_severe_entry_cannot_wait_in_next(tmp_path):
    snap = _snap(tmp_path)
    f = _facts(analysis={"severity_changes": [{"finding_id": "resilience.replicas-same-node.*", "final": "low", "reason": "one replica by design"}]})
    done = F.complete(f, snap)
    assert [p["severity"] for p in done["problems"]] == ["critical", "low"]
    f = _facts(problems=[_problem("2", ["resilience.replicas-same-node.*"])], next=[{"id": "n1", "title": "backup", "finding_ids": ["resilience.no-backup.cluster"]}])
    assert any("next holds a critical entry" in e for e in F.check(f, snap, "full"))
    assert any("severity_changes" in e for e in F.check(_facts(analysis={"severity_changes": [{"finding_id": "x"}]}), snap, "full"))


def test_a_source_outside_the_snapshot_is_refused(tmp_path):
    snap = _snap(tmp_path)
    p = _problem("1", ["resilience.no-backup.cluster"], "irreversible", facts=[{"what": "values", "value": "none", "source_file": "/home/u/work/manifests/values.yaml"}])
    f = _facts(problems=[p, _facts()["problems"][1]], analysis={"files_read": ["objects/pods.json", str(snap.parent / "2026-11-11T00-00-00" / "summary.json"), "/home/u/work/manifests/values.yaml"]})
    out = [e for e in F.check(f, snap, "full") if "outside the snapshot" in e]
    assert len(out) == 2 and all("/home/u/work/manifests/values.yaml" in e for e in out)


def test_limits_are_one_of_three_kinds_and_say_what_they_weaken(tmp_path):
    f = _facts(limits=[{"kind": "not-seen", "what": "x"}, {"kind": "no-data", "what": "ingress request metrics"}])
    out = [e for e in F.check(f, _snap(tmp_path), "full") if e.startswith("limits")]
    assert len(out) == 2 and "kind must be" in out[0] and "weakens" in out[1]


def test_a_daily_run_reports_what_happened_and_picks_no_problems(tmp_path):
    snap = _snap(tmp_path, mode="daily")
    assert any("daily run does not pick problems" in e for e in F.check(_facts(), snap, "daily"))
    f = _facts(problems=[], next=[{"id": "n1", "title": "rest", "finding_ids": ["resilience.no-backup.cluster", "resilience.replicas-same-node.*"]}])
    f["happened"]["incidents"][0]["exposed"] = ["n1"]
    assert F.check(f, snap, "daily") == []


def test_who_declares_a_target_comes_from_the_snapshot_and_is_none_without_evidence(tmp_path):
    snap = _snap(tmp_path)
    summary = {
        "hygiene": {"templating": {"owners": [{"workload": "prod/deployment/api", "managed_by": "argocd", "argocd_app": "shop"}, {"workload": "monitoring/statefulset/prom", "managed_by": "helm", "helm_release": "kps"}]}},
        "argocdctl": {"applications": {"count": 1, "rows": [{"name": "shop", "repo_url": "https://example.com/org/manifests", "path": "prod/shop", "target_revision": "HEAD", "self_heal": True}]}},
    }
    (snap / "summary.json").write_text(json.dumps(summary))
    f = _facts()
    f["problems"][1]["targets"] = ["prod/deployment/api", "prod/api", "monitoring/prom", "kube-system/deployment/coredns"]
    d = F.complete(f, snap)["problems"][1]["declared_in"]
    assert d["prod/deployment/api"] == {"managed_by": "argocd", "argocd_app": "shop", "repo_url": "https://example.com/org/manifests", "path": "prod/shop", "target_revision": "HEAD", "self_heal": True}
    assert d["prod/api"] == d["prod/deployment/api"] and d["monitoring/prom"] == {"managed_by": "helm", "helm_release": "kps"}
    assert d["kube-system/deployment/coredns"] is None


def _with_diff(snap: Path, report: bool) -> None:
    base = snap.parent / "2026-11-11T14-00-00"
    base.mkdir()
    (base / "inventory.json").write_text(json.dumps({"taken_at": "2026-11-11T14:08:33+09:00"}))
    if report:
        (base / "report.md").write_text("r")
    df = {
        "new": [{"id": "n", "status": "fail", "severity_default": "high"}, {"id": "w", "status": "warn", "severity_default": "high"}],
        "resolved": [{"id": "r1", "status": "fail", "severity_default": "high"}, {"id": "r2", "status": "fail", "severity_default": "high"}],
        "changed": [{"id": "c", "status": ["warn", "fail"], "severity_default": ["medium", "medium"]}, {"id": "d", "status": ["fail", "warn"], "severity_default": ["high", "high"]}],
        "criteria_changes": {"severity_changed": [{"id": "s"}], "note": "text"},
    }
    (snap / "diff.json").write_text(json.dumps({"a": str(base), "findings": df}))


def test_numbers_show_what_went_away_and_what_is_new_against_one_baseline(tmp_path):
    snap = _snap(tmp_path, scale={"name": "small", "source": "guessed", "nodes": 2})
    _with_diff(snap, report=True)
    text = S.numbers(snap, "ko")
    assert "| high | 2 | 0 | 3 | 1 |" in text and "| medium | 1 | 0 | 0 | 1 |" in text
    assert "비교 기준은 2026-11-11 14:08 full 점검" in text and "리포트가 있는 가장 최근 점검" in text
    assert "운영 규모 소형" in text and "노드 2대로 짐작" in text and "1건은 클러스터가 아니라" in text
    en = S.numbers(snap, "en")
    assert "Compared with the full run of 2026-11-11 14:08, the last one that has a report." in en and "scale small" in en


def test_numbers_without_a_baseline_have_no_comparison_columns(tmp_path):
    text = S.numbers(_snap(tmp_path), "ko")
    assert "비교할 이전 full 점검이 없습니다." in text and "| critical | 1 | 0 |\n" in text + "\n"


def test_what_was_decided_not_to_do_is_only_what_the_config_records(tmp_path):
    sup = [{"check": "coredns.availability", "target": "cluster", "suppressed_by": {"reason": "two nodes; control plane stays single", "until": "2027-01-01"}}]
    text = S.declined(_snap(tmp_path, suppressed=sup), "ko")
    assert "`coredns.availability` — cluster: two nodes; control plane stays single (2027-01-01까지)" in text
    assert "`suppress`에 이유와 함께" in S.declined(_snap(tmp_path / "none"), "ko")


def test_limits_come_in_three_groups_with_what_code_knows_added(tmp_path):
    snap = _snap(tmp_path)
    f = {"limits": [{"kind": "no-data", "what": "인그레스 요청 메트릭이 없습니다.", "weakens": "재부팅 동안 사용자가 받은 오류 수를 모릅니다", "to_see": "ingress-nginx 컨트롤러 메트릭을 켭니다"}]}
    text = S.limits(f, snap, "ko", skipped=[{"id": "grafana-token", "header": "Grafana 토큰", "gain": ["Grafana에서 직접 만든 대시보드 목록"]}])
    assert text.index("클러스터에 데이터가 없어서") < text.index("kubegap이 아직 읽지 못하는 것") < text.index("보지 않기로 고른 것")
    assert "- 인그레스 요청 메트릭이 없습니다.\n  - 약해지는 결론: 재부팅 동안 사용자가 받은 오류 수를 모릅니다.\n  - 보려면: ingress-nginx 컨트롤러 메트릭을 켭니다." in text
    assert "컴포넌트 2개는 오브젝트와 메트릭으로만 읽었습니다. kubegap에 전용 점검 항목이 없습니다: istio, reloader." in text  # coredns has checks; k3s is the platform
    assert "- Grafana 토큰.\n  - 약해지는 결론: Grafana에서 직접 만든 대시보드 목록.\n  - 보려면: `/kubegap setup`에서 다시 고르기." in text


def test_a_version_past_its_end_of_support_is_weighed_one_step_higher(tmp_path):
    """A date already passed grows while it waits (no patches, a longer upgrade path), so the problem is compared one step above what it loses today."""
    findings = [_finding("resilience.no-backup", "cluster"), {**_finding("platform.k8s-version-eol", "cluster"), "overdue": True}, _finding("observability.prometheus-no-persistence", "monitoring")]
    snap = _snap(tmp_path, findings)
    eol, prom = _problem("1", ["platform.k8s-version-eol.cluster"], "partial"), _problem("2", ["observability.prometheus-no-persistence.monitoring"], "outage")
    base = {"problems": [_problem("0", ["resilience.no-backup.cluster"], "irreversible")]}
    order = lambda *ps: [e for e in F.check({**_facts(), **base, "problems": base["problems"] + list(ps)}, snap, "full") if "not in order" in e]  # noqa: E731
    assert order(eol, prom) == []  # partial, one step up, ties with outage
    behind = order(_problem("2", ["observability.prometheus-no-persistence.monitoring"], "partial"), eol)  # the same loss on paper, but the overdue one goes first
    assert behind and "overdue" in behind[0]

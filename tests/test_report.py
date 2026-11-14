"""A full report is written by the agent that analysed the run; code holds what it can vouch for (lib/output/outline.py, report.py,
sections.py): nothing serious left out, the problems in order, one title per entry wherever it appears, no address from memory, and the
sections no agent writes."""

from __future__ import annotations

import json
from pathlib import Path

from lib.output import outline as F
from lib.output import report
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


def test_who_declares_a_target_comes_from_the_snapshot_and_is_none_without_evidence(tmp_path):
    snap = _snap(tmp_path)
    summary = {
        "hygiene": {"templating": {"owners": [{"workload": "prod/deployment/api", "managed_by": "argocd", "argocd_app": "shop"}, {"workload": "monitoring/statefulset/prom", "managed_by": "helm", "helm_release": "kps"}]}},
        "argocdctl": {"applications": {"count": 1, "rows": [{"name": "shop", "repo_url": "https://example.com/org/manifests", "path": "prod/shop", "target_revision": "HEAD", "self_heal": True}]}},
    }
    (snap / "summary.json").write_text(json.dumps(summary))
    owners = F.owners(snap)
    d = {t: F.declared_in(owners, t) for t in ("prod/deployment/api", "prod/api", "monitoring/prom", "kube-system/deployment/coredns")}
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
    assert text.startswith("## 고치지 않기로 정해 둔 항목")
    assert S.declined(_snap(tmp_path / "none"), "ko") == ""


def test_limits_come_in_three_groups_with_what_code_knows_added(tmp_path):
    snap = _snap(tmp_path)
    f = {"limits": [{"kind": "no-data", "what": "인그레스 요청 메트릭이 없습니다.", "weakens": "재부팅 동안 사용자가 받은 오류 수를 모릅니다", "to_see": "ingress-nginx 컨트롤러 메트릭을 켭니다"}]}
    text = S.limits(f, snap, "ko", skipped=[{"id": "grafana-token", "header": "Grafana 토큰", "gain": ["Grafana에서 직접 만든 대시보드 목록"]}])
    assert text.index("클러스터에 데이터가 없어서") < text.index("kubegap이 아직 읽지 못하는 것") < text.index("첫 실행 질문에서 읽지 않기로 답하신 것")
    assert "- 인그레스 요청 메트릭이 없습니다.\n  - 약해지는 결론: 재부팅 동안 사용자가 받은 오류 수를 모릅니다.\n  - 보려면: ingress-nginx 컨트롤러 메트릭을 켭니다." in text
    assert "컴포넌트 2개는 오브젝트와 메트릭으로만 읽었습니다. kubegap에 전용 점검 항목이 없습니다: istio, reloader." in text  # coredns has checks; k3s is the platform
    assert "- Grafana 토큰.\n  - 답하면 더 보는 것: Grafana에서 직접 만든 대시보드 목록.\n  - 보려면: `/kubegap setup`에서 다시 고를 수 있습니다." in text


SECTIONS = "\n\n".join(f"### {s}\n\ntext." for s in ("무슨 일인가", "왜 생기나", "추천 점검 방법", "추천 해결 방안", "근거", "더 읽을 것"))
AREAS = dict.fromkeys(F.AREAS, "이번 점검에서 문제를 찾지 못했습니다.")


def _outline(**over):
    o = {
        "broken_now": [],
        "happened": [{"title": "알림 2건이 전달되지 않음", "state": "ended", "finding_ids": ["observability.alertmanager-notification-failed.slack", "traffic.pod-not-ready.*"]}],
        "problems": [
            {"title": "백업이 클러스터 밖에 없음", "loss": "irreversible", "finding_ids": ["resilience.no-backup.cluster"]},
            {"title": "레플리카가 한 노드에 있음", "loss": "outage", "finding_ids": ["resilience.replicas-same-node.*"]},
        ],
        "next": [],
        "area_summary": dict(AREAS),
    }
    o.update(over)
    return o


def _write(snap: Path, outline: dict, overview: str | None = None, problems: list[str] | None = None) -> None:
    d = snap / "report"
    d.mkdir(exist_ok=True)
    (d / "outline.json").write_text(json.dumps(outline, ensure_ascii=False))
    happened = "\n\n".join(f"### {i['title']}\n\n일어난 일입니다." for i in outline.get("happened") or [])
    (d / "overview.md").write_text(overview if overview is not None else f"## 이미 일어난 일\n\n{happened}\n\n## 그다음으로 큰 문제\n\n없습니다.\n")
    for n, p in enumerate(outline.get("problems") or [], 1):
        text = problems[n - 1] if problems else f"## {n}. {p['title']}\n\n**고른 이유.** 이유입니다.\n\n{SECTIONS}\n"
        (d / f"problem-{n}.md").write_text(text)


def test_an_outline_that_keeps_its_promises_has_nothing_to_fix(tmp_path):
    snap = _snap(tmp_path)
    assert F.check(_outline(), snap) == []
    _write(snap, _outline())
    assert report.problems_with(snap, "ko") == []


def test_the_outline_is_refused_for_what_it_leaves_out_or_puts_in_the_wrong_order(tmp_path):
    snap = _snap(tmp_path)
    one = _outline()["problems"]
    assert any("1 critical or high failures are in no list" in e and "resilience.replicas-same-node.prod/deployment/api" in e for e in F.check(_outline(problems=one[:1]), snap))
    assert any("not in order" in e for e in F.check(_outline(problems=[one[1], one[0]]), snap))  # high before critical
    assert any("finding id no.such.id is not in findings-draft.json" in e for e in F.check(_outline(next=[{"title": "x", "finding_ids": ["no.such.id"]}]), snap))
    assert any("problems is empty" in e for e in F.check(_outline(problems=[], next=[{"title": "x", "finding_ids": ["resilience.no-backup.cluster", "resilience.replicas-same-node.*"]}]), snap))
    lowered = _outline(problems=one[1:], next=[{"title": "backup", "finding_ids": ["resilience.no-backup.cluster"]}])
    assert any("next holds a critical entry" in e for e in F.check(lowered, snap))
    assert F.check({**lowered, "severity_changes": [{"finding_id": "resilience.no-backup.cluster", "final": "medium", "reason": "snapshots and dumps exist"}]}, snap) == []
    assert any("unknown area ['node']" in e for e in F.check(_outline(area_summary={**AREAS, "node": "x"}), snap))
    assert any("no line for cost" in e for e in F.check(_outline(area_summary={k: v for k, v in AREAS.items() if k != "cost"}), snap))


def test_a_version_past_its_end_of_support_is_weighed_one_step_higher(tmp_path):
    findings = [_finding("resilience.no-backup", "cluster"), {**_finding("platform.k8s-version-eol", "cluster"), "overdue": True}, _finding("observability.prometheus-no-persistence", "monitoring")]
    snap = _snap(tmp_path, findings)
    backup = {"title": "b", "loss": "irreversible", "finding_ids": ["resilience.no-backup.cluster"]}
    eol = {"title": "e", "loss": "partial", "finding_ids": ["platform.k8s-version-eol.cluster"]}

    def order(*ps):
        return [e for e in F.check(_outline(happened=[], problems=[backup, *ps]), snap) if "not in order" in e]

    assert order(eol, {"title": "p", "loss": "outage", "finding_ids": ["observability.prometheus-no-persistence.monitoring"]}) == []  # partial, one step up, ties with outage
    assert order({"title": "p", "loss": "partial", "finding_ids": ["observability.prometheus-no-persistence.monitoring"]}, eol)  # the same loss on paper, but the overdue one goes first


def test_a_heading_that_differs_from_the_outline_is_refused_so_one_title_cannot_say_two_things(tmp_path):
    snap = _snap(tmp_path)
    o = _outline()
    _write(snap, o, problems=[f"## 1. 백업이 클러스터 밖에 있을 수도 있음\n\n{SECTIONS}\n", f"## 2. {o['problems'][1]['title']}\n\n{SECTIONS}\n"])
    issues = report.problems_with(snap, "ko")
    assert len(issues) == 1 and "problem-1.md must start with `## 1. 백업이 클러스터 밖에 없음` (the outline's title)" in issues[0]
    _write(snap, o, overview="## 이미 일어난 일\n\n### 다른 제목\n\n글.\n\n## 그다음으로 큰 문제\n\n없습니다.\n")
    assert any("its `### ` headings must be the outline's happened titles" in e for e in report.problems_with(snap, "ko"))


def test_what_a_reader_should_not_get_is_named_file_by_file(tmp_path):
    snap = _snap(tmp_path)
    fd = json.loads((snap / "findings-draft.json").read_text())
    fd["learn"] = [{"topic": "backup-off-cluster", "checks": ["resilience.no-backup"], "reading": [{"title": "k3s", "url": "https://docs.k3s.io/cli/etcd-snapshot"}]}]
    (snap / "findings-draft.json").write_text(json.dumps(fd))
    o = _outline()
    good = f"## 2. {o['problems'][1]['title']}\n\n{SECTIONS}\n"
    bad = f"## 1. {o['problems'][0]['title']}\n\n덤프가 같이 사라져요. [k3s](https://docs.k3s.io/cli/etcd-snapshot)와 [블로그](https://example.com/from-memory)를 보세요.\n\n### 무슨 일인가\n\n글.\n"
    _write(snap, o, problems=[bad, good])
    issues = report.problems_with(snap, "ko")
    assert any("https://example.com/from-memory is not in a learn topic" in e for e in issues) and not any("docs.k3s.io" in e for e in issues)
    assert any("해요체 (사라져요)" in e for e in issues) and not any("보세요" in e for e in issues)  # a request keeps its ending
    assert any("needs these `### ` sections in this order" in e for e in issues)
    (snap / "report" / "problem-3.md").write_text("## 3. 남은 파일\n")
    assert any("problem-3.md has no problem in the outline" in e for e in report.problems_with(snap, "ko"))
    (snap / "report" / "problem-2.md").unlink()
    assert any("problem-2.md does not exist" in e for e in report.problems_with(snap, "ko"))


def test_the_report_is_assembled_with_one_source_for_every_title(tmp_path):
    snap = _snap(tmp_path)
    o = _outline(upcoming=[{"when": "2026-11-20", "what": "인증서를 갱신합니다.", "source": "summary.json"}], limits=[{"kind": "no-data", "what": "인그레스 요청 메트릭이 없습니다.", "weakens": "사용자가 받은 오류 수를 모릅니다"}])
    _write(snap, o)
    assert report.problems_with(snap, "ko") == []
    text = report.assemble(snap, "ko", "0.1.91", "0.2.0")
    assert text.startswith("# c — full 점검, 2026-11-14 12:00\n\n지금 깨져 있는 것: 없음\n\n가장 큰 문제 2개: ① 백업이 클러스터 밖에 없음 ② 레플리카가 한 노드에 있음\n\n이미 일어난 일: 알림 2건이 전달되지 않음\n\n운영 규모: 소형")
    at = [
        text.index(h)
        for h in (
            "## 클러스터 한눈에",
            "## 이미 일어난 일",
            "## 1. 백업이 클러스터 밖에 없음",
            "## 2. 레플리카가 한 노드에 있음",
            "## 그다음으로 큰 문제",
            "## 지난 리포트 이후",
            "## 다가오는 일",
            "## 영역별 한 줄",
            "## 이번 점검의 한계",
            "## 숫자",
        )
    ]
    assert at == sorted(at) and "## 지금 깨져 있는 것" not in text and "## 고치지 않기로 정해 둔 항목" not in text
    assert "## 이미 일어난 일\n\n비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.\n\n### 알림 2건이 전달되지 않음" in text
    assert "| 2026-11-20 | 인증서를 갱신합니다. | summary.json |" in text and "| 비용 | 이번 점검에서 문제를 찾지 못했습니다. |" in text
    assert "- 인그레스 요청 메트릭이 없습니다.\n  - 약해지는 결론: 사용자가 받은 오류 수를 모릅니다." in text
    assert "- 백업이 클러스터 밖에 없음: `resilience.no-backup.cluster`" in text and "- 알림 2건이 전달되지 않음: `observability.alertmanager-notification-failed.slack`, `traffic.pod-not-ready.*`" in text

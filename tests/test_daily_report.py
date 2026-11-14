"""The daily report (lib/output/daily.py): three things that matter now, told briefly, checked by code and printed without a separate writer."""

from __future__ import annotations

import json
from pathlib import Path

from lib.output import daily, writer

URL = "https://example.com/backup"
FINDINGS = [
    {"id": "resilience.no-backup.cluster", "check": "resilience.no-backup", "target": "cluster", "status": "fail", "severity_default": "high", "nature": "state"},
    {"id": "platform.k8s-version-eol.cluster", "check": "platform.k8s-version-eol", "target": "cluster", "status": "fail", "severity_default": "high", "nature": "state", "overdue": True},
    {"id": "resources.oomkilled.prod/web", "check": "resources.oomkilled", "target": "prod/web", "status": "fail", "severity_default": "high", "nature": "occurrence"},
    {"id": "hygiene.latest-tag.prod/web", "check": "hygiene.latest-tag", "target": "prod/web", "status": "warn", "severity_default": "low", "nature": "state"},
]


def _snap(root: Path, name="2026-11-14T09-00-00", findings=FINDINGS, mode="daily") -> Path:
    s = root / "c" / name
    (s / "llm").mkdir(parents=True)
    (s / "MODE").write_text(mode + "\n")
    fd = {
        "findings": findings,
        "scale": {"name": "small"},
        "checks": {"total": 349, "by_status": {"done": 250, "not-collected": 90}},
        "learn": [{"topic": "backup-off-cluster", "checks": ["resilience.no-backup"], "reading": [{"title": "k3s", "url": URL}]}],
    }
    (s / "findings-draft.json").write_text(json.dumps(fd))
    (s / "summary.json").write_text(json.dumps({"backup": {"cronjobs": 7}}))
    (s / "inventory.json").write_text(json.dumps({"taken_at": name[:10] + "T09:00:00+09:00", "cluster": {"cluster_name": "lab", "platform": "k3s", "server_version": "v1.33.5+k3s1"}, "nodes": {"count": 2, "ready": 2}}))
    return s


def _facts(**over) -> dict:
    f = {
        "schema": 2,
        "broken_now": [],
        "happened": {"incidents": [{"id": "A", "title": "web이 OOM으로 재시작함", "what": "prod/web 컨테이너가 메모리 한도에 닿아 두 번 재시작했습니다.", "state": "ended", "finding_ids": ["resources.oomkilled.prod/web"]}]},
        "top": [
            {
                "id": "1",
                "title": "백업이 클러스터 밖에 없음",
                "loss": "irreversible",
                "what": "백업 CronJob 7개가 모두 같은 클러스터의 볼륨에 덤프를 씁니다.",
                "why": "두 노드를 함께 잃으면 원본과 사본이 같이 사라집니다.",
                "do": "덤프를 클러스터 밖 오브젝트 스토리지로 한 벌 더 보내는 CronJob을 두는 편이 좋습니다.",
                "read": {"title": "k3s 문서", "url": URL},
                "finding_ids": ["resilience.no-backup.cluster"],
                "facts": [{"what": "백업 CronJob", "value": 7, "source_file": "summary.json", "json_path": "backup.cronjobs"}],
            },
            {
                "id": "2",
                "title": "Kubernetes 지원이 끝남",
                "loss": "partial",
                "what": "1.33의 지원이 끝났습니다.",
                "why": "보안 패치가 나오지 않습니다.",
                "do": "마이너 버전을 하나씩 올립니다.",
                "read": None,
                "finding_ids": ["platform.k8s-version-eol.cluster"],
            },
        ],
        "rest": [],
        "since_last": {"appeared": ["web의 OOM 재시작 2번"], "gone": []},
    }
    f.update(over)
    return f


def test_good_daily_facts_break_no_rule(tmp_path):
    assert daily.check(_facts(), _snap(tmp_path)) == []


def test_the_daily_facts_are_refused_for_what_a_reader_should_not_get(tmp_path):
    snap = _snap(tmp_path)

    def errors(**over):
        return daily.check(_facts(**over), snap)

    top = _facts()["top"]
    assert any("not `problems` and `next`" in e for e in errors(problems=[{"id": "1"}]))
    assert any("4 entries in top" in e for e in errors(top=top + top))
    assert any("in no list" in e for e in errors(top=top[:1]))  # the end-of-support failure is high and placed nowhere
    assert any("address from `learn`" in e for e in errors(top=[{**top[0], "read": {"title": "t", "url": "https://example.com/from-memory"}}, top[1]]))
    assert any("facts say 9" in e for e in errors(top=[{**top[0], "facts": [{"what": "백업 CronJob", "value": 9, "source_file": "summary.json", "json_path": "backup.cronjobs"}]}, top[1]]))
    assert any("source file objects/cronjobs.json does not exist" in e for e in errors(top=[{**top[0], "facts": [{"what": "x", "value": 7, "source_file": "objects/cronjobs.json", "json_path": "items"}]}, top[1]]))  # the raw files are gone
    assert any("해요체" in e for e in errors(top=[{**top[0], "why": "두 노드를 잃으면 같이 사라져요."}, top[1]]))
    assert any("5 sentences" in e for e in errors(top=[{**top[0], "what": "하나입니다. 둘입니다. 셋입니다. 넷입니다. 다섯입니다."}, top[1]]))
    assert any("no code block" in e for e in errors(top=[{**top[0], "do": "아래처럼 합니다.\n```yaml\na: 1\n```"}, top[1]]))
    assert any("not in order" in e for e in errors(top=[{**top[1], "loss": "degraded"}, {**top[0], "loss": "outage"}]))


def test_a_version_past_its_end_of_support_is_weighed_one_step_higher_in_the_daily_order_too(tmp_path):
    snap = _snap(tmp_path)
    top = _facts()["top"]
    assert daily.check(_facts(top=[{**top[1], "loss": "partial"}, {**top[0], "loss": "outage"}]), snap) == []  # partial, one step up, ties with outage


def test_the_report_is_printed_from_the_facts_with_what_code_knows(tmp_path):
    for day in ("12", "13"):  # two earlier daily runs that already had the backup finding
        _snap(tmp_path, f"2026-11-{day}T09-00-00", [FINDINGS[0]])
    snap = _snap(tmp_path)
    text = daily.assemble(snap, _facts(), "ko", "0.1.91", "0.2.0")
    assert text.startswith("# lab — daily 점검, 2026-11-14 09:00\n\n지금 깨져 있는 것 0개 · 지난 점검 이후 일어난 일 1건 · 지금 가장 중요한 것 2개")
    assert "지금 가장 중요한 것: ① 백업이 클러스터 밖에 없음 ② Kubernetes 지원이 끝남" in text and "운영 규모: 소형" in text
    at = [text.index(h) for h in ("## 클러스터 한눈에", "## 지난 점검 이후 일어난 일", "## 지금 가장 중요한 것", "## 지난 점검 이후 달라진 것", "## 이번 점검이 보지 않은 것")]
    first = daily.assemble(_snap(tmp_path / "first"), _facts(), "ko", "0.1.91", "0.2.0")  # the first run of a cluster: nothing to compare with
    assert "첫 daily 점검이라" in first and "처음 나왔습니다" not in first and "## 지난 점검 이후 달라진 것" not in first
    assert at == sorted(at) and "## 지금 깨져 있는 것" not in text and "## 그 밖에 열려 있는 것" not in text
    assert "### 1. 백업이 클러스터 밖에 없음\n\n2026-11-12 점검부터 그대로입니다. 이번이 3번째입니다." in text
    assert "### 2. Kubernetes 지원이 끝남\n\n이번 점검에서 처음 나왔습니다." in text
    assert "**무슨 일인가.** 백업 CronJob 7개가" in text and "**왜 중요한가.** 두 노드를" in text and "**무엇을 하면 되나.** 덤프를" in text
    assert f"더 읽기: [k3s 문서]({URL})" in text
    assert "두 번 재시작했습니다. 지금은 끝난 일입니다." in text
    assert "점검 항목 349개 가운데 90개는 이번에 보지 못했습니다" in text and "AWS API를 부르지 않았습니다" not in text  # not EKS
    assert "`/kubegap full`" in text and "- 백업이 클러스터 밖에 없음: `resilience.no-backup.cluster`" in text


def test_write_report_starts_no_agent_for_a_daily_snapshot(tmp_path):
    snap = _snap(tmp_path)
    (snap / "llm" / "facts.json").write_text(json.dumps(_facts()))

    def run(*a, **k):
        raise AssertionError("a daily report starts no agent")

    said = []
    p = writer.write_report(snap, "ko", "none", "0.1.91", "0.2.0", say=said.append, run=run)
    assert p.read_text().startswith("# lab — daily 점검") and any("no separate writer" in s for s in said)
    (snap / "llm" / "facts.json").write_text(json.dumps(_facts(top=[])))
    try:
        writer.write_report(snap, "ko", "none", "0.1.91", "0.2.0", say=said.append, run=run)
    except writer.WriterError as e:
        assert "daily contract" in str(e)
    else:
        raise AssertionError("facts that leave a high failure out are refused")

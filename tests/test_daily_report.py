"""The daily report (lib/output/daily.py): three things that matter now, told briefly, checked by code and printed without a separate writer."""

from __future__ import annotations

import json
from pathlib import Path

from lib.output import daily

URL = "https://example.com/backup"
FINDINGS = [
    {"id": "resilience.no-backup.cluster", "check": "resilience.no-backup", "target": "cluster", "status": "fail", "severity_default": "high", "nature": "state"},
    {"id": "platform.k8s-version-eol.cluster", "check": "platform.k8s-version-eol", "target": "cluster", "status": "fail", "severity_default": "high", "nature": "state", "overdue": True},
    {"id": "resources.oomkilled.prod/web", "check": "resources.oomkilled", "target": "prod/web", "status": "fail", "severity_default": "high", "nature": "occurrence"},
    {"id": "hygiene.latest-tag.prod/web", "check": "hygiene.latest-tag", "target": "prod/web", "status": "warn", "severity_default": "low", "nature": "state"},
]


def _snap(root: Path, name="2026-11-14T09-00-00", findings=FINDINGS, mode="daily") -> Path:
    s = root / "c" / name
    (s / "report").mkdir(parents=True)
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
        "broken_now": [],
        "happened": {"incidents": [{"id": "A", "title": "web이 OOM으로 재시작함", "what": "prod/web 컨테이너가 메모리 한도에 닿아 두 번 재시작했습니다.", "state": "ended", "finding_ids": ["resources.oomkilled.prod/web"]}]},
        "top": [
            {
                "id": "1",
                "title": "백업이 클러스터 밖에 없음",
                "loss": "irreversible",
                "what": "백업 CronJob 7개가 모두 같은 클러스터의 볼륨에 덤프를 씁니다.",
                "why": "두 노드를 함께 잃으면 원본과 사본이 같이 사라집니다.",
                "do": "덤프를 클러스터 밖 오브젝트 스토리지로 한 번 더 보내는 CronJob을 두는 편이 좋습니다.",
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
    assert "### 1. 백업이 클러스터 밖에 없음\n\n2026-11-12 09:00 점검부터 그대로입니다. 이번이 3번째 점검입니다." in text
    assert "### 2. Kubernetes 지원이 끝남\n\n이번 점검에서 처음 나왔습니다." in text
    assert "**무슨 일인가.** 백업 CronJob 7개가" in text and "**왜 중요한가.** 두 노드를" in text and "**무엇을 하면 되나.** 덤프를" in text
    assert f"더 읽기: [k3s 문서]({URL})" in text
    assert "두 번 재시작했습니다. 지금은 끝난 일입니다." in text
    assert "점검 항목 349개 가운데 90개는 이번에 보지 못했습니다" in text and "AWS API를 부르지 않았습니다" not in text  # not EKS
    assert "`/kubegap full`" in text and "- 백업이 클러스터 밖에 없음: `resilience.no-backup.cluster`" in text


def test_every_serious_check_a_daily_run_cannot_judge_is_named_for_the_reader():
    """A reader must not take the absence of these for a pass, so the report lists them; a new full-only critical or high check needs its phrase."""
    for platform in ("k3s", "eks", "other"):
        missing = [c["id"] for c in daily.serious_full_only(platform, None) if c["id"] not in daily.UNSEEN["ko"]]
        assert missing == [], f"{platform}: add a phrase to daily.UNSEEN for {missing}"


def test_the_daily_report_says_what_each_unit_it_left_out_would_have_shown(tmp_path):
    """One line per collection unit the daily run leaves out, in the unit's own words (collectors/units.yaml), and none for a unit the platform
    does not have: a k3s cluster has no AWS account."""
    from lib.foundations import units

    snap = _snap(tmp_path)
    (snap / "MODE").write_text("daily\n")
    section = daily.assemble(snap, _facts(), "ko", "0.1.93", "0.2.0").split("## 이번 점검이 보지 않은 것")[1].split("\n## ")[0]
    left = units.left_out("daily", "k3s")
    assert len(left) == 7 and all(f"- {u['unseen']['ko']}" in section for u in left)
    assert "AWS API" not in section and "- 노드에 접속하지 않았습니다." in section and "- Secret 값은 어느 점검에서도 읽지 않습니다." in section


def test_the_daily_report_lists_what_it_cannot_find_for_this_cluster(tmp_path):
    snap = _snap(tmp_path)
    inv = json.loads((snap / "inventory.json").read_text())
    inv["collectors_enabled"] = ["core", "k3s-platform", "local-path-provisioner"]
    (snap / "inventory.json").write_text(json.dumps(inv))
    text = daily.assemble(snap, _facts(), "ko", "0.1.91", "0.2.0")
    assert "- 노드 디스크가 차는 것" in text and "- k3s 내부 인증서의 만료" in text and "ACM 인증서" not in text  # k3s, not EKS
    assert "이 리포트에 없다고 해서 문제가 없다는 뜻이 아닙니다." in text
    assert "daily 점검이 볼 수 없는 심각한 문제가" in text.split("## 클러스터 한눈에")[0]  # said on the first screen too


def test_a_number_nobody_can_check_is_not_accepted(tmp_path):
    snap = _snap(tmp_path)
    top = _facts()["top"]
    made_up = {**top[0], "facts": [{"what": "x", "value": 7, "derived": True, "source_file": "summary.json", "json_path": "backup.cronjobs"}]}
    assert any("`derived` is not accepted in a daily report" in e for e in daily.check(_facts(top=[made_up, top[1]]), snap))


def test_an_english_daily_report_is_assembled(tmp_path):
    snap = _snap(tmp_path)
    (snap / "MODE").write_text("daily\n")
    text = daily.assemble(snap, _facts(), "en", "0.1.93", "0.2.0")
    assert "— daily audit," in text and "## What matters most now" in text and "**What to do.**" in text
    section = text.split("## What this audit did not look at")[1]
    assert "- It contacted no node." in section and "- Secret values are not read by any audit." in section and "run `/kubegap full`" in section
    # the serious things it cannot see are named by the checks' own English names
    assert any(f"- {c['name']}" in section for c in daily.serious_full_only("k3s", None))

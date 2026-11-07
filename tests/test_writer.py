"""The report pipeline (`kubegap write-report`): which agent gets what, how the step check goes into the facts, and what code refuses. No agent runs here."""

from __future__ import annotations

import json

import pytest

from lib.foundations import paths, shell
from lib.output import writer


def _facts(**over):
    f = {
        "cluster": {"name": "lab", "taken_at": "2026-11-05T17:01:01+09:00"},
        "counts": {"critical": {"fail": 3, "warn": 1, "delta": {"fail": 1, "warn": -2}}},
        "problems": [
            {
                "id": "1",
                "title": "restarts",
                "targets": ["ns/app"],
                "situation": {"numbers": [{"what": "restarts", "value": 7, "source_file": "summary.json", "json_path": "a.b[0].c"}], "impact": {"affected": [{"who": "ns/app", "evidence": "BackOff"}], "not_checked": []}},
                "steps": [{"kind": "check", "do": "look", "command": "kubectl get pods", "check": "ok"}, {"kind": "change", "do": "raise the limit", "command": "limits: 1Gi", "check": "0 restarts"}],
                "finding_ids": ["a.b", "c.d"],
            }
        ],
    }
    return {**f, **over}


def _snap(tmp_path, facts=None):
    s = tmp_path / "2026-11-05T17-01-01"
    (s / "llm").mkdir(parents=True)
    (s / "MODE").write_text("daily")
    (s / "summary.json").write_text(json.dumps({"a": {"b": [{"c": 7}]}}))
    (s / "inventory.json").write_text(
        json.dumps(
            {
                "cluster": {"server_version": "v1.33.5+k3s1", "platform": "k3s"},
                "nodes": {"count": 2, "ready": 2},
                "pods": {"by_phase": {"Running": 96, "Failed": 4}},
                "namespaces": {"count": 26, "prod_like": ["a", "b"]},
                "components_present": ["coredns", "argocd"],
                "stores": {"prometheus": {"kind": "prometheus", "version": "2.5"}},
            }
        )
    )
    (s / "llm" / "facts.json").write_text(json.dumps(facts or _facts()))
    return s


OK = json.dumps({"actions": [{"problem": "1", "step": 0, "verdict": "ok"}, {"problem": "1", "step": 1, "verdict": "ok"}], "missing": [], "impact": []})


class Runner:
    """Stands in for shell.run and records each agent: the prompt file, its tools, its input."""

    def __init__(self, replies=None):
        self.calls, self.replies = [], {"check-actions-ko.md": OK, "check-actions-en.md": OK, **(replies or {})}

    def __call__(self, cmd, stdin=None, cwd=None, timeout=None):
        guide = cmd[cmd.index("--system-prompt-file") + 1].rsplit("/", 1)[1]
        self.calls.append({"guide": guide, "tools": cmd[cmd.index("--tools") + 1], "stdin": stdin})
        return shell.Result(cmd=cmd, code=0, stdout=self.replies.get(guide, f"text from {guide}"))


def test_four_agents_in_order_and_each_gets_only_its_input(tmp_path):
    s, r = _snap(tmp_path), Runner()
    report = writer.write_report(s, "ko", "claude", "0.1.80", "0.1.2", say=lambda m: None, run=r)
    assert [c["guide"] for c in r.calls] == ["check-actions-ko.md", "writing-ko.md", "check-facts-ko.md", "replace-ko.md"]
    assert r.calls[0]["tools"] == "Read,Grep,Glob" and r.calls[2]["tools"] == "Read,Grep,Glob"
    assert r.calls[1]["tools"] == "" and r.calls[3]["tools"] == ""
    steps_in = json.loads(r.calls[0]["stdin"])
    assert list(steps_in["problems"][0]) == ["id", "title", "targets", "steps", "impact"]  # the step checker never sees the analysis text
    assert "situation" not in r.calls[0]["stdin"] and "cause" not in r.calls[0]["stdin"]
    assert json.loads(r.calls[1]["stdin"])["problems"][0]["steps"][0]["verdict"] == "ok"  # the writer gets the merged facts
    assert r.calls[2]["stdin"].startswith("<notes>\nnone\n</notes>\n\n<report>\ntext from writing-ko.md")
    assert "<wrong>\ntext from check-facts-ko.md" in r.calls[3]["stdin"] and "<facts>" in r.calls[3]["stdin"]
    text = report.read_text()
    assert text.startswith("# lab — daily 점검, 2026-11-05 17:01\n\ntext from replace-ko.md")
    assert "| critical | 3 | 1 | fail +1, warn -2 |" in text and "## 숫자" in text and "rubric 0.1.80" in text
    assert "문제별 체크:\n\n- 문제 1: `a.b`, `c.d`\n\n자세한" in text
    assert (s / "llm" / "writing" / "actions.json").is_file() and (s / "llm" / "facts-analysis.json").is_file()
    assert json.loads((s / "llm" / "facts.json").read_text())["problems"][0]["steps"][1]["verdict"] == "ok"


def test_a_clean_fact_check_skips_the_replacer(tmp_path):
    r = Runner({"check-facts-ko.md": "none", "writing-ko.md": "draft"})
    report = writer.write_report(_snap(tmp_path), "ko", "claude", "r", "v", say=lambda m: None, run=r)
    assert [c["guide"] for c in r.calls] == ["check-actions-ko.md", "writing-ko.md", "check-facts-ko.md"]
    assert "\n\ndraft\n\n" in report.read_text()


def test_harm_removes_the_step_hold_adds_the_condition_fix_sets_the_fields_and_missing_risks_land_on_the_problem():
    facts = _facts()
    result = {
        "actions": [
            {"problem": "1", "step": 1, "verdict": "harm", "reason": "init container pushes the schema with --accept-data-loss", "files": ["objects/deployments.json"]},
            {"problem": "1", "step": 0, "verdict": "hold", "reason": "dump the database first"},
        ],
        "missing": [{"problem": "1", "what": "hm-qdrant is pinned to the same node", "files": ["objects/statefulsets.json"]}],
        "impact": [{"problem": "1", "affected": [], "not_checked": ["ns/app"]}],
    }
    out, notes = writer.apply_action_check(facts, result)
    assert [s["do"] for s in out["problems"][0]["steps"]] == ["look"]
    assert out["problems"][0]["steps"][0]["verdict"] == "hold" and out["problems"][0]["steps"][0]["when"] == "dump the database first"
    assert out["problems"][0]["missing_risks"] == ["hm-qdrant is pinned to the same node (objects/statefulsets.json)"]
    assert out["problems"][0]["situation"]["impact"] == {"affected": [], "not_checked": ["ns/app"]}
    assert facts["problems"][0]["steps"][1]["do"] == "raise the limit"  # the input is not changed
    assert any("removed as harm" in n for n in notes) and any("missing risk" in n for n in notes)
    fixed, _ = writer.apply_action_check(_facts(), {"actions": [{"problem": "1", "step": 1, "verdict": "fix", "set": {"risk": "the pod stops while it rolls", "rollback": "set 512Mi again", "verdict": "ignored"}}]})
    step = fixed["problems"][0]["steps"][1]
    assert step["risk"] == "the pod stops while it rolls" and step["rollback"] == "set 512Mi again" and step["verdict"] == "fix"
    _, notes = writer.apply_action_check(_facts(), {"actions": [{"problem": "9", "step": 0, "verdict": "ok"}, {"problem": "1", "step": 5, "verdict": "ok"}]})
    assert len(notes) == 2 and all("does not exist" in n for n in notes)


def test_the_step_check_answer_is_read_with_or_without_a_fence():
    assert writer.parse_json('```json\n{"actions": []}\n```')["actions"] == []
    assert writer.parse_json('Here it is:\n{"actions": [], "missing": []}\n')["missing"] == []
    with pytest.raises(writer.WriterError, match="JSON"):
        writer.parse_json("none")
    with pytest.raises(writer.WriterError, match="broken JSON"):
        writer.parse_json("{'actions': }")


BEFORE = "## 1. 문제\n\n① 보세요.\n\n```\nkubectl get pods\n```\n\n② 지우세요.\n"


def test_a_replacement_may_change_sentences_but_not_commands_steps_or_problems():
    assert writer.gate(BEFORE, BEFORE.replace("보세요", "확인하세요")) == []
    assert any("command block" in p for p in writer.gate(BEFORE, BEFORE.replace("get pods", "get pod")))
    assert any("steps" in p for p in writer.gate(BEFORE, BEFORE.replace("② 지우세요.\n", "")))
    assert any("problems" in p for p in writer.gate(BEFORE, BEFORE + "\n## 2. 또\n"))


def test_a_broken_replacement_is_dropped_and_the_run_says_so(tmp_path):
    said = []
    r = Runner({"writing-ko.md": BEFORE, "check-facts-ko.md": "- Quote: x", "replace-ko.md": "## 1. 문제\n\n① 보세요.\n"})
    report = writer.write_report(_snap(tmp_path), "ko", "claude", "r", "v", say=said.append, run=r)
    assert "kubectl get pods" in report.read_text() and any("replacement was dropped" in m for m in said)


def test_the_change_column_takes_numbers_only():
    assert writer._delta({"delta": {"fail": 0, "warn": 3}}) == "fail 0, warn +3"
    assert writer._delta({"delta": "automatic: fail 0, warn +1"}) == ""


def test_a_failed_agent_stops_with_the_reason(tmp_path):
    def run(cmd, **kw):
        return shell.Result(cmd=cmd, code=1, stderr="Operation not permitted")

    with pytest.raises(writer.WriterError, match="Operation not permitted"):
        writer.write_report(_snap(tmp_path), "ko", "claude", "r", "v", say=lambda m: None, run=run)


def test_missing_facts_says_what_to_do(tmp_path):
    s = _snap(tmp_path)
    (s / "llm" / "facts.json").unlink()
    with pytest.raises(writer.WriterError, match=r"references/facts-en\.md"):
        writer.write_report(s, "en", "claude", "r", "v", say=lambda m: None, run=Runner())


def test_numbers_are_checked_against_the_snapshot(tmp_path):
    def with_numbers(numbers):
        return _facts(problems=[{"id": "1", "situation": {"numbers": numbers}}])

    good = _facts()
    s = _snap(tmp_path, good)
    assert writer.verify_numbers(s, good) == []
    assert "facts say 9" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "summary.json", "json_path": "a.b[0].c"}]))[0]
    assert "a.z is not in summary.json" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "summary.json", "json_path": "a.z"}]))[0]
    assert "does not exist" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "no.json", "json_path": "a"}]))[0]
    assert writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "derived": True}])) == []


def test_agents_get_no_user_settings_and_codex_stays_read_only(tmp_path):
    cmd, prefix = writer.agent_command("claude", writer.REFERENCES / "writing-ko.md", read_files=False)
    assert cmd[cmd.index("--setting-sources") + 1] == "" and cmd[cmd.index("--tools") + 1] == "" and prefix == ""
    cmd, prefix = writer.agent_command("codex", writer.REFERENCES / "writing-en.md", read_files=True)
    assert cmd[:4] == ["codex", "exec", "--sandbox", "read-only"] and prefix.startswith("You are a senior engineer")


def test_the_prompts_exist_per_language_and_share_nothing():
    for name in ("check-actions", "writing", "check-facts", "replace"):
        ko, en = (writer.REFERENCES / f"{name}-ko.md").read_text(), (writer.REFERENCES / f"{name}-en.md").read_text()
        assert ko and en and ko != en
        assert not any(w in ko for w in ("You are", "Do not")), name  # the Korean file is written in Korean, not carried over
    for f in ("review-facts.md", "review-actions.md", "review-reading-ko.md", "review-reading-en.md", "edit-ko.md", "edit-en.md", "report-grouping.md"):
        assert not (paths.ROOT / "references" / f).exists(), f
    ko, en = (writer.REFERENCES / "writing-ko.md").read_text(), (writer.REFERENCES / "writing-en.md").read_text()
    assert "번역하지 마세요" in ko and "<example>" in ko and "<example>" in en
    for text in (ko, en):
        for tool_word in ("kubegap", "render-details", "findings-draft"):
            assert tool_word not in text
    assert "## 1. " in ko and "**상황.**" in ko and "**되돌리기.**" in ko
    assert "**What is happening.**" in en and "**Rollback.**" in en


def test_blocks_get_blank_lines_but_lists_tables_and_code_stay_together():
    body = "Urgent now: no\nToday: ① a\n\n## 1. t\n\n**What.** x\n- a: 1\n- b: 2\n**Why.** y\n① do\n```\nkubectl get pods\nkubectl get nodes\n```\nCheck: ok\n**Evidence.**\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    out = writer.space_blocks(body)
    assert "Urgent now: no\n\nToday: ① a\n\n## 1. t" in out
    assert "**What.** x\n\n- a: 1\n- b: 2\n\n**Why.** y\n\n① do\n\n```\nkubectl get pods\nkubectl get nodes\n```\n\nCheck: ok\n\n**Evidence.**\n\n| a | b |\n|---|---|\n| 1 | 2 |" in out
    assert writer.space_blocks(out) == out  # idempotent


def test_code_writes_the_glance_coming_up_since_last_and_area_sections(tmp_path):
    facts = _facts(
        upcoming=[{"when": "2026-11-07", "what": "node-1 expires", "source_file": "summary.json", "json_path": "a.b[0].c"}],
        since_last={
            "compared_with": "2026-11-04 daily",
            "done": [{"problem": "pin the image", "proof": "digest set"}],
            "not_done": [{"problem": "add a PDB", "proof": "0 PDBs"}],
            "appeared": ["N+1 fails"],
            "gone": [],
            "criteria_changed": ["the node-loss check counts pinned pods"],
        },
        analysis={"area_summary": {"resources": "fine", "security": "one plaintext token"}},
    )
    s = _snap(tmp_path, facts)
    body = "지금 급한 일: 없음\n\n## 1. t\n\n**상황.** x\n\n## 오늘은 안 하지만 심각한 것\n\n- a\n\n## 이번에 못 본 것\n\n- b\n"
    out = writer.insert_sections(body, s, facts, "ko", "daily")
    assert out.index("## 클러스터 한눈에") < out.index("## 다가오는 일") < out.index("## 1. t") < out.index("## 지난 daily 점검 이후") < out.index("## 오늘은 안 하지만 심각한 것")
    assert "| 노드 | 2대 중 Ready 2대 |" in out and "| 파드 | 실행 96, 대기 0, 실패 4 |" in out and "| 네임스페이스 | 26개, 프로덕션 2개 |" in out and "| 메트릭·로그 저장소 | prometheus 2.5 / 없음 |" in out
    assert "| 2026-11-07 | node-1 expires | summary.json |" in out
    assert "| pin the image | 했음 | digest set |" in out and "| add a PDB | 안 했음 | 0 PDBs |" in out and "**새로 생긴 것.**\n- N+1 fails" in out and "**사라진 것.**\n- 없음" in out
    assert "## 영역별 한 줄" not in out
    full = writer.insert_sections(body, s, facts, "ko", "full")
    assert full.index("## 영역별 한 줄") < full.index("## 이번에 못 본 것") and "| security | one plaintext token |" in full and "| scaling | 없음 |" in full
    nothing = writer.insert_sections("Urgent now: no\n\n## 1. t\n", s, _facts(), "en", "daily")
    assert "## Coming up\n\nnone" in nothing and "No earlier daily run to compare with." in nothing
    assert "upcoming: node-1 expires: facts say 2026-11-07" in writer.verify_numbers(s, facts)[0]  # a date has a source like a number


def test_code_prints_the_findings_the_checks_changed_from_diff_json(tmp_path):
    facts = _facts(since_last={"compared_with": "yesterday", "appeared": ["N+1 fails"]})
    s = _snap(tmp_path, facts)
    (s / "diff.json").write_text(
        json.dumps(
            {
                "findings": {
                    "criteria_changes": {
                        "new_checks": [{"id": "traffic.ingress-nginx-retired.cluster", "status": "warn", "severity_default": "medium"}],
                        "rule_changed": [{"id": "resilience.n-plus-one.cluster", "status": "fail", "severity_default": "critical"}],
                        "dropped_checks": [],
                        "rule_unknown_checks": ["x.y"],
                        "note": "text",
                    }
                }
            }
        )
    )
    out = writer.since_last(facts, writer.HEADINGS["ko"], "daily", s)
    assert "**두 점검 사이에 판정 규칙이 바뀐 항목.**\n- `resilience.n-plus-one.cluster` (fail/critical)" in out
    assert "클러스터가 아니라 점검에 새로 보인 것.**\n- `traffic.ingress-nginx-retired.cluster` (warn/medium)" in out
    assert "이번에 돌지 않은 점검 항목" not in out  # an empty bucket prints nothing
    assert writer.criteria_changes(tmp_path, writer.HEADINGS["en"]) == []  # no diff.json, no lines

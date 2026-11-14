"""The report pipeline (`kubegap write-report`): which agent gets what, how the solution check goes into the facts, what code writes itself and what it refuses. No agent runs here."""

from __future__ import annotations

import json

import pytest

from lib.foundations import paths, shell
from lib.output import glossary, writer

FINDINGS = [
    {"id": "resilience.no-backup.cluster", "check": "resilience.no-backup", "target": "cluster", "status": "fail", "severity_default": "critical", "nature": "state"},
    {"id": "resilience.replicas-same-node.prod/deployment/api", "check": "resilience.replicas-same-node", "target": "prod/deployment/api", "status": "fail", "severity_default": "high", "nature": "state"},
    {"id": "traffic.pod-not-ready.prod/web", "check": "traffic.pod-not-ready", "target": "prod/web", "status": "fail", "severity_default": "medium", "nature": "occurrence"},
]
URL = "https://example.com/postmortem"


def _problem(pid, ids, loss, **over):
    p = {
        "id": pid,
        "title": f"title {pid}",
        "finding_ids": ids,
        "targets": ["prod/deployment/api"],
        "picked": {"loss": loss, "reason": "r"},
        "facts": [{"what": "restarts", "value": 7, "source_file": "summary.json", "json_path": "a.b[0].c"}],
        "cause": {"statement": "s", "certainty": "confirmed", "evidence": []},
        "scope": {"affected": [{"who": "prod/deployment/api", "evidence": "both pods on n1"}]},
        "check_methods": [{"kind": "metric", "what": "m"}],
        "solutions": [{"approach": "spread", "for_scale": "small"}, {"approach": "descheduler", "for_scale": "large"}],
        "learn": {"cases": [{"company": "X", "url": URL}], "reading": []},
    }
    p.update(over)
    return p


def _facts(**over):
    f = {
        "schema": 2,
        "broken_now": [],
        "happened": {"incidents": [{"id": "A", "title": "nodes rebooted", "state": "ended", "finding_ids": ["traffic.pod-not-ready.*"], "exposed": ["2"]}]},
        "problems": [_problem("1", ["resilience.no-backup.cluster"], "irreversible"), _problem("2", ["resilience.replicas-same-node.*"], "outage")],
        "next": [],
        "since_last": {},
        "upcoming": [],
        "limits": [],
        "analysis": {},
    }
    return {**f, **over}


def _snap(tmp_path, facts=None, mode="full"):
    s = tmp_path / "c" / "2026-11-14T12-00-00"
    (s / "llm").mkdir(parents=True)
    (s / "MODE").write_text(mode)
    (s / "summary.json").write_text(
        json.dumps(
            {
                "a": {"b": [{"c": 7}]},
                "hygiene": {"templating": {"owners": [{"workload": "prod/deployment/api", "managed_by": "argocd", "argocd_app": "shop"}]}},
                "argocdctl": {"applications": {"rows": [{"name": "shop", "repo_url": "https://example.com/org/manifests", "path": "prod/shop", "self_heal": True}]}},
            }
        )
    )
    (s / "findings-draft.json").write_text(json.dumps({"findings": FINDINGS, "suppressed": [], "scale": {"name": "small", "source": "answered"}}))
    (s / "inventory.json").write_text(
        json.dumps(
            {
                "context": "c",
                "taken_at": "2026-11-14T12:00:00+09:00",
                "cluster": {"cluster_name": "lab", "server_version": "v1.33.5+k3s1", "platform": "k3s"},
                "nodes": {"count": 2, "ready": 2},
                "pods": {"by_phase": {"Running": 96, "Failed": 4}},
                "namespaces": {"count": 26, "prod_like": ["a", "b"]},
                "components_present": ["coredns", "argocd", "istio"],
                "stores": {"prometheus": {"kind": "prometheus", "version": "2.5"}},
            }
        )
    )
    (s / "llm" / "facts.json").write_text(json.dumps(facts or _facts()))
    return s


SECTIONS = "### 무슨 일인가\n\nx\n\n### 왜 생기나\n\ny\n\n### 추천 점검 방법\n\nz\n\n### 추천 해결 방안\n\n```yaml\nmaxUnavailable: 1\n```\n\n### 근거\n\n| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |\n\n### 더 읽을 것\n\n- r\n"
OVERVIEW = "## 이미 일어난 일\n\n### nodes rebooted\n\n끝난 일이에요.\n\n## 그다음으로 큰 문제\n\n다섯 개 밖에 남은 critical·high 문제가 없어요.\n\n## 지난 리포트 이후\n\n| 지난 리포트의 권고 | 상태 | 근거 |\n|---|---|---|\n| move the dumps | 반영됨 | 7 CronJobs on n1 |\n\n**새로 생긴 것**\n\n- two nodes rebooted\n\n**없어진 것**\n\n- 없음\n"
NOTHING = json.dumps({"cautions": [], "drop": [], "scope": []})


class Runner:
    """Stands in for shell.run and records each agent: the prompt file, its tools, its input. The problem writer answers with a text for the number it was given."""

    def __init__(self, replies=None):
        self.calls, self.replies = [], {"check-solutions-ko.md": NOTHING, "write-overview-ko.md": OVERVIEW, "check-facts-ko.md": "none", **(replies or {})}

    def __call__(self, cmd, stdin=None, cwd=None, timeout=None):
        guide = cmd[cmd.index("--system-prompt-file") + 1].rsplit("/", 1)[1]
        self.calls.append({"guide": guide, "tools": cmd[cmd.index("--tools") + 1], "stdin": stdin})
        if guide == "write-problem-ko.md" and guide not in self.replies:
            n = stdin.split("<number>\n", 1)[1].split("\n", 1)[0]
            return shell.Result(cmd=cmd, code=0, stdout=f"## {n}. title {n}\n\n**고른 이유.** r\n\n{SECTIONS}")
        return shell.Result(cmd=cmd, code=0, stdout=self.replies.get(guide, f"text from {guide}"))

    def guides(self):
        return sorted(c["guide"] for c in self.calls)


def _run(s, r, **kw):
    said = []
    writer.write_report(s, "ko", "claude", "0.1.88", "0.2.0", say=said.append, run=r, **kw)
    return said, (s / "report.md").read_text()


def test_the_agents_and_what_each_one_gets(tmp_path):
    s = _snap(tmp_path)
    r = Runner()
    _run(s, r)
    assert r.guides() == ["check-facts-ko.md", "check-solutions-ko.md", "write-overview-ko.md", "write-problem-ko.md", "write-problem-ko.md"]  # nothing to fix: no replacer
    by = {c["guide"]: c for c in r.calls}
    assert by["check-solutions-ko.md"]["tools"] == writer.READ_ONLY_TOOLS and by["check-facts-ko.md"]["tools"] == writer.READ_ONLY_TOOLS
    assert by["write-overview-ko.md"]["tools"] == "" and by["write-problem-ko.md"]["tools"] == ""  # a writer has no tools at all
    check_input = json.loads(by["check-solutions-ko.md"]["stdin"])
    assert check_input["scale"] == "small" and set(check_input["problems"][0]) == {"id", "title", "targets", "scope", "solutions"}  # nothing the analysis wrote to explain them
    overview_in = by["write-overview-ko.md"]["stdin"]
    assert "<glossary>" in overview_in and "nodes rebooted" in overview_in and '"solutions"' not in overview_in  # the overview names problems, it does not explain them
    problem_inputs = [c["stdin"] for c in r.calls if c["guide"] == "write-problem-ko.md"]
    assert sorted(i.split("<number>\n", 1)[1].split("\n", 1)[0] for i in problem_inputs) == ["1", "2"]
    assert all("<glossary>" in i and '"declared_in"' in i and '"severity"' in i for i in problem_inputs)  # the writer gets the facts with the computed parts
    assert "<notes>\nnone\n</notes>" in by["check-facts-ko.md"]["stdin"] and "## 1. title 1" in by["check-facts-ko.md"]["stdin"]
    assert (s / "llm" / "facts-analysis.json").is_file() and json.loads((s / "llm" / "facts.json").read_text())["scale"]["name"] == "small"
    assert sorted(p.name for p in (s / "llm" / "writing").iterdir()) == ["draft.md", "facts-check.md", "overview.md", "problem-1.md", "problem-2.md", "solutions.json"]


def test_the_report_is_assembled_in_its_order_with_what_code_writes(tmp_path):
    facts = _facts(
        upcoming=[{"when": "2026-11-20", "what": "certificate renews", "source_file": "summary.json", "json_path": "a"}],
        since_last={"done": [{"problem": "move the dumps", "proof": "7 CronJobs on n1"}], "appeared": ["two nodes rebooted"]},
        analysis={"area_summary": {"security": "one plaintext token"}},
    )
    s = _snap(tmp_path, facts)
    base = s.parent / "2026-11-11T14-00-00"
    base.mkdir()
    (base / "inventory.json").write_text(json.dumps({"taken_at": "2026-11-11T14:08:33+09:00"}))
    (base / "report.md").write_text("r")
    (s / "diff.json").write_text(
        json.dumps(
            {
                "a": str(base),
                "findings": {
                    "new": [],
                    "resolved": [],
                    "changed": [],
                    "criteria_changes": {"rule_changed": [{"id": "x.y.z", "check": "x.y", "status": "fail", "severity_default": "high"}, {"id": "x.y.w", "check": "x.y", "status": "warn", "severity_default": "low"}]},
                },
            }
        )
    )
    _said, text = _run(s, Runner(), skipped=[{"id": "grafana-token", "header": "Grafana 토큰", "gain": ["대시보드 목록"]}])
    order = [
        "# lab — full 점검, 2026-11-14 12:00",
        "지금 깨져 있는 것: 없음",
        "## 클러스터 한눈에",
        "## 이미 일어난 일",
        "## 1. title 1",
        "## 2. title 2",
        "## 그다음으로 큰 문제",
        "## 하지 않기로 한 것",
        "## 지난 리포트 이후",
        "## 다가오는 일",
        "## 영역별 한 줄",
        "## 이번 점검의 한계",
        "## 숫자",
        "항목별 체크:",
    ]
    at = [text.index(x) for x in order]
    assert at == sorted(at)
    assert "가장 큰 문제 2개: ① title 1 ② title 2" in text and "이미 일어난 일: nodes rebooted" in text and "운영 규모: 소형" in text
    assert "## 이미 일어난 일\n\n2026-11-11 14:08부터 2026-11-14 12:00까지 본 것이에요." in text
    assert "## 지금 깨져 있는 것" not in text  # nothing broken: the section is not there, the first screen says so
    assert "| move the dumps | 반영됨 | 7 CronJobs on n1 |" in text and "**새로 생긴 것**\n\n- two nodes rebooted" in text and "**없어진 것**\n\n- 없음" in text
    assert "**두 점검 사이에 판정 규칙이 바뀐 항목**\n\n- `x.y` 2" in text  # counted per check; the ids are in report-details.md
    assert "| 2026-11-20 | certificate renews | summary.json |" in text and "| security | one plaintext token |" in text
    assert "- Grafana 토큰.\n  - 약해지는 결론: 대시보드 목록." in text and "kubegap에 전용 점검 항목이 없어요: istio." in text
    assert "비교 기준은 2026-11-11 14:08 full 점검이에요." in text and "| critical | 1 | 0 | 0 | 0 |" in text
    assert "- 사건 A: `traffic.pod-not-ready.*`" in text and "- 문제 1: `resilience.no-backup.cluster`" in text
    assert text.rstrip().endswith(f"수집 자료 `{s}`")


def test_facts_that_break_the_contract_stop_before_any_agent(tmp_path):
    s = _snap(tmp_path, _facts(problems=[_problem("2", ["resilience.replicas-same-node.*"], "outage")]))
    r = Runner()
    with pytest.raises(writer.WriterError, match="in no list") as e:
        writer.write_report(s, "ko", "claude", "r", "v", say=lambda m: None, run=r)
    assert "check-facts" in str(e.value) and r.calls == []


def test_what_the_solution_check_found_goes_into_the_facts(tmp_path):
    found = {
        "cautions": [{"problem": "2", "solution": 0, "what": "a new pod runs db-migrate with --accept-data-loss", "read": ["objects/deployments.json"]}, {"problem": "9", "solution": 0, "what": "x"}],
        "drop": [{"problem": "2", "solution": 1, "reason": "evicts the only replica of the database"}],
        "scope": [{"problem": "2", "affected": [], "not_checked": ["prod/deployment/api"]}],
    }
    out, notes = writer.apply_solution_check(_facts(), found)
    p = out["problems"][1]
    assert [s["approach"] for s in p["solutions"]] == ["spread"] and p["dropped_solutions"] == [{"approach": "descheduler", "reason": "evicts the only replica of the database"}]
    assert p["solutions"][0]["cautions"] == [{"what": "a new pod runs db-migrate with --accept-data-loss", "read": ["objects/deployments.json"], "from": "solution check"}]
    assert p["scope"] == {"affected": [], "not_checked": ["prod/deployment/api"]}
    assert any("does not exist" in n for n in notes) and any("dropped" in n for n in notes)
    every = {"cautions": [], "drop": [{"problem": "1", "solution": 0, "reason": "r1"}, {"problem": "1", "solution": 1, "reason": "r2"}], "scope": []}
    kept = writer.apply_solution_check(_facts(), every)[0]["problems"][0]["solutions"]
    assert len(kept) == 1 and kept[0]["cautions"][-1]["what"] == "r2"  # a problem is never left without a way out


def test_shape_terms_and_facts_are_fixed_in_one_replacement(tmp_path):
    s = _snap(tmp_path)
    bad = "## 1. title 1\n\n**고른 이유.** r\n\n### 무슨 일인가\n\n파드를 놓는 순간에만 적용돼요. [m](https://memory.example/x)\n"
    fixed = OVERVIEW + "\n## 1. title 1\n\n**고른 이유.** r\n\n" + SECTIONS + "\n## 2. title 2\n\n**고른 이유.** r\n\n" + SECTIONS
    r = Runner({"check-facts-ko.md": '- 인용: "x"\n  사실: y\n  출처: z', "replace-ko.md": fixed})
    r.replies["write-problem-ko.md"] = bad
    _said, text = _run(s, r)
    wrong = next(c for c in r.calls if c["guide"] == "replace-ko.md")["stdin"].split("<wrong>\n", 1)[1]
    assert '- 인용: "x"' in wrong and "needs these sections in this order" in wrong and "https://memory.example/x" in wrong and "'파드를 놓' is not used" in wrong
    assert "### 왜 생기나" in text and "파드를 놓는" not in text


def test_a_replacement_that_drops_a_code_block_or_adds_an_address_is_refused(tmp_path):
    s = _snap(tmp_path)
    dropped = (OVERVIEW + "\n## 1. title 1\n\n" + SECTIONS + "\n## 2. title 2\n\n" + SECTIONS).replace("maxUnavailable: 1", "maxUnavailable: 2")
    said, text = _run(s, Runner({"check-facts-ko.md": "- 인용: x", "replace-ko.md": dropped}))
    assert any("the replacement was dropped" in m and "code block" in m for m in said) and "maxUnavailable: 1" in text
    before = "## 1. t\n\n### a\n\n[x](" + URL + ")\n"
    assert writer.gate(before, before.replace("[x]", "[y]"), {URL}) == []
    assert "address the facts do not hold" in writer.gate(before, before + "[n](https://new.example/)\n", {URL})[0]
    assert writer.gate(before, before + "\n### b\n", {URL}) == [] and writer.gate(before + "\n### b\n", before, {URL}) == ["a section is gone"]
    assert writer.gate(before, before + "\n## 2. u\n", {URL}) == ["the number of problems changed"]


def test_a_daily_report_picks_no_problems_and_shows_the_last_full_run_s(tmp_path):
    full = tmp_path / "c" / "2026-11-10T09-00-00"
    (full / "llm").mkdir(parents=True)
    (full / "MODE").write_text("full")
    (full / "report.md").write_text("r")
    (full / "inventory.json").write_text(json.dumps({"taken_at": "2026-11-10T09:00:00+09:00"}))
    (full / "llm" / "facts.json").write_text(json.dumps({"schema": 2, "problems": [{"title": "backups stay in the cluster"}, {"title": "replicas on one node"}]}))
    daily = _facts(problems=[], next=[{"id": "N1", "title": "serious", "finding_ids": ["resilience.no-backup.cluster", "resilience.replicas-same-node.*"]}])
    daily["happened"]["incidents"][0]["exposed"] = ["N1"]
    s = _snap(tmp_path, daily, mode="daily")
    r = Runner()
    _said, text = _run(s, r)
    assert r.guides() == ["check-facts-ko.md", "write-overview-ko.md"]  # no problems: no solution check, no problem writer
    assert "가장 큰 문제 (2026-11-10 09:00 full 점검): ① backups stay in the cluster ② replicas on one node" in text
    assert "## 지금 남아 있는 심각한 문제" in text and "## 그다음으로 큰 문제" not in text and "## 영역별 한 줄" not in text and "## 1. " not in text


def test_a_failed_agent_stops_with_the_reason(tmp_path):
    s = _snap(tmp_path)

    def run(cmd, stdin=None, cwd=None, timeout=None):
        return shell.Result(cmd=cmd, code=1, stdout="", stderr="rate limited")

    with pytest.raises(writer.WriterError, match="rate limited"):
        writer.write_report(s, "ko", "claude", "r", "v", say=lambda m: None, run=run)
    (s / "llm" / "facts.json").unlink()
    with pytest.raises(writer.WriterError, match=r"references/facts-ko\.md"):
        writer.write_report(s, "ko", "claude", "r", "v", say=lambda m: None, run=Runner())
    with pytest.raises(writer.WriterError, match="no prompts for language fr"):
        writer.write_report(_snap(tmp_path / "x"), "fr", "claude", "r", "v", say=lambda m: None, run=Runner())


def test_numbers_are_checked_against_the_snapshot(tmp_path):
    def with_numbers(numbers):
        return _facts(problems=[_problem("1", ["resilience.no-backup.cluster"], "irreversible", facts=numbers)])

    s = _snap(tmp_path)
    assert writer.verify_numbers(s, _facts()) == []
    assert "facts say 9" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "summary.json", "json_path": "a.b[0].c"}]))[0]
    assert "a.z is not in summary.json" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "summary.json", "json_path": "a.z"}]))[0]
    assert "does not exist" in writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "source_file": "no.json", "json_path": "a"}]))[0]
    assert writer.verify_numbers(s, with_numbers([{"what": "x", "value": 9, "derived": True}])) == []
    dated = _facts(upcoming=[{"when": "2026-11-07", "what": "node-1 expires", "source_file": "summary.json", "json_path": "a.b[0].c"}])
    assert "upcoming: node-1 expires: facts say 2026-11-07" in writer.verify_numbers(s, dated)[0]  # a date has a source like a number


def test_agents_get_no_user_settings_and_codex_stays_read_only(tmp_path):
    cmd, prefix = writer.agent_command("claude", writer.REFERENCES / "write-problem-ko.md", read_files=False)
    assert cmd[cmd.index("--setting-sources") + 1] == "" and cmd[cmd.index("--tools") + 1] == "" and prefix == ""
    cmd, prefix = writer.agent_command("codex", writer.REFERENCES / "check-facts-ko.md", read_files=True)
    assert cmd[:4] == ["codex", "exec", "--sandbox", "read-only"] and prefix.startswith("다 쓰인 점검 리포트를")


def test_the_korean_prompts_are_written_as_statements_and_carry_whole_examples():
    for name in writer.GUIDES:
        text = (writer.REFERENCES / f"{name}-ko.md").read_text()
        assert not any(w in text for w in ("You are", "Do not")), name  # written in Korean, not carried over
        head = text.split("<example>")[0]
        for ending in ("해요.", "써요.", "봐요.", "않아요."):  # the instructions are plain statements: an agent copies the voice of its instructions
            assert ending not in "\n".join(ln for ln in head.splitlines() if "`" not in ln and "“" not in ln and '"' not in ln), (name, ending)
    problem = (writer.REFERENCES / "write-problem-ko.md").read_text()
    assert problem.count("<example>") == 2 and all(f"### {x}" in problem for x in writer.HEADINGS["ko"]["sections"])
    overview = (writer.REFERENCES / "write-overview-ko.md").read_text()
    assert all(f"## {writer.HEADINGS['ko'][k]}" in overview for k in ("broken", "happened", "next", "since"))
    for text in (problem, overview):
        for tool_word in ("kubegap", "render-details", "findings-draft"):
            assert tool_word not in text
    for old in ("writing-ko.md", "writing-en.md", "check-actions-ko.md", "check-actions-en.md", "review-facts.md", "edit-ko.md", "report-grouping.md"):
        assert not (paths.ROOT / "references" / old).exists(), old


def test_an_english_report_says_its_guides_are_not_written_yet(tmp_path):
    with pytest.raises(writer.WriterError, match=r"write-problem-en\.md"):
        writer.write_report(_snap(tmp_path), "en", "claude", "r", "v", say=lambda m: None, run=Runner())


def test_the_glossary_names_what_not_to_write_and_skips_code():
    terms = glossary.load("ko")
    assert terms and all(t["use"] and t["avoid"] for t in terms)
    hits = glossary.find("스케줄러가 파드를 놓는 순간에만 적용돼요.\n\n```\n퇴거\n```\n`퇴거`는 그대로예요.", terms)
    assert len(hits) == 1 and "'파드를 놓'" in hits[0] and "스케줄링" in hits[0]
    assert glossary.find("스케줄링할 때만 적용돼요.", terms) == []
    for example in ("write-problem-ko.md", "write-overview-ko.md"):  # the examples the writers imitate follow the glossary themselves
        assert glossary.find((writer.REFERENCES / example).read_text().split("<example>", 1)[1], terms) == [], example


def test_blocks_get_blank_lines_but_lists_tables_and_code_stay_together():
    body = "Urgent now: no\nToday: ① a\n\n## 1. t\n\n**What.** x\n- a: 1\n- b: 2\n**Why.** y\n① do\n```\nkubectl get pods\nkubectl get nodes\n```\nCheck: ok\n**Evidence.**\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    out = writer.space_blocks(body)
    assert "Urgent now: no\n\nToday: ① a\n\n## 1. t" in out
    assert "**What.** x\n\n- a: 1\n- b: 2\n\n**Why.** y\n\n① do\n\n```\nkubectl get pods\nkubectl get nodes\n```\n\nCheck: ok\n\n**Evidence.**\n\n| a | b |\n|---|---|\n| 1 | 2 |" in out
    assert writer.space_blocks(out) == out  # idempotent


def test_code_prints_the_findings_the_checks_changed_from_diff_json(tmp_path):
    s = _snap(tmp_path)
    crit = {
        "new_checks": [{"id": "traffic.ingress-nginx-retired.cluster", "check": "traffic.ingress-nginx-retired", "status": "warn", "severity_default": "medium"}],
        "severity_changed": [{"id": f"resilience.single-eligible-node.prod/deployment/a{i}", "check": "resilience.single-eligible-node", "status": "warn", "severity_default": ["high", "medium"]} for i in range(42)],
        "dropped_checks": [],
        "note": "text",
    }
    (s / "diff.json").write_text(json.dumps({"findings": {"criteria_changes": crit}}))
    out = "\n".join(writer.criteria_changes(s, writer.HEADINGS["ko"]))
    assert "운영 규모나 점검 기준이 바뀌어 심각도가 달라진 항목**\n\n- `resilience.single-eligible-node` 42" in out  # one line for forty-two findings; the ids are in report-details.md
    assert "클러스터가 아니라 점검에 새로 보인 것**\n\n- `traffic.ingress-nginx-retired` 1" in out
    assert "이번에 돌지 않은 점검 항목" not in out  # an empty bucket prints nothing
    assert writer.criteria_changes(tmp_path, writer.HEADINGS["en"]) == []  # no diff.json, no lines

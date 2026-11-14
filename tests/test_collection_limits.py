"""A collection limit that was reached is recorded: the last N lines of a node log, a page of an AWS list, the tail of a component log. What was
read is then not all there is, and the summary and the report say which step stopped at its limit, so a count made from it is not read as the whole."""

from __future__ import annotations

import json

from lib.collection import aws, collect
from lib.foundations import shell
from lib.foundations.config import Config
from lib.foundations.runlog import RunLog
from lib.output import sections


class _Access:
    method = "ssh"

    def __init__(self, lines):
        self.lines = lines

    def run_on_node(self, node, cmd, **kw):
        return shell.Result(cmd=["ssh"], code=0, stdout="x\n" * self.lines[node])


class _Runner:
    def __init__(self, lines):
        self.na = _Access(lines)

    def caps(self):
        return {}

    def select(self, which):
        return sorted(self.na.lines)


def test_a_node_log_that_filled_its_tail_limit_is_recorded(tmp_path):
    st = {"id": "k3s-webhook-failures", "type": "node", "cmd": "journalctl -u k3s --since -24h | grep -E 'failed calling webhook' | tail -n 200", "out": "logs/node/{node}/w.log"}
    res = collect.node_steps.run_node_step(st, st["id"], "k3s-platform", {}, Config(), tmp_path, RunLog(None), _Runner({"a": 200, "b": 17}), 10, None)
    assert res["nodes"]["a"]["at_limit"] is True and res["nodes"]["a"]["line_limit"] == 200 and res["nodes"]["b"]["at_limit"] is False
    assert res["at_limit"] == ["a"]
    summary = collect.step_summary({"k3s-platform": {"steps": {st["id"]: res}}}, "full", 1.0)
    assert summary["at_limit"] == {"k3s-platform.k3s-webhook-failures": ["a"]}


def test_an_aws_list_that_stopped_before_the_end_says_so():
    assert aws.more_to_read(json.dumps({"imageDetails": [], "NextToken": "eyJ"})) and aws.more_to_read(json.dumps({"nextToken": "t"}))
    assert not aws.more_to_read(json.dumps({"imageDetails": []})) and not aws.more_to_read("") and not aws.more_to_read("not json")


def test_the_limits_section_names_the_steps_that_stopped_at_a_limit(tmp_path):
    (tmp_path / "summary.json").write_text(json.dumps({"collection": {"at_limit": {"ecr.images": ["app/api"], "core.component-logs": ["argocd: argocd/argocd-server"]}}}))
    (tmp_path / "inventory.json").write_text(json.dumps({}))
    text = sections.limits({}, tmp_path, "ko")
    assert "수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: `core.component-logs` (argocd: argocd/argocd-server); `ecr.images` (app/api)." in text
    assert "실제보다 적을 수 있고" in text
    (tmp_path / "summary.json").write_text(json.dumps({"collection": {"at_limit": {}}}))
    assert "자체 제한" not in sections.limits({}, tmp_path, "ko")


def test_a_step_that_takes_the_first_item_on_purpose_is_not_at_a_limit(tmp_path, monkeypatch):
    """`pricing get-products --max-results 1` returns one product and a token for the rest: that is the request, not a list that was cut."""
    from lib.collection.collect import cloud_steps

    monkeypatch.setattr(cloud_steps._aws, "aws", lambda args, **kw: shell.Result(cmd=["aws"], code=0, stdout=json.dumps({"PriceList": ["x"], "NextToken": "t"})))
    eks = {"name": "c", "region": "ap-northeast-2"}
    step = {"id": "pricing", "type": "aws", "args": ["pricing", "get-products", "--max-results", "1"], "out": "aws/pricing.json"}
    assert cloud_steps.run_aws_step(step, "pricing", "eks-platform", eks, Config(), tmp_path, RunLog(None), 10, None)["at_limit"] == ["pricing"]
    assert cloud_steps.run_aws_step({**step, "first_only": True}, "pricing", "eks-platform", eks, Config(), tmp_path, RunLog(None), 10, None)["at_limit"] == []

"""The facts the artifacts carry for the report model (#61, #64, #76): a finding's whole material in `details`, open defects as `known_issues`, and a `rule_hash` that outlives rewording."""

from __future__ import annotations

import json

from lib.foundations import paths, rubric
from lib.judgement.evaluate import Context
from lib.judgement.evaluate.rules import Run, details, referenced_keys
from lib.judgement.evaluate.types import eval_summary

CHECK = {
    "id": "resilience.prod-concentration",
    "name": "n",
    "area": "resilience",
    "type": "summary",
    "each": "resilience.placement.prod_by_node",
    "rule": {"expr": "item['share'] >= 0.4"},
    "target": "item['node']",
    "evidence": "f\"{item['prod_pods']} prod pods {item['prod_workloads'][:10]}\"",
    "severity_default": "high",
}


def test_referenced_keys_reads_hard_and_soft_item_keys():
    assert referenced_keys(CHECK) == {"share", "node", "prod_pods", "prod_workloads"}
    assert referenced_keys({"rule": {"expr": "item.get('a', 0) > 1"}, "evidence": "f\"{item.get('b')}\""}) == {"a", "b"}


def test_details_keeps_the_whole_list_the_evidence_cut(tmp_path):
    workloads = [f"prod/app-{i}" for i in range(20)]
    item = {"node": "n1", "share": 0.48, "prod_pods": 20, "prod_workloads": workloads, "huge": list(range(10000)), "pool": "app"}
    summary = {"resilience": {"placement": {"prod_by_node": [item]}}}
    cx = Context(tmp_path, {}, summary, "large")
    run = Run(CHECK, cx, {})
    r = eval_summary(cx, CHECK, run)
    f = r["findings"][0]
    assert "prod/app-19" not in str(f["evidence"]) and "prod/app-9" in str(f["evidence"])  # the one-line evidence cuts at 10
    assert f["details"]["prod_workloads"] == workloads  # the whole list lives on the finding
    assert "huge" not in f["details"] and "pool" not in f["details"]  # only what the check read


def test_details_keeps_what_a_helper_read(tmp_path):
    """`_oom_text(item)` reads keys the expression text never names; the recorder sees them, a regex over the text could not."""
    check = {
        "id": "resources.oomkilled-repeated",
        "name": "n",
        "area": "resources",
        "type": "summary",
        "each": "resilience.oom_7d.rows",
        "rule": {"expr": "item.get('kernel_kills_24h', 0) >= 3"},
        "target": "item['target']",
        "evidence": "_oom_text(item)",
        "severity_default": "high",
    }
    item = {
        "target": "a/deploy/x:c",
        "kernel_kills_24h": 5,
        "kernel_log_read": True,
        "kernel_nodes_read": 2,
        "kernel_nodes_total": 2,
        "last_kill": "t",
        "pods_oomkilled": 3,
        "pods_replaced": 2,
        "restarts_of_those_pods": 5,
        "cadvisor_oom_events_7d": 0,
        "pods": [{"pod": "p"}],
        "nodes": ["n1"],
    }
    cx = Context(tmp_path, {}, {"resilience": {"oom_7d": {"rows": [item]}}}, "large")
    run = Run(check, cx, {})
    f = eval_summary(cx, check, run)["findings"][0]
    assert {"last_kill", "pods_replaced", "cadvisor_oom_events_7d", "kernel_nodes_total"} <= set(f["details"])
    assert "pods" not in f["details"] and "nodes" not in f["details"]  # read by nobody


def test_details_for_metric_object_and_inventory_items():
    assert details({}, {"labels": {"pod": "p", "namespace": "a"}, "value": 0.3}) == {"labels": {"pod": "p", "namespace": "a"}, "value": 0.3}
    assert details({}, {"labels": {"node": "n"}, "v": {"x": 1, "y": 2}, "value": 1}) == {"labels": {"node": "n"}, "values": {"x": 1, "y": 2}}
    assert details({}, {"obj": {"kind": "Deployment"}, "ns": "a", "name": "web"}) == {"namespace": "a", "name": "web", "kind": "Deployment"}
    assert details({}, {"item": {"a": 1}, "key": "k"}) == {"key": "k", "item": {"a": 1}}
    assert details({}, {"prod": False}) is None  # absence and cluster-level checks carry nothing


def test_details_merge_into_a_list_when_instances_merge(tmp_path):
    check = {**CHECK, "target": "'cluster'"}
    items = [{"node": "n1", "share": 0.5, "prod_pods": 3, "prod_workloads": ["a"]}, {"node": "n2", "share": 0.6, "prod_pods": 4, "prod_workloads": ["b"]}]
    cx = Context(tmp_path, {}, {"resilience": {"placement": {"prod_by_node": items}}}, "large")
    run = Run(check, cx, {})
    f = eval_summary(cx, check, run)["findings"][0]
    assert f["instances"] == 2 and [d["prod_pods"] for d in f["details"]] == [3, 4] and "node" not in f["details"][0]  # the target no longer reads node, so details does not carry it


def test_damaged_known_issues_file_is_an_error_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUBRIC_DIR", tmp_path)
    (tmp_path / "known-issues.yaml").write_text("checks:\n  a.b:\n    - issue: abc\n")
    known, errors = rubric.load_known_issues()
    assert known == {} and errors and "not a number" in errors[0]
    (tmp_path / "known-issues.yaml").write_text("- just a list\n")
    assert rubric.load_known_issues() == ({}, ["rubric/known-issues.yaml: expected a mapping with a `checks` mapping"])


def test_rule_hash_is_pinned_and_ignores_gates_and_number_spelling():
    base = {"id": "x", "type": "metric", "inputs": ["m"], "rule": {"expr": "value >= threshold", "threshold": {"prod": 0.25, "lab": 1}}, "target": "labels['pod']", "platforms": ["eks"], "modes": ["full"]}
    assert rubric.rule_hash(base) == rubric.rule_hash({**base, "platforms": None, "scales": ["large"], "modes": None, "requires_tool": "krr"})  # gates are read from check_results.status, not from the hash
    assert rubric.rule_hash(base) == rubric.rule_hash({**base, "rule": {"expr": "value >= threshold", "threshold": {"prod": 0.25, "lab": 1.0}}})  # 1 and 1.0 are one number
    assert rubric.rule_hash(base) == "529422faedeb"  # pinned: a change here means every check will read as rule_changed in the next diff, so it must be deliberate


def test_rule_hash_ignores_wording_and_follows_thresholds():
    base = {"id": "x", "type": "metric", "inputs": ["m"], "rule": {"expr": "value >= threshold", "threshold": {"prod": 0.25, "lab": 0.25}}, "target": "labels['pod']", "evidence": 'f"{value}"', "why": "one", "platforms": ["eks"]}
    reworded = {**base, "why": "two", "name": "other", "evidence": 'f"now {value}"', "suggest": "s", "cases": [{"who": "a", "url": "u"}]}
    retuned = {**base, "rule": {"expr": "value >= threshold", "threshold": {"prod": 0.30, "lab": 0.25}}}
    assert rubric.rule_hash(base) == rubric.rule_hash(reworded)
    assert rubric.rule_hash(base) != rubric.rule_hash(retuned)
    assert len(rubric.rule_hash(base)) == 12


def test_known_issues_file_names_real_checks_and_tracker_numbers():
    known, errors = rubric.load_known_issues()
    assert known and not errors, f"rubric/known-issues.yaml is empty, missing or damaged: {errors}"
    checks, _errors = rubric.load_checks([p.name for p in sorted(paths.COLLECTORS_DIR.iterdir()) if (p / "checks.yaml").is_file()])
    ids = {c["id"] for c in checks}
    for cid, rows in known.items():
        assert cid in ids, f"{cid} in rubric/known-issues.yaml is not a check"
        for r in rows:
            assert isinstance(r["issue"], int) and r["issue"] > 0 and r["note"], f"{cid}: every entry needs an issue number and a note"


def test_known_issue_reaches_the_finding_and_its_evidence(tmp_path, monkeypatch):
    from lib.judgement import evaluate

    monkeypatch.setattr(rubric, "load_known_issues", lambda: ({"resilience.prod-concentration": [{"issue": 64, "note": "n"}]}, []))
    item = {"node": "n1", "share": 0.5, "prod_pods": 3, "prod_workloads": ["a"]}
    (tmp_path / "summary.json").write_text(json.dumps({"resilience": {"placement": {"prod_by_node": [item]}}}))
    (tmp_path / "inventory.json").write_text(json.dumps({"scale": {"name": "large", "source": "guessed"}, "cluster": {"platform": "eks"}}))
    monkeypatch.setattr(rubric, "load_checks", lambda collectors: ([{**CHECK, "collector": "core"}], []))
    from lib.foundations.config import load_config

    evaluate.evaluate(tmp_path, load_config(None), echo=None)
    d = json.loads((tmp_path / "findings-draft.json").read_text())
    f = d["findings"][0]
    assert f["known_issues"] == [{"issue": 64, "note": "n"}] and "known issue" not in f["evidence"]  # the evidence stays the check's; render adds the tag
    from lib.output.render import _evidence

    assert _evidence(f, 300).endswith(" known issue #64")
    rec = next(c for c in d["check_results"] if c["id"] == CHECK["id"])
    assert rec["known_issues"] == f["known_issues"] and len(rec["rule_hash"]) == 12

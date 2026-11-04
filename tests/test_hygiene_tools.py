"""The tool files are parsed the way the pinned tools write them (#119): kubent's Since is the deprecation minor and the removal minor is in the rule set text,
its cluster-scoped objects say "<undefined>", polaris's Results count controllers with a failure once the successes are filtered out."""

from __future__ import annotations

import json
from pathlib import Path

from lib import hygiene

ROOT = Path(__file__).resolve().parent.parent


def _snap(tmp_path, **files):
    (tmp_path / "tools").mkdir()
    for name, doc in files.items():
        (tmp_path / "tools" / f"{name}.json").write_text(json.dumps(doc))
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": {name: {"ok": True, "api_read": True} for name in files}}}))
    return tmp_path


# kubent 0.7.3 pkg/judge/judge.go:3-11, pkg/rules/rego/deprecated-1-25.rego:13-33 (PodDisruptionBudget: since 1.21 in the rule set "removed in 1.25"), rego.go:61-64 ("<undefined>")
KUBENT_ROWS = [
    {"Name": "restricted", "Namespace": "<undefined>", "Kind": "PodSecurityPolicy", "ApiVersion": "policy/v1beta1", "RuleSet": "Deprecated APIs removed in 1.25", "ReplaceWith": "<removed>", "Since": "1.21"},
    {"Name": "web", "Namespace": "prod-a", "Kind": "PodDisruptionBudget", "ApiVersion": "policy/v1beta1", "RuleSet": "Deprecated APIs removed in 1.25", "ReplaceWith": "policy/v1", "Since": "1.21"},
    {"Name": "fs", "Namespace": "prod-a", "Kind": "FlowSchema", "ApiVersion": "flowcontrol.apiserver.k8s.io/v1beta3", "RuleSet": "Deprecated APIs removed in 1.32", "ReplaceWith": "flowcontrol.apiserver.k8s.io/v1", "Since": "1.29"},
    {"Name": "x", "Namespace": "prod-a", "Kind": "Thing", "ApiVersion": "x/v1beta1", "RuleSet": "Deprecated APIs to be removed in future", "ReplaceWith": "x/v1", "Since": "1.21"},
]


def test_kubent_removed_minor_comes_from_the_rule_set_and_is_judged_against_the_target(tmp_path):
    snap = _snap(tmp_path, kubent=KUBENT_ROWS)
    d = hygiene._deprecated(hygiene._Ctx(snap, {"cluster": {"server_version": "v1.24.17-eks-abc"}}))
    assert d["target_minor"] == "1.25"
    by_name = {i["name"]: i for i in d["items"]}
    psp, pdb, fs, future = by_name["restricted"], by_name["web"], by_name["fs"], by_name["x"]
    assert psp["deprecated_in"] == "1.21" and psp["removed_in"] == "1.25" and psp["removed"] is True
    assert psp["namespace"] is None and psp["replacement"] is None  # "<undefined>" and "<removed>" are kubent's spellings of absence
    assert pdb["removed"] is True and pdb["replacement"] == "policy/v1" and pdb["namespace"] == "prod-a"
    assert fs["removed_in"] == "1.32" and fs["removed"] is False  # removed later than the target: still deprecated, not removed
    assert future["removed_in"] is None and future["removed"] is False and future["deprecated"] is True
    assert [i["name"] for i in d["removed_next"]] == ["restricted", "web"]


def test_kubent_rows_are_never_removed_without_a_target(tmp_path):
    snap = _snap(tmp_path, kubent=KUBENT_ROWS)
    d = hygiene._deprecated(hygiene._Ctx(snap, {}))
    assert d["target_minor"] is None and all(i["removed"] is False for i in d["items"])


def test_pluto_target_versions_supply_the_minor_when_the_inventory_has_none(tmp_path):
    snap = _snap(tmp_path, kubent=KUBENT_ROWS, pluto={"target-versions": {"k8s": "v1.32.0"}})
    d = hygiene._deprecated(hygiene._Ctx(snap, {}))
    assert d["target_minor"] == "1.32"
    assert {i["name"] for i in d["removed_next"]} == {"restricted", "web", "fs"}


def test_the_check_fails_on_a_kubent_row_removed_by_the_target(tmp_path):
    from lib import evaluate
    from tests.test_degraded import _all_checks, _ctx

    snap = _snap(tmp_path, kubent=KUBENT_ROWS[:1])
    summary = hygiene._deprecated(hygiene._Ctx(snap, {"cluster": {"server_version": "v1.24.0"}}))
    check = next(c for c in _all_checks() if c["id"] == "hygiene.deprecated-api")
    r = evaluate.evaluate_check(check, _ctx(snap, {"hygiene": {"deprecated": summary}}), {})
    assert r["status"] == "done" and r["counts"] == {"fail": 1}
    assert r["findings"][0]["target"] == "podsecuritypolicy/restricted"  # no namespace, no leading slash
    assert "removed 1.25" in r["findings"][0]["evidence"]


# polaris v10.2.6 pkg/validator/output.go:77-91: with --only-show-failed-tests a controller without a failed check is not in Results at all
def test_polaris_controllers_is_the_cluster_info_count_and_results_are_objects_with_failures(tmp_path):
    doc = {
        "PolarisOutputVersion": "1.0",
        "ClusterInfo": {"Version": "v1.32.0", "Nodes": 3, "Pods": 40, "Namespaces": 8, "Controllers": 25},
        "Score": 81,
        "Results": [
            {
                "Name": "web",
                "Namespace": "prod-a",
                "Kind": "Deployment",
                "Results": {},
                "PodResult": {
                    "Name": "",
                    "Results": {},
                    "ContainerResults": [
                        {
                            "Name": "app",
                            "Results": {"cpuLimitsMissing": {"ID": "cpuLimitsMissing", "Message": "CPU limits should be set", "Details": None, "Success": False, "Severity": "warning", "Category": "Efficiency", "Mutations": None}},
                        }
                    ],
                },
                "CreatedTime": "2026-01-01T00:00:00Z",
            },
            {
                "Name": "ing",
                "Namespace": "prod-a",
                "Kind": "Ingress",
                "Results": {"tlsSettingsMissing": {"ID": "tlsSettingsMissing", "Message": "Ingress does not have TLS configured", "Details": None, "Success": False, "Severity": "warning", "Category": "Security", "Mutations": None}},
                "PodResult": None,
                "CreatedTime": "2026-01-01T00:00:00Z",
            },
        ],
    }
    snap = _snap(tmp_path, polaris=doc)
    p = hygiene._polaris(hygiene._Ctx(snap, {"namespaces": {"prod_like": ["prod-a"]}}))
    assert p["controllers"] == 25 and p["with_failures"] == 2 and p["score"] == 81 and "audited" not in p
    assert [w["target"] for w in p["workloads"]] == ["prod-a/deployment/web", "prod-a/ingress/ing"]
    assert p["workloads"][0]["failed"][0]["where"] == "container:app"
    assert p["by_category"] == {"Efficiency/warning": 1, "Security/warning": 1}

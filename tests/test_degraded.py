"""A check whose input is missing reports skip, never pass (#114): the `rule.needs` gate, the builders that stopped answering "nothing" with zeros,
and a scan that keeps availability guards out of `expr`."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib import discover, evaluate, rubric, summarize, yamlite
from lib.runlog import RunLog

ROOT = Path(__file__).resolve().parent.parent


def _ctx(tmp_path, summary: dict, inv: dict | None = None):
    inv = inv or {"cluster": {"platform": "k3s"}, "namespaces": {"prod_like": []}, "profile": {"name": "lab"}}
    (tmp_path / "inventory.json").write_text(json.dumps(inv))
    return evaluate.Context(tmp_path, inv, summary, rubric.load_profile("lab"))


def _check(**kw) -> dict:
    base = {
        "id": "t.needs",
        "name": "t",
        "area": "t",
        "type": "summary",
        "each": "sec.rows",
        "rule": {"needs": "item.get('metrics_available')", "needs_reason": "metrics not read", "expr": "item['bad'] > 0"},
        "evidence": "f\"bad {item['bad']}\"",
        "severity_default": "low",
        "profiles": ["lab"],
    }
    base.update(kw)
    return base


def test_every_target_lacking_the_input_makes_the_check_skip(tmp_path):
    cx = _ctx(tmp_path, {"sec": {"rows": [{"name": "a", "metrics_available": False, "bad": 5}, {"name": "b", "metrics_available": False, "bad": 0}]}})
    r = evaluate.evaluate_check(_check(), cx, {})
    assert r["status"] == "skip" and r["reason"] == "nothing to judge: metrics not read (2)" and r["findings"] == []
    assert r["counts"] == {"skipped": 2}


def test_some_targets_lacking_the_input_are_counted_and_named_not_passed(tmp_path):
    cx = _ctx(tmp_path, {"sec": {"rows": [{"name": "a", "metrics_available": True, "bad": 5}, {"name": "b", "metrics_available": False, "bad": 9}, {"name": "c", "metrics_available": True, "bad": 0}]}})
    r = evaluate.evaluate_check(_check(target="item['name']"), cx, {})
    assert r["status"] == "done" and r["counts"] == {"fail": 1, "skipped": 1, "pass": 1}
    assert r["skipped_reason"] == "metrics not read"
    assert [f["target"] for f in r["findings"]] == ["a"], "the unjudged target b is not a finding and not a pass"


def test_without_needs_the_old_behaviour_stays(tmp_path):
    cx = _ctx(tmp_path, {"sec": {"rows": [{"name": "a", "bad": 0}]}})
    r = evaluate.evaluate_check(_check(rule={"expr": "item['bad'] > 0"}), cx, {})
    assert r["status"] == "done" and r["counts"] == {"pass": 1} and "skipped_reason" not in r


def test_needs_reason_defaults_to_the_expression(tmp_path):
    cx = _ctx(tmp_path, {"sec": {"rows": [{"name": "a", "metrics_available": False, "bad": 1}]}})
    r = evaluate.evaluate_check(_check(rule={"needs": "item.get('metrics_available')", "expr": "item['bad'] > 0"}), cx, {})
    assert r["status"] == "skip" and r["reason"] == "nothing to judge: needs item.get('metrics_available')"


def test_eks_inventory_checks_skip_when_describe_cluster_failed(tmp_path):
    inv = {"cluster": {"platform": "eks", "eks": {"name": "c1", "region": "ap-northeast-2", "error": "AccessDeniedException: eks:DescribeCluster"}}, "namespaces": {"prod_like": []}, "profile": {"name": "lab"}}
    cx = _ctx(tmp_path, {}, inv)
    c = _check(id="eks.audit-log-off", type="inventory", each=None, rule={"expr": "'audit' not in ((inv['cluster'].get('eks') or {}).get('logging_enabled') or [])"}, evidence="'audit logging off'")
    del c["each"]
    r = evaluate.evaluate_check(c, cx, {})
    assert r["status"] == "skip" and r["reason"].startswith("EKS facts not read (eks describe-cluster: AccessDeniedException")
    inv["cluster"]["eks"] = {"name": "c1", "logging_enabled": ["api"]}
    cx = _ctx(tmp_path, {}, inv)
    assert evaluate.evaluate_check(c, cx, {})["status"] == "done"


# ---------- builders ----------


def test_webhooks_without_endpoints_file_report_nothing_as_endpoint_less(tmp_path):
    objs = tmp_path / "objects"
    objs.mkdir()
    wh = {"items": [{"metadata": {"name": "w"}, "webhooks": [{"name": "x", "failurePolicy": "Fail", "clientConfig": {"service": {"namespace": "ns", "name": "svc"}}, "rules": [{"resources": ["pods"]}]}]}]}
    (objs / "validatingwebhookconfigurations.admissionregistration.k8s.io.json").write_text(json.dumps(wh))
    (objs / "services.json").write_text(json.dumps({"items": []}))
    out = summarize.summarize_webhooks(tmp_path)
    assert out["no_endpoints"] is None and out["endpoints_read"] is False and out["webhooks"][0]["ready_endpoints"] is None
    (objs / "endpoints.json").write_text(json.dumps({"items": []}))
    out = summarize.summarize_webhooks(tmp_path)
    assert out["endpoints_read"] is True and [r["webhook"] for r in out["no_endpoints"]] == ["x"]


def test_discover_turns_the_node_backend_off_when_the_ssm_list_cannot_be_read(monkeypatch):
    from lib import shell

    monkeypatch.setattr(discover.kube, "kubectl_json", lambda *a, **k: ({"items": []}, None))
    monkeypatch.setattr(discover.aws, "aws_json", lambda *a, **k: (None, shell.Result(cmd=["aws"], code=254, stderr="An error occurred (AccessDeniedException) when calling the DescribeInstanceInformation operation")))
    out = discover._node_access("eks", {"nodes": [{"name": "n1", "provider_id": "aws:///ap-northeast-2a/i-0123456789abcdef0"}]}, {}, {"profile": "p", "region": "ap-northeast-2"}, RunLog(None))
    assert out["method"] == "none" and "AccessDeniedException" in out["ssm_error"]
    assert any("no node command is sent" in r for r in out["reasons"])


# ---------- the rubric itself ----------

ATOM = re.compile(r"""^\(?(?:\(item\.get\(['"][a-z_]+['"]\) or \{\}\)|item(?:\[['"][a-z_]+['"]\]|\.get\(['"][a-z_]+['"]\))?)(?:\[['"]([a-z_]+)['"]\]|\.get\(['"]([a-z_]+)['"]\))\)?$""")
FLAG = re.compile(
    r"^(available|applicable|present|collected|metrics_available|kubelet_metrics_available|api_metrics_available|controller_present)$"
)  # the availability keys the builders write; `prod_present` and the like are conditions, not availability
ALLOWED_GUARDS = {"argocd.sync-failures", "karpenter.interruption-handling", "traffic.metallb-l2-leader-concentration", "vpccni.node-ip-exhaustion"}  # a branch of the rule judges without the flag, or its absence is the finding


def _all_checks():
    for f in sorted(ROOT.glob("collectors/*/checks.yaml")):
        doc = yamlite.load_file(f)
        yield from doc.get("checks") if isinstance(doc, dict) else doc


def test_no_rule_guards_on_an_availability_flag_at_its_head():
    """`item.get('available') and …` at the head of expr evaluates to false and passes; the precondition belongs in rule.needs."""
    offenders = []
    for c in _all_checks():
        rule = c.get("rule") or {}
        for key in ("expr", "warn_expr"):
            e = str(rule.get(key) or "").strip()
            for conj in re.split(r"\s+and\s+", e):  # every bare flag conjunct, at the head or anywhere else, with single or double quotes
                m = ATOM.match(conj.strip())
                if m and FLAG.search(m.group(1) or m.group(2) or "") and c["id"] not in ALLOWED_GUARDS:
                    offenders.append(f"{c['id']} {key}: {e[:80]}")
                    break
    assert offenders == [], offenders


def test_every_needs_has_a_reason_and_parses():
    n = 0
    for c in _all_checks():
        rule = c.get("rule") or {}
        if rule.get("needs"):
            n += 1
            assert rule.get("needs_reason"), c["id"]
            compile(rule["needs"], c["id"], "eval")
    assert n >= 70


def test_selftest_accepts_expect_skip():
    src = (ROOT / "lib" / "selftest.py").read_text(encoding="utf-8")
    assert 'if expect == "skip"' in src
    assert sum(1 for c in _all_checks() for case in ((c.get("test") or {}).get("cases") or []) if case.get("expect") == "skip") >= 25


@pytest.mark.parametrize("cid", ["node.kubelet-reserved-missing", "eks.acm-certificate-expiring", "storage.ebs-unattached", "platform.k8s-version-eol", "eks.no-backup-policy", "ecr.pull-failures"])
def test_the_checks_the_issue_named_carry_needs(cid):
    c = next(c for c in _all_checks() if c["id"] == cid)
    assert c["rule"].get("needs") and c["rule"].get("needs_reason"), cid


def test_summarize_echo_survives_missing_endpoints(tmp_path):
    """`scripts/kubegap summarize` prints the webhook line; with endpoints unread it says so instead of calling len(None)."""
    (tmp_path / "objects").mkdir()
    (tmp_path / "inventory.json").write_text(
        json.dumps(
            {
                "context": "c",
                "cluster": {"platform": "k3s"},
                "profile": {"name": "lab"},
                "nodes": {"count": 0, "nodes": []},
                "namespaces": {"count": 0, "prod_like": []},
                "crds": {"count": 0},
                "node_access": {"method": "none"},
                "collectors_enabled": ["core"],
            }
        )
    )
    lines = []
    summarize.summarize(tmp_path, echo=lines.append)
    assert any("zero endpoints not read" in ln for ln in lines), lines


def test_albctl_webhooks_skip_when_endpointslices_were_not_read(tmp_path):
    from lib import albctl

    objs = tmp_path / "objects"
    objs.mkdir()
    dep = {"metadata": {"name": "aws-load-balancer-controller", "namespace": "kube-system"}, "spec": {"replicas": 2, "template": {"spec": {"containers": [{"image": "x:v2.8.0", "args": []}]}}}, "status": {"readyReplicas": 2}}
    (objs / "deployments.json").write_text(json.dumps({"items": [dep]}))
    wh = {
        "items": [
            {
                "metadata": {"name": "aws-load-balancer-webhook"},
                "webhooks": [{"name": "mpod.elbv2.k8s.aws", "failurePolicy": "Fail", "clientConfig": {"service": {"namespace": "kube-system", "name": "aws-load-balancer-webhook-service"}}, "rules": [{"resources": ["pods"]}]}],
            }
        ]
    }
    (objs / "mutatingwebhookconfigurations.admissionregistration.k8s.io.json").write_text(json.dumps(wh))
    out = albctl.analyze(tmp_path, {"cluster": {"platform": "eks"}, "namespaces": {"prod_like": []}})
    assert out["summary"]["webhook_no_endpoints"] is None, "endpointslices not read: no webhook is endpoint-less"
    (objs / "endpointslices.discovery.k8s.io.json").write_text(json.dumps({"items": []}))
    out = albctl.analyze(tmp_path, {"cluster": {"platform": "eks"}, "namespaces": {"prod_like": []}})
    assert out["summary"]["webhook_no_endpoints"] == ["mpod.elbv2.k8s.aws"]


def test_argocd_unread_pods_exclude_pods_the_collector_skipped(tmp_path):
    from lib import argocdctl

    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "deployments.json").write_text(
        json.dumps({"items": [{"metadata": {"name": "argocd-server", "namespace": "argocd"}, "spec": {"replicas": 1, "template": {"spec": {"containers": [{"image": "argocd:v2.13.0"}]}}}, "status": {"readyReplicas": 1}}]})
    )
    cr = {
        "argocd": {
            "steps": {
                "repo-server-metrics": {"pods": {"argocd-repo-server-a": {"ok": False, "error": "proxy blocked"}, "argocd-repo-server-old": {"ok": False, "skipped": "pod not Running (Succeeded)"}}},
                "server-metrics": {"pods": {"argocd-server-b": {"ok": True}}},
            }
        }
    }
    (tmp_path / "collect-result.json").write_text(json.dumps(cr))
    out = argocdctl.analyze(tmp_path, {"namespaces": {"prod_like": []}})
    assert out["summary"]["pods_unread"] == ["argocd-repo-server-a"]


def test_node_rows_for_unread_nodes_make_the_node_checks_skip_by_name(tmp_path):
    from lib import nodeos

    inv = {"nodes": {"nodes": [{"name": "n1"}, {"name": "n2"}]}, "cluster": {"platform": "k3s"}}
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": {"node-os": {"nodes": {"n1": {"ok": False, "error": "no node access"}}}}}}))
    out = nodeos.analyze(tmp_path, inv)
    assert [r["node"] for r in out["nodes"]] == ["n1", "n2"] and all(r["collected"] is False for r in out["nodes"])
    cx = _ctx(tmp_path, {"nodeos": out}, {**inv, "namespaces": {"prod_like": []}, "profile": {"name": "lab"}})
    c = next(c for c in _all_checks() if c["id"] == "node.kernel-lockup")
    r = evaluate.evaluate_check(c, cx, rubric.resolve_thresholds(c, rubric.load_profile("lab"), {}))
    assert r["status"] == "skip" and r["reason"] == "nothing to judge: node not read (2)"
    assert out["pod_logs"] is None and out["pod_dirs"] is None, "nothing large is not the same as nothing read"


def test_ssm_list_not_read_makes_ssm_unregistered_skip(tmp_path):
    inv = {"cluster": {"platform": "eks", "eks": {"name": "c"}}, "node_access": {"method": "none", "ssm_error": "AccessDenied", "ssm_unregistered": None, "ssm_registered": []}, "namespaces": {"prod_like": []}, "profile": {"name": "prod"}}
    cx = _ctx(tmp_path, {}, inv)
    c = next(c for c in _all_checks() if c["id"] == "eks.ssm-unregistered")
    r = evaluate.evaluate_check(c, cx, {})
    assert r["status"] == "skip" and "ssm_unregistered missing" in r["reason"]


SAVED_KINDS = {"kinds": 110, "skipped": ["pods"], "failed": {"foos.example.com": "boom"}, "not_permitted": ["csrs.certificates.k8s.io"]}  # what objects.dump-all returns; pluto reads what it saved


# The pinned binaries can exit 0 without reading the cluster (#117).
def _deprecated_tool(tmp_path, monkeypatch, tool, doc, stderr, code=0):
    import os
    import shlex

    from lib import collect

    bindir = tmp_path / "fakebin"
    bindir.mkdir(exist_ok=True)
    fake = bindir / tool
    fake.write_text(f"#!/bin/sh\nprintf '%s\\n' {shlex.quote(json.dumps(doc))}\nprintf '%s\\n' {shlex.quote(stderr)} >&2\nexit {code}\n")
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    step = next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == tool)
    result = collect._run_tool_step(step, tool, "core", "unreachable", None, tmp_path, RunLog(None), None, 10, None, inv={"cluster": {"server_version": "v1.32.0"}}, objects_dump=SAVED_KINDS)
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": {tool: result}}}))
    return result


def _deprecated_result(tmp_path):
    from lib import hygiene

    summary = hygiene._deprecated(hygiene._Ctx(tmp_path, {}))
    check = next(c for c in _all_checks() if c["id"] == "hygiene.deprecated-api")
    return summary, evaluate.evaluate_check(check, _ctx(tmp_path, {"hygiene": {"deprecated": summary}}), {})


@pytest.mark.parametrize(
    "tool,doc,stderr",
    [
        ("kubent", [], 'ERR Failed to initialize collector error="context unreachable does not exist"'),
        ("kubent", [], "INF Retrieved 0 resources from collector name=Cluster"),
        ("kubent", [], "INF Retrieved 10 resources from collector name=Helm v3"),
        ("kubent", [], "INF Retrieved 10 resources from collector name=Cluster\nERR Failed to initialize collector"),
    ],
)
def test_deprecated_tools_exit_zero_without_reading_skip(tmp_path, monkeypatch, tool, doc, stderr):
    result = _deprecated_tool(tmp_path, monkeypatch, tool, doc, stderr)
    assert result["ok"] is False and result["api_read"] is False
    assert "not confirmed read" in result["error"]
    summary, verdict = _deprecated_result(tmp_path)
    assert summary[f"{tool}_present"] is True  # A nonempty output file is not read evidence.
    assert summary["pluto_read"] is False and summary["kubent_read"] is False
    assert summary["items"] is None and summary["count"] is None
    assert verdict["status"] == "skip" and verdict["findings"] == []


@pytest.mark.parametrize(
    "tool,doc,stderr",
    [
        ("kubent", [], "INF Retrieved 12 resources from collector name=Cluster"),
        ("kubent", [], "\x1b[32mINF\x1b[0m Retrieved 12 resources from collector \x1b[36mname=\x1b[0mCluster"),
        ("pluto", {"target-versions": {"k8s": "v1.33.0"}}, ""),  # a clean run: Instance.Outputs is omitempty (pkg/api/output.go:58@v5.24.5)
    ],
)
def test_deprecated_tools_read_but_no_deprecations_pass(tmp_path, monkeypatch, tool, doc, stderr):
    result = _deprecated_tool(tmp_path, monkeypatch, tool, doc, stderr)
    assert result["ok"] is True and result["api_read"] is True
    summary, verdict = _deprecated_result(tmp_path)
    assert summary[f"{tool}_read"] is True
    assert summary["items"] == [] and summary["count"] == 0
    assert verdict["status"] == "done" and verdict["findings"] == []


KUBENT_DEBUG = "DBG Retrieving: deployments.v1.apps\nDBG Retrieving: podsecuritypolicies.v1beta1.policy\nDBG Failed to retrieve: policy/v1beta1, Resource=podsecuritypolicies: the server could not find the requested resource\nDBG Retrieving: ingresses.v1.networking.k8s.io\nINF Retrieved 0 resources from collector name=Cluster"


@pytest.mark.parametrize(
    "tool,doc,stderr,lists",
    [
        ("kubent", [], KUBENT_DEBUG, (2, 1)),  # three Lists started, one failed: read, although no object carried the annotation (a Helm or server-side-apply cluster)
        ("kubent", [], "\x1b[90m10:20PM\x1b[0m \x1b[33mDBG\x1b[0m Retrieving: deployments.v1.apps\nINF Retrieved 0 resources from collector name=Cluster", (1, 0)),  # coloured
        ("pluto", {"target-versions": {"k8s": "v1.33.0"}}, "", (111, 2)),  # pluto reads no List: the kinds objects.dump-all saved, and the two it could not
    ],
)
def test_deprecated_tools_successful_lists_are_read_evidence(tmp_path, monkeypatch, tool, doc, stderr, lists):
    """#132: `Retrieving` minus `Failed to retrieve` (kubent pkg/collector/cluster.go:121,124@0.7.3 at --log-level=debug) counts the Lists that succeeded. kubent's `Retrieved N` counts annotated objects only (cluster.go:129-130), so 0 after a full read is the normal case on a
    cluster managed by Helm or server-side apply, and until this change every full run of such a cluster had a failed kubent step."""
    result = _deprecated_tool(tmp_path, monkeypatch, tool, doc, stderr)
    assert result["ok"] is True and result["api_read"] is True
    assert (result["lists_ok"], result["lists_failed"]) == lists
    summary, verdict = _deprecated_result(tmp_path)
    assert summary[f"{tool}_read"] is True and (summary[f"{tool}_lists_ok"], summary[f"{tool}_lists_failed"]) == lists
    assert verdict["status"] == "done" and verdict["findings"] == []


def test_deprecated_tools_every_list_failed_is_not_a_read(tmp_path, monkeypatch):
    """Two Lists started, two failed (an unreachable server reports every List as failed in kubent; pluto prints nothing): no evidence, the step fails, the check skips."""
    result = _deprecated_tool(
        tmp_path,
        monkeypatch,
        "kubent",
        [],
        "DBG Retrieving: a.v1\nDBG Failed to retrieve: a: dial tcp: connection refused\nDBG Retrieving: b.v1\nDBG Failed to retrieve: b: dial tcp: connection refused\nINF Retrieved 0 resources from collector name=Cluster",
    )
    assert result["ok"] is False and (result["lists_ok"], result["lists_failed"]) == (0, 2)
    assert "not confirmed read" in result["error"] and "Failed to retrieve: b" in result["error"]
    summary, verdict = _deprecated_result(tmp_path)
    assert summary["kubent_read"] is False and summary["kubent_lists_ok"] == 0 and summary["kubent_lists_failed"] == 2 and verdict["status"] == "skip"


def test_a_failed_list_does_not_count_the_collector_level_failure_line(tmp_path, monkeypatch):
    """kubent's `Failed to retrieve data from collector` (cmd/kubent/main.go:45) is the collector failing, not one List; it still vetoes the read."""
    result = _deprecated_tool(tmp_path, monkeypatch, "kubent", [], "DBG Retrieving: a.v1\nERR Failed to retrieve data from collector name=Cluster")
    assert result["ok"] is False and (result["lists_ok"], result["lists_failed"]) == (1, 0) and result["api_read"] is False


def test_pluto_error_printed_to_stdout_reaches_the_step_error(tmp_path, monkeypatch):
    """pluto prints the error of `detect` with fmt.Println, to stdout, and exits 1 (cmd/root.go:413@v5.24.5); stderr has only klog's target-version lines (#132)."""
    import os
    import shlex

    from lib import collect

    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    fake = bindir / "pluto"
    fake.write_text(
        "#!/bin/sh\nprintf '%s\\n' "
        + shlex.quote("Error checking for versions: yaml: did not find expected node content")
        + "\nprintf '%s\\n' "
        + shlex.quote("I1104 root.go:259] assuming default targetVersion cert-manager v1.5.3")
        + " >&2\nexit 1\n"
    )
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    step = next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == "pluto")
    result = collect._run_tool_step(step, "pluto", "core", "x", None, tmp_path, RunLog(None), None, 10, None, inv={"cluster": {"server_version": "v1.32.0"}}, objects_dump=SAVED_KINDS)
    assert result["ok"] is False and result["api_read"] is False
    assert result["error"].startswith("Error checking for versions: yaml: did not find expected node content; I1104 root.go:259] assuming default targetVersion")


def test_kubent_step_asks_for_the_debug_log_level():
    step = next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == "kubent")
    assert "--log-level=debug" in step["cmd"]


@pytest.mark.parametrize("steps", [{}, {"kubent": {"ok": True}}, {"kubent": {"ok": False, "api_read": True}}, {"kubent": {"ok": False, "tool_missing": "kubent"}}])
def test_deprecated_output_without_confirmed_step_does_not_pass(tmp_path, steps):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/kubent.json").write_text("[]")
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": steps}}))
    summary, verdict = _deprecated_result(tmp_path)
    assert summary["kubent_read"] is False and verdict["status"] == "skip"


@pytest.mark.parametrize("tool", ["pluto", "kubent"])
def test_deprecated_read_failure_overrides_success_log(tmp_path, monkeypatch, tool):
    result = _deprecated_tool(tmp_path, monkeypatch, tool, [], "INF Retrieved 12 resources from collector name=Cluster\nNo annotations for ResourceVer apps/v1", code=1)
    assert result["ok"] is False and result["api_read"] is False
    assert _deprecated_result(tmp_path)[1]["status"] == "skip"


def test_deprecated_one_successful_tool_keeps_findings_and_ignores_failed_output(tmp_path, monkeypatch):
    doc = {"items": [{"name": "web", "namespace": "prod-a", "api": {"version": "networking.k8s.io/v1beta1", "kind": "Ingress"}, "deprecated": True, "removed": True}]}  # the shape of the pinned binary's output: the kind is inside api
    pluto = _deprecated_tool(tmp_path, monkeypatch, "pluto", doc, "")
    kubent = _deprecated_tool(tmp_path, monkeypatch, "kubent", [{"Name": "stale"}], "ERR Failed to initialize collector")
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"steps": {"pluto": pluto, "kubent": kubent}}}))
    summary, verdict = _deprecated_result(tmp_path)
    assert summary["count"] == 1 and summary["pluto_read"] and not summary["kubent_read"]
    assert verdict["status"] == "done" and verdict["counts"] == {"fail": 1}
    assert verdict["findings"][0]["target"] == "prod-a/ingress/web"


def test_pluto_step_keeps_exit_code_zero_when_it_finds_something():
    """pluto exits 2 (deprecated), 3 (removed) or 4 (no replacement) unless told not to (pkg/api/output.go:333-341@v5.24.5; cmd/root.go:353 and :167 exit with it).
    lib/shell.py writes the output file only on exit 0, so without the three flags tools/pluto.json was never written when pluto found something and
    the check passed with no pluto rows; with the read evidence of this branch it would skip instead. The flags do not filter the items (FilterOutput, pkg/api/output.go:159-181). Observed with the pinned binary:
    detect on a networking.k8s.io/v1beta1 Ingress exits 3 without the flags and 0 with them, with the same item in both JSONs."""
    step = next(s for s in yamlite.load_file(ROOT / "collectors/core/collect.yaml") if s.get("id") == "pluto")
    assert {"--ignore-deprecations", "--ignore-removals", "--ignore-unavailable-replacements"} <= set(step["cmd"])


def test_pluto_findings_with_exit_three_would_be_dropped(tmp_path, monkeypatch):
    """What the flags prevent: a pluto that prints one removed item and exits 3 is a failed step whose output is never saved (lib/shell.py), its read
    evidence is not computed, and the summary carries no items. The test documents the failure mode the flags exist for; it is not a behaviour to keep."""
    doc = {"items": [{"name": "web", "namespace": "prod-a", "api": {"version": "networking.k8s.io/v1beta1", "kind": "Ingress"}, "deprecated": True, "removed": True}]}
    result = _deprecated_tool(tmp_path, monkeypatch, "pluto", doc, "", code=3)
    assert result["ok"] is False and result["api_read"] is False
    summary, verdict = _deprecated_result(tmp_path)
    assert summary["pluto_read"] is False and summary["items"] is None and verdict["status"] == "skip"

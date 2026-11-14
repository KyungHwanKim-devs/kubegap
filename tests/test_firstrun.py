"""First-run questions: one per missing thing, each with choices and a way to skip, remembered per context.

The setup dicts below are cut from real `setup.json` files of an EKS cluster and a k3s cluster (names changed); no key is invented.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

from lib.collection import discover, kube
from lib.commands import firstrun
from lib.foundations.config import Config as _Config
from lib.foundations.runlog import RunLog

ROOT = Path(__file__).resolve().parent.parent


def Config(data=None):
    """A config with the scale already decided: every test below is about one of the other questions, and the scale question would head
    each list. The scale question has its own test, which uses the bare config."""
    return _Config({"scale": "medium", **(data or {})})


def _tool(name, present=True, required=False, checks=None):
    return {
        "name": name,
        "role": f"role of {name}",
        "required": required,
        "present": present,
        "path": f"/usr/bin/{name}" if present else None,
        "version": "1.0" if present else None,
        "checks": checks or [f"{name}.check"],
        "installable": True,
        "note": "",
    }


def _store(kind, ok=True):
    return {"kind": kind, "ok": True, "version": "1.0", "access": "port-forward", "service": {"namespace": "monitoring", "name": kind, "port": 80}} if ok else {"kind": kind, "ok": False, "access": None, "error": "service not found"}


def _setup(platform="eks", *, doc=None, stores_ok=True, tools=None, nodes=9):
    eks = platform == "eks"
    return {
        "tools": tools or [_tool("kubectl", required=True), _tool("krr"), _tool("pluto")],
        "cluster": {
            "context": "c",
            "is_eks": eks,
            "eks": {"region": "ap-northeast-2", "account": "111122223333", "name": "demo", "profile": "demo"} if eks else None,
            "reachable": True,
            "node_count": nodes,
            "can_list_pods": True,
            "platform": platform,
        },
        "monitoring": {k: _store(k, stores_ok or k != "loki") for k in firstrun.STORES},
        "aws": {"ssm_document": doc or {"present": True, "current": True, "version": "5", "error": None}} if eks else None,
        "ready": True,
    }


def _ids(setup, cfg=None, ctx_dir=None, **kw):
    return [q["id"] for q in firstrun.questions(setup, cfg or Config(), ctx_dir, **kw)]


def test_nothing_missing_asks_nothing():
    assert _ids(_setup("eks"), Config({"grafana_api_token": "x"})) == []


def test_unreachable_cluster_asks_nothing():
    s = _setup("k3s")
    s["cluster"]["reachable"] = False
    assert _ids(s) == []


def test_eks_document_missing_or_outdated_is_asked_unless_policy_decides():
    missing = {"present": False, "current": False, "error": None}
    outdated = {"present": True, "current": False, "version": "4", "error": None}
    unreadable = {"present": None, "current": False, "error": "AccessDenied"}
    token = {"grafana_api_token": "x"}
    assert _ids(_setup("eks", doc=missing), Config(token)) == ["ssm-document"]
    assert _ids(_setup("eks", doc=outdated), Config(token)) == ["ssm-document"]
    assert _ids(_setup("eks", doc=unreadable), Config(token)) == []
    for decided in ({"ssm_document": "never"}, {"ssm_document": "always"}, {"node_access": "none"}):
        assert _ids(_setup("eks", doc=missing), Config({**token, **decided})) == []


def test_k3s_ssh_question_then_follow_up_from_the_probe(tmp_path):
    s, token = _setup("k3s", nodes=2), Config({"grafana_api_token": "x"})
    q = firstrun.questions(s, token, tmp_path)[0]
    assert q["id"] == "node-ssh" and [o["id"] for o in q["options"]] == ["check", "skip"]
    assert q["options"][0]["run"] == ["nodes"] and not q["options"][0]["remember"]
    # the user already wrote how to reach the nodes
    assert _ids(s, Config({"grafana_api_token": "x", "ssh": {"user": "u"}}), tmp_path) == []
    # probe saved by `kubegap nodes`: one node unreachable, one with an unknown host key
    probe = {"a": {"ok": False, "host": "192.168.0.1", "kind": "unreachable", "why": "timed out"}, "b": {"ok": False, "host": "192.168.0.2", "kind": "host-key", "why": "Host key verification failed"}}
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "probe": probe}))
    q = firstrun.questions(s, token, tmp_path)[0]
    assert [o["id"] for o in q["options"]] == ["accept-keys", "skip"]  # no node answered: nothing to go on with
    accept = q["options"][0]
    assert accept["config"] == ["ssh.accept_new_hosts", "true"] and accept["run"] == ["nodes"] and "config file" in accept["description"]
    assert "192.168.0.1" in q["explain"] and "ssh.hosts.<node>" in q["typed"]
    # one node answers: the user can go on with it, and that choice keeps SSH on
    probe["c"] = {"ok": True, "host": "192.168.0.3", "kind": None, "why": None}
    probe["b"]["kind"] = "auth"
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "probe": probe}))
    q = firstrun.questions(s, token, tmp_path)[0]
    assert [o["id"] for o in q["options"]] == ["check", "partial", "skip"] and "a, b" in q["options"][1]["description"]
    # a probe of another backend says nothing about SSH
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssm", "probe": probe}))
    assert [o["id"] for o in firstrun.questions(s, token, tmp_path)[0]["options"]] == ["check", "skip"]
    # every node answers: nothing left to ask
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "probe": {"a": {"ok": True}, "b": {"ok": True}}}))
    assert _ids(s, token, tmp_path) == []
    # asking again still offers the choice, so SSH can be turned off later
    assert [o["id"] for o in firstrun.questions(s, token, tmp_path, all_=True)[0]["options"]] == ["check", "skip"]


def test_skip_is_remembered_and_asked_again_on_request(tmp_path):
    s, token = _setup("k3s"), Config({"grafana_api_token": "x"})
    firstrun.record_answer(tmp_path, "node-ssh", "skip")
    assert _ids(s, token, tmp_path) == []
    assert _ids(s, token, tmp_path, all_=True) == ["node-ssh"]
    assert [x["id"] for x in firstrun.skipped(s, token, tmp_path)] == ["node-ssh"]
    assert firstrun.forget_answers(tmp_path, ["node-ssh"]) == ["node-ssh"]
    assert _ids(s, token, tmp_path) == ["node-ssh"]


def test_no_ssh_connection_before_the_user_decided(tmp_path):
    """Collection reads nodes over SSH only after a decision: nothing is contacted because of a question nobody answered."""
    nodes = {"count": 1, "nodes": [{"name": "a", "internal_ip": "10.0.0.1", "provider_id": None}]}

    def method(cfg=None, **kw):
        na = discover._node_access("k3s", nodes, cfg or Config(), None, RunLog(None), **kw)
        return na["method"], na["reasons"][0] if na["reasons"] else ""

    assert firstrun.ssh_decision(tmp_path, Config()) == "open"
    m, why = method(ssh_state="open")
    assert m == "none" and "/kubegap setup" in why and "node_access: ssh" in why
    # the three ways to decide yes
    assert firstrun.ssh_decision(tmp_path, Config({"ssh": {"user": "u"}})) == "yes"
    assert firstrun.ssh_decision(tmp_path, Config({"node_access": "ssh"})) == "yes"
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "nodes": {}}))  # the file `kubegap nodes` wrote before probes were saved
    assert firstrun.ssh_decision(tmp_path, Config()) == "yes" and method(ssh_state="yes")[0] == "ssh"
    # skip wins over an earlier probe; config.yaml wins over skip
    firstrun.record_answer(tmp_path, "node-ssh", "skip")
    assert firstrun.ssh_decision(tmp_path, Config()) == "skipped"
    m, why = method(ssh_state="skipped")
    assert m == "none" and "skipped" in why
    assert method(Config({"node_access": "ssh"}), ssh_state="skipped")[0] == "ssh"
    # "check now" after a skip forgets the skip (the then: line of that option), and going on with the nodes that answer keeps SSH on
    firstrun.forget_answers(tmp_path, ["node-ssh"])
    assert firstrun.ssh_decision(tmp_path, Config()) == "yes"
    (tmp_path / firstrun.NODE_ACCESS_FILE).unlink()
    firstrun.record_answer(tmp_path, "node-ssh", firstrun.PARTIAL)
    assert firstrun.ssh_decision(tmp_path, Config()) == "yes"
    # EKS and GKE are not touched by the SSH decision
    assert discover._node_access("gke", nodes, Config({"node_access": "none"}), None, RunLog(None), ssh_state="open")["method"] == "none"


def test_discovery_receives_the_ssh_decision_from_the_command():
    """Discovery is a collection module and does not read first-run answers (#149): the command computes `firstrun.ssh_decision` for the context folder
    and passes it, and `discover()` has no default for it, so no caller can contact a node by leaving the decision out."""
    import inspect

    assert inspect.signature(discover.discover).parameters["ssh_state"].default is inspect.Parameter.empty
    cli = (Path(__file__).resolve().parent.parent / "scripts" / "kubegap").read_text(encoding="utf-8")
    assert cli.count("_discover.discover(") == 2 and cli.count("ssh_state=_firstrun.ssh_decision(snap.parent, cfg)") == 2
    assert inspect.signature(discover._node_access).parameters["ssh_state"].default == "yes"  # `kubegap nodes` is itself the decision


def test_a_platform_without_node_access_gets_no_node_question():
    token = Config({"grafana_api_token": "x"})
    assert _ids(_setup("gke"), token) == []
    assert _ids(_setup("k3s"), token) == ["node-ssh"]


def test_a_store_that_was_found_but_did_not_answer_is_not_called_absent():
    s = _setup("eks")
    s["monitoring"]["loki"] = {"kind": "loki", "ok": False, "access": "port-forward", "error": "port-forward failed", "service": {"namespace": "monitoring", "name": "loki", "port": 3100}}
    assert _ids(s, Config({"grafana_api_token": "x"})) == []
    s["monitoring"]["loki"] = _store("loki", ok=False)
    assert _ids(s, Config({"grafana_api_token": "x"})) == ["stores"]
    s["monitoring"]["error"] = "services is forbidden"
    assert _ids(s, Config({"grafana_api_token": "x"})) == []


def test_tools_question_and_a_newly_missing_tool_reopens_it(tmp_path):
    tools = [_tool("kubectl", required=True), _tool("krr", present=False), _tool("pluto")]
    s, token = _setup("eks", tools=tools), Config({"grafana_api_token": "x"})
    q = firstrun.questions(s, token, tmp_path)[0]
    assert q["id"] == "tools" and q["state"] == {"missing": ["krr"]} and q["options"][0]["run"] == ["setup", "--install-only", "krr"]
    firstrun.record_answer(tmp_path, "tools", "skip", q["state"])
    assert _ids(s, token, tmp_path) == []
    tools[2] = _tool("pluto", present=False)
    assert _ids(s, token, tmp_path) == ["tools"]
    for policy in ("never", "always"):
        assert _ids(s, Config({"grafana_api_token": "x", "install_tools": policy}), tmp_path / "x") == []


def test_tools_of_another_platform_are_not_offered():
    tools = [_tool("kubectl", required=True), _tool("aws", present=False), _tool("ssh", present=False)]
    token = Config({"grafana_api_token": "x", "node_access": "none"})
    k3s, eks = firstrun.questions(_setup("k3s", tools=tools), token, None)[0], firstrun.questions(_setup("eks", tools=tools), token, None)[0]
    assert k3s["state"] == {"missing": ["ssh"]} and eks["state"] == {"missing": ["aws"]}
    # "Install all" installs what the question names and nothing else
    assert k3s["options"][0]["run"] == ["setup", "--install-only", "ssh"] and eks["options"][0]["run"] == ["setup", "--install-only", "aws"]


def test_stores_and_grafana():
    assert _ids(_setup("eks", stores_ok=False)) == ["grafana-token", "stores"]
    assert _ids(_setup("eks", stores_ok=False), Config({"loki_url": "http://loki:3100"})) == ["grafana-token"]


def _all_questions(tmp_path, language="en"):
    probe = {"a": {"ok": False, "host": "h", "kind": "host-key", "why": "x"}, "b": {"ok": True, "host": "i"}}
    (tmp_path / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "probe": probe}))
    tools = [_tool("krr", present=False)]
    out = []
    eks = _setup("eks", doc={"present": False, "current": False}, stores_ok=False, tools=tools)
    eks["machine"] = {"open_dirs": [{"path": "/home/u/.kubegap", "mode": "0755"}]}
    out += firstrun.questions(eks, _Config(), None, language=language)
    out += firstrun.questions(_setup("k3s"), Config(), None, language=language)
    out += firstrun.questions(_setup("k3s"), Config(), tmp_path, language=language)
    out += firstrun.questions(_setup("aks"), Config(), None, language=language)
    probe_rest = {"a": {"ok": False, "host": "h", "kind": "other", "why": "x"}, "b": {"ok": True, "host": "i"}}
    (tmp_path / "rest").mkdir(exist_ok=True)
    (tmp_path / "rest" / firstrun.NODE_ACCESS_FILE).write_text(json.dumps({"method": "ssh", "probe": probe_rest}))
    out += firstrun.questions(_setup("k3s"), Config({"ssh": {"accept_new_hosts": True}}), tmp_path / "rest", language=language)
    return out


def test_every_question_fits_both_choice_windows_and_can_be_skipped(tmp_path):
    qs = _all_questions(tmp_path)
    assert {q["id"] for q in qs} == {"scale", "home-mode", "tools", "ssm-document", "node-ssh", "grafana-token", "stores"}
    assert {q["id"] for q in _all_questions(tmp_path, "ko")} == {q["id"] for q in qs}, "the Korean block asks the same questions"
    for q in qs:
        assert 2 <= len(q["options"]) <= 3, q["id"]  # Codex request_user_input: 2-3 options
        assert len(q["header"]) <= 12, q["header"]  # both hosts: header of 12 characters or fewer
        assert q["question"] and q["explain"] and q["gain"]
        ids = [o["id"] for o in q["options"]]
        assert len(set(ids)) == len(ids)
        # one option always leaves things as they are and runs nothing
        assert any(not o["run"] and not o["show"] and not o["config"] for o in q["options"]), q["id"]
        for o in q["options"]:
            assert len(o["label"].split()) <= 5 and o["description"]


def test_render_names_every_option_with_its_command(tmp_path):
    qs = _all_questions(tmp_path)
    text = firstrun.render(qs, "ctx")
    assert text.startswith(f"== questions for the user ({len(qs)})")
    for q in qs:
        assert f"[{q['id']}]" in text
        for o in q["options"]:
            assert f"option {o['id']}: {o['label']}" in text
    assert "kubegap nodes --context ctx" in text and "answer --context ctx node-ssh skip" in text
    # an option that acts forgets an earlier remembered answer instead of recording one
    assert "      run:  $KUBEGAP/scripts/kubegap nodes --context ctx\n      then: $KUBEGAP/scripts/kubegap answer --context ctx node-ssh --forget" in text
    assert "      config: ssh.accept_new_hosts true   (dry run" in text
    assert "      show: " in text and "  typed answer: " in text
    assert text.count("      then: ") == sum(len(q["options"]) for q in qs)
    assert "none" in firstrun.render([], "ctx")
    tail = firstrun.render([], "ctx", [{"id": "node-ssh", "header": "Node checks", "gain": ["g"]}]).splitlines()[-2:]
    assert tail[0] == "skipped earlier [node-ssh] Node checks: g" and "Limits of this run" in tail[1]


def test_node_check_count_is_the_catalog_s_and_is_worded_as_an_upper_bound():
    full_only_node = [c for c in firstrun._checks() if c["id"].startswith("node.") and c.get("modes") == ["full"]]
    assert firstrun.node_script_checks() == len(full_only_node) > 0
    # some of them run on one platform only, which is why every text says "up to"
    assert any(c.get("platforms") for c in full_only_node)
    q = firstrun.questions(_setup("k3s"), Config({"grafana_api_token": "x"}), None)[0]
    assert q["gain"][0].startswith(f"up to {len(full_only_node)} node checks in a full run")


# ---------- the commands ----------


def _cli():
    loader = importlib.machinery.SourceFileLoader("kubegap_cli", str(ROOT / "scripts" / "kubegap"))
    spec = importlib.util.spec_from_loader("kubegap_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_answer_and_questions_commands(tmp_path, capsys):
    cli = _cli()
    ctx_dir = tmp_path / "c"
    ctx_dir.mkdir()
    (ctx_dir / "setup.json").write_text(json.dumps(_setup("k3s")))
    (tmp_path / "config.yaml").write_text("scale: medium\n")  # decided, so the list starts at the node question
    base = ["--context", "c", "--snapshots-root", str(tmp_path), "--config", str(tmp_path / "config.yaml")]
    assert cli.main(["questions", *base]) == 0
    assert "[node-ssh]" in capsys.readouterr().out
    assert cli.main(["answer", *base, "node-ssh", "nope"]) == 1
    assert cli.main(["answer", *base, "no-such", "skip"]) == 1
    assert cli.main(["answer", *base, "node-ssh", "skip"]) == 0
    capsys.readouterr()
    assert cli.main(["questions", *base]) == 0
    out = capsys.readouterr().out
    assert "\n[node-ssh]" not in out and "skipped earlier [node-ssh]" in out and "grafana-token" in out
    assert cli.main(["answer", *base, "grafana-token", "skip"]) == 0
    assert cli.main(["answer", *base, "node-ssh", "--forget"]) == 0
    assert set(firstrun.load_answers(ctx_dir)) == {"grafana-token"}
    assert cli.main(["answer", *base, "--forget"]) == 0 and firstrun.load_answers(ctx_dir) == {}
    capsys.readouterr()
    assert cli.main(["questions", *base, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["id"] == "node-ssh"


def test_questions_without_a_setup_result_says_what_to_run(tmp_path, capsys):
    base = ["--context", "c", "--snapshots-root", str(tmp_path), "--config", str(tmp_path / "config.yaml")]
    assert _cli().main(["questions", *base]) == 1
    assert "kubegap setup --context c" in capsys.readouterr().err
    assert _cli().main(["answer", *base, "node-ssh", "--forget"]) == 0  # forgetting needs no setup result


def test_config_set_command(tmp_path, capsys):
    cli, cfg = _cli(), tmp_path / "config.yaml"
    assert cli.main(["config", "--config", str(cfg), "set", "ssh.hosts.a", "10.0.0.1", "--dry-run"]) == 0
    assert "nothing was written" in capsys.readouterr().out and not cfg.exists()
    assert cli.main(["config", "--config", str(cfg), "set", "ssh.hosts.a", "10.0.0.1"]) == 0
    assert "a: 10.0.0.1" in cfg.read_text()
    assert cli.main(["config", "--config", str(cfg), "set", "grafana_api_token", "x"]) == 1


def test_iam_policy_is_filled_from_the_context(monkeypatch, capsys):
    cli = _cli()
    monkeypatch.setattr(kube, "context_info", lambda ctx, kubeconfig=None: {"is_eks": True, "eks": {"account": "111122223333", "name": "demo", "region": "eu-west-1"}})
    assert cli.main(["iam-policy", "--context", "c"]) == 0
    out = capsys.readouterr().out
    policy = json.loads(out)
    assert "<" not in out and "111122223333:document/kubegap-node-read" in out and "kubernetes.io/cluster/demo" in out
    assert len(policy["Statement"]) == 3
    assert cli.main(["iam-policy", "--context", "c", "--without-node-access"]) == 0
    less = json.loads(capsys.readouterr().out)
    assert [s["Sid"] for s in less["Statement"]] == ["KubegapReadOnly"]
    monkeypatch.setattr(kube, "context_info", lambda ctx, kubeconfig=None: {"is_eks": False, "eks": None})
    assert cli.main(["iam-policy", "--context", "c"]) == 1


def test_nodes_reads_the_node_list_from_the_cluster_without_a_snapshot(tmp_path, monkeypatch, capsys):
    """`kubegap nodes` before the first collection: README told first-time users to run it and it failed with "no snapshots"."""
    cli = _cli()
    node = {"metadata": {"name": "a", "labels": {}}, "spec": {}, "status": {"nodeInfo": {"kubeletVersion": "v1.33.5+k3s1"}, "addresses": [{"type": "InternalIP", "address": "10.0.0.1"}], "conditions": [{"type": "Ready", "status": "True"}]}}
    monkeypatch.setattr(kube, "context_info", lambda ctx, kubeconfig=None: {"context": ctx, "server": "https://10.0.0.1:6443", "is_eks": False, "eks": None})

    class R:
        ok, error, stderr, stdout = True, None, "", ""

    monkeypatch.setattr(kube, "kubectl_json", lambda args, **kw: ({"items": [node] if args[:2] == ["get", "nodes"] else []}, R()))
    from lib.collection import node as node_mod
    from lib.collection.node import NodeResult

    sent = []

    def fake_ssh(self, name, cmd, timeout):
        sent.append(name)
        return NodeResult(name, "ssh", False, error="ssh: connect to host 10.0.0.1 port 22: Operation timed out → hint", detail={"host": "10.0.0.1", "kind": "unreachable"})

    monkeypatch.setattr(node_mod.NodeAccess, "_ssh", fake_ssh)
    base = ["--context", "c", "--snapshots-root", str(tmp_path), "--config", str(tmp_path / "config.yaml")]
    assert cli.main(["nodes", *base]) == 1
    out = capsys.readouterr().out
    assert "1 nodes read from the cluster now, backend ssh" in out and "reachable 0/1" in out and sent == ["a"]
    saved = json.loads((tmp_path / "c" / firstrun.NODE_ACCESS_FILE).read_text())
    assert saved["probe"]["a"] == {"ok": False, "host": "10.0.0.1", "kind": "unreachable", "why": "ssh: connect to host 10.0.0.1 port 22: Operation timed out"}


@pytest.mark.parametrize("err,kind", [("Host key verification failed.", "host-key"), ("Permission denied (publickey).", "auth"), ("ssh: connect to host x port 22: Operation timed out", "unreachable"), ("exit 255", "other")])
def test_ssh_failures_are_classified(monkeypatch, err, kind):
    from lib.collection import node as node_mod
    from lib.foundations import shell

    class R:
        ok, error, stderr, stdout, code, seconds = False, None, err, "", 255, 0.1

    monkeypatch.setattr(shell, "run", lambda argv, timeout=0: R())
    na = node_mod.NodeAccess({"node_access": {"method": "ssh"}, "nodes": {"nodes": [{"name": "a", "internal_ip": "10.0.0.1"}]}}, Config())
    assert na.run_on_node("a", "true").detail["kind"] == kind


def test_readme_numbers_and_question_names_match_the_code():
    """The README tells a first-time reader how many checks reading the nodes adds; the number is the catalog's."""
    n = firstrun.node_script_checks()
    en, ko = (ROOT / "README.md").read_text(encoding="utf-8"), (ROOT / "README.ko.md").read_text(encoding="utf-8")
    node_area = sum(1 for c in firstrun._checks() if c["area"] == "node")
    assert f"That is up to {n} more checks in a full audit" in en and "409 of the 411" in en and f"Of the {node_area} Node OS checks, {n} can be seen only by reaching the nodes" in en
    assert f"full 점검의 항목이 최대 {n}개 늘고" in ko and f"노드 OS {node_area}개 중 {n}개는 노드에 들어가야 볼 수 있습니다" in ko
    # the names the README gives for `focus` are the catalog's area names, and the counts next to them are the catalog's
    import collections

    for area, count in collections.Counter(c["area"] for c in firstrun._checks()).items():
        assert f"| `{area}` | {count} |" in en and f"| `{area}` | {count} |" in ko, area
    setup_doc = (ROOT / "docs" / "SETUP.md").read_text(encoding="utf-8")
    assert f"the {n} `node.*` checks" in setup_doc
    first_run = (ROOT / "references" / "first-run.md").read_text(encoding="utf-8")
    for qid in ("scale", "tools", "ssm-document", "node-ssh", "grafana-token", "stores"):
        assert f"| `{qid}` |" in setup_doc and f"| `{qid}` |" in first_run, qid


def test_setup_doc_names_every_key_config_set_writes():
    from lib.commands import configedit

    setup_doc = (ROOT / "docs" / "SETUP.md").read_text(encoding="utf-8")
    line = next(ln for ln in setup_doc.splitlines() if ln.startswith("It keeps your comments"))
    for key in configedit.SETTABLE:
        assert f"`{key}`" in line or (key.endswith("_url") and "the four `<store>_url` keys" in line), key
    assert "`ssh.hosts.<node>`" in line


def test_scale_is_asked_first_once_per_cluster_and_config_overrides_the_answer(tmp_path):
    from lib.foundations import rubric

    s = _setup("k3s", nodes=2)
    q = firstrun.questions(s, _Config({"grafana_api_token": "x", "node_access": "none"}), tmp_path)[0]
    assert q["id"] == "scale" and [o["id"] for o in q["options"]] == ["small", "medium", "large"]
    assert all(o["remember"] and not o["run"] and not o["config"] for o in q["options"])
    assert firstrun.scale_decision(tmp_path) is None
    assert rubric.resolve_scale({}, firstrun.scale_decision(tmp_path), 2) == {"name": "small", "source": "guessed", "nodes": 2}
    assert rubric.resolve_scale({}, None, 9)["name"] == "medium" and rubric.resolve_scale({}, None, 21)["name"] == "large"
    firstrun.record_answer(tmp_path, "scale", "large")
    assert firstrun.scale_decision(tmp_path) == "large"
    assert rubric.resolve_scale({}, firstrun.scale_decision(tmp_path), 2) == {"name": "large", "source": "answered"}
    assert rubric.resolve_scale({"scale": "medium"}, "large", 2) == {"name": "medium", "source": "config.yaml"}
    assert "scale" not in _ids(s, _Config({"scale": "small"}), tmp_path / "other") and "scale" not in _ids(s, _Config(), tmp_path)


def test_home_mode_question_comes_first_and_fix_runs_protect_home():
    s = _setup("k3s")
    s["machine"] = {"open_dirs": [{"path": "/home/u/.kubegap", "mode": "0755"}, {"path": "/home/u/.kubegap/snapshots", "mode": "0755"}]}
    qs = firstrun.questions(s, Config(), None)
    assert qs[0]["id"] == "home-mode"
    assert "/home/u/.kubegap" in qs[0]["question"] and "0755" in qs[0]["question"]
    fix, leave = qs[0]["options"]
    assert fix["run"] == ["protect-home"] and fix["remember"] is False and "2 folders" in fix["description"]
    assert leave["remember"] is True
    assert "home-mode" not in _ids(_setup("k3s"))


_TRANSLATIONESE = ("에 대해", "를 통해", "에 있어", "되어지", "에 의해", "가지고 있", "수행", "실시")


def test_every_question_is_written_in_korean_not_translated(tmp_path):
    """The Korean texts are written from the question's purpose (#173). Every English text has a Korean twin that differs, is not English, and
    carries none of the translation patterns the writing guides are checked against. ids, commands and paths stay the same."""
    en = {q["id"]: q for q in _all_questions(tmp_path, "en")}
    ko = {q["id"]: q for q in _all_questions(tmp_path, "ko")}
    assert set(en) == set(ko)
    for qid, q in ko.items():
        texts = [q["header"], q["question"], q["explain"], *q["gain"], q.get("typed") or ""] + [t for o in q["options"] for t in (o["label"], o["description"], *(o["show"] or []))]
        for t in texts:
            for pat in _TRANSLATIONESE:
                assert pat not in t, (qid, pat, t)
        assert any("\uac00" <= ch <= "\ud7a3" for ch in q["question"]), (qid, q["question"])
        assert q["question"] != en[qid]["question"] and q["explain"] != en[qid]["explain"]
        assert [o["id"] for o in q["options"]] == [o["id"] for o in en[qid]["options"]]
        assert [o["run"] for o in q["options"]] == [o["run"] for o in en[qid]["options"]]
        assert len(q["header"]) <= 12 and all(len(o["label"]) <= 12 for o in q["options"]), qid
    text = firstrun.render(list(ko.values()), "ctx", [{"id": "node-ssh", "header": "노드 점검", "gain": ["g"]}], ["loki: 묻지 않았습니다"], language="ko")
    assert "  question: " in text and "  option skip: 건너뛰기 — " in text and "answer --context ctx node-ssh skip" in text
    assert "skipped earlier [node-ssh] 노드 점검: g" in text and "note loki: 묻지 않았습니다" in text and "이번 점검의 한계" in text
    assert "none:" in firstrun.render([], "ctx", language="ko")


def test_grafana_token_is_asked_only_for_dashboards_that_are_not_in_configmaps():
    """Helm puts dashboards and datasources into ConfigMaps, which are read without a token. The question comes only when Grafana counts more
    dashboards than the ConfigMaps hold, with the numbers, or when nothing is provisioned that way."""
    s = _setup("eks")
    assert [q["id"] for q in firstrun.questions(s, Config(), None) if q["id"] == "grafana-token"] == ["grafana-token"], "nothing provisioned: asked as before"
    s["monitoring"]["grafana"]["provisioned"] = {"dashboards": 25, "datasources": 1, "total_dashboards": 25, "error": None}
    assert "grafana-token" not in [q["id"] for q in firstrun.questions(s, Config(), None)]
    assert firstrun.noted(s, Config(), None) == ["grafana: no token needed; 25 dashboards and 1 datasources are read from ConfigMaps. Grafana counts 25 dashboards too, so none is missing"]
    assert firstrun.noted(s, Config(), None, language="ko") == ["grafana: 토큰 없이 ConfigMap에서 대시보드 25개와 데이터소스 1개를 읽습니다. Grafana가 세는 대시보드도 25개라 빠진 게 없습니다"]
    s["monitoring"]["grafana"]["provisioned"]["total_dashboards"] = None
    assert "grafana-token" not in [q["id"] for q in firstrun.questions(s, Config(), None)]
    assert "could not be read" in firstrun.noted(s, Config(), None)[0]
    s["monitoring"]["grafana"]["provisioned"]["total_dashboards"] = 30
    q = next(q for q in firstrun.questions(s, Config(), None) if q["id"] == "grafana-token")
    assert "Grafana has 30 dashboards and 25 of them" in q["question"] and "The other 5" in q["question"] and [o["id"] for o in q["options"]] == ["show", "skip"]
    assert "5 dashboards made in Grafana" in q["options"][1]["description"]
    assert firstrun.noted(s, Config(), None) == []
    kq = next(q for q in firstrun.questions(s, Config(), None, language="ko") if q["id"] == "grafana-token")
    assert "대시보드가 30개 있는데" in kq["question"] and "나머지 5개" in kq["question"]
    assert firstrun.noted(s, Config({"grafana_api_token": "t"}), None) == []

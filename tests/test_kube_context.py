"""context_info keeps only the exec env values kubegap reads and setup says how the context authenticates (#90)."""

import json

from lib import kube, shell


def _fake_config(user: dict, cluster_name: str = "arn:aws:eks:ap-northeast-2:123456789012:cluster/c1"):
    doc = {"clusters": [{"name": cluster_name, "cluster": {"server": "https://x.eks.amazonaws.com"}}], "users": [{"name": "u", "user": user}]}

    def fake(args, *, context=None, timeout=60, **kw):
        assert args[:2] == ["config", "view"]
        return doc, shell.Result(cmd=["kubectl"], code=0, stdout=json.dumps(doc))

    return fake


def test_exec_env_values_are_redacted_except_aws_profile_and_region(monkeypatch):
    user = {
        "exec": {
            "command": "aws",
            "args": ["eks", "get-token", "--cluster-name", "c1"],
            "env": [{"name": "AWS_PROFILE", "value": "p"}, {"name": "AWS_REGION", "value": "ap-northeast-2"}, {"name": "SECRET_X", "value": "abc"}, {"name": "TENANT", "value": "t-42"}],
        }
    }
    monkeypatch.setattr(kube, "kubectl_json", _fake_config(user))
    info = kube.context_info("ctx")
    assert info["auth"]["env"] == {"AWS_PROFILE": "p", "AWS_REGION": "ap-northeast-2", "SECRET_X": "<redacted>", "TENANT": "<redacted>"}
    dumped = json.dumps(info)
    assert "abc" not in dumped and "t-42" not in dumped
    assert info["auth"]["command"] == "aws" and info["auth"]["args"] == ["eks", "get-token", "--cluster-name", "c1"]
    assert info["is_eks"] and info["eks"]["profile"] == "p" and info["eks"]["name"] == "c1"


def test_env_entries_without_name_or_value(monkeypatch):
    user = {"exec": {"command": "aws", "args": ["eks", "get-token"], "env": [{"value": "orphan"}, {"name": "ONLY_NAME"}, {"name": "AWS_PROFILE"}, "not-a-dict"]}}
    monkeypatch.setattr(kube, "kubectl_json", _fake_config(user))
    info = kube.context_info("ctx")
    assert info["auth"]["env"] == {"ONLY_NAME": None, "AWS_PROFILE": None}
    assert "orphan" not in json.dumps(info)
    assert kube.auth_summary(info) == "exec aws eks get-token, env AWS_PROFILE, ONLY_NAME"


def test_aws_region_from_exec_env_is_read_when_the_cluster_name_is_not_an_arn(monkeypatch):
    user = {"exec": {"command": "aws", "args": ["eks", "get-token", "--cluster-name", "c1"], "env": [{"name": "AWS_REGION", "value": "eu-west-1"}]}}
    monkeypatch.setattr(kube, "kubectl_json", _fake_config(user, cluster_name="my-eks"))
    info = kube.context_info("ctx")
    assert info["is_eks"] and info["eks"]["region"] == "eu-west-1" and info["eks"]["name"] == "c1"


def test_auth_summary_lines(monkeypatch):
    user = {"exec": {"command": "aws", "args": ["eks", "get-token", "--cluster-name", "c1"], "env": [{"name": "AWS_PROFILE", "value": "p"}, {"name": "SECRET_X", "value": "abc"}]}}
    monkeypatch.setattr(kube, "kubectl_json", _fake_config(user))
    line = kube.auth_summary(kube.context_info("ctx"))
    assert line == "exec aws eks get-token --cluster-name c1, env AWS_PROFILE, SECRET_X"
    assert "abc" not in line
    with_region = {"auth": {"type": "exec", "command": "aws", "args": ["--region", "ap-northeast-2", "eks", "get-token", "--cluster-name", "c1", "--output=json"], "env": {"AWS_PROFILE": "p"}}}
    assert kube.auth_summary(with_region) == "exec aws --region ap-northeast-2 eks get-token --cluster-name c1 --output=json, env AWS_PROFILE"
    assert kube.auth_summary({"auth": {"type": "exec", "command": "gke-gcloud-auth-plugin", "args": [], "env": {}}}) == "exec gke-gcloud-auth-plugin, env none"
    assert kube.auth_summary({"auth": {"type": "exec", "command": None, "args": ["--flag"], "env": None}}) == "exec ? --flag, env none"
    long = kube.auth_summary({"auth": {"type": "exec", "command": "x", "args": ["a" * 100], "env": {}}})
    assert long.startswith("exec x aaaa") and "..." in long and len(long) < 100
    monkeypatch.setattr(kube, "kubectl_json", _fake_config({"client-certificate-data": "..."}))
    assert kube.auth_summary(kube.context_info("ctx")) == "client certificate"
    monkeypatch.setattr(kube, "kubectl_json", _fake_config({"token": "t"}))
    assert kube.auth_summary(kube.context_info("ctx")) == "token"
    monkeypatch.setattr(kube, "kubectl_json", _fake_config({}))
    assert kube.auth_summary(kube.context_info("ctx")).startswith("unknown")


def test_setup_prints_the_auth_line_and_writes_no_exec_value(tmp_path, monkeypatch):
    from lib import setup as _setup
    from lib.config import Config

    user = {"exec": {"command": "aws", "args": ["eks", "get-token"], "env": [{"name": "AWS_PROFILE", "value": "p"}, {"name": "SECRET_X", "value": "abc"}]}}
    cfg_view = _fake_config(user)

    def fake_kubectl_json(args, *, context=None, timeout=60, **kw):
        if args[:2] == ["config", "view"]:
            return cfg_view(args, context=context, timeout=timeout, **kw)
        return None, shell.Result(cmd=["kubectl"], code=1, stderr="unreachable in test")

    monkeypatch.setattr(kube, "kubectl_json", fake_kubectl_json)
    monkeypatch.setattr(kube, "kubectl", lambda *a, **k: shell.Result(cmd=["kubectl"], code=1, stderr="unreachable in test"))
    # never call the real aws CLI or probe the tools on PATH from a test
    fake_aws = {"usable": False, "profile": "p", "region": None, "cluster_name": "c1", "checks": {"sts:GetCallerIdentity": {"ok": False, "why": "not called in a test", "account": None, "arn": None}}}
    monkeypatch.setattr(_setup.aws, "check_permissions", lambda *a, **k: fake_aws)
    monkeypatch.setattr(_setup.tools, "check_tools", lambda *a, **k: [])
    lines = []
    monkeypatch.setattr(_setup, "_p", lines.append)
    _setup.run_setup("ctx", Config(), snapshots_root=tmp_path, verbose=False)
    assert any(ln.strip() == "auth: exec aws eks get-token, env AWS_PROFILE, SECRET_X" for ln in lines), lines
    written = (tmp_path / "ctx" / "setup.json").read_text(encoding="utf-8")
    assert "abc" not in written and '"SECRET_X": "<redacted>"' in written
    assert "sts get-caller-identity" not in (tmp_path / "ctx" / "setup.log").read_text(encoding="utf-8")

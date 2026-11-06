"""`kubegap grafana-token --create` (lib/grafana_token.py): the one Secret read and the one write to Grafana, both only when the user chose it."""

from __future__ import annotations

import base64
import json
import stat

from lib import configedit, grafana_token, http, shell

OK = shell.Result(cmd=["kubectl"], code=0)


def _b64(s):
    return base64.b64encode(s.encode()).decode()


def _deploy(env):
    return {"items": [{"metadata": {"name": "kube-prometheus-stack-grafana"}, "spec": {"template": {"spec": {"containers": [{"name": "grafana", "env": env}]}}}}]}


SECRET_ENV = [
    {"name": "GF_SECURITY_ADMIN_USER", "valueFrom": {"secretKeyRef": {"name": "kube-prometheus-stack-grafana", "key": "admin-user"}}},
    {"name": "GF_SECURITY_ADMIN_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "kube-prometheus-stack-grafana", "key": "admin-password"}}},
]


def test_admin_ref_reads_the_workload_env_names_only(monkeypatch):
    monkeypatch.setattr(grafana_token.kube, "kubectl_json", lambda args, **kw: (_deploy(SECRET_ENV) if args[1] == "deployments" else {"items": []}, OK))
    ref = grafana_token.admin_ref("ctx", "monitoring")
    assert ref == {"workload": "deployment/kube-prometheus-stack-grafana", "container": "grafana", "secret": "kube-prometheus-stack-grafana", "password_key": "admin-password", "user_key": "admin-user", "user_value": None}
    monkeypatch.setattr(grafana_token.kube, "kubectl_json", lambda args, **kw: (_deploy([{"name": "GF_SECURITY_ADMIN_PASSWORD", "value": "plain"}]), OK))
    assert grafana_token.admin_ref("ctx", "monitoring") is None, "a password set as a plain env value is not offered: nothing to read once"


class _FakePF:
    url = "http://127.0.0.1:1"
    error = None

    def __init__(self, *a, **k):
        pass

    def start(self):
        return True

    def stop(self):
        pass


def _fake_post(calls, sa_status=201):
    def post(url, body, timeout=15, headers=None, max_bytes=0):
        calls.append((url, body, headers))
        if url.endswith("/api/serviceaccounts"):
            if sa_status == 409 and len([c for c in calls if c[0].endswith("/api/serviceaccounts")]) == 1:
                return http.HttpResult(url, 409, json.dumps({"message": "service account already exists"}), error="HTTP 409")
            return http.HttpResult(url, 201, json.dumps({"id": 7, "name": body["name"], "role": body["role"]}))
        assert url.endswith("/api/serviceaccounts/7/tokens")
        return http.HttpResult(url, 200, json.dumps({"id": 3, "name": body["name"], "key": "glsa_secret_value"}))

    return post


def test_create_reads_the_secret_once_posts_as_viewer_and_writes_the_token_0600(tmp_path, monkeypatch):
    reads = []

    def kubectl_json(args, **kw):
        reads.append(args)
        assert args[:2] == ["get", "secret"]
        return {"data": {"admin-user": _b64("admin"), "admin-password": _b64("p4ss")}}, OK

    calls = []
    monkeypatch.setattr(grafana_token.kube, "kubectl_json", kubectl_json)
    monkeypatch.setattr(grafana_token, "PortForward", _FakePF)
    monkeypatch.setattr(grafana_token.http, "post_json", _fake_post(calls))
    cfg = tmp_path / "config.yaml"
    cfg.write_text("language: ko\n")
    cfg.chmod(0o644)
    ref = {"secret": "kube-prometheus-stack-grafana", "password_key": "admin-password", "user_key": "admin-user", "user_value": None}
    grafana = {"ok": True, "service": {"namespace": "monitoring", "name": "kube-prometheus-stack-grafana", "port": 80}}
    out = grafana_token.create("my-ctx", grafana, ref, cfg)
    assert out["ok"] and out["service_account"].startswith("kubegap-my-ctx-") and out["id"] == 7 and "token" not in out
    assert reads == [["get", "secret", "-n", "monitoring", "kube-prometheus-stack-grafana"]], "one Secret, read once"
    assert calls[0][1] == {"name": out["service_account"], "role": "Viewer", "isDisabled": False}
    assert calls[0][2]["Authorization"] == "Basic " + _b64("admin:p4ss") and calls[1][1] == {"name": "kubegap", "secondsToLive": 0}
    text = cfg.read_text()
    assert "grafana_api_token: glsa_secret_value" in text and "language: ko" in text
    assert stat.S_IMODE(cfg.stat().st_mode) == 0o600
    assert "glsa_secret_value" not in grafana_token.describe(out) and "p4ss" not in grafana_token.describe(out)


def test_a_taken_name_gets_a_suffix_and_a_forbidden_secret_is_explained(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(grafana_token.http, "post_json", _fake_post(calls, sa_status=409))
    made = grafana_token.create_via_api("http://g", "admin", "p", "kubegap-x-2026-01-01")
    assert made["ok"] and made["service_account"] == "kubegap-x-2026-01-01-2"
    monkeypatch.setattr(grafana_token.kube, "kubectl_json", lambda args, **kw: (None, shell.Result(cmd=["kubectl"], code=1, stderr='Error from server (Forbidden): secrets "x" is forbidden: User "u" cannot get resource "secrets"')))
    out = grafana_token.create("c", {"ok": True, "service": {"namespace": "m", "name": "g", "port": 80}}, {"secret": "x", "password_key": "k"}, tmp_path / "c.yaml")
    assert not out["ok"] and "may not read Secret m/x" in out["error"] and "Show how" in out["error"]
    assert not (tmp_path / "c.yaml").exists()


def test_a_refused_login_names_the_cause_and_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(grafana_token.http, "post_json", lambda url, body, **kw: http.HttpResult(url, 401, "", error="HTTP 401"))
    made = grafana_token.create_via_api("http://g", "admin", "wrong", "n")
    assert not made["ok"] and "refused the admin login" in made["error"]


def test_set_secret_key_is_the_only_way_to_write_the_token(tmp_path):
    cfg = tmp_path / "config.yaml"
    try:
        configedit.set_key(cfg, "grafana_api_token", "glsa_x")
        raise AssertionError("the command-line path must refuse the token")
    except configedit.ConfigEditError as e:
        assert "not set by this command" in str(e)
    assert configedit.set_secret_key(cfg, "grafana_api_token", "glsa_x") is True
    assert "grafana_api_token: glsa_x" in cfg.read_text() and stat.S_IMODE(cfg.stat().st_mode) == 0o600
    assert configedit.set_secret_key(cfg, "grafana_api_token", "glsa_x") is False
    try:
        configedit.set_secret_key(cfg, "grafana_api_token", "has space")
        raise AssertionError("a token with a space is not a token")
    except configedit.ConfigEditError:
        pass

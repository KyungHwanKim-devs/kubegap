"""ingress-nginx controller in the traffic summary: version from the image, the IngressNightmare boundary, the admission webhook, and None when absent."""

from __future__ import annotations

import json

import pytest

from lib.summaries import traffic


@pytest.mark.parametrize(
    "version,expected",
    [("1.11.4", True), ("1.11.5", False), ("1.11.9", False), ("1.12.0", True), ("1.12.1", False), ("1.10.3", True), ("1.14.0", False), ("1.15.1", False), (None, None), ("latest", None)],
)
def test_vulnerable_boundary(version, expected):
    assert traffic.nginx_vulnerable(version) is expected


def _write(tmp_path, stem, items):
    (tmp_path / "objects").mkdir(exist_ok=True)
    (tmp_path / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}), encoding="utf-8")


def _controller(image, args=(), kind="Deployment"):
    o = {
        "metadata": {"namespace": "ingress-nginx", "name": "ingress-nginx-controller"},
        "spec": {"replicas": 2, "template": {"spec": {"containers": [{"name": "controller", "image": image, "args": list(args)}]}}},
        "status": {"readyReplicas": 2},
    }
    return o


def test_absent_is_none(tmp_path):
    _write(tmp_path, "deployments", [])
    _write(tmp_path, "daemonsets", [])
    out = traffic.analyze(tmp_path, {})
    assert out["nginx"] is None


def test_controller_version_webhook_and_vulnerability(tmp_path):
    _write(tmp_path, "deployments", [_controller("registry.k8s.io/ingress-nginx/controller:v1.12.0@sha256:abc", ["--validating-webhook=:8443"])])
    _write(tmp_path, "daemonsets", [])
    _write(tmp_path, "validatingwebhookconfigurations.admissionregistration.k8s.io", [{"metadata": {"name": "ingress-nginx-admission"}, "webhooks": [{"name": "validate.nginx.ingress.kubernetes.io", "failurePolicy": "Fail"}]}])
    n = traffic.analyze(tmp_path, {})["nginx"]
    assert n["present"] and n["version"] == "1.12.0" and n["vulnerable"] is True and n["admission_webhook"] is True
    assert n["admission_webhooks"] == [{"configuration": "ingress-nginx-admission", "failure_policy": "Fail"}]
    assert n["controllers"][0]["image"] == "registry.k8s.io/ingress-nginx/controller:v1.12.0" and n["controllers"][0]["replicas"] == 2 and n["retired"] is True


def test_fixed_version_without_webhook(tmp_path):
    _write(tmp_path, "deployments", [_controller("registry.k8s.io/ingress-nginx/controller:v1.14.0")])
    _write(tmp_path, "daemonsets", [])
    n = traffic.analyze(tmp_path, {})["nginx"]
    assert n["vulnerable"] is False and n["admission_webhook"] is False and n["versions"] == ["1.14.0"]


def test_unknown_version_is_not_cleared(tmp_path):
    _write(tmp_path, "deployments", [_controller("registry.k8s.io/ingress-nginx/controller@sha256:0123456789abcdef"), _controller("registry.k8s.io/ingress-nginx/controller:v1.14.0")])
    _write(tmp_path, "daemonsets", [])
    n = traffic.analyze(tmp_path, {})["nginx"]
    assert n["version"] == "1.14.0" and n["vulnerable"] is None and len(n["unknown_version_controllers"]) == 1


def test_nginx_inc_product_is_not_matched(tmp_path):
    _write(tmp_path, "deployments", [_controller("nginx/nginx-ingress:3.7.0"), _controller("private-registry.nginx.com/nginx-ic/nginx-plus-ingress:3.7.0")])
    _write(tmp_path, "daemonsets", [])
    assert traffic.analyze(tmp_path, {})["nginx"] is None


def test_bitnami_image_is_matched(tmp_path):
    _write(tmp_path, "deployments", [_controller("docker.io/bitnami/nginx-ingress-controller:1.12.0-debian-12-r0")])
    _write(tmp_path, "daemonsets", [])
    n = traffic.analyze(tmp_path, {})["nginx"]
    assert n["version"] == "1.12.0" and n["vulnerable"] is True

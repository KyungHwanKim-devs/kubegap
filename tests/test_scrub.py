"""ConfigMap values never reach the snapshot (lib/scrub.py), except the configuration keys kubegap parses, and the readers work on scrubbed and on older raw objects."""

from __future__ import annotations

import copy
import json

from lib import scrub


def _cm(ns, name, data, binary=None):
    d = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"namespace": ns, "name": name}, "data": data}
    if binary:
        d["binaryData"] = binary
    return d


APP = _cm(
    "prod-a",
    "app-config",
    {"DB_PASSWORD": "hunter2hunter2", "LOG_LEVEL": "info", "config.ini": "user = app\npassword = s3cr3t-value-1\nport = 5432\n", "ENDPOINT": "https://api.example.com", "DATA_DIR": "/var/data", "REPLICAS": "3", "DEBUG": "false"},
    binary={"blob": "AAECAwQ="},
)
COREDNS = _cm("kube-system", "coredns", {"Corefile": ".:53 {\n  cache 30\n}\n", "NodeHosts": "10.0.0.1 node-a\n", "extra": "something"})
ARGOCD = _cm("argocd", "argocd-cm", {"url": "https://argo.example.com", "admin.enabled": "false", "dex.config": "connectors:\n- type: github\n  config:\n    clientSecret: abcdefghijklmnop\n", "timeout.reconciliation": "180s"})
RBAC = _cm("argocd", "argocd-rbac-cm", {"policy.default": "role:readonly", "policy.csv": "p, role:dev, applications, get, */*, allow\n\ng, team, role:dev\n"})
SECRET = {"apiVersion": "v1", "kind": "Secret", "metadata": {"namespace": "prod-a", "name": "db"}, "type": "Opaque", "data": {"password": "aHVudGVyMg=="}, "stringData": {"x": "y"}}


def _all_strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _all_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _all_strings(v)
    elif isinstance(o, str):
        yield o


def test_configmap_values_are_dropped_and_described():
    cm = scrub.scrub_configmap(copy.deepcopy(APP))
    text = json.dumps(cm)
    for secret in ("hunter2hunter2", "s3cr3t-value-1", "https://api.example.com", "AAECAwQ="):
        assert secret not in text
    assert cm["data"]["DB_PASSWORD"] == {"len": 14, "shape": "word"}
    assert cm["data"]["config.ini"]["shape"] == "multiline"
    assert cm["data"]["ENDPOINT"]["shape"] == "url"
    assert cm["data"]["DATA_DIR"]["shape"] == "path"
    assert cm["data"]["REPLICAS"]["shape"] == "number"
    assert cm["data"]["DEBUG"]["shape"] == "bool"
    assert cm["binaryData"] == {"blob": {"len": 8}}
    mark = cm[scrub.MARK]
    assert mark["values_dropped"] is True
    assert mark["data_chars"] == sum(len(v) for v in APP["data"].values()) + len("AAECAwQ=")
    assert mark["secret_like_keys"] == ["DB_PASSWORD", "config.ini:password"]
    assert mark["kept_keys"] == []


def test_parser_keys_are_kept_and_only_those():
    cm = scrub.scrub_configmap(copy.deepcopy(COREDNS))
    assert cm["data"]["Corefile"] == COREDNS["data"]["Corefile"]
    assert cm["data"]["NodeHosts"] == COREDNS["data"]["NodeHosts"]
    assert cm["data"]["extra"] == {"len": 9, "shape": "word"}
    assert cm[scrub.MARK]["kept_keys"] == ["Corefile", "NodeHosts"]


def test_argocd_secret_bearing_keys_are_reduced():
    cm = scrub.scrub_configmap(copy.deepcopy(ARGOCD))
    assert "abcdefghijklmnop" not in json.dumps(cm)
    assert cm["data"]["dex.config"] == {"present": True, "len": len(ARGOCD["data"]["dex.config"])}
    assert cm["data"]["url"] == "https://argo.example.com"
    assert cm["data"]["admin.enabled"] == "false"
    rb = scrub.scrub_configmap(copy.deepcopy(RBAC))
    assert rb["data"]["policy.default"] == "role:readonly"
    assert rb["data"]["policy.csv"] == {"lines": 2, "len": len(RBAC["data"]["policy.csv"])}


def test_scrub_objects_handles_lists_and_secrets_and_is_idempotent():
    lst = {"apiVersion": "v1", "kind": "List", "items": [copy.deepcopy(APP), copy.deepcopy(SECRET), {"kind": "Pod", "metadata": {"name": "p"}, "spec": {"containers": [{"env": [{"name": "DB_PASSWORD", "value": "literal-in-pod-spec"}]}]}}]}
    out = scrub.scrub_objects(lst)
    assert "hunter2hunter2" not in json.dumps(out)
    assert "data" not in out["items"][1] and "stringData" not in out["items"][1]
    assert out["items"][1]["type"] == "Opaque"
    assert out["items"][2]["spec"]["containers"][0]["env"][0]["value"] == "literal-in-pod-spec"  # Pod specs are not touched; security.plaintext-env reads them
    again = scrub.scrub_objects(copy.deepcopy(out))
    assert again == out


def test_readers_work_on_scrubbed_and_unscrubbed_objects():
    raw = copy.deepcopy(APP)
    scrubbed = scrub.scrub_configmap(copy.deepcopy(APP))
    assert scrub.configmap_chars(raw) == scrub.configmap_chars(scrubbed)
    assert scrub.configmap_secret_like_keys(raw) == scrub.configmap_secret_like_keys(scrubbed) == ["DB_PASSWORD", "config.ini:password"]


def test_secret_like_detection_skips_templates_and_paths():
    data = {"TOKEN_FILE": "/var/run/token", "API_URL": "https://x", "fluent.conf": "[OUTPUT]\n    HTTP_Passwd ${ES_PASSWORD}\n    HTTP_Passwd realpassword99\n", "PASSWORD": "12345678", "SECRET_ENABLED": "true"}
    assert scrub.secret_like_keys(data) == ["fluent.conf:HTTP_Passwd"]


def test_argocd_helpers_accept_scrubbed_and_raw_values():
    from lib import argocdctl

    assert argocdctl._csv_lines({"lines": 4, "len": 100}) == 4
    assert argocdctl._csv_lines("a\n\nb\n") == 2
    assert argocdctl._csv_lines(None) == 0
    assert argocdctl._non_empty({"present": True, "len": 40}) is True
    assert argocdctl._non_empty({"present": False, "len": 0}) is False
    assert argocdctl._non_empty({"len": 0, "shape": "empty"}) is False
    assert argocdctl._non_empty({"len": 3, "shape": "word"}) is True
    assert argocdctl._non_empty("") is False and argocdctl._non_empty("x") is True


def test_presence_only_is_false_for_empty_values_and_keys_are_deduped():
    cm = scrub.scrub_configmap(_cm("argocd", "argocd-cm", {"dex.config": "   ", "oidc.config": "issuer: x\nclientSecret: abcdefghijklmnop\n"}))
    assert cm["data"]["dex.config"]["present"] is False and cm["data"]["oidc.config"]["present"] is True
    conf = "[OUTPUT]\n    HTTP_Passwd realpassword99\n[OUTPUT]\n    HTTP_Passwd realpassword99\n"
    assert scrub.secret_like_keys({"fluent-bit.conf": conf}) == ["fluent-bit.conf:HTTP_Passwd"]

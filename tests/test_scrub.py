"""ConfigMap values never reach the snapshot (lib/foundations/scrub.py), except the configuration keys kubegap parses, and the readers work on scrubbed and on older raw objects."""

from __future__ import annotations

import copy
import json
import re

from lib.foundations import scrub


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
    # a credential-like variable loses its value and keeps the verdict security.plaintext-env reads
    assert "literal-in-pod-spec" not in json.dumps(out)
    assert out["items"][2]["spec"]["containers"][0]["env"][0] == {"name": "DB_PASSWORD", scrub.MARK: {"len": 19, "shape": "word", "secret_like": True}}
    again = scrub.scrub_objects(copy.deepcopy(out))
    assert again == out


def test_env_values_go_only_for_credential_like_names():
    env = [
        {"name": "NEO4J_AUTH", "value": "neo4j/correct-horse"},
        {"name": "TOKEN_CAP", "value": "500000"},
        {"name": "CLUSTER_NAME", "value": "prod-a"},
        {"name": "DB_PASSWORD_FILE", "value": "/run/secrets/db"},
        {"name": "API_TOKEN", "valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}},
    ]
    tpl = {"kind": "ControllerRevision", "metadata": {"name": "r"}, "data": {"spec": {"template": {"spec": {"containers": [{"name": "c", "env": copy.deepcopy(env)}]}}}}}
    out = scrub.scrub_objects(tpl)["data"]["spec"]["template"]["spec"]["containers"][0]["env"]
    assert "correct-horse" not in json.dumps(out) and "500000" not in json.dumps(out)
    assert [scrub.entry_secret_like(e) for e in out] == [True, False, False, False, False]
    assert out[2] == env[2] and out[3] == env[3] and out[4] == env[4]  # other names, skipped suffixes and references stay as they were


def test_a_workload_keeps_only_apiversion_and_kind_of_its_applied_copy():
    applied = json.dumps({"apiVersion": "apps/v1", "kind": "Deployment", "spec": {"template": {"spec": {"containers": [{"env": [{"name": "X", "value": "in-the-copy"}]}]}}}})
    dep = {"kind": "Deployment", "metadata": {"name": "d", "annotations": {scrub.LAST_APPLIED: applied, "other": "kept"}}}
    out = scrub.scrub_objects(dep)
    assert json.loads(out["metadata"]["annotations"][scrub.LAST_APPLIED]) == {"apiVersion": "apps/v1", "kind": "Deployment"}
    assert out["metadata"]["annotations"]["other"] == "kept"
    assert scrub.scrub_objects(copy.deepcopy(out)) == out


def test_readers_work_on_scrubbed_and_unscrubbed_objects():
    raw = copy.deepcopy(APP)
    scrubbed = scrub.scrub_configmap(copy.deepcopy(APP))
    assert scrub.configmap_chars(raw) == scrub.configmap_chars(scrubbed)
    assert scrub.secret_like_keys(raw["data"]) == scrub.configmap_secret_like_keys(scrubbed) == ["DB_PASSWORD", "config.ini:password"]
    assert scrub.configmap_secret_like_keys(raw) == []  # a ConfigMap that did not go through the scrub has no record; every one in a snapshot has


def test_secret_like_detection_skips_templates_and_paths():
    data = {"TOKEN_FILE": "/var/run/token", "API_URL": "https://x", "fluent.conf": "[OUTPUT]\n    HTTP_Passwd ${ES_PASSWORD}\n    HTTP_Passwd realpassword99\n", "PASSWORD": "12345678", "SECRET_ENABLED": "true"}
    assert scrub.secret_like_keys(data) == ["fluent.conf:HTTP_Passwd"]


def test_argocd_helpers_accept_scrubbed_and_raw_values():
    from lib.summaries import argocdctl

    assert argocdctl._csv_lines({"lines": 4, "len": 100}) == 4
    assert argocdctl._csv_lines("a\n\nb\n") == 0  # the text form does not reach a snapshot (lib/foundations/scrub.py LINE_COUNT_ONLY)
    assert argocdctl._csv_lines(None) == 0
    assert argocdctl._non_empty({"present": True, "len": 40}) is True
    assert argocdctl._non_empty({"present": False, "len": 0}) is False
    assert argocdctl._non_empty({"len": 0, "shape": "empty"}) is False
    assert argocdctl._non_empty({"len": 3, "shape": "word"}) is True
    assert argocdctl._non_empty("") is False and argocdctl._non_empty("x") is False  # a plain string is not a scrubbed value


def test_presence_only_is_false_for_empty_values_and_keys_are_deduped():
    cm = scrub.scrub_configmap(_cm("argocd", "argocd-cm", {"dex.config": "   ", "oidc.config": "issuer: x\nclientSecret: abcdefghijklmnop\n"}))
    assert cm["data"]["dex.config"]["present"] is False and cm["data"]["oidc.config"]["present"] is True
    conf = "[OUTPUT]\n    HTTP_Passwd realpassword99\n[OUTPUT]\n    HTTP_Passwd realpassword99\n"
    assert scrub.secret_like_keys({"fluent-bit.conf": conf}) == ["fluent-bit.conf:HTTP_Passwd"]


def _applied_copy(cm: dict) -> str:
    return json.dumps({"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": cm["metadata"]["name"], "namespace": cm["metadata"]["namespace"]}, "data": cm["data"]})


def test_applied_annotations_are_dropped_and_keys_kept():
    import base64
    import gzip

    raw = copy.deepcopy(APP)
    plain = _applied_copy(raw)
    packed = base64.b64encode(gzip.compress(plain.encode())).decode()
    raw["metadata"]["annotations"] = {"kubectl.kubernetes.io/last-applied-configuration": plain, "objectset.rio.cattle.io/applied": packed, "argocd.argoproj.io/tracking-id": "app:v1/ConfigMap:prod/app"}
    cm = scrub.scrub_configmap(raw)
    text = json.dumps(cm)
    for secret in ("hunter2hunter2", "s3cr3t-value-1", "https://api.example.com"):
        assert secret not in text
    assert packed not in text
    ann = cm["metadata"]["annotations"]
    assert ann["kubectl.kubernetes.io/last-applied-configuration"] == {"len": len(plain), "shape": "text"}
    assert ann["objectset.rio.cattle.io/applied"] == {"len": len(packed), "shape": "word"}
    assert ann["argocd.argoproj.io/tracking-id"] == "app:v1/ConfigMap:prod/app"  # other annotations are untouched
    assert cm[scrub.MARK]["annotations_dropped"] == ["kubectl.kubernetes.io/last-applied-configuration", "objectset.rio.cattle.io/applied"]
    assert cm[scrub.MARK]["secret_like_keys"] == ["DB_PASSWORD", "config.ini:password"]  # the copy carries the same keys; no duplicates


def test_applied_annotation_secret_keys_are_found_even_when_data_differs():
    raw = copy.deepcopy(APP)
    raw["data"] = {"PLAIN": "nothing-secret-here"}
    raw["metadata"]["annotations"] = {"kubectl.kubernetes.io/last-applied-configuration": json.dumps({"kind": "ConfigMap", "data": {"API_TOKEN": "tok-0123456789abcdef"}})}
    cm = scrub.scrub_configmap(raw)
    assert cm[scrub.MARK]["secret_like_keys"] == ["API_TOKEN"]
    assert "tok-0123456789abcdef" not in json.dumps(cm)


def test_scrub_without_annotations_and_twice():
    raw = copy.deepcopy(APP)
    raw["metadata"].pop("annotations", None)
    cm = scrub.scrub_configmap(raw)
    assert cm[scrub.MARK]["annotations_dropped"] == []
    assert scrub.scrub_configmap(copy.deepcopy(cm)) == cm


def test_plain_json_objectset_and_odd_copies_do_not_break():
    raw = copy.deepcopy(APP)
    raw["metadata"]["annotations"] = {"objectset.rio.cattle.io/applied": json.dumps({"kind": "ConfigMap", "data": {"API_TOKEN": "tok-0123456789abcdef"}})}
    cm = scrub.scrub_configmap(raw)
    assert cm[scrub.MARK]["secret_like_keys"] == ["DB_PASSWORD", "config.ini:password", "API_TOKEN"]
    for odd in (json.dumps({"data": ["not", "a", "dict"]}), json.dumps(["list"]), "not json", "H4sInotreallygzip"):
        raw = copy.deepcopy(APP)
        raw["metadata"]["annotations"] = {"kubectl.kubernetes.io/last-applied-configuration": odd}
        assert scrub.scrub_configmap(raw)[scrub.MARK]["annotations_dropped"] == ["kubectl.kubernetes.io/last-applied-configuration"]


def test_secret_copy_annotation_is_dropped_in_the_defensive_path():
    sec = copy.deepcopy(SECRET)
    sec["metadata"]["annotations"] = {"kubectl.kubernetes.io/last-applied-configuration": json.dumps({"kind": "Secret", "data": {"password": "aHVudGVyMg=="}})}
    out = scrub.scrub_objects(sec)
    assert "aHVudGVyMg==" not in json.dumps(out) and out["metadata"]["annotations"]["kubectl.kubernetes.io/last-applied-configuration"]["len"] > 0


def test_gzip_applied_copy_beyond_the_cap_is_not_inspected_but_still_replaced(monkeypatch):
    """A 20 MiB document gzips to about 20 KB; the scrubber must stop expanding at GZIP_MAX_BYTES and still drop the annotation (#91)."""
    import base64
    import gzip

    monkeypatch.setattr(scrub, "GZIP_MAX_BYTES", 1024 * 1024)
    big = json.dumps({"kind": "ConfigMap", "data": {"API_TOKEN": "tok-0123456789abcdef", "pad": "0" * (20 * 1024 * 1024)}}).encode()
    packed = base64.b64encode(gzip.compress(big)).decode()
    assert len(packed) < 100_000 and packed.startswith("H4sI")
    reads = []
    orig = gzip.GzipFile.read

    def spy(self, size=-1):
        out = orig(self, size)
        reads.append((size, len(out)))
        return out

    monkeypatch.setattr(gzip.GzipFile, "read", spy)
    assert scrub._secret_like_in_applied(packed) == []
    assert reads == [(1024 * 1024 + 1, 1024 * 1024 + 1)], "asked for cap+1 bytes, got cap+1, and expanded nothing more"
    raw = {"kind": "ConfigMap", "metadata": {"name": "c", "namespace": "n", "annotations": {"objectset.rio.cattle.io/applied": packed}}, "data": {"a": "b"}}
    cm = scrub.scrub_configmap(raw)
    assert cm["metadata"]["annotations"]["objectset.rio.cattle.io/applied"] == {"len": len(packed), "shape": "word"}
    assert "tok-0123456789abcdef" not in json.dumps(cm)


def test_gzip_applied_copy_under_the_cap_is_inspected():
    import base64
    import gzip

    doc = json.dumps({"kind": "ConfigMap", "data": {"API_TOKEN": "tok-0123456789abcdef"}}).encode()
    packed = base64.b64encode(gzip.compress(doc)).decode()
    assert scrub._secret_like_in_applied(packed) == ["API_TOKEN"]


def test_a_sample_never_carries_a_load_balancer_address_or_the_snapshot_folder(tmp_path):
    """scripts/scrub-sample.py replaces these whatever the map holds: a report about an open port names the address it is open on."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("scrub_sample", Path(__file__).resolve().parent.parent / "scripts" / "scrub-sample.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = "open on k8s-mw-kafka-0a1b2c3d4e-0011223344556677.elb.ap-northeast-2.amazonaws.com, snapshot `/Users/me/.kubegap-x/snapshots/prod/2026-11-15T01-51-00`"
    out = mod.scrub(text, mod.build({}))
    assert "0a1b2c3d4e" not in out and "amazonaws.com" not in out and re.search(r"lb-[0-9a-f]{10}\.elb\.example\.com", out)
    other = mod.scrub("a-1.elb.us-east-1.amazonaws.com b-2.elb.us-east-1.amazonaws.com a-1.elb.us-east-1.amazonaws.com", mod.build({})).split()
    assert other[0] == other[2] != other[1]  # the same address gets the same name, another address another
    assert "/Users/me" not in out and "`~/.kubegap/snapshots/<context>/2026-11-15T01-51-00`" in out
    out = mod.scrub("target group k8s-prodshop-checkout-1234567890 and ALB k8s-acmeprodlb-abcdef0123 x", mod.build({}))
    assert "prodshop" not in out and "checkout" not in out and "k8s-lb-1234567890" in out
    assert "acmeprodlb" not in out and "k8s-lb-abcdef0123" in out

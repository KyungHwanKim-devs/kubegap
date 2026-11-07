"""deploy/node-access/COMMANDS.md and deploy/permissions/ssm-document.yaml are generated from the collector definitions; these tests fail when a node command changes without regenerating them, and pin what the SSM document must guarantee."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from lib.collection import nodecommands
from lib.foundations import yamlite

ROOT = Path(__file__).resolve().parent.parent


def _cli(*args: str) -> str:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "node-commands", *args], check=True, capture_output=True, text=True, cwd=ROOT).stdout


def test_commands_md_is_current():
    assert _cli("--markdown") == nodecommands.COMMANDS_MD_PATH.read_text(encoding="utf-8"), "run `scripts/kubegap node-commands --markdown > deploy/node-access/COMMANDS.md`"


def test_ssm_document_is_current():
    assert _cli("--ssm-document") == nodecommands.DOCUMENT_PATH.read_text(encoding="utf-8"), "run `scripts/kubegap node-commands --ssm-document > deploy/permissions/ssm-document.yaml`"


def test_every_node_command_is_a_document_step():
    """Whatever lib/collection/collect can send (type: node steps, pod-metrics fallbacks, the two probes) must be selectable in the document, otherwise the SSM backend fails for that step."""
    doc = yamlite.load_file(nodecommands.DOCUMENT_PATH)
    allowed = set(doc["parameters"]["step"]["allowedValues"])
    assert allowed == set(nodecommands.step_keys())
    assert {"probe", "capabilities", "core/node-os"} <= allowed


def test_document_has_no_free_text_parameter():
    """The only parameters are the step name (fixed list), podIp (IPv4 only), port (digits, #136) and executionTimeout (digits). A free string parameter would let a key run arbitrary commands again."""
    doc = yamlite.load_file(nodecommands.DOCUMENT_PATH)
    params = doc["parameters"]
    assert set(params) == {"step", "podIp", "port", "executionTimeout"}
    assert params["port"]["allowedPattern"] == nodecommands.PORT_PATTERN and re.fullmatch(params["port"]["allowedPattern"], "9402") and not re.fullmatch(params["port"]["allowedPattern"], "80;id")
    assert params["step"].get("allowedValues") and "allowedPattern" not in params["step"]
    assert params["podIp"]["allowedPattern"] == nodecommands.IPV4_PATTERN
    assert re.fullmatch(params["podIp"]["allowedPattern"], "10.0.12.34") and not re.fullmatch(params["podIp"]["allowedPattern"], "10.0.0.1; rm -rf /")
    assert re.fullmatch(params["executionTimeout"]["allowedPattern"], "600") and not re.fullmatch(params["executionTimeout"]["allowedPattern"], "60; id")
    script = doc["mainSteps"][0]["inputs"]["runCommand"][0]
    assert set(re.findall(r"\{\{ *([A-Za-z]+) *\}\}", script)) <= {"step", "podIp", "port"}
    assert doc["mainSteps"][0]["inputs"]["timeoutSeconds"] == "{{ executionTimeout }}"


def test_document_script_is_valid_shell():
    doc = yamlite.load_file(nodecommands.DOCUMENT_PATH)
    script = doc["mainSteps"][0]["inputs"]["runCommand"][0].replace("{{ step }}", "probe").replace("{{ podIp }}", "10.0.0.1")
    r = subprocess.run(["sh", "-n"], input=script, text=True, capture_output=True, check=False)
    assert r.returncode == 0, r.stderr


def test_pod_metrics_cmd_matches_collect_py():
    """lib/collection/collect sends exactly this text over SSH, and the document embeds it with {{ podIp }}; the two must be the same function."""
    assert nodecommands.pod_metrics_cmd("10.1.2.3", 8080, "/metrics", None) == "curl -s -m 8 http://10.1.2.3:8080/metrics | grep -vE '^#|_bucket\\{'"
    assert nodecommands.pod_metrics_cmd("10.1.2.3", 9402, "/metrics", "^certmanager_").endswith(" | grep -E '^certmanager_'")


def test_iam_policy_allows_only_the_document():
    import json

    pol = json.loads((ROOT / "deploy" / "permissions" / "iam-policy.json").read_text(encoding="utf-8"))
    send = [st for st in pol["Statement"] if "ssm:SendCommand" in st["Action"]]
    resources = [r for st in send for r in ([st["Resource"]] if isinstance(st["Resource"], str) else st["Resource"])]
    docs = [r for r in resources if ":document/" in r]
    assert docs == [f"arn:aws:ssm:*:<ACCOUNT_ID>:document/{nodecommands.DOCUMENT_NAME}"], (
        "SendCommand must be allowed on the kubegap document only (no AWS-RunShellScript) and only in this account, so a same-named document shared from another account does not match"
    )
    inst = [st for st in send if any("instance/" in r for r in ([st["Resource"]] if isinstance(st["Resource"], str) else st["Resource"]))]
    assert inst and all("Condition" in st for st in inst), "the instance statement must carry the cluster tag condition"
    assert "ssm:DescribeDocument" in pol["Statement"][0]["Action"]


def test_pod_ip_allowed_admits_pod_addresses_only():
    """The node-side curl may be pointed at a pod address and nothing else; the refusal carries the reason (#93)."""
    assert nodecommands.pod_ip_allowed("10.0.12.34") == (True, "private IPv4")
    assert nodecommands.pod_ip_allowed("172.16.5.6") == (True, "private IPv4")
    assert nodecommands.pod_ip_allowed("192.168.0.1") == (True, "private IPv4")
    assert nodecommands.pod_ip_allowed("100.64.0.1") == (True, "shared address space (100.64.0.0/10)"), "EKS custom networking pods live here and ipaddress.is_private says False"
    assert nodecommands.pod_ip_allowed(" 10.0.0.5\n") == (False, "not an IP address"), "the string is sent as it is, so only an exact address passes"
    outside = "not in a pod address range (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 or 100.64.0.0/10)"
    refused = {
        "127.0.0.1": "loopback",
        "169.254.169.254": "link-local",
        "224.0.0.1": "multicast",
        "8.8.8.8": outside,
        "100.128.0.1": outside,
        "198.18.0.1": outside,
        "192.0.0.170": outside,
        "203.0.113.1": outside,
        "0.0.0.1": outside,
        "255.255.255.255": "reserved",
        "fd00::1": "IPv6 pod: node-side metrics fallback not supported",
        "::1": "IPv6 pod: node-side metrics fallback not supported",
        "0.0.0.0": "unspecified",
        "not-an-ip": "not an IP address",
        "": "not an IP address",
        "10.0.0.5; rm -rf /": "not an IP address",
    }
    for ip, why in refused.items():
        assert nodecommands.pod_ip_allowed(ip) == (False, why), ip
    assert nodecommands.pod_ip_allowed(None) == (False, "not an IP address")


def test_commands_md_says_which_pods_are_curled():
    text = nodecommands.COMMANDS_MD_PATH.read_text(encoding="utf-8")
    assert "Only Running pods with an IPv4 address in 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 or 100.64.0.0/10 are curled" in text


def test_install_document_finds_the_uploaded_version_by_describing_it(monkeypatch):
    """#125: list-document-versions carries no Hash (DocumentVersionInfo, ssm service-2.json:7949-7990@2.39.3), so a version already holding the local content is found through describe-document --document-version and made the default instead of being uploaded again."""
    from lib.collection import aws as _aws
    from lib.collection import nodecommands

    local = nodecommands.document_sha256()
    calls = []

    def fake(args, **kw):
        calls.append(args)
        op = args[1]
        if op == "describe-document" and "--document-version" not in args:
            # the default version differs, then after the switch it matches
            h = local if any(a[1] == "update-document-default-version" for a in calls) else "0" * 64
            return {"Document": {"Hash": h, "HashType": "Sha256", "DocumentVersion": "3" if h == local else "1", "Status": "Active"}}, None
        if op == "list-document-versions":
            return {"DocumentVersions": [{"Name": nodecommands.DOCUMENT_NAME, "DocumentVersion": "1", "IsDefaultVersion": True}, {"Name": nodecommands.DOCUMENT_NAME, "DocumentVersion": "3", "IsDefaultVersion": False}]}, None
        if op == "describe-document":
            ver = args[args.index("--document-version") + 1]
            return {"Document": {"Hash": local if ver == "3" else "0" * 64, "DocumentVersion": ver}}, None
        if op == "update-document-default-version":
            return {"Description": {"Name": nodecommands.DOCUMENT_NAME, "DefaultVersion": "3"}}, None
        raise AssertionError(f"unexpected call {args}")

    monkeypatch.setattr(_aws, "aws_json", fake)
    res = nodecommands.install_document(None, None)
    assert res["ok"] and res["action"] == "switch-default" and res["version"] == "3", res
    assert not any(a[1] == "update-document" for a in calls), "a version with the same content must not be uploaded twice"
    assert ["ssm", "describe-document", "--name", nodecommands.DOCUMENT_NAME, "--document-version", "3"] in calls

"""deploy/node-access/COMMANDS.md and deploy/permissions/ssm-document.yaml are generated from the collector definitions; these tests fail when a node command changes without regenerating them, and pin what the SSM document must guarantee."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from lib import nodecommands, yamlite

ROOT = Path(__file__).resolve().parent.parent


def _cli(*args: str) -> str:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "kubegap"), "node-commands", *args], check=True, capture_output=True, text=True, cwd=ROOT).stdout


def test_commands_md_is_current():
    assert _cli("--markdown") == nodecommands.COMMANDS_MD_PATH.read_text(encoding="utf-8"), "run `scripts/kubegap node-commands --markdown > deploy/node-access/COMMANDS.md`"


def test_ssm_document_is_current():
    assert _cli("--ssm-document") == nodecommands.DOCUMENT_PATH.read_text(encoding="utf-8"), "run `scripts/kubegap node-commands --ssm-document > deploy/permissions/ssm-document.yaml`"


def test_every_node_command_is_a_document_step():
    """Whatever collect.py can send (type: node steps, pod-metrics fallbacks, the two probes) must be selectable in the document, otherwise the SSM backend fails for that step."""
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
    """collect.py sends exactly this text over SSH and DaemonSet, and the document embeds it with {{ podIp }}; the two must be the same function."""
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


def test_node_reader_daemonset_image_is_pinned_by_index_digest():
    """The node-reader pod is privileged with the host root mounted, so a moved tag must not change what runs: the image carries the digest of the
    multi-architecture index. yamlite reads one document at a time, so the file is split on its `---` line and the DaemonSet document is loaded."""
    text = (ROOT / "deploy" / "node-access" / "daemonset.yaml").read_text(encoding="utf-8")
    docs = [yamlite.load(part) for part in re.split(r"^---$", text, flags=re.MULTILINE) if part.strip()]
    assert [d["kind"] for d in docs] == ["Namespace", "DaemonSet"]
    containers = docs[1]["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    image = containers[0]["image"]
    assert re.fullmatch(r"public\.ecr\.aws/docker/library/busybox:1\.36@sha256:[0-9a-f]{64}", image), image
    assert "crane digest public.ecr.aws/docker/library/busybox:1.36" in text, "the bump command stays next to the pin"


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

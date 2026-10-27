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
    """The only parameters are the step name (fixed list), podIp (IPv4 only) and executionTimeout (digits). A free string parameter would let a key run arbitrary commands again."""
    doc = yamlite.load_file(nodecommands.DOCUMENT_PATH)
    params = doc["parameters"]
    assert set(params) == {"step", "podIp", "executionTimeout"}
    assert params["step"].get("allowedValues") and "allowedPattern" not in params["step"]
    assert params["podIp"]["allowedPattern"] == nodecommands.IPV4_PATTERN
    assert re.fullmatch(params["podIp"]["allowedPattern"], "10.0.12.34") and not re.fullmatch(params["podIp"]["allowedPattern"], "10.0.0.1; rm -rf /")
    assert re.fullmatch(params["executionTimeout"]["allowedPattern"], "600") and not re.fullmatch(params["executionTimeout"]["allowedPattern"], "60; id")
    script = doc["mainSteps"][0]["inputs"]["runCommand"][0]
    assert set(re.findall(r"\{\{ *([A-Za-z]+) *\}\}", script)) <= {"step", "podIp"}
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
    assert docs == [f"arn:aws:ssm:*:*:document/{nodecommands.DOCUMENT_NAME}"], "SendCommand must be allowed on the kubegap document only (no AWS-RunShellScript)"
    inst = [st for st in send if any("instance/" in r for r in ([st["Resource"]] if isinstance(st["Resource"], str) else st["Resource"]))]
    assert inst and all("Condition" in st for st in inst), "the instance statement must carry the cluster tag condition"
    assert "ssm:DescribeDocument" in pol["Statement"][0]["Action"]

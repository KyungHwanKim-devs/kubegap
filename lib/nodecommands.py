"""The complete list of commands kubegap runs on nodes, and the SSM document that pins them.

Node access is a shell on the node (SSM on EKS, SSH on k3s and bare metal, `kubectl exec` into the DaemonSet elsewhere). A shell
has no read-only mode, so "read-only" has to be made visible and enforced on top of it:

- `deploy/node-access/COMMANDS.md` lists every command, per backend, generated from the collector definitions
  (`type: node` steps and their scripts, `type: pod-metrics` steps that fall back to curl inside a node, and the two built-in
  probes in lib/node.py). `scripts/kubegap node-commands --markdown` writes it; tests/test_node_commands.py fails when it is stale.
- `deploy/permissions/ssm-document.yaml` is an SSM Command document with the same commands embedded. The IAM policy allows
  `ssm:SendCommand` on that document only, so a key with the policy can run these commands and nothing else. `step` picks the
  command by name from a fixed list; the only free value is `podIp`, limited to an IPv4 address. `scripts/kubegap node-commands
  --ssm-document` writes it, and lib/node.py compares the sha256 of this file with the document in the account before sending.

The two files come from one walk over the collectors, so they cannot disagree with each other or with what collect.py sends.
"""

from __future__ import annotations

import hashlib
import json
import re

from . import paths, yamlite

DOCUMENT_NAME = "kubegap-node-read"
DOCUMENT_PATH = paths.ROOT / "deploy" / "permissions" / "ssm-document.yaml"
COMMANDS_MD_PATH = paths.ROOT / "deploy" / "node-access" / "COMMANDS.md"
SUDOERS_PATH = paths.ROOT / "deploy" / "node-access" / "kubegap-sudoers"
IPV4_PATTERN = r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$"

# Built-in commands of lib/node.py (not collector steps). Kept here so the generator and the runtime read the same strings.
PROBE_CMD = "echo kubegap-ok; uname -r; hostname"
CAPABILITY_SCRIPT = (
    "echo cap:journal=$( journalctl -n1 -q -u k3s -u k3s-agent -u kubelet -u containerd >/dev/null 2>&1 && echo yes || echo no );"
    "echo cap:kernlog=$( [ -r /var/log/kern.log ] && echo yes || echo no );"
    "echo cap:dmesg=$( dmesg -T >/dev/null 2>&1 && echo yes || ( sudo -n dmesg -T >/dev/null 2>&1 && echo sudo || echo no ) );"
    "echo cap:k3s-db=$( ls /var/lib/rancher/k3s/server/db >/dev/null 2>&1 && echo yes || ( sudo -n ls -la /var/lib/rancher/k3s/server/db >/dev/null 2>&1 && echo sudo || echo no ) );"
    "echo cap:k3s-config=$( cat /etc/rancher/k3s/config.yaml >/dev/null 2>&1 && echo yes || ( sudo -n cat /etc/rancher/k3s/config.yaml >/dev/null 2>&1 && echo sudo || ( [ -e /etc/rancher/k3s/config.yaml ] && echo no || echo absent ) ) );"
    "echo cap:crictl=$( (command -v crictl >/dev/null && crictl info >/dev/null 2>&1) && echo yes || ( sudo -n /usr/local/bin/k3s crictl info >/dev/null 2>&1 && echo sudo || echo no ) );"
    "echo cap:sudo-any=$( sudo -n true >/dev/null 2>&1 && echo yes || echo no );"
    "echo cap:k3s-role=$( systemctl is-active k3s >/dev/null 2>&1 && echo server || ( systemctl is-active k3s-agent >/dev/null 2>&1 && echo agent || echo none ) );"
    "echo cap:cgroup=$( stat -fc %T /sys/fs/cgroup/ 2>/dev/null )"
)


def pod_metrics_cmd(pod_ip: str, port: int | str, path: str, keep: str | None) -> str:
    """The curl kubegap runs inside a node when the apiserver pod proxy is blocked. Histogram buckets and comments are dropped on the node (SSM output cap); `keep` narrows to the metric names a collector needs."""
    tail = f" | grep -E '{keep}'" if keep else ""
    return f"curl -s -m 8 http://{pod_ip}:{port}{path} | grep -vE '^#|_bucket\\{{'" + tail


def normalize_cmd(cmd: str) -> str:
    """collect.py sends `cmd:` steps with whitespace collapsed (YAML folded scalars arrive with newlines)."""
    return " ".join(str(cmd).split())


def node_commands() -> list[dict]:
    """Every command that can reach a node, in a stable order. Each entry: step (document key), kind (script|cmd|pod-metrics|builtin), collector, id, text, plus nodes/requires/out for collector steps and port/path/keep for pod-metrics."""
    out: list[dict] = [
        {"step": "probe", "kind": "builtin", "collector": "lib/node.py", "id": "probe", "text": PROBE_CMD, "note": "access check: `kubegap nodes`, setup and discover"},
        {"step": "capabilities", "kind": "builtin", "collector": "lib/node.py", "id": "capabilities", "text": CAPABILITY_SCRIPT, "note": "which privileged reads work on the node (SSH backend: `kubegap nodes`)"},
    ]
    for folder in sorted(p for p in paths.COLLECTORS_DIR.iterdir() if (p / "collect.yaml").is_file()):
        steps = yamlite.load_file(folder / "collect.yaml") or []
        for st in steps:
            if not isinstance(st, dict) or "id" not in st:
                continue
            key = f"{folder.name}/{st['id']}"
            if st.get("type") == "node":
                if st.get("script"):
                    text = (folder / str(st["script"])).read_text(encoding="utf-8")
                    out.append(
                        {
                            "step": key,
                            "kind": "script",
                            "collector": folder.name,
                            "id": st["id"],
                            "text": text,
                            "file": f"collectors/{folder.name}/{st['script']}",
                            "nodes": st.get("nodes", "all"),
                            "requires": st.get("requires"),
                            "out": st.get("out"),
                        }
                    )
                else:
                    out.append({"step": key, "kind": "cmd", "collector": folder.name, "id": st["id"], "text": normalize_cmd(st["cmd"]), "nodes": st.get("nodes", "all"), "requires": st.get("requires"), "out": st.get("out")})
            elif st.get("type") == "pod-metrics":
                port, path, keep = st["port"], st.get("path", "/metrics"), st.get("keep")
                out.append(
                    {
                        "step": key,
                        "kind": "pod-metrics",
                        "collector": folder.name,
                        "id": st["id"],
                        "text": pod_metrics_cmd("<podIp>", port, path, keep),
                        "port": port,
                        "path": path,
                        "keep": keep,
                        "namespace": st.get("namespace"),
                        "selector": st.get("selector"),
                    }
                )
    return out


def step_keys() -> list[str]:
    return [c["step"] for c in node_commands()]


# ---------- COMMANDS.md ----------


def render_markdown(cmds: list[dict] | None = None) -> str:
    cmds = cmds if cmds is not None else node_commands()
    builtin = [c for c in cmds if c["kind"] == "builtin"]
    node_steps = [c for c in cmds if c["kind"] in ("script", "cmd")]
    pm = [c for c in cmds if c["kind"] == "pod-metrics"]
    L: list[str] = []
    L.append("# Commands kubegap runs on nodes")
    L.append("")
    L.append(
        f"Generated by `scripts/kubegap node-commands --markdown` from `collectors/*/collect.yaml`, the scripts those steps name, and `lib/node.py`. {len(cmds)} commands: {len(builtin)} built-in probes, {len(node_steps)} collector node steps, {len(pm)} pod-metrics fallbacks. `tests/test_node_commands.py` fails when this file is older than its sources."
    )
    L.append("")
    L.append(
        "This is the complete list. Nothing else is sent to a node. Every command reads; none writes, restarts, deletes or changes configuration. Directory sizes are read with `du -d` (totals per directory, no file contents). Tokens in the k3s unit file are removed on the node before the output leaves it."
    )
    L.append("")
    L.append("## How a command reaches the node")
    L.append("")
    L.append("| Backend | Platform | Who runs it | How the list is enforced |")
    L.append("|---|---|---|---|")
    L.append(
        f"| SSM | EKS | root, via the SSM agent | The IAM policy allows `ssm:SendCommand` only on the document [`deploy/permissions/ssm-document.yaml`](../permissions/ssm-document.yaml) (`{DOCUMENT_NAME}`), which embeds exactly these commands. kubegap compares the sha256 of that file with the document in the account before sending. |"
    )
    L.append(
        '| SSH | k3s, bare metal, kubeadm | the login user; root only for the commands in [`kubegap-sudoers`](kubegap-sudoers) via `sudo -n` | The sudoers file lists the allowed root commands one by one. Anything not listed fails and the section is reported as "no permission". |'
    )
    L.append(
        "| DaemonSet | GKE, AKS, anything without SSM or SSH | root inside the privileged pod from [`daemonset.yaml`](daemonset.yaml), as `kubectl exec … chroot /host /bin/sh -c <command>` | No enforcement beyond this list; the pod runs the same commands as the other two backends. Delete the DaemonSet after the audit. |"
    )
    L.append("")
    L.append("## Built-in probes (`lib/node.py`)")
    L.append("")
    for c in builtin:
        L.append(f"### `{c['step']}`")
        L.append("")
        L.append(c["note"] + ".")
        L.append("")
        L.append("```sh")
        L.append(c["text"].replace(";echo", ";\necho"))
        L.append("```")
        L.append("")
    L.append("## Collector node steps (`type: node` in `collectors/*/collect.yaml`)")
    L.append("")
    L.append("| Step | Nodes | Needs | Output in the snapshot |")
    L.append("|---|---|---|---|")
    for c in node_steps:
        L.append(f"| [`{c['step']}`](#{_anchor(c['step'])}) | {c.get('nodes') or 'all'} | {c.get('requires') or '-'} | `{c.get('out') or '-'}` |")
    L.append("")
    L.append('`Needs` is the privilege table entry (deploy/node-access/README.md) a node must have on the SSH backend; without it the step is skipped as "node permission missing". SSM runs as root and does not use it.')
    L.append("")
    for c in node_steps:
        L.append(f"### `{c['step']}`")
        L.append("")
        if c["kind"] == "script":
            L.append(f"Script `{c['file']}`, sent as is.")
        else:
            L.append(f"One line from `collectors/{c['collector']}/collect.yaml`.")
        L.append("")
        L.append("```sh")
        L.append(c["text"].rstrip("\n"))
        L.append("```")
        L.append("")
    L.append("## Pod metrics fallback (`type: pod-metrics`)")
    L.append("")
    L.append(
        "These steps first read `/metrics` through the apiserver pod proxy. When the proxy is blocked by the node security group, kubegap runs the curl below from inside a node (the pod network is reachable from any node). `<podIp>` is the pod's IP from `kubectl get pod`; port, path and the metric filter are fixed per step."
    )
    L.append("")
    L.append("| Step | Port | Path | Pods |")
    L.append("|---|---|---|---|")
    for c in pm:
        L.append(f"| `{c['step']}` | {c['port']} | `{c['path']}` | `{c.get('namespace') or '-'}` / `{c.get('selector') or '-'}` |")
    L.append("")
    for c in pm:
        L.append(f"### `{c['step']}`")
        L.append("")
        L.append("```sh")
        L.append(c["text"])
        L.append("```")
        L.append("")
    L.append("## Root commands allowed over SSH (`kubegap-sudoers`)")
    L.append("")
    L.append("Installed by the node owner as `/etc/sudoers.d/kubegap`. Only these exact command lines run as root; the scripts above call them with `sudo -n` and fall back to an empty section when one is refused.")
    L.append("")
    L.append("```")
    L.append(SUDOERS_PATH.read_text(encoding="utf-8").rstrip("\n"))
    L.append("```")
    return "\n".join(L) + "\n"


def _anchor(s: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", s.lower().replace("/", ""))


# ---------- SSM document ----------


def render_ssm_document(cmds: list[dict] | None = None) -> str:
    """SSM Command document (schema 2.2, one aws:runShellScript step). `step` is restricted to the list; `podIp` to an IPv4 address; `executionTimeout` to digits. The embedded shell dispatches with `case`."""
    cmds = cmds if cmds is not None else node_commands()
    for c in cmds:
        if "{{" in c["text"]:
            raise ValueError(f"{c['step']}: '{{{{' is not allowed in node commands (SSM would treat it as a parameter reference)")
    steps = [c["step"] for c in cmds]
    body: list[str] = ['case "{{ step }}" in']
    for c in cmds:
        body.append(f"{c['step']})")
        if c["kind"] == "pod-metrics":
            text = pod_metrics_cmd("{{ podIp }}", c["port"], c["path"], c["keep"])
        else:
            text = c["text"].rstrip("\n")
        body += ["  " + ln if ln else "" for ln in text.split("\n")]
        body.append("  ;;")
    body += ["*)", '  echo "kubegap: unknown step {{ step }}" >&2; exit 2', "  ;;", "esac"]
    ind = " " * 10
    L = [
        "# kubegap read-only node inspection, as an SSM Command document.",
        "# Generated by `scripts/kubegap node-commands --ssm-document` from collectors/*/collect.yaml and lib/node.py; tests/test_node_commands.py fails when it is stale.",
        "# The IAM policy (deploy/permissions/iam-policy.json) allows ssm:SendCommand on this document only, so the commands below are all a key with that policy can run on a node.",
        "# Install once per account and region (needs ssm:CreateDocument, ssm:UpdateDocument, ssm:UpdateDocumentDefaultVersion and ssm:ListDocumentVersions; none of these is in the read-only policy):",
        f"#   aws ssm create-document --name {DOCUMENT_NAME} --document-type Command --document-format YAML --content file://deploy/permissions/ssm-document.yaml",
        "# After a kubegap update that changes this file:",
        f"#   aws ssm update-document --name {DOCUMENT_NAME} --document-version '$LATEST' --document-format YAML --content file://deploy/permissions/ssm-document.yaml",
        f"#   aws ssm update-document-default-version --name {DOCUMENT_NAME} --document-version <new version>",
        "# `kubegap setup --install-ssm-document` runs these for you with the current AWS credentials.",
        'schemaVersion: "2.2"',
        f"description: kubegap read-only node inspection. step selects one of {len(steps)} fixed read commands; podIp is the only free value. Generated from the kubegap repository, do not edit by hand.",
        "parameters:",
        "  step:",
        "    type: String",
        "    description: Which fixed read command to run.",
        "    allowedValues:",
    ]
    L += [f"      - {s}" for s in steps]
    L += [
        "  podIp:",
        "    type: String",
        "    description: Pod IP for the pod-metrics curl steps. Ignored by the other steps.",
        "    default: 127.0.0.1",
        f"    allowedPattern: '{IPV4_PATTERN}'",
        "  executionTimeout:",
        "    type: String",
        "    description: Seconds before the command is stopped.",
        "    default: '600'",
        "    allowedPattern: '^[0-9]{1,4}$'",
        "mainSteps:",
        "  - action: aws:runShellScript",
        "    name: kubegapRead",
        "    precondition:",
        "      StringEquals:",
        "        - platformType",
        "        - Linux",
        "    inputs:",
        "      timeoutSeconds: '{{ executionTimeout }}'",
        "      runCommand:",
        "        - |",
    ]
    L += [(ind + ln) if ln else "" for ln in body]
    return "\n".join(L) + "\n"


def document_sha256(text: str | None = None) -> str:
    data = (text if text is not None else DOCUMENT_PATH.read_text(encoding="utf-8")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ---------- the document in the account ----------


def document_status(profile: str | None, region: str | None, log=None) -> dict:
    """Compare the document in the account with deploy/permissions/ssm-document.yaml. Keys: present (True/False/None=could not read), current, account_hash, local_hash, version, error, denied."""
    from . import aws as _aws

    local = document_sha256()
    d, r = _aws.aws_json(["ssm", "describe-document", "--name", DOCUMENT_NAME], profile=profile, region=region, timeout=30, id="ssm.describe-document", log=log)
    if d is None:
        err = (r.error or "") + " " + (r.stderr or "")
        if "InvalidDocument" in err:
            return {"present": False, "current": False, "local_hash": local, "account_hash": None, "version": None, "error": None}
        return {"present": None, "current": False, "local_hash": local, "account_hash": None, "version": None, "error": _aws._why(r), "denied": "AccessDenied" in err or "not authorized" in err}
    doc = d.get("Document") or {}
    acct = doc.get("Hash")
    return {"present": True, "current": acct == local, "local_hash": local, "account_hash": acct, "version": doc.get("DocumentVersion"), "default_version": doc.get("DefaultVersion"), "error": None}


def install_document(profile: str | None, region: str | None, log=None) -> dict:
    """Create the document, or upload the local content as a new version and make it the default. The only write calls in kubegap; run by `kubegap setup --install-ssm-document` after the user agreed. Returns {ok, action, version, error}."""
    from . import aws as _aws

    st = document_status(profile, region, log=log)
    if st.get("current"):
        return {"ok": True, "action": "unchanged", "version": st.get("version"), "error": None}
    if st.get("present") is None:
        return {"ok": False, "action": "describe", "version": None, "error": f"cannot read the document: {st.get('error')}"}
    kw = {"profile": profile, "region": region, "timeout": 60, "log": log}
    content = f"file://{DOCUMENT_PATH}"
    if st.get("present") is False:
        d, r = _aws.aws_json(["ssm", "create-document", "--name", DOCUMENT_NAME, "--document-type", "Command", "--document-format", "YAML", "--content", content], id="ssm.create-document", **kw)
        if d is None:
            return {"ok": False, "action": "create", "version": None, "error": _aws._why(r)}
        action, ver = "create", (d.get("DocumentDescription") or {}).get("DocumentVersion")
    else:
        # A version with the local content may already exist (an earlier run uploaded it but could not switch the default version). update-document would then fail with DuplicateDocumentContent, so look first.
        d, r = _aws.aws_json(["ssm", "list-document-versions", "--name", DOCUMENT_NAME], id="ssm.list-document-versions", **kw)
        have = [v.get("DocumentVersion") for v in ((d or {}).get("DocumentVersions") or []) if v.get("Hash") == st["local_hash"]]
        if have:
            action, ver = "switch-default", have[0]
        else:
            d, r = _aws.aws_json(["ssm", "update-document", "--name", DOCUMENT_NAME, "--document-version", "$LATEST", "--document-format", "YAML", "--content", content], id="ssm.update-document", **kw)
            if d is None:
                return {"ok": False, "action": "update", "version": None, "error": _aws._why(r)}
            action, ver = "update", (d.get("DocumentDescription") or {}).get("DocumentVersion")
        if not ver:
            return {"ok": False, "action": action, "version": None, "error": "SSM returned no document version"}
        d2, r2 = _aws.aws_json(["ssm", "update-document-default-version", "--name", DOCUMENT_NAME, "--document-version", str(ver)], id="ssm.update-document-default-version", **kw)
        if d2 is None:
            return {
                "ok": False,
                "action": action,
                "version": ver,
                "error": f"version {ver} is uploaded but could not be made the default (ssm:UpdateDocumentDefaultVersion): {_aws._why(r2)}. Rerun after fixing the permission; nothing is uploaded twice",
            }
    # Verify instead of trusting: if the default version still differs from the local file, say so and stop rather than uploading again on every run.
    after = document_status(profile, region, log=log)
    if not after.get("current"):
        return {
            "ok": False,
            "action": action,
            "version": ver,
            "error": f"version {ver} is in place but describe-document reports hash {after.get('account_hash')} while the local file is {after.get('local_hash')}. Not retrying; please report this",
        }
    return {"ok": True, "action": action, "version": ver, "error": None}


def missing_document_message(st: dict, profile: str | None, region: str | None) -> str:
    where = f"{'profile ' + profile if profile else 'default profile'}, region {region or 'default'}"
    if st.get("present") is False:
        return f"SSM document {DOCUMENT_NAME} is not in the account ({where}). Node OS checks are skipped. Install it with `kubegap setup --install-ssm-document` (needs ssm:CreateDocument, ssm:UpdateDocument, ssm:UpdateDocumentDefaultVersion and ssm:ListDocumentVersions on your current credentials) or with the aws commands in deploy/permissions/ssm-document.yaml"
    if st.get("present") is None:
        hint = " The IAM policy needs ssm:DescribeDocument." if st.get("denied") else ""
        return f"could not read SSM document {DOCUMENT_NAME} ({where}): {st.get('error')}.{hint} Node OS checks are skipped"
    return f"SSM document {DOCUMENT_NAME} in the account ({where}) differs from deploy/permissions/ssm-document.yaml (kubegap was updated). Node OS checks are skipped until it is updated: `kubegap setup --install-ssm-document`"


def as_json(cmds: list[dict] | None = None) -> str:
    return json.dumps(cmds if cmds is not None else node_commands(), ensure_ascii=False, indent=1)

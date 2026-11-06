"""Run commands on nodes.

The node OS layer (kernel log, sysctl, containerd state, disk paths) is invisible to kubectl. This module wraps the backends
behind one interface, `run_on_node(node, cmd)`:
- ssm : EKS. `aws ssm send-command` with the kubegap-node-read document (deploy/permissions/ssm-document.yaml) → `get-command-invocation` polling.
                The document embeds every node command; the caller names a `step` and the document runs that fixed command. The IAM policy allows SendCommand on
                that document only, so the key cannot run anything else. Before the first send, the sha256 of the local document file is compared with the one in
                the account; when it is missing or different every node step fails with one message telling the user to run `kubegap setup --install-ssm-document`.
                Works only for nodes whose IAM role has SSM permissions and whose agent is registered. Unregistered nodes come back as "not registered with SSM".
- ssh : small k3s cluster / bare metal. `ssh -o BatchMode=yes` (no password prompt). The host is chosen from config.yaml `ssh.hosts.<node>` → node Hostname →
                InternalIP, in that order. User, key and port come from config.yaml `ssh.user/key/port`; when empty, ~/.ssh/config applies.
                Host keys are checked strictly: only a node whose key is already in known_hosts is reached (`StrictHostKeyChecking=yes`). The user accepts
                a new node once by hand, or sets `ssh.accept_new_hosts: true` to let ssh store first-seen keys (`accept-new`).
- none: no backend (platforms with neither SSM nor SSH, such as GKE and AKS). Only node-exporter metrics are used. A backend for them is one more
                branch of `run_on_node` that runs the same command list; contributions welcome.
The detection result (inventory.node_access.method) picks the backend; config.yaml `node_access` overrides it.

Read-only principle: the only commands sent here are the read commands defined by collectors (node entries in collect.yaml) and the two probes in
lib/nodecommands.py. deploy/node-access/COMMANDS.md lists all of them. On SSM the document enforces the list; on SSH the node's sudoers file limits the
root commands.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from . import aws as _aws
from . import nodecommands, shell
from .config import Config
from .runlog import RunLog

SSM_DOCUMENT = nodecommands.DOCUMENT_NAME


@dataclass
class NodeResult:
    node: str
    backend: str
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    seconds: float = 0.0
    detail: dict = field(default_factory=dict)


def ssh_argv(ssh_cfg: dict, host: str, cmd: str) -> list[str]:
    """The ssh command line for one node. BatchMode so no password prompt; host keys are checked strictly by default (only nodes already in
    known_hosts are reached). `ssh.accept_new_hosts: true` relaxes that to accept-new, which stores a first-seen key without asking; a stored key that
    changed is still refused."""
    strict = "accept-new" if ssh_cfg.get("accept_new_hosts") is True else "yes"
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", f"StrictHostKeyChecking={strict}"]
    if ssh_cfg.get("key"):
        argv += ["-i", str(ssh_cfg["key"]).replace("~", str(Path.home()), 1)]
    if ssh_cfg.get("port"):
        argv += ["-p", str(ssh_cfg["port"])]
    # If a hosts value is `user@address`, use that user (when usernames differ per node). Otherwise ssh.user, and failing that ~/.ssh/config
    target = host if "@" in host else (f"{ssh_cfg['user']}@{host}" if ssh_cfg.get("user") else host)
    return [*argv, target, "--", cmd]


def ssh_hand_command(ssh_cfg: dict, host: str) -> str:
    """The command a user runs once to see and store a node's host key, in the same form kubegap connects with. OpenSSH files a
    non-default port under `[address]:port`, so the port must match."""
    argv = ssh_argv(ssh_cfg, host, "true")
    port = [f"-p {argv[i + 1]}" for i, a in enumerate(argv) if a == "-p"]
    return " ".join(["ssh", *port, argv[-3], "true"])


class NodeAccess:
    def __init__(self, inv: dict, cfg: Config, log: RunLog | None = None):
        self.inv, self.cfg, self.log = inv, cfg, log
        na = inv.get("node_access") or {}
        self.method = cfg.get("node_access") or na.get("method") or "none"
        self.nodes = {n["name"]: n for n in (inv.get("nodes") or {}).get("nodes", [])}
        eks = (inv.get("cluster") or {}).get("eks") or {}
        self.aws_profile = cfg.get("aws_profile") or eks.get("profile")
        self.aws_region = cfg.get("aws_region") or eks.get("region")
        self.ssm_registered = {x["node"]: x.get("instance_id") for x in na.get("ssm_registered", [])}
        self.ssm_unregistered = {x["node"] for x in na.get("ssm_unregistered") or []}
        self.ssh = cfg.get("ssh") or {}

    # ---------- public interface ----------
    def run_on_node(self, node: str, cmd: str, timeout: float = 60, id: str | None = None, collector: str | None = None, *, step: str | None = None, params: dict | None = None) -> NodeResult:
        """`cmd` is the shell text (SSH sends it as is). `step` is the same command's name in the SSM document (`<collector>/<step id>`, `probe`, `capabilities`); the SSM backend sends only that name plus `params` (podIp), never the text."""
        if node not in self.nodes:
            return NodeResult(node, self.method, False, error=f"node {node} not in inventory")
        if self.method == "ssm":
            r = self._ssm(node, step, params or {}, timeout)
        elif self.method == "ssh":
            r = self._ssh(node, cmd, timeout)
        else:
            r = NodeResult(node, self.method, False, error=f"no node command backend (method={self.method}). Using node-exporter metrics only")
        if self.log is not None and id is not None:
            self.log.command(id=f"{id}.{node}", cmd=[f"node:{r.backend}", node, cmd], code=0 if r.ok else 1, seconds=r.seconds, error=r.error, collector=collector)
        return r

    def run_on_all(self, cmd: str, timeout: float = 60, id: str | None = None, collector: str | None = None, *, step: str | None = None, params: dict | None = None) -> dict[str, NodeResult]:
        return {n: self.run_on_node(n, cmd, timeout, id, collector, step=step, params=params) for n in self.nodes}

    CAPABILITY_SCRIPT = nodecommands.CAPABILITY_SCRIPT
    PROBE_CMD = nodecommands.PROBE_CMD

    def capabilities(self) -> dict[str, dict]:
        """Which read permissions each node has (readiness of stages 1 and 2 in deploy/node-access/README.md). yes=works as-is, sudo=works via sudoers, no=no permission."""
        out = {}
        for n, r in self.run_on_all(self.CAPABILITY_SCRIPT, timeout=30, id="node.capabilities", step="capabilities").items():
            caps = {}
            for line in r.stdout.splitlines():
                if line.startswith("cap:") and "=" in line:
                    k, v = line[4:].split("=", 1)
                    caps[k] = v.strip()
            out[n] = {"ok": r.ok, "backend": r.backend, "error": r.error, "caps": caps}
        return out

    def probe(self) -> dict[str, NodeResult]:
        """Send the probe (echo, uname, hostname) to every node to confirm access. `kubegap nodes` prints the result."""
        return self.run_on_all(self.PROBE_CMD, timeout=30, id="node.probe", step="probe")

    # ---------- SSM ----------
    def _instance_id(self, node: str) -> str | None:
        iid = self.ssm_registered.get(node)
        if iid:
            return iid
        m = re.search(r"(i-[0-9a-f]+)$", (self.nodes[node].get("provider_id") or ""))
        return m.group(1) if m else None

    @cached_property
    def ssm_document(self) -> dict:
        """The kubegap-node-read document in the account compared with the local file, read once per NodeAccess (see lib/nodecommands.document_status)."""
        return nodecommands.document_status(self.aws_profile, self.aws_region, log=self.log)

    def _ssm(self, node: str, step: str | None, params: dict, timeout: float) -> NodeResult:
        t0 = time.monotonic()
        if node in self.ssm_unregistered:
            return NodeResult(node, "ssm", False, error="node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore")
        if not step:
            return NodeResult(node, "ssm", False, error=f"the SSM backend runs only the steps of the {SSM_DOCUMENT} document (deploy/node-access/COMMANDS.md); a free command cannot be sent")
        if not self.ssm_document.get("current"):
            return NodeResult(node, "ssm", False, error=nodecommands.missing_document_message(self.ssm_document, self.aws_profile, self.aws_region))
        iid = self._instance_id(node)
        if not iid:
            return NodeResult(node, "ssm", False, error="could not find an instance id in providerID")
        # Standard output is truncated at 24,000 characters (---Output truncated---). This is why the scripts limit line counts per section.
        # --document-hash makes SSM refuse the call unless the default version is exactly the file checked above: no window between describe and send, and no other version can be substituted.
        p = {"step": [step], "executionTimeout": [str(int(max(timeout, 30)))]}
        if params.get("podIp"):
            p["podIp"] = [str(params["podIp"])]
        if params.get("port"):
            p["port"] = [str(int(params["port"]))]  # the discovered metrics port; the document's allowedPattern keeps it to digits (#136)
        d, r = _aws.aws_json(
            [
                "ssm",
                "send-command",
                "--instance-ids",
                iid,
                "--document-name",
                SSM_DOCUMENT,
                "--document-hash",
                self.ssm_document["local_hash"],
                "--document-hash-type",
                "Sha256",
                "--parameters",
                json.dumps(p),
                "--timeout-seconds",
                str(int(max(timeout, 30))),
                "--comment",
                f"kubegap read-only {step}",
            ],
            profile=self.aws_profile,
            region=self.aws_region,
            timeout=30,
        )
        if d is None:
            err = (r.error or "") + " " + (r.stderr or "")
            if "AccessDenied" in err or "not authorized" in err:
                return NodeResult(
                    node,
                    "ssm",
                    False,
                    error=f"send-command denied for {iid}. The IAM policy allows SendCommand only on instances tagged kubernetes.io/cluster/<cluster name>=owned (deploy/permissions/iam-policy.json); check the tag on this node and the document name {SSM_DOCUMENT}: {r.stderr.strip()[-200:]}",
                    seconds=time.monotonic() - t0,
                )
        if d is None:
            return NodeResult(node, "ssm", False, error=f"send-command failed: {r.error or r.stderr.strip()[-300:]}", seconds=time.monotonic() - t0)
        cid = (d.get("Command") or {}).get("CommandId")
        deadline = time.monotonic() + timeout + 15
        status, inv = "Pending", {}
        # SSM is asynchronous. It usually finishes within 2–5 seconds, so poll every second.
        while time.monotonic() < deadline:
            time.sleep(1.0)
            inv, r = _aws.aws_json(["ssm", "get-command-invocation", "--command-id", cid, "--instance-id", iid], profile=self.aws_profile, region=self.aws_region, timeout=30)
            if inv is None:
                if "InvocationDoesNotExist" in (r.stderr or ""):
                    continue  # not registered yet
                return NodeResult(node, "ssm", False, error=f"get-command-invocation failed: {r.error or r.stderr.strip()[-300:]}", seconds=time.monotonic() - t0)
            status = inv.get("Status")
            # the terminal values of CommandInvocationStatus (awscli/botocore/data/ssm/2014-11-06/service-2.json:4621-4632@2.39.3); DeliveryTimedOut and the like are StatusDetails words, never Status
            if status in ("Success", "Failed", "Cancelled", "TimedOut", "Cancelling"):
                break
        secs = time.monotonic() - t0
        if status != "Success":
            return NodeResult(
                node,
                "ssm",
                False,
                stdout=inv.get("StandardOutputContent", ""),
                stderr=inv.get("StandardErrorContent", ""),
                error=f"SSM status {status}: {inv.get('StatusDetails')}",
                seconds=secs,
                detail={"command_id": cid, "instance_id": iid},
            )
        return NodeResult(node, "ssm", True, stdout=inv.get("StandardOutputContent", ""), stderr=inv.get("StandardErrorContent", ""), seconds=secs, detail={"command_id": cid, "instance_id": iid})

    # ---------- SSH ----------
    def _ssh_host(self, node: str) -> str:
        hosts = self.ssh.get("hosts") or {}
        if node in hosts:
            return str(hosts[node])
        n = self.nodes[node]
        return n.get("name") if self.ssh.get("prefer_hostname") else (n.get("internal_ip") or n.get("name"))

    def _ssh(self, node: str, cmd: str, timeout: float) -> NodeResult:
        host = self._ssh_host(node)
        argv = ssh_argv(self.ssh, host, cmd)
        r = shell.run(argv, timeout=timeout + 10)
        if not r.ok:
            err = r.error or r.stderr.strip()[-300:] or f"exit {r.code}"
            hint, kind = "", "other"
            if "Host key verification failed" in err or "REMOTE HOST IDENTIFICATION HAS CHANGED" in err:
                kind = "host-key"
                hint = f" → the host key of {host} is not in known_hosts, or differs from the stored one. Connect once by hand (`{ssh_hand_command(self.ssh, host)}`) to check and store the key, or set config.yaml ssh.accept_new_hosts: true to store first-seen keys automatically"
            elif "Permission denied" in err:
                kind = "auth"
                hint = " → check config.yaml ssh.user / ssh.key (password login is not supported)"
            elif "Could not resolve" in err or "timed out" in err or "No route" in err:
                kind = "unreachable"
                hint = " → set config.yaml ssh.hosts.<node> to an address reachable from this machine (e.g. a Tailscale IP)"
            return NodeResult(node, "ssh", False, stdout=r.stdout, stderr=r.stderr, error=err + hint, seconds=r.seconds, detail={"host": host, "kind": kind})
        return NodeResult(node, "ssh", True, stdout=r.stdout, stderr=r.stderr, seconds=r.seconds, detail={"host": host})

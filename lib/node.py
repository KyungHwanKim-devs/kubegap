"""Run commands on nodes.

The node OS layer (kernel log, sysctl, containerd state, disk paths) is invisible to kubectl. This module wraps two backends
behind one interface, `run_on_node(node, cmd)`:
- ssm : EKS. `aws ssm send-command` (document AWS-RunShellScript) → `get-command-invocation` polling. Works only for nodes whose IAM role has
                SSM permissions and whose agent is registered. Unregistered nodes come back as "not registered with SSM" (their kernel log checks are marked skipped).
- ssh : small k3s cluster / bare metal. `ssh -o BatchMode=yes` (no password prompt). The host is chosen from config.yaml `ssh.hosts.<node>` → node Hostname →
                InternalIP, in that order. User, key and port come from config.yaml `ssh.user/key/port`; when empty, ~/.ssh/config applies.
- none: platforms without a backend in 1.0 (GKE, AKS). Only node-exporter metrics are used.
The detection result (inventory.node_access.method) picks the backend; config.yaml `node_access` overrides it. A privileged DaemonSet backend is planned.

Read-only principle: the only commands sent here are the read commands defined by collectors (node entries in collect.yaml). This module does not
inspect commands, so the collector definitions are responsible.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from . import aws as _aws
from . import kube as _kube
from . import shell
from .config import Config
from .runlog import RunLog

SSM_DOCUMENT = "AWS-RunShellScript"


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
        self.ssm_unregistered = {x["node"] for x in na.get("ssm_unregistered", [])}
        self.ssh = cfg.get("ssh") or {}

    # ---------- public interface ----------
    def run_on_node(self, node: str, cmd: str, timeout: float = 60, id: str | None = None, collector: str | None = None) -> NodeResult:
        if node not in self.nodes:
            return NodeResult(node, self.method, False, error=f"node {node} not in inventory")
        if self.method == "ssm":
            r = self._ssm(node, cmd, timeout)
        elif self.method == "ssh":
            r = self._ssh(node, cmd, timeout)
        elif self.method == "daemonset":
            r = self._daemonset(node, cmd, timeout)
        else:
            r = NodeResult(node, self.method, False, error=f"no node command backend (method={self.method}). Using node-exporter metrics only")
        if self.log is not None and id is not None:
            self.log.command(id=f"{id}.{node}", cmd=[f"node:{r.backend}", node, cmd], code=0 if r.ok else 1, seconds=r.seconds, error=r.error, collector=collector)
        return r

    def run_on_all(self, cmd: str, timeout: float = 60, id: str | None = None, collector: str | None = None) -> dict[str, NodeResult]:
        return {n: self.run_on_node(n, cmd, timeout, id, collector) for n in self.nodes}

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

    def capabilities(self) -> dict[str, dict]:
        """Which read permissions each node has (readiness of stages 1 and 2 in deploy/node-access/README.md). yes=works as-is, sudo=works via sudoers, no=no permission."""
        out = {}
        for n, r in self.run_on_all(self.CAPABILITY_SCRIPT, timeout=30, id="node.capabilities").items():
            caps = {}
            for line in r.stdout.splitlines():
                if line.startswith("cap:") and "=" in line:
                    k, v = line[4:].split("=", 1)
                    caps[k] = v.strip()
            out[n] = {"ok": r.ok, "backend": r.backend, "error": r.error, "caps": caps}
        return out

    def probe(self) -> dict[str, NodeResult]:
        """Send `echo ok; uname -r` to every node to confirm access. setup and discover record the result."""
        return self.run_on_all("echo kubegap-ok; uname -r; hostname", timeout=30, id="node.probe")

    # ---------- DaemonSet (kubectl exec → chroot /host) ----------
    DS_NAMESPACE, DS_LABEL = "kubegap", "app.kubernetes.io/name=kubegap-node-reader"

    @cached_property
    def _ds_pods(self) -> dict[str, str]:
        """node name -> Running kubegap-node-reader pod name. Listed once per NodeAccess instance (only when the daemonset backend is used)."""
        d, _ = _kube.kubectl_json(["get", "pods", "-n", self.DS_NAMESPACE, "-l", self.DS_LABEL, "-o", "json"], context=self.inv.get("context") or self.cfg.get("context"), timeout=30)
        return {p_["spec"].get("nodeName"): p_["metadata"]["name"] for p_ in ((d or {}).get("items") or []) if (p_.get("status") or {}).get("phase") == "Running"}

    def _ds_pod(self, node: str) -> str | None:
        return self._ds_pods.get(node)

    def _daemonset(self, node: str, cmd: str, timeout: float) -> NodeResult:
        """Run node commands with `chroot /host` inside the privileged pod from deploy/node-access/daemonset.yaml. Sending only read commands is the caller's (collector script's) responsibility; the same scripts as SSM/SSH are used."""
        t0 = time.monotonic()
        pod = self._ds_pod(node)
        if not pod:
            return NodeResult(node, "daemonset", False, error="no Running kubegap-node-reader pod on this node")
        r = _kube.kubectl(["exec", "-n", self.DS_NAMESPACE, pod, "--", "chroot", "/host", "/bin/sh", "-c", cmd], context=self.inv.get("context") or self.cfg.get("context"), timeout=timeout + 15)
        return NodeResult(node, "daemonset", r.ok, stdout=r.stdout, stderr=r.stderr, error=None if r.ok else (r.error or r.stderr.strip()[-300:]), seconds=round(time.monotonic() - t0, 1), detail={"pod": pod})

    # ---------- SSM ----------
    def _instance_id(self, node: str) -> str | None:
        iid = self.ssm_registered.get(node)
        if iid:
            return iid
        m = re.search(r"(i-[0-9a-f]+)$", (self.nodes[node].get("provider_id") or ""))
        return m.group(1) if m else None

    def _ssm(self, node: str, cmd: str, timeout: float) -> NodeResult:
        t0 = time.monotonic()
        if node in self.ssm_unregistered:
            return NodeResult(node, "ssm", False, error="node not registered with SSM. The node IAM role needs AmazonSSMManagedInstanceCore")
        iid = self._instance_id(node)
        if not iid:
            return NodeResult(node, "ssm", False, error="could not find an instance id in providerID")
        # AWS-RunShellScript joins the elements of commands with newlines and runs them as one script. Multi-line scripts are passed line by line.
        # Standard output is truncated at 24,000 characters (---Output truncated---). This is why the script limits line counts per section.
        lines = cmd.split("\n") if "\n" in cmd else [cmd]
        params = json.dumps({"commands": lines, "executionTimeout": [str(int(max(timeout, 30)))]})
        d, r = _aws.aws_json(
            ["ssm", "send-command", "--instance-ids", iid, "--document-name", SSM_DOCUMENT, "--parameters", params, "--timeout-seconds", str(int(max(timeout, 30))), "--comment", "kubegap read-only"],
            profile=self.aws_profile,
            region=self.aws_region,
            timeout=30,
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
            if status in ("Success", "Failed", "Cancelled", "TimedOut", "Cancelling", "DeliveryTimedOut", "ExecutionTimedOut", "Undeliverable", "Terminated"):
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
        argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new"]
        if self.ssh.get("key"):
            argv += ["-i", str(self.ssh["key"]).replace("~", str(Path.home()), 1)]
        if self.ssh.get("port"):
            argv += ["-p", str(self.ssh["port"])]
        # If a hosts value is `user@address`, use that user (when usernames differ per node). Otherwise ssh.user, and failing that ~/.ssh/config
        target = host if "@" in host else (f"{self.ssh['user']}@{host}" if self.ssh.get("user") else host)
        argv += [target, "--", cmd]
        r = shell.run(argv, timeout=timeout + 10)
        if not r.ok:
            err = r.error or r.stderr.strip()[-300:] or f"exit {r.code}"
            hint = ""
            if "Permission denied" in err:
                hint = " → check config.yaml ssh.user / ssh.key (password login is not supported)"
            elif "Could not resolve" in err or "timed out" in err or "No route" in err:
                hint = " → set config.yaml ssh.hosts.<node> to an address reachable from this machine (e.g. a Tailscale IP)"
            return NodeResult(node, "ssh", False, stdout=r.stdout, stderr=r.stderr, error=err + hint, seconds=r.seconds, detail={"host": host})
        return NodeResult(node, "ssh", True, stdout=r.stdout, stderr=r.stderr, seconds=r.seconds, detail={"host": host})

"""SSH command line: strict host key checking by default, `ssh.accept_new_hosts: true` relaxes it, the other options stay as they were."""

from __future__ import annotations

from pathlib import Path

from lib.node import ssh_argv


def _opt(argv, name):
    for i, a in enumerate(argv):
        if a == "-o" and argv[i + 1].startswith(name + "="):
            return argv[i + 1].split("=", 1)[1]
    return None


def test_default_is_strict():
    argv = ssh_argv({}, "10.0.0.1", "uname -r")
    assert _opt(argv, "StrictHostKeyChecking") == "yes"
    assert _opt(argv, "BatchMode") == "yes"
    assert argv[-3:] == ["10.0.0.1", "--", "uname -r"]


def test_accept_new_hosts_relaxes():
    assert _opt(ssh_argv({"accept_new_hosts": True}, "h", "x"), "StrictHostKeyChecking") == "accept-new"


def test_only_true_relaxes():
    for v in (False, None, "true", "yes", 1):
        assert _opt(ssh_argv({"accept_new_hosts": v}, "h", "x"), "StrictHostKeyChecking") == "yes", v


def test_user_key_port_and_per_host_user():
    argv = ssh_argv({"user": "ubuntu", "key": "~/.ssh/id_ed25519", "port": 2222}, "10.0.0.1", "x")
    assert argv[argv.index("-i") + 1] == str(Path.home() / ".ssh/id_ed25519")
    assert argv[argv.index("-p") + 1] == "2222"
    assert argv[-3] == "ubuntu@10.0.0.1"
    assert ssh_argv({"user": "ubuntu"}, "admin@10.0.0.2", "x")[-3] == "admin@10.0.0.2"


def test_hand_command_matches_port_and_user():
    from lib.node import ssh_hand_command

    assert ssh_hand_command({}, "10.0.0.1") == "ssh 10.0.0.1 true"
    assert ssh_hand_command({"user": "ubuntu", "port": 2222}, "10.0.0.1") == "ssh -p 2222 ubuntu@10.0.0.1 true"


def test_refused_host_key_hint(monkeypatch):
    from lib import node as node_mod
    from lib.shell import Result

    monkeypatch.setattr(node_mod.shell, "run", lambda argv, **kw: Result(argv, code=255, stderr="No ED25519 host key is known for 10.0.0.1 and you have requested strict checking.\nHost key verification failed."))
    na = node_mod.NodeAccess({"node_access": {"method": "ssh"}, "nodes": {"nodes": [{"name": "n1", "internal_ip": "10.0.0.1"}]}}, {"ssh": {"user": "ubuntu", "port": 2222}})
    r = na.run_on_node("n1", "true")
    assert not r.ok
    assert "known_hosts" in r.error and "`ssh -p 2222 ubuntu@10.0.0.1 true`" in r.error and "accept_new_hosts" in r.error

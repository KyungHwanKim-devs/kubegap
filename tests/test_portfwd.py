"""`lib.portfwd.PortForward` lets kubectl choose the local port (#99) and keeps the forward usable while kubectl talks.

A fake `kubectl` first on PATH plays the parts kubectl can play: it binds the port the arguments ask for (0 = any free
one), prints the `Forwarding from` lines kubectl prints for `--address localhost` (127.0.0.1 and ::1), writes the port it
got to a file so the test can compare, and then serves connections, printing `Handling connection for <port>` per
connection as kubectl does; or it exits at once with an error; or it binds but never prints the line.
"""

from __future__ import annotations

import os
import socket
import stat
import textwrap
from pathlib import Path

import pytest

from lib import portfwd
from lib.portfwd import PortForward, _port_open

FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, select, socket, sys
    mode = os.environ.get("FAKE_KUBECTL_MODE", "serve")
    if mode == "exit":
        sys.stderr.write("Unable to listen on port 0: address already in use\\n")
        sys.exit(1)
    spec = sys.argv[-1]                      # "<local>:<remote>", the last argument kubectl gets
    local, remote = spec.split(":")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", int(local)))
    srv.listen(16)
    port = srv.getsockname()[1]
    if os.environ.get("FAKE_KUBECTL_PORTFILE"):
        with open(os.environ["FAKE_KUBECTL_PORTFILE"], "w") as f:
            f.write(str(port))
    if mode != "silent":
        sys.stdout.write(f"Forwarding from 127.0.0.1:{port} -> {remote}\\n")
        sys.stdout.write(f"Forwarding from [::1]:{port} -> {remote}\\n")
        sys.stdout.flush()
    if mode == "chatty":                     # what kubectl prints over a long collection, all at once
        for _ in range(int(os.environ.get("FAKE_KUBECTL_LINES", "20000"))):
            sys.stdout.write(f"Handling connection for {port}\\n")
        sys.stdout.flush()
    while True:
        r, _, _ = select.select([srv], [], [], 60)
        for s in r:
            c, _ = s.accept()
            sys.stdout.write(f"Handling connection for {port}\\n")
            sys.stdout.flush()
            c.sendall(b"ok")                 # a byte back: proof that the fake got past its writes and serves
            c.close()
    """
)


@pytest.fixture
def fake_kubectl(tmp_path, monkeypatch):
    path = tmp_path / "bin" / "kubectl"
    path.parent.mkdir()
    path.write_text(FAKE)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(path.parent) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.delenv("FAKE_KUBECTL_MODE", raising=False)
    monkeypatch.setenv("FAKE_KUBECTL_PORTFILE", str(tmp_path / "port"))
    return tmp_path / "port"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _served(port: int, timeout: float = 10) -> bool:
    """Connect and wait for the byte the fake sends once it serves; False when nothing comes back in time."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return s.recv(2) == b"ok"
        except OSError:
            return False


def test_kubectl_chooses_the_port_and_the_class_reads_it(fake_kubectl):
    pf = PortForward(None, "monitoring", "prometheus", 9090)
    assert pf.local_port is None, "no port is picked before kubectl reports one"
    assert pf.start() is True, pf.error
    try:
        assert pf.proc.args[-1] == "0:9090", "kubectl is asked for any free local port"
        assert pf.local_port == int(fake_kubectl.read_text()), "the port is the one kubectl printed"
        assert pf.url == f"http://127.0.0.1:{pf.local_port}"
        assert _served(pf.local_port)
    finally:
        pf.stop()
    assert pf.proc is None
    assert not _port_open(pf.local_port), "stop() ends the process and with it the listener"


def test_an_explicit_local_port_is_still_honoured(fake_kubectl):
    port = _free_port()
    pf = PortForward(None, "monitoring", "loki", 3100, local_port=port)
    assert pf.start() is True, pf.error
    try:
        assert pf.proc.args[-1] == f"{port}:3100"
        assert pf.local_port == port == int(fake_kubectl.read_text())
    finally:
        pf.stop()


def test_a_second_start_does_not_start_a_second_process(fake_kubectl):
    pf = PortForward(None, "monitoring", "prometheus", 9090)
    assert pf.start() is True, pf.error
    try:
        proc, port = pf.proc, pf.local_port
        assert pf.start() is True
        assert pf.proc is proc and pf.local_port == port
    finally:
        pf.stop()


def test_an_early_exit_is_reported_with_the_exit_code_and_stderr(fake_kubectl, monkeypatch):
    monkeypatch.setenv("FAKE_KUBECTL_MODE", "exit")
    pf = PortForward(None, "monitoring", "prometheus", 9090, wait=5)
    assert pf.start() is False
    assert pf.proc is None, "no child process is left behind"
    assert "code 1" in pf.error and "address already in use" in pf.error


def test_no_forwarding_line_within_the_wait_is_its_own_error(fake_kubectl, monkeypatch):
    monkeypatch.setenv("FAKE_KUBECTL_MODE", "silent")
    pf = PortForward(None, "monitoring", "prometheus", 9090, wait=1.5)
    assert pf.start() is False
    assert pf.error == "kubectl did not report a local port within 1.5s"
    assert pf.proc is None


def test_stdout_is_drained_so_a_talkative_kubectl_does_not_block(fake_kubectl, monkeypatch):
    # 20,000 `Handling connection` lines are about 600 KB, far past a pipe buffer. The fake listens before it writes, so
    # a bare TCP connect would succeed even with kubectl stuck in its write (the kernel completes the handshake from the
    # backlog); only the byte the fake sends after the burst proves the writes went through, which needs a reader.
    monkeypatch.setenv("FAKE_KUBECTL_MODE", "chatty")
    pf = PortForward(None, "monitoring", "prometheus", 9090)
    assert pf.start() is True, pf.error
    try:
        assert _served(pf.local_port), "kubectl never got past its stdout writes: the pipe is not being drained"
        assert _served(pf.local_port)
    finally:
        pf.stop()
    assert pf.proc is None


def test_the_forwarding_line_regex_takes_the_ipv4_line_only():
    # kubectl prints one line per bound address for the default `--address localhost`
    # (kubernetes/kubernetes staging/src/k8s.io/client-go/tools/portforward/portforward.go:304@v1.34.2)
    assert portfwd.FORWARDING_RE.match("Forwarding from 127.0.0.1:54321 -> 9090\n").group(1) == "54321"
    assert portfwd.FORWARDING_RE.match("Forwarding from [::1]:54321 -> 9090\n") is None
    assert portfwd.FORWARDING_RE.match("Handling connection for 54321\n") is None


def test_free_port_probing_is_gone():
    assert not hasattr(portfwd, "free_port"), "the port is chosen by kubectl, never probed here (#99)"
    src = Path(portfwd.__file__).read_text()
    assert 'bind(("127.0.0.1", 0))' not in src

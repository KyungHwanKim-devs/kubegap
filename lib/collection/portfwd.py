"""Start `kubectl port-forward` in the background and wait until the local port opens.

setup uses it to verify connectivity; collect keeps it alive during PromQL/LogQL queries. Used as a context manager,
it terminates the process on exit. If the config file provides a URL, that URL is used instead of port-forwarding.

kubectl chooses the local port: the process is started with `0:<remote>` and the port is read from the
`Forwarding from 127.0.0.1:<port> -> <remote>` line kubectl prints on stdout once it has bound the listener
(kubernetes/kubernetes staging/src/k8s.io/client-go/tools/portforward/portforward.go:289-304@v1.34.2; a local port
of 0 means "any free port", documented at lines 80-83 and parsed at line 104 of the same file). Picking a free port
here and handing it over would leave a gap between our close and kubectl's bind in which any other process can take
the port.
"""

from __future__ import annotations

import collections
import re
import socket
import subprocess
import threading
import time

# source: kubernetes/kubernetes staging/src/k8s.io/client-go/tools/portforward/portforward.go:304@v1.34.2
# (`Forwarding from %s -> %d` with net.JoinHostPort(hostname, port)); the default `--address localhost` binds
# 127.0.0.1 and ::1 and prints one line per address
# (kubernetes/kubernetes staging/src/k8s.io/kubectl/pkg/cmd/portforward/portforward.go:118@v1.34.2)
FORWARDING_RE = re.compile(r"^Forwarding from 127\.0\.0\.1:(\d+) -> \d+\s*$")

STDERR_KEEP = 40  # last lines of kubectl's stderr kept for the error message


def _port_open(port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


class PortForward:
    """One `kubectl port-forward svc/<service>` process.

    `url` is valid only after `start()` returned True: without `local_port`, the port is known only once kubectl
    has reported it. `error` says why `start()` returned False.
    """

    def __init__(self, context: str | None, namespace: str, service: str, remote_port: int, local_port: int | None = None, kubeconfig: str | None = None, wait: float = 15.0):
        self.context, self.namespace, self.service, self.remote_port = context, namespace, service, remote_port
        self.local_port: int | None = local_port
        self.kubeconfig = kubeconfig
        self.wait = wait
        self.proc: subprocess.Popen | None = None
        self.error: str | None = None
        self._reported: int | None = None  # the port kubectl printed, set by the stdout reader
        self._stderr: collections.deque[str] = collections.deque(maxlen=STDERR_KEEP)
        self._readers: list[threading.Thread] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.local_port}"

    def _read_stdout(self, proc: subprocess.Popen) -> None:
        # kubectl writes `Forwarding from ...` once per bound address and `Handling connection for <port>` for every
        # connection (portforward.go:344-345@v1.34.2). The pipe must be drained for the life of the process: a full
        # pipe would block kubectl and with it every query that goes through the forward.
        for line in proc.stdout:
            m = FORWARDING_RE.match(line)
            if m and self._reported is None:
                self._reported = int(m.group(1))

    def _read_stderr(self, proc: subprocess.Popen) -> None:
        # Every failed connection is a stderr line too (portforward.go:322,357,380,391,404@v1.34.2): same reason to drain
        for line in proc.stderr:
            self._stderr.append(line.rstrip("\n"))

    def start(self) -> bool:
        if self.proc is not None:  # already started: say whether the first process is still there, never start a second one
            return self.proc.poll() is None
        cmd = ["kubectl"]
        if self.context:
            cmd += ["--context", self.context]
        if self.kubeconfig:
            cmd += ["--kubeconfig", self.kubeconfig]
        cmd += ["-n", self.namespace, "port-forward", f"svc/{self.service}", f"{self.local_port or 0}:{self.remote_port}"]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except OSError as e:
            self.error = str(e)
            return False
        self._readers = [threading.Thread(target=self._read_stdout, args=(self.proc,), daemon=True), threading.Thread(target=self._read_stderr, args=(self.proc,), daemon=True)]
        for t in self._readers:
            t.start()
        # The local port usually opens within about a second. Poll every 0.2s for up to `wait` seconds.
        deadline = time.monotonic() + self.wait
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                code = self.proc.returncode
                self.stop()
                self.error = f"port-forward exited (code {code}): {' | '.join(self._stderr)[-400:]}"
                return False
            port = self.local_port or self._reported
            if port and _port_open(port):
                self.local_port = port
                return True
            time.sleep(0.2)
        if self.local_port:
            self.error = f"local port {self.local_port} did not open within {self.wait:g}s"
        else:
            self.error = f"kubectl did not report a local port within {self.wait:g}s"
        self.stop()
        return False

    def stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        for t in self._readers:  # the process is gone, so the pipes are at EOF and the readers end
            t.join(timeout=5)
        if any(t.is_alive() for t in self._readers):
            return  # never close a stream a reader still holds
        self._readers = []
        for stream in (proc.stdout, proc.stderr):
            if stream:
                stream.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

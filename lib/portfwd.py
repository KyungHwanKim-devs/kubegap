"""Start `kubectl port-forward` in the background and wait until the local port opens.

setup uses it to verify connectivity; collect keeps it alive during PromQL/LogQL queries. Used as a context manager,
it terminates the process on exit. If the config file provides a URL, that URL is used instead of port-forwarding.
"""

from __future__ import annotations

import socket
import subprocess
import time


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_open(port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


class PortForward:
    def __init__(self, context: str | None, namespace: str, service: str, remote_port: int, local_port: int | None = None, kubeconfig: str | None = None, wait: float = 15.0):
        self.context, self.namespace, self.service, self.remote_port = context, namespace, service, remote_port
        self.local_port = local_port or free_port()
        self.kubeconfig = kubeconfig
        self.wait = wait
        self.proc: subprocess.Popen | None = None
        self.error: str | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.local_port}"

    def start(self) -> bool:
        cmd = ["kubectl"]
        if self.context:
            cmd += ["--context", self.context]
        if self.kubeconfig:
            cmd += ["--kubeconfig", self.kubeconfig]
        cmd += ["-n", self.namespace, "port-forward", f"svc/{self.service}", f"{self.local_port}:{self.remote_port}"]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        except OSError as e:
            self.error = str(e)
            return False
        # The local port usually opens within about a second. Poll every 0.2s for up to `wait` seconds.
        deadline = time.monotonic() + self.wait
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                err = (self.proc.stderr.read() if self.proc.stderr else "").strip()
                self.error = f"port-forward exited (code {self.proc.returncode}): {err[-400:]}"
                return False
            if _port_open(self.local_port):
                return True
            time.sleep(0.2)
        self.error = f"local port {self.local_port} did not open within {self.wait}s"
        self.stop()
        return False

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

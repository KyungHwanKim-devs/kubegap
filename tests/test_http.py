"""lib.http never follows a redirect, and a token over plain http to a non-loopback host is warned about once (#83)."""

import http.server
import threading

import pytest

from lib import collect
from lib import http as khttp
from lib.runlog import RunLog


class _Server:
    """A local HTTP server: /a redirects (302 by default), every other path records that it was hit and with which headers."""

    def __init__(self, location=None, code=302):
        self.hits: list[tuple[str, dict]] = []
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/a":
                    self.send_response(code)
                    self.send_header("Location", location or f"http://127.0.0.1:{server.port}/b")
                    self.end_headers()
                    return
                server.hits.append((self.path, dict(self.headers)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = _Server()
    yield s
    s.close()


def test_redirect_is_refused_and_the_target_is_never_requested(server):
    r = khttp.get(f"http://127.0.0.1:{server.port}/a", headers={"Authorization": "Bearer x"})
    assert r.ok is False
    assert r.status == 302
    assert r.error == "redirect refused: 127.0.0.1"
    assert r.body == ""
    assert server.hits == [], "the Location was requested, with the Authorization header"


def test_a_plain_get_still_works(server):
    r = khttp.get(f"http://127.0.0.1:{server.port}/b", headers={"Authorization": "Bearer x"})
    assert r.ok and r.status == 200 and r.json() == {}
    assert server.hits[0][0] == "/b" and server.hits[0][1]["Authorization"] == "Bearer x"


@pytest.mark.parametrize("code", [301, 303, 307, 308])
def test_every_redirect_code_is_refused(code):
    s = _Server(code=code)
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/a")
        assert r.status == code and r.error == "redirect refused: 127.0.0.1" and s.hits == []
    finally:
        s.close()


def test_error_names_the_other_host_only_not_its_path_or_query():
    s = _Server(location="http://evil.example/steal?token=abc")
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/a", headers={"Authorization": "Bearer x"})
        assert r.error == "redirect refused: evil.example"
        assert "steal" not in r.error and "abc" not in r.error
        assert s.hits == []
    finally:
        s.close()


def test_relative_location_reports_the_request_host():
    s = _Server(location="/b")
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/a")
        assert r.status == 302 and r.error == "redirect refused: 127.0.0.1" and s.hits == []
    finally:
        s.close()


def test_redirect_target_host():
    assert khttp.redirect_target_host("https://grafana.example/login", "http://127.0.0.1:3000/api") == "grafana.example"
    assert khttp.redirect_target_host("/login", "http://127.0.0.1:3000/api") == "127.0.0.1"
    assert khttp.redirect_target_host(None, "http://[::1]:3000/api") == "::1"


@pytest.mark.parametrize(
    "base, host",
    [
        ("http://grafana.example", "grafana.example"),
        ("http://grafana.example:3000/", "grafana.example"),
        ("http://10.0.0.5:3000", "10.0.0.5"),
        ("http://127.0.0.1:3000", None),
        ("http://127.5.6.7:3000", None),
        ("http://localhost:3000", None),
        ("http://[::1]:3000", None),
        ("http://[::ffff:127.0.0.1]:3000", None),
        ("https://grafana.example", None),
    ],
)
def test_plain_http_token_host(base, host):
    assert collect.plain_http_token_host(base) == host


def _stores(url: str, tmp_path):
    log = RunLog(tmp_path / "run.log")
    stores = collect.Stores(None, collect.Config({"grafana_api_token": "glsa_x"}), {}, None, log)
    stores._url["grafana"] = url
    return stores, log


def _grafana_step(stores, log, tmp_path, echo, monkeypatch):
    monkeypatch.setattr(khttp, "get", lambda url, params=None, timeout=15, headers=None: khttp.HttpResult(url, 200, "[]"))
    st = {"id": "datasources", "type": "http", "store": "grafana", "path": "/api/datasources", "out": "grafana/datasources.json", "auth": "grafana_api_token"}
    return collect._run_http_step(st, "datasources", "grafana", stores.cfg, tmp_path, log, stores, 5, echo)


def test_token_over_plain_http_is_warned_once_per_host(tmp_path, monkeypatch):
    stores, log = _stores("http://grafana.example", tmp_path)
    lines = []
    _grafana_step(stores, log, tmp_path, lines.append, monkeypatch)
    _grafana_step(stores, log, tmp_path, lines.append, monkeypatch)

    notes = [ln for ln in (tmp_path / "run.log").read_text().splitlines() if "token sent over plain http" in ln]
    assert len(notes) == 1 and '"host": "grafana.example"' in notes[0]
    warnings = [ln for ln in lines if ln.strip().startswith("warning:")]
    assert len(warnings) == 1 and "grafana.example" in warnings[0] and "glsa_x" not in warnings[0]


def test_no_warning_for_a_loopback_url(tmp_path, monkeypatch):
    stores, log = _stores("http://127.0.0.1:3000", tmp_path)
    lines = []
    _grafana_step(stores, log, tmp_path, lines.append, monkeypatch)

    assert "token sent over plain http" not in (tmp_path / "run.log").read_text()
    assert not [ln for ln in lines if "warning:" in ln]

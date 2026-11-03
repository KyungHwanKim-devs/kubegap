"""lib.http never follows a redirect, and a token over plain http to a non-loopback host is warned about once (#83)."""

import http.server
import threading

import pytest

from lib import collect
from lib import http as khttp
from lib.runlog import RunLog, read_runlog


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


# ---------- response size cap (#91) ----------


class _BigServer:
    """Streams `size` bytes of x for every path, in chunks, so the client has to stop reading on its own."""

    def __init__(self, size: int, status: int = 200):
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(status)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(server.size))
                self.end_headers()
                left = server.size
                try:
                    while left > 0:
                        n = min(left, 65536)
                        self.wfile.write(b"x" * n)
                        left -= n
                except OSError:  # the client stops reading at its cap and closes; macOS may report EPROTOTYPE rather than EPIPE
                    pass

            def log_message(self, *a):
                pass

        self.size = size
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def test_a_reply_over_the_cap_is_refused_with_an_empty_body():
    s = _BigServer(3 * 1024 * 1024)
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/big", max_bytes=1024 * 1024)
        assert r.ok is False and r.status == 200 and r.body == ""
        assert r.error == "response larger than 1 MiB"
    finally:
        s.close()


def test_a_reply_exactly_at_the_cap_is_accepted():
    s = _BigServer(1000)
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/ok", max_bytes=1000)
        assert r.ok and len(r.body) == 1000
        r = khttp.get(f"http://127.0.0.1:{s.port}/ok", max_bytes=999)
        assert r.ok is False and r.error == "response larger than 999 bytes" and r.body == ""
    finally:
        s.close()


def test_an_error_body_is_capped_too():
    s = _BigServer(5000, status=500)
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/err", max_bytes=100)
        assert r.status == 500 and r.error == "HTTP 500" and r.body == ""
        r = khttp.get(f"http://127.0.0.1:{s.port}/err", max_bytes=10000)
        assert r.status == 500 and len(r.body) == 5000
    finally:
        s.close()


def test_default_cap_is_64_mib():
    assert khttp.HTTP_MAX_BYTES == 64 * 1024 * 1024
    assert khttp._size_error(khttp.HTTP_MAX_BYTES) == "response larger than 64 MiB"


class _CutServer:
    """Advertises Content-Length 3000 and closes after 1000 bytes, as a store that died mid-reply would."""

    def __init__(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "3000")
                self.end_headers()
                self.wfile.write(b"y" * 1000)
                self.wfile.flush()
                self.connection.close()

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def test_a_reply_the_server_cut_short_is_not_a_success():
    s = _CutServer()
    try:
        r = khttp.get(f"http://127.0.0.1:{s.port}/cut", max_bytes=10_000)
        assert r.ok is False and r.body == "" and r.status is None
        assert r.error.startswith("incomplete response:") and "2000 more expected" in r.error
    finally:
        s.close()


def test_for_each_file_items_record_their_error_and_a_runlog_line(tmp_path, monkeypatch):
    stores, log = _stores("http://127.0.0.1:3000", tmp_path)
    monkeypatch.setattr(khttp, "get", lambda url, params=None, timeout=15, headers=None: khttp.HttpResult(url, 200, "", error="response larger than 64 MiB") if url.endswith("/big") else khttp.HttpResult(url, 200, "{}"))
    (tmp_path / "grafana").mkdir()
    (tmp_path / "grafana" / "dashboards.json").write_text('[{"uid": "ok1"}, {"uid": "big"}]')
    st = {
        "id": "dashboards-json",
        "type": "http",
        "store": "grafana",
        "path": "/api/dashboards/uid/{item.uid}",
        "for_each_file": {"path": "grafana/dashboards.json", "key": "uid"},
        "out": "grafana/dashboards/{item_safe}.json",
        "auth": "grafana_api_token",
    }
    res = collect._run_http_step(st, "dashboards-json", "grafana", stores.cfg, tmp_path, log, stores, 5, None)
    assert res["ok"] is True and res["runs"] == 2
    recs = [x for x in read_runlog(tmp_path / "run.log") if x.get("kind") == "command"]
    assert [(x["id"], x["code"], x["error"]) for x in recs] == [("grafana.dashboards-json.ok1", 0, None), ("grafana.dashboards-json.big", 200, "response larger than 64 MiB")]
    assert (tmp_path / "grafana" / "dashboards" / "ok1.json").is_file() and not (tmp_path / "grafana" / "dashboards" / "big.json").exists()

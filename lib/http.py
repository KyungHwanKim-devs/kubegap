"""Small urllib-based HTTP GET. For Prometheus, Loki, Alertmanager and Grafana API queries.

Redirects are never followed. urllib's default opener copies every request header except Content-Length and Content-Type, the
Authorization header among them, onto the redirected request, so a store that answered a redirect with another host in Location would
receive the Grafana token. A redirect (301, 302, 303, 307, 308) is returned as a failed HttpResult that names the host of the Location
only, never its path or query.
"""

from __future__ import annotations

import contextlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

REDIRECT_CODES = (301, 302, 303, 307, 308)


@dataclass
class HttpResult:
    url: str
    status: int | None
    body: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def json(self):
        try:
            return json.loads(self.body) if self.body else None
        except json.JSONDecodeError:
            return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn every redirect into the HTTPError that `get()` reports; nothing is requested from the Location."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


_opener = urllib.request.build_opener(_NoRedirect)


def redirect_target_host(location: str | None, request_url: str) -> str:
    """The host a redirect points at: the Location's host, or the request's own host when Location is relative or absent."""
    host = urllib.parse.urlsplit(location).hostname if location else None
    return host or urllib.parse.urlsplit(request_url).hostname or "?"


def get(url: str, params: dict | None = None, timeout: float = 15, headers: dict | None = None) -> HttpResult:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"})
    try:
        with _opener.open(req, timeout=timeout) as resp:  # only opens a local port-forward or a configured URL
            return HttpResult(url, resp.status, resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code in REDIRECT_CODES:
            with contextlib.suppress(Exception):
                e.close()
            return HttpResult(url, e.code, "", error=f"redirect refused: {redirect_target_host(e.headers.get('Location'), url)}")
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return HttpResult(url, e.code, body, error=f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return HttpResult(url, None, error=str(getattr(e, "reason", e)))

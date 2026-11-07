"""Small urllib-based HTTP GET. For Prometheus, Loki, Alertmanager and Grafana API queries.

Redirects are never followed. urllib's default opener copies every request header except Content-Length and Content-Type, the
Authorization header among them, onto the redirected request, so a store that answered a redirect with another host in Location would
receive the Grafana token. A redirect (301, 302, 303, 307, 308) is returned as a failed HttpResult that names the host of the Location
only, never its path or query.

A response is read up to HTTP_MAX_BYTES (64 MiB) and refused beyond that, so a store that ignores its own limit, or a Loki query that
returns everything, cannot fill memory and the snapshot with one reply; the step fails with "response larger than 64 MiB" and report
section 7-1 shows it. The body of an error response is capped the same way. A reply the server cut short fails as "incomplete response"
instead of being written as if whole; a near-cap reply costs about twice the cap in memory, bytes and then text.
"""

from __future__ import annotations

import contextlib
import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

REDIRECT_CODES = (301, 302, 303, 307, 308)
HTTP_MAX_BYTES = 64 * 1024 * 1024


@dataclass
class HttpResult:
    url: str
    status: int | None
    body: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300  # a capped reply has status 200 and an error, and is not ok

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


def _size_error(max_bytes: int) -> str:
    mib = max_bytes / (1024 * 1024)
    return f"response larger than {mib:g} MiB" if max_bytes >= 1024 * 1024 else f"response larger than {max_bytes} bytes"


def _read_capped(fp, max_bytes: int) -> bytes | None:
    """Up to max_bytes of the response body; None when the body is longer (one byte more is read to know).

    `read(n)` does not check completeness the way `read()` does, so a reply the server cut short is checked here: when Content-Length
    still owes bytes, IncompleteRead is raised and the step fails instead of a truncated body passing as whole.
    """
    data = fp.read(max_bytes + 1)
    if len(data) > max_bytes:
        return None
    left = getattr(fp, "length", None)  # HTTPResponse: bytes still owed by Content-Length; 0 when done, None when chunked or EOF-delimited
    if isinstance(left, int) and left > 0:
        raise http.client.IncompleteRead(data, left)
    return data


def get(url: str, params: dict | None = None, timeout: float = 15, headers: dict | None = None, max_bytes: int = HTTP_MAX_BYTES) -> HttpResult:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"})
    try:
        with _opener.open(req, timeout=timeout) as resp:  # only opens a local port-forward or a configured URL
            raw = _read_capped(resp, max_bytes)
            if raw is None:
                return HttpResult(url, resp.status, "", error=_size_error(max_bytes))
            return HttpResult(url, resp.status, raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code in REDIRECT_CODES:
            with contextlib.suppress(Exception):
                e.close()
            return HttpResult(url, e.code, "", error=f"redirect refused: {redirect_target_host(e.headers.get('Location'), url)}")
        try:
            raw = _read_capped(e, max_bytes)
            body = "" if raw is None else raw.decode("utf-8", "replace")
        except Exception:
            body = ""
        return HttpResult(url, e.code, body, error=f"HTTP {e.code}")
    except http.client.HTTPException as e:  # IncompleteRead, a chunked reply without its last chunk, a bad status line: not an OSError
        return HttpResult(url, None, error=f"incomplete response: {e}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return HttpResult(url, None, error=str(getattr(e, "reason", e)))

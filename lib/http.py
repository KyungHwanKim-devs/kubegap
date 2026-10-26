"""Small urllib-based HTTP GET. For Prometheus, Loki, Alertmanager and Grafana API queries."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


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


def get(url: str, params: dict | None = None, timeout: float = 15, headers: dict | None = None) -> HttpResult:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # only opens a local port-forward or a configured URL
            return HttpResult(url, resp.status, resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return HttpResult(url, e.code, body, error=f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return HttpResult(url, None, error=str(getattr(e, "reason", e)))

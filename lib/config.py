"""Read config.yaml. The file is optional; without it we run with an empty config.

Known keys: context, profile, confirm_context (bool, default true), install_tools (ask|always|never, default ask), aws_profile, aws_region, prometheus_url, loki_url, alertmanager_url, grafana_url,
node_access(ssm|ssh|none), ssh(user, key, port), suppress[], overrides{}.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import yamlite

KNOWN_KEYS = {
    "context",
    "profile",
    "aws_profile",
    "aws_region",
    "prometheus_url",
    "loki_url",
    "alertmanager_url",
    "grafana_url",
    "node_access",
    "ssh",
    "suppress",
    "overrides",
    "namespace_profiles",
    "language",
    "mode",
    "confirm_context",
    "install_tools",
    "grafana_api_token",
    "snapshots_root",
}
INSTALL_POLICIES = ("ask", "always", "never")


class Config(dict):
    def __init__(self, data: dict | None = None, path: Path | None = None, loaded: bool = False):
        super().__init__(data or {})
        self.path = path
        self.loaded = loaded
        self.warnings = [f"unknown key in config.yaml: {k}" for k in self if k not in KNOWN_KEYS]

    @property
    def install_policy(self) -> str:
        v = str(self.get("install_tools", "ask")).lower()
        return v if v in INSTALL_POLICIES else "ask"

    @property
    def confirm_context(self) -> bool:
        return bool(self.get("confirm_context", True))

    def url(self, name: str) -> str | None:
        v = self.get(f"{name}_url")
        return str(v).rstrip("/") if v else None


def load_config(path: str | Path | None) -> Config:
    if not path:
        return Config()
    p = Path(path).expanduser()
    if not p.is_file():
        return Config(path=p, loaded=False)
    data: Any = yamlite.load_file(p)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise yamlite.YamlError(f"{p}: top level must be a mapping")
    return Config(data, path=p, loaded=True)

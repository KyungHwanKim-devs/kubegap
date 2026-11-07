"""`kubegap config set`: write one key of `~/.kubegap/config.yaml` without the user opening the file.

The first-run questions (lib/commands/firstrun.py) end in values only the user knows: the address a node answers SSH on, the URL of a Prometheus that
lives outside the cluster. Before this module the answer was "copy config.example.yaml and edit it". The edit is line based so that the comments
and the order of a hand-written file survive; the result is parsed again with lib/foundations/yamlite and the key must read back as the value that was asked
for, otherwise nothing is written.

Only the keys in SETTABLE can be set. `grafana_api_token` is refused on purpose: a token typed into the agent's chat or put on a command line the
agent runs has already left the machine, so the user adds that one line by hand.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from ..foundations import yamlite
from ..foundations.config import INSTALL_POLICIES
from ..foundations.paths import MODES, ensure_private_dir
from ..foundations.snapshot import write_private

_BOOL = ("true", "false")
_URL = re.compile(r"^https?://[^\s#]+$")
_PLAIN = re.compile(r"^[A-Za-z0-9_./@~-]+$")  # written without quotes; anything else is double-quoted
_NODE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$")  # a Kubernetes node name is a DNS subdomain
_ADDRESS = re.compile(r"^([A-Za-z0-9._-]+@)?[A-Za-z0-9.:_-]+$")  # host, IP, or user@host

# key -> (validator, what a valid value looks like). `ssh.hosts.<node>` is matched separately.
SETTABLE: dict[str, tuple] = {
    "language": (lambda v: v in ("en", "ko"), "en or ko"),
    "mode": (lambda v: v in MODES, " or ".join(MODES)),
    "node_access": (lambda v: v in ("ssm", "ssh", "none"), "ssm, ssh or none"),
    "install_tools": (lambda v: v in INSTALL_POLICIES, ", ".join(INSTALL_POLICIES)),
    "ssm_document": (lambda v: v in INSTALL_POLICIES, ", ".join(INSTALL_POLICIES)),
    "confirm_context": (lambda v: v in _BOOL, "true or false"),
    "prometheus_url": (lambda v: bool(_URL.match(v)), "an http:// or https:// address"),
    "alertmanager_url": (lambda v: bool(_URL.match(v)), "an http:// or https:// address"),
    "loki_url": (lambda v: bool(_URL.match(v)), "an http:// or https:// address"),
    "grafana_url": (lambda v: bool(_URL.match(v)), "an http:// or https:// address"),
    "ssh.user": (lambda v: bool(re.match(r"^[A-Za-z_][A-Za-z0-9_.-]*$", v)), "a login name"),
    "ssh.key": (lambda v: bool(v) and "\n" not in v, "the path of a private key file"),
    "ssh.port": (lambda v: v.isdigit() and 0 < int(v) < 65536, "a port number"),
    "ssh.accept_new_hosts": (lambda v: v in _BOOL, "true or false"),
}
REFUSED = {
    "grafana_api_token": "a token must not pass through the agent or a command line it runs. Add the line `grafana_api_token: <token>` to the file yourself and `chmod 600` it",
}


class ConfigEditError(ValueError):
    pass


def _validate(key: str, value: str) -> list[str]:
    """The key as a path, after checking that it may be set and that the value has the right shape."""
    if key in REFUSED:
        raise ConfigEditError(f"{key} is not set by this command: {REFUSED[key]}")
    if key.startswith("ssh.hosts."):
        node = key[len("ssh.hosts.") :]
        if not _NODE.match(node):
            raise ConfigEditError(f"{node!r} is not a node name")
        if not _ADDRESS.match(value):
            raise ConfigEditError(f"{value!r} is not an address; expected a host name, an IP or user@host")
        return ["ssh", "hosts", node]
    if key not in SETTABLE:
        raise ConfigEditError(f"{key} cannot be set by this command. Keys: {', '.join(sorted(SETTABLE))}, ssh.hosts.<node>. Every other key is edited in the file (config.example.yaml lists them)")
    ok, shape = SETTABLE[key]
    if not ok(value):
        raise ConfigEditError(f"{key}: {value!r} is not {shape}")
    return key.split(".")


_BOOL_KEYS = ("confirm_context", "ssh.accept_new_hosts")
_INT_KEYS = ("ssh.port",)


def _python_value(key: str, value: str):
    """What the key must read back as: a bool or an int for the keys that are one, text for every other key."""
    if key in _BOOL_KEYS:
        return value == "true"
    return int(value) if key in _INT_KEYS else value


def _render(key: str, value: str) -> str:
    """The value as YAML. Text that YAML would read as something else (`12345`, `true`, `null`) is quoted, so a host or a login stays text."""
    want = _python_value(key, value)
    if not isinstance(want, str):
        return value
    if (_PLAIN.match(value) or _URL.match(value)) and yamlite.parse_scalar(value) == value:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_content(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#")


def _find(lines: list[str], start: int, end: int, indent: int, key: str) -> int | None:
    k = re.escape(key)
    pat = re.compile(rf"^ {{{indent}}}({k}|\"{k}\"|'{k}')\s*:(\s|$)")
    for i in range(start, end):
        if pat.match(lines[i]):
            return i
    return None


def _block_end(lines: list[str], idx: int, end: int) -> int:
    """First line after the block that the key on line `idx` opens: the next content line indented no deeper than the key."""
    ind = _indent(lines[idx])
    for i in range(idx + 1, end):
        if _is_content(lines[i]) and _indent(lines[i]) <= ind:
            return i
    return end


def _key_text(key: str) -> str:
    return key if _PLAIN.match(key) else '"' + key + '"'


def set_text(text: str, key: str, value: str) -> str:
    """The config text with `key` set to `value`. Raises ConfigEditError when the key may not be set, the value has the wrong shape,
    or the file's layout is one this line editor does not handle (the message says to edit by hand)."""
    path = _validate(key, value)
    if text.startswith("\ufeff"):
        raise ConfigEditError("the file starts with a byte order mark; save it as plain UTF-8, or edit it by hand")
    eol = "\r\n" if "\r\n" in text else "\n"  # a file written with Windows line ends keeps them
    lines = text.replace("\r\n", "\n").splitlines()
    start, end, indent = 0, len(lines), 0
    for depth, part in enumerate(path):
        leaf = depth == len(path) - 1
        idx = _find(lines, start, end, indent, part)
        if idx is None:
            # insert the rest of the path after the last content line of the enclosing block
            # (blank lines, and comments indented less than the block's keys, belong to what follows)
            at = end
            while at > start and (not lines[at - 1].strip() or (not _is_content(lines[at - 1]) and _indent(lines[at - 1]) < indent)):
                at -= 1
            new = [" " * (indent + 2 * j) + _key_text(p) + ":" for j, p in enumerate(path[depth:-1])]
            new.append(" " * (indent + 2 * (len(path) - 1 - depth)) + _key_text(path[-1]) + ": " + _render(key, value))
            lines[at:at] = new
            break
        after_key = lines[idx].split(":", 1)[1]
        rest = yamlite._strip_comment(after_key).strip()
        comment = after_key[len(yamlite._strip_comment(after_key)) :].strip()  # the user's note on that line stays
        b_end = _block_end(lines, idx, end)
        children = [i for i in range(idx + 1, b_end) if _is_content(lines[i])]
        if leaf:
            if children:
                raise ConfigEditError(f"{key} holds a block in the file, not one value; edit it by hand")
            lines[idx] = " " * indent + _key_text(part) + ": " + _render(key, value) + (f"  {comment}" if comment else "")
            break
        if rest:
            raise ConfigEditError(f"{'.'.join(path[: depth + 1])} is written on one line in the file (`{lines[idx].strip()}`); edit it by hand")
        start, end = idx + 1, b_end
        indent = _indent(lines[children[0]]) if children else indent + 2
    out = eol.join(lines) + eol
    try:
        data = yamlite.load(out.replace("\r\n", "\n")) or {}
    except yamlite.YamlError as e:
        raise ConfigEditError(f"the edited file would not parse ({e}); edit it by hand") from e
    got = data
    for part in path:
        got = got.get(part) if isinstance(got, dict) else None
    if got != _python_value(key, value) or type(got) is not type(_python_value(key, value)):
        raise ConfigEditError(f"after the edit {key} would read {got!r}, not {value!r}; edit the file by hand")
    return out


HEADER = "# kubegap settings. Every key is optional; config.example.yaml in the kubegap folder lists them.\n"


def set_key(path: Path, key: str, value: str, *, dry_run: bool = False) -> tuple[str, bool]:
    """Set one key in the file at `path` (created when absent, readable by the user only). Returns the changed lines as a unified diff
    and whether the file was written. Nothing is written when the value is already there or with dry_run."""
    path = path.resolve()  # a config.yaml that is a link into a dotfiles folder: write the file it points at, do not replace the link
    old = path.read_bytes().decode("utf-8") if path.is_file() else ""
    new = set_text(old or HEADER, key, value)
    if new == old:
        return "", False
    diff = "\n".join(ln for ln in difflib.unified_diff(old.splitlines(), new.splitlines(), "before", "after", lineterm="", n=1) if not ln.startswith(("---", "+++")))
    if dry_run:
        return diff, False
    ensure_private_dir(path.parent)
    write_private(path, new)
    return diff, True

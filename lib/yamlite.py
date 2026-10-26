"""Partial YAML parser. The Python standard library has no YAML, and kubegap uses the standard library only, so this is hand-written
(deliberately kept instead of PyYAML so the skill installs with zero dependencies).

It reads only what kubegap's YAML needs (checks.yaml, config.yaml, profiles, signatures.yaml). Supported subset:
- block mappings and block sequences by indentation (spaces only), mappings inside sequence items starting with `- key: value`, nested `- - x`
- a sequence at the same indent as its parent key (`key:` followed by `- a` on the next line)
- single-line flow collections `{ a: 1, b: [x, y] }`, `[a, b]` (nesting allowed, must close on the same line)
- block scalars `|` and `>` with chomping indicators `-` (strip) and `+` (keep); without an indicator one trailing newline is kept (clip)
- quoted scalars 'single' (with '' escape) and "double" (with \\n \\t \\" \\\\ escapes); a quoted scalar may continue on following lines until the closing quote
- `#` comments (at line start or after whitespace, outside quotes) and `%` directives (ignored)
- scalars: null/~/empty, true/false, integers (with _ separators), floats, and everything else as a plain string
Not supported (raise YamlError): anchors (&), aliases (*), tags (!), multiple documents (---), multi-line plain scalars, complex (non-scalar) keys,
block scalar indentation indicators (`|2`), tabs in indentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class YamlError(ValueError):
    pass


_INT = re.compile(r"^[-+]?(0|[1-9][0-9_]*)$")
_FLOAT = re.compile(r"^[-+]?(\d[\d_]*)?\.\d+([eE][-+]?\d+)?$|^[-+]?\d[\d_]*[eE][-+]?\d+$")


def load(text: str) -> Any:
    lines = _prepare(text)
    if not lines:
        return None
    first = next((ln for ln in lines if ln[1]), None)
    if first is not None and first[1][0] in "[{" and all(not ln[1] for ln in lines if ln is not first):
        return parse_scalar(first[1])  # the whole document is a single `[]` or `{a: 1}`
    p = _Parser(lines)
    value, idx = p.parse_block(0, lines[0][0])
    if idx != len(lines):
        ln = lines[idx][2]
        raise YamlError(f"line {ln}: unexpected content {lines[idx][1]!r}")
    return value


def load_file(path: str | Path) -> Any:
    return load(Path(path).read_text(encoding="utf-8"))


# ---------- Preprocessing ----------


def _quote_opens(s: str, i: int) -> bool:
    """True when the quote at s[i] starts a scalar: at the start of the content, after `key: `, after `- `, or after `[`, `{`, `,` inside a flow collection.
    An apostrophe inside a plain scalar (`why: Karpenter's budget`) is not a quote, otherwise a comment after it would be kept as part of the value."""
    j = i - 1
    while j >= 0 and s[j] in " \t":
        j -= 1
    if j < 0:
        return True
    if s[j] in "[{,:":
        return True
    return s[j] == "-" and s[:j].strip() == ""


def _strip_comment(s: str) -> str:
    """Strip from ` #` outside quotes, or from a leading `#`, to the end of the line."""
    if "#" not in s:
        return s
    q = None
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            if ch == q:
                if q == "'" and i + 1 < len(s) and s[i + 1] == "'":  # '' escape inside a single-quoted scalar
                    i += 2
                    continue
                q = None
            elif q == '"' and ch == "\\":
                i += 2
                continue
        elif ch in ("'", '"') and _quote_opens(s, i):
            q = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i]
        i += 1
    return s


def _prepare(text: str) -> list[tuple[int, str, int, str]]:
    """List of (indent, content without comment, line number, raw line). Blank lines are kept with content "" (to preserve blank lines inside block strings)."""
    out = []
    for n, raw in enumerate(text.splitlines(), 1):
        if raw.strip().startswith("---") and raw.strip() == "---":
            if any(ln[1] for ln in out):
                raise YamlError(f"line {n}: multiple documents (---) are not supported")
            continue
        if raw.strip().startswith("%"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {n}: tab in indentation")
        content = _strip_comment(raw).rstrip()
        indent = len(raw) - len(raw.lstrip(" "))
        # keep the raw line too, for block string bodies
        out.append((indent, content.strip(), n, raw))
    return out


# ---------- Scalars ----------


def parse_scalar(s: str) -> Any:
    s = s.strip()
    if s == "" or s in ("~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if s[0] in ("'", '"'):
        return _unquote(s)
    if _INT.match(s):
        return int(s.replace("_", ""))
    if _FLOAT.match(s):
        return float(s.replace("_", ""))
    if s.startswith(("{", "[")):
        v, rest = _FlowParser(s).parse_value()
        if rest.strip():
            raise YamlError(f"trailing content after flow value: {rest!r}")
        return v
    if s[0] in "&*!":
        raise YamlError(f"anchors, aliases and tags are not supported: {s!r}")
    return s


def _unquote(s: str) -> str:
    q = s[0]
    if len(s) < 2 or s[-1] != q:
        raise YamlError(f"unterminated quote: {s!r}")
    body = s[1:-1]
    if q == "'":
        return body.replace("''", "'")
    return body.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")


def _split_key(s: str) -> tuple[str, str] | None:
    """Split `key: value` or `key:` into (key, value). None if not a mapping entry. Colons inside quotes or flow style are ignored."""
    q = None
    depth = 0
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
            continue
        if ch in ("'", '"') and depth == 0 and i == 0:
            q = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == ":" and depth == 0 and (i + 1 == len(s) or s[i + 1] in " \t"):
            key = s[:i].strip()
            if key.startswith(("'", '"')):
                key = _unquote(key)
            return key, s[i + 1 :].strip()
    return None


# ---------- Flow style { } [ ] ----------


class _FlowParser:
    def __init__(self, s: str):
        self.s = s
        self.i = 0

    def _ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def parse_value(self) -> tuple[Any, str]:
        self._ws()
        if self.i >= len(self.s):
            raise YamlError("empty flow value")
        ch = self.s[self.i]
        if ch == "{":
            v = self._mapping()
        elif ch == "[":
            v = self._sequence()
        else:
            v = self._scalar(stop=",]}")
        return v, self.s[self.i :]

    def _mapping(self) -> dict:
        self.i += 1
        out: dict = {}
        while True:
            self._ws()
            if self.i >= len(self.s):
                raise YamlError("unterminated '{'")
            if self.s[self.i] == "}":
                self.i += 1
                return out
            key = self._scalar(stop=":,}")
            self._ws()
            if self.i < len(self.s) and self.s[self.i] == ":":
                self.i += 1
                self._ws()
                if self.i < len(self.s) and self.s[self.i] in ",}":
                    val = None
                else:
                    val, _ = self.parse_value()
            else:
                val = None
            out[str(key)] = val
            self._ws()
            if self.i < len(self.s) and self.s[self.i] == ",":
                self.i += 1

    def _sequence(self) -> list:
        self.i += 1
        out: list = []
        while True:
            self._ws()
            if self.i >= len(self.s):
                raise YamlError("unterminated '['")
            if self.s[self.i] == "]":
                self.i += 1
                return out
            val, _ = self.parse_value()
            out.append(val)
            self._ws()
            if self.i < len(self.s) and self.s[self.i] == ",":
                self.i += 1

    def _scalar(self, stop: str) -> Any:
        self._ws()
        if self.i < len(self.s) and self.s[self.i] in ("'", '"'):
            q = self.s[self.i]
            j = self.s.find(q, self.i + 1)
            while q == "'" and j != -1 and j + 1 < len(self.s) and self.s[j + 1] == "'":
                j = self.s.find(q, j + 2)
            if j == -1:
                raise YamlError("unterminated quote")
            raw = self.s[self.i : j + 1]
            self.i = j + 1
            return _unquote(raw)
        j = self.i
        while j < len(self.s):
            c = self.s[j]
            if c in stop:
                # a colon not followed by a space (as in `http://`) is part of the value
                if c == ":" and j + 1 < len(self.s) and self.s[j + 1] not in " \t,}]":
                    j += 1
                    continue
                break
            j += 1
        raw = self.s[self.i : j].strip()
        self.i = j
        return parse_scalar(raw) if raw else None


# ---------- Block style ----------


class _Parser:
    def __init__(self, lines):
        self.lines = lines  # (indent, content, lineno, raw)

    def _skip_blank(self, idx: int) -> int:
        while idx < len(self.lines) and self.lines[idx][1] == "":
            idx += 1
        return idx

    def parse_block(self, idx: int, indent: int) -> tuple[Any, int]:
        idx = self._skip_blank(idx)
        if idx >= len(self.lines):
            return None, idx
        ind, content, ln, _ = self.lines[idx]
        if ind != indent:
            raise YamlError(f"line {ln}: indent {ind}, expected {indent}")
        if content.startswith("- ") or content == "-":
            return self._sequence(idx, indent)
        return self._mapping(idx, indent)

    def _sequence(self, idx: int, indent: int) -> tuple[list, int]:
        out: list = []
        while True:
            idx = self._skip_blank(idx)
            if idx >= len(self.lines):
                return out, idx
            ind, content, ln, raw = self.lines[idx]
            if ind < indent:
                return out, idx
            if ind > indent:
                raise YamlError(f"line {ln}: list indentation mismatch")
            if not (content.startswith("- ") or content == "-"):
                return out, idx
            rest = content[1:].strip()
            if rest == "":
                val, idx = self._nested_or_null(idx + 1, indent)
                out.append(val)
                continue
            # `- key: v` or `- - x`: replace the dash with a space and re-read the same line as a block at indent+2
            if (_split_key(rest) is not None and not rest.startswith(("{", "[", "'", '"'))) or rest.startswith("- ") or rest == "-":
                dash_pos = raw.index("-", ind)
                new_raw = raw[:dash_pos] + " " + raw[dash_pos + 1 :]
                new_indent = len(new_raw) - len(new_raw.lstrip(" "))
                self.lines[idx] = (new_indent, rest, ln, new_raw)
                val, idx = self.parse_block(idx, new_indent)
                out.append(val)
                continue
            val, idx = self._inline_value(rest, idx, indent)
            out.append(val)

    def _mapping(self, idx: int, indent: int) -> tuple[dict, int]:
        out: dict = {}
        while True:
            idx = self._skip_blank(idx)
            if idx >= len(self.lines):
                return out, idx
            ind, content, ln, _raw = self.lines[idx]
            if ind < indent:
                return out, idx
            if ind > indent:
                raise YamlError(f"line {ln}: mapping indentation mismatch ({ind} > {indent})")
            if content.startswith("- "):
                return out, idx
            kv = _split_key(content)
            if kv is None:
                raise YamlError(f"line {ln}: not a `key: value` entry: {content!r} (multi-line plain strings are not supported; use `>`)")
            key, rest = kv
            if key in out:
                raise YamlError(f"line {ln}: duplicate key {key!r}")
            if rest == "":
                val, idx = self._nested_or_null(idx + 1, indent)
            else:
                val, idx = self._inline_value(rest, idx, indent)
            out[key] = val

    def _nested_or_null(self, idx: int, indent: int) -> tuple[Any, int]:
        j = self._skip_blank(idx)
        if j < len(self.lines) and self.lines[j][0] > indent:
            return self.parse_block(j, self.lines[j][0])
        # a `- ` list at the same indent on the line after `key:` (allowed by YAML)
        if j < len(self.lines) and self.lines[j][0] == indent and self.lines[j][1].startswith("- "):
            return self._sequence(j, indent)
        return None, idx

    @staticmethod
    def _quote_closed(text: str) -> bool:
        q = text[0]
        i = 1
        while i < len(text):
            if text[i] == q:
                if q == "'" and i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                return True
            if q == '"' and text[i] == "\\":
                i += 2
                continue
            i += 1
        return False

    def _inline_value(self, rest: str, idx: int, indent: int) -> tuple[Any, int]:
        ln = self.lines[idx][2]
        if rest[0] in ">|":
            return self._block_scalar(rest, idx, indent)
        # a quoted scalar spanning several lines (e.g. Alertmanager templates): join following lines with spaces until the closing quote
        if rest[0] in ("'", '"') and not self._quote_closed(rest):
            j = idx + 1
            text = rest
            while j < len(self.lines):
                piece = self.lines[j][3].strip()
                text += " " + piece
                j += 1
                if piece and self._quote_closed(text):
                    break
            try:
                return parse_scalar(text), j
            except YamlError as e:
                raise YamlError(f"line {ln}: {e}") from None
        try:
            return parse_scalar(rest), idx + 1
        except YamlError as e:
            raise YamlError(f"line {ln}: {e}") from None

    def _block_scalar(self, header: str, idx: int, indent: int) -> tuple[str, int]:
        style, chomp = header[0], header[1:2]
        if header[1:] not in ("", "-", "+"):
            raise YamlError(f"line {self.lines[idx][2]}: block string indicator {header!r} is not supported")
        body_lines: list[str] = []
        j = idx + 1
        block_indent = None
        while j < len(self.lines):
            ind, _content, _, raw = self.lines[j]
            if raw.strip() == "":  # test the raw line: a comment-only line inside a block scalar is content, not a blank
                body_lines.append("")
                j += 1
                continue
            if ind <= indent:
                break
            if block_indent is None:
                block_indent = ind
            body_lines.append(raw[block_indent:].rstrip("\n"))
            j += 1
        trailing_blank = 0
        while body_lines and body_lines[-1] == "":
            body_lines.pop()
            trailing_blank += 1
        if style == "|":
            text = "\n".join(body_lines)
        else:
            # folded: consecutive lines are joined with spaces, a blank line becomes one newline
            paras: list[str] = []
            cur: list[str] = []
            for ln in body_lines:
                if ln == "":
                    paras.append(" ".join(cur))
                    cur = []
                else:
                    cur.append(ln.strip())
            paras.append(" ".join(cur))
            text = "\n".join(paras)
        # chomping: `-` strips the final newline, `+` keeps the final newline and every trailing blank line, no indicator keeps exactly one newline (clip)
        if chomp == "+":
            text += "\n" * (1 + trailing_blank)
        elif chomp != "-":
            text += "\n"
        return text, j

"""Masking.

Applied to the report body and the condensed version. After the LLM writes the report, it is passed through `scripts/kubegap mask <file>` once more before saving.
The raw snapshot stays local and is read directly by the LLM, so it is not masked as a whole. What may hold a credential is kept out of it instead: Secret data and ConfigMap values are dropped at collection time (lib/foundations/scrub.py), and component pod logs are deleted after summarize, with only masked sample lines surviving in summary.json (lib/summaries/logs.py calls mask_text on them).

What is masked:
- token/password patterns: the values of `Bearer …`, `password=…`/`passwd:`/`pwd=`, `token=`, `api[_-]?key=`, `secret=`, `authorization:`
- credential shapes: AWS access keys (AKIA…/ASIA…), the 40 characters after an AWS secret key, JWTs (eyJ…), PEM blocks, Slack/Discord webhook URLs, GitHub tokens (ghp_…)
- base64 runs of 40 or more characters (certificate/key data)
- AWS account ids: the 12 digits inside ARNs and every known account id (from inventory) → <account>
- (optional, --ips) private IPv4 → <ip>. Off by default: an IP needed for a finding may be written individually, and not dumping the full list is a rule of the LLM procedure (SKILL.md).
- terminal control characters, first of all: ECMA-48 control sequences (CSI: colours, cursor moves, `\x1b[2J`), control strings (OSC 8 hyperlinks,
  DCS, SOS, PM, APC, each with its payload up to ST), the other ESC sequences, and every C0 and C1 control character except newline and tab. Report strings come from pod names, annotations, events and log lines,
  and a terminal that `cat`s the report would interpret them. Removed before the credential patterns so an escape sequence cannot split a token in two.
  Unicode above U+009F is left alone, bidi overrides and zero-width characters included: they change how text reads, not what a terminal executes.
  The cost of reading the 8-bit introducers as ECMA-48 does: a line that carries U+0090, U+0098, U+009D, U+009E or U+009F as text (double-encoded
  Windows-1252, where `Ÿ` is 0x9F) loses its tail from that character, as a terminal would; masking runs on report text and 240-character log
  samples, never on the snapshot files, so what is lost is one line of a report or one sample.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MASK = "<masked>"

# ECMA-48 5th edition (references/sources.md, #128): a control sequence is CSI (ESC [ or 0x9B) + parameter bytes 0x30-0x3F + intermediate bytes 0x20-0x2F
# + one final byte 0x40-0x7E (§5.4, §8.3.16); a control string is OSC/DCS/SOS/PM/APC (ESC ] P X ^ _ or 0x9D 0x90 0x98 0x9E 0x9F) up to ST (ESC \ or 0x9C; §5.6,
# §8.3.143), and OSC also up to BEL, which terminals accept although the standard does not name it; an unterminated string ends at its line, never beyond.
# Then any other escape sequence, ESC + intermediate bytes 0x20-0x2F + one final byte 0x30-0x7E (ESC c, ESC ( B, ESC =; ECMA-48 §8.3.48 defers the structure to ECMA-35 §13.1),
# then lone C0 (minus \n and \t), DEL and C1 bytes.
# Until #128 a string that ended with the 8-bit ST, or that opened with an 8-bit introducer, was cut at the wrong place: the OSC pattern knew BEL and ESC \ only,
# so `ESC ] 8;;url 0x9C name` lost `name` with the link, and the DCS/APC payload was left in the text.
_CONTROL = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
    r"|\x9b[0-?]*[ -/]*[@-~]"
    r"|(?:\x1b\]|\x9d)[^\x07\x1b\x9c\n]*(?:\x07|\x1b\\|\x9c)?"
    r"|(?:\x1b[PX^_]|[\x90\x98\x9e\x9f])[^\x1b\x9c\n]*(?:\x1b\\|\x9c)?"
    r"|\x1b[ -/]*[0-~]"
    r"|[\x00-\x08\x0b-\x1f\x7f\x80-\x9f]"
)


def strip_control(text: str) -> tuple[str, int]:
    """`text` without terminal control sequences and control characters (newline and tab stay), and how many were removed. The one place that knows the
    ECMA-48 shapes; lib/collection/collect.py reads a tool's coloured stderr through it before matching log lines."""
    return _CONTROL.subn("", text)


_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pem", re.compile(r"-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----", re.DOTALL)),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*")),
    ("authorization", re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)")),
    ("kv-secret", re.compile(r"(?i)\b((?:password|passwd|pwd|token|access[_-]?token|refresh[_-]?token|api[_-]?key|apikey|secret|client[_-]?secret|private[_-]?key)\s*[:=]\s*[\"']?)([^\s\"'&,;]{4,})")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws-secret-key", re.compile(r"(?i)(aws_secret_access_key\s*[:=]\s*)([A-Za-z0-9/+=]{40,})")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("slack-webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+")),
    ("discord-webhook", re.compile(r"https://discord(?:app)?\.com/api/webhooks/[A-Za-z0-9/_-]+")),
    ("base64-long", re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")),
]
_ARN_ACCOUNT = re.compile(r"(arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:)(\d{12})(:)")
_PRIVATE_IP = re.compile(
    r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})(?![\d.])"
)  # not \b: in JSON text an escaped newline (`\n192.168…`) puts a letter right before the address
# exceptions to avoid base64 false positives: sha256 hashes (64 hex chars), image digests and long tokens in URL paths are not masked
_HEX = re.compile(r"^[0-9a-f]{40,}$")
# A pure-ASCII camelCase identifier (k8s field name) with no digits, '+' or '/' and a lowercase→uppercase transition is not base64.
# The chance that 40+ base64 characters are all letters is (52/64)^40 ≈ 0.02%, so the risk of missing something is small
_CAMEL = re.compile(r"^(?=.*[a-z][A-Z])[A-Za-z]+$")


@dataclass
class MaskResult:
    text: str
    counts: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def mask_text(text: str, account_ids: list[str] | None = None, ips: bool = False) -> MaskResult:
    counts: dict[str, int] = {}

    def bump(name: str, n: int = 1):
        if n:
            counts[name] = counts.get(name, 0) + n

    text, n = strip_control(text)
    bump("control-chars", n)
    for name, pat in _PATTERNS:
        if name in ("authorization", "kv-secret", "aws-secret-key"):
            text, n = pat.subn(lambda m: m.group(1) + MASK, text)
        elif name == "base64-long":
            hit = [0]

            def _b64(m):
                s = m.group(0)
                if _HEX.match(s.lower()) or ("/" in s and s.count("/") > 3):
                    return s  # keep sha256 hashes, digests and URL paths
                if _CAMEL.match(s):
                    return s  # k8s field names such as requiredDuringSchedulingIgnoredDuringExecution (false positive seen in a real report)
                hit[0] += 1
                return MASK

            text = pat.sub(_b64, text)
            n = hit[0]
        else:
            text, n = pat.subn(MASK, text)
        bump(name, n)
    text, n = _ARN_ACCOUNT.subn(r"\1<account>\3", text)
    bump("aws-account-arn", n)
    for acct in account_ids or []:
        if acct and re.fullmatch(r"\d{12}", str(acct)):
            text, n = re.subn(r"\b" + re.escape(str(acct)) + r"\b", "<account>", text)
            bump("aws-account-id", n)
    if ips:
        text, n = _PRIVATE_IP.subn("<ip>", text)
        bump("private-ip", n)
    return MaskResult(text, counts)


def mask_file(path, account_ids: list[str] | None = None, ips: bool = False, write: bool = True) -> MaskResult:
    import stat
    from pathlib import Path

    from .snapshot import write_private

    p = Path(path)
    r = mask_text(p.read_text(encoding="utf-8"), account_ids, ips)
    if write and r.total:
        write_private(p, r.text, mode=stat.S_IMODE(p.stat().st_mode))  # the report is the user's file; keep its permissions, only make the rewrite atomic
    return r

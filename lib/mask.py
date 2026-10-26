"""Masking.

Applied to the report body and the condensed version. After the LLM writes the report, it is passed through `scripts/kubegap mask <file>` once more before saving.
The raw snapshot stays local and is read directly by the LLM, so it is not masked (Secret values are already stripped at collection time).

What is masked:
- token/password patterns: the values of `Bearer …`, `password=…`/`passwd:`/`pwd=`, `token=`, `api[_-]?key=`, `secret=`, `authorization:`
- credential shapes: AWS access keys (AKIA…/ASIA…), the 40 characters after an AWS secret key, JWTs (eyJ…), PEM blocks, Slack/Discord webhook URLs, GitHub tokens (ghp_…)
- base64 runs of 40 or more characters (certificate/key data)
- AWS account ids: the 12 digits inside ARNs and every known account id (from inventory) → <account>
- (optional, --ips) private IPv4 → <ip>. Off by default: an IP needed for a finding may be written individually, and not dumping the full list is a rule of the LLM procedure (SKILL.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MASK = "<masked>"

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
_PRIVATE_IP = re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})\b")
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
    from pathlib import Path

    p = Path(path)
    r = mask_text(p.read_text(encoding="utf-8"), account_ids, ips)
    if write and r.total:
        p.write_text(r.text, encoding="utf-8")
    return r

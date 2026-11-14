"""Counting log lines: which known failure pattern a line matches, and which error lines match none.

The same counting serves two callers. Component logs are counted while they are collected, from the text `kubectl logs` returned, and only the
counts are written (lib/collection/collect: no line of a component log is ever a file in the snapshot). Node logs are files of a full run and are
counted from them (lib/summaries/logs.py). `merge` joins the two results.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import Counter, defaultdict

from .logtext import normalize_message
from .mask import mask_text, strip_control
from .signatures import Signature

SAMPLES = 5  # masked sample lines kept per signature when lines are kept
ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
KLOG_TS_RE = re.compile(r"\b[IWEF](\d{2})(\d{2}) (\d{2}:\d{2}:\d{2})")
PREFIX_RE = re.compile(r"^\[pod/([^/\]]+)/([^\]]+)\] ")
# The line formats these two regexes know, with the source of each format in references/sources.md (#129): klog text (`E1104 … file.go:12] "msg" err="…"`,
# also behind the journal prefix `<host> kubelet[<pid>]: `), logfmt `level=` (go-kit: Prometheus 2.x, Loki, promtail, Alertmanager ≤0.27; slog: Prometheus 3.x,
# Alertmanager ≥0.28, spelled `INFO`/`ERROR`; logrus text, spelled `warning`), JSON `"level":` (zap, logrus JSON, go-kit JSON, zerolog; Karpenter spells
# `INFO`/`ERROR`), Elasticsearch 7 `"level": "INFO"` with a space and ECS `"log.level"`, actions-runner-controller `"severity"`, zap console (KEDA,
# actions-runner-controller text: tab-separated `\tINFO\t`), fluent-bit `[ warn]`/`[error]` (width-5 label), nginx error log `[crit] 31#31: ` (emerg,
# alert and crit are above error), zerolog console ` ERR ` (Traefik 3 default). klog JSON (`--logging-format=json`) has no level key and is not told apart.
ERROR_RE = re.compile(
    r'(?i)\b(error|fatal|panic|exception|failed|failure)\b|"(level|log\.level)":\s*"(error|fatal|critical)"|level=(error|fatal)|^\[?[^\]]*\]? ?\S* ?E\d{4} '
    r"|(?-i: ERR |\[(emerg|alert|crit)\] \d+#\d+: )"
)
NOT_ERROR_RE = re.compile(
    r'level=(info|debug|warn|warning)|"(level|log\.level)":\s*"(info|debug|warn|warning)"|"severity":"(info|debug|notice)"|\[ ?(info|debug|warn)\]|\t(INFO|DEBUG|WARN)\t'
    r'|errors=0|error=nil|error=<nil>|"error":""|error: null|RegistrationStatus',
    re.IGNORECASE,
)
# Lines whose level is info, debug or warn in any of the formats above are not errors even when the body contains "failed" (seen: actions-runner-controller
# "severity":"info" lines and ebs-csi NotifyRegistrationStatus were caught as unclassified errors; before #129 only the JSON spelling was excluded, so a
# KEDA `\tINFO\t`, Elasticsearch `"level": "INFO"`, logfmt `level=warn` or fluent-bit `[ warn]` line with a "failed" word counted as an error).
BOOT_WINDOW_S = 300  # 300 seconds after node creation or reboot. Was 120, but after a small k3s cluster node reboot the first kubelet line came 140 seconds later, so it was raised. kubelet/containerd lines within this window after node creation are boot ordering (PLEG, network not ready before CNI init) and are excluded from signatures.
ISO_TZ_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:[.,]\d+)?(Z|[+-]\d{2}:?\d{2})?")
# Any timestamp a component writes into its own line: ISO 8601 (logfmt `ts=`/`time=`, logrus `time="…"`, zap `"ts"`/`"time"`, Grafana `t=`, ECS `"@timestamp"`,
# Elasticsearch 7 `"timestamp": "…,123Z"`) or the `2026/11/05 00:05:48` form of nginx and fluent-bit (milliseconds from fluent-bit 4.1.0).
TS_ANY_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?|\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,9})?")
MAX_FILE_BYTES = 30 * 1024 * 1024


def _ts_of(line: str, today: _dt.date) -> str | None:
    """The first timestamp in the line as written (ISO 8601 with its fraction and offset when present, so `_parse_iso` keeps a `+09:00` line 9 hours apart
    from a `Z` one), else a klog header `E1104 15:10:15` completed with the year of `today`, the snapshot date (no offset: read as UTC, and by `scan` once more as node-local time)."""
    m = ISO_TZ_RE.search(line)
    if m:
        return m.group(0)
    m = KLOG_TS_RE.search(line)
    if m:
        y = today.year - 1 if (int(m.group(1)), int(m.group(2))) > (today.month, today.day) else today.year  # a January scan reads December lines as last year's
        return f"{y}-{m.group(1)}-{m.group(2)}T{m.group(3)}"
    return None


def _utc_str(ts: str | None, assume_tz: _dt.tzinfo | None = None) -> str | None:
    """`ts` from `_ts_of` as `YYYY-MM-DDTHH:MM:SSZ` in UTC, so first/last compare across pods whose containerd wrote local-time offsets. A timestamp without an
    offset (a klog header in the k3s journal) is read in `assume_tz` (the node-local zone `scan` takes from the snapshot's `taken_at`), else as UTC. None when unreadable."""
    t = _parse_iso(ts)
    if t is None:
        return None
    m = ISO_TZ_RE.search(ts or "")
    if assume_tz is not None and not (m and m.group(2)):
        t = t.replace(tzinfo=assume_tz)
    return t.astimezone(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> _dt.datetime | None:
    if not s:
        return None
    m = ISO_TZ_RE.search(s)
    if not m:
        return None
    try:
        base = _dt.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    tz = m.group(2)
    if not tz or tz == "Z":
        return base.replace(tzinfo=_dt.UTC)
    sign = 1 if tz[0] == "+" else -1
    hh, mm = int(tz[1:3]), int(tz[-2:])
    return base.replace(tzinfo=_dt.timezone(sign * _dt.timedelta(hours=hh, minutes=mm)))


def _strip_prefix(line: str) -> tuple[str, str | None]:
    """'[pod/x/y] 2026-..Z body' → (body, 'x'). Also strips the timestamp."""
    pod = None
    m = PREFIX_RE.match(line)
    if m:
        pod = m.group(1)
        line = line[m.end() :]
    line = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\s*", "", line, count=1)
    line = re.sub(r"^\S+ \S+\[\d+\]: ", "", line)  # journalctl short-iso: '<host> <unit>[<pid>]: ' (the time was stripped above)
    return line.strip(), pod


def any_regex(sigs: list[Signature]) -> re.Pattern:
    """One regex that matches a line when any of `sigs` would: the pre-filter of `scan`. A pattern that starts with the global `(?i)` becomes a scoped
    `(?i:…)` group, since Python refuses a global flag anywhere but at the start of the whole expression (the first case-insensitive patterns came with #129)."""
    parts = [f"(?i:{s.pattern[4:]})" if s.pattern.startswith("(?i)") else f"(?:{s.pattern})" for s in sigs]
    return re.compile("|".join(parts))


def match_line(line: str, sigs: list[Signature]) -> set[str]:
    """The ids of `sigs` that count `line`: every signature whose pattern matches, except that a `component: any` signature yields to a component signature
    on the same line (seen: metallb.speaker-error and common.context-deadline double-counted 533 times). `scan` and tests/test_signature_lines.py use it."""
    hit = {s.id for s in sigs if s.regex.search(line)}
    by_id = {s.id: s for s in sigs}
    if any(by_id[h].component != "any" for h in hit):
        hit = {h for h in hit if by_id[h].component != "any"}
    return hit


def normalize_unclassified(line: str) -> str:
    """The key under which an error line that matched no signature is counted: the kubectl and journal prefixes off, every timestamp the component wrote
    replaced by `<ts>` (otherwise identical errors one second apart never collapse), then `lib/foundations/logtext.normalize_message` (klog header off, numbers, ids and addresses blanked)."""
    body, _pod = _strip_prefix(line)
    body = TS_ANY_RE.sub("<ts>", body)
    body = re.sub(r'"(@?timestamp|ts|time|start time|end time)":\s*"[^"]*"', r'"\1":"<ts>"', body)  # time fields in JSON logs that TS_ANY_RE does not spell
    body = re.sub(r'"(ts|time)":\s*\d+(\.\d+)?', r'"\1":<ts>', body)  # zap EpochTimeEncoder (external-secrets `--zap-time-encoding=epoch`): seconds as a float
    msg = normalize_message(body)
    return msg if len(msg) <= 140 else msg[:140].rsplit(" ", 1)[0] + " …"  # the table shows this, so a cut is visible and ends at a word


def scan_texts(sources, sigs: list[Signature], *, taken: _dt.datetime, boot_until: dict[str, _dt.datetime] | None = None, keep_lines: bool = True) -> dict:
    """Count signature matches and unclassified error lines in log texts. `sources` yields (path, text), the path as it would be under the snapshot
    (`logs/pods/<component>/<ns>_<workload>.log`, `logs/node/<node>/<file>`): signatures choose their targets by it. The texts may come from files
    (node logs, lib/summaries/logs.py) or straight from `kubectl logs` without ever being written (component logs, lib/collection/collect). `taken`
    is the snapshot time: it completes the year of a klog header and gives the node-local zone. With `keep_lines` false no text of a line is kept:
    neither a sample nor a pattern cut from one."""
    hits: dict[str, dict] = {s.id: {"count": 0, "first": None, "last": None, "files": Counter(), "samples": []} for s in sigs}
    unclassified: Counter = Counter()
    uncl_sample: dict[str, str] = {}
    uncl_files: dict[str, Counter] = defaultdict(Counter)
    lines_total = 0
    error_lines = 0
    scanned: list[str] = []
    boot_until = boot_until or {}
    boot_skipped: Counter = Counter()
    # klog lines in the k3s journal ("E1025 13:23:38") are node-local time without a tz. Interpret them once more with the snapshot's taken_at offset (operator local = small k3s cluster node local) to compare against the boot window
    local_tz = taken.tzinfo
    today = taken.date()  # completes the year of a klog header
    for rel, data in sources:
        applicable = [s for s in sigs if s.applies_to(rel)]
        if not applicable:
            continue
        scanned.append(rel)
        any_re = any_regex(applicable)
        parts = rel.split("/")
        component = parts[2] if rel.startswith("logs/pods/") and len(parts) > 3 else ("node:" + parts[2] if rel.startswith("logs/node/") and len(parts) > 3 else rel)
        node_boot_until = boot_until.get(parts[2]) if rel.startswith("logs/node/") and len(parts) > 3 else None
        for line in data.splitlines():
            if not line.strip():
                continue
            line = strip_control(line)[0]  # Traefik's default console format colours the level and message (zerolog console.go:374-384@v1.33.0); the patterns read the text
            lines_total += 1
            matched = False
            if any_re.search(line):
                matched_ids = match_line(line, applicable)
                if node_boot_until is not None:
                    ts_txt = _ts_of(line, today)
                    lt = _parse_iso(ts_txt)
                    if lt is not None and local_tz is not None and not (ISO_RE.search(line)) and KLOG_TS_RE.search(line):
                        lt_local = lt.replace(tzinfo=local_tz)
                        lt = min(lt, lt_local, key=lambda t: abs((t - node_boot_until).total_seconds()))  # whichever interpretation is closer to the boot time
                    if lt is not None and lt <= node_boot_until:
                        # node log inside the boot window. Not counted, but marked "matched" so it does not become an unclassified error either.
                        for s in applicable:
                            if s.regex.search(line):
                                boot_skipped[s.id] += 1
                                matched = True
                        if matched:
                            continue
                for s in applicable:
                    if s.id in matched_ids:
                        matched = True
                        h = hits[s.id]
                        h["count"] += 1
                        h["files"][rel] += 1
                        ts = _utc_str(_ts_of(line, today), local_tz)
                        if ts:
                            h["first"] = min(h["first"], ts) if h["first"] else ts
                            h["last"] = max(h["last"], ts) if h["last"] else ts
                        if len(h["samples"]) < SAMPLES:
                            h["samples"].append(mask_text(line[:240]).text)  # the lines themselves are not stored; these samples are what a reader sees, so they are masked
            if not matched and ERROR_RE.search(line) and not NOT_ERROR_RE.search(line):
                error_lines += 1
                key = f"{component} | {normalize_unclassified(line)}"
                unclassified[key] += 1
                uncl_files[key][rel] += 1
                uncl_sample.setdefault(key, mask_text(line[:240]).text)
    by_id = {s.id: s for s in sigs}
    sig_rows = []
    for sid, h in hits.items():
        if h["count"] == 0:
            continue
        s = by_id[sid]
        targets = len(h["files"])  # number of distinct pod/node files. Repetition from a single target is warn, not fail (seen: one ExternalSecret repeating produced fail/high)
        sig_rows.append(
            {
                **s.public(),
                "count": h["count"],
                "first": h["first"],
                "last": h["last"],
                "files": dict(h["files"].most_common()),
                "targets": targets,
                "samples": h["samples"] if keep_lines else [],
                "status": "fail" if (h["count"] >= s.fail_at and targets >= 2) else ("warn" if h["count"] >= s.warn_at else "info"),
            }
        )
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sig_rows.sort(key=lambda r: (order.get(r["severity"], 9), -r["count"]))
    uncl_rows = [{"pattern": k, "count": c, "files": dict(uncl_files[k].most_common()), "sample": uncl_sample.get(k)} for k, c in unclassified.most_common()]
    if not keep_lines:  # a daily run counts and keeps no log text: neither a sample line nor a pattern cut from one
        uncl_rows = []
    return {
        "lines_kept": keep_lines,
        "files_scanned": scanned,
        "lines_scanned": lines_total,
        "error_lines_unclassified": error_lines,
        "signatures": sig_rows,
        "unclassified_errors": uncl_rows,
        "boot_window_skipped": dict(boot_skipped),
        "boot_window_seconds": BOOT_WINDOW_S,
    }


def merge(parts: list[dict], sigs: list[Signature]) -> dict:
    """One scan result from several (the component logs counted at collection and the node logs counted from their files): counts add up, the first
    and last time widen, the file lists join, and a signature's status is judged again on the sum."""
    parts = [p for p in parts if isinstance(p, dict)]
    by_id = {s.id: s for s in sigs}
    rows: dict[str, dict] = {}
    for p in parts:
        for r in p.get("signatures") or []:
            cur = rows.get(r["id"])
            if cur is None:
                rows[r["id"]] = {**r, "files": dict(r.get("files") or {}), "samples": list(r.get("samples") or [])}
                continue
            cur["count"] += r["count"]
            cur["first"] = min(x for x in (cur.get("first"), r.get("first")) if x) if (cur.get("first") or r.get("first")) else None
            cur["last"] = max(x for x in (cur.get("last"), r.get("last")) if x) if (cur.get("last") or r.get("last")) else None
            for f, n in (r.get("files") or {}).items():
                cur["files"][f] = cur["files"].get(f, 0) + n
            cur["samples"] = (cur["samples"] + list(r.get("samples") or []))[:SAMPLES]
    for sid, r in rows.items():
        r["targets"] = len(r["files"])
        s = by_id.get(sid)
        if s:
            r["status"] = "fail" if (r["count"] >= s.fail_at and r["targets"] >= 2) else ("warn" if r["count"] >= s.warn_at else "info")
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    uncl: dict[str, dict] = {}
    for p in parts:
        for u in p.get("unclassified_errors") or []:
            cur = uncl.setdefault(u["pattern"], {"pattern": u["pattern"], "count": 0, "files": {}, "sample": u.get("sample")})
            cur["count"] += u["count"]
            for f, n in (u.get("files") or {}).items():
                cur["files"][f] = cur["files"].get(f, 0) + n
    boot: Counter = Counter()
    for p in parts:
        boot.update(p.get("boot_window_skipped") or {})
    return {
        "lines_kept": all(p.get("lines_kept") for p in parts) if parts else False,
        "files_scanned": [f for p in parts for f in p.get("files_scanned") or []],
        "lines_scanned": sum(p.get("lines_scanned") or 0 for p in parts),
        "error_lines_unclassified": sum(p.get("error_lines_unclassified") or 0 for p in parts),
        "signatures": sorted(rows.values(), key=lambda r: (order.get(r["severity"], 9), -r["count"])),
        "unclassified_errors": sorted(uncl.values(), key=lambda u: -u["count"]),
        "boot_window_skipped": dict(boot),
        "boot_window_seconds": BOOT_WINDOW_S,
    }

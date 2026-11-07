"""Log lines as text: the klog header and the normalisation that lets errors of one kind collapse into one line (#150).

lib/controlplane groups the control-plane error samples with it and lib/logs the component log lines; it lived in controlplane and logs imported it.
"""

from __future__ import annotations

import re

# klog header `Lmmdd hh:mm:ss.uuuuuu <pid, %7d> file.go:line] ` (k8s.io/klog/v2 internal/buffer/buffer.go:117-155@v2.130.1, @v2.140.0); the file name may hold digits
# (cronjob_controllerv2.go) or a directory with --add_dir_header, hence `\S+`.
KLOG_RE = re.compile(r"^([EIWF])\d{4} [\d:.]+ +\d+ (\S+\.go):\d+\] (.*)$")


def normalize_message(msg: str) -> str:
    """Strip the klog header (time, PID, source) and blank out numbers, ids and IPs so errors of the same kind collapse into one line."""
    m = KLOG_RE.match(msg.strip())
    body = m.group(3) if m else msg.strip()
    body = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", "<ip>", body)
    body = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", body)
    body = re.sub(r"\b[a-z0-9-]+-[0-9a-f]{5,10}-[0-9a-z]{5}\b", "<pod>", body)
    body = re.sub(r"\b\d+(\.\d+)?(ms|s|m|h|µs|ns)\b", "<dur>", body)
    body = re.sub(r"\b\d{3,}\b", "<n>", body)
    return body[:160]

"""The line formats lib/summaries/logs.py reads (#129): the two classification regexes, the timestamp readers and the unclassified-error key, each on a line built
from the cited format string (references/sources.md, "Pod log formats"), plus a scan over files that mix containerd offsets and ANSI colour."""

from __future__ import annotations

import datetime as dt
import re

import pytest

from lib.foundations.logtext import KLOG_RE, normalize_message
from lib.foundations.signatures import Signature
from lib.summaries import logs

P = "[pod/x-7d9f8c6b5-abcde/main] 2026-11-05T00:10:15.100000000Z "


def _class(line: str) -> str:
    e = bool(logs.ERROR_RE.search(line))
    n = bool(logs.NOT_ERROR_RE.search(line))
    return "error" if (e and not n) else ("not-error" if n else "none")


# (format, line, expected class). Lines come from the format strings cited in references/sources.md; "failed"/"error" words are placed in info lines on purpose.
CASES = [
    # klog text (k8s.io/klog/v2 internal/buffer/buffer.go:117-155@v2.130.1), behind the kubectl prefix and behind the journal short-iso prefix
    ("klog E, kubectl", P + 'E1104 15:10:15.175726       1 scraper.go:149] "Failed to scrape node" err="x"', "error"),
    ("klog E, journal", '2026-11-04T13:20:26+0000 ip-10-0-1-5 kubelet[1234]: E1104 13:20:26.752445    1234 kubelet.go:1555] "Image garbage collection failed once"', "error"),
    ("klog E, journal, no error word", '2026-11-04T13:20:26+0000 ip-10-0-1-5 kubelet[1234]: E1104 13:20:26.752445    1234 kubelet.go:100] "Something odd"', "error"),
    ("klog I, kubectl", P + 'I1104 15:10:15.175726       1 reconciler.go:142] "Updated object" logger="cert-manager"', "none"),
    # go-kit logfmt: Prometheus 2.x (ts caller level msg) and Loki (level ts caller msg)
    ("logfmt prom2 info", P + 'ts=2026-11-05T00:10:15.175Z caller=scrape.go:1 level=info msg="Scrape failed" err="x"', "not-error"),
    ("logfmt prom2 error", P + 'ts=2026-11-05T00:10:15.175Z caller=main.go:1 level=error msg="Error loading config"', "error"),
    ("logfmt loki warn", P + 'level=warn ts=2026-11-05T00:10:15.175726273Z caller=flush.go:1 msg="failed to flush" err="x"', "not-error"),
    # slog text (Prometheus 3.x, Alertmanager 0.28+): level spelled INFO/WARN/ERROR
    ("slog info", P + 'time=2026-11-05T00:10:15.175Z level=INFO source=scrape.go:123 msg="Scrape failed" err="x"', "not-error"),
    ("slog warn", P + 'time=2026-11-05T00:10:15.175Z level=WARN source=scrape.go:123 msg="Scrape failed"', "not-error"),
    ("slog error", P + 'time=2026-11-05T00:10:15.175Z level=ERROR source=main.go:1 msg="Error loading config"', "error"),
    # zap JSON: controller-runtime default (RFC3339 ts), ESO (epoch ts), Karpenter (INFO/ERROR, time, message)
    ("zap json info", P + '{"level":"info","ts":"2026-11-03T15:37:27Z","logger":"c","msg":"failed to get"}', "not-error"),
    ("zap json error epoch", P + '{"level":"error","ts":1793760840.1233974,"logger":"c","msg":"unable to get","error":"x"}', "error"),
    ("karpenter info", P + '{"level":"INFO","time":"2026-11-05T00:10:15.175Z","logger":"controller","message":"failed to launch"}', "not-error"),
    ("karpenter error", P + '{"level":"ERROR","time":"2026-11-05T00:10:15.175Z","logger":"controller","message":"x"}', "error"),
    # zap console (KEDA manifests pass --zap-encoder=console; actions-runner-controller text): tab-separated, upper-case level
    ("zap console info", P + '2026-11-05T00:10:15Z\tINFO\tscalehandler\tfailed to get metrics\t{"scaledObject": "a"}', "not-error"),
    ("zap console error", P + '2026-11-05T00:10:15Z\tERROR\tscalehandler\tx\t{"error": "y"}', "error"),
    ("arc json info", P + '{"severity":"info","ts":"2026-11-05T00:10:15Z","logger":"l","message":"failed x"}', "not-error"),
    # logrus text (Argo CD 2.x, external-dns, vpc-cni entrypoint) and JSON (Argo CD 3.x default)
    ("logrus text warning", P + 'time="2026-11-05T00:10:15Z" level=warning msg="failed to sync"', "not-error"),
    ("logrus text error", P + 'time="2026-11-05T00:10:15Z" level=error msg="x"', "error"),
    ("logrus json warning", P + '{"level":"warning","msg":"failed to sync","time":"2026-11-05T00:10:15Z"}', "not-error"),
    # fluent-bit src/flb_log.c: [date] [%5s] label, milliseconds from 4.1.0
    ("fluent-bit warn", P + "[2026/11/05 00:05:48] [ warn] [input:tail:tail.0] failed to open", "not-error"),
    ("fluent-bit error 4.1", P + "[2026/11/05 00:05:48.123] [error] [output:es:es.0] could not pack", "error"),
    # nginx error log src/core/ngx_log.c: crit/alert/emerg are above error and carry no error word
    ("nginx crit", P + "2026/11/05 00:05:48 [crit] 31#31: *12 SSL_do_handshake() rejected, client: 1.2.3.4", "error"),
    ("nginx warn", P + "2026/11/05 00:05:48 [warn] 31#31: *12 an upstream response is buffered", "not-error"),
    ("nginx access log 502", P + '10.0.0.1 - - [05/Nov/2026:00:05:48 +0000] "GET /api HTTP/1.1" 502 150 "-" "curl/8.0" 80 0.002 [default-foo-80] [] 10.42.0.5:8080 0 0.002 502 3f2a', "none"),
    # zerolog console (Traefik 3 default): ` ERR ` label, no error word needed
    ("zerolog ERR", P + "2026-11-05T00:10:15Z ERR Skipping service: no endpoints found ingress=foo namespace=default", "error"),
    ("zerolog INF", P + "2026-11-05T00:10:15Z INF Traefik version 3.3.6 built on 2025-04-18 version=3.3.6", "none"),
    # Elasticsearch 7 ESJsonLayout (space after the colon) and 8/9 ECS (log.level)
    ("es7 info", P + '{"type": "server", "timestamp": "2026-11-05T00:05:48,123Z", "level": "INFO", "component": "o.e.c.r.a.AllocationService", "message": "failed shard"}', "not-error"),
    ("es7 error", P + '{"type": "server", "timestamp": "2026-11-05T00:05:48,123Z", "level": "ERROR", "component": "o.e.b.ElasticsearchUncaughtExceptionHandler", "message": "x"}', "error"),
    ("es8 info", P + '{"@timestamp":"2026-11-05T00:05:48.123Z", "log.level": "INFO", "message":"failed shard", "ecs.version": "1.2.0"}', "not-error"),
    ("es8 error", P + '{"@timestamp":"2026-11-05T00:05:48.123Z", "log.level":"ERROR", "message":"x", "ecs.version": "1.2.0"}', "error"),
    # etcd zap JSON in the k3s journal: warn is not an error
    ("etcd warn", '{"level":"warn","ts":"2026-11-04T13:20:26.752Z","caller":"etcdserver/util.go:171","msg":"apply request took too long"}', "not-error"),
]


@pytest.mark.parametrize(("name", "line", "expected"), CASES, ids=[c[0] for c in CASES])
def test_the_two_regexes_classify_every_known_format(name, line, expected):
    assert _class(line) == expected


def test_a_klog_json_line_has_no_level_to_read():
    # --logging-format=json (k8s.io/component-base/logs/json/json.go:66-73@v1.32.13) writes ts, caller, msg, err, v and no level key: the regexes fall back to words. Documented, not supported.
    assert _class(P + '{"ts":1762262426752.445,"caller":"kubelet.go:100","msg":"Pod failed to schedule, retrying","v":2}') == "error"


def test_ts_of_keeps_the_offset_containerd_wrote():
    # containerd stamps the CRI log line with time.Now() in the node's zone (internal/cri/io/logger.go:134@v2.1.5), so pods on one cluster mix Z and +09:00
    plus9 = "[pod/a/b] 2026-11-05T00:10:15.175726273+09:00 hello"
    zulu = "[pod/a/b] 2026-11-04T15:10:15.175726273Z hello"
    today = dt.date(2026, 11, 5)
    assert logs._ts_of(plus9, today) == "2026-11-05T00:10:15.175726273+09:00"
    assert logs._utc_str(logs._ts_of(plus9, today)) == logs._utc_str(logs._ts_of(zulu, today)) == "2026-11-04T15:10:15Z"
    assert logs._utc_str(logs._ts_of("E1104 13:20:26.752445    1316 pod_workers.go:1301] x", today)) == "2026-11-04T13:20:26Z"
    assert logs._utc_str(None) is None and logs._ts_of("no time here", today) is None


def test_klog_lines_without_an_offset_take_the_node_zone():
    # the k3s journal step strips the journal prefix, so its lines carry only the klog header (no offset); scan passes the zone of inventory.taken_at
    import datetime as dt

    kst = dt.timezone(dt.timedelta(hours=9))
    assert logs._utc_str("2026-11-05T00:10:15", kst) == "2026-11-04T15:10:15Z"
    assert logs._utc_str("2026-11-05T00:10:15", None) == "2026-11-05T00:10:15Z"
    assert logs._utc_str("2026-11-05T00:10:15+09:00", None) == "2026-11-04T15:10:15Z"
    assert logs._utc_str("2026-11-05T00:10:15Z", kst) == "2026-11-05T00:10:15Z"  # an explicit offset wins over the assumed zone


def test_klog_dates_after_the_snapshot_date_belong_to_last_year():
    # the klog header has no year (internal/buffer/buffer.go:133-142@v2.130.1): a snapshot taken on 2027-01-02 whose journal starts on 2026-12-31 must not put those lines a year ahead.
    # The year comes from the snapshot date, not the wall clock, so the same snapshot scans the same way later (#165)
    today = dt.date(2027, 1, 2)
    assert logs._ts_of("E1231 23:59:59.000000    1316 x.go:1] a", today) == "2026-12-31T23:59:59"
    assert logs._ts_of("E0102 00:00:01.000000    1316 x.go:1] a", today) == "2027-01-02T00:00:01"


def test_klog_header_with_digits_in_the_file_name_is_normalized():
    # observed: 21 copies of one cronjob_controllerv2.go line filled the top-30 list because the old KLOG_RE refused digits in the file name
    line = 'E1103 18:15:54.813376  707592 cronjob_controllerv2.go:174] "Unhandled Error" err="error syncing CronJobController a/b-123, requeuing"'
    assert KLOG_RE.match(line)
    assert normalize_message(line).startswith('"Unhandled Error" err=')


@pytest.mark.parametrize(
    "pair",
    [
        (P + 'ts=2026-11-05T00:10:15.175Z caller=main.go:1 level=error msg="x"', P + 'ts=2026-11-05T00:10:16.175Z caller=main.go:1 level=error msg="x"'),
        (P + 'time="2026-11-05T00:10:15Z" level=error msg="x"', P + 'time="2026-11-05T00:10:16Z" level=error msg="x"'),
        (P + "[2026/11/05 00:05:48.123] [error] [output:es:es.0] could not pack", P + "[2026/11/05 00:05:49.456] [error] [output:es:es.0] could not pack"),
        (P + "2026/11/05 00:05:48 [error] 31#31: *1234 connect() failed", P + "2026/11/05 00:05:49 [error] 31#31: *1235 connect() failed"),
        (P + '{"@timestamp":"2026-11-05T00:05:48.123Z", "log.level":"ERROR", "message":"x"}', P + '{"@timestamp":"2026-11-05T00:05:49.456Z", "log.level":"ERROR", "message":"x"}'),
        (P + '{"type": "server", "timestamp": "2026-11-05T00:05:48,123Z", "level": "ERROR", "message": "x"}', P + '{"type": "server", "timestamp": "2026-11-05T00:05:49,456Z", "level": "ERROR", "message": "x"}'),
        (P + '{"level":"error","ts":1793760840.1233974,"msg":"x"}', P + '{"level":"error","ts":1793760841.5,"msg":"x"}'),
    ],
    ids=["logfmt", "logrus", "fluent-bit", "nginx", "ecs", "es7", "epoch"],
)
def test_identical_errors_one_second_apart_share_one_unclassified_key(pair):
    a, b = (logs.normalize_unclassified(x) for x in pair)
    assert a == b and "2026" not in a and "00:10:1" not in a, (a, b)


def _sig(sid: str, pattern: str, sources: list[str]) -> Signature:
    return Signature(id=sid, name=sid, component="x", area="traffic", severity="low", sources=sources, regex=re.compile(pattern), pattern=pattern)


def test_scan_reads_colour_coded_lines_and_reports_first_last_in_utc(tmp_path):
    d = tmp_path / "logs" / "pods" / "traefik"
    d.mkdir(parents=True)
    coloured = "[pod/t-1/traefik] 2026-11-05T00:10:15.100000000+09:00 \x1b[90m2026-11-04T15:10:15Z\x1b[0m \x1b[31mERR\x1b[0m \x1b[1mSkipping service: no endpoints found\x1b[0m \x1b[36mingress=\x1b[0mfoo\n"
    plain = "[pod/t-2/traefik] 2026-11-04T16:00:00.000000000Z 2026-11-04T16:00:00Z ERR Skipping service: no endpoints found ingress=bar\n"
    (d / "kube-system_traefik.log").write_text(coloured + plain, encoding="utf-8")
    res = logs.scan(tmp_path, [_sig("traefik.config-error", " ERR Skipping service", ["logs/pods/traefik/*.log"])])
    row = res["signatures"][0]
    assert row["count"] == 2 and row["first"] == "2026-11-04T15:10:15Z" and row["last"] == "2026-11-04T16:00:00Z"
    assert "\x1b" not in row["samples"][0]
    assert res["error_lines_unclassified"] == 0

"""references/sources.md lists every fact kubegap relies on from another project's source, with a `path:line@tag` citation and the kubegap location (#119).
Every `type: tool` step must carry a `source:` line, so a new tool cannot be added from memory."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lib import paths, signatures, yamlite

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "references" / "sources.md"
CITATION = re.compile(r"[\w./-]+\.(?:go|py|rego|toml|yaml):\d+(?:-\d+)?(?:, ?\d+(?:-\d+)?)*@[\w.+-]+")
KUBEGAP_LOCATION = re.compile(r"`(lib/[\w/]+\.py)(?::(\w+))?`|step `([\w.-]+)`|check `([\w.-]+)`|`([A-Za-z_]\w*)`")


def _rows():
    """The rows of the `| Fact | kubegap | Source | Holds for |` tables; the signature tables (#129) have their own columns and their own test."""
    rows = []
    ours = False
    for ln in SOURCES.read_text(encoding="utf-8").splitlines():
        if ln.startswith("| Fact"):
            ours = True
        elif ln.startswith("| ") and not ln.startswith("|---"):
            if not ours:
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 4:
                rows.append(cells)
        elif not ln.startswith("|"):
            ours = False
    return rows


def test_every_row_cites_a_file_line_and_version_or_says_unverified():
    rows = _rows()
    assert len(rows) >= 40
    for fact, _where, source, _holds in rows:
        assert CITATION.search(source) or source.startswith("**unverified"), (fact, source)


def test_every_kubegap_location_exists():
    steps = {f"{Path(f).parent.name}.{s.get('id')}" for f in (ROOT / "collectors").glob("*/collect.yaml") for s in yamlite.load_file(f) or []}
    checks = {c.get("id") for f in (ROOT / "collectors").glob("*/checks.yaml") for c in yamlite.load_file(f) or []}
    lib_texts = [f.read_text(encoding="utf-8") for f in (ROOT / "lib").glob("*.py")]
    seen = 0
    for fact, where, _source, _holds in _rows():
        for m in KUBEGAP_LOCATION.finditer(where):
            seen += 1
            path, func, step, check, bare = m.groups()
            if path:
                text = (ROOT / path).read_text(encoding="utf-8")
                assert not func or f"def {func}(" in text, (fact, path, func)
            elif step:
                assert step in steps, (fact, step)
            elif check:
                assert check in checks, (fact, check)
            elif bare:
                assert any(f"def {bare}(" in t for t in lib_texts), (fact, bare, "no such function in lib/")
    assert seen >= 40


def test_every_tool_step_names_its_source():
    for f in (ROOT / "collectors").glob("*/collect.yaml"):
        for s in yamlite.load_file(f) or []:
            if s.get("type") == "tool":
                assert CITATION.search(str(s.get("source") or "")), (f.name, s.get("id"), "add a source: line citing the pinned version's file:line")


def test_every_http_step_names_its_source():
    """#126: the 22 calls to the Prometheus, Alertmanager, Loki and Grafana APIs cite the route and the response type at the versions read."""
    seen = 0
    for f in (ROOT / "collectors").glob("*/collect.yaml"):
        for s in yamlite.load_file(f) or []:
            if s.get("type") == "http":
                seen += 1
                src = str(s.get("source") or "")
                assert CITATION.search(src) or f"collectors/{f.parent.name}/pod-metrics.yaml" in src, (f.name, s.get("id"), "add a source: line citing the store's handler file:line@tag (or the pod-metrics table that carries the citations)")
    assert seen >= 22


# ---------- pod /metrics names (#120): collectors/<area>/pod-metrics.yaml ----------

VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
PARSERS = ["lib/karpenterctl.py", "lib/kedactl.py", "lib/stackhealth.py", "lib/argocdctl.py", "lib/albctl.py", "lib/certmanager.py", "lib/esoctl.py", "lib/metallbctl.py", "lib/k3s.py", "lib/logs.py"]


def test_every_pod_metrics_step_names_its_table():
    from lib import podmetrics

    for f in (ROOT / "collectors").glob("*/collect.yaml"):
        for s in yamlite.load_file(f) or []:
            if s.get("type") == "pod-metrics":
                src = str(s.get("source") or "")
                assert f"collectors/{f.parent.name}/pod-metrics.yaml" in src, (f.name, s.get("id"), "a pod-metrics step names its pod-metrics.yaml in source:")
                assert podmetrics.table(f.parent.name), (f.parent.name, "has a pod-metrics step but no pod-metrics.yaml")
    # a table may also back an http step that saves a /metrics text (Loki); then that step names it
    for t in (ROOT / "collectors").glob("*/pod-metrics.yaml"):
        steps = yamlite.load_file(t.parent / "collect.yaml") or []
        assert any(f"collectors/{t.parent.name}/pod-metrics.yaml" in str(s.get("source") or "") for s in steps), (t.parent.name, "no collect step names its pod-metrics.yaml in source:")


def test_every_pod_metric_name_has_a_source_and_a_valid_version_range():
    from lib import podmetrics

    seen = 0
    for area, entries in podmetrics.tables().items():
        keys = [e.get("key") for e in entries]
        assert len(keys) == len(set(keys)) and all(keys), (area, "duplicate or empty key")
        for e in entries:
            assert e.get("names"), (area, e.get("key"))
            for n in e["names"]:
                seen += 1
                assert CITATION.search(str(n.get("source") or "")), (area, e["key"], n.get("name"), "every spelling cites file:line@tag")
                for bound in ("since", "before"):
                    if n.get(bound) is not None:
                        assert VERSION.match(str(n[bound])), (area, e["key"], n["name"], bound, n[bound])
    assert seen >= 100


def test_every_metric_literal_in_a_parser_is_in_a_table():
    """A parser may spell a metric only as one of its area's table carries. Every metric-shaped string literal counts, in a tuple, a startswith, an `in`
    test or a .get on the parsed text; a dict key (`"x":`) and a read of another dict (`rec["x"]`, `(ld or {}).get("x")`) do not. The
    grafana_stat_totals_users typo lived in a tuple for weeks because nothing checked this."""
    from lib import podmetrics

    names = {n for a in podmetrics.tables() for n in podmetrics.all_names(a)}
    query_ids = {it["id"] for _, it in _queries()}  # a metrics.yaml query id (`loki_discarded_1h`) is not a metric name
    literal = re.compile(
        r'"((?:karpenter|argocd|certmanager|externalsecret|clustersecretstore|secretstore|grafana|keda|metallb|aws_api|controller_runtime|workqueue|rest_client|leader_election|apiserver|registered_metrics|grpc_server|loki)_[a-z0-9_]+)"'
    )
    seen = 0
    for rel in PARSERS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in literal.finditer(text):
            before, after = text[max(0, m.start() - 60) : m.start()].rstrip(), text[m.end() : m.end() + 3]
            if after.lstrip().startswith(":"):
                continue  # a summary field being built
            recv = before[:-5] if before.endswith(".get(") else before[:-1] if before.endswith("[") else None
            if recv is not None and not (recv.endswith(('pm["labeled"]', 'pm["single"]')) or re.search(r"\b(?:lb|sg|s|parsed)$", recv)):
                continue  # a read of some other dict (a summary row, a config)
            lit = m.group(1)
            if lit in query_ids:
                continue
            base = re.sub(r"_(sum|count|bucket)$", "", lit)
            seen += 1
            assert lit in names or base in names, (rel, lit, "not in any collectors/*/pod-metrics.yaml")
    assert seen >= 60


def test_the_literal_test_catches_a_tuple_typo(tmp_path, monkeypatch):
    """The old stackhealth loop spelled the typo in a tuple; the test above must see it."""
    bad = tmp_path / "lib" / "stackhealth.py"
    bad.parent.mkdir()
    bad.write_text('for k in ("grafana_stat_totals_dashboard", "grafana_stat_totals_users"):\n    if k in pm["single"]:\n        pass\n')
    import sys

    import pytest

    me = sys.modules[__name__]  # pytest may import this file under either name; patch the module object the test function closes over
    monkeypatch.setattr(me, "ROOT", tmp_path)
    monkeypatch.setattr(me, "PARSERS", ["lib/stackhealth.py"])

    with pytest.raises(AssertionError, match="grafana_stat_totals_users"):
        test_every_metric_literal_in_a_parser_is_in_a_table()


# ---------- log signatures (#129): collectors/*/signatures.yaml carry a source: list per signature ----------

# Collectors whose signatures have not been read in source yet (#129): each leaves this list in the pull request that reads its phrases. A new
# collectors/<name>/signatures.yaml is covered by default, so a signature without `source:` fails CI unless its collector is listed here.
NOT_YET_READ = [
    "alb-controller",
    "alertmanager",
    "argocd",
    "cert-manager",
    "core",
    "ebs-csi",
    "ecr",
    "eks-platform",
    "external-secrets",
    "flannel",
    "grafana",
    "k3s-platform",
    "karpenter",
    "keda",
    "kube-proxy",
    "local-path-provisioner",
    "loki",
    "metallb",
    "prometheus",
    "vpc-cni",
]
COVERED = sorted(p.parent.name for p in (ROOT / "collectors").glob("*/signatures.yaml") if p.parent.name not in NOT_YET_READ)
SIG_CITATION = re.compile(r"^[\w.-]+/[\w.-]+ \S+:\d+(,\d+)*@\S+$")


def _entries(name: str) -> list[dict]:
    return yamlite.load_file(paths.COLLECTORS_DIR / name / "signatures.yaml") or []


def _all_files():
    yield paths.SIGNATURES_DIR / "catalog.yaml"
    yield from sorted(paths.COLLECTORS_DIR.glob("*/signatures.yaml"))


def test_the_not_yet_read_list_names_only_collectors_that_exist():
    have = {p.parent.name for p in (ROOT / "collectors").glob("*/signatures.yaml")}
    assert set(NOT_YET_READ) <= have, sorted(set(NOT_YET_READ) - have)
    assert "coredns" in COVERED


@pytest.mark.parametrize("name", COVERED)
def test_covered_signatures_name_their_source(name):
    items = _entries(name)
    assert items, f"{name}: no signatures"
    missing = [it["id"] for it in items if not it.get("source")]
    assert not missing, f"{name}: signatures without source: {missing} (read the logging call in source, see references/sources.md)"


def test_every_source_entry_is_a_citation():
    bad = []
    for f in _all_files():
        for it in yamlite.load_file(f) or []:
            src = it.get("source")
            if src is None:
                continue
            if not isinstance(src, list) or not src:
                bad.append(f"{f.name}: {it['id']}: source must be a non-empty list")
                continue
            bad += [f"{f.name}: {it['id']}: {s!r}" for s in src if not SIG_CITATION.match(str(s))]
    assert not bad, "source entries must read '<owner>/<repo> <path>:<line>@<tag>':\n" + "\n".join(bad)


def test_covered_collectors_are_documented():
    text = (paths.ROOT / "references" / "sources.md").read_text(encoding="utf-8")
    for name in COVERED:
        for it in _entries(name):
            assert f"`{it['id']}`" in text, f"{it['id']} has a source key but no row in references/sources.md"


# ---------- CoreDNS lines built from the cited format strings ----------

# plugin/errors/errors.go:97@v1.11.3 "%d %s %s: %s" after "[ERROR] " (plugin/pkg/log/log.go:101) and "plugin/errors: " (plugin/pkg/log/plugin.go:15)
ERR_TIMEOUT = "2026-11-04T02:10:00.000000000Z [ERROR] plugin/errors: 2 example.com. A: read udp 10.42.0.5:48711->1.1.1.1:53: i/o timeout"
ERR_NO_HEALTHY = "2026-11-04T02:10:00.000000000Z [ERROR] plugin/errors: 2 example.com. AAAA: no healthy proxies"
ERR_UNREACHABLE = "2026-11-04T02:10:00.000000000Z [ERROR] plugin/errors: 2 example.com. A: dial udp 1.1.1.1:53: connect: network is unreachable"
# plugin/log/log.go:69@v1.11.3 CommonLogFormat with {rcode} from dns.RcodeToString (plugin/pkg/replacer/replacer.go:67)
QUERY_SERVFAIL = '2026-11-04T02:10:00.000000000Z [INFO] 10.42.0.9:53412 - 4242 "A IN example.com. udp 29 false 512" SERVFAIL qr,rd 29 0.000123s'
QUERY_NOERROR = '2026-11-04T02:10:00.000000000Z [INFO] 10.42.0.9:53412 - 4242 "A IN example.com. udp 29 false 512" NOERROR qr,rd,ra 45 0.000123s'
# plugin/loop/loop.go:53@v1.11.3 Fatalf
LOOP = '2026-11-04T02:10:00.000000000Z [FATAL] plugin/loop: Loop (127.0.0.1:55953 -> :53) detected for zone ".", see https://coredns.io/plugins/loop#troubleshooting. Query: "HINFO 4547991504243258144.3688648895315093531."'
# plugin/reload/reload.go:97 and :111@v1.11.3; coredns/caddy caddyfile/dispenser.go:229@v1.1.1
RELOAD_PARSE = "2026-11-04T02:10:00.000000000Z [WARNING] plugin/reload: Corefile parse failed: Corefile:7 - Error during parsing: Unknown directive 'cahce'"
RELOAD_RESTART = "2026-11-04T02:10:00.000000000Z [ERROR] plugin/reload: Corefile changed but reload failed: plugin/forward: /etc/coredns/Corefile:9 - Error during parsing: Wrong argument count or unexpected line ending after '.'"
RELOAD_OK = "2026-11-04T02:10:00.000000000Z [INFO] plugin/reload: Running configuration SHA512 = 0f2a"


@pytest.fixture(scope="module")
def coredns():
    sigs, errors = signatures.load(["coredns"])
    assert not errors
    return {s.id: s for s in sigs if s.component == "coredns"}


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (ERR_TIMEOUT, {"coredns.upstream-timeout"}),  # one outage, one finding: the timeout line is not also a servfail line
        (ERR_NO_HEALTHY, {"coredns.servfail"}),
        (ERR_UNREACHABLE, {"coredns.upstream-timeout"}),
        (QUERY_SERVFAIL, {"coredns.servfail"}),
        (QUERY_NOERROR, set()),
        (LOOP, {"coredns.loop"}),
        (RELOAD_PARSE, {"coredns.reload-failed"}),
        (RELOAD_RESTART, {"coredns.reload-failed"}),
        (RELOAD_OK, set()),
    ],
)
def test_coredns_patterns_match_what_coredns_prints(coredns, line, expected):
    assert {sid for sid, s in coredns.items() if s.regex.search(line)} == expected


def test_coredns_servfail_matches_without_the_log_plugin(coredns):
    # The default k3s Corefile has no `log` plugin (manifests/coredns.yaml@v1.33.5+k3s1), so the errors line is the only SERVFAIL CoreDNS writes. #129
    assert "SERVFAIL" not in ERR_NO_HEALTHY
    assert coredns["coredns.servfail"].regex.search(ERR_NO_HEALTHY)


def test_one_upstream_outage_is_one_finding(tmp_path):
    """250 timeout lines on each of two pods: coredns.upstream-timeout fails (500 >= 200) and coredns.servfail counts nothing, so the outage is not two findings."""
    from lib import logs

    d = tmp_path / "logs" / "pods" / "coredns"
    d.mkdir(parents=True)
    for pod in ("a", "b"):
        (d / f"kube-system_coredns-{pod}.log").write_text((ERR_TIMEOUT + "\n") * 250 + ERR_NO_HEALTHY + "\n", encoding="utf-8")
    sigs, errors = signatures.load(["coredns"])
    assert not errors
    counts = {r["id"]: r["count"] for r in logs.scan(tmp_path, sigs)["signatures"]}
    assert counts.get("coredns.upstream-timeout") == 500 and counts.get("coredns.servfail") == 2


# ---------- PromQL queries (#121, #122, #123): every query that reads a node-exporter, cAdvisor, kubelet, kube-state-metrics, apiserver, CoreDNS, kube-proxy,
# EBS CSI, kubelet volume, client-go, Prometheus, Alertmanager, Loki, promtail, Fluent Bit, KEDA or ingress-controller name, or a series Prometheus writes
# itself (`up`, `scrape_*`, `ALERTS`, `ALERTS_FOR_STATE`), cites each name ----------

QUERY_FAMILIES = re.compile(
    r"\b(node_[A-Za-z0-9_]+|kube_[A-Za-z0-9_]+|kubelet_[A-Za-z0-9_]+|container_[A-Za-z0-9_]+|apiserver_[A-Za-z0-9_]+|coredns_[A-Za-z0-9_]+|kubeproxy_[A-Za-z0-9_]+"
    r"|aws_ebs_csi_[A-Za-z0-9_]+|cloudprovider_aws_[A-Za-z0-9_]+|csi_operations_seconds_[a-z]+|storage_operation_duration_seconds_[a-z]+|rest_client_requests_total"
    r"|prometheus_[A-Za-z0-9_]+|alertmanager_[A-Za-z0-9_]+|promtail_[A-Za-z0-9_]+|loki_[A-Za-z0-9_]+|fluentbit_[A-Za-z0-9_]+|keda_[A-Za-z0-9_]+"
    r"|nginx_ingress_controller_[A-Za-z0-9_]+|traefik_[A-Za-z0-9_]+|scrape_duration_seconds|scrape_samples_scraped|ALERTS_FOR_STATE|ALERTS)\b"
)
# a `{__name__=~"<pattern>"}` selector reads every name the pattern matches; the entries are expected to name each of them, which the test cannot enumerate,
# so it requires at least one entry the pattern matches on every selector that spells a cited family (a `.+` or `http_.*` selector reads no cited family)
NAME_SELECTOR = re.compile(r'__name__=~"([^"]+)"')
FAMILY_PREFIX = re.compile(
    r"(?<![A-Za-z0-9_])(node_|kube_|kubelet_|container_|apiserver_|coredns_|kubeproxy_|aws_ebs_csi|cloudprovider_aws|csi_operations_seconds|storage_operation_duration_seconds|rest_client_requests"
    r"|prometheus_|alertmanager_|promtail_|loki_|fluentbit_|keda_|nginx_ingress_controller_|traefik_)"
)
# '<name>: <owner>/<repo> <file>:<line>@<tag>' then more citations and notes; or 'label <what>: ...' for a label the scrape configuration sets
QUERY_CITATION = re.compile(r"^(?:[A-Za-z_:][A-Za-z0-9_:]*|label [^:]+): [\w.-]+/[\w.-]+ \S+?:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*@[\w.+-]+")
# Names an exporter removed, renamed or leaves off by default, with the source that says so. A query reading one is empty on every default install and nothing tells
# "the situation did not occur" from "the series does not exist". node_processes_state may come back behind a `needs` that reads the collector state
# once a check needs it; today nothing does.
GONE = {
    "kube_endpoint_address_not_ready": 'kube-state-metrics 2.14.0 removed it (internal/store/endpoint.go:148@v2.13.0, absent @v2.14.0); read kube_endpoint_address{ready="false"}',
    "node_processes_state": "the node-exporter processes collector is off by default (collector/processes_linux.go:46@v1.7.0, :45@v1.10.2, :44@v1.12.1)",
    "coredns_forward_request_duration_seconds_bucket": "CoreDNS 1.11.0 moved it to coredns_proxy_request_duration_seconds{proxy_name} (plugin/forward/metrics.go:27@v1.10.1, plugin/pkg/proxy/metrics.go:15@v1.11.0)",
    "coredns_forward_request_duration_seconds_count": "CoreDNS 1.11.0 moved it to coredns_proxy_request_duration_seconds{proxy_name} (plugin/forward/metrics.go:27@v1.10.1, plugin/pkg/proxy/metrics.go:15@v1.11.0)",
    "coredns_forward_healthcheck_failures_total": "CoreDNS 1.11.0 moved it to coredns_proxy_healthcheck_failures_total{proxy_name} (plugin/forward/metrics.go:34@v1.10.1, plugin/pkg/proxy/metrics.go:23@v1.11.0)",
}


def _queries():
    for f in sorted((ROOT / "collectors").glob("*/metrics.yaml")):
        for it in yamlite.load_file(f) or []:
            yield f.parent.name, it


def _query_names(query: str) -> tuple[set[str], list[str]]:
    """The names a query reads outside its `__name__` selectors, and the patterns of those selectors."""
    patterns = [pat for pat in NAME_SELECTOR.findall(query) if FAMILY_PREFIX.search(pat)]
    rest = NAME_SELECTOR.sub("", query).replace("{apiserver_job}", "")  # the job placeholder of #140 is not a metric name
    names = set(QUERY_FAMILIES.findall(rest))
    if re.search(r"\bup\b", rest):  # `up{...}` and the bare `up == 0`
        names.add("up")
    return names, patterns


@pytest.mark.parametrize(
    ("query", "names", "patterns"),
    [
        ('count({__name__=~"aws_ebs_csi_.*"})', set(), ["aws_ebs_csi_.*"]),
        ('count({__name__=~"(aws_ebs_csi|cloudprovider_aws)_api_request_duration_seconds_count"})', set(), ["(aws_ebs_csi|cloudprovider_aws)_api_request_duration_seconds_count"]),
        ('sum({__name__=~"apiserver_.*"})', set(), ["apiserver_.*"]),
        ('sum(increase({__name__=~"kubeproxy_sync_proxy_rules_iptables_.*restore_failures_total"}[24h]))', set(), ["kubeproxy_sync_proxy_rules_iptables_.*restore_failures_total"]),
        ('topk(20, count by (__name__) ({__name__=~".+"}))', set(), []),
        ('count by (namespace) ({__name__=~"http_requests_total|grpc_server_handled_total"})', set(), []),
        ('count(up{job=~".*coredns.*"} == 1)', {"up"}, []),
        ("count by (job) (up == 0)", {"up"}, []),
        ("count(prometheus_build_info)", {"prometheus_build_info"}, []),
        ('count by (exported_namespace, ingress) ({__name__=~"nginx_ingress_controller_requests|traefik_service_requests_total"})', set(), ["nginx_ingress_controller_requests|traefik_service_requests_total"]),
        ("sum by (instance) (promtail_targets_active_total)", {"promtail_targets_active_total"}, []),
        ('count by (alertname) (count_over_time(ALERTS{alertstate="firing"}[15d]))', {"ALERTS"}, []),
        ('(time() - ALERTS_FOR_STATE{alertname!="Watchdog"}) / 86400 > 3', {"ALERTS_FOR_STATE"}, []),
        ("sum by (name) (increase(fluentbit_output_errors_total[1h])) > 0", {"fluentbit_output_errors_total"}, []),
        ('node_network_up{device=~"flannel.*"}', {"node_network_up"}, []),
        ('sum(rate(apiserver_request_total{job="apiserver",code="401"}[1h]))', {"apiserver_request_total"}, []),
    ],
)
def test_query_names_recognize_the_cited_families_and_their_selectors(query, names, patterns):
    assert _query_names(query) == (names, patterns)


def test_every_query_of_the_read_families_cites_each_name():
    seen = 0
    for area, it in _queries():
        names, patterns = _query_names(str(it["query"]))
        if not names and not patterns:
            continue
        seen += 1
        src = it.get("source")
        assert isinstance(src, list) and src, (area, it["id"], "a query reading one of the cited families needs a source: list, one entry per name")
        subjects = set()
        for e in src:
            assert QUERY_CITATION.match(str(e)), (area, it["id"], e, "an entry reads '<name>: <owner>/<repo> <file>:<line>@<tag> ...'")
            subjects.add(str(e).split(":", 1)[0])
        assert names <= subjects, (area, it["id"], sorted(names - subjects), "every name the query reads has an entry")
        for pat in patterns:
            assert any(re.fullmatch(pat, s) for s in subjects), (area, it["id"], pat, "a __name__ selector that spells a cited family needs an entry the pattern matches")
    assert seen >= 170


def test_no_query_reads_a_name_the_exporter_removed_or_leaves_off():
    for area, it in _queries():
        for name in QUERY_FAMILIES.findall(str(it["query"])):
            assert name not in GONE, (area, it["id"], name, GONE.get(name))


def _query_text(qid: str) -> str:
    qs = {it["id"]: " ".join(str(it["query"]).split()) for _, it in _queries()}
    assert qid in qs, qid
    return qs[qid]


def test_endpoint_address_counts_collapse_the_per_port_series():
    """Since kube-state-metrics 2.14.0 kube_endpoint_address has one series per address and port (internal/store/endpoint.go:136-153@v2.14.0); a plain
    count would give addresses times ports for a Service with more than one port, and before 2.14.0 the same expression counts one series per address."""
    for qid, ready in (("endpoint_ready_addresses", "true"), ("endpoint_not_ready_addresses", "false")):
        assert f'count by (namespace, endpoint) (count by (namespace, endpoint, ip) (kube_endpoint_address{{ready="{ready}"}}))' in _query_text(qid), qid


def test_every_apiserver_selector_filters_on_the_apiserver_job():
    """On k3s the kubelet scrape serves the apiserver's registry a second time (k3s pkg/daemons/executor/embed.go:77,99,126@v1.33.5+k3s1); a sum without
    the job filter doubled (observed 1274 watches for one node)."""
    seen = 0
    for area, it in _queries():
        q = " ".join(str(it["query"]).split())
        for m in re.finditer(r"\bapiserver_[A-Za-z0-9_]+(\{(?:[^{}]|\{[^{}]*\})*\})?", q):
            seen += 1
            assert m.group(1) and 'job="{apiserver_job}"' in m.group(1), (area, it["id"], m.group(0), 'every apiserver_* selector carries job="{apiserver_job}", filled per run (#140)')
    assert seen >= 13


def test_the_stored_object_queries_read_the_old_and_the_new_name():
    """apiserver_storage_objects is deprecated since 1.34.0 and hidden from 1.37 (component-base registry.go:47-70,74-83@v1.37.2); apiserver_resource_objects exists
    since 1.34 (storage/etcd3/metrics/metrics.go:91-95@v1.34.13). lib/controlplane.py reads the new query first."""
    assert _query_text("apiserver_storage_objects_top") == 'topk(15, apiserver_storage_objects{job="{apiserver_job}"})'
    assert _query_text("apiserver_resource_objects_top") == 'topk(15, apiserver_resource_objects{job="{apiserver_job}"})'


def test_the_no_local_endpoints_gauge_is_read_as_a_value_never_as_a_rate():
    """kubeproxy_sync_proxy_rules_no_local_endpoints_total is a gauge of Services (pkg/proxy/metrics/metrics.go:269-276@v1.33.5); increase() over it measured nothing."""
    for area, it in _queries():
        q = " ".join(str(it["query"]).split())
        assert not re.search(r"(increase|rate|irate|delta)\(kubeproxy_sync_proxy_rules_no_local_endpoints_total", q), (area, it["id"])
    assert _query_text("kubeproxy_no_local_endpoint_services") == "max by (instance, traffic_policy) (kubeproxy_sync_proxy_rules_no_local_endpoints_total)"


def test_the_restore_failure_counters_are_read_by_two_queries_that_the_library_adds():
    """Since 1.33 each counter has a series only after its first failure and in ipvs mode only the full one is registered (pkg/proxy/metrics/metrics.go:159-181,343-351@v1.33.5);
    one expression adding the two was empty whenever one side had no series, and increase() over a __name__ selector matching both is refused (same label set)."""
    assert _query_text("kubeproxy_restore_failures_24h") == "sum by (instance) (increase(kubeproxy_sync_proxy_rules_iptables_restore_failures_total[24h]))"
    assert _query_text("kubeproxy_partial_restore_failures_24h") == "sum by (instance) (increase(kubeproxy_sync_proxy_rules_iptables_partial_restore_failures_total[24h]))"
    for area, it in _queries():
        q = " ".join(str(it["query"]).split())
        assert not ("iptables_restore_failures_total" in q and "partial_restore_failures_total" in q), (area, it["id"], "one query must not add the two counters")


def test_the_iptables_rule_query_adds_the_ip_families():
    """Since 1.33 kubeproxy_sync_proxy_rules_iptables_total has one series per ip_family (pkg/proxy/metrics/metrics.go:186-190@v1.33.5); a max picked the larger family."""
    assert _query_text("kubeproxy_iptables_rules") == "sum by (instance, table) (kubeproxy_sync_proxy_rules_iptables_total)"


def test_the_ebs_csi_controller_queries_read_both_name_generations():
    """The aws_ebs_csi_ names exist since driver v1.38.1 (pkg/cloud/handlers.go:47,52,60@v1.38.1); before, cloudprovider_aws_ (handlers.go:47,49,54@v1.37.0). A count over
    aws_ebs_csi_.* also counted the node plugin's NVMe series (pkg/metrics/nvme.go:41-60@v1.38.1)."""
    errors = _query_text("ebscsi_api_errors_24h")
    assert "increase(aws_ebs_csi_api_request_errors_total[24h]) or increase(cloudprovider_aws_api_request_errors[24h])" in errors, errors
    throttles = _query_text("ebscsi_api_throttles_24h")
    assert "increase(aws_ebs_csi_api_request_throttles_total[24h]) or increase(cloudprovider_aws_api_throttled_requests_total[24h])" in throttles, throttles
    count = _query_text("ebscsi_controller_metrics_series")
    pat = NAME_SELECTOR.search(count)
    assert pat, count
    for name in ("aws_ebs_csi_api_request_duration_seconds_count", "cloudprovider_aws_api_request_duration_seconds_count"):
        assert re.fullmatch(pat.group(1), name), (pat.group(1), name)
    assert not re.fullmatch(pat.group(1), "aws_ebs_csi_read_ops_total"), "the node plugin's NVMe series must not count as controller metrics"


def test_the_ebs_csi_kubelet_queries_match_the_ebs_driver_exactly():
    """storage_operation_duration_seconds carries volume_plugin kubernetes.io/csi:<driver> (pkg/volume/util/metrics.go:120-129@v1.30.14); a kubernetes.io/csi.* pattern
    counted every CSI driver's failures as EBS."""
    for qid in ("ebscsi_storage_ops_by_status_24h", "ebscsi_storage_ops_p99_24h"):
        q = _query_text(qid)
        assert 'volume_plugin="kubernetes.io/csi:ebs.csi.aws.com"' in q and "csi.*" not in q, (qid, q)
    for qid in ("ebscsi_node_ops_by_status_24h", "ebscsi_node_ops_p99_24h"):
        assert 'driver_name="ebs.csi.aws.com"' in _query_text(qid), qid


def test_the_servfail_ratio_has_a_zero_numerator_when_no_servfail_series_exists():
    """A rate of a series that never existed is empty (observed on EKS), so without the fallback the ratio was missing instead of 0."""
    q = _query_text("coredns_servfail_ratio_1h")
    assert q.startswith('(sum(rate(coredns_dns_responses_total{rcode="SERVFAIL"}[1h])) or vector(0)) / sum(rate(coredns_dns_responses_total[1h]))'), q


def _query(area: str, qid: str) -> dict:
    return next(it for a, it in _queries() if a == area and it["id"] == qid)


def test_the_replica_count_reads_one_series_per_prometheus_process():
    """kube-prometheus-stack scrapes two ports of each Prometheus pod under one job (web and reloader-web), so `count(up{job=~".*prometheus$"} == 1)`
    read 2 for a single replica; prometheus_build_info is served by the Prometheus process only, once."""
    q = _query("prometheus", "prom_replicas")
    assert q["query"] == "count(prometheus_build_info)"
    assert any(str(e).startswith("prometheus_build_info: ") for e in q["source"])
    assert any(str(e).startswith("label job on these self series: ") and "reloader-web" in str(e) for e in q["source"])


def test_the_sample_limit_counter_is_summed_without_a_job_label():
    """prometheus_target_scrapes_exceeded_sample_limit_total is one Counter per Prometheus with no target label (scrape/metrics.go); a `sum by (job)`
    grouped it by the Prometheus's own job. The library names the targets from prometheus/targets.json instead."""
    q = str(_query("prometheus", "prom_sample_limit_exceeded_1h")["query"])
    assert "prometheus_target_scrapes_exceeded_sample_limit_total" in q and "by (job)" not in q
    slow = str(_query("prometheus", "prom_scrape_interval_s")["why"])
    assert "targets.json" in slow, "the interval query is the fallback; targets.json carries each job's own scrapeInterval"


def test_the_two_up_equals_zero_queries_cite_up():
    for area, qid in (("core", "targets_down"), ("prometheus", "scrape_targets_down_by_job")):
        q = _query(area, qid)
        assert "up" in _query_names(str(q["query"]))[0]
        assert any(str(e).startswith("up: prometheus/prometheus scrape/scrape.go") for e in q["source"]), (area, qid)


def test_the_keda_error_query_reads_only_the_counter_that_carries_a_scaled_object():
    """keda_scaler_errors_total is a plain total with no labels at every version (prommetrics.go:49@v2.12.0, :110@v2.16.0); grouped by namespace and scaledObject
    it yields one row with empty labels that no ScaledObject matches."""
    q = str(_query("core", "keda_scaler_errors_24h")["query"])
    assert "keda_scaler_detail_errors_total" in q and "keda_scaler_errors_total" not in q


def test_the_loki_table_carries_both_retention_names():
    from lib import podmetrics

    names = podmetrics.entry("loki", "retention_last_run")["names"]
    assert [n["name"] for n in names] == ["loki_compactor_apply_retention_last_successful_run_timestamp_seconds", "loki_boltdb_shipper_apply_retention_last_successful_run_timestamp_seconds"]
    assert names[0]["since"] == "3.0.0" and names[1]["before"] == "3.0.0"
    assert podmetrics.candidates("loki", "compactor_running") == ["loki_boltdb_shipper_compactor_running"]


def test_every_version_a_query_cites_is_named_in_sources():
    text = SOURCES.read_text(encoding="utf-8")
    tags = set()
    for _, it in _queries():
        for e in it.get("source") or []:
            tags |= set(re.findall(r"@([\w.+-]+)", str(e)))
    assert len(tags) >= 60
    missing = sorted(t for t in tags if t not in text)
    assert not missing, (missing, "name the version in the PromQL section of references/sources.md")

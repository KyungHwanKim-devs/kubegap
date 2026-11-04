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


# ---------- pod /metrics names (#120): collectors/<area>/pod-metrics.yaml ----------

VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
PARSERS = ["lib/karpenterctl.py", "lib/kedactl.py", "lib/stackhealth.py", "lib/argocdctl.py", "lib/albctl.py", "lib/certmanager.py", "lib/esoctl.py", "lib/metallbctl.py", "lib/k3s.py"]


def test_every_pod_metrics_step_names_its_table():
    from lib import podmetrics

    for f in (ROOT / "collectors").glob("*/collect.yaml"):
        for s in yamlite.load_file(f) or []:
            if s.get("type") == "pod-metrics":
                src = str(s.get("source") or "")
                assert f"collectors/{f.parent.name}/pod-metrics.yaml" in src, (f.name, s.get("id"), "a pod-metrics step names its pod-metrics.yaml in source:")
                assert podmetrics.table(f.parent.name), (f.parent.name, "has a pod-metrics step but no pod-metrics.yaml")


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
    literal = re.compile(
        r'"((?:karpenter|argocd|certmanager|externalsecret|clustersecretstore|secretstore|grafana|keda|metallb|aws_api|controller_runtime|workqueue|rest_client|leader_election|apiserver|registered_metrics|grpc_server)_[a-z0-9_]+)"'
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

COVERED = ["coredns"]
SIG_CITATION = re.compile(r"^[\w.-]+/[\w.-]+ \S+:\d+(,\d+)*@\S+$")


def _entries(name: str) -> list[dict]:
    return yamlite.load_file(paths.COLLECTORS_DIR / name / "signatures.yaml") or []


def _all_files():
    yield paths.SIGNATURES_DIR / "catalog.yaml"
    yield from sorted(paths.COLLECTORS_DIR.glob("*/signatures.yaml"))


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
        (ERR_TIMEOUT, {"coredns.servfail", "coredns.upstream-timeout"}),
        (ERR_NO_HEALTHY, {"coredns.servfail"}),
        (ERR_UNREACHABLE, {"coredns.servfail", "coredns.upstream-timeout"}),
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

"""Facts about other software carry their source (references/sources.md, #129).

Every signature of a collector in COVERED needs a `source:` list of "<owner>/<repo> <path>:<line>@<tag>" entries naming the logging call.
A collector joins COVERED in the pull request that reads its phrases in source; once every collector and signatures/catalog.yaml are in, the list goes away.
The sample lines below are built from the format strings cited in sources.md, so a pattern that drifts away from what the component prints fails here.
"""

from __future__ import annotations

import re

import pytest

from lib import paths, signatures, yamlite

COVERED = ["coredns"]
CITATION = re.compile(r"^[\w.-]+/[\w.-]+ \S+:\d+(,\d+)*@\S+$")


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
            bad += [f"{f.name}: {it['id']}: {s!r}" for s in src if not CITATION.match(str(s))]
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

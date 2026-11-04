"""references/sources.md lists every fact kubegap relies on from another project's source, with a `path:line@tag` citation and the kubegap location (#119).
Every `type: tool` step must carry a `source:` line, so a new tool cannot be added from memory."""

from __future__ import annotations

import re
from pathlib import Path

from lib import yamlite

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "references" / "sources.md"
CITATION = re.compile(r"[\w./-]+\.(?:go|py|rego|toml|yaml):\d+(?:-\d+)?(?:, ?\d+(?:-\d+)?)*@[\w.+-]+")
KUBEGAP_LOCATION = re.compile(r"`(lib/[\w/]+\.py)(?::(\w+))?`|step `([\w.-]+)`|check `([\w.-]+)`|`([A-Za-z_]\w*)`")


def _rows():
    rows = []
    for ln in SOURCES.read_text(encoding="utf-8").splitlines():
        if ln.startswith("| ") and not ln.startswith("| Fact") and not ln.startswith("|---"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 4:
                rows.append(cells)
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
METRIC_LITERAL = re.compile(
    r'"((?:karpenter|argocd|certmanager|externalsecret|clustersecretstore|secretstore|grafana|keda|metallb|aws_api|controller_runtime|workqueue|rest_client|leader_election|apiserver|registered_metrics|grpc_server|process)_[a-z0-9_]+)"'
)
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
    """A parser may read a metric only under a spelling its area's table carries; the grafana_stat_totals_users typo lived for weeks because nothing checked this."""
    from lib import podmetrics

    names = {n for a in podmetrics.tables() for n in podmetrics.all_names(a)}
    # a read of a parsed /metrics text: pm["labeled"].get(...), pm["single"].get(...), the lb/sg/s shorthands the parsers use, or a startswith on a raw line
    read = re.compile(
        r'(?:pm\["(?:labeled|single)"\]\.get|\b(?:lb|sg|s)\.get|startswith)\("((?:karpenter|argocd|certmanager|externalsecret|clustersecretstore|secretstore|grafana|keda|metallb|aws_api|controller_runtime|workqueue|rest_client|leader_election|apiserver|registered_metrics|grpc_server|process)_[a-z0-9_]+)'
    )
    seen = 0
    for rel in PARSERS:
        for m in read.finditer((ROOT / rel).read_text(encoding="utf-8")):
            lit = m.group(1)
            base = re.sub(r"_(sum|count|bucket)$", "", lit)
            seen += 1
            assert lit in names or base in names, (rel, lit, "not in any collectors/*/pod-metrics.yaml")
    assert seen >= 40

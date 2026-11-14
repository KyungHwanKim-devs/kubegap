"""A summary is a set of facts computed from the raw files, and a fact is not cut. `rows[:40]` once made a check judge 40 of 69 rows and
`names[:6]` made a report say 11 workloads where there were 15 (2026-11-14): the reader of a cut list cannot know it was cut.

So under lib/summaries nothing is shortened by a constant, neither `x[:N]` nor `Counter.most_common(N)`, except the expressions listed in
tests/data/summary-cuts-allowed.tsv. Those are text (a message trimmed to 160 characters, the date part of a timestamp), tuples, and a few
samples of raw text lines that carry their total next to them. A new line in that file is a decision someone has to make and write down."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path("lib/summaries")
ALLOWED = Path("tests/data/summary-cuts-allowed.tsv")


def _const(b) -> bool:
    return isinstance(b, ast.Constant) or (isinstance(b, ast.UnaryOp) and isinstance(b.operand, ast.Constant))


def cuts() -> list[tuple[str, str, str]]:
    """(file, the expression that is cut, how) for every constant slice and every most_common(n) under lib/summaries."""
    out = []
    for path in sorted(ROOT.rglob("*.py")):
        src = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                bounds = [b for b in (node.slice.lower, node.slice.upper) if b is not None]
                if bounds and all(_const(b) for b in bounds):
                    out.append((str(path.relative_to(ROOT)), " ".join(ast.unparse(node.value).split()), "[" + ast.unparse(node.slice) + "]"))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "most_common" and node.args:
                out.append((str(path.relative_to(ROOT)), " ".join(ast.unparse(node.func.value).split()), f".most_common({ast.unparse(node.args[0])})"))
    return out


def allowed() -> set[tuple[str, str, str]]:
    rows = [ln.split("\t") for ln in ALLOWED.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    return {(r[0], r[1], r[2]) for r in rows}


def test_no_list_is_cut_in_the_summaries():
    extra = sorted(set(cuts()) - allowed())
    assert extra == [], "a summary keeps whole lists; if this is text, a tuple or a counted sample, add it to tests/data/summary-cuts-allowed.tsv with the reason:\n" + "\n".join("\t".join(e) for e in extra)


def test_the_allowed_list_has_no_stale_entries():
    assert sorted(allowed() - set(cuts())) == []


def test_a_summary_row_holds_as_many_as_the_raw_objects_do():
    """Counted independently from the raw objects of the committed k3s snapshot: every workload whose spec names the ConfigMap. The summary
    once kept the first six of ten."""
    import json
    import tempfile

    from lib.commands import regress

    fixture = next(f for f in regress.fixtures() if f.name.endswith("-k3s"))
    with tempfile.TemporaryDirectory() as d:
        snap = regress.stage(fixture, Path(d))
        regress.run(snap)
        summary = json.loads((snap / "summary.json").read_text())
        for row in summary["security"]["secrets"]["plaintext_configmap"]:
            ns, name = row["namespace"], row["name"]
            users = set()
            for kind in ("cronjobs", "deployments", "statefulsets", "daemonsets"):
                for o in json.loads((snap / "objects" / f"{kind}.json").read_text())["items"]:
                    if o["metadata"]["namespace"] == ns and f'"{name}"' in json.dumps(o.get("spec")):
                        users.add(o["metadata"]["name"])
            assert len(row["mounted_by"]) == len(users), (row["target"], sorted(users), row["mounted_by"])


def test_an_evidence_sentence_that_shows_part_of_a_list_says_how_many_more():
    from lib.judgement.evaluate.evidence import shown

    assert shown(["a", "b"], 6) == "['a', 'b']"
    assert shown(list("abcdefgh"), 3) == "['a', 'b', 'c'] and 5 more"
    assert shown("x" * 10, 4) == "xxxx…" and shown(None, 3) == "[]"
    # the check definitions do not cut a list by hand: they call shown(), which names the remainder
    import re

    for path in sorted(Path("collectors").glob("*/checks.yaml")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith(("evidence:", "target:")):
                left = [m.group(0) for m in re.finditer(r"\w+(?:\['\w+'\])?\[:\d+\]", line) if not m.group(0).startswith(("s[", "e['pattern']", "item['changed_at']"))]
                assert left == [], f"{path}:{n}: {left} cuts a list in an evidence sentence; use shown(list, n)"
                assert not re.search(r"(join|sorted|len|set|list)\(shown\(", line), f"{path}:{n}: shown() returns text; it is the last thing done to a list"


def test_a_query_that_feeds_a_verdict_does_not_ask_for_the_top_n_only():
    """`topk(300, ratio)` kept the 300 largest ratios, so on a cluster with more containers the check for the smallest ratios
    (over-provisioned requests) saw none of them. Only a query that is a ranking by its name (…_top, …_slow_…) may ask for the top N."""
    import re

    from lib.foundations import yamlite

    for path in sorted(Path("collectors").glob("*/metrics.yaml")):
        for q in yamlite.load_file(path) or []:
            if re.search(r"\b(topk|bottomk)\(", str(q.get("query") or "")):
                assert re.search(r"(^|_)(top|slow)(_|$)", q["id"]), f"{path}: {q['id']} cuts its result with topk; filter by a condition instead, or name it a ranking"

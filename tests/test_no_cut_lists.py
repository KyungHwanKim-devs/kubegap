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

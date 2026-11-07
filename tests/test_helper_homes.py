"""Every small job has one home under lib/ (#150), and the duplicates that were swept out cannot come back.

Three readings of the sources: a private helper with the same body in two modules, a function whose name is one of the jobs that have a home, and the
inline forms of those jobs (a unit table, an image-tag regular expression, the `metrics/<query>.json` path) outside the module that owns them.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"

# A function name that means one job, and the module and name that job has. Any other module defining the name fails here.
HOMED: dict[str, str] = {
    "_q": "quantity.parse",
    "_quantity": "quantity.parse",
    "_parse_mem": "quantity.parse (then divide by quantity.MIB)",
    "_size_mb": "quantity.parse (then divide by quantity.MIB)",
    "_r": "quantity.rounded",
    "_round": "quantity.rounded",
    "_num": "quantity.to_float",
    "_float": "quantity.to_float",
    "_int": "quantity.to_int",
    "_ver": "versions.image_version",
    "_minor": "versions.minor or versions.minor_text",
    "_minor_of": "versions.minor",
    "_major_minor": "versions.major_minor",
    "_metric_rows": "snapshot.metric_rows",
    "_rows": "snapshot.metric_result or snapshot.metric_rows",
    "_scalar": "snapshot.metric_scalar",
    "_metric_scalar": "snapshot.metric_scalar",
    "_metric_sum": "snapshot.metric_sum",
    "_v": "snapshot.metric_value",
    "_metric_doc": "snapshot.metric_doc",
    "_metric": "snapshot.metric_by",
    "_metric_map": "snapshot.metric_by",
    "_metric_by": "snapshot.metric_by",
    "_series_present": "snapshot.series_present",
    "count_of": "snapshot.event_count",
    "_count_of": "snapshot.event_count",
    "_wl": "workload.key or workload.workload_of",
    "_wl_key": "workload.key",
    "workload_of": "workload.workload_of",
    "is_db_like": "workload.is_db_like",
    "image_repo": "workload.image_repo",
    "mounts_pvc": "workload.mounts_pvc",
    "selector_matches": "workload.selector_matches",
    "eligible_nodes": "workload.eligible_nodes",
    "_normalize_msg": "logtext.normalize_message",
    "parse_sections": "nodetext.parse_sections",
    "_kv": "nodetext.key_values",
    "key_values": "nodetext.key_values",
    "parse_oom_kill": "nodetext.parse_oom_kill",
    "kernel_oom_kills": "nodetext.kernel_oom_kills",
    "_parse_prom_text": "promtext.parse",
    "_parse_prom": "promtext.parse",
    "_cell": "render.cell",
    "_table": "render.table",
    "_load_json": "snapshot.load_json",
    "_parse_ts": "snapshot.parse_ts",
    "_go_duration": "durations.go_duration_s",
}


def _modules() -> dict[str, ast.Module]:
    return {p.stem: ast.parse(p.read_text(encoding="utf-8"), str(p)) for p in sorted(LIB.rglob("*.py")) if p.name != "__init__.py"}


def _top_functions(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield node


def _shape(fn: ast.FunctionDef) -> str:
    """The function without its docstring, with its parameters renamed by position, so two copies with different names for the same thing compare equal."""
    fn = ast.parse(ast.unparse(fn)).body[0]
    names = {a.arg: f"p{i}" for i, a in enumerate(fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs)}
    if fn.args.vararg:
        names[fn.args.vararg.arg] = "pv"
    if fn.args.kwarg:
        names[fn.args.kwarg.arg] = "pk"
    for node in ast.walk(fn):
        if isinstance(node, ast.arg) and node.arg in names:
            node.arg = names[node.arg]
        elif isinstance(node, ast.Name) and node.id in names:
            node.id = names[node.id]
    if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) and isinstance(fn.body[0].value.value, str):
        fn.body = fn.body[1:]
    fn.name = "f"
    return ast.dump(fn, annotate_fields=False)


def test_no_two_modules_define_the_same_private_helper():
    """Two private top-level functions with the same name and the same body in different modules are one job written twice."""
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    for mod, tree in _modules().items():
        for fn in _top_functions(tree):
            if fn.name.startswith("_") and not fn.name.startswith("__"):
                seen[(fn.name, _shape(fn))].append(mod)
    twice = sorted(f"{name} in {', '.join(mods)}" for (name, _), mods in seen.items() if len(mods) > 1)
    assert twice == [], "the same private helper in two modules: give it one home (references/development.md, 'Before adding a helper')"


def test_a_job_with_a_home_is_not_defined_elsewhere():
    offenders = []
    for mod, tree in _modules().items():
        for node in _top_functions(tree):
            if node.name in HOMED and HOMED[node.name].split(".")[0] != mod:
                offenders.append(f"{mod}.{node.name}: use {HOMED[node.name]}")
    assert sorted(offenders) == []


def test_every_home_in_the_table_exists():
    mods = _modules()
    for name, home in HOMED.items():
        mod, _, fn = home.split(" ")[0].partition(".")
        assert mod in mods, (name, home)
        assert any(f.name == fn for f in _top_functions(mods[mod])), (name, home)


def _sources() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(LIB.rglob("*.py")) if p.name != "__init__.py"}


def test_the_metrics_file_path_is_spelled_by_the_reader_and_the_writer_only():
    """`metrics/<query id>.json` and `metrics/series-present.json` are read through lib/foundations/snapshot (metric_doc, metric_result, metric_rows, metric_by,
    metric_scalar, metric_sum, series_present) and written by lib/collection/prom (and by selftest, which builds a fake snapshot); no other module opens them,
    whether the query id is a variable or a literal name."""
    pat = re.compile(r'"metrics"\s*/\s*f?"[^"]*\.json"')
    offenders = [m for m, src in _sources().items() if m not in ("snapshot", "prom", "selftest") and pat.search(src)]
    assert offenders == []


def test_quantity_unit_tables_live_in_quantity_only():
    pat = re.compile(r'["\'](?:Ki|Mi|Gi|Ti)["\']\s*[,:]\s*(?:1024|1 / 1024|\d|MIB)')
    offenders = [m for m, src in _sources().items() if m != "quantity" and pat.search(src)]
    assert offenders == []


def test_image_tag_regular_expressions_live_in_versions_only():
    pat = re.compile(r":v\?\(\[0-9\]\+|:v\?\(\\d\+\\\.\\d\+|:v\?\(\\d\+\\\.\\d")
    offenders = [m for m, src in _sources().items() if m != "versions" and pat.search(src)]
    assert offenders == []


def test_the_node_os_text_path_is_spelled_by_snapshot_only():
    pat = re.compile(r'/\s*"os\.txt"')
    offenders = [m for m, src in _sources().items() if m != "snapshot" and pat.search(src)]
    assert offenders == []


def test_the_shape_reading_ignores_names_and_docstrings_but_not_bodies():
    a = ast.parse('def _r(x, n=3):\n    """doc"""\n    return None if x is None else round(x, n)\n').body[0]
    b = ast.parse("def _r(v, digits=3):\n    return None if v is None else round(v, digits)\n").body[0]
    c = ast.parse("def _r(v, digits=2):\n    return None if v is None else round(v, digits)\n").body[0]
    assert _shape(a) == _shape(b) and _shape(a) != _shape(c)

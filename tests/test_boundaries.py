"""The layers of lib/ and the direction an import may take (#149). The map below is the rule: every module has a layer, a module imports only its own layer
and the layers below it, and the one exception is `summarize`, the entry point of the summaries layer, which runs every section module by name.
An import against the rule fails here unless it is listed in EXCEPTIONS with the date and the issue that removes it; an exception whose import is gone fails
too, so the list cannot outlive the debt it records. The rule is written out in references/development.md."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"

FOUNDATIONS, COLLECTION, SUMMARIES, JUDGEMENT, OUTPUT, COMMANDS = ("foundations", "collection", "summaries", "judgement", "output", "commands")
ORDER = (FOUNDATIONS, COLLECTION, SUMMARIES, JUDGEMENT, OUTPUT, COMMANDS)  # bottom to top, the order the documentation lists them in

# What each layer may import. The layers hand their work on as files (the snapshot, summary.json, the check results), not as imports: judgement reads the
# summaries' output and output reads judgement's, so neither imports a module of the layer below it, only the foundations.
MAY_IMPORT: dict[str, frozenset[str]] = {
    FOUNDATIONS: frozenset({FOUNDATIONS}),
    COLLECTION: frozenset({FOUNDATIONS, COLLECTION}),
    SUMMARIES: frozenset({FOUNDATIONS}),  # a section module imports no sibling; summarize (ORCHESTRATORS) is the exception
    JUDGEMENT: frozenset({FOUNDATIONS}),
    OUTPUT: frozenset({FOUNDATIONS, OUTPUT}),
    COMMANDS: frozenset(ORDER),
}

# Every module under lib/ and its layer. Adding a module means placing it here; the test fails on a module without a row and on a row without a module.
LAYERS: dict[str, str] = {
    # foundations: standard-library helpers and data-file loaders; they know neither the cluster nor the checks
    "__init__": FOUNDATIONS,
    "amconfig": FOUNDATIONS,
    "components": FOUNDATIONS,
    "config": FOUNDATIONS,
    "durations": FOUNDATIONS,
    "http": FOUNDATIONS,
    "lastapplied": FOUNDATIONS,
    "mask": FOUNDATIONS,
    "metricnames": FOUNDATIONS,
    "paths": FOUNDATIONS,
    "podmetrics": FOUNDATIONS,
    "promtext": FOUNDATIONS,
    "rubric": FOUNDATIONS,
    "runlog": FOUNDATIONS,
    "scrub": FOUNDATIONS,
    "shell": FOUNDATIONS,
    "signatures": FOUNDATIONS,
    "snapshot": FOUNDATIONS,
    "versions": FOUNDATIONS,
    "yamlite": FOUNDATIONS,
    # collection: touches the cluster, AWS, the nodes or Prometheus and writes the snapshot files
    "albmetrics": COLLECTION,
    "aws": COLLECTION,
    "collect": COLLECTION,
    "cwlogs": COLLECTION,
    "cwmetrics": COLLECTION,
    "discover": COLLECTION,
    "kube": COLLECTION,
    "logsinks": COLLECTION,
    "monitoring": COLLECTION,
    "node": COLLECTION,
    "nodecommands": COLLECTION,
    "portfwd": COLLECTION,
    "prom": COLLECTION,
    # summaries: read snapshot files, write the sections of summary.json; summarize is the entry point that runs them
    "albctl": SUMMARIES,
    "argocdctl": SUMMARIES,
    "certmanager": SUMMARIES,
    "controlplane": SUMMARIES,
    "coredns": SUMMARIES,
    "cost": SUMMARIES,
    "ebscsi": SUMMARIES,
    "ecr": SUMMARIES,
    "eksplatform": SUMMARIES,
    "esoctl": SUMMARIES,
    "events": SUMMARIES,
    "flannelctl": SUMMARIES,
    "hygiene": SUMMARIES,
    "k3s": SUMMARIES,
    "karpenterctl": SUMMARIES,
    "kedactl": SUMMARIES,
    "kubeproxy": SUMMARIES,
    "localpath": SUMMARIES,
    "logs": SUMMARIES,
    "metallbctl": SUMMARIES,
    "nodeos": SUMMARIES,
    "observability": SUMMARIES,
    "resilience": SUMMARIES,
    "resources": SUMMARIES,
    "scaling": SUMMARIES,
    "security": SUMMARIES,
    "stackhealth": SUMMARIES,
    "storage": SUMMARIES,
    "summarize": SUMMARIES,
    "tenancy": SUMMARIES,
    "traffic": SUMMARIES,
    "vpccni": SUMMARIES,
    # judgement: evaluates the checks against summary.json and the metric files (the summaries are read as files, never imported)
    "evaluate": JUDGEMENT,
    # output: the judgement result in a form a person reads
    "diff": OUTPUT,
    "render": OUTPUT,
    "verified": OUTPUT,
    "writer": OUTPUT,
    # commands: the bodies of `scripts/kubegap` sub-commands; they may import any layer
    "configedit": COMMANDS,
    "firstrun": COMMANDS,
    "prune": COMMANDS,
    "regress": COMMANDS,
    "selftest": COMMANDS,
    "setup": COMMANDS,
    "tools": COMMANDS,
}

# The one module allowed to import its siblings: summarize runs every section module (by name, through importlib) and reads two key lists from them.
ORCHESTRATORS = {"summarize"}

# Imports against the rule that are known, dated and owned by the issue that removes them. Key: (importing module, imported module).
# Shared helpers that a summary module lends to the others have no home below the summaries layer yet; #150 gives each one a home and deletes its row.
# A summary that computes part of another section itself gets that section's result from summarize instead; #151 does that and deletes its row.
EXCEPTIONS: dict[tuple[str, str], str] = {
    ("evaluate", "resilience"): "2026-11-07 is_db_like, mounts_pvc have no home below the summaries → #150",
    ("metallbctl", "resilience"): "2026-11-07 eligible_nodes, selector_matches have no home below the summaries → #150",
    ("tenancy", "resilience"): "2026-11-07 _q (resource quantity) has no home below the summaries → #150",
    ("hygiene", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("k3s", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("logs", "controlplane"): "2026-11-07 workload_of, _normalize_msg have no home below the summaries → #150",
    ("nodeos", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("resilience", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("resources", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("traffic", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("vpccni", "controlplane"): "2026-11-07 workload_of has no home below the summaries → #150",
    ("ebscsi", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("resilience", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("scaling", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("storage", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("traffic", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("vpccni", "events"): "2026-11-07 count_of has no home below the summaries → #150",
    ("resilience", "nodeos"): "2026-11-07 kernel_oom_kills has no home below the summaries → #150",
    ("k3s", "nodeos"): "2026-11-07 parse_sections, _kv, _int, _num have no home below the summaries → #150",
    ("security", "hygiene"): "2026-11-07 security runs hygiene's polaris reader itself; summarize passes the hygiene section instead → #151",
    ("traffic", "security"): "2026-11-07 traffic asks security whether NetworkPolicy is enforced; summarize passes the security section instead → #151",
    ("observability", "traffic"): "2026-11-07 observability asks traffic which Services ALB covers; summarize passes the traffic section instead → #151",
}


def lib_imports(source: str, modules: set[str]) -> set[str]:
    """The lib modules `source` imports, at any depth (an import inside a function is the same dependency, only later), in every form the code uses:
    `from . import a, b`, `from .a import b`, `from lib.a import b`, `import lib.a`, plus summarize's two dynamic forms, `_component("a", ...)` and the
    module column of COMPONENT_SECTIONS."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.level == 1 and node.module is None:
                out |= {a.name for a in node.names if a.name in modules}
            elif node.level == 1 and node.module:
                out.add(node.module.split(".")[0])
            elif node.level == 0 and node.module and node.module.split(".")[0] == "lib":
                parts = node.module.split(".")
                out |= {parts[1]} if len(parts) > 1 else {a.name for a in node.names if a.name in modules}
        elif isinstance(node, ast.Import):
            out |= {a.name.split(".")[1] for a in node.names if a.name.startswith("lib.")}
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_component" and node.args and isinstance(node.args[0], ast.Constant):
            out.add(str(node.args[0].value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "COMPONENT_SECTIONS" and node.value is not None:
            out |= {row[1] for row in ast.literal_eval(node.value)}
    return out


def _modules() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(LIB.glob("*.py"))}


def _edges() -> set[tuple[str, str]]:
    mods = _modules()
    names = set(mods)
    return {(m, d) for m, src in mods.items() for d in lib_imports(src, names) if d != m}


def _allowed(importer: str, imported: str) -> bool:
    a, b = LAYERS[importer], LAYERS[imported]
    return b in MAY_IMPORT[a] or (importer in ORCHESTRATORS and a == b)


def test_every_module_has_a_layer_and_every_row_a_module():
    mods = set(_modules())
    assert mods - set(LAYERS) == set(), "a new module under lib/ is placed in LAYERS first"
    assert set(LAYERS) - mods == set(), "a row for a module that is gone"
    assert set(LAYERS.values()) <= set(ORDER) and set(MAY_IMPORT) == set(ORDER)


def test_summaries_do_not_import_each_other_and_no_layer_imports_upward():
    edges = _edges()
    against = sorted(e for e in edges if not _allowed(*e))
    unlisted = [f"{a} ({LAYERS[a]}) imports {b} ({LAYERS[b]})" for a, b in against if (a, b) not in EXCEPTIONS]
    assert unlisted == [], "an import against the layer rule (references/development.md); place the helper in a lower layer or add a dated EXCEPTIONS row with the issue that removes it"


def test_every_exception_is_still_an_import_against_the_rule():
    """A row whose import was fixed is deleted with the fix; a row that names an allowed import is a mistake."""
    edges = _edges()
    gone = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if (a, b) not in edges]
    assert gone == [], "exception rows for imports that no longer exist"
    allowed = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if _allowed(a, b)]
    assert allowed == [], "exception rows for imports the rule allows"
    assert all(" → #" in why and why[:10].count("-") == 2 for why in EXCEPTIONS.values()), "every exception carries its date and the issue that removes it"


def test_the_two_feared_imports_do_not_exist():
    """The issue's examples: a summary module importing the renderer, a collector importing the evaluator (#149)."""
    edges = _edges()
    assert not [e for e in edges if LAYERS[e[0]] == SUMMARIES and e[1] in ("render", "evaluate")]
    assert not [e for e in edges if LAYERS[e[0]] == COLLECTION and e[1] == "evaluate"]


def test_foundations_import_only_foundations():
    """The bottom layer never reaches up, with or without an exception: a helper that needs the cluster is not a foundation."""
    edges = _edges()
    assert sorted(e for e in edges if LAYERS[e[0]] == FOUNDATIONS and LAYERS[e[1]] != FOUNDATIONS) == []


def test_every_summaries_module_is_run_by_summarize():
    """summarize runs every section module by name and imports the two readers that write into a section (events, logs); a summaries module it never
    reaches is dead code, or a helper that belongs below the summaries (#150). The other direction, no sibling imports, is the layer-rule test above."""
    mods = _modules()
    run_by_summarize = lib_imports(mods["summarize"], set(mods))
    sections = {m for m, layer in LAYERS.items() if layer == SUMMARIES} - ORCHESTRATORS
    assert sorted(sections - run_by_summarize) == [], "a summaries module summarize does not run: a section it should run, or a helper that belongs in a lower layer"


def test_the_scanner_sees_every_import_form():
    src = (
        "from . import a, b\n"
        "from .c import x\n"
        "from lib.d import y\n"
        "import lib.e\n"
        "def f():\n"
        "    from .g import z\n"
        "    return _component('h', 1)\n"
        'COMPONENT_SECTIONS: tuple = (("k", "i", ("x",), None),)\n'
        "import os\n"
        "from pathlib import Path\n"
    )
    assert lib_imports(src, {"a", "b", "c", "d", "e", "g", "h", "i"}) == {"a", "b", "c", "d", "e", "g", "h", "i"}


def test_the_layer_rule_reads_as_documented():
    """references/development.md names the six layers in order and says which module is the exception."""
    doc = (ROOT / "references" / "development.md").read_text(encoding="utf-8")
    positions = [doc.find(f"**{name}**") for name in ORDER]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), "the six layers, bottom to top, each in bold once"
    assert "tests/test_boundaries.py" in doc and "summarize" in doc

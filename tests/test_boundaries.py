"""The layers of lib/ are its packages, and an import may only go down (#149, #151). `lib/foundations`, `lib/collection`, `lib/summaries`, `lib/judgement`,
`lib/output` and `lib/commands` are the six layers; a module imports its own package and the packages below it as MAY_IMPORT says, and a layer hands
its work on as files, so judgement and output import the foundations only. Inside `lib/summaries` no section module imports a sibling: `summarize`,
the entry point that runs every section by name, is the one exception. An import against the rule fails here unless it is listed in EXCEPTIONS with
the date and the issue that removes it; an exception whose import is gone fails too, so the list cannot outlive the debt it records. The rule is
written out in references/development.md."""

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

# The one module allowed to import its siblings: summarize runs every section module (by name, through importlib) and reads two key lists from them.
ORCHESTRATORS = {"summarize"}

# Imports against the rule that are known, dated and owned by the issue that removes them. Key: (importing module, imported module).
# Empty since #151: the three summaries that computed part of another section get it from summarize as an argument.
EXCEPTIONS: dict[tuple[str, str], str] = {}


def layers() -> dict[str, str]:
    """module name -> its layer, read from the folder it lives in."""
    return {p.stem: p.parent.name for layer in ORDER for p in sorted((LIB / layer).glob("*.py")) if p.name != "__init__.py"}


def lib_imports(source: str, modules: dict[str, str]) -> set[str]:
    """The lib modules `source` imports, at any depth (an import inside a function is the same dependency, only later), in every form the code uses:
    `from . import a, b` and `from .a import b` (own package), `from ..layer import a` and `from ..layer.a import b` (another package), `from lib.layer.a import b`,
    `import lib.layer.a`, plus summarize's two dynamic forms, `_component("a", ...)` and the module column of COMPONENT_SECTIONS."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            parts = (node.module or "").split(".") if node.module else []
            if node.level == 1 and not parts:
                out |= {a.name for a in node.names if a.name in modules}
            elif node.level == 1 and parts:
                out.add(parts[0])
            elif node.level == 2 and len(parts) == 1 and parts[0] in ORDER:
                out |= {a.name for a in node.names if a.name in modules}
            elif node.level == 2 and len(parts) >= 2 and parts[0] in ORDER:
                out.add(parts[1])
            elif node.level == 0 and parts[:1] == ["lib"]:
                if len(parts) >= 3:
                    out.add(parts[2])
                elif len(parts) == 2 and parts[1] in ORDER:
                    out |= {a.name for a in node.names if a.name in modules}
        elif isinstance(node, ast.Import):
            out |= {a.name.split(".")[2] for a in node.names if a.name.startswith("lib.") and a.name.count(".") >= 2}
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_component" and node.args and isinstance(node.args[0], ast.Constant):
            out.add(str(node.args[0].value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "COMPONENT_SECTIONS" and node.value is not None:
            out |= {row[1] for row in ast.literal_eval(node.value)}
    return out


def _sources() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for layer in ORDER for p in sorted((LIB / layer).glob("*.py")) if p.name != "__init__.py"}


def _edges() -> set[tuple[str, str]]:
    mods, srcs = layers(), _sources()
    return {(m, d) for m, src in srcs.items() for d in lib_imports(src, mods) if d != m}


def _allowed(importer: str, imported: str, mods: dict[str, str]) -> bool:
    a, b = mods[importer], mods[imported]
    return b in MAY_IMPORT[a] or (importer in ORCHESTRATORS and a == b)


def test_lib_is_exactly_the_six_layer_packages():
    assert sorted(p.name for p in LIB.iterdir() if p.is_dir() and p.name != "__pycache__") == sorted(ORDER)
    assert sorted(p.name for p in LIB.glob("*.py")) == ["__init__.py"], "a module at the top of lib/ belongs in a layer package"
    names = [p.stem for layer in ORDER for p in (LIB / layer).glob("*.py") if p.name != "__init__.py"]
    assert len(names) == len(set(names)), "a module name is used in two layers"
    assert set(MAY_IMPORT) == set(ORDER)


def test_summaries_do_not_import_each_other_and_no_layer_imports_upward():
    mods = layers()
    against = sorted(e for e in _edges() if not _allowed(*e, mods))
    unlisted = [f"{a} ({mods[a]}) imports {b} ({mods[b]})" for a, b in against if (a, b) not in EXCEPTIONS]
    assert unlisted == [], "an import against the layer rule (references/development.md); place the helper in a lower layer or add a dated EXCEPTIONS row with the issue that removes it"


def test_every_exception_is_still_an_import_against_the_rule():
    """A row whose import was fixed is deleted with the fix; a row that names an allowed import is a mistake."""
    mods, edges = layers(), _edges()
    gone = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if (a, b) not in edges]
    assert gone == [], "exception rows for imports that no longer exist"
    allowed = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if _allowed(a, b, mods)]
    assert allowed == [], "exception rows for imports the rule allows"
    assert all(" → #" in why and why[:10].count("-") == 2 for why in EXCEPTIONS.values()), "every exception carries its date and the issue that removes it"


def test_the_two_feared_imports_do_not_exist():
    """The issue's examples: a summary module importing the renderer, a collector importing the evaluator (#149)."""
    mods, edges = layers(), _edges()
    assert not [e for e in edges if mods[e[0]] == SUMMARIES and e[1] in ("render", "evaluate")]
    assert not [e for e in edges if mods[e[0]] == COLLECTION and e[1] == "evaluate"]


def test_foundations_import_only_foundations():
    """The bottom layer never reaches up, with or without an exception: a helper that needs the cluster is not a foundation."""
    mods = layers()
    assert sorted(e for e in _edges() if mods[e[0]] == FOUNDATIONS and mods[e[1]] != FOUNDATIONS) == []


def test_every_summaries_module_is_run_by_summarize():
    """summarize runs every section module by name and imports the two readers that write into a section (events, logs); a summaries module it never
    reaches is dead code, or a helper that belongs below the summaries (#150). The other direction, no sibling imports, is the layer-rule test above."""
    mods, srcs = layers(), _sources()
    run_by_summarize = lib_imports(srcs["summarize"], mods)
    sections = {m for m, layer in mods.items() if layer == SUMMARIES} - ORCHESTRATORS
    assert sorted(sections - run_by_summarize) == [], "a summaries module summarize does not run: a section it should run, or a helper that belongs in a lower layer"


def test_the_scanner_sees_every_import_form():
    mods = {"a": SUMMARIES, "b": SUMMARIES, "c": SUMMARIES, "d": FOUNDATIONS, "e": FOUNDATIONS, "f": COLLECTION, "g": FOUNDATIONS, "h": SUMMARIES, "i": SUMMARIES, "j": OUTPUT}
    src = (
        "from . import a, b\n"
        "from .c import x\n"
        "from ..foundations import d\n"
        "from ..foundations.e import y\n"
        "from lib.collection.f import z\n"
        "import lib.foundations.g\n"
        "def f():\n"
        "    from ..output import j\n"
        "    return _component('h', 1)\n"
        'COMPONENT_SECTIONS: tuple = (("k", "i", ("x",), None),)\n'
        "import os\n"
        "from pathlib import Path\n"
    )
    assert lib_imports(src, mods) == {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"}


def test_the_layer_rule_reads_as_documented():
    """references/development.md names the six layers in order and says which module is the exception."""
    doc = (ROOT / "references" / "development.md").read_text(encoding="utf-8")
    positions = [doc.find(f"**{name}**") for name in ORDER]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), "the six layers, bottom to top, each in bold once"
    assert "tests/test_boundaries.py" in doc and "summarize" in doc

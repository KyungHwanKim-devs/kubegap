"""The layers of lib/ are its packages, and an import may only go down (#149, #151). `lib/foundations`, `lib/collection`, `lib/summaries`, `lib/judgement`,
`lib/output` and `lib/commands` are the six layers; a module imports its own layer and the layers below it as MAY_IMPORT says, and a layer hands its
work on as files, so judgement and output import the foundations only. Inside `lib/summaries` no section module imports a sibling: `summarize`, the
entry point that runs every section by name, is the one exception. A large module is a sub-package (`lib/summaries/resilience/`): its `__init__` is
the module, its other files are its parts, a part may import another part of the same sub-package but never in a cycle and never the `__init__`,
and parts count as their module for the layer rule. An import against the rule fails here unless it is listed in EXCEPTIONS with the date and the
issue that removes it; an exception whose import is gone fails too. The rule is written out in references/development.md."""

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


def files() -> dict[str, Path]:
    """Every module file under lib/ by its dotted name below the layer: `snapshot`, `resilience` (a sub-package's __init__), `resilience.capacity` (a part)."""
    out: dict[str, Path] = {}
    for layer in ORDER:
        for p in sorted((LIB / layer).rglob("*.py")):
            rel = p.relative_to(LIB / layer).with_suffix("")
            parts = list(rel.parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                out[".".join(parts)] = p
    return out


def layers() -> dict[str, str]:
    """dotted name -> its layer, read from the folder it lives in."""
    return {name: p.relative_to(LIB).parts[0] for name, p in files().items()}


def sub_packages() -> set[str]:
    """The modules that are folders: their __init__ sits in the sub-package folder, like a part."""
    return {name for name, p in files().items() if p.name == "__init__.py"}


def module_of(name: str) -> str:
    """The module a dotted name belongs to for the layer rule: a part of a sub-package counts as the sub-package."""
    return name.split(".")[0]


def lib_imports(source: str, importer: str, modules: dict[str, str], subpkgs: set[str] = frozenset()) -> set[str]:
    """The dotted names `source` imports, at any depth (an import inside a function is the same dependency, only later), resolved from the importer's place:
    in a layer module `from . import a` / `from .a import b` name a layer sibling and `from ..layer import a` / `from ..layer.a import b` another layer;
    in a sub-package part one more dot is needed for each. Absolute `from lib.layer.a import b` and `import lib.layer.a` are read too, plus summarize's two
    dynamic forms, `_component("a", ...)` and the module column of COMPONENT_SECTIONS."""
    depth = 1 if ("." in importer or importer in subpkgs) else 0  # the file sits in a sub-package folder (a part or the __init__) or in the layer folder
    own_pkg = importer.split(".")[0]
    out: set[str] = set()

    def resolve(level: int, module: str | None, names: list[str]) -> None:
        parts = module.split(".") if module else []
        # climb: level 1 = the folder the file is in, 2 = its parent, ...
        folder_depth = depth + 1 - level  # 1 = the sub-package folder, 0 = the layer folder, -1 = lib/
        if folder_depth == 1:  # inside the sub-package: parts of the same module
            out.update({f"{own_pkg}.{parts[0]}"} if parts else {f"{own_pkg}.{n}" for n in names})
        elif folder_depth == 0:  # the layer folder
            out.update({parts[0]} if parts else {n for n in names if n in modules})
        elif folder_depth == -1 and parts and parts[0] in ORDER:  # lib/: another layer
            if len(parts) >= 2:
                out.add(parts[1])
            else:
                out.update(n for n in names if n in modules)

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                resolve(node.level, node.module, [a.name for a in node.names])
            elif node.module and node.module.split(".")[:1] == ["lib"]:
                parts = node.module.split(".")
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


def _edges() -> set[tuple[str, str]]:
    mods, subs = layers(), sub_packages()
    srcs = {name: p.read_text(encoding="utf-8") for name, p in files().items()}
    return {(m, d) for m, src in srcs.items() for d in lib_imports(src, m, mods, subs) if d != m}


def _allowed(importer: str, imported: str, mods: dict[str, str]) -> bool:
    a, b = module_of(importer), module_of(imported)
    if a == b:  # inside one sub-package: a part may import a part (acyclicity is its own test); nothing imports the __init__
        return "." in imported
    la, lb = mods[a], mods[b]
    return lb in MAY_IMPORT[la] or (a in ORCHESTRATORS and la == lb)


def test_lib_is_exactly_the_six_layer_packages():
    assert sorted(p.name for p in LIB.iterdir() if p.is_dir() and p.name != "__pycache__") == sorted(ORDER)
    assert sorted(p.name for p in LIB.glob("*.py")) == ["__init__.py"], "a module at the top of lib/ belongs in a layer package"
    names = [n for n in files() if "." not in n]
    assert len(names) == len(set(names)), "a module name is used in two layers"
    assert set(MAY_IMPORT) == set(ORDER)


def test_a_sub_package_is_one_module_with_parts():
    """A folder inside a layer is a module split into parts: it has an __init__.py, every part is a direct child (no deeper nesting), and the parts
    never import the __init__ (the __init__ assembles them)."""
    for layer in ORDER:
        for d in (LIB / layer).iterdir():
            if d.is_dir() and d.name != "__pycache__":
                assert (d / "__init__.py").is_file(), d
                assert not [x for x in d.iterdir() if x.is_dir() and x.name != "__pycache__"], f"{d}: a part of a part"
    bad = sorted(f"{a} imports {b}" for a, b in _edges() if "." in a and "." not in b and module_of(a) == b)
    assert bad == [], "a part imports its own sub-package's __init__"


def test_parts_of_a_sub_package_do_not_import_in_a_cycle():
    edges = {(a, b) for a, b in _edges() if "." in a and "." in b and module_of(a) == module_of(b)}
    graph: dict[str, set[str]] = {}
    for a, b in edges:
        graph.setdefault(a, set()).add(b)
    seen: dict[str, int] = {}

    def visit(n: str, stack: list[str]) -> None:
        if seen.get(n) == 1:
            raise AssertionError(f"cycle among parts: {' -> '.join([*stack, n])}")
        if seen.get(n) == 2:
            return
        seen[n] = 1
        for m in graph.get(n, ()):
            visit(m, [*stack, n])
        seen[n] = 2

    for n in graph:
        visit(n, [])


def test_summaries_do_not_import_each_other_and_no_layer_imports_upward():
    mods = layers()
    against = sorted(e for e in _edges() if not _allowed(*e, mods))
    unlisted = [f"{a} ({mods[module_of(a)]}) imports {b} ({mods[module_of(b)]})" for a, b in against if (module_of(a), module_of(b)) not in EXCEPTIONS]
    assert unlisted == [], "an import against the layer rule (references/development.md); place the helper in a lower layer or add a dated EXCEPTIONS row with the issue that removes it"


def test_every_exception_is_still_an_import_against_the_rule():
    """A row whose import was fixed is deleted with the fix; a row that names an allowed import is a mistake."""
    mods, edges = layers(), {(module_of(a), module_of(b)) for a, b in _edges()}
    gone = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if (a, b) not in edges]
    assert gone == [], "exception rows for imports that no longer exist"
    allowed = [f"{a} -> {b}" for (a, b) in EXCEPTIONS if _allowed(a, b, mods)]
    assert allowed == [], "exception rows for imports the rule allows"
    assert all(" → #" in why and why[:10].count("-") == 2 for why in EXCEPTIONS.values()), "every exception carries its date and the issue that removes it"


def test_the_two_feared_imports_do_not_exist():
    """The issue's examples: a summary module importing the renderer, a collector importing the evaluator (#149)."""
    mods, edges = layers(), _edges()
    assert not [e for e in edges if mods[module_of(e[0])] == SUMMARIES and module_of(e[1]) in ("render", "evaluate")]
    assert not [e for e in edges if mods[module_of(e[0])] == COLLECTION and module_of(e[1]) == "evaluate"]


def test_foundations_import_only_foundations():
    """The bottom layer never reaches up, with or without an exception: a helper that needs the cluster is not a foundation."""
    mods = layers()
    assert sorted(e for e in _edges() if mods[module_of(e[0])] == FOUNDATIONS and mods[module_of(e[1])] != FOUNDATIONS) == []


def test_every_summaries_module_is_run_by_summarize():
    """summarize runs every section module by name and imports the two readers that write into a section (events, logs); a summaries module it never
    reaches is dead code, or a helper that belongs below the summaries (#150). The other direction, no sibling imports, is the layer-rule test above."""
    mods = layers()
    run_by_summarize = lib_imports(files()["summarize"].read_text(encoding="utf-8"), "summarize", mods)
    sections = {m for m, layer in mods.items() if layer == SUMMARIES and "." not in m} - ORCHESTRATORS
    assert sorted(sections - run_by_summarize) == [], "a summaries module summarize does not run: a section it should run, or a helper that belongs in a lower layer"


def test_the_scanner_sees_every_import_form():
    mods = {"a": SUMMARIES, "b": SUMMARIES, "c": SUMMARIES, "d": FOUNDATIONS, "e": FOUNDATIONS, "f": COLLECTION, "g": FOUNDATIONS, "h": SUMMARIES, "i": SUMMARIES, "j": OUTPUT, "r": SUMMARIES, "events": SUMMARIES}
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
    assert lib_imports(src, "r", mods) == {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"}
    part = "from .capacity import n_plus_one\nfrom ...foundations.snapshot import objects\nfrom .. import events\n"
    assert lib_imports(part, "r.oom", mods) == {"r.capacity", "snapshot", "events"}
    init = "from .capacity import n_plus_one\nfrom ...foundations.snapshot import objects\nfrom .. import events\n"
    assert lib_imports(init, "r", mods, {"r"}) == {"r.capacity", "snapshot", "events"}, "a sub-package __init__ sits in the sub-package folder like a part"


def test_the_layer_rule_reads_as_documented():
    """references/development.md names the six layers in order and says which module is the exception."""
    doc = (ROOT / "references" / "development.md").read_text(encoding="utf-8")
    positions = [doc.find(f"**{name}**") for name in ORDER]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), "the six layers, bottom to top, each in bold once"
    assert "tests/test_boundaries.py" in doc and "summarize" in doc

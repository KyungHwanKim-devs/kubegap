"""Collection units (collectors/units.yaml): a mode is a list of units, the daily run collects nothing but units of low sensitivity, and
every step and every check speaks of units, never of modes."""

from __future__ import annotations

from lib.foundations import paths, rubric, units


def test_the_declarations_and_the_steps_that_name_them_are_valid():
    assert units.validate() == []


def test_the_daily_run_collects_units_of_low_sensitivity_only():
    daily = [units.get(u) for u in units.of_mode("daily")]
    assert daily and all(u["sensitivity"] == "low" for u in daily)
    assert units.of_mode("daily") < units.of_mode("full") == frozenset(units.ids())  # the full run collects every unit


def test_a_unit_the_daily_run_leaves_out_says_what_cannot_be_learned_without_it():
    for u in units.left_out("daily"):
        assert set(u["unseen"]) == {"en", "ko"}, u["id"]


def test_a_sensitive_unit_in_the_daily_run_is_refused(monkeypatch):
    bad = [{**u, "modes": ["daily", "full"]} if u["id"] == "node-os" else u for u in units.units()]
    monkeypatch.setattr(units, "_load", lambda: tuple(bad))
    assert any("node-os is collected by the daily run" in e for e in units.validate())


def test_every_need_of_a_check_is_a_unit_and_a_misspelt_unit_is_an_error():
    checks, errors = rubric.load_checks(sorted(p.name for p in paths.COLLECTORS_DIR.iterdir() if p.is_dir()))
    assert not errors
    assert {n for c in checks for n in c.get("needs") or []} <= set(units.ids())
    try:
        units.collected("daily", "node-oss")
    except KeyError as e:
        assert "node-oss" in str(e)
    else:
        raise AssertionError("a misspelt unit must not read as not collected")


def test_the_data_documents_carry_the_table_the_declarations_print():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    begin, end = "<!-- units-table:begin -->\n", "<!-- units-table:end -->\n"
    for language, doc in (("en", "docs/DATA.md"), ("ko", "docs/ko/DATA.md")):
        text = (root / doc).read_text(encoding="utf-8")
        assert begin in text and end in text, f"{doc} lost the units-table markers"
        assert text.split(begin, 1)[1].split(end, 1)[0] == units.render_table(language), f"regenerate: scripts/kubegap units --markdown --language {language}, pasted between the markers of {doc}"

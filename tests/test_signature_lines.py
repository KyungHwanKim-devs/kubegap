"""Every signature pattern against lines built from the logging calls it cites (#129): the cases live in tests/signature_lines.py, one list per component
group, each line with the citation of its format string. A positive line must match exactly the signatures named; a normal line must match none."""

from __future__ import annotations

import pytest

from lib.foundations import paths, signatures
from lib.summaries import logs
from tests import signature_lines as data

SIGS, ERRORS = signatures.load(sorted(p.parent.name for p in paths.COLLECTORS_DIR.glob("*/signatures.yaml")))
BY_ID = {s.id: s for s in SIGS}


def test_the_catalog_loads_without_errors():
    assert not ERRORS
    logs.any_regex(SIGS)  # the scanner's combined pre-filter must compile too: a `(?i)` pattern joined mid-expression is a PatternError (seen with loki.rate-limited)
    assert any(s.pattern.startswith("(?i)") for s in SIGS)


def test_every_case_names_known_signatures_and_every_signature_has_a_positive_case():
    named = {sid for _, expected, _ in data.CASES for sid in expected}
    assert not named - set(BY_ID), sorted(named - set(BY_ID))
    without = sorted(set(BY_ID) - named)
    assert not without, f"signatures with no positive test line: {without}"


@pytest.mark.parametrize(("line", "expected", "rel"), data.CASES, ids=[f"{i}:{'+'.join(sorted(e)) or 'none'}" for i, (_, e, _) in enumerate(data.CASES)])
def test_each_line_matches_exactly_the_signatures_it_should(line, expected, rel):
    applicable = [s for s in SIGS if s.applies_to(rel)]
    hit = logs.match_line(line, applicable)  # the scanner's own rule (common.* yields to a component signature on the same line)
    assert hit == expected, f"{rel}: {line[:160]!r}"
    for sid in expected:  # the expected signature must also scan that file: a pattern that matches but a glob that does not is still silent
        assert sid in {s.id for s in applicable}, f"{sid} does not scan {rel} (sources {BY_ID[sid].sources})"

"""rubric/learn/: what a report teaches about a group of checks. The files are data written by people who opened every page they cite; these tests
keep their shape, their link to the checks, and the promise that a check a problem can be headed by has something to teach."""

from __future__ import annotations

from lib.foundations import rubric

GOOD = {
    "topic": "t",
    "checks": ["resilience.no-backup"],
    "mechanism": "word " * 60,
    "sources": [{"title": "s", "url": "https://example.com/a"}],
    "detect": [{"kind": "alert", "what": "w"}, {"kind": "command", "what": "c"}],
    "solutions": [{"scale": ["small"], "approach": "a", "tradeoff": "t"}, {"scale": ["medium", "large"], "approach": "b", "tradeoff": "t"}],
    "cases": [],
    "reading": [{"title": "r", "url": "https://example.com/r", "why": "w"}, {"title": "r2", "url": "https://example.com/r2", "why": "w"}],
}
IDS = {"resilience.no-backup"}


def _errors(**over):
    return rubric.validate_learn({**GOOD, **over}, "rubric/learn/t.yaml", IDS)


def test_the_committed_topics_load_and_each_check_has_one_topic():
    topics, errs = rubric.load_learn()
    assert errs == [] and topics
    owners = [c for t in topics for c in t["checks"]]
    assert len(owners) == len(set(owners))


def test_every_check_that_can_head_a_problem_has_a_topic():
    """A problem is headed by a critical or high check (at any scale); the report explains it at length, so the material must exist."""
    covered = {c for t in rubric.load_learn()[0] for c in t["checks"]}

    def serious(c):
        s = c["severity_default"]
        return any(v in ("critical", "high") for v in (s.values() if isinstance(s, dict) else [s]))

    assert sorted(c["id"] for c in rubric.catalog() if serious(c) and c["id"] not in covered) == []


def test_a_topic_says_how_it_works_how_to_watch_it_and_how_to_solve_it_at_every_scale():
    assert _errors() == []
    assert any("topic must equal the file name" in e for e in _errors(topic="other"))
    assert any("does not exist" in e for e in _errors(checks=["no.such-check"]))
    assert any("mechanism" in e for e in _errors(mechanism="short"))
    assert any("sources" in e for e in _errors(sources=[{"title": "s", "url": "example.com"}]))
    assert any("commands only" in e for e in _errors(detect=[{"kind": "command", "what": "kubectl"}]))
    assert any("leave a scale without an answer: ['large']" in e for e in _errors(solutions=[{"scale": ["small", "medium"], "approach": "a", "tradeoff": "t"}]))
    assert any("a solution needs" in e for e in _errors(solutions=[{"scale": ["small", "medium", "large"], "approach": "a"}]))
    assert any("a case needs" in e for e in _errors(cases=[{"company": "c", "url": "https://example.com/c"}]))
    assert any("reading" in e for e in _errors(reading=GOOD["reading"][:1]))


def test_the_topics_of_a_set_of_checks_are_found_by_check_id():
    topics = rubric.learn_for({"resilience.no-backup", "no.such-check"})
    assert [t["topic"] for t in topics] == ["backup-off-cluster"]
    assert rubric.learn_for({"no.such-check"}) == []

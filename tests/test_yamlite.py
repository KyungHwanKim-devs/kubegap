"""lib/yamlite.py: the hand-written YAML subset parser. Each test is one feature of the supported subset, one fixed bug, or one rejected construct."""

import textwrap

import pytest

from lib import yamlite
from lib.yamlite import YamlError, load


def y(text: str):
    return load(textwrap.dedent(text).lstrip("\n"))


# ---------- scalars ----------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a: 1", 1),
        ("a: -7", -7),
        ("a: 1_000", 1000),
        ("a: 1.5", 1.5),
        ("a: .5", 0.5),
        ("a: 1e3", 1000.0),
        ("a: true", True),
        ("a: False", False),
        ("a: null", None),
        ("a: ~", None),
        ("a:", None),
        ("a: hello world", "hello world"),
        ("a: 0.1.44", "0.1.44"),
        ("a: http://example.com:8080/x", "http://example.com:8080/x"),
        ("a: 'single'", "single"),
        ('a: "double"', "double"),
        ("a: 'it''s'", "it's"),
        ('a: "line\\nbreak\\t\\"q\\""', 'line\nbreak\t"q"'),
        ("a: '123'", "123"),
    ],
)
def test_scalars(text, expected):
    assert load(text) == {"a": expected}


def test_empty_document_is_none():
    assert load("") is None
    assert load("# only a comment\n") is None


# ---------- mappings and sequences ----------


def test_nested_mapping():
    assert y("""
        rule:
          expr: x > 1
          threshold:
            prod: 5
            lab: 2
        """) == {"rule": {"expr": "x > 1", "threshold": {"prod": 5, "lab": 2}}}


def test_sequence_of_scalars_and_sequence_of_mappings():
    assert y("""
        - a
        - 2
        - id: x
          name: X
        - id: y
        """) == ["a", 2, {"id": "x", "name": "X"}, {"id": "y"}]


def test_sequence_at_same_indent_as_key():
    assert y("""
        disabled_checks:
        - a.b
        - c.d
        other: 1
        """) == {"disabled_checks": ["a.b", "c.d"], "other": 1}


def test_nested_sequence_with_double_dash():
    assert y("""
        - - 1
          - 2
        - - 3
        """) == [[1, 2], [3]]


def test_empty_sequence_item_followed_by_nested_block():
    assert y("""
        items:
          -
            k: v
          - plain
        """) == {"items": [{"k": "v"}, "plain"]}


def test_quoted_key_and_duplicate_key():
    assert load("'a b': 1") == {"a b": 1}
    with pytest.raises(YamlError, match="duplicate key"):
        load("a: 1\na: 2")


# ---------- flow collections ----------


def test_flow_mapping_and_sequence():
    assert load("a: { x: 1, y: [p, q], z: {} }") == {"a": {"x": 1, "y": ["p", "q"], "z": {}}}
    assert load("a: [1, 'two', three, [4]]") == {"a": [1, "two", "three", [4]]}
    assert load("a: []") == {"a": []}


def test_flow_mapping_key_without_value_and_url_value():
    assert load("a: {flag, url: http://h:9090/x}") == {"a": {"flag": None, "url": "http://h:9090/x"}}


def test_whole_document_is_a_flow_collection():
    assert load("[a, b]") == ["a", "b"]
    assert load("{a: 1}") == {"a": 1}


# ---------- comments (bug a: apostrophe inside a plain scalar) ----------


def test_comment_after_plain_scalar():
    assert load("a: value # note") == {"a": "value"}
    assert load("a: value#notacomment") == {"a": "value#notacomment"}


def test_apostrophe_inside_plain_scalar_does_not_open_a_quote():
    # Before the fix the apostrophe in Karpenter's started a "quote" and the comment stayed in the value.
    assert load("why: Karpenter's budget # note") == {"why": "Karpenter's budget"}
    assert load("- Karpenter's budget # note") == ["Karpenter's budget"]


def test_hash_inside_quotes_is_kept_and_comment_after_quote_is_dropped():
    assert load("a: 'x # y' # c") == {"a": "x # y"}
    assert load('a: "x # y" # c') == {"a": "x # y"}
    assert load("a: 'it''s # not' # yes") == {"a": "it's # not"}
    assert load("a: ['x # y', \"z\"] # c") == {"a": ["x # y", "z"]}
    assert load("- 'q # r' # c") == ["q # r"]


def test_comment_only_line_and_percent_directive_are_skipped():
    assert y("""
        %YAML 1.2
        # heading comment
        a: 1
          # indented comment
        b: 2
        """) == {"a": 1, "b": 2}


# ---------- block scalars (bug b: keep chomping) ----------


def test_literal_block_clip_keeps_one_newline():
    assert y("""
        a: |
          line one
          line two

        b: 1
        """) == {"a": "line one\nline two\n", "b": 1}


def test_literal_block_strip():
    assert y("""
        a: |-
          x
          y
        """) == {"a": "x\ny"}


def test_literal_block_keep_preserves_trailing_newlines():
    # Before the fix `|+` behaved like `|` and dropped the trailing blank lines.
    assert y("""
        a: |+
          x


        b: 1
        """) == {"a": "x\n\n\n", "b": 1}


def test_folded_block_variants():
    assert y("""
        a: >
          one
          two

          three
        """) == {"a": "one two\nthree\n"}
    assert y("""
        a: >-
          one
          two
        """) == {"a": "one two"}
    assert y("""
        a: >+
          one
          two

        """) == {"a": "one two\n\n"}


def test_block_scalar_keeps_hash_and_relative_indent():
    assert y("""
        a: |
          # not a comment
            indented
        """) == {"a": "# not a comment\n  indented\n"}


def test_block_scalar_inside_sequence_item():
    assert y("""
        - text: |
            hi
          n: 1
        """) == [{"text": "hi\n", "n": 1}]


# ---------- multi-line quoted scalar ----------


def test_quoted_scalar_spanning_lines_is_joined_with_spaces():
    assert y("""
        a: "first
          second"
        b: 1
        """) == {"a": "first second", "b": 1}


# ---------- errors ----------


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("a: [1, 2", "unterminated"),
        ("a: {x: 1", "unterminated"),
        ("a: 'oops", "unterminated quote"),
        ("a:\n  b: 1\n c: 2", "indent"),
        ("a: 1\n  b: 2", "indentation mismatch"),
        ("a: |2\n  x", "block string indicator"),
        ("a: &anchor x", "anchors"),
        ("a: *alias", "anchors"),
        ("a: !!str x", "anchors"),
        ("a: 1\n---\nb: 2", "multiple documents"),
        ("a:\n\tb: 1", "tab in indentation"),
        ("a: 1\nplain text without colon", "not a `key: value` entry"),
        ("a: [1] trailing", "trailing content"),
    ],
)
def test_errors(text, match):
    with pytest.raises(YamlError, match=match):
        load(text)


def test_load_file(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("a: 1\nb: [x]\n", encoding="utf-8")
    assert yamlite.load_file(p) == {"a": 1, "b": ["x"]}
    assert yamlite.load_file(str(p)) == {"a": 1, "b": ["x"]}


def test_parse_scalar_directly():
    assert yamlite.parse_scalar(" 42 ") == 42
    assert yamlite.parse_scalar("{a: [1]}") == {"a": [1]}
    assert yamlite.parse_scalar("") is None

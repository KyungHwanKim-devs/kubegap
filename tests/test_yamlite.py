"""lib/foundations/yamlite.py: the hand-written YAML subset parser. Each test is one feature of the supported subset, one fixed bug, or one rejected construct."""

import textwrap

import pytest

from lib.foundations import yamlite
from lib.foundations.yamlite import YamlError, load


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


def test_bare_dash_at_same_indent_as_key():
    """A bare `-` at the key's indent starts the list as `- x` does, so a leading empty item loads (PyYAML gives the same)."""
    assert y("""
        a:
        -
        - y
        """) == {"a": [None, "y"]}
    assert y("""
        - k:
          -
          - w
        """) == [{"k": [None, "w"]}]
    assert y("""
        a:
        -
        b: 1
        """) == {"a": [None], "b": 1}


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


def test_empty_sequence_item_then_sibling_dash_is_not_nested():
    """Same-indent `- w` after an empty `-` is the next item, matching PyYAML (#66)."""
    assert y("""
        -
        - w
        """) == [None, "w"]
    assert y("""
        - a
        -
        - w
        """) == ["a", None, "w"]
    assert y("""
        a:
          -
          - w
        """) == {"a": [None, "w"]}


def test_scalar_on_the_line_after_key_or_dash():
    assert y("""
        a:
          value
        b:
          "q"
        c:
          -
            x
        """) == {"a": "value", "b": "q", "c": ["x"]}


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


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("a: first\n  second\nb: 1", 2),
        ("a: first\n\n  second", 3),
        ("a: 1\n  2", 2),
        ("- first\n  second", 2),
        ("- k: one\n    two", 2),
        ("x:\n  - a: 1\n    why: long text\n      continues here\n  - b", 4),
        ("a: first\n  - second", 2),
        ("a:\n  first\n  second", 3),
        ("-\n  first\n  second", 3),
    ],
)
def test_multi_line_plain_scalar_names_the_continuation_line(text, line):
    # PyYAML reads each of these as one folded string; before the fix the error was "indentation mismatch".
    with pytest.raises(YamlError, match=rf"^line {line}: .*multi-line plain scalars are not supported"):
        load(text)


@pytest.mark.parametrize("text", ["&a key: v", "!!str key: v", "- &a k: v", "a:\n  *x: 1"])
def test_anchor_or_tag_on_a_key_is_rejected(text):
    # Before the fix these were read as a key named "&a key" and so on.
    with pytest.raises(YamlError, match=r"^line \d+: anchors, aliases and tags are not supported"):
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


LOKI_LIKE = """auth_enabled: false
server:
  http_listen_port: 3100
limits_config:
  reject_old_samples: true
  retention_period: 31d
  per_tenant_override_config: ""
table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
ruler:
  storage:
    type: local
  write_throttle_query: sum(rate(cortex_dynamo_throttled_total{operation="x"}[1m]))
    by (table) > 0
compactor:
  working_directory: /data/loki/compactor
  retention_enabled: false
  retention_delete_delay: 2h0m0s
"""


def test_mapping_value_reads_a_key_inside_its_own_section_of_text_the_parser_cannot_load():
    """Loki's /config dump carries multi-line plain scalars (yamlite.load rejects them) and a `retention_period` under table_manager as well as under
    limits_config; the whole-text regular expression kubegap used took whichever came first (#126)."""
    import pytest

    from lib.foundations import yamlite

    with pytest.raises(yamlite.YamlError):
        yamlite.load(LOKI_LIKE)
    assert yamlite.mapping_value(LOKI_LIKE, "limits_config", "retention_period") == "31d"
    assert yamlite.mapping_value(LOKI_LIKE, "table_manager", "retention_period") == "0s"
    assert yamlite.mapping_value(LOKI_LIKE, "compactor", "retention_enabled") == "false"
    assert yamlite.mapping_value(LOKI_LIKE, "ruler", "storage", "type") == "local"
    assert yamlite.mapping_value(LOKI_LIKE, "limits_config", "retention_enabled") is None
    assert yamlite.mapping_value(LOKI_LIKE, "nowhere", "x") is None and yamlite.mapping_value(LOKI_LIKE, "auth_enabled") == "false"
    assert yamlite.mapping_value(LOKI_LIKE, "limits_config", "per_tenant_override_config") is None  # an empty quoted value reads as absent


FOLDED_AM = """receivers:
- name: slack
  slack_configs:
  - api_url: https://hooks.example/x
    title: 'a single-quoted title that go-yaml folded at eighty columns onto the
      next line'
    text: a plain very long text that go-yaml folded at eighty columns onto the next
      line and even a third
      line here
    send_resolved: true
route:
  receiver: slack
  routes:
  - receiver: slack
    matchers:
    - severity = "critical"
"""


def test_unfolding_plain_scalars_lets_go_yaml_output_load():
    """Alertmanager serves Config.String() and Loki its /config: both are go-yaml output, which folds plain scalars at 80 columns."""
    import pytest

    from lib.foundations import yamlite

    with pytest.raises(yamlite.YamlError):
        yamlite.load(FOLDED_AM)
    d = yamlite.load(yamlite.unfold_plain_scalars(FOLDED_AM))
    sc = d["receivers"][0]["slack_configs"][0]
    assert sc["text"] == "a plain very long text that go-yaml folded at eighty columns onto the next line and even a third line here"
    assert sc["title"] == "a single-quoted title that go-yaml folded at eighty columns onto the next line" and sc["send_resolved"] is True
    assert d["route"]["routes"][0]["matchers"] == ['severity = "critical"']
    d2 = yamlite.load(yamlite.unfold_plain_scalars(LOKI_LIKE))
    assert d2["limits_config"]["retention_period"] == "31d" and d2["ruler"]["write_throttle_query"].endswith("by (table) > 0")
    assert yamlite.unfold_plain_scalars("a: 1\nb:\n  - x\n  - y\n") == "a: 1\nb:\n  - x\n  - y\n"  # nothing to unfold stays byte-identical


def test_mapping_value_handles_block_scalars_comments_and_broken_quotes():
    from lib.foundations import yamlite

    text = 'a:\n  b: |\n    long\n  c: value # a comment\n  d: "quoted # not a comment"\n  e: "unterminated\n    continued"\n'
    assert yamlite.mapping_value(text, "a", "b") is None
    assert yamlite.mapping_value(text, "a", "c") == "value"
    assert yamlite.mapping_value(text, "a", "d") == "quoted # not a comment"
    assert yamlite.mapping_value(text, "a", "e") == '"unterminated'

"""lib/monitoring reads Loki's retention from the /config dump by structure, never from the first `retention_period:` line of the text (#126, #148)."""

from __future__ import annotations

from lib import monitoring

DUMP = """auth_enabled: false
limits_config:
  reject_old_samples: true
  retention_period: 31d
table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
ruler:
  write_throttle_query: sum(rate(cortex_dynamo_throttled_total{operation="DynamoDB.BatchWriteItem"}[1m]))
    by (table) > 0
compactor:
  retention_enabled: false
"""


def test_the_dump_is_parsed_whole_and_the_keys_come_from_their_sections():
    assert monitoring._loki_retention(DUMP) == ("31d", "false", "parsed")
    reordered = DUMP.replace("limits_config:\n  reject_old_samples: true\n  retention_period: 31d\n", "") + "limits_config:\n  retention_period: 7d\n"
    assert monitoring._loki_retention(reordered) == ("7d", "false", "parsed")  # table_manager's 0s comes first in the text and is not taken


def test_text_outside_the_parser_subset_falls_back_to_a_section_read():
    text = "anchors: &a\n  x: 1\nlimits_config:\n  retention_period: 14d\ncompactor:\n  retention_enabled: true\n"
    assert monitoring._loki_retention(text) == ("14d", "true", "section")
    assert monitoring._loki_retention("server:\n  http_listen_port: 3100\n") == (None, None, "parsed")


def test_a_real_loki_3_7_9_config_dump_loads_whole_once_unfolded():
    """tests/fixtures/loki-config-3.7.9.yaml is GET /config of loki 3.7.9 run locally with a minimal file configuration (retention 744h, compactor retention
    on): go-yaml folds its long query strings, yamlite.load refuses the raw text, and the unfolded text loads whole (3,584 lines, 42 top-level keys)."""
    from pathlib import Path

    from lib import yamlite

    dump = Path(__file__).parent.joinpath("fixtures", "loki-config-3.7.9.yaml").read_text(encoding="utf-8")
    import pytest

    with pytest.raises(yamlite.YamlError):
        yamlite.load(dump)
    d = yamlite.load(yamlite.unfold_plain_scalars(dump))
    assert len(d) >= 40 and d["limits_config"]["retention_period"] == "31d" and d["compactor"]["retention_enabled"] is True
    assert d["table_manager"]["retention_period"] == "0s"  # the other retention_period the old whole-text regex could have taken
    assert monitoring._loki_retention(dump) == ("31d", "true", "parsed")

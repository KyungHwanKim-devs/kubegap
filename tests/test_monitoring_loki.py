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

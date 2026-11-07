"""lib/foundations/snapshot's readers of metrics/<query>.json, the one reading of a Prometheus result file (#150)."""

import json
import math

from lib.foundations import snapshot


def _write(snap, qid, doc):
    (snap / "metrics").mkdir(exist_ok=True)
    (snap / "metrics" / f"{qid}.json").write_text(json.dumps(doc))


def test_rows_come_only_from_a_query_that_ran_and_only_with_a_usable_value(tmp_path):
    _write(
        tmp_path,
        "ok",
        {
            "ok": True,
            "result": [{"metric": {"pod": "a"}, "value": [0, "1.5"]}, {"metric": {"pod": "b"}, "value": [0, "NaN"]}, {"metric": {"pod": "c"}, "value": [0, "+Inf"]}, {"metric": {"pod": "d"}}, {"metric": {"pod": "e"}, "value": [0, "x"]}],
        },
    )
    _write(tmp_path, "failed", {"ok": False, "error": "boom", "result": [{"metric": {}, "value": [0, "1"]}]})
    assert snapshot.metric_rows(tmp_path, "ok") == [({"pod": "a"}, 1.5)]
    assert snapshot.metric_result(tmp_path, "ok")[1]["metric"] == {"pod": "b"}, "metric_result hands the rows over as written; the value reading is metric_value's"
    assert snapshot.metric_rows(tmp_path, "failed") == [] and snapshot.metric_result(tmp_path, "failed") == []
    assert snapshot.metric_doc(tmp_path, "failed")["error"] == "boom"
    assert snapshot.metric_doc(tmp_path, "missing") is None and snapshot.metric_rows(tmp_path, "missing") == []


def test_value_scalar_and_sum(tmp_path):
    assert snapshot.metric_value({"value": [0, "2.5"]}) == 2.5 and snapshot.metric_value({"value": [0, "NaN"]}) is None and snapshot.metric_value({}) is None
    assert math.isnan(snapshot.metric_sample({"value": [0, "NaN"]})) and snapshot.metric_sample({"value": [0, "+Inf"]}) == float("inf") and snapshot.metric_sample({}) is None, "the evaluator keeps NaN for `value == value` rules"
    _write(tmp_path, "two", {"ok": True, "result": [{"metric": {}, "value": [0, "2"]}, {"metric": {}, "value": [0, "3"]}]})
    _write(tmp_path, "empty", {"ok": True, "result": []})
    assert snapshot.metric_scalar(tmp_path, "two") == 2.0 and snapshot.metric_sum(tmp_path, "two") == 5.0
    assert snapshot.metric_scalar(tmp_path, "empty") is None and snapshot.metric_sum(tmp_path, "empty") is None, "no rows is not a zero"


def test_metric_by_keys_rows_by_one_or_several_labels_and_drops_unaddressable_rows(tmp_path):
    _write(tmp_path, "q", {"ok": True, "result": [{"metric": {"ns": "a", "pod": "x"}, "value": [0, "1"]}, {"metric": {"ns": "b", "pod": "y"}, "value": [0, "2"]}, {"metric": {"pod": "z"}, "value": [0, "3"]}]})
    assert snapshot.metric_by(tmp_path, "q", "ns") == {"a": 1.0, "b": 2.0}
    assert snapshot.metric_by(tmp_path, "q", "ns", "pod") == {("a", "x"): 1.0, ("b", "y"): 2.0}
    assert snapshot.metric_by(tmp_path, "missing", "ns") == {}


def test_series_present_is_the_names_map_or_none(tmp_path):
    assert snapshot.series_present(tmp_path) is None
    (tmp_path / "metrics").mkdir()
    (tmp_path / "metrics" / "series-present.json").write_text(json.dumps({"names": {"up": 3, "gone_metric": 0}}))
    assert snapshot.series_present(tmp_path) == {"up": 3, "gone_metric": 0}
    (tmp_path / "metrics" / "series-present.json").write_text(json.dumps({"names": []}))
    assert snapshot.series_present(tmp_path) is None


def test_node_os_text_reads_the_node_script_output_or_none(tmp_path):
    assert snapshot.node_os_text(tmp_path, "n1") is None
    (tmp_path / "logs" / "node" / "n1").mkdir(parents=True)
    (tmp_path / "logs" / "node" / "n1" / "os.txt").write_bytes(b"### meta\nhostname=n1\n\xff")
    assert snapshot.node_os_text(tmp_path, "n1").startswith("### meta\nhostname=n1\n")


def test_a_document_that_is_not_a_mapping_is_no_document(tmp_path):
    _write(tmp_path, "list", [1, 2])
    assert snapshot.metric_doc(tmp_path, "list") is None and snapshot.metric_rows(tmp_path, "list") == []

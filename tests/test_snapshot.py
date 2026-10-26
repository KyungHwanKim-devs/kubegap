"""lib/snapshot.py: forgiving readers (a missing or corrupt file must not stop the summary)."""

import json

from lib import snapshot


def test_load_json_reads_a_valid_file(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"items": [1, 2]}), encoding="utf-8")
    assert snapshot.load_json(p) == {"items": [1, 2]}


def test_load_json_missing_file_returns_none(tmp_path):
    assert snapshot.load_json(tmp_path / "missing.json") is None


def test_load_json_corrupt_file_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert snapshot.load_json(p) is None


def test_load_json_on_a_directory_returns_none(tmp_path):
    assert snapshot.load_json(tmp_path) is None


def test_items_handles_every_shape():
    assert snapshot.items({"items": [{"a": 1}]}) == [{"a": 1}]
    assert snapshot.items({"items": None}) == []
    assert snapshot.items({"kind": "List"}) == []
    assert snapshot.items(None) == []
    assert snapshot.items([1, 2]) == []
    assert snapshot.items("text") == []


def test_objects_reads_objects_folder_by_stem(tmp_path):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "bgppeers.metallb.io.json").write_text(json.dumps({"items": [{"metadata": {"name": "p"}}]}), encoding="utf-8")
    assert snapshot.objects(tmp_path, "bgppeers.metallb.io") == [{"metadata": {"name": "p"}}]


def test_objects_missing_or_corrupt_returns_empty_list(tmp_path):
    assert snapshot.objects(tmp_path, "deployments.apps") == []
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / "deployments.apps.json").write_text("[", encoding="utf-8")
    assert snapshot.objects(tmp_path, "deployments.apps") == []

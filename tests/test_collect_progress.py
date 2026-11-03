"""The progress line collect prints per finished collector and writes into INCOMPLETE (#78)."""

from lib import collect


def test_progress_line_has_counts_elapsed_last_and_running():
    line = collect.progress_line(7, 21, 61.4, ("eks-platform", 42.2), ["core", "karpenter"])
    assert line == "progress: 7/21 collectors done, elapsed 61 s, last eks-platform 42 s, running core, karpenter"


def test_progress_line_before_the_first_collector_finishes():
    assert collect.progress_line(0, 21, 0.2, None, []) == "progress: 0/21 collectors done, elapsed 0 s"


def test_progress_counts_finished_collectors():
    p = collect.Progress(3, collect._time.monotonic())
    first = p.done("core", 10.0, ["a", "b"])
    second = p.done("a", 2.0, ["b"])
    assert first.startswith("progress: 1/3 collectors done")
    assert second.startswith("progress: 2/3 collectors done") and "last a 2 s" in second and second.endswith("running b")


def test_incomplete_marker_carries_the_progress_line_first(tmp_path):
    collect._write_incomplete(tmp_path, "progress: 1/3 collectors done, elapsed 5 s")
    text = (tmp_path / "INCOMPLETE").read_text().splitlines()
    assert text[0] == "progress: 1/3 collectors done, elapsed 5 s"
    assert "interrupted" in text[1]

"""`lib/foundations/durations.go_duration_s` reads what Go's `time.ParseDuration` reads (golang/go src/time/format.go:1605-1614,1621-1718@go1.25.0): the form of every
`metav1.Duration` field and of the Argo CD and KEDA ConfigMap values kubegap compares (#124 N-7, N-8)."""

import pytest

from lib.foundations.durations import go_duration_s


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("720h", 2592000.0),
        ("30m", 1800.0),
        ("20m0s", 1200.0),
        ("1h30m", 5400.0),  # compound: the three former regexes returned None here
        ("3m0s", 180.0),
        ("90m0s", 5400.0),
        ("2m30s", 150.0),
        ("1.5h", 5400.0),
        ("100ms", 0.1),
        ("0", 0.0),  # the one bare number Go accepts
        ("-1m", -60.0),
        (" 15s ", 15.0),
    ],
)
def test_go_durations_parse(text, seconds):
    assert go_duration_s(text) == pytest.approx(seconds)


@pytest.mark.parametrize("text", ["Never", "", None, "15", "1d", "1h30", "5", "abc", "1w"])
def test_non_durations_are_none(text):
    assert go_duration_s(text) is None

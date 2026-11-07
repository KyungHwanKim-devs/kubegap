"""lib/foundations/quantity: the one reader of Kubernetes quantities (#150)."""

import pytest

from lib.foundations import quantity


@pytest.mark.parametrize(
    "text, value",
    [
        ("500m", 0.5),
        ("2", 2.0),
        ("1.5", 1.5),
        ("128Ki", 131072.0),
        ("512Mi", 536870912.0),
        ("2Gi", 2147483648.0),
        ("1Ti", 1099511627776.0),
        ("1Pi", 1125899906842624.0),
        ("1Ei", 1152921504606846976.0),
        ("2k", 2000.0),
        ("2K", 2000.0),
        ("3M", 3000000.0),
        ("4G", 4000000000.0),
        ("5T", 5000000000000.0),
        ("1P", 1e15),
        ("1E", 1e18),
        (" 100m ", 0.1),
        (7, 7.0),
        (0.25, 0.25),
    ],
)
def test_parse_reads_every_suffix_apimachinery_accepts(text, value):
    assert quantity.parse(text) == pytest.approx(value)


def test_parse_gives_the_default_for_nothing_and_for_text_that_is_not_a_quantity():
    assert quantity.parse(None) == 0.0 and quantity.parse("") == 0.0 and quantity.parse("   ") == 0.0
    assert quantity.parse("lots") == 0.0 and quantity.parse("Gi") == 0.0 and quantity.parse("1.2.3") == 0.0
    assert quantity.parse(None, None) is None and quantity.parse("lots", None) is None


def test_binary_suffix_wins_over_the_milli_and_decimal_letters_it_ends_with():
    assert quantity.parse("5Mi") == 5 * 1024**2 and quantity.parse("5M") == 5e6 and quantity.parse("5m") == 0.005


def test_mib_is_the_constant_the_memory_readers_divide_by():
    assert quantity.parse("512Mi") / quantity.MIB == 512.0


def test_to_float_and_to_int():
    assert quantity.to_float("3.5") == 3.5 and quantity.to_float(2) == 2.0
    assert quantity.to_float(None) is None and quantity.to_float("x") is None and quantity.to_float("x", 0.0) == 0.0
    assert quantity.to_int("3.9") == 3 and quantity.to_int(None) == 0 and quantity.to_int("x", None) is None and quantity.to_int("12") == 12


def test_rounded_lets_none_through():
    assert quantity.rounded(None) is None and quantity.rounded(1.23456) == 1.235 and quantity.rounded(1.23456, 1) == 1.2

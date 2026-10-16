"""Check documented decimal precision and explicit missing-value handling."""

from decimal import Decimal

import pytest

from gas_intel.validation.values import classify_volume


@pytest.mark.parametrize("text", ["", " ", "***", "NaN", "Infinity", "1e3", "1,000", "bad"])
def test_unresolved_values_are_never_zero(text: str) -> None:
    assert classify_volume(text) == ("invalid_or_blank", None)


@pytest.mark.parametrize("text", ["1.0001", "10000000000", "-10000000000"])
def test_source_precision_is_enforced(text: str) -> None:
    assert classify_volume(text)[0] == "outside_documented_precision"


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("0", "zero"),
        ("-0.000", "zero"),
        ("-1", "negative"),
        ("9999999999.999", "positive"),
        (" 1.125 ", "positive"),
    ],
)
def test_valid_decimal_values_keep_exact_precision(text: str, state: str) -> None:
    assert classify_volume(text) == (state, Decimal(text))

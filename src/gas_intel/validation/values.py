"""Classify source gas volumes without converting unresolved values to zero."""

import re
from decimal import Decimal

DECIMAL_TEXT = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?\Z")


def classify_volume(text: str) -> tuple[str, Decimal | None]:
    """Apply documented Decimal(13,3) capacity and the V1 nonnegative policy."""
    if not DECIMAL_TEXT.fullmatch(text.strip()):
        return "invalid_or_blank", None
    value = Decimal(text)
    if value.as_tuple().exponent < -3 or abs(value) >= Decimal("10000000000"):
        return "outside_documented_precision", value
    return "negative" if value < 0 else "zero" if value == 0 else "positive", value

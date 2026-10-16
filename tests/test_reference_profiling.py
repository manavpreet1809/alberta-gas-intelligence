"""Reference schema checks use synthetic identifiers and no contact details."""

from pathlib import Path

import pytest

from gas_intel.reference_profiling import profile_reference


def test_reference_keys_preserve_leading_zeros_and_detect_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_operators.csv"
    path.write_text("BAIdentifier,BALegalName\n0012,Example A\n12,Example B\n0012,Example A\n,\n")
    report = profile_reference(path, "operators")
    assert report["row_count"] == 4
    assert report["distinct_keys"] == 3
    assert report["duplicate_extra_rows"] == 1
    assert report["blank_key_rows"] == 1
    assert report["blank_counts"]["BALegalName"] == 1
    assert "Example A" not in str(report)


def test_history_is_not_assumed_unique_per_facility(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_history.csv"
    path.write_text(
        "FacilityID,OperatorBAID,StartDate,EndDate\n"
        "ABBT0000001,0012,2024-01,2024-12\nABBT0000001,0013,2025-01,9999-12\n"
    )
    assert profile_reference(path, "operator_history")["distinct_keys"] == 2


@pytest.mark.parametrize("source", ["facilities", "operators", "operator_history"])
def test_wrong_reference_schema_fails(tmp_path: Path, source: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("unknown\nvalue\n")
    with pytest.raises(ValueError, match="columns"):
        profile_reference(path, source)


def test_unknown_reference_type_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown reference"):
        profile_reference(tmp_path / "missing.csv", "unknown")

"""Changes in observed rows are distinct from operational events."""

from pathlib import Path

import pytest

from gas_intel.continuity import compare_assignments, compare_months

FIXTURE = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"


def test_missing_production_row_with_other_activity_is_visible(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    current.write_bytes(
        FIXTURE.read_bytes()
        .replace(b"2025-01", b"2025-02")
        .replace(b",PROD,GAS,***", b",REC,GAS,***")
    )
    report = compare_months(FIXTURE, current, "2025-01", "2025-02")
    assert report["qualifying_only_previous"] == 1
    assert report["previous_qualifying_now_other_rows_only"] == 1
    assert report["previous_qualifying_now_no_facility_rows"] == 0


def test_nonconsecutive_comparisons_fail() -> None:
    with pytest.raises(ValueError, match="consecutive"):
        compare_months(FIXTURE, FIXTURE, "2025-01", "2025-03")


def test_current_operator_does_not_replace_historical_assignment(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    history.write_text(
        "FacilityID,OperatorBAID,StartDate,EndDate\n"
        "ABBT0000001,0012,2024-01,2025-01\n"
        "ABBT0000001,0013,2025-02,9999-12\n"
    )
    current = tmp_path / "current.csv"
    current.write_text("FacilityID,OperatorBAID\nABBT0000001,0013\n")
    report = compare_assignments(FIXTURE, "2025-01", history, current)
    assert report["checks"]["history_match"] == 1
    assert report["checks"]["current_operator_differs"] == 1
    assert report["checks"]["history_missing"] == 3


def test_duplicate_current_reference_keys_fail(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    history.write_text("FacilityID,OperatorBAID,StartDate,EndDate\n")
    current = tmp_path / "current.csv"
    current.write_text("FacilityID,OperatorBAID\nA,0012\nA,0013\n")
    with pytest.raises(ValueError, match="Duplicate"):
        compare_assignments(FIXTURE, "2025-01", history, current)

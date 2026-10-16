"""Temporal edge cases protect operator assignment from silent row multiplication."""

from pathlib import Path

import pytest

from gas_intel.history_profiling import assignment_candidates, month_number, profile_history


@pytest.mark.parametrize("value", ["2025-00", "2025-13", "2025-1", "0000-01", " 2025-01", "bad"])
def test_invalid_periods_fail(value: str) -> None:
    with pytest.raises(ValueError, match="period"):
        month_number(value)


def test_open_end_and_year_boundary() -> None:
    assert month_number("2025-01") == month_number("2024-12") + 1
    intervals = [
        (month_number("2024-01"), month_number("2024-12"), "0012"),
        (month_number("2025-01"), month_number("9999-12"), "0013"),
    ]
    assert assignment_candidates(intervals, "2024-12") == ["0012"]
    assert assignment_candidates(intervals, "2025-01") == ["0013"]
    assert assignment_candidates(intervals, "2023-12") == []


def test_overlap_is_not_silently_resolved() -> None:
    intervals = [
        (month_number("2024-01"), month_number("2025-01"), "0012"),
        (month_number("2025-01"), month_number("9999-12"), "0013"),
    ]
    assert assignment_candidates(intervals, "2025-01") == ["0012", "0013"]


def test_history_diagnostics_detect_gaps_and_overlaps(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_history.csv"
    path.write_text(
        "FacilityID,OperatorBAID,StartDate,EndDate\n"
        "ABBT0000001,0012,2024-01,2024-12\n"
        "ABBT0000001,0013,2024-12,2025-01\n"
        "ABBT0000001,0014,2025-03,9999-12\n"
    )
    report = profile_history(path)
    assert report["overlap_events"] == 1
    assert report["gap_events"] == 1
    assert report["open_end_rows"] == 1


def test_reversed_history_fails(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_history.csv"
    path.write_text("FacilityID,OperatorBAID,StartDate,EndDate\nA,0012,2025-01,2024-01\n")
    with pytest.raises(ValueError, match="Reversed"):
        profile_history(path)

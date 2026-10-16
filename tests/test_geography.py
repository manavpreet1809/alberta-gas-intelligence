"""Verify inclusion boundaries without assuming a geological formation."""

import csv
from pathlib import Path

import pytest

from gas_intel.geography import DLSBox, profile_box


@pytest.mark.parametrize("township,range_", [("060", "03"), ("065", "07"), ("63", "5")])
def test_box_is_inclusive_and_accepts_leading_zeros(township: str, range_: str) -> None:
    assert DLSBox(60, 65, 3, 7, 6).contains(township, range_, "06")


@pytest.mark.parametrize(
    "coordinates", [("59", "5", "6"), ("66", "5", "6"), ("63", "8", "6"), ("63", "5", "5")]
)
def test_box_excludes_other_locations(coordinates: tuple[str, str, str]) -> None:
    assert not DLSBox(60, 65, 3, 7, 6).contains(*coordinates)


@pytest.mark.parametrize(
    "coordinates", [("", "5", "6"), ("W6", "5", "6"), ("63", "5.0", "6"), ("６３", "5", "6")]
)
def test_malformed_coordinates_are_not_silently_included(coordinates) -> None:
    with pytest.raises(ValueError, match="ASCII"):
        DLSBox(60, 65, 3, 7, 6).contains(*coordinates)


@pytest.mark.parametrize(
    "bounds", [(65, 60, 3, 7, 6), (60, 65, 7, 3, 6), (0, 65, 3, 7, 6), (True, 65, 3, 7, 6)]
)
def test_invalid_bounds_fail(bounds) -> None:
    with pytest.raises(ValueError):
        DLSBox(*bounds)


def test_coverage_uses_detail_rows_without_double_counting_facilities(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"
    with fixture.open() as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        headers = reader.fieldnames
    for row in rows:
        row.update(FacilityTownship="63", FacilityRange="5", FacilityMeridian="6")
    rows[2]["FacilityMeridian"] = "5"
    path = tmp_path / "synthetic_scope.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = profile_box(path, "2025-01", DLSBox(60, 65, 3, 7, 6))
    assert report["gas_prod_rows"] == 4
    assert report["producing_facility_count"] == 3
    assert report["accepted_volume_e3m3"] == "102.500"
    assert report["invalid_selected_volume_rows"] == 2

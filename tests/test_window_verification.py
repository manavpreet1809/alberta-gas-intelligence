"""Full-window checks detect missing periods, changed bytes and location drift."""

import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

from gas_intel.geography import DLSBox
from gas_intel.profiling import profile_source
from gas_intel.window_verification import month_sequence, verify_window


def prepare_month(root: Path, month: str, township: str = "63") -> None:
    """Build synthetic local inventory; never require real source files in CI."""
    fixture = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"
    with fixture.open() as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames
        rows = list(reader)
    for row in rows:
        row.update(
            ProductionMonth=month,
            FacilityTownship=township,
            FacilityRange="5",
            FacilityMeridian="6",
        )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode()
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "data/raw" / digest / "source.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    profile = profile_source(path, month)
    target = root / "data/verification" / f"{month}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "event": {
                    "source_file": str(path.relative_to(root)),
                    "sha256": digest,
                    "url": "https://example.invalid/synthetic",
                    "downloaded_at": "2026-10-18T00:00:00+00:00",
                },
                "profile": profile,
            }
        )
    )


@pytest.fixture
def window_root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(Path(__file__).parents[1] / "config/sources.yaml", tmp_path / "config/sources.yaml")
    return tmp_path


def test_explicit_month_sequence_handles_year_boundary() -> None:
    assert month_sequence("2023-12", "2024-02") == ["2023-12", "2024-01", "2024-02"]
    assert len(month_sequence("2024-01", "2025-12")) == 24


def test_reversed_window_fails() -> None:
    with pytest.raises(ValueError, match="reversed"):
        month_sequence("2025-12", "2024-01")


def test_window_totals_and_cohort_are_independently_measured(window_root: Path) -> None:
    prepare_month(window_root, "2025-01")
    prepare_month(window_root, "2025-02")
    report = verify_window(window_root, "2025-01", "2025-02", DLSBox(60, 65, 3, 7, 6))
    assert report["month_count"] == 2
    assert report["candidate_cohort_facility_count"] == 4
    assert report["candidate_location_conflict_facility_count"] == 0
    assert report["monthly_checks"][0]["source_volume_e3m3"] == "101.500"
    assert report["monthly_checks"][0]["unresolved_volume_facilities"] == 2


def test_earlier_outside_box_location_is_not_lost(window_root: Path) -> None:
    prepare_month(window_root, "2025-01", township="59")
    prepare_month(window_root, "2025-02", township="63")
    report = verify_window(window_root, "2025-01", "2025-02", DLSBox(60, 65, 3, 7, 6))
    assert report["candidate_location_conflict_facility_count"] == 4


def test_missing_month_cannot_be_treated_as_zero(window_root: Path) -> None:
    prepare_month(window_root, "2025-01")
    with pytest.raises(FileNotFoundError):
        verify_window(window_root, "2025-01", "2025-02", DLSBox(60, 65, 3, 7, 6))


def test_changed_raw_bytes_fail(window_root: Path) -> None:
    prepare_month(window_root, "2025-01")
    source = next((window_root / "data/raw").glob("*/source.zip"))
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        verify_window(window_root, "2025-01", "2025-01", DLSBox(60, 65, 3, 7, 6))

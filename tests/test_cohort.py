"""Candidate cohort evidence uses fixed analysis membership and separate context."""

import json
import shutil
from pathlib import Path

import pytest
from test_pipeline import source as pipeline_source

from gas_intel.cohort import prepare_cohort
from gas_intel.window_verification import month_sequence


def source(root: Path, month: str, records: list[dict]) -> None:
    """Add the source URL required by the independent window audit contract."""
    pipeline_source(root, month, records)
    path = root / "data/verification" / f"{month}.json"
    inventory = json.loads(path.read_text())
    inventory["event"]["url"] = "https://example.invalid/synthetic"
    path.write_text(json.dumps(inventory))


@pytest.fixture
def cohort_root(tmp_path: Path) -> Path:
    shutil.copytree(Path(__file__).parents[1] / "config", tmp_path / "config")
    for month in month_sequence("2023-12", "2025-12"):
        records = [{}]
        if month == "2023-12":
            records.append({"ReportingFacilityID": "ABBT9999999", "Volume": "50.000"})
        if month == "2025-12":
            records.append({"ReportingFacilityID": "ABBT0000002", "Volume": "25.000"})
        source(tmp_path, month, records)
    return tmp_path


def test_fixed_cohort_excludes_context_only_and_retains_late_members(cohort_root: Path) -> None:
    result = prepare_cohort(cohort_root)
    assert result["facility_count"] == 2
    assert result["source_month_count"] == 25
    assert result["analysis_month_count"] == 24
    assert result["scope_approved"] is False
    artifact_path = cohort_root / result["artifact"]
    artifact = json.loads(artifact_path.read_text())
    assert [row["facility_id"] for row in artifact["facilities"]] == ["ABBT0000001", "ABBT0000002"]
    context = artifact["monthly_source_baselines"][0]
    assert context["candidate_volume_e3m3"] == "150.125"
    assert context["cohort_volume_e3m3"] == "100.125"
    assert context["cohort_gas_prod_rows"] == 1
    assert artifact["monthly_source_baselines"][-1]["cohort_volume_e3m3"] == "125.125"
    assert prepare_cohort(cohort_root) == result
    assert len(list(artifact_path.parent.glob("*.json"))) == 1


def test_context_location_outside_box_is_checked_for_analysis_members(cohort_root: Path) -> None:
    source(cohort_root, "2023-12", [{"FacilityTownship": "59"}])
    with pytest.raises(ValueError, match="Conflicting cohort location"):
        prepare_cohort(cohort_root)
    assert not (cohort_root / "data/processed/cohorts").exists()


@pytest.mark.parametrize(
    "records, message",
    [
        ([{"Volume": ""}], "Unresolved qualifying"),
        ([{}, {}], "Duplicate cohort detail"),
        ([{}, {"ActivityID": "REC", "OperatorBAID": "0099"}], "Conflicting cohort operators"),
    ],
)
def test_unresolved_cohort_input_blocks_artifact(
    cohort_root: Path, records: list, message: str
) -> None:
    source(cohort_root, "2025-01", records)
    with pytest.raises(ValueError, match=message):
        prepare_cohort(cohort_root)
    assert not (cohort_root / "data/processed/cohorts").exists()


def test_missing_source_month_blocks_candidate_freeze(cohort_root: Path) -> None:
    (cohort_root / "data/verification/2024-06.json").unlink()
    with pytest.raises(FileNotFoundError):
        prepare_cohort(cohort_root)
    assert not (cohort_root / "data/processed/cohorts").exists()


def test_failed_artifact_publication_leaves_no_partial_target(
    cohort_root: Path, monkeypatch
) -> None:
    def fail_link(*args) -> None:
        raise OSError("simulated publication failure")

    monkeypatch.setattr("gas_intel.cohort.os.link", fail_link)
    with pytest.raises(OSError, match="publication failure"):
        prepare_cohort(cohort_root)
    assert list((cohort_root / "data/processed/cohorts").iterdir()) == []

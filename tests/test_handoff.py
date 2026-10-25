"""Portable handoff verifies accepted exports and exact start/end bridge boundaries."""

import hashlib
import json
from pathlib import Path

import duckdb
import pytest
from test_cohort import cohort_root, source  # noqa: F401
from test_full_window_pipeline import full_project  # noqa: F401

from gas_intel.cohort import prepare_cohort
from gas_intel.handoff import handoff_report
from gas_intel.pipeline import run_pipeline


@pytest.fixture
def bundle(full_project) -> Path:  # noqa: F811
    root, _ = full_project
    source(
        root,
        "2023-12",
        [{"Volume": "200.125"}, {"ReportingFacilityID": "ABBT9999999", "Volume": "50"}],
    )
    artifact = Path(prepare_cohort(root)["artifact"])
    return run_pipeline(root, [], offline=True, cohort_artifact=artifact)


def test_three_findings_and_start_exclusive_bridge_boundary(bundle: Path) -> None:
    report = handoff_report(bundle)
    assert report["files_verified"] == 30
    assert len(report["findings"]) == 3
    assert report["dashboard_created"] is False
    assert report["dax_executed"] is False
    assert report["human_scope_approval_recorded"] is False
    assert report["table_rows"]["facility_month"] == 48
    area = report["findings"][0]
    assert area["start_volume"] == "100.125"
    assert area["end_volume"] == "125.125"
    assert area["change"] == "25.000"
    assert report["findings"][1]["operator_id"] == "0012"
    # The context-to-January change is -100; it must not enter the Jan-to-Dec bridge.
    # A later new facility adds 25 to the same 0012 operator in this fixture.
    assert report["findings"][1]["change"] == "25.000"
    assert handoff_report(bundle) == report


def test_changed_export_bytes_are_rejected(bundle: Path) -> None:
    (bundle / "dim_facility.csv").write_text("modified")
    with pytest.raises(ValueError, match="hash/path mismatch"):
        handoff_report(bundle)


def test_duplicate_keys_rejected_even_if_file_hash_is_updated(bundle: Path) -> None:
    path = bundle / "fact_gas_production.parquet"
    with duckdb.connect() as db:
        db.execute("CREATE TABLE bad AS SELECT * FROM read_parquet(?)", [str(path)])
        db.execute("INSERT INTO bad SELECT * FROM bad LIMIT 1")
        db.execute("COPY bad TO ? (FORMAT PARQUET)", [str(path)])
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["files_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="key validation failed"):
        handoff_report(bundle)


def test_unaccepted_bundle_cannot_generate_portfolio_evidence(bundle: Path) -> None:
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["validation"]["bridge_checks"]["passed"] = False
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="accepted bridge validation"):
        handoff_report(bundle)


def test_foreign_identifier_cannot_be_coerced_to_number(bundle: Path) -> None:
    path = bundle / "fact_gas_production.parquet"
    with duckdb.connect() as db:
        db.execute(
            "CREATE TABLE bad AS SELECT * REPLACE(operator_id::INT AS operator_id) "
            "FROM read_parquet(?)",
            [str(path)],
        )
        db.execute("COPY bad TO ? (FORMAT PARQUET)", [str(path)])
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["files_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="must remain text"):
        handoff_report(bundle)

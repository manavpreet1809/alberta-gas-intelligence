"""Offline integration tests exercise source totals, joins, states and publication failures."""

import csv
import io
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import duckdb
import pytest
from typer.testing import CliRunner

from gas_intel.cli import app
from gas_intel.pipeline import (
    build_model,
    export_tables,
    load_sources,
    run_pipeline,
    validate_warehouse,
)
from gas_intel.profiling import profile_source


@pytest.fixture
def project(tmp_path: Path) -> Path:
    repository = Path(__file__).parents[1]
    shutil.copytree(repository / "config", tmp_path / "config")
    shutil.copytree(repository / "sql", tmp_path / "sql")
    return tmp_path


def source(root: Path, month: str, records: list[dict]) -> None:
    """Materialize a synthetic pinned source using the observed thirty-column header."""
    import hashlib

    fixture = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"
    headers = fixture.read_text().splitlines()[0].split(",")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = {
            "ProductionMonth": month,
            "ReportingFacilityID": "ABBT0000001",
            "OperatorBAID": "0012",
            "OperatorName": "Example Operator",
            "ReportingFacilityName": "Example facility",
            "ReportingFacilityType": "BT",
            "FacilityTownship": "63",
            "FacilityRange": "5",
            "FacilityMeridian": "6",
            "SubmissionDate": "2025-03-15",
            "ActivityID": "PROD",
            "ProductID": "GAS",
            "FromToID": "ABWI0000001",
            "Volume": "100.125",
        }
        row.update(record)
        writer.writerow(row)
    payload = stream.getvalue().encode()
    for name in ["source.csv", "inner.zip"]:
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr(name, payload)
        payload = output.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "data/raw" / digest / "source.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    profile = profile_source(path, month)
    inventory = root / "data/verification" / f"{month}.json"
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(
        json.dumps(
            {
                "event": {
                    "source_file": str(path.relative_to(root)),
                    "sha256": digest,
                    "downloaded_at": "2026-10-19T00:00:00+00:00",
                },
                "profile": profile,
            }
        )
    )


def seed(project: Path) -> None:
    source(
        project,
        "2025-01",
        [
            {},
            {"FromToID": "ABWI0000002", "Volume": "2.375"},
            {"ReportingFacilityID": "ABBT0000002", "Volume": "0"},
            {"ActivityID": "REC", "Volume": "999"},
        ],
    )
    source(
        project,
        "2025-02",
        [
            {"OperatorBAID": "0013", "Volume": "120.000"},
            {"ReportingFacilityID": "ABBT0000002", "ActivityID": "SHUTIN", "Volume": ""},
            {"ReportingFacilityID": "ABBT0000003", "OperatorBAID": "", "Volume": "5.500"},
        ],
    )


def test_pipeline_preserves_states_historical_operators_and_exact_totals(
    project: Path,
) -> None:
    seed(project)
    output = run_pipeline(project, ["2025-01", "2025-02"], offline=True)
    assert output.is_dir()
    assert len(list(output.glob("*.csv"))) == 15
    assert len(list(output.glob("*.parquet"))) == 15
    with (output / "fact_gas_production.csv").open() as file:
        exported_rows = list(csv.DictReader(file))
    assert {row["operator_id"] for row in exported_rows if row["month"] == "2025-01"} == {"0012"}
    with duckdb.connect() as connection:
        value = connection.execute(
            "SELECT sum(volume) FROM read_parquet(?) WHERE month='2025-01'",
            [str(output / "fact_gas_production.parquet")],
        ).fetchone()[0]
    assert str(value) == "102.500"
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        states = db.execute(
            "SELECT report_status FROM core.facility_month WHERE "
            "facility_id='ABBT0000002' ORDER BY month"
        ).fetchall()
        assert states == [("reported_zero",), ("no_qualifying_row",)]
        assert db.execute(
            "SELECT operator_id FROM core.fact_gas_production WHERE "
            "facility_id='ABBT0000001' ORDER BY month"
        ).fetchall() == [("0012",), ("0013",)]
        assert [
            str(row[0])
            for row in db.execute(
                "SELECT volume FROM analytics.monthly_area_production ORDER BY month"
            ).fetchall()
        ] == ["102.500", "125.500"]
        assert db.execute("SELECT count(*) FROM core.facility_month").fetchone()[0] == 6
        assert (
            db.execute(
                "SELECT count(*) FROM core.fact_gas_production WHERE operator_id='UNKNOWN'"
            ).fetchone()[0]
            == 1
        )
    assert validate_warehouse(project)["passed"]


def test_reloading_does_not_duplicate_and_invalidates_previous_build(project: Path) -> None:
    seed(project)
    run_pipeline(project, ["2025-01"], offline=True)
    load_sources(project, ["2025-01"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        assert db.execute("SELECT count(*) FROM staging.volumetrics").fetchone()[0] == 4
    with pytest.raises(ValueError, match="Build"):
        export_tables(project)
    build_model(project)
    assert validate_warehouse(project)["passed"]


def test_tampered_analytics_blocks_export_and_preserves_last_bundle(project: Path) -> None:
    seed(project)
    accepted = run_pipeline(project, ["2025-01"], offline=True)
    previous = (project / "data/exports/latest.json").read_bytes()
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute("UPDATE analytics.monthly_area_production SET volume=volume+1")
    with pytest.raises(ValueError, match="reconciliation"):
        export_tables(project)
    assert (project / "data/exports/latest.json").read_bytes() == previous
    assert accepted.is_dir()


@pytest.mark.parametrize(
    "record", [{"Volume": ""}, {"Volume": "-1"}, {"Volume": "0.0001"}, {"Volume": "NaN"}]
)
def test_invalid_selected_volumes_block_before_accepting_a_load(
    project: Path, record: dict
) -> None:
    source(project, "2025-01", [record])
    with pytest.raises(ValueError, match="Unresolved"):
        run_pipeline(project, ["2025-01"], offline=True)
    assert not (project / "data/warehouse.duckdb").exists()


def test_duplicate_detail_rolls_back_build(project: Path) -> None:
    source(project, "2025-01", [{}, {}])
    load_sources(project, ["2025-01"], offline=True)
    with pytest.raises(ValueError, match="duplicate=1"):
        build_model(project)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='core'"
            ).fetchone()[0]
            == 0
        )


def test_missing_month_does_not_become_zero(project: Path) -> None:
    source(project, "2025-01", [{}])
    with pytest.raises(FileNotFoundError, match="inventory"):
        run_pipeline(project, ["2025-01", "2025-02"], offline=True)
    assert not (project / "data/warehouse.duckdb").exists()


def test_changed_raw_and_configuration_block_publication(project: Path) -> None:
    seed(project)
    run_pipeline(project, ["2025-01"], offline=True)
    inventory = json.loads((project / "data/verification/2025-01.json").read_text())
    path = project / inventory["event"]["source_file"]
    original = path.read_bytes()
    path.write_bytes(b"modified")
    with pytest.raises(ValueError, match="source changed"):
        export_tables(project)
    path.write_bytes(original)
    config = project / "config/study_area.yaml"
    config.write_text(config.read_text() + "\n# changed\n")
    with pytest.raises(ValueError, match="Configuration changed"):
        export_tables(project)


def test_cli_runs_fixture_pipeline_offline(project: Path) -> None:
    seed(project)
    result = CliRunner().invoke(
        app, ["run-all", "--project-root", str(project), "--month", "2025-01", "--offline"]
    )
    assert result.exit_code == 0, result.output
    assert (project / "data/exports/latest.json").exists()


def test_operator_attribution_corruption_is_detected_even_if_area_total_is_unchanged(
    project: Path,
) -> None:
    seed(project)
    run_pipeline(project, ["2025-01"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute("UPDATE core.fact_gas_production SET operator_id='0099'")
    with pytest.raises(ValueError, match="operator reconciliation"):
        export_tables(project)


def test_reporting_state_corruption_cannot_be_published(project: Path) -> None:
    seed(project)
    run_pipeline(project, ["2025-01", "2025-02"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute(
            "UPDATE core.facility_month SET report_status='reported_zero' "
            "WHERE report_status='no_qualifying_row'"
        )
    with pytest.raises(ValueError, match="reporting-state"):
        export_tables(project)


def test_inconsistent_monthly_operator_assignment_fails_build(project: Path) -> None:
    source(project, "2025-01", [{}, {"ActivityID": "REC", "OperatorBAID": "0013"}])
    load_sources(project, ["2025-01"], offline=True)
    with pytest.raises(ValueError, match="operator_conflict=1"):
        build_model(project)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE staging.volumetrics SET FromToID='different-origin'",
        "UPDATE staging.volumetrics SET downloaded_at='2099-01-01'",
        "UPDATE staging.volumetrics SET Volume=CASE WHEN Volume='100.125' "
        "THEN '99.125' WHEN Volume='2.375' THEN '3.375' ELSE Volume END",
    ],
)
def test_modified_staging_cannot_be_rebuilt_or_exported(project: Path, mutation: str) -> None:
    seed(project)
    accepted = run_pipeline(project, ["2025-01"], offline=True)
    latest = (project / "data/exports/latest.json").read_bytes()
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute(mutation)
    for operation in [build_model, export_tables]:
        with pytest.raises(ValueError, match="Staging snapshot integrity"):
            operation(project)
    assert (project / "data/exports/latest.json").read_bytes() == latest
    assert accepted.is_dir()


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE core.dim_facility SET facility_name='incorrect name'",
        "UPDATE core.excluded_records SET source_row_number=999",
        "UPDATE core.selected_records SET FromToID='incorrect origin'",
        "UPDATE core.facility_month SET operator_id='UNKNOWN'",
        "UPDATE analytics.operator_monthly_production SET area_share=0.123",
        "UPDATE analytics.data_quality_summary SET facility_count=999",
        "INSERT INTO analytics.monthly_area_production SELECT * "
        "FROM analytics.monthly_area_production",
    ],
)
def test_model_detail_changes_preserving_totals_block_publication(
    project: Path, mutation: str
) -> None:
    seed(project)
    run_pipeline(project, ["2025-01"], offline=True)
    latest = (project / "data/exports/latest.json").read_bytes()
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="Built table snapshot integrity"):
        export_tables(project)
    assert (project / "data/exports/latest.json").read_bytes() == latest
    # A clean rebuild from the accepted staging snapshot repairs derived tables.
    build_model(project)
    assert validate_warehouse(project)["passed"]


def test_snapshot_hash_retains_duplicates_and_ignores_physical_row_order() -> None:
    from gas_intel.pipeline import table_fingerprint

    with duckdb.connect() as db:
        db.execute(
            "CREATE TABLE example AS SELECT * FROM (VALUES ('001', 10), ('002', 20)) t(id,v)"
        )
        original = table_fingerprint(db, "example")
        db.execute("CREATE OR REPLACE TABLE example AS SELECT * FROM example ORDER BY id DESC")
        assert table_fingerprint(db, "example") == original
        db.execute("INSERT INTO example VALUES ('001', 10)")
        assert table_fingerprint(db, "example") != original
        with_duplicates = table_fingerprint(db, "example")
        db.execute("CREATE OR REPLACE TABLE example AS SELECT id, v::VARCHAR AS v FROM example")
        assert table_fingerprint(db, "example") != with_duplicates

"""Full-window pipeline tests retain fixed membership and isolate comparison context."""

import hashlib
import json
import shutil
from pathlib import Path

import duckdb
import pytest
from test_cohort import cohort_root, source  # noqa: F401
from typer.testing import CliRunner

from gas_intel.cli import app
from gas_intel.cohort import prepare_cohort
from gas_intel.pipeline import export_tables, load_sources, run_pipeline, validate_warehouse


@pytest.fixture
def full_project(cohort_root: Path) -> tuple[Path, Path]:  # noqa: F811
    shutil.copytree(Path(__file__).parents[1] / "sql", cohort_root / "sql")
    summary = prepare_cohort(cohort_root)
    return cohort_root, Path(summary["artifact"])


def changed_artifact(root: Path, path: Path, mutate) -> Path:
    value = json.loads((root / path).read_text())
    mutate(value)
    payload = json.dumps(value).encode()
    target = root / "data/processed/cohorts" / f"{hashlib.sha256(payload).hexdigest()}.json"
    target.write_bytes(payload)
    return target


def test_full_cli_run_keeps_context_out_of_reporting_exports(full_project) -> None:
    root, artifact = full_project
    result = CliRunner().invoke(
        app,
        ["run-all", "--project-root", str(root), "--cohort-artifact", str(artifact), "--offline"],
    )
    assert result.exit_code == 0, result.output
    latest = json.loads((root / "data/exports/latest.json").read_text())
    bundle = root / latest["path"]
    report = validate_warehouse(root)
    assert report["pilot"] is False
    assert report["scope_status"] == "working_scope"
    assert report["cohort_facilities"] == 2
    assert len(report["checks"]) == 25
    assert len(report["analysis_months"]) == 24
    assert report["context_months"] == ["2023-12"]
    with duckdb.connect(str(root / "data/warehouse.duckdb")) as db:
        assert db.execute("SELECT count(*) FROM core.facility_month").fetchone()[0] == 50
        assert db.execute("SELECT count(*) FROM analytics.monthly_area_all").fetchone()[0] == 25
        assert (
            db.execute("SELECT count(*) FROM analytics.monthly_area_production").fetchone()[0] == 24
        )
        assert (
            db.execute(
                "SELECT count(*) FROM core.dim_facility WHERE facility_id='ABBT9999999'"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT volume FROM analytics.monthly_area_all WHERE month='2023-12'"
            ).fetchone()[0]
            == 100.125
        )
        for table in [
            "dim_month",
            "fact_gas_production",
            "facility_month",
            "monthly_area_production",
            "operator_monthly_production",
            "data_quality_summary",
        ]:
            assert (
                db.execute(
                    "SELECT count(*) FROM read_parquet(?) WHERE month='2023-12'",
                    [str(bundle / f"{table}.parquet")],
                ).fetchone()[0]
                == 0
            )
        assert (
            db.execute(
                "SELECT count(*) FROM read_parquet(?)", [str(bundle / "facility_month.parquet")]
            ).fetchone()[0]
            == 48
        )
    # The same pinned source selection can be rerun without adding rows.
    load_sources(root, [], offline=True, cohort_artifact=artifact)
    with duckdb.connect(str(root / "data/warehouse.duckdb")) as db:
        assert db.execute("SELECT count(*) FROM staging.volumetrics").fetchone()[0] == 27


def test_changed_source_revision_cannot_replace_selected_snapshot(full_project) -> None:
    root, artifact = full_project
    run_pipeline(root, [], offline=True, cohort_artifact=artifact)
    previous = (root / "data/exports/latest.json").read_bytes()
    source(root, "2025-01", [{"Volume": "999.000"}])
    with pytest.raises(ValueError, match="source revision differs"):
        load_sources(root, [], offline=True, cohort_artifact=artifact)
    assert (root / "data/exports/latest.json").read_bytes() == previous


def test_altered_frozen_membership_cannot_build(full_project) -> None:
    root, path = full_project

    def alter(value):
        value["facilities"] = value["facilities"][:1]
        value["candidate_cohort_set_sha256"] = hashlib.sha256(b"ABBT0000001").hexdigest()

    changed = changed_artifact(root, path, alter)
    with pytest.raises(ValueError, match="Frozen cohort"):
        run_pipeline(root, [], offline=True, cohort_artifact=changed)
    assert not (root / "data/exports/latest.json").exists()


def test_wrong_baseline_blocks_export(full_project) -> None:
    root, path = full_project

    def alter(value):
        value["monthly_source_baselines"][1]["cohort_volume_e3m3"] = "999.000"

    changed = changed_artifact(root, path, alter)
    with pytest.raises(ValueError, match="reconciliation"):
        run_pipeline(root, [], offline=True, cohort_artifact=changed)
    assert not (root / "data/exports/latest.json").exists()


def test_artifact_modified_after_build_blocks_direct_export(full_project) -> None:
    root, path = full_project
    run_pipeline(root, [], offline=True, cohort_artifact=path)
    previous = (root / "data/exports/latest.json").read_bytes()
    (root / path).write_text("{}")
    with pytest.raises(ValueError, match="artifact hash"):
        export_tables(root)
    assert (root / "data/exports/latest.json").read_bytes() == previous


def test_cannot_mix_full_artifact_and_manual_months(full_project) -> None:
    root, path = full_project
    with pytest.raises(ValueError, match="either explicit months"):
        load_sources(root, ["2025-01"], offline=True, cohort_artifact=path)

"""Hand-calculated analytical examples cover boundaries, exits, UNKNOWN and ranks."""

from pathlib import Path

import duckdb
import pytest
from test_pipeline import project, source  # noqa: F401

from gas_intel.pipeline import run_pipeline
from gas_intel.validation.analytics import validate_analytics


def analytical_months(root: Path) -> list[str]:
    source(
        root,
        "2024-01",
        [
            {"Volume": "60.000"},
            {"ReportingFacilityID": "ABBT0000002", "OperatorBAID": "0013", "Volume": "40.000"},
        ],
    )
    source(
        root,
        "2024-02",
        [
            {"Volume": "50.000"},
            {"ReportingFacilityID": "ABBT0000003", "OperatorBAID": "0014", "Volume": "30.000"},
            {"ReportingFacilityID": "ABBT0000004", "OperatorBAID": "", "Volume": "20.000"},
        ],
    )
    source(root, "2024-03", [{"ActivityID": "REC", "Volume": "0"}])
    source(root, "2024-04", [{"Volume": "10.000"}])
    source(root, "2025-01", [{"Volume": "125.000"}])
    return ["2024-01", "2024-02", "2024-03", "2024-04", "2025-01"]


def test_hand_calculated_changes_concentration_and_drivers(project: Path) -> None:  # noqa: F811
    run_pipeline(project, analytical_months(project), offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        assert db.execute(
            "SELECT mom_change,mom_percent_change FROM "
            "analytics.monthly_area_production WHERE month='2024-01'"
        ).fetchone() == (None, None)
        assert db.execute(
            "SELECT mom_change,mom_percent_change FROM "
            "analytics.monthly_area_production WHERE month='2024-02'"
        ).fetchone() == (0, 0.0)
        assert db.execute(
            "SELECT mom_change,mom_percent_change FROM "
            "analytics.monthly_area_production WHERE month='2024-03'"
        ).fetchone() == (-100, -100.0)
        assert db.execute(
            "SELECT mom_change,mom_percent_change FROM "
            "analytics.monthly_area_production WHERE month='2024-04'"
        ).fetchone() == (10, None)
        assert db.execute(
            "SELECT mom_change,yoy_change,yoy_percent_change FROM "
            "analytics.monthly_area_production WHERE month='2025-01'"
        ).fetchone() == (None, 25, 25.0)
        exit_row = db.execute(
            "SELECT volume,previous_volume,mom_change,has_qualifying_row FROM "
            "analytics.operator_monthly_production WHERE month='2024-02' AND "
            "operator_id='0013'"
        ).fetchone()
        assert exit_row == (0, 40, -40, False)
        entry = db.execute(
            "SELECT mom_change,mom_percent_change FROM "
            "analytics.operator_monthly_production WHERE month='2024-02' AND "
            "operator_id='0014'"
        ).fetchone()
        assert entry == (30, None)
        hhi, unknown, top1, top3 = db.execute(
            "SELECT hhi,unknown_share,top_1_share,top_3_share FROM "
            "analytics.operator_concentration WHERE month='2024-02'"
        ).fetchone()
        assert (hhi, unknown, top1, top3) == pytest.approx((3800, 0.2, 0.5, 1))
        assert db.execute(
            "SELECT hhi,unknown_share,top_1_share FROM "
            "analytics.operator_concentration WHERE month='2024-03'"
        ).fetchone() == (None, None, None)
        absent = db.execute(
            "SELECT "
            "current_observed_volume,current_reported_contribution,volume_change,cu"
            "rrent_report_status,decrease_rank FROM analytics.facility_drivers WHER"
            "E month='2024-02' AND facility_id='ABBT0000002'"
        ).fetchone()
        assert absent == (None, 0, -40, "no_qualifying_row", 1)
        assert db.execute(
            "SELECT increase_rank FROM analytics.facility_drivers WHERE "
            "month='2024-02' AND facility_id='ABBT0000003'"
        ).fetchone() == (1,)
        assert db.execute(
            "SELECT count(*) FROM analytics.facility_drivers WHERE month='2025-01'"
        ).fetchone() == (0,)
        assert validate_analytics(db)["passed"]


def test_one_operator_and_deterministic_facility_ties(project: Path) -> None:  # noqa: F811
    source(
        project, "2025-01", [{"Volume": "0"}, {"ReportingFacilityID": "ABBT0000002", "Volume": "0"}]
    )
    source(
        project,
        "2025-02",
        [{"Volume": "10"}, {"ReportingFacilityID": "ABBT0000002", "Volume": "10"}],
    )
    run_pipeline(project, ["2025-01", "2025-02"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        assert db.execute(
            "SELECT hhi,top_1_share FROM analytics.operator_concentration WHERE month='2025-02'"
        ).fetchone() == (10000, 1)
        assert db.execute(
            "SELECT facility_id,increase_rank FROM analytics.facility_drivers ORDER "
            "BY increase_rank"
        ).fetchall() == [("ABBT0000001", 1), ("ABBT0000002", 2)]
        assert db.execute(
            "SELECT DISTINCT previous_report_status,previous_observed_volume FROM "
            "analytics.facility_drivers"
        ).fetchall() == [("reported_zero", 0)]


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE analytics.monthly_area_production SET mom_change=999 WHERE month='2024-02'",
        "DELETE FROM analytics.operator_monthly_production WHERE month='2024-02' "
        "AND operator_id='0013'",
        "UPDATE analytics.operator_concentration SET hhi=0 WHERE month='2024-02'",
        "UPDATE analytics.facility_drivers SET increase_rank=99 WHERE increase_rank=1",
        "DELETE FROM analytics.facility_drivers WHERE month='2024-02' AND "
        "facility_id='ABBT0000002'",
    ],
)
def test_independent_validation_rejects_wrong_analytics(project: Path, mutation: str) -> None:  # noqa: F811
    run_pipeline(project, analytical_months(project), offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute(mutation)
        with pytest.raises(ValueError, match="Analytics validation failed"):
            validate_analytics(db)

"""Signed-bridge examples, exhaustive state pairs, randomized histories and corruption tests."""

import itertools
import random
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from test_pipeline import project, source  # noqa: F401

from gas_intel.pipeline import export_tables, run_pipeline
from gas_intel.validation.bridge import validate_bridge


def record(number: int, volume, operator: str = "0012") -> dict:
    return {
        "ReportingFacilityID": f"ABBT{number:07d}",
        "OperatorBAID": operator,
        "ActivityID": "REC" if volume is None else "PROD",
        "Volume": "" if volume is None else str(volume),
    }


def examples(root: Path) -> list[str]:
    source(
        root,
        "2024-01",
        [
            record(1, 100),
            record(2, 100),
            record(3, 100),
            record(4, 100, ""),
            record(5, 100),
            record(6, 50),
        ],
    )
    source(
        root,
        "2024-02",
        [record(1, 120, "0013"), record(2, 0, "0013"), record(4, 120, "0013"), record(5, 0)],
    )
    source(root, "2024-03", [record(5, 120, "0013"), record(6, 75), record(7, 20)])
    return ["2024-01", "2024-02", "2024-03"]


def test_required_signed_examples_and_observed_history(project: Path) -> None:  # noqa: F811
    run_pipeline(project, examples(project), offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:

        def event(facility, component, month="2024-02"):
            return db.execute(
                "SELECT credited_operator_id,volume FROM analytics.bridge_component_events "
                "WHERE facility_id=? AND month=? AND component=?",
                [f"ABBT{facility:07d}", month, component],
            ).fetchone()

        assert event(1, "transfer_out") == ("0012", -100)
        assert event(1, "transfer_in") == ("0013", 100)
        assert event(1, "continuing_change") == ("0013", 20)
        assert event(2, "transfer_out") == ("0012", -100)
        assert event(2, "transfer_in") == ("0013", 100)
        assert event(2, "to_reported_zero") == ("0013", -100)
        assert event(3, "attribution_out") == ("0012", -100)
        assert event(3, "attribution_in") == ("UNKNOWN", 100)
        assert event(3, "absent_production_row") == ("UNKNOWN", -100)
        assert event(4, "attribution_out") == ("UNKNOWN", -100)
        assert event(4, "attribution_in") == ("0013", 100)
        assert event(4, "continuing_change") == ("0013", 20)
        assert event(5, "transfer_out", "2024-03") == ("0012", 0)
        assert event(5, "transfer_in", "2024-03") == ("0013", 0)
        assert event(5, "returning_positive", "2024-03") == ("0013", 120)
        rows = db.execute(
            "SELECT facility_id,state_category,returning_from,left_censored "
            "FROM analytics.facility_bridge_monthly WHERE month='2024-03' "
            "AND facility_id IN ('ABBT0000005','ABBT0000006','ABBT0000007') "
            "ORDER BY facility_id"
        ).fetchall()
        assert rows == [
            ("ABBT0000005", "returning_positive", "reported_zero", False),
            ("ABBT0000006", "returning_positive", "no_qualifying_row", False),
            ("ABBT0000007", "first_observed_positive", None, True),
        ]
        assert validate_bridge(db)["multi_month_ranges_checked"] == 3
        assert (
            db.execute(
                "SELECT max(abs(reconciliation_difference)) FROM analytics.operator_bridge_monthly"
            ).fetchone()[0]
            == 0
        )


def test_every_state_pair_and_known_unknown_operator_pair(project: Path) -> None:  # noqa: F811
    first, second = [], []
    pairs = list(
        itertools.product(
            [100, 0, None],
            [120, 0, None],
            [("0012", "0012"), ("0012", "0013"), ("0012", ""), ("", "0013"), ("", "")],
        )
    )
    for number, (p, c, (a, b)) in enumerate(pairs, 1):
        first.append(record(number, p, a))
        second.append(record(number, c, b))
    source(project, "2025-01", first)
    source(project, "2025-02", second)
    run_pipeline(project, ["2025-01", "2025-02"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        report = validate_bridge(db)
        assert report["facility_transitions"] == 45
        assert report["area_months"] == 1
        assert db.execute(
            "SELECT transfer_in+transfer_out,attribution_in+attribution_out "
            "FROM analytics.area_bridge_monthly"
        ).fetchone() == (0, 0)


def test_deterministic_randomized_histories_reconcile_exactly(project: Path) -> None:  # noqa: F811
    rng = random.Random(20261023)
    months = [f"2024-{month:02d}" for month in range(1, 7)]
    for month in months:
        rows = []
        for facility in range(1, 61):
            volume = rng.choice([None, 0, Decimal(rng.randrange(1, 200000)) / 1000])
            rows.append(record(facility, volume, rng.choice(["0012", "0013", "0014", ""])))
        source(project, month, rows)
    run_pipeline(project, months, offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        report = validate_bridge(db)
        assert report["facility_transitions"] == 300
        assert report["multi_month_ranges_checked"] == 15


def test_gap_never_creates_bridge_or_baseline(project: Path) -> None:  # noqa: F811
    source(project, "2024-01", [record(1, 100)])
    source(project, "2024-03", [record(1, 120, "0013")])
    run_pipeline(project, ["2024-01", "2024-03"], offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        assert validate_bridge(db)["facility_transitions"] == 0
        assert db.execute("SELECT count(*) FROM analytics.area_bridge_monthly").fetchone()[0] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE analytics.bridge_component_events SET credited_operator_id='0013' "
        "WHERE component='transfer_out'",
        "UPDATE analytics.facility_bridge_monthly SET first_observed_positive=999",
        "UPDATE analytics.operator_bridge_monthly SET actual_change=0",
        "UPDATE analytics.area_bridge_monthly SET reconciliation_difference=1",
        "DELETE FROM analytics.bridge_source_lineage WHERE period_role='previous'",
        "DELETE FROM analytics.operator_transfers",
    ],
)
def test_independent_bridge_validator_rejects_corruption(project: Path, mutation: str) -> None:  # noqa: F811
    run_pipeline(project, examples(project), offline=True)
    with duckdb.connect(str(project / "data/warehouse.duckdb")) as db:
        db.execute(mutation)
        with pytest.raises(ValueError, match="(validation|reconciliation) failed"):
            validate_bridge(db)
    # Direct export also rejects modified state without publishing a new bundle.
    previous = (project / "data/exports/latest.json").read_bytes()
    with pytest.raises(ValueError):
        export_tables(project)
    assert (project / "data/exports/latest.json").read_bytes() == previous

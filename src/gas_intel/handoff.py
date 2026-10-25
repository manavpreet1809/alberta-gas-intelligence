"""Build a reproducible portfolio handoff from a hash-verified accepted export bundle."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import duckdb

from gas_intel.pipeline import TABLES, atomic_json
from gas_intel.validation.analytics import offset_month
from gas_intel.validation.bridge import COMPONENTS

KEYS = {
    "dim_month": ["month"],
    "dim_facility": ["facility_id"],
    "dim_operator": ["operator_id"],
    "fact_gas_production": ["facility_id", "month"],
    "facility_month": ["facility_id", "month"],
    "monthly_area_production": ["month"],
    "operator_monthly_production": ["month", "operator_id"],
    "data_quality_summary": ["month", "report_status"],
    "operator_concentration": ["month"],
    "facility_drivers": ["facility_id", "month"],
    "facility_bridge_monthly": ["facility_id", "month"],
    "bridge_component_events": ["facility_id", "month", "component"],
    "operator_bridge_monthly": ["month", "operator_id"],
    "area_bridge_monthly": ["month"],
    "operator_transfers": ["facility_id", "month"],
}


def handoff_report(bundle: Path) -> dict:
    """Verify a bundle and derive three provisional findings with acceptance values."""
    bundle = bundle.resolve()
    payload = (bundle / "manifest.json").read_bytes()
    manifest = json.loads(payload)
    if (
        manifest["validation"].get("passed") is not True
        or manifest["validation"].get("bridge_checks", {}).get("passed") is not True
    ):
        raise ValueError("Handoff requires an accepted bridge validation result")
    expected = {f"{name}.{suffix}" for name in TABLES for suffix in ["csv", "parquet"]}
    if set(manifest["files_sha256"]) != expected:
        raise ValueError("Handoff requires the complete reporting-file inventory")
    for name in sorted(expected):
        path = (bundle / name).resolve()
        if (
            path.parent != bundle
            or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files_sha256"][name]
        ):
            raise ValueError(f"Export hash/path mismatch: {name}")
    with duckdb.connect() as db:
        counts = {}
        for name in TABLES:
            db.execute(
                f"CREATE TABLE {name} AS SELECT * FROM read_parquet(?)",
                [str(bundle / f"{name}.parquet")],
            )
            keys = ",".join(KEYS[name])
            duplicate = db.execute(
                f"SELECT count(*) FROM (SELECT {keys} FROM {name} GROUP BY ALL HAVING count(*)>1)"
            ).fetchone()[0]
            nulls = db.execute(
                f"SELECT count(*) FROM {name} WHERE "
                + " OR ".join(f"{k} IS NULL" for k in KEYS[name])
            ).fetchone()[0]
            if duplicate or nulls:
                raise ValueError(f"Export key validation failed: {name}")
            counts[name] = db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        dimensions = {
            "facility_id": ("dim_facility", "facility_id"),
            "operator_id": ("dim_operator", "operator_id"),
            "credited_operator_id": ("dim_operator", "operator_id"),
            "previous_operator_id": ("dim_operator", "operator_id"),
            "current_operator_id": ("dim_operator", "operator_id"),
        }
        for table in TABLES:
            types = {row[0]: row[1] for row in db.execute(f"DESCRIBE {table}").fetchall()}
            for column in KEYS[table]:
                if types[column] != "VARCHAR":
                    raise ValueError(f"Export key must remain text: {table}.{column}")
            if table.startswith("dim_"):
                continue
            for column in types.keys() & dimensions.keys():
                if types[column] != "VARCHAR":
                    raise ValueError(f"Export key must remain text: {table}.{column}")
                dimension, key = dimensions[column]
                missing = db.execute(
                    f"SELECT count(*) FROM {table} f LEFT JOIN {dimension} d "
                    f"ON f.{column}=d.{key} WHERE d.{key} IS NULL"
                ).fetchone()[0]
                if missing:
                    raise ValueError(f"Export dimension relationship failed: {table}.{column}")
        months = [r[0] for r in db.execute("SELECT month FROM dim_month ORDER BY month").fetchall()]
        if (
            len(months) != 24
            or any(offset_month(a, 1) != b for a, b in zip(months, months[1:]))
            or months != manifest["run"]["analysis_months"]
        ):
            raise ValueError("Portfolio handoff requires all 24 contiguous analysis months")
        for name in TABLES:
            if name.startswith("dim_"):
                continue
            if db.execute(
                f"SELECT count(*) FROM {name} WHERE month NOT IN (SELECT month FROM dim_month)"
            ).fetchone()[0]:
                raise ValueError(f"Non-analysis month in export: {name}")
        for name in ["operator_bridge_monthly", "area_bridge_monthly"]:
            if db.execute(
                f"SELECT count(*) FROM {name} WHERE reconciliation_difference IS DISTINCT FROM 0"
            ).fetchone()[0]:
                raise ValueError("Published bridge reconciliation failed")
        for table in ["fact_gas_production", "operator_monthly_production"]:
            errors = db.execute(f"""
                WITH totals AS (SELECT month,sum(volume) volume FROM {table} GROUP BY month)
                SELECT count(*) FROM monthly_area_production a LEFT JOIN totals t USING(month)
                WHERE a.volume IS DISTINCT FROM coalesce(t.volume,0)
            """).fetchone()[0]
            if errors:
                raise ValueError(f"Exported production reconciliation failed: {table}")
        start, end = months[0], months[-1]
        first = db.execute(
            "SELECT volume FROM monthly_area_production WHERE month=?", [start]
        ).fetchone()[0]
        last = db.execute(
            "SELECT volume FROM monthly_area_production WHERE month=?", [end]
        ).fetchone()[0]
        delta = last - first
        columns = ",".join(f"coalesce(sum({name}),0) AS {name}" for name in COMPONENTS)
        area_values = db.execute(
            f"SELECT {columns} FROM area_bridge_monthly WHERE month>? AND month<=?", [start, end]
        ).fetchone()
        area_components = dict(zip(COMPONENTS, area_values, strict=True))
        if sum(area_values, Decimal(0)) != delta:
            raise ValueError("Selected-period area waterfall does not equal end minus start")
        operator = db.execute(
            """WITH start AS (SELECT operator_id,volume FROM operator_monthly_production
                           WHERE month=?),
            finish AS (SELECT operator_id,volume FROM operator_monthly_production WHERE month=?)
            SELECT coalesce(s.operator_id,f.operator_id) AS operator_id,
                   coalesce(s.volume,0) AS start_volume,coalesce(f.volume,0) AS end_volume,
                   coalesce(f.volume,0)-coalesce(s.volume,0) AS change
            FROM start s FULL JOIN finish f USING(operator_id)
            ORDER BY abs(change) DESC,operator_id LIMIT 1""",
            [start, end],
        ).fetchone()
        op_id, p, c, change = operator
        name = db.execute(
            "SELECT operator_name FROM dim_operator WHERE operator_id=?", [op_id]
        ).fetchone()[0]
        op_values = db.execute(
            f"SELECT {columns} FROM operator_bridge_monthly "
            "WHERE operator_id=? AND month>? AND month<=?",
            [op_id, start, end],
        ).fetchone()
        if sum(op_values, Decimal(0)) != change:
            raise ValueError("Selected-period operator waterfall does not reconcile")
        concentration = db.execute(
            "SELECT month,top_3_share,hhi,unknown_share FROM operator_concentration "
            "WHERE month IN (?,?) ORDER BY month",
            [start, end],
        ).fetchall()
        if len(concentration) != 2:
            raise ValueError("Concentration endpoints unavailable")
        findings = [
            {
                "id": "area_endpoints",
                "start_month": start,
                "end_month": end,
                "unit": "e3m3",
                "start_volume": str(first),
                "end_volume": str(last),
                "change": str(delta),
                "percent_change": str(100 * delta / first) if first else None,
                "bridge_components": {k: str(v) for k, v in area_components.items()},
            },
            {
                "id": "largest_operator_endpoint_change",
                "operator_id": op_id,
                "operator_name": name,
                "start_volume": str(p),
                "end_volume": str(c),
                "change": str(change),
                "unit": "e3m3",
                "bridge_components": dict(zip(COMPONENTS, map(str, op_values), strict=True)),
            },
            {
                "id": "concentration_endpoints",
                "start_top_3_share": concentration[0][1],
                "end_top_3_share": concentration[1][1],
                "start_hhi": concentration[0][2],
                "end_hhi": concentration[1][2],
                "start_unknown_share": concentration[0][3],
                "end_unknown_share": concentration[1][3],
            },
        ]
        quality = dict(
            db.execute(
                "SELECT report_status,count(*) FROM facility_month GROUP BY report_status"
            ).fetchall()
        )
    return {
        "handoff_format_version": 1,
        "handoff_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": "provisional portfolio handoff; Power BI and scope approval pending",
        "export_id": manifest["export_id"],
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "configuration_hash": manifest["run"]["configuration_hash"],
        "model_hash": manifest["run"]["model_hash"],
        "scope_status": manifest["run"]["scope_status"],
        "human_scope_approval_recorded": manifest["run"]["human_scope_approval_recorded"],
        "files_verified": len(expected),
        "table_rows": counts,
        "reporting_states": quality,
        "start_month": start,
        "end_month": end,
        "findings": findings,
        "source_sha256_by_month": manifest["validation"]["source_sha256_by_month"],
        "dashboard_created": False,
        "dax_executed": False,
    }


def main() -> None:
    """Verify one accepted bundle and write a reproducible handoff evidence report."""
    import argparse

    import typer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(args.bundle.resolve()) or "raw" in output.parts:
        parser.error("Handoff output must be outside accepted bundles and raw storage")
    report = handoff_report(args.bundle)
    atomic_json(output, report)
    typer.echo(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

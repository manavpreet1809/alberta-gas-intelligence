"""Independently recompute analytical measures from core facts using Decimal arithmetic."""

import math
from collections import defaultdict
from decimal import Decimal

import duckdb


def offset_month(month: str, offset: int) -> str:
    """Return an exact calendar month offset rather than a previous available row."""
    year, number = map(int, month.split("-"))
    value = year * 12 + number - 1 + offset
    return f"{value // 12:04d}-{value % 12 + 1:02d}"


def indexed_rows(db: duckdb.DuckDBPyConnection, table: str, keys: list[str]) -> dict:
    """Read a small analytical table and reject duplicate keys."""
    cursor = db.execute(f"SELECT * FROM {table}")
    names = [column[0] for column in cursor.description]
    result = {}
    for values in cursor.fetchall():
        row = dict(zip(names, values, strict=True))
        key = tuple(row[name] for name in keys)
        if key in result:
            raise ValueError(f"Analytics validation failed: duplicate {table} key")
        result[key] = row
    return result


def require_values(row: dict, expected: dict, label: str) -> None:
    """Compare exact volumes and nullable values; allow only numerical display tolerance."""
    for name, value in expected.items():
        actual = row.get(name)
        if isinstance(value, float):
            equal = actual is not None and math.isclose(
                float(actual), value, rel_tol=1e-12, abs_tol=1e-8
            )
        else:
            equal = actual == value
        if not equal:
            raise ValueError(f"Analytics validation failed: {label}.{name}")


def percent(change: Decimal, baseline: Decimal | None) -> float | None:
    """Return percentage points, leaving unavailable and zero baselines undefined."""
    return float(100 * change / baseline) if baseline else None


def validate_analytics(db: duckdb.DuckDBPyConnection) -> dict:
    """Recompute calendar changes, operator entries/exits, concentration and driver ranks."""
    months = {row[0] for row in db.execute("SELECT month FROM core.dim_month").fetchall()}
    analysis = {
        row[0]
        for row in db.execute("SELECT month FROM core.dim_month WHERE is_analysis").fetchall()
    }
    spine = indexed_rows(db, "core.facility_month", ["facility_id", "month"])
    totals = {month: Decimal(0) for month in months}
    operators = defaultdict(dict)
    for (_, month), row in spine.items():
        totals[month] += row["volume"] or Decimal(0)
    for month, operator, volume in db.execute(
        "SELECT month,operator_id,volume FROM core.fact_gas_production"
    ).fetchall():
        operators[month][operator] = operators[month].get(operator, Decimal(0)) + volume
    area = indexed_rows(db, "analytics.monthly_area_production", ["month"])
    if set(area) != {(month,) for month in analysis}:
        raise ValueError("Analytics validation failed: area month coverage")
    expected_operators = {}
    for month in analysis:
        previous, year = offset_month(month, -1), offset_month(month, -12)
        prior = totals.get(previous)
        yoy_prior = totals.get(year)
        change = totals[month] - prior if prior is not None else None
        yoy_change = totals[month] - yoy_prior if yoy_prior is not None else None
        require_values(
            area[(month,)],
            {
                "volume": totals[month],
                "previous_month": previous if previous in months else None,
                "previous_volume": prior,
                "mom_change": change,
                "mom_percent_change": percent(change, prior) if change is not None else None,
                "prior_year_month": year if year in months else None,
                "prior_year_volume": yoy_prior,
                "yoy_change": yoy_change,
                "yoy_percent_change": percent(yoy_change, yoy_prior)
                if yoy_change is not None
                else None,
            },
            "area",
        )
        for operator in operators[month].keys() | operators[previous].keys():
            current = operators[month].get(operator, Decimal(0))
            previous_volume = (
                operators[previous].get(operator, Decimal(0)) if previous in months else None
            )
            delta = current - previous_volume if previous_volume is not None else None
            expected_operators[(month, operator)] = {
                "volume": current,
                "area_share": float(current / totals[month]) if totals[month] else None,
                "has_qualifying_row": operator in operators[month],
                "previous_month": previous if previous in months else None,
                "previous_volume": previous_volume,
                "mom_change": delta,
                "mom_percent_change": percent(delta, previous_volume)
                if delta is not None
                else None,
            }
    actual_operators = indexed_rows(
        db, "analytics.operator_monthly_production", ["month", "operator_id"]
    )
    if actual_operators.keys() != expected_operators.keys():
        raise ValueError("Analytics validation failed: operator entry/exit coverage")
    for key, expected in expected_operators.items():
        require_values(actual_operators[key], expected, "operator")
    concentration = indexed_rows(db, "analytics.operator_concentration", ["month"])
    if concentration.keys() != area.keys():
        raise ValueError("Analytics validation failed: concentration month coverage")
    for month in analysis:
        ranked = sorted(operators[month].items(), key=lambda pair: (-pair[1], pair[0]))
        total = totals[month]
        values = {"area_volume": total, "positive_operator_count": sum(v > 0 for _, v in ranked)}
        for count in [1, 3, 5]:
            values[f"top_{count}_share"] = (
                float(sum((v for _, v in ranked[:count]), Decimal(0)) / total) if total else None
            )
        values["unknown_share"] = (
            float(operators[month].get("UNKNOWN", Decimal(0)) / total) if total else None
        )
        values["hhi"] = (
            float(sum(((100 * v / total) ** 2 for _, v in ranked), Decimal(0))) if total else None
        )
        require_values(concentration[(month,)], values, "concentration")
    drivers = indexed_rows(db, "analytics.facility_drivers", ["facility_id", "month"])
    expected_drivers = {}
    for (facility, month), current in spine.items():
        previous = offset_month(month, -1)
        prior = spine.get((facility, previous))
        if month not in analysis or prior is None:
            continue
        p, c = prior["volume"] or Decimal(0), current["volume"] or Decimal(0)
        expected_drivers[(facility, month)] = {
            "previous_month": previous,
            "previous_operator_id": prior["operator_id"],
            "current_operator_id": current["operator_id"],
            "previous_report_status": prior["report_status"],
            "current_report_status": current["report_status"],
            "previous_observed_volume": prior["volume"],
            "current_observed_volume": current["volume"],
            "previous_reported_contribution": p,
            "current_reported_contribution": c,
            "volume_change": c - p,
            "increase_rank": None,
            "decrease_rank": None,
        }
    if drivers.keys() != expected_drivers.keys():
        raise ValueError("Analytics validation failed: facility transition coverage")
    for month in analysis:
        for sign, field in [(1, "increase_rank"), (-1, "decrease_rank")]:
            ranked = sorted(
                (
                    key
                    for key, row in expected_drivers.items()
                    if key[1] == month and sign * row["volume_change"] > 0
                ),
                key=lambda key: (-sign * expected_drivers[key]["volume_change"], key[0]),
            )
            for rank, key in enumerate(ranked, 1):
                expected_drivers[key][field] = rank
        if offset_month(month, -1) in months:
            delta = sum(
                (r["volume_change"] for (f, m), r in expected_drivers.items() if m == month),
                Decimal(0),
            )
            if delta != totals[month] - totals[offset_month(month, -1)]:
                raise ValueError("Analytics validation failed: facility drivers do not reconcile")
    for key, row in expected_drivers.items():
        require_values(drivers[key], row, "facility_driver")
    return {
        "passed": True,
        "area_months": len(area),
        "operator_months": len(actual_operators),
        "concentration_months": len(concentration),
        "facility_transitions": len(drivers),
    }

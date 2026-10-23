"""Recompute the signed bridge independently from core reporting states and facts."""

from collections import defaultdict
from decimal import Decimal

import duckdb

from gas_intel.validation.analytics import indexed_rows, offset_month, require_values

COMPONENTS = (
    "continuing_change",
    "transfer_in",
    "transfer_out",
    "attribution_in",
    "attribution_out",
    "first_observed_positive",
    "returning_positive",
    "to_reported_zero",
    "absent_production_row",
)
ZERO = Decimal(0)


def validate_bridge(db: duckdb.DuckDBPyConnection) -> dict:
    """Prove component allocation, lineage, monthly identities and contiguous period identities."""
    spine = indexed_rows(db, "core.facility_month", ["facility_id", "month"])
    months = sorted({month for _, month in spine})
    analysis = {
        m for (m,) in db.execute("SELECT month FROM core.dim_month WHERE is_analysis").fetchall()
    }
    bridges = indexed_rows(db, "analytics.facility_bridge_monthly", ["facility_id", "month"])
    events = indexed_rows(
        db, "analytics.bridge_component_events", ["facility_id", "month", "component"]
    )
    expected_bridges, expected_events = {}, {}
    prior_positive = {}
    for (facility, month), current in sorted(spine.items()):
        previous = offset_month(month, -1)
        prior = spine.get((facility, previous))
        last_positive = prior_positive.get(facility)
        if prior is not None and month in analysis:
            p, c = prior["volume"] or ZERO, current["volume"] or ZERO
            a, b = prior["operator_id"], current["operator_id"]
            reallocation = (
                "none"
                if a == b
                else "attribution_change"
                if "UNKNOWN" in (a, b)
                else "reported_operator_reassignment"
            )
            category = None
            if p > 0:
                category = (
                    "continuing_change"
                    if c > 0
                    else "to_reported_zero"
                    if current["report_status"] == "reported_zero"
                    else "absent_production_row"
                )
            elif c > 0:
                category = "returning_positive" if last_positive else "first_observed_positive"
            components = dict.fromkeys(COMPONENTS, ZERO)
            if category:
                components[category] = c - p
                expected_events[(facility, month, category)] = (b, c - p)
            if a != b:
                prefix = "attribution" if "UNKNOWN" in (a, b) else "transfer"
                components[prefix + "_out"], components[prefix + "_in"] = -p, p
                expected_events[(facility, month, prefix + "_out")] = (a, -p)
                expected_events[(facility, month, prefix + "_in")] = (b, p)
            expected_bridges[(facility, month)] = {
                **components,
                "facility_id": facility,
                "month": month,
                "previous_month": previous,
                "previous_operator_id": a,
                "current_operator_id": b,
                "previous_report_status": prior["report_status"],
                "current_report_status": current["report_status"],
                "previous_observed_volume": prior["volume"],
                "current_observed_volume": current["volume"],
                "previous_reported_contribution": p,
                "current_reported_contribution": c,
                "volume_change": c - p,
                "history_start": months[0],
                "prior_positive_month": last_positive,
                "left_censored": last_positive is None,
                "previous_source_rows": prior["facility_source_rows"],
                "current_source_rows": current["facility_source_rows"],
                "reallocation_type": reallocation,
                "state_category": category,
                "returning_from": prior["report_status"]
                if category == "returning_positive"
                else None,
                "unit": "e3m3",
            }
            # Independent per-facility operator-vector identity, not just area netting.
            vector = defaultdict(lambda: ZERO)
            vector[a] -= p
            vector[b] += c
            credited = defaultdict(lambda: ZERO)
            for component in COMPONENTS:
                operator = a if component.endswith("_out") else b
                credited[operator] += components[component]
            if any(vector[k] != credited[k] for k in vector.keys() | credited.keys()):
                raise ValueError("Bridge reconciliation failed: facility operator vector")
        if (current["volume"] or ZERO) > 0:
            prior_positive[facility] = month
    if bridges.keys() != expected_bridges.keys() or events.keys() != expected_events.keys():
        raise ValueError("Bridge reconciliation failed: facility/event coverage")
    for key, expected in expected_bridges.items():
        require_values(bridges[key], expected, "facility_bridge")
    grouped = defaultdict(lambda: dict.fromkeys(COMPONENTS, ZERO))
    for key, (operator, volume) in expected_events.items():
        facility, month, component = key
        require_values(
            events[key],
            {
                "credited_operator_id": operator,
                "volume": volume,
                "previous_month": offset_month(month, -1),
                "unit": "e3m3",
            },
            "bridge_event",
        )
        grouped[(month, operator)][component] += volume
    levels = defaultdict(dict)
    for month, operator, volume in db.execute(
        "SELECT month,operator_id,volume FROM core.fact_gas_production"
    ).fetchall():
        levels[month][operator] = levels[month].get(operator, ZERO) + volume
    comparable = {m for m in analysis if offset_month(m, -1) in months}
    expected_keys = set(grouped)
    for month in comparable:
        expected_keys.update(
            (month, op) for op in levels[month].keys() | levels[offset_month(month, -1)].keys()
        )
    operator_rows = indexed_rows(db, "analytics.operator_bridge_monthly", ["month", "operator_id"])
    if operator_rows.keys() != expected_keys:
        raise ValueError("Bridge reconciliation failed: operator coverage")
    for month, operator in expected_keys:
        comp = grouped[(month, operator)]
        actual = levels[month].get(operator, ZERO) - levels[offset_month(month, -1)].get(
            operator, ZERO
        )
        calculated = sum(comp.values(), ZERO)
        if calculated != actual:
            raise ValueError("Bridge reconciliation failed: independent operator delta")
        require_values(
            operator_rows[(month, operator)],
            {
                **comp,
                "actual_change": actual,
                "calculated_change": calculated,
                "reconciliation_difference": ZERO,
                "previous_month": offset_month(month, -1),
                "unit": "e3m3",
            },
            "operator_bridge",
        )
    area = indexed_rows(db, "analytics.area_bridge_monthly", ["month"])
    if area.keys() != {(m,) for m in comparable}:
        raise ValueError("Bridge reconciliation failed: area coverage")
    for month in comparable:
        comp = {
            c: sum((values[c] for (m, o), values in grouped.items() if m == month), ZERO)
            for c in COMPONENTS
        }
        actual = sum(levels[month].values(), ZERO) - sum(
            levels[offset_month(month, -1)].values(), ZERO
        )
        if (
            comp["transfer_in"] + comp["transfer_out"] != 0
            or comp["attribution_in"] + comp["attribution_out"] != 0
            or sum(comp.values(), ZERO) != actual
        ):
            raise ValueError("Bridge reconciliation failed: area allocation")
        require_values(
            area[(month,)],
            {
                **comp,
                "actual_change": actual,
                "calculated_change": actual,
                "reconciliation_difference": ZERO,
                "previous_month": offset_month(month, -1),
                "unit": "e3m3",
            },
            "area_bridge",
        )
    transfers = indexed_rows(db, "analytics.operator_transfers", ["facility_id", "month"])
    expected_transfers = {
        key: row for key, row in expected_bridges.items() if row["reallocation_type"] != "none"
    }
    if transfers.keys() != expected_transfers.keys():
        raise ValueError("Bridge reconciliation failed: operator-change event coverage")
    for key, row in expected_transfers.items():
        require_values(transfers[key], {k: row[k] for k in transfers[key]}, "operator_change")
    ranges = 0
    for start_index, start in enumerate(months):
        cumulative = defaultdict(lambda: ZERO)
        for end in months[start_index + 1 :]:
            if end not in comparable or offset_month(end, -1) != months[months.index(end) - 1]:
                break
            for (month, operator), comp in grouped.items():
                if month == end:
                    cumulative[operator] += sum(comp.values(), ZERO)
            for operator in cumulative.keys() | levels[start].keys() | levels[end].keys():
                if cumulative[operator] != levels[end].get(operator, ZERO) - levels[start].get(
                    operator, ZERO
                ):
                    raise ValueError("Bridge reconciliation failed: multi-month end-minus-start")
            ranges += 1
    expected_lineage = sum(
        r["previous_source_rows"] + r["current_source_rows"] for r in expected_bridges.values()
    )
    count = db.execute("SELECT count(*) FROM analytics.bridge_source_lineage").fetchone()[0]
    duplicates = db.execute("""SELECT count(*) FROM (SELECT facility_id,month,period_role,
        source_sha256,source_row_number FROM analytics.bridge_source_lineage
        GROUP BY ALL HAVING count(*)>1)""").fetchone()[0]
    invalid = db.execute("""SELECT count(*) FROM analytics.bridge_source_lineage l
        LEFT JOIN analytics.facility_bridge_monthly b USING(facility_id,month)
        LEFT JOIN staging.volumetrics s ON s.source_sha256=l.source_sha256
          AND s.source_row_number=l.source_row_number
        WHERE b.facility_id IS NULL OR s.ReportingFacilityID IS DISTINCT FROM l.facility_id
          OR s.ProductionMonth IS DISTINCT FROM
             CASE WHEN l.period_role='current' THEN l.month ELSE b.previous_month END
          OR l.period_role NOT IN ('current','previous')
          OR s.source_file IS DISTINCT FROM l.source_file
          OR s.ingestion_run_id IS DISTINCT FROM l.ingestion_run_id
          OR s.downloaded_at IS DISTINCT FROM l.downloaded_at""").fetchone()[0]
    if count != expected_lineage or duplicates or invalid:
        raise ValueError("Bridge reconciliation failed: source lineage")
    return {
        "passed": True,
        "facility_transitions": len(bridges),
        "component_events": len(events),
        "operator_months": len(operator_rows),
        "area_months": len(area),
        "operator_change_events": len(transfers),
        "multi_month_ranges_checked": ranges,
        "source_lineage_rows": count,
    }

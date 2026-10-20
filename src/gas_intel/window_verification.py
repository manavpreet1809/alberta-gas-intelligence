"""Audit a candidate reporting window without approving scope or building a warehouse."""

import hashlib
import json
import tempfile
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

from gas_intel.geography import DLSBox
from gas_intel.history_profiling import month_number
from gas_intel.ingestion.parsers import csv_records, read_csv_payload


def month_sequence(start: str, end: str) -> list[str]:
    """Return an explicit inclusive month sequence; never select dynamic latest data."""
    first, last = month_number(start), month_number(end)
    if first > last:
        raise ValueError("Reporting window is reversed")
    if last - first > 120:
        raise ValueError("Verification window exceeds ten years")
    return [f"{number // 12:04d}-{number % 12 + 1:02d}" for number in range(first, last + 1)]


def verify_window(
    root: Path,
    start: str,
    end: str,
    box: DLSBox,
    *,
    include_members: bool = False,
    tracked_facilities: set[str] | None = None,
) -> dict[str, object]:
    """Independently check pinned monthly inventory, exact totals and cohort-location stability."""
    summaries = []
    contract = yaml.safe_load((root / "config/sources.yaml").read_text())["volumetrics"]
    invalid_locations: set[str] = set()
    locations: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
    cohort: set[str] = set()
    qualifying_cohort: set[str] = set()
    fields = "ReportingFacilityID, FacilityTownship, FacilityRange, FacilityMeridian"
    for month in month_sequence(start, end):
        inventory = json.loads((root / "data/verification" / f"{month}.json").read_text())
        event, profile = inventory["event"], inventory["profile"]
        path = root / event["source_file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != event["sha256"] or digest != profile["source_sha256"]:
            raise ValueError(f"Source hash mismatch for {month}")
        payload, lineage = read_csv_payload(path)
        csv_records(payload, set(contract["expected_headers"]), contract["expected_headers"])
        if hashlib.sha256(payload).hexdigest() != profile["payload_sha256"]:
            raise ValueError(f"Payload hash mismatch for {month}")
        with tempfile.TemporaryDirectory(prefix="gas-window-") as temporary:
            csv_path = Path(temporary) / "source.csv"
            csv_path.write_bytes(payload)
            with duckdb.connect() as db:
                db.execute(
                    "CREATE TABLE source AS SELECT * FROM "
                    "read_csv(?, all_varchar=true, header=true)",
                    [str(csv_path)],
                )
                source_rows, wrong_months = db.execute(
                    "SELECT count(*), count(*) FILTER "
                    "(WHERE ProductionMonth IS DISTINCT FROM ?) FROM source",
                    [month],
                ).fetchone()
                if wrong_months or source_rows != profile["row_count"]:
                    raise ValueError(f"Row count or period mismatch for {month}")
                qualifiers = "ActivityID='PROD' AND ProductID='GAS'"
                rows, volume = db.execute(
                    "SELECT count(*), sum(try_cast(Volume AS DECIMAL(18,3))) "
                    f"FROM source WHERE {qualifiers}"
                ).fetchone()
                gas = profile["gas_prod"]
                volume = volume or Decimal(0)
                if rows != gas["row_count"] or volume != Decimal(gas["finite_volume_sum_e3m3"]):
                    raise ValueError(f"Independent production totals differ for {month}")
                scope_sql = (
                    "regexp_full_match(FacilityTownship, '[0-9]+') AND "
                    "regexp_full_match(FacilityRange, '[0-9]+') AND "
                    "regexp_full_match(FacilityMeridian, '[0-9]+') AND "
                    "try_cast(FacilityTownship AS INTEGER) BETWEEN ? AND ? AND "
                    "try_cast(FacilityRange AS INTEGER) BETWEEN ? AND ? AND "
                    "try_cast(FacilityMeridian AS INTEGER)=?"
                )
                bounds = [
                    box.township_min,
                    box.township_max,
                    box.range_min,
                    box.range_max,
                    box.meridian,
                ]
                selected = db.execute(
                    f"SELECT DISTINCT {fields} FROM source WHERE {scope_sql}", bounds
                ).fetchall()
                qualified = db.execute(
                    "SELECT DISTINCT ReportingFacilityID FROM source "
                    f"WHERE {scope_sql} AND {qualifiers}",
                    bounds,
                ).fetchall()
                for facility, township, range_, meridian in selected:
                    cohort.add(facility)
                qualifying_cohort.update(facility for (facility,) in qualified)
                # Retain all locations so a facility entering the candidate box later
                # still has earlier outside-box locations checked for stability.
                observed = db.execute(f"SELECT DISTINCT {fields} FROM source").fetchall()
                for facility, township, range_, meridian in observed:
                    try:
                        position = (int(township), int(range_), int(meridian))
                    except (TypeError, ValueError):
                        invalid_locations.add(facility)
                    else:
                        locations[facility].add(position)
                candidate_rows, candidate_volume = db.execute(
                    "SELECT count(*), sum(try_cast(Volume AS DECIMAL(18,3))) "
                    f"FROM source WHERE {scope_sql} AND {qualifiers}",
                    bounds,
                ).fetchone()
                tracked_rows = tracked_volume = None
                if tracked_facilities is not None:
                    tracked_rows, tracked_volume = db.execute(
                        "SELECT count(*), coalesce(sum(try_cast(Volume AS DECIMAL(18,3))),0) "
                        f"FROM source WHERE {qualifiers} AND ReportingFacilityID IN "
                        "(SELECT unnest(?))",
                        [sorted(tracked_facilities)],
                    ).fetchone()
                operators = db.execute(
                    "SELECT count(DISTINCT coalesce(nullif(OperatorBAID, ''), 'UNKNOWN')) "
                    f"FROM source WHERE {scope_sql} AND {qualifiers}",
                    bounds,
                ).fetchone()[0]
        summaries.append(
            {
                "period": month,
                "source_sha256": digest,
                "payload_sha256": profile["payload_sha256"],
                "downloaded_at": event["downloaded_at"],
                "source_rows": source_rows,
                "gas_prod_rows": rows,
                "source_volume_e3m3": str(volume),
                "candidate_facilities_with_rows": len({row[0] for row in selected}),
                "candidate_qualifying_facilities": len(qualified),
                "candidate_operators": operators,
                "tracked_gas_prod_rows": tracked_rows,
                "tracked_volume_e3m3": str(tracked_volume) if tracked_volume is not None else None,
                "candidate_gas_prod_rows": candidate_rows,
                "candidate_volume_e3m3": str(candidate_volume or Decimal(0)),
                "unresolved_volume_facilities": gas["unresolved_volume_facility_count"],
                "missing_operator_facilities": gas["missing_operator_facility_count"],
                "conflicting_operator_facilities": gas["conflicting_operator_facility_count"],
                "source_url": event["url"],
                "candidate_key_duplicate_extra_rows": gas["candidate_key_duplicate_extra_rows"],
                "archive_layers": len(lineage),
            }
        )
    report = {
        "status": "candidate-window evidence only; human scope confirmation pending",
        "box": asdict(box),
        "start_month": start,
        "end_month": end,
        "month_count": len(summaries),
        "monthly_checks": summaries,
        "candidate_cohort_facility_count": len(cohort),
        "candidate_qualifying_facility_union_count": len(qualifying_cohort),
        "candidate_location_conflict_facility_count": sum(
            len(locations[facility]) > 1 for facility in cohort
        ),
        "candidate_unresolved_location_facilities": len(cohort & invalid_locations),
        "candidate_cohort_set_sha256": hashlib.sha256(
            "\n".join(sorted(cohort)).encode()
        ).hexdigest(),
        "source_contract_sha256": hashlib.sha256(
            (root / "config/sources.yaml").read_bytes()
        ).hexdigest(),
    }

    if include_members:
        report["candidate_facility_ids"] = sorted(cohort)
        report["location_evidence"] = [
            {
                "facility_id": facility,
                "positions": sorted(locations[facility]),
                "has_unresolved_location": facility in invalid_locations,
            }
            for facility in sorted(cohort | (tracked_facilities or set()))
        ]
    return report


def main() -> None:
    """Recheck the configured candidate window using local verification inventory."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load((args.root / "config/study_area.yaml").read_text())[
        "candidate_proposal"
    ]
    box = DLSBox(
        **{
            key: config[key]
            for key in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        }
    )
    report = verify_window(args.root, config["start_month"], config["end_month"], box)
    if month_number(config["start_month"]) - month_number(config["context_start_month"]) != 1:
        raise ValueError("Comparison context must immediately precede the analysis window")
    report["comparison_context"] = verify_window(
        args.root, config["context_start_month"], config["context_start_month"], box
    )["monthly_checks"][0]
    report["scope_approved"] = config.get("approved") is True
    output = args.output.resolve()
    if "raw" in output.parts:
        parser.error("Evidence output must be outside immutable raw storage")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

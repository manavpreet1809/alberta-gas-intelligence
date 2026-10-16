"""Cross-check monthly source coverage and operator attribution without causal labels."""

import csv
import hashlib
import io
from collections import Counter, defaultdict
from pathlib import Path

from gas_intel.history_profiling import assignment_candidates, history_intervals, month_number
from gas_intel.ingestion.parsers import read_csv_payload


def monthly_metadata(path: Path, month: str) -> dict[str, dict[str, set]]:
    """Collect presence and distinct metadata independently of volume totals."""
    payload, _ = read_csv_payload(path)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    required = {
        "ProductionMonth",
        "ReportingFacilityID",
        "OperatorBAID",
        "ActivityID",
        "ProductID",
        "FacilityTownship",
        "FacilityRange",
        "FacilityMeridian",
    }
    headers = reader.fieldnames or []
    if len(set(headers)) != len(headers) or not required.issubset(headers):
        raise ValueError("Missing or duplicate monthly metadata headers")
    facilities = defaultdict(lambda: {"operators": set(), "locations": set(), "qualifies": set()})
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed monthly metadata row")
        if row["ProductionMonth"] != month or not row["ReportingFacilityID"]:
            raise ValueError("Unexpected month or blank facility in monthly metadata")
        facility = facilities[row["ReportingFacilityID"]]
        facility["operators"].add(row["OperatorBAID"] or "UNKNOWN")
        facility["locations"].add(
            tuple(row[field] for field in ["FacilityTownship", "FacilityRange", "FacilityMeridian"])
        )
        if row["ActivityID"] == "PROD" and row["ProductID"] == "GAS":
            facility["qualifies"].add(True)
    return dict(facilities)


def compare_months(previous: Path, current: Path, previous_month: str, current_month: str) -> dict:
    """Describe observed set transitions; never label them physical starts or closures."""
    if month_number(current_month) != month_number(previous_month) + 1:
        raise ValueError("Continuity comparison requires consecutive months")
    before, after = (
        monthly_metadata(previous, previous_month),
        monthly_metadata(current, current_month),
    )
    p = {key for key, value in before.items() if value["qualifies"]}
    c = {key for key, value in after.items() if value["qualifies"]}
    common = before.keys() & after.keys()
    return {
        "previous_month": previous_month,
        "current_month": current_month,
        "source_sha256_previous": hashlib.sha256(previous.read_bytes()).hexdigest(),
        "source_sha256_current": hashlib.sha256(current.read_bytes()).hexdigest(),
        "qualifying_in_both": len(p & c),
        "qualifying_only_previous": len(p - c),
        "qualifying_only_current": len(c - p),
        "previous_qualifying_now_other_rows_only": len((p - c) & after.keys()),
        "previous_qualifying_now_no_facility_rows": len((p - c) - after.keys()),
        "operator_metadata_changed": sum(
            before[key]["operators"] != after[key]["operators"] for key in common
        ),
        "location_metadata_changed": sum(
            before[key]["locations"] != after[key]["locations"] for key in common
        ),
        "interpretation": "Source presence changes only; no physical newness or shut-in inference",
    }


def compare_assignments(volumetrics: Path, month: str, history: Path, infrastructure: Path) -> dict:
    """Compare monthly operator with supporting history and current reference."""
    monthly = monthly_metadata(volumetrics, month)
    intervals = history_intervals(history)
    payload, _ = read_csv_payload(infrastructure)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    if not {"FacilityID", "OperatorBAID"}.issubset(reader.fieldnames or []):
        raise ValueError("Missing infrastructure assignment columns")
    current: dict[str, str] = {}
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed infrastructure row")
        if row["FacilityID"] in current:
            raise ValueError("Duplicate infrastructure assignment key")
        current[row["FacilityID"]] = row["OperatorBAID"] or "UNKNOWN"
    checks: Counter[str] = Counter()
    for facility, metadata in monthly.items():
        if not metadata["qualifies"]:
            continue
        checks["qualifying_facilities"] += 1
        operators = metadata["operators"]
        candidates = assignment_candidates(intervals.get(facility, []), month)
        if len(operators) != 1:
            checks["monthly_conflicting_operator"] += 1
            continue
        operator = next(iter(operators))
        if not candidates:
            checks["history_missing"] += 1
        elif len(candidates) > 1:
            checks["history_ambiguous"] += 1
        else:
            checks["history_match" if candidates[0] == operator else "history_mismatch"] += 1
        if facility not in current:
            checks["current_reference_missing"] += 1
        elif current[facility] != operator:
            checks["current_operator_differs"] += 1
    return {
        "period": month,
        "checks": dict(checks),
        "volumetrics_sha256": hashlib.sha256(volumetrics.read_bytes()).hexdigest(),
        "history_sha256": hashlib.sha256(history.read_bytes()).hexdigest(),
        "infrastructure_sha256": hashlib.sha256(infrastructure.read_bytes()).hexdigest(),
        "policy": "Monthly operator stays authoritative; this diagnostic cannot assign fallbacks",
    }

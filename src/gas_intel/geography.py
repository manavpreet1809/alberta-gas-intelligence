"""Assess a candidate DLS box; does not certify an official field boundary."""

import csv
import hashlib
import io
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from gas_intel.ingestion.parsers import read_csv_payload
from gas_intel.validation.values import classify_volume


@dataclass(frozen=True)
class DLSBox:
    """Inclusive analyst-selected township/range box on one meridian."""

    township_min: int
    township_max: int
    range_min: int
    range_max: int
    meridian: int

    def __post_init__(self) -> None:
        """Reject ambiguous or reversed numeric bounds."""
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            raise ValueError("DLS bounds must be positive integers")
        if self.township_min > self.township_max or self.range_min > self.range_max:
            raise ValueError("DLS lower bounds must not exceed upper bounds")

    def contains(self, township: str, range_: str, meridian: str) -> bool:
        """Use explicit numeric fields, never names or substring matching."""
        if not all(value.isascii() and value.isdecimal() for value in [township, range_, meridian]):
            raise ValueError("DLS coordinates must contain ASCII digits")
        return (
            self.township_min <= int(township) <= self.township_max
            and self.range_min <= int(range_) <= self.range_max
            and int(meridian) == self.meridian
        )


def profile_box(path: Path, month: str, box: DLSBox) -> dict[str, object]:
    """Report sample coverage using that month's locations, not a frozen cohort."""
    payload, _ = read_csv_payload(path)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    required = {
        "ProductionMonth",
        "ReportingFacilityID",
        "OperatorBAID",
        "ActivityID",
        "ProductID",
        "Volume",
        "FacilityTownship",
        "FacilityRange",
        "FacilityMeridian",
    }
    headers = reader.fieldnames or []
    if len(set(headers)) != len(headers) or not required.issubset(headers):
        raise ValueError("Missing or duplicate coverage headers")
    facilities: set[str] = set()
    operators: set[str] = set()
    positions: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    total = Decimal(0)
    selected_rows = invalid_locations = invalid_volumes = 0
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed coverage row")
        if row["ProductionMonth"] != month:
            raise ValueError("Unexpected month in coverage input")
        facility = row["ReportingFacilityID"]
        position = (row["FacilityTownship"], row["FacilityRange"], row["FacilityMeridian"])
        positions[facility].add(position)
        try:
            included = box.contains(*position)
        except ValueError:
            invalid_locations += 1
            continue
        if not included or row["ActivityID"] != "PROD" or row["ProductID"] != "GAS":
            continue
        selected_rows += 1
        facilities.add(facility)
        operators.add(row["OperatorBAID"] or "UNKNOWN")
        state, volume = classify_volume(row["Volume"])
        if state not in {"positive", "zero"}:
            invalid_volumes += 1
        else:
            total += volume
    cohort_fingerprint = hashlib.sha256("\n".join(sorted(facilities)).encode()).hexdigest()
    return {
        "period": month,
        "box": asdict(box),
        "status": "candidate coverage only; scope approval and frozen cohort pending",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "gas_prod_rows": selected_rows,
        "producing_facility_count": len(facilities),
        "operator_count_including_unknown": len(operators),
        "accepted_volume_e3m3": str(total),
        "invalid_location_source_rows": invalid_locations,
        "invalid_selected_volume_rows": invalid_volumes,
        "conflicting_location_facilities": sum(len(values) > 1 for values in positions.values()),
        "qualifying_facility_set_sha256": cohort_fingerprint,
    }

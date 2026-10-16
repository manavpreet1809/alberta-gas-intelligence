"""Offline source profiling for Stage 2; never modifies or extracts raw files."""

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZipFile

MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_DEPTH = 2


def read_csv_payload(path: Path) -> tuple[bytes, list[dict[str, object]]]:
    """Read a CSV through at most two ZIP layers, recording every content hash."""
    payload = path.read_bytes()
    lineage: list[dict[str, object]] = []
    for depth in range(MAX_DEPTH + 1):
        if not payload.startswith(b"PK"):
            return payload, lineage
        if depth == MAX_DEPTH:
            raise ValueError("Archive nesting exceeds the verified two-layer structure")
        with ZipFile(io.BytesIO(payload)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1:
                raise ValueError("Expected exactly one payload member per ZIP layer")
            member = members[0]
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError("Archive member exceeds the profiling size limit")
            # Read in memory, never extract member paths onto the filesystem.
            payload = archive.read(member)
            lineage.append(
                {
                    "name": member.filename,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    raise AssertionError("Unreachable archive state")


def profile_source(path: Path, expected_month: str) -> dict[str, object]:
    """Measure observed GAS/PROD rows without claiming a final study-area metric."""
    payload, lineage = read_csv_payload(path)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    headers = reader.fieldnames or []
    required = {
        "ProductionMonth",
        "ReportingFacilityID",
        "OperatorBAID",
        "ActivityID",
        "ProductID",
        "Volume",
        "FromToID",
        "ReportingFacilityType",
        "SubmissionDate",
    }
    if len(set(headers)) != len(headers) or not required.issubset(headers):
        raise ValueError("Missing required or duplicate source headers")
    blanks: Counter[str] = Counter()
    codes: dict[str, Counter[str]] = {key: Counter() for key in ["ActivityID", "ProductID"]}
    facility_types: Counter[str] = Counter()
    volume_states: Counter[str] = Counter()
    facility_volumes: dict[str, Decimal] = defaultdict(Decimal)
    operators: dict[str, set[str]] = defaultdict(set)
    keys: Counter[tuple[str, ...]] = Counter()
    total = Decimal(0)
    rows = qualifying = masked = 0
    submissions: list[str] = []
    for row in reader:
        rows += 1
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed column count at source row {rows}")
        if row["ProductionMonth"] != expected_month:
            raise ValueError(f"Unexpected production month at source row {rows}")
        for key, value in row.items():
            if not value.strip():
                blanks[key] += 1
        for key, counts in codes.items():
            counts[row[key]] += 1
        if row["SubmissionDate"]:
            submissions.append(row["SubmissionDate"])
        if row["ActivityID"] != "PROD" or row["ProductID"] != "GAS":
            continue
        qualifying += 1
        facility = row["ReportingFacilityID"]
        operators[facility].add(row["OperatorBAID"])
        facility_types[row["ReportingFacilityType"]] += 1
        keys[(expected_month, facility, row["ActivityID"], row["ProductID"], row["FromToID"])] += 1
        masked += row["FromToID"] == "***"
        try:
            volume = Decimal(row["Volume"])
            if not volume.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            volume_states["invalid_or_blank"] += 1
            continue
        if volume.as_tuple().exponent < -3:
            volume_states["exceeds_documented_scale"] += 1
        volume_states["negative" if volume < 0 else "zero" if volume == 0 else "positive"] += 1
        total += volume
        facility_volumes[facility] += volume
    return {
        "period": expected_month,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "archive_lineage": lineage,
        "encoding": "utf-8-sig (strict decode succeeded)",
        "headers": headers,
        "row_count": rows,
        "blank_counts": dict(blanks),
        "codes": {key: dict(value) for key, value in codes.items()},
        "submission_date_min": min(submissions, default=None),
        "submission_date_max": max(submissions, default=None),
        "gas_prod": {
            "row_count": qualifying,
            "facility_count": len(operators),
            "operator_count": len({op for values in operators.values() for op in values if op}),
            "facility_types": dict(facility_types),
            "volume_states": dict(volume_states),
            "valid_volume_sum_e3m3": str(total),
            "facility_aggregate_zero_count": sum(v == 0 for v in facility_volumes.values()),
            "masked_from_to_count": masked,
            "missing_operator_facility_count": sum("" in values for values in operators.values()),
            "conflicting_operator_facility_count": sum(
                len(values) > 1 for values in operators.values()
            ),
            "candidate_key_duplicate_extra_rows": sum(count - 1 for count in keys.values()),
            "candidate_key": [
                "ProductionMonth",
                "ReportingFacilityID",
                "ActivityID",
                "ProductID",
                "FromToID",
            ],
        },
    }


def main() -> None:
    """Profile one local download and write a JSON report outside raw storage."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--month", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw_path = args.path.resolve()
    output = args.output.resolve()
    if output == raw_path or "raw" in output.parts:
        parser.error("Profile output must be outside raw storage")
    report = profile_source(args.path, args.month)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

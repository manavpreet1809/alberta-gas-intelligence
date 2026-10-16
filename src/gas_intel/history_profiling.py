"""Inspect operator-history month intervals without choosing ambiguous operators."""

import csv
import hashlib
import io
import re
from collections import defaultdict
from pathlib import Path

from gas_intel.ingestion.parsers import read_csv_payload

MONTH_PATTERN = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])\Z")


def month_number(text: str) -> int:
    """Validate a production period and return its sortable integer month."""
    match = MONTH_PATTERN.fullmatch(text)
    if not match or int(match[1]) == 0:
        raise ValueError(f"Invalid production period: {text!r}")
    return int(match[1]) * 12 + int(match[2]) - 1


def history_intervals(path: Path) -> dict[str, list[tuple[int, int, str]]]:
    """Read documented month intervals; end-of-time stays an integer, not a timestamp."""
    payload, _ = read_csv_payload(path)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True)
    required = {"FacilityID", "OperatorBAID", "StartDate", "EndDate"}
    headers = reader.fieldnames or []
    if len(set(headers)) != len(headers) or not required.issubset(headers):
        raise ValueError("Missing or duplicate history headers")
    groups: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed history row")
        if not row["FacilityID"] or not row["OperatorBAID"]:
            raise ValueError("Blank history assignment key")
        start, end = month_number(row["StartDate"]), month_number(row["EndDate"])
        if start > end:
            raise ValueError("Reversed history interval")
        groups[row["FacilityID"]].append((start, end, row["OperatorBAID"]))
    return {facility: sorted(values) for facility, values in groups.items()}


def assignment_candidates(intervals: list[tuple[int, int, str]], month: str) -> list[str]:
    """Return every candidate under the explicit inclusive-end hypothesis."""
    period = month_number(month)
    return [operator for start, end, operator in intervals if start <= period <= end]


def profile_history(path: Path) -> dict[str, object]:
    """Measure gaps and overlaps; observations do not prove endpoint semantics."""
    groups = history_intervals(path)
    overlap_events = gap_events = open_ends = rows = 0
    for intervals in groups.values():
        covered_until = None
        for start, end, _ in intervals:
            rows += 1
            open_ends += end == month_number("9999-12")
            if covered_until is not None:
                overlap_events += start <= covered_until
                gap_events += start > covered_until + 1
            covered_until = end if covered_until is None else max(covered_until, end)
    return {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "interval_hypothesis": "inclusive production-month endpoints; diagnostics only",
        "row_count": rows,
        "facility_count": len(groups),
        "open_end_rows": open_ends,
        "overlap_events": overlap_events,
        "gap_events": gap_events,
        "policy": "Do not choose arbitrary assignments; compare against monthly volumetrics first",
    }

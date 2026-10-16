"""Measure reference-file schemas and key cardinality without publishing source rows."""

import hashlib
from collections import Counter
from pathlib import Path

from gas_intel.ingestion.parsers import csv_records, read_csv_payload

REFERENCE_KEYS = {
    "facilities": ("FacilityID",),
    "operators": ("BAIdentifier",),
    "operator_history": ("FacilityID", "OperatorBAID", "StartDate", "EndDate"),
}


def profile_reference(path: Path, source: str) -> dict[str, object]:
    """Profile a verified reference category; IDs always remain strings."""
    if source not in REFERENCE_KEYS:
        raise ValueError(f"Unknown reference category: {source}")
    payload, lineage = read_csv_payload(path)
    key_fields = REFERENCE_KEYS[source]
    headers, reader = csv_records(payload, set(key_fields))
    blanks: Counter[str] = Counter()
    keys: Counter[tuple[str, ...]] = Counter()
    rows = blank_keys = 0
    for row in reader:
        rows += 1
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed reference row {rows}")
        for field, value in row.items():
            if not value.strip():
                blanks[field] += 1
        key = tuple(row[field] for field in key_fields)
        keys[key] += 1
        blank_keys += any(not item.strip() for item in key)
    return {
        "source": source,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "archive_lineage": lineage,
        "headers": headers,
        "row_count": rows,
        "key_fields": list(key_fields),
        "distinct_keys": len(keys),
        "blank_key_rows": blank_keys,
        "duplicate_extra_rows": sum(count - 1 for count in keys.values()),
        "blank_counts": dict(blanks),
    }

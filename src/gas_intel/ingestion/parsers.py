"""Read verified archive packaging without extracting member paths."""

import hashlib
import io
from collections.abc import Iterator
from pathlib import Path
from zipfile import ZipFile

MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_DEPTH = 2


def read_csv_payload(path: Path) -> tuple[bytes, list[dict[str, object]]]:
    """Read plain CSV or nested ZIP bytes with size, CRC and ambiguity checks."""
    if path.stat().st_size > MAX_MEMBER_BYTES:
        raise ValueError("Source exceeds the profiling size limit")
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
            # Limit actual reads too: declared metadata is not the only guard.
            with archive.open(member) as stream:
                payload = stream.read(MAX_MEMBER_BYTES + 1)
            if len(payload) > MAX_MEMBER_BYTES:
                raise ValueError("Archive payload exceeds the profiling size limit")
            lineage.append(
                {
                    "name": member.filename,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    raise AssertionError("Unreachable archive state")


def csv_records(
    payload: bytes, required: set[str], expected_headers: list[str] | None = None
) -> tuple[list[str], Iterator[dict[str, str]]]:
    """Validate UTF-8 CSV structure and optionally an exact ordered schema."""
    import csv

    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True)
    headers = reader.fieldnames or []
    if not headers or any(not header.strip() for header in headers):
        raise ValueError("Missing or blank source headers")
    if len(set(headers)) != len(headers) or not required.issubset(headers):
        raise ValueError("Missing required columns or duplicate source headers")
    if expected_headers is not None and headers != expected_headers:
        raise ValueError("Source headers differ from the pinned schema")

    def records() -> Iterator[dict[str, str]]:
        """Keep ordinal row checks shared across profiling paths."""
        for ordinal, row in enumerate(reader, 1):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed column count at source row {ordinal}")
            yield row

    return headers, records()

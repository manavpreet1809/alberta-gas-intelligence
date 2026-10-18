"""Atomically append acquisition events while preserving previous manifest history."""

import csv
import os
import tempfile
from pathlib import Path

FIELDS = [
    "ingestion_run_id",
    "source_name",
    "reporting_period",
    "url",
    "downloaded_at",
    "bytes",
    "sha256",
    "source_file",
    "row_count",
    "configuration_hash",
    "status",
    "error",
]


def append_event(path: Path, event: dict[str, object]) -> None:
    """Serialize writers with an exclusive lock directory and atomically publish CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError("Manifest is locked; do not run simultaneous acquisitions") from exc
    temporary = None
    try:
        previous = []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames != FIELDS:
                    raise ValueError("Existing manifest schema is incompatible")
                previous = list(reader)
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, newline="", encoding="utf-8"
        ) as file:
            temporary = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(previous)
            writer.writerow({field: event.get(field, "") for field in FIELDS})
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.rmdir()

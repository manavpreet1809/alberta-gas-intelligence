"""Acquire explicitly requested verification months without approving study scope."""

import hashlib
import logging
import os
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

from gas_intel.history_profiling import month_number
from gas_intel.ingestion.manifest import append_event
from gas_intel.profiling import profile_source

LOGGER = logging.getLogger(__name__)
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


def acquire_month(root: Path, month: str, *, attempts: int = 3) -> dict[str, object]:
    """Validate a temporary download, retain revisions by hash and append an audit event."""
    month_number(month)
    if not 1 <= attempts <= 3:
        raise ValueError("Acquisition attempts must be between 1 and 3")
    contract_path = root / "config/sources.yaml"
    contract_bytes = contract_path.read_bytes()
    config = yaml.safe_load(contract_bytes)["volumetrics"]
    url = config["url_template"].format(month=month)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.petrinex.gov.ab.ca" or parsed.username:
        raise ValueError("Source URL must use the verified public Petrinex HTTPS endpoint")
    event: dict[str, object] = {
        "ingestion_run_id": str(uuid.uuid4()),
        "source_name": "AB volumetrics",
        "reporting_period": month,
        "url": url,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "configuration_hash": hashlib.sha256(contract_bytes).hexdigest(),
    }
    manifest = root / "data/raw/manifest.csv"
    temporary_dir = root / "data/processed"
    temporary_dir.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        for attempt in range(attempts):
            try:
                response = requests.get(url, stream=True, timeout=(15, 90))
                try:
                    response.raise_for_status()
                    with tempfile.NamedTemporaryFile(dir=temporary_dir, delete=False) as file:
                        temporary = Path(file.name)
                        size = 0
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            size += len(chunk)
                            if size > MAX_DOWNLOAD_BYTES:
                                raise ValueError("Download exceeds the source size limit")
                            file.write(chunk)
                        file.flush()
                        os.fsync(file.fileno())
                    if not size:
                        raise ValueError("Downloaded source is empty")
                finally:
                    response.close()
                break
            except requests.RequestException:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
                if attempt + 1 == attempts:
                    raise
                LOGGER.warning(
                    "Retrying %s after request failure (%s/%s)", month, attempt + 1, attempts
                )
                time.sleep(attempt + 1)
        profile = profile_source(temporary, month, config["expected_headers"])
        if len(profile["archive_lineage"]) != 2:
            raise ValueError("Source packaging differs from the verified nested ZIP contract")
        if not profile["row_count"]:
            raise ValueError("Source has no records")
        digest = profile["source_sha256"]
        accepted = root / "data/raw" / digest / "source.zip"
        accepted.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation avoids overwriting an accepted revision, even on reruns.
        try:
            os.link(temporary, accepted)
        except FileExistsError:
            if hashlib.sha256(accepted.read_bytes()).hexdigest() != digest:
                raise ValueError(
                    "Existing content-addressed raw file failed its hash check"
                ) from None
            event["status"] = "unchanged"
        else:
            event["status"] = "downloaded"
        event.update(
            bytes=size,
            sha256=digest,
            source_file=str(accepted.relative_to(root)),
            row_count=profile["row_count"],
        )
        append_event(manifest, event)
        return {"event": event, "profile": profile}
    except Exception as exc:
        event.update(status="failed", error=type(exc).__name__)
        append_event(manifest, event)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

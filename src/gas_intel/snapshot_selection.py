"""Validate explicit fixed-cohort source selection before loading a warehouse."""

import hashlib
import json
from pathlib import Path

from gas_intel.geography import DLSBox
from gas_intel.window_verification import month_sequence


def read_cohort(root: Path, path: Path, study: dict, config_hash: str) -> tuple[dict, str]:
    """Require a content-addressed artifact for the exact configured window and source set."""
    path = path if path.is_absolute() else root / path
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if path.stem != digest:
        raise ValueError("Cohort artifact hash does not match its filename")
    artifact = json.loads(payload)
    months = month_sequence(study["start_month"], study["end_month"])
    if (
        artifact.get("format_version") != 1
        or artifact.get("configuration_hash") != config_hash
        or artifact.get("analysis_months") != months
        or artifact.get("context_month") != study["context_start_month"]
    ):
        raise ValueError("Cohort artifact does not match the configured study")
    box = DLSBox(
        **{
            k: study[k]
            for k in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        }
    )
    members = artifact["facilities"]
    ids = [row["facility_id"] for row in members]
    if (
        not ids
        or any(not isinstance(key, str) or not key for key in ids)
        or ids != sorted(set(ids))
    ):
        raise ValueError("Cohort IDs must be nonempty, unique, sorted strings")
    if (
        hashlib.sha256("\n".join(ids).encode()).hexdigest()
        != artifact["candidate_cohort_set_sha256"]
    ):
        raise ValueError("Cohort membership fingerprint mismatch")
    for row in members:
        if len(row["location"]) != 3 or not box.contains(*map(str, row["location"])):
            raise ValueError("Cohort location is outside the configured box")
    periods = [row["period"] for row in artifact["monthly_source_baselines"]]
    if periods != [study["context_start_month"], *months]:
        raise ValueError("Cohort artifact requires one baseline per analysis/context month")
    return artifact, digest

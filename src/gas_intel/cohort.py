"""Prepare a pinned candidate cohort and independently checked monthly baselines."""

import hashlib
import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path

from gas_intel.geography import DLSBox
from gas_intel.ingestion.parsers import csv_records, read_csv_payload
from gas_intel.pipeline import configuration
from gas_intel.validation.values import classify_volume
from gas_intel.window_verification import month_sequence, verify_window


def prepare_cohort(root: Path) -> dict:
    """Freeze candidate membership without claiming human approval or changing the warehouse."""
    study, config_hash = configuration(root)
    box = DLSBox(
        **{
            key: study[key]
            for key in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        }
    )
    months = month_sequence(study["start_month"], study["end_month"])
    if month_sequence(study["context_start_month"], study["start_month"]) != [
        study["context_start_month"],
        study["start_month"],
    ]:
        raise ValueError("Context must immediately precede the analysis window")
    report = verify_window(root, months[0], months[-1], box, include_members=True)
    members = set(report["candidate_facility_ids"])
    if not members:
        raise ValueError("Candidate cohort is empty")
    context = verify_window(
        root,
        study["context_start_month"],
        study["context_start_month"],
        box,
        include_members=True,
        tracked_facilities=members,
    )
    locations = {
        row["facility_id"]: set(map(tuple, row["positions"])) for row in report["location_evidence"]
    }
    for row in [*report["location_evidence"], *context["location_evidence"]]:
        facility = row["facility_id"]
        if facility not in members:
            continue
        if row["has_unresolved_location"]:
            raise ValueError(f"Unresolved cohort location: {facility}")
        locations[facility].update(map(tuple, row["positions"]))
        if len(locations[facility]) != 1:
            raise ValueError(f"Conflicting cohort location: {facility}")
    baselines = []
    for monthly in [*context["monthly_checks"], *report["monthly_checks"]]:
        month = monthly["period"]
        inventory = json.loads((root / "data/verification" / f"{month}.json").read_text())
        source = root / inventory["event"]["source_file"]
        payload, _ = read_csv_payload(source)
        _, records = csv_records(
            payload, {"ReportingFacilityID", "ActivityID", "ProductID", "Volume"}
        )
        rows, total = 0, Decimal(0)
        detail_keys = set()
        operators: dict[str, set[str]] = {}
        for record in records:
            facility = record["ReportingFacilityID"]
            if facility not in members:
                continue
            operators.setdefault(facility, set()).add(record["OperatorBAID"] or "UNKNOWN")
            if record["ActivityID"] != "PROD" or record["ProductID"] != "GAS":
                continue
            state, volume = classify_volume(record["Volume"])
            if state not in {"positive", "zero"}:
                raise ValueError(f"Unresolved qualifying volumes: {month}")
            key = (facility, record["FromToID"])
            if key in detail_keys:
                raise ValueError(f"Duplicate cohort detail: {month}")
            detail_keys.add(key)
            rows += 1
            total += volume
        if any(len(values) > 1 for values in operators.values()):
            raise ValueError(f"Conflicting cohort operators: {month}")
        is_context = month == study["context_start_month"]
        expected_rows = (
            monthly["tracked_gas_prod_rows"] if is_context else monthly["candidate_gas_prod_rows"]
        )
        expected_volume = (
            monthly["tracked_volume_e3m3"] if is_context else monthly["candidate_volume_e3m3"]
        )
        if rows != expected_rows or total != Decimal(expected_volume):
            raise ValueError(f"Independent cohort baseline mismatch: {month}")
        monthly = {**monthly, "cohort_gas_prod_rows": rows, "cohort_volume_e3m3": str(total)}
        baselines.append(monthly)
    artifact = {
        "format_version": 1,
        "status": "candidate; final scope confirmation pending",
        "scope_approved": study.get("approved") is True,
        "configuration_hash": config_hash,
        "cohort_policy": (
            "union of in-box facilities in the 24 analysis months; context does not add members"
        ),
        "analysis_months": months,
        "context_month": study["context_start_month"],
        "box": report["box"],
        "candidate_cohort_set_sha256": report["candidate_cohort_set_sha256"],
        "facilities": [
            {"facility_id": facility, "location": list(next(iter(locations[facility])))}
            for facility in sorted(members)
        ],
        "monthly_source_baselines": baselines,
        "code_sha256": {
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ["cohort.py", "window_verification.py", "geography.py"]
        },
    }
    payload = (json.dumps(artifact, sort_keys=True, indent=2) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    target = root / "data/processed/cohorts" / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != payload:
                    raise ValueError(
                        "Existing cohort artifact content does not match its hash"
                    ) from None
        finally:
            temporary.unlink(missing_ok=True)
    return {
        "artifact": str(target.relative_to(root)),
        "artifact_sha256": digest,
        "configuration_hash": config_hash,
        "scope_approved": artifact["scope_approved"],
        "facility_count": len(members),
        "analysis_month_count": len(months),
        "candidate_cohort_set_sha256": report["candidate_cohort_set_sha256"],
        "context_adds_members": False,
        "source_month_count": len(baselines),
    }


def main() -> None:
    """Prepare local candidate evidence; keep facility-level source data out of Git."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    import typer

    typer.echo(json.dumps(prepare_cohort(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()

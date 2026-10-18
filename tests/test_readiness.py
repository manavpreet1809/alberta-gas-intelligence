"""Evidence summaries cannot certify missing source contracts."""

import json
from pathlib import Path

import yaml

from gas_intel.readiness import source_readiness


def test_missing_evidence_is_pending(tmp_path: Path) -> None:
    checks = source_readiness(tmp_path)
    assert all(item["status"] == "pending" for item in checks)


def test_malformed_reference_evidence_fails(tmp_path: Path) -> None:
    evidence = tmp_path / "docs/evidence"
    evidence.mkdir(parents=True)
    (evidence / "reference_facilities.json").write_text("{bad")
    checks = source_readiness(tmp_path)
    assert checks[0]["status"] == "fail"


def test_bad_window_does_not_pass(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "study_area.yaml").write_text(
        yaml.safe_dump(
            {
                "candidate_proposal": {
                    "township_min": 60,
                    "township_max": 65,
                    "range_min": 3,
                    "range_max": 7,
                    "meridian": 6,
                    "start_month": "2024-01",
                    "end_month": "2025-11",
                    "approved": True,
                }
            }
        )
    )
    checks = source_readiness(tmp_path)
    assert next(item for item in checks if item["check"] == "study_scope")["status"] == "fail"


def test_scope_confirmation_is_not_source_certification(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "study_area.yaml").write_text(
        yaml.safe_dump(
            {
                "candidate_proposal": {
                    "township_min": 60,
                    "township_max": 65,
                    "range_min": 3,
                    "range_max": 7,
                    "meridian": 6,
                    "start_month": "2024-01",
                    "end_month": "2025-12",
                    "approved": True,
                }
            }
        )
    )
    checks = source_readiness(tmp_path)
    assert next(item for item in checks if item["check"] == "study_scope")["status"] == "pass"
    assert (
        next(item for item in checks if item["check"] == "source_exit_review")["status"]
        == "pending"
    )


def test_duplicate_reference_keys_fail_summary(tmp_path: Path) -> None:
    evidence = tmp_path / "docs/evidence"
    evidence.mkdir(parents=True)
    (evidence / "reference_facilities.json").write_text(
        json.dumps(
            {
                "row_count": 2,
                "blank_key_rows": 0,
                "duplicate_extra_rows": 1,
            }
        )
    )
    assert source_readiness(tmp_path)[0]["status"] == "fail"


def test_window_evidence_must_match_proposed_box_and_month_sequence(tmp_path: Path) -> None:
    import hashlib
    import shutil

    from gas_intel.window_verification import month_sequence

    config = tmp_path / "config"
    config.mkdir()
    repository = Path(__file__).parents[1]
    for name in ["sources.yaml", "study_area.yaml"]:
        shutil.copy(repository / "config" / name, config / name)
    study = yaml.safe_load((config / "study_area.yaml").read_text())["candidate_proposal"]
    evidence = tmp_path / "docs/evidence"
    evidence.mkdir(parents=True)
    report = {
        "month_count": 24,
        "start_month": study["start_month"],
        "end_month": study["end_month"],
        "box": {
            key: study[key]
            for key in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        },
        "source_contract_sha256": hashlib.sha256(
            (config / "sources.yaml").read_bytes()
        ).hexdigest(),
        "candidate_location_conflict_facility_count": 0,
        "candidate_unresolved_location_facilities": 0,
        "monthly_checks": [
            {
                "period": month,
                "unresolved_volume_facilities": 0,
                "candidate_key_duplicate_extra_rows": 0,
            }
            for month in month_sequence(study["start_month"], study["end_month"])
        ],
    }
    path = evidence / "candidate_window_verification.json"
    path.write_text(json.dumps(report))

    def selected() -> dict[str, str]:
        return next(
            item for item in source_readiness(tmp_path) if item["check"] == "selected_window"
        )

    assert selected()["status"] == "pass"
    report["monthly_checks"][1]["period"] = report["monthly_checks"][0]["period"]
    path.write_text(json.dumps(report))
    assert selected()["status"] == "fail"
    report["monthly_checks"][1]["period"] = month_sequence(
        study["start_month"], study["end_month"]
    )[1]
    report["box"]["range_min"] = 1
    path.write_text(json.dumps(report))
    assert selected()["status"] == "fail"

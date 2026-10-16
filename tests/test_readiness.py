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

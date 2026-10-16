"""The audit must fail without pinned inputs; synthetic CI never needs private raw files."""

import json
from pathlib import Path

import pytest

from gas_intel.source_audit import audit_sources


def test_missing_evidence_fails_instead_of_reporting_success(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        audit_sources(tmp_path)


def test_tampered_source_hash_fails_before_baseline_calculation(tmp_path: Path) -> None:
    evidence = tmp_path / "docs/evidence"
    evidence.mkdir(parents=True)
    digest = "0" * 64
    (evidence / "known_month_baselines.json").write_text(json.dumps([{"source_sha256": digest}]))
    raw = tmp_path / "data/raw" / digest
    raw.mkdir(parents=True)
    (raw / "source.zip").write_bytes(b"modified content")
    with pytest.raises(ValueError, match="Pinned source bytes changed"):
        audit_sources(tmp_path)

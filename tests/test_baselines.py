"""Reviewed expectations stay independent of the implementation's calculations."""

import hashlib
from pathlib import Path

import pytest

from gas_intel.baselines import verify_baseline


@pytest.fixture
def reviewed_source(tmp_path: Path) -> tuple[Path, dict, Path]:
    fixture = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"
    lines = fixture.read_bytes().splitlines()
    source = tmp_path / "synthetic_known_month.csv"
    source.write_bytes(b"\n".join(lines[index] for index in [0, 1, 2, 3, 6, 7]) + b"\n")
    contract = Path(__file__).parents[1] / "config/sources.yaml"
    baseline = {
        "period": "2025-01",
        "source_rows": 5,
        "qualifying_rows": 3,
        "facilities": 2,
        "volume_e3m3": "102.500",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "payload_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
    }
    return source, baseline, contract


def test_independent_baseline_passes(reviewed_source) -> None:
    assert verify_baseline(*reviewed_source)["passed"] is True


@pytest.mark.parametrize(
    "field,value",
    [("source_rows", 6), ("qualifying_rows", 4), ("facilities", 3), ("volume_e3m3", "103")],
)
def test_changed_counts_or_volumes_fail(reviewed_source, field, value) -> None:
    source, baseline, contract = reviewed_source
    baseline[field] = value
    with pytest.raises(ValueError, match="counts/volume"):
        verify_baseline(source, baseline, contract)


@pytest.mark.parametrize("field", ["source_sha256", "payload_sha256", "source_contract_sha256"])
def test_changed_snapshot_or_contract_cannot_pass(reviewed_source, field) -> None:
    source, baseline, contract = reviewed_source
    baseline[field] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        verify_baseline(source, baseline, contract)

"""Source profiling edge cases use invented values with verified source headers."""

import io
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pytest

from gas_intel.profiling import profile_source

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_volumetrics.csv"


def zipped(payload: bytes, name: str = "source.csv") -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(name, payload)
    return stream.getvalue()


def test_profile_preserves_detail_and_reports_invalid_states() -> None:
    result = profile_source(FIXTURE, "2025-01")
    assert result["row_count"] == 7
    gas = result["gas_prod"]
    assert gas["row_count"] == 5
    assert gas["valid_volume_sum_e3m3"] == "101.500"
    assert gas["volume_states"] == {"positive": 2, "zero": 1, "negative": 1, "invalid_or_blank": 1}
    assert gas["facility_aggregate_zero_count"] == 1
    assert gas["masked_from_to_count"] == 1
    assert gas["missing_operator_facility_count"] == 1
    assert gas["candidate_key_duplicate_extra_rows"] == 0
    assert result["blank_counts"]["ActivityID"] == 1


def test_nested_archives_have_lineage_without_extraction(tmp_path: Path) -> None:
    path = tmp_path / "download.zip"
    path.write_bytes(zipped(zipped(FIXTURE.read_bytes()), "inner.zip"))
    result = profile_source(path, "2025-01")
    assert len(result["archive_lineage"]) == 2
    assert result["gas_prod"] == profile_source(FIXTURE, "2025-01")["gas_prod"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["download.zip"]


def test_wrong_month_fails() -> None:
    with pytest.raises(ValueError, match="Unexpected production month"):
        profile_source(FIXTURE, "2025-02")


@pytest.mark.parametrize("data", [b"Volume\n1\n", b"Volume,Volume\n1,2\n"])
def test_missing_or_duplicate_headers_fail(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="headers"):
        profile_source(path, "2025-01")


def test_truncated_row_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(FIXTURE.read_bytes().splitlines()[0] + b"\n2025-01,0012\n")
    with pytest.raises(ValueError, match="Malformed column count"):
        profile_source(path, "2025-01")


def test_ambiguous_archive_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("one.csv", FIXTURE.read_bytes())
        archive.writestr("two.csv", FIXTURE.read_bytes())
    with pytest.raises(ValueError, match="exactly one"):
        profile_source(path, "2025-01")


def test_deep_archive_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    path.write_bytes(zipped(zipped(zipped(FIXTURE.read_bytes()))))
    with pytest.raises(ValueError, match="nesting"):
        profile_source(path, "2025-01")


def test_corrupt_archive_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    path.write_bytes(b"PKcorrupt")
    with pytest.raises(BadZipFile):
        profile_source(path, "2025-01")


def test_nonfinite_volume_is_not_zero(tmp_path: Path) -> None:
    path = tmp_path / "nonfinite.csv"
    path.write_bytes(FIXTURE.read_bytes().replace(b"100.125", b"NaN"))
    gas = profile_source(path, "2025-01")["gas_prod"]
    assert gas["volume_states"]["invalid_or_blank"] == 2
    assert gas["volume_states"]["zero"] == 1


def test_duplicate_detail_and_operator_conflicts_are_visible(tmp_path: Path) -> None:
    path = tmp_path / "conflicts.csv"
    lines = FIXTURE.read_bytes().splitlines()
    # Keep one exact duplicate and a second operator on the same facility.
    path.write_bytes(b"\n".join([*lines, lines[1], lines[1].replace(b",0012,", b",12,")]) + b"\n")
    gas = profile_source(path, "2025-01")["gas_prod"]
    assert gas["candidate_key_duplicate_extra_rows"] == 2
    assert gas["conflicting_operator_facility_count"] == 1
    assert gas["operator_count"] == 4  # '0012' and '12' remain different IDs.


def test_archive_size_limit_is_checked_before_reading(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "source.zip"
    path.write_bytes(zipped(FIXTURE.read_bytes()))
    monkeypatch.setattr("gas_intel.ingestion.parsers.MAX_MEMBER_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        profile_source(path, "2025-01")


def test_archive_member_paths_are_never_extracted(tmp_path: Path) -> None:
    path = tmp_path / "source.zip"
    path.write_bytes(zipped(FIXTURE.read_bytes(), "../../outside.csv"))
    assert profile_source(path, "2025-01")["row_count"] == 7
    assert sorted(p.name for p in tmp_path.iterdir()) == ["source.zip"]


def test_plain_source_size_is_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("gas_intel.ingestion.parsers.MAX_MEMBER_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        profile_source(FIXTURE, "2025-01")

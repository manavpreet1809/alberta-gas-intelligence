"""Mocked acquisition checks preserve accepted raw bytes and all attempt history."""

import csv
import io
import shutil
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import requests

from gas_intel.ingestion.download import acquire_month
from gas_intel.ingestion.manifest import append_event


def archive(payload: bytes) -> bytes:
    for name in ["source.csv", "source.zip"]:
        output = io.BytesIO()
        with ZipFile(output, "w") as file:
            file.writestr(name, payload)
        payload = output.getvalue()
    return payload


@pytest.fixture
def acquisition_root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(Path(__file__).parents[1] / "config/sources.yaml", tmp_path / "config/sources.yaml")
    return tmp_path


def response(body: bytes) -> Mock:
    result = Mock()
    result.iter_content.return_value = [body]
    return result


def test_success_and_identical_rerun_are_audited_without_replacing_raw(
    acquisition_root, monkeypatch
) -> None:
    fixture = Path(__file__).parent / "fixtures/synthetic_volumetrics.csv"
    body = archive(fixture.read_bytes())
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response(body))
    first = acquire_month(acquisition_root, "2025-01")
    path = acquisition_root / first["event"]["source_file"]
    original_mtime = path.stat().st_mtime_ns
    second = acquire_month(acquisition_root, "2025-01")
    assert second["event"]["status"] == "unchanged"
    assert path.read_bytes() == body
    assert path.stat().st_mtime_ns == original_mtime
    with (acquisition_root / "data/raw/manifest.csv").open() as file:
        assert [row["status"] for row in csv.DictReader(file)] == ["downloaded", "unchanged"]
    assert list((acquisition_root / "data/processed").iterdir()) == []


def test_retry_uses_timeouts_and_closes_response(acquisition_root, monkeypatch) -> None:
    body = archive((Path(__file__).parent / "fixtures/synthetic_volumetrics.csv").read_bytes())
    success = response(body)
    get = Mock(side_effect=[requests.Timeout(), success])
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr("gas_intel.ingestion.download.time.sleep", lambda _: None)
    assert acquire_month(acquisition_root, "2025-01")["event"]["status"] == "downloaded"
    assert get.call_count == 2
    assert get.call_args.kwargs["timeout"] == (15, 90)
    success.close.assert_called_once()


@pytest.mark.parametrize("body", [b"", b"<html>maintenance</html>", b"A\n1\n"])
def test_invalid_response_never_becomes_accepted_raw(acquisition_root, monkeypatch, body) -> None:
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response(body))
    with pytest.raises(ValueError):
        acquire_month(acquisition_root, "2025-01")
    assert list((acquisition_root / "data/raw").glob("*/source.zip")) == []
    with (acquisition_root / "data/raw/manifest.csv").open() as file:
        assert list(csv.DictReader(file))[0]["status"] == "failed"


def test_failed_revision_does_not_touch_accepted_raw(acquisition_root, monkeypatch) -> None:
    body = archive((Path(__file__).parent / "fixtures/synthetic_volumetrics.csv").read_bytes())
    get = Mock(side_effect=[response(body), response(b"bad")])
    monkeypatch.setattr(requests, "get", get)
    accepted = acquire_month(acquisition_root, "2025-01")
    path = acquisition_root / accepted["event"]["source_file"]
    with pytest.raises(ValueError):
        acquire_month(acquisition_root, "2025-01")
    assert path.read_bytes() == body


def test_changed_revision_is_retained_separately(acquisition_root, monkeypatch) -> None:
    fixture = (Path(__file__).parent / "fixtures/synthetic_volumetrics.csv").read_bytes()
    monkeypatch.setattr(
        requests,
        "get",
        Mock(
            side_effect=[
                response(archive(fixture)),
                response(archive(fixture.replace(b"100.125", b"101.125"))),
            ]
        ),
    )
    first = acquire_month(acquisition_root, "2025-01")
    second = acquire_month(acquisition_root, "2025-01")
    assert first["event"]["sha256"] != second["event"]["sha256"]
    assert len(list((acquisition_root / "data/raw").glob("*/source.zip"))) == 2


def test_manifest_lock_fails_without_erasing_history(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    append_event(path, {"status": "downloaded"})
    original = path.read_bytes()
    path.with_suffix(".csv.lock").mkdir()
    with pytest.raises(RuntimeError, match="locked"):
        append_event(path, {"status": "failed"})
    assert path.read_bytes() == original


def test_exhausted_requests_are_audited(acquisition_root, monkeypatch) -> None:
    get = Mock(side_effect=requests.Timeout())
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr("gas_intel.ingestion.download.time.sleep", lambda _: None)
    with pytest.raises(requests.Timeout):
        acquire_month(acquisition_root, "2025-01")
    assert get.call_count == 3
    with (acquisition_root / "data/raw/manifest.csv").open() as file:
        assert list(csv.DictReader(file))[0]["error"] == "Timeout"


def test_atomic_publication_failure_leaves_no_partial_accepted_source(
    acquisition_root, monkeypatch
) -> None:
    body = archive((Path(__file__).parent / "fixtures/synthetic_volumetrics.csv").read_bytes())
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response(body))
    monkeypatch.setattr(
        "gas_intel.ingestion.download.os.link", Mock(side_effect=OSError("disk error"))
    )
    with pytest.raises(OSError, match="disk error"):
        acquire_month(acquisition_root, "2025-01")
    assert list((acquisition_root / "data/raw").glob("*/source.zip")) == []
    assert list((acquisition_root / "data/processed").iterdir()) == []

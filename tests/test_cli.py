"""Verify honest CLI behavior without source data or network access."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from gas_intel.cli import app
from gas_intel.settings import CONFIG_NAMES

runner = CliRunner()


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create explicit synthetic configuration templates."""
    for name in CONFIG_NAMES:
        (tmp_path / f"{name}.yaml").write_text('notes: "TODO(human): verify"\n')
    return tmp_path


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("doctor", "download", "load", "build", "validate", "export", "run-all"):
        assert command in result.output


@pytest.mark.parametrize("command", ["download", "load", "build", "validate", "export", "run-all"])
def test_stubs_fail_without_creating_outputs(command: str, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [command])
    assert result.exit_code == 2
    assert "not implemented in M0" in result.output
    assert list(tmp_path.iterdir()) == []


def test_doctor_separates_scaffold_from_source_readiness(config_dir: Path) -> None:
    result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir)])
    assert result.exit_code == 0
    assert "Scaffold ready" in result.output
    assert "Source contracts NOT verified" in result.output
    assert "TODO(human)" in result.output
    strict = runner.invoke(app, ["doctor", "--config-dir", str(config_dir), "--require-sources"])
    assert strict.exit_code == 1


def test_removing_markers_cannot_certify_source_contracts(config_dir: Path) -> None:
    for name in CONFIG_NAMES:
        (config_dir / f"{name}.yaml").write_text("verification_status: claimed\n")
    result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir), "--require-sources"])
    assert result.exit_code == 1
    assert "NOT verified" in result.output


@pytest.mark.parametrize("content", ["[broken", "[]", "", "scalar"])
def test_doctor_rejects_invalid_config(config_dir: Path, content: str) -> None:
    (config_dir / "sources.yaml").write_text(content)
    result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir)])
    assert result.exit_code == 1
    assert "ERROR: sources.yaml" in result.output
    assert "Scaffold ready" not in result.output


def test_doctor_rejects_missing_config(config_dir: Path) -> None:
    (config_dir / "codes.yaml").unlink()
    result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir)])
    assert result.exit_code == 1
    assert "codes.yaml" in result.output


def test_doctor_details_explains_missing_evidence_without_certifying_sources(
    config_dir: Path,
) -> None:
    result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir), "--details"])
    assert result.exit_code == 0
    assert "PENDING: reference_facilities" in result.output
    assert "PENDING: source_exit_review" in result.output
    assert "Source contracts NOT verified" in result.output

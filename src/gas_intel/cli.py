"""Command-line entry point for the milestone-driven pipeline."""

from pathlib import Path
from typing import Annotated

import typer

from gas_intel.doctor import check_scaffold
from gas_intel.ingestion.download import acquire_month
from gas_intel.readiness import source_readiness

app = typer.Typer(no_args_is_help=True, help="Alberta Gas Production Intelligence Platform")


@app.command()
def doctor(
    config_dir: Annotated[
        Path, typer.Option(help="Directory containing YAML configuration")
    ] = Path("config"),
    details: Annotated[
        bool, typer.Option(help="Show Stage 2 evidence and pending decisions")
    ] = False,
    require_sources: Annotated[
        bool, typer.Option(help="Fail unless source contracts have been verified")
    ] = False,
) -> None:
    """Check scaffold readiness; M0 cannot certify source contracts."""
    errors, pending = check_scaffold(config_dir)
    for error in errors:
        typer.echo(f"ERROR: {error}", err=True)
    if errors:
        raise typer.Exit(1)
    typer.echo("Scaffold ready: Python and configuration templates are readable.")
    typer.echo("Source contracts NOT verified: M1 is pending.")
    for name in pending:
        typer.echo(f"TODO(human): verify {name} during M1.")
    if details:
        for item in source_readiness(config_dir.resolve().parent):
            typer.echo(f"{item['status'].upper()}: {item['check']} — {item['detail']}")
    if require_sources:
        raise typer.Exit(1)


def not_implemented(command: str) -> None:
    """Fail safely instead of reporting a successful pipeline operation."""
    typer.echo(f"{command} is not implemented in M0. See PLAN.md for its milestone.", err=True)
    raise typer.Exit(2)


@app.command()
def download(
    verification_month: Annotated[
        str | None, typer.Option(help="Acquire one explicit source-verification month (YYYY-MM)")
    ] = None,
    project_root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
) -> None:
    """Acquire a verification sample; approved production-window downloads remain pending."""
    if verification_month is None:
        typer.echo(
            "Specify --verification-month YYYY-MM; production scope is not approved.", err=True
        )
        raise typer.Exit(2)
    try:
        result = acquire_month(project_root.resolve(), verification_month)
    except Exception as exc:
        typer.echo(f"Acquisition failed: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(1) from exc
    event = result["event"]
    typer.echo(f"{event['reporting_period']}: {event['status']} — SHA-256 {event['sha256']}")


@app.command()
def load() -> None:
    """Load a pinned source snapshot into staging (pending)."""
    not_implemented("load")


@app.command()
def build() -> None:
    """Build core and analytics tables (pending)."""
    not_implemented("build")


@app.command()
def validate() -> None:
    """Run data quality and reconciliation checks (pending)."""
    not_implemented("validate")


@app.command()
def export() -> None:
    """Validate and publish analytics exports (pending)."""
    not_implemented("export")


@app.command("run-all")
def run_all() -> None:
    """Run the validated end-to-end pipeline (pending)."""
    not_implemented("run-all")

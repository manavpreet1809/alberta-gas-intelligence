"""Report scaffold readiness without claiming source verification."""

import sys
from pathlib import Path

from gas_intel.settings import inspect_config


def check_scaffold(config_dir: Path) -> tuple[list[str], list[str]]:
    """Check the runtime and readable configuration templates."""
    errors, pending = inspect_config(config_dir)
    if sys.version_info < (3, 11):  # noqa: UP036 - explicit runtime diagnostic
        errors.append("Python 3.11 or newer is required")
    return errors, pending

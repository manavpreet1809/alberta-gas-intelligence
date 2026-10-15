"""Scaffold configuration checks; source contracts are verified in M1."""

from pathlib import Path

import yaml

CONFIG_NAMES = ("sources", "study_area", "codes", "validation")


def inspect_config(config_dir: Path) -> tuple[list[str], list[str]]:
    """Return structural errors and unresolved configuration markers."""
    errors: list[str] = []
    pending: list[str] = []
    for name in CONFIG_NAMES:
        path = config_dir / f"{name}.yaml"
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(f"{path.name}: cannot read YAML ({type(exc).__name__})")
            continue
        if not isinstance(content, dict):
            errors.append(f"{path.name}: expected a YAML mapping")
            continue
        # Structural readiness cannot certify domain semantics, even without TODOs.
        if "TODO(human)" in str(content):
            pending.append(path.name)
    return errors, pending

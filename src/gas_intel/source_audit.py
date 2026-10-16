"""Reproduce Stage 2 evidence from pinned local downloads; no pipeline publication."""

import hashlib
import json
from pathlib import Path

from gas_intel.baselines import verify_baseline
from gas_intel.continuity import compare_assignments, compare_months
from gas_intel.geography import DLSBox, profile_box
from gas_intel.history_profiling import profile_history
from gas_intel.reference_profiling import profile_reference


def audit_sources(root: Path) -> list[dict[str, object]]:
    """Fail on changed bytes or measured evidence; never refresh expectations."""
    evidence = root / "docs/evidence"
    results: list[dict[str, object]] = []

    def load(name: str) -> object:
        return json.loads((evidence / name).read_text())

    def source(digest: str) -> Path:
        path = root / "data/raw" / digest / "source.zip"
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Pinned source bytes changed: {digest}")
        return path

    def compare(name: str, actual: dict, expected: dict, keys: list[str]) -> None:
        for key in keys:
            if actual[key] != expected[key]:
                raise ValueError(f"Evidence mismatch: {name}.{key}")
        results.append({"check": name, "passed": True})

    baselines = load("known_month_baselines.json")
    for baseline in baselines:
        results.append(
            verify_baseline(
                source(baseline["source_sha256"]), baseline, root / "config/sources.yaml"
            )
        )
    reference_paths = {}
    for category in ["facilities", "operators", "operator_history"]:
        expected = load(f"reference_{category}.json")
        path = source(expected["source_sha256"])
        reference_paths[category] = path
        actual = profile_reference(path, category)
        compare(
            f"reference_{category}",
            actual,
            expected,
            [
                "source_sha256",
                "payload_sha256",
                "archive_lineage",
                "headers",
                "row_count",
                "key_fields",
                "distinct_keys",
                "blank_key_rows",
                "duplicate_extra_rows",
                "blank_counts",
            ],
        )
    expected_history = load("history_intervals.json")
    actual_history = profile_history(reference_paths["operator_history"])
    compare(
        "history_intervals",
        actual_history,
        expected_history,
        [
            "source_sha256",
            "row_count",
            "facility_count",
            "open_end_rows",
            "overlap_events",
            "gap_events",
        ],
    )
    expected_cross = load("cross_snapshot_checks.json")
    continuity = expected_cross["continuity"]
    actual_continuity = compare_months(
        source(continuity["source_sha256_previous"]),
        source(continuity["source_sha256_current"]),
        continuity["previous_month"],
        continuity["current_month"],
    )
    compare(
        "monthly_continuity",
        actual_continuity,
        continuity,
        [key for key in continuity if key != "interpretation"],
    )
    for expected in expected_cross["assignments"]:
        actual = compare_assignments(
            source(expected["volumetrics_sha256"]),
            expected["period"],
            reference_paths["operator_history"],
            reference_paths["facilities"],
        )
        compare(
            f"operator_assignment_{expected['period']}",
            actual,
            expected,
            ["period", "checks", "volumetrics_sha256", "history_sha256", "infrastructure_sha256"],
        )
    for expected in load("candidate_coverage.json"):
        actual = profile_box(
            source(expected["source_sha256"]), expected["period"], DLSBox(**expected["box"])
        )
        compare(f"candidate_coverage_{expected['period']}", actual, expected, list(expected))
    return results


def main() -> None:
    """Write audit results to stdout; never update evidence files or accepted exports."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    sys.stdout.write(json.dumps(audit_sources(args.root), indent=2) + "\n")


if __name__ == "__main__":
    main()

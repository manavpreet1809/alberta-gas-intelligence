"""Recheck independently reviewed source-wide baselines against pinned local bytes."""

import hashlib
import json
import tempfile
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

from gas_intel.ingestion.parsers import read_csv_payload
from gas_intel.profiling import profile_source

BASELINE_SQL = """SELECT count(*) AS source_rows,
 count(*) FILTER (WHERE ActivityID='PROD' AND ProductID='GAS') AS qualifying_rows,
 count(DISTINCT ReportingFacilityID)
 FILTER (WHERE ActivityID='PROD' AND ProductID='GAS') AS facilities,
 sum(try_cast(Volume AS DECIMAL(18,3)))
 FILTER (WHERE ActivityID='PROD' AND ProductID='GAS') AS volume_e3m3
 FROM read_csv(?, all_varchar=true, header=true)"""


def verify_baseline(source: Path, baseline: dict, contract: Path) -> dict[str, object]:
    """Check content/config hashes and independent Python/SQL totals; never update expectations."""
    if hashlib.sha256(source.read_bytes()).hexdigest() != baseline["source_sha256"]:
        raise ValueError("Source hash differs from reviewed baseline")
    if hashlib.sha256(contract.read_bytes()).hexdigest() != baseline["source_contract_sha256"]:
        raise ValueError("Source contract hash differs from reviewed baseline")
    schema = yaml.safe_load(contract.read_text())["volumetrics"]["expected_headers"]
    profile = profile_source(source, baseline["period"], schema)
    if profile["payload_sha256"] != baseline["payload_sha256"]:
        raise ValueError("CSV payload hash differs from reviewed baseline")
    gas = profile["gas_prod"]
    if gas["unresolved_volume_facility_count"] or gas["candidate_key_duplicate_extra_rows"]:
        raise ValueError("Baseline source has unresolved volumes or duplicate detail")
    expected = (
        baseline["source_rows"],
        baseline["qualifying_rows"],
        baseline["facilities"],
        Decimal(baseline["volume_e3m3"]),
    )
    actual_python = (
        profile["row_count"],
        gas["row_count"],
        gas["facility_count"],
        Decimal(gas["accepted_volume_sum_e3m3"]),
    )
    if actual_python != expected:
        raise ValueError("Python profile differs from reviewed counts/volume")
    payload, _ = read_csv_payload(source)
    with tempfile.TemporaryDirectory(prefix="gas-baseline-") as temporary:
        path = Path(temporary) / "source.csv"
        path.write_bytes(payload)
        with duckdb.connect() as connection:
            actual_sql = connection.execute(BASELINE_SQL, [str(path)]).fetchone()
    if actual_sql != expected:
        raise ValueError("Independent SQL differs from reviewed counts/volume")
    return {
        "period": baseline["period"],
        "passed": True,
        "checks": [
            "source hash",
            "source contract hash",
            "payload hash",
            "exact ordered schema",
            "accepted volumes",
            "detail uniqueness",
            "Python totals",
            "independent SQL totals",
        ],
    }


def main() -> None:
    """Verify all reviewed baselines using local content-addressed source snapshots."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baselines", type=Path, default=Path("docs/evidence/known_month_baselines.json")
    )
    parser.add_argument("--contract", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    results = []
    for baseline in json.loads(args.baselines.read_text()):
        source = args.raw_dir / baseline["source_sha256"] / "source.zip"
        results.append(verify_baseline(source, baseline, args.contract))
    # CLI result output, not pipeline logging.
    import sys

    sys.stdout.write(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()

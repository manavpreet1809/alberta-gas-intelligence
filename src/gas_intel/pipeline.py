"""Run a reproducible pilot warehouse from pinned monthly source selections."""

import hashlib
import json
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

from gas_intel.geography import DLSBox, profile_box
from gas_intel.history_profiling import month_number
from gas_intel.ingestion.download import acquire_month
from gas_intel.ingestion.parsers import read_csv_payload
from gas_intel.profiling import profile_source
from gas_intel.snapshot_selection import read_cohort
from gas_intel.validation.analytics import validate_analytics

LOGGER = logging.getLogger(__name__)

TABLES = {
    "dim_month": "core.dim_month",
    "dim_facility": "core.dim_facility",
    "dim_operator": "core.dim_operator",
    "facility_month": "core.facility_month",
    "fact_gas_production": "core.fact_gas_production",
    "monthly_area_production": "analytics.monthly_area_production",
    "operator_monthly_production": "analytics.operator_monthly_production",
    "data_quality_summary": "analytics.data_quality_summary",
    "operator_concentration": "analytics.operator_concentration",
    "facility_drivers": "analytics.facility_drivers",
}


INTERNAL_TABLES = [
    "core.selected_records",
    "core.excluded_records",
    "analytics.monthly_area_all",
    "analytics.operator_monthly_all",
]


def table_fingerprint(db: duckdb.DuckDBPyConnection, table: str) -> str:
    """Hash schema and the row multiset, retaining duplicates with bounded Python memory."""
    # Table names come only from the internal model contract, never CLI input.
    schema = db.execute(f"DESCRIBE {table}").fetchall()
    digest = hashlib.sha256(json.dumps(schema).encode())
    cursor = db.execute(
        f"SELECT sha256(to_json(record)) AS row_hash FROM {table} record ORDER BY row_hash"
    )
    while rows := cursor.fetchmany(8192):
        for (row_hash,) in rows:
            digest.update(row_hash.encode("ascii"))
    return digest.hexdigest()


def require_staging_integrity(db: duckdb.DuckDBPyConnection, info: dict) -> None:
    """Reject modified loaded rows before they can become a new accepted model."""
    if info.get("cohort_fingerprint") != table_fingerprint(db, "staging.cohort"):
        raise ValueError("Staging cohort integrity failed; reload the pinned sources")
    expected = info.get("staging_fingerprint")
    if not expected or table_fingerprint(db, "staging.volumetrics") != expected:
        raise ValueError("Staging snapshot integrity failed; reload the pinned sources")


def require_model_integrity(db: duckdb.DuckDBPyConnection, info: dict) -> None:
    """Check all exported model data and intermediate selection/exclusion lineage."""
    expected = info.get("table_fingerprints", {})
    tables = [*TABLES.values(), *INTERNAL_TABLES]
    for table in tables:
        if table not in expected or table_fingerprint(db, table) != expected[table]:
            raise ValueError(
                f"Built table snapshot integrity reconciliation failed: {table}; rebuild the model"
            )


def atomic_json(path: Path, value: object) -> None:
    """Replace metadata only after the complete JSON has been flushed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, encoding="utf-8"
        ) as file:
            temporary = Path(file.name)
            json.dump(value, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def configuration(root: Path) -> tuple[dict, str]:
    """Use the documented box as a working default, without fabricating human approval."""
    files = [root / "config" / f"{name}.yaml" for name in ["study_area", "sources", "codes"]]
    config_hash = hashlib.sha256(b"\0".join(path.read_bytes() for path in files)).hexdigest()
    study = yaml.safe_load(files[0].read_text())["candidate_proposal"]
    if month_number(study["end_month"]) - month_number(study["start_month"]) != 23:
        raise ValueError("Working study must specify exactly 24 analysis months")
    DLSBox(
        **{
            key: study[key]
            for key in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        }
    )
    codes = yaml.safe_load(files[2].read_text())
    if (
        codes.get("product") != "GAS"
        or codes.get("activity") != "PROD"
        or codes.get("volume_unit") != "e3m3"
    ):
        raise ValueError("This model requires the verified GAS/PROD/e3m3 contract")
    return study, config_hash


def database_path(root: Path) -> Path:
    """Return the local warehouse path without creating an empty database."""
    return root / "data/warehouse.duckdb"


def model_files(root: Path) -> list[Path]:
    """Resolve numbered source SQL files in deterministic layer order."""
    return [
        *sorted((root / "sql/core").glob("[0-9]*.sql")),
        *sorted((root / "sql/analytics").glob("[0-9]*.sql")),
    ]


def model_hash(root: Path) -> str:
    """Bind a built warehouse to the exact transformation code."""
    values = [path.read_bytes() for path in model_files(root)]
    values.append(Path(__file__).read_bytes())
    values.append((Path(__file__).parent / "snapshot_selection.py").read_bytes())
    values.append((Path(__file__).parent / "validation/analytics.py").read_bytes())
    return hashlib.sha256(b"\0".join(values)).hexdigest()


def load_sources(
    root: Path, months: list[str], *, offline: bool = False, cohort_artifact: Path | None = None
) -> dict:
    """Replace the selected staging snapshot atomically; preserve all raw source rows."""
    study, config_hash = configuration(root)
    artifact, artifact_hash = None, None
    if cohort_artifact is not None:
        artifact, artifact_hash = read_cohort(root, cohort_artifact, study, config_hash)
        if months:
            raise ValueError("Select either explicit months or a full-window cohort artifact")
        months = [artifact["context_month"], *artifact["analysis_months"]]
    if not months or len(set(months)) != len(months):
        raise ValueError("Supply unique explicit reporting months")
    months = sorted(months)
    if not any(study["start_month"] <= month <= study["end_month"] for month in months):
        raise ValueError("Load at least one analysis month; context alone is not a study")
    allowed_start = month_number(study["context_start_month"])
    allowed_end = month_number(study["end_month"])
    if any(not allowed_start <= month_number(month) <= allowed_end for month in months):
        raise ValueError("Requested month is outside the configured reporting/context window")
    box = DLSBox(
        **{
            key: study[key]
            for key in ["township_min", "township_max", "range_min", "range_max", "meridian"]
        }
    )
    headers = yaml.safe_load((root / "config/sources.yaml").read_text())["volumetrics"][
        "expected_headers"
    ]
    selections = []
    with tempfile.TemporaryDirectory(prefix="gas-load-") as temporary:
        for month in months:
            inventory_path = root / "data/verification" / f"{month}.json"
            if not inventory_path.exists():
                if offline:
                    raise FileNotFoundError(f"No pinned inventory for {month}; acquire it first")
                atomic_json(inventory_path, acquire_month(root, month))
            inventory = json.loads(inventory_path.read_text())
            event = inventory["event"]
            source = (root / event["source_file"]).resolve()
            if not source.is_relative_to((root / "data/raw").resolve()):
                raise ValueError("Pinned source must be inside data/raw")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest != event["sha256"]:
                raise ValueError(f"Pinned source hash mismatch for {month}")
            profile = profile_source(source, month, headers)
            LOGGER.info("Verified source %s: %s rows", month, profile["row_count"])
            if artifact is not None:
                baseline = next(
                    row for row in artifact["monthly_source_baselines"] if row["period"] == month
                )
                if (
                    digest != baseline["source_sha256"]
                    or profile["row_count"] != baseline["source_rows"]
                ):
                    raise ValueError(f"Pinned cohort source revision differs for {month}")
                scoped = {
                    "gas_prod_rows": baseline["cohort_gas_prod_rows"],
                    "accepted_volume_e3m3": baseline["cohort_volume_e3m3"],
                }
            else:
                scoped = profile_box(source, month, box)
                if scoped["invalid_selected_volume_rows"]:
                    raise ValueError(f"Unresolved selected volumes for {month}")
            payload, _ = read_csv_payload(source)
            csv_path = Path(temporary) / f"{month}.csv"
            csv_path.write_bytes(payload)
            selections.append(
                {
                    "month": month,
                    "source_file": str(source.relative_to(root.resolve())),
                    "sha256": digest,
                    "downloaded_at": event["downloaded_at"],
                    "source_rows": profile["row_count"],
                    "selected_rows": scoped["gas_prod_rows"],
                    "selected_volume": scoped["accepted_volume_e3m3"],
                    "csv_path": str(csv_path),
                }
            )
        info = {
            "run_id": str(uuid.uuid4()),
            "status": "loaded",
            "months": months,
            "configuration_hash": config_hash,
            "analysis_months": [month for month in months if month >= study["start_month"]],
            "context_months": [month for month in months if month < study["start_month"]],
            "cohort_artifact": str(cohort_artifact) if cohort_artifact is not None else None,
            "cohort_artifact_sha256": artifact_hash,
            "scope_status": "working_scope",
            "human_scope_approval_recorded": study.get("approved") is True,
            "cohort_policy": artifact["cohort_policy"]
            if artifact is not None
            else "fixed union of in-box facilities in the loaded analysis months",
            "pilot": sum(
                month_number(study["start_month"]) <= month_number(month) for month in months
            )
            < 24,
            "sources": [{k: v for k, v in item.items() if k != "csv_path"} for item in selections],
        }
        database_path(root).parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(database_path(root))) as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            db.execute("BEGIN")
            try:
                db.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
                db.execute("DROP SCHEMA IF EXISTS core CASCADE")
                db.execute("DROP SCHEMA IF EXISTS staging CASCADE")
                db.execute("CREATE SCHEMA staging")
                db.execute(
                    "CREATE TABLE staging.cohort (facility_id VARCHAR, township INT, "
                    "range INT, meridian INT)"
                )
                if artifact is not None:
                    db.executemany(
                        "INSERT INTO staging.cohort VALUES (?,?,?,?)",
                        [[row["facility_id"], *row["location"]] for row in artifact["facilities"]],
                    )
                info["cohort_fingerprint"] = table_fingerprint(db, "staging.cohort")
                for index, item in enumerate(selections):
                    mode = (
                        "CREATE TABLE staging.volumetrics AS"
                        if index == 0
                        else "INSERT INTO staging.volumetrics"
                    )
                    db.execute(
                        mode + " SELECT *, row_number() OVER () AS source_row_number, "
                        "? AS source_file, ? AS source_sha256, ? AS downloaded_at, ? AS "
                        "ingestion_run_id "
                        "FROM read_csv(?, all_varchar=true, header=true, parallel=false)",
                        [
                            item["source_file"],
                            item["sha256"],
                            item["downloaded_at"],
                            info["run_id"],
                            item["csv_path"],
                        ],
                    )
                info["staging_fingerprint"] = table_fingerprint(db, "staging.volumetrics")
                db.execute(
                    "CREATE OR REPLACE TABLE staging.run_info AS SELECT ? AS metadata",
                    [json.dumps(info)],
                )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
    return info


def read_info(db: duckdb.DuckDBPyConnection) -> dict:
    """Require a loaded snapshot instead of accepting an empty database."""
    try:
        return json.loads(db.execute("SELECT metadata FROM staging.run_info").fetchone()[0])
    except duckdb.Error as exc:
        raise ValueError("Run gas-intel load first") from exc


def open_existing(root: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Fail without creating files when no warehouse has been loaded."""
    if not database_path(root).exists():
        raise FileNotFoundError("Run gas-intel load first; no warehouse exists")
    db = duckdb.connect(str(database_path(root)), read_only=read_only)
    db.execute("SET memory_limit='1GB'")
    db.execute("SET threads=2")
    return db


def build_model(root: Path) -> dict:
    """Build monthly core/analytics tables with hard data-grain checks in one transaction."""
    study, digest = configuration(root)
    with open_existing(root) as db:
        info = read_info(db)
        if info["configuration_hash"] != digest:
            raise ValueError("Configuration changed; reload the selected sources")
        db.execute("BEGIN")
        try:
            require_staging_integrity(db, info)
            db.execute(
                "CREATE OR REPLACE TEMP TABLE pipeline_settings AS SELECT ?::INT "
                "township_min, ?::INT township_max, ?::INT range_min, ?::INT range_max, "
                "?::INT meridian, ?::VARCHAR start_month, ?::VARCHAR end_month",
                [
                    *[
                        study[key]
                        for key in [
                            "township_min",
                            "township_max",
                            "range_min",
                            "range_max",
                            "meridian",
                        ]
                    ],
                    study["start_month"],
                    study["end_month"],
                ],
            )
            for path in model_files(root):
                db.execute(path.read_text())
            if info.get("cohort_artifact_sha256"):
                cohort_errors = db.execute("""
                    SELECT count(*) FROM (
                        (SELECT facility_id FROM candidate_cohort
                         EXCEPT SELECT facility_id FROM staging.cohort)
                        UNION ALL
                        (SELECT facility_id FROM staging.cohort
                         EXCEPT SELECT facility_id FROM candidate_cohort)
                    )
                """).fetchone()[0]
                location_errors = db.execute("""
                    SELECT count(*) FROM staging.cohort s
                    JOIN core.dim_facility d USING(facility_id)
                    WHERE s.township IS DISTINCT FROM d.township OR s.range IS DISTINCT FROM d.range
                       OR s.meridian IS DISTINCT FROM d.meridian
                """).fetchone()[0]
                if cohort_errors or location_errors:
                    raise ValueError("Frozen cohort does not match analysis-month source evidence")
            invalid = db.execute(
                "SELECT count(*) FROM core.selected_records WHERE "
                "NOT coalesce(regexp_full_match(trim(Volume), "
                "'[+-]?[0-9]+(\\.[0-9]{1,3})?'), false) "
                "OR volume_value IS NULL OR volume_value < 0"
            ).fetchone()[0]
            duplicates = db.execute(
                "SELECT count(*) FROM (SELECT ProductionMonth, ReportingFacilityID, "
                "FromToID FROM core.selected_records GROUP BY ALL HAVING count(*) > 1)"
            ).fetchone()[0]
            conflicts = db.execute(
                "SELECT count(*) FROM (SELECT s.ProductionMonth, s.ReportingFacilityID "
                "FROM staging.volumetrics s JOIN core.dim_facility d ON "
                "s.ReportingFacilityID=d.facility_id GROUP BY ALL HAVING count(DISTINCT "
                "coalesce(OperatorBAID,''))>1)"
            ).fetchone()[0]
            locations = db.execute(
                "SELECT count(*) FROM staging.volumetrics s JOIN core.dim_facility d ON "
                "s.ReportingFacilityID=d.facility_id WHERE try_cast(FacilityTownship AS "
                "INT) IS DISTINCT FROM d.township OR try_cast(FacilityRange AS INT) IS "
                "DISTINCT FROM d.range OR try_cast(FacilityMeridian AS INT) IS DISTINCT "
                "FROM d.meridian"
            ).fetchone()[0]
            if invalid or duplicates or conflicts or locations:
                raise ValueError(
                    f"Core data checks failed: invalid={invalid}, duplicate={duplicates}, "
                    f"operator_conflict={conflicts}, location_conflict={locations}"
                )
            info.update(
                status="built",
                model_hash=model_hash(root),
                table_fingerprints={
                    table: table_fingerprint(db, table)
                    for table in [
                        *TABLES.values(),
                        *INTERNAL_TABLES,
                    ]
                },
            )
            db.execute("UPDATE staging.run_info SET metadata=?", [json.dumps(info)])
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
    return info


def validate_warehouse(root: Path) -> dict:
    """Reconcile the current warehouse in a consistent read transaction."""
    with open_existing(root, read_only=True) as db:
        db.execute("BEGIN")
        return validate_connection(root, db)


def validate_connection(root: Path, db: duckdb.DuckDBPyConnection) -> dict:
    """Validate one database snapshot; caller owns the read transaction."""
    _, digest = configuration(root)
    info = read_info(db)
    if info["status"] != "built" or info.get("model_hash") != model_hash(root):
        raise ValueError("Build the current transformation model before validation")
    if info["configuration_hash"] != digest:
        raise ValueError("Configuration changed since loading")
    require_staging_integrity(db, info)
    if info.get("cohort_artifact"):
        _, artifact_hash = read_cohort(
            root, Path(info["cohort_artifact"]), configuration(root)[0], digest
        )
        if artifact_hash != info["cohort_artifact_sha256"]:
            raise ValueError("Cohort artifact changed after loading")
    checks = []
    for source in info["sources"]:
        path = root / source["source_file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Pinned raw source changed after loading")
        month = source["month"]
        actual_rows = db.execute(
            "SELECT count(*) FROM staging.volumetrics WHERE ProductionMonth=?", [month]
        ).fetchone()[0]
        selected_rows, staging_volume = db.execute(
            "SELECT count(*), coalesce(sum(try_cast(Volume AS DECIMAL(13,3))),0) FROM"
            " staging.volumetrics s JOIN core.dim_facility d ON "
            "s.ReportingFacilityID=d.facility_id WHERE ProductionMonth=? AND "
            "ActivityID='PROD' AND ProductID='GAS'",
            [month],
        ).fetchone()
        fact_rows, core_volume = db.execute(
            "SELECT coalesce(sum(source_record_count),0), coalesce(sum(volume),0) "
            "FROM core.fact_gas_production WHERE month=?",
            [month],
        ).fetchone()
        area = db.execute(
            "SELECT volume FROM analytics.monthly_area_all WHERE month=?", [month]
        ).fetchone()
        operator_volume = db.execute(
            "SELECT coalesce(sum(volume),0) FROM analytics.operator_monthly_all WHERE month=?",
            [month],
        ).fetchone()[0]
        excluded = db.execute(
            "SELECT count(*) FROM core.excluded_records WHERE month=?", [month]
        ).fetchone()[0]
        expected_volume = Decimal(source["selected_volume"])
        passed = (
            actual_rows == source["source_rows"]
            and selected_rows == source["selected_rows"] == fact_rows
            and excluded + selected_rows == actual_rows
            and area is not None
            and expected_volume == staging_volume == core_volume == area[0] == operator_volume
        )
        if not passed:
            raise ValueError(f"Source/staging/core/analytics reconciliation failed for {month}")
        checks.append(
            {
                "month": month,
                "passed": True,
                "volume_e3m3": str(core_volume),
                "selected_rows": selected_rows,
            }
        )
    duplicates = db.execute(
        "SELECT count(*) FROM (SELECT facility_id,month FROM core.facility_month "
        "GROUP BY ALL HAVING count(*)<>1)"
    ).fetchone()[0]
    spine_count = db.execute("SELECT count(*) FROM core.facility_month").fetchone()[0]
    expected_spine = db.execute(
        "SELECT (SELECT count(*) FROM core.dim_facility)*(SELECT count(*) FROM core.dim_month)"
    ).fetchone()[0]
    if duplicates or spine_count != expected_spine:
        raise ValueError("Facility-month spine cardinality failed")
    operator_errors = db.execute("""
        WITH source_totals AS (
            SELECT ProductionMonth AS month,
                   coalesce(nullif(OperatorBAID,''),'UNKNOWN') AS operator_id,
                   sum(try_cast(Volume AS DECIMAL(13,3))) AS volume
            FROM staging.volumetrics s JOIN core.dim_facility d
            ON s.ReportingFacilityID=d.facility_id
            WHERE ActivityID='PROD' AND ProductID='GAS' GROUP BY ALL
        ), fact_totals AS (
            SELECT month,operator_id,sum(volume) AS volume
            FROM core.fact_gas_production GROUP BY ALL
        ), keys AS (
            SELECT month,operator_id FROM source_totals UNION
            SELECT month,operator_id FROM fact_totals UNION
            SELECT month,operator_id FROM analytics.operator_monthly_all
        )
        SELECT count(*) FROM keys k
        LEFT JOIN source_totals s USING(month,operator_id)
        LEFT JOIN fact_totals f USING(month,operator_id)
        LEFT JOIN analytics.operator_monthly_all a USING(month,operator_id)
        WHERE coalesce(s.volume,0)<>coalesce(f.volume,0)
           OR coalesce(f.volume,0)<>coalesce(a.volume,0)
    """).fetchone()[0]
    if operator_errors:
        raise ValueError("Historical operator reconciliation failed")
    for table, key in [
        ("core.dim_operator", "operator_id"),
        ("core.dim_facility", "facility_id"),
        ("core.dim_month", "month"),
        ("core.fact_gas_production", "facility_id,month"),
    ]:
        duplicates = db.execute(
            f"SELECT count(*) FROM (SELECT {key} FROM {table} GROUP BY ALL HAVING count(*)>1)"
        ).fetchone()[0]
        if duplicates:
            raise ValueError(f"Duplicate model key: {table}")
    state_errors = db.execute("""
        SELECT count(*) FROM core.facility_month fm
        LEFT JOIN core.fact_gas_production f USING(facility_id,month)
        WHERE fm.volume IS DISTINCT FROM f.volume
           OR fm.report_status <> CASE WHEN f.facility_id IS NULL THEN 'no_qualifying_row'
                                  WHEN f.volume=0 THEN 'reported_zero' ELSE 'reported_volume' END
    """).fetchone()[0]
    if state_errors:
        raise ValueError("Facility reporting-state reconciliation failed")
    require_model_integrity(db, info)
    analytics_checks = validate_analytics(db)
    return {
        "run_id": info["run_id"],
        "passed": True,
        "snapshot_integrity": {
            "algorithm": "sha256_schema_and_sorted_row_hashes_v1",
            "staging_fingerprint": info["staging_fingerprint"],
            "table_fingerprints": info["table_fingerprints"],
        },
        "checks": checks,
        "analytics_checks": analytics_checks,
        "cohort_facilities": expected_spine // len(info["months"]),
        "scope_status": info["scope_status"],
        "pilot": info["pilot"],
        "analysis_months": info["analysis_months"],
        "context_months": info["context_months"],
        "cohort_artifact_sha256": info["cohort_artifact_sha256"],
        "configuration_hash": info["configuration_hash"],
        "model_hash": info["model_hash"],
        "source_sha256_by_month": {item["month"]: item["sha256"] for item in info["sources"]},
        "warnings": {
            "unknown_operator_fact_rows": db.execute(
                "SELECT count(*) FROM core.fact_gas_production WHERE operator_id='UNKNOWN'"
            ).fetchone()[0],
            "absent_qualifying_facility_months": db.execute(
                "SELECT count(*) FROM core.facility_month WHERE report_status='no_qualifying_row'"
            ).fetchone()[0],
        },
    }


def export_tables(root: Path) -> Path:
    """Always revalidate; publish a new immutable export bundle before changing latest metadata."""
    parent = root / "data/exports"
    export_id = str(uuid.uuid4())
    temporary = parent / f".pending-{export_id}"
    published = parent / export_id
    files = {}
    with open_existing(root, read_only=True) as db:
        db.execute("BEGIN")
        validation = validate_connection(root, db)
        info = read_info(db)
        parent.mkdir(parents=True, exist_ok=True)
        temporary.mkdir()
        for name, table in TABLES.items():
            for extension, format_ in [("csv", "CSV, HEADER true"), ("parquet", "PARQUET")]:
                path = temporary / f"{name}.{extension}"
                selection = f"SELECT * FROM {table}"
                if table in {"core.dim_month", "core.fact_gas_production", "core.facility_month"}:
                    selection += (
                        " WHERE month IN (SELECT month FROM core.dim_month WHERE is_analysis)"
                    )
                db.execute(
                    f"COPY ({selection} ORDER BY ALL) TO ? (FORMAT {format_})",
                    [str(path)],
                )
                files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    bundle = {
        "export_id": export_id,
        "run": info,
        "validation": validation,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "files_sha256": files,
    }
    atomic_json(temporary / "manifest.json", bundle)
    os.rename(temporary, published)
    atomic_json(
        parent / "latest.json",
        {
            "export_id": export_id,
            "path": str(published.relative_to(root)),
            "run_id": info["run_id"],
        },
    )
    return published


def run_pipeline(
    root: Path, months: list[str], *, offline: bool = False, cohort_artifact: Path | None = None
) -> Path:
    """Load, build, validate and export the explicit selection with no skipped checks."""
    load_sources(root, months, offline=offline, cohort_artifact=cohort_artifact)
    build_model(root)
    return export_tables(root)

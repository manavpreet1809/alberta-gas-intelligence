# Alberta Gas Production Intelligence Platform

A planned Python, SQL, DuckDB and Power BI pipeline to examine changes in publicly
reported natural gas production for facilities in Alberta's Kakwa area.

**Status: Stage 2 source verification in progress.** Two real monthly extracts
have been profiled locally; no warehouse, dashboard or analytical findings exist yet. Source interpretation, the exact DLS
study boundary and fixed 24-month window remain subject to M1 verification.

```mermaid
flowchart LR
    A[Petrinex files] --> B[Immutable raw snapshots]
    B --> C[DuckDB staging]
    C --> D[Core model]
    D --> E[Analytics]
    E --> F[Validation]
    F --> G[CSV and Parquet]
    G --> H[Power BI]
```

## Setup

Use Python 3.11 or newer. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
gas-intel --help
gas-intel doctor
pytest
ruff check .
ruff format --check .
```

`doctor` checks runtime and YAML template readability only. It explicitly reports
that source contracts remain unverified. `doctor --require-sources` fails until
a later milestone implements real contract verification. Use `--config-dir` to
check a different configuration directory.

`load`, `build`, `validate`, `export` and `run-all` remain honest stubs:
they exit with code 2 and perform no pipeline work. No warehouse creation or
analytical export is implemented yet. Explicit source-verification acquisition is
available through `gas-intel download --verification-month YYYY-MM`; see
[acquisition and revision handling](docs/acquisition.md).

## Next stage

Complete Stage 2 using the [source checklist](docs/m1_checklist.md), then deliver
the first working month in Stage 3 before expanding to 24 months. See [PLAN.md](PLAN.md) and
[AGENTS.md](AGENTS.md) for the bridge definitions and acceptance requirements.

Missing rows do not establish zero output or physical shut-in. Reporting-month
operators do not establish asset ownership. Source revisions must be retained;
raw data, local warehouses and generated bulk exports are excluded from Git.
Power BI is built manually from validated exports in a later milestone.


## Verified source profiling

January and February 2025 official downloads have been inspected and independently
cross-checked. See [source verification](docs/source_verification.md) for exact
counts, hashes, observed schema and remaining decisions. These are province-wide
source checks, not approved Kakwa totals. Raw files remain local and ignored by Git.

```bash
python -m gas_intel.profiling data/raw/<sha256>/source.zip \
  --month 2025-01 --output data/processed/profile_2025-01.json
```

The profiler reads plain CSV or the observed two nested ZIP layers without extracting
member paths. It preserves identifiers, reports blanks/invalid volumes and candidate
key duplicates, and performs no network calls or production pipeline operations.
Use notebooks/01_source_profiling.ipynb to reproduce the evidence and independent SQL
cross-check against pinned local source files. Fixture values in tests are invented;
source headers match observed downloads. Crown copyright acknowledged: Government
of Alberta, Petrinex public data. Source use remains subject to provider terms.

Recheck the reviewed, source-wide regression baselines offline:

```bash
python -m gas_intel.baselines
```

This fails on source/configuration/payload hash changes, schema drift, unresolved
selected volumes, duplicate detail, or count/volume mismatches. It never silently
updates expected values. CI uses independently specified synthetic expectations;
full-source verification needs the pinned local downloads.

Use `gas-intel doctor --details` for a Stage 2 evidence summary. It distinguishes
missing evidence, failed reference key checks, pinned baseline configuration and
pending scope/cohort decisions. This summary does not rerun the full-source verifier
and cannot certify source contracts. `--require-sources` continues to fail while
Stage 2 is incomplete.

Run the integrated Stage 2 audit against all five pinned local downloads:

```bash
python -m gas_intel.source_audit
gas-intel doctor --details
```

The audit rechecks monthly regressions, reference schemas/keys, history intervals,
monthly continuity, operator assignments and candidate-box coverage. It makes no
network requests, never overwrites evidence, and does not publish pipeline exports.
The proposed study box and dates remain unapproved; passing this audit alone does
not finish Stage 2. See [scope proposal](docs/study_scope_proposal.md) and
[reference contracts](docs/reference_contracts.md).

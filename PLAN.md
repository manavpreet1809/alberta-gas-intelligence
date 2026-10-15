# PLAN.md — Alberta Gas Production Intelligence Platform

Build the project milestone by milestone.

Do not work ahead.

Before every milestone:

1. Read `AGENTS.md`.
2. Read this file.
3. Read the relevant existing documentation.
4. Implement only the current milestone.
5. Run tests.
6. Run ruff.
7. Update documentation.
8. Summarize changes.

`🧑 HUMAN GATE` means Codex must stop until the human completes or verifies something.

Expected total duration:

An estimate only; source discovery and manual dashboard work determine duration.


# Milestone overview

| Milestone | Purpose |
|---|---|
| M0 | Repository foundation |
| M1 | Verify Petrinex sources and meaning |
| M1S | One-month end-to-end slice and first visual |
| M2 | Download + manifest |
| M3 | Staging layer |
| M4 | Core analytical model |
| M5 | Production bridge |
| M6 | Validation |
| M7 | Exports + full pipeline |
| M8 | Power BI + findings |
| M9 | Portfolio polish |


# M0 — Repository foundation

Status: implemented locally; CLI behavior tests and Ruff checks pass.
Source verification remains pending in M1.

## Goal

Create a clean, runnable project structure without implementing business logic.


## Required work

Create:

- project folders
- Python package
- `pyproject.toml`
- CLI
- config templates
- test structure
- GitHub Actions
- placeholder docs


## Required CLI stubs

```text
doctor
download
load
build
validate
export
run-all
```


## Acceptance criteria

```bash
pip install -e ".[dev]"
```

works.

```bash
gas-intel --help
```

shows commands.

```bash
pytest
```

passes.

```bash
ruff check .
ruff format --check .
```

pass.

GitHub Actions runs:

- pytest
- ruff

Do not implement Petrinex logic.


## Codex prompt

> Read AGENTS.md and PLAN.md. Implement M0 only. Create the repository structure defined in AGENTS.md, configure Python 3.11+, create pyproject.toml with runtime and development dependencies, create the gas-intel Typer CLI with stub commands doctor, download, load, build, validate, export and run-all, create placeholder YAML configuration files containing TODO(human) markers rather than invented values, add pytest and ruff configuration, create one placeholder test, and create a GitHub Actions workflow running pytest and ruff. Do not implement Petrinex-specific data logic. Run pytest and ruff and report results.


# M1 — Petrinex source verification 🧑 HUMAN GATE

## Goal

Understand exactly what the source data means before implementing transformations.

This is the most important accuracy milestone.


## Human tasks

Codex may research and profile official public downloads. Human verification is required for the frozen geography, analysis window and any unresolved material source interpretation; do not shift all source research to the human.

Acquire representative files for:

1. volumetrics
2. facility/reference data
3. business associate/operator data
4. operator history/effective-date data if separate
5. official codes/reference documentation

Initially download only 2–3 representative months.

Place the files in:

```text
data/raw/
```

Copy 20–50 representative rows from each file into:

```text
tests/fixtures/
```

Keep the real headers.


## Update

`config/sources.yaml`

with verified source URLs or file patterns.

No guessed URLs.


# M1A — Source profiling

Codex builds:

`notebooks/01_source_profiling.ipynb`


## Profile each file

Report:

- file name
- row count
- columns
- inferred types
- null rate
- date/reporting period range
- candidate keys
- duplicate counts
- code-like columns
- activity codes
- product codes
- units
- facility types
- facility subtypes
- business associate/operator fields
- township
- range
- meridian
- location fields
- possible operator effective-date fields


## Create

`docs/data_dictionary.md`

Include:

- source file
- column
- observed type
- sample value
- likely purpose
- verified meaning
- uncertainty


Never infer code meanings from code names alone.


## Codex prompt

> Read AGENTS.md. Work only on M1 source profiling. Inspect the real fixtures in tests/fixtures/ and any source files already placed in data/raw/. Build notebooks/01_source_profiling.ipynb. For every source, report columns, inferred types, row count, null rates, distinct values for code-like columns, candidate keys and uniqueness, reporting-month ranges, facility-location fields, operator-related fields and units. Draft docs/data_dictionary.md from observed evidence. Mark uncertain meanings as TODO(human): verify. Do not invent activity, product, facility-type or unit meanings.


# M1B — Human methodology decision gate 🧑

The human must answer every question below.

Record the verified answers in:

`docs/methodology.md`

and configuration.


## Required questions

### Grain

What does one volumetric row represent?

Example format:

```text
one reporting month × facility × product × activity
```

But use the actual verified grain.


### Activity

Which exact activity code means production?


### Product

Which exact code means natural gas?


### Unit

What unit is gas reported in?


### Facilities

Which facility types legitimately report production?

Which facility types only receive/move/process production?


### Operator

How is the operator associated with each reporting month?


### Geography

Which Petrinex fields identify:

- township
- range
- meridian

Define the initial Kakwa bounding box.


### Time window

Choose exactly 24 months.


### Coverage

Calculate rough counts for:

- facilities
- operators

Target enough data to support meaningful analysis.

Aim for approximately 10+ operators where possible.


## Stop condition

Do not continue if:

- production code is unknown
- natural-gas code is unknown
- unit is unknown
- operator assignment is unknown
- facility location is unknown

Widen the geography or switch to the Deep Basin only with human approval.


# M1S — One-month vertical slice

After M1 exit criteria pass, implement the minimum reusable portions of M2–M7
needed to move one pinned month through raw → staging → core → analytics →
validation → exports. This is an explicit exception to the original instruction
not to work ahead; do not create a parallel throwaway pipeline.

Scope:
- One verified month, frozen study cohort, GAS/PROD metric and monthly operator.
- Immutable hashed source, run manifest, source lineage and exact monthly totals.
- One area total and operator totals, with counts and UNKNOWN share.
- CLI validation before export and a documented Power BI import/model contract.
- One human-built Power BI visual of production by operator, reconciled to exports.

Acceptance: independent source-to-core-to-analytics totals reconcile, reruns do
not duplicate data, invalid inputs block export, and the visual agrees with the
validated table. Record an honest demo status if the human visual is pending.
One month cannot establish MoM change or a production bridge. Add a second
consecutive verified month before demonstrating change; do not invent a baseline.

Then complete M2–M7 by extending these same components to the fixed 24-month
window, full bridge, reference handling and validation coverage. Source contracts
remain mandatory; early delivery does not relax correctness requirements.

# M1 hard exit criteria

Complete docs/m1_checklist.md with evidence. All material source contracts must
be verified; unresolved material questions block dependent implementation.
Document revision behavior that is known, and explicitly identify what the
provider does not establish. Do not invent a maximum revision horizon.

# M2 — Download and source manifest

## Goal

Create a reproducible ingestion process.


## Required functionality

`gas-intel download`

reads:

`config/sources.yaml`

and downloads files for the configured window.


## Download process

For each source:

1. create ingestion run ID
2. download to temporary file
3. enforce timeout
4. retry a small fixed number of times
5. verify non-empty
6. verify expected structure/header
7. calculate SHA-256
8. compare with existing file/hash
9. store valid file at a new content-addressed raw path, retaining earlier revisions
10. update manifest


## Manifest

Create:

`data/raw/manifest.csv`

Fields:

```text
ingestion_run_id
source_name
file_name
url
reporting_period
downloaded_at
bytes
sha256
row_count
status
```


Possible statuses:

```text
downloaded
unchanged
failed
invalid
```


## Tests

Mock network requests.

Required tests:

- successful download
- timeout
- retry
- empty response
- wrong header
- unchanged hash
- failed download does not overwrite good file


## Acceptance criteria

Re-downloading identical data produces no duplicate or destructive change.


## Codex prompt

> Read AGENTS.md, PLAN.md, config/sources.yaml and docs/data_dictionary.md. Implement M2 only. Build the download and manifest components under src/gas_intel/ingestion/. All URLs and file patterns must come from verified config/sources.yaml. Use timeouts, limited retries, temporary files, expected-header validation, SHA-256 hashing and atomic moves. Create data/raw/manifest.csv with the required fields. Never overwrite a valid existing file with an invalid download. Mock network calls in tests. Run pytest and ruff.


# M3 — Staging layer

## Goal

Load raw source files into DuckDB with minimal transformation.


## Required database

`data/warehouse.duckdb`

Schema:

`staging`


## Staging tables

Names must be based on verified sources.

Expected categories:

```text
staging.volumetrics
staging.facilities
staging.operators
staging.operator_history
```

Only create tables supported by actual files.


## Transformations allowed

Only:

- snake_case column names
- explicit type normalization where verified
- IDs to strings
- provenance columns


## Required provenance

Each staging row:

```text
source_file
downloaded_at
ingestion_run_id
```


## Idempotency

Reloading the same source file must not duplicate records.


## Tests

- source row count equals staged row count
- leading zeros remain
- provenance populated
- rerun does not duplicate
- malformed records handled according to documented policy


## Codex prompt

> Read AGENTS.md, docs/data_dictionary.md and docs/methodology.md. Implement M3 only. Load verified raw files into the DuckDB staging schema using numbered SQL files and the SQL runner. Preserve source structure except snake_case names and verified types. Treat all identifiers as strings. Add provenance fields to every row. Make reloads idempotent per selected source hash/member. Add tests for source/staging row counts, leading-zero IDs, provenance and reruns. Do not implement analytical business logic yet.


# M4 — Core analytical model

## Goal

Create trustworthy tables at clearly documented grains.


# Required core tables

## `core.dim_month`

One row per month.

Fields:

```text
month
year
quarter
month_number
```


## `core.dim_facility`

One row per facility.

Include verified fields such as:

```text
facility_id
facility_name
facility_type
facility_subtype
township
range
meridian
in_study_area
```


## `core.dim_operator`

One row per operator/business associate.

Include:

```text
operator_id
operator_name
```


## `core.facility_month`

One row per:

```text
facility × month
```

for study-area facilities.

Include:

```text
facility_id
month
operator_id
report_status
```

`report_status` must be exactly:

```text
reported_volume
reported_zero
no_qualifying_row
```


## `core.fact_gas_production`

Grain:

Use the verified grain from methodology.

At minimum:

```text
month
facility_id
operator_id
volume
unit
```


Filter:

- study area only
- natural gas only
- production activity only
- configured 24-month window


## `core.excluded_records`

Track exclusions.

Possible reasons:

```text
outside_study_area
outside_window
wrong_activity
wrong_product
invalid_record
```


## Historical operator assignment

Operator must correspond to the reporting month.

Use the verified methodology.

Never use current operator for old production unless the source methodology proves that is correct.


## Acceptance tests

### Reconciliation

For every month:

```text
filtered staging gas-production volume
=
core fact gas-production volume
```


### Join safety

No core join may increase fact rows unexpectedly.


### Facility month

Synthetic tests must prove distinction between:

- volume
- zero
- missing report


### Operator changes

Synthetic facility changes from operator A to operator B.


## Codex prompt

> Read AGENTS.md, docs/data_dictionary.md, docs/methodology.md and all config files. Implement M4 only using numbered SQL files in sql/core/. Create the month, facility and operator dimensions, the facility-month reporting spine, the gas-production fact and excluded-record reporting. Apply only codes explicitly defined in config/codes.yaml. Apply only the area/window in config/study_area.yaml. Assign operators according to the historical monthly methodology. Preserve reported-volume, reported-zero and not-reported as distinct states. Add tests for historical operator changes, all three report states, no row multiplication, excluded-record counts and monthly staging-to-core volume reconciliation.


# M5 — Production bridge and analytics

## Goal

Answer the central business question.


# M5A — Facility bridge

Create:

`analytics.facility_bridge_monthly`

Grain:

```text
facility × month_transition
```


Fields should include:

```text
facility_id
month_previous
month_current
operator_previous
operator_current
volume_previous
volume_current
status_previous
status_current
continuing_change_change
transfer_in
transfer_out
first_observed_positive
returning_positive_volume
to_reported_zero_change
absent_production_row_change
actual_change
```


Use the authoritative bridge rules in `AGENTS.md`.


# M5B — Operator bridge

Create:

`analytics.operator_bridge_monthly`

Include:

```text
month
operator_id
operator_name
continuing_change
transfer_in
transfer_out
first_observed_positive
returning_positive
to_reported_zero
absent_production_row
bridge_change
actual_change
reconciliation_difference
```


Requirement:

```text
reconciliation_difference = 0
```


# M5C — Area bridge

Create:

`analytics.area_bridge_monthly`

Transfers must net to zero.


# M5D — Additional analytics

Create:

## `analytics.monthly_area_production`

- month
- production
- MoM change
- MoM %
- YoY change
- YoY %
- reporting facilities


## `analytics.operator_monthly_production`

- month
- operator
- volume
- share
- MoM change


## `analytics.operator_concentration`

- top-1 share
- top-3 share
- top-5 share
- HHI


## `analytics.facility_drivers`

Largest increases/decreases.


## `analytics.operator_transfers`

Facility transfers between operators.


# Required synthetic cases

1. continuing_change increase
2. continuing_change decrease
3. same-volume operator transfer
4. transfer + increased production
5. transfer + decreased production
6. first observed positive facility
7. returning_positive facility
8. transition to reported zero
9. have no qualifying production row


# Critical tests

For every operator/month:

```text
bridge_change = actual_change
```

For every area/month:

```text
area_bridge = actual_area_change
```

Transfers:

```text
sum(area transfer_in + transfer_out) = 0
```

Multi-month:

```text
sum(monthly bridges)
=
end period production - start period production
```


## Codex prompt

> Read AGENTS.md carefully, especially the authoritative Production Bridge definition. Read docs/methodology.md. Implement M5 only. Build the facility-level monthly bridge first, then aggregate it into operator and area bridges. Build the additional analytics views listed in PLAN.md. Create synthetic fixtures covering continuing_change increases/decreases, reported operator changes with and without simultaneous volume changes, first observed positive facilities, returning_positive facilities, transitions to reported zero and have no qualifying production row. Add tests proving exact operator reconciliation, exact area reconciliation, transfer net-zero behavior and multi-month reconciliation. Document every analytical measure in dashboard/measures.md.


# M6 — Validation framework

## Goal

Make it easy to prove the analytical outputs are trustworthy.


# Hard failures

The CLI exits non-zero for:

- duplicate fact keys
- staging/core reconciliation failure
- core/analytics reconciliation failure
- production bridge reconciliation failure
- unexpected row multiplication
- invalid required config


# Warnings

Report but do not fail on:

- facility-month with no qualifying production row
- missing operator
- extreme MoM movement
- source manifest anomaly
- unexpected source code
- potentially incomplete/revised recent month


# Configuration

Thresholds go in:

`config/validation.yaml`


# Output

Generate:

```text
data/exports/data_quality_summary.parquet
docs/data_quality_report.md
```


The markdown report should explain:

- check
- severity
- result
- count
- examples
- recommended action


## Codex prompt

> Read AGENTS.md and implement M6 only. Build the validation framework under src/gas_intel/validation/. Hard failures must return a non-zero CLI exit status. Warnings must be included in the report but must not fail the pipeline. Write data/exports/data_quality_summary.parquet and docs/data_quality_report.md. Add a fixture-driven test for every validation rule. Run pytest and ruff.


# M7 — Export and full pipeline

## Goal

Run the entire analytical workflow with one command.


# `gas-intel export`

Export every final analytics table as:

```text
CSV
Parquet
```

to:

`data/exports/`


# `gas-intel run-all`

Execute:

```text
doctor
download
load
build
validate
export
```

in the correct order.


## Failure behavior

Stop immediately on hard failure.

Return non-zero CLI exit code.


## End-to-end test

CI must run an end-to-end pipeline using fixtures only.


## README draft

At this milestone create the first complete README.

Include:

- project purpose
- business question
- architecture diagram
- study area
- source description
- pipeline
- data model
- production bridge explanation
- validation
- how to run
- outputs
- limitations


## Codex prompt

> Read AGENTS.md and implement M7 only. Implement gas-intel export and gas-intel run-all. Export all final analytics views and the data-quality summary as CSV and Parquet. Add a complete fixture-based end-to-end test. Ensure the pipeline stops on validation hard failures. Draft the complete README with a Mermaid architecture diagram, setup instructions, data model explanation, production bridge explanation, outputs and limitations. Run pytest and ruff.


# M8 — Power BI and findings 🧑 HUMAN GATE

Codex does not build the `.pbix`.

The human builds Power BI manually.


# Dashboard page 1 — Area Overview

Include:

## KPI cards

- current-period production
- MoM change
- YoY change
- reporting facilities
- operator count
- source download date


## Charts

- monthly gas production
- MoM/YoY trend
- top operators
- operator shares


## Optional

- top-5 concentration
- HHI trend


# Dashboard page 2 — Operator Drivers

Filters:

- operator
- start month
- end month


Include:

## Waterfall

Production bridge:

```text
starting production
continuing reported-volume change
transfer in
transfer out
first_observed_positive
returning_positive
transition to reported zero
have no qualifying production row
ending production
```


Also show:

- selected operator trend
- production share
- largest facility drivers


Main question:

> Did production change because existing assets performed differently or because facilities changed operator?


# Dashboard page 3 — Data Quality / Facility Detail

Include:

- largest increasing facilities
- largest decreasing facilities
- reported operator changes
- missing reporting
- unassigned operators
- excluded-record counts
- reconciliation status


# DAX

After exported tables exist, ask Codex:

> Read AGENTS.md, dashboard/measures.md and the schemas of all files in data/exports/. Draft the DAX measures needed for the three Power BI pages in PLAN.md. Save them in dashboard/dax_measures.md. Do not invent columns. Explain the purpose of each measure.


# Findings brief

Create:

`docs/findings.md`

Maximum approximately two pages.

Include exactly three primary findings.

For each:

```text
Finding
Evidence
Business interpretation
Limitation
```


Example structure:

```text
Finding 1:
Operator X accounted for Y% of the area's MoM increase.

Evidence:
...

Interpretation:
...

Limitation:
...
```


Do not write claims unsupported by analytics outputs.


# Findings review prompt

> Read AGENTS.md, docs/findings.md and the final analytics tables. Review each finding for factual support. Identify any statement that is not directly supported by the data, any wording that implies causation where only association is shown, and any place where the area boundary could be confused with geological formation. Suggest precise corrections only.


# M9 — Portfolio polish

## Goal

Make the project recruiter-ready.


# README final structure

## 1. Title

Alberta Gas Production Intelligence Platform


## 2. One-sentence description

Example:

> A Python, SQL and Power BI analytics pipeline that uses public Petrinex data to identify which operators drive month-over-month reported natural gas production changes in Alberta's Kakwa area.


## 3. Business question

Explain the central question.


## 4. Dashboard screenshots

Show:

- overview
- operator bridge
- data quality


## 5. Key findings

Three concise findings.


## 6. Architecture

Mermaid diagram.


## 7. Data model

Explain:

```text
raw
staging
core
analytics
Power BI
```


## 8. Production bridge

Explain in plain English.


## 9. Data quality

Explain reconciliation.


## 10. Tech stack

- Python
- SQL
- DuckDB
- Power BI
- Pandas
- Parquet
- Pytest
- GitHub Actions


## 11. Run instructions


## 12. Limitations


# Portfolio walkthrough

Record a 2–3 minute video.

Suggested structure:

### 0:00–0:20

Problem.

### 0:20–0:45

Architecture.

### 0:45–1:30

Power BI dashboard.

### 1:30–2:15

Production bridge.

### 2:15–2:40

Data quality.

### 2:40–3:00

What you learned.


# Resume bullet template

Do not fill in numbers until the project is complete.

Use actual measured values.

Example:

> Built an end-to-end Python, SQL, DuckDB and Power BI analytics pipeline processing **[N]+ Petrinex records across [N] facilities and [N] operators** in Alberta's Kakwa area.

> Developed a production bridge decomposing monthly gas-production changes into **continuing_change movement, reported operator changes, new/returning_positive facilities, transitions to reported zero and reporting changes**, with full monthly volume reconciliation.

> Built an interactive Power BI dashboard tracking **MoM/YoY production, operator share, facility drivers, transfers and data-quality metrics**.


# Final Definition of Done

Version 1 is complete only when:

- all real source assumptions are verified
- configured 24-month window runs
- raw files have a manifest
- staging loads correctly
- IDs retain leading zeros
- facility/month reporting states work
- historical operator assignment works
- production filters are verified
- monthly volumes reconcile
- production bridges reconcile exactly
- validation passes
- exports are generated
- Power BI dashboard exists
- findings are written
- screenshots are in README
- README explains limitations
- tests pass
- ruff passes
- CI passes
- repository contains no raw data or secrets

# Revised milestone acceptance requirements

These requirements supplement every milestone above. Use the authoritative bridge
in AGENTS.md; shorthand field lists above must include all its signed components.

- M0: test CLI help and honest stub failure, not an assertion-only placeholder test.
  doctor distinguishes scaffold-ready from source-contract-ready configuration.
- M1: complete docs/source_verification.md with actual headers, packaging, source
  grain, qualifying-row tests, masking/negative/zero policies, reporting-month
  operators, cohort membership and confidentiality limits. Freeze the exact 24
  display months and any preceding context months. Record evidence and approval.
  Operator counts describe coverage, not a quota used to manipulate study boundaries.
- M2: implement versioned source storage, ZIP validation and pinned run manifests.
  Test changed-hash revisions, interrupted writes and recovery as well as retries.
- M3: load only selected revisions; preserve member and row lineage. Test that
  switching revisions replaces the selected analytical snapshot without summing both.
- M4: keep UNKNOWN operators in totals; document cohort stability and independent
  source filtering reconciliation. Missing monthly files and invalid selected values
  are hard failures. Aggregate verified detail grain before facility-month bridges.
- M5: implement component events and credited operator; independently compute actual
  deltas. Test all 3 × 3 state transitions with same operator, changed verified
  operators, UNKNOWN → known, known → UNKNOWN and UNKNOWN → UNKNOWN. Test first
  observed versus returning positive, left censoring, multiple detail rows, zero
  area total, operator entry/exit, transfer + zero, transfer + absence and no prior
  comparison month. Include deterministic randomized multi-facility tests proving
  facility, operator, area and end-minus-start identities using exact decimals.
- M6: warnings must be visible in exports, findings and dashboard. Hard failures
  prevent publishing accepted exports. Preserve last known-good exports; write new
  outputs to a run-specific temporary location and publish atomically on success.
- M7: export the dimension/model contract and bridge component events. Offline CI
  uses fixtures and mock downloads; full-source checks run separately and save a
  run-specific validation artifact with configuration and snapshot hashes.
- M8: build dashboard/model.md before DAX. Human creates Power BI and validates
  relationships, period waterfall, UNKNOWN share and volume reconciliation. Findings
  describe observed contribution, with no unsupported physical or causal labels.
- M9: distinguish pipeline completion from dashboard and portfolio completion.
  Public repository excludes bulk raw files, warehouse, credentials and unreviewed
  source extracts; small real fixtures require redistribution review. Retain enough
  pinned metadata and acquisition instructions to explain reproducibility limits.

A successful synthetic test suite does not verify real source interpretation.
Version 1 cannot be labelled fully verified until the real-data M1 contracts and
full-window reconciliation evidence exist. No percentage accuracy guarantee is made.



# Delivery and learning priorities

Time-box M0 to one focused working session as a planning target, not a reason to
skip working CLI/config checks. Defer cosmetic tooling and unnecessary abstractions.

Validation is mandatory inside both run-all and export. Export must validate the
current database/run/config/source snapshot itself, or verify an equivalent
validation artifact bound to that exact state; a stale earlier pass is insufficient.
There is no publish-without-validation flag. Write failed-run reports separately
without replacing accepted analytical exports.

After M1, independently calculate expected source row counts, qualifying row
counts, facility counts and exact volume for one pinned known month. Store a
reviewed regression baseline with source hash, config hash, metric definition and
expected values. Do not obtain expected values solely from the pipeline being
tested. Revisions require a reviewed new baseline, never silent test updates.
CI uses a redistributable fixture with its own baseline; a private/full-source
regression runs locally against the pinned month when data is available.

For the portfolio walkthrough, explain the core grain, production filter,
reporting-month operator, missing/zero distinction and every bridge component.
Use a small worked example and trace it through the SQL. Document three findings
only once validated outputs exist; prioritize their clarity over cosmetic tooling.

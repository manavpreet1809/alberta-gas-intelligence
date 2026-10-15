# AGENTS.md — Alberta Gas Production Intelligence Platform

Instructions for AI coding agents working in this repository.

Read this file fully before every task.

Then read `PLAN.md` and work only on the current milestone.

Do not expand scope without explicit human approval.


# 1. Project purpose

Build a portfolio-quality Alberta energy analytics platform that answers:

> Which operators are driving month-over-month changes in reported natural gas production in the Kakwa area of Alberta, and how do those reported changes decompose?

The project must produce traceable evidence showing whether changes are associated with:

- continuing reported-volume changes at existing facilities
- reported operator changes
- first observed positive facilities
- returning_positive facilities
- transitions to reported zero
- facilities with no qualifying production row

Primary audience:

- Data Analyst hiring managers
- Business Intelligence hiring managers
- Data Engineering hiring managers
- Business Technology / Digital hiring managers
- Alberta upstream producers
- Alberta midstream companies
- Calgary energy consultancies

The project should demonstrate:

- Alberta energy-domain knowledge
- Python
- SQL
- DuckDB
- data engineering fundamentals
- data modeling
- data validation
- analytical reasoning
- Power BI
- business communication
- testing
- documentation


# 2. Version 1 scope

Version 1 is intentionally narrow.

Do not add features outside this scope without explicit human approval.

## Source

Public Petrinex data only.

Expected source categories:

- volumetric data
- facility/reference data
- business associate/operator data
- operator history/effective-date data if available
- official code/reference documentation where required

Do not scrape websites if downloadable files are available.

Do not use unofficial third-party datasets in Version 1.


## Geography

Study facilities inside a township-range box configured in:

`config/study_area.yaml`

Primary target:

Kakwa area of Alberta.

Fallback:

Deep Basin area if the Kakwa box produces too few operators or facilities for meaningful analysis.

Always describe the geography as:

> facilities in the Kakwa area of Alberta (Twp X–Y, Rge A–B W6M)

Do not call the dataset:

- Montney production
- Duvernay production
- formation production

unless the source explicitly proves formation membership.

Facility location does not establish geological formation.


## Product

Natural gas only.


## Activity

Production only.

Do not treat the following as production:

- receipts
- dispositions
- deliveries
- fuel
- flare
- vent
- injection
- inventory changes
- plant inlet
- plant outlet


## Time window

Use one fixed 24-month window.

Store the window in:

`config/study_area.yaml`

Do not dynamically use "latest 24 months" in Version 1.

The project must be reproducible.

Record:

- reporting window
- download date
- source files used
- source hashes

Recent Petrinex months may be revised later.

Document that limitation.


# 3. Explicitly out of scope for Version 1

Do not implement:

- machine learning
- LLMs
- forecasting
- decline curves
- Arps models
- emissions
- oil
- condensate
- NGL analysis
- gas plant inlet/outlet balances
- automated cloud deployment
- Airflow
- Prefect
- scheduled refresh
- web application
- REST API
- geospatial map server
- Kubernetes
- Spark

These may be considered only after Version 1 is fully complete and published.


# 4. Central analytical question

Every major design decision must support this question:

> Which operators are driving month-over-month changes in reported natural gas production in the selected Alberta study area?

Secondary questions:

1. What is total reported gas production by month?
2. Which operators account for the largest share?
3. Which operators increased or decreased production the most?
4. Was an operator's change continuing_change or caused by transferred facilities?
5. Which individual facilities drove the largest changes?
6. Which facilities first appear with positive volume, return to positive volume, transition to reported zero, or have no qualifying production row?
7. How concentrated is production among operators?
8. Can all reported analytical totals be reconciled back to source data?


# 5. Architecture

```text
Petrinex public files
        |
        | gas-intel download
        v
data/raw/
immutable source files
manifest with hashes + metadata
        |
        | gas-intel load
        v
DuckDB staging schema
source-shaped tables
provenance columns
        |
        | gas-intel build
        v
DuckDB core schema
clean dimensions
facility-month reporting states
gas production fact
historical operator assignment
        |
        v
DuckDB analytics schema
monthly production
operator production
production bridge
facility drivers
reported operator changes
concentration
        |
        | gas-intel validate
        v
data-quality report
        |
        | gas-intel export
        v
data/exports/
CSV + Parquet
        |
        v
Power BI
        |
        v
README + findings brief
```

Database:

`data/warehouse.duckdb`

Schemas:

- `staging`
- `core`
- `analytics`


# 6. Technology stack

Use:

- Python 3.11+
- DuckDB
- pandas
- PyArrow
- PyYAML
- requests
- Typer
- pytest
- ruff
- GitHub Actions
- Power BI

Do not introduce another major framework unless required by a milestone.


# 7. Repository structure

```text
alberta-gas-intelligence/
├── AGENTS.md
├── PLAN.md
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── config/
│   ├── sources.yaml
│   ├── study_area.yaml
│   ├── codes.yaml
│   └── validation.yaml
│
├── data/
│   ├── .gitkeep
│   ├── raw/
│   ├── processed/
│   └── exports/
│
├── src/
│   └── gas_intel/
│       ├── __init__.py
│       ├── cli.py
│       ├── settings.py
│       ├── doctor.py
│       ├── pipeline.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── download.py
│       │   ├── manifest.py
│       │   └── parsers.py
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   └── sql_runner.py
│       │
│       └── validation/
│           ├── __init__.py
│           ├── checks.py
│           └── report.py
│
├── sql/
│   ├── staging/
│   ├── core/
│   └── analytics/
│
├── tests/
│   ├── fixtures/
│   └── test_*.py
│
├── notebooks/
│   └── 01_source_profiling.ipynb
│
├── dashboard/
│   ├── measures.md
│   ├── dax_measures.md
│   └── screenshots/
│
└── docs/
    ├── data_dictionary.md
    ├── methodology.md
    ├── limitations.md
    ├── data_quality_report.md
    └── findings.md
```


# 8. CLI commands

Required:

```bash
pip install -e ".[dev]"

gas-intel doctor
gas-intel download
gas-intel load
gas-intel build
gas-intel validate
gas-intel export
gas-intel run-all

pytest
ruff check .
ruff format --check .
```


# 9. Non-negotiable data rules

## Rule 1 — Never guess

Never invent:

- source URLs
- source file names
- column names
- activity codes
- product codes
- units
- facility type meanings
- operator identifiers
- geographic definitions
- effective-date semantics

These must come from:

- verified source files
- official documentation
- `config/*.yaml`
- `docs/methodology.md`

If something cannot be verified:

```text
TODO(human): verify ...
```

Then stop work that depends on it.


## Rule 2 — Raw data is immutable

Never edit previously accepted source bytes in `data/raw/`. Store accepted downloads by content hash; keep every revision. Append manifest events atomically; manifest metadata is not an immutable source file.

Any transformation happens downstream.


## Rule 3 — Provenance

Every staging row must include:

- `source_file`
- `downloaded_at`
- `ingestion_run_id`

If available, also preserve:

- source reporting period
- source record identifiers


## Rule 4 — Idempotency

Running the same pipeline twice against the same source files must not duplicate data.

Tests must verify this.


## Rule 5 — Safe downloads

Never replace a known-good raw file with an incomplete or corrupt download.

Download to a temporary path first.

Validate:

- non-empty
- expected structure/header
- readable file

Then atomically store it under a content-addressed path in `data/raw/`; never replace an earlier revision.


## Rule 6 — Identifiers are strings

All identifiers must be treated as strings unless explicitly proven otherwise.

Examples:

- facility IDs
- well IDs
- business associate IDs
- operator IDs

Preserve leading zeros.


## Rule 7 — Missing is not zero

Maintain three different states:

1. reported with positive/non-zero volume
2. reported zero
3. no report

Do not convert missing source volumes into zero. The bridge-only reported-total contribution is defined separately below.


## Rule 8 — Production only

Do not add together volumes that represent movements between connected facilities.

Do not double-count gas moving through the system.

Only include verified production activity.


## Rule 9 — Historical operators

Use the operator associated with the reporting month.

Never assign historical production to the current operator merely because they own/operate the facility today.


## Rule 10 — No row multiplication

Core joins must not accidentally duplicate fact rows.

Every many-to-one or temporal join must have a row-count or volume reconciliation test.


## Rule 11 — Explicit units

Every production fact must preserve the unit.

Any conversion must be:

- explicit
- tested
- documented in `docs/methodology.md`


## Rule 12 — Reconciliation

Production volumes must reconcile:

```text
filtered staging
      =
core production fact
      =
analytics total
```

Reconciliation must be testable by reporting month.


## Rule 13 — Production bridge must reconcile exactly

Every bridge must mathematically reconcile to actual production change.

No unexplained residual bucket is allowed merely to make numbers match.


## Rule 14 — No secrets

No credentials or secrets in Git.

Use `.env`.

Maintain `.env.example`.


# 10. Facility-month reporting model and reporting boundary

The metric is publicly available reported GAS/PROD volume for a fixed cohort of
reporting facilities inside the configured DLS box. It is not all physical gas
production originating inside that box: linked wells can be elsewhere and public
extracts can omit or suppress data. Do not claim geological formation membership.

M1 must freeze the cohort, geographic evidence and location reference snapshot.
Use production-month location where verified and complete; otherwise use an
explicitly labelled fixed reference-date cohort. Never silently mix approaches.
Facilities must not enter or leave the cohort merely because their monthly rows
appear or disappear. Store out-of-area linked-well caveats in methodology.

Create one row per cohort facility × analysis month. At this grain define:
- reported_volume: qualifying valid aggregate volume > 0;
- reported_zero: qualifying valid rows exist and aggregate volume = 0;
- no_qualifying_row: no qualifying GAS/PROD row is present in the selected extract.

No qualifying row does not prove failure to submit, zero output, inactivity or
shut-in. Preserve separate evidence fields for source facility presence, other
activities, known suppression and source-period completeness. Evidence of a
SHUTIN activity may be retained separately only with verified semantics; it is
never included in GAS/PROD volume.

Null, masked, malformed or unexpected negative qualifying volumes are unresolved
input, not zero or absence. Quarantine with provenance and fail publication until
resolved under a documented source-supported policy. Distinguish a valid absent
row in an available monthly file from a missing or invalid monthly source file;
the latter is a hard failure. M1 must verify whether explicit zero rows exist and
whether absence can be interpreted beyond the narrow definition above.

# 11. Authoritative signed bridge

Use exact DECIMAL arithmetic at the verified source scale; do not round before
reconciliation. Production source values stay nullable where absent. Define a
separate bridge variable Q: valid observed volume when present, otherwise 0 for
no_qualifying_row. Q is contribution to the observed reported total, not an estimate
of physical output. Compare only consecutive available months in the same frozen
cohort and snapshot selection. The first analysis month has no MoM bridge unless
a verified preceding context month was ingested; never fabricate its baseline.

For each facility transition:
P = previous Q; C = current Q; D = C - P.
A = previous reporting-month operator, B = current reporting-month operator.
Use reserved UNKNOWN when assignment is unavailable; retain assignment evidence.

Step 1: allocate the baseline between operator groups.
If A != B, emit transfer_out = -P to A and transfer_in = +P to B.
If both IDs are verified, label these reported-operator reassignments. They do not
prove ownership transfers, acquisitions or a physical transfer date. If either ID
is UNKNOWN, use attribution_out = -P and attribution_in = +P instead, labelled
operator attribution changes. Never label unknown-to-known as an acquisition.
If A == B, emit no reallocation.

Step 2: allocate D to B in exactly one state category:
- previous positive, current positive: continuing_change = D;
- previous positive, current reported_zero: to_reported_zero = -P;
- previous positive, current no_qualifying_row: absent_production_row = -P;
- previous nonpositive/absent, current positive, prior observed positive history:
  returning_positive = C;
- previous nonpositive/absent, current positive, no prior observed positive history:
  first_observed_positive = C;
- all other valid nonpositive/absent combinations: D = 0; no volume component.

Record whether returning_positive followed explicit zero or absent rows.
First observed means first within available history, never newly commissioned.
Returning positive does not prove a physical restart. to_reported_zero does not
prove a shut-in. continuing_change is an arithmetic label, not a causal claim of
organic growth. Store history_start and left_censored flags. Optional pre-window
context must be fixed in config and excluded from the 24-month displayed totals.

# 12. Reconciliation and operator attribution

All components are signed. For every operator and month:
actual_change = continuing_change + transfer_in + transfer_out
              + attribution_in + attribution_out + first_observed_positive
              + returning_positive + to_reported_zero + absent_production_row.

Compute actual_change independently from monthly operator totals, using the union
of prior and current operator IDs, including UNKNOWN. A missing operator total
means zero reported contribution, not an omitted comparison row.

At area level both reallocation pairs net to zero; sum the state components to
obtain the area change. No arbitrary residual bucket is permitted.

For every facility, (C at B) - (P at A) equals reallocation plus D at B.
This identity handles concurrent operator and state changes without double counting.
When current operator is unavailable, B is UNKNOWN. Do not carry forward an
operator without documented source-supported temporal coverage.

# 13. Required bridge examples

| Previous → current | Previous operator contributions | Current operator contributions |
|---|---|---|
| A:100 → B:120 | A transfer_out -100 | B transfer_in +100, continuing_change +20 |
| A:100 → B:0 explicit | A transfer_out -100 | B transfer_in +100, to_reported_zero -100 |
| A:100 → no row, operator unknown | A attribution_out -100 | UNKNOWN attribution_in +100, absent_production_row -100 |
| UNKNOWN:100 → B:120 | UNKNOWN attribution_out -100 | B attribution_in +100, continuing_change +20 |
| A:0 → B:120, earlier positive exists | A transfer_out 0 | B transfer_in 0, returning_positive +120 |

Zero-volume operator-change events may still be recorded as events. Facility bridge
has one wide row per transition with both operator IDs. Operator bridge is built
from signed component events with an explicit credited_operator_id; do not group
all facility components under the current operator. Maintain event lineage back
to the facility bridge and source rows.

# 14. Analytics outputs

Version 1 must include:

## `analytics.monthly_area_production`

Fields should include:

- month
- gas volume
- unit
- MoM absolute change
- MoM percent change
- YoY absolute change
- YoY percent change
- reporting facility count
- positive-production facility count


## `analytics.operator_monthly_production`

Include:

- month
- operator ID
- operator name
- gas volume
- unit
- operator share of study-area production
- MoM change


## `analytics.facility_bridge_monthly`

One row per:

```text
facility × month transition
```

Include relevant contributions and flags.


## `analytics.operator_bridge_monthly`

Include:

- operator
- month
- continuing_change
- transfer_in
- transfer_out
- first_observed_positive
- returning_positive
- to_reported_zero
- absent_production_row
- calculated_change
- actual_change
- reconciliation_difference


## `analytics.area_bridge_monthly`

Same concept at study-area level.


## `analytics.operator_concentration`

Include:

- month
- top-1 share
- top-3 share
- top-5 share
- HHI


## `analytics.facility_drivers`

Include facilities with the largest:

- increases
- decreases

Provide operator and period context.


## `analytics.operator_transfers`

Include:

- facility
- previous operator
- new operator
- transfer month
- previous-month volume
- current-month volume


## `analytics.data_quality_summary`

Summary of validation checks.


# 15. Validation

Hard failures:

- duplicate fact grain
- staging-to-core production reconciliation mismatch
- core-to-analytics reconciliation mismatch
- bridge reconciliation failure
- row multiplication caused by joins
- missing required configuration

Warnings:

- unassigned operators
- not-reported facility-months
- large MoM production changes
- unexpected codes
- incomplete recent periods
- source manifest anomalies


# 16. Testing philosophy

Tests use:

`tests/fixtures/`

Never require full Petrinex files in CI.

Use two fixture classes:

## Real fixtures

Small extracts copied from real public data.

Purpose:

- parsing
- actual schemas
- realistic values


## Synthetic fixtures

Prefix filenames with:

`synthetic_`

Required synthetic cases:

1. stable continuing_change production
2. continuing_change increase
3. continuing_change decrease
4. operator transfer, same volume
5. operator transfer + volume increase
6. operator transfer + volume decrease
7. first observed positive facility
8. returning_positive facility
9. transition to reported zero
10. have no qualifying production row
11. reported zero
12. missing month
13. duplicate record
14. leading-zero identifier
15. operator missing
16. excluded non-production activity


# 17. SQL conventions

SQL files must be numbered.

Example:

```text
sql/core/
010_dim_month.sql
020_dim_facility.sql
030_dim_operator.sql
040_facility_month.sql
050_fact_gas_production.sql
060_excluded_records.sql
```

Analytics:

```text
010_monthly_area_production.sql
020_operator_monthly_production.sql
030_facility_bridge_monthly.sql
040_operator_bridge_monthly.sql
050_area_bridge_monthly.sql
060_operator_concentration.sql
070_facility_drivers.sql
080_operator_transfers.sql
090_data_quality_summary.sql
```

The SQL runner executes in filename order.


# 18. Python conventions

Use:

- type hints on functions
- short docstrings
- logging
- pathlib
- clear exception messages

Do not use `print()` for pipeline logging.

Functions should have one clear responsibility.

Avoid unnecessary abstraction.


# 19. Notebook rule

Notebooks are exploratory only.

No production logic may exist exclusively in notebooks.

Any reusable logic must move into:

- `src/`
- `sql/`


# 20. Power BI rules

Codex does not create `.pbix` files.

The human builds Power BI manually from:

`data/exports/`

Codex may:

- draft DAX
- define measures
- review calculations
- review screenshots
- review findings

Codex must not claim a dashboard exists until the human has created it.


# 21. README expectations

Final README must explain:

1. Business question
2. Why it matters
3. Study area
4. Data source
5. Architecture
6. Data model
7. Production bridge
8. Validation approach
9. Dashboard
10. Key findings
11. Limitations
12. How to run
13. Tests
14. Technology stack


# 22. Portfolio-quality requirements

The project must be understandable by:

- a recruiter
- a BI analyst
- a data analyst
- a data engineer

Avoid excessive technical jargon in the README.

Always connect technical choices to business value.


# 23. Git rules

Commit only coherent, reviewable units after relevant checks pass. Do not automatically commit after every task or stage; combine related implementation, tests and documentation. Leave routine work uncommitted until a meaningful unit is ready. Follow PLAN.md for commit policy.

Do not create artificial commit quotas.

Good examples:

```text
Add Petrinex source profiling notebook
Load volumetric files into staging
Model facility-month reporting status
Assign historical operators by month
Build facility production bridge
Add monthly reconciliation checks
Export analytics tables for Power BI
```

Do not use meaningless commit messages like:

```text
update
fix
changes
commit 34
milestone 7
```


# 24. Definition of done for every task

Before considering a task complete:

- implementation works
- relevant tests exist for implementation changes
- relevant tests pass
- Ruff passes for Python changes; documentation-only changes pass consistency and diff checks
- docs are updated
- no hard-coded source assumptions
- no unresolved silent guesses
- all `TODO(human)` items are reported to the human

At the end of every Codex task, report:

1. files changed
2. what was implemented
3. tests run
4. results
5. assumptions
6. `TODO(human)` items
7. next stage

# 25. Source contracts, revisions and numerical policies

Read docs/source_verification.md before M1. Documentation-derived facts are
provisional implementation contracts until matched to actual selected downloads.
Use the volumetric extract's production-month Operator BA ID as primary historical
assignment when present and consistent. Operator history is optional supporting
evidence, not a mandatory dependency when the extract already provides assignment.
Define effective-date interval and within-month conflict resolution before any
history join; ambiguous assignments cannot be silently selected.

Preserve source bytes plus container/member hashes for ZIP downloads. Validate ZIP
integrity and prevent extraction path traversal. Handle actual response packaging,
encoding, delimiters, quoting, metadata lines and masking from verified fixtures.
No source row may be dropped as a duplicate merely because an assumed key matches.
Document row grain including From/To and other relevant fields; reconcile detailed
qualifying rows to one facility-month aggregate without adding overlapping totals.

Manifest events include original source fields plus snapshot_id, source_sha256,
member_sha256 where applicable, content_path, retrieved_at_utc, parser_version,
configuration_hash and accepted/rejected status. Failed attempts remain auditable.
A run manifest pins exactly one accepted source revision per source/period and all
reference snapshots. Staging keys use source hash + member + source row ordinal.
Revision selection must never append multiple versions into analytical totals.

Unknown operators remain in totals and shares as reserved UNKNOWN. Missing display
names do not erase valid BA IDs. Unknown attribution produces warnings and limits
interpretation; ambiguous volume/grain or historical assignment conflicts are hard
failures until resolved. Exclusions preserve row lineage and reason; provide a
waterfall from source scope through accepted and excluded rows, and assert both
counts and valid-volume conservation at each filtering boundary.

Unexpected codes outside the configured metric are logged exclusions; unrecognized
semantics affecting the selected metric block publication. Exact source-scale
volume reconciliation uses DECIMAL. Presentation percentages may use floating point
with documented precision. MoM/YoY percentage is null when baseline is zero or
unavailable. HHI uses percentage shares squared, range 0–10,000, including UNKNOWN;
report unknown share alongside it. Top-N shares use volume ranking with stable ID
tie-breaking; denominator zero yields null, not division by zero. Keep monthly
volume distinct from average daily volume and document any days-in-month adjustment.

# 26. Power BI contract and publication

Export dim_month, dim_facility and dim_operator along with analytics facts. Document
each table's exact grain, primary key, units, additive/nonadditive measures and date
representation in dashboard/model.md. Use unique dimension keys and one-to-many,
single-direction relationships from dimensions to facts. No fact-to-fact joins or
ambiguous relationship paths. Area aggregates cannot be filtered as if they were
operator/facility facts. Role-playing operator fields in transfer detail need an
explicit relationship design; use credited operator for bridge component events.
Never sum shares, percentages or HHI across months; recompute them at valid grain.

For a selected start and end month, starting production is the selected start-month
level and bridge transitions are strictly after start through end inclusive.
Their sum must equal end minus start, including operator entries/exits. Reject
noncontiguous month selections for waterfall measures or explain their semantics.
Provide Power BI import steps, relationship diagram, validated DAX, source snapshot
metadata, screenshots and manual reconciliation checks. A .pbix is human-built;
record dashboard status honestly. Publication requires all hard checks passing,
visible warnings, source-access/redistribution review and no unsupported claims.



# 27. Early delivery and mandatory export validation

PLAN.md Stage 3 follows Stage 2 source verification: one month through reusable
pipeline layers to validated exports and a human-built Power BI visual. A second
month is necessary for a change demonstration. Then complete the remaining
stages using the same components.

Both run-all and direct export must enforce current-state validation. An old
successful validation report cannot authorize changed inputs or database state.
Keep regression expectations independently calculated and pinned to exact source
and configuration hashes. Read docs/m1_checklist.md for the M1 exit checklist.

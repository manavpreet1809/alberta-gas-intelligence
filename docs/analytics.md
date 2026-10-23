# Reported-production analytics

Status: implemented analytical tables; final study scope and the human-built Power BI
dashboard remain pending. The signed production-change bridge is now implemented;
see [production_bridge.md](production_bridge.md).

## Area changes

`analytics.monthly_area_production` has one row per analysis month. `volume`,
`previous_volume`, `prior_year_volume`, `mom_change` and `yoy_change` use exact
source-scale DECIMAL values in e3m3. Absolute changes are current minus baseline.

MoM compares the immediately preceding calendar month. YoY compares the same
calendar month one year earlier. A gap cannot be skipped by choosing the preceding
available row. A missing baseline produces null change and null percentage; a
zero baseline produces an exact absolute change but null percentage. Percentage
fields use 100 × change / baseline, so 25 means 25%, not 0.25. They are not additive.
Context can supply a comparison baseline while staying outside reporting exports.

## Operator changes

`analytics.operator_monthly_production` has one row per month/operator combination
with a qualifying current or previous-month contribution. Entries and exits are
both present. An operator with prior production and no current qualifying rows has
zero current **reported contribution**, `has_qualifying_row=false`, and a negative
change equal to its prior total. This does not prove zero physical output.

`previous_volume`, `mom_change` and `mom_percent_change` follow the same baseline
rules as the area table. `area_share` is a fraction, so 0.25 means 25%. UNKNOWN is
retained in totals, changes and denominators. Display names do not replace IDs.
Summing signed operator changes, including exits, reproduces the area MoM change.
These monthly deltas do not separate reassignments themselves; use the signed
bridge tables for that decomposition.

## Concentration

`analytics.operator_concentration` has one row per analysis month. Operators rank
by descending reported volume, then string operator ID for deterministic ties.
`top_1_share`, `top_3_share`, `top_5_share` and `unknown_share` are fractions.
HHI is the sum of squared percentage shares, including UNKNOWN, on a 0–10,000 scale.
`positive_operator_count` counts operators with positive contribution. An area with
zero reported total has null shares and null HHI. Never sum these metrics across months.
Concentration describes this fixed reporting cohort, not an entire physical gas market.

## Facility drivers

`analytics.facility_drivers` has one row per cohort facility and available consecutive
month transition ending in an analysis month. It includes both period operator IDs,
both reporting states, nullable observed volumes, separate reported contributions,
and exact signed `volume_change` in e3m3. An absent qualifying row stays null in the
observed-volume field; only its contribution to the reported total is zero.

Positive changes have `increase_rank` (largest first); negative changes have
`decrease_rank` (most negative first). Ties use facility ID. Zero changes have no
rank. All transitions are retained so their sum can reconcile exactly to the area
change; use rank filters for a top-facility visual. An unavailable prior calendar
month produces no transition. No operator-transfer, new-facility, restart or shut-in
claim follows from this arithmetic. For selected start/end months, use the start-month
production level and sum only transitions strictly after start through end inclusive.
Reject noncontiguous selections for that waterfall. Use the signed bridge in the next stage to
allocate changes between previous and current operators. The implementation is
documented in [production_bridge.md](production_bridge.md).

## Independent validation

Before every export, a Python/Decimal validator recomputes calendar baselines,
operator entry/exit coverage, shares, concentration, nullable facility contributions
and rank ordering directly from core facts and reporting states. It compares these
with SQL outputs. Source-scale volumes reconcile exactly. Display ratios and HHI
use relative tolerance 1e-12 and absolute tolerance 1e-8 for floating-point arithmetic.
Existing source reconciliation and snapshot fingerprints remain mandatory.
Hand-calculated fixture tests include zero denominators, missing comparison months,
YoY, exits, UNKNOWN, absent versus explicit zero, tied facility ranks and corrupted
analytics. All tests remain offline; real warehouse checks use pinned source files.


## Real-data validation — 2026-10-22

The accepted full-window run checks all 24 reporting months using the pinned
13.78-million-row staging snapshot and fixed 551-facility cohort. All 24 MoM
comparisons use available preceding months, including context for January 2024.
Thirteen YoY comparisons are available: December 2024 uses December 2023 context,
then January–December 2025 use their 2024 baselines. Earlier YoY fields stay null.
The accepted bundle has 20 CSV/Parquet files; their hashes were checked after export.
Published Parquet facility deltas reconcile to every area MoM change. See
[evidence/analytics_validation.json](evidence/analytics_validation.json).
These checks do not record final scope approval or establish operational causes.

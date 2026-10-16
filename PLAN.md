# Delivery plan — Alberta Gas Production Intelligence Platform

Build a working result early, then expand it. This plan replaces the earlier
M0–M9 sequence. Stages are delivery boundaries, not commit quotas. AGENTS.md
remains the authority for metric definitions, source handling and bridge rules.

## Stages and current status

| Stage | Deliverable | Status |
|---|---|---|
| 1. Foundation | Installable package, honest CLI, tests and CI workflow | Implemented; local checks and remote CI passed |
| 2. Verify source and scope | Evidence-backed data contract and frozen study definition | In progress: monthly/reference evidence cross-checked; scope and cohort decisions pending |
| 3. First working result | One real month through every layer to validated exports and one visual | Pending |
| 4. Complete data pipeline | Reproducible 24-month warehouse with integrated validation | Pending |
| 5. Explain reported changes | Reconciled facility, operator and area bridges | Pending |
| 6. Dashboard and portfolio | Validated Power BI model, three findings and clear documentation | Pending |

## 1. Foundation

Already implemented: Python package, Typer command interface, configuration
templates, README, test structure and GitHub Actions workflow. Local CLI tests,
Ruff lint and formatting pass. Commands that are not implemented exit nonzero.
Do not add tooling or abstractions without a concrete need in a later stage.

## 2. Verify source and scope

Acquire two or three representative official monthly downloads and relevant
reference documentation. Complete docs/m1_checklist.md and update the source
verification register, data dictionary, methodology and configuration together.

Resolve:

- Actual packaging, headers, detail grain and nonoverlapping production aggregation.
- Production/product codes, eligible facilities, units, precision and invalid values.
- Reporting-month operator assignment, conflicts and UNKNOWN handling.
- Explicit-zero, absent-row and confidentiality semantics.
- Source revisions and the exact versions used; do not assume historical vintages exist.
- DLS boundaries, stable cohort, location reference, fixed 24 display months and any context.
- Source access and small-fixture redistribution terms.

Independently calculate a known-month baseline: source and qualifying row counts,
facility count and exact volume, pinned to source/configuration hashes. Expected
values must not come solely from the pipeline being tested.

Exit: material source questions have evidence-backed answers; the human confirms
the geography and dates. Unresolved material assumptions block dependent work.
Codex performs the research and profiling rather than shifting discovery to the human.
Legacy checklist name M1 refers to this stage.

## 3. First working result

Implement the smallest reusable pipeline for one verified month:

raw snapshot → staging → core → operator/area totals → validation → CSV/Parquet.

Include safe versioned downloads, hashes, a pinned manifest, row lineage, preserved
IDs and monthly operators from the start. Aggregate verified detail rows to the
facility-month grain. Keep UNKNOWN operators in totals. Validate source/core/analytics
counts and volumes, join safety and rerun idempotency before accepting exports.

Provide the minimal Power BI model/import instructions. The human builds one visual
of production by operator and checks it against the validated export. Record the
visual as pending until it actually exists. Independent pipeline work can continue
while the human builds it. No change metric is possible from one month alone.

Exit: a real month runs repeatably through the same code that will support the full
project, reconciles independently and produces usable exports. Never create a
throwaway demo pipeline. A missing visual does not justify claiming a dashboard exists.

## 4. Complete data pipeline

Extend the existing implementation to the configured 24 months and context months.
Finish reference handling, complete fixed-cohort facility-month spine, dimensions,
production fact and exclusion lineage. Preserve positive, explicit-zero and
no-qualifying-row states without turning missing source volumes into physical zero.

Complete monthly area/operator totals, shares, concentration and facility drivers.
Implement all CLI commands using the same modules and numbered SQL files. Add
revision-selection, invalid-input, rerun and fixture-based end-to-end tests.

Both run-all and direct export must enforce validation of the current data,
configuration and pinned snapshot. Hard failures stop publication. Retain previous
accepted outputs and publish new run outputs only after checks pass. Save warning
and validation evidence with each run; stale reports cannot authorize changed data.

Exit: all months run reproducibly, counts/volumes reconcile, joins do not multiply
facts, revision selection does not duplicate totals, tests pass and exports are
accepted only after validation. Remote CI uses fixtures and no live source requests.

## 5. Explain reported changes

Implement the authoritative signed bridge in AGENTS.md. Build facility transitions,
then signed component events with credited operators, then operator/area aggregates.
Compute actual deltas independently from monthly production totals.

Components: continuing_change, transfer_in/out, attribution_in/out,
first_observed_positive, returning_positive, to_reported_zero and
absent_production_row. These describe reported contributions, not proven operational
causes or ownership transactions. Known operator reassignment and UNKNOWN attribution
must remain separate. Track left censoring and prior history.

Test every reporting-state pair with unchanged, changed and UNKNOWN operators;
concurrent operator/state changes; first observation versus return; operator entry/
exit; zero denominators; multiple detail rows; and missing comparison periods.
Use exact DECIMAL arithmetic. Prove facility, operator and area reconciliation,
reallocation net-zero and multi-month end-minus-start identities. Include deterministic
randomized cases and the pinned real-month regression.

Exit: all identities hold exactly without a residual bucket. Integrated validation
blocks bridge failures. Document measures and worked examples that the project
owner can explain line by line.

## 6. Dashboard and portfolio

Export dimensions, facts and component events with documented grains, keys, units
and relationships. Complete dashboard/model.md before drafting DAX. Use
one-to-many, single-direction dimension-to-fact relationships, no fact-to-fact joins
and explicit operator roles. Do not sum shares or concentration across months.

The human builds the final Power BI dashboard:

- Area overview: production, MoM/YoY, operator shares and coverage.
- Operator drivers: trend, reconciled waterfall and facility contributions.
- Data quality/detail: missing rows, UNKNOWN share, exclusions and source vintage.

For a start/end selection, the waterfall baseline is start-month production and
transitions run strictly after start through end. Reconcile dashboard totals and
selected-period bridges against exports, including operator entry/exit.

Write exactly three evidence-backed findings with interpretation and limitations.
Finish README, screenshots and a short walkthrough explaining the SQL, bridge,
source limitations and business value. Use only measured numbers in resume claims.

Exit: the real dashboard exists, checks agree with exports, findings are supported,
CI passes and a reader can reproduce the pipeline and understand its limitations.
Code completion, dashboard completion and portfolio completion are distinct statuses.

## Commit and verification policy

- Commit coherent, reviewable changes after relevant checks pass; no automatic
  commit after every task, file, stage label or minor correction.
- Combine tightly related implementation, tests and documentation in one commit.
  Split a large stage only when the pieces are independently meaningful and tested.
- Do not create empty, placeholder-only or artificial milestone commits.
- Keep working edits uncommitted until a useful unit is ready; report that status.
  Do not rewrite existing commits or force-push unless the user asks.
- Before committing, inspect the staged diff and exclude raw data, warehouses,
  generated bulk exports, local environments and secrets.
- Run checks appropriate to the change. For Python changes run relevant pytest,
  Ruff lint and formatting; documentation edits need link/consistency/diff checks.
- Keep synthetic and real-source verification distinct. Tests cannot certify
  unverified source assumptions. No guarantee of 100 percent real-world accuracy.

Existing specification, foundation and planning commits are useful history and
remain intact. Future progress should be judged by working deliverables, not the
number of commits.

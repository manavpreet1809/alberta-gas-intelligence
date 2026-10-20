# Full candidate-window verification — 2026-10-18

Status: source evidence checked; proposed study scope and cohort are not approved.
This is Stage 2 verification, not a warehouse, production dashboard or causal analysis.

## Results

- All 24 months from January 2024 through December 2025 were acquired and checked.
- December 2023 is available and independently checked as comparison context.
- The analysis-window extracts contain 13,207,735 source rows in total.
- Independent DuckDB counts and exact source-wide GAS/PROD totals match the Python
  profiles for every analysis month and the context month.
- All files match the exact ordered 30-column schema and nested ZIP packaging.
- No unresolved GAS/PROD volumes or duplicate candidate detail keys were found.
- The source profiles found no missing or conflicting qualifying operator assignments.
  This is within-month consistency, not a full-window history-join certification.

## Candidate geography and cohort

The analyst-selected box is Twp 60–65, Rge 3–7 W6M. It is not an official field or
formation boundary. In the 24 analysis months, it contains:

| Measurement | Observed result |
|---|---:|
| Facilities with any rows, union across analysis months | 551 |
| Facilities with GAS/PROD rows, union across analysis months | 389 |
| Facilities with any rows in a single month | 471–483 |
| Facilities with GAS/PROD rows in a single month | 327–345 |
| Operators attached to qualifying rows in a single month | 19–20 |
| Conflicting observed locations among candidate cohort facilities | 0 |
| Unresolved observed locations among candidate cohort facilities | 0 |

Location checks retain all observed monthly locations, including outside-box
positions before a facility first appears inside the box. The fixed-set fingerprint
is recorded in the evidence. December 2023 is checked separately and does not
silently enlarge the analysis-window cohort.

Recommended freeze policy: use the union of facilities with an observed in-box
location in the 24 analysis months. Keep that same set for every analysis month;
retain absent facility-month states. Current infrastructure may supplement names,
but does not remove historical facilities or automatically add facilities observed
only after the analysis window. This refines the earlier reference-union proposal
using the complete monthly evidence. Human scope confirmation remains pending.

A no-qualifying-row month still does not prove physical zero, shut-in or nonexistence.
No observed location conflict is not proof that the geography captures the origins
of all linked-well production.

## Reproduce

Acquire or retain the exact snapshots and local inventory described in
[acquisition.md](acquisition.md), then run:

```bash
python -m gas_intel.window_verification --output data/processed/window_verification.json
gas-intel doctor --details
```

[evidence/candidate_window_verification.json](evidence/candidate_window_verification.json)
contains per-month original URLs, source/payload hashes, acquisition dates, counts,
exact volumes and the candidate set fingerprint. The source/configuration hash binds
the schema used for verification. Raw files and local inventory are excluded from Git.

January/February 2025 reuse the original October 16 snapshots; other files were
retrieved October 18. This is a pinned collection of acquisition vintages, not an
as-first-reported series or a claim that all files have the same source revision date.

## Remaining Stage 2 exit decisions

1. Human confirmation of the proposed box and fixed dates.
2. Record the final frozen cohort policy and a cohort-specific reviewed baseline
   bound to the approved study configuration.
3. Complete final source-contract review, including interpretation and publication
   limitations. Full-window operator-history comparison is separate from observed
   within-month consistency.

No approved study findings or Power BI dashboard are claimed.

## Candidate cohort artifact — 2026-10-20

The new preparation command checks all 24 analysis months and the preceding
context month before writing a candidate membership artifact:

```bash
python -m gas_intel.cohort
```

It reads the explicit dates and box from config/study_area.yaml. Membership is the
union of in-box facilities observed in the analysis months. Context-only facilities
are excluded. All observed locations of cohort members are checked across the
analysis and context months, including outside-box positions; a conflicting or
unresolved location blocks the artifact. Qualifying invalid volumes, duplicate
detail and within-month operator conflicts also block it.

For each month, a Python CSV/Decimal pass over that fixed membership must match
independent DuckDB counts and exact totals. Context baselines use the same cohort,
not every facility appearing in the context-month box. This distinction is tested
with a synthetic context-only facility. Missing monthly inventory is a hard failure.

The artifact in `data/processed/cohorts/<sha256>.json` records sorted membership,
observed locations, the 24 analysis months, separate context, configuration/code
hashes and monthly source/payload hashes with acquisition dates and baselines.
Publication uses a complete flushed temporary file and an exclusive atomic link;
existing artifact bytes are checked before reuse. Identical inputs produce the
same artifact. Facility-level artifacts remain local and excluded from Git;
only aggregate evidence is included in documentation.

This prepares a reproducible candidate cohort; it does not grant human scope
approval, update config approval flags, rebuild the warehouse or certify a
completed dashboard. The existing pilot still uses its two-month cohort. The full
warehouse must explicitly consume the reviewed full-window cohort in Stage 4.

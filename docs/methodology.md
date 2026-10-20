# Methodology — Stage 2 verified observations

The metric under investigation is publicly available GAS/PROD volume attached to
reporting facilities. The official documentation defines gas volume in e3m3
(thousands of cubic metres). Preserve that unit; no conversion is performed in
profiling. Decimal arithmetic avoids binary floating-point reconciliation drift.

Read CSV identifiers as strings, preserve leading zeros and retain every source
row. Filter ActivityID=PROD and ProductID=GAS for exploratory production counts.
Do not add REC, DISP, FUEL, FLARE, VENT, SHUTIN or proration rows. Different FromToID
rows under a facility are detail, not duplicate facility-month totals. The observed
candidate key must be revalidated across the eventual full window.

OperatorBAID is the reporting-month operator according to the learning aid. It is
not ownership or licensee attribution. Current reference operator values must not
replace it. Blank or conflicting assignments require the documented UNKNOWN or
conflict policy before publication.

No explicit-zero GAS/PROD detail rows occur in the two inspected samples. Preserve
no_qualifying_row as a separate state; neither missing activity nor absence proves
physical shut-in. Null/masked/invalid selected volumes are not zeros. Pending a
source-supported alternative, selected invalid or negative volumes block publication.

Source snapshots represent the versions retrieved on the recorded acquisition
UTC dates. No first-report vintage or revision cutoff is claimed. A fixed period
alone does not freeze source revisions. Retain container and all member hashes.

Study boundaries, 24-month window, cohort location policy and cohort-specific
baseline remain pending. Province-wide exploratory totals must never be labelled
Kakwa totals. See source_verification.md for observations and unresolved contracts.

Archive inspection uses a shared bounded reader: root and uncompressed member sizes
are checked, ambiguous/multiply nested archives fail, and member paths are never
extracted. CRC errors propagate rather than being treated as empty data.

Profiling reports distinguish finite-volume sums (diagnostic, including rejected
negative/precision values) from accepted nonnegative source-scale sums. Invalid,
negative or out-of-precision detail makes that facility unresolved; partial valid
detail cannot establish a facility's reported-zero status. This is a conservative
project policy, not a claim that all possible source corrections are nonnegative.

## Implemented warehouse pilot — 2026-10-19

Two explicit months now run through staging, core, analytics, mandatory validation
and versioned exports. Source configuration, raw hashes and model hashes bind each
built snapshot. Staging is replaced transactionally for the selected inventory,
not appended blindly on reruns. Every row preserves source_file, source_sha256,
downloaded_at, ingestion_run_id and a one-based logical source-row ordinal.

The cohort is the union of in-box facilities in the months actually loaded. It is
fixed across those months, including facilities without qualifying production rows.
The January–February pilot has 477 cohort facilities; do not confuse this with the
previously researched 551-facility full-window cohort. Exports explicitly record
pilot status, cohort policy and working-scope status. No approval is invented.

Reporting-month BA IDs determine operator allocation. Reporting-month source names
label operator-month totals; missing IDs enter UNKNOWN. A facility's monthly
metadata must not contain conflicting operators or changing observed locations.
The pipeline rejects duplicate selected detail and invalid selected volume before
publication. Selected detail is aggregated once to the facility-month fact.

Monthly source totals are independently computed using the Python/Decimal source
profiler before loading. SQL staging/core/area/operator totals must equal those
values exactly; row-count and exclusion conservation are checked separately.
Additional checks cover operator attribution, dimension/fact keys, complete
facility-month spine and consistency of reporting states with nullable volumes.

Export validation and table reads share one database transaction. A new bundle is
written before latest.json changes, preserving previous accepted exports on failure.
The latest pointer identifies a bundle; it is not permission to reuse its validation
for changed source/configuration/model state. Direct export always revalidates.

To trace an exported facility-month value to logical input records:

```sql
SELECT ProductionMonth, ReportingFacilityID, FromToID, Volume,
       source_file, source_sha256, source_row_number, ingestion_run_id
FROM staging.volumetrics
WHERE ReportingFacilityID = 'your-facility-id'
  AND ProductionMonth = '2025-01'
  AND ActivityID = 'PROD' AND ProductID = 'GAS';
```

The Power BI import contract is in dashboard/model.md. No bridge or causal findings
are implemented in this pilot. The original local checkout was missing at the start
of recovery; the repository and two raw months were restored, while other ignored
raw files must be reacquired before a full-window run.

## Snapshot integrity — 2026-10-20

A loaded snapshot now records a SHA-256 fingerprint of the staging table. Before
building or validating, the pipeline checks that fingerprint in the same database
transaction. A successful build records fingerprints for all eight exported tables
plus selected detail and exclusion lineage. Direct export and run-all check these
fingerprints as well as the independent monthly volume/count reconciliations.
This detects changed facility names, operator assignments, detail lineage, shares,
reporting counts, duplicate aggregate rows and balanced edits that preserve totals.

The versioned algorithm `sha256_schema_and_sorted_row_hashes_v1` hashes DuckDB's
DESCRIBE schema and the sorted multiset of SHA-256 hashes of JSON row structures.
Nulls and text IDs are preserved, duplicate rows remain in the multiset, and
physical row order has no effect. Python reads hashes in bounded batches; sorting
is managed by DuckDB. Fingerprints are recorded in the validation/export manifest.
They prove consistency with accepted load/build state, not correctness of source
semantics, and are not a signature against someone rewriting database metadata.
Independent source regressions and scope verification remain necessary.

Legacy warehouses lack these fingerprints and must be reloaded and rebuilt from
the pinned inventory. Never populate fingerprints from an unreviewed old database
just to pass validation. Modified staging requires reload; rebuild repairs changed
derived tables. Validation failure leaves the previous accepted bundle and latest
pointer intact. Raw source files and source selections are unchanged by these checks.

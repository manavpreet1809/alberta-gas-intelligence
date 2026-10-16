# Source verification register

Updated 2026-10-16. Stage 2 is in progress, not complete.

## Evidence and scope

Two official downloads returned HTTP 200. Original containers remain in ignored,
content-addressed data/raw storage. Acquisition URL, UTC timestamp, byte counts,
container hash and every member hash are in [profile evidence](evidence/profile_2025-01.json)
and [February evidence](evidence/profile_2025-02.json). No bulk source rows are committed.

The samples are January and February 2025; they are not the approved 24-month study
window. All counts below cover the entire downloaded Alberta extract, not Kakwa,
and are exploratory source checks rather than dashboard findings.

| Month | Source rows | GAS/PROD rows | Facilities | Operators | GAS/PROD sum (e3m3) |
|---|---:|---:|---:|---:|---:|
| 2025-01 | 564,749 | 135,264 | 13,358 | 366 | 13080721.6 |
| 2025-02 | 556,305 | 135,011 | 13,344 | 369 | 12171055.6 |

## Verified observations

- Response format is an outer ZIP containing a monthly ZIP, containing one CSV.
- CSV strictly decodes as UTF-8, uses comma-separated fields and has 30 headers.
- Blank activity/product/volume rows exist; not every source row is a volume fact.
- GAS/PROD detail rows are positive, finite and nonblank in both samples. There are
  no qualifying explicit zeros, negative volumes or masked FromToID values in these samples.
- Qualifying rows have one consistent nonblank operator ID per facility/month.
  All observed GAS/PROD reporting facilities are type BT. This is not a rule to
  exclude other documented valid types without inspecting their data.
- The detail candidate key including FromToID has no duplicate extra rows in either
  sample. Facility-month requires aggregation; metadata rows need separate treatment.
- Source SubmissionDate includes dates after the production month. An acquisition
  in 2026 is not an as-first-reported 2025 vintage.
- Independent DuckDB DECIMAL totals and counts match the Python csv/Decimal profiler;
  [baselines](evidence/known_month_baselines.json) retain the query and hashes.

## Official documentation checked

- [Alberta Public Data](https://petrinex.ca/public-data/apd/) links the official reports.
- [Conventional volumetric learning aid](https://www.petrinex.ca/media/4gfhoah5/pd_conventional_volumetrics_report.pdf), September 2022: pages 5–8 document the endpoint, monthly operator, gas units and suppression; page 13 defines PROD and its applicable facility types.
- [Public-data notice](https://www.petrinex.ca/public-data/) warns about excluded confidential information.
- [Terms](https://www.petrinex.ca/terms) require Crown copyright acknowledgement for non-commercial reuse and prior consent for commercial use. Do not treat access as an unrestricted open-data licence. This project does not publish source rows; fixture values are synthetic.

Revisions are possible: the learning aid describes monthly generation and refreshes
triggered by confidentiality and identifier changes. It does not establish a maximum
revision horizon or promise an as-first-reported archive. We have only one acquisition
vintage per sample and have not measured change between vintages.

## Remaining exit requirements

- TODO(human): approve exact DLS study boundaries and fixed 24-month window after evidence-backed coverage review. No Kakwa box has been asserted or configured.
- Verify a stable cohort and location policy across selected months; build a cohort-specific independent regression baseline with configuration hashes.
- Reference sources and two-sample cross-period checks are complete; extend those checks to the selected full window.
- Resolve absence/zero treatment with source-supported semantics. An absent qualifying row remains unavailable, not proven zero output or shut-in.
- Verify all selected months, final aggregation eligibility and invalid-value policy.
- Review source-use conditions for the intended portfolio publication; no source extracts are redistributed in this commit.

No Stage 3 pipeline or Power BI dashboard has been implemented. doctor must continue
to report source contracts as unverified until all material Stage 2 decisions pass.

## Extended source audit, 2026-10-16

Current facility, BA and operator-history downloads are now pinned and profiled.
Their measured keys are clean. History has no gaps/overlaps under the inclusive
production-month interpretation, and matches all qualifying facilities in both
monthly samples. Current operators differ at 1,862 January and 1,829 February
facilities; use monthly operators, not current references, for past volumes.

Candidate DLS coverage (Twp 60–65, Rge 3–7 W6M) contains 337–342 qualifying
facilities and 20 operators in the samples. It remains an unapproved analyst-defined
box. Current infrastructure has fewer facility IDs than history, so it cannot be
treated as a complete historical facility universe. See the scope proposal.

Source profiling now enforces bounded archives, strict CSV structure and optional
exact ordered schemas. Volume diagnostics distinguish accepted nonnegative values
from unresolved/negative/out-of-precision values. Zero status cannot be inferred
from partially invalid detail. Pinned baselines bind both content and source-config
hashes and are independently cross-checked using DuckDB.

Run `python -m gas_intel.source_audit` to reproduce all evidence from local raw
snapshots. [Latest audit result](evidence/source_audit_result.json) records checks
and code hashes. It does not certify approved scope, the complete 24-month cohort
or operational causes.

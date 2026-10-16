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
- Verify any necessary reference sources and cross-period operator/location conflicts.
- Resolve absence/zero treatment with source-supported semantics. An absent qualifying row remains unavailable, not proven zero output or shut-in.
- Verify all selected months, final aggregation eligibility and invalid-value policy.
- Review source-use conditions for the intended portfolio publication; no source extracts are redistributed in this commit.

No Stage 3 pipeline or Power BI dashboard has been implemented. doctor must continue
to report source contracts as unverified until all material Stage 2 decisions pass.

# Source verification register

Reviewed 2026-10-14. This register distinguishes official documentation from
verification against actual downloaded files. No real production files have yet
been profiled and no pipeline or dashboard has been built.

## Official evidence

- [Petrinex Alberta Public Data](https://petrinex.ca/public-data/apd/): entrypoint for volumetrics, reference reports and operator-history learning aids. The page's general update wording must not be interpreted as the volumetric release cadence.
- [Alberta Conventional Volumetric Download learning aid, September 2022](https://www.petrinex.ca/media/4gfhoah5/pd_conventional_volumetrics_report.pdf): primary source for the statements below. Recheck the current aid and real downloads during M1.

Documentation-derived facts (not live endpoint tests):

- Pages 4–5 describe monthly generation, revisions and CSV/XML requests. Do not infer that a fixed analysis window freezes the data vintage.
- Page 6 defines Operator BA ID and Operator Name for the production month. An additional history join is unnecessary when these fields provide valid monthly assignment.
- Pages 6–8 show From/To fields and confidentiality rules. A simplistic facility/product/activity key is not established as the detail-row grain.
- Pages 7–8 describe withheld rows and masked identifiers. Missing qualifying rows cannot establish physical inactivity or a failed submission.
- Page 9 describes ZIP packaging for CSV downloads. Validate actual API response packaging before implementation.
- Pages 7 and 11 document gas volume in thousands of cubic metres (e3m3 / 10^3 m3), and the GAS product. This is a documented unit contract, not an observed unit column: preserve unit metadata even if the CSV has no unit column.
- Page 13 lists PROD as production and includes facility-type applicability. It also lists SHUTIN separately. A code listing alone does not establish a complete nonoverlapping aggregation strategy.

## Required M1 evidence — pending

- Exact official endpoints used, access time, response status, packaging and hashes.
- Actual headers, types, precision, encoding, row counts and masked values.
- Verified detail grain, duplicate semantics, revisions and nonoverlapping GAS/PROD aggregation.
- Valid facility types and whether selected rows represent complete or partial public coverage.
- Monthly operator consistency and conflicts; any history interval interpretation.
- Zero-row availability and absence semantics; negative and malformed volume policy.
- DLS cohort boundaries, location vintage, facility-location versus well-origin limitations.
- Fixed analysis window and optional historical context; source availability for each month.
- Source access and fixture redistribution terms.

Implementation must not convert documentation-derived facts into a claim that real
data has passed validation. Record each contract's status, evidence path/hash,
reviewer and decision before source-dependent milestones proceed.

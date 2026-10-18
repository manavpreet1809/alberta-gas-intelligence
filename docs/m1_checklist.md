# M1 verification checklist

Status: in progress. January and February 2025 official volumetric downloads have
been profiled; see source_verification.md and evidence/. Unticked items remain
partially or wholly unresolved.
For each item record evidence URL/file/hash, observation, decision, reviewer and
verification date. A tick without evidence is not a completed contract.

- [x] Acquire and hash two representative official volumetric files; record endpoint, packaging, headers, encoding and sample months. Facility, BA and operator-history snapshots are also acquired and profiled; see reference_contracts.md.
- [ ] Establish revision behavior from official documentation and available snapshots. Separate published evidence from observed changes; do not assert a revision horizon without evidence.
- [ ] Choose a pinned acquisition vintage for every month. V1 uses the selected versions as downloaded, not an as-first-reported series unless actual historical vintages exist. Disclose unequal download dates.
- [ ] Verify GAS/PROD codes, source units, source precision and eligible facilities against actual rows and official definitions. Exclude movements, processing, flaring and fuel from production.
- [ ] Prove the detail grain and nonoverlapping aggregation. Document From/To, masked rows, totals, duplicates and corrections.
- [ ] Preserve source units in staging; apply any approved conversion once in core. Test conversion and never mix units in totals.
- [ ] Verify reporting-month operator ID and distinguish it from licensee or ownership. Resolve conflicting IDs and any within-month changes using documented source semantics; never infer a transaction date from monthly observations.
- [ ] Define UNKNOWN attribution and temporal fallback evidence. Do not join current operator attributes onto past production.
- [ ] Verify explicit-zero representation and masking. Define absence only as no qualifying row in a valid selected extract. Do not infer shut-in, not-yet-reported, nonexistence or closure without independent evidence.
- [ ] Freeze DLS study boundaries, cohort membership, location vintage, 24 display months and optional context months. Record facility-location versus well-origin limitations.
- [ ] Define invalid/null/negative qualifying-volume handling and prove all required monthly files are present.
- [ ] Independently calculate and review a known-month regression baseline with counts, exact total, source hash and config hash.
- [ ] Confirm source access and fixture redistribution terms.
- [ ] Record unresolved questions, their dependent tasks and final exit decision. Material ambiguity blocks those tasks.

This is the source checklist for Stage 2 (legacy name M1). After passing, deliver Stage 3: the first working month. Expand the same implementation in Stage 4, then build the bridge in Stage 5.

## Progress details

- Completed: observed schemas and packaging; documented code/unit definitions;
  reference key checks; two-month historical operator cross-check; history interval
  diagnostics; candidate-box coverage; source-wide independent regressions.
- Pending: human scope confirmation; stable full-window cohort/location policy;
  all selected-month availability; cohort-specific reviewed baseline; final
  source-contract exit review and intended publication-use review.

Ticked acquisition items do not certify these remaining requirements.

## Full-window evidence added 2026-10-18

All 24 proposed analysis months and December 2023 context have been acquired.
Independent counts and exact source-wide totals match every monthly profile.
Candidate cohort union and cross-month locations have been checked; no candidate
location conflicts or unresolved locations were found. See window_verification.md.

Availability is no longer an unresolved data-access question. Scope confirmation,
final cohort freeze, approved-configuration baseline and source exit review remain
pending; these are not replaced by passing profiling tests.

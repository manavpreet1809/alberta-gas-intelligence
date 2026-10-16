# Candidate study scope — pending human confirmation

Proposal: facilities in the Kakwa area of Alberta (Twp 60–65, Rge 3–7 W6M),
January 2024–December 2025, with December 2023 as a proposed comparison/context
month. No final study configuration or cohort is approved yet.

This is an analyst-selected rectangle around documented Kakwa locations, not an
AER field boundary and not a formation selection. The exact bounding edges are
a design choice for this project, not values supplied by Petrinex.

The [AER active-facility report](https://www.aer.ca/data/codes/ActiveFacility.pdf)
contains Kakwa facilities at Twp 63, Rge 5 W6. It is supporting geographic context,
not a second production source. Production coverage is measured solely from the
Petrinex snapshots already acquired.

| Sample month | GAS/PROD detail rows | Facilities with qualifying rows | Operators |
|---|---:|---:|---:|
| 2025-01 | 2,385 | 337 | 20 |
| 2025-02 | 2,407 | 342 | 20 |

Both samples have zero invalid location rows, zero conflicting facility locations
and zero invalid selected volume rows. Counts are month-specific and do not establish
the final fixed cohort. No area widening is needed merely to increase operator count.

[evidence/candidate_coverage.json](evidence/candidate_coverage.json) records the box,
source hashes, aggregate volumes and qualifying facility-set fingerprints. Use
geography.profile_box with an explicit DLSBox to reproduce it. Numeric bounds are
inclusive and meridian is matched exactly. Invalid coordinates remain unresolved.

Recommended cohort policy, to verify before freezing: union of facilities inside
the box in any selected monthly extract plus the pinned infrastructure snapshot,
then retain that union for all display months. Any conflicting location membership
must be reviewed rather than silently changing geography month to month. Do not
infer formation, linked-well origin, physical newness or nonexistence from this cohort.

TODO(human): confirm this analyst-defined box and fixed dates, or provide preferred
bounds/dates. While confirmation is pending, source/reference profiling can proceed;
production pipeline publication and approved study findings cannot.

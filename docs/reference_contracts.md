# Reference-source contracts

Verified 2026-10-16 against local official downloads. Evidence files contain
hashes, schemas and counts, never BA addresses, phone numbers or source rows.

| Category | Observed key | Intended role |
|---|---|---|
| Facility infrastructure | FacilityID | Frozen reference-date facility metadata and location, if selected |
| Business associate | BAIdentifier | Current display names; not historical operator assignment |
| Operator history | FacilityID + OperatorBAID + StartDate + EndDate | Supporting historical assignment checks |

[Facility infrastructure learning aid](https://petrinex.ca/media/ltjnok3k/pd_facility_infrastructure_report.pdf)
identifies a current snapshot, with separate operator and licensee fields. The
observed 43-column schema includes October 2026 additions. Do not discard new
columns silently or substitute current operator for historical production.

[Operator history learning aid](https://petrinex.ca/media/klcp3fyn/pd_facility_operator_history_report.pdf)
defines StartDate and EndDate as production periods; 9999-12 denotes the open end.
Before a temporal join, inspect overlap/gap behavior and compare assignments with
production-month OperatorBAID. A unique reference row alone does not establish
unambiguous month coverage. Never select an arbitrary matching row.

[Business associate learning aid](https://petrinex.ca/media/ovnpwahu/pd_business_associate_report.pdf)
describes current legal names. Keep historical BA IDs as reported even when
names or corporate status change. No contact information is needed in V1 exports.

The profiler tests key cardinality, blank keys and malformed records. A reported
candidate key is measured, not a provider guarantee. Archive and payload hashes
pin exactly which current reference snapshots were inspected.

Evidence: reference_facilities.json, reference_operators.json and
reference_operator_history.json under docs/evidence/. Do not infer historical
nonexistence from missing current infrastructure rows.

## Temporal interval checks

The history profiler reads production-month strings as integer month indices,
including 9999-12 without timestamp overflow. It explicitly tests inclusive-end
intervals as a hypothesis. It counts overlaps and gaps and returns every candidate
rather than arbitrarily resolving multiple matches. See history_intervals.json
under docs/evidence/. Cross-check assignments with reporting-month volumetrics
before allowing any history fallback in production.

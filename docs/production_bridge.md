# Signed production-change bridge

The bridge explains arithmetic changes in publicly reported GAS/PROD contributions
for the fixed cohort. It does not prove operational causes, ownership transactions,
commissioning, restarts or shut-ins. Final study approval remains pending.

## Two allocations per facility transition

Let P be the previous reported contribution and C the current contribution. Each
uses the observed valid volume, or zero contribution when no qualifying row exists.
Observed-volume fields stay nullable; this does not estimate physical production.
Only consecutive available months are compared.

First reallocate P when the monthly operator changes. With known IDs A → B, emit
transfer_out = -P to A and transfer_in = +P to B. These are reported operator
reassignments. If either ID is UNKNOWN, emit attribution_out/in instead. Both pairs
net to zero for the area. Zero-volume reassignment events are retained.

Then credit D = C - P to the current operator in exactly one state category:

| Previous → current | Category | Signed amount |
|---|---|---:|
| Positive → positive | continuing_change | C - P |
| Positive → explicit zero | to_reported_zero | -P |
| Positive → absent qualifying row | absent_production_row | -P |
| Nonpositive/absent → positive, earlier positive observed | returning_positive | C |
| Nonpositive/absent → positive, no earlier positive observed | first_observed_positive | C |
| All other valid combinations | No volume event | 0 |

These labels describe reported arithmetic. In particular, continuing_change does
not mean organic growth, first_observed_positive does not mean a new facility,
and returning_positive does not establish a physical restart.

For A:100 → B:120, A receives transfer_out -100; B receives transfer_in +100 and
continuing_change +20. For A:100 → B:0 explicit, B receives transfer_in +100 and
to_reported_zero -100, net zero. For A:100 → no row with UNKNOWN attribution,
A receives attribution_out -100; UNKNOWN receives attribution_in +100 and
absent_production_row -100. Grouping every component under the current operator
would give the wrong operator result.

## History and evidence

`history_start` is the earliest month in the selected snapshot. `prior_positive_month`
is the latest earlier observed positive month. `left_censored=true` means no earlier
positive has been seen in the available history; it does not prove when the facility
began producing. A false flag only establishes an earlier positive observation.
`returning_from` records whether a return followed explicit zero or an absent row.
A gap in available monthly files never creates a transition across that gap.
Available earlier observations can still inform first-observed/return classification.

Operator assignments come from each reporting month's source evidence, including
consistent facility metadata when no qualifying production row exists. No operator
is carried forward into an unobserved month. UNKNOWN attribution events can exist
even when all positive production facts have known operators.

## Tables and lineage

- `facility_bridge_monthly`: one facility × current transition month; both operator
  IDs, states, nullable observations, separate contributions, nine signed components,
  category, source-presence counts and history flags.
- `bridge_component_events`: one facility × month × component, with the explicit
  credited_operator_id, signed volume, previous_month and unit. Includes zero baseline
  reassignment events and zero continuing-change events.
- `operator_bridge_monthly`: one operator × month with all signed components,
  actual_change, calculated_change and reconciliation_difference.
- `area_bridge_monthly`: one month with the same measures. Both reallocation pairs
  net to zero, leaving the state components to explain the area change.
- `operator_transfers`: one observed operator-change event per facility/month,
  explicitly separated by reallocation_type into known-ID reassignments and UNKNOWN
  attribution changes. This is not a list of acquisitions or ownership transfers.

These five tables are exported alongside the ten existing reporting tables.
`analytics.bridge_source_lineage` stays inside the warehouse: one transition ×
period role × source hash × logical row ordinal. It includes facility metadata and
other-activity rows supporting assignment, not just production rows. Join events to
the facility bridge by facility_id/month, then lineage, then staging by source hash
and ordinal. This trace joins inside DuckDB; do not add fact-to-fact Power BI joins.

```sql
SELECT e.component, e.credited_operator_id, e.volume,
       l.period_role, l.source_file, l.source_sha256, l.source_row_number
FROM analytics.bridge_component_events e
JOIN analytics.bridge_source_lineage l USING(facility_id,month)
WHERE e.facility_id = 'your-facility-id' AND e.month = '2025-02';
```

The join deliberately returns multiple source evidence rows per event. Do not sum
event volumes after that lineage join; use the original event grain for totals.

## Exact validation

The pipeline independently rebuilds expected components and credited operators
from core states using Python/Decimal. It proves the facility operator-vector
identity, exact monthly operator and area deltas, reallocation net-zero, event and
operator-change coverage, source-lineage completeness and contiguous multi-month
end-minus-start identities. All nine components are signed; there is no residual.
Source-scale reconciliation is exact, without presentation rounding. Export fails
if these checks fail, preserving the previous accepted export bundle.

Tests include the worked examples above, all reporting-state pairs with known and
UNKNOWN operator changes, first observation versus return, missing months,
zero-volume events, deterministic randomized histories and intentionally corrupted
components, attribution, lineage and aggregate results.

For a selected start/end range, start with the selected start-month level and sum
transitions strictly after start through end, including operator entries/exits.
Reject noncontiguous waterfall selections. The first analysis month can have a
bridge only when its immediately preceding context month is actually loaded.


## Real-data checks — 2026-10-23

The accepted fixed-cohort run validated 13,224 facility transitions, 8,832 component
events, 513 operator-month rows, 24 area months and all 300 contiguous start/end
ranges in the 25-month analysis/context snapshot. Every reconciliation difference
is exactly zero. The 295 observed operator-ID change events comprise 116 known-ID
reassignments and 179 UNKNOWN attribution changes; they are not counts of asset
transactions. Source-lineage checks cover 645,151 logical evidence rows.
All 30 CSV/Parquet file hashes were verified, and published bridge reconciliation
fields and area reallocation pairs were checked after export. See
[evidence/bridge_validation.json](evidence/bridge_validation.json).
Scope confirmation and the human-built Power BI model remain pending.

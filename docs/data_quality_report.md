# Data quality and delivery status

Updated 2026-10-25. This report distinguishes automated checks from pending human
study and dashboard review. Passing reconciliation does not guarantee complete
physical coverage or final publication readiness.

| Check | Recorded result |
|---|---|
| Source window | 24 analysis months plus fixed December 2023 context |
| Source rows loaded | 13,783,410 |
| Frozen candidate cohort | 551 facilities |
| Analysis facility-month spine | 13,224 rows |
| Positive reported-volume facility-months | 8,120 |
| Explicit reported-zero facility-months | 0 observed |
| No qualifying production row | 5,104 facility-months; retained as warnings |
| Monthly source/core/operator/area reconciliation | All 25 selected months passed |
| Signed bridge | 13,224 transitions; exact facility/operator/area identities |
| Contiguous start/end identities | 300 ranges passed |
| Source lineage | 645,151 logical evidence rows checked |
| Export integrity | 30 CSV/Parquet files hash-verified |
| Handoff checks | Text keys, unique/non-null grains, dimension links and endpoint waterfalls passed |
| Power BI reconciliation | Pending; no .pbix or executed DAX validation exists |

The 5,104 absent qualifying facility-months are not missing monthly source files.
Every required source month is present. Absence means no qualifying GAS/PROD row
for that facility in the selected extract; it does not establish physical zero,
nonexistence, non-submission or shutdown. No explicit zero states were observed in
these reporting exports; synthetic tests cover them.

Positive production facts have no UNKNOWN operators in this snapshot. The bridge
still contains 179 UNKNOWN attribution-change events and 116 known-ID reassignment
events; these counts must not be interpreted as ownership transactions. Source
revision, suppression and facility-location versus well-origin limitations remain.

The handoff command verifies an **already accepted export bundle**. It does not
replace current-state pipeline validation or recheck mutable raw files. Use
`gas-intel validate` or `gas-intel export` for the current warehouse. Evidence:
[bridge validation](evidence/bridge_validation.json),
[portfolio handoff](evidence/portfolio_handoff.json), and
[limitations](limitations.md).

Pending human items: confirm the candidate study scope/cohort, review intended
source/publication use and thresholds, build Power BI, and record manual measure
checks and screenshots. No approval has been inferred from automated test results.

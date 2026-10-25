# Power BI and portfolio handoff

The Python/SQL pipeline and signed bridge work. A first web report and semantic
model are saved, with production DAX controls checked against the exports. The
full dashboard, bridge measure acceptance, screenshots and .pbix remain pending.
See [observed draft evidence](../docs/evidence/powerbi_draft.json) and the executed
[production control query](validation/production_controls.dax).

Only fact_gas_production is imported so far. The draft still uses currency display
formatting inherited from the fixed-decimal type; change this to a numeric e3m3
format before presentation. The month chart also needs chronological sorting.
The user authorized importing all remaining project CSVs to the same connected
organizational OneDrive/Power BI account. All fourteen remaining CSV files are
now visible in the private OneDrive folder `gas-intel-csv-upload-jyq8dmqe` under
Uploaded Files. Uploading files is distinct from importing them into the semantic
model: the model still contains only fact_gas_production. Its Editing transition
has not persisted in the observed session, leaving Apply and data-editing controls
unavailable. See the evidence record for the uploaded file fingerprints.

## Verify the bundle first

Read data/exports/latest.json and select its immutable bundle folder. From the
repository root, run with that folder (replace EXPORT_ID with the actual ID):

```bash
python -m gas_intel.handoff --bundle data/exports/EXPORT_ID \
  --output data/processed/portfolio_handoff.json
```

The command verifies the accepted manifest, all 30 file hashes, 15 table grains,
text identifiers, dimension references, 24 contiguous months, production totals,
and selected-period bridge identities. It computes exactly three provisional
findings and records the export/manifest/model/configuration/source hashes. This is
a portable check of accepted exports; it does not authorize changed warehouse state
or replace mandatory validation on `gas-intel export`. Never edit an accepted bundle.

Use the prepared [Power Query import drafts](power_query/README.md) to create all
15 table queries from one selected bundle. Their execution remains part of manual
acceptance.

## Build three report pages

1. **Area overview:** reported volume trend, single-month MoM/YoY, positive/absent
   facility counts, top-three share and HHI. Show unit e3m3, the fixed geography,
   period, snapshot identity and provisional status prominently.
2. **Operator drivers:** monthly reported BA-ID contribution, signed bridge
   waterfall, and ranked facility detail. Use credited_operator_id on component
   events; keep previous/current operator roles explicit in wide detail.
3. **Quality and traceability:** reporting states, UNKNOWN attribution, observed
   operator-ID changes, snapshot dates, hashes and reconciliation differences.

Use [model.md](model.md) for unique keys and relationships and
[dax_measures.md](dax_measures.md) for draft measures. Import every table from the
same bundle. Keep IDs and YYYY-MM keys as text and volume as fixed decimal with
three source decimals. Relations are one-to-many and single-direction from
dimensions. Do not join fact tables together. HHI and area aggregates cannot answer
operator/facility filters through missing keys. Never sum shares across months.

## Manual acceptance values for the recorded real bundle

| Case | Expected result |
|---|---:|
| January 2024 reported gas | 1,300,192.700 e3m3 |
| December 2025 reported gas | 1,295,276.400 e3m3 |
| January–December endpoint change | −4,916.300 e3m3 |
| All signed transitions strictly after January 2024 through December 2025 | −4,916.300 e3m3 |
| A8FG January 2024 contribution | 99,680.500 e3m3 |
| A8FG December 2025 contribution | 0.000 e3m3 |
| A8FG selected-period signed components | −99,680.500 e3m3 |
| January 2024 top-three share | 74.5163159276% |
| December 2025 top-three share | 82.3050045535% |
| January 2024 HHI | 2,457.4437661096 |
| December 2025 HHI | 3,069.5153578846 |
| Facility-month rows / absent qualifying rows | 13,224 / 5,104 |

These values are pinned to [portfolio_handoff.json](../docs/evidence/portfolio_handoff.json).
If a new bundle is selected, regenerate expectations and review differences; do not
silently retain stale dashboard reference values. Compare volumes exactly to three
decimals and display percentages to an agreed precision. Check that leading-zero
IDs survive import. A zero-contribution operator exit must remain visible.

For a selected start/end waterfall, the start-month production is its baseline.
Include event transitions strictly after start through end inclusive. January's
context-based MoM transition is excluded when January is the starting level.
Reject noncontiguous month selections. Test operator entries/exits and UNKNOWN;
use synthetic pipeline examples for explicit-zero cases absent from this snapshot.

## Completion evidence to record

Record .pbix location, selected export ID, tested measures/filter states, expected
and observed results, screenshots of all three pages, and any remaining warnings.
Final scope/source-use review and three findings must be approved before claiming
published portfolio completion. See [findings](../docs/findings.md) and
[data quality](../docs/data_quality_report.md).

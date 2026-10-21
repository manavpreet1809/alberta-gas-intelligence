# Power BI import model

Status: validated CSV/Parquet bundles exist; no Power BI dashboard has been created.
Use the bundle selected by `data/exports/latest.json`. Each bundle is immutable and
contains source/configuration/model hashes and its own validation result.

| Export | Grain | Use |
|---|---|---|
| dim_month | month | ISO YYYY-MM text month dimension |
| dim_facility | facility_id | Fixed cohort of facilities across the loaded months |
| dim_operator | operator_id | Operator display dimension, including UNKNOWN |
| fact_gas_production | facility_id × month | Exact reported volume, monthly operator and contributing source count |
| facility_month | facility_id × month | Full spine; missing volumes remain blank and states stay distinct |
| monthly_area_production | month | Area validation totals and reporting-state counts |
| operator_monthly_production | month × operator_id | Monthly source operator name, volume and area share |
| data_quality_summary | month × report_status | Facility reporting-state counts |

## First visual

1. Import `fact_gas_production.csv`, `dim_month.csv`, `dim_facility.csv` and
   `dim_operator.csv` from the same accepted bundle.
2. Explicitly keep month and all IDs as text; Power BI must not remove leading zeros.
   Set volume to fixed decimal, not whole number. Source volume unit is e3m3
   (thousands of cubic metres); no conversion has been applied.
3. Set unique dimension keys on the one side of one-to-many relationships to the
   corresponding fact keys. Use single-direction filtering from dimensions to fact.
4. Use dim_month.month as a single-month slicer. Add a bar chart with
   dim_operator.operator_name and `Reported gas (e3m3)`.
5. Check the total against monthly_area_production.csv for that same month.

Do not join aggregate tables to facts. If importing area/operator aggregates, use
separate dimension-to-aggregate relationships and measures appropriate to their
available grain. Area totals cannot respond to a facility filter through a missing
facility key. Avoid ambiguous relationship paths and never sum shares across months.

The pilot cohort changes only when the selection of loaded months changes; the
cohort remains fixed inside each built snapshot. A two-month pilot cohort is not
the previously researched full 24-month cohort. Export metadata explicitly records
`pilot`, `scope_status` and `cohort_policy`. No human approval is fabricated.


## Full-window contract

A run selected with `--cohort-artifact` uses the same fixed analysis-window cohort
for every analysis and context month. The current candidate set has 551 facilities.
`core.dim_month` has an `is_analysis` flag; the database keeps the context month,
but all month-grained reporting exports contain only analysis months. Internal
`analytics.monthly_area_all` and `analytics.operator_monthly_all` retain context for
reconciliation and later comparisons. They are not Power BI exports.

The full facility_month export has 551 × 24 = 13,224 facility-month rows when all
configured months pass validation. The warehouse also retains 551 context rows.
Fact volume is additive across exported months in e3m3; blank facility-month volume
remains distinct from explicit zero. Shares remain nonadditive. The YYYY-MM text
month key is unique in dim_month; its exported `is_analysis` values are all true.
Existing one-to-many dimension relationships and measure definitions still apply.

`pilot=false` means all 24 analysis months were loaded. It does not mean scope
approval or dashboard completion. See `scope_status`, `human_scope_approval_recorded`,
`cohort_artifact_sha256`, `analysis_months` and `context_months` in the bundle manifest.

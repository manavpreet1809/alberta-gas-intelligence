# Draft DAX measures

These target the actual export schema and relationship contract in model.md.
They have **not been executed in Power BI**. The human must check them against
handoff.md before recording dashboard completion.

```dax
Reported gas (e3m3) = SUM(fact_gas_production[volume])

Bridge component (e3m3) = SUM(bridge_component_events[volume])

Area MoM (single month, e3m3) =
IF(HASONEVALUE(dim_month[month]), SUM(monthly_area_production[mom_change]))

Area YoY (single month, e3m3) =
IF(HASONEVALUE(dim_month[month]), SUM(monthly_area_production[yoy_change]))

Study-area HHI (single month) =
IF(HASONEVALUE(dim_month[month]), MAX(operator_concentration[hhi]))

Study-area top-three share (single month) =
IF(HASONEVALUE(dim_month[month]), MAX(operator_concentration[top_3_share]))
```

Area changes and concentration are cohort-wide measures; do not present them as
operator/facility-specific responses. Format top-three share as a percentage,
but HHI as a number. Stored mom_percent_change/yoy_percent_change already use
percent units (25 means 25%), so percentage-formatting them directly multiplies
by 100 again. A numeric custom label or division by 100 is required for display.

The simple Bridge component measure is additive at its original event grain.
It does not itself validate a waterfall range. Apply the required start-exclusive,
end-inclusive contiguous transition filter and compare against the selected
end-minus-start production level. Do not add all January context transitions to
a waterfall whose baseline is January. Range measures remain a manual modeling
and validation task; no executed DAX or completed waterfall is claimed.

# First-visual DAX

Draft for the actual pilot export schema; validate it in Power BI after import.
No dashboard or DAX execution is claimed here.

```dax
Reported gas (e3m3) = SUM(fact_gas_production[volume])
```

This measure sums the exported exact volume under the selected month/operator
filters. Display the unit in the visual title. Use a single-month filter for the
first operator comparison and reconcile the grand total against the exported area
validation total. The fixed-decimal import type preserves the three source decimals.

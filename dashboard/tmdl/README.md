# Applied model metadata

These scripts reproduce the 23 relationships and 14 measures applied through
Power BI web TMDL view on 2026-10-25. The source tables must already exist with
the types in [model.md](../model.md). Apply relationships first, then the numbered
measure files in order. Each apply replaces only the named objects; the measure
scripts reference the existing production table rather than replacing that table.

Relationships are many-to-one, single-direction, from each fact key to its unique
dimension key. Previous/current operator roles remain detail fields. The signed
events use credited_operator_id. Area aggregates connect only to dim_month.
Automatic relationship detection was disabled in the observed model.

The web editor reported successful application and zero TMDL problems. This is
metadata evidence, not a successful bridge calculation. Power BI requires a
refresh/recalculation after the relationships are added. The first range query
failed with a relationship-needs-recalculation error; successful range validation
is pending. Do not claim dashboard acceptance from applying these scripts.

Range measures use the selected start-month level and only transitions strictly
after start through end. Noncontiguous month selections return blank range values.
Verify this behavior in Power BI before acceptance. Start/end levels retain
operator and facility filters; component filters affect bridge contributions,
while the reconciliation measure removes the component filter for a total check.
Area-only measures are labelled explicitly and have no facility/operator grain.

Volume formatting is numeric `#,##0.000` in e3m3. Fixed-decimal storage is not a
currency measure. See [validation queries](../validation) and
[observed evidence](../../docs/evidence/powerbi_draft.json).

TMDL syntax reference: [Microsoft TMDL scripts](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-scripts?view=sql-analysis-services-2025).

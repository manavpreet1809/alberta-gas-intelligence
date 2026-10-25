# Import the accepted bundle

These Power Query drafts match the current 15 Parquet export schemas. They have
not been executed in Power BI Desktop; importing and checking them is part of
[manual dashboard acceptance](../handoff.md).

1. Run the Python bundle verifier described in handoff.md before import.
2. Copy that entire immutable bundle folder to the computer running Power BI
   Desktop. Verify the copied bundle there with the same Python command. Do not
   combine files from different bundles or point the report at latest.json.
3. Create a Text parameter named `ExportFolder`, containing the bundle folder's
   absolute local path without a trailing separator. On Windows, for example:
   `C:\Projects\gas\data\exports\EXPORT_ID`.
4. Create a blank query called `LoadGasTable`. Paste the contents of
   [LoadGasTable.pq](LoadGasTable.pq) into its Advanced Editor. Disable its load.
5. Create 15 separate blank queries using the names and expressions in
   [table_queries.pq](table_queries.pq). That file is a list of separate query
   expressions; do not paste the entire list into one query.
6. Close and Apply. Create only the dimension-to-fact relationships in
   [model.md](../model.md). Disable automatic relationship detection if it
   creates additional paths. Keep previous/current operator fields as detail.
7. Format gas volumes as numbers with three decimals and unit e3m3. The M fixed
   decimal type is named Currency.Type; this does not mean the values are money.
   Format fractional shares as percentages and HHI as a number.
8. Execute all acceptance cases in handoff.md and record observed results.

The importer preserves Parquet types and explicitly sets string fields to text
and source decimal fields to fixed decimal. It never fills missing volume with
zero. Shares and percentages retain their exported floating-point types. Unknown
table names fail; missing contracted columns fail instead of silently disappearing.
The M code does not verify cryptographic hashes: the Python verifier does that
before import. These drafts do not establish a validated dashboard.

Microsoft documents [local Parquet import](https://learn.microsoft.com/en-us/power-query/connectors/parquet)
and [fixed-decimal types](https://learn.microsoft.com/en-us/powerquery-m/type-conversion).

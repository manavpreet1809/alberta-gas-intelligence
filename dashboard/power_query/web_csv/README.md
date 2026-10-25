# Typed web CSV imports

These fifteen separate Power Query queries preserve the accepted bundle's column
names and types. They provide a reusable copy of the web import approach used in
Safari on 2026-10-25. They are not proof that the tables were saved in Power BI.

Create a text parameter `UploadedFilesRoot` ending in `/`, pointing to the approved
private OneDrive `Documents/Apps/Microsoft Power Query/Uploaded Files/` folder.
Use the existing organizational connection. The production CSV is directly in
that folder; the remaining fourteen are in `gas-intel-csv-upload-jyq8dmqe/`.
Paste each `.pq` into its own query, named exactly as the filename without `.pq`.
Do not place credentials in the parameter or these files.

Every column is explicitly typed from the Parquet schema in accepted export
`8f01c2ae-9596-441e-a2cd-c35f4d5e47f6`. IDs and months stay text. Volumes use
`Currency.Type` for fixed-decimal storage; set their model display format to
`#,##0.000`, with e3m3 in visual labels. They represent gas volume, not money.
Boolean, count and percentage/share fields retain their corresponding types.
Blank observed volumes remain blank; no replacement with zero is applied.

The UI showed fifteen query definitions and successful selected previews. Two
bulk saves failed with `MaxConcurrentEvaluationsReached` for SKU `General`.
Try a small batch first and verify the model's saved tables before adding more;
that recovery strategy has not yet succeeded in the observed session. Preview
success does not certify full import, relationships, DAX or dashboard acceptance.
See [draft evidence](../../../docs/evidence/powerbi_draft.json) and
[model contract](../../model.md) for required relationships and validation.

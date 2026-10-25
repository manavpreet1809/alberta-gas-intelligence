// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named area_bridge_monthly. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/area_bridge_monthly.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"previous_month", type text},
        {"actual_change", Currency.Type},
        {"continuing_change", Currency.Type},
        {"transfer_in", Currency.Type},
        {"transfer_out", Currency.Type},
        {"attribution_in", Currency.Type},
        {"attribution_out", Currency.Type},
        {"first_observed_positive", Currency.Type},
        {"returning_positive", Currency.Type},
        {"to_reported_zero", Currency.Type},
        {"absent_production_row", Currency.Type},
        {"unit", type text},
        {"calculated_change", Currency.Type},
        {"reconciliation_difference", Currency.Type}
    }, "en-US")
in
    Typed

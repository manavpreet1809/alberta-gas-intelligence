// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named operator_monthly_production. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/operator_monthly_production.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"operator_id", type text},
        {"operator_name", type text},
        {"volume", Currency.Type},
        {"unit", type text},
        {"area_share", type number},
        {"has_qualifying_row", type logical},
        {"previous_month", type text},
        {"previous_volume", Currency.Type},
        {"mom_change", Currency.Type},
        {"mom_percent_change", type number}
    }, "en-US")
in
    Typed

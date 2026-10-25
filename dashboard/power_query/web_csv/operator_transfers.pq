// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named operator_transfers. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/operator_transfers.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"facility_id", type text},
        {"month", type text},
        {"previous_month", type text},
        {"previous_operator_id", type text},
        {"current_operator_id", type text},
        {"reallocation_type", type text},
        {"previous_observed_volume", Currency.Type},
        {"current_observed_volume", Currency.Type},
        {"previous_reported_contribution", Currency.Type},
        {"current_reported_contribution", Currency.Type},
        {"unit", type text}
    }, "en-US")
in
    Typed

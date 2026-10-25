// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named facility_drivers. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/facility_drivers.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"facility_id", type text},
        {"month", type text},
        {"previous_month", type text},
        {"previous_operator_id", type text},
        {"current_operator_id", type text},
        {"previous_report_status", type text},
        {"current_report_status", type text},
        {"previous_observed_volume", Currency.Type},
        {"current_observed_volume", Currency.Type},
        {"previous_reported_contribution", Currency.Type},
        {"current_reported_contribution", Currency.Type},
        {"volume_change", Currency.Type},
        {"unit", type text},
        {"increase_rank", Int64.Type},
        {"decrease_rank", Int64.Type}
    }, "en-US")
in
    Typed

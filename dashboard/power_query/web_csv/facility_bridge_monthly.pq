// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named facility_bridge_monthly. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/facility_bridge_monthly.csv"),
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
        {"previous_source_rows", Int64.Type},
        {"current_source_rows", Int64.Type},
        {"history_start", type text},
        {"prior_positive_month", type text},
        {"left_censored", type logical},
        {"reallocation_type", type text},
        {"state_category", type text},
        {"unit", type text},
        {"returning_from", type text},
        {"transfer_out", Currency.Type},
        {"transfer_in", Currency.Type},
        {"attribution_out", Currency.Type},
        {"attribution_in", Currency.Type},
        {"continuing_change", Currency.Type},
        {"to_reported_zero", Currency.Type},
        {"absent_production_row", Currency.Type},
        {"returning_positive", Currency.Type},
        {"first_observed_positive", Currency.Type}
    }, "en-US")
in
    Typed

// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named facility_month. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/facility_month.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"facility_id", type text},
        {"month", type text},
        {"operator_id", type text},
        {"volume", Currency.Type},
        {"unit", type text},
        {"facility_source_rows", Int64.Type},
        {"report_status", type text}
    }, "en-US")
in
    Typed

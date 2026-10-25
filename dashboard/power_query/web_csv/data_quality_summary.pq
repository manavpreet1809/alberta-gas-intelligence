// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named data_quality_summary. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/data_quality_summary.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"report_status", type text},
        {"facility_count", Int64.Type}
    }, "en-US")
in
    Typed

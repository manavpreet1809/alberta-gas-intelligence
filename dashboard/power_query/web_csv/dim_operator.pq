// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named dim_operator. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/dim_operator.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"operator_id", type text},
        {"operator_name", type text}
    }, "en-US")
in
    Typed

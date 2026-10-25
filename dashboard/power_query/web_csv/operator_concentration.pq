// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named operator_concentration. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/operator_concentration.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"area_volume", Currency.Type},
        {"unit", type text},
        {"top_1_share", type number},
        {"top_3_share", type number},
        {"top_5_share", type number},
        {"hhi", type number},
        {"unknown_share", type number},
        {"positive_operator_count", Int64.Type}
    }, "en-US")
in
    Typed

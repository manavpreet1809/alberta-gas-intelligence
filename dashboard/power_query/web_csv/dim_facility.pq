// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named dim_facility. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/dim_facility.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"facility_id", type text},
        {"facility_name", type text},
        {"facility_type", type text},
        {"facility_subtype", type text},
        {"township", Int64.Type},
        {"range", Int64.Type},
        {"meridian", Int64.Type}
    }, "en-US")
in
    Typed

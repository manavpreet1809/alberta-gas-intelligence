// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named fact_gas_production. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "fact_gas_production.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"facility_id", type text},
        {"operator_id", type text},
        {"volume", Currency.Type},
        {"unit", type text},
        {"source_record_count", Int64.Type}
    }, "en-US")
in
    Typed

// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named bridge_component_events. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/bridge_component_events.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"facility_id", type text},
        {"month", type text},
        {"previous_month", type text},
        {"component", type text},
        {"credited_operator_id", type text},
        {"volume", Currency.Type},
        {"unit", type text}
    }, "en-US")
in
    Typed

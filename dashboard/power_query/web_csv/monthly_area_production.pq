// Create a text parameter UploadedFilesRoot ending in / for the approved private folder.
// One separate query named monthly_area_production. Schema checked against the accepted export.
let
    Source = Csv.Document(Web.Contents(UploadedFilesRoot & "gas-intel-csv-upload-jyq8dmqe/monthly_area_production.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month", type text},
        {"volume", Currency.Type},
        {"unit", type text},
        {"reporting_facilities", Int64.Type},
        {"positive_facilities", Int64.Type},
        {"zero_facilities", Int64.Type},
        {"absent_facilities", Int64.Type},
        {"previous_month", type text},
        {"previous_volume", Currency.Type},
        {"mom_change", Currency.Type},
        {"mom_percent_change", type number},
        {"prior_year_month", type text},
        {"prior_year_volume", Currency.Type},
        {"yoy_change", Currency.Type},
        {"yoy_percent_change", type number}
    }, "en-US")
in
    Typed

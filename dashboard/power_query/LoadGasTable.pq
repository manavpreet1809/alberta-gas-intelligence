// Create a text parameter named ExportFolder pointing to one verified bundle.
// Paste this function into a blank query named LoadGasTable. Disable its load.
// Reviewed against exported schemas; execution in Power BI remains pending.
(tableName as text) as table =>
let
    Contracts = [
        area_bridge_monthly = {{"month", type text}, {"previous_month", type text}, {"unit", type text}, {"actual_change", Currency.Type}, {"continuing_change", Currency.Type}, {"transfer_in", Currency.Type}, {"transfer_out", Currency.Type}, {"attribution_in", Currency.Type}, {"attribution_out", Currency.Type}, {"first_observed_positive", Currency.Type}, {"returning_positive", Currency.Type}, {"to_reported_zero", Currency.Type}, {"absent_production_row", Currency.Type}, {"calculated_change", Currency.Type}, {"reconciliation_difference", Currency.Type}},
        bridge_component_events = {{"facility_id", type text}, {"month", type text}, {"previous_month", type text}, {"component", type text}, {"credited_operator_id", type text}, {"unit", type text}, {"volume", Currency.Type}},
        data_quality_summary = {{"month", type text}, {"report_status", type text}},
        dim_facility = {{"facility_id", type text}, {"facility_name", type text}, {"facility_type", type text}, {"facility_subtype", type text}},
        dim_month = {{"month", type text}},
        dim_operator = {{"operator_id", type text}, {"operator_name", type text}},
        facility_bridge_monthly = {{"facility_id", type text}, {"month", type text}, {"previous_month", type text}, {"previous_operator_id", type text}, {"current_operator_id", type text}, {"previous_report_status", type text}, {"current_report_status", type text}, {"history_start", type text}, {"prior_positive_month", type text}, {"reallocation_type", type text}, {"state_category", type text}, {"unit", type text}, {"returning_from", type text}, {"previous_observed_volume", Currency.Type}, {"current_observed_volume", Currency.Type}, {"previous_reported_contribution", Currency.Type}, {"current_reported_contribution", Currency.Type}, {"volume_change", Currency.Type}, {"transfer_out", Currency.Type}, {"transfer_in", Currency.Type}, {"attribution_out", Currency.Type}, {"attribution_in", Currency.Type}, {"continuing_change", Currency.Type}, {"to_reported_zero", Currency.Type}, {"absent_production_row", Currency.Type}, {"returning_positive", Currency.Type}, {"first_observed_positive", Currency.Type}},
        facility_drivers = {{"facility_id", type text}, {"month", type text}, {"previous_month", type text}, {"previous_operator_id", type text}, {"current_operator_id", type text}, {"previous_report_status", type text}, {"current_report_status", type text}, {"unit", type text}, {"previous_observed_volume", Currency.Type}, {"current_observed_volume", Currency.Type}, {"previous_reported_contribution", Currency.Type}, {"current_reported_contribution", Currency.Type}, {"volume_change", Currency.Type}},
        facility_month = {{"facility_id", type text}, {"month", type text}, {"operator_id", type text}, {"unit", type text}, {"report_status", type text}, {"volume", Currency.Type}},
        fact_gas_production = {{"month", type text}, {"facility_id", type text}, {"operator_id", type text}, {"unit", type text}, {"volume", Currency.Type}},
        monthly_area_production = {{"month", type text}, {"unit", type text}, {"previous_month", type text}, {"prior_year_month", type text}, {"volume", Currency.Type}, {"previous_volume", Currency.Type}, {"mom_change", Currency.Type}, {"prior_year_volume", Currency.Type}, {"yoy_change", Currency.Type}},
        operator_bridge_monthly = {{"month", type text}, {"operator_id", type text}, {"previous_month", type text}, {"unit", type text}, {"actual_change", Currency.Type}, {"continuing_change", Currency.Type}, {"transfer_in", Currency.Type}, {"transfer_out", Currency.Type}, {"attribution_in", Currency.Type}, {"attribution_out", Currency.Type}, {"first_observed_positive", Currency.Type}, {"returning_positive", Currency.Type}, {"to_reported_zero", Currency.Type}, {"absent_production_row", Currency.Type}, {"calculated_change", Currency.Type}, {"reconciliation_difference", Currency.Type}},
        operator_concentration = {{"month", type text}, {"unit", type text}, {"area_volume", Currency.Type}},
        operator_monthly_production = {{"month", type text}, {"operator_id", type text}, {"operator_name", type text}, {"unit", type text}, {"previous_month", type text}, {"volume", Currency.Type}, {"previous_volume", Currency.Type}, {"mom_change", Currency.Type}},
        operator_transfers = {{"facility_id", type text}, {"month", type text}, {"previous_month", type text}, {"previous_operator_id", type text}, {"current_operator_id", type text}, {"reallocation_type", type text}, {"unit", type text}, {"previous_observed_volume", Currency.Type}, {"current_observed_volume", Currency.Type}, {"previous_reported_contribution", Currency.Type}, {"current_reported_contribution", Currency.Type}}
    ],
    Types = if Record.HasFields(Contracts, tableName)
        then Record.Field(Contracts, tableName)
        else error "Table is outside the verified export contract",
    Source = Parquet.Document(File.Contents(ExportFolder & "/" & tableName & ".parquet")),
    Typed = Table.TransformColumnTypes(Source, Types, "en-US")
in
    Typed

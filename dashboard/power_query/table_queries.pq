// Create each named query separately using its expression below.
// These are separate queries, not one executable M document.

// Query: area_bridge_monthly
LoadGasTable("area_bridge_monthly")

// Query: bridge_component_events
LoadGasTable("bridge_component_events")

// Query: data_quality_summary
LoadGasTable("data_quality_summary")

// Query: dim_facility
LoadGasTable("dim_facility")

// Query: dim_month
LoadGasTable("dim_month")

// Query: dim_operator
LoadGasTable("dim_operator")

// Query: facility_bridge_monthly
LoadGasTable("facility_bridge_monthly")

// Query: facility_drivers
LoadGasTable("facility_drivers")

// Query: facility_month
LoadGasTable("facility_month")

// Query: fact_gas_production
LoadGasTable("fact_gas_production")

// Query: monthly_area_production
LoadGasTable("monthly_area_production")

// Query: operator_bridge_monthly
LoadGasTable("operator_bridge_monthly")

// Query: operator_concentration
LoadGasTable("operator_concentration")

// Query: operator_monthly_production
LoadGasTable("operator_monthly_production")

// Query: operator_transfers
LoadGasTable("operator_transfers")

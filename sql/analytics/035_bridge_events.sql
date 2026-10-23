CREATE OR REPLACE TABLE analytics.bridge_component_events AS
SELECT b.facility_id,b.month,b.previous_month,e.component,e.credited_operator_id,
       e.volume::DECIMAL(20,3) AS volume,b.unit
FROM analytics.facility_bridge_monthly b
CROSS JOIN LATERAL (VALUES
    ('transfer_out',b.previous_operator_id,b.transfer_out,b.reallocation_type='reported_operator_reassignment'),
    ('transfer_in',b.current_operator_id,b.transfer_in,b.reallocation_type='reported_operator_reassignment'),
    ('attribution_out',b.previous_operator_id,b.attribution_out,b.reallocation_type='attribution_change'),
    ('attribution_in',b.current_operator_id,b.attribution_in,b.reallocation_type='attribution_change'),
    ('continuing_change',b.current_operator_id,b.continuing_change,b.state_category='continuing_change'),
    ('to_reported_zero',b.current_operator_id,b.to_reported_zero,b.state_category='to_reported_zero'),
    ('absent_production_row',b.current_operator_id,b.absent_production_row,b.state_category='absent_production_row'),
    ('returning_positive',b.current_operator_id,b.returning_positive,b.state_category='returning_positive'),
    ('first_observed_positive',b.current_operator_id,b.first_observed_positive,b.state_category='first_observed_positive')
) e(component,credited_operator_id,volume,emit)
WHERE e.emit;

-- Logical source ordinals retain evidence for both monthly operator assignments,
-- including metadata/other activities when no qualifying production row exists.
CREATE OR REPLACE TABLE analytics.bridge_source_lineage AS
SELECT b.facility_id,b.month,
       CASE WHEN s.ProductionMonth=b.month THEN 'current' ELSE 'previous' END AS period_role,
       s.source_file,s.source_sha256,s.source_row_number,s.ingestion_run_id,s.downloaded_at
FROM analytics.facility_bridge_monthly b JOIN staging.volumetrics s
  ON s.ReportingFacilityID=b.facility_id
 AND (s.ProductionMonth=b.month OR s.ProductionMonth=b.previous_month);

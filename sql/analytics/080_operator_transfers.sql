CREATE OR REPLACE TABLE analytics.operator_transfers AS
SELECT facility_id,month,previous_month,previous_operator_id,current_operator_id,
       reallocation_type,previous_observed_volume,current_observed_volume,
       previous_reported_contribution,current_reported_contribution,unit
FROM analytics.facility_bridge_monthly WHERE reallocation_type<>'none';

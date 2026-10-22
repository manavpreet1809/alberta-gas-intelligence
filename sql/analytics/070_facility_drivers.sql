-- This is an arithmetic reported-contribution comparison, not the signed operator bridge.
CREATE OR REPLACE TABLE analytics.facility_drivers AS
WITH transitions AS (
    SELECT c.facility_id,c.month,p.month AS previous_month,
           p.operator_id AS previous_operator_id,c.operator_id AS current_operator_id,
           p.report_status AS previous_report_status,c.report_status AS current_report_status,
           p.volume AS previous_observed_volume,c.volume AS current_observed_volume,
           coalesce(p.volume,0)::DECIMAL(20,3) AS previous_reported_contribution,
           coalesce(c.volume,0)::DECIMAL(20,3) AS current_reported_contribution,
           (coalesce(c.volume,0)-coalesce(p.volume,0))::DECIMAL(20,3) AS volume_change,
           'e3m3' AS unit
    FROM core.facility_month c JOIN core.dim_month m ON m.month=c.month AND m.is_analysis
    JOIN core.facility_month p ON p.facility_id=c.facility_id
      AND strptime(p.month,'%Y-%m')=strptime(c.month,'%Y-%m') - INTERVAL '1 month'
)
SELECT *,
       CASE WHEN volume_change>0 THEN row_number() OVER (
           PARTITION BY month,volume_change>0 ORDER BY volume_change DESC,facility_id)
           END AS increase_rank,
       CASE WHEN volume_change<0 THEN row_number() OVER (
           PARTITION BY month,volume_change<0 ORDER BY volume_change,facility_id)
           END AS decrease_rank
FROM transitions;

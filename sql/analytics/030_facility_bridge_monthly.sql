CREATE OR REPLACE TABLE analytics.facility_bridge_monthly AS
WITH history AS (
    SELECT *, min(month) OVER(PARTITION BY facility_id) AS history_start,
           max(CASE WHEN volume>0 THEN month END) OVER (
               PARTITION BY facility_id ORDER BY month
               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prior_positive_month
    FROM core.facility_month
), transitions AS (
    SELECT c.facility_id,c.month,p.month AS previous_month,
           p.operator_id AS previous_operator_id,c.operator_id AS current_operator_id,
           p.report_status AS previous_report_status,c.report_status AS current_report_status,
           p.volume AS previous_observed_volume,c.volume AS current_observed_volume,
           coalesce(p.volume,0)::DECIMAL(20,3) AS previous_reported_contribution,
           coalesce(c.volume,0)::DECIMAL(20,3) AS current_reported_contribution,
           (coalesce(c.volume,0)-coalesce(p.volume,0))::DECIMAL(20,3) AS volume_change,
           p.facility_source_rows AS previous_source_rows,c.facility_source_rows AS current_source_rows,
           c.history_start,c.prior_positive_month,c.prior_positive_month IS NULL AS left_censored,
           CASE WHEN p.operator_id=c.operator_id THEN 'none'
                WHEN p.operator_id='UNKNOWN' OR c.operator_id='UNKNOWN' THEN 'attribution_change'
                ELSE 'reported_operator_reassignment' END AS reallocation_type,
           CASE WHEN p.volume>0 AND c.volume>0 THEN 'continuing_change'
                WHEN p.volume>0 AND c.report_status='reported_zero' THEN 'to_reported_zero'
                WHEN p.volume>0 AND c.report_status='no_qualifying_row' THEN 'absent_production_row'
                WHEN c.volume>0 AND c.prior_positive_month IS NOT NULL THEN 'returning_positive'
                WHEN c.volume>0 THEN 'first_observed_positive' END AS state_category
    FROM history c JOIN core.dim_month m ON m.month=c.month AND m.is_analysis
    JOIN history p ON p.facility_id=c.facility_id
      AND strptime(p.month,'%Y-%m')=strptime(c.month,'%Y-%m') - INTERVAL '1 month'
)
SELECT *, 'e3m3' AS unit,
       CASE WHEN state_category='returning_positive' THEN previous_report_status END AS returning_from,
       CASE WHEN reallocation_type='reported_operator_reassignment'
            THEN -previous_reported_contribution ELSE 0 END AS transfer_out,
       CASE WHEN reallocation_type='reported_operator_reassignment'
            THEN previous_reported_contribution ELSE 0 END AS transfer_in,
       CASE WHEN reallocation_type='attribution_change'
            THEN -previous_reported_contribution ELSE 0 END AS attribution_out,
       CASE WHEN reallocation_type='attribution_change'
            THEN previous_reported_contribution ELSE 0 END AS attribution_in,
       CASE WHEN state_category='continuing_change' THEN volume_change ELSE 0 END AS continuing_change,
       CASE WHEN state_category='to_reported_zero' THEN volume_change ELSE 0 END AS to_reported_zero,
       CASE WHEN state_category='absent_production_row' THEN volume_change ELSE 0 END AS absent_production_row,
       CASE WHEN state_category='returning_positive' THEN volume_change ELSE 0 END AS returning_positive,
       CASE WHEN state_category='first_observed_positive' THEN volume_change ELSE 0 END AS first_observed_positive
FROM transitions;

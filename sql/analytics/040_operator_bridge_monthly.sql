CREATE OR REPLACE TABLE analytics.operator_bridge_monthly AS
WITH components AS (
    SELECT month,credited_operator_id AS operator_id,
       sum(CASE WHEN component='continuing_change' THEN volume ELSE 0 END)::DECIMAL(20,3) AS continuing_change,
       sum(CASE WHEN component='transfer_in' THEN volume ELSE 0 END)::DECIMAL(20,3) AS transfer_in,
       sum(CASE WHEN component='transfer_out' THEN volume ELSE 0 END)::DECIMAL(20,3) AS transfer_out,
       sum(CASE WHEN component='attribution_in' THEN volume ELSE 0 END)::DECIMAL(20,3) AS attribution_in,
       sum(CASE WHEN component='attribution_out' THEN volume ELSE 0 END)::DECIMAL(20,3) AS attribution_out,
       sum(CASE WHEN component='first_observed_positive' THEN volume ELSE 0 END)::DECIMAL(20,3) AS first_observed_positive,
       sum(CASE WHEN component='returning_positive' THEN volume ELSE 0 END)::DECIMAL(20,3) AS returning_positive,
       sum(CASE WHEN component='to_reported_zero' THEN volume ELSE 0 END)::DECIMAL(20,3) AS to_reported_zero,
       sum(CASE WHEN component='absent_production_row' THEN volume ELSE 0 END)::DECIMAL(20,3) AS absent_production_row
    FROM analytics.bridge_component_events GROUP BY month,credited_operator_id
), keys AS (
    SELECT month,operator_id FROM components
    UNION
    SELECT month,operator_id FROM analytics.operator_monthly_production
    WHERE previous_month IS NOT NULL
), levels AS (
    SELECT k.*,a.previous_month,
           coalesce(c.volume,0)-coalesce(p.volume,0) AS actual_change
    FROM keys k JOIN analytics.monthly_area_production a ON a.month=k.month
    LEFT JOIN analytics.operator_monthly_all c ON c.month=k.month AND c.operator_id=k.operator_id
    LEFT JOIN analytics.operator_monthly_all p ON p.month=a.previous_month AND p.operator_id=k.operator_id
), allocated AS (
    SELECT l.*,
           coalesce(e.continuing_change,0)::DECIMAL(20,3) AS continuing_change,
           coalesce(e.transfer_in,0)::DECIMAL(20,3) AS transfer_in,
           coalesce(e.transfer_out,0)::DECIMAL(20,3) AS transfer_out,
           coalesce(e.attribution_in,0)::DECIMAL(20,3) AS attribution_in,
           coalesce(e.attribution_out,0)::DECIMAL(20,3) AS attribution_out,
           coalesce(e.first_observed_positive,0)::DECIMAL(20,3) AS first_observed_positive,
           coalesce(e.returning_positive,0)::DECIMAL(20,3) AS returning_positive,
           coalesce(e.to_reported_zero,0)::DECIMAL(20,3) AS to_reported_zero,
           coalesce(e.absent_production_row,0)::DECIMAL(20,3) AS absent_production_row,
           'e3m3' AS unit
    FROM levels l LEFT JOIN components e USING(month,operator_id)
), calculated AS (
    SELECT *, (continuing_change + transfer_in + transfer_out
            + attribution_in + attribution_out + first_observed_positive
            + returning_positive + to_reported_zero + absent_production_row)::DECIMAL(20,3) AS calculated_change
    FROM allocated
)
SELECT *, (calculated_change-actual_change)::DECIMAL(20,3) AS reconciliation_difference
FROM calculated;

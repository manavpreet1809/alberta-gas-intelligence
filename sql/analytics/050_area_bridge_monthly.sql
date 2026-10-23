CREATE OR REPLACE TABLE analytics.area_bridge_monthly AS
WITH components AS (
    SELECT month,
           sum(continuing_change) AS continuing_change,
           sum(transfer_in) AS transfer_in,
           sum(transfer_out) AS transfer_out,
           sum(attribution_in) AS attribution_in,
           sum(attribution_out) AS attribution_out,
           sum(first_observed_positive) AS first_observed_positive,
           sum(returning_positive) AS returning_positive,
           sum(to_reported_zero) AS to_reported_zero,
           sum(absent_production_row) AS absent_production_row
    FROM analytics.operator_bridge_monthly GROUP BY month
), allocated AS (
    SELECT a.month,a.previous_month,a.mom_change AS actual_change,
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
    FROM analytics.monthly_area_production a LEFT JOIN components e USING(month)
    WHERE a.previous_month IS NOT NULL
), calculated AS (
    SELECT *, (continuing_change + transfer_in + transfer_out
            + attribution_in + attribution_out + first_observed_positive
            + returning_positive + to_reported_zero + absent_production_row)::DECIMAL(20,3) AS calculated_change
    FROM allocated
)
SELECT *, (calculated_change-actual_change)::DECIMAL(20,3) AS reconciliation_difference
FROM calculated;

-- Comparisons use exact calendar offsets; missing months never become a baseline.
CREATE OR REPLACE TABLE analytics.monthly_area_production AS
SELECT a.*, p.month AS previous_month, p.volume AS previous_volume,
       a.volume - p.volume AS mom_change,
       100.0 * (a.volume - p.volume) / nullif(p.volume,0) AS mom_percent_change,
       y.month AS prior_year_month, y.volume AS prior_year_volume,
       a.volume - y.volume AS yoy_change,
       100.0 * (a.volume - y.volume) / nullif(y.volume,0) AS yoy_percent_change
FROM analytics.monthly_area_all a
JOIN core.dim_month m ON m.month=a.month AND m.is_analysis
LEFT JOIN analytics.monthly_area_all p
  ON strptime(p.month,'%Y-%m') = strptime(a.month,'%Y-%m') - INTERVAL '1 month'
LEFT JOIN analytics.monthly_area_all y
  ON strptime(y.month,'%Y-%m') = strptime(a.month,'%Y-%m') - INTERVAL '1 year';

-- Prior-month-only operator keys retain exits as zero reported contribution.
CREATE OR REPLACE TABLE analytics.operator_monthly_production AS
WITH keys AS (
    SELECT month,operator_id FROM analytics.operator_monthly_all
    UNION
    SELECT strftime(strptime(month,'%Y-%m') + INTERVAL '1 month','%Y-%m'),operator_id
    FROM analytics.operator_monthly_all
)
SELECT k.month, k.operator_id, coalesce(c.operator_name,d.operator_name) AS operator_name,
       coalesce(c.volume,0)::DECIMAL(20,3) AS volume, 'e3m3' AS unit,
       coalesce(c.volume,0) / nullif(a.volume,0) AS area_share,
       c.operator_id IS NOT NULL AS has_qualifying_row,
       a.previous_month,
       CASE WHEN a.previous_month IS NOT NULL THEN coalesce(p.volume,0) END
           AS previous_volume,
       CASE WHEN a.previous_month IS NOT NULL THEN coalesce(c.volume,0)-coalesce(p.volume,0) END
           AS mom_change,
       CASE WHEN a.previous_month IS NOT NULL
            THEN 100.0 * (coalesce(c.volume,0)-coalesce(p.volume,0))/nullif(p.volume,0) END
           AS mom_percent_change
FROM keys k JOIN analytics.monthly_area_production a USING(month)
JOIN core.dim_operator d USING(operator_id)
LEFT JOIN analytics.operator_monthly_all c ON c.month=k.month AND c.operator_id=k.operator_id
LEFT JOIN analytics.operator_monthly_all p ON p.month=a.previous_month AND p.operator_id=k.operator_id;

CREATE OR REPLACE TABLE analytics.monthly_area_all AS
SELECT month, coalesce(sum(volume), 0)::DECIMAL(20,3) AS volume, 'e3m3' AS unit,
       count(*) FILTER (WHERE report_status <> 'no_qualifying_row') AS reporting_facilities,
       count(*) FILTER (WHERE report_status = 'reported_volume') AS positive_facilities,
       count(*) FILTER (WHERE report_status = 'reported_zero') AS zero_facilities,
       count(*) FILTER (WHERE report_status = 'no_qualifying_row') AS absent_facilities
FROM core.facility_month GROUP BY month ORDER BY month;

CREATE OR REPLACE TABLE analytics.operator_monthly_all AS
WITH totals AS (
    SELECT month, operator_id, sum(volume)::DECIMAL(20,3) AS volume
    FROM core.fact_gas_production GROUP BY month, operator_id
), names AS (
    SELECT ProductionMonth AS month,
           coalesce(nullif(OperatorBAID,''),'UNKNOWN') AS operator_id,
           max(nullif(OperatorName,'')) AS operator_name
    FROM staging.volumetrics GROUP BY ProductionMonth, OperatorBAID
)
SELECT t.month, t.operator_id,
       CASE WHEN t.operator_id='UNKNOWN' THEN 'Unknown operator'
            ELSE coalesce(n.operator_name,d.operator_name) END AS operator_name, t.volume, 'e3m3' AS unit,
       t.volume / nullif(a.volume, 0) AS area_share
FROM totals t JOIN core.dim_operator d USING (operator_id)
JOIN analytics.monthly_area_all a USING (month)
LEFT JOIN names n ON n.month=t.month AND n.operator_id=t.operator_id
ORDER BY month, volume DESC, operator_id;

CREATE OR REPLACE TABLE analytics.data_quality_summary AS
SELECT month, report_status, count(*) AS facility_count
FROM core.facility_month JOIN core.dim_month USING(month)
WHERE is_analysis GROUP BY month, report_status;

CREATE OR REPLACE TABLE analytics.monthly_area_production AS
SELECT a.* FROM analytics.monthly_area_all a JOIN core.dim_month USING(month)
WHERE is_analysis;

CREATE OR REPLACE TABLE analytics.operator_monthly_production AS
SELECT a.* FROM analytics.operator_monthly_all a JOIN core.dim_month USING(month)
WHERE is_analysis;

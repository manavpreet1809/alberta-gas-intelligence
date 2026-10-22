-- Shares are fractions; HHI uses percentage shares squared, including UNKNOWN.
CREATE OR REPLACE TABLE analytics.operator_concentration AS
WITH ranked AS (
    SELECT *, row_number() OVER(PARTITION BY month ORDER BY volume DESC,operator_id) AS volume_rank
    FROM analytics.operator_monthly_production
)
SELECT a.month, a.volume AS area_volume, 'e3m3' AS unit,
       sum(r.volume) FILTER(WHERE volume_rank<=1) / nullif(a.volume,0) AS top_1_share,
       sum(r.volume) FILTER(WHERE volume_rank<=3) / nullif(a.volume,0) AS top_3_share,
       sum(r.volume) FILTER(WHERE volume_rank<=5) / nullif(a.volume,0) AS top_5_share,
       sum(pow(100.0*r.volume/nullif(a.volume,0),2)) AS hhi,
       coalesce(sum(r.volume) FILTER(WHERE r.operator_id='UNKNOWN'),0) / nullif(a.volume,0)
           AS unknown_share,
       count(*) FILTER(WHERE r.volume>0) AS positive_operator_count
FROM analytics.monthly_area_production a
LEFT JOIN ranked r USING(month)
GROUP BY a.month,a.volume;

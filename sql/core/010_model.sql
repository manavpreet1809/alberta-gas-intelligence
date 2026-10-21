CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE OR REPLACE TABLE core.dim_month AS
SELECT DISTINCT ProductionMonth AS month,
       ProductionMonth BETWEEN start_month AND end_month AS is_analysis
FROM staging.volumetrics CROSS JOIN pipeline_settings ORDER BY month;

CREATE OR REPLACE TEMP TABLE candidate_cohort AS
    SELECT DISTINCT ReportingFacilityID AS facility_id
    FROM staging.volumetrics CROSS JOIN pipeline_settings
    WHERE ProductionMonth BETWEEN start_month AND end_month
      AND regexp_full_match(FacilityTownship, '[0-9]+')
      AND regexp_full_match(FacilityRange, '[0-9]+')
      AND regexp_full_match(FacilityMeridian, '[0-9]+')
      AND try_cast(FacilityTownship AS INTEGER) BETWEEN township_min AND township_max
      AND try_cast(FacilityRange AS INTEGER) BETWEEN range_min AND range_max
      AND try_cast(FacilityMeridian AS INTEGER) = meridian;

CREATE OR REPLACE TABLE core.dim_facility AS
WITH cohort AS (
    SELECT facility_id FROM staging.cohort
    UNION ALL
    SELECT facility_id FROM candidate_cohort WHERE NOT EXISTS (SELECT 1 FROM staging.cohort)
)
SELECT ReportingFacilityID AS facility_id, ReportingFacilityName AS facility_name,
       ReportingFacilityType AS facility_type, ReportingFacilitySubType AS facility_subtype,
       try_cast(FacilityTownship AS INTEGER) AS township,
       try_cast(FacilityRange AS INTEGER) AS range,
       try_cast(FacilityMeridian AS INTEGER) AS meridian
FROM staging.volumetrics JOIN cohort ON ReportingFacilityID = facility_id
QUALIFY row_number() OVER (
    PARTITION BY ReportingFacilityID ORDER BY ProductionMonth DESC, source_row_number
) = 1;

CREATE OR REPLACE TABLE core.dim_operator AS
SELECT operator_id, max(operator_name) AS operator_name FROM (
    SELECT coalesce(nullif(OperatorBAID, ''), 'UNKNOWN') AS operator_id,
           coalesce(nullif(OperatorName, ''), 'Unknown operator') AS operator_name
    FROM staging.volumetrics
    UNION ALL SELECT 'UNKNOWN', 'Unknown operator'
) GROUP BY operator_id;

CREATE OR REPLACE TABLE core.selected_records AS
SELECT s.*, coalesce(nullif(OperatorBAID, ''), 'UNKNOWN') AS operator_id,
       try_cast(Volume AS DECIMAL(13,3)) AS volume_value
FROM staging.volumetrics s
JOIN core.dim_facility d ON s.ReportingFacilityID = d.facility_id
WHERE ActivityID = 'PROD' AND ProductID = 'GAS';

CREATE OR REPLACE TABLE core.fact_gas_production AS
SELECT ProductionMonth AS month, ReportingFacilityID AS facility_id,
       min(operator_id) AS operator_id, sum(volume_value)::DECIMAL(20,3) AS volume,
       'e3m3' AS unit, count(*) AS source_record_count
FROM core.selected_records GROUP BY ProductionMonth, ReportingFacilityID;

CREATE OR REPLACE TABLE core.facility_month AS
WITH presence AS (
    SELECT ProductionMonth AS month, ReportingFacilityID AS facility_id,
           min(coalesce(nullif(OperatorBAID, ''), 'UNKNOWN')) AS operator_id,
           count(*) AS facility_source_rows
    FROM staging.volumetrics GROUP BY ProductionMonth, ReportingFacilityID
)
SELECT d.facility_id, m.month, coalesce(p.operator_id, 'UNKNOWN') AS operator_id,
       f.volume, 'e3m3' AS unit, coalesce(p.facility_source_rows, 0) AS facility_source_rows,
       CASE WHEN f.facility_id IS NULL THEN 'no_qualifying_row'
            WHEN f.volume = 0 THEN 'reported_zero' ELSE 'reported_volume' END AS report_status
FROM core.dim_facility d CROSS JOIN core.dim_month m
LEFT JOIN presence p ON p.facility_id = d.facility_id AND p.month = m.month
LEFT JOIN core.fact_gas_production f ON f.facility_id = d.facility_id AND f.month = m.month;

CREATE OR REPLACE TABLE core.excluded_records AS
SELECT s.source_file, s.source_sha256, s.source_row_number, s.ProductionMonth AS month,
       CASE WHEN d.facility_id IS NULL THEN 'outside_loaded_cohort'
            WHEN ActivityID IS DISTINCT FROM 'PROD' THEN 'wrong_activity'
            ELSE 'wrong_product' END AS exclusion_reason
FROM staging.volumetrics s LEFT JOIN core.dim_facility d ON s.ReportingFacilityID = d.facility_id
WHERE d.facility_id IS NULL OR ActivityID IS DISTINCT FROM 'PROD' OR ProductID IS DISTINCT FROM 'GAS';

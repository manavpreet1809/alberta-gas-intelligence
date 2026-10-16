# Observed volumetric data dictionary

Verified against January and February 2025 CSV members downloaded 2026-10-16.
These are exact source headers, not invented snake_case schema names. All source
fields remain strings during profiling; blanks and leading zeros are preserved.

| Field group | Exact source headers | Interpretation |
|---|---|---|
| Period | ProductionMonth, SubmissionDate | Production month versus reported update date; not acquisition time |
| Operator | OperatorBAID, OperatorName | Reporting-month operator; not licensee or owner |
| Facility | ReportingFacilityID, ReportingFacilityProvinceState, ReportingFacilityType, ReportingFacilityIdentifier, ReportingFacilityName, ReportingFacilitySubType, ReportingFacilitySubTypeDesc | Reporting facility metadata |
| Location | ReportingFacilityLocation, FacilityLegalSubdivision, FacilitySection, FacilityTownship, FacilityRange, FacilityMeridian | DLS facility location, not proof of linked well origin |
| Activity/product | ActivityID, ProductID | Select PROD and GAS only for production profiling |
| Counterparty | FromToID, FromToIDProvinceState, FromToIDType, FromToIDIdentifier | Detail link; preserve it before aggregation |
| Measures | Volume, Energy, Hours | Gas volume e3m3 documented externally; energy/hours are not gas volume |
| Additional | CCICode, ProrationProduct, ProrationFactor, Heat | Retain source values; no V1 production calculation from these fields |

## Observed grain

The complete CSV contains metadata/proration rows with blank activity/volume, plus
activity detail. Do not impose one universal business key on all source rows.
For GAS/PROD only, (ProductionMonth, ReportingFacilityID, ActivityID, ProductID,
FromToID) is unique in both samples. Facility-month is not a detail key: many linked
rows belong to one reporting facility. This candidate must be checked for every
future month; sample uniqueness does not establish a provider-guaranteed key.

Raw lineage key remains source hash + archive-member chain + row ordinal.
Aggregate validated qualifying detail rows to facility-month without including
receipt or disposition rows. Exact headers and blank counts are in docs/evidence/.

## Schema drift checks

The shared CSV reader rejects blank/duplicate headers, missing required columns,
malformed quoting and unequal column counts. The production profiler optionally
accepts the exact ordered expected_headers contract from config/sources.yaml;
when supplied, additions, removals and reordering all require explicit review.
Exploratory checks that supply only required columns do not certify the full schema.

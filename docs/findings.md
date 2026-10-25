# Three provisional findings

These describe facilities in the Kakwa area of Alberta (Twp 60–65, Rge 3–7 W6M),
using the fixed 551-facility candidate cohort and January 2024–December 2025 window.
Scope confirmation and portfolio publication review remain pending. Numerical
claims are derived from the hash-verified accepted export bundle recorded in
[evidence/portfolio_handoff.json](evidence/portfolio_handoff.json). They are not
Power BI observations; the dashboard has not been built.

## 1. Nearly flat endpoint volume hides offsetting reported contributions

Reported monthly volume changed from **1,300,192.700 e3m3** in January 2024 to
**1,295,276.400 e3m3** in December 2025: **−4,916.300 e3m3 (−0.3781%)**.
The start-exclusive bridge (February 2024 through December 2025) reconciles exactly:

| State component | Signed contribution (e3m3) |
|---|---:|
| continuing_change | −57,213.000 |
| first_observed_positive | +78,374.900 |
| returning_positive | +21,577.700 |
| to_reported_zero | 0.000 |
| absent_production_row | −47,655.900 |
| Total change | −4,916.300 |

Both operator-reallocation pairs net to zero for the area. The arithmetic shows
why endpoint levels alone miss changes within the reporting population. First
observed does not establish a new facility, returning does not establish a restart,
and absent production rows do not prove physical output fell to zero. These are
monthly levels, not an annual volume or a daily production rate.

## 2. The largest BA-ID endpoint decline cannot be read as physical decline

Reporting BA ID **A8FG**, displayed as **STRATHCONA RESOURCES LTD.**, changed from
**99,680.500 e3m3** to **0.000 e3m3** of reported contribution, the largest absolute
BA-ID endpoint change in this cohort. Its signed decomposition is:

| Component | Signed contribution (e3m3) |
|---|---:|
| continuing_change | −10,675.700 |
| transfer_out | −111,553.100 |
| attribution_out | −18,927.600 |
| first_observed_positive | +41,836.900 |
| returning_positive | +3,656.200 |
| absent_production_row | −4,017.200 |
| Other components | 0.000 |
| Total change | −99,680.500 |

The bridge separates reported operator reassignments and UNKNOWN attribution
changes from state-volume changes. This is a comparison of one reporting BA ID,
not a consolidated corporate production total. Different BA IDs must not be
combined by display name without a verified mapping. A zero endpoint contribution
does not establish an asset sale, company exit from Alberta or physical shutdown.

## 3. Reported volume became more concentrated among reporting BA IDs

The top-three share rose from **74.52%** to **82.31%**, an increase of **7.79 percentage
points**. HHI rose from **2,457.44** to **3,069.52** on the percentage-share-squared
0–10,000 scale. UNKNOWN share was zero at both endpoints.

These metrics describe concentration of reported volume in this fixed cohort.
They do not establish concentration in an economic market, ultimate corporate
ownership, geological formation output or complete physical production. A zero
UNKNOWN volume share does not eliminate attribution-change events around absent rows.

Reproduce all three calculations with `python -m gas_intel.handoff`; see
[the handoff guide](../dashboard/handoff.md). Exact unrounded values, component
amounts, model/configuration hashes and source hashes are in the evidence file.

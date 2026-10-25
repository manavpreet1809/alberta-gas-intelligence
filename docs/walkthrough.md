# Project walkthrough

This project asks which reporting operators account for changes in publicly
reported natural gas production at facilities in the proposed Kakwa study box.
The candidate scope is Twp 60–65, Rge 3–7 W6M, January 2024–December 2025, with
December 2023 used only as comparison context. Scope approval remains pending.

## Explain the pipeline

Python downloads official Petrinex files, checks their structure and stores
unchanged bytes under hashes. A run pins one selected revision per month, so
revised downloads cannot accidentally double production. Staging preserves the
source columns, file identity and row ordinal. SQL builds a fixed 551-facility
cohort, reporting-month operators, a facility-month spine and exact production
facts in DuckDB. CSV and Parquet exports are released only after validation of
the current database, configuration and source snapshots.

A valid absent production row stays missing in the source-volume field. It is
not evidence of zero physical output. Only the separate bridge contribution uses
zero for absence when explaining the observed reported total. Explicit reported
zero is a different state. Invalid selected volumes stop publication.

## Explain the bridge

Take a facility reported under operator A at 100 and operator B at 120 the next
month. First move the previous reported contribution: A receives −100 and B
receives +100. Then credit B with the remaining +20 continuing change. A's change
is −100, B's is +120, and the study area's is +20. This also works when the
current row is absent or explicitly zero. Changes involving UNKNOWN operator
assignment are attribution changes, not evidence of acquisitions.

Explain [the signed bridge](production_bridge.md) before discussing findings.
Show how component events carry a credited operator rather than attributing all
changes to the current operator. Explain why a January-to-December waterfall
starts at January's level and includes only February-through-December changes.

## Show evidence

The recorded candidate run includes 24 display months, 13,224 facility-month
transitions and independently checked reconciliation over all 300 contiguous
start/end selections. The portable handoff verifier checks all 30 export hashes,
keys, text IDs, dimension references and analytical totals. CI uses small fixtures
rather than downloading millions of live records.

Open [the three findings](findings.md). Describe the small endpoint area decline,
the largest individual BA-ID contribution change and the rise in concentration.
Use the exact pinned values there. Separate arithmetic explanation from operational
causation, and individual BA IDs from consolidated corporate groups.

## Technology and business value

- Python and Typer provide repeatable pipeline commands; requests retrieves sources
  and PyYAML reads explicit configuration.
- SQL and DuckDB produce inspectable dimensions, facts and signed bridge tables
  without requiring a database server.
- pandas supports data inspection; PyArrow supplies typed Parquet interchange.
- pytest checks source handling, missing states, operator allocation and exact
  reconciliation; Ruff checks Python quality; GitHub Actions runs fixture checks.
- Power BI is the planned presentation layer. Import queries, model instructions,
  draft measures and expected results are supplied; the human-built dashboard and
  executed DAX checks remain outstanding.

## Close with limits

The metric is reported GAS/PROD at cohort facilities, not all physical gas
originating inside the box. Facility location does not establish formation.
Sources can be revised or suppressed, and first observed positive does not mean
newly commissioned. Report the pinned download vintage and provisional scope.
Do not present a dashboard demo until the actual report passes acceptance.

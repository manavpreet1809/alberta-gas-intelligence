# Implemented measures

- Reported gas volume: exact sum of verified GAS/PROD detail, aggregated to
  facility-month, in e3m3. Missing source rows are not physical zero production.
- Reporting facilities: facilities with a qualifying production row for the month.
- Positive facilities: qualifying aggregate volume greater than zero.
- Zero facilities: explicit qualifying rows aggregate to exactly zero.
- Absent facilities: no qualifying GAS/PROD row in the selected source snapshot.
- Operator share: operator-month volume divided by the month's area volume.
  Returns blank for zero denominators; not additive across months.

Monthly operator IDs and names come from that month's source, with UNKNOWN kept
in totals when assignment is absent. None of these measures establishes asset
ownership, operational causation or geological formation membership.

Area MoM/YoY and operator MoM changes, top-1/3/5 shares, HHI, UNKNOWN share and
ranked facility contribution changes are implemented. Definitions and nullable
baseline rules are in [analytics.md](../docs/analytics.md). A percent-change value
of 25 means 25%; share fields use fractions, where 0.25 means 25%. These values
cannot be summed across months. The signed production-change bridge is implemented; see
[production_bridge.md](../docs/production_bridge.md) for component definitions and
credited-operator allocation. DAX execution and dashboard reconciliation remain pending.

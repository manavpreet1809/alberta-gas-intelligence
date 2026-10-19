# Implemented pilot measures

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

MoM/YoY measures, concentration and the change bridge remain future implementation.

# Methodology — Stage 2 verified observations

The metric under investigation is publicly available GAS/PROD volume attached to
reporting facilities. The official documentation defines gas volume in e3m3
(thousands of cubic metres). Preserve that unit; no conversion is performed in
profiling. Decimal arithmetic avoids binary floating-point reconciliation drift.

Read CSV identifiers as strings, preserve leading zeros and retain every source
row. Filter ActivityID=PROD and ProductID=GAS for exploratory production counts.
Do not add REC, DISP, FUEL, FLARE, VENT, SHUTIN or proration rows. Different FromToID
rows under a facility are detail, not duplicate facility-month totals. The observed
candidate key must be revalidated across the eventual full window.

OperatorBAID is the reporting-month operator according to the learning aid. It is
not ownership or licensee attribution. Current reference operator values must not
replace it. Blank or conflicting assignments require the documented UNKNOWN or
conflict policy before publication.

No explicit-zero GAS/PROD detail rows occur in the two inspected samples. Preserve
no_qualifying_row as a separate state; neither missing activity nor absence proves
physical shut-in. Null/masked/invalid selected volumes are not zeros. Pending a
source-supported alternative, selected invalid or negative volumes block publication.

Source snapshots represent the versions retrieved on the recorded acquisition
UTC dates. No first-report vintage or revision cutoff is claimed. A fixed period
alone does not freeze source revisions. Retain container and all member hashes.

Study boundaries, 24-month window, cohort location policy and cohort-specific
baseline remain pending. Province-wide exploratory totals must never be labelled
Kakwa totals. See source_verification.md for observations and unresolved contracts.

Archive inspection uses a shared bounded reader: root and uncompressed member sizes
are checked, ambiguous/multiply nested archives fail, and member paths are never
extracted. CRC errors propagate rather than being treated as empty data.

Profiling reports distinguish finite-volume sums (diagnostic, including rejected
negative/precision values) from accepted nonnegative source-scale sums. Invalid,
negative or out-of-precision detail makes that facility unresolved; partial valid
detail cannot establish a facility's reported-zero status. This is a conservative
project policy, not a claim that all possible source corrections are nonnegative.

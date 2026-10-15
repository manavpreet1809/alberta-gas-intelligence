# Specification review

Revised 2026-10-14.

- Corrected signed transfer arithmetic and explicit credited-operator attribution.
- Separated observed reporting states from operational and ownership claims.
- Defined UNKNOWN attribution, pinned source revisions, cohort policy and Power BI relationships.
- Added official source evidence and pending real-data contracts.
- Checked the operator bridge algebra across 162 state/operator/history combinations using Python Decimal. All operator and area identities passed. This algebra check does not test an implemented pipeline or real source interpretation.

Remaining verification: M1 real-download profiling, cohort/window approval, full-source reconciliation and manual Power BI validation. No pipeline tests, lint or dashboard checks have run because only specification documents were created.

# AIOS Foundation Data Import — NUTE Prototype

The prototype accepts NUTE institutional `.xlsx` workbooks from the Administration workspace and normalizes them into a shared Foundation Identity & People store.

Supported workbook structures:

- IX.1 — Organization units → `organizations`
- IX.2 — Positions/job titles → `positions`
- IX.3 — Staff/personnel profiles → canonical `people` (`person_kind=staff`) plus organization assignments
- V.1 — Student cohorts → `student_cohorts`
- V.2 — Major/cohort definitions → `major_cohorts`
- V.4 — Administrative/advising classes → `admin_classes`
- V.5 — Student profiles → canonical `people` (`person_kind=student`)

## Identity model

A person is stored once as a canonical Person/Identity. Account, role assignment and authority scope are separate objects. This allows the same identity to participate across RIS, LIS, SIS, PIS and future domains without copying the person record into each domain.

## Account administration

Administration can create/edit an account linked to a Person, assign multiple role codes and an authority scope, reset a temporary password, and set account state to `active`, `locked` or `disabled`.

## Data handling

Uploaded source workbooks are parsed in memory and are not committed to the source repository. Prototype normalized data is persisted in `runtime/aios-prototype.sqlite3`, which is ignored by Git. Production deployment requires database encryption, backup, access controls, audit and institutional retention policies before importing real sensitive data.

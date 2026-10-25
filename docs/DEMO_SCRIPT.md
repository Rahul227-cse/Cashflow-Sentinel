# Demo script and recording checklist

1. Show `GET /api/health` returning `exasol`.
2. Open Overview and explain outstanding, overdue, risk and discrepancy metrics.
3. In Invoice registry, search `CED-882` and explain its high risk factors.
4. Open Discrepancies: click **Run reconciliation** to demonstrate deterministic rule evaluation and audit event logging in Exasol; identify duplicate `AST-1048`, the unmatched remittance, and deduction-reference cue.
5. Open Collections: show why the highest-ranked invoice needs follow-up.
6. Show the Exasol `CFS_DEMO` tables and the seed command used for repeatability.
7. Close with limitations: synthetic data, heuristic risk, human investigation required.

Before recording: confirm `.env` is private, run the seed, API tests, live integration test, backend, frontend, and the production build. Do not record credentials, a database console containing secrets, or unsupported impact claims.

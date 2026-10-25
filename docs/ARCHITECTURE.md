# Architecture and data flow

```text
React + Vite (localhost:5173)
        │ HTTP /api
        ▼
Flask (localhost:5000) ──► repository + deterministic risk/reconciliation rules
        │
        ▼
Exasol Personal / CFS_DEMO (127.0.0.1:8563)
```

`backend/seed.py` creates the dedicated `CFS_DEMO` schema and merges fixed
synthetic rows. Flask queries invoices, customers, payments and audit events
through `backend/db.py`. Risk scoring runs transparently in Python over records
retrieved from the selected store; the UI never embeds dashboard numbers.

## Data dictionary

| Entity | Key fields | Purpose |
|---|---|---|
| CUSTOMERS | id, avg_days_late, late_rate | historical payment behaviour |
| INVOICES | id, invoice_number, due_date, amount, status | receivable registry |
| PAYMENTS | id, invoice_id, amount, reference | settlement and reconciliation evidence |
| AUDIT_EVENTS | id, event_type, created_at | review/reconciliation traceability |

## Rules

- Duplicate: invoice number appears more than once.
- Partial: an invoice marked partial has remaining balance.
- Mismatch: invoice marked paid has a non-zero balance.
- Unmatched: payment has no invoice identifier.
- Deduction: a payment reference contains `DEDUCTION`; it is an investigation cue, not proof of fraud.

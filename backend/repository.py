from __future__ import annotations

from datetime import datetime, timezone

from backend.analytics import collection_priority, risk_assessment
from backend.db import connect


def _records(sql: str, params: tuple = ()) -> list[dict]:
    db = connect()
    try:
        return db.records(sql, params)
    finally:
        db.close()


def invoice_rows() -> list[dict]:
    return _records("""
      SELECT i.*, c.name customer_name, c.avg_days_late, c.late_rate,
      COALESCE(p.paid_amount, 0) paid_amount
      FROM {{SCHEMA}}.invoices i JOIN {{SCHEMA}}.customers c ON c.id=i.customer_id
      LEFT JOIN (
        SELECT invoice_id, SUM(amount) AS paid_amount
        FROM {{SCHEMA}}.payments
        WHERE invoice_id IS NOT NULL
        GROUP BY invoice_id
      ) p ON p.invoice_id=i.id
      ORDER BY i.due_date ASC
    """)


def enriched_invoices() -> list[dict]:
    result = []
    for row in invoice_rows():
        assessment = risk_assessment(row, row)
        row.update({"outstanding": assessment["outstanding"], "risk": assessment})
        result.append(row)
    return result


def alerts() -> list[dict]:
    rows = enriched_invoices(); result = []
    by_number: dict[str, list[dict]] = {}
    for invoice in rows: by_number.setdefault(invoice["invoice_number"], []).append(invoice)
    for number, grouped in by_number.items():
        if len(grouped) > 1:
            result.append({"id": f"duplicate-{number}", "severity": "high", "type": "Likely duplicate invoice", "record_ids": [x["id"] for x in grouped], "compared_amounts": [x["amount"] for x in grouped], "discrepancy_amount": grouped[0]["amount"], "reason": f"Invoice identifier {number} occurs {len(grouped)} times.", "suggested_step": "Confirm whether this is a correction or duplicate bill before payment."})
    for row in rows:
        if row["status"] == "partial" and row["outstanding"] > 0:
            result.append({"id": f"partial-{row['id']}", "severity": "medium", "type": "Partial payment", "record_ids": [row["id"]], "compared_amounts": [row["amount"], row["paid_amount"]], "discrepancy_amount": row["outstanding"], "reason": "Recorded payment does not settle the invoice.", "suggested_step": "Request remittance advice and confirm the balance."})
        if row["status"] == "paid" and abs(row["outstanding"]) > .01:
            result.append({"id": f"mismatch-{row['id']}", "severity": "high", "type": "Invoice/payment mismatch", "record_ids": [row["id"]], "compared_amounts": [row["amount"], row["paid_amount"]], "discrepancy_amount": row["outstanding"], "reason": "Status is paid but payment total differs from invoice value.", "suggested_step": "Review status and reconcile payment reference."})
    for payment in _records("SELECT * FROM {{SCHEMA}}.payments WHERE invoice_id IS NULL"):
        result.append({"id": f"unmatched-{payment['id']}", "severity": "medium", "type": "Unmatched payment", "record_ids": [payment["id"]], "compared_amounts": [payment["amount"]], "discrepancy_amount": payment["amount"], "reason": f"Payment {payment['reference']} has no linked invoice.", "suggested_step": "Match the remittance to an invoice or record the reason."})
    for payment in _records("SELECT * FROM {{SCHEMA}}.payments WHERE reference LIKE ?", ("%DEDUCTION%",)):
        result.append({"id": f"deduction-{payment['id']}", "severity": "medium", "type": "Unexpected deduction reference", "record_ids": [payment["id"], payment["invoice_id"]], "compared_amounts": [payment["amount"]], "discrepancy_amount": payment["amount"], "reason": f"Payment reference {payment['reference']} indicates a deduction requiring supporting evidence.", "suggested_step": "Obtain the deduction note and approve or dispute it."})
    return sorted(result, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])


def dashboard() -> dict:
    invoices = enriched_invoices()
    open_rows = [x for x in invoices if x["outstanding"] > 0]
    priorities = collections(invoices)
    return {
      "reporting_date": datetime.now(timezone.utc).date().isoformat(),
      "metrics": {"outstanding": round(sum(x["outstanding"] for x in open_rows), 2), "overdue": round(sum(x["outstanding"] for x in open_rows if x["risk"]["overdue_days"] > 0), 2), "high_risk_count": sum(x["risk"]["level"] == "high" for x in open_rows), "discrepancy_count": len(alerts())},
      "expected_collections": [{"bucket": "0–7 days", "amount": round(sum(x["outstanding"] for x in open_rows if x["risk"]["overdue_days"] == 0), 2)}, {"bucket": "Overdue", "amount": round(sum(x["outstanding"] for x in open_rows if x["risk"]["overdue_days"] > 0), 2)}],
      "recent_alerts": alerts()[:4], "top_collections": priorities[:4]
    }


def collections(invoices: list[dict] | None = None) -> list[dict]:
    invoices = invoices or enriched_invoices()
    result = []
    for invoice in invoices:
        if invoice["outstanding"] > 0:
            result.append({"invoice_id": invoice["id"], "invoice_number": invoice["invoice_number"], "customer_name": invoice["customer_name"], **collection_priority(invoice, invoice["risk"]), "outstanding": invoice["outstanding"]})
    return sorted(result, key=lambda x: x["priority_score"], reverse=True)


def invoice_detail(invoice_id: str) -> dict | None:
    invoice = next((x for x in enriched_invoices() if x["id"] == invoice_id), None)
    if not invoice: return None
    invoice["payments"] = _records("SELECT * FROM {{SCHEMA}}.payments WHERE invoice_id=? ORDER BY payment_date", (invoice_id,))
    invoice["collection"] = collection_priority(invoice, invoice["risk"])
    return invoice


def audit_reconciliation() -> dict:
    from uuid import uuid4
    db = connect()
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO {{SCHEMA}}.audit_events(id,event_type,created_at,details) VALUES(?,?,?,?)",
            (str(uuid4()), "reconciliation_run", timestamp, "Deterministic reconciliation completed"),
        )
    finally:
        db.close()
    detected = alerts()
    return {
        "status": "completed",
        "alerts_found": len(detected),
        "message": "Reconciliation completed; suspected discrepancies require human review.",
    }

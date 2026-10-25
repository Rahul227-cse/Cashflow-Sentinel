from __future__ import annotations

from backend.db import SQLiteStore, connect, initialize

CUSTOMERS = [
    ("C001", "Aster Retail Pvt Ltd", 12, .68), ("C002", "BlueRiver Foods", 4, .22),
    ("C003", "Cedar Works", 19, .81), ("C004", "Dawn Mart", 2, .10),
]
INVOICES = [
    ("INV001", "C001", "AST-1048", "2026-08-01", "2026-08-31", 125000, "open", "SUP001"),
    ("INV002", "C002", "BRF-2051", "2026-09-05", "2026-10-05", 68000, "partial", "SUP001"),
    ("INV003", "C003", "CED-882", "2026-07-12", "2026-08-11", 210000, "open", "SUP001"),
    ("INV004", "C004", "DWN-777", "2026-10-01", "2026-10-31", 32500, "open", "SUP001"),
    ("INV005", "C001", "AST-1048", "2026-08-01", "2026-08-31", 125000, "open", "SUP001"),
    ("INV006", "C002", "BRF-2060", "2026-09-18", "2026-10-18", 91000, "paid", "SUP001"),
]
PAYMENTS = [
    ("PAY001", "INV002", "2026-10-10", 40000, "NEFT-BRF-1"),
    ("PAY002", "INV006", "2026-10-23", 85000, "NEFT-BRF-2"),
    ("PAY003", None, "2026-10-20", 15000, "UNMATCHED-778"),
    ("PAY004", "INV001", "2026-10-22", 5000, "DEDUCTION-UNEXPLAINED"),
]


def _merge(db, table: str, columns: tuple[str, ...], row: tuple) -> None:
    """Idempotently insert/update only CashFlow Sentinel's own stable IDs."""
    projection = ", ".join(f"? AS {column}" for column in columns)
    updates = ", ".join(f"T.{column}=S.{column}" for column in columns[1:])
    names = ", ".join(columns)
    values = ", ".join(f"S.{column}" for column in columns)
    db.execute(f"MERGE INTO {{{{SCHEMA}}}}.{table} T USING (SELECT {projection} FROM DUAL) S ON (T.ID=S.ID) WHEN MATCHED THEN UPDATE SET {updates} WHEN NOT MATCHED THEN INSERT ({names}) VALUES ({values})", row)


def seed() -> None:
    db = connect(); initialize(db)
    try:
        if isinstance(db, SQLiteStore):
            for table in ("payments", "invoices", "customers", "audit_events"): db.execute(f"DELETE FROM {table}")
            db.many("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS)
            db.many("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?)", INVOICES)
            db.many("INSERT INTO payments VALUES (?, ?, ?, ?, ?)", PAYMENTS)
        else:
            for row in CUSTOMERS: _merge(db, "CUSTOMERS", ("ID", "NAME", "AVG_DAYS_LATE", "LATE_RATE"), row)
            for row in INVOICES: _merge(db, "INVOICES", ("ID", "CUSTOMER_ID", "INVOICE_NUMBER", "INVOICE_DATE", "DUE_DATE", "AMOUNT", "STATUS", "SUPPLIER_ID"), row)
            for row in PAYMENTS: _merge(db, "PAYMENTS", ("ID", "INVOICE_ID", "PAYMENT_DATE", "AMOUNT", "REFERENCE"), row)
    finally:
        db.close()


if __name__ == "__main__": seed()

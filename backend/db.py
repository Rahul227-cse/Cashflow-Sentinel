from __future__ import annotations

import os
import re
import sqlite3
import ssl
from pathlib import Path
from typing import Any, Protocol

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT NOT NULL, avg_days_late REAL NOT NULL, late_rate REAL NOT NULL);
CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, invoice_number TEXT NOT NULL, invoice_date TEXT NOT NULL, due_date TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL, supplier_id TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id));
CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, invoice_id TEXT, payment_date TEXT NOT NULL, amount REAL NOT NULL, reference TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL);
"""

class Store(Protocol):
    name: str
    def records(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None: ...
    def close(self) -> None: ...

def load_local_env() -> None:
    """Load gitignored local configuration without overwriting supplied variables."""
    env_file = Path(".env")
    if not env_file.is_file(): return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1); os.environ.setdefault(key.strip(), value.strip())

def _schema_name() -> str:
    name = os.getenv("EXASOL_SCHEMA", "CFS_DEMO").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,62}", name): raise ValueError("EXASOL_SCHEMA must be an uppercase SQL identifier")
    return name

class SQLiteStore:
    name = "sqlite-test"
    def __init__(self) -> None:
        configured = os.getenv("DATABASE_URL", "sqlite:///cashflow_sentinel.db")
        self.connection = sqlite3.connect(configured.removeprefix("sqlite:///")); self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
    def initialize(self) -> None:
        self.connection.executescript(SQLITE_SCHEMA)
        cols = {row["name"].lower(): row["type"].upper() for row in self.connection.execute("PRAGMA table_info(audit_events)").fetchall()}
        if cols.get("id") != "TEXT":
            self.connection.execute("DROP TABLE audit_events")
            self.connection.execute("CREATE TABLE audit_events (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL)")
        self.connection.commit()
    def records(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: return [dict(row) for row in self.connection.execute(sql.replace("{{SCHEMA}}.", ""), params).fetchall()]
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None: self.connection.execute(sql.replace("{{SCHEMA}}.", ""), params); self.connection.commit()
    def many(self, sql: str, rows: list[tuple[Any, ...]]) -> None: self.connection.executemany(sql.replace("{{SCHEMA}}.", ""), rows); self.connection.commit()
    def close(self) -> None: self.connection.close()

class ExasolStore:
    name = "exasol"
    def __init__(self) -> None:
        load_local_env(); missing = [key for key in ("EXASOL_DSN", "EXASOL_USER", "EXASOL_PASSWORD") if not os.getenv(key)]
        if missing: raise RuntimeError("Exasol selected but missing " + ", ".join(missing) + ". Configure a local .env; SQLite requires CASHFLOW_STORE=sqlite.")
        import pyexasol
        self.schema = _schema_name()
        options: dict[str, Any] = {"dsn": os.environ["EXASOL_DSN"], "user": os.environ["EXASOL_USER"], "password": os.environ["EXASOL_PASSWORD"]}
        # Exasol Personal uses a self-signed certificate locally. This escape hatch is
        # deliberately opt-in and must only be used for the loopback development instance.
        if os.getenv("EXASOL_INSECURE_TLS", "").lower() == "true": options["websocket_sslopt"] = {"cert_reqs": ssl.CERT_NONE}
        self.connection = pyexasol.connect(**options)
    def initialize(self) -> None:
        content = (Path(__file__).with_name("sql") / "exasol_schema.sql").read_text(encoding="utf-8").replace("{{SCHEMA}}", self.schema)
        for statement in content.split(";\n"):
            if statement.strip(): self.connection.execute(statement)
    def _statement(self, sql: str, params: tuple[Any, ...]):
        query = sql.replace("{{SCHEMA}}", self.schema)
        for index in range(len(params)): query = query.replace("?", "{p" + str(index) + "}", 1)
        return query, ({"p" + str(index): value for index, value in enumerate(params)} or None)
    def records(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        query, arguments = self._statement(sql, params); stmt = self.connection.execute(query, arguments)
        columns = [(column[0] if isinstance(column, tuple) else column).lower() for column in stmt.columns()]
        return [dict(zip(columns, row)) for row in stmt.fetchall()]
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        query, arguments = self._statement(sql, params); self.connection.execute(query, arguments)
    def close(self) -> None: self.connection.close()

def connect() -> Store:
    store = os.getenv("CASHFLOW_STORE", "exasol").lower()
    if store == "sqlite": return SQLiteStore()
    if store == "exasol": return ExasolStore()
    raise ValueError("CASHFLOW_STORE must be 'exasol' or 'sqlite'")

def initialize(store: Store) -> None: getattr(store, "initialize")()

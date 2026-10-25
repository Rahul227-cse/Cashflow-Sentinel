import os

import pytest

from backend.db import connect, load_local_env
from backend.seed import seed


@pytest.mark.integration
def test_exasol_seed_and_query():
    load_local_env()
    if not all(os.getenv(key) for key in ("EXASOL_DSN", "EXASOL_USER", "EXASOL_PASSWORD")):
        pytest.skip("Exasol integration not configured: provide a local ignored .env with EXASOL_* values")
    previous = os.environ.get("CASHFLOW_STORE")
    os.environ["CASHFLOW_STORE"] = "exasol"
    try:
        seed()
        store = connect()
        try:
            rows = store.records("SELECT COUNT(*) AS COUNT FROM {{SCHEMA}}.INVOICES")
            assert rows[0]["count"] == 6
        finally:
            store.close()
    finally:
        if previous is None: os.environ.pop("CASHFLOW_STORE", None)
        else: os.environ["CASHFLOW_STORE"] = previous


@pytest.mark.integration
def test_exasol_reconciliation_endpoint_and_audit():
    load_local_env()
    if not all(os.getenv(key) for key in ("EXASOL_DSN", "EXASOL_USER", "EXASOL_PASSWORD")):
        pytest.skip("Exasol integration not configured: provide a local ignored .env with EXASOL_* values")
    previous = os.environ.get("CASHFLOW_STORE")
    os.environ["CASHFLOW_STORE"] = "exasol"
    try:
        from backend.app import create_app
        client = create_app().test_client()
        response = client.post("/api/reconciliation/run")
        assert response.status_code == 200
        data = response.json
        assert data["status"] == "completed"
        assert data["alerts_found"] >= 1
        assert "human review" in data["message"].lower()

        store = connect()
        try:
            events = store.records("SELECT * FROM {{SCHEMA}}.AUDIT_EVENTS WHERE EVENT_TYPE = 'reconciliation_run' ORDER BY CREATED_AT DESC")
            assert len(events) > 0
            assert events[0]["details"] == "Deterministic reconciliation completed"
            assert events[0]["created_at"] is not None
        finally:
            store.close()
    finally:
        if previous is None: os.environ.pop("CASHFLOW_STORE", None)
        else: os.environ["CASHFLOW_STORE"] = previous

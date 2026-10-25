import os
from backend.seed import seed

os.environ["DATABASE_URL"] = "sqlite:///test_cashflow.db"
os.environ["CASHFLOW_STORE"] = "sqlite"
from backend.app import create_app


def setup_module(): seed()


def test_dashboard_is_derived_from_data():
    response = create_app().test_client().get("/api/dashboard")
    assert response.status_code == 200
    assert response.json["metrics"]["outstanding"] > 0


def test_alerts_include_duplicate_and_unmatched_payment():
    response = create_app().test_client().get("/api/alerts")
    types = {alert["type"] for alert in response.json}
    assert {"Likely duplicate invoice", "Unmatched payment", "Unexpected deduction reference"} <= types


def test_risks_include_explanation():
    response = create_app().test_client().get("/api/risks")
    assert response.status_code == 200 and response.json[0]["factors"]


def test_invalid_page_is_rejected():
    response = create_app().test_client().get("/api/invoices?page=bad")
    assert response.status_code == 400


def test_run_reconciliation_success():
    from backend.db import connect
    response = create_app().test_client().post("/api/reconciliation/run")
    assert response.status_code == 200
    data = response.json
    assert data["status"] == "completed"
    assert data["alerts_found"] > 0
    assert "human review" in data["message"].lower()

    store = connect()
    try:
        events = store.records("SELECT * FROM {{SCHEMA}}.audit_events WHERE event_type = ? ORDER BY created_at DESC", ("reconciliation_run",))
        assert len(events) > 0
        assert events[0]["details"] == "Deterministic reconciliation completed"
        assert events[0]["created_at"]
    finally:
        store.close()


def test_run_reconciliation_method_not_allowed():
    response = create_app().test_client().get("/api/reconciliation/run")
    assert response.status_code == 405


def test_run_reconciliation_database_failure(monkeypatch):
    from backend import repository
    class FailingStore:
        def __init__(self):
            self.closed = False
        def execute(self, sql, params=()):
            raise RuntimeError("Simulated DB write failure")
        def close(self):
            self.closed = True
    failing_store = FailingStore()
    monkeypatch.setattr(repository, "connect", lambda: failing_store)
    response = create_app().test_client().post("/api/reconciliation/run")
    assert response.status_code == 500
    assert "Simulated DB write failure" in response.json["error"]
    assert failing_store.closed is True

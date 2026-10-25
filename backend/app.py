from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.repository import alerts, audit_reconciliation, collections, dashboard, enriched_invoices, invoice_detail
from backend.db import connect


def create_app() -> Flask:
    app = Flask(__name__); CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    @app.get("/api/health")
    def health():
        store = connect()
        try: return jsonify({"status": "ok", "store": store.name})
        finally: store.close()

    @app.get("/api/dashboard")
    def get_dashboard(): return jsonify(dashboard())

    @app.get("/api/invoices")
    def get_invoices():
        try:
            page = max(1, int(request.args.get("page", 1))); size = min(100, max(1, int(request.args.get("page_size", 20))))
        except ValueError: return jsonify({"error": "page and page_size must be integers"}), 400
        query, status, risk = request.args.get("query", "").lower(), request.args.get("status", ""), request.args.get("risk", "")
        rows = [x for x in enriched_invoices() if (not query or query in x["invoice_number"].lower() or query in x["customer_name"].lower()) and (not status or x["status"] == status) and (not risk or x["risk"]["level"] == risk)]
        return jsonify({"items": rows[(page-1)*size:page*size], "total": len(rows), "page": page, "page_size": size})

    @app.get("/api/invoices/<invoice_id>")
    def get_invoice(invoice_id: str):
        value = invoice_detail(invoice_id)
        return (jsonify(value), 200) if value else (jsonify({"error": "invoice not found"}), 404)

    @app.get("/api/alerts")
    def get_alerts():
        severity = request.args.get("severity", "")
        if severity and severity not in {"high", "medium", "low"}: return jsonify({"error": "severity must be high, medium, or low"}), 400
        return jsonify([x for x in alerts() if not severity or x["severity"] == severity])

    @app.get("/api/collections")
    def get_collections(): return jsonify(collections())

    @app.get("/api/risks")
    def get_risks():
        return jsonify([{ "invoice_id": row["id"], "invoice_number": row["invoice_number"], "customer_name": row["customer_name"], **row["risk"] } for row in enriched_invoices()])

    @app.post("/api/reconciliation/run")
    def run_reconciliation():
        try:
            return jsonify(audit_reconciliation())
        except Exception as e:
            return jsonify({"error": f"Reconciliation failed: {str(e)}"}), 500
    return app


app = create_app()

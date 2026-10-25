from __future__ import annotations

from datetime import date


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def risk_assessment(invoice: dict, customer: dict, today: date | None = None) -> dict:
    """Explainable baseline score, deliberately not a machine-learning model."""
    today = today or date.today()
    due = date.fromisoformat(str(invoice["due_date"]))
    balance = float(invoice["amount"]) - float(invoice.get("paid_amount", 0))
    overdue_days = max(0, (today - due).days)
    historical_late = float(customer.get("avg_days_late") or 0)
    late_rate = float(customer.get("late_rate") or 0)
    history_points = clamp(historical_late * 3.5, 0, 35)
    timing_points = clamp(overdue_days * 2.5 if overdue_days else max(0, 10 - (due - today).days), 0, 30)
    amount_points = clamp(balance / 5000, 0, 20)
    behaviour_points = clamp(late_rate * 15, 0, 15)
    score = round(history_points + timing_points + amount_points + behaviour_points)
    level = "high" if score >= 70 else "medium" if score >= 40 else "low"
    factors = [
        {"label": "Historical late days", "points": round(history_points), "evidence": f"{historical_late:.1f} average days late"},
        {"label": "Timing", "points": round(timing_points), "evidence": f"{overdue_days} days overdue" if overdue_days else f"due in {(due - today).days} days"},
        {"label": "Open balance", "points": round(amount_points), "evidence": f"₹{balance:,.0f} outstanding"},
        {"label": "Payment history", "points": round(behaviour_points), "evidence": f"{late_rate:.0%} historical late-payment rate"},
    ]
    return {"score": score, "level": level, "factors": factors, "overdue_days": overdue_days, "outstanding": round(balance, 2)}


def collection_priority(invoice: dict, assessment: dict) -> dict:
    priority = round(min(100, assessment["score"] * .55 + min(assessment["overdue_days"] * 2, 25) + min(assessment["outstanding"] / 10000, 20)))
    if assessment["overdue_days"] > 0:
        action = "Call accounts payable and request a confirmed payment date"
    elif assessment["level"] == "high":
        action = "Send a proactive payment reminder before the due date"
    else:
        action = "Monitor as part of the normal collections cadence"
    return {"priority_score": priority, "suggested_action": action, "reason": f"{assessment['level'].title()} delay risk, {assessment['overdue_days']} overdue days, and ₹{assessment['outstanding']:,.0f} open balance"}

from datetime import date
from backend.analytics import risk_assessment


def test_high_risk_score_for_late_large_balance():
    result = risk_assessment({"due_date": "2026-08-01", "amount": 200000, "paid_amount": 0}, {"avg_days_late": 20, "late_rate": .8}, date(2026, 10, 25))
    assert result["level"] == "high" and result["score"] >= 70


def test_low_risk_score_for_recent_small_balance():
    result = risk_assessment({"due_date": "2026-11-10", "amount": 10000, "paid_amount": 0}, {"avg_days_late": 0, "late_rate": 0}, date(2026, 10, 25))
    assert result["level"] == "low"

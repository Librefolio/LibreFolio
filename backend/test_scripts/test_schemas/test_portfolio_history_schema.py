"""The income history point of the portfolio report on the wire (project 79, STK1-fix).

``IncomeHistoryPoint.reward`` (rewards in kind, REWARD) came with release 1.4. An answer from before it, or a report
captured then (the e2e fixture ``dashboard-report.json``), has no ``reward``: the point must still validate, and the
OpenAPI document must not list ``reward`` as required, or the generated client refuses the whole report. The service
always sends it.
"""

from __future__ import annotations

from decimal import Decimal

from backend.app.main import app
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio.history import IncomeHistoryPoint


def test_a_point_without_reward_validates_and_reads_none():
    point = IncomeHistoryPoint.model_validate({"date": "2025-10-31", "dividend": {"code": "EUR", "amount": "0"}, "interest": {"code": "EUR", "amount": "139.71"}})
    assert point.reward is None


def test_a_point_with_reward_keeps_it():
    point = IncomeHistoryPoint.model_validate({"date": "2025-10-31", "dividend": {"code": "EUR", "amount": "0"}, "interest": {"code": "EUR", "amount": "0"}, "reward": {"code": "EUR", "amount": "10"}})
    assert point.reward == Currency(code="EUR", amount=Decimal("10"))


def test_reward_is_not_required_in_the_openapi_document():
    schema = app.openapi()["components"]["schemas"]["IncomeHistoryPoint"]
    assert "reward" in schema["properties"]
    assert "reward" not in schema.get("required", [])
    assert {"date", "dividend", "interest"} <= set(schema.get("required", []))

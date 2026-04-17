"""
Tests for computed properties and methods at 0% coverage across schemas.

Covers:
- BRSummary: currencies, total_cash_positions, total_asset_positions
- BackwardFillInfo: actual_rate_date_str
- BaseBulkResponse: total_count, failed_count
- FXConversionResult: conversion_date_str
- FXUpsertResult: date_str
- FAPricePoint: close_cur, open_cur, high_cur, low_cur
- FACurrentValue: value_cur
- TXCreateItem / TXUpdateItem: _validate_tags, get_tags_csv
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from backend.app.schemas.common import BackwardFillInfo, BaseBulkResponse, Currency
from backend.app.schemas.fx import FXConversionResult, FXUpsertResult
from backend.app.schemas.prices import FACurrentValue, FAPricePoint
from backend.app.schemas.transactions import TXCreateItem, TXUpdateItem

# Helper for creating BRSummary with all required fields
_NOW = datetime.now(UTC)
_BR_BASE = {
    "id": 1,
    "name": "Test",
    "allow_cash_overdraft": False,
    "allow_asset_shorting": False,
    "is_active": True,
    "created_at": _NOW,
    "updated_at": _NOW,
}


# ============================================================================
# BRSummary computed properties
# ============================================================================


class TestBRSummaryComputed:
    """Test BRSummary computed properties (currencies, total_cash, total_asset)."""

    def test_currencies_from_cash_balances(self):
        from backend.app.schemas.brokers import BRSummary  # noqa: PLC0415 — test setup — imports after sys.path/db config

        summary = BRSummary(
            **_BR_BASE,
            cash_balances=[
                Currency(code="EUR", amount=Decimal("100")),
                Currency(code="USD", amount=Decimal("50")),
            ],
            holdings=[],
        )
        assert summary.currencies == ["EUR", "USD"]

    def test_currencies_empty(self):
        from backend.app.schemas.brokers import BRSummary  # noqa: PLC0415 — test setup — imports after sys.path/db config

        summary = BRSummary(**_BR_BASE, cash_balances=[], holdings=[])
        assert summary.currencies == []

    def test_total_cash_positions(self):
        from backend.app.schemas.brokers import BRSummary  # noqa: PLC0415 — test setup — imports after sys.path/db config

        summary = BRSummary(
            **_BR_BASE,
            cash_balances=[
                Currency(code="EUR", amount=Decimal("100")),
                Currency(code="GBP", amount=Decimal("200")),
                Currency(code="USD", amount=Decimal("300")),
            ],
            holdings=[],
        )
        assert summary.total_cash_positions == 3

    def test_total_asset_positions(self):
        from backend.app.schemas.brokers import BRAssetHolding, BRSummary  # noqa: PLC0415 — test setup — imports after sys.path/db config

        summary = BRSummary(
            **_BR_BASE,
            cash_balances=[],
            holdings=[
                BRAssetHolding(
                    asset_id=1,
                    asset_name="VWCE",
                    quantity=Decimal("10"),
                    total_cost=Currency(code="EUR", amount=Decimal("500")),
                    average_cost_per_unit=Decimal("50"),
                ),
            ],
        )
        assert summary.total_asset_positions == 1


# ============================================================================
# BackwardFillInfo
# ============================================================================


class TestBackwardFillInfo:
    def test_actual_rate_date_str(self):
        info = BackwardFillInfo(
            actual_rate_date=date(2025, 3, 15),
            days_back=1,
        )
        assert info.actual_rate_date_str() == "2025-03-15"


# ============================================================================
# BaseBulkResponse
# ============================================================================


class TestBaseBulkResponse:
    def test_total_count(self):
        resp = BaseBulkResponse[str](
            results=["a", "b", "c"],
            success_count=2,
        )
        assert resp.total_count == 3

    def test_failed_count(self):
        resp = BaseBulkResponse[str](
            results=["a", "b", "c"],
            success_count=1,
        )
        assert resp.failed_count == 2


# ============================================================================
# FX schemas
# ============================================================================


class TestFXConversionResult:
    def test_conversion_date_str(self):
        result = FXConversionResult(
            from_amount=Currency(code="EUR", amount=Decimal("100")),
            to_amount=Currency(code="USD", amount=Decimal("110")),
            rate=Decimal("1.1"),
            conversion_date=date(2025, 6, 15),
        )
        assert result.conversion_date_str() == "2025-06-15"


class TestFXUpsertResult:
    def test_date_str(self):
        result = FXUpsertResult(
            success=True,
            action="inserted",
            rate=Decimal("1.1"),
            date=date(2025, 6, 15),
            base="EUR",
            quote="USD",
        )
        assert result.date_str() == "2025-06-15"


# ============================================================================
# Price schemas
# ============================================================================


class TestFAPricePointCur:
    def _make_price(self, **kwargs):
        defaults = {
            "date": date(2025, 1, 1),
            "currency": "EUR",
            "close": Decimal("100.50"),
        }
        defaults.update(kwargs)
        return FAPricePoint(**defaults)

    def test_close_cur(self):
        p = self._make_price()
        assert p.close_cur == Currency(code="EUR", amount=Decimal("100.50"))

    def test_open_cur_present(self):
        p = self._make_price(open=Decimal("99"))
        assert p.open_cur == Currency(code="EUR", amount=Decimal("99"))

    def test_open_cur_none(self):
        p = self._make_price()
        assert p.open_cur is None

    def test_high_cur_present(self):
        p = self._make_price(high=Decimal("105"))
        assert p.high_cur == Currency(code="EUR", amount=Decimal("105"))

    def test_high_cur_none(self):
        p = self._make_price()
        assert p.high_cur is None

    def test_low_cur_present(self):
        p = self._make_price(low=Decimal("95"))
        assert p.low_cur == Currency(code="EUR", amount=Decimal("95"))

    def test_low_cur_none(self):
        p = self._make_price()
        assert p.low_cur is None


class TestFACurrentValueCur:
    def test_value_cur(self):
        cv = FACurrentValue(
            value=Decimal("42.5"),
            currency="USD",
            as_of_date=date(2025, 1, 1),
        )
        assert cv.value_cur == Currency(code="USD", amount=Decimal("42.5"))


# ============================================================================
# Transaction tag helpers
# ============================================================================


class TestTXTagHelpers:
    def test_create_item_tags_from_csv_string(self):
        """TXCreateItem._validate_tags converts comma-separated string to list."""
        item = TXCreateItem(
            broker_id=1,
            type="DEPOSIT",
            date=date(2025, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags="foo,bar",
        )
        assert item.tags == ["foo", "bar"]

    def test_create_item_tags_none(self):
        item = TXCreateItem(
            broker_id=1,
            type="DEPOSIT",
            date=date(2025, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags=None,
        )
        assert item.tags is None

    def test_create_item_get_tags_csv(self):
        item = TXCreateItem(
            broker_id=1,
            type="DEPOSIT",
            date=date(2025, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("500")),
            tags=["alpha", "beta"],
        )
        csv = item.get_tags_csv()
        assert csv == "alpha,beta"

    def test_create_item_get_tags_csv_none(self):
        item = TXCreateItem(
            broker_id=1,
            type="DEPOSIT",
            date=date(2025, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags=None,
        )
        assert item.get_tags_csv() is None

    def test_update_item_tags_validation(self):
        item = TXUpdateItem(id=1, tags="x,y,z")
        assert item.tags == ["x", "y", "z"]

    def test_update_item_get_tags_csv(self):
        item = TXUpdateItem(id=1, tags=["a", "b"])
        assert item.get_tags_csv() == "a,b"

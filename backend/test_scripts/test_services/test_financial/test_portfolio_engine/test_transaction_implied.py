"""Unit tests for transaction-implied valuation in DailyStateBuilder.

Tests the TRANSACTION_IMPLIED fallback: when an asset has no PriceHistory
but has a WAC series, the engine uses open_cost_basis as the market_value
proxy and tracks the asset in transaction_implied_asset_ids.

Pure tests — no DB, no async.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
)

# =============================================================================
# HELPERS (same pattern as test_daily_state_builder.py)
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = 10,
    type: str = "DEPOSIT",
    dt: str = "2025-01-01",
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = date.fromisoformat(dt)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _ctxn(tx: MagicMock, share: str = "1") -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification="normal", share=Decimal(share))


def _builder(
    *,
    classified_txs=None,
    price_map=None,
    wac_series=None,
    quote_base_map=None,
    fx_rate_map=None,
    date_from: str = "2025-01-01",
    date_to: str = "2025-01-01",
    target_currency: str = "EUR",
) -> DailyStateBuilder:
    return DailyStateBuilder(
        classified_txs=classified_txs or [],
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map=price_map or {},
        quote_base_map=quote_base_map or {},
        wac_series=wac_series or {},
        fx_rate_map=fx_rate_map or {},
        asset_classifications={},
        asset_types={},
        target_currency=target_currency,
        date_from=date.fromisoformat(date_from),
        date_to=date.fromisoformat(date_to),
    )


# =============================================================================
# TEST: BUY asset without PriceHistory → TRANSACTION_IMPLIED
# =============================================================================


class TestTransactionImpliedWithoutPriceHistory:
    """Asset bought before first PriceHistory → NAV should not drop to zero."""

    def test_no_price_no_wac_asset_excluded_from_nav(self):
        """MISSING path: no price, no WAC → market_value=0, asset in missing set."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-05", type="DEPOSIT", amount="10000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-9950", quantity="100", asset_id=999)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={},  # no prices
            wac_series={},  # no WAC
            date_from="2025-01-05",
            date_to="2025-01-05",
        )
        states = builder.build()
        assert len(states) == 1
        s = states[0]
        assert 999 in s.missing_price_asset_ids
        assert 999 not in s.transaction_implied_asset_ids
        assert s.market_value == Decimal("0")

    def test_no_price_with_wac_uses_implied_valuation(self):
        """TRANSACTION_IMPLIED path: no price, WAC present → market_value > 0."""
        buy_date = date(2025, 1, 5)
        txs = [
            # DEPOSIT and BUY on the same day so both are in range
            _ctxn(_tx(id=1, dt="2025-01-05", type="DEPOSIT", amount="10000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-9950", quantity="100", asset_id=999)),
        ]
        # WAC = 99.50 EUR per unit
        wac_series = {(999, 10): [(buy_date, Decimal("99.50"), "EUR")]}

        builder = _builder(
            classified_txs=txs,
            price_map={},  # no market prices yet
            wac_series=wac_series,
            date_from="2025-01-05",
            date_to="2025-01-05",
        )
        states = builder.build()
        s = states[0]

        # Asset should NOT be in missing set
        assert 999 not in s.missing_price_asset_ids
        # Asset SHOULD be in implied set
        assert 999 in s.transaction_implied_asset_ids
        # Market value should be qty × WAC = 100 × 99.50 = 9950
        assert s.market_value == Decimal("9950")
        # Cash = 10000 - 9950 = 50; NAV = 9950 + 50 = 10000
        assert s.nav_value == Decimal("10000")

    def test_market_price_overrides_transaction_implied(self):
        """Once PriceHistory exists, MARKET_PRICE takes precedence over implied."""
        buy_date = date(2025, 1, 5)
        price_date = date(2025, 1, 10)
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="10000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-9950", quantity="100", asset_id=999)),
        ]
        wac_series = {(999, 10): [(buy_date, Decimal("99.50"), "EUR")]}
        # Price appears on Jan 10 = 101.00
        price_map = {999: [(price_date, Decimal("101.00"), "EUR")]}

        builder = _builder(
            classified_txs=txs,
            price_map=price_map,
            wac_series=wac_series,
            date_from="2025-01-05",
            date_to="2025-01-12",
        )
        states = builder.build()

        # Days before price: implied
        pre_price = [s for s in states if s.date < price_date]
        for s in pre_price:
            assert 999 in s.transaction_implied_asset_ids
            assert 999 not in s.missing_price_asset_ids

        # Days from first price onwards: market price, not implied
        post_price = [s for s in states if s.date >= price_date]
        for s in post_price:
            assert 999 not in s.transaction_implied_asset_ids
            assert 999 not in s.missing_price_asset_ids
            # Market value should use actual price (101 × 100 = 10100)
            assert s.market_value == Decimal("10100")

    def test_btp_with_quote_base_quantity(self):
        """BTP scenario: nominal qty=10000, quote_base_quantity=100, WAC in EUR.

        For TRANSACTION_IMPLIED we use WAC × qty directly as open_cost_basis.
        Result should be positive and match the purchase amount approximately.
        """
        buy_date = date(2025, 1, 5)
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-05", type="DEPOSIT", amount="10000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-9850", quantity="10000", asset_id=888)),
        ]
        # WAC per unit = 0.985 EUR (nominal-based: 0.985 × 10000 = 9850 total cost)
        wac_series = {(888, 10): [(buy_date, Decimal("0.985"), "EUR")]}

        builder = _builder(
            classified_txs=txs,
            price_map={},
            wac_series=wac_series,
            date_from="2025-01-05",
            date_to="2025-01-05",
        )
        states = builder.build()
        s = states[0]

        assert 888 in s.transaction_implied_asset_ids
        assert 888 not in s.missing_price_asset_ids
        # open_cost_basis ~ WAC × qty = 0.985 × 10000 = 9850
        assert s.market_value == Decimal("9850")

    def test_missing_price_without_cost_basis_stays_error(self):
        """Asset with no price AND no WAC stays in missing set (MISSING_PRICE error)."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-05", type="DEPOSIT", amount="5000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-4900", quantity="50", asset_id=777)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={},
            wac_series={},  # no WAC either
            date_from="2025-01-05",
            date_to="2025-01-05",
        )
        states = builder.build()
        s = states[0]

        assert 777 in s.missing_price_asset_ids
        assert 777 not in s.transaction_implied_asset_ids
        assert s.market_value == Decimal("0")
        assert s.nav_complete is False

    def test_nav_complete_is_true_for_implied(self):
        """nav_complete = True when all assets have value (even implied), False only for fully missing."""
        buy_date = date(2025, 1, 5)
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-05", type="DEPOSIT", amount="10000")),
            _ctxn(_tx(id=2, dt="2025-01-05", type="BUY", amount="-9950", quantity="100", asset_id=999)),
        ]
        wac_series = {(999, 10): [(buy_date, Decimal("99.50"), "EUR")]}
        builder = _builder(
            classified_txs=txs,
            price_map={},
            wac_series=wac_series,
            date_from="2025-01-05",
            date_to="2025-01-05",
        )
        states = builder.build()
        s = states[0]
        # Implied assets have a value, so nav_complete should be True
        assert s.nav_complete is True
        assert len(s.missing_price_asset_ids) == 0

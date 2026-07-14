"""Unit tests for Cash Decomposition (Capital Baseline narrative).

Tests validate the formulas:
    capital_baseline = cumulative_external_cash_flow
    book_asset_like = open_cost_basis + in_transit_asset_cost_basis
    cash_like = cash_value + in_transit_cash_value
    cash_from_contributed_capital = min(cash_like, max(capital_baseline - book_asset_like, 0))
    cash_from_generated_returns = cash_like - cash_from_contributed_capital
    total_pnl = nav_value - capital_baseline

Invariants:
    cash_from_contributed_capital >= 0
    cash_from_generated_returns >= 0
    cash_from_contributed + cash_from_generated == cash_like (within rounding)
    total_pnl == nav_value - capital_baseline

Pure tests — no DB, no async. Uses mock Transaction objects + DailyStateBuilder.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
)

# =============================================================================
# HELPERS
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
    related_id: int | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
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
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _ctxn(
    tx: MagicMock,
    classification: str = "normal",
    share: str = "1",
    paired: MagicMock | None = None,
) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share), paired_tx=paired)


# Market price for asset 100 = its BUY unit cost, so market_value == open_cost_basis
# (no unrealized gain/loss). The engine no longer falls back to WAC for valuation
# (MARKET_PRICE → LAST_BUY_PRICE → MISSING), so a price is required for NAV to be
# complete; these cash-decomposition tests are about the cash formula, not valuation.
_PRICE_MAP_100 = {100: [(date(2025, 1, 1), Decimal("100"), "EUR")]}


def _builder(txs, ecfs, **overrides) -> DailyStateBuilder:
    """Build with cost basis for asset 100 provided implicitly by its BUY tx (WAC is
    computed inline by the builder — no external wac_series needed anymore)."""
    defaults = {
        "classified_txs": txs,
        "in_transit_intervals": [],
        "external_cash_flows": ecfs,
        "price_map": {},
        "quote_base_map": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "asset_currencies": {},
        "target_currency": "EUR",
        "date_from": date(2025, 1, 1),
        "date_to": date(2025, 1, 1),
    }
    defaults.update(overrides)
    return DailyStateBuilder(**defaults)


def _last_state(txs, ecfs, **kwargs):
    """Build states and return the last one for single-day assertions."""
    builder = _builder(txs, ecfs, **kwargs)
    result = builder.build()
    return result.daily_states[-1]


def _assert_invariants(state):
    """Verify cash decomposition invariants hold."""
    zero = Decimal("0")
    # Non-negativity
    assert state.cash_from_contributed_capital >= zero, f"cash_from_contributed_capital must be >= 0, got {state.cash_from_contributed_capital}"
    assert state.cash_from_generated_returns >= zero, f"cash_from_generated_returns must be >= 0, got {state.cash_from_generated_returns}"
    # Sum = cash_like
    cash_like = state.cash_value + state.in_transit_cash_value
    decomp_sum = state.cash_from_contributed_capital + state.cash_from_generated_returns
    assert abs(decomp_sum - cash_like) < Decimal("0.01"), f"Decomposition sum {decomp_sum} != cash_like {cash_like}"
    # total_pnl = nav - capital_baseline
    capital_baseline = state.cumulative_external_cash_flow
    expected_pnl = state.nav_value - capital_baseline
    assert abs(state.total_pnl - expected_pnl) < Decimal("0.01"), f"total_pnl {state.total_pnl} != nav {state.nav_value} - baseline {capital_baseline} = {expected_pnl}"


# =============================================================================
# EXAMPLE A: Deposit + Buy → all capital deployed, no cash, no P&L
# =============================================================================


class TestExampleA:
    """DEPOSIT 1000, BUY 1000 → capital fully deployed."""

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]
        # WAC: BUY 10 units at 100 → WAC = 100 per unit

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("1000")  # capital_baseline
        assert state.cash_value == Decimal("0")
        assert state.open_cost_basis == Decimal("1000")  # WAC 100 × 10 qty
        assert state.cash_from_contributed_capital == Decimal("0")
        assert state.cash_from_generated_returns == Decimal("0")
        assert state.total_pnl == Decimal("0")
        _assert_invariants(state)


# =============================================================================
# EXAMPLE B: Deposit + Buy + Interest → returns show as cash_from_generated
# =============================================================================


class TestExampleB:
    """DEPOSIT 1000, BUY 1000, INTEREST 100 → 100€ returns in cash."""

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="INTEREST", amount="100")),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.cash_value == Decimal("100")  # interest received
        assert state.open_cost_basis == Decimal("1000")
        # capital_baseline(1000) - book_asset_like(1000) = 0 → cash_from_contributed = min(100, 0) = 0
        assert state.cash_from_contributed_capital == Decimal("0")
        assert state.cash_from_generated_returns == Decimal("100")
        # NAV = 1000 (market_value, implied at cost) + 100 (cash) = 1100
        # total_pnl = 1100 - 1000 = 100
        assert state.total_pnl == Decimal("100")
        _assert_invariants(state)


# =============================================================================
# EXAMPLE C: Sell in Gain → realized gain appears in cash_from_generated
# =============================================================================


class TestExampleC:
    """DEPOSIT 1000, BUY 1000 (10 units), SELL 1 unit (cost 100) at 120."""

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="SELL", amount="120", quantity="-1", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]
        # After BUY 10 at 100, then SELL 1: WAC still 100, qty=9 → cost_basis=900

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.cash_value == Decimal("120")  # -1000 + 120 = 120? No: 1000-1000+120=120
        assert state.open_cost_basis == Decimal("900")  # 9 × 100
        # capital_baseline(1000) - book_asset_like(900) = 100
        # cash_from_contributed = min(120, 100) = 100
        assert state.cash_from_contributed_capital == Decimal("100")
        # cash_from_generated = 120 - 100 = 20
        assert state.cash_from_generated_returns == Decimal("20")
        # NAV = market(900, implied) + cash(120) = 1020
        # total_pnl = 1020 - 1000 = 20
        assert state.total_pnl == Decimal("20")
        _assert_invariants(state)


# =============================================================================
# EXAMPLE D: Sell in Loss → cash_from_generated stays 0
# =============================================================================


class TestExampleD:
    """DEPOSIT 1000, BUY 1000 (10 units), SELL 1 unit (cost 100) at 80."""

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="SELL", amount="80", quantity="-1", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.cash_value == Decimal("80")  # 1000-1000+80=80
        assert state.open_cost_basis == Decimal("900")  # 9 × 100
        # capital_baseline(1000) - book_asset_like(900) = 100
        # cash_from_contributed = min(80, 100) = 80
        assert state.cash_from_contributed_capital == Decimal("80")
        # cash_from_generated = 80 - 80 = 0
        assert state.cash_from_generated_returns == Decimal("0")
        # NAV = 900 + 80 = 980
        # total_pnl = 980 - 1000 = -20
        assert state.total_pnl == Decimal("-20")
        _assert_invariants(state)


# =============================================================================
# EXAMPLE E: P2P Repayment + Interest
# =============================================================================


class TestExampleE:
    """DEPOSIT 1000, BUY/P2P 1000, SELL/repayment 100, INTEREST 10."""

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            # Repayment: SELL 1 unit at cost (100)
            _ctxn(_tx(id=3, dt="2025-01-01", type="SELL", amount="100", quantity="-1", asset_id=100)),
            _ctxn(_tx(id=4, dt="2025-01-01", type="INTEREST", amount="10")),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.cash_value == Decimal("110")  # 1000-1000+100+10=110
        assert state.open_cost_basis == Decimal("900")  # 9 × 100
        # capital_baseline(1000) - book_asset_like(900) = 100
        # cash_from_contributed = min(110, 100) = 100
        assert state.cash_from_contributed_capital == Decimal("100")
        # cash_from_generated = 110 - 100 = 10
        assert state.cash_from_generated_returns == Decimal("10")
        # NAV = 900 + 110 = 1010
        # total_pnl = 1010 - 1000 = 10
        assert state.total_pnl == Decimal("10")
        _assert_invariants(state)


# =============================================================================
# EXAMPLE F: Interest + Withdrawal → baseline shrinks, P&L preserved
# =============================================================================


class TestExampleF:
    """DEPOSIT 1000, BUY 1000, INTEREST 100, WITHDRAWAL 100.

    The interest was earned, then withdrawn. P&L should still be +100
    because baseline decreased by 100 (from 1000 to 900).
    """

    def test_cash_decomposition(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="INTEREST", amount="100")),
            _ctxn(_tx(id=4, dt="2025-01-01", type="WITHDRAWAL", amount="-100")),
        ]
        # ECF: +1000 (deposit) -100 (withdrawal) = 900 net
        ecfs = [
            (date(2025, 1, 1), Decimal("1000"), "EUR"),
            (date(2025, 1, 1), Decimal("-100"), "EUR"),
        ]

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cumulative_external_cash_flow == Decimal("900")  # 1000 - 100
        assert state.cash_value == Decimal("0")  # 1000-1000+100-100=0
        assert state.open_cost_basis == Decimal("1000")
        # capital_baseline(900) - book_asset_like(1000) = -100 → max(-100, 0) = 0
        # cash_from_contributed = min(0, 0) = 0
        assert state.cash_from_contributed_capital == Decimal("0")
        assert state.cash_from_generated_returns == Decimal("0")
        # NAV = 1000 (implied cost) + 0 (cash) = 1000
        # total_pnl = 1000 - 900 = 100 ← the earned interest is preserved as P&L!
        assert state.total_pnl == Decimal("100")
        _assert_invariants(state)


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Edge cases for the cash decomposition formula."""

    def test_only_deposit_no_buy(self):
        """All capital sits in cash → cash_from_contributed = full amount."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="5000")),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("5000"), "EUR")]

        state = _last_state(txs, ecfs)

        assert state.cash_value == Decimal("5000")
        assert state.open_cost_basis == Decimal("0")
        # capital_baseline(5000) - book_asset_like(0) = 5000
        # cash_from_contributed = min(5000, 5000) = 5000
        assert state.cash_from_contributed_capital == Decimal("5000")
        assert state.cash_from_generated_returns == Decimal("0")
        assert state.total_pnl == Decimal("0")
        _assert_invariants(state)

    def test_fee_reduces_cash(self):
        """FEE reduces cash → still correctly decomposed."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="INTEREST", amount="50")),
            _ctxn(_tx(id=4, dt="2025-01-01", type="FEE", amount="-10")),
        ]
        ecfs = [(date(2025, 1, 1), Decimal("1000"), "EUR")]

        state = _last_state(txs, ecfs, price_map=_PRICE_MAP_100)

        assert state.cash_value == Decimal("40")  # 1000-1000+50-10=40
        # capital_baseline(1000) - book_asset_like(1000) = 0
        # cash_from_contributed = min(40, 0) = 0
        assert state.cash_from_contributed_capital == Decimal("0")
        # All cash is from returns (interest minus fee)
        assert state.cash_from_generated_returns == Decimal("40")
        # total_pnl = (1000+40) - 1000 = 40
        assert state.total_pnl == Decimal("40")
        _assert_invariants(state)

    def test_empty_portfolio(self):
        """No transactions → all zeros."""
        state = _last_state([], [])

        assert state.cash_from_contributed_capital == Decimal("0")
        assert state.cash_from_generated_returns == Decimal("0")
        assert state.total_pnl == Decimal("0")
        _assert_invariants(state)

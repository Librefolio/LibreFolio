"""Regression tests: performance inputs must fold in in-kind ADJUSTMENT capital.

A priced in-kind ADJUSTMENT (opening equity / succession / transfer) injects book
value into NAV with NO cash counterpart. The engine routes that cost into the
capital baseline (``cumulative_external_cash_flow``). ``build_performance_inputs``
MUST derive its capital-flow series from that baseline — NOT from the cash-only
``external_cash_flow`` field — otherwise the invested denominator omits the in-kind
capital and ROI explodes to thousands of percent on in-kind-seeded portfolios.

See PortfolioCalculationEngine._is_capital_adjustment and the capital-baseline
narrative. This guards the "3000% ROI on the 3y range" bug from regressing.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import ClassifiedTransaction, DailyStateBuilder, DerivedViewsBuilder
from backend.app.utils.financial.roi_utils import calculate_simple_roi_series


def _tx(*, id: int, type: str, dt: str, amount: str = "0", currency: str | None = "EUR", quantity: str = "0", asset_id: int | None = None, cost_basis_override: str | None = None, cost_basis_currency: str | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = 10
    tx.type = TransactionType(type)
    tx.date = date.fromisoformat(dt)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    tx.asset_event_id = None
    return tx


def _ctxn(tx: MagicMock) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification="normal", share=Decimal("1"), paired_tx=None)


def _build_states(txs, ecfs, date_from, date_to):
    builder = DailyStateBuilder(
        classified_txs=txs,
        in_transit_intervals=[],
        external_cash_flows=ecfs,
        price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
        quote_base_map={},
        fx_rate_map={},
        asset_classifications={},
        asset_types={},
        asset_currencies={100: "EUR"},
        target_currency="EUR",
        date_from=date_from,
        date_to=date_to,
    )
    return builder.build().daily_states


class TestPerformanceInputsInKind:
    """In-kind ADJUSTMENT capital must appear in the performance capital-flow series."""

    def test_inkind_capital_is_in_flow_series(self):
        # Opening seed: in-kind ADJUSTMENT of 100 units @ 100 EUR = 10,000 book value,
        # NO cash. Plus a tiny 100 EUR cash deposit.
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="100", asset_id=100, cost_basis_override="100", cost_basis_currency="EUR")
        dep = _tx(id=2, type="DEPOSIT", dt="2025-01-01", amount="100", currency="EUR")
        states = _build_states([_ctxn(adj), _ctxn(dep)], [(date(2025, 1, 1), Decimal("100"), "EUR")], date(2025, 1, 1), date(2025, 1, 1))

        _navs, cash_flows = DerivedViewsBuilder(states, "EUR").build_performance_inputs()

        # Contribution = -amount (investor perspective). Must equal the capital baseline
        # (10,000 in-kind + 100 cash), NOT the cash-only 100.
        total_contribution = sum(-cf.amount for cf in cash_flows)
        assert total_contribution == Decimal("10100"), f"expected capital baseline 10100, got {total_contribution}"

    def test_inkind_seed_does_not_explode_roi(self):
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="100", asset_id=100, cost_basis_override="100", cost_basis_currency="EUR")
        dep = _tx(id=2, type="DEPOSIT", dt="2025-01-01", amount="100", currency="EUR")
        states = _build_states([_ctxn(adj), _ctxn(dep)], [(date(2025, 1, 1), Decimal("100"), "EUR")], date(2025, 1, 1), date(2025, 1, 1))

        navs, cash_flows = DerivedViewsBuilder(states, "EUR").build_performance_inputs()
        roi_series = calculate_simple_roi_series(navs, cash_flows)

        # NAV = 10,000 market + 100 cash = 10,100; net_invested = 10,100 → ROI ≈ 0%.
        # With the old cash-only denominator (100) ROI would be ~10,000% (100.0 as a fraction).
        assert roi_series
        assert abs(roi_series[-1].roi) < Decimal("0.05"), f"ROI should be near 0, got {roi_series[-1].roi} (in-kind capital missing from denominator?)"

    def test_split_linked_adjustment_excluded(self):
        # A SPLIT-linked ADJUSTMENT (asset_event_id set) redistributes existing cost and
        # must NOT be treated as capital-in. Here a BUY seeds cost, then a split-linked
        # ADJUSTMENT adds quantity — the baseline must stay at the cash deposit only.
        dep = _tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="10000", currency="EUR")
        buy = _tx(id=2, type="BUY", dt="2025-01-01", amount="10000", currency="EUR", quantity="100", asset_id=100)
        split_adj = _tx(id=3, type="ADJUSTMENT", dt="2025-01-01", quantity="100", asset_id=100, cost_basis_override="50", cost_basis_currency="EUR")
        split_adj.asset_event_id = 999  # marks it split-linked

        builder = DailyStateBuilder(
            classified_txs=[_ctxn(dep), _ctxn(buy), _ctxn(split_adj)],
            in_transit_intervals=[],
            external_cash_flows=[(date(2025, 1, 1), Decimal("10000"), "EUR")],
            price_map={100: [(date(2025, 1, 1), Decimal("50"), "EUR")]},
            quote_base_map={},
            fx_rate_map={},
            asset_classifications={},
            asset_types={},
            asset_currencies={100: "EUR"},
            target_currency="EUR",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
            split_linked_tx_ids={3},
        )
        states = builder.build().daily_states
        _navs, cash_flows = DerivedViewsBuilder(states, "EUR").build_performance_inputs()

        total_contribution = sum(-cf.amount for cf in cash_flows)
        assert total_contribution == Decimal("10000"), f"split-linked adjustment must not inflate baseline; got {total_contribution}"

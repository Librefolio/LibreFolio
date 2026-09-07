"""
Portfolio Engine vNext — Integration tests.

Validates the core architectural invariants:
1. Inline WAC correctness (BUY/SELL/multi-broker)
2. Valuation hierarchy and transaction-reference propagation
3. 3-pool event-driven (K, R, W)
4. Position states emission (start + end snapshots)
5. Period accumulators (realized, income, fees)
6. Pre-frame / frame separation
"""

from datetime import date
from decimal import Decimal

import pytest

import backend.app.services.portfolio_engine as portfolio_engine_module
from backend.app.db.models import Transaction
from backend.app.schemas.common import Currency
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
    InTransitInterval,
    PortfolioCalculationEngine,
    SplitRecord,
    TransactionType,
    ValuationSource,
)
from backend.app.services.price_resolver import build_asset_price_series


def _tx(*, tx_id=1, broker_id=1, asset_id=1, tx_type=TransactionType.BUY, dt=date(2025, 1, 2), quantity=Decimal("0"), amount=None, currency="EUR", cbo=None, cbo_ccy=None):
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = broker_id
    tx.asset_id = asset_id
    tx.type = tx_type
    tx.date = dt
    tx.quantity = quantity
    tx.amount = amount
    tx.currency = currency
    tx.cost_basis_override = cbo
    tx.cost_basis_currency = cbo_ccy
    tx.related_transaction_id = None
    tx.updated_at = dt
    return tx


def _c(tx, share=Decimal("1")):
    return ClassifiedTransaction(tx=tx, classification="normal", share=share)


def _build_mark_series(txs, asset_currencies, price_map, quote_base_map, split_linked_tx_ids):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in txs:
        tx = ctxn.tx
        if tx.asset_id is not None:
            txs_by_asset.setdefault(tx.asset_id, []).append(tx)
    asset_ids = set(txs_by_asset) | set(price_map or {})
    mark_series = {}
    for aid in asset_ids:
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=split_linked_tx_ids or set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=(quote_base_map or {}).get(aid) or 1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _build(
    txs,
    asset_currencies=None,
    price_map=None,
    quote_base_map=None,
    fx_rate_map=None,
    split_history=None,
    split_linked_tx_ids=None,
    frame_start=None,
    date_from=date(2025, 1, 1),
    date_to=date(2025, 1, 10),
    mark_series=None,
):
    resolved_currencies = asset_currencies or {1: "EUR", 2: "EUR"}
    if mark_series is None:
        mark_series = _build_mark_series(
            txs,
            resolved_currencies,
            price_map or {},
            quote_base_map or {},
            split_linked_tx_ids or set(),
        )
    return DailyStateBuilder(
        classified_txs=txs,
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map=price_map or {},
        quote_base_map=quote_base_map or {},
        fx_rate_map=fx_rate_map or {},
        asset_classifications={},
        asset_types={1: "ETF", 2: "ETF"},
        asset_currencies=resolved_currencies,
        target_currency="EUR",
        date_from=date_from,
        date_to=date_to,
        frame_start=frame_start,
        split_history=split_history or {},
        split_linked_tx_ids=split_linked_tx_ids or set(),
        mark_series=mark_series,
    ).build()


# =============================================================================
# 1. INLINE WAC
# =============================================================================


class TestInlineWAC:
    """Verify WAC is computed correctly inline during daily loop."""

    def test_simple_buy(self):
        """Single BUY → WAC = unit cost."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("-1000")))]
        result = _build(txs)
        ps = result.position_states_end
        assert len(ps) == 1
        assert ps[0].wac == Decimal("100")
        assert ps[0].quantity == Decimal("10")

    def test_weighted_average_multiple_buys(self):
        """Two BUYs at different prices → weighted average."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, quantity=Decimal("5"), amount=Decimal("-750"), dt=date(2025, 1, 3))),
        ]
        result = _build(txs)
        ps = result.position_states_end
        assert len(ps) == 1
        expected_wac = Decimal("1750") / Decimal("15")
        assert abs(ps[0].wac - expected_wac) < Decimal("0.001")
        assert ps[0].quantity == Decimal("15")

    def test_sell_preserves_wac(self):
        """SELL does not change WAC."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.SELL, quantity=Decimal("-3"), amount=Decimal("450"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        ps = result.position_states_end
        assert len(ps) == 1
        assert ps[0].wac == Decimal("100")
        assert ps[0].quantity == Decimal("7")

    def test_independent_broker_pools(self):
        """Same asset on 2 brokers → independent WAC pools."""
        txs = [
            _c(_tx(tx_id=1, broker_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, broker_id=2, quantity=Decimal("5"), amount=Decimal("-600"), dt=date(2025, 1, 3))),
        ]
        result = _build(txs)
        ps = result.position_states_end
        assert len(ps) == 2
        b1 = next(p for p in ps if p.broker_id == 1)
        b2 = next(p for p in ps if p.broker_id == 2)
        assert b1.wac == Decimal("100")
        assert b2.wac == Decimal("120")


# =============================================================================
# 2. UNIFIED RESOLVER VALUATION (MARKET_PRICE / LAST_TRADE_PRICE / MISSING)
# =============================================================================


class TestResolverValuation:
    """The unified price resolver is the single valuation brain: a real quote (exact or carried)
    → MARKET_PRICE; an observed trade mark (BUY/SELL/priced ADJUSTMENT, same-day average, LOCF)
    → LAST_TRADE_PRICE; nothing on/before the date → MISSING.
    """

    def test_market_price_preferred(self):
        """A real asset-system quote wins over the same asset's trade observations."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2)))]
        prices = {1: [(date(2025, 1, 3), Decimal("120"), "EUR")]}
        result = _build(txs, price_map=prices)
        ps = result.position_states_end
        assert ps[0].valuation_source == "MARKET_PRICE"
        assert ps[0].market_value == Decimal("1200")  # 10 * 120 (quote carried to end)
        assert ps[0].valuation_reference_date == date(2025, 1, 3)
        assert ps[0].valuation_reference_unit_price == Decimal("120")
        assert ps[0].valuation_reference_currency == "EUR"

    def test_trade_price_when_no_market(self):
        """No asset-system quote → the last observed trade marks the position (LAST_TRADE_PRICE)."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2)))]
        result = _build(txs, quote_base_map={1: 100})
        ps = result.position_states_end
        assert ps[0].valuation_source == "LAST_TRADE_PRICE"
        assert ps[0].market_value == Decimal("1000")  # 10 * (1000/10)
        assert ps[0].valuation_reference_date == date(2025, 1, 2)
        assert ps[0].valuation_reference_unit_price == Decimal("100")
        assert ps[0].valuation_reference_currency == "EUR"

    def test_sell_observation_marks_position(self):
        """A SELL is a real observation the resolver ingests (the old last-buy tier ignored it)."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.SELL, quantity=Decimal("-4"), amount=Decimal("480"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        ps = result.position_states_end
        assert ps[0].valuation_source == "LAST_TRADE_PRICE"
        # residual 6 units marked at the last trade (SELL 480/4 = 120) → 6 * 120 = 720
        assert ps[0].market_value == Decimal("720")
        assert ps[0].valuation_reference_date == date(2025, 1, 5)

    def test_historical_trade_selects_latest_reference_not_after_valuation_date(self):
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("1"), amount=Decimal("-100"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, quantity=Decimal("1"), amount=Decimal("-120"), dt=date(2025, 1, 10))),
        ]
        mark_series = _build_mark_series(txs, {1: "EUR"}, {}, {}, set())
        builder = DailyStateBuilder(
            classified_txs=[],
            in_transit_intervals=[],
            external_cash_flows=[],
            price_map={},
            quote_base_map={},
            fx_rate_map={},
            asset_classifications={},
            asset_types={1: "ETF"},
            asset_currencies={1: "EUR"},
            target_currency="EUR",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 15),
            mark_series=mark_series,
        )

        before_second_buy = builder._market_value_for(1, Decimal("2"), date(2025, 1, 5))
        after_second_buy = builder._market_value_for(1, Decimal("2"), date(2025, 1, 10))

        assert before_second_buy.reference_date == date(2025, 1, 2)
        assert before_second_buy.effective_unit_price == Decimal("100")
        assert before_second_buy.market_value == Decimal("200")
        assert after_second_buy.reference_date == date(2025, 1, 10)
        assert after_second_buy.effective_unit_price == Decimal("120")
        assert after_second_buy.market_value == Decimal("240")

    def test_market_price_is_quote_base_aware_and_outranks_trade(self):
        txs = [_c(_tx(tx_id=1, quantity=Decimal("1000"), amount=Decimal("-100000"), dt=date(2025, 1, 2)))]
        mark_series = _build_mark_series(txs, {1: "EUR"}, {1: [(date(2025, 1, 5), Decimal("98"), "EUR")]}, {1: 100}, set())
        builder = DailyStateBuilder(
            classified_txs=[],
            in_transit_intervals=[],
            external_cash_flows=[],
            price_map={1: [(date(2025, 1, 5), Decimal("98"), "EUR")]},
            quote_base_map={1: 100},
            fx_rate_map={},
            asset_classifications={},
            asset_types={1: "BOND"},
            asset_currencies={1: "EUR"},
            target_currency="EUR",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 5),
            mark_series=mark_series,
        )

        valuation = builder._market_value_for(1, Decimal("1000"), date(2025, 1, 5))

        assert valuation.source == ValuationSource.MARKET_PRICE
        assert valuation.market_value == Decimal("980")
        assert valuation.effective_unit_price == Decimal("98")
        assert valuation.reference_unit_price == Decimal("98")
        assert valuation.effective_currency == valuation.reference_currency == "EUR"

    def test_missing_when_no_price_no_trade(self):
        """A position held via an unpriced quantity-only ADJUSTMENT (no quote, no priced trade)
        cannot be marked → MISSING. WAC is never used for valuation."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("0"), tx_type=TransactionType.ADJUSTMENT, dt=date(2025, 1, 2)))]
        result = _build(txs)
        ps = result.position_states_end
        assert ps[0].valuation_source == "MISSING"
        assert ps[0].market_value is None
        assert ps[0].valuation_reference_date is None
        assert ps[0].valuation_reference_unit_price is None
        assert ps[0].valuation_reference_currency is None
        assert ps[0].missing_fx_pair is None

    def test_wac_is_not_used_as_price(self):
        """WAC is NEVER the valuation source: with only an unpriced adjustment the position is
        MISSING even though a WAC exists (from a separate priced leg would still not apply)."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("0"), tx_type=TransactionType.ADJUSTMENT, dt=date(2025, 1, 2)))]
        result = _build(txs)
        ps = result.position_states_end
        assert ps[0].market_value is None
        assert ps[0].valuation_source == "MISSING"


class TestPricedAdjustmentValuation:
    """A priced opening ADJUSTMENT (per-unit ``cost_basis_override``) is a TRADE observation the
    resolver ingests, so a holding with no market quote is marked LAST_TRADE_PRICE at its seeded
    unit price (unrealized P&L 0 when valued at cost)."""

    def test_priced_adjustment_used_when_no_market(self):
        txs = [_c(_tx(tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        result = _build(txs, quote_base_map={1: 100})
        ps = result.position_states_end
        assert ps[0].market_value == Decimal("1000")  # 10 * 100
        assert ps[0].cost_basis == Decimal("1000")
        assert ps[0].unrealized_pnl == Decimal("0")  # valued at cost
        assert ps[0].valuation_source == "LAST_TRADE_PRICE"
        assert ps[0].valuation_reference_date == date(2025, 1, 2)
        assert ps[0].valuation_reference_unit_price == Decimal("100")
        assert ps[0].valuation_reference_currency == "EUR"
        assert result.daily_states[-1].market_value == Decimal("1000")
        assert result.daily_states[-1].open_cost_basis == Decimal("1000")
        assert result.daily_states[-1].unrealized_gain_loss == Decimal("0")
        assert result.daily_states[-1].nav_value == Decimal("1000")

    def test_market_price_preferred_over_priced_adjustment(self):
        txs = [_c(_tx(tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        prices = {1: [(date(2025, 1, 3), Decimal("130"), "EUR")]}
        result = _build(txs, price_map=prices)
        ps = result.position_states_end
        assert ps[0].valuation_source == "MARKET_PRICE"
        assert ps[0].market_value == Decimal("1300")  # 10 * 130 (not the seed cost)

    def test_priced_adjustment_isolated_position_by_broker(self):
        txs = [
            _c(_tx(tx_id=1, broker_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), cbo=Decimal("100"), cbo_ccy="EUR")),
            _c(_tx(tx_id=2, broker_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("5"), cbo=None, cbo_ccy=None)),
        ]
        result = _build(txs)
        by_broker = {position.broker_id: position for position in result.position_states_end}

        # The priced adjustment marks the asset (shared resolver series); broker 2's unpriced leg
        # holds units of the same asset and is marked at the same last observed trade.
        assert by_broker[1].valuation_source == "LAST_TRADE_PRICE"
        assert by_broker[1].market_value == Decimal("1000")
        assert by_broker[2].valuation_source == "LAST_TRADE_PRICE"
        assert by_broker[2].market_value == Decimal("500")

    def test_trade_fx_missing_preserves_source_and_metadata(self):
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), cbo=Decimal("100"), cbo_ccy="USD")),
            _c(_tx(tx_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), dt=date(2025, 1, 5))),
        ]
        result = _build(
            txs,
            asset_currencies={1: "USD"},
            split_linked_tx_ids={2},
            split_history={1: (SplitRecord(event_id=10, asset_id=1, date=date(2025, 1, 5), ratio=Decimal("2")),)},
        )
        position = result.position_states_end[0]

        assert position.valuation_source == "LAST_TRADE_PRICE"
        assert position.market_value is None
        assert position.valuation_reference_date == date(2025, 1, 2)
        assert position.valuation_reference_unit_price == Decimal("100")
        assert position.valuation_reference_currency == "USD"
        assert position.valuation_effective_unit_price == Decimal("50")
        assert position.valuation_effective_currency == "USD"
        assert position.valuation_split_adjusted is True
        assert position.missing_fx_pair == "USD/EUR"
        assert result.daily_states[-1].missing_fx_pairs == {"USD/EUR"}

    def test_zero_cost_priced_adjustment_stays_at_zero(self):
        txs = [_c(_tx(tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), cbo=Decimal("0"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        result = _build(txs)
        position = result.position_states_end[0]

        # A zero-cost override carries no price → the position is MISSING (no priced observation).
        assert position.valuation_source == "MISSING"
        assert position.market_value is None
        assert position.cost_basis == Decimal("0")


class TestSplitAdjustedResolver:
    @pytest.mark.parametrize(
        ("ratio", "split_quantity", "expected_quantity", "expected_price"),
        [
            (Decimal("2"), Decimal("10"), Decimal("20"), Decimal("50")),
            (Decimal("0.5"), Decimal("-5"), Decimal("5"), Decimal("200")),
        ],
    )
    def test_trade_mark_is_rebased_to_current_units(self, ratio, split_quantity, expected_quantity, expected_price):
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.BUY, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=split_quantity, amount=Decimal("0"), dt=date(2025, 1, 5))),
        ]
        result = _build(
            txs,
            split_linked_tx_ids={2},
            split_history={1: (SplitRecord(event_id=10, asset_id=1, date=date(2025, 1, 5), ratio=ratio),)},
        )
        position = result.position_states_end[0]

        assert position.quantity == expected_quantity
        assert position.valuation_source == ValuationSource.LAST_TRADE_PRICE
        assert position.valuation_effective_unit_price == expected_price
        assert position.valuation_reference_date == date(2025, 1, 2)
        assert position.valuation_reference_unit_price == Decimal("100")
        assert position.valuation_effective_currency == position.valuation_reference_currency == "EUR"
        assert position.valuation_split_adjusted is True
        assert position.market_value == Decimal("1000")

    @pytest.mark.parametrize(
        ("ratio", "split_quantity", "expected_quantity", "expected_price"),
        [
            (Decimal("2"), Decimal("10"), Decimal("20"), Decimal("50")),
            (Decimal("0.5"), Decimal("-5"), Decimal("5"), Decimal("200")),
        ],
    )
    def test_priced_adjustment_mark_uses_split_adjusted_units(self, ratio, split_quantity, expected_quantity, expected_price):
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=split_quantity, amount=Decimal("0"), dt=date(2025, 1, 5))),
        ]
        result = _build(
            txs,
            split_linked_tx_ids={2},
            split_history={1: (SplitRecord(event_id=10, asset_id=1, date=date(2025, 1, 5), ratio=ratio),)},
        )
        position = result.position_states_end[0]

        assert position.quantity == expected_quantity
        assert position.valuation_source == ValuationSource.LAST_TRADE_PRICE
        assert position.valuation_effective_unit_price == expected_price
        assert position.valuation_reference_unit_price == Decimal("100")
        assert position.valuation_split_adjusted is True
        assert position.market_value == Decimal("1000")
        assert position.cost_basis == Decimal("1000")
        assert position.unrealized_pnl == Decimal("0")


# =============================================================================
# 3. THREE-POOL (K, R, W) EVENT-DRIVEN
# =============================================================================


class TestThreePool:
    """Verify 3-pool cash decomposition."""

    def test_deposit_goes_to_capital(self):
        """DEPOSIT → K increases."""
        txs = [_c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2)))]
        result = _build(txs)
        last = result.daily_states[-1]
        # After deposit: cash=1000, K=1000, R=0
        assert last.cash_from_contributed_capital == Decimal("1000")
        assert last.cash_from_generated_returns == Decimal("0")

    def test_dividend_goes_to_returns(self):
        """DIVIDEND → R increases."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("50"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # K=1000, R=50, cash=1050
        assert last.cash_from_contributed_capital == Decimal("1000")
        assert last.cash_from_generated_returns == Decimal("50")

    def test_buy_consumes_returns_first(self):
        """BUY → consumes R first, then K."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("200"), dt=date(2025, 1, 3))),
            _c(_tx(tx_id=3, tx_type=TransactionType.BUY, asset_id=1, quantity=Decimal("5"), amount=Decimal("-500"), dt=date(2025, 1, 4))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # After deposit: K=1000, R=0
        # After dividend: K=1000, R=200
        # After BUY 500: from_R=min(500,200)=200, R=0; K -= (500-200) = K=700
        # cash = 1000 + 200 - 500 = 700, K=700, R=0
        assert last.cash_value == Decimal("700")
        assert last.cash_from_contributed_capital == Decimal("700")
        assert last.cash_from_generated_returns == Decimal("0")

    def test_full_sell_splits_capital_and_gain(self):
        """Full SELL splits proceeds between K (cost_basis) and R (gain).

        Regression test: previously, full sell (qty→0) caused pool_q=0 at read time,
        making cost_basis=0 and putting ALL proceeds into R.
        """
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.BUY, asset_id=1, quantity=Decimal("1"), amount=Decimal("-1000"), dt=date(2025, 1, 3))),
            _c(_tx(tx_id=3, tx_type=TransactionType.SELL, asset_id=1, quantity=Decimal("-1"), amount=Decimal("1005"), dt=date(2025, 1, 8))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # Deposit 1000 → K=1000, R=0
        # BUY 1000: from_R=min(1000,0)=0, K -= 1000 → K=0, R=0
        # SELL proceeds=1005, cost_basis=1000 (WAC=1000), gain=5
        #   K += cost_basis(1000) → K=1000
        #   R += gain(5) → R=5
        # cash = 1000 - 1000 + 1005 = 1005
        assert last.cash_value == Decimal("1005")
        assert last.cash_from_contributed_capital == Decimal("1000")
        assert last.cash_from_generated_returns == Decimal("5")

    def test_withdrawal_moves_returns_to_w_then_deposit_restores(self):
        """WITHDRAWAL from R → W. Re-DEPOSIT restores from W to R first."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("200"), dt=date(2025, 1, 3))),
            # Withdraw 300: from_K=min(300,1000)=300, K=700, no from_R
            _c(_tx(tx_id=3, tx_type=TransactionType.WITHDRAWAL, asset_id=None, quantity=Decimal("0"), amount=Decimal("-300"), dt=date(2025, 1, 4))),
            # Withdraw 900: from_K=min(900,700)=700, K=0; from_R=min(200,200)=200, R=0, W=200
            _c(_tx(tx_id=4, tx_type=TransactionType.WITHDRAWAL, asset_id=None, quantity=Decimal("0"), amount=Decimal("-900"), dt=date(2025, 1, 5))),
            # Re-deposit 150: restore=min(150, W=200)=150 → R+=150, W=50; K += 0
            _c(_tx(tx_id=5, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("150"), dt=date(2025, 1, 8))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # cash = 1000 + 200 - 300 - 900 + 150 = 150
        assert last.cash_value == Decimal("150")
        # K=0, R=150 (restored from W)
        assert last.cash_from_contributed_capital == Decimal("0")
        assert last.cash_from_generated_returns == Decimal("150")


class TestInKindAdjustmentCapital:
    """Priced in-kind ADJUSTMENT (opening / transfer / succession) is a capital
    contribution or distribution, NOT profit.

    Such a transaction injects (qty>0) or removes (qty<0) real book value with no
    cash counterpart, so its cost must move the capital baseline
    (``cumulative_external_cash_flow``). Otherwise the book value leaks into total
    P&L and, at portfolio level, into the "Other / reconciliation residual".
    """

    def test_priced_adjustment_in_is_capital_not_pnl(self):
        """ADJUSTMENT-in with cost_basis_override raises the capital baseline by its
        book value; total P&L then reflects only unrealized (market − cost)."""
        txs = [_c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        prices = {1: [(date(2025, 1, 2), Decimal("120"), "EUR")]}
        result = _build(txs, price_map=prices)
        last = result.daily_states[-1]
        # book (cost) = 10 * 100 = 1000; market = 10 * 120 = 1200; unrealized = 200
        assert last.nav_value == Decimal("1200")
        assert last.open_cost_basis == Decimal("1000")
        assert last.unrealized_gain_loss == Decimal("200")
        # capital baseline absorbs the in-kind book value → total P&L == unrealized only
        assert last.cumulative_external_cash_flow == Decimal("1000")
        assert last.total_pnl == Decimal("200")

    def test_priced_adjustment_at_cost_has_zero_pnl(self):
        """When market == injected cost, an opening ADJUSTMENT yields zero P&L (pure
        capital, no reconciliation residual)."""
        txs = [_c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        prices = {1: [(date(2025, 1, 2), Decimal("100"), "EUR")]}
        result = _build(txs, price_map=prices)
        last = result.daily_states[-1]
        assert last.cumulative_external_cash_flow == Decimal("1000")
        assert last.total_pnl == Decimal("0")

    def test_adjustment_out_is_symmetric_capital_distribution(self):
        """ADJUSTMENT-out (in-kind removal, no cash) removes book at WAC from the
        capital baseline — mirror of the contribution — with no phantom realized P&L.
        A full in→out cycle returns the capital baseline to zero."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("-10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 6))),
        ]
        prices = {1: [(date(2025, 1, 2), Decimal("120"), "EUR")]}
        result = _build(txs, price_map=prices)
        # Mid-state (after in, before out): capital 1000, unrealized 200
        mid = next(s for s in result.daily_states if s.date == date(2025, 1, 4))
        assert mid.cumulative_external_cash_flow == Decimal("1000")
        assert mid.total_pnl == Decimal("200")
        # Final (after out): position closed, capital baseline back to 0, no residual
        last = result.daily_states[-1]
        assert last.market_value == Decimal("0")
        assert last.cumulative_external_cash_flow == Decimal("0")
        assert last.total_pnl == Decimal("0")

    def test_preframe_priced_adjustment_carries_capital_into_frame(self):
        """An opening ADJUSTMENT before frame_start seeds the capital baseline so a
        bounded period starts with the right capital (not a phantom P&L)."""
        txs = [_c(_tx(tx_id=1, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("10"), amount=Decimal("0"), cbo=Decimal("100"), cbo_ccy="EUR", dt=date(2025, 1, 2)))]
        prices = {1: [(date(2025, 1, 2), Decimal("120"), "EUR"), (date(2025, 1, 5), Decimal("120"), "EUR")]}
        result = _build(txs, price_map=prices, frame_start=date(2025, 1, 5))
        last = result.daily_states[-1]
        assert last.cumulative_external_cash_flow == Decimal("1000")
        assert last.total_pnl == Decimal("200")

    def test_unpriced_quantity_adjustment_is_not_capital(self):
        """A quantity-only ADJUSTMENT (no cost_basis_override) is NOT a capital event
        and must not touch the capital baseline (backward-compatible gating)."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.BUY, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("2"), amount=Decimal("0"), dt=date(2025, 1, 5))),
        ]
        prices = {1: [(date(2025, 1, 2), Decimal("100"), "EUR")]}
        result = _build(txs, price_map=prices)
        last = result.daily_states[-1]
        # BUY pays cash (not an external cash flow); the unpriced adjustment adds no
        # capital → capital baseline stays 0.
        assert last.cumulative_external_cash_flow == Decimal("0")


# =============================================================================
# 4. POSITION STATE EMISSION
# =============================================================================


class TestPositionStates:
    """Verify engine emits position snapshots at start and end of frame."""

    def test_end_positions_emitted(self):
        """Position states are emitted for positions with qty > 0 at end."""
        txs = [_c(_tx(quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2)))]
        result = _build(txs)
        assert len(result.position_states_end) == 1
        ps = result.position_states_end[0]
        assert ps.asset_id == 1
        assert ps.broker_id == 1
        assert ps.quantity == Decimal("10")

    def test_closed_position_not_in_end(self):
        """Fully sold position does not appear in end states."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.SELL, quantity=Decimal("-10"), amount=Decimal("1500"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        assert len(result.position_states_end) == 0

    def test_start_positions_from_preframe(self):
        """Positions at frame_start reflect pre-frame accumulation."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, quantity=Decimal("5"), amount=Decimal("-600"), dt=date(2025, 1, 8))),
        ]
        # frame_start=Jan 5 → pre-frame includes tx1, frame includes tx2
        result = _build(txs, frame_start=date(2025, 1, 5))
        assert len(result.position_states_start) == 1
        assert result.position_states_start[0].quantity == Decimal("10")
        # End includes both
        assert result.position_states_end[0].quantity == Decimal("15")


# =============================================================================
# 5. PERIOD ACCUMULATORS
# =============================================================================


class TestPeriodAccumulators:
    """Verify realized, income, fees accumulation during frame."""

    def test_sell_realized(self):
        """SELL in frame → per_realized accumulated."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.SELL, quantity=Decimal("-5"), amount=Decimal("750"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        # Realized = proceeds(750) - cost_basis(5 * WAC=100 = 500) = 250
        key = (1, 1)
        assert key in result.per_realized
        assert result.per_realized[key] == Decimal("250")

    def test_income_attributed(self):
        """DIVIDEND with asset_id → per_income."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("50"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        assert result.per_income.get((1, 1)) == Decimal("50")

    def test_unallocated_fees(self):
        """FEE without asset_id → unalloc_fees."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, tx_type=TransactionType.FEE, asset_id=None, quantity=Decimal("0"), amount=Decimal("-10"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        assert result.unalloc_fees.get(1) == Decimal("10")


# =============================================================================
# 6. PRE-FRAME / FRAME SEPARATION
# =============================================================================


class TestPreframeFrame:
    """Verify pre-frame processes txs without market eval."""

    def test_preframe_no_states_emitted(self):
        """Transactions before frame_start don't produce daily states."""
        txs = [
            _c(_tx(tx_id=1, quantity=Decimal("10"), amount=Decimal("-1000"), dt=date(2025, 1, 2))),
        ]
        result = _build(txs, frame_start=date(2025, 1, 5))
        # States only from frame_start to date_to
        assert all(s.date >= date(2025, 1, 5) for s in result.daily_states)
        assert result.daily_states[0].date == date(2025, 1, 5)

    def test_preframe_accumulates_cash(self):
        """Pre-frame deposit is reflected in frame's cash value."""
        txs = [
            _c(_tx(tx_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
        ]
        result = _build(txs, frame_start=date(2025, 1, 5))
        # First frame day should show cash=1000 from pre-frame deposit
        assert result.daily_states[0].cash_value == Decimal("1000")


# =============================================================================
# 7. PER-BROKER POOLS
# =============================================================================


class TestPerBrokerPools:
    """Verify 3-pool is per-broker: K[bid], R[bid], W global."""

    def test_buy_only_consumes_own_broker_returns(self):
        """BUY on broker 1 does NOT consume R from broker 2."""
        txs = [
            # Broker 1: deposit 1000
            _c(_tx(tx_id=1, broker_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("1000"), dt=date(2025, 1, 2))),
            # Broker 2: deposit 500 + dividend 200 (R[2]=200)
            _c(_tx(tx_id=2, broker_id=2, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("500"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=3, broker_id=2, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("200"), dt=date(2025, 1, 3))),
            # BUY on broker 1 for 800: should consume from R[1]=0, then K[1]
            _c(_tx(tx_id=4, broker_id=1, tx_type=TransactionType.BUY, asset_id=1, quantity=Decimal("8"), amount=Decimal("-800"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # K[1]=1000, R[1]=0 after deposit
        # BUY 800 on broker 1: from_R[1]=min(800,0)=0 → K[1] -= 800 → K[1]=200
        # Broker 2 untouched: K[2]=500, R[2]=200
        # Total: K_tot=700, R_tot=200, cash=1000+500+200-800=900
        assert last.cash_value == Decimal("900")
        assert last.cash_from_contributed_capital == Decimal("700")
        assert last.cash_from_generated_returns == Decimal("200")

    def test_withdrawal_from_broker_with_returns_goes_to_w(self):
        """WITHDRAWAL from broker that has R → from_K first, then R → W."""
        txs = [
            _c(_tx(tx_id=1, broker_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("100"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, broker_id=1, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("50"), dt=date(2025, 1, 3))),
            # Withdraw 120: from_K[1]=min(120,100)=100 → K[1]=0; from_R[1]=min(20,50)=20 → R[1]=30, W=20
            _c(_tx(tx_id=3, broker_id=1, tx_type=TransactionType.WITHDRAWAL, asset_id=None, quantity=Decimal("0"), amount=Decimal("-120"), dt=date(2025, 1, 5))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # cash = 100 + 50 - 120 = 30
        # K[1]=0, R[1]=30
        assert last.cash_value == Decimal("30")
        assert last.cash_from_contributed_capital == Decimal("0")
        assert last.cash_from_generated_returns == Decimal("30")

    def test_redeposit_on_different_broker_restores_from_w(self):
        """W is global: re-deposit on broker 2 restores from W (earned on broker 1)."""
        txs = [
            # Broker 1: deposit + dividend + full withdrawal (R goes to W)
            _c(_tx(tx_id=1, broker_id=1, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("100"), dt=date(2025, 1, 2))),
            _c(_tx(tx_id=2, broker_id=1, tx_type=TransactionType.DIVIDEND, asset_id=1, quantity=Decimal("0"), amount=Decimal("50"), dt=date(2025, 1, 3))),
            # Withdraw all 150: K[1]=100→0, R[1]=50→0, W=50
            _c(_tx(tx_id=3, broker_id=1, tx_type=TransactionType.WITHDRAWAL, asset_id=None, quantity=Decimal("0"), amount=Decimal("-150"), dt=date(2025, 1, 4))),
            # Re-deposit 30 on broker 2: restore=min(30, W=50)=30 → R[2]+=30, W=20
            _c(_tx(tx_id=4, broker_id=2, tx_type=TransactionType.DEPOSIT, asset_id=None, quantity=Decimal("0"), amount=Decimal("30"), dt=date(2025, 1, 8))),
        ]
        result = _build(txs)
        last = result.daily_states[-1]
        # cash = 100 + 50 - 150 + 30 = 30
        # K[1]=0, R[1]=0, K[2]=0, R[2]=30
        assert last.cash_value == Decimal("30")
        assert last.cash_from_contributed_capital == Decimal("0")
        assert last.cash_from_generated_returns == Decimal("30")


class TestPreloadFxRates:
    """Target FX preload helper directly."""

    @pytest.mark.asyncio
    async def test_preload_fx_rates_collects_all_main_sources(self, monkeypatch):
        txs = [
            _c(
                _tx(
                    tx_id=1,
                    asset_id=1,
                    tx_type=TransactionType.BUY,
                    dt=date(2025, 1, 2),
                    quantity=Decimal("2"),
                    amount=Decimal("-100"),
                    currency="USD",
                )
            ),
        ]

        cash_dep = _tx(
            tx_id=10,
            broker_id=1,
            asset_id=None,
            tx_type=TransactionType.CASH_TRANSFER,
            dt=date(2025, 1, 1),
            quantity=Decimal("0"),
            amount=Decimal("-300"),
            currency="CAD",
        )
        cash_arr = _tx(
            tx_id=11,
            broker_id=2,
            asset_id=None,
            tx_type=TransactionType.CASH_TRANSFER,
            dt=date(2025, 1, 4),
            quantity=Decimal("0"),
            amount=Decimal("300"),
            currency="CAD",
        )
        asset_dep = _tx(
            tx_id=12,
            broker_id=1,
            asset_id=1,
            tx_type=TransactionType.TRANSFER,
            dt=date(2025, 1, 1),
            quantity=Decimal("-1"),
            amount=None,
            currency="JPY",
        )
        asset_arr = _tx(
            tx_id=13,
            broker_id=2,
            asset_id=1,
            tx_type=TransactionType.TRANSFER,
            dt=date(2025, 1, 4),
            quantity=Decimal("1"),
            amount=None,
            currency="JPY",
        )

        intervals = [
            InTransitInterval(
                start_date=date(2025, 1, 2),
                end_date=date(2025, 1, 3),
                tx_type="cash",
                departure_leg=cash_dep,
                arrival_leg=cash_arr,
                share=Decimal("1"),
            ),
            InTransitInterval(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 2),
                tx_type="asset",
                departure_leg=asset_dep,
                arrival_leg=asset_arr,
                share=Decimal("1"),
                asset_id=1,
                cost_basis_amount=Decimal("80"),
                cost_basis_currency="AUD",
            ),
        ]

        captured: dict[str, object] = {}

        async def fake_convert_bulk(db, bulk_items, raise_on_error=False):
            captured["db"] = db
            captured["bulk_items"] = bulk_items
            captured["raise_on_error"] = raise_on_error
            results = [(Currency(code="EUR", amount=Decimal("1")), item[2], False) for item in bulk_items]
            return results, []

        db = object()
        monkeypatch.setattr(portfolio_engine_module, "convert_bulk", fake_convert_bulk)

        fx_map = await PortfolioCalculationEngine(db)._preload_fx_rates(
            classified_txs=txs,
            in_transit_intervals=intervals,
            external_cash_flows=[(date(2025, 1, 3), Decimal("50"), "GBP")],
            price_map={
                1: [(date(2025, 1, 1), Decimal("10"), "USD")],
                2: [(date(2025, 1, 1), Decimal("20"), "CHF")],
            },
            asset_currencies={1: "JPY", 2: "EUR"},
            target_currency="EUR",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
        )

        expected_keys = {
            ("USD", "EUR", date(2025, 1, 1)),
            ("USD", "EUR", date(2025, 1, 2)),
            ("USD", "EUR", date(2025, 1, 3)),
            ("CHF", "EUR", date(2025, 1, 1)),
            ("CHF", "EUR", date(2025, 1, 2)),
            ("CHF", "EUR", date(2025, 1, 3)),
            ("JPY", "EUR", date(2025, 1, 1)),
            ("JPY", "EUR", date(2025, 1, 2)),
            ("JPY", "EUR", date(2025, 1, 3)),
            ("GBP", "EUR", date(2025, 1, 3)),
            ("CAD", "EUR", date(2025, 1, 2)),
            ("CAD", "EUR", date(2025, 1, 3)),
            ("AUD", "EUR", date(2025, 1, 1)),
            ("AUD", "EUR", date(2025, 1, 2)),
        }

        assert captured["db"] is db
        assert captured["raise_on_error"] is False
        assert {(item[0].code, item[1], item[2]) for item in captured["bulk_items"]} == expected_keys
        assert set(fx_map.keys()) == expected_keys
        assert set(fx_map.values()) == {Decimal("1")}

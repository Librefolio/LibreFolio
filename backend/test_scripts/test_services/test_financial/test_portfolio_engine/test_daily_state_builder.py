"""Unit tests for DailyStateBuilder.

Pure tests — no DB, no async, no fixtures. Uses mock Transaction objects.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import ClassificationResult, ClassifiedTransaction, InTransitInterval, SplitRecord, UnrealizedSplit, ValuationSource
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

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


def _mark_series_from(classified_txs, price_map, asset_currencies, quote_base_map, split_linked_tx_ids):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.asset_id is not None:
            txs_by_asset.setdefault(tx.asset_id, []).append(tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
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


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg.

    Mirrors PortfolioCalculationEngine by building the per-asset resolver ``mark_series`` from the
    given ``price_map`` + trades, and the ``average_costs`` and ``native_cash`` from the transactions
    with the given ``fx_rate_map``, unless the test supplies its own.
    """
    defaults = {
        "classified_txs": [],
        "in_transit_intervals": [],
        "external_cash_flows": [],
        "price_map": {},
        "quote_base_map": {},
        "asset_currencies": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "target_currency": "EUR",
        "date_from": date(2025, 1, 1),
        "date_to": date(2025, 1, 3),
    }
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
            defaults.get("split_linked_tx_ids"),
        )
    if "average_costs" not in defaults:
        defaults["average_costs"] = engine_average_costs(
            defaults["classified_txs"],
            asset_currencies=defaults["asset_currencies"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            split_linked_tx_ids=defaults.get("split_linked_tx_ids"),
            date_to=defaults["date_to"],
        )
    if "native_cash" not in defaults:
        defaults["native_cash"] = engine_native_cash(
            defaults["classified_txs"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            date_to=defaults["date_to"],
        )
    return DailyStateBuilder(**defaults)


# =============================================================================
# TESTS
# =============================================================================


class TestCashLedger:
    """Cash ledger tracks cumulative signed amounts."""

    def test_single_deposit(self):
        """DEPOSIT 1000 EUR → cash_value=1000 from deposit date onwards."""
        tx = _tx(dt="2025-01-01", type="DEPOSIT", amount="1000")
        builder = _builder(
            classified_txs=[_ctxn(tx)],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert len(states) == 2
        assert states[0].cash_value == Decimal("1000")
        assert states[1].cash_value == Decimal("1000")

    def test_deposit_then_buy(self):
        """DEPOSIT +1000 then BUY -400 → cash=600."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="BUY", amount="-400", quantity="10", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("1000")  # day 1: deposit
        assert states[1].cash_value == Decimal("600")  # day 2: after buy
        assert states[2].cash_value == Decimal("600")  # day 3: unchanged

    def test_all_tx_types_contribute(self):
        """Every tx type with amount≠0 contributes to cash."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="FEE", amount="-10")),
            _ctxn(_tx(id=3, dt="2025-01-01", type="DIVIDEND", amount="50")),
            _ctxn(_tx(id=4, dt="2025-01-01", type="TAX", amount="-20")),
        ]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("1020")  # 1000 - 10 + 50 - 20

    def test_share_percentage(self):
        """share_percentage scales cash contributions."""
        tx = _tx(dt="2025-01-01", type="DEPOSIT", amount="1000")
        builder = _builder(
            classified_txs=[_ctxn(tx, share="0.5")],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("500")


class TestQuantityLedger:
    """Quantity tracks all tx types with quantity != 0 (including TRANSFER, ADJUSTMENT)."""

    def test_buy_and_sell(self):
        """BUY +10, SELL -3 → net qty 7, market_value = 7 * price."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=2, dt="2025-01-02", type="SELL", amount="300", quantity="-3", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("1000")  # 10 * 100
        assert states[1].market_value == Decimal("700")  # 7 * 100

    def test_transfer_changes_quantity(self):
        """TRANSFER with quantity ≠ 0 affects market value (fixes known bug)."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100)),
            _ctxn(_tx(id=2, dt="2025-01-02", type="TRANSFER", quantity="-5", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("50"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("500")  # 10 * 50
        assert states[1].market_value == Decimal("250")  # 5 * 50


class TestNAVFormula:
    """NAV = market_value + cash_value + in_transit."""

    def test_nav_basic(self):
        """nav_value = broker_nav_value + in_transit_market_value."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("50"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.cash_value == Decimal("500")  # 1000 - 500
        assert s.market_value == Decimal("500")  # 10 * 50
        assert s.broker_nav_value == Decimal("1000")
        assert s.in_transit_market_value == Decimal("0")
        assert s.nav_value == Decimal("1000")


class TestBookValueFormula:
    """book_value = open_cost_basis + cash + in_transit_book_value."""

    def test_book_value_with_wac(self):
        """book_value computed from WAC series."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100, broker_id=10)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("60"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.open_cost_basis == Decimal("500")  # WAC 50 * qty 10
        assert s.cash_value == Decimal("500")
        assert s.book_value == Decimal("1000")  # 500 + 500
        assert s.unrealized_gain_loss == s.nav_value - s.book_value
        assert s.unrealized_gain_loss == Decimal("100")  # NAV 1100 - book 1000

    def test_book_asset_like_drops_after_maturity_sell(self):
        """A maturity encoded as SELL closes the WAC pool, so growth cost basis drops."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-95000", quantity="95000", asset_id=100)),
            _ctxn(_tx(id=2, dt="2025-01-02", type="SELL", amount="95000", quantity="-95000", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: 100},
            asset_types={100: "Bond"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
        )
        states = builder.build().daily_states

        assert states[0].book_asset_like == Decimal("95000")
        assert states[1].book_asset_like == Decimal("0")
        assert states[2].book_asset_like == Decimal("0")


class TestSplitRescale:
    """SPLIT-linked ADJUSTMENT rescales the WAC pool instead of add/reduce (Fase 0 fix).

    Regression coverage for the WAC split-doubling bug (fifo-engine reports 1-6):
    a SPLIT must never add or remove economic cost, only redistribute the existing
    total cost (open_cost_basis) over a new quantity. split_linked_tx_ids is passed
    directly to DailyStateBuilder — resolving it from Transaction.asset_event_id is
    PortfolioCalculationEngine.run()'s responsibility, tested separately.
    """

    def test_forward_split_in_frame_preserves_cost_basis(self):
        """BUY 15@100 (cost 1500) + SPLIT +15 (frame) → 30 units, cost basis still 1500."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-1500", quantity="15", asset_id=100, broker_id=10)),
            _ctxn(_tx(id=2, dt="2025-01-10", type="ADJUSTMENT", amount="0", quantity="15", asset_id=100, broker_id=10)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 10),
            split_linked_tx_ids={2},
        )
        states = builder.build().daily_states

        assert states[0].open_cost_basis == Decimal("1500")  # before split: 15@100
        s_after = states[-1]
        assert s_after.open_cost_basis == Decimal("1500")  # after split: 30@50, cost unchanged
        assert s_after.market_value == Decimal("3000")  # 30 * 100

    def test_reverse_split_in_frame_preserves_cost_basis(self):
        """BUY 30@50 (cost 1500) + SPLIT -15 (frame) → 15 units, cost basis still 1500."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-1500", quantity="30", asset_id=100, broker_id=10)),
            _ctxn(_tx(id=2, dt="2025-01-10", type="ADJUSTMENT", amount="0", quantity="-15", asset_id=100, broker_id=10)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 10),
            split_linked_tx_ids={2},
        )
        states = builder.build().daily_states

        s_after = states[-1]
        # Without the fix, a reduction would keep WAC at 50 and drop cost to 750.
        assert s_after.open_cost_basis == Decimal("1500")
        assert s_after.market_value == Decimal("1500")  # 15 * 100

    def test_forward_split_before_date_from_preserves_cost_basis(self):
        """Same as forward-split test but the split falls before date_from.

        J1: replayed by the same loop, with the same rules, as any emitted day (before
        J1 it ran in the pre-frame, a separate copy of the accounting); only the states
        from date_from are emitted.
        """
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-1500", quantity="15", asset_id=100, broker_id=10)),
            _ctxn(_tx(id=2, dt="2025-01-05", type="ADJUSTMENT", amount="0", quantity="15", asset_id=100, broker_id=10)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 6),
            date_to=date(2025, 1, 6),
            split_linked_tx_ids={2},
        )
        states = builder.build().daily_states

        assert len(states) == 1  # only date_from..date_to emitted
        s = states[0]
        assert s.open_cost_basis == Decimal("1500")  # carried over from the rescale before date_from
        assert s.market_value == Decimal("3000")  # 30 * 100


class TestMarketValueWithQuoteBase:
    """quote_base_quantity divides raw price (e.g. BTP/bond at 102 per 100 nominal)."""

    def test_quote_base(self):
        """qty=200, price=102, quote_base=100 → (200/100)*102 = 204."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-200", quantity="200", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("102"), "EUR")]},
            quote_base_map={100: 100},
            asset_types={100: "Bond"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("204")


class TestMissingPrices:
    """Assets without prices are flagged, not included in market_value."""

    def test_missing_price(self):
        """No priced observation (unpriced quantity-only ADJUSTMENT) → missing_price_asset_ids
        contains asset_id, market_value=0."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="ADJUSTMENT", amount="0", quantity="5", asset_id=200)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={},  # no prices, and the adjustment carries no price → MISSING
            asset_types={200: "ETF"},
            asset_classifications={200: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("0")
        assert 200 in states[0].missing_price_asset_ids
        assert states[0].nav_complete is False


class TestStalePriceDetection:
    """Prices older than threshold days are flagged as stale."""

    def test_stale_price(self):
        """A carried asset-system quote from 10 days ago (> 7 day threshold) → stale."""
        txs = [
            _ctxn(_tx(id=1, dt="2024-12-22", type="BUY", amount="-100", quantity="5", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2024, 12, 22), Decimal("20"), "EUR")]},  # 10 days before Jan 1
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert 100 in states[0].stale_price_asset_ids
        assert states[0].market_value == Decimal("100")  # still valued, just flagged


class TestInTransitCash:
    """Cash in-transit during transit window."""

    def test_cash_in_transit(self):
        """Cash transfer between brokers with 2-day gap → in-transit on middle day."""
        dep_tx = _tx(id=10, broker_id=10, dt="2025-01-01", type="CASH_TRANSFER", amount="-3000")
        arr_tx = _tx(id=11, broker_id=20, dt="2025-01-04", type="CASH_TRANSFER", amount="3000")

        interval = InTransitInterval(
            start_date=date(2025, 1, 2),
            end_date=date(2025, 1, 3),
            tx_type="cash",
            departure_leg=dep_tx,
            arrival_leg=arr_tx,
            share=Decimal("1"),
        )

        builder = _builder(
            classified_txs=[
                _ctxn(dep_tx, classification="linked_internal"),
                _ctxn(arr_tx, classification="linked_internal"),
            ],
            in_transit_intervals=[interval],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )
        states = builder.build().daily_states

        # Day 1: cash -3000, no in-transit yet (departure date itself)
        assert states[0].in_transit_cash_value == Decimal("0")
        # Day 2: in transit
        assert states[1].in_transit_cash_value == Decimal("3000")
        # Day 3: still in transit
        assert states[2].in_transit_cash_value == Decimal("3000")
        # Day 4: arrival — cash +3000, no more in transit
        assert states[3].in_transit_cash_value == Decimal("0")


class TestAllocationLiquidity:
    """Cash treated as Liquidity in type/sector allocation, NOT in geography."""

    def test_cash_as_liquidity(self):
        """Pure cash portfolio → type=Liquidity, sector=Liquidity, geography=empty."""
        txs = [_ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="5000"))]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.by_type.get("Liquidity") == Decimal("5000")
        assert s.by_sector.get("Liquidity") == Decimal("5000")
        assert len(s.by_geography) == 0  # cash is NOT a country


class TestExternalCashFlow:
    """External cash flows tracked correctly for performance calculations."""

    def test_ecf_deposit(self):
        """DEPOSIT external cash flow captured in DailyPortfolioState."""
        txs = [_ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000"))]
        builder = _builder(
            classified_txs=txs,
            external_cash_flows=[(date(2025, 1, 1), 10, Decimal("1000"), "EUR")],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].external_cash_flow == Decimal("1000")
        assert states[1].external_cash_flow == Decimal("0")


class TestFXConversion:
    """Amounts in non-target currencies are converted using fx_rate_map."""

    def test_usd_cash_converted(self):
        """USD deposit with FX rate → cash in EUR."""
        txs = [
            _ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000", currency="USD")),
        ]
        builder = _builder(
            classified_txs=txs,
            fx_rate_map={("USD", "EUR", date(2025, 1, 1)): Decimal("0.9")},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("900")  # 1000 * 0.9

    def test_missing_fx_flagged(self):
        """USD amount without FX rate → cash=0, missing_fx_pairs populated."""
        txs = [
            _ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000", currency="USD")),
        ]
        builder = _builder(
            classified_txs=txs,
            fx_rate_map={},  # no rate
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        # USD couldn't be converted → cash=0
        assert states[0].cash_value == Decimal("0")


class TestPrivateValuationHelpers:
    """Target small private helper branches directly."""

    def test_market_value_for_foreign_market_price_uses_fx_rate(self):
        builder = _builder(
            price_map={100: [(date(2025, 1, 1), Decimal("20"), "USD")]},
            fx_rate_map={("USD", "EUR", date(2025, 1, 2)): Decimal("0.9")},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(
            asset_id=100,
            qty=Decimal("5"),
            dt=date(2025, 1, 2),
        )

        assert valuation.market_value == Decimal("90")  # 5 * 20 USD * 0.9 EUR/USD
        assert valuation.source == ValuationSource.MARKET_PRICE
        assert valuation.reference_date == date(2025, 1, 1)
        assert valuation.effective_unit_price == Decimal("20")
        assert valuation.effective_currency == "USD"
        assert valuation.reference_unit_price == Decimal("20")
        assert valuation.reference_currency == "USD"
        assert valuation.stale is False
        assert valuation.missing_fx_pair is None

    def test_market_value_for_trade_mark_uses_fx_rate(self):
        # A foreign BUY (USD) with no asset-system quote → the resolver marks it LAST_TRADE_PRICE
        # and the engine converts at the valuation date's FX rate.
        buy = _tx(id=1, dt="2025-01-01", type="BUY", amount="60", currency="USD", quantity="2", asset_id=100)
        series = build_asset_price_series(
            price_rows=[],
            transactions=[buy],
            split_linked_tx_ids=set(),
            asset_currency="USD",
            quote_base_quantity=1,
        )
        builder = _builder(
            fx_rate_map={("USD", "EUR", date(2025, 1, 2)): Decimal("0.8")},
            asset_currencies={100: "USD"},
            mark_series={100: series},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(
            asset_id=100,
            qty=Decimal("2"),
            dt=date(2025, 1, 2),
        )

        assert valuation.market_value == Decimal("48")  # 2 * 30 USD * 0.8 EUR/USD
        assert valuation.source == ValuationSource.LAST_TRADE_PRICE
        assert valuation.reference_date == date(2025, 1, 1)
        assert valuation.effective_unit_price == Decimal("30")
        assert valuation.effective_currency == "USD"
        assert valuation.reference_unit_price == Decimal("30")
        assert valuation.reference_currency == "USD"
        assert valuation.stale is False
        assert valuation.missing_fx_pair is None


class TestCostConversionThroughAverageCosts:
    """The conversions the removed ``_buy_unit_cost`` made, now through ``average_costs``.

    Every acquisition is converted at its own date and the builder replays that historical
    cost: ``open_cost_basis`` and the position's ``cost_basis`` are never re-converted at a
    later day's rate. ``wac`` is per unit in the target currency, ``wac_asset`` in the asset's.
    """

    def test_buy_paid_in_another_currency_costs_its_amount_at_that_days_rate(self):
        # EUR asset bought with 100 USD on 01-02: cost = 100 USD × 0.9 = 90 EUR (18 EUR/unit),
        # whatever the USD rate does afterwards (0.5 on 01-03, the date of the end snapshot).
        buy = _tx(id=100, type="BUY", dt="2025-01-02", amount="-100", currency="USD", quantity="5", asset_id=100)
        builder = _builder(
            classified_txs=[_ctxn(buy)],
            asset_currencies={100: "EUR"},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.9"),
                ("USD", "EUR", date(2025, 1, 3)): Decimal("0.5"),
            },
        )

        result = builder.build()

        assert {s.date: s.open_cost_basis for s in result.daily_states} == {date(2025, 1, 1): Decimal("0"), date(2025, 1, 2): Decimal("90"), date(2025, 1, 3): Decimal("90")}
        (position,) = result.position_states_end
        assert position.cost_basis == Decimal("90")
        assert position.wac == Decimal("18")  # 100 USD × 0.9 / 5
        assert position.wac_currency == "EUR"
        assert position.cost_complete is True
        assert result.missing_fx == {}

    def test_transfer_override_in_a_third_currency_costs_the_same_in_both_legs(self):
        # GBP asset received with a 50 USD/unit override, 4 units on 01-02:
        #   report leg: 200 USD × 0.8 = 160 EUR (40 EUR/unit);
        #   asset leg:  160 EUR × (1 / 1.6) = 100 GBP (25 GBP/unit, the old cross rate 0.8 / 1.6).
        # 01-03 is re-evaluated (a GBP quote lands): GBP/EUR is 2.0 there, the cost stays 160 EUR.
        transfer_in = _tx(id=101, type="TRANSFER", dt="2025-01-02", quantity="4", asset_id=101, cost_basis_override="50", cost_basis_currency="USD")
        builder = _builder(
            classified_txs=[_ctxn(transfer_in)],
            asset_currencies={101: "GBP"},
            price_map={101: [(date(2025, 1, 3), Decimal("30"), "GBP")]},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.8"),
                ("GBP", "EUR", date(2025, 1, 2)): Decimal("1.6"),
                ("GBP", "EUR", date(2025, 1, 3)): Decimal("2.0"),
            },
        )

        result = builder.build()

        assert {s.date: s.open_cost_basis for s in result.daily_states} == {date(2025, 1, 1): Decimal("0"), date(2025, 1, 2): Decimal("160"), date(2025, 1, 3): Decimal("160")}
        (position,) = result.position_states_end
        assert position.cost_basis == Decimal("160")
        assert position.wac == Decimal("40")
        assert position.wac_currency == "EUR"
        assert position.asset_currency == "GBP"
        assert position.wac_asset == Decimal("25")
        assert position.cost_complete is True
        assert position.market_value == Decimal("240")  # 4 × 30 GBP × 2.0
        assert position.unrealized_pnl == Decimal("80")  # against the historical 160, not 100 GBP × 2.0 = 200
        assert result.missing_fx == {}

    def test_buy_paid_in_the_target_currency_costs_the_amount_exactly_for_a_foreign_asset(self):
        # Issue #32: USD asset bought with 500 EUR (the target currency) costs exactly 500 EUR.
        # The report leg needs no rate — the map has no EUR/EUR rate and nothing asks for one;
        # the USD rates only give the asset leg (500 EUR / 0.8 = 625 USD) and never move the EUR cost.
        buy = _tx(id=102, type="BUY", dt="2025-01-02", amount="-500", currency="EUR", quantity="4", asset_id=102)
        builder = _builder(
            classified_txs=[_ctxn(buy)],
            asset_currencies={102: "USD"},
            price_map={102: [(date(2025, 1, 3), Decimal("150"), "USD")]},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.8"),
                ("USD", "EUR", date(2025, 1, 3)): Decimal("0.5"),
            },
        )

        result = builder.build()

        assert {s.date: s.open_cost_basis for s in result.daily_states} == {date(2025, 1, 1): Decimal("0"), date(2025, 1, 2): Decimal("500"), date(2025, 1, 3): Decimal("500")}
        (position,) = result.position_states_end
        assert position.cost_basis == Decimal("500")
        assert position.wac == Decimal("125")
        assert position.wac_currency == "EUR"
        assert position.asset_currency == "USD"
        assert position.wac_asset == Decimal("156.25")  # 625 USD / 4
        assert position.cost_complete is True
        assert result.missing_fx == {}  # no conversion failed: in particular no EUR/EUR


class TestPrivateInTransitHelper:
    """Direct unit tests for in-transit aggregation helper."""

    def test_compute_in_transit_combines_cash_market_value_and_cost_basis(self):
        cash_dep = _tx(id=200, dt="2025-01-01", type="CASH_TRANSFER", amount="-300", currency="USD")
        cash_arr = _tx(id=201, broker_id=20, dt="2025-01-04", type="CASH_TRANSFER", amount="300", currency="USD")
        asset_dep = _tx(id=202, dt="2025-01-01", type="TRANSFER", quantity="-4", asset_id=100)
        asset_arr = _tx(id=203, broker_id=20, dt="2025-01-04", type="TRANSFER", quantity="4", asset_id=100)

        builder = _builder(
            in_transit_intervals=[
                InTransitInterval(
                    start_date=date(2025, 1, 2),
                    end_date=date(2025, 1, 3),
                    tx_type="cash",
                    departure_leg=cash_dep,
                    arrival_leg=cash_arr,
                    share=Decimal("0.25"),
                ),
                InTransitInterval(
                    start_date=date(2025, 1, 2),
                    end_date=date(2025, 1, 3),
                    tx_type="asset",
                    departure_leg=asset_dep,
                    arrival_leg=asset_arr,
                    share=Decimal("0.5"),
                    asset_id=100,
                    cost_basis_amount=Decimal("20"),
                    cost_basis_currency="USD",
                ),
            ],
            price_map={100: [(date(2025, 1, 2), Decimal("50"), "EUR")]},
            quote_base_map={100: None},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.9"),
                # D6: the frozen cost is converted at the arrival leg's date, 2025-01-04
                ("USD", "EUR", date(2025, 1, 4)): Decimal("0.75"),
            },
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )

        missing_fx: set[str] = set()
        it_cash, it_asset_mv, it_asset_cb = builder._compute_in_transit(date(2025, 1, 2), missing_fx)

        assert it_cash == Decimal("67.5")  # 300 USD * 0.9 * 0.25
        assert it_asset_mv == Decimal("100")  # 4 * 50 * 0.5
        # D6: historical cost at the arrival-date rate, 80 USD * 0.75 * 0.5 (was 36 = 80 * 0.9 * 0.5 at the transit day's rate)
        assert it_asset_cb == Decimal("30")
        assert missing_fx == set()
        assert builder._missing_fx == {}

    def test_compute_in_transit_cost_is_not_reconverted_on_each_transit_day(self):
        """D6: CBO × quantity is converted once, at the arrival date, so the in-transit cost is
        the same on every transit day while the USD rate moves; cash in transit still follows
        each day's rate."""
        cash_dep = _tx(id=200, dt="2025-01-01", type="CASH_TRANSFER", amount="-300", currency="USD")
        cash_arr = _tx(id=201, broker_id=20, dt="2025-01-04", type="CASH_TRANSFER", amount="300", currency="USD")
        asset_dep = _tx(id=202, dt="2025-01-01", type="TRANSFER", quantity="-4", asset_id=100)
        asset_arr = _tx(id=203, broker_id=20, dt="2025-01-04", type="TRANSFER", quantity="4", asset_id=100)
        builder = _builder(
            in_transit_intervals=[
                InTransitInterval(start_date=date(2025, 1, 2), end_date=date(2025, 1, 3), tx_type="cash", departure_leg=cash_dep, arrival_leg=cash_arr, share=Decimal("1")),
                InTransitInterval(
                    start_date=date(2025, 1, 2),
                    end_date=date(2025, 1, 3),
                    tx_type="asset",
                    departure_leg=asset_dep,
                    arrival_leg=asset_arr,
                    share=Decimal("1"),
                    asset_id=100,
                    cost_basis_amount=Decimal("20"),
                    cost_basis_currency="USD",
                ),
            ],
            price_map={100: [(date(2025, 1, 2), Decimal("50"), "EUR")]},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.9"),
                ("USD", "EUR", date(2025, 1, 3)): Decimal("0.6"),
                ("USD", "EUR", date(2025, 1, 4)): Decimal("0.75"),
            },
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )

        cash_day2, _, cost_day2 = builder._compute_in_transit(date(2025, 1, 2), set())
        cash_day3, _, cost_day3 = builder._compute_in_transit(date(2025, 1, 3), set())

        assert (cash_day2, cash_day3) == (Decimal("270"), Decimal("180"))  # 300 USD at each day's rate
        assert cost_day2 == cost_day3 == Decimal("60")  # 80 USD * 0.75, the arrival-date rate, on both days
        assert builder._missing_fx == {}

    def test_compute_in_transit_missing_arrival_rate_is_a_movement_failure_dated_at_arrival(self):
        """No USD rate at the arrival date: the in-transit cost is left out (never re-converted at
        the transit day's rate), and the failure is recorded as a movement conversion — pair and
        arrival date in ``builder._missing_fx`` — not as a valuation failure of the day."""
        asset_dep = _tx(id=202, dt="2025-01-01", type="TRANSFER", quantity="-4", asset_id=100)
        asset_arr = _tx(id=203, broker_id=20, dt="2025-01-04", type="TRANSFER", quantity="4", asset_id=100)
        builder = _builder(
            in_transit_intervals=[
                InTransitInterval(
                    start_date=date(2025, 1, 2),
                    end_date=date(2025, 1, 3),
                    tx_type="asset",
                    departure_leg=asset_dep,
                    arrival_leg=asset_arr,
                    share=Decimal("1"),
                    asset_id=100,
                    cost_basis_amount=Decimal("20"),
                    cost_basis_currency="USD",
                )
            ],
            price_map={100: [(date(2025, 1, 2), Decimal("50"), "EUR")]},
            fx_rate_map={("USD", "EUR", date(2025, 1, 2)): Decimal("0.9")},  # the transit day's rate only
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )

        missing_fx: set[str] = set()
        _, it_asset_mv, it_asset_cb = builder._compute_in_transit(date(2025, 1, 2), missing_fx)

        assert it_asset_cb == Decimal("0")
        assert it_asset_mv == Decimal("200")  # 4 * 50 EUR: the market value does not need the cost
        assert builder._missing_fx == {"USD/EUR": {date(2025, 1, 4)}}
        assert missing_fx == set()
        # The same failure reaches the result of a full build.
        assert builder.build().missing_fx == {"USD/EUR": {date(2025, 1, 4)}}

    def test_compute_in_transit_uses_frozen_per_unit_cost_when_unpriced(self):
        asset_dep = _tx(id=202, broker_id=10, dt="2025-01-01", type="TRANSFER", quantity="-4", asset_id=100)
        asset_arr = _tx(id=203, broker_id=20, dt="2025-01-04", type="TRANSFER", quantity="4", asset_id=100)
        builder = _builder(
            in_transit_intervals=[
                InTransitInterval(
                    start_date=date(2025, 1, 2),
                    end_date=date(2025, 1, 3),
                    tx_type="asset",
                    departure_leg=asset_dep,
                    arrival_leg=asset_arr,
                    share=Decimal("1"),
                    asset_id=100,
                    cost_basis_amount=Decimal("20"),
                    cost_basis_currency="EUR",
                )
            ],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )

        missing_fx: set[str] = set()
        _, it_asset_mv, it_asset_cb = builder._compute_in_transit(date(2025, 1, 2), missing_fx)

        assert it_asset_mv == Decimal("80")
        assert it_asset_cb == Decimal("80")
        assert missing_fx == set()


_AT_COST = "ESTIMATED_AT_COST"


def _at_cost_problems(position, value: str) -> list[str]:
    """What keeps ``position`` from being valued at its book cost ``value``, as a declared estimate (J-17).

    No price is reported for it: the effective and reference fields stay empty, it is never
    stale, it needs no rate, and its unrealized result is 0.
    """
    expected = {
        "valuation_source": _AT_COST,
        "market_value": Decimal(value),
        "cost_basis": Decimal(value),
        "unrealized_pnl": Decimal("0"),
        "valuation_effective_unit_price": None,
        "valuation_effective_currency": None,
        "valuation_reference_date": None,
        "valuation_reference_unit_price": None,
        "valuation_reference_currency": None,
        "valuation_stale": False,
        "missing_fx_pair": None,
        "cost_complete": True,
    }
    return [f"{position.date}/asset {position.asset_id}: {name}={getattr(position, name)!r}, expected {want!r}" for name, want in expected.items() if getattr(position, name) != want]


def _day_problems(states, day: date, **expected) -> list[str]:
    """Mismatches between the DailyPortfolioState of ``day`` and ``expected`` (field -> value)."""
    state = next((s for s in states if s.date == day), None)
    if state is None:
        return [f"{day}: no state emitted"]
    return [f"{day}: {name}={getattr(state, name)!r}, expected {want!r}" for name, want in expected.items() if getattr(state, name) != want]


class TestValuedAtCostWithoutObservation:
    """J-17 (developer's P2 and option A, 16/10): an ADJUSTMENT is never a price observation, and a
    held position with no observation on or before the day is valued at its book cost.

    When the resolver has nothing on or before the day (it was MISSING) and the position's average-
    cost pool is complete (``CostStep.report_complete``), the position is ``ESTIMATED_AT_COST``: its
    value is the pool's historical cost in the report currency (each acquisition at its own date's
    rate, never re-converted), no price, unrealized 0, not missing (``nav_complete`` holds), not
    transaction-implied. An unknown or incomplete cost stays MISSING. An orphan TRANSFER leg of such
    an asset is capital at the cost it moves in its pool, so it crosses the scope boundary without a
    fake gain. The pool counts an unknown cost as zero, so a leg moves its known cost whether the pool
    is complete or not, as an in-kind ADJUSTMENT does: nothing is left in the capital once the units
    are gone.

    Built like ``PortfolioCalculationEngine.calculate``: the mark series from the transactions and the
    quotes (``_builder``), the average costs from the same rate map.
    """

    def test_estimated_at_cost_is_a_valuation_source(self):
        """Before J-17: ValueError/AttributeError — ValuationSource had MARKET_PRICE, LAST_TRADE_PRICE, MISSING only."""
        assert ValuationSource(_AT_COST) is ValuationSource.ESTIMATED_AT_COST
        assert ValuationSource.ESTIMATED_AT_COST == "ESTIMATED_AT_COST"

    def test_adjustment_only_asset_is_valued_at_its_historical_cost_through_an_fx_move(self):
        """(a) USD asset received only by an ADJUSTMENT-in of 10 units at 20 USD on 01-01; no quote,
        no BUY/SELL; USD→EUR 0.9, 0.8, 0.7 on 01-01..01-03. The cost is 200 USD × 0.9 = 180 EUR,
        booked as in-kind capital. Every day: valued at 180 EUR at cost (flat through the rate move),
        NAV 180, total P&L 0, unrealized 0 — none of it from the asset nor from the rate, so the USD
        unrealized split is (0, 0, 0) —, not missing, not transaction-implied.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 20 USD converted at each day's rate —
        market value 180, 160, 140 EUR, total P&L 0, -20, -40, the USD split's fx part 0, -20, -40,
        the asset transaction-implied every day.
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=300, cost_basis_override="20", cost_basis_currency="USD")
        builder = _builder(
            classified_txs=[_ctxn(adj)],
            asset_currencies={300: "USD"},
            asset_types={300: "ETF"},
            asset_classifications={300: None},
            fx_rate_map={
                ("USD", "EUR", date(2025, 1, 1)): Decimal("0.9"),
                ("USD", "EUR", date(2025, 1, 2)): Decimal("0.8"),
                ("USD", "EUR", date(2025, 1, 3)): Decimal("0.7"),
            },
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
        )

        result = builder.build()

        (start,) = result.position_states_start
        (end,) = result.position_states_end
        problems = _at_cost_problems(start, "180") + _at_cost_problems(end, "180")
        for day in (date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("180"),
                nav_value=Decimal("180"),
                open_cost_basis=Decimal("180"),
                cumulative_external_cash_flow=Decimal("180"),
                total_pnl=Decimal("0"),
                unrealized_gain_loss=Decimal("0"),
                unrealized_by_currency={"USD": UnrealizedSplit(asset=Decimal("0"), fx=Decimal("0"), unsplit=Decimal("0"))},
                missing_price_asset_ids=set(),
                transaction_implied_asset_ids=set(),
                missing_fx_pairs=set(),
                nav_complete=True,
            )
        assert not problems, "\n".join(problems)
        assert result.missing_fx == {}

    def test_adjustment_without_cost_stays_missing(self):
        """(b) Guard: an ADJUSTMENT-in with no cost_basis_override leaves the cost unknown, so the
        position stays MISSING — no value, flagged missing, NAV incomplete.

        Before J-17: the same (guard, green before and after).
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=301)
        result = _builder(classified_txs=[_ctxn(adj)], asset_currencies={301: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 2)).build()

        (position,) = result.position_states_end
        assert (position.valuation_source, position.market_value, position.unrealized_pnl, position.cost_complete) == ("MISSING", None, None, False)
        problems = []
        for day in (date(2025, 1, 1), date(2025, 1, 2)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("0"), missing_price_asset_ids={301}, transaction_implied_asset_ids=set(), nav_complete=False)
        assert not problems, "\n".join(problems)

    def test_priced_adjustment_whose_cost_cannot_be_converted_stays_missing(self):
        """(b) ADJUSTMENT-in of 10 units at 20 USD with no USD→EUR rate at all: the cost cannot reach
        the report currency (pool incomplete, the pair reported as a movement failure), so the position
        is MISSING, not at cost and not at the adjustment's price.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 20 USD, market value None for the missing
        rate (missing_fx_pair USD/EUR), the asset transaction-implied and NOT missing (nav_complete True).
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=302, cost_basis_override="20", cost_basis_currency="USD")
        result = _builder(classified_txs=[_ctxn(adj)], asset_currencies={302: "USD"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 2)).build()

        assert result.missing_fx == {"USD/EUR": {date(2025, 1, 1)}}, "precondition: the adjustment's cost cannot be converted"
        (position,) = result.position_states_end
        assert position.valuation_source == "MISSING", f"valuation_source={position.valuation_source!r}"
        assert (position.market_value, position.cost_complete, position.missing_fx_pair) == (None, False, None)
        assert position.valuation_reference_date is None
        problems = []
        for day in (date(2025, 1, 1), date(2025, 1, 2)):
            problems += _day_problems(result.daily_states, day, missing_price_asset_ids={302}, transaction_implied_asset_ids=set(), missing_fx_pairs=set(), nav_complete=False)
        assert not problems, "\n".join(problems)

    def test_priced_and_unpriced_adjustments_on_one_position_stay_missing(self):
        """(b) Same day, same position: ADJUSTMENT-in 10 units at 20 EUR, then ADJUSTMENT-in 5 units
        with no cost. Part of the pool has no known cost, so the position is MISSING (cost_basis keeps
        the known 200).

        Before J-17: LAST_TRADE_PRICE at the priced adjustment's 20 EUR on all 15 units (300), the asset
        transaction-implied, not missing.
        """
        priced = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=303, cost_basis_override="20", cost_basis_currency="EUR")
        unpriced = _tx(id=2, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=303)
        result = _builder(classified_txs=[_ctxn(priced), _ctxn(unpriced)], asset_currencies={303: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 2)).build()

        (position,) = result.position_states_end
        assert position.valuation_source == "MISSING", f"valuation_source={position.valuation_source!r}"
        assert (position.market_value, position.cost_complete, position.cost_basis) == (None, False, Decimal("200"))
        problems = _day_problems(result.daily_states, date(2025, 1, 2), missing_price_asset_ids={303}, transaction_implied_asset_ids=set(), nav_complete=False)
        assert not problems, "\n".join(problems)

    def test_weekend_adjustment_does_not_replace_fridays_quote(self):
        """(c) Quote 50 EUR on Friday 2025-01-03; ADJUSTMENT-in of 10 units at 40 EUR on Saturday
        01-04; nothing on Sunday 01-05. Saturday and Sunday are valued at Friday's quote carried:
        MARKET_PRICE 500, reference Friday, unrealized +100 over the 400 cost, total P&L +100.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 40 EUR — 400 on Saturday and Sunday,
        reference Saturday, total P&L 0, the asset transaction-implied.
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-04", quantity="10", asset_id=304, cost_basis_override="40", cost_basis_currency="EUR")
        result = _builder(
            classified_txs=[_ctxn(adj)],
            asset_currencies={304: "EUR"},
            price_map={304: [(date(2025, 1, 3), Decimal("50"), "EUR")]},
            date_from=date(2025, 1, 3),
            date_to=date(2025, 1, 5),
        ).build()

        (sunday,) = result.position_states_end
        assert sunday.date == date(2025, 1, 5)
        assert sunday.valuation_source == "MARKET_PRICE", f"valuation_source={sunday.valuation_source!r}"
        assert (sunday.market_value, sunday.cost_basis, sunday.unrealized_pnl) == (Decimal("500"), Decimal("400"), Decimal("100"))
        assert (sunday.valuation_reference_date, sunday.valuation_reference_unit_price, sunday.valuation_reference_currency) == (date(2025, 1, 3), Decimal("50"), "EUR")
        assert (sunday.valuation_effective_unit_price, sunday.valuation_effective_currency, sunday.valuation_stale) == (Decimal("50"), "EUR", False)
        problems = []
        for day in (date(2025, 1, 4), date(2025, 1, 5)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("500"),
                nav_value=Decimal("500"),
                cumulative_external_cash_flow=Decimal("400"),
                total_pnl=Decimal("100"),
                transaction_implied_asset_ids=set(),
                missing_price_asset_ids=set(),
            )
        assert not problems, "\n".join(problems)

    def test_adjustment_before_the_first_quote_is_at_cost_then_market(self):
        """(d) ADJUSTMENT-in of 10 units at 40 EUR on 01-01, first quotes 50 on 01-03 and 52 on 01-04.
        01-01 and 01-02 are valued at cost (400, P&L 0, not implied, not missing); from 01-03 at the
        market (500, then 520).

        Before J-17: 01-01 and 01-02 were LAST_TRADE_PRICE at the adjustment's 40 EUR (same 400, but
        the asset transaction-implied and the opening position's source LAST_TRADE_PRICE, reference 01-01).
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=305, cost_basis_override="40", cost_basis_currency="EUR")
        result = _builder(
            classified_txs=[_ctxn(adj)],
            asset_currencies={305: "EUR"},
            price_map={305: [(date(2025, 1, 3), Decimal("50"), "EUR"), (date(2025, 1, 4), Decimal("52"), "EUR")]},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        ).build()

        (opening,) = result.position_states_start
        (closing,) = result.position_states_end
        problems = _at_cost_problems(opening, "400")
        for day in (date(2025, 1, 1), date(2025, 1, 2)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("400"), total_pnl=Decimal("0"), transaction_implied_asset_ids=set(), missing_price_asset_ids=set(), nav_complete=True)
        problems += _day_problems(result.daily_states, date(2025, 1, 3), market_value=Decimal("500"), total_pnl=Decimal("100"))
        problems += _day_problems(result.daily_states, date(2025, 1, 4), market_value=Decimal("520"), total_pnl=Decimal("120"))
        assert not problems, "\n".join(problems)
        assert (closing.valuation_source, closing.market_value, closing.valuation_reference_date) == ("MARKET_PRICE", Decimal("520"), date(2025, 1, 4))

    def test_orphan_transfer_in_of_an_unpriced_asset_is_capital_at_cost(self):
        """(e) An orphan TRANSFER-in (no partner) of 10 units with a 30 EUR cost basis, on 01-02, of an
        asset never quoted nor traded: valued at its cost 300, and the same 300 is in-kind capital, so
        NAV 300, capital 300, total P&L 0 — unchanged by the transfer. Not a cash flow of the day.

        Before J-17: MISSING — no value (NAV 0), no capital (the leg could not be valued), the asset
        missing and the NAV incomplete from 01-02.
        """
        transfer_in = _tx(id=1, type="TRANSFER", dt="2025-01-02", currency=None, quantity="10", asset_id=306, cost_basis_override="30", cost_basis_currency="EUR")
        result = _builder(classified_txs=[_ctxn(transfer_in)], asset_currencies={306: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 3)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), nav_value=Decimal("0"), cumulative_external_cash_flow=Decimal("0"), total_pnl=Decimal("0"))
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("300"),
                nav_value=Decimal("300"),
                cumulative_external_cash_flow=Decimal("300"),
                total_pnl=Decimal("0"),
                external_cash_flow=Decimal("0"),
                missing_price_asset_ids=set(),
                nav_complete=True,
            )
        (position,) = result.position_states_end
        problems += _at_cost_problems(position, "300")
        assert not problems, "\n".join(problems)
        contribution = next(s for s in result.daily_states if s.date == date(2025, 1, 3)).broker_contributions[10]
        assert (contribution.nav_contribution, contribution.capital_contribution, contribution.pnl_contribution) == (Decimal("300"), Decimal("300"), Decimal("0"))

    def test_orphan_transfer_into_an_at_cost_position_brings_its_own_cost_as_capital(self):
        """(e) ADJUSTMENT-in of 10 units at 20 EUR on 01-01 (at cost 200, capital 200), then an orphan
        TRANSFER-in of 5 units with a 40 EUR cost basis on 01-02. The pool is 15 units costing 400, the
        NAV rises by the 200 the transfer brings, so the capital must rise by that same 200 (not by
        5/15 of the pool's 400): total P&L stays 0 on both days.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 20 EUR — 01-02 market value 300 (15 × 20),
        transfer capital 100 (5 × 20), capital 300, unrealized -100, the asset transaction-implied.
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=307, cost_basis_override="20", cost_basis_currency="EUR")
        transfer_in = _tx(id=2, type="TRANSFER", dt="2025-01-02", currency=None, quantity="5", asset_id=307, cost_basis_override="40", cost_basis_currency="EUR")
        result = _builder(classified_txs=[_ctxn(adj), _ctxn(transfer_in)], asset_currencies={307: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 3)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), market_value=Decimal("200"), cumulative_external_cash_flow=Decimal("200"), total_pnl=Decimal("0"), transaction_implied_asset_ids=set())
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("400"),
                nav_value=Decimal("400"),
                cumulative_external_cash_flow=Decimal("400"),
                total_pnl=Decimal("0"),
                unrealized_gain_loss=Decimal("0"),
                transaction_implied_asset_ids=set(),
            )
        (position,) = result.position_states_end
        problems += _at_cost_problems(position, "400")
        assert not problems, "\n".join(problems)

    def test_an_old_buy_price_beats_a_later_adjustment_carried_and_stale(self):
        """No at-cost estimate once a price exists, however old (developer, 16/10): BUY of 10 at 100 EUR on
        01-01, priced ADJUSTMENT-in of 10 at 150 EUR on 01-20, nothing else. From 01-20 the 20 units are
        valued at the BUY's 100 carried from 01-01 — LAST_TRADE_PRICE, stale (19 days > 7) — never at the
        adjustment's 150, nor at cost.

        Before J-17: the adjustment's 150 became the mark on 01-20 — market value 3000, reference 01-20
        at 150, fresh (not stale), unrealized +500.
        """
        buy = _tx(id=1, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=308)
        adj = _tx(id=2, type="ADJUSTMENT", dt="2025-01-20", quantity="10", asset_id=308, cost_basis_override="150", cost_basis_currency="EUR")
        result = _builder(classified_txs=[_ctxn(buy), _ctxn(adj)], asset_currencies={308: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 21)).build()

        problems = []
        for day in (date(2025, 1, 20), date(2025, 1, 21)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("2000"), transaction_implied_asset_ids={308}, stale_price_asset_ids={308}, missing_price_asset_ids=set())
        assert not problems, "\n".join(problems)
        (position,) = result.position_states_end
        observed = {
            "valuation_source": position.valuation_source,
            "market_value": position.market_value,
            "valuation_reference_date": position.valuation_reference_date,
            "valuation_reference_unit_price": position.valuation_reference_unit_price,
            "valuation_effective_unit_price": position.valuation_effective_unit_price,
            "valuation_stale": position.valuation_stale,
            "cost_basis": position.cost_basis,
            "unrealized_pnl": position.unrealized_pnl,
        }
        assert observed == {
            "valuation_source": "LAST_TRADE_PRICE",
            "market_value": Decimal("2000"),
            "valuation_reference_date": date(2025, 1, 1),
            "valuation_reference_unit_price": Decimal("100"),
            "valuation_effective_unit_price": Decimal("100"),
            "valuation_stale": True,
            "cost_basis": Decimal("2500"),
            "unrealized_pnl": Decimal("-500"),
        }

    def test_a_sell_is_the_first_price_after_an_adjustment(self):
        """Day by day, no look-ahead; SELL stays a price observation (developer, 16/10). ADJUSTMENT-in of
        10 at 40 EUR on 01-01, SELL of 4 for 220 EUR (55 a unit) on 01-03, nothing else. 01-01 and 01-02
        are at cost (400, P&L 0, not transaction-implied); from 01-03 the SELL's 55 marks the 6 left —
        LAST_TRADE_PRICE 330, NAV 330 + 220 of cash, P&L 150 on the 400 of in-kind capital.

        Before J-17: 01-01 and 01-02 were LAST_TRADE_PRICE at the adjustment's 40 (same 400, but the asset
        transaction-implied and the opening position's reference 01-01 at 40).
        """
        adj = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="10", asset_id=309, cost_basis_override="40", cost_basis_currency="EUR")
        sell = _tx(id=2, type="SELL", dt="2025-01-03", amount="220", quantity="-4", asset_id=309)
        result = _builder(classified_txs=[_ctxn(adj), _ctxn(sell)], asset_currencies={309: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 4)).build()

        (opening,) = result.position_states_start
        problems = _at_cost_problems(opening, "400")
        for day in (date(2025, 1, 1), date(2025, 1, 2)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("400"), nav_value=Decimal("400"), total_pnl=Decimal("0"), transaction_implied_asset_ids=set(), missing_price_asset_ids=set())
        for day in (date(2025, 1, 3), date(2025, 1, 4)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("330"), nav_value=Decimal("550"), total_pnl=Decimal("150"), transaction_implied_asset_ids={309}, missing_price_asset_ids=set())
        assert not problems, "\n".join(problems)
        (closing,) = result.position_states_end
        assert (closing.valuation_source, closing.market_value, closing.valuation_reference_date, closing.valuation_effective_unit_price) == ("LAST_TRADE_PRICE", Decimal("330"), date(2025, 1, 3), Decimal("55"))

    def test_orphan_transfer_out_of_an_at_cost_position_takes_its_cost_out_of_capital(self):
        """(e), the other way: an orphan TRANSFER-in of 10 units with a 30 EUR cost basis on 01-01 (an
        asset never quoted nor traded: at cost 300, capital 300), then an orphan TRANSFER-out of 4 on
        01-02. The leg leaves at the 120 of cost it takes from the pool, so the capital falls to 180 with
        the NAV (6 units at cost, 180): total P&L 0 on every day, and no cash flow of the day.

        Before J-17: neither leg could be valued (no capital) and the units were MISSING: NAV 0,
        capital 0, the asset missing and the NAV incomplete from 01-01.
        """
        transfer_in = _tx(id=1, type="TRANSFER", dt="2025-01-01", currency=None, quantity="10", asset_id=310, cost_basis_override="30", cost_basis_currency="EUR")
        transfer_out = _tx(id=2, type="TRANSFER", dt="2025-01-02", currency=None, quantity="-4", asset_id=310)
        result = _builder(classified_txs=[_ctxn(transfer_in), _ctxn(transfer_out)], asset_currencies={310: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 3)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), market_value=Decimal("300"), nav_value=Decimal("300"), cumulative_external_cash_flow=Decimal("300"), total_pnl=Decimal("0"), missing_price_asset_ids=set(), nav_complete=True)
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("180"),
                nav_value=Decimal("180"),
                cumulative_external_cash_flow=Decimal("180"),
                total_pnl=Decimal("0"),
                external_cash_flow=Decimal("0"),
                missing_price_asset_ids=set(),
                nav_complete=True,
            )
        (position,) = result.position_states_end
        problems += _at_cost_problems(position, "180")
        assert not problems, "\n".join(problems)

    def test_orphan_transfer_emptying_a_pool_of_unknown_cost_moves_its_known_cost(self):
        """(e), a pool of unknown cost: on 01-01 an ADJUSTMENT-in of 5 units at 10 EUR and one of 5 units
        with no cost, of an asset with no price at all — the pool's cost is incomplete, so the position is
        MISSING: NAV 0 and incomplete, the 50 of the priced ADJUSTMENT in the capital, P&L -50. On 01-02 an
        orphan TRANSFER-out of all 10 moves the pool's known cost, -50 (the unknown part counts as zero), as
        the in-kind ADJUSTMENT brought it in: once the units are gone the capital is 0, the NAV 0, the P&L 0,
        nothing held.

        Before J-17: the adjustment's 10 a unit was the mark (LAST_TRADE_PRICE): NAV 100 and P&L +50 on
        01-01; the leg moved -100 (10 x 10), so after the exit capital -50 and P&L +50. (The completeness
        check tried and reverted on 16/10 moved nothing: capital 50 and P&L -50 left after the exit.)
        """
        priced = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=311, cost_basis_override="10", cost_basis_currency="EUR")
        unpriced = _tx(id=2, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=311)
        transfer_out = _tx(id=3, type="TRANSFER", dt="2025-01-02", currency=None, quantity="-10", asset_id=311)
        result = _builder(classified_txs=[_ctxn(priced), _ctxn(unpriced), _ctxn(transfer_out)], asset_currencies={311: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 3)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), market_value=Decimal("0"), nav_value=Decimal("0"), open_cost_basis=Decimal("50"), cumulative_external_cash_flow=Decimal("50"), total_pnl=Decimal("-50"), missing_price_asset_ids={311}, nav_complete=False)
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("0"),
                nav_value=Decimal("0"),
                open_cost_basis=Decimal("0"),
                cumulative_external_cash_flow=Decimal("0"),
                total_pnl=Decimal("0"),
                external_cash_flow=Decimal("0"),
                missing_price_asset_ids=set(),
                nav_complete=True,
            )
        assert not problems, "\n".join(problems)
        assert result.position_states_end == []

    def test_orphan_transfer_out_of_part_of_a_pool_of_unknown_cost_moves_its_share_of_the_known_cost(self):
        """(e), reductions of a pool of unknown cost: the same pool (5 units at 10 EUR and 5 of no cost, no
        price at all; capital 50, P&L -50), then an orphan TRANSFER-out of 4 units on 01-02 and one of the 6
        left on 01-04. Each leg moves its proportional share of the pool's known cost: -20 (50 x 4/10),
        leaving 6 units MISSING at a cost of 30 against a capital of 30 (P&L -30); then -30, the rest, so
        after the last exit the capital is 0 and the P&L 0, nothing held.

        Before J-17: the adjustment's 10 a unit marked the asset (LAST_TRADE_PRICE): NAV 100; the first leg
        moved -40 (NAV 60, capital 10), the second -60 (NAV 0, capital -50); P&L +50 on every day, nothing
        missing. (J-17's earlier versions moved nothing on the first leg, the pool still incomplete after it.)
        """
        priced = _tx(id=1, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=312, cost_basis_override="10", cost_basis_currency="EUR")
        unpriced = _tx(id=2, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=312)
        first_out = _tx(id=3, type="TRANSFER", dt="2025-01-02", currency=None, quantity="-4", asset_id=312)
        last_out = _tx(id=4, type="TRANSFER", dt="2025-01-04", currency=None, quantity="-6", asset_id=312)
        result = _builder(classified_txs=[_ctxn(priced), _ctxn(unpriced), _ctxn(first_out), _ctxn(last_out)], asset_currencies={312: "EUR"}, date_from=date(2025, 1, 1), date_to=date(2025, 1, 5)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), market_value=Decimal("0"), nav_value=Decimal("0"), open_cost_basis=Decimal("50"), cumulative_external_cash_flow=Decimal("50"), total_pnl=Decimal("-50"), missing_price_asset_ids={312}, nav_complete=False)
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("0"), nav_value=Decimal("0"), open_cost_basis=Decimal("30"), cumulative_external_cash_flow=Decimal("30"), total_pnl=Decimal("-30"), missing_price_asset_ids={312}, nav_complete=False)
        for day in (date(2025, 1, 4), date(2025, 1, 5)):
            problems += _day_problems(result.daily_states, day, market_value=Decimal("0"), nav_value=Decimal("0"), open_cost_basis=Decimal("0"), cumulative_external_cash_flow=Decimal("0"), total_pnl=Decimal("0"), missing_price_asset_ids=set(), nav_complete=True)
        assert not problems, "\n".join(problems)
        assert result.position_states_end == []


# =============================================================================
# N78-1 — an outgoing ADJUSTMENT has no value, whatever it stores (J-24, inverted)
# =============================================================================

_J24_USD_ASSET = 400
_J24_EUR_ASSET = 401
_J24_HANDOVER_ID = 3
# 1 USD = 0.90 EUR on the purchase day (01-01), 0.80 on the day of the exit (01-02) and after
_J24_USD_RATES = {
    ("USD", "EUR", date(2025, 1, 1)): Decimal("0.9"),
    ("USD", "EUR", date(2025, 1, 2)): Decimal("0.8"),
    ("USD", "EUR", date(2025, 1, 3)): Decimal("0.8"),
}
# Only the purchase day's rate: a conversion asked on the day of the exit would be a movement failure
_J24_USD_RATE_OF_THE_PURCHASE_ONLY = {("USD", "EUR", date(2025, 1, 1)): Decimal("0.9")}


def _j24_handover(*, asset_id: int = _J24_USD_ASSET, quantity: str = "-10", cost: str | None = "100", currency: str | None = "USD") -> MagicMock:
    """The outgoing ADJUSTMENT under test, on 01-02: no cash, ``quantity`` units at ``cost`` a unit in ``currency``."""
    return _tx(id=_J24_HANDOVER_ID, type="ADJUSTMENT", dt="2025-01-02", currency=None, quantity=quantity, asset_id=asset_id, cost_basis_override=cost, cost_basis_currency=currency)


def _j24_book(handover: MagicMock, *, foreign: bool, share: str = "1") -> dict:
    """The builder inputs of one book: money deposited and spent on 10 units on 01-01, then ``handover`` on 01-02.

    Foreign: 1000 USD for 10 units of the USD asset, 100 USD a unit. Otherwise: 200 EUR for 10 units of the EUR asset,
    20 EUR a unit. Every row at the broker's ``share``, and the deposit's external flow at that share, as the
    classifier gives it (the cash is spent, so no foreign cash is left to revalue).
    """
    currency, paid, asset_id = ("USD", "1000", _J24_USD_ASSET) if foreign else ("EUR", "200", _J24_EUR_ASSET)
    deposit = _tx(id=1, type="DEPOSIT", dt="2025-01-01", amount=paid, currency=currency)
    buy = _tx(id=2, type="BUY", dt="2025-01-01", amount=f"-{paid}", currency=currency, quantity="10", asset_id=asset_id)
    return {
        "classified_txs": [_ctxn(deposit, share=share), _ctxn(buy, share=share), _ctxn(handover, share=share)],
        "external_cash_flows": [(date(2025, 1, 1), 10, Decimal(paid) * Decimal(share), currency)],
        "asset_currencies": {_J24_USD_ASSET: "USD", _J24_EUR_ASSET: "EUR"},
    }


def _sales_of(result, transaction_id: int) -> list[dict]:
    """The realized sales the replay booked for one row — found by the row's id, never by position — field by field."""
    fields = ("asset_id", "broker_id", "date", "quantity", "proceeds", "cost", "cost_complete")
    return [{name: getattr(sale, name) for name in fields} for sale in result.realized_sales if sale.transaction_id == transaction_id]


def _j24_sale(*, asset_id: int, quantity: str, proceeds: str | None, cost: str, cost_complete: bool = True) -> dict:
    """The RealizedSale expected for the exit of broker 10 on 01-02, in the shape of :func:`_sales_of`."""
    return {
        "asset_id": asset_id,
        "broker_id": 10,
        "date": date(2025, 1, 2),
        "quantity": Decimal(quantity),
        "proceeds": None if proceeds is None else Decimal(proceeds),
        "cost": Decimal(cost),
        "cost_complete": cost_complete,
    }


def _broker_problems(states, day: date, broker_id: int, **expected) -> list[str]:
    """Mismatches between one broker's contribution on ``day`` and ``expected`` (field -> value)."""
    state = next((s for s in states if s.date == day), None)
    contribution = state.broker_contributions.get(broker_id) if state is not None else None
    if contribution is None:
        return [f"{day}: no contribution of broker {broker_id}"]
    return [f"{day}/broker {broker_id}: {name}={getattr(contribution, name)!r}, expected {want!r}" for name, want in expected.items() if getattr(contribution, name) != want]


class TestAdjustmentOutHasNoValue:
    """N78-1 (the developer's decision, 21/10/2026): an outgoing ADJUSTMENT has no value — it only lowers the quantity.
    Whatever ``cost_basis_override`` the row stores is ignored: the capital (``cumulative_external_cash_flow``, and the
    broker's ``capital_contribution``) does not move, TWRR and MWRR see no flow that day, no rate is asked on its date, and
    the row realizes 0 − C, C the historical cost the pool gives up: one ``RealizedSale`` for the row, proceeds 0, cost C,
    ``cost_complete`` the pool's before the row — as the FIFO lots close it at 0. With or without a stored value, rows
    before ``date_from`` too (J1: one replay with the same rules every day). Unchanged: a split-linked ADJUSTMENT (a split
    rescales the pool and realizes nothing), the NAV, the pool (the PMC never moves on an exit).

    RED until N78-1, but for the split guard. Before N78-1 — J-24 (developer's rule P21) — an outgoing ADJUSTMENT storing a
    value handed its units over at ``D = |quantity × share| × cost_basis_override`` converted at its own date: the capital
    fell by D (by C without a rate that day, a movement failure dated that day), a RealizedSale booked proceeds D against
    C, and the day's performance flow was D; one without a value moved no capital and booked no RealizedSale (J-11, its
    −C landing in «other» on the Dashboard). Each docstring keeps what its test read before.

    Built like ``PortfolioCalculationEngine.calculate``: the mark series, the average costs and the native cash from
    the same transactions and rate map (``_builder``); the deposit's external flow as the classifier gives it.
    """

    def test_foreign_adjustment_out_storing_a_value_keeps_the_capital(self):
        """10 units of a USD asset bought for 1000 USD on 01-01, when 1 USD = 0.90 EUR — the 1000 USD deposited that
        day: capital 900, and the pool's cost C = 900 EUR —; an ADJUSTMENT −10 storing 100 USD a unit on 01-02, when
        1 USD = 0.80 EUR. From 01-02: capital 900, NAV 0 (no units, no cash), P&L −900, the broker's line alike, no cash
        flow of the day; one RealizedSale for the row — 10 units, proceeds 0, cost 900, a realized −900 —; no missing
        rate. 01-01 reads the same before and after: capital 900, NAV 900, P&L 0.

        Before N78-1 (J-24): from 01-02 capital 100 (900 − D, D = 800) and P&L −100; the RealizedSale's proceeds 800.
        """
        result = _builder(**_j24_book(_j24_handover(), foreign=True), fx_rate_map=_J24_USD_RATES).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), cumulative_external_cash_flow=Decimal("900"), nav_value=Decimal("900"), total_pnl=Decimal("0"))
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("900"), external_cash_flow=Decimal("0"), nav_value=Decimal("0"), total_pnl=Decimal("-900"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("900"), pnl_contribution=Decimal("-900"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_USD_ASSET, quantity="10", proceeds="0", cost="900")]
        assert result.missing_fx == {}

    def test_the_day_of_the_exit_has_no_performance_flow(self):
        """The same foreign book: TWRR and MWRR take the capital flows from the baseline's daily change
        (``DerivedViewsBuilder.build_performance_inputs``), and the baseline does not move on 01-02 — the only flow is the
        deposit of 01-01, −900 in the investor's sign.

        Before N78-1 (J-24): a flow of +800 on 01-02, the value handed over.
        """
        result = _builder(**_j24_book(_j24_handover(), foreign=True), fx_rate_map=_J24_USD_RATES).build()

        _navs, flows = DerivedViewsBuilder(result.daily_states, "EUR").build_performance_inputs()

        assert {flow.date: flow.amount for flow in flows} == {date(2025, 1, 1): Decimal("-900")}

    def test_a_stored_value_above_the_average_realizes_minus_the_cost(self):
        """One currency, a stored value other than the average: 10 units bought for 200 EUR on 01-01 (200 deposited;
        average 20), an ADJUSTMENT −4 storing 25 EUR on 01-02: C = 80. From 01-02: capital 200, NAV 120 (6 units at the
        purchase's 20, no cash), P&L −80 — the realized loss, nothing unrealized —, the broker's line alike; one
        RealizedSale of 4 units, proceeds 0, cost 80.

        Before N78-1 (J-24): capital 100 (200 − D, D = 100) and P&L +20; the RealizedSale's proceeds 100.
        """
        handover = _j24_handover(asset_id=_J24_EUR_ASSET, quantity="-4", cost="25", currency="EUR")
        result = _builder(**_j24_book(handover, foreign=False)).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), cumulative_external_cash_flow=Decimal("200"), nav_value=Decimal("200"), total_pnl=Decimal("0"))
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("200"), nav_value=Decimal("120"), open_cost_basis=Decimal("120"), total_pnl=Decimal("-80"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("200"), pnl_contribution=Decimal("-80"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_EUR_ASSET, quantity="4", proceeds="0", cost="80")]

    def test_a_stored_value_at_the_average_leaves_the_capital_alone_too(self):
        """The same EUR book with the ADJUSTMENT −4 storing the average, 20 EUR. From 01-02: capital 200, NAV 120, P&L
        −80, the broker's line alike; the only performance flow is the deposit's, −200 on 01-01; the row realizes 0 − 80.

        Before N78-1 (J-24, a guard then): capital 120 (200 − 80), P&L 0, a flow of +80 on 01-02, a realized 80 − 80 = 0.
        """
        handover = _j24_handover(asset_id=_J24_EUR_ASSET, quantity="-4", cost="20", currency="EUR")
        result = _builder(**_j24_book(handover, foreign=False)).build()

        problems = []
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("200"), nav_value=Decimal("120"), total_pnl=Decimal("-80"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("200"), pnl_contribution=Decimal("-80"))
        assert not problems, "\n".join(problems)
        _navs, flows = DerivedViewsBuilder(result.daily_states, "EUR").build_performance_inputs()
        assert {flow.date: flow.amount for flow in flows} == {date(2025, 1, 1): Decimal("-200")}
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_EUR_ASSET, quantity="4", proceeds="0", cost="80")]

    def test_owner_share_scales_the_cost_the_exit_realizes(self):
        """C is at the owner's share, as the pool's cost is: the EUR book of a broker owned at 50 % — 5 units costing
        100 EUR, 100 of capital —, the ADJUSTMENT −4 storing 25 EUR: 2 units leave, C = 2 × 20 = 40. From 01-02: capital
        100, NAV 60 (3 units at 20), P&L −40; one RealizedSale of 2 units, proceeds 0, cost 40.

        Before N78-1 (J-24): capital 50 (100 − |−4 × 0.5| × 25) and P&L +10; the RealizedSale's proceeds 50.
        """
        handover = _j24_handover(asset_id=_J24_EUR_ASSET, quantity="-4", cost="25", currency="EUR")
        result = _builder(**_j24_book(handover, foreign=False, share="0.5")).build()

        problems = []
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("100"), nav_value=Decimal("60"), total_pnl=Decimal("-40"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_EUR_ASSET, quantity="2", proceeds="0", cost="40")]

    def test_a_stored_value_without_currency_is_ignored_too(self):
        """The foreign book with the ADJUSTMENT's stored value written in no currency: still no value — from 01-02 capital
        900 and P&L −900; proceeds 0 against a cost of 900.

        Before N78-1 (J-24): 100 a unit counted in the asset's currency, D = 800 EUR: capital 100, P&L −100, proceeds 800.
        """
        result = _builder(**_j24_book(_j24_handover(currency=None), foreign=True), fx_rate_map=_J24_USD_RATES).build()

        problems = []
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("900"), total_pnl=Decimal("-900"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_USD_ASSET, quantity="10", proceeds="0", cost="900")]

    def test_no_rate_is_asked_on_the_day_of_the_exit(self):
        """The foreign book with no USD rate on 01-02 (0.90 on 01-01 only): nothing needs converting on that day. One
        RealizedSale for the row with proceeds 0 and cost 900, no missing pair; from 01-02 capital 900, NAV 0, P&L −900,
        the broker's line alike.

        Before N78-1 (J-24): proceeds None (the stored 1000 USD had no rate), USD/EUR missing on 01-02, and the capital
        fell by C: 0 from 01-02, P&L 0.
        """
        result = _builder(**_j24_book(_j24_handover(), foreign=True), fx_rate_map=_J24_USD_RATE_OF_THE_PURCHASE_ONLY).build()

        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_USD_ASSET, quantity="10", proceeds="0", cost="900")]
        assert result.missing_fx == {}
        problems = []
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("900"), nav_value=Decimal("0"), total_pnl=Decimal("-900"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("900"))
        assert not problems, "\n".join(problems)

    def test_an_exit_before_the_period_keeps_the_capital(self):
        """The foreign book read from 01-05 to 01-06: the purchase and the ADJUSTMENT come before ``date_from``, so they
        are replayed before the first emitted state (J1: with the same rules as any day). The states open on 01-05 with
        capital 900, NAV 0 and P&L −900, the broker's line alike; the row's RealizedSale is there (10 units, proceeds 0,
        cost 900, dated 01-02); no missing rate.

        Before N78-1 (J-24): capital 100 and P&L −100 on 01-05; the RealizedSale's proceeds 800.
        """
        rates = {**_J24_USD_RATES, ("USD", "EUR", date(2025, 1, 5)): Decimal("0.8"), ("USD", "EUR", date(2025, 1, 6)): Decimal("0.8")}
        result = _builder(**_j24_book(_j24_handover(), foreign=True), fx_rate_map=rates, date_from=date(2025, 1, 5), date_to=date(2025, 1, 6)).build()

        assert min(s.date for s in result.daily_states) == date(2025, 1, 5), "precondition: the frame starts after the two rows"
        problems = _day_problems(result.daily_states, date(2025, 1, 5), cumulative_external_cash_flow=Decimal("900"), nav_value=Decimal("0"), total_pnl=Decimal("-900"))
        problems += _broker_problems(result.daily_states, date(2025, 1, 5), 10, capital_contribution=Decimal("900"), pnl_contribution=Decimal("-900"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_USD_ASSET, quantity="10", proceeds="0", cost="900")]
        assert result.missing_fx == {}

    def test_an_exit_without_a_value_realizes_minus_its_cost(self):
        """The foreign book with the ADJUSTMENT −10 storing no value, and no rate on 01-02. The units go without moving
        the capital: 900 on every day, NAV 0 and P&L −900 from 01-02; one RealizedSale — 10 units, proceeds 0, cost 900:
        the Dashboard's realized −900, as the lots' (decision 3 of N78-1); no rate asked (no missing pair).

        Before N78-1 (J-11): the same capital, NAV and P&L, but no RealizedSale — the −900 sat in «other».
        """
        result = _builder(**_j24_book(_j24_handover(cost=None, currency=None), foreign=True), fx_rate_map=_J24_USD_RATE_OF_THE_PURCHASE_ONLY).build()

        problems = _day_problems(result.daily_states, date(2025, 1, 1), cumulative_external_cash_flow=Decimal("900"), nav_value=Decimal("900"), total_pnl=Decimal("0"))
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("900"), nav_value=Decimal("0"), total_pnl=Decimal("-900"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("900"))
        assert not problems, "\n".join(problems)
        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_USD_ASSET, quantity="10", proceeds="0", cost="900")]
        assert result.missing_fx == {}

    def test_split_linked_adjustment_out_with_a_cost_basis_moves_nothing(self):
        """GUARD: the ADJUSTMENT −5 of a 1-for-2 reverse split on 01-02, carrying a cost basis of 200 USD (as Auto mode
        once wrote on split rows), with no rate on 01-02. A split rescales the pool: the capital stays 900, the 5 units
        left keep the cost of 900, nothing is realized and no rate is asked. Green before and after J-24 and N78-1.
        """
        split = SplitRecord(event_id=90, asset_id=_J24_USD_ASSET, date=date(2025, 1, 2), ratio=Decimal("0.5"))
        result = _builder(
            **_j24_book(_j24_handover(quantity="-5", cost="200"), foreign=True),
            fx_rate_map=_J24_USD_RATE_OF_THE_PURCHASE_ONLY,
            split_linked_tx_ids={_J24_HANDOVER_ID},
            split_history={_J24_USD_ASSET: (split,)},
        ).build()

        problems = []
        for day in (date(2025, 1, 2), date(2025, 1, 3)):
            problems += _day_problems(result.daily_states, day, cumulative_external_cash_flow=Decimal("900"))
            problems += _broker_problems(result.daily_states, day, 10, capital_contribution=Decimal("900"))
        assert not problems, "\n".join(problems)
        (position,) = result.position_states_end
        assert (position.quantity, position.cost_basis) == (Decimal("5"), Decimal("900"))
        assert _sales_of(result, _J24_HANDOVER_ID) == []
        assert result.missing_fx == {}

    def test_cost_complete_is_the_pools_before_the_row(self):
        """As for a SELL, the RealizedSale says whether the pool it took from knew its whole cost. On 01-01: 5 units
        received by an ADJUSTMENT without cost basis and 5 bought for 100 EUR (10 units, a known cost of 100, the pool
        incomplete); on 01-02 the ADJUSTMENT −4 storing 25 EUR: proceeds 0, cost 40 (the known 100 × 4/10),
        cost_complete False — the Dashboard leaves it out of the realized.

        Before N78-1 (J-24): proceeds 100, the stored value.
        """
        deposit = _tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="100")
        received = _tx(id=2, type="ADJUSTMENT", dt="2025-01-01", quantity="5", asset_id=_J24_EUR_ASSET)
        buy = _tx(id=4, type="BUY", dt="2025-01-01", amount="-100", quantity="5", asset_id=_J24_EUR_ASSET)
        handover = _j24_handover(asset_id=_J24_EUR_ASSET, quantity="-4", cost="25", currency="EUR")
        result = _builder(
            classified_txs=[_ctxn(deposit), _ctxn(received), _ctxn(buy), _ctxn(handover)],
            external_cash_flows=[(date(2025, 1, 1), 10, Decimal("100"), "EUR")],
            asset_currencies={_J24_EUR_ASSET: "EUR"},
        ).build()

        assert _sales_of(result, _J24_HANDOVER_ID) == [_j24_sale(asset_id=_J24_EUR_ASSET, quantity="4", proceeds="0", cost="40", cost_complete=False)]


class TestClassificationResultHelper:
    """Tiny getter should expose already-computed paired IDs."""

    def test_get_needed_paired_ids_returns_internal_set(self):
        result = ClassificationResult()
        result._needed_paired_ids = {11, 22}

        assert result.get_needed_paired_ids() == {11, 22}

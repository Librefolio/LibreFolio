"""MF6-1 (workstream MF, wave 6, T-U5) — one home of «the price of an asset on a day»: ``marked_price`` and ``AssetMarks``.

Module under test: ``backend/app/services/financial_math/portfolio/daily_state.py``. New in the working tree:

* ``MarkedPrice`` and ``marked_price(series, splits, quote_base, day, default_currency)``: the mark of an asset on a day
  as the portfolio values it. A market quote is its own unit price (``MARKET_PRICE``, never split-adjusted); a trade
  mark is restated to current units through the splits since it was observed (unit = mark / cumulative split ratio,
  ``LAST_TRADE_PRICE``), and its reference price goes back to the per-unit axis of the trade record (mark /
  quote_base). ``DailyStateBuilder._market_value_for`` now calls it, so the valuation's
  ``effective_unit_price`` / ``reference_unit_price`` / ``source`` / ``split_adjusted`` are its fields;
* ``AssetMarks`` (frozen; ``PortfolioCalculationResult.marks``): the engine's reader of marks, splits and rates.
  ``price_at`` and ``last_market_price_at`` (the last market quote on or before the day — a later trade observation
  does not move it) answer on the engine's days only, ``first_day`` … ``last_day``; ``in_target`` multiplies by
  ``fx_rate_map[(ccy, target, day)]`` and is None without a rate or outside those days, even for an amount already in
  the target currency.

Red on HEAD ``33b66ba1c``: the whole file fails at collection, ``ImportError: cannot import name 'AssetMarks' from
'backend.app.services.financial_math.portfolio.daily_state'`` — new API. ``TestTheValuationReadsTheOneRule`` asserts
values that HEAD's inline ``_market_value_for`` gave too (its arithmetic is unchanged); on the tree it locks that the
valuation and the reader are one rule.

Isolation: PURE — no database, no server, no network, no clock: the builder is constructed directly, with no
transaction. Runs in ``./dev.py test services financial-math``; alone:
``./dev.py test services financial-math test_asset_marks``.

Reference: backend/app/services/financial_math/portfolio/daily_state.py (marked_price, AssetMarks,
DailyStateBuilder._market_value_for), backend/app/services/financial_math/price_marks.py (build_asset_price_series,
AssetPriceSeries.last_market_date).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.daily_state import AssetMarks, DailyStateBuilder, MarkedPrice, marked_price
from backend.app.services.financial_math.portfolio.models import SplitRecord, ValuationSource
from backend.app.services.financial_math.price_marks import AssetPriceSeries, build_asset_price_series
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

D = Decimal
EUR = "EUR"
USD = "USD"
ASSET = 7

D1, D2, D3, D4 = (date(2025, 5, day) for day in (1, 2, 3, 4))
BEFORE = date(2025, 4, 30)
AFTER = date(2025, 5, 5)


def _trade(tx_id: int, day: date, quantity: str, amount: str, currency: str = USD) -> SimpleNamespace:
    """A BUY as ``build_asset_price_series`` reads it: id, type, date, quantity, amount, currency."""
    return SimpleNamespace(id=tx_id, type=TransactionType.BUY, date=day, quantity=D(quantity), amount=D(amount), currency=currency)


def _series(*, closes: tuple[tuple[date, str], ...] = (), trades: tuple[SimpleNamespace, ...] = (), quote_base: int = 1, currency: str = USD) -> AssetPriceSeries:
    return build_asset_price_series(
        price_rows=[(day, D(close), currency) for day, close in closes],
        transactions=list(trades),
        split_linked_tx_ids=set(),
        asset_currency=currency,
        quote_base_quantity=quote_base,
    )


#: 2:1 on D2 — a unit observed before it is two units after it.
SPLIT = SplitRecord(event_id=1, asset_id=ASSET, date=D2, ratio=D("2"))


def _builder(series: AssetPriceSeries, *, quote_base: int | None, splits: tuple[SplitRecord, ...] = (), fx_rate_map=None) -> DailyStateBuilder:
    """A builder with no transaction: only what ``_market_value_for`` reads (the asset's series, quote base, splits,
    rates)."""
    rates = fx_rate_map or {}
    return DailyStateBuilder(
        classified_txs=[],
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map={},
        quote_base_map={ASSET: quote_base},
        fx_rate_map=rates,
        asset_classifications={ASSET: None},
        asset_types={ASSET: "STOCK"},
        asset_currencies={ASSET: USD},
        average_costs={},
        native_cash=engine_native_cash([], target_currency=EUR, fx_rate_map=rates, date_to=D4),
        target_currency=EUR,
        date_from=D1,
        date_to=D4,
        split_history={ASSET: splits} if splits else None,
        mark_series={ASSET: series},
    )


class TestMarkedPrice:
    def test_a_market_mark(self):
        """A close of 101.25 USD on D1, read on D3 (carried): unit = the close, MARKET_PRICE, not split-adjusted even
        across the D2 split (a real quote already sits on the current-unit axis)."""
        series = _series(closes=((D1, "101.25"),))
        priced = marked_price(series, (SPLIT,), None, D3, EUR)
        assert isinstance(priced, MarkedPrice)
        assert (priced.unit_price, priced.currency, priced.source, priced.reference_unit_price, priced.split_adjusted) == (D("101.25"), USD, ValuationSource.MARKET_PRICE, D("101.25"), False)
        assert priced.mark.as_of_date == D1

    def test_a_trade_mark_across_a_split(self):
        """A BUY of 10 for 1 000 USD on D1, no quote, a 2:1 split on D2, read on D3: unit 100 / 2 = 50,
        LAST_TRADE_PRICE, split-adjusted; the reference stays the trade's 100."""
        series = _series(trades=(_trade(1, D1, "10", "-1000"),))
        priced = marked_price(series, (SPLIT,), 1, D3, EUR)
        assert (priced.unit_price, priced.currency, priced.source, priced.reference_unit_price, priced.split_adjusted) == (D("50"), USD, ValuationSource.LAST_TRADE_PRICE, D("100"), True)

    def test_a_trade_mark_on_a_quote_base(self):
        """Quote base 100 (a bond's): the BUY's per-unit 100 is lifted to 10 000 on the market axis at ingestion; after
        the split the unit is 5 000, and the reference goes back to the per-unit 100 of the trade record."""
        series = _series(trades=(_trade(1, D1, "10", "-1000"),), quote_base=100)
        assert series.resolve(D1).unit_price == D("10000"), "precondition: the trade lifted to the market axis"
        priced = marked_price(series, (SPLIT,), 100, D3, EUR)
        assert (priced.unit_price, priced.reference_unit_price, priced.source, priced.split_adjusted) == (D("5000"), D("100"), ValuationSource.LAST_TRADE_PRICE, True)

    def test_a_trade_mark_before_the_split_is_not_adjusted(self):
        series = _series(trades=(_trade(1, D1, "10", "-1000"),))
        priced = marked_price(series, (SPLIT,), 1, D1, EUR)
        assert (priced.unit_price, priced.split_adjusted) == (D("100"), False)

    def test_no_mark(self):
        """No series, or a day before the first observation: None."""
        assert marked_price(None, (), None, D3, EUR) is None
        assert marked_price(_series(closes=((D2, "10"),)), (), None, D1, EUR) is None

    def test_the_default_currency_labels_nothing_that_has_one(self):
        priced = marked_price(_series(closes=((D1, "10"),), currency=USD), (), None, D1, EUR)
        assert priced.currency == USD


class TestTheValuationReadsTheOneRule:
    """``_market_value_for`` gives the fields of ``marked_price`` — the valuation and the reader are one rule."""

    @pytest.mark.parametrize(
        ("label", "series", "quote_base", "expected"),
        [
            ("market", _series(closes=((D1, "101.25"),)), None, (D("101.25"), D("101.25"), ValuationSource.MARKET_PRICE, False)),
            ("trade-split", _series(trades=(_trade(1, D1, "10", "-1000"),)), 1, (D("50"), D("100"), ValuationSource.LAST_TRADE_PRICE, True)),
            ("trade-quote-base", _series(trades=(_trade(1, D1, "10", "-1000"),), quote_base=100), 100, (D("5000"), D("100"), ValuationSource.LAST_TRADE_PRICE, True)),
        ],
    )
    def test_valuation_equals_marked_price(self, label, series, quote_base, expected):
        rates = {(USD, EUR, D3): D("0.8")}
        builder = _builder(series, quote_base=quote_base, splits=(SPLIT,), fx_rate_map=rates)
        valuation = builder._market_value_for(ASSET, D("4"), D3)
        priced = marked_price(series, (SPLIT,), quote_base, D3, EUR)
        observed = (valuation.effective_unit_price, valuation.reference_unit_price, valuation.source, valuation.split_adjusted)
        assert observed == (priced.unit_price, priced.reference_unit_price, priced.source, priced.split_adjusted) == expected, label
        assert valuation.effective_currency == valuation.reference_currency == priced.currency == USD
        assert valuation.reference_date == priced.mark.as_of_date == D1
        assert valuation.missing_fx_pair is None


def _marks(series: AssetPriceSeries, *, quote_base: int | None = 1, splits: tuple[SplitRecord, ...] = (), rates=None) -> AssetMarks:
    return AssetMarks(
        mark_series={ASSET: series},
        split_history={ASSET: splits},
        quote_base_map={ASSET: quote_base},
        fx_rate_map=rates or {},
        target_currency=EUR,
        first_day=D1,
        last_day=D4,
    )


class TestAssetMarksDays:
    """The reader answers on the engine's days only: ``first_day`` … ``last_day``."""

    def test_price_at_inside_is_marked_price(self):
        series = _series(trades=(_trade(1, D1, "10", "-1000"),))
        marks = _marks(series, splits=(SPLIT,))
        for day in (D1, D3, D4):
            assert marks.price_at(ASSET, day) == marked_price(series, (SPLIT,), 1, day, EUR), day

    def test_price_at_outside_is_none(self):
        """A close on 04-30 exists, but 04-30 and 05-05 are outside the engine's days."""
        marks = _marks(_series(closes=((BEFORE, "10"), (D1, "11"), (AFTER, "12"))))
        assert marks.price_at(ASSET, BEFORE) is None
        assert marks.price_at(ASSET, AFTER) is None
        assert marks.price_at(ASSET, D1).unit_price == D("11")

    def test_an_unknown_asset_has_no_price(self):
        marks = _marks(_series(closes=((D1, "11"),)))
        assert marks.price_at(ASSET + 1, D2) is None
        assert marks.last_market_price_at(ASSET + 1, D2) is None

    def test_last_market_price_at_outside_is_none(self):
        marks = _marks(_series(closes=((BEFORE, "10"), (D1, "11"))))
        assert marks.last_market_price_at(ASSET, BEFORE) is None
        assert marks.last_market_price_at(ASSET, AFTER) is None
        assert marks.last_market_price_at(ASSET, D4).unit_price == D("11")


class TestLastMarketPrice:
    def test_a_later_trade_does_not_move_it(self):
        """A close of 100 on D1, a BUY at 130 on D2: the mark of D3 is the trade (LAST_TRADE_PRICE, 130), the last
        market price is still D1's close."""
        series = _series(closes=((D1, "100"),), trades=(_trade(1, D2, "1", "-130"),))
        marks = _marks(series)
        assert marks.price_at(ASSET, D3).source == ValuationSource.LAST_TRADE_PRICE
        assert marks.price_at(ASSET, D3).unit_price == D("130")
        last = marks.last_market_price_at(ASSET, D3)
        assert (last.unit_price, last.source, last.mark.as_of_date) == (D("100"), ValuationSource.MARKET_PRICE, D1)

    def test_none_before_the_first_quote(self):
        """Only a trade on D1 and a close on D3: on D2 there is no market price yet."""
        marks = _marks(_series(closes=((D3, "100"),), trades=(_trade(1, D1, "1", "-90"),)))
        assert marks.last_market_price_at(ASSET, D2) is None
        assert marks.last_market_price_at(ASSET, D3).unit_price == D("100")


class TestInTarget:
    RATES = {(USD, EUR, D2): D("0.9"), (USD, EUR, D3): D("0.8")}

    def test_multiplies_by_the_day_s_rate(self):
        marks = _marks(_series(closes=((D1, "10"),)), rates=self.RATES)
        assert marks.in_target(D("25"), USD, D2) == D("22.5")
        assert marks.in_target(D("25"), USD, D3) == D("20.0")

    def test_no_rate_no_value(self):
        marks = _marks(_series(closes=((D1, "10"),)), rates=self.RATES)
        assert marks.in_target(D("25"), USD, D4) is None, "no USD/EUR rate on D4"
        assert marks.in_target(D("25"), "GBP", D2) is None

    def test_the_target_currency_is_the_amount(self):
        marks = _marks(_series(closes=((D1, "10"),)), rates=self.RATES)
        assert marks.in_target(D("25"), EUR, D4) == D("25")

    def test_outside_the_days_none_even_in_the_target_currency(self):
        rates = {**self.RATES, (USD, EUR, AFTER): D("0.7")}
        marks = _marks(_series(closes=((D1, "10"),)), rates=rates)
        assert marks.in_target(D("25"), EUR, BEFORE) is None
        assert marks.in_target(D("25"), EUR, AFTER) is None
        assert marks.in_target(D("25"), USD, AFTER) is None, "a rate stored for a day outside the engine's days is not read"


class TestTheReaderIsFrozen:
    def test_frozen(self):
        marks = _marks(_series(closes=((D1, "10"),)))
        with pytest.raises((AttributeError, TypeError)):
            marks.last_day = AFTER  # type: ignore[misc]

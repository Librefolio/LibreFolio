"""
MF-P4b small checkpoint (D-P4 cure B, contract ``CONTRATTO-P4b.md`` §6): ``AssetPriceSeries.observation_dates``.

Module under test: ``backend/app/services/financial_math/price_marks.py`` — a new public **property** of
``AssetPriceSeries``: the days that carry an observation (a MARKET quote, or a same-day TRADE average), ascending, as a
``tuple``; ``()`` without observations. It reflects the collapse the constructor already performs — a day with a quote
and trades appears once. The lots (J) read prices only on these candidate days instead of every calendar day.
``resolve()`` is unchanged: each observation day resolves exactly (MARKET / TRADE_AVG, ``as_of_date`` = that day), every
other day CARRIED or MISSING.

Built both directly from ``PriceObservation`` lists and through ``build_asset_price_series`` (whose filters — a
``None`` close, a split-linked row, an ADJUSTMENT, a zero quantity, a zero amount — decide what is an observation).

On HEAD ``445386f80`` the property does not exist: every test fails naming it.
"""

from __future__ import annotations

import inspect
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.price_marks import AssetPriceSeries, MarkSource, ObservationKind, PriceObservation, build_asset_price_series

D = Decimal
D0 = date(2026, 10, 1)


def d(n: int) -> date:
    return D0 + timedelta(days=n)


def _observation_dates(series: AssetPriceSeries):
    if not hasattr(type(series), "observation_dates"):
        pytest.fail("AssetPriceSeries.observation_dates is missing (MF-P4b §6)")
    return series.observation_dates


def _market(n: int, price: str = "10", ccy: str = "EUR") -> PriceObservation:
    return PriceObservation(date=d(n), unit_price=D(price), currency=ccy, kind=ObservationKind.MARKET)


def _trade(n: int, price: str = "10", ccy: str = "EUR") -> PriceObservation:
    return PriceObservation(date=d(n), unit_price=D(price), currency=ccy, kind=ObservationKind.TRADE)


def _tx(tx_id: int, tx_type: TransactionType, n: int, quantity: str | None, amount: str | None, currency: str = "EUR") -> SimpleNamespace:
    """The fields ``build_asset_price_series`` reads off a Transaction row, nothing else."""
    return SimpleNamespace(id=tx_id, type=tx_type, date=d(n), quantity=None if quantity is None else D(quantity), amount=None if amount is None else D(amount), currency=currency)


class TestObservationDatesDirect:
    def test_is_a_property(self):
        attr = inspect.getattr_static(AssetPriceSeries, "observation_dates", None)
        if attr is None:
            pytest.fail("AssetPriceSeries.observation_dates is missing (MF-P4b §6)")
        assert isinstance(attr, property), "observation_dates is a property, not a method"

    def test_empty_series_is_an_empty_tuple(self):
        dates = _observation_dates(AssetPriceSeries([]))
        assert dates == ()
        assert type(dates) is tuple

    def test_market_only(self):
        series = AssetPriceSeries([_market(5), _market(1), _market(3)])
        dates = _observation_dates(series)
        assert type(dates) is tuple
        assert dates == (d(1), d(3), d(5))

    def test_trade_only_same_day_trades_collapse_to_one_day(self):
        series = AssetPriceSeries([_trade(4, "10"), _trade(2, "12"), _trade(4, "14"), _trade(4, "9")])
        assert _observation_dates(series) == (d(2), d(4))

    def test_mixed_same_day_quote_and_trades_appear_once(self):
        series = AssetPriceSeries([_trade(3, "11"), _market(3, "10"), _trade(3, "12"), _market(1), _trade(6), _market(6, "7"), _trade(8)])
        assert _observation_dates(series) == (d(1), d(3), d(6), d(8))

    def test_duplicate_market_rows_on_a_day_appear_once(self):
        series = AssetPriceSeries([_market(2, "10"), _market(2, "11"), _market(9)])
        assert _observation_dates(series) == (d(2), d(9))

    def test_elements_are_dates_and_strictly_ascending(self):
        series = AssetPriceSeries([_trade(n) if n % 3 else _market(n) for n in (17, 3, 9, 3, 0, 12, -40, 9)])
        dates = _observation_dates(series)
        assert all(type(day) is date for day in dates)
        assert list(dates) == sorted(set(dates))
        assert dates == tuple(sorted({d(n) for n in (17, 3, 9, 0, 12, -40)}))

    def test_stable_across_reads(self):
        series = AssetPriceSeries([_market(1), _trade(2)])
        assert _observation_dates(series) == _observation_dates(series) == (d(1), d(2))

    def test_agrees_with_resolve(self):
        """``resolve()`` unchanged: an observation day is exact, every other day is carried (or missing before the first)."""
        series = AssetPriceSeries([_market(2), _trade(5), _trade(5, "13"), _market(9), _trade(9, "99")])
        dates = _observation_dates(series)
        assert dates == (d(2), d(5), d(9))
        for n in range(0, 13):
            mark = series.resolve(d(n))
            if d(n) in dates:
                assert mark.source in (MarkSource.MARKET, MarkSource.TRADE_AVG)
                assert mark.as_of_date == d(n)
            elif d(n) < dates[0]:
                assert mark.source is MarkSource.MISSING
            else:
                assert mark.source is MarkSource.CARRIED
                assert mark.as_of_date == max(day for day in dates if day < d(n))
        assert series.resolve(d(5)).source is MarkSource.TRADE_AVG
        assert series.resolve(d(9)).source is MarkSource.MARKET


class TestObservationDatesThroughTheBuilder:
    def _build(self, price_rows, transactions, split_linked=frozenset()):
        return build_asset_price_series(price_rows=price_rows, transactions=transactions, split_linked_tx_ids=set(split_linked), asset_currency="EUR", quote_base_quantity=1)

    def test_empty(self):
        assert _observation_dates(self._build([], [])) == ()

    def test_market_rows_only_skipping_a_none_close(self):
        series = self._build([(d(5), D("11"), "EUR"), (d(1), None, "EUR"), (d(2), D("10"), "EUR")], [])
        assert _observation_dates(series) == (d(2), d(5))

    def test_trades_only(self):
        txs = [_tx(1, TransactionType.BUY, 4, "2", "-20"), _tx(2, TransactionType.SELL, 7, "-1", "11"), _tx(3, TransactionType.BUY, 4, "1", "-12")]
        assert _observation_dates(self._build([], txs)) == (d(4), d(7))

    def test_mixed_same_day_and_rows_that_are_not_observations(self):
        txs = [
            _tx(1, TransactionType.BUY, 2, "1", "-10"),  # same day as a quote: one day
            _tx(2, TransactionType.BUY, 4, "2", "-21"),  # trade-only day
            _tx(3, TransactionType.SELL, 4, "-1", "11"),  # same trade-only day
            _tx(4, TransactionType.ADJUSTMENT, 6, "1", "-10"),  # never a price
            _tx(5, TransactionType.BUY, 7, "1", "-10"),  # split-linked: skipped
            _tx(6, TransactionType.BUY, 8, "0", "-10"),  # zero quantity: skipped
            _tx(7, TransactionType.BUY, 10, "1", "0"),  # zero amount: skipped
        ]
        prices = [(d(2), D("10"), "EUR"), (d(5), D("11"), "EUR"), (d(1), None, "EUR")]
        series = self._build(prices, txs, split_linked={5})
        assert _observation_dates(series) == (d(2), d(4), d(5))
        assert series.resolve(d(4)).source is MarkSource.TRADE_AVG
        assert series.resolve(d(6)).source is MarkSource.CARRIED

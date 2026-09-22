"""Unit tests for backend/app/services/price_resolver.py.

The pure calculator (:class:`AssetPriceSeries`) is tested in isolation with hand-built
observations — no DB, no FX, no async. :func:`build_asset_price_series` is tested with
lightweight transaction stand-ins (attribute-only, no SQLModel) since the builder only
reads attributes.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.price_resolver import (
    AssetPriceSeries,
    MarkSource,
    ObservationKind,
    PriceObservation,
    build_asset_price_series,
)


def _d(value: str) -> Decimal:
    return Decimal(value)


def _market(day: str, price: str, currency: str = "EUR") -> PriceObservation:
    return PriceObservation(date=date.fromisoformat(day), unit_price=_d(price), currency=currency, kind=ObservationKind.MARKET)


def _trade(day: str, price: str, currency: str = "EUR") -> PriceObservation:
    return PriceObservation(date=date.fromisoformat(day), unit_price=_d(price), currency=currency, kind=ObservationKind.TRADE)


# --------------------------------------------------------------------------- #
# AssetPriceSeries — pure daily model
# --------------------------------------------------------------------------- #


def test_empty_series_resolves_missing():
    series = AssetPriceSeries([])
    mark = series.resolve(date(2025, 1, 1))
    assert mark.is_missing
    assert mark.source is MarkSource.MISSING
    assert mark.as_of_date is None
    assert mark.price_backward_fill is None
    assert not series.has_observations


def test_before_first_observation_is_missing():
    series = AssetPriceSeries([_market("2025-01-10", "100")])
    mark = series.resolve(date(2025, 1, 5))
    assert mark.is_missing


def test_market_exact_day_wins():
    series = AssetPriceSeries([_market("2025-01-10", "100")])
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("100")
    assert mark.as_of_date == date(2025, 1, 10)
    assert mark.price_backward_fill is None
    assert mark.estimated is False


def test_trade_average_same_day():
    series = AssetPriceSeries([_trade("2025-01-10", "100"), _trade("2025-01-10", "104"), _trade("2025-01-10", "106")])
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.TRADE_AVG
    assert mark.unit_price == (_d("100") + _d("104") + _d("106")) / _d("3")
    assert mark.estimated is True
    assert mark.price_backward_fill is None


def test_market_wins_tie_over_same_day_trade():
    series = AssetPriceSeries([_trade("2025-01-10", "90"), _market("2025-01-10", "100")])
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("100")
    assert mark.estimated is False


def test_locf_carries_market_forward_stale_not_estimated():
    series = AssetPriceSeries([_market("2025-01-10", "100")])
    mark = series.resolve(date(2025, 1, 15))
    assert mark.source is MarkSource.CARRIED
    assert mark.unit_price == _d("100")
    assert mark.as_of_date == date(2025, 1, 10)
    assert mark.price_backward_fill is not None
    assert mark.price_backward_fill.actual_rate_date == date(2025, 1, 10)
    assert mark.price_backward_fill.days_back == 5
    # A real quote carried forward is stale but NOT estimated.
    assert mark.estimated is False


def test_locf_carries_trade_forward_estimated():
    series = AssetPriceSeries([_trade("2025-01-10", "100")])
    mark = series.resolve(date(2025, 1, 12))
    assert mark.source is MarkSource.CARRIED
    assert mark.unit_price == _d("100")
    assert mark.price_backward_fill.days_back == 2
    # A trade carried forward is estimated.
    assert mark.estimated is True


def test_more_recent_real_quote_wins_over_older_trade():
    # trade on 01-10, real quote on 01-12 -> query 01-13 carries the real quote (newer).
    series = AssetPriceSeries([_trade("2025-01-10", "90"), _market("2025-01-12", "100")])
    mark = series.resolve(date(2025, 1, 13))
    assert mark.source is MarkSource.CARRIED
    assert mark.unit_price == _d("100")
    assert mark.as_of_date == date(2025, 1, 12)
    assert mark.estimated is False


def test_more_recent_trade_fills_gap_after_old_quote():
    # real quote on 01-10, later trade on 01-14 -> query 01-15 carries the trade (newer).
    series = AssetPriceSeries([_market("2025-01-10", "100"), _trade("2025-01-14", "130")])
    mark = series.resolve(date(2025, 1, 15))
    assert mark.source is MarkSource.CARRIED
    assert mark.unit_price == _d("130")
    assert mark.as_of_date == date(2025, 1, 14)
    assert mark.estimated is True
    assert mark.price_backward_fill.days_back == 1


def test_latest_returns_most_recent_exact():
    series = AssetPriceSeries([_market("2025-01-10", "100"), _trade("2025-01-14", "130")])
    latest = series.latest()
    assert latest.source is MarkSource.TRADE_AVG
    assert latest.unit_price == _d("130")
    assert latest.as_of_date == date(2025, 1, 14)
    assert latest.price_backward_fill is None


def test_latest_empty_is_missing():
    assert AssetPriceSeries([]).latest().is_missing


# --------------------------------------------------------------------------- #
# build_asset_price_series — normalization (currency/scale)
# --------------------------------------------------------------------------- #


def _tx(tx_id, tx_type, *, day, quantity="0", amount="0", cost_basis_override=None, cost_basis_currency=None, currency="EUR"):
    return SimpleNamespace(
        id=tx_id,
        type=tx_type,
        date=date.fromisoformat(day),
        quantity=_d(quantity),
        amount=_d(amount) if amount is not None else None,
        cost_basis_override=_d(cost_basis_override) if cost_basis_override is not None else None,
        cost_basis_currency=cost_basis_currency,
        currency=currency,
    )


def test_build_market_close_not_rescaled_by_qbq():
    # price_history.close is already per quote_base_quantity -> no ×qbq; kept native.
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("101.5"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=100,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("101.5")
    assert mark.currency == "EUR"


def test_build_trade_unit_price_scaled_by_qbq():
    # BUY 10 units for 1000 -> unit 100/unit; ×qbq(100) -> 10000 on market par axis.
    buy = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[buy],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=100,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.TRADE_AVG
    assert mark.unit_price == _d("10000")
    assert mark.currency == "EUR"


def test_build_sell_produces_trade_observation():
    sell = _tx(1, "SELL", day="2025-01-10", quantity="-5", amount="650")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[sell],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
    )
    mark = series.resolve(date(2025, 1, 10))
    # 650 / 5 = 130 per unit; qbq=1 -> 130.
    assert mark.unit_price == _d("130")
    assert mark.estimated is True


def test_build_priced_adjustment_observation():
    adj = _tx(1, "ADJUSTMENT", day="2025-01-10", quantity="20", cost_basis_override="5.16", cost_basis_currency="EUR")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[adj],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.unit_price == _d("5.16")


def test_build_skips_split_linked_and_zero_qty_and_unpriced_adjustment():
    split = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000")
    zero = _tx(2, "BUY", day="2025-01-11", quantity="0", amount="1000")
    qty_only_adj = _tx(3, "ADJUSTMENT", day="2025-01-12", quantity="5", cost_basis_override=None)
    series = build_asset_price_series(
        price_rows=[],
        transactions=[split, zero, qty_only_adj],
        split_linked_tx_ids={1},
        asset_currency="EUR",
        quote_base_quantity=1,
    )
    assert not series.has_observations


def test_build_keeps_trade_in_its_native_currency():
    # A foreign-currency trade stays native (no FX here); the mark carries its currency so the
    # engine can convert at the valuation date.
    buy = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000", currency="USD")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[buy],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.unit_price == _d("100")
    assert mark.currency == "USD"


# --------------------------------------------------------------------------- #
# G1b — synthetic P&L candles: OHLC observation/resolution semantics
# --------------------------------------------------------------------------- #
#
# The full engine-level candle *composition* (DailyStateBuilder / PnlCandleContribution)
# lives in test_portfolio_engine/test_pnl_candles.py. These tests cover only the resolver's
# own contract: when a resolved mark carries open/high/low, and when it must not.


def test_market_full_ohlc_triple_resolves_on_exact_day():
    obs = PriceObservation(date=date(2025, 1, 10), unit_price=_d("108"), currency="EUR", kind=ObservationKind.MARKET, open=_d("105"), high=_d("110"), low=_d("102"))
    mark = AssetPriceSeries([obs]).resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("108")
    assert (mark.open, mark.high, mark.low) == (_d("105"), _d("110"), _d("102"))


def test_build_day_missing_from_ohlc_by_date_has_no_ohlc():
    # 01-10 has an ohlc_by_date entry; 01-11 is a real MARKET day too but omitted from
    # ohlc_by_date on purpose -> it must resolve with no OHLC, never a guess.
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("108"), "EUR"), (date(2025, 1, 11), _d("109"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        ohlc_by_date={date(2025, 1, 10): (_d("105"), _d("110"), _d("102"))},
    )
    day10 = series.resolve(date(2025, 1, 10))
    assert (day10.open, day10.high, day10.low) == (_d("105"), _d("110"), _d("102"))
    day11 = series.resolve(date(2025, 1, 11))
    assert day11.source is MarkSource.MARKET
    assert (day11.open, day11.high, day11.low) == (None, None, None)


def test_build_ohlc_by_date_omitted_entirely_has_no_ohlc():
    # ohlc_by_date not passed at all (default None) -> every MARKET day still resolves,
    # just with no intraday range (additive parameter, must never be required).
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("108"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("108")
    assert (mark.open, mark.high, mark.low) == (None, None, None)


def test_carried_day_never_reports_ohlc_even_if_origin_day_had_it():
    # The origin day (01-10) has a full OHLC triple; carrying it forward to 01-15 must
    # drop the range entirely (no intraday variance is known for a day nothing traded on)
    # — the flat fallback belongs to the consuming engine, never a frozen prior range here.
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("108"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        ohlc_by_date={date(2025, 1, 10): (_d("105"), _d("110"), _d("102"))},
    )
    exact = series.resolve(date(2025, 1, 10))
    assert (exact.open, exact.high, exact.low) == (_d("105"), _d("110"), _d("102"))

    carried = series.resolve(date(2025, 1, 15))
    assert carried.source is MarkSource.CARRIED
    assert carried.unit_price == _d("108")  # the price itself is still carried
    assert (carried.open, carried.high, carried.low) == (None, None, None)


def test_trade_avg_observation_never_has_ohlc_even_with_matching_ohlc_by_date_entry():
    # No price_history row on 01-10 (only a trade) -> ohlc_by_date is keyed by MARKET days
    # from price_rows only, so an entry for the trade's own date must never leak into its
    # TRADE_AVG mark, regardless of it being present in the dict.
    buy = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[buy],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        ohlc_by_date={date(2025, 1, 10): (_d("95"), _d("105"), _d("90"))},
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.TRADE_AVG
    assert (mark.open, mark.high, mark.low) == (None, None, None)


def test_partial_ohlc_observation_is_treated_as_no_ohlc():
    # open+high present, low missing -> AssetPriceSeries must drop the WHOLE triple, never
    # guess the missing extremum or emit a partially-filled ResolvedMark. Exercised directly
    # at the PriceObservation/AssetPriceSeries layer (below the build_asset_price_series
    # normalization), matching the docstring contract verbatim.
    obs = PriceObservation(date=date(2025, 1, 10), unit_price=_d("108"), currency="EUR", kind=ObservationKind.MARKET, open=_d("105"), high=_d("110"), low=None)
    mark = AssetPriceSeries([obs]).resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("108")  # the close itself is unaffected by the dropped range
    assert (mark.open, mark.high, mark.low) == (None, None, None)


def test_build_partial_ohlc_by_date_entry_is_treated_as_no_ohlc():
    # Same guarantee through the full build_asset_price_series pipeline.
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("108"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        ohlc_by_date={date(2025, 1, 10): (_d("105"), _d("110"), None)},
    )
    mark = series.resolve(date(2025, 1, 10))
    assert (mark.open, mark.high, mark.low) == (None, None, None)

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


def _market(day: str, price: str) -> PriceObservation:
    return PriceObservation(date=date.fromisoformat(day), unit_price=_d(price), kind=ObservationKind.MARKET)


def _trade(day: str, price: str) -> PriceObservation:
    return PriceObservation(date=date.fromisoformat(day), unit_price=_d(price), kind=ObservationKind.TRADE)


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


def _identity_convert(amount, currency, on_date):
    return amount


def test_build_market_close_not_rescaled_by_qbq():
    # price_history.close is already per quote_base_quantity -> convert only, no ×qbq.
    series = build_asset_price_series(
        price_rows=[(date(2025, 1, 10), _d("101.5"), "EUR")],
        transactions=[],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=100,
        convert=_identity_convert,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.MARKET
    assert mark.unit_price == _d("101.5")


def test_build_trade_unit_price_scaled_by_qbq():
    # BUY 10 units for 1000 -> unit 100/unit; ×qbq(100) -> 10000 on market par axis.
    buy = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[buy],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=100,
        convert=_identity_convert,
    )
    mark = series.resolve(date(2025, 1, 10))
    assert mark.source is MarkSource.TRADE_AVG
    assert mark.unit_price == _d("10000")


def test_build_sell_produces_trade_observation():
    sell = _tx(1, "SELL", day="2025-01-10", quantity="-5", amount="650")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[sell],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        convert=_identity_convert,
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
        convert=_identity_convert,
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
        convert=_identity_convert,
    )
    assert not series.has_observations


def test_build_convert_none_falls_back_to_unconverted_trade():
    def _no_fx(amount, currency, on_date):
        return None

    buy = _tx(1, "BUY", day="2025-01-10", quantity="10", amount="1000", currency="USD")
    series = build_asset_price_series(
        price_rows=[],
        transactions=[buy],
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
        convert=_no_fx,
    )
    mark = series.resolve(date(2025, 1, 10))
    # Falls back to the raw unit price (100) when FX is unavailable.
    assert mark.unit_price == _d("100")

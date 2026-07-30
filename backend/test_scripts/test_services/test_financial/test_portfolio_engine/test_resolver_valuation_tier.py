"""F2: price-less valuation routed through the unified price resolver (``LAST_TRADE_PRICE``).

When the ``LIBREFOLIO_RESOLVER_VALUATION`` flag is on, an asset with no asset-system quote
on/before a day is valued from the resolver's observed-trade mark (BUY/SELL/priced ADJUSTMENT,
same-day average, LOCF carry with staleness) — the SAME unified source the FIFO price line
already consumes — instead of the legacy ``LAST_BUY_PRICE`` / ``LAST_SEED_COST`` tiers.

The flag defaults OFF (mark_series empty) so the historical cascade and every golden test are
unchanged; these tests exercise the ON path by injecting a ``mark_series`` directly into the
pure builder (mirroring what ``PortfolioCalculationEngine.calculate`` does under the flag).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import DailyStateBuilder, ValuationSource, _resolver_valuation_enabled
from backend.app.services.price_resolver import build_asset_price_series

_ASSET = 100


def _tx(*, id: int, type: str, dt: str, amount: str | None = None, currency: str = "EUR", quantity: str = "0", cost_basis_override: str | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.type = TransactionType(type)
    tx.date = date.fromisoformat(dt)
    tx.amount = Decimal(amount) if amount is not None else None
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = currency
    return tx


def _identity(amount: Decimal, currency: str | None, on_date: date) -> Decimal:
    return amount


def _series(txs, *, qbq: int = 1):
    return build_asset_price_series(
        price_rows=[],
        transactions=txs,
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=qbq,
        convert=_identity,
    )


def _builder(*, mark_series=None, last_buy_prices=None, quote_base_map=None) -> DailyStateBuilder:
    return DailyStateBuilder(
        classified_txs=[],
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map={},  # no asset-system quotes → MARKET tier always misses
        quote_base_map=quote_base_map or {},
        fx_rate_map={},
        asset_classifications={},
        asset_types={},
        asset_currencies={_ASSET: "EUR"},
        target_currency="EUR",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
        last_buy_prices=last_buy_prices,
        mark_series=mark_series,
    )


def test_flag_reads_environment(monkeypatch) -> None:
    monkeypatch.delenv("LIBREFOLIO_RESOLVER_VALUATION", raising=False)
    assert _resolver_valuation_enabled() is False
    for on in ("1", "true", "YES", "On"):
        monkeypatch.setenv("LIBREFOLIO_RESOLVER_VALUATION", on)
        assert _resolver_valuation_enabled() is True
    for off in ("", "0", "false", "no"):
        monkeypatch.setenv("LIBREFOLIO_RESOLVER_VALUATION", off)
        assert _resolver_valuation_enabled() is False


def test_priceless_asset_valued_as_last_trade_price() -> None:
    series = _series([_tx(id=1, type="BUY", dt="2024-03-01", amount="500", quantity="100")])
    builder = _builder(mark_series={_ASSET: series})

    valuation = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 3, 1))

    assert valuation.source is ValuationSource.LAST_TRADE_PRICE
    assert valuation.effective_currency == "EUR"
    # BUY unit price = 500/100 = 5.00 → holding value = 100 * 5.00
    assert valuation.market_value == Decimal("500")
    assert valuation.effective_unit_price == Decimal("5")
    assert valuation.stale is False


def test_sell_observation_marks_position_where_last_buy_would_miss() -> None:
    # A SELL is a real market observation the legacy LAST_BUY tier ignores. The resolver ingests it.
    series = _series([_tx(id=2, type="SELL", dt="2024-05-10", amount="660", quantity="60")])
    builder = _builder(mark_series={_ASSET: series})

    valuation = builder._market_value_for(_ASSET, Decimal("40"), date(2024, 5, 10))

    assert valuation.source is ValuationSource.LAST_TRADE_PRICE
    # SELL unit price = 660/60 = 11.00 → residual 40 units * 11.00 = 440
    assert valuation.market_value == Decimal("440")


def test_carried_mark_flagged_stale_after_threshold() -> None:
    series = _series([_tx(id=3, type="BUY", dt="2024-03-01", amount="500", quantity="100")])
    builder = _builder(mark_series={_ASSET: series})

    fresh = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 3, 6))  # 5 days back ≤ 7
    stale = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 3, 20))  # 19 days back > 7

    assert fresh.source is ValuationSource.LAST_TRADE_PRICE and fresh.stale is False
    assert stale.source is ValuationSource.LAST_TRADE_PRICE and stale.stale is True
    # Value is carried forward unchanged (LOCF).
    assert stale.market_value == Decimal("500")


def test_resolver_mark_supersedes_last_buy_price() -> None:
    # Both present: resolver (SELL 12.0) must win over the legacy last-buy reference (5.0).
    series = _series([_tx(id=4, type="SELL", dt="2024-06-01", amount="1200", quantity="100")])
    builder = _builder(
        mark_series={_ASSET: series},
        last_buy_prices={_ASSET: [(date(2024, 1, 1), Decimal("5"), "EUR")]},
    )

    valuation = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 6, 1))

    assert valuation.source is ValuationSource.LAST_TRADE_PRICE
    assert valuation.effective_unit_price == Decimal("12")


def test_flag_off_falls_back_to_legacy_cascade() -> None:
    # No mark_series (flag OFF) → the legacy LAST_BUY_PRICE tier is used, proving zero change by default.
    builder = _builder(last_buy_prices={_ASSET: [(date(2024, 1, 1), Decimal("5"), "EUR")]})

    valuation = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 6, 1))

    assert valuation.source is ValuationSource.LAST_BUY_PRICE
    assert valuation.effective_unit_price == Decimal("5")


def test_bond_quote_base_scale_preserved() -> None:
    # qbq=100 bond: BUY 95.0 per unit → resolver lifts to par axis; holding value stays qty*price.
    series = _series([_tx(id=5, type="BUY", dt="2024-04-01", amount="9500", quantity="100")], qbq=100)
    builder = _builder(mark_series={_ASSET: series}, quote_base_map={_ASSET: 100})

    valuation = builder._market_value_for(_ASSET, Decimal("100"), date(2024, 4, 1))

    assert valuation.source is ValuationSource.LAST_TRADE_PRICE
    # unit price 95.0 → mark on par axis = 9500 (95*100); holding = (100/100)*9500 = 9500
    assert valuation.market_value == Decimal("9500")
    assert valuation.effective_unit_price == Decimal("9500")

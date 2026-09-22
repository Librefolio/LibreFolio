"""Regression tests for G1b — synthetic total-P&L candles (plan §4.3).

Mandatory invariant under test, verbatim: "Daily total candle close must equal
canonical total P&L exactly." Concretely, for EVERY emitted DailyPortfolioState with a
non-None ``pnl_candle``:

    state.pnl_candle.close == state.total_pnl

Also covers:
- The composition formula (offset = total_pnl - sum(asset_close); {open,high,low} =
  offset + sum(asset_{open,high,low})) against a hand-verified golden scenario.
- ``compute_ohlc=False`` (the default) on ``_market_value_for`` never populates the new
  ``market_value_*`` fields, even when the underlying mark has a full OHLC triple — the
  "ordinary reports pay nothing extra" contract (plan §4.1).
- A MISSING held-asset valuation gates the WHOLE day's candle to None, mirroring
  ``nav_complete``, even when every other held asset resolves fine that day.
- The day-skip ("stationary day") fast path reuses the previous day's ``pnl_candle``
  object verbatim rather than recomputing it.
- The ``qty <= 0`` guard (already used by every other per-asset loop in this engine) is
  reused as-is for candle accumulation — a short/negative position simply does not
  contribute, no special-case crash or wrong value.
- ``DerivedViewsBuilder.build_pnl_candles()``: shape, the close/total_pnl invariant, and
  that a day with no candle is OMITTED (a real gap), never zeroed.
- ``PortfolioService.get_pnl_candles()``: slicing to [date_from, date_to] via
  ``_precomputed_engine_result`` — pure, no DB (mirrors ``get_broker_pnl_history()``).
- The L1 blob cache (``PortfolioCalculationEngine.calculate``) and L2 report cache
  (``PortfolioService.get_report``) keys both include their respective candle flags
  (``include_candles`` / ``query.include_pnl_candles``), so a blob/report computed
  without candles is never silently reused for a request that asked for them.

Pure tests (no DB, no async) mirror the conventions in test_cash_decomposition.py /
test_broker_pnl_contributions.py / test_daily_state_builder.py in this directory. The
two cache-key tests are real DB integration tests (real AsyncSession against the test
database, no HTTP server), mirroring TestPortfolioBlobCacheFxSensitivity in
test_financial/test_portfolio_service.py — the closest existing precedent for this
exact class of cache-key regression.
"""

import sys
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.portfolio_engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.schemas.portfolio import PnlCandleSeries, PortfolioReportQuery
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyPortfolioState,
    DailyStateBuilder,
    DerivedViewsBuilder,
    PortfolioCalculationResult,
    ValuationSource,
)
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.price_resolver import build_asset_price_series
from backend.app.utils.datetime_utils import utcnow

# =============================================================================
# HELPERS — mirror the established conventions in this test directory
# =============================================================================


def _d(value: str) -> Decimal:
    return Decimal(value)


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


def _mark_series_from(classified_txs, price_map, asset_currencies, quote_base_map=None, split_linked_tx_ids=None, ohlc_by_date=None):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades.

    ``ohlc_by_date``, if given, is ``{asset_id: {market_date: (open, high, low)}}`` — the
    per-asset G1b slice PortfolioCalculationEngine.calculate() builds from PriceHistory rows.
    """
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
            ohlc_by_date=(ohlc_by_date or {}).get(aid),
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg.

    ``ohlc_by_date`` is accepted (and popped) here even though it is not a
    DailyStateBuilder constructor kwarg — it is only consumed by ``_mark_series_from``
    to build ``mark_series``, mirroring how PortfolioCalculationEngine.calculate() feeds
    ``build_asset_price_series(..., ohlc_by_date=...)`` per asset.
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
        "date_to": date(2025, 1, 1),
    }
    ohlc_by_date = overrides.pop("ohlc_by_date", None)
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
            defaults.get("split_linked_tx_ids"),
            ohlc_by_date,
        )
    return DailyStateBuilder(**defaults)


def _assert_close_equals_total_pnl(state: DailyPortfolioState) -> None:
    """Plan §4.3 mandatory invariant: a non-None candle's close is EXACTLY total_pnl."""
    if state.pnl_candle is None:
        return
    assert state.pnl_candle.close == state.total_pnl, f"{state.date}: pnl_candle.close={state.pnl_candle.close} != total_pnl={state.total_pnl}"


def _assert_invariant_every_day(states: list[DailyPortfolioState]) -> None:
    for s in states:
        _assert_close_equals_total_pnl(s)


# =============================================================================
# GOLDEN SCENARIO (hand-verified) — single asset, one real OHLC day
# =============================================================================
#
# Broker 10: DEPOSIT 1000 (2025-01-01), BUY 10 units @ 100 (asset 100, same day — no
# price_history row exists yet, so the mark resolves via TRADE_AVG from the BUY itself,
# which has NO OHLC -> flat fallback). price_history for asset 100: exactly one row,
# (2025-01-02, close=108, EUR), with ohlc_by_date {2025-01-02: (open=105, high=110, low=102)}.
#
# Day 2025-01-01 (BUY day, TRADE_AVG mark, no OHLC -> flat fallback):
#   market_value = 10*100 = 1000 (flat), cash = 1000 (dep) - 1000 (buy) = 0, nav = 1000,
#   capital_baseline = 1000, total_pnl = 0. candle = (open=0, high=0, low=0, close=0).
#
# Day 2025-01-02 (real MARKET day with OHLC):
#   market_value = 10*108 = 1080 (close), open=10*105=1050, high=10*110=1100, low=10*102=1020.
#   cash stays 0 (no new tx), nav = 1080, capital_baseline = 1000 (unchanged), total_pnl = 80.
#   offset = total_pnl - candle_close_sum = 80 - 1080 = -1000 (same offset as day 1: cash and
#   capital_baseline are unchanged between the two days, a useful cross-check).
#   candle = (open=-1000+1050=50, high=-1000+1100=100, low=-1000+1020=20, close=80).

_GOLDEN_PRICE_MAP = {100: [(date(2025, 1, 2), _d("108"), "EUR")]}
_GOLDEN_OHLC_BY_DATE = {100: {date(2025, 1, 2): (_d("105"), _d("110"), _d("102"))}}
_GOLDEN_ECF = [(date(2025, 1, 1), 10, _d("1000"), "EUR")]


def _golden_txs() -> list[ClassifiedTransaction]:
    return [
        _ctxn(_tx(id=1, broker_id=10, type="DEPOSIT", dt="2025-01-01", amount="1000")),
        _ctxn(_tx(id=2, broker_id=10, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=100)),
    ]


def _golden_result() -> PortfolioCalculationResult:
    builder = _builder(
        classified_txs=_golden_txs(),
        external_cash_flows=_GOLDEN_ECF,
        price_map=_GOLDEN_PRICE_MAP,
        ohlc_by_date=_GOLDEN_OHLC_BY_DATE,
        asset_currencies={100: "EUR"},
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 2),
        compute_candles=True,
    )
    return builder.build()


class TestGoldenScenario:
    """DEPOSIT 1000, BUY 10u@100 (no price yet -> TRADE_AVG/flat), then a real MARKET
    day with a full OHLC triple. Hand-verified numbers, see module-level comment above.
    """

    def test_day_one_buy_day_flat_fallback_zero_pnl(self):
        result = _golden_result()
        day1 = result.daily_states[0]
        assert day1.date == date(2025, 1, 1)

        assert day1.total_pnl == _d("0")
        assert day1.pnl_candle is not None
        assert day1.pnl_candle.open == _d("0")
        assert day1.pnl_candle.high == _d("0")
        assert day1.pnl_candle.low == _d("0")
        assert day1.pnl_candle.close == _d("0")
        _assert_close_equals_total_pnl(day1)

    def test_day_two_real_ohlc_day_matches_hand_verified_numbers(self):
        result = _golden_result()
        day2 = result.daily_states[1]
        assert day2.date == date(2025, 1, 2)

        assert day2.market_value == _d("1080")
        assert day2.nav_value == _d("1080")
        assert day2.cumulative_external_cash_flow == _d("1000")
        assert day2.total_pnl == _d("80")

        assert day2.pnl_candle is not None
        assert day2.pnl_candle.open == _d("50")
        assert day2.pnl_candle.high == _d("100")
        assert day2.pnl_candle.low == _d("20")
        assert day2.pnl_candle.close == _d("80")
        _assert_close_equals_total_pnl(day2)

    def test_offset_is_identical_both_days(self):
        """Sanity cross-check called out by the golden scenario: cash and
        capital_baseline are unchanged between the two days, so the composition
        offset (total_pnl - candle_close_sum, i.e. total_pnl - market_value for this
        single-asset scope) must be the same -1000 on both.
        """
        result = _golden_result()
        day1, day2 = result.daily_states
        offset1 = day1.total_pnl - day1.market_value
        offset2 = day2.total_pnl - day2.market_value
        assert offset1 == offset2 == _d("-1000")

    def test_invariant_holds_on_every_emitted_day(self):
        result = _golden_result()
        assert len(result.daily_states) == 2
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# compute_ohlc=False (default) never populates market_value_open/high/low
# =============================================================================


class TestComputeOhlcDefaultOff:
    """``_market_value_for``'s compute_ohlc kwarg defaults to False and must never
    populate market_value_open/high/low even when the resolved mark DOES carry a full
    OHLC triple — the "ordinary reports pay nothing extra" contract (plan §4.1).
    """

    def _series(self):
        return build_asset_price_series(
            price_rows=[(date(2025, 1, 2), _d("108"), "EUR")],
            transactions=[],
            split_linked_tx_ids=set(),
            asset_currency="EUR",
            quote_base_quantity=1,
            ohlc_by_date={date(2025, 1, 2): (_d("105"), _d("110"), _d("102"))},
        )

    def test_default_call_leaves_ohlc_fields_none(self):
        builder = _builder(
            mark_series={100: self._series()},
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(asset_id=100, qty=Decimal("10"), dt=date(2025, 1, 2))

        assert valuation.market_value == _d("1080")
        assert valuation.source == ValuationSource.MARKET_PRICE
        assert valuation.market_value_open is None
        assert valuation.market_value_high is None
        assert valuation.market_value_low is None

    def test_explicit_compute_ohlc_true_populates_the_same_mark(self):
        """Same builder, same mark, same day — only the kwarg differs. Proves the
        None above is the default's absence, not an unrelated setup gap.
        """
        builder = _builder(
            mark_series={100: self._series()},
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(asset_id=100, qty=Decimal("10"), dt=date(2025, 1, 2), compute_ohlc=True)

        assert valuation.market_value_open == _d("1050")
        assert valuation.market_value_high == _d("1100")
        assert valuation.market_value_low == _d("1020")

    def test_default_false_also_holds_through_the_full_daily_builder(self):
        """End-to-end: compute_candles=False (DailyStateBuilder default) must produce
        None pnl_candle for every day, and the per-asset OHLC fields must stay closed
        off even though the same price data would resolve a full triple.
        """
        result = _builder(
            classified_txs=_golden_txs(),
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            ohlc_by_date=_GOLDEN_OHLC_BY_DATE,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            # compute_candles omitted -> defaults to False
        ).build()

        for state in result.daily_states:
            assert state.pnl_candle is None
        # The underlying valuation still resolves normally (market_value unaffected).
        assert result.daily_states[1].market_value == _d("1080")


# =============================================================================
# Foreign-currency OHLC: same FX conversion pipeline as market_value
# =============================================================================


class TestComputeOhlcForeignCurrencyUsesSameFxRate:
    """When the asset's native currency differs from target_currency, open/high/low
    must be converted through the exact same per-day FX rate as market_value — not
    left native, not converted at the observation date instead of the valuation date.
    """

    def test_foreign_ohlc_converted_with_same_rate_as_market_value(self):
        series = build_asset_price_series(
            price_rows=[(date(2025, 1, 2), _d("108"), "USD")],
            transactions=[],
            split_linked_tx_ids=set(),
            asset_currency="USD",
            quote_base_quantity=1,
            ohlc_by_date={date(2025, 1, 2): (_d("105"), _d("110"), _d("102"))},
        )
        builder = _builder(
            mark_series={100: series},
            asset_currencies={100: "USD"},
            fx_rate_map={("USD", "EUR", date(2025, 1, 2)): _d("0.8")},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(asset_id=100, qty=Decimal("10"), dt=date(2025, 1, 2), compute_ohlc=True)

        assert valuation.market_value == _d("864")  # 10 * 108 USD * 0.8 EUR/USD
        assert valuation.market_value_open == _d("840")  # 10 * 105 USD * 0.8
        assert valuation.market_value_high == _d("880")  # 10 * 110 USD * 0.8
        assert valuation.market_value_low == _d("816")  # 10 * 102 USD * 0.8

    def test_missing_fx_rate_leaves_ohlc_none_like_market_value(self):
        """No FX rate available for the valuation date -> market_value is None
        (missing_fx_pair reported); the OHLC fields must fail the same way, not
        silently report a native-currency (unconverted) number.
        """
        series = build_asset_price_series(
            price_rows=[(date(2025, 1, 2), _d("108"), "USD")],
            transactions=[],
            split_linked_tx_ids=set(),
            asset_currency="USD",
            quote_base_quantity=1,
            ohlc_by_date={date(2025, 1, 2): (_d("105"), _d("110"), _d("102"))},
        )
        builder = _builder(
            mark_series={100: series},
            asset_currencies={100: "USD"},
            fx_rate_map={},  # no USD/EUR rate at all
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )

        valuation = builder._market_value_for(asset_id=100, qty=Decimal("10"), dt=date(2025, 1, 2), compute_ohlc=True)

        assert valuation.market_value is None
        assert valuation.missing_fx_pair == "USD/EUR"
        assert valuation.market_value_open is None
        assert valuation.market_value_high is None
        assert valuation.market_value_low is None


# =============================================================================
# A MISSING held-asset valuation gates the WHOLE day's candle to None
# =============================================================================


class TestMissingAssetGatesWholeDayCandle:
    """Two held assets: asset 100 always resolves (TRADE_AVG from day 1 onward). Asset
    200 is acquired via an UNPRICED quantity-only ADJUSTMENT (no cost_basis_override) on
    day 2 -> it has zero observations ever until day 3's real price row lands. Day 2 must
    therefore have pnl_candle=None (mirrors nav_complete=False) even though asset 100's
    valuation is perfectly fine that day; day 1 (only asset 100 held) and day 3 (both
    resolve) must both have a non-None candle.
    """

    def _result(self) -> PortfolioCalculationResult:
        txs = [
            _ctxn(_tx(id=1, broker_id=10, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=100)),
            # Unpriced quantity-only ADJUSTMENT for asset 200: no cost_basis_override ->
            # build_asset_price_series skips it entirely (see test_price_resolver.py),
            # so asset 200 has NO observation until its price row on day 3.
            _ctxn(_tx(id=2, broker_id=10, type="ADJUSTMENT", dt="2025-01-02", quantity="5", asset_id=200)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={200: [(date(2025, 1, 3), _d("50"), "EUR")]},
            asset_currencies={100: "EUR", 200: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
            compute_candles=True,
        )
        return builder.build()

    def test_missing_day_has_no_candle_but_neighbours_do(self):
        result = self._result()
        states_by_date = {s.date: s for s in result.daily_states}

        day1 = states_by_date[date(2025, 1, 1)]
        day2 = states_by_date[date(2025, 1, 2)]
        day3 = states_by_date[date(2025, 1, 3)]

        assert 200 not in day1.missing_price_asset_ids  # asset 200 not held yet
        assert day1.pnl_candle is not None

        assert day2.nav_complete is False
        assert 200 in day2.missing_price_asset_ids
        assert day2.pnl_candle is None, "a MISSING held-asset valuation must gate the whole day's candle to None"

        assert day3.nav_complete is True
        assert day3.pnl_candle is not None

        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# Stationary-day reuse — the day-skip fast path
# =============================================================================


class TestStationaryDayReusesCandle:
    """A day with no tx/ecf/price change reuses the previous DailyPortfolioState
    verbatim (day-skip fast path in DailyStateBuilder.build()) — including
    pnl_candle, which the code assigns as `pnl_candle=prev.pnl_candle` (the SAME
    object reference, not a recomputed equal value).
    """

    def test_quiet_day_reuses_the_same_pnl_candle_object(self):
        txs = [
            _ctxn(_tx(id=1, broker_id=10, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), _d("100"), "EUR")]},
            ohlc_by_date={100: {date(2025, 1, 1): (_d("98"), _d("102"), _d("97"))}},
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),  # day 2: no tx, no ecf, no new price row -> stationary
            compute_candles=True,
        )
        result = builder.build()
        day1, day2 = result.daily_states
        assert day1.date == date(2025, 1, 1)
        assert day2.date == date(2025, 1, 2)

        assert day1.pnl_candle is not None
        assert day2.pnl_candle is day1.pnl_candle, "the stationary day must reuse the SAME pnl_candle object, not an equal recomputed one"


# =============================================================================
# Negative/short quantity is excluded from candle accumulation (guard reuse)
# =============================================================================


class TestNegativeQuantityExcludedFromCandle:
    """A SELL exceeding the tracked lot drives cumulative_qty negative. The existing
    `if qty <= 0: continue` guard (shared by market_value/allocation/etc.) must simply
    exclude that asset from candle_*_sum accumulation too — no special-case crash, no
    wrong value. This is not new negative-position support, just confirming the guard
    reuse didn't regress.
    """

    def test_short_position_day_excludes_asset_from_candle_but_stays_composable(self):
        txs = [
            _ctxn(_tx(id=1, broker_id=10, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, broker_id=10, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=100)),
            # SELL 15 > the 10 held -> cumulative_qty goes to -5.
            _ctxn(_tx(id=3, broker_id=10, type="SELL", dt="2025-01-02", amount="1500", quantity="-15", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), 10, _d("1000"), "EUR")]
        builder = _builder(
            classified_txs=txs,
            external_cash_flows=ecfs,
            price_map={100: [(date(2025, 1, 2), _d("100"), "EUR")]},
            ohlc_by_date={100: {date(2025, 1, 2): (_d("95"), _d("105"), _d("90"))}},
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_candles=True,
        )
        result = builder.build()
        day2 = result.daily_states[1]

        # The negative-qty asset must not appear as MISSING (it was never valued at
        # all — excluded upstream by the qty<=0 guard, same as market_value).
        assert 100 not in day2.missing_price_asset_ids
        assert day2.market_value == _d("0")
        assert day2.cash_value == _d("1500")  # 1000 dep - 1000 buy + 1500 sell
        assert day2.nav_value == _d("1500")
        assert day2.total_pnl == _d("500")

        # With zero held (qty>0) assets contributing, the candle degenerates to a
        # flat point at total_pnl exactly (no stray -500 contribution from the
        # excluded short position, which WOULD show up as a wrong non-flat value).
        assert day2.pnl_candle is not None
        assert day2.pnl_candle.open == _d("500")
        assert day2.pnl_candle.high == _d("500")
        assert day2.pnl_candle.low == _d("500")
        assert day2.pnl_candle.close == _d("500")
        _assert_close_equals_total_pnl(day2)


# =============================================================================
# DerivedViewsBuilder.build_pnl_candles()
# =============================================================================


class TestDerivedViewsBuilderPnlCandles:
    def test_shape_and_golden_values(self):
        result = _golden_result()
        points = DerivedViewsBuilder(result.daily_states, "EUR").build_pnl_candles()

        assert len(points) == 2
        for point in points:
            assert set(point.keys()) == {"date", "open", "high", "low", "close"}
            for field in ("open", "high", "low", "close"):
                assert isinstance(point[field], CurrencySchema)
                assert point[field].code == "EUR"

        by_date = {p["date"]: p for p in points}
        day1 = by_date[date(2025, 1, 1)]
        assert (day1["open"].amount, day1["high"].amount, day1["low"].amount, day1["close"].amount) == (_d("0"), _d("0"), _d("0"), _d("0"))
        day2 = by_date[date(2025, 1, 2)]
        assert (day2["open"].amount, day2["high"].amount, day2["low"].amount, day2["close"].amount) == (_d("50"), _d("100"), _d("20"), _d("80"))

    def test_close_reproduces_total_pnl_every_returned_day(self):
        result = _golden_result()
        states_by_date = {s.date: s for s in result.daily_states}
        points = DerivedViewsBuilder(result.daily_states, "EUR").build_pnl_candles()

        assert points  # sanity: the golden scenario has no gaps
        for point in points:
            assert point["close"].amount == states_by_date[point["date"]].total_pnl

    def test_missing_day_is_omitted_not_zeroed(self):
        """Reuses the MISSING-gating scenario above: day 2's candle is None, so
        build_pnl_candles() must OMIT it entirely (a real gap), never emit a zeroed
        or otherwise synthesized point for it.
        """
        txs = [
            _ctxn(_tx(id=1, broker_id=10, type="BUY", dt="2025-01-01", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=2, broker_id=10, type="ADJUSTMENT", dt="2025-01-02", quantity="5", asset_id=200)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={200: [(date(2025, 1, 3), _d("50"), "EUR")]},
            asset_currencies={100: "EUR", 200: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
            compute_candles=True,
        )
        result = builder.build()
        points = DerivedViewsBuilder(result.daily_states, "EUR").build_pnl_candles()

        assert {p["date"] for p in points} == {date(2025, 1, 1), date(2025, 1, 3)}, "the MISSING day (01-02) must be omitted entirely, never zeroed"


# =============================================================================
# PortfolioService.get_pnl_candles() — pure slicing (no DB)
# =============================================================================


class TestPortfolioServiceGetPnlCandlesPure:
    """get_pnl_candles() mirrors get_broker_pnl_history()'s _precomputed_engine_result
    pattern: with both that AND target_currency_override supplied, self.db is never
    touched, so this is exercisable purely (no DB, no HTTP server).
    """

    @pytest.mark.asyncio
    async def test_slices_to_date_range_and_matches_golden_values(self):
        result = _golden_result()
        service = PortfolioService(db=None)

        series = await service.get_pnl_candles(
            user_id=1,
            target_currency_override="EUR",
            date_from=date(2025, 1, 2),
            date_to=date(2025, 1, 2),
            _precomputed_engine_result=result,
        )

        assert isinstance(series, PnlCandleSeries)
        assert series.hypothetical is True
        assert [p.date for p in series.points] == [date(2025, 1, 2)]
        point = series.points[0]
        assert point.open.amount == _d("50")
        assert point.high.amount == _d("100")
        assert point.low.amount == _d("20")
        assert point.close.amount == _d("80")

    @pytest.mark.asyncio
    async def test_unbounded_range_returns_every_non_gap_day(self):
        result = _golden_result()
        service = PortfolioService(db=None)

        series = await service.get_pnl_candles(
            user_id=1,
            target_currency_override="EUR",
            _precomputed_engine_result=result,
        )

        assert [p.date for p in series.points] == [date(2025, 1, 1), date(2025, 1, 2)]

    @pytest.mark.asyncio
    async def test_empty_daily_states_returns_empty_series(self):
        service = PortfolioService(db=None)
        empty_result = PortfolioCalculationResult(daily_states=[])

        series = await service.get_pnl_candles(
            user_id=1,
            target_currency_override="EUR",
            _precomputed_engine_result=empty_result,
        )

        assert series.points == []


# =============================================================================
# L1 blob cache (PortfolioCalculationEngine.calculate) — include_candles key
# =============================================================================
#
# Real DB integration tests (AsyncSession against the test database, no HTTP server),
# mirroring TestPortfolioBlobCacheFxSensitivity in test_financial/test_portfolio_service.py.


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    user = User(
        username=f"pnlcandle_{utcnow().timestamp()}",
        email=f"pnlcandle_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_single_asset_portfolio(session, test_user, *, name_prefix: str, dep_date: date, price_date: date) -> Broker:
    """One broker, one asset, DEPOSIT 1000 + BUY 10@100 + a same-shape price row as the
    golden scenario (close=108, OHLC=105/110/102) — enough to make pnl_candle non-None
    when candles are requested.
    """
    broker = Broker(name=f"{name_prefix}_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    asset = Asset(display_name=f"{name_prefix}Asset_{utcnow().timestamp()}", currency="EUR", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    session.add_all(
        [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=dep_date, amount=Decimal("1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=dep_date, quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=price_date, open=Decimal("105"), high=Decimal("110"), low=Decimal("102"), close=Decimal("108"), currency="EUR", source_plugin_key="manual_test"),
        ]
    )
    await session.flush()
    return broker


class TestPortfolioBlobCacheIncludeCandlesSensitivity:
    """The L1 blob cache key (blob_key tuple in PortfolioCalculationEngine.calculate)
    now includes include_candles as its last element (G1b) — a blob computed for a
    plain report must never be reused for a candles request, and vice versa, or the
    wrong shape (missing/unwanted pnl_candle) would silently leak into the caller.
    """

    @pytest.mark.asyncio
    async def test_blob_cache_distinguishes_include_candles(self, session, test_user, monkeypatch):
        broker = await _seed_single_asset_portfolio(session, test_user, name_prefix="PnlCandleBlob", dep_date=date(2034, 1, 1), price_date=date(2034, 1, 2))
        portfolio_engine_module._portfolio_blob_cache.clear()

        build_calls = {"n": 0}
        original_build = portfolio_engine_module.DailyStateBuilder.build

        def counting_build(builder_self):
            build_calls["n"] += 1
            return original_build(builder_self)

        monkeypatch.setattr(portfolio_engine_module.DailyStateBuilder, "build", counting_build)

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)
        date_to = date(2034, 1, 2)

        result_false = await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR", include_candles=False)
        assert build_calls["n"] == 1
        assert result_false.daily_states[-1].pnl_candle is None

        # Same scope/date, include_candles=True -> must NOT reuse the False blob.
        result_true = await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR", include_candles=True)
        assert build_calls["n"] == 2, "include_candles=True reused the include_candles=False blob (L1 cache key missing the flag)"
        assert result_true.daily_states[-1].pnl_candle is not None
        assert result_true.daily_states[-1].pnl_candle.close == result_true.daily_states[-1].total_pnl == Decimal("80")

        # Re-requesting False must hit its OWN cached blob (still 2 builds total).
        result_false_again = await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR", include_candles=False)
        assert build_calls["n"] == 2, "re-requesting include_candles=False triggered a rebuild instead of hitting its own cached blob"
        assert result_false_again.daily_states[-1].pnl_candle is None

        # Re-requesting True must likewise hit its own cached blob (still 2 builds).
        result_true_again = await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR", include_candles=True)
        assert build_calls["n"] == 2, "re-requesting include_candles=True triggered a rebuild instead of hitting its own cached blob"
        assert result_true_again.daily_states[-1].pnl_candle is not None


# =============================================================================
# L2 report cache (PortfolioService.get_report) — include_pnl_candles key
# =============================================================================


class TestPortfolioL2CacheIncludesPnlCandlesFlag:
    """get_report()'s L2 report cache key (l2_key tuple) must include
    query.include_pnl_candles — same class of bug as the L1 blob key: without it, a
    report requested WITHOUT candles would satisfy a later request WITH candles from
    the stale L2 entry, silently dropping pnl_candles from the response.
    """

    @pytest.mark.asyncio
    async def test_l2_cache_distinguishes_include_pnl_candles(self, session, test_user):
        broker = await _seed_single_asset_portfolio(session, test_user, name_prefix="PnlCandleL2", dep_date=date(2034, 2, 1), price_date=date(2034, 2, 2))
        portfolio_service_module._portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()

        service = portfolio_service_module.PortfolioService(session)
        query_kwargs = {
            "broker_ids": [broker.id],
            "include_summary": False,
            "include_history": False,
            "include_allocation_history": False,
            "date_range": {"start": "2034-02-01", "end": "2034-02-02"},
        }

        report_false = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, include_pnl_candles=False))
        assert report_false.pnl_candles is None

        report_true = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, include_pnl_candles=True))
        assert report_true.pnl_candles is not None, "include_pnl_candles=True reused the include_pnl_candles=False L2 cache entry (L2 key missing the flag)"
        assert report_true.pnl_candles.points
        last_point = report_true.pnl_candles.points[-1]
        assert last_point.date == date(2034, 2, 2)
        assert last_point.close.amount == Decimal("80")

        report_false_again = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, include_pnl_candles=False))
        assert report_false_again.pnl_candles is None, "re-requesting include_pnl_candles=False picked up the include_pnl_candles=True L2 cache entry"

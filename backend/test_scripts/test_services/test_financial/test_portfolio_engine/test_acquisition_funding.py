"""Regression tests for batch 2 — new-vs-reinvested BUY funding split (plan §5.2).

Mandatory invariant under test, stated as the feature's own contract: for EVERY day
the engine emits an ``acquisition_funding`` contribution,

    from_new_capital + from_reinvested == that day's total BUY cash outflow
                                          (target currency, share-scaled)

exactly — not approximately, not as a residual. The split is NOT new business logic:
the BUY branch of ``DailyStateBuilder.build()`` already computed ``from_r`` (and, by
subtraction, ``amount_target - from_r``) to update the running 3-pool K/R balances;
batch 2 only captures those two numbers into a per-day accumulator instead of
discarding them. So the invariant holds *by construction*, and these tests lock that
construction in place rather than re-deriving arithmetic.

Also covered:

- The four funding regimes the coordinator called out explicitly: a BUY funded
  entirely from fresh capital (R pool empty), entirely from reinvested returns
  (R covers it), a genuinely mixed BUY (R partially covers it), and a no-BUY day
  (``acquisition_funding is None`` — a real gap, never a zero-valued object).
- ``compute_acquisition_funding=False`` (the default) never populates the field, even
  on a day with BUYs — the "extra output stays off ordinary reports" convention it
  shares with ``compute_candles``.
- The deliberate asymmetry vs ``pnl_candle`` on the stationary (day-skip) fast path:
  the reused-state branch carries ``pnl_candle=prev.pnl_candle`` forward but sets
  ``acquisition_funding=None``. That is CORRECT, and this file proves *why* rather
  than merely asserting it: a stationary day is by definition absent from
  ``dirty_days``, which is seeded from every transaction date, so it can never
  contain a BUY. A candle legitimately stays flat across a quiet day (it describes a
  standing position); an acquisition is an event, and no event happened.
- The PRE-FRAME loop's separate, deliberately untouched BUY branch: pre-frame days
  emit no ``DailyPortfolioState`` at all, so they can carry no funding split — but
  they must still draw down K/R correctly, because that drawn-down pool state is
  exactly what seeds the frame's first day.
- Non-BUY position activity (SELL, in-kind ADJUSTMENT-in) and an unpriceable BUY
  (missing FX route) never fabricate a contribution.
- ``DerivedViewsBuilder.build_acquisition_funding()``: shape, the sum invariant, and
  that a no-BUY day is OMITTED (mirrors ``build_pnl_candles``'s own gap convention).
- ``PortfolioService.get_acquisition_funding_history()``: the pure
  ``_precomputed_engine_result`` slicing mode (following
  ``TestPortfolioServiceGetPnlCandlesPure`` in test_pnl_candles.py verbatim), PLUS a
  real-DB parity check that the standalone mode returns the identical series — the
  half of the dual mode the pnl-candles precedent does not exercise.
- The L1 blob cache (``PortfolioCalculationEngine.calculate``) key includes
  ``include_acquisition_funding``, and the L2 report cache (``PortfolioService.get_report``)
  key includes all three new batch-2 flags. Same bug class the pnl-candles tests guard.

Pure tests (no DB, no async) mirror the conventions in test_pnl_candles.py /
test_cash_decomposition.py / test_signed_income.py in this directory. The cache-key and
dual-mode tests are real DB integration tests (real AsyncSession against the test
database, no HTTP server), mirroring test_pnl_candles.py's own two cache classes.
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
from backend.app.schemas.portfolio import AcquisitionFundingSeries, PortfolioReportQuery
from backend.app.services.portfolio_engine import (
    AcquisitionFundingContribution,
    ClassifiedTransaction,
    DailyStateBuilder,
    DerivedViewsBuilder,
    PortfolioCalculationResult,
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
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _ctxn(tx: MagicMock, classification: str = "normal", share: str = "1") -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share), paired_tx=None)


def _mark_series_from(classified_txs, price_map, asset_currencies, quote_base_map=None):
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
            split_linked_tx_ids=set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=(quote_base_map or {}).get(aid) or 1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg."""
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
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
        )
    return DailyStateBuilder(**defaults)


def _expected_buy_totals(classified_txs, target_currency: str = "EUR", fx_rate_map: dict | None = None) -> dict[date, Decimal]:
    """That day's total BUY cash outflow, computed INDEPENDENTLY of the engine.

    Deliberately re-derived from the transaction list the same way the engine's own
    ``amount_target`` is (abs(amount) -> FX -> * share), so the invariant assertion is a
    genuine cross-check against the source rows rather than a restatement of whatever the
    engine happened to accumulate. A BUY whose amount cannot be converted is skipped here
    exactly as ``if amount_target is None: continue`` skips it there.
    """
    totals: dict[date, Decimal] = {}
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.type != TransactionType.BUY or not tx.asset_id:
            continue
        if not tx.amount or tx.amount == 0 or tx.currency is None:
            continue
        if tx.currency == target_currency:
            converted = abs(tx.amount)
        else:
            rate = (fx_rate_map or {}).get((tx.currency, target_currency, tx.date))
            if rate is None:
                continue
            converted = abs(tx.amount) * rate
        totals[tx.date] = totals.get(tx.date, Decimal("0")) + converted * ctxn.share
    return totals


def _assert_split_reproduces_total_buy(result: PortfolioCalculationResult, classified_txs, *, target_currency: str = "EUR", fx_rate_map: dict | None = None) -> None:
    """THE invariant: every emitted split sums to that day's independently-derived total
    BUY outflow, and every day with a (frame-visible) BUY emits a split."""
    expected = _expected_buy_totals(classified_txs, target_currency, fx_rate_map)
    emitted: dict[date, Decimal] = {}
    for state in result.daily_states:
        if state.acquisition_funding is None:
            continue
        emitted[state.date] = state.acquisition_funding.from_new_capital + state.acquisition_funding.from_reinvested

    frame_dates = {s.date for s in result.daily_states}
    expected_in_frame = {d: v for d, v in expected.items() if d in frame_dates}

    assert emitted == expected_in_frame, f"split sums {emitted} != independently derived per-day BUY totals {expected_in_frame}"


def _funding_by_date(result: PortfolioCalculationResult) -> dict[date, AcquisitionFundingContribution | None]:
    return {s.date: s.acquisition_funding for s in result.daily_states}


# =============================================================================
# GOLDEN SCENARIO (hand-traced, empirically verified by the tests below)
# =============================================================================
#
# Broker 10, asset 100 priced flat at 100 EUR from 2025-01-01, so market value always
# equals cost basis and nothing below is attributable to valuation drift. Every BUY is
# the ONLY position transaction on its day, so "that day's total BUY" is unambiguous.
#
#   2025-01-01  DEPOSIT 1000        -> K=1000, R=0                 (no BUY -> None)
#   2025-01-02  BUY 4u, amount -400 -> R empty: from_r=0, from_k=400
#                                      K=600, R=0                  (400 / 0)
#   2025-01-03  DIVIDEND 300        -> R=300                       (no BUY -> None)
#   2025-01-04  BUY 2u, amount -200 -> R covers it: from_r=200, from_k=0
#                                      K=600, R=100                (0 / 200)
#   2025-01-05  BUY 5u, amount -500 -> R partial: from_r=100, from_k=400
#                                      K=200, R=0                  (400 / 100)
#
# Cash never goes negative (1000 -> 600 -> 900 -> 700 -> 200), so the end-of-day
# "4g. Clamp pools per-broker" step never fires and cannot be confused for the split.

_GOLDEN_PRICE_MAP = {100: [(date(2025, 1, 1), _d("100"), "EUR")]}
_GOLDEN_ECF = [(date(2025, 1, 1), 10, _d("1000"), "EUR")]


def _golden_txs() -> list[ClassifiedTransaction]:
    return [
        _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
        _ctxn(_tx(id=2, type="BUY", dt="2025-01-02", amount="-400", quantity="4", asset_id=100)),
        _ctxn(_tx(id=3, type="DIVIDEND", dt="2025-01-03", amount="300")),
        _ctxn(_tx(id=4, type="BUY", dt="2025-01-04", amount="-200", quantity="2", asset_id=100)),
        _ctxn(_tx(id=5, type="BUY", dt="2025-01-05", amount="-500", quantity="5", asset_id=100)),
    ]


def _golden_result(*, compute_acquisition_funding: bool = True) -> PortfolioCalculationResult:
    return _builder(
        classified_txs=_golden_txs(),
        external_cash_flows=_GOLDEN_ECF,
        price_map=_GOLDEN_PRICE_MAP,
        asset_currencies={100: "EUR"},
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 5),
        compute_acquisition_funding=compute_acquisition_funding,
    ).build()


class TestGoldenFundingRegimes:
    """The four regimes the split exists to distinguish, on one shared timeline."""

    def test_buy_from_empty_returns_pool_is_entirely_new_capital(self):
        """2025-01-02: the very first BUY, before any income ever arrived. R is empty,
        so ``from_r = min(400, max(0, 0)) = 0`` and the whole 400 is drawn from K."""
        funding = _funding_by_date(_golden_result())[date(2025, 1, 2)]

        assert funding is not None, "a BUY day must emit a contribution"
        assert funding.from_new_capital == _d("400")
        assert funding.from_reinvested == _d("0"), "nothing had been earned yet — reinvested must be exactly 0, not a rounding smear"

    def test_buy_fully_covered_by_returns_pool_is_entirely_reinvested(self):
        """2025-01-04: R=300 after the day-3 DIVIDEND, and the BUY is only 200 — the
        returns pool covers it outright, so K is untouched."""
        funding = _funding_by_date(_golden_result())[date(2025, 1, 4)]

        assert funding is not None
        assert funding.from_reinvested == _d("200")
        assert funding.from_new_capital == _d("0"), "R covered the whole BUY — no fresh capital may be attributed"

    def test_mixed_buy_drains_returns_first_then_falls_back_to_capital(self):
        """2025-01-05: R=100 left, BUY is 500 -> 100 reinvested + 400 fresh. Returns
        are consumed FIRST (``from_r = min(amount, R)``), which is the whole economic
        point of the dimension."""
        funding = _funding_by_date(_golden_result())[date(2025, 1, 5)]

        assert funding is not None
        assert funding.from_reinvested == _d("100")
        assert funding.from_new_capital == _d("400")

    def test_no_buy_day_has_no_contribution_object_at_all(self):
        """2025-01-01 (DEPOSIT only) and 2025-01-03 (DIVIDEND only) both have real
        transactions and are therefore fully evaluated days — they simply contain no
        BUY. The contract is ``None`` (a genuine "nothing acquired"), NOT a zero-valued
        AcquisitionFundingContribution, which a consumer would render as a 0-height bar
        rather than as absence."""
        by_date = _funding_by_date(_golden_result())

        for day in (date(2025, 1, 1), date(2025, 1, 3)):
            assert by_date[day] is None, f"{day} has no BUY -> must be None, got {by_date[day]!r}"

    def test_split_reproduces_each_days_total_buy_outflow(self):
        """THE invariant, checked against per-day totals re-derived from the raw
        transaction rows (see _expected_buy_totals) rather than from the engine."""
        txs = _golden_txs()
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 5),
            compute_acquisition_funding=True,
        ).build()

        _assert_split_reproduces_total_buy(result, txs)

    def test_both_legs_are_never_negative(self):
        """``from_r = min(amount, max(R, 0))`` is bounded below by 0 and above by the
        BUY amount, so neither leg can go negative even when R was driven below zero by
        a prior FEE/TAX or a negative income correction."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            # A legacy negative INTEREST correction pushes R below zero before the BUY.
            _ctxn(_tx(id=2, type="INTEREST", dt="2025-01-02", amount="-90")),
            _ctxn(_tx(id=3, type="BUY", dt="2025-01-03", amount="-300", quantity="3", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
            compute_acquisition_funding=True,
        ).build()

        funding = _funding_by_date(result)[date(2025, 1, 3)]
        assert funding is not None
        assert funding.from_new_capital >= _d("0")
        assert funding.from_reinvested >= _d("0")
        _assert_split_reproduces_total_buy(result, txs)


class TestMultipleBuysOneDay:
    """The accumulator is per-DAY, not per-transaction: several BUYs on one date collapse
    into a single contribution whose legs are the summed draws."""

    def test_two_buys_same_day_sum_into_one_contribution(self):
        """R=250 at the start of 2025-01-03. BUY #1 (100) is fully reinvested, leaving
        R=150; BUY #2 (400) then draws 150 reinvested + 250 fresh. The day's single
        contribution must be (250 fresh, 250 reinvested) = 500 total."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="DIVIDEND", dt="2025-01-02", amount="250")),
            _ctxn(_tx(id=3, type="BUY", dt="2025-01-03", amount="-100", quantity="1", asset_id=100)),
            _ctxn(_tx(id=4, type="BUY", dt="2025-01-03", amount="-400", quantity="4", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
            compute_acquisition_funding=True,
        ).build()

        states = [s for s in result.daily_states if s.date == date(2025, 1, 3)]
        assert len(states) == 1, "one state per day — two BUYs must not emit two states"
        funding = states[0].acquisition_funding
        assert funding is not None
        assert funding.from_reinvested == _d("250"), "150 (BUY #2) + 100 (BUY #1) = 250"
        assert funding.from_new_capital == _d("250")
        _assert_split_reproduces_total_buy(result, txs)

    def test_accumulator_resets_between_days(self):
        """The per-day accumulator is reset at the top of every frame day (like
        external_cash_flow). A second BUY day must NOT carry the first day's draw."""
        by_date = _funding_by_date(_golden_result())

        assert by_date[date(2025, 1, 2)].from_new_capital == _d("400")
        assert by_date[date(2025, 1, 5)].from_new_capital == _d("400"), "same value by coincidence, but it must be this day's own draw"
        assert by_date[date(2025, 1, 5)].from_reinvested == _d("100"), "day 2's from_reinvested (0) must not leak, nor day 4's (200) accumulate"


class TestComputeAcquisitionFundingDefaultOff:
    """``compute_acquisition_funding`` defaults to False — the same "extra output stays
    off unless a caller asks" convention as ``compute_candles``."""

    def test_default_builder_leaves_every_day_none_even_on_buy_days(self):
        result = _golden_result(compute_acquisition_funding=False)

        assert [s.acquisition_funding for s in result.daily_states] == [None] * len(result.daily_states)
        assert any(s.date == date(2025, 1, 2) for s in result.daily_states), "sanity: the BUY day WAS emitted, it just carries no split"

    def test_explicit_true_populates_the_same_days(self):
        on = _golden_result(compute_acquisition_funding=True)
        off = _golden_result(compute_acquisition_funding=False)

        assert [s.date for s in on.daily_states] == [s.date for s in off.daily_states], "the flag must change only the extra field, never which days are emitted"
        assert [s.total_pnl for s in on.daily_states] == [s.total_pnl for s in off.daily_states], "the flag must not perturb any canonical output"
        assert sum(1 for s in on.daily_states if s.acquisition_funding is not None) == 3


class TestStationaryDayAsymmetryVsPnlCandle:
    """The reused-state (day-skip) branch carries ``pnl_candle`` forward but resets
    ``acquisition_funding`` to None. This test does not merely assert the asymmetry —
    it demonstrates the reason: a stationary day has no transactions at all, so it
    cannot have a BUY, while a candle describes a standing position that legitimately
    stays flat.
    """

    def _quiet_result(self) -> PortfolioCalculationResult:
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="BUY", dt="2025-01-01", amount="-400", quantity="4", asset_id=100)),
        ]
        return _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
            compute_candles=True,
            compute_acquisition_funding=True,
        ).build()

    def test_buy_day_has_a_contribution_and_the_quiet_days_after_it_do_not(self):
        by_date = _funding_by_date(self._quiet_result())

        assert by_date[date(2025, 1, 1)] is not None, "the BUY day itself"
        assert by_date[date(2025, 1, 1)].from_new_capital == _d("400")
        for quiet in (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4)):
            assert by_date[quiet] is None, f"{quiet} is stationary (no transactions) -> no acquisition happened on it"

    def test_the_candle_is_carried_forward_across_the_same_quiet_days(self):
        """The asymmetry, made explicit side by side: on the very same reused states the
        candle IS the previous day's object while the funding split is None."""
        states = {s.date: s for s in self._quiet_result().daily_states}
        buy_day = states[date(2025, 1, 1)]

        for quiet in (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4)):
            assert states[quiet].pnl_candle is buy_day.pnl_candle, "candles carry forward on a stationary day (same object)"
            assert states[quiet].acquisition_funding is None, "funding does not — nothing was acquired"

    def test_a_stationary_day_genuinely_contains_no_transaction(self):
        """The justification itself: the day-skip fast path is gated on ``dirty_days``,
        which is seeded from every transaction date. So "stationary" and "has a BUY" are
        mutually exclusive by construction — proven here by the cash/NAV being byte-identical
        to the previous day (no tx could have moved them)."""
        states = {s.date: s for s in self._quiet_result().daily_states}
        buy_day = states[date(2025, 1, 1)]

        for quiet in (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4)):
            assert states[quiet].cash_value == buy_day.cash_value
            assert states[quiet].nav_value == buy_day.nav_value
            assert states[quiet].external_cash_flow == _d("0")


class TestPreFrameBuysSeedThePoolsWithoutEmittingADay:
    """The PRE-FRAME loop has its own, deliberately untouched BUY branch. Pre-frame days
    emit no DailyPortfolioState, so they can carry no split — but the K/R drawdown they
    perform is exactly what the frame's first BUY then draws against."""

    def _split_frame_result(self, *, frame_start: date) -> tuple[PortfolioCalculationResult, list[ClassifiedTransaction]]:
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="DIVIDEND", dt="2025-01-02", amount="300")),
            # PRE-FRAME BUY when frame_start=2025-01-05: draws 250 from R (R 300 -> 50).
            _ctxn(_tx(id=3, type="BUY", dt="2025-01-03", amount="-250", quantity="2.5", asset_id=100)),
            # FRAME BUY: R is now 50, so 50 reinvested + 150 fresh.
            _ctxn(_tx(id=4, type="BUY", dt="2025-01-05", amount="-200", quantity="2", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            frame_start=frame_start,
            date_to=date(2025, 1, 5),
            compute_acquisition_funding=True,
        ).build()
        return result, txs

    def test_preframe_buy_day_is_not_emitted_at_all(self):
        result, _ = self._split_frame_result(frame_start=date(2025, 1, 5))

        assert [s.date for s in result.daily_states] == [date(2025, 1, 5)], "only the frame day is emitted"

    def test_preframe_buy_drawdown_is_visible_in_the_frames_own_split(self):
        """The pre-frame BUY consumed 250 of the 300 returns pool. If the pre-frame
        branch had NOT drawn the pools down, the frame BUY would have found R=300 and
        reported (0 fresh / 200 reinvested) instead of (150 / 50)."""
        result, txs = self._split_frame_result(frame_start=date(2025, 1, 5))
        funding = _funding_by_date(result)[date(2025, 1, 5)]

        assert funding is not None
        assert funding.from_reinvested == _d("50"), "only the 50 the pre-frame BUY left behind"
        assert funding.from_new_capital == _d("150")
        _assert_split_reproduces_total_buy(result, txs)

    def test_same_transactions_without_a_preframe_produce_the_same_pool_arithmetic(self):
        """Cross-check that the pre-frame branch and the frame branch agree: run the
        identical transactions with frame_start at t=0, so the 2025-01-03 BUY goes through
        the FRAME branch instead. The 2025-01-05 split must be unchanged — the two code
        paths are two implementations of one pool policy, and this pins them together."""
        preframe_result, _ = self._split_frame_result(frame_start=date(2025, 1, 5))
        full_frame_result, txs = self._split_frame_result(frame_start=date(2025, 1, 1))

        preframe_day5 = _funding_by_date(preframe_result)[date(2025, 1, 5)]
        full_day5 = _funding_by_date(full_frame_result)[date(2025, 1, 5)]

        assert (full_day5.from_new_capital, full_day5.from_reinvested) == (preframe_day5.from_new_capital, preframe_day5.from_reinvested)
        # ...and in the all-frame run the 2025-01-03 BUY now DOES emit its own split.
        assert _funding_by_date(full_frame_result)[date(2025, 1, 3)].from_reinvested == _d("250")
        _assert_split_reproduces_total_buy(full_frame_result, txs)


class TestNonBuyActivityNeverFabricatesAContribution:
    def test_sell_day_emits_no_contribution(self):
        """A SELL credits both pools and `continue`s before the BUY branch — a disposal
        is not an acquisition and must not appear in this dimension."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="BUY", dt="2025-01-01", amount="-400", quantity="4", asset_id=100)),
            _ctxn(_tx(id=3, type="SELL", dt="2025-01-02", amount="250", quantity="-2", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_acquisition_funding=True,
        ).build()

        by_date = _funding_by_date(result)
        assert by_date[date(2025, 1, 1)] is not None, "sanity: the BUY day still reports"
        assert by_date[date(2025, 1, 2)] is None, "a SELL-only day acquires nothing"
        _assert_split_reproduces_total_buy(result, txs)

    def test_in_kind_adjustment_in_is_not_a_buy(self):
        """An in-kind ADJUSTMENT-in adds quantity with no cash outflow. It is a capital
        contribution, not a funded acquisition, so it must not appear here."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="ADJUSTMENT", dt="2025-01-02", amount="0", quantity="3", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_acquisition_funding=True,
        ).build()

        assert _funding_by_date(result)[date(2025, 1, 2)] is None

    def test_buy_with_an_unconvertible_currency_is_skipped_not_zeroed(self):
        """``amount_target is None`` (no FX route) makes the engine skip the whole 3-pool
        block for that transaction. The day must then report NO contribution rather than a
        (0, 0) one that would read as "acquired nothing" instead of "could not price it"."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000")),
            _ctxn(_tx(id=2, type="BUY", dt="2025-01-02", amount="-400", currency="PGK", quantity="4", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            fx_rate_map={},  # no PGK/EUR route
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_acquisition_funding=True,
        ).build()

        assert _funding_by_date(result)[date(2025, 1, 2)] is None, "unpriceable BUY must be a gap, never a zeroed contribution"


class TestShareAndFxScaling:
    def test_split_is_computed_on_the_share_scaled_amount(self):
        """A 30%-share BUY of 1000 draws 300, not 1000 — the split must be taken on
        ``amount_target`` AFTER the share multiplication, so the two legs still sum to
        the scaled figure."""
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="1000"), share="0.3"),
            _ctxn(_tx(id=2, type="BUY", dt="2025-01-02", amount="-1000", quantity="10", asset_id=100), share="0.3"),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=[(date(2025, 1, 1), 10, _d("300"), "EUR")],
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_acquisition_funding=True,
        ).build()

        funding = _funding_by_date(result)[date(2025, 1, 2)]
        assert funding is not None
        assert funding.from_new_capital + funding.from_reinvested == _d("300"), "0.3 * 1000"
        _assert_split_reproduces_total_buy(result, txs)

    def test_split_is_computed_on_the_fx_converted_amount(self):
        """A USD BUY at 0.9 USD/EUR draws 900 EUR. The legs are in the TARGET currency,
        like every other engine output."""
        fx = {("USD", "EUR", date(2025, 1, 2)): _d("0.9")}
        txs = [
            _ctxn(_tx(id=1, type="DEPOSIT", dt="2025-01-01", amount="2000")),
            _ctxn(_tx(id=2, type="BUY", dt="2025-01-02", amount="-1000", currency="USD", quantity="10", asset_id=100)),
        ]
        result = _builder(
            classified_txs=txs,
            external_cash_flows=[(date(2025, 1, 1), 10, _d("2000"), "EUR")],
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            fx_rate_map=fx,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
            compute_acquisition_funding=True,
        ).build()

        funding = _funding_by_date(result)[date(2025, 1, 2)]
        assert funding is not None
        assert funding.from_new_capital + funding.from_reinvested == _d("900"), "1000 USD * 0.9 = 900 EUR"
        _assert_split_reproduces_total_buy(result, txs, fx_rate_map=fx)


# =============================================================================
# DerivedViewsBuilder.build_acquisition_funding()
# =============================================================================


class TestDerivedViewsBuilderAcquisitionFunding:
    def test_shape_and_golden_values(self):
        points = DerivedViewsBuilder(_golden_result().daily_states, "EUR").build_acquisition_funding()

        assert len(points) == 3, "three BUY days out of five emitted days"
        for point in points:
            assert set(point.keys()) == {"date", "from_new_capital", "from_reinvested"}
            for field in ("from_new_capital", "from_reinvested"):
                assert isinstance(point[field], CurrencySchema)
                assert point[field].code == "EUR"

        by_date = {p["date"]: p for p in points}
        assert (by_date[date(2025, 1, 2)]["from_new_capital"].amount, by_date[date(2025, 1, 2)]["from_reinvested"].amount) == (_d("400"), _d("0"))
        assert (by_date[date(2025, 1, 4)]["from_new_capital"].amount, by_date[date(2025, 1, 4)]["from_reinvested"].amount) == (_d("0"), _d("200"))
        assert (by_date[date(2025, 1, 5)]["from_new_capital"].amount, by_date[date(2025, 1, 5)]["from_reinvested"].amount) == (_d("400"), _d("100"))

    def test_no_buy_day_is_omitted_not_zeroed(self):
        """Mirrors build_pnl_candles's own omission convention: 2025-01-01 and
        2025-01-03 are emitted daily states with real activity, but no BUY — so the view
        must skip them entirely rather than emit a (0, 0) row."""
        points = DerivedViewsBuilder(_golden_result().daily_states, "EUR").build_acquisition_funding()

        assert {p["date"] for p in points} == {date(2025, 1, 2), date(2025, 1, 4), date(2025, 1, 5)}

    def test_every_returned_point_reproduces_its_states_contribution(self):
        result = _golden_result()
        states_by_date = {s.date: s for s in result.daily_states}
        points = DerivedViewsBuilder(result.daily_states, "EUR").build_acquisition_funding()

        assert points
        for point in points:
            contribution = states_by_date[point["date"]].acquisition_funding
            assert point["from_new_capital"].amount == contribution.from_new_capital
            assert point["from_reinvested"].amount == contribution.from_reinvested

    def test_target_currency_is_propagated_to_both_legs(self):
        points = DerivedViewsBuilder(_golden_result().daily_states, "CHF").build_acquisition_funding()

        assert points
        assert {p["from_new_capital"].code for p in points} == {"CHF"}
        assert {p["from_reinvested"].code for p in points} == {"CHF"}

    def test_engine_run_without_the_flag_yields_an_empty_view(self):
        points = DerivedViewsBuilder(_golden_result(compute_acquisition_funding=False).daily_states, "EUR").build_acquisition_funding()

        assert points == [], "no state carries a contribution -> nothing to emit"


# =============================================================================
# PortfolioService.get_acquisition_funding_history() — pure slicing (no DB)
# =============================================================================


class TestGetAcquisitionFundingHistoryPure:
    """Follows TestPortfolioServiceGetPnlCandlesPure in test_pnl_candles.py verbatim:
    with both ``_precomputed_engine_result`` AND ``target_currency_override`` supplied,
    ``self.db`` is never touched, so this mode is exercisable purely.
    """

    @pytest.mark.asyncio
    async def test_slices_to_date_range_and_matches_golden_values(self):
        series = await PortfolioService(db=None).get_acquisition_funding_history(
            user_id=1,
            target_currency_override="EUR",
            date_from=date(2025, 1, 3),
            date_to=date(2025, 1, 4),
            _precomputed_engine_result=_golden_result(),
        )

        assert isinstance(series, AcquisitionFundingSeries)
        assert [p.date for p in series.points] == [date(2025, 1, 4)]
        assert series.points[0].from_new_capital.amount == _d("0")
        assert series.points[0].from_reinvested.amount == _d("200")

    @pytest.mark.asyncio
    async def test_unbounded_range_returns_every_buy_day(self):
        series = await PortfolioService(db=None).get_acquisition_funding_history(
            user_id=1,
            target_currency_override="EUR",
            _precomputed_engine_result=_golden_result(),
        )

        assert [p.date for p in series.points] == [date(2025, 1, 2), date(2025, 1, 4), date(2025, 1, 5)]

    @pytest.mark.asyncio
    async def test_date_from_slice_is_exclusive_start_inclusive_end(self):
        """Canonical (date_from, date_to] boundary: a BUY dated exactly on date_from
        belongs to the PREVIOUS period and is excluded; one dated on date_to is included.

        This DELIBERATELY diverges from get_pnl_candles / get_broker_pnl_history, whose
        engine-backed slicing this method otherwise mirrors exactly. Those two are LEVEL
        series (a cumulative value per day), so the opening day is the baseline and must
        be shown. Acquisition funding is a FLOW series (that day's own BUY split), so it
        follows the same exclusive-start rule as its five co-rendered Income-submode
        siblings. Sharing the engine-backed *mechanism* is not the same as sharing the
        *semantics* — the original implementation inherited the wrong one, which is the
        bug this test now pins the fix for.
        """
        series = await PortfolioService(db=None).get_acquisition_funding_history(
            user_id=1,
            target_currency_override="EUR",
            date_from=date(2025, 1, 2),
            date_to=date(2025, 1, 5),
            _precomputed_engine_result=_golden_result(),
        )

        assert [p.date for p in series.points] == [date(2025, 1, 4), date(2025, 1, 5)], "the BUY day equal to date_from must be EXCLUDED; the one equal to date_to included"

    @pytest.mark.asyncio
    async def test_diverges_from_get_pnl_candles_on_the_same_engine_result_and_window(self):
        """The divergence above, proven by EXECUTION rather than asserted in a comment.

        One engine result, one (date_from, date_to) pair, two methods: the level series
        keeps its date_from day, the flow series drops it. If someone ever "harmonises"
        the two slicing rules in either direction, exactly one of these two assertions
        goes red and names which contract was broken.
        """
        result = _builder(
            classified_txs=_golden_txs(),
            external_cash_flows=_GOLDEN_ECF,
            price_map=_GOLDEN_PRICE_MAP,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 5),
            compute_candles=True,
            compute_acquisition_funding=True,
        ).build()
        service = PortfolioService(db=None)
        window = {"date_from": date(2025, 1, 2), "date_to": date(2025, 1, 5)}

        candles = await service.get_pnl_candles(user_id=1, target_currency_override="EUR", _precomputed_engine_result=result, **window)
        funding = await service.get_acquisition_funding_history(user_id=1, target_currency_override="EUR", _precomputed_engine_result=result, **window)

        # LEVEL series: date_from itself is the period's opening baseline -> kept.
        assert date(2025, 1, 2) in [p.date for p in candles.points], "get_pnl_candles must still INCLUDE its date_from day (level-series semantics, unchanged)"
        # FLOW series: a BUY on date_from belongs to the previous period -> dropped.
        assert date(2025, 1, 2) not in [p.date for p in funding.points], "get_acquisition_funding_history must EXCLUDE its date_from day (flow-series semantics)"
        # ...and both agree on every day strictly inside the window.
        assert date(2025, 1, 5) in [p.date for p in candles.points]
        assert date(2025, 1, 5) in [p.date for p in funding.points]

    @pytest.mark.asyncio
    async def test_empty_daily_states_returns_empty_series(self):
        series = await PortfolioService(db=None).get_acquisition_funding_history(
            user_id=1,
            target_currency_override="EUR",
            _precomputed_engine_result=PortfolioCalculationResult(daily_states=[]),
        )

        assert series.points == []

    @pytest.mark.asyncio
    async def test_precomputed_result_without_the_flag_returns_no_points(self):
        """The documented caveat: the flag must be set on the SHARED engine run or every
        day comes back empty. This is the failure mode get_report() avoids by threading
        include_acquisition_funding into engine.calculate()."""
        series = await PortfolioService(db=None).get_acquisition_funding_history(
            user_id=1,
            target_currency_override="EUR",
            _precomputed_engine_result=_golden_result(compute_acquisition_funding=False),
        )

        assert series.points == []


# =============================================================================
# REAL-DB INTEGRATION — dual-mode parity + L1/L2 cache keys
# =============================================================================
#
# Mirrors test_pnl_candles.py's own DB fixtures (AsyncSession against the test database,
# no HTTP server). Dates are parked far in the future so these rows cannot collide with
# mock data or with another unit's window.


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
        username=f"acqfund_{utcnow().timestamp()}",
        email=f"acqfund_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_acquisition_portfolio(session, test_user, *, name_prefix: str, day1: date) -> Broker:
    """DEPOSIT 1000 + BUY 400 (day1), DIVIDEND 300 (day2), BUY 200 (day3) — the golden
    scenario's shape, compressed: day1 is fresh-capital-only, day3 is reinvested-only.
    """
    broker = Broker(name=f"{name_prefix}_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    asset = Asset(display_name=f"{name_prefix}Asset_{utcnow().timestamp()}", currency="EUR", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    day2 = date.fromordinal(day1.toordinal() + 1)
    day3 = date.fromordinal(day1.toordinal() + 2)
    session.add_all(
        [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day1, amount=Decimal("1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day1, quantity=Decimal("4"), amount=Decimal("-400"), currency="EUR"),
            Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=day2, amount=Decimal("300"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day3, quantity=Decimal("2"), amount=Decimal("-200"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=day1, close=Decimal("100"), currency="EUR", source_plugin_key="manual_test"),
        ]
    )
    await session.flush()
    return broker


class TestGetAcquisitionFundingHistoryDualMode:
    """The method has two modes — a caller-supplied ``_precomputed_engine_result`` (how
    get_report uses it, sharing one engine run) and a standalone
    ``engine.calculate(include_acquisition_funding=True)``. They must produce the SAME
    series, or the report and a direct call would disagree about the same portfolio.

    The pnl-candles precedent only exercises the precomputed half (pure, no DB); this
    runs both against a real session and compares them.
    """

    @pytest.mark.asyncio
    async def test_standalone_and_precomputed_modes_agree_exactly(self, session, test_user):
        day1 = date(2035, 3, 1)
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqDual", day1=day1)
        portfolio_engine_module._portfolio_blob_cache.clear()
        service = PortfolioService(session)
        day3 = date(2035, 3, 3)

        standalone = await service.get_acquisition_funding_history(user_id=test_user.id, broker_ids=[broker.id], date_to=day3, target_currency_override="EUR")

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)
        shared_result = await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=day3, target_currency="EUR", include_acquisition_funding=True)
        precomputed = await service.get_acquisition_funding_history(user_id=test_user.id, broker_ids=[broker.id], date_to=day3, target_currency_override="EUR", _precomputed_engine_result=shared_result)

        assert [(p.date, p.from_new_capital.amount, p.from_reinvested.amount) for p in standalone.points] == [(p.date, p.from_new_capital.amount, p.from_reinvested.amount) for p in precomputed.points]

    @pytest.mark.asyncio
    async def test_standalone_mode_reports_the_expected_two_buy_days(self, session, test_user):
        """Not just parity — the shared value must also be RIGHT: day1's BUY predates
        any income (400 fresh / 0), day3's is fully covered by the day2 dividend
        (0 fresh / 200 reinvested)."""
        day1 = date(2035, 4, 1)
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqStandalone", day1=day1)
        portfolio_engine_module._portfolio_blob_cache.clear()

        series = await PortfolioService(session).get_acquisition_funding_history(user_id=test_user.id, broker_ids=[broker.id], date_to=date(2035, 4, 3), target_currency_override="EUR")

        assert [(p.date, p.from_new_capital.amount, p.from_reinvested.amount) for p in series.points] == [
            (date(2035, 4, 1), Decimal("400"), Decimal("0")),
            (date(2035, 4, 3), Decimal("0"), Decimal("200")),
        ]

    @pytest.mark.asyncio
    async def test_standalone_mode_always_computes_from_t0_regardless_of_date_from(self, session, test_user):
        """``date_from=None`` is passed to the engine deliberately: the K/R split depends
        on pool state accumulated over the ENTIRE prior history. Asking only for day3 must
        still report it as reinvested — which is only knowable from the day2 dividend that
        falls outside the requested window.

        The window is (day2, day3]: day2 carries the dividend and is itself excluded by the
        boundary, so this also demonstrates that "outside the reported window" and "outside
        the computation" are two different things.
        """
        day1 = date(2035, 5, 1)
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqT0", day1=day1)
        portfolio_engine_module._portfolio_blob_cache.clear()

        series = await PortfolioService(session).get_acquisition_funding_history(user_id=test_user.id, broker_ids=[broker.id], date_from=date(2035, 5, 2), date_to=date(2035, 5, 3), target_currency_override="EUR")

        assert [p.date for p in series.points] == [date(2035, 5, 3)]
        assert series.points[0].from_reinvested.amount == Decimal("200"), "the out-of-window day2 dividend is what makes this reinvested"
        assert series.points[0].from_new_capital.amount == Decimal("0")


class TestPortfolioBlobCacheIncludeAcquisitionFundingSensitivity:
    """The L1 blob cache key (blob_key tuple in PortfolioCalculationEngine.calculate) must
    include ``include_acquisition_funding`` — the exact omission that has been caught twice
    before in this file's history for ``include_candles``. Without it, a blob computed for
    a plain report would satisfy a later acquisition-funding request and every day would
    come back None.
    """

    @pytest.mark.asyncio
    async def test_blob_cache_distinguishes_include_acquisition_funding(self, session, test_user, monkeypatch):
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqBlob", day1=date(2035, 6, 1))
        portfolio_engine_module._portfolio_blob_cache.clear()

        build_calls = {"n": 0}
        original_build = portfolio_engine_module.DailyStateBuilder.build

        def counting_build(builder_self):
            build_calls["n"] += 1
            return original_build(builder_self)

        monkeypatch.setattr(portfolio_engine_module.DailyStateBuilder, "build", counting_build)

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)
        kwargs = {"broker_ids": [broker.id], "date_to": date(2035, 6, 3), "target_currency": "EUR"}

        result_false = await engine.calculate(test_user.id, **kwargs, include_acquisition_funding=False)
        assert build_calls["n"] == 1
        assert all(s.acquisition_funding is None for s in result_false.daily_states)

        result_true = await engine.calculate(test_user.id, **kwargs, include_acquisition_funding=True)
        assert build_calls["n"] == 2, "include_acquisition_funding=True reused the =False blob (L1 cache key missing the flag)"
        assert any(s.acquisition_funding is not None for s in result_true.daily_states)

        result_false_again = await engine.calculate(test_user.id, **kwargs, include_acquisition_funding=False)
        assert build_calls["n"] == 2, "re-requesting =False triggered a rebuild instead of hitting its own cached blob"
        assert all(s.acquisition_funding is None for s in result_false_again.daily_states)

        result_true_again = await engine.calculate(test_user.id, **kwargs, include_acquisition_funding=True)
        assert build_calls["n"] == 2, "re-requesting =True triggered a rebuild instead of hitting its own cached blob"
        assert any(s.acquisition_funding is not None for s in result_true_again.daily_states)

    @pytest.mark.asyncio
    async def test_blob_cache_keeps_candles_and_acquisition_funding_distinct(self, session, test_user, monkeypatch):
        """The two opt-in flags are separate key elements, not one "extras" bit: asking
        for candles must not hand back an acquisition-funding blob, or vice versa."""
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqBlobMix", day1=date(2035, 7, 1))
        portfolio_engine_module._portfolio_blob_cache.clear()

        build_calls = {"n": 0}
        original_build = portfolio_engine_module.DailyStateBuilder.build

        def counting_build(builder_self):
            build_calls["n"] += 1
            return original_build(builder_self)

        monkeypatch.setattr(portfolio_engine_module.DailyStateBuilder, "build", counting_build)

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)
        kwargs = {"broker_ids": [broker.id], "date_to": date(2035, 7, 3), "target_currency": "EUR"}

        candles_only = await engine.calculate(test_user.id, **kwargs, include_candles=True, include_acquisition_funding=False)
        assert build_calls["n"] == 1
        assert all(s.acquisition_funding is None for s in candles_only.daily_states)

        funding_only = await engine.calculate(test_user.id, **kwargs, include_candles=False, include_acquisition_funding=True)
        assert build_calls["n"] == 2, "the acquisition-funding request reused the candles blob"
        assert any(s.acquisition_funding is not None for s in funding_only.daily_states)
        assert all(s.pnl_candle is None for s in funding_only.daily_states)

        both = await engine.calculate(test_user.id, **kwargs, include_candles=True, include_acquisition_funding=True)
        assert build_calls["n"] == 3, "the both-flags request reused one of the single-flag blobs"
        assert any(s.pnl_candle is not None and s.acquisition_funding is not None for s in both.daily_states)


class TestPortfolioL2CacheIncludesBatch2Flags:
    """get_report()'s L2 report cache key must include all three new flags. Without one,
    a report requested WITHOUT that section would satisfy a later request WITH it, and the
    section would silently come back None.
    """

    _SECTIONS = [
        ("include_cost_history", "cost_history"),
        ("include_deposit_history", "deposit_history"),
        ("include_acquisition_funding", "acquisition_funding"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("flag", "field"), _SECTIONS)
    async def test_l2_cache_distinguishes_each_batch2_flag(self, session, test_user, flag, field):
        day1 = date(2035, 8, 1)
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix=f"AcqL2_{flag}", day1=day1)
        # A FEE so the cost_history section has something to report on this scope too.
        session.add(Transaction(broker_id=broker.id, type=TransactionType.FEE, date=day1, amount=Decimal("-7"), currency="EUR"))
        await session.flush()
        portfolio_service_module._portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()

        service = PortfolioService(session)
        query_kwargs = {
            "broker_ids": [broker.id],
            "include_summary": False,
            "include_history": False,
            "include_allocation_history": False,
            "date_range": {"start": "2035-07-31", "end": "2035-08-03"},
        }

        off = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, **{flag: False}))
        assert getattr(off, field) is None
        assert field not in off.metadata.included_features

        # POSITIVE CONTROL. Without this the test could pass for the wrong reason: if the
        # L2 cache were never consulted at all (disabled, or keyed on something volatile),
        # every request below would recompute and the "cache-key sensitivity" assertion
        # would be vacuous. get_report returns the cached object BY IDENTITY on a hit, so
        # an identical repeat proves the cache is genuinely live for this scope/query.
        off_cached = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, **{flag: False}))
        assert off_cached is off, "L2 cache did not serve an identical repeat request — the sensitivity assertions below would be vacuous"

        on = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, **{flag: True}))
        assert getattr(on, field) is not None, f"{flag}=True reused the {flag}=False L2 cache entry (L2 key missing the flag)"
        assert field in on.metadata.included_features
        assert getattr(on, field).points, f"{field} must actually carry data for this scope"

        off_again = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**query_kwargs, **{flag: False}))
        assert getattr(off_again, field) is None, f"re-requesting {flag}=False picked up the {flag}=True L2 cache entry"

    @pytest.mark.asyncio
    async def test_report_acquisition_funding_matches_the_direct_call(self, session, test_user):
        """get_report threads include_acquisition_funding into the SHARED engine run and
        then passes that result in as _precomputed_engine_result. If the threading were
        missing, the section would be present but empty — so compare it against the
        standalone method on the same scope."""
        day1 = date(2035, 9, 1)
        broker = await _seed_acquisition_portfolio(session, test_user, name_prefix="AcqReport", day1=day1)
        portfolio_service_module._portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()

        service = PortfolioService(session)
        report = await service.get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                broker_ids=[broker.id],
                include_summary=False,
                include_history=False,
                include_allocation_history=False,
                include_acquisition_funding=True,
                date_range={"start": "2035-08-31", "end": "2035-09-03"},
            ),
        )
        direct = await service.get_acquisition_funding_history(user_id=test_user.id, broker_ids=[broker.id], date_from=date(2035, 8, 31), date_to=date(2035, 9, 3), target_currency_override="EUR")

        assert report.acquisition_funding is not None
        assert [(p.date, p.from_new_capital.amount, p.from_reinvested.amount) for p in report.acquisition_funding.points] == [(p.date, p.from_new_capital.amount, p.from_reinvested.amount) for p in direct.points]
        assert report.acquisition_funding.points, "sanity: the shared engine run really did carry the flag"


class TestIncomeSubmodeFlowSeriesShareOneBoundary:
    """THE cross-series invariant, and the one that actually protects the user-visible
    chart: all four Income-submode flow dimensions render as bars on ONE shared x-axis,
    so they must agree on which day a flow belongs to.

    Each series' own boundary test (TestGetCostHistory / TestGetDepositHistory /
    TestGetIncomeHistory in test_portfolio_service.py, and the pure slicing tests above)
    checks that series in isolation — all four could individually be "correct" against
    their own docstring and still disagree with each other, which is exactly the defect
    that shipped: acquisition funding inherited a LEVEL-series inclusive start from
    get_pnl_candles, so a BUY dated on date_from drew a bar while a DIVIDEND on that very
    same date drew none. This test compares them against EACH OTHER instead.
    """

    async def _seed_one_of_every_flow_on_two_days(self, session, test_user, *, boundary_day: date, inside_day: date) -> Broker:
        """Every flow type on BOTH days, so "absent" can only mean the boundary rule."""
        broker = Broker(name=f"AcqBoundary_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        asset = Asset(display_name=f"AcqBoundaryAsset_{utcnow().timestamp()}", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        rows = []
        for day, dep, div, fee, buy_amt, buy_qty in ((boundary_day, "1000", "50", "-5", "-200", "2"), (inside_day, "500", "60", "-7", "-300", "3")):
            rows += [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day, amount=Decimal(dep), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=day, amount=Decimal(div), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=day, amount=Decimal(fee), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day, quantity=Decimal(buy_qty), amount=Decimal(buy_amt), currency="EUR"),
            ]
        rows.append(PriceHistory(asset_id=asset.id, date=boundary_day, close=Decimal("100"), currency="EUR", source_plugin_key="manual_test"))
        session.add_all(rows)
        await session.flush()
        return broker

    async def _all_four_series_dates(self, session, test_user, broker, *, date_from: date | None, date_to: date) -> dict[str, list[date]]:
        portfolio_engine_module._portfolio_blob_cache.clear()
        service = PortfolioService(session)
        kwargs = {"user_id": test_user.id, "broker_ids": [broker.id], "date_from": date_from, "date_to": date_to, "target_currency_override": "EUR"}
        return {
            "income": [p.date for p in (await service.get_income_history(**kwargs)).points],
            "cost": [p.date for p in (await service.get_cost_history(**kwargs)).points],
            "deposit": [p.date for p in (await service.get_deposit_history(**kwargs)).points],
            "acquisition_funding": [p.date for p in (await service.get_acquisition_funding_history(**kwargs)).points],
        }

    @pytest.mark.asyncio
    async def test_a_flow_dated_exactly_on_date_from_is_absent_from_ALL_four_series(self, session, test_user):
        boundary_day, inside_day = date(2035, 10, 1), date(2035, 10, 2)
        broker = await self._seed_one_of_every_flow_on_two_days(session, test_user, boundary_day=boundary_day, inside_day=inside_day)

        # POSITIVE CONTROL first. Widen date_from by one day and all four series must show
        # BOTH days — without this, "absent" below could equally mean "this series never
        # had anything on that day", and the invariant would be vacuous.
        control = await self._all_four_series_dates(session, test_user, broker, date_from=date(2035, 9, 30), date_to=inside_day)
        for name, dates in control.items():
            assert dates == [boundary_day, inside_day], f"control: {name} must carry BOTH days when the window opens before them, got {dates}"

        # THE INVARIANT: with date_from ON the boundary day, every series drops it — the
        # same day, the same scope, four independently implemented code paths (three pure
        # transaction scans and one engine-derived view).
        windowed = await self._all_four_series_dates(session, test_user, broker, date_from=boundary_day, date_to=inside_day)
        for name, dates in windowed.items():
            assert dates == [inside_day], f"{name} disagrees with its co-rendered siblings about the (date_from, date_to] boundary, got {dates}"

        # Stated as the property itself, so a future failure reads as what it is.
        assert len({tuple(d) for d in windowed.values()}) == 1, f"all four Income-submode flow series must report the SAME set of dates for one window, got {windowed}"

    @pytest.mark.asyncio
    async def test_date_to_is_inclusive_for_all_four_series_alike(self, session, test_user):
        """The other end of the same window, checked the same way: date_to belongs to the
        period in every one of the four."""
        boundary_day, inside_day = date(2035, 11, 1), date(2035, 11, 2)
        broker = await self._seed_one_of_every_flow_on_two_days(session, test_user, boundary_day=boundary_day, inside_day=inside_day)

        series = await self._all_four_series_dates(session, test_user, broker, date_from=None, date_to=inside_day)

        for name, dates in series.items():
            assert dates[-1] == inside_day, f"{name} dropped its date_to day, got {dates}"
        assert len({tuple(d) for d in series.values()}) == 1, f"all four series must agree on an unbounded-start window too, got {series}"

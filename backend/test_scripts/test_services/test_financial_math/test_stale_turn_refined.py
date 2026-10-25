"""MF-P4b (D-P4 cure B, contract §3 and §8.4) — the «price turning stale» day is a novelty only before a real gap.

Today ``DailyStateBuilder._collect_dirty_days`` marks ``d + STALE_PRICE_THRESHOLD_DAYS + 1`` dirty after EVERY observed
day ``d`` (every quote and every position movement). A Friday quote therefore makes the Saturday of the next week a
segment start although Monday's quote already restarted the price's age: a spurious novelty, an extra step in every series
of the report.

The refined rule (contract §3): a day is dirty for a price turning stale only when an asset's mark has an observation on
day ``d`` (``AssetPriceSeries.observation_dates``) and NO newer observation of that asset in
``(d, d + STALE_PRICE_THRESHOLD_DAYS + 1]``; then ``d + STALE_PRICE_THRESHOLD_DAYS + 1`` is dirty. The threshold (7) and
every daily state stay identical: only the segment starts change.

What is tested (pure: no database, no server, no network; the builder is fed by hand as in
``test_engine_state_segments.py``, whose helpers are copied below):

1. ``TestWeekdayQuotes`` — an EUR stock quoted every weekday for four weeks, the window ending before the last quote's
   own turn: no segment starts on a Saturday or a Sunday, and the segment starts are exactly ``date_from`` and the quote
   days. RED on HEAD: the Fridays + 8 (three Saturdays) and the Tuesday/Wednesday + 8 of the last week are segment starts.
2. ``TestTenDayGap`` — weekday quotes with a gap of ten days: ``last quote + 8`` (a Saturday) is a segment start, the
   stale flag (``stale_price_asset_ids``) flips there and only there, and the segment starts are exactly ``date_from``, the
   quote days and that one turn. RED on HEAD for the exact list (the spurious Saturdays); the flip itself is a guard.
3. ``TestDailyStatesUnchanged`` (guards, green on HEAD and after the cure) — on both books:
   - every day's ``stale_price_asset_ids`` equals the one computed from ``mark_series[asset].resolve(day)``
     (``days_back > STALE_PRICE_THRESHOLD_DAYS``) over the held assets;
   - every daily state equals, field by field (Decimals by ``as_tuple``), the state of a dense run in which every day of
     the frame is computed (``_collect_dirty_days`` wrapped to add every day): fewer segments, same days.

No clock, no sleep, no translated text; days are built from fixed dates.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).

Reference: backend/app/services/financial_math/portfolio/daily_state.py (_collect_dirty_days, _market_value_for),
backend/app/services/financial_math/price_marks.py (AssetPriceSeries.observation_dates),
backend/app/services/platform/data_quality_thresholds.py (STALE_PRICE_THRESHOLD_DAYS).
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A = 10
X = 100
TURN = STALE_PRICE_THRESHOLD_DAYS + 1  # 8: the first day a carried price is stale

# =============================================================================
# HELPERS — copies of test_engine_state_segments.py
# =============================================================================


def _tx(*, id: int, type: str = "DEPOSIT", dt: date, amount: str = "0", quantity: str = "0", asset_id: int | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = A
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = "EUR"
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _ledger(txs, *, date_to: date, price_map: dict) -> dict:
    """Builder kwargs of a classified EUR ledger on broker A (the real classifier, loading order (date, id), share 1)."""
    classification = ScopeAwareTransactionClassifier(
        scope_broker_ids={A},
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares={A: Decimal("1")},
    ).classify()
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    kwargs = {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "quote_base_map": {},
        "fx_rate_map": {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR"),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "target_currency": "EUR",
        "date_to": date_to,
    }
    kwargs["mark_series"] = _mark_series_from(kwargs["classified_txs"], price_map, kwargs["asset_currencies"])
    kwargs["average_costs"] = engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map={}, date_to=date_to)
    kwargs["native_cash"] = engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map={}, date_to=date_to)
    return kwargs


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _weekdays(first: date, last: date) -> list[date]:
    return [day for day in _days(first, last) if day.weekday() < 5]


def _closes(days: list[date]) -> dict[int, list[tuple[date, Decimal, str]]]:
    """X's quotes, one a day, each different from the day before (100.00, 100.25, … in a cycle of 13)."""
    return {X: [(day, Decimal(f"{100 + (index % 13) / 4:.2f}"), "EUR") for index, day in enumerate(days)]}


def _build(ledger: dict, *, date_from: date) -> PortfolioCalculationResult:
    return DailyStateBuilder(**ledger, date_from=date_from).build()


def _exact(value):
    """A comparable form of a state's field: Decimals by ``as_tuple`` (exponent included), containers recursively."""
    if isinstance(value, Decimal):
        return ("D", value.as_tuple())
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (type(value).__name__, tuple((f.name, _exact(getattr(value, f.name))) for f in dataclasses.fields(value)))
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((repr(k), _exact(v)) for k, v in value.items()), key=lambda item: item[0])))
    if isinstance(value, (set, frozenset)):
        return ("set", tuple(sorted(repr(_exact(v)) for v in value)))
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(_exact(v) for v in value))
    return value


def _state_fields(state: DailyPortfolioState) -> dict:
    return {f.name: _exact(getattr(state, f.name)) for f in dataclasses.fields(state)}


# =============================================================================
# BOOKS
# =============================================================================

# The weekday book: A deposits 10 000 and buys 10 X for 1000 on Monday 2025-03-03; X is quoted every weekday from 03-03
# to Friday 03-28 (four weeks). The window ends on Thursday 04-03, before the last quote's own turn (03-28 + 8 = 04-05).
WEEKDAY_FROM, WEEKDAY_TO = date(2025, 3, 3), date(2025, 4, 3)
WEEKDAY_QUOTES = _weekdays(date(2025, 3, 3), date(2025, 3, 28))


def _weekday_book() -> dict:
    txs = [
        _tx(id=1, dt=WEEKDAY_FROM, amount="10000"),
        _tx(id=2, type="BUY", dt=WEEKDAY_FROM, amount="-1000", quantity="10", asset_id=X),
    ]
    return _ledger(txs, date_to=WEEKDAY_TO, price_map=_closes(WEEKDAY_QUOTES))


#: HEAD's extra segment starts on the weekday book: every quote day + 8 that is no quote day and falls in the window.
WEEKDAY_SPURIOUS_ON_HEAD = sorted({day + timedelta(days=TURN) for day in WEEKDAY_QUOTES if day + timedelta(days=TURN) <= WEEKDAY_TO} - set(WEEKDAY_QUOTES))

# The gap book: same deposit and BUY; X quoted on the weekdays 03-03..03-14 (Friday), then not until Tuesday 03-25, then
# every weekday to Friday 04-04. The window ends on Thursday 04-10, before 04-04's own turn (04-12).
GAP_FROM, GAP_TO = date(2025, 3, 3), date(2025, 4, 10)
GAP_LAST_BEFORE = date(2025, 3, 14)
GAP_TURN = GAP_LAST_BEFORE + timedelta(days=TURN)  # Saturday 2025-03-22
GAP_RESUME = date(2025, 3, 25)
GAP_QUOTES = _weekdays(GAP_FROM, GAP_LAST_BEFORE) + _weekdays(GAP_RESUME, date(2025, 4, 4))


def _gap_book() -> dict:
    txs = [
        _tx(id=1, dt=GAP_FROM, amount="10000"),
        _tx(id=2, type="BUY", dt=GAP_FROM, amount="-1000", quantity="10", asset_id=X),
    ]
    return _ledger(txs, date_to=GAP_TO, price_map=_closes(GAP_QUOTES))


BOOKS = [
    pytest.param(_weekday_book, WEEKDAY_FROM, WEEKDAY_TO, id="weekday-quotes"),
    pytest.param(_gap_book, GAP_FROM, GAP_TO, id="ten-day-gap"),
]


def test_the_books_are_what_the_docstring_says():
    """Preconditions on the hand calendar (green everywhere): the turns HEAD adds exist, and the gap is longer than the
    threshold while every weekend is not."""
    assert WEEKDAY_SPURIOUS_ON_HEAD, "the weekday book should give HEAD spurious turns"
    assert any(day.weekday() >= 5 for day in WEEKDAY_SPURIOUS_ON_HEAD), WEEKDAY_SPURIOUS_ON_HEAD
    assert GAP_TURN.weekday() == 5 and (GAP_RESUME - GAP_LAST_BEFORE).days > TURN
    assert all((later - earlier).days <= 3 for earlier, later in zip(WEEKDAY_QUOTES, WEEKDAY_QUOTES[1:], strict=False))
    assert WEEKDAY_QUOTES[-1] + timedelta(days=TURN) > WEEKDAY_TO
    assert GAP_QUOTES[-1] + timedelta(days=TURN) > GAP_TO


# =============================================================================
# 1. WEEKDAY QUOTES — NO WEEKEND NOVELTY
# =============================================================================


class TestWeekdayQuotes:
    def test_no_segment_starts_on_a_weekend(self):
        """RED on HEAD: the Saturdays 03-15, 03-22 and 03-29 (Friday quotes + 8) start a segment."""
        ds = _build(_weekday_book(), date_from=WEEKDAY_FROM).daily_states
        weekend_starts = [seg.start for seg in ds.segments if seg.start.weekday() >= 5]
        assert weekend_starts == [], f"segments start on a weekend: {weekend_starts}"

    def test_segment_starts_are_date_from_and_the_quote_days(self):
        """RED on HEAD: the extra starts are exactly every quote day + 8 that is no quote day."""
        ds = _build(_weekday_book(), date_from=WEEKDAY_FROM).daily_states
        starts = [seg.start for seg in ds.segments]
        expected = sorted({WEEKDAY_FROM, *WEEKDAY_QUOTES})
        assert starts == expected, f"extra starts {sorted(set(starts) - set(expected))}, missing {sorted(set(expected) - set(starts))}"
        assert ds.segments[-1].end == WEEKDAY_TO

    def test_no_day_is_stale(self):
        """Guard: with a quote at most three days old, X is never stale (the spurious turns change nothing)."""
        ds = _build(_weekday_book(), date_from=WEEKDAY_FROM).daily_states
        assert [state.date for state in ds if state.stale_price_asset_ids] == []


# =============================================================================
# 2. A TEN-DAY GAP — ONE TURN, WHERE THE FLAG FLIPS
# =============================================================================


class TestTenDayGap:
    def test_the_turn_after_the_gap_starts_a_segment(self):
        """Guard (green on HEAD too): last quote before the gap + 8, a Saturday, starts a segment."""
        ds = _build(_gap_book(), date_from=GAP_FROM).daily_states
        assert GAP_TURN in {seg.start for seg in ds.segments}

    def test_the_stale_flag_flips_on_the_turn_and_only_there(self):
        """Guard: X is stale from the turn to the day before the quotes resume, and on no other day."""
        ds = _build(_gap_book(), date_from=GAP_FROM).daily_states
        stale_days = [state.date for state in ds if X in state.stale_price_asset_ids]
        assert stale_days == _days(GAP_TURN, GAP_RESUME - timedelta(days=1))
        assert X not in ds.state_on(GAP_TURN - timedelta(days=1)).stale_price_asset_ids
        assert X in ds.state_on(GAP_TURN).stale_price_asset_ids

    def test_segment_starts_are_date_from_the_quote_days_and_the_one_turn(self):
        """RED on HEAD: 03-15 and 04-05 (Fridays + 8), 03-18..03-21 (the quotes of 03-10..03-13 + 8, although 03-14 is
        newer) and 04-08..04-10 are segment starts too."""
        ds = _build(_gap_book(), date_from=GAP_FROM).daily_states
        starts = [seg.start for seg in ds.segments]
        expected = sorted({GAP_FROM, *GAP_QUOTES, GAP_TURN})
        assert starts == expected, f"extra starts {sorted(set(starts) - set(expected))}, missing {sorted(set(expected) - set(starts))}"

    def test_no_weekend_start_but_the_turn(self):
        """RED on HEAD: Saturday 03-15 (Friday 03-07 + 8) starts a segment, although 03-10's quote is three days later."""
        ds = _build(_gap_book(), date_from=GAP_FROM).daily_states
        assert [seg.start for seg in ds.segments if seg.start.weekday() >= 5] == [GAP_TURN]


# =============================================================================
# 3. EVERY DAILY STATE UNCHANGED (GUARDS)
# =============================================================================


def _dense_result(monkeypatch, book, date_from: date) -> PortfolioCalculationResult:
    """The same book with every day of the frame computed: ``_collect_dirty_days`` wrapped to add every day (the
    oracle of "today's daily states", independent of which days the rule calls novelties)."""
    real = getattr(DailyStateBuilder, "_collect_dirty_days", None)
    assert real is not None, "the dense oracle wraps DailyStateBuilder._collect_dirty_days, which no longer exists"

    def every_day(self, *args, **kwargs):
        dirty = set(real(self, *args, **kwargs))
        dirty.update(_days(min(dirty | {self.date_from}), self.date_to))
        return dirty

    with monkeypatch.context() as patch:
        patch.setattr(DailyStateBuilder, "_collect_dirty_days", every_day)
        return _build(book(), date_from=date_from)


class TestDailyStatesUnchanged:
    @pytest.mark.parametrize(("book", "date_from", "date_to"), BOOKS)
    def test_stale_set_of_every_day_is_the_resolvers(self, book, date_from, date_to):
        ledger = book()
        ds = _build(ledger, date_from=date_from).daily_states
        mark_series = ledger["mark_series"]
        assert [state.date for state in ds] == _days(date_from, date_to)
        for state in ds:
            held = {aid for (aid, _bid), qty in _held_on(ledger, state.date).items() if qty > 0}
            expected = set()
            for aid in held:
                mark = mark_series[aid].resolve(state.date)
                days_back = mark.price_backward_fill.days_back if mark.price_backward_fill else 0
                if not mark.is_missing and days_back > STALE_PRICE_THRESHOLD_DAYS:
                    expected.add(aid)
            assert state.stale_price_asset_ids == expected, state.date

    @pytest.mark.parametrize(("book", "date_from", "date_to"), BOOKS)
    def test_every_day_equals_the_dense_run(self, monkeypatch, book, date_from, date_to):
        segmented = _build(book(), date_from=date_from).daily_states
        dense = _dense_result(monkeypatch, book, date_from).daily_states
        assert len(dense.segments) == len(_days(date_from, date_to)), "precondition: the oracle computes every day"
        assert len(segmented.segments) < len(dense.segments), "precondition: the book has quiet days"
        segmented_days, dense_days = list(segmented), list(dense)
        assert [s.date for s in segmented_days] == [s.date for s in dense_days] == _days(date_from, date_to)
        for got, want in zip(segmented_days, dense_days, strict=True):
            assert _state_fields(got) == _state_fields(want), got.date


def _held_on(ledger: dict, day: date) -> dict[tuple[int, int], Decimal]:
    """Quantity of every (asset, broker) at the end of ``day``, from the classified ledger."""
    held: dict[tuple[int, int], Decimal] = {}
    for ctxn in ledger["classified_txs"]:
        tx = ctxn.tx
        if tx.asset_id is not None and tx.date <= day and tx.quantity:
            key = (tx.asset_id, tx.broker_id)
            held[key] = held.get(key, Decimal(0)) + tx.quantity * ctxn.share
    return held

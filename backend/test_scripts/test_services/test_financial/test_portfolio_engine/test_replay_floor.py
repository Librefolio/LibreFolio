"""R13-SEC8-2 (MF-SEC8-2, MEDIUM, DoS) — a transaction dated long before 1900 no longer makes the replay walk every day since.

The defect. A transaction already stored with a date far in the past (``0001-01-01``, ``1800-01-01``; the write floor
N74, 1900 <= date, only guards the rows written from now on) made ``DailyStateBuilder.build`` walk every calendar day
from that date: ``_replay_from = min(date_from, *movement_days)``, then ``while current <= date_to`` visits each day, a
quiet one carried through ``dataclasses.replace`` (imported by name in ``daily_state``) even before ``date_from``, where
nothing is emitted; ``_valuation_rate_change_days`` builds ``_calendar(_replay_from - 1 day, date_to)`` for the
non-target currencies of prices and assets, and ``_calendar(start - 1 day, end)`` for each cash interval in transit —
with a movement dated exactly ``0001-01-01`` that is ``date.min - 1 day``: ``OverflowError`` (a 500).

The cure (``financial_math/portfolio/daily_state.py``): the quiet days before ``date_from`` are skipped — from one dirty
day to the next — so no state is carried there. The rows before 1900 are replayed exactly, on their own dates and in their
own order: quantities, cash, cost pools and the K/R/W pools at ``date_from`` are what they were.

MF-PAV-L1: the rate calendars no longer start at the floor ``EARLIEST_RANGE_START = date(1900, 1, 1)`` (``utils/datetime_utils.py``,
removed by D-P4 L5). They hold only the days a reading can change on (``_reading_calendar``), so a row stored
centuries back costs the days of its rate changes, never a calendar of every day since: each starts at the replay start
(``_replay_from``, the first movement's day), or at the cash transit's own start, and never earlier than one day before it.

- ``TestTheFloor`` — the constant is gone (D-P4 L5): a guard that ``datetime_utils`` has none. Every other test that names 1900 reads
  the literal ``date(1900, 1, 1)``; this one guards that the product's constant is not back.
- ``TestNoQuietDayBeforeDateFrom`` — red on HEAD: the ``replace`` calls made for days before ``date_from`` (a counting
  wrapper records each one's ``date=``) number 49 301 (date_from D2) / 49 302 (D3); after the cure, none. Since P4
  (MF5-1) the engine builds no quiet day at all (segments, ``StateSegment.state_on`` for a reader): the test counts
  ``state_on`` calls (none during ``build()``) and ``DailyPortfolioState`` constructions (one per computed day, those
  from ``date_from`` on being the segment starts); D4 and D6 lying inside a segment keeps it from passing vacuously.
- ``TestRateCalendarsStartAtTheReplayStart`` — RED on HEAD 999f1899e (MF-PAV-L1): a recording wrapper of
  ``DailyStateBuilder._reading_calendar`` (the candidate days only) sees the valuation calendar of the USD stock start on
  1900-01-01 (days from 1899-12-31) and the one of the USD cash in transit since 1890-01-02 start on 1900-01-01; after L1
  they start at the replay start 1890-01-01 (days from 1889-12-31, the day before the first movement) and at the transit's
  start 1890-01-02 (days from 1890-01-01). GREEN on HEAD (guard): no calendar starts before the day before the replay
  start. The precondition (the calendar of that currency still runs to its last day) keeps both from passing vacuously.
- ``TestAMovementOnDayOne`` — GREEN on HEAD and after (a guard): a movement dated ``date(1, 1, 1)`` beside a USD stock, and
  beside USD cash in transit since that day, build without ``OverflowError`` (``date.min - 1 day``), every row replayed on its
  own date (the conversions it misses are recorded on ``0001-01-01``).
- ``TestRowsBeforeTheFloorReplayedExactly`` — GREEN on HEAD and after (a guard of the cure): the numbers at
  ``date_from`` (quiet D2 and D3) pinned by hand, the 1890 rows included on their own dates and in their own order; and
  a ``period_start`` before the floor (before 1900, and before ``date_from``: the engine's case when the caller's period starts long before its window) still snapshotted.
  Mutation checks (applied in memory on top of a candidate cure): the 1890 rows folded onto 1900-01-01, the day-end
  clamp of K skipped before ``date_from``, the skip jumping over dirty days too, or from one movement day to the next —
  each turns it red.
- ``TestADateFromBeforeTheFirstMovement`` — GREEN on HEAD and after: a ``date_from`` earlier than the first movement
  emits every day from it, empty until the first movement, then the run from the first movement. (The «window equals
  full replay» invariant after the first movement is ``test_single_replay.py::TestWindowEqualsFullReplay``.)

The old book (target EUR; broker A = 10; X = 100 a EUR stock, Y = 200 a USD stock; exact-day USD->EUR rates):

- 1890-01-01 (O0): DEPOSIT 500, BUY 4 X for 400 — the day's additions first: K -400, then +500 = 100; cash 100.
- 1890-01-02 (O1): BUY 4 X for 400 — cash -300, K -300 clamped to 0 at the day's end.
- 1890-01-03 (O2): DEPOSIT 300 — cash 0, K 300.
- 1890-06-02 (O3): SELL 2 X for 300, cost 200 (8 X for 800) — cash 300, K 500, R 100; X 6 units, cost 600.
- 2025-01-01 (D0): DEPOSIT 1000 USD at 0.90 — cash 1200, K 1400, capital 1700 (500 + 300 + 900).
- 2025-01-02 (D1): BUY 5 Y for 500 USD at 0.95 (cost 475) — the cash's exchange result first: 300 EUR + 500 USD at
  0.95 = 775 against 725 booked, +50 to cash and R (150); then the BUY draws R's 150 and 325 of K: K 1075, R 0.
  X closes 120 EUR.
- 2025-01-03 (D2): quiet (no movement, no quote, the rate unchanged at 0.95).
- 2025-01-04 (D3): the dollar at 1.00: +25 on the cash (800) and R (25); Y closes 104 USD.
- 2025-01-06 (D5): the dollar at 0.98: -10 (cash 790, R 15). D4 and D6 are quiet.

Folded onto one day, the 1890 rows would run BUY, BUY, SELL, then the DEPOSITs: K 200 instead of 500 entering 2025, so
K 775 instead of 1075 at the end. Without the day-end clamp of O1: K 0 after O2, 200 after O3, 775 at the end.

Pure — no DB, no server, no network. Helpers are copies of test_single_replay.py (this directory has no cross-test-module
imports).
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, PortfolioCalculationResult, StateSegment
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 100
Y = 200

#: 1900-01-01, the date of the old floor ``EARLIEST_RANGE_START`` (gone, D-P4 L5; TestTheFloor guards it): a literal here.
FLOOR = date(1900, 1, 1)
DAY_ONE = date(1, 1, 1)

O0 = date(1890, 1, 1)
O1 = date(1890, 1, 2)
O2 = date(1890, 1, 3)
O3 = date(1890, 6, 2)

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
D6 = date(2025, 1, 7)

# =============================================================================
# HELPERS — copies of test_single_replay.py
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date = D0,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies):
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
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder_kwargs(**overrides) -> dict:
    """DailyStateBuilder kwargs: defaults, overrides, then the mark series, average costs and native cash."""
    kwargs = {
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
        "date_from": D0,
        "date_to": D0,
    }
    kwargs.update(overrides)
    kwargs.setdefault("mark_series", _mark_series_from(kwargs["classified_txs"], kwargs["price_map"], kwargs["asset_currencies"]))
    kwargs.setdefault(
        "average_costs",
        engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]),
    )
    kwargs.setdefault("native_cash", engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]))
    return kwargs


def _classify(txs, scope):
    """Run the real classifier, transactions in loading order (date, id), share 1."""
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict.fromkeys(scope, Decimal("1")),
    )
    return classifier.classify()


def _ledger(txs, scope, *, date_to, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder overrides of a classified ledger (``date_from`` is the test's to set); every asset is a "Stock"."""
    classification = _classify(txs, scope)
    price_map = price_map or {}
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "fx_rate_map": fx_rate_map or {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR") | (asset_currencies or {}),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "date_to": date_to,
    }


def _prices(asset_id: int, currency: str, closes: dict[date, str]) -> dict[int, list[tuple[date, Decimal, str]]]:
    return {asset_id: [(day, Decimal(close), currency) for day, close in sorted(closes.items())]}


def _usd_rates(rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    """USD->EUR on the given days only (the map is exact-day: any other day has no rate)."""
    return {("USD", "EUR", day): Decimal(rate) for day, rate in rates.items()}


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _state(result: PortfolioCalculationResult, day: date) -> DailyPortfolioState:
    return next(s for s in result.daily_states if s.date == day)


_RATES_2025 = {D0: "0.90", D1: "0.95", D2: "0.95", D3: "1.00", D4: "1.00", D5: "0.98", D6: "0.98"}

# =============================================================================
# BOOKS
# =============================================================================


def _old_book() -> dict:
    """The module's book (see the docstring): 1890 rows on X in EUR, then a USD deposit and a USD stock in 2025."""
    txs = [
        _tx(id=1, dt=O0, amount="500"),
        _tx(id=2, type="BUY", dt=O0, amount="-400", quantity="4", asset_id=X),
        _tx(id=3, type="BUY", dt=O1, amount="-400", quantity="4", asset_id=X),
        _tx(id=4, dt=O2, amount="300"),
        _tx(id=5, type="SELL", dt=O3, amount="300", quantity="-2", asset_id=X),
        _tx(id=6, dt=D0, amount="1000", currency="USD"),
        _tx(id=7, type="BUY", dt=D1, amount="-500", currency="USD", quantity="5", asset_id=Y),
    ]
    prices = _prices(X, "EUR", {D1: "120"}) | _prices(Y, "USD", {D3: "104"})
    return _ledger(txs, {A}, date_to=D6, price_map=prices, fx_rate_map=_usd_rates(_RATES_2025), asset_currencies={Y: "USD"})


def _old_transit_book() -> dict:
    """A deposits 1000 USD on 1890-01-01 (no rate that day: a missing conversion); 400 USD leave A on 1890-01-02 and
    reach B on D1 — USD cash in transit from 1890-01-02 to D0. No asset: the only rate calendar is the transit's."""
    txs = [
        _tx(id=1, dt=O0, amount="1000", currency="USD"),
        _tx(id=2, type="CASH_TRANSFER", dt=O1, amount="-400", currency="USD", related_id=3),
        _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=D1, amount="400", currency="USD", related_id=2),
    ]
    return _ledger(txs, {A, B}, date_to=D6, fx_rate_map=_usd_rates(_RATES_2025))


def _day_one_stock_book() -> dict:
    """A deposits 1000 and buys 5 Y (a USD stock) for 500 EUR on 0001-01-01; Y closes 104 USD on D1."""
    txs = [
        _tx(id=1, dt=DAY_ONE, amount="1000"),
        _tx(id=2, type="BUY", dt=DAY_ONE, amount="-500", quantity="5", asset_id=Y),
    ]
    rates = {day: rate for day, rate in _RATES_2025.items() if day <= D3}
    return _ledger(txs, {A}, date_to=D3, price_map=_prices(Y, "USD", {D1: "104"}), fx_rate_map=_usd_rates(rates), asset_currencies={Y: "USD"})


def _day_one_transit_book() -> dict:
    """A deposits 1000 USD on 0001-01-01 and 400 USD leave it that day, reaching B on D1 (no rate before D0: both
    0001-01-01 conversions are missing). USD cash in transit from 0001-01-01 to D0."""
    txs = [
        _tx(id=1, dt=DAY_ONE, amount="1000", currency="USD"),
        _tx(id=2, type="CASH_TRANSFER", dt=DAY_ONE, amount="-400", currency="USD", related_id=3),
        _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=D1, amount="400", currency="USD", related_id=2),
    ]
    rates = {day: rate for day, rate in _RATES_2025.items() if day <= D3}
    return _ledger(txs, {A, B}, date_to=D3, fx_rate_map=_usd_rates(rates))


def _build(ledger: dict, date_from: date, **overrides) -> PortfolioCalculationResult:
    return DailyStateBuilder(**_builder_kwargs(**ledger, date_from=date_from, **overrides)).build()


# =============================================================================
# THE FLOOR
# =============================================================================


class TestTheFloor:
    def test_datetime_utils_has_no_earliest_range_start(self):
        """D-P4 L5: ``EARLIEST_RANGE_START`` is gone from ``datetime_utils``: no portfolio walk has a floor, so the 1900
        every other test here names is a literal of the test and the module offers no constant to read it from."""
        from backend.app.utils import datetime_utils  # noqa: PLC0415 — read at run time

        assert not hasattr(datetime_utils, "EARLIEST_RANGE_START")


# =============================================================================
# (b) NO STATE IS CARRIED THROUGH A QUIET DAY BEFORE date_from
# =============================================================================


class TestNoQuietDayBeforeDateFrom:
    @pytest.mark.parametrize("date_from", [pytest.param(D2, id="quiet-date_from"), pytest.param(D3, id="rate-change-date_from")])
    def test_no_state_is_carried_before_date_from(self, monkeypatch, date_from):
        """A quiet day before ``date_from`` is skipped, not carried. HEAD 94e170ae1 carried every quiet day from 1890-01-01
        on through ``replace`` — about 49 000 calls. Since P4 (MF5-1) the engine builds no quiet day at all: it keeps one
        ``StateSegment`` per computed day from ``date_from`` on, and a reader builds a quiet day through
        ``StateSegment.state_on``. So during ``build()``: no ``state_on`` call; one ``DailyPortfolioState`` constructed per
        computed day (``dataclasses.replace`` constructs through ``__init__`` too), those from ``date_from`` on being
        exactly the segment starts; the few before it are the old rows' own days, each once. D4 and D6 are quiet: they lie
        inside a segment, so the quiet path is still exercised (by the readers, not by the build)."""
        built: list[date] = []
        materialized: list[date] = []
        real_init = DailyPortfolioState.__init__
        real_state_on = StateSegment.state_on

        def counting_init(self, *args, **kwargs):
            real_init(self, *args, **kwargs)
            built.append(self.date)

        def counting_state_on(self, day):
            materialized.append(day)
            return real_state_on(self, day)

        monkeypatch.setattr(DailyPortfolioState, "__init__", counting_init)
        monkeypatch.setattr(StateSegment, "state_on", counting_state_on)

        result = _build(_old_book(), date_from)
        built_during_build, materialized_during_build = list(built), list(materialized)

        starts = [segment.start for segment in result.daily_states.segments]
        assert starts[:1] == [date_from], f"the first segment starts on {starts[:1]}, not on date_from {date_from}"
        assert [start for start in starts if start < date_from] == [], "no segment starts before date_from"
        assert not {D4, D6} & set(starts), f"precondition: D4 and D6 are quiet days, inside a segment; starts {starts}"
        assert [s.date for s in result.daily_states] == _days(date_from, D6), "every day from date_from is emitted"
        assert materialized_during_build == [], f"build() materialized {len(materialized_during_build)} quiet days"
        assert sorted(day for day in built_during_build if day >= date_from) == starts, "one state constructed per computed day from date_from on"
        before = [day for day in built_during_build if day < date_from]
        assert len(before) == len(set(before)) and len(before) < 20, f"{len(before)} states constructed before date_from {date_from}, from {min(before, default=None)} to {max(before, default=None)}"


# =============================================================================
# (c) THE RATE CALENDARS START AT THE REPLAY START
# =============================================================================


def _recording_calendar(monkeypatch) -> list[tuple[frozenset[str], date, date, list[date]]]:
    """Wrap ``DailyStateBuilder._reading_calendar``: every ``(currencies, first, last, days read)``, in order.

    MF5-2a: the rate calendars hold only the days a reading can change on (``_reading_calendar``, which starts at
    ``first`` - 1 day unless ``first`` is ``date.min``); before it, ``daily_state._calendar`` gave every day.
    """
    calls: list[tuple[frozenset[str], date, date, list[date]]] = []
    real_reading_calendar = DailyStateBuilder._reading_calendar

    def recording(self, currencies, first, last):
        days = real_reading_calendar(self, currencies, first, last)
        calls.append((frozenset(currencies), first, last, list(days)))
        return days

    monkeypatch.setattr(DailyStateBuilder, "_reading_calendar", recording)
    return calls


class TestRateCalendarsStartAtTheReplayStart:
    """The old book's replay starts on its first movement, 1890-01-01 (O0): ``_replay_from = min(date_from, movement days)``.
    The USD stock's valuation calendar starts there (``first`` = O0, days from 1889-12-31); the USD cash in transit since
    1890-01-02 gets its own, from the transit's start (``first`` = O1, days from O0)."""

    @pytest.mark.parametrize(
        ("ledger", "last_day", "first_day"),
        [
            pytest.param(_old_book, D6, O0, id="valuation-calendar-of-a-usd-stock"),
            pytest.param(_old_transit_book, D0, O1, id="usd-cash-in-transit-since-1890"),
        ],
    )
    def test_the_calendar_starts_at_the_replay_start_not_at_the_floor(self, monkeypatch, ledger, last_day, first_day):
        """RED on HEAD (MF-PAV-L1): HEAD clamps ``first`` to 1900-01-01, so the calendar holds nothing before 1899-12-31 and
        the 1890 days — the first movement's, the transit's own — are never read. After L1 the calendar of USD that runs to
        ``last_day`` starts at ``first_day`` and its first day is the day before it."""
        calls = _recording_calendar(monkeypatch)

        _build(ledger(), D3)

        asked = [(sorted(currencies), first, last, days[:1]) for currencies, first, last, days in calls]
        usd_to_the_end = [(first, days) for currencies, first, last, days in calls if "USD" in currencies and last == last_day and days]
        assert usd_to_the_end, f"precondition: a USD calendar runs to {last_day}, calendars asked: {asked}"
        assert [(first, days[0]) for first, days in usd_to_the_end] == [(first_day, first_day - timedelta(days=1))] * len(
            usd_to_the_end
        ), f"USD calendars to {last_day} start at (first, first day read) {[(first, days[0]) for first, days in usd_to_the_end]}, expected the replay start {first_day} and the day before it"

    @pytest.mark.parametrize(
        ("ledger", "last_day"),
        [
            pytest.param(_old_book, D6, id="valuation-calendar-of-a-usd-stock"),
            pytest.param(_old_transit_book, D0, id="usd-cash-in-transit-since-1890"),
        ],
    )
    def test_guard_no_calendar_starts_before_the_day_before_the_replay_start(self, monkeypatch, ledger, last_day):
        """GUARD (green on HEAD too): the replay starts on 1890-01-01, so no calendar asks a day before 1889-12-31 — a row
        centuries back costs the days a reading can change on, never a calendar from before its own date."""
        calls = _recording_calendar(monkeypatch)

        _build(ledger(), D3)

        asked = [(sorted(currencies), first, last, days[:1]) for currencies, first, last, days in calls]
        assert any("USD" in currencies and last == last_day and days for currencies, _first, last, days in calls), f"precondition: a USD calendar runs to {last_day}, calendars asked: {asked}"
        early = [(sorted(currencies), first, days[:1]) for currencies, first, _last, days in calls if first < O0 or (days and days[0] < O0 - timedelta(days=1))]
        assert early == [], f"rate calendars starting before {O0 - timedelta(days=1)}: {early}"


# =============================================================================
# date(1, 1, 1): NO OVERFLOW
# =============================================================================


class TestAMovementOnDayOne:
    def test_a_movement_on_day_one_beside_a_usd_stock_is_replayed(self):
        """GUARD (green on HEAD and after): no ``OverflowError`` (``date(1, 1, 1) - 1 day``) from the stock's valuation
        calendar, now that it starts at the replay start, which is day one. The states from D0, the day-one rows in them — cash
        500, the 5 Y at their cost of 500."""
        result = _build(_day_one_stock_book(), D0)

        assert [s.date for s in result.daily_states] == _days(D0, D3)
        first = _state(result, D0)
        assert (first.cash_value, first.open_cost_basis, first.cumulative_external_cash_flow) == (Decimal("500"), Decimal("500"), Decimal("1000"))
        assert result.end_state.cumulative_qty == {(Y, A): Decimal("5")}

    def test_usd_cash_in_transit_since_day_one_is_replayed(self):
        """GUARD (green on HEAD and after): no ``OverflowError`` from the transit's calendar (``start - 1 day``, start
        0001-01-01), which now starts at the transit's own start. The states from D2; both day-one conversions are missing,
        recorded on their own date."""
        result = _build(_day_one_transit_book(), D2)

        assert [s.date for s in result.daily_states] == _days(D2, D3)
        assert DAY_ONE in result.missing_fx.get("USD/EUR", set()), f"the day-one rows are replayed on their own date: {result.missing_fx}"


# =============================================================================
# GUARD: THE ROWS BEFORE THE FLOOR ARE REPLAYED EXACTLY
# =============================================================================


class TestRowsBeforeTheFloorReplayedExactly:
    """GREEN on HEAD and after: the numbers of the module's book (worked out in the module docstring)."""

    @pytest.mark.parametrize("date_from", [pytest.param(D2, id="quiet-date_from"), pytest.param(D3, id="rate-change-date_from")])
    def test_the_numbers_from_date_from_include_the_1890_rows(self, date_from):
        result = _build(_old_book(), date_from)

        assert [s.date for s in result.daily_states] == _days(date_from, D6)
        d3 = _state(result, D3)
        assert (d3.cash_value, d3.open_cost_basis, d3.cumulative_external_cash_flow) == (Decimal("800"), Decimal("1075"), Decimal("1700"))
        assert (d3.market_value, d3.nav_value, d3.total_pnl) == (Decimal("1240"), Decimal("2040"), Decimal("340")), "X 6 x 120, Y 5 x 104 USD at 1.00"
        start = {(position.asset_id, position.broker_id): (position.quantity, position.cost_basis) for position in result.position_states_start}
        assert result.position_states_start_date == date_from
        assert start == {(X, A): (Decimal("6"), Decimal("600")), (Y, A): (Decimal("5"), Decimal("475"))}
        end = result.end_state
        assert (end.capital_pool, end.returns_pool, end.withdrawn_pool) == ({A: Decimal("1075")}, {A: Decimal("15")}, Decimal("0")), "K and R carry the 1890 rows' order and day-end clamps"
        assert (end.cumulative_cash, end.cumulative_ecf) == (Decimal("790"), Decimal("1700"))
        assert end.cumulative_qty == {(X, A): Decimal("6"), (Y, A): Decimal("5")}
        sales = [(sale.transaction_id, sale.date, sale.quantity, sale.proceeds, sale.cost) for sale in result.realized_sales]
        assert sales == [(5, O3, Decimal("2"), Decimal("300"), Decimal("200"))], "the 1890 SELL, on its own date"
        assert result.missing_fx == {}

    def test_a_quiet_date_from_starts_from_the_previous_days_numbers(self):
        """date_from D2, a quiet day: the D1 numbers — cash 775, Y 5 x 100 USD (the BUY's price) at 0.95."""
        d2 = _state(_build(_old_book(), D2), D2)

        assert (d2.cash_value, d2.open_cost_basis, d2.market_value, d2.nav_value) == (Decimal("775"), Decimal("1075"), Decimal("1195"), Decimal("1970"))

    def test_a_period_start_before_the_floor_is_still_snapshotted(self):
        """``period_start`` 1895-01-01, a quiet day before the floor and before ``date_from`` (the engine's case when the
        caller's period starts before its window: ``calculate(date_from=…, period_start=<the caller's start>)``): the snapshot is
        taken at its end — 6 X at their cost of 600 — though no state is emitted there. A skip that jumped from one
        movement to the next would pass it by."""
        period_start = date(1895, 1, 1)

        result = _build(_old_book(), D3, period_start=period_start)

        assert result.position_states_start_date == period_start
        assert [(p.date, p.asset_id, p.broker_id, p.quantity, p.cost_basis) for p in result.position_states_start] == [(period_start, X, A, Decimal("6"), Decimal("600"))]
        assert result.daily_states[0].date == D3


# =============================================================================
# GUARD: A date_from BEFORE THE FIRST MOVEMENT
# =============================================================================


class TestADateFromBeforeTheFirstMovement:
    def test_every_day_from_date_from_is_emitted_and_the_rest_is_the_run_from_the_first_movement(self):
        """The 2025 rows of the book, ``date_from`` three days before D0: those three days are emitted empty, then the
        states equal, day by day, those of the run from D0. Nothing before ``date_from`` exists to be skipped."""
        txs = [
            _tx(id=6, dt=D0, amount="1000", currency="USD"),
            _tx(id=7, type="BUY", dt=D1, amount="-500", currency="USD", quantity="5", asset_id=Y),
        ]
        ledger = _ledger(txs, {A}, date_to=D6, price_map=_prices(Y, "USD", {D3: "104"}), fx_rate_map=_usd_rates(_RATES_2025), asset_currencies={Y: "USD"})
        early = D0 - timedelta(days=3)

        from_early = _build(ledger, early)
        from_first = _build(ledger, D0)

        assert [s.date for s in from_early.daily_states] == _days(early, D6)
        assert all((s.cash_value, s.nav_value, s.cumulative_external_cash_flow) == (0, 0, 0) for s in from_early.daily_states if s.date < D0)
        assert [s for s in from_early.daily_states if s.date >= D0] == from_first.daily_states

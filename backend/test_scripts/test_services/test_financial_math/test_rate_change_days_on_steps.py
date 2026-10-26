"""MF5-2a — the portfolio engine's last day-by-day walk reads only the days on which a rate can change.

Workstream MF (release 1.3), lot MF5-2a. Pure: no database, no server, no network; steps built by hand.

WHY. ``DailyStateBuilder._valuation_rate_change_days`` (``financial_math/portfolio/daily_state.py``) finds the frame days
on which a rate the valuation reads changes from the day before. Today (HEAD ``352d48ff3``) it builds
``_calendar(replay_from - 1 day, date_to)`` — every calendar day — and hands it to ``native_cash.change_days`` with
``self._read_rate`` (``fx_rate_map.get((currency, target, day))``), once for the currencies of the securities and once
per cash in-transit interval. A book with a deposit on 1900-01-02 and activity in 2025 is read on ~46 000 days per
currency, although the map changes on a handful of them. And ``replay_from - timedelta(days=1)`` raises
``OverflowError`` on ``date.min`` once a date floor is lowered. Since D-P4 / MF-PAV-L1 the floor is gone: the calendars
start at ``builder._replay_from`` (the earliest movement, or ``date_from``), even in year 1.

THE CONTRACT (MF5-2a):

1. ``AskedDayRates.reading_change_days(source, destination=None) -> tuple[date, ...]`` (``financial_math/fx_rates.py``;
   ``destination`` defaults to ``fixed_destination``; with a fixed destination another destination gives ``()``):
   ascending, unique; it contains every day d on which the view's reading of the pair (``get`` with the view's own key
   format) differs from its reading on d - 1 day, and only days that are a step day inside an asked window, an asked
   window's first day, or the day after an asked window's last day. A pair with no steps or no windows gives ``()``.
2. ``DailyStateBuilder._valuation_rate_change_days()`` returns exactly the set HEAD returns, for any ``fx_rate_map`` (an
   ``AskedDayRates`` or a plain dict keyed ``(currency, target, day)``), but reads only candidate days: the reads are
   bounded by a small multiple of the candidate days (rate keys / steps / window bounds, + 2 per in-transit interval),
   not by the calendar length.
3. With no date floor (D-P4, MF-PAV-L1) a movement on ``date(1, 1, 1)`` makes the method (and ``build()``) read from
   ``date.min`` without raising, and the reads stay bounded by the candidate days, not by the ~740 000 calendar days to
   today; the same for a cash in-transit interval starting on ``date(1, 1, 1)``. The calendar starts at the replay start,
   never at 1900.

What is tested:

- ``TestReadingChangeDays`` — 60 seeded random views (steps before / inside / after the windows, a step equal to the
  previous value — ``1.1`` then ``1.10`` —, ``None`` before the first step, gaps, touching and overlapping windows that
  ``merged_windows`` joins, a reversed window), both key formats, every pair compared with a dense scan of ``get`` over a
  range covering everything by more than 3 days; hand cases; the fixed-destination rules; a window on ``date.min``.
- ``TestBuilderEquivalence`` — ``_valuation_rate_change_days()`` against an independent dense reference written here
  (the dense algorithm: every day from ``replay_from`` - 1, plus each cash in-transit interval; no date floor), on named builders (dict and
  ``AskedDayRates`` maps; a foreign security; a foreign quote currency; cash in transit in a foreign currency, clipped,
  ignored when of an asset or in the report currency, or empty; a replay that starts before ``date_from``; ``date_from``
  on a rate change) and on 40 seeded random builders per map kind: these pin that the cure changes no day.
- ``TestReadCost`` — the cost guarantee: ``_read_rate`` calls, map lookups and steps ``at`` calls during one call are at
  most 50 × the candidate days and at most 5 000, from 1900 and from ``date.min`` (dict book through ``build()``, view with
  a long cash in-transit interval, both maps over the ~740 000 days from year 1 to today). A walk of the calendar would read
  ~2 × 46 000 (dict book), ~137 000 (view with a long transit), ~740 000 (from year 1).
- ``TestDateMin`` — no floor: with a movement on ``date(1, 1, 1)`` the method (dict map, view map, cash in transit from
  ``date.min``) and ``build()`` do not raise and equal the dense reference from ``date.min`` (no day before it: a rate on
  ``date.min`` counts as a change there). Plus the opposite of the old guard: a movement on year 1 reads from year 1, the
  calendar starts at the replay start, not on 1 January 1900. A walk that computes ``replay_from - timedelta(days=1)``
  raises ``OverflowError`` there.

Note on ``_replay_from``: ``build()`` sets it (the earliest movement, or ``date_from``) before calling the method; the
method-level tests set it directly, as ``build()`` would, to keep each case to the method's own inputs. The build-level
tests (``test_cost_dict_book_through_build``, ``test_build_does_not_raise_on_date_min``) take it from a real book.

History: written red on HEAD ``352d48ff3`` (MF5-2a); the oracles read the 1900 floor until MF-PAV-L1 removed it (D-P4):
now they start at ``_replay_from``.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory);
alone: ``./dev.py test services financial-math test_rate_change_days_on_steps``.

Reference: backend/app/services/financial_math/portfolio/daily_state.py (_valuation_rate_change_days, _read_rate,
_calendar), backend/app/services/financial_math/fx_rates.py (AskedDayRates, merged_windows, UnitRateReader),
backend/app/services/financial_math/native_cash.py (change_days).
"""

from __future__ import annotations

import random
from bisect import bisect_right
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.fx_rates import AskedDayRates
from backend.app.services.financial_math.native_cash import NativeCash
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import InTransitInterval
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

Pair = tuple[str, str]
Window = tuple[date, date]

REPORT = "EUR"
ONE_DAY = timedelta(days=1)
A, B = 10, 20
X, Y = 100, 200
# 1.1 and 1.10 are the same number: a step that does not change the reading
VALUES = (Decimal("1.1"), Decimal("1.10"), Decimal("1.2"), Decimal("0.987654321"), Decimal("1.3"))
READ_FACTOR = 50
READ_CAP = 5_000


# =============================================================================
# STEPS, VIEWS AND THE CURE'S NAME
# =============================================================================


class _Steps:
    """A ``UnitRateReader``: the last step on or before the day, None before the first. Counts its ``at`` calls."""

    def __init__(self, points: Mapping[date, Decimal]) -> None:
        ordered = sorted(points.items())
        self.days = tuple(day for day, _value in ordered)
        self.values = tuple(value for _day, value in ordered)
        self.calls = 0

    def at(self, day: date) -> Decimal | None:
        self.calls += 1
        index = bisect_right(self.days, day) - 1
        return self.values[index] if index >= 0 else None


class _CountingView(AskedDayRates):
    """An ``AskedDayRates`` that counts its lookups (``get`` goes through ``__getitem__``)."""

    lookups = 0

    def __getitem__(self, key: tuple) -> Decimal:
        self.lookups += 1
        return super().__getitem__(key)


class _CountingDict(dict):
    """A dict rate map that counts its lookups."""

    lookups = 0

    def get(self, key, default=None):
        self.lookups += 1
        return super().get(key, default)

    def __getitem__(self, key):
        self.lookups += 1
        return super().__getitem__(key)

    def __contains__(self, key):
        self.lookups += 1
        return super().__contains__(key)


def _reading_change_days(view: AskedDayRates, *args: str) -> tuple[date, ...]:
    """``view.reading_change_days(*args)``, read when a test runs: before the cure each test fails here, by absence."""
    method = getattr(view, "reading_change_days", None)
    if method is None:
        pytest.fail("MF5-2a: AskedDayRates has no reading_change_days yet (red by absence, before the cure)")
    return method(*args)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _key(source: str, destination: str, day: date, fixed: str | None) -> tuple:
    return (source, day) if fixed is not None else (source, destination, day)


def _dense_changes(view: Mapping, source: str, destination: str, fixed: str | None, first: date, last: date) -> set[date]:
    """Every day of [first, last] whose ``get`` differs from the day before's (numeric comparison, None included)."""
    previous = view.get(_key(source, destination, first - ONE_DAY, fixed))
    changed: set[date] = set()
    for day in _days(first, last):
        current = view.get(_key(source, destination, day, fixed))
        if current != previous:
            changed.add(day)
        previous = current
    return changed


def _candidates(steps: Mapping[Pair, _Steps], windows: Mapping[Pair, Sequence[Window]], pair: Pair) -> set[date]:
    """The days the contract allows: a step day inside an asked window, a window's first day, the day after its last."""
    asked = [(first, last) for first, last in windows.get(pair, ()) if first <= last]
    reader = steps.get(pair)
    if reader is None or not asked:
        return set()
    allowed = {first for first, _last in asked} | {last + ONE_DAY for _first, last in asked}
    allowed.update(day for day in reader.days if any(first <= day <= last for first, last in asked))
    return allowed


def _change_day_problems(label: str, result: object, changes: set[date], allowed: set[date]) -> list[str]:
    problems: list[str] = []
    if not isinstance(result, tuple):
        return [f"{label}: not a tuple: {type(result).__name__}"]
    if list(result) != sorted(set(result)):
        problems.append(f"{label}: not ascending and unique: {result}")
    missing = sorted(changes - set(result))
    if missing:
        problems.append(f"{label}: misses reading changes {missing[:6]}")
    extra = sorted(set(result) - allowed)
    if extra:
        problems.append(f"{label}: days that are no step in a window nor a window bound {extra[:6]}")
    return problems


# =============================================================================
# 1. reading_change_days
# =============================================================================

BASE = date(2024, 3, 1)
PAIRS: tuple[Pair, ...] = (("USD", "EUR"), ("GBP", "EUR"), ("USD", "GBP"), ("CHF", "EUR"))


def _random_view_case(seed: int) -> tuple[dict[Pair, _Steps], dict[Pair, list[Window]]]:
    rng = random.Random(seed)
    steps: dict[Pair, _Steps] = {}
    windows: dict[Pair, list[Window]] = {}
    for pair in PAIRS:
        if rng.random() < 0.85:
            offsets = rng.sample(range(-6, 46), rng.randint(0, 7))
            steps[pair] = _Steps({BASE + timedelta(days=offset): rng.choice(VALUES) for offset in offsets})
        if rng.random() < 0.85:
            spans: list[tuple[int, int]] = []
            for _ in range(rng.randint(0, 5)):
                first = rng.randint(-4, 40)
                spans.append((first, first + rng.randint(0, 9)))
            if spans and rng.random() < 0.5:  # touching: merged
                last = spans[-1][1]
                spans.append((last + 1, last + 1 + rng.randint(0, 4)))
            if spans and rng.random() < 0.5:  # overlapping: merged
                first, last = spans[0]
                spans.append((first + (last - first) // 2, last + rng.randint(0, 5)))
            if rng.random() < 0.2:  # reversed: holds no day
                spans.append((12, 8))
            rng.shuffle(spans)
            windows[pair] = [(BASE + timedelta(days=first), BASE + timedelta(days=last)) for first, last in spans]
    return steps, windows


def _view_problems(steps: dict[Pair, _Steps], windows: dict[Pair, list[Window]], fixed: str | None, label: str) -> list[str]:
    view = AskedDayRates(steps, windows) if fixed is None else AskedDayRates(steps, windows, fixed_destination=fixed)
    first, last = BASE - timedelta(days=12), BASE + timedelta(days=62)
    problems: list[str] = []
    for pair in PAIRS:
        source, destination = pair
        if fixed is not None and destination != fixed:
            result = _reading_change_days(view, source, destination)
            if result != ():
                problems.append(f"{label} {pair}: another destination than the fixed one gives {result}, not ()")
            continue
        result = _reading_change_days(view, source, destination)
        changes = _dense_changes(view, source, destination, fixed, first, last)
        allowed = _candidates(steps, windows, pair)
        problems += _change_day_problems(f"{label} {pair}", result, changes, allowed)
        if not allowed and result != ():
            problems.append(f"{label} {pair}: no steps or no windows, yet {result}")
        if fixed is not None and _reading_change_days(view, source) != result:
            problems.append(f"{label} {pair}: the destination does not default to the fixed one")
    return problems


class TestReadingChangeDays:
    """``AskedDayRates.reading_change_days``: every day the view's reading changes, and only candidate days."""

    @pytest.mark.parametrize("fixed", [None, REPORT], ids=["three-part-keys", "fixed-destination"])
    def test_random_views_against_a_dense_scan(self, fixed: str | None) -> None:
        problems: list[str] = []
        for seed in range(60):
            steps, windows = _random_view_case(seed)
            problems += _view_problems(steps, windows, fixed, f"seed {seed}")
        assert not problems, "\n".join(problems[:20])

    def test_steps_before_inside_and_after_one_window(self) -> None:
        """Window [d3, d12]; steps d5 1.1, d8 1.2, d15 1.3. Reading: None to d4, 1.1 d5-d7, 1.2 d8-d12, None from d13."""
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        steps = {("USD", REPORT): _Steps({day(5): Decimal("1.1"), day(8): Decimal("1.2"), day(15): Decimal("1.3")})}
        view = AskedDayRates(steps, {("USD", REPORT): [(day(3), day(12))]})
        result = _reading_change_days(view, "USD", REPORT)
        assert {day(5), day(8), day(13)} <= set(result) <= {day(3), day(5), day(8), day(13)}, result

    def test_a_window_after_the_only_step(self) -> None:
        """A step on d0 read only in [d10, d12]: the rate appears on d10 and disappears on d13 — exactly those."""
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        view = AskedDayRates({("USD", REPORT): _Steps({day(0): Decimal("1.1")})}, {("USD", REPORT): [(day(10), day(12))]})
        assert _reading_change_days(view, "USD", REPORT) == (day(10), day(13))

    def test_touching_and_overlapping_windows_read_as_one(self) -> None:
        """Windows [d1, d3], [d4, d6] (touching) and [d5, d8] (overlapping), one step before them: in on d1, out on d9."""
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        steps = {("USD", REPORT): _Steps({day(0): Decimal("1.1")})}
        view = AskedDayRates(steps, {("USD", REPORT): [(day(5), day(8)), (day(1), day(3)), (day(4), day(6))]})
        result = _reading_change_days(view, "USD", REPORT)
        assert {day(1), day(9)} <= set(result) <= {day(1), day(4), day(5), day(7), day(9)}, result
        assert day(1) in result and day(9) in result

    def test_an_equal_step_is_no_reading_change(self) -> None:
        """Steps 1.1 on d2 and 1.10 on d4 in the window [d0, d6]: the reading changes on d2 and d7 only (d4 is allowed)."""
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        steps = {("USD", REPORT): _Steps({day(2): Decimal("1.1"), day(4): Decimal("1.10")})}
        view = AskedDayRates(steps, {("USD", REPORT): [(day(0), day(6))]})
        result = _reading_change_days(view, "USD", REPORT)
        assert {day(2), day(7)} <= set(result) <= {day(0), day(2), day(4), day(7)}, result

    def test_no_steps_or_no_windows_give_nothing(self) -> None:
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        view = AskedDayRates({("USD", REPORT): _Steps({day(0): Decimal("1.1")})}, {("GBP", REPORT): [(day(0), day(5))]})
        assert _reading_change_days(view, "USD", REPORT) == ()
        assert _reading_change_days(view, "GBP", REPORT) == ()
        assert _reading_change_days(view, "CHF", REPORT) == ()
        empty_steps = AskedDayRates({("USD", REPORT): _Steps({})}, {("USD", REPORT): [(day(0), day(5))]})
        assert _reading_change_days(empty_steps, "USD", REPORT) == ()

    def test_fixed_destination_reads_its_own_pairs_only(self) -> None:
        day = lambda offset: BASE + timedelta(days=offset)  # noqa: E731
        steps = {("USD", REPORT): _Steps({day(1): Decimal("1.1")}), ("USD", "GBP"): _Steps({day(1): Decimal("0.8")})}
        windows = {("USD", REPORT): [(day(0), day(3))], ("USD", "GBP"): [(day(0), day(3))]}
        view = AskedDayRates(steps, windows, fixed_destination=REPORT)
        assert _reading_change_days(view, "USD") == _reading_change_days(view, "USD", REPORT)
        assert {day(1), day(4)} <= set(_reading_change_days(view, "USD")) <= {day(0), day(1), day(4)}
        assert _reading_change_days(view, "USD", "GBP") == ()

    def test_a_window_on_the_first_day_of_the_calendar(self) -> None:
        """A step and a window from ``date.min``: no OverflowError; the rate disappears the day after the window."""
        steps = {("USD", REPORT): _Steps({date.min: Decimal("1.1"), date.min + timedelta(days=4): Decimal("1.2")})}
        view = AskedDayRates(steps, {("USD", REPORT): [(date.min, date.min + timedelta(days=10))]})
        result = _reading_change_days(view, "USD", REPORT)
        changes = _dense_changes(view, "USD", REPORT, None, date.min + ONE_DAY, date.min + timedelta(days=20))
        problems = _change_day_problems("date.min", result, changes, _candidates(steps, {("USD", REPORT): [(date.min, date.min + timedelta(days=10))]}, ("USD", REPORT)))
        assert not problems, "\n".join(problems)


# =============================================================================
# 2. THE BUILDER: THE SAME DAYS AS HEAD
# =============================================================================


def _cash_interval(start: date, end: date, currency: str | None, tx_type: str = "cash") -> InTransitInterval:
    leg = SimpleNamespace(currency=currency)
    return InTransitInterval(start_date=start, end_date=end, tx_type=tx_type, departure_leg=leg, arrival_leg=leg, share=Decimal("1"))  # type: ignore[arg-type]


def _builder(
    *,
    fx_rate_map: Mapping,
    replay_from: date,
    date_to: date,
    date_from: date | None = None,
    asset_currencies: dict[int, str] | None = None,
    price_map: dict[int, list[tuple[date, Decimal, str]]] | None = None,
    intervals: Iterable[InTransitInterval] = (),
) -> DailyStateBuilder:
    """A builder with only what ``_valuation_rate_change_days`` reads; ``_replay_from`` set as ``build()`` sets it."""
    builder = DailyStateBuilder(
        classified_txs=[],
        in_transit_intervals=list(intervals),
        external_cash_flows=[],
        price_map=price_map or {},
        quote_base_map={},
        fx_rate_map=fx_rate_map,  # type: ignore[arg-type]
        asset_classifications={},
        asset_types={},
        asset_currencies=asset_currencies or {},
        average_costs={},
        native_cash=NativeCash(report_currency=REPORT, movements=(), converted=(), unit_rates={}),
        target_currency=REPORT,
        date_from=date_from or replay_from,
        date_to=date_to,
    )
    builder._replay_from = replay_from
    return builder


def _dense_reference(builder: DailyStateBuilder, fx_rate_map: Mapping | None = None) -> set[date]:
    """The dense algorithm, written again: every day from ``replay_from`` - 1 (none before ``date.min``) through
    ``date_to``, the exact day's rate of each watched currency, with no date floor (D-P4, MF-PAV-L1); plus each cash
    in-transit interval on its own days."""
    rates = builder.fx_rate_map if fx_rate_map is None else fx_rate_map
    target = builder.target_currency

    def changes(currencies: set[str], first: date, last: date) -> set[date]:
        previous = {currency: (rates.get((currency, target, first - ONE_DAY)) if first > date.min else None) for currency in currencies}
        changed: set[date] = set()
        for day in _days(first, last) if first <= last else []:
            current = {currency: rates.get((currency, target, day)) for currency in currencies}
            if current != previous:
                changed.add(day)
            previous = current
        return changed

    replay_from = builder._replay_from  # no date floor (D-P4, MF-PAV-L1): the calendars start at the replay's start
    currencies = {currency for prices in builder.price_map.values() for _day, _close, currency in prices if currency}
    currencies.update(currency for currency in builder.asset_currencies.values() if currency)
    currencies.discard(target)
    result: set[date] = changes(currencies, replay_from, builder.date_to) if currencies else set()
    for interval in builder.in_transit_intervals:
        currency = interval.departure_leg.currency
        start, end = max(interval.start_date, replay_from), min(interval.end_date, builder.date_to)
        if interval.tx_type != "cash" or not currency or currency == target or start > end:
            continue
        result |= changes({currency}, start, end)
    return result


def _rates(currency: str, points: Mapping[date, str], target: str = REPORT) -> dict[tuple[str, str, date], Decimal]:
    return {(currency, target, day): Decimal(rate) for day, rate in points.items()}


D = lambda offset: date.min + timedelta(days=offset)  # noqa: E731
J = lambda day: date(2025, 1, day)  # noqa: E731
F = lambda day: date(2025, 2, day)  # noqa: E731


def _named_dict_builders() -> dict[str, DailyStateBuilder]:
    usd = _rates("USD", {J(1): "1.0", J(4): "1.05", J(5): "1.05", J(6): "1.07", J(8): "1.07", J(9): "1.07", J(12): "1.10", J(13): "1.10", J(20): "1.2", J(21): "1.20", F(1): "1.3", F(20): "1.4"})
    gbp = _rates("GBP", {J(3): "0.8", J(4): "0.8", J(10): "0.81", J(25): "0.82", F(5): "0.83"})
    chf = _rates("CHF", {J(9): "0.95", J(10): "0.95", J(15): "0.96", J(16): "0.96", J(19): "0.97", J(21): "0.98", F(15): "0.99"})
    noise = _rates("USD", {J(7): "9", J(11): "9"}, target="GBP") | _rates("EUR", {J(7): "1"}) | _rates("GBP", {J(7): "1.2"}, target="USD")
    intervals = [
        _cash_interval(J(10), J(20), "CHF"),  # rates on start - 1 and start equal: the start day is no change
        _cash_interval(J(2), J(6), "CHF"),  # starts before replay_from: clipped
        _cash_interval(F(5), F(20), "CHF"),  # ends after date_to: clipped
        _cash_interval(J(10), J(20), "USD", tx_type="asset"),  # an asset interval: ignored
        _cash_interval(J(10), J(20), REPORT),  # in the report currency: ignored
        _cash_interval(J(18), J(17), "CHF"),  # empty
        _cash_interval(J(14), J(16), None),  # no currency: ignored
    ]
    return {
        "foreign-security": _builder(fx_rate_map=usd | noise, replay_from=J(5), date_from=J(20), date_to=F(10), asset_currencies={X: "USD", Y: REPORT}),
        "foreign-quote-currency": _builder(fx_rate_map=gbp | usd, replay_from=J(2), date_to=F(10), asset_currencies={Y: REPORT}, price_map={Y: [(J(3), Decimal("10"), "GBP"), (J(9), Decimal("11"), "GBP")]}),
        "cash-in-transit": _builder(fx_rate_map=chf | usd, replay_from=J(5), date_to=F(10), intervals=intervals),
        "date-from-on-a-rate-change": _builder(fx_rate_map=usd, replay_from=J(6), date_from=J(6), date_to=J(31), asset_currencies={X: "USD"}),
        "replay-before-date-from-all-kinds": _builder(
            fx_rate_map=usd | gbp | chf | noise,
            replay_from=J(3),
            date_from=J(15),
            date_to=F(25),
            asset_currencies={X: "USD"},
            price_map={Y: [(J(3), Decimal("10"), "GBP"), (J(4), Decimal("1"), None)]},  # type: ignore[list-item]
            intervals=intervals,
        ),
        "first-rate-on-replay-from": _builder(fx_rate_map=usd, replay_from=J(1), date_to=J(10), asset_currencies={X: "USD"}),
        "no-foreign-currency": _builder(fx_rate_map=usd, replay_from=J(1), date_to=J(10), asset_currencies={X: REPORT}),
    }


def _named_view_builders() -> dict[str, DailyStateBuilder]:
    usd = _Steps({J(1): Decimal("1.0"), J(6): Decimal("1.05"), J(9): Decimal("1.050"), J(14): Decimal("1.1"), F(2): Decimal("1.2")})
    gbp = _Steps({date(2024, 12, 20): Decimal("0.8"), J(12): Decimal("0.81"), J(30): Decimal("0.82")})
    chf = _Steps({J(8): Decimal("0.95"), J(15): Decimal("0.96"), J(16): Decimal("0.97"), F(1): Decimal("0.98")})
    steps = {("USD", REPORT): usd, ("GBP", REPORT): gbp, ("CHF", REPORT): chf, ("USD", "GBP"): _Steps({J(1): Decimal("0.9")})}
    windows = {
        ("USD", REPORT): [(J(1), J(10)), (J(13), J(20)), (J(21), F(5))],  # a gap, then two touching windows
        ("GBP", REPORT): [(J(5), J(8)), (J(7), J(25))],  # overlapping
        ("CHF", REPORT): [(J(9), J(18)), (F(1), F(3))],
        ("USD", "GBP"): [(J(1), F(28))],
    }
    view = AskedDayRates(steps, windows)
    return {
        "view-foreign-security": _builder(fx_rate_map=view, replay_from=J(4), date_from=J(10), date_to=F(10), asset_currencies={X: "USD"}),
        "view-foreign-quote-currency": _builder(fx_rate_map=view, replay_from=J(1), date_to=F(10), price_map={Y: [(J(3), Decimal("10"), "GBP")]}),
        "view-cash-in-transit": _builder(fx_rate_map=view, replay_from=J(4), date_to=F(2), intervals=[_cash_interval(J(9), J(16), "CHF"), _cash_interval(J(20), F(5), "CHF"), _cash_interval(J(1), J(9), "CHF")]),
        "view-date-from-on-a-rate-change": _builder(fx_rate_map=view, replay_from=J(14), date_from=J(14), date_to=J(31), asset_currencies={X: "USD", Y: "GBP"}),
    }


CURRENCIES = ("USD", "GBP", "CHF", REPORT)


def _random_builder(seed: int, use_view: bool) -> DailyStateBuilder:
    rng = random.Random(1_000 + seed)
    base = date(2025, 3, 1)

    def day(offset: int) -> date:
        return base + timedelta(days=offset)

    if use_view:
        steps: dict[Pair, _Steps] = {}
        windows: dict[Pair, list[Window]] = {}
        for currency in ("USD", "GBP", "CHF"):
            for destination in (REPORT, "GBP"):
                pair = (currency, destination)
                steps[pair] = _Steps({day(offset): rng.choice(VALUES) for offset in rng.sample(range(-20, 70), rng.randint(0, 8))})
                spans = []
                for _ in range(rng.randint(0, 4)):
                    first = rng.randint(-15, 60)
                    spans.append((first, first + rng.randint(0, 20)))
                windows[pair] = [(day(first), day(last)) for first, last in spans]
        fx_rate_map: Mapping = AskedDayRates(steps, windows)
    else:
        fx_rate_map = {}
        for currency in ("USD", "GBP", "CHF", REPORT):
            for destination in (REPORT, "GBP"):
                for offset in rng.sample(range(-20, 70), rng.randint(0, 15)):
                    fx_rate_map[(currency, destination, day(offset))] = rng.choice(VALUES)
    replay_offset = rng.randint(-5, 20)
    date_from = day(replay_offset + rng.randint(0, 10))
    date_to = date_from + timedelta(days=rng.randint(0, 40))
    asset_currencies = {asset_id: rng.choice(CURRENCIES) for asset_id in range(rng.randint(0, 3))}
    price_map = {10 + asset_id: [(day(rng.randint(-5, 40)), Decimal("1"), rng.choice(CURRENCIES))] for asset_id in range(rng.randint(0, 2))}
    intervals = []
    for _ in range(rng.randint(0, 3)):
        start = day(rng.randint(-10, 60))
        intervals.append(_cash_interval(start, start + timedelta(days=rng.randint(-2, 15)), rng.choice(CURRENCIES), rng.choice(("cash", "cash", "asset"))))
    return _builder(fx_rate_map=fx_rate_map, replay_from=day(replay_offset), date_from=date_from, date_to=date_to, asset_currencies=asset_currencies, price_map=price_map, intervals=intervals)


def _equivalence_problem(label: str, builder: DailyStateBuilder) -> str | None:
    expected = _dense_reference(builder)
    got = builder._valuation_rate_change_days()
    if got != expected:
        return f"{label}: missing {sorted(expected - got)[:6]}, extra {sorted(got - expected)[:6]}"
    return None


class TestBuilderEquivalence:
    """``_valuation_rate_change_days()`` gives HEAD's days, whatever map it reads (green on HEAD: a guard for the cure)."""

    @pytest.mark.parametrize("name", list(_named_dict_builders()))
    def test_named_dict_builders(self, name: str) -> None:
        problem = _equivalence_problem(name, _named_dict_builders()[name])
        assert problem is None, problem

    @pytest.mark.parametrize("name", list(_named_view_builders()))
    def test_named_view_builders(self, name: str) -> None:
        problem = _equivalence_problem(name, _named_view_builders()[name])
        assert problem is None, problem

    def test_the_named_cases_are_not_trivial(self) -> None:
        """Self-check of the fixtures: each named case with a foreign currency has rate-change days to find."""
        builders = _named_dict_builders() | _named_view_builders()
        empty = [name for name, builder in builders.items() if name != "no-foreign-currency" and not _dense_reference(builder)]
        assert not empty, empty
        assert J(10) not in _dense_reference(builders["cash-in-transit"]) and J(15) in _dense_reference(builders["cash-in-transit"])
        assert J(6) in _dense_reference(builders["date-from-on-a-rate-change"])

    @pytest.mark.parametrize("use_view", [False, True], ids=["dict-map", "asked-day-rates"])
    def test_random_builders(self, use_view: bool) -> None:
        problems = [problem for seed in range(40) if (problem := _equivalence_problem(f"seed {seed}", _random_builder(seed, use_view))) is not None]
        assert not problems, "\n".join(problems[:10])


# =============================================================================
# 3. THE COST: CANDIDATE DAYS ONLY
# =============================================================================


def _tx(*, id: int, dt: date, amount: str, currency: str | None, type: str = "DEPOSIT", broker_id: int = A, quantity: str = "0", asset_id: int | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies):
    """As PortfolioCalculationEngine: one AssetPriceSeries per asset, from its prices and trades (copy of
    test_fx_only_days.py)."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for asset_id in set(txs_by_asset) | set(price_map):
        series = build_asset_price_series(
            price_rows=price_map.get(asset_id, []),
            transactions=txs_by_asset.get(asset_id, []),
            split_linked_tx_ids=set(),
            asset_currency=asset_currencies.get(asset_id, REPORT),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[asset_id] = series
    return mark_series


def _book_builder(txs: list[MagicMock], *, fx_rate_map: Mapping, asset_currencies: dict[int, str], price_map: dict, date_from: date, date_to: date) -> DailyStateBuilder:
    """A real builder for a book of one broker: the classifier, the average costs and the native cash as ``calculate()``."""
    classified = ScopeAwareTransactionClassifier(scope_broker_ids={A}, all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)), broker_shares={A: Decimal("1")}).classify().classified
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map=price_map,
        quote_base_map={},
        fx_rate_map=fx_rate_map,  # type: ignore[arg-type]
        asset_classifications=dict.fromkeys(asset_currencies),
        asset_types=dict.fromkeys(asset_currencies, "Stock"),
        asset_currencies=asset_currencies,
        average_costs=engine_average_costs(classified, asset_currencies=asset_currencies, target_currency=REPORT, fx_rate_map=fx_rate_map, date_to=date_to),
        native_cash=engine_native_cash(classified, target_currency=REPORT, fx_rate_map=fx_rate_map, date_to=date_to),
        target_currency=REPORT,
        date_from=date_from,
        date_to=date_to,
        mark_series=_mark_series_from(classified, price_map, asset_currencies),
    )


def _count_read_rate(builder: DailyStateBuilder) -> list[int]:
    """Counts ``_read_rate`` calls on this instance (the method still runs)."""
    calls = [0]
    original: Callable[[str, date], Decimal | None] = builder._read_rate

    def counting(currency: str, day: date) -> Decimal | None:
        calls[0] += 1
        return original(currency, day)

    builder._read_rate = counting  # type: ignore[method-assign]
    return calls


def _budget(candidates: int) -> int:
    return min(READ_FACTOR * max(candidates, 1), READ_CAP)


class TestReadCost:
    """The method reads candidate days only: its reads do not grow with the calendar (red on HEAD)."""

    def test_cost_dict_book_through_build(self) -> None:
        """A deposit on 1900-01-02, a USD security bought in 2025 and a GBP-quoted one: HEAD reads ~2 × 46 000 days."""
        usd = _rates("USD", {date(1900, 1, 2): "4.8", date(1950, 6, 1): "3.1", date(2025, 3, 3): "1.04", date(2025, 3, 4): "1.05", date(2025, 6, 30): "1.07", date(2025, 12, 1): "1.1"})
        gbp = _rates("GBP", {date(2025, 1, 2): "1.18", date(2025, 4, 1): "1.19", date(2025, 4, 2): "1.19", date(2025, 9, 9): "1.2"})
        fx_rate_map = _CountingDict(usd | gbp)
        txs = [
            _tx(id=1, dt=date(1900, 1, 2), amount="1000", currency="USD"),
            _tx(id=2, dt=date(2025, 3, 3), amount="-100", currency="USD", type="BUY", quantity="2", asset_id=X),
            _tx(id=3, dt=date(2025, 5, 5), amount="50", currency=REPORT),
        ]
        price_map = {Y: [(date(2025, 2, 3), Decimal("10"), "GBP"), (date(2025, 8, 1), Decimal("11"), "GBP")]}
        builder = _book_builder(txs, fx_rate_map=fx_rate_map, asset_currencies={X: "USD", Y: REPORT}, price_map=price_map, date_from=date(2025, 1, 1), date_to=date(2025, 12, 31))
        builder.build()
        assert builder._replay_from == date(1900, 1, 2), "fixture: the replay starts on the 1900 deposit"
        expected = _dense_reference(builder, fx_rate_map=dict(fx_rate_map))
        candidates = len({day for _currency, _target, day in fx_rate_map})
        calls = _count_read_rate(builder)
        fx_rate_map.lookups = 0

        got = builder._valuation_rate_change_days()

        assert got == expected, f"missing {sorted(expected - got)[:6]}, extra {sorted(got - expected)[:6]}"
        budget = _budget(candidates)
        assert calls[0] <= budget, f"_read_rate called {calls[0]} times for {candidates} candidate days (budget {budget}): the calendar is walked day by day"
        assert fx_rate_map.lookups <= budget, f"{fx_rate_map.lookups} rate map lookups for {candidates} candidate days (budget {budget})"

    def test_cost_view_with_a_long_cash_transit(self) -> None:
        """An ``AskedDayRates`` asked on every day since 1900 (one step carried for decades) and a CHF transit of 125
        years: HEAD reads ~137 000 days."""
        floor = date(1900, 1, 1)
        last = date(2025, 12, 31)
        usd = _Steps({floor: Decimal("4.8"), date(1950, 6, 1): Decimal("3.1"), date(2025, 3, 3): Decimal("1.04"), date(2025, 3, 4): Decimal("1.05"), date(2025, 6, 30): Decimal("1.050"), date(2025, 12, 1): Decimal("1.1")})
        gbp = _Steps({floor: Decimal("1.5"), date(2025, 4, 1): Decimal("1.19"), date(2025, 9, 9): Decimal("1.2"), date(2025, 9, 10): Decimal("1.21")})
        chf = _Steps({floor: Decimal("0.2"), date(1971, 8, 15): Decimal("0.25"), date(2015, 1, 15): Decimal("0.95")})
        steps = {("USD", REPORT): usd, ("GBP", REPORT): gbp, ("CHF", REPORT): chf}
        windows = {pair: [(floor, last)] for pair in steps}
        view = _CountingView(steps, windows)
        builder = _builder(
            fx_rate_map=view,
            replay_from=date(1900, 1, 2),
            date_from=date(2025, 1, 1),
            date_to=last,
            asset_currencies={X: "USD"},
            price_map={Y: [(date(2025, 5, 5), Decimal("10"), "GBP")]},
            intervals=[_cash_interval(date(1900, 1, 2), date(2024, 12, 31), "CHF")],
        )
        expected = _dense_reference(builder)
        candidates = sum(len(reader.days) for reader in steps.values()) + 2 * len(windows) + 2 * len(builder.in_transit_intervals)
        calls = _count_read_rate(builder)
        view.lookups = 0
        for reader in steps.values():
            reader.calls = 0

        got = builder._valuation_rate_change_days()

        assert got == expected, f"missing {sorted(expected - got)[:6]}, extra {sorted(got - expected)[:6]}"
        budget = _budget(candidates)
        at_calls = sum(reader.calls for reader in steps.values())
        assert calls[0] <= budget, f"_read_rate called {calls[0]} times for {candidates} candidate days (budget {budget}): the calendar is walked day by day"
        assert view.lookups <= budget, f"{view.lookups} view lookups for {candidates} candidate days (budget {budget})"
        assert at_calls <= budget, f"{at_calls} steps .at() calls for {candidates} candidate days (budget {budget})"


class TestReadCostFromYearOne:
    """The same guarantee with no date floor: from 1 Jan year 1 to 2025 (~740 000 calendar days) the reads follow the
    stored rows and the transit's bounds, not the days (D-P4, MF-PAV-L1: this is the default case, not an exception)."""

    LAST = date(2025, 12, 31)

    def test_cost_dict_map_from_date_min(self) -> None:
        """A dict map with rows on year 1 and in 2025, a foreign security and a CHF transit of 2 025 years."""
        usd = _rates("USD", {D(0): "0.5", D(1): "0.5", D(10): "0.6", date(2025, 3, 3): "1.04", date(2025, 3, 4): "1.05"})
        chf = _rates("CHF", {D(0): "0.9", D(3): "0.95", date(2024, 12, 31): "0.95", date(2025, 1, 1): "0.96"})
        fx_rate_map = _CountingDict(usd | chf)
        builder = _builder(
            fx_rate_map=fx_rate_map,
            replay_from=D(0),
            date_from=date(2025, 1, 1),
            date_to=self.LAST,
            asset_currencies={X: "USD"},
            intervals=[_cash_interval(D(0), date(2025, 1, 1), "CHF")],
        )
        calls = _count_read_rate(builder)
        fx_rate_map.lookups = 0

        got = builder._valuation_rate_change_days()

        usd_changes = {D(0), D(2), D(10), D(11), date(2025, 3, 3), date(2025, 3, 4), date(2025, 3, 5)}
        chf_changes = {D(0), D(1), D(3), D(4), date(2024, 12, 31), date(2025, 1, 1), date(2025, 1, 2)}
        # the transit reads CHF on [D(0), 2025-01-01]: 2025-01-02 is outside it, 2025-01-01 is its last day
        assert got == usd_changes | (chf_changes - {date(2025, 1, 2)}), sorted(got)
        candidates = len({day for _currency, _target, day in fx_rate_map}) + 2
        budget = _budget(candidates)
        assert calls[0] <= budget, f"_read_rate called {calls[0]} times for {candidates} candidate days (budget {budget}): the calendar is walked day by day"
        assert fx_rate_map.lookups <= budget, f"{fx_rate_map.lookups} rate map lookups for {candidates} candidate days (budget {budget})"

    def test_cost_view_from_date_min(self) -> None:
        """An ``AskedDayRates`` asked on every day since year 1 and a CHF transit from ``date.min``."""
        usd = _Steps({D(0): Decimal("0.5"), D(100): Decimal("0.6"), date(1950, 6, 1): Decimal("3.1"), date(2025, 3, 3): Decimal("1.04")})
        chf = _Steps({D(0): Decimal("0.2"), date(1971, 8, 15): Decimal("0.25"), date(2015, 1, 15): Decimal("0.95")})
        steps = {("USD", REPORT): usd, ("CHF", REPORT): chf}
        windows = {pair: [(D(0), self.LAST)] for pair in steps}
        view = _CountingView(steps, windows)
        builder = _builder(
            fx_rate_map=view,
            replay_from=D(0),
            date_from=date(2025, 1, 1),
            date_to=self.LAST,
            asset_currencies={X: "USD"},
            intervals=[_cash_interval(D(0), date(2024, 12, 31), "CHF")],
        )
        candidates = sum(len(reader.days) for reader in steps.values()) + 2 * len(windows) + 2 * len(builder.in_transit_intervals)
        calls = _count_read_rate(builder)
        view.lookups = 0
        for reader in steps.values():
            reader.calls = 0

        got = builder._valuation_rate_change_days()

        # USD (the security) changes on each step day; CHF (the transit) on D(0) and its two steps inside the transit
        assert got == {D(0), D(100), date(1950, 6, 1), date(2025, 3, 3), date(1971, 8, 15), date(2015, 1, 15)}, sorted(got)
        budget = _budget(candidates)
        at_calls = sum(reader.calls for reader in steps.values())
        assert calls[0] <= budget, f"_read_rate called {calls[0]} times for {candidates} candidate days (budget {budget}): the calendar is walked day by day"
        assert view.lookups <= budget, f"{view.lookups} view lookups for {candidates} candidate days (budget {budget})"
        assert at_calls <= budget, f"{at_calls} steps .at() calls for {candidates} candidate days (budget {budget})"

    def test_build_from_date_min_reads_stored_rows_not_days(self) -> None:
        """``build()`` of a book whose first deposit is on 1 Jan year 1 and whose last movement is in 2025: the rate map
        is read about as many times as it holds rows, not once per day of the 2 025 years."""
        usd = _rates("USD", {D(0): "0.5", D(1): "0.5", date(1900, 1, 2): "4.8", date(2025, 3, 3): "1.04", date(2025, 3, 4): "1.05"})
        fx_rate_map = _CountingDict(usd)
        txs = [
            _tx(id=1, dt=D(0), amount="1000", currency="USD"),
            _tx(id=2, dt=date(2025, 3, 3), amount="-100", currency="USD", type="BUY", quantity="2", asset_id=X),
        ]
        builder = _book_builder(txs, fx_rate_map=fx_rate_map, asset_currencies={X: "USD"}, price_map={}, date_from=date(2025, 1, 1), date_to=self.LAST)
        builder.build()
        assert builder._replay_from == D(0), "fixture: the replay starts on the year-1 deposit"
        calls = _count_read_rate(builder)
        fx_rate_map.lookups = 0

        got = builder._valuation_rate_change_days()

        assert {D(0), D(2), date(1900, 1, 2), date(2025, 3, 3), date(2025, 3, 4), date(2025, 3, 5)} <= got
        candidates = len({day for _currency, _target, day in fx_rate_map})
        budget = _budget(candidates)
        assert calls[0] <= budget, f"_read_rate called {calls[0]} times for {candidates} candidate days (budget {budget}): the calendar is walked day by day"
        assert fx_rate_map.lookups <= budget, f"{fx_rate_map.lookups} rate map lookups for {candidates} candidate days (budget {budget})"


# =============================================================================
# 4. THE FIRST DAY OF THE CALENDAR
# =============================================================================


def _call(method: Callable[[], Any]) -> Any:
    try:
        return method()
    except OverflowError as error:
        pytest.fail(f"MF5-2a: OverflowError on date.min ({error}) — HEAD computes replay_from - 1 day (or start - 1 day)")


class TestDateMin:
    """With no date floor, a movement on 1 Jan year 1 is read like any other (D-P4, MF-PAV-L1)."""

    def test_dict_map_from_date_min(self) -> None:
        usd = _rates("USD", {D(0): "0.5", D(1): "0.5", D(4): "0.6", D(6): "0.6", D(9): "0.7", D(40): "0.8"})
        builder = _builder(fx_rate_map=usd, replay_from=D(0), date_from=D(20), date_to=D(60), asset_currencies={X: "USD"})
        expected = _dense_reference(builder)
        assert D(0) in expected and D(1) not in expected, "fixture: a rate on date.min is a change there"
        assert _call(builder._valuation_rate_change_days) == expected

    def test_view_map_from_date_min(self) -> None:
        steps = {("USD", REPORT): _Steps({D(0): Decimal("0.5"), D(5): Decimal("0.6"), D(30): Decimal("0.7")})}
        view = AskedDayRates(steps, {("USD", REPORT): [(D(0), D(10)), (D(25), D(50))]})
        builder = _builder(fx_rate_map=view, replay_from=D(0), date_from=D(20), date_to=D(60), price_map={Y: [(D(0), Decimal("1"), "USD")]})
        expected = _dense_reference(builder)
        assert {D(0), D(5), D(11), D(25), D(30), D(51)} == expected, f"fixture: {sorted(expected)}"
        assert _call(builder._valuation_rate_change_days) == expected

    def test_cash_in_transit_from_date_min(self) -> None:
        chf = _rates("CHF", {D(0): "0.9", D(3): "0.95", D(4): "0.95", D(12): "1.0"})
        builder = _builder(fx_rate_map=chf, replay_from=D(0), date_to=D(30), intervals=[_cash_interval(D(0), D(10), "CHF")])
        expected = _dense_reference(builder)
        assert expected == {D(0), D(1), D(3), D(5)}, f"fixture: {sorted(expected)}"
        assert _call(builder._valuation_rate_change_days) == expected

    def test_build_does_not_raise_on_date_min(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A USD deposit and a USD security bought on 1 Jan year 1: ``build()`` runs, and the method's days inside it are
        the dense reference's."""
        fx_rate_map = _rates("USD", {D(0): "0.5", D(1): "0.6", D(35): "0.65", D(36): "0.7"})
        txs = [
            _tx(id=1, dt=D(0), amount="100", currency="USD"),
            _tx(id=2, dt=D(0), amount="-10", currency=REPORT, type="BUY", quantity="2", asset_id=X),
            _tx(id=3, dt=D(33), amount="5", currency=REPORT),
        ]
        builder = _book_builder(txs, fx_rate_map=fx_rate_map, asset_currencies={X: "USD"}, price_map={}, date_from=D(31), date_to=D(40))
        captured: list[set[date]] = []
        original = DailyStateBuilder._valuation_rate_change_days

        def spy(self: DailyStateBuilder) -> set[date]:
            result = original(self)
            captured.append(result)
            return result

        monkeypatch.setattr(DailyStateBuilder, "_valuation_rate_change_days", spy)
        _call(builder.build)
        assert builder._replay_from == D(0)
        assert captured, "build() did not ask for the valuation rate-change days"
        assert captured[-1] == _dense_reference(builder) == {D(0), D(1), D(2), D(35), D(36), D(37)}

    def test_the_calendar_starts_at_the_replay_start_not_at_1900(self) -> None:
        """Opposite of the old guard: a movement on 1 Jan year 1 reads rates from year 1 on, with no floor on 1900.

        Rates on year 1 (0.1 on D(0), 0.2 on D(5)) and around 1900; replay from D(0), date_from in 1900. Every change
        day of the whole span is found: the year-1 ones (D(0), D(1), D(5), D(6)) as well as the 1900 ones.
        """
        usd = _rates("USD", {D(0): "0.1", D(5): "0.2", date(1899, 12, 31): "0.5", date(1900, 1, 1): "0.5", date(1900, 1, 10): "0.6"})
        builder = _builder(fx_rate_map=usd, replay_from=D(0), date_from=date(1900, 1, 5), date_to=date(1900, 2, 1), asset_currencies={X: "USD"})
        got = builder._valuation_rate_change_days()
        assert {D(0), D(1), D(5), D(6)} <= got, f"the year-1 change days are lost: {sorted(got)[:8]}"
        assert min(got) == D(0), f"the first change day is the replay start, not 1900: {min(got)}"
        assert got == {D(0), D(1), D(5), D(6), date(1899, 12, 31), date(1900, 1, 2), date(1900, 1, 10), date(1900, 1, 11)}, sorted(got)

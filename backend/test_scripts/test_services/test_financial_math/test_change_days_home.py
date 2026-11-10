"""The days something can change on, in their one home: ``financial_math/change_days.py``.

Pure: no database, no server, no network; maps and steps built by hand.

WHY. The rule «a daily figure is computed only on the days one of its inputs can change» (P3, D-P4) had four inline
copies: the candidate days of an FX reading in ``DailyStateBuilder._reading_calendar`` (plain map keyed
``(source, destination, day)``) and in ``FxRateResolver.rate_change_days`` (plain map keyed ``(source, day)``), and the
«days inside a calendar, with the day after each» of ``lots.change_days.lot_change_days`` (a set calendar) and
``price_candidate_days`` (a window). ``change_days`` itself moved verbatim from ``native_cash.py``. The module now holds
``reading_change_days``, ``change_days`` and ``with_next_days``; the callers import them.

What is tested:

- ``TestReadingChangeDays`` — on an ``AskedDayRates`` it is the view's own ``reading_change_days`` (both key formats,
  another destination of a fixed view gives none); on a plain 3-key map and on a 2-key map each key's day and the day
  after, other pairs ignored, ascending and unique; a key on ``date.max`` gives ``date.max`` and no day after, without
  ``OverflowError`` (the intended micro-difference from the old inline copy of ``rate_change_days``).
- ``TestWithNextDays`` — a set calendar and a ``DayRange``: days outside the calendar dropped, the day after only when
  in the calendar and only after a day of ``days`` (not transitive), ``date.max`` never followed.
- ``TestChangeDays`` — the behaviour the tests of ``test_fx_only_days.TestChangeDays`` pin, plus the calendar order, an
  empty calendar, no currency, and numeric equality (``1.1`` is ``1.10``).
- ``TestParityWithTheOldInlineFormulas`` — the four inline formulas as they were at HEAD ``ed2f59268`` (copied below,
  verbatim but for names) against the new calls, on seeded random maps and calendars away from ``date.max``: the same
  days. ``_reading_calendar`` and ``rate_change_days`` are compared through the real methods.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory);
alone: ``./dev.py test services financial-math test_change_days_home``.

Reference: backend/app/services/financial_math/change_days.py, backend/app/services/financial_math/fx_rates.py
(AskedDayRates.reading_change_days), backend/app/services/financial_math/portfolio/daily_state.py (_reading_calendar),
backend/app/services/financial_math/lots/conversions.py (FxRateResolver.rate_change_days),
backend/app/services/financial_math/lots/change_days.py (lot_change_days, price_candidate_days, DayRange).
"""

from __future__ import annotations

import random
from bisect import bisect_right
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.services.financial_math.change_days import change_days, reading_change_days, with_next_days
from backend.app.services.financial_math.fx_rates import AskedDayRates
from backend.app.services.financial_math.lots.change_days import DayRange
from backend.app.services.financial_math.lots.conversions import FxRateResolver
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder

ONE_DAY = timedelta(days=1)
REPORT = "EUR"
BASE = date(2025, 1, 1)
MAX = date.max


def day(offset: int) -> date:
    return BASE + timedelta(days=offset)


class _Steps:
    """A ``UnitRateReader``: the last step on or before the day, None before the first."""

    def __init__(self, points: Mapping[date, Decimal]) -> None:
        ordered = sorted(points.items())
        self.days = tuple(point_day for point_day, _value in ordered)
        self.values = tuple(value for _day, value in ordered)

    def at(self, when: date) -> Decimal | None:
        index = bisect_right(self.days, when) - 1
        return self.values[index] if index >= 0 else None


def _view(fixed: str | None = None) -> AskedDayRates:
    """USD → EUR: steps d2 1.1, d6 1.2 read in [d1, d4] and [d6, d8]; GBP → EUR: a step d0 read in [d3, d3]."""
    steps = {("USD", REPORT): _Steps({day(2): Decimal("1.1"), day(6): Decimal("1.2")}), ("GBP", REPORT): _Steps({day(0): Decimal("0.8")})}
    windows = {("USD", REPORT): [(day(1), day(4)), (day(6), day(8))], ("GBP", REPORT): [(day(3), day(3))]}
    return AskedDayRates(steps, windows) if fixed is None else AskedDayRates(steps, windows, fixed_destination=fixed)


# =============================================================================
# reading_change_days
# =============================================================================


class TestReadingChangeDays:
    """``reading_change_days(rates, source, destination)``: the days the reading of a pair may differ from the day before."""

    @pytest.mark.parametrize("fixed", [None, REPORT], ids=["three-part-keys", "fixed-destination"])
    def test_an_asked_day_rates_gives_its_own_reading_change_days(self, fixed: str | None) -> None:
        view = _view(fixed)
        for source in ("USD", "GBP", "CHF"):
            assert reading_change_days(view, source, REPORT) == view.reading_change_days(source, REPORT), source
        assert reading_change_days(view, "USD", REPORT) == (day(1), day(2), day(5), day(6), day(9))
        assert reading_change_days(view, "GBP", REPORT) == (day(3), day(4))

    def test_another_destination_of_a_fixed_view_gives_none(self) -> None:
        assert reading_change_days(_view(REPORT), "USD", "GBP") == ()

    def test_a_three_part_map_gives_each_key_day_and_the_day_after_of_its_pair_only(self) -> None:
        """USD → EUR on d1, d2, d5; GBP → EUR on d3 and USD → CHF on d8 are other pairs."""
        rates = {
            ("USD", REPORT, day(5)): Decimal("1.2"),
            ("USD", REPORT, day(1)): Decimal("1.1"),
            ("USD", REPORT, day(2)): Decimal("1.1"),
            ("GBP", REPORT, day(3)): Decimal("0.8"),
            ("USD", "CHF", day(8)): Decimal("0.9"),
        }
        assert reading_change_days(rates, "USD", REPORT) == (day(1), day(2), day(3), day(5), day(6))
        assert reading_change_days(rates, "GBP", REPORT) == (day(3), day(4))
        assert reading_change_days(rates, "USD", "CHF") == (day(8), day(9))
        assert reading_change_days(rates, "CHF", REPORT) == ()

    def test_a_two_part_map_into_one_destination_gives_each_key_day_and_the_day_after(self) -> None:
        """Keys ``(source, day)``: the map reads into one destination, so only the source selects."""
        rates = {("USD", day(4)): Decimal("1.2"), ("USD", day(1)): Decimal("1.1"), ("GBP", day(2)): Decimal("0.8")}
        assert reading_change_days(rates, "USD", REPORT) == (day(1), day(2), day(4), day(5))
        assert reading_change_days(rates, "GBP", REPORT) == (day(2), day(3))
        assert reading_change_days(rates, "CHF", REPORT) == ()

    def test_an_empty_map_gives_none(self) -> None:
        assert reading_change_days({}, "USD", REPORT) == ()

    @pytest.mark.parametrize("key", [("USD", REPORT, MAX), ("USD", MAX)], ids=["three-part", "two-part"])
    def test_a_key_on_date_max_gives_no_day_after_and_does_not_overflow(self, key: tuple) -> None:
        rates = {key: Decimal("1.1"), (*key[:-1], MAX - ONE_DAY): Decimal("1.1")}
        assert reading_change_days(rates, "USD", REPORT) == (MAX - ONE_DAY, MAX)

    def test_a_key_on_date_min_is_kept(self) -> None:
        assert reading_change_days({("USD", REPORT, date.min): Decimal("1")}, "USD", REPORT) == (date.min, date.min + ONE_DAY)


# =============================================================================
# with_next_days
# =============================================================================


class TestWithNextDays:
    """``with_next_days(days, calendar)``: the days inside ``calendar``, with the day after each when inside too."""

    def test_a_set_calendar_drops_the_days_outside_and_adds_the_day_after_only_inside(self) -> None:
        """Calendar d1, d2, d3, d5: d1 brings d2; d3's day after d4 is not in it; d9 is outside."""
        calendar = {day(1), day(2), day(3), day(5)}
        assert with_next_days([day(1), day(3), day(9)], calendar) == {day(1), day(2), day(3)}

    def test_the_day_after_is_not_transitive(self) -> None:
        """d1 brings d2, but d2 — not a day of ``days`` — brings no d3."""
        assert with_next_days([day(1)], {day(1), day(2), day(3)}) == {day(1), day(2)}

    def test_a_day_outside_the_calendar_brings_no_day_after(self) -> None:
        """d0 is outside; its day after d1 is in the calendar but comes only after a day inside."""
        assert with_next_days([day(0)], {day(1), day(2)}) == set()

    def test_a_day_range_calendar(self) -> None:
        window = DayRange(day(1), day(5))
        assert with_next_days([day(0), day(1), day(3), day(5), day(6)], window) == {day(1), day(2), day(3), day(4), day(5)}

    def test_an_empty_day_range_keeps_nothing(self) -> None:
        assert with_next_days([day(1), day(2)], DayRange(day(2), day(1))) == set()

    def test_a_generator_of_days_and_duplicates(self) -> None:
        assert with_next_days((d for d in (day(1), day(1), day(2))), {day(1), day(2), day(3)}) == {day(1), day(2), day(3)}

    def test_no_day_after_date_max(self) -> None:
        assert with_next_days([MAX], {MAX}) == {MAX}
        assert with_next_days([MAX], DayRange(MAX - ONE_DAY, MAX)) == {MAX}
        assert with_next_days([MAX - ONE_DAY], DayRange(MAX - ONE_DAY, MAX)) == {MAX - ONE_DAY, MAX}

    def test_nothing_in_nothing_out(self) -> None:
        assert with_next_days([], {day(1)}) == set()
        assert with_next_days([day(1)], set()) == set()


# =============================================================================
# change_days
# =============================================================================


CALENDAR = tuple(day(offset) for offset in range(1, 6))
D1, D2, D3, D4, D5 = CALENDAR


def _exact_day(rates: Mapping[tuple[str, date], str]):
    points = {key: Decimal(rate) for key, rate in rates.items()}
    return lambda currency, when: points.get((currency, when))


def _last_known(rates: Mapping[tuple[str, date], str]):
    points = sorted((key, Decimal(rate)) for key, rate in rates.items())

    def read(currency: str, when: date) -> Decimal | None:
        known = [rate for (point_currency, point_day), rate in points if point_currency == currency and point_day <= when]
        return known[-1] if known else None

    return read


_USD_WITH_A_GAP = {("USD", D1): "0.90", ("USD", D2): "0.90", ("USD", D4): "0.90", ("USD", D5): "0.90"}


class TestChangeDays:
    """``change_days(read, currencies, days)``: the calendar days on which a watched currency reads another rate than
    on the calendar's previous day (None before the first day)."""

    def test_exact_day_reading_counts_the_day_a_rate_disappears_and_comes_back(self) -> None:
        assert change_days(_exact_day(_USD_WITH_A_GAP), {"USD"}, CALENDAR) == (D1, D3, D4)

    def test_last_known_reading_sees_no_change_across_a_gap(self) -> None:
        assert change_days(_last_known(_USD_WITH_A_GAP), {"USD"}, CALENDAR) == (D1,)

    def test_a_rate_present_on_the_first_calendar_day_counts(self) -> None:
        flat = {("USD", when): "0.90" for when in CALENDAR}
        assert change_days(_exact_day(flat), {"USD"}, (D2, D3, D4)) == (D2,)

    def test_a_rate_absent_on_the_first_calendar_day_is_no_change(self) -> None:
        assert change_days(_exact_day({("USD", D2): "0.90", ("USD", D3): "0.90"}), {"USD"}, (D1, D2, D3)) == (D2,)

    def test_several_currencies_merge_in_calendar_order_once(self) -> None:
        usd = {("USD", when): rate for when, rate in zip(CALENDAR, ("0.90", "0.90", "0.80", "0.85", "0.85"), strict=True)}
        gbp = {("GBP", when): rate for when, rate in zip(CALENDAR[1:], ("1.20", "1.20", "1.10", "1.10"), strict=True)}
        assert change_days(_exact_day(usd | gbp), ["USD", "GBP", "USD"], CALENDAR) == (D1, D2, D3, D4)

    def test_a_currency_outside_the_set_is_ignored(self) -> None:
        rates = {("USD", when): "0.90" for when in CALENDAR} | {("CHF", D1): "1.05", ("CHF", D2): "1.10", ("CHF", D3): "1.05"}
        assert change_days(_exact_day(rates), {"USD"}, CALENDAR) == (D1,)

    def test_a_rate_equal_by_value_is_no_change(self) -> None:
        """``1.1`` then ``1.10``: the same number, no change on D2."""
        assert change_days(_exact_day({("USD", D1): "1.1", ("USD", D2): "1.10", ("USD", D3): "1.2"}), {"USD"}, (D1, D2, D3)) == (D1, D3)

    def test_the_calendar_is_read_in_its_own_order(self) -> None:
        """Calendar D3, D1, D2: each day compared with the one before it in the calendar, and given in that order."""
        rates = {("USD", D1): "0.90", ("USD", D2): "0.90", ("USD", D3): "0.80"}
        assert change_days(_exact_day(rates), {"USD"}, iter((D3, D1, D2))) == (D3, D1)

    def test_no_day_or_no_currency_gives_none(self) -> None:
        read = _exact_day(_USD_WITH_A_GAP)
        assert change_days(read, {"USD"}, ()) == ()
        assert change_days(read, set(), CALENDAR) == ()


# =============================================================================
# Parity with the inline formulas of HEAD ed2f59268
# =============================================================================


def _old_lot_change_days_inside(changes: set[date], calendar: set[date]) -> list[date]:
    """``lots/change_days.py::lot_change_days`` at HEAD, its last three lines."""
    inside = {d for d in changes if d in calendar}
    inside.update(d + ONE_DAY for d in list(inside) if d + ONE_DAY in calendar)
    return sorted(inside)


def _old_price_candidate_days_inside(seeds: set[date], first: date, last: date) -> list[date]:
    """``lots/change_days.py::price_candidate_days`` at HEAD, its last three lines."""
    inside = {d for d in seeds if first <= d <= last}
    inside.update(d + ONE_DAY for d in list(inside) if d + ONE_DAY <= last)
    return sorted(inside)


def _old_reading_calendar(rates, target_currency: str, currencies: set[str], first: date, last: date) -> list[date]:
    """``DailyStateBuilder._reading_calendar`` at HEAD, ``self`` replaced by its two attributes."""
    candidates: set[date] = set()
    if isinstance(rates, AskedDayRates):
        for currency in currencies:
            candidates.update(rates.reading_change_days(currency, target_currency))
    else:
        for key in rates:
            if len(key) == 3 and key[0] in currencies and key[1] == target_currency:
                d = key[2]
                candidates.add(d)
                if d < date.max:
                    candidates.add(d + timedelta(days=1))
    days: set[date] = {first - timedelta(days=1)} if first > date.min else set()
    for d in candidates:
        if first <= d <= last:
            days.add(d)
            if d > date.min:
                days.add(d - timedelta(days=1))
    return sorted(days)


def _old_rate_change_days(resolver: FxRateResolver) -> tuple[date, ...]:
    """``FxRateResolver.rate_change_days`` at HEAD."""
    days: set[date] = set()
    for currency in resolver._windows:
        for rates in resolver._rates.maps:
            if isinstance(rates, AskedDayRates):
                days.update(rates.reading_change_days(currency, resolver.target_currency))
            else:
                for rate_key in rates:
                    if rate_key[0] == currency:
                        days.update((rate_key[1], rate_key[1] + timedelta(days=1)))
    return tuple(sorted(days))


SEEDS = range(40)
CURRENCIES = ("USD", "GBP", "CHF")


def _random_days(rng: random.Random, count: int, span: int = 60) -> set[date]:
    return {day(rng.randint(-5, span)) for _ in range(count)}


def _random_three_part_map(rng: random.Random) -> dict[tuple, Decimal]:
    destinations = (REPORT, REPORT, "JPY")
    return {(rng.choice(CURRENCIES), rng.choice(destinations), when): Decimal(rng.choice(("1.1", "1.10", "0.9"))) for when in _random_days(rng, rng.randint(0, 25))}


def _random_view(rng: random.Random, fixed: str | None) -> AskedDayRates:
    steps, windows = {}, {}
    for currency in CURRENCIES[: rng.randint(1, 3)]:
        steps[(currency, REPORT)] = _Steps({when: Decimal(rng.choice(("1.1", "1.2"))) for when in _random_days(rng, rng.randint(1, 6))})
        asked = []
        for _ in range(rng.randint(1, 3)):
            first = day(rng.randint(-5, 50))
            asked.append((first, first + timedelta(days=rng.randint(0, 10))))
        windows[(currency, REPORT)] = asked
    return AskedDayRates(steps, windows) if fixed is None else AskedDayRates(steps, windows, fixed_destination=fixed)


class TestParityWithTheOldInlineFormulas:
    """The new calls give the days the four inline formulas gave, away from ``date.max``."""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_lot_change_days_inside_a_set_calendar(self, seed: int) -> None:
        rng = random.Random(seed)
        changes, calendar = _random_days(rng, rng.randint(0, 20)), _random_days(rng, rng.randint(0, 40))
        assert sorted(with_next_days(changes, calendar)) == _old_lot_change_days_inside(changes, calendar)

    @pytest.mark.parametrize("seed", SEEDS)
    def test_price_candidate_days_inside_a_window(self, seed: int) -> None:
        rng = random.Random(seed)
        seeds = _random_days(rng, rng.randint(0, 20))
        first = day(rng.randint(-3, 30))
        last = first + timedelta(days=rng.randint(-2, 30))
        assert sorted(with_next_days(seeds, DayRange(first, last))) == _old_price_candidate_days_inside(seeds, first, last)

    @pytest.mark.parametrize("seed", SEEDS)
    def test_reading_calendar_of_the_portfolio_engine(self, seed: int) -> None:
        """The real ``DailyStateBuilder._reading_calendar`` against its HEAD copy, on a plain 3-part map and on a view."""
        rng = random.Random(seed)
        currencies = set(rng.sample(CURRENCIES, rng.randint(1, 3)))
        first = day(rng.randint(-3, 30))
        last = first + timedelta(days=rng.randint(0, 30))
        for rates in (_random_three_part_map(rng), _random_view(rng, None)):
            builder = SimpleNamespace(fx_rate_map=rates, target_currency=REPORT)
            new = DailyStateBuilder._reading_calendar(builder, currencies, first, last)
            assert new == _old_reading_calendar(rates, REPORT, currencies, first, last), type(rates).__name__

    @pytest.mark.parametrize("seed", SEEDS)
    def test_rate_change_days_of_the_lots_resolver(self, seed: int) -> None:
        """The real ``FxRateResolver.rate_change_days`` against its HEAD copy: a hand-filled 2-part map, then views."""
        rng = random.Random(seed)
        resolver = FxRateResolver(REPORT)
        for currency in rng.sample(CURRENCIES, rng.randint(1, 3)):
            first = day(rng.randint(-3, 30))
            resolver.need_days(currency, first, first + timedelta(days=rng.randint(0, 20)))
        for when in _random_days(rng, rng.randint(0, 20)):
            resolver._rates[(rng.choice(CURRENCIES), when)] = Decimal("1.1")
        for _ in range(rng.randint(0, 2)):
            resolver._rates.maps.append(_random_view(rng, REPORT))
        assert resolver.rate_change_days() == _old_rate_change_days(resolver)

    def test_the_old_resolver_copy_overflowed_on_date_max_and_the_new_does_not(self) -> None:
        """The one intended difference: a hand-built key on ``date.max``."""
        resolver = FxRateResolver(REPORT)
        resolver.need_days("USD", day(1), day(2))
        resolver._rates[("USD", MAX)] = Decimal("1.1")
        with pytest.raises(OverflowError):
            _old_rate_change_days(resolver)
        assert resolver.rate_change_days() == (MAX,)

"""P3 of MF's fast formulas (workstream MF, release 1.3) — ``AskedDayRates``: X's unit-rate steps read only on the days
that were asked, as the dict of today; and the native cash valued from those steps exactly as from that dict.

The developer's rule: «è imperativo non sbagliare i calcoli, veloci sì, ma precisi». The cure must give the same digits,
exponent included, and only then be fast.

Today (HEAD ``2f4ab1962``) the portfolio engine (``portfolio/engine.py::_preload_fx_rates``) and the native cash
(``native_cash.py::compute_native_cash``) ask ``convert_bulk`` for one unit of each foreign currency on every calendar day
they may read, and keep the answers in a dict: ``fx_rate_map[(currency, target, day)]`` and
``NativeCash.unit_rates[(currency, day)]``. A day nobody asked is absent: ``.get`` gives None.

The cure (MF, written after these reds), pinned here:

- ``financial_math/fx_rates.py::AskedDayRates``, a ``collections.abc.Mapping``, built as
  ``AskedDayRates(steps, windows, fixed_destination=None)``: ``steps[(src, dst)]`` an object with ``.at(day)`` (X's
  ``UnitRateSteps``), ``windows[(src, dst)]`` an iterable of ``(first, last)`` (both included), merged when they overlap
  or touch. Its keys are ``(src, dst, day)``, or ``(src, day)`` with ``fixed_destination``. ``m[key]`` is
  ``steps[(src, dst)].at(day)`` only when ``day`` is inside a window of the pair and the value is not None; otherwise
  ``KeyError`` (so ``.get`` gives None). ``__iter__``/``__len__``/``.items()`` walk every asked day with a value (a walk
  kept for the tests). ``step_series()`` gives ``{src: (days, values)}``, the steps of each pair, for the native cash.
- ``NativeCash.__post_init__``: given an ``AskedDayRates``, its rate series are the steps (``step_series()``), not every
  asked day; given a plain dict, ``_rate_series(dict)`` as today.

Why the windows matter (the off-window trap). X's ``UnitRateSteps.at`` answers on ANY day, with the last step on or before
it: off the asked windows that is not ``convert_bulk``'s answer (a row between two windows is no step). Today's dict has no
entry there. A view that reads ``at`` off its windows changes what ``DailyStateBuilder`` reads (``.get`` at the exact day)
— the numbers move.

What is tested (pure: no database, no server, no network; steps built by hand):

1. ``TestTheViewIsTheDictOfToday`` — on 30 seeded random cases (1–3 pairs, step functions with long-digit values and
   trailing zeros, 1–7 windows per pair: single days, nested, overlapping, touching, disjoint, repeated, in any order) and
   on named shapes: the view equals, key for key and digit for digit (``as_tuple()``), the dict built day by day as today
   (every day of every window, ``at(day)`` kept when not None); its walk has no duplicate; ``.get``/``in``/``[]`` agree
   with that dict on every day around the windows (off the windows and before the first step: None, ``KeyError``);
   steps answering only ``.at`` (a stub) are enough; with ``fixed_destination`` the keys are ``(src, day)``; windows given
   as a one-shot iterator are read once and fully.
1b. ``TestTheContractPoints`` — MF's answers to the first hand-over's ambiguities, one test each: ``step_series()``
   raises ``ValueError`` without ``fixed_destination`` (1); a pair without steps is absent from it (3);
   ``merged_windows`` leaves out a window that ends before it starts and joins overlapping and touching ones (4); a
   ``datetime`` day or a malformed key is ``KeyError`` (6); with ``fixed_destination`` the pairs into another
   destination are ignored, steps and windows (7); the view is a ``Mapping``, never a ``MutableMapping`` (8).
2. ``TestStepSeries`` — ``step_series()`` is each pair's ``(days, values)``, the anchor step of every window included.
3. ``TestTheNativeCashFromTheView`` — ``NativeCash(unit_rates=view)`` against ``NativeCash(unit_rates=<the dense dict of
   the same asked days>)`` on a named book (movements before ``EARLIEST_RANGE_START`` on single-day windows, a stored rate
   strictly between two windows, a currency whose first rate comes after its first movement, a repeated rate, a zero
   movement, a report-currency movement) and on 30 seeded random books: same ``value_at`` on every day (or the same
   ``ValueError``), same ``rate_change_days`` (whole and on windows), same ``exchange_results``, ``converted``,
   ``balances``, ``foreign_cash_broker_ids``. The asked days are those of HEAD's ``_unit_requests`` (copied verbatim below
   as the oracle ``_unit_requests_today``); the windows the fixture builds are checked to cover exactly them.
4. ``TestTheNativeCashCost`` — the cost red: ``NativeCash._rate_days`` built from a view holds no more days than the
   steps of that currency (today's ``_rate_series`` on any Mapping keeps every asked day).

The steps are built as X's ``unit_rate_steps`` builds them (``backend/app/services/fx/conversion.py``: each window's first
day with the backward-fill anchor, plus every row inside a window; a row between two windows is no step) by
``_steps_like_unit_rate_steps``; ``test_fx_rate_steps.py`` pins that rule against the database.

RED on HEAD 2f4ab1962, by absence: ``AskedDayRates`` (and ``merged_windows``) do not exist, every test that builds one
fails with that message (``_asked_day_rates_class``, ``_merged_windows``). GREEN on HEAD: the fixture self-checks (``TestTheFixtures``), which never touch the cure.
After a cure that adds ``AskedDayRates`` but keeps ``NativeCash.__post_init__`` on ``_rate_series`` for every Mapping,
every parity test is green and ``TestTheNativeCashCost`` stays red: that is the cost red.

Mutants, measured first on a scratch reference cure (green 187/187), then on MF's cure (2026-10-20, a scratch copy of
HEAD 2f4ab1962 + the cure: green 197/197); the counts are MF's cure's:
- the view not limited to the windows (``at`` read on any day) — 80 reds, ``TestTheViewIsTheDictOfToday`` and (7);
- windows not merged — 63 reds: nested/overlapping windows, a bisect over unmerged windows misses days; and (4);
- the native cash calendar from the steps missing a currency's first step — 25 reds, ``rate_change_days`` parity;
- ``step_series`` with the anchor day dropped — 53 reds, ``TestStepSeries`` and ``value_at`` parity;
- ``NativeCash._rate_at`` reading the exact day only, or forward — 27 reds each, the native-cash parity;
- the contract points: ``step_series`` without the destination check (1), a pair without steps kept as an empty series
  (15), ``merged_windows`` keeping a reversed window (2), a ``datetime`` day raising ``TypeError`` (1), the
  fixed-destination filter of the steps removed (1). Two survive, equivalent by construction: the same filter removed
  from the windows alone (a window whose pair has no steps is skipped by the walk, and ``[]`` looks up only
  ``(source, fixed destination)``), and ``merged_windows`` keeping a reversed window seen through the mapping only (it
  covers no day, and cannot widen a merge: that would need ``previous_last < last < first <= previous_last + 1``), which
  is why (4) tests ``merged_windows`` itself.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory);
alone: ``./dev.py test services financial-math test_asked_day_rates``.

Reference: backend/app/services/fx/conversion.py (UnitRateSteps, unit_rate_steps), backend/app/services/financial_math/
native_cash.py (_unit_requests, _rate_series, _rate_at, change_days), backend/app/services/financial_math/portfolio/
engine.py (_preload_fx_rates), backend/test_scripts/test_services/test_fx_rate_steps.py (X's oracle),
LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md («formule veloci», P3).
"""

from __future__ import annotations

import random
from bisect import bisect_right
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from backend.app.services.financial_math import fx_rates as fx_rates_module
from backend.app.services.financial_math.native_cash import CashMovement, NativeCash
from backend.app.services.fx.conversion import UnitRateSteps
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START
from backend.test_scripts.test_utils import print_section, print_success

Pair = tuple[str, str]
Window = tuple[date, date]

FLOOR = EARLIEST_RANGE_START
REPORT = "EUR"
SEEDS = range(30)


# =============================================================================
# THE CURE'S NAME, AND THE ORACLES OF TODAY
# =============================================================================


def _asked_day_rates_class() -> type:
    """``financial_math/fx_rates.py::AskedDayRates``, read when a test runs: before the cure each test fails here, by
    absence, while the module still collects."""
    cls = getattr(fx_rates_module, "AskedDayRates", None)
    if cls is None:
        pytest.fail("P3: financial_math/fx_rates.py has no AskedDayRates yet (red by absence, before the cure)")
    return cls


def _view(steps: Mapping[Pair, Any], windows: Mapping[Pair, Iterable[Window]], fixed_destination: str | None = None) -> Mapping:
    """``AskedDayRates(steps, windows)``, with ``fixed_destination`` only when given."""
    cls = _asked_day_rates_class()
    if fixed_destination is None:
        return cls(steps, windows)
    return cls(steps, windows, fixed_destination=fixed_destination)


def _days(first: date, last: date) -> list[date]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _dense_today(steps: Mapping[Pair, Any], windows: Mapping[Pair, Sequence[Window]], fixed_destination: str | None = None) -> dict:
    """THE ORACLE of the mapping: the dict built day by day as today's code builds it — every day of every window of
    every pair, ``at(day)`` kept when it is not None (``fx_rate_map[(ccy, target, dt)] = amount``: a day asked twice is one
    key)."""
    dense: dict = {}
    for (source, destination), pair_windows in windows.items():
        for first, last in pair_windows:
            for day in _days(first, last):
                value = steps[(source, destination)].at(day)
                if value is not None:
                    dense[(source, day) if fixed_destination is not None else (source, destination, day)] = value
    return dense


def _unit_requests_today(foreign: Sequence[CashMovement], rates_until: date | None) -> list[tuple[str, date]]:
    """THE ORACLE of the native cash's asked days: HEAD 2f4ab1962's ``native_cash._unit_requests``, verbatim (the
    floor read as ``EARLIEST_RANGE_START``)."""
    first: dict[str, date] = {}
    last: dict[str, date] = {}
    early: dict[str, set[date]] = {}
    for movement in foreign:
        currency = movement.currency
        if currency not in first or movement.date < first[currency]:
            first[currency] = movement.date
        if currency not in last or movement.date > last[currency]:
            last[currency] = movement.date
        if movement.date < EARLIEST_RANGE_START:
            early.setdefault(currency, set()).add(movement.date)
    requests: list[tuple[str, date]] = []
    for currency in sorted(first):
        requests.extend((currency, day) for day in sorted(early.get(currency, ())))
        day = max(first[currency], EARLIEST_RANGE_START)
        end = last[currency] if rates_until is None else rates_until
        while day <= end:
            requests.append((currency, day))
            day += timedelta(days=1)
    return requests


def _native_windows(foreign: Sequence[CashMovement], rates_until: date | None) -> dict[Pair, list[Window]]:
    """The windows the cure asks for the native cash, as the contract states them: each movement's own day before the
    floor as ``(d, d)``, then one window from ``max(first movement, floor)`` to ``rates_until`` (or the last movement),
    skipped when it would end before it starts. ``TestTheFixtures`` checks they cover exactly ``_unit_requests_today``."""
    by_currency: dict[str, list[CashMovement]] = {}
    for movement in foreign:
        by_currency.setdefault(movement.currency, []).append(movement)
    windows: dict[Pair, list[Window]] = {}
    for currency, rows in sorted(by_currency.items()):
        asked = sorted({(row.date, row.date) for row in rows if row.date < FLOOR})
        start = max(min(row.date for row in rows), FLOOR)
        end = max(row.date for row in rows) if rates_until is None else rates_until
        if start <= end:
            asked.append((start, end))
        if asked:
            windows[(currency, REPORT)] = asked
    return windows


def _steps_like_unit_rate_steps(source: str, destination: str, rows: Mapping[date, Decimal], windows: Sequence[Window]) -> UnitRateSteps:
    """A ``UnitRateSteps`` as X's ``unit_rate_steps`` builds it from one pair's usable ``rows`` (``{row day: unit
    value}``): each window's first day with its anchor, the last row on or before it (no step without one), and every
    row inside a window on its own day; a row between two windows is no step."""
    row_days = sorted(rows)
    by_day: dict[date, date] = {}
    for first, last in sorted(windows):
        anchor = bisect_right(row_days, first) - 1
        if anchor >= 0:
            by_day[first] = row_days[anchor]
        for index in range(anchor + 1, bisect_right(row_days, last)):
            by_day[row_days[index]] = row_days[index]
    days = tuple(sorted(by_day))
    return UnitRateSteps(source=source, destination=destination, days=days, values=tuple(rows[by_day[day]] for day in days), rate_days=tuple(by_day[day] for day in days))


# =============================================================================
# COMPARING: DIGIT AND EXPONENT
# =============================================================================


def _bits(value: object) -> object:
    """None, or a Decimal's sign, digits and exponent: ``==`` alone takes 1.0837 for 1.0837000000."""
    if value is None:
        return None
    if type(value) is Decimal:
        return value.as_tuple()
    return (type(value).__name__, repr(value))


def _bits_dict(mapping: Mapping) -> dict:
    return {key: _bits(value) for key, value in mapping.items()}


def _show(lines: list[str], shown: int = 12) -> str:
    more = f"\n  … and {len(lines) - shown} more" if len(lines) > shown else ""
    return "\n  " + "\n  ".join(lines[:shown]) + more


def _probe_keys(steps: Mapping[Pair, Any], windows: Mapping[Pair, Sequence[Window]], fixed_destination: str | None, margin: int = 4) -> list:
    """Every key from a few days before the earliest window or step of each pair to a few days after the latest: on
    them the view must answer what the dense dict answers — off the windows and before the first step, nothing."""
    keys = []
    for (source, destination), pair_windows in windows.items():
        edges = [day for window in pair_windows for day in window] + list(getattr(steps[(source, destination)], "days", ()))
        for day in _days(min(edges) - timedelta(days=margin), max(edges) + timedelta(days=margin)):
            keys.append((source, day) if fixed_destination is not None else (source, destination, day))
    return keys


def _walk_problems(view: Mapping, dense: Mapping) -> list[str]:
    """The walk of ``view`` (``__iter__``, ``__len__``, ``.items()``) against ``dense``: the same keys, once each, and the
    same values to the digit."""
    problems: list[str] = []
    walked = list(view)
    if len(walked) != len(set(walked)):
        doubled = sorted({key for key in walked if walked.count(key) > 1}, key=repr)
        problems.append(f"the walk yields {len(walked)} keys, {len(set(walked))} distinct: doubled {doubled[:4]}")
    if set(walked) != set(dense):
        problems.append(f"the walk's keys differ from the dict of today: missing {sorted(set(dense) - set(walked), key=repr)[:4]}, extra {sorted(set(walked) - set(dense), key=repr)[:4]}")
    if len(view) != len(dense):
        problems.append(f"len(view) is {len(view)}, the dict of today has {len(dense)} keys")
    items, expected = _bits_dict(dict(view.items())), _bits_dict(dense)
    differing = [f"{key}: view {view_bits}, today {expected.get(key)}" for key, view_bits in items.items() if key in expected and view_bits != expected[key]]
    if differing:
        problems.append(f"{len(differing)} value(s) of the walk differ from the dict of today (as_tuple): {differing[:4]}")
    return problems


def _lookup_problem(view: Mapping, dense: Mapping, key: object) -> str | None:
    """``.get``, ``in`` and ``[]`` of ``view`` on ``key`` against ``dense``: the first that differs, or None."""
    wanted = dense.get(key)
    got = view.get(key)
    if _bits(got) != _bits(wanted):
        return f".get({key}) is {got!r}, the dict of today gives {wanted!r}"
    if (key in view) != (key in dense):
        return f"{key} in view is {key in view}, in the dict of today {key in dense}"
    if wanted is not None:
        return None if _bits(view[key]) == _bits(wanted) else f"view[{key}] is {view[key]!r}, the dict of today gives {wanted!r}"
    try:
        answer = view[key]
    except KeyError:
        return None
    return f"view[{key}] answers {answer!r}: expected KeyError (not asked, or no rate yet)"


def _mapping_problems(view: Mapping, dense: Mapping, probes: Iterable) -> list[str]:
    """Every way ``view`` differs from ``dense``: its walk, and ``.get``, ``in`` and ``[]`` on ``probes`` and on every
    dense key."""
    problems = _walk_problems(view, dense)
    problems += [problem for problem in (_lookup_problem(view, dense, key) for key in list(dense) + list(probes)) if problem]
    return problems


# =============================================================================
# RANDOM CASES
# =============================================================================

ORIGIN = date(2024, 3, 1)
_LONG_DIGITS = ("0.9227646027498385161945187783", "1.0837000000", "1.0837", "0.8571234567", "1.2643210987000", "7E+2", "0.70", "1", "1.000", "0.5")


def _value(rng: random.Random) -> Decimal:
    """A unit value with long digits, trailing zeros or a positive exponent: what ``as_tuple()`` tells apart."""
    if rng.random() < 0.5:
        return Decimal(rng.choice(_LONG_DIGITS))
    return Decimal(rng.randint(1, 10**12)) / Decimal(10 ** rng.randint(0, 14))


def _random_windows(rng: random.Random, span: int) -> list[Window]:
    """1–7 windows in ``[ORIGIN, ORIGIN + span)``: single days, spans, a window nested in another, an overlapping one,
    a touching one, a repeated one, and disjoint ones — shuffled."""
    windows: list[Window] = []
    for _ in range(rng.randint(1, 7)):
        kind = rng.choice(("single", "span", "nested", "overlap", "touch", "repeat", "span"))
        if kind in ("nested", "overlap", "touch", "repeat") and windows:
            first, last = rng.choice(windows)
            if kind == "nested" and last > first:
                inner_first = first + timedelta(days=rng.randint(0, (last - first).days))
                windows.append((inner_first, inner_first + timedelta(days=rng.randint(0, (last - inner_first).days))))
            elif kind == "overlap":
                start = first + timedelta(days=rng.randint(0, (last - first).days))
                windows.append((start, last + timedelta(days=rng.randint(1, 9))))
            elif kind == "touch":
                windows.append((last + timedelta(days=1), last + timedelta(days=rng.randint(1, 6))))
            else:
                windows.append((first, last))
            continue
        first = ORIGIN + timedelta(days=rng.randrange(span))
        windows.append((first, first) if kind == "single" else (first, first + timedelta(days=rng.randint(1, 15))))
    rng.shuffle(windows)
    return windows


def _random_steps(rng: random.Random, source: str, destination: str, span: int) -> UnitRateSteps:
    """A hand-built step function: 0–12 step days anywhere in ``[ORIGIN - 10, ORIGIN + span + 10)``, inside the windows or
    not — the view must read it only inside them."""
    days = tuple(sorted({ORIGIN + timedelta(days=rng.randrange(-10, span + 10)) for _ in range(rng.randint(0, 12))}))
    return UnitRateSteps(source=source, destination=destination, days=days, values=tuple(_value(rng) for _ in days), rate_days=tuple(day - timedelta(days=rng.randint(0, 3)) for day in days))


_PAIRS: tuple[Pair, ...] = (("USD", "EUR"), ("EUR", "USD"), ("CHF", "EUR"), ("GBP", "JPY"))
_TO_EUR: tuple[Pair, ...] = (("USD", "EUR"), ("CHF", "EUR"), ("GBP", "EUR"))


def _random_case(seed: int, pairs: Sequence[Pair]) -> tuple[dict[Pair, UnitRateSteps], dict[Pair, list[Window]]]:
    rng = random.Random(seed)
    chosen = rng.sample(list(pairs), rng.randint(1, len(pairs)))
    span = rng.choice((20, 45, 90))
    steps = {pair: _random_steps(rng, *pair, span) for pair in chosen}
    windows = {pair: _random_windows(rng, span) for pair in chosen}
    return steps, windows


@dataclass(frozen=True)
class _AtOnly:
    """Steps that answer ``.at`` and nothing else: what the contract asks of a step object for the mapping."""

    days: tuple[date, ...]
    values: tuple[Decimal, ...]

    def at(self, day: date) -> Decimal | None:
        index = bisect_right(self.days, day) - 1
        return self.values[index] if index >= 0 else None


def _d(offset: int) -> date:
    return ORIGIN + timedelta(days=offset)


#: Named shapes, ``{pair: (step days as offsets, windows as offset pairs)}``: what each one is there to catch.
_NAMED_SHAPES = {
    # a row between two windows (offset 10) is a step of the hand-built function: the view must not read it on 6..14
    "two-disjoint-windows-a-step-between": {("USD", "EUR"): ((0, 3, 10, 16), ((0, 5), (15, 20)))},
    # (3, 5) inside (0, 12): a bisect on window starts over unmerged windows finds (3, 5) for day 8 and misses it
    "a-window-nested-in-another": {("USD", "EUR"): ((-2, 4, 9), ((0, 12), (3, 5)))},
    "two-overlapping-windows": {("USD", "EUR"): ((-1, 6, 11), ((0, 8), (5, 14)))},
    "two-touching-windows": {("CHF", "EUR"): ((-3, 5, 6), ((0, 5), (6, 9)))},
    "the-same-window-twice": {("CHF", "EUR"): ((0, 2), ((0, 4), (0, 4)))},
    "single-days-before-and-inside": {("USD", "EUR"): ((-30, 2, 7), ((-20, -20), (-5, -5), (0, 9), (4, 4)))},
    # the first step after the first window starts: None on its first days, and nothing on the window before any step
    "windows-before-the-first-step": {("GBP", "EUR"): ((6, 8), ((0, 2), (4, 10)))},
    "a-pair-without-steps": {("JPY", "EUR"): ((), ((0, 6),)), ("USD", "EUR"): ((1,), ((0, 3),))},
    "steps-after-every-window": {("USD", "EUR"): ((30, 40), ((0, 5), (10, 12)))},
}


def _named_case(name: str) -> tuple[dict[Pair, UnitRateSteps], dict[Pair, list[Window]]]:
    steps: dict[Pair, UnitRateSteps] = {}
    windows: dict[Pair, list[Window]] = {}
    for index, (pair, (step_offsets, window_offsets)) in enumerate(_NAMED_SHAPES[name].items()):
        days = tuple(_d(offset) for offset in step_offsets)
        values = tuple(Decimal(_LONG_DIGITS[(index + position) % len(_LONG_DIGITS)]) for position in range(len(days)))
        steps[pair] = UnitRateSteps(source=pair[0], destination=pair[1], days=days, values=values, rate_days=days)
        windows[pair] = [(_d(first), _d(last)) for first, last in window_offsets]
    return steps, windows


# =============================================================================
# 0 — THE FIXTURES (GREEN ON HEAD: THEY NEVER TOUCH THE CURE)
# =============================================================================


class TestTheFixtures:
    def test_the_random_windows_cover_every_shape(self):
        """Across the seeds the random windows hold single days, nested, overlapping, touching, repeated and disjoint
        windows, and step days outside every window: the cases the view must not get wrong."""
        print_section("P3 fixtures: the random windows cover every shape")
        seen: set[str] = set()
        for seed in SEEDS:
            steps, windows = _random_case(seed, _PAIRS)
            for pair, pair_windows in windows.items():
                ordered = sorted(pair_windows)
                seen.update("single" for first, last in ordered if first == last)
                for (first_a, last_a), (first_b, last_b) in zip(ordered, ordered[1:], strict=False):
                    if (first_a, last_a) == (first_b, last_b):
                        seen.add("repeat")
                    elif first_b <= last_a and last_b <= last_a:
                        seen.add("nested")
                    elif first_b <= last_a:
                        seen.add("overlap")
                    elif first_b == last_a + timedelta(days=1):
                        seen.add("touch")
                    else:
                        seen.add("disjoint")
                inside = {day for first, last in ordered for day in _days(first, last)}
                if any(day not in inside for day in steps[pair].days):
                    seen.add("step-off-windows")
        wanted = {"single", "repeat", "nested", "overlap", "touch", "disjoint", "step-off-windows"}
        assert wanted <= seen, f"the random corpus misses the shapes {sorted(wanted - seen)}"
        print_success(f"✓ {len(SEEDS)} seeds cover {sorted(seen)}")

    @pytest.mark.parametrize("seed", SEEDS)
    def test_the_native_windows_ask_the_days_of_today(self, seed):
        """The windows the native-cash fixtures build (``_native_windows``) cover exactly the days HEAD's
        ``_unit_requests`` asks, per currency: the view is built on the days of today."""
        book = _random_book(seed)
        problems = _window_days_problems(book)
        assert not problems, f"seed {seed}: the fixture's windows are not the days of today:{_show(problems)}"

    def test_the_named_book_has_what_it_claims(self):
        """The named book holds a movement before the floor, a stored rate strictly between two windows of one
        currency, and a currency whose first rate comes after its first movement; its windows are the days of today."""
        print_section("P3 fixtures: the named native-cash book")
        book = _named_book()
        assert any(movement.date < FLOOR for movement in book.movements if movement.currency != REPORT and movement.amount != 0), "no foreign movement before the floor"
        between = [(currency, day) for (currency, _report), pair_windows in book.windows.items() for (_first_a, last_a), (first_b, _last_b) in zip(sorted(pair_windows), sorted(pair_windows)[1:], strict=False) for day in book.rows[currency] if last_a < day < first_b]
        assert between, "no stored rate strictly between two windows of one currency"
        late = [currency for currency, rows in book.rows.items() if min(rows) > min(movement.date for movement in book.movements if movement.currency == currency)]
        assert late == ["GBP"], f"the currencies whose first rate comes after their first movement are {late}, expected GBP"
        assert not _window_days_problems(book)
        print_success(f"✓ before the floor, a rate between windows {between}, GBP's first rate after its first movement")


# =============================================================================
# 1 — THE VIEW IS THE DICT OF TODAY
# =============================================================================


class TestTheViewIsTheDictOfToday:
    @pytest.mark.parametrize("seed", SEEDS)
    def test_random_steps_and_windows(self, seed):
        """Keys ``(src, dst, day)``: the view equals the dict of today on 30 random cases, and answers nothing off the
        windows or before the first step."""
        steps, windows = _random_case(seed, _PAIRS)
        view = _view(steps, windows)
        problems = _mapping_problems(view, _dense_today(steps, windows), _probe_keys(steps, windows, None))
        assert not problems, f"seed {seed}: AskedDayRates is not the dict of today ({len(problems)} problem(s)); windows {windows}:{_show(problems)}"

    @pytest.mark.parametrize("name", sorted(_NAMED_SHAPES))
    def test_named_shapes(self, name):
        """The shapes the cure could get wrong, one by one: a step between two windows, a nested window, overlapping,
        touching and repeated windows, single days, a window before the first step, a pair without steps."""
        print_section(f"P3 AskedDayRates: {name}")
        steps, windows = _named_case(name)
        view = _view(steps, windows)
        problems = _mapping_problems(view, _dense_today(steps, windows), _probe_keys(steps, windows, None))
        assert not problems, f"{name}: AskedDayRates is not the dict of today ({len(problems)} problem(s)):{_show(problems)}"
        print_success(f"✓ {name}: {len(view)} asked days with a rate, nothing else")

    @pytest.mark.parametrize("seed", SEEDS[:10])
    def test_steps_that_only_answer_at(self, seed):
        """The mapping needs nothing from a step object but ``.at(day)``."""
        steps, windows = _random_case(seed, _PAIRS)
        stubs = {pair: _AtOnly(days=pair_steps.days, values=pair_steps.values) for pair, pair_steps in steps.items()}
        view = _view(stubs, windows)
        problems = _mapping_problems(view, _dense_today(stubs, windows), _probe_keys(stubs, windows, None))
        assert not problems, f"seed {seed}: AskedDayRates over .at-only steps is not the dict of today:{_show(problems)}"

    @pytest.mark.parametrize("seed", SEEDS)
    def test_fixed_destination_keys_are_source_and_day(self, seed):
        """With ``fixed_destination`` the keys are ``(src, day)``, as ``NativeCash.unit_rates`` has them today."""
        steps, windows = _random_case(seed, _TO_EUR)
        view = _view(steps, windows, fixed_destination=REPORT)
        dense = _dense_today(steps, windows, fixed_destination=REPORT)
        problems = _mapping_problems(view, dense, _probe_keys(steps, windows, REPORT))
        assert not problems, f"seed {seed}: AskedDayRates(fixed_destination={REPORT}) is not the dict of today:{_show(problems)}"
        assert all(len(key) == 2 for key in view), f"seed {seed}: a key of the view is not (src, day): {[key for key in view if len(key) != 2][:3]}"

    def test_windows_given_as_one_shot_iterators(self):
        """``windows`` values are ``Iterable``: a one-shot iterator is read once and fully, as a list would be."""
        print_section("P3 AskedDayRates: windows as one-shot iterators")
        steps, windows = _named_case("a-window-nested-in-another")
        view = _view(steps, {pair: iter(list(pair_windows)) for pair, pair_windows in windows.items()})
        problems = _mapping_problems(view, _dense_today(steps, windows), _probe_keys(steps, windows, None))
        assert not problems, f"AskedDayRates over one-shot window iterators is not the dict of today:{_show(problems)}"
        print_success("✓ one-shot iterators read as lists")

    def test_an_unknown_pair_and_odd_days_answer_nothing(self):
        """A pair never asked, and a day of an asked pair outside its windows, give None from ``.get`` and are not in."""
        print_section("P3 AskedDayRates: an unknown pair answers nothing")
        steps, windows = _named_case("two-disjoint-windows-a-step-between")
        view = _view(steps, windows)
        for key in (("CHF", "EUR", _d(1)), ("EUR", "USD", _d(1)), ("USD", "EUR", _d(10)), ("USD", "EUR", _d(-1)), ("USD", "EUR", _d(21))):
            assert view.get(key) is None, f".get({key}) is {view.get(key)!r}: not asked, expected None"
            assert key not in view, f"{key} is in the view: not asked"
        assert view.get(("USD", "EUR", _d(16))) == steps[("USD", "EUR")].at(_d(16)), "a day inside the second window reads its step"
        print_success("✓ None off the windows and for a pair never asked")


# =============================================================================
# 1b — THE CONTRACT POINTS OF THE CURE (MF's answers of 2026-10-20, pinned one by one)
# =============================================================================


def _merged_windows() -> Any:
    """``financial_math/fx_rates.py::merged_windows``, read when a test runs (absent before the cure)."""
    merged = getattr(fx_rates_module, "merged_windows", None)
    if merged is None:
        pytest.fail("P3: financial_math/fx_rates.py has no merged_windows yet (red by absence, before the cure)")
    return merged


class TestTheContractPoints:
    """MF's answers to the ambiguities of the first hand-over, each pinned so that a mutant of it shows:
    (1) ``step_series()`` raises ``ValueError`` without ``fixed_destination``; (3) a pair with no steps is absent from it;
    (4) ``merged_windows`` leaves out a window that ends before it starts, joins overlapping and touching ones;
    (6) a day of another type is ``KeyError`` (``.get`` None); (7) with ``fixed_destination``, the pairs into another
    destination are ignored — steps and windows; (8) read-only: a ``Mapping``, never a ``MutableMapping``."""

    def test_step_series_needs_a_fixed_destination(self):
        """(1) Without ``fixed_destination`` two pairs from one source would collide on one key: refused."""
        print_section("P3 contract (1): step_series without a fixed destination")
        steps, windows = _named_case("two-overlapping-windows")
        with pytest.raises(ValueError):
            _view(steps, windows).step_series()
        print_success("✓ ValueError")

    def test_a_pair_without_steps_is_absent_from_the_series(self):
        """(3) JPY has no step at all: ``step_series()`` has no JPY key (not an empty series); USD keeps its own."""
        print_section("P3 contract (3): a pair without steps is absent")
        steps, windows = _named_case("a-pair-without-steps")
        series = _view(steps, windows, fixed_destination=REPORT).step_series()
        assert set(series) == {"USD"}, f"step_series() keys are {sorted(series)}: a source without a step is absent"
        assert tuple(series["USD"][0]) == steps[("USD", "EUR")].days
        print_success("✓ JPY absent, USD's steps kept")

    @pytest.mark.parametrize(
        ("windows", "expected"),
        [
            pytest.param([(_d(5), _d(4))], (), id="a-reversed-window-alone"),
            pytest.param([(_d(0), _d(2)), (_d(9), _d(3)), (_d(4), _d(6))], ((_d(0), _d(2)), (_d(4), _d(6))), id="a-reversed-window-among-others"),
            pytest.param([(_d(4), _d(6)), (_d(0), _d(2)), (_d(3), _d(3))], ((_d(0), _d(6)),), id="touching-windows-joined-in-any-order"),
            pytest.param([(_d(0), _d(10)), (_d(3), _d(5)), (_d(8), _d(14)), (_d(20), _d(20))], ((_d(0), _d(14)), (_d(20), _d(20))), id="nested-and-overlapping-joined"),
            pytest.param([], (), id="no-window"),
        ],
    )
    def test_merged_windows(self, windows, expected):
        """(4) ``merged_windows``: ascending, overlapping or touching windows joined, a window ending before it starts
        left out."""
        merged = tuple(tuple(window) for window in _merged_windows()(iter(windows)))
        assert merged == expected, f"merged_windows({windows}) is {merged}, expected {expected}"

    def test_a_day_of_another_type_is_absent(self):
        """(6) A ``datetime`` day, a key of the wrong length, a string: ``KeyError``, so ``.get`` None — as a dict keyed
        by dates."""
        print_section("P3 contract (6): odd keys")
        steps, windows = _named_case("two-overlapping-windows")
        view = _view(steps, windows)
        fixed = _view(steps, windows, fixed_destination=REPORT)
        moment = datetime(ORIGIN.year, ORIGIN.month, ORIGIN.day + 2, 12, 0)
        for mapping, key in ((view, ("USD", "EUR", moment)), (view, ("USD", "EUR")), (view, "USD"), (fixed, ("USD", moment)), (fixed, ("USD", "EUR", _d(2)))):
            assert mapping.get(key) is None, f".get({key!r}) is {mapping.get(key)!r}: expected None"
            with pytest.raises(KeyError):
                mapping[key]
        assert view.get(("USD", "EUR", _d(2))) is not None, "precondition: the same day as a date is asked and has a rate"
        print_success("✓ KeyError for a datetime, a short key, a string")

    def test_fixed_destination_ignores_the_pairs_into_another_destination(self):
        """(7) Steps and windows of ``USD→CHF`` and ``GBP→CHF`` beside ``USD→EUR``: with ``fixed_destination`` EUR the view
        is the dict of today of ``USD→EUR`` alone — in ``[]``, in the walk, in ``len`` — and ``step_series()`` holds USD's
        EUR steps only (GBP, into CHF only, is absent)."""
        print_section("P3 contract (7): pairs into another destination are ignored")
        eur_steps, eur_windows = _named_case("two-disjoint-windows-a-step-between")
        other = {("USD", "CHF"): ((-3, 1, 7, 18), ((0, 25),)), ("GBP", "CHF"): ((-1, 4), ((0, 9),))}
        steps = dict(eur_steps)
        windows = {pair: list(asked) for pair, asked in eur_windows.items()}
        for pair, (offsets, window_offsets) in other.items():
            days = tuple(_d(offset) for offset in offsets)
            steps[pair] = UnitRateSteps(source=pair[0], destination=pair[1], days=days, values=tuple(Decimal("9.99") for _ in days), rate_days=days)
            windows[pair] = [(_d(first), _d(last)) for first, last in window_offsets]
        view = _view(steps, windows, fixed_destination=REPORT)
        dense = _dense_today(eur_steps, eur_windows, fixed_destination=REPORT)
        problems = _mapping_problems(view, dense, _probe_keys(steps, windows, REPORT))
        assert not problems, f"AskedDayRates(fixed_destination=EUR) reads a pair into CHF:{_show(problems)}"
        series = view.step_series()
        assert set(series) == {"USD"} and tuple(series["USD"][0]) == eur_steps[("USD", "EUR")].days, f"step_series() is {series}: only USD→EUR's steps"
        print_success("✓ only USD→EUR is read")

    def test_the_view_is_read_only(self):
        """(8) The engine's worker threads read it: a ``Mapping``, with no way to write it."""
        steps, windows = _named_case("two-overlapping-windows")
        view = _view(steps, windows)
        assert isinstance(view, Mapping) and not isinstance(view, MutableMapping), f"{type(view).__name__} is not a read-only Mapping"
        before = dict(view.items())
        _ = [view.get(key) for key in _probe_keys(steps, windows, None)]
        assert dict(view.items()) == before, "reading the view changed it"


# =============================================================================
# 2 — step_series(): THE STEPS OF EACH PAIR, ANCHORS INCLUDED
# =============================================================================


def _series_problems(view: Mapping, steps: Mapping[Pair, UnitRateSteps]) -> list[str]:
    """``view.step_series()`` against each pair's ``(days, values)``; a pair without steps is absent (contract point 3)."""
    series = view.step_series()
    expected = {source: (tuple(pair_steps.days), tuple(_bits(value) for value in pair_steps.values)) for (source, _destination), pair_steps in steps.items() if pair_steps.days}
    found = {source: (tuple(days), tuple(_bits(value) for value in values)) for source, (days, values) in series.items()}
    problems = []
    for source in sorted(set(expected) | set(found)):
        if expected.get(source) != found.get(source):
            want_days, got_days = expected.get(source, ((), ()))[0], found.get(source, ((), ()))[0]
            problems.append(f"{source}: step_series days {list(got_days)}, the steps' {list(want_days)} (missing {sorted(set(want_days) - set(got_days))}, extra {sorted(set(got_days) - set(want_days))}); values equal: {expected.get(source, ((), ()))[1] == found.get(source, ((), ()))[1]}")
    return problems


class TestStepSeries:
    @pytest.mark.parametrize("seed", SEEDS)
    def test_step_series_is_the_steps_of_each_pair(self, seed):
        """``step_series()`` is ``{src: (days, values)}`` of the steps as ``unit_rate_steps`` builds them on the windows
        asked — every window's anchor step included."""
        book = _random_book(seed)
        view = _view(book.steps, book.windows, fixed_destination=REPORT)
        problems = _series_problems(view, book.steps)
        assert not problems, f"seed {seed}: step_series() is not the steps:{_show(problems)}"

    def test_the_anchor_of_every_window_is_a_step(self):
        """The named book: each window's first day is a step read from an older row (1899-11-20 from 1899-10-15,
        1899-12-25 from 1899-12-20, 1900-01-01 from 1899-12-20 for USD; 1900-01-05 from 1899-06-01 for CHF)."""
        print_section("P3 step_series: the anchor steps")
        book = _named_book()
        view = _view(book.steps, book.windows, fixed_destination=REPORT)
        problems = _series_problems(view, book.steps)
        assert not problems, f"step_series() is not the steps of the named book:{_show(problems)}"
        anchors = {("USD", date(1899, 11, 20)), ("USD", date(1899, 12, 25)), ("USD", FLOOR), ("CHF", date(1900, 1, 5))}
        series = view.step_series()
        missing = sorted(anchor for anchor in anchors if anchor[1] not in tuple(series.get(anchor[0], ((), ()))[0]))
        assert not missing, f"step_series() drops the anchor steps {missing}"
        print_success(f"✓ {len(anchors)} anchor steps kept")


# =============================================================================
# 3 — THE NATIVE CASH FROM THE VIEW IS THE NATIVE CASH FROM THE DICT
# =============================================================================


@dataclass(frozen=True)
class _Book:
    """A native-cash book: movements, their conversions, the usable rows of each currency (unit values), the asked
    windows, X's steps on them, and the dense dict of the asked days."""

    movements: tuple[CashMovement, ...]
    converted: tuple[Decimal | None, ...]
    rates_until: date | None
    rows: dict[str, dict[date, Decimal]]
    windows: dict[Pair, list[Window]]
    steps: dict[Pair, UnitRateSteps]
    dense: dict[tuple[str, date], Decimal]

    def foreign(self) -> list[CashMovement]:
        """The movements whose unit rate is asked: foreign, non-zero (``compute_native_cash``'s ``amount_indexes``)."""
        return [movement for movement in self.movements if movement.currency != REPORT and movement.amount != 0]

    def frame(self) -> list[date]:
        """Every day from before the first movement to after the last day a rate is asked."""
        last = max([movement.date for movement in self.movements] + ([self.rates_until] if self.rates_until else []))
        return _days(min(movement.date for movement in self.movements) - timedelta(days=3), last + timedelta(days=12))


def _converted(movement: CashMovement, rows: Mapping[str, Mapping[date, Decimal]]) -> Decimal | None:
    """The movement in the report currency at its date: as ``compute_native_cash`` keeps it (a report or zero amount as it
    is), else ``amount ×`` the last row on or before its date, None without one (backward fill, no limit)."""
    if movement.currency == REPORT or movement.amount == 0:
        return movement.amount
    known = [day for day in rows.get(movement.currency, {}) if day <= movement.date]
    return movement.amount * rows[movement.currency][max(known)] if known else None


def _book(movements: Sequence[CashMovement], rows: dict[str, dict[date, Decimal]], rates_until: date | None) -> _Book:
    movements = tuple(movements)
    foreign = [movement for movement in movements if movement.currency != REPORT and movement.amount != 0]
    windows = _native_windows(foreign, rates_until)
    steps = {pair: _steps_like_unit_rate_steps(pair[0], pair[1], rows.get(pair[0], {}), pair_windows) for pair, pair_windows in windows.items()}
    dense: dict[tuple[str, date], Decimal] = {}
    for currency, day in _unit_requests_today(foreign, rates_until):
        value = steps[(currency, REPORT)].at(day)
        if value is not None:
            dense[(currency, day)] = value
    return _Book(movements=movements, converted=tuple(_converted(movement, rows) for movement in movements), rates_until=rates_until, rows=rows, windows=windows, steps=steps, dense=dense)


def _window_days_problems(book: _Book) -> list[str]:
    asked: dict[str, set[date]] = {}
    for currency, day in _unit_requests_today(book.foreign(), book.rates_until):
        asked.setdefault(currency, set()).add(day)
    built = {source: {day for first, last in pair_windows for day in _days(first, last)} for (source, _destination), pair_windows in book.windows.items()}
    return [
        f"{currency}: windows ask {len(built.get(currency, set()))} days, today {len(asked.get(currency, set()))}; missing {sorted(asked.get(currency, set()) - built.get(currency, set()))[:3]}, extra {sorted(built.get(currency, set()) - asked.get(currency, set()))[:3]}"
        for currency in sorted(set(asked) | set(built))
        if asked.get(currency, set()) != built.get(currency, set())
    ]


def _move(day: date, currency: str, amount: str, broker_id: int = 1, *, kind: str = "DEPOSIT", share: str = "1", asset_id: int | None = None) -> CashMovement:
    return CashMovement(movement_id=None, transaction_type=kind, date=day, broker_id=broker_id, asset_id=asset_id, currency=currency, amount=Decimal(amount), share=Decimal(share))


def _named_book() -> _Book:
    """USD: rows on 1899-10-15, 1899-12-20 (strictly between its two early windows), 1900-01-10, 1900-02-01 and 02-02
    (the same rate twice), 1900-03-15; movements on 1899-11-20 and 1899-12-25 (before the floor: single-day windows),
    1900-01-20, 1900-03-01, and a zero one on 1899-11-01 (never asked). CHF: rows from 1899-06-01, one movement on
    1900-01-05. GBP: a movement on 1900-01-03 before its first row (1900-01-12, not converted), one on 1900-02-10. A
    report-currency movement. Rates until 1900-03-31. No two currencies change on the same day."""
    rows = {
        "USD": {date(1899, 10, 15): Decimal("0.80"), date(1899, 12, 20): Decimal("0.9227646027498385161945187783"), date(1900, 1, 10): Decimal("0.75"), date(1900, 2, 1): Decimal("0.7000000000"), date(1900, 2, 2): Decimal("0.7000000000"), date(1900, 3, 15): Decimal("0.72")},
        "CHF": {date(1899, 6, 1): Decimal("1.0234567891"), date(1900, 1, 25): Decimal("1.05"), date(1900, 3, 20): Decimal("1.01")},
        "GBP": {date(1900, 1, 12): Decimal("1.2643210987"), date(1900, 2, 20): Decimal("1.25")},
    }
    movements = [
        _move(date(1899, 11, 1), "USD", "0.00", kind="FEE"),
        _move(date(1899, 11, 20), "USD", "1000.00"),
        _move(date(1899, 12, 25), "USD", "-200", kind="WITHDRAWAL"),
        _move(date(1900, 1, 3), "GBP", "700"),
        _move(date(1900, 1, 5), "CHF", "500", broker_id=2),
        _move(date(1900, 1, 15), REPORT, "50.0", broker_id=3),
        _move(date(1900, 1, 20), "USD", "300", broker_id=2, share="0.5"),
        _move(date(1900, 2, 10), "GBP", "100", kind="DIVIDEND", asset_id=7),
        _move(date(1900, 3, 1), "USD", "-100", kind="FEE"),
    ]
    return _book(movements, rows, date(1900, 3, 31))


def _random_book(seed: int) -> _Book:
    """5–14 movements around the floor (about a third before it), in USD, CHF, GBP or the report currency, some zero, at
    three brokers with shares; each currency's rows scattered before, between and after the movements (sometimes all
    after the first one); ``rates_until`` None, inside the history or after it."""
    rng = random.Random(1000 + seed)
    start = date(1899, 10, 1)
    rows: dict[str, dict[date, Decimal]] = {}
    for currency in ("USD", "CHF", "GBP"):
        first_row = rng.randrange(-60, 120)
        rows[currency] = {start + timedelta(days=rng.randrange(first_row, 200)): _value(rng) for _ in range(rng.randint(0, 9))}
    movements = []
    for _ in range(rng.randint(5, 14)):
        day = start + timedelta(days=rng.randrange(0, 92) if rng.random() < 0.35 else rng.randrange(92, 200))
        currency = rng.choice(("USD", "CHF", "GBP", "USD", REPORT))
        amount = "0" if rng.random() < 0.1 else str(Decimal(rng.randint(-500, 2000)) / Decimal(rng.choice((1, 10, 100))))
        movements.append(_move(day, currency, amount, broker_id=rng.choice((1, 2, 3)), kind=rng.choice(("DEPOSIT", "WITHDRAWAL", "FEE", "DIVIDEND")), share=rng.choice(("1", "0.5", "0.25"))))
    rates_until = rng.choice((None, start + timedelta(days=rng.randrange(80, 260))))
    return _book(movements, rows, rates_until)


def _outcome(call: Callable[[], Any]) -> object:
    """What a call answers, compared to the digit: a dict's values as ``as_tuple()``, a tuple as it is, or the class of
    the ``ValueError`` it raised (a counted balance without a rate)."""
    try:
        answer = call()
    except ValueError as error:
        return ("raises", type(error).__name__)
    if isinstance(answer, dict):
        return {key: (_bits_dict(value) if isinstance(value, dict) else _bits(value)) for key, value in answer.items()}
    return answer


def _native_cash(book: _Book, unit_rates: Mapping) -> NativeCash:
    return NativeCash(report_currency=REPORT, movements=book.movements, converted=book.converted, unit_rates=unit_rates)


def _reading_windows(frame: list[date]) -> list[tuple[date | None, date]]:
    """The ``(date_from, date_to)`` the parity reads ``rate_change_days`` and ``exchange_results`` on: the whole frame,
    open and closed, the days around the floor, and windows of a few lengths inside the frame."""
    last_index = len(frame) - 1
    windows: list[tuple[date | None, date]] = [(None, frame[-1]), (frame[0], frame[-1]), (FLOOR - timedelta(days=1), FLOOR + timedelta(days=40))]
    windows += [(frame[min(index, last_index)], frame[min(index + step, last_index)]) for index, step in ((5, 17), (30, 9), (60, 45), (len(frame) // 2, 3))]
    return windows


def _window_reading_problems(from_view: NativeCash, from_dict: NativeCash, frame: list[date], label: str) -> list[str]:
    """``rate_change_days`` and ``exchange_results`` of the two native cashes on every reading window."""
    problems: list[str] = []
    for date_from, date_to in _reading_windows(frame):
        view_days, dict_days = from_view.rate_change_days(date_from, date_to), from_dict.rate_change_days(date_from, date_to)
        if view_days != dict_days:
            problems.append(f"{label} rate_change_days({date_from}, {date_to}): view {list(view_days)}, dict {list(dict_days)}")
        if date_from is None or date_from >= date_to:
            continue
        view_results, dict_results = _outcome(lambda a=date_from, b=date_to: from_view.exchange_results(a, b)), _outcome(lambda a=date_from, b=date_to: from_dict.exchange_results(a, b))
        if view_results != dict_results:
            problems.append(f"{label} exchange_results({date_from}, {date_to}): view {view_results}, dict {dict_results}")
    return problems


def _native_cash_problems(book: _Book, label: str) -> list[str]:
    """``NativeCash`` from the view against ``NativeCash`` from the dense dict: every reading, on every day."""
    from_view = _native_cash(book, _view(book.steps, book.windows, fixed_destination=REPORT))
    from_dict = _native_cash(book, book.dense)
    frame = book.frame()
    problems = [f"{label} value_at({day}): view {view_value}, dict {dict_value}" for day in frame if (view_value := _outcome(lambda day=day: from_view.value_at(day))) != (dict_value := _outcome(lambda day=day: from_dict.value_at(day)))]
    problems += _window_reading_problems(from_view, from_dict, frame, label)
    if [_bits(value) for value in from_view.converted] != [_bits(value) for value in from_dict.converted]:
        problems.append(f"{label} converted: view {from_view.converted}, dict {from_dict.converted}")
    problems += [f"{label} balances({as_of}) differ" for as_of in (None, frame[0], FLOOR, frame[len(frame) // 2], frame[-1]) if _outcome(lambda as_of=as_of: from_view.balances(as_of)) != _outcome(lambda as_of=as_of: from_dict.balances(as_of))]
    if from_view.foreign_cash_broker_ids != from_dict.foreign_cash_broker_ids:
        problems.append(f"{label} foreign_cash_broker_ids: view {sorted(from_view.foreign_cash_broker_ids)}, dict {sorted(from_dict.foreign_cash_broker_ids)}")
    return problems


class TestTheNativeCashFromTheView:
    def test_the_named_book(self):
        """Movements before the floor (single-day windows), a stored rate between two windows that must stay unread
        (USD on 1899-12-21..24 is still the 1899-10-15 rate in both), GBP's first rate after its first movement, a
        repeated rate: the two native cashes agree on every day and every reading."""
        print_section("P3 NativeCash: from the view and from the dict of today, the named book")
        book = _named_book()
        problems = _native_cash_problems(book, "named")
        assert not problems, f"NativeCash(unit_rates=view) differs from NativeCash(unit_rates=dict) ({len(problems)} problem(s)):{_show(problems)}"
        print_success(f"✓ {len(book.frame())} days, every reading equal; {len(book.dense)} dense rates, {sum(len(steps.days) for steps in book.steps.values())} steps")

    def test_the_named_book_reads_the_rate_of_today_between_two_windows(self):
        """Pinned figures, not only parity: on 1899-12-22 the 1000 USD of 1899-11-20 are worth 1000 × 0.80 (the anchor
        of the asked day 1899-11-20), not × the 1899-12-20 row nobody asked; on 1899-12-26 the 800 USD left are worth
        800 × 0.9227646027498385161945187783 (the anchor of 1899-12-25); and GBP appears in the change days on
        1900-01-12, its first rate."""
        print_section("P3 NativeCash: the named book's figures")
        book = _named_book()
        cash = _native_cash(book, _view(book.steps, book.windows, fixed_destination=REPORT))
        assert _bits(cash.value_at(date(1899, 12, 22)).get(1)) == _bits(Decimal("1000.00") * Decimal("0.80"))
        assert _bits(cash.value_at(date(1899, 12, 26)).get(1)) == _bits(Decimal("800.00") * Decimal("0.9227646027498385161945187783"))
        days = cash.rate_change_days(None, date(1900, 3, 31))
        assert date(1900, 1, 12) in days and date(1900, 1, 5) in days and date(1899, 11, 20) in days, f"the first rate of each held currency is a change day: {list(days)}"
        print_success("✓ the rate between two windows stays unread; first rates are change days")

    @pytest.mark.parametrize("seed", SEEDS)
    def test_random_books(self, seed):
        book = _random_book(seed)
        problems = _native_cash_problems(book, f"seed {seed}")
        assert not problems, f"seed {seed}: NativeCash(unit_rates=view) differs from NativeCash(unit_rates=dict) ({len(problems)} problem(s)):{_show(problems)}"


# =============================================================================
# 4 — THE COST: THE NATIVE CASH'S SERIES ARE THE STEPS, NOT EVERY ASKED DAY
# =============================================================================


class TestTheNativeCashCost:
    @pytest.mark.parametrize("seed", [None, *SEEDS[:10]])
    def test_the_rate_series_hold_no_more_days_than_the_steps(self, seed):
        """``NativeCash(unit_rates=view)._rate_days[ccy]`` is no longer than the steps of ``ccy``: the calendar of the
        change days is the steps, not every asked day (today ``_rate_series`` walks the Mapping: one day per asked day).
        ``seed`` None is the named book, whose USD window alone asks 90 days for 5 steps."""
        book = _named_book() if seed is None else _random_book(seed)
        cash = _native_cash(book, _view(book.steps, book.windows, fixed_destination=REPORT))
        too_long = {source: (len(cash._rate_days.get(source, ())), len(steps.days)) for (source, _destination), steps in book.steps.items() if len(cash._rate_days.get(source, ())) > len(steps.days)}
        assert not too_long, f"{'named book' if seed is None else f'seed {seed}'}: NativeCash keeps more rate days than steps, (rate days, steps) by currency: {too_long} — the series are not the steps"

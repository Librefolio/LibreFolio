"""P3 of MF's fast formulas (release 1.3, workstream X) — ``unit_rate_steps``: one unit of a currency in another as a
calendar of steps, answering on every day of the windows asked exactly what ``convert_bulk`` answers.

The function (``services/fx/conversion.py``, written after these reds). ``unit_rate_steps(session, requests)`` takes
``{(source, destination): [(first_day, last_day), …]}`` — two currency codes as stored, windows with both days included,
which may touch, overlap or lie apart — and answers one ``UnitRateSteps`` per pair asked: ``days`` (ascending),
``values`` (one unit of ``source`` in ``destination`` from ``days[i]`` on), ``rate_days`` (the date of the stored row
each value comes from), ``at(day)`` and ``rate_day_at(day)`` (the last step on or before ``day``, None before the first).
The steps of a pair are the first day of each window, with the backward-fill anchor — the last usable row on or before
that day; no step when the pair has none by then —, plus every day inside a window with a usable row of the pair; rows
strictly between two windows are no steps. Today the engine (``_preload_fx_rates``) and the native cash
(``compute_native_cash``) ask ``convert_bulk`` for ``Currency(1, source)`` in ``destination`` on every day; the steps
give the same answers once per rate change.

The contract (MF, the owner of the consumers), pinned here:

- (n1) the arithmetic of ``convert_bulk``: ``Decimal("1") * rate`` when ``source`` is the stored base, ``Decimal("1") /
  rate`` otherwise, in the same decimal context. The rates have long inverses (1 / 1.0837 =
  0.9227646027498385161945187783), so another context, another rounding or a normalised value shows in ``as_tuple()``;
- (n2) the rows of ``convert_bulk``: X-R38's usable filter, 1E-10 <= rate < 1E+14 (``usable_fx_rate_bounds()``), in the
  anchor and in the window — 0, 1E-11, -1.5, inf, 1E+14 and 1E+19 planted as the would-be anchor, on the first day,
  inside and on the last day are skipped like a missing date, 1E-10 and 99999999999999 are read —, and its chunks of
  500 pairs per query (``FX_PAIRS_PER_QUERY``), counted on the engine at 501 and 1 035 distinct stored pairs;
- (n3) ``rate_days`` are the dates of the rows used; a window's first step falls on its first day, with the anchor's
  row; before the first usable row, None;
- (n4) two consecutive rows with the same rate are two steps;
- (n5) a pair of one currency, and a window whose last day comes before its first, raise ``ValueError``;
- (n6) THE ORACLE (``_steps_matching_convert_bulk``): on every day of every window, ``at(day)`` is the amount of
  ``convert_bulk(session, [(Currency(code=source, amount=Decimal("1")), destination, day)], raise_on_error=False)`` bit
  for bit (``as_tuple()``, not only ``==``) and ``rate_day_at(day)`` its rate date; where ``convert_bulk`` has no rate,
  both are None. One ``convert_bulk`` call holds every day of the request: it answers each day as a call of its own.

Beside the oracle, the calendar: ``days`` are the first day of each window that has an anchor plus the usable row days
inside the windows, ascending and once each, and ``rate_days`` their rows' dates. It pins the steps the values cannot
show — the first day of a window inside another, a repeated rate — and that a row before the anchor, between two windows
or after the last one is no step. The shape: ``UnitRateSteps`` is frozen, ``days``, ``values`` and ``rate_days`` are
tuples of one length, ``at`` and ``rate_day_at`` answer each step's own value and row, and on a day outside every window
``at`` is the last step on or before it — not ``convert_bulk``'s answer there.

The cases: the direct pair (EUR→USD, EUR the stored base) and the inverse one (USD→EUR) on the same rows, through every
calendar — rows inside the window, gaps, an anchor five weeks before, no row before the first day, no row at all, rows
only after the window, three one-day windows, the same rate on consecutive rows, two disjoint windows in either order, a
first window before any row, overlapping, nested, sharing a day, adjacent, repeated —; the unusable rates and the two
bounds; both directions of one stored pair and a pair without rows in one request; days outside the windows; 501 and
1 035 pairs in one request; the ``ValueError``s; the empty request. Rows of EUR/GBP and GBP/USD, each sharing a currency
with EUR/USD, are planted around every EUR/USD calendar: none of them is its step.

RED on HEAD 10335d428, every case for one reason: ``UnitRateSteps`` and ``unit_rate_steps`` do not exist yet, so the
import of this module fails at collection (``ImportError``). ``convert_bulk``, the oracle's other half, is unchanged.
Before the hand-over the oracle, the calendars and the planting were run on ``convert_bulk`` alone, through a temporary
reference built only from its answers (since removed): all 63 cases passed. References made wrong on purpose turned red
the cases they concern, and only those: a quotient one digit short (the 27 inverse cases with a step), a value
normalised, ``Decimal('1.0837')`` for ``Decimal('1.0837000000')`` (the 26 cases whose values keep trailing zeros, where
``==`` alone would pass), a row between two windows taken as a step (the 8 cases with rows between windows), a step
merged into an equal predecessor (12), a window's first step put on its anchor's date (45), and every pair read in one
statement (both counts: 1 statement for 501 pairs, «Expression tree is too large» for 1 035).

Isolation: PURE — each test has its own in-memory SQLite database (``SQLModel.metadata.create_all``), closed and
disposed at teardown; the rates are planted with raw SQL past the model, as an older release could leave them, and read
back before use. No lane database, no server, no network.

Reference: backend/app/services/fx/conversion.py (convert_bulk, FX_PAIRS_PER_QUERY, and the cure's UnitRateSteps and
unit_rate_steps), backend/app/db/precision.py (usable_fx_rate_bounds), backend/app/utils/sql_chunks.py
(OR_TERMS_PER_QUERY), backend/test_scripts/test_services/test_bulk_reads_chunked.py (convert_bulk's X-R38 guards),
backend/test_scripts/test_services/test_fx_pairs_per_query.py (convert_bulk's chunks),
LibreFolio_developer_journal/Release_2/Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md («P3, la funzione
«a gradini» — analisi»).
"""

from __future__ import annotations

import contextlib
import dataclasses
import math
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from itertools import combinations, pairwise
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.schemas.common import Currency
from backend.app.services.fx.conversion import UnitRateSteps, convert_bulk, unit_rate_steps
from backend.test_scripts.test_utils import print_section, print_success

Pair = tuple[str, str]
Window = tuple[date, date]

D0 = date(2024, 3, 4)  # the first day of most windows; any day would do
SOURCE = "P3-STEPS"  # the source of every planted rate
#: The pair of the calendars, as ``fx_rates`` keeps it (base < quote): 1 EUR = rate USD. EUR→USD multiplies by the rate,
#: USD→EUR divides by it.
BASE, QUOTE = "EUR", "USD"
DIRECTIONS = [
    pytest.param((BASE, QUOTE), id="direct-EUR-USD"),
    pytest.param((QUOTE, BASE), id="inverse-USD-EUR"),
]
#: Rates as SQLite binds them, with long inverses: a quotient in another context, or a value rounded or normalised on the
#: way, shows in ``as_tuple()``. The column reads them back with its 10 decimal places (``Decimal('1.0837000000')``), a
#: form ``Decimal("1") * rate`` keeps.
R1, R2, R3, R4, R5 = 1.0837, 0.9123456789, 1.0612345678, 1.1, 1.3
#: Two pairs that each share a currency with EUR/USD, priced around every calendar: none of their rows is a step of it.
DECOYS = {("EUR", "GBP"): 0.8571234567, ("GBP", "USD"): 1.2643210987}
DECOY_OFFSETS = (-40, -3, 0, 1, 5, 11, 15)


def _d(offset: int) -> date:
    return D0 + timedelta(days=offset)


def _windows(offsets: Sequence[tuple[int, int]]) -> list[Window]:
    """Windows from (first, last) day offsets."""
    return [(_d(first), _d(last)) for first, last in offsets]


def _calendar(offsets: Sequence[tuple[int, int]]) -> list[tuple[date, date]]:
    """Steps as (step day, rate day) from day offsets."""
    return [(_d(day), _d(rate_day)) for day, rate_day in offsets]


def _window_days(windows: Sequence[Window]) -> list[date]:
    """Every day of every window, both ends included, ascending and once."""
    return sorted({first + timedelta(days=offset) for first, last in windows for offset in range((last - first).days + 1)})


def _dates(calendar: Sequence[tuple[Any, Any]]) -> str:
    return "[" + ", ".join(f"{day} ← {rate_day}" for day, rate_day in calendar) + "]"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


# =============================================================================
# THE PLANTING, THE READS COUNTED, THE ORACLE
# =============================================================================


async def _plant(session: AsyncSession, rates: Mapping[tuple[str, str, date], float]) -> None:
    """``{(base, quote, day): rate}`` written with raw SQL, past the model: what an older release could leave in
    ``fx_rates`` (``test_bulk_reads_chunked._xr45_plant``).

    Barrier: raw SQL reads back the very rates planted — an inf stays inf, a 0 stays 0 — and no other row.
    """
    if rates:
        await session.execute(
            text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"),
            [{"day": day.isoformat(), "base": base, "quote": quote, "rate": rate, "source": SOURCE} for (base, quote, day), rate in rates.items()],
        )
    stored = (await session.execute(text("SELECT base, quote, date, rate FROM fx_rates"))).all()
    found = {(base, quote, date.fromisoformat(day)): rate for base, quote, day, rate in stored}
    assert found == dict(rates), f"the fixture itself is wrong: raw SQL reads back {len(found)} rows for the {len(rates)} planted, differing on {sorted(set(found.items()) ^ set(rates.items()))[:5]}"


async def _plant_eur_usd(session: AsyncSession, rows: Mapping[int, float]) -> None:
    """EUR/USD's ``rows`` by day offset from D0, and the decoys of the two neighbouring pairs."""
    rates = {(BASE, QUOTE, _d(offset)): rate for offset, rate in rows.items()}
    rates.update({(base, quote, _d(offset)): rate for (base, quote), rate in DECOYS.items() for offset in DECOY_OFFSETS})
    await _plant(session, rates)


@contextlib.contextmanager
def _fx_rate_reads(session: AsyncSession) -> Iterator[list[str]]:
    """The statements naming ``fx_rates`` that the session's engine sends while inside, as they reach the driver
    (``before_cursor_execute``)."""
    sent: list[str] = []

    def record(_connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        if "fx_rates" in statement.lower():
            sent.append(statement)

    engine = session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        yield sent
    finally:
        event.remove(engine, "before_cursor_execute", record)


@dataclasses.dataclass(frozen=True)
class OracleRun:
    """What the oracle ran: the steps of every pair asked, and how many statements naming ``fx_rates`` each side sent."""

    steps: Mapping[Pair, UnitRateSteps]
    steps_reads: int
    bulk_reads: int


def _bits(value: object) -> object:
    """A value as the oracle compares it: None, or a Decimal's sign, digits and exponent (``as_tuple()``) — ``==`` alone
    takes 1.0837 for 1.0837000000. Anything else as its type and repr: a difference, never a crash."""
    if value is None:
        return None
    if type(value) is Decimal:
        return value.as_tuple()
    return (type(value).__name__, repr(value))


def _assert_well_formed(pair: Pair, pair_steps: Any) -> None:
    """The shape of one pair's steps: a frozen ``UnitRateSteps`` of that pair, three tuples of one length, the days
    strictly ascending; ``at`` and ``rate_day_at`` answer each step's own value (bit for bit) and row date, and None the
    day before the first step — on any day at all when there is no step."""
    assert isinstance(pair_steps, UnitRateSteps), f"{pair}: the steps are a {type(pair_steps).__name__}, not a UnitRateSteps"
    assert (pair_steps.source, pair_steps.destination) == pair, f"{pair}: the steps say {pair_steps.source}→{pair_steps.destination}"
    days, values, rate_days = pair_steps.days, pair_steps.values, pair_steps.rate_days
    kinds = [type(part).__name__ for part in (days, values, rate_days)]
    assert kinds == ["tuple"] * 3, f"{pair}: days, values and rate_days are {kinds}, not tuples"
    assert len(days) == len(values) == len(rate_days), f"{pair}: {len(days)} days, {len(values)} values, {len(rate_days)} rate days"
    assert all(earlier < later for earlier, later in pairwise(days)), f"{pair}: the step days are not strictly ascending: {days}"
    own = [(_bits(pair_steps.at(day)), pair_steps.rate_day_at(day)) for day in days]
    assert own == [(_bits(value), rate_day) for value, rate_day in zip(values, rate_days, strict=True)], f"{pair}: at/rate_day_at on the step days answer {own}, not the steps' own values and rows"
    probes = [days[0] - timedelta(days=1)] if days else [_d(-3650), _d(3650)]
    answers = [(pair_steps.at(day), pair_steps.rate_day_at(day)) for day in probes]
    assert answers == [(None, None)] * len(probes), f"{pair}: at/rate_day_at answer {answers} on {probes}, before the first step or with no step: expected None"
    with pytest.raises(dataclasses.FrozenInstanceError):
        pair_steps.days = ()


def _assert_same_answers(pair: Pair, pair_steps: Any, days: Sequence[date], results: Sequence[Any]) -> None:
    """``at``/``rate_day_at`` against ``convert_bulk``'s amount, bit for bit, and its rate date, on each of ``days``;
    (None, None) where ``convert_bulk`` has no rate. The first day that differs is reported, with how many do."""
    differing = []
    for day, result in zip(days, results, strict=True):
        expected = (None, None) if result is None else (result[0].amount, result[1])
        found = (pair_steps.at(day), pair_steps.rate_day_at(day))
        if (_bits(found[0]), found[1]) != (_bits(expected[0]), expected[1]):
            differing.append((day, found, expected))
    if differing:
        day, found, expected = differing[0]
        pytest.fail(f"{pair}: at/rate_day_at differ from convert_bulk on {len(differing)} of {len(days)} window days; the first is {day}: the steps answer {found!r}, convert_bulk {expected!r} (n6: bit for bit, as_tuple())")


async def _steps_matching_convert_bulk(session: AsyncSession, requests: Mapping[Pair, Sequence[Window]]) -> OracleRun:
    """THE ORACLE (n6). ``unit_rate_steps`` once for ``requests``; then ONE ``convert_bulk`` of ``Currency(code=source,
    amount=Decimal("1"))`` into ``destination`` on every day of every window of every pair, which answers each day as a
    call of its own would (it reads each pair from the anchor of its earliest day, and takes the last row on or before
    each day).

    Every pair asked has an entry of the right shape (``_assert_well_formed``), and on every one of those days ``at`` is
    the converted amount bit for bit and ``rate_day_at`` its rate date, both None where ``convert_bulk`` has no rate.
    """
    with _fx_rate_reads(session) as steps_reads:
        steps = await unit_rate_steps(session, requests)
    assert sorted(steps) == sorted(requests), f"unit_rate_steps answered the pairs {sorted(steps)}, asked {sorted(requests)}: every pair asked has an entry"

    days_by_pair = {pair: _window_days(windows) for pair, windows in requests.items()}
    conversions = [(Currency(code=source, amount=Decimal("1")), destination, day) for (source, destination), days in days_by_pair.items() for day in days]
    with _fx_rate_reads(session) as bulk_reads:
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
    assert len(results) == len(conversions), f"the oracle itself is wrong: {len(results)} answers for {len(conversions)} conversions"

    answers = iter(results)
    for pair, days in days_by_pair.items():
        _assert_well_formed(pair, steps[pair])
        _assert_same_answers(pair, steps[pair], days, [next(answers) for _ in days])
    return OracleRun(steps=steps, steps_reads=len(steps_reads), bulk_reads=len(bulk_reads))


def _assert_calendar(steps: Mapping[Pair, Any], pair: Pair, expected: Sequence[tuple[date, date]]) -> None:
    """The steps of ``pair``, as (day, rate day), are ``expected``: the first day of each window that has an anchor, with
    the anchor's date, and every usable row day inside a window, with its own — ascending, once each."""
    found = list(zip(steps[pair].days, steps[pair].rate_days, strict=True))
    assert found == list(expected), f"{pair}: the steps (day ← rate day) are {_dates(found)}, expected {_dates(expected)}"


# =============================================================================
# 1. EVERY CALENDAR, DIRECT AND INVERSE: THE ANSWERS OF convert_bulk, AND THE STEPS
# =============================================================================

#: (EUR/USD's rates by day offset from D0, the windows as (first, last) offsets, the steps expected as (step day, rate
#: day) offsets). No value is written here: the oracle takes them from ``convert_bulk``.
CALENDARS = [
    pytest.param({0: R1, 3: R2, 4: R3, 9: R4}, [(0, 9)], [(0, 0), (3, 3), (4, 4), (9, 9)], id="rows-inside-the-window"),
    pytest.param({-1: R1, 2: R2, 9: R3, 10: R4, 20: R5, 25: R1}, [(0, 21)], [(0, -1), (2, 2), (9, 9), (10, 10), (20, 20)], id="gaps-between-rows"),
    pytest.param({-60: R5, -35: R1, 4: R2}, [(0, 7)], [(0, -35), (4, 4)], id="anchor-five-weeks-before-the-window"),
    pytest.param({3: R1, 5: R2}, [(0, 7)], [(3, 3), (5, 5)], id="no-usable-row-before-the-first-day"),
    pytest.param({}, [(0, 7)], [], id="no-rows-at-all"),
    pytest.param({8: R1, 12: R2}, [(0, 7)], [], id="rows-only-after-the-window"),
    pytest.param({-3: R1, 1: R2}, [(0, 0)], [(0, -3)], id="one-day-window-backward-filled"),
    pytest.param({-3: R1, 0: R2, 1: R3}, [(0, 0)], [(0, 0)], id="one-day-window-on-its-own-row"),
    pytest.param({1: R1}, [(0, 0)], [], id="one-day-window-before-any-row"),
    pytest.param({-2: R1, 1: R1, 2: R1, 3: R2}, [(0, 4)], [(0, -2), (1, 1), (2, 2), (3, 3)], id="same-rate-on-consecutive-rows"),
    pytest.param({-2: R1, 2: R2, 6: R3, 8: R4, 12: R5}, [(0, 4), (10, 14)], [(0, -2), (2, 2), (10, 8), (12, 12)], id="two-disjoint-windows"),
    pytest.param({-2: R1, 2: R2, 6: R3, 8: R4, 12: R5}, [(10, 14), (0, 4)], [(0, -2), (2, 2), (10, 8), (12, 12)], id="two-disjoint-windows-latest-first"),
    pytest.param({4: R1, 7: R2}, [(0, 2), (6, 9)], [(6, 4), (7, 7)], id="first-window-before-any-row"),
    pytest.param({-1: R1, 3: R2, 7: R3, 10: R4}, [(0, 8), (5, 12)], [(0, -1), (3, 3), (5, 3), (7, 7), (10, 10)], id="two-overlapping-windows"),
    pytest.param({-1: R1, 2: R2, 4: R3, 9: R4}, [(0, 10), (3, 5)], [(0, -1), (2, 2), (3, 2), (4, 4), (9, 9)], id="a-window-inside-another"),
    pytest.param({-1: R1, 2: R2, 6: R3}, [(0, 4), (4, 8)], [(0, -1), (2, 2), (4, 2), (6, 6)], id="two-windows-sharing-a-day"),
    pytest.param({-1: R1, 2: R2, 5: R3, 7: R4}, [(0, 4), (5, 9)], [(0, -1), (2, 2), (5, 5), (7, 7)], id="two-adjacent-windows"),
    pytest.param({-1: R1, 2: R2}, [(0, 4), (0, 4)], [(0, -1), (2, 2)], id="the-same-window-twice"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize(("rows", "windows", "steps"), CALENDARS)
async def test_steps_answer_as_convert_bulk_on_every_day_of_the_windows(session, rows, windows, steps, direction):
    """(n1, n3, n4, n6) EUR/USD's ``rows``, asked EUR→USD (``Decimal("1") * rate``) or USD→EUR (``Decimal("1") /
    rate``) on ``windows``: on every day of every window ``at`` is ``convert_bulk``'s amount bit for bit and
    ``rate_day_at`` its rate date, None where it has no rate; and the steps are ``steps``.

    The calendars: rows inside the window, the first on its first day; gaps of days between rows, and a row after the
    window that is no step; an anchor five weeks before the window, an older row that is no step; no usable row before
    the first day, the leading days None; no row at all, and rows only after the window: no step; a one-day window
    backward-filled, on its own row, before any row; the same rate on four consecutive steps, three of them rows: every
    one a step; two disjoint windows, given in either order, the rows between them no steps and the later anchoring the
    second window; a first window before any row, the second anchored on a row between them; two overlapping windows, a
    window inside another and two windows sharing a day: the inner window's first day a step of its own, with the
    anchor of that day; two adjacent windows, the second starting on a row: one step; the same window twice: each step
    once.
    """
    source, destination = direction
    story = f"{source}→{destination}, EUR/USD rows on day offsets {sorted(rows)}, windows {windows}"
    print_section(f"P3 steps: {story}")
    await _plant_eur_usd(session, rows)

    run = await _steps_matching_convert_bulk(session, {direction: _windows(windows)})

    _assert_calendar(run.steps, direction, _calendar(steps))
    print_success(f"{story}: steps {steps}, every window day as convert_bulk")


# =============================================================================
# 2. THE ROWS OF convert_bulk: X-R38's USABLE FILTER, IN THE ANCHOR AND IN THE WINDOW
# =============================================================================

#: Rates outside X-R38's ``usable_fx_rate_bounds()`` (1E-10 <= rate < 1E+14), as SQLite binds them: what an older
#: release, or another tool, could leave in ``fx_rates``.
UNUSABLE = [
    pytest.param(0.0, id="0"),  # a manual 1E-11, truncated to the column's 10 decimals
    pytest.param(1e-11, id="1E-11"),  # a REAL another tool wrote
    pytest.param(-1.5, id="negative-1.5"),
    pytest.param(float("inf"), id="inf"),  # 1E+400, written as an SQLite REAL
    pytest.param(1e14, id="first-refused-1E+14"),
    pytest.param(1e19, id="1E+19"),  # X-R38's rate of 20 digits before the decimal point
]
#: The two bounds a read still uses.
USABLE_BOUNDS = [
    pytest.param(1e-10, id="smallest-1E-10"),
    pytest.param(99999999999999.0, id="largest-99999999999999"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize("unusable", UNUSABLE)
async def test_unusable_rates_are_skipped_like_a_missing_date(session, unusable, direction):
    """(n2) X-R38's usable filter, in the anchor and in the window: a rate outside ``usable_fx_rate_bounds()`` is a day
    without a row, as in ``convert_bulk``.

    EUR/USD 1.0837 on D-5, ``unusable`` on D-2 (the would-be anchor), on D0 (the first day), on D4 (inside) and on D7
    (the last day), 0.9123456789 on D2 and 1.0612345678 on D6; window [D0, D7]. The steps: D0 anchored on D-5, D2, D6 —
    no step with the unusable rate, D-2 never the anchor — and every day as ``convert_bulk``.
    """
    source, destination = direction
    story = f"{source}→{destination}, a legacy {unusable!r} on D-2, D0, D4 and D7 of EUR/USD"
    print_section(f"P3 steps: {story}")
    await _plant_eur_usd(session, {-5: R1, -2: unusable, 0: unusable, 2: R2, 4: unusable, 6: R3, 7: unusable})

    run = await _steps_matching_convert_bulk(session, {direction: _windows([(0, 7)])})

    _assert_calendar(run.steps, direction, _calendar([(0, -5), (2, 2), (6, 6)]))
    print_success(f"{story}: skipped like a missing date, in the anchor and in the window")


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize("bound", USABLE_BOUNDS)
async def test_rates_at_the_usable_bounds_are_steps(session, bound, direction):
    """(n2) The bounds of X-R38's filter are usable rates: EUR/USD 1.0837 on D-5, ``bound`` on D-2 (the anchor) and on
    D4, 0.9123456789 on D6; window [D0, D7]. The steps: D0 anchored on D-2, D4 and D6, every day as ``convert_bulk``
    (1E-10 inverted is 1E+10; 99999999999999 inverted, 1.000000000000010000000000000E-14)."""
    source, destination = direction
    story = f"{source}→{destination}, {bound!r} on D-2 and D4 of EUR/USD"
    print_section(f"P3 steps: {story}")
    await _plant_eur_usd(session, {-5: R1, -2: bound, 4: bound, 6: R2})

    run = await _steps_matching_convert_bulk(session, {direction: _windows([(0, 7)])})

    _assert_calendar(run.steps, direction, _calendar([(0, -2), (4, 4), (6, 6)]))
    print_success(f"{story}: read, the anchor and a step")


# =============================================================================
# 3. ONE REQUEST: BOTH DIRECTIONS OF ONE STORED PAIR, A PAIR WITHOUT ROWS; DAYS OUTSIDE THE WINDOWS
# =============================================================================


@pytest.mark.asyncio
async def test_both_directions_of_one_stored_pair_in_one_request(session):
    """Both directions of EUR/USD and a pair with no row (JPY→CHF, stored CHF/JPY) in ONE request: three entries, each
    with the calendar of its own windows — EUR→USD on [D0, D5], USD→EUR on [D2, D9] —, the products of the same rows in
    one direction and their quotients in the other, every day as ``convert_bulk`` in its direction; JPY→CHF an entry
    without steps, None on every day.
    """
    print_section("P3 steps: EUR→USD, USD→EUR and JPY→CHF in one request")
    await _plant_eur_usd(session, {-4: R1, 1: R2, 3: R3, 8: R4})
    requests = {(BASE, QUOTE): _windows([(0, 5)]), (QUOTE, BASE): _windows([(2, 9)]), ("JPY", "CHF"): _windows([(0, 9)])}

    run = await _steps_matching_convert_bulk(session, requests)

    _assert_calendar(run.steps, (BASE, QUOTE), _calendar([(0, -4), (1, 1), (3, 3)]))
    _assert_calendar(run.steps, (QUOTE, BASE), _calendar([(2, 1), (3, 3), (8, 8)]))
    _assert_calendar(run.steps, ("JPY", "CHF"), [])
    print_success("three entries, each direction with its own calendar, JPY→CHF without steps")


#: ``two-disjoint-windows`` again, and days outside its windows with the step whose value and row ``at`` and
#: ``rate_day_at`` answer there: (day offset, that step's day offset, None before the first step).
OUTSIDE_ROWS = {-2: R1, 2: R2, 6: R3, 8: R4, 12: R5}
OUTSIDE_WINDOWS = [(0, 4), (10, 14)]
OUTSIDE_STEPS = [(0, -2), (2, 2), (10, 8), (12, 12)]
OUTSIDE_DAYS = [(-3, None), (-1, None), (5, 2), (6, 2), (7, 2), (9, 2), (15, 12), (40, 12)]


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
async def test_at_outside_the_windows_is_the_last_step_on_or_before_the_day(session, direction):
    """``at`` and ``rate_day_at`` are the last step on or before the day, None before the first, on any day: outside the
    windows too, where they are not ``convert_bulk``'s answer — the steps are cut to the windows.

    EUR/USD rows on D-2, D2, D6, D8 and D12, windows [D0, D4] and [D10, D14]. On D-3 and D-1, before the first step
    (D0), None — though D-2 holds a row. From D5 to D9 the step of D2 — though D6 and D8 hold rows, between the windows.
    On D15 and D40, after the last window, the step of D12.
    """
    source, destination = direction
    print_section(f"P3 steps: {source}→{destination} outside two windows")
    await _plant_eur_usd(session, OUTSIDE_ROWS)

    run = await _steps_matching_convert_bulk(session, {direction: _windows(OUTSIDE_WINDOWS)})

    _assert_calendar(run.steps, direction, _calendar(OUTSIDE_STEPS))
    pair_steps = run.steps[direction]
    found = {offset: (_bits(pair_steps.at(_d(offset))), pair_steps.rate_day_at(_d(offset))) for offset, _step in OUTSIDE_DAYS}
    expected = {offset: (None, None) if step is None else (_bits(pair_steps.at(_d(step))), pair_steps.rate_day_at(_d(step))) for offset, step in OUTSIDE_DAYS}
    assert found == expected, f"{direction} outside the windows answers {found}, expected {expected}: the last step on or before each day"
    print_success(f"{source}→{destination}: None before D0, D2's step from D5 to D9, D12's after D14")


# =============================================================================
# 4. MORE PAIRS THAN ONE QUERY HOLDS: THE CHUNKS OF convert_bulk
# =============================================================================

#: 46 ISO 4217 codes ``Currency.validate_code`` accepts (``test_fx_pairs_per_query.py``'s).
CODES = (
    "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HUF",
    "IDR", "ILS", "INR", "ISK", "JPY", "KES", "KRW", "MAD", "MXN", "MYR", "NGN", "NOK", "NZD", "PEN", "PHP", "PKR",
    "PLN", "QAR", "RON", "RSD", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
)  # fmt: skip
#: Every pair as ``fx_rates`` stores it (base < quote, so from the codes in alphabetical order): 1 035.
ALL_PAIRS = list(combinations(sorted(CODES), 2))
CHUNK = 500  # FX_PAIRS_PER_QUERY: the contract's number, written here and not read from the module under test
PAIR_COUNTS = [
    pytest.param(501, id="501-pairs-one-past-a-chunk"),
    pytest.param(len(ALL_PAIRS), id="1035-pairs-every-pair-of-46-codes"),
]


def _many_pairs(count: int) -> tuple[dict[tuple[str, str, date], float], dict[Pair, list[Window]], dict[Pair, list[tuple[date, date]]]]:
    """The first ``count`` stored pairs, each asked in one direction — as stored at an even index, inverted at an odd
    one — on [D0, D3]: (the rates to plant, the request, the steps expected per pair).

    By ``(index + 1) % 3``: an anchor on D-9 and a row on D2 (steps D0 ← D-9 and D2), a row on D0 (step D0), or no row
    (no step). The last pair of either count has an anchor and a row: the last chunk is never only pairs without rows.
    Every pair has rates of its own, with long inverses.
    """
    rates: dict[tuple[str, str, date], float] = {}
    requests: dict[Pair, list[Window]] = {}
    expected: dict[Pair, list[tuple[date, date]]] = {}
    for index, (base, quote) in enumerate(ALL_PAIRS[:count]):
        pair = (base, quote) if index % 2 == 0 else (quote, base)
        requests[pair] = _windows([(0, 3)])
        rate = 1 + (index + 1) / 997
        kind = (index + 1) % 3
        if kind == 0:
            rates[(base, quote, _d(-9))] = rate
            rates[(base, quote, _d(2))] = rate + 0.0123456789
            expected[pair] = _calendar([(0, -9), (2, 2)])
        elif kind == 1:
            rates[(base, quote, D0)] = rate
            expected[pair] = _calendar([(0, 0)])
        else:
            expected[pair] = []
    return rates, requests, expected


@pytest.mark.asyncio
@pytest.mark.parametrize("count", PAIR_COUNTS)
async def test_more_pairs_than_one_query_holds_are_read_in_the_chunks_of_convert_bulk(session, count):
    """(n2) ``count`` distinct stored pairs in one request, half of them inverted, a third without rows: every pair as
    ``convert_bulk`` on every window day, with its own steps, read in the statements ``convert_bulk`` sends for the same
    pairs — one per 500 pairs, ⌈count / 500⌉, counted on the engine. At 501 one OR of every pair would still parse, and
    only the count tells; at 1 035 SQLite refuses it («Expression tree is too large»).

    Barrier: ``convert_bulk`` itself sends ⌈count / 500⌉ statements (``FX_PAIRS_PER_QUERY``, 500).
    """
    story = f"{count} pairs in one request"
    print_section(f"P3 steps: {story}")
    rates, requests, expected = _many_pairs(count)
    await _plant(session, rates)

    try:
        run = await _steps_matching_convert_bulk(session, requests)
    except OperationalError as error:
        pytest.fail(f"{story}: SQLite refused a statement, {error.orig!r} — one OR of every pair, not the chunks of convert_bulk (n2)")

    reads = math.ceil(count / CHUNK)
    assert run.bulk_reads == reads, f"the barrier itself is wrong: convert_bulk read {count} pairs in {run.bulk_reads} statements, not {reads} — is FX_PAIRS_PER_QUERY still {CHUNK}?"
    assert run.steps_reads == reads, f"{story}: unit_rate_steps sent {run.steps_reads} statements naming fx_rates, expected {reads}, the chunks of convert_bulk ({CHUNK} pairs per query, n2)"
    found = {pair: list(zip(run.steps[pair].days, run.steps[pair].rate_days, strict=True)) for pair in requests}
    wrong = [pair for pair in requests if found[pair] != expected[pair]]
    assert not wrong, f"{story}: {len(wrong)} pairs have other steps; the first, {wrong[0]}: {_dates(found[wrong[0]])}, expected {_dates(expected[wrong[0]])}"
    print_success(f"{story}: every pair as convert_bulk, in {reads} statements")


# =============================================================================
# 5. THE REFUSALS (n5), AND THE EMPTY REQUEST
# =============================================================================

#: Requests as {pair: [(first, last) day offsets]}.
ONE_CURRENCY = [
    pytest.param({("EUR", "EUR"): [(0, 7)]}, id="alone"),
    pytest.param({(BASE, QUOTE): [(0, 7)], ("USD", "USD"): [(0, 7)]}, id="beside-a-valid-pair"),
]
BACKWARD_WINDOWS = [
    pytest.param({(BASE, QUOTE): [(1, 0)]}, id="alone"),
    pytest.param({(BASE, QUOTE): [(0, 7), (9, 8)]}, id="beside-a-valid-window"),
    pytest.param({(BASE, QUOTE): [(0, 7)], (QUOTE, BASE): [(5, -5)]}, id="in-another-pair"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", ONE_CURRENCY)
async def test_a_pair_of_one_currency_is_refused(session, spec):
    """(n5) A pair whose source is its destination raises ``ValueError``, alone or beside a valid pair, though EUR/USD has
    rows: ``convert_bulk`` answers it with the day itself as its rate date, which no step can say."""
    print_section(f"P3 steps: a pair of one currency, {sorted(spec)}")
    await _plant_eur_usd(session, {-1: R1, 2: R2})
    requests = {pair: _windows(windows) for pair, windows in spec.items()}

    with pytest.raises(ValueError):
        await unit_rate_steps(session, requests)
    print_success(f"{sorted(spec)}: ValueError")


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", BACKWARD_WINDOWS)
async def test_a_window_ending_before_it_starts_is_refused(session, spec):
    """(n5) A window whose last day comes before its first raises ``ValueError``: alone, beside a valid window of its
    pair, or in another pair of the request than a valid one — though EUR/USD has rows."""
    print_section(f"P3 steps: a window ending before it starts, {spec}")
    await _plant_eur_usd(session, {-1: R1, 2: R2})
    requests = {pair: _windows(windows) for pair, windows in spec.items()}

    with pytest.raises(ValueError):
        await unit_rate_steps(session, requests)
    print_success(f"{spec}: ValueError")


@pytest.mark.asyncio
async def test_an_empty_request_answers_no_pair(session):
    """No pair asked, no entry: ``{}``, though EUR/USD has rows."""
    print_section("P3 steps: an empty request")
    await _plant_eur_usd(session, {-1: R1, 2: R2})

    run = await _steps_matching_convert_bulk(session, {})

    assert dict(run.steps) == {}, f"an empty request answers {run.steps}"
    print_success("an empty request: no entry")

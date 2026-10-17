"""X-R55 (night decision N75): a date range has a ceiling — asset prices, FX conversions and the sync walk.

The defect: a request whose ``end`` is 9999-12-31 made the backend build one item per calendar day up to that date.
``get_prices_bulk`` backward-filled about 2.9 million price points after the last stored price,
``POST /fx/currencies/convert`` expanded about 3.6 million daily conversions (and, with a signal, walked its warm-up
from as far back as 0001-01-01), and the refresh walked every day from the requested start to find the gaps of its
history cache. A denial of service any logged-in user could send — and a useless one to wait for: a walk ending on
9999-12-31 finally steps past the last day a date can hold, so after the whole cost the answer is a 500 «date value out
of range». The contract pinned here (N75, its revision, and the alignment on R13-SEC7-1):

1. One helper for the ceiling: ``datetime_utils.latest_range_end()`` (R13-SEC7-1, workstream J), tomorrow by the
   server's calendar, imported by name where X-R55 reads it: ``price_query`` and ``currencies`` (``CEILING_CONSUMERS``).
   ``backend/app/utils/date_range_limits.py`` has no ceiling of its own: it keeps ``RANGE_SPAN_LIMIT_DAYS = 36_525``
   (100 years) and ``range_span_floor(end)``, ``end - RANGE_SPAN_LIMIT_DAYS days``, never before ``date.min``. These
   tests freeze the ceiling the way ``_range_bounds.lift_range_bound`` lifts it, by replacing the name in each consumer
   (``frozen_ceiling``: ``CEILING``, the day after ``FROZEN_TODAY``); and that lift reaches both consumers.
2. ``get_prices_bulk``: each item's end becomes ``min(end or start, latest_range_end())`` before anything else; the
   series, the comparison series, the signal context, the load ranges and the events all see the clamped range. An item
   starting after it gives an empty result at its own position (its asset id, no price, no event, no error); the other
   items of the call give what they give when asked alone.
3. ``_build_backward_filled_series``: without a seed the walk starts at the first date of ``price_map``; an empty map
   without a seed returns ``[]`` at once. The points emitted do not change.
4. ``convert_currency_bulk``, per conversion: the end clamped as in 2; ``start = max(start, range_span_floor(clamped
   end))``; the signal warm-up never starts before ``range_span_floor(clamped end)``. A conversion entirely after the
   ceiling gives no result and no error, and its signals, if any, run on an empty series as for a pair without rates;
   the other conversions of the call are unaffected. Each signal result's ``date_range`` is the range its signals
   cover: the requested one cut at the ceiling, its start raised to the floor; a conversion entirely after the ceiling
   echoes the requested range (X's review).
5. The refresh with a history cache: the walk for the missing days covers ``max(start, floor) … history_end`` only,
   ``floor = range_span_floor(history_end)``; a start before the floor adds itself and the day before the floor to the
   missing days, so the provider is never asked less than before (more, in that extreme case only).

The moderate cases show the defect at a size that runs in milliseconds. The extreme cases (0001-01-01 … 9999-12-31) are
guards bounded twice: by the wall clock (``GUARD_SECONDS``) and by a fuse that raises inside a per-day loop once it has
stepped ``FUSE_DAY_STEPS`` days (or tested that many against a cache), so on unbounded code a guard fails in well under
a second instead of allocating gigabytes before any timeout could fire.

Isolation: PURE — no lane database, no server, no network. The price queries run on a private SQLite file under
``tmp_path`` built by ``create_all``; the conversion handler is called directly, ``convert_bulk`` replaced by an
in-process converter that records every day it is handed; the refresh step runs with an in-process provider double and
stand-ins for the two core caches it reads.

Red before the change (HEAD 3d13fbcdc), each for the reason its docstring gives ("Red before X-R55"): RC-000,
RC-B02…B04, RC-A01…A06, RC-F01…F05, RC-S01, RC-S04. Green then too — behaviour the change had to keep: RC-B01, RC-S02,
RC-S03. Written green, with no red phase: RC-001 (the lift reaches X-R55's consumers) and RC-F06 (the signal ranges
echoed, a review fix).
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1.fx import currencies
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, PriceHistory, ProviderInputType
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest, FXConvertResponse
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint, FAPriceQueryItem, FAPriceQueryResult
from backend.app.schemas.signals import SignalRequest
from backend.app.services.assets import core, price_query, refresh
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.signals.service import SignalService
from backend.app.utils import date_range_limits, datetime_utils
from backend.test_scripts.test_services._range_bounds import RANGE_BOUND_CONSUMERS, lift_range_bound

#: Where X-R55 reads its ceiling: the modules that import ``latest_range_end`` by name. The name is replaced there, as
#: ``lift_range_bound`` does it: replacing it in ``datetime_utils`` would change nothing.
CEILING_CONSUMERS = ("backend.app.services.assets.price_query", "backend.app.api.v1.fx.currencies")

FROZEN_TODAY = date(2025, 6, 18)  # any day: the ceiling is frozen at the day after it, refresh's date_type at it
CEILING = FROZEN_TODAY + timedelta(days=1)  # latest_range_end(), frozen: tomorrow of FROZEN_TODAY
RANGE_SPAN_LIMIT_DAYS = 36_525  # the contract's 100 years, written here and not read from the module under test
WALK_BOUND = RANGE_SPAN_LIMIT_DAYS + 3  # days a capped sync walk may test: floor … history_end, the start, floor - 1
FUSE_DAY_STEPS = 200_000  # > 2.5 × the longest capped loop below; 1/18 of the unbounded 0001-01-01 … 9999-12-31 one
GUARD_SECONDS = 20.0  # a capped extreme call takes well under a second; an unbounded one, minutes
YEAR_ONE = date(1, 1, 1)
LAST_DAY = date(9999, 12, 31)
SMA3 = SignalRequest(instance_id="sma3", signal_code="SMA", params={"period": 3})


def _day(offset: int) -> date:
    """``FROZEN_TODAY`` plus ``offset`` days."""
    return FROZEN_TODAY + timedelta(days=offset)


def _days(first: date, last: date) -> list[date]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def _floor(end: date) -> date:
    """``range_span_floor(end)`` as the contract defines it: ``RANGE_SPAN_LIMIT_DAYS`` before ``end``, never before ``date.min``."""
    return end - timedelta(days=RANGE_SPAN_LIMIT_DAYS) if (end - date.min).days > RANGE_SPAN_LIMIT_DAYS else date.min


def _span(days: list[date]) -> str:
    return f"{len(days):,} days, {days[0]} … {days[-1]}" if days else "no day"


# =============================================================================
# FUSES AND THE WALL CLOCK
# =============================================================================


class _FuseTripped(Exception):
    """A per-day loop went past its fuse: no capped range is that long."""


class _DayStepFuse:
    """Stands in for ``timedelta`` in one product module: counts the calls, and raises past ``limit``.

    Every per-day loop of the code under test steps with ``timedelta(days=1)``, so the count is the number of days
    walked; the values returned are real ``timedelta`` objects, so the arithmetic is unchanged.
    """

    def __init__(self, limit: int = FUSE_DAY_STEPS) -> None:
        self.limit = limit
        self.calls = 0

    def __call__(self, *args: Any, **kwargs: Any) -> timedelta:
        self.calls += 1
        if self.calls > self.limit:
            raise _FuseTripped(f"more than {self.limit:,} timedelta() steps in one call: a per-day loop longer than any capped range")
        return timedelta(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(timedelta, name)


def _install_fuse(monkeypatch: pytest.MonkeyPatch, module: Any) -> _DayStepFuse:
    fuse = _DayStepFuse()
    monkeypatch.setattr(module, "timedelta", fuse)
    return fuse


def _assert_within_guard(started: float) -> None:
    elapsed = time.perf_counter() - started
    assert elapsed < GUARD_SECONDS, f"{elapsed:.1f} s, past the {GUARD_SECONDS:.0f} s bound: the range is not capped"


async def _within_guard[ResultT](make_call: Callable[[], Awaitable[ResultT]]) -> ResultT:
    """Run one extreme call: a tripped fuse fails the test here, saying so; then the wall clock is checked."""
    started = time.perf_counter()
    try:
        result = await make_call()
    except _FuseTripped as fuse:
        pytest.fail(f"stopped by the fuse after {time.perf_counter() - started:.2f} s: {fuse}")
    _assert_within_guard(started)
    return result


def _freeze_ceiling(monkeypatch: pytest.MonkeyPatch, ceiling: date) -> None:
    """``latest_range_end()`` answers ``ceiling`` in every consumer: ``setattr`` raises for one that stops reading the name."""
    for module in CEILING_CONSUMERS:
        monkeypatch.setattr(f"{module}.latest_range_end", lambda: ceiling)


@pytest.fixture
def frozen_ceiling(monkeypatch: pytest.MonkeyPatch) -> date:
    """The ceiling of the price and FX cases: ``CEILING``, whatever the day the suite runs."""
    _freeze_ceiling(monkeypatch, CEILING)
    return CEILING


# =============================================================================
# RC-000 / RC-001 — ONE CEILING HELPER, ONE SPAN MODULE, ONE LIFT
# =============================================================================


def test_rc000_one_ceiling_helper_and_the_span():
    """RC-000: the price query and the conversions read R13-SEC7-1's ``datetime_utils.latest_range_end`` itself, imported
    by name, and ``date_range_limits`` has no ceiling of its own; it keeps the 100-year span and its floor, which never
    goes before ``date.min``.

    Two helpers for one day could drift apart (one in UTC, one by the server's calendar), and a name imported by value
    is the one a test or ``lift_range_bound`` replaces: a consumer reading the ceiling some other way escapes both.
    Red before X-R55: ``date_range_limits`` did not exist, and neither consumer read a ceiling.
    """
    for name in CEILING_CONSUMERS:
        assert importlib.import_module(name).latest_range_end is datetime_utils.latest_range_end, f"{name} must read datetime_utils.latest_range_end"
    assert not hasattr(date_range_limits, "latest_range_end"), "date_range_limits must not define a second ceiling"
    assert date_range_limits.RANGE_SPAN_LIMIT_DAYS == RANGE_SPAN_LIMIT_DAYS
    assert date_range_limits.range_span_floor(date(2025, 6, 19)) == date(1925, 6, 19)
    assert date_range_limits.range_span_floor(date(50, 1, 1)) == date.min
    edges = (date.min, date.min + timedelta(days=RANGE_SPAN_LIMIT_DAYS), date.min + timedelta(days=RANGE_SPAN_LIMIT_DAYS + 1))
    for end in (*edges, date(2000, 2, 29), FROZEN_TODAY, LAST_DAY):
        assert date_range_limits.range_span_floor(end) == _floor(end), end
    assert _floor(edges[-1]) == date.min + timedelta(days=1)


@pytest.mark.asyncio
async def test_rc001_lift_range_bound_lifts_the_ceiling(private_db, monkeypatch, frozen_ceiling):
    """RC-001: ``_range_bounds.lift_range_bound`` lifts X-R55's ceiling too, in both modules that read it.

    The suites whose scenarios live in 2032–2091 lift R13-SEC7-1's bound with it; the price query and the conversions
    read the same helper, so without the lift those suites would see their prices and rates cut at tomorrow. The ceiling
    is frozen at ``CEILING``, then lifted: a price query and a conversion up to ``CEILING`` + 9 days run to that day.
    No red phase: written with the alignment on R13-SEC7-1, it pins the two consumers added to
    ``RANGE_BOUND_CONSUMERS``.
    """
    missing = [name for name in CEILING_CONSUMERS if name not in RANGE_BOUND_CONSUMERS]
    assert not missing, f"lift_range_bound does not reach {missing}: far-future suites would be cut at tomorrow"
    lift_range_bound(monkeypatch)
    for name in CEILING_CONSUMERS:
        assert importlib.import_module(name).latest_range_end() == date.max, name
    end = CEILING + timedelta(days=9)
    asset_id = await _asset(private_db, prices=_days(_day(-5), _day(-1)))
    (result,) = await _query(private_db, _item(asset_id, _day(-3), end))
    assert _price_days(result) == _days(_day(-3), end), f"got {_span(_price_days(result))}"
    response = await _convert(monkeypatch, _Converter(), _conversion("100", _day(-5), end))
    assert _result_days(response) == _days(_day(-5), end), f"got {_span(_result_days(response))}"


# =============================================================================
# RC-B — _build_backward_filled_series
# =============================================================================


def _row(day: date, close: int) -> PriceHistory:
    value = Decimal(close)
    return PriceHistory(asset_id=1, date=day, open=value - 1, high=value + 2, low=value - 2, close=value, volume=Decimal(1000 + close), currency="EUR", source_plugin_key="rc_fixture")


def _rows(days: Iterable[date]) -> list[PriceHistory]:
    return [_row(day, 100 + n) for n, day in enumerate(days)]


class _CountingPriceMap(dict):
    """``price_map`` for the builder, counting the days it looks up — the length of its walk.

    ``fuse`` stops a walk that looks up more days than that, raising inside it.
    """

    def __init__(self, rows: Iterable[PriceHistory] = (), *, fuse: int | None = None) -> None:
        super().__init__((row.date, row) for row in rows)
        self.lookups = 0
        self.fuse = fuse

    def _looked_up(self) -> None:
        self.lookups += 1
        if self.fuse is not None and self.lookups > self.fuse:
            raise _FuseTripped(f"more than {self.fuse:,} days looked up in the price map")

    def get(self, key: Any, default: Any = None) -> Any:
        self._looked_up()
        return super().get(key, default)

    def __getitem__(self, key: Any) -> Any:
        self._looked_up()
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        self._looked_up()
        return super().__contains__(key)


def _build(price_map: dict, start: date, end: date, seed: PriceHistory | None = None):
    return PriceQueryOperations._build_backward_filled_series(price_map, start, end, seed_price=seed)


def _observed(row: PriceHistory) -> tuple:
    return (row.open, row.high, row.low, row.close, row.volume, row.currency, row.source_plugin_key)


def _projection(points) -> list[tuple]:
    """The builder's points as tuples: the day, the carried row's values, then the backward fill (rate day, days back)."""
    out = []
    for point in points:
        fill = point.backward_fill_info
        carried = (point.open, point.high, point.low, point.close, point.volume, point.currency, point.source_plugin_key)
        out.append((point.date, *carried, *((fill.actual_rate_date, fill.days_back) if fill else (None, None))))
    return out


def _reference(rows: Iterable[PriceHistory], start: date, end: date, seed: PriceHistory | None) -> list[tuple]:
    """What the builder emits, from its contract alone, written apart from its code.

    Nothing before the first price inside ``[start, end]`` — or from ``start`` itself when a seed is given — then one
    point a day up to ``end``: the day's own row, or the last known one, with its day and how many days back it is.
    A row before ``start`` without a seed is never emitted nor carried.
    """
    by_day = {row.date: row for row in rows}
    in_range = sorted(day for day in by_day if start <= day <= end)
    first = start if seed is not None else (in_range[0] if in_range else None)
    if first is None:
        return []
    out, last = [], seed
    for day in _days(first, end):
        row = by_day.get(day)
        if row is not None:
            last = row
            out.append((day, *_observed(row), None, None))
        else:
            out.append((day, *_observed(last), last.date, (day - last.date).days))
    return out


_B01_SHAPES = [
    pytest.param([d for d in _days(_day(-5), _day(-1)) if d != _day(-3)], date(1990, 1, 1), CEILING, None, id="no-seed-start-decades-before-the-first-price"),
    pytest.param([_day(-20), *_days(_day(-5), _day(-1))], _day(-10), CEILING, None, id="no-seed-a-row-before-start-is-never-emitted"),
    pytest.param(_days(_day(-5), _day(-1)), _day(-8), CEILING, _row(_day(-30), 90), id="seed-fills-from-start"),
    pytest.param([_day(5)], _day(-10), CEILING, None, id="no-seed-the-only-row-after-end"),
]


@pytest.mark.parametrize(("days", "start", "end", "seed"), _B01_SHAPES)
def test_rcb01_points_emitted_do_not_change(days, start, end, seed):
    """RC-B01: whatever the walk's start, the builder emits exactly the points of its contract (an independent
    reference): from the first price of the range without a seed (a row before ``start`` is never emitted), from
    ``start`` with one, each empty day carrying the last known row with its day and distance.

    Green before X-R55 too: it pins the output the change to the walk's start had to keep.
    """
    rows = _rows(days)
    points = _build({row.date: row for row in rows}, start, end, seed)
    assert _projection(points) == _reference(rows, start, end, seed)


def test_rcb02_walk_starts_at_the_first_price_without_seed():
    """RC-B02: no seed, prices on the five days before today, asked from 1900-01-01: the walk starts at the first price.

    The map counts the days looked up: at most the 7 days from the first price to the end, not one per day since 1900.
    Red before X-R55: the walk looked up every day from 1900-01-01, 45 826 of them, to emit the same 7 points.
    """
    rows = _rows(_days(_day(-5), _day(-1)))
    price_map = _CountingPriceMap(rows)
    start, end = date(1900, 1, 1), CEILING
    points = _build(price_map, start, end)
    assert _projection(points) == _reference(rows, start, end, None)
    walk = (end - _day(-5)).days + 1
    lookups = price_map.lookups
    assert lookups <= walk, f"{lookups:,} days looked up for {walk} days from the first price {_day(-5)}: the walk starts at {start}"


def test_rcb03_empty_map_without_seed_returns_at_once():
    """RC-B03: an empty map and no seed: ``[]`` at once, not one day looked up.

    Red before X-R55: the walk looked up each of the 3 652 days of the range, to emit nothing.
    """
    price_map = _CountingPriceMap()
    assert _build(price_map, _day(-3650), CEILING) == []
    lookups = price_map.lookups
    assert lookups == 0, f"{lookups:,} days looked up in an empty map without a seed"


def test_rcb04_extreme_empty_range_guard():
    """RC-B04 (guard): 0001-01-01 … 9999-12-31, an empty map, no seed: ``[]`` at once, within ``GUARD_SECONDS``.

    The fuse in the map stops a walk past ``FUSE_DAY_STEPS`` days.
    Red before X-R55: the walk would have looked up 3 652 059 days to emit nothing, then failed stepping past
    9999-12-31 (OverflowError); the fuse stopped it first.
    """
    price_map = _CountingPriceMap(fuse=FUSE_DAY_STEPS)
    started = time.perf_counter()
    try:
        points = _build(price_map, YEAR_ONE, LAST_DAY)
    except _FuseTripped as fuse:
        pytest.fail(f"stopped by the fuse after {time.perf_counter() - started:.2f} s: {fuse}")
    _assert_within_guard(started)
    assert points == []
    lookups = price_map.lookups
    assert lookups == 0, f"{lookups:,} days looked up in an empty map without a seed"


# =============================================================================
# RC-A — get_prices_bulk, on a private database
# =============================================================================


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own; disposed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'range_ceiling.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


async def _asset(engine: AsyncEngine, *, prices: Iterable[date], events: Iterable[date] = ()) -> int:
    """An asset of the private database: a close on each day of ``prices`` (100, 101, … in order), a dividend on each of ``events``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"Range ceiling {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        for n, day in enumerate(sorted(prices)):
            session.add(PriceHistory(asset_id=asset.id, date=day, close=Decimal(100 + n), currency="EUR", source_plugin_key="MANUAL"))
        for day in events:
            session.add(AssetEvent(asset_id=asset.id, date=day, type=AssetEventType.DIVIDEND, value=Decimal("0.50"), currency="EUR"))
        await session.commit()
        return asset.id


async def _query(engine: AsyncEngine, *items: FAPriceQueryItem) -> list[FAPriceQueryResult]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await PriceQueryOperations.get_prices_bulk(list(items), session)


def _item(asset_id: int, start: date, end: date | None, **extra: Any) -> FAPriceQueryItem:
    return FAPriceQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=start, end=end), **extra)


def _price_days(result: FAPriceQueryResult) -> list[date]:
    return [point.date for point in result.prices]


@pytest.mark.asyncio
async def test_rca01_series_stops_at_the_ceiling(private_db, frozen_ceiling):
    """RC-A01: the last stored price yesterday, asked from today-3 up to today+10: the series ends on today+1, its last
    two days backward-filled from yesterday.

    Red before X-R55: the series ran on to today+10, nine backward-filled days past the ceiling.
    """
    asset_id = await _asset(private_db, prices=_days(_day(-5), _day(-1)))
    (result,) = await _query(private_db, _item(asset_id, _day(-3), _day(10)))
    days = _price_days(result)
    late = [day for day in days if day > CEILING]
    assert not late, f"points after the ceiling {CEILING}: {_span(late)}"
    assert days == _days(_day(-3), CEILING)
    assert [(p.backward_fill_info.actual_rate_date, p.backward_fill_info.days_back) for p in result.prices[-2:]] == [(_day(-1), 1), (_day(-1), 2)]
    assert result.errors == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_offset", "expected_offsets"),
    [pytest.param(1, [1], id="start-on-the-ceiling"), pytest.param(2, [], id="start-the-day-after-the-ceiling")],
)
async def test_rca02_range_after_the_ceiling(private_db, frozen_ceiling, start_offset, expected_offsets):
    """RC-A02: up to today+30, starting on the ceiling (today+1): that one day, backward-filled; starting the day after
    it: an empty series, and no error.

    Red before X-R55: both ran on to today+30, backward-filled from yesterday's price (30 and 29 points).
    """
    asset_id = await _asset(private_db, prices=_days(_day(-5), _day(-1)))
    (result,) = await _query(private_db, _item(asset_id, _day(start_offset), _day(30)))
    assert result.asset_id == asset_id
    assert _price_days(result) == [_day(offset) for offset in expected_offsets], f"got {_span(_price_days(result))}"
    assert result.errors == []


@pytest.mark.asyncio
async def test_rca03_events_follow_the_clamped_range(private_db, frozen_ceiling):
    """RC-A03 (N75 revision): events dated today-2, today, today+1, today+2 and today+5, asked up to today+10: the
    ones after today+1 are not returned though the requested range covers them; today's and today+1's still are.

    Red before X-R55: the events of today+2 and today+5 came back too.
    """
    asset_id = await _asset(private_db, prices=_days(_day(-5), _day(-1)), events=[_day(offset) for offset in (-2, 0, 1, 2, 5)])
    (result,) = await _query(private_db, _item(asset_id, _day(-3), _day(10), include_events=True))
    returned = [event.date for event in result.events]
    assert returned == [_day(-2), _day(0), _day(1)], f"events returned: {returned} (ceiling {CEILING})"


@pytest.mark.asyncio
async def test_rca04_item_after_the_ceiling_is_empty_in_its_place(private_db, frozen_ceiling):
    """RC-A04 (N75 revision): three items in one call — a past one, one wholly after the ceiling, a past one — give,
    in that order: the first as when asked alone; an empty result at position 1 (its asset id, no price, no event, no
    error), though that asset has prices before and an event inside the requested range; the third as when asked alone.

    Red before X-R55: position 1 held 11 points backward-filled up to today+30, and the event of today+25.
    """
    first = await _asset(private_db, prices=_days(_day(-15), _day(-1)), events=[_day(-8)])
    second = await _asset(private_db, prices=_days(_day(-15), _day(-1)), events=[_day(-3), _day(25)])
    past = _item(first, _day(-10), _day(-1), include_events=True)
    future = _item(second, _day(20), _day(30), include_events=True)
    other_past = _item(second, _day(-6), _day(-2), include_events=True)

    results = await _query(private_db, past, future, other_past)

    assert [result.asset_id for result in results] == [first, second, second]
    middle = results[1]
    assert (middle.prices, middle.events, middle.errors) == ([], [], []), f"position 1: prices {_span(_price_days(middle))}, events {[e.date for e in middle.events]}, errors {middle.errors}"
    (alone_past,) = await _query(private_db, past)
    (alone_other,) = await _query(private_db, other_past)
    assert alone_past.prices and alone_other.prices and alone_other.events, "the items asked alone must have data to compare"
    assert results[0].model_dump() == alone_past.model_dump()
    assert results[2].model_dump() == alone_other.model_dump()


@pytest.mark.asyncio
async def test_rca05_signal_input_stops_at_the_ceiling(private_db, monkeypatch, frozen_ceiling):
    """RC-A05: a signal on a range reaching today+10 computes on a series that ends on today+1 (the signal context and
    the load range see the clamped range). Read through ``availability.input_coverage.last_available_date``, the last
    day of the series the signal was handed.

    Red before X-R55: the signal read the backward-filled days up to today+10.
    """

    async def _no_market_holidays() -> frozenset[date]:
        return frozenset()

    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    asset_id = await _asset(private_db, prices=_days(_day(-30), _day(-1)))
    (result,) = await _query(private_db, _item(asset_id, _day(-10), _day(10), signals=[SMA3]))
    (signal,) = result.signals
    assert signal.availability is not None and signal.availability.input_coverage is not None, signal
    last_input_day = signal.availability.input_coverage.last_available_date
    assert last_input_day == CEILING, f"the signal was handed a series ending {last_input_day}, past the ceiling {CEILING}"


@pytest.mark.asyncio
async def test_rca06_extreme_range_guard(private_db, monkeypatch, frozen_ceiling):
    """RC-A06 (guard): 0001-01-01 … 9999-12-31 answers within ``GUARD_SECONDS`` with the three stored days and the two
    backward-filled ones up to the ceiling — at most ``latest_range_end() - first point + 1`` points.

    Red before X-R55: the builder walked the 739 416 empty days from 0001-01-01, then would have backward-filled
    2 912 640 points and failed stepping past 9999-12-31 (OverflowError); the fuse on ``price_query.timedelta`` stopped
    the walk first, after ``FUSE_DAY_STEPS`` steps.
    """
    asset_id = await _asset(private_db, prices=_days(_day(-3), _day(-1)))
    _install_fuse(monkeypatch, price_query)
    (result,) = await _within_guard(lambda: _query(private_db, _item(asset_id, YEAR_ONE, LAST_DAY)))
    days = _price_days(result)
    assert days, "no point at all: the stored days are missing"
    assert len(days) <= (CEILING - days[0]).days + 1, f"{len(days):,} points from {days[0]}"
    assert days == _days(_day(-3), CEILING), f"got {_span(days)}"


# =============================================================================
# RC-F — POST /fx/currencies/convert (the handler, called directly)
# =============================================================================


def _rate(day: date) -> Decimal:
    """The in-process converter's rate on ``day``: it moves from day to day, so two series compare day by day."""
    return Decimal("1.1") + Decimal(day.toordinal() % 7) / 100


class _Converter:
    """In-process ``convert_bulk``: a rate on every day for every pair but those listed without rates; records every
    item it is handed. A pair without rates answers as ``convert_bulk`` does: ``None`` and its error, item by item."""

    def __init__(self, *, without_rates: frozenset[tuple[str, str]] = frozenset()) -> None:
        self.without_rates = without_rates
        self.handed: list[date] = []

    async def __call__(self, _session: Any, conversions: list, raise_on_error: bool = True) -> tuple[list, list[str]]:
        results, errors = [], []
        for index, (amount, to_currency, on_day) in enumerate(conversions):
            self.handed.append(on_day)
            if amount.code == to_currency:
                results.append((Currency(code=to_currency, amount=amount.amount), on_day, False))
            elif (amount.code, to_currency) in self.without_rates:
                base, quote = sorted((amount.code, to_currency))
                results.append(None)
                errors.append(f"Conversion {index}: No FX rate found for {base}/{quote} on or before {on_day}. Please sync rates using POST /api/v1/fx/currencies/sync")
            else:
                results.append((Currency(code=to_currency, amount=amount.amount * _rate(on_day)), on_day, False))
        return results, errors


def _conversion(amount: str, start: date, end: date | None, *, signals: Iterable[SignalRequest] = ()) -> FXConversionRequest:
    return FXConversionRequest(from_amount=Currency(code="EUR", amount=Decimal(amount)), to_currency="USD", date_range=DateRangeModel(start=start, end=end), signals=list(signals))


async def _convert(monkeypatch: pytest.MonkeyPatch, converter: _Converter, *conversions: FXConversionRequest) -> FXConvertResponse:
    monkeypatch.setattr(currencies, "convert_bulk", converter)
    return await currencies.convert_currency_bulk(request=list(conversions), session=None, _current_user=None)


def _result_days(response: FXConvertResponse, amount: str | None = None) -> list[date]:
    """The days of the conversion results, of one conversion when ``amount`` (each conversion here has its own)."""
    return [r.conversion_date for r in response.results if amount is None or r.from_amount.amount == Decimal(amount)]


def _dumps(models: Iterable[Any]) -> list[dict]:
    return [model.model_dump(mode="json") for model in models]


@pytest.mark.asyncio
async def test_rcf01_conversion_stops_at_the_ceiling(monkeypatch, frozen_ceiling):
    """RC-F01: a conversion asked from today-5 up to today+10 gives its last result on today+1.

    Red before X-R55: one result a day up to today+10.
    """
    response = await _convert(monkeypatch, _Converter(), _conversion("100", _day(-5), _day(10)))
    days = _result_days(response)
    late = [day for day in days if day > CEILING]
    assert not late, f"conversions after the ceiling {CEILING}: {_span(late)}"
    assert days == _days(_day(-5), CEILING)
    assert response.errors == []


@pytest.mark.asyncio
async def test_rcf02_start_before_the_floor_is_raised_to_it(monkeypatch, frozen_ceiling):
    """RC-F02: from 1900-01-01 to yesterday, with a signal: the daily results start on ``range_span_floor(yesterday)``,
    100 years back, and no day before that floor reaches the converter, the signal's warm-up included.

    Red before X-R55: the converter was handed days from 1899-12-26 on (1900-01-01 less the warm-up), and 45 824 daily
    results.
    """
    converter = _Converter()
    end = _day(-1)
    response = await _convert(monkeypatch, converter, _conversion("100", date(1900, 1, 1), end, signals=[SMA3]))
    floor = _floor(end)
    earliest = min(converter.handed, default=None)
    assert earliest is not None and earliest >= floor, f"the converter was handed {earliest}, before the floor {floor}"
    days = _result_days(response)
    assert (days[0], days[-1], len(days)) == (floor, end, RANGE_SPAN_LIMIT_DAYS + 1), f"daily results: {_span(days)}"
    assert [result.request_index for result in response.signal_results] == [0]


class _FullHistoryPlans(SignalService):
    """The handler's ``SignalService``, its plans asking for the whole history before the visible range.

    No FX signal plugin is full-history today (RISK_DRAWDOWN, the one there is, is ASSET-only), so the plan stands in:
    ``requires_full_history`` set, and a warm-up of more calendar days than lie between 0001-01-01 and 9999-12-31 —
    without the floor, the handler would start the warm-up on 0001-01-01. The computations are the real ones.
    """

    def prepare_plan(self, requests, context, annotation_requests=()):
        plan = super().prepare_plan(requests, context, annotation_requests)
        return dataclasses.replace(plan, requires_full_history=True, max_calendar_total_points=(LAST_DAY - YEAR_ONE).days)


@pytest.mark.asyncio
@pytest.mark.parametrize("start", [pytest.param(date(1900, 1, 1), id="start-1900"), pytest.param(_day(-30), id="start-a-month-ago")])
async def test_rcf03_full_history_warmup_stops_at_the_floor(monkeypatch, frozen_ceiling, start):
    """RC-F03: a full-history signal up to yesterday hands the converter no day before ``range_span_floor(yesterday)``;
    the daily results run from ``max(start, floor)`` to yesterday, and the signal result is there.

    Red before X-R55: the warm-up started on 0001-01-01, about 739 000 days; the fuse on the handler's ``timedelta``
    stopped it.
    """
    monkeypatch.setattr(currencies, "SignalService", _FullHistoryPlans)
    _install_fuse(monkeypatch, currencies)
    converter = _Converter()
    end = _day(-1)
    response = await _within_guard(lambda: _convert(monkeypatch, converter, _conversion("100", start, end, signals=[SMA3])))
    floor = _floor(end)
    earliest = min(converter.handed, default=None)
    assert earliest is not None and earliest >= floor, f"the converter was handed {earliest}, before the floor {floor}"
    first = max(start, floor)
    days = _result_days(response)
    assert (days[0], days[-1], len(days)) == (first, end, (end - first).days + 1), f"daily results: {_span(days)}"
    assert [result.request_index for result in response.signal_results] == [0]


@pytest.mark.asyncio
async def test_rcf04_conversion_after_the_ceiling_is_empty_others_unaffected(monkeypatch, frozen_ceiling):
    """RC-F04 (N75 revision): a past conversion, one wholly after the ceiling with a signal, a past one with a signal,
    in one call. The one after the ceiling gives no result and no error; its signal result is there, equal to what the
    same request gets from a converter without rates for its pair (an empty series). The other two give what they give
    alone, signal included.

    Red before X-R55: the conversion after the ceiling gave 11 results, backward-filled up to today+30.
    """
    past = _conversion("100", _day(-6), _day(-2))
    after_ceiling = _conversion("200", _day(20), _day(30), signals=[SMA3])
    past_with_signal = _conversion("300", _day(-9), _day(-1), signals=[SMA3])

    mixed = await _convert(monkeypatch, _Converter(), past, after_ceiling, past_with_signal)

    assert _result_days(mixed, "200") == [], f"results of the conversion after the ceiling: {_span(_result_days(mixed, '200'))}"
    assert mixed.errors == []
    signals_by_index = {result.request_index: result.signals for result in mixed.signal_results}
    assert sorted(signals_by_index) == [1, 2]

    without_rates = await _convert(monkeypatch, _Converter(without_rates=frozenset({("EUR", "USD")})), after_ceiling)
    (empty_series,) = without_rates.signal_results
    assert empty_series.signals and all(not signal.series for signal in empty_series.signals), "the reference is the empty-series result"
    assert _dumps(signals_by_index[1]) == _dumps(empty_series.signals)

    alone_past = await _convert(monkeypatch, _Converter(), past)
    alone_with_signal = await _convert(monkeypatch, _Converter(), past_with_signal)
    assert _dumps(r for r in mixed.results if r.from_amount.amount == Decimal("100")) == _dumps(alone_past.results)
    assert _dumps(r for r in mixed.results if r.from_amount.amount == Decimal("300")) == _dumps(alone_with_signal.results)
    assert _dumps(signals_by_index[2]) == _dumps(alone_with_signal.signal_results[0].signals)


@pytest.mark.asyncio
async def test_rcf05_extreme_range_guard(monkeypatch, frozen_ceiling):
    """RC-F05 (guard): 0001-01-01 … 9999-12-31 answers within ``GUARD_SECONDS`` with one result a day from
    ``range_span_floor(today+1)`` to today+1 — 36 526 results, at most ``latest_range_end() - first + 1`` — no error,
    and nothing outside that span handed to the converter.

    Red before X-R55: 3 652 059 daily conversions, built before the converter was even called, and an OverflowError
    stepping past 9999-12-31; the fuse on the handler's ``timedelta`` stopped the expansion first, after
    ``FUSE_DAY_STEPS`` days.
    """
    _install_fuse(monkeypatch, currencies)
    converter = _Converter()
    response = await _within_guard(lambda: _convert(monkeypatch, converter, _conversion("100", YEAR_ONE, LAST_DAY)))
    floor = _floor(CEILING)
    days = _result_days(response)
    assert days, "no result at all"
    assert len(days) <= (CEILING - days[0]).days + 1, f"{len(days):,} results from {days[0]}"
    assert (days[0], days[-1], len(days), len(set(days))) == (floor, CEILING, RANGE_SPAN_LIMIT_DAYS + 1, RANGE_SPAN_LIMIT_DAYS + 1), f"daily results: {_span(days)}"
    assert response.errors == []
    assert floor <= min(converter.handed) and max(converter.handed) <= CEILING


@pytest.mark.asyncio
async def test_rcf06_signal_results_echo_the_range_they_cover(monkeypatch, frozen_ceiling):
    """RC-F06 (X's review, LOW): each signal result's ``date_range`` is the range its signals cover, not the one asked.

    Four conversions with a signal in one call, so each echo is read at its own ``request_index``: (a) up to the ceiling
    + 9 days → the requested start to ``CEILING``; (b) from 1800-01-01 to the same end → ``range_span_floor(CEILING)``
    to ``CEILING``; (c) wholly after the ceiling → the requested range, as asked (its signals see no point); (d) a range
    the ceiling does not cut → as asked.
    No red phase: written after the fix, it pins X's review of X-R55. Until then every signal result echoed the requested
    range, even where the signals stopped at the ceiling or started at the floor.
    """
    asked = {
        "cut-at-the-ceiling": _conversion("100", _day(-6), CEILING + timedelta(days=9), signals=[SMA3]),
        "start-raised-to-the-floor": _conversion("200", date(1800, 1, 1), CEILING + timedelta(days=9), signals=[SMA3]),
        "wholly-after-the-ceiling": _conversion("300", _day(20), _day(30), signals=[SMA3]),
        "not-cut": _conversion("400", _day(-9), _day(-2), signals=[SMA3]),
    }
    expected = {
        "cut-at-the-ceiling": DateRangeModel(start=_day(-6), end=CEILING),
        "start-raised-to-the-floor": DateRangeModel(start=_floor(CEILING), end=CEILING),
        "wholly-after-the-ceiling": DateRangeModel(start=_day(20), end=_day(30)),
        "not-cut": DateRangeModel(start=_day(-9), end=_day(-2)),
    }

    response = await _convert(monkeypatch, _Converter(), *asked.values())

    by_index = {result.request_index: result for result in response.signal_results}
    assert sorted(by_index) == [0, 1, 2, 3], f"signal results at {sorted(by_index)}"
    echoed = {label: by_index[index].date_range for index, label in enumerate(asked)}
    assert echoed == expected
    for index, conversion in enumerate(asked.values()):
        assert (by_index[index].from_currency, by_index[index].to_currency) == (conversion.from_amount.code, conversion.to_currency)


# =============================================================================
# RC-S — the refresh walk over its history cache (refresh._fetch_refresh_item)
# =============================================================================
#
# The fetch step called directly with a prepared item and an in-process provider double, as the X-R12 cases of
# test_asset_source_refresh do: no database, no network. Today is frozen through refresh.date_type; the history cache
# is a stand-in serving one entry, whose ``dates`` count the days the walk tests against them.

_FLOOR_OFFSET = -1 - RANGE_SPAN_LIMIT_DAYS  # range_span_floor(yesterday), as an offset from today
_CACHED_CLOSE = Decimal("7")
_HISTORY_CLOSE = Decimal("10")
_CURRENT_VALUE = Decimal("11")


class _FrozenRefreshDate(date):
    """``refresh.date_type`` during these cases: ``today()`` is ``FROZEN_TODAY``, the rest a plain ``date``."""

    @classmethod
    def today(cls) -> date:
        return FROZEN_TODAY


class _CountingCachedDays(dict):
    """The ``dates`` of a history cache entry (ISO day → point), counting the days the walk tests against it.

    ``fuse`` stops a walk testing more days than that, raising inside it.
    """

    def __init__(self, days: Iterable[date], *, fuse: int | None = None) -> None:
        super().__init__({day.isoformat(): {"date": day, "close": _CACHED_CLOSE, "currency": "EUR"} for day in days})
        self.tests = 0
        self.fuse = fuse

    def __contains__(self, key: object) -> bool:
        self.tests += 1
        if self.fuse is not None and self.tests > self.fuse:
            raise _FuseTripped(f"more than {self.fuse:,} days tested against the history cache")
        return super().__contains__(key)


class _HistoryCache:
    """``core._asset_history_cache`` for one case: serves its one entry whatever the key; what is stored is kept apart."""

    def __init__(self, entry: dict | None) -> None:
        self.entry = entry
        self.stored: list[tuple[Any, Any]] = []

    def get(self, _key: Any) -> tuple[Any, bool]:
        return (self.entry, True) if self.entry is not None else (None, False)

    def set(self, key: Any, value: Any, **_kwargs: Any) -> None:
        self.stored.append((key, value))

    def delete(self, _key: Any) -> None:
        return None


class _NoCurrentCache:
    """``core._asset_current_cache`` for these cases: never hits, never stores."""

    def get(self, _key: Any) -> tuple[None, bool]:
        return None, False

    def set(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def delete(self, _key: Any) -> None:
        return None


class _ProviderDouble:
    """In-process provider: not a plugin, so ``core.call_provider`` calls it as it is (no settings, no pause, no network).

    Records each history call; answers at most three closes, up to yesterday, and a current value dated today.
    """

    provider_code = "rcfake"
    supports_history = True

    def __init__(self) -> None:
        self.history_calls: list[tuple[date, date]] = []

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        self.history_calls.append((start_date, end_date))
        last = min(end_date, _day(-1))
        days = [day for day in _days(last - timedelta(days=2), last) if day >= start_date]
        return FAHistoricalData(prices=[FAPricePoint(date=day, close=_HISTORY_CLOSE, currency="EUR") for day in days], events=[], currency="EUR", source=self.provider_code)

    async def get_current_value(self, identifier, identifier_type, provider_params) -> FACurrentValue:
        return FACurrentValue(value=_CURRENT_VALUE, currency="EUR", as_of_date=FROZEN_TODAY, source=self.provider_code)


@dataclasses.dataclass
class _FetchOutcome:
    provider: _ProviderDouble
    data: Any
    error: str | None


@pytest.fixture
def fetch_step(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Awaitable[_FetchOutcome]]:
    """The refresh fetch step for one prepared item, today frozen and the two core caches stood in."""
    monkeypatch.setattr(refresh, "date_type", _FrozenRefreshDate)
    monkeypatch.setattr(core, "_asset_current_cache", _NoCurrentCache())

    async def run(start: date, end: date, cached: _CountingCachedDays) -> _FetchOutcome:
        monkeypatch.setattr(core, "_asset_history_cache", _HistoryCache({"dates": cached, "events": []}))
        provider = _ProviderDouble()
        prep = refresh._PreparedRefreshItem(
            assignment_id=None,
            asset_currency="EUR",
            provider=provider,
            provider_code=provider.provider_code,
            provider_params=None,
            identifier=f"RC-{uuid.uuid4().hex}",
            identifier_type=ProviderInputType.TICKER,
            start=start,
            end=end,
        )
        data, error, refusal = await refresh._fetch_refresh_item(1, prep, asyncio.Semaphore(1), 60)
        assert refusal is None, refusal
        return _FetchOutcome(provider=provider, data=data, error=error)

    return run


def _cached(*spans: tuple[int, int], fuse: int | None = None) -> _CountingCachedDays:
    """Cached days: every day of each ``(first, last)`` span of offsets from today."""
    return _CountingCachedDays((day for first, last in spans for day in _days(_day(first), _day(last))), fuse=fuse)


def _pre_n75_window(start: date, end: date, cached: Iterable[str]) -> tuple[date, date] | None:
    """The history call the refresh made before N75 for this cache: the first and last missing day of the whole walk
    (the last one replaced by today when the range reaches today), or ``None`` on a full hit. The reference for
    "never asked less"."""
    today = FROZEN_TODAY
    history_end = min(end, today - timedelta(days=1)) if end >= today else end
    have = set(cached)
    missing = [day for day in _days(start, history_end) if day.isoformat() not in have]
    if not missing:
        return None
    return missing[0], today if end >= today else missing[-1]


@pytest.mark.asyncio
async def test_rcs01_walk_is_bounded_and_the_start_still_asked(fetch_step):
    """RC-S01: from 1800-01-01 up to today, with a history cache of the last 30 days: the provider is still asked from
    1800-01-01 up to today, as before, but the walk tests at most ``RANGE_SPAN_LIMIT_DAYS + 3`` days against the cache
    (the 100 years up to yesterday, both ends included, then the start and the day before the floor).

    Red before X-R55: the walk tested every day from 1800-01-01 to yesterday, 82 348 of them.
    """
    cached = _cached((-30, -1))
    outcome = await fetch_step(date(1800, 1, 1), FROZEN_TODAY, cached)
    assert outcome.provider.history_calls == [(date(1800, 1, 1), FROZEN_TODAY)]
    tests = cached.tests
    assert tests <= WALK_BOUND, f"the walk tested {tests:,} days against the cache (bound {WALK_BOUND:,})"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start", "end", "spans", "expected"),
    [
        pytest.param(-60, -1, [(-20, -1)], (-60, -21), id="past-range-the-cache-holding-its-tail"),
        pytest.param(-60, 0, [(-20, -1)], (-60, 0), id="range-reaching-today"),
        pytest.param(-50, -5, [(-40, -31), (-15, -5)], (-50, -16), id="two-gaps"),
        pytest.param(-30, -1, [(-30, -1)], None, id="full-hit"),
        pytest.param(_FLOOR_OFFSET, -1, [(-10, -1)], (_FLOOR_OFFSET, -11), id="start-on-the-floor"),
    ],
)
async def test_rcs02_fetch_window_unchanged_from_the_floor_on(fetch_step, start, end, spans, expected):
    """RC-S02: a start on the floor or after it asks the provider exactly what it asked before — the first and the last
    missing day (up to today when the range reaches today), or nothing on a full hit. A start on the floor itself is
    not before it: neither it nor the day before the floor is added.

    Green before X-R55 too: these windows are the ones it asked.
    """
    outcome = await fetch_step(_day(start), _day(end), _cached(*spans))
    assert outcome.provider.history_calls == ([] if expected is None else [(_day(expected[0]), _day(expected[1]))])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("end", "spans", "exact"),
    [
        pytest.param(-1, [(_FLOOR_OFFSET, -1)], (_FLOOR_OFFSET - 100, _FLOOR_OFFSET - 1), id="cache-holding-the-whole-span"),
        pytest.param(0, [(_FLOOR_OFFSET, -1)], (_FLOOR_OFFSET - 100, 0), id="cache-holding-the-whole-span-range-reaching-today"),
        pytest.param(-1, [(_FLOOR_OFFSET - 50, -1)], None, id="cache-reaching-50-days-before-the-floor"),
    ],
)
async def test_rcs03_start_before_the_floor_is_never_asked_less(fetch_step, end, spans, exact):
    """RC-S03: a start 100 days before the floor: the provider is asked from that start, and the window covers the one
    asked before N75 (never less). With the whole span from the floor cached, that is exactly the start to the day
    before the floor — the day the contract adds — or to today when the range reaches today.

    Green before X-R55 too: its window was the reference itself.
    """
    start = _day(_FLOOR_OFFSET - 100)
    cached = _cached(*spans)
    before = _pre_n75_window(start, _day(end), cached.keys())
    outcome = await fetch_step(start, _day(end), cached)
    assert before is not None
    assert len(outcome.provider.history_calls) == 1, outcome.provider.history_calls
    ((asked_start, asked_end),) = outcome.provider.history_calls
    assert asked_start == start
    assert asked_end >= before[1], f"asked up to {asked_end}, less than the {before[1]} asked before"
    if exact is not None:
        assert (asked_start, asked_end) == (_day(exact[0]), _day(exact[1]))


@pytest.mark.asyncio
async def test_rcs04_extreme_range_guard(fetch_step):
    """RC-S04 (guard): 0001-01-01 … 9999-12-31 with a history cache: within ``GUARD_SECONDS`` the provider is asked
    from 0001-01-01 up to today, the walk testing at most ``RANGE_SPAN_LIMIT_DAYS + 3`` days against the cache.

    Red before X-R55: the walk tested every day from 0001-01-01 to yesterday, 739 419 of them; a fuse in the cached days
    stopped it after 4 × ``RANGE_SPAN_LIMIT_DAYS`` tests — the refresh took that for a failed history fetch, and never
    asked.
    """
    cached = _cached((-30, -1), fuse=4 * RANGE_SPAN_LIMIT_DAYS)
    started = time.perf_counter()
    outcome = await fetch_step(YEAR_ONE, LAST_DAY, cached)
    tests = cached.tests
    assert tests <= WALK_BOUND, f"the walk tested {tests:,} days against the cache (bound {WALK_BOUND:,}; fuse at {cached.fuse:,})"
    assert outcome.provider.history_calls == [(YEAR_ONE, FROZEN_TODAY)]
    _assert_within_guard(started)

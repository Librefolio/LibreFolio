"""Z-25 (night decision N77): a bulk price or FX request has two caps — how many items it holds, and the item-days they cost.

The defect, of X-R55's family (and R13-SEC7's): after X-R55 every range ends at tomorrow and an FX range spans 100 years
at most, but nothing bounds how many ranges one request holds. ``POST /fx/currencies/convert`` with 500 conversions of
100 years builds 18 million daily conversions; ``POST /assets/prices/query`` backward-fills one point a day per item from
its first price — and a full-history signal (``RISK_DRAWDOWN``) loads from ``date.min``, so an item whose visible range
is ONE day still makes the fill emit every day since the first stored price. Any logged-in user can send either. The
contract pinned here (N77):

1. ``backend/app/utils/date_range_limits.py`` holds ``MAX_BULK_ITEMS = 1_000``, ``MAX_BULK_ITEM_DAYS = 5_000_000`` and
   ``BulkTooManyDaysError``, with ``item_days`` and ``max_item_days``. ``price_query`` and ``currencies`` import the
   budget by name where they apply it: the seam these tests lower it through (``lower_budget``), as ``lift_range_bound``
   lifts X-R55's ceiling.
2. Items: both routes, before any work — no statement read, nothing converted — answer 422 ``{"code":
   "bulk_too_many_items", "message", "max_items": 1000, "items": n}`` to more than ``MAX_BULK_ITEMS`` items, whatever
   their ranges. Exactly 1 000 pass.
3. Item-days, prices: ``get_prices_bulk``, once the prices and the seeds are read and before the fill, sums for every
   item the span its fill will emit — from ``max(load start, first price or seed)`` to the cut end, 0 for an item that
   emits nothing, the comparison series of its signals included — and raises ``BulkTooManyDaysError(item_days=total,
   max_item_days=budget)`` when the total exceeds the budget; the route turns it into 422 ``{"code":
   "bulk_too_many_days", "message", "max_item_days", "item_days"}``. Up to the budget nothing changes.
4. Item-days, FX: the handler counts the daily items and the signal items (warm-up included) it is about to build,
   conversion by conversion; as soon as the running total exceeds the budget it answers 422 with the same detail,
   ``item_days`` the count at that point — more than the budget, at most the total through the conversion that crossed
   it — and ``convert_bulk`` is never called.

The budget is lowered to a few dozen item-days, so each case stays small; the real numbers are pinned by BL-001 and used
by the guards that are cheap to refuse: 1 001 items (BL-I01…I03) and 200 one-day items of 36 525 filled days each
(BL-A06). The real budget through the conversion route is BL-API-03 (``api fx``); through the price route it is not
tested at API level: over 5 million item-days, code without the budget would make the lane's shared backend build them.

Isolation: PURE — no lane database, no server, no network. The price queries run on a private SQLite file under
``tmp_path`` built by ``create_all``, or on a stand-in session that answers every statement with no row and counts them;
the conversion handler is called directly, ``convert_bulk`` replaced by an in-process converter that records what it is
handed; the market holiday table is an empty one.

Red before the change (HEAD eed325d99), each for the reason its docstring gives ("Red before Z-25"): BL-001, BL-002,
BL-I01…I03, BL-A01, BL-A03…A07, BL-F01…F03. Green then too — behaviour the change has to keep: BL-I04, BL-A02.
"""

from __future__ import annotations

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
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1.assets import prices
from backend.app.api.v1.fx import currencies
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, PriceHistory
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest, FXConvertResponse
from backend.app.schemas.prices import FAPriceQueryItem, FAPriceQueryResponse, FAPriceQueryResult
from backend.app.schemas.signals import SignalRequest
from backend.app.services.assets import price_query
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.utils import date_range_limits

#: Where the item-day budget is applied: the modules that import ``MAX_BULK_ITEM_DAYS`` by name (BL-002).
BUDGET_CONSUMERS = ("backend.app.services.assets.price_query", "backend.app.api.v1.fx.currencies")
#: Where it may be read at all: the consumers, the module that defines it and the price route. All are lowered, so the
#: 422's ``max_item_days`` reports the lowered budget whichever of them builds the detail.
BUDGET_READERS = (*BUDGET_CONSUMERS, "backend.app.utils.date_range_limits", "backend.app.api.v1.assets.prices")

MAX_ITEMS = 1_000  # the contract's numbers, written here and not read from the module under test
MAX_ITEM_DAYS = 5_000_000
HUNDRED_YEARS = 36_525  # days: from 36 524 days back to today, a fill emits this many
FROZEN_TODAY = date(2025, 6, 18)  # any day: the ceiling is frozen at the day after it
CEILING = FROZEN_TODAY + timedelta(days=1)  # latest_range_end(), frozen
LAST_DAY = date(9999, 12, 31)
FUSE_DAY_STEPS = 200_000  # one day-step per item built: no refused request here builds one
GUARD_SECONDS = 20.0  # a refusal takes milliseconds; building the refused request, minutes
SMA3 = SignalRequest(instance_id="sma3", signal_code="SMA", params={"period": 3})
DRAWDOWN = SignalRequest(instance_id="drawdown", signal_code="RISK_DRAWDOWN", params={})  # full history by default


def _day(offset: int) -> date:
    """``FROZEN_TODAY`` plus ``offset`` days."""
    return FROZEN_TODAY + timedelta(days=offset)


def _days(first: date, last: date) -> list[date]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


# =============================================================================
# THE CEILING, THE BUDGET, THE FUSE
# =============================================================================


@pytest.fixture
def frozen_ceiling(monkeypatch: pytest.MonkeyPatch) -> date:
    """``latest_range_end()`` answers ``CEILING`` where X-R55 reads it, whatever the day the suite runs."""
    for module in ("backend.app.services.assets.price_query", "backend.app.api.v1.fx.currencies"):
        monkeypatch.setattr(f"{module}.latest_range_end", lambda: CEILING)
    return CEILING


@pytest.fixture
def lower_budget(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Sets ``MAX_BULK_ITEM_DAYS`` to the given item-days in every ``BUDGET_READERS`` module, for the test.

    Set even where the name is missing (``raising=False``): on code without the budget the call then runs as it always
    did, and the case fails on what it built — the budget not enforced — not on a missing attribute. Where the budget
    is read is BL-002's question.
    """

    def lower(item_days: int) -> None:
        for name in BUDGET_READERS:
            monkeypatch.setattr(importlib.import_module(name), "MAX_BULK_ITEM_DAYS", item_days, raising=False)

    return lower


@pytest.fixture
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The signals' market holiday table, empty: built for real it takes a process of its own."""

    async def _none() -> frozenset[date]:
        return frozenset()

    monkeypatch.setattr(price_query, "ensure_market_holidays", _none)


class _FuseTripped(Exception):
    """A per-day loop went past its fuse: the request was being built, day by day."""


class _DayStepFuse:
    """Stands in for ``timedelta`` in one product module: counts the calls, and raises past ``limit``.

    The per-day loops of the code under test step with ``timedelta(days=1)``, one call per item built; the values
    returned are real ``timedelta`` objects, so the arithmetic is unchanged.
    """

    def __init__(self, limit: int = FUSE_DAY_STEPS) -> None:
        self.limit = limit
        self.calls = 0

    def __call__(self, *args: Any, **kwargs: Any) -> timedelta:
        self.calls += 1
        if self.calls > self.limit:
            raise _FuseTripped(f"more than {self.limit:,} timedelta() steps in one call: the request is being built day by day")
        return timedelta(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(timedelta, name)


def _install_fuse(monkeypatch: pytest.MonkeyPatch, module: Any) -> _DayStepFuse:
    fuse = _DayStepFuse()
    monkeypatch.setattr(module, "timedelta", fuse)
    return fuse


async def _within_guard[ResultT](make_call: Callable[[], Awaitable[ResultT]]) -> ResultT:
    """Run one call that would be expensive unbounded: a tripped fuse fails the test here, saying so; then the clock."""
    started = time.perf_counter()
    try:
        result = await make_call()
    except _FuseTripped as fuse:
        pytest.fail(f"stopped by the fuse after {time.perf_counter() - started:.2f} s: {fuse}")
    elapsed = time.perf_counter() - started
    assert elapsed < GUARD_SECONDS, f"{elapsed:.1f} s, past the {GUARD_SECONDS:.0f} s bound"
    return result


# =============================================================================
# REFUSALS: WHAT A REFUSED CALL RAISES, AND WHAT IT BUILT WHEN IT RAISED NOTHING
# =============================================================================


def _answered(answer: Any) -> str:
    if isinstance(answer, FXConvertResponse):
        return f"{len(answer.results):,} results and {len(answer.signal_results)} signal results"
    if isinstance(answer, FAPriceQueryResponse):
        return f"{len(answer.items):,} items and {sum(len(item.prices) for item in answer.items):,} points"
    return repr(answer)[:200]


async def _refusal(make_call: Callable[[], Awaitable[Any]], also: Callable[[], str] = lambda: "") -> HTTPException:
    """The ``HTTPException`` the route raises; when it raises none, the test fails saying what it answered (and ``also``)."""
    try:
        answer = await make_call()
    except HTTPException as refused:
        return refused
    pytest.fail(f"no refusal: the route answered {_answered(answer)}{also()}")


def _coded_detail(refused: HTTPException, code: str) -> dict:
    """The 422's coded detail: its ``code`` checked, a non-empty ``message``; returned for the numbers."""
    detail = refused.detail
    assert refused.status_code == 422, f"{refused.status_code}: {detail!r}"
    assert isinstance(detail, dict), f"the 422 is not coded: {detail!r}"
    assert detail.get("code") == code, detail
    message = detail.get("message")
    assert isinstance(message, str) and message.strip(), f"no message: {detail!r}"
    return detail


def _numbers(detail: dict) -> dict:
    """The detail without its ``code`` and ``message``: what is left must be exactly the contract's numbers."""
    return {key: value for key, value in detail.items() if key not in ("code", "message")}


async def _refused_for_days(make_call: Callable[[], Awaitable[list[FAPriceQueryResult]]]) -> Any:
    """The ``BulkTooManyDaysError`` the price query raises; when it raises none, the test fails saying what it built."""
    error_class = getattr(date_range_limits, "BulkTooManyDaysError", None)
    try:
        results = await make_call()
    except Exception as error:
        if error_class is not None and isinstance(error, error_class):
            return error
        raise
    points = sum(len(result.prices) for result in results)
    pytest.fail(f"no BulkTooManyDaysError: the fill ran, {len(results)} items and {points:,} visible points returned")


# =============================================================================
# PRICES: A PRIVATE DATABASE, AND A SESSION THAT READS NOTHING
# =============================================================================


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own; disposed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bulk_limits.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


async def _asset(engine: AsyncEngine, *, prices_on: Iterable[date] = ()) -> int:
    """An asset of the private database, with a close on each day of ``prices_on`` (100, 101, … in order)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"Bulk limits {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        for n, day in enumerate(sorted(prices_on)):
            session.add(PriceHistory(asset_id=asset.id, date=day, close=Decimal(100 + n), currency="EUR", source_plugin_key="MANUAL"))
        await session.commit()
        return asset.id


async def _query(engine: AsyncEngine, *items: FAPriceQueryItem) -> list[FAPriceQueryResult]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await PriceQueryOperations.get_prices_bulk(list(items), session)


def _item(asset_id: int, start: date, end: date | None, **extra: Any) -> FAPriceQueryItem:
    return FAPriceQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=start, end=end), **extra)


def _dump(results: Iterable[FAPriceQueryResult]) -> list[dict]:
    """The results as JSON, less the one field that names the moment of the call: a risk signal's ``computed_at``."""
    dumped = [result.model_dump(mode="json") for result in results]
    for result in dumped:
        for signal in result["signals"]:
            if signal.get("risk_metadata"):
                signal["risk_metadata"].pop("computed_at")
    return dumped


def _point_counts(results: Iterable[FAPriceQueryResult]) -> list[int]:
    return [len(result.prices) for result in results]


class _NoRows:
    """The answer of ``_StatementCounter``: no row, however it is read."""

    def scalars(self) -> _NoRows:
        return self

    def all(self) -> list:
        return []

    def first(self) -> None:
        return None


class _StatementCounter:
    """Stands in for the route's session: answers every statement with no row, and counts them."""

    def __init__(self) -> None:
        self.statements = 0

    async def execute(self, *_args: Any, **_kwargs: Any) -> _NoRows:
        self.statements += 1
        return _NoRows()


async def _query_route(session: Any, items: list[FAPriceQueryItem]) -> FAPriceQueryResponse:
    return await prices.query_prices_bulk(requests=items, session=session, _current_user=None)


# =============================================================================
# CONVERSIONS: THE HANDLER, CALLED DIRECTLY WITH A RECORDING CONVERTER
# =============================================================================


class _Converter:
    """In-process ``convert_bulk``: a rate on every day for every pair, an identity for a currency to itself; records
    every call and every item it is handed."""

    def __init__(self) -> None:
        self.calls = 0
        self.handed: list[date] = []

    async def __call__(self, _session: Any, conversions: list, raise_on_error: bool = True) -> tuple[list, list[str]]:
        self.calls += 1
        results = []
        for amount, to_currency, on_day in conversions:
            self.handed.append(on_day)
            rate = Decimal(1) if amount.code == to_currency else Decimal("1.1") + Decimal(on_day.toordinal() % 7) / 100
            results.append((Currency(code=to_currency, amount=amount.amount * rate), on_day, False))
        return results, []

    def said(self) -> str:
        return f"; convert_bulk was handed {len(self.handed):,} items in {self.calls} call(s)"


def _conversion(amount: str, start: date, end: date | None, *, signals: Iterable[SignalRequest] = ()) -> FXConversionRequest:
    return FXConversionRequest(from_amount=Currency(code="EUR", amount=Decimal(amount)), to_currency="USD", date_range=DateRangeModel(start=start, end=end), signals=list(signals))


async def _convert(monkeypatch: pytest.MonkeyPatch, converter: _Converter, *conversions: FXConversionRequest) -> FXConvertResponse:
    monkeypatch.setattr(currencies, "convert_bulk", converter)
    return await currencies.convert_currency_bulk(request=list(conversions), session=None, _current_user=None)


# =============================================================================
# BL-001 / BL-002 — THE NUMBERS, THE ERROR, WHERE THE BUDGET IS READ
# =============================================================================


def test_bl001_constants_and_error():
    """BL-001: ``date_range_limits`` holds ``MAX_BULK_ITEMS = 1_000``, ``MAX_BULK_ITEM_DAYS = 5_000_000`` and
    ``BulkTooManyDaysError``, an ``Exception`` built with ``item_days`` and ``max_item_days`` and carrying both.

    Red before Z-25: none of the three existed.
    """
    assert getattr(date_range_limits, "MAX_BULK_ITEMS", None) == MAX_ITEMS
    assert getattr(date_range_limits, "MAX_BULK_ITEM_DAYS", None) == MAX_ITEM_DAYS
    error_class = getattr(date_range_limits, "BulkTooManyDaysError", None)
    assert isinstance(error_class, type) and issubclass(error_class, Exception), f"BulkTooManyDaysError: {error_class!r}"
    error = error_class(item_days=MAX_ITEM_DAYS + 7, max_item_days=MAX_ITEM_DAYS)
    assert (error.item_days, error.max_item_days) == (MAX_ITEM_DAYS + 7, MAX_ITEM_DAYS)


def test_bl002_budget_read_by_name_where_applied():
    """BL-002: ``price_query`` and ``currencies`` read ``date_range_limits.MAX_BULK_ITEM_DAYS`` itself, imported by name.

    A name imported by value is the one a test lowers; a consumer reading the budget some other way would apply the real
    5 million where every case here believes it lowered it. Red before Z-25: neither module read a budget.
    """
    budget = getattr(date_range_limits, "MAX_BULK_ITEM_DAYS", None)
    assert budget is not None, "date_range_limits has no MAX_BULK_ITEM_DAYS"
    for name in BUDGET_CONSUMERS:
        module = importlib.import_module(name)
        assert hasattr(module, "MAX_BULK_ITEM_DAYS"), f"{name} does not import MAX_BULK_ITEM_DAYS by name"
        assert module.MAX_BULK_ITEM_DAYS is budget, f"{name} reads a MAX_BULK_ITEM_DAYS of its own"


# =============================================================================
# BL-I — THE ITEMS PER REQUEST, BOTH ROUTES
# =============================================================================


@pytest.mark.asyncio
async def test_bli01_price_query_over_1000_items_refused_before_any_read():
    """BL-I01: ``POST /assets/prices/query`` with 1 001 one-day items answers 422 ``bulk_too_many_items``, ``max_items``
    1 000, ``items`` 1 001 — and its session never ran a statement.

    Red before Z-25: the 1 001 items were queried (200, 1 001 empty items, the statements read).
    """
    session = _StatementCounter()
    items = [_item(1, FROZEN_TODAY, FROZEN_TODAY) for _ in range(MAX_ITEMS + 1)]

    refused = await _refusal(lambda: _query_route(session, items), also=lambda: f"; {session.statements} statement(s) read")

    detail = _coded_detail(refused, "bulk_too_many_items")
    assert _numbers(detail) == {"max_items": MAX_ITEMS, "items": MAX_ITEMS + 1}
    assert session.statements == 0, f"{session.statements} statement(s) read before the refusal"


@pytest.mark.asyncio
async def test_bli02_conversion_over_1000_items_refused_before_any_conversion(monkeypatch):
    """BL-I02: ``POST /fx/currencies/convert`` with 1 001 one-day conversions answers 422 ``bulk_too_many_items``,
    ``max_items`` 1 000, ``items`` 1 001 — and ``convert_bulk`` is never called.

    Red before Z-25: the 1 001 conversions were made (200, 1 001 results).
    """
    converter = _Converter()
    conversions = [_conversion("100", FROZEN_TODAY, FROZEN_TODAY) for _ in range(MAX_ITEMS + 1)]

    refused = await _refusal(lambda: _convert(monkeypatch, converter, *conversions), also=converter.said)

    detail = _coded_detail(refused, "bulk_too_many_items")
    assert _numbers(detail) == {"max_items": MAX_ITEMS, "items": MAX_ITEMS + 1}
    assert converter.calls == 0, converter.said()


@pytest.mark.asyncio
async def test_bli03_items_checked_before_any_day_is_built(monkeypatch, frozen_ceiling):
    """BL-I03 (guard): 1 001 conversions of 100 years each — 36.5 million item-days — answer ``bulk_too_many_items``,
    not ``bulk_too_many_days``: the items are checked first, before a day is counted or built. Within ``GUARD_SECONDS``,
    and not one day-step taken by the handler (a fuse on its ``timedelta`` stops a day-by-day expansion).

    Red before Z-25: the handler expanded the conversions day by day; the fuse stopped it after ``FUSE_DAY_STEPS``.
    """
    fuse = _install_fuse(monkeypatch, currencies)
    converter = _Converter()
    conversions = [_conversion("100", date(1800, 1, 1), FROZEN_TODAY) for _ in range(MAX_ITEMS + 1)]

    refused = await _within_guard(lambda: _refusal(lambda: _convert(monkeypatch, converter, *conversions), also=converter.said))

    detail = _coded_detail(refused, "bulk_too_many_items")
    assert _numbers(detail) == {"max_items": MAX_ITEMS, "items": MAX_ITEMS + 1}
    assert (converter.calls, fuse.calls) == (0, 0), f"{fuse.calls:,} day-steps taken{converter.said()}"


@pytest.mark.asyncio
async def test_bli04_exactly_1000_items_pass(monkeypatch):
    """BL-I04: exactly 1 000 items pass the item check on both routes: 1 000 price results, 1 000 conversions.

    Green before Z-25 too: it pins the edge the cap must keep open.
    """
    session = _StatementCounter()
    response = await _query_route(session, [_item(1, FROZEN_TODAY, FROZEN_TODAY) for _ in range(MAX_ITEMS)])
    assert len(response.items) == MAX_ITEMS
    assert session.statements > 0, "the 1 000 items were never read"

    converter = _Converter()
    converted = await _convert(monkeypatch, converter, *[_conversion("100", FROZEN_TODAY, FROZEN_TODAY) for _ in range(MAX_ITEMS)])
    assert len(converted.results) == MAX_ITEMS
    assert len(converter.handed) == MAX_ITEMS


# =============================================================================
# BL-A — THE ITEM-DAYS OF A PRICE QUERY (get_prices_bulk, on a private database)
# =============================================================================


async def _seeded_and_from_first_price(engine: AsyncEngine) -> tuple[list[FAPriceQueryItem], list[int]]:
    """Two items and the span each one's fill emits.

    - today-59 … today, a seed on today-400 (no price on the range's first day): filled from the range's start, 60 days;
    - today-100 … today, the first price on today-40 and none before: filled from that price, 41 days.
    """
    seeded = await _asset(engine, prices_on=[_day(-400), *_days(_day(-10), _day(-1))])
    from_first = await _asset(engine, prices_on=_days(_day(-40), _day(-1)))
    return [_item(seeded, _day(-59), _day(0)), _item(from_first, _day(-100), _day(0))], [60, 41]


@pytest.mark.asyncio
async def test_bla01_total_over_the_budget_raises_with_the_exact_total(private_db, frozen_ceiling, lower_budget):
    """BL-A01: two items whose fills emit 60 days (from the range's start, with a seed) and 41 days (from the first
    price) — 101 item-days — under a budget of 100: ``BulkTooManyDaysError`` with ``item_days`` 101 and
    ``max_item_days`` 100.

    101 is the span the fill emits, not the span asked (161) nor the prices stored in the ranges (50).
    Red before Z-25: no error; both series were built.
    """
    items, spans = await _seeded_and_from_first_price(private_db)
    lower_budget(sum(spans) - 1)

    error = await _refused_for_days(lambda: _query(private_db, *items))

    assert (error.item_days, error.max_item_days) == (sum(spans), sum(spans) - 1)


@pytest.mark.asyncio
async def test_bla02_total_at_the_budget_is_unchanged(private_db, frozen_ceiling, lower_budget):
    """BL-A02: the same two items under a budget of exactly 101 give what they give under the real budget — the 60 and
    41 points the fill emits — so the count is the fill's own span, and a total equal to the budget passes.

    Green before Z-25 too: it pins the output the budget must leave alone.
    """
    items, spans = await _seeded_and_from_first_price(private_db)
    reference = await _query(private_db, *items)
    assert _point_counts(reference) == spans

    lower_budget(sum(spans))
    assert _dump(await _query(private_db, *items)) == _dump(reference)


@pytest.mark.asyncio
async def test_bla03_full_history_signal_counts_its_load_range(private_db, frozen_ceiling, lower_budget, no_market_holidays):
    """BL-A03: ONE visible day with a full-history signal (``RISK_DRAWDOWN``), the first stored price 300 days back:
    the fill emits from that price, 301 days, and they count. Under a budget of 301 the item gives what it gives under
    the real budget; under 300, ``BulkTooManyDaysError`` with ``item_days`` 301 — while the same day without the signal
    costs 1 and passes.

    The warm-up loads from ``date.min``: counting the visible range would let one day carry any history.
    Red before Z-25: no error; the 301 days were filled for one visible point.
    """
    asset_id = await _asset(private_db, prices_on=[_day(-300), _day(-150), _day(-1)])
    one_day_with_history = _item(asset_id, _day(0), _day(0), signals=[DRAWDOWN])
    reference = await _query(private_db, one_day_with_history)
    lower_budget(301)
    assert _dump(await _query(private_db, one_day_with_history)) == _dump(reference)
    lower_budget(300)
    (plain,) = await _query(private_db, _item(asset_id, _day(0), _day(0)))
    assert [point.date for point in plain.prices] == [_day(0)]

    error = await _refused_for_days(lambda: _query(private_db, one_day_with_history))

    assert (error.item_days, error.max_item_days) == (301, 300)


@pytest.mark.asyncio
async def test_bla04_an_item_that_emits_nothing_counts_zero_never_less(private_db, frozen_ceiling, lower_budget):
    """BL-A04: five items — ten years of an asset without any price; an asset's range that ends before its first price
    (prices today-5 … today-1, asked today-100 … today-50: neither data nor seed in it); that asset from the day after
    the ceiling to 9999-12-31; that asset over today-10 … today-1 (5 days from its first price); another asset over 60
    days of prices. Their fills emit 0, 0, 0, 5 and 60 days: 65 item-days.

    Under a budget of 65 the five give what they give under the real budget. Under 64, ``item_days`` 65 exactly: an
    empty item counted at its asked span would say more, and the item ending before its first price counted as
    ``end - first + 1`` (-44) would say less — and let the 65 through.
    Red before Z-25: no error; the 65 points were built.
    """
    empty = await _asset(private_db)
    late = await _asset(private_db, prices_on=_days(_day(-5), _day(-1)))
    full = await _asset(private_db, prices_on=_days(_day(-60), _day(-1)))
    items = [
        _item(empty, _day(-3650), _day(-1)),
        _item(late, _day(-100), _day(-50)),
        _item(late, CEILING + timedelta(days=1), LAST_DAY),
        _item(late, _day(-10), _day(-1)),
        _item(full, _day(-60), _day(-1)),
    ]
    reference = await _query(private_db, *items)
    assert _point_counts(reference) == [0, 0, 0, 5, 60]
    lower_budget(65)
    assert _dump(await _query(private_db, *items)) == _dump(reference)
    lower_budget(64)

    error = await _refused_for_days(lambda: _query(private_db, *items))

    assert (error.item_days, error.max_item_days) == (65, 64)


@pytest.mark.asyncio
@pytest.mark.parametrize(("comparison", "total"), [pytest.param("other", 16, id="comparison-asset"), pytest.param("self", 10, id="self-comparison")])
async def test_bla05_comparison_series_count(private_db, frozen_ceiling, lower_budget, no_market_holidays, comparison, total):
    """BL-A05: a rolling beta on prices today-10 … today-1 against a comparison asset priced today-6 … today-1: the
    comparison gets a fill of its own, 6 days, and it counts with the item's 10 — 16 item-days. Against the asset itself
    there is no second fill, and nothing is counted twice: 10. Under a budget equal to the total the item gives what it
    gives under the real budget; one day less, ``BulkTooManyDaysError`` with ``item_days`` the total.

    Red before Z-25: no error; the series were built.
    """
    primary = await _asset(private_db, prices_on=_days(_day(-10), _day(-1)))
    comparison_id = await _asset(private_db, prices_on=_days(_day(-6), _day(-1))) if comparison == "other" else primary
    beta = SignalRequest(instance_id="beta", signal_code="RISK_ROLLING_BETA", params={"window": 2, "comparison_asset_id": comparison_id})
    item = _item(primary, _day(-10), _day(-1), signals=[beta])
    reference = await _query(private_db, item)
    lower_budget(total)
    assert _dump(await _query(private_db, item)) == _dump(reference)
    lower_budget(total - 1)

    error = await _refused_for_days(lambda: _query(private_db, item))

    assert (error.item_days, error.max_item_days) == (total, total - 1)


@pytest.mark.asyncio
async def test_bla06_guard_real_budget_refused_before_the_fill(private_db, monkeypatch, frozen_ceiling, no_market_holidays):
    """BL-A06 (guard, the real budget): 200 items of ONE visible day each, with a full-history drawdown, on an asset
    whose first price is 36 524 days back: each fill would emit 36 525 days, 7 305 000 in all.
    ``BulkTooManyDaysError`` with ``item_days`` 7 305 000 and ``max_item_days`` 5 000 000, within ``GUARD_SECONDS``,
    the fill never started (the fuse on ``price_query.timedelta`` stops a fill past ``FUSE_DAY_STEPS`` days).

    Red before Z-25: the fill ran — 7.3 million points for 200 visible ones; the fuse stopped it first.
    """
    asset_id = await _asset(private_db, prices_on=[_day(1 - HUNDRED_YEARS), _day(-1)])
    items = [_item(asset_id, _day(0), _day(0), signals=[DRAWDOWN]) for _ in range(200)]
    _install_fuse(monkeypatch, price_query)

    error = await _within_guard(lambda: _refused_for_days(lambda: _query(private_db, *items)))

    assert (error.item_days, error.max_item_days) == (200 * HUNDRED_YEARS, MAX_ITEM_DAYS)


@pytest.mark.asyncio
async def test_bla07_price_route_answers_422_bulk_too_many_days(private_db, frozen_ceiling, lower_budget):
    """BL-A07: the price route turns the error into 422 ``bulk_too_many_days``: BL-A01's two items under a budget of
    100 give ``max_item_days`` 100 and ``item_days`` 101 — not a 500, not a silent half answer.

    Red before Z-25: 200, both series served.
    """
    items, spans = await _seeded_and_from_first_price(private_db)
    lower_budget(sum(spans) - 1)

    async with AsyncSession(private_db, expire_on_commit=False) as session:
        refused = await _refusal(lambda: _query_route(session, items))

    detail = _coded_detail(refused, "bulk_too_many_days")
    assert _numbers(detail) == {"max_item_days": sum(spans) - 1, "item_days": sum(spans)}


# =============================================================================
# BL-F — THE ITEM-DAYS OF A CONVERSION (the handler, called directly)
# =============================================================================


@pytest.mark.asyncio
async def test_blf01_daily_items_over_the_budget(monkeypatch, frozen_ceiling, lower_budget):
    """BL-F01: three conversions of 60, 41 and 60 days. Under a budget of 161 they give what they give under the real
    budget; under 100, 422 ``bulk_too_many_days`` with ``item_days`` 101 — the count when the second conversion crossed
    the budget, not the 161 of all three — and ``convert_bulk`` never called.

    Red before Z-25: the 161 daily conversions were made.
    """
    conversions = [_conversion("100", _day(-59), _day(0)), _conversion("200", _day(-40), _day(0)), _conversion("300", _day(-59), _day(0))]
    reference = await _convert(monkeypatch, _Converter(), *conversions)
    assert len(reference.results) == 161
    lower_budget(161)
    assert (await _convert(monkeypatch, _Converter(), *conversions)).model_dump(mode="json") == reference.model_dump(mode="json")
    lower_budget(100)
    converter = _Converter()

    refused = await _refusal(lambda: _convert(monkeypatch, converter, *conversions), also=converter.said)

    detail = _coded_detail(refused, "bulk_too_many_days")
    assert _numbers(detail) == {"max_item_days": 100, "item_days": 101}
    assert converter.calls == 0, converter.said()


@pytest.mark.asyncio
async def test_blf02_signal_warmup_is_counted(monkeypatch, frozen_ceiling, lower_budget):
    """BL-F02: 30 days with an SMA(3) build 30 daily items and the signal's, from its warm-up start: N items in all, as
    many as ``convert_bulk`` is handed. Under a budget of N the same answer as under the real budget; under N - 1 —
    room for the daily and the visible signal items, not for the warm-up — 422 ``bulk_too_many_days`` with
    ``item_days`` N, nothing converted.

    Red before Z-25: the N items were converted.
    """
    conversion = _conversion("100", _day(-29), _day(0), signals=[SMA3])
    counted = _Converter()
    reference = await _convert(monkeypatch, counted, conversion)
    built = len(counted.handed)
    assert built > 2 * 30, f"{built} items: the SMA(3) has no warm-up to count"
    lower_budget(built)
    assert (await _convert(monkeypatch, _Converter(), conversion)).model_dump(mode="json") == reference.model_dump(mode="json")
    lower_budget(built - 1)
    converter = _Converter()

    refused = await _refusal(lambda: _convert(monkeypatch, converter, conversion), also=converter.said)

    detail = _coded_detail(refused, "bulk_too_many_days")
    assert _numbers(detail) == {"max_item_days": built - 1, "item_days": built}
    assert converter.calls == 0, converter.said()


@pytest.mark.asyncio
async def test_blf03_conversion_after_the_ceiling_counts_zero(monkeypatch, frozen_ceiling, lower_budget):
    """BL-F03: a conversion wholly after the ceiling, up to 9999-12-31 and with a signal, then one of 11 days. Under a
    budget of 11 the two give what they give under the real budget: 11 results, and the first one's signal result on
    an empty series. Under 10, ``item_days`` 11 — the first builds nothing, its signals included, and counts nothing.

    Red before Z-25: the 11 conversions were made under any budget.
    """
    after_ceiling = _conversion("100", CEILING + timedelta(days=1), LAST_DAY, signals=[SMA3])
    eleven_days = _conversion("200", _day(-10), _day(0))
    reference = await _convert(monkeypatch, _Converter(), after_ceiling, eleven_days)
    assert (len(reference.results), [result.request_index for result in reference.signal_results]) == (11, [0])
    lower_budget(11)
    assert (await _convert(monkeypatch, _Converter(), after_ceiling, eleven_days)).model_dump(mode="json") == reference.model_dump(mode="json")
    lower_budget(10)
    converter = _Converter()

    refused = await _refusal(lambda: _convert(monkeypatch, converter, after_ceiling, eleven_days), also=converter.said)

    detail = _coded_detail(refused, "bulk_too_many_days")
    assert _numbers(detail) == {"max_item_days": 10, "item_days": 11}
    assert converter.calls == 0, converter.said()

"""R13-SEC9-1, -3, -4 (security review by E; lands with X-R59) — ``POST /assets/prices/current``: one fetch per distinct
asset, 1 000 ids at most, a ``range_start`` up to tomorrow, and no 500 that echoes its error.

The defects, on HEAD f252acb4a:

- SEC9-1 (MEDIUM, DoS). The route took any number of ids — E measured 8 000 copies of one id: 7.9 s and +382 MB — and
  ``PriceQueryOperations.get_current_prices_bulk`` fetched every requested id, duplicates included. ``_live_quote_item``
  read the 2-minute current-value cache (``core._asset_current_cache``) only BEFORE waiting for its provider slot (the
  call's semaphore), so the lookups of one cache key that waited behind the first all missed it: N lookups, N provider
  calls — duplicates of one id, and distinct assets sharing a provider identifier and parameters alike. The write-back of
  today's row then added one row per requested id: a repeated id broke the commit (UNIQUE asset_id + date), and the
  rollback lost today's row of EVERY asset of the call. The whole-range change (``live_range_changes``, X-R59) was
  computed for every requested id.
- SEC9-3. A failure of ``POST /prices/query`` or ``POST /prices/current`` answered 500 with ``detail=str(e)``: an SQL
  error echoed its statement, naming the schema.
- SEC9-4. ``range_start`` was refused before 1900-01-01 only: any later day, 9999-12-31 included, was accepted.

The cure's contract, pinned here:

1. The route refuses more than ``MAX_BULK_ITEMS`` (1 000) ids — counted as sent, duplicates included — with 422
   ``{"code": "bulk_too_many_items", "message", "max_items": 1000, "items": n}`` before any read: the service is never
   called. Exactly 1 000 pass.
2. The service fetches once per distinct id and writes today's row back once per distinct id; it answers one item per
   requested id, in request order, a repeated id getting the same item.
3. ``_live_quote_item`` reads the cache again once the slot is its own: lookups of one key waiting behind the first make
   ONE provider call. Lookups of distinct keys each make their own (guard).
4. The route computes the whole-range change once per distinct id; every item carries its id's change.
5. ``range_start`` is bounded by its PARAMETER (X's review, point 4: ``Annotated[…, Query(…),
   AfterValidator(_range_start_in_bounds)]``): outside ``EARLIEST_RANGE_START`` (1900-01-01) … ``latest_range_end()``
   (tomorrow, by the server's calendar) the request is refused by FastAPI's own validation — 422 in the standard shape,
   ``detail`` a list whose error has ``loc`` ``["query", "range_start"]`` and ``type`` ``value_error`` — before the route
   body runs, so before the item cap too; both ends are accepted.
6. A failure of either route answers 500 with a detail that does not echo the error; the error is logged, with its
   exception.
7. Guard (X's review, point 1 — the try/except entered with X-R59): when the whole-range change fails, the quotes still
   stand — every value, the success count — and every ``range_change`` is the empty one, its three fields null.
8. Y's D1: ``target_currency`` (an ISO 4217 code, normalized — ``usd`` → ``USD`` —, refused otherwise by its parameter:
   422 at ``["query", "target_currency"]``) is handed to ``live_range_changes`` with ``range_start``; the quotes stay in
   their own currency; without ``range_start`` it changes nothing. What the service does with it is
   ``test_period_changes.py::TestLiveRangeChange``'s.

Three ways in. The SERVICE (2, 3) runs ``AssetSourceManager.get_current_prices_bulk`` on a private in-memory SQLite
database (``SQLModel.metadata.create_all``), the provider a double of the test's own code behind
``core.configured_provider`` (``_Quotes``): not a plugin, so the real ``core.call_provider`` runs it in a thread of its own,
as it runs a plugin — the lookups started meanwhile miss the cache, as in production. The current-value cache is a
private one for the test (``core._asset_current_cache`` replaced, nothing of the process's cleared or shared), and the
service's today is frozen at ``TODAY``, the day the double's quotes are dated. The slot test does not infer that its
lookups waited for the slot, it verifies it: ``_SlotWatch`` wraps the semaphore the service hands ``_live_quote_item`` and
counts the lookups asking for it, and the double answers only once both have (a ``threading.Event``, waited in the
double's own thread with a deadline; a deadline passed fails the test as an unmet precondition). The ROUTE BODY (1, 4, 6,
7) is called directly, its service and ``live_range_changes`` replaced by recorders (``monkeypatch``), its session a
stand-in that counts statements and reads nothing. The REQUEST (5, 8) — a parameter's validation runs only when FastAPI
handles a request — goes through the price router mounted on a fresh ``FastAPI`` app of the test's own, served in this
process by ``httpx.ASGITransport`` (no server, no port), its session and user dependencies overridden; the same
recorders behind it. ``latest_range_end`` is held at the real tomorrow for the test.

Red on HEAD f252acb4a, each for the reason its docstring gives: ``test_sec9_1_a_repeated_id_asks_its_provider_once``,
``test_sec9_1_a_repeated_id_writes_todays_row_once``,
``test_sec9_1_lookups_of_one_cache_key_waiting_for_the_slot_make_one_provider_call``,
``test_sec9_1_more_than_1000_ids_refused_before_any_read``, ``test_sec9_1_the_range_change_is_computed_once_per_distinct_id``,
``test_sec9_4_range_start_after_tomorrow_refused`` (both cases: accepted), ``test_sec9_4_range_start_before_1900_refused``
(both cases: refused, but by the route body, a 422 whose ``detail`` is a string, not the parameter's error),
``test_sec9_4_range_start_is_checked_before_the_item_cap`` (accepted, the ids not capped),
``test_sec9_3_a_failure_answers_500_without_echoing_it`` (both routes), ``test_d1_target_currency_reaches_the_range_change_normalized``
(both cases) and ``test_d1_invalid_target_currency_refused_by_its_parameter`` (both cases): no such parameter, ignored.
Green before and after — what the cure keeps:
``test_sec9_1_guard_lookups_of_distinct_keys_each_ask_their_provider``, ``test_sec9_1_exactly_1000_ids_pass``,
``test_sec9_4_range_start_from_1900_to_tomorrow_accepted``, ``test_xr59_guard_the_quotes_stand_when_the_range_change_fails``,
``test_d1_guard_without_target_currency_the_change_is_native``,
``test_d1_guard_target_currency_without_range_start_changes_nothing``.

Isolation: PURE — no lane database, no server, no network. Every row is written to the test's own in-memory database,
closed and disposed at teardown; the cache, the provider lookup, the service's today, the route's service, change and
ceiling are replaced for the test only (``monkeypatch``); the app the requests reach is built per test and touches the
process's app nowhere.

MF-SEC9c, on HEAD d63558abb: the database fallback of ``get_current_prices_bulk`` read the session from inside the
parallel lookups. ``_fetch_one`` ran per distinct id in ``asyncio.gather`` and, without a live quote (no provider, a
provider that failed, one paused), awaited ``_last_readable_price(session, asset_id)`` there: several tasks on ONE
``AsyncSession`` at once, which SQLAlchemy does not support (sporadic «This session is provisioning a new connection;
concurrent operations are not permitted», ``IllegalStateChangeError``, or interleaved results) — and one paged read per
asset. The cure's contract, pinned here:

- The lookups never use the session: no statement of the session starts while another one is in flight.
- The fallbacks are ONE grouped read of the latest row of every asset left without a live quote, once the lookups are
  in; an asset whose latest close does not read (±inf, W-B62) is then looked up alone, older rows a page at a time —
  that asset, and no other, by itself.
- Guards, what the cure keeps: the latest close that reads a number is served, however deep under unreadable ones; an
  asset with none, or with no row, answers "No price data available"; an unknown id "Asset not found"; the fallback of a
  paused provider carries ``RATE_LIMITED`` and its ``retry_after``, the one of a failed provider neither; live quotes
  and fallbacks come back in request order, a repeated id asked of its provider once.

The way in is the service's, on the private database, through ``_WatchedSession``: the session itself, watching its own
statements — how many are in flight at once, and which assets each statement on ``price_history`` reads. Each statement
yields to the event loop once before it runs, as a driver handing it to a thread of its own does: a task ready to run
meanwhile runs, so an overlap the code allows is an overlap observed, whatever the driver's timing. An unreadable close is
written as ``test_current_price_storable.py`` writes it: raw SQL over a row the ORM wrote (``9e999``, a REAL +inf),
checked as the file holds it.

Red on HEAD d63558abb, each for the reason its docstring gives: ``test_mf_sec9c_the_session_is_never_used_concurrently``
and ``test_mf_sec9c_the_fallbacks_are_one_grouped_read``. Green before and after:
``test_mf_sec9c_guard_the_latest_close_that_reads_is_served``,
``test_mf_sec9c_guard_a_paused_provider_falls_back_with_its_refusal``,
``test_mf_sec9c_guard_live_quotes_and_fallbacks_in_request_order``.

Reference: backend/app/api/v1/assets/prices.py (query_prices_bulk, get_current_prices_bulk),
backend/app/services/assets/price_query.py (_live_quote_item, _last_readable_prices,
PriceQueryOperations.get_current_prices_bulk).
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import threading
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from sqlalchemy import TableClause, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import BinaryExpression, BindParameter

from backend.app.api.v1.assets import prices
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import FACurrentPriceItem, FACurrentPriceResponse, FACurrentValue, FAPriceQueryItem, FARangeChange
from backend.app.services.assets import core, price_query
from backend.app.services.assets.base import AssetRateLimitedError
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.utils.runtime.cache import NamedCache
from backend.test_scripts.test_utils import print_section, print_success

MAX_ITEMS = 1_000  # the contract's number, written here and not read from the module under test
EARLIEST = date(1900, 1, 1)  # EARLIEST_RANGE_START, written here as well
TODAY = date(2025, 6, 18)  # the service's today, frozen; any day would do
GATE_SECONDS = 5.0  # how long the double waits for the lookups to reach the slot: below the 10 s call_provider allows it
#: What the failing service raises in the SEC9-3 cases: an SQL error names the schema.
LEAK = "SELECT secret_column FROM secret_table"


# =============================================================================
# THE SERVICE: A PRIVATE DATABASE, A PROVIDER DOUBLE, A PRIVATE CACHE
# =============================================================================


@contextlib.asynccontextmanager
async def _private_session(session_class: type[AsyncSession] = AsyncSession) -> AsyncIterator[AsyncSession]:
    """A session of ``session_class`` on the test's own in-memory database with the ORM schema: never the lane's
    database. Closed, and its engine disposed, on the way out."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with session_class(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    async with _private_session() as private_session:
        yield private_session


class _FrozenDate(date):
    """``date`` for the service's write-back, its today held at ``TODAY``."""

    @classmethod
    def today(cls) -> date:
        return TODAY


class _Quotes:
    """The provider double, behind ``core.configured_provider`` for the test's own code: each identifier's quote, in EUR,
    as of ``TODAY``; every call counted per identifier. An identifier of ``raises`` raises, instead of answering, the error
    its factory builds: a provider that fails, or one paused (``AssetRateLimitedError``, as ``core.call_provider`` raises
    it for a paused plugin). Not a plugin (no settings, no pause): ``core.call_provider`` runs it in a thread of its own,
    as it runs a plugin. With a ``gate`` it answers only once the gate is open, waiting in that thread, ``GATE_SECONDS``
    at most: a wait that ran out is counted, and fails the test as an unmet precondition."""

    def __init__(self, code: str) -> None:
        self.code = code
        self.quotes: dict[str, Decimal] = {}
        self.raises: dict[str, Callable[[], Exception]] = {}
        self.calls: Counter[str] = Counter()
        self.gate: threading.Event | None = None
        self.gate_missed = 0
        self._lock = threading.Lock()

    async def get_current_value(self, identifier, identifier_type, provider_params=None) -> FACurrentValue:
        with self._lock:
            self.calls[identifier] += 1
        if self.gate is not None and not self.gate.wait(GATE_SECONDS):
            with self._lock:
                self.gate_missed += 1
        if identifier in self.raises:
            raise self.raises[identifier]()
        return FACurrentValue(value=self.quotes[identifier], currency="EUR", as_of_date=TODAY, source=self.code)


@pytest.fixture
def quotes(monkeypatch: pytest.MonkeyPatch) -> _Quotes:
    """A ``_Quotes`` of a code of the test's own, the one provider ``core.configured_provider`` hands out; a private
    current-value cache; the service's today frozen at ``TODAY``. All undone at teardown."""
    double = _Quotes(f"sec9_{uuid.uuid4().hex[:10]}")

    async def configured_provider(code: str, *, user_id: int | None = None):
        return double if code == double.code else None

    monkeypatch.setattr(core, "configured_provider", configured_provider)
    monkeypatch.setattr(core, "_asset_current_cache", NamedCache(name=f"{double.code}_current", maxsize=300, ttl=120))
    monkeypatch.setattr(price_query, "date_type", _FrozenDate)
    return double


class _WatchedSlot:
    """The provider slot (the call's semaphore) as ``_live_quote_item`` uses it, counting the lookups that ask for it."""

    def __init__(self, semaphore, watch: _SlotWatch) -> None:
        self._semaphore = semaphore
        self._watch = watch

    async def __aenter__(self) -> None:
        self._watch.asked += 1
        if self._watch.asked >= self._watch.expected:
            self._watch.everyone_asked.set()
        await self._semaphore.acquire()

    async def __aexit__(self, *exc_info: object) -> None:
        self._semaphore.release()


class _SlotWatch:
    """Wraps the semaphore ``get_current_prices_bulk`` hands ``_live_quote_item``: ``everyone_asked`` opens once
    ``expected`` lookups have asked for the slot — the gate of the double, so the first call answers only when the others
    are waiting behind it."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, expected: int) -> None:
        self.expected = expected
        self.asked = 0
        self.everyone_asked = threading.Event()
        original = price_query._live_quote_item

        def watched(asset_id, assignment, semaphore):
            return original(asset_id, assignment, _WatchedSlot(semaphore, self))

        monkeypatch.setattr(price_query, "_live_quote_item", watched)


async def _assigned_asset(session: AsyncSession, double: _Quotes, identifier: str) -> int:
    """An asset of the private database, assigned to the double under ``identifier`` (a TICKER, no parameters)."""
    asset = Asset(display_name=f"SEC9-1 {identifier} {uuid.uuid4().hex[:6]}", currency="EUR", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=double.code, identifier=identifier, identifier_type=ProviderInputType.TICKER))
    await session.commit()
    return asset.id


async def _current(session: AsyncSession, asset_ids: list[int], **kwargs: Any) -> list[FACurrentPriceItem]:
    return await AssetSourceManager.get_current_prices_bulk(asset_ids, session, **kwargs)


async def _closes_today(session: AsyncSession, asset_ids: list[int]) -> dict[int, list[Decimal]]:
    """Every close stored on ``TODAY`` for each of ``asset_ids`` (an asset without a row is left out)."""
    rows = (await session.execute(select(PriceHistory.asset_id, PriceHistory.close).where(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date == TODAY).order_by(PriceHistory.id))).all()
    closes: dict[int, list[Decimal]] = {}
    for asset_id, close in rows:
        closes.setdefault(asset_id, []).append(close)
    return closes


# =============================================================================
# SEC9-1 — THE SERVICE: ONE FETCH, ONE WRITE-BACK PER DISTINCT ID; THE CACHE READ AGAIN AFTER THE SLOT
# =============================================================================


@pytest.mark.asyncio
async def test_sec9_1_a_repeated_id_asks_its_provider_once(session, quotes):
    """``[a, a, b, a]``: the provider is asked once for a and once for b; the answer holds 4 items in request order, the
    three of a equal, each with its asset's quote from the provider.

    Red on HEAD f252acb4a: a's three lookups all start before the first answer, all miss the cache: a asked 3 times.
    """
    print_section("R13-SEC9-1: a repeated id, one provider call")
    a = await _assigned_asset(session, quotes, "SEC9A")
    b = await _assigned_asset(session, quotes, "SEC9B")
    quotes.quotes.update(SEC9A=Decimal("101.5"), SEC9B=Decimal("42"))
    requested = [a, a, b, a]

    items = await _current(session, requested)

    assert dict(quotes.calls) == {"SEC9A": 1, "SEC9B": 1}, f"provider calls per identifier: {dict(quotes.calls)}"
    assert [item.asset_id for item in items] == requested
    assert [(item.value, item.currency, item.as_of_date, item.source) for item in items] == [(quotes.quotes[identifier], "EUR", TODAY, f"provider:{quotes.code}") for identifier in ("SEC9A", "SEC9A", "SEC9B", "SEC9A")]
    assert items[0].model_dump() == items[1].model_dump() == items[3].model_dump()
    print_success(f"{len(requested)} items in request order, {sum(quotes.calls.values())} provider calls")


@pytest.mark.asyncio
async def test_sec9_1_a_repeated_id_writes_todays_row_once(session, quotes):
    """``[a, a, b, a]``: exactly one row on ``TODAY`` for a and one for b, each holding its quote; nothing raised.

    Red on HEAD f252acb4a: one row was added per requested id; the three of a broke the commit (UNIQUE asset_id + date),
    and the rollback lost b's row too: no row at all.
    """
    print_section("R13-SEC9-1: a repeated id, one row written back")
    a = await _assigned_asset(session, quotes, "SEC9A")
    b = await _assigned_asset(session, quotes, "SEC9B")
    quotes.quotes.update(SEC9A=Decimal("101.5"), SEC9B=Decimal("42"))

    await _current(session, [a, a, b, a])

    closes = await _closes_today(session, [a, b])
    assert closes == {a: [Decimal("101.5")], b: [Decimal("42")]}, f"closes stored on {TODAY} (a={a}, b={b}): {closes}"
    print_success("one row on today per asset, with its quote")


@pytest.mark.asyncio
async def test_sec9_1_lookups_of_one_cache_key_waiting_for_the_slot_make_one_provider_call(session, quotes, monkeypatch):
    """Two DISTINCT assets assigned to the same provider, identifier and parameters — one cache key —, one provider slot
    (``concurrency=1``): the second lookup waits for the slot while the first is at the provider (verified: the double
    answers only once both asked for it), then finds the first one's quote in the cache. ONE provider call; both items
    carry the quote, and both assets get today's row.

    Red on HEAD f252acb4a: the cache was read before the slot only: 2 provider calls.
    """
    print_section("R13-SEC9-1: one cache key, two lookups waiting for the slot, one provider call")
    first = await _assigned_asset(session, quotes, "SEC9SHARED")
    second = await _assigned_asset(session, quotes, "SEC9SHARED")
    quotes.quotes["SEC9SHARED"] = Decimal("77.25")
    watch = _SlotWatch(monkeypatch, expected=2)
    quotes.gate = watch.everyone_asked

    items = await _current(session, [first, second], concurrency=1)

    assert quotes.gate_missed == 0, f"precondition not met: {watch.asked} lookup(s) asked for the slot within {GATE_SECONDS} s, not 2"
    assert quotes.calls["SEC9SHARED"] == 1, f"{quotes.calls['SEC9SHARED']} provider calls for one cache key"
    assert [(item.asset_id, item.value, item.source) for item in items] == [(first, Decimal("77.25"), f"provider:{quotes.code}"), (second, Decimal("77.25"), f"provider:{quotes.code}")]
    closes = await _closes_today(session, [first, second])
    assert closes == {first: [Decimal("77.25")], second: [Decimal("77.25")]}, f"closes stored on {TODAY}: {closes}"
    print_success("2 lookups waited for the slot, 1 provider call, 2 items and 2 rows")


@pytest.mark.asyncio
async def test_sec9_1_guard_lookups_of_distinct_keys_each_ask_their_provider(session, quotes, monkeypatch):
    """Guard: the same scene with two identifiers — two cache keys — makes two provider calls, each asset its own quote.
    The cache read after the slot never lends one key's quote to another.

    Green on HEAD f252acb4a too.
    """
    print_section("R13-SEC9-1 guard: two cache keys, two provider calls")
    first = await _assigned_asset(session, quotes, "SEC9X")
    second = await _assigned_asset(session, quotes, "SEC9Y")
    quotes.quotes.update(SEC9X=Decimal("10"), SEC9Y=Decimal("20"))
    watch = _SlotWatch(monkeypatch, expected=2)
    quotes.gate = watch.everyone_asked

    items = await _current(session, [first, second], concurrency=1)

    assert quotes.gate_missed == 0, f"precondition not met: {watch.asked} lookup(s) asked for the slot within {GATE_SECONDS} s, not 2"
    assert dict(quotes.calls) == {"SEC9X": 1, "SEC9Y": 1}
    assert [(item.asset_id, item.value) for item in items] == [(first, Decimal("10")), (second, Decimal("20"))]
    print_success("2 keys, 2 provider calls, each asset its own quote")


# =============================================================================
# MF-SEC9c — THE SERVICE: THE LOOKUPS NEVER USE THE SESSION; THE FALLBACKS, ONE GROUPED READ
# =============================================================================

RETRY_AFTER = 42.0  # the pause the paused double reports, in seconds
UNREADABLE = "9e999"  # an SQLite literal for a REAL +inf: a close that reads None (W-B58, W-B62)
NO_PRICE = "No price data available"


def _provider_failure() -> Exception:
    return RuntimeError("provoked: the provider failed")


def _provider_paused() -> Exception:
    return AssetRateLimitedError("provoked: paused after too many requests", retry_after=RETRY_AFTER)


def _is_price_history_asset_id(column: Any) -> bool:
    return getattr(column, "name", None) == "asset_id" and getattr(getattr(column, "table", None), "name", None) == PriceHistory.__tablename__


def _price_history_reads(statement: Any) -> frozenset[int] | None:
    """The asset ids a statement on ``price_history`` binds to ``price_history.asset_id`` (``=`` or ``IN``, its subqueries
    included); None for a statement that names no ``price_history`` (a raw ``text()`` names no table)."""
    on_price_history, asset_ids = False, set()
    for element in visitors.iterate(statement):
        if isinstance(element, TableClause) and element.name == PriceHistory.__tablename__:
            on_price_history = True
        elif isinstance(element, BinaryExpression) and isinstance(element.right, BindParameter) and _is_price_history_asset_id(element.left):
            value = element.right.value
            asset_ids.update(value if isinstance(value, (list, tuple)) else (value,))
    return frozenset(asset_ids) if on_price_history else None


class _WatchedSession(AsyncSession):
    """The private database's session, watching its own statements: ``most_in_flight``, the most ``execute`` calls under
    way at once — above 1, a statement started while another was still awaiting its rows, which one ``AsyncSession`` does
    not support —, and ``price_reads``, for each statement on ``price_history`` in order, the asset ids it reads.

    Each statement yields to the event loop once before it runs, as a driver handing it to a thread of its own does: a
    task ready to run meanwhile runs, so an overlap the code allows is an overlap observed, whatever the driver's timing.
    ``watch()`` forgets what was seen: what follows is the call under test."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.watch()

    def watch(self) -> None:
        self.in_flight = 0
        self.most_in_flight = 0
        self.price_reads: list[frozenset[int]] = []

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        reads = _price_history_reads(statement)
        if reads is not None:
            self.price_reads.append(reads)
        self.in_flight += 1
        self.most_in_flight = max(self.most_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)
            return await super().execute(statement, *args, **kwargs)
        finally:
            self.in_flight -= 1


@pytest_asyncio.fixture
async def watched() -> AsyncIterator[_WatchedSession]:
    """This test's own in-memory database, its session a ``_WatchedSession``."""
    async with _private_session(_WatchedSession) as private_session:
        yield private_session


def _day(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


async def _unassigned_asset(session: AsyncSession, label: str) -> int:
    """An asset of the private database without a provider: its current price is always the database's."""
    asset = Asset(display_name=f"MF-SEC9c {label} {uuid.uuid4().hex[:6]}", currency="EUR", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.commit()
    return asset.id


async def _store_closes(session: AsyncSession, asset_id: int, closes: dict[int, str]) -> None:
    """Price rows of ``asset_id`` in EUR, one per day ``days_ago`` before ``TODAY``, each close an SQLite literal written
    with raw SQL over a row the ORM wrote (``UNREADABLE``: as an older release or another tool leaves it), then checked as
    the file holds it. Each row is then dropped from the session's identity map: the service reads the close the file
    holds, not the ORM's copy."""
    for days_ago, literal in closes.items():
        row = PriceHistory(asset_id=asset_id, date=_day(days_ago), close=Decimal("1"), currency="EUR", source_plugin_key="MANUAL")
        session.add(row)
        await session.flush()
        await session.execute(text(f"UPDATE price_history SET close = {literal} WHERE id = :id"), {"id": row.id})
        storage, held = (await session.execute(text("SELECT typeof(close), close FROM price_history WHERE id = :id"), {"id": row.id})).one()
        assert storage in ("integer", "real") and float(held) == float(literal), f"scaffold: the close of {_day(days_ago)} is held as {storage} {held!r}, not {literal}"
        session.expunge(row)
    await session.commit()


Served = tuple[int, Decimal | None, str | None, date | None, str | None, str | None, str | None, float | None]


def _served(items: list[FACurrentPriceItem]) -> list[Served]:
    """Each item as ``(asset_id, value, currency, as_of_date, source, error, error_code, retry_after)``."""
    return [(item.asset_id, item.value, item.currency, item.as_of_date, item.source, item.error, item.error_code, item.retry_after) for item in items]


def _refusal_of(paused: bool) -> tuple[str | None, float | None]:
    return ("RATE_LIMITED", RETRY_AFTER) if paused else (None, None)


def _last_known(asset_id: int, close: str, days_ago: int, *, paused: bool = False) -> Served:
    return (asset_id, Decimal(close), "EUR", _day(days_ago), "db:last_known", None, *_refusal_of(paused))


def _no_price(asset_id: int, *, paused: bool = False) -> Served:
    return (asset_id, None, None, None, None, NO_PRICE, *_refusal_of(paused))


@pytest.mark.asyncio
async def test_mf_sec9c_the_session_is_never_used_concurrently(watched, quotes):
    """20 assets, none with a live quote — 7 without a provider, 7 whose provider fails, 6 whose provider is paused —,
    each with a stored close: no statement of the session ever starts while another is in flight, and every item is its
    asset's stored close (``db:last_known``), the paused ones' with ``RATE_LIMITED`` and the pause's ``retry_after``.

    The double runs in a thread of its own (``core.call_provider``): each lookup that reaches it suspends its task, and
    the lookups interleave with one another and with whatever else runs meanwhile, as in production. Every one of the 13
    asked its provider once (verified).

    Red on HEAD d63558abb: each lookup read its fallback from inside the gather — all 20 statements in flight at once on
    one ``AsyncSession``, the watcher's yield or not (aiosqlite hands each statement to a thread of its own).
    """
    print_section("MF-SEC9c: 20 fallbacks, the session never used by two at once")
    requested: list[int] = []
    expected: list[Served] = []
    asked: dict[str, int] = {}
    for n in range(20):
        kind = ("no-provider", "failing", "paused")[n % 3]
        close, days_ago = f"{100 + n}.5", 1 + n % 4
        if kind == "no-provider":
            asset_id = await _unassigned_asset(watched, f"fallback {n}")
        else:
            identifier = f"SEC9C{n}"
            asset_id = await _assigned_asset(watched, quotes, identifier)
            quotes.raises[identifier] = _provider_paused if kind == "paused" else _provider_failure
            asked[identifier] = 1
        await _store_closes(watched, asset_id, {days_ago: close})
        requested.append(asset_id)
        expected.append(_last_known(asset_id, close, days_ago, paused=kind == "paused"))
    watched.watch()

    items = await _current(watched, requested)

    assert dict(quotes.calls) == asked, f"precondition not met: the lookups with a provider asked it {dict(quotes.calls)}"
    assert watched.most_in_flight == 1, f"{watched.most_in_flight} statements in flight at once on one AsyncSession"
    assert _served(items) == expected
    print_success(f"{len(requested)} fallbacks served, never two statements at once")


@pytest.mark.asyncio
async def test_mf_sec9c_the_fallbacks_are_one_grouped_read(watched, quotes):
    """9 assets without a live quote: 6 whose latest close reads (3 without a provider, 3 whose provider fails), 2 whose
    latest close is +inf over an older one that reads, 1 with no row. The statements on ``price_history`` are ONE that
    reads all 9, then lookups alone of the 2 unreadable — no statement reads a readable or row-less asset by itself.
    Each item is the asset's latest close that reads.

    Red on HEAD d63558abb: one paged read per asset, alone — 6 statements read the 6 readable fallbacks.
    """
    print_section("MF-SEC9c: the fallbacks, one grouped read")
    expected: dict[int, Served] = {}
    readable: list[int] = []
    for n in range(6):
        if n % 2:
            identifier = f"SEC9CR{n}"
            asset_id = await _assigned_asset(watched, quotes, identifier)
            quotes.raises[identifier] = _provider_failure
        else:
            asset_id = await _unassigned_asset(watched, f"readable {n}")
        await _store_closes(watched, asset_id, {3: "1", 1: f"{20 + n}.25"})
        readable.append(asset_id)
        expected[asset_id] = _last_known(asset_id, f"{20 + n}.25", 1)
    unreadable: list[int] = []
    for n in range(2):
        asset_id = await _unassigned_asset(watched, f"unreadable {n}")
        await _store_closes(watched, asset_id, {2: f"{30 + n}.75", 1: UNREADABLE})
        unreadable.append(asset_id)
        expected[asset_id] = _last_known(asset_id, f"{30 + n}.75", 2)
    row_less = await _unassigned_asset(watched, "row-less")
    expected[row_less] = _no_price(row_less)
    requested = [*readable[:3], unreadable[0], row_less, *readable[3:], unreadable[1]]
    watched.watch()

    items = await _current(watched, requested)

    reads = watched.price_reads
    on_readable = [sorted(ids) for ids in reads if ids & set(readable)]
    assert len(on_readable) == 1, f"{len(on_readable)} statements on price_history read the {len(readable)} readable fallbacks (assets {readable}): {on_readable}"
    assert reads[:1] == [frozenset(requested)], f"the first statement on price_history does not read the {len(requested)} fallbacks: {[sorted(ids) for ids in reads]}"
    assert set(reads[1:]) == {frozenset({asset_id}) for asset_id in unreadable}, f"after the grouped read, read alone: {[sorted(ids) for ids in reads[1:]]}; the unreadable: {unreadable}"
    assert _served(items) == [expected[asset_id] for asset_id in requested]
    print_success(f"1 grouped read for {len(requested)} fallbacks, {len(reads) - 1} lookup(s) alone for {len(unreadable)} unreadable")


@pytest.mark.asyncio
async def test_mf_sec9c_guard_the_latest_close_that_reads_is_served(session):
    """Guard: the latest close that reads a number is served — under one unreadable close, under 35 (past the latest row
    and a full page of older ones), or the latest of two that read; an asset whose closes are all ±inf, and one with no
    row, answer "No price data available".

    Green on HEAD d63558abb too.
    """
    print_section("MF-SEC9c guard: the latest close that reads")
    one_over = await _unassigned_asset(session, "one over")
    await _store_closes(session, one_over, {3: "10", 1: UNREADABLE})
    deep = await _unassigned_asset(session, "deep")
    await _store_closes(session, deep, {40: "7.5", **dict.fromkeys(range(1, 36), UNREADABLE)})
    plain = await _unassigned_asset(session, "plain")
    await _store_closes(session, plain, {5: "3", 2: "4"})
    never = await _unassigned_asset(session, "never")
    await _store_closes(session, never, {2: "-" + UNREADABLE, 1: UNREADABLE})
    row_less = await _unassigned_asset(session, "row-less")

    items = await _current(session, [one_over, deep, plain, never, row_less])

    assert _served(items) == [_last_known(one_over, "10", 3), _last_known(deep, "7.5", 40), _last_known(plain, "4", 2), _no_price(never), _no_price(row_less)]
    print_success("the latest readable close of each, or no price")


@pytest.mark.asyncio
async def test_mf_sec9c_guard_a_paused_provider_falls_back_with_its_refusal(session, quotes):
    """Guard: a paused provider's asset falls back to its stored close with ``RATE_LIMITED`` and the pause's
    ``retry_after``, or answers "No price data available" with them; a failed provider's, the same without them.

    Green on HEAD d63558abb too.
    """
    print_section("MF-SEC9c guard: a paused provider's fallback says why")
    assets: dict[str, int] = {}
    for name, failure in (("SEC9CP1", _provider_paused), ("SEC9CP2", _provider_paused), ("SEC9CF1", _provider_failure), ("SEC9CF2", _provider_failure)):
        assets[name] = await _assigned_asset(session, quotes, name)
        quotes.raises[name] = failure
    await _store_closes(session, assets["SEC9CP1"], {2: "55"})
    await _store_closes(session, assets["SEC9CF1"], {2: "66"})

    items = await _current(session, list(assets.values()))

    assert dict(quotes.calls) == dict.fromkeys(assets, 1), f"precondition not met: the providers were asked {dict(quotes.calls)}"
    assert _served(items) == [
        _last_known(assets["SEC9CP1"], "55", 2, paused=True),
        _no_price(assets["SEC9CP2"], paused=True),
        _last_known(assets["SEC9CF1"], "66", 2),
        _no_price(assets["SEC9CF2"]),
    ]
    print_success("paused: RATE_LIMITED and retry_after, with or without a stored close; failed: neither")


@pytest.mark.asyncio
async def test_mf_sec9c_guard_live_quotes_and_fallbacks_in_request_order(session, quotes):
    """Guard: ``[live, stored, unknown, live, row-less, stored, paused, unknown]`` — one answer per requested id, in request
    order: the live quote, the stored close, "Asset not found", "No price data available", the paused provider's stored
    close with its refusal; each repeated id answered alike, its provider asked once.

    Green on HEAD d63558abb too.
    """
    print_section("MF-SEC9c guard: live quotes and fallbacks, in request order")
    live = await _assigned_asset(session, quotes, "SEC9CL")
    quotes.quotes["SEC9CL"] = Decimal("101.5")
    stored = await _unassigned_asset(session, "stored")
    await _store_closes(session, stored, {1: "20"})
    paused = await _assigned_asset(session, quotes, "SEC9CP")
    quotes.raises["SEC9CP"] = _provider_paused
    await _store_closes(session, paused, {4: "8"})
    row_less = await _unassigned_asset(session, "row-less")
    unknown = max(live, stored, paused, row_less) + 1  # the private database holds no other asset
    expected = {
        live: (live, Decimal("101.5"), "EUR", TODAY, f"provider:{quotes.code}", None, None, None),
        stored: _last_known(stored, "20", 1),
        unknown: (unknown, None, None, None, None, "Asset not found", None, None),
        row_less: _no_price(row_less),
        paused: _last_known(paused, "8", 4, paused=True),
    }
    requested = [live, stored, unknown, live, row_less, stored, paused, unknown]

    items = await _current(session, requested)

    assert dict(quotes.calls) == {"SEC9CL": 1, "SEC9CP": 1}, f"provider calls per identifier: {dict(quotes.calls)}"
    assert _served(items) == [expected[asset_id] for asset_id in requested]
    print_success(f"{len(requested)} answers in request order, each repeated id alike")


# =============================================================================
# THE ROUTE: CALLED DIRECTLY, ITS SERVICE RECORDED, ITS SESSION READING NOTHING
# =============================================================================


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


class _CurrentService:
    """Stands in for ``AssetSourceManager.get_current_prices_bulk``: records each call's ids and answers as the service
    does, one item per requested id in request order, a repeated id getting its id's item again; an id of ``unpriced``
    gets an item without a price, as an asset with nothing stored."""

    def __init__(self) -> None:
        self.calls: list[list[int]] = []
        self.unpriced: set[int] = set()

    def item(self, asset_id: int) -> FACurrentPriceItem:
        if asset_id in self.unpriced:
            return FACurrentPriceItem(asset_id=asset_id, error="No price data available")
        return FACurrentPriceItem(asset_id=asset_id, value=Decimal(asset_id), currency="EUR", as_of_date=TODAY, source="provider:sec9")

    async def __call__(self, asset_ids: list[int], _session: Any, *_args: Any, **_kwargs: Any) -> list[FACurrentPriceItem]:
        self.calls.append(list(asset_ids))
        items = {asset_id: self.item(asset_id) for asset_id in dict.fromkeys(asset_ids)}
        return [items[asset_id] for asset_id in asset_ids]


class _RangeChanges:
    """Stands in for ``live_range_changes``: records the asset ids of the items each call is handed and the
    ``target_currency`` it is asked (None without one), and answers a change of its own for each item."""

    def __init__(self) -> None:
        self.handed: list[list[int]] = []
        self.targets: list[str | None] = []

    @staticmethod
    def change_of(asset_id: int, range_start: date) -> FARangeChange:
        return FARangeChange(reference_date=range_start, change_abs=Decimal(asset_id), change_ratio=Decimal("0.01"))

    async def __call__(self, _session: Any, live: list[FACurrentPriceItem], range_start: date, target_currency: str | None = None) -> dict[int, FARangeChange]:
        self.handed.append([item.asset_id for item in live])
        self.targets.append(target_currency)
        return {item.asset_id: self.change_of(item.asset_id, range_start) for item in live}


@pytest.fixture
def route(monkeypatch: pytest.MonkeyPatch) -> tuple[_CurrentService, _RangeChanges]:
    """The route's service and ``live_range_changes`` replaced by recorders, for the test."""
    service, changes = _CurrentService(), _RangeChanges()
    monkeypatch.setattr(AssetSourceManager, "get_current_prices_bulk", staticmethod(service))
    monkeypatch.setattr(prices, "live_range_changes", changes)
    return service, changes


@pytest.fixture
def tomorrow(monkeypatch: pytest.MonkeyPatch) -> date:
    """``latest_range_end()`` as the route reads it, held at the real tomorrow for the test: no midnight in between.

    Set even where the route does not read it (``raising=False``): code without the upper bound then runs as it did, and
    the case fails on what it accepted, not on a missing name."""
    held = date.today() + timedelta(days=1)
    monkeypatch.setattr(prices, "latest_range_end", lambda: held, raising=False)
    return held


async def _current_route(session: Any, asset_ids: list[int], range_start: date | None = None) -> FACurrentPriceResponse:
    return await prices.get_current_prices_bulk(asset_ids=asset_ids, range_start=range_start, session=session, _current_user=None)


async def _refusal(make_call: Callable[[], Awaitable[Any]], also: Callable[[], str] = lambda: "") -> HTTPException:
    """The ``HTTPException`` the route raises; when it raises none, the test fails saying what it answered (and ``also``)."""
    try:
        answer = await make_call()
    except HTTPException as refused:
        return refused
    answered = f"{len(answer.results)} results" if isinstance(answer, FACurrentPriceResponse) else repr(answer)[:200]
    pytest.fail(f"no refusal: the route answered {answered}{also()}")


@pytest.mark.asyncio
async def test_sec9_1_more_than_1000_ids_refused_before_any_read(route):
    """1 001 copies of one id: 422 ``bulk_too_many_items``, ``max_items`` 1 000, ``items`` 1 001 — the ids as sent, the
    duplicates counted —; the service never called, no statement read.

    Red on HEAD f252acb4a: no cap on this route; the service was called with the 1 001 ids.
    """
    print_section("R13-SEC9-1: POST /prices/current, 1 001 ids")
    service, _changes = route
    session = _StatementCounter()

    refused = await _refusal(lambda: _current_route(session, [1] * (MAX_ITEMS + 1)), also=lambda: f"; the service was called {len(service.calls)} time(s)")

    assert refused.status_code == 422, f"{refused.status_code}: {refused.detail!r}"
    detail = refused.detail
    assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", f"the 422 is not coded: {detail!r}"
    assert isinstance(detail.get("message"), str) and detail["message"].strip(), f"no message: {detail!r}"
    assert {key: value for key, value in detail.items() if key not in ("code", "message")} == {"max_items": MAX_ITEMS, "items": MAX_ITEMS + 1}
    assert (service.calls, session.statements) == ([], 0), f"{len(service.calls)} service call(s), {session.statements} statement(s) before the refusal"
    print_success("422 bulk_too_many_items, nothing read")


@pytest.mark.asyncio
async def test_sec9_1_exactly_1000_ids_pass(route):
    """Exactly 1 000 ids pass the cap: the service is called once with them, 1 000 results come back.

    Green on HEAD f252acb4a too: the edge the cap must keep open.
    """
    print_section("R13-SEC9-1: POST /prices/current, 1 000 ids")
    service, _changes = route
    asset_ids = list(range(1, MAX_ITEMS + 1))

    response = await _current_route(_StatementCounter(), asset_ids)

    assert service.calls == [asset_ids]
    assert [item.asset_id for item in response.results] == asset_ids
    print_success("1 000 ids answered")


@pytest.mark.asyncio
async def test_sec9_1_the_range_change_is_computed_once_per_distinct_id(route, tomorrow):
    """``[7, 7, 9, 7]`` with a ``range_start``: ``live_range_changes`` is handed one item per distinct id (7 and 9), once;
    the 4 results come back in request order, each with its id's change.

    Red on HEAD f252acb4a: it was handed every requested item, 7 three times.
    """
    print_section("R13-SEC9-1: the whole-range change, once per distinct id")
    _service, changes = route
    requested, range_start = [7, 7, 9, 7], tomorrow - timedelta(days=30)

    response = await _current_route(_StatementCounter(), requested, range_start)

    assert [sorted(handed) for handed in changes.handed] == [[7, 9]], f"live_range_changes handed: {changes.handed}"
    assert [(item.asset_id, item.range_change) for item in response.results] == [(asset_id, changes.change_of(asset_id, range_start)) for asset_id in requested]
    print_success("one change per distinct id, every result carries its own")


# =============================================================================
# SEC9-4 — range_start BOUNDED BY ITS PARAMETER: THROUGH A REQUEST, ON AN APP OF THE TEST'S OWN
# =============================================================================


@pytest_asyncio.fixture
async def client(route: tuple[_CurrentService, _RangeChanges]) -> AsyncIterator[tuple[httpx.AsyncClient, _StatementCounter]]:
    """A client of a fresh app holding the price router under ``/api/v1/assets``, served in this process (no server,
    no port): signed in, its session a ``_StatementCounter``; behind it, the ``route`` recorders. The process's app is
    never touched."""
    session = _StatementCounter()
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(prices.price_router, prefix="/api/v1/assets")
    app.dependency_overrides[prices.get_session_generator] = lambda: session
    app.dependency_overrides[prices.get_current_user] = lambda: None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://sec9.test") as http:
        yield http, session


async def _post_current(http: httpx.AsyncClient, asset_ids: list[int], range_start: date | None, **params: str) -> httpx.Response:
    query = {**({} if range_start is None else {"range_start": range_start.isoformat()}), **params}
    return await http.post("/api/v1/assets/prices/current", params=query, json=asset_ids)


def _assert_refused_by_its_parameter(response: httpx.Response, name: str) -> None:
    """422 in FastAPI's own shape: ``detail`` a list, one error at ``["query", name]``, ``value_error``. The message is
    the backend's English and not asserted: the location and the type say what was refused."""
    assert response.status_code == 422, f"{response.status_code}: {response.text[:300]}"
    detail = response.json().get("detail")
    assert isinstance(detail, list), f"not the parameter's 422 (a detail of the route body?): {detail!r}"
    assert [(error.get("loc"), error.get("type")) for error in detail] == [(["query", name], "value_error")], detail


def _assert_range_start_refused_by_its_parameter(response: httpx.Response) -> None:
    _assert_refused_by_its_parameter(response, "range_start")


@pytest.mark.asyncio
@pytest.mark.parametrize("days_after_tomorrow", [pytest.param(1, id="the-day-after-tomorrow"), pytest.param(None, id="9999-12-31")])
async def test_sec9_4_range_start_after_tomorrow_refused(client, route, tomorrow, days_after_tomorrow):
    """A ``range_start`` after tomorrow (the day after, and 9999-12-31): the parameter's 422, before the route body —
    the service never called, no statement read.

    Red on HEAD f252acb4a: accepted, 200 (only a day before 1900 was refused).
    """
    (http, session), (service, changes) = client, route
    range_start = date(9999, 12, 31) if days_after_tomorrow is None else tomorrow + timedelta(days=days_after_tomorrow)
    print_section(f"R13-SEC9-4: range_start {range_start}, tomorrow {tomorrow}")

    response = await _post_current(http, [1], range_start)

    _assert_range_start_refused_by_its_parameter(response)
    assert (service.calls, changes.handed, session.statements) == ([], [], 0)
    print_success(f"range_start {range_start}: 422 at query.range_start, nothing read")


@pytest.mark.asyncio
@pytest.mark.parametrize("range_start", [pytest.param(date(1899, 12, 31), id="1899-12-31"), pytest.param(date(1, 1, 1), id="0001-01-01")])
async def test_sec9_4_range_start_before_1900_refused(client, route, tomorrow, range_start):
    """A ``range_start`` before 1900-01-01: the parameter's 422, before the route body — nothing read.

    Red on HEAD f252acb4a for the SHAPE only: refused there too, but by the route body, a 422 whose ``detail`` is a string.
    """
    (http, session), (service, changes) = client, route
    print_section(f"R13-SEC9-4: range_start {range_start} refused")

    response = await _post_current(http, [1], range_start)

    _assert_range_start_refused_by_its_parameter(response)
    assert (service.calls, changes.handed, session.statements) == ([], [], 0)
    print_success(f"range_start {range_start}: 422 at query.range_start")


@pytest.mark.asyncio
@pytest.mark.parametrize("which", ["1900-01-01", "today", "tomorrow"])
async def test_sec9_4_range_start_from_1900_to_tomorrow_accepted(client, route, tomorrow, which):
    """A ``range_start`` on either end of the allowed range, or between, is accepted: 200, the quote and its change.

    Green on HEAD f252acb4a too.
    """
    (http, _session), (service, changes) = client, route
    range_start = {"1900-01-01": EARLIEST, "today": tomorrow - timedelta(days=1), "tomorrow": tomorrow}[which]
    print_section(f"R13-SEC9-4: range_start {range_start} accepted")

    response = await _post_current(http, [3], range_start)

    assert response.status_code == 200, f"{response.status_code}: {response.text[:300]}"
    assert (service.calls, changes.handed) == ([[3]], [[3]])
    expected = FACurrentPriceResponse(results=[service.item(3).model_copy(update={"range_change": changes.change_of(3, range_start)})], success_count=1)
    assert FACurrentPriceResponse.model_validate(response.json()) == expected
    print_success(f"range_start {range_start}: answered")


@pytest.mark.asyncio
async def test_sec9_4_range_start_is_checked_before_the_item_cap(client, route, tomorrow):
    """1 001 ids AND a ``range_start`` after tomorrow: the parameter's 422, not ``bulk_too_many_items`` — FastAPI validates
    the parameters before the route body, where the cap is. Nothing read either way.

    Red on HEAD f252acb4a: neither bound existed, 200 with the 1 001 ids.
    """
    (http, session), (service, changes) = client, route
    print_section("R13-SEC9-4: range_start refused before the 1 000-item cap is counted")

    response = await _post_current(http, [1] * (MAX_ITEMS + 1), tomorrow + timedelta(days=1))

    _assert_range_start_refused_by_its_parameter(response)
    assert (service.calls, changes.handed, session.statements) == ([], [], 0)
    print_success("the parameter's 422 first")


# =============================================================================
# Y'S D1 — target_currency: THE RANGE CHANGE IN THE PAGE'S CURRENCY, THE QUOTES UNCHANGED
# =============================================================================


def _quotes(response: httpx.Response) -> list[tuple[int, str | None, str | None, str | None]]:
    """Each result's quote as the JSON carries it: asset id, value, currency, source."""
    return [(result["asset_id"], result["value"], result["currency"], result["source"]) for result in response.json()["results"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("sent, normalized", [("usd", "USD"), ("CHF", "CHF")])
async def test_d1_target_currency_reaches_the_range_change_normalized(client, route, tomorrow, sent, normalized):
    """``target_currency`` with ``range_start``: ``live_range_changes`` is asked it, normalized (``usd`` → ``USD``), once;
    the quotes stay in their own currency, as the service answered them; each result carries its change.

    Red on HEAD f252acb4a: the parameter does not exist — ignored, the change asked without a target (None).
    """
    (http, _session), (service, changes) = client, route
    print_section(f"Y's D1: target_currency {sent!r}")
    range_start = tomorrow - timedelta(days=30)

    response = await _post_current(http, [3, 3, 8], range_start, target_currency=sent)

    assert response.status_code == 200, f"{response.status_code}: {response.text[:300]}"
    assert changes.targets == [normalized], f"live_range_changes asked target_currency {changes.targets}"
    assert _quotes(response) == [(asset_id, str(asset_id), "EUR", "provider:sec9") for asset_id in (3, 3, 8)], "the quotes must stay native"
    assert [FARangeChange.model_validate(result["range_change"]) for result in response.json()["results"]] == [changes.change_of(asset_id, range_start) for asset_id in (3, 3, 8)]
    assert service.calls == [[3, 3, 8]]
    print_success(f"{sent!r} → {normalized!r} handed to the range change, the quotes native")


@pytest.mark.asyncio
async def test_d1_guard_without_target_currency_the_change_is_native(client, route, tomorrow):
    """Guard: without ``target_currency`` the change is asked without one (None), as before Y's D1.

    Green on HEAD f252acb4a too.
    """
    (http, _session), (_service, changes) = client, route
    print_section("Y's D1 guard: no target_currency")

    response = await _post_current(http, [3], tomorrow - timedelta(days=30))

    assert response.status_code == 200, f"{response.status_code}: {response.text[:300]}"
    assert changes.targets == [None]
    print_success("asked without a target")


@pytest.mark.asyncio
@pytest.mark.parametrize("sent", ["ZZZ", "EU"])
async def test_d1_invalid_target_currency_refused_by_its_parameter(client, route, tomorrow, sent):
    """A ``target_currency`` that is no ISO 4217 code: the parameter's 422 at ``["query", "target_currency"]``, before the
    route body — the service never called, no statement read.

    Red on HEAD f252acb4a: the parameter does not exist — ignored, 200.
    """
    (http, session), (service, changes) = client, route
    print_section(f"Y's D1: target_currency {sent!r} refused")

    response = await _post_current(http, [3], tomorrow - timedelta(days=30), target_currency=sent)

    _assert_refused_by_its_parameter(response, "target_currency")
    assert (service.calls, changes.handed, session.statements) == ([], [], 0)
    print_success(f"{sent!r}: 422 at query.target_currency, nothing read")


@pytest.mark.asyncio
async def test_d1_guard_target_currency_without_range_start_changes_nothing(client, route):
    """Guard: ``target_currency`` alone asks no change — ``live_range_changes`` never called, every ``range_change``
    null — and the quotes come back as the service answered them.

    Green on HEAD f252acb4a too (the parameter ignored there).
    """
    (http, _session), (service, changes) = client, route
    print_section("Y's D1 guard: target_currency without range_start")

    response = await _post_current(http, [3, 8], None, target_currency="usd")

    assert response.status_code == 200, f"{response.status_code}: {response.text[:300]}"
    assert (changes.handed, changes.targets) == ([], [])
    assert [result["range_change"] for result in response.json()["results"]] == [None, None]
    assert _quotes(response) == [(3, "3", "EUR", "provider:sec9"), (8, "8", "EUR", "provider:sec9")]
    assert service.calls == [[3, 8]]
    print_success("no change asked, the quotes native")


# =============================================================================
# X-R59 GUARD — THE QUOTES STAND WHEN THE RANGE CHANGE FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_xr59_guard_the_quotes_stand_when_the_range_change_fails(route, tomorrow, monkeypatch):
    """``live_range_changes`` raises: the route still answers every quote — the values, ``success_count`` — and every
    result's ``range_change`` is the empty one, ``reference_date``, ``change_abs`` and ``change_ratio`` null. The failure
    is logged.

    Guard (X's review, point 1): green on HEAD f252acb4a too — the try/except entered with X-R59.
    """
    print_section("X-R59 guard: the range change fails, the quotes stand")
    service, _changes = route
    service.unpriced.add(6)

    async def failing_change(*_args: Any, **_kwargs: Any) -> dict[int, FARangeChange]:
        raise RuntimeError("the range change failed")

    monkeypatch.setattr(prices, "live_range_changes", failing_change)
    log = _RecordingLogger()
    monkeypatch.setattr(prices, "logger", log)
    requested = [4, 5, 4, 6]

    response = await _current_route(_StatementCounter(), requested, tomorrow - timedelta(days=30))

    assert [(item.asset_id, item.value, item.error) for item in response.results] == [(4, Decimal(4), None), (5, Decimal(5), None), (4, Decimal(4), None), (6, None, "No price data available")]
    assert response.success_count == 3
    assert [(item.range_change.reference_date, item.range_change.change_abs, item.range_change.change_ratio) for item in response.results] == [(None, None, None)] * len(requested)
    assert any(level in ("exception", "error") and isinstance(error, RuntimeError) for level, _message, _kwargs, error in log.lines), f"the failure is not logged: {log.lines}"
    print_success("4 quotes, 3 priced, every range change empty; the failure logged")


# =============================================================================
# SEC9-3 — A 500 NEVER ECHOES ITS ERROR
# =============================================================================


class _RecordingLogger:
    """Stands in for the route module's logger: records every line at any level, with the exception being handled."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict, BaseException | None]] = []

    def __getattr__(self, level: str) -> Callable[..., None]:
        def log(message: str = "", *_args: Any, **kwargs: Any) -> None:
            self.lines.append((level, str(message), kwargs, sys.exc_info()[1]))

        return log


async def _failing(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError(LEAK)


SEC9_3_ROUTES = [
    pytest.param(
        "get_prices_bulk",
        lambda session: prices.query_prices_bulk(requests=[FAPriceQueryItem(asset_id=1, date_range=DateRangeModel(start=TODAY, end=TODAY))], session=session, _current_user=None),
        id="POST-prices-query",
    ),
    pytest.param("get_current_prices_bulk", lambda session: _current_route(session, [1]), id="POST-prices-current"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name, call", SEC9_3_ROUTES)
async def test_sec9_3_a_failure_answers_500_without_echoing_it(monkeypatch, service_name, call):
    """The route's service raises an error naming the schema (``LEAK``): the route answers 500 with a detail that holds
    none of it; the error itself is logged, with its exception.

    Red on HEAD f252acb4a: ``detail=str(e)``, the SQL echoed to the caller.
    """
    print_section(f"R13-SEC9-3: {service_name} fails")
    monkeypatch.setattr(AssetSourceManager, service_name, staticmethod(_failing))
    log = _RecordingLogger()
    monkeypatch.setattr(prices, "logger", log)

    refused = await _refusal(lambda: call(_StatementCounter()))

    assert refused.status_code == 500, f"{refused.status_code}: {refused.detail!r}"
    detail = str(refused.detail)
    assert detail.strip(), "an empty detail"
    leaked = [word for word in ("SELECT", "secret", "FROM", "RuntimeError") if word in detail]
    assert not leaked, f"the 500 echoes the error ({leaked}): {refused.detail!r}"
    logged = [(level, error) for level, _message, kwargs, error in log.lines if level in ("exception", "error", "critical") and (isinstance(error, RuntimeError) or kwargs.get("exc_info"))]
    assert logged and all(str(error) == LEAK for _level, error in logged), f"the error is not logged with its exception: {log.lines}"
    print_success(f"500 {refused.detail!r}; the error logged")

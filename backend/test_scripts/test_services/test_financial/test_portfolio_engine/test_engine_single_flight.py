"""MF-J45b, MF-J45d (workstream MF) — one portfolio build per key and range at a time, a failed build fails everyone
waiting on it at once, and the shared result stays read-only.

The defect (J45b): ``PortfolioCalculationEngine.calculate`` checked the blob cache, missed, and built. N identical
requests arriving together (a Dashboard opened in two tabs, the AI Export's components, a report and a planner on the
same scope) all missed, and each paid the reads, the preloads and a worker of the engine's two-worker executor (J-45)
for the same result. The cure (``financial_math/portfolio/engine.py``): after the cache miss, ``calculate``
single-flights the build on ``(blob_key, actual_from, actual_to)`` in the module's ``_IN_FLIGHT``. The first request
leads: it registers a future, runs ``_compute_uncached`` (steps 6–12, moved unchanged) and settles the future with the
result. An identical request that arrives meanwhile follows: it awaits ``asyncio.shield(flight)`` and gets the same
object (the one the cache holds, read-only like a cache hit).

The defect (J45d, J's review of J45b, HEAD c5ff1f68d): a leader whose build raised settled its flight with
``_LeaderGone`` too, so every follower rebuilt, one after another (the first to resume led, the others followed it):
on data that fails deterministically the k-th follower waited about k builds before failing the same way. The cure:
the build's own exception settles the flight (``except Exception``: ``set_exception(error)``, marked retrieved,
re-raised), so the leader's caller and every follower raise that very object at once, and nothing rebuilds. A leader
that is cancelled (``CancelledError`` is a ``BaseException``: outside that ``except``) still leaves the flight pending
for its ``finally``, which settles it with ``_LeaderGone`` (marked retrieved): the first follower to resume leads a new
build, the others follow it. Either way the flight is settled before its key is removed. A ``BaseException`` other
than cancellation (``KeyboardInterrupt``, ``SystemExit``) is out of scope.

HEAD 98b364b45 is before J45b (no single-flight), HEAD c5ff1f68d is J45b before J45d.

- ``TestOneBuildForIdenticalRequests`` — red on 98b364b45 (every request builds), green on c5ff1f68d and after: two and
  five identical concurrent calculations make one build, every caller gets the identical object, the one the blob cache
  holds; ``_IN_FLIGHT`` is empty after.
- ``TestTheLeaderFails`` — red on c5ff1f68d (once the leader's build fails a follower starts a new build and the
  others wait on it, instead of ending), green after: leader + 3 followers, the leader's build raises; before any build
  is released again all four requests have ended, each raising that very exception object (``is``); one build in all;
  one flight, settled with that exception before its key went (the ordering pin of this path), awaited once by each
  follower, never read stale; a later identical request is not handed the failure: it builds anew and succeeds.
- ``TestTheLeaderIsCancelled`` — red on 98b364b45 (each request builds), green on c5ff1f68d and after: the path J45d
  keeps. The leader's task is cancelled (its caller is cancelled); the followers make exactly one new build among them,
  led by one of them, and all succeed with its object; none hangs; ``_IN_FLIGHT`` is empty. Guards the ``except``'s
  breadth: ``except BaseException`` would hand the ``CancelledError`` to the followers, cancelled with their leader.
- ``TestAFollowerIsCancelled`` — red on 98b364b45 (each request builds), green on c5ff1f68d and after: a follower
  cancelled while it waits leaves the build, its leader and the other followers untouched (``asyncio.shield``): one
  build, all others succeed.
- ``TestNoCoalescingAcrossKeysOrRanges`` — green on both HEADs and after (a guard of the key): another range
  (``date_to``; the blob key is the same, a precondition read from the registered flights), another broker scope,
  another currency: one build each, no request waits for another.
- ``TestTheSettledFlightIsRetrieved`` — red on 98b364b45 (no flight is registered: the precondition fails), green on
  c5ff1f68d and after: a leader that fails or is cancelled with nobody waiting leaves no «Future exception was never
  retrieved» once its future is collected (the loop's exception handler captures it; a weak reference proves the
  future was freed). Guards both ``flight.exception()`` calls: the one after ``set_exception(error)`` (fails), the one
  after ``_LeaderGone`` (is cancelled).
- ``TestTheFlightIsSettledBeforeItsKeyGoes`` — red on 98b364b45 (no flight registered), green on c5ff1f68d and after:
  requirement (1) on the cancellation path, the one with two flights. When the cancelled leader's ``finally`` removes
  its key, its future is already done; no request ever reads a settled flight from ``_IN_FLIGHT`` (the recorder raises
  if one does: a settled flight left under its key would make the follower loop spin forever on the loop's thread, a
  hang no timeout could interrupt); the follower that resumes first finds the key gone and leads, the other follows its
  new flight — none awaits the cancelled one twice.
- ``TestTheSharedResultIsNotMutatedByItsConsumers`` — green on both HEADs and after, a guard of requirement (2): with one
  object now served to every concurrent caller, a consumer that wrote into it would corrupt the others' answers. A deep
  structural snapshot (``_snapshot``: every dataclass field, container and Decimal exponent) of each result
  ``calculate`` returns, taken when it returns, equals the same snapshot after the consumers ran: the report
  (``PortfolioService.get_report`` with every include flag: summary with breakdown, history, allocation history,
  positions contribution, broker P&L history, P&L candles, income/cost/deposit history, acquisition funding; then
  ``get_summary``, ``get_history`` and ``get_positions_contribution`` on their own engine runs), the PAC planner's
  current distribution (``pac_allocator/source/distribution.py``), and the AI Export's ``portfolio.summary``,
  ``portfolio.positions`` and ``portfolio.performance`` components (they read the engine only through
  ``get_report``'s ``PortfolioReportResponse``). Each object watched is the one the blob cache stored.

The seams. A build is counted and held at ``compute_average_costs`` (step 10a, called once per build, on HEAD and
after: patched on the engine module, which resolves it at call time): ``_BuildGate`` holds each build on an
``asyncio.Event`` until the test releases it, optionally with an exception to raise. ``_IN_FLIGHT`` is replaced by
``_RecordedFlights``, a dict that records each flight registered (and its owner task), each pending flight a request
read (it then awaits it at once: no suspension point in between), and whether each flight was done when its key was
removed. The test proceeds when every live request is either held in the gate or waiting on a pending flight
(``_Harness.settle``), an event-driven condition; ``_HANG_S`` only bounds a failure (a request that never settles).
No sleep, no wall-clock assertion.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): user U owns brokers A and B at 100 %; X is a EUR stock,
Y a USD stock; read in EUR up to END (2024-03-14), or EARLIER_END:

- D0 03-04: DEPOSIT 10000 at A, 1000 at B;  D1 03-05: BUY 3 X for 1000 at A;
- D2 03-07: TRANSFER of 1 X A -> B (arrives D4); CASH_TRANSFER of 500 A -> B (arrives D3);
- D3 03-08: FX_CONVERSION at A, 1000 EUR into 1090 USD; BUY 2 Y for 500 USD at A;
- D4 03-11: SELL 1 X for 340 at A; DIVIDEND 12 on X, FEE 3, TAX 2 at A;  D5 03-12: WITHDRAWAL 100 at B.

Prices (X: 333.5, 345.67, 350; Y: 250, 255 USD) and EUR/USD rates (1.09, 1.1) end on or before EARLIER_END (03-13),
so END and EARLIER_END share every fingerprint of the blob key.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. Each concurrent
request opens its own session on the test's private file, as each HTTP request does. The engine's blob cache and the
report's L2 cache (process-global) are emptied around each test; ``_IN_FLIGHT`` and the patches go through
``monkeypatch``. Every request a test starts is released, ended and awaited at teardown (``_harness``).

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_engine_single_flight``.

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate: the single-flight after step 5b;
_compute_uncached; _LeaderGone; _IN_FLIGHT), LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/
plan-phase01FinancialMath.prompt.md («MF-J45b», «MF-J45d»).
"""

from __future__ import annotations

import asyncio
import dataclasses
import enum
import gc
import weakref
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.portfolio_financial import PORTFOLIO_PERFORMANCE_COMPONENT, PORTFOLIO_POSITIONS_COMPONENT, PORTFOLIO_SUMMARY_COMPONENT
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import DailyStates, PortfolioCalculationResult, StateSegment
from backend.app.services.pac_allocator.source.distribution import build_planner_current_distribution
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"

D0 = date(2024, 3, 4)
D1 = date(2024, 3, 5)
D2 = date(2024, 3, 7)
D3 = date(2024, 3, 8)
D4 = date(2024, 3, 11)
D5 = date(2024, 3, 12)
EARLIER_END = date(2024, 3, 13)
END = date(2024, 3, 14)

#: Only a failure reaches it: a request that never reaches the gate or a flight, a gathered request that never ends.
_HANG_S = 30.0
#: Rounds of gc.collect() and one loop iteration before a freed flight must be gone (one is enough today).
_COLLECT_ROUNDS = 10

# (label, broker, asset, type, day, quantity, amount, currency)
_ROWS = (
    ("dep_A", "A", None, TransactionType.DEPOSIT, D0, "0", "10000", EUR),
    ("dep_B", "B", None, TransactionType.DEPOSIT, D0, "0", "1000", EUR),
    ("buy_X", "A", "X", TransactionType.BUY, D1, "3", "-1000", EUR),
    ("tr_out", "A", "X", TransactionType.TRANSFER, D2, "-1", "0", None),
    ("ct_out", "A", None, TransactionType.CASH_TRANSFER, D2, "0", "-500", EUR),
    ("ct_in", "B", None, TransactionType.CASH_TRANSFER, D3, "0", "500", EUR),
    ("fx_out", "A", None, TransactionType.FX_CONVERSION, D3, "0", "-1000", EUR),
    ("fx_in", "A", None, TransactionType.FX_CONVERSION, D3, "0", "1090", USD),
    ("buy_Y", "A", "Y", TransactionType.BUY, D3, "2", "-500", USD),
    ("tr_in", "B", "X", TransactionType.TRANSFER, D4, "1", "0", None),
    ("sell_X", "A", "X", TransactionType.SELL, D4, "-1", "340", EUR),
    ("div_X", "A", "X", TransactionType.DIVIDEND, D4, "0", "12", EUR),
    ("fee_A", "A", None, TransactionType.FEE, D4, "0", "-3", EUR),
    ("tax_X", "A", "X", TransactionType.TAX, D4, "0", "-2", EUR),
    ("wd_B", "B", None, TransactionType.WITHDRAWAL, D5, "0", "-100", EUR),
)
_LINKED_PAIRS = (("tr_out", "tr_in"), ("ct_out", "ct_in"), ("fx_out", "fx_in"))
# (asset, day, close, currency): none after EARLIER_END
_CLOSES = (("X", D1, "333.5", EUR), ("X", D4, "345.67", EUR), ("X", EARLIER_END, "350", EUR), ("Y", D3, "250", USD), ("Y", D5, "255", USD))
# 1 EUR = rate USD from that day (base EUR < quote USD, as FxRate's check requires): none after EARLIER_END
_EUR_USD = ((D3, "1.09"), (D5, "1.1"))


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_ids: dict[str, int]
    asset_ids: dict[str, int]


async def _seed(engine: AsyncEngine) -> _Book:
    """The module's ledger, owned by a new user, committed to the private file."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"j45b_{tag}", email=f"j45b_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"J-45b single flight {label} {tag}") for label in ("A", "B")}
        assets = {
            "X": Asset(display_name=f"J-45b single flight X {tag}", currency=EUR, asset_type=AssetType.STOCK),
            "Y": Asset(display_name=f"J-45b single flight Y {tag}", currency=USD, asset_type=AssetType.STOCK),
        }
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])
        session.add_all(
            [
                *(PriceHistory(asset_id=assets[asset].id, date=day, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=Decimal("1"), currency=currency, source_plugin_key="j45b_single_flight_test") for asset, day, close, currency in _CLOSES),
                *(FxRate(date=day, base=EUR, quote=USD, rate=Decimal(rate), source="TEST") for day, rate in _EUR_USD),
            ]
        )
        rows = {label: Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency) for label, broker, asset, tx_type, day, quantity, amount, currency in _ROWS}
        session.add_all(rows.values())
        await session.flush()
        for left, right in _LINKED_PAIRS:
            rows[left].related_transaction_id = rows[right].id
            rows[right].related_transaction_id = rows[left].id
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_ids={label: broker.id for label, broker in brokers.items()}, asset_ids={label: asset.id for label, asset in assets.items()})


@asynccontextmanager
async def _private_book(directory: Path) -> AsyncIterator[_Book]:
    """The app schema and the module's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'j45b_single_flight.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


async def _calculate(book: _Book, *, broker_labels: tuple[str, ...] | None = None, date_to: date = END, target_currency: str = EUR) -> PortfolioCalculationResult:
    """One request: its own session on the book's file, as each HTTP request has its own."""
    broker_ids = [book.broker_ids[label] for label in broker_labels] if broker_labels else None
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, broker_ids=broker_ids, date_to=date_to, target_currency=target_currency)


# =============================================================================
# THE SEAMS — the build gate and the recorded flights
# =============================================================================


class _BuildFailed(Exception):
    """The exception a held build raises when the test makes it fail."""


class _StaleFlight(AssertionError):
    """A request read a settled flight from ``_IN_FLIGHT``: its key outlived its build."""


class _Wake:
    """The event every seam sets when a request may have changed state; ``until`` re-checks its condition on each."""

    def __init__(self) -> None:
        self._changed = asyncio.Event()

    def __call__(self, *_args: object) -> None:
        self._changed.set()

    async def until(self, condition: Callable[[], bool], what: str) -> None:
        async def wait() -> None:
            while not condition():
                self._changed.clear()
                await self._changed.wait()

        try:
            await asyncio.wait_for(wait(), timeout=_HANG_S)
        except TimeoutError:
            pytest.fail(f"{what}: not reached within {_HANG_S}s — a request hangs")


@dataclass(eq=False)
class _HeldBuild:
    task: asyncio.Task | None
    release: asyncio.Event
    failure: BaseException | None = None

    def held(self) -> bool:
        """Waiting for its release (a build whose request was cancelled meanwhile is no longer held)."""
        return not self.release.is_set() and not (self.task is not None and self.task.done())


class _BuildGate:
    """``compute_average_costs`` (step 10a: once per build, on HEAD and after) held until the test releases the build.

    Once ``open()``, a build that enters is counted but not held: the end of a test never strands a late build."""

    def __init__(self, real: Callable[..., Any], wake: _Wake) -> None:
        self._real = real
        self._wake = wake
        self._open = False
        self.builds: list[_HeldBuild] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        build = _HeldBuild(task=asyncio.current_task(), release=asyncio.Event())
        if self._open:
            build.release.set()
        self.builds.append(build)
        self._wake()
        await build.release.wait()
        if build.failure is not None:
            raise build.failure
        return await self._real(*args, **kwargs)

    def held_by(self, task: asyncio.Task) -> bool:
        return any(build.task is task and build.held() for build in self.builds)

    def release(self, build: _HeldBuild, *, failure: BaseException | None = None) -> None:
        build.failure = failure
        build.release.set()

    def open(self) -> None:
        """Release every held build, and hold none from now on."""
        self._open = True
        for build in self.builds:
            build.release.set()


class _RecordedFlights(dict):
    """The engine's ``_IN_FLIGHT``, recording what the single-flight does with it.

    ``registered``: each flight set, with the task that set it (its leader). ``awaited``: per task, each pending flight
    ``get`` handed it (the request awaits it at once). ``removed``: per key removed, whether its flight was done then.
    A ``get`` by another task than the leader that finds a settled flight raises ``_StaleFlight``: the follower's loop
    would otherwise await it, fail, and read it again forever without yielding to the event loop."""

    def __init__(self, wake: _Wake) -> None:
        super().__init__()
        self._wake = wake
        self.registered: list[tuple[tuple, asyncio.Future, asyncio.Task | None]] = []
        self.awaited: dict[asyncio.Task | None, list[asyncio.Future]] = defaultdict(list)
        self.removed: list[tuple[tuple, bool]] = []
        self.stale_reads: list[tuple[tuple, asyncio.Task | None]] = []

    def _leader_of(self, flight: asyncio.Future) -> asyncio.Task | None:
        return next((task for _key, registered, task in self.registered if registered is flight), None)

    def get(self, key: Any, default: Any = None) -> Any:
        flight = super().get(key, default)
        if flight is None or not isinstance(flight, asyncio.Future):
            return flight
        task = asyncio.current_task()
        if task is self._leader_of(flight):
            return flight  # the leader's own check before removing its key
        if flight.done():
            self.stale_reads.append((key, task))
            raise _StaleFlight("a request read a settled flight from _IN_FLIGHT: its key outlived its build")
        self.awaited[task].append(flight)
        self._wake()
        return flight

    def __setitem__(self, key: Any, flight: Any) -> None:
        self.registered.append((key, flight, asyncio.current_task()))
        super().__setitem__(key, flight)

    def __delitem__(self, key: Any) -> None:
        self.removed.append((key, super().__getitem__(key).done()))
        super().__delitem__(key)

    def pop(self, key: Any, *default: Any) -> Any:
        if key in self:
            self.removed.append((key, super().__getitem__(key).done()))
        return super().pop(key, *default)

    def waiting_on(self, task: asyncio.Task) -> asyncio.Future | None:
        """The pending flight ``task`` is waiting on, if any."""
        flights = self.awaited.get(task)
        return flights[-1] if flights and not flights[-1].done() else None

    def forget(self) -> None:
        """Drop every reference to a flight or a task (the never-retrieved test needs the futures freed)."""
        self.registered.clear()
        self.awaited.clear()
        self.stale_reads.clear()


@dataclass
class _Harness:
    """The requests of one test, the gate holding their builds, the flights they register and await."""

    book: _Book
    gate: _BuildGate
    flights: _RecordedFlights
    wake: _Wake
    tasks: list[asyncio.Task] = field(default_factory=list)

    def start(self, **request: Any) -> asyncio.Task:
        task = asyncio.ensure_future(_calculate(self.book, **request))
        task.add_done_callback(self.wake)
        self.tasks.append(task)
        return task

    def live(self) -> list[asyncio.Task]:
        return [task for task in self.tasks if not task.done()]

    def quiet(self) -> bool:
        """Every live request is held in the gate or waits on a pending flight (a request being cancelled is about to
        run: not quiet until it has ended)."""
        return all(not task.cancelling() and (self.gate.held_by(task) or self.flights.waiting_on(task) is not None) for task in self.live())

    async def settle(self, what: str) -> None:
        await self.wake.until(self.quiet, what)

    def held_builds(self) -> list[_HeldBuild]:
        return [build for build in self.gate.builds if build.held()]

    def waiting(self) -> list[asyncio.Task]:
        return [task for task in self.live() if self.flights.waiting_on(task) is not None]

    async def finish(self) -> list[object]:
        """Open the gate and gather every request: results and exceptions, in start order."""
        self.gate.open()
        try:
            return await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), timeout=_HANG_S)
        except TimeoutError:
            pytest.fail(f"the requests did not end within {_HANG_S}s once every build was released — a request hangs")

    def failed_builds(self) -> list[BaseException]:
        return [build.failure for build in self.gate.builds if build.failure is not None]


@asynccontextmanager
async def _harness_for(book: _Book, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Harness]:
    """The gate on ``compute_average_costs`` and the recorded ``_IN_FLIGHT`` installed; at the end every build released
    and every request ended (cancelled if it still runs), so none outlives the test or its private file."""
    wake = _Wake()
    gate = _BuildGate(portfolio_engine_module.compute_average_costs, wake)
    flights = _RecordedFlights(wake)
    monkeypatch.setattr(portfolio_engine_module, "compute_average_costs", gate)
    # raising=False: HEAD 98b364b45 has no _IN_FLIGHT, and its tests must fail on their counts, not on the patch
    monkeypatch.setattr(portfolio_engine_module, "_IN_FLIGHT", flights, raising=False)
    harness = _Harness(book=book, gate=gate, flights=flights, wake=wake)
    try:
        yield harness
    finally:
        gate.open()
        for task in harness.tasks:
            if not task.done():
                task.cancel()
        if harness.tasks:
            await asyncio.wait(harness.tasks, timeout=_HANG_S)


class _BlobStores:
    """Every object the engine stored in its blob cache (the object served to later requests)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.stored: list[object] = []
        cache = portfolio_engine_module._portfolio_blob_cache
        real_set = cache.set

        def recording_set(key: Any, value: Any, **kwargs: Any) -> None:
            self.stored.append(value)
            real_set(key, value, **kwargs)

        monkeypatch.setattr(cache, "set", recording_set)

    def holds(self, result: object) -> bool:
        return any(stored is result for stored in self.stored)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No engine blob and no report crosses into or out of a test: a cached one would answer without a build."""
    portfolio_engine_module._portfolio_blob_cache.clear()
    portfolio_service_module._portfolio_l2_cache.clear()
    request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)
    request.addfinalizer(portfolio_service_module._portfolio_l2_cache.clear)


@pytest_asyncio.fixture
async def book(tmp_path) -> AsyncIterator[_Book]:
    async with _private_book(tmp_path) as opened:
        yield opened


@pytest_asyncio.fixture
async def harness(book, monkeypatch) -> AsyncIterator[_Harness]:
    async with _harness_for(book, monkeypatch) as opened:
        yield opened


@pytest.fixture
def blob_stores(monkeypatch) -> _BlobStores:
    return _BlobStores(monkeypatch)


# =============================================================================
# 1 — RED ON HEAD 98b364b45: IDENTICAL CONCURRENT REQUESTS MAKE ONE BUILD
# =============================================================================


class TestOneBuildForIdenticalRequests:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("requests", [2, 5])
    async def test_identical_concurrent_requests_share_one_build_and_one_object(self, harness, blob_stores, requests):
        """N identical requests started together: one build; every caller gets the identical object, the one the blob
        cache holds; no flight left. HEAD 98b364b45: every request builds (N builds, N objects)."""
        print_section(f"MF-J45b: {requests} identical concurrent requests")
        for _ in range(requests):
            harness.start()
        await harness.settle("every request held in a build or waiting on one")
        held, waiting = len(harness.held_builds()), len(harness.waiting())

        results = await harness.finish()

        assert all(isinstance(result, PortfolioCalculationResult) for result in results), f"a request failed: {results!r}"
        assert len(harness.gate.builds) == 1, f"{requests} identical concurrent requests made {len(harness.gate.builds)} builds (held together: {held} building, {waiting} waiting): expected one, the others waiting for it"
        first = results[0]
        assert first.daily_states, "precondition: the build produced daily states"
        assert all(result is first for result in results), "the requests got different objects: each built its own"
        assert blob_stores.holds(first), "the object served is not the one the blob cache holds"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        print_success(f"one build, one object for {requests} requests")


# =============================================================================
# 2 — RED ON HEAD c5ff1f68d: THE LEADER FAILS, EVERY FOLLOWER RAISES ITS EXCEPTION AT ONCE, NOTHING REBUILDS
# =============================================================================


async def _leader_with_followers(harness: _Harness, followers: int) -> tuple[_HeldBuild, list[asyncio.Task]]:
    """``1 + followers`` identical requests settled: the leader's build held, the others waiting on its flight."""
    for _ in range(1 + followers):
        harness.start()
    await harness.settle("the leader held in its build, the followers waiting")
    assert len(harness.gate.builds) == 1, f"precondition: one build for {1 + followers} identical requests, got {len(harness.gate.builds)} (each request built its own)"
    [leader_build] = harness.gate.builds
    waiting = [task for task in harness.tasks if task is not leader_build.task]
    assert all(harness.flights.waiting_on(task) is not None for task in waiting), "precondition: every other request waits on the leader's flight"
    return leader_build, waiting


class TestTheLeaderFails:
    @pytest.mark.asyncio
    async def test_every_waiting_request_raises_the_builds_own_exception_at_once_and_nothing_rebuilds(self, harness):
        """Leader + 3 followers; the leader's build raises. Before any build is released again, all four requests have
        ended, each raising that very exception object: one build in all. The one flight was settled with it before its
        key went, each follower awaited it once. A later identical request is not handed the failure: it builds anew.
        HEAD c5ff1f68d: the flight is settled with ``_LeaderGone``, a follower leads a new build, the others wait on it."""
        print_section("MF-J45d: the leader's build fails, three followers")
        leader_build, followers = await _leader_with_followers(harness, followers=3)
        [(key, flight, _leader)] = harness.flights.registered
        failure = _BuildFailed("corrupt data: the leader's build failed")
        harness.gate.release(leader_build, failure=failure)
        await harness.settle("the leader's failure reached its followers: each ended, or holds or awaits a new build")
        rebuilds, still_running = len(harness.gate.builds) - 1, len(harness.live())
        waiting_again = len(harness.waiting())
        ended_at_once = rebuilds == 0 and still_running == 0

        results = await harness.finish()

        assert ended_at_once, f"once the leader's build failed, the followers started {rebuilds} new build(s) and {still_running} request(s) still ran ({waiting_again} waiting on a new flight), before any build was released: expected every follower to fail at once with the leader's exception"
        wrong = {index: result for index, result in enumerate(results) if result is not failure}
        assert wrong == {}, f"requests did not raise the leader's build's own exception (by start order): {wrong!r}"
        assert [flight for _key, flight, _task in harness.flights.registered] == [flight], "a second flight was registered after the leader's build failed"
        assert flight.exception() is failure, f"the flight was settled with {flight.exception()!r}, not the build's own exception"
        assert harness.flights.removed == [(key, True)], f"(key, flight done) per removal: {harness.flights.removed} — expected the leader's key removed once, its flight already settled"
        assert harness.flights.stale_reads == [], f"{len(harness.flights.stale_reads)} read(s) of a settled flight from _IN_FLIGHT: a key outlived its build"
        assert all(harness.flights.awaited[task] == [flight] for task in followers), "a follower did not await the leader's flight exactly once"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"

        later = harness.start()
        outcome = (await harness.finish())[-1]

        assert isinstance(outcome, PortfolioCalculationResult), f"a later identical request did not build anew: {outcome!r}"
        assert len(harness.gate.builds) == 2 and harness.gate.builds[-1].task is later, "the later request was not served by a build of its own"
        print_success("one build, its exception raised by the leader and its three followers at once; a later request builds")


# =============================================================================
# 3 — RED ON HEAD 98b364b45, GREEN ON c5ff1f68d AND AFTER: THE LEADER IS CANCELLED, THE FOLLOWERS BUILD ONCE
# =============================================================================


class TestTheLeaderIsCancelled:
    @pytest.mark.asyncio
    async def test_the_followers_make_one_new_build_and_all_succeed(self, harness, blob_stores):
        """Leader + 3 followers; the leader's task is cancelled (its caller is cancelled): no failure of the build to
        hand on. The followers resume: one leads a new build, the other two wait on it; that build released, the three
        succeed with its object. Two builds in all; no flight left."""
        print_section("MF-J45b: the leader is cancelled, three followers")
        leader_build, followers = await _leader_with_followers(harness, followers=3)
        leader = leader_build.task
        leader.cancel()
        await harness.settle("the followers resumed: one building, the others waiting on it")
        rebuilds = harness.held_builds()

        results = await harness.finish()

        assert leader.cancelled(), f"the cancelled leader's caller was not cancelled: {results[harness.tasks.index(leader)]!r}"
        follower_results = [results[harness.tasks.index(task)] for task in followers]
        assert all(isinstance(result, PortfolioCalculationResult) for result in follower_results), f"a follower did not succeed after its leader was cancelled (a cancellation handed on as a failure?): {follower_results!r}"
        assert len(harness.gate.builds) == 2, f"after the leader was cancelled, the followers made {len(harness.gate.builds) - 1} builds: expected one, the first to resume leading the others"
        assert len(rebuilds) == 1 and rebuilds[0].task in followers, "the new build is not led by one of the followers"
        assert all(result is follower_results[0] for result in follower_results), "the followers got different objects"
        assert blob_stores.holds(follower_results[0]), "the followers' object is not the one the blob cache holds"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        print_success("leader cancelled: one rebuild, three followers served")


# =============================================================================
# 4 — RED ON HEAD 98b364b45: A FOLLOWER CANCELLED WHILE WAITING TOUCHES NOTHING ELSE
# =============================================================================


class TestAFollowerIsCancelled:
    @pytest.mark.asyncio
    async def test_a_cancelled_follower_leaves_the_build_its_leader_and_the_others_untouched(self, harness, blob_stores):
        """Leader + 3 followers; one follower cancelled while it waits: the leader's flight is still pending and its
        build still held; released, the leader and the two other followers succeed with one object; one build."""
        print_section("MF-J45b: a follower cancelled while it waits")
        leader_build, followers = await _leader_with_followers(harness, followers=3)
        cancelled, *others = followers
        flight = harness.flights.waiting_on(cancelled)
        cancelled.cancel()
        await harness.wake.until(cancelled.done, "the cancelled follower ended")
        await harness.settle("the others still held or waiting")

        assert not flight.done(), f"cancelling a follower settled the leader's flight: {flight!r}"
        assert leader_build.held() and not leader_build.task.done(), "cancelling a follower ended the leader's build"
        results = await harness.finish()

        assert cancelled.cancelled(), "precondition: the follower was cancelled"
        served = [results[harness.tasks.index(task)] for task in (leader_build.task, *others)]
        assert all(isinstance(result, PortfolioCalculationResult) for result in served), f"the leader or another follower did not succeed: {served!r}"
        assert all(result is served[0] for result in served), "the leader and the other followers got different objects"
        assert len(harness.gate.builds) == 1, f"a cancelled follower caused {len(harness.gate.builds)} builds: expected one"
        assert blob_stores.holds(served[0]), "the object served is not the one the blob cache holds"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        print_success("one build, the leader and two followers served")


# =============================================================================
# 5 — GREEN ON BOTH HEADS AND AFTER: NO COALESCING ACROSS KEYS OR RANGES
# =============================================================================


class TestNoCoalescingAcrossKeysOrRanges:
    @pytest.mark.asyncio
    async def test_another_range_scope_or_currency_builds_on_its_own(self, harness):
        """Four concurrent requests that differ in one thing each — the base request, another range (EARLIER_END: the
        same blob key, a precondition), another broker scope (A only), another currency (USD) — make four builds,
        held together, none waiting for another; four distinct objects; no flight left."""
        print_section("MF-J45b: another range, scope or currency is another build")
        requests = {
            "base": {},
            "range": {"date_to": EARLIER_END},
            "scope": {"broker_labels": ("A",)},
            "currency": {"target_currency": USD},
        }
        tasks = {name: harness.start(**request) for name, request in requests.items()}
        await harness.settle("every request held in a build or waiting on one")
        held, waiting = len(harness.held_builds()), [name for name, task in tasks.items() if harness.flights.waiting_on(task) is not None]

        results = await harness.finish()

        assert all(isinstance(result, PortfolioCalculationResult) for result in results), f"a request failed: {results!r}"
        assert waiting == [], f"requests waited for another's build: {waiting}"
        assert held == len(requests) and len(harness.gate.builds) == len(requests), f"{len(requests)} different requests made {len(harness.gate.builds)} builds ({held} held together): expected one each"
        assert len({id(result) for result in results}) == len(requests), "two different requests got the same object"
        if harness.flights.registered:  # after the cure: the range case differs from the base only by its range
            keys = {task: key for key, _flight, task in harness.flights.registered}
            base_key, range_key = keys[tasks["base"]], keys[tasks["range"]]
            assert base_key[0] == range_key[0], "precondition: the base and the EARLIER_END requests share the blob key, so only the range tells them apart"
            assert base_key != range_key, "the range is not part of the flight key"
        by_name = dict(zip(requests, results, strict=True))
        assert by_name["range"].date_to == EARLIER_END and by_name["base"].date_to == END, "a request got another range's result"
        assert by_name["currency"].target_currency == USD and by_name["base"].target_currency == EUR, "a request got another currency's result"
        assert sorted(by_name["scope"].scope_broker_ids) == [harness.book.broker_ids["A"]], "the A-only request got another scope's result"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        print_success("four requests, four builds")


# =============================================================================
# 6 — RED ON HEAD 98b364b45 (NO FLIGHT): A SETTLED FLIGHT NOBODY AWAITED IS RETRIEVED
# =============================================================================


class TestTheSettledFlightIsRetrieved:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ["fails", "is_cancelled"])
    async def test_a_lone_leader_that_ends_badly_leaves_no_never_retrieved_exception(self, harness, how):
        """One request, no follower; its build raises (the flight holds that exception) or its task is cancelled (the
        flight holds ``_LeaderGone``). Once the request and its flight are freed, the loop's exception handler has seen
        no «exception was never retrieved»."""
        print_section(f"MF-J45b/J45d: a lone leader {how.replace('_', ' ')}")
        loop = asyncio.get_running_loop()
        reported: list[dict] = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: reported.append(context))
        try:
            flight_ref = await self._end_a_lone_leader_badly(harness, how)
            # A handle the loop still queues may hold the ended request one more iteration: collect, yield, again.
            for _ in range(_COLLECT_ROUNDS):
                gc.collect()
                if flight_ref is None or flight_ref() is None:
                    break
                await asyncio.sleep(0)
            flight_freed = flight_ref is not None and flight_ref() is None
        finally:
            loop.set_exception_handler(previous_handler)

        never_retrieved = [context.get("message") for context in reported if "never retrieved" in str(context.get("message", ""))]
        assert flight_ref is not None, "precondition: the request registered no flight in _IN_FLIGHT (no single-flight)"
        assert flight_freed, "precondition: the flight was not freed, so its finalizer could not report"
        assert never_retrieved == [], f"a settled flight nobody awaited reported: {never_retrieved}"
        print_success("nothing reported")

    @staticmethod
    async def _end_a_lone_leader_badly(harness: _Harness, how: str) -> weakref.ref | None:
        """Run one request to a failed or cancelled build; keep nothing but a weak reference to its flight."""
        task = harness.start()
        await harness.settle("the lone request held in its build")
        [build] = harness.gate.builds
        failure = _BuildFailed("the lone build failed")
        if how == "fails":
            harness.gate.release(build, failure=failure)
        else:
            task.cancel()
        outcome = (await harness.finish())[0]
        assert (outcome is failure) if how == "fails" else isinstance(outcome, asyncio.CancelledError), f"precondition: the request ended with {outcome!r}"
        flight_ref = weakref.ref(harness.flights.registered[0][1]) if harness.flights.registered else None
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        # Drop every strong reference: the recorder's, the gate's, the harness's tasks (their exceptions' tracebacks
        # hold calculate's frame, and with it the flight; a failed flight holds the exception in turn: a cycle).
        harness.flights.forget()
        harness.gate.builds.clear()
        harness.tasks.clear()
        del task, build, outcome, failure
        return flight_ref


# =============================================================================
# 7 — RED ON HEAD 98b364b45 (NO FLIGHT): A CANCELLED LEADER'S FLIGHT IS SETTLED BEFORE ITS KEY GOES
# =============================================================================


class TestTheFlightIsSettledBeforeItsKeyGoes:
    @pytest.mark.asyncio
    async def test_a_resuming_follower_finds_the_key_gone_and_never_awaits_the_failed_flight_again(self, harness):
        """Leader + 2 followers; the leader is cancelled (a failing build's path is pinned in ``TestTheLeaderFails``).
        When its key was removed its flight was done, settled with ``_LeaderGone``; no request read a settled flight;
        the first follower to resume registered the second flight (it leads), the other awaited the leader's flight then
        the new one — never the cancelled one twice; the second flight's key was removed done too."""
        print_section("MF-J45b: the leader is cancelled: settle, then remove")
        leader_build, followers = await _leader_with_followers(harness, followers=2)
        assert harness.flights.registered, "precondition: the leader registered a flight in _IN_FLIGHT (no single-flight)"
        [(first_key, first_flight, first_leader)] = harness.flights.registered
        assert first_leader is leader_build.task, "precondition: the flight's leader is the request holding the build"
        leader_build.task.cancel()
        await harness.settle("the followers resumed: one building, the other waiting on it")

        results = await harness.finish()

        assert harness.flights.stale_reads == [], f"{len(harness.flights.stale_reads)} read(s) of a settled flight from _IN_FLIGHT: a key outlived its build"
        removed_done = [done for _key, done in harness.flights.removed]
        assert removed_done == [True, True], f"flight done when its key was removed, per removal: {removed_done} — a key removed before its flight is settled leaves its followers on an orphaned future"
        assert [key for key, _done in harness.flights.removed] == [first_key, first_key], "precondition: the leader's key, then the new leader's (the same key) were removed"
        [(_key, second_flight, second_leader)] = harness.flights.registered[1:]
        assert second_leader in followers, "the second flight is not led by a follower"
        [other] = [task for task in followers if task is not second_leader]
        assert harness.flights.awaited[second_leader] == [first_flight], "the new leader awaited something else than the cancelled leader's flight before leading"
        assert harness.flights.awaited[other] == [first_flight, second_flight], "the other follower did not go from the cancelled leader's flight to the new one"
        assert isinstance(first_flight.exception(), portfolio_engine_module._LeaderGone), f"the cancelled leader's flight was settled with {first_flight.exception()!r}, not _LeaderGone"
        assert all(isinstance(results[harness.tasks.index(task)], PortfolioCalculationResult) for task in followers), f"a follower did not succeed: {results!r}"
        assert len(harness.flights) == 0, f"{len(harness.flights)} flight(s) left in _IN_FLIGHT once every request ended"
        print_success("settled, then removed; the first follower to resume led")


# =============================================================================
# 8 — GREEN ON BOTH HEADS AND AFTER (GUARD): THE SHARED RESULT IS NOT MUTATED BY ITS CONSUMERS
# =============================================================================


class _UnsnapshottableValue(TypeError):
    """``_snapshot`` met a value it cannot compare structurally: extend it rather than skip the value."""


def _snapshot(value: Any, path: str = "result", _stack: frozenset[int] = frozenset()) -> Any:
    """A structural, comparable copy of ``value``: every dataclass field (``init=False`` ones included), every mapping
    in insertion order, every sequence, sets sorted, a Decimal with its exponent. Unknown types raise, never skip."""
    if isinstance(value, Decimal):
        return ("Decimal", str(value))
    if isinstance(value, enum.Enum):
        return (type(value).__name__, value.value)
    if value is None or isinstance(value, str | int | float | date):  # bool is an int, datetime a date
        return (type(value).__name__, value)
    if id(value) in _stack:
        return ("cycle", type(value).__name__)
    stack = _stack | {id(value)}
    if isinstance(value, DailyStates):
        # P4: the states a consumer could write into are the stored ones, one per segment (start, end, state)
        return (type(value).__name__, _snapshot(value.segments, f"{path}.segments", stack))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _snapshot_dataclass(value, path, stack)
    if isinstance(value, Mapping):
        return (type(value).__name__, tuple((_snapshot(key, f"{path}[key]", stack), _snapshot(item, f"{path}[{key!r}]", stack)) for key, item in value.items()))
    if isinstance(value, set | frozenset):
        return (type(value).__name__, tuple(sorted((_snapshot(item, f"{path}{{}}", stack) for item in value), key=repr)))
    if isinstance(value, list | tuple):
        return (type(value).__name__, tuple(_snapshot(item, f"{path}[{index}]", stack) for index, item in enumerate(value)))
    raise _UnsnapshottableValue(f"{path}: cannot snapshot a {type(value).__qualname__}")


def _snapshot_dataclass(value: Any, path: str, stack: frozenset[int]) -> Any:
    """Every field of a dataclass instance, ``init=False`` ones included (one never set is marked, not skipped)."""
    fields = []
    for field_ in dataclasses.fields(value):
        try:
            item = getattr(value, field_.name)
        except AttributeError:
            fields.append((field_.name, ("unset",)))
            continue
        fields.append((field_.name, _snapshot(item, f"{path}.{field_.name}", stack)))
    return (type(value).__name__, tuple(fields))


def _differences(before: Any, after: Any) -> list[str]:
    """The top-level fields of a result whose snapshots differ (a result's snapshot is (name, ((field, value), ...)))."""
    before_fields, after_fields = dict(before[1]), dict(after[1])
    return [name for name in before_fields if before_fields[name] != after_fields.get(name)]


class _ResultWatch:
    """Every result ``calculate`` returns, with its snapshot taken as it returns; ``changes()`` lists what moved since.

    A result returned again (a cache hit, a follower) is checked against its first snapshot at that moment too."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls = 0
        self.watched: dict[int, tuple[PortfolioCalculationResult, Any]] = {}
        self.changed_on_return: list[str] = []
        real_calculate = PortfolioCalculationEngine.calculate
        watch = self

        async def calculate(engine: PortfolioCalculationEngine, *args: Any, **kwargs: Any) -> PortfolioCalculationResult:
            result = await real_calculate(engine, *args, **kwargs)
            watch.calls += 1
            known = watch.watched.get(id(result))
            if known is None:
                watch.watched[id(result)] = (result, _snapshot(result))
            elif moved := _differences(known[1], _snapshot(result)):
                watch.changed_on_return.append(f"result {id(result):#x} returned again with {moved} changed")
            return result

        monkeypatch.setattr(PortfolioCalculationEngine, "calculate", calculate)

    def results(self) -> list[PortfolioCalculationResult]:
        return [result for result, _snap in self.watched.values()]

    def changes(self) -> list[str]:
        problems = list(self.changed_on_return)
        for result, before in self.watched.values():
            if moved := _differences(before, _snapshot(result)):
                problems.append(f"result {id(result):#x} ({result.date_from}..{result.date_to}, {result.target_currency}): {moved} changed")
        return problems


def _full_report_query(book: _Book) -> PortfolioReportQuery:
    return PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=D2, end=END),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
        include_breakdown=True,
        include_positions_contribution=True,
        include_broker_pnl_history=True,
        include_pnl_candles=True,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
    )


def _portfolio_scope(book: _Book) -> BuildScope:
    return BuildScope(request_id=f"j45b-{uuid4().hex[:8]}", user_id=book.user_id, domain=Domain.PORTFOLIO, detail_level=DetailLevel.STANDARD, period_start=D2, period_end=END, target_currency=EUR, broker_scope=())


class TestTheSharedResultIsNotMutatedByItsConsumers:
    @pytest.mark.asyncio
    async def test_the_report_the_planner_and_the_ai_export_leave_the_engine_result_as_built(self, book, blob_stores, monkeypatch):
        """Every result ``calculate`` returns while the consumers run is snapshotted when it returns and again at the
        end: equal. The consumers: the full report and the report's methods on their own runs, the PAC planner's
        current distribution, three AI Export components on a fresh request context."""
        print_section("MF-J45b: the shared result is read-only for its consumers")
        watch = _ResultWatch(monkeypatch)

        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            service = PortfolioService(session)
            report = await service.get_report(book.user_id, _full_report_query(book))
            summary = await service.get_summary(book.user_id, include_breakdown=True, target_currency_override=EUR, date_from=D2, date_to=END)
            history = await service.get_history(book.user_id, date_from=D2, date_to=END, target_currency_override=EUR)
            contribution = await service.get_positions_contribution(book.user_id, date_from=D2, date_to=END, target_currency_override=EUR)
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            distribution = await build_planner_current_distribution(
                session,
                user_id=book.user_id,
                broker_ids=sorted(book.broker_ids.values()),
                scenario_asset_ids=sorted(book.asset_ids.values()),
                as_of=END,
                target_currency=EUR,
                issues=[],
            )
        portfolio_service_module._portfolio_l2_cache.clear()  # the AI Export's report runs the engine again, not the L2 cache
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            scope = _portfolio_scope(book)
            context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
            ai_payloads = [await component.builder(context, {}) for component in (PORTFOLIO_SUMMARY_COMPONENT, PORTFOLIO_POSITIONS_COMPONENT, PORTFOLIO_PERFORMANCE_COMPONENT)]

        # Preconditions: the consumers read real data, from objects the blob cache shares.
        assert report.summary is not None and report.summary.holdings, "precondition: the report has holdings"
        assert report.history and report.allocation_history and report.positions_contribution and report.broker_pnl_history, "precondition: the report has its history, allocation, contribution and broker P&L views"
        assert report.pnl_candles and report.income_history and report.cost_history and report.deposit_history and report.acquisition_funding, "precondition: the report has candles, income, cost, deposit and funding series"
        assert summary.holdings and history and contribution.positions, "precondition: the standalone summary, history and contribution have rows"
        assert distribution.status == "complete" and distribution.rows, f"precondition: the planner valued the scenario ({distribution.status})"
        assert ai_payloads[1].positions, "precondition: the AI Export's positions component has rows"
        results = watch.results()
        assert watch.calls >= 6 and results, f"precondition: the consumers ran the engine ({watch.calls} calls)"
        assert all(result.daily_states and result.position_states_end for result in results), "precondition: every result watched has daily states and end positions"
        assert all(blob_stores.holds(result) for result in results), "precondition: every result watched is the blob cache's shared object"
        assert watch.calls > len(results), "precondition: a result was served more than once (a cache hit), as concurrent followers are served"

        changes = watch.changes()
        assert changes == [], "a consumer wrote into the engine's shared result:\n" + "\n".join(changes)
        print_success(f"{len(results)} shared results, {watch.calls} engine calls, nothing moved")

    def test_the_snapshot_sees_a_write_anywhere_in_a_result(self):
        """The guard's teeth (pure): a write into a nested dict of a daily state, a list append, a Decimal's exponent,
        a field rebound — each changes the snapshot; an object it cannot compare raises instead of being skipped."""
        from backend.app.services.financial_math.portfolio.models import DailyPortfolioState  # noqa: PLC0415

        zero = Decimal("0")
        state_fields = {field_.name: zero for field_ in dataclasses.fields(DailyPortfolioState) if field_.default is dataclasses.MISSING and field_.default_factory is dataclasses.MISSING and field_.name != "date"}

        def build() -> PortfolioCalculationResult:
            state = DailyPortfolioState(date=D0, **state_fields, by_type={"Stock": Decimal("1.0")})
            return PortfolioCalculationResult(daily_states=[state], date_from=D0, date_to=D0)

        writes: dict[str, Callable[[PortfolioCalculationResult], None]] = {
            "nested dict": lambda result: result.daily_states[0].by_type.__setitem__("Stock", Decimal("2")),
            "list append": lambda result: result.realized_sales.append(None),
            "exponent": lambda result: result.daily_states[0].by_type.__setitem__("Stock", Decimal("1.00")),
            "set add": lambda result: result.daily_states[0].missing_fx_pairs.add("EUR/USD"),
            "rebound field": lambda result: setattr(result, "target_currency", USD),
        }
        for name, write in writes.items():
            result = build()
            before = _snapshot(result)
            write(result)
            assert _differences(before, _snapshot(result)), f"the snapshot missed a write: {name}"
        assert _differences(_snapshot(build()), _snapshot(build())) == [], "two equal results snapshot differently"

        def build_segments() -> PortfolioCalculationResult:
            state = DailyPortfolioState(date=D0, **state_fields, by_type={"Stock": Decimal("1.0")})
            return PortfolioCalculationResult(daily_states=DailyStates([StateSegment(start=D0, end=D0 + timedelta(days=2), state=state)]), date_from=D0, date_to=D0)

        segment_writes: dict[str, Callable[[PortfolioCalculationResult], None]] = {
            "segment state nested dict": lambda result: result.daily_states.segments[0].state.by_type.__setitem__("Stock", Decimal("2")),
            "segment state set add": lambda result: result.daily_states.segments[0].state.missing_fx_pairs.add("EUR/USD"),
        }
        for name, write in segment_writes.items():
            result = build_segments()
            before = _snapshot(result)
            write(result)
            assert _differences(before, _snapshot(result)), f"the snapshot missed a write: {name}"
        assert _differences(_snapshot(build_segments()), _snapshot(build_segments())) == [], "two equal segmented results snapshot differently"
        with pytest.raises(_UnsnapshottableValue):
            _snapshot(PortfolioCalculationResult(daily_states=[object()]))

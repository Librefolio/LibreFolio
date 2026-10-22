"""J-45 = R13-SEC7-1b (workstream MF; J and E review) — the portfolio replay runs off the event loop.

The defect (MEDIUM, DoS): ``PortfolioCalculationEngine.calculate`` ran ``builder.build()`` (``DailyStateBuilder.build``,
pure CPU, long on a wide range) directly on the event loop: while one user's wide report was being replayed, no other
request was served. R13-SEC7-1 capped the range end; this lot moves the replay off the loop. The cure
(``financial_math/portfolio/engine.py``): the engine's own ``ThreadPoolExecutor(max_workers=2,
thread_name_prefix="portfolio-engine")``, created on first use by ``_engine_executor()`` and kept in the module's
``_ENGINE_EXECUTOR``, ``None`` until then and after an app shutdown (MF-J45a, below), and ``result = await
loop.run_in_executor(_engine_executor(), contextvars.copy_context().run, builder.build)`` — the copied context keeps
the request's contextvars in the worker: today the secrets ``secrets_in_flight`` masks and the ``decimal`` context; no
code binds a structlog context yet. Its
safety (MF plan, «SEC7-1b»): the builder reads only loaded column attributes of the ORM ``Transaction`` instances it is
handed (``classified_txs[*].tx``, ``paired_tx``, the transit legs), never a relationship (``Transaction.related_transaction``,
the only one, is lazy), there are no deferred columns, it reads only rows ``calculate()``'s own queries loaded, which
never commits, rolls back or expires, and no session enters the thread.

- ``TestTheReplayRunsOffTheEventLoop`` — red on HEAD 7e6cf7914, green after:
  * ``…on_a_portfolio_engine_worker``: ``build`` runs on a ``portfolio-engine_N`` thread, not the loop's. HEAD: on the
    loop's thread (``MainThread``);
  * ``…the_event_loop_keeps_running_during_a_replay``: ``build`` blocks its thread on a ``threading.Event`` that only a
    concurrent asyncio task sets, once it has run ``_TICKS`` loop iterations (``await asyncio.sleep(0)``) counted from
    the replay's start; only then does the real replay run. HEAD: the ticker cannot run while ``build`` holds the loop's
    thread; the wait times out after ``_RELEASE_TIMEOUT_S`` and the test fails on that, it never hangs.
- ``TestTheWorkerKeepsTheRequestContext`` — green on HEAD (``build`` runs in the request's own context there), a guard
  of ``copy_context().run``: an executor call without it hands the worker an empty context, and the replay's log lines
  stop masking the secrets in flight (``utils/runtime/secret_masking.py``) and would lose any structlog context bound.
- ``TestNoLazyLoadDuringTheReplay`` — green on HEAD and after:
  * the guard: during the replay — on a ``portfolio-engine`` thread, or on the thread running ``build`` (HEAD's loop) —
    any read of ``Transaction.related_transaction`` and any lazy load of a mapped attribute (the one funnel of SQLAlchemy's
    loaders, ``AttributeImpl._fire_loader_callables``: relationships, expired and deferred columns) raises
    ``_LazyReadInReplay`` and is recorded (in case the replay swallowed the exception). A ledger with a linked TRANSFER
    and CASH_TRANSFER in transit and a linked FX_CONVERSION, so ``paired_tx`` and the transit legs exist, replays
    without tripping it; every transaction the replay can reach is a persistent instance of the session, with every
    column loaded. Without the guard such a read is silent: both legs of a pair are in the session's identity map, so
    the lazy loader answers from it — on the worker thread. Mutation check: add ``_ = tx.related_transaction`` after
    ``tx = ctxn.tx`` in ``DailyStateBuilder.build``'s day loop; this test must fail naming that read;
  * ``…the_guard_trips…`` (pure): the guard's teeth, on a transient ``Transaction``.
- ``TestTheSameNumbersOnAnyThread`` (pure) — green on HEAD and after: the same ledger replayed on the loop's thread and,
  as the engine does it, in a worker through ``copy_context().run`` gives the same daily states, field by field and
  exponent by exponent (``_canonical``), the same other replay outputs, under the same ``decimal`` settings. The cost of
  3 units bought for 1000 and a KZT rate of 523.45678 make the figures depend on the decimal context.
  The ``native_cash_guard`` golden (``test_financial/test_native_cash_guard.py``) already pins the engine's numbers
  through the executor; it is not duplicated here.
- ``TestTheExecutorIsShutDownWithTheApp`` (pure; MF-J45a, the executor J-45 never shut down) — red on HEAD f252acb4a
  (no ``shutdown_engine_executor``, no ``_engine_executor``: both are looked up when the test runs, so the file still
  collects there), green after. ``shutdown_engine_executor()``, the app's ``portfolio-engine`` shutdown step
  (``test_app_lifecycle.py`` pins its place):
  * before any replay: no error, and no executor created;
  * with every worker held on a ``threading.Event`` and one more call queued behind them: the slot is emptied, the
    queued call cancelled (it never runs), the old executor refuses a new call (``RuntimeError``), and the shutdown
    returns while the held calls still run — it waits for none; released, they end normally;
  * after it, ``_engine_executor()`` creates a new executor, as bounded as the first, that runs a call on a
    ``portfolio-engine`` thread.

The ledger (the DB tests and, as transient instances, the parity test), dated 2093 so that its EUR/KZT rates are its own;
user U owns brokers A and B at 100 %, X is a EUR stock, read in EUR up to END:

- D0: DEPOSIT 10000 at A, DEPOSIT 1000 at B;  D1: BUY 3 X for 1000 at A; X closes 333.5;
- D2: TRANSFER of 1 X out of A (arrives at B on D4: in transit D2..D3); CASH_TRANSFER of 500 out of A (arrives at B on
  D3: in transit on D2);
- D3: FX_CONVERSION at A, 1000 EUR into 523456.78 KZT (1 EUR = 523.45678 KZT that day, 530.1 on END);
- D4: SELL 1 X for 340 at A; X closes 345.67.

Isolation: WRITE-SCOPED (the services default). Each DB test owns its user, brokers and asset (uuid names) and writes
through a session that is rolled back: nothing is committed. The EUR/KZT rates are global rows, written on 2093 days no
other test uses and never committed; R13-SEC7-1's bound is lifted for those days (``lift_range_bound``). Nothing counts a
collection the test does not own: the replay's inputs are read from the builder of the test's own calculation. The
engine's blob cache is emptied around each test (a cached blob would answer without a replay). The patches
(``DailyStateBuilder.build``, ``Transaction.related_transaction``, ``AttributeImpl._fire_loader_callables``) go through
``monkeypatch`` and are undone at teardown. The MF-J45a tests empty the executor slot (``_ENGINE_EXECUTOR``) through
``monkeypatch`` (``engine_executor_slot``): the executor an earlier calculation of the process created is neither used
nor shut down by them and is given back at teardown; every executor they create is shut down, its workers joined. No
server, no network; no wall-clock wait is an assertion (the ticker counts loop iterations; ``_RELEASE_TIMEOUT_S`` and
``_HOLD_TIMEOUT_S`` only bound a failure: the held workers wait for events, the test for futures).

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate, step 11; _engine_executor,
shutdown_engine_executor), backend/app/services/financial_math/portfolio/daily_state.py (DailyStateBuilder.build),
backend/app/services/platform/app_lifespan.py (SHUTDOWN_STEPS), LibreFolio_developer_journal/Release_2/Phase_1/
11_financialMath/plan-phase01FinancialMath.prompt.md («SEC7-1b», «J-45 = R13-SEC7-1b», «MF-J45a»).
"""

import asyncio
import contextvars
import dataclasses
import decimal
import sys
import threading
from collections.abc import Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
import structlog

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import _AttributeImpl as AttributeImpl  # private since SQLAlchemy 2.1

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.utils.runtime.secret_masking import active_secrets, secrets_in_flight
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash
from backend.test_scripts.test_services._range_bounds import lift_range_bound
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
KZT = "KZT"

D0 = date(2093, 3, 2)
D1 = date(2093, 3, 3)
D2 = date(2093, 3, 5)
D3 = date(2093, 3, 6)
D4 = date(2093, 3, 8)
END = date(2093, 3, 10)

#: The engine executor's thread_name_prefix: its threads are named portfolio-engine_0, portfolio-engine_1.
_ENGINE_THREAD_PREFIX = "portfolio-engine"
#: Loop iterations the ticker counts while the replay is held, before releasing it.
_TICKS = 5
#: How long a held replay waits for the ticker. On the cure the release comes after five loop iterations; on HEAD it
#: never comes (the loop's thread is the one waiting), and this bound turns the hang into a failure.
_RELEASE_TIMEOUT_S = 5.0
#: MF-J45a: the longest a worker held by a test waits for its release, and the longest the test waits for a call it
#: submitted. Only a failure reaches it: the release comes from the test's ``finally``, the calls end at once.
_HOLD_TIMEOUT_S = 10.0
#: A structlog context key the test binds (no request binds one today; logging_config's merge_contextvars would merge it).
_LOG_CONTEXT_KEY = "request_id"

# (label, broker, on X, type, day, quantity, amount, currency)
_ROWS = (
    ("dep_A", "A", False, TransactionType.DEPOSIT, D0, "0", "10000", EUR),
    ("dep_B", "B", False, TransactionType.DEPOSIT, D0, "0", "1000", EUR),
    ("buy_A", "A", True, TransactionType.BUY, D1, "3", "-1000", EUR),
    ("tr_out_A", "A", True, TransactionType.TRANSFER, D2, "-1", "0", None),
    ("ct_out_A", "A", False, TransactionType.CASH_TRANSFER, D2, "0", "-500", EUR),
    ("ct_in_B", "B", False, TransactionType.CASH_TRANSFER, D3, "0", "500", EUR),
    ("fx_out_A", "A", False, TransactionType.FX_CONVERSION, D3, "0", "-1000", EUR),
    ("fx_in_A", "A", False, TransactionType.FX_CONVERSION, D3, "0", "523456.78", KZT),
    ("tr_in_B", "B", True, TransactionType.TRANSFER, D4, "1", "0", None),
    ("sell_A", "A", True, TransactionType.SELL, D4, "-1", "340", EUR),
)
# Each pair points at each other: a TRANSFER and a CASH_TRANSFER in transit, a same-day FX_CONVERSION.
_LINKED_PAIRS = (("tr_out_A", "tr_in_B"), ("ct_out_A", "ct_in_B"), ("fx_out_A", "fx_in_A"))
# X's closes, in EUR.
_CLOSES = ((D1, "333.5"), (D4, "345.67"))
# 1 EUR = rate KZT from that day (base EUR < quote KZT, as FxRate's check requires).
_EUR_KZT = ((D3, "523.45678"), (END, "530.1"))

# The parity ledger's ids: no DB.
_PURE_BROKER_IDS = {"A": 10, "B": 20}
_PURE_ASSET_ID = 100

# The replay outputs compared by the parity test besides the daily states (the result's other fields are its inputs
# handed through, or set by the engine after the replay).
_REPLAY_OUTPUTS = ("position_states_start", "position_states_start_date", "position_states_end", "internal_asset_transfers", "end_state", "realized_sales", "missing_fx")


# =============================================================================
# THE LEDGER
# =============================================================================


@dataclass(frozen=True)
class _Book:
    user_id: int
    broker_ids: tuple[int, ...]
    asset_id: int


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


def _partners() -> dict[str, str]:
    """Each linked leg's label -> its partner's label."""
    return dict(_LINKED_PAIRS) | {right: left for left, right in _LINKED_PAIRS}


async def _ledger(session: AsyncSession, keep_alive: list[object]) -> _Book:
    """The module's ledger, owned by a new user: rows flushed, linked pairs pointing at each other, nothing committed."""
    tag = uuid4().hex[:12]
    user = User(username=f"j45_{tag}", email=f"j45_{tag}@test.com", hashed_password="fakehash", is_active=True)
    brokers = {label: Broker(name=f"J-45 off the loop {label} {tag}") for label in _PURE_BROKER_IDS}
    asset = Asset(display_name=f"J-45 off the loop X {tag}", currency=EUR, asset_type=AssetType.STOCK)
    await _persist(session, keep_alive, user, *brokers.values(), asset)
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()))
    await _persist(
        session,
        keep_alive,
        *(PriceHistory(asset_id=asset.id, date=day, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=Decimal("1"), currency=EUR, source_plugin_key="j45_off_the_loop_test") for day, close in _CLOSES),
        *(FxRate(date=day, base=EUR, quote=KZT, rate=Decimal(rate), source="TEST") for day, rate in _EUR_KZT),
    )
    rows = {label: Transaction(broker_id=brokers[broker].id, asset_id=asset.id if on_asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency) for label, broker, on_asset, tx_type, day, quantity, amount, currency in _ROWS}
    await _persist(session, keep_alive, *rows.values())
    # Both legs flushed first: the foreign key of related_transaction_id is deferred.
    for label, partner in _partners().items():
        rows[label].related_transaction_id = rows[partner].id
    await session.flush()
    return _Book(user_id=user.id, broker_ids=tuple(broker.id for broker in brokers.values()), asset_id=asset.id)


async def _calculate(session: AsyncSession, book: _Book) -> PortfolioCalculationResult:
    return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, date_to=END, target_currency=EUR)


def _transient_ledger() -> list[Transaction]:
    """The module's ledger as transient ``Transaction`` instances with ids of their own, in loading order (date, id)."""
    ids = {label: index for index, (label, *_rest) in enumerate(_ROWS, start=1)}
    partners = _partners()
    rows = [
        Transaction(
            id=ids[label],
            broker_id=_PURE_BROKER_IDS[broker],
            asset_id=_PURE_ASSET_ID if on_asset else None,
            type=tx_type,
            date=day,
            quantity=Decimal(quantity),
            amount=Decimal(amount),
            currency=currency,
            related_transaction_id=ids[partners[label]] if label in partners else None,
        )
        for label, broker, on_asset, tx_type, day, quantity, amount, currency in _ROWS
    ]
    return sorted(rows, key=lambda tx: (tx.date, tx.id))


def _kzt_rate_map() -> dict[tuple[str, str, date], Decimal]:
    """KZT -> EUR on every day from the first rate to END, each day at the last EUR/KZT rate on or before it."""
    rates: dict[tuple[str, str, date], Decimal] = {}
    day = _EUR_KZT[0][0]
    while day <= END:
        eur_kzt = [Decimal(rate) for since, rate in _EUR_KZT if since <= day][-1]
        rates[(KZT, EUR, day)] = Decimal("1") / eur_kzt
        day += timedelta(days=1)
    return rates


def _parity_builder() -> DailyStateBuilder:
    """A builder fed with the module's ledger as the engine would feed it (inputs built here, on the calling thread)."""
    scope = set(_PURE_BROKER_IDS.values())
    classification = ScopeAwareTransactionClassifier(scope, _transient_ledger(), dict.fromkeys(scope, Decimal("1"))).classify()
    classified = classification.classified
    asset_currencies = {_PURE_ASSET_ID: EUR}
    price_rows = [(day, Decimal(close), EUR) for day, close in _CLOSES]
    fx_rate_map = _kzt_rate_map()
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=classification.in_transit_intervals,
        external_cash_flows=classification.external_cash_flows,
        price_map={_PURE_ASSET_ID: price_rows},
        quote_base_map={_PURE_ASSET_ID: 1},
        fx_rate_map=fx_rate_map,
        asset_classifications={_PURE_ASSET_ID: None},
        asset_types={_PURE_ASSET_ID: "Stock"},
        asset_currencies=asset_currencies,
        average_costs=engine_average_costs(classified, asset_currencies=asset_currencies, target_currency=EUR, fx_rate_map=fx_rate_map, date_to=END),
        native_cash=engine_native_cash(classified, target_currency=EUR, fx_rate_map=fx_rate_map, date_to=END),
        target_currency=EUR,
        date_from=D0,
        date_to=END,
        mark_series={
            _PURE_ASSET_ID: build_asset_price_series(price_rows=price_rows, transactions=[ctxn.tx for ctxn in classified if ctxn.tx.asset_id == _PURE_ASSET_ID], split_linked_tx_ids=set(), asset_currency=EUR, quote_base_quantity=1),
        },
    )


# =============================================================================
# THE REPLAY, WRAPPED
# =============================================================================

_Around = Callable[[DailyStateBuilder, Callable[[], PortfolioCalculationResult]], PortfolioCalculationResult]


def _wrap_replay(monkeypatch: pytest.MonkeyPatch, around: _Around) -> None:
    """Replace ``DailyStateBuilder.build`` with ``around(builder, build)``, where ``build()`` runs the real replay.

    Patched on the class: the engine builds the class it imports, and resolves ``builder.build`` when it calls it."""
    assert portfolio_engine_module.DailyStateBuilder is DailyStateBuilder, "precondition: the engine builds daily_state.DailyStateBuilder"
    real_build = DailyStateBuilder.build

    def build(self: DailyStateBuilder) -> PortfolioCalculationResult:
        return around(self, lambda: real_build(self))

    monkeypatch.setattr(DailyStateBuilder, "build", build)


@dataclass
class _HeldReplay:
    """What a replay held by ``_hold_replay_until_ticked`` saw."""

    entered: bool = False
    released_in_time: bool = False
    ticks_when_released: int | None = None
    calculation_running_at_release: bool | None = None


async def _hold_replay_until_ticked(monkeypatch: pytest.MonkeyPatch, calculate: Callable[[], Awaitable[PortfolioCalculationResult]]) -> tuple[_HeldReplay, PortfolioCalculationResult]:
    """Run ``calculate()`` with its replay held on a ``threading.Event`` that a concurrent task sets after ``_TICKS``
    iterations of the event loop, counted from the moment the replay started; then the real replay runs.

    The held thread waits ``_RELEASE_TIMEOUT_S`` at most, so a replay holding the loop's own thread ends in a failed
    assertion instead of a hang."""
    loop = asyncio.get_running_loop()
    replay_started = asyncio.Event()
    release = threading.Event()
    ticks = [0]
    held = _HeldReplay()

    def hold(builder: DailyStateBuilder, build: Callable[[], PortfolioCalculationResult]) -> PortfolioCalculationResult:
        held.entered = True
        loop.call_soon_threadsafe(replay_started.set)
        held.released_in_time = release.wait(timeout=_RELEASE_TIMEOUT_S)
        held.ticks_when_released = ticks[0]
        return build()

    _wrap_replay(monkeypatch, hold)

    async def tick_then_release(calculation: asyncio.Future) -> None:
        started = asyncio.ensure_future(replay_started.wait())
        try:
            await asyncio.wait({started, calculation}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            started.cancel()
        if not replay_started.is_set():
            return  # the calculation ended without a replay: the caller's precondition says so
        for _ in range(_TICKS):
            await asyncio.sleep(0)
            ticks[0] += 1
        held.calculation_running_at_release = not calculation.done()
        release.set()

    calculation = asyncio.ensure_future(calculate())
    ticker = asyncio.ensure_future(tick_then_release(calculation))
    try:
        result = await calculation
        await ticker
    finally:
        release.set()  # never leave a worker of the shared executor waiting
        ticker.cancel()
    return held, result


# =============================================================================
# THE LAZY-READ GUARD
# =============================================================================


class _LazyReadInReplay(AssertionError):
    """The replay read ``Transaction.related_transaction`` or lazily loaded a mapped attribute."""


class _LazyReadGuard:
    """Trips on any read of ``Transaction.related_transaction`` and any lazy load of a mapped attribute made during the
    replay — on a thread of the engine's executor, or on the thread running ``build`` inside :meth:`replay` (HEAD's
    loop). A trip raises ``_LazyReadInReplay`` and is recorded in ``violations``, which the test also asserts empty: a
    replay that swallowed the exception would still be caught.

    Lazy loads all pass through ``AttributeImpl._fire_loader_callables`` (relationship loaders, expired and deferred
    columns); a value already in the instance's ``__dict__`` never does, hence the read guard on the relationship too."""

    def __init__(self) -> None:
        self.violations: list[str] = []
        self._local = threading.local()

    def replaying(self) -> bool:
        return getattr(self._local, "replaying", False) or threading.current_thread().name.startswith(_ENGINE_THREAD_PREFIX)

    @contextmanager
    def replay(self) -> Iterator[None]:
        """Mark the current thread as running the replay."""
        self._local.replaying = True
        try:
            yield
        finally:
            self._local.replaying = False

    def check(self, what: str) -> None:
        if self.replaying():
            message = f"{what} on thread {threading.current_thread().name!r} during the replay"
            self.violations.append(message)
            raise _LazyReadInReplay(message)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        guard = self
        fire_loader_callables = AttributeImpl._fire_loader_callables

        def guarded_fire_loader_callables(impl: AttributeImpl, state: Any, key: str, passive: Any) -> Any:
            guard.check(f"lazy load of {state.class_.__name__}.{key}")
            return fire_loader_callables(impl, state, key, passive)

        monkeypatch.setattr(AttributeImpl, "_fire_loader_callables", guarded_fire_loader_callables)
        monkeypatch.setattr(Transaction, "related_transaction", _ReadGuardedAttribute(Transaction.__dict__["related_transaction"], guard))


class _ReadGuardedAttribute:
    """A mapped attribute read through the guard: during the replay any read trips it, loaded or not; otherwise it
    behaves as the original ``InstrumentedAttribute`` (class access returns the original)."""

    def __init__(self, attribute: Any, guard: _LazyReadGuard) -> None:
        self._attribute = attribute
        self._guard = guard

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self._attribute
        self._guard.check(f"read of {type(instance).__name__}.{self._attribute.key}")
        return self._attribute.__get__(instance, owner)

    def __set__(self, instance: Any, value: Any) -> None:
        self._attribute.__set__(instance, value)

    def __delete__(self, instance: Any) -> None:
        self._attribute.__delete__(instance)


@dataclass(frozen=True)
class _ReplayReach:
    """The transactions a replay can reach (``tx``, ``paired_tx``, the transit legs), read from its builder."""

    paired_types: frozenset[TransactionType]
    transit_kinds: frozenset[str]
    not_persistent: tuple[str, ...]
    unloaded_columns: tuple[tuple[int | None, tuple[str, ...]], ...]


def _replay_reach(builder: DailyStateBuilder) -> _ReplayReach:
    """Read from the instances' state only (``sa_inspect``), so that collecting it can never load anything."""
    reachable: list[Transaction] = []
    for ctxn in builder.classified_txs:
        reachable.append(ctxn.tx)
        if ctxn.paired_tx is not None:
            reachable.append(ctxn.paired_tx)
    for interval in builder.in_transit_intervals:
        reachable += [interval.departure_leg, interval.arrival_leg]
    columns = {attribute.key for attribute in sa_inspect(Transaction).column_attrs}
    not_persistent: list[str] = []
    unloaded: list[tuple[int | None, tuple[str, ...]]] = []
    for tx in reachable:
        state = sa_inspect(tx)
        if not state.persistent:
            not_persistent.append(f"tx {state.dict.get('id')} ({'transient' if state.transient else 'pending' if state.pending else 'detached'})")
        missing = tuple(sorted(columns & (state.unloaded | state.expired_attributes)))
        if missing:
            unloaded.append((state.dict.get("id"), missing))
    return _ReplayReach(
        paired_types=frozenset(sa_inspect(ctxn.tx).dict.get("type") for ctxn in builder.classified_txs if ctxn.classification == "linked_internal" and ctxn.paired_tx is not None),
        transit_kinds=frozenset(interval.tx_type for interval in builder.in_transit_intervals),
        not_persistent=tuple(not_persistent),
        unloaded_columns=tuple(unloaded),
    )


# =============================================================================
# PARITY
# =============================================================================


def _canonical(value: Any) -> Any:
    """A comparable form that keeps every Decimal's exponent (Decimal("1.0") != Decimal("1.00") here), sets sorted."""
    if isinstance(value, Decimal):
        return ("Decimal", str(value))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (type(value).__name__, tuple((field.name, _canonical(getattr(value, field.name))) for field in dataclasses.fields(value)))
    if isinstance(value, dict):
        return ("dict", tuple((_canonical(key), _canonical(item)) for key, item in value.items()))
    if isinstance(value, set | frozenset):
        return ("set", tuple(sorted((_canonical(item) for item in value), key=repr)))
    if isinstance(value, list | tuple):
        return (type(value).__name__, tuple(_canonical(item) for item in value))
    return value


def _daily_state_differences(on_loop: list[DailyPortfolioState], in_worker: list[DailyPortfolioState]) -> list[str]:
    """Every field of every day that differs between the two replays."""
    if [state.date for state in on_loop] != [state.date for state in in_worker]:
        return [f"days: on the loop {[state.date for state in on_loop]}, in a worker {[state.date for state in in_worker]}"]
    problems: list[str] = []
    for left, right in zip(on_loop, in_worker, strict=True):
        for field in dataclasses.fields(DailyPortfolioState):
            left_value, right_value = getattr(left, field.name), getattr(right, field.name)
            if _canonical(left_value) != _canonical(right_value):
                problems.append(f"{left.date} {field.name}: on the loop {left_value!r}, in a worker {right_value!r}")
    return problems


def _decimal_settings() -> tuple:
    """The current thread's decimal context, as what changes a result: precision, rounding, exponent range, traps."""
    context = decimal.getcontext()
    return (context.prec, context.rounding, context.Emin, context.Emax, context.clamp, tuple(sorted(signal.__name__ for signal, on in context.traps.items() if on)))


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.fixture
def keep_alive() -> list[object]:
    """Strong references to every row the test flushes (see _persist)."""
    return []


@pytest_asyncio.fixture
async def book(session, keep_alive, monkeypatch) -> _Book:
    """The module's ledger, seeded for this test; R13-SEC7-1's bound lifted for its 2093 days."""
    lift_range_bound(monkeypatch)
    return await _ledger(session, keep_alive)


@pytest.fixture(autouse=True)
def no_cached_blob(request):
    """No engine blob crosses into or out of a test: a cached blob would answer without a replay."""
    portfolio_engine_module._portfolio_blob_cache.clear()
    request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)


@pytest.fixture
def engine_executor_slot(monkeypatch) -> Iterator[None]:
    """MF-J45a: the engine's executor slot (``_ENGINE_EXECUTOR``) empty for the test and given back after it, so the
    executor an earlier calculation of the process created is neither used nor shut down here. Whatever executor the test
    leaves in the slot is shut down at teardown, its workers joined (a test releases every worker it holds)."""
    monkeypatch.setattr(portfolio_engine_module, "_ENGINE_EXECUTOR", None)
    yield
    left_in_the_slot = portfolio_engine_module._ENGINE_EXECUTOR
    if left_in_the_slot is not None:
        left_in_the_slot.shutdown(wait=True, cancel_futures=True)


# =============================================================================
# 1-2 — RED ON HEAD: THE REPLAY RUNS OFF THE EVENT LOOP
# =============================================================================


class TestTheReplayRunsOffTheEventLoop:
    @pytest.mark.asyncio
    async def test_the_replay_runs_on_a_portfolio_engine_worker(self, session, book, monkeypatch):
        """``build`` runs on a ``portfolio-engine_N`` thread of the engine's executor. HEAD: on the loop's thread."""
        print_section("J-45: the replay's thread")
        threads: list[tuple[str, int | None]] = []

        def record_thread(builder: DailyStateBuilder, build: Callable[[], PortfolioCalculationResult]) -> PortfolioCalculationResult:
            current = threading.current_thread()
            threads.append((current.name, current.ident))
            return build()

        _wrap_replay(monkeypatch, record_thread)
        loop_thread = threading.current_thread()

        result = await _calculate(session, book)

        assert len(threads) == 1, f"precondition: an uncached calculation replays once, it replayed {len(threads)} times"
        assert result.daily_states, "precondition: the replay produced daily states"
        [(name, ident)] = threads
        assert ident != loop_thread.ident and name.startswith(_ENGINE_THREAD_PREFIX), f"the replay ran on thread {name!r} while the event loop runs on {loop_thread.name!r}: expected a worker named {_ENGINE_THREAD_PREFIX}_N"
        print_success(f"replayed on {name}")

    @pytest.mark.asyncio
    async def test_the_event_loop_keeps_running_during_a_replay(self, session, book, monkeypatch):
        """With the replay held until the loop has ticked ``_TICKS`` times, the loop ticks, the replay is released while
        the calculation is still running, and the real replay then completes. HEAD: no tick before the timeout."""
        print_section("J-45: the event loop during a replay")

        held, result = await _hold_replay_until_ticked(monkeypatch, lambda: _calculate(session, book))

        assert held.entered, "precondition: the calculation never replayed (a cached blob answered?)"
        released = held.released_in_time and held.ticks_when_released is not None and held.ticks_when_released >= _TICKS
        assert released, f"the replay waited {_RELEASE_TIMEOUT_S}s for the event loop to tick {_TICKS} times and saw {held.ticks_when_released} ticks: the loop did not run while the replay ran (it ran on the loop's thread)"
        assert held.calculation_running_at_release, "the loop ticked only after the calculation had finished"
        assert result.daily_states, "the replay, once released, produced daily states"
        print_success(f"the loop ticked {held.ticks_when_released} times during the replay")


# =============================================================================
# 5 — GREEN ON HEAD, A GUARD OF copy_context(): THE WORKER KEEPS THE REQUEST'S CONTEXT
# =============================================================================


class TestTheWorkerKeepsTheRequestContext:
    @pytest.mark.asyncio
    async def test_the_request_context_reaches_the_replay(self, session, book, monkeypatch):
        """A ``request_id`` bound in structlog's context and a secret in flight (``secrets_in_flight``, which masks it in
        every log line written in that context) before ``calculate`` are both in the replay's context. Green on HEAD
        (same thread, same context); after the cure only because the worker runs in a copy of the request's context."""
        print_section("J-45: the request's context in the replay")
        marker = f"j45-{uuid4().hex}"
        secret = f"j45-secret-{uuid4().hex}"
        seen: list[tuple[object, bool]] = []

        def read_context(builder: DailyStateBuilder, build: Callable[[], PortfolioCalculationResult]) -> PortfolioCalculationResult:
            seen.append((structlog.contextvars.get_contextvars().get(_LOG_CONTEXT_KEY, "<unbound>"), secret in active_secrets()))
            return build()

        _wrap_replay(monkeypatch, read_context)

        with structlog.contextvars.bound_contextvars(**{_LOG_CONTEXT_KEY: marker}), secrets_in_flight(frozenset({secret})):
            await _calculate(session, book)

        assert len(seen) == 1, f"precondition: an uncached calculation replays once, it replayed {len(seen)} times"
        [(log_context_value, secret_masked)] = seen
        assert log_context_value == marker, f"the replay's log context holds {_LOG_CONTEXT_KEY}={log_context_value!r}, the request bound {marker!r}"
        assert secret_masked, "the secret in flight is not in the replay's context: a line the replay logged would not mask it"
        print_success("request_id and the secret mask seen by the replay")


# =============================================================================
# 4 — GREEN ON HEAD AND AFTER: NO LAZY LOAD DURING THE REPLAY
# =============================================================================


class TestNoLazyLoadDuringTheReplay:
    @pytest.mark.asyncio
    async def test_a_replay_of_linked_pairs_reads_no_relationship_and_loads_nothing(self, session, book, monkeypatch):
        """With the guard on, the ledger's linked TRANSFER, CASH_TRANSFER and FX_CONVERSION replay without a read of
        ``related_transaction`` or a lazy load; every transaction the replay reaches is persistent, every column loaded."""
        print_section("J-45: no lazy load during the replay")
        guard = _LazyReadGuard()
        guard.install(monkeypatch)
        reached: list[_ReplayReach] = []

        def guarded(builder: DailyStateBuilder, build: Callable[[], PortfolioCalculationResult]) -> PortfolioCalculationResult:
            reached.append(_replay_reach(builder))
            with guard.replay():
                return build()

        _wrap_replay(monkeypatch, guarded)

        result = await _calculate(session, book)

        assert len(reached) == 1, f"precondition: an uncached calculation replays once, it replayed {len(reached)} times"
        [reach] = reached
        linked_types = {TransactionType.TRANSFER, TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION}
        assert linked_types <= reach.paired_types, f"precondition: linked internal legs with a paired_tx of every linked type, got {sorted(str(kind) for kind in reach.paired_types)}"
        assert {"asset", "cash"} <= reach.transit_kinds, f"precondition: an asset and a cash transit interval, got {sorted(reach.transit_kinds)}"
        assert reach.not_persistent == (), f"precondition: the replay reaches instances of the session, these are not: {reach.not_persistent}"
        assert reach.unloaded_columns == (), f"columns the replay could read are not loaded, a read would load them from its thread: {reach.unloaded_columns}"
        assert guard.violations == [], f"the replay read a relationship or loaded an attribute lazily: {guard.violations}"
        assert result.daily_states, "the replay produced daily states"
        print_success("no relationship read, no lazy load")

    def test_the_guard_trips_on_a_relationship_read_or_a_lazy_load_during_a_replay(self, monkeypatch):
        """The guard's teeth: off the replay a read passes through; on a ``portfolio-engine`` thread a read of the
        relationship and a load through the mapper's loader both trip it, and so does a read inside ``replay()``."""
        guard = _LazyReadGuard()
        guard.install(monkeypatch)
        tx = Transaction(id=1, broker_id=_PURE_BROKER_IDS["A"], asset_id=_PURE_ASSET_ID, type=TransactionType.TRANSFER, date=D2, quantity=Decimal("-1"), related_transaction_id=2)

        assert tx.related_transaction is None and guard.violations == [], "precondition: off the replay a read passes through"
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix=_ENGINE_THREAD_PREFIX) as worker:
            read = worker.submit(lambda: tx.related_transaction)
            loaded = worker.submit(lambda: sa_inspect(tx).attrs.related_transaction.value)
            read_error, loaded_error = read.exception(), loaded.exception()
        with guard.replay(), pytest.raises(_LazyReadInReplay):
            _ = tx.related_transaction

        assert isinstance(read_error, _LazyReadInReplay), f"a read of the relationship on a worker did not trip the guard: {read_error!r}"
        assert isinstance(loaded_error, _LazyReadInReplay), f"a lazy load through the mapper on a worker did not trip the guard: {loaded_error!r}"
        assert len(guard.violations) == 3, f"every trip is recorded: {guard.violations}"


# =============================================================================
# 3 — GREEN ON HEAD AND AFTER: THE SAME NUMBERS ON ANY THREAD
# =============================================================================


class TestTheSameNumbersOnAnyThread:
    @pytest.mark.asyncio
    async def test_the_replay_on_the_loop_equals_the_replay_in_a_worker(self):
        """The same inputs replayed on the loop's thread and in a worker (``copy_context().run``, as the engine does it):
        the same decimal settings, the same daily states field by field, the same other replay outputs."""
        print_section("J-45: the same numbers on the loop and in a worker")
        on_loop_builder, in_worker_builder = _parity_builder(), _parity_builder()
        seen: dict[str, tuple[str, tuple]] = {}

        def replay(where: str, builder: DailyStateBuilder) -> PortfolioCalculationResult:
            seen[where] = (threading.current_thread().name, _decimal_settings())
            return builder.build()

        on_loop = replay("loop", on_loop_builder)
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="j45-parity-worker") as worker:
            in_worker = await asyncio.get_running_loop().run_in_executor(worker, contextvars.copy_context().run, replay, "worker", in_worker_builder)

        assert seen["loop"][0] != seen["worker"][0], f"precondition: two threads, got {seen['loop'][0]!r} twice"
        assert on_loop.daily_states and on_loop.realized_sales, "precondition: the replay produced daily states and a realized sale"
        assert any(state.in_transit_market_value for state in on_loop.daily_states), "precondition: the ledger has value in transit"
        assert seen["worker"][1] == seen["loop"][1], f"decimal settings: on the loop {seen['loop'][1]}, in a worker {seen['worker'][1]}"
        problems = _daily_state_differences(on_loop.daily_states, in_worker.daily_states)
        problems += [f"{name}: on the loop {getattr(on_loop, name)!r}, in a worker {getattr(in_worker, name)!r}" for name in _REPLAY_OUTPUTS if _canonical(getattr(on_loop, name)) != _canonical(getattr(in_worker, name))]
        assert problems == [], "the replay differs between the loop and a worker:\n" + "\n".join(problems)
        print_success(f"{len(on_loop.daily_states)} days identical")


# =============================================================================
# 6 — RED ON HEAD f252acb4a (MF-J45a): THE EXECUTOR IS SHUT DOWN WITH THE APP
# =============================================================================


def _engine_function(name: str) -> Callable[[], Any]:
    """``engine.<name>``, looked up when the test runs: HEAD f252acb4a has neither function, and the file still collects."""
    function = getattr(portfolio_engine_module, name, None)
    assert callable(function), f"MF-J45a: engine.{name}() is missing: the engine's executor is not created on first use and shut down with the app"
    return function


class TestTheExecutorIsShutDownWithTheApp:
    def test_a_shutdown_before_any_replay_does_nothing(self, engine_executor_slot):
        """No executor created yet (the app stops before any report): the shutdown raises nothing and creates none."""
        print_section("MF-J45a: a shutdown before any replay")
        shutdown_engine_executor = _engine_function("shutdown_engine_executor")
        assert portfolio_engine_module._ENGINE_EXECUTOR is None, "precondition: no executor in the slot"

        shutdown_engine_executor()

        assert portfolio_engine_module._ENGINE_EXECUTOR is None, f"the shutdown left an executor in the slot: {portfolio_engine_module._ENGINE_EXECUTOR!r}"
        print_success("nothing to shut down, nothing created")

    def test_a_shutdown_cancels_a_queued_replay_refuses_a_new_one_and_waits_for_none(self, engine_executor_slot):
        """Every worker of the engine's executor held on a ``threading.Event``, one more call queued behind them: the
        shutdown empties the slot, cancels the queued call, makes the executor refuse a new one, and returns while the
        held calls still run; released, they end normally and the cancelled call never runs."""
        print_section("MF-J45a: a shutdown with every worker busy and a replay queued")
        engine_executor, shutdown_engine_executor = _engine_function("_engine_executor"), _engine_function("shutdown_engine_executor")
        executor = engine_executor()
        assert portfolio_engine_module._ENGINE_EXECUTOR is executor, "precondition: _engine_executor() keeps the executor it creates in the slot"
        workers = executor._max_workers
        started = [threading.Event() for _ in range(workers)]
        releases = [threading.Event() for _ in range(workers)]
        queued_ran = threading.Event()

        def held(index: int) -> bool:
            started[index].set()
            return releases[index].wait(timeout=_HOLD_TIMEOUT_S)

        try:
            running = [executor.submit(held, index) for index in range(workers)]
            assert all(event.wait(timeout=_HOLD_TIMEOUT_S) for event in started), f"precondition: each of the {workers} workers holds a call"
            queued = executor.submit(queued_ran.set)
            assert not queued.running() and not queued.done(), "precondition: with every worker held, the call waits in the queue"

            shutdown_engine_executor()

            # Sampled before anything else: the held calls are released only in the finally below.
            held_still_running = [future.running() for future in running]
            assert portfolio_engine_module._ENGINE_EXECUTOR is None, "the shutdown left the executor in the slot: the next calculation would submit to a shut-down executor"
            assert queued.cancelled(), f"the replay queued behind the busy workers was not cancelled ({queued!r}): it would run after the app's shutdown"
            with pytest.raises(RuntimeError, match="after shutdown"):
                executor.submit(lambda: None)
            assert all(held_still_running), f"the shutdown returned once the running calls had ended (running: {held_still_running}): it waited for them"
        finally:
            for release in releases:
                release.set()
        assert [future.result(timeout=_HOLD_TIMEOUT_S) for future in running] == [True] * workers, "a held call was not released by the test: it timed out instead"
        assert not queued_ran.is_set(), "the cancelled call ran all the same"
        executor.shutdown(wait=True)  # its workers joined: no thread outlives the test
        print_success(f"{workers} running calls ended in their threads, the queued one cancelled, a new one refused")

    def test_after_a_shutdown_the_next_use_creates_a_new_live_executor(self, engine_executor_slot):
        """After a shutdown (a test app stopped, a restart in the same process) ``_engine_executor()`` creates a new
        executor, as bounded as the first, kept in the slot, that runs a call on a ``portfolio-engine`` thread."""
        print_section("MF-J45a: the executor after a shutdown")
        engine_executor, shutdown_engine_executor = _engine_function("_engine_executor"), _engine_function("shutdown_engine_executor")
        first = engine_executor()
        assert engine_executor() is first, "precondition: until a shutdown, every use gets the same executor"

        shutdown_engine_executor()
        after = engine_executor()

        assert after is not first, "after a shutdown _engine_executor() handed back the executor that was shut down"
        assert portfolio_engine_module._ENGINE_EXECUTOR is after and engine_executor() is after, "the new executor is not the one kept in the slot"
        assert after._max_workers == first._max_workers, f"the new executor has {after._max_workers} workers, the first {first._max_workers}: J-45's bound is lost"
        thread_name = after.submit(lambda: threading.current_thread().name).result(timeout=_HOLD_TIMEOUT_S)
        assert thread_name.startswith(_ENGINE_THREAD_PREFIX), f"the new executor ran a call on {thread_name!r}: expected a worker named {_ENGINE_THREAD_PREFIX}_N"
        print_success(f"a new executor, its call on {thread_name}")

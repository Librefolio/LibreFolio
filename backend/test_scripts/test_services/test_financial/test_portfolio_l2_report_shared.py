"""MF-J45c (workstream MF) — the report the portfolio's Layer-2 cache shares stays read-only for its consumers.

What it guards. ``PortfolioService.get_report`` (``backend/app/services/portfolio_service.py``) keeps its answers in
``_portfolio_l2_cache`` (``get_ttl_cache("portfolio_layer2")``). On a miss it stores the ``PortfolioReportResponse`` it
built and returns that object; on a hit it returns the stored object as it is (``return cached``). One Pydantic object
therefore goes to every request with the same key — and to every AI Export component of a request, which memoizes it.
A consumer that wrote into it (a ``.sort()``, an ``append``, a field assignment, a nested Decimal rewritten with another
exponent) would silently change the answer of every later request with that key. No such write has been seen: this is
a guard (green on HEAD 5af05312b), the J45b idea (``test_portfolio_engine/test_engine_single_flight.py``,
``TestTheSharedResultIsNotMutatedByItsConsumers``, which guards the ENGINE's blob-cached dataclass) applied to the L2
cached Pydantic report.

- ``TestTheCachedReportIsShared`` — the precondition: two ``get_report`` calls with the same query return the SAME
  object (``is``), the one the cache holds under the key it was stored with (read back from the cache itself).
- ``TestTheCachedReportIsNotMutatedByItsConsumers`` — the guard. ``_L2Watch`` records every report stored in L2, with a
  deep structural snapshot taken as it is stored, every ``get_report`` call (its consumer, the code that called it, the
  object returned, whether it came from L2), and every report an AI Export component received from its request's
  memoized resource. Two passes run every consumer: the first stores each consumer's own key (after an explicit prime
  with every include flag), the second must be served from L2 for every call. After each consumer every stored report is
  snapshotted again: a difference is reported with the consumer after which it appeared and the path that moved. The
  consumers: ``POST /portfolio/report`` (the real route on an app of the test's own, FastAPI's serialization included),
  ``RiskService.execute`` on portfolio scopes (historical whole portfolio, current composition on a broker, a historical
  slice; every analytic a portfolio supports but the two that run in spawned processes, simulation and
  portfolio_optimization: ``risk/scope.py::load_scope_inputs`` and what reads its ``ScopeInputs``, whose data quality
  object the results carry as is), the AI Export through its real entry
  point (``AiExportSnapshotService.build_snapshot``, every public dataset of the four domains) and every component of
  each domain resolved on one request context (``BuildContext.resolve``: internal-only components included; their
  drawdowns reach ``get_report`` through ``RiskService``), and ``model_dump`` / ``model_dump_json`` /
  ``jsonable_encoder`` on every stored report.
- ``TestTheSnapshotSeesAWrite`` — the guard's teeth, on ``model_copy(deep=True)`` of a real report: a Decimal rewritten
  with another exponent only, a list append, a list reordered, a nested field set — each changes the snapshot at the
  path written; and pure: a dict entry set, added or reordered, a field rebound to an equal value (the fields-set moves)
  change it too; an object it cannot compare raises at its path instead of being skipped.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): user U owns brokers A and B at 100 %; X is a EUR stock,
Y a USD stock; read in EUR over START..END (2024-03-01..2024-04-12):

- D0 03-04: DEPOSIT 10000 at A, 1000 at B;  D1 03-05: BUY 3 X for 1000 at A, BUY 1 X for 333.5 at B;
- D3 03-08: FX_CONVERSION at A, 1000 EUR into 1090 USD; BUY 2 Y for 500 USD at A;
- D4 03-11: SELL 1 X for 340 at A; DIVIDEND 12 on X, FEE 3 at A.

A close on every weekday, X from D1 and Y (USD) from D3 to 04-11: more than the 20 observations a risk analytic needs, so
the risk consumers compute instead of stopping at «insufficient history». EUR/USD 1.09, 1.1 (D3, D5). The report with
every include flag has a summary with holdings and broker breakdown, history, allocation history, positions
contribution, broker P&L history, P&L candles, income, cost and deposit history and acquisition funding (asserted).

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. Every request opens
its own session on the test's private file. The L2, WAC and engine blob caches (process-global) are emptied before and
after each test; the market holiday table is an empty one (built for real it takes a QuantLib process); every patch goes
through ``monkeypatch``. No sleep, no wall-clock assertion.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_portfolio_l2_report_shared``.

Reference: backend/app/services/portfolio_service.py (_portfolio_l2_cache; get_report: the L2 check, ``return cached``,
``_portfolio_l2_cache.set``), LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/
plan-phase01FinancialMath.prompt.md («MF-J45c»).
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.api.v1 import portfolio_api
from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportAssetSnapshotRequest,
    AiExportBrokerSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportFxSnapshotRequest,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery, PortfolioReportResponse
from backend.app.schemas.risk import RiskQueryRequest, RiskResultStatus
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.ai_export.components.types import Domain
from backend.app.services.ai_export.datasets.catalog import PUBLIC_DATASETS
from backend.app.services.ai_export.datasets.spec import DatasetSpec
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.ai_export.runtime_service import AiExportSnapshotService
from backend.app.services.assets import price_query
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.service import RiskService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"

START = date(2024, 3, 1)
D0 = date(2024, 3, 4)
D1 = date(2024, 3, 5)
D3 = date(2024, 3, 8)
D4 = date(2024, 3, 11)
D5 = date(2024, 3, 12)
LAST_CLOSE = date(2024, 4, 11)
END = date(2024, 4, 12)

# (label, broker, asset, type, day, quantity, amount, currency)
_ROWS = (
    ("dep_A", "A", None, TransactionType.DEPOSIT, D0, "0", "10000", EUR),
    ("dep_B", "B", None, TransactionType.DEPOSIT, D0, "0", "1000", EUR),
    ("buy_X_A", "A", "X", TransactionType.BUY, D1, "3", "-1000", EUR),
    ("buy_X_B", "B", "X", TransactionType.BUY, D1, "1", "-333.5", EUR),
    ("fx_out", "A", None, TransactionType.FX_CONVERSION, D3, "0", "-1000", EUR),
    ("fx_in", "A", None, TransactionType.FX_CONVERSION, D3, "0", "1090", USD),
    ("buy_Y", "A", "Y", TransactionType.BUY, D3, "2", "-500", USD),
    ("sell_X", "A", "X", TransactionType.SELL, D4, "-1", "340", EUR),
    ("div_X", "A", "X", TransactionType.DIVIDEND, D4, "0", "12", EUR),
    ("fee_A", "A", None, TransactionType.FEE, D4, "0", "-3", EUR),
)
_LINKED_PAIRS = (("fx_out", "fx_in"),)


def _weekday_closes(asset: str, first: date, base: str, currency: str) -> tuple[tuple[str, date, Decimal, str], ...]:
    """(asset, day, close, currency) on every weekday from ``first`` to LAST_CLOSE, a different close each day."""
    days = [first + timedelta(days=offset) for offset in range((LAST_CLOSE - first).days + 1)]
    return tuple((asset, day, Decimal(base) + Decimal(index % 7) / 2 + Decimal(index) / 4, currency) for index, day in enumerate(day for day in days if day.weekday() < 5))


_CLOSES = (*_weekday_closes("X", D1, "333.5", EUR), *_weekday_closes("Y", D3, "250", USD))
# 1 EUR = rate USD from that day (base EUR < quote USD, as FxRate's check requires)
_EUR_USD = ((D3, "1.09"), (D5, "1.1"))

#: Every include flag of PortfolioReportQuery, all on in the primed queries.
_EVERY_INCLUDE_FLAG = (
    "include_summary",
    "include_history",
    "include_allocation_history",
    "include_breakdown",
    "include_positions_contribution",
    "include_broker_pnl_history",
    "include_pnl_candles",
    "include_income_history",
    "include_cost_history",
    "include_deposit_history",
    "include_acquisition_funding",
)
#: The code that calls get_report (module.qualname of the caller's frame): each must be reached, and served from L2.
_EXPECTED_CALL_SITES = frozenset(
    {
        "backend.app.api.v1.portfolio_api.get_portfolio_report",
        "backend.app.services.risk.scope.load_scope_inputs",
        "backend.app.services.ai_export.components.payloads.portfolio_broker.load_portfolio_report.<locals>._loader",
        "backend.app.services.ai_export.components.asset_resources.load_asset_report.<locals>._load",
        "backend.app.services.ai_export.components.fx_core._load_exposure_report.<locals>._loader",
    }
)
#: The AI Export components handed the shared report by their request's memoized resource (portfolio.report,
#: broker.report, broker.whole_portfolio_report, asset.core.report, fx_core.exposure_report), at HEAD 5af05312b: each must
#: be handed an object L2 stored. A component that stops reading the report leaves this list; one that starts is run
#: anyway (every component of each domain is) and joins it.
_EXPECTED_READERS = frozenset(
    {
        "portfolio.summary",
        "portfolio.positions",
        "portfolio.allocations_cash",
        "portfolio.performance",
        "portfolio.flows_income",
        "portfolio.fees_taxes",
        "portfolio.reconciliation",
        "portfolio.technical_coverage",
        "portfolio.technical_prices",
        "broker.summary",
        "broker.positions",
        "broker.allocation_concentration",
        "broker.performance",
        "broker.flows_income_costs",
        "broker.reconciliation",
        "broker.concentration_context",
        "broker.concentration_comparison",
        "broker.cost_efficiency",
        "broker.technical_coverage",
        "broker.technical_prices",
        "asset.position_scope",
        "asset.positions_by_broker",
        "asset.cost_value_pl",
        "asset.performance",
        "fx.exposure_base_quote",
    }
)
#: The AI Export components whose drawdown reaches get_report through RiskService (risk/scope.py): each must be served
#: from L2.
_EXPECTED_RISK_READERS = frozenset({"portfolio.drawdown_summary", "broker.drawdown_summary"})
#: The guard's message shows this many moved paths at most (a reorder moves every field of every row it touches).
_SHOWN_LINES = 25


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
        user = User(username=f"j45c_{tag}", email=f"j45c_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"J-45c shared report {label} {tag}") for label in ("A", "B")}
        assets = {
            "X": Asset(display_name=f"J-45c shared report X {tag}", currency=EUR, asset_type=AssetType.STOCK),
            "Y": Asset(display_name=f"J-45c shared report Y {tag}", currency=USD, asset_type=AssetType.STOCK),
        }
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])
        session.add_all(
            [
                *(PriceHistory(asset_id=assets[asset].id, date=day, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=currency, source_plugin_key="j45c_shared_report_test") for asset, day, close, currency in _CLOSES),
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
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'j45c_shared_report.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


def _full_query(book: _Book, *, broker_labels: tuple[str, ...] | None = None) -> PortfolioReportQuery:
    """Every include flag on, over START..END in EUR, for every accessible broker or the brokers named."""
    broker_ids = [book.broker_ids[label] for label in broker_labels] if broker_labels else None
    return PortfolioReportQuery(broker_ids=broker_ids, date_range=OpenDateRangeModel(start=START, end=END), target_currency=EUR, **dict.fromkeys(_EVERY_INCLUDE_FLAG, True))


async def _report(book: _Book, query: PortfolioReportQuery) -> PortfolioReportResponse:
    """One request: its own session on the book's file, as each HTTP request has its own."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


# =============================================================================
# THE SNAPSHOT — a structural, comparable copy of a report
# =============================================================================


class _UnsnapshottableValue(TypeError):
    """``_snapshot`` met a value it cannot compare structurally: extend it rather than skip the value."""


@dataclass(frozen=True)
class _Node:
    """A container in a snapshot: its kind, its type, and its entries as (label, snapshot) in their order."""

    kind: str
    type_name: str
    children: tuple[tuple[str, Any], ...]


def _leaf(value: Any) -> tuple | None:
    """A scalar's snapshot (a Decimal keeps its exponent, a float its exact bits), or None for a container."""
    if isinstance(value, Decimal):
        return ("Decimal", value.as_tuple())
    if isinstance(value, enum.Enum):  # before str and int: a StrEnum is a str
        return ("enum", type(value).__qualname__, value.name)
    if value is None or isinstance(value, bool | int | str):
        return (type(value).__name__, value)
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, datetime):  # before date: a datetime is a date
        return ("datetime", value.isoformat())
    if isinstance(value, date):
        return ("date", value.isoformat())
    return None


def _snapshot(value: Any, path: str = "report", _stack: frozenset[int] = frozenset()) -> Any:
    """A structural, comparable copy of ``value``: every Pydantic field (and its fields-set, extras and private
    attributes), every dataclass field, every mapping in insertion order, every sequence, sets sorted, a Decimal with its
    exponent. Unknown types raise, never skip."""
    leaf = _leaf(value)
    if leaf is not None:
        return leaf
    if id(value) in _stack:
        return ("cycle", type(value).__qualname__)
    stack = _stack | {id(value)}
    if isinstance(value, BaseModel):
        return _Node("model", type(value).__qualname__, _model_children(value, path, stack))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _Node("dataclass", type(value).__qualname__, tuple(_attribute_child(value, field_.name, path, stack) for field_ in dataclasses.fields(value)))
    if isinstance(value, Mapping):
        entries = ((key, item, f"[{key!r}]") for key, item in value.items())
        return _Node("mapping", type(value).__qualname__, tuple((label, _Node("entry", "", (("<key>", _snapshot(key, f"{path}<key>", stack)), ("<value>", _snapshot(item, f"{path}{label}", stack))))) for key, item, label in entries))
    if isinstance(value, set | frozenset):
        items = sorted((_snapshot(item, f"{path}{{}}", stack) for item in value), key=repr)
        return _Node(type(value).__name__, "", tuple((f"{{{index}}}", item) for index, item in enumerate(items)))
    if isinstance(value, list | tuple):
        return _Node(type(value).__name__, "", tuple((f"[{index}]", _snapshot(item, f"{path}[{index}]", stack)) for index, item in enumerate(value)))
    raise _UnsnapshottableValue(f"{path}: cannot snapshot a {type(value).__qualname__}")


def _model_children(value: BaseModel, path: str, stack: frozenset[int]) -> tuple[tuple[str, Any], ...]:
    """Every field in ``model_fields`` (read on the class), the fields-set (``exclude_unset`` reads it), then any extras
    and private attributes."""
    children = [_attribute_child(value, name, path, stack) for name in type(value).model_fields]
    children.append(("<fields_set>", ("fields_set", tuple(sorted(value.model_fields_set)))))
    for label, extra in (("<extra>", value.model_extra), ("<private>", value.__pydantic_private__)):
        if extra:
            children.append((label, _snapshot(dict(extra), f"{path}{label}", stack)))
    return tuple(children)


def _attribute_child(value: Any, name: str, path: str, stack: frozenset[int]) -> tuple[str, Any]:
    """One field as (label, snapshot); a field never set is marked, not skipped."""
    try:
        item = getattr(value, name)
    except AttributeError:
        return (f".{name}", ("unset",))
    return (f".{name}", _snapshot(item, f"{path}.{name}", stack))


def _show(snapshot: Any) -> str:
    if isinstance(snapshot, _Node):
        return f"<{snapshot.kind} {snapshot.type_name} of {len(snapshot.children)}>".replace("  ", " ")
    if snapshot[0] == "Decimal":
        return f"Decimal('{Decimal(snapshot[1])}')"
    shown = repr(snapshot)
    return shown if len(shown) <= 160 else f"{shown[:157]}..."


def _join(path: str, label: str) -> str:
    return f"{path}{label}" if label[:1] in ".[{" else f"{path} {label}"


def _differences(before: Any, after: Any, path: str = "report") -> list[str]:
    """Every path at which two snapshots differ, each with what it was and what it became."""
    if before == after:
        return []
    if isinstance(before, _Node) and isinstance(after, _Node) and (before.kind, before.type_name) == (after.kind, after.type_name):
        old, new = dict(before.children), dict(after.children)
        lines = []
        if list(old) != list(new):
            added, removed = [label for label in new if label not in old], [label for label in old if label not in new]
            lines.append(f"{path}: {len(old)} entries became {len(new)} (added {added}, removed {removed})" if added or removed else f"{path}: entries reordered")
        for label, item in old.items():
            if label in new:
                lines.extend(_differences(item, new[label], _join(path, label)))
        return lines
    return [f"{path}: {_show(before)} -> {_show(after)}"]


# =============================================================================
# THE WATCH — what L2 stores, who asks for it, who is handed it
# =============================================================================

#: The consumer a call is made for (set by the test around each one).
_CONSUMER: ContextVar[str | None] = ContextVar("mf_j45c_consumer", default=None)
#: The AI Export component being resolved, if any.
_COMPONENT: ContextVar[str | None] = ContextVar("mf_j45c_component", default=None)
#: The object L2 served (a hit) inside the get_report call running in this context.
_SERVED: ContextVar[object | None] = ContextVar("mf_j45c_served", default=None)


@dataclass(eq=False)
class _Stored:
    key: Any
    report: PortfolioReportResponse
    snapshot: Any
    label: str
    description: str


@dataclass(frozen=True, eq=False)
class _Call:
    consumer: str | None
    component: str | None
    site: str
    report: PortfolioReportResponse
    from_l2: bool


@dataclass(frozen=True, eq=False)
class _Receipt:
    consumer: str | None
    component: str | None
    resource: str
    report: PortfolioReportResponse


@dataclass(eq=False)
class _L2Watch:
    """Every report ``get_report`` stored in L2 (snapshotted as stored), every call and every AI Export receipt.

    ``consumer(label)`` runs one consumer under ``label`` and, when it ends, snapshots every stored report again: a path
    that moved is recorded once, with the consumer after which it first appeared (``moved``)."""

    stored: list[_Stored] = field(default_factory=list)
    calls: list[_Call] = field(default_factory=list)
    receipts: list[_Receipt] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> _L2Watch:
        cache = portfolio_service_module._portfolio_l2_cache
        real_get, real_set = cache.get, cache.set
        real_get_report, real_db_resource, real_resolve = PortfolioService.get_report, BuildContext.db_resource, BuildContext.resolve
        watch = self

        def get(key: Any) -> tuple[Any, bool]:
            value, hit = real_get(key)
            if hit:
                _SERVED.set(value)
            return value, hit

        def set_(key: Any, value: Any, **kwargs: Any) -> None:
            metadata = value.metadata
            description = f"brokers {metadata.broker_ids or 'all'}, {metadata.requested_date_from}..{metadata.requested_date_to}, {'+'.join(metadata.included_features)}; stored for «{_CONSUMER.get()}»"
            watch.stored.append(_Stored(key=key, report=value, snapshot=_snapshot(value), label=f"report#{len(watch.stored)}", description=description))
            real_set(key, value, **kwargs)

        async def get_report(service: PortfolioService, *args: Any, **kwargs: Any) -> PortfolioReportResponse:
            caller = inspect.currentframe().f_back  # the frame that awaits get_report
            site = f"{caller.f_globals['__name__']}.{caller.f_code.co_qualname}"
            token = _SERVED.set(None)
            try:
                report = await real_get_report(service, *args, **kwargs)
                served = _SERVED.get()
            finally:
                _SERVED.reset(token)
            watch.calls.append(_Call(consumer=_CONSUMER.get(), component=_COMPONENT.get(), site=site, report=report, from_l2=served is not None and served is report))
            return report

        async def db_resource(context: BuildContext, key: Any, loader: Callable[[AsyncSession], Any]) -> Any:
            value = await real_db_resource(context, key, loader)
            if isinstance(value, PortfolioReportResponse):
                watch.receipts.append(_Receipt(consumer=_CONSUMER.get(), component=_COMPONENT.get(), resource=key.name, report=value))
            return value

        async def resolve(context: BuildContext, component_id: str, *, required: bool) -> Any:
            token = _COMPONENT.set(component_id)
            try:
                return await real_resolve(context, component_id, required=required)
            finally:
                _COMPONENT.reset(token)

        monkeypatch.setattr(cache, "get", get)
        monkeypatch.setattr(cache, "set", set_)
        monkeypatch.setattr(PortfolioService, "get_report", get_report)
        monkeypatch.setattr(BuildContext, "db_resource", db_resource)
        monkeypatch.setattr(BuildContext, "resolve", resolve)
        return self

    def holds(self, report: object) -> bool:
        return any(stored.report is report for stored in self.stored)

    def legend(self, lines: list[str]) -> str:
        """Which stored report each ``report#i`` in ``lines`` is."""
        named = [stored for stored in self.stored if any(line.startswith(f"{stored.label}.") or f": {stored.label}." in line for line in lines)]
        return "\n".join(f"  {stored.label}: {stored.description}" for stored in named)

    def changes(self) -> list[str]:
        """Every path of every stored report that differs from its snapshot at storage."""
        return [line for stored in self.stored for line in _differences(stored.snapshot, _snapshot(stored.report), stored.label)]

    @contextmanager
    def consumer(self, label: str) -> Iterator[None]:
        token = _CONSUMER.set(label)
        try:
            yield
        finally:
            _CONSUMER.reset(token)
        for line in self.changes():
            if line not in self.seen:
                self.seen.add(line)
                self.moved.append(f"after «{label}»: {line}")


# =============================================================================
# THE CONSUMERS
# =============================================================================


async def _api_report(book: _Book, watch: _L2Watch) -> None:
    """``POST /api/v1/portfolio/report`` with every include flag, in process: the real portfolio router on an app of the
    call's own (the app mounts it under /api/v1), its session and user dependencies overridden with the book's; FastAPI
    validates and serializes the returned report as it answers. The answer must be the stored report, as JSON."""

    async def session_for_request() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            yield session

    user = User(id=book.user_id, username="j45c_route", email="j45c_route@test.com", hashed_password="fakehash", is_active=True)
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(portfolio_api.portfolio_router, prefix="/api/v1")
    app.dependency_overrides[portfolio_api.get_session_generator] = session_for_request
    app.dependency_overrides[portfolio_api.get_current_user] = lambda: user
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mf-j45c.test") as client:
        response = await client.post("/api/v1/portfolio/report", json=_full_query(book).model_dump(mode="json"))
    assert response.status_code == 200, f"POST /portfolio/report answered {response.status_code}: {response.text[:500]}"
    (served,) = [call.report for call in watch.calls if call.consumer == _CONSUMER.get() and call.site.endswith("portfolio_api.get_portfolio_report")]
    assert response.json() == served.model_dump(mode="json"), "the route answers the report get_report returned, as JSON"


def _risk_bodies(book: _Book) -> dict[str, dict[str, Any]]:
    """``POST /risk/query``'s bodies on portfolio scopes: every analytic a portfolio supports in each mode, but the two
    that run in spawned processes (simulation, portfolio_optimization: they read the same execution context)."""
    common = {"date_range": {"start": START.isoformat(), "end": END.isoformat()}, "target_currency": EUR}
    comparison = {"instance_id": "cmp", "analytic_code": "comparison", "parameters": {"comparison_asset_id": book.asset_ids["X"]}}
    replay = {"instance_id": "replay", "analytic_code": "stress", "parameters": {"method": "historical_replay", "replay_range": common["date_range"]}}
    shared = [{"instance_id": code, "analytic_code": code} for code in ("historical_kpi", "historical_var", "correlation")]
    return {
        "risk: historical, whole portfolio": {**common, "scope": {"kind": "portfolio"}, "mode": "historical", "analytics": [*shared, comparison, {"instance_id": "dd", "analytic_code": "drawdown_summary"}]},
        "risk: current composition, broker A": {
            **common,
            "scope": {"kind": "portfolio", "broker_ids": [book.broker_ids["A"]]},
            "mode": "current_composition",
            "composition_policy": "current_buy_and_hold",
            "analytics": [*shared, comparison, replay, {"instance_id": "rc", "analytic_code": "risk_contribution"}, {"instance_id": "arr", "analytic_code": "asset_risk_return"}],
        },
        "risk: historical, slice X": {**common, "scope": {"kind": "portfolio", "asset_ids": [book.asset_ids["X"]]}, "mode": "historical", "analytics": [{"instance_id": "kpi", "analytic_code": "historical_kpi"}, {"instance_id": "dd", "analytic_code": "drawdown_summary"}]},
    }


async def _risk(book: _Book, body: dict[str, Any]) -> None:
    """``POST /risk/query``'s service on the book, its response serialized as the route answers it."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        response = await RiskService(session).execute(user_id=book.user_id, request=RiskQueryRequest.model_validate(body))
    not_computed = [(item.instance_id, item.status.value, item.error.code.value if item.error else None) for item in response.items if item.status not in (RiskResultStatus.OK, RiskResultStatus.PARTIAL)]
    assert response.items and not not_computed, f"precondition: every analytic computes on the book ({body['scope']}): {not_computed}"
    response.model_dump(mode="json")


def _snapshot_request(book: _Book, dataset: DatasetSpec) -> Any:
    """``POST /ai-export/snapshot``'s body for ``dataset``: the period START..END in EUR; broker A, asset X, pair EUR/USD."""
    common = {
        "selection": AiExportDatasetSelection(kind="dataset", id=dataset.dataset_id, version=dataset.version),
        "detail_level": AiExportDetailLevel.STANDARD,
        "period": {"start": START, "end": END},
        "target_currency": EUR,
        "expected_catalog_version": AI_EXPORT_CATALOG_VERSION,
    }
    if dataset.domain is Domain.PORTFOLIO:
        return AiExportPortfolioSnapshotRequest(domain="portfolio", **common)
    if dataset.domain is Domain.BROKER:
        return AiExportBrokerSnapshotRequest(domain="broker", broker_id=book.broker_ids["A"], **common)
    if dataset.domain is Domain.ASSET:
        return AiExportAssetSnapshotRequest(domain="asset", asset_id=book.asset_ids["X"], **common)
    return AiExportFxSnapshotRequest(domain="fx", base_currency=EUR, quote_currency=USD, **common)


async def _ai_export_snapshot(book: _Book, dataset: DatasetSpec) -> None:
    """The AI Export's real entry point (``build_snapshot``) for one public dataset, its response serialized."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        response = await AiExportSnapshotService(session).build_snapshot(book.user_id, _snapshot_request(book, dataset))
    assert response.sections, f"{dataset.dataset_id}: the snapshot has no section"
    response.model_dump(mode="json")


async def _ai_export_every_component(book: _Book, dataset: DatasetSpec) -> None:
    """Every component of ``dataset``'s domain resolved on one request context, as ``build_snapshot`` prepares it —
    the internal-only components included. Each must build: one that fails may never have read the report."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        prepared = await service.prepare_request(book.user_id, _snapshot_request(book, dataset))
        context = BuildContext(service.component_registry, request_id=prepared.scope.request_id, scope=prepared.scope, bucket_plan=build_bucket_plan_for_scope(prepared.scope), session=session)
        component_ids = [spec.component_id for spec in service.component_registry if prepared.scope.domain in spec.domains]
        for component_id in component_ids:
            await context.resolve(component_id, required=False)
    assert component_ids, f"precondition: the {prepared.scope.domain.value} domain has components"
    assert not context.diagnostics, f"precondition: every {prepared.scope.domain.value} component builds: {[(diagnostic.component_id, diagnostic.reason) for diagnostic in context.diagnostics]}"


def _serialize_every_stored_report(watch: _L2Watch) -> None:
    """What a route, a log or an export does with a report: dumps, JSON, FastAPI's encoder."""
    for stored in list(watch.stored):
        stored.report.model_dump()
        stored.report.model_dump(mode="json")
        stored.report.model_dump_json()
        jsonable_encoder(stored.report)


@dataclass(frozen=True)
class _Consumer:
    label: str
    run: Callable[[], Awaitable[None] | None]
    #: Whether it asks get_report for a report (the serialization reads the stored ones; a market-only dataset has no
    #: component that reads the report).
    asks: bool = True


def _reads_the_report(dataset: DatasetSpec) -> bool:
    return bool((_EXPECTED_READERS | _EXPECTED_RISK_READERS) & {*dataset.required_component_ids, *dataset.optional_component_ids})


def _consumers(book: _Book, watch: _L2Watch) -> list[_Consumer]:
    consumers = [_Consumer("api: POST /portfolio/report", lambda: _api_report(book, watch))]
    consumers += [_Consumer(label, lambda body=body: _risk(book, body)) for label, body in _risk_bodies(book).items()]
    consumers += [_Consumer(f"ai export: snapshot {dataset.dataset_id}", lambda dataset=dataset: _ai_export_snapshot(book, dataset), asks=_reads_the_report(dataset)) for dataset in PUBLIC_DATASETS]
    overview_by_domain: dict[Domain, DatasetSpec] = {}
    for dataset in PUBLIC_DATASETS:
        overview_by_domain.setdefault(dataset.domain, dataset)  # the first public dataset of each domain
    consumers += [_Consumer(f"ai export: every {domain.value} component", lambda dataset=dataset: _ai_export_every_component(book, dataset)) for domain, dataset in overview_by_domain.items()]
    consumers.append(_Consumer("serialization: model_dump, model_dump_json, jsonable_encoder", lambda: _serialize_every_stored_report(watch), asks=False))
    return consumers


async def _run(watch: _L2Watch, label: str, consumer: _Consumer) -> None:
    with watch.consumer(label):
        outcome = consumer.run()
        if inspect.isawaitable(outcome):
            await outcome


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _no_market_holidays() -> frozenset[date]:
    return frozenset()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch):
    """The market holiday table, empty, wherever a consumer awaits it (the prices' signals, the risk runs)."""
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)


@pytest_asyncio.fixture
async def book(tmp_path) -> AsyncIterator[_Book]:
    async with _private_book(tmp_path) as opened:
        yield opened


@pytest.fixture
def l2_watch(monkeypatch) -> _L2Watch:
    return _L2Watch().install(monkeypatch)


# =============================================================================
# 1 — PRECONDITION: THE CACHED REPORT IS ONE SHARED OBJECT
# =============================================================================


class TestTheCachedReportIsShared:
    @pytest.mark.asyncio
    async def test_two_identical_queries_get_the_object_the_cache_holds(self, book, l2_watch):
        """Two requests, each on its own session, same query: one report is stored, both get it (``is``), and the cache
        holds that very object under the key it was stored with."""
        print_section("MF-J45c: the L2 cache hands one report object to every identical request")
        first = await _report(book, _full_query(book))
        second = await _report(book, _full_query(book))

        assert len(l2_watch.stored) == 1, f"one report stored for one query, got {len(l2_watch.stored)}"
        (stored,) = l2_watch.stored
        assert first is stored.report and second is stored.report, "both requests get the stored object"
        assert [call.from_l2 for call in l2_watch.calls] == [False, True], "the first request builds, the second is served from L2"
        cached, hit = portfolio_service_module._portfolio_l2_cache.get(stored.key)
        assert hit and cached is first, "the cache holds the very object both requests got"
        print_success("one object: built once, stored, served as is")


# =============================================================================
# 2 — GUARD: NO CONSUMER WRITES INTO A CACHED REPORT
# =============================================================================


def _assert_the_book_fills_every_section(watch: _L2Watch) -> None:
    every_feature = [stored.report for stored in watch.stored if len(stored.report.metadata.included_features) == len(_EVERY_INCLUDE_FLAG) - 1]  # include_breakdown is a part of the summary
    assert len(every_feature) == 2, f"precondition: the two primed reports carry every section, got {len(every_feature)}"
    for report in every_feature:
        summary = report.summary
        assert summary is not None and len(summary.holdings) >= 2 and summary.by_broker, "precondition: the summary has holdings (two at least, to reorder) and its broker breakdown"
        assert report.history and report.allocation_history and report.allocation_history.type and report.positions_contribution and report.positions_contribution.positions and report.broker_pnl_history, "precondition: history, allocation history, contribution and broker P&L"
        assert report.pnl_candles and report.pnl_candles.points and report.income_history and report.income_history.points and report.cost_history and report.cost_history.points, "precondition: candles, income and cost"
        assert report.deposit_history and report.deposit_history.points and report.acquisition_funding and report.acquisition_funding.points, "precondition: deposit history and acquisition funding"


def _assert_every_consumer_was_served_from_l2(watch: _L2Watch, replay: dict[str, _Consumer]) -> None:
    """The guard is not vacuous: each replayed consumer asked for reports and got them from L2, at every call site and in
    every AI Export component expected to read them."""
    calls = [call for call in watch.calls if call.consumer in replay]
    not_from_l2 = [f"{call.consumer} / {call.component} at {call.site}" for call in calls if not (call.from_l2 and watch.holds(call.report))]
    assert not not_from_l2, "precondition: in the second pass every get_report is served the stored object from L2, not:\n" + "\n".join(not_from_l2)
    silent = [label for label, consumer in replay.items() if consumer.asks and not any(call.consumer == label for call in calls)]
    assert not silent, f"precondition: every consumer calls get_report, these did not: {silent}"
    missing_sites = sorted(_EXPECTED_CALL_SITES - {call.site for call in calls})
    assert not missing_sites, f"precondition: every call site is reached in the second pass, these were not: {missing_sites}"
    receipts = [receipt for receipt in watch.receipts if receipt.consumer in replay]
    foreign = [f"{receipt.consumer} / {receipt.component} ({receipt.resource})" for receipt in receipts if not watch.holds(receipt.report)]
    assert receipts and not foreign, f"precondition: every AI Export component is handed a stored report, not: {foreign}"
    missing_readers = sorted(_EXPECTED_READERS - {receipt.component for receipt in receipts})
    assert not missing_readers, f"precondition: these AI Export components were never handed the shared report: {missing_readers}"
    missing_risk_readers = sorted(_EXPECTED_RISK_READERS - {call.component for call in calls if call.site.endswith("risk.scope.load_scope_inputs")})
    assert not missing_risk_readers, f"precondition: these drawdowns never reached get_report through RiskService: {missing_risk_readers}"


class TestTheCachedReportIsNotMutatedByItsConsumers:
    @pytest.mark.asyncio
    async def test_every_consumer_leaves_every_cached_report_as_stored(self, book, l2_watch):
        """Prime L2 with every include flag (whole portfolio, broker A); run every consumer twice — the first pass stores
        each one's own key, the second is served from L2 at every call; after each consumer every stored report still
        equals its snapshot at storage."""
        print_section("MF-J45c: no consumer writes into a report the L2 cache shares")
        with l2_watch.consumer("prime: every include flag, whole portfolio"):
            await _report(book, _full_query(book))
        with l2_watch.consumer("prime: every include flag, broker A"):
            await _report(book, _full_query(book, broker_labels=("A",)))
        _assert_the_book_fills_every_section(l2_watch)

        consumers = _consumers(book, l2_watch)
        for consumer in consumers:
            await _run(l2_watch, f"first pass: {consumer.label}", consumer)
        stored_after_first_pass = len(l2_watch.stored)
        for consumer in consumers:
            await _run(l2_watch, f"second pass: {consumer.label}", consumer)

        moved = l2_watch.moved + [line for line in l2_watch.changes() if line not in l2_watch.seen]
        shown = "\n".join(moved[:_SHOWN_LINES]) + (f"\n... and {len(moved) - _SHOWN_LINES} more" if len(moved) > _SHOWN_LINES else "")
        assert moved == [], f"a consumer wrote into a report the L2 cache shares:\n{shown}\nwhere:\n{l2_watch.legend(moved)}"
        # Not vacuous: the second pass was served from L2, at every call site and in every reader expected.
        assert len(l2_watch.stored) == stored_after_first_pass, f"precondition: the second pass stores nothing new ({len(l2_watch.stored) - stored_after_first_pass} more)"
        _assert_every_consumer_was_served_from_l2(l2_watch, {f"second pass: {consumer.label}": consumer for consumer in consumers})
        served = sum(call.from_l2 for call in l2_watch.calls)
        print_success(f"{len(l2_watch.stored)} stored reports, {len(l2_watch.calls)} get_report calls ({served} served from L2), {len(l2_watch.receipts)} AI Export receipts: nothing moved")


# =============================================================================
# 3 — THE GUARD'S TEETH: THE SNAPSHOT SEES A WRITE
# =============================================================================


def _another_exponent(value: Decimal) -> Decimal:
    """The same number with one more digit after the point: 1.0 -> 1.00."""
    return value + Decimal((0, (0,), value.as_tuple().exponent - 1))


class TestTheSnapshotSeesAWrite:
    @pytest.mark.asyncio
    async def test_the_snapshot_sees_a_write_anywhere_in_a_report(self, book):
        """On a deep copy of a real report: a nested Decimal rewritten with another exponent only, a list append, a list
        reversed, a nested field set, a nested field rebound to an equal value — each changes the snapshot, at the path
        written; the untouched copy snapshots as the original."""
        report = await _report(book, _full_query(book))
        assert report.summary is not None and len(report.summary.holdings) >= 2, "precondition: two holdings to reorder"

        def exponent(copy: PortfolioReportResponse) -> None:
            holding = copy.summary.holdings[0]
            holding.quantity = _another_exponent(holding.quantity)
            assert holding.quantity == report.summary.holdings[0].quantity, "the rewrite keeps the value"

        writes: dict[str, tuple[Callable[[PortfolioReportResponse], None], str]] = {
            "exponent": (exponent, "report.summary.holdings[0].quantity"),
            "list append": (lambda copy: copy.history.append(copy.history[-1].model_copy()), "report.history"),
            "list reversed": (lambda copy: copy.summary.holdings.reverse(), "report.summary.holdings[0]"),
            "nested field set": (lambda copy: setattr(copy.metadata, "target_currency", USD), "report.metadata.target_currency"),
            "nested list in a model": (lambda copy: copy.metadata.included_features.append("extra"), "report.metadata.included_features"),
        }
        original = _snapshot(report)
        assert _differences(original, _snapshot(report.model_copy(deep=True))) == [], "a deep copy snapshots as the original"
        for name, (write, path) in writes.items():
            copy = report.model_copy(deep=True)
            write(copy)
            moved = _differences(original, _snapshot(copy))
            assert moved, f"the snapshot missed a write: {name}"
            assert any(line.startswith(path) for line in moved), f"{name}: the difference is reported at {moved}, not at {path}"
        assert _differences(original, _snapshot(report)) == [], "the writes went to the copies only"

    def test_the_snapshot_sees_a_dict_write_and_raises_on_an_unknown_type(self):
        """Pure: a dict entry set, a key reordered and a field rebound to an equal value (it joins the fields-set, which
        ``exclude_unset`` reads) change the snapshot; an object it cannot compare raises, at its path."""

        @dataclass
        class Holder:
            by_type: dict[str, Decimal]

        def build() -> Holder:
            return Holder(by_type={"Stock": Decimal("1.0"), "ETF": Decimal("2")})

        before = _snapshot(build())
        for name, write in {
            "dict entry set": lambda holder: holder.by_type.__setitem__("Stock", Decimal("1.00")),
            "dict entry added": lambda holder: holder.by_type.__setitem__("Bond", Decimal("0")),
            "dict reordered": lambda holder: holder.by_type.__setitem__("Stock", holder.by_type.pop("Stock")),
        }.items():
            holder = build()
            write(holder)
            assert _differences(before, _snapshot(holder)), f"the snapshot missed a write: {name}"

        query = PortfolioReportQuery(target_currency=EUR)
        rebound = query.model_copy()
        rebound.include_summary = query.include_summary
        assert _differences(_snapshot(query), _snapshot(rebound), "query") == ["query <fields_set>: ('fields_set', ('target_currency',)) -> ('fields_set', ('include_summary', 'target_currency'))"], "a field rebound to its own value joins the fields-set"

        with pytest.raises(_UnsnapshottableValue, match=r"report\.history\[0\]: cannot snapshot a object"):
            _snapshot(PortfolioReportResponse.model_construct(history=[object()]))

"""FB-14 — one engine run for the Portfolio page: the report, the Performance table, the positions chart and the BUY
funding split share one build, and their outputs are those of the old per-caller runs.

The defect: ``PortfolioService.get_report``, ``get_positions_contribution``, ``get_positions_series`` and
``get_acquisition_funding_history`` each called ``PortfolioCalculationEngine.calculate`` with flags of their own (the
report: funding only if asked, ``period_start`` only with the contribution, no position frames; the series: frames and
``period_start``, no funding; the contribution: ``period_start`` only; the funding: funding only, no ``period_start``).
Those flags are part of the engine's blob-cache key and of its single-flight key (``financial_math/portfolio/engine.py``,
step 5b, ``_IN_FLIGHT``), so the page's report and positions-series requests built the engine twice. The cure
(``backend/app/services/portfolio/portfolio_service.py``, ``PortfolioService._engine_run``): every one of them asks the same run —
from t=0, ``period_start=date_from``, ``include_positions=True``, ``include_acquisition_funding=True`` — the candles
alone staying a flag of the caller.

- ``TestOneBuildPerPage`` — red before FB-14 (the report and the series make two builds; the guard
  ``test_the_old_flags_build_twice`` pins that this count can tell the two apart): a report with every section the page
  asks then the positions series of the same window → one build; the same two requests concurrent, the build held until
  the second one waits on it → one build (single-flight); the standalone Performance table and BUY funding split of that
  window after the report → no new build. Each call is first proved to answer with data (series points, contribution
  rows, history points), so a «no build» can never come from an early empty return.
- ``TestOutputsUnchanged`` — the parity: each public output computed with the shared run equals, field by field
  (``model_dump(mode="json")``), the same output computed with the old flags of its caller. The old flags are put back
  by patching ``PortfolioService._engine_run`` with ``_OldEngineRun``, which the test tells which caller it stands for
  before each call; both caches are emptied between the two computations. Outputs: the full report (summary with
  breakdown, history, allocation history, positions contribution, broker P&L history on two brokers, income, cost and
  deposit history, BUY funding); the report with summary and history only (and there ``positions_contribution`` and
  ``acquisition_funding`` are None); the positions series; the positions contribution; the BUY funding history. Each in a
  window starting mid-history (D2..END) and with no date range.

The seam of a build: ``PortfolioCalculationEngine._compute_uncached`` (steps 6–12 of ``calculate``: the replay), patched
on the class. ``calculate`` returns before it on a blob-cache hit, and a request that waits on another's build never
calls it: one call is one replay. The concurrent test holds that build on an ``asyncio.Event`` and replaces
``_IN_FLIGHT`` with ``_RecordedFlights``, which records the request that finds the pending build; it releases the build
only when both happened. No sleep: ``_HANG_S`` only bounds a failure.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, NullPool, disposed at teardown): user U owns brokers A and B at 100 %; X is a EUR stock, Y a USD stock; read in
EUR:

- D0 03-04: DEPOSIT 10000 at A, 1000 at B;  D1 03-05: BUY 3 X for 1000 at A;
- D2 03-07: TRANSFER of 1 X A -> B (arrives D4); CASH_TRANSFER of 500 A -> B (arrives D3);
- D3 03-08: FX_CONVERSION at A, 1000 EUR into 1090 USD; BUY 2 Y for 500 USD at A;
- D4 03-11: SELL 1 X for 340 at A; DIVIDEND 12 on X, FEE 3, TAX 2 at A;  D5 03-12: WITHDRAWAL 100 at B.

Prices of X (EUR) and Y (USD) and EUR/USD rates on a few days up to 03-13.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The engine's blob
cache and the report's L2 cache (process-global) are emptied around each test; ``_IN_FLIGHT`` and the patches go through
``monkeypatch``.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services engine-shared-run``.

Reference: backend/app/services/portfolio/portfolio_service.py (_engine_run and its four callers),
backend/app/services/financial_math/portfolio/engine.py (calculate: the blob key and the single-flight after step 5b).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
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
from backend.app.schemas.portfolio import PortfolioReportQuery, PositionKey, PositionsSeriesQuery
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"

D0 = date(2024, 3, 4)
D1 = date(2024, 3, 5)
D2 = date(2024, 3, 7)
D3 = date(2024, 3, 8)
D4 = date(2024, 3, 11)
D5 = date(2024, 3, 12)
LAST_QUOTE = date(2024, 3, 13)
END = date(2024, 3, 14)

#: Only a failure reaches it: a request that never reaches the build or the flight.
_HANG_S = 30.0
#: How many differing fields an assertion message shows.
_DIFF_SHOWN = 12

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
# (asset, day, close, currency)
_CLOSES = (("X", D1, "333.5", EUR), ("X", D4, "345.67", EUR), ("X", LAST_QUOTE, "350", EUR), ("Y", D3, "250", USD), ("Y", D5, "255", USD))
# 1 EUR = rate USD from that day (base EUR < quote USD, as FxRate's check requires)
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
        user = User(username=f"fb14_{tag}", email=f"fb14_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"FB-14 shared run {label} {tag}") for label in ("A", "B")}
        assets = {
            "X": Asset(display_name=f"FB-14 shared run X {tag}", currency=EUR, asset_type=AssetType.STOCK),
            "Y": Asset(display_name=f"FB-14 shared run Y {tag}", currency=USD, asset_type=AssetType.STOCK),
        }
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])
        session.add_all(
            [
                *(PriceHistory(asset_id=assets[asset].id, date=day, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=Decimal("1"), currency=currency, source_plugin_key="fb14_shared_run_test") for asset, day, close, currency in _CLOSES),
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
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'fb14_shared_run.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


# =============================================================================
# THE QUERIES — what the Portfolio page asks
# =============================================================================


def _range(window: tuple[date, date] | None) -> OpenDateRangeModel | None:
    return OpenDateRangeModel(start=window[0], end=window[1]) if window else None


def _page_report_query(book: _Book, window: tuple[date, date] | None) -> PortfolioReportQuery:
    """Every section the Portfolio page asks, on both brokers. No candles: they are a flag of their own (a lazy submode)."""
    return PortfolioReportQuery(
        broker_ids=sorted(book.broker_ids.values()),
        date_range=_range(window),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
        include_breakdown=True,
        include_positions_contribution=True,
        include_broker_pnl_history=True,
        include_pnl_candles=False,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
    )


def _summary_history_query(book: _Book, window: tuple[date, date] | None) -> PortfolioReportQuery:
    """The report with summary and history only: neither the contribution nor the funding asked."""
    return PortfolioReportQuery(
        broker_ids=sorted(book.broker_ids.values()),
        date_range=_range(window),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=False,
        include_breakdown=False,
        include_positions_contribution=False,
        include_acquisition_funding=False,
    )


def _series_query(book: _Book, window: tuple[date, date] | None) -> PositionsSeriesQuery:
    """X at A, X at B (it arrives by the transfer), Y at A (USD), and X summed over the brokers."""
    x, y = book.asset_ids["X"], book.asset_ids["Y"]
    a, b = book.broker_ids["A"], book.broker_ids["B"]
    return PositionsSeriesQuery(
        broker_ids=sorted(book.broker_ids.values()),
        date_range=_range(window),
        target_currency=EUR,
        positions=[PositionKey(asset_id=x, broker_id=a), PositionKey(asset_id=x, broker_id=b), PositionKey(asset_id=y, broker_id=a), PositionKey(asset_id=x, broker_id=None)],
    )


# =============================================================================
# THE SEAMS — the build counter, the held build, the recorded flights, the old flags
# =============================================================================


class _Builds:
    """Counts the calls of ``PortfolioCalculationEngine._compute_uncached``: one per replay. Optionally holds each build
    until ``release`` is set (``entered`` is set once a build is held: its flight is registered by then)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        self.hold = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        original = PortfolioCalculationEngine._compute_uncached

        async def counted(engine_self, **kwargs):
            self.count += 1
            if self.hold:
                self.entered.set()
                await asyncio.wait_for(self.release.wait(), _HANG_S)
            return await original(engine_self, **kwargs)

        monkeypatch.setattr(PortfolioCalculationEngine, "_compute_uncached", counted)


class _RecordedFlights(dict):
    """``_IN_FLIGHT`` that sets ``follower_seen`` when a request reads a pending build: that request waits on it."""

    def __init__(self) -> None:
        super().__init__()
        self.follower_seen = asyncio.Event()

    def get(self, key, default=None):
        flight = super().get(key, default)
        if flight is not None and not flight.done():
            self.follower_seen.set()
        return flight


class _OldEngineRun:
    """``PortfolioService._engine_run`` with the flags each caller passed before FB-14. ``caller`` is set by the test
    before each public call; ``query`` is the report's query (its include flags chose the report's engine flags)."""

    def __init__(self) -> None:
        self.caller: str | None = None
        self.query: PortfolioReportQuery | None = None
        self.calls: list[str] = []

    async def __call__(self, service: PortfolioService, *, user_id, broker_ids, date_from, date_to, target_currency, include_candles: bool = False, apply_ownership_share: bool = True):
        assert self.caller is not None, "the test did not say which caller the old run stands for"
        self.calls.append(self.caller)
        flags: dict[str, Any]
        if self.caller == "report":
            assert self.query is not None
            flags = {
                "include_candles": include_candles,
                "include_acquisition_funding": self.query.include_acquisition_funding,
                "period_start": date_from if self.query.include_positions_contribution else None,
                "include_positions": False,
            }
        elif self.caller == "series":
            flags = {"period_start": date_from, "include_positions": True}
        elif self.caller == "contribution":
            flags = {"period_start": date_from}
        elif self.caller == "funding":
            flags = {"include_acquisition_funding": True}
        else:  # pragma: no cover — a typo in the test
            raise AssertionError(f"unknown caller {self.caller!r}")
        # MF6-3: the owner's share is not one of the per-caller flags FB-14 unified: it goes to the engine as asked.
        return await PortfolioCalculationEngine(service.db).calculate(user_id=user_id, broker_ids=broker_ids, date_from=None, date_to=date_to, target_currency=target_currency, apply_ownership_share=apply_ownership_share, **flags)

    def as_method(self):
        """A plain function, so that it binds to the service as ``_engine_run`` does (an instance would not)."""

        async def _engine_run(service, **kwargs):
            return await self(service, **kwargs)

        return _engine_run


def _clear_caches() -> None:
    portfolio_engine_module._portfolio_blob_cache.clear()
    report_module._portfolio_l2_cache.clear()


def _diff(old: Any, new: Any, path: str = "$") -> list[tuple[str, Any, Any]]:
    """Every leaf where two JSON trees differ, as (path, old, new)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out: list[tuple[str, Any, Any]] = []
        for key in sorted(set(old) | set(new), key=str):
            if key not in old or key not in new:
                out.append((f"{path}.{key}", old.get(key, "<absent>"), new.get(key, "<absent>")))
            else:
                out.extend(_diff(old[key], new[key], f"{path}.{key}"))
        return out
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [(f"{path}.length", len(old), len(new))]
        out = []
        for index, (left, right) in enumerate(zip(old, new, strict=True)):
            out.extend(_diff(left, right, f"{path}[{index}]"))
        return out
    return [] if old == new else [(path, old, new)]


def _assert_same(label: str, old: Any, new: Any) -> None:
    differences = _diff(old.model_dump(mode="json"), new.model_dump(mode="json"))
    shown = "\n".join(f"  {path}: old={left!r} new={right!r}" for path, left, right in differences[:_DIFF_SHOWN])
    assert not differences, f"{label}: {len(differences)} field(s) differ between the old flags and the shared run:\n{shown}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No engine blob and no report crosses into or out of a test: a cached one would answer without a build."""
    _clear_caches()
    request.addfinalizer(_clear_caches)


@pytest_asyncio.fixture
async def book(tmp_path) -> AsyncIterator[_Book]:
    async with _private_book(tmp_path) as opened:
        yield opened


@pytest.fixture
def builds(monkeypatch) -> _Builds:
    return _Builds(monkeypatch)


WINDOW = (D2, END)


def _assert_report_has_data(report) -> None:
    assert report.history, "the report has no history: the engine run answered empty"
    assert report.positions_contribution is not None and report.positions_contribution.positions, "the report has no positions contribution"
    assert report.acquisition_funding is not None and report.acquisition_funding.points, "the report has no BUY funding in the window"
    assert report.broker_pnl_history is not None and len(report.broker_pnl_history) == 2, "the report has not the P&L history of both brokers"


def _assert_series_has_data(series) -> None:
    assert len(series.series) == 4, "the series do not answer the four positions asked"
    assert all(entry.points for entry in series.series), f"a position asked has no point: {[(entry.key, len(entry.points)) for entry in series.series]}"


# =============================================================================
# 1 — ONE BUILD PER PAGE
# =============================================================================


class TestOneBuildPerPage:
    @pytest.mark.asyncio
    async def test_the_report_then_the_series_make_one_build(self, book, builds):
        print_section("FB-14: the report then the positions series of the same window — one build")
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            service = PortfolioService(session)
            report = await service.get_report(book.user_id, _page_report_query(book, WINDOW))
            _assert_report_has_data(report)
            assert builds.count == 1, f"the report made {builds.count} builds"
            series = await service.get_positions_series(book.user_id, _series_query(book, WINDOW))
            _assert_series_has_data(series)
        assert builds.count == 1, f"the report and the series made {builds.count} builds, not one"
        print_success("one build for the report and the series")

    @pytest.mark.asyncio
    async def test_the_old_flags_build_twice(self, book, builds, monkeypatch):
        """Guard of the count above: with the old per-caller flags the same two requests make two builds."""
        print_section("FB-14 guard: the old flags — the report and the series build twice")
        old = _OldEngineRun()
        monkeypatch.setattr(PortfolioService, "_engine_run", old.as_method())
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            service = PortfolioService(session)
            old.caller, old.query = "report", _page_report_query(book, WINDOW)
            _assert_report_has_data(await service.get_report(book.user_id, old.query))
            old.caller = "series"
            _assert_series_has_data(await service.get_positions_series(book.user_id, _series_query(book, WINDOW)))
        assert builds.count == 2, f"the old flags made {builds.count} builds: the count cannot tell the shared run from them"
        print_success("two builds with the old flags")

    @pytest.mark.asyncio
    async def test_the_report_and_the_series_concurrent_make_one_build(self, book, builds, monkeypatch):
        print_section("FB-14: the report and the series concurrent — one build (single-flight)")
        flights = _RecordedFlights()
        monkeypatch.setattr(portfolio_engine_module, "_IN_FLIGHT", flights)
        builds.hold = True

        async def report():
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                return await PortfolioService(session).get_report(book.user_id, _page_report_query(book, WINDOW))

        async def series():
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                return await PortfolioService(session).get_positions_series(book.user_id, _series_query(book, WINDOW))

        tasks = [asyncio.create_task(report()), asyncio.create_task(series())]
        try:
            # The build is held with its flight registered, and the other request waits on that flight.
            await asyncio.wait_for(asyncio.gather(builds.entered.wait(), flights.follower_seen.wait()), _HANG_S)
            assert builds.count == 1, f"{builds.count} builds started while the first one was held"
        finally:
            builds.release.set()
            report_result, series_result = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), _HANG_S)
        for result in (report_result, series_result):
            if isinstance(result, BaseException):
                raise result
        _assert_report_has_data(report_result)
        _assert_series_has_data(series_result)
        assert builds.count == 1, f"the concurrent report and series made {builds.count} builds"
        assert not dict(flights), "a flight was left in _IN_FLIGHT"
        print_success("one build shared by the two concurrent requests")

    @pytest.mark.asyncio
    async def test_the_standalone_contribution_and_funding_after_the_report_build_nothing(self, book, builds):
        print_section("FB-14: the standalone Performance table and BUY funding after the report — no new build")
        broker_ids = sorted(book.broker_ids.values())
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            service = PortfolioService(session)
            _assert_report_has_data(await service.get_report(book.user_id, _page_report_query(book, WINDOW)))
            assert builds.count == 1
            contribution = await service.get_positions_contribution(book.user_id, broker_ids=broker_ids, date_from=WINDOW[0], date_to=WINDOW[1], target_currency_override=EUR)
            assert contribution.positions, "the standalone contribution has no row"
            funding = await service.get_acquisition_funding_history(book.user_id, broker_ids=broker_ids, date_from=WINDOW[0], date_to=WINDOW[1], target_currency_override=EUR)
            assert funding.points, "the standalone BUY funding has no point in the window"
        assert builds.count == 1, f"the standalone contribution and funding made {builds.count - 1} new builds"
        print_success("the report's run answers the standalone contribution and funding")


# =============================================================================
# 2 — THE OUTPUTS ARE THOSE OF THE OLD PER-CALLER RUNS
# =============================================================================


async def _report(book: _Book, query: PortfolioReportQuery):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


async def _series(book: _Book, window: tuple[date, date] | None):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_positions_series(book.user_id, _series_query(book, window))


async def _contribution(book: _Book, window: tuple[date, date] | None):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        date_from, date_to = window if window else (None, None)
        return await PortfolioService(session).get_positions_contribution(book.user_id, broker_ids=sorted(book.broker_ids.values()), date_from=date_from, date_to=date_to, target_currency_override=EUR)


async def _funding(book: _Book, window: tuple[date, date] | None):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        date_from, date_to = window if window else (None, None)
        return await PortfolioService(session).get_acquisition_funding_history(book.user_id, broker_ids=sorted(book.broker_ids.values()), date_from=date_from, date_to=date_to, target_currency_override=EUR)


async def _old_and_new(monkeypatch: pytest.MonkeyPatch, caller: str, compute, query: PortfolioReportQuery | None = None):
    """The output under the old flags of ``caller``, then under the shared run, each on empty caches."""
    old_run = _OldEngineRun()
    old_run.caller, old_run.query = caller, query
    _clear_caches()
    with monkeypatch.context() as patch:
        patch.setattr(PortfolioService, "_engine_run", old_run.as_method())
        old = await compute()
    # Exactly one engine run per public call, as before FB-14 (the report's contribution reads the report's run). None
    # would mean the comparison compares the shared run with itself.
    assert old_run.calls == [caller], f"engine runs under the old flags of {caller}: {old_run.calls}"
    _clear_caches()
    new = await compute()
    _clear_caches()
    return old, new


_WINDOWS = pytest.mark.parametrize("window", [WINDOW, None], ids=["mid-history", "no-date-range"])


class TestOutputsUnchanged:
    @pytest.mark.asyncio
    @_WINDOWS
    async def test_the_page_report(self, book, monkeypatch, window):
        print_section(f"FB-14 parity: the page's report, window {window}")
        query = _page_report_query(book, window)
        old, new = await _old_and_new(monkeypatch, "report", lambda: _report(book, query), query)
        _assert_report_has_data(new)
        assert new.summary is not None and new.allocation_history is not None
        assert new.income_history is not None and new.cost_history is not None and new.deposit_history is not None
        _assert_same("get_report (every section of the page)", old, new)
        print_success("the page's report is unchanged")

    @pytest.mark.asyncio
    @_WINDOWS
    async def test_the_report_with_summary_and_history_only(self, book, monkeypatch, window):
        print_section(f"FB-14 parity: the report with summary and history only, window {window}")
        query = _summary_history_query(book, window)
        old, new = await _old_and_new(monkeypatch, "report", lambda: _report(book, query), query)
        assert new.summary is not None and new.history, "the report has no summary or no history"
        assert new.positions_contribution is None, "the contribution was not asked"
        assert new.acquisition_funding is None, "the BUY funding was not asked"
        _assert_same("get_report (summary + history)", old, new)
        print_success("the summary-and-history report is unchanged, contribution and funding absent")

    @pytest.mark.asyncio
    @_WINDOWS
    async def test_the_positions_series(self, book, monkeypatch, window):
        print_section(f"FB-14 parity: the positions series, window {window}")
        old, new = await _old_and_new(monkeypatch, "series", lambda: _series(book, window))
        _assert_series_has_data(new)
        _assert_same("get_positions_series", old, new)
        print_success("the positions series are unchanged")

    @pytest.mark.asyncio
    @_WINDOWS
    async def test_the_positions_contribution(self, book, monkeypatch, window):
        print_section(f"FB-14 parity: the positions contribution, window {window}")
        old, new = await _old_and_new(monkeypatch, "contribution", lambda: _contribution(book, window))
        assert new.positions, "the contribution has no row"
        _assert_same("get_positions_contribution", old, new)
        print_success("the positions contribution is unchanged")

    @pytest.mark.asyncio
    @_WINDOWS
    async def test_the_acquisition_funding_history(self, book, monkeypatch, window):
        print_section(f"FB-14 parity: the BUY funding history, window {window}")
        old, new = await _old_and_new(monkeypatch, "funding", lambda: _funding(book, window))
        assert new.points, "the BUY funding has no point"
        _assert_same("get_acquisition_funding_history", old, new)
        print_success("the BUY funding history is unchanged")

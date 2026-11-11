"""MF-K3 (workstream MF, wave 6) — the Dashboard's TWRR and simple ROI: the card and the line follow one rule.

What changed (``backend/app/services/portfolio/portfolio_service.py``, HEAD ``33b66ba1c`` → the working tree):

* the summary card's ``twrr_percent`` is ``returns.period_twrr(period_navs, period_cfs)``, the last point of
  ``period_twrr_series``: None where the period's last NAV is at or below zero. HEAD computed ``calculate_twrr`` under
  its own guard ``engine_nav > 0``;
* the history's ``twrr`` points (``get_history_steps``) come from ``period_twrr_series``: None on a day whose NAV is at or
  below zero. HEAD's ``calculate_twrr_series`` drew a flat number on an emptied portfolio;
* the card's ``simple_roi_percent`` and the history's ``roi`` points count their capital from
  ``returns.period_roi_cash_flows``: the rebased flows, except when ``date_from`` precedes every snapshot — then every
  flow, so the first day's deposit counts as capital. HEAD's rebase left it out: ROI 0.

Tests:

- ``test_an_emptied_portfolio_has_no_twrr_card_nor_point`` (red on HEAD): DEPOSIT 1 000 and BUY 10 × 100 on 03-03,
  close 110 on 03-04, SELL all for 1 100 and WITHDRAWAL 1 100 on 03-05: NAV 0 on 03-05. The card is None (HEAD: None
  too, by its ``engine_nav > 0`` guard), and the history's point dated 03-05 has ``twrr`` None — HEAD drew 0.1. The
  card is the last point;
- ``test_a_range_before_the_portfolio_counts_the_first_deposit`` (red on HEAD): DEPOSIT 1 000 and BUY 10 × 100 on
  03-03, closes 100 / 105 / 112 on 03-03 / 03-04 / 03-05, read with ``date_from`` 03-01 (before the portfolio): the
  card's ``simple_roi_percent`` is the one without ``date_from``, 0.12; the history's ``roi`` points are the ones of
  the history without ``date_from``. HEAD: 0 and 0;
- ``TestGuards`` (green on HEAD and on the tree, concrete numbers from the book): without ``date_from`` ROI 0.12 and
  TWRR 0.12 (1 000 → 1 120 with no other flow); with ``date_from`` 03-04 (inside the history) the period opens on 1 050:
  ROI and TWRR (1 120 − 1 050) / 1 050 = 0.066667. And the card's TWRR is the last point of the line.

Red on HEAD ``33b66ba1c`` (the backend of that commit extracted with ``git archive``, this file copied into it), the
exact messages:

- ``test_an_emptied_portfolio_has_no_twrr_card_nor_point``: «the history's point on 03-05 (NAV 0) has twrr 0.100000:
  an emptied portfolio has no TWRR»;
- ``test_a_range_before_the_portfolio_counts_the_first_deposit``: «simple_roi_percent 0 with date_from 2025-03-01
  before the portfolio: without date_from it is 0.120000».

It was red on the working tree's first wiring of MF-K3 too (2026-10-28): the service handed ``period_roi_cash_flows``
the flows of ``DerivedViewsBuilder.build_performance_inputs(date_from)``, which start from the opening state's baseline,
so a ``date_from`` before the first state had no flow for the first day's deposit and the ROI stayed 0. MF then added
``DerivedViewsBuilder.build_roi_cash_flows``, which reads the whole history's inputs in that case: green since.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): one user owning one broker at 100 %, one EUR stock.
Every point of a history is found by its date (``date <= day <= through``), never by position.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The report (L2),
WAC and engine blob caches (process-global) are emptied around each test. No sleep.

Runs in ``./dev.py test services roi-fifo-utils``; alone:
``./dev.py test services roi-fifo-utils test_portfolio_twrr_roi_card_and_line``.

Reference: backend/app/services/portfolio/portfolio_service.py (get_summary «5. Performance», get_history_steps),
backend/app/services/financial_math/returns.py (period_twrr, period_twrr_series, period_roi_cash_flows),
backend/app/services/financial_math/portfolio/derived_views.py (build_performance_inputs, build_roi_cash_flows).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.portfolio import PortfolioHistoryPoint, PortfolioSummary
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

D = Decimal
EUR = "EUR"

BEFORE = date(2025, 3, 1)
MAR_03 = date(2025, 3, 3)
MAR_04 = date(2025, 3, 4)
MAR_05 = date(2025, 3, 5)


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Scenario:
    """One EUR stock at one broker: the movements ``(type, day, quantity, amount)`` and the closes."""

    label: str
    movements: tuple[tuple[TransactionType, date, str, str], ...]
    closes: tuple[tuple[date, str], ...]


#: Bought on 03-03, worth 1 100 on 03-04, all sold and all withdrawn on 03-05: NAV 0.
EMPTIED = _Scenario(
    label="emptied",
    movements=(
        (TransactionType.DEPOSIT, MAR_03, "0", "1000"),
        (TransactionType.BUY, MAR_03, "10", "-1000"),
        (TransactionType.SELL, MAR_05, "-10", "1100"),
        (TransactionType.WITHDRAWAL, MAR_05, "0", "-1100"),
    ),
    closes=((MAR_03, "100"), (MAR_04, "110"), (MAR_05, "110")),
)
#: One deposit and one buy on 03-03, the price rising to 112 on 03-05: 1 000 → 1 120.
YOUNG = _Scenario(
    label="young",
    movements=((TransactionType.DEPOSIT, MAR_03, "0", "1000"), (TransactionType.BUY, MAR_03, "10", "-1000")),
    closes=((MAR_03, "100"), (MAR_04, "105"), (MAR_05, "112")),
)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_id: int


async def _seed(engine: AsyncEngine, scenario: _Scenario) -> _Book:
    """The scenario's ledger, owned by a new user, committed to the private file."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"mfk3_{scenario.label}_{tag}", email=f"mfk3_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker = Broker(name=f"MF-K3 {scenario.label} {tag}")
        asset = Asset(display_name=f"MF-K3 {scenario.label} {tag}", currency=EUR, asset_type=AssetType.STOCK)
        session.add_all([user, broker, asset])
        await session.flush()
        session.add_all(
            [
                BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")),
                *(
                    Transaction(
                        broker_id=broker.id,
                        asset_id=None if kind in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL) else asset.id,
                        type=kind,
                        date=day,
                        quantity=D(quantity),
                        amount=D(amount),
                        currency=EUR,
                    )
                    for kind, day, quantity, amount in scenario.movements
                ),
                *(PriceHistory(asset_id=asset.id, date=day, open=D(close), high=D(close), low=D(close), close=D(close), volume=D("1"), currency=EUR, source_plugin_key="mfk3_test") for day, close in scenario.closes),
            ]
        )
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_id=broker.id)


@asynccontextmanager
async def _private_book(directory: Path, scenario: _Scenario) -> AsyncIterator[_Book]:
    """The app schema and the scenario's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'mfk3_{scenario.label}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, scenario)
    finally:
        await engine.dispose()


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: each private file numbers its rows from 1."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


async def _summary(book: _Book, date_from: date | None) -> PortfolioSummary:
    _clear_portfolio_caches()
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_summary(user_id=book.user_id, broker_ids=[book.broker_id], target_currency_override=EUR, date_from=date_from, date_to=MAR_05)


async def _history(book: _Book, date_from: date | None) -> list[PortfolioHistoryPoint]:
    _clear_portfolio_caches()
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_history(user_id=book.user_id, broker_ids=[book.broker_id], target_currency_override=EUR, date_from=date_from, date_to=MAR_05)


def _point_on(history: list[PortfolioHistoryPoint], day: date) -> PortfolioHistoryPoint:
    """The step of the history that holds ``day`` (``date <= day <= through``), found by its dates."""
    found = [point for point in history if point.date <= day <= (point.through or point.date)]
    assert len(found) == 1, f"one step holds {day}: {[(point.date, point.through) for point in history]}"
    return found[0]


# =============================================================================
# THE TESTS
# =============================================================================


class TestTheCardAndTheLineAgree:
    @pytest.mark.asyncio
    async def test_an_emptied_portfolio_has_no_twrr_card_nor_point(self, tmp_path):
        """NAV 0 on 03-05: no TWRR on the card, none on the line's 03-05 point; the card is the last point."""
        async with _private_book(tmp_path, EMPTIED) as book:
            summary = await _summary(book, None)
            history = await _history(book, None)

        last = _point_on(history, MAR_05)
        assert last.nav_value.amount == 0, f"precondition: the portfolio emptied on 03-05, NAV {last.nav_value.amount}"
        assert _point_on(history, MAR_04).twrr == D("0.1"), f"precondition: +10 % on 03-04, got {_point_on(history, MAR_04).twrr}"
        assert summary.twrr_percent is None, f"card twrr_percent {summary.twrr_percent} on an emptied portfolio"
        assert last.twrr is None, f"the history's point on 03-05 (NAV 0) has twrr {last.twrr}: an emptied portfolio has no TWRR"
        assert summary.twrr_percent == last.twrr, "the card is the line's last point"

    @pytest.mark.asyncio
    async def test_a_range_before_the_portfolio_counts_the_first_deposit(self, tmp_path):
        """``date_from`` 03-01, before the first day: the ROI's capital is the 03-03 deposit, as without ``date_from``
        — the card's ROI and the line's ROI points are the whole history's."""
        async with _private_book(tmp_path, YOUNG) as book:
            whole = await _summary(book, None)
            before = await _summary(book, BEFORE)
            whole_history = await _history(book, None)
            before_history = await _history(book, BEFORE)

        assert whole.simple_roi_percent == D("0.12"), f"precondition: 1 000 → 1 120 without date_from, got {whole.simple_roi_percent}"
        assert before.simple_roi_percent != 0, f"simple_roi_percent {before.simple_roi_percent} with date_from {BEFORE} before the portfolio: without date_from it is {whole.simple_roi_percent}"
        assert before.simple_roi_percent == whole.simple_roi_percent, f"simple_roi_percent {before.simple_roi_percent} with date_from {BEFORE}, {whole.simple_roi_percent} without"
        for day in (MAR_03, MAR_04, MAR_05):
            assert _point_on(before_history, day).roi == _point_on(whole_history, day).roi, f"roi on {day}: {_point_on(before_history, day).roi} with date_from {BEFORE}, {_point_on(whole_history, day).roi} without"
        assert _point_on(before_history, MAR_05).roi == D("0.12")


class TestGuards:
    """Green on HEAD and on the tree: an ordinary book, ``date_from`` None or inside the history."""

    @pytest.mark.asyncio
    async def test_without_date_from(self, tmp_path):
        """1 000 → 1 050 → 1 120, one deposit on the first day: ROI 0.12, TWRR 0.12; the card is the last point."""
        async with _private_book(tmp_path, YOUNG) as book:
            summary = await _summary(book, None)
            history = await _history(book, None)

        assert summary.simple_roi_percent == D("0.12"), f"simple_roi_percent {summary.simple_roi_percent}"
        assert summary.twrr_percent == D("0.12"), f"twrr_percent {summary.twrr_percent}"
        assert _point_on(history, MAR_05).twrr == summary.twrr_percent, "the card is the line's last point"

    @pytest.mark.asyncio
    async def test_date_from_inside_the_history(self, tmp_path):
        """From 03-04 the period opens on 1 050 and ends on 1 120: ROI and TWRR 70 / 1 050 = 0.066667."""
        async with _private_book(tmp_path, YOUNG) as book:
            summary = await _summary(book, MAR_04)
            history = await _history(book, MAR_04)

        assert summary.simple_roi_percent == D("0.066667"), f"simple_roi_percent {summary.simple_roi_percent}"
        assert summary.twrr_percent == D("0.066667"), f"twrr_percent {summary.twrr_percent}"
        assert _point_on(history, MAR_05).twrr == summary.twrr_percent, "the card is the line's last point"
        assert _point_on(history, MAR_05).roi == summary.simple_roi_percent, "the line's last ROI is the card's"

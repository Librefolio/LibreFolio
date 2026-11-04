"""B3 / MF-J3 — through ``PortfolioService``: a cash transfer seen from a broker-filtered view moves K/R as a DEPOSIT.

The decided rule (developer, wave 6; backlog ``BACKLOG_POST_1.2.md`` «B3» and «MF-J3»): a CASH_TRANSFER / FX_CONVERSION
leg whose other leg is outside the perimeter (``linked_external_inflow`` / ``linked_external_outflow``) or that has
lost its pair moves the pools K (contributed capital) and R (generated returns) exactly as a DEPOSIT (amount > 0) or a
WITHDRAWAL (amount < 0). The pure rule is tested in ``test_portfolio_engine/test_external_cash_leg_pools.py``; here, the
wiring: ``PortfolioService.get_history`` with ``broker_ids`` loads the leg outside the perimeter
(``ScopeAwareTransactionClassifier.get_needed_paired_ids``), so the arrival classifies as ``linked_external_inflow``.

One book (a private SQLite file, the app schema; one user owning 100 % of two brokers A and B; EUR, no FX rate):
A deposits 1000 on D0; a linked CASH_TRANSFER moves 650 from A to B on D1. A second book adds, at B, a DEPOSIT of 100
and an INTEREST of 100 on D0 (K_B 100 / R_B 100 before the transfer).

- ``broker_ids=[B]``, first book: on D1 cash 650, capital baseline 650 -> contributed 650 / generated 0.
  HEAD 3f8e670f2: contributed 0 / generated 650 (the arrival moves no pool; the display gives an empty K nothing).
- ``broker_ids=[B]``, second book: on D1 cash 850, capital baseline 750 -> contributed 750 / generated 100.
  HEAD: K 100 / R 100 against a cash of 850, rescaled x 4.25: 425 / 425.
- Parity pins (green before and after): the whole perimeter {A, B} (the pair is linked-internal, J2's rule: 1000 / 0,
  and 1100 / 100 with B's history); the capital baseline and the NAV of the view {B} on D1.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), as ``test_allocation_non_positive_sum_report.py``: no lane database, no server, no
network. The report, WAC and engine blob caches are emptied before and after each test.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory) and in
``./dev.py test services external-cash-leg-pools``.
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
from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.series_steps import value_at
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1 = date(2025, 9, 1), date(2025, 9, 3)
END = date(2025, 9, 8)
ZERO = Decimal("0")


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_a: int
    broker_b: int


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


@asynccontextmanager
async def _private_book(directory: Path, *, b_history: bool) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf_b3_external_cash_leg.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"mf_b3_{tag}", email=f"mf_b3_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker_a = Broker(name=f"MF-B3 A {tag}")
            broker_b = Broker(name=f"MF-B3 B {tag}")
            session.add_all([user, broker_a, broker_b])
            await session.flush()
            for broker in (broker_a, broker_b):
                session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            departure = Transaction(broker_id=broker_a.id, type=TransactionType.CASH_TRANSFER, date=D1, quantity=ZERO, amount=Decimal("-650"), currency=EUR)
            arrival = Transaction(broker_id=broker_b.id, type=TransactionType.CASH_TRANSFER, date=D1, quantity=ZERO, amount=Decimal("650"), currency=EUR)
            session.add_all([Transaction(broker_id=broker_a.id, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("1000"), currency=EUR), departure, arrival])
            if b_history:
                session.add_all(
                    [
                        Transaction(broker_id=broker_b.id, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("100"), currency=EUR),
                        Transaction(broker_id=broker_b.id, type=TransactionType.INTEREST, date=D0, quantity=ZERO, amount=Decimal("100"), currency=EUR),
                    ]
                )
            await session.flush()
            # A linked pair references itself both ways: the ids exist only after the first flush.
            departure.related_transaction_id, arrival.related_transaction_id = arrival.id, departure.id
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, broker_a=broker_a.id, broker_b=broker_b.id)
        yield book
    finally:
        await engine.dispose()


async def _point_on(book: _Book, day: date, broker_ids: list[int]):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        history = await PortfolioService(session).get_history(book.user_id, broker_ids=broker_ids, date_from=D0, date_to=END, target_currency_override=EUR)
    point = value_at(history, day)
    assert point is not None, f"no history step holds {day} for broker_ids={broker_ids}"
    return point


def _shown(point) -> dict[str, Decimal]:
    return {
        "cash": point.cash_value.amount,
        "capital_baseline": point.capital_baseline.amount,
        "nav": point.nav_value.amount,
        "contributed": point.cash_from_contributed_capital.amount,
        "generated": point.cash_from_generated_returns.amount,
    }


class TestBrokerFilteredView:
    @pytest.mark.asyncio
    async def test_the_arrival_from_outside_the_view_is_contributed_capital(self, tmp_path):
        """View {B}, B empty before D1: 650 arrive from A. Rule: contributed 650 / generated 0. HEAD: 0 / 650."""
        async with _private_book(tmp_path, b_history=False) as book:
            point = await _point_on(book, D1, [book.broker_b])
        shown = _shown(point)
        assert (shown["cash"], shown["capital_baseline"]) == (Decimal("650"), Decimal("650")), f"precondition: cash and capital baseline 650, got {shown}"
        assert (shown["contributed"], shown["generated"]) == (Decimal("650"), ZERO), f"on {D1} (contributed, generated) expected (650, 0), got {shown}"

    @pytest.mark.asyncio
    async def test_the_arrival_keeps_the_returns_the_view_already_had(self, tmp_path):
        """View {B}, B at K 100 / R 100 on D0: +650 from A. Rule: contributed 750 / generated 100. HEAD: 425 / 425."""
        async with _private_book(tmp_path, b_history=True) as book:
            point = await _point_on(book, D1, [book.broker_b])
        shown = _shown(point)
        assert (shown["cash"], shown["capital_baseline"]) == (Decimal("850"), Decimal("750")), f"precondition: cash 850, capital baseline 750, got {shown}"
        assert (shown["contributed"], shown["generated"]) == (Decimal("750"), Decimal("100")), f"on {D1} (contributed, generated) expected (750, 100), got {shown}"


class TestParity:
    """Green before and after the rule."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("b_history", "expected"), [pytest.param(False, ("1000", "1000", "1000", "0"), id="b_empty"), pytest.param(True, ("1200", "1100", "1100", "100"), id="b_with_returns")])
    async def test_the_whole_perimeter_is_unchanged(self, tmp_path, b_history, expected):
        """{A, B}: the pair is linked-internal (J2): A's 650 leave K (A has no returns), B receives K 650. With B's
        history: cash 1200, baseline 1100, contributed 1100 / generated 100."""
        async with _private_book(tmp_path, b_history=b_history) as book:
            point = await _point_on(book, D1, [book.broker_a, book.broker_b])
        shown = _shown(point)
        assert (shown["cash"], shown["capital_baseline"], shown["contributed"], shown["generated"]) == tuple(Decimal(v) for v in expected), f"{D1}: {shown}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("b_history", "baseline", "nav"), [pytest.param(False, "650", "650", id="b_empty"), pytest.param(True, "750", "850", id="b_with_returns")])
    async def test_the_view_capital_baseline_and_nav_do_not_move(self, tmp_path, b_history, baseline, nav):
        async with _private_book(tmp_path, b_history=b_history) as book:
            point = await _point_on(book, D1, [book.broker_b])
        shown = _shown(point)
        assert (shown["capital_baseline"], shown["nav"], point.total_pnl.amount) == (Decimal(baseline), Decimal(nav), Decimal(nav) - Decimal(baseline)), f"{D1}: {shown}"

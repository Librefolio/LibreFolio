"""MF-A3 (workstream MF, wave 6) — the Performance table's annualized column on a closed flight too short to annualize.

What changed. ``PortfolioService.get_positions_contribution`` (``backend/app/services/portfolio/portfolio_service.py``), the
``annualized_return`` of a row:

* MF-A3 — a row fully sold in the period whose closed rule (``closed_position_annualized``) gives no value and whose
  flight in the period (first opening clamped to ``date_from`` → last close) is under 30 days now shows None
  (``closed_flight_too_short``). HEAD ``33b66ba1c`` fell back to the period's general rule, which spreads ten days held
  over the whole year.

(MF-A11, the open row's ``left_base``, was reverted by MF before landing — the numbers did not confirm it — so
this file asserts nothing about it; the name of the file stays as briefed.)

Tests (period 2025-01-01 → 2025-12-31, one EUR stock, the table read in EUR):

- ``test_ten_days_held_in_the_period_is_not_annualized`` (A3, red on HEAD): 100 bought at 10 on 2024-12-01, close
  10 on 2024-12-31 (start value 1 000), all sold for 1 100 on 2025-01-11 — ten days into the period. The closed rule
  needs 30 days and gives None; the row's ``annualized_return`` is None. HEAD: the general rule, +10 % on the start
  value annualized over the year, 0.100288;
- ``test_a_long_flight_without_a_base_keeps_the_general_rule`` (guard, green on both): the same 100 units leave broker
  A on 2025-03-01 (59 days into the period) by a TRANSFER to broker B, outside the table's scope (``broker_ids=[A]``):
  no unit was sold, the closed rule has no base, the flight is long enough, so the general rule stands — the row's P&L
  on its start value 1 100, over the period: −0.091138, on HEAD as on the tree.

Red on HEAD ``33b66ba1c`` (the backend of that commit extracted with ``git archive``, this file copied into it), the
exact messages:

- ``test_ten_days_held_in_the_period_is_not_annualized``: «annualized_return 0.100288 for a position held 10 days in
  the period: too short to annualize».

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): one user owning its brokers at 100 %. Every row is found
by its broker and asset, never by position.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The report (L2),
WAC and engine blob caches (process-global) are emptied around each test. No sleep.

Runs in ``./dev.py test services roi-fifo-utils``; alone:
``./dev.py test services roi-fifo-utils test_positions_contribution_short_flight_and_open_base``.

Reference: backend/app/services/portfolio/portfolio_service.py (get_positions_contribution),
backend/app/services/financial_math/portfolio/contributions.py (annualized_period_return, closed_flight_too_short,
closed_position_base), test_financial_math/test_contributions_short_flight_and_open_base.py (the pure
numbers).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
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
from backend.app.schemas.portfolio import AssetPeriodContribution
from backend.app.services.portfolio import portfolio_service as portfolio_service_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

D = Decimal
EUR = "EUR"

DATE_FROM = date(2025, 1, 1)
DATE_TO = date(2025, 12, 31)


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Scenario:
    """One EUR stock: movements ``(broker, type, day, quantity, amount)``, closes, and one optional linked TRANSFER
    ``(from broker, to broker, day, quantity, unit cost)``."""

    label: str
    brokers: tuple[str, ...]
    movements: tuple[tuple[str, TransactionType, date, str, str], ...]
    closes: tuple[tuple[date, str], ...]
    transfer: tuple[str, str, date, str, str] | None = None
    scope: tuple[str, ...] = ("A",)


#: Held at the period's start (bought 2024-12-01, close 10 on 2024-12-31), all sold ten days into the period.
SHORT_FLIGHT = _Scenario(
    label="short-flight",
    brokers=("A",),
    movements=(("A", TransactionType.DEPOSIT, date(2024, 12, 1), "0", "1000"), ("A", TransactionType.BUY, date(2024, 12, 1), "100", "-1000"), ("A", TransactionType.SELL, date(2025, 1, 11), "-100", "1100")),
    closes=((date(2024, 12, 1), "10"), (date(2024, 12, 31), "10"), (date(2025, 1, 11), "11")),
)
#: Held at the start (close 11 on 2024-12-31: start value 1 100), moved to B — outside the scope — 59 days in.
LONG_FLIGHT_NO_BASE = _Scenario(
    label="long-no-base",
    brokers=("A", "B"),
    movements=(("A", TransactionType.DEPOSIT, date(2024, 12, 1), "0", "1000"), ("A", TransactionType.BUY, date(2024, 12, 1), "100", "-1000")),
    closes=((date(2024, 12, 1), "10"), (date(2024, 12, 31), "11"), (date(2025, 3, 1), "12"), (DATE_TO, "12")),
    transfer=("A", "B", date(2025, 3, 1), "100", "10"),
)


@dataclass
class _Book:
    engine: AsyncEngine
    user_id: int
    asset_id: int
    brokers: dict[str, int] = field(default_factory=dict)


async def _seed(engine: AsyncEngine, scenario: _Scenario) -> _Book:
    """The scenario's ledger, owned by a new user at 100 % of every broker, committed to the private file."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"mfa3_{scenario.label}_{tag}", email=f"mfa3_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"MF-A3 {scenario.label} {label} {tag}") for label in scenario.brokers}
        asset = Asset(display_name=f"MF-A3 {scenario.label} {tag}", currency=EUR, asset_type=AssetType.STOCK)
        session.add_all([user, asset, *brokers.values()])
        await session.flush()
        session.add_all(
            [
                *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")) for broker in brokers.values()),
                *(
                    Transaction(
                        broker_id=brokers[label].id,
                        asset_id=None if kind in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL) else asset.id,
                        type=kind,
                        date=day,
                        quantity=D(quantity),
                        amount=D(amount),
                        currency=EUR,
                    )
                    for label, kind, day, quantity, amount in scenario.movements
                ),
                *(PriceHistory(asset_id=asset.id, date=day, open=D(close), high=D(close), low=D(close), close=D(close), volume=D("1"), currency=EUR, source_plugin_key="mfa3_test") for day, close in scenario.closes),
            ]
        )
        if scenario.transfer is not None:
            giver, receiver, day, quantity, unit_cost = scenario.transfer
            departure = Transaction(broker_id=brokers[giver].id, asset_id=asset.id, type=TransactionType.TRANSFER, date=day, quantity=-D(quantity), amount=D("0"))
            arrival = Transaction(broker_id=brokers[receiver].id, asset_id=asset.id, type=TransactionType.TRANSFER, date=day, quantity=D(quantity), amount=D("0"), cost_basis_override=D(unit_cost), cost_basis_currency=EUR)
            session.add_all([departure, arrival])
            await session.flush()
            # A linked pair references itself both ways: the ids exist only after the first flush
            departure.related_transaction_id = arrival.id
            arrival.related_transaction_id = departure.id
        await session.commit()
        return _Book(engine=engine, user_id=user.id, asset_id=asset.id, brokers={label: broker.id for label, broker in brokers.items()})


@asynccontextmanager
async def _private_book(directory: Path, scenario: _Scenario) -> AsyncIterator[_Book]:
    """The app schema and the scenario's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'mfa3_{scenario.label}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, scenario)
    finally:
        await engine.dispose()


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: each private file numbers its rows from 1."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


async def _row(book: _Book, scenario: _Scenario, broker: str = "A") -> AssetPeriodContribution:
    """The table's row of the book's asset at ``broker``, read in EUR over the period: found by broker and asset."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        table = await PortfolioService(session).get_positions_contribution(
            user_id=book.user_id,
            broker_ids=[book.brokers[label] for label in scenario.scope],
            date_from=DATE_FROM,
            date_to=DATE_TO,
            target_currency_override=EUR,
        )
    rows = [row for row in table.positions if row.broker_id == book.brokers[broker] and row.asset_id == book.asset_id]
    assert len(rows) == 1, f"expected one row of asset {book.asset_id} at broker {broker}, got {[(row.broker_id, row.asset_id) for row in table.positions]}"
    return rows[0]


# =============================================================================
# THE TESTS
# =============================================================================


class TestShortFlight:
    @pytest.mark.asyncio
    async def test_ten_days_held_in_the_period_is_not_annualized(self, tmp_path):
        """+100 on a start value of 1 000, all sold on 2025-01-11: ten days in the period, «—»."""
        async with _private_book(tmp_path, SHORT_FLIGHT) as book:
            row = await _row(book, SHORT_FLIGHT)

        assert row.is_fully_sold, "precondition: the position is closed in the period"
        assert row.start_value == D("1000"), f"precondition: held at the start, worth 1 000; got {row.start_value}"
        assert row.period_pnl == D("100"), f"precondition: +100 realized; got {row.period_pnl}"
        assert row.annualized_return is None, f"annualized_return {row.annualized_return} for a position held 10 days in the period: too short to annualize"

    @pytest.mark.asyncio
    async def test_a_long_flight_without_a_base_keeps_the_general_rule(self, tmp_path):
        """Moved out of the scope 59 days in, nothing sold: no closed base, a long enough flight — the general rule,
        the row's P&L on its start value annualized over the period."""
        async with _private_book(tmp_path, LONG_FLIGHT_NO_BASE) as book:
            row = await _row(book, LONG_FLIGHT_NO_BASE)

        assert row.is_fully_sold, "precondition: nothing left at A"
        assert row.start_value == D("1100"), f"precondition: held at the start, worth 1 100; got {row.start_value}"
        assert row.period_realized_gain_loss is None, f"precondition: nothing sold, got {row.period_realized_gain_loss}"
        assert row.period_pnl == D("-100"), f"precondition: the start unrealized given up, got {row.period_pnl}"
        assert row.annualized_return == D("-0.091138"), f"annualized_return {row.annualized_return}: the general rule, −100 / 1 100 = −0.0909 over the period's 364 days"

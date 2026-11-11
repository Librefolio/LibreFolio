"""MF6-2 (backlog MF-A6) — the Performance rows add up to the summary also with a dust residual.

What changes. The Performance table (``PortfolioService.get_positions_contribution``) treats a quantity ≤
``QUANTITY_DUST_THRESHOLD`` (0.00001) as not held: no end value, no unrealized. The engine's daily state
(``financial_math/portfolio/daily_state.py``) valued every quantity > 0, so the summary's
``period_unrealized_gain_loss_delta`` (ΔUGL = [MV − OCB](t1) − [MV − OCB](t0)) carried the dust's market value − cost
and the identity of the engine documentation §7 («Dust aside») broke: Σ rows' ``period_unrealized_delta`` ≠ ΔUGL. The
fix makes the daily state hold a position only above the threshold; the dust's cost then leaves the NAV, and lands in
the period's residual «Other» (Other = P&L − ΔUGL − Realized − Income + FeesTaxes), by design.

The book (period 2025-01-01 → 2025-12-31, one EUR stock X at one broker, the table read in EUR). Prices are 100 000 a
unit so that the residual's figures are readable cents:

- 2024-12-01: DEPOSIT 1 000 000, BUY 10 X for 1 000 000 (close 100 000; 2024-12-31 close 100 000: start value
  1 000 000, start unrealized 0);
- 2025-06-02: SELL 10 − 0.00001 = 9.99999 X at 120 000 for 1 199 998.80 (close 120 000): realized
  9.99999 × (120 000 − 100 000) = 199 999.80; 0.00001 X left — exactly the threshold, dust;
- 2025-12-31: close 150 000. The dust is worth 0.00001 × 150 000 = 1.50 at a cost of 0.00001 × 100 000 = 1.00.

Expected after the fix / current tree:

- the row: fully sold, end value 0, unrealized delta 0, realized 199 999.80, P&L 199 999.80 (both trees: a
  precondition);
- the summary: ΔUGL 0 / 0.50 (the dust's 1.50 − 1.00); period P&L = NAV_end − NAV_start = 1 199 998.80 − 1 000 000 =
  199 998.80 / 200 000.30 (with the dust's 1.50); Other = 199 998.80 − 0 − 199 999.80 = −1.00 (the dust's cost) /
  200 000.30 − 0.50 − 199 999.80 = 0.

Red on the current tree, green after:

- ``test_the_rows_add_up_to_the_summary_unrealized_delta`` — Σ rows 0 against the summary's 0.50;
- ``test_rows_and_other_effects_close_the_period_pnl`` — rows 199 999.80 + other 0 against the period P&L
  200 000.30 (the same 0.50: Σ rows' P&L + other − P&L == Σ rows' delta − ΔUGL);
- ``test_the_dust_cost_is_the_period_other_result`` — ΔUGL 0, P&L 199 998.80, Other −1.00 against 0.50, 200 000.30, 0.

Each through both paths that build the table: the Dashboard's report (``get_report``, one engine run for the summary
and the table) and the standalone calls (``get_summary`` then ``get_positions_contribution``).

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): one user owning its broker at 100 %. The row is found
by its broker and asset, never by position. Isolation: PURE with respect to the lane — no session on the lane's
database, no server, no network. The report (L2), WAC and engine blob caches (process-global) are emptied around each
test. No sleep.

Runs in ``./dev.py test services roi-fifo-utils``; alone:
``./dev.py test services roi-fifo-utils test_positions_contribution_dust_identity``.

Reference: backend/app/services/portfolio/portfolio_service.py (get_positions_contribution, get_summary),
backend/app/services/financial_math/portfolio/daily_state.py (DailyStateBuilder.build),
test_portfolio_engine/test_daily_state_dust_threshold.py (the engine's numbers),
test_positions_contribution_engine.py (TestInvariant, the same identities without dust).
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
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio.report import PortfolioReportQuery
from backend.app.schemas.portfolio.summary import AssetPeriodContribution, PortfolioSummary, PositionsContribution
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

D = Decimal
ZERO = D("0")
EUR = "EUR"

DATE_FROM = date(2025, 1, 1)
DATE_TO = date(2025, 12, 31)

#: 10 − 0.00001 = 9.99999: leaves exactly the threshold
DUST_SALE = D("10") - QUANTITY_DUST_THRESHOLD

#: (type, day, quantity, amount)
MOVEMENTS: tuple[tuple[TransactionType, date, Decimal, Decimal], ...] = (
    (TransactionType.DEPOSIT, date(2024, 12, 1), ZERO, D("1000000")),
    (TransactionType.BUY, date(2024, 12, 1), D("10"), D("-1000000")),
    (TransactionType.SELL, date(2025, 6, 2), -DUST_SALE, DUST_SALE * D("120000")),  # 1 199 998.80
)
CLOSES: tuple[tuple[date, str], ...] = ((date(2024, 12, 1), "100000"), (date(2024, 12, 31), "100000"), (date(2025, 6, 2), "120000"), (DATE_TO, "150000"))

PATHS = ("report", "standalone")


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_id: int
    asset_id: int


async def _seed(engine: AsyncEngine) -> _Book:
    """The ledger, owned by a new user at 100 % of its broker, committed to the private file."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"mf62_{tag}", email=f"mf62_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker = Broker(name=f"MF6-2 dust {tag}")
        asset = Asset(display_name=f"MF6-2 dust {tag}", currency=EUR, asset_type=AssetType.STOCK)
        session.add_all([user, broker, asset])
        await session.flush()
        session.add_all(
            [
                BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")),
                *(
                    Transaction(
                        broker_id=broker.id,
                        asset_id=None if kind == TransactionType.DEPOSIT else asset.id,
                        type=kind,
                        date=day,
                        quantity=quantity,
                        amount=amount,
                        currency=EUR,
                    )
                    for kind, day, quantity, amount in MOVEMENTS
                ),
                *(PriceHistory(asset_id=asset.id, date=day, open=D(close), high=D(close), low=D(close), close=D(close), volume=D("1"), currency=EUR, source_plugin_key="mf62_test") for day, close in CLOSES),
            ]
        )
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_id=broker.id, asset_id=asset.id)


@asynccontextmanager
async def _private_book(directory: Path) -> AsyncIterator[_Book]:
    """The app schema and the ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf62_dust.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
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


async def _read(book: _Book, path: str) -> tuple[PositionsContribution, PortfolioSummary]:
    """The Performance table and the summary over the period, in EUR, through ``path``."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = PortfolioService(session)
        if path == "report":
            report = await service.get_report(
                book.user_id,
                PortfolioReportQuery(
                    broker_ids=[book.broker_id],
                    date_range=OpenDateRangeModel(start=DATE_FROM, end=DATE_TO),
                    target_currency=EUR,
                    include_summary=True,
                    include_history=False,
                    include_allocation_history=False,
                    include_breakdown=False,
                    include_positions_contribution=True,
                ),
            )
            contribution, summary = report.positions_contribution, report.summary
            assert contribution is not None and summary is not None, "the report includes what it was asked for"
        else:
            # The summary first, as a Dashboard would (see test_positions_contribution_engine.py, _read)
            summary = await service.get_summary(user_id=book.user_id, broker_ids=[book.broker_id], target_currency_override=EUR, date_from=DATE_FROM, date_to=DATE_TO)
            contribution = await service.get_positions_contribution(user_id=book.user_id, broker_ids=[book.broker_id], date_from=DATE_FROM, date_to=DATE_TO, target_currency_override=EUR)
    return contribution, summary


def _row(contribution: PositionsContribution, book: _Book) -> AssetPeriodContribution:
    """The row of X at the book's broker, and a check that every row is the book's."""
    foreign = [(row.broker_id, row.asset_id) for row in contribution.positions if (row.broker_id, row.asset_id) != (book.broker_id, book.asset_id)]
    assert not foreign, f"rows that are not the book's: {foreign}"
    rows = [row for row in contribution.positions if (row.broker_id, row.asset_id) == (book.broker_id, book.asset_id)]
    assert len(rows) == 1, f"expected one row of X at the broker, got {len(rows)}"
    return rows[0]


def _assert_the_scenario(row: AssetPeriodContribution) -> None:
    """Precondition, green on both trees: the row sold 9.99999 X with a realized 199 999.80 and holds nothing at the end."""
    assert row.start_value == D("1000000"), f"precondition: 10 X × 100 000 at the start, got {row.start_value}"
    assert row.is_fully_sold, "precondition: the 0.00001 X left is dust, so the row is fully sold"
    assert row.end_value == ZERO, f"precondition: the row values the dust at 0, got {row.end_value}"
    assert row.period_realized_gain_loss == D("199999.80"), f"precondition: 9.99999 × (120 000 − 100 000), got {row.period_realized_gain_loss}"
    assert (row.period_unrealized_delta or ZERO) == ZERO, f"precondition: the row's unrealized delta 0 − 0, got {row.period_unrealized_delta}"


# =============================================================================
# THE TESTS
# =============================================================================


class TestDustIdentity:
    """§7 with a dust residual at the period's end: the rows add up to the engine."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PATHS)
    async def test_the_rows_add_up_to_the_summary_unrealized_delta(self, tmp_path, path):
        """Σ rows' ``period_unrealized_delta`` (0) == the summary's ``period_unrealized_gain_loss_delta``."""
        async with _private_book(tmp_path) as book:
            contribution, summary = await _read(book, path)
            row = _row(contribution, book)

        _assert_the_scenario(row)
        rows_delta = sum((r.period_unrealized_delta or ZERO for r in contribution.positions), ZERO)
        assert summary.period_unrealized_gain_loss_delta is not None
        assert rows_delta == summary.period_unrealized_gain_loss_delta.amount, f"Σ rows' unrealized delta {rows_delta} ≠ summary ΔUGL {summary.period_unrealized_gain_loss_delta.amount}: the dust's 1.50 − 1.00 valued by the engine"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PATHS)
    async def test_rows_and_other_effects_close_the_period_pnl(self, tmp_path, path):
        """Σ rows' ``period_pnl`` + Σ ``other_effects`` == the summary's ``period_pnl``, up to ``CONVERSION_DUST`` per
        hidden row (the broker's FX-on-cash row and the residual), as TestInvariant of the MF-A file."""
        async with _private_book(tmp_path) as book:
            contribution, summary = await _read(book, path)
            row = _row(contribution, book)

        _assert_the_scenario(row)
        rows_pnl = sum((r.period_pnl or ZERO for r in contribution.positions), ZERO)
        other = sum((effect.period_pnl for effect in contribution.other_effects), ZERO)
        assert summary.period_pnl is not None
        gap = rows_pnl + other - summary.period_pnl.amount
        assert abs(gap) <= CONVERSION_DUST * 2, f"rows {rows_pnl} + other {other} = {rows_pnl + other} ≠ period P&L {summary.period_pnl.amount} (gap {gap})"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PATHS)
    async def test_the_dust_cost_is_the_period_other_result(self, tmp_path, path):
        """ΔUGL 0; P&L = 1 199 998.80 − 1 000 000 = 199 998.80; Other = 199 998.80 − 0 − 199 999.80 = −1.00, the dust's
        cost (0.00001 × 100 000)."""
        async with _private_book(tmp_path) as book:
            contribution, summary = await _read(book, path)
            row = _row(contribution, book)

        _assert_the_scenario(row)
        figures = {
            "period_unrealized_gain_loss_delta": None if summary.period_unrealized_gain_loss_delta is None else summary.period_unrealized_gain_loss_delta.amount,
            "period_realized_gain_loss": None if summary.period_realized_gain_loss is None else summary.period_realized_gain_loss.amount,
            "period_pnl": None if summary.period_pnl is None else summary.period_pnl.amount,
            "period_other_result": None if summary.period_other_result is None else summary.period_other_result.amount,
        }
        assert figures == {
            "period_unrealized_gain_loss_delta": ZERO,
            "period_realized_gain_loss": D("199999.80"),
            "period_pnl": D("199998.80"),
            "period_other_result": D("-1.00"),
        }, f"summary {figures}: the dust valued at 1.50 in the NAV instead of its cost 1.00 left to Other"

"""
MF5-3 · B5 — the Performance waterfall gives securities that cross the scope at market value a row of their own.

A TRANSFER leg whose partner sits at a broker outside the selected ones is in-kind capital at market value on its date
(lot 41, D2/D5: ``DailyStateBuilder._transfer_leg_capital``), while the position's cost moves by the leg's cost step.
So in a view filtered on the sender the period identity ``pnl = ugl_delta + realized + income − fees + other`` leaves
MV − cost in «other» (the gain accrued at the sender), for the receiver cost − MV. Today
``PortfolioService.get_positions_contribution`` shows it inside «Other / reconciliation residual».

The contract (service part): when the period's other result is computed, after the «FX on cash» rows and before the
residual, one ``OtherPeriodEffect(description="Transfers at market value", category="Other", period_pnl=<amount>,
broker_id=<id>, broker_name=<name>)`` per broker of ``market_value_transfer_results(engine_result.market_value_transfers,
date_from, effective_end)``, in broker access order (the FX rows' order), skipped when |amount| < CONVERSION_DUST; the
residual drops by every amount shown. ``get_report(include_positions_contribution=True)`` returns the same rows.

The book (report EUR, every amount exact): user U owns brokers A and B (and C for the order test); X, an EUR stock,
closes at 50 on 2025-03-01, 60 from 03-02, 80 from 03-10, 90 from 03-15. A deposits 1000 and buys 10 X for 500 on
03-01; on 03-10 a TRANSFER pair moves the 10 X from A to B, both legs carrying 50 EUR a unit. Period 03-02..03-15.

- (a) view A only: A's leg is ``linked_external_outflow``, capital −800, cost −500: a row (A) of +300 = MV − cost on
  the transfer day, and no residual left (absent, or below CONVERSION_DUST). Today: the +300 sits in the residual.
  Also through ``get_report``, where the rows of category Other still add up to the summary's period_other_result.
- (b) view B only: B's leg is ``linked_external_inflow``, capital +800, cost +500: a row (B) of −300.
- (c) both brokers: the pair is internal (B8), no such row, and no residual either — as today (guard).
- (d) the transfer before the period start (date_from 03-12): no such row in either single-broker view (guard).
- (e) A and B both send to C, outside the view, with an unallocated interest at A: two rows, in the order the service
  reads the user's accesses (read from the service itself, never assumed), after the unallocated income row.

Rows are identified by ``description`` / ``category`` / ``broker_id`` — API keys, not translated text.

Red on HEAD b6a25adcb: (a), (b), (a) through ``get_report`` and (e) — no «Transfers at market value» row; the amount is
in «Other / reconciliation residual». (c) and (d) are guards, green before and after the cure.

Isolation: PURE with respect to the lane — every database is a private SQLite file under ``tmp_path`` (the app schema,
``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no server, no network. The report,
WAC and engine blob caches are emptied around each test. No sleep, no wall-clock assertion, no translated text.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).

Reference: backend/app/services/portfolio_service.py (get_positions_contribution),
backend/app/services/financial_math/portfolio/daily_state.py (_transfer_leg_capital),
backend/test_scripts/test_services/test_financial_math/test_market_value_transfers.py (the records and the period
function, pure).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
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
from backend.app.schemas.portfolio import OtherPeriodEffect, PortfolioReportQuery, PositionsContribution
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
TRANSFER_ROW = "Transfers at market value"
RESIDUAL_ROW = "Other / reconciliation residual"

PRICE_START = date(2025, 3, 1)
PRICE_END = date(2025, 3, 20)
BUY_DAY = date(2025, 3, 1)
PERIOD_FROM = date(2025, 3, 2)
TRANSFER_DAY = date(2025, 3, 10)
SECOND_TRANSFER_DAY = date(2025, 3, 11)
PERIOD_TO = date(2025, 3, 15)
AFTER_TRANSFER = date(2025, 3, 12)


def _close(day: date) -> Decimal:
    if day < date(2025, 3, 2):
        return Decimal("50")
    if day < TRANSFER_DAY:
        return Decimal("60")
    if day < date(2025, 3, 15):
        return Decimal("80")
    return Decimal("90")


# =============================================================================
# PRIVATE DATABASE
# =============================================================================


@asynccontextmanager
async def _private_engine(directory: Path, name: str) -> AsyncIterator[AsyncEngine]:
    """The app schema on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'b5_{name}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    brokers: dict[str, int]
    broker_names: dict[int, str]


def _row(broker: Broker, tx_type: TransactionType, day: date, *, amount: str = "0", currency: str | None = EUR, asset: Asset | None = None, quantity: str = "0", unit_cost: str | None = None) -> Transaction:
    return Transaction(
        broker_id=broker.id,
        asset_id=asset.id if asset else None,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        cost_basis_override=Decimal(unit_cost) if unit_cost is not None else None,
        cost_basis_currency=EUR if unit_cost is not None else None,
    )


async def _link(session: AsyncSession, sent: Transaction, received: Transaction) -> None:
    session.add_all([sent, received])
    await session.flush()
    sent.related_transaction_id, received.related_transaction_id = received.id, sent.id


async def _seed(engine: AsyncEngine, *, order_book: bool = False) -> _Book:
    """The module docstring's book; with ``order_book``, B also buys 4 X for 200, A sends its 10 X to C on 03-10 and B its
    4 X to C on 03-11 (no A→B pair), and A books an interest of 7 EUR with no asset on 03-05."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"b5_{tag}", email=f"b5_{tag}@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"B5 {label} {tag}") for label in ("A", "B", "C")}
        stock = Asset(display_name=f"B5 X {tag}", currency=EUR, asset_type=AssetType.STOCK)
        session.add_all([user, stock, *brokers.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])
        day = PRICE_START
        while day <= PRICE_END:
            close = _close(day)
            session.add(PriceHistory(asset_id=stock.id, date=day, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="b5_mvt"))
            day += timedelta(days=1)
        a, b, c = brokers["A"], brokers["B"], brokers["C"]
        session.add_all([_row(a, TransactionType.DEPOSIT, BUY_DAY, amount="1000"), _row(a, TransactionType.BUY, BUY_DAY, amount="-500", asset=stock, quantity="10")])
        if not order_book:
            await _link(
                session,
                _row(a, TransactionType.TRANSFER, TRANSFER_DAY, currency=None, asset=stock, quantity="-10", unit_cost="50"),
                _row(b, TransactionType.TRANSFER, TRANSFER_DAY, currency=None, asset=stock, quantity="10", unit_cost="50"),
            )
        else:
            session.add_all(
                [
                    _row(b, TransactionType.DEPOSIT, BUY_DAY, amount="200"),
                    _row(b, TransactionType.BUY, BUY_DAY, amount="-200", asset=stock, quantity="4"),
                    _row(a, TransactionType.INTEREST, date(2025, 3, 5), amount="7"),
                ]
            )
            await _link(
                session,
                _row(a, TransactionType.TRANSFER, TRANSFER_DAY, currency=None, asset=stock, quantity="-10", unit_cost="50"),
                _row(c, TransactionType.TRANSFER, TRANSFER_DAY, currency=None, asset=stock, quantity="10", unit_cost="50"),
            )
            await _link(
                session,
                _row(b, TransactionType.TRANSFER, SECOND_TRANSFER_DAY, currency=None, asset=stock, quantity="-4", unit_cost="50"),
                _row(c, TransactionType.TRANSFER, SECOND_TRANSFER_DAY, currency=None, asset=stock, quantity="4", unit_cost="50"),
            )
        await session.commit()
        return _Book(engine=engine, user_id=user.id, brokers={label: broker.id for label, broker in brokers.items()}, broker_names={broker.id: broker.name for broker in brokers.values()})


async def _contribution(book: _Book, labels: tuple[str, ...], date_from: date = PERIOD_FROM, date_to: date = PERIOD_TO) -> PositionsContribution:
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_positions_contribution(book.user_id, broker_ids=[book.brokers[label] for label in labels], date_from=date_from, date_to=date_to, target_currency_override=EUR)


# =============================================================================
# ROW HELPERS
# =============================================================================


def _rows(contribution: PositionsContribution) -> list[tuple]:
    return [(row.description, row.category, row.period_pnl, row.broker_id, row.broker_name) for row in contribution.other_effects]


def _transfer_rows(contribution: PositionsContribution) -> list[OtherPeriodEffect]:
    return [row for row in contribution.other_effects if row.description == TRANSFER_ROW]


def _residual_problems(contribution: PositionsContribution) -> list[str]:
    """No residual left: the row absent, or below CONVERSION_DUST."""
    residuals = [row for row in contribution.other_effects if row.description == RESIDUAL_ROW]
    if len(residuals) > 1:
        return [f"more than one residual row: {_rows(contribution)}"]
    if residuals and abs(residuals[0].period_pnl) >= CONVERSION_DUST:
        return [f"the residual still holds {residuals[0].period_pnl}: {_rows(contribution)}"]
    return []


def _one_transfer_row_problems(book: _Book, contribution: PositionsContribution, label: str, amount: str) -> list[str]:
    broker_id = book.brokers[label]
    rows = _transfer_rows(contribution)
    want = [(TRANSFER_ROW, "Other", Decimal(amount), broker_id, book.broker_names[broker_id])]
    got = [(row.description, row.category, row.period_pnl, row.broker_id, row.broker_name) for row in rows]
    return [] if got == want else [f"«{TRANSFER_ROW}» rows expected {want}, got {got}; every other_effects row: {_rows(contribution)}"]


# =============================================================================
# TESTS
# =============================================================================


class TestTransfersAtMarketValueRow:
    @pytest.mark.asyncio
    async def test_a_view_on_the_sender_shows_mv_minus_cost(self, tmp_path):
        """(a) A only: A's 10 X (cost 500) leave on 03-10 worth 800 → a row (A) of +300, no residual left.
        Today: no such row, «Other / reconciliation residual» +300."""
        async with _private_engine(tmp_path, "sender") as engine:
            book = await _seed(engine)
            contribution = await _contribution(book, ("A",))
        problems = _one_transfer_row_problems(book, contribution, "A", "300") + _residual_problems(contribution)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_a_view_on_the_receiver_shows_cost_minus_mv(self, tmp_path):
        """(b) B only: the 10 X arrive on 03-10 worth 800 with a cost of 500 → a row (B) of −300, no residual left.
        Today: no such row, «Other / reconciliation residual» −300."""
        async with _private_engine(tmp_path, "receiver") as engine:
            book = await _seed(engine)
            contribution = await _contribution(book, ("B",))
        problems = _one_transfer_row_problems(book, contribution, "B", "-300") + _residual_problems(contribution)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_the_report_returns_the_same_row_and_still_adds_up_to_the_summary(self, tmp_path):
        """(a) through ``get_report(include_positions_contribution=True)``: the same row (A, +300), no residual left, and
        the rows of category Other add up to the summary's period_other_result (the FX on cash rule kept)."""
        async with _private_engine(tmp_path, "report") as engine:
            book = await _seed(engine)
            query = PortfolioReportQuery(
                broker_ids=[book.brokers["A"]],
                date_range=OpenDateRangeModel(start=PERIOD_FROM, end=PERIOD_TO),
                target_currency=EUR,
                include_summary=True,
                include_positions_contribution=True,
            )
            async with AsyncSession(engine, expire_on_commit=False) as session:
                report = await PortfolioService(session).get_report(book.user_id, query)
        contribution = report.positions_contribution
        assert contribution is not None and report.summary is not None, "precondition: the report has a summary and a contribution"
        assert report.summary.period_other_result is not None, "precondition: the summary computes the period's other result"
        problems = _one_transfer_row_problems(book, contribution, "A", "300") + _residual_problems(contribution)
        shown = sum((row.period_pnl for row in contribution.other_effects if row.category == "Other"), Decimal("0"))
        if abs(shown - report.summary.period_other_result.amount) >= CONVERSION_DUST:
            problems.append(f"the Other rows add up to {shown}, the summary's period_other_result is {report.summary.period_other_result.amount}")
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_both_brokers_show_no_such_row(self, tmp_path):
        """(c) A and B: the pair is internal (B8), the capital stays in the scope; no row, no residual. Green on HEAD."""
        async with _private_engine(tmp_path, "both") as engine:
            book = await _seed(engine)
            contribution = await _contribution(book, ("A", "B"))
        assert contribution.positions, "precondition: the view has position rows"
        problems = ([] if not _transfer_rows(contribution) else [f"unexpected «{TRANSFER_ROW}» rows: {_rows(contribution)}"]) + _residual_problems(contribution)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("label", ["A", "B"])
    async def test_a_transfer_before_the_period_gives_no_row(self, tmp_path, label):
        """(d) date_from 03-12, after the transfer: neither single-broker view shows the row (nor a residual). Green on HEAD."""
        async with _private_engine(tmp_path, f"before_{label}") as engine:
            book = await _seed(engine)
            contribution = await _contribution(book, (label,), date_from=AFTER_TRANSFER)
        problems = ([] if not _transfer_rows(contribution) else [f"unexpected «{TRANSFER_ROW}» rows: {_rows(contribution)}"]) + _residual_problems(contribution)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_one_row_per_broker_in_access_order_after_unallocated_income(self, tmp_path):
        """(e) A and B in view, both send to C (outside it): A +300 (10 X of cost 500 worth 800 on 03-10), B +120 (4 X of
        cost 200 worth 320 on 03-11), in the order the service reads the user's accesses, after A's «Unallocated income»
        (the interest of 7 with no asset); no residual left. Today: no such row, the residual +420."""
        async with _private_engine(tmp_path, "order") as engine:
            book = await _seed(engine, order_book=True)
            in_view = [book.brokers["A"], book.brokers["B"]]
            async with AsyncSession(engine, expire_on_commit=False) as session:
                accesses = await PortfolioService(session)._get_user_broker_access(book.user_id, in_view)
            contribution = await _contribution(book, ("A", "B"))
        amounts = {book.brokers["A"]: Decimal("300"), book.brokers["B"]: Decimal("120")}
        access_order = [access.broker_id for access in accesses if access.broker_id in amounts]
        assert sorted(access_order) == sorted(amounts), f"precondition: the service reads both accesses, got {access_order}"
        want = [(TRANSFER_ROW, "Other", amounts[broker_id], broker_id, book.broker_names[broker_id]) for broker_id in access_order]
        got = [(row.description, row.category, row.period_pnl, row.broker_id, row.broker_name) for row in _transfer_rows(contribution)]
        problems = [] if got == want else [f"«{TRANSFER_ROW}» rows expected {want}, got {got}; every row: {_rows(contribution)}"]
        descriptions = [row.description for row in contribution.other_effects]
        if "Unallocated income" not in descriptions:
            problems.append(f"precondition: A's unallocated income row is missing: {_rows(contribution)}")
        elif TRANSFER_ROW in descriptions and descriptions.index(TRANSFER_ROW) < descriptions.index("Unallocated income"):
            problems.append(f"the transfer rows come before the unallocated income row: {descriptions}")
        problems += _residual_problems(contribution)
        assert not problems, "\n".join(problems)

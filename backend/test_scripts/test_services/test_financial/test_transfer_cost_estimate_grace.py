"""W-B94 road (b) — the TRANSACTION_IMPLIED grace of an asset priced by the cost of the transfer that brought it in.

Through ``PortfolioService.get_summary`` (``backend/app/services/portfolio/portfolio_service.py``, section «6. Data quality report»)
and ``financial_math.portfolio.data_quality.transaction_implied_assets_to_report``.

With W-B94 an asset that has no quote and no other operation, received by an incoming TRANSFER with a cost, is valued
at that cost as an estimated price (``LAST_TRADE_PRICE``), so it is transaction-implied. The data-quality report lists a
transaction-implied asset with a provider under TRANSACTION_IMPLIED only after ``TRANSACTION_IMPLIED_GRACE_DAYS`` (14),
counted from its last market quote or, never quoted, from its first position date — which held only BUY/SELL dates. An
asset that arrived by a transfer has none, so it was listed from its first day, with no grace. The fix: with no BUY or
SELL, the grace counts from the asset's first lot movement, the arrival (as VALUED_AT_COST's grace does); an asset with
trades keeps its BUY/SELL date.

Book (a private SQLite file, the app schema): one user owning 100 % of one broker; one EUR stock WITH a price provider
assignment (yfinance) and no price rows; on D an orphan TRANSFER-in of 10 units at a cost basis of 50 EUR. The summary is
read with ``date_to`` = D + n. Every test first proves, through the holding row, that the asset is valued at the
transfer-cost estimate (LAST_TRADE_PRICE, 500 EUR), so an absent listing can only come from the grace.

- D+5 and D+14 (within the grace): neither TRANSACTION_IMPLIED nor VALUED_AT_COST. RED without the fix: listed under
  TRANSACTION_IMPLIED on D+5 (no first position date → listed at once).
- D+15 and D+20 (past it): listed under TRANSACTION_IMPLIED, not VALUED_AT_COST. Green with and without the fix.
- Parity guard (green with and without the fix): the same arrival, then a BUY at 55 on D+10, read on D+20 — the grace
  counts from the BUY (10 days), not from the arrival (20 days): not listed.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), as ``test_external_cash_leg_pools_service.py``: no lane database, no server, no network.
The report, WAC and engine blob caches are emptied before and after each test.

Runs in ``./dev.py test services roi-fifo-utils`` (the whole ``test_financial/``) and in
``./dev.py test services transfer-cost-estimate``.
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
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, ProviderInputType, Transaction, TransactionType, User, UserRole
from backend.app.services.platform.data_quality_thresholds import TRANSACTION_IMPLIED_GRACE_DAYS
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

EUR = "EUR"
D = date(2025, 6, 2)
GRACE = TRANSACTION_IMPLIED_GRACE_DAYS


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    asset_id: int


def _clear_portfolio_caches() -> None:
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


@asynccontextmanager
async def _private_book(directory: Path, *, buy_after_days: int | None = None) -> AsyncIterator[_Book]:
    """The book above; ``buy_after_days`` adds a BUY of 10 at 55 EUR on D + that many days (cash deposited first)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'wb94_transfer_grace.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"wb94_{tag}", email=f"wb94_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"W-B94 grace {tag}")
            asset = Asset(display_name=f"W-B94 transferred {tag}", currency=EUR, asset_type=AssetType.STOCK, identifier_ticker=f"WB{tag[:6]}".upper())
            session.add_all([user, broker, asset])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            session.add(AssetProviderAssignment(asset_id=asset.id, provider_code="yfinance", identifier=asset.identifier_ticker, identifier_type=ProviderInputType.TICKER))
            # The orphan TRANSFER-in: no partner, no amount, a cost basis of 50 EUR a unit
            session.add(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=D, quantity=Decimal("10"), cost_basis_override=Decimal("50"), cost_basis_currency=EUR))
            if buy_after_days is not None:
                buy_day = D + timedelta(days=buy_after_days)
                session.add_all(
                    [
                        Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=buy_day, quantity=Decimal("0"), amount=Decimal("550"), currency=EUR),
                        Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=buy_day, quantity=Decimal("10"), amount=Decimal("-550"), currency=EUR),
                    ]
                )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, asset_id=asset.id)
        yield book
    finally:
        await engine.dispose()


async def _summary(book: _Book, days_after_d: int):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_summary(user_id=book.user_id, date_to=D + timedelta(days=days_after_d), target_currency_override=EUR)


def _listed_ids(summary, code: str) -> set[int]:
    issue = next((issue for issue in summary.data_quality.issues if issue.code == code), None)
    return set(issue.affected_asset_ids) if issue is not None else set()


def _assert_valued_at_the_transfer_cost(summary, asset_id: int, value: str = "500") -> None:
    """Barrier: the asset is held and valued at a trade-derived mark (the transfer-cost estimate, or a later BUY)."""
    rows = [holding for holding in summary.holdings if holding.asset_id == asset_id]
    assert len(rows) == 1, f"expected exactly one open holding of asset {asset_id}, got {rows}"
    assert (rows[0].valuation_source, rows[0].current_value) == ("LAST_TRADE_PRICE", Decimal(value)), f"barrier: the asset must be valued at its trade-derived mark ({value} EUR), got {(rows[0].valuation_source, rows[0].current_value)}"


class TestGraceFromTheArrival:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("days_after_d", [pytest.param(5, id="d+5"), pytest.param(GRACE, id="d+14-last-day-of-grace")])
    async def test_within_the_grace_it_is_not_listed(self, tmp_path, days_after_d):
        """On D+5 and D+14 the asset is in neither TRANSACTION_IMPLIED nor VALUED_AT_COST.

        Without the fix: listed under TRANSACTION_IMPLIED (no BUY/SELL, so no first position date: listed at once)."""
        async with _private_book(tmp_path) as book:
            summary = await _summary(book, days_after_d)
        _assert_valued_at_the_transfer_cost(summary, book.asset_id)
        listed = {code: book.asset_id in _listed_ids(summary, code) for code in ("TRANSACTION_IMPLIED", "VALUED_AT_COST")}
        assert listed == {"TRANSACTION_IMPLIED": False, "VALUED_AT_COST": False}, f"D+{days_after_d}: listed {listed}, expected in neither (the grace counts from the arrival on {D})"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("days_after_d", [pytest.param(GRACE + 1, id="d+15-first-day-past-grace"), pytest.param(20, id="d+20")])
    async def test_past_the_grace_it_is_listed_as_transaction_implied(self, tmp_path, days_after_d):
        """On D+15 and D+20 the asset is listed under TRANSACTION_IMPLIED, not under VALUED_AT_COST (it has a price)."""
        async with _private_book(tmp_path) as book:
            summary = await _summary(book, days_after_d)
        _assert_valued_at_the_transfer_cost(summary, book.asset_id)
        listed = {code: book.asset_id in _listed_ids(summary, code) for code in ("TRANSACTION_IMPLIED", "VALUED_AT_COST")}
        assert listed == {"TRANSACTION_IMPLIED": True, "VALUED_AT_COST": False}, f"D+{days_after_d}: listed {listed}"


class TestAnAssetWithTradesKeepsItsBuyDate:
    @pytest.mark.asyncio
    async def test_the_grace_counts_from_the_buy_not_from_the_arrival(self, tmp_path):
        """Parity guard: arrival on D, BUY of 10 at 55 on D+10, read on D+20 — valued at the BUY's 55 (20 units, 1100);
        the grace counts from the BUY (10 days ≤ 14), not from the arrival (20 days): not listed."""
        async with _private_book(tmp_path, buy_after_days=10) as book:
            summary = await _summary(book, 20)
        _assert_valued_at_the_transfer_cost(summary, book.asset_id, value="1100")
        assert book.asset_id not in _listed_ids(summary, "TRANSACTION_IMPLIED"), "the grace of an asset with a BUY counts from the BUY"

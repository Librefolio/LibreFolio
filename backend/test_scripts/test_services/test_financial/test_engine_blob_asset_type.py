"""
The engine's blob cache follows the type of the held assets (lane 80, lot B1a-0).

What it guards. ``PortfolioCalculationEngine.calculate`` keeps its result in ``_portfolio_blob_cache`` (24 h) under a key
of fingerprints: transactions, prices, FX, splits, the profile's countries and sectors, the accesses. The result splits
each day's value by asset type (``DailyPortfolioState.by_type``), yet the key held no fingerprint of the types: an edit
of an asset's type changes no transaction, price or rate, so the engine kept answering with the old type. The report's
Layer-2 key has its own asset fingerprint, so the report missed, ran the engine again, and the engine's blob gave the
old type back: the «By type» pie showed the old type for up to 24 hours. The key now carries the ``(id, asset_type)``
of the held assets.

- ``test_nothing_changed_is_the_cached_object`` — the control: the same run twice returns the SAME result object.
- ``test_a_type_change_is_seen_by_the_next_run`` — the ETF becomes an ETF_BOND: the next run is a new object, and its
  last day's ``by_type`` holds ETF_BOND, not ETF.
- ``test_a_type_change_is_seen_by_the_next_report`` — the same through ``get_report``: ``allocation_by_type`` names the
  new type.

The book, on a private SQLite file under ``tmp_path`` (the app schema, NullPool, disposed after): a user, one broker at
100 %, a DEPOSIT and a BUY of one EUR ETF with a close. Isolation: PURE with respect to the lane — no lane database, no
server, no network; the L2, WAC and engine blob caches (process-global) are emptied before and after each test. No
sleep, no wall-clock assertion.

RED on HEAD 17397f5a5: the second and third tests get the cached object (or its old ``by_type``) after the edit.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_engine_blob_asset_type``.
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
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio.report import PortfolioReportQuery
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import PortfolioCalculationResult
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1 = date(2025, 9, 1), date(2025, 9, 3)
END = date(2025, 9, 15)
ZERO = Decimal("0")


def _clear_portfolio_caches() -> None:
    for cache in (report_module._portfolio_l2_cache, wac_module._wac_cache, portfolio_engine_module._portfolio_blob_cache):
        cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    asset_id: int


@asynccontextmanager
async def _book(directory: Path) -> AsyncIterator[_Book]:
    """A user holding one ETF, on a private SQLite file; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'engine_blob_asset_type.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"b1a0_{tag}", email=f"b1a0_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"B1a-0 asset type {tag}")
            asset = Asset(display_name=f"B1a-0 etf {tag}", currency=EUR, asset_type=AssetType.ETF)
            session.add_all([user, broker, asset])
            await session.flush()
            close = Decimal("10")
            session.add_all(
                [
                    BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=D1, quantity=Decimal("30"), amount=Decimal("-300"), currency=EUR),
                    PriceHistory(asset_id=asset.id, date=D1, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="b1a0_asset_type_test"),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, asset_id=asset.id)
        yield book
    finally:
        await engine.dispose()


async def _run(book: _Book) -> PortfolioCalculationResult:
    """One engine run on its own session, D0..END in EUR."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, date_from=D0, date_to=END, target_currency=EUR)


async def _retype(book: _Book, asset_type: AssetType) -> None:
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        await session.execute(update(Asset).where(Asset.id == book.asset_id).values(asset_type=asset_type))
        await session.commit()


def _types(result: PortfolioCalculationResult) -> set[str]:
    """The asset types of the last day's allocation that hold value (the cash is Liquidity)."""
    assert len(result.daily_states) > 0, "precondition: the run has states"
    return {name for name, amount in result.daily_states[-1].by_type.items() if amount != 0 and name != "Liquidity"}


class TestTheEngineCacheFollowsTheAssetType:
    @pytest.mark.asyncio
    async def test_nothing_changed_is_the_cached_object(self, tmp_path):
        async with _book(tmp_path) as book:
            first = await _run(book)
            second = await _run(book)
        served_from_cache = second is first  # a bool, so a red does not print two whole results
        assert served_from_cache, "the control: with nothing changed the second run is the one the blob cache stored"
        assert _types(first) == {"ETF"}, "precondition: the asset's type is read"

    @pytest.mark.asyncio
    async def test_a_type_change_is_seen_by_the_next_run(self, tmp_path):
        async with _book(tmp_path) as book:
            before = await _run(book)
            assert _types(before) == {"ETF"}, "precondition"
            await _retype(book, AssetType.ETF_BOND)
            after = await _run(book)
        served_from_cache = after is before
        assert not served_from_cache, "a type edit must not be answered by the run cached before it"
        assert _types(after) == {"ETF_BOND"}, f"the last day's by_type follows the new type: {_types(after)}"

    @pytest.mark.asyncio
    async def test_the_run_and_its_cached_copy_carry_the_types_and_profiles(self, tmp_path):
        """Lane 80, B1a: the result carries the maps the replay split by, and the blob cache keeps them."""
        async with _book(tmp_path) as book:
            first = await _run(book)
            second = await _run(book)
        assert second is first, "precondition: the second run is the cached one"
        assert second.asset_types == {book.asset_id: "ETF"}
        assert dict(second.asset_classifications) == {book.asset_id: None}, "no profile row: None, both voices unknown"

    @pytest.mark.asyncio
    async def test_a_type_change_is_seen_by_the_next_report(self, tmp_path):
        query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=D0, end=END), target_currency=EUR, include_summary=True)
        async with _book(tmp_path) as book:
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                before = await PortfolioService(session).get_report(book.user_id, query)
            assert before.summary is not None and "ETF" in {item.name for item in before.summary.allocation_by_type}, "precondition"
            await _retype(book, AssetType.ETF_BOND)
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                after = await PortfolioService(session).get_report(book.user_id, query)
        assert after.summary is not None
        names = {item.name for item in after.summary.allocation_by_type if item.amount != 0}
        assert names == {"ETF_BOND", "Liquidity"}, f"the «By type» pie names the new type: {names}"

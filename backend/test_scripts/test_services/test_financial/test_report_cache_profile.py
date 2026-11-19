"""
The portfolio report's Layer-2 cache follows the asset profile's countries and sectors (project 68, lot D2b).

What it guards. ``PortfolioService.get_report`` keeps its answer in ``_portfolio_l2_cache`` (30 min) under a key of
fingerprints. Since D2 the engine reads each asset's countries and sectors from the profile (``asset_profile_updates``,
voices ``geography`` and ``sector``), as steps over the period; the key's ``asset_fp`` hashed ``classification_params``
instead, so a new profile row (an enricher's read, a hand edit) or a forgotten one («Dimentica») left the report cached
for up to 30 minutes with the old allocation. The key now carries the fingerprint of the profile rows of those two voices
for the assets of the scope (``store.rows_fingerprint``: count, sum of ids, latest ``created_at``), and no longer the
column.

- ``test_nothing_changed_is_the_cached_object`` — the control: the same query twice returns the SAME object.
- ``test_a_new_profile_row_is_seen_by_the_next_report`` — a geography row read on the last day (all Japan): the next
  report is a new object, and its current geography is Japan.
- ``test_a_forgotten_profile_row_is_seen_by_the_next_report`` — the only geography row deleted: a new object, the
  geography Unknown.
- (``test_the_old_column_alone_no_longer_moves_the_key`` went with the column, plan 68 D7b.)

The book, on a private SQLite file under ``tmp_path`` (the app schema, NullPool, disposed after): a user, one broker at
100 %, a DEPOSIT and a BUY of one EUR ETF with a close, its geography «all USA» read on the BUY's day. Isolation: PURE
with respect to the lane — no lane database, no server, no network; the L2, WAC and engine blob caches (process-global)
are emptied before and after each test. No sleep, no wall-clock assertion.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_report_cache_profile``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio.report import PortfolioReportQuery, PortfolioReportResponse
from backend.app.services.assets.profile.catalogue import normalize_value
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


def _geography_row(asset_id: int, weights: dict[str, str], read_on: date) -> AssetProfileUpdate:
    return AssetProfileUpdate(asset_id=asset_id, key="geography", value=json.dumps(normalize_value("geography", weights)), source="justetf", read_on=read_on)


@asynccontextmanager
async def _book(directory: Path) -> AsyncIterator[_Book]:
    """A user holding one ETF whose profile says «all USA» from D1, on a private SQLite file; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'report_cache_profile.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"d2b_{tag}", email=f"d2b_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"D2b report in steps {tag}")
            asset = Asset(display_name=f"D2b etf {tag}", currency=EUR, asset_type=AssetType.ETF)
            session.add_all([user, broker, asset])
            await session.flush()
            close = Decimal("10")
            session.add_all(
                [
                    BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=D1, quantity=Decimal("30"), amount=Decimal("-300"), currency=EUR),
                    PriceHistory(asset_id=asset.id, date=D1, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="d2b_report_in_steps_test"),
                    _geography_row(asset.id, {"USA": "1"}, D1),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, asset_id=asset.id)
        yield book
    finally:
        await engine.dispose()


async def _report(book: _Book) -> PortfolioReportResponse:
    """One request: its own session on the book's file, the summary over D0..END in EUR."""
    query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=D0, end=END), target_currency=EUR, include_summary=True)
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


def _geography(report: PortfolioReportResponse) -> set[str]:
    """The countries of the current allocation that hold value (the cash never does)."""
    assert report.summary is not None, "precondition: the report carries the summary it was asked for"
    return {item.name for item in report.summary.allocation_by_geography if item.amount != 0}


class TestTheReportCacheFollowsTheProfile:
    @pytest.mark.asyncio
    async def test_nothing_changed_is_the_cached_object(self, tmp_path):
        async with _book(tmp_path) as book:
            first = await _report(book)
            second = await _report(book)
        served_from_cache = second is first  # a bool, so a red does not print two whole reports
        assert served_from_cache, "the control: with nothing changed the second report is the one L2 stored"
        assert _geography(first) == {"USA"}, "precondition: the profile's geography is read"

    @pytest.mark.asyncio
    async def test_a_new_profile_row_is_seen_by_the_next_report(self, tmp_path):
        async with _book(tmp_path) as book:
            before = await _report(book)
            assert _geography(before) == {"USA"}, "precondition"
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                session.add(_geography_row(book.asset_id, {"JPN": "1"}, END))
                await session.commit()
            after = await _report(book)
        served_from_cache = after is before
        assert not served_from_cache, "a new profile row must not be answered by the report cached before it"
        assert _geography(after) == {"JPN"}, f"the new row is the last day's geography: {_geography(after)}"

    @pytest.mark.asyncio
    async def test_a_forgotten_profile_row_is_seen_by_the_next_report(self, tmp_path):
        async with _book(tmp_path) as book:
            before = await _report(book)
            assert _geography(before) == {"USA"}, "precondition"
            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                await session.execute(delete(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == book.asset_id))
                await session.commit()
            after = await _report(book)
        served_from_cache = after is before
        assert not served_from_cache, "a forgotten profile row must not be answered by the report cached before it"
        assert _geography(after) == {"Unknown"}, f"no geography left: {_geography(after)}"

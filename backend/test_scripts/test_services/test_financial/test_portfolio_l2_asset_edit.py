"""
The portfolio report's Layer-2 cache forgets its answer when an asset's own data is edited.

What it guards. ``PortfolioService.get_report`` (``backend/app/services/portfolio/portfolio_service.py``) keeps its answer in
``_portfolio_l2_cache`` (30 min TTL) under a key of transaction, price, FX and yield-on-cost fingerprints. The report also
shows each asset's own data — the allocation slice by asset carries its name, ``icon_url`` and ``asset_type``, a holding
its ``asset_name`` — and an edit of those changes none of the four: the developer changed an asset's icon, refreshed, and
the allocation pie kept the old one for up to 30 minutes. The key now carries an ``asset_fp`` over every asset of the
scope (id, display_name, icon_url, asset_type, currency, classification_params).

- ``test_nothing_changed_is_the_cached_object`` — the control: the same query twice returns the SAME object (``is``), so
  the cases below prove the key, not a disabled cache.
- ``test_an_asset_edit_is_seen_by_the_next_report`` — one field edited and committed (icon, name, type): the next report
  is a new object and carries the new value.

The book, on a private SQLite file under ``tmp_path`` (the app schema, an engine of its own, NullPool, disposed after):
a user, one broker at 100 %, a DEPOSIT and a BUY of one EUR ETF with a close. Isolation: PURE with respect to the lane —
no session on the lane's database, no server, no network; the L2, WAC and engine blob caches (process-global) are
emptied before and after each test. No sleep, no wall-clock assertion.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_portfolio_l2_asset_edit``.
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
from backend.app.schemas.portfolio import AssetAllocationItem, PortfolioReportQuery, PortfolioReportResponse
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1 = date(2025, 9, 1), date(2025, 9, 3)
END = date(2025, 9, 15)
ZERO = Decimal("0")
ICON_A = "/static/icons/l2-asset-edit-a.png"
ICON_B = "/static/icons/l2-asset-edit-b.png"


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
    name: str


@asynccontextmanager
async def _book(directory: Path) -> AsyncIterator[_Book]:
    """A user holding one ETF with icon A, on a private SQLite file; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'l2_asset_edit.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        name = f"L2 asset edit etf {tag}"
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"l2ae_{tag}", email=f"l2ae_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"L2 asset edit {tag}")
            asset = Asset(display_name=name, currency=EUR, asset_type=AssetType.ETF, icon_url=ICON_A)
            session.add_all([user, broker, asset])
            await session.flush()
            close = Decimal("10")
            session.add_all(
                [
                    BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=D1, quantity=Decimal("30"), amount=Decimal("-300"), currency=EUR),
                    PriceHistory(asset_id=asset.id, date=D1, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="l2_asset_edit_test"),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, asset_id=asset.id, name=name)
        yield book
    finally:
        await engine.dispose()


async def _report(book: _Book) -> PortfolioReportResponse:
    """One request: its own session on the book's file, the summary over D0..END in EUR."""
    query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=D0, end=END), target_currency=EUR, include_summary=True)
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


async def _edit_asset(book: _Book, **fields: object) -> None:
    """Write ``fields`` on the book's asset and commit, in a session of its own (no transaction, price or rate moves)."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        asset = await session.get(Asset, book.asset_id)
        assert asset is not None
        for attribute, value in fields.items():
            setattr(asset, attribute, value)
        await session.commit()


def _slice(report: PortfolioReportResponse, asset_id: int) -> AssetAllocationItem:
    assert report.summary is not None, "precondition: the report carries the summary it was asked for"
    return next(item for item in report.summary.allocation_by_asset if item.id == asset_id)


def _holding_name(report: PortfolioReportResponse, asset_id: int) -> str:
    assert report.summary is not None
    return next(holding.asset_name for holding in report.summary.holdings if holding.asset_id == asset_id)


class TestAssetEditBustsTheReportCache:
    @pytest.mark.asyncio
    async def test_nothing_changed_is_the_cached_object(self, tmp_path):
        async with _book(tmp_path) as book:
            first = await _report(book)
            second = await _report(book)
        served_from_cache = second is first  # a bool, so a red does not print two whole reports
        assert served_from_cache, "the control: with nothing changed the second report is the one L2 stored"
        assert (_slice(first, book.asset_id).icon_url, _slice(first, book.asset_id).name) == (ICON_A, book.name)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("fields", "expected"),
        [
            pytest.param({"icon_url": ICON_B}, {"icon_url": ICON_B}, id="icon_url"),
            pytest.param({"display_name": "L2 asset edit renamed"}, {"name": "L2 asset edit renamed", "holding_name": "L2 asset edit renamed"}, id="display_name"),
            pytest.param({"asset_type": AssetType.STOCK}, {"asset_type": "STOCK"}, id="asset_type"),
        ],
    )
    async def test_an_asset_edit_is_seen_by_the_next_report(self, tmp_path, fields, expected):
        async with _book(tmp_path) as book:
            before = await _report(book)
            before_slice = _slice(before, book.asset_id)
            assert (before_slice.icon_url, before_slice.name, before_slice.asset_type) == (ICON_A, book.name, "ETF"), "precondition: the first report shows the asset as seeded"
            await _edit_asset(book, **fields)
            after = await _report(book)
        served_from_cache = after is before  # a bool, so a red does not print two whole reports
        assert not served_from_cache, f"the edit of {sorted(fields)} must not be answered by the report cached before it"
        after_slice = _slice(after, book.asset_id)
        observed = {"icon_url": after_slice.icon_url, "name": after_slice.name, "asset_type": after_slice.asset_type, "holding_name": _holding_name(after, book.asset_id)}
        assert {key: observed[key] for key in expected} == expected

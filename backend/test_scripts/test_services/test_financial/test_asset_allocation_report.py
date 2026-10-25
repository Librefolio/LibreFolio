"""MF5-1b — the report's asset dimension: ``summary.allocation_by_asset`` and ``allocation_history.asset``.

The pure contract (``DailyPortfolioState.by_asset``, ``DerivedViewsBuilder.build_asset_allocation_current/history``, the
schema fields) is tested in ``test_financial_math/test_asset_allocation.py``. Here, the wiring through
``PortfolioService.get_report``: with ``include_summary`` the summary carries ``allocation_by_asset``, with
``include_allocation_history`` the history carries ``asset``; the names are ``Asset.display_name``; ``Liquidity`` has
no id; the other dimensions' items keep ``id`` None.

Consistency checks (the brief's): on every day of the history, the asset amounts plus Liquidity add up to the same total
as the ``type`` dimension's amounts; a position closed in the period appears in the history only on the days it was held,
and every one of them; the current allocation is the last day's.

The book (a private SQLite file, the app schema; one user owning 100 % of one broker; EUR, no FX rate): a deposit, X (a
stock) and Y (an ETF) bought on D1, X quoted on D2, X sold out on D3 (closed: held D1..D3-1), Y quoted on D4. The report
runs over D0..END.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), no lane database, no server, no network. The report, WAC and engine blob caches are
emptied before and after each test.

RED on HEAD 5dc68b650, by absence: ``PortfolioSummary`` has no ``allocation_by_asset`` and
``AllocationHistoryDimensions`` no ``asset`` (``AttributeError`` on the report's response).

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).
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
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1, D2, D3, D4 = date(2025, 6, 2), date(2025, 6, 3), date(2025, 6, 6), date(2025, 6, 12), date(2025, 6, 18)
END = date(2025, 6, 25)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    x_id: int
    y_id: int
    x_name: str
    y_name: str


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


def _close(asset_id: int, day: date, value: str) -> PriceHistory:
    price = Decimal(value)
    return PriceHistory(asset_id=asset_id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf5_asset_allocation_test")


@asynccontextmanager
async def _private_book(directory: Path) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf5_asset_allocation.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"mf5_aa_{tag}", email=f"mf5_aa_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"MF5 asset allocation {tag}")
            x = Asset(display_name=f"MF5 alloc X {tag}", currency=EUR, asset_type=AssetType.STOCK)
            y = Asset(display_name=f"MF5 alloc Y {tag}", currency=EUR, asset_type=AssetType.ETF)
            session.add_all([user, broker, x, y])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            session.add_all(
                [
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=Decimal("0"), amount=Decimal("5000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=x.id, type=TransactionType.BUY, date=D1, quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=y.id, type=TransactionType.BUY, date=D1, quantity=Decimal("5"), amount=Decimal("-450"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=x.id, type=TransactionType.SELL, date=D3, quantity=Decimal("-10"), amount=Decimal("1120"), currency=EUR),
                    _close(x.id, D2, "106.5"),
                    _close(y.id, D4, "93.25"),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, x_id=x.id, y_id=y.id, x_name=x.display_name, y_name=y.display_name)
        yield book
    finally:
        await engine.dispose()


async def _report(book: _Book):
    query = PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=D0, end=END),
        target_currency=EUR,
        include_summary=True,
        include_history=False,
        include_allocation_history=True,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


def _total(items) -> Decimal:
    return sum((item.amount for item in items), Decimal("0"))


class TestTheReportsAssetDimension:
    @pytest.mark.asyncio
    async def test_the_summary_carries_the_current_asset_allocation(self, tmp_path):
        async with _private_book(tmp_path) as book:
            report = await _report(book)
        items = report.summary.allocation_by_asset
        assert [(item.name, item.id) for item in items] == [("Liquidity", None), (book.y_name, book.y_id)], "X is closed by END; Liquidity first: the cash is the larger amount"
        assert _total(items) == _total(report.summary.allocation_by_type)
        y_item = next(item for item in items if item.id == book.y_id)
        assert y_item.amount == Decimal("466.25"), "5 Y at the last close 93.25"
        assert sum((item.value for item in items), Decimal("0")) == Decimal("100.00")
        assert all(item.id is None for item in report.summary.allocation_by_type), "the other dimensions carry no id"

    @pytest.mark.asyncio
    async def test_the_history_carries_the_asset_dimension_consistent_with_type(self, tmp_path):
        async with _private_book(tmp_path) as book:
            report = await _report(book)
        assets, types = report.allocation_history.asset, report.allocation_history.type
        assert assets, "precondition: an asset history"
        assert [point.date for point in assets] == [point.date for point in types]
        for asset_point, type_point in zip(assets, types, strict=True):
            assert _total(asset_point.components) == _total(type_point.components), f"{asset_point.date}: assets + Liquidity {_total(asset_point.components)}, type {_total(type_point.components)}"
            names = {component.id: component.name for component in asset_point.components}
            assert names.get(None) == "Liquidity", f"{asset_point.date}: Liquidity is always present"
            assert set(names) <= {None, book.x_id, book.y_id}
            for asset_id, name in ((book.x_id, book.x_name), (book.y_id, book.y_name)):
                if asset_id in names:
                    assert names[asset_id] == name, "the name is Asset.display_name"
            amounts = [component.amount for component in asset_point.components]
            assert amounts == sorted(amounts, reverse=True), f"{asset_point.date}: not by amount descending"
        for type_point in types:
            assert all(component.id is None for component in type_point.components)

    @pytest.mark.asyncio
    async def test_a_closed_position_appears_only_on_the_days_it_was_held(self, tmp_path):
        async with _private_book(tmp_path) as book:
            report = await _report(book)
        assets = report.allocation_history.asset
        with_x = [point.date for point in assets if any(component.id == book.x_id for component in point.components)]
        with_y = [point.date for point in assets if any(component.id == book.y_id for component in point.components)]
        held_x = [D1 + timedelta(days=offset) for offset in range((D3 - D1).days)]
        assert with_x == held_x, f"X appears on {with_x[:1]}..{with_x[-1:]}, held {held_x[0]}..{held_x[-1]}"
        assert with_y == [point.date for point in assets if point.date >= D1]

    @pytest.mark.asyncio
    async def test_the_current_allocation_is_the_last_days(self, tmp_path):
        async with _private_book(tmp_path) as book:
            report = await _report(book)
        last = report.allocation_history.asset[-1]
        assert last.date == END
        current = [(item.name, item.id, item.value, item.amount) for item in report.summary.allocation_by_asset]
        assert current == [(component.name, component.id, component.value, component.amount) for component in last.components]

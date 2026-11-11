"""
F-10 (ondata 8, lot B8) — the slices of the allocation by asset carry what the pie needs to draw their icon.

The Dashboard's pie by asset draws each slice's icon: the asset's own (``icon_url``), else its type's (``asset_type``); the Liquidity
slice has neither (it wears its own icon). The backend only reports the two fields next to the slice's ``id``: no figure changes.

What is pinned, through the real service on a private database:
- an asset with an icon: its ``icon_url`` and its type;
- an asset without: ``icon_url`` None (an empty string too), its type still there;
- the Liquidity slice: both None; the other dimensions do not carry the keys at all;
- the fields are in the JSON the frontend reads.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
from backend.app.services.portfolio import portfolio_service as portfolio_service_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1 = date(2025, 9, 1), date(2025, 9, 3)
END = date(2025, 9, 15)
ZERO = Decimal("0")
ICON = "/static/icons/test-etf.png"


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    for cache in (portfolio_service_module._portfolio_l2_cache, portfolio_service_module._wac_cache, portfolio_engine_module._portfolio_blob_cache):
        cache.clear()
    yield
    for cache in (portfolio_service_module._portfolio_l2_cache, portfolio_service_module._wac_cache, portfolio_engine_module._portfolio_blob_cache):
        cache.clear()


def _close(asset_id: int, day: date, value: str) -> PriceHistory:
    price = Decimal(value)
    return PriceHistory(asset_id=asset_id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="b8_allocation_icons_test")


@asynccontextmanager
async def _book(directory: Path) -> AsyncIterator[tuple[AsyncEngine, int, dict[str, int]]]:
    """A user holding three assets: an ETF with its own icon, a stock with none, a bond whose icon is an empty string."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'b8_allocation_icons.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"b8_{tag}", email=f"b8_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"B8 icons {tag}")
            with_icon = Asset(display_name=f"B8 etf {tag}", currency=EUR, asset_type=AssetType.ETF, icon_url=ICON)
            without = Asset(display_name=f"B8 stock {tag}", currency=EUR, asset_type=AssetType.STOCK)
            blank = Asset(display_name=f"B8 bond {tag}", currency=EUR, asset_type=AssetType.BOND, icon_url="")
            session.add_all([user, broker, with_icon, without, blank])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            rows = [Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("5000"), currency=EUR)]
            for asset, units in ((with_icon, "30"), (without, "20"), (blank, "10")):
                rows.append(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=D1, quantity=Decimal(units), amount=-Decimal(units) * 10, currency=EUR))
                rows.append(_close(asset.id, D1, "10"))
            session.add_all(rows)
            await session.commit()
            ids = {"with_icon": with_icon.id, "without": without.id, "blank": blank.id}
            user_id = user.id
        yield engine, user_id, ids
    finally:
        await engine.dispose()


async def _summary(engine: AsyncEngine, user_id: int):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_summary(user_id, target_currency_override=EUR, date_from=D0, date_to=END)


class TestAssetSliceIcons:
    @pytest.mark.asyncio
    async def test_each_slice_carries_its_icon_and_its_type(self, tmp_path):
        async with _book(tmp_path) as (engine, user_id, ids):
            summary = await _summary(engine, user_id)
        by_id = {item.id: item for item in summary.allocation_by_asset if item.id is not None}
        assert set(by_id) == set(ids.values()), f"precondition: one slice per held asset, got {sorted(by_id)}"
        assert (by_id[ids["with_icon"]].icon_url, by_id[ids["with_icon"]].asset_type) == (ICON, "ETF")
        assert (by_id[ids["without"]].icon_url, by_id[ids["without"]].asset_type) == (None, "STOCK")
        assert (by_id[ids["blank"]].icon_url, by_id[ids["blank"]].asset_type) == (None, "BOND"), "an empty icon is no icon: the type's is drawn"

    @pytest.mark.asyncio
    async def test_the_liquidity_slice_carries_neither(self, tmp_path):
        async with _book(tmp_path) as (engine, user_id, _ids):
            summary = await _summary(engine, user_id)
        cash = [item for item in summary.allocation_by_asset if item.id is None]
        assert [item.name for item in cash] == ["Liquidity"]
        assert (cash[0].icon_url, cash[0].asset_type) == (None, None)

    @pytest.mark.asyncio
    async def test_the_other_dimensions_are_untouched(self, tmp_path):
        """Type, sector and geography keep the keys they had: the two fields belong to the asset dimension alone."""
        async with _book(tmp_path) as (engine, user_id, _ids):
            summary = await _summary(engine, user_id)
        dumped = summary.model_dump(mode="json")
        for dimension in ("allocation_by_type", "allocation_by_sector", "allocation_by_geography"):
            for item in dumped[dimension]:
                assert "icon_url" not in item and "asset_type" not in item, f"{dimension}: {item}"

    @pytest.mark.asyncio
    async def test_the_fields_are_in_the_json_the_frontend_reads(self, tmp_path):
        async with _book(tmp_path) as (engine, user_id, ids):
            summary = await _summary(engine, user_id)
        dumped = summary.model_dump(mode="json")["allocation_by_asset"]
        row = next(item for item in dumped if item["id"] == ids["with_icon"])
        assert row["icon_url"] == ICON and row["asset_type"] == "ETF"

    @pytest.mark.asyncio
    async def test_no_figure_moved(self, tmp_path):
        """The slices' names, values and amounts are what the engine gave: the two fields are the only addition."""
        async with _book(tmp_path) as (engine, user_id, _ids):
            summary = await _summary(engine, user_id)
        assert sum((item.amount for item in summary.allocation_by_asset), ZERO) == summary.net_worth.amount

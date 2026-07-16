"""Integration tests for LotsAnalysisService."""

import sys
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.app.utils.datetime_utils import utcnow


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    stamp = str(utcnow().timestamp()).replace(".", "")
    user = User(
        username=f"lots_{stamp}",
        email=f"lots_{stamp}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def asset(session) -> Asset:
    stamp = str(utcnow().timestamp()).replace(".", "")
    row = Asset(
        display_name=f"LotsAsset_{stamp}",
        identifier_ticker=f"LOTS{stamp[-4:]}",
        currency="EUR",
        asset_type=AssetType.STOCK,
    )
    session.add(row)
    await session.flush()
    return row


@pytest_asyncio.fixture
async def broker(session, test_user) -> Broker:
    row = Broker(name=f"LotsBroker_{utcnow().timestamp()}")
    session.add(row)
    await session.flush()
    session.add(
        BrokerUserAccess(
            broker_id=row.id,
            user_id=test_user.id,
            role="OWNER",
            share_percentage=Decimal("1"),
        )
    )
    await session.flush()
    return row


@pytest.mark.asyncio
async def test_buy_sell_summary_converts_to_target_currency(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.BUY,
                date=date(2025, 1, 10),
                quantity=Decimal("10"),
                amount=Decimal("-1000"),
                currency="EUR",
            ),
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.SELL,
                date=date(2025, 2, 1),
                quantity=Decimal("-4"),
                amount=Decimal("520"),
                currency="EUR",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("100"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 2, 1),
                close=Decimal("130"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            FxRate(date=date(2025, 1, 10), base="EUR", quote="USD", rate=Decimal("1.2"), source="TEST"),
            FxRate(date=date(2025, 2, 1), base="EUR", quote="USD", rate=Decimal("1.3"), source="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 2, 1),
        target_currency="USD",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.calculation_status == "COMPLETE"
    assert result.data_quality is not None
    assert result.data_quality.issues == []
    assert result.lots is not None
    assert len(result.lots) == 1

    lot = result.lots[0]
    assert lot.opening_unit_price == Decimal("120")
    assert lot.original_quantity == Decimal("10")
    assert lot.open_quantity == Decimal("6")
    assert lot.original_cost == Decimal("1200")
    assert lot.realized_quantity == Decimal("4")
    assert lot.realized_pnl == Decimal("156")
    assert lot.cumulative_proceeds == Decimal("676")
    assert lot.open_value == Decimal("1014")
    assert lot.total_value == Decimal("1690")
    assert lot.pnl == Decimal("490")
    assert lot.states == ["LONG", "PARTIALLY_CLOSED"]


@pytest.mark.asyncio
async def test_split_adjustment_uses_asset_event_ratio(session, test_user, asset, broker):
    split_event = AssetEvent(
        asset_id=asset.id,
        date=date(2025, 2, 1),
        type=AssetEventType.SPLIT,
        value=Decimal("2"),
        currency="EUR",
    )
    session.add(split_event)
    await session.flush()

    session.add_all(
        [
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.BUY,
                date=date(2025, 1, 10),
                quantity=Decimal("10"),
                amount=Decimal("-1000"),
                currency="EUR",
            ),
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date(2025, 2, 1),
                quantity=Decimal("10"),
                amount=Decimal("0"),
                currency="EUR",
                asset_event_id=split_event.id,
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 2, 10),
                close=Decimal("60"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 2, 10),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "EVENT_HISTORY"],
    )

    assert result.lots is not None
    assert len(result.lots) == 1
    lot = result.lots[0]
    assert lot.original_quantity == Decimal("20")
    assert lot.open_quantity == Decimal("20")
    assert lot.opening_unit_price == Decimal("50")
    assert lot.original_cost == Decimal("1000")
    assert result.lot_events is not None
    split_rows = [row for row in result.lot_events if row.kind == "SPLIT"]
    assert len(split_rows) == 1
    assert split_rows[0].ratio == Decimal("2")


@pytest.mark.asyncio
async def test_service_uses_constant_query_count(session, test_user, asset, broker, engine):
    for idx in range(12):
        session.add(
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.BUY if idx % 2 == 0 else TransactionType.SELL,
                date=date(2025, 1, 1 + idx),
                quantity=Decimal("5") if idx % 2 == 0 else Decimal("-1"),
                amount=Decimal("-500") if idx % 2 == 0 else Decimal("120"),
                currency="EUR",
            )
        )
    session.add(PriceHistory(asset_id=asset.id, date=date(2025, 1, 12), close=Decimal("120"), currency="EUR", source_plugin_key="TEST"))
    await session.flush()

    statements: list[str] = []

    def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):
        sql = statement.lstrip().upper()
        if sql.startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        result = await get_lots_analysis(
            session=session,
            user_id=test_user.id,
            asset_id=asset.id,
            broker_ids=[broker.id],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 12),
            target_currency="EUR",
            selected_lot_ids=None,
            requested_analyses=["BROKER_WAC_HISTORY", "CUMULATIVE_WAC_HISTORY"],
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    assert len(statements) <= 6
    assert result.broker_wac_history is not None
    assert result.cumulative_wac_history is not None
    assert result.broker_wac_history[-1].wac == Decimal("100")
    assert result.cumulative_wac_history[-1].wac == Decimal("100")

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


def _points_by_date(points):
    return {point.date: point for point in points}


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


@pytest.mark.asyncio
async def test_buy_return_history_populates_total_and_open_return(session, test_user, asset, broker):
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
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("100"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("110"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("90"),
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
        date_to=date(2025, 1, 12),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "RETURN_HISTORY"],
    )

    assert result.lots is not None
    assert result.return_history is not None
    assert len(result.lots) == 1
    points = _points_by_date(result.return_history)
    assert set(points) == {date(2025, 1, 10), date(2025, 1, 11), date(2025, 1, 12)}

    original_cost = Decimal("1000")
    opening_unit_price = Decimal("100")
    expected_market_prices = {
        date(2025, 1, 10): Decimal("100"),
        date(2025, 1, 11): Decimal("110"),
        date(2025, 1, 12): Decimal("90"),
    }
    for point_date, market_price in expected_market_prices.items():
        expected_total_return = ((Decimal("10") * market_price) / original_cost) - Decimal("1")
        expected_open_return = (market_price / opening_unit_price) - Decimal("1")
        point = points[point_date]
        assert point.total_return == expected_total_return
        assert point.relative_return == expected_open_return
        assert point.reference_price_source == "exact"

    lot = result.lots[0]
    assert lot.reference_unit_price == Decimal("100")
    assert lot.reference_price_source == "exact"
    assert lot.relative_return == Decimal("-0.1")


@pytest.mark.asyncio
async def test_adjustment_return_history_keeps_reference_and_zero_cost_guard(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date(2025, 1, 10),
                quantity=Decimal("5"),
                amount=Decimal("0"),
                currency="EUR",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("80"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("100"),
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
        date_to=date(2025, 1, 11),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "RETURN_HISTORY"],
    )

    assert result.lots is not None
    assert result.return_history is not None
    lot = result.lots[0]
    assert lot.original_cost == Decimal("0")
    assert lot.reference_unit_price == Decimal("80")
    assert lot.reference_price_source == "exact"
    assert lot.relative_return == Decimal("0.25")

    points = _points_by_date(result.return_history)
    assert set(points) == {date(2025, 1, 10), date(2025, 1, 11)}
    assert all(point.total_return is None for point in result.return_history)
    assert points[date(2025, 1, 10)].relative_return == Decimal("0")
    assert points[date(2025, 1, 11)].relative_return == Decimal("0.25")
    assert all(point.reference_price_source == "exact" for point in result.return_history)


@pytest.mark.asyncio
async def test_short_lot_return_history_computes_total_return(session, test_user, asset):
    short_broker = Broker(name=f"LotsShortBroker_{utcnow().timestamp()}", allow_asset_shorting=True)
    session.add(short_broker)
    await session.flush()
    session.add(
        BrokerUserAccess(
            broker_id=short_broker.id,
            user_id=test_user.id,
            role="OWNER",
            share_percentage=Decimal("1"),
        )
    )
    session.add_all(
        [
            Transaction(
                broker_id=short_broker.id,
                asset_id=asset.id,
                type=TransactionType.SELL,
                date=date(2025, 1, 10),
                quantity=Decimal("-5"),
                amount=Decimal("600"),
                currency="EUR",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("120"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("110"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("100"),
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
        broker_ids=[short_broker.id],
        date_from=None,
        date_to=date(2025, 1, 12),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["RETURN_HISTORY"],
    )

    assert result.return_history is not None
    assert len(result.return_history) == 3
    assert all(point.total_return is not None for point in result.return_history)
    assert result.return_history[0].total_return == Decimal("-1")


@pytest.mark.asyncio
async def test_performance_history_buy_only_tracks_roi_and_twrr(session, test_user, asset, broker):
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
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("100"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("110"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("120"),
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
        date_to=date(2025, 1, 12),
        target_currency="EUR",
        selected_lot_ids=[],
        requested_analyses=["PERFORMANCE_HISTORY"],
    )

    assert result.performance_history is not None
    points = _points_by_date(result.performance_history)
    assert [point.date for point in result.performance_history] == [date(2025, 1, 10), date(2025, 1, 11), date(2025, 1, 12)]
    assert points[date(2025, 1, 10)].roi == Decimal("0")
    assert points[date(2025, 1, 10)].twrr is None
    assert points[date(2025, 1, 11)].roi == Decimal("0.1")
    assert points[date(2025, 1, 11)].twrr == Decimal("0.1")
    assert points[date(2025, 1, 12)].roi == Decimal("0.2")
    assert points[date(2025, 1, 12)].twrr == Decimal("0.2")


@pytest.mark.asyncio
async def test_performance_history_sell_partial_registers_sale_cash_flow(session, test_user, asset, broker):
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
                date=date(2025, 1, 12),
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
                date=date(2025, 1, 11),
                close=Decimal("120"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("130"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 13),
                close=Decimal("130"),
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
        date_to=date(2025, 1, 13),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["PERFORMANCE_HISTORY"],
    )

    assert result.performance_history is not None
    points = _points_by_date(result.performance_history)
    assert points[date(2025, 1, 12)].twrr == Decimal("0.3")
    assert points[date(2025, 1, 12)].roi == Decimal("0.625")
    assert points[date(2025, 1, 13)].twrr == Decimal("0.3")
    assert points[date(2025, 1, 13)].roi == Decimal("0.625")


@pytest.mark.asyncio
async def test_performance_history_transfer_internal_vs_external_scope(session, test_user, asset, broker):
    broker_b = Broker(name=f"LotsBrokerB_{utcnow().timestamp()}")
    session.add(broker_b)
    await session.flush()
    session.add(
        BrokerUserAccess(
            broker_id=broker_b.id,
            user_id=test_user.id,
            role="OWNER",
            share_percentage=Decimal("1"),
        )
    )
    await session.flush()

    buy = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.BUY,
        date=date(2025, 1, 10),
        quantity=Decimal("10"),
        amount=Decimal("-1000"),
        currency="EUR",
    )
    transfer_out = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.TRANSFER,
        date=date(2025, 1, 12),
        quantity=Decimal("-10"),
        amount=Decimal("0"),
        currency="EUR",
    )
    transfer_in = Transaction(
        broker_id=broker_b.id,
        asset_id=asset.id,
        type=TransactionType.TRANSFER,
        date=date(2025, 1, 13),
        quantity=Decimal("10"),
        amount=Decimal("0"),
        currency="EUR",
    )
    session.add_all(
        [
            buy,
            transfer_out,
            transfer_in,
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
                close=Decimal("100"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("120"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("130"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 13),
                close=Decimal("130"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 14),
                close=Decimal("140"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
        ]
    )
    await session.flush()
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    await session.flush()

    combined_scope = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id, broker_b.id],
        date_from=None,
        date_to=date(2025, 1, 14),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["PERFORMANCE_HISTORY"],
    )
    source_scope_only = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 14),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["PERFORMANCE_HISTORY"],
    )

    assert combined_scope.performance_history is not None
    assert source_scope_only.performance_history is not None

    combined_points = _points_by_date(combined_scope.performance_history)
    source_points = _points_by_date(source_scope_only.performance_history)

    assert combined_points[date(2025, 1, 12)].twrr == Decimal("0.3")
    assert combined_points[date(2025, 1, 13)].twrr == Decimal("0.3")
    assert combined_points[date(2025, 1, 14)].roi == Decimal("0.4")
    assert combined_points[date(2025, 1, 14)].twrr == Decimal("0.4")

    assert source_points[date(2025, 1, 12)].twrr == Decimal("0.3")
    assert source_points[date(2025, 1, 12)].roi == Decimal("0")
    assert source_points[date(2025, 1, 13)].roi == Decimal("0")
    assert source_points[date(2025, 1, 14)].twrr == Decimal("0.3")


@pytest.mark.asyncio
async def test_performance_history_missing_price_yields_none_without_exception(session, test_user, asset, broker):
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
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 12),
                close=Decimal("120"),
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
        date_to=date(2025, 1, 12),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["PERFORMANCE_HISTORY"],
    )

    assert result.performance_history is not None
    points = _points_by_date(result.performance_history)
    assert points[date(2025, 1, 10)].roi is None
    assert points[date(2025, 1, 10)].twrr is None
    assert points[date(2025, 1, 11)].roi is None
    assert points[date(2025, 1, 11)].twrr is None
    assert points[date(2025, 1, 12)].roi == Decimal("0.2")
    assert points[date(2025, 1, 12)].twrr is None

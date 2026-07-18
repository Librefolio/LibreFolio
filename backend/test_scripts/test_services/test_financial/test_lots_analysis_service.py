"""Integration tests for LotsAnalysisService."""

import sys
from datetime import date, timedelta
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
from backend.app.schemas.portfolio import IssueCode
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.app.utils.datetime_utils import utcnow


def _points_by_date(points):
    return {point.date: point for point in points}


def _points_by_lot_date(points):
    return {(point.lot_id, point.date): point for point in points}


def _assert_closed_lot_history_flat(result, lot_id: int, close_date: date, date_to: date) -> None:
    assert result.value_history is not None
    assert result.return_history is not None
    value_points = _points_by_lot_date(result.value_history)
    return_points = _points_by_lot_date(result.return_history)

    close_value = value_points[(lot_id, close_date)]
    close_return = return_points[(lot_id, close_date)]
    assert close_value.open_value == Decimal("0")

    current_date = close_date + timedelta(days=1)
    while current_date <= date_to:
        value_point = value_points[(lot_id, current_date)]
        return_point = return_points[(lot_id, current_date)]

        assert value_point.open_value == Decimal("0")
        assert value_point.proceeds == close_value.proceeds
        assert value_point.income == close_value.income
        assert value_point.total_value == close_value.total_value
        assert value_point.pnl == close_value.pnl
        assert return_point.income == close_return.income
        assert return_point.total_return == close_return.total_return

        current_date += timedelta(days=1)


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


@pytest.mark.asyncio
async def test_dividend_allocated_pro_rata_to_open_long_lots(session, test_user, asset, broker):
    """DIVIDEND is split across open LONG lots by open quantity; conservation holds; metrics reflect income."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 15), quantity=Decimal("30"), amount=Decimal("-3000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 20), quantity=Decimal("-4"), amount=Decimal("520"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), quantity=Decimal("0"), amount=Decimal("360"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 2, 1), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
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
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None
    by_qty = {lot.original_quantity: lot for lot in result.lots}
    lot_a = by_qty[Decimal("10")]  # partially sold (open 6)
    lot_b = by_qty[Decimal("30")]  # fully open

    # Conservation: total allocated income equals the dividend amount.
    assert lot_a.asset_income + lot_b.asset_income == Decimal("360")
    # Pro-rata by open quantity at dividend date: A open 6, B open 30 -> 6/36 and 30/36.
    assert lot_a.asset_income == Decimal("60")
    assert lot_b.asset_income == Decimal("300")

    # Lot A (partial): market_pnl excludes income, total_pnl includes it.
    assert lot_a.realized_pnl == Decimal("120")
    assert lot_a.market_pnl == Decimal("0")
    assert lot_a.total_pnl == Decimal("180")
    assert lot_a.cash_yield == Decimal("60") / Decimal("1000")
    assert lot_a.total_return == Decimal("180") / Decimal("1000")
    assert lot_a.value_source == "MARKET_PRICE"

    # Lot B (fully open, no market move): total_pnl == income.
    assert lot_b.market_pnl == Decimal("0")
    assert lot_b.total_pnl == Decimal("300")
    assert lot_b.total_return == Decimal("300") / Decimal("3000")

    # Value/return history carry cumulative income for lot B (0 before, 300 from dividend date).
    b_value = _points_by_date([p for p in result.value_history if p.lot_id == lot_b.lot_id])
    assert b_value[date(2025, 1, 31)].income == Decimal("0")
    assert b_value[date(2025, 2, 1)].income == Decimal("300")
    b_return = _points_by_date([p for p in result.return_history if p.lot_id == lot_b.lot_id])
    assert b_return[date(2025, 2, 1)].total_return == Decimal("300") / Decimal("3000")


@pytest.mark.asyncio
async def test_income_events_payload_exposes_allocated_income_markers(session, test_user, asset, broker):
    """INCOME_EVENTS returns one marker per allocated income tx with total amount + involved lot ids (plan v3 §11)."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 15), quantity=Decimal("30"), amount=Decimal("-3000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), quantity=Decimal("0"), amount=Decimal("360"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.INTEREST, date=date(2025, 2, 10), quantity=Decimal("0"), amount=Decimal("40"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 2, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
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
        requested_analyses=["LOT_SUMMARY", "INCOME_EVENTS"],
    )

    assert result.income_events is not None
    assert len(result.income_events) == 2
    by_date = {event.date: event for event in result.income_events}

    dividend = by_date[date(2025, 2, 1)]
    assert dividend.type == "DIVIDEND"
    assert dividend.amount == Decimal("360")
    assert dividend.broker_id == broker.id
    # Both lots open at the dividend date -> both allocated.
    lot_ids = {lot.lot_id for lot in result.lots}
    assert set(dividend.lot_ids) == lot_ids

    interest = by_date[date(2025, 2, 10)]
    assert interest.type == "INTEREST"
    assert interest.amount == Decimal("40")


@pytest.mark.asyncio
async def test_dividend_in_foreign_currency_converted_to_target(session, test_user, asset, broker):
    """Income is FX-converted to target currency at the transaction date before allocation."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), quantity=Decimal("0"), amount=Decimal("120"), currency="USD"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 2, 1), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            FxRate(date=date(2025, 2, 1), base="EUR", quote="USD", rate=Decimal("1.25"), source="TEST"),
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
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    assert result.lots[0].asset_income == Decimal("96")  # 120 USD / 1.25


@pytest.mark.asyncio
async def test_estimated_at_cost_when_no_price_history(session, test_user, asset, broker):
    """No price history -> open value estimated at cost, market_pnl 0, income still accrues, DQ issue raised."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("1000"), amount=Decimal("-15000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.INTEREST, date=date(2025, 3, 1), quantity=Decimal("0"), amount=Decimal("1250"), currency="EUR"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 3, 1),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    assert lot.value_source == "ESTIMATED_AT_COST"
    assert lot.open_value == Decimal("15000")
    assert lot.market_pnl == Decimal("0")
    assert lot.asset_income == Decimal("1250")
    assert lot.total_pnl == Decimal("1250")
    assert lot.total_return == Decimal("1250") / Decimal("15000")

    codes = {issue.code for issue in result.data_quality.issues}
    assert IssueCode.CURRENT_PRICE_ASSUMED_AT_COST in codes

    # History is now populated (previously skipped when market_price was None).
    assert result.value_history
    last_value = _points_by_date(result.value_history)[date(2025, 3, 1)]
    assert last_value.open_value == Decimal("15000")
    assert last_value.income == Decimal("1250")
    last_return = _points_by_date(result.return_history)[date(2025, 3, 1)]
    assert abs(last_return.total_return - Decimal("1250") / Decimal("15000")) < Decimal("1e-9")


@pytest.mark.asyncio
async def test_closed_lot_history_continues_flat_without_close_market_price(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 12), quantity=Decimal("-10"), amount=Decimal("1300"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 15), close=Decimal("125"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 16),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY", "PRICE_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    _assert_closed_lot_history_flat(result, lot.lot_id, date(2025, 1, 12), date(2025, 1, 16))

    value_points = _points_by_lot_date(result.value_history)
    return_points = _points_by_lot_date(result.return_history)
    assert value_points[(lot.lot_id, date(2025, 1, 12))].proceeds == Decimal("1300")
    assert value_points[(lot.lot_id, date(2025, 1, 12))].pnl == Decimal("300")
    assert return_points[(lot.lot_id, date(2025, 1, 12))].total_return == Decimal("0.3")
    assert return_points[(lot.lot_id, date(2025, 1, 13))].relative_return is None
    assert return_points[(lot.lot_id, date(2025, 1, 14))].relative_return is None
    assert result.price_history == []


@pytest.mark.asyncio
async def test_partially_then_fully_closed_lot_history_continues_flat(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 12), quantity=Decimal("-4"), amount=Decimal("520"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 14), quantity=Decimal("-6"), amount=Decimal("780"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 14), close=Decimal("130"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 16),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    _assert_closed_lot_history_flat(result, lot.lot_id, date(2025, 1, 14), date(2025, 1, 16))

    close_value = _points_by_lot_date(result.value_history)[(lot.lot_id, date(2025, 1, 14))]
    assert close_value.proceeds == Decimal("1300")
    assert close_value.pnl == Decimal("300")


@pytest.mark.asyncio
async def test_closed_lot_history_keeps_income_crystallized_after_close(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 1, 12), quantity=Decimal("0"), amount=Decimal("50"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 14), quantity=Decimal("-10"), amount=Decimal("1200"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 14), close=Decimal("120"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 16),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    _assert_closed_lot_history_flat(result, lot.lot_id, date(2025, 1, 14), date(2025, 1, 16))

    close_value = _points_by_lot_date(result.value_history)[(lot.lot_id, date(2025, 1, 14))]
    close_return = _points_by_lot_date(result.return_history)[(lot.lot_id, date(2025, 1, 14))]
    assert close_value.income == Decimal("50")
    assert close_value.total_value == Decimal("1200")
    assert close_value.pnl == Decimal("200")
    assert close_return.income == Decimal("50")
    assert close_return.total_return == Decimal("0.25")


@pytest.mark.asyncio
async def test_closed_and_open_lots_keep_independent_history_continuity(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 11), quantity=Decimal("5"), amount=Decimal("-500"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 12), quantity=Decimal("-10"), amount=Decimal("1300"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 12), close=Decimal("130"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 14), close=Decimal("140"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 14),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 2
    closed_lot = next(row for row in result.lots if row.opening_date == date(2025, 1, 10))
    open_lot = next(row for row in result.lots if row.opening_date == date(2025, 1, 11))
    _assert_closed_lot_history_flat(result, closed_lot.lot_id, date(2025, 1, 12), date(2025, 1, 14))

    open_value = _points_by_lot_date(result.value_history)[(open_lot.lot_id, date(2025, 1, 14))]
    open_return = _points_by_lot_date(result.return_history)[(open_lot.lot_id, date(2025, 1, 14))]
    assert open_value.open_value == Decimal("700")
    assert open_value.total_value == Decimal("700")
    assert open_return.total_return == Decimal("0.4")


@pytest.mark.asyncio
async def test_multiple_fully_closed_lots_each_continue_flat_to_date_to(session, test_user, asset, broker):
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 11), quantity=Decimal("20"), amount=Decimal("-2000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 12), quantity=Decimal("-10"), amount=Decimal("1100"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 13), quantity=Decimal("-20"), amount=Decimal("2500"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 13), close=Decimal("125"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 15),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 2
    first_lot = next(row for row in result.lots if row.opening_date == date(2025, 1, 10))
    second_lot = next(row for row in result.lots if row.opening_date == date(2025, 1, 11))

    _assert_closed_lot_history_flat(result, first_lot.lot_id, date(2025, 1, 12), date(2025, 1, 15))
    _assert_closed_lot_history_flat(result, second_lot.lot_id, date(2025, 1, 13), date(2025, 1, 15))

    value_points = _points_by_lot_date(result.value_history)
    assert value_points[(first_lot.lot_id, date(2025, 1, 12))].pnl == Decimal("100")
    assert value_points[(second_lot.lot_id, date(2025, 1, 13))].pnl == Decimal("500")


@pytest.mark.asyncio
async def test_income_after_lot_closed_is_not_allocated(session, test_user, asset, broker):
    """A dividend paid after the only lot is fully closed is not attributed to it (broker-level effect)."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 1, 20), quantity=Decimal("-10"), amount=Decimal("1300"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), quantity=Decimal("0"), amount=Decimal("50"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 2, 1), close=Decimal("130"), currency="EUR", source_plugin_key="TEST"),
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
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    assert lot.asset_income == Decimal("0")
    assert lot.total_pnl == lot.pnl  # income does not distort a fully-closed lot


@pytest.mark.asyncio
async def test_same_asset_open_value_scales_with_quantity_only(session, test_user, asset, broker):
    """Reproduces the user report: 4 open lots of the same asset show DIFFERENT current values.

    Expected (not a bug): current value = open_quantity * latest_market_price, and
    latest_market_price is a single scalar shared by every lot of the asset. So the per-unit
    current value is uniform across lots; a lot with a larger open quantity simply has a larger
    current value. Here 3 lots hold 36 units (-> 304.20) and 1 lot holds 40 units (-> 338.00),
    latest price 8.45 EUR, mirroring the real portfolio numbers.
    """
    latest_price = Decimal("8.45")
    quantities = [Decimal("36"), Decimal("36"), Decimal("40"), Decimal("36")]
    buy_dates = [date(2026, 1, 2), date(2026, 2, 2), date(2026, 3, 2), date(2026, 7, 1)]
    unit_costs = [Decimal("7.67"), Decimal("7.89"), Decimal("7.79"), Decimal("8.48")]

    rows: list = []
    for qty, buy_date, unit_cost in zip(quantities, buy_dates, unit_costs, strict=True):
        rows.append(
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.BUY,
                date=buy_date,
                quantity=qty,
                amount=-(qty * unit_cost),
                currency="EUR",
            )
        )
        rows.append(
            PriceHistory(asset_id=asset.id, date=buy_date, close=unit_cost, currency="EUR", source_plugin_key="TEST")
        )
    # Single latest market price shared by all lots.
    rows.append(PriceHistory(asset_id=asset.id, date=date(2026, 7, 2), close=latest_price, currency="EUR", source_plugin_key="TEST"))
    session.add_all(rows)
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2026, 7, 2),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.lots is not None and len(result.lots) == 4
    lots = sorted(result.lots, key=lambda lot_row: lot_row.opening_date)

    # 1) Every lot is priced at the same single market price.
    for lot in lots:
        assert lot.value_source == "MARKET_PRICE"
        assert lot.open_value == lot.open_quantity * latest_price
        # Per-unit current value is uniform across all lots of the asset.
        assert lot.open_value / lot.open_quantity == latest_price

    # 2) The differing current values are explained ONLY by differing quantities.
    by_qty = {lot.open_quantity: lot.open_value for lot in lots}
    assert by_qty[Decimal("36")] == Decimal("304.20")
    assert by_qty[Decimal("40")] == Decimal("338.00")
    assert by_qty[Decimal("40")] - by_qty[Decimal("36")] == (Decimal("40") - Decimal("36")) * latest_price

    # 3) Totals are internally consistent (sum of lots == total quantity * price).
    total_quantity = sum((lot.open_quantity for lot in lots), Decimal("0"))
    total_open_value = sum((lot.open_value for lot in lots), Decimal("0"))
    assert total_quantity == Decimal("148")
    assert total_open_value == Decimal("1250.60")
    assert total_open_value == total_quantity * latest_price

"""Integration tests for LotsAnalysisService."""

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, FxConversionRoute, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import EconomicAllocationGroupSchema, EconomicLotAllocationSchema, IssueCode, LotTimelineEventSchema
from backend.app.services.financial_math.returns import cumulative_to_annualized
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.app.services.portfolio_service import PortfolioService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._lots_steps import daily_points
from backend.test_scripts.test_services._range_bounds import lift_range_bound


async def _own_fx_rate(session, *, on: date, base: str, quote: str, rate: Decimal) -> None:
    """Insert an FX rate this test owns, without depending on the table's prior state.

    ``fx_rates`` is global -- no ``user_id`` -- and unique on ``(date, base, quote)``.
    Two things follow, and both have bitten this file:

    * a plain ``session.add`` fails with ``UNIQUE constraint failed`` whenever a
      neighbour (the mock ECB seed, an FX sync test, another unit) already
      committed that exact key. The test then reds for a reason it did not cause;
    * asserting on a rate this test did not write is asserting on someone else's
      data.

    Deleting the key first makes the test independent of what came before. The
    delete runs inside the same transaction as the insert, and the ``session``
    fixture rolls that transaction back, so a neighbour's row is restored intact
    -- nothing is destroyed, the test just guarantees its own starting point.
    """
    await session.execute(delete(FxRate).where(FxRate.date == on, FxRate.base == base, FxRate.quote == quote))
    session.add(FxRate(date=on, base=base, quote=quote, rate=rate, source="TEST"))
    await session.flush()


def _points_by_date(points):
    """A history by day (J5-5: its steps repeated over their days — these tests are about the figures of a day, not about
    how the days are grouped)."""
    return {point.date: point for point in daily_points(points)}


def _points_by_lot_date(points):
    return {(point.lot_id, point.date): point for point in daily_points(points)}


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


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the opening-event scenarios live in 2048, after tomorrow, so the range bound is lifted for the whole
    module, before any fixture builds data (see ``lift_range_bound``)."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        lift_range_bound(monkeypatch)
        yield


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
        ]
    )
    await session.flush()
    # This test owns EUR/USD on 10 Jan and 1 Feb 2025. See _own_fx_rate: the pair
    # is global, so the rows are claimed rather than assumed absent.
    await _own_fx_rate(session, on=date(2025, 1, 10), base="EUR", quote="USD", rate=Decimal("1.2"))
    await _own_fx_rate(session, on=date(2025, 2, 1), base="EUR", quote="USD", rate=Decimal("1.3"))

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
    # CP-7a (developer's decision 26): each leg at its own date, 4 × 130 EUR at 1.3 − 4 × 100 EUR at 1.2 = 676 − 480.
    # Before CP-7a: 156 = (520 − 400) EUR × 1.3, the cost converted at the sale's rate.
    assert lot.realized_pnl == Decimal("196")
    assert lot.cumulative_proceeds == Decimal("676")
    assert lot.open_value == Decimal("1014")
    assert lot.total_value == Decimal("1690")
    assert lot.pnl == Decimal("490")
    assert lot.states == ["LONG", "PARTIALLY_CLOSED"]
    assert lot.closing_date is None


@pytest.mark.asyncio
async def test_closing_date_set_only_for_fully_closed_lot(session, test_user, asset, broker):
    """closing_date must be the max LotClosure.close_date when open_quantity == 0, else None."""
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
                quantity=Decimal("-6"),
                amount=Decimal("780"),
                currency="EUR",
            ),
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.SELL,
                date=date(2025, 3, 15),
                quantity=Decimal("-4"),
                amount=Decimal("560"),
                currency="EUR",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 10),
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
        date_to=date(2025, 3, 15),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.lots is not None
    assert len(result.lots) == 1
    lot = result.lots[0]
    assert lot.open_quantity == Decimal("0")
    assert lot.closing_date == date(2025, 3, 15)


@pytest.mark.asyncio
async def test_full_history_keeps_prior_price_seed_for_first_chart_day(session, test_user, asset, broker):
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
                date=date(2025, 1, 9),
                close=Decimal("95"),
                currency="EUR",
                source_plugin_key="TEST",
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2025, 1, 11),
                close=Decimal("105"),
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
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "PRICE_HISTORY"],
    )

    assert result.lots is not None
    assert len(result.lots) == 1
    # Single valuation brain: the unified resolver now drives *valuation* exactly like the chart
    # line. On the BUY day there is no real quote, so the same-day trade (1000 / 10 = 100) wins over
    # the carried 01-09 seed (95) -> open value = 10 * 100 = 1000 (was 950 under the legacy
    # market-only map; lots-analysis and the portfolio engine now agree).
    assert result.value_history is not None
    value_points = _points_by_lot_date(result.value_history)
    assert value_points[(result.lots[0].lot_id, date(2025, 1, 10))].open_value == Decimal("1000")
    # The estimated market *line*, however, shows the most-recent observation: on the BUY day the
    # trade (1000 / 10 = 100) is newer than the 01-09 seed -> 100, flagged estimate; on 01-11 the
    # real quote (105) is the newest observation -> 105, not an estimate.
    assert result.price_history is not None
    price_points = _points_by_lot_date(result.price_history)
    assert price_points[(result.lots[0].lot_id, date(2025, 1, 10))].market_price == Decimal("100")
    assert price_points[(result.lots[0].lot_id, date(2025, 1, 10))].estimated is True
    assert price_points[(result.lots[0].lot_id, date(2025, 1, 11))].market_price == Decimal("105")
    assert price_points[(result.lots[0].lot_id, date(2025, 1, 11))].estimated is False


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
    """A short's total return is its P&L over the notional it sold: 5 sold short at 120 EUR, a notional of 600.

    Quoted 120, 110 and 100 from 10 to 12 Jan: break-even, then 5 × 10 = 50 and 5 × 20 = 100 of P&L, so 0, 50 / 600 and
    100 / 600 — the lot summary's total P&L / opening value. Compared to 12 places: the last digit of a Decimal division is
    the context's rounding, not the contract. Before CP-7a: −1, −0.92 and −0.83, a short read like a long.
    """
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
    sell = Transaction(
        broker_id=short_broker.id,
        asset_id=asset.id,
        type=TransactionType.SELL,
        date=date(2025, 1, 10),
        quantity=Decimal("-5"),
        amount=Decimal("600"),
        currency="EUR",
    )
    session.add_all(
        [
            sell,
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
    returns = {point.date: point.total_return for point in daily_points(result.return_history) if point.lot_id == sell.id}
    twelve_places = Decimal("1E-12")
    observed = {day: None if value is None else value.quantize(twelve_places) for day, value in returns.items()}
    assert observed == {
        date(2025, 1, 10): Decimal("0"),
        date(2025, 1, 11): (Decimal("50") / Decimal("600")).quantize(twelve_places),
        date(2025, 1, 12): (Decimal("100") / Decimal("600")).quantize(twelve_places),
    }


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
    assert [point.date for point in daily_points(result.performance_history)] == [date(2025, 1, 10), date(2025, 1, 11), date(2025, 1, 12)]
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
    # The resolver marks the BUY day from its own trade (1000 / 10 = 100), so performance starts on
    # 01-10 with NAV == invested -> roi 0 (was None under the legacy market-only map, which had no
    # mark until the first real quote). The 01-12 quote (120) lifts NAV to 1200 -> roi 0.2.
    assert points[date(2025, 1, 10)].roi == Decimal("0")
    assert points[date(2025, 1, 10)].twrr is None
    assert points[date(2025, 1, 11)].roi == Decimal("0")
    assert points[date(2025, 1, 11)].twrr == Decimal("0")
    assert points[date(2025, 1, 12)].roi == Decimal("0.2")
    assert points[date(2025, 1, 12)].twrr == Decimal("0.2")


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
async def test_fee_and_tax_allocated_to_lot_and_net_metrics(session, test_user, asset, broker):
    """Asset-linked FEE (same-day BUY) and TAX (same-day DIVIDEND) allocate to the lot; net metrics subtract them."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=date(2025, 1, 10), quantity=Decimal("0"), amount=Decimal("-30"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 1, 15), quantity=Decimal("0"), amount=Decimal("50"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.TAX, date=date(2025, 1, 15), quantity=Decimal("0"), amount=Decimal("-10"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 15), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
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

    assert result.calculation_status == "COMPLETE"
    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]

    # FEE (positive magnitude) and TAX allocated to the single lot.
    assert lot.allocated_fees == Decimal("30")
    assert lot.allocated_taxes == Decimal("10")
    assert lot.asset_income == Decimal("50")

    # Gross: price==cost -> market_pnl 0; total_pnl == income.
    assert lot.market_pnl == Decimal("0")
    assert lot.total_pnl == Decimal("50")
    assert lot.total_return == Decimal("50") / Decimal("1000")

    # Net subtracts costs: net_total_pnl = 50 - 30 - 10 = 10.
    assert lot.net_total_pnl == Decimal("10")
    assert lot.net_total_return == Decimal("10") / Decimal("1000")
    assert lot.net_metrics_status == "AVAILABLE"

    # No orphan: every cost/income found an eligible lot.
    assert result.asset_orphan_fees == Decimal("0")
    assert result.asset_orphan_taxes == Decimal("0")
    assert result.asset_orphan_income == Decimal("0")

    # Inline economic audit surfaces one group per pool (FEE, DIVIDEND, TAX).
    assert result.economic_allocation_groups is not None
    group_types = sorted(group.economic_type for group in result.economic_allocation_groups)
    assert group_types == ["DIVIDEND", "FEE", "TAX"]
    for group in result.economic_allocation_groups:
        allocated = sum((alloc.target_amount for op in group.operation_allocations for alloc in op.lot_allocations), Decimal("0"))
        # Conservation per pool: allocated + orphan == native pool total (single currency EUR).
        assert allocated + group.target_orphan == group.target_pool_total

    # Net value/return history at date_to reflect cumulative costs.
    v_by_date = _points_by_date([p for p in result.value_history if p.lot_id == lot.lot_id])
    end_value = v_by_date[date(2025, 1, 15)]
    assert end_value.allocated_fees == Decimal("30")
    assert end_value.allocated_taxes == Decimal("10")
    assert end_value.net_pnl == end_value.pnl - Decimal("30") - Decimal("10")
    r_by_date = _points_by_date([p for p in result.return_history if p.lot_id == lot.lot_id])
    assert r_by_date[date(2025, 1, 15)].net_total_return == Decimal("10") / Decimal("1000")


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
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 5), quantity=Decimal("0"), amount=Decimal("120"), currency="USD"),
            PriceHistory(asset_id=asset.id, date=date(2025, 1, 10), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2025, 3, 5), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()
    # 5 Mar 2025, not 1 Feb: test_buy_sell_summary_converts_to_target_currency owns
    # EUR/USD on 1 Feb, and two tests writing the same unique key raced whenever the
    # suite ran them close together.
    await _own_fx_rate(session, on=date(2025, 3, 5), base="EUR", quote="USD", rate=Decimal("1.25"))

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 3, 5),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    assert result.lots[0].asset_income == Decimal("96")  # 120 USD / 1.25


@pytest.mark.asyncio
async def test_an_asset_without_quotes_is_priced_by_its_trades_and_raises_no_at_cost_warning(session, test_user, asset, broker):
    """No asset-system price -> the resolver values the open portion at the last observed *trade*
    mark (the BUY at 15/unit), so value_source is MARKET_PRICE (observation-based) with market_pnl 0
    while price == cost; income still accrues.

    J-28 (CP-7b): the BUY prices the lot from its first day, so nothing is assumed at cost and the
    lots raise no CURRENT_PRICE_ASSUMED_AT_COST. Before CP-7b that warning was raised whenever the
    asset had no quote, although its trades priced the lots."""
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
    assert lot.value_source == "MARKET_PRICE"
    assert lot.open_value == Decimal("15000")
    assert lot.market_pnl == Decimal("0")
    assert lot.asset_income == Decimal("1250")
    assert lot.total_pnl == Decimal("1250")
    assert lot.total_return == Decimal("1250") / Decimal("15000")

    codes = {issue.code for issue in result.data_quality.issues}
    assert IssueCode.CURRENT_PRICE_ASSUMED_AT_COST not in codes, f"issues={result.data_quality.issues}"

    # History is now populated (previously skipped when market_price was None).
    assert result.value_history
    last_value = _points_by_date(result.value_history)[date(2025, 3, 1)]
    assert last_value.open_value == Decimal("15000")
    assert last_value.income == Decimal("1250")
    last_return = _points_by_date(result.return_history)[date(2025, 3, 1)]
    assert abs(last_return.total_return - Decimal("1250") / Decimal("15000")) < Decimal("1e-9")


@pytest.mark.asyncio
async def test_adjustment_only_asset_is_estimated_at_cost_not_priced_by_its_adjustment(session, test_user, asset, broker):
    """J-17: an ADJUSTMENT is never a price. An asset received only by an ADJUSTMENT-in (10 units at a
    3000 NPR cost basis on 2025-01-10, when 1 EUR = 150 NPR) and never quoted, bought or sold has no
    market price at all: its lot is ESTIMATED_AT_COST, open value = its cost converted at the opening
    date (30000 / 150 = 200 EUR) on every day, market P&L 0, and the chart has no price line.

    FX: EUR/NPR, a pair no other test stores (checked first, never committed).

    Before J-17: MARKET_PRICE with the adjustment's 3000 NPR as the price, converted at each day's
    rate — open value 250 EUR on 2025-03-01 (1 EUR = 120 NPR), market P&L +50, and a price line at the
    adjustment's cost (estimated).
    """
    stored = (await session.execute(select(FxRate.id).where(FxRate.base == "EUR", FxRate.quote == "NPR"))).all()
    assert stored == [], f"precondition broken: {len(stored)} EUR/NPR rate(s) stored by someone else — this case needs a pair nobody stores"
    session.add_all(
        [
            FxRate(date=date(2025, 1, 10), base="EUR", quote="NPR", rate=Decimal("150"), source="TEST_J17"),
            FxRate(date=date(2025, 3, 1), base="EUR", quote="NPR", rate=Decimal("120"), source="TEST_J17"),
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date(2025, 1, 10),
                quantity=Decimal("10"),
                amount=Decimal("0"),
                currency=None,
                cost_basis_override=Decimal("3000"),
                cost_basis_currency="NPR",
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
        date_to=date(2025, 3, 1),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "PRICE_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    assert (lot.value_source, lot.original_cost, lot.open_value, lot.market_pnl) == ("ESTIMATED_AT_COST", Decimal("200"), Decimal("200"), Decimal("0"))
    assert result.value_history
    off_cost = sorted((point.date, point.open_value) for point in daily_points(result.value_history) if point.open_value != Decimal("200"))
    assert off_cost == [], f"days whose open value is not the 200 EUR cost: {off_cost}"
    assert not result.price_history, f"an adjustment-only asset has no price line, got {result.price_history}"


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
    # Between the close (01-12) and the post-close quote (01-15), the resolver carries the last trade
    # mark (SELL unit 130) forward, so the lot's price line has an observation and relative_return is
    # the mark vs the opening reference (130 / 100 - 1 = 0.3) rather than None. This mirrors the
    # chart price line and the portfolio engine (single valuation brain), not the legacy market-only gap.
    assert return_points[(lot.lot_id, date(2025, 1, 13))].relative_return == Decimal("0.3")
    assert return_points[(lot.lot_id, date(2025, 1, 14))].relative_return == Decimal("0.3")
    # No real quote exists during the lot's lifetime (the only price, 01-15, is after the close), so
    # the market line is estimated from the lot's own trades: BUY unit 100 carried, stepping to the
    # SELL unit 130 on the close date. The post-close real quote falls outside the closed lot window.
    price_points = _points_by_lot_date(result.price_history)
    assert price_points[(lot.lot_id, date(2025, 1, 10))].market_price == Decimal("100")
    assert price_points[(lot.lot_id, date(2025, 1, 10))].estimated is True
    assert price_points[(lot.lot_id, date(2025, 1, 12))].market_price == Decimal("130")
    assert price_points[(lot.lot_id, date(2025, 1, 12))].estimated is True
    assert (lot.lot_id, date(2025, 1, 15)) not in price_points


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
        rows.append(PriceHistory(asset_id=asset.id, date=buy_date, close=unit_cost, currency="EUR", source_plugin_key="TEST"))
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


@pytest.mark.asyncio
async def test_bond_quote_base_quantity_scales_open_value_and_pnl(session, test_user, broker):
    """BTP-style bond: the raw quote is per 100 nominal (quote_base_quantity=100).

    Reproduces the user report: a bond lot showed a +9000% P&L because open_value was
    computed as quantity * raw_price (100000 * 102.5) instead of applying the base-100
    scaling. With the fix, open_value = (quantity / 100) * price, so market value and P&L
    stay on the same scale as the real money cost basis.
    """
    stamp = str(utcnow().timestamp()).replace(".", "")
    bond = Asset(
        display_name=f"BTP_{stamp}",
        identifier_ticker=f"BTP{stamp[-4:]}",
        currency="EUR",
        asset_type=AssetType.BOND,
        quote_base_quantity=100,
    )
    session.add(bond)
    await session.flush()

    # Buy 1000 nominal at quoted 98.00 -> real cost (1000/100)*98.00 = 980 EUR.
    session.add_all(
        [
            Transaction(
                broker_id=broker.id,
                asset_id=bond.id,
                type=TransactionType.BUY,
                date=date(2025, 1, 10),
                quantity=Decimal("1000"),
                amount=Decimal("-980"),
                currency="EUR",
            ),
            PriceHistory(asset_id=bond.id, date=date(2025, 1, 10), close=Decimal("98.00"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=bond.id, date=date(2025, 1, 15), close=Decimal("102.50"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=bond.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 15),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    # (1000 / 100) * 102.50 = 1025, NOT 102500.
    assert lot.open_value == Decimal("1025.00")
    assert lot.total_value == Decimal("1025.00")
    assert lot.original_cost == Decimal("980")
    assert lot.pnl == Decimal("45.00")
    # 45 / 980 ~= 4.59%, a sane bond return (not +9000%).
    assert lot.total_return is not None and lot.total_return < Decimal("0.10")

    # Value history at the latest date carries the scaled market value.
    value_points = _points_by_lot_date(result.value_history)
    latest_value = value_points[(lot.lot_id, date(2025, 1, 15))]
    assert latest_value.open_value == Decimal("1025.00")
    assert latest_value.pnl == Decimal("45.00")

    # Return history at the latest date is scaled the same way.
    return_points = _points_by_lot_date(result.return_history)
    latest_return = return_points[(lot.lot_id, date(2025, 1, 15))]
    assert latest_return.total_return is not None and latest_return.total_return < Decimal("0.10")


@pytest.mark.asyncio
async def test_bond_relative_return_scaled_when_opening_has_no_market_price(session, test_user, broker):
    """BTP bought at emission: the opening date predates the first market quote, so the reference
    price falls back to the lot's own buy price. That buy price is per-single-unit (cost / raw
    quantity), while market_price is quoted per 100 nominal; without scaling the fallback by
    quote_base_quantity, relative_return compared the two on different axes and reported ~+9700%
    instead of the real ~-2% market move (user round-8 report)."""
    stamp = str(utcnow().timestamp()).replace(".", "")
    bond = Asset(
        display_name=f"BTP_EMIT_{stamp}",
        identifier_ticker=f"BTE{stamp[-4:]}",
        currency="EUR",
        asset_type=AssetType.BOND,
        quote_base_quantity=100,
    )
    session.add(bond)
    await session.flush()

    # Buy 1000 nominal at par: amount -1000 -> per-single-unit cost 1.0. The first market quote
    # appears only 5 days later, so the opening day (2025-01-10) has no price and the reference
    # falls back to the buy price.
    session.add_all(
        [
            Transaction(
                broker_id=broker.id,
                asset_id=bond.id,
                type=TransactionType.BUY,
                date=date(2025, 1, 10),
                quantity=Decimal("1000"),
                amount=Decimal("-1000"),
                currency="EUR",
            ),
            PriceHistory(asset_id=bond.id, date=date(2025, 1, 15), close=Decimal("98.00"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=bond.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 15),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "RETURN_HISTORY"],
    )

    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    # Fallback reference is the par buy price rescaled to the per-100 market axis (1.0 * 100 = 100),
    # not the raw per-single-unit 1.0.
    assert lot.reference_unit_price == Decimal("100")
    # 98.00 / 100 - 1 = -0.02, a ~-2% market move, NOT +9700%.
    assert lot.relative_return is not None and lot.relative_return == Decimal("-0.02")

    # Return history uses the same scaled reference.
    return_points = _points_by_lot_date(result.return_history)
    latest_return = return_points[(lot.lot_id, date(2025, 1, 15))]
    assert latest_return.relative_return is not None and latest_return.relative_return == Decimal("-0.02")


@pytest.mark.asyncio
async def test_price_history_estimates_market_line_from_last_known_trade(session, test_user, asset, broker):
    # Price-less asset (no PriceHistory rows): the chart's market-price line is estimated from the
    # last-known trade (BUY cost, then SELL proceeds) carried forward, stepping up at the sale.
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
        requested_analyses=["PRICE_HISTORY"],
    )

    assert result.price_history is not None and len(result.price_history) > 0
    points = _points_by_date(result.price_history)
    # Before the sale: carried BUY unit price (1000 / 10 = 100), flagged as an estimate.
    assert points[date(2025, 1, 15)].market_price == Decimal("100")
    assert points[date(2025, 1, 15)].estimated is True
    # After the sale: steps up to the SELL unit price (520 / 4 = 130), still an estimate.
    assert points[date(2025, 2, 5)].market_price == Decimal("130")
    assert points[date(2025, 2, 5)].estimated is True


@pytest.mark.asyncio
async def test_price_history_real_quote_wins_but_trade_fills_later_gap(session, test_user, asset, broker):
    # A single real quote at opening, no later quotes: the real price is carried forward (not an
    # estimate) while it is the most recent observation; once a later SELL happens, the trade price
    # becomes the most recent observation and fills the gap, flagged as an estimate.
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
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 2, 5),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["PRICE_HISTORY"],
    )

    assert result.price_history is not None and len(result.price_history) > 0
    points = _points_by_date(result.price_history)
    # Gap after the only real quote, before the sale: carried real price, NOT an estimate.
    assert points[date(2025, 1, 20)].market_price == Decimal("100")
    assert points[date(2025, 1, 20)].estimated is False
    # After the sale: the trade is the most recent observation -> fills with 130, flagged estimate.
    assert points[date(2025, 2, 3)].market_price == Decimal("130")
    assert points[date(2025, 2, 3)].estimated is True


@pytest.mark.asyncio
async def test_an_asset_without_a_rate_to_the_target_currency_is_degraded_never_valued_in_its_own_currency(session, test_user, broker):
    """B3a: a VND asset, quoted and bought in VND, analysed in EUR with no VND/EUR rate or route.

    Every VND amount is unknown in EUR. The service used to put the native figures in the EUR
    fields -- 26 000 VND per share shown as 26 000 EUR, the 2 500 000 VND purchase counted as
    2 500 000 EUR -- and report nothing. It must instead leave empty what needs the missing rate
    and say why: VND/EUR in ``missing_fx_pairs`` (the BUY date among its dates), the
    MISSING_FX_MARKET issue the portfolio banner raises for an unconfigured pair, and DEGRADED.

    The absence of the pair is owned, not assumed. ``fx_rates`` and ``fx_conversion_routes`` are
    global and store a pair alphabetically (EUR/VND): both are emptied for it inside this test's
    transaction, which the ``session`` fixture rolls back -- the ``_own_fx_rate`` contract. A
    neighbour's committed rate would matter even if years old: the FX service backward-fills
    without limit.
    """
    stamp = str(utcnow().timestamp()).replace(".", "")
    vnd_asset = Asset(display_name=f"LotsVND_{stamp}", identifier_ticker=f"LVND{stamp[-4:]}", currency="VND", asset_type=AssetType.STOCK)
    session.add(vnd_asset)
    await session.flush()
    base, quote = sorted(("VND", "EUR"))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))

    buy_date = date(2025, 6, 9)
    date_to = date(2025, 6, 13)
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=vnd_asset.id, type=TransactionType.BUY, date=buy_date, quantity=Decimal("100"), amount=Decimal("-2500000"), currency="VND"),
            PriceHistory(asset_id=vnd_asset.id, date=buy_date, close=Decimal("25000"), currency="VND", source_plugin_key="TEST"),
            PriceHistory(asset_id=vnd_asset.id, date=date(2025, 6, 12), close=Decimal("26000"), currency="VND", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=vnd_asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY", "PRICE_HISTORY", "PERFORMANCE_HISTORY"],
    )

    # Presence first: the BUY opened this asset's only lot, and the analysis covers its five days.
    window = [buy_date + timedelta(days=offset) for offset in range((date_to - buy_date).days + 1)]
    assert result.lots is not None and len(result.lots) == 1
    lot = result.lots[0]
    assert (lot.opening_date, lot.original_quantity) == (buy_date, Decimal("100"))
    assert result.performance_history is not None
    assert [point.date for point in daily_points(result.performance_history)] == window

    # Reported: the status, the pair with the BUY date, the issue.
    assert result.calculation_status == "DEGRADED"
    assert result.data_quality is not None
    missing_dates = {item.pair: item.dates for item in result.data_quality.missing_fx_pairs}
    assert buy_date in missing_dates.get("VND/EUR", []), f"missing_fx_pairs={result.data_quality.missing_fx_pairs}"
    # The banner names a pair by its slug: both codes sorted, joined by a dash (_normalize_fx_pair_slug).
    market_issue_pairs = [issue.affected_fx_pairs for issue in result.data_quality.issues if issue.code == IssueCode.MISSING_FX_MARKET]
    assert any("EUR-VND" in pairs for pairs in market_issue_pairs), f"issues={result.data_quality.issues}"

    # Never valued in VND as if it were EUR: no figure, no point, no performance.
    assert (lot.open_value, lot.pnl, lot.total_pnl) == (None, None, None)
    assert result.value_history is not None
    assert [(point.date, point.open_value) for point in daily_points(result.value_history) if point.lot_id == lot.lot_id] == []
    assert result.price_history is not None
    assert [(point.date, point.market_price) for point in daily_points(result.price_history) if point.lot_id == lot.lot_id] == []
    assert [(point.date, point.roi, point.twrr) for point in daily_points(result.performance_history)] == [(day, None, None) for day in window]


# --------------------------------------------------------------------------- #
# B3b: an economic event without a rate is withheld on the lots it reaches
# --------------------------------------------------------------------------- #
#
# The asset is in EUR and analysed in EUR; the events (or the trades weighting them)
# are in VND, which has no rate and no route to EUR. The engine still places such an
# event -- the service hands it the native amount only as a placeholder -- and its
# audit says which lots each pool reaches. On those lots, from the pool's date, every
# figure that needs the event in EUR is withheld (None) and net_metrics_status says
# UNAVAILABLE; every other lot, figure and day keeps its value. Today the native
# amount is read as euros and nothing is withheld.

_ECONOMIC_ANALYSES = ["LOT_SUMMARY", "VALUE_HISTORY", "RETURN_HISTORY", "INCOME_EVENTS"]


async def _own_missing_rate(session, currency: str, target: str) -> None:
    """Guarantee that ``currency`` has no rate and no route to ``target`` while this test runs.

    The ``_own_fx_rate`` contract applied to an absence: ``fx_rates`` and ``fx_conversion_routes`` are
    global and store a pair alphabetically, so both are emptied for it inside this test's transaction,
    which the ``session`` fixture rolls back -- a neighbour's rows come back intact. Even a years-old
    rate would matter: the FX service backward-fills without limit.
    """
    base, quote = sorted((currency, target))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))


async def _economic_analysis(session, user: User, asset: Asset, broker: Broker, date_to: date):
    """The four analyses that read the economic allocation, on this test's own broker, in EUR."""
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=_ECONOMIC_ANALYSES,
    )


def _assert_reported_missing(result, pair: str, on: date) -> None:
    """Precondition: the analysis itself reports the rate missing that day (B3a), so a None below is about it."""
    assert result.data_quality is not None
    missing = {item.pair: item.dates for item in result.data_quality.missing_fx_pairs}
    assert on in missing.get(pair, []), f"missing_fx_pairs={result.data_quality.missing_fx_pairs}"


def _group_of(result, transaction_id: int) -> EconomicAllocationGroupSchema:
    """The audit group pooling ``transaction_id``: found by the source this test created, never by position."""
    assert result.economic_allocation_groups is not None
    matches = [group for group in result.economic_allocation_groups if transaction_id in group.source_transaction_ids]
    assert len(matches) == 1, f"economic_allocation_groups={result.economic_allocation_groups}"
    return matches[0]


def _lot_allocations(group: EconomicAllocationGroupSchema) -> dict[int, EconomicLotAllocationSchema]:
    return {allocation.lot_id: allocation for operation in group.operation_allocations for allocation in operation.lot_allocations}


def _figures(row, expected: dict) -> dict:
    """The fields of ``row`` named by ``expected``, to compare in one assertion that shows every value."""
    return {name: getattr(row, name) for name in expected}


def _days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _lot_points(points, lot_id: int) -> dict:
    return _points_by_date([point for point in points if point.lot_id == lot_id])


@dataclass(frozen=True)
class _DividendSeed:
    buy_a: Transaction
    buy_b: Transaction
    buy_c: Transaction
    eur_dividend: Transaction
    vnd_dividend: Transaction
    date_to: date


async def _seed_a_dividend_without_a_rate(session, asset: Asset, broker: Broker) -> _DividendSeed:
    """Two EUR lots paid an EUR dividend, then a VND one without a rate; a third lot opens the day after.

    * A: 10 bought on 3 Mar, B: 30 bought on 4 Mar, both at 100 EUR.
    * 10 Mar, 40 EUR of dividend: A and B held on D-1, 10 and 30.
    * 24 Mar, 80 VND of dividend: A and B held on D-1 again. Without a rate; today read as 80 EUR, 20 and 60.
    * C: 5 bought on 25 Mar at 100 EUR, after both dividends: reached by neither.
    * Priced 100 EUR until 110 EUR on 30 Apr, the end of the analysis (more than 30 days for each lot,
      so their annualized return is computed).

    The VND amount is small on purpose: the native fallback then yields a plausible figure (+3% of
    income on A), which is exactly what makes it dangerous; an absurd one would be noticed.
    """
    buy_a = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 3, 3), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    buy_b = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 3, 4), quantity=Decimal("30"), amount=Decimal("-3000"), currency="EUR")
    eur_dividend = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 10), quantity=Decimal("0"), amount=Decimal("40"), currency="EUR")
    vnd_dividend = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 24), quantity=Decimal("0"), amount=Decimal("80"), currency="VND")
    buy_c = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 3, 25), quantity=Decimal("5"), amount=Decimal("-500"), currency="EUR")
    date_to = date(2025, 4, 30)
    session.add_all(
        [
            buy_a,
            buy_b,
            eur_dividend,
            vnd_dividend,
            buy_c,
            *(PriceHistory(asset_id=asset.id, date=day, close=Decimal("100"), currency="EUR", source_plugin_key="TEST") for day in (buy_a.date, buy_b.date, buy_c.date)),
            PriceHistory(asset_id=asset.id, date=date_to, close=Decimal("110"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()
    return _DividendSeed(buy_a=buy_a, buy_b=buy_b, buy_c=buy_c, eur_dividend=eur_dividend, vnd_dividend=vnd_dividend, date_to=date_to)


@pytest.mark.asyncio
async def test_a_dividend_without_a_rate_is_withheld_from_the_summary_of_the_lots_it_reaches(session, test_user, asset, broker):
    """B3b: the VND dividend reaches lots A and B, whose income in EUR is then unknown.

    Their income, every figure built on it (total P&L, cash yield, total return, the net figures, the
    annualized return) and their net metrics status are withheld; what does not depend on income (value,
    P&L, market P&L, fees, taxes) stays. Today the 80 VND count as 80 EUR on top of the 40 EUR dividend.
    Lot C opened after the dividend: not reached, it keeps every figure.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_dividend_without_a_rate(session, asset, broker)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.vnd_dividend.date)
    assert result.lots is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    lot_a, lot_b, lot_c = lots[seed.buy_a.id], lots[seed.buy_b.id], lots[seed.buy_c.id]

    # Not reached: C keeps its figures, the net ones included.
    c_expected = {
        "asset_income": Decimal("0"),
        "open_value": Decimal("550"),
        "pnl": Decimal("50"),
        "total_pnl": Decimal("50"),
        "cash_yield": Decimal("0"),
        "total_return": Decimal("0.1"),
        "allocated_fees": Decimal("0"),
        "allocated_taxes": Decimal("0"),
        "net_total_pnl": Decimal("50"),
        "net_total_return": Decimal("0.1"),
        "annualized_return": cumulative_to_annualized(Decimal("0.1"), (seed.date_to - seed.buy_c.date).days),
        "net_metrics_status": "AVAILABLE",
    }
    assert _figures(lot_c, c_expected) == c_expected

    # Reached: what does not depend on income stays.
    for lot, cost in ((lot_a, Decimal("1000")), (lot_b, Decimal("3000"))):
        capital = {"open_value": cost * Decimal("1.1"), "pnl": cost / 10, "market_pnl": cost / 10, "allocated_fees": Decimal("0"), "allocated_taxes": Decimal("0")}
        assert _figures(lot, capital) == capital, f"lot {lot.lot_id}"

    # Reached: income and every figure built on it are withheld, and the lot says so.
    withheld = dict.fromkeys(("asset_income", "total_pnl", "cash_yield", "total_return", "net_total_pnl", "net_total_return", "annualized_return"))
    for lot in (lot_a, lot_b):
        assert _figures(lot, withheld) == withheld, f"lot {lot.lot_id}"
        assert lot.net_metrics_status == "UNAVAILABLE", f"lot {lot.lot_id}"


@pytest.mark.asyncio
async def test_a_dividend_without_a_rate_is_withheld_from_the_histories_from_its_date(session, test_user, asset, broker):
    """B3b: the same dividend in the value and return histories of lots A and B.

    Up to the day before it the income is known (the EUR dividend: 10 and 30 from 10 Mar), and so are
    the returns built on it. From 24 Mar the income is unknown, and with it the income-inclusive total
    return and the net total return; the capital fields and the value history's net P&L (which excludes
    income) stay. Today the VND amount is added to the income as if it were euros.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_dividend_without_a_rate(session, asset, broker)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.vnd_dividend.date)
    assert result.value_history is not None and result.return_history is not None
    vnd_date = seed.vnd_dividend.date
    day_before = vnd_date - timedelta(days=1)
    from_vnd_date = _days_between(vnd_date, seed.date_to)
    for lot_id, cost, eur_share in ((seed.buy_a.id, Decimal("1000"), Decimal("10")), (seed.buy_b.id, Decimal("3000"), Decimal("30"))):
        values, returns = _lot_points(result.value_history, lot_id), _lot_points(result.return_history, lot_id)

        # Known before: nothing until the EUR dividend, its share from then to the day before the VND one.
        assert (values[date(2025, 3, 9)].income, returns[date(2025, 3, 9)].income) == (Decimal("0"), Decimal("0")), f"lot {lot_id}"
        known = (values[day_before].income, returns[day_before].income, returns[day_before].total_return, returns[day_before].net_total_return)
        assert known == (eur_share, eur_share, Decimal("0.01"), Decimal("0.01")), f"lot {lot_id}"

        # Every day from the VND dividend on keeps its points and their capital fields.
        assert [day for day in sorted(values) if day >= vnd_date] == from_vnd_date, f"lot {lot_id}"
        assert [day for day in sorted(returns) if day >= vnd_date] == from_vnd_date, f"lot {lot_id}"
        capital_at_end = {"open_value": cost * Decimal("1.1"), "proceeds": Decimal("0"), "total_value": cost * Decimal("1.1"), "original_cost": cost, "pnl": cost / 10, "net_pnl": cost / 10}
        assert _figures(values[seed.date_to], capital_at_end) == capital_at_end, f"lot {lot_id}"
        assert returns[seed.date_to].relative_return == Decimal("0.1"), f"lot {lot_id}"

        # Withheld from the VND dividend on.
        assert {values[day].income for day in from_vnd_date} == {None}, f"lot {lot_id}"
        assert {(returns[day].income, returns[day].total_return, returns[day].net_total_return) for day in from_vnd_date} == {(None, None, None)}, f"lot {lot_id}"


@pytest.mark.asyncio
async def test_a_dividend_without_a_rate_is_withheld_from_its_income_event(session, test_user, asset, broker):
    """B3b: the chart marker of the VND dividend still names the lots it reached, but has no EUR amount.

    Today its amount is the native 80 VND read as 80 EUR. The EUR dividend's marker is unchanged.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_dividend_without_a_rate(session, asset, broker)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.vnd_dividend.date)
    assert result.income_events is not None
    events = {event.transaction_id: event for event in result.income_events}
    eur_event, vnd_event = events[seed.eur_dividend.id], events[seed.vnd_dividend.id]
    reached = {seed.buy_a.id, seed.buy_b.id}
    assert (eur_event.date, eur_event.amount, set(eur_event.lot_ids)) == (seed.eur_dividend.date, Decimal("40"), reached)
    assert (vnd_event.date, set(vnd_event.lot_ids)) == (seed.vnd_dividend.date, reached)
    assert vnd_event.amount is None


@pytest.mark.asyncio
async def test_a_degraded_pool_is_withheld_from_the_audit_but_keeps_its_native_figures(session, test_user, asset, broker):
    """B3b: the audit group of the VND dividend.

    Its native figures are right -- 80 VND split 1:3 by the quantities held on D-1 -- and stay. Its target
    figures (pool total, orphan, each lot's amount) are withheld: today they are the same native numbers
    labelled EUR. The EUR dividend's group, a pool with its rate, keeps its target figures.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_dividend_without_a_rate(session, asset, broker)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.vnd_dividend.date)
    eur_group, vnd_group = _group_of(result, seed.eur_dividend.id), _group_of(result, seed.vnd_dividend.id)
    lot_a, lot_b = seed.buy_a.id, seed.buy_b.id

    # Control: a pool with its rate keeps its target figures.
    assert (eur_group.target_pool_total, eur_group.target_orphan) == (Decimal("40"), Decimal("0"))
    assert {lot_id: allocation.target_amount for lot_id, allocation in _lot_allocations(eur_group).items()} == {lot_a: Decimal("10"), lot_b: Decimal("30")}

    # The VND pool: who it is and its native figures stay.
    assert (vnd_group.economic_type, vnd_group.native_currency, vnd_group.target_currency, vnd_group.rule) == ("DIVIDEND", "VND", "EUR", "ASSET_INCOME_HOLDINGS")
    assert (vnd_group.native_pool_total, vnd_group.native_orphan) == (Decimal("80"), Decimal("0"))
    vnd_allocations = _lot_allocations(vnd_group)
    assert {lot_id: (allocation.weight, allocation.native_amount) for lot_id, allocation in vnd_allocations.items()} == {lot_a: (Decimal("0.25"), Decimal("20")), lot_b: (Decimal("0.75"), Decimal("60"))}

    # Its target figures are withheld.
    assert (vnd_group.target_pool_total, vnd_group.target_orphan) == (None, None)
    assert {lot_id: allocation.target_amount for lot_id, allocation in vnd_allocations.items()} == {lot_a: None, lot_b: None}


@pytest.mark.asyncio
async def test_a_fee_without_a_rate_is_withheld_from_the_lot_its_same_day_trade_closed(session, test_user, asset, broker):
    """B3b: a FEE of 9 VND, without a rate, on the day an EUR SELL closed 4 of lot A.

    The FEE follows its same-day trade, so all of it lands on A, whose fees in EUR are unknown from that
    day: its allocated fees, net P&L and net returns are withheld and its net metrics are UNAVAILABLE.
    Before that day its 7 EUR fee (on its BUY) is known, and so are its gross figures throughout. Today
    the 9 VND are added to the 7 EUR as euros (16). Lot B, which the SELL did not touch, keeps its figures.
    """
    await _own_missing_rate(session, "VND", "EUR")
    buy_a = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 6), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    eur_fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=date(2025, 1, 6), quantity=Decimal("0"), amount=Decimal("-7"), currency="EUR")
    buy_b = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 1, 20), quantity=Decimal("20"), amount=Decimal("-2200"), currency="EUR")
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 2, 10), quantity=Decimal("-4"), amount=Decimal("480"), currency="EUR")
    vnd_fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=date(2025, 2, 10), quantity=Decimal("0"), amount=Decimal("-9"), currency="VND")
    date_to = date(2025, 2, 20)
    session.add_all(
        [
            buy_a,
            eur_fee,
            buy_b,
            sell,
            vnd_fee,
            *(PriceHistory(asset_id=asset.id, date=day, close=close, currency="EUR", source_plugin_key="TEST") for day, close in ((date(2025, 1, 6), Decimal("100")), (date(2025, 1, 15), Decimal("110")), (date(2025, 1, 20), Decimal("110")), (date(2025, 2, 10), Decimal("120")))),
        ]
    )
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, date_to)

    _assert_reported_missing(result, "VND/EUR", vnd_fee.date)
    vnd_group = _group_of(result, vnd_fee.id)
    assert (vnd_group.rule, set(_lot_allocations(vnd_group))) == ("SAME_DAY_TRADES", {buy_a.id})
    assert result.lots is not None and result.value_history is not None and result.return_history is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    lot_a, lot_b = lots[buy_a.id], lots[buy_b.id]

    # Not reached: B (20 at 110, now 120) keeps its fees and net figures.
    b_expected = {"allocated_fees": Decimal("0"), "total_pnl": Decimal("200"), "net_total_pnl": Decimal("200"), "net_total_return": Decimal("200") / Decimal("2200"), "net_metrics_status": "AVAILABLE"}
    assert _figures(lot_b, b_expected) == b_expected

    # Reached, but gross: 6 open at 120 plus 480 of proceeds against a cost of 1000, 80 of it realized.
    a_gross = {"pnl": Decimal("200"), "realized_pnl": Decimal("80"), "market_pnl": Decimal("120"), "asset_income": Decimal("0"), "total_pnl": Decimal("200"), "total_return": Decimal("0.2"), "allocated_taxes": Decimal("0")}
    assert _figures(lot_a, a_gross) == a_gross

    # A's history before the VND fee: the 7 EUR fee is known, and its net P&L / net return with it.
    values, returns = _lot_points(result.value_history, buy_a.id), _lot_points(result.return_history, buy_a.id)
    assert [(day, values[day].pnl, values[day].allocated_fees, values[day].net_pnl) for day in (date(2025, 1, 6), date(2025, 2, 9))] == [
        (date(2025, 1, 6), Decimal("0"), Decimal("7"), Decimal("-7")),
        (date(2025, 2, 9), Decimal("100"), Decimal("7"), Decimal("93")),
    ]
    assert returns[date(2025, 2, 9)].net_total_return == Decimal("0.093")
    from_fee_date = _days_between(vnd_fee.date, date_to)
    assert [day for day in sorted(values) if day >= vnd_fee.date] == from_fee_date
    assert [day for day in sorted(returns) if day >= vnd_fee.date] == from_fee_date
    assert {(values[day].pnl, values[day].income, values[day].allocated_taxes, returns[day].total_return) for day in from_fee_date} == {(Decimal("200"), Decimal("0"), Decimal("0"), Decimal("0.2"))}

    # Withheld on A: its fees and everything net, in the summary and from the VND fee's date on.
    withheld = dict.fromkeys(("allocated_fees", "net_total_pnl", "net_total_return", "annualized_return"))
    assert _figures(lot_a, withheld) == withheld
    assert lot_a.net_metrics_status == "UNAVAILABLE"
    assert {(values[day].allocated_fees, values[day].net_pnl, returns[day].net_total_return) for day in from_fee_date} == {(None, None, None)}


@pytest.mark.asyncio
async def test_a_tax_without_a_rate_is_withheld_but_the_income_it_taxes_is_not(session, test_user, asset, broker):
    """B3b: a TAX of 12 VND, without a rate, on the day of a 50 EUR dividend on the only lot.

    The TAX follows the income it taxes and reaches the same lot. The dividend has its rate: the income,
    the gross figures built on it (total P&L, cash yield, total return) and the income-inclusive return
    history stay. The taxes and every net figure are withheld, from the dividend's date on in the
    histories, and the net metrics are UNAVAILABLE. Today the 12 VND are subtracted as 12 EUR.
    """
    await _own_missing_rate(session, "VND", "EUR")
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 8, 4), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    dividend = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 9, 1), quantity=Decimal("0"), amount=Decimal("50"), currency="EUR")
    vnd_tax = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.TAX, date=date(2025, 9, 1), quantity=Decimal("0"), amount=Decimal("-12"), currency="VND")
    date_to = date(2025, 9, 10)
    session.add_all(
        [
            buy,
            dividend,
            vnd_tax,
            PriceHistory(asset_id=asset.id, date=buy.date, close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date_to, close=Decimal("110"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, date_to)

    _assert_reported_missing(result, "VND/EUR", vnd_tax.date)
    tax_group = _group_of(result, vnd_tax.id)
    assert (tax_group.rule, set(_lot_allocations(tax_group))) == ("SAME_DAY_INCOME", {buy.id})
    assert result.lots is not None and result.value_history is not None and result.return_history is not None
    lot = next(row for row in result.lots if row.lot_id == buy.id)

    # Known: the income and the gross figures (10 at 110 against 1000, plus 50 of dividend).
    gross = {"asset_income": Decimal("50"), "allocated_fees": Decimal("0"), "pnl": Decimal("100"), "total_pnl": Decimal("150"), "cash_yield": Decimal("0.05"), "total_return": Decimal("0.15")}
    assert _figures(lot, gross) == gross

    values, returns = _lot_points(result.value_history, buy.id), _lot_points(result.return_history, buy.id)
    day_before = vnd_tax.date - timedelta(days=1)
    assert (values[day_before].allocated_taxes, values[day_before].net_pnl, returns[day_before].net_total_return) == (Decimal("0"), Decimal("0"), Decimal("0"))
    from_tax_date = _days_between(vnd_tax.date, date_to)
    assert [day for day in sorted(values) if day >= vnd_tax.date] == from_tax_date
    assert [day for day in sorted(returns) if day >= vnd_tax.date] == from_tax_date
    assert [(day, values[day].income, returns[day].income, returns[day].total_return) for day in (vnd_tax.date, date_to)] == [
        (vnd_tax.date, Decimal("50"), Decimal("50"), Decimal("0.05")),
        (date_to, Decimal("50"), Decimal("50"), Decimal("0.15")),
    ]

    # Withheld: the taxes and everything net.
    withheld = dict.fromkeys(("allocated_taxes", "net_total_pnl", "net_total_return", "annualized_return"))
    assert _figures(lot, withheld) == withheld
    assert lot.net_metrics_status == "UNAVAILABLE"
    assert {(values[day].allocated_taxes, values[day].net_pnl, returns[day].net_total_return) for day in from_tax_date} == {(None, None, None)}


@pytest.mark.asyncio
@pytest.mark.parametrize(("fee_delay", "rule"), [(0, "SAME_DAY_TRADES"), (1, "PREVIOUS_DAY_TRADES")], ids=["same-day-trades", "previous-day-trades"])
async def test_a_fee_weighted_by_trades_in_mixed_currencies_one_without_a_rate_is_withheld(session, test_user, asset, broker, fee_delay, rule):
    """B3b: a 20 EUR FEE weighted by two BUYs of 10 each, one paid 1000 EUR, the other 1000 VND without a rate.

    The FEE is known in EUR but its split is not: the weights are the trades' EUR values and one is
    unknown. Today the 1000 VND weigh as 1000 EUR and the FEE is halved, 10 and 10 -- a split no rate
    supports. Both lots' fees are withheld, whether the trades are on the FEE's day or the day before.
    """
    await _own_missing_rate(session, "VND", "EUR")
    trade_date = date(2025, 4, 7)
    buy_eur = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=trade_date, quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    buy_vnd = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=trade_date, quantity=Decimal("10"), amount=Decimal("-1000"), currency="VND")
    fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=trade_date + timedelta(days=fee_delay), quantity=Decimal("0"), amount=Decimal("-20"), currency="EUR")
    date_to = date(2025, 5, 12)
    session.add_all([buy_eur, buy_vnd, fee, PriceHistory(asset_id=asset.id, date=trade_date, close=Decimal("100"), currency="EUR", source_plugin_key="TEST")])
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, date_to)

    _assert_reported_missing(result, "VND/EUR", trade_date)
    fee_group = _group_of(result, fee.id)
    assert (fee_group.rule, fee_group.native_currency, fee_group.native_pool_total, set(_lot_allocations(fee_group))) == (rule, "EUR", Decimal("20"), {buy_eur.id, buy_vnd.id})
    assert result.lots is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    eur_lot, vnd_lot = lots[buy_eur.id], lots[buy_vnd.id]

    # Gross: the EUR lot is worth what it cost.
    gross = {"pnl": Decimal("0"), "total_pnl": Decimal("0"), "total_return": Decimal("0")}
    assert _figures(eur_lot, gross) == gross

    # Withheld on both lots: their share of the FEE, and on the EUR lot every net figure.
    for lot in (eur_lot, vnd_lot):
        assert (lot.allocated_fees, lot.net_metrics_status) == (None, "UNAVAILABLE"), f"lot {lot.lot_id}"
    withheld = dict.fromkeys(("net_total_pnl", "net_total_return", "annualized_return"))
    assert _figures(eur_lot, withheld) == withheld


@pytest.mark.asyncio
async def test_a_fee_weighted_by_trades_all_in_one_rate_less_currency_is_not_withheld(session, test_user, asset, broker):
    """B3b guard: the same 20 EUR FEE weighted by two BUYs both paid in VND, 3000 and 1000, still without a rate.

    The EUR value of each trade is unknown, but in one currency their ratio is exact (3:1), so the split
    is known: 15 and 5. The pool is not degraded: the lots keep their fees and AVAILABLE, and the audit
    its target figures. (The lots' VND cost has no rate either; that is the base fields' rule, pinned by
    the pure tests, not this one.)
    """
    await _own_missing_rate(session, "VND", "EUR")
    trade_date = date(2025, 4, 14)
    buy_big = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=trade_date, quantity=Decimal("10"), amount=Decimal("-3000"), currency="VND")
    buy_small = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=trade_date, quantity=Decimal("10"), amount=Decimal("-1000"), currency="VND")
    fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=trade_date, quantity=Decimal("0"), amount=Decimal("-20"), currency="EUR")
    session.add_all([buy_big, buy_small, fee, PriceHistory(asset_id=asset.id, date=trade_date, close=Decimal("100"), currency="EUR", source_plugin_key="TEST")])
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, date(2025, 4, 30))

    _assert_reported_missing(result, "VND/EUR", trade_date)
    fee_group = _group_of(result, fee.id)
    assert (fee_group.rule, fee_group.target_pool_total) == ("SAME_DAY_TRADES", Decimal("20"))
    assert {lot_id: allocation.target_amount for lot_id, allocation in _lot_allocations(fee_group).items()} == {buy_big.id: Decimal("15"), buy_small.id: Decimal("5")}
    assert result.lots is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    assert {lot_id: (lots[lot_id].allocated_fees, lots[lot_id].net_metrics_status) for lot_id in (buy_big.id, buy_small.id)} == {
        buy_big.id: (Decimal("15"), "AVAILABLE"),
        buy_small.id: (Decimal("5"), "AVAILABLE"),
    }


@dataclass(frozen=True)
class _TradeSplitSeed:
    sell: Transaction
    vnd_trade: Transaction
    fee: Transaction
    lot_a: int
    lot_a2: int
    vnd_lot: int
    vnd_context: str
    date_to: date


async def _seed_a_fee_split_by_two_trades(session, asset: Asset, broker: Broker, *, sell_currency: str, vnd_trade_type: TransactionType, fee_delay: int) -> _TradeSplitSeed:
    """A 20 EUR FEE weighted by two trades on 13 Oct: a SELL in ``sell_currency``, and a trade in VND, which has no rate.

    * A: 15 bought on 6 Oct for 1500, A2: 5 on 7 Oct for 500, both in ``sell_currency``; V: 10 on 8 Oct for 1000 VND.
    * 13 Oct: the SELL of 20 for 3000 closes all of A and A2, so it reaches them by 15:5. The VND trade is a SELL
      of 4 of V for 1000 VND (two SELLs) or a BUY of 10 for 1000 VND opening its own lot (a SELL and a BUY).
    * The FEE is paid on 13 Oct (same-day trades) or on 14 Oct (previous-day trades).

    Weighted by the trades' values, 3000 against 1000, the FEE splits 15 and 5 -- when their ratio is known.
    """
    trade_date = date(2025, 10, 13)
    buy_a = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 10, 6), quantity=Decimal("15"), amount=Decimal("-1500"), currency=sell_currency)
    buy_a2 = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 10, 7), quantity=Decimal("5"), amount=Decimal("-500"), currency=sell_currency)
    buy_v = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 10, 8), quantity=Decimal("10"), amount=Decimal("-1000"), currency="VND")
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=trade_date, quantity=Decimal("-20"), amount=Decimal("3000"), currency=sell_currency)
    prices = [PriceHistory(asset_id=asset.id, date=day, close=close, currency="EUR", source_plugin_key="TEST") for day, close in ((buy_a.date, Decimal("100")), (trade_date, Decimal("150")))]
    session.add_all([buy_a, buy_a2, buy_v, sell, *prices])
    await session.flush()
    # Same-day trades replay by transaction id. Flushed after the SELL, the VND trade comes second: the SELL closes
    # the oldest lots, A and A2, and a VND SELL then closes V -- never a lot bought in another currency.
    closes_v = vnd_trade_type is TransactionType.SELL
    vnd_quantity, vnd_amount = (Decimal("-4"), Decimal("1000")) if closes_v else (Decimal("10"), Decimal("-1000"))
    vnd_trade = Transaction(broker_id=broker.id, asset_id=asset.id, type=vnd_trade_type, date=trade_date, quantity=vnd_quantity, amount=vnd_amount, currency="VND")
    fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=trade_date + timedelta(days=fee_delay), quantity=Decimal("0"), amount=Decimal("-20"), currency="EUR")
    session.add_all([vnd_trade, fee])
    await session.flush()
    assert sell.id < vnd_trade.id, "the SELL must replay before the VND trade, to close A and A2"
    return _TradeSplitSeed(
        sell=sell,
        vnd_trade=vnd_trade,
        fee=fee,
        lot_a=buy_a.id,
        lot_a2=buy_a2.id,
        vnd_lot=buy_v.id if closes_v else vnd_trade.id,
        vnd_context="CLOSURE" if closes_v else "OPENING",
        date_to=date(2025, 10, 31),
    )


_EACH_TRADE_WEIGHTED_RULE = pytest.mark.parametrize(
    ("vnd_trade_type", "fee_delay", "rule"),
    [(TransactionType.SELL, 0, "SAME_DAY_TRADES"), (TransactionType.BUY, 0, "SAME_DAY_MIXED_TRADES"), (TransactionType.BUY, 1, "PREVIOUS_DAY_TRADES")],
    ids=["same-day-trades", "same-day-mixed-trades", "previous-day-trades"],
)


@pytest.mark.asyncio
@_EACH_TRADE_WEIGHTED_RULE
async def test_a_pool_split_by_trades_in_mixed_currencies_one_without_a_rate_withholds_its_split_in_the_audit(session, test_user, asset, broker, vnd_trade_type, fee_delay, rule):
    """B3b: the audit group of the 20 EUR FEE, weighted by an EUR SELL and a VND trade without a rate.

    The FEE has its rate: its totals are known, 20 native and 20 EUR, nothing orphan. Its split between the two
    trades is not -- each weighs by its EUR value and the VND one has none (its 1000 VND, read as 1000 EUR, would
    make it 15 and 5). So every operation weight, and every lot's native and target share, is withheld. Inside
    an operation the lots share by quantity, which needs no rate: the SELL keeps A and A2 at 0.75 and 0.25. The
    lots reached have their fees withheld and their net metrics UNAVAILABLE. For each trade-weighted rule: two
    SELLs, or a SELL and a BUY, on the FEE's day, and that pair on the day before it.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_fee_split_by_two_trades(session, asset, broker, sell_currency="EUR", vnd_trade_type=vnd_trade_type, fee_delay=fee_delay)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.vnd_trade.date)
    fee_group = _group_of(result, seed.fee.id)
    reached = {seed.lot_a, seed.lot_a2, seed.vnd_lot}

    # Presence: the FEE's pool, weighted by the two trades, each reaching its lots by quantity.
    assert (fee_group.economic_type, fee_group.rule, fee_group.native_currency, fee_group.target_currency) == ("FEE", rule, "EUR", "EUR")
    lot_weights = {(operation.context, operation.operation_transaction_id): {allocation.lot_id: allocation.weight for allocation in operation.lot_allocations} for operation in fee_group.operation_allocations}
    assert lot_weights == {
        ("CLOSURE", seed.sell.id): {seed.lot_a: Decimal("0.75"), seed.lot_a2: Decimal("0.25")},
        (seed.vnd_context, seed.vnd_trade.id): {seed.vnd_lot: Decimal("1")},
    }

    # Known: what the FEE amounts to, natively and in EUR.
    assert (fee_group.native_pool_total, fee_group.target_pool_total, fee_group.native_orphan, fee_group.target_orphan) == (Decimal("20"), Decimal("20"), Decimal("0"), Decimal("0"))

    # Withheld: how it splits between the trades, and so every lot's share of it.
    assert [operation.weight for operation in fee_group.operation_allocations] == [None, None]
    assert {lot_id: (allocation.native_amount, allocation.target_amount) for lot_id, allocation in _lot_allocations(fee_group).items()} == dict.fromkeys(reached, (None, None))

    # And on the lots reached: their fees, and so their net metrics.
    assert result.lots is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    assert {lot_id: (lots[lot_id].allocated_fees, lots[lot_id].net_metrics_status) for lot_id in reached} == dict.fromkeys(reached, (None, "UNAVAILABLE"))


@pytest.mark.asyncio
@_EACH_TRADE_WEIGHTED_RULE
async def test_a_pool_split_by_trades_all_in_one_rate_less_currency_keeps_its_split_in_the_audit(session, test_user, asset, broker, vnd_trade_type, fee_delay, rule):
    """B3b guard: the same FEE and trades, with the SELL and its lots in VND as well -- every weighting trade in one
    currency, none of them with a rate.

    Their EUR values are unknown, but in one currency their ratio is exact (3000:1000), so the split is known and
    the pool is not degraded: the audit keeps each operation's weight (0.75 and 0.25) and each lot's native and
    target share -- 11.25 and 3.75 on A and A2, 5 on the VND trade's lot -- and the lots keep their fees, AVAILABLE.
    """
    await _own_missing_rate(session, "VND", "EUR")
    seed = await _seed_a_fee_split_by_two_trades(session, asset, broker, sell_currency="VND", vnd_trade_type=vnd_trade_type, fee_delay=fee_delay)

    result = await _economic_analysis(session, test_user, asset, broker, seed.date_to)

    _assert_reported_missing(result, "VND/EUR", seed.sell.date)
    fee_group = _group_of(result, seed.fee.id)
    assert (fee_group.rule, fee_group.native_pool_total, fee_group.target_pool_total) == (rule, Decimal("20"), Decimal("20"))
    shares = {seed.lot_a: Decimal("11.25"), seed.lot_a2: Decimal("3.75"), seed.vnd_lot: Decimal("5")}
    assert len(fee_group.operation_allocations) == 2
    operations = {(operation.context, operation.operation_transaction_id): (operation.weight, {allocation.lot_id: (allocation.weight, allocation.native_amount, allocation.target_amount) for allocation in operation.lot_allocations}) for operation in fee_group.operation_allocations}
    assert operations == {
        ("CLOSURE", seed.sell.id): (Decimal("0.75"), {seed.lot_a: (Decimal("0.75"), shares[seed.lot_a], shares[seed.lot_a]), seed.lot_a2: (Decimal("0.25"), shares[seed.lot_a2], shares[seed.lot_a2])}),
        (seed.vnd_context, seed.vnd_trade.id): (Decimal("0.25"), {seed.vnd_lot: (Decimal("1"), shares[seed.vnd_lot], shares[seed.vnd_lot])}),
    }
    assert result.lots is not None
    lots = {lot.lot_id: lot for lot in result.lots}
    assert {lot_id: (lots[lot_id].allocated_fees, lots[lot_id].net_metrics_status) for lot_id in shares} == {lot_id: (share, "AVAILABLE") for lot_id, share in shares.items()}


@pytest.mark.asyncio
async def test_an_orphan_income_without_a_rate_is_withheld_from_the_asset_total(session, test_user, asset, broker):
    """B3b: a 70 VND dividend, without a rate, paid after the only lot was sold: orphan income.

    How much that is in EUR is unknown, so the asset's orphan income is withheld (today the native 70
    VND, as 70 EUR), and so are the target figures of its audit group, whose native ones stay. A 5 EUR
    FEE orphaned the same day stays known: only the degraded pool's type is withheld. The lot, reached
    by neither, keeps its figures.
    """
    await _own_missing_rate(session, "VND", "EUR")
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 6, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 6, 16), quantity=Decimal("-10"), amount=Decimal("1100"), currency="EUR")
    vnd_dividend = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.DIVIDEND, date=date(2025, 7, 1), quantity=Decimal("0"), amount=Decimal("70"), currency="VND")
    eur_fee = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.FEE, date=date(2025, 7, 1), quantity=Decimal("0"), amount=Decimal("-5"), currency="EUR")
    session.add_all(
        [
            buy,
            sell,
            vnd_dividend,
            eur_fee,
            PriceHistory(asset_id=asset.id, date=buy.date, close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=sell.date, close=Decimal("110"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, vnd_dividend.date)

    _assert_reported_missing(result, "VND/EUR", vnd_dividend.date)
    income_group, fee_group = _group_of(result, vnd_dividend.id), _group_of(result, eur_fee.id)
    # Both pools are orphan: no allocation, the whole native amount left over.
    assert (income_group.operation_allocations, income_group.native_pool_total, income_group.native_orphan) == ([], Decimal("70"), Decimal("70"))
    assert (fee_group.operation_allocations, fee_group.rule, fee_group.target_orphan) == ([], "OPEN_LOTS_FALLBACK", Decimal("5"))
    assert result.lots is not None
    lot = next(row for row in result.lots if row.lot_id == buy.id)
    assert (lot.asset_income, lot.allocated_fees, lot.net_metrics_status) == (Decimal("0"), Decimal("0"), "AVAILABLE")

    # Known: the orphan FEE in EUR, and no orphan tax.
    assert (result.asset_orphan_fees, result.asset_orphan_taxes) == (Decimal("5"), Decimal("0"))

    # Withheld: the orphan income, at asset level and in its audit group.
    assert result.asset_orphan_income is None
    assert (income_group.target_pool_total, income_group.target_orphan) == (None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "amount", "currency", "code", "audit_target", "stated"),
    [
        pytest.param(TransactionType.DIVIDEND, Decimal("70"), "VND", IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS, None, (Decimal("70"), "VND"), id="dividend-without-rate"),
        pytest.param(TransactionType.FEE, Decimal("-9"), "VND", IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS, None, (Decimal("9"), "VND"), id="fee-without-rate"),
        pytest.param(TransactionType.TAX, Decimal("-12"), "VND", IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS, None, (Decimal("12"), "VND"), id="tax-without-rate"),
        pytest.param(TransactionType.DIVIDEND, Decimal("8"), "USD", IssueCode.ASSET_INCOME_NO_ELIGIBLE_LOTS, Decimal("6.4"), (Decimal("6.4"), "EUR"), id="dividend-converted"),
        pytest.param(TransactionType.FEE, Decimal("-8"), "USD", IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS, Decimal("6.4"), (Decimal("6.4"), "EUR"), id="fee-converted"),
        pytest.param(TransactionType.TAX, Decimal("-8"), "USD", IssueCode.ASSET_COST_NO_ELIGIBLE_LOTS, Decimal("6.4"), (Decimal("6.4"), "EUR"), id="tax-converted"),
    ],
)
async def test_an_orphan_pool_issue_states_its_amount_in_a_currency_it_is_known_in(session, test_user, asset, broker, event_type, amount, currency, code, audit_target, stated):
    """B3b: the data-quality issue of an orphan pool, whose banner reads "No open lot eligible for {economic_type} of
    {target_amount} {target_currency} on {as_of_date}".

    Without a rate (VND), the pool's target amount is only the native placeholder the engine was handed: stated in the
    target currency, 70 VND reads "70 EUR". The issue states it in its own currency instead -- the pool's native total
    and native currency -- which is true, and needs no new message. With a rate (USD, 1.25 per EUR, owned for the day)
    the issue keeps the converted amount in the target currency: 8 USD is 6.4 EUR. One orphan pool per case -- income
    (ASSET_INCOME_NO_ELIGIBLE_LOTS), FEE and TAX (ASSET_COST_NO_ELIGIBLE_LOTS) -- paid after the only lot was sold.
    """
    await _own_missing_rate(session, "VND", "EUR")
    orphan_date = date(2025, 7, 1)
    await _own_fx_rate(session, on=orphan_date, base="EUR", quote="USD", rate=Decimal("1.25"))
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 6, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 6, 16), quantity=Decimal("-10"), amount=Decimal("1100"), currency="EUR")
    orphan = Transaction(broker_id=broker.id, asset_id=asset.id, type=event_type, date=orphan_date, quantity=Decimal("0"), amount=amount, currency=currency)
    prices = [PriceHistory(asset_id=asset.id, date=day, close=close, currency="EUR", source_plugin_key="TEST") for day, close in ((buy.date, Decimal("100")), (sell.date, Decimal("110")))]
    session.add_all([buy, sell, orphan, *prices])
    await session.flush()

    result = await _economic_analysis(session, test_user, asset, broker, orphan_date)

    # Presence: the pool is orphan, natively the event's amount, and its target total known exactly when the rate is.
    group = _group_of(result, orphan.id)
    assert (group.operation_allocations, group.native_currency, group.native_pool_total, group.target_pool_total) == ([], currency, abs(amount), audit_target)

    # Its issue, found by its code and its source transaction.
    assert result.data_quality is not None
    issues = [issue for issue in result.data_quality.issues if issue.code == code and issue.message_params.get("transaction_id") == orphan.id]
    assert len(issues) == 1, f"issues={result.data_quality.issues}"
    params = issues[0].message_params
    assert (params["economic_type"], params["as_of_date"], params["target_amount"], params["target_currency"]) == (event_type.value, orphan_date.isoformat(), *stated)


# --------------------------------------------------------------------------- #
# CP-7a — developer's decision 26 (D-J1, option B): a lot realizes what the Dashboard realizes
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_foreign_lot_sold_whole_realizes_what_the_dashboard_realizes(session, test_user, broker):
    """R7: a USD asset, report EUR; 10 bought for 1000 USD on 2 Jan (0.8 EUR a dollar), all sold for 1100 USD on 2 Jun (0.78125).

    Each leg at its own date, as the Dashboard's average cost already does: 1100 × 0.78125 − 1000 × 0.8 = 859.375 − 800 =
    59.375 EUR, for the lot (LOT_SUMMARY) and for the Dashboard's position (get_positions_contribution) alike. Before CP-7a
    the lot realized its native gain at the sale's rate, 100 × 0.78125 = 78.125, against the Dashboard's 59.375.

    The rates are owned for both days (_own_fx_rate, 1.25 and 1.28 USD a euro: exact inverses), the asset and its prices are
    this test's own, and the session fixture rolls everything back.
    """
    stamp = str(utcnow().timestamp()).replace(".", "")
    usd_asset = Asset(display_name=f"LotsParity_{stamp}", identifier_ticker=f"LPAR{stamp[-4:]}", currency="USD", asset_type=AssetType.STOCK)
    session.add(usd_asset)
    await session.flush()
    purchase_day, sale_day = date(2025, 1, 2), date(2025, 6, 2)
    await _own_fx_rate(session, on=purchase_day, base="EUR", quote="USD", rate=Decimal("1.25"))
    await _own_fx_rate(session, on=sale_day, base="EUR", quote="USD", rate=Decimal("1.28"))
    buy = Transaction(broker_id=broker.id, asset_id=usd_asset.id, type=TransactionType.BUY, date=purchase_day, quantity=Decimal("10"), amount=Decimal("-1000"), currency="USD")
    sell = Transaction(broker_id=broker.id, asset_id=usd_asset.id, type=TransactionType.SELL, date=sale_day, quantity=Decimal("-10"), amount=Decimal("1100"), currency="USD")
    session.add_all(
        [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=purchase_day, amount=Decimal("1000"), currency="USD"),
            buy,
            sell,
            PriceHistory(asset_id=usd_asset.id, date=purchase_day, close=Decimal("100"), currency="USD", source_plugin_key="TEST"),
            PriceHistory(asset_id=usd_asset.id, date=sale_day, close=Decimal("110"), currency="USD", source_plugin_key="TEST"),
        ]
    )
    await session.flush()

    lots = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=usd_asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=sale_day,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )
    contribution = await PortfolioService(session).get_positions_contribution(user_id=test_user.id, broker_ids=[broker.id], date_from=None, date_to=sale_day, target_currency_override="EUR")

    lot_realized = [lot.realized_pnl for lot in lots.lots or [] if lot.lot_id == buy.id]
    dashboard_realized = [row.period_realized_gain_loss for row in contribution.positions if row.asset_id == usd_asset.id and row.broker_id == broker.id]
    assert {"lot": lot_realized, "dashboard": dashboard_realized} == {"lot": [Decimal("59.375")], "dashboard": [Decimal("59.375")]}


# --------------------------------------------------------------------------- #
# CP-7b — the lots read their prices from the asset's daily price series (V1, with J-28)
# --------------------------------------------------------------------------- #
#
# The developer's decisions P2/J-17 («trades are prices, an adjustment isn't») and P21 («every amount at the rate of its
# day»), then option (a) of the CP-7b amendment («the Dashboard's per-day rule in the lots too: one rule in the whole
# app»), through the real service and database. The lots read the asset's daily price series (financial_math.
# price_marks): the last close, or BUY/SELL price, on or before a day, carried forward — never an ADJUSTMENT.
#
# * A lot opened by an ADJUSTMENT takes the opening day's mark as its reference — a BUY's price too — converted at the
#   opening day's rate. Before CP-7b: the last stored close however old, converted at that close's own day.
# * An open LONG lot of known cost is valued at cost on the days with no observation on or before them — the run before
#   the asset's first close, BUY or SELL — and CURRENT_PRICE_ASSUMED_AT_COST names that range: from the first
#   transaction to the day before the first observation, or to the analysis end when there is none. Before CP-7b: at
#   cost only when the asset had no close at all (then every unpriced day), and the warning raised on that alone, so an
#   asset priced by its trades was told its price was assumed at cost (J-28).
#
# Every test owns its user, broker and asset (the fixtures, or an asset of its own) and the EUR/USD rates it reads
# (_own_fx_rate); the session fixture rolls everything back. GUARD marks a value CP-7b leaves as it was.


def _at_cost_warnings(result) -> list[dict]:
    """The lots' CURRENT_PRICE_ASSUMED_AT_COST issues, each as its message key and its parameters: the range it names."""
    assert result.data_quality is not None
    return [{"key": issue.message_i18n_key, **issue.message_params} for issue in result.data_quality.issues if issue.code == IssueCode.CURRENT_PRICE_ASSUMED_AT_COST]


def _at_cost_warning(asset: Asset, date_from: date, date_to: date) -> dict:
    """The at-cost warning of ``asset`` over [date_from, date_to], as _at_cost_warnings reads it."""
    return {"key": "dataQuality.currentPriceAssumedAtCostRange", "asset_id": asset.id, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()}


def _value_points_of(result, lot_id: int) -> dict[date, tuple[Decimal, Decimal]]:
    """A lot's value history as {date: (open value, P&L)}, the lot found by its id."""
    assert result.value_history is not None
    return {point.date: (point.open_value, point.pnl) for point in daily_points(result.value_history) if point.lot_id == lot_id}


async def _assert_never_quoted(session, asset: Asset) -> None:
    """Precondition: no close is stored for the asset, so whatever prices it below is a trade, or nothing."""
    closes = (await session.execute(select(PriceHistory.id).where(PriceHistory.asset_id == asset.id))).all()
    assert closes == [], f"precondition broken: {len(closes)} close(s) stored for this test's own asset"


def _received_at_20(broker: Broker, asset: Asset, day: date) -> Transaction:
    """10 units received by an ADJUSTMENT at a cost basis of 20 EUR a unit — an inherited position, 200 EUR of cost."""
    return Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=day,
        quantity=Decimal("10"),
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=Decimal("20"),
        cost_basis_currency="EUR",
    )


@pytest.mark.asyncio
async def test_an_asset_priced_by_its_trades_alone_raises_no_at_cost_warning(session, test_user, asset, broker):
    """(g) J-28: never quoted, bought (10 for 1000 EUR on 1 Apr) and sold (4 for 520 EUR on 15 Apr), read on 20 Apr.

    The BUY prices the lot from its first day, the SELL from the 15th: no day is at cost, so no CURRENT_PRICE_ASSUMED_AT_COST,
    and the lot is at the SELL's 130 carried forward — MARKET_PRICE, 6 × 130 = 780. Before CP-7b: the same lot, but the
    warning raised over 1–20 Apr, because the asset had no close.
    """
    await _assert_never_quoted(session, asset)
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 4, 1), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2025, 4, 15), quantity=Decimal("-4"), amount=Decimal("520"), currency="EUR")
    session.add_all([buy, sell])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 4, 20),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    lots = [(lot.value_source, lot.open_quantity, lot.open_value) for lot in result.lots or [] if lot.opening_transaction_id == buy.id]
    assert {"at-cost warnings": _at_cost_warnings(result), "the BUY's lot": lots} == {
        "at-cost warnings": [],
        "the BUY's lot": [("MARKET_PRICE", Decimal("6"), Decimal("780"))],
    }


@pytest.mark.asyncio
async def test_an_asset_with_adjustments_alone_is_at_cost_over_the_whole_window_and_says_so(session, test_user, asset, broker):
    """(h) GUARD: never quoted, bought or sold, only received — 10 by an ADJUSTMENT at 20 EUR a unit on 2 May — read on 10 May.

    No day has an observation, so the whole window is at cost: one CURRENT_PRICE_ASSUMED_AT_COST over [the first
    transaction, the analysis end] = [2 May, 10 May], and the lot ESTIMATED_AT_COST at its cost, 200, market P&L 0.
    The same before CP-7b, where this was the only case at cost.
    """
    await _assert_never_quoted(session, asset)
    adjustment = _received_at_20(broker, asset, date(2025, 5, 2))
    session.add(adjustment)
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 5, 10),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    lots = [(lot.value_source, lot.open_value, lot.market_pnl) for lot in result.lots or [] if lot.opening_transaction_id == adjustment.id]
    assert {"at-cost warnings": _at_cost_warnings(result), "the ADJUSTMENT's lot": lots} == {
        "at-cost warnings": [_at_cost_warning(asset, date(2025, 5, 2), date(2025, 5, 10))],
        "the ADJUSTMENT's lot": [("ESTIMATED_AT_COST", Decimal("200"), Decimal("0"))],
    }


@pytest.mark.asyncio
async def test_a_lot_opened_by_an_adjustment_after_a_newer_buy_takes_the_buys_price_as_reference(session, test_user, asset, broker):
    """(i) X closed at 100 EUR on 2 Jun, 10 were bought at 120 EUR on 5 Jun, 5 received by an ADJUSTMENT at 90 EUR a unit on 9 Jun, read that day.

    On 9 Jun the newest observation is the BUY: the ADJUSTMENT's lot is referenced to 120, ``fallback`` (no close that
    day), and its relative return is 120 / 120 − 1 = 0. GUARD: the BUY's lot keeps its own price, 120, ``exact``.
    Before CP-7b: 100, the close of 2 Jun, still ``fallback``, and a relative return of +20 %.
    """
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 6, 5), quantity=Decimal("10"), amount=Decimal("-1200"), currency="EUR")
    adjustment = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=date(2025, 6, 9),
        quantity=Decimal("5"),
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=Decimal("90"),
        cost_basis_currency="EUR",
    )
    session.add_all([buy, adjustment, PriceHistory(asset_id=asset.id, date=date(2025, 6, 2), close=Decimal("100"), currency="EUR", source_plugin_key="TEST")])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 6, 9),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    lots = {lot.opening_transaction_id: lot for lot in result.lots or []}
    assert set(lots) == {buy.id, adjustment.id}, f"precondition: the BUY and the ADJUSTMENT open one lot each, got {result.lots}"
    observed = {
        "the ADJUSTMENT's lot": (lots[adjustment.id].reference_unit_price, lots[adjustment.id].reference_price_source, lots[adjustment.id].relative_return),
        "the BUY's lot": (lots[buy.id].reference_unit_price, lots[buy.id].reference_price_source),
    }
    assert observed == {
        "the ADJUSTMENT's lot": (Decimal("120"), "fallback", Decimal("0")),
        "the BUY's lot": (Decimal("120"), "exact"),
    }


@pytest.mark.asyncio
async def test_a_foreign_reference_carried_from_an_older_close_converts_at_the_opening_days_rate(session, test_user, broker):
    """(j) A USD asset, report EUR: closed at 64 USD on 2 Jul; 10 received by an ADJUSTMENT at 50 USD a unit on 7 Jul, five days later; read that day.

    The reference is that close carried forward, 64 USD, ``fallback``. It stands for 7 Jul and converts at that day's rate,
    1.28 USD a euro: 64 × 0.78125 = 50 EUR. The lot's current price is the same mark at the same rate, so its relative
    return is 0. Before CP-7b it converted at the close's day, 2 Jul, 1.25 USD a euro: 64 × 0.8 = 51.2 EUR, and a relative
    return of 50 / 51.2 − 1 = −0.0234375 — the exchange rate's move read as the asset's.

    The rates are owned for both days (_own_fx_rate, 1.25 and 1.28 USD a euro: exact inverses), the asset is this test's own.
    """
    marker = uuid4().hex
    usd_asset = Asset(display_name=f"LotsRefFx_{marker}", identifier_ticker=f"LRFX{marker[:4]}", currency="USD", asset_type=AssetType.STOCK)
    session.add(usd_asset)
    await session.flush()
    close_day, opening_day = date(2025, 7, 2), date(2025, 7, 7)
    await _own_fx_rate(session, on=close_day, base="EUR", quote="USD", rate=Decimal("1.25"))
    await _own_fx_rate(session, on=opening_day, base="EUR", quote="USD", rate=Decimal("1.28"))
    adjustment = Transaction(
        broker_id=broker.id,
        asset_id=usd_asset.id,
        type=TransactionType.ADJUSTMENT,
        date=opening_day,
        quantity=Decimal("10"),
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=Decimal("50"),
        cost_basis_currency="USD",
    )
    session.add_all([adjustment, PriceHistory(asset_id=usd_asset.id, date=close_day, close=Decimal("64"), currency="USD", source_plugin_key="TEST")])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=usd_asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=opening_day,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY"],
    )

    assert result.data_quality is not None and result.data_quality.missing_fx_pairs == [], f"precondition: both rates are this test's own, got {result.data_quality}"
    lots = [(lot.reference_unit_price, lot.reference_price_source, lot.relative_return) for lot in result.lots or [] if lot.opening_transaction_id == adjustment.id]
    assert lots == [(Decimal("50"), "fallback", Decimal("0"))]


@pytest.mark.asyncio
async def test_an_adjustment_before_the_first_quote_is_at_cost_until_that_quote(session, test_user, asset, broker):
    """(k) Received by an ADJUSTMENT-in (10 at 20 EUR a unit) on 10 Jan, first quoted on 15 Jan (25 EUR), read on 20 Jan.

    10–14 Jan have no observation on or before them: the lot is at its cost, 200, P&L 0, as the Dashboard values the
    holding (J-17); from 15 Jan it is worth 10 × 25 = 250, P&L 50. One CURRENT_PRICE_ASSUMED_AT_COST names 10–14 Jan,
    and the summary, read on 20 Jan, is at the market: MARKET_PRICE, 250 (GUARD).

    Before CP-7b (J-17's rule, at cost only an asset with no close at all): no point on 10–14 Jan and no warning, which
    test_adjustment_before_the_first_quote_has_no_value_point pinned; this test replaces it.
    """
    adjustment = _received_at_20(broker, asset, date(2025, 1, 10))
    session.add_all([adjustment, PriceHistory(asset_id=asset.id, date=date(2025, 1, 15), close=Decimal("25"), currency="EUR", source_plugin_key="TEST")])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 1, 20),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY"],
    )

    at_cost, priced = _days_between(date(2025, 1, 10), date(2025, 1, 14)), _days_between(date(2025, 1, 15), date(2025, 1, 20))
    summary = [(lot.value_source, lot.open_value) for lot in result.lots or [] if lot.opening_transaction_id == adjustment.id]
    observed = {"value history": _value_points_of(result, adjustment.id), "at-cost warnings": _at_cost_warnings(result), "summary": summary}
    assert observed == {
        "value history": {**dict.fromkeys(at_cost, (Decimal("200"), Decimal("0"))), **dict.fromkeys(priced, (Decimal("250"), Decimal("50")))},
        "at-cost warnings": [_at_cost_warning(asset, date(2025, 1, 10), date(2025, 1, 14))],
        "summary": [("MARKET_PRICE", Decimal("250"))],
    }


@pytest.mark.asyncio
async def test_an_adjustment_before_the_first_buy_is_at_cost_until_that_buy(session, test_user, asset, broker):
    """(l) Never quoted: received by an ADJUSTMENT-in (10 at 20 EUR a unit) on 1 Sep, then 5 bought at 30 EUR on 6 Sep, read on 8 Sep.

    1–5 Sep have no observation on or before them: the ADJUSTMENT's lot is at its cost, 200, P&L 0; from 6 Sep the BUY's
    30 prices it, 10 × 30 = 300, P&L 100. The warning names 1–5 Sep, and both lots' summaries are at the market.
    Before CP-7b the values were the same (the asset had no close, so every unpriced day was at cost), but the warning
    named the whole window, 1–8 Sep, although the BUY priced the lots from 6 Sep.
    """
    await _assert_never_quoted(session, asset)
    adjustment = _received_at_20(broker, asset, date(2025, 9, 1))
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2025, 9, 6), quantity=Decimal("5"), amount=Decimal("-150"), currency="EUR")
    session.add_all([adjustment, buy])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2025, 9, 8),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "VALUE_HISTORY"],
    )

    at_cost, priced = _days_between(date(2025, 9, 1), date(2025, 9, 5)), _days_between(date(2025, 9, 6), date(2025, 9, 8))
    summaries = {lot.opening_transaction_id: (lot.value_source, lot.open_value) for lot in result.lots or []}
    observed = {"the ADJUSTMENT's value history": _value_points_of(result, adjustment.id), "at-cost warnings": _at_cost_warnings(result), "summaries": summaries}
    assert observed == {
        "the ADJUSTMENT's value history": {**dict.fromkeys(at_cost, (Decimal("200"), Decimal("0"))), **dict.fromkeys(priced, (Decimal("300"), Decimal("100")))},
        "at-cost warnings": [_at_cost_warning(asset, date(2025, 9, 1), date(2025, 9, 5))],
        "summaries": {adjustment.id: ("MARKET_PRICE", Decimal("300")), buy.id: ("MARKET_PRICE", Decimal("150"))},
    }


# --------------------------------------------------------------------------- #
# MF-E1 (V11) — an opening event states the lot's opening value
# --------------------------------------------------------------------------- #
#
# ``LotTimelineEventSchema.opening_value``: on a BUY and an ADJUSTMENT_IN event — the two that open a lot — the lot's
# original cost converted to the analysis currency at the opening date: the very figure of that lot's
# ``LotSummarySchema.original_cost``, in the currency of the event's ``unit_price``. None on every other kind (SELL,
# SPLIT, TRANSFER_*), and None when the opening's conversion is missing. Before MF-E1 the schema has no such field.
#
# Every test owns its user, broker(s) and asset (the fixtures, or an asset of its own), and the rates it reads, in
# 2048, a year no other test writes (_own_fx_rate); the session fixture rolls everything back.


def _assert_the_event_schema_has_an_opening_value() -> None:
    assert "opening_value" in LotTimelineEventSchema.model_fields, "LotTimelineEventSchema has no opening_value field (MF-E1, V11)"


@pytest.mark.asyncio
async def test_an_opening_event_states_its_lots_original_cost_in_the_analysis_currency(session, test_user, asset, broker):
    """(V11) An EUR asset analysed in EUR, three lots opened three ways, then a SELL, a 2:1 SPLIT and a TRANSFER:

    * 2 Mar 2048, BUY 10 for 1 000 EUR — original cost 1 000 EUR;
    * 3 Mar, BUY 4 for 500 USD at 1.25 USD a euro — 400 EUR;
    * 4 Mar, ADJUSTMENT-in 5 at a cost basis of 30 USD a unit, at 1.6 USD a euro — 150 USD, 93.75 EUR;
    * 5 Mar, SELL 3 of the first lot; 7 Mar, SPLIT 2:1; 8→9 Mar, TRANSFER of 4 to a second broker; read on 10 Mar.

    Each opening event's ``opening_value`` is its lot's ``original_cost``: converted at the opening date (two different
    rates), and in the currency of the event's ``unit_price`` — quantity × unit price, no fees. The SELL, SPLIT and
    TRANSFER events have none. Before MF-E1: no ``opening_value`` on the event schema at all.
    """
    _assert_the_event_schema_has_an_opening_value()
    broker_b = Broker(name=f"LotsBrokerB_{uuid4().hex}")
    session.add(broker_b)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker_b.id, user_id=test_user.id, role="OWNER", share_percentage=Decimal("1")))
    await session.flush()
    await _own_fx_rate(session, on=date(2048, 3, 3), base="EUR", quote="USD", rate=Decimal("1.25"))
    await _own_fx_rate(session, on=date(2048, 3, 4), base="EUR", quote="USD", rate=Decimal("1.6"))
    split_event = AssetEvent(asset_id=asset.id, date=date(2048, 3, 7), type=AssetEventType.SPLIT, value=Decimal("2"), currency="EUR")
    session.add(split_event)
    await session.flush()

    buy_eur = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2048, 3, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR")
    buy_usd = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=date(2048, 3, 3), quantity=Decimal("4"), amount=Decimal("-500"), currency="USD")
    received = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=date(2048, 3, 4),
        quantity=Decimal("5"),
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=Decimal("30"),
        cost_basis_currency="USD",
    )
    sell = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=date(2048, 3, 5), quantity=Decimal("-3"), amount=Decimal("390"), currency="EUR")
    # 16 held at the split (7 + 4 + 5): the 2:1 split adds 16.
    split = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=date(2048, 3, 7),
        quantity=Decimal("16"),
        amount=Decimal("0"),
        currency="EUR",
        asset_event_id=split_event.id,
    )
    transfer_out = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=date(2048, 3, 8), quantity=Decimal("-4"), amount=Decimal("0"), currency="EUR")
    transfer_in = Transaction(broker_id=broker_b.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=date(2048, 3, 9), quantity=Decimal("4"), amount=Decimal("0"), currency="EUR")
    session.add_all(
        [
            buy_eur,
            buy_usd,
            received,
            sell,
            split,
            transfer_out,
            transfer_in,
            PriceHistory(asset_id=asset.id, date=date(2048, 3, 2), close=Decimal("100"), currency="EUR", source_plugin_key="TEST"),
            PriceHistory(asset_id=asset.id, date=date(2048, 3, 10), close=Decimal("60"), currency="EUR", source_plugin_key="TEST"),
        ]
    )
    await session.flush()
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=asset.id,
        broker_ids=[broker.id, broker_b.id],
        date_from=None,
        date_to=date(2048, 3, 10),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "EVENT_HISTORY"],
    )

    # Precondition: the three lots, each cost converted at its own opening date (GUARD: the summary as before MF-E1).
    original_costs = {lot.lot_id: lot.original_cost for lot in result.lots or []}
    assert original_costs == {buy_eur.id: Decimal("1000"), buy_usd.id: Decimal("400"), received.id: Decimal("93.75")}, f"precondition: three lots of known cost, got {result.lots}"
    assert result.lot_events is not None
    events_by_kind: dict[str, list[LotTimelineEventSchema]] = {}
    for row in result.lot_events:
        events_by_kind.setdefault(str(row.kind), []).append(row)
    # Presence first: every kind this ledger produces is there, so the Nones below are about rows that exist.
    assert set(events_by_kind) == {"BUY", "ADJUSTMENT_IN", "SELL", "SPLIT", "TRANSFER_DEPART", "TRANSFER_ARRIVE"}, f"precondition: the ledger's event kinds, got {sorted(events_by_kind)}"

    openings = {row.lot_id: (str(row.kind), row.opening_value) for row in events_by_kind["BUY"] + events_by_kind["ADJUSTMENT_IN"]}
    assert openings == {
        buy_eur.id: ("BUY", Decimal("1000")),
        buy_usd.id: ("BUY", Decimal("400")),
        received.id: ("ADJUSTMENT_IN", Decimal("93.75")),
    }
    assert {lot_id: opening_value for lot_id, (_kind, opening_value) in openings.items()} == original_costs
    # The currency of the event's unit price: quantity × unit price, a BUY without fees and a priced ADJUSTMENT.
    assert {row.lot_id: row.quantity * row.unit_price for row in events_by_kind["BUY"] + events_by_kind["ADJUSTMENT_IN"]} == original_costs

    others = [(str(row.kind), row.lot_id, row.opening_value) for kind in ("SELL", "SPLIT", "TRANSFER_DEPART", "TRANSFER_ARRIVE") for row in events_by_kind[kind]]
    assert [(kind, lot_id) for kind, lot_id, opening_value in others if opening_value is not None] == []


@pytest.mark.asyncio
async def test_an_opening_event_has_no_opening_value_when_its_conversion_is_missing(session, test_user, broker):
    """(V11) A VND asset bought in VND on 9 Jun 2048, analysed in EUR with no VND/EUR rate or route.

    The lot's original cost is unknown in EUR (B3a), and so is its opening event's ``opening_value``: None, never the
    native 2 500 000 VND. The absence of the pair is owned as in B3a's test: ``fx_rates`` and ``fx_conversion_routes``
    are emptied for EUR/VND inside this test's transaction, which the ``session`` fixture rolls back.
    Before MF-E1: no ``opening_value`` on the event schema at all.
    """
    _assert_the_event_schema_has_an_opening_value()
    marker = uuid4().hex
    vnd_asset = Asset(display_name=f"LotsOpeningVND_{marker}", identifier_ticker=f"LOVN{marker[:4]}", currency="VND", asset_type=AssetType.STOCK)
    session.add(vnd_asset)
    await session.flush()
    base, quote = sorted(("VND", "EUR"))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
    buy = Transaction(broker_id=broker.id, asset_id=vnd_asset.id, type=TransactionType.BUY, date=date(2048, 6, 9), quantity=Decimal("100"), amount=Decimal("-2500000"), currency="VND")
    session.add_all([buy, PriceHistory(asset_id=vnd_asset.id, date=date(2048, 6, 9), close=Decimal("25000"), currency="VND", source_plugin_key="TEST")])
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=test_user.id,
        asset_id=vnd_asset.id,
        broker_ids=[broker.id],
        date_from=None,
        date_to=date(2048, 6, 10),
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["LOT_SUMMARY", "EVENT_HISTORY"],
    )

    # Precondition: the BUY opened the only lot, of unknown cost in EUR.
    assert [(lot.lot_id, lot.original_cost) for lot in result.lots or []] == [(buy.id, None)], f"precondition: one lot of unknown EUR cost, got {result.lots}"
    openings = [(row.lot_id, row.opening_value) for row in result.lot_events or [] if row.kind == "BUY"]
    assert openings == [(buy.id, None)]

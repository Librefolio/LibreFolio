"""J5-1 (#48) — ``PortfolioService.get_positions_series``: the daily series of the chosen positions, read from the engine.

The pure side (``financial_math/portfolio/position_series.py``) is pinned in ``test_financial_math/test_position_series.py``;
this file pins the reading: the engine run with the position frames (``include_positions``), the cash flows by day, the
realized sales, the internal transfers and the cost of what was bought, handed to it, and the schema it answers.

What is pinned, on ledgers written straight into the session (rolled back; each test owns its user, brokers and assets):

* **P1** — the last point of a series is the Performance table's row: ``pnl`` equals the ``period_pnl`` of
  ``get_positions_contribution`` for the same position and the same dates, to the digit, on a ledger with a purchase, a partial
  sale, a dividend and a fee;
* **P2** — with every position chosen, the ``market_value`` of the series on each day adds up to the report's
  ``market_value`` of that day;
* only the **asked** positions come back, in the order asked; ``broker_id`` None sums the brokers of the asset; a position
  never held has no points; a position sold out ends the day it went to 0;
* a position of a broker the user cannot read comes back empty, never its figures.

EUR everywhere: no rate is needed. Dates in 2024, with prices stored for every day the engine marks.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery, PositionKey, PositionsSeriesQuery
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
FROM = date(2024, 1, 1)
TO = date(2024, 3, 31)
D = Decimal


# =============================================================================
# Ledgers
# =============================================================================


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


async def _user(session: AsyncSession, keep_alive: list[object], label: str, *, brokers: int = 1) -> tuple[User, list[Broker]]:
    tag = uuid4().hex[:12]
    user = User(username=f"ps_{label}_{tag}", email=f"ps_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    rows = [Broker(name=f"Ps {label} {index} {tag}") for index in range(brokers)]
    await _persist(session, keep_alive, user, *rows)
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")) for broker in rows))
    return user, rows


async def _asset(session: AsyncSession, keep_alive: list[object], label: str) -> Asset:
    asset = Asset(display_name=f"Ps {label} {uuid4().hex[:8]}", currency=EUR, asset_type=AssetType.STOCK)
    await _persist(session, keep_alive, asset)
    return asset


def _prices(asset: Asset, first: date, last: date, *, start: str, step: str) -> list[PriceHistory]:
    rows = []
    for index in range((last - first).days + 1):
        price = D(start) + D(step) * index
        rows.append(PriceHistory(asset_id=asset.id, date=first + timedelta(days=index), open=price, high=price, low=price, close=price, volume=D("1"), currency=EUR, source_plugin_key="ps_test"))
    return rows


def _tx(broker: Broker, asset: Asset | None, kind: TransactionType, on: date, quantity: str, amount: str) -> Transaction:
    return Transaction(broker_id=broker.id, asset_id=None if asset is None else asset.id, type=kind, date=on, quantity=D(quantity), amount=D(amount), currency=EUR)


async def _ledger(session: AsyncSession, keep_alive: list[object], label: str):
    """Two assets at one broker: A bought 10 on 10 Jan (cost 1 000), 4 sold on 20 Feb, a dividend on 1 Mar and a fee on 5 Mar; B bought 5 on 15 Jan (cost 500)."""
    user, [broker] = await _user(session, keep_alive, label)
    a, b = await _asset(session, keep_alive, f"{label}A"), await _asset(session, keep_alive, f"{label}B")
    await _persist(
        session,
        keep_alive,
        _tx(broker, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        _tx(broker, a, TransactionType.BUY, date(2024, 1, 10), "10", "-1000"),
        _tx(broker, b, TransactionType.BUY, date(2024, 1, 15), "5", "-500"),
        _tx(broker, a, TransactionType.SELL, date(2024, 2, 20), "-4", "520"),
        _tx(broker, a, TransactionType.DIVIDEND, date(2024, 3, 1), "0", "30"),
        _tx(broker, a, TransactionType.FEE, date(2024, 3, 5), "0", "-2"),
        *_prices(a, date(2024, 1, 1), TO, start="100", step="0.5"),
        *_prices(b, date(2024, 1, 1), TO, start="100", step="-0.25"),
    )
    return user, broker, a, b


def _query(positions: list[tuple[int | None, int]], *, broker_ids: list[int] | None = None, date_from: date = FROM, date_to: date = TO) -> PositionsSeriesQuery:
    return PositionsSeriesQuery(broker_ids=broker_ids, date_range=OpenDateRangeModel(start=date_from, end=date_to), target_currency=EUR, positions=[PositionKey(broker_id=broker, asset_id=asset) for broker, asset in positions])


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.fixture
def keep_alive() -> list[object]:
    return []


@pytest.fixture(autouse=True)
def clean_portfolio_caches(request):
    for cache in (portfolio_service_module._portfolio_l2_cache, portfolio_service_module._wac_cache, portfolio_engine_module._portfolio_blob_cache):
        cache.clear()
    request.addfinalizer(lambda: [cache.clear() for cache in (portfolio_service_module._portfolio_l2_cache, portfolio_service_module._wac_cache, portfolio_engine_module._portfolio_blob_cache)])


# =============================================================================
# P1 — the last point is the Performance table's row
# =============================================================================


@pytest.mark.asyncio
async def test_p1_the_last_point_is_the_periodo_rows_pnl(session, keep_alive):
    user, broker, a, b = await _ledger(session, keep_alive, "p1")
    service = PortfolioService(session)

    response = await service.get_positions_series(user_id=user.id, query=_query([(broker.id, a.id), (broker.id, b.id)]))
    contribution = await service.get_positions_contribution(user_id=user.id, target_currency_override=EUR, date_from=FROM, date_to=TO)

    rows = {(row.broker_id, row.asset_id): row for row in contribution.positions}
    for series in response.series:
        row = rows[(series.key.broker_id, series.key.asset_id)]
        assert series.points[-1].date == TO
        assert series.points[-1].pnl == row.period_pnl, f"asset {series.key.asset_id}: the series ends where the table's row does"
    assert {s.key.asset_id for s in response.series} == {a.id, b.id}


@pytest.mark.asyncio
async def test_p1_a_series_counts_the_realized_gain_the_dividend_and_the_fee(session, keep_alive):
    """Asset A is quoted 100 + 0.5 a day from 1 Jan (so 125 on 20 Feb, 129.5 on 29 Feb, 130 on 1 Mar, 131.5 on 4 Mar, 132 on 5 Mar), bought
    10 for 1 000 (cost 100 a unit), 4 sold for 520 on 20 Feb (realized 520 - 400 = 120). The 6 left are worth 6 x price: the unrealized
    result is 6 x (price - 100). The dividend of 30 enters on 1 Mar, the fee of 2 on 5 Mar."""
    user, broker, a, _ = await _ledger(session, keep_alive, "p1parts")

    [series] = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(broker.id, a.id)]))).series

    points = {p.date: p for p in series.points}
    assert points[date(2024, 2, 19)].pnl == D("10") * (D("124.5") - D("100"))
    assert points[date(2024, 2, 20)].pnl == D("6") * (D("125") - D("100")) + D("120")
    assert points[date(2024, 2, 29)].pnl == D("6") * (D("129.5") - D("100")) + D("120")
    assert points[date(2024, 3, 1)].pnl == D("6") * (D("130") - D("100")) + D("120") + D("30")
    assert points[date(2024, 3, 4)].pnl == D("6") * (D("131.5") - D("100")) + D("120") + D("30")
    assert points[date(2024, 3, 5)].pnl == D("6") * (D("132") - D("100")) + D("120") + D("30") - D("2")


# =============================================================================
# P2 — the market values add up to the report's
# =============================================================================


@pytest.mark.asyncio
async def test_p2_with_every_position_chosen_the_market_values_add_up_to_the_reports(session, keep_alive):
    user, broker, a, b = await _ledger(session, keep_alive, "p2")
    service = PortfolioService(session)

    response = await service.get_positions_series(user_id=user.id, query=_query([(broker.id, a.id), (broker.id, b.id)]))
    report = await service.get_report(user_id=user.id, query=PortfolioReportQuery(date_range=OpenDateRangeModel(start=FROM, end=TO), target_currency=EUR, include_summary=False, include_allocation_history=False))

    by_day: dict[date, Decimal] = {}
    for series in response.series:
        for point in series.points:
            by_day[point.date] = by_day.get(point.date, D("0")) + (point.market_value or D("0"))
    checked = 0
    for point in report.history or []:
        if point.date in by_day and point.date >= date(2024, 1, 16):
            assert by_day[point.date] == point.market_value.amount, point.date
            checked += 1
    assert checked > 60, "the comparison covers the days both positions are held"


# =============================================================================
# The selection
# =============================================================================


@pytest.mark.asyncio
async def test_only_the_asked_positions_come_back_in_the_order_asked(session, keep_alive):
    user, broker, a, b = await _ledger(session, keep_alive, "sel")

    response = await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(broker.id, b.id)]))

    assert [(s.key.broker_id, s.key.asset_id) for s in response.series] == [(broker.id, b.id)]
    assert response.currency == EUR and (response.date_from, response.date_to) == (FROM, TO)


@pytest.mark.asyncio
async def test_an_asset_with_no_broker_sums_the_brokers_that_hold_it(session, keep_alive):
    user, [first, second] = await _user(session, keep_alive, "two", brokers=2)
    asset = await _asset(session, keep_alive, "twoA")
    await _persist(
        session,
        keep_alive,
        _tx(first, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        _tx(second, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        _tx(first, asset, TransactionType.BUY, date(2024, 1, 10), "10", "-1000"),
        _tx(second, asset, TransactionType.BUY, date(2024, 1, 12), "4", "-400"),
        *_prices(asset, date(2024, 1, 1), TO, start="100", step="0.5"),
    )
    service = PortfolioService(session)

    summed, one, other = (await service.get_positions_series(user_id=user.id, query=_query([(None, asset.id), (first.id, asset.id), (second.id, asset.id)]))).series

    day = date(2024, 2, 1)
    at = lambda series: next(point for point in series.points if point.date == day)  # noqa: E731
    assert at(summed).quantity == at(one).quantity + at(other).quantity == D("14")
    assert at(summed).market_value == at(one).market_value + at(other).market_value
    assert at(summed).pnl == at(one).pnl + at(other).pnl


@pytest.mark.asyncio
async def test_a_position_never_held_has_no_points_and_a_sold_out_one_ends_when_it_closed(session, keep_alive):
    user, broker, a, _ = await _ledger(session, keep_alive, "closed")
    other = await _asset(session, keep_alive, "closedX")
    await _persist(session, keep_alive, _tx(broker, a, TransactionType.SELL, date(2024, 3, 10), "-6", "700"))

    sold, never = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(broker.id, a.id), (broker.id, other.id)]))).series

    assert never.points == [] and never.first_date is None
    assert (sold.closed_on, sold.last_date, sold.held_at_end) == (date(2024, 3, 10), date(2024, 3, 10), False)
    assert (sold.points[-1].quantity, sold.points[-1].market_value) == (D("0"), D("0"))


@pytest.mark.asyncio
async def test_a_broker_the_user_cannot_read_comes_back_empty(session, keep_alive):
    user, _, a, _ = await _ledger(session, keep_alive, "mine")
    stranger, [theirs] = await _user(session, keep_alive, "theirs")
    await _persist(session, keep_alive, _tx(theirs, a, TransactionType.BUY, date(2024, 1, 10), "3", "-300"))

    [series] = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(theirs.id, a.id)]))).series

    assert series.points == [] and stranger.id != user.id


# =============================================================================
# P4 — a transfer between two brokers, bought in two goes, a split
# =============================================================================


@pytest.mark.asyncio
async def test_p4_a_transfer_between_two_brokers_leaves_no_jump_and_each_last_point_is_its_row(session, keep_alive):
    """10 bought at broker 1 on 10 Jan for 1 000, sent on 5 Feb, arriving at broker 2 on 7 Feb (cost basis 100 a unit); the price lifts by half a euro a day.
    Each broker answers for its tract (P22); the asset summed over both goes smoothly through the move; the last points are the rows."""
    user, [first, second] = await _user(session, keep_alive, "move", brokers=2)
    asset = await _asset(session, keep_alive, "moveA")
    out_leg = _tx(first, asset, TransactionType.TRANSFER, date(2024, 2, 5), "-10", "0")
    in_leg = _tx(second, asset, TransactionType.TRANSFER, date(2024, 2, 7), "10", "0")
    in_leg.cost_basis_override, in_leg.cost_basis_currency = D("100"), EUR
    await _persist(
        session,
        keep_alive,
        _tx(first, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        _tx(first, asset, TransactionType.BUY, date(2024, 1, 10), "10", "-1000"),
        out_leg,
        in_leg,
        *_prices(asset, date(2024, 1, 1), TO, start="100", step="0.5"),
    )
    out_leg.related_transaction_id, in_leg.related_transaction_id = in_leg.id, out_leg.id
    await session.flush()
    service = PortfolioService(session)

    sender, receiver, summed = (await service.get_positions_series(user_id=user.id, query=_query([(first.id, asset.id), (second.id, asset.id), (None, asset.id)]))).series
    contribution = await service.get_positions_contribution(user_id=user.id, target_currency_override=EUR, date_from=FROM, date_to=TO)

    rows = {(row.broker_id, row.asset_id): row for row in contribution.positions}
    assert sender.points[-1].pnl == rows[(first.id, asset.id)].period_pnl
    assert receiver.points[-1].pnl == rows[(second.id, asset.id)].period_pnl
    assert (sender.closed_on, sender.last_date, receiver.held_at_end) == (date(2024, 2, 5), date(2024, 2, 7), True)
    # The asset held at one broker would go price by price: pnl = 10 x (price - 100) on every day of the move.
    for point in summed.points:
        if point.date >= date(2024, 2, 8):
            assert point.pnl == D("10") * (D("100") + D("0.5") * (point.date - date(2024, 1, 1)).days - D("100")), point.date
    assert {point.base for point in summed.points} == {D("1000")}, "the move brings in no new capital"


@pytest.mark.asyncio
async def test_p4_bought_in_two_goes_the_base_grows_with_the_second_purchase_and_a_sale_does_not_lower_it(session, keep_alive):
    user, [broker] = await _user(session, keep_alive, "twogoes")
    asset = await _asset(session, keep_alive, "twogoesA")
    await _persist(
        session,
        keep_alive,
        _tx(broker, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "9000"),
        _tx(broker, asset, TransactionType.BUY, date(2024, 1, 10), "10", "-1000"),
        _tx(broker, asset, TransactionType.BUY, date(2024, 2, 1), "10", "-1100"),
        _tx(broker, asset, TransactionType.SELL, date(2024, 3, 1), "-5", "700"),
        *_prices(asset, date(2024, 1, 1), TO, start="100", step="0.5"),
    )

    [series] = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(broker.id, asset.id)]))).series

    points = {p.date: p for p in series.points}
    assert series.first_date == date(2024, 1, 10) and not series.held_at_start
    assert points[date(2024, 1, 31)].base == D("1000")
    assert points[date(2024, 2, 1)].base == D("2100")
    assert points[date(2024, 3, 31)].base == D("2100"), "a sale never lowers the base"
    assert points[date(2024, 3, 31)].pnl_percent == points[date(2024, 3, 31)].pnl / D("2100")


@pytest.mark.asyncio
async def test_p4_a_split_changes_the_quantity_and_not_the_pnl(session, keep_alive):
    from backend.app.db.models import AssetEvent, AssetEventType  # noqa: PLC0415

    user, [broker] = await _user(session, keep_alive, "split")
    asset = await _asset(session, keep_alive, "splitA")
    event = AssetEvent(asset_id=asset.id, date=date(2024, 2, 15), type=AssetEventType.SPLIT, value=D("2"), currency=EUR)
    await _persist(session, keep_alive, event)
    adjustment = _tx(broker, asset, TransactionType.ADJUSTMENT, date(2024, 2, 15), "10", "0")
    adjustment.asset_event_id = event.id
    # The price halves with the split, so the position's worth goes on smoothly.
    rows = [*_prices(asset, date(2024, 1, 1), date(2024, 2, 14), start="100", step="0"), *_prices(asset, date(2024, 2, 15), TO, start="50", step="0")]
    await _persist(
        session,
        keep_alive,
        _tx(broker, None, TransactionType.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        _tx(broker, asset, TransactionType.BUY, date(2024, 1, 10), "10", "-1000"),
        adjustment,
        *rows,
    )

    [series] = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_query([(broker.id, asset.id)]))).series

    points = {p.date: p for p in series.points}
    assert (points[date(2024, 2, 14)].quantity, points[date(2024, 2, 15)].quantity) == (D("10"), D("20"))
    assert {p.pnl for p in series.points} == {D("0")}
    assert {p.base for p in series.points} == {D("1000")}

"""
W5-2b, the numbers: the incoming ADJUSTMENT a broker's split row becomes, read by Lots (FIFO + WAC lines) and by the Dashboard.

A stock split reaches the ledger as a SPLIT asset event (``value`` = the ratio) and, per broker, one incoming ADJUSTMENT row linked to it
(``asset_event_id``) whose ``quantity`` is the shares ADDED. The Revolut and Trading 212 plugins write that row with no cost
(``cost_basis_override`` 0) and flag it ``possible_split``; the user then links the SPLIT event. The two engines do not read the linked row alike:

- the FIFO engine (``financial_math/fifo/engine.py``, ``_apply_split``) IGNORES the row's quantity and multiplies every open fragment by the
  event's RATIO (quantity x ratio, unit price / ratio);
- the average cost (``financial_math/average_cost.py``, ``cost_movement_from_transaction`` with ``split_linked``) ADDS the row's QUANTITY to the pool
  and leaves the cost alone.

They agree only when ``row quantity = shares held x (ratio - 1)``. That is what the plugin's new ``rounding_delta`` in the ``possible_split``
context reports. This file pins the numbers, never a formula: each expectation is written by hand, and the same history is read in a second,
equivalent configuration (the row written without a cost: what the book's own split writes) to prove the two agree.

Cases (the lot W5-2b brief, in its letters):
- (b) a linked row, 10 shares bought at 100 and a 2:1 split with a row of 10: 20 shares, total cost 1000, average 50, in the lots and in the
  Dashboard, the same with the row at cost 0 as without cost;
- (c) 0.08215962 shares held and a 3:1 split: a row of 0.16431924 (exact) agrees across the engines; a row rounded to 0.1643 does NOT: it records
  the difference (this is the case the plugin flags with ``rounding_delta``);
- (d) a sale before the split: 10 bought, 4 sold, a 2:1 split with a row of 6: 12 shares, the cost of the 6 left, average halved;
- (a) a row NOT linked to an event: the total cost stays, the new shares are a lot at cost 0 and the average falls;
- (e) one asset at two brokers, each with its own row on the same event;
- (f) two splits on one day: two events, two rows.

Every row of the ledger is the test's own: a user, brokers and an asset created under a unique marker, read back by id; the session is rolled back.
"""

import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse, PortfolioSummary
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

REPORT = "EUR"
BUY_DAY = date(2025, 1, 10)
SELL_DAY = date(2025, 1, 20)
SPLIT_DAY = date(2025, 2, 1)
READING_DAY = date(2025, 2, 10)

# How the split's row is written (the three states a row of a split can be in, in the ledger).
ZERO_COST = "linked, cost_basis_override 0"  # what the Revolut / Trading 212 plugins write, once the user links the event
NO_COST = "linked, no cost basis"  # what the book's own split writes
UNLINKED = "not linked, cost_basis_override 0"  # what the plugins write before the user links an event


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@dataclass
class Book:
    """One test's user, its brokers and one asset, quoted ``prices`` (a price per day) in EUR."""

    user: User
    asset: Asset
    brokers: list[Broker]
    events: list[AssetEvent] = field(default_factory=list)

    @property
    def broker(self) -> Broker:
        return self.brokers[0]


async def _book(session: AsyncSession, label: str, prices: dict[date, str], *, brokers: int = 1) -> Book:
    marker = uuid4().hex[:12]
    user = User(username=f"splitledger_{marker}", email=f"splitledger_{marker}@test.com", hashed_password="fakehash", is_active=True)
    session.add(user)
    await session.flush()
    asset = Asset(display_name=f"Split ledger {label} {marker}", currency=REPORT, asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    owned = []
    for index in range(brokers):
        broker = Broker(name=f"Split ledger {label} {index} {marker}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        owned.append(broker)
    session.add_all(PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=REPORT, source_plugin_key="split_ledger_test") for day, close in prices.items())
    await session.flush()
    return Book(user=user, asset=asset, brokers=owned)


async def _deposit_and_buy(session: AsyncSession, book: Book, broker: Broker, quantity: str, cost: str, *, day: date = BUY_DAY) -> None:
    """The cash the purchase spends (so the Dashboard's capital is the cost) and the purchase itself."""
    session.add_all(
        [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day, amount=Decimal(cost), currency=REPORT),
            Transaction(broker_id=broker.id, asset_id=book.asset.id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), amount=-Decimal(cost), currency=REPORT),
        ]
    )
    await session.flush()


async def _sell(session: AsyncSession, book: Book, broker: Broker, quantity: str, proceeds: str, *, day: date = SELL_DAY) -> None:
    session.add(Transaction(broker_id=broker.id, asset_id=book.asset.id, type=TransactionType.SELL, date=day, quantity=-Decimal(quantity), amount=Decimal(proceeds), currency=REPORT))
    await session.flush()


async def _split_event(session: AsyncSession, book: Book, ratio: str, *, day: date = SPLIT_DAY) -> AssetEvent:
    event = AssetEvent(asset_id=book.asset.id, date=day, type=AssetEventType.SPLIT, value=Decimal(ratio), currency=REPORT)
    session.add(event)
    await session.flush()
    book.events.append(event)
    return event


async def _split_row(session: AsyncSession, book: Book, broker: Broker, event: AssetEvent, quantity: str, *, how: str = ZERO_COST) -> Transaction:
    """The incoming ADJUSTMENT of a split: ``quantity`` shares added, written the way ``how`` says."""
    row = Transaction(
        broker_id=broker.id,
        asset_id=book.asset.id,
        type=TransactionType.ADJUSTMENT,
        date=event.date,
        quantity=Decimal(quantity),
        asset_event_id=None if how == UNLINKED else event.id,
        cost_basis_override=None if how == NO_COST else Decimal("0"),
        cost_basis_currency=None if how == NO_COST else REPORT,
    )
    session.add(row)
    await session.flush()
    return row


async def _lots(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> LotsAnalysisResponse:
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=None,
        date_from=None,
        date_to=date_to,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY, LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
    )


async def _dashboard(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> PortfolioSummary:
    return await PortfolioService(session).get_summary(user_id=book.user.id, target_currency_override=REPORT, date_to=date_to)


def _amount(value: Optional[Currency]) -> Optional[Decimal]:
    return None if value is None else value.amount


def _ledger_view(lots: LotsAnalysisResponse, summary: PortfolioSummary, book: Book, *, on: date = READING_DAY) -> dict:
    """What the two pages say of the asset on ``on``: the FIFO lots' quantity and cost, the average-cost line's point, the Dashboard's holdings."""
    lot_rows = lots.lots or []
    wac_points = {point.date: point for point in lots.cumulative_wac_history or []}
    holdings = [holding for holding in summary.holdings if holding.asset_id == book.asset.id]
    return {
        "lots status": lots.calculation_status,
        "lots: open quantity": sum((lot.open_quantity for lot in lot_rows), Decimal("0")),
        "lots: original cost of the open lots": sum((lot.original_cost for lot in lot_rows if lot.open_quantity > 0), Decimal("0")),
        "average-cost line: quantity": wac_points[on].pool_qty if on in wac_points else None,
        "average-cost line: cost per share": wac_points[on].wac if on in wac_points else None,
        "dashboard: quantity": sum((holding.quantity for holding in holdings), Decimal("0")),
        "dashboard: open cost basis": _amount(summary.open_cost_basis),
        "dashboard: total invested": _amount(summary.total_invested),
        "dashboard: total gain": _amount(summary.total_gain_loss),
        "dashboard: cost per share": holdings[0].wac_per_unit if len(holdings) == 1 else None,
        "dashboard: realized gain": _amount(summary.period_realized_gain_loss),
        "lots: realized gain": sum((lot.realized_pnl for lot in lot_rows), Decimal("0")),
    }


async def _read(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> dict:
    return _ledger_view(await _lots(session, book, date_to=date_to), await _dashboard(session, book, date_to=date_to), book, on=date_to)


ROW_STYLES = [ZERO_COST, NO_COST]


# =============================================================================
# (b) a linked row: 10 at 100, a 2:1 split, a row of 10
# =============================================================================


class TestLinkedRowAfterOnePurchase:
    """(b) 10 bought at 100 (cost 1000), a SPLIT of ratio 2 and a linked row of 10 shares: 20 shares, cost 1000, average 50, in every reader."""

    EXPECTED = {
        "lots status": "COMPLETE",
        "lots: open quantity": Decimal("20"),
        "lots: original cost of the open lots": Decimal("1000"),
        "average-cost line: quantity": Decimal("20"),
        "average-cost line: cost per share": Decimal("50"),
        "dashboard: quantity": Decimal("20"),
        "dashboard: open cost basis": Decimal("1000"),
        "dashboard: total invested": Decimal("1000"),
        "dashboard: total gain": Decimal("200"),  # 20 shares x 60 (the quote on the reading day) - 1000
        "dashboard: cost per share": Decimal("50"),
        "dashboard: realized gain": Decimal("0"),
        "lots: realized gain": Decimal("0"),
    }

    async def _build(self, session: AsyncSession, how: str) -> Book:
        book = await _book(session, "b", {BUY_DAY: "100", READING_DAY: "60"})
        await _deposit_and_buy(session, book, book.broker, "10", "1000")
        event = await _split_event(session, book, "2")
        await _split_row(session, book, book.broker, event, "10", how=how)
        return book

    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ROW_STYLES, ids=["row at cost 0", "row without a cost"])
    async def test_quantity_cost_and_average_are_the_hand_written_numbers(self, session, how: str):
        print_section(f"(b) {how}")
        book = await self._build(session, how)

        assert await _read(session, book) == self.EXPECTED
        print_success("(b): 20 shares, cost 1000, average 50, gain 200")

    @pytest.mark.asyncio
    async def test_a_row_at_cost_zero_reads_as_a_row_without_cost(self, session):
        """The configuration of the reference (what the book's own split writes) and the plugin's agree figure by figure, in two separate books."""
        at_zero = await self._build(session, ZERO_COST)
        without = await self._build(session, NO_COST)

        assert await _read(session, at_zero) == await _read(session, without)

    @pytest.mark.asyncio
    async def test_the_lot_is_one_lot_of_twenty_at_fifty(self, session):
        book = await self._build(session, ZERO_COST)

        lots = (await _lots(session, book)).lots or []

        assert [(lot.original_quantity, lot.open_quantity, lot.opening_unit_price, lot.original_cost) for lot in lots] == [(Decimal("20"), Decimal("20"), Decimal("50"), Decimal("1000"))]

    @pytest.mark.asyncio
    async def test_the_split_event_shows_in_the_lot_history_with_its_ratio(self, session):
        book = await self._build(session, ZERO_COST)
        response = await LotsAnalysisService(session).get_lots_analysis(
            user_id=book.user.id,
            asset_id=book.asset.id,
            broker_ids=None,
            date_from=None,
            date_to=READING_DAY,
            target_currency=REPORT,
            selected_lot_ids=None,
            requested_analyses=[LotAnalysisType.LOT_SUMMARY, LotAnalysisType.EVENT_HISTORY],
        )

        splits = [row for row in response.lot_events or [] if row.kind == "SPLIT"]

        assert [row.ratio for row in splits] == [Decimal("2")]


# =============================================================================
# (c) rounding: 0.08215962 shares held, a 3:1 split
# =============================================================================


HELD = "0.08215962"
HELD_COST = "8.215962"  # 100 a share
EXACT_ROW = "0.16431924"  # held x (3 - 1)
ROUNDED_ROW = "0.1643"  # the same row, as a broker that rounds to four places writes it
FIFO_AFTER_SPLIT = Decimal("0.24647886")  # held x 3
WAC_AFTER_ROUNDED_ROW = Decimal("0.24645962")  # held + 0.1643
ROUNDING_GAP = Decimal("0.00001924")  # 0.1643 - 0.16431924 in absolute value: FIFO has MORE shares than the average-cost line


class TestRoundingOfTheRow:
    """(c) The engines agree when the row is ``held x (ratio - 1)`` and differ by the rounding of the row when it is not. The plugin's
    ``rounding_delta`` is the same gap seen at import time."""

    async def _build(self, session: AsyncSession, row: str, how: str = ZERO_COST) -> Book:
        book = await _book(session, "c", {BUY_DAY: "100", READING_DAY: "35"})
        await _deposit_and_buy(session, book, book.broker, HELD, HELD_COST)
        event = await _split_event(session, book, "3")
        await _split_row(session, book, book.broker, event, row, how=how)
        return book

    @pytest.mark.asyncio
    async def test_an_exact_row_gives_the_same_quantity_and_cost_in_every_reader(self, session):
        book = await self._build(session, EXACT_ROW)

        view = await _read(session, book)

        assert view["lots: open quantity"] == FIFO_AFTER_SPLIT
        assert view["average-cost line: quantity"] == FIFO_AFTER_SPLIT
        assert view["dashboard: quantity"] == FIFO_AFTER_SPLIT
        assert view["lots: original cost of the open lots"] == Decimal(HELD_COST)
        assert view["dashboard: open cost basis"] == Decimal(HELD_COST)

    @pytest.mark.asyncio
    async def test_an_exact_row_gives_the_same_average_to_the_lot_and_to_the_line(self, session):
        """The lot's unit price and the line's cost per share are two outputs of the backend for 8.215962 over 0.24647886: they may differ only by
        the last digit of the division."""
        book = await self._build(session, EXACT_ROW)
        lots = await _lots(session, book)

        (lot,) = lots.lots or []
        (point,) = [p for p in lots.cumulative_wac_history or [] if p.date == READING_DAY]

        assert abs(lot.opening_unit_price - point.wac) < Decimal("1e-9"), f"lot {lot.opening_unit_price}, line {point.wac}"

    @pytest.mark.asyncio
    async def test_a_rounded_row_leaves_fifo_with_the_shares_the_average_cost_does_not_count(self, session):
        """CURRENT BEHAVIOUR, not an endorsement. A row of 0.1643 on a split of ratio 3 over 0.08215962 held: the FIFO lots follow the RATIO
        (0.08215962 x 3 = 0.24647886), the average-cost line follows the ROW (0.08215962 + 0.1643 = 0.24645962). The gap, 0.00001924, is exactly what
        the plugin now reports as ``rounding_delta`` (held x (suggested ratio - 1) - row)."""
        book = await self._build(session, ROUNDED_ROW)

        view = await _read(session, book)

        assert view["lots: open quantity"] == FIFO_AFTER_SPLIT
        assert view["average-cost line: quantity"] == WAC_AFTER_ROUNDED_ROW
        assert view["lots: open quantity"] - view["average-cost line: quantity"] == ROUNDING_GAP
        # The Dashboard: the same rows through the average cost.
        assert view["dashboard: quantity"] == WAC_AFTER_ROUNDED_ROW
        # The cost does not move in either engine.
        assert view["lots: original cost of the open lots"] == Decimal(HELD_COST)
        assert view["dashboard: open cost basis"] == Decimal(HELD_COST)

    @pytest.mark.asyncio
    async def test_selling_what_the_average_cost_holds_leaves_the_gap_open_in_the_lots(self, session):
        """CURRENT BEHAVIOUR. The user sells everything the broker says is held, 0.24645962 shares (held + the rounded row): the average-cost
        line and the Dashboard are at zero, the FIFO lot keeps the 0.00001924 shares nobody can sell."""
        book = await self._build(session, ROUNDED_ROW)
        await _sell(session, book, book.broker, str(WAC_AFTER_ROUNDED_ROW), "9", day=date(2025, 2, 5))

        lots = await _lots(session, book)
        summary = await _dashboard(session, book)
        view = _ledger_view(lots, summary, book)

        assert view["average-cost line: quantity"] == Decimal("0")
        assert view["dashboard: quantity"] == Decimal("0")
        assert view["lots: open quantity"] == ROUNDING_GAP


# =============================================================================
# (d) a sale before the split
# =============================================================================


class TestSplitAfterAPartialSale:
    """(d) 10 bought at 100, 4 sold for 500, then a 2:1 split with a row of 6 (= 6 held x (2 - 1)): 12 shares, the cost of the 6 left, average halved."""

    EXPECTED = {
        "lots status": "COMPLETE",
        "lots: open quantity": Decimal("12"),  # 6 left x 2
        "lots: original cost of the open lots": Decimal("1000"),  # the lot's own cost, 4 of its 10 sold: the cost of what is left is read below
        "average-cost line: quantity": Decimal("12"),
        "average-cost line: cost per share": Decimal("50"),  # 100 halved
        "dashboard: quantity": Decimal("12"),
        "dashboard: open cost basis": Decimal("600"),  # the 6 left, bought at 100: the sale took 400 of the 1000
        "dashboard: total invested": Decimal("1000"),
        "dashboard: total gain": Decimal("280"),  # 12 x 65 (the quote on the reading day) + 500 of proceeds - 1000
        "dashboard: cost per share": Decimal("50"),
        "dashboard: realized gain": Decimal("100"),  # 4 sold for 500 against 4 x 100
        "lots: realized gain": Decimal("100"),
    }

    async def _build(self, session: AsyncSession, how: str) -> Book:
        book = await _book(session, "d", {BUY_DAY: "100", SELL_DAY: "125", READING_DAY: "65"})
        await _deposit_and_buy(session, book, book.broker, "10", "1000")
        await _sell(session, book, book.broker, "4", "500")
        event = await _split_event(session, book, "2")
        await _split_row(session, book, book.broker, event, "6", how=how)
        return book

    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ROW_STYLES, ids=["row at cost 0", "row without a cost"])
    async def test_the_numbers_are_the_hand_written_ones(self, session, how: str):
        book = await self._build(session, how)

        assert await _read(session, book) == self.EXPECTED

    @pytest.mark.asyncio
    async def test_a_row_at_cost_zero_reads_as_a_row_without_cost(self, session):
        at_zero = await self._build(session, ZERO_COST)
        without = await self._build(session, NO_COST)

        assert await _read(session, at_zero) == await _read(session, without)

    @pytest.mark.asyncio
    async def test_the_open_lot_holds_twelve_shares_worth_780_over_a_cost_of_600(self, session):
        """The lot's own reading of the cost left: open value 12 x 65, price-only gain = value - cost of the 6 left x 100 = 180."""
        book = await self._build(session, ZERO_COST)

        lots = (await _lots(session, book)).lots or []

        assert [(lot.open_quantity, lot.open_value, lot.market_pnl) for lot in lots] == [(Decimal("12"), Decimal("780"), Decimal("180"))]


# =============================================================================
# (a) a row that is NOT linked to a split event
# =============================================================================


class TestUnlinkedRow:
    """(a) The row as the plugin writes it, before the user links a SPLIT event: 10 more shares at cost 0. The position's total cost stays 1000, the new
    shares are a lot of their own at cost 0 and the average falls to 50 (declared behaviour: without the link nothing says it is a split)."""

    async def _build(self, session: AsyncSession) -> Book:
        book = await _book(session, "a", {BUY_DAY: "100", SPLIT_DAY: "50", READING_DAY: "50"})
        await _deposit_and_buy(session, book, book.broker, "10", "1000")
        event = await _split_event(session, book, "2")  # the event exists, the row is just not linked to it
        await _split_row(session, book, book.broker, event, "10", how=UNLINKED)
        return book

    @pytest.mark.asyncio
    async def test_total_cost_stays_and_the_average_falls(self, session):
        book = await self._build(session)

        view = await _read(session, book)

        assert view["lots: open quantity"] == Decimal("20")
        assert view["lots: original cost of the open lots"] == Decimal("1000")
        assert view["average-cost line: quantity"] == Decimal("20")
        assert view["average-cost line: cost per share"] == Decimal("50")
        assert (view["dashboard: quantity"], view["dashboard: open cost basis"], view["dashboard: total invested"], view["dashboard: cost per share"]) == (Decimal("20"), Decimal("1000"), Decimal("1000"), Decimal("50"))

    @pytest.mark.asyncio
    async def test_the_new_shares_are_a_lot_at_cost_zero_beside_the_untouched_first_lot(self, session):
        book = await self._build(session)

        lots = (await _lots(session, book)).lots or []

        by_day = {lot.opening_date: (lot.original_quantity, lot.opening_unit_price, lot.original_cost, lot.open_quantity) for lot in lots}
        assert by_day == {BUY_DAY: (Decimal("10"), Decimal("100"), Decimal("1000"), Decimal("10")), SPLIT_DAY: (Decimal("10"), Decimal("0"), Decimal("0"), Decimal("10"))}

    @pytest.mark.asyncio
    async def test_the_gain_is_zero_the_day_before_and_the_day_of_when_the_quote_halves(self, session):
        """No jump: the 10 shares cost nothing, and the quote halves from 100 to 50 on the day, so the position is worth 1000 on both days, as cost."""
        book = await self._build(session)

        before = await _dashboard(session, book, date_to=date(2025, 1, 31))
        after = await _dashboard(session, book)

        assert (_amount(before.total_gain_loss), _amount(after.total_gain_loss)) == (Decimal("0"), Decimal("0"))


# =============================================================================
# (e) one asset at two brokers
# =============================================================================


class TestTwoBrokersOnOneEvent:
    """(e) The same asset at two brokers, one SPLIT event, a row at each broker (10 at A, 6 at B, each = its holding x (2 - 1)): each position doubles
    on its own, and the totals are the sums."""

    async def _build(self, session: AsyncSession, how: str) -> Book:
        book = await _book(session, "e", {BUY_DAY: "100", READING_DAY: "60"}, brokers=2)
        broker_a, broker_b = book.brokers
        await _deposit_and_buy(session, book, broker_a, "10", "1000")
        await _deposit_and_buy(session, book, broker_b, "6", "600")
        event = await _split_event(session, book, "2")
        await _split_row(session, book, broker_a, event, "10", how=how)
        await _split_row(session, book, broker_b, event, "6", how=how)
        return book

    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ROW_STYLES, ids=["rows at cost 0", "rows without a cost"])
    async def test_the_totals_are_the_sums_of_two_doubled_positions(self, session, how: str):
        book = await self._build(session, how)

        view = await _read(session, book)

        assert view["lots status"] == "COMPLETE"
        assert (view["lots: open quantity"], view["lots: original cost of the open lots"]) == (Decimal("32"), Decimal("1600"))
        assert (view["average-cost line: quantity"], view["average-cost line: cost per share"]) == (Decimal("32"), Decimal("50"))
        assert (view["dashboard: quantity"], view["dashboard: open cost basis"], view["dashboard: total invested"]) == (Decimal("32"), Decimal("1600"), Decimal("1600"))
        assert view["dashboard: total gain"] == Decimal("320")  # 32 x 60 - 1600

    @pytest.mark.asyncio
    async def test_each_broker_keeps_its_own_lot_doubled(self, session):
        book = await self._build(session, ZERO_COST)
        broker_a, broker_b = book.brokers

        lots = (await _lots(session, book)).lots or []

        assert {lot.opening_broker_id: (lot.open_quantity, lot.original_cost, lot.opening_unit_price) for lot in lots} == {
            broker_a.id: (Decimal("20"), Decimal("1000"), Decimal("50")),
            broker_b.id: (Decimal("12"), Decimal("600"), Decimal("50")),
        }

    @pytest.mark.asyncio
    async def test_each_broker_has_its_own_average_cost_line(self, session):
        book = await self._build(session, ZERO_COST)
        broker_a, broker_b = book.brokers

        response = await _lots(session, book)

        points = {point.broker_id: (point.pool_qty, point.wac) for point in response.broker_wac_history or [] if point.date == READING_DAY}
        assert points == {broker_a.id: (Decimal("20"), Decimal("50")), broker_b.id: (Decimal("12"), Decimal("50"))}


# =============================================================================
# (f) two splits on one day
# =============================================================================


class TestTwoSplitsOnOneDay:
    """(f) Two SPLIT events on one day, 2:1 then 3:1, a row each (10 = 10 x (2 - 1), then 40 = 20 x (3 - 1)): 60 shares, cost 1000."""

    async def _build(self, session: AsyncSession, how: str) -> Book:
        book = await _book(session, "f", {BUY_DAY: "100", READING_DAY: "20"})
        await _deposit_and_buy(session, book, book.broker, "10", "1000")
        first = await _split_event(session, book, "2")
        await _split_row(session, book, book.broker, first, "10", how=how)
        second = await _split_event(session, book, "3")
        await _split_row(session, book, book.broker, second, "40", how=how)
        return book

    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ROW_STYLES, ids=["rows at cost 0", "rows without a cost"])
    async def test_sixty_shares_at_the_cost_of_ten(self, session, how: str):
        book = await self._build(session, how)

        view = await _read(session, book)

        assert view["lots status"] == "COMPLETE"
        assert (view["lots: open quantity"], view["lots: original cost of the open lots"]) == (Decimal("60"), Decimal("1000"))
        assert (view["average-cost line: quantity"], view["dashboard: quantity"], view["dashboard: open cost basis"]) == (Decimal("60"), Decimal("60"), Decimal("1000"))
        assert abs(view["average-cost line: cost per share"] - Decimal("1000") / Decimal("60")) < Decimal("1e-9")
        assert view["dashboard: total gain"] == Decimal("200")  # 60 x 20 - 1000

"""CP-16 — decision 47 end to end: the lots and the Dashboard of a book whose negative ADJUSTMENT carries a cost.

Workstream J «Numeri e analisi», release 1.3. Decision 47 (J-11): a leg that leaves without its pair becomes an
ADJUSTMENT −q carrying the average cost the units leave at — «the same principle in the opposite direction» as an
ADJUSTMENT-in with a cost — and in the decision's example both the Dashboard and the lots read a gain of 60.

THE SCENARIO — the S7 book of test_orphan_transfer_after_broker_delete.py, with the outgoing leg written as the
ADJUSTMENT decision 47 makes of it. One user owns broker A, 100 %. On 1 Oct 2018 A receives 200 EUR and buys 10 X for
200 EUR, 20 EUR a unit. On 3 Oct an ADJUSTMENT −4 X carries cost_basis_override 20 — per unit (db/models.py) — and
cost_basis_currency EUR: the 4 units leave at the pool's average cost, 80 EUR. X is quoted 25 EUR on 3 Oct and 30 EUR
on 5 Oct. Both readings are in EUR, in A's scope, up to 5 Oct.

(a) Dashboard — PortfolioService.get_summary. The ADJUSTMENT −4 with an override is a capital distribution
    (DailyStateBuilder._is_capital_adjustment): the cost it takes from the pool, 4 × 20, leaves the capital. Invested
    200 − 80 = 120, net worth 6 × 30 = 180 (no cash: 200 − 200), P&L 60. A GUARD: the Dashboard already read this
    before CP-16 (J-11), and CP-16 does not touch it.
(b) Lots — LotsAnalysisService.get_lots_analysis, LOT_SUMMARY: COMPLETE, one LONG lot, the BUY's. One lot, so the
    two readings of decision 47 coincide: the 4 units close at 20 — realized 4 × (20 − 20) = 0 — and the 80 handed
    over at cost are proceeds. Open 6, open value 6 × 30 = 180, pnl = 180 + 80 − 200 = 60, market_pnl = 60 − 0 = 60,
    total_pnl = 60 + 0 + 0 of income = 60. Before CP-16 the ADJUSTMENT_OUT closed at 0 — realized −80, proceeds 0,
    pnl 180 − 200 = −20, total_pnl −20 (market_pnl 60 either way).
(c) The lot's total_pnl is the Dashboard's P&L: 60 and 60. Before CP-16: −20 against 60.

No screen writes a cost on a negative ADJUSTMENT (type_metadata.py: the ADJUSTMENT cost basis is
"required_qty_pos"): the API can, and W's conversions will (the deletion of a receiving broker, the orphans already
in the databases, «split the pair»). So the rows are written straight into the session — no transaction
validation — and never committed: the ``session`` fixture rolls back, so nothing outlives the test. Each test owns
its user, broker and asset, named with a unique marker; the prices it writes are its asset's. No FX: everything is
in EUR.
"""

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse, PortfolioSummary
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

REPORT = "EUR"
FUNDING_DAY = date(2018, 10, 1)  # A: +200 EUR, then 10 X for 200 EUR — 20 EUR a unit
HANDOVER_DAY = date(2018, 10, 3)  # the ADJUSTMENT −4 at 20 EUR a unit
READING_DAY = date(2018, 10, 5)  # date_to of both readings
PRICES = {HANDOVER_DAY: "25", READING_DAY: "30"}
COST_PER_UNIT = "20"  # the pool's average cost on 3 Oct, 200 / 10: what the Auto cost writes on the row

# (a) The Dashboard of A: the 80 handed over at cost leave the capital.
DASHBOARD = {
    "total_invested": Decimal("120"),  # 200 deposited − 4 × 20 distributed in kind
    "net_worth": Decimal("180"),  # 6 × 30, and no cash: 200 − 200
    "total_gain_loss": Decimal("60"),  # 180 − 120
}

# (b) The lots of X in A: the BUY's lot hands 4 units over at their cost.
LOTS = {
    "calculation_status": "COMPLETE",
    "lots": [
        {
            "opens on": "the BUY",
            "direction": "LONG",
            "open_quantity": Decimal("6"),  # 10 − 4
            "cumulative_proceeds": Decimal("80"),  # 4 × 20, the value handed over at cost (before CP-16: 0)
            "realized_pnl": Decimal("0"),  # 4 × (20 − 20) (before CP-16: −80, closed at 0)
            "pnl": Decimal("60"),  # 6 × 30 + 80 − 200 (before CP-16: −20)
            "market_pnl": Decimal("60"),  # pnl − realized (60 before CP-16 too: −20 − (−80))
            "total_pnl": Decimal("60"),  # market + realized + 0 of income (before CP-16: −20)
        }
    ],
}


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
    """One test's user, its broker A, asset X, and A's two rows on X: the BUY and the ADJUSTMENT −4 with a cost."""

    user: User
    broker: Broker
    asset: Asset
    buy: Transaction
    handover: Transaction


async def _book(session: AsyncSession) -> Book:
    """The scenario, written straight into the session and flushed, never committed."""
    marker = uuid4().hex[:12]
    user = User(username=f"handover_{marker}", email=f"handover_{marker}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"Handover at cost A {marker}")
    asset = Asset(display_name=f"Handover at cost X {marker}", currency=REPORT, asset_type=AssetType.STOCK)
    session.add_all([user, broker, asset])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    session.add_all(PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=REPORT, source_plugin_key="handover_at_cost_test") for day, close in PRICES.items())
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=FUNDING_DAY, quantity=Decimal("10"), amount=Decimal("-200"), currency=REPORT)
    handover = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=HANDOVER_DAY,
        quantity=Decimal("-4"),
        cost_basis_override=Decimal(COST_PER_UNIT),
        cost_basis_currency=REPORT,
    )
    session.add_all([Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=FUNDING_DAY, amount=Decimal("200"), currency=REPORT), buy, handover])
    await session.flush()
    return Book(user=user, broker=broker, asset=asset, buy=buy, handover=handover)


async def _dashboard(session: AsyncSession, book: Book) -> PortfolioSummary:
    """The Dashboard of A's scope, in EUR, up to the reading day."""
    return await PortfolioService(session).get_summary(user_id=book.user.id, broker_ids=[book.broker.id], target_currency_override=REPORT, date_to=READING_DAY)


async def _lots(session: AsyncSession, book: Book) -> LotsAnalysisResponse:
    """The lots page of X in A's scope, in EUR, from the first movement to the reading day: the lot summary."""
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=[book.broker.id],
        date_from=None,
        date_to=READING_DAY,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY],
    )


def _amount(value: Currency | None) -> Decimal | None:
    return None if value is None else value.amount


def _dashboard_view(summary: PortfolioSummary) -> dict:
    return {name: _amount(getattr(summary, name)) for name in DASHBOARD}


def _holding_of_x(summary: PortfolioSummary, book: Book) -> list[dict]:
    """A's holding of X, printed for the record: 6 at 20, worth 180, a gain of 60 (pinned by S7's MIRROR, not here)."""
    fields = ("quantity", "wac_per_unit", "current_value", "gain_loss")
    return [{name: getattr(holding, name) for name in fields} for holding in summary.holdings if holding.asset_id == book.asset.id and holding.broker_id == book.broker.id]


def _lots_view(response: LotsAnalysisResponse, book: Book) -> dict:
    return {
        "calculation_status": response.calculation_status,
        "lots": [
            {
                "opens on": "the BUY" if lot.opening_transaction_id == book.buy.id else lot.opening_transaction_id,
                "direction": lot.direction,
                "open_quantity": lot.open_quantity,
                "cumulative_proceeds": lot.cumulative_proceeds,
                "realized_pnl": lot.realized_pnl,
                "pnl": lot.pnl,
                "market_pnl": lot.market_pnl,
                "total_pnl": lot.total_pnl,
            }
            for lot in response.lots or []
        ],
    }


def _issue_codes(response: LotsAnalysisResponse) -> list[str] | None:
    quality = response.data_quality
    return None if quality is None else [issue.code for issue in quality.issues]


# =============================================================================
# Decision 47's example: lots and Dashboard read the same 60
# =============================================================================


class TestAdjustmentOutWithCostNumbers:
    @pytest.mark.asyncio
    async def test_dashboard_takes_the_handed_over_cost_out_of_the_capital(self, session):
        """(a) GUARD — as before CP-16 (J-11): invested 120 (200 − 4 × 20), net worth 180 (6 × 30), P&L 60."""
        print_section("CP-16 (a) — Dashboard of A after the ADJUSTMENT −4 at 20 EUR")
        book = await _book(session)

        summary = await _dashboard(session, book)
        observed = _dashboard_view(summary)
        print(f"dashboard: {observed}")
        print(f"A's X: {_holding_of_x(summary, book)}")

        assert observed == DASHBOARD
        print_success("CP-16 (a): 120 invested, 180 of net worth, 60 of P&L")

    @pytest.mark.asyncio
    async def test_lots_hand_the_units_over_at_their_cost(self, session):
        """(b) COMPLETE, one LONG lot — open 6, proceeds 80, realized 0, pnl 60, market 60, total 60.

        Before CP-16 the ADJUSTMENT_OUT closed at 0: proceeds 0, realized −80, pnl −20, total −20 (market 60).
        """
        print_section("CP-16 (b) — lots of X in A after the ADJUSTMENT −4 at 20 EUR")
        book = await _book(session)

        response = await _lots(session, book)
        observed = _lots_view(response, book)
        print(f"lots: {observed}")
        print(f"issue codes: {_issue_codes(response)}")

        assert observed == LOTS
        print_success("CP-16 (b): the BUY's lot hands 4 over at 20 — realized 0, proceeds 80, total 60")

    @pytest.mark.asyncio
    async def test_the_lots_total_pnl_is_the_dashboards_pnl(self, session):
        """(c) The BUY's lot reads the Dashboard's P&L, 60 and 60 — before CP-16, −20 against 60."""
        print_section("CP-16 (c) — the lot's total P&L against the Dashboard's")
        book = await _book(session)

        dashboard_pnl = _amount((await _dashboard(session, book)).total_gain_loss)
        lot_total_pnls = [lot.total_pnl for lot in (await _lots(session, book)).lots or [] if lot.opening_transaction_id == book.buy.id]
        print(f"Dashboard P&L: {dashboard_pnl}, the BUY's lot total_pnl: {lot_total_pnls}")

        assert lot_total_pnls == [dashboard_pnl]
        print_success(f"CP-16 (c): lots and Dashboard both read {dashboard_pnl}")

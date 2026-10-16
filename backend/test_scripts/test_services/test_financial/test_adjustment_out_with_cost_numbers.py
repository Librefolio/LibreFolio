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
its user, broker and asset, named with a unique marker; the prices it writes are its asset's. No FX in CP-16's book:
everything is in EUR.

J-24 — the developer's rule P21: «convert into the target currency at the rate of the transaction's day, and do every
calculation in the target currency». The Dashboard hands an outgoing ADJUSTMENT with a cost over at that cost converted
at the rate of its day, D, and realizes D − C against the historical cost C the pool gives up, as for a SELL
(DailyStateBuilder); the lots do it since CP-7a (lots/conversions.py, convert_closure). CP-16's book above is a GUARD
of it: one currency and the average cost on the row, D = C = 80 — its three tests read the same before and after J-24.

THE FOREIGN BOOK (TestForeignAdjustmentOutHandsOverAtItsDate) — the same handover in another currency. One user owns
broker A′, 100 %. On 5 Nov 2018 A′ receives 1000 USD and buys 10 X′ — a USD asset — for 1000 USD, 100 USD a unit, when
1 EUR = 1.25 USD (1 USD = 0.80 EUR): capital 800 EUR, the pool's cost 800 EUR. On 7 Nov an ADJUSTMENT −10 X′ carries
cost_basis_override 100 USD, when 1 EUR = 1.60 USD (1 USD = 0.625 EUR): it hands over D = 625 EUR, the pool gives up
C = 800 EUR. No price is written: nothing is held after 7 Nov. Both readings in EUR, up to 9 Nov.
(d) Dashboard: invested 800 − 625 = 175, net worth 0, P&L −175; the period's P&L −175, realized −175, other 0.
    Before J-24: invested 0 (800 − C), P&L 0, realized 0.
(e) Lots: one LONG lot, closed — cost 800, proceeds 625, realized −175, total P&L −175. A GUARD: CP-7a already reads it.
(f) The J-24 parity: the Dashboard's realized and P&L are the lot's, −175 and −175. Before J-24: 0 and 0 against them.
FX rows: the book reads two EUR/USD rates, on its own days, which it writes. ``fx_rates`` is global and unique on
(date, base, quote): a neighbour's row on those keys is deleted first, inside the same rolled-back transaction, so it
comes back intact afterwards and the test never reads a rate it did not write (the pattern of
test_lots_analysis_service.py, ``_own_fx_rate``). The days in between read them by backward fill; no figure pinned
here depends on those days.
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

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
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

# J-24 — the foreign book: X′ quoted in USD, read in EUR. FxRate stores the pair as EUR/USD (base < quote):
# 1 EUR = rate USD, so 1 USD = 1 / rate EUR — 0.80 on the purchase day, 0.625 on the handover day.
FX_ASSET_CURRENCY = "USD"
FX_BUY_DAY = date(2018, 11, 5)  # A′: +1000 USD, then 10 X′ for 1000 USD — 100 USD a unit
FX_HANDOVER_DAY = date(2018, 11, 7)  # the ADJUSTMENT −10 at 100 USD a unit
FX_READING_DAY = date(2018, 11, 9)  # date_to of both readings
FX_EUR_USD_RATES = {FX_BUY_DAY: "1.25", FX_HANDOVER_DAY: "1.6"}

# (d) The Dashboard of A′: the 10 units leave at 1000 USD × 0.625 = 625 EUR, the pool gives up 1000 USD × 0.80 = 800.
FX_DASHBOARD = {
    "total_invested": Decimal("175"),  # 800 deposited (1000 USD at 0.80) − 625 handed over (before J-24: 0, 800 − C)
    "net_worth": Decimal("0"),  # no units, no cash: 1000 − 1000 USD (0 before J-24 too)
    "total_gain_loss": Decimal("-175"),  # 0 − 175 (before J-24: 0)
    "period_pnl": Decimal("-175"),  # the period from the first row: NAV 0 − the net flows, 175 (before J-24: 0)
    "period_realized_gain_loss": Decimal("-175"),  # D − C = 625 − 800 (before J-24: 0, only a SELL was realized)
    "period_other_result": Decimal("0"),  # the period's P&L is all realized (0 before J-24 too)
}

# (e) The lots of X′ in A′: the BUY's lot hands its 10 units over at 100 USD, each leg at its own date (CP-7a).
FX_LOTS = [
    {
        "opens on": "the BUY",
        "direction": "LONG",
        "open_quantity": Decimal("0"),
        "original_cost": Decimal("800"),  # 1000 USD at 0.80, the opening's rate
        "cumulative_proceeds": Decimal("625"),  # 1000 USD at 0.625, the handover's rate
        "realized_pnl": Decimal("-175"),  # 625 − 800
        "total_pnl": Decimal("-175"),  # nothing open, no income: the realized
    }
]


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
    """One test's user, its broker, its asset, and the broker's two rows on it: the BUY and the outgoing ADJUSTMENT with
    a cost (−4 at 20 EUR in CP-16's book, −10 at 100 USD in J-24's foreign book)."""

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


async def _dashboard(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> PortfolioSummary:
    """The Dashboard of the book's broker, in EUR, up to ``date_to`` (CP-16's reading day by default)."""
    return await PortfolioService(session).get_summary(user_id=book.user.id, broker_ids=[book.broker.id], target_currency_override=REPORT, date_to=date_to)


async def _lots(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> LotsAnalysisResponse:
    """The lots page of the book's asset at its broker, in EUR, from the first movement to ``date_to``: the lot summary."""
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=[book.broker.id],
        date_from=None,
        date_to=date_to,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY],
    )


async def _own_eur_usd_rate(session: AsyncSession, day: date, rate: str) -> None:
    """The EUR/USD rate of ``day`` the foreign book reads, written by it: 1 EUR = ``rate`` USD.

    ``fx_rates`` is global and unique on (date, base, quote). A neighbour's row on this key is deleted first, inside
    this test's transaction, which the ``session`` fixture rolls back: the neighbour's row comes back intact, and
    this test reads its own rate, never someone else's.
    """
    await session.execute(delete(FxRate).where(FxRate.date == day, FxRate.base == REPORT, FxRate.quote == FX_ASSET_CURRENCY))
    session.add(FxRate(date=day, base=REPORT, quote=FX_ASSET_CURRENCY, rate=Decimal(rate), source="TEST_J24"))
    await session.flush()


async def _foreign_book(session: AsyncSession) -> Book:
    """J-24's book, written straight into the session and flushed, never committed: A′ receives 1000 USD and buys
    10 X′ (a USD asset) with them on 5 Nov, then an ADJUSTMENT −10 hands them over at 100 USD a unit on 7 Nov. The two
    EUR/USD rates it reads are its own."""
    marker = uuid4().hex[:12]
    user = User(username=f"handover_fx_{marker}", email=f"handover_fx_{marker}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"Handover at its date A {marker}")
    asset = Asset(display_name=f"Handover at its date X {marker}", currency=FX_ASSET_CURRENCY, asset_type=AssetType.STOCK)
    session.add_all([user, broker, asset])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    for day, rate in FX_EUR_USD_RATES.items():
        await _own_eur_usd_rate(session, day, rate)
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=FX_BUY_DAY, quantity=Decimal("10"), amount=Decimal("-1000"), currency=FX_ASSET_CURRENCY)
    handover = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=FX_HANDOVER_DAY,
        quantity=Decimal("-10"),
        cost_basis_override=Decimal("100"),
        cost_basis_currency=FX_ASSET_CURRENCY,
    )
    session.add_all([Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=FX_BUY_DAY, amount=Decimal("1000"), currency=FX_ASSET_CURRENCY), buy, handover])
    await session.flush()
    return Book(user=user, broker=broker, asset=asset, buy=buy, handover=handover)


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


def _fx_dashboard_view(summary: PortfolioSummary) -> dict:
    return {name: _amount(getattr(summary, name)) for name in FX_DASHBOARD}


def _fx_lots_view(response: LotsAnalysisResponse, book: Book) -> list[dict]:
    return [
        {
            "opens on": "the BUY" if lot.opening_transaction_id == book.buy.id else lot.opening_transaction_id,
            "direction": lot.direction,
            "open_quantity": lot.open_quantity,
            "original_cost": lot.original_cost,
            "cumulative_proceeds": lot.cumulative_proceeds,
            "realized_pnl": lot.realized_pnl,
            "total_pnl": lot.total_pnl,
        }
        for lot in response.lots or []
    ]


# =============================================================================
# Decision 47's example: lots and Dashboard read the same 60
# =============================================================================


class TestAdjustmentOutWithCostNumbers:
    @pytest.mark.asyncio
    async def test_dashboard_takes_the_handed_over_cost_out_of_the_capital(self, session):
        """(a) GUARD — as before CP-16 (J-11): invested 120 (200 − 4 × 20), net worth 180 (6 × 30), P&L 60.

        A J-24 GUARD too: one currency and the average cost on the row, so the 80 handed over are the 80 of cost.
        """
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


# =============================================================================
# J-24: the same handover in USD, read in EUR — the Dashboard realizes it at the rate of its day, as the lots do
# =============================================================================


class TestForeignAdjustmentOutHandsOverAtItsDate:
    @pytest.mark.asyncio
    async def test_dashboard_realizes_the_handover_at_the_rate_of_its_day(self, session):
        """(d) Invested 175 (800 − 625), net worth 0, P&L −175; the period's P&L −175, realized −175, other 0.

        Before J-24: invested 0 (800 − the pool's 800), net worth 0, P&L 0; the period's P&L 0, realized 0, other 0.
        """
        print_section("J-24 (d) — Dashboard of A′ after the ADJUSTMENT −10 at 100 USD, in EUR")
        book = await _foreign_book(session)

        observed = _fx_dashboard_view(await _dashboard(session, book, date_to=FX_READING_DAY))
        print(f"dashboard: {observed}")

        assert observed == FX_DASHBOARD
        print_success("J-24 (d): 175 invested, 0 of net worth, −175 of P&L, all of it realized")

    @pytest.mark.asyncio
    async def test_lots_realize_the_handover_at_the_rate_of_its_day(self, session):
        """(e) GUARD (CP-7a) — one LONG lot, closed: cost 800 at the opening's rate, proceeds 625 at the handover's,
        realized −175, total P&L −175. The same before and after J-24: the lots do not change."""
        print_section("J-24 (e) — lots of X′ in A′ after the ADJUSTMENT −10 at 100 USD, in EUR")
        book = await _foreign_book(session)

        response = await _lots(session, book, date_to=FX_READING_DAY)
        observed = _fx_lots_view(response, book)
        print(f"lots: {observed}")
        print(f"issue codes: {_issue_codes(response)}")

        assert observed == FX_LOTS
        print_success("J-24 (e): the BUY's lot hands 10 over at 100 USD — cost 800, proceeds 625, realized −175")

    @pytest.mark.asyncio
    async def test_the_dashboards_realized_is_the_lots_realized(self, session):
        """(f) The J-24 parity: one lot, whose cost is the row's cost, so the Dashboard reads the lot's realized and P&L —
        −175 and −175 on both sides.

        Before J-24: the Dashboard read 0 and 0 against the lot's −175 and −175.
        """
        print_section("J-24 (f) — the Dashboard's realized and P&L against the lot's")
        book = await _foreign_book(session)

        summary = await _dashboard(session, book, date_to=FX_READING_DAY)
        lots = [lot for lot in (await _lots(session, book, date_to=FX_READING_DAY)).lots or [] if lot.opening_transaction_id == book.buy.id]
        assert len(lots) == 1, f"precondition: one lot, opened by the BUY — got {lots}"
        (lot,) = lots
        dashboard = {"realized": _amount(summary.period_realized_gain_loss), "P&L": _amount(summary.total_gain_loss)}
        print(f"Dashboard: {dashboard}, the BUY's lot: realized {lot.realized_pnl}, total P&L {lot.total_pnl}")

        assert dashboard == {"realized": lot.realized_pnl, "P&L": lot.total_pnl}
        print_success(f"J-24 (f): Dashboard and lots both realize {lot.realized_pnl}")

"""N78-1 — an outgoing ADJUSTMENT has no value: the lots and the Dashboard of a book whose negative ADJUSTMENT stores one.

THE DECISION — the developer's, 21/10/2026 (N78-1, plan 04 «N78-1 · Una rettifica in uscita non ha valore: cura»;
``salvataggi-worktrees-20261021/ondata3/N78-1-analisi.md`` § 8). An ADJUSTMENT with a NEGATIVE quantity has no value: it
only lowers the quantity. Whatever ``cost_basis_override`` the row holds in the database — an old row, a 1.2.1 install,
a row decision 47 converted at the average cost — is ignored by every engine:
- no capital flow: the capital (``total_invested``) does not move, and TWRR/MWRR see no flow that day;
- the Dashboard realizes 0 − the historical cost the pool gives up (the average cost × q), proceeds 0, as the FIFO lots
  already close such a row at 0 (realized −cost);
- the average cost (PMC) never changes on an exit.
Unchanged, and pinned elsewhere as guards: an ADJUSTMENT-in with a cost (a capital contribution), the J-10 scope-boundary
readings (``financial_math/lots/scope_boundary.py``: a TRANSFER leg leaving the scope, read at the market value of its
day — test_lots_transfer_scope_boundary.py, test_lots_scope_boundary.py).

Before N78-1 — CP-16 (decision 47, J-11) and J-24 — the row's value was handed over: the capital fell by it, the Dashboard
realized it less the historical cost, and the lots closed at it. This file pinned that; its tests are now inverted to the
decision and RED until its cure. Each docstring keeps what its test read before.

THE SCENARIO — the S7 book of test_orphan_transfer_after_broker_delete.py, with the outgoing leg written as the
ADJUSTMENT decision 47 used to make of it. One user owns broker A, 100 %. On 1 Oct 2018 A receives 200 EUR and buys 10 X
for 200 EUR, 20 EUR a unit. On 3 Oct an ADJUSTMENT −4 X stores cost_basis_override 20 — per unit (db/models.py) — and
cost_basis_currency EUR. X is quoted 25 EUR on 3 Oct and 30 EUR on 5 Oct. Both readings are in EUR, in A's scope, up to
5 Oct.

(a) Dashboard — PortfolioService.get_summary. The ADJUSTMENT −4 moves no capital: invested 200, net worth 6 × 30 = 180
    (no cash: 200 − 200), P&L −20; realized 0 − 4 × 20 = −80, nothing else. Before N78-1: invested 120 (200 − 4 × 20),
    P&L 60, realized 0.
(b) Lots — LotsAnalysisService.get_lots_analysis, LOT_SUMMARY: COMPLETE, one LONG lot, the BUY's. The 4 units close at
    0: proceeds 0, realized −80; open 6, open value 180, pnl 180 + 0 − 200 = −20, market_pnl −20 − (−80) = 60,
    total_pnl −20. Before N78-1 (CP-16): proceeds 80, realized 0, pnl 60, total 60 (market 60 either way).
(c) The lot's total_pnl is the Dashboard's P&L, and its realized the Dashboard's: −20 and −80 on both sides. Before:
    60 and 0 on both sides.

No screen writes a cost on a negative ADJUSTMENT, and after N78-1 the API refuses one (``costBasisNotAllowed``): the
rows are written straight into the session — no transaction validation, as an old row or a 1.2.1 install holds them —
and never committed: the ``session`` fixture rolls back, so nothing outlives the test. Each test owns its user, broker
and asset, named with a unique marker; the prices it writes are its asset's.

THE FOREIGN BOOK (TestForeignAdjustmentOutIgnoresItsStoredValue) — the same in another currency. One user owns broker A′,
100 %. On 5 Nov 2018 A′ receives 1000 USD and buys 10 X′ — a USD asset — for 1000 USD, 100 USD a unit, when
1 EUR = 1.25 USD (1 USD = 0.80 EUR): capital 800 EUR, the pool's cost 800 EUR. On 7 Nov an ADJUSTMENT −10 X′ stores
cost_basis_override 100 USD, when 1 EUR = 1.60 USD. No price is written: nothing is held after 7 Nov. Both readings in
EUR, up to 9 Nov.
(d) Dashboard: invested 800, net worth 0, P&L −800; the period's P&L −800, realized 0 − 800 = −800, other 0. No rate
    of 7 Nov is needed. Before N78-1 (J-24): invested 175 (800 − 625), P&L −175, realized −175.
(e) Lots: one LONG lot, closed — cost 800, proceeds 0, realized −800, total P&L −800. Before (CP-7a): proceeds 625,
    realized −175.
(f) The parity: the Dashboard's realized and P&L are the lot's, −800 and −800. Before: −175 and −175.
FX rows: the book reads two EUR/USD rates, on its own days, which it writes. ``fx_rates`` is global and unique on
(date, base, quote): a neighbour's row on those keys is deleted first, inside the same rolled-back transaction, so it
comes back intact afterwards and the test never reads a rate it did not write (the pattern of
test_lots_analysis_service.py, ``_own_fx_rate``).

THE EXAMPLE OF THE DECISION (TestTheExampleOfTheDecision) — the developer's own: one user owns broker E, 100 %. On 8 Oct
2018 E receives 500 EUR and buys 10 Z at 50 (X quoted 50 that day); Z is quoted 80 on 9 and 10 Oct; on 10 Oct an
ADJUSTMENT −2 Z — once WITHOUT a value, once storing 50 EUR a unit (the average), once 80 (the market): the three must
read the SAME numbers. Quantity 8, PMC 50; capital (invested) 500; realized −100 (Dashboard and lots); market value 640,
unrealized 8 × (80 − 50) = 240; «other» 0; total P&L 640 − 500 = 140; the day's TWRR (10 Oct, NAV 800 → 640, no flow)
−20 %. Before N78-1 only the row without a value read so on capital and TWRR, and its realized was 0 with −100 in
«other»; the row at 50 read capital 400, P&L 240, TWRR −7.5 %; the row at 80 capital 340, realized +60, P&L 300, TWRR 0.
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
from backend.test_scripts.test_services._lots_steps import daily_points
from backend.test_scripts.test_utils import print_section, print_success

REPORT = "EUR"
FUNDING_DAY = date(2018, 10, 1)  # A: +200 EUR, then 10 X for 200 EUR — 20 EUR a unit
HANDOVER_DAY = date(2018, 10, 3)  # the ADJUSTMENT −4 storing 20 EUR a unit
READING_DAY = date(2018, 10, 5)  # date_to of both readings
PRICES = {HANDOVER_DAY: "25", READING_DAY: "30"}
COST_PER_UNIT = "20"  # the pool's average cost on 3 Oct, 200 / 10: the value decision 47 used to write on the row

# (a) The Dashboard of A: the ADJUSTMENT −4 moves no capital and realizes 0 − 4 × 20.
DASHBOARD = {
    "total_invested": Decimal("200"),  # 200 deposited; nothing distributed (before N78-1: 120, 200 − 4 × 20)
    "net_worth": Decimal("180"),  # 6 × 30, and no cash: 200 − 200
    "total_gain_loss": Decimal("-20"),  # 180 − 200 (before N78-1: 60)
    "period_realized_gain_loss": Decimal("-80"),  # 0 − 4 × 20, the cost the pool gives up (before N78-1: 0, 80 − 80)
    "period_other_result": Decimal("0"),  # the realized holds the −80 (before N78-1: 0 as well)
}

# (b) The lots of X in A: the BUY's lot closes 4 units at 0.
LOTS = {
    "calculation_status": "COMPLETE",
    "lots": [
        {
            "opens on": "the BUY",
            "direction": "LONG",
            "open_quantity": Decimal("6"),  # 10 − 4
            "cumulative_proceeds": Decimal("0"),  # no value leaves (before N78-1: 80, 4 × 20)
            "realized_pnl": Decimal("-80"),  # 4 × (0 − 20) (before N78-1: 0)
            "pnl": Decimal("-20"),  # 6 × 30 + 0 − 200 (before N78-1: 60)
            "market_pnl": Decimal("60"),  # pnl − realized: 60 either way
            "total_pnl": Decimal("-20"),  # market + realized + 0 of income (before N78-1: 60)
        }
    ],
}

# The foreign book: X′ quoted in USD, read in EUR. FxRate stores the pair as EUR/USD (base < quote):
# 1 EUR = rate USD, so 1 USD = 1 / rate EUR — 0.80 on the purchase day, 0.625 on the day of the exit.
FX_ASSET_CURRENCY = "USD"
FX_BUY_DAY = date(2018, 11, 5)  # A′: +1000 USD, then 10 X′ for 1000 USD — 100 USD a unit
FX_HANDOVER_DAY = date(2018, 11, 7)  # the ADJUSTMENT −10 storing 100 USD a unit
FX_READING_DAY = date(2018, 11, 9)  # date_to of both readings
FX_EUR_USD_RATES = {FX_BUY_DAY: "1.25", FX_HANDOVER_DAY: "1.6"}

# (d) The Dashboard of A′: the 10 units leave without a value; the pool gives up 1000 USD × 0.80 = 800 EUR.
FX_DASHBOARD = {
    "total_invested": Decimal("800"),  # 800 deposited (1000 USD at 0.80), nothing distributed (before N78-1: 175)
    "net_worth": Decimal("0"),  # no units, no cash: 1000 − 1000 USD
    "total_gain_loss": Decimal("-800"),  # 0 − 800 (before N78-1: −175)
    "period_pnl": Decimal("-800"),  # the period from the first row: NAV 0 − the net flows, 800 (before N78-1: −175)
    "period_realized_gain_loss": Decimal("-800"),  # 0 − C = 0 − 800 (before N78-1: −175, 625 − 800)
    "period_other_result": Decimal("0"),  # the period's P&L is all realized
}

# (e) The lots of X′ in A′: the BUY's lot closes its 10 units at 0.
FX_LOTS = [
    {
        "opens on": "the BUY",
        "direction": "LONG",
        "open_quantity": Decimal("0"),
        "original_cost": Decimal("800"),  # 1000 USD at 0.80, the opening's rate
        "cumulative_proceeds": Decimal("0"),  # no value leaves (before N78-1: 625, 1000 USD at 0.625)
        "realized_pnl": Decimal("-800"),  # 0 − 800 (before N78-1: −175)
        "total_pnl": Decimal("-800"),  # nothing open, no income: the realized (before N78-1: −175)
    }
]

# THE EXAMPLE OF THE DECISION: 10 Z at 50 (500 deposited first), Z worth 80, 2 Z leave.
EXAMPLE_BUY_DAY = date(2018, 10, 8)  # E: +500 EUR, then 10 Z for 500 EUR — 50 EUR a unit
EXAMPLE_EVE_DAY = date(2018, 10, 9)  # Z worth 80: NAV 800
EXAMPLE_EXIT_DAY = date(2018, 10, 10)  # the ADJUSTMENT −2, Z still worth 80: NAV 640; date_to of every reading
EXAMPLE_PRICES = {EXAMPLE_BUY_DAY: "50", EXAMPLE_EVE_DAY: "80", EXAMPLE_EXIT_DAY: "80"}
# The value the ADJUSTMENT −2 stores in the database, per unit, in EUR: none, the average cost, the market price.
EXAMPLE_STORED_VALUES = [
    pytest.param(None, id="without-a-value"),
    pytest.param("50", id="stored-at-the-average-50"),
    pytest.param("80", id="stored-at-the-market-80"),
]
# The Dashboard of E up to the exit day, from its first row: the same for the three rows.
EXAMPLE_DASHBOARD = {
    "total_invested": Decimal("500"),  # 500 deposited; the exit moves no capital (before: 400 at 50, 340 at 80)
    "market_value": Decimal("640"),  # 8 × 80
    "net_worth": Decimal("640"),  # and no cash: 500 − 500
    "total_gain_loss": Decimal("140"),  # 640 − 500 (before: 240 at 50, 300 at 80)
    "period_pnl": Decimal("140"),  # NAV 640 − the net flows, 500 (before: 240 at 50, 300 at 80)
    "period_realized_gain_loss": Decimal("-100"),  # 0 − 2 × 50 (before: 0 without a value and at 50, +60 at 80)
    "period_unrealized_gain_loss_end": Decimal("240"),  # 8 × (80 − 50)
    "period_other_result": Decimal("0"),  # (before: −100 without a value)
}
EXAMPLE_HOLDING = {"quantity": Decimal("8"), "wac_per_unit": Decimal("50")}  # the PMC never moves on an exit
EXAMPLE_DAY_TWRR = Decimal("-0.2")  # 10 Oct alone: NAV 800 → 640, no flow (before: −0.075 at 50, 0 at 80)
# The lots of Z in E: the BUY's lot closes 2 units at 0.
EXAMPLE_LOTS = [
    {
        "opens on": "the BUY",
        "direction": "LONG",
        "open_quantity": Decimal("8"),
        "cumulative_proceeds": Decimal("0"),  # (before: 100 at 50, 160 at 80)
        "realized_pnl": Decimal("-100"),  # 2 × (0 − 50) (before: 0 at 50, +60 at 80)
        "pnl": Decimal("140"),  # 8 × 80 + 0 − 500 (before: 240 at 50, 300 at 80)
        "market_pnl": Decimal("240"),  # pnl − realized
        "total_pnl": Decimal("140"),  # the Dashboard's P&L
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
    """One test's user, its broker, its asset, and the broker's two rows on it: the BUY and the outgoing ADJUSTMENT
    (−4 storing 20 EUR in CP-16's book, −10 storing 100 USD in the foreign book, −2 in the example)."""

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


async def _dashboard(session: AsyncSession, book: Book, *, date_to: date = READING_DAY, date_from: date | None = None) -> PortfolioSummary:
    """The Dashboard of the book's broker, in EUR, from ``date_from`` (the first row by default) up to ``date_to`` (CP-16's
    reading day by default)."""
    return await PortfolioService(session).get_summary(user_id=book.user.id, broker_ids=[book.broker.id], target_currency_override=REPORT, date_from=date_from, date_to=date_to)


async def _lots(session: AsyncSession, book: Book, *, date_to: date = READING_DAY, analyses: tuple[LotAnalysisType, ...] = (LotAnalysisType.LOT_SUMMARY,)) -> LotsAnalysisResponse:
    """The lots page of the book's asset at its broker, in EUR, from the first movement to ``date_to``: ``analyses``, the
    lot summary by default."""
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=[book.broker.id],
        date_from=None,
        date_to=date_to,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=list(analyses),
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
    """The foreign book, written straight into the session and flushed, never committed: A′ receives 1000 USD and buys
    10 X′ (a USD asset) with them on 5 Nov, then an ADJUSTMENT −10 storing 100 USD a unit takes them out on 7 Nov. The
    two EUR/USD rates it reads are its own."""
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


async def _example_book(session: AsyncSession, stored_value: str | None) -> Book:
    """The developer's example, written straight into the session and flushed, never committed: E receives 500 EUR and
    buys 10 Z at 50 on 8 Oct; on 10 Oct an ADJUSTMENT −2 Z storing ``stored_value`` EUR a unit — None: no value, the
    row the API saves; 50 or 80: a value an old row or a 1.2.1 install may hold, which the API refuses after N78-1."""
    marker = uuid4().hex[:12]
    user = User(username=f"n78_1_{marker}", email=f"n78_1_{marker}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"N78-1 example E {marker}")
    asset = Asset(display_name=f"N78-1 example Z {marker}", currency=REPORT, asset_type=AssetType.STOCK)
    session.add_all([user, broker, asset])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    session.add_all(PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=REPORT, source_plugin_key="n78_1_example_test") for day, close in EXAMPLE_PRICES.items())
    buy = Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=EXAMPLE_BUY_DAY, quantity=Decimal("10"), amount=Decimal("-500"), currency=REPORT)
    exit_row = Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=EXAMPLE_EXIT_DAY,
        quantity=Decimal("-2"),
        cost_basis_override=None if stored_value is None else Decimal(stored_value),
        cost_basis_currency=None if stored_value is None else REPORT,
    )
    session.add_all([Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=EXAMPLE_BUY_DAY, amount=Decimal("500"), currency=REPORT), buy, exit_row])
    await session.flush()
    return Book(user=user, broker=broker, asset=asset, buy=buy, handover=exit_row)


def _amount(value: Currency | None) -> Decimal | None:
    return None if value is None else value.amount


def _dashboard_view(summary: PortfolioSummary, expected: dict = DASHBOARD) -> dict:
    return {name: _amount(getattr(summary, name)) for name in expected}


def _holding_of_x(summary: PortfolioSummary, book: Book, fields: tuple[str, ...] = ("quantity", "wac_per_unit", "current_value", "gain_loss")) -> list[dict]:
    """The book's holding of its asset at its broker: by default 6 at 20, worth 180, a gain of 60 in CP-16's book."""
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


def _stored(book: Book) -> str:
    """What the book's outgoing ADJUSTMENT stores, for a message."""
    row = book.handover
    return "no value" if row.cost_basis_override is None else f"{row.cost_basis_override} {row.cost_basis_currency} a unit"


# =============================================================================
# CP-16's book: an ADJUSTMENT −4 storing 20 EUR reads as one without a value
# =============================================================================


class TestAdjustmentOutWithAStoredValueNumbers:
    @pytest.mark.asyncio
    async def test_dashboard_keeps_the_capital_and_realizes_minus_the_cost(self, session):
        """(a) RED until N78-1: invested 200, net worth 180 (6 × 30), P&L −20; realized 0 − 4 × 20 = −80, other 0.

        Before N78-1 (CP-16, J-11): invested 120 (200 − 4 × 20, the stored value taken out of the capital), P&L 60,
        realized 0 (80 handed over − 80 of cost).
        """
        print_section("N78-1 (a) — Dashboard of A after the ADJUSTMENT −4 storing 20 EUR")
        book = await _book(session)

        summary = await _dashboard(session, book)
        observed = _dashboard_view(summary)
        print(f"dashboard: {observed}")
        print(f"A's X: {_holding_of_x(summary, book)}")

        assert observed == DASHBOARD, f"N78-1: an ADJUSTMENT −4 storing {_stored(book)} has no value — no capital out, realized 0 − 80; the Dashboard reads {observed}"
        print_success("N78-1 (a): 200 invested, 180 of net worth, −20 of P&L, −80 realized")

    @pytest.mark.asyncio
    async def test_lots_close_the_units_at_zero_whatever_the_row_stores(self, session):
        """(b) RED until N78-1: COMPLETE, one LONG lot — open 6, proceeds 0, realized −80, pnl −20, market 60, total −20.

        Before N78-1 (CP-16) the lot closed at the stored 20: proceeds 80, realized 0, pnl 60, total 60 (market 60).
        """
        print_section("N78-1 (b) — lots of X in A after the ADJUSTMENT −4 storing 20 EUR")
        book = await _book(session)

        response = await _lots(session, book)
        observed = _lots_view(response, book)
        print(f"lots: {observed}")
        print(f"issue codes: {_issue_codes(response)}")

        assert observed == LOTS, f"N78-1: the lots close the 4 units at 0 whatever the row stores ({_stored(book)}); they read {observed}"
        print_success("N78-1 (b): the BUY's lot closes 4 at 0 — realized −80, proceeds 0, total −20")

    @pytest.mark.asyncio
    async def test_the_lots_total_pnl_and_realized_are_the_dashboards(self, session):
        """(c) RED until N78-1: the BUY's lot reads the Dashboard's P&L and realized, −20 and −80 on both sides.

        Before N78-1: 60 and 0 on both sides — equal, but at the stored value.
        """
        print_section("N78-1 (c) — the lot's total P&L and realized against the Dashboard's")
        book = await _book(session)

        summary = await _dashboard(session, book)
        lots = [lot for lot in (await _lots(session, book)).lots or [] if lot.opening_transaction_id == book.buy.id]
        observed = {
            "Dashboard": {"P&L": _amount(summary.total_gain_loss), "realized": _amount(summary.period_realized_gain_loss)},
            "the BUY's lot": [{"P&L": lot.total_pnl, "realized": lot.realized_pnl} for lot in lots],
        }
        print(f"parity: {observed}")

        expected = {"P&L": Decimal("-20"), "realized": Decimal("-80")}
        assert observed == {"Dashboard": expected, "the BUY's lot": [expected]}
        print_success("N78-1 (c): lots and Dashboard both read −20 of P&L, −80 realized")


# =============================================================================
# The foreign book: an ADJUSTMENT −10 storing 100 USD, read in EUR, reads as one without a value
# =============================================================================


class TestForeignAdjustmentOutIgnoresItsStoredValue:
    @pytest.mark.asyncio
    async def test_dashboard_keeps_the_capital_and_realizes_minus_the_historical_cost(self, session):
        """(d) RED until N78-1: invested 800, net worth 0, P&L −800; the period's P&L −800, realized −800, other 0.

        Before N78-1 (J-24): invested 175 (800 − 625, the stored 1000 USD at 0.625), P&L −175, realized −175.
        """
        print_section("N78-1 (d) — Dashboard of A′ after the ADJUSTMENT −10 storing 100 USD, in EUR")
        book = await _foreign_book(session)

        observed = _fx_dashboard_view(await _dashboard(session, book, date_to=FX_READING_DAY))
        print(f"dashboard: {observed}")

        assert observed == FX_DASHBOARD, f"N78-1: an ADJUSTMENT −10 storing {_stored(book)} has no value — no capital out, realized 0 − 800; the Dashboard reads {observed}"
        print_success("N78-1 (d): 800 invested, 0 of net worth, −800 of P&L, all of it realized")

    @pytest.mark.asyncio
    async def test_lots_close_the_units_at_zero_in_another_currency(self, session):
        """(e) RED until N78-1: one LONG lot, closed — cost 800 at the opening's rate, proceeds 0, realized −800, total
        P&L −800.

        Before N78-1 (CP-7a): proceeds 625 (1000 USD at the exit day's 0.625), realized −175, total −175.
        """
        print_section("N78-1 (e) — lots of X′ in A′ after the ADJUSTMENT −10 storing 100 USD, in EUR")
        book = await _foreign_book(session)

        response = await _lots(session, book, date_to=FX_READING_DAY)
        observed = _fx_lots_view(response, book)
        print(f"lots: {observed}")
        print(f"issue codes: {_issue_codes(response)}")

        assert observed == FX_LOTS, f"N78-1: the lots close the 10 units at 0 whatever the row stores ({_stored(book)}); they read {observed}"
        print_success("N78-1 (e): the BUY's lot closes 10 at 0 — cost 800, proceeds 0, realized −800")

    @pytest.mark.asyncio
    async def test_the_dashboards_realized_is_the_lots_realized(self, session):
        """(f) RED until N78-1: one lot, so the Dashboard reads the lot's realized and P&L — −800 and −800 on both sides.

        Before N78-1 (J-24): −175 and −175 on both sides — equal, but at the stored value.
        """
        print_section("N78-1 (f) — the Dashboard's realized and P&L against the lot's")
        book = await _foreign_book(session)

        summary = await _dashboard(session, book, date_to=FX_READING_DAY)
        lots = [lot for lot in (await _lots(session, book, date_to=FX_READING_DAY)).lots or [] if lot.opening_transaction_id == book.buy.id]
        assert len(lots) == 1, f"precondition: one lot, opened by the BUY — got {lots}"
        (lot,) = lots
        observed = {
            "Dashboard": {"realized": _amount(summary.period_realized_gain_loss), "P&L": _amount(summary.total_gain_loss)},
            "the BUY's lot": {"realized": lot.realized_pnl, "P&L": lot.total_pnl},
        }
        print(f"parity: {observed}")

        expected = {"realized": Decimal("-800"), "P&L": Decimal("-800")}
        assert observed == {"Dashboard": expected, "the BUY's lot": expected}
        print_success("N78-1 (f): Dashboard and lots both realize −800")


# =============================================================================
# The developer's example: 10 at 50, worth 80, ADJUSTMENT −2 — the same numbers whatever the row stores
# =============================================================================


class TestTheExampleOfTheDecision:
    """N78-1, the developer's example (module docstring): the three rows — no value, 50 stored, 80 stored — read the same
    Dashboard, the same lots and the same day's TWRR. RED until the cure for the rows storing a value, and, for the row
    without one, on the realized (Dashboard −100 against 0 today, the −100 sitting in «other»)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stored_value", EXAMPLE_STORED_VALUES)
    async def test_dashboard_reads_the_same_numbers_whatever_the_row_stores(self, session, stored_value):
        """Capital 500, market value and net worth 640, P&L 140 (the period's too), realized −100, unrealized 240,
        other 0; Z held 8 at a PMC of 50.

        Before N78-1: without a value capital 500 and P&L 140, but realized 0 and other −100; storing 50 capital 400 and
        P&L 240; storing 80 capital 340, realized +60 and P&L 300.
        """
        print_section(f"N78-1 example — Dashboard of E after the ADJUSTMENT −2 ({stored_value or 'no value'})")
        book = await _example_book(session, stored_value)

        summary = await _dashboard(session, book, date_to=EXAMPLE_EXIT_DAY)
        observed = {**_dashboard_view(summary, EXAMPLE_DASHBOARD), "Z held": _holding_of_x(summary, book, tuple(EXAMPLE_HOLDING))}
        print(f"dashboard: {observed}")

        assert observed == {**EXAMPLE_DASHBOARD, "Z held": [EXAMPLE_HOLDING]}, f"N78-1: the ADJUSTMENT −2 storing {_stored(book)} must read as one without a value; the Dashboard reads {observed}"
        print_success(f"N78-1 example ({stored_value or 'no value'}): 500 invested, 140 of P&L, −100 realized, 240 unrealized, 0 other")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stored_value", EXAMPLE_STORED_VALUES)
    async def test_the_days_twrr_is_minus_twenty_percent_whatever_the_row_stores(self, session, stored_value):
        """The Dashboard from 9 Oct to 10 Oct — the period opens on the NAV of its first day: 800 on 9 Oct, 640 on 10 Oct,
        no flow — TWRR −0.2.

        Before N78-1: −0.2 without a value; storing 50 the day saw a flow of 100 out, (640 + 100) / 800 − 1 = −0.075;
        storing 80 a flow of 160, 0.
        """
        print_section(f"N78-1 example — the day's TWRR of E ({stored_value or 'no value'})")
        book = await _example_book(session, stored_value)

        summary = await _dashboard(session, book, date_from=EXAMPLE_EVE_DAY, date_to=EXAMPLE_EXIT_DAY)
        observed = {"period_nav_start": _amount(summary.period_nav_start), "net_worth": _amount(summary.net_worth), "period_net_flows": _amount(summary.period_net_flows), "twrr": summary.twrr_percent}
        print(f"the day: {observed}")

        assert observed == {"period_nav_start": Decimal("800"), "net_worth": Decimal("640"), "period_net_flows": Decimal("0"), "twrr": EXAMPLE_DAY_TWRR}, f"N78-1: the ADJUSTMENT −2 storing {_stored(book)} is no flow; the day reads {observed}"
        print_success(f"N78-1 example ({stored_value or 'no value'}): NAV 800 → 640, no flow, TWRR −20 %")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stored_value", EXAMPLE_STORED_VALUES)
    async def test_lots_read_the_same_numbers_whatever_the_row_stores(self, session, stored_value):
        """COMPLETE, one LONG lot, the BUY's: open 8, proceeds 0, realized −100, pnl 140, market 240, total 140; and the
        lots' own performance sees no flow on 10 Oct: its cumulative TWRR moves by 640 / 800 − 1 = −0.2 that day.

        Before N78-1: without a value the same; storing 50 proceeds 100, realized 0, total 240; storing 80 proceeds 160,
        realized +60, total 300 — and a flow out on 10 Oct.
        """
        print_section(f"N78-1 example — lots of Z in E ({stored_value or 'no value'})")
        book = await _example_book(session, stored_value)

        response = await _lots(session, book, date_to=EXAMPLE_EXIT_DAY, analyses=(LotAnalysisType.LOT_SUMMARY, LotAnalysisType.PERFORMANCE_HISTORY))
        twrr_by_day = {point.date: point.twrr for point in daily_points(response.performance_history)}
        eve, day = twrr_by_day.get(EXAMPLE_EVE_DAY), twrr_by_day.get(EXAMPLE_EXIT_DAY)
        day_move = None if eve is None or day is None else (1 + day) / (1 + eve) - 1
        observed = {**_lots_view(response, book), "the day's TWRR in the lots' performance": day_move}
        print(f"lots: {observed}")
        print(f"issue codes: {_issue_codes(response)}; cumulative TWRR by day: {twrr_by_day}")

        assert observed == {"calculation_status": "COMPLETE", "lots": EXAMPLE_LOTS, "the day's TWRR in the lots' performance": EXAMPLE_DAY_TWRR}, f"N78-1: the lots close the 2 units at 0 whatever the row stores ({_stored(book)}), and see no flow; they read {observed}"
        print_success(f"N78-1 example ({stored_value or 'no value'}): realized −100, total 140, the day's TWRR −20 %")

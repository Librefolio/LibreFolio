"""
Average cost in the report currency, through PortfolioService (issue #32, workstream P).

Real test database, real PortfolioService / engine / facade / lots service. Every test opens
its own user, broker and asset, inserts its rows directly with the session (bypassing the
transaction validation on purpose) and never commits: the ``session`` fixture rolls back, so
nothing written here outlives the test and nothing needs deleting.

Five groups:

- ``TestIssue32ReportCurrencyCost`` (S1–S3): the #32 numbers. S1 and S3 are RED before the
  fix (the engine adds a purchase paid in the report currency at cost 0); S2, the same
  history reported in the asset currency, is GREEN before and after.
- ``TestCostDiagnostics`` (S4–S6): a cost that cannot be known is reported, never a silent
  zero. RED before the fix.
- ``TestAverageCostInvariants`` (I1–I7): single-currency figures and the facade/lots contracts
  that must not move. GREEN before and after; exact Decimal equality on finite quotients.
- ``TestLotsAverageCostLines`` (L1–L3): the lots page's WAC lines in the report currency. L1,
  bought with the report currency, is exact without any rate (GREEN before and after); L2, a
  purchase that cannot be converted, is reported (pair, banner issue, DEGRADED) and leaves the
  lines blank until its pool empties — RED before the fix, which drew the unconverted cost; L3,
  an acquisition without cost basis, does the same with a MISSING_COST_BASIS issue for the
  asset — RED before the fix, which counted it at zero cost.
- ``TestPeriodUnrealizedBreakdown`` (B1–B4): the period's unrealized change split by asset
  currency into the assets' own change, the exchange-rate effect on their cost and what cannot
  be split; the rows add up to ``period_unrealized_gain_loss_delta`` exactly. Written after the
  code: GREEN.

FX rows. ``FxRate`` is a global table, unique on (date, base, quote). Every rate written
here is EUR/ISK — a pair no other test stores (test_fx_core.py owns BGN/ISK and CHF/ISK) —
or EUR/TJS (B4, after proving nobody stores a TJS rate or route), and is never committed. The
"missing rate" cases use currencies nobody stores a rate or a route for, and verify that as a
precondition instead of assuming it: MNT (S4, I6), BWP (S4b), KGS (S6) and MGA (L2). Not BTN:
test_risk_asset_set.py commits a BTN/EUR rate for the length of its module, and the FX service
backward-fills without limit, so a neighbour's 2007 rate would quietly turn "missing" into
"found".

Pairs. Stored EUR/ISK means 1 EUR = rate ISK, so EUR→ISK multiplies and ISK→EUR divides:
with 125 at the report date, 3125 ISK are exactly 25 EUR.
"""

import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    PriceHistory,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse, PortfolioHolding, PortfolioSummary
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math import average_cost
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService, compute_wac_iterative
from backend.test_scripts.test_utils import print_section, print_success

REPORT = "EUR"

# #32 (S1, S2, I5): an ISK asset bought three times with EUR — 100 + 150 + 150 = 400 EUR.
ISSUE_32_BUYS = (
    (date(2021, 3, 1), "10", "-100"),
    (date(2021, 6, 1), "5", "-150"),
    (date(2021, 9, 1), "5", "-150"),
)
ISSUE_32_RATES = {date(2021, 3, 1): "150", date(2021, 6, 1): "140", date(2021, 9, 1): "160", date(2021, 12, 31): "125"}
ISSUE_32_PRICES = {date(2021, 9, 1): "3000", date(2021, 12, 31): "3125"}
ISSUE_32_END = date(2021, 12, 31)

# S3: an opening position on an ISK asset whose cost basis is in EUR.
ADJ_IN_DAY = date(2022, 3, 1)
ADJ_IN_END = date(2022, 12, 30)

# S4: one purchase paid in EUR, one paid in a currency with no rate at all.
T_LEG_EUR_DAY = date(2023, 3, 1)
T_LEG_MNT_DAY = date(2023, 6, 1)
T_LEG_END = date(2023, 12, 29)

# S4b: an opening position whose cost basis is in a currency with no rate at all.
CBO_FX_DAY = date(2023, 4, 3)
CBO_FX_END = date(2023, 11, 30)

# S5: an opening position with no cost basis at all.
NO_COST_DAY = date(2022, 5, 2)
NO_COST_END = date(2022, 10, 31)

# S6: an asset quoted in a currency with no rate at all, observed over June 2021.
PERIOD_FX_BUY = date(2021, 3, 1)
PERIOD_FX_OUTSIDE = date(2021, 4, 15)  # a price, no movement, before the period
PERIOD_FX_FROM = date(2021, 6, 1)
PERIOD_FX_TO = date(2021, 6, 30)

# I1, I4, I7: single currency — BUY 10 for 1000, BUY 10 for 2000, SELL 5 for 1000.
SINGLE_BUY_1 = date(2020, 2, 3)
SINGLE_BUY_2 = date(2020, 4, 1)
SINGLE_SELL = date(2020, 7, 1)
SINGLE_FROM = date(2020, 5, 15)  # between the second purchase and the sale
SINGLE_END = date(2020, 12, 31)

# I2: full exit, then a new pool.
REOPEN_BUY = date(2020, 3, 2)
REOPEN_SELL = date(2020, 6, 1)
REOPEN_REBUY = date(2020, 9, 1)
REOPEN_END = date(2020, 10, 30)

# I3: a 2-for-1 split.
SPLIT_BUY = date(2020, 1, 15)
SPLIT_DAY = date(2020, 3, 16)
SPLIT_END = date(2020, 4, 30)

# I6: facade fail-safe on a payment currency with no rate.
FAIL_SAFE_DAY = date(2023, 2, 1)
FAIL_SAFE_END = date(2023, 2, 28)

# L1: a USD-quoted asset bought twice with EUR, then partly sold.
LOTS_PAID_BUY_1 = date(2019, 5, 6)
LOTS_PAID_BUY_2 = date(2019, 5, 8)
LOTS_PAID_SELL = date(2019, 5, 9)
LOTS_PAID_END = date(2019, 5, 10)

# L2: one pool holding a purchase paid in MGA (no rate at all), emptied, then a new pool.
LOTS_GAP_BUY_EUR = date(2019, 3, 4)
LOTS_GAP_BUY_MGA = date(2019, 3, 6)
LOTS_GAP_SELL_ALL = date(2019, 3, 8)
LOTS_GAP_REBUY = date(2019, 3, 11)
LOTS_GAP_END = date(2019, 3, 12)

# L3: one pool receiving an ADJUSTMENT-in of 5, with or without a cost basis, emptied, then a new pool.
LOTS_UNKNOWN_BUY = date(2019, 8, 5)
LOTS_UNKNOWN_ADJUSTMENT_IN = date(2019, 8, 7)
LOTS_UNKNOWN_SELL_ALL = date(2019, 8, 9)
LOTS_UNKNOWN_REBUY = date(2019, 8, 12)
LOTS_UNKNOWN_END = date(2019, 8, 13)

# B2, B4: the #32 history observed from mid-October — after the last purchase, before the year
# end. Nothing moves between 1 Sep and 31 Dec, so 15 Oct and the day before value alike
# (3000 ISK carried from 1 Sep, 160 ISK/EUR carried from 1 Sep).
BREAKDOWN_FROM = date(2021, 10, 15)

# B4: a TJS-quoted asset bought with EUR before any TJS rate exists; the TJS rates start after
# BREAKDOWN_FROM. 1 EUR = rate TJS.
TJS_BUYS = ((date(2021, 4, 1), "10", "-100"), (date(2021, 5, 3), "10", "-300"))
TJS_RATES = {date(2021, 11, 15): "12.5", date(2021, 12, 31): "10"}
TJS_PRICES = {date(2021, 12, 31): "150"}


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
    """One test's own user, its single broker (100% OWNER) and its single asset."""

    user: User
    broker: Broker
    asset: Asset
    txs: dict[str, Transaction] = field(default_factory=dict)


async def _open_book(session: AsyncSession, *, asset_currency: str, label: str) -> Book:
    marker = uuid4().hex[:12]
    user = User(username=f"costccy_{marker}", email=f"costccy_{marker}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"CostCcy {label} {marker}")
    asset = Asset(display_name=f"CostCcy {label} {marker}", currency=asset_currency, asset_type=AssetType.STOCK)
    session.add_all([user, broker, asset])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    await session.flush()
    return Book(user=user, broker=broker, asset=asset)


def _tx(book: Book, tx_type: TransactionType, day: date, quantity: str, amount: str = "0", currency: str | None = None, *, cbo: str | None = None, cbo_currency: str | None = None, asset_event_id: int | None = None) -> Transaction:
    return Transaction(
        broker_id=book.broker.id,
        asset_id=book.asset.id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        cost_basis_override=None if cbo is None else Decimal(cbo),
        cost_basis_currency=cbo_currency,
        asset_event_id=asset_event_id,
    )


async def _add_txs(session: AsyncSession, book: Book, **txs: Transaction) -> None:
    session.add_all(txs.values())
    await session.flush()
    book.txs.update(txs)


async def _add_isk_rates(session: AsyncSession, rates: dict[date, str]) -> None:
    """EUR/ISK rows: 1 EUR = rate ISK."""
    session.add_all(FxRate(date=day, base="EUR", quote="ISK", rate=Decimal(rate), source="TEST_COST_CCY") for day, rate in rates.items())
    await session.flush()


async def _add_prices(session: AsyncSession, asset: Asset, closes: dict[date, str]) -> None:
    session.add_all(PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=asset.currency, source_plugin_key="cost_ccy_test") for day, close in closes.items())
    await session.flush()


async def _assert_no_fx_data(session: AsyncSession, currency: str) -> None:
    """Precondition of every 'missing rate' case: no rate and no route for {currency}/EUR exist, committed by anyone."""
    base, quote = sorted((currency, REPORT))
    rates = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == base, FxRate.quote == quote))).scalar_one()
    routes = (await session.execute(select(func.count()).select_from(FxConversionRoute).where(or_(and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote), and_(FxConversionRoute.base == quote, FxConversionRoute.quote == base))))).scalar_one()
    assert (rates, routes) == (0, 0), f"precondition broken: {base}/{quote} has {rates} rate(s) and {routes} route(s) — this case needs a pair nobody stores"


async def _seed_issue_32(session: AsyncSession) -> Book:
    book = await _open_book(session, asset_currency="ISK", label="issue32")
    await _add_isk_rates(session, ISSUE_32_RATES)
    await _add_prices(session, book.asset, ISSUE_32_PRICES)
    await _add_txs(session, book, **{f"buy{index}": _tx(book, TransactionType.BUY, day, quantity, paid, "EUR") for index, (day, quantity, paid) in enumerate(ISSUE_32_BUYS, start=1)})
    return book


async def _seed_single_currency(session: AsyncSession) -> Book:
    book = await _open_book(session, asset_currency="EUR", label="single")
    await _add_prices(session, book.asset, {SINGLE_BUY_2: "160", SINGLE_END: "180"})
    await _add_txs(
        session,
        book,
        buy1=_tx(book, TransactionType.BUY, SINGLE_BUY_1, "10", "-1000", "EUR"),
        buy2=_tx(book, TransactionType.BUY, SINGLE_BUY_2, "10", "-2000", "EUR"),
        sell=_tx(book, TransactionType.SELL, SINGLE_SELL, "-5", "1000", "EUR"),
    )
    return book


async def _summary(session: AsyncSession, book: Book, *, currency: str = REPORT, date_to: date, date_from: date | None = None) -> PortfolioSummary:
    return await PortfolioService(session).get_summary(user_id=book.user.id, target_currency_override=currency, date_from=date_from, date_to=date_to)


def _holding(summary: PortfolioSummary, book: Book) -> PortfolioHolding:
    rows = [holding for holding in summary.holdings if holding.asset_id == book.asset.id and holding.broker_id == book.broker.id]
    assert len(rows) == 1, f"expected one holding for asset {book.asset.id} at broker {book.broker.id}, got {len(rows)}"
    return rows[0]


def _amount(value: Currency | None) -> Decimal | None:
    return None if value is None else value.amount


def _missing_dates(summary: PortfolioSummary, pair: str) -> set[date]:
    return {day for item in summary.missing_fx_pairs if item.pair == pair for day in item.dates}


def _mentions(summary: PortfolioSummary, currency: str) -> list[str]:
    """Every FX diagnostic of the summary that names ``currency``: the missing pairs and the data-quality issues."""
    found = [f"missing_fx_pairs {item.pair}" for item in summary.missing_fx_pairs if currency in item.pair]
    quality = summary.data_quality
    if quality is not None:
        found += [f"data_quality.missing_fx_pairs {item.pair}" for item in quality.missing_fx_pairs if currency in item.pair]
        for issue in quality.issues:
            texts = [*issue.affected_fx_pairs, *(str(value) for value in issue.message_params.values())]
            found += [f"issue {issue.code}: {text}" for text in texts if currency in text]
    return found


async def _lots_wac_lines(session: AsyncSession, book: Book, *, date_to: date) -> LotsAnalysisResponse:
    """The lots page's two WAC lines for the book's asset, in the report currency, from the first movement."""
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=None,
        date_from=None,
        date_to=date_to,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
    )


def _wac_lines(response: LotsAnalysisResponse, book: Book) -> dict[str, dict[date, tuple[Decimal, Decimal]]]:
    """Both lines as {date: (WAC, pool quantity)}: the book's broker line and the cumulative one."""
    return {
        "broker": {point.date: (point.wac, point.pool_qty) for point in response.broker_wac_history or [] if point.broker_id == book.broker.id},
        "cumulative": {point.date: (point.wac, point.pool_qty) for point in response.cumulative_wac_history or []},
    }


def _breakdown(summary: PortfolioSummary) -> list[tuple[str, str, str, Decimal]]:
    """``period_unrealized_breakdown`` as (kind, asset currency, amount currency, amount), in the order given."""
    return [(row.kind, row.asset_currency, row.period_delta.code, row.period_delta.amount) for row in summary.period_unrealized_breakdown]


@dataclass
class _NoConversionProbe:
    """Stands in for ``average_cost.convert_bulk`` where nothing may be converted: records the call, then fails."""

    calls: list[tuple[tuple, dict]] = field(default_factory=list)

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("convert_bulk must not be called: every amount is already in the report currency")


# =============================================================================
# S1–S3 — #32: what was paid, in the report currency
# =============================================================================


class TestIssue32ReportCurrencyCost:
    @pytest.mark.asyncio
    async def test_s1_issue_32_report_in_the_payment_currency_costs_what_was_paid(self, session):
        """S1 (RED before the fix): an ISK asset bought for 400 EUR, Dashboard in EUR → purchase cost 400, not 0."""
        print_section("S1 — #32 report in EUR")
        book = await _seed_issue_32(session)

        summary = await _summary(session, book, date_to=ISSUE_32_END)

        holding = _holding(summary, book)
        observed = {
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "current_value": holding.current_value,
            "gain_loss": holding.gain_loss,
            "FX diagnostics naming ISK": _mentions(summary, "ISK"),
        }
        assert observed == {
            "open_cost_basis": Decimal("400"),
            "wac_per_unit": Decimal("20"),
            "current_value": Decimal("500"),  # 20 × 3125 ISK / 125
            "gain_loss": Decimal("100"),
            "FX diagnostics naming ISK": [],
        }
        print_success("S1: 400 EUR paid, 20 per unit, 100 unrealized")

    @pytest.mark.asyncio
    async def test_s2_issue_32_report_in_the_asset_currency_is_unchanged(self, session):
        """S2 (GREEN before and after): the same history reported in ISK — each EUR payment at its own date's rate."""
        print_section("S2 — #32 report in ISK")
        book = await _seed_issue_32(session)

        summary = await _summary(session, book, currency="ISK", date_to=ISSUE_32_END)

        holding = _holding(summary, book)
        observed = {
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "current_value": holding.current_value,
            "gain_loss": holding.gain_loss,
        }
        assert observed == {
            "open_cost_basis": Decimal("60000"),  # 100×150 + 150×140 + 150×160
            "wac_per_unit": Decimal("3000"),
            "current_value": Decimal("62500"),
            "gain_loss": Decimal("2500"),
        }
        print_success("S2: 60000 ISK, 3000 per unit")

    @pytest.mark.asyncio
    async def test_s3_opening_position_costed_in_the_report_currency_is_capital_not_profit(self, session):
        """S3 (RED before the fix): ADJUSTMENT-in of 10 ISK-quoted units at 12 EUR each, worth 200 EUR at the end."""
        print_section("S3 — in-kind opening cost in EUR on an ISK asset")
        book = await _open_book(session, asset_currency="ISK", label="adj-in-eur")
        await _add_isk_rates(session, {ADJ_IN_DAY: "150", ADJ_IN_END: "125"})
        await _add_prices(session, book.asset, {ADJ_IN_DAY: "1800", ADJ_IN_END: "2500"})
        await _add_txs(session, book, opening=_tx(book, TransactionType.ADJUSTMENT, ADJ_IN_DAY, "10", "0", None, cbo="12", cbo_currency="EUR"))

        summary = await _summary(session, book, date_to=ADJ_IN_END)

        observed = {
            "market_value": _amount(summary.market_value),
            "open_cost_basis": _amount(summary.open_cost_basis),
            "total_invested": _amount(summary.total_invested),
            "total_gain_loss": _amount(summary.total_gain_loss),
        }
        assert observed == {
            "market_value": Decimal("200"),  # 10 × 2500 ISK / 125
            "open_cost_basis": Decimal("120"),
            "total_invested": Decimal("120"),  # the in-kind contribution is capital…
            "total_gain_loss": Decimal("80"),  # …so only 200 − 120 is profit
        }
        print_success("S3: 120 EUR of in-kind capital, 80 EUR of gain")


# =============================================================================
# S4–S6 — a cost that cannot be known is reported, never a silent zero
# =============================================================================


class TestCostDiagnostics:
    @pytest.mark.asyncio
    async def test_s4_purchase_paid_in_an_unconvertible_currency_leaves_the_cost_incomplete(self, session):
        """S4 (RED before the fix): the MNT purchase adds quantity, not cost; the row has no WAC and no P&L; MNT/EUR is reported."""
        print_section("S4 — T-leg conversion missing")
        await _assert_no_fx_data(session, "MNT")
        book = await _open_book(session, asset_currency="ISK", label="t-leg-missing")
        await _add_isk_rates(session, {T_LEG_EUR_DAY: "150", T_LEG_END: "125"})
        await _add_prices(session, book.asset, {T_LEG_END: "2500"})
        await _add_txs(
            session,
            book,
            paid_in_eur=_tx(book, TransactionType.BUY, T_LEG_EUR_DAY, "10", "-100", "EUR"),
            paid_in_mnt=_tx(book, TransactionType.BUY, T_LEG_MNT_DAY, "10", "-50", "MNT"),
        )

        summary = await _summary(session, book, date_to=T_LEG_END)

        holding = _holding(summary, book)
        observed = {
            "current_value": holding.current_value,
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "gain_loss": holding.gain_loss,
            "MNT/EUR reported on the MNT purchase day": T_LEG_MNT_DAY in _missing_dates(summary, "MNT/EUR"),
        }
        assert observed == {
            "current_value": Decimal("400"),  # 20 × 2500 ISK / 125: the valuation itself is complete
            "open_cost_basis": Decimal("100"),  # the known part
            "wac_per_unit": None,
            "gain_loss": None,
            "MNT/EUR reported on the MNT purchase day": True,
        }
        print_success("S4: 100 EUR known, row incomplete, MNT/EUR reported")

    @pytest.mark.asyncio
    async def test_s4b_opening_cost_in_an_unconvertible_currency_reaches_the_banner(self, session):
        """S4b (RED before the fix — silent today): a BWP cost basis with no BWP rate is a missing pair on the banner."""
        print_section("S4b — cost basis in a currency without rates")
        await _assert_no_fx_data(session, "BWP")
        book = await _open_book(session, asset_currency="ISK", label="cbo-missing")
        await _add_isk_rates(session, {CBO_FX_DAY: "150", CBO_FX_END: "125"})
        await _add_prices(session, book.asset, {CBO_FX_END: "2500"})
        await _add_txs(session, book, opening=_tx(book, TransactionType.ADJUSTMENT, CBO_FX_DAY, "10", "0", None, cbo="1000", cbo_currency="BWP"))

        summary = await _summary(session, book, date_to=CBO_FX_END)

        holding = _holding(summary, book)
        issues = summary.data_quality.issues if summary.data_quality is not None else []
        observed = {
            "current_value": holding.current_value,
            "open_cost_basis": _amount(summary.open_cost_basis),
            "BWP/EUR reported on the opening day": CBO_FX_DAY in _missing_dates(summary, "BWP/EUR"),
            "issues naming BWP-EUR": [issue.code for issue in issues if "BWP-EUR" in issue.affected_fx_pairs],
            "wac_per_unit": holding.wac_per_unit,
            "gain_loss": holding.gain_loss,
        }
        assert observed == {
            "current_value": Decimal("200"),
            "open_cost_basis": Decimal("0"),
            "BWP/EUR reported on the opening day": True,
            "issues naming BWP-EUR": ["MISSING_FX_MARKET"],  # no route for the pair (precondition)
            "wac_per_unit": None,
            "gain_loss": None,
        }
        print_success("S4b: BWP/EUR on the banner, row incomplete")

    @pytest.mark.asyncio
    async def test_s5_acquisition_without_cost_basis_raises_missing_cost_basis(self, session):
        """S5 (RED before the fix): an ADJUSTMENT-in without cost basis costs zero, says so, and has no WAC nor P&L."""
        print_section("S5 — MISSING_COST_BASIS")
        book = await _open_book(session, asset_currency="EUR", label="no-cost-basis")
        await _add_prices(session, book.asset, {NO_COST_END: "30"})
        await _add_txs(session, book, opening=_tx(book, TransactionType.ADJUSTMENT, NO_COST_DAY, "10", "0", None))

        summary = await _summary(session, book, date_to=NO_COST_END)

        holding = _holding(summary, book)
        issues = summary.data_quality.issues if summary.data_quality is not None else []
        observed = {
            "current_value": holding.current_value,
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "gain_loss": holding.gain_loss,
            "MISSING_COST_BASIS issues": [
                {
                    "severity": issue.severity,
                    "message_i18n_key": issue.message_i18n_key,
                    "message_params": issue.message_params,
                    "affected_asset_ids": issue.affected_asset_ids,
                    "affected_asset_names": issue.affected_asset_names,
                    "cta_action": issue.cta_action,
                    "group_key": issue.group_key,
                }
                for issue in issues
                if issue.code == "MISSING_COST_BASIS"
            ],
        }
        # The whole portfolio belongs to this test, so "one asset" is a count it created.
        assert observed == {
            "current_value": Decimal("300"),
            "open_cost_basis": Decimal("0"),
            "wac_per_unit": None,
            "gain_loss": None,
            "MISSING_COST_BASIS issues": [
                {
                    "severity": "warning",
                    "message_i18n_key": "dataQuality.missingCostBasis",
                    "message_params": {"count": 1},
                    "affected_asset_ids": [book.asset.id],
                    "affected_asset_names": [book.asset.display_name],
                    "cta_action": "navigate_asset",
                    "group_key": "missing_cost_basis",
                }
            ],
        }
        print_success("S5: MISSING_COST_BASIS for the asset, row incomplete")

    @pytest.mark.asyncio
    async def test_s6_engine_fx_failures_surface_with_movement_dates_and_in_period_valuations(self, session):
        """S6 (RED before the fix): a KGS asset bought with 100 EUR, observed over June with no KGS rate at all."""
        print_section("S6 — engine FX failures on the banner")
        await _assert_no_fx_data(session, "KGS")
        book = await _open_book(session, asset_currency="KGS", label="period-fx")
        await _add_prices(session, book.asset, {PERIOD_FX_BUY: "800", PERIOD_FX_OUTSIDE: "850", PERIOD_FX_TO: "900"})
        await _add_txs(session, book, buy=_tx(book, TransactionType.BUY, PERIOD_FX_BUY, "10", "-100", "EUR"))

        summary = await _summary(session, book, date_from=PERIOD_FX_FROM, date_to=PERIOD_FX_TO)

        kgs_dates = _missing_dates(summary, "KGS/EUR")
        observed = {
            "open_cost_basis": _amount(summary.open_cost_basis),
            "purchase day (asset leg of the cost, any period)": PERIOD_FX_BUY in kgs_dates,
            "first day of the period (valuation, date_from included)": PERIOD_FX_FROM in kgs_dates,
            "last day of the period (valuation)": PERIOD_FX_TO in kgs_dates,
            "valuation day before the period": PERIOD_FX_OUTSIDE in kgs_dates,
            "day before the period": date(2021, 5, 31) in kgs_dates,
        }
        assert observed == {
            "open_cost_basis": Decimal("100"),  # paid in the report currency: known exactly without any KGS rate
            "purchase day (asset leg of the cost, any period)": True,
            "first day of the period (valuation, date_from included)": True,
            "last day of the period (valuation)": True,
            "valuation day before the period": False,
            "day before the period": False,
        }
        print_success("S6: KGS/EUR with the purchase day and the period's valuation days only")


# =============================================================================
# I1–I7 — what must not move
# =============================================================================


class TestAverageCostInvariants:
    @pytest.mark.asyncio
    async def test_i1_single_currency_summary_and_period_contribution(self, session):
        """I1: 10 @ 100 + 10 @ 200, 5 sold for 1000 → 15 units at 150, 250 realized; prices 160 then 180."""
        print_section("I1 — single currency summary + contribution")
        book = await _seed_single_currency(session)
        service = PortfolioService(session)

        summary = await _summary(session, book, date_from=SINGLE_FROM, date_to=SINGLE_END)
        contribution = await service.get_positions_contribution(user_id=book.user.id, date_from=SINGLE_FROM, date_to=SINGLE_END, target_currency_override=REPORT)

        holding = _holding(summary, book)
        rows = [row for row in contribution.positions if row.asset_id == book.asset.id and row.broker_id == book.broker.id]
        assert len(rows) == 1, f"expected one contribution row for the asset, got {len(rows)}"
        row = rows[0]
        observed = {
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "gain_loss": holding.gain_loss,
            "period_realized_gain_loss": _amount(summary.period_realized_gain_loss),
            "period_unrealized_gain_loss_start": _amount(summary.period_unrealized_gain_loss_start),
            "period_unrealized_gain_loss_end": _amount(summary.period_unrealized_gain_loss_end),
            "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta),
            "row.period_realized_gain_loss": row.period_realized_gain_loss,
            "row.start_value": row.start_value,
            "row.end_value": row.end_value,
            "row.period_unrealized_delta": row.period_unrealized_delta,
            "row.period_pnl": row.period_pnl,
            "row.is_fully_sold": row.is_fully_sold,
        }
        assert observed == {
            "open_cost_basis": Decimal("2250"),
            "wac_per_unit": Decimal("150"),
            "gain_loss": Decimal("450"),  # 15 × 180 − 2250
            "period_realized_gain_loss": Decimal("250"),  # 1000 − 5 × 150
            "period_unrealized_gain_loss_start": Decimal("200"),  # 20 × 160 − 3000
            "period_unrealized_gain_loss_end": Decimal("450"),
            "period_unrealized_gain_loss_delta": Decimal("250"),
            "row.period_realized_gain_loss": Decimal("250"),
            "row.start_value": Decimal("3200"),
            "row.end_value": Decimal("2700"),
            "row.period_unrealized_delta": Decimal("250"),
            "row.period_pnl": Decimal("500"),
            "row.is_fully_sold": False,
        }
        print_success("I1: 2250 open, 150 per unit, 250 realized, 200 → 450 unrealized")

    @pytest.mark.asyncio
    async def test_i2_full_exit_then_a_new_pool(self, session):
        """I2: 4 @ 50 sold for 300, then 2 @ 30 — the new pool owes nothing to the old one."""
        print_section("I2 — full exit then new pool")
        book = await _open_book(session, asset_currency="EUR", label="reopen")
        await _add_prices(session, book.asset, {REOPEN_END: "35"})
        await _add_txs(
            session,
            book,
            buy=_tx(book, TransactionType.BUY, REOPEN_BUY, "4", "-200", "EUR"),
            sell=_tx(book, TransactionType.SELL, REOPEN_SELL, "-4", "300", "EUR"),
            rebuy=_tx(book, TransactionType.BUY, REOPEN_REBUY, "2", "-60", "EUR"),
        )

        summary = await _summary(session, book, date_to=REOPEN_END)

        holding = _holding(summary, book)
        observed = {
            "quantity": holding.quantity,
            "wac_per_unit": holding.wac_per_unit,
            "open_cost_basis": _amount(summary.open_cost_basis),
            "gain_loss": holding.gain_loss,
            "period_realized_gain_loss": _amount(summary.period_realized_gain_loss),
        }
        assert observed == {
            "quantity": Decimal("2"),
            "wac_per_unit": Decimal("30"),
            "open_cost_basis": Decimal("60"),
            "gain_loss": Decimal("10"),
            "period_realized_gain_loss": Decimal("100"),
        }
        print_success("I2: 2 units at 30, 100 realized")

    @pytest.mark.asyncio
    async def test_i3_split_rescales_the_pool_without_moving_cost(self, session):
        """I3: 10 @ 100, then a 2-for-1 split (ADJUSTMENT +10 linked to a SPLIT event) → 20 units at 50."""
        print_section("I3 — split")
        book = await _open_book(session, asset_currency="EUR", label="split")
        event = AssetEvent(asset_id=book.asset.id, date=SPLIT_DAY, type=AssetEventType.SPLIT, value=Decimal("2"), currency="EUR")
        session.add(event)
        await session.flush()
        await _add_prices(session, book.asset, {SPLIT_END: "60"})
        await _add_txs(
            session,
            book,
            buy=_tx(book, TransactionType.BUY, SPLIT_BUY, "10", "-1000", "EUR"),
            split=_tx(book, TransactionType.ADJUSTMENT, SPLIT_DAY, "10", "0", "EUR", asset_event_id=event.id),
        )

        summary = await _summary(session, book, date_to=SPLIT_END)

        holding = _holding(summary, book)
        observed = {
            "quantity": holding.quantity,
            "open_cost_basis": _amount(summary.open_cost_basis),
            "wac_per_unit": holding.wac_per_unit,
            "gain_loss": holding.gain_loss,
        }
        assert observed == {
            "quantity": Decimal("20"),
            "open_cost_basis": Decimal("1000"),
            "wac_per_unit": Decimal("50"),
            "gain_loss": Decimal("200"),  # 20 × 60 − 1000
        }
        print_success("I3: 1000 for 20 units, 50 each")

    @pytest.mark.asyncio
    async def test_i4_facade_rows_on_a_single_currency_history(self, session):
        """I4: compute_wac_iterative keeps its rows: add, add, reduce, with unit cost and running WAC."""
        print_section("I4 — facade rows")
        book = await _seed_single_currency(session)

        result = await compute_wac_iterative(session=session, broker_id=book.broker.id, asset_id=book.asset.id, as_of_date=SINGLE_END, asset_currency="EUR", use_cache=False)

        assert result.wac == Currency(code="EUR", amount=Decimal("150"))
        assert [(row.tx_id, row.effect, row.unit_cost, row.running_wac, row.currency) for row in result.wac_qualifying_txs] == [
            (book.txs["buy1"].id, "add", Decimal("100"), Decimal("100"), "EUR"),
            (book.txs["buy2"].id, "add", Decimal("200"), Decimal("150"), "EUR"),
            (book.txs["sell"].id, "reduce", Decimal("150"), Decimal("150"), "EUR"),
        ]
        assert [(row.fx_info, row.fx_rate_used, row.original_unit_cost, row.original_currency) for row in result.wac_qualifying_txs] == [(None, None, None, None)] * 3
        assert result.wac_missing_pairs == []
        print_success("I4: 150 EUR, rows unchanged")

    @pytest.mark.asyncio
    async def test_i5_facade_fx_metadata_in_the_asset_currency(self, session):
        """I5: the #32 history through the facade in ISK — each row carries its own date's rate and provenance."""
        print_section("I5 — facade FX metadata")
        book = await _seed_issue_32(session)

        result = await compute_wac_iterative(session=session, broker_id=book.broker.id, asset_id=book.asset.id, as_of_date=ISSUE_32_END, asset_currency="ISK", target_currency_override="ISK", use_cache=False)

        assert result.wac == Currency(code="ISK", amount=Decimal("3000"))
        rows = [
            (
                row.tx_id,
                row.effect,
                row.unit_cost,
                row.running_wac,
                row.currency,
                row.original_unit_cost,
                row.original_currency,
                row.fx_rate_used,
                row.fx_info.fx_rate_date if row.fx_info else None,
                row.fx_info.fx_days_back if row.fx_info else None,
            )
            for row in result.wac_qualifying_txs
        ]
        assert rows == [
            (book.txs["buy1"].id, "add", Decimal("1500"), Decimal("1500"), "ISK", Decimal("10"), "EUR", Decimal("150"), date(2021, 3, 1), 0),
            (book.txs["buy2"].id, "add", Decimal("4200"), Decimal("2400"), "ISK", Decimal("30"), "EUR", Decimal("140"), date(2021, 6, 1), 0),
            (book.txs["buy3"].id, "add", Decimal("4800"), Decimal("3000"), "ISK", Decimal("30"), "EUR", Decimal("160"), date(2021, 9, 1), 0),
        ]
        assert result.wac_missing_pairs == []
        print_success("I5: 3000 ISK, rates 150/140/160 at their own dates")

    @pytest.mark.asyncio
    async def test_i6_facade_is_fail_safe_on_a_missing_payment_rate(self, session):
        """I6: a payment that cannot be converted gives no WAC at all, never a partial one."""
        print_section("I6 — facade fail-safe")
        await _assert_no_fx_data(session, "MNT")
        book = await _open_book(session, asset_currency="ISK", label="fail-safe")
        await _add_txs(session, book, buy=_tx(book, TransactionType.BUY, FAIL_SAFE_DAY, "10", "-500", "MNT"))

        result = await compute_wac_iterative(session=session, broker_id=book.broker.id, asset_id=book.asset.id, as_of_date=FAIL_SAFE_END, asset_currency="ISK", target_currency_override=REPORT, use_cache=False)

        assert (result.wac, result.wac_qualifying_txs) == (None, [])
        assert result.wac_missing_pairs == [WACMissingPairInfo(pair="MNT/EUR", dates=[FAIL_SAFE_DAY])]
        print_success("I6: wac None, MNT/EUR on the purchase day")

    @pytest.mark.asyncio
    async def test_i7_lots_wac_lines_on_a_single_currency_history(self, session):
        """I7: the lots page's broker and cumulative WAC lines step 100 → 150 → 150 with the pool 10 → 20 → 15."""
        print_section("I7 — lots WAC lines")
        book = await _seed_single_currency(session)

        response = await LotsAnalysisService(session).get_lots_analysis(
            user_id=book.user.id,
            asset_id=book.asset.id,
            broker_ids=None,
            date_from=None,
            date_to=SINGLE_END,
            target_currency=REPORT,
            selected_lot_ids=None,
            requested_analyses=[LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
        )

        broker_line = {point.date: (point.wac, point.pool_qty) for point in response.broker_wac_history or [] if point.broker_id == book.broker.id}
        cumulative_line = {point.date: (point.wac, point.pool_qty) for point in response.cumulative_wac_history or []}
        expected = {
            SINGLE_BUY_1: (Decimal("100"), Decimal("10")),
            SINGLE_BUY_2: (Decimal("150"), Decimal("20")),
            SINGLE_SELL: (Decimal("150"), Decimal("15")),
        }
        assert {day: broker_line.get(day) for day in expected} == expected
        assert {day: cumulative_line.get(day) for day in expected} == expected
        print_success("I7: both WAC lines 100 → 150 → 150")


# =============================================================================
# L1–L3 — the lots page's WAC lines in the report currency
# =============================================================================


class TestLotsAverageCostLines:
    @pytest.mark.asyncio
    async def test_l1_lines_of_an_asset_bought_with_the_report_currency_cost_what_was_paid(self, session, monkeypatch):
        """L1: a USD-quoted asset bought for 200 + 100 EUR and partly sold, lines in EUR → 20 per unit, without any rate."""
        print_section("L1 — lots WAC lines, paid in the report currency")
        probe = _NoConversionProbe()
        monkeypatch.setattr(average_cost, "convert_bulk", probe)
        book = await _open_book(session, asset_currency="USD", label="lots-paid-in-eur")
        await _add_txs(
            session,
            book,
            buy1=_tx(book, TransactionType.BUY, LOTS_PAID_BUY_1, "10", "-200", "EUR"),
            buy2=_tx(book, TransactionType.BUY, LOTS_PAID_BUY_2, "5", "-100", "EUR"),
            sell=_tx(book, TransactionType.SELL, LOTS_PAID_SELL, "-3", "75", "EUR"),
        )

        response = await _lots_wac_lines(session, book, date_to=LOTS_PAID_END)

        line = {
            date(2019, 5, 6): (Decimal("20"), Decimal("10")),
            date(2019, 5, 7): (Decimal("20"), Decimal("10")),
            date(2019, 5, 8): (Decimal("20"), Decimal("15")),
            date(2019, 5, 9): (Decimal("20"), Decimal("12")),
            date(2019, 5, 10): (Decimal("20"), Decimal("12")),
        }
        observed = {
            "lines": _wac_lines(response, book),
            "calculation_status": response.calculation_status,
            "missing_fx_pairs": response.data_quality.missing_fx_pairs if response.data_quality else None,
            "convert_bulk calls": len(probe.calls),
        }
        assert observed == {
            "lines": {"broker": line, "cumulative": line},
            "calculation_status": "COMPLETE",
            "missing_fx_pairs": [],
            "convert_bulk calls": 0,
        }
        print_success("L1: 20 EUR per unit on both lines, no conversion")

    @pytest.mark.asyncio
    async def test_l2_a_purchase_that_cannot_be_converted_is_reported_and_blanks_the_lines_until_the_pool_empties(self, session):
        """L2: 10 for 100 EUR, 10 for 5000 MGA (no MGA rate anywhere), all 20 sold, then 4 for 60 EUR."""
        print_section("L2 — lots WAC lines, a purchase without rate")
        await _assert_no_fx_data(session, "MGA")
        book = await _open_book(session, asset_currency="EUR", label="lots-mga")
        await _add_txs(
            session,
            book,
            buy_eur=_tx(book, TransactionType.BUY, LOTS_GAP_BUY_EUR, "10", "-100", "EUR"),
            buy_mga=_tx(book, TransactionType.BUY, LOTS_GAP_BUY_MGA, "10", "-5000", "MGA"),
            sell_all=_tx(book, TransactionType.SELL, LOTS_GAP_SELL_ALL, "-20", "300", "EUR"),
            rebuy=_tx(book, TransactionType.BUY, LOTS_GAP_REBUY, "4", "-60", "EUR"),
        )

        response = await _lots_wac_lines(session, book, date_to=LOTS_GAP_END)

        # 6 and 7 March: the pool holds the MGA purchase, whose cost is unknown — no point, not a
        # wrong average. From the full sale on, the pool is whole again: 0 while empty, then 60 / 4.
        line = {
            date(2019, 3, 4): (Decimal("10"), Decimal("10")),
            date(2019, 3, 5): (Decimal("10"), Decimal("10")),
            date(2019, 3, 8): (Decimal("0"), Decimal("0")),
            date(2019, 3, 9): (Decimal("0"), Decimal("0")),
            date(2019, 3, 10): (Decimal("0"), Decimal("0")),
            date(2019, 3, 11): (Decimal("15"), Decimal("4")),
            date(2019, 3, 12): (Decimal("15"), Decimal("4")),
        }
        quality = response.data_quality
        assert quality is not None
        observed = {
            "lines": _wac_lines(response, book),
            "missing_fx_pairs": quality.missing_fx_pairs,
            "FX issues": [(issue.code, issue.affected_fx_pairs) for issue in quality.issues if issue.code in ("MISSING_FX_MARKET", "MISSING_FX_RATES")],
            "calculation_status": response.calculation_status,
        }
        assert observed == {
            "lines": {"broker": line, "cumulative": line},
            "missing_fx_pairs": [WACMissingPairInfo(pair="MGA/EUR", dates=[LOTS_GAP_BUY_MGA])],
            "FX issues": [("MISSING_FX_MARKET", ["EUR-MGA"])],  # no route for the pair (precondition)
            "calculation_status": "DEGRADED",
        }
        print_success("L2: MGA/EUR on 6 March, MISSING_FX_MARKET, DEGRADED, no point while the MGA cost is in the pool")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("cbo", "adjustment_points", "expected_issues", "expected_status"),
        [
            pytest.param(None, {}, "missing cost basis", "DEGRADED", id="adjustment-in-without-cost-basis"),
            pytest.param(
                "10",
                {date(2019, 8, 7): (Decimal("10"), Decimal("15")), date(2019, 8, 8): (Decimal("10"), Decimal("15"))},
                "none",
                "COMPLETE",
                id="control-adjustment-in-with-cost-basis",
            ),
        ],
    )
    async def test_l3_an_acquisition_without_cost_basis_is_reported_and_blanks_the_lines_until_the_pool_empties(self, session, cbo, adjustment_points, expected_issues, expected_status):
        """L3: 10 for 100 EUR, 5 in by ADJUSTMENT without a cost basis, all 15 sold, then 4 for 60 EUR.

        A price on the adjustment day gives the FIFO engine an exact reference price for the lot it
        opens, so the engine itself raises nothing: what turns the analysis DEGRADED is the unknown
        cost in the WAC lines, reported as MISSING_COST_BASIS for the asset. The control carries a
        cost basis of 10 EUR per unit: no issue, COMPLETE, and no gap in the lines (150 for 15).
        """
        print_section("L3 — lots WAC lines, an acquisition without cost basis")
        book = await _open_book(session, asset_currency="EUR", label="lots-unknown-cost")
        await _add_prices(session, book.asset, {LOTS_UNKNOWN_ADJUSTMENT_IN: "11"})
        await _add_txs(
            session,
            book,
            buy=_tx(book, TransactionType.BUY, LOTS_UNKNOWN_BUY, "10", "-100", "EUR"),
            adjustment_in=_tx(book, TransactionType.ADJUSTMENT, LOTS_UNKNOWN_ADJUSTMENT_IN, "5", "0", None, cbo=cbo, cbo_currency=None if cbo is None else "EUR"),
            sell_all=_tx(book, TransactionType.SELL, LOTS_UNKNOWN_SELL_ALL, "-15", "180", "EUR"),
            rebuy=_tx(book, TransactionType.BUY, LOTS_UNKNOWN_REBUY, "4", "-60", "EUR"),
        )

        response = await _lots_wac_lines(session, book, date_to=LOTS_UNKNOWN_END)

        # Without a cost basis, 7 and 8 August have no point: the pool holds 5 units of unknown cost.
        line = {
            date(2019, 8, 5): (Decimal("10"), Decimal("10")),
            date(2019, 8, 6): (Decimal("10"), Decimal("10")),
            **adjustment_points,
            date(2019, 8, 9): (Decimal("0"), Decimal("0")),
            date(2019, 8, 10): (Decimal("0"), Decimal("0")),
            date(2019, 8, 11): (Decimal("0"), Decimal("0")),
            date(2019, 8, 12): (Decimal("15"), Decimal("4")),
            date(2019, 8, 13): (Decimal("15"), Decimal("4")),
        }
        missing_cost_basis_issue = {
            "code": "MISSING_COST_BASIS",
            "severity": "warning",
            "message_i18n_key": "dataQuality.missingCostBasis",
            "message_params": {"count": 1},
            "affected_asset_ids": [book.asset.id],
            "affected_asset_names": [book.asset.display_name],
            "cta_action": "navigate_asset",
            "cta_target": str(book.asset.id),
            "group_key": "missing_cost_basis",
        }
        quality = response.data_quality
        assert quality is not None
        observed = {
            "lines": _wac_lines(response, book),
            # Every issue, the engine's included: the unknown cost must be the only one, reported once
            # although it sits in two lines (the broker's and the cumulative one).
            "issues": [{field_name: getattr(issue, field_name) for field_name in missing_cost_basis_issue} for issue in quality.issues],
            "missing_fx_pairs": quality.missing_fx_pairs,
            "calculation_status": response.calculation_status,
        }
        assert observed == {
            "lines": {"broker": line, "cumulative": line},
            "issues": [missing_cost_basis_issue] if expected_issues == "missing cost basis" else [],
            "missing_fx_pairs": [],
            "calculation_status": expected_status,
        }
        print_success(f"L3: {expected_status}, issues: {expected_issues}")


# =============================================================================
# B1–B4 — the period's unrealized change by asset currency
# =============================================================================


class TestPeriodUnrealizedBreakdown:
    @pytest.mark.asyncio
    async def test_b1_issue_32_from_inception_splits_100_into_the_asset_20_and_the_exchange_rate_80(self, session):
        """B1: MV 500 − C_A 60000 ISK × 0.008 = 20, the asset's own change; 480 − C_T 400 = 80, the exchange rate's."""
        print_section("B1 — #32 breakdown, no date_from")
        book = await _seed_issue_32(session)

        summary = await _summary(session, book, date_to=ISSUE_32_END)

        rows = _breakdown(summary)
        observed = {
            "rows": rows,
            "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta),
            "sum of the rows": sum(row[3] for row in rows),
        }
        assert observed == {
            "rows": [("asset", "ISK", "EUR", Decimal("20")), ("fx", "ISK", "EUR", Decimal("80"))],
            "period_unrealized_gain_loss_delta": Decimal("100"),  # from inception: the start values are zero
            "sum of the rows": Decimal("100"),
        }
        print_success("B1: asset ISK 20 + fx ISK 80 = 100")

    @pytest.mark.asyncio
    async def test_b2_issue_32_from_mid_october_rows_add_up_to_the_period_delta(self, session):
        """B2: on 15 Oct MV = C_A × r = 20 × 3000 / 160 = 375 against C_T 400 → asset 0, fx −25; at the year end 20 and 80."""
        print_section("B2 — #32 breakdown from 15 October")
        book = await _seed_issue_32(session)

        summary = await _summary(session, book, date_from=BREAKDOWN_FROM, date_to=ISSUE_32_END)

        rows = _breakdown(summary)
        observed = {
            "rows": rows,
            "period_unrealized_gain_loss_start": _amount(summary.period_unrealized_gain_loss_start),
            "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta),
            "sum of the rows": sum(row[3] for row in rows),
        }
        assert observed == {
            "rows": [("asset", "ISK", "EUR", Decimal("20")), ("fx", "ISK", "EUR", Decimal("105"))],
            "period_unrealized_gain_loss_start": Decimal("-25"),
            "period_unrealized_gain_loss_delta": Decimal("125"),
            "sum of the rows": Decimal("125"),
        }
        print_success("B2: asset ISK +20, fx ISK +105 = 125")

    @pytest.mark.asyncio
    async def test_b3_a_single_currency_portfolio_has_one_asset_row_and_no_exchange_rate_row(self, session):
        """B3: the I1 history in EUR from 15 May 2020 — unrealized 200 → 450, all of it the asset's own change."""
        print_section("B3 — single-currency breakdown")
        book = await _seed_single_currency(session)

        summary = await _summary(session, book, date_from=SINGLE_FROM, date_to=SINGLE_END)

        observed = {"rows": _breakdown(summary), "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta)}
        assert observed == {"rows": [("asset", "EUR", "EUR", Decimal("250"))], "period_unrealized_gain_loss_delta": Decimal("250")}
        print_success("B3: one asset EUR row of 250, no fx row")

    @pytest.mark.asyncio
    async def test_b4_a_currency_without_a_rate_on_the_first_boundary_day_is_unsplit_and_the_rows_still_add_up(self, session):
        """B4: the #32 book plus a TJS asset bought with EUR before any TJS rate exists; TJS rates start on 15 Nov.

        On 15 Oct there is no TJS rate at all, so the TJS position cannot be split; at the year end
        it still cannot, its cost in TJS being unknown (no rate on its purchase days). Its whole
        change is therefore one unsplit row: MV 20 × 150 TJS / 10 = 300 EUR at the end, against
        20 × 30 EUR = 600 EUR on 15 Oct (no TJS quote yet: the last purchase's price) — −300.
        The ISK rows are B2's. Unrealized 175 → 0: the five rows add up to −175.
        """
        print_section("B4 — breakdown with an unsplit currency")
        await _assert_no_fx_data(session, "TJS")
        book = await _seed_issue_32(session)
        tjs_asset = Asset(display_name=f"CostCcy tjs {uuid4().hex[:12]}", currency="TJS", asset_type=AssetType.STOCK)
        session.add(tjs_asset)
        await session.flush()
        session.add_all(FxRate(date=day, base="EUR", quote="TJS", rate=Decimal(rate), source="TEST_COST_CCY") for day, rate in TJS_RATES.items())
        await _add_prices(session, tjs_asset, TJS_PRICES)
        session.add_all(Transaction(broker_id=book.broker.id, asset_id=tjs_asset.id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), amount=Decimal(paid), currency="EUR") for day, quantity, paid in TJS_BUYS)
        await session.flush()

        summary = await _summary(session, book, date_from=BREAKDOWN_FROM, date_to=ISSUE_32_END)

        rows = _breakdown(summary)
        observed = {
            "rows": rows,
            "period_unrealized_gain_loss_start": _amount(summary.period_unrealized_gain_loss_start),
            "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta),
            "sum of the rows": sum(row[3] for row in rows),
        }
        assert observed == {
            "rows": [
                ("asset", "ISK", "EUR", Decimal("20")),
                ("asset", "TJS", "EUR", Decimal("0")),
                ("fx", "ISK", "EUR", Decimal("105")),
                ("fx", "TJS", "EUR", Decimal("0")),
                ("unsplit", "TJS", "EUR", Decimal("-300")),
            ],
            "period_unrealized_gain_loss_start": Decimal("175"),  # ISK −25 + TJS 600 − 400
            "period_unrealized_gain_loss_delta": Decimal("-175"),
            "sum of the rows": Decimal("-175"),
        }
        print_success("B4: TJS unsplit −300; the five rows add up to −175")

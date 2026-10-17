"""
MF-P (workstream MF, lot P, part 1 — R17 and W8): the Dashboard summary's day change, timing effect and holding groups.

``PortfolioService.get_summary`` gains five fields (``schemas/portfolio.py``), every ratio a fraction (0.05 = 5 %),
unrounded:

* R17 — ``pnl_change_1d`` (Currency), ``pnl_change_1d_vs_total_pnl_percent`` and ``pnl_change_1d_vs_nav_percent``:
  ``period.day_change(engine_result.daily_states, valuation_date)``, the engine's states of the valuation date and of
  the calendar day before; the change of ``total_pnl``, and that change over |the day before's total_pnl| and over
  |its NAV| (``returns.change_ratio``: the change's sign, None on a zero base). All three None for a portfolio born on
  the valuation date. The engine always runs from the first transaction, so the period's range does not limit them;
* ``timing_effect_percent`` = ``mwrr_cumulative_percent − twrr_percent`` of the same summary, None when either is;
* W8 — ``holding_groups``: one ``HoldingGroupGainLoss(broker_id, asset_type, gain_loss, gain_loss_percent)`` per broker
  (``asset_type`` None: all its holdings) and per asset type at each broker, ordered by broker_id, the broker's group
  first, then asset_type alphabetically. ``returns.group_gain_loss`` over the holdings' ``(current_value, gain_loss)``:
  only the holdings with both count, on both sides of Σ gain / Σ (value − gain); a group where none counts is
  (None, None).

What the frontend computes today, and where the new fields differ from it:

* KPI day change (``frontend/src/lib/features/dashboard/KpiSection.svelte:79-135``): the last point of the report's
  ``history`` less the point before it (``total_pnl``), over |that point's total_pnl| and |its nav_value|. On a daily
  history that reaches the day before, the same figures (``test_the_report_agrees_with_its_daily_history``); on a range
  of one day the history has one point and today's KPI shows no change, the summary has it
  (``test_a_one_day_range_still_has_the_change``);
* timing: ``mwrr_cumulative − twrr`` — the same;
* treemap group (``ExposureTreemap.svelte:366-450``): Σ gain / (Σ value − Σ gain) over every holding with a value above
  zero, a holding whose gain is unknown still adding its value to the base, and a group without any known gain at 0 %.
  Here two priced holdings of unknown cost (ADJUSTMENTs in without a cost) move broker A's ratio and its STOCK
  group's, and make its FUND group (None, None) instead of 0 %.

Scenarios — report currency EUR, every amount in EUR (no FX rate is read), one user owning 100 % of the test's brokers:

* R17 — one broker; DEPOSIT 10000 and BUY 10 X for 1000 (on 2025-01-02, a Thursday, unless said), X's closes by case
  (``DAY_CASES``): ``weekday`` Thursday 110 / Friday 113; ``loss-shrinks`` 90 / 95 (P&L −100 → −50: +0.5);
  ``zero-pnl-the-day-before`` bought on Thursday 2025-01-30 at 100, Friday 113 (no ratio of a zero P&L);
  ``monday`` Friday 113 / Monday 120, the weekend carrying Friday; ``monday-after-a-weekend-quote`` adds a Saturday quote
  of 116, so Sunday carries Saturday and the change is Monday − Sunday (+40), not Monday − Friday (+70). Born on the
  valuation date: the same ledger, everything on Friday;
* timing — the two ledgers of ``test_portfolio_mwrr_card_and_line.py``: deposits only (MWRR and TWRR both there, and
  different), and net withdrawals (D-MF5: no MWRR, a TWRR still);
* W8 — ``GROUP_HOLDINGS``: broker A holds X, Y (STOCK, bought), U (STOCK, ADJUSTMENT in without a cost, priced:
  value 200, gain None), M (STOCK, ADJUSTMENT in without a cost, no price: MISSING, no value), E (ETF, bought), V (FUND,
  like U: value 300, gain None); broker B holds Z (STOCK, bought), W (BOND, ADJUSTMENT in at 40 a unit, no price:
  ESTIMATED_AT_COST 200, gain 0) and C (CRYPTO, like M). Every group computed by hand in ``GROUPS``.

Red on HEAD (c2feebaa8), every test: the scenario's preconditions read existing fields and hold there, then the first
read of a new field — ``summary.pnl_change_1d``, ``summary.timing_effect_percent``, ``summary.holding_groups`` —
raises AttributeError: ``PortfolioSummary`` has no such attribute on HEAD.

Isolation: every test owns its user, brokers and assets (unique names) and writes only through a session that is rolled
back: nothing is committed. The report (layer 2), WAC and engine blob caches are emptied around each test. Holdings and
groups are found by the test's own broker and asset ids; a history belongs to the test's user alone and is read by date.

Reference: backend/app/services/portfolio_service.py (get_summary), backend/app/services/financial_math/returns.py
(change_ratio, group_gain_loss, timing_effect), backend/app/services/financial_math/portfolio/period.py (day_change).
"""

import sys
from collections.abc import Iterable
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

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioHolding, PortfolioReportQuery, PortfolioReportResponse, PortfolioSummary
from backend.app.services.portfolio_service import PortfolioService

D = Decimal
EUR = "EUR"
ZERO = D("0")

# R17
OPEN_DAY = date(2025, 1, 2)
THURSDAY = date(2025, 1, 30)
FRIDAY = date(2025, 1, 31)
SATURDAY = date(2025, 2, 1)
MONDAY = date(2025, 2, 3)

# Timing: deposits only (DO) and net withdrawals (NW), the ledgers of test_portfolio_mwrr_card_and_line.py.
DO_START = date(2025, 1, 2)
DO_FROM = date(2025, 2, 1)
DO_PRICE_1 = date(2025, 3, 3)
DO_TOP_UP = date(2025, 5, 2)
DO_PRICE_2 = date(2025, 6, 2)
DO_TO = date(2025, 8, 29)
NW_START = date(2025, 1, 2)
NW_PRICE_UP = date(2025, 6, 30)
NW_SELL = date(2025, 7, 1)
NW_WITHDRAWAL = date(2025, 7, 15)
NW_END = date(2025, 9, 30)

# W8
GROUPS_OPEN = date(2025, 1, 2)
GROUPS_VALUATION = date(2025, 1, 31)


# =============================================================================
# HELPERS
# =============================================================================


@dataclass
class _Book:
    """One user owning 100 % of the test's brokers, and the test's EUR assets, each by a label."""

    user: User
    brokers: dict[str, Broker]
    assets: dict[str, Asset]


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


async def _book(session: AsyncSession, keep_alive: list[object], label: str, brokers: tuple[str, ...], assets: dict[str, AssetType]) -> _Book:
    tag = uuid4().hex[:12]
    user = User(username=f"mfp_{label}_{tag}", email=f"mfp_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker_rows = {name: Broker(name=f"MfP {label} {name} {tag}") for name in brokers}
    asset_rows = {name: Asset(display_name=f"MfP {label} {name} {tag}", currency=EUR, asset_type=asset_type) for name, asset_type in assets.items()}
    await _persist(session, keep_alive, user, *broker_rows.values(), *asset_rows.values())
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")) for broker in broker_rows.values()))
    return _Book(user=user, brokers=broker_rows, assets=asset_rows)


def _cash(book: _Book, broker: str, kind: TransactionType, day: date, amount: str) -> Transaction:
    """A cash-only row (DEPOSIT > 0, WITHDRAWAL < 0): no asset, quantity 0."""
    return Transaction(broker_id=book.brokers[broker].id, asset_id=None, type=kind, date=day, quantity=ZERO, amount=D(amount), currency=EUR)


def _trade(book: _Book, broker: str, asset: str, kind: TransactionType, day: date, quantity: str, amount: str) -> Transaction:
    """A BUY (quantity > 0, amount < 0) or SELL (quantity < 0, amount > 0)."""
    return Transaction(broker_id=book.brokers[broker].id, asset_id=book.assets[asset].id, type=kind, date=day, quantity=D(quantity), amount=D(amount), currency=EUR)


def _adjustment_in(book: _Book, broker: str, asset: str, day: date, quantity: str, unit_cost: str | None = None) -> Transaction:
    """An ADJUSTMENT in, in kind (no cash): at ``unit_cost`` EUR a unit, or of unknown cost without one. Never a price."""
    cost = D(unit_cost) if unit_cost is not None else None
    return Transaction(
        broker_id=book.brokers[broker].id,
        asset_id=book.assets[asset].id,
        type=TransactionType.ADJUSTMENT,
        date=day,
        quantity=D(quantity),
        amount=ZERO,
        cost_basis_override=cost,
        cost_basis_currency=EUR if cost is not None else None,
    )


def _close(book: _Book, asset: str, day: date, close: str) -> PriceHistory:
    price = D(close)
    return PriceHistory(asset_id=book.assets[asset].id, date=day, open=price, high=price, low=price, close=price, volume=D("1"), currency=EUR, source_plugin_key="mf_p_test")


async def _summary(session: AsyncSession, book: _Book, valuation_date: date, date_from: date | None = None) -> PortfolioSummary:
    return await PortfolioService(session).get_summary(user_id=book.user.id, target_currency_override=EUR, date_from=date_from, date_to=valuation_date)


async def _report(session: AsyncSession, book: _Book, start: date | None, end: date) -> PortfolioReportResponse:
    """The Dashboard's report: summary and daily history, nothing else."""
    query = PortfolioReportQuery(target_currency=EUR, include_summary=True, include_history=True, include_allocation_history=False, date_range=OpenDateRangeModel(start=start, end=end))
    return await PortfolioService(session).get_report(user_id=book.user.id, query=query)


def _ratio(numerator: str, denominator: str) -> Decimal:
    """The context's quotient of two hand figures: an unrounded ratio."""
    return D(numerator) / D(denominator)


def _assert_headline(summary: PortfolioSummary | None, net_worth: str, total_pnl: str) -> None:
    assert summary is not None, "precondition: no summary"
    shown = (summary.net_worth.amount, summary.total_gain_loss.amount)
    assert shown == (D(net_worth), D(total_pnl)), f"precondition — not the ledger intended: NAV / total P&L {shown[0]} / {shown[1]}, expected {net_worth} / {total_pnl}"


# =============================================================================
# FIXTURES
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
    """Strong references to every row the test flushes (see _persist)."""
    return []


@pytest.fixture(autouse=True)
def clean_portfolio_caches(request):
    """No cached report, WAC or engine blob crosses into or out of a test."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# R17 — the day change
# =============================================================================


@dataclass(frozen=True)
class _DayCase:
    """One ledger: DEPOSIT 10000 and BUY 10 X for 1000 on ``open_day``, X's ``closes``; the headline it must show on
    ``valuation_date`` and its day change by hand. A ratio is (numerator, denominator), None for no ratio."""

    open_day: date
    closes: dict[date, str]
    valuation_date: date
    net_worth: str
    total_pnl: str
    change: str
    vs_total_pnl: tuple[str, str] | None
    vs_nav: tuple[str, str] | None


DAY_CASES = {
    # Thursday 110: NAV 9000 + 1100 = 10100, P&L 100. Friday 113: 10130, 130.
    "weekday": _DayCase(OPEN_DAY, {THURSDAY: "110", FRIDAY: "113"}, FRIDAY, "10130", "130", "30", ("30", "100"), ("30", "10100")),
    # Thursday 90: NAV 9900, P&L −100. Friday 95: 9950, −50. A loss that shrinks is a rise: +50 / |−100| = +0.5.
    "loss-shrinks": _DayCase(OPEN_DAY, {THURSDAY: "90", FRIDAY: "95"}, FRIDAY, "9950", "-50", "50", ("50", "100"), ("50", "9900")),
    # Bought on Thursday with no quote that day: valued at the trade's 100, NAV 10000, P&L 0. Friday 113.
    "zero-pnl-the-day-before": _DayCase(THURSDAY, {FRIDAY: "113"}, FRIDAY, "10130", "130", "130", None, ("130", "10000")),
    # Friday 113, nothing over the weekend, Monday 120: Sunday carries Friday's 10130 / 130. Monday 10200 / 200.
    "monday": _DayCase(OPEN_DAY, {FRIDAY: "113", MONDAY: "120"}, MONDAY, "10200", "200", "70", ("70", "130"), ("70", "10130")),
    # A quote on Saturday, 116: Sunday carries Saturday's 10160 / 160. Monday − Sunday = +40, not Monday − Friday (+70).
    "monday-after-a-weekend-quote": _DayCase(OPEN_DAY, {FRIDAY: "113", SATURDAY: "116", MONDAY: "120"}, MONDAY, "10200", "200", "40", ("40", "160"), ("40", "10160")),
}


async def _one_stock_ledger(session: AsyncSession, keep_alive: list[object], label: str, open_day: date, closes: dict[date, str]) -> _Book:
    book = await _book(session, keep_alive, label, ("A",), {"X": AssetType.STOCK})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, open_day, "10000"),
        _trade(book, "A", "X", TransactionType.BUY, open_day, "10", "-1000"),
        *(_close(book, "X", day, close) for day, close in closes.items()),
    )
    return book


def _day_figures(summary: PortfolioSummary) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """(pnl_change_1d, vs total P&L, vs NAV) of a summary; the change in the report currency."""
    change = summary.pnl_change_1d
    assert change is None or change.code == EUR, f"pnl_change_1d in {change.code}, expected {EUR}"
    return (change.amount if change is not None else None, summary.pnl_change_1d_vs_total_pnl_percent, summary.pnl_change_1d_vs_nav_percent)


def _expected_day(case: _DayCase) -> tuple[Decimal, Decimal | None, Decimal | None]:
    return (D(case.change), _ratio(*case.vs_total_pnl) if case.vs_total_pnl else None, _ratio(*case.vs_nav) if case.vs_nav else None)


class TestDayChange:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(DAY_CASES))
    async def test_the_change_from_the_calendar_day_before(self, session, keep_alive, name):
        """The total P&L of the valuation date less the calendar day before's, and that change over the day before's
        |total P&L| and |NAV|, exactly (``DAY_CASES``)."""
        case = DAY_CASES[name]
        book = await _one_stock_ledger(session, keep_alive, "r17", case.open_day, case.closes)

        summary = await _summary(session, book, case.valuation_date)
        _assert_headline(summary, case.net_worth, case.total_pnl)

        assert _day_figures(summary) == _expected_day(case)

    @pytest.mark.asyncio
    async def test_none_for_a_portfolio_born_on_the_valuation_date(self, session, keep_alive):
        """DEPOSIT, BUY and the close of 113 all on Friday: NAV 10130 and P&L 130, and no Thursday to change from —
        no change at all, not +130 from nothing."""
        book = await _one_stock_ledger(session, keep_alive, "born", FRIDAY, {FRIDAY: "113"})

        summary = await _summary(session, book, FRIDAY)
        _assert_headline(summary, "10130", "130")

        assert _day_figures(summary) == (None, None, None)

    @pytest.mark.asyncio
    async def test_the_period_range_does_not_limit_it(self, session, keep_alive):
        """date_from = the valuation date: a period of one day, and the engine's states still start on 2025-01-02 —
        the weekday's change, +30, 30 / 100 and 30 / 10100."""
        case = DAY_CASES["weekday"]
        book = await _one_stock_ledger(session, keep_alive, "range", case.open_day, case.closes)

        summary = await _summary(session, book, FRIDAY, date_from=FRIDAY)
        _assert_headline(summary, case.net_worth, case.total_pnl)

        assert _day_figures(summary) == _expected_day(case)

    @pytest.mark.asyncio
    async def test_the_report_agrees_with_its_daily_history(self, session, keep_alive):
        """get_report to Friday over the whole history: its summary carries the weekday's change, and today's KPI
        formula on its history — Friday's point less Thursday's, over |Thursday's total_pnl| and |nav_value|, here in
        Decimal and as a fraction — gives the very same figures."""
        case = DAY_CASES["weekday"]
        book = await _one_stock_ledger(session, keep_alive, "report", case.open_day, case.closes)

        report = await _report(session, book, None, FRIDAY)
        _assert_headline(report.summary, case.net_worth, case.total_pnl)
        points = {point.date: point for point in report.history or []}
        assert sorted(points)[-2:] == [THURSDAY, FRIDAY], f"precondition: a daily history ending on Friday, got {sorted(points)[-2:]}"
        last, previous = points[FRIDAY], points[THURSDAY]
        kpi_change = last.total_pnl.amount - previous.total_pnl.amount
        kpi_today = (kpi_change, kpi_change / abs(previous.total_pnl.amount), kpi_change / abs(previous.nav_value.amount))
        assert kpi_today == _expected_day(case), f"precondition: today's KPI on the daily history gives {kpi_today}"

        assert _day_figures(report.summary) == _expected_day(case)

    @pytest.mark.asyncio
    async def test_a_one_day_range_still_has_the_change(self, session, keep_alive):
        """get_report on the range Friday–Friday: the history is that one day, so today's KPI has no point before it
        and shows no change. The summary has it: +30, 30 / 100 and 30 / 10100."""
        case = DAY_CASES["weekday"]
        book = await _one_stock_ledger(session, keep_alive, "oneday", case.open_day, case.closes)

        report = await _report(session, book, FRIDAY, FRIDAY)
        _assert_headline(report.summary, case.net_worth, case.total_pnl)
        assert [point.date for point in report.history or []] == [FRIDAY], "precondition: a one-day history, no previous point for today's KPI"

        assert _day_figures(report.summary) == _expected_day(case)


# =============================================================================
# The timing effect
# =============================================================================


async def _deposits_only_ledger(session: AsyncSession, keep_alive: list[object]) -> _Book:
    """DEPOSIT 1000 and BUY 10 at 100 on DO_START, 120 from DO_PRICE_1, DEPOSIT 500 on DO_TOP_UP (kept as cash),
    130 from DO_PRICE_2: NAV 1800, net invested 1500. The top-up came after the rise: MWRR below TWRR."""
    book = await _book(session, keep_alive, "do", ("A",), {"X": AssetType.STOCK})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, DO_START, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, DO_START, "10", "-1000"),
        _close(book, "X", DO_START, "100"),
        _close(book, "X", DO_PRICE_1, "120"),
        _cash(book, "A", TransactionType.DEPOSIT, DO_TOP_UP, "500"),
        _close(book, "X", DO_PRICE_2, "130"),
    )
    return book


async def _net_withdrawal_ledger(session: AsyncSession, keep_alive: list[object]) -> _Book:
    """DEPOSIT 1000 and BUY 10 at 100 on NW_START, 180 from NW_PRICE_UP, SELL 10 for 1800 on NW_SELL, WITHDRAWAL 1500
    on NW_WITHDRAWAL: NAV 300 > 0, net invested −500 (D-MF5: no MWRR)."""
    book = await _book(session, keep_alive, "nw", ("A",), {"X": AssetType.STOCK})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, NW_START, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, NW_START, "10", "-1000"),
        _close(book, "X", NW_START, "100"),
        _close(book, "X", NW_PRICE_UP, "180"),
        _trade(book, "A", "X", TransactionType.SELL, NW_SELL, "-10", "1800"),
        _cash(book, "A", TransactionType.WITHDRAWAL, NW_WITHDRAWAL, "-1500"),
    )
    return book


class TestTimingEffect:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [None, DO_FROM], ids=["whole-history", "rebased"])
    async def test_mwrr_less_twrr(self, session, keep_alive, date_from):
        """Both returns of the period, different: the timing effect is their difference, the same Decimals."""
        book = await _deposits_only_ledger(session, keep_alive)

        summary = await _summary(session, book, DO_TO, date_from=date_from)
        assert summary.net_worth.amount == D("1800"), f"precondition: NAV 1800, got {summary.net_worth.amount}"
        mwrr_cumulative, twrr = summary.mwrr_cumulative_percent, summary.twrr_percent
        assert mwrr_cumulative is not None and twrr is not None and mwrr_cumulative != twrr, f"precondition: both returns, different — MWRR {mwrr_cumulative}, TWRR {twrr}"

        assert summary.timing_effect_percent == mwrr_cumulative - twrr

    @pytest.mark.asyncio
    async def test_none_without_an_mwrr(self, session, keep_alive):
        """Net withdrawals: no MWRR (D-MF5), a TWRR still — no timing effect, rather than −TWRR."""
        book = await _net_withdrawal_ledger(session, keep_alive)

        summary = await _summary(session, book, NW_END)
        assert summary.net_worth.amount == D("300"), f"precondition: NAV 300, got {summary.net_worth.amount}"
        assert summary.mwrr_cumulative_percent is None, f"precondition: no MWRR (net invested −500), got {summary.mwrr_cumulative_percent}"
        assert summary.twrr_percent is not None, "precondition: a TWRR, so the None comes from the missing MWRR"

        assert summary.timing_effect_percent is None


# =============================================================================
# W8 — the holding groups
# =============================================================================

GROUP_ASSETS = {
    "X": AssetType.STOCK,
    "Y": AssetType.STOCK,
    "U": AssetType.STOCK,
    "M": AssetType.STOCK,
    "E": AssetType.ETF,
    "V": AssetType.FUND,
    "Z": AssetType.STOCK,
    "W": AssetType.BOND,
    "C": AssetType.CRYPTO,
}


@dataclass(frozen=True)
class _Holding:
    """A holding row the scenario must show: how it is valued, its value and its gain (None: unknown)."""

    source: str
    value: str | None
    gain: str | None


GROUP_HOLDINGS = {
    ("A", "X"): _Holding("MARKET_PRICE", "1130", "130"),  # 10 bought for 1000, close 113
    ("A", "Y"): _Holding("MARKET_PRICE", "885", "-115"),  # 5 bought for 1000, close 177
    ("A", "U"): _Holding("MARKET_PRICE", "200", None),  # 4 in without a cost, close 50
    ("A", "M"): _Holding("MISSING", None, None),  # 3 in without a cost, no price
    ("A", "E"): _Holding("MARKET_PRICE", "1220", "220"),  # 20 bought for 1000, close 61
    ("A", "V"): _Holding("MARKET_PRICE", "300", None),  # 2 in without a cost, close 150
    ("B", "Z"): _Holding("MARKET_PRICE", "720", "-80"),  # 8 bought for 800, close 90
    ("B", "W"): _Holding("ESTIMATED_AT_COST", "200", "0"),  # 5 in at 40 a unit, no price
    ("B", "C"): _Holding("MISSING", None, None),  # 2 in without a cost, no price
}

# (broker, asset type or None) → (gain, (Σ gain, Σ cost)), by hand; (None, None) when no holding has a gain.
GROUPS: dict[tuple[str, str | None], tuple[str | None, tuple[str, str] | None]] = {
    ("A", None): ("235", ("235", "3000")),  # X, Y, E: 130 − 115 + 220 on 1000 + 1000 + 1000; U, V, M out
    ("A", "ETF"): ("220", ("220", "1000")),
    ("A", "FUND"): (None, None),  # V alone, gain unknown
    ("A", "STOCK"): ("15", ("15", "2000")),  # X, Y; U and M out
    ("B", None): ("-80", ("-80", "1000")),  # Z, W: −80 + 0 on 800 + 200; C out
    ("B", "BOND"): ("0", ("0", "200")),  # W at cost: a known zero
    ("B", "CRYPTO"): (None, None),  # C alone, nothing known
    ("B", "STOCK"): ("-80", ("-80", "800")),
}

# Each broker's groups in the order the summary lists them: its own group, then its types alphabetically.
GROUP_ORDER = {"A": (None, "ETF", "FUND", "STOCK"), "B": (None, "BOND", "CRYPTO", "STOCK")}


async def _groups_ledger(session: AsyncSession, keep_alive: list[object]) -> _Book:
    """Every row on GROUPS_OPEN, every close on GROUPS_VALUATION. At each broker the rows come in an order that is not
    their types' alphabetical one (A: STOCK, ETF, FUND; B: STOCK, BOND, CRYPTO)."""
    book = await _book(session, keep_alive, "w8", ("A", "B"), GROUP_ASSETS)
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, GROUPS_OPEN, "4000"),
        _trade(book, "A", "X", TransactionType.BUY, GROUPS_OPEN, "10", "-1000"),
        _trade(book, "A", "Y", TransactionType.BUY, GROUPS_OPEN, "5", "-1000"),
        _adjustment_in(book, "A", "U", GROUPS_OPEN, "4"),
        _adjustment_in(book, "A", "M", GROUPS_OPEN, "3"),
        _trade(book, "A", "E", TransactionType.BUY, GROUPS_OPEN, "20", "-1000"),
        _adjustment_in(book, "A", "V", GROUPS_OPEN, "2"),
        _cash(book, "B", TransactionType.DEPOSIT, GROUPS_OPEN, "1000"),
        _trade(book, "B", "Z", TransactionType.BUY, GROUPS_OPEN, "8", "-800"),
        _adjustment_in(book, "B", "W", GROUPS_OPEN, "5", unit_cost="40"),
        _adjustment_in(book, "B", "C", GROUPS_OPEN, "2"),
        _close(book, "X", GROUPS_VALUATION, "113"),
        _close(book, "Y", GROUPS_VALUATION, "177"),
        _close(book, "U", GROUPS_VALUATION, "50"),
        _close(book, "E", GROUPS_VALUATION, "61"),
        _close(book, "V", GROUPS_VALUATION, "150"),
        _close(book, "Z", GROUPS_VALUATION, "90"),
    )
    return book


def _holdings_by_label(summary: PortfolioSummary, book: _Book) -> dict[tuple[object, object], PortfolioHolding]:
    broker_labels = {broker.id: label for label, broker in book.brokers.items()}
    asset_labels = {asset.id: label for label, asset in book.assets.items()}
    return {(broker_labels.get(h.broker_id, h.broker_id), asset_labels.get(h.asset_id, h.asset_id)): h for h in summary.holdings}


def _holding_problems(summary: PortfolioSummary, book: _Book) -> list[str]:
    """The holding rows against GROUP_HOLDINGS: one per (broker, asset), each valued, worth and gaining as expected,
    of its asset's type."""
    shown = _holdings_by_label(summary, book)
    problems: list[str] = []
    if set(shown) != set(GROUP_HOLDINGS):
        problems.append(f"holdings {sorted(map(str, shown))}, expected {sorted(map(str, GROUP_HOLDINGS))}")
    for key, expected in GROUP_HOLDINGS.items():
        holding = shown.get(key)
        if holding is None:
            continue
        actual = (holding.valuation_source, holding.current_value, holding.gain_loss, holding.asset_type)
        wanted = (expected.source, D(expected.value) if expected.value is not None else None, D(expected.gain) if expected.gain is not None else None, book.assets[key[1]].asset_type.value)
        if actual != wanted:
            problems.append(f"holding {key}: (source, value, gain, type) {actual}, expected {wanted}")
    return problems


async def _groups_summary(session: AsyncSession, keep_alive: list[object]) -> tuple[_Book, PortfolioSummary]:
    """The W8 ledger's summary, once its holdings are proven to be the ones intended."""
    book = await _groups_ledger(session, keep_alive)
    summary = await _summary(session, book, GROUPS_VALUATION)
    problems = _holding_problems(summary, book)
    assert not problems, "precondition — not the holdings intended:\n" + "\n".join(problems)
    return book, summary


def _group_figures(summary: PortfolioSummary, book: _Book, broker: str, asset_type: str | None) -> tuple[Decimal | None, Decimal | None]:
    """(gain_loss, gain_loss_percent) of one group, found by the test's broker id; the gain in the report currency."""
    broker_id = book.brokers[broker].id
    matches = [group for group in summary.holding_groups if group.broker_id == broker_id and group.asset_type == asset_type]
    assert len(matches) == 1, f"one group ({broker}, {asset_type}) expected, found {len(matches)}"
    group = matches[0]
    assert group.gain_loss is None or group.gain_loss.code == EUR, f"group ({broker}, {asset_type}) in {group.gain_loss.code}"
    return (group.gain_loss.amount if group.gain_loss is not None else None, group.gain_loss_percent)


def _expected_group(broker: str, asset_type: str | None) -> tuple[Decimal | None, Decimal | None]:
    gain, ratio = GROUPS[(broker, asset_type)]
    return (D(gain) if gain is not None else None, _ratio(*ratio) if ratio is not None else None)


def _treemap_ratio_today(holdings: Iterable[PortfolioHolding]) -> Decimal | None:
    """The treemap's group ratio as the frontend computes it today (ExposureTreemap.svelte ``:366-450``), in Decimal:
    every holding with a value above zero adds it, its gain when known; Σ gain / (Σ value − Σ gain), None on a zero
    cost."""
    value = ZERO
    gain = ZERO
    for holding in holdings:
        if holding.current_value is None or holding.current_value <= 0:
            continue
        value += holding.current_value
        if holding.gain_loss is not None:
            gain += holding.gain_loss
    return gain / (value - gain) if value - gain != 0 else None


class TestHoldingGroups:
    @pytest.mark.asyncio
    async def test_one_group_per_broker_and_per_asset_type_in_order(self, session, keep_alive):
        """By broker_id; at each broker its own group first, then its types alphabetically (A: ETF, FUND, STOCK;
        B: BOND, CRYPTO, STOCK) — not the order the holdings come in."""
        book, summary = await _groups_summary(session, keep_alive)
        brokers = sorted(GROUP_ORDER, key=lambda label: book.brokers[label].id)
        expected = [(book.brokers[label].id, asset_type) for label in brokers for asset_type in GROUP_ORDER[label]]

        assert [(group.broker_id, group.asset_type) for group in summary.holding_groups] == expected

    @pytest.mark.asyncio
    async def test_each_group_as_computed_by_hand(self, session, keep_alive):
        """Every group's gain and its fraction of the cost (``GROUPS``), exactly."""
        book, summary = await _groups_summary(session, keep_alive)

        problems = []
        for broker, asset_type in GROUPS:
            shown, expected = _group_figures(summary, book, broker, asset_type), _expected_group(broker, asset_type)
            if shown != expected:
                problems.append(f"group ({broker}, {asset_type}): (gain, ratio) {shown}, expected {expected}")
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_a_holding_without_a_gain_lends_no_value_to_the_base(self, session, keep_alive):
        """U (STOCK, priced at 200, cost unknown) and V (FUND, 300, cost unknown) are out of broker A's base, and U out
        of its STOCK group's: 235 / 3000 and 15 / 2000. Today's treemap, on the same holdings, puts their values in:
        235 / (3735 − 235) and 15 / (2215 − 15)."""
        book, summary = await _groups_summary(session, keep_alive)
        holdings = _holdings_by_label(summary, book)
        broker_a = [holding for (broker, _asset), holding in holdings.items() if broker == "A"]
        stock_a = [holding for holding in broker_a if holding.asset_type == AssetType.STOCK.value]
        assert (_treemap_ratio_today(broker_a), _treemap_ratio_today(stock_a)) == (_ratio("235", "3500"), _ratio("15", "2200")), "precondition: today's formula on these holdings"

        assert _group_figures(summary, book, "A", None) == (D("235"), _ratio("235", "3000"))
        assert _group_figures(summary, book, "A", "STOCK") == (D("15"), D("0.0075"))

    @pytest.mark.asyncio
    async def test_a_holding_valued_at_cost_counts(self, session, keep_alive):
        """W (BOND, ESTIMATED_AT_COST 200, gain 0) is in broker B's base: −80 / (800 + 200) = −0.08, not −80 / 800;
        and its BOND group is a known zero, (0, 0), not (None, None)."""
        book, summary = await _groups_summary(session, keep_alive)

        assert _group_figures(summary, book, "B", None) == (D("-80"), D("-0.08"))
        assert _group_figures(summary, book, "B", "BOND") == (D("0"), D("0"))

    @pytest.mark.asyncio
    async def test_a_group_without_any_known_gain_has_none(self, session, keep_alive):
        """A's FUND group is V alone (priced, cost unknown): today's treemap shows it at 0 %. B's CRYPTO group is C
        alone (no price, no cost): today's treemap has no tile for it. Both (None, None): no gain is known."""
        book, summary = await _groups_summary(session, keep_alive)
        fund_a = [holding for (broker, _asset), holding in _holdings_by_label(summary, book).items() if broker == "A" and holding.asset_type == AssetType.FUND.value]
        assert _treemap_ratio_today(fund_a) == ZERO, "precondition: today's treemap shows 0 % for V's group"

        assert _group_figures(summary, book, "A", "FUND") == (None, None)
        assert _group_figures(summary, book, "B", "CRYPTO") == (None, None)

    @pytest.mark.asyncio
    async def test_the_broker_group_is_all_its_holdings(self, session, keep_alive):
        """A broker's group spans its types: its gain is the sum of its types' known gains (A: 220 + 15, FUND unknown;
        B: 0 − 80, CRYPTO unknown), its cost every counted holding's (A: ETF's 1000 + STOCK's 2000)."""
        book, summary = await _groups_summary(session, keep_alive)

        problems = []
        for broker, order in GROUP_ORDER.items():
            type_gains = [_group_figures(summary, book, broker, asset_type)[0] for asset_type in order[1:]]
            broker_gain = _group_figures(summary, book, broker, None)[0]
            if broker_gain != sum((gain for gain in type_gains if gain is not None), ZERO):
                problems.append(f"broker {broker}: group gain {broker_gain}, its types' {type_gains}")
        assert not problems, "\n".join(problems)
        assert _group_figures(summary, book, "A", None) == (D("235"), D("235") / (D("1000") + D("2000")))

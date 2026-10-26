"""
MF-K2 — the Dashboard's MWRR line has a value only where its card has one.

Decision D-MF5 = (b), 16/10/2026: «se non ci sono dati per la card, anche la linea è corretto che
sparisca». The card (get_summary) gives ``mwrr_annualized_percent`` only for a period with
snapshots and flows, a value above zero at its end and capital in it; otherwise it is None and the
data-quality report carries MWRR_NOT_CALCULABLE. With MF-K2 every point of the line (get_history)
is the card of the period ending on that day (financial_math/returns.period_mwrr_series): None
where that card is None, the first point still pinned to 0. Since D-P4 cure B the line is the
report's ``mwrr_line`` (``history[].mwrr_*`` are gone): a point on each step's ``date`` and
``through`` of the history, so «the point on day d» is the line point dated d and «the last point»
is the one dated ``range.end``.

The capital is the one the solve itself sees (returns._net_invested, decision N54): the value of
the period's first snapshot — what the investor «buys» at the start, a deposit of that day
included — plus the flows strictly after it, up to the end. A range that opens before the
portfolio's first day rebases to an opening NAV 0 and leaves the first day's deposit inside the
first snapshot: counting −Σ of the period's flows there found no capital at all, and a portfolio
with a single deposit showed «—».

Three states of the code, by reading and by evaluating the pure functions on each scenario's flows:
HEAD (committed: card −Σ of the period's flows, line calculate_mwrr_series unguarded), PREV (the
worktree's first wiring: period_mwrr / period_mwrr_series with −Σ of the flows up to the end), and
N54 (period_mwrr / period_mwrr_series with _net_invested). Every test is green on N54.

Red on HEAD, green on PREV:

- TestNetWithdrawalPeriod::test_line_has_no_mwrr_from_the_net_withdrawal_on — from the day the
  withdrawal takes the net invested to −500 every point still carries a rate (whole history:
  ≈ 2.0219 annualized on that day, ≈ 1.8375 on the last day) and its cumulative;
- TestNetWithdrawalPeriod::test_each_point_is_the_card_of_the_period_ending_there — the sampled
  days from the withdrawal on: card None, point a rate (the day before it agrees already);
- TestValueGonePeriod::test_line_has_no_mwrr_once_the_value_is_gone — NAV 0 from the day the last
  cash is withdrawn, net invested still +500: the line holds the constant 0.5^(365/194) − 1
  ≈ −0.7286 annualized there, and a cumulative that keeps falling after the portfolio is empty
  (−0.5 on that day, ≈ −0.6203 on the last).

Red on HEAD and on PREV (the range opens before the first day, «opens-before» ids):

- TestRangeOpeningOnOrBeforeThePortfolio::test_card_has_the_mwrr_of_its_opening_value and
  ::test_line_has_mwrr_after_the_first_point_and_ends_on_the_card — a single DEPOSIT 1000: the card
  is «—» with MWRR_NOT_CALCULABLE (net invested −(−0) = 0). The line has values on HEAD (≈ 0.3297
  on the last day), none after the first point on PREV;
- TestYoungPortfolioPartialWithdrawal (both tests) — DEPOSIT 1000, WITHDRAWAL 300 later: the card
  is «—» on HEAD and on PREV (net invested −300); PREV's line has no value after the first point;
- TestYoungPortfolioWithdrawalExhaustingCapital::test_card_has_no_mwrr_from_the_withdrawal_on —
  its presence barrier: the card of the period ending the day before the withdrawal is «—» on HEAD
  and on PREV (no capital seen at all), so the «—» after it would prove nothing there;
- TestYoungPortfolioWithdrawalExhaustingCapital::test_line_has_no_mwrr_from_the_withdrawal_on —
  HEAD draws a rate from the withdrawal on (≈ 2.2208 on that day for both amounts); PREV draws
  none before it.

Pinned, green on HEAD, PREV and N54:

- TestNetWithdrawalPeriod::test_card_has_no_mwrr and TestValueGonePeriod::test_card_has_no_mwrr:
  the card already returns None and reports MWRR_NOT_CALCULABLE;
- TestDepositsOnlyParity: in an ordinary deposits-only portfolio the card equals the last point
  of the line, annualized and cumulative, the same Decimal, with and without date_from and date_to;
- TestRangeOpeningOnOrBeforeThePortfolio, «opens-on» ids: a range starting on the first day
  rebases to an opening NAV 1000 and a −1000 flow, so every guard sees the same capital.

N54 changes no expectation of the others: where the first snapshot's value equals the first day's
deposits (every scenario here buys at the day's close), first NAV + later flows equals −Σ of the
flows: 1000 → −500 (net withdrawals, whole history and rebased), 1000 → 500 (value gone), 1500
(deposits only).

Isolation: every test owns its user, broker and asset (unique names) and writes only through a
session that is rolled back: nothing is committed. Every amount is in EUR and is read in EUR
(target_currency_override), so no FX rate and no other test's row reaches the figures. The report,
WAC and engine blob caches are emptied around each test. A history belongs to the test's user
alone and comes back in steps (D-P4 cure B): the history holds the days of each step, the MWRR is
the report's ``mwrr_line`` (PortfolioService.get_history_steps), true values at each step's date and
through, dated within the response's ``range``. The line's first and last points are the period's
ends by construction (range.start, range.end), not a position in a shared collection.

Reference: backend/app/services/portfolio_service.py (get_summary, get_history_steps),
backend/app/services/financial_math/returns.py (period_mwrr, period_mwrr_series).
"""

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

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import IssueCode, MwrrLinePoint, PortfolioHistoryPoint, PortfolioSummary
from backend.app.services.financial_math.series_steps import value_at
from backend.app.services.portfolio_service import HistorySteps, PortfolioService

EUR = "EUR"

# Net withdrawals (TestNetWithdrawalPeriod). DEPOSIT 1000 and BUY 10 at 100 on NW_START, the price
# goes to 180 on NW_PRICE_UP, SELL 10 at 180 on NW_SELL, WITHDRAWAL 1500 on NW_WITHDRAWAL.
# NAV 1000 → 1800 → 300 (> 0 to the end); net invested 1000 → −500 from NW_WITHDRAWAL.
# NW_REBASED_FROM opens the period after the BUY, before the price move: opening NAV 1000, so the
# rebased net invested goes the same way, 1000 → −500.
NW_START = date(2025, 1, 2)
NW_REBASED_FROM = date(2025, 1, 15)
NW_PRICE_UP = date(2025, 6, 30)
NW_SELL = date(2025, 7, 1)
NW_WITHDRAWAL = date(2025, 7, 15)
NW_END = date(2025, 9, 30)
NW_END_NAV = Decimal("300")

# Value gone (TestValueGonePeriod). DEPOSIT 1000 and BUY 10 at 100 on VG_START, the price falls to
# 50 on VG_PRICE_DOWN, SELL 10 at 50 on VG_SELL, WITHDRAWAL 500 on VG_EMPTY. NAV 1000 → 500 → 0
# from VG_EMPTY; net invested 1000 → 500, positive throughout: only the value explains a None.
VG_START = date(2025, 1, 2)
VG_PRICE_DOWN = date(2025, 6, 30)
VG_SELL = date(2025, 7, 1)
VG_EMPTY = date(2025, 7, 15)
VG_END = date(2025, 9, 30)

# Deposits only (TestDepositsOnlyParity). DEPOSIT 1000 and BUY 10 at 100 on DO_START, the price
# goes to 120 on DO_PRICE_1, DEPOSIT 500 on DO_TOP_UP (kept as cash), the price goes to 130 on
# DO_PRICE_2. NAV 1800 from DO_PRICE_2 on, net invested 1500: the card has a rate.
DO_START = date(2025, 1, 2)
DO_FROM = date(2025, 2, 1)
DO_PRICE_1 = date(2025, 3, 3)
DO_TOP_UP = date(2025, 5, 2)
DO_PRICE_2 = date(2025, 6, 2)
DO_TO = date(2025, 8, 29)

# Single deposit (TestRangeOpeningOnOrBeforeThePortfolio). DEPOSIT 1000 and BUY 10 at 100 on
# OB_START, the price goes to 115 on OB_PRICE_UP. NAV 1000 → 1150, no other flow: the MWRR is the
# closed form (1150 / 1000)^(365 / days) − 1, cumulative +15 %, from OB_START whatever date_from.
OB_START = date(2025, 3, 3)
OB_FROM_BEFORE = OB_START - timedelta(days=30)
OB_PRICE_UP = date(2025, 6, 2)
OB_TO = date(2025, 8, 29)
OB_OPENING_NAV = Decimal("1000")
OB_END_NAV = Decimal("1150")

# Young portfolio with a withdrawal (TestYoungPortfolio*), read from YW_FROM, before its first day.
# DEPOSIT 1000 and BUY 5 at 100 on YW_START (500 left in cash), the price goes to 180 on
# YW_PRICE_UP, SELL 5 at 180 on YW_SELL, WITHDRAWAL of W on YW_WITHDRAWAL. NAV 1000 → 1400 → 1400 − W
# (> 0 for every W used); net invested, first NAV + later flows: 1000 → 1000 − W from YW_WITHDRAWAL.
YW_START = date(2025, 3, 3)
YW_FROM = YW_START - timedelta(days=30)
YW_PRICE_UP = date(2025, 5, 2)
YW_SELL = date(2025, 5, 5)
YW_WITHDRAWAL = date(2025, 6, 16)
YW_END = date(2025, 8, 29)
YW_NAV_BEFORE_WITHDRAWAL = Decimal("1400")
YW_PARTIAL = "300"  # net invested 700: the card and the line keep a rate
YW_EXHAUSTING = {"exactly-zero": "1000", "below-zero": "1200"}  # net invested 0 and −200: «—»

# A rate solved to 6 decimals against its closed form computed in float.
CLOSED_FORM_TOLERANCE = Decimal("0.00001")

# =============================================================================
# HELPERS
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one.

    The identity map holds flushed objects weakly: kept alive, every query of the test returns the
    rows exactly as built, so the card and the line of one test read the same Decimals."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


@dataclass(frozen=True)
class _Scope:
    """One user owning 100 % of one broker, and one EUR asset with no provider."""

    user: User
    broker: Broker
    asset: Asset


async def _new_scope(session: AsyncSession, keep_alive: list[object], label: str) -> _Scope:
    tag = uuid4().hex[:12]
    user = User(username=f"mfk2_{label}_{tag}", email=f"mfk2_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"MfK2_{label}_{tag}")
    asset = Asset(display_name=f"MfK2 {label} {tag}", identifier_ticker=f"MK{tag[:8].upper()}", currency=EUR, asset_type=AssetType.STOCK)
    await _persist(session, keep_alive, user, broker, asset)
    await _persist(session, keep_alive, BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1.0")))
    return _Scope(user=user, broker=broker, asset=asset)


def _cash(scope: _Scope, tx_type: TransactionType, on: date, amount: str) -> Transaction:
    """A cash-only row (DEPOSIT > 0, WITHDRAWAL < 0): no asset, quantity 0."""
    return Transaction(broker_id=scope.broker.id, asset_id=None, type=tx_type, date=on, quantity=Decimal("0"), amount=Decimal(amount), currency=EUR)


def _trade(scope: _Scope, tx_type: TransactionType, on: date, quantity: str, amount: str) -> Transaction:
    """A BUY (quantity > 0, amount < 0) or SELL (quantity < 0, amount > 0) of the scope's asset."""
    return Transaction(broker_id=scope.broker.id, asset_id=scope.asset.id, type=tx_type, date=on, quantity=Decimal(quantity), amount=Decimal(amount), currency=EUR)


def _close(scope: _Scope, on: date, price: str) -> PriceHistory:
    value = Decimal(price)
    return PriceHistory(asset_id=scope.asset.id, date=on, open=value, high=value, low=value, close=value, volume=Decimal("1"), currency=EUR, source_plugin_key="manual_test")


async def _net_withdrawal_scope(session: AsyncSession, keep_alive: list[object]) -> _Scope:
    scope = await _new_scope(session, keep_alive, "nw")
    await _persist(
        session,
        keep_alive,
        _cash(scope, TransactionType.DEPOSIT, NW_START, "1000"),
        _trade(scope, TransactionType.BUY, NW_START, "10", "-1000"),
        _close(scope, NW_START, "100"),
        _close(scope, NW_PRICE_UP, "180"),
        _trade(scope, TransactionType.SELL, NW_SELL, "-10", "1800"),
        _cash(scope, TransactionType.WITHDRAWAL, NW_WITHDRAWAL, "-1500"),
    )
    return scope


async def _value_gone_scope(session: AsyncSession, keep_alive: list[object]) -> _Scope:
    scope = await _new_scope(session, keep_alive, "vg")
    await _persist(
        session,
        keep_alive,
        _cash(scope, TransactionType.DEPOSIT, VG_START, "1000"),
        _trade(scope, TransactionType.BUY, VG_START, "10", "-1000"),
        _close(scope, VG_START, "100"),
        _close(scope, VG_PRICE_DOWN, "50"),
        _trade(scope, TransactionType.SELL, VG_SELL, "-10", "500"),
        _cash(scope, TransactionType.WITHDRAWAL, VG_EMPTY, "-500"),
    )
    return scope


async def _deposits_only_scope(session: AsyncSession, keep_alive: list[object]) -> _Scope:
    scope = await _new_scope(session, keep_alive, "do")
    await _persist(
        session,
        keep_alive,
        _cash(scope, TransactionType.DEPOSIT, DO_START, "1000"),
        _trade(scope, TransactionType.BUY, DO_START, "10", "-1000"),
        _close(scope, DO_START, "100"),
        _close(scope, DO_PRICE_1, "120"),
        _cash(scope, TransactionType.DEPOSIT, DO_TOP_UP, "500"),
        _close(scope, DO_PRICE_2, "130"),
    )
    return scope


async def _single_deposit_scope(session: AsyncSession, keep_alive: list[object]) -> _Scope:
    scope = await _new_scope(session, keep_alive, "ob")
    await _persist(
        session,
        keep_alive,
        _cash(scope, TransactionType.DEPOSIT, OB_START, "1000"),
        _trade(scope, TransactionType.BUY, OB_START, "10", "-1000"),
        _close(scope, OB_START, "100"),
        _close(scope, OB_PRICE_UP, "115"),
    )
    return scope


async def _young_withdrawal_scope(session: AsyncSession, keep_alive: list[object], withdrawal: str) -> _Scope:
    scope = await _new_scope(session, keep_alive, "yw")
    await _persist(
        session,
        keep_alive,
        _cash(scope, TransactionType.DEPOSIT, YW_START, "1000"),
        _trade(scope, TransactionType.BUY, YW_START, "5", "-500"),
        _close(scope, YW_START, "100"),
        _close(scope, YW_PRICE_UP, "180"),
        _trade(scope, TransactionType.SELL, YW_SELL, "-5", "900"),
        _cash(scope, TransactionType.WITHDRAWAL, YW_WITHDRAWAL, f"-{withdrawal}"),
    )
    return scope


async def _card(session: AsyncSession, scope: _Scope, date_from: date | None, date_to: date | None) -> PortfolioSummary:
    """The Dashboard's summary of the period (the MWRR card)."""
    return await PortfolioService(session).get_summary(user_id=scope.user.id, target_currency_override=EUR, date_from=date_from, date_to=date_to)


async def _line(session: AsyncSession, scope: _Scope, date_from: date | None, date_to: date | None) -> HistorySteps:
    """The Dashboard's history of the period in steps: its ``range``, the steps and the MWRR line."""
    return await PortfolioService(session).get_history_steps(user_id=scope.user.id, date_from=date_from, date_to=date_to, target_currency_override=EUR)


def _reports_mwrr_not_calculable(summary: PortfolioSummary) -> bool:
    assert summary.data_quality is not None, "the summary carries no data-quality report"
    return any(issue.code == IssueCode.MWRR_NOT_CALCULABLE for issue in summary.data_quality.issues)


def _step_on(line: HistorySteps, day: date) -> PortfolioHistoryPoint:
    """The history step holding ``day`` (the history has no gap inside its range)."""
    step = value_at(line.history, day)
    span = f"{line.range.start}..{line.range.end}" if line.range else "nothing"
    assert step is not None, f"the history has no step holding {day} (its range is {span})"
    return step


def _mwrr_on(points: list[MwrrLinePoint], day: date) -> MwrrLinePoint:
    """The MWRR line's true point dated ``day`` (a step's date or through)."""
    point = next((point for point in points if point.date == day), None)
    span = f"{points[0].date}..{points[-1].date}" if points else "nothing"
    assert point is not None, f"the MWRR line has no point on {day} (it spans {span})"
    return point


def _shown(points: list[MwrrLinePoint]) -> list[tuple[str, str | None, str | None]]:
    """(date, annualized, cumulative) of each point, for a failure message."""
    return [(point.date.isoformat(), None if point.annualized is None else str(point.annualized), None if point.cumulative is None else str(point.cumulative)) for point in points]


def _assert_line_spans(line: HistorySteps, first_day: date, last_day: date | None) -> None:
    """Presence barrier: the history and its MWRR line cover the period end to end, so an absent MWRR is not an absent point.

    ``last_day`` None: the period ends today, read from the response's range rather than from the clock."""
    assert line.range is not None and line.history and line.mwrr_line, "the history or its MWRR line is empty"
    assert line.range.start == first_day, f"the range is {line.range.start}..{line.range.end}, expected it to open on {first_day}"
    if last_day is not None:
        assert line.range.end == last_day, f"the range is {line.range.start}..{line.range.end}, expected it to end on {last_day}"
    assert (line.history[0].date, line.history[-1].through) == (line.range.start, line.range.end), "the history does not cover its range end to end"
    assert (line.mwrr_line[0].date, line.mwrr_line[-1].date) == (line.range.start, line.range.end), f"the MWRR line spans {line.mwrr_line[0].date}..{line.mwrr_line[-1].date}, the range {line.range.start}..{line.range.end}"


def _assert_card_is_the_last_point(summary: PortfolioSummary, line: HistorySteps, period_start: date, date_to: date | None) -> None:
    """The card has an MWRR, reports no MWRR_NOT_CALCULABLE, and equals the line's last point (dated range.end), the same Decimal."""
    _assert_line_spans(line, period_start, date_to)
    last = line.mwrr_line[-1]
    # Without date_to both end "today": the card's MWRR window ends where the line does, read
    # from the card instead of the clock so a midnight between the calls cannot pass for a defect.
    assert summary.mwrr_period_days == (last.date - period_start).days, f"the card's MWRR covers {summary.mwrr_period_days} days, the line {period_start}..{last.date}"
    assert summary.mwrr_annualized_percent is not None, f"the card shows «—» (data-quality MWRR_NOT_CALCULABLE: {_reports_mwrr_not_calculable(summary)}), the line's last point ({last.date}) {_shown([last])}"
    assert not _reports_mwrr_not_calculable(summary), "the card has an MWRR, MWRR_NOT_CALCULABLE should not be reported"
    assert (last.annualized, str(last.annualized)) == (summary.mwrr_annualized_percent, str(summary.mwrr_annualized_percent)), f"annualized: card {summary.mwrr_annualized_percent}, last point ({last.date}) {last.annualized}"
    assert (last.cumulative, str(last.cumulative)) == (summary.mwrr_cumulative_percent, str(summary.mwrr_cumulative_percent)), f"cumulative: card {summary.mwrr_cumulative_percent}, last point ({last.date}) {last.cumulative}"


def _assert_close(actual: Decimal | None, expected: float, what: str) -> None:
    assert actual is not None, f"{what}: «—», expected ≈ {expected:.6f}"
    assert abs(actual - Decimal(repr(expected))) <= CLOSED_FORM_TOLERANCE, f"{what}: {actual}, expected ≈ {expected:.6f} (± {CLOSED_FORM_TOLERANCE})"


def _assert_first_point_pinned(points: list[MwrrLinePoint]) -> None:
    first = points[0]
    assert (first.annualized, first.cumulative) == (Decimal("0"), Decimal("0")), f"the first point ({first.date}) is not pinned to 0: {_shown([first])}"


def _assert_rates_before(points: list[MwrrLinePoint], cutoff: date) -> None:
    """Every line point strictly between the first one and ``cutoff`` has a rate, annualized and cumulative:
    the period ending there has capital in it and a positive value, so its card has one."""
    before = [point for point in points if points[0].date < point.date < cutoff]
    assert before, f"no point between {points[0].date} and {cutoff}"
    blank = [point for point in before if point.annualized is None or point.cumulative is None]
    assert blank == [], f"{len(blank)}/{len(before)} points before {cutoff} lost their MWRR, e.g. {_shown(blank[:3])}"


def _assert_no_rate_from(points: list[MwrrLinePoint], cutoff: date, why: str) -> None:
    """D-MF5: from ``cutoff`` on the card of the period ending on each day is «—», and so is the line (every point dated on or after it)."""
    after = [point for point in points if point.date >= cutoff]
    assert after, f"no point from {cutoff} on"
    assert after[0].date == cutoff, f"presence barrier: a step starts on {cutoff}, so the line has a true point on it, yet its first point from there is {after[0].date}"
    drawn = [point for point in after if point.annualized is not None or point.cumulative is not None]
    assert drawn == [], f"D-MF5: from {cutoff} on {why}, so the card shows «—», yet {len(drawn)}/{len(after)} points of the line carry an MWRR: first {_shown(drawn[:3])}, last {_shown(drawn[-1:])}"


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
# TestNetWithdrawalPeriod — net invested ≤ 0, value > 0
# =============================================================================


class TestNetWithdrawalPeriod:
    """More withdrawn than deposited, with a value still above zero: the card has no MWRR, and
    from the day of that withdrawal neither has the line."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [None, NW_REBASED_FROM], ids=["whole-history", "rebased"])
    async def test_card_has_no_mwrr(self, session, keep_alive, date_from):
        """Green before and after: the card's rule already holds."""
        scope = await _net_withdrawal_scope(session, keep_alive)

        summary = await _card(session, scope, date_from, NW_END)

        assert summary.net_worth.amount == NW_END_NAV, f"precondition: the value at {NW_END} is {summary.net_worth.amount}, expected {NW_END_NAV} (> 0)"
        assert summary.mwrr_annualized_percent is None, f"net invested −500: the card should show «—», got {summary.mwrr_annualized_percent}"
        assert summary.mwrr_cumulative_percent is None, f"net invested −500: no cumulative MWRR either, got {summary.mwrr_cumulative_percent}"
        assert _reports_mwrr_not_calculable(summary), "the card has no MWRR, the data-quality report should say MWRR_NOT_CALCULABLE"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [None, NW_REBASED_FROM], ids=["whole-history", "rebased"])
    async def test_line_has_no_mwrr_from_the_net_withdrawal_on(self, session, keep_alive, date_from):
        """Red on HEAD: calculate_mwrr_series draws a rate on every day from the withdrawal on."""
        scope = await _net_withdrawal_scope(session, keep_alive)

        line = await _line(session, scope, date_from, NW_END)

        _assert_line_spans(line, date_from or NW_START, NW_END)
        not_positive = [step.date for step in line.history if step.nav_value.amount <= 0]
        assert not_positive == [], f"precondition: the value stays above zero, yet it is ≤ 0 on {not_positive[:3]}"
        assert _step_on(line, NW_WITHDRAWAL).nav_value.amount == NW_END_NAV
        _assert_first_point_pinned(line.mwrr_line)
        _assert_rates_before(line.mwrr_line, NW_WITHDRAWAL)
        _assert_no_rate_from(line.mwrr_line, NW_WITHDRAWAL, "the net invested is −500")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [None, NW_REBASED_FROM], ids=["whole-history", "rebased"])
    async def test_each_point_is_the_card_of_the_period_ending_there(self, session, keep_alive, date_from):
        """Point by point, D-MF5: the line's true point on day d equals the card of the same period ended on d.

        Green on the day before the withdrawal (both a rate) before and after; red on HEAD from the
        withdrawal on (card None, line a rate)."""
        scope = await _net_withdrawal_scope(session, keep_alive)
        line = await _line(session, scope, date_from, NW_END)
        _assert_line_spans(line, date_from or NW_START, NW_END)

        day_before = NW_WITHDRAWAL - timedelta(days=1)
        # The line has true points on a step's date and through, and at the month ends inside a long step: the days
        # sampled are line points, the day before the withdrawal (the through of the step before it), the withdrawal
        # itself (the date of its step), a month end inside the step it opens, and the last day.
        inside = [point.date for point in line.mwrr_line if NW_WITHDRAWAL < point.date < NW_END]
        assert inside, f"presence barrier: the line has no point between {NW_WITHDRAWAL} and {NW_END}, nothing proves the days after the withdrawal"
        problems: list[str] = []
        for day in (day_before, NW_WITHDRAWAL, inside[0], NW_END):
            # Each card runs the engine afresh: the comparison is about the MWRR, not the blob cache's range handling.
            _clear_portfolio_caches()
            card = await _card(session, scope, date_from, day)
            if day == day_before:
                assert card.mwrr_annualized_percent is not None, f"anchor: the card ending {day_before} has capital and value, it should have an MWRR"
            point = _mwrr_on(line.mwrr_line, day)
            card_pair = (card.mwrr_annualized_percent, card.mwrr_cumulative_percent)
            line_pair = (point.annualized, point.cumulative)
            if card_pair != line_pair:
                problems.append(f"{day}: card {card_pair}, line {line_pair}")

        assert problems == [], "D-MF5: the line differs from the card of the period ending on the same day:\n" + "\n".join(problems)


# =============================================================================
# TestValueGonePeriod — value ≤ 0, net invested > 0
# =============================================================================


class TestValueGonePeriod:
    """Everything sold and withdrawn, at a loss: the value is 0 and the net invested still positive.
    The card has no MWRR, and from the day the value is gone neither has the line."""

    @pytest.mark.asyncio
    async def test_card_has_no_mwrr(self, session, keep_alive):
        """Green before and after: the card requires a value above zero."""
        scope = await _value_gone_scope(session, keep_alive)

        summary = await _card(session, scope, None, VG_END)

        assert summary.net_worth.amount == Decimal("0"), f"precondition: the value at {VG_END} is {summary.net_worth.amount}, expected 0"
        assert summary.net_deposited_capital is not None and summary.net_deposited_capital.amount == Decimal("500"), f"precondition: net invested +500, got {summary.net_deposited_capital}"
        assert summary.mwrr_annualized_percent is None, f"value 0: the card should show «—», got {summary.mwrr_annualized_percent}"
        assert summary.mwrr_cumulative_percent is None, f"value 0: no cumulative MWRR either, got {summary.mwrr_cumulative_percent}"
        assert _reports_mwrr_not_calculable(summary), "the card has no MWRR, the data-quality report should say MWRR_NOT_CALCULABLE"

    @pytest.mark.asyncio
    async def test_line_has_no_mwrr_once_the_value_is_gone(self, session, keep_alive):
        """Red on HEAD: calculate_mwrr_series keeps a rate after the value is gone (≈ −0.7286 annualized,
        a cumulative from −0.5 falling to ≈ −0.6203 on the last day)."""
        scope = await _value_gone_scope(session, keep_alive)

        line = await _line(session, scope, None, VG_END)

        _assert_line_spans(line, VG_START, VG_END)
        assert [step.date for step in line.history if step.date < VG_EMPTY and step.nav_value.amount <= 0] == [], "precondition: the value is above zero before the last withdrawal"
        assert [step.date for step in line.history if step.date >= VG_EMPTY and step.nav_value.amount != 0] == [], "precondition: the value is 0 from the last withdrawal on"
        _assert_first_point_pinned(line.mwrr_line)
        _assert_rates_before(line.mwrr_line, VG_EMPTY)
        _assert_no_rate_from(line.mwrr_line, VG_EMPTY, "the value is 0")


# =============================================================================
# TestDepositsOnlyParity — the card is the last point of the line
# =============================================================================


class TestDepositsOnlyParity:
    """An ordinary deposits-only portfolio: the card and the last point of the line are one MWRR."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("date_from", "date_to"),
        [(DO_FROM, DO_TO), (DO_FROM, None), (None, DO_TO), (None, None)],
        ids=["from-to", "from-today", "whole-to", "whole-today"],
    )
    async def test_card_equals_the_last_point_of_the_line(self, session, keep_alive, date_from, date_to):
        """Green on HEAD, PREV and N54: same flows, same opening snapshot, same end."""
        scope = await _deposits_only_scope(session, keep_alive)

        summary = await _card(session, scope, date_from, date_to)
        line = await _line(session, scope, date_from, date_to)

        assert line.history, "the history is empty"
        assert summary.net_worth.amount == Decimal("1800") and line.history[-1].nav_value.amount == Decimal("1800"), f"precondition: value 1800 at the end, card {summary.net_worth.amount}, history {line.history[-1].nav_value.amount}"
        _assert_card_is_the_last_point(summary, line, date_from or DO_START, date_to)


# =============================================================================
# TestRangeOpeningOnOrBeforeThePortfolio — a single deposit, read from or before its first day
# =============================================================================

_OB_FROMS = pytest.mark.parametrize("date_from", [OB_FROM_BEFORE, OB_START], ids=["opens-before", "opens-on"])
_OB_TOS = pytest.mark.parametrize("date_to", [OB_TO, None], ids=["to-date", "to-today"])


class TestRangeOpeningOnOrBeforeThePortfolio:
    """A Dashboard range that starts 30 days before the portfolio's first day, or on it: the period
    opens on the first snapshot, with the first day's deposit inside its value (1000), and that
    value is the capital. The card has an MWRR, no MWRR_NOT_CALCULABLE, and the line ends on it."""

    @pytest.mark.asyncio
    @_OB_TOS
    @_OB_FROMS
    async def test_card_has_the_mwrr_of_its_opening_value(self, session, keep_alive, date_from, date_to):
        """opens-before: red on HEAD and PREV («—», net invested 0). opens-on: green on all three."""
        scope = await _single_deposit_scope(session, keep_alive)

        summary = await _card(session, scope, date_from, date_to)

        assert summary.net_worth.amount == OB_END_NAV, f"precondition: the value at the end is {summary.net_worth.amount}, expected {OB_END_NAV}"
        assert summary.mwrr_annualized_percent is not None, f"a single deposit of 1000 now worth {OB_END_NAV}: the card should have an MWRR, it shows «—» (MWRR_NOT_CALCULABLE: {_reports_mwrr_not_calculable(summary)})"
        assert not _reports_mwrr_not_calculable(summary), "the card has an MWRR, MWRR_NOT_CALCULABLE should not be reported"
        days = summary.mwrr_period_days
        assert days is not None and days > 0, f"the card's MWRR window is {days} days"
        if date_to is not None:
            assert days == (date_to - OB_START).days, f"the card's MWRR covers {days} days: it should open on the first day {OB_START}, not on {date_from}"
        # One flow in, one value out: the MWRR is the closed form, which only an opening capital of 1000 on OB_START gives.
        _assert_close(summary.mwrr_annualized_percent, float(OB_END_NAV / OB_OPENING_NAV) ** (365 / days) - 1, f"annualized MWRR over {days} days")
        _assert_close(summary.mwrr_cumulative_percent, float(OB_END_NAV / OB_OPENING_NAV) - 1, "cumulative MWRR")

    @pytest.mark.asyncio
    @_OB_TOS
    @_OB_FROMS
    async def test_line_has_mwrr_after_the_first_point_and_ends_on_the_card(self, session, keep_alive, date_from, date_to):
        """opens-before: red on HEAD (the card is «—» while the line has values) and on PREV (no value
        after the first point either). opens-on: green on all three."""
        scope = await _single_deposit_scope(session, keep_alive)

        line = await _line(session, scope, date_from, date_to)
        summary = await _card(session, scope, date_from, date_to)

        _assert_line_spans(line, OB_START, date_to)
        assert _step_on(line, OB_START).nav_value.amount == OB_OPENING_NAV, f"precondition: the first day's value is {_step_on(line, OB_START).nav_value.amount}, expected {OB_OPENING_NAV}"
        _assert_first_point_pinned(line.mwrr_line)
        _assert_rates_before(line.mwrr_line, line.range.end + timedelta(days=1))
        _assert_card_is_the_last_point(summary, line, OB_START, date_to)


# =============================================================================
# TestYoungPortfolio* — read from before the first day, with a withdrawal after it
# =============================================================================


class TestYoungPortfolioPartialWithdrawal:
    """DEPOSIT 1000, WITHDRAWAL 300 later, the value above zero throughout: net invested 1000 → 700.
    The card and every point of the line keep an MWRR."""

    @pytest.mark.asyncio
    async def test_card_keeps_mwrr(self, session, keep_alive):
        """Red on HEAD and PREV: −Σ of the rebased flows is −300, «—» with MWRR_NOT_CALCULABLE."""
        scope = await _young_withdrawal_scope(session, keep_alive, YW_PARTIAL)

        summary = await _card(session, scope, YW_FROM, YW_END)

        end_nav = YW_NAV_BEFORE_WITHDRAWAL - Decimal(YW_PARTIAL)
        assert summary.net_worth.amount == end_nav, f"precondition: the value at {YW_END} is {summary.net_worth.amount}, expected {end_nav}"
        assert summary.mwrr_annualized_percent is not None, f"net invested 700, value {end_nav}: the card should have an MWRR, it shows «—» (MWRR_NOT_CALCULABLE: {_reports_mwrr_not_calculable(summary)})"
        assert summary.mwrr_cumulative_percent is not None, "the card has an annualized MWRR, it should have its cumulative too"
        assert not _reports_mwrr_not_calculable(summary), "the card has an MWRR, MWRR_NOT_CALCULABLE should not be reported"

    @pytest.mark.asyncio
    async def test_line_keeps_mwrr_and_ends_on_the_card(self, session, keep_alive):
        """Red on HEAD (the card is «—» while the line has values) and on PREV (the line has none
        after the first point)."""
        scope = await _young_withdrawal_scope(session, keep_alive, YW_PARTIAL)

        line = await _line(session, scope, YW_FROM, YW_END)
        summary = await _card(session, scope, YW_FROM, YW_END)

        _assert_line_spans(line, YW_START, YW_END)
        not_positive = [step.date for step in line.history if step.nav_value.amount <= 0]
        assert not_positive == [], f"precondition: the value stays above zero, yet it is ≤ 0 on {not_positive[:3]}"
        _assert_first_point_pinned(line.mwrr_line)
        _assert_rates_before(line.mwrr_line, YW_END + timedelta(days=1))
        _assert_card_is_the_last_point(summary, line, YW_START, YW_END)


class TestYoungPortfolioWithdrawalExhaustingCapital:
    """The boundary: the withdrawal takes the net invested, first NAV + later flows, to 0 or below
    while the value stays above zero. A rate up to the day before; «—» from that day on, on the line
    and on the card."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("withdrawal", list(YW_EXHAUSTING.values()), ids=list(YW_EXHAUSTING))
    async def test_card_has_no_mwrr_from_the_withdrawal_on(self, session, keep_alive, withdrawal):
        """Red on HEAD and PREV through the presence barrier: the card ending the day before the
        withdrawal is already «—» there, so the «—» after it would be the wrong «—»."""
        scope = await _young_withdrawal_scope(session, keep_alive, withdrawal)
        net_invested_after = Decimal("1000") - Decimal(withdrawal)

        cards: dict[date, PortfolioSummary] = {}
        for day in (YW_WITHDRAWAL - timedelta(days=1), YW_WITHDRAWAL, YW_END):
            # Each card runs the engine afresh: the check is about the MWRR, not the blob cache's range handling.
            _clear_portfolio_caches()
            cards[day] = await _card(session, scope, YW_FROM, day)

        day_before = cards[YW_WITHDRAWAL - timedelta(days=1)]
        assert day_before.mwrr_annualized_percent is not None, f"presence barrier: the card ending {YW_WITHDRAWAL - timedelta(days=1)} has capital 1000 and value {day_before.net_worth.amount}, it should have an MWRR (MWRR_NOT_CALCULABLE: {_reports_mwrr_not_calculable(day_before)})"
        for day in (YW_WITHDRAWAL, YW_END):
            card = cards[day]
            assert card.net_worth.amount > 0, f"precondition: the value at {day} is {card.net_worth.amount}, expected above zero"
            assert (card.mwrr_annualized_percent, card.mwrr_cumulative_percent) == (None, None), f"net invested {net_invested_after} from {YW_WITHDRAWAL}: the card ending {day} should show «—», got {card.mwrr_annualized_percent} / {card.mwrr_cumulative_percent}"
            assert _reports_mwrr_not_calculable(card), f"the card ending {day} has no MWRR, the data-quality report should say MWRR_NOT_CALCULABLE"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("withdrawal", list(YW_EXHAUSTING.values()), ids=list(YW_EXHAUSTING))
    async def test_line_has_no_mwrr_from_the_withdrawal_on(self, session, keep_alive, withdrawal):
        """Red on HEAD (a rate from the withdrawal on) and on PREV (no rate before it)."""
        scope = await _young_withdrawal_scope(session, keep_alive, withdrawal)
        net_invested_after = Decimal("1000") - Decimal(withdrawal)

        line = await _line(session, scope, YW_FROM, YW_END)

        _assert_line_spans(line, YW_START, YW_END)
        not_positive = [step.date for step in line.history if step.nav_value.amount <= 0]
        assert not_positive == [], f"precondition: the value stays above zero, yet it is ≤ 0 on {not_positive[:3]}"
        _assert_first_point_pinned(line.mwrr_line)
        _assert_rates_before(line.mwrr_line, YW_WITHDRAWAL)
        _assert_no_rate_from(line.mwrr_line, YW_WITHDRAWAL, f"the net invested is {net_invested_after}")

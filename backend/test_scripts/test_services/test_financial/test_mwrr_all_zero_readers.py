"""MF-P1d — the readers of the period MWRR on a period that opens at zero: no «10 %» on the day of its only deposit.

The pure defect is in ``financial_math/returns._mwrr_solve`` (see ``test_financial_math/test_mwrr_all_zero_flows.py``):
when every XIRR flow of a period is zero — it opens at NAV 0 and its only flow is a deposit on its last day, so
NAV_D + flow_D = 0 — Newton returns its starting guess ``_MWRR_GUESS`` = 0.1. The cure approved by the developer
(24/10/2026): no rate, the Dashboard shows «—». These tests pin what each reader hands out on such a day.

Which periods open at zero, measured on HEAD 270e85a55 with ``PortfolioService.get_report``:
- NOT a range that merely starts before the portfolio's first day: the engine's daily states start at the first
  transaction, so the period opens on that day with the deposit already inside its value (1000 > 0), and the bug does
  not reach the Dashboard that way (the probe gave 0 on every point, the first pinned);
- an account emptied and refunded (``_emptied_book``): deposits of 3 000 and 2 000, a withdrawal of 5 000 on 20/4/2025,
  a window opening on 1/5 at the emptied state (NAV 0), a re-deposit of 1 000 on 11/5, an INTEREST of 5 on 13/5;
- the whole history of a portfolio whose BUY is recorded before its DEPOSIT (``_buy_first_book``): BUY 10 at 100 on
  3/3/2025 (cash −1000, value +1000, NAV 0), DEPOSIT 1000 on 10/3, the price 100 → 110 on 20/3. No ``date_from``:
  the rebase-free path.

RED on HEAD 270e85a55 (every one reads the 0.1 of the solver's start, or its cumulative):
- TestEmptiedAndRefundedReport::test_history_point_on_the_redeposit_day_has_no_mwrr (0.100000 / 0.002615)
- TestEmptiedAndRefundedReport::test_report_json_carries_null_on_the_redeposit_day ("0.100000" in the JSON)
- TestEmptiedAndRefundedReport::test_card_ending_on_the_redeposit_day_has_no_mwrr (0.100000 / 0.002615, timing 0.002615)
- TestEmptiedAndRefundedReport::test_card_ending_on_the_redeposit_day_reports_mwrr_not_calculable (no issue reported)
- TestWholeHistoryOpeningAtZero::test_history_point_on_the_deposit_day_has_no_mwrr (0.100000 / 0.001830)
- TestAiExportPortfolioMwrr::test_summary_and_performance_have_no_mwrr (0.100000 in both payloads)

GREEN on HEAD, guards the cure must keep green (pinned from HEAD 270e85a55): every other history point of both books,
the card of the longer window (to 20/5), and the AI Export of that longer window.

Isolation: PURE with respect to the lane — every database is a private SQLite file under ``tmp_path`` (the app schema,
``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no server, no network. Every
amount is EUR and read in EUR. The report, WAC and engine blob caches are emptied around each test. No sleep, no
wall-clock dependency (every range is explicit), no translated text.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).

Reference: backend/app/services/portfolio_service.py (get_report, get_summary, get_history),
backend/app/services/financial_math/returns.py (period_mwrr, period_mwrr_series, _mwrr_solve),
backend/app/services/ai_export/components/portfolio_financial.py (portfolio.summary, portfolio.performance).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import IssueCode, PortfolioHistoryPoint, PortfolioReportQuery, PortfolioReportResponse, PortfolioSummary
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"

# The emptied-and-refunded book.
EMPTIED_WITHDRAWAL = date(2025, 4, 20)
WINDOW_OPEN = date(2025, 5, 1)
REDEPOSIT_DAY = date(2025, 5, 11)
INTEREST_DAY = date(2025, 5, 13)
WINDOW_END = date(2025, 5, 20)

# HEAD 270e85a55, window 1/5..20/5: (annualized, cumulative) of every point but the re-deposit day.
EMPTIED_HEAD: dict[date, tuple[str | None, str | None]] = {
    WINDOW_OPEN: ("0", "0"),  # the first point, pinned by get_history
    **{WINDOW_OPEN + timedelta(days=offset): (None, None) for offset in range(1, 10)},  # NAV 0: no capital
    date(2025, 5, 12): ("0.000000", "0.000000"),
    date(2025, 5, 13): ("1.484885", "0.030378"),
    date(2025, 5, 14): ("0.834584", "0.021848"),
    date(2025, 5, 15): ("0.576352", "0.017610"),
    date(2025, 5, 16): ("0.439204", "0.015075"),
    date(2025, 5, 17): ("0.354468", "0.013389"),
    date(2025, 5, 18): ("0.297014", "0.012186"),
    date(2025, 5, 19): ("0.255528", "0.011285"),
    date(2025, 5, 20): ("0.224182", "0.010585"),
}
# HEAD 270e85a55: the card of 1/5..20/5 — annualized, cumulative, days, timing effect, TWRR.
EMPTIED_CARD_HEAD = ("0.224182", "0.010585", 19, "0.005585", "0.005000")

# The buy-first book (whole history, no date_from).
BUY_DAY = date(2025, 3, 3)
LATE_DEPOSIT_DAY = date(2025, 3, 10)
PRICE_UP_DAY = date(2025, 3, 20)
BUY_FIRST_END = date(2025, 3, 25)
BUY_FIRST_HEAD: dict[date, tuple[str | None, str | None]] = {
    BUY_DAY: ("0", "0"),
    **{BUY_DAY + timedelta(days=offset): (None, None) for offset in range(1, 7)},  # NAV 0 until the deposit
    **{date(2025, 3, day): ("0.000000", "0.000000") for day in range(11, 20)},
    date(2025, 3, 20): ("31.421493", "0.175892"),
    date(2025, 3, 21): ("22.631133", "0.168782"),
    date(2025, 3, 22): ("17.156307", "0.162889"),
    date(2025, 3, 23): ("13.527110", "0.157927"),
    date(2025, 3, 24): ("10.999591", "0.153690"),
    date(2025, 3, 25): ("9.167683", "0.150030"),
}


# =============================================================================
# PRIVATE DATABASE
# =============================================================================


@asynccontextmanager
async def _private_engine(directory: Path, name: str) -> AsyncIterator[AsyncEngine]:
    """The app schema on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'p1d_{name}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int


def _cash(broker: Broker, tx_type: TransactionType, day: date, amount: str) -> Transaction:
    return Transaction(broker_id=broker.id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=EUR)


async def _new_owner(session: AsyncSession, label: str) -> tuple[User, Broker]:
    tag = uuid4().hex[:12]
    user = User(username=f"p1d_{label}_{tag}", email=f"p1d_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"P1d {label} {tag}")
    session.add_all([user, broker])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    return user, broker


async def _emptied_book(engine: AsyncEngine) -> _Book:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user, broker = await _new_owner(session, "emptied")
        session.add_all(
            [
                _cash(broker, TransactionType.DEPOSIT, date(2025, 1, 10), "3000"),
                _cash(broker, TransactionType.DEPOSIT, date(2025, 2, 10), "2000"),
                _cash(broker, TransactionType.WITHDRAWAL, EMPTIED_WITHDRAWAL, "-5000"),
                _cash(broker, TransactionType.DEPOSIT, REDEPOSIT_DAY, "1000"),
                _cash(broker, TransactionType.INTEREST, INTEREST_DAY, "5"),
            ]
        )
        await session.commit()
        return _Book(engine=engine, user_id=user.id)


async def _buy_first_book(engine: AsyncEngine) -> _Book:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user, broker = await _new_owner(session, "buyfirst")
        stock = Asset(display_name=f"P1d stock {uuid4().hex[:12]}", currency=EUR, asset_type=AssetType.STOCK)
        session.add(stock)
        await session.flush()
        session.add_all(
            [
                Transaction(broker_id=broker.id, asset_id=stock.id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
                _cash(broker, TransactionType.DEPOSIT, LATE_DEPOSIT_DAY, "1000"),
            ]
        )
        day = BUY_DAY
        while day <= BUY_FIRST_END:
            close = Decimal("110") if day >= PRICE_UP_DAY else Decimal("100")
            session.add(PriceHistory(asset_id=stock.id, date=day, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="p1d_test"))
            day += timedelta(days=1)
        await session.commit()
        return _Book(engine=engine, user_id=user.id)


async def _report(book: _Book, start: date | None, end: date) -> PortfolioReportResponse:
    query = PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=start, end=end),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=False,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


# =============================================================================
# HELPERS
# =============================================================================


def _shown(points: list[PortfolioHistoryPoint]) -> dict[date, tuple[str | None, str | None]]:
    return {point.date: (None if point.mwrr_annualized is None else str(point.mwrr_annualized), None if point.mwrr_cumulative is None else str(point.mwrr_cumulative)) for point in points}


def _history(report: PortfolioReportResponse) -> list[PortfolioHistoryPoint]:
    assert report.history, "the report has no history"
    return sorted(report.history, key=lambda point: point.date)


def _point_on(points: list[PortfolioHistoryPoint], day: date) -> PortfolioHistoryPoint:
    point = next((point for point in points if point.date == day), None)
    assert point is not None, f"no history point on {day} (the history spans {points[0].date}..{points[-1].date})"
    return point


def _card(summary: PortfolioSummary | None) -> tuple[str | None, str | None, int | None, str | None, str | None]:
    assert summary is not None, "the report has no summary"

    def text(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    return (text(summary.mwrr_annualized_percent), text(summary.mwrr_cumulative_percent), summary.mwrr_period_days, text(summary.timing_effect_percent), text(summary.twrr_percent))


def _reports_mwrr_not_calculable(summary: PortfolioSummary) -> bool:
    assert summary.data_quality is not None, "the summary carries no data-quality report"
    return any(issue.code == IssueCode.MWRR_NOT_CALCULABLE for issue in summary.data_quality.issues)


def _assert_opens_at_zero_and_deposit_lands(points: list[PortfolioHistoryPoint], opening: date, deposit_day: date) -> None:
    """Presence barrier: the history covers the period from its opening at NAV 0 to the deposit day, worth 1000 there."""
    assert points[0].date == opening, f"the history opens on {points[0].date}, expected {opening}"
    assert points[0].nav_value.amount == 0, f"precondition: the period should open at NAV 0, it opens at {points[0].nav_value.amount}"
    assert _point_on(points, deposit_day).nav_value.amount == Decimal("1000"), f"precondition: the value on {deposit_day} is {_point_on(points, deposit_day).nav_value.amount}, expected 1000"


# =============================================================================
# TESTS
# =============================================================================


class TestEmptiedAndRefundedReport:
    """The window opens on 1/5 at the emptied state (NAV 0); the only flow inside it is the re-deposit of 11/5."""

    @pytest.mark.asyncio
    async def test_history_point_on_the_redeposit_day_has_no_mwrr(self, tmp_path):
        """RED on HEAD: 0.100000 annualized, 0.002615 cumulative on 11/5."""
        async with _private_engine(tmp_path, "history") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, WINDOW_END)

        points = _history(report)
        _assert_opens_at_zero_and_deposit_lands(points, WINDOW_OPEN, REDEPOSIT_DAY)
        point = _point_on(points, REDEPOSIT_DAY)
        assert (point.mwrr_annualized, point.mwrr_cumulative) == (None, None), f"{REDEPOSIT_DAY}: every XIRR flow of the period ending there is 0, the line should show «—», got {_shown([point])}"

    @pytest.mark.asyncio
    async def test_history_other_points_unchanged(self, tmp_path):
        """GREEN guard: every other point as on HEAD."""
        async with _private_engine(tmp_path, "others") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, WINDOW_END)

        shown = _shown(_history(report))
        assert REDEPOSIT_DAY in shown, f"no point on {REDEPOSIT_DAY}"
        del shown[REDEPOSIT_DAY]
        assert shown == EMPTIED_HEAD

    @pytest.mark.asyncio
    async def test_report_json_carries_null_on_the_redeposit_day(self, tmp_path):
        """RED on HEAD: the JSON carries "0.100000". The report serialises either way."""
        async with _private_engine(tmp_path, "json") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, WINDOW_END)

        dumped = report.model_dump(mode="json")
        entry = next((row for row in dumped["history"] if row["date"] == REDEPOSIT_DAY.isoformat()), None)
        assert entry is not None, f"no JSON history entry on {REDEPOSIT_DAY}"
        assert (entry["mwrr_annualized"], entry["mwrr_cumulative"]) == (None, None), (entry["mwrr_annualized"], entry["mwrr_cumulative"])

    @pytest.mark.asyncio
    async def test_card_ending_on_the_redeposit_day_has_no_mwrr(self, tmp_path):
        """RED on HEAD: (0.100000, 0.002615, 10, timing 0.002615, TWRR 0.000000). After the cure the MWRR and the timing
        effect derived from it are None; the window length and the TWRR stay."""
        async with _private_engine(tmp_path, "card") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, REDEPOSIT_DAY)

        _assert_opens_at_zero_and_deposit_lands(_history(report), WINDOW_OPEN, REDEPOSIT_DAY)
        assert report.summary is not None and report.summary.net_worth.amount == Decimal("1000"), "precondition: the card's value at the end is 1000"
        assert _card(report.summary) == (None, None, 10, None, "0.000000"), f"the card of {WINDOW_OPEN}..{REDEPOSIT_DAY}: (annualized, cumulative, days, timing effect, TWRR) = {_card(report.summary)}"
        dumped = report.model_dump(mode="json")["summary"]
        assert (dumped["mwrr_annualized_percent"], dumped["mwrr_cumulative_percent"], dumped["timing_effect_percent"]) == (None, None, None)

    @pytest.mark.asyncio
    async def test_card_ending_on_the_redeposit_day_reports_mwrr_not_calculable(self, tmp_path):
        """RED on HEAD: the card has a (false) rate, so no MWRR_NOT_CALCULABLE. A «—» card reports it, as every other one."""
        async with _private_engine(tmp_path, "quality") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, REDEPOSIT_DAY)

        assert report.summary is not None
        assert _reports_mwrr_not_calculable(report.summary), f"the card is «—» on the re-deposit day: MWRR_NOT_CALCULABLE expected, card {_card(report.summary)}"

    @pytest.mark.asyncio
    async def test_card_of_the_longer_window_unchanged(self, tmp_path):
        """GREEN guard: the card of 1/5..20/5 as on HEAD."""
        async with _private_engine(tmp_path, "longer") as engine:
            report = await _report(await _emptied_book(engine), WINDOW_OPEN, WINDOW_END)

        assert _card(report.summary) == EMPTIED_CARD_HEAD


class TestWholeHistoryOpeningAtZero:
    """The BUY recorded before the DEPOSIT: the portfolio's first day is worth 0; no date_from (the rebase-free path)."""

    @pytest.mark.asyncio
    async def test_history_point_on_the_deposit_day_has_no_mwrr(self, tmp_path):
        """RED on HEAD: 0.100000 annualized, 0.001830 cumulative on 10/3."""
        async with _private_engine(tmp_path, "whole") as engine:
            report = await _report(await _buy_first_book(engine), None, BUY_FIRST_END)

        points = _history(report)
        _assert_opens_at_zero_and_deposit_lands(points, BUY_DAY, LATE_DEPOSIT_DAY)
        point = _point_on(points, LATE_DEPOSIT_DAY)
        assert (point.mwrr_annualized, point.mwrr_cumulative) == (None, None), f"{LATE_DEPOSIT_DAY}: every XIRR flow is 0, the line should show «—», got {_shown([point])}"

    @pytest.mark.asyncio
    async def test_history_other_points_unchanged(self, tmp_path):
        """GREEN guard: every other point as on HEAD, and the card of the whole history."""
        async with _private_engine(tmp_path, "whole_others") as engine:
            report = await _report(await _buy_first_book(engine), None, BUY_FIRST_END)

        shown = _shown(_history(report))
        assert LATE_DEPOSIT_DAY in shown, f"no point on {LATE_DEPOSIT_DAY}"
        del shown[LATE_DEPOSIT_DAY]
        assert shown == BUY_FIRST_HEAD
        assert _card(report.summary) == ("9.167683", "0.150030", 22, "0.050030", "0.100000")


class TestAiExportPortfolioMwrr:
    """AI Export reads the period MWRR from the card (``portfolio.summary``, ``portfolio.performance``): its «missing»
    value is None."""

    @staticmethod
    async def _payloads(book: _Book, period_end: date) -> tuple[dict, dict]:
        scope = BuildScope(
            request_id=f"p1d-{uuid4().hex}",
            user_id=book.user_id,
            domain=Domain.PORTFOLIO,
            detail_level=DetailLevel.STANDARD,
            period_start=WINDOW_OPEN,
            period_end=period_end,
            target_currency=EUR,
        )
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
            summary = await context.resolve("portfolio.summary", required=True)
            performance = await context.resolve("portfolio.performance", required=True)
        return summary.payload, performance.payload

    @staticmethod
    def _mwrr(payload: dict) -> tuple[object, object]:
        return payload["mwrr_annualized_percent"], payload["mwrr_cumulative_percent"]

    @pytest.mark.asyncio
    async def test_summary_and_performance_have_no_mwrr(self, tmp_path):
        """RED on HEAD: both payloads carry 0.100000 for the period 1/5..11/5."""
        async with _private_engine(tmp_path, "ai") as engine:
            summary, performance = await self._payloads(await _emptied_book(engine), REDEPOSIT_DAY)

        assert {"summary": self._mwrr(summary), "performance": self._mwrr(performance)} == {"summary": (None, None), "performance": (None, None)}

    @pytest.mark.asyncio
    async def test_longer_period_keeps_its_mwrr(self, tmp_path):
        """GREEN guard: the period 1/5..20/5 carries the card's rate in both payloads."""
        async with _private_engine(tmp_path, "ai_longer") as engine:
            summary, performance = await self._payloads(await _emptied_book(engine), WINDOW_END)

        expected = (Decimal(EMPTIED_CARD_HEAD[0]), Decimal(EMPTIED_CARD_HEAD[1]))
        got = {name: tuple(None if value is None else Decimal(str(value)) for value in self._mwrr(payload)) for name, payload in (("summary", summary), ("performance", performance))}
        assert got == {"summary": expected, "performance": expected}

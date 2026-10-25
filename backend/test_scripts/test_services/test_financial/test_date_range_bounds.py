"""R13-SEC7-1 — the portfolio engine, the report, the risk portfolio scope and the lots bound their date range.

An unbounded date range let any user freeze the instance. ``PortfolioCalculationEngine.calculate`` replayed every
day from ``date_from`` (else the first transaction) to ``date_to`` (else today) on the event loop, so
``POST /portfolio/report {"date_range": {"end": "9999-12-30"}}`` replayed ~2.9 M days, and a start of 0001-01-01
the same. ``POST /risk/query`` with a portfolio scope reaches that engine through the report it builds
(``risk.scope.load_scope_inputs``), and ``LotsAnalysisService.get_lots_analysis`` valued every day up to
``date_to``.

The bound these tests pin, read only through the public entry points (``max_end = today + 1 day``: one day of
slack for users east of UTC):

* engine — ``actual_to = min(date_to or today, max_end)``; a ``date_from`` before the first transaction starts at
  the first transaction; a range entirely before the first transaction has no daily state (and no exception);
* lots — ``actual_to = min(date_to or today, max_end)``.

Every red uses MODERATE values — 400 days ahead, 3000 days before the first transaction — that the old code
replays in seconds and returns, so the red run fails fast instead of hanging. The extreme values the API
accepts (9999-12-30, 0001-01-01) are in ``TestExtremeRangesFinishQuickly``: they would hang on the old code, so
deselect that class in the red run (``-k "date_range_bounds and not TestExtremeRangesFinishQuickly"``).

Every row is written on the test's own session and rolled back. The book is relative to today (first
transaction 60 days ago), so the tests never age. ``today`` is read before and after the call under test: a
run that crosses midnight may legitimately see either day, so an equality on today or tomorrow accepts both.

J-49 — ``TestRangeBoundSeamCoversEveryReader``, pure (no database): the seam that lifts this bound for the far-future
suites (``_range_bounds.lift_range_bound``) replaces ``latest_range_end`` by name; the class holds its list of modules
to exactly the modules of ``backend/app`` that bind that name.
"""

import ast
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.risk.service as risk_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.schemas.risk import RiskQueryRequest
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.app.services.portfolio_service import PortfolioService, _portfolio_l2_cache
from backend.app.services.risk.scope import load_scope_inputs
from backend.app.services.risk.service import RiskService
from backend.test_scripts.test_services._range_bounds import RANGE_BOUND_CONSUMERS

ONE_DAY = timedelta(days=1)
FIRST_TX_DAYS_AGO = 60
# Moderate values: the old code replays them in seconds and returns them, so a red fails fast.
AHEAD = timedelta(days=400)
BEHIND = timedelta(days=3000)
# The extreme values the API accepts: on the old code they hang (TestExtremeRangesFinishQuickly only).
EXTREME_START = date(1, 1, 1)
EXTREME_END = date(9999, 12, 30)
QUICK_SECONDS = 30


# =============================================================================
# FIXTURES
# =============================================================================


@dataclass(frozen=True)
class OwnedBook:
    """One user's book, created on the test's own session: its ids and the dates the assertions read."""

    user_id: int
    broker_id: int
    first_tx: date
    asset_id: int | None = None
    last_quote: date | None = None


@pytest.fixture(scope="module")
def db_engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(db_engine):
    async with AsyncSession(db_engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.fixture(autouse=True)
def fresh_portfolio_caches():
    """The engine's blob cache and the report's L2 cache live in the process: every test starts and ends
    without them, so no result is served from another test's run."""
    portfolio_engine_module._portfolio_blob_cache.clear()
    _portfolio_l2_cache.clear()
    yield
    portfolio_engine_module._portfolio_blob_cache.clear()
    _portfolio_l2_cache.clear()


async def _seed_book(session: AsyncSession, *, with_position: bool) -> OwnedBook:
    """10 000 EUR deposited 60 days ago; with a position, 10 units bought the day after at 100 and quoted 100
    then 110 (30 days after the deposit). Every name carries a fresh uuid: nothing collides with a neighbour."""
    marker = uuid4().hex
    first_tx = date.today() - timedelta(days=FIRST_TX_DAYS_AGO)
    user = User(username=f"r13sec7_{marker}", email=f"r13sec7_{marker}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"R13-SEC7-1 broker {marker}")
    session.add_all([user, broker])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    session.add(Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=first_tx, amount=Decimal("10000"), currency="EUR"))
    if not with_position:
        await session.flush()
        return OwnedBook(user_id=user.id, broker_id=broker.id, first_tx=first_tx)

    asset = Asset(display_name=f"R13-SEC7-1 asset {marker}", identifier_ticker=f"R13{marker[:8].upper()}", currency="EUR", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    bought = first_tx + ONE_DAY
    last_quote = first_tx + timedelta(days=30)
    session.add_all(
        [
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=bought, quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
            PriceHistory(asset_id=asset.id, date=bought, close=Decimal("100"), currency="EUR", source_plugin_key="r13_sec7_1_test"),
            PriceHistory(asset_id=asset.id, date=last_quote, close=Decimal("110"), currency="EUR", source_plugin_key="r13_sec7_1_test"),
        ]
    )
    await session.flush()
    return OwnedBook(user_id=user.id, broker_id=broker.id, first_tx=first_tx, asset_id=asset.id, last_quote=last_quote)


@pytest_asyncio.fixture
async def book(session) -> OwnedBook:
    """A deposit, a position bought the day after, two quotes."""
    return await _seed_book(session, with_position=True)


@pytest_asyncio.fixture
async def cash_book(session) -> OwnedBook:
    """A deposit and nothing else: no asset is held, so a risk query reads the portfolio TWRR on every calendar
    day of the report instead of on the days a held asset was quoted."""
    return await _seed_book(session, with_position=False)


# =============================================================================
# HELPERS
# =============================================================================


def _tomorrows(before: date, after: date) -> set[date]:
    """max_end as the service may have read it: tomorrow of the day read before the call, or after it."""
    return {before + ONE_DAY, after + ONE_DAY}


def _state_dates(result) -> list[date]:
    return [state.date for state in result.daily_states]


async def _calculate(session: AsyncSession, book: OwnedBook, **kwargs):
    return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, broker_ids=[book.broker_id], target_currency="EUR", **kwargs)


async def _report(session: AsyncSession, book: OwnedBook, *, start: date, end: date):
    """POST /portfolio/report's service with the Dashboard's sections: summary, history, allocation history."""
    query = PortfolioReportQuery(
        broker_ids=[book.broker_id],
        target_currency="EUR",
        date_range=OpenDateRangeModel(start=start, end=end),
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
    )
    return await PortfolioService(session).get_report(user_id=book.user_id, query=query)


async def _lots(session: AsyncSession, book: OwnedBook, *, date_to: date | None):
    return await get_lots_analysis(
        session=session,
        user_id=book.user_id,
        asset_id=book.asset_id,
        broker_ids=[book.broker_id],
        date_from=None,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=["VALUE_HISTORY", "PRICE_HISTORY"],
    )


def _risk_request(book: OwnedBook, *, start: date, end: date) -> RiskQueryRequest:
    """POST /risk/query's body: this book's broker as a portfolio scope, historical KPIs."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "portfolio", "broker_ids": [book.broker_id]},
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [{"instance_id": "kpi", "analytic_code": "historical_kpi"}],
        }
    )


async def _no_market_holidays() -> frozenset[date]:
    """The holiday table is built in a spawned QuantLib process; the range bound does not read it."""
    return frozenset()


def _history_dates(points) -> list[date]:
    return [point.date for point in points or []]


def _last_day(steps) -> date:
    """The last day a lots history covers: its last step's ``through`` (J5-5: a row holds from ``date`` to ``through``)."""
    return max(step.through for step in steps)


# =============================================================================
# ENGINE — PortfolioCalculationEngine.calculate
# =============================================================================


class TestEngineBoundsTheRange:
    @pytest.mark.asyncio
    async def test_date_to_after_tomorrow_stops_at_tomorrow(self, session, book):
        """Red (R13-SEC7-1): a date_to 400 days ahead is clamped to tomorrow (max_end = today + 1): the result's
        date_to is tomorrow and no daily state is dated after it.

        Before: actual_to = date_to — the replay ran every day to the requested end and returned a state for each
        of the 400 future days (with 9999-12-30, ~2.9 M days on the event loop)."""
        before = date.today()
        result = await _calculate(session, book, date_to=before + AHEAD)
        after = date.today()

        assert result.daily_states, "the book has a deposit 60 days ago: the result must have daily states"
        assert max(_state_dates(result)) <= after + ONE_DAY, f"daily states run to {max(_state_dates(result))}, past tomorrow ({after + ONE_DAY})"
        assert result.date_to in _tomorrows(before, after), f"result.date_to is {result.date_to}, expected tomorrow ({before + ONE_DAY})"
        assert max(_state_dates(result)) == result.date_to, "the last daily state must be the result's date_to"

    @pytest.mark.asyncio
    async def test_date_from_before_first_transaction_starts_at_first_transaction(self, session, book):
        """Red (R13-SEC7-1): a date_from 3000 days before the first transaction starts the result at the first
        transaction: result.date_from and the first daily state are the first transaction's day.

        Before: actual_from = date_from — 3000 empty days before the first transaction were replayed and returned
        (with 0001-01-01, ~740 000)."""
        result = await _calculate(session, book, date_from=book.first_tx - BEHIND)

        assert result.daily_states, "the book has a deposit 60 days ago: the result must have daily states"
        assert min(_state_dates(result)) == book.first_tx, f"the first daily state is {min(_state_dates(result))}, expected the first transaction ({book.first_tx})"
        assert result.date_from == book.first_tx, f"result.date_from is {result.date_from}, expected the first transaction ({book.first_tx})"

    @pytest.mark.asyncio
    async def test_range_entirely_before_first_transaction_has_no_daily_state(self, session, book):
        """Red (R13-SEC7-1): a range that ends before the first transaction has no day to replay — no daily
        state, and no exception.

        Before: the requested 2001 empty days, from 3000 to 1000 days before the first transaction, were
        replayed and returned."""
        result = await _calculate(session, book, date_from=book.first_tx - BEHIND, date_to=book.first_tx - timedelta(days=1000))

        assert result.daily_states == [], f"{len(result.daily_states)} daily states returned for a range that ends before the first transaction"


class TestEngineRangesWithinBoundsAreUnchanged:
    @pytest.mark.asyncio
    async def test_range_inside_the_history_is_replayed_as_before(self, session, book):
        """Guard: a range that starts after the first transaction and ends today gives the states it always
        gave — one a day, from date_from to date_to."""
        today = date.today()
        date_from = book.first_tx + timedelta(days=5)

        result = await _calculate(session, book, date_from=date_from, date_to=today)

        dates = _state_dates(result)
        assert (result.date_from, result.date_to) == (date_from, today)
        assert (dates[0], dates[-1]) == (date_from, today), f"states run {dates[0]}..{dates[-1]}, expected {date_from}..{today}"
        assert len(dates) == (today - date_from).days + 1, "one daily state per day of the range"

    @pytest.mark.asyncio
    async def test_without_date_to_the_result_ends_today(self, session, book):
        """Guard: without date_to the result ends today, as before — the bound is tomorrow, it never replaces
        today as the default end."""
        before = date.today()
        result = await _calculate(session, book)
        after = date.today()

        assert result.date_to in {before, after}, f"result.date_to is {result.date_to}, expected today ({before})"
        assert max(_state_dates(result)) == result.date_to
        assert (result.date_from, min(_state_dates(result))) == (book.first_tx, book.first_tx)

    @pytest.mark.asyncio
    async def test_date_to_tomorrow_is_kept(self, session, book):
        """Guard: tomorrow is inside the bound (one day of slack for users east of UTC): a date_to of tomorrow is
        replayed exactly, not cut to today."""
        tomorrow = date.today() + ONE_DAY

        result = await _calculate(session, book, date_to=tomorrow)

        assert result.date_to == tomorrow
        assert max(_state_dates(result)) == tomorrow

    @pytest.mark.asyncio
    async def test_date_from_on_the_first_transaction_is_kept(self, session, book):
        """Guard: a date_from on the first transaction is not moved, and a past date_to is not touched."""
        date_to = book.first_tx + timedelta(days=10)

        result = await _calculate(session, book, date_from=book.first_tx, date_to=date_to)

        dates = _state_dates(result)
        assert (result.date_from, result.date_to) == (book.first_tx, date_to)
        assert (dates[0], dates[-1]) == (book.first_tx, date_to)


# =============================================================================
# REPORT — PortfolioService.get_report (POST /portfolio/report)
# =============================================================================


class TestReportBoundsTheRange:
    @pytest.mark.asyncio
    async def test_report_history_stops_at_tomorrow_and_starts_at_first_transaction(self, session, book):
        """Red (R13-SEC7-1): the report asked for 3000 days before the first transaction to 400 days ahead has
        no history point after tomorrow, and metadata.computed_date_to is tomorrow.

        Before: the engine replayed every day to the requested end, so the history carried a point for each of
        the 400 future days and computed_date_to was the requested end (with 9999-12-30, the reported freeze).
        The lower end already held — get_report runs the engine from the first transaction (date_from=None) —
        and is pinned so the bound does not move it: no point before the first transaction."""
        before = date.today()
        report = await _report(session, book, start=book.first_tx - BEHIND, end=before + AHEAD)
        after = date.today()

        dates = _history_dates(report.history)
        assert dates, "the report has no history at all"
        assert max(dates) <= after + ONE_DAY, f"the history runs to {max(dates)}, past tomorrow ({after + ONE_DAY})"
        assert report.metadata.computed_date_to in _tomorrows(before, after), f"computed_date_to is {report.metadata.computed_date_to}, expected tomorrow ({before + ONE_DAY})"
        assert min(dates) == book.first_tx, f"the history starts on {min(dates)}, expected the first transaction ({book.first_tx})"
        assert report.metadata.computed_date_from == book.first_tx


class TestReportRangesWithinBoundsAreUnchanged:
    @pytest.mark.asyncio
    async def test_report_inside_the_history_is_unchanged(self, session, book):
        """Guard: a report from five days after the first transaction to today is the one it always was — its
        history covers exactly that range, and the engine still runs from the first transaction."""
        today = date.today()
        start = book.first_tx + timedelta(days=5)

        report = await _report(session, book, start=start, end=today)

        dates = _history_dates(report.history)
        assert (dates[0], dates[-1]) == (start, today), f"history runs {dates[0]}..{dates[-1]}, expected {start}..{today}"
        assert len(dates) == (today - start).days + 1, "one history point per day of the range"
        assert (report.metadata.computed_date_from, report.metadata.computed_date_to) == (book.first_tx, today)


# =============================================================================
# RISK, PORTFOLIO SCOPE — RiskService.execute (POST /risk/query) and the report it builds
# =============================================================================


class TestRiskPortfolioScopeBoundsTheRange:
    @pytest.mark.asyncio
    async def test_scope_inputs_report_stops_at_tomorrow(self, session, book):
        """Red (R13-SEC7-1): load_scope_inputs — what RiskService.execute runs for a portfolio scope — asked for a
        window ending 400 days ahead builds a report whose history and computed range stop at tomorrow.

        Before: the report it builds replayed every requested day (risk/scope.py calls PortfolioService.get_report
        with the raw window), so the series the analytics read ran 400 days past today."""
        before = date.today()
        inputs = await load_scope_inputs(session, user_id=book.user_id, request=_risk_request(book, start=book.first_tx - BEHIND, end=before + AHEAD))
        after = date.today()

        report = inputs.portfolio_report
        assert report is not None, "a portfolio scope must carry the report it was built from"
        dates = _history_dates(report.history)
        assert dates, "the scope's report has no history at all"
        assert max(dates) <= after + ONE_DAY, f"the scope's report runs to {max(dates)}, past tomorrow ({after + ONE_DAY})"
        assert report.metadata.computed_date_to in _tomorrows(before, after)
        assert min(dates) == book.first_tx

    @pytest.mark.asyncio
    async def test_risk_query_analyzed_range_stops_at_tomorrow(self, session, cash_book, monkeypatch):
        """Red (R13-SEC7-1): POST /risk/query's service, portfolio scope in historical mode, window ending 400 days
        ahead — the result's metadata.analyzed_range ends no later than tomorrow.

        The book holds cash only, so the portfolio TWRR is read on every calendar day of the report and the
        analyzed range ends where the report ends (with a held asset it would end at its last quote whatever the
        bound). TestRiskPortfolioScopeWithinBoundsIsUnchanged pins that premise.

        Before: the report ran to the requested end and the analyzed range with it, 400 days past today."""
        monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)
        before = date.today()
        response = await RiskService(session).execute(user_id=cash_book.user_id, request=_risk_request(cash_book, start=cash_book.first_tx, end=before + AHEAD))
        after = date.today()

        (item,) = response.items
        assert item.metadata is not None, f"the KPI result carries no metadata: {item.status} {item.error}"
        assert item.metadata.analyzed_range.end <= after + ONE_DAY, f"analyzed_range ends {item.metadata.analyzed_range.end}, past tomorrow ({after + ONE_DAY})"


class TestRiskPortfolioScopeWithinBoundsIsUnchanged:
    @pytest.mark.asyncio
    async def test_risk_query_analyzed_range_is_the_reports(self, session, cash_book, monkeypatch):
        """Guard: inside the bounds the analyzed range is read from the report, not echoed from the request — for a
        cash-only portfolio from its deposit to today, the first return is the day after the deposit and the last
        is today. It is the premise that makes the red above able to turn green."""
        monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)
        today = date.today()

        response = await RiskService(session).execute(user_id=cash_book.user_id, request=_risk_request(cash_book, start=cash_book.first_tx, end=today))

        (item,) = response.items
        assert item.metadata is not None, f"the KPI result carries no metadata: {item.status} {item.error}"
        analyzed = item.metadata.analyzed_range
        assert (analyzed.start, analyzed.end) == (cash_book.first_tx + ONE_DAY, today), f"analyzed_range is {analyzed.start}..{analyzed.end}"


# =============================================================================
# LOTS — LotsAnalysisService.get_lots_analysis (POST /portfolio/lots/analysis)
# =============================================================================


class TestLotsBoundTheRange:
    @pytest.mark.asyncio
    async def test_date_to_after_tomorrow_stops_at_tomorrow(self, session, book):
        """Red (R13-SEC7-1): the lots analysis with a date_to 400 days ahead computes to tomorrow —
        calculation_metadata.computed_date_to is tomorrow, and neither the value nor the price history has a
        day after it.

        Before: actual_to = date_to — every day from the first transaction to the requested end was valued
        (history_dates) and computed_date_to echoed it (with 9999-12-30, ~2.9 M days)."""
        before = date.today()
        result = await _lots(session, book, date_to=before + AHEAD)
        after = date.today()

        assert result.value_history and result.price_history, "an open lot must have a value and a price history"
        last_value, last_price = _last_day(result.value_history), _last_day(result.price_history)
        assert last_value <= after + ONE_DAY, f"the value history runs to {last_value}, past tomorrow ({after + ONE_DAY})"
        assert last_price <= after + ONE_DAY, f"the price history runs to {last_price}, past tomorrow ({after + ONE_DAY})"
        assert result.calculation_metadata.computed_date_to in _tomorrows(before, after), f"computed_date_to is {result.calculation_metadata.computed_date_to}, expected tomorrow ({before + ONE_DAY})"


class TestLotsRangesWithinBoundsAreUnchanged:
    @pytest.mark.asyncio
    async def test_without_date_to_the_histories_end_today(self, session, book):
        """Guard: without date_to the lots are computed to today, as before."""
        before = date.today()
        result = await _lots(session, book, date_to=None)
        after = date.today()

        computed_to = result.calculation_metadata.computed_date_to
        assert computed_to in {before, after}, f"computed_date_to is {computed_to}, expected today ({before})"
        assert _last_day(result.value_history) == computed_to
        assert _last_day(result.price_history) == computed_to

    @pytest.mark.asyncio
    async def test_past_date_to_is_kept(self, session, book):
        """Guard: a date_to in the past (the last quote) is computed exactly to that day."""
        result = await _lots(session, book, date_to=book.last_quote)

        assert result.calculation_metadata.computed_date_to == book.last_quote
        assert _last_day(result.value_history) == book.last_quote
        assert _last_day(result.price_history) == book.last_quote

    @pytest.mark.asyncio
    async def test_date_to_tomorrow_is_kept(self, session, book):
        """Guard: tomorrow is inside the bound (one day of slack for users east of UTC): a date_to of tomorrow is
        computed exactly, not cut to today."""
        tomorrow = date.today() + ONE_DAY

        result = await _lots(session, book, date_to=tomorrow)

        assert result.calculation_metadata.computed_date_to == tomorrow
        assert _last_day(result.value_history) == tomorrow


# =============================================================================
# EXTREME VALUES — new code only
# =============================================================================


class TestExtremeRangesFinishQuickly:
    """Guards (new code only): the extreme values the API accepts — 9999-12-30, 0001-01-01 — come back bounded,
    well within QUICK_SECONDS.

    On the old code every test here replays millions of days on the event loop (minutes, and as many state
    objects): it HANGS rather than fails. Deselect this class in the red run with
    ``-k "date_range_bounds and not TestExtremeRangesFinishQuickly"``."""

    @pytest.mark.asyncio
    async def test_engine_with_end_9999_12_30(self, session, book):
        """Guard (new code only; hangs on the old code): the engine asked to 9999-12-30 stops at tomorrow, fast."""
        before = date.today()
        started = time.monotonic()
        result = await _calculate(session, book, date_to=EXTREME_END)
        elapsed = time.monotonic() - started
        after = date.today()

        assert elapsed < QUICK_SECONDS, f"the engine took {elapsed:.1f}s for date_to={EXTREME_END}"
        assert result.date_to in _tomorrows(before, after)
        assert max(_state_dates(result)) == result.date_to

    @pytest.mark.asyncio
    async def test_engine_with_start_0001_01_01(self, session, book):
        """Guard (new code only; hangs on the old code): the engine asked from 0001-01-01 starts at the first
        transaction, fast."""
        started = time.monotonic()
        result = await _calculate(session, book, date_from=EXTREME_START)
        elapsed = time.monotonic() - started

        assert elapsed < QUICK_SECONDS, f"the engine took {elapsed:.1f}s for date_from={EXTREME_START}"
        assert result.date_from == book.first_tx
        assert min(_state_dates(result)) == book.first_tx

    @pytest.mark.asyncio
    async def test_report_from_0001_01_01_to_9999_12_30(self, session, book):
        """Guard (new code only; hangs on the old code): the reported request itself — POST /portfolio/report
        from 0001-01-01 to 9999-12-30 — completes fast, with a history from the first transaction to tomorrow."""
        before = date.today()
        started = time.monotonic()
        report = await _report(session, book, start=EXTREME_START, end=EXTREME_END)
        elapsed = time.monotonic() - started
        after = date.today()

        assert elapsed < QUICK_SECONDS, f"the report took {elapsed:.1f}s for {EXTREME_START}..{EXTREME_END}"
        dates = _history_dates(report.history)
        assert dates, "the report has no history at all"
        assert min(dates) == book.first_tx, f"the history starts on {min(dates)}, expected the first transaction ({book.first_tx})"
        assert max(dates) in _tomorrows(before, after), f"the history ends on {max(dates)}, expected tomorrow ({before + ONE_DAY})"
        assert report.metadata.computed_date_to in _tomorrows(before, after)

    @pytest.mark.asyncio
    async def test_lots_with_end_9999_12_30(self, session, book):
        """Guard (new code only; hangs on the old code): the lots asked to 9999-12-30 are computed to tomorrow,
        fast."""
        before = date.today()
        started = time.monotonic()
        result = await _lots(session, book, date_to=EXTREME_END)
        elapsed = time.monotonic() - started
        after = date.today()

        assert elapsed < QUICK_SECONDS, f"the lots analysis took {elapsed:.1f}s for date_to={EXTREME_END}"
        assert result.calculation_metadata.computed_date_to in _tomorrows(before, after)
        assert _last_day(result.value_history) <= after + ONE_DAY


# =============================================================================
# J-49 — THE RANGE-BOUND SEAM COVERS EVERY READER (pure: no database)
# =============================================================================

#: The module that defines the ceiling, its package, and the name the seam replaces.
_CEILING_MODULE = "backend.app.utils.datetime_utils"
_CEILING_PACKAGE, _, _CEILING_MODULE_NAME = _CEILING_MODULE.rpartition(".")
_CEILING_NAME = "latest_range_end"
_APP_ROOT = PROJECT_ROOT / "backend" / "app"
_DEFINING_FILE = _APP_ROOT / "utils" / "datetime_utils.py"  # defines the name: never a reader
#: The dotted name the detector's fake sources pretend to have: a relative import resolves against it.
_FAKE_MODULE = "backend.app.services.fake_reader"


@dataclass(frozen=True)
class _CeilingReading:
    """How one module reaches ``latest_range_end``: the lines that bind the name at module level — the one form the seam
    replaces — and every other way, each as ``(line, what)``."""

    binding_lines: tuple[int, ...]
    violations: tuple[tuple[int, str], ...]


def _dotted_name(node: ast.expr) -> str | None:
    """``a.b.c`` for a name and its chain of attributes; None for any other expression."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _absolute_module(node: ast.ImportFrom, *, module: str, is_package: bool) -> str | None:
    """The module a ``from … import`` reads from, its relative form resolved against ``module`` as Python resolves it."""
    if node.level == 0:
        return node.module
    package = module.split(".") if is_package else module.split(".")[:-1]
    if node.level - 1 >= len(package):
        return None
    base = package[: len(package) - (node.level - 1)]
    return ".".join([*base, node.module] if node.module else base)


def _nodes_with_scope(tree: ast.Module) -> list[tuple[ast.AST, bool]]:
    """Every node of ``tree``, with whether it sits in a function or a class body: an import there binds no name of the
    module."""
    found: list[tuple[ast.AST, bool]] = []
    pending = [(child, False) for child in ast.iter_child_nodes(tree)]
    while pending:
        node, nested = pending.pop()
        found.append((node, nested))
        inner = nested or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
        pending.extend((child, inner) for child in ast.iter_child_nodes(node))
    return found


def _what_is_wrong(alias: ast.alias, nested: bool) -> str | None:
    """None for ``latest_range_end`` imported under its own name at module level: the one binding the seam replaces."""
    if alias.asname not in (None, _CEILING_NAME):
        return f"imported as {alias.asname}"
    if nested:
        return "imported inside a function or a class"
    return None


def _ceiling_imports(nodes: list[tuple[ast.AST, bool]], *, module: str, is_package: bool) -> tuple[set[str], list[tuple[int, str | None]]]:
    """The names a module gives the ceiling's module object, and each import of the name itself as ``(line, what is
    wrong)`` — None when it binds the name."""
    module_object_names = {_CEILING_MODULE}  # the full dotted path, whatever import brought the package in
    name_imports: list[tuple[int, str | None]] = []
    for node, nested in nodes:
        if isinstance(node, ast.Import):
            module_object_names.update(alias.asname for alias in node.names if alias.name == _CEILING_MODULE and alias.asname)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        imported_from = _absolute_module(node, module=module, is_package=is_package)
        for alias in node.names:
            if imported_from == _CEILING_PACKAGE and alias.name == _CEILING_MODULE_NAME:
                module_object_names.add(alias.asname or alias.name)
            elif imported_from == _CEILING_MODULE and alias.name == _CEILING_NAME:
                name_imports.append((alias.lineno, _what_is_wrong(alias, nested)))
    return module_object_names, name_imports


def _read_ceiling_use(source: str, *, module: str, is_package: bool = False) -> _CeilingReading:
    """The detector. Binding: ``from backend.app.utils.datetime_utils import latest_range_end``, absolute or relative, at
    module level. Violations: that import under another name, or inside a function or a class; and any use through the
    module object — ``import backend.app.utils.datetime_utils [as x]`` or ``from backend.app.utils import datetime_utils
    [as x]``, then ``<that name>.latest_range_end``. A docstring or a comment is no code: never found."""
    nodes = _nodes_with_scope(ast.parse(source))
    module_object_names, name_imports = _ceiling_imports(nodes, module=module, is_package=is_package)
    violations = [(line, wrong) for line, wrong in name_imports if wrong is not None]
    for node, _nested in nodes:
        if isinstance(node, ast.Attribute) and node.attr == _CEILING_NAME:
            owner = _dotted_name(node.value)
            if owner in module_object_names:
                violations.append((node.lineno, f"read as {owner}.{_CEILING_NAME}"))
    return _CeilingReading(binding_lines=tuple(sorted(line for line, wrong in name_imports if wrong is None)), violations=tuple(sorted(violations)))


def _module_of(path: Path) -> tuple[str, bool]:
    """The dotted name of the module at ``path`` under the project root, and whether it is a package's ``__init__``."""
    parts = path.relative_to(PROJECT_ROOT).with_suffix("").parts
    if parts[-1] == "__init__":
        return ".".join(parts[:-1]), True
    return ".".join(parts), False


def _fake_reader(import_line: str, call: str) -> str:
    """A fake module: ``import_line`` on line 1, then a function that calls ``<call>()`` on line 5."""
    return f"{import_line}\n\n\ndef window_end(day):\n    return min(day, {call}())\n"


_IMPORT_INSIDE_A_FUNCTION = "def window_end(day):\n    from backend.app.utils.datetime_utils import latest_range_end\n\n    return min(day, latest_range_end())\n"
_ONLY_MENTIONS = (
    '"""The range ends at latest_range_end(), tomorrow: datetime_utils.latest_range_end is the one ceiling."""\n'
    "\n"
    "# latest_range_end() is read by the consumers, never here.\n"
    "\n"
    "\n"
    "def latest_range_end():\n"
    '    """An unrelated local helper that happens to share the name."""\n'
    "    return None\n"
    "\n"
    "\n"
    "LAST = latest_range_end()\n"
)


class TestRangeBoundSeamCoversEveryReader:
    """J-49 — the range-bound seam reaches every module that reads the ceiling, through the one name it replaces.

    The suites whose scenarios live in 2032–2091, so that they own their rows, run with ``_range_bounds.lift_range_bound``:
    it makes ``latest_range_end()`` answer ``date.max`` by replacing the name in each module of ``RANGE_BOUND_CONSUMERS``,
    and a seam by name reaches only a module that binds ``latest_range_end`` itself, with ``from
    backend.app.utils.datetime_utils import latest_range_end`` at module level. That list is kept by hand — X-R55 added two
    readers to it, SEC8-1b reused ``risk/scope.py`` — and nothing checked it against the code: a new reader nobody adds
    cuts those suites at tomorrow, and a reader that reaches the ceiling another way (an alias, the module object, an
    import inside a function) escapes the seam even when it is listed. Pure: an ``ast`` scan of ``backend/app``, no
    database.
    """

    def test_the_seam_lists_exactly_the_modules_that_bind_the_ceiling_by_name(self):
        """The rule: every ``.py`` under ``backend/app`` but ``utils/datetime_utils.py`` (it defines the name) is read by
        the detector. No module may reach the ceiling but by the binding import (each violation named ``path:line``), and
        the modules that bind it, as dotted names, are exactly ``RANGE_BOUND_CONSUMERS``: one missing from the list has
        its far-future suites cut at tomorrow; one listed that binds nothing is a seam that patches nothing — its
        ``monkeypatch.setattr`` would raise at run time, said here without running it.
        """
        files = sorted(_APP_ROOT.rglob("*.py"))
        assert _DEFINING_FILE in files, f"the scan does not walk backend/app: {_DEFINING_FILE} is not under {_APP_ROOT}"
        binding: set[str] = set()
        violations: list[str] = []
        for path in files:
            if path == _DEFINING_FILE:
                continue
            module, is_package = _module_of(path)
            reading = _read_ceiling_use(path.read_text(encoding="utf-8"), module=module, is_package=is_package)
            if reading.binding_lines:
                binding.add(module)
            violations.extend(f"{path.relative_to(PROJECT_ROOT)}:{line}: {what}" for line, what in reading.violations)
        listed = set(RANGE_BOUND_CONSUMERS)

        findings = {
            "violations: readers the by-name seam cannot reach": violations,
            "binding but missing from RANGE_BOUND_CONSUMERS: their far-future suites are cut at tomorrow": sorted(binding - listed),
            "listed but not binding: the seam patches nothing there (its setattr raises at run time)": sorted(listed - binding),
        }
        assert findings == dict.fromkeys(findings, [])

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            pytest.param(_fake_reader("from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, latest_range_end", "latest_range_end"), ([1], []), id="plain-import-binds"),
            pytest.param(_fake_reader("from ..utils.datetime_utils import latest_range_end", "latest_range_end"), ([1], []), id="relative-import-binds"),
            pytest.param(_fake_reader("from backend.app.utils.datetime_utils import latest_range_end as ceiling", "ceiling"), ([], [(1, "imported as ceiling")]), id="aliased-import"),
            pytest.param(_IMPORT_INSIDE_A_FUNCTION, ([], [(2, "imported inside a function or a class")]), id="import-inside-a-function"),
            pytest.param(_fake_reader("from backend.app.utils import datetime_utils", "datetime_utils.latest_range_end"), ([], [(5, "read as datetime_utils.latest_range_end")]), id="from-package-module-object"),
            pytest.param(_fake_reader("from backend.app.utils import datetime_utils as dates", "dates.latest_range_end"), ([], [(5, "read as dates.latest_range_end")]), id="from-package-module-object-aliased"),
            pytest.param(_fake_reader("import backend.app.utils.datetime_utils as du", "du.latest_range_end"), ([], [(5, "read as du.latest_range_end")]), id="import-module-object-aliased"),
            pytest.param(_fake_reader("import backend.app.utils.datetime_utils", "backend.app.utils.datetime_utils.latest_range_end"), ([], [(5, "read as backend.app.utils.datetime_utils.latest_range_end")]), id="import-module-object-dotted"),
            pytest.param(_fake_reader("from backend.app.utils import datetime_utils", "datetime_utils.utcnow"), ([], []), id="module-object-for-another-helper"),
            pytest.param(_ONLY_MENTIONS, ([], []), id="docstring-comment-and-unrelated-local-function"),
        ],
    )
    def test_the_detector_finds_exactly_what_a_fake_source_does_with_the_ceiling(self, source, expected):
        """The detector's own proof, on fake sources and never on files: what it finds — the binding lines, and every
        violation with its line — is asserted exactly, so a detector that finds nothing fails every case with something
        to find, and one that finds too much fails the last two: a module reading another helper through the module
        object, and one that only mentions the name (a docstring, a comment) or defines an unrelated function of that
        name. A relative import binds as the absolute one does; an import inside a function or a class binds no name of
        the module, so the seam cannot reach it.
        """
        reading = _read_ceiling_use(source, module=_FAKE_MODULE)

        assert (list(reading.binding_lines), list(reading.violations)) == expected

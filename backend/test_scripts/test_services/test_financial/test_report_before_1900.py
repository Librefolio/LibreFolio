"""MF-PAV-L1 — the portfolio report loses the 1 January 1900 date floor: its history starts on the first row, and costs like the steps.

Until now ``PortfolioCalculationEngine.calculate`` started its frame at ``max(date_from, first transaction, 1900-01-01)``:
a book whose first row is dated before 1900 (stored by an older version, or by a hand edit: the write floor,
``transaction_date_bounds``, still refuses it through the API) was replayed from its own date but reported from 1900. The
contract after L1: the frame, the report's ``range`` and every series start on the first row — even ``0001-01-03``, a typo
of the year. The cost follows the engine's segments (D-P4: steps), not the days: ~740 000 days from the typo to 2025, a
few hundred segments.

The book (report EUR, user U owns brokers A and B at share 1; rows inserted directly in a private database, never through
the API):

- B deposits 1000 EUR on 0001-01-03 (Tuesday of year 1) and nothing else ever happens to B: one step of ~2024 years.
- A: deposit 10 000 on 2025-01-02, buy 50 X (an EUR ETF) for 5000 on 01-03, buy 10 Y (a USD stock) for 900 EUR on 01-06,
  sell 10 X for 1100 on 03-17. X, Y and EUR/USD are quoted every weekday 2025-01-02 (Y and EUR/USD: 01-06) to 2025-04-30,
  nothing after: the stale tail to the end.
- The report ends on 2025-06-30 (explicit, so no wall clock). Windows: «all» (``start=None``) and 1Y (2024-06-30 to the end).

``include_summary``, ``include_history``, ``include_allocation_history``, ``include_broker_pnl_history`` and
``include_pnl_candles`` are on. The 1Y window starts a year before A's first row, inside B's long step.

What each test pins, and how it stands on HEAD 999f1899e (the floor still in the engine):

- ``TestTheHistoryStartsOnTheFirstRow`` — RED on HEAD: the report's ``range.start`` is 1900-01-01, not 0001-01-03, and so are
  the first date of ``history``, ``allocation_history``, ``broker_pnl_history``, ``pnl_candles`` and ``mwrr_line``. GREEN
  on HEAD (guards): the end of the report, the contiguity of the history, the first step's numbers (B's 1000 EUR, replayed
  since the first row), and the first step holding until the day before A's deposit.
- ``TestTheCostFollowsTheSteps`` — GREEN on HEAD, because the floor is what keeps the frame at 125 years there: these are
  the gate that must stay green once the floor is gone and the frame is 2024 years (~740 000 days): fewer than 500 history
  steps, at most 30 ``StateSegment.state_on`` calls in ``get_report`` (10 / 15 measured on HEAD: the summary's single-day
  reads), under 50 MB at peak (``tracemalloc``), ``mwrr_line`` no longer
  than twice the steps plus 24 for each step longer than 62 days. Not red on HEAD by construction; red after L1 the day a
  reader walks the days.
- ``TestMwrrOverTwoThousandYears`` — GREEN on HEAD (125 years there), the gate for 2024 years: no exception; every
  ``mwrr_line`` point, the summary's ``mwrr_annualized_percent`` / ``mwrr_cumulative_percent`` / ``twrr_percent`` and every
  history ``twrr`` / ``roi`` is None or a finite Decimal (``(1 + r) ** (days / 365)`` on 739 000 days may overflow a Decimal);
  the last line point's cumulative is the annualized MWRR carried over the days since the first snapshot, ``range.start``.
- ``TestAOneYearWindowIsUnaffected`` — GREEN on HEAD and after: ``range.start`` is the window's first day, and the
  window's history equals, day by day, the «all» history clipped with ``series_steps.points_between`` — every value but
  ``twrr`` and ``roi``, which are relative to the period.

Isolation: PURE with respect to the lane — the database is a private SQLite file under a pytest temporary directory (the app
schema, ``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no server, no network. The
report, WAC and engine blob caches are emptied around each run, and ``StateSegment.state_on`` is wrapped only inside the
module's fixture, undone at its end. No sleep, no wall clock, no translated text, no fixed position (points are found by date).

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate step 5), backend/app/services/portfolio_service.py
(get_report), backend/app/services/financial_math/series_steps.py.
"""

from __future__ import annotations

import asyncio
import tracemalloc
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery, PortfolioReportResponse
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.portfolio.models import StateSegment
from backend.app.services.financial_math.returns import annualized_to_cumulative
from backend.app.services.financial_math.series_steps import points_between, value_at
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
END = date(2025, 6, 30)
YEAR_START = date(2024, 6, 30)
FIRST_ROW = date(1, 1, 3)  # B's deposit: the first row of the book (a typo of the year)
A_DEPOSIT = date(2025, 1, 2)
BUY_X_DAY = date(2025, 1, 3)
BUY_Y_DAY = date(2025, 1, 6)
SELL_X_DAY = date(2025, 3, 17)
QUOTES_END = date(2025, 4, 30)
LONG_STEP_DAYS = 62  # a step longer than this gets monthly MWRR points
MAX_MONTHLY_POINTS = 24

STEPS_BUDGET = 500
PEAK_BUDGET_BYTES = 50 * 1024 * 1024
#: ``state_on`` calls tolerated in ``get_report``: a small constant, never proportional to the days or the steps. The summary
#: reads single days — the end state, the day change (two days), the period boundaries, the current allocations — and
#: the data-quality and allocation-id readers walk ``iter_segments`` (one call per segment is NOT ``state_on``). Measured
#: on HEAD 999f1899e: 10 for «all», 15 for the 1Y window (87 history steps each); a reader walking the days would make
#: 740 000, one walking the steps ~90 more per walk.
STATE_ON_BUDGET = 30

PERIOD_RELATIVE = ("twrr", "roi")


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _weekdays(first: date, last: date) -> list[date]:
    return [day for day in _days(first, last) if day.weekday() < 5]


X_QUOTES = _weekdays(A_DEPOSIT, QUOTES_END)
Y_QUOTES = _weekdays(BUY_Y_DAY, QUOTES_END)


def _cycle(day: date, base: str, step: str, length: int) -> Decimal:
    return Decimal(base) + Decimal(step) * (day.toordinal() % length)


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# THE BOOK
# =============================================================================


def _tx(broker: Broker, tx_type: TransactionType, day: date, *, amount: str, asset: Asset | None = None, quantity: str = "0") -> Transaction:
    return Transaction(broker_id=broker.id, asset_id=asset.id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=EUR)


def _price(asset: Asset, day: date, close: Decimal, currency: str) -> PriceHistory:
    return PriceHistory(asset_id=asset.id, date=day, open=close - Decimal("0.5"), high=close + Decimal("1"), low=close - Decimal("1"), close=close, volume=Decimal("1"), currency=currency, source_plugin_key="pav_l1")


async def _seed(session: AsyncSession) -> tuple[int, dict[str, int]]:
    """The book above, rows inserted directly (the write floor refuses year 1 through the API). Returns (U's id, brokers' ids)."""
    tag = uuid4().hex[:12]
    user = User(username=f"pavl1_{tag}", email=f"pavl1_{tag}@test.com", hashed_password="fakehash", is_active=True)
    a, b = Broker(name=f"PAV-L1 A {tag}"), Broker(name=f"PAV-L1 B {tag}")
    x = Asset(display_name=f"PAV-L1 X {tag}", currency=EUR, asset_type=AssetType.ETF)
    y = Asset(display_name=f"PAV-L1 Y {tag}", currency="USD", asset_type=AssetType.STOCK)
    session.add_all([user, a, b, x, y])
    await session.flush()
    session.add_all(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in (a, b))
    session.add_all(_price(x, day, _cycle(day, "100", "0.25", 13), EUR) for day in X_QUOTES)
    session.add_all(_price(y, day, _cycle(day, "50", "0.5", 11), "USD") for day in Y_QUOTES)
    session.add_all(FxRate(date=day, base=EUR, quote="USD", rate=_cycle(day, "1.08", "0.001", 7), source="PAV_L1") for day in Y_QUOTES)
    session.add_all(
        [
            _tx(b, TransactionType.DEPOSIT, FIRST_ROW, amount="1000"),
            _tx(a, TransactionType.DEPOSIT, A_DEPOSIT, amount="10000"),
            _tx(a, TransactionType.BUY, BUY_X_DAY, amount="-5000", asset=x, quantity="50"),
            _tx(a, TransactionType.BUY, BUY_Y_DAY, amount="-900", asset=y, quantity="10"),
            _tx(a, TransactionType.SELL, SELL_X_DAY, amount="1100", asset=x, quantity="-10"),
        ]
    )
    await session.commit()
    return user.id, {"A": a.id, "B": b.id}


def _query(start: date | None) -> PortfolioReportQuery:
    return PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=start, end=END),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
        include_broker_pnl_history=True,
        include_pnl_candles=True,
    )


# =============================================================================
# THE RUNS: «all» AND 1Y, ONCE PER MODULE
# =============================================================================


@dataclass
class _Run:
    report: PortfolioReportResponse
    state_on_calls: int
    peak_bytes: int


@dataclass
class _Runs:
    broker_ids: dict[str, int]
    runs: dict[str, _Run]


async def _get_report(engine, user_id: int, start: date | None, counter: list[int]) -> _Run:
    """One ``get_report`` on a fresh session and empty caches, with ``state_on`` calls counted and the peak measured."""
    _clear_portfolio_caches()
    counter.clear()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            report = await PortfolioService(session).get_report(user_id, _query(start))
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    _clear_portfolio_caches()
    return _Run(report=report, state_on_calls=len(counter), peak_bytes=peak)


async def _run_all(directory: Path, counter: list[int]) -> _Runs:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'pav_l1.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id, broker_ids = await _seed(session)
        # A warm-up first: the first report of a process allocates once-only structures (imports, caches) that are not its cost.
        await _get_report(engine, user_id, YEAR_START, counter)
        runs = {"all": await _get_report(engine, user_id, None, counter), "year": await _get_report(engine, user_id, YEAR_START, counter)}
        return _Runs(broker_ids=broker_ids, runs=runs)
    finally:
        await engine.dispose()
        _clear_portfolio_caches()


@pytest.fixture(scope="module")
def runs(tmp_path_factory) -> _Runs:
    """The book's two reports (a private database), ``StateSegment.state_on`` counted while they run."""
    counter: list[int] = []
    real_state_on = StateSegment.state_on

    def counting_state_on(self, day):
        counter.append(1)
        return real_state_on(self, day)

    patch = pytest.MonkeyPatch()
    patch.setattr(StateSegment, "state_on", counting_state_on)
    try:
        return asyncio.run(_run_all(tmp_path_factory.mktemp("pav_l1"), counter))
    finally:
        patch.undo()


@pytest.fixture
def whole(runs) -> _Run:
    return runs.runs["all"]


@pytest.fixture
def year(runs) -> _Run:
    return runs.runs["year"]


def _finite(value) -> bool:
    return value is None or (isinstance(value, Decimal) and value.is_finite())


# =============================================================================
# a. THE HISTORY STARTS ON THE FIRST ROW
# =============================================================================


class TestTheHistoryStartsOnTheFirstRow:
    def test_the_range_starts_on_the_first_row(self, whole):
        """RED on HEAD 999f1899e: ``range.start`` is 1900-01-01 (the engine floor), the contract is the first row, 0001-01-03,
        even though no API can write it."""
        report = whole.report
        assert report.range is not None, "include_history=True gives the report a range"
        assert report.range.start == FIRST_ROW, f"range.start is {report.range.start}: the report starts on the first row, whatever its year"
        assert report.range.end == END, "the range ends on the window's end"

    def test_the_history_starts_on_the_first_row(self, whole):
        """RED on HEAD: ``history[0].date`` is 1900-01-01, not 0001-01-03."""
        history = whole.report.history
        assert history, "the history has steps"
        assert history[0].date == FIRST_ROW, f"history[0].date is {history[0].date}: the history starts on the first row"

    def test_every_series_starts_on_the_first_row(self, whole, runs):
        """RED on HEAD: the allocation by type and by asset, the broker P&L of B, the P&L candles and the MWRR line all
        start on 1900-01-01. Each series is looked at from the first step of B's deposit (a candle needs a complete NAV: B's
        cash is)."""
        report = whole.report
        broker_b = next(history for history in report.broker_pnl_history or [] if history.broker_id == runs.broker_ids["B"])
        firsts = {
            "allocation_history.type": (report.allocation_history.type or [None])[0],
            "allocation_history.asset": (report.allocation_history.asset or [None])[0],
            "broker_pnl_history[B]": (broker_b.points or [None])[0],
            "pnl_candles": ((report.pnl_candles.points if report.pnl_candles else None) or [None])[0],
            "mwrr_line": (report.mwrr_line or [None])[0],
        }
        assert {name: point.date if point else None for name, point in firsts.items()} == dict.fromkeys(firsts, FIRST_ROW), "every series starts on the first row, as the history does"

    def test_guard_the_history_is_contiguous_to_the_end(self, whole):
        """GUARD (green on HEAD too): from the first step to the end, every step starts the day after the previous one's
        ``through``, and the last holds to the report's end."""
        history = whole.report.history
        assert [(previous.through + timedelta(days=1), step.date) for previous, step in zip(history, history[1:], strict=False) if previous.through + timedelta(days=1) != step.date] == [], "no gap or overlap between steps"
        assert history[-1].through == END, "the last step holds to the report's end"

    def test_guard_the_year_one_deposit_is_replayed_to_the_day_before_a(self, whole):
        """GUARD (green on HEAD too): B's deposit is replayed since the first row — the first step (day one of the history:
        its ``twrr`` is pinned to 0, so it is a step of its own) and the step holding the day before A's deposit both read
        cash 1000 EUR, capital 1000 EUR, nothing else. On HEAD the same numbers start on 1900-01-01."""
        history = whole.report.history
        eve = value_at(history, A_DEPOSIT - timedelta(days=1))
        assert eve is not None, "the history holds the day before A's deposit"
        for name, step in (("first step", history[0]), (f"step of {A_DEPOSIT - timedelta(days=1)}", eve)):
            assert (step.cash_value.amount, step.market_value.amount, step.nav_value.amount, step.capital_baseline.amount, step.total_pnl.amount) == (
                Decimal("1000"),
                Decimal("0"),
                Decimal("1000"),
                Decimal("1000"),
                Decimal("0"),
            ), f"{name}: B's deposit of year 1 is replayed — cash 1000 EUR, capital 1000 EUR, nothing else"


# =============================================================================
# b. THE COST FOLLOWS THE STEPS
# =============================================================================


class TestTheCostFollowsTheSteps:
    @pytest.mark.parametrize("window", ["all", "year"])
    def test_the_history_has_a_few_steps_not_a_step_a_day(self, runs, window):
        """GREEN on HEAD (guard of L1): the history is ~the engine's segments — fewer than 500 — over 2024 years, not one
        point per day (HEAD: 125 years, same count)."""
        history = runs.runs[window].report.history
        assert 0 < len(history) < STEPS_BUDGET, f"{window}: {len(history)} history steps; the cost follows the segments, not the days"

    @pytest.mark.parametrize("window", ["all", "year"])
    def test_no_quiet_day_is_materialised(self, runs, window):
        """GREEN on HEAD (guard of L1): ``get_report`` reads steps, never one ``StateSegment.state_on`` per day: a few
        single-day reads of the summary (see ``STATE_ON_BUDGET``), not a number that follows the days."""
        calls = runs.runs[window].state_on_calls
        assert calls <= STATE_ON_BUDGET, f"{window}: get_report called state_on {calls} times (budget {STATE_ON_BUDGET}): a reader is walking the days"

    @pytest.mark.parametrize("window", ["all", "year"])
    def test_the_peak_memory_stays_small(self, runs, window):
        """GREEN on HEAD (guard of L1): the report of a 2024-year book peaks under 50 MB (``tracemalloc``): a state or a
        point per day would be 740 000 objects, ~GB."""
        peak = runs.runs[window].peak_bytes
        assert peak < PEAK_BUDGET_BYTES, f"{window}: get_report peaked at {peak / 1024 / 1024:.1f} MB, over {PEAK_BUDGET_BYTES // 1024 // 1024} MB"

    @pytest.mark.parametrize("window", ["all", "year"])
    def test_the_mwrr_line_is_bounded_by_the_steps(self, runs, window):
        """GREEN on HEAD (guard of L1): ``len(mwrr_line) <= 2 * steps + 24 * (steps longer than 62 days)`` — a point at the
        start and the end of each step and at most 24 month ends inside each long one."""
        report = runs.runs[window].report
        long_steps = sum(1 for step in report.history if (step.through - step.date).days + 1 > LONG_STEP_DAYS)
        bound = 2 * len(report.history) + MAX_MONTHLY_POINTS * long_steps
        assert report.mwrr_line is not None and len(report.mwrr_line) <= bound, f"{window}: {len(report.mwrr_line or [])} MWRR points for {len(report.history)} steps ({long_steps} long): at most {bound}"


# =============================================================================
# c. THE MWRR OVER TWO THOUSAND YEARS
# =============================================================================


class TestMwrrOverTwoThousandYears:
    def test_every_mwrr_line_point_is_none_or_finite(self, whole):
        """GREEN on HEAD (125 years there), the gate for 2024 years: no point of the line is NaN or infinite — a rate raised to
        739 000 / 365 may overflow a Decimal; the report did not raise to get here."""
        bad = [(point.date, point.annualized, point.cumulative) for point in whole.report.mwrr_line or [] if not (_finite(point.annualized) and _finite(point.cumulative))]
        assert whole.report.mwrr_line, "precondition: the report has an MWRR line"
        assert bad == [], f"MWRR line points neither None nor finite: {bad[:3]}"

    def test_the_summary_returns_are_none_or_finite(self, whole):
        """GREEN on HEAD, the gate for 2024 years: the summary's MWRR (annualized, cumulative) and TWRR are None or finite."""
        summary = whole.report.summary
        assert summary is not None, "include_summary=True gives the report a summary"
        values = {name: getattr(summary, name) for name in ("mwrr_annualized_percent", "mwrr_cumulative_percent", "twrr_percent")}
        assert {name: value for name, value in values.items() if not _finite(value)} == {}, f"summary returns neither None nor finite: {values}"

    @pytest.mark.parametrize("window", ["all", "year"])
    def test_every_history_twrr_and_roi_is_none_or_finite(self, runs, window):
        """GREEN on HEAD, the gate for 2024 years: every history step's ``twrr`` and ``roi`` is None or finite."""
        history = runs.runs[window].report.history
        bad = [(step.date, step.twrr, step.roi) for step in history if not (_finite(step.twrr) and _finite(step.roi))]
        assert bad == [], f"{window}: history steps with a twrr or roi neither None nor finite: {bad[:3]}"

    def test_the_cumulative_is_the_annualized_over_the_days_since_the_first_snapshot(self, whole):
        """GREEN on HEAD (days since 1900 there), the gate for year 1: where the last line point has both, its cumulative is
        ``annualized_to_cumulative(annualized, days since range.start)`` — the days since the first snapshot, 739 000 of
        them from 0001-01-03, not since a floor."""
        report = whole.report
        point = next((point for point in reversed(report.mwrr_line or []) if point.annualized is not None and point.cumulative is not None), None)
        if point is None:
            pytest.skip("no MWRR line point holds both values on this book")
        expected = annualized_to_cumulative(point.annualized, (point.date - report.range.start).days)
        assert expected is not None and abs(point.cumulative - expected) <= Decimal("1e-9") * max(Decimal(1), abs(expected)), f"cumulative {point.cumulative} on {point.date}, {expected} expected over {(point.date - report.range.start).days} days"


# =============================================================================
# d. A 1Y WINDOW IS UNAFFECTED
# =============================================================================


def _values(point) -> dict:
    """A point's values, every field but its days and the period-relative returns."""
    return {key: item for key, item in point.model_dump().items() if key not in ("date", "through", *PERIOD_RELATIVE)}


class TestAOneYearWindowIsUnaffected:
    def test_guard_the_range_starts_on_the_window_start(self, year):
        """GUARD (green on HEAD and after): the window opens a year before A's first row, inside B's long step: the range
        starts on the window's first day, ends on its end, and the history starts there."""
        report = year.report
        assert (report.range.start, report.range.end) == (YEAR_START, END), "the 1Y window's range is the window"
        assert report.history[0].date == YEAR_START, "the 1Y history starts on the window's first day"
        assert report.history[-1].through == END

    def test_guard_the_window_history_is_the_whole_history_clipped(self, whole, year):
        """GUARD (green on HEAD and after): on every first and last day of a step of either series, the 1Y window's history
        has the values of the «all» history clipped to the window (``points_between``) — every field but ``twrr`` and ``roi``
        (period-relative: the window starts its own return)."""
        clipped = points_between(whole.report.history, YEAR_START, END)
        assert clipped and (clipped[0].date, clipped[-1].through) == (YEAR_START, END), "precondition: the clipped history covers the window"
        days = sorted({day for step in (*clipped, *year.report.history) for day in (step.date, step.through)})

        differing = []
        for day in days:
            window_step, whole_step = value_at(year.report.history, day), value_at(clipped, day)
            if window_step is None or whole_step is None or _values(window_step) != _values(whole_step):
                differing.append(day)
        assert differing == [], f"the 1Y history differs from the clipped whole history on {differing[:5]} (of {len(days)} days checked)"

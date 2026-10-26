"""MF-P4b (D-P4 cure B, contract §1.1–§2 and §8.1–§8.3) — ``PortfolioService.get_report`` gives its series in steps.

Today ``history``, ``allocation_history``, ``broker_pnl_history`` and ``pnl_candles`` carry one point per calendar day.
The contract: one point per stretch without novelty, holding from ``date`` to ``through`` (both included); the response
carries ``range {start, end}`` and the history's MWRR moves to ``mwrr_line`` (true values at each step's ``date`` and
``through``, plus the last day of each calendar month strictly inside a step longer than 62 days, at most 24 a step).

What is tested, on one private book (below) and two windows — ``start=None`` (the whole history; the end is explicit, so
no wall clock) and a window opening on 2024-10-10, in the middle of an engine segment:

1. ``TestSchemas`` (pure) — the point models extend ``StepSpan`` / carry ``through``; the history point has no
   ``mwrr_*`` and every other field of today; ``MwrrLinePoint``; ``PortfolioReportResponse.range`` / ``.mwrr_line``.
2. ``TestRange`` — ``range.start`` = the first day of the window with a state, ``range.end`` = the window's end.
3. ``TestStructure`` — every series: in order, no overlap, inside ``range``, ``through >= date``; the history covers
   ``range`` without a gap (first ``date == range.start``, last ``through == range.end``, contiguous).
4. ``TestMaximalSteps`` — two adjacent points of a series (per broker for broker P&L) never carry identical values
   (Decimals compared with ``as_tuple``, every field but ``date``/``through``).
5. ``TestExpansionParity`` — repeating each point over its days gives, field by field (``as_tuple``), today's daily value.
   The oracle of a day is the engine's state of that day (``PortfolioCalculationEngine.calculate`` with the service's
   arguments, ``daily_states.state_on``), mapped as HEAD 1164a1e65's ``DerivedViewsBuilder.build_history`` /
   ``build_allocation_history`` / ``build_asset_allocation_history`` / ``build_broker_pnl_history`` /
   ``build_pnl_candles`` map it (frozen copies below, so the oracle does not move with the cure); ``twrr`` / ``roi``
   from ``build_performance_inputs`` on the dense daily list → ``rebase_to_period`` → ``calculate_twrr_series`` /
   ``calculate_simple_roi_series``, the first day's ``twrr`` pinned to 0, as ``get_history`` does today. A day without a
   candle is a gap in the candle series.
6. ``TestMwrrLine`` — the dates are exactly the steps' ``date`` and ``through`` plus the month ends inside the long
   steps (a step of more than 24 month ends: at most 24 of them, all month ends strictly inside); each point's
   ``annualized`` is today's daily MWRR line on that day (``period_mwrr_series`` on the daily rebased inputs, first day
   pinned to 0) and ``cumulative`` = ``annualized_to_cumulative(annualized, days since the period's first snapshot)``.
7. ``TestEventSeriesUnchanged`` — income, cost, deposit and acquisition funding: the points the service's own methods
   give (one per event, no ``through``).

RED on HEAD 1164a1e65: every test that reads ``through``, ``range`` or ``mwrr_line`` (``StepSpan`` is not a base of any
point model; one point per day); the schema tests. GREEN on HEAD: the event series, the presence barriers.

The book (report EUR, user U owns brokers A and B at share 1):
- B deposits 1000 EUR on Monday 2022-01-03 and nothing happens until 2024-06-03: a step of ~29 months (> 24 month ends).
- A deposits 10 000 on 2024-06-03, buys 50 X (EUR ETF) for 5000 and pays a fee of 5 on 06-04; B buys 10 Y (USD stock)
  for 900 EUR on 06-12; A receives 5 Z by an ADJUSTMENT with no cost and no price on 07-01 (Z is MISSING until its only
  quote on 07-08: those days have no candle and an incomplete NAV); a dividend of 25 on X on 09-02; A sells 10 X for 1050
  on 08-20.
- X is quoted every weekday 2024-06-03..2024-09-27 and 2025-01-06..2025-01-31, Y and EUR/USD every weekday
  2024-06-10..2024-09-27 and 2025-01-06..2025-01-31; nothing on the holiday 2024-08-15. From 2024-09-28 to 2025-01-05
  nothing happens: a quiet step of ~3 months (three month ends inside) after the stale turns of 10-05.
- The window ends on Friday 2025-01-31.

Isolation: PURE with respect to the lane — the database is a private SQLite file under a pytest temporary directory
(the app schema, ``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no server, no
network. The report, WAC and engine blob caches are emptied around each scenario. No sleep, no wall clock, no
translated text, no fixed position (points are found by date, brokers by id).

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).

Reference: backend/app/services/portfolio_service.py (get_report, get_history), backend/app/schemas/portfolio.py,
backend/app/schemas/common.py (StepSpan, DateSpan), backend/app/services/financial_math/series_steps.py,
backend/app/services/financial_math/portfolio/derived_views.py, backend/app/services/financial_math/returns.py.
"""

from __future__ import annotations

import asyncio
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.schemas.portfolio as portfolio_schemas
import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import Currency, OpenDateRangeModel
from backend.app.schemas.portfolio import AllocationItem, PortfolioReportQuery, PortfolioReportResponse
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.returns import annualized_to_cumulative, calculate_simple_roi_series, calculate_twrr_series, period_mwrr_series, rebase_to_period
from backend.app.services.financial_math.weights import slice_percents
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
END = date(2025, 1, 31)
WINDOW_START = date(2024, 10, 10)
LONG_STEP_DAYS = 62  # a step longer than this gets monthly MWRR points
MAX_MONTHLY_POINTS = 24

FIRST_DEPOSIT = date(2022, 1, 3)
A_DEPOSIT = date(2024, 6, 3)
BUY_X_DAY = date(2024, 6, 4)
BUY_Y_DAY = date(2024, 6, 12)
Z_IN_DAY = date(2024, 7, 1)
Z_QUOTE_DAY = date(2024, 7, 8)
SELL_X_DAY = date(2024, 8, 20)
DIVIDEND_DAY = date(2024, 9, 2)
HOLIDAY = date(2024, 8, 15)
QUOTES_PAUSE = date(2024, 9, 27)
QUOTES_RESUME = date(2025, 1, 6)

#: HEAD 1164a1e65's PortfolioHistoryPoint fields, without the two MWRR ones the contract removes.
HISTORY_FIELDS_TODAY_BUT_MWRR = {
    "date",
    "cash_value",
    "market_value",
    "broker_nav_value",
    "in_transit_cash_value",
    "in_transit_asset_market_value",
    "in_transit_market_value",
    "nav_value",
    "open_cost_basis",
    "in_transit_asset_cost_basis",
    "in_transit_book_value",
    "book_value",
    "capital_baseline",
    "book_asset_like",
    "cash_from_contributed_capital",
    "cash_from_generated_returns",
    "total_pnl",
    "unrealized_gain_loss",
    "twrr",
    "roi",
}
SPAN_FIELDS = ("date", "through")


# =============================================================================
# CALENDAR HELPERS
# =============================================================================


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _weekdays(first: date, last: date) -> list[date]:
    return [day for day in _days(first, last) if day.weekday() < 5 and day != HOLIDAY]


def _month_ends_strictly_inside(first: date, last: date) -> list[date]:
    ends = []
    year, month = first.year, first.month
    while True:
        end = date(year, month, calendar.monthrange(year, month)[1])
        if end >= last:
            return ends
        if end > first:
            ends.append(end)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def _step_days(point) -> int:
    return (point.through - point.date).days + 1


X_QUOTES = _weekdays(A_DEPOSIT, QUOTES_PAUSE) + _weekdays(QUOTES_RESUME, END)
Y_QUOTES = _weekdays(date(2024, 6, 10), QUOTES_PAUSE) + _weekdays(QUOTES_RESUME, END)


def _cycle(day: date, base: str, step: str, length: int) -> Decimal:
    return Decimal(base) + Decimal(step) * (day.toordinal() % length)


# =============================================================================
# THE BOOK AND THE SCENARIOS
# =============================================================================


@dataclass
class _Scenario:
    start: date | None
    report: PortfolioReportResponse
    states: dict[date, Any]  # every day of the engine's frame -> its state (the oracle)
    first_state_day: date
    segment_starts: list[date]
    dense: list[Any]
    names: dict[int, str]
    broker_ids: dict[str, int]
    standalone: dict[str, Any] = field(default_factory=dict)


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


def _tx(broker: Broker, tx_type: TransactionType, day: date, *, amount: str = "0", currency: str | None = EUR, asset: Asset | None = None, quantity: str = "0") -> Transaction:
    return Transaction(broker_id=broker.id, asset_id=asset.id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency)


def _price(asset: Asset, day: date, close: Decimal, currency: str) -> PriceHistory:
    return PriceHistory(asset_id=asset.id, date=day, open=close - Decimal("0.5"), high=close + Decimal("1"), low=close - Decimal("1"), close=close, volume=Decimal("1"), currency=currency, source_plugin_key="p4b_steps")


async def _seed(session: AsyncSession) -> tuple[int, dict[str, int], dict[int, str]]:
    tag = uuid4().hex[:12]
    user = User(username=f"p4b_{tag}", email=f"p4b_{tag}@test.com", hashed_password="fakehash", is_active=True)
    a, b = Broker(name=f"P4b A {tag}"), Broker(name=f"P4b B {tag}")
    x = Asset(display_name=f"P4b X {tag}", currency=EUR, asset_type=AssetType.ETF)
    y = Asset(display_name=f"P4b Y {tag}", currency="USD", asset_type=AssetType.STOCK)
    z = Asset(display_name=f"P4b Z {tag}", currency=EUR, asset_type=AssetType.STOCK)
    session.add_all([user, a, b, x, y, z])
    await session.flush()
    session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in (a, b)])
    session.add_all(_price(x, day, _cycle(day, "100", "0.25", 13), EUR) for day in X_QUOTES)
    session.add_all(_price(y, day, _cycle(day, "50", "0.5", 11), "USD") for day in Y_QUOTES)
    session.add(_price(z, Z_QUOTE_DAY, Decimal("20"), EUR))
    session.add_all(FxRate(date=day, base=EUR, quote="USD", rate=_cycle(day, "1.08", "0.001", 7), source="P4B_STEPS") for day in Y_QUOTES)
    session.add_all(
        [
            _tx(b, TransactionType.DEPOSIT, FIRST_DEPOSIT, amount="1000"),
            _tx(a, TransactionType.DEPOSIT, A_DEPOSIT, amount="10000"),
            _tx(a, TransactionType.BUY, BUY_X_DAY, amount="-5000", asset=x, quantity="50"),
            _tx(a, TransactionType.FEE, BUY_X_DAY, amount="-5"),
            _tx(b, TransactionType.BUY, BUY_Y_DAY, amount="-900", asset=y, quantity="10"),
            _tx(a, TransactionType.ADJUSTMENT, Z_IN_DAY, currency=None, asset=z, quantity="5"),
            _tx(a, TransactionType.SELL, SELL_X_DAY, amount="1050", asset=x, quantity="-10"),
            _tx(a, TransactionType.DIVIDEND, DIVIDEND_DAY, amount="25", asset=x),
        ]
    )
    await session.commit()
    return user.id, {"A": a.id, "B": b.id}, {x.id: x.display_name, y.id: y.display_name, z.id: z.display_name}


def _query(start: date | None) -> PortfolioReportQuery:
    return PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=start, end=END),
        target_currency=EUR,
        include_summary=False,
        include_history=True,
        include_allocation_history=True,
        include_broker_pnl_history=True,
        include_pnl_candles=True,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
    )


async def _run(directory: Path, start: date | None) -> _Scenario:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'p4b_steps.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id, broker_ids, names = await _seed(session)
        _clear_portfolio_caches()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            report = await PortfolioService(session).get_report(user_id, _query(start))
        _clear_portfolio_caches()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # The service's own engine call (get_report, step 1): from t=0, to the window's end, candles and funding on
            result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, broker_ids=None, date_from=None, date_to=END, target_currency=EUR, include_candles=True, include_acquisition_funding=True, period_start=None)
            service = PortfolioService(session)
            standalone = {
                "income_history": await service.get_income_history(user_id, date_from=start, date_to=END, target_currency_override=EUR, _precomputed_native_cash=result.native_cash),
                "cost_history": await service.get_cost_history(user_id, date_from=start, date_to=END, target_currency_override=EUR, _precomputed_native_cash=result.native_cash),
                "deposit_history": await service.get_deposit_history(user_id, date_from=start, date_to=END, target_currency_override=EUR, _precomputed_native_cash=result.native_cash),
                "acquisition_funding": await service.get_acquisition_funding_history(user_id, date_from=start, date_to=END, target_currency_override=EUR, _precomputed_engine_result=result),
            }
        ds = result.daily_states
        dense = list(ds)
        return _Scenario(
            start=start,
            report=report,
            states={state.date: state for state in dense},
            first_state_day=ds.first_date,
            segment_starts=[segment.start for segment in ds.segments],
            dense=dense,
            names=names,
            broker_ids=broker_ids,
            standalone=standalone,
        )
    finally:
        await engine.dispose()
        _clear_portfolio_caches()


@pytest.fixture(scope="module", params=[pytest.param(None, id="whole-history"), pytest.param(WINDOW_START, id="window-mid-segment")])
def scenario(request, tmp_path_factory) -> _Scenario:
    """The book, its report and its engine oracle, once per window (a private database each)."""
    return asyncio.run(_run(tmp_path_factory.mktemp("p4b_steps"), request.param))


# =============================================================================
# ORACLE — frozen copies of HEAD 1164a1e65's daily mappings
# =============================================================================


def _norm(value):
    """A comparable form: Decimals by ``as_tuple`` (exponent included), models by their dump, containers recursively."""
    if isinstance(value, Decimal):
        return ("D", value.as_tuple())
    if isinstance(value, BaseModel):
        return _norm(value.model_dump())
    if isinstance(value, dict):
        return {key: _norm(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_norm(item) for item in value]
    return value


def _point_values(point) -> dict:
    """A point's values, every field but date/through."""
    return {key: _norm(item) for key, item in point.model_dump().items() if key not in SPAN_FIELDS}


def _money(amount: Decimal) -> Currency:
    return Currency(code=EUR, amount=amount)


def _history_row(s) -> dict:
    """``DerivedViewsBuilder.build_history``'s mapping of one state (HEAD), without the date."""
    return {
        "cash_value": _money(s.cash_value),
        "market_value": _money(s.market_value),
        "broker_nav_value": _money(s.broker_nav_value),
        "in_transit_cash_value": _money(s.in_transit_cash_value) if s.in_transit_cash_value else None,
        "in_transit_asset_market_value": _money(s.in_transit_asset_market_value) if s.in_transit_asset_market_value else None,
        "in_transit_market_value": _money(s.in_transit_market_value) if s.in_transit_market_value else None,
        "nav_value": _money(s.nav_value),
        "open_cost_basis": _money(s.open_cost_basis) if s.open_cost_basis else None,
        "in_transit_asset_cost_basis": _money(s.in_transit_asset_cost_basis) if s.in_transit_asset_cost_basis else None,
        "in_transit_book_value": _money(s.in_transit_book_value) if s.in_transit_book_value else None,
        "book_value": _money(s.book_value) if s.book_value else None,
        "capital_baseline": _money(s.cumulative_external_cash_flow),
        "book_asset_like": _money(s.book_asset_like),
        "cash_from_contributed_capital": _money(s.cash_from_contributed_capital),
        "cash_from_generated_returns": _money(s.cash_from_generated_returns),
        "total_pnl": _money(s.total_pnl),
        "unrealized_gain_loss": _money(s.unrealized_gain_loss) if s.unrealized_gain_loss else None,
    }


def _allocation_components(s, dimension: str, names: dict[int, str]) -> list:
    """``build_allocation_history`` (type/sector/geography) and ``build_asset_allocation_history`` (asset) of one state."""
    if dimension == "asset":
        slices: dict[int | None, Decimal] = dict(s.by_asset)
        slices[None] = s.cash_value + s.in_transit_cash_value
        percents = slice_percents(slices)
        return [AllocationItem(name="Liquidity" if asset_id is None else names.get(asset_id, f"Asset {asset_id}"), id=asset_id, value=percents[asset_id].quantize(Decimal("0.01")), amount=amount) for asset_id, amount in sorted(slices.items(), key=lambda item: -item[1])]
    d = getattr(s, {"type": "by_type", "sector": "by_sector", "geography": "by_geography"}[dimension], {})
    percents = slice_percents(d)
    return [AllocationItem(name=name, value=percents[name].quantize(Decimal("0.01")), amount=amount) for name, amount in sorted(d.items(), key=lambda item: -item[1])]


def _window_days(sc: _Scenario) -> list[date]:
    """Every day of the report's window that has a state: the oracle's calendar."""
    first = sc.first_state_day if sc.start is None else max(sc.start, sc.first_state_day)
    return _days(first, END)


def _daily_performance(sc: _Scenario) -> dict[date, dict[str, Decimal | None]]:
    """Today's per-day twrr / roi / MWRR (annualized, cumulative), as ``get_history`` builds them, first day pinned."""
    snapshots, flows = DerivedViewsBuilder(sc.dense, EUR).build_performance_inputs(sc.start)
    period = rebase_to_period(snapshots, flows, sc.start)
    period_snapshots, period_flows = list(period.nav_snapshots), list(period.cash_flows)
    twrr: dict[date, Decimal] = {}
    roi: dict[date, Decimal] = {}
    mwrr: dict[date, Decimal | None] = {}
    if period_snapshots and period_flows:
        twrr = {pt.date: pt.twrr for pt in calculate_twrr_series(period_snapshots, period_flows)}
        roi = {pt.date: pt.roi for pt in calculate_simple_roi_series(period_snapshots, period_flows)}
        mwrr = {pt.date: pt.mwrr for pt in period_mwrr_series(period_snapshots, period_flows)}
    period_start = period_snapshots[0].date if period_snapshots else None
    days = _window_days(sc)
    out: dict[date, dict[str, Decimal | None]] = {}
    for day in days:
        annualized = mwrr.get(day)
        out[day] = {
            "twrr": twrr.get(day),
            "roi": roi.get(day),
            "annualized": annualized,
            "cumulative": annualized_to_cumulative(annualized, (day - period_start).days if period_start else 0),
        }
    out[days[0]].update(twrr=Decimal("0"), annualized=Decimal("0"), cumulative=Decimal("0"))
    return out


def _expected_history(sc: _Scenario) -> dict[date, dict]:
    performance = _daily_performance(sc)
    return {day: _norm({**_history_row(sc.states[day]), "twrr": performance[day]["twrr"], "roi": performance[day]["roi"]}) for day in _window_days(sc)}


# =============================================================================
# STEP HELPERS
# =============================================================================


def _expand(points) -> dict[date, Any]:
    """Each day covered by a point -> the point (a day covered twice fails)."""
    covered: dict[date, Any] = {}
    for point in points:
        for day in _days(point.date, point.through):
            assert day not in covered, f"{day} is covered by two points"
            covered[day] = point
    return covered


def _assert_structure(points, report_range, label: str) -> None:
    """In order, no overlap, inside range, through >= date."""
    previous = None
    for point in points:
        assert point.through >= point.date, f"{label}: {point.date}..{point.through}"
        assert report_range.start <= point.date and point.through <= report_range.end, f"{label}: {point.date}..{point.through} outside {report_range.start}..{report_range.end}"
        if previous is not None:
            assert point.date > previous.through, f"{label}: {point.date} not after the previous through {previous.through}"
        previous = point


def _assert_maximal(points, label: str) -> None:
    """Two adjacent points (no gap between them) never carry identical values."""
    for previous, point in zip(points, points[1:], strict=False):
        if point.date == previous.through + timedelta(days=1):
            assert _point_values(previous) != _point_values(point), f"{label}: {previous.date}..{previous.through} and {point.date}..{point.through} carry the same values: one step"


def _series(sc: _Scenario) -> list[tuple[str, list]]:
    """Every step series of the report, labelled: history, the four allocation dimensions, each broker's P&L, candles."""
    report = sc.report
    out = [("history", report.history or [])]
    for dimension in ("type", "sector", "geography", "asset"):
        out.append((f"allocation_history.{dimension}", getattr(report.allocation_history, dimension)))
    for entry in report.broker_pnl_history or []:
        out.append((f"broker_pnl_history[{entry.broker_id}]", entry.points))
    out.append(("pnl_candles", report.pnl_candles.points))
    return out


def _history(sc: _Scenario) -> list:
    assert sc.report.history, "the report has no history"
    return sc.report.history


def _range(sc: _Scenario):
    report_range = getattr(sc.report, "range", None)
    assert report_range is not None, "the report has no range"
    return report_range


# =============================================================================
# 1. SCHEMAS
# =============================================================================


def _step_span():
    import backend.app.schemas.common as common  # noqa: PLC0415

    return common.StepSpan


class TestSchemas:
    @pytest.mark.parametrize("name", ["PortfolioHistoryPoint", "AllocationHistoryPoint"])
    def test_point_models_extend_step_span(self, name):
        assert issubclass(getattr(portfolio_schemas, name), _step_span()), f"{name} does not extend StepSpan"

    def test_history_point_has_through_and_no_mwrr(self):
        fields = set(portfolio_schemas.PortfolioHistoryPoint.model_fields)
        assert fields == HISTORY_FIELDS_TODAY_BUT_MWRR | {"through"}, f"extra {sorted(fields - HISTORY_FIELDS_TODAY_BUT_MWRR - {'through'})}, missing {sorted(HISTORY_FIELDS_TODAY_BUT_MWRR | {'through'} - fields)}"

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            pytest.param("AllocationHistoryPoint", {"date", "through", "components"}, id="allocation"),
            pytest.param("BrokerPnlHistoryPoint", {"date", "through", "total_pnl"}, id="broker-pnl"),
            pytest.param("PnlCandlePoint", {"date", "through", "open", "high", "low", "close"}, id="candle"),
            pytest.param("MwrrLinePoint", {"date", "annualized", "cumulative"}, id="mwrr-line"),
        ],
    )
    def test_point_fields(self, name, expected):
        model = getattr(portfolio_schemas, name, None)
        assert model is not None, f"schemas.portfolio has no {name}"
        assert set(model.model_fields) == expected

    def test_mwrr_line_point_is_strict_and_optional(self):
        model = getattr(portfolio_schemas, "MwrrLinePoint", None)
        assert model is not None, "schemas.portfolio has no MwrrLinePoint"
        point = model(date=date(2025, 1, 1), annualized=None, cumulative=None)
        assert (point.annualized, point.cumulative) == (None, None)
        with pytest.raises(ValueError):
            model(date=date(2025, 1, 1), annualized=None, cumulative=None, through=date(2025, 1, 1))

    @pytest.mark.parametrize("name", ["range", "mwrr_line"])
    def test_report_response_fields(self, name):
        info = PortfolioReportResponse.model_fields.get(name)
        assert info is not None, f"PortfolioReportResponse has no {name}"
        assert not info.is_required(), f"{name} must be optional (set only with the history)"


# =============================================================================
# 2. RANGE
# =============================================================================


class TestRange:
    def test_range_is_the_window_with_a_state(self, scenario):
        report_range = _range(scenario)
        expected_start = scenario.first_state_day if scenario.start is None else max(scenario.start, scenario.first_state_day)
        assert (report_range.start, report_range.end) == (expected_start, END)

    def test_presence_barrier_the_window_starts_mid_segment(self, scenario):
        """Precondition (green on HEAD): the window's first day is inside an engine segment, not on its start; the whole
        history starts on the first deposit."""
        if scenario.start is None:
            assert scenario.first_state_day == FIRST_DEPOSIT
        else:
            assert scenario.start not in scenario.segment_starts
            assert any(start < scenario.start for start in scenario.segment_starts)


# =============================================================================
# 3. STRUCTURE
# =============================================================================


class TestStructure:
    def test_every_series_is_ordered_disjoint_and_inside_range(self, scenario):
        report_range = _range(scenario)
        for label, points in _series(scenario):
            assert points, f"{label} is empty"
            _assert_structure(points, report_range, label)

    def test_history_covers_range_without_gaps(self, scenario):
        report_range, history = _range(scenario), _history(scenario)
        assert history[0].date == report_range.start
        assert history[-1].through == report_range.end
        for previous, point in zip(history, history[1:], strict=False):
            assert point.date == previous.through + timedelta(days=1), f"gap or overlap between {previous.through} and {point.date}"

    def test_history_has_far_fewer_points_than_days(self, scenario):
        """One point per step: the quiet stretches (29 months, 3 months, every weekend) are single points."""
        history = _history(scenario)
        days = len(_window_days(scenario))
        assert len(history) < days / 2, f"{len(history)} points for {days} days"
        assert max(_step_days(point) for point in history) > LONG_STEP_DAYS

    def test_presence_barrier_the_candles_have_a_gap(self, scenario):
        """Precondition (green on HEAD): Z is MISSING from 07-01 to 07-07 — those days have no candle — and the other days
        have one (whole history only: the window starts after)."""
        no_candle = [day for day in _window_days(scenario) if scenario.states[day].pnl_candle is None]
        if scenario.start is None:
            assert _days(Z_IN_DAY, Z_QUOTE_DAY - timedelta(days=1)) == [day for day in no_candle if day >= A_DEPOSIT]
        assert any(scenario.states[day].pnl_candle is not None for day in _window_days(scenario))

    def test_two_brokers_in_the_broker_series(self, scenario):
        ids = {entry.broker_id for entry in scenario.report.broker_pnl_history or []}
        assert ids == set(scenario.broker_ids.values())


# =============================================================================
# 4. MAXIMAL STEPS
# =============================================================================


class TestMaximalSteps:
    def test_no_two_adjacent_points_carry_the_same_values(self, scenario):
        for label, points in _series(scenario):
            _assert_maximal(points, label)


# =============================================================================
# 5. EXPANSION PARITY
# =============================================================================


class TestExpansionParity:
    def test_history(self, scenario):
        expected = _expected_history(scenario)
        covered = _expand(_history(scenario))
        assert sorted(covered) == sorted(expected), "the history does not cover the window's days"
        for day, point in covered.items():
            got = _point_values(point)
            assert set(got) == set(expected[day]), f"{day}: fields {sorted(set(got) ^ set(expected[day]))} differ"
            assert got == expected[day], f"{day} (point {point.date}..{point.through}): {[key for key in got if got[key] != expected[day][key]]}"

    @pytest.mark.parametrize("dimension", ["type", "sector", "geography", "asset"])
    def test_allocation_history(self, scenario, dimension):
        points = getattr(scenario.report.allocation_history, dimension)
        covered = _expand(points)
        assert sorted(covered) == _window_days(scenario)
        for day, point in covered.items():
            assert _norm(point.components) == _norm(_allocation_components(scenario.states[day], dimension, scenario.names)), f"{dimension} {day} (point {point.date}..{point.through})"

    def test_broker_pnl_history(self, scenario):
        for entry in scenario.report.broker_pnl_history or []:
            expected = {day: _norm(_money(state.broker_contributions[entry.broker_id].pnl_contribution)) for day in _window_days(scenario) if entry.broker_id in (state := scenario.states[day]).broker_contributions}
            covered = _expand(entry.points)
            assert sorted(covered) == sorted(expected), f"broker {entry.broker_id}"
            for day, point in covered.items():
                assert _norm(point.total_pnl) == expected[day], f"broker {entry.broker_id} {day} (point {point.date}..{point.through})"

    def test_pnl_candles(self, scenario):
        expected = {}
        for day in _window_days(scenario):
            candle = scenario.states[day].pnl_candle
            if candle is not None:
                expected[day] = _norm({"open": _money(candle.open), "high": _money(candle.high), "low": _money(candle.low), "close": _money(candle.close)})
        covered = _expand(scenario.report.pnl_candles.points)
        assert sorted(covered) == sorted(expected), "the candles cover other days than the days with a candle"
        for day, point in covered.items():
            assert _point_values(point) == expected[day], f"candle {day} (point {point.date}..{point.through})"


# =============================================================================
# 6. MWRR LINE
# =============================================================================


def _mwrr_line(sc: _Scenario) -> list:
    line = getattr(sc.report, "mwrr_line", None)
    assert line, "the report has no mwrr_line"
    return line


class TestMwrrLine:
    def test_the_dates(self, scenario):
        history = _history(scenario)
        line_dates = [point.date for point in _mwrr_line(scenario)]
        assert line_dates == sorted(set(line_dates)), "mwrr_line is not sorted and unique"
        assert all(_step_days(point) != LONG_STEP_DAYS + 1 for point in history), "precondition: no step of exactly 63 days (where «longer than 62 days» is ambiguous)"

        expected: set[date] = set()
        crowded = []
        for point in history:
            expected.update({point.date, point.through})
            if _step_days(point) > LONG_STEP_DAYS:
                ends = _month_ends_strictly_inside(point.date, point.through)
                if len(ends) <= MAX_MONTHLY_POINTS:
                    expected.update(ends)
                else:
                    crowded.append((point, set(ends)))
        rest = set(line_dates)
        for point, ends in crowded:
            inside = {day for day in rest if point.date < day < point.through}
            assert 0 < len(inside) <= MAX_MONTHLY_POINTS, f"step {point.date}..{point.through}: {len(inside)} interior points"
            assert inside <= ends, f"step {point.date}..{point.through}: interior points that are no month end: {sorted(inside - ends)}"
            rest -= inside
        assert sorted(rest) == sorted(expected), f"extra {sorted(rest - expected)}, missing {sorted(expected - rest)}"

    def test_presence_barrier_long_segments(self, scenario):
        """Precondition (green on HEAD): the engine has, inside the window, a segment longer than 62 days with at most 24
        month ends (the quiet autumn of 2024) and, on the whole history, one with more (2022-01-03..2024-06-02)."""
        first = _window_days(scenario)[0]
        ends = [start - timedelta(days=1) for start in scenario.segment_starts[1:]] + [END]
        spans = [(max(start, first), end) for start, end in zip(scenario.segment_starts, ends, strict=True) if end >= first]
        counts = [len(_month_ends_strictly_inside(start, end)) for start, end in spans if (end - start).days + 1 > LONG_STEP_DAYS]
        assert any(0 < count <= MAX_MONTHLY_POINTS for count in counts), counts
        if scenario.start is None:
            assert any(count > MAX_MONTHLY_POINTS for count in counts), counts

    def test_the_values(self, scenario):
        performance = _daily_performance(scenario)
        for point in _mwrr_line(scenario):
            assert point.date in performance, f"{point.date} outside the window"
            want = performance[point.date]
            assert (_norm(point.annualized), _norm(point.cumulative)) == (_norm(want["annualized"]), _norm(want["cumulative"])), f"{point.date}: ({point.annualized}, {point.cumulative}) != ({want['annualized']}, {want['cumulative']})"

    def test_presence_barrier_the_line_moves(self, scenario):
        """Precondition (green on HEAD): on the whole history today's daily MWRR changes across the quiet step of autumn
        2024 (time passes over the 2022 deposit), so its monthly points carry information. In the window opening on
        10-10 the NAV is flat until 01-06 (the line is 0 there) and moves with the quotes of January 2025."""
        performance = _daily_performance(scenario)
        first, last = (date(2024, 10, 31), date(2024, 12, 31)) if scenario.start is None else (QUOTES_RESUME, END)
        values = {performance[day]["annualized"] for day in _days(first, last)}
        assert len(values) > 1, values

    def test_json_has_no_mwrr_in_history(self, scenario):
        dumped = scenario.report.model_dump(mode="json")
        assert all("mwrr_annualized" not in row and "mwrr_cumulative" not in row for row in dumped["history"])
        assert dumped.get("mwrr_line"), "the JSON has no mwrr_line"
        assert all(set(row) == {"date", "annualized", "cumulative"} for row in dumped["mwrr_line"]), "mwrr_line rows"


# =============================================================================
# 7. EVENT SERIES UNCHANGED
# =============================================================================


class TestEventSeriesUnchanged:
    @pytest.mark.parametrize("name", ["income_history", "cost_history", "deposit_history", "acquisition_funding"])
    def test_same_points_as_the_services_methods(self, scenario, name):
        got = getattr(scenario.report, name)
        assert got is not None, f"the report has no {name}"
        assert _norm(got) == _norm(scenario.standalone[name])
        assert all("through" not in row for row in got.model_dump()["points"]), f"{name} points carry a through"

    def test_presence_barrier_every_event_series_has_points(self, scenario):
        """Precondition: the whole history holds one income, one cost, two deposits and two BUYs."""
        if scenario.start is None:
            assert [len(scenario.report.income_history.points), len(scenario.report.cost_history.points)] == [1, 1]
            assert len(scenario.report.deposit_history.points) >= 2
            assert len(scenario.report.acquisition_funding.points) >= 2

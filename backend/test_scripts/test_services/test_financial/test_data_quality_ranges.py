"""MF-P4b (D-P4 cure B, contract §3 and §4, §8.5–§8.6) — the report's data quality as ranges, and the stale FX pair.

Today ``DataQualityReport.incomplete_nav_dates`` lists every incomplete day, and ``missing_fx_pairs[].dates`` lists the
movements and every valuation day together. The contract:
- ``incomplete_nav_ranges`` (and ``incomplete_book_value_ranges`` / ``incomplete_allocation_ranges`` /
  ``incomplete_valuation_ranges``): ``List[DateSpan]``, today's days with the consecutive ones merged;
- ``missing_fx_pairs[i].ranges``: the valuation days of the pair (the engine's states that list it, in the window)
  merged into runs; ``missing_fx_pairs[i].dates``: only the movement dates (``engine_result.missing_fx``);
- the engine state gains ``stale_fx_pairs`` (``"USD/EUR"``): the pairs a day reads to value its held securities whose
  rate comes from a stored row older than ``STALE_PRICE_THRESHOLD_DAYS`` (7) days; the day a pair turns stale is a
  segment start; ``DataQualityReport.stale_fx_pairs`` lists the pairs stale on the report's valuation day as
  ``StaleFxPair(pair, last_rate_date, stale_days = valuation day − last_rate_date)``.
The old ``incomplete_*_dates`` fields stay for now (the risk side reads them): their removal is not tested.

The book (report EUR, user U owns broker A at share 1):
- A deposits 1000 EUR and 2000 USD on Monday 2025-03-03, buys 10 Y (a USD stock) for 1000 USD on 03-04; Y is quoted every
  weekday 03-03..04-01 (then never again);
- EUR/USD is stored every weekday from 03-10 to Tuesday 04-15: before 03-10 the pair is missing — the two USD movements
  (03-03, 03-04) and every valuation day 03-04..03-09; after 04-15 the last row is carried, and on
  04-23 (04-15 + 8) it turns stale, a day with no quote, no row and no movement;
- A receives 3 Z by an ADJUSTMENT with no cost and no price on 03-12 (Z is quoted once, 03-20) and 2 W the same way on
  04-07 (never quoted): the NAV is incomplete on 03-12..03-19 and on 04-07..the end — two runs.
- Windows: the whole history to Friday 04-25 (without and with the summary, whose data quality is built by
  ``get_summary``), the window 03-06..04-25 (opening inside the missing span), and the whole history to 04-20 (the last
  row 5 days old: no stale pair).

What is tested:
1. ``TestSchemas`` (pure) — the new fields and their empty defaults; ``StaleFxPair``; ``WACMissingPairInfo.ranges``.
2. ``TestIncompleteRanges`` — ``incomplete_nav_ranges`` = the engine's incomplete days in the window, merged (two runs,
   clipped at a window's start); the three other ranges are empty, as today's lists always are; the NAV_INCOMPLETE issue
   still counts the days (guard).
3. ``TestMissingFxRangesAndDates`` — ``ranges`` = the merged valuation days; ``dates`` = the engine's movement dates only
   (without the summary); with the summary every date is a movement date.
4. ``TestStaleFxPair`` — the report lists ``USD/EUR`` with last date 04-15 and 10 days; nothing at 04-20; the engine's
   04-23 is a segment start and every day's ``stale_fx_pairs`` holds the pair exactly when its last row is more than 7
   days old.

RED on HEAD 1164a1e65: every test reading a new field (``*_ranges``, ``ranges``, ``stale_fx_pairs``), the movement-only
``dates`` (HEAD lists 03-05..03-09 too) and the 04-23 segment start; GREEN on HEAD: the presence barriers and the
NAV_INCOMPLETE guard.

Isolation: PURE with respect to the lane — each scenario's database is a private SQLite file under a pytest temporary
directory (the app schema, ``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no
server, no network. The report, WAC and engine blob caches are emptied around each scenario. No sleep, no wall clock
(every window has an explicit end), no translated text (issues by ``code``).

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).

Reference: backend/app/services/portfolio_service.py (get_report, get_summary, _engine_missing_fx_pairs),
backend/app/services/financial_math/portfolio/data_quality.py, backend/app/services/financial_math/portfolio/daily_state.py,
backend/app/services/fx/conversion.py (UnitRateSteps.rate_day_at), backend/app/schemas/portfolio.py, schemas/wac.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.schemas.portfolio as portfolio_schemas
import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import DataQualityReport, IssueCode, PortfolioReportQuery, PortfolioReportResponse
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
PAIR = "USD/EUR"
FIRST_DAY = date(2025, 3, 3)
BUY_Y_DAY = date(2025, 3, 4)
FIRST_RATE = date(2025, 3, 10)
Z_IN_DAY, Z_QUOTE_DAY = date(2025, 3, 12), date(2025, 3, 20)
LAST_Y_QUOTE = date(2025, 4, 1)
W_IN_DAY = date(2025, 4, 7)
LAST_RATE = date(2025, 4, 15)
FX_TURN = LAST_RATE + timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 1)  # 2025-04-23
END = date(2025, 4, 25)
FRESH_END = date(2025, 4, 20)
WINDOW_START = date(2025, 3, 6)

DATE_FIELDS_TODAY = ("incomplete_nav_dates", "incomplete_book_value_dates", "incomplete_allocation_dates", "incomplete_valuation_dates")
NEW_RANGE_FIELDS = ("incomplete_nav_ranges", "incomplete_book_value_ranges", "incomplete_allocation_ranges", "incomplete_valuation_ranges")


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _weekdays(first: date, last: date) -> list[date]:
    return [day for day in _days(first, last) if day.weekday() < 5]


RATE_DAYS = _weekdays(FIRST_RATE, LAST_RATE)
Y_QUOTE_DAYS = _weekdays(FIRST_DAY, LAST_Y_QUOTE)


def _runs(days) -> list[tuple[date, date]]:
    """Consecutive days merged: [(start, end), …]."""
    runs: list[tuple[date, date]] = []
    for day in sorted(set(days)):
        if runs and day == runs[-1][1] + timedelta(days=1):
            runs[-1] = (runs[-1][0], day)
        else:
            runs.append((day, day))
    return runs


def _spans(items) -> list[tuple[date, date]]:
    return [(item.start, item.end) for item in items]


# =============================================================================
# THE BOOK AND THE SCENARIOS
# =============================================================================


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@dataclass
class _Scenario:
    start: date | None
    end: date
    summary: bool
    report: PortfolioReportResponse
    result: Any  # the engine result of the service's own call
    tx_dates: set[date]

    @property
    def quality(self) -> DataQualityReport:
        quality = self.report.summary.data_quality if self.summary else self.report.data_quality
        assert quality is not None, "the report has no data quality"
        return quality

    def window(self) -> list[date]:
        first = self.result.daily_states.first_date
        return _days(first if self.start is None else max(first, self.start), self.end)


def _tx(broker: Broker, tx_type: TransactionType, day: date, *, amount: str = "0", currency: str | None = EUR, asset: Asset | None = None, quantity: str = "0") -> Transaction:
    return Transaction(broker_id=broker.id, asset_id=asset.id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency)


def _price(asset: Asset, day: date, close: Decimal, currency: str) -> PriceHistory:
    return PriceHistory(asset_id=asset.id, date=day, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=currency, source_plugin_key="p4b_dq")


async def _seed(session: AsyncSession) -> int:
    tag = uuid4().hex[:12]
    user = User(username=f"p4bdq_{tag}", email=f"p4bdq_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"P4b DQ {tag}")
    y = Asset(display_name=f"P4b DQ Y {tag}", currency="USD", asset_type=AssetType.STOCK)
    z = Asset(display_name=f"P4b DQ Z {tag}", currency=EUR, asset_type=AssetType.STOCK)
    w = Asset(display_name=f"P4b DQ W {tag}", currency=EUR, asset_type=AssetType.STOCK)
    session.add_all([user, broker, y, z, w])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    session.add_all(_price(y, day, Decimal("100") + Decimal(day.toordinal() % 9), "USD") for day in Y_QUOTE_DAYS)
    session.add(_price(z, Z_QUOTE_DAY, Decimal("30"), EUR))
    session.add_all(FxRate(date=day, base=EUR, quote="USD", rate=Decimal("1.08") + Decimal("0.001") * (day.toordinal() % 5), source="P4B_DQ") for day in RATE_DAYS)
    session.add_all(
        [
            _tx(broker, TransactionType.DEPOSIT, FIRST_DAY, amount="1000"),
            _tx(broker, TransactionType.DEPOSIT, FIRST_DAY, amount="2000", currency="USD"),
            _tx(broker, TransactionType.BUY, BUY_Y_DAY, amount="-1000", currency="USD", asset=y, quantity="10"),
            _tx(broker, TransactionType.ADJUSTMENT, Z_IN_DAY, currency=None, asset=z, quantity="3"),
            _tx(broker, TransactionType.ADJUSTMENT, W_IN_DAY, currency=None, asset=w, quantity="2"),
        ]
    )
    await session.commit()
    return user.id


async def _run(directory: Path, start: date | None, end: date, summary: bool) -> _Scenario:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'p4b_dq.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id = await _seed(session)
        _clear_portfolio_caches()
        query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=start, end=end), target_currency=EUR, include_summary=summary, include_history=True, include_allocation_history=False)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            report = await PortfolioService(session).get_report(user_id, query)
        _clear_portfolio_caches()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # The service's own engine call (get_report, step 1)
            result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, broker_ids=None, date_from=None, date_to=end, target_currency=EUR, include_candles=False, include_acquisition_funding=False, period_start=None)
            tx_dates = {row.date for row in (await session.execute(Transaction.__table__.select())).all()}
        return _Scenario(start=start, end=end, summary=summary, report=report, result=result, tx_dates=tx_dates)
    finally:
        await engine.dispose()
        _clear_portfolio_caches()


SCENARIOS = {
    "whole": (None, END, False),
    "whole-summary": (None, END, True),
    "window": (WINDOW_START, END, False),
    "fresh": (None, FRESH_END, False),
}


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory) -> dict[str, _Scenario]:
    """Every scenario once (a private database each)."""
    return {name: asyncio.run(_run(tmp_path_factory.mktemp(f"p4b_dq_{name}"), *args)) for name, args in SCENARIOS.items()}


def _incomplete_days(sc: _Scenario) -> list[date]:
    return [day for day in sc.window() if not sc.result.daily_states.state_on(day).nav_complete]


def _valuation_days(sc: _Scenario, pair: str) -> list[date]:
    return [day for day in sc.window() if pair in sc.result.daily_states.state_on(day).missing_fx_pairs]


def _pair_info(sc: _Scenario, pair: str):
    info = next((item for item in sc.quality.missing_fx_pairs if item.pair == pair), None)
    assert info is not None, f"{pair} is not in missing_fx_pairs ({[item.pair for item in sc.quality.missing_fx_pairs]})"
    return info


# =============================================================================
# 1. SCHEMAS
# =============================================================================


class TestSchemas:
    @pytest.mark.parametrize("name", [*NEW_RANGE_FIELDS, "stale_fx_pairs"])
    def test_data_quality_report_new_fields_default_empty(self, name):
        assert name in DataQualityReport.model_fields, f"DataQualityReport has no {name}"
        assert getattr(DataQualityReport(), name) == []

    @pytest.mark.parametrize("name", DATE_FIELDS_TODAY)
    def test_the_old_date_fields_stay(self, name):
        """Guard: the risk side still reads them until workstream J moves it (contract, coordinator 25/10)."""
        assert name in DataQualityReport.model_fields

    def test_stale_fx_pair_model(self):
        model = getattr(portfolio_schemas, "StaleFxPair", None)
        assert model is not None, "schemas.portfolio has no StaleFxPair"
        assert set(model.model_fields) == {"pair", "last_rate_date", "stale_days"}
        with pytest.raises(ValueError):
            model(pair=PAIR, last_rate_date=LAST_RATE, stale_days=10, extra=1)

    def test_missing_pair_info_has_ranges(self):
        assert "ranges" in WACMissingPairInfo.model_fields, "WACMissingPairInfo has no ranges"
        assert WACMissingPairInfo(pair=PAIR, dates=[]).ranges == []


# =============================================================================
# 2. INCOMPLETE RANGES
# =============================================================================


class TestIncompleteRanges:
    def test_presence_barrier_two_incomplete_runs(self, scenarios):
        """Precondition (green on HEAD): Z's days and W's days, two runs."""
        assert _runs(_incomplete_days(scenarios["whole"])) == [(Z_IN_DAY, Z_QUOTE_DAY - timedelta(days=1)), (W_IN_DAY, END)]

    @pytest.mark.parametrize("name", ["whole", "whole-summary", "window", "fresh"])
    def test_incomplete_nav_ranges_merge_the_days(self, scenarios, name):
        sc = scenarios[name]
        ranges = getattr(sc.quality, "incomplete_nav_ranges", None)
        assert ranges is not None, "the data quality has no incomplete_nav_ranges"
        assert _spans(ranges) == _runs(_incomplete_days(sc))

    @pytest.mark.parametrize("name", ["whole", "whole-summary"])
    @pytest.mark.parametrize("field", NEW_RANGE_FIELDS[1:])
    def test_the_other_ranges_are_empty_as_todays_lists(self, scenarios, name, field):
        quality = scenarios[name].quality
        assert field in type(quality).model_fields, f"the data quality has no {field}"
        assert getattr(quality, field) == []

    @pytest.mark.parametrize("name", ["whole", "window"])
    def test_nav_incomplete_issue_still_counts_the_days(self, scenarios, name):
        """Guard (green on HEAD): the issue's count and bounds are the incomplete days'."""
        sc = scenarios[name]
        days = _incomplete_days(sc)
        issue = next((item for item in sc.quality.issues if item.code == IssueCode.NAV_INCOMPLETE), None)
        assert issue is not None, "no NAV_INCOMPLETE issue"
        assert (issue.count, issue.message_params["date_from"], issue.message_params["date_to"]) == (len(days), days[0].isoformat(), days[-1].isoformat())


# =============================================================================
# 3. MISSING FX: RANGES FOR THE VALUATION DAYS, DATES FOR THE MOVEMENTS
# =============================================================================


class TestMissingFxRangesAndDates:
    def test_presence_barrier_valuation_days_beyond_the_movements(self, scenarios):
        """Precondition (green on HEAD): USD/EUR is missing on the valuation days 03-04..03-09 (from the BUY of Y: the USD
        cash of 03-03 is no valuation failure of the state) and on the movements of 03-03 and 03-04 only."""
        sc = scenarios["whole"]
        assert _valuation_days(sc, PAIR) == _days(BUY_Y_DAY, FIRST_RATE - timedelta(days=1))
        assert sorted(sc.result.missing_fx.get(PAIR, ())) == [FIRST_DAY, BUY_Y_DAY]

    @pytest.mark.parametrize("name", ["whole", "whole-summary", "window"])
    def test_ranges_are_the_merged_valuation_days(self, scenarios, name):
        sc = scenarios[name]
        info = _pair_info(sc, PAIR)
        ranges = getattr(info, "ranges", None)
        assert ranges is not None, "missing_fx_pairs[] has no ranges"
        assert _spans(ranges) == _runs(_valuation_days(sc, PAIR))

    def test_the_window_clips_the_range(self, scenarios):
        info = _pair_info(scenarios["window"], PAIR)
        assert _spans(getattr(info, "ranges", None) or []) == [(WINDOW_START, FIRST_RATE - timedelta(days=1))]

    @pytest.mark.parametrize("name", ["whole", "window"])
    def test_dates_are_the_movement_dates_only(self, scenarios, name):
        """RED on HEAD: the dates hold 03-03..03-09, the valuation days too."""
        sc = scenarios[name]
        assert _pair_info(sc, PAIR).dates == sorted(sc.result.missing_fx[PAIR])

    def test_with_the_summary_every_date_is_a_movement_date(self, scenarios):
        sc = scenarios["whole-summary"]
        dates = set(_pair_info(sc, PAIR).dates)
        assert dates, "no movement date listed"
        assert dates <= sc.tx_dates, f"dates that are no movement: {sorted(dates - sc.tx_dates)}"


# =============================================================================
# 4. THE STALE FX PAIR
# =============================================================================


def _stale_fx(state) -> set[str]:
    assert hasattr(state, "stale_fx_pairs"), "DailyPortfolioState has no stale_fx_pairs"
    return set(state.stale_fx_pairs)


class TestStaleFxPair:
    @pytest.mark.parametrize("name", ["whole", "whole-summary", "window"])
    def test_report_lists_the_stale_pair(self, scenarios, name):
        quality = scenarios[name].quality
        stale = getattr(quality, "stale_fx_pairs", None)
        assert stale is not None, "the data quality has no stale_fx_pairs"
        assert [item.model_dump() for item in stale] == [{"pair": PAIR, "last_rate_date": LAST_RATE, "stale_days": (END - LAST_RATE).days}]

    def test_no_stale_pair_while_the_row_is_recent(self, scenarios):
        """At 04-20 the last row is 5 days old: no stale pair (presence barrier: the field exists and the pair is read)."""
        sc = scenarios["fresh"]
        assert "stale_fx_pairs" in type(sc.quality).model_fields, "the data quality has no stale_fx_pairs"
        assert PAIR not in sc.result.daily_states.state_on(FRESH_END).missing_fx_pairs
        assert sc.quality.stale_fx_pairs == []

    def test_the_turn_is_a_segment_start(self, scenarios):
        """RED on HEAD: nothing else happens on 04-23 (no quote, no row, no movement), so only the FX turn starts it."""
        ds = scenarios["whole"].result.daily_states
        assert FX_TURN in {segment.start for segment in ds.segments}, f"segments around the turn: {[(s.start, s.end) for s in ds.iter_segments(LAST_RATE, END)]}"

    def test_presence_barrier_nothing_else_happens_on_the_turn(self, scenarios):
        """Precondition (green on HEAD): 04-23 is no quote, row or movement day, and no price turns stale on it."""
        sc = scenarios["whole"]
        assert FX_TURN not in sc.tx_dates and FX_TURN not in RATE_DAYS and FX_TURN not in Y_QUOTE_DAYS
        assert LAST_Y_QUOTE + timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 1) != FX_TURN

    def test_every_days_stale_pairs(self, scenarios):
        """The pair is stale on a day exactly when Y is held and the last stored row is more than 7 days old."""
        sc = scenarios["whole"]
        for day in sc.window():
            state = sc.result.daily_states.state_on(day)
            earlier = [row_day for row_day in RATE_DAYS if row_day <= day]
            expected = {PAIR} if day >= BUY_Y_DAY and earlier and (day - earlier[-1]).days > STALE_PRICE_THRESHOLD_DAYS else set()
            assert _stale_fx(state) == expected, day
        assert _stale_fx(sc.result.daily_states.state_on(FX_TURN - timedelta(days=1))) == set()
        assert _stale_fx(sc.result.daily_states.state_on(FX_TURN)) == {PAIR}

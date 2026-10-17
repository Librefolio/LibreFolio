"""SEC8-1b — a historical replay walks a bounded window: it ends by tomorrow and starts at most 100 years before its end.

R13-SEC8 (E), assigned to J. ``/risk/query`` (any user) replays a stress scenario over ``replay_range``, a parameter of the
stress analytic (``{"method": "historical_replay", "replay_range": {...}}``), and that window has no bounds:
``DateRangeModel`` only checks that its end is not before its start. ``risk/replay.py::prepare_historical_replay_context``
hands it raw to ``load_price_window_facts``, to ``replay_coverage`` and ``verified_replay_range``, and to
``prepare_asset_series(date_range=replay_range)``. Since X-R55 ``get_prices_bulk`` ends every item at
``latest_range_end()`` (the server's tomorrow) and starts its daily walk at the first stored price; but a price can be
stored at any date (``POST /assets/prices``), and a window starting the day after it counts as covered at both ends
(``STALE_PRICE_THRESHOLD_DAYS`` = 7) and walks every day since. R13-SEC7-1's clamp in ``risk/scope.py`` covers a portfolio
scope's period, not this window.

THE RULE (coordinator, 17/10; the fix follows these reds). The replay window ends at ``latest_range_end()`` at most and
starts no earlier than ``range_span_floor(end)`` = ``end − RANGE_SPAN_LIMIT_DAYS`` (36 525 days,
``utils/date_range_limits.py``); a start after that end moves to the end. The bounded window drives the facts, the
coverage, the suggestion and the preparation, and ``analyzed_range`` falls back to it; the output's ``replay_range``
and the parameters the metadata repeats echo the request, unchanged. The request's own period is bounded the same way,
at the entry of ``RiskService.execute``, for every scope kind (R4, G3: one ASSET scope is enough, the asset-series call
is shared).

TODAY (base ``4e11fabec``) the window reaches the facts, the coverage, the suggestion and the preparation raw:
- a window ending in the future excludes an asset quoted until yesterday as stale at its end (R1), and a suggestion keeps
  that end, after tomorrow (R3);
- a window starting the day after a planted price is covered at both ends and walks every day since (R2: 39 999 days);
  one from year 1 excludes its asset at the end only to suggest [0001-01-03, its last quote], ~739 000 days (R5) — walked
  when applied (G2) or asked as the request's own period (G3, and R4 over P: 39 999 days).
``analyzed_range`` never echoes the request's window: ``plugin.py``'s ``prepared.effective_range or
params.replay_range`` is reached only when an asset has returns, so ``effective_range`` is set and ends by tomorrow
(X-R55).

THE BOOKS, every date relative to ``date.today()``, every close moving from day to day (``_close``):
- A: quoted every weekday from today − 40 to yesterday (the "recent quotes");
- B: one quote planted at P = today − 40 000, beyond the span but near enough for the old walk to take about a second,
  and the recent quotes;
- C: first quoted at today − 10 (the nearest weekday when that day is not one), then every weekday through yesterday;
- G: one quote planted at ``date(1, 1, 2)`` — clear of ``date.min``'s arithmetic — and the recent quotes.
Each replay runs one window over one asset (an ASSET scope, ``current_composition`` as the stress requires; the request's
own period is the last 30 days); R4 and G3 ask the KPIs of one asset over the request's period.

THE RUNS. ``TestExtremeReplayRangesFinishQuickly`` (G2, G3) stays out of the red run: on the old code each walks
~739 000 days. Its tests pin dates and spans, never the elapsed time. The red run:
``services risk-all "test_risk_replay_range_bounds and not TestExtremeReplayRangesFinishQuickly"``.

READING A REPLAY. An asset the replay leaves out is reported in two places: on a replayed result in
``metadata.excluded_assets`` (``historical_replay_<reason>``); when nothing is left to replay — the one asset of an
ASSET scope excluded — the stress is unavailable (``insufficient_history``) and its error's ``details.excluded_assets``
name it (``<reason>``), with the suggested window if any. ``_replay_exclusions`` and ``_suggested_range`` read both.
``_stated_dates`` reads every date of the result, the two echoes of the request's window aside (``output.replay_range``
and the parameters the metadata repeats).

Isolation: a private SQLite file under ``tmp_path`` built by ``create_all`` (as ``test_risk_price_day_budget.py``) — no
lane database, no server, no network; uuid4 names; the market holiday table empty (built for real, it takes a QuantLib
process). Not a seam file: nothing here lifts the bound (``_range_bounds.lift_range_bound``) — the bound is the subject.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, PriceHistory
from backend.app.schemas.risk import RiskAnalyticResult, RiskQueryRequest, RiskResultStatus
from backend.app.services.assets import price_query
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.service import RiskService

SPAN_DAYS = 36_525  # RANGE_SPAN_LIMIT_DAYS: how far back a per-day walk may go from the end of its range
PLANTED_DAYS_BACK = 40_000  # B's planted quote: today − 40 000
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The request's window, echoed unchanged: in the output, and in the parameters the metadata repeats.
ECHOES = (("output", "replay_range"), ("metadata", "params", "replay_range"))


# --------------------------------------------------------------------------- #
# The private database, the holiday table
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own; disposed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'risk_replay_range_bounds.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The market holiday table, empty, wherever a request awaits it: built for real it takes a process of its own."""

    async def _none() -> frozenset[date]:
        return frozenset()

    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _none)
    monkeypatch.setattr(price_query, "ensure_market_holidays", _none)


# --------------------------------------------------------------------------- #
# Days and books
# --------------------------------------------------------------------------- #


def _days_from_today(n: int) -> date:
    return date.today() + timedelta(days=n)


def _weekdays(first: date, last: date) -> list[date]:
    days = (first + timedelta(days=n) for n in range((last - first).days + 1))
    return [day for day in days if day.weekday() < 5]


def _first_weekday_from(day: date) -> date:
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def _last_weekday_until(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def _nearest_weekday(day: date) -> date:
    """``day``, or the weekday next to it: a Saturday moves back to Friday, a Sunday on to Monday."""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _close(day: date) -> Decimal:
    """A close that moves from one day to the next, the same for the same day in every book."""
    ordinal = day.toordinal()
    return Decimal(100) + Decimal(ordinal % 11) + Decimal(ordinal % 4) / 4


def _recent_quotes() -> list[date]:
    """Every weekday from today − 40 to yesterday."""
    return _weekdays(_days_from_today(-40), _days_from_today(-1))


def _first_recent_quote() -> date:
    """The first of the recent quotes: the first weekday from today − 40."""
    return _first_weekday_from(_days_from_today(-40))


async def _asset(engine: AsyncEngine, label: str, quotes: Sequence[date]) -> int:
    """An EUR asset of the private database quoted on ``quotes``, named with a uuid4."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"SEC8-1b {label} {uuid4().hex}", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add_all([PriceHistory(asset_id=asset.id, date=day, close=_close(day), currency="EUR", source_plugin_key="MANUAL") for day in quotes])
        await session.commit()
        return asset.id


# --------------------------------------------------------------------------- #
# Requests and readings
# --------------------------------------------------------------------------- #


def _replay_request(asset_id: int, window: tuple[date, date]) -> RiskQueryRequest:
    """One historical replay of ``window`` over the asset alone; the request's own period is the last 30 days."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset", "asset_id": asset_id},
            "date_range": {"start": _days_from_today(-30).isoformat(), "end": _days_from_today(-1).isoformat()},
            "target_currency": "EUR",
            "mode": "current_composition",
            "composition_policy": "current_buy_and_hold",
            "analytics": [{"instance_id": "replay", "analytic_code": "stress", "parameters": {"method": "historical_replay", "replay_range": {"start": window[0].isoformat(), "end": window[1].isoformat()}}}],
        }
    )


async def _execute(engine: AsyncEngine, request: RiskQueryRequest, instance_id: str) -> RiskAnalyticResult:
    """``RiskService.execute`` on the private database; the result of ``instance_id``, found by its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await RiskService(session).execute(user_id=1, request=request)
    return next(item for item in response.items if item.instance_id == instance_id)


async def _replay(engine: AsyncEngine, asset_id: int, window: tuple[date, date]) -> RiskAnalyticResult:
    return await _execute(engine, _replay_request(asset_id, window), "replay")


def _kpi_request(asset_id: int, period: tuple[date, date]) -> RiskQueryRequest:
    """The KPIs of the asset over the request's own ``period``, historical."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset", "asset_id": asset_id},
            "date_range": {"start": period[0].isoformat(), "end": period[1].isoformat()},
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [{"instance_id": "kpi", "analytic_code": "historical_kpi"}],
        }
    )


def _calendar_days(result: RiskAnalyticResult) -> int | None:
    """The span the result read: its last return date minus the baseline (``observed_annualization``)."""
    return None if result.metadata is None else result.metadata.calendar_days


def _replayed(result: RiskAnalyticResult) -> list[int]:
    """The assets the replay gives an impact to."""
    return sorted(impact.asset_id for impact in result.output.impacts) if result.output is not None else []


def _replay_exclusions(result: RiskAnalyticResult) -> dict[int, str]:
    """The assets the replay leaves out, and why, wherever the result says it (see READING A REPLAY)."""
    found: dict[int, str] = {}
    if result.metadata is not None:
        for item in result.metadata.excluded_assets:
            if item.reason.startswith("historical_replay_"):
                found[item.asset_id] = item.reason.removeprefix("historical_replay_")
    if result.error is not None:
        for item in result.error.details.get("excluded_assets", []):
            found[item["asset_id"]] = item["reason"]
    return found


def _suggested_range(result: RiskAnalyticResult) -> tuple[date, date] | None:
    """The window the replay proposes instead, wherever the result carries it."""
    audit = result.metadata.historical_replay_audit if result.metadata is not None else None
    if audit is not None and audit.suggested_range is not None:
        return audit.suggested_range.start, audit.suggested_range.end or audit.suggested_range.start
    if result.error is not None and "suggested_range" in result.error.details:
        raw = result.error.details["suggested_range"]
        return date.fromisoformat(raw["start"]), date.fromisoformat(raw["end"])
    return None


def _analyzed_range(result: RiskAnalyticResult) -> tuple[date, date] | None:
    analyzed = result.metadata.analyzed_range if result.metadata is not None else None
    return None if analyzed is None else (analyzed.start, analyzed.end or analyzed.start)


def _echo(result: RiskAnalyticResult) -> tuple[date, date] | None:
    """The window the output echoes, the request's."""
    echoed = result.output.replay_range if result.output is not None else None
    return None if echoed is None else (echoed.start, echoed.end or echoed.start)


def _dates(value: Any, path: tuple = ()) -> Iterator[tuple[str, date]]:
    if any(path[: len(echo)] == echo for echo in ECHOES):
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            yield from _dates(nested, (*path, key))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _dates(nested, (*path, index))
    elif isinstance(value, str) and ISO_DATE.match(value):
        yield ".".join(str(part) for part in path), date.fromisoformat(value)


def _stated_dates(result: RiskAnalyticResult) -> list[tuple[str, date]]:
    """Every date the result states, with its path, the two echoes of the request's window aside."""
    return list(_dates(result.model_dump(mode="json")))


def _today_reading(result: RiskAnalyticResult) -> str:
    """What the result says, for the failure message: status, error, analyzed range and span."""
    metadata = result.metadata
    error = None if result.error is None else (result.error.code.value, result.error.details)
    span = None if metadata is None else (metadata.n_observations, metadata.calendar_days)
    return f"status={result.status.value} error={error} analyzed_range={_analyzed_range(result)} (n_observations, calendar_days)={span}"


# --------------------------------------------------------------------------- #
# R1 — a window ending after tomorrow
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r1_a_window_ending_after_tomorrow_is_replayed_to_tomorrow_and_dates_nothing_later(private_db):
    """R1: A quoted every weekday until yesterday, the window [today − 20, today + 400]. The window ends at tomorrow, so A is
    priced at both of its ends and replayed: no exclusion, no suggestion, the analyzed range from A's first quote in the
    window to its last, nothing in the result dated after ``latest_range_end()``; the output echoes the request.

    Today (read 17/10/2026): unavailable, ``insufficient_history``. A, the scope's only asset, is excluded as
    ``stale_at_window_end`` (its last quote 401 days before the window's end), so nothing is left to replay; the error
    suggests [today − 20, A's last quote], which recovers A. No output, so no echo; the metadata's ``analyzed_range`` is
    the request's own period (from today − 30), not the replay's. Nothing is dated after tomorrow.
    """
    today = date.today()
    latest_end = today + timedelta(days=1)  # latest_range_end()
    asset_a = await _asset(private_db, "A", _recent_quotes())
    window = (today - timedelta(days=20), today + timedelta(days=400))

    result = await _replay(private_db, asset_a, window)

    observed = {
        "error": None if result.error is None else result.error.code,
        "replayed": _replayed(result),
        "excluded": _replay_exclusions(result),
        "suggested_range": _suggested_range(result),
        "analyzed_range": _analyzed_range(result),
        "dated after latest_range_end()": [(path, day) for path, day in _stated_dates(result) if day > latest_end],
        "replay_range echo": _echo(result),
    }
    assert observed == {
        "error": None,
        "replayed": [asset_a],
        "excluded": {},
        "suggested_range": None,
        "analyzed_range": (_first_weekday_from(window[0]), _last_weekday_until(today - timedelta(days=1))),
        "dated after latest_range_end()": [],
        "replay_range echo": window,
    }, _today_reading(result)


# --------------------------------------------------------------------------- #
# R2 — a window starting more than 36 525 days back, over a planted price
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r2_a_window_starting_beyond_the_span_starts_at_its_floor_where_the_planted_price_is_stale(private_db):
    """R2: B quoted on P = today − 40 000 and every weekday from today − 40, the window [P + 1, yesterday]. The window starts
    at yesterday − 36 525; B's last quote before that day is P, thousands of days stale: B is excluded as stale at the
    window's start, and the replay suggests the part of the bounded window B covers, exactly [B's first quote in it + 1,
    yesterday] — the first recent quote, today − 40 or the Monday after it.

    Today (read 17/10/2026): B is covered at both ends (P one day before the window) and replayed — status ok, no
    exclusion, no suggestion. The walk runs from P: ``calendar_days`` 39 999 (last return date − baseline P), 30
    observations.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    planted = today - timedelta(days=PLANTED_DAYS_BACK)
    asset_b = await _asset(private_db, "B", [planted, *_recent_quotes()])
    window = (planted + timedelta(days=1), yesterday)

    result = await _replay(private_db, asset_b, window)

    observed = {
        "replayed": _replayed(result),
        "excluded": _replay_exclusions(result),
        "suggested_range": _suggested_range(result),
    }
    assert observed == {
        "replayed": [],
        "excluded": {asset_b: "stale_at_window_start"},
        "suggested_range": (_first_recent_quote() + timedelta(days=1), yesterday),
    }, _today_reading(result)


# --------------------------------------------------------------------------- #
# R3 — the suggestion for a window ending after tomorrow
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r3_the_suggestion_for_a_window_ending_after_tomorrow_ends_at_tomorrow(private_db):
    """R3: C first quoted at today − 10 (the nearest weekday when that day is not one, so the gap from the window's start
    stays above 7 days) and every weekday through yesterday, the window [today − 20, today + 3]. C starts quoting after the
    window's start: it is excluded, and the replay suggests the part of the window C covers. Bounded, the window ends at
    tomorrow, and so does the suggestion: exactly [C's first quote + 1, ``latest_range_end()``]. Nothing in the result is
    dated after tomorrow.

    Today (read 17/10/2026): unavailable, ``insufficient_history``; C excluded as ``starts_after_window_start``, as after;
    the suggestion keeps the window's end — [C's first quote + 1, today + 3] — and is the one date after tomorrow
    (``error.details.suggested_range.end``).
    """
    today = date.today()
    latest_end = today + timedelta(days=1)
    first_quote = _nearest_weekday(today - timedelta(days=10))
    asset_c = await _asset(private_db, "C", _weekdays(first_quote, today - timedelta(days=1)))
    window = (today - timedelta(days=20), today + timedelta(days=3))

    result = await _replay(private_db, asset_c, window)

    observed = {
        "excluded": _replay_exclusions(result),
        "suggested_range": _suggested_range(result),
        "dated after latest_range_end()": [(path, day) for path, day in _stated_dates(result) if day > latest_end],
    }
    assert observed == {
        "excluded": {asset_c: "starts_after_window_start"},
        "suggested_range": (first_quote + timedelta(days=1), latest_end),
        "dated after latest_range_end()": [],
    }, _today_reading(result)


# --------------------------------------------------------------------------- #
# R5 — a window from year 1 to year 9999: the suggestion the UI offers
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r5_a_window_from_year_one_to_year_9999_suggests_only_the_bounded_window(private_db):
    """R5: G quoted on ``date(1, 1, 2)`` and every weekday from today − 40 to yesterday, the window [``date(1, 1, 3)``,
    ``date(9999, 12, 30)``]. Bounded, it runs from tomorrow − 36 525 to tomorrow: G's last quote before it is the planted
    one, so G is excluded as stale at the window's start, and the replay suggests exactly [G's first recent quote + 1,
    ``latest_range_end()``]. Nothing in the result is dated outside the bounded window.

    Today (read 17/10/2026): unavailable, ``insufficient_history``; G excluded as ``stale_at_window_end``, and the replay
    suggests [0001-01-03, G's last quote] (``error.details.suggested_range.start`` the one date outside): applied, that
    window covers G at both ends and walks ~739 000 days — the long walk the UI offers (G2). The old code answers this
    request quickly (0.06 s when read): G is excluded before any walk.
    """
    latest_end = date.today() + timedelta(days=1)
    floor = latest_end - timedelta(days=SPAN_DAYS)  # range_span_floor(latest_range_end())
    asset_g = await _asset(private_db, "G", [date(1, 1, 2), *_recent_quotes()])

    result = await _replay(private_db, asset_g, (date(1, 1, 3), date(9999, 12, 30)))

    observed = {
        "excluded": _replay_exclusions(result),
        "suggested_range": _suggested_range(result),
        "dated outside the bounded window": [(path, day) for path, day in _stated_dates(result) if not floor <= day <= latest_end],
    }
    assert observed == {
        "excluded": {asset_g: "stale_at_window_start"},
        "suggested_range": (_first_recent_quote() + timedelta(days=1), latest_end),
        "dated outside the bounded window": [],
    }, _today_reading(result)


# --------------------------------------------------------------------------- #
# G1 — GUARD: a plain past replay
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_guard_g1_a_plain_past_replay_is_unchanged(private_db):
    """GUARD (green today and after): the window [today − 25, today − 5] over A lies inside every bound. A is replayed from
    its close on the last weekday before the window (the baseline, today − 26 or the Friday before it) to its last quote in
    the window; the analyzed range runs from its first quote in the window to that last one, one observation a weekday;
    nothing is excluded or suggested; the output echoes the request.
    """
    today = date.today()
    asset_a = await _asset(private_db, "A", _recent_quotes())
    window = (today - timedelta(days=25), today - timedelta(days=5))
    baseline = _last_weekday_until(window[0] - timedelta(days=1))
    last = _last_weekday_until(window[1])

    result = await _replay(private_db, asset_a, window)

    observed = {
        "status": result.status,
        "error": None if result.error is None else result.error.code,
        "excluded": _replay_exclusions(result),
        "suggested_range": _suggested_range(result),
        "analyzed_range": _analyzed_range(result),
        "n_observations": None if result.metadata is None else result.metadata.n_observations,
        "impacts": {impact.asset_id: impact.shock_return for impact in result.output.impacts} if result.output is not None else None,
        "replay_range echo": _echo(result),
    }
    assert observed == {
        "status": RiskResultStatus.OK,
        "error": None,
        "excluded": {},
        "suggested_range": None,
        "analyzed_range": (_first_weekday_from(window[0]), last),
        "n_observations": len(_weekdays(window[0], window[1])),
        "impacts": {asset_a: pytest.approx(float(_close(last) / _close(baseline)) - 1, rel=1e-9)},
        "replay_range echo": window,
    }


# --------------------------------------------------------------------------- #
# R4 — the request's own period over an ASSET scope (the coordinator may drop it)
# --------------------------------------------------------------------------- #


class TestAssetScopeMainRange:
    """R4: the same bound on the request's own period. R13-SEC7-1 clamps a portfolio scope's period
    (``risk/scope.py::load_scope_inputs``), not an asset's: ``RiskService.execute`` prepares it raw. The bound will sit at
    the entry of ``RiskService.execute``, for every scope kind; one ASSET scope is enough, the asset-series call being
    shared. The span read is ``metadata.calendar_days`` (last return date − baseline): ``analyzed_range`` runs between
    return dates, which sit on quote days only, so it never shows the baseline."""

    @pytest.mark.asyncio
    async def test_r4_an_asset_scope_period_starting_beyond_the_span_spans_at_most_the_limit(self, private_db):
        """R4: the KPIs of B (quoted on P = today − 40 000 and every weekday from today − 40) over the request's period
        [P + 1, yesterday], historical. The period starts at yesterday − 36 525, so the prepared series spans at most
        36 526 days (``RANGE_SPAN_LIMIT_DAYS`` + 1: the baseline is the day before the period).

        Today (read 17/10/2026): ``calendar_days`` 39 999 — the period prepared raw from its baseline P — with status
        ok and ``analyzed_range`` from today − 40 (B's first quote in the period) to yesterday.
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        planted = today - timedelta(days=PLANTED_DAYS_BACK)
        asset_b = await _asset(private_db, "B", [planted, *_recent_quotes()])

        result = await _execute(private_db, _kpi_request(asset_b, (planted + timedelta(days=1), yesterday)), "kpi")

        calendar_days = _calendar_days(result)
        assert calendar_days is not None and calendar_days <= SPAN_DAYS + 1, _today_reading(result)


# --------------------------------------------------------------------------- #
# G2, G3 — the extreme ranges (out of the red run: the old code walks ~739 000 days)
# --------------------------------------------------------------------------- #


class TestExtremeReplayRangesFinishQuickly:
    """G is quoted on ``date(1, 1, 2)`` and every weekday from today − 40. On the old code each test here walks every day
    from year 1 (~739 000 points, under Z-25's per-request budget), so the class stays out of the red run; bounded, it walks at
    most 36 526 days. Dates and spans are pinned, never the elapsed time."""

    @pytest.mark.asyncio
    async def test_g2_applying_todays_suggestion_starts_at_the_floor(self, private_db):
        """G2: R5's suggestion of today applied, the window [``date(1, 1, 3)``, yesterday]. Bounded, it starts at
        yesterday − 36 525: G's last quote before it is the planted one, so G is excluded as stale at the window's start,
        and the replay suggests exactly [G's first recent quote + 1, yesterday]. Nothing in the result is dated outside
        [yesterday − 36 525, ``latest_range_end()``].

        Old code: G is covered at both ends (the planted quote one day before the window) and the replay's preparation
        walks from ``date(1, 1, 2)``.
        """
        yesterday = date.today() - timedelta(days=1)
        latest_end = yesterday + timedelta(days=2)
        floor = yesterday - timedelta(days=SPAN_DAYS)
        asset_g = await _asset(private_db, "G", [date(1, 1, 2), *_recent_quotes()])

        result = await _replay(private_db, asset_g, (date(1, 1, 3), yesterday))

        observed = {
            "excluded": _replay_exclusions(result),
            "suggested_range": _suggested_range(result),
            "dated outside the bounded window": [(path, day) for path, day in _stated_dates(result) if not floor <= day <= latest_end],
        }
        assert observed == {
            "excluded": {asset_g: "stale_at_window_start"},
            "suggested_range": (_first_recent_quote() + timedelta(days=1), yesterday),
            "dated outside the bounded window": [],
        }, _today_reading(result)

    @pytest.mark.asyncio
    async def test_g3_an_asset_scope_period_from_year_one_spans_at_most_the_limit(self, private_db):
        """G3: the KPIs of G over the request's period [``date(1, 1, 3)``, yesterday], historical. The period starts at
        yesterday − 36 525, so the prepared series spans at most 36 526 days (``calendar_days``).

        Old code: the period is prepared raw, from ``date(1, 1, 2)``.
        """
        yesterday = date.today() - timedelta(days=1)
        asset_g = await _asset(private_db, "G", [date(1, 1, 2), *_recent_quotes()])

        result = await _execute(private_db, _kpi_request(asset_g, (date(1, 1, 3), yesterday)), "kpi")

        calendar_days = _calendar_days(result)
        assert calendar_days is not None and calendar_days <= SPAN_DAYS + 1, _today_reading(result)

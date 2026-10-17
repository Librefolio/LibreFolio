"""J-50 — a risk request whose price preparation exceeds the bulk day budget is refused for its size, never a 500.

Workstream J «Numeri e analisi», release 1.3. Z-25 (N77) made ``AssetSourceManager.get_prices_bulk`` raise
``BulkTooManyDaysError`` (``backend/app/utils/date_range_limits.py``) when one request would build more than
``MAX_BULK_ITEM_DAYS`` per-day points, all its items together; the prices API answers it 422. Risk calls it in
``risk/scope.py::prepare_asset_series``: for the request's period, in ``RiskService.execute`` outside every per-analytic
``try``; and for a historical replay's window, in ``risk/replay.py::prepare_historical_replay_context``, whose caller
catches only ``RiskUnavailableError``.

TODAY (base ``d67ac4603``) the error crosses ``RiskService.execute`` whole, and ``/risk/query`` maps only 403 and 404: the
user gets a 500 — for the request's period, and for one replay inside an otherwise good request.

THE RULE (coordinator, 17/10; D379's convention, ``risk_plugins/simulation/plugin.py::_resource_limit``).
``prepare_asset_series`` turns the error into ``RiskUnavailableError(code=RESOURCE_LIMIT, details={"metric":
"price_item_days", "actual": <item_days>, "limit": <max_item_days>, "remedy": "period_or_assets"})``:

1. at the main preparation, ``RiskService.execute`` answers every planned analytic unavailable with that code and those
   details — a response, no exception (HTTP 200);
2. at a replay's preparation, that analytic alone is unavailable (the existing ``except RiskUnavailableError``); the
   other analytics of the request complete;
3. GUARD: within the budget — untouched, or exactly reached — the request completes as today.

THE BOOK. One EUR asset with a close on every day of 2024 (moving every day), target EUR, ASSET scope. The fill counts one
point a day from the day before the period (``prepare_asset_series`` loads it for the first return), which holds a close
here: June is 31 points (31 May … 30 June); a replay window of 2 January … 31 October is 305 (1 January … 31 October);
November–December is 62 (31 October … 31 December). The budget is lowered where the price query reads it,
``backend.app.services.assets.price_query.MAX_BULK_ITEM_DAYS`` (Z-25's seam, ``test_bulk_limits.py``).

Isolation: a private SQLite file under ``tmp_path`` built by ``create_all`` (Z-25's pattern) — no lane database, no
server, no network; the market holiday table is an empty one (built for real, it takes a QuantLib process).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, PriceHistory
from backend.app.schemas.risk import RiskErrorCode, RiskQueryRequest, RiskQueryResponse, RiskResultStatus
from backend.app.services.assets import price_query
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.service import RiskService
from backend.app.utils.date_range_limits import BulkTooManyDaysError

OK = RiskResultStatus.OK
UNAVAILABLE = RiskResultStatus.UNAVAILABLE
RESOURCE_LIMIT = RiskErrorCode.RESOURCE_LIMIT
JUNE_POINTS = 31  # 31 May … 30 June
REPLAY_POINTS = 305  # 1 January … 31 October
NOVEMBER_DECEMBER_POINTS = 62  # 31 October … 31 December


def _refused_for_size(actual: int, limit: int) -> dict:
    """The details of a refusal for the price-day budget, as the rule writes them."""
    return {"metric": "price_item_days", "actual": actual, "limit": limit, "remedy": "period_or_assets"}


# --------------------------------------------------------------------------- #
# The private database, the holiday table, the budget
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own; disposed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'risk_price_day_budget.db'}", poolclass=NullPool)
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


@pytest.fixture
def lower_budget(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Sets the item-day budget where ``get_prices_bulk`` reads it, for the test."""

    def lower(item_days: int) -> None:
        monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", item_days)

    return lower


async def _asset_quoted_every_day_of_2024(engine: AsyncEngine) -> int:
    """An EUR asset of the private database with a close on every day of 2024, a different one each day."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name="J50 risk asset", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        day, n = date(2024, 1, 1), 0
        while day <= date(2024, 12, 31):
            session.add(PriceHistory(asset_id=asset.id, date=day, close=Decimal(100) + Decimal(n % 7) + Decimal(n) / 10, currency="EUR", source_plugin_key="MANUAL"))
            day += timedelta(days=1)
            n += 1
        await session.commit()
        return asset.id


# --------------------------------------------------------------------------- #
# The requests
# --------------------------------------------------------------------------- #


def _period_request(asset_id: int) -> RiskQueryRequest:
    """June 2024, historical: two analytics of the request's period, KPIs and the drawdown."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset", "asset_id": asset_id},
            "date_range": {"start": "2024-06-01", "end": "2024-06-30"},
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [{"instance_id": "kpi", "analytic_code": "historical_kpi"}, {"instance_id": "drawdown", "analytic_code": "drawdown_summary"}],
        }
    )


def _replay_request(asset_id: int) -> RiskQueryRequest:
    """November–December 2024, current composition: a historical replay of 2 January … 31 October, and the KPIs."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset", "asset_id": asset_id},
            "date_range": {"start": "2024-11-01", "end": "2024-12-31"},
            "target_currency": "EUR",
            "mode": "current_composition",
            "composition_policy": "current_buy_and_hold",
            "analytics": [
                {"instance_id": "replay", "analytic_code": "stress", "parameters": {"method": "historical_replay", "replay_range": {"start": "2024-01-02", "end": "2024-10-31"}}},
                {"instance_id": "kpi", "analytic_code": "historical_kpi"},
            ],
        }
    )


_REQUESTS = {"period": _period_request, "replay": _replay_request}


async def _execute(engine: AsyncEngine, request: RiskQueryRequest) -> RiskQueryResponse:
    """``RiskService.execute`` on the private database; the size error it lets through today fails the test, by name."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            return await RiskService(session).execute(user_id=1, request=request)
        except BulkTooManyDaysError as exc:
            pytest.fail(f"RiskService.execute raised BulkTooManyDaysError(item_days={exc.item_days}, max_item_days={exc.max_item_days}): /risk/query answers it 500")


def _results(response: RiskQueryResponse) -> dict[str, tuple]:
    """(status, error code, error details) of each result, by instance."""
    return {item.instance_id: (item.status, item.error.code if item.error else None, item.error.details if item.error else None) for item in response.items}


# --------------------------------------------------------------------------- #
# Rule 1: the request's period over the budget
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_period_over_the_price_day_budget_answers_every_analytic_unavailable_for_resource_limit(private_db, lower_budget):
    """Rule 1: the budget lowered to 30 item-days, June's 31 points do not fit the main preparation. ``RiskService.execute``
    answers: both analytics unavailable, code ``resource_limit``, details exactly ``{"metric": "price_item_days",
    "actual": 31, "limit": 30, "remedy": "period_or_assets"}`` — what to change, a shorter period or fewer assets.

    Today: ``BulkTooManyDaysError(item_days=31, max_item_days=30)`` crosses ``RiskService.execute`` (``/risk/query``: 500).
    """
    asset_id = await _asset_quoted_every_day_of_2024(private_db)
    lower_budget(JUNE_POINTS - 1)

    response = await _execute(private_db, _period_request(asset_id))

    assert _results(response) == {
        "kpi": (UNAVAILABLE, RESOURCE_LIMIT, _refused_for_size(JUNE_POINTS, JUNE_POINTS - 1)),
        "drawdown": (UNAVAILABLE, RESOURCE_LIMIT, _refused_for_size(JUNE_POINTS, JUNE_POINTS - 1)),
    }


# --------------------------------------------------------------------------- #
# Rule 2: a replay window over the budget
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_replay_window_over_the_budget_answers_its_stress_unavailable_and_the_rest_completes(private_db, lower_budget):
    """Rule 2: the budget lowered to 100 item-days, the request's period fits (November–December, 62 points) and the
    replay's window does not (305 points). The replay is unavailable, code ``resource_limit``, details ``{"metric":
    "price_item_days", "actual": 305, "limit": 100, "remedy": "period_or_assets"}``; the KPIs of the same request complete.

    Today: ``BulkTooManyDaysError(item_days=305, max_item_days=100)``, raised by the replay's preparation, crosses
    ``RiskService.execute``: the whole request fails (``/risk/query``: 500), the KPIs with it.
    """
    asset_id = await _asset_quoted_every_day_of_2024(private_db)
    lower_budget(100)
    assert NOVEMBER_DECEMBER_POINTS <= 100 < REPLAY_POINTS  # the numbers of the case: the period fits, the window does not

    response = await _execute(private_db, _replay_request(asset_id))

    assert _results(response) == {
        "replay": (UNAVAILABLE, RESOURCE_LIMIT, _refused_for_size(REPLAY_POINTS, 100)),
        "kpi": (OK, None, None),
    }


# --------------------------------------------------------------------------- #
# Rule 3: GUARD — within the budget
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_kind", "budget"),
    [
        pytest.param("period", None, id="period-budget-untouched"),
        pytest.param("period", JUNE_POINTS, id="period-exactly-at-the-budget"),
        pytest.param("replay", None, id="replay-budget-untouched"),
        pytest.param("replay", REPLAY_POINTS, id="replay-exactly-at-the-budget"),
    ],
)
async def test_guard_within_the_budget_the_request_completes_as_today(private_db, lower_budget, request_kind, budget):
    """GUARD (green today and after): with the budget untouched, or lowered to exactly the points the request builds (the
    budget refuses only more than it), every analytic of both requests completes — status ok, no error.
    """
    asset_id = await _asset_quoted_every_day_of_2024(private_db)
    if budget is not None:
        lower_budget(budget)
    request = _REQUESTS[request_kind](asset_id)

    response = await _execute(private_db, request)

    assert _results(response) == {analytic.instance_id: (OK, None, None) for analytic in request.analytics}

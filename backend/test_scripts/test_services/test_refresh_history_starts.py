"""The first day a source has prices for, in the refresh's outcome (project 76, lot P2b; the consultant's rule).

A source may give no prices before some day: CoinGecko's Demo plan answers the last 365 days only. The user then imports
the days before by hand («Importa prezzi»), and must know FROM WHICH DAY. The contract pinned here:

1. ``FAHistoricalData.history_starts`` (optional, typed): «the source gives no points before this day».
2. The refresh copies it into ``FARefreshResult.history_starts`` **only when the range asked started before it**
   (``"min"`` counts as before); a range inside the source's window gives none, and so does a provider that says none.
3. It is no error: the status is the status of the prices themselves.
4. CoinGecko says it on the Demo plan (today − 364), never on the Pro plan.

Pure: a private SQLite file behind the session; the test-only ``mockprov`` with its history wrapped to say a first day
and give no point before it; no network, no server.
Red on HEAD: no such field.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import IdentifierType
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, ProviderInputType
from backend.app.schemas.prices import FAHistoricalData
from backend.app.schemas.refresh import FARefreshItem, FARefreshResult, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source_providers.coingecko import plugin as coingecko_plugin
from backend.app.services.asset_source_providers.coingecko.plugin import CoinGeckoProvider
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets.refresh import RefreshOperations
from backend.app.services.platform import provider_cooldown
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

TODAY = date.today()
#: The first day the wrapped mock source has prices for.
FIRST_DAY = TODAY - timedelta(days=10)


@pytest.fixture(autouse=True)
def private_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", Cooldowns(60, 3600, jitter=0.0))


@pytest_asyncio.fixture
async def private_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'p2b_history_starts.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(db_session, "async_engine", engine)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def source_from_first_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """mockprov's history, as a source that has no price before ``FIRST_DAY`` and says so."""
    original = MockProvider.get_history_value

    async def wrapped(self, identifier, identifier_type, provider_params, start_date, end_date):
        data = await original(self, identifier, identifier_type, provider_params, start_date, end_date)
        return FAHistoricalData(prices=[point for point in data.prices if point.date >= FIRST_DAY], events=data.events, currency=data.currency, source=data.source, history_starts=FIRST_DAY)

    monkeypatch.setattr(MockProvider, "get_history_value", wrapped)


async def _asset(engine: AsyncEngine) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"P2b asset {uuid.uuid4().hex[:10]}", currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code="mockprov", identifier=f"P2B{uuid.uuid4().hex[:10].upper()}", identifier_type=ProviderInputType.TICKER, provider_params=json.dumps({})))
        await session.commit()
        return asset.id


async def _refresh(engine: AsyncEngine, asset_id: int, start: date | str, end: date = TODAY - timedelta(days=1)) -> FARefreshResult:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await RefreshOperations.bulk_refresh_prices([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=start, end=end))], session)
    (result,) = response.results
    return result


@pytest.mark.asyncio
async def test_p2b_a_range_that_starts_before_the_sources_first_day_says_that_day(private_db: AsyncEngine, source_from_first_day: None):
    print_section("P2b 2: the first day in the outcome")
    result = await _refresh(private_db, await _asset(private_db), TODAY - timedelta(days=20))

    assert result.history_starts == FIRST_DAY
    assert result.status is SyncStatus.OK, "no error: the prices themselves decide the status"
    assert result.points_fetched > 0
    print_success("the first day reported, status OK")


@pytest.mark.asyncio
async def test_p2b_min_counts_as_before(private_db: AsyncEngine, source_from_first_day: None):
    result = await _refresh(private_db, await _asset(private_db), "min")
    assert result.history_starts == FIRST_DAY


@pytest.mark.asyncio
async def test_p2b_a_range_inside_the_window_says_nothing(private_db: AsyncEngine, source_from_first_day: None):
    result = await _refresh(private_db, await _asset(private_db), FIRST_DAY + timedelta(days=2))
    assert result.history_starts is None


@pytest.mark.asyncio
async def test_p2b_a_range_wholly_before_the_first_day_still_says_it(private_db: AsyncEngine, source_from_first_day: None):
    """The case the sentence exists for: nothing comes back, and the outcome says from which day the source has prices."""
    result = await _refresh(private_db, await _asset(private_db), FIRST_DAY - timedelta(days=30), FIRST_DAY - timedelta(days=20))

    assert result.points_fetched == 0
    assert result.history_starts == FIRST_DAY


@pytest.mark.asyncio
async def test_p2b_the_second_refresh_of_the_same_range_says_it_too(private_db: AsyncEngine, source_from_first_day: None):
    """The history cache never answers a start before the source's first day alone: the second refresh asks again."""
    asset_id = await _asset(private_db)
    start = TODAY - timedelta(days=20)
    first = await _refresh(private_db, asset_id, start)
    second = await _refresh(private_db, asset_id, start)

    assert (first.history_starts, second.history_starts) == (FIRST_DAY, FIRST_DAY)


@pytest.mark.asyncio
async def test_p2b_a_provider_that_says_no_first_day_gives_none(private_db: AsyncEngine):
    result = await _refresh(private_db, await _asset(private_db), TODAY - timedelta(days=20))
    assert result.history_starts is None


# =============================================================================
# 4. COINGECKO SAYS IT ON THE DEMO PLAN
# =============================================================================


class _Group:
    def __init__(self, plan: str) -> None:
        self._plan = plan

    def secret(self, name: str) -> str | None:
        return "CG-test-p2b-KEY" if name == "api_key" else None

    def get(self, name: str):
        return self._plan if name == "plan" else None


class _Bound:
    def __init__(self, plan: str) -> None:
        self._group = _Group(plan)

    def group(self, name: str) -> _Group:
        return self._group

    def get(self, key: str):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(("plan", "expected"), [("demo", TODAY - timedelta(days=364)), ("pro", None)])
async def test_p2b_coingecko_says_its_first_day_on_the_demo_plan_only(monkeypatch: pytest.MonkeyPatch, plan: str, expected: date | None):
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound(plan))  # type: ignore[arg-type]
    wire = httpx.MockTransport(lambda request: httpx.Response(200, content=b'{"prices": [], "market_caps": [], "total_volumes": []}', headers={"content-type": "application/json"}))
    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=wire))
    monkeypatch.setattr(coingecko_plugin, "_utc_today", lambda: TODAY)

    history = await provider.get_history_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}, TODAY - timedelta(days=30), TODAY - timedelta(days=1))

    assert history.history_starts == expected


@pytest.mark.asyncio
async def test_p2b_coingecko_demo_asks_nothing_for_a_range_wholly_before_its_year(monkeypatch: pytest.MonkeyPatch):
    """A range that ends before the Demo plan's first day spends no credit, and still says that day."""
    provider = CoinGeckoProvider()
    provider.bind_settings(_Bound("demo"))  # type: ignore[arg-type]
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b'{"prices": [], "market_caps": [], "total_volumes": []}', headers={"content-type": "application/json"})

    monkeypatch.setattr(CoinGeckoProvider, "_http_client", httpx.Client(transport=httpx.MockTransport(answer)))
    monkeypatch.setattr(coingecko_plugin, "_utc_today", lambda: TODAY)

    history = await provider.get_history_value("bitcoin", IdentifierType.TICKER, {"vs_currency": "EUR"}, TODAY - timedelta(days=500), TODAY - timedelta(days=400))

    assert requests == []
    assert history.prices == []
    assert history.history_starts == TODAY - timedelta(days=364)

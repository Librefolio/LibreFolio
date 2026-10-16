"""X-RL X5: the results that tell a caller a provider refused for too many requests, or is paused, and for how long.

Plan 06 of Z, section «Z7 — disegno», contract X5 (and D-Z7-2, D-Z7-3); implementation notes in plan 03, section «X-RL
(X1–X8)», step 4. The contract pinned here:

1. Live current price (``price_query.get_current_prices_bulk``): a refusal, or a pause, keeps the last stored price
   (``source="db:last_known"``) and adds ``error_code="RATE_LIMITED"`` and ``retry_after``; without a stored price the
   item is the error item with the same two fields. While paused, the provider is not called. A provider that answers
   adds neither field.
2. Refresh (``RefreshOperations.bulk_refresh_prices``): the refusal met on the way — history or current value, the
   longest wait winning — decorates the finished result, whatever its status: FAILED when nothing came (nothing
   stored), PARTIAL or OK when part of the data came and was stored.
3. FX sync (``sync_pairs_bulk``): a pair FAILED or PARTIAL whose routes use a provider that refused (or is paused) is
   marked ``RATE_LIMITED`` with the shortest wait among those providers; a pair another route served in full, and a
   pair that failed through no refused provider, stay as they are. A refusal is logged at INFO, not as a traceback.
4. Probe (``probe_provider_config``): every refused or paused operation carries ``retry_after`` on the result and in
   ``error_details``; another failure carries neither.
5. Search: a refused or paused provider is listed in ``providers_with_errors`` and logged at INFO, never as a
   traceback; a query cached before the pause is still answered; the SSE ``provider_error`` event carries
   ``error_code`` (``RATE_LIMITED``) and ``retry_after``. The event of another ``AssetSourceError`` carries that error's
   own ``error_code`` and never ``retry_after``; the event of an error that is no ``AssetSourceError`` carries neither.

In process, never on the shared backend. Each test gets a private ``Cooldowns`` on a fake clock, without jitter, in
place of ``provider_cooldown.PROVIDER_COOLDOWNS``, the two pause variables set with ``monkeypatch``, and — when it needs
a database — a private SQLite file under ``tmp_path`` built with ``create_all``, put in place of the process's engine
(``db.session.async_engine``), so every ``get_async_engine()`` of the services under test (the plugin settings, the
refresh's persist sessions, the FX sync's rate writes) reaches that file and nothing of the lane. No variable of the
mockprov or MOCKFX fields is inherited, and the instance key is a test key, so no key file is read or made. The
refusals come from mockprov's ``mock_rate_limited`` parameter and ``lf-rate-limited`` query, MockFX's class attributes
(set with ``monkeypatch``), and test providers handed out by the registries for codes of their own. Identifiers,
queries and FX date ranges are unique per test, so the process's provider caches never answer for another test.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, FxConversionRoute, PriceHistory, ProviderInputType
from backend.app.schemas.provider import FAProviderConfigBase, ProbeOperation
from backend.app.schemas.refresh import FARefreshItem, FARefreshResult, FXSyncPairResult, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source_providers.mockprov.plugin import RATE_LIMITED_QUERY, MockProvider
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.assets.provider_management import ProviderManagementOperations, _probe_failure_fields
from backend.app.services.assets.refresh import RefreshOperations, _refusal_of, _with_refusal
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService
from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx.sync import _note_provider_failure, _with_fx_refusal, sync_pairs_bulk
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.platform import provider_cooldown
from backend.app.services.plugin_settings.fields import env_name, env_variables
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

START = 1_000_000.0
MOCK_KEY = ("asset", "mockprov", None)
TEST_INSTANCE_KEY = "x-rl-results-test-instance-key-0123456789abcdef"
CURRENT_REFUSED = "xrl_current_refused"
HISTORY_REFUSED = "xrl_history_refused"
ANSWERING_FX, EMPTY_FX, REFUSING_FX = "XRL_OKFX", "XRL_EMPTYFX", "XRL_SLOWFX"


class FakeClock:
    """A clock that moves only when the test moves it."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class _CurrentRefused(MockProvider):
    """mockprov's history; its current value refused for too many requests (Retry-After 240 s). No settings."""

    settings_fields = ()

    @property
    def provider_code(self) -> str:
        return CURRENT_REFUSED

    async def get_current_value(self, identifier, identifier_type, provider_params=None):
        raise AssetRateLimitedError("current value refused for too many requests (testing)", retry_after=240.0)


class _HistoryRefused(MockProvider):
    """mockprov's current value; its history, served by another host, refused for too many requests (Retry-After 180 s)."""

    settings_fields = ()

    @property
    def provider_code(self) -> str:
        return HISTORY_REFUSED

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
        raise AssetRateLimitedError("history refused for too many requests (testing)", retry_after=180.0, scope="history.example")


class _AnsweringFX(MockFXProvider):
    """An FX provider of the test: rate 2 on the first day for every currency asked, whatever MockFX's mode."""

    settings_fields = ()
    rate_limited = False

    @property
    def code(self) -> str:
        return ANSWERING_FX

    async def fetch_rates(self, date_range, currencies, base_currency=None):
        return {currency: [(date_range[0], "EUR", currency, Decimal("2.000000"))] for currency in currencies}


class _EmptyFX(_AnsweringFX):
    """An FX provider of the test that answers no rate at all."""

    @property
    def code(self) -> str:
        return EMPTY_FX

    async def fetch_rates(self, date_range, currencies, base_currency=None):
        return {currency: [] for currency in currencies}


class _RefusingFX(_AnsweringFX):
    """An FX provider of the test that refuses for too many requests (Retry-After 120 s)."""

    @property
    def code(self) -> str:
        return REFUSING_FX

    async def fetch_rates(self, date_range, currencies, base_currency=None):
        raise FXRateLimitedError("XRL_SLOWFX refused for too many requests (testing)", retry_after=120.0)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pauses on (60 s, an hour at most); no ambient variable of the mockprov or MOCKFX fields; a test instance key."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    declared = [("asset", "mockprov", field) for field in MockProvider.settings_fields] + [("fx", "MOCKFX", field) for field in MockFXProvider.settings_fields]
    for family, code, field in declared:
        for name in {*env_variables(family, code, field), env_name(family, code, field.key)}:
            monkeypatch.delenv(name, raising=False)
            monkeypatch.delenv(name + "_FILE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def cooldowns(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> Cooldowns:
    """A private instance on the fake clock, without jitter, in place of the process's."""
    private = Cooldowns(60, 3600, jitter=0.0, clock=clock)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


@pytest_asyncio.fixture
async def private_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole schema, as the process's engine for the test; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'x_rl_results.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(db_session, "async_engine", engine)
        yield engine
    finally:
        await engine.dispose()


def _state(cooldowns: Cooldowns) -> dict:
    return {state.key: (state.refusals, state.remaining) for state in cooldowns.snapshot()}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _count(monkeypatch: pytest.MonkeyPatch, cls: type, name: str) -> list:
    """Count the calls of the async method ``cls.name`` (its first argument each), still running it."""
    calls: list = []
    original = getattr(cls, name)

    async def counted(self, *args, **kwargs):
        calls.append(args[0] if args else None)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(cls, name, counted)
    return calls


def _hand_out(monkeypatch: pytest.MonkeyPatch, registry: type, doubles: dict[str, type]) -> None:
    """``registry`` hands out a new instance of ``doubles[code]`` for those codes, and its own providers otherwise."""
    original = registry.get_provider_instance

    def get_provider_instance(_cls, code, **kwargs):
        double = doubles.get(code)
        return double() if double is not None else original(code, **kwargs)

    monkeypatch.setattr(registry, "get_provider_instance", classmethod(get_provider_instance))


async def _asset(engine: AsyncEngine, *, provider_code: str = "mockprov", params: dict | None = None, last_price: tuple[date, Decimal] | None = None) -> int:
    """A USD asset of this test, with its provider assignment and, optionally, one stored price."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("X-RL asset"), currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=provider_code, identifier=_unique("XRL"), identifier_type=ProviderInputType.TICKER, provider_params=json.dumps(params or {})))
        if last_price is not None:
            day, close = last_price
            session.add(PriceHistory(asset_id=asset.id, date=day, close=close, currency="USD", source_plugin_key="test"))
        await session.commit()
        return asset.id


async def _stored_days(engine: AsyncEngine, asset_id: int) -> list[date]:
    async with AsyncSession(engine) as session:
        rows = await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date))
        return list(rows.scalars())


async def _current_prices(engine: AsyncEngine, asset_ids: list[int]) -> list:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await PriceQueryOperations.get_current_prices_bulk(asset_ids, session)


async def _refresh(engine: AsyncEngine, asset_id: int, start: date, end: date) -> FARefreshResult:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await RefreshOperations.bulk_refresh_prices([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=start, end=end))], session)
    (result,) = response.results
    return result


async def _routes(engine: AsyncEngine, routes: dict[tuple[str, str], list[list[str]]]) -> None:
    """One route per provider list, in priority order; each route a single step base → quote."""
    async with AsyncSession(engine) as session:
        for (base, quote), chains in routes.items():
            for priority, providers in enumerate(chains, start=1):
                steps = [{"from": base, "to": quote, "provider": provider} for provider in providers]
                session.add(FxConversionRoute(base=base, quote=quote, priority=priority, chain_steps=json.dumps(steps)))
        await session.commit()


async def _sync(engine: AsyncEngine, pairs: list[str], date_range: tuple[date, date]) -> dict[str, FXSyncPairResult]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await sync_pairs_bulk(session, pairs, date_range)
    return {result.pair: result for result in response.results}


async def _sse(stream) -> list[dict]:
    """The events of an SSE stream, decoded."""
    events = []
    async for chunk in stream:
        assert chunk.startswith("data: ") and chunk.endswith("\n\n"), chunk
        events.append(json.loads(chunk[len("data: ") :]))
    return events


# =============================================================================
# 1. Live current price
# =============================================================================


@pytest.mark.asyncio
async def test_a_refused_live_price_keeps_the_last_stored_price_and_says_why(private_db: AsyncEngine, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """XRL-R01 — contract 1: mockprov refuses (Retry-After 90): the stored 42.5 of 2 January, ``db:last_known``, RATE_LIMITED, 90 s."""
    print_section("XRL-R01: live price refused, last known price kept")
    calls = _count(monkeypatch, MockProvider, "get_current_value")
    asset_id = await _asset(private_db, params={"mock_rate_limited": 90}, last_price=(date(2026, 1, 2), Decimal("42.5")))

    (item,) = await _current_prices(private_db, [asset_id])

    assert (item.asset_id, item.value, item.currency, item.as_of_date, item.source) == (asset_id, Decimal("42.5"), "USD", date(2026, 1, 2), "db:last_known")
    assert (item.error, item.error_code, item.retry_after) == (None, "RATE_LIMITED", 90.0)
    assert len(calls) == 1
    assert _state(cooldowns) == {MOCK_KEY: (1, 90.0)}
    print_success("last known price, RATE_LIMITED, 90 s")


@pytest.mark.asyncio
async def test_while_paused_a_live_price_without_a_stored_one_is_the_error_item_with_the_wait(private_db: AsyncEngine, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """XRL-R02 — contract 1: after the refusal, another asset of the same provider, 30 s later: no call, no price, RATE_LIMITED, 60 s left."""
    calls = _count(monkeypatch, MockProvider, "get_current_value")
    refused_id = await _asset(private_db, params={"mock_rate_limited": 90})
    paused_id = await _asset(private_db)
    await _current_prices(private_db, [refused_id])
    clock.now += 30

    (item,) = await _current_prices(private_db, [paused_id])

    assert (item.asset_id, item.value, item.source) == (paused_id, None, None)
    assert item.error, "the error item says there is no price"
    assert (item.error_code, item.retry_after) == ("RATE_LIMITED", 60.0)
    assert len(calls) == 1, "the paused provider was not called for the second asset"


@pytest.mark.asyncio
async def test_a_live_price_the_provider_answers_has_no_refusal_fields(private_db: AsyncEngine):
    """XRL-R03 — contract 1, the control: mockprov answers its 100 USD: the provider's price, neither field."""
    asset_id = await _asset(private_db, last_price=(date(2026, 1, 2), Decimal("42.5")))

    (item,) = await _current_prices(private_db, [asset_id])

    assert (item.value, item.source) == (Decimal("100.00"), "provider:mockprov")
    assert (item.error_code, item.retry_after) == (None, None)


# =============================================================================
# 2. Refresh
# =============================================================================


@pytest.mark.asyncio
async def test_a_refused_refresh_fails_with_the_refusal_and_stores_nothing(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    """XRL-R04 — contract 2: the history is refused (90 s) and the current value is then held by the pause: FAILED, RATE_LIMITED, 90 s, no row."""
    print_section("XRL-R04: refresh refused")
    history_calls = _count(monkeypatch, MockProvider, "get_history_value")
    current_calls = _count(monkeypatch, MockProvider, "get_current_value")
    asset_id = await _asset(private_db, params={"mock_rate_limited": 90})
    today = date.today()

    result = await _refresh(private_db, asset_id, today - timedelta(days=5), today)

    assert (result.status, result.error_code, result.retry_after) == (SyncStatus.FAILED, "RATE_LIMITED", 90.0)
    assert result.points_fetched == 0 and result.errors, "a failed item says why"
    assert (len(history_calls), len(current_calls)) == (1, 0)
    assert await _stored_days(private_db, asset_id) == []
    print_success("FAILED with RATE_LIMITED, the current value never asked")


@pytest.mark.asyncio
async def test_a_refresh_whose_history_is_refused_stores_the_current_value_and_is_partial(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns):
    """XRL-R05 — contract 2: the history host refuses (180 s, its own scope), the current value answers: PARTIAL, today's price stored, RATE_LIMITED, 180 s."""
    _hand_out(monkeypatch, AssetProviderRegistry, {HISTORY_REFUSED: _HistoryRefused})
    asset_id = await _asset(private_db, provider_code=HISTORY_REFUSED)
    today = date.today()

    result = await _refresh(private_db, asset_id, today - timedelta(days=5), today)

    assert (result.status, result.points_fetched, result.error_code, result.retry_after) == (SyncStatus.PARTIAL, 1, "RATE_LIMITED", 180.0)
    assert await _stored_days(private_db, asset_id) == [today]
    assert _state(cooldowns) == {("asset", HISTORY_REFUSED, "history.example"): (1, 180.0)}


@pytest.mark.asyncio
async def test_a_refresh_whose_current_value_is_refused_stores_the_history_with_the_refusal(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    """XRL-R06 — contract 2: the history answers five days, the current value is refused (240 s): the five days stored, the result RATE_LIMITED, 240 s."""
    _hand_out(monkeypatch, AssetProviderRegistry, {CURRENT_REFUSED: _CurrentRefused})
    asset_id = await _asset(private_db, provider_code=CURRENT_REFUSED)
    today = date.today()

    result = await _refresh(private_db, asset_id, today - timedelta(days=5), today)

    assert (result.status, result.points_fetched, result.error_code, result.retry_after) == (SyncStatus.OK, 5, "RATE_LIMITED", 240.0)
    assert await _stored_days(private_db, asset_id) == [today - timedelta(days=offset) for offset in range(5, 0, -1)]


@pytest.mark.asyncio
async def test_a_refresh_the_provider_answers_has_no_refusal_fields(private_db: AsyncEngine):
    """XRL-R07 — contract 2, the control: mockprov answers history and current value: OK, neither field."""
    asset_id = await _asset(private_db)
    today = date.today()

    result = await _refresh(private_db, asset_id, today - timedelta(days=3), today)

    assert result.status == SyncStatus.OK
    assert (result.error_code, result.retry_after) == (None, None)


def test_the_refusal_reported_is_the_one_with_the_longest_wait():
    """XRL-R08 — contract 2: ``_refusal_of`` keeps the longest wait met (no wait counts as none), and ignores other errors."""
    short, long_wait, untimed = AssetRateLimitedError("a", retry_after=30.0), AssetRateLimitedError("b", retry_after=90.0), AssetRateLimitedError("c")

    assert _refusal_of(short, None) is short
    assert _refusal_of(long_wait, short) is long_wait
    assert _refusal_of(short, long_wait) is long_wait
    assert _refusal_of(untimed, short) is short
    assert _refusal_of(AssetSourceError("gone", "NOT_FOUND"), short) is short
    assert _refusal_of(ValueError("boom"), None) is None


@pytest.mark.parametrize("status", [SyncStatus.FAILED, SyncStatus.PARTIAL, SyncStatus.OK])
def test_a_finished_refresh_result_is_decorated_whatever_its_status(status: SyncStatus):
    """XRL-R09 — contract 2: ``_with_refusal`` adds the code and the wait and changes nothing else; no refusal, the very result."""
    result = FARefreshResult(asset_id=7, status=status, points_fetched=3, errors=["kept"])

    decorated = _with_refusal(result, AssetRateLimitedError("refused", retry_after=45.0))

    assert decorated.model_dump(exclude={"error_code", "retry_after"}) == result.model_dump(exclude={"error_code", "retry_after"})
    assert (decorated.error_code, decorated.retry_after) == ("RATE_LIMITED", 45.0)
    assert _with_refusal(result, None) is result


# =============================================================================
# 3. FX sync
# =============================================================================


@pytest.mark.asyncio
async def test_fx_sync_marks_the_pairs_a_refused_provider_left_failed_or_partial(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    """XRL-R10 — contract 3: MockFX refuses (300 s), XRL_SLOWFX refuses (120 s); five pairs, five outcomes."""
    print_section("XRL-R10: FX sync pair results")
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", 300.0)
    _hand_out(monkeypatch, FXProviderRegistry, {ANSWERING_FX: _AnsweringFX, EMPTY_FX: _EmptyFX, REFUSING_FX: _RefusingFX})
    await _routes(
        private_db,
        {
            ("EUR", "USD"): [["MOCKFX"]],
            ("EUR", "GBP"): [["MOCKFX"], [ANSWERING_FX]],
            ("EUR", "JPY"): [["MOCKFX"], [EMPTY_FX]],
            ("EUR", "SEK"): [["MOCKFX"], [REFUSING_FX]],
            ("EUR", "NOK"): [["MOCKFX_FAIL"]],
        },
    )

    with capture_logs() as events:
        results = await _sync(private_db, ["EUR-USD", "EUR-GBP", "EUR-JPY", "EUR-SEK", "EUR-NOK"], (date(1987, 6, 1), date(1987, 6, 3)))

    assert {pair: (result.status, result.error_code, result.retry_after) for pair, result in results.items()} == {
        "EUR-USD": (SyncStatus.FAILED, "RATE_LIMITED", 300.0),
        "EUR-GBP": (SyncStatus.OK, None, None),
        "EUR-JPY": (SyncStatus.PARTIAL, "RATE_LIMITED", 300.0),
        "EUR-SEK": (SyncStatus.FAILED, "RATE_LIMITED", 120.0),
        "EUR-NOK": (SyncStatus.FAILED, None, None),
    }
    assert results["EUR-GBP"].provider_used == ANSWERING_FX, "barrier: the pair left untouched was served by its fallback route"
    refusals_logged = {(event.get("provider"), event.get("retry_after")) for event in events if event.get("log_level") == "info" and "retry_after" in event and event.get("provider") in ("MOCKFX", REFUSING_FX)}
    tracebacks = [str(event.get("event")) for event in events if event.get("exc_info")]
    assert refusals_logged == {("MOCKFX", 300.0), (REFUSING_FX, 120.0)}
    assert tracebacks and all("MOCKFX_FAIL" in text for text in tracebacks), f"barrier and claim: only the plain failure leaves a traceback: {tracebacks}"
    print_success("FAILED/PARTIAL by a refused provider marked; the fallback and the plain failure untouched")


@pytest.mark.asyncio
async def test_while_mockfx_is_paused_the_sync_asks_it_nothing_and_says_how_long(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch, clock: FakeClock):
    """XRL-R11 — contract 3: a second sync 100 s after the refusal, MockFX answering again: not called, the pair FAILED with 200 s left."""
    fetches = _count(monkeypatch, MockFXProvider, "fetch_rates")
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", 300.0)
    await _routes(private_db, {("EUR", "USD"): [["MOCKFX"]]})
    first = await _sync(private_db, ["EUR-USD"], (date(1987, 7, 1), date(1987, 7, 2)))
    monkeypatch.setattr(MockFXProvider, "rate_limited", False)
    clock.now += 100

    second = await _sync(private_db, ["EUR-USD"], (date(1987, 7, 6), date(1987, 7, 7)))

    assert (first["EUR-USD"].error_code, first["EUR-USD"].retry_after) == ("RATE_LIMITED", 300.0)
    assert (second["EUR-USD"].status, second["EUR-USD"].error_code, second["EUR-USD"].retry_after) == (SyncStatus.FAILED, "RATE_LIMITED", 200.0)
    assert len(fetches) == 1, "the paused provider was asked once, before its pause"


def _route_of(*providers: str) -> SimpleNamespace:
    """A route as ``_with_fx_refusal`` reads it: its steps' providers."""
    return SimpleNamespace(parsed_steps=[{"from": "EUR", "to": "USD", "provider": provider} for provider in providers])


def test_with_fx_refusal_reads_the_routes_and_keeps_the_shortest_known_wait():
    """XRL-R12 — contract 3: only FAILED and PARTIAL, only through a refused provider of its routes (any case), the shortest known wait."""
    failed, partial, ok = (FXSyncPairResult(pair="EUR-USD", status=status) for status in (SyncStatus.FAILED, SyncStatus.PARTIAL, SyncStatus.OK))
    refusals = {"MOCKFX": 300.0, "ECB": 90.0, "FED": None}

    assert _with_fx_refusal(ok, [_route_of("MOCKFX")], refusals) is ok
    assert _with_fx_refusal(failed, [_route_of("BOE")], refusals) is failed
    assert _with_fx_refusal(failed, [_route_of("MOCKFX")], {}) is failed
    marked = _with_fx_refusal(partial, [_route_of("mockfx"), _route_of("ECB", "BOE")], refusals)
    assert (marked.status, marked.error_code, marked.retry_after) == (SyncStatus.PARTIAL, "RATE_LIMITED", 90.0)
    untimed = _with_fx_refusal(failed, [_route_of("FED")], refusals)
    assert (untimed.error_code, untimed.retry_after) == ("RATE_LIMITED", None)
    mixed = _with_fx_refusal(failed, [_route_of("FED"), _route_of("MOCKFX")], refusals)
    assert (mixed.error_code, mixed.retry_after) == ("RATE_LIMITED", 300.0)


def test_note_provider_failure_records_a_refusal_at_info_and_logs_any_other_failure():
    """XRL-R13 — contract 3: the refusal's wait under the code in capitals, an INFO line; another error recorded nowhere, logged as an error."""
    refusals: dict[str, float | None] = {}

    with capture_logs() as events:
        _note_provider_failure("mockfx", FXRateLimitedError("refused", retry_after=12.0), refusals)
        _note_provider_failure("ECB", FXServiceError("ECB API error"), refusals)

    assert refusals == {"MOCKFX": 12.0}
    assert [(event.get("log_level"), event.get("provider"), event.get("retry_after")) for event in events if event.get("log_level") == "info"] == [("info", "mockfx", 12.0)]
    assert [(event.get("log_level"), bool(event.get("exc_info"))) for event in events if "ECB" in str(event.get("event"))] == [("error", True)]


# =============================================================================
# 4. Probe
# =============================================================================


@pytest.mark.asyncio
async def test_a_refused_probe_carries_the_wait_on_every_operation(private_db: AsyncEngine, clock: FakeClock, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """XRL-R14 — contract 4: refused (Retry-After 45 → a 60 s pause), then paused 15 s later: the wait on the result and in ``error_details``."""
    print_section("XRL-R14: probe")
    identifier = _unique("XRL")
    refused = await ProviderManagementOperations.probe_provider_config(FAProviderConfigBase(provider_code="mockprov", identifier=identifier, identifier_type="TICKER", provider_params={"mock_rate_limited": 45}), list(ProbeOperation))
    clock.now += 15
    calls = {name: _count(monkeypatch, MockProvider, name) for name in ("get_current_value", "get_history_value", "fetch_asset_metadata")}

    paused = await ProviderManagementOperations.probe_provider_config(FAProviderConfigBase(provider_code="mockprov", identifier=identifier, identifier_type="TICKER", provider_params={}), list(ProbeOperation))

    for response, wait in ((refused, 60.0), (paused, 45.0)):
        operations = {"current_price": response.current_price, "history": response.history, "metadata": response.metadata}
        assert {name: (op.success, op.error_code, op.retry_after, op.error_details) for name, op in operations.items()} == dict.fromkeys(operations, (False, "RATE_LIMITED", wait, {"retry_after": wait}))
    assert {name: len(made) for name, made in calls.items()} == dict.fromkeys(calls, 0), "the paused probe reached no operation of the provider"
    assert _state(cooldowns) == {MOCK_KEY: (1, 45.0)}
    print_success("60 s, then 45 s left, on the result and in error_details")


@pytest.mark.asyncio
async def test_a_probe_failing_otherwise_carries_no_wait(private_db: AsyncEngine):
    """XRL-R15 — contract 4, the control: NOT_FOUND from the current value — no ``retry_after``, no details."""
    response = await ProviderManagementOperations.probe_provider_config(FAProviderConfigBase(provider_code="mockprov", identifier="INVALID_TICKER_12345", identifier_type="TICKER", provider_params={}), [ProbeOperation.CURRENT_PRICE])

    op = response.current_price
    assert (op.success, op.error_code, op.retry_after, op.error_details) == (False, "NOT_FOUND", None, None)


def test_probe_failure_fields_put_the_wait_beside_the_details():
    """XRL-R16 — contract 4: the wait goes on the result and joins the JSON-safe details; without a wait, nothing is added."""
    timed = AssetRateLimitedError("paused", retry_after=30.0, details={"day": date(2026, 1, 2)})

    assert _probe_failure_fields(timed) == {"error": "paused", "error_code": "RATE_LIMITED", "error_details": {"day": "2026-01-02", "retry_after": 30.0}, "retry_after": 30.0}
    assert _probe_failure_fields(AssetRateLimitedError("paused")) == {"error": "paused", "error_code": "RATE_LIMITED", "error_details": None, "retry_after": None}
    assert _probe_failure_fields(AssetSourceError("gone", "NOT_FOUND", {"identifier": "X"})) == {"error": "gone", "error_code": "NOT_FOUND", "error_details": {"identifier": "X"}, "retry_after": None}
    assert _probe_failure_fields(RuntimeError("boom")) == {"error": "boom", "error_code": None, "error_details": None, "retry_after": None}


# =============================================================================
# 5. Search
# =============================================================================


@pytest.mark.asyncio
async def test_a_refused_search_lists_the_provider_with_errors_and_logs_no_traceback(private_db: AsyncEngine, cooldowns: Cooldowns):
    """XRL-R17 — contract 5: ``lf-rate-limited`` (Retry-After 30 → a 60 s pause): no result, the provider in ``providers_with_errors``, one INFO line, no error line."""
    with capture_logs() as events:
        response = await AssetSearchService.search(RATE_LIMITED_QUERY, provider_codes=["mockprov"])

    assert (response.providers_queried, response.providers_with_errors, response.results) == (["mockprov"], ["mockprov"], [])
    assert _state(cooldowns) == {MOCK_KEY: (1, 60.0)}
    paused_lines = [event for event in events if event.get("log_level") == "info" and event.get("provider") == "mockprov" and event.get("retry_after") == 60.0]
    assert len(paused_lines) == 1, f"barrier: the INFO line of the pause: {events}"
    assert [event for event in events if event.get("log_level") == "error" or event.get("exc_info")] == []


@pytest.mark.asyncio
async def test_a_cached_search_still_answers_during_the_pause_and_a_new_one_reaches_no_provider(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    """XRL-R18 — contract 5: the caches stand before the boundary: a query answered before the pause is answered again; a new one is refused without a call."""
    searches = _count(monkeypatch, MockProvider, "search")
    known, new = _unique("xrl-known"), _unique("xrl-new")
    before = await AssetSearchService.search(known, provider_codes=["mockprov"])
    await AssetSearchService.search(RATE_LIMITED_QUERY, provider_codes=["mockprov"])

    again = await AssetSearchService.search(known, provider_codes=["mockprov"])
    refused = await AssetSearchService.search(new, provider_codes=["mockprov"])

    assert before.providers_with_errors == [] and before.results, "barrier: the provider answered the first query"
    assert (again.providers_with_errors, [item.identifier for item in again.results]) == ([], [item.identifier for item in before.results])
    assert (refused.providers_with_errors, refused.results) == (["mockprov"], [])
    assert searches == [known, RATE_LIMITED_QUERY]


@pytest.mark.asyncio
async def test_the_search_stream_error_event_carries_the_code_and_the_wait(private_db: AsyncEngine, clock: FakeClock):
    """XRL-R19 — contract 5: the ``provider_error`` event of a refusal, then of the pause 20 s later, with ``error_code`` and ``retry_after``; ``done`` lists the provider."""
    with capture_logs() as events:
        refused = await _sse(AssetSearchService.search_stream(RATE_LIMITED_QUERY, provider_codes=["mockprov"]))
    clock.now += 20
    paused = await _sse(AssetSearchService.search_stream(_unique("xrl-paused"), provider_codes=["mockprov"]))

    for stream, wait in ((refused, 60.0), (paused, 40.0)):
        (error,) = [event for event in stream if event["event"] == "provider_error"]
        (done,) = [event for event in stream if event["event"] == "done"]
        assert error.keys() == {"event", "provider_code", "error", "error_code", "retry_after"}
        assert (error["provider_code"], error["error_code"], error["retry_after"]) == ("mockprov", "RATE_LIMITED", wait)
        assert error["error"], "the raw message stays"
        assert (done["providers_queried"], done["providers_with_errors"], done["total_results"]) == (["mockprov"], ["mockprov"], 0)
    assert [(event.get("provider"), event.get("retry_after")) for event in events if event.get("log_level") == "info" and "retry_after" in event and "domain" not in event] == [("mockprov", 60.0)]


@pytest.mark.asyncio
async def test_the_search_stream_event_of_another_error_carries_no_refusal_fields(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch):
    """XRL-R20 — contract 5, the control: a search that fails otherwise: the event has its message, and neither field."""

    async def broken(self, query):
        raise RuntimeError("the search backend is down")

    monkeypatch.setattr(MockProvider, "search", broken)

    events = await _sse(AssetSearchService.search_stream(_unique("xrl-broken"), provider_codes=["mockprov"]))

    (error,) = [event for event in events if event["event"] == "provider_error"]
    assert error.keys() == {"event", "provider_code", "error"}
    assert error["provider_code"] == "mockprov"


@pytest.mark.asyncio
async def test_the_search_stream_event_of_another_provider_error_keeps_its_own_code(private_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns):
    """XRL-R21 — contract 5 (decision N7): a search failing with an ``AssetSourceError`` of its own code: the event
    carries that ``error_code`` beside its message, never ``retry_after``; no pause follows."""

    async def down(self, query):
        raise AssetSourceError("the search backend is down (testing)", "SEARCH_ERROR")

    monkeypatch.setattr(MockProvider, "search", down)

    events = await _sse(AssetSearchService.search_stream(_unique("xrl-search-error"), provider_codes=["mockprov"]))

    (error,) = [event for event in events if event["event"] == "provider_error"]
    (done,) = [event for event in events if event["event"] == "done"]
    assert error.keys() == {"event", "provider_code", "error", "error_code"}
    assert (error["provider_code"], error["error_code"]) == ("mockprov", "SEARCH_ERROR")
    assert error["error"], "the raw message stays"
    assert (done["providers_queried"], done["providers_with_errors"]) == (["mockprov"], ["mockprov"])
    assert _state(cooldowns) == {}, "an error of the provider's own is no refusal: no pause"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

# ruff: noqa: PLC0415 — the new names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""The enrichers active on the instance (plan 68, lot B2, «Arricchitori attivi sull'istanza»).

The contract pinned here:

1. **``LIBREFOLIO_ENRICHERS_ENABLED``**, the twin of X1's ``LIBREFOLIO_ASSET_PROVIDERS_ENABLED``: read by
   ``enrichers_enabled()`` in ``config/plugins.py`` through ``_provider_codes`` (comma-separated, stripped, lowercased,
   in order, each once; None unset, blank or only commas), at every call. ``EnricherRegistry`` overrides
   ``_enabled_codes()`` → ``enrichers_enabled()`` and ``_enabled_variable()`` → the variable's name, so X1's gate of
   ``AbstractPluginRegistry`` applies: a code not listed is not found (``get_plugin`` None), not listed
   (``list_plugin_codes``), so absent from ``installed_enrichers()``, ``enrichers_catalogue()`` (its enrichers and every
   ``default_order``), ``default_order(type)``, and never asked by ``recognize_cascade(..., plugins=None)``. A listed
   code no enricher has is ignored and logged once (warning, keys ``variable`` and ``codes``).
2. **No clean-up.** An asset bound to a turned-off enricher keeps its binding (``config``) and its ``state``; the read
   skips it as a plugin not installed (``refresh_assets``); nothing is written for it; the weekly job's item of that
   asset stays «ok» (``joblog._profile_read_item``). A PATCH keeps a turned-off code in ``config``.
3. **The read cache never outlives the switch.** ``read_bindings`` looks the plugin up before the cache: a turned-off,
   or no longer installed, enricher answers ``NO_ANSWER`` (``_unanswered``) even with a warm cache; ``source_value``
   says it is not an installed enricher.
4. **A required setting left empty → the enricher is not used** (76's N1 boundary rule, ``configure_instance`` +
   ``BoundSettings.missing``). ``refresh_assets`` skips a not-configured enricher like a turned-off one;
   ``read_bindings`` binds each served enricher's settings (``configure_instance(instance, "enricher",
   plugin_code=code)``) before reading, and a not-configured one answers each request ``ERROR`` / ``NOT_CONFIGURED``
   (no cache, no plugin call); the API's cascade (``_recognize_events``) does not ask it; ``test_enricher`` and
   ``search_enricher`` answer the app's coded 422 for it (section 7) and 404, as for an unknown code, for a turned-off
   one. Positive control: with the required value set (its environment variable), the same enricher is used.

Lot B2b (small corrections, consultant and coordinator):

5. **Voices hand over.** A switched-off or not-configured enricher is absent like a source that is down: with ``{A, B}``
   bound (A first) and A «now», switching A off writes nothing by itself; the next ``refresh_assets`` makes B's value
   «now» (one row, source B), A's rows stay, the ``config`` (A then B) is unchanged; A back on, the next read makes A
   «now» again, a row only where the value differs from now. Guards (green on HEAD, see each docstring).
6. **One log line per refresh call** naming the bound enrichers it skipped (not served or not configured): one event for
   the whole call, its ``enrichers`` field the codes sorted and unique; none when nothing is skipped.
7. **The not-configured refusal is the app's coded 422.** ``backend/app/api/plugin_errors.py``
   ``not_configured_error(plugin_code, missing) -> HTTPException``: 422, ``detail == {"error_code": "NOT_CONFIGURED",
   "message": <names the plugin and each missing key>, "missing": [<keys, as given>]}``. The test and search routes
   raise it with ``plugins_readiness(...).missing`` (what a caller may be told: in the managed profile a field an
   environment variable locks is left out).

B2b, red on HEAD 3e720ad61: ``api/plugin_errors.py`` does not exist, the test and search routes answer 400 with two
keys (and, in the managed profile, name a field a variable locks), and ``refresh_assets`` logs no line naming what it
skipped; sections 5 and the «no line» case are guards.

Red on HEAD 786d541e8: ``enrichers_enabled`` and the registry override do not exist, the read cache is looked up before
the plugin, and nothing binds an enricher's settings. Every test imports a missing name in its body or reaches the
missing behaviour through an existing name, so each fails for its own reason, never at collection. Every assertion that
only proves the scenario is set up says ``barrier:``. Guards already green are named in their docstring.

Pure: no lane DB, no server, no network. Every variable through ``monkeypatch``; a private SQLite file under
``tmp_path`` behind every ``get_async_engine`` the paths touch (settings, readiness, refresh); the synthetic enrichers
are ``MockEnricher`` subclasses registered in the process's ``EnricherRegistry`` under unique ``b2_*`` codes and removed
at teardown with their claims; the process-wide ``enricher_read`` cache is cleared around each test. The real
``justetf`` enricher is installed: its two library calls (``get_etf_overview``, ``load_overview``) are replaced by a stub
that records and raises, so no path can reach justetf.com; where a test needs it «not asked», the recorder is the proof.
The Yahoo enricher (lot C3, code ``yfinance``: STOCK, the ETF family and FUND, ticker only) is guarded the same way once
its module exists: its ``yf`` is an offline stub whose every use records and raises, and yfinance's own ``Ticker``,
``Tickers``, ``Search`` and ``download`` do the same. No test here may ask Yahoo (every cascade holds an ISIN, every
binding is another code's), so a recorded call fails the test at teardown; before C3 the module is absent and only the
library stubs stand (``test_b2_yahoo_is_guarded_offline`` is the witness, red until C3).
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import json
import threading
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
import yfinance
import yfinance.exceptions
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, User
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.assets.enrichers import FAEnricherBinding, FAEnricherRecognizeRequest, FAEnricherTestRequest
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.assets.profile.store import current_rows
from backend.app.services.enricher_providers.mockenrich.plugin import READ_VALUES, MockEnricher
from backend.app.services.enrichers import bindings, recognize, refresh
from backend.app.services.enrichers.base import EnricherBinding, EnricherReadStatus, EnricherSearchResult
from backend.app.services.enrichers.bindings import default_order, enrichers_catalogue, installed_enrichers
from backend.app.services.enrichers.recognize import Recognized, recognize_cascade
from backend.app.services.enrichers.refresh import AssetRefreshResult, ReadOutcome, SourceValue, ask_profile, refresh_assets, source_value
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.platform import provider_registry
from backend.app.services.platform.scheduler.joblog import _profile_read_item
from backend.app.services.plugin_settings import readiness, runtime
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name, release_env_variables
from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness
from backend.app.utils.runtime.cache import clear_cache

VARIABLE = "LIBREFOLIO_ENRICHERS_ENABLED"
FAMILY = "enricher"
CACHE_NAME = "enricher_read"
INSTANCE_KEY = "LibreFolio-enrichers-enabled-test-key-0123456789"
LOG_CANARY = "enrichers enabled test: the capture reaches the registry's logger"
CODE_PREFIX = "b2_"
CLASS_PREFIX = "B2Enricher_"
#: The bound on every read, refresh and stream: against a hang, never a wait.
DEADLINE = 15.0
NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
LATER = NOW + timedelta(days=1)
#: The required field of the keyed enricher: plain text (no secret, so no crypto and no minimum length), the instance's.
KEY = "api_key"
KEY_VALUE = "b2-configured-value"
KEY_FIELD = PluginSettingField(key=KEY, type=SettingType.STRING, scope=SettingScope.SYSTEM, label="API key (b2 test)", required=True)
#: The voices every read of a MockEnricher subclass writes for an ETF (its fixed values plus its description).
MOCK_VOICES = {*READ_VALUES, "description"}
USER = SimpleNamespace(id=9_268)


def _ident(tag: str) -> str:
    """An ISIN-shaped identifier no other test (and no other run within the cache's TTL) uses."""
    return f"B2{tag}{uuid.uuid4().hex[:10].upper()}"


def _entry(identifier: str) -> dict[str, str]:
    """A binding as ``asset_enrichers.config`` stores it."""
    return {"identifier_type": "ISIN", "identifier": identifier}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def b2_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode (``mockenrich`` is test-only), a data directory and an instance key of this test, no allow-list
    inherited; the once-only report of unknown codes and the read cache start over."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", INSTANCE_KEY)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)
    monkeypatch.delenv(VARIABLE, raising=False)
    provider_registry._report_unknown_enabled.cache_clear()
    clear_cache(CACHE_NAME)
    yield
    provider_registry._report_unknown_enabled.cache_clear()
    clear_cache(CACHE_NAME)


@dataclass
class NetworkGuard:
    """Every call that would have reached justetf.com, as ``(function, argument)``."""

    calls: list[tuple[str, Any]] = field(default_factory=list)


@pytest.fixture(autouse=True)
def justetf_offline(monkeypatch: pytest.MonkeyPatch) -> NetworkGuard:
    """The real ``justetf`` enricher never reaches its site: both library calls record and raise."""
    EnricherRegistry.auto_discover()
    from backend.app.services.enricher_providers.justetf import plugin as justetf_plugin

    guard = NetworkGuard()
    lock = threading.Lock()

    def stub(name: str) -> Callable[..., Any]:
        def call(*args: Any, **_kwargs: Any) -> Any:
            with lock:
                guard.calls.append((name, args[0] if args else None))
            raise ConnectionError(f"b2 test: justetf.{name} must never reach the network")

        return call

    monkeypatch.setattr(justetf_plugin, "get_etf_overview", stub("get_etf_overview"))
    monkeypatch.setattr(justetf_plugin, "load_overview", stub("load_overview"))
    return guard


#: The Yahoo enricher's module (lot C3): absent before it, guarded once it exists.
YAHOO_PLUGIN = "backend.app.services.enricher_providers.yahoo_finance.plugin"


@dataclass
class YahooGuard:
    """Every use of yfinance that would have reached Yahoo, as ``(what, argument)``; ``installed`` once the enricher's
    module exists and its ``yf`` is the offline stub."""

    calls: list[tuple[str, Any]] = field(default_factory=list)
    installed: bool = False


class _YahooOffline:
    """The Yahoo enricher's ``yf``: ``Ticker(symbol)`` gives a ticker whose every attribute records and raises; any other
    attribute of the module records and raises; ``exceptions`` is yfinance's own."""

    exceptions = yfinance.exceptions

    def __init__(self, guard: YahooGuard, lock: threading.Lock) -> None:
        self._guard, self._lock = guard, lock

    def _refuse(self, what: str, argument: Any) -> ConnectionError:
        with self._lock:
            self._guard.calls.append((what, argument))
        return ConnectionError(f"b2 test: Yahoo ({what}) must never be reached here")

    def Ticker(self, symbol: Any, *_args: Any, **_kwargs: Any) -> Any:  # noqa: N802 — yfinance's own name
        offline = self

        class _Ticker:
            def __getattr__(self, name: str) -> Any:
                if name.startswith("__"):
                    raise AttributeError(name)
                raise offline._refuse(f"Ticker.{name}", symbol)

        return _Ticker()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        raise self._refuse(f"yf.{name}", None)


@pytest.fixture(autouse=True)
def yahoo_offline(monkeypatch: pytest.MonkeyPatch) -> Iterator[YahooGuard]:
    """The Yahoo enricher never reaches its site: its ``yf`` (once the module exists) and yfinance's own entry points
    record and raise. Nothing here may ask Yahoo: a recorded call fails the test at teardown."""
    EnricherRegistry.auto_discover()
    guard = YahooGuard()
    lock = threading.Lock()
    offline = _YahooOffline(guard, lock)

    def stub(name: str) -> Callable[..., Any]:
        def call(*args: Any, **_kwargs: Any) -> Any:
            raise offline._refuse(f"yfinance.{name}", args[0] if args else None)

        return call

    for name in ("Ticker", "Tickers", "Search", "download"):
        monkeypatch.setattr(yfinance, name, stub(name), raising=True)
    try:
        module = importlib.import_module(YAHOO_PLUGIN)
    except ModuleNotFoundError as error:
        # Before C3 the package (or its plugin) does not exist: only the library stubs above stand
        if error.name not in {YAHOO_PLUGIN, YAHOO_PLUGIN.rsplit(".", 1)[0]}:
            raise
    else:
        monkeypatch.setattr(module, "yf", offline, raising=True)
        guard.installed = True
    yield guard
    assert guard.calls == [], f"b2 test: Yahoo was asked, which no test here may do (an ISIN cascade, other codes' bindings): {guard.calls}"


@pytest_asyncio.fixture(autouse=True)
async def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema, behind every ``get_async_engine`` the paths under test open a
    session with (settings binding, readiness, the background refresh)."""
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'enricher_enabled.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        for module in (runtime, readiness, refresh):
            monkeypatch.setattr(module, "get_async_engine", lambda: private)
        yield private
    finally:
        await private.dispose()


@dataclass
class Fake:
    """A registered ``MockEnricher`` subclass: its code, and every call it answered (from worker threads)."""

    code: str
    reads: list[tuple[list[str], Any]] = field(default_factory=list)
    recognized: list[str] = field(default_factory=list)
    searched: list[str] = field(default_factory=list)

    @property
    def variable(self) -> str:
        """The environment variable of its required field."""
        return env_name(FAMILY, self.code, KEY)

    def identifiers_read(self) -> list[str]:
        return [identifier for identifiers, _seen in self.reads for identifier in identifiers]


@pytest.fixture
def fake() -> Iterator[Callable[..., Fake]]:
    """``fake(tag, keyed=…, ter=…, fields=…)`` registers a MockEnricher subclass under a unique ``b2_<tag>_…`` code: it
    answers as the mock (any ISIN found, the mock's values), searches (one result), and records each ``read`` (the
    identifiers and the value of its key it saw), ``recognize`` and ``search``. ``keyed``: one required SYSTEM field,
    ``api_key``; ``fields``: these settings fields instead; ``ter``: the raw TER its reads give instead of the mock's.
    Removed from the registry, with its claims, at teardown."""
    made: list[Fake] = []

    def register(tag: str, *, keyed: bool = False, ter: str | None = None, fields: tuple[PluginSettingField, ...] | None = None) -> Fake:
        code = f"{CODE_PREFIX}{tag}_{uuid.uuid4().hex[:8]}"
        handle = Fake(code=code)
        lock = threading.Lock()
        declared = fields if fields is not None else ((KEY_FIELD,) if keyed else ())

        def read(self, bindings_read, keys=None):
            with lock:
                handle.reads.append(([binding.identifier for binding in bindings_read], self.settings.get(KEY) if KEY in {setting.key for setting in declared} else None))
            for item in MockEnricher.read(self, bindings_read, keys):
                if ter is not None and item.status is EnricherReadStatus.OK:
                    item = dataclasses.replace(item, values={**item.values, "ter": ter})
                yield item

        def recognize_one(self, binding):
            with lock:
                handle.recognized.append(binding.identifier)
            return MockEnricher.recognize(self, binding)

        def search(self, query: str) -> list[EnricherSearchResult]:
            with lock:
                handle.searched.append(query)
            binding = EnricherBinding(identifier_type="ISIN", identifier=f"IE{abs(hash(query)) % 10**10:010d}")
            return [EnricherSearchResult(name=f"B2 {query}", binding=binding, asset_type=AssetType.ETF, page_url=None)]

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"B2 {tag} (testing)",
            "settings_fields": declared,
            "read": read,
            "recognize": recognize_one,
            "search": search,
        }
        EnricherRegistry.register(type(f"{CLASS_PREFIX}{tag}_{code}", (MockEnricher,), attributes))
        made.append(handle)
        assert EnricherRegistry.get_plugin(code) is not None, f"barrier: {code} is served after its registration"
        return handle

    yield register
    storage = EnricherRegistry._get_storage()
    for handle in made:
        stored = storage.get(handle.code)
        if stored is not None and getattr(stored, "__name__", "").startswith(CLASS_PREFIX):
            storage.pop(handle.code, None)
        release_env_variables(FAMILY, handle.code)


@dataclass
class _Captured:
    events: list[dict[str, Any]]

    def reports(self, variable: str) -> list[tuple[Any, Any]]:
        """``(level, codes)`` of each report naming ``variable``, in order."""
        return [(event.get("log_level"), event.get("codes")) for event in self.events if event.get("variable") == variable]


@pytest.fixture
def captured() -> Iterator[_Captured]:
    """The structlog events of the test, behind a barrier: a canary logged through the registry's own logger is there."""
    with capture_logs() as events:
        provider_registry.logger.debug(LOG_CANARY)
        yield _Captured(events)
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the registry's logger does not reach capture_logs: {events}"


# --- helpers -------------------------------------------------------------------


async def _asset(engine: AsyncEngine, tag: str, config: Mapping[str, Mapping[str, Any]] | None = None) -> int:
    """An ETF of this test, bound to ``config`` (code → binding, in its order) when given."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"B2 {tag} {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.ETF)
        session.add(asset)
        await session.commit()
    asset_id = int(asset.id)
    if config:
        async with AsyncSession(engine) as session:
            await bindings.save_config(session, asset_id, {code: dict(binding) for code, binding in config.items()})
            await session.commit()
    return asset_id


async def _user(engine: AsyncEngine) -> int:
    name = f"b2_{uuid.uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.com", hashed_password="$argon2id$seeded-account")
        session.add(user)
        await session.commit()
    return int(user.id)


async def _row(engine: AsyncEngine, asset_id: int) -> bindings.AssetEnricherRow | None:
    async with AsyncSession(engine) as session:
        return (await bindings.load_enrichers(session, [asset_id])).get(asset_id)


async def _config(engine: AsyncEngine, asset_id: int) -> dict[str, Any]:
    row = await _row(engine, asset_id)
    return {} if row is None else row.config


async def _state(engine: AsyncEngine, asset_id: int) -> dict[str, Any]:
    row = await _row(engine, asset_id)
    return {} if row is None else row.state


async def _profile_rows(engine: AsyncEngine, asset_id: int) -> list[tuple[int, str, str]]:
    """The asset's profile rows as ``(id, voice, source)``, from a session of their own (what was committed)."""
    async with AsyncSession(engine) as session:
        statement = select(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == asset_id).order_by(AssetProfileUpdate.id)
        return [(row.id, row.key, row.source) for row in (await session.execute(statement)).scalars()]


async def _refresh(engine: AsyncEngine, asset_id: int, now: datetime) -> AssetRefreshResult:
    async def run() -> list[AssetRefreshResult]:
        async with AsyncSession(engine) as session:
            return await refresh_assets(session, [asset_id], now=now)

    results = await asyncio.wait_for(run(), DEADLINE)
    found = [result for result in results if result.asset_id == asset_id]
    assert len(found) == 1, f"one result for asset {asset_id}: {results}"
    return found[0]


async def _ask(config: Mapping[str, Mapping[str, Any]], keys: Any = None) -> refresh.AskResult:
    return await asyncio.wait_for(ask_profile(AssetType.ETF, config, keys), DEADLINE)


def _outcome(outcomes: list[ReadOutcome], code: str) -> ReadOutcome:
    found = [outcome for outcome in outcomes if outcome.code == code]
    assert len(found) == 1, f"exactly one outcome of {code}: {outcomes}"
    return found[0]


async def _cascade(identifiers: Mapping[str, str], plugins: Any = None) -> list[Any]:
    async def run() -> list[Any]:
        return [event async for event in recognize_cascade(AssetType.ETF, identifiers, plugins=plugins)]

    return await asyncio.wait_for(run(), DEADLINE)


async def _recognize_api(codes: list[str], identifier: str) -> list[dict[str, Any]]:
    """The events of ``POST /assets/enrichers/recognize``'s stream, parsed."""
    from backend.app.api.v1.assets import enrichers as routes

    request = FAEnricherRecognizeRequest(asset_type=AssetType.ETF, identifiers={"ISIN": identifier}, codes=codes)

    async def run() -> list[dict[str, Any]]:
        return [json.loads(chunk.removeprefix("data: ").strip()) async for chunk in routes._recognize_events(request)]

    return await asyncio.wait_for(run(), DEADLINE)


@pytest.fixture
def routes(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The enricher route module, with the probe's per-user limit off (C0 counts first; not the subject here)."""
    from backend.app.api.v1.assets import enrichers as enricher_routes
    from backend.app.api.v1.assets import providers

    monkeypatch.setattr(providers, "probe_limiter", lambda: None, raising=True)
    return enricher_routes


async def _route_refusal(call: Callable[[], Any]) -> tuple[int, Any]:
    with pytest.raises(HTTPException) as refused:
        await asyncio.wait_for(call(), DEADLINE)
    return refused.value.status_code, refused.value.detail


def _assert_not_configured(refused: tuple[int, Any], code: str, missing: list[str]) -> None:
    """The coded 422 of section 7: exactly ``error_code``, ``message`` and ``missing``; the message names the plugin and
    each missing key (its wording is free)."""
    status_code, detail = refused
    assert status_code == 422, f"the not-configured refusal is the app's coded 422: {refused}"
    assert isinstance(detail, dict) and set(detail) == {"error_code", "message", "missing"}, detail
    assert detail["error_code"] == "NOT_CONFIGURED", detail
    assert isinstance(detail["missing"], list) and detail["missing"] == missing, detail
    assert isinstance(detail["message"], str) and code in detail["message"], detail
    assert all(key in detail["message"] for key in missing), detail


def _test_request(identifier: str) -> FAEnricherTestRequest:
    return FAEnricherTestRequest(binding=FAEnricherBinding(identifier_type="ISIN", identifier=identifier))


# =============================================================================
# 1. THE VARIABLE AND THE REGISTRY
# =============================================================================


def test_b2_the_variable_is_read_at_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """1: comma-separated, stripped, lowercased, in order, each once; None unset, blank or only commas; never cached."""
    from backend.app.config.plugins import enrichers_enabled

    assert enrichers_enabled() is None
    for blank in ("", "   ", " , ,,"):
        monkeypatch.setenv(VARIABLE, blank)
        assert enrichers_enabled() is None, f"{blank!r} lists no code: every enricher stays on"
    monkeypatch.setenv(VARIABLE, " MockEnrich , justetf,mockenrich ,, ESMA")
    assert enrichers_enabled() == ("mockenrich", "justetf", "esma")
    monkeypatch.setenv(VARIABLE, "JustETF")
    assert enrichers_enabled() == ("justetf",), "read at every call: a change of the variable is seen without a restart"


def test_b2_the_enricher_registry_reads_its_own_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """1: ``EnricherRegistry`` names LIBREFOLIO_ENRICHERS_ENABLED, keeps nothing always on, and its codes are the
    config's; the asset providers' variable does not touch it."""
    from backend.app.config.plugins import enrichers_enabled

    assert EnricherRegistry._enabled_variable() == VARIABLE
    assert EnricherRegistry._always_enabled() == frozenset()
    assert EnricherRegistry._enabled_codes() is None
    monkeypatch.setenv("LIBREFOLIO_ASSET_PROVIDERS_ENABLED", "yfinance")
    assert EnricherRegistry._enabled_codes() is None and EnricherRegistry.get_plugin("justetf") is not None, "the asset providers' list is not the enrichers'"
    monkeypatch.setenv(VARIABLE, "MockEnrich,justetf")
    assert EnricherRegistry._enabled_codes() == enrichers_enabled() == ("mockenrich", "justetf")


def test_b2_unset_or_blank_every_enricher_is_served(monkeypatch: pytest.MonkeyPatch) -> None:
    """1: unset (test mode), both installed enrichers are found and listed; a blank list is «all» too. Guard: green on
    HEAD, where nothing reads the variable."""
    assert {"mockenrich", "justetf"} <= set(EnricherRegistry.list_plugin_codes())
    assert {plugin.code for plugin in installed_enrichers()} >= {"mockenrich", "justetf"}
    for blank in ("", " ,, "):
        monkeypatch.setenv(VARIABLE, blank)
        assert EnricherRegistry.get_plugin("justetf") is not None and EnricherRegistry.get_plugin("mockenrich") is not None, f"{blank!r}: all on"


def test_b2_an_enricher_not_listed_is_found_and_listed_nowhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """1: ``mockenrich`` listed alone (any case): justetf is not found, not listed, not installed, not in the catalogue
    nor in any default order; mockenrich still is."""
    catalogue = enrichers_catalogue()
    assert "justetf" in {info.code for info in catalogue.enrichers} and "justetf" in catalogue.default_order[AssetType.ETF], "barrier: unset, justetf is in the catalogue"
    assert "justetf" in default_order(AssetType.ETF), "barrier: unset, justetf orders the ETF"

    monkeypatch.setenv(VARIABLE, "MockEnrich")
    assert EnricherRegistry.get_plugin("mockenrich") is not None and "mockenrich" in EnricherRegistry.list_plugin_codes()
    assert EnricherRegistry.get_plugin("justetf") is None and EnricherRegistry.get_plugin_instance("justetf") is None
    assert "justetf" not in EnricherRegistry.list_plugin_codes()
    assert "justetf" not in {plugin.code for plugin in installed_enrichers()}
    catalogue = enrichers_catalogue()
    assert "justetf" not in {info.code for info in catalogue.enrichers} and "mockenrich" in {info.code for info in catalogue.enrichers}
    assert all("justetf" not in order for order in catalogue.default_order.values()), catalogue.default_order
    assert "justetf" not in default_order(AssetType.ETF) and "mockenrich" in default_order(AssetType.ETF)


@pytest.mark.asyncio
async def test_b2_the_cascade_never_asks_an_enricher_not_listed(monkeypatch: pytest.MonkeyPatch, justetf_offline: NetworkGuard) -> None:
    """1: ``recognize_cascade`` with ``plugins=None`` (the installed enrichers) asks justetf when unset, never when only
    mockenrich is listed. The stub that would have reached justetf.com is the witness."""
    isin = _ident("RC")
    unset = await _cascade({"ISIN": isin})
    assert any(isinstance(event, Recognized) and event.code == "justetf" for event in unset), f"barrier: unset, justetf is asked: {unset}"
    assert ("get_etf_overview", isin) in justetf_offline.calls, f"barrier: unset, justetf reached its (stubbed) library: {justetf_offline.calls}"
    justetf_offline.calls.clear()

    monkeypatch.setenv(VARIABLE, "mockenrich")
    events = await _cascade({"ISIN": _ident("RC")})
    assert any(isinstance(event, Recognized) and event.code == "mockenrich" for event in events), f"barrier: mockenrich still answers: {events}"
    assert not any(getattr(event, "code", None) == "justetf" or getattr(event, "source", None) == "justetf" for event in events), events
    assert justetf_offline.calls == [], f"justetf was asked: {justetf_offline.calls}"


def test_b2_yahoo_is_guarded_offline(yahoo_offline: YahooGuard) -> None:
    """Witness of the Yahoo guard, red until C3 (the module is absent): the Yahoo enricher is installed and its ``yf``
    is this file's offline stub, so the guard of every other test here is not inert."""
    module = importlib.import_module(YAHOO_PLUGIN)
    assert yahoo_offline.installed and isinstance(module.yf, _YahooOffline), f"the Yahoo enricher's yf is not the offline stub: {getattr(module, 'yf', None)!r}"
    assert EnricherRegistry.get_plugin("yfinance") is not None, "the Yahoo enricher is installed"


def test_b2_an_unknown_code_is_ignored_and_logged_once(monkeypatch: pytest.MonkeyPatch, captured: _Captured) -> None:
    """1: ``mockenrich,<unknown>``: mockenrich alone is on, and the unknown code is one warning naming the variable,
    however many lookups."""
    unknown = f"b2_nosuch_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv(VARIABLE, f"mockenrich,{unknown.upper()}")
    for _ in range(3):
        EnricherRegistry.list_plugin_codes()
        EnricherRegistry.get_plugin("justetf")
        installed_enrichers()
    assert EnricherRegistry.get_plugin("mockenrich") is not None and EnricherRegistry.get_plugin("justetf") is None
    assert captured.reports(VARIABLE) == [("warning", [unknown])]


def test_b2_the_switch_needs_no_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    """1: read at every call: the same process sees mockenrich off, then on again, then all."""
    monkeypatch.setenv(VARIABLE, "justetf")
    assert EnricherRegistry.get_plugin("mockenrich") is None and EnricherRegistry.get_plugin("justetf") is not None
    monkeypatch.setenv(VARIABLE, "mockenrich")
    assert EnricherRegistry.get_plugin("mockenrich") is not None and EnricherRegistry.get_plugin("justetf") is None
    monkeypatch.delenv(VARIABLE)
    assert EnricherRegistry.get_plugin("mockenrich") is not None and EnricherRegistry.get_plugin("justetf") is not None


# =============================================================================
# 2. NO CLEAN-UP
# =============================================================================


@pytest.mark.asyncio
async def test_b2_a_turned_off_enricher_is_skipped_and_its_never_read_binding_stays(engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """2: an asset bound to mockenrich (never read) and to an enricher that is on; mockenrich turned off with the list
    ``justetf,<on>``: the refresh reads only the one on, mockenrich's binding stays, it gets no state, no row in its
    name, and the weekly job's item is «ok»."""
    on = fake("on")
    off_isin, on_isin = _ident("OF"), _ident("ON")
    asset_id = await _asset(engine, "off never read", {"mockenrich": _entry(off_isin), on.code: _entry(on_isin)})
    config_before = await _config(engine, asset_id)
    monkeypatch.setenv(VARIABLE, f"justetf,{on.code}")
    assert EnricherRegistry.get_plugin("mockenrich") is None, "mockenrich is turned off by the list"

    result = await _refresh(engine, asset_id, NOW)

    assert on.identifiers_read() == [on_isin] and set(result.written) == MOCK_VOICES, f"barrier: the enricher on is read and written: {result}"
    assert [outcome.code for outcome in result.outcomes] == [on.code], f"mockenrich is not read: {result.outcomes}"
    assert await _config(engine, asset_id) == config_before, "the binding to the enricher turned off stays"
    assert set(await _state(engine, asset_id)) == {on.code}, "no state for the enricher turned off"
    assert {source for _id, _key, source in await _profile_rows(engine, asset_id)} == {on.code}, "no row in the name of the enricher turned off"
    item = _profile_read_item(result, "B2 asset", None)
    assert (item["status"], item["error"]) == ("ok", None), item


@pytest.mark.asyncio
async def test_b2_a_turned_off_enricher_keeps_its_state_and_rows(engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """2: mockenrich read once (on), then turned off: a refresh at another time leaves its state entry and its rows as
    they were (a read would have stamped the new ``read_at``), and the item is «ok»."""
    on = fake("on")
    asset_id = await _asset(engine, "off primed", {"mockenrich": _entry(_ident("MP")), on.code: _entry(_ident("OP"))})
    primed = await _refresh(engine, asset_id, NOW)
    state_before, rows_before = await _state(engine, asset_id), await _profile_rows(engine, asset_id)
    assert {outcome.code for outcome in primed.outcomes} == {"mockenrich", on.code} and "mockenrich" in state_before, f"barrier: both read once: {primed}"
    assert any(source == "mockenrich" for _id, _key, source in rows_before), f"barrier: mockenrich wrote rows: {rows_before}"
    clear_cache(CACHE_NAME)  # the next read of the enricher on reaches its plugin
    reads_before = len(on.reads)

    monkeypatch.setenv(VARIABLE, f"justetf,{on.code}")
    result = await _refresh(engine, asset_id, LATER)

    assert len(on.reads) == reads_before + 1, f"barrier: the enricher on is read again: {on.reads}"
    assert [outcome.code for outcome in result.outcomes] == [on.code], f"mockenrich is not read: {result.outcomes}"
    state = await _state(engine, asset_id)
    assert state["mockenrich"] == state_before["mockenrich"], "the state of the enricher turned off is as it was"
    assert state[on.code] != state_before[on.code], "barrier: the enricher on got a new state entry (another read_at)"
    mine_before = [row for row in rows_before if row[2] == "mockenrich"]
    assert [row for row in await _profile_rows(engine, asset_id) if row[2] == "mockenrich"] == mine_before, "no row in the name of the enricher turned off"
    assert _profile_read_item(result, "B2 asset", None)["status"] == "ok"


def test_b2_a_patch_item_may_name_a_turned_off_enricher(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: the PATCH item accepts a binding to an enricher not served (a code, installed or not). Guard: green on HEAD."""
    monkeypatch.setenv(VARIABLE, "justetf")
    item = FAAssetPatchItem(asset_id=1, enrichers={"mockenrich": FAEnricherBinding(identifier_type="ISIN", identifier="IE00B4L5Y983"), "justetf": FAEnricherBinding(identifier_type="ISIN", identifier="IE00B4L5Y983")})
    assert list(item.enrichers or {}) == ["mockenrich", "justetf"]


@pytest.mark.asyncio
async def test_b2_a_patch_keeps_a_turned_off_enricher_in_the_config(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """2: with mockenrich turned off, a PATCH of another field leaves the binding, and a PATCH that sends the bindings
    again (the order changed) stores mockenrich in them. Guard: green on HEAD; pins that the switch never cleans up."""
    user_id = await _user(engine)
    first, second = _ident("P1"), _ident("P2")
    asset_id = await _asset(engine, "patch", {"mockenrich": _entry(first), "justetf": _entry(second)})
    monkeypatch.setenv(VARIABLE, "justetf")

    async def patch(item: dict[str, Any]) -> Any:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await AssetCRUDService.patch_assets_bulk([FAAssetPatchItem(asset_id=asset_id, **item)], session, user_id=user_id)

    renamed = await patch({"display_name": f"B2 renamed {uuid.uuid4().hex[:8]}"})
    assert renamed.committed is True, renamed
    assert await _config(engine, asset_id) == {"mockenrich": _entry(first), "justetf": _entry(second)}
    reordered = await patch({"enrichers": {"justetf": _entry(second), "mockenrich": _entry(first)}})
    assert reordered.committed is True, reordered
    assert list((await _config(engine, asset_id)).items()) == [("justetf", _entry(second)), ("mockenrich", _entry(first))]


# =============================================================================
# 3. THE READ CACHE NEVER OUTLIVES THE SWITCH
# =============================================================================


@pytest.mark.asyncio
async def test_b2_a_turned_off_enricher_answers_no_answer_even_with_a_warm_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: mockenrich read once (the cache now holds it), then turned off: ask answers its request ``NO_ANSWER``, with no
    value, and merges nothing from it."""
    config = {"mockenrich": _entry(_ident("WC"))}
    warm = await _ask(config)
    assert _outcome(warm.outcomes, "mockenrich").status is EnricherReadStatus.OK and warm.voices, f"barrier: the first ask reads mockenrich: {warm}"
    again = await _ask(config)
    assert _outcome(again.outcomes, "mockenrich").from_cache is True, "barrier: the cache holds the read"

    monkeypatch.setenv(VARIABLE, "justetf")
    off = await _ask(config)

    outcome = _outcome(off.outcomes, "mockenrich")
    assert (outcome.status, outcome.error_code, dict(outcome.values), outcome.from_cache) == (EnricherReadStatus.ERROR, "NO_ANSWER", {}, False), outcome
    assert off.voices == {}, f"nothing merged from an enricher turned off: {off.voices}"


@pytest.mark.asyncio
async def test_b2_an_enricher_no_longer_installed_answers_no_answer_even_with_a_warm_cache(fake: Callable[..., Fake]) -> None:
    """3, without the variable: an enricher read once, then removed from the registry (uninstalled), is not answered
    from the cache. Red on HEAD for the order of the lookups alone (the cache is looked up before the plugin)."""
    gone = fake("gone")
    config = {gone.code: _entry(_ident("GN"))}
    assert _outcome((await _ask(config)).outcomes, gone.code).status is EnricherReadStatus.OK, "barrier: the first ask reads it"
    EnricherRegistry._get_storage().pop(gone.code)
    assert EnricherRegistry.get_plugin(gone.code) is None, "barrier: no longer installed"

    after = await _ask(config)

    outcome = _outcome(after.outcomes, gone.code)
    assert (outcome.status, outcome.error_code, dict(outcome.values), outcome.from_cache) == (EnricherReadStatus.ERROR, "NO_ANSWER", {}, False), outcome
    assert after.voices == {}


@pytest.mark.asyncio
async def test_b2_the_source_value_of_a_turned_off_enricher_is_not_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: ``source_value`` (a «use the source's value») of mockenrich, cached, then turned off: «not an installed
    enricher», never the cached value."""
    binding = _entry(_ident("SV"))
    first = await asyncio.wait_for(source_value("mockenrich", binding, "ter"), DEADLINE)
    assert isinstance(first, SourceValue), f"barrier: on, the source gives its value: {first}"

    monkeypatch.setenv(VARIABLE, "justetf")
    answer = await asyncio.wait_for(source_value("mockenrich", binding, "ter"), DEADLINE)

    assert isinstance(answer, str) and "not an installed enricher" in answer, answer


# =============================================================================
# 4. A REQUIRED SETTING LEFT EMPTY → THE ENRICHER IS NOT USED
# =============================================================================


async def _not_configured_barrier(handle: Fake) -> None:
    """The platform's own view: the keyed enricher lacks its key (unset), and is ready once its variable is set."""
    assert await plugins_readiness(FAMILY, [handle.code], user_id=None) == {handle.code: PluginReadiness(False, (KEY,))}, "barrier: the keyed enricher is not configured"


@pytest.mark.asyncio
async def test_b2_readiness_sees_the_keyed_enricher(fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """Barrier of section 4, on its own: the keyed enricher is not configured unset and configured with its variable.
    Guard: green on HEAD (76's N1)."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    assert await plugins_readiness(FAMILY, [keyed.code], user_id=None) == {keyed.code: PluginReadiness(True, ())}


@pytest.mark.asyncio
async def test_b2_the_refresh_skips_a_not_configured_enricher(engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4: an asset bound to the keyed enricher (no key) and to mockenrich: the refresh never calls the keyed one, gives it
    no state and no row, keeps its binding, and the item is «ok». Positive control: with its key set, the next refresh
    reads it, with the key bound."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)
    keyed_isin = _ident("KR")
    asset_id = await _asset(engine, "not configured", {keyed.code: _entry(keyed_isin), "mockenrich": _entry(_ident("MR"))})
    config_before = await _config(engine, asset_id)

    result = await _refresh(engine, asset_id, NOW)

    assert "mockenrich" in {outcome.code for outcome in result.outcomes} and set(result.written) == MOCK_VOICES, f"barrier: mockenrich is read and written: {result}"
    assert keyed.reads == [], f"the not-configured enricher was called: {keyed.reads}"
    assert keyed.code not in {outcome.code for outcome in result.outcomes}, f"skipped like a plugin not installed: {result.outcomes}"
    assert await _config(engine, asset_id) == config_before and set(await _state(engine, asset_id)) == {"mockenrich"}
    assert {source for _id, _key, source in await _profile_rows(engine, asset_id)} == {"mockenrich"}
    assert _profile_read_item(result, "B2 asset", None)["status"] == "ok"

    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    configured = await _refresh(engine, asset_id, LATER)

    assert keyed.reads == [([keyed_isin], KEY_VALUE)], f"configured, it is read with its key bound: {keyed.reads}"
    assert _outcome(configured.outcomes, keyed.code).status is EnricherReadStatus.OK
    assert keyed.code in await _state(engine, asset_id)


@pytest.mark.asyncio
async def test_b2_ask_answers_not_configured_without_calling_the_enricher(fake: Callable[..., Fake]) -> None:
    """4: ask on the keyed enricher (no key) beside mockenrich: an ``ERROR`` / ``NOT_CONFIGURED`` outcome for it, no
    value, no call; mockenrich answers."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)

    answer = await _ask({keyed.code: _entry(_ident("KA")), "mockenrich": _entry(_ident("MA"))})

    assert _outcome(answer.outcomes, "mockenrich").status is EnricherReadStatus.OK, f"barrier: mockenrich answers: {answer.outcomes}"
    outcome = _outcome(answer.outcomes, keyed.code)
    assert (outcome.status, outcome.error_code, dict(outcome.values)) == (EnricherReadStatus.ERROR, "NOT_CONFIGURED", {}), outcome
    assert keyed.reads == [], f"the not-configured enricher was called: {keyed.reads}"
    assert all(voice.source == "mockenrich" for voice in answer.voices.values())


@pytest.mark.asyncio
async def test_b2_a_not_configured_enricher_is_not_answered_from_a_warm_cache(fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4: read once with its key (the cache now holds it, and the read saw the key bound), then the key removed: the
    next ask answers ``NOT_CONFIGURED``, not from the cache, and calls nothing."""
    keyed = fake("keyed", keyed=True)
    config = {keyed.code: _entry(_ident("KW"))}
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    warm = await _ask(config)
    assert _outcome(warm.outcomes, keyed.code).status is EnricherReadStatus.OK, f"barrier: configured, it answers: {warm.outcomes}"
    assert [seen for _ids, seen in keyed.reads] == [KEY_VALUE], f"its settings are bound before the read: {keyed.reads}"

    monkeypatch.delenv(keyed.variable)
    await _not_configured_barrier(keyed)
    answer = await _ask(config)

    outcome = _outcome(answer.outcomes, keyed.code)
    assert (outcome.status, outcome.error_code, dict(outcome.values), outcome.from_cache) == (EnricherReadStatus.ERROR, "NOT_CONFIGURED", {}, False), outcome
    assert len(keyed.reads) == 1, f"no second call: {keyed.reads}"


@pytest.mark.asyncio
async def test_b2_the_source_value_of_a_not_configured_enricher_is_not_given(fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4: ``source_value`` of the keyed enricher without its key gives a reason, not a value, and calls nothing;
    configured, it gives the value."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)
    binding = _entry(_ident("KS"))

    answer = await asyncio.wait_for(source_value(keyed.code, binding, "ter"), DEADLINE)

    assert isinstance(answer, str), answer
    assert keyed.reads == [], f"the not-configured enricher was called: {keyed.reads}"
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    assert isinstance(await asyncio.wait_for(source_value(keyed.code, binding, "ter"), DEADLINE), SourceValue), "configured, it gives its value"


@pytest.mark.asyncio
async def test_b2_the_api_cascade_does_not_ask_a_not_configured_enricher(fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4: ``POST /assets/enrichers/recognize`` (its event stream) over the keyed enricher and mockenrich: no answer of
    the keyed one, no call; configured, it answers."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)

    events = await _recognize_api([keyed.code, "mockenrich"], _ident("KC"))

    results = [event["code"] for event in events if event.get("event") == "enricher_result"]
    assert "mockenrich" in results and events[-1].get("event") == "done", f"barrier: mockenrich answers and the stream ends: {events}"
    assert keyed.code not in results and keyed.recognized == [], f"the not-configured enricher was asked: {events} {keyed.recognized}"

    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    configured = await _recognize_api([keyed.code, "mockenrich"], _ident("KC"))
    assert keyed.code in [event["code"] for event in configured if event.get("event") == "enricher_result"], configured
    assert len(keyed.recognized) == 1


@pytest.mark.asyncio
async def test_b2_the_test_route_refuses_a_not_configured_enricher(routes: Any, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4 and 7: ``POST /assets/enrichers/{code}/test`` on the keyed enricher without its key: the coded 422
    ``NOT_CONFIGURED`` naming it and the missing key, no call; configured, it answers «found». Changed by B2b (was 400
    with ``error_code`` and ``missing`` only)."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)

    refused = await _route_refusal(lambda: routes.test_enricher(keyed.code, _test_request(_ident("KT")), USER))

    _assert_not_configured(refused, keyed.code, [KEY])
    assert keyed.recognized == []
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    answer = await asyncio.wait_for(routes.test_enricher(keyed.code, _test_request(_ident("KT")), USER), DEADLINE)
    assert answer.status == "found" and len(keyed.recognized) == 1, answer


@pytest.mark.asyncio
async def test_b2_the_search_route_refuses_a_not_configured_enricher(routes: Any, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4 and 7: ``GET /assets/enrichers/{code}/search`` on the keyed enricher without its key: the coded 422
    ``NOT_CONFIGURED`` naming it and the missing key, no call; configured, it searches. Changed by B2b (was 400 with
    ``error_code`` and ``missing`` only)."""
    keyed = fake("keyed", keyed=True)
    await _not_configured_barrier(keyed)
    query = f"b2 search {uuid.uuid4().hex[:8]}"

    refused = await _route_refusal(lambda: routes.search_enricher(keyed.code, query, USER))

    _assert_not_configured(refused, keyed.code, [KEY])
    assert keyed.searched == []
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    results = await asyncio.wait_for(routes.search_enricher(keyed.code, query, USER), DEADLINE)
    assert keyed.searched == [query] and len(results) == 1, results


@pytest.mark.parametrize("route", ["test", "search"])
@pytest.mark.asyncio
async def test_b2_a_turned_off_enricher_is_404_like_an_unknown_code(route: str, routes: Any, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """4: the test and search routes on an enricher turned off (configured, so only the switch decides) answer as for a
    code no enricher has: 404, same detail but the code; nothing called."""
    on = fake("keyed", keyed=True)
    monkeypatch.setenv(on.variable, KEY_VALUE)
    query = f"b2 off {uuid.uuid4().hex[:8]}"

    def call(code: str) -> Callable[[], Any]:
        if route == "test":
            return lambda: routes.test_enricher(code, _test_request(_ident("OT")), USER)
        return lambda: routes.search_enricher(code, query, USER)

    await asyncio.wait_for(call(on.code)(), DEADLINE)
    assert len(on.recognized) + len(on.searched) == 1, "barrier: unset, the route reaches the enricher"
    unknown_code = f"b2_nosuch_{uuid.uuid4().hex[:8]}"
    unknown = await _route_refusal(call(unknown_code))
    assert unknown[0] == 404, f"barrier: today's answer to an unknown code: {unknown}"

    monkeypatch.setenv(VARIABLE, "mockenrich")
    status_code, detail = await _route_refusal(call(on.code))

    assert (status_code, json.dumps(detail).replace(on.code, "<code>")) == (unknown[0], json.dumps(unknown[1]).replace(unknown_code, "<code>"))
    assert len(on.recognized) + len(on.searched) == 1, "the enricher turned off was called"


@pytest.mark.asyncio
async def test_b2_the_cascade_over_the_installed_enrichers_follows_the_switch(fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch, justetf_offline: NetworkGuard) -> None:
    """1 and 4 together through the API's stream with no ``codes``: listed ``mockenrich,<keyed>`` with the keyed one
    configured, the stream asks both and never justetf (its stub stays silent)."""
    keyed = fake("keyed", keyed=True)
    monkeypatch.setenv(keyed.variable, KEY_VALUE)
    monkeypatch.setenv(VARIABLE, f"mockenrich,{keyed.code}")
    from backend.app.api.v1.assets import enrichers as enricher_routes

    request = FAEnricherRecognizeRequest(asset_type=AssetType.ETF, identifiers={"ISIN": _ident("AL")})
    events = [json.loads(chunk.removeprefix("data: ").strip()) async for chunk in enricher_routes._recognize_events(request)]

    results = {event["code"] for event in events if event.get("event") == "enricher_result"}
    assert {"mockenrich", keyed.code} <= results, events
    assert "justetf" not in results and justetf_offline.calls == [], f"justetf was asked: {justetf_offline.calls}"
    assert "justetf" not in events[-1]["default_order"], events[-1]


def test_b2_recognize_module_reads_the_installed_enrichers() -> None:
    """Barrier of the cascade tests: ``recognize_cascade`` with ``plugins=None`` reads ``installed_enrichers`` from the
    bindings module (so the registry's gate reaches it). Guard: green on HEAD."""
    assert recognize.installed_enrichers is bindings.installed_enrichers


# =============================================================================
# 5. VOICES HAND OVER (B2b)
# =============================================================================

#: The raw TER each of the two enrichers of the hand-over gives: different, so the source of «now» is visible.
TER_A = "0.0012"
TER_B = "0.0047"


async def _now(engine: AsyncEngine, asset_id: int, key: str) -> tuple[str, Any] | None:
    """«Now» of one voice as ``(source, value in stored form)``, from the store's own reader."""
    async with AsyncSession(engine) as session:
        row = (await current_rows(session, asset_id, [key])).get(key)
    return None if row is None else (row.source, row.value)


def _sources_of(rows: list[tuple[int, str, str]], key: str) -> list[str]:
    """The sources of the rows of one voice, in the order they were written (``_profile_rows`` is by id)."""
    return [source for _id, voice, source in rows if voice == key]


@pytest.mark.parametrize("absence", ["switched_off", "not_configured"])
@pytest.mark.asyncio
async def test_b2b_a_missing_enricher_hands_its_voices_over_and_takes_them_back(absence: str, engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """5: ``{A, B}`` bound (A first), both give ``ter`` with different values, A read first: «now» is A's. A switched off
    (or its required key removed): nothing is written by the switch; the next refresh makes B's value «now» (one row,
    source B), A's rows stay, the ``config`` (A then B) is unchanged, and a voice both give alike makes no row. A back:
    the next read makes A «now» again (one row), and a further read writes nothing. Guard: green on HEAD 3e720ad61."""
    keyed = absence == "not_configured"
    a = fake("ha", keyed=keyed, ter=TER_A)
    b = fake("hb", ter=TER_B)
    if keyed:
        monkeypatch.setenv(a.variable, KEY_VALUE)
    ter_a, ter_b = normalize_value("ter", TER_A), normalize_value("ter", TER_B)
    assert ter_a != ter_b, "barrier: the two TERs differ in stored form"
    asset_id = await _asset(engine, f"hand over {absence}", {a.code: _entry(_ident("HA")), b.code: _entry(_ident("HB"))})
    config_before = await _config(engine, asset_id)
    assert list(config_before) == [a.code, b.code], "barrier: the user's order is A then B"

    first = await _refresh(engine, asset_id, NOW)
    assert {outcome.code: outcome.status for outcome in first.outcomes} == {a.code: EnricherReadStatus.OK, b.code: EnricherReadStatus.OK}, f"barrier: both read: {first}"
    assert await _now(engine, asset_id, "ter") == (a.code, ter_a), "barrier: A, first of the order, is «now»"
    rows_first, state_first = await _profile_rows(engine, asset_id), await _state(engine, asset_id)
    assert _sources_of(rows_first, "ter") == [a.code] and _sources_of(rows_first, "distribution_policy") == [a.code], f"barrier: A wrote the voices: {rows_first}"

    if keyed:
        monkeypatch.delenv(a.variable)
        await _not_configured_barrier(a)
    else:
        monkeypatch.setenv(VARIABLE, f"mockenrich,{b.code}")
        assert EnricherRegistry.get_plugin(a.code) is None and EnricherRegistry.get_plugin(b.code) is not None, "barrier: A off, B on"
    assert (await _profile_rows(engine, asset_id), await _state(engine, asset_id), await _config(engine, asset_id)) == (rows_first, state_first, config_before), "the switch alone writes nothing"

    handed = await _refresh(engine, asset_id, LATER)

    assert [outcome.code for outcome in handed.outcomes] == [b.code], f"A is absent like a source that is down: {handed.outcomes}"
    assert await _now(engine, asset_id, "ter") == (b.code, ter_b), "B's value is «now»"
    rows_handed = await _profile_rows(engine, asset_id)
    assert _sources_of(rows_handed, "ter") == [a.code, b.code], f"one row, source B: {rows_handed}"
    assert set(rows_first) <= set(rows_handed), "A's rows are still there"
    assert _sources_of(rows_handed, "distribution_policy") == [a.code], "a voice B gives alike makes no row"
    assert list((await _config(engine, asset_id)).items()) == list(config_before.items()), "the user's dictionary is unchanged, A then B"
    assert (await _state(engine, asset_id))[a.code] == state_first[a.code], "A's state is as it was"

    if keyed:
        monkeypatch.setenv(a.variable, KEY_VALUE)
    else:
        monkeypatch.delenv(VARIABLE)
    back = await _refresh(engine, asset_id, LATER + timedelta(days=1))

    assert {outcome.code for outcome in back.outcomes} == {a.code, b.code}, f"barrier: A read again: {back.outcomes}"
    assert await _now(engine, asset_id, "ter") == (a.code, ter_a), "A is «now» again"
    rows_back = await _profile_rows(engine, asset_id)
    assert _sources_of(rows_back, "ter") == [a.code, b.code, a.code], f"one row, source A: {rows_back}"
    assert _sources_of(rows_back, "distribution_policy") == [a.code]

    await _refresh(engine, asset_id, LATER + timedelta(days=2))
    assert _sources_of(await _profile_rows(engine, asset_id), "ter") == [a.code, b.code, a.code], "A already «now»: no row"
    assert list((await _config(engine, asset_id)).items()) == list(config_before.items())


# =============================================================================
# 6. ONE LOG LINE PER REFRESH CALL NAMING THE SKIPPED ENRICHERS (B2b)
# =============================================================================

REFRESH_CANARY = "enrichers enabled test: the capture reaches the refresh module's logger"


async def _refresh_many(engine: AsyncEngine, asset_ids: list[int], now: datetime) -> list[AssetRefreshResult]:
    """One ``refresh_assets`` call over every asset given."""

    async def run() -> list[AssetRefreshResult]:
        async with AsyncSession(engine) as session:
            return await refresh_assets(session, asset_ids, now=now)

    results = await asyncio.wait_for(run(), DEADLINE)
    assert sorted(result.asset_id for result in results) == sorted(asset_ids), f"barrier: one result per asset: {results}"
    return results


def _skip_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The lines naming the skipped enrichers: those with an ``enrichers`` field (message and level are free)."""
    return [event for event in events if "enrichers" in event]


@contextmanager
def _refresh_logs() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through ``refresh``'s own logger is there."""
    with capture_logs() as events:
        refresh.logger.info(REFRESH_CANARY)
        yield events
    assert any(event.get("event") == REFRESH_CANARY for event in events), f"barrier: refresh's logger does not reach capture_logs: {events}"


@pytest.mark.asyncio
async def test_b2b_one_line_names_every_enricher_the_call_skipped(engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """6: one call over three assets: two bound to a switched-off enricher, one to a not-configured one, all three to an
    enricher on. Exactly one line for the call, its ``enrichers`` the two skipped codes, sorted, each once."""
    on, off, keyed = fake("lon"), fake("loff"), fake("lkey", keyed=True)
    await _not_configured_barrier(keyed)
    monkeypatch.setenv(VARIABLE, f"{on.code},{keyed.code}")
    assert EnricherRegistry.get_plugin(off.code) is None and EnricherRegistry.get_plugin(keyed.code) is not None, "barrier: off is off, keyed is served"
    assets = [
        await _asset(engine, "log off 1", {off.code: _entry(_ident("L1")), on.code: _entry(_ident("O1"))}),
        await _asset(engine, "log off 2", {off.code: _entry(_ident("L2")), on.code: _entry(_ident("O2"))}),
        await _asset(engine, "log keyed", {keyed.code: _entry(_ident("L3")), on.code: _entry(_ident("O3"))}),
    ]

    with _refresh_logs() as events:
        results = await _refresh_many(engine, assets, NOW)

    assert len(on.identifiers_read()) == 3 and all(set(result.written) == MOCK_VOICES for result in results), f"barrier: the enricher on is read for every asset: {results}"
    assert off.reads == [] and keyed.reads == [], "barrier: the two are skipped"
    lines = _skip_lines(events)
    assert len(lines) == 1, f"one line for the whole call, not one per asset: {lines}"
    assert lines[0]["enrichers"] == sorted([off.code, keyed.code]), lines[0]


@pytest.mark.asyncio
async def test_b2b_one_line_per_call_names_a_code_bound_twice_once(engine: AsyncEngine, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """6: two assets bound to the same switched-off enricher: one line, the code once; a second call logs its own line
    (one per call, not once per process)."""
    on, off = fake("lon"), fake("loff")
    monkeypatch.setenv(VARIABLE, on.code)
    assets = [await _asset(engine, f"log twice {n}", {off.code: _entry(_ident(f"T{n}")), on.code: _entry(_ident(f"U{n}"))}) for n in (1, 2)]

    for now in (NOW, LATER):
        with _refresh_logs() as events:
            await _refresh_many(engine, assets, now)
        lines = _skip_lines(events)
        assert [line.get("enrichers") for line in lines] == [[off.code]], f"call at {now}: one line, the code once: {lines}"
    assert off.reads == []


@pytest.mark.asyncio
async def test_b2b_no_line_when_nothing_is_skipped(engine: AsyncEngine, fake: Callable[..., Fake]) -> None:
    """6: every bound enricher served and configured: the call writes and logs no line naming skipped enrichers. Guard:
    green on HEAD (nothing logs it yet); with the canary and the write it is not vacuous."""
    on = fake("lon")
    asset_id = await _asset(engine, "log none", {on.code: _entry(_ident("N1")), "mockenrich": _entry(_ident("N2"))})

    with _refresh_logs() as events:
        results = await _refresh_many(engine, [asset_id], NOW)

    assert set(results[0].written) == MOCK_VOICES and {outcome.code for outcome in results[0].outcomes} == {on.code, "mockenrich"}, f"barrier: both read: {results}"
    assert _skip_lines(events) == [], events


# =============================================================================
# 7. THE NOT-CONFIGURED REFUSAL IS THE APP'S CODED 422 (B2b)
# =============================================================================


def test_b2b_not_configured_error_is_the_coded_422() -> None:
    """7: ``not_configured_error(code, missing)``: an ``HTTPException`` 422 whose detail has exactly ``error_code``
    (``NOT_CONFIGURED``), ``message`` (names the plugin and each key) and ``missing`` (a list, in the order given)."""
    from backend.app.api.plugin_errors import not_configured_error

    error = not_configured_error("b2b_somecode", ("zeta_key", "alpha.token"))

    assert isinstance(error, HTTPException) and error.status_code == 422, error
    assert isinstance(error.detail, dict) and set(error.detail) == {"error_code", "message", "missing"}, error.detail
    assert error.detail["error_code"] == "NOT_CONFIGURED"
    assert error.detail["missing"] == ["zeta_key", "alpha.token"] and type(error.detail["missing"]) is list, "a list, in the order given"
    message = error.detail["message"]
    assert isinstance(message, str) and all(part in message for part in ("b2b_somecode", "zeta_key", "alpha.token")), message
    assert not_configured_error("b2b_other", ["only_key"]).detail["missing"] == ["only_key"], "a list in, the same list out"


#: A setting a variable locks with an invalid value: the plugin is not configured, and in the managed profile the
#: customer is not told about it (decision N2).
LOCKED_KEY = "hoster_region"
LOCKED_FIELD = PluginSettingField(key=LOCKED_KEY, type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Region (b2b test)", default="eu", options=(SettingOption("eu", "EU"), SettingOption("us", "US")))


@pytest.mark.parametrize("route", ["test", "search"])
@pytest.mark.parametrize(("profile", "told"), [("managed", [KEY]), ("selfhosted", [KEY, LOCKED_KEY])])
@pytest.mark.asyncio
async def test_b2b_the_routes_tell_what_readiness_may_tell(profile: str, told: list[str], route: str, routes: Any, fake: Callable[..., Fake], monkeypatch: pytest.MonkeyPatch) -> None:
    """7: ``missing`` is ``plugins_readiness(...).missing``: an enricher whose key is empty and whose region a variable
    locks with an invalid value. Managed: the coded 422 names the key only (the locked field is neither in ``missing``
    nor in the message); self-hosted: both. Nothing called."""
    keyed = fake("mgd", fields=(KEY_FIELD, LOCKED_FIELD))
    monkeypatch.setenv(env_name(FAMILY, keyed.code, LOCKED_KEY), "zz")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", profile)
    readiness_now = await plugins_readiness(FAMILY, [keyed.code], user_id=None)
    assert readiness_now == {keyed.code: PluginReadiness(False, tuple(told))}, f"barrier: what a caller may be told: {readiness_now}"
    query = f"b2b managed {uuid.uuid4().hex[:8]}"

    if route == "test":
        refused = await _route_refusal(lambda: routes.test_enricher(keyed.code, _test_request(_ident("MG")), USER))
    else:
        refused = await _route_refusal(lambda: routes.search_enricher(keyed.code, query, USER))

    _assert_not_configured(refused, keyed.code, told)
    if LOCKED_KEY not in told:
        assert LOCKED_KEY not in refused[1]["message"], f"the locked field is not told: {refused}"
    assert keyed.recognized == [] and keyed.searched == []

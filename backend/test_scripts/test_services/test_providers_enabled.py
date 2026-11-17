# ruff: noqa: PLC0415 — the new names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""Instance allow-lists of the asset and FX providers (project 76, lot X1).

``LIBREFOLIO_ASSET_PROVIDERS_ENABLED`` and ``LIBREFOLIO_FX_PROVIDERS_ENABLED``: set, only the listed providers are active;
unset, blank or only commas, all are. A provider not listed appears in no list, search, setting, assignment or route.
No clean-up: an existing assignment or route to a switched-off provider stays, and its call answers as for an absent
provider. The contract pinned here:

1. **Config** (``config/plugins.py``): ``asset_providers_enabled()`` and ``fx_providers_enabled()`` →
   ``tuple[str, ...] | None`` through ``_provider_codes`` (comma-separated, stripped, lowercased, ordered, each once;
   None when unset, blank or only commas). Read at every call, never cached.
2. **Registry hook** (``services/platform/provider_registry.py``, ``AbstractPluginRegistry``): classmethods
   ``_enabled_codes()`` (default None), ``_enabled_variable()`` (default None), ``_always_enabled()`` (lowercase codes,
   default empty) and ``_switched_off(code)``: True iff ``_enabled_codes()`` is not None and ``code.lower()`` is neither
   in it nor in ``_always_enabled()``. Applied by ``get_plugin`` (None), ``get_plugin_instance`` /
   ``get_provider_instance`` (None), ``list_plugin_codes`` and ``list_providers`` (omitted); case-insensitive; X-R44
   (``_withheld``) still applies on its own. ``AssetProviderRegistry``: ``LIBREFOLIO_ASSET_PROVIDERS_ENABLED``.
   ``FXProviderRegistry``: ``LIBREFOLIO_FX_PROVIDERS_ENABLED``, and ``MANUAL`` always enabled. A listed code no
   registered provider of that registry has (case-insensitive; a test-only one outside test mode counts as unknown) is
   ignored and logged once per process, at warning level, with the keys ``variable`` (the variable's name) and ``codes``
   (the unknown codes, lowercased, in the listed order). The once-only memory is
   ``provider_registry._report_unknown_enabled`` (a ``functools.cache`` function, like
   ``provider_policy._report_unknown``): the fixture empties it with ``cache_clear()``.
3. **Effects**: ``GET /assets/provider`` and ``GET /fx/providers`` omit a switched-off provider; an assignment item
   naming one is refused exactly as an unknown code (``FAProviderConfigBase`` validator); ``POST /fx/providers/routes``
   naming one is refused as an unknown code, MANUAL still accepted; an existing assignment's current price and refresh
   answer as for an unknown code (last stored price; ``Provider not found``); the FX sync never asks a switched-off
   provider and answers its pair as for an unknown code; the search never asks one by default and answers a request that
   names one as an unknown code; the plugin settings serve no switched-off plugin (catalogue, writes ``UNKNOWN_FIELD``,
   readiness ``(True, ())``); a shared group whose every reader is off is not served (catalogue, writes ``UNKNOWN_FIELD``);
   with one reader on it is listed and ``used_by`` names the readers that are on; a test-only plugin is switched off by
   an allow-list that does not name it, in test mode too.

Red on HEAD 7534fd6f3: the two config functions, the hook and its filtering do not exist. Every test imports the new
names inside its body, or reaches the missing behaviour through an existing name, so each one fails for its own reason;
every assertion that only proves the scenario is set up says ``barrier:``.

Pure: no lane DB, no server, no network. Every variable through ``monkeypatch``; a private SQLite file under
``tmp_path`` behind every ``get_async_engine`` the paths touch; extra plugins are put in the real registries' storage with
``monkeypatch.setitem`` for the length of a test, or in throwaway registries that subclass the real ones (so they inherit
the hook); search queries are unique; the web link finder is off.
"""

from __future__ import annotations

import dataclasses
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel
from backend.app.db.models import Asset, AssetProviderAssignment, FxConversionRoute, FxRate, PriceHistory, ProviderInputType, User
from backend.app.schemas.plugin_settings import PluginSettingErrorCode, PluginSettingWriteItem
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncStatus
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService
from backend.app.services.fx import sync as fx_sync
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.platform import provider_registry
from backend.app.services.platform.provider_registry import AbstractProviderRegistry
from backend.app.services.plugin_settings import readiness, runtime, service
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group

ASSET_VARIABLE = "LIBREFOLIO_ASSET_PROVIDERS_ENABLED"
FX_VARIABLE = "LIBREFOLIO_FX_PROVIDERS_ENABLED"
INSTANCE_KEY = "LibreFolio-providers-enabled-test-key-0123456789"
LOG_CANARY = "providers enabled test: the capture reaches the registry's logger"
#: The asset plugins shipped today that are not test-only: a barrier for the cases that read the real registry.
SHIPPED_ASSET = frozenset({"borsa_italiana", "css_scraper", "justetf", "scheduled_investment", "yfinance"})
GROUP = "x1_grp"

KEY_FIELD = PluginSettingField(key="api_key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="API key (x1)", secret=True, required=True)
PLAN_FIELD = PluginSettingField(key="plan", type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Plan (x1)", default="free", options=(SettingOption("free", "Free"), SettingOption("paid", "Paid")))


def _unique(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


# =============================================================================
# THROWAWAY REGISTRIES AND PLUGINS
# =============================================================================


class _AssetLab(AssetProviderRegistry):
    """A throwaway asset registry: it inherits the allow-list of ``AssetProviderRegistry``, not its storage."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "x1_providers_enabled_lab_assets"


class _PlainLab(AbstractProviderRegistry):
    """A registry with no allow-list of its own: the base's defaults."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "x1_providers_enabled_lab_plain"


def _settings_plugin(code: str, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = ()) -> type:
    return type(f"X1Plugin_{code}", (PluginSettingsMixin,), {"provider_code": code, "provider_name": f"Plugin {code}", "settings_fields": fields, "settings_groups": groups})


def _asset_clone(code: str) -> type:
    """A listed (not test-only) asset provider: the mock, under another code, with no settings."""
    return type(f"X1Asset_{code}", (MockProvider,), {"provider_code": property(lambda self: code), "provider_name": f"X1 {code}", "test_only": False, "settings_fields": (), "settings_groups": ()})


def _fx_clone(code: str, calls: list[str] | None = None) -> type:
    """A listed (not test-only) FX provider: the mock, under another code, with no settings; ``calls`` records each
    ``fetch_rates`` it answers."""

    async def fetch_rates(self, date_range, currencies, base_currency=None):
        if calls is not None:
            calls.append(code)
        return await MockFXProvider.fetch_rates(self, date_range, currencies, base_currency)

    return type(f"X1Fx_{code}", (MockFXProvider,), {"code": property(lambda self: code), "name": property(lambda self: f"X1 {code}"), "test_only": False, "settings_fields": (), "fetch_rates": fetch_rates})


# =============================================================================
# FIXTURES
# =============================================================================


def _reset_unknown_reports() -> None:
    """Empty the once-per-process memory of the unknown codes (pinned name; absent on HEAD)."""
    hook = getattr(provider_registry, "_report_unknown_enabled", None)
    if hook is not None and hasattr(hook, "cache_clear"):
        hook.cache_clear()


@pytest.fixture(autouse=True)
def x1_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode, a data directory and an instance key of this test, the self-hosted profile, neither allow-list nor
    search override inherited, the link finder off; the once-only report and the x1 groups start over."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", INSTANCE_KEY)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setenv("LIBREFOLIO_WEB_LINK_FINDER_ENABLED", "0")
    for variable in (ASSET_VARIABLE, FX_VARIABLE, "LIBREFOLIO_ASSET_PROVIDERS_PREMIUM", "LIBREFOLIO_ASSET_PROVIDERS_ORDER"):
        monkeypatch.delenv(variable, raising=False)
    _reset_unknown_reports()
    yield
    _reset_unknown_reports()
    for name in [name for name in all_groups() if name.startswith("x1")]:
        release_group(name)


@pytest_asyncio.fixture
async def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file, behind every ``get_async_engine`` the paths under test open a session with."""
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'providers_enabled.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        for module in (runtime, readiness, fx_sync):
            monkeypatch.setattr(module, "get_async_engine", lambda: private)
        yield private
    finally:
        await private.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as opened:
        yield opened


@pytest_asyncio.fixture
async def admin(engine: AsyncEngine) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as opened:
        user = User(username=_unique("x1admin"), email=f"{_unique('x1')}@example.test", hashed_password="$argon2id$test", is_superuser=True)
        opened.add(user)
        await opened.commit()
    return user


@pytest.fixture
def asset_lab(monkeypatch: pytest.MonkeyPatch) -> Callable[[type], None]:
    """The plugin settings read the asset family from ``_AssetLab``; ``add(plugin_class)`` fills it."""
    store: dict[str, type] = {}
    monkeypatch.setattr(_AssetLab, "_providers", store)
    monkeypatch.setattr(_AssetLab, "_discovery_done", True)
    monkeypatch.setitem(service.FAMILY_REGISTRIES, "asset", _AssetLab)

    def add(plugin_class: type) -> None:
        store[plugin_class.provider_code] = plugin_class

    return add


def _put(monkeypatch: pytest.MonkeyPatch, registry: type, code: str, plugin_class: type) -> None:
    """``plugin_class`` in the real ``registry`` under ``code`` for the length of the test."""
    registry.auto_discover()
    monkeypatch.setitem(registry._get_storage(), registry._normalize_lookup_code(code), plugin_class)


def _codes(registry: type) -> set[str]:
    return {item["code"] for item in registry.list_providers()}


# =============================================================================
# 1. CONFIG
# =============================================================================


@pytest.mark.parametrize(("function", "variable"), [("asset_providers_enabled", ASSET_VARIABLE), ("fx_providers_enabled", FX_VARIABLE)])
def test_x1_each_allow_list_is_read_at_every_call(function: str, variable: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """1: comma-separated, stripped, lowercased, in order, each once; None unset, blank or only commas; never cached."""
    from backend.app.config import plugins as plugin_config

    read = getattr(plugin_config, function)
    assert read() is None
    for blank in ("", "   ", " , ,,"):
        monkeypatch.setenv(variable, blank)
        assert read() is None, f"{blank!r} lists no code: all providers stay on"
    monkeypatch.setenv(variable, " YFinance , justetf,yfinance ,, ECB")
    assert read() == ("yfinance", "justetf", "ecb")
    monkeypatch.setenv(variable, "Css_Scraper")
    assert read() == ("css_scraper",), "read at every call: a change of the variable is seen without a restart"


# =============================================================================
# 2. THE REGISTRY HOOK
# =============================================================================


def test_x1_a_registry_without_an_allow_list_switches_nothing_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: the base's defaults: no codes, no variable, nothing always on, nothing switched off."""
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    monkeypatch.setenv(FX_VARIABLE, "ecb")
    assert _PlainLab._enabled_codes() is None
    assert _PlainLab._enabled_variable() is None
    assert _PlainLab._always_enabled() == frozenset()
    assert _PlainLab._switched_off("justetf") is False and _PlainLab._switched_off("FED") is False


def test_x1_each_family_reads_its_own_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: the asset registry reads LIBREFOLIO_ASSET_PROVIDERS_ENABLED, the FX one LIBREFOLIO_FX_PROVIDERS_ENABLED and
    keeps MANUAL always on; the codes are the config's."""
    from backend.app.config.plugins import asset_providers_enabled, fx_providers_enabled

    assert AssetProviderRegistry._enabled_variable() == ASSET_VARIABLE
    assert FXProviderRegistry._enabled_variable() == FX_VARIABLE
    assert AssetProviderRegistry._always_enabled() == frozenset()
    assert FXProviderRegistry._always_enabled() == frozenset({"manual"})
    assert AssetProviderRegistry._enabled_codes() is None and FXProviderRegistry._enabled_codes() is None
    monkeypatch.setenv(ASSET_VARIABLE, "YFinance,justetf")
    monkeypatch.setenv(FX_VARIABLE, "Ecb")
    assert AssetProviderRegistry._enabled_codes() == asset_providers_enabled() == ("yfinance", "justetf")
    assert FXProviderRegistry._enabled_codes() == fx_providers_enabled() == ("ecb",)


def test_x1_switched_off_compares_codes_in_any_case(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: ``_switched_off`` lowercases the code; unset, nothing is off; FX MANUAL is never off."""
    assert AssetProviderRegistry._switched_off("justetf") is False and FXProviderRegistry._switched_off("FED") is False
    monkeypatch.setenv(ASSET_VARIABLE, "YFinance")
    monkeypatch.setenv(FX_VARIABLE, "Ecb")
    assert [AssetProviderRegistry._switched_off(code) for code in ("yfinance", "YFINANCE", "justetf")] == [False, False, True]
    assert [FXProviderRegistry._switched_off(code) for code in ("ECB", "ecb", "FED", "MANUAL", "manual")] == [False, False, True, False, False]


def test_x1_the_asset_lookups_leave_a_switched_off_provider_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: listed ``YFinance``: yfinance found and listed; justetf not found, not instantiated, not listed. Blank → all."""
    assert SHIPPED_ASSET <= set(AssetProviderRegistry.list_plugin_codes()) and SHIPPED_ASSET <= _codes(AssetProviderRegistry), "barrier: unset, every shipped provider is on"
    monkeypatch.setenv(ASSET_VARIABLE, "YFinance")
    assert AssetProviderRegistry.get_plugin("yfinance") is not None and AssetProviderRegistry.get_provider_instance("yfinance") is not None
    assert "yfinance" in AssetProviderRegistry.list_plugin_codes() and "yfinance" in _codes(AssetProviderRegistry)
    assert AssetProviderRegistry.get_plugin("justetf") is None
    assert AssetProviderRegistry.get_plugin_instance("justetf") is None and AssetProviderRegistry.get_provider_instance("justetf") is None
    assert "justetf" not in AssetProviderRegistry.list_plugin_codes()
    assert _codes(AssetProviderRegistry) & SHIPPED_ASSET == {"yfinance"}
    for blank in ("", " ,, "):
        monkeypatch.setenv(ASSET_VARIABLE, blank)
        assert AssetProviderRegistry.get_plugin("justetf") is not None and SHIPPED_ASSET <= _codes(AssetProviderRegistry), f"{blank!r}: all on"


def test_x1_the_fx_lookups_leave_a_switched_off_provider_out_and_keep_manual(monkeypatch: pytest.MonkeyPatch) -> None:
    """2: listed ``ecb`` (any case against the registered ``ECB``): ECB and MANUAL on, FED off."""
    assert {"ECB", "FED", "MANUAL"} <= _codes(FXProviderRegistry), "barrier: unset, ECB, FED and MANUAL are on"
    monkeypatch.setenv(FX_VARIABLE, "ecb")
    assert FXProviderRegistry.get_plugin("ECB") is not None and "ECB" in FXProviderRegistry.list_plugin_codes() and "ECB" in _codes(FXProviderRegistry)
    assert FXProviderRegistry.get_plugin("MANUAL") is not None and FXProviderRegistry.get_provider_instance("MANUAL") is not None
    assert "MANUAL" in FXProviderRegistry.list_plugin_codes() and "MANUAL" in _codes(FXProviderRegistry)
    assert FXProviderRegistry.get_plugin("FED") is None and FXProviderRegistry.get_provider_instance("FED") is None
    assert "FED" not in FXProviderRegistry.list_plugin_codes() and "FED" not in _codes(FXProviderRegistry)


def test_x1_a_test_only_plugin_not_listed_is_switched_off_in_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """2 / 3: in test mode an allow-list that does not name mockprov or MOCKFX switches them off too."""
    assert AssetProviderRegistry.get_plugin("mockprov") is not None and FXProviderRegistry.get_plugin("MOCKFX") is not None, "barrier: in test mode the mocks are served"
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    monkeypatch.setenv(FX_VARIABLE, "ecb")
    assert AssetProviderRegistry.get_plugin("mockprov") is None and "mockprov" not in AssetProviderRegistry.list_plugin_codes()
    assert FXProviderRegistry.get_plugin("MOCKFX") is None and "MOCKFX" not in _codes(FXProviderRegistry)
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance,MockProv")
    assert AssetProviderRegistry.get_plugin("mockprov") is not None, "named, the test-only one is on in test mode"


# -----------------------------------------------------------------------------
# Unknown codes: ignored, logged once
# -----------------------------------------------------------------------------


@dataclasses.dataclass
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


def _look_up_three_times(registry: type, codes: tuple[str, ...]) -> None:
    for _ in range(3):
        registry.list_plugin_codes()
        registry.list_providers()
        for code in codes:
            registry.get_plugin(code)


def test_x1_an_unknown_asset_code_is_ignored_and_logged_once(monkeypatch: pytest.MonkeyPatch, captured: _Captured) -> None:
    """2: ``yfinance,<unknown>``: yfinance alone is on, and the unknown code is one warning however many lookups."""
    unknown = _unique("x1_nosuch_")
    monkeypatch.setenv(ASSET_VARIABLE, f"yfinance,{unknown.upper()}")
    _look_up_three_times(AssetProviderRegistry, ("yfinance", "justetf"))
    assert AssetProviderRegistry.get_plugin("yfinance") is not None and AssetProviderRegistry.get_plugin("justetf") is None
    assert captured.reports(ASSET_VARIABLE) == [("warning", [unknown])]


def test_x1_an_unknown_fx_code_is_ignored_and_logged_once(monkeypatch: pytest.MonkeyPatch, captured: _Captured) -> None:
    """2: ``Ecb,<unknown>``: ``Ecb`` is known (case-insensitive) and not reported; the unknown one is, once."""
    unknown = _unique("x1nosuchfx")
    monkeypatch.setenv(FX_VARIABLE, f"Ecb,{unknown}")
    _look_up_three_times(FXProviderRegistry, ("ECB", "FED"))
    assert FXProviderRegistry.get_plugin("ECB") is not None and FXProviderRegistry.get_plugin("FED") is None
    assert captured.reports(FX_VARIABLE) == [("warning", [unknown])]


def test_x1_a_test_only_code_outside_test_mode_counts_as_unknown(monkeypatch: pytest.MonkeyPatch, captured: _Captured) -> None:
    """2: outside test mode ``mockprov`` is withheld (X-R44): listed, it is an unknown code, logged once."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance,mockprov")
    _look_up_three_times(AssetProviderRegistry, ("yfinance", "mockprov"))
    assert AssetProviderRegistry.get_plugin("mockprov") is None, "barrier: outside test mode mockprov is withheld"
    assert captured.reports(ASSET_VARIABLE) == [("warning", ["mockprov"])]


# =============================================================================
# 3. EFFECTS: THE PROVIDER LISTS
# =============================================================================


async def _always_ready(family: str, codes: Any, *, user_id: int | None) -> dict[str, Any]:
    from backend.app.services.plugin_settings.readiness import PluginReadiness

    return {code: PluginReadiness(True, ()) for code in codes}


@pytest.mark.asyncio
async def test_x1_the_asset_provider_list_omits_a_switched_off_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: ``GET /assets/provider`` lists the listed provider and not the other one."""
    from backend.app.api.v1.assets import providers as asset_routes

    monkeypatch.setattr(asset_routes, "plugins_readiness", _always_ready)
    for code in ("x1_on", "x1_off"):
        _put(monkeypatch, AssetProviderRegistry, code, _asset_clone(code))

    async def listed() -> set[str]:
        return {item.code for item in await asset_routes.list_providers(providers="x1_on,x1_off", _current_user=SimpleNamespace(id=1))}

    assert await listed() == {"x1_on", "x1_off"}, "barrier: unset, both are listed"
    monkeypatch.setenv(ASSET_VARIABLE, "x1_on")
    assert await listed() == {"x1_on"}


@pytest.mark.asyncio
async def test_x1_the_fx_provider_list_omits_a_switched_off_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: ``GET /fx/providers`` lists the listed provider and not the other one (listed lowercase, registered uppercase)."""
    from backend.app.api.v1.fx import providers as fx_routes

    monkeypatch.setattr(fx_routes, "plugins_readiness", _always_ready)
    for code in ("X1FXON", "X1FXOFF"):
        _put(monkeypatch, FXProviderRegistry, code, _fx_clone(code))

    async def listed() -> set[str]:
        return {item.code for item in await fx_routes.list_providers(providers=["X1FXON", "X1FXOFF"], _current_user=SimpleNamespace(id=1))}

    assert await listed() == {"X1FXON", "X1FXOFF"}, "barrier: unset, both are listed"
    monkeypatch.setenv(FX_VARIABLE, "x1fxon")
    assert await listed() == {"X1FXON"}


# =============================================================================
# 3. EFFECTS: ASSIGNMENTS AND ROUTES
# =============================================================================


def _refusal(code: str) -> str:
    """The message the assignment item answers for ``code``, with the code replaced: the shape of the refusal."""
    with pytest.raises(ValidationError) as refused:
        FAProviderAssignmentItem(asset_id=1, provider_code=code, identifier="AAPL", identifier_type="TICKER")
    return "; ".join(error["msg"] for error in refused.value.errors()).replace(code, "<code>")


def test_x1_assigning_a_switched_off_provider_is_refused_like_an_unknown_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: the item naming a switched-off provider never builds (so nothing is written), with the unknown code's message."""
    item = FAProviderAssignmentItem(asset_id=1, provider_code="yfinance", identifier="AAPL", identifier_type="TICKER")
    assert item.provider_code == "yfinance", "barrier: unset, yfinance can be assigned"
    unknown = _refusal(_unique("x1_nosuch_"))
    assert "Unknown provider" in unknown, f"barrier: today's answer to an unknown code: {unknown}"
    monkeypatch.setenv(ASSET_VARIABLE, "mockprov")
    assert FAProviderAssignmentItem(asset_id=1, provider_code="mockprov", identifier="AAPL", identifier_type="TICKER").provider_code == "mockprov"
    assert _refusal("yfinance") == unknown


async def _post_routes(session: AsyncSession, *items: tuple[str, str, int, str]) -> Any:
    """``POST /fx/providers/routes`` in process, one single-step route per ``(base, quote, priority, provider)``."""
    from backend.app.api.v1.fx.providers import create_routes_bulk
    from backend.app.schemas.fx import FXConversionRouteItem

    routes = [FXConversionRouteItem(base=base, quote=quote, priority=priority, chain_steps=[{"from": base, "to": quote, "provider": provider}]) for base, quote, priority, provider in items]
    return await create_routes_bulk(routes, replace=False, session=session, _current_user=SimpleNamespace(id=1))


async def _route_refusal(session: AsyncSession, provider: str) -> tuple[int, list[dict[str, Any]]]:
    with pytest.raises(HTTPException) as refused:
        await _post_routes(session, ("EUR", "USD", 1, provider))
    return refused.value.status_code, json.loads(json.dumps(refused.value.detail["results"], default=str).replace(provider, "<code>"))


@pytest.mark.asyncio
async def test_x1_a_route_naming_a_switched_off_provider_is_refused_like_an_unknown_code(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: listed ``ecb``: a FED route answers as an unknown code; ECB and MANUAL routes are accepted."""
    unknown = await _route_refusal(session, _unique("X1NOSUCH").upper())
    assert unknown[0] == 400 and "Unknown provider" in unknown[1][0]["message"], f"barrier: today's answer to an unknown code: {unknown}"
    monkeypatch.setenv(FX_VARIABLE, "ecb")
    assert await _route_refusal(session, "FED") == unknown
    accepted = await _post_routes(session, ("EUR", "USD", 1, "ECB"), ("EUR", "JPY", 999, "MANUAL"))
    assert (accepted.success_count, accepted.error_count) == (2, 0), accepted
    monkeypatch.delenv(FX_VARIABLE)
    assert (await _post_routes(session, ("EUR", "CHF", 1, "FED"))).success_count == 1, "barrier: unset, FED is accepted"


# =============================================================================
# 3. EFFECTS: AN EXISTING ASSIGNMENT
# =============================================================================


STORED_CLOSE = Decimal("42.5")
STORED_DAY = date(2020, 1, 6)


async def _assigned_asset(session: AsyncSession, provider_code: str) -> int:
    """An asset of this test assigned to ``provider_code`` (unique identifier), with one stored price."""
    asset = Asset(display_name=_unique("X1 asset "), currency="USD")
    session.add(asset)
    await session.flush()
    session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=provider_code, identifier=_unique("X1ID"), identifier_type=ProviderInputType.TICKER))
    session.add(PriceHistory(asset_id=asset.id, date=STORED_DAY, close=STORED_CLOSE, currency="USD", source_plugin_key="MANUAL"))
    await session.commit()
    return asset.id


async def _prices_of(session: AsyncSession, asset_id: int) -> list[tuple[date, Decimal | None]]:
    return [(row.date, row.close) for row in (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date))).scalars()]


def _shape(item: Any) -> dict[str, Any]:
    return item.model_dump(exclude={"asset_id"})


@pytest.mark.asyncio
async def test_x1_the_current_price_of_a_switched_off_provider_is_the_stored_one(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: an asset still assigned to a switched-off provider answers as one assigned to an unknown code: the last stored
    price, no exception, no row written."""
    off_id = await _assigned_asset(session, "mockprov")
    unknown_id = await _assigned_asset(session, _unique("x1_nosuch_"))
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")

    unknown_item, off_item = await PriceQueryOperations.get_current_prices_bulk([unknown_id, off_id], session)
    assert unknown_item.source == "db:last_known" and unknown_item.value == STORED_CLOSE, f"barrier: today's answer for an unknown provider: {unknown_item}"
    assert _shape(off_item) == _shape(unknown_item)
    assert await _prices_of(session, off_id) == [(STORED_DAY, STORED_CLOSE)], "the stored price is untouched"

    monkeypatch.delenv(ASSET_VARIABLE)
    (live,) = await PriceQueryOperations.get_current_prices_bulk([off_id], session)
    assert live.source == "provider:mockprov", f"barrier: unset, mockprov answers: {live}"


@pytest.mark.asyncio
async def test_x1_the_refresh_of_a_switched_off_provider_answers_like_an_unknown_code(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: the refresh resolves no provider for an assignment to a switched-off one: the unknown code's result."""
    from backend.app.services.assets.refresh import _prepare_refresh_items

    off_id = await _assigned_asset(session, "mockprov")
    unknown_code = _unique("x1_nosuch_")
    unknown_id = await _assigned_asset(session, unknown_code)
    window = {"start": date(2020, 1, 1), "end": date(2020, 1, 10)}
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")

    prepared, immediate = await _prepare_refresh_items([FARefreshItem(asset_id=asset_id, date_range=window) for asset_id in (unknown_id, off_id)], session, time.monotonic_ns())
    by_asset = {result.asset_id: result for result in immediate}
    assert unknown_id in by_asset and unknown_id not in prepared, f"barrier: today an unknown provider is refused at preparation: {immediate}"

    def shape(result: Any, code: str) -> dict[str, Any]:
        return json.loads(json.dumps(result.model_dump(mode="json", exclude={"asset_id", "elapsed_ms"})).replace(code, "<code>"))

    assert off_id not in prepared and off_id in by_asset, f"a switched-off provider is not prepared: {list(prepared)}"
    assert shape(by_asset[off_id], "mockprov") == shape(by_asset[unknown_id], unknown_code)

    monkeypatch.delenv(ASSET_VARIABLE)
    prepared, _immediate = await _prepare_refresh_items([FARefreshItem(asset_id=off_id, date_range=window)], session, time.monotonic_ns())
    assert off_id in prepared, "barrier: unset, mockprov is prepared"


# =============================================================================
# 3. EFFECTS: THE FX SYNC
# =============================================================================


async def _set_routes(session: AsyncSession, *providers: str) -> None:
    """EUR-USD with one single-step route per provider, priority 1, 2, … in order; no stored rate."""
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == "EUR", FxConversionRoute.quote == "USD"))
    await session.execute(delete(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD"))
    for priority, provider in enumerate(providers, start=1):
        session.add(FxConversionRoute(base="EUR", quote="USD", priority=priority, chain_steps=json.dumps([{"from": "EUR", "to": "USD", "provider": provider}])))
    await session.commit()


@pytest.mark.asyncio
async def test_x1_the_fx_sync_never_asks_a_switched_off_provider(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: a pair whose first route uses a switched-off provider: that provider is never asked, and the pair answers as
    with an unknown code in its place (the existing skip of a leg whose provider is absent)."""
    calls: list[str] = []
    _put(monkeypatch, FXProviderRegistry, "X1FXA", _fx_clone("X1FXA", calls))
    day = date(2001, 3, 5) + timedelta(days=uuid.uuid4().int % 300)
    window = (day, day + timedelta(days=1))

    def shape(result: Any, code: str) -> dict[str, Any]:
        (pair,) = result.results
        return json.loads(json.dumps(pair.model_dump(mode="json", exclude={"elapsed_ms"})).replace(code, "<code>"))

    unknown_code = _unique("X1NOSUCH").upper()
    await _set_routes(session, unknown_code, "MOCKFX")
    unknown = await fx_sync.sync_pairs_bulk(session, ["EUR-USD"], window)
    assert unknown.results[0].status in (SyncStatus.OK, SyncStatus.PARTIAL), f"barrier: today an unknown first route still syncs the pair: {unknown}"

    monkeypatch.setenv(FX_VARIABLE, "mockfx")
    await _set_routes(session, "X1FXA", "MOCKFX")
    switched_off = await fx_sync.sync_pairs_bulk(session, ["EUR-USD"], window)
    assert calls == [], f"the switched-off provider was asked: {calls}"
    assert shape(switched_off, "X1FXA") == shape(unknown, unknown_code)

    monkeypatch.delenv(FX_VARIABLE)
    await _set_routes(session, "X1FXA", "MOCKFX")
    on = await fx_sync.sync_pairs_bulk(session, ["EUR-USD"], window)
    assert calls == ["X1FXA"] and on.results[0].provider_used == "X1FXA", f"barrier: unset, X1FXA serves the pair: {calls} {on}"


# =============================================================================
# 3. EFFECTS: THE SEARCH
# =============================================================================


@pytest.mark.asyncio
async def test_x1_the_search_without_providers_never_asks_a_switched_off_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """3: the default list of the search is the list of the providers on: justetf is never asked."""
    asked: list[str] = []

    async def configured_provider(code: str, *, user_id: int | None = None) -> None:
        asked.append(code)
        return None

    monkeypatch.setattr(core, "configured_provider", configured_provider)
    await AssetSearchService.search(_unique("x1 default list "))
    assert {"yfinance", "justetf"} <= set(asked), f"barrier: unset, the default list asks yfinance and justetf: {asked}"
    asked.clear()
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    await AssetSearchService.search(_unique("x1 default list "))
    assert asked == ["yfinance"]


@pytest.mark.asyncio
async def test_x1_a_search_naming_a_switched_off_provider_answers_like_an_unknown_code(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: ``provider_codes=["mockprov"]`` with an allow-list that does not name it: the unknown code's answer."""
    query = _unique("x1 named ")
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    unknown = await AssetSearchService.search(query, provider_codes=[_unique("x1_nosuch_")])
    assert unknown.providers_queried == [] and unknown.total_results == 0, f"barrier: today's answer to an unknown code: {unknown}"
    switched_off = await AssetSearchService.search(query, provider_codes=["mockprov"])
    assert switched_off.model_dump() == unknown.model_dump()

    monkeypatch.delenv(ASSET_VARIABLE)
    on = await AssetSearchService.search(_unique("x1 named "), provider_codes=["mockprov"])
    assert on.providers_queried == ["mockprov"], f"barrier: unset, mockprov is asked: {on}"


# =============================================================================
# 3. EFFECTS: THE PLUGIN SETTINGS
# =============================================================================


def _write(family: str, code: str, key: str, value: str) -> PluginSettingWriteItem:
    return PluginSettingWriteItem(family=family, plugin_code=code, field_key=key, scope="system", value=value)


async def _write_error(session: AsyncSession, user: User, item: PluginSettingWriteItem) -> PluginSettingErrorCode | None:
    """The error code of a write of one item; None when it is written."""
    try:
        await service.write_settings(session, user, [item])
    except service.PluginSettingsRefused as refused:
        return refused.results[0].error_code
    return None


async def _entries(session: AsyncSession, user: User, **filters: Any) -> dict[tuple[str, str], Any]:
    catalogue = await service.read_catalogue(session, user, **filters)
    return {(entry.family, entry.plugin_code): entry for entry in catalogue.plugins}


@pytest.mark.asyncio
async def test_x1_a_switched_off_plugin_has_no_settings(session: AsyncSession, admin: User, monkeypatch: pytest.MonkeyPatch) -> None:
    """3: mockprov named, with an allow-list that does not name it: absent from the catalogue, a write is UNKNOWN_FIELD."""
    assert ("asset", "mockprov") in await _entries(session, admin, family="asset", plugin_code="mockprov"), "barrier: unset, mockprov has settings"
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    assert await _entries(session, admin, family="asset", plugin_code="mockprov") == {}
    assert await _write_error(session, admin, _write("asset", "mockprov", "region", "us")) == PluginSettingErrorCode.UNKNOWN_FIELD


@pytest.mark.asyncio
async def test_x1_a_switched_off_plugin_is_out_of_the_catalogue_and_ready(session: AsyncSession, admin: User, asset_lab: Callable[[type], None], monkeypatch: pytest.MonkeyPatch) -> None:
    """3: a plugin that needs a key, switched off: not in the catalogue's default list, and readiness answers
    ``(True, ())``, as for an unknown code."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugin_readiness, plugins_readiness

    asset_lab(_settings_plugin("x1_keyed", (KEY_FIELD,)))
    asset_lab(_settings_plugin("x1_other", (PLAN_FIELD,)))
    assert {("asset", "x1_keyed"), ("asset", "x1_other")} <= set(await _entries(session, admin, family="asset")), "barrier: unset, both are listed"
    assert await plugins_readiness("asset", ["x1_keyed"], user_id=None) == {"x1_keyed": PluginReadiness(False, ("api_key",))}, "barrier: unset, x1_keyed lacks its key"

    monkeypatch.setenv(ASSET_VARIABLE, "x1_other")
    entries = await _entries(session, admin, family="asset")
    assert ("asset", "x1_other") in entries and ("asset", "x1_keyed") not in entries
    assert await plugins_readiness("asset", ["x1_keyed", "x1_other"], user_id=None) == {"x1_keyed": PluginReadiness(True, ()), "x1_other": PluginReadiness(True, ())}
    assert await plugin_readiness("asset", "x1_keyed", user_id=None) == PluginReadiness(True, ())


@pytest.mark.asyncio
async def test_x1_a_group_whose_readers_are_all_off_is_not_served(session: AsyncSession, admin: User, monkeypatch: pytest.MonkeyPatch) -> None:
    """3 (decision for groups): the test-only group ``mock`` is read by mockprov alone; mockprov off, the group is absent
    even when named, and a write to it is UNKNOWN_FIELD."""
    named = await _entries(session, admin, family="group", plugin_code="mock")
    assert ("group", "mock") in named and [ref.plugin_code for ref in named[("group", "mock")].used_by] == ["mockprov"], f"barrier: unset, mock is served, read by mockprov: {named}"
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    assert await _entries(session, admin, family="group", plugin_code="mock") == {}
    assert await _write_error(session, admin, _write("group", "mock", "tier", "paid")) == PluginSettingErrorCode.UNKNOWN_FIELD


@pytest.mark.asyncio
async def test_x1_a_group_with_one_reader_on_names_only_the_readers_on(session: AsyncSession, admin: User, asset_lab: Callable[[type], None], monkeypatch: pytest.MonkeyPatch) -> None:
    """3 (decision for groups): a group read by two plugins, one listed: still served, ``used_by`` names that one; both
    off: not served, a write is UNKNOWN_FIELD."""
    register_group(SettingsGroup(name=GROUP, label="Group x1", fields=(PLAN_FIELD,)))
    asset_lab(_settings_plugin("x1_reader_on", (), (GROUP,)))
    asset_lab(_settings_plugin("x1_reader_off", (), (GROUP,)))

    async def readers() -> list[str] | None:
        entry = (await _entries(session, admin, family="group", plugin_code=GROUP)).get(("group", GROUP))
        return None if entry is None else sorted(ref.plugin_code for ref in entry.used_by)

    assert await readers() == ["x1_reader_off", "x1_reader_on"], "barrier: unset, both readers are named"
    monkeypatch.setenv(ASSET_VARIABLE, "x1_reader_on")
    assert await readers() == ["x1_reader_on"]
    assert await _write_error(session, admin, _write("group", GROUP, "plan", "paid")) is None, "one reader on: the group is written"
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    assert await readers() is None
    assert await _write_error(session, admin, _write("group", GROUP, "plan", "free")) == PluginSettingErrorCode.UNKNOWN_FIELD


# =============================================================================
# 4. FACTS ABOUT ROWS ALREADY STORED (from the review)
# =============================================================================


def test_x1_leaving_a_switched_off_parametric_provider_still_wipes_its_invented_series(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review: the kind of a stored provider is a fact about the row, not a way to serve it. An asset assigned to
    ``scheduled_investment`` (parametric: its series is invented from the params) and moved to ``yfinance`` while the
    allow-list switches ``scheduled_investment`` off still has that series wiped (#R3-4), as when the list is unset; and
    new params on it still count as a change. Otherwise the fiction would stay and poison the next sync."""
    from backend.app.services.assets.provider_management import _wipe_reason

    assert _wipe_reason("scheduled_investment", "{}", "yfinance", None) == "provider changed", "barrier: no allow-list"
    monkeypatch.setenv(ASSET_VARIABLE, "yfinance")
    assert AssetProviderRegistry.get_plugin("scheduled_investment") is None, "barrier: switched off"

    assert _wipe_reason("scheduled_investment", "{}", "yfinance", None) == "provider changed"
    assert _wipe_reason("scheduled_investment", '{"a": 1}', "scheduled_investment", '{"a": 2}') == "params changed"

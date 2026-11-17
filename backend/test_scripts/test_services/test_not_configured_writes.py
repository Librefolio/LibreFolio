"""Plugin settings, the writes that would put an unconfigured plugin to use are refused (project 76, lot N2).

Routes under test, called in process: ``POST /assets/provider`` (``api/v1/assets/providers.assign_providers_bulk`` →
``AssetSourceManager.bulk_assign_providers``) and ``POST /fx/providers/routes`` (``api/v1/fx/providers.create_routes_bulk``,
with ``replace``). The contract pinned here:

1. **Assets.** Before anything is written, the items whose provider is NEWLY put to use on their asset (the asset has no
   stored assignment, or its stored assignment names another provider) are checked with ONE
   ``plugins_readiness("asset", codes, user_id=<caller>)``. Any of them not configured → the whole request is refused with
   ``not_configured_error(code, missing)`` (``api/plugin_errors.py``: 422, ``detail = {"error_code": "NOT_CONFIGURED",
   "message", "missing"}``) for the FIRST such item in request order; nothing written: no assignment created or changed for
   any item, the stored ones untouched, no price wiped. An item that re-saves the provider its asset already has (params
   changed or not) is not refused even when that provider is not configured (no clean-up, plan 76 §3.9). A configured
   provider, and one that declares no settings, pass as today.
2. **FX routes.** Before anything is written, every non-MANUAL step provider of every posted route that is NEW for its
   pair (the pair normalised as the endpoint does, ``(min(base, quote), max(base, quote))`` upper-cased, has no stored route
   whose steps name that provider) is checked with ONE ``plugins_readiness("fx", codes, user_id=<caller>)``. Any not
   configured → the whole request refused with ``not_configured_error(code, missing)`` for the first in request order
   (route order, then step order); nothing written: no route created, replaced or deleted, also with ``?replace=true``,
   the MANUAL route untouched. A provider a stored route of that pair already names passes even if not configured.
   Unknown provider codes keep today's per-item 400 (readiness answers «ready» for an unknown code).
3. **Order of checks.** After the request's own validation (the schema's error for an unknown asset provider code stays),
   before any write.
4. **Managed profile.** ``missing`` never names a field an environment variable locks (it is ``PluginReadiness.missing``),
   and the request is still refused.

Red on HEAD 5d9936d0f: neither route asks the readiness check, so every refusal test finds its write done (or no 422) and
every spy test counts zero calls. The guards (re-save passes, a provider already on the pair passes, configured and
setting-less providers pass, unknown codes keep their error) are green before and after N2.

How: a private SQLite engine under ``tmp_path`` handed to the routes as their session and to the readiness check
(``readiness.get_async_engine`` and ``runtime.get_async_engine`` are replaced); the REAL asset and FX registries receive
this module's provider classes (subclasses of the mock providers, test-only off, settings of the test) for the length of a
test, because the assignment schema, ``_is_parametric`` and the FX route read those registries directly; a test instance
key; every variable through ``monkeypatch``. No server, no network. Every code starts with ``n2``/``N2``.

No API test on the shared backend: the only test-only plugins it serves (``mockprov`` and its ``mock`` group, ``MOCKFX``)
declare no required field, so a «not configured» provider there needs a product declaration changed under the
neighbours' feet.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.plugin_errors import not_configured_error
from backend.app.api.v1.assets import providers as asset_routes
from backend.app.api.v1.fx import providers as fx_routes
from backend.app.db.base import SQLModel
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, FxConversionRoute, PluginSystemSetting, PriceHistory, ProviderInputType, User
from backend.app.schemas.fx import FXConversionRouteItem
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderKind
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import provider_management
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.plugin_settings import readiness, resolver, runtime
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name
from backend.app.services.plugin_settings.readiness import PluginReadiness
from backend.test_scripts.test_utils import print_section, print_success

KEY = "LibreFolio-not-configured-writes-test-key-0123456789"
SYSTEM = SettingScope.SYSTEM
KEY_FIELD = PluginSettingField(key="api_key", type=SettingType.STRING, scope=SYSTEM, label="API key (n2)", secret=True, required=True)
ENDPOINT_FIELD = PluginSettingField(key="endpoint", type=SettingType.STRING, scope=SYSTEM, label="Endpoint (n2)", required=True)
REGION_FIELD = PluginSettingField(key="region", type=SettingType.SELECT, scope=SYSTEM, label="Region (n2)", default="eu", options=(SettingOption("eu", "EU"), SettingOption("us", "US")))

# Asset providers. «ok»: key stored; «plain»: declares nothing; «key»/«zeta»/«alpha»: unconfigured (zeta sorts after alpha).
A_OK, A_PLAIN, A_KEY, A_ZETA, A_ALPHA, A_PARAM, A_MANAGED = "n2_ok", "n2_plain", "n2_key", "n2_zeta", "n2_alpha", "n2_param", "n2_managed"
# FX providers, upper-case as the route's steps are.
F_OK, F_PLAIN, F_KEY, F_ZETA, F_ALPHA = "N2FXOK", "N2FXPLAIN", "N2FXKEY", "N2FXZETA", "N2FXALPHA"


# =============================================================================
# PLUGINS, FIXTURES AND ROWS
# =============================================================================


def _asset_plugin(code: str, fields: tuple = (), *, parametric: bool = False) -> type:
    """A listed asset provider: the mock under another code, with the settings of the test and no group."""
    attributes: dict[str, Any] = {"provider_code": property(lambda self: code), "provider_name": f"N2 {code}", "test_only": False, "settings_fields": fields, "settings_groups": ()}
    if parametric:
        attributes["provider_kind"] = property(lambda self: FAProviderKind.PARAMETRIC_GENERATION)
    return type(f"N2Asset_{code}", (MockProvider,), attributes)


def _fx_plugin(code: str, fields: tuple = ()) -> type:
    return type(f"N2Fx_{code}", (MockFXProvider,), {"code": property(lambda self: code), "name": property(lambda self: f"N2 {code}"), "test_only": False, "settings_fields": fields, "settings_groups": ()})


_ASSET_PLUGINS = {
    A_OK: _asset_plugin(A_OK, (KEY_FIELD,)),
    A_PLAIN: _asset_plugin(A_PLAIN),
    A_KEY: _asset_plugin(A_KEY, (KEY_FIELD,)),
    A_ZETA: _asset_plugin(A_ZETA, (KEY_FIELD,)),
    A_ALPHA: _asset_plugin(A_ALPHA, (ENDPOINT_FIELD,)),
    A_PARAM: _asset_plugin(A_PARAM, parametric=True),
    A_MANAGED: _asset_plugin(A_MANAGED, (ENDPOINT_FIELD, REGION_FIELD)),
}
_FX_PLUGINS = {
    F_OK: _fx_plugin(F_OK, (KEY_FIELD,)),
    F_PLAIN: _fx_plugin(F_PLAIN),
    F_KEY: _fx_plugin(F_KEY, (KEY_FIELD,)),
    F_ZETA: _fx_plugin(F_ZETA, (KEY_FIELD,)),
    F_ALPHA: _fx_plugin(F_ALPHA, (ENDPOINT_FIELD,)),
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A test instance key, a data directory of this test, the self-hosted profile, no ambient variable of this module's plugins."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    for family, plugins in (("asset", _ASSET_PLUGINS), ("fx", _FX_PLUGINS)):
        for code in plugins:
            for field in ("api_key", "endpoint", "region"):
                monkeypatch.delenv(env_name(family, code, field), raising=False)
                monkeypatch.delenv(env_name(family, code, field) + "_FILE", raising=False)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])


@pytest_asyncio.fixture
async def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """The private database: the routes get it as their session, the readiness check (and the runtime) as their engine."""
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'n2.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(runtime, "get_async_engine", lambda: private)
        monkeypatch.setattr(readiness, "get_async_engine", lambda: private)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def registries(monkeypatch: pytest.MonkeyPatch) -> None:
    """This module's providers in the REAL registries, for the length of the test."""
    AssetProviderRegistry.auto_discover()
    FXProviderRegistry.auto_discover()
    for registry, plugins in ((AssetProviderRegistry, _ASSET_PLUGINS), (FXProviderRegistry, _FX_PLUGINS)):
        storage = registry._get_storage()
        for code, plugin_class in plugins.items():
            monkeypatch.setitem(storage, registry._normalize_lookup_code(code), plugin_class)


@pytest_asyncio.fixture
async def caller(engine: AsyncEngine) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="n2_caller", email="n2_caller@example.test", hashed_password="$argon2id$test")
        session.add(user)
        await session.commit()
    return user


@pytest_asyncio.fixture
async def configured(engine: AsyncEngine, registries: None) -> None:
    """``n2_ok`` and ``N2FXOK`` have their key stored; every other provider of this module is left as declared."""
    await _store(engine, _secret_row("asset", A_OK, "api_key"), _secret_row("fx", F_OK, "api_key"))


class _ReadinessSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], int | None]] = []


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _ReadinessSpy:
    """Records every ``plugins_readiness`` call, wherever the routes or the assignment service hold the name."""
    recorder = _ReadinessSpy()
    original = readiness.plugins_readiness

    async def recording(family: str, codes: Any, *, user_id: int | None):
        recorder.calls.append((family, list(codes), user_id))
        return await original(family, codes, user_id=user_id)

    monkeypatch.setattr(readiness, "plugins_readiness", recording)
    for module in (asset_routes, fx_routes, provider_management):
        monkeypatch.setattr(module, "plugins_readiness", recording, raising=False)
    return recorder


def _secret_row(family: str, code: str, key: str) -> PluginSystemSetting:
    subkey = settings_subkey()
    blob = encrypt_secret(subkey, secret_aad(family, code, key, "system", None), "a-secret-value")
    return PluginSystemSetting(family=family, plugin_code=code, field_key=key, secret_ciphertext=blob, key_id=key_id_of(subkey))


async def _store(engine: AsyncEngine, *rows: Any) -> None:
    async with AsyncSession(engine) as session:
        session.add_all(rows)
        await session.commit()


async def _assets(engine: AsyncEngine, count: int) -> list[int]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = [Asset(display_name=f"N2 asset {index}", currency="EUR", asset_type=AssetType.STOCK) for index in range(count)]
        session.add_all(rows)
        await session.commit()
        return [row.id for row in rows]


def _stored_assignment(asset_id: int, code: str, params: dict | None = None) -> AssetProviderAssignment:
    return AssetProviderAssignment(asset_id=asset_id, provider_code=code, identifier="N2X", identifier_type=ProviderInputType.TICKER, provider_params=json.dumps(params) if params is not None else None)


async def _assignments(engine: AsyncEngine) -> dict[int, tuple[str, str | None, str | None]]:
    """Every stored assignment, read through a fresh session: ``asset_id -> (provider_code, identifier, provider_params)``."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(AssetProviderAssignment))).scalars().all()
        return {row.asset_id: (row.provider_code, row.identifier, row.provider_params) for row in rows}


def _item(asset_id: int, code: str, params: dict | None = None, identifier: str = "N2X") -> FAProviderAssignmentItem:
    return FAProviderAssignmentItem(asset_id=asset_id, provider_code=code, identifier=identifier, identifier_type="TICKER", provider_params=params)


def _route(base: str, quote: str, priority: int, *steps: tuple[str, str, str]) -> FXConversionRouteItem:
    return FXConversionRouteItem(base=base, quote=quote, priority=priority, chain_steps=[{"from": origin, "to": target, "provider": code} for origin, target, code in steps])


def _stored_route(base: str, quote: str, priority: int, *steps: tuple[str, str, str]) -> FxConversionRoute:
    """A stored route as the endpoint writes it: the pair alphabetical, the codes upper-case."""
    assert base < quote, "a stored pair is alphabetical"
    return FxConversionRoute(base=base, quote=quote, priority=priority, chain_steps=json.dumps([{"from": origin, "to": target, "provider": code} for origin, target, code in steps]))


async def _routes(engine: AsyncEngine) -> dict[tuple[str, str, int], list[dict]]:
    """Every stored route, read through a fresh session: ``(base, quote, priority) -> steps``."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(FxConversionRoute))).scalars().all()
        return {(row.base, row.quote, row.priority): json.loads(row.chain_steps) for row in rows}


async def _outcome(call: Awaitable[Any]) -> Any:
    """The route's answer, or the ``HTTPException`` it raised: each test asserts its own point first."""
    try:
        return await call
    except HTTPException as refusal:
        return refusal


async def _assign(engine: AsyncEngine, user: User, items: list[FAProviderAssignmentItem]) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await _outcome(asset_routes.assign_providers_bulk(items, session=session, _current_user=user))


async def _post_routes(engine: AsyncEngine, user: User, routes: list[FXConversionRouteItem], *, replace: bool = False) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await _outcome(fx_routes.create_routes_bulk(routes, replace=replace, session=session, _current_user=user))


def _assert_refused(answer: Any, code: str, missing: list[str]) -> None:
    assert isinstance(answer, HTTPException), f"the request was not refused: {answer!r}"
    expected = not_configured_error(code, missing)
    assert answer.status_code == expected.status_code == 422, f"status {answer.status_code}, detail {answer.detail!r}"
    assert answer.detail == expected.detail


async def _barrier(family: str, expected: dict[str, PluginReadiness], user: User) -> None:
    """The state the scenario names, before the request (in a spy test the spy records it: the test clears it after)."""
    assert await readiness.plugins_readiness(family, list(expected), user_id=user.id) == expected, "barrier: the scenario's readiness"


_UNCONFIGURED = PluginReadiness(False, ("api_key",))
_READY = PluginReadiness(True, ())


# =============================================================================
# 1. ASSETS
# =============================================================================


@pytest.mark.asyncio
async def test_n2_asset_new_assignment_of_an_unconfigured_provider_is_refused(engine, caller, configured):
    """1: an asset with no assignment, given a provider whose key is unset → 422 with the shared body, nothing stored."""
    print_section("N2 1: asset, new assignment, unconfigured")
    (asset_id,) = await _assets(engine, 1)
    await _barrier("asset", {A_KEY: _UNCONFIGURED}, caller)

    answer = await _assign(engine, caller, [_item(asset_id, A_KEY)])

    assert asset_id not in await _assignments(engine), "the assignment of an unconfigured provider was written"
    _assert_refused(answer, A_KEY, ["api_key"])
    print_success("refused, nothing written")


@pytest.mark.asyncio
async def test_n2_asset_second_item_unconfigured_refuses_the_whole_request(engine, caller, configured):
    """1: two items, only the second's provider unconfigured → 422 for the second, and the first is NOT written."""
    first_asset, second_asset = await _assets(engine, 2)
    await _barrier("asset", {A_OK: _READY, A_KEY: _UNCONFIGURED}, caller)

    answer = await _assign(engine, caller, [_item(first_asset, A_OK), _item(second_asset, A_KEY)])

    stored = await _assignments(engine)
    assert first_asset not in stored, "the first item was written although the request is refused"
    assert second_asset not in stored
    _assert_refused(answer, A_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_asset_refusal_names_the_first_unconfigured_item_in_request_order(engine, caller, configured):
    """1: two unconfigured providers, posted zeta then alpha (the reverse of their sorted order) → the body names zeta."""
    first_asset, second_asset = await _assets(engine, 2)
    await _barrier("asset", {A_ZETA: _UNCONFIGURED, A_ALPHA: PluginReadiness(False, ("endpoint",))}, caller)

    answer = await _assign(engine, caller, [_item(first_asset, A_ZETA), _item(second_asset, A_ALPHA)])

    assert not set(await _assignments(engine)) & {first_asset, second_asset}, "an unconfigured provider was assigned"
    _assert_refused(answer, A_ZETA, ["api_key"])


@pytest.mark.asyncio
async def test_n2_asset_change_to_an_unconfigured_provider_keeps_the_stored_assignment_and_prices(engine, caller, configured):
    """1: an asset on a parametric provider, moved to an unconfigured one → refused; its assignment and prices untouched
    (on HEAD leaving the parametric provider wipes the prices)."""
    (asset_id,) = await _assets(engine, 1)
    await _store(
        engine,
        _stored_assignment(asset_id, A_PARAM, {"rate": 1}),
        *(PriceHistory(asset_id=asset_id, date=day, close=Decimal("10.5"), currency="EUR", source_plugin_key=A_PARAM) for day in (date(2026, 1, 5), date(2026, 1, 6))),
    )
    before = await _assignments(engine)
    await _barrier("asset", {A_KEY: _UNCONFIGURED, A_PARAM: _READY}, caller)

    answer = await _assign(engine, caller, [_item(asset_id, A_KEY, identifier="N2NEW")])

    async with AsyncSession(engine) as session:
        prices = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == asset_id))).scalars().all()
    assert len(prices) == 2, f"the prices were wiped: {len(prices)} left"
    assert await _assignments(engine) == before, "the stored assignment was changed"
    _assert_refused(answer, A_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_asset_refusal_leaves_a_re_saved_assignment_of_the_same_request_untouched(engine, caller, configured):
    """1: a re-save with new params (asset A) and a new configured item (asset B) before an unconfigured one (asset C) →
    refused; A keeps its stored params, B gets nothing."""
    asset_a, asset_b, asset_c = await _assets(engine, 3)
    await _store(engine, _stored_assignment(asset_a, A_OK, {"v": 1}))
    before = await _assignments(engine)
    await _barrier("asset", {A_OK: _READY, A_PLAIN: _READY, A_KEY: _UNCONFIGURED}, caller)

    answer = await _assign(engine, caller, [_item(asset_a, A_OK, {"v": 2}), _item(asset_b, A_PLAIN), _item(asset_c, A_KEY)])

    assert await _assignments(engine) == before, "an item of a refused request was written"
    _assert_refused(answer, A_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_asset_re_saving_the_stored_unconfigured_provider_passes(engine, caller, configured):
    """1 (guard, green on HEAD): an asset already on an unconfigured provider re-saves it, params changed → written, no
    refusal: existing assignments stay as they are (plan 76 §3.9)."""
    asset_id, other_id = await _assets(engine, 2)
    await _store(engine, _stored_assignment(asset_id, A_KEY, {"v": 1}))
    await _barrier("asset", {A_KEY: _UNCONFIGURED, A_PLAIN: _READY}, caller)

    answer = await _assign(engine, caller, [_item(asset_id, A_KEY, {"v": 2}), _item(other_id, A_PLAIN)])

    assert not isinstance(answer, HTTPException), f"a re-save was refused: {getattr(answer, 'detail', answer)!r}"
    assert answer.success_count == 2
    stored = await _assignments(engine)
    assert stored[asset_id] == (A_KEY, "N2X", json.dumps({"v": 2}))
    assert stored[other_id][0] == A_PLAIN


@pytest.mark.asyncio
async def test_n2_asset_configured_and_settingless_providers_pass(engine, caller, configured):
    """1 (guard, green on HEAD): a provider with its key stored and one that declares nothing are assigned as today."""
    first_asset, second_asset = await _assets(engine, 2)
    await _barrier("asset", {A_OK: _READY, A_PLAIN: _READY}, caller)

    answer = await _assign(engine, caller, [_item(first_asset, A_OK), _item(second_asset, A_PLAIN)])

    assert not isinstance(answer, HTTPException), f"refused: {getattr(answer, 'detail', answer)!r}"
    stored = await _assignments(engine)
    assert (stored[first_asset][0], stored[second_asset][0]) == (A_OK, A_PLAIN)


def test_n2_asset_unknown_provider_code_keeps_the_schema_error(registries):
    """3 (guard, green on HEAD): an unknown asset provider code is still refused by the request's own validation."""
    with pytest.raises(ValidationError, match="Unknown provider code"):
        _item(1, "n2_no_such_provider")


@pytest.mark.asyncio
async def test_n2_asset_one_readiness_call_per_request(engine, caller, configured, spy):
    """1: a passing request with two new providers and a refused one each ask the check ONCE, for the caller."""
    asset_a, asset_b, asset_c = await _assets(engine, 3)
    await _barrier("asset", {A_OK: _READY, A_PLAIN: _READY, A_KEY: _UNCONFIGURED}, caller)

    spy.calls.clear()
    passing = await _assign(engine, caller, [_item(asset_a, A_OK), _item(asset_b, A_PLAIN)])
    assert not isinstance(passing, HTTPException), f"refused: {getattr(passing, 'detail', passing)!r}"
    assert len(spy.calls) == 1, f"one readiness call per request, got {len(spy.calls)}"
    family, codes, user_id = spy.calls[0]
    assert family == "asset" and user_id == caller.id and {A_OK, A_PLAIN} <= set(codes)

    spy.calls.clear()
    refused = await _assign(engine, caller, [_item(asset_c, A_KEY)])
    assert len(spy.calls) == 1, f"one readiness call per request, got {len(spy.calls)}"
    family, codes, user_id = spy.calls[0]
    assert family == "asset" and user_id == caller.id and A_KEY in codes
    _assert_refused(refused, A_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_managed_profile_refuses_without_naming_a_locked_field(engine, caller, configured, monkeypatch):
    """4: managed profile, a required field unset and a field locked by an invalid variable → refused (not configured),
    and ``missing`` names only the unlocked field."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(env_name("asset", A_MANAGED, "region"), "zz")
    (asset_id,) = await _assets(engine, 1)
    instance = AssetProviderRegistry.get_plugin(A_MANAGED)()
    await runtime.configure_instance(instance, "asset", user_id=caller.id, plugin_code=A_MANAGED)
    assert tuple(instance.settings.missing) == ("endpoint", "region"), "barrier: the boundary misses both"
    await _barrier("asset", {A_MANAGED: PluginReadiness(False, ("endpoint",))}, caller)

    answer = await _assign(engine, caller, [_item(asset_id, A_MANAGED)])

    assert asset_id not in await _assignments(engine), "the assignment of an unconfigured provider was written"
    _assert_refused(answer, A_MANAGED, ["endpoint"])
    assert "region" not in answer.detail["missing"]


# =============================================================================
# 2. FX ROUTES
# =============================================================================


@pytest.mark.asyncio
async def test_n2_fx_new_route_of_an_unconfigured_provider_is_refused_and_manual_kept(engine, caller, configured):
    """2: a pair on its MANUAL route, posted with an unconfigured provider → 422, the MANUAL route still there, no new route."""
    print_section("N2 2: FX route, new provider, unconfigured")
    await _store(engine, _stored_route("GBP", "USD", fx_routes.MANUAL_PRIORITY, ("GBP", "USD", "MANUAL")))
    before = await _routes(engine)
    await _barrier("fx", {F_KEY: _UNCONFIGURED}, caller)

    answer = await _post_routes(engine, caller, [_route("GBP", "USD", 1, ("GBP", "USD", F_KEY))])

    assert await _routes(engine) == before, "the routes of the pair changed (route created or MANUAL removed)"
    _assert_refused(answer, F_KEY, ["api_key"])
    print_success("refused, MANUAL kept")


@pytest.mark.asyncio
async def test_n2_fx_second_route_unconfigured_refuses_the_whole_request(engine, caller, configured):
    """2: two routes, only the second's provider unconfigured → 422 for the second, the first pair not written."""
    await _barrier("fx", {F_OK: _READY, F_KEY: _UNCONFIGURED}, caller)

    answer = await _post_routes(engine, caller, [_route("EUR", "CHF", 1, ("EUR", "CHF", F_OK)), _route("EUR", "JPY", 1, ("EUR", "JPY", F_KEY))])

    assert await _routes(engine) == {}, "a route of a refused request was written"
    _assert_refused(answer, F_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_fx_refusal_names_the_first_in_route_then_step_order(engine, caller, configured):
    """2: route order first (zeta's route before alpha's), then step order (a chain zeta then alpha) → zeta is named."""
    await _barrier("fx", {F_ZETA: _UNCONFIGURED, F_ALPHA: PluginReadiness(False, ("endpoint",))}, caller)

    by_route = await _post_routes(engine, caller, [_route("GBP", "USD", 1, ("GBP", "USD", F_ZETA)), _route("CHF", "USD", 1, ("CHF", "USD", F_ALPHA))])
    by_step = await _post_routes(engine, caller, [_route("RON", "USD", 1, ("RON", "EUR", F_ZETA), ("EUR", "USD", F_ALPHA))])

    assert await _routes(engine) == {}, "a route of a refused request was written"
    _assert_refused(by_route, F_ZETA, ["api_key"])
    _assert_refused(by_step, F_ZETA, ["api_key"])


@pytest.mark.asyncio
async def test_n2_fx_replace_with_an_unconfigured_new_provider_keeps_the_pairs_routes(engine, caller, configured):
    """2: ``?replace=true`` posting an unconfigured provider for priority 1 → refused; priorities 1 and 2 stay as stored."""
    await _store(engine, _stored_route("EUR", "USD", 1, ("EUR", "USD", F_PLAIN)), _stored_route("EUR", "USD", 2, ("EUR", "USD", F_OK)))
    before = await _routes(engine)
    await _barrier("fx", {F_KEY: _UNCONFIGURED}, caller)

    answer = await _post_routes(engine, caller, [_route("EUR", "USD", 1, ("EUR", "USD", F_KEY))], replace=True)

    assert await _routes(engine) == before, "replace=true changed the pair's routes although the request is refused"
    _assert_refused(answer, F_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_fx_chain_with_an_unconfigured_second_step_is_refused(engine, caller, configured):
    """2: a chain whose first step is configured and whose second is not; the provider is stored only on the step's own
    edge pair (EUR/USD), not on the route's pair (RON/USD) → still new for the pair, refused."""
    await _store(engine, _stored_route("EUR", "USD", 1, ("EUR", "USD", F_KEY)))
    before = await _routes(engine)
    await _barrier("fx", {F_PLAIN: _READY, F_KEY: _UNCONFIGURED}, caller)

    answer = await _post_routes(engine, caller, [_route("RON", "USD", 1, ("RON", "EUR", F_PLAIN), ("EUR", "USD", F_KEY))])

    assert await _routes(engine) == before, "the chain route was written"
    _assert_refused(answer, F_KEY, ["api_key"])


@pytest.mark.asyncio
async def test_n2_fx_provider_already_on_the_pair_passes_even_unconfigured(engine, caller, configured):
    """2 (guard, green on HEAD): an unconfigured provider a stored route of the pair already names passes: posted with the
    pair reversed (USD/EUR is the stored EUR/USD), and against a stored chain naming it in its second step."""
    await _store(engine, _stored_route("EUR", "USD", 1, ("EUR", "USD", F_KEY)), _stored_route("RON", "USD", 1, ("RON", "EUR", F_PLAIN), ("EUR", "USD", F_KEY)))
    await _barrier("fx", {F_KEY: _UNCONFIGURED}, caller)

    reversed_pair = await _post_routes(engine, caller, [_route("USD", "EUR", 2, ("USD", "EUR", F_KEY))])
    after_chain = await _post_routes(engine, caller, [_route("RON", "USD", 2, ("RON", "USD", F_KEY))])

    for answer in (reversed_pair, after_chain):
        assert not isinstance(answer, HTTPException), f"refused: {getattr(answer, 'detail', answer)!r}"
        assert answer.success_count == 1
    stored = await _routes(engine)
    assert {("EUR", "USD", 1), ("EUR", "USD", 2), ("RON", "USD", 1), ("RON", "USD", 2)} <= set(stored)


@pytest.mark.asyncio
async def test_n2_fx_configured_and_settingless_providers_pass(engine, caller, configured):
    """2 (guard, green on HEAD): a provider with its key stored and one that declares nothing are saved as today."""
    await _barrier("fx", {F_OK: _READY, F_PLAIN: _READY}, caller)

    answer = await _post_routes(engine, caller, [_route("EUR", "CHF", 1, ("EUR", "CHF", F_OK)), _route("EUR", "JPY", 1, ("EUR", "JPY", F_PLAIN))])

    assert not isinstance(answer, HTTPException), f"refused: {getattr(answer, 'detail', answer)!r}"
    assert {("CHF", "EUR", 1), ("EUR", "JPY", 1)} <= set(await _routes(engine))


@pytest.mark.asyncio
async def test_n2_fx_unknown_provider_keeps_its_per_item_error(engine, caller, configured):
    """2 (guard, green on HEAD): an unknown provider code is not a readiness question: still the per-item 400, nothing saved."""
    answer = await _post_routes(engine, caller, [_route("EUR", "CHF", 1, ("EUR", "CHF", "N2FXNOSUCH"))])

    assert isinstance(answer, HTTPException) and answer.status_code == 400, f"not the per-item error: {answer!r}"
    assert answer.detail["results"][0]["success"] is False
    assert await _routes(engine) == {}


@pytest.mark.asyncio
async def test_n2_fx_one_readiness_call_per_request(engine, caller, configured, spy):
    """2: a passing request with two new providers and a refused one each ask the check ONCE, for the caller."""
    await _barrier("fx", {F_OK: _READY, F_PLAIN: _READY, F_KEY: _UNCONFIGURED}, caller)

    spy.calls.clear()
    passing = await _post_routes(engine, caller, [_route("EUR", "CHF", 1, ("EUR", "CHF", F_OK)), _route("RON", "USD", 1, ("RON", "EUR", F_PLAIN), ("EUR", "USD", F_OK))])
    assert not isinstance(passing, HTTPException), f"refused: {getattr(passing, 'detail', passing)!r}"
    assert len(spy.calls) == 1, f"one readiness call per request, got {len(spy.calls)}"
    family, codes, user_id = spy.calls[0]
    assert family == "fx" and user_id == caller.id and {F_OK, F_PLAIN} <= set(codes)

    spy.calls.clear()
    refused = await _post_routes(engine, caller, [_route("EUR", "JPY", 1, ("EUR", "JPY", F_KEY))])
    assert len(spy.calls) == 1, f"one readiness call per request, got {len(spy.calls)}"
    family, codes, user_id = spy.calls[0]
    assert family == "fx" and user_id == caller.id and F_KEY in codes
    _assert_refused(refused, F_KEY, ["api_key"])

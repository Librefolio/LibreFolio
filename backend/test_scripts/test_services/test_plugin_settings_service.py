"""Plugin settings, the service: the catalogue a caller sees, and the writes, all or nothing (plan 03, CP10).

Module under test: ``services/plugin_settings/service.py`` (``read_catalogue``, ``write_settings``), with the real test
doubles ``mockprov`` (asset: four system fields, three user fields, a secret of each scope, an alias) and ``MOCKFX``
(FX: a system secret and a system integer). The contract pinned here:

1. **The catalogue** lists the plugins that declare settings, a test-only one only when ``plugin_code`` names it, each
   field as declared, with its state for the caller: the value of a plain field, for a secret only ``is_set``,
   ``source`` and ``problem`` (``unreadable`` once the instance key changed; ``invalid_stored`` for a row the field
   refuses now). A system field is editable by an administrator only, a user field by its owner; ``env_variable`` is
   shown to an administrator only. A user's values reach nobody else's catalogue, an administrator's included. Each
   plugin says whether it is ``configured``: every required field has a usable value — a secret set and readable by
   the current key — and no environment variable of its fields is invalid, optional fields included; a row the field
   refuses now while a default stands in does not unconfigure it. Each plugin shows its name and its icon
   (``icon_url``), read from one instance as its family's provider list reads them (``_plugin_identity``): ``get_icon``
   for an asset plugin (``GET /assets/provider``), ``icon`` for an FX one (``GET /fx/providers``), never the other
   family's, stripped. A plugin that cannot be instantiated shows its code and no icon; a name that raises is the code,
   the icon read all the same; an icon that raises, or is not a non-blank string, is no icon, the name read all the
   same; a family without a row in ``FAMILY_ICON_ATTRIBUTES`` has no icon, and every family of ``FAMILY_REGISTRIES``
   has its row.
2. **Writes are all or nothing**: every item is checked first; one refused item refuses the write, the refusal lists
   every item with its outcome and nothing is written. A system field needs an administrator (``FORBIDDEN_SCOPE``); a
   field an environment variable sets is ``LOCKED_BY_ENV`` (the derived name, its ``_FILE``, the alias; never a user
   field); an unknown plugin, key or scope is ``UNKNOWN_FIELD``; a value the field refuses, the same field twice, not
   exactly one of ``value`` / ``secret_value`` / ``clear``, a secret outside ``secret_value`` or a plain value inside
   it are ``INVALID_VALUE``. No message contains a value.
3. **The managed profile** (``LIBREFOLIO_PROFILE=managed``): a field the environment locks is absent from the
   catalogue (a plugin with no field left is absent too) and a write to it is ``UNKNOWN_FIELD``, for an administrator
   too; the other fields behave as usual. ``configured`` is judged on every field, the hidden ones too, and the entry
   never names which one is missing (decision N2).
4. **Storage**: a secret is encrypted with the instance's subkey, bound to its row (family, plugin, field, scope, user)
   and recorded with the key id; no plaintext of a secret anywhere in the database; a system row records who wrote it;
   writing again updates the row, clearing deletes it. A write that needs the key when the key cannot be used raises
   ``PluginSettingsKeyUnavailable`` and writes nothing; a write without a secret never needs the key; the catalogue
   still answers, every stored secret «set but unreadable».
5. **The log** of a write says who wrote which fields (``family/code/key:scope:set|clear``) and never a value.
6. **FX**: ``MOCKFX``'s two system fields are written here (never over HTTP, where they would change the cache keys
   of every FX call of the lane) and reach a configured ``MOCKFX``.

**X-R43** (workstream X): an integer past the double range is refused like any value its field refuses — ``INVALID_VALUE``
«too large», never with its digits, nothing written — instead of an ``OverflowError`` escaping the write. «Red today» is
the state before the cure; a guard passes before and after.

Pure: the database is a private SQLite file under ``tmp_path`` built by ``create_all``, with its own users; the instance
key is a test key set with ``monkeypatch`` and the data directory points into ``tmp_path``; every variable is set with
``monkeypatch``, the ambient ones of the plugins removed first. The plugin with required fields is a lab plugin of this
module, put in the service's place of the asset registry with ``monkeypatch`` for the tests that need it. The icons are
read from stand-in classes of this module, handed to ``_plugin_identity`` directly; no FX plugin declares settings and
an icon yet, so ``MOCKFX`` is given one with ``monkeypatch`` where the FX family needs it.
"""

from __future__ import annotations

import json
import random
import sqlite3
import uuid
from collections.abc import AsyncIterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.schemas.plugin_settings import PluginSettingErrorCode, PluginSettingsCatalogResponse, PluginSettingsPluginRead, PluginSettingWriteItem, PluginSettingWriteResult
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.platform.instance_key import InstanceKeyError
from backend.app.services.plugin_settings import resolver, runtime, service
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.crypto import decrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType, env_name, env_variables
from backend.app.services.plugin_settings.service import PluginSettingsKeyUnavailable, PluginSettingsRefused, read_catalogue, write_settings
from backend.app.services.provider_registry import AbstractProviderRegistry
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-plugin-settings-test-key-A-0123456789"
KEY_B = "LibreFolio-plugin-settings-test-key-B-9876543210"
UNKNOWN, FORBIDDEN, LOCKED, INVALID = (PluginSettingErrorCode.UNKNOWN_FIELD, PluginSettingErrorCode.FORBIDDEN_SCOPE, PluginSettingErrorCode.LOCKED_BY_ENV, PluginSettingErrorCode.INVALID_VALUE)
MOCKPROV_KEYS = [declared.key for declared in MockProvider.settings_fields]
SYSTEM_KEYS = ["api_key", "region", "price_tolerance", "verbose"]
USER_KEYS = ["preferred_language", "results_limit", "personal_token"]
REGION_VARIABLE = "LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_REGION"
API_KEY_ALIAS = "LIBREFOLIO_MOCKPROV_API_KEY"

LAB_CODE = "lab_required"
#: The lab plugin's fields: two required system fields, a plain one and a secret, and an optional user field.
LAB_FIELDS = (
    PluginSettingField(key="endpoint", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Endpoint (testing)", required=True),
    PluginSettingField(key="api_key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="API key (testing)", secret=True, required=True),
    PluginSettingField(key="limit", type=SettingType.INTEGER, scope=SettingScope.USER, label="Limit (testing)", default=5, minimum=1, maximum=9),
)


class _LabPlugin(PluginSettingsMixin):
    """An asset plugin of these tests that cannot work without its two required fields: listed only when named."""

    provider_code = LAB_CODE
    test_only = True
    settings_fields = LAB_FIELDS


class _LabRegistry(AbstractProviderRegistry):
    """The asset registry these tests put in the service's place: the lab plugin only, no folder to discover."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_settings_service_lab"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"


def _secret() -> str:
    return f"lfsecret{uuid.uuid4().hex}"


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The test key A, a data directory of this test, the self-hosted profile, no ambient variable of mockprov, MOCKFX or the lab plugin."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    for family, plugin in (("asset", MockProvider), ("fx", MockFXProvider), ("asset", _LabPlugin)):
        code = plugin().provider_code
        for declared in plugin.settings_fields:
            for name in {*env_variables(family, code, declared), env_name(family, code, declared.key)}:
                monkeypatch.delenv(name, raising=False)
                monkeypatch.delenv(name + "_FILE", raising=False)
    # The resolver logs some problems once per process: each test starts with none logged.
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema, opened as production opens its own; disposed at teardown."""
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield private
    finally:
        await private.dispose()


@pytest_asyncio.fixture
async def people(engine: AsyncEngine) -> dict[str, User]:
    """An administrator and two members of the private database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = {
            "admin": User(username="admin", email="admin@example.test", hashed_password="$argon2id$test", is_superuser=True),
            "alice": User(username="alice", email="alice@example.test", hashed_password="$argon2id$test"),
            "bob": User(username="bob", email="bob@example.test", hashed_password="$argon2id$test"),
        }
        session.add_all(created.values())
        await session.commit()
    return created


def _item(key: str, scope: str, *, family: str = "asset", code: str = "mockprov", **write: Any) -> PluginSettingWriteItem:
    return PluginSettingWriteItem(family=family, plugin_code=code, field_key=key, scope=scope, **write)


def _fx(key: str, **write: Any) -> PluginSettingWriteItem:
    return _item(key, "system", family="fx", code="MOCKFX", **write)


async def _write(engine: AsyncEngine, user: User, items: list[PluginSettingWriteItem]):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await write_settings(session, user, items)


async def _refused(engine: AsyncEngine, user: User, items: list[PluginSettingWriteItem]) -> list[PluginSettingWriteResult]:
    """The outcome of every item of a refused write; the test fails if the write goes through."""
    with pytest.raises(PluginSettingsRefused) as refused:
        await _write(engine, user, items)
    assert len(refused.value.results) == len(items), "the refusal lists every item"
    return refused.value.results


def _outcomes(results: list[PluginSettingWriteResult]) -> list[tuple]:
    return [(result.field_key, result.success, result.error_code) for result in results]


async def _catalogue(engine: AsyncEngine, user: User, **filters: Any) -> PluginSettingsCatalogResponse:
    async with AsyncSession(engine) as session:
        return await read_catalogue(session, user, **filters)


async def _fields(engine: AsyncEngine, user: User, code: str = "mockprov", family: str | None = None) -> dict[str, Any]:
    """The fields of one plugin as ``user`` sees them, by key; empty when the plugin is not listed."""
    catalogue = await _catalogue(engine, user, plugin_code=code, family=family)
    plugins = [plugin for plugin in catalogue.plugins if plugin.plugin_code == code]
    assert len(plugins) <= 1
    return {field.key: field for field in plugins[0].fields} if plugins else {}


async def _entry(engine: AsyncEngine, user: User, code: str) -> PluginSettingsPluginRead:
    """The catalogue entry of one plugin as ``user`` sees it; the test fails when it is not listed exactly once."""
    catalogue = await _catalogue(engine, user, plugin_code=code)
    (entry,) = [plugin for plugin in catalogue.plugins if plugin.plugin_code == code]
    return entry


def _by_key(entry: PluginSettingsPluginRead) -> dict[str, Any]:
    return {field.key: field for field in entry.fields}


@pytest.fixture
def lab_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The service reads the asset family from a registry holding the lab plugin alone (mockprov out of sight)."""
    monkeypatch.setattr(_LabRegistry, "_providers", {LAB_CODE: _LabPlugin})
    monkeypatch.setattr(_LabRegistry, "_discovery_done", True)
    monkeypatch.setitem(service.FAMILY_REGISTRIES, "asset", _LabRegistry)


async def _rows(engine: AsyncEngine) -> tuple[list[PluginSystemSetting], list[PluginUserSetting]]:
    async with AsyncSession(engine) as session:
        system = list((await session.execute(select(PluginSystemSetting).order_by(PluginSystemSetting.id))).scalars())
        user = list((await session.execute(select(PluginUserSetting).order_by(PluginUserSetting.id))).scalars())
    return system, user


async def _assert_nothing_written(engine: AsyncEngine) -> None:
    system, user = await _rows(engine)
    assert (system, user) == ([], []), f"nothing may be written: {len(system)} system and {len(user)} user row(s)"


def _state(field: Any) -> tuple:
    return (field.value, field.is_set, field.source, field.locked, field.editable, field.problem)


def _database_text(db: Path) -> str:
    """Every row of the private database as SQL text, and its files as text: where a plaintext would show."""
    with closing(sqlite3.connect(db)) as conn:
        dump = "\n".join(conn.iterdump())
    raw = b"".join(path.read_bytes() for path in (db, db.with_name(db.name + "-wal")) if path.exists())
    return dump + raw.decode("latin-1")


# =============================================================================
# 1. THE CATALOGUE
# =============================================================================


@pytest.mark.asyncio
async def test_a_test_only_plugin_is_listed_only_when_named(engine: AsyncEngine, people: dict[str, User]):
    """1: ``mockprov`` and ``MOCKFX`` exist for the tests: listed by code, never in the full catalogue."""
    print_section("1: test-only plugins")
    everything = await _catalogue(engine, people["admin"])
    listed = {plugin.plugin_code for plugin in everything.plugins}

    assert not {"mockprov", "MOCKFX", "MOCKFX_FAIL"} & listed, f"a test-only plugin is listed: {listed}"
    assert set(await _fields(engine, people["admin"], "mockprov")) == set(MOCKPROV_KEYS)
    assert set(await _fields(engine, people["admin"], "MOCKFX")) == {"api_key", "decimals"}
    assert await _fields(engine, people["admin"], "MOCKFX_FAIL") == {}, "a plugin without fields is never listed"
    print_success("hidden from the full catalogue, listed when named")


@pytest.mark.asyncio
async def test_the_family_filter(engine: AsyncEngine, people: dict[str, User]):
    assert set(await _fields(engine, people["alice"], "mockprov", family="asset")) == set(MOCKPROV_KEYS)
    assert await _fields(engine, people["alice"], "mockprov", family="fx") == {}
    assert await _fields(engine, people["alice"], "MOCKFX", family="asset") == {}
    assert set(await _fields(engine, people["alice"], "MOCKFX", family="fx")) == {"api_key", "decimals"}


@pytest.mark.asyncio
async def test_the_catalogue_describes_each_field_as_declared(engine: AsyncEngine, people: dict[str, User]):
    """1: declaration order, type, scope, secret, labels, options, lengths, bounds; a secret has no default and no value."""
    catalogue = await _catalogue(engine, people["admin"], plugin_code="mockprov")
    (plugin,) = catalogue.plugins

    assert (plugin.family, plugin.plugin_code) == ("asset", "mockprov") and plugin.plugin_name
    assert [field.key for field in plugin.fields] == MOCKPROV_KEYS
    for field, declared in zip(plugin.fields, MockProvider.settings_fields, strict=True):
        assert (field.type, field.scope, field.secret, field.required, field.label) == (declared.type.value, declared.scope.value, declared.secret, declared.required, declared.label)
        assert [option.value for option in field.options] == list(declared.option_values)
        assert (field.minimum, field.maximum) == (declared.minimum, declared.maximum)
        textual = declared.type.value == "string"
        assert (field.min_length, field.max_length) == ((declared.effective_min_length, declared.effective_max_length) if textual else (None, None))
        assert field.default == (None if declared.secret else declared.default)
        expected = (None, False, "none", False, True, None) if declared.secret else (declared.default, False, "default", False, True, None)
        assert _state(field) == expected, f"{field.key}: {_state(field)}"
        assert field.env_variable is None and field.updated_at is None


@pytest.mark.asyncio
async def test_a_member_reads_the_system_fields_without_editing_them(engine: AsyncEngine, people: dict[str, User]):
    """1: system fields read-only for a member, user fields editable; the FX plugin read-only throughout."""
    asset = await _fields(engine, people["alice"])
    fx = await _fields(engine, people["alice"], "MOCKFX")
    admins_fx = await _fields(engine, people["admin"], "MOCKFX")

    assert {key: field.editable for key, field in asset.items()} == {key: key in USER_KEYS for key in MOCKPROV_KEYS}
    assert {key: field.editable for key, field in fx.items()} == {"api_key": False, "decimals": False}
    assert {key: field.editable for key, field in admins_fx.items()} == {"api_key": True, "decimals": True}


# -----------------------------------------------------------------------------
# configured: one rule for the catalogue and for a call (resolver.missing_field_keys)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_plugin_with_nothing_required_and_nothing_invalid_is_configured(engine: AsyncEngine, people: dict[str, User]):
    """1: mockprov and MOCKFX declare no required field: configured for everyone, before and after writes, and with a
    row the field refuses now (``invalid_stored``), for which the default stands in."""
    print_section("1: configured, nothing required")
    admin, alice = people["admin"], people["alice"]
    untouched = {(code, name): (await _entry(engine, user, code)).configured for code in ("mockprov", "MOCKFX") for name, user in (("admin", admin), ("alice", alice))}
    await _write(engine, admin, [_item("api_key", "system", secret_value=_secret()), _fx("decimals", value=2)])
    await _write(engine, alice, [_item("results_limit", "user", value=7)])
    async with AsyncSession(engine) as session:
        session.add(PluginSystemSetting(family="asset", plugin_code="mockprov", field_key="price_tolerance", value_json="99"))
        await session.commit()

    written = {(code, name): (await _entry(engine, user, code)) for code in ("mockprov", "MOCKFX") for name, user in (("admin", admin), ("alice", alice))}

    assert untouched == dict.fromkeys(untouched, True)
    assert _by_key(written[("mockprov", "alice")])["price_tolerance"].problem == "invalid_stored", "barrier: the refused row is there"
    assert {key: entry.configured for key, entry in written.items()} == dict.fromkeys(written, True)
    print_success("configured, whatever was written; invalid_stored with a default does not unconfigure")


@pytest.mark.asyncio
async def test_a_required_field_without_a_value_leaves_the_plugin_not_configured_until_a_valid_save(engine: AsyncEngine, people: dict[str, User], lab_registry: None):
    """1: both required fields unset: not configured; a refused write changes nothing, one of the two is not enough;
    with both saved, configured for every caller."""
    print_section("1: configured after a valid save")
    admin, alice = people["admin"], people["alice"]

    before = await _entry(engine, alice, LAB_CODE)
    (refused,) = await _refused(engine, admin, [_item("endpoint", "system", code=LAB_CODE, value="")])
    after_refusal = await _entry(engine, alice, LAB_CODE)
    await _write(engine, admin, [_item("endpoint", "system", code=LAB_CODE, value="https://api.example/v1")])
    half = await _entry(engine, alice, LAB_CODE)
    await _write(engine, admin, [_item("api_key", "system", code=LAB_CODE, secret_value=_secret())])
    after = {name: await _entry(engine, user, LAB_CODE) for name, user in people.items()}

    unset = _by_key(before)
    assert {key: (field.required, _state(field)) for key, field in unset.items() if field.required} == {
        "endpoint": (True, (None, False, "none", False, False, None)),
        "api_key": (True, (None, False, "none", False, False, None)),
    }
    assert (refused.error_code, before.configured, after_refusal.configured, half.configured) == (INVALID, False, False, False)
    assert {name: entry.configured for name, entry in after.items()} == {"admin": True, "alice": True, "bob": True}
    assert _state(_by_key(after["alice"])["api_key"]) == (None, True, "db", False, False, None), "the secret is set and readable, never shown"
    print_success("not configured until both required fields hold a valid value")


@pytest.mark.asyncio
async def test_a_required_secret_the_current_key_cannot_read_leaves_the_plugin_not_configured(engine: AsyncEngine, people: dict[str, User], lab_registry: None, monkeypatch: pytest.MonkeyPatch):
    """1: the required secret written under key A, the instance key now B: «set but unreadable», not configured;
    written again under B, configured."""
    admin = people["admin"]
    await _write(engine, admin, [_item("endpoint", "system", code=LAB_CODE, value="https://api.example/v1"), _item("api_key", "system", code=LAB_CODE, secret_value=_secret())])
    readable = await _entry(engine, admin, LAB_CODE)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)

    unreadable = await _entry(engine, admin, LAB_CODE)
    await _write(engine, admin, [_item("api_key", "system", code=LAB_CODE, secret_value=_secret())])
    rewritten = await _entry(engine, admin, LAB_CODE)

    assert readable.configured is True
    assert (_state(_by_key(unreadable)["api_key"]), unreadable.configured) == ((None, True, "db", False, True, "unreadable"), False)
    assert (_state(_by_key(rewritten)["api_key"]), rewritten.configured) == ((None, True, "db", False, True, None), True)


@pytest.mark.parametrize(
    ("code", "key", "variable", "valid", "invalid"),
    [
        pytest.param("mockprov", "region", REGION_VARIABLE, "us", "atlantis", id="mockprov-region-select"),
        pytest.param("MOCKFX", "decimals", env_name("fx", "MOCKFX", "decimals"), "4", "four", id="MOCKFX-decimals-integer"),
    ],
)
@pytest.mark.asyncio
async def test_an_invalid_variable_leaves_the_plugin_not_configured_even_for_an_optional_field(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch, code, key, variable, valid, invalid):
    """1: an optional system field locked by a variable: configured while the value is valid, not configured once it is
    not — its default never stands in."""
    monkeypatch.setenv(variable, valid)
    with_a_valid_value = await _entry(engine, people["alice"], code)
    monkeypatch.setenv(variable, invalid)

    with_an_invalid_value = await _entry(engine, people["alice"], code)

    field = next(field for field in with_an_invalid_value.fields if field.key == key)
    assert (field.required, field.locked, field.source, field.value, field.problem) == (False, True, "env", None, "invalid_env")
    assert (with_a_valid_value.configured, with_an_invalid_value.configured) == (True, False)


# -----------------------------------------------------------------------------
# The plugin's name and icon (_plugin_identity): one instance, read as its family's provider list reads it
# -----------------------------------------------------------------------------

#: The icons of the shipped plugins that declare settings, today: what their ``get_icon`` gives, and ``GET /assets/provider`` publishes.
SHIPPED_ICONS = {
    "borsa_italiana": "https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico",
    "justetf": "https://www.justetf.com/android-chrome-144x144.png?v2",
}
STAND_IN_CODE = "stand_in"
STAND_IN_NAME = "Stand-in plugin (testing)"
ASSET_ICON = "https://icons.example.test/stand-in-asset.png"
FX_ICON = "https://icons.example.test/stand-in-fx.svg"
#: Where each family's provider list reads a plugin's icon: ``GET /assets/provider`` reads ``get_icon``, ``GET /fx/providers`` reads ``icon``.
PROVIDER_LIST_ICONS = [pytest.param("asset", "get_icon", id="asset-get_icon"), pytest.param("fx", "icon", id="fx-icon")]


def _stand_in(**attributes: Any) -> type:
    """A plugin class of these tests, never registered: each keyword is a property that returns its value, or raises it
    when the value is an exception."""

    def readable(value: Any) -> property:
        def read(_self: Any) -> Any:
            if isinstance(value, Exception):
                raise value
            return value

        return property(read)

    return type("StandInPlugin", (), {key: readable(value) for key, value in attributes.items()})


class _Unbuildable:
    """A plugin class whose constructor raises. Its name and both icons are class attributes, readable without an
    instance: none of them may show."""

    provider_name = STAND_IN_NAME
    name = STAND_IN_NAME
    get_icon = ASSET_ICON
    icon = FX_ICON

    def __init__(self) -> None:
        raise RuntimeError("cannot be instantiated (testing)")


@pytest.mark.parametrize(
    ("family", "plugin_class", "icon"),
    [
        pytest.param("asset", _stand_in(provider_name=STAND_IN_NAME, get_icon=f"  {ASSET_ICON}\n"), ASSET_ICON, id="asset-get_icon-stripped"),
        pytest.param("fx", _stand_in(name=STAND_IN_NAME, icon=f"\t{FX_ICON} "), FX_ICON, id="fx-icon-stripped"),
        pytest.param("asset", _stand_in(provider_name=STAND_IN_NAME, get_icon=ASSET_ICON, icon=FX_ICON), ASSET_ICON, id="asset-with-both-reads-get_icon"),
        pytest.param("fx", _stand_in(name=STAND_IN_NAME, get_icon=ASSET_ICON, icon=FX_ICON), FX_ICON, id="fx-with-both-reads-icon"),
        pytest.param("asset", _stand_in(provider_name=STAND_IN_NAME, icon=FX_ICON), None, id="asset-with-only-the-fx-attribute"),
        pytest.param("fx", _stand_in(name=STAND_IN_NAME, get_icon=ASSET_ICON), None, id="fx-with-only-the-asset-attribute"),
        pytest.param("asset", _stand_in(provider_name=STAND_IN_NAME), None, id="asset-without-an-icon-attribute"),
        pytest.param("fx", _stand_in(name=STAND_IN_NAME), None, id="fx-without-an-icon-attribute"),
    ],
)
def test_the_icon_is_the_attribute_its_familys_provider_list_publishes(family: str, plugin_class: type, icon: str | None):
    """1: ``get_icon`` for an asset plugin, ``icon`` for an FX one, stripped; never the other family's; without it, no icon."""
    assert service._plugin_identity(family, plugin_class, STAND_IN_CODE) == (STAND_IN_NAME, icon)


@pytest.mark.parametrize("error", [RuntimeError("the icon cannot be built (testing)"), AttributeError("the icon needs an attribute it does not find (testing)")], ids=["RuntimeError", "AttributeError"])
@pytest.mark.parametrize(("family", "attribute"), PROVIDER_LIST_ICONS)
def test_an_icon_that_raises_is_no_icon_and_the_name_is_still_read(family: str, attribute: str, error: Exception):
    """1: an icon is decoration: a property that raises gives no icon, never a failed catalogue, and the name still shows."""
    plugin_class = _stand_in(provider_name=STAND_IN_NAME, **{attribute: error})
    with pytest.raises(type(error)):
        getattr(plugin_class(), attribute)  # barrier: reading the icon does raise, so the None below is the guard's

    assert service._plugin_identity(family, plugin_class, STAND_IN_CODE) == (STAND_IN_NAME, None)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param(" \t\n ", id="blank"),
        pytest.param(None, id="None"),
        pytest.param(123, id="an-int"),
        pytest.param(b"https://icons.example.test/bytes.png", id="bytes"),
        pytest.param(["https://icons.example.test/in-a-list.png"], id="a-list"),
    ],
)
@pytest.mark.parametrize(("family", "attribute"), PROVIDER_LIST_ICONS)
def test_an_icon_that_is_not_a_non_blank_string_is_no_icon(family: str, attribute: str, value: Any):
    assert service._plugin_identity(family, _stand_in(provider_name=STAND_IN_NAME, **{attribute: value}), STAND_IN_CODE) == (STAND_IN_NAME, None)


@pytest.mark.parametrize("family", ["asset", "fx"])
def test_a_plugin_that_cannot_be_instantiated_shows_its_code_and_no_icon(family: str):
    """1: its class attributes are never read in place of an instance's."""
    with pytest.raises(RuntimeError):
        _Unbuildable()  # barrier: the constructor does raise

    assert service._plugin_identity(family, _Unbuildable, STAND_IN_CODE) == (STAND_IN_CODE, None)


def test_a_family_without_an_icon_attribute_has_no_icon_and_still_its_name():
    """1: the attribute is the family's row of ``FAMILY_ICON_ATTRIBUTES``; without a row, none — not another family's."""
    family = "lab_family"
    assert family not in service.FAMILY_ICON_ATTRIBUTES, "barrier: the family has no row"

    assert service._plugin_identity(family, _stand_in(provider_name=STAND_IN_NAME, get_icon=ASSET_ICON, icon=FX_ICON), STAND_IN_CODE) == (STAND_IN_NAME, None)


@pytest.mark.parametrize(
    ("plugin_class", "name", "icon"),
    [
        pytest.param(_stand_in(provider_name="Provider name (testing)", name="Name (testing)"), "Provider name (testing)", None, id="provider_name-first"),
        pytest.param(_stand_in(provider_name="", name="Name (testing)"), "Name (testing)", None, id="empty-provider_name-then-name"),
        pytest.param(_stand_in(name="Name (testing)"), "Name (testing)", None, id="name-without-provider_name"),
        pytest.param(_stand_in(), STAND_IN_CODE, None, id="neither-then-the-code"),
        # A RuntimeError, not an AttributeError: getattr(..., None) would swallow the latter by itself, so only this one
        # proves the guard. The icon shows that a name that cannot be read does not cost the icon too.
        pytest.param(_stand_in(provider_name=RuntimeError("the name cannot be built (testing)"), get_icon=ASSET_ICON), STAND_IN_CODE, ASSET_ICON, id="provider_name-raises-then-the-code-icon-still-read"),
    ],
)
def test_the_name_is_provider_name_else_name_else_the_code(plugin_class: type, name: str, icon: str | None):
    """1: ``provider_name``, else ``name``, else the code; a name that raises is the code, and the icon is read all the same."""
    assert service._plugin_identity("asset", plugin_class, STAND_IN_CODE) == (name, icon)


def test_every_settings_family_has_its_icon_attribute():
    """1, guard: a family added to ``FAMILY_REGISTRIES`` adds its row to ``FAMILY_ICON_ATTRIBUTES``, or its plugins show
    no icon without a word; and every plugin its registry holds has the attribute the row names, so it is no typo."""
    unmapped = sorted(set(service.FAMILY_REGISTRIES) - set(service.FAMILY_ICON_ATTRIBUTES))
    assert not unmapped, f"add the icon attribute of these families to FAMILY_ICON_ATTRIBUTES: {unmapped}"
    for family, registry in service.FAMILY_REGISTRIES.items():
        attribute = service.FAMILY_ICON_ATTRIBUTES[family]
        codes = registry.list_plugin_codes()
        assert codes, f"barrier: the {family} registry holds no plugin"
        without = [code for code in codes if not hasattr(registry.get_plugin(code), attribute)]
        assert not without, f"{family} plugins without {attribute!r}, the attribute FAMILY_ICON_ATTRIBUTES names: {without}"


def test_the_plugins_of_the_catalogue_carry_their_icons(monkeypatch: pytest.MonkeyPatch):
    """1: ``_plugins``, no database: justetf and borsa_italiana with their own icons; mockprov, named, with none; MOCKFX,
    named, with none, then with the ``icon`` it is given here — the FX family's icon reaches the catalogue too."""
    print_section("1: the icons of the catalogue's plugins")
    listed = {(plugin.family, plugin.code): plugin.icon_url for plugin in service._plugins(None, None)}
    (mockprov,) = service._plugins("asset", "mockprov")
    (mockfx,) = service._plugins("fx", "MOCKFX")
    assert service.FAMILY_REGISTRIES["fx"].get_plugin("MOCKFX") is MockFXProvider, "barrier: the class given an icon below is the registered one"
    monkeypatch.setattr(MockFXProvider, "icon", property(lambda _self: FX_ICON))
    (mockfx_with_an_icon,) = service._plugins("fx", "MOCKFX")

    assert {("asset", code) for code in SHIPPED_ICONS} <= set(listed), f"the full catalogue lists {sorted(listed)}"
    assert {code: listed[("asset", code)] for code in SHIPPED_ICONS} == SHIPPED_ICONS
    assert (mockprov.family, mockprov.code, mockprov.icon_url) == ("asset", "mockprov", None)
    assert (mockfx.family, mockfx.icon_url, mockfx_with_an_icon.icon_url) == ("fx", None, FX_ICON)
    print_success("justetf and borsa_italiana with their icons; mockprov none; MOCKFX's own icon reaches it")


@pytest.mark.asyncio
async def test_each_entry_of_the_catalogue_carries_its_plugins_icon(engine: AsyncEngine, people: dict[str, User]):
    """1: ``read_catalogue`` puts each plugin's icon in its entry: justetf's and borsa_italiana's own, none for mockprov."""
    everything = await _catalogue(engine, people["alice"])
    mockprov = await _entry(engine, people["alice"], "mockprov")

    icons = {plugin.plugin_code: plugin.icon_url for plugin in everything.plugins}
    assert set(SHIPPED_ICONS) <= set(icons), f"the full catalogue lists {sorted(icons)}"
    assert {code: icons[code] for code in SHIPPED_ICONS} == SHIPPED_ICONS
    assert mockprov.icon_url is None


# =============================================================================
# 2. WRITES AND READS
# =============================================================================


@pytest.mark.asyncio
async def test_writes_are_stored_encrypted_and_read_back_by_the_right_people(engine: AsyncEngine, people: dict[str, User], tmp_path: Path):
    """2/4: the administrator's system fields, alice's own fields: rows, encryption, AAD, author, and who sees what."""
    print_section("2: a write by role, and what each caller reads")
    admin, alice, bob = people["admin"], people["alice"], people["bob"]
    system_secret, alice_secret = _secret(), _secret()

    by_admin = await _write(engine, admin, [_item("api_key", "system", secret_value=system_secret), _item("region", "system", value="us"), _item("price_tolerance", "system", value=1.25), _item("verbose", "system", value=True)])
    by_alice = await _write(engine, alice, [_item("results_limit", "user", value=7), _item("personal_token", "user", secret_value=alice_secret), _item("preferred_language", "user", value="it")])

    assert by_admin.success_count == 4 and all(result.success and result.error_code is None for result in by_admin.results)
    assert by_alice.success_count == 3 and [result.field_key for result in by_alice.results] == ["results_limit", "personal_token", "preferred_language"]

    system, user = await _rows(engine)
    subkey = settings_subkey()
    stored = {row.field_key: row for row in system}
    assert set(stored) == {"api_key", "region", "price_tolerance", "verbose"} and all(row.updated_by_user_id == admin.id and row.updated_at for row in system)
    assert (stored["api_key"].value_json, stored["api_key"].key_id) == (None, key_id_of(subkey))
    assert decrypt_secret(subkey, secret_aad("asset", "mockprov", "api_key", "system", None), stored["api_key"].secret_ciphertext) == system_secret
    assert {key: json.loads(stored[key].value_json) for key in ("region", "price_tolerance", "verbose")} == {"region": "us", "price_tolerance": 1.25, "verbose": True}
    mine = {row.field_key: row for row in user}
    assert {row.user_id for row in user} == {alice.id} and set(mine) == {"results_limit", "personal_token", "preferred_language"}
    assert decrypt_secret(subkey, secret_aad("asset", "mockprov", "personal_token", "user", alice.id), mine["personal_token"].secret_ciphertext) == alice_secret
    database = _database_text(tmp_path / "settings.db")
    assert system_secret not in database and alice_secret not in database, "a secret's plaintext reached the database"

    as_admin, as_alice, as_bob = (await _fields(engine, admin)), (await _fields(engine, alice)), (await _fields(engine, bob))
    assert _state(as_admin["api_key"]) == (None, True, "db", False, True, None)
    assert _state(as_alice["api_key"]) == (None, True, "db", False, False, None), "a member sees only that the system secret is set"
    for view in (as_admin, as_alice, as_bob):
        assert (view["region"].value, view["price_tolerance"].value, view["verbose"].value) == ("us", 1.25, True)
    assert (_state(as_alice["results_limit"]), _state(as_alice["personal_token"]), as_alice["preferred_language"].value) == ((7, True, "db", False, True, None), (None, True, "db", False, True, None), "it")
    for other in (as_admin, as_bob):
        assert _state(other["results_limit"]) == (10, False, "default", False, True, None), "a user's values reach nobody else, an administrator included"
        assert _state(other["personal_token"]) == (None, False, "none", False, True, None)
        assert other["preferred_language"].value == "all"
    print_success("encrypted and bound to their rows; each caller reads what is theirs and the instance's")


@pytest.mark.asyncio
async def test_writing_again_updates_the_row_and_clearing_deletes_it(engine: AsyncEngine, people: dict[str, User]):
    alice = people["alice"]
    await _write(engine, alice, [_item("results_limit", "user", value=7)])
    _system, (first,) = await _rows(engine)

    await _write(engine, alice, [_item("results_limit", "user", value=9)])
    _system, (second,) = await _rows(engine)
    cleared = await _write(engine, alice, [_item("results_limit", "user", clear=True), _item("personal_token", "user", clear=True)])

    assert (second.id, json.loads(second.value_json)) == (first.id, 9), "the same row, updated"
    assert cleared.success_count == 2, "clearing a field never written succeeds too"
    await _assert_nothing_written(engine)
    assert _state((await _fields(engine, alice))["results_limit"]) == (10, False, "default", False, True, None)


@pytest.mark.asyncio
async def test_a_secret_written_under_another_instance_key_is_unreadable_until_written_again(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    """2: the key changed (a restore without it, a lost key file): «set but unreadable», never a wrong value; a new write cures it."""
    admin = people["admin"]
    await _write(engine, admin, [_item("api_key", "system", secret_value=_secret())])
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)

    unreadable = (await _fields(engine, admin))["api_key"]
    await _write(engine, admin, [_item("api_key", "system", secret_value=_secret())])
    rewritten = (await _fields(engine, admin))["api_key"]

    assert _state(unreadable) == (None, True, "db", False, True, "unreadable")
    assert _state(rewritten) == (None, True, "db", False, True, None)


@pytest.mark.asyncio
async def test_a_row_the_field_refuses_now_shows_as_invalid_stored(engine: AsyncEngine, people: dict[str, User]):
    """2: a value an older declaration accepted: the default applies, and the interface is told why."""
    async with AsyncSession(engine) as session:
        session.add(PluginSystemSetting(family="asset", plugin_code="mockprov", field_key="region", value_json='"atlantis"'))
        await session.commit()

    region = (await _fields(engine, people["admin"]))["region"]

    assert _state(region) == ("eu", False, "default", False, True, "invalid_stored") and region.updated_at is not None


# =============================================================================
# 3. ALL OR NOTHING, AND EVERY REFUSAL
# =============================================================================


@pytest.mark.asyncio
async def test_one_refused_item_refuses_the_whole_write(engine: AsyncEngine, people: dict[str, User]):
    """3: every item is checked; the refusal lists each one in order with its outcome, and nothing is written."""
    print_section("3: all or nothing")
    alice, admin = people["alice"], people["admin"]

    by_alice = await _refused(engine, alice, [_item("results_limit", "user", value=7), _item("personal_token", "user", secret_value=_secret()), _item("region", "system", value="us")])
    by_admin = await _refused(engine, admin, [_item("region", "system", value="us"), _item("results_limit", "user", value=0)])

    assert _outcomes(by_alice) == [("results_limit", True, None), ("personal_token", True, None), ("region", False, FORBIDDEN)]
    assert _outcomes(by_admin) == [("region", True, None), ("results_limit", False, INVALID)]
    await _assert_nothing_written(engine)
    print_success("refused as a whole, every item reported, nothing written")


@pytest.mark.parametrize(
    "item",
    [
        pytest.param(_item("api_key", "system", secret_value="a-system-secret-1"), id="mockprov-api_key"),
        pytest.param(_item("region", "system", value="us"), id="mockprov-region"),
        pytest.param(_item("price_tolerance", "system", value=1.0), id="mockprov-price_tolerance"),
        pytest.param(_item("verbose", "system", value=True), id="mockprov-verbose"),
        pytest.param(_fx("api_key", secret_value="a-system-secret-1"), id="MOCKFX-api_key"),
        pytest.param(_fx("decimals", value=3), id="MOCKFX-decimals"),
        pytest.param(_item("region", "system", clear=True), id="a-clear-too"),
    ],
)
@pytest.mark.asyncio
async def test_a_member_cannot_write_a_system_field(engine: AsyncEngine, people: dict[str, User], item: PluginSettingWriteItem):
    """3: ``FORBIDDEN_SCOPE`` for every system field of both families, a clear included."""
    assert _outcomes(await _refused(engine, people["bob"], [item])) == [(item.field_key, False, FORBIDDEN)]
    await _assert_nothing_written(engine)


@pytest.mark.parametrize(
    "item",
    [
        pytest.param(_item("no_such_field", "user", value=1), id="unknown-key"),
        pytest.param(_item("region", "user", value="us"), id="system-field-as-user"),
        pytest.param(_item("results_limit", "system", value=5), id="user-field-as-system"),
        pytest.param(_item("region", "system", code="no_such_plugin", value="us"), id="unknown-plugin"),
        pytest.param(_item("decimals", "system", code="MOCKFX", value=3), id="fx-plugin-under-asset"),
        pytest.param(_fx("region", value="us"), id="asset-field-under-fx"),
        pytest.param(_item("decimals", "user", family="fx", code="MOCKFX", value=3), id="fx-has-no-user-field"),
        pytest.param(_item("region", "system", family="fx", code="MOCKFX_FAIL", value="us"), id="plugin-without-fields"),
    ],
)
@pytest.mark.asyncio
async def test_an_unknown_plugin_field_or_scope_is_unknown_field(engine: AsyncEngine, people: dict[str, User], item: PluginSettingWriteItem):
    assert _outcomes(await _refused(engine, people["admin"], [item])) == [(item.field_key, False, UNKNOWN)]


@pytest.mark.parametrize(
    ("item", "reason"),
    [
        pytest.param(_item("results_limit", "user", value=0), "below the minimum", id="integer-below"),
        pytest.param(_item("results_limit", "user", value=51), "above the maximum", id="integer-above"),
        pytest.param(_item("results_limit", "user", value="7"), "expected a number", id="integer-as-text"),
        pytest.param(_item("results_limit", "user", value=7.5), "expected a whole number", id="integer-fractional"),
        pytest.param(_item("results_limit", "user", value=True), "expected a number", id="integer-as-boolean"),
        pytest.param(_item("preferred_language", "user", value="de"), "not one of the options", id="select-other"),
        pytest.param(_item("price_tolerance", "system", value=-1), "below the minimum", id="number-below"),
        pytest.param(_item("verbose", "system", value="true"), "expected true or false", id="boolean-as-text"),
        pytest.param(_item("api_key", "system", secret_value="seven77"), "too short", id="secret-too-short"),
        pytest.param(_item("api_key", "system", secret_value="tab\tinside-a-secret"), "control characters", id="secret-with-a-tab"),
    ],
)
@pytest.mark.asyncio
async def test_a_value_the_field_refuses_is_invalid_value(engine: AsyncEngine, people: dict[str, User], item: PluginSettingWriteItem, reason: str):
    (result,) = await _refused(engine, people["admin"], [item])
    assert (result.success, result.error_code) == (False, INVALID) and reason in result.message


@pytest.mark.parametrize(
    "write",
    [
        pytest.param({}, id="nothing"),
        pytest.param({"value": 7, "clear": True}, id="value-and-clear"),
        pytest.param({"value": 7, "secret_value": "lfsecret-both-0001"}, id="value-and-secret"),
        pytest.param({"secret_value": "lfsecret-both-0001", "clear": True}, id="secret-and-clear"),
    ],
)
@pytest.mark.asyncio
async def test_exactly_one_of_value_secret_value_and_clear(engine: AsyncEngine, people: dict[str, User], write: dict):
    (result,) = await _refused(engine, people["alice"], [_item("results_limit", "user", **write)])
    assert (result.error_code, result.message) == (INVALID, "give exactly one of value, secret_value and clear")


@pytest.mark.asyncio
async def test_a_secret_travels_in_secret_value_only_and_is_never_repeated(engine: AsyncEngine, people: dict[str, User]):
    """3: a secret given as ``value``, a plain value given as ``secret_value``: refused, and the message holds neither."""
    secret, plain = _secret(), _secret()

    results = await _refused(engine, people["admin"], [_item("api_key", "system", value=secret), _item("region", "system", secret_value=plain)])

    assert [(result.error_code, result.message) for result in results] == [(INVALID, "a secret is written in secret_value"), (INVALID, "this field is not secret: write it in value")]
    assert secret not in repr(results) and plain not in repr(results)


@pytest.mark.asyncio
async def test_the_same_field_twice_is_refused_at_its_second_occurrence(engine: AsyncEngine, people: dict[str, User]):
    results = await _refused(engine, people["admin"], [_item("region", "system", value="us"), _item("region", "system", value="eu"), _item("verbose", "system", value=True)])

    assert _outcomes(results) == [("region", True, None), ("region", False, INVALID), ("verbose", True, None)]
    assert results[1].message == "the field appears twice in this write"
    await _assert_nothing_written(engine)


@pytest.mark.asyncio
async def test_no_refusal_message_contains_the_value(engine: AsyncEngine, people: dict[str, User]):
    """3: one write refused for every reason at once, each carrying a marker: no marker in any outcome."""
    markers = [_secret() for _ in range(5)]
    sent = ["Q" + markers[0][-6:], markers[1], markers[2], markers[3], markers[4]]
    items = [
        _item("api_key", "system", secret_value=sent[0]),
        _item("personal_token", "user", value=sent[1]),
        _item("preferred_language", "user", value=sent[2]),
        _item("region", "system", secret_value=sent[3]),
        _item(markers[4][:20], "user", value=sent[4]),
    ]

    results = await _refused(engine, people["admin"], items)

    assert [result.error_code for result in results] == [INVALID, INVALID, INVALID, INVALID, UNKNOWN], "barrier: each item is refused, each for its own rule"
    assert not any(value in (result.message or "") for value in sent for result in results)


# -----------------------------------------------------------------------------
# X-R43: an integer past what a double holds
# -----------------------------------------------------------------------------


def _huge(sign: int = 1) -> int:
    """An integer of 401 random digits, the first not 0, of the given sign: past the double range (about 309 digits)
    like 10**400, and digits no message can show a run of by chance."""
    return sign * int(random.choice("123456789") + "".join(random.choices("0123456789", k=400)))


def _shows_a_run_of(number: int, text: str, width: int = 20) -> bool:
    """Whether ``text`` holds ``width`` consecutive digits of ``number``: the value whole, or any long piece of it."""
    digits = str(abs(number))
    return any(digits[start : start + width] in text for start in range(len(digits) - width + 1))


async def _refused_not_crashed(engine: AsyncEngine, user: User, items: list[PluginSettingWriteItem], story: str) -> list[PluginSettingWriteResult]:
    """The outcome of every item of a write that must be refused. Any other exception fails the test, naming it — the
    route answers 500 to it —, and so does a write that goes through."""
    try:
        written = await _write(engine, user, items)
    except PluginSettingsRefused as refused:
        return refused.results
    except Exception as error:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(f"{story} raised {type(error).__name__} ({error}) instead of PluginSettingsRefused (X-R43): PATCH /settings/plugins/bulk answers 500 where the write's refusal, 422 INVALID_VALUE «too large», is due")
    pytest.fail(f"{story} was written ({written.success_count} item(s)) instead of being refused «too large» (X-R43)")


@pytest.mark.parametrize(
    ("who", "key", "scope", "sign", "beside"),
    [
        pytest.param("alice", "results_limit", "user", 1, _item("preferred_language", "user", value="it"), id="a-members-integer"),
        pytest.param("alice", "results_limit", "user", -1, _item("preferred_language", "user", value="it"), id="a-members-integer-negative"),
        pytest.param("admin", "price_tolerance", "system", 1, _item("region", "system", value="us"), id="an-administrators-number"),
    ],
)
@pytest.mark.asyncio
async def test_an_integer_past_the_double_range_is_invalid_value_and_nothing_is_written(engine: AsyncEngine, people: dict[str, User], who: str, key: str, scope: str, sign: int, beside: PluginSettingWriteItem):
    """Red today (X-R43): ``OverflowError`` escapes ``write_settings`` — the finiteness check of ``validate_value``
    cannot convert 401 digits to a double, and ``_check_item`` catches ``SettingValueError`` only —, so the route
    answers 500 where the write's refusal is due.

    Contract: ``PluginSettingsRefused`` listing every item in order: the valid one beside it accepted, the huge one
    ``INVALID_VALUE`` «too large», never with its digits; nothing written, the valid item included (all or nothing)."""
    print_section(f"X-R43: {who} writes {key} = {'minus ' if sign < 0 else ''}401 digits")
    value = _huge(sign)

    results = await _refused_not_crashed(engine, people[who], [beside, _item(key, scope, value=value)], f"{who}'s write of {key} with {'minus ' if sign < 0 else ''}401 digits")

    assert _outcomes(results) == [(beside.field_key, True, None), (key, False, INVALID)], _outcomes(results)
    refusal = results[1].message or ""
    assert "too large" in refusal, f"the refusal must say why: {refusal!r}"
    assert not _shows_a_run_of(value, repr(results)), "the refusal repeats the value"
    await _assert_nothing_written(engine)
    print_success(f"refused as a whole: {refusal}")


@pytest.mark.parametrize(
    ("who", "item", "reason"),
    [
        pytest.param("alice", _item("results_limit", "user", value=51), "above the maximum of 50", id="51"),
        pytest.param("alice", _item("results_limit", "user", value=2**53 - 1), "above the maximum of 50", id="the-largest-safe-integer"),
        pytest.param("alice", _item("results_limit", "user", value=-(2**53 - 1)), "below the minimum of 1", id="the-largest-safe-integer-negative"),
        pytest.param("admin", _item("price_tolerance", "system", value=1e300), "above the maximum of 10", id="a-float-of-1e300"),
    ],
)
@pytest.mark.asyncio
async def test_a_number_within_the_safe_limit_is_still_judged_by_the_bounds(engine: AsyncEngine, people: dict[str, User], who: str, item: PluginSettingWriteItem, reason: str):
    """Guard: green today and after (X-R43). Only an integer past ``MAX_SAFE_INTEGER`` in absolute value is «too large»:
    51, the largest safe integer of either sign and a float of 1e300 are refused by the bounds, as today; nothing written."""
    (result,) = await _refused(engine, people[who], [item])

    assert (result.success, result.error_code) == (False, INVALID), _outcomes([result])
    assert reason in (result.message or "") and "too large" not in (result.message or ""), result.message
    await _assert_nothing_written(engine)


# =============================================================================
# 3. LOCKED BY THE ENVIRONMENT
# =============================================================================


@pytest.mark.parametrize(
    ("variable", "key", "write", "named"),
    [
        pytest.param(REGION_VARIABLE, "region", {"value": "us"}, REGION_VARIABLE, id="derived-name"),
        pytest.param(REGION_VARIABLE + "_FILE", "region", {"value": "us"}, REGION_VARIABLE, id="derived-name-_FILE"),
        pytest.param(API_KEY_ALIAS, "api_key", {"secret_value": "a-system-secret-1"}, API_KEY_ALIAS, id="alias"),
        pytest.param(API_KEY_ALIAS + "_FILE", "api_key", {"secret_value": "a-system-secret-1"}, API_KEY_ALIAS, id="alias-_FILE"),
    ],
)
@pytest.mark.asyncio
async def test_a_field_the_environment_sets_is_locked(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch, tmp_path: Path, variable, key, write, named):
    """3: ``LOCKED_BY_ENV`` for the administrator, naming the field's variable (its ``_FILE`` form under the same name), never its value; read-only for all."""
    print_section(f"3: locked by {variable}")
    value = _secret()
    if variable.endswith("_FILE"):
        holder = tmp_path / "value.txt"
        holder.write_text("us" if key == "region" else value, encoding="utf-8")
        monkeypatch.setenv(variable, str(holder))
    else:
        monkeypatch.setenv(variable, "us" if key == "region" else value)
    admin, alice = people["admin"], people["alice"]

    (result,) = await _refused(engine, admin, [_item(key, "system", **write)])
    (forbidden,) = await _refused(engine, alice, [_item(key, "system", **write)])
    as_admin, as_alice = (await _fields(engine, admin))[key], (await _fields(engine, alice))[key]

    assert (result.error_code, forbidden.error_code) == (LOCKED, FORBIDDEN), "a member is refused for the scope before the lock"
    assert result.message == f"set by the environment variable {named}" and value not in result.message
    shown = "us" if key == "region" else None
    assert _state(as_admin) == (shown, True, "env", True, False, None) and _state(as_alice) == (shown, True, "env", True, False, None)
    assert as_admin.env_variable == variable.removesuffix("_FILE") and as_alice.env_variable is None, "the variable is named to an administrator only"
    await _assert_nothing_written(engine)
    print_success(f"locked: {result.message}")


@pytest.mark.asyncio
async def test_an_invalid_variable_still_locks_and_shows_its_problem(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(REGION_VARIABLE, "atlantis")

    (result,) = await _refused(engine, people["admin"], [_item("region", "system", value="us")])
    region = (await _fields(engine, people["admin"]))["region"]

    assert result.error_code == LOCKED
    assert _state(region) == (None, True, "env", True, False, "invalid_env")


@pytest.mark.asyncio
async def test_the_environment_never_locks_a_user_field(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(env_name("asset", "mockprov", "results_limit"), "5")

    written = await _write(engine, people["alice"], [_item("results_limit", "user", value=7)])

    assert written.success_count == 1
    assert _state((await _fields(engine, people["alice"]))["results_limit"]) == (7, True, "db", False, True, None)


# =============================================================================
# 3. THE MANAGED PROFILE
# =============================================================================


@pytest.mark.asyncio
async def test_in_the_managed_profile_a_locked_field_does_not_exist(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    """3: the hoster sets it, the customer never sees it: absent from the catalogue, ``UNKNOWN_FIELD`` to write, for everyone."""
    print_section("3: the managed profile")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(REGION_VARIABLE, "us")
    assert service._is_managed(), "barrier: the service reads the managed profile, or nothing below is about it"
    admin, alice = people["admin"], people["alice"]

    as_admin, as_alice = await _fields(engine, admin), await _fields(engine, alice)
    refusals = [await _refused(engine, user, [_item("region", "system", value="eu")]) for user in (admin, alice)]
    written = await _write(engine, admin, [_item("verbose", "system", value=True)])

    assert set(as_admin) == set(as_alice) == set(MOCKPROV_KEYS) - {"region"}
    assert [_outcomes(results) for results in refusals] == [[("region", False, UNKNOWN)], [("region", False, UNKNOWN)]]
    assert written.success_count == 1, "the fields the environment does not set behave as usual"
    print_success("region hidden and unknown, verbose still writable")


@pytest.mark.asyncio
async def test_in_the_managed_profile_a_plugin_whose_fields_are_all_locked_is_not_listed(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(env_name("fx", "MOCKFX", "api_key"), _secret())
    monkeypatch.setenv(env_name("fx", "MOCKFX", "decimals"), "4")

    assert await _fields(engine, people["admin"], "MOCKFX") == {}
    assert set(await _fields(engine, people["admin"], "mockprov")) == set(MOCKPROV_KEYS), "managed alone hides nothing"


@pytest.mark.parametrize(("value", "configured"), [pytest.param("us", True, id="a-valid-variable"), pytest.param("atlantis", False, id="an-invalid-variable")])
@pytest.mark.asyncio
async def test_in_the_managed_profile_configured_counts_a_hidden_field_without_naming_it(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch, value: str, configured: bool):
    """3 (decision N2): ``region`` locked by its variable is hidden; valid, the plugin stays configured; invalid, it is
    not — and the entry says only that: no field, key, variable or value of the hidden field anywhere in it."""
    print_section(f"3: managed, a hidden field locked by {value!r}")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(REGION_VARIABLE, value)
    assert service._is_managed(), "barrier: the service reads the managed profile, or nothing below is about it"

    entries = {name: await _entry(engine, user, "mockprov") for name, user in people.items()}

    for name, entry in entries.items():
        shown = entry.model_dump_json()
        assert [field.key for field in entry.fields] == [key for key in MOCKPROV_KEYS if key != "region"], name
        assert entry.configured is configured, name
        assert set(entry.model_dump()) == {"family", "plugin_code", "plugin_name", "icon_url", "configured", "fields"}, "the entry has no place for a missing field's name"
        assert "region" not in shown.lower() and REGION_VARIABLE not in shown and "atlantis" not in shown, f"{name}: the hidden field shows: {shown}"
    print_success(f"region hidden for everyone, configured={configured}, named nowhere")


# =============================================================================
# 4. THE KEY
# =============================================================================


def _unusable_key():
    raise InstanceKeyError("LIBREFOLIO_INSTANCE_KEY_FILE (/run/secrets/missing): the instance key cannot be read")


@pytest.mark.asyncio
async def test_a_secret_write_without_a_usable_key_is_refused_and_writes_nothing(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    """4: ``PluginSettingsKeyUnavailable``: the plain items of the same write are not written either."""
    monkeypatch.setattr(service, "settings_subkey", _unusable_key)

    with pytest.raises(PluginSettingsKeyUnavailable):
        await _write(engine, people["admin"], [_item("region", "system", value="us"), _item("api_key", "system", secret_value=_secret())])

    await _assert_nothing_written(engine)


@pytest.mark.asyncio
async def test_a_write_without_a_secret_never_needs_the_key(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    """4: plain values and the clear of a secret are written with the key unusable."""
    monkeypatch.setattr(service, "settings_subkey", _unusable_key)

    written = await _write(engine, people["admin"], [_item("region", "system", value="us"), _item("api_key", "system", clear=True), _item("personal_token", "user", clear=True)])

    assert written.success_count == 3


@pytest.mark.asyncio
async def test_with_an_unusable_key_the_catalogue_still_answers_with_the_stored_secrets_unreadable(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """4: ``LIBREFOLIO_INSTANCE_KEY_FILE`` naming a file that is gone: the catalogue (``GET /settings/plugins``) raises nothing.

    Every stored secret is «set but unreadable», the plain values are as written, one error is logged; a secret write is
    refused with ``PluginSettingsKeyUnavailable``, a plain one goes through.
    """
    print_section("4: the catalogue with an unusable instance key")
    admin, alice = people["admin"], people["alice"]
    await _write(engine, admin, [_item("api_key", "system", secret_value=_secret()), _item("region", "system", value="us")])
    await _write(engine, alice, [_item("personal_token", "user", secret_value=_secret())])
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY")
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY_FILE", str(tmp_path / "gone-instance.key"))

    with capture_logs() as logs:
        as_admin, as_alice = await _fields(engine, admin), await _fields(engine, alice)
    with pytest.raises(PluginSettingsKeyUnavailable):
        await _write(engine, admin, [_item("api_key", "system", secret_value=_secret())])
    written = await _write(engine, admin, [_item("verbose", "system", value=True)])

    assert _state(as_admin["api_key"]) == (None, True, "db", False, True, "unreadable")
    assert _state(as_alice["api_key"]) == (None, True, "db", False, False, "unreadable")
    assert _state(as_alice["personal_token"]) == (None, True, "db", False, True, "unreadable")
    assert as_admin["region"].value == as_alice["region"].value == "us"
    assert [entry["log_level"] for entry in logs if entry["event"].startswith("Plugin secrets unreadable")] == ["error"]
    assert written.success_count == 1
    print_success("the catalogue answers, the secrets unreadable, the plain values intact")


# =============================================================================
# 5. THE LOG OF A WRITE
# =============================================================================


@pytest.mark.asyncio
async def test_the_log_of_a_write_names_the_fields_and_never_a_value(engine: AsyncEngine, people: dict[str, User]):
    """5: one event per accepted write, ``family/code/key:scope:set|clear``; none for a refused one; no value anywhere."""
    print_section("5: the log of a write")
    admin, alice = people["admin"], people["alice"]
    secrets = [_secret(), _secret()]

    with capture_logs() as logs:
        await _write(engine, admin, [_item("api_key", "system", secret_value=secrets[0]), _item("price_tolerance", "system", value=7.25), _fx("decimals", value=3)])
        await _write(engine, alice, [_item("personal_token", "user", secret_value=secrets[1]), _item("results_limit", "user", clear=True)])
        await _refused(engine, alice, [_item("region", "system", value="us")])

    written = [entry for entry in logs if entry.get("event") == "Plugin settings written"]
    assert [(entry["log_level"], entry["user_id"], entry["fields"]) for entry in written] == [
        ("info", admin.id, ["asset/mockprov/api_key:system:set", "asset/mockprov/price_tolerance:system:set", "fx/MOCKFX/decimals:system:set"]),
        ("info", alice.id, ["asset/mockprov/personal_token:user:set", "asset/mockprov/results_limit:user:clear"]),
    ]
    assert all(set(entry) == {"event", "log_level", "user_id", "fields"} for entry in written), written
    everything = repr(logs)
    assert not any(secret in everything for secret in secrets) and "7.25" not in everything
    print_success("who wrote which fields; no value, no secret")


# =============================================================================
# 6. FX
# =============================================================================


@pytest.mark.asyncio
async def test_the_fx_fields_are_written_here_and_reach_a_configured_mockfx(engine: AsyncEngine, people: dict[str, User], monkeypatch: pytest.MonkeyPatch):
    """6: the administrator writes MOCKFX's integer and secret; the rows are the FX family's; MOCKFX receives both."""
    print_section("6: MOCKFX")
    secret = _secret()
    written = await _write(engine, people["admin"], [_fx("decimals", value=3), _fx("api_key", secret_value=secret)])
    (out_of_bounds,) = await _refused(engine, people["admin"], [_fx("decimals", value=11)])
    monkeypatch.setattr(runtime, "get_async_engine", lambda: engine)

    configured = await fx_runtime.configured_fx_provider("MOCKFX")
    system, _user = await _rows(engine)
    view = await _fields(engine, people["alice"], "MOCKFX")

    assert written.success_count == 2 and (out_of_bounds.error_code, out_of_bounds.field_key) == (INVALID, "decimals")
    assert {(row.family, row.plugin_code, row.field_key) for row in system} == {("fx", "MOCKFX", "decimals"), ("fx", "MOCKFX", "api_key")}
    secret_row = next(row for row in system if row.field_key == "api_key")
    assert decrypt_secret(settings_subkey(), secret_aad("fx", "MOCKFX", "api_key", "system", None), secret_row.secret_ciphertext) == secret
    assert (configured.settings.get("decimals"), configured.settings.secret("api_key")) == (3, secret)
    assert (_state(view["decimals"]), _state(view["api_key"])) == ((3, True, "db", False, False, None), (None, True, "db", False, False, None))
    print_success("written, encrypted for the FX family, delivered to MOCKFX")

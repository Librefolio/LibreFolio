"""The values of a Tool on a private database (CP12, X5-4b): resolved for a caller, listed in the catalogue, written by a user.

Modules under test: ``services/plugin_settings/runtime.py`` (``configure_instance(…, plugin_code=…)``, ``bound_settings_for``
for a tool code), the new ``services/tools/settings.py`` (``bound_settings_for_batch``) and ``services/plugin_settings/service.py``
(the ``tool`` family of the catalogue and of the writes). The contract pinned here:

1. **A Tool has no ``provider_code``**: ``configure_instance`` takes the plugin's code as ``plugin_code`` and, when given, it
   replaces the attribute; ``bound_settings_for(ToolPluginRegistry-like, tool_code, user_id=…)`` binds the values of the tool code.
2. **The parent resolves the values of a batch** (``bound_settings_for_batch(batch, *, user_id, registry=ToolPluginRegistry)``): one
   ``BoundSettings`` per distinct tool code whose plugin declares a field, the instance's values and the caller's own; a Tool
   without fields, or unknown, is absent and costs no database read; a ``system`` field ignores a user row; another user's
   values never appear; each service of a bundle has its own values.
3. **The catalogue lists the Tools by tool code** (``FAMILY_REGISTRIES["tool"]``, name = ``ToolService.name``, no icon), a
   ``test_only`` one only when named; the write path accepts ``family="tool"`` with the rules of every family (an
   administrator for the instance's fields, the owner for a personal one, a variable locks, a value the field refuses is
   refused, all or nothing, no secret).

Pure: the rows live in a private SQLite file under ``tmp_path`` reached through a private engine put in place of
``runtime.get_async_engine``; no product Tool is used (the Tools are those of ``_tool_settings_fixtures``, in a private
registry put in the catalogue's place of the Tool registry with ``monkeypatch``).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.schemas.plugin_settings import PluginSettingErrorCode, PluginSettingFamily, PluginSettingsPluginRead, PluginSettingWriteItem
from backend.app.schemas.tools import ToolComputeBatchRequest
from backend.app.services.plugin_settings import resolver, runtime, service
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import env_name, env_variables
from backend.app.services.plugin_settings.service import PluginSettingsRefused, read_catalogue, write_settings
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.test_scripts.test_services import _brim_settings_lab as brim_lab
from backend.test_scripts.test_services import _tool_settings_fixtures as fx

ROUNDING, PAIR_A, PAIR_B, REQUIRED, PLAIN, TESTONLY = fx.ROUNDING_CODE, fx.PAIR_A_CODE, fx.PAIR_B_CODE, fx.REQUIRED_CODE, fx.PLAIN_CODE, fx.TESTONLY_CODE
LISTED = {ROUNDING, PAIR_A, PAIR_B, REQUIRED}
UNKNOWN, FORBIDDEN, LOCKED, INVALID = (PluginSettingErrorCode.UNKNOWN_FIELD, PluginSettingErrorCode.FORBIDDEN_SCOPE, PluginSettingErrorCode.LOCKED_BY_ENV, PluginSettingErrorCode.INVALID_VALUE)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode, a data directory of this test, the self-hosted profile, no ambient variable of a fixture Tool."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    for code in (ROUNDING, PAIR_A, PAIR_B, REQUIRED, TESTONLY):
        for declared in (*fx.ROUNDING_FIELDS, fx.REGION):
            for name in {*env_variables("tool", code, declared), env_name("tool", code, declared.key)}:
                monkeypatch.delenv(name, raising=False)
                monkeypatch.delenv(name + "_FILE", raising=False)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    yield
    fx.release_fixture_claims()


@pytest.fixture
def registry() -> type[ToolPluginRegistry]:
    """A private Tool registry: the worked example, a two-service bundle, a Tool with a required field, a Tool without
    fields and a ``test_only`` one."""
    return fx.private_registry(fx.RoundingToolPlugin, fx.PairToolPlugin, fx.RequiredToolPlugin, fx.PlainToolPlugin, fx.OnlyForTestsToolPlugin)


@pytest.fixture
def as_the_tool_family(registry: type[ToolPluginRegistry], monkeypatch: pytest.MonkeyPatch) -> type[ToolPluginRegistry]:
    """The catalogue and the writes read the private registry as the ``tool`` family."""
    monkeypatch.setitem(service.FAMILY_REGISTRIES, "tool", registry)
    return registry


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema, opened as production opens its own; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def through_private_engine(private_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The settings rows are read through the private engine; the list counts the reads."""
    reads: list[int] = []

    def engine() -> AsyncEngine:
        reads.append(1)
        return private_engine

    monkeypatch.setattr(runtime, "get_async_engine", engine)
    return reads


def _no_database() -> AsyncEngine:
    raise AssertionError("the database was reached: a Tool that declares no field has nothing to read")


@pytest_asyncio.fixture
async def people(private_engine: AsyncEngine) -> dict[str, User]:
    """An administrator and two members of the private database."""
    async with AsyncSession(private_engine, expire_on_commit=False) as session:
        created = {
            "admin": User(username="admin", email="admin@example.test", hashed_password="$argon2id$test", is_superuser=True),
            "alice": User(username="alice", email="alice@example.test", hashed_password="$argon2id$test"),
            "bob": User(username="bob", email="bob@example.test", hashed_password="$argon2id$test"),
        }
        session.add_all(created.values())
        await session.commit()
    return created


async def _store(engine: AsyncEngine, *rows: PluginSystemSetting | PluginUserSetting) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all(rows)
        await session.commit()


def _system(code: str, key: str, value_json: str, family: str = "tool") -> PluginSystemSetting:
    return PluginSystemSetting(family=family, plugin_code=code, field_key=key, value_json=value_json)


def _user(user: User, code: str, key: str, value_json: str, family: str = "tool") -> PluginUserSetting:
    return PluginUserSetting(user_id=user.id, family=family, plugin_code=code, field_key=key, value_json=value_json)


@pytest_asyncio.fixture
async def rows(private_engine: AsyncEngine, people: dict[str, User]) -> dict[str, User]:
    """The rounding Tool's instance value and the users' personal ones, with decoys that must never be read: the same keys
    under another family, under the sibling service, and bob's value."""
    await _store(
        private_engine,
        _system(ROUNDING, "max_points", "700"),
        _user(people["alice"], ROUNDING, "rounding", '"half_up"'),
        _user(people["bob"], ROUNDING, "rounding", '"half_even"'),
        _system(ROUNDING, "max_points", "9000", family="asset"),
        _user(people["alice"], ROUNDING, "rounding", '"half_even"', family="asset"),
        _system(PAIR_B, "max_points", "9000"),
        _user(people["alice"], PAIR_B, "rounding", '"half_up"'),
    )
    return people


def _resolver():
    """``bound_settings_for_batch``, imported when a test runs: the module is new (every test is red on its own, not the file)."""
    from backend.app.services.tools.settings import bound_settings_for_batch  # noqa: PLC0415 — see the docstring

    return bound_settings_for_batch


def _batch(registry: type[ToolPluginRegistry], *codes: str) -> ToolComputeBatchRequest:
    return ToolComputeBatchRequest(request_id="r1", items=[fx.item_for(registry, code, correlation=f"c{index}") for index, code in enumerate(codes)])


def _ghost_batch(registry: type[ToolPluginRegistry], *codes: str) -> ToolComputeBatchRequest:
    """Items naming codes the registry does not know (only the code matters to the resolver)."""
    base = fx.item_for(registry, ROUNDING)
    return ToolComputeBatchRequest(request_id="r1", items=[base.model_copy(update={"tool_code": code, "correlation_id": f"g{index}"}) for index, code in enumerate(codes)])


# =============================================================================
# 1. configure_instance AND bound_settings_for FOR A TOOL CODE
# =============================================================================


@pytest.mark.asyncio
async def test_configure_instance_takes_the_plugin_code_of_a_tool(rows: dict[str, User], through_private_engine: list[int]):
    """A tool plugin has no ``provider_code``: the code is given. Alice gets her own value and the instance's; the decoy rows
    of another family and of the sibling service do not reach it."""
    plugin = fx.RoundingToolPlugin()
    assert not hasattr(plugin, "provider_code"), "barrier: a Tool has no provider_code"

    configured = await runtime.configure_instance(plugin, "tool", user_id=rows["alice"].id, plugin_code=ROUNDING)

    assert configured is plugin
    assert (plugin.settings.get("rounding"), plugin.settings.get("max_points"), plugin.settings.missing) == ("half_up", 700, ())
    assert len(through_private_engine) == 1


@pytest.mark.asyncio
async def test_a_given_plugin_code_replaces_the_attribute(rows: dict[str, User], through_private_engine: list[int], private_engine: AsyncEngine):
    """For a plugin that does have a ``provider_code``, a given ``plugin_code`` wins: the rows read are the given code's."""
    await _store(private_engine, _system("other_brim", "region", '"us"', family="brim"), _system(brim_lab.CODE, "region", '"eu"', family="brim"))

    plugin = await runtime.configure_instance(brim_lab.SettingsBrimPlugin(), "brim", plugin_code="other_brim")

    assert plugin.settings.get("region") == "us", "the rows of the given code, not of the attribute"
    assert (await runtime.configure_instance(brim_lab.SettingsBrimPlugin(), "brim")).settings.get("region") == "eu", "without it, the attribute as before"


@pytest.mark.asyncio
async def test_each_service_of_a_bundle_is_configured_by_its_own_tool_code(rows: dict[str, User], through_private_engine: list[int]):
    """The two services of one plugin class: ``settings_pair_a`` has no row, ``settings_pair_b`` has its own (and alice's)."""
    alice = rows["alice"].id
    a = await runtime.configure_instance(fx.PairToolPlugin(), "tool", user_id=alice, plugin_code=PAIR_A)
    b = await runtime.configure_instance(fx.PairToolPlugin(), "tool", user_id=alice, plugin_code=PAIR_B)

    assert (a.settings.get("rounding"), a.settings.get("max_points")) == ("half_even", 500), "defaults: no row of this service"
    assert (b.settings.get("rounding"), b.settings.get("max_points")) == ("half_up", 9000)


@pytest.mark.asyncio
async def test_bound_settings_for_works_for_a_tool_code(rows: dict[str, User], through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """The registry hands out the plugin by tool code; the values are those ``configure_instance`` binds, for a user and for nobody."""
    for user in (rows["alice"], rows["bob"], None):
        user_id = user.id if user is not None else None
        bound = await runtime.bound_settings_for(registry, ROUNDING, user_id=user_id)
        instance = await runtime.configure_instance(fx.RoundingToolPlugin(), "tool", user_id=user_id, plugin_code=ROUNDING)

        assert isinstance(bound, BoundSettings), user_id
        assert (bound.plain_values(), bound.secret_values(), bound.missing, bound.fingerprint) == (instance.settings.plain_values(), instance.settings.secret_values(), instance.settings.missing, instance.settings.fingerprint)
    alices = await runtime.bound_settings_for(registry, ROUNDING, user_id=rows["alice"].id)
    bobs = await runtime.bound_settings_for(registry, ROUNDING, user_id=rows["bob"].id)
    nobody = await runtime.bound_settings_for(registry, ROUNDING)
    assert [b.get("rounding") for b in (alices, bobs, nobody)] == ["half_up", "half_even", "half_even"]
    assert {b.get("max_points") for b in (alices, bobs, nobody)} == {700}


@pytest.mark.asyncio
async def test_bound_settings_for_a_tool_without_fields_or_unknown_reads_nothing(monkeypatch: pytest.MonkeyPatch, registry: type[ToolPluginRegistry]):
    """No field, or no such Tool: ``None`` and no database read."""
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)

    assert await runtime.bound_settings_for(registry, PLAIN, user_id=1) is None
    assert await runtime.bound_settings_for(registry, "settings_nowhere", user_id=1) is None


# =============================================================================
# 2. bound_settings_for_batch
# =============================================================================


def test_bound_settings_for_batch_has_the_documented_signature():
    """``(batch, *, user_id, registry=ToolPluginRegistry)``: the caller is always named, the registry defaults to the product's."""
    parameters = inspect.signature(_resolver()).parameters

    assert list(parameters) == ["batch", "user_id", "registry"]
    assert parameters["user_id"].kind is inspect.Parameter.KEYWORD_ONLY and parameters["user_id"].default is inspect.Parameter.empty
    assert parameters["registry"].kind is inspect.Parameter.KEYWORD_ONLY and parameters["registry"].default is ToolPluginRegistry
    assert inspect.iscoroutinefunction(_resolver())


@pytest.mark.asyncio
async def test_the_batch_gets_the_instance_values_and_the_callers_own_by_tool_code(rows: dict[str, User], through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """Alice's batch: her rounding and the instance's max, per tool code; a Tool without fields is not in the mapping; a
    Tool whose required field has no value is, with ``missing`` set."""
    batch = _batch(registry, ROUNDING, PAIR_A, PLAIN, REQUIRED)

    resolved = await _resolver()(batch, user_id=rows["alice"].id, registry=registry)

    assert set(resolved) == {ROUNDING, PAIR_A, REQUIRED}, "the Tool without fields is absent"
    assert all(isinstance(bound, BoundSettings) for bound in resolved.values())
    assert (resolved[ROUNDING].get("rounding"), resolved[ROUNDING].get("max_points")) == ("half_up", 700)
    assert (resolved[PAIR_A].get("rounding"), resolved[PAIR_A].get("max_points")) == ("half_even", 500), "the sibling service's rows are not this one's"
    assert resolved[REQUIRED].missing == ("region",)
    assert resolved[ROUNDING].plain_values() == (await runtime.bound_settings_for(registry, ROUNDING, user_id=rows["alice"].id)).plain_values()


@pytest.mark.asyncio
async def test_another_users_values_do_not_reach_the_batch(rows: dict[str, User], through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """The same batch for three callers: alice's choice reaches alice only; with no caller, the personal defaults."""
    batch = _batch(registry, ROUNDING)

    alice = await _resolver()(batch, user_id=rows["alice"].id, registry=registry)
    bob = await _resolver()(batch, user_id=rows["bob"].id, registry=registry)
    nobody = await _resolver()(batch, user_id=None, registry=registry)

    assert [r[ROUNDING].get("rounding") for r in (alice, bob, nobody)] == ["half_up", "half_even", "half_even"]
    assert {r[ROUNDING].get("max_points") for r in (alice, bob, nobody)} == {700}, "the instance's value is everyone's"
    assert alice[ROUNDING].fingerprint != bob[ROUNDING].fingerprint


@pytest.mark.asyncio
async def test_a_system_field_ignores_a_user_row(rows: dict[str, User], private_engine: AsyncEngine, through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """A user row under the key of an instance field (no write path makes one) is not read: the instance decides."""
    await _store(private_engine, _user(rows["alice"], PAIR_A, "max_points", "9999"))

    resolved = await _resolver()(_batch(registry, PAIR_A), user_id=rows["alice"].id, registry=registry)

    assert resolved[PAIR_A].get("max_points") == 500, "the default: the instance has no row for this service"


@pytest.mark.asyncio
async def test_one_read_per_distinct_tool_code_with_fields(rows: dict[str, User], through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """Four items, three tool codes, one without fields: two short sessions."""
    batch = _batch(registry, ROUNDING, ROUNDING, PAIR_A, PLAIN)

    resolved = await _resolver()(batch, user_id=rows["alice"].id, registry=registry)

    assert set(resolved) == {ROUNDING, PAIR_A}
    assert len(through_private_engine) == 2


@pytest.mark.asyncio
async def test_a_batch_of_tools_without_fields_or_unknown_reads_nothing(monkeypatch: pytest.MonkeyPatch, registry: type[ToolPluginRegistry]):
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)

    assert await _resolver()(_batch(registry, PLAIN), user_id=1, registry=registry) == {}
    assert await _resolver()(_ghost_batch(registry, "settings_nowhere", "settings_other"), user_id=1, registry=registry) == {}


@pytest.mark.asyncio
async def test_the_batch_accepts_any_object_with_items_carrying_a_tool_code(rows: dict[str, User], through_private_engine: list[int], registry: type[ToolPluginRegistry]):
    """Only ``batch.items[*].tool_code`` is read."""
    duck = SimpleNamespace(items=[SimpleNamespace(tool_code=ROUNDING)])

    assert set(await _resolver()(duck, user_id=rows["bob"].id, registry=registry)) == {ROUNDING}


# =============================================================================
# 3. THE CATALOGUE AND THE WRITES
# =============================================================================


async def _catalogue(engine: AsyncEngine, user: User, **filters: Any):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await read_catalogue(session, user, **filters)


async def _entries(engine: AsyncEngine, user: User, **filters: Any) -> dict[str, PluginSettingsPluginRead]:
    return {entry.plugin_code: entry for entry in (await _catalogue(engine, user, family="tool", **filters)).plugins}


async def _write(engine: AsyncEngine, user: User, items: list[PluginSettingWriteItem]):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await write_settings(session, user, items)


def _item(code: str, key: str, scope: str, **write: Any) -> PluginSettingWriteItem:
    return PluginSettingWriteItem(family="tool", plugin_code=code, field_key=key, scope=scope, **write)


def test_the_tool_family_is_wired_into_the_service():
    """The registry of the family; the enum value of the API."""
    assert service.FAMILY_REGISTRIES.get("tool") is ToolPluginRegistry
    assert PluginSettingFamily("tool") is PluginSettingFamily.TOOL and PluginSettingFamily.TOOL.value == "tool"
    assert [family.value for family in PluginSettingFamily][:3] == ["asset", "fx", "brim"], "the families that were there keep their values"


@pytest.mark.asyncio
async def test_the_catalogue_lists_the_tools_by_tool_code(rows: dict[str, User], private_engine: AsyncEngine, as_the_tool_family: type[ToolPluginRegistry]):
    """Family ``tool``, code = tool code, name = ``ToolService.name``, no icon; the Tool without fields and the ``test_only``
    one are not listed; each field as declared, in order, with its state for the caller."""
    for user in (rows["admin"], rows["alice"]):
        entries = await _entries(private_engine, user)

        assert set(entries) == LISTED, "the Tool without fields and the test-only one are not there"
        for code in (ROUNDING, PAIR_A, PAIR_B):
            assert (entries[code].family, entries[code].plugin_name, entries[code].icon_url) == ("tool", fx.NAMES[code], None), code
            assert [field.key for field in entries[code].fields] == ["rounding", "max_points"], code
    alice = await _entries(private_engine, rows["alice"])
    rounding, max_points = alice[ROUNDING].fields
    assert (rounding.scope, rounding.type, rounding.value, rounding.source, rounding.editable) == ("user", "select", "half_up", "db", True)
    assert [option.value for option in rounding.options] == ["half_even", "half_up"]
    assert (max_points.scope, max_points.value, max_points.source, max_points.editable, max_points.minimum, max_points.maximum) == ("system", 700, "db", False, 10, 10_000)
    assert alice[ROUNDING].configured is True and alice[REQUIRED].configured is False, "a required field without a value: not configured"
    admin = await _entries(private_engine, rows["admin"])
    assert admin[ROUNDING].fields[1].editable is True and admin[ROUNDING].fields[0].value == "half_even", "the administrator edits the instance's field and sees no one's personal value"
    assert (await _entries(private_engine, rows["admin"], plugin_code=ROUNDING)).keys() == {ROUNDING}


@pytest.mark.asyncio
async def test_each_service_of_a_bundle_is_listed_with_its_own_values(rows: dict[str, User], private_engine: AsyncEngine, as_the_tool_family: type[ToolPluginRegistry]):
    entries = await _entries(private_engine, rows["alice"])

    values = {code: {field.key: field.value for field in entries[code].fields} for code in (PAIR_A, PAIR_B)}
    assert values == {PAIR_A: {"rounding": "half_even", "max_points": 500}, PAIR_B: {"rounding": "half_up", "max_points": 9000}}


@pytest.mark.asyncio
async def test_a_test_only_tool_is_listed_only_when_named(rows: dict[str, User], private_engine: AsyncEngine, as_the_tool_family: type[ToolPluginRegistry]):
    named = await _entries(private_engine, rows["admin"], plugin_code=TESTONLY)
    everything = await _catalogue(private_engine, rows["admin"])

    assert set(named) == {TESTONLY} and named[TESTONLY].plugin_name == fx.NAMES[TESTONLY]
    assert TESTONLY not in {entry.plugin_code for entry in everything.plugins if entry.family == "tool"}


@pytest.mark.asyncio
async def test_a_user_writes_a_personal_value_and_the_batch_resolves_it(people: dict[str, User], private_engine: AsyncEngine, through_private_engine: list[int], as_the_tool_family: type[ToolPluginRegistry]):
    """The write path takes ``family="tool"``: the row is filed under the tool code; the value reaches her calls only."""
    registry = as_the_tool_family

    response = await _write(private_engine, people["alice"], [_item(PAIR_A, "rounding", "user", value="half_up")])

    assert (response.success_count, [(r.plugin_code, r.field_key, r.success) for r in response.results]) == (1, [(PAIR_A, "rounding", True)])
    async with AsyncSession(private_engine) as session:
        stored = (await session.execute(select(PluginUserSetting))).scalars().all()
    assert [(row.user_id, row.family, row.plugin_code, row.field_key) for row in stored] == [(people["alice"].id, "tool", PAIR_A, "rounding")]
    batch = _batch(registry, PAIR_A, PAIR_B)
    alice = await _resolver()(batch, user_id=people["alice"].id, registry=registry)
    bob = await _resolver()(batch, user_id=people["bob"].id, registry=registry)
    assert [alice[PAIR_A].get("rounding"), alice[PAIR_B].get("rounding"), bob[PAIR_A].get("rounding")] == ["half_up", "half_even", "half_even"]
    entries = await _entries(private_engine, people["alice"])
    assert entries[PAIR_A].fields[0].value == "half_up" and entries[PAIR_B].fields[0].value == "half_even"


@pytest.mark.asyncio
async def test_only_an_administrator_writes_the_instances_value_of_a_tool(people: dict[str, User], private_engine: AsyncEngine, through_private_engine: list[int], as_the_tool_family: type[ToolPluginRegistry]):
    registry = as_the_tool_family
    with pytest.raises(PluginSettingsRefused) as refused:
        await _write(private_engine, people["alice"], [_item(ROUNDING, "max_points", "system", value=800)])
    assert [(r.field_key, r.success, r.error_code) for r in refused.value.results] == [("max_points", False, FORBIDDEN)]

    await _write(private_engine, people["admin"], [_item(ROUNDING, "max_points", "system", value=800)])

    resolved = await _resolver()(_batch(registry, ROUNDING), user_id=people["bob"].id, registry=registry)
    assert resolved[ROUNDING].get("max_points") == 800


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "field", "scope", "write", "refusal"),
    [
        pytest.param(ROUNDING, "rounding", "user", {"value": "banker"}, INVALID, id="a-select-value-that-is-not-an-option"),
        pytest.param(ROUNDING, "rounding", "user", {"value": 3}, INVALID, id="a-select-given-a-number"),
        pytest.param(ROUNDING, "max_points", "system", {"value": 5}, INVALID, id="below-the-minimum"),
        pytest.param(ROUNDING, "max_points", "system", {"value": 20_000}, INVALID, id="above-the-maximum"),
        pytest.param(ROUNDING, "max_points", "system", {"value": 2.5}, INVALID, id="not-a-whole-number"),
        pytest.param(ROUNDING, "rounding", "user", {"secret_value": "a-secret-value-123"}, INVALID, id="a-secret-for-a-field-that-is-not-secret"),
        pytest.param(ROUNDING, "unknown", "user", {"value": "x"}, UNKNOWN, id="an-unknown-field"),
        pytest.param(ROUNDING, "max_points", "user", {"value": 800}, UNKNOWN, id="an-instance-field-written-as-personal"),
        pytest.param("settings_nowhere", "rounding", "user", {"value": "half_up"}, UNKNOWN, id="an-unknown-tool"),
        pytest.param(PLAIN, "rounding", "user", {"value": "half_up"}, UNKNOWN, id="a-tool-without-fields"),
        pytest.param(TESTONLY, "rounding", "user", {"value": "half_up"}, None, id="a-test-only-tool-is-writable-by-name"),
    ],
)
async def test_a_write_the_field_refuses_is_refused_like_in_every_family(code: str, field: str, scope: str, write: dict, refusal: PluginSettingErrorCode | None, people: dict[str, User], private_engine: AsyncEngine, as_the_tool_family: type[ToolPluginRegistry]):
    """The caller is an administrator, so the refusal is the field's, not the scope's."""
    item = _item(code, field, scope, **write)
    if refusal is None:
        assert (await _write(private_engine, people["admin"], [item])).success_count == 1
        return
    with pytest.raises(PluginSettingsRefused) as refused:
        await _write(private_engine, people["admin"], [item])
    assert [r.error_code for r in refused.value.results] == [refusal]
    async with AsyncSession(private_engine) as session:
        assert (await session.execute(select(PluginUserSetting))).scalars().all() == [] and (await session.execute(select(PluginSystemSetting))).scalars().all() == []


@pytest.mark.asyncio
async def test_a_write_is_all_or_nothing_for_tools(people: dict[str, User], private_engine: AsyncEngine, as_the_tool_family: type[ToolPluginRegistry]):
    with pytest.raises(PluginSettingsRefused) as refused:
        await _write(private_engine, people["admin"], [_item(ROUNDING, "rounding", "user", value="half_up"), _item(PAIR_A, "max_points", "system", value=1)])

    assert [(r.plugin_code, r.success) for r in refused.value.results] == [(ROUNDING, True), (PAIR_A, False)]
    async with AsyncSession(private_engine) as session:
        assert (await session.execute(select(PluginUserSetting))).scalars().all() == []


@pytest.mark.asyncio
async def test_a_variable_of_a_tool_code_locks_its_field(monkeypatch: pytest.MonkeyPatch, people: dict[str, User], private_engine: AsyncEngine, through_private_engine: list[int], as_the_tool_family: type[ToolPluginRegistry]):
    """``LIBREFOLIO_PLUGIN_TOOL_<TOOL_CODE>_<FIELD>``: it sets the field of that service, locks it for writes, and reaches the
    batch; the sibling service is not locked."""
    registry = as_the_tool_family
    monkeypatch.setenv(env_name("tool", PAIR_A, "max_points"), "650")

    with pytest.raises(PluginSettingsRefused) as refused:
        await _write(private_engine, people["admin"], [_item(PAIR_A, "max_points", "system", value=800)])
    assert [r.error_code for r in refused.value.results] == [LOCKED]
    assert (await _write(private_engine, people["admin"], [_item(PAIR_B, "max_points", "system", value=800)])).success_count == 1
    entries = await _entries(private_engine, people["admin"])
    locked = entries[PAIR_A].fields[1]
    assert (locked.value, locked.source, locked.locked, locked.env_variable) == (650, "env", True, env_name("tool", PAIR_A, "max_points"))
    resolved = await _resolver()(_batch(registry, PAIR_A, PAIR_B), user_id=people["alice"].id, registry=registry)
    assert (resolved[PAIR_A].get("max_points"), resolved[PAIR_B].get("max_points")) == (650, 800)

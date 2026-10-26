"""Plugin settings API: ``GET /api/v1/settings/plugins`` and ``PATCH /api/v1/settings/plugins/bulk`` (plan 03, CP10 step 6).

Against the lane's server, with the test double ``mockprov`` (four system fields, three user fields, a secret of each
scope), read-only ``MOCKFX``, and the search preferences of two real plugins, ``justetf`` and ``borsa_italiana`` (CP11a).
The contract pinned here:

1. **The catalogue**: a test-only plugin is listed only when ``plugin_code`` names it; ``family`` filters; each field
   shows what its declaration says and its state for the caller; system fields are editable by an administrator only,
   user fields by their owner; ``MOCKFX`` is read-only for a member. Each entry says whether its plugin is
   ``configured`` (a boolean), and carries its icon, ``icon_url``: null or a URL, ``justetf``'s the one
   ``GET /assets/provider`` publishes for it, the test doubles' null. The full catalogue lists ``justetf``
   (``preferred_currency``) and ``borsa_italiana`` (``preferred_language``): one user select each, editable by a
   member, on its default ``all``, configured, its options with their label keys; a member saves them, reads them back
   as theirs, and clears them.
2. **Secrets are write-only**: a secret goes in ``secret_value`` and never comes back — no response of this module
   (every body is collected) ever holds a marker secret; a set secret shows only ``is_set`` and ``source: db``.
3. **All or nothing**: a refused write answers 422 whose ``detail.results`` lists every item with ``success`` and
   ``error_code``, and writes nothing. The codes over HTTP: ``FORBIDDEN_SCOPE`` (a member on a system field),
   ``UNKNOWN_FIELD`` (a bad key, a wrong scope), ``INVALID_VALUE`` (out of range, twice, a secret in ``value``, a value
   with ``clear``), none of their messages holding the value.
4. **No input echo**: FastAPI's own 422 (a missing field, 101 items, a secret that is no string, an extra field, a bad
   enum, in the body or the query) keeps ``loc``, ``msg`` and ``type`` and drops ``input``: the marker never comes back.
5. **Isolation**: a user's own values reach that user only — not an administrator, not another user — in the
   catalogue and in what the plugin receives: ``mockprov`` answers the query ``lf-settings-echo`` with a summary of the
   settings it was given, secrets only as set or unset.
6. **The administrator's path** (one write and one clear of mockprov's four system fields): stored encrypted, shown to a
   member read-only, delivered to the plugin, recorded with the administrator who wrote them; deleting that
   administrator leaves the rows without an author (``SET NULL``); deleting a user deletes the user's rows (``CASCADE``).

7. **The BRIM family** (W-BS): ``family=brim`` is a value of the API's enum (the catalogue's filter, every write item, the
   OpenAPI schema ``PluginSettingFamily``); the server of the lane holds the real BRIM plugins only and none declares a
   setting, so the BRIM group of the catalogue is empty, whether it is asked for or not; a write that names a setting of a
   real BRIM plugin is the all-or-nothing refusal, ``UNKNOWN_FIELD``, never FastAPI's enum error. (The lab BRIM plugin that
   declares settings lives in the service suites: this server cannot hold it.)

**X-R43** (workstream X): a JSON integer of 401 digits is the write's refusal — 422, ``INVALID_VALUE`` «too large», no
digit of it in the answer, nothing written — never a 500; one of 5000 digits, past what the server's JSON parser reads,
is FastAPI's own refusal. «Red today» is the state before the cure; a guard passes before and after.

Isolation. The user fields are written only by accounts this module registers (never ``e2e_test_user``) and go with
them at teardown; the search preferences of ``justetf`` and ``borsa_italiana`` are also cleared in a ``finally`` by the
account that wrote them. The system fields are instance-wide singletons whose values make the fingerprint in the cache keys
of every mockprov call, so the unit is exclusive (its ``exclusive_because`` in the runner): one write-and-clear round,
done by administrators this module creates, and the rows of mockprov's system fields put back exactly as they were
found, after a red too. ``MOCKFX`` is never written over HTTP: its writes are covered on a private database by
``test_plugin_settings_service.py``.
"""

from __future__ import annotations

import json
import random
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.api.v1 import auth as auth_api
from backend.app.config import get_settings
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.plugin_settings import PluginSettingFieldRead
from backend.app.services.accounts import user_service
from backend.app.services.asset_source_providers.mockprov.plugin import SETTINGS_ECHO_QUERY, MockProvider
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME
CATALOGUE = "/settings/plugins"
BULK = "/settings/plugins/bulk"

MOCKPROV_KEYS = [declared.key for declared in MockProvider.settings_fields]
SYSTEM_KEYS = ("api_key", "region", "price_tolerance", "verbose")
USER_KEYS = ("preferred_language", "results_limit", "personal_token")
FIELD_KEYS = frozenset(PluginSettingFieldRead.model_fields)


@pytest.fixture(scope="module")
def test_server():
    """The lane's server (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# =============================================================================
# THE LANE: ACCOUNTS OF THIS MODULE, EVERY RESPONSE RECORDED
# =============================================================================


def _marker(prefix: str = "lfsecret") -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: this module reads and restores its own rows there only."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to touch a database that is not the lane's test database: {database_url}"
    return get_async_engine()


@dataclass(frozen=True)
class _Account:
    user_id: int
    username: str
    cookie: str


@dataclass
class _Lane:
    """What one test created on the lane, and every response body it received."""

    usernames: list[str] = field(default_factory=list)
    bodies: list[str] = field(default_factory=list)

    async def call(self, method: str, path: str, *, account: _Account | None = None, json: Any = None, params: dict | None = None, content: str | None = None) -> httpx.Response:
        """One request from a client of its own: no cookie jar, the session sent explicitly; the body is recorded.

        ``content`` is a JSON text sent as written (``Content-Type: application/json``): a number the client's own
        serializer would not write as it stands (X-R43)."""
        headers = {"Cookie": f"{COOKIE}={account.cookie}"} if account else {}
        if content is not None:
            headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f"{API_BASE}{path}", content=content, json=json, params=params, headers=headers, timeout=TIMEOUT)
        self.bodies.append(response.text)
        return response

    async def member(self, prefix: str) -> _Account:
        """A regular account of this test: registered, then signed in."""
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        password = f"Plugin-Settings-{uuid.uuid4().hex[:12]}"
        registered = await self.call("POST", "/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password})
        assert registered.status_code == 201, f"Setup: registering {username} failed; the lane's registration must be open: {registered.status_code} {registered.text}"
        user = registered.json()["user"]
        assert user["is_superuser"] is False, f"Precondition: {username} registered as the lane's first account, hence its administrator: the api setup (db populate) did not run on this lane"
        login = await self.call("POST", "/auth/login", json={"username": username, "password": password})
        cookie = login.cookies.get(COOKIE)
        assert login.status_code == 200 and cookie, f"Setup: login as {username} failed: {login.status_code} {login.text}"
        return _Account(user["id"], username, cookie)

    async def admin(self, prefix: str) -> _Account:
        """An administrator of this test: registered, promoted through user_service on the lane's database, signed in again."""
        account = await self.member(prefix)
        async with AsyncSession(_lane_engine()) as session:
            done, error = await user_service.set_user_admin(session, account.username, True)
        assert done, f"Setup: promoting {account.username} failed: {error}"
        me = await self.call("GET", "/auth/me", account=account)
        assert me.status_code == 200 and me.json()["user"]["is_superuser"] is True, f"Setup: {account.username} must act as an administrator: {me.text}"
        return account

    def shows(self, *values: str) -> list[str]:
        """The values that appear in any response body this test received."""
        return [value for value in values if any(value in body for body in self.bodies)]


async def _delete_accounts(usernames: list[str]) -> list[str]:
    errors = []
    engine = _lane_engine()
    async with AsyncSession(engine) as session:
        user_ids = list((await session.execute(select(User.id).where(User.username.in_(usernames)))).scalars())
    for user_id in user_ids:
        async with AsyncSession(engine) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_Lane]:
    """The accounts a test creates go at teardown, after a red too: their plugin rows go with them (CASCADE)."""
    created = _Lane()
    try:
        yield created
    finally:
        errors = await _delete_accounts(created.usernames)
        assert not errors, f"Teardown: could not delete this test's accounts: {errors}"


def _item(key: str, scope: str, *, family: str = "asset", code: str = "mockprov", **write: Any) -> dict[str, Any]:
    return {"family": family, "plugin_code": code, "field_key": key, "scope": scope, **write}


async def _fields(lane: _Lane, account: _Account, code: str = "mockprov", family: str | None = None) -> dict[str, dict]:
    """The fields of one plugin as ``account`` sees them, by key; empty when the plugin is not listed."""
    params = {"plugin_code": code} | ({"family": family} if family else {})
    response = await lane.call("GET", CATALOGUE, account=account, params=params)
    assert response.status_code == 200, response.text
    plugins = [plugin for plugin in response.json()["plugins"] if plugin["plugin_code"] == code]
    assert len(plugins) <= 1
    return {field["key"]: field for field in plugins[0]["fields"]} if plugins else {}


async def _entry(lane: _Lane, account: _Account, code: str) -> dict[str, Any]:
    """The catalogue entry of one plugin, named by ``plugin_code``, as ``account`` sees it; listed once, or the test fails."""
    response = await lane.call("GET", CATALOGUE, account=account, params={"plugin_code": code})
    assert response.status_code == 200, response.text
    (entry,) = [plugin for plugin in response.json()["plugins"] if plugin["plugin_code"] == code]
    return entry


async def _write(lane: _Lane, account: _Account, items: list[dict]) -> httpx.Response:
    return await lane.call("PATCH", BULK, account=account, json={"items": items})


def _outcomes(response: httpx.Response) -> list[tuple]:
    """``(field_key, success, error_code)`` of each item of a refused write."""
    assert response.status_code == 422, f"expected the refusal of the write, got {response.status_code}: {response.text}"
    detail = response.json()["detail"]
    assert isinstance(detail, dict) and detail["success_count"] == 0, detail
    return [(result["field_key"], result["success"], result["error_code"]) for result in detail["results"]]


async def _user_rows(user_id: int) -> list[PluginUserSetting]:
    async with AsyncSession(_lane_engine()) as session:
        return list((await session.execute(select(PluginUserSetting).where(PluginUserSetting.user_id == user_id))).scalars())


async def _echo(lane: _Lane, account: _Account) -> dict[str, str]:
    """What mockprov received for ``account``'s search: its summary of the settings, as ``{key: value}``."""
    response = await lane.call("GET", "/assets/provider/search", account=account, params={"q": SETTINGS_ECHO_QUERY, "providers": "mockprov"})
    assert response.status_code == 200, response.text
    echoes = [item["display_name"] for item in response.json()["results"] if item["provider_code"] == "mockprov" and item["identifier"] == "MOCK_SETTINGS"]
    assert len(echoes) == 1, f"mockprov must answer the echo query with one item: {response.text}"
    summary = echoes[0].removeprefix("settings: ")
    return dict(part.split("=", 1) for part in summary.split("; "))


# =============================================================================
# 1. THE CATALOGUE
# =============================================================================


@pytest.mark.asyncio
async def test_a_test_only_plugin_is_listed_only_when_named(lane: _Lane):
    """1: the full catalogue never lists mockprov, MOCKFX or MOCKFX_FAIL; naming one lists it (MOCKFX_FAIL has no field)."""
    print_section("1: test-only plugins in the catalogue")
    member = await lane.member("ps_catalogue")

    everything = await lane.call("GET", CATALOGUE, account=member)
    by_name = await _fields(lane, member)

    assert everything.status_code == 200
    assert not {"mockprov", "MOCKFX", "MOCKFX_FAIL"} & {plugin["plugin_code"] for plugin in everything.json()["plugins"]}
    assert list(by_name) == MOCKPROV_KEYS, "the fields in their declared order"
    assert set(await _fields(lane, member, "MOCKFX")) == {"api_key", "decimals"}
    assert await _fields(lane, member, "MOCKFX_FAIL") == {}
    print_success("hidden unless named; mockprov's seven fields in order")


@pytest.mark.asyncio
async def test_the_family_filter(lane: _Lane):
    member = await lane.member("ps_family")

    assert list(await _fields(lane, member, family="asset")) == MOCKPROV_KEYS
    assert await _fields(lane, member, family="fx") == {}
    assert set(await _fields(lane, member, "MOCKFX", family="fx")) == {"api_key", "decimals"}
    assert await _fields(lane, member, "MOCKFX", family="asset") == {}


@pytest.mark.asyncio
async def test_the_brim_family_is_accepted_and_holds_no_plugin_that_declares_a_setting(lane: _Lane):
    """7: ``family=brim`` answers 200 with no plugin — the server has the real BRIM plugins only, and none declares a
    field —, with or without a plugin named; the full catalogue has no ``brim`` entry. The count is the subject."""
    print_section("7: the BRIM family over HTTP")
    member = await lane.member("ps_brim_family")

    by_family = await lane.call("GET", CATALOGUE, account=member, params={"family": "brim"})
    named = await lane.call("GET", CATALOGUE, account=member, params={"family": "brim", "plugin_code": "broker_generic_csv"})
    everything = await lane.call("GET", CATALOGUE, account=member)

    assert (by_family.status_code, named.status_code, everything.status_code) == (200, 200, 200), (by_family.text, named.text)
    assert by_family.json() == {"plugins": []} and named.json() == {"plugins": []}
    assert [plugin["plugin_code"] for plugin in everything.json()["plugins"] if plugin["family"] == "brim"] == []
    print_success("brim accepted, nothing in it")


@pytest.mark.asyncio
async def test_the_openapi_schema_lists_brim_among_the_plugin_setting_families(lane: _Lane):
    """7: the generated client's enum comes from here: ``asset``, ``fx`` and ``brim``."""
    response = await lane.call("GET", "/openapi.json")

    assert response.status_code == 200, response.text
    family = response.json()["components"]["schemas"]["PluginSettingFamily"]
    assert {"asset", "fx", "brim"} <= set(family["enum"]), family


@pytest.mark.asyncio
async def test_a_write_to_a_setting_of_a_real_brim_plugin_is_an_unknown_field_not_a_bad_request(lane: _Lane):
    """7: the family is valid, the plugin declares nothing: the all-or-nothing refusal with ``UNKNOWN_FIELD`` and nothing
    written, never FastAPI's enum error (a list ``detail``)."""
    member = await lane.member("ps_brim_write")
    secret = _marker()

    refused = await _write(lane, member, [_item("api_key", "system", family="brim", code="broker_generic_csv", secret_value=secret)])

    assert _outcomes(refused) == [("api_key", False, "UNKNOWN_FIELD")]
    assert lane.shows(secret) == []
    assert await _user_rows(member.user_id) == []


@pytest.mark.asyncio
async def test_each_field_shows_its_declaration_and_nothing_of_a_secret(lane: _Lane):
    """1/2: the read schema has no field for a secret's value; a secret has no default and no value, only its state."""
    member = await lane.member("ps_shape")
    fields = await _fields(lane, member)

    for declared in MockProvider.settings_fields:
        shown = fields[declared.key]
        assert set(shown) == FIELD_KEYS, f"{declared.key}: unexpected keys {set(shown) ^ FIELD_KEYS}"
        assert (shown["type"], shown["scope"], shown["secret"], shown["required"], shown["label"]) == (declared.type.value, declared.scope.value, declared.secret, declared.required, declared.label)
        assert [option["value"] for option in shown["options"]] == list(declared.option_values)
        if declared.secret:
            assert (shown["default"], shown["value"]) == (None, None)
    assert fields["results_limit"]["minimum"] == 1 and fields["results_limit"]["maximum"] == 50
    assert fields["personal_token"]["min_length"] == 8


@pytest.mark.asyncio
async def test_system_fields_are_editable_by_an_administrator_only_and_mockfx_is_read_only_for_a_member(lane: _Lane):
    """1: who may write what, as the catalogue tells the interface."""
    print_section("1: editable, by role")
    member, admin = await lane.member("ps_editable"), await lane.admin("ps_editable_admin")

    as_member, as_admin = await _fields(lane, member), await _fields(lane, admin)
    fx_member, fx_admin = await _fields(lane, member, "MOCKFX"), await _fields(lane, admin, "MOCKFX")

    assert not any(field["locked"] for field in as_admin.values()), "precondition: the lane's server sets no mockprov variable"
    assert {key: field["editable"] for key, field in as_member.items()} == {key: key in USER_KEYS for key in MOCKPROV_KEYS}
    assert {key: field["editable"] for key, field in as_admin.items()} == dict.fromkeys(MOCKPROV_KEYS, True)
    assert {key: field["editable"] for key, field in fx_member.items()} == {"api_key": False, "decimals": False}
    assert {key: field["editable"] for key, field in fx_admin.items()} == {"api_key": True, "decimals": True}
    assert all(field["env_variable"] is None for field in [*as_member.values(), *as_admin.values()])
    print_success("member: user fields only, MOCKFX read-only; administrator: everything")


#: The search preferences of the real plugins (CP11a): plugin → (its one field, its options with their label keys).
_SEARCH_PREFERENCES = {
    "justetf": ("preferred_currency", [("all", "pluginSettings.asset.justetf.option.preferred_currency.all"), ("EUR", None), ("USD", None), ("CHF", None), ("GBP", None)]),
    "borsa_italiana": (
        "preferred_language",
        [
            ("all", "pluginSettings.asset.borsa_italiana.option.preferred_language.all"),
            ("it", "pluginSettings.asset.borsa_italiana.option.preferred_language.it"),
            ("en", "pluginSettings.asset.borsa_italiana.option.preferred_language.en"),
        ],
    ),
}


@pytest.mark.asyncio
async def test_the_full_catalogue_lists_the_search_preferences_of_justetf_and_borsa_italiana(lane: _Lane):
    """1: every entry says whether its plugin is configured; justetf and borsa_italiana each list their one user select,
    editable by a member, on its default ``all``, configured, with its options' label keys; the test doubles, named,
    are configured too (no field of theirs is required, the lane sets no variable of theirs)."""
    print_section("1: configured, and the search preferences in the full catalogue")
    member = await lane.member("ps_preferences")

    response = await lane.call("GET", CATALOGUE, account=member)
    doubles = {code: (await _entry(lane, member, code))["configured"] for code in ("mockprov", "MOCKFX")}

    assert response.status_code == 200, response.text
    entries = {entry["plugin_code"]: entry for entry in response.json()["plugins"]}
    assert all(type(entry["configured"]) is bool for entry in entries.values()), f"configured must be a boolean: {entries}"
    assert set(_SEARCH_PREFERENCES) <= set(entries), f"the full catalogue lists {sorted(entries)}"
    for code, (key, options) in _SEARCH_PREFERENCES.items():
        entry = entries[code]
        assert (entry["family"], entry["configured"], [field["key"] for field in entry["fields"]]) == ("asset", True, [key]), code
        (field,) = entry["fields"]
        assert (field["type"], field["scope"], field["secret"], field["required"], field["editable"], field["locked"]) == ("select", "user", False, False, True, False), code
        assert (field["source"], field["value"], field["default"], field["is_set"], field["problem"]) == ("default", "all", "all", False, None), code
        assert (field["label_key"], field["description_key"]) == (f"pluginSettings.asset.{code}.label.{key}", f"pluginSettings.asset.{code}.description.{key}")
        assert [(option["value"], option["label_key"]) for option in field["options"]] == options, code
    assert doubles == {"mockprov": True, "MOCKFX": True}
    print_success("justetf and borsa_italiana: one user select each, on 'all', configured")


@pytest.mark.asyncio
async def test_a_member_saves_the_search_preferences_and_clears_them(lane: _Lane):
    """1: a member writes both preferences and reads them back as theirs; a value outside the options is refused; cleared
    in the end — after a red too — the defaults are back and no row is left."""
    print_section("1: the search preferences, written and cleared")
    member = await lane.member("ps_preference_write")
    preferences = [_item("preferred_currency", "user", code="justetf", value="EUR"), _item("preferred_language", "user", code="borsa_italiana", value="en")]
    try:
        written = await _write(lane, member, preferences)
        saved = {code: (await _fields(lane, member, code))[key] for code, (key, _options) in _SEARCH_PREFERENCES.items()}
        refused = await _write(lane, member, [_item("preferred_currency", "user", code="justetf", value="JPY")])
    finally:
        cleared = await _write(lane, member, [_item(item["field_key"], "user", code=item["plugin_code"], clear=True) for item in preferences])
    restored = {code: (await _fields(lane, member, code))[key] for code, (key, _options) in _SEARCH_PREFERENCES.items()}

    assert written.status_code == 200 and written.json()["success_count"] == 2, written.text
    assert {code: (field["value"], field["source"], field["is_set"]) for code, field in saved.items()} == {"justetf": ("EUR", "db", True), "borsa_italiana": ("en", "db", True)}
    assert _outcomes(refused) == [("preferred_currency", False, "INVALID_VALUE")]
    assert cleared.status_code == 200 and cleared.json()["success_count"] == 2, cleared.text
    assert {code: (field["value"], field["source"], field["is_set"]) for code, field in restored.items()} == dict.fromkeys(_SEARCH_PREFERENCES, ("all", "default", False))
    assert await _user_rows(member.user_id) == [], "nothing left behind"
    print_success("EUR and en saved as the member's own, JPY refused, both cleared")


#: justetf's icon today: what its plugin's ``get_icon`` gives, and ``GET /assets/provider`` publishes.
JUSTETF_ICON = "https://www.justetf.com/android-chrome-144x144.png?v2"


def _a_valid_icon(value: Any) -> bool:
    """``icon_url`` as the catalogue promises it: null, or a non-blank URL without surrounding whitespace."""
    return value is None or (isinstance(value, str) and value != "" and value == value.strip())


@pytest.mark.asyncio
async def test_every_entry_carries_its_plugins_icon(lane: _Lane):
    """1: every entry has ``icon_url``, null or a URL: justetf's is the icon ``GET /assets/provider`` publishes for it;
    mockprov and MOCKFX, named, have none and answer null — the key is there all the same."""
    print_section("1: the plugin's icon in the catalogue")
    member = await lane.member("ps_icon")

    response = await lane.call("GET", CATALOGUE, account=member)
    doubles = [await _entry(lane, member, code) for code in ("mockprov", "MOCKFX")]
    providers = await lane.call("GET", "/assets/provider", account=member, params={"providers": "justetf"})

    assert response.status_code == 200, response.text
    entries = [*response.json()["plugins"], *doubles]
    wrong = {entry["plugin_code"]: entry.get("icon_url", "<no icon_url key>") for entry in entries if "icon_url" not in entry or not _a_valid_icon(entry["icon_url"])}
    assert not wrong, f"every entry must carry icon_url, null or a non-blank URL: {wrong}"
    icons = {entry["plugin_code"]: entry["icon_url"] for entry in entries}
    assert "justetf" in icons, f"the full catalogue lists {sorted(icons)}"
    assert providers.status_code == 200, providers.text
    published = [provider["icon_url"] for provider in providers.json() if provider["code"] == "justetf"]
    assert (icons["justetf"], published) == (JUSTETF_ICON, [JUSTETF_ICON]), "justetf's icon in the catalogue is the one the asset provider list publishes"
    assert (icons["mockprov"], icons["MOCKFX"]) == (None, None)
    print_success("icon_url in every entry; justetf's is the provider list's, the test doubles' null")


# =============================================================================
# 2/3. WRITES: SECRETS WRITE-ONLY, ALL OR NOTHING, EVERY REFUSAL
# =============================================================================


@pytest.mark.asyncio
async def test_a_secret_is_write_only_and_never_comes_back(lane: _Lane):
    """2: written, then read back by its owner: ``is_set`` and ``source: db``, no value; no response body ever holds it."""
    print_section("2: a write-only secret")
    member = await lane.member("ps_secret")
    secret = _marker()

    written = await _write(lane, member, [_item("personal_token", "user", secret_value=secret), _item("results_limit", "user", value=7)])
    fields = await _fields(lane, member)

    assert written.status_code == 200 and written.json()["success_count"] == 2, written.text
    token = fields["personal_token"]
    assert (token["is_set"], token["source"], token["value"], token["problem"], token["locked"]) == (True, "db", None, None, False)
    assert (fields["results_limit"]["value"], fields["results_limit"]["source"]) == (7, "db")
    (row,) = [row for row in await _user_rows(member.user_id) if row.field_key == "personal_token"]
    assert row.value_json is None and row.key_id and secret.encode() not in row.secret_ciphertext
    assert lane.shows(secret) == [], "the secret came back in a response"
    print_success(f"stored encrypted, shown as set; not in any of {len(lane.bodies)} responses")


@pytest.mark.asyncio
async def test_a_refused_write_lists_every_item_and_writes_nothing(lane: _Lane):
    """3: a member's valid user items beside a system one: 422, each item reported in order, no row written."""
    print_section("3: all or nothing over HTTP")
    member = await lane.member("ps_all_or_nothing")
    secret = _marker()

    refused = await _write(lane, member, [_item("results_limit", "user", value=7), _item("personal_token", "user", secret_value=secret), _item("region", "system", value="us")])

    assert _outcomes(refused) == [("results_limit", True, None), ("personal_token", True, None), ("region", False, "FORBIDDEN_SCOPE")]
    assert refused.json()["detail"]["message"] == "1 of 3 plugin setting(s) refused"
    assert await _user_rows(member.user_id) == [], "a refused write must write nothing"
    assert (await _fields(lane, member))["results_limit"]["is_set"] is False
    assert lane.shows(secret) == []
    print_success("422, every item reported, nothing written")


#: (case, items, the outcome of each item). Each case is refused as a whole, so one account can send them all.
_REFUSALS = (
    ("a member on a system field", [_item("verbose", "system", value=True)], [("verbose", False, "FORBIDDEN_SCOPE")]),
    ("an unknown key", [_item("no_such_field", "user", value=1)], [("no_such_field", False, "UNKNOWN_FIELD")]),
    ("a system field as a user's", [_item("region", "user", value="us")], [("region", False, "UNKNOWN_FIELD")]),
    ("a user field as the instance's", [_item("results_limit", "system", value=5)], [("results_limit", False, "UNKNOWN_FIELD")]),
    ("below the range", [_item("results_limit", "user", value=0)], [("results_limit", False, "INVALID_VALUE")]),
    ("above the range", [_item("results_limit", "user", value=51)], [("results_limit", False, "INVALID_VALUE")]),
    ("the same field twice", [_item("results_limit", "user", value=5), _item("results_limit", "user", value=6)], [("results_limit", True, None), ("results_limit", False, "INVALID_VALUE")]),
    ("a secret in value", [_item("personal_token", "user", value="lfsecret-in-the-wrong-place-0001")], [("personal_token", False, "INVALID_VALUE")]),
    ("a value with clear", [_item("results_limit", "user", value=5, clear=True)], [("results_limit", False, "INVALID_VALUE")]),
)


@pytest.mark.asyncio
async def test_each_refusal_has_its_code_and_never_the_value(lane: _Lane):
    """3: the error codes over HTTP, case by case; nothing written; no message holds a value the write carried."""
    print_section("3: the refusals over HTTP")
    member = await lane.member("ps_refusal")
    violations = []

    for case, items, expected in _REFUSALS:
        refused = await _write(lane, member, items)
        found = _outcomes(refused) if refused.status_code == 422 else f"{refused.status_code} {refused.text[:200]}"
        if found != expected:
            violations.append(f"{case}: expected {expected}, got {found}")
        elif "lfsecret-in-the-wrong-place-0001" in refused.text:
            violations.append(f"{case}: the refusal repeats the value: {refused.text[:200]}")

    assert not violations, "\n- " + "\n- ".join(violations)
    assert await _user_rows(member.user_id) == [], "a refused write must write nothing"
    print_success(f"{len(_REFUSALS)} refusals, each with its code, none with the value")


# -----------------------------------------------------------------------------
# X-R43: a JSON integer past what a double holds
# -----------------------------------------------------------------------------


def _digits(count: int) -> str:
    """``count`` random decimal digits, the first not 0: a number no answer can show a run of by chance."""
    return random.choice("123456789") + "".join(random.choices("0123456789", k=count - 1))


def _shows_a_run_of(digits: str, text: str, width: int = 20) -> bool:
    """Whether ``text`` holds ``width`` consecutive digits of ``digits``: the value whole, or any long piece of it."""
    return any(digits[start : start + width] in text for start in range(len(digits) - width + 1))


def _item_text(key: str, scope: str, number: str) -> str:
    """One write item of mockprov as JSON text, its ``value`` the JSON number ``number`` exactly as written: no client
    serializer in between (``json.dumps`` refuses an int past 4300 digits)."""
    return json.dumps(_item(key, scope)).removesuffix("}") + f', "value": {number}}}'


def _shown(field: dict[str, Any]) -> tuple:
    """A field's state as the catalogue shows it: value, source, set, problem."""
    return (field["value"], field["source"], field["is_set"], field["problem"])


_ON_THEIR_DEFAULTS = {"preferred_language": ("all", "default", False, None), "results_limit": (10, "default", False, None)}


@pytest.mark.asyncio
async def test_a_json_integer_of_401_digits_is_refused_too_large_never_a_500(lane: _Lane):
    """Red today (X-R43): 500. The server reads the integer whole (``json.loads`` reads up to 4300 digits), the
    finiteness check of ``validate_value`` cannot convert it to a double, and nobody catches the ``OverflowError``: a
    member who pastes a long number in a numeric setting gets a server error.

    Contract: the write's refusal: 422, ``detail.results`` listing both items — the valid ``preferred_language``
    accepted, ``results_limit`` ``INVALID_VALUE`` «too large» —, no run of the value's digits in the answer, nothing
    written: the member's catalogue shows both fields as before. The member is this test's own, gone at teardown with
    its rows."""
    print_section("X-R43: a JSON integer of 401 digits")
    member = await lane.member("ps_huge_integer")
    before = await _fields(lane, member)
    assert {key: _shown(before[key]) for key in _ON_THEIR_DEFAULTS} == _ON_THEIR_DEFAULTS, "precondition: a new member's fields are on their defaults"
    digits = _digits(401)
    body = '{"items": [' + json.dumps(_item("preferred_language", "user", value="it")) + ", " + _item_text("results_limit", "user", digits) + "]}"

    refused = await lane.call("PATCH", BULK, account=member, content=body)
    after = await _fields(lane, member)

    assert refused.status_code == 422, f"a JSON integer of 401 digits for results_limit answers {refused.status_code} {refused.text[:200]!r}: expected the write's refusal, 422 INVALID_VALUE «too large» (X-R43)"
    assert _outcomes(refused) == [("preferred_language", True, None), ("results_limit", False, "INVALID_VALUE")]
    message = next(result["message"] for result in refused.json()["detail"]["results"] if result["field_key"] == "results_limit") or ""
    assert "too large" in message, f"the refusal must say why: {message!r}"
    assert not _shows_a_run_of(digits, refused.text), "the refusal repeats the value"
    assert await _user_rows(member.user_id) == [], "a refused write must write nothing"
    assert {key: _shown(after[key]) for key in _ON_THEIR_DEFAULTS} == _ON_THEIR_DEFAULTS, "the refused write changed the member's catalogue"
    print_success(f"422, INVALID_VALUE: {message}")


@pytest.mark.asyncio
async def test_a_json_integer_past_what_the_server_reads_is_fastapis_own_refusal(lane: _Lane):
    """Guard: green today and after (X-R43). 5000 digits are past what ``json.loads`` reads (4300): FastAPI refuses the
    body itself — 400 «There was an error parsing the body», or a 422 of its own — never a 500; no run of the digits in
    the answer, nothing written."""
    member = await lane.member("ps_unreadable_integer")
    digits = _digits(5000)

    response = await lane.call("PATCH", BULK, account=member, content='{"items": [' + _item_text("results_limit", "user", digits) + "]}")

    assert response.status_code in (400, 422), f"a JSON integer of 5000 digits answers {response.status_code} {response.text[:200]!r}: expected FastAPI's own refusal of the body, never a 500"
    assert not _shows_a_run_of(digits, response.text), "the answer repeats the value"
    assert await _user_rows(member.user_id) == [], "nothing may be written"


# =============================================================================
# 4. NO INPUT ECHO IN FASTAPI'S OWN 422
# =============================================================================


def _echo_cases(marker: str, number: int) -> list[tuple[str, dict]]:
    """``(name, request)`` of each malformed request carrying ``marker`` (or ``number``) where FastAPI would echo it."""
    item = _item("personal_token", "user", secret_value=marker)
    return [
        ("a missing field beside the secret", {"json": {"items": [{key: value for key, value in item.items() if key != "scope"}]}}),
        ("101 items carrying the secret", {"json": {"items": [item] * 101}}),
        ("a secret that is no string", {"json": {"items": [_item("personal_token", "user", secret_value=number)]}}),
        ("an extra field", {"json": {"items": [item | {"unexpected": marker}]}}),
        ("a bad enum beside the secret", {"json": {"items": [item | {"family": marker}]}}),
        ("a bad enum in the query", {"params": {"family": marker}, "method": "GET"}),
    ]


@pytest.mark.asyncio
async def test_fastapis_422_never_echoes_the_input(lane: _Lane):
    """4: every malformed request is refused by FastAPI's validation, which keeps loc, msg and type and drops input."""
    print_section("4: no input echo")
    member = await lane.member("ps_echo")
    marker, number = _marker(), int(str(uuid.uuid4().int)[:15])
    problems = []

    for name, request in _echo_cases(marker, number):
        method = request.pop("method", "PATCH")
        response = await lane.call(method, CATALOGUE if method == "GET" else BULK, account=member, **request)
        detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
        if response.status_code != 422 or not isinstance(detail, list) or not detail:
            problems.append(f"{name}: expected FastAPI's 422 with a list of errors, got {response.status_code} {response.text[:200]}")
            continue
        if marker in response.text or str(number) in response.text:
            problems.append(f"{name}: the 422 echoes the input: {response.text[:300]}")
        for error in detail:
            if "input" in error or not {"loc", "msg", "type"} <= set(error):
                problems.append(f"{name}: an error must keep loc, msg and type and drop input: {error}")

    assert not problems, "\n- " + "\n- ".join(problems)
    assert await _user_rows(member.user_id) == []
    print_success(f"{len(_echo_cases(marker, number))} malformed requests, no echo, loc/msg/type kept")


# =============================================================================
# 5. ISOLATION, AND WHAT THE PLUGIN RECEIVES
# =============================================================================


@pytest.mark.asyncio
async def test_a_users_values_reach_that_user_only(lane: _Lane):
    """5: alice's values in her catalogue and in what mockprov receives for her; bob and an administrator get the defaults; the administrator's own values are not alice's either."""
    print_section("5: isolation between users")
    alice, bob, admin = await lane.member("ps_alice"), await lane.member("ps_bob"), await lane.admin("ps_isolation_admin")
    alice_secret, admin_secret = _marker(), _marker()

    assert (await _write(lane, alice, [_item("results_limit", "user", value=7), _item("preferred_language", "user", value="it"), _item("personal_token", "user", secret_value=alice_secret)])).status_code == 200
    assert (await _write(lane, admin, [_item("results_limit", "user", value=42), _item("personal_token", "user", secret_value=admin_secret)])).status_code == 200
    views = {name: await _fields(lane, account) for name, account in (("alice", alice), ("bob", bob), ("admin", admin))}
    echoes = {name: await _echo(lane, account) for name, account in (("alice", alice), ("bob", bob), ("admin", admin))}

    mine = {name: {key: (view[key]["value"], view[key]["is_set"]) for key in USER_KEYS} for name, view in views.items()}
    assert mine == {
        "alice": {"preferred_language": ("it", True), "results_limit": (7, True), "personal_token": (None, True)},
        "bob": {"preferred_language": ("all", False), "results_limit": (10, False), "personal_token": (None, False)},
        "admin": {"preferred_language": ("all", False), "results_limit": (42, True), "personal_token": (None, True)},
    }
    received = {name: {key: echo[key] for key in USER_KEYS} for name, echo in echoes.items()}
    assert received == {
        "alice": {"preferred_language": "it", "results_limit": "7", "personal_token": "set"},
        "bob": {"preferred_language": "all", "results_limit": "10", "personal_token": "unset"},
        "admin": {"preferred_language": "all", "results_limit": "42", "personal_token": "set"},
    }
    system_parts = {name: {key: echo[key] for key in SYSTEM_KEYS} for name, echo in echoes.items()}
    assert system_parts["alice"] == system_parts["bob"] == system_parts["admin"], f"the instance's values are the same for everyone: {system_parts}"
    assert lane.shows(alice_secret, admin_secret) == []
    print_success("each user's own values, in the catalogue and in the plugin; the instance's for all")


@pytest.mark.asyncio
async def test_deleting_a_user_deletes_the_users_settings(lane: _Lane):
    """6: ``ON DELETE CASCADE``: the account's rows go with it; another account's stay."""
    print_section("6: a deleted user's settings")
    leaving, staying = await lane.member("ps_leaving"), await lane.member("ps_staying")
    for account in (leaving, staying):
        assert (await _write(lane, account, [_item("results_limit", "user", value=3), _item("personal_token", "user", secret_value=_marker())])).status_code == 200
    assert len(await _user_rows(leaving.user_id)) == 2, "barrier: the rows exist before the deletion"

    deleted = await lane.call("DELETE", "/auth/users/me", account=leaving)

    assert deleted.status_code == 200, deleted.text
    assert await _user_rows(leaving.user_id) == []
    assert len(await _user_rows(staying.user_id)) == 2
    print_success("the deleted account's rows are gone, the other account's stay")


# =============================================================================
# 6. THE ADMINISTRATOR'S PATH: ONE WRITE AND ONE CLEAR OF THE SYSTEM FIELDS
# =============================================================================

_SYSTEM_COLUMNS = ("id", "family", "plugin_code", "field_key", "value_json", "secret_ciphertext", "key_id", "updated_at", "updated_by_user_id")


async def _mockprov_system_rows() -> list[dict[str, Any]]:
    async with AsyncSession(_lane_engine()) as session:
        rows = (await session.execute(select(PluginSystemSetting).where(PluginSystemSetting.family == "asset", PluginSystemSetting.plugin_code == "mockprov").order_by(PluginSystemSetting.id))).scalars()
        return [{column: getattr(row, column) for column in _SYSTEM_COLUMNS} for row in rows]


async def _restore_mockprov_system_rows(snapshot: list[dict[str, Any]]) -> None:
    """Put mockprov's system rows back exactly as they were found: the instance-wide values are not this test's."""
    async with AsyncSession(_lane_engine()) as session:
        await session.execute(delete(PluginSystemSetting).where(PluginSystemSetting.family == "asset", PluginSystemSetting.plugin_code == "mockprov"))
        session.add_all(PluginSystemSetting(**row) for row in snapshot)
        await session.commit()


@pytest_asyncio.fixture
async def mockprov_system_rows_restored(test_server) -> AsyncIterator[list[dict[str, Any]]]:
    """The rows of mockprov's system fields as found, put back after the test, after a red too."""
    snapshot = await _mockprov_system_rows()
    try:
        yield snapshot
    finally:
        await _restore_mockprov_system_rows(snapshot)
        assert await _mockprov_system_rows() == snapshot, "Teardown: mockprov's system rows were not put back as they were"


@pytest.mark.asyncio
async def test_an_administrator_writes_and_clears_the_system_fields(lane: _Lane, mockprov_system_rows_restored: list[dict[str, Any]]):
    """6: written by an administrator, read-only for a member, delivered to the plugin, recorded with their author; the author's deletion leaves them without one; another administrator clears them."""
    print_section("6: the administrator's path")
    writer, clearer, member = await lane.admin("ps_writer"), await lane.admin("ps_clearer"), await lane.member("ps_reader")
    secret = _marker()

    written = await _write(lane, writer, [_item("api_key", "system", secret_value=secret), _item("region", "system", value="us"), _item("price_tolerance", "system", value=1.25), _item("verbose", "system", value=True)])
    as_member = await _fields(lane, member)
    echo = await _echo(lane, member)
    rows_written = await _mockprov_system_rows()

    assert written.status_code == 200 and written.json()["success_count"] == 4, written.text
    assert (as_member["api_key"]["is_set"], as_member["api_key"]["value"], as_member["api_key"]["source"], as_member["api_key"]["editable"]) == (True, None, "db", False)
    assert {key: as_member[key]["value"] for key in ("region", "price_tolerance", "verbose")} == {"region": "us", "price_tolerance": 1.25, "verbose": True}
    assert {key: echo[key] for key in SYSTEM_KEYS} == {"api_key": "set", "region": "us", "price_tolerance": "1.25", "verbose": "True"}
    assert {row["field_key"]: row["updated_by_user_id"] for row in rows_written if row["field_key"] in SYSTEM_KEYS} == dict.fromkeys(SYSTEM_KEYS, writer.user_id)
    secret_row = next(row for row in rows_written if row["field_key"] == "api_key")
    assert secret_row["value_json"] is None and secret_row["key_id"] and secret.encode() not in secret_row["secret_ciphertext"]

    gone = await lane.call("DELETE", "/auth/users/me", account=writer)
    rows_without_author = await _mockprov_system_rows()
    cleared = await _write(lane, clearer, [_item(key, "system", clear=True) for key in SYSTEM_KEYS])
    after_clear = await _fields(lane, member)
    echo_after = await _echo(lane, member)

    assert gone.status_code == 200, gone.text
    assert {row["field_key"]: row["updated_by_user_id"] for row in rows_without_author if row["field_key"] in SYSTEM_KEYS} == dict.fromkeys(SYSTEM_KEYS), "ON DELETE SET NULL: the rows stay, without their author"
    assert cleared.status_code == 200 and cleared.json()["success_count"] == 4, cleared.text
    assert [row for row in await _mockprov_system_rows() if row["field_key"] in SYSTEM_KEYS] == [], "cleared: no row left for a system field"
    assert {key: (after_clear[key]["value"], after_clear[key]["is_set"]) for key in SYSTEM_KEYS} == {"api_key": (None, False), "region": ("eu", False), "price_tolerance": (0.5, False), "verbose": (False, False)}
    assert {key: echo_after[key] for key in SYSTEM_KEYS} == {"api_key": "unset", "region": "eu", "price_tolerance": "0.5", "verbose": "False"}
    assert lane.shows(secret) == [], "the secret came back in a response"
    print_success("written, read-only for a member, delivered, unlinked from its deleted author, cleared")

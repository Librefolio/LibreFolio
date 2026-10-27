"""The parse hook of the BRIM settings (W-BS): what the parent resolves, what the child binds, and what never leaks.

Modules under test: ``services/brim/brim_parse_pool.py`` (``parse_file_offloaded``), ``services/brim/brim_provider.py``
(``parse_file``), ``services/plugin_settings/runtime.py`` (``bound_settings_for``) and the parse endpoint of
``api/v1/brokers.py``. The contract pinned here:

1. **A plugin that declares no field is parsed exactly as before** (every real BRIM plugin): ``parse_file`` is called with
   the same three positional arguments and no keyword, whether or not the caller says which user it is parsing for, and
   nothing is read from the database (the engine of these tests raises when it is reached). The existing pool and race
   suites stay as they are.
2. **A plugin that declares fields** gets its values: in the PARENT, ``parse_file_offloaded(..., user_id=…)`` resolves
   them (the instance's, and the user's when ``user_id`` is given) and hands the picklable ``BoundSettings`` to the child
   as ``settings``; the three positional arguments stay as they were. ``parse_file(..., settings=…)`` binds them on the
   plugin instance before it parses, and holds their secrets «in flight» for the length of the parse (so that its log
   lines are masked); without ``settings`` the plugin sees the unbound defaults and no secret.
3. **A secret never leaves the parent**: an error of the parse that shows a bound secret — in its message, its details, its
   URL-encoded form — reaches the caller masked (``***``), its type kept; with a secret of the user's own bound, no text of
   it shows a secret; the log lines written while the parse runs show none either.
4. **The parse endpoint** passes ``user_id=current_user.id``.
5. ``BoundSettings`` crosses a process boundary: it pickles with its values, its secrets and its fingerprint, and its
   ``repr`` still shows no secret.

The pool path itself cannot be used with the lab plugin (the worker re-creates a plugin by its code in its own registry,
where the lab plugin is not): the tests use the thread fallback, which runs the same parent code and the same call; the
real pool, with a plugin that declares nothing, is covered by ``test_brim_parse_pool.py``.

Pure: the settings rows live in a private SQLite file under ``tmp_path`` reached through a private engine put in place of
``runtime.get_async_engine``; the instance key is a test key; the uploaded files live under ``tmp_path``; the lab BRIM
plugin (``_brim_settings_lab``) is registered for the length of a test and taken out again.
"""

from __future__ import annotations

import pickle
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import brokers as brokers_api
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import BRIMParseOutput, BRIMParseRequest
from backend.app.services.brim import brim_parse_pool, brim_provider
from backend.app.services.brim.brim_provider import BRIMParseError
from backend.app.services.plugin_settings import resolver, runtime
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import env_name, env_variables
from backend.app.utils.runtime.secret_masking import MASK, active_secrets, mask_event_dict
from backend.test_scripts.test_services import _brim_settings_lab as brim_lab
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-brim-parse-settings-test-key-0123456789"
BRIM_CODE = brim_lab.CODE
#: A real plugin that declares no field (broker_generic_csv declares ``date_order`` since W5-8).
REAL_PLUGIN = "broker_schwab"
BROKER_ID = 5
logger = get_logger(__name__)


def _marker(prefix: str = "lfsecret") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test mode (the lab plugin is ``test_only``), a test instance key, a data directory of this test, no ambient
    variable of the lab plugin's fields, the once-per-process logs of the resolver empty."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    for declared in brim_lab.SETTINGS_FIELDS:
        for name in {*env_variables("brim", BRIM_CODE, declared), env_name("brim", BRIM_CODE, declared.key)}:
            monkeypatch.delenv(name, raising=False)
            monkeypatch.delenv(name + "_FILE", raising=False)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])


@pytest.fixture
def uploaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A file uploaded under ``tmp_path`` (the reports directory is redirected): its id."""
    reports = tmp_path / "broker_reports"
    reports.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    return brim_provider.save_uploaded_file(b"date,amount\n2026-01-01,10\n", "generic_simple.csv", user_id=1, broker_id=BROKER_ID).file_id


@pytest.fixture
def thread_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pool is given up: ``parse_file_offloaded`` parses in a thread of this process, as it does when no worker can start."""
    monkeypatch.setattr(brim_parse_pool, "_pool_disabled", True)


@pytest.fixture
def lab_plugin(monkeypatch: pytest.MonkeyPatch):
    """The lab BRIM plugin registered in the real registry, its record and hook empty; out again at teardown."""
    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "seen", [])
    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "on_parse", None)
    with brim_lab.registered_settings_brim() as plugin_class:
        yield plugin_class


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
    raise AssertionError("the database was reached: a plugin that declares no field has nothing to read")


@pytest_asyncio.fixture
async def rows(private_engine: AsyncEngine) -> dict[str, Any]:
    """Two users, the lab plugin's instance rows and alice's own, and bob's language: what a parse resolves."""
    secrets = {"api_key": _marker(), "alice_token": _marker()}
    async with AsyncSession(private_engine, expire_on_commit=False) as session:
        alice = User(username="alice", email="alice@example.test", hashed_password="$argon2id$test")
        bob = User(username="bob", email="bob@example.test", hashed_password="$argon2id$test")
        session.add_all([alice, bob])
        await session.commit()
        subkey = settings_subkey()

        def blob(key: str, scope: str, user_id: int | None, plaintext: str) -> dict[str, Any]:
            return {"secret_ciphertext": encrypt_secret(subkey, secret_aad("brim", BRIM_CODE, key, scope, user_id), plaintext), "key_id": key_id_of(subkey)}

        session.add_all(
            [
                PluginSystemSetting(family="brim", plugin_code=BRIM_CODE, field_key="region", value_json='"us"'),
                PluginSystemSetting(family="brim", plugin_code=BRIM_CODE, field_key="api_key", **blob("api_key", "system", None, secrets["api_key"])),
                PluginUserSetting(user_id=alice.id, family="brim", plugin_code=BRIM_CODE, field_key="statement_language", value_json='"it"'),
                PluginUserSetting(user_id=alice.id, family="brim", plugin_code=BRIM_CODE, field_key="personal_token", **blob("personal_token", "user", alice.id, secrets["alice_token"])),
                PluginUserSetting(user_id=bob.id, family="brim", plugin_code=BRIM_CODE, field_key="statement_language", value_json='"en"'),
            ]
        )
        await session.commit()
    return {"alice": alice.id, "bob": bob.id, **secrets}


class _Spy:
    """A stand-in for ``brim_provider.parse_file``: records each call as ``(args, kwargs)`` and answers an empty parse."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> BRIMParseOutput:
        self.calls.append((args, kwargs))
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})

    def settings_of(self, index: int = -1) -> BoundSettings | None:
        """The ``BoundSettings`` the call carried, as a keyword or as a fourth positional argument; None for none."""
        args, kwargs = self.calls[index]
        return kwargs.get("settings", args[3] if len(args) > 3 else None)


# =============================================================================
# 1. A PLUGIN WITHOUT FIELDS: EXACTLY AS BEFORE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [pytest.param({}, id="no-user-id-the-legacy-call"), pytest.param({"user_id": None}, id="user-id-none"), pytest.param({"user_id": 7}, id="a-user-id")])
async def test_a_plugin_without_fields_is_parsed_exactly_as_before(extra: dict, thread_only: None, monkeypatch: pytest.MonkeyPatch):
    """1: ``parse_file`` gets the same three positional arguments and no keyword, with or without a user, and the database
    is never reached. Red today for the calls that name a user: ``parse_file_offloaded`` has no ``user_id``."""
    print_section(f"1: no field, {extra or 'the legacy call'}")
    spy = _Spy()
    monkeypatch.setattr(brim_provider, "parse_file", spy)
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)

    output = await brim_parse_pool.parse_file_offloaded("a-file-id", REAL_PLUGIN, BROKER_ID, **extra)

    assert isinstance(output, BRIMParseOutput)
    assert spy.calls == [(("a-file-id", REAL_PLUGIN, BROKER_ID), {})], "no settings, no keyword: the call is what it was"
    print_success("parse_file called with the same positional arguments, nothing else, no database read")


@pytest.mark.asyncio
async def test_an_unknown_plugin_is_still_the_childs_error_whoever_the_user_is(uploaded: str, thread_only: None):
    """1: the parent finds no class for the code and declares nothing: the child answers «Plugin not found» as before."""
    with pytest.raises(ValueError, match="Plugin not found"):
        await brim_parse_pool.parse_file_offloaded(uploaded, "broker_nonexistent_plugin", BROKER_ID, user_id=1)


# =============================================================================
# 2. A PLUGIN WITH FIELDS: THE PARENT RESOLVES, THE CHILD BINDS
# =============================================================================


@pytest.mark.asyncio
async def test_a_plugin_with_fields_gets_its_settings_handed_to_parse_file(lab_plugin: type, rows: dict[str, Any], through_private_engine: list[int], thread_only: None, monkeypatch: pytest.MonkeyPatch):
    """2: the parent resolves the instance's values and the user's, and hands them to ``parse_file`` as ``settings``; the
    three positional arguments stay. Alice's call carries her language and token, bob's his language, a call for nobody the
    defaults; the instance's region and secret reach all three."""
    print_section("2: the parent resolves, parse_file receives")
    spy = _Spy()
    monkeypatch.setattr(brim_provider, "parse_file", spy)

    for user_id in (rows["alice"], rows["bob"], None):
        await brim_parse_pool.parse_file_offloaded("a-file-id", BRIM_CODE, BROKER_ID, user_id=user_id)

    assert [args[:3] for args, _kwargs in spy.calls] == [("a-file-id", BRIM_CODE, BROKER_ID)] * 3, "the positional arguments are what they were"
    alices, bobs, nobodys = (spy.settings_of(index) for index in range(3))
    assert all(isinstance(bound, BoundSettings) for bound in (alices, bobs, nobodys)), "a plugin that declares fields gets its BoundSettings"
    for bound in (alices, bobs, nobodys):
        assert (bound.get("region"), bound.secret("api_key"), bound.missing) == ("us", rows["api_key"], ())
    assert (alices.get("statement_language"), alices.secret("personal_token")) == ("it", rows["alice_token"])
    assert (bobs.get("statement_language"), bobs.secret("personal_token")) == ("en", None)
    assert (nobodys.get("statement_language"), nobodys.secret("personal_token")) == ("all", None)
    assert (alices.carries_user_secrets, bobs.carries_user_secrets, nobodys.carries_user_secrets) == (True, False, False)
    assert len(through_private_engine) >= 3, "the rows were read from the database, in the parent"
    print_success("alice, bob and nobody each get their settings")


@pytest.mark.asyncio
async def test_parse_file_binds_the_settings_it_is_given_before_the_plugin_parses(lab_plugin: type, uploaded: str):
    """2: in the child: ``parse_file(..., settings=bound)`` binds ``bound`` on the plugin instance, which reads it in
    ``parse``; without ``settings`` the plugin sees the unbound defaults and no secret."""
    secret = _marker()
    bound = BoundSettings(brim_lab.SETTINGS_FIELDS, {"region": "us", "statement_language": "it"}, {"api_key": secret}, fingerprint="fp")

    brim_provider.parse_file(uploaded, BRIM_CODE, BROKER_ID, settings=bound)
    brim_provider.parse_file(uploaded, BRIM_CODE, BROKER_ID)

    given, unbound = brim_lab.SettingsBrimPlugin.seen
    assert given is bound, "the plugin reads the very BoundSettings the child was given"
    assert (unbound.get("region"), unbound.get("statement_language"), unbound.secret("api_key"), unbound.fingerprint) == ("eu", "all", None, "")


@pytest.mark.asyncio
async def test_parse_file_holds_the_secrets_in_flight_for_the_length_of_the_parse(lab_plugin: type, uploaded: str, monkeypatch: pytest.MonkeyPatch):
    """2: the child's own log lines are masked: while the plugin parses, the bound secrets are in flight, and only then;
    without ``settings`` nothing is in flight."""
    secret, token = _marker(), _marker()
    bound = BoundSettings(brim_lab.SETTINGS_FIELDS, {}, {"api_key": secret, "personal_token": token})
    in_flight: list[frozenset[str]] = []
    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "on_parse", lambda _bound: in_flight.append(active_secrets()))

    brim_provider.parse_file(uploaded, BRIM_CODE, BROKER_ID, settings=bound)
    assert active_secrets() == frozenset(), "the secrets are in flight for the parse only"
    brim_provider.parse_file(uploaded, BRIM_CODE, BROKER_ID)

    assert in_flight == [frozenset({secret, token}), frozenset()]


# =============================================================================
# 3. A SECRET NEVER LEAVES THE PARENT
# =============================================================================


def _raise_a_value_error(bound: BoundSettings) -> None:
    secrets = sorted(bound.secret_values())
    raise ValueError("upstream refused the credentials " + " and ".join(secrets) + " (" + quote(secrets[0], safe="") + ")")


def _raise_a_parse_error(bound: BoundSettings) -> None:
    secrets = sorted(bound.secret_values())
    raise BRIMParseError(f"cannot read the report with {secrets[0]}", {"credentials": secrets, "url": f"https://broker.example/report?key={quote(secrets[0], safe='')}"})


@pytest.mark.asyncio
@pytest.mark.parametrize("raiser", [pytest.param(_raise_a_value_error, id="a-value-error"), pytest.param(_raise_a_parse_error, id="a-parse-error-with-details")])
@pytest.mark.parametrize("who", ["nobody", "alice"])
async def test_a_parse_error_that_shows_a_bound_secret_is_masked_before_it_leaves(raiser, who: str, lab_plugin: type, rows: dict[str, Any], uploaded: str, through_private_engine: list[int], thread_only: None, monkeypatch: pytest.MonkeyPatch):
    """3: the error the caller gets shows no secret — not in its text, its arguments, its details, its URL-encoded form —,
    keeps its type, and shows the mask. With alice's own token bound too, no text of it shows a secret."""
    print_section(f"3: a failing parse for {who}")
    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "on_parse", raiser)
    user_id = rows["alice"] if who == "alice" else None
    secrets = {rows["api_key"], rows["alice_token"]} if who == "alice" else {rows["api_key"]}
    expected = BRIMParseError if raiser is _raise_a_parse_error else ValueError

    with pytest.raises(expected) as raised:
        await brim_parse_pool.parse_file_offloaded(uploaded, BRIM_CODE, BROKER_ID, user_id=user_id)

    error = raised.value
    shown = " ".join([str(error), repr(error), repr(error.args), repr(getattr(error, "details", None)), repr(vars(error))])
    assert not any(secret in shown or quote(secret, safe="") in shown for secret in secrets), f"a secret reached the caller: {shown}"
    assert MASK in str(error), "the error says that something was masked"
    print_success("masked, type kept")


@pytest.mark.asyncio
async def test_the_log_of_a_parse_never_shows_a_bound_secret(lab_plugin: type, rows: dict[str, Any], uploaded: str, through_private_engine: list[int], thread_only: None, monkeypatch: pytest.MonkeyPatch):
    """3: a line the plugin logs while it parses, with a secret in it, is masked by the logging pipeline (``mask_event_dict``
    in the logger's processors, as in production): the secrets are in flight while the parse runs, in the parent as in the child."""

    def log_the_credentials(bound: BoundSettings) -> None:
        logger.info("calling the upstream", token=bound.secret("personal_token"), key=bound.secret("api_key"))

    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "on_parse", log_the_credentials)

    with capture_logs(processors=[mask_event_dict]) as logs:
        await brim_parse_pool.parse_file_offloaded(uploaded, BRIM_CODE, BROKER_ID, user_id=rows["alice"])

    calls = [entry for entry in logs if entry["event"] == "calling the upstream"]
    assert len(calls) == 1, "barrier: the plugin's line was captured"
    assert (calls[0]["token"], calls[0]["key"]) == (MASK, MASK)
    assert rows["api_key"] not in repr(logs) and rows["alice_token"] not in repr(logs)


@pytest.mark.asyncio
async def test_the_log_of_a_failing_parse_never_shows_a_bound_secret(lab_plugin: type, rows: dict[str, Any], uploaded: str, through_private_engine: list[int], thread_only: None, monkeypatch: pytest.MonkeyPatch):
    """3: whatever the parent and the child log about the failure shows no secret."""
    monkeypatch.setattr(brim_lab.SettingsBrimPlugin, "on_parse", _raise_a_value_error)

    with capture_logs(processors=[mask_event_dict]) as logs, pytest.raises(ValueError):
        await brim_parse_pool.parse_file_offloaded(uploaded, BRIM_CODE, BROKER_ID, user_id=rows["alice"])

    shown = repr(logs)
    assert not any(secret in shown or quote(secret, safe="") in shown for secret in (rows["api_key"], rows["alice_token"]))


# =============================================================================
# 4. THE ENDPOINT
# =============================================================================


class _Stop(BaseException):
    """Ends the endpoint right after the parse call: a ``BaseException``, so that no ``except Exception`` of the handler takes it."""


@pytest.mark.asyncio
async def test_the_parse_endpoint_passes_the_calling_user_to_the_offloaded_parse(monkeypatch: pytest.MonkeyPatch):
    """4: ``POST /brim/files/{file_id}/parse`` hands ``user_id=current_user.id`` and the ``bound`` values it resolved (None for a
    plugin without fields) to ``parse_file_offloaded``, after the three arguments it always passed. The access checks and the report-set guard are put aside: they are not the subject."""
    seen: dict[str, Any] = {}

    async def access(*_args: Any, **_kwargs: Any) -> object:
        return object()

    async def editor(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def offloaded(*args: Any, **kwargs: Any) -> BRIMParseOutput:
        seen["args"], seen["kwargs"] = args, kwargs
        raise _Stop

    monkeypatch.setattr(brokers_api, "_get_brim_file_with_access", access)
    monkeypatch.setattr(brokers_api, "_require_broker_editor", editor)
    monkeypatch.setattr(brokers_api, "_refuse_report_set_member", lambda _code, _info: None)
    monkeypatch.setattr(brokers_api, "parse_file_offloaded", offloaded)

    with pytest.raises(_Stop):
        await brokers_api.parse_file("a-file-id", BRIMParseRequest(plugin_code=REAL_PLUGIN, broker_id=BROKER_ID), SimpleNamespace(id=4242), None)

    assert seen["args"] == ("a-file-id", REAL_PLUGIN, BROKER_ID)
    assert seen["kwargs"] == {"user_id": 4242, "bound": None}, "the route resolves the values once and hands them over; a plugin without fields has none"


# =============================================================================
# 5. ACROSS THE PROCESS BOUNDARY
# =============================================================================


def test_bound_settings_survive_the_pickle_to_the_child():
    """5, guard: the child receives what the parent resolved: values, secrets, missing fields and fingerprint intact,
    ``carries_user_secrets`` the same, and the ``repr`` of the copy still names the secrets without showing them."""
    secret, token = _marker("SECRET"), _marker("TOKEN")
    bound = BoundSettings(brim_lab.SETTINGS_FIELDS, {"region": "us", "statement_language": "it"}, {"api_key": secret, "personal_token": token}, ("api_key",), fingerprint="f" * 32)

    copy = pickle.loads(pickle.dumps(bound))

    assert (copy.plain_values(), copy.secret_values(), copy.missing, copy.fingerprint, copy.carries_user_secrets) == (bound.plain_values(), bound.secret_values(), bound.missing, bound.fingerprint, True)
    assert (copy.get("region"), copy.secret("api_key"), copy.secret("personal_token")) == ("us", secret, token)
    assert secret not in repr(copy) and token not in repr(copy) and "api_key" in repr(copy)
    unbound = pickle.loads(pickle.dumps(BoundSettings.unbound(brim_lab.SETTINGS_FIELDS)))
    assert (unbound.get("region"), unbound.secret("api_key"), unbound.fingerprint) == ("eu", None, "")

"""
The legal links in the public configuration of the instance (workstream A, lot A9: F09): ``GET /api/v1/system/instance``.

Under test: the route ``get_instance_config`` (``backend/app/api/v1/system/instance.py``), the schema
``LegalInstanceConfig`` and the field ``legal`` of ``InstanceConfigResponse`` (``backend/app/schemas/system.py``), and
the OpenAPI document of the application. The readers and the links behind the block (``tos_url()``, ``privacy_url()``,
``terms_link()``, ``privacy_link()``) are in ``test_services/test_legal_links.py``. The contract:

1. Anyone, without a session, gets a block ``legal`` beside the fields of before: exactly ``{terms_url, privacy_url}``,
   each the value of ``LIBREFOLIO_TOS_URL`` / ``LIBREFOLIO_PRIVACY_URL`` as ``env_url()`` gives it (stripped, one
   trailing slash removed) when it is a valid http(s) address, ``null`` when it is unset or blank. Self-hosted and
   managed alike.
2. An invalid address (another scheme, ``mailto:`` included, or none) is ``null``, beside the other link when that one is
   valid, and the answer is still 200: an invalid address never breaks what the app reads at startup. An address with
   user info is ``null``, and the answer holds neither its user name nor its password.
3. Unchanged: the other fields. The answer is exactly ``profile``, ``accounts``, ``email``, ``support_url``, ``legal``
   and (H-60) ``client_log_level``; the profile is still the one ``LIBREFOLIO_PROFILE`` sets; ``support_url`` is still
   the support address alone, never a legal one, and no legal link is ever the support address.
4. ``LegalInstanceConfig``, in ``backend/app/schemas/system.py``: exactly ``terms_url`` and ``privacy_url``, each a
   string or ``null``. ``InstanceConfigResponse.legal`` is typed with it and defaults to both ``null``: an answer built
   without it says that no legal link is set.
5. The OpenAPI document of the application (``backend.app.main.app.openapi()``, what ``./dev.py api sync`` exports to
   the frontend) declares it: the 200 of ``GET /api/v1/system/instance`` is ``InstanceConfigResponse``, whose properties
   are the fields of before, ``legal`` and ``client_log_level``; ``legal`` refers to ``LegalInstanceConfig`` and is not
   required (it has a default, as ``email`` has); ``LegalInstanceConfig``'s properties are exactly ``terms_url`` and
   ``privacy_url``, each a string or null.
6. Live, on the lane's backend: the lane sets neither variable (the runner drops every ``LIBREFOLIO_*`` setting), so an
   anonymous request reads ``legal`` with both ``null``.

How: cases 1 to 3 run in-process on a private instance: the system router mounted as ``api/v1/router.py`` mounts it,
every session on a SQLite file under ``tmp_path`` with the schema and the default settings of a new install, the
engine disposed at teardown, so the lane's database is never read. The variables are set with ``monkeypatch``, with
``LIBREFOLIO_TEST_MODE=1`` (``get_settings()`` reads no ``.env``) and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path``;
the once-per-process log of an invalid instance link (``_report_invalid``) and the settings, should they ever be cached,
are emptied before and after each case. Cases 4 and 5 start no server. Case 6 talks HTTP to the lane's shared backend
(``_TestingServerManager``). The user-info address is built from its parts. ``LegalInstanceConfig`` is looked up when a
test runs: until A9 each test fails on its own with «red until A9: …», never the collection. Texts and names that may
still change are constants at the top.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.api.v1.system as system_module
from backend.app import config
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.session import get_session_generator
from backend.app.schemas import system as system_schemas
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.platform import instance_links
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
#: The route, as the in-process app and the OpenAPI document of the application name it.
INSTANCE_PATH = f"{API_V1_PREFIX}/system/instance"
INSTANCE_URL = f"{API_BASE}/system/instance"

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
TOS_VARIABLE = "LIBREFOLIO_TOS_URL"
PRIVACY_VARIABLE = "LIBREFOLIO_PRIVACY_URL"
SUPPORT_VARIABLE = "LIBREFOLIO_SUPPORT_URL"
#: Variables of other owners the answer reads, unset on the private instance: a value exported in the shell must not turn
#: the answer into a 500 for a reason foreign to this file.
FOREIGN_VARIABLES = ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS")

LEGAL_SCHEMA = "LegalInstanceConfig"
LEGAL_FIELD = "legal"
LEGAL_KEYS = {"terms_url", "privacy_url"}
NO_LEGAL_LINK = {"terms_url": None, "privacy_url": None}
#: The public configuration after A9 and H-60: the fields of before, legal, and client_log_level.
# H-62 (contract L3 §6): ``mode``, normal or awaiting_restore. B-33 (22/10): ``restore_interrupted``; H5-3 (24/10): ``restore_interrupted_reason``
INSTANCE_KEYS = {"profile", "accounts", "email", "support_url", LEGAL_FIELD, "client_log_level", "mode", "restore_interrupted", "restore_interrupted_reason"}

TERMS_ADDRESS = "https://legal.example.org/terms"
PRIVACY_ADDRESS = "https://legal.example.org/privacy"
SUPPORT_ADDRESS = "https://help.example.org/support"
#: The user name and the password of the user-info cases; the address is built from them, never written whole.
USER_INFO_NAME = "alice-legal"
USER_INFO_PASSWORD = "t0s-s3cr3t-pw"
USER_INFO_ADDRESS = f"https://{USER_INFO_NAME}:{USER_INFO_PASSWORD}@legal.example.org/terms"

#: (1) Both profiles, as written and as read.
PROFILES = [pytest.param(None, "selfhosted", id="selfhosted"), pytest.param("managed", "managed", id="managed")]


# =============================================================================
# HELPERS
# =============================================================================


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the live case only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


def _legal_model() -> type[BaseModel]:
    """``LegalInstanceConfig``, looked up when the test runs."""
    model = getattr(system_schemas, LEGAL_SCHEMA, None)
    assert isinstance(model, type) and issubclass(model, BaseModel), f"red until A9: backend.app.schemas.system has no {LEGAL_SCHEMA} model (found {model!r})"
    return model


def _forget_cached_state() -> None:
    """The settings (built at each call today; emptied should they ever be cached) and the once-per-process log of an invalid instance link start over."""
    settings_cache_clear = getattr(config.get_settings, "cache_clear", None)
    if callable(settings_cache_clear):
        settings_cache_clear()
    report_cache_clear = getattr(getattr(instance_links, "_report_invalid", None), "cache_clear", None)
    if callable(report_cache_clear):
        report_cache_clear()


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _use_profile(monkeypatch: pytest.MonkeyPatch, written: str | None, expected: str) -> None:
    """``LIBREFOLIO_PROFILE`` as ``written`` (``None``: unset); barrier: ``get_settings()`` reads ``expected``."""
    _set_variable(monkeypatch, PROFILE_VARIABLE, written)
    _forget_cached_state()
    resolved = get_settings().LIBREFOLIO_PROFILE
    assert resolved == expected, f"barrier: with {PROFILE_VARIABLE}={written!r}, get_settings() reads the profile {resolved!r}, not {expected!r}"


@pytest_asyncio.fixture
async def private_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FastAPI]:
    """The system router mounted as ``api/v1/router.py`` mounts it, every session on a private SQLite file under ``tmp_path`` (schema and default settings of a new install); no profile, legal, support or foreign variable; disposed at teardown."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (PROFILE_VARIABLE, TOS_VARIABLE, PRIVACY_VARIABLE, SUPPORT_VARIABLE, *FOREIGN_VARIABLES):
        monkeypatch.delenv(name, raising=False)
    _forget_cached_state()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)

        async def private_session() -> AsyncIterator[AsyncSession]:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        app = FastAPI()
        app.include_router(system_module.router, prefix=API_V1_PREFIX)
        app.dependency_overrides[get_session_generator] = private_session
        yield app
    finally:
        await engine.dispose()
        _forget_cached_state()


async def _anonymous_get(app: FastAPI) -> httpx.Response:
    """``GET /system/instance`` on the private instance, anonymous: no cookie, no header."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.get(INSTANCE_PATH)


def _body_and_legal(response: httpx.Response) -> tuple[dict[str, Any], dict[str, Any]]:
    """The answer and its ``legal`` block, behind the barriers: 200, the block present, the fields of before, ``legal`` and ``client_log_level``, the block exactly its two keys."""
    assert response.status_code == 200, f"GET /system/instance is public and never breaks on a link: expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert LEGAL_FIELD in body, f"red until A9: GET /system/instance answers no {LEGAL_FIELD} block: {response.text}"
    assert set(body) == INSTANCE_KEYS, f"the public configuration must be exactly the fields of before, {LEGAL_FIELD} and client_log_level: missing {INSTANCE_KEYS - set(body)}, extra {set(body) - INSTANCE_KEYS}"
    legal = body[LEGAL_FIELD]
    assert isinstance(legal, dict) and set(legal) == LEGAL_KEYS, f"{LEGAL_FIELD} must be exactly {sorted(LEGAL_KEYS)}: {legal!r}"
    return body, legal


def _component(document: dict[str, Any], schema: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The name and the component a schema refers to: its own ``$ref``, or the one of its ``allOf``."""
    references = [schema.get("$ref"), *(option.get("$ref") for option in schema.get("allOf", []))]
    reference = next((ref for ref in references if ref), None)
    assert reference, f"the schema refers to no component: {schema}"
    name = reference.rsplit("/", 1)[-1]
    return name, document["components"]["schemas"][name]


def _json_types(schema: dict[str, Any]) -> set[str]:
    """The JSON types a property allows: its own ``type``, and those of its ``anyOf`` / ``oneOf`` members."""
    found: set[str] = set()
    for candidate in (schema, *schema.get("anyOf", []), *schema.get("oneOf", [])):
        kind = candidate.get("type")
        if isinstance(kind, str):
            found.add(kind)
        elif isinstance(kind, list):
            found.update(kind)
    return found


# =============================================================================
# 1-3. IN-PROCESS: THE BLOCK ANYONE READS, ON A PRIVATE INSTANCE
# =============================================================================


# red until A9: GET /system/instance answers no legal block
@pytest.mark.asyncio
@pytest.mark.parametrize(("written", "profile"), PROFILES)
async def test_without_legal_addresses_anyone_reads_both_links_null(private_app: FastAPI, monkeypatch: pytest.MonkeyPatch, written: str | None, profile: str) -> None:
    """ICL-001 (1, 3): neither variable set: ``legal`` is both ``null``, beside the profile of before and a ``null`` support address."""
    print_section(f"ICL-001: no legal address, {profile}")
    _use_profile(monkeypatch, written, profile)

    body, legal = _body_and_legal(await _anonymous_get(private_app))

    assert legal == NO_LEGAL_LINK, f"neither {TOS_VARIABLE} nor {PRIVACY_VARIABLE} set: {LEGAL_FIELD} must be {NO_LEGAL_LINK}, got {legal}"
    assert body["profile"] == profile and body["support_url"] is None, f"unchanged: the profile {profile!r} and no support address: {body}"
    print_success(f"{profile}: {LEGAL_FIELD} == {legal}")


# red until A9: GET /system/instance answers no legal block
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("terms", "privacy", "expected"),
    [
        pytest.param(" https://legal.example.org/terms/ ", " https://legal.example.org/privacy/ ", {"terms_url": TERMS_ADDRESS, "privacy_url": PRIVACY_ADDRESS}, id="both-stripped-without-their-trailing-slash"),
        pytest.param("HTTP://Legal.Example.ORG/Terms", None, {"terms_url": "HTTP://Legal.Example.ORG/Terms", "privacy_url": None}, id="terms-alone-the-case-kept"),
        pytest.param(None, "https://legal.example.org/doc?lang=it#privacy", {"terms_url": None, "privacy_url": "https://legal.example.org/doc?lang=it#privacy"}, id="privacy-alone-query-and-fragment-kept"),
    ],
)
@pytest.mark.parametrize(("written", "profile"), PROFILES)
async def test_a_valid_address_is_published_as_env_url_gives_it(private_app: FastAPI, monkeypatch: pytest.MonkeyPatch, written: str | None, profile: str, terms: str | None, privacy: str | None, expected: dict[str, str | None]) -> None:
    """ICL-002 (1): a valid http(s) address is published as ``env_url()`` gives it, the other link ``null`` when unset; self-hosted and managed alike."""
    print_section(f"ICL-002: {TOS_VARIABLE}={terms!r}, {PRIVACY_VARIABLE}={privacy!r}, {profile}")
    _use_profile(monkeypatch, written, profile)
    _set_variable(monkeypatch, TOS_VARIABLE, terms)
    _set_variable(monkeypatch, PRIVACY_VARIABLE, privacy)

    body, legal = _body_and_legal(await _anonymous_get(private_app))

    assert legal == expected, f"{TOS_VARIABLE}={terms!r}, {PRIVACY_VARIABLE}={privacy!r}: {LEGAL_FIELD} must be {expected}, got {legal}"
    assert body["profile"] == profile, f"unchanged: the profile {profile!r}: {body}"
    print_success(f"{profile}: {LEGAL_FIELD} == {legal}")


# red until A9: GET /system/instance answers no legal block
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("terms", "privacy", "expected"),
    [
        pytest.param("ftp://legal.example.org/terms", PRIVACY_ADDRESS, {"terms_url": None, "privacy_url": PRIVACY_ADDRESS}, id="terms-ftp-privacy-valid"),
        pytest.param(TERMS_ADDRESS, "mailto:privacy@example.org", {"terms_url": TERMS_ADDRESS, "privacy_url": None}, id="privacy-mailto-terms-valid"),
        pytest.param("legal.example.org/terms", "   ", {"terms_url": None, "privacy_url": None}, id="terms-without-a-scheme-privacy-blank"),
    ],
)
async def test_an_invalid_address_is_null_and_the_answer_still_200(private_app: FastAPI, monkeypatch: pytest.MonkeyPatch, terms: str, privacy: str, expected: dict[str, str | None]) -> None:
    """ICL-003 (2): an invalid address is ``null``, beside the other link when valid; the answer is still 200."""
    print_section(f"ICL-003: {TOS_VARIABLE}={terms!r}, {PRIVACY_VARIABLE}={privacy!r}")
    monkeypatch.setenv(TOS_VARIABLE, terms)
    monkeypatch.setenv(PRIVACY_VARIABLE, privacy)

    _, legal = _body_and_legal(await _anonymous_get(private_app))

    assert legal == expected, f"{TOS_VARIABLE}={terms!r}, {PRIVACY_VARIABLE}={privacy!r}: an invalid address is null, a valid one published: expected {expected}, got {legal}"
    print_success(f"{LEGAL_FIELD} == {legal}")


# red until A9: GET /system/instance answers no legal block
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("variable", "key", "other_variable", "other_address", "other_key"),
    [
        pytest.param(TOS_VARIABLE, "terms_url", PRIVACY_VARIABLE, PRIVACY_ADDRESS, "privacy_url", id="terms-with-user-info"),
        pytest.param(PRIVACY_VARIABLE, "privacy_url", TOS_VARIABLE, TERMS_ADDRESS, "terms_url", id="privacy-with-user-info"),
    ],
)
async def test_an_address_with_user_info_is_null_and_never_in_the_answer(private_app: FastAPI, monkeypatch: pytest.MonkeyPatch, variable: str, key: str, other_variable: str, other_address: str, other_key: str) -> None:
    """ICL-004 (2): an address with user info is ``null``, the other link still published, and the raw answer holds neither the user name nor the password."""
    print_section(f"ICL-004: {variable} with user info")
    monkeypatch.setenv(variable, USER_INFO_ADDRESS)
    monkeypatch.setenv(other_variable, other_address)

    response = await _anonymous_get(private_app)
    _, legal = _body_and_legal(response)

    assert legal[key] is None and legal[other_key] == other_address, f"{variable} with user info must be null, {other_variable} published as {other_address!r}: {legal}"
    leaked = [part for part in (USER_INFO_NAME, USER_INFO_PASSWORD) if part.casefold() in response.text.casefold()]
    assert leaked == [], f"the public configuration must hold neither the user name nor the password of {variable}, found {leaked}: {response.text}"
    print_success(f"{variable} with user info: {key} null, nothing leaked")


# red until A9: GET /system/instance answers no legal block
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("terms", "privacy", "expected"),
    [
        pytest.param(None, None, NO_LEGAL_LINK, id="support-address-alone"),
        pytest.param(TERMS_ADDRESS, PRIVACY_ADDRESS, {"terms_url": TERMS_ADDRESS, "privacy_url": PRIVACY_ADDRESS}, id="support-and-both-legal-addresses"),
    ],
)
async def test_the_support_address_and_the_legal_addresses_stay_apart(private_app: FastAPI, monkeypatch: pytest.MonkeyPatch, terms: str | None, privacy: str | None, expected: dict[str, str | None]) -> None:
    """ICL-005 (3): ``support_url`` is the support address alone and ``legal`` the legal addresses alone: no legal link is ever the support address, nor the reverse."""
    print_section(f"ICL-005: support set, {TOS_VARIABLE}={terms!r}, {PRIVACY_VARIABLE}={privacy!r}")
    monkeypatch.setenv(SUPPORT_VARIABLE, SUPPORT_ADDRESS)
    _set_variable(monkeypatch, TOS_VARIABLE, terms)
    _set_variable(monkeypatch, PRIVACY_VARIABLE, privacy)

    body, legal = _body_and_legal(await _anonymous_get(private_app))

    assert body["support_url"] == SUPPORT_ADDRESS, f"unchanged: support_url is {SUPPORT_VARIABLE}, {SUPPORT_ADDRESS!r}, got {body['support_url']!r}"
    assert legal == expected, f"{LEGAL_FIELD} carries the legal addresses alone, never the support one: expected {expected}, got {legal}"
    print_success(f"support_url {body['support_url']!r}, {LEGAL_FIELD} {legal}")


# =============================================================================
# 4. THE SCHEMA: LegalInstanceConfig, AND legal OF InstanceConfigResponse
# =============================================================================


# red until A9: backend/app/schemas/system.py has no LegalInstanceConfig
def test_legal_instance_config_is_the_two_addresses() -> None:
    """ICL-006 (4): ``LegalInstanceConfig`` is exactly ``terms_url`` and ``privacy_url``, each a string or ``null``."""
    print_section(f"ICL-006: {LEGAL_SCHEMA}")
    model = _legal_model()

    filled = model(terms_url=TERMS_ADDRESS, privacy_url=None).model_dump(mode="json")
    empty = model(terms_url=None, privacy_url=None).model_dump(mode="json")

    assert set(model.model_fields) == LEGAL_KEYS, f"{LEGAL_SCHEMA} must be exactly {sorted(LEGAL_KEYS)}: {sorted(model.model_fields)}"
    assert filled == {"terms_url": TERMS_ADDRESS, "privacy_url": None}, f"{LEGAL_SCHEMA} must carry an address and a null as given: {filled}"
    assert empty == NO_LEGAL_LINK, f"{LEGAL_SCHEMA} must carry two nulls as given: {empty}"
    print_success(f"{LEGAL_SCHEMA}: {sorted(model.model_fields)}")


# red until A9: backend/app/schemas/system.py has no LegalInstanceConfig
def test_an_answer_built_without_legal_says_no_legal_link_is_set() -> None:
    """ICL-007 (4): ``InstanceConfigResponse.legal`` is typed with ``LegalInstanceConfig``, and an answer built without it serializes both links ``null``."""
    print_section(f"ICL-007: {LEGAL_FIELD} defaults to both null")
    model = _legal_model()
    field = system_schemas.InstanceConfigResponse.model_fields.get(LEGAL_FIELD)
    assert field is not None, f"red until A9: InstanceConfigResponse has no field {LEGAL_FIELD}"

    answer = system_schemas.InstanceConfigResponse(profile="selfhosted", accounts=AccountsInstanceConfig(registration_mode="open", registration_locked=False)).model_dump(mode="json")

    assert field.annotation is model, f"InstanceConfigResponse.{LEGAL_FIELD} must be typed with {LEGAL_SCHEMA}, is {field.annotation!r}"
    assert answer.get(LEGAL_FIELD) == NO_LEGAL_LINK, f"an answer built without {LEGAL_FIELD} must say no legal link is set, {NO_LEGAL_LINK}: {answer}"
    print_success(f"InstanceConfigResponse without {LEGAL_FIELD}: {answer.get(LEGAL_FIELD)}")


# =============================================================================
# 5. THE OPENAPI DOCUMENT OF THE APPLICATION
# =============================================================================


# red until A9: backend/app/schemas/system.py has no LegalInstanceConfig
def test_the_openapi_document_of_the_application_declares_legal() -> None:
    """ICL-008 (5): in ``app.openapi()`` the 200 of ``GET /system/instance`` declares the fields of before, ``client_log_level`` and ``legal``, not required, referring to ``LegalInstanceConfig``, exactly ``terms_url`` and ``privacy_url``, each a string or null."""
    print_section(f"ICL-008: {LEGAL_FIELD} in the OpenAPI document of the application")
    _legal_model()
    from backend.app.main import app  # noqa: PLC0415 — only this test pays for importing the application, and after the lookup above

    document = app.openapi()

    response_schema = document["paths"][INSTANCE_PATH]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    _, instance_schema = _component(document, response_schema)
    assert set(instance_schema["properties"]) == INSTANCE_KEYS, f"the 200 of GET /system/instance must declare exactly the fields of before, {LEGAL_FIELD} and client_log_level: {sorted(instance_schema['properties'])}"
    assert LEGAL_FIELD not in instance_schema.get("required", []), f"{LEGAL_FIELD} has a default, both null: it must not be required, as email is not; required: {instance_schema.get('required')}"
    legal_name, legal_schema = _component(document, instance_schema["properties"][LEGAL_FIELD])
    assert legal_name.split("-")[0] == LEGAL_SCHEMA, f"{LEGAL_FIELD} must refer to {LEGAL_SCHEMA}, refers to {legal_name}"
    assert set(legal_schema.get("properties", {})) == LEGAL_KEYS, f"{LEGAL_SCHEMA} must declare exactly {sorted(LEGAL_KEYS)}: {legal_schema}"
    wrong = {key: sorted(_json_types(legal_schema["properties"][key])) for key in LEGAL_KEYS if _json_types(legal_schema["properties"][key]) != {"string", "null"}}
    assert wrong == {}, f"each legal link is a string or null in the OpenAPI document: {wrong}"
    print_success(f"{LEGAL_FIELD} -> {legal_name}: {sorted(legal_schema['properties'])}")


# =============================================================================
# 6. LIVE: THE LANE'S BACKEND
# =============================================================================


class TestLegalBlockLive:
    """``GET /system/instance`` on the lane's backend: anyone reads the block, both links null on a lane that sets neither."""

    @pytest.fixture(autouse=True)
    def lane_sets_no_legal_address(self):
        """Precondition: no legal address. The runner drops every LIBREFOLIO_* setting from a lane, and the server reads the same environment as this process."""
        configured = {name: os.environ.get(name) for name in (TOS_VARIABLE, PRIVACY_VARIABLE)}
        assert not any((value or "").strip() for value in configured.values()), f"Precondition: this test reads a lane without legal addresses; this lane runs {configured} (the runner drops every LIBREFOLIO_* setting from a lane: was this run started outside ./dev.py test?)"

    # red until A9: GET /system/instance answers no legal block
    @pytest.mark.asyncio
    async def test_anyone_reads_both_legal_links_null_on_the_lane(self, test_server) -> None:
        """ICL-009 (6): anonymous, on the lane's backend: 200 and ``legal`` both ``null``."""
        print_section("ICL-009: the lane's backend, anonymous")
        async with httpx.AsyncClient() as client:
            response = await client.get(INSTANCE_URL, timeout=TIMEOUT)

        _, legal = _body_and_legal(response)

        assert legal == NO_LEGAL_LINK, f"the lane sets neither {TOS_VARIABLE} nor {PRIVACY_VARIABLE}: {LEGAL_FIELD} must be {NO_LEGAL_LINK}, got {legal}"
        print_success(f"the lane: {LEGAL_FIELD} == {legal}")

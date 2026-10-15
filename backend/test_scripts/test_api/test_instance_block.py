"""
The instance block (workstream H, platform, checkpoint CP6, decision D4).

Under test: ``backend/app/api/v1/instance_block.py`` (``refuse_when_blocked``, a dependency of the ``/api/v1`` router,
and ``ALLOWED_WHEN_BLOCKED``) and the block page ``GET /api/v1/system/block`` (``api/v1/system/block.py``,
``InstanceBlockResponse``). The contract:

(a) Blocked (``LIBREFOLIO_BLOCKED``). An anonymous caller of a protected refused route gets the 401 of
    ``get_current_user``, the same status and body as on an instance that is not blocked. A public route outside the
    allow-list (registration, the ``utilities`` lists, the global settings, the AI Export catalogue) answers that 401
    only while blocked, and its usual answer otherwise: the known limit stated in ``instance_block.py``, documented as it
    is by one test. A refused registration creates no account. A signed-in caller gets ``423`` with exactly
    ``{"detail": {"code": "instance_blocked", "message": ...}}``, before the body is validated: an invalid body gets
    423, not 422. The allowed routes answer as usual: ``/auth/me``, ``/system/block`` (blocked, with the deletion date),
    ``/system/info`` in full, health, the test runner's probe, readiness and the public configuration; signing in and
    out works, and so does deleting one's own account.
(b) Not blocked (unset, blank, or a value that does not block): the routes answer as before, and ``/system/block`` is
    ``{"blocked": false, "deletion_date": null}`` with a session and 401 without, on the lane's backend too.
(c) The guard. FastAPI gives router dependencies to an ``APIRoute`` (and its subclasses) only, never to a plain
    ``Route``, a ``WebSocketRoute`` or a ``Mount``. So every route or mount of the app under ``/api/v1`` must be an
    ``APIRoute`` resolving ``refuse_when_blocked`` first, before the route's own dependencies, so that a signed-in
    caller of a refused route meets the block before any other answer. The one exception, pinned, is FastAPI's own
    documentation (``openapi_url``, ``docs_url``, ``redoc_url`` of ``main.py``): three plain routes, which the block does
    not reach. Every function of ``ALLOWED_WHEN_BLOCKED`` is the endpoint of a registered route, and the list is pinned
    by name and by route, so an addition shows in review.
(d) OpenAPI documents ``GET /api/v1/system/block`` with ``InstanceBlockResponse``.

The block is set in this process only: the app of ``backend/app/main.py`` runs in process through
``httpx.ASGITransport`` (its lifespan does not run), and ``LIBREFOLIO_BLOCKED`` and ``LIBREFOLIO_DELETION_DATE`` are set
through ``monkeypatch``; ``instance_blocked()`` reads them at every request. The lane's shared backend is never blocked:
only the live checks of (b) run on it. The in-process app reads and writes the lane's database and signs its own
session tokens, so its sessions are opened in process. Write-scoped: each test that signs in registers a regular user
of its own while the instance is not blocked, and deletes it. On a lane whose database has no account yet, the first
registration becomes its administrator (``auth.register``): the test then registers the regular user it needs, and
deletes that administrator through the service layer, since the API keeps the last administrator.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.routing import Mount, Route, WebSocketRoute

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED, refuse_when_blocked
from backend.app.config import API_V1_PREFIX, TEST_LANE_HEADER, get_settings, is_test_mode
from backend.app.db.session import get_async_engine
from backend.app.schemas.system import InstanceBlockResponse, SystemInfoResponse
from backend.app.services.accounts import user_service
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
DELETION_DATE_VARIABLE = "LIBREFOLIO_DELETION_DATE"
DELETION_DATE = "2026-11-14"
PASSWORD = "InstanceBlockPass123!"
TIMEOUT = 30

#: The answer of a refused route to a signed-in caller, whole.
BLOCKED_ANSWER = {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}

#: Refused routes a signed-in user reads without changing anything; each answers 200 when the instance is not blocked.
REFUSED_READS = [
    pytest.param("/brokers", id="brokers"),
    pytest.param("/settings/user", id="user-settings"),
    pytest.param("/system/connection", id="system-connection"),
    pytest.param("/system/plugin-diagnostics", id="plugin-diagnostics"),
]

#: Public reads outside the allow-list: they answer anyone when the instance is not blocked.
PUBLIC_READS_OUTSIDE_THE_LIST = [
    pytest.param("/utilities/sectors", id="utilities-sectors"),
    pytest.param("/utilities/currencies", id="utilities-currencies"),
    pytest.param("/settings/global", id="global-settings"),
    pytest.param("/ai-export/catalog", id="ai-export-catalog"),
]

#: Every endpoint allowed on a blocked instance, by name, with the one route it serves. An addition goes through the
#: developer first (instance_block.py): this pin makes it show in review.
ALLOWED_ROUTES = {
    "backend.app.api.v1.auth.login": ("POST", "/api/v1/auth/login"),
    "backend.app.api.v1.auth.logout": ("POST", "/api/v1/auth/logout"),
    "backend.app.api.v1.auth.get_me": ("GET", "/api/v1/auth/me"),
    "backend.app.api.v1.auth.delete_own_account": ("DELETE", "/api/v1/auth/users/me"),
    "backend.app.api.v1.system.block.get_instance_block": ("GET", "/api/v1/system/block"),
    "backend.app.api.v1.system.instance.get_instance_config": ("GET", "/api/v1/system/instance"),
    "backend.app.api.v1.system.health.health_check": ("GET", "/api/v1/system/health"),
    "backend.app.api.v1.system.health.test_lane_health": ("GET", "/api/v1/system/test-lane-health"),
    "backend.app.api.v1.system.ready.get_readiness": ("GET", "/api/v1/system/ready"),
    "backend.app.api.v1.system.info.get_system_info": ("GET", "/api/v1/system/info"),
}

#: The routes under /api/v1 that are not API routes: FastAPI's own documentation (openapi_url, docs_url, redoc_url of
#: main.py), each a plain Route. No router dependency reaches them, so they answer on a blocked instance too.
DOCUMENTATION_ROUTES = {"/api/v1/docs": "Route", "/api/v1/openapi.json": "Route", "/api/v1/redoc": "Route"}


# =============================================================================
# The app in process, and the variables of the block
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """The app the server runs, in this process, on the lane's test database."""
    assert is_test_mode(), "Precondition: test mode, so the app in process reads and writes the lane's test database"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixtures that need it

    return main_app


def _block(monkeypatch: pytest.MonkeyPatch, deletion_date: str | None = DELETION_DATE) -> None:
    """Block the instance, in this process only; ``None`` leaves no deletion date."""
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    if deletion_date is None:
        monkeypatch.delenv(DELETION_DATE_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(DELETION_DATE_VARIABLE, deletion_date)


def _unblock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither variable set: the instance is not blocked, as every install."""
    monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)
    monkeypatch.delenv(DELETION_DATE_VARIABLE, raising=False)


async def _request(app: FastAPI, method: str, path: str, *, session: dict[str, str] | None = None, json: object = None) -> httpx.Response:
    """``method`` ``/api/v1<path>`` on the app in process, from a client of its own: a session travels only in ``session``."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", headers=session or {}, json=json, timeout=TIMEOUT)


def _session_of(login: httpx.Response) -> dict[str, str]:
    """The Cookie header of the session a login opened."""
    token = login.cookies.get(SESSION_COOKIE_NAME)
    assert login.status_code == 200 and token, f"the login must open a session: {login.status_code} {login.text}"
    return {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}


def _forged_session() -> dict[str, str]:
    """A session cookie the server never issued."""
    return {"Cookie": f"{SESSION_COOKIE_NAME}=forged-{uuid4().hex}"}


def _credentials(username: str) -> dict[str, str]:
    return {"username": username, "password": PASSWORD}


@dataclass(frozen=True)
class Account:
    """A regular user of one test, with the Cookie header of a session the app in process opened."""

    username: str
    session: dict[str, str]


async def _register(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> tuple[str, bool]:
    """Register a user of this test while the instance is not blocked, whatever the test set: its username, and whether
    it became the administrator (the first account of a database without one does, ``auth.register``)."""
    username = f"instblock_{uuid4().hex[:12]}"
    with monkeypatch.context() as unblocked:
        _unblock(unblocked)
        registered = await _request(app, "POST", "/auth/register", json={**_credentials(username), "email": f"{username}@example.com"})
    assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
    return username, registered.json()["user"]["is_superuser"]


async def _delete_administrator_of_this_test(username: str) -> None:
    """Cleanup of the administrator a registration of this test made on a database without accounts: the API keeps the
    last administrator, so it goes through the service layer, as the API would delete any other account."""
    assert is_test_mode(), "Precondition: test mode, so the cleanup reaches the lane's test database"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await user_service.get_user_by_username_or_email(session, username)
        if user is not None:
            await user_service.delete_user(session, user.id)


async def _regular_user(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str | None]:
    """A regular user of this test, and the administrator registered first when the lane's database had no account."""
    username, administrator = await _register(app, monkeypatch)
    if not administrator:
        return username, None
    regular, administrator = await _register(app, monkeypatch)
    if administrator:
        await _delete_administrator_of_this_test(regular)
        await _delete_administrator_of_this_test(username)
        pytest.fail(f"Setup: the second registration became an administrator too: {regular}")
    return regular, username


async def _delete_if_present(app: FastAPI, monkeypatch: pytest.MonkeyPatch, username: str) -> None:
    """Cleanup while the instance is not blocked: sign in by email, which a rename leaves, and delete the account, unless it is already gone."""
    with monkeypatch.context() as unblocked:
        _unblock(unblocked)
        login = await _request(app, "POST", "/auth/login", json={"username": f"{username}@example.com", "password": PASSWORD})
        if login.status_code == 401:
            return
        deleted = await _request(app, "DELETE", "/auth/users/me", session=_session_of(login))
    assert deleted.status_code == 200, f"Cleanup: deleting {username} failed: {deleted.status_code} {deleted.text}"


async def _delete_users_of_this_test(app: FastAPI, monkeypatch: pytest.MonkeyPatch, username: str | None, administrator: str | None) -> None:
    """Cleanup: the regular user through the API, then the administrator this test made, if any."""
    try:
        if username is not None:
            await _delete_if_present(app, monkeypatch, username)
    finally:
        if administrator is not None:
            await _delete_administrator_of_this_test(administrator)


def _split_by_role(username: str, administrator: bool) -> tuple[str | None, str | None]:
    """``(regular, administrator)`` for one registered user, as ``_delete_users_of_this_test`` takes them."""
    return (None, username) if administrator else (username, None)


@pytest_asyncio.fixture
async def account(app, monkeypatch) -> AsyncIterator[Account]:
    """A regular user of this test, signed in through the app in process while not blocked; deleted at teardown."""
    username, administrator = await _regular_user(app, monkeypatch)
    try:
        with monkeypatch.context() as unblocked:
            _unblock(unblocked)
            session = _session_of(await _request(app, "POST", "/auth/login", json=_credentials(username)))
        yield Account(username, session)
    finally:
        await _delete_users_of_this_test(app, monkeypatch, username, administrator)


# =============================================================================
# (a) Blocked: anonymous callers
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("forged", [False, True], ids=["no-cookie", "forged-session-cookie"])
@pytest.mark.parametrize("path", REFUSED_READS)
async def test_anonymous_gets_the_401_of_any_protected_route(app, monkeypatch, path, forged):
    """(a) Without a valid session a refused route answers as it does when not blocked: the 401 of get_current_user."""
    session = _forged_session() if forged else None
    _unblock(monkeypatch)
    before = await _request(app, "GET", path, session=session)
    _block(monkeypatch)
    blocked = await _request(app, "GET", path, session=session)

    detail = "Session expired or invalid" if forged else "Not authenticated"
    assert (before.status_code, before.json()) == (401, {"detail": detail}), f"Barrier: GET {path} without a valid session is a 401 when not blocked: {before.status_code} {before.text}"
    assert (blocked.status_code, blocked.json()) == (before.status_code, before.json()), f"GET {path} without a valid session must answer the same when blocked: {blocked.status_code} {blocked.text}"
    print_success(f"GET {path} ({'forged' if forged else 'no'} cookie): 401 {detail!r}, blocked or not")


@pytest.mark.asyncio
async def test_anonymous_cannot_register_on_a_blocked_instance(app, monkeypatch):
    """(a) POST /auth/register is no allowed route: anonymous, it gets the 401, and no account is created."""
    print_section("Instance block: registration while blocked")
    username = f"instblock_{uuid4().hex[:12]}"
    _block(monkeypatch)

    registered = await _request(app, "POST", "/auth/register", json={**_credentials(username), "email": f"{username}@example.com"})
    login = await _request(app, "POST", "/auth/login", json=_credentials(username))

    try:
        assert (registered.status_code, registered.json()) == (401, {"detail": "Not authenticated"}), f"an anonymous registration on a blocked instance must get the 401 of get_current_user: {registered.status_code} {registered.text}"
        assert (login.status_code, login.json()) == (401, {"detail": "Invalid credentials"}), f"the refused registration must create no account, so its credentials sign nobody in: {login.status_code} {login.text}"
    finally:
        if registered.status_code == 201:
            await _delete_users_of_this_test(app, monkeypatch, *_split_by_role(username, registered.json()["user"]["is_superuser"]))
    print_success("POST /auth/register while blocked: 401, no account")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PUBLIC_READS_OUTSIDE_THE_LIST)
async def test_a_public_route_outside_the_list_answers_401_only_while_blocked(app, monkeypatch, path):
    """(a) The known, accepted limit, pending a developer decision (stated in instance_block.py): a public route outside
    ALLOWED_WHEN_BLOCKED answers anyone when the instance is not blocked, and the 401 of get_current_user while it is.
    A caller without a session can tell from it that the instance is blocked, and nothing more. Documented as it is:
    if the developer decides otherwise, this test changes with the code."""
    _unblock(monkeypatch)
    before = await _request(app, "GET", path)
    _block(monkeypatch)
    blocked = await _request(app, "GET", path)

    assert before.status_code == 200, f"Barrier: GET {path} is public, it answers anyone when not blocked: {before.status_code} {before.text}"
    assert (blocked.status_code, blocked.json()) == (401, {"detail": "Not authenticated"}), f"GET {path} without a session on a blocked instance: {blocked.status_code} {blocked.text}"
    print_success(f"GET {path} anonymous: 200 when not blocked, 401 when blocked (known limit)")


@pytest.mark.asyncio
async def test_registration_is_the_same_known_limit(app, monkeypatch):
    """(a) The same known, accepted limit, pending a developer decision, on POST /auth/register: an anonymous
    registration is created (201) when the instance is not blocked, and gets the 401 of get_current_user while it is."""
    blocked_username = f"instblock_{uuid4().hex[:12]}"
    _block(monkeypatch)
    blocked = await _request(app, "POST", "/auth/register", json={**_credentials(blocked_username), "email": f"{blocked_username}@example.com"})

    username, administrator = await _register(app, monkeypatch)
    await _delete_users_of_this_test(app, monkeypatch, *_split_by_role(username, administrator))

    assert (blocked.status_code, blocked.json()) == (401, {"detail": "Not authenticated"}), f"POST /auth/register without a session on a blocked instance: {blocked.status_code} {blocked.text}"
    print_success("POST /auth/register anonymous: 201 when not blocked, 401 when blocked (known limit)")


# =============================================================================
# (a) Blocked: signed-in callers of refused routes
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("path", REFUSED_READS)
async def test_a_signed_in_user_gets_423_on_a_refused_route(app, monkeypatch, account, path):
    """(a) The same session reads the route when not blocked, and gets exactly the 423 of the block when blocked."""
    _unblock(monkeypatch)
    before = await _request(app, "GET", path, session=account.session)
    _block(monkeypatch)
    blocked = await _request(app, "GET", path, session=account.session)

    assert before.status_code == 200, f"Barrier: GET {path} answers this user when not blocked: {before.status_code} {before.text}"
    assert (blocked.status_code, blocked.json()) == (423, BLOCKED_ANSWER), f"GET {path} on a blocked instance must answer 423 with the block's code and message: {blocked.status_code} {blocked.text}"
    print_success(f"GET {path}: 200 when not blocked, 423 when blocked")


@pytest.mark.asyncio
async def test_a_signed_in_user_cannot_register_or_change_the_profile_on_a_blocked_instance(app, monkeypatch, account):
    """(a) Refused writes: a registration and a profile change get the 423, and neither happens."""
    new_username = f"instblock_{uuid4().hex[:12]}"
    renamed = f"instblock_{uuid4().hex[:12]}"
    _block(monkeypatch)

    registered = await _request(app, "POST", "/auth/register", session=account.session, json={**_credentials(new_username), "email": f"{new_username}@example.com"})
    profile = await _request(app, "PUT", "/auth/profile", session=account.session, json={"username": renamed})
    login = await _request(app, "POST", "/auth/login", json=_credentials(new_username))
    me = await _request(app, "GET", "/auth/me", session=account.session)

    try:
        assert (registered.status_code, registered.json()) == (423, BLOCKED_ANSWER), f"POST /auth/register with a session on a blocked instance: {registered.status_code} {registered.text}"
        assert (profile.status_code, profile.json()) == (423, BLOCKED_ANSWER), f"PUT /auth/profile on a blocked instance: {profile.status_code} {profile.text}"
        assert login.status_code == 401, f"the refused registration must create no account: {login.status_code} {login.text}"
        assert me.status_code == 200 and me.json()["user"]["username"] == account.username, f"the refused profile change must leave the username as it was: {me.status_code} {me.text}"
    finally:
        if registered.status_code == 201:
            await _delete_if_present(app, monkeypatch, new_username)
    print_success("register and profile change while blocked: 423, nothing changed")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        pytest.param("/auth/change-password", {}, id="change-password-empty-body"),
        pytest.param("/brokers", {}, id="create-brokers-an-object-for-a-list"),
        pytest.param("/brokers", [{"name": None}], id="create-brokers-a-broker-without-name"),
    ],
)
async def test_an_invalid_body_gets_423_not_422(app, monkeypatch, account, path, body):
    """(a) The router dependency runs before the body is validated: a signed-in invalid POST meets the block first."""
    _unblock(monkeypatch)
    before = await _request(app, "POST", path, session=account.session, json=body)
    _block(monkeypatch)
    blocked = await _request(app, "POST", path, session=account.session, json=body)

    assert before.status_code == 422, f"Barrier: the body is invalid, so POST {path} answers 422 when not blocked: {before.status_code} {before.text}"
    assert (blocked.status_code, blocked.json()) == (423, BLOCKED_ANSWER), f"POST {path} with an invalid body on a blocked instance must answer 423, not 422: {blocked.status_code} {blocked.text}"
    print_success(f"POST {path} {body!r}: 422 when not blocked, 423 when blocked")


# =============================================================================
# (a) Blocked: the allowed routes answer as usual
# =============================================================================


@pytest.mark.asyncio
async def test_each_allowed_route_answers_a_signed_in_user(app, monkeypatch, account):
    """(a) The routes of the block page, the probes and the version answer a signed-in user as they always do."""
    print_section("Instance block: the allowed routes, signed in")
    lane_token = f"lane-{uuid4().hex}"
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_token)
    _block(monkeypatch)

    me = await _request(app, "GET", "/auth/me", session=account.session)
    block = await _request(app, "GET", "/system/block", session=account.session)
    info = await _request(app, "GET", "/system/info", session=account.session)
    health = await _request(app, "GET", "/system/health", session=account.session)
    lane = await _request(app, "GET", f"/system/test-lane-health?token={lane_token}", session=account.session)
    ready = await _request(app, "GET", "/system/ready", session=account.session)
    instance = await _request(app, "GET", "/system/instance", session=account.session)

    assert me.status_code == 200 and me.json()["user"]["username"] == account.username, f"GET /auth/me: {me.status_code} {me.text}"
    assert (block.status_code, block.json()) == (200, {"blocked": True, "deletion_date": DELETION_DATE}), f"GET /system/block: {block.status_code} {block.text}"
    assert info.status_code == 200 and set(info.json()) == set(SystemInfoResponse.model_fields), f"GET /system/info must answer in full to a session: {info.status_code} {info.text}"
    SystemInfoResponse.model_validate(info.json())
    assert (health.status_code, health.json()) == (200, {"status": "ok"}), f"GET /system/health: {health.status_code} {health.text}"
    assert (lane.status_code, lane.json(), lane.headers.get(TEST_LANE_HEADER)) == (200, {"status": "ok"}, lane_token), f"GET /system/test-lane-health with the lane's token: {lane.status_code} {lane.text}"
    assert (ready.status_code, ready.json()) == (200, {"status": "ready", "checks": {"database": "ok", "migrations": "ok"}}), f"GET /system/ready on the lane's migrated database: {ready.status_code} {ready.text}"
    assert (instance.status_code, instance.json()) == (200, {"profile": "managed"}), f"GET /system/instance: {instance.status_code} {instance.text}"
    print_success("me, block, info, health, test-lane-health, ready, instance: as usual")


@pytest.mark.asyncio
async def test_the_allowed_routes_answer_anonymous_callers_as_usual(app, monkeypatch):
    """(a) Allowed is not public: the probes and the version answer anyone, the block page and /auth/me still want a session."""
    _block(monkeypatch)

    health = await _request(app, "GET", "/system/health")
    ready = await _request(app, "GET", "/system/ready")
    instance = await _request(app, "GET", "/system/instance")
    info = await _request(app, "GET", "/system/info")
    lane = await _request(app, "GET", f"/system/test-lane-health?token=not-the-lane-{uuid4().hex}")
    block = await _request(app, "GET", "/system/block")
    me = await _request(app, "GET", "/auth/me")

    assert (health.status_code, health.json()) == (200, {"status": "ok"}), f"GET /system/health: {health.status_code} {health.text}"
    assert ready.status_code == 200 and ready.json()["status"] == "ready", f"GET /system/ready: {ready.status_code} {ready.text}"
    assert instance.status_code == 200 and set(instance.json()) == {"profile"}, f"GET /system/instance: {instance.status_code} {instance.text}"
    assert info.status_code == 200 and set(info.json()) == {"app_version"}, f"GET /system/info answers the app version only without a session: {info.status_code} {info.text}"
    assert lane.status_code == 404, f"GET /system/test-lane-health with another token answers its own 404: {lane.status_code} {lane.text}"
    assert (block.status_code, block.json()) == (401, {"detail": "Not authenticated"}), f"GET /system/block needs a session: {block.status_code} {block.text}"
    assert (me.status_code, me.json()) == (401, {"detail": "Not authenticated"}), f"GET /auth/me needs a session: {me.status_code} {me.text}"
    print_success("health, ready, instance, info (version): open; block and me: 401")


@pytest.mark.asyncio
async def test_signing_in_and_out_works_on_a_blocked_instance(app, monkeypatch, account):
    """(a) A blocked instance still signs users in, refuses a wrong password as usual, and signs them out."""
    _block(monkeypatch)

    wrong = await _request(app, "POST", "/auth/login", json={"username": account.username, "password": "Not" + PASSWORD})
    login = await _request(app, "POST", "/auth/login", json=_credentials(account.username))
    session = _session_of(login)
    me = await _request(app, "GET", "/auth/me", session=session)
    logout = await _request(app, "POST", "/auth/logout", session=session)

    assert (wrong.status_code, wrong.json()) == (401, {"detail": "Invalid credentials"}), f"a wrong password while blocked: {wrong.status_code} {wrong.text}"
    assert login.json()["user"]["username"] == account.username, f"the login must answer its user: {login.text}"
    assert me.status_code == 200 and me.json()["user"]["username"] == account.username, f"the new session must be accepted: {me.status_code} {me.text}"
    assert logout.status_code == 200, f"POST /auth/logout while blocked: {logout.status_code} {logout.text}"
    cleared = [header for header in logout.headers.get_list("set-cookie") if header.startswith(f"{SESSION_COOKIE_NAME}=")]
    assert len(cleared) == 1 and "max-age=0" in cleared[0].lower(), f"the logout must clear the session cookie: {logout.headers.get_list('set-cookie')}"
    print_success("wrong password 401, login 200, me 200, logout 200 with the cookie cleared")


@pytest.mark.asyncio
async def test_a_user_can_delete_their_own_account_on_a_blocked_instance(app, monkeypatch):
    """(a) DELETE /auth/users/me is allowed: the account goes, and its credentials sign nobody in afterwards."""
    username, administrator = await _regular_user(app, monkeypatch)
    try:
        _block(monkeypatch)
        session = _session_of(await _request(app, "POST", "/auth/login", json=_credentials(username)))

        deleted = await _request(app, "DELETE", "/auth/users/me", session=session)
        login = await _request(app, "POST", "/auth/login", json=_credentials(username))

        assert deleted.status_code == 200, f"DELETE /auth/users/me while blocked: {deleted.status_code} {deleted.text}"
        assert (login.status_code, login.json()) == (401, {"detail": "Invalid credentials"}), f"the deleted account must sign nobody in: {login.status_code} {login.text}"
    finally:
        await _delete_users_of_this_test(app, monkeypatch, username, administrator)
    print_success("own account deleted while blocked")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deletion_date", "answered"),
    [
        pytest.param(DELETION_DATE, DELETION_DATE, id="with-a-date"),
        pytest.param(f" {DELETION_DATE} ", DELETION_DATE, id="with-a-date-stripped"),
        pytest.param(None, None, id="without-a-date"),
        pytest.param("   ", None, id="with-a-blank-date"),
    ],
)
async def test_the_block_page_answers_the_deletion_date_when_given(app, monkeypatch, account, deletion_date, answered):
    """(a) GET /system/block on a blocked instance: blocked, and the deletion date in ISO, or null when none is given."""
    _block(monkeypatch, deletion_date)

    response = await _request(app, "GET", "/system/block", session=account.session)

    assert (response.status_code, response.json()) == (200, {"blocked": True, "deletion_date": answered}), f"GET /system/block with {DELETION_DATE_VARIABLE}={deletion_date!r}: {response.status_code} {response.text}"
    InstanceBlockResponse.model_validate(response.json())


# =============================================================================
# (b) Not blocked
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "", "  ", "false", "0", "no", "OFF"], ids=["unset", "empty", "blank", "false", "0", "no", "OFF"])
async def test_routes_answer_as_before_when_not_blocked(app, monkeypatch, account, value):
    """(b) Unset, blank or a value that does not block: reads answer, invalid bodies are 422, anonymous callers 401."""
    if value is None:
        monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(BLOCKED_VARIABLE, value)
    monkeypatch.delenv(DELETION_DATE_VARIABLE, raising=False)

    brokers = await _request(app, "GET", "/brokers", session=account.session)
    connection = await _request(app, "GET", "/system/connection", session=account.session)
    invalid = await _request(app, "POST", "/auth/change-password", session=account.session, json={})
    anonymous = await _request(app, "GET", "/brokers")
    block = await _request(app, "GET", "/system/block", session=account.session)

    assert brokers.status_code == 200, f"GET /brokers: {brokers.status_code} {brokers.text}"
    assert connection.status_code == 200, f"GET /system/connection: {connection.status_code} {connection.text}"
    assert invalid.status_code == 422, f"POST /auth/change-password with an empty body: {invalid.status_code} {invalid.text}"
    assert (anonymous.status_code, anonymous.json()) == (401, {"detail": "Not authenticated"}), f"GET /brokers without a session: {anonymous.status_code} {anonymous.text}"
    assert (block.status_code, block.json()) == (200, {"blocked": False, "deletion_date": None}), f"GET /system/block: {block.status_code} {block.text}"
    print_success(f"{BLOCKED_VARIABLE}={value!r}: routes as before, not blocked")


@pytest.mark.asyncio
async def test_the_block_page_needs_a_session_when_not_blocked(app, monkeypatch):
    """(b) GET /system/block is for signed-in users: 401 without a session, or with one the server never issued."""
    _unblock(monkeypatch)

    anonymous = await _request(app, "GET", "/system/block")
    forged = await _request(app, "GET", "/system/block", session=_forged_session())

    assert (anonymous.status_code, anonymous.json()) == (401, {"detail": "Not authenticated"}), f"without a session: {anonymous.status_code} {anonymous.text}"
    assert (forged.status_code, forged.json()) == (401, {"detail": "Session expired or invalid"}), f"with a forged session: {forged.status_code} {forged.text}"


# The lane's backend, which is never blocked: the route is registered there and answers as the app in process does.

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}{API_V1_PREFIX}"


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest_asyncio.fixture
async def live_session(test_server) -> AsyncIterator[dict[str, str]]:
    """The Cookie header of a regular user of this test on the lane's backend; the account is deleted at teardown, and
    so is the administrator a first registration makes on a database without accounts."""

    async def register(client: httpx.AsyncClient) -> tuple[str, bool]:
        username = f"instblock_{uuid4().hex[:12]}"
        registered = await client.post(f"{API_BASE}/auth/register", json={**_credentials(username), "email": f"{username}@example.com"}, timeout=TIMEOUT)
        assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
        return username, registered.json()["user"]["is_superuser"]

    async with httpx.AsyncClient() as client:
        username, administrator = await register(client)
        bootstrap = None
        if administrator:
            bootstrap, (username, administrator) = username, await register(client)
        try:
            assert administrator is False, f"Setup: {username} must be a regular user"
            session = _session_of(await client.post(f"{API_BASE}/auth/login", json=_credentials(username), timeout=TIMEOUT))
            client.cookies.clear()

            yield session

            deleted = await client.delete(f"{API_BASE}/auth/users/me", headers=session, timeout=TIMEOUT)
            assert deleted.status_code == 200, f"Cleanup: deleting {username} failed: {deleted.status_code} {deleted.text}"
        finally:
            if bootstrap is not None:
                await _delete_administrator_of_this_test(bootstrap)


@pytest.mark.asyncio
async def test_the_lane_backend_is_not_blocked(live_session):
    """(b) Live: the lane's backend answers the block page, not blocked and without a date, and only to a session."""
    async with httpx.AsyncClient() as client:
        signed_in = await client.get(f"{API_BASE}/system/block", headers=live_session, timeout=TIMEOUT)
    async with httpx.AsyncClient() as client:
        anonymous = await client.get(f"{API_BASE}/system/block", timeout=TIMEOUT)

    assert (signed_in.status_code, signed_in.json()) == (200, {"blocked": False, "deletion_date": None}), f"GET /system/block on the lane's backend: {signed_in.status_code} {signed_in.text}"
    assert (anonymous.status_code, anonymous.json()) == (401, {"detail": "Not authenticated"}), f"GET /system/block without a session on the lane's backend: {anonymous.status_code} {anonymous.text}"
    print_success("lane backend: not blocked, the block page behind the session")


# =============================================================================
# (c) The guard
# =============================================================================


def _under_api_v1(path: str | None) -> bool:
    return path is not None and (path == API_V1_PREFIX or path.startswith(API_V1_PREFIX + "/"))


def _path_of(context) -> str | None:
    """The full path a route context serves. An included plain route, WebSocket or mount is served by the Starlette route
    FastAPI builds for it (``starlette_route``), whose path carries the prefixes; the context's own path is None then."""
    starlette_route = getattr(context, "starlette_route", None)
    return getattr(starlette_route, "path", None) if starlette_route is not None else context.path


def _api_routes(routes: list) -> list:
    """The API routes under /api/v1 as FastAPI serves them: effective route contexts, each with its effective dependant."""
    return [context for context in iter_route_contexts(routes) if _under_api_v1(_path_of(context)) and isinstance(context.original_route, APIRoute)]


def _not_blocked_first(routes: list) -> dict[str, str]:
    """Every route or mount under /api/v1 the block does not reach first, by path, with the reason: not an APIRoute (no
    router dependency reaches it, or not as a request), or an APIRoute whose first dependency is not refuse_when_blocked."""
    flagged: dict[str, str] = {}
    for context in iter_route_contexts(routes):
        path = _path_of(context)
        if not _under_api_v1(path):
            continue
        route = context.original_route
        if not isinstance(route, APIRoute):
            flagged[path] = type(route).__name__
            continue
        dependencies = context.dependant.dependencies
        first = dependencies[0].call if dependencies else None
        if first is not refuse_when_blocked:
            flagged[path] = f"APIRoute {'/'.join(sorted(context.methods or ()))}, first dependency {getattr(first, '__name__', first)}"
    return flagged


def _endpoint_name(endpoint) -> str:
    return f"{endpoint.__module__}.{endpoint.__qualname__}"


class _ProbeRoute(APIRoute):
    """An APIRoute subclass, as ToolRoute is one: the router's dependencies reach it."""


def test_the_guard_walk_flags_every_route_the_block_does_not_reach_first():
    """(c) Presence barrier of the next test: through the same walk, under /api/v1, a plain Route, a WebSocketRoute, a
    WebSocket of the guarded router, a Mount, an APIRoute outside the guarded router and an APIRoute whose router puts
    another dependency first are flagged; an APIRoute of the guarded router, and one of an APIRoute subclass, are not."""
    guarded = APIRouter(dependencies=[Depends(refuse_when_blocked)])
    guarded_subclass = APIRouter(dependencies=[Depends(refuse_when_blocked)], route_class=_ProbeRoute)
    late = APIRouter(dependencies=[Depends(lambda: None), Depends(refuse_when_blocked)])

    @guarded.get("/inside")
    def inside() -> dict:
        return {}

    @guarded.websocket("/guarded-socket")
    async def guarded_socket(websocket: WebSocket) -> None:
        await websocket.close()

    @guarded_subclass.get("/inside-subclass")
    def inside_subclass() -> dict:
        return {}

    @late.get("/late")
    def late_route() -> dict:
        return {}

    async def plain(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("")

    async def socket(websocket: WebSocket) -> None:
        await websocket.close()

    probe = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    for router in (guarded, guarded_subclass, late):
        probe.include_router(router, prefix=API_V1_PREFIX)

    @probe.get(f"{API_V1_PREFIX}/outside")
    def outside() -> dict:
        return {}

    # Added as Starlette objects, as any code could add them under /api/v1
    probe.router.routes.extend([Route(f"{API_V1_PREFIX}/plain", plain), WebSocketRoute(f"{API_V1_PREFIX}/socket", socket), Mount(f"{API_V1_PREFIX}/files", app=PlainTextResponse(""))])

    flagged = _not_blocked_first(probe.routes)

    expected = {
        "/api/v1/files": "Mount",
        "/api/v1/guarded-socket": "APIWebSocketRoute",
        "/api/v1/late": "APIRoute GET, first dependency <lambda>",
        "/api/v1/outside": "APIRoute GET, first dependency None",
        "/api/v1/plain": "Route",
        "/api/v1/socket": "WebSocketRoute",
    }
    assert flagged == expected, f"the walk must flag exactly the six routes the block does not reach first, each with its reason: {flagged}"
    assert {"/api/v1/inside", "/api/v1/inside-subclass"} <= {_path_of(context) for context in _api_routes(probe.routes)}, "Barrier: the walk must see the guarded routes it does not flag"


def test_every_route_under_api_v1_is_an_api_route_resolving_the_block_first(app):
    """(c) On the app the server runs, every route or mount under /api/v1 is an APIRoute (or a subclass) whose first
    dependency is refuse_when_blocked, but FastAPI's own documentation, pinned: a WebSocket, a plain route or a mount
    added under /api/v1 would answer on a blocked instance, and fails here."""
    print_section("Instance block: the guard on every route")
    walked = {_path_of(context) for context in _api_routes(app.routes)}
    known = {"/api/v1/auth/login", "/api/v1/brokers", "/api/v1/system/block", "/api/v1/system/ready"}
    assert known <= walked, f"Barrier: the walk must reach the API routes of the app: missing {sorted(known - walked)}"

    flagged = _not_blocked_first(app.routes)

    unexpected = {path: reason for path, reason in flagged.items() if DOCUMENTATION_ROUTES.get(path) != reason}
    assert not unexpected, "under /api/v1 only FastAPI's documentation may stay out of the block; these routes are not reached first by refuse_when_blocked:\n" + "\n".join(f"  {path}: {reason}" for path, reason in sorted(unexpected.items()))
    assert flagged == DOCUMENTATION_ROUTES, f"FastAPI's documentation routes under /api/v1 changed: expected {DOCUMENTATION_ROUTES}, found {flagged}"
    print_success(f"{len(walked)} API paths under {API_V1_PREFIX}, each resolving refuse_when_blocked first; outside: the {len(DOCUMENTATION_ROUTES)} documentation routes")


def test_every_allowed_endpoint_serves_a_registered_route(app):
    """(c) Each function of ALLOWED_WHEN_BLOCKED is the endpoint of a route of the app: an entry that serves nothing is a stale one."""
    served = {context.endpoint for context in _api_routes(app.routes)}

    stale = sorted(_endpoint_name(endpoint) for endpoint in ALLOWED_WHEN_BLOCKED if endpoint not in served)

    assert not stale, f"these allowed endpoints serve no route of the app: {stale}"


def test_the_allowed_list_is_pinned_by_name_and_route(app):
    """(c) The allowed endpoints, by name, each with the one route it serves: an addition to the list shows here."""
    names = sorted(_endpoint_name(endpoint) for endpoint in ALLOWED_WHEN_BLOCKED)
    assert names == sorted(ALLOWED_ROUTES), f"ALLOWED_WHEN_BLOCKED changed: an endpoint allowed on a blocked instance goes through the developer first:\n  expected {sorted(ALLOWED_ROUTES)}\n  got      {names}"

    routes: dict[str, set[tuple[str, str]]] = {}
    for context in _api_routes(app.routes):
        if context.endpoint in ALLOWED_WHEN_BLOCKED:
            routes.setdefault(_endpoint_name(context.endpoint), set()).update((method, _path_of(context)) for method in context.methods or ())

    assert routes == {name: {route} for name, route in ALLOWED_ROUTES.items()}, f"each allowed endpoint must serve exactly its one route: {routes}"
    print_success(f"{len(names)} allowed endpoints, each on its route")


# =============================================================================
# (d) OpenAPI
# =============================================================================


def test_openapi_documents_the_block_page(app):
    """(d) GET /api/v1/system/block: a System route whose 200 is InstanceBlockResponse, blocked required, the date optional."""
    document = app.openapi()
    operation = document["paths"][f"{API_V1_PREFIX}/system/block"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert schema == {"$ref": "#/components/schemas/InstanceBlockResponse"}, f"the 200 of GET /system/block must be InstanceBlockResponse: {schema}"
    assert operation["tags"] == ["System"], f"GET /system/block belongs to the System tag: {operation['tags']}"
    component = document["components"]["schemas"]["InstanceBlockResponse"]
    properties = component["properties"]
    assert set(properties) == {"blocked", "deletion_date"} and component.get("required") == ["blocked"], f"InstanceBlockResponse: {component}"
    assert properties["blocked"]["type"] == "boolean", f"blocked: {properties['blocked']}"
    variants = properties["deletion_date"].get("anyOf", [])
    assert {"type": "string", "format": "date"} in variants and {"type": "null"} in variants, f"deletion_date is an ISO date or null: {properties['deletion_date']}"

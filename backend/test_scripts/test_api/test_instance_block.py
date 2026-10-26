"""
The instance block (workstream H, platform, checkpoint CP6, decision D4).

Under test: ``backend/app/api/v1/instance_block.py`` (``refuse_when_blocked``, a dependency of the ``/api/v1`` router,
and ``ALLOWED_WHEN_BLOCKED``) and the block page ``GET /api/v1/system/block`` (``api/v1/system/block.py``,
``InstanceBlockResponse``). The contract:

(a) Blocked (``LIBREFOLIO_BLOCKED``). An anonymous caller of a protected refused route gets the 401 of
    ``get_current_user``, the same status and body as on an instance that is not blocked. A public route outside the
    allow-list (registration, the ``utilities`` lists, the AI Export catalogue) answers that 401
    only while blocked, and its usual answer otherwise: the known limit stated in ``instance_block.py``, documented as it
    is by one test. A refused registration creates no account. A signed-in caller gets ``423`` with exactly
    ``{"detail": {"code": "instance_blocked", "message": ...}}``, before the body is validated: an invalid body gets
    423, not 422. The allowed routes answer as usual: ``/auth/me``, ``/system/block`` (blocked, with the deletion date),
    ``/system/info`` in full, health, the test runner's probe, readiness and the public configuration; signing in and
    out works, and so does deleting one's own account. A link already sent works too: ``POST /auth/tokens/inspect`` and
    ``POST /auth/password-reset`` answer a caller without a session as on the instance not blocked, and a reset link
    issued before the block sets the new password, which signs in and reaches the block page. Registration stays out of
    the list: an invitation reads as valid, and spending it registers nobody. ``/system/block`` gives an administrator
    ``billing_url``, ``LIBREFOLIO_BILLING_URL`` through A5's ``billing_link()`` (one trailing slash removed; null when
    unset or not an http(s) address), and anyone else null, whatever the variable says. An administrator keeps the full
    backup (decision 12): its four routes start, poll, download and delete a job as on any instance, and
    ``/system/block`` answers ``backup_available`` true; a regular user meets the 403 of ``require_admin`` on each of
    them, never the 423, and the backup service is never reached.
(b) Not blocked (unset, blank, or a value that does not block): the routes answer as before, and ``/system/block`` is
    ``{"blocked": false, "deletion_date": null, "billing_url": null, "backup_available": false}`` with the session of a
    regular user and 401 without, on the lane's backend too.
(c) The guard. FastAPI gives router dependencies to an ``APIRoute`` (and its subclasses) only, never to a plain
    ``Route``, a ``WebSocketRoute`` or a ``Mount``. So every route or mount of the app under ``/api/v1`` must be an
    ``APIRoute`` resolving ``refuse_when_blocked`` first, before the route's own dependencies, so that a signed-in
    caller of a refused route meets the block before any other answer. The one exception, pinned, is the API
    documentation (H-55 R5): ``/api/v1/docs`` and ``/api/v1/redoc``, our own pages, and their start scripts
    ``/api/v1/docs/swagger-init.js`` and ``/api/v1/redoc/redoc-init.js`` (``install_api_docs``: four ``APIRoute``
    endpoints of ``backend/app/api/api_docs.py``, registered on the app itself and out of the OpenAPI schema, so no router
    dependency reaches them) and ``/api/v1/openapi.json`` (FastAPI's ``openapi_url``, a plain ``Route``). They carry the
    API's schema and no data, exist only where the documentation is on (the app of this test runs in test mode, so it is),
    and the block does not reach them. Every function of ``ALLOWED_WHEN_BLOCKED`` is the endpoint of a registered route, and the list is pinned
    by name and by route, so an addition shows in review.
(d) OpenAPI documents ``GET /api/v1/system/block`` with ``InstanceBlockResponse``: ``blocked`` required, the deletion
    date and the billing link optional.

The block is set in this process only: the app of ``backend/app/main.py`` runs in process through
``httpx.ASGITransport`` (its lifespan does not run), and ``LIBREFOLIO_BLOCKED``, ``LIBREFOLIO_DELETION_DATE`` and
``LIBREFOLIO_BILLING_URL`` are set through ``monkeypatch``; ``instance_blocked()`` and ``billing_link()`` read them at
every request. The lane's shared backend is never blocked: only the live checks of (b) run on it. The in-process app
reads and writes the lane's database and signs its own session tokens, so its sessions are opened in process.
Write-scoped: each test that signs in registers a regular user of its own while the instance is not blocked, and deletes
it. On a lane whose database has no account yet, the first registration becomes its administrator (``auth.register``):
the test then registers the regular user it needs, and deletes that administrator through the service layer, since the
API keeps the last administrator. The administrator of a billing case is a user of the test promoted through
``user_service``, as ``test_users_admin_api.py`` does on the lane, and deleted through the service layer too. The links
are issued by A5's token service in the lane's database, as ``test_registration_api.py`` issues them: a reset link goes
with its account, an invitation is deleted by id.
The backup cases sign in the same administrator, and replace the backup service in this process (``monkeypatch`` on
``services/platform/instance_backup/jobs.py``): no backup runs on the lane's data directory, whose run lock other
suites of the lane take.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.routing import Mount, Route, WebSocketRoute

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.api.v1.backup import instance as backup_instance
from backend.app.api.v1.backup import panel as backup_panel
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED, refuse_when_blocked
from backend.app.config import API_V1_PREFIX, TEST_LANE_HEADER, get_settings, is_test_mode
from backend.app.config.platform import instance_blocked
from backend.app.db.models import AccountToken, AccountTokenPurpose
from backend.app.db.session import get_async_engine
from backend.app.schemas.system import InstanceBlockResponse, SystemInfoPublicResponse, SystemInfoResponse
from backend.app.services.accounts import token_service, user_service
from backend.app.services.accounts.registration_service import billing_link
from backend.app.services.platform.instance_backup import jobs
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
DELETION_DATE_VARIABLE = "LIBREFOLIO_DELETION_DATE"
DELETION_DATE = "2026-11-14"
PASSWORD = "InstanceBlockPass123!"
NEW_PASSWORD = "InstanceBlockReset456!"
TIMEOUT = 30

BILLING_VARIABLE = "LIBREFOLIO_BILLING_URL"
#: Where a provider's customer manages the subscription, as the provider writes it, and as the block page gives it.
BILLING_ADDRESS = "https://billing.example.test/acme/"
BILLING_LINK = "https://billing.example.test/acme"
#: Not an http(s) address: billing_link() refuses it.
INVALID_BILLING_ADDRESS = "ftp://billing.example.test"

#: The two link routes, under /api/v1, and a placeholder token that no link ever carried.
INSPECT = "/auth/tokens/inspect"
RESET = "/auth/password-reset"
NEVER_ISSUED_TOKEN = "never-issued-instance-block-placeholder"

#: The answer of a refused route to a signed-in caller, whole.
BLOCKED_ANSWER = {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}

#: Refused routes a signed-in user reads without changing anything; each answers 200 when the instance is not blocked.
REFUSED_READS = [
    pytest.param("/brokers", id="brokers"),
    pytest.param("/settings/user", id="user-settings"),
    pytest.param("/settings/global", id="global-settings"),
    pytest.param("/system/connection", id="system-connection"),
    pytest.param("/system/plugin-diagnostics", id="plugin-diagnostics"),
]

#: Public reads outside the allow-list: they answer anyone when the instance is not blocked.
PUBLIC_READS_OUTSIDE_THE_LIST = [
    pytest.param("/utilities/sectors", id="utilities-sectors"),
    pytest.param("/utilities/currencies", id="utilities-currencies"),
    pytest.param("/ai-export/catalog", id="ai-export-catalog"),
    pytest.param("/auth/address-probe", id="address-probe"),
    pytest.param("/auth/address-probe.png", id="address-probe-image"),
]

#: Every endpoint allowed on a blocked instance, by name, with the one route it serves. An addition goes through the
#: developer first (instance_block.py): this pin makes it show in review.
ALLOWED_ROUTES = {
    "backend.app.api.v1.auth.login": ("POST", "/api/v1/auth/login"),
    "backend.app.api.v1.auth.logout": ("POST", "/api/v1/auth/logout"),
    "backend.app.api.v1.auth.get_me": ("GET", "/api/v1/auth/me"),
    "backend.app.api.v1.auth.inspect_link_token": ("POST", "/api/v1/auth/tokens/inspect"),
    "backend.app.api.v1.auth.reset_password_with_link": ("POST", "/api/v1/auth/password-reset"),
    "backend.app.api.v1.auth.delete_own_account": ("DELETE", "/api/v1/auth/users/me"),
    "backend.app.api.v1.auth.preview_own_account_deletion": ("GET", "/api/v1/auth/users/me/deletion-preview"),
    "backend.app.api.v1.backup.instance.start_instance_backup": ("POST", "/api/v1/backup/instance"),
    "backend.app.api.v1.backup.instance.get_instance_backup_options": ("GET", "/api/v1/backup/instance/options"),
    "backend.app.api.v1.backup.instance.get_instance_backup_job": ("GET", "/api/v1/backup/instance/jobs/{job_id}"),
    "backend.app.api.v1.backup.instance.download_instance_backup": ("GET", "/api/v1/backup/instance/jobs/{job_id}/file"),
    "backend.app.api.v1.backup.instance.delete_instance_backup_job": ("DELETE", "/api/v1/backup/instance/jobs/{job_id}"),
    "backend.app.api.v1.backup.panel.start_panel_backup": ("POST", "/api/v1/backup/panel/jobs"),
    "backend.app.api.v1.backup.panel.get_panel_backup_job": ("GET", "/api/v1/backup/panel/jobs/{job_id}"),
    "backend.app.api.v1.backup.panel.download_panel_backup": ("GET", "/api/v1/backup/panel/jobs/{job_id}/file"),
    "backend.app.api.v1.backup.panel.delete_panel_backup_job": ("DELETE", "/api/v1/backup/panel/jobs/{job_id}"),
    "backend.app.api.v1.backup.restore.get_restore_outcome": ("GET", "/api/v1/backup/restore/outcome"),
    "backend.app.api.v1.system.block.get_instance_block": ("GET", "/api/v1/system/block"),
    "backend.app.api.v1.system.instance.get_instance_config": ("GET", "/api/v1/system/instance"),
    "backend.app.api.v1.system.health.health_check": ("GET", "/api/v1/system/health"),
    "backend.app.api.v1.system.health.test_lane_health": ("GET", "/api/v1/system/test-lane-health"),
    "backend.app.api.v1.system.ready.get_readiness": ("GET", "/api/v1/system/ready"),
    "backend.app.api.v1.system.info.get_system_info": ("GET", "/api/v1/system/info"),
    "backend.app.api.v1.system.wake.wake_sync": ("POST", "/api/v1/system/wake-sync"),
    "backend.app.api.v1.panel.get_panel_status": ("GET", "/api/v1/panel/status"),
    # H-62 (contract L3 §5): the hosting panel's restore, ticket only. Allowed by the block so that the credential is
    # checked first (404/401/429/503 of its scope) and only then the route's own 423 instance_blocked: a caller without a
    # valid ticket never learns the block. Red until H-62.
    "backend.app.api.v1.backup.panel_restore.upload_panel_restore_archive": ("PUT", "/api/v1/backup/panel/restore/upload"),
    "backend.app.api.v1.backup.panel_restore.start_panel_restore_check": ("POST", "/api/v1/backup/panel/restore/stage"),
    "backend.app.api.v1.backup.panel_restore.get_panel_restore_check": ("GET", "/api/v1/backup/panel/restore/stage/{stage_id}"),
    "backend.app.api.v1.backup.panel_restore.confirm_panel_restore_check": ("POST", "/api/v1/backup/panel/restore/stage/{stage_id}/confirm"),
    "backend.app.api.v1.backup.panel_restore.restart_panel_restore": ("POST", "/api/v1/backup/panel/restore/restart"),
    "backend.app.api.v1.backup.panel_restore.get_panel_restore_status": ("GET", "/api/v1/backup/panel/restore/status"),
    "backend.app.api.v1.backup.panel_restore.cancel_panel_pending_restore": ("DELETE", "/api/v1/backup/panel/restore/pending"),
}

#: The routes under /api/v1 the block does not reach first: the API documentation (H-55 R5). Our two pages and their two
#: start scripts are APIRoutes registered on the app itself by ``install_api_docs`` (no router dependency reaches them:
#: their first dependency is None), and the schema is FastAPI's ``openapi_url``, a plain Route. They answer on a blocked
#: instance too.
DOCUMENTATION_ROUTES = {
    "/api/v1/docs": "APIRoute GET, first dependency None",
    "/api/v1/docs/swagger-init.js": "APIRoute GET, first dependency None",
    "/api/v1/openapi.json": "Route",
    "/api/v1/redoc": "APIRoute GET, first dependency None",
    "/api/v1/redoc/redoc-init.js": "APIRoute GET, first dependency None",
}
#: Our pages and start scripts, of the documentation routes: served by the endpoints of this module, out of the OpenAPI schema.
API_DOCS_PAGES = ("/api/v1/docs", "/api/v1/docs/swagger-init.js", "/api/v1/redoc", "/api/v1/redoc/redoc-init.js")
API_DOCS_MODULE = "backend.app.api.api_docs"


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
    """A regular user of one test (or the administrator of ``administrator``), with the Cookie header of a session the app in process opened."""

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


async def _delete_if_present(app: FastAPI, monkeypatch: pytest.MonkeyPatch, username: str, password: str = PASSWORD) -> None:
    """Cleanup while the instance is not blocked: sign in by email, which a rename leaves, with ``password``, and delete
    the account, unless it is already gone. After a password reset the caller tries the new password, then the old."""
    with monkeypatch.context() as unblocked:
        _unblock(unblocked)
        login = await _request(app, "POST", "/auth/login", json={"username": f"{username}@example.com", "password": password})
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


async def _promote(username: str) -> None:
    """Make one of this test's users an administrator through user_service, in the lane's database, as
    ``test_users_admin_api.py`` promotes its own on the lane."""
    assert is_test_mode(), "Precondition: test mode, so the promotion reaches the lane's test database"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        done, error = await user_service.set_user_admin(session, username, True)
    assert done, f"Setup: promoting {username} failed: {error}"


@pytest_asyncio.fixture
async def administrator(app, monkeypatch) -> AsyncIterator[Account]:
    """An administrator of this test: registered while not blocked and promoted through user_service (unless the lane had
    no account, which made it the administrator already), then signed in through the app in process. Deleted at
    teardown through the service layer, since the API keeps the last administrator."""
    username, first_account = await _register(app, monkeypatch)
    try:
        if not first_account:
            await _promote(username)
        with monkeypatch.context() as unblocked:
            _unblock(unblocked)
            session = _session_of(await _request(app, "POST", "/auth/login", json=_credentials(username)))
            me = await _request(app, "GET", "/auth/me", session=session)
        assert me.status_code == 200 and me.json()["user"]["is_superuser"] is True, f"Setup: {username} must be signed in as an administrator: {me.status_code} {me.text}"
        yield Account(username, session)
    finally:
        await _delete_administrator_of_this_test(username)


async def _reset_link(username: str) -> str:
    """A password-reset link for one of this test's users, issued by A5's token service in the lane's database and
    committed, as ``test_registration_api.py`` issues one: its token, shown once. Its row goes with the account."""
    assert is_test_mode(), "Precondition: test mode, so the link is written in the lane's test database"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await user_service.get_user_by_username(session, username)
        assert user is not None, f"Setup: {username} must exist to receive a reset link"
        issued = await token_service.issue_token(session, AccountTokenPurpose.PASSWORD_RESET, user_id=user.id)
        await session.commit()
    return issued.token


async def _invitation() -> token_service.IssuedToken:
    """An invitation that grants no role, issued by A5's token service in the lane's database and committed, as
    ``test_registration_api.py`` issues one. No account holds its row: the test deletes it by id (``_delete_token``)."""
    assert is_test_mode(), "Precondition: test mode, so the invitation is written in the lane's test database"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE)
        await session.commit()
    return issued


async def _delete_token(token_id: int) -> None:
    """Cleanup of a link this test issued, by id."""
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(AccountToken).where(AccountToken.id == token_id))
        await session.commit()


def _error_code(response: httpx.Response) -> str | None:
    """``detail.error_code`` of a coded refusal, or None when the body has none."""
    body = response.json()
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("error_code") if isinstance(detail, dict) else None


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

#: Allowed routes whose answers other workstreams own and extend (A, X, B, Z put their public flags in /system/instance):
#: blocked, each answers as the same request does on the instance not blocked, whatever fields are added.
AS_USUAL = ["/auth/me", "/system/info", "/system/ready", "/system/instance"]


def _answer(response: httpx.Response) -> tuple[int, object]:
    """Status and JSON body: what «as usual» compares."""
    return response.status_code, response.json()


async def _usual_then_blocked(app: FastAPI, monkeypatch: pytest.MonkeyPatch, paths: list[str], *, session: dict[str, str] | None = None, method: str = "GET", json: object = None) -> tuple[dict[str, httpx.Response], dict[str, httpx.Response]]:
    """``method`` each path (GET by default; ``json`` its body, if any) from the same session, or the same anonymity,
    with the block off for these requests only, then blocked: ``(usual, blocked)``, by path. The block the test set is on
    again for the second requests, and stays on. Each request is sent twice: only for requests that change nothing."""
    assert instance_blocked(), "Precondition: the test blocks the instance first"
    with monkeypatch.context() as unblocked:
        _unblock(unblocked)
        assert not instance_blocked(), "Barrier: the usual requests run on the instance not blocked"
        usual = {path: await _request(app, method, path, session=session, json=json) for path in paths}
    assert instance_blocked(), "Barrier: the block is on again for the blocked requests, and for the rest of the test"
    blocked = {path: await _request(app, method, path, session=session, json=json) for path in paths}
    return usual, blocked


@pytest.mark.asyncio
async def test_each_allowed_route_answers_a_signed_in_user(app, monkeypatch, account):
    """(a) The routes of the block page, the probes and the version answer a signed-in user as they always do: each the
    same status and body as the same request, with the same session, on the instance not blocked. The block page differs
    in its own two fields only, which report the block; the public configuration shows the managed profile."""
    print_section("Instance block: the allowed routes, signed in")
    lane_token = f"lane-{uuid4().hex}"
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_token)
    _block(monkeypatch)

    usual, blocked = await _usual_then_blocked(app, monkeypatch, [*AS_USUAL, "/system/block"], session=account.session)
    health = await _request(app, "GET", "/system/health", session=account.session)
    lane = await _request(app, "GET", f"/system/test-lane-health?token={lane_token}", session=account.session)

    me, info, block = usual["/auth/me"], usual["/system/info"], usual["/system/block"]
    assert me.status_code == 200 and me.json()["user"]["username"] == account.username, f"Barrier: GET /auth/me answers this session when not blocked: {me.status_code} {me.text}"
    assert info.status_code == 200 and set(info.json()) == set(SystemInfoResponse.model_fields), f"Barrier: GET /system/info answers in full to a session when not blocked: {info.status_code} {info.text}"
    assert block.status_code == 200 and block.json()["blocked"] is False, f"Barrier: GET /system/block reports no block for the usual requests: {block.status_code} {block.text}"
    for path in AS_USUAL:
        assert usual[path].status_code == 200, f"Barrier: GET {path} answers this session when not blocked: {usual[path].status_code} {usual[path].text}"
        assert _answer(blocked[path]) == _answer(usual[path]), f"GET {path} must answer as when not blocked: {usual[path].status_code} {usual[path].text}, blocked {blocked[path].status_code} {blocked[path].text}"
    blocked_page, instance = blocked["/system/block"], blocked["/system/instance"]
    assert _answer(blocked_page) == (200, {**block.json(), "blocked": True, "deletion_date": DELETION_DATE}), f"GET /system/block reports the block and its date, the rest as when not blocked: {blocked_page.status_code} {blocked_page.text}"
    assert instance.json()["profile"] == "managed", f"GET /system/instance shows the managed profile: {instance.status_code} {instance.text}"
    assert (health.status_code, health.json()) == (200, {"status": "ok"}), f"GET /system/health: {health.status_code} {health.text}"
    assert (lane.status_code, lane.json(), lane.headers.get(TEST_LANE_HEADER)) == (200, {"status": "ok"}, lane_token), f"GET /system/test-lane-health with the lane's token: {lane.status_code} {lane.text}"
    print_success("me, info, ready, instance: as when not blocked; block: blocked, with its date; health, test-lane-health: ok")


@pytest.mark.asyncio
async def test_the_allowed_routes_answer_anonymous_callers_as_usual(app, monkeypatch):
    """(a) Allowed is not public: blocked, each allowed route answers a caller without a session as the same request
    does on the instance not blocked, the same status and body. The probes and the version answer anyone, the block
    page and /auth/me still want a session."""
    _block(monkeypatch)

    usual, blocked = await _usual_then_blocked(app, monkeypatch, [*AS_USUAL, "/system/block"])
    health = await _request(app, "GET", "/system/health")
    lane = await _request(app, "GET", f"/system/test-lane-health?token=not-the-lane-{uuid4().hex}")

    statuses = {path: response.status_code for path, response in usual.items()}
    expected = {"/auth/me": 401, "/system/info": 200, "/system/ready": 200, "/system/instance": 200, "/system/block": 401}
    assert statuses == expected, f"Barrier: without a session and not blocked, the probes and the version answer, the block page and /auth/me want a session: {statuses}"
    info = usual["/system/info"]
    assert set(info.json()) == set(SystemInfoPublicResponse.model_fields), f"Barrier: GET /system/info answers the public part only without a session: {info.text}"
    for path, response in usual.items():
        assert _answer(blocked[path]) == _answer(response), f"GET {path} without a session must answer as when not blocked: {response.status_code} {response.text}, blocked {blocked[path].status_code} {blocked[path].text}"
    assert (health.status_code, health.json()) == (200, {"status": "ok"}), f"GET /system/health: {health.status_code} {health.text}"
    assert lane.status_code == 404, f"GET /system/test-lane-health with another token answers its own 404: {lane.status_code} {lane.text}"
    print_success("ready, instance, info (public part): open; block and me: 401; each as when not blocked")


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


# =============================================================================
# (a) Blocked: a link already sent
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", ["password_reset", "invite"], ids=["reset-link", "invitation"])
async def test_reading_a_link_answers_a_caller_without_a_session_as_usual(app, monkeypatch, purpose):
    """(a) POST /auth/tokens/inspect is allowed: blocked, a token no link ever carried gets, without a session, the same
    status and body as on the instance not blocked (200, ``unknown``): neither the 401 a refused route gives a caller
    without a session, nor the 423 of the block."""
    body = {"token": NEVER_ISSUED_TOKEN, "purpose": purpose}
    _block(monkeypatch)

    usual, blocked = await _usual_then_blocked(app, monkeypatch, [INSPECT], method="POST", json=body)

    before, after = usual[INSPECT], blocked[INSPECT]
    assert before.status_code == 200 and (before.json()["status"], before.json()["purpose"]) == ("unknown", purpose), f"Barrier: POST {INSPECT} answers a token never issued as unknown when not blocked: {before.status_code} {before.text}"
    assert after.status_code not in (401, 423), f"POST {INSPECT} must not be refused on a blocked instance: {after.status_code} {after.text}"
    assert _answer(after) == _answer(before), f"POST {INSPECT} without a session must answer as when not blocked: {before.status_code} {before.text}, blocked {after.status_code} {after.text}"
    print_success(f"POST {INSPECT} ({purpose}, never issued): 200 unknown, blocked or not")


@pytest.mark.asyncio
async def test_a_reset_with_a_link_never_issued_is_refused_as_usual(app, monkeypatch):
    """(a) POST /auth/password-reset is allowed: blocked, a token no link ever carried gets, without a session, its usual
    refusal, 400 ``TOKEN_INVALID``, the same status and body as on the instance not blocked: neither 401 nor 423."""
    body = {"token": NEVER_ISSUED_TOKEN, "new_password": NEW_PASSWORD}
    _block(monkeypatch)

    usual, blocked = await _usual_then_blocked(app, monkeypatch, [RESET], method="POST", json=body)

    before, after = usual[RESET], blocked[RESET]
    assert (before.status_code, _error_code(before)) == (400, "TOKEN_INVALID"), f"Barrier: POST {RESET} refuses a token never issued with TOKEN_INVALID when not blocked: {before.status_code} {before.text}"
    assert after.status_code not in (401, 423), f"POST {RESET} must not be refused by the block: {after.status_code} {after.text}"
    assert _answer(after) == _answer(before), f"POST {RESET} without a session must answer as when not blocked: {before.status_code} {before.text}, blocked {after.status_code} {after.text}"
    print_success(f"POST {RESET} (never issued): 400 TOKEN_INVALID, blocked or not")


@pytest.mark.asyncio
async def test_a_reset_link_sent_before_the_block_sets_a_password_that_signs_in(app, monkeypatch):
    """(a) Someone who lost the password, on a blocked instance: the reset link sent before the block reads as valid, for
    their account; spent without a session, it sets the new password (200). The old password no longer signs in, the new
    one does, and its session reaches /auth/me and the block page."""
    print_section("Instance block: a password reset with a link already sent")
    username, administrator = await _regular_user(app, monkeypatch)
    try:
        link = await _reset_link(username)
        _block(monkeypatch)

        inspected = await _request(app, "POST", INSPECT, json={"token": link, "purpose": "password_reset"})
        reset = await _request(app, "POST", RESET, json={"token": link, "new_password": NEW_PASSWORD})
        with_old = await _request(app, "POST", "/auth/login", json=_credentials(username))
        with_new = await _request(app, "POST", "/auth/login", json={"username": username, "password": NEW_PASSWORD})

        assert inspected.status_code == 200 and (inspected.json()["status"], inspected.json()["username"]) == ("valid", username), f"POST {INSPECT} with the reset link while blocked: {inspected.status_code} {inspected.text}"
        assert reset.status_code == 200, f"POST {RESET} with the reset link while blocked: {reset.status_code} {reset.text}"
        assert (with_old.status_code, with_old.json()) == (401, {"detail": "Invalid credentials"}), f"the old password must no longer sign in: {with_old.status_code} {with_old.text}"
        session = _session_of(with_new)
        me = await _request(app, "GET", "/auth/me", session=session)
        block = await _request(app, "GET", "/system/block", session=session)

        assert instance_blocked(), "Barrier: every request of this test ran on the blocked instance"
        assert me.status_code == 200 and me.json()["user"]["username"] == username, f"the new password's session must be this account's: {me.status_code} {me.text}"
        assert (block.status_code, block.json()) == (200, {"blocked": True, "deletion_date": DELETION_DATE, "billing_url": None, "backup_available": False}), f"the new password's session must reach the block page: {block.status_code} {block.text}"
    finally:
        try:
            await _delete_if_present(app, monkeypatch, username, password=NEW_PASSWORD)
        finally:
            await _delete_users_of_this_test(app, monkeypatch, username, administrator)
    print_success("reset link read and spent while blocked: the new password signs in and reaches the block page")


@pytest.mark.asyncio
async def test_an_invitation_reads_as_valid_but_registers_nobody_on_a_blocked_instance(app, monkeypatch):
    """(a) Registration stays out of the list, links or not: blocked, an invitation already sent reads as valid, but
    POST /auth/register with it gets the 401 of get_current_user, as a registration without a session does: no account
    is created, and the invitation is still valid afterwards."""
    username = f"instblock_{uuid4().hex[:12]}"
    invitation = await _invitation()
    registered = None
    try:
        _block(monkeypatch)

        inspected = await _request(app, "POST", INSPECT, json={"token": invitation.token, "purpose": "invite"})
        registered = await _request(app, "POST", "/auth/register", json={**_credentials(username), "email": f"{username}@example.com", "invite_token": invitation.token})
        login = await _request(app, "POST", "/auth/login", json=_credentials(username))
        afterwards = await _request(app, "POST", INSPECT, json={"token": invitation.token, "purpose": "invite"})

        assert inspected.status_code == 200 and inspected.json()["status"] == "valid", f"Barrier: the invitation reads as valid while blocked: {inspected.status_code} {inspected.text}"
        assert (registered.status_code, registered.json()) == (401, {"detail": "Not authenticated"}), f"POST /auth/register with an invitation on a blocked instance must get the 401 of get_current_user: {registered.status_code} {registered.text}"
        assert (login.status_code, login.json()) == (401, {"detail": "Invalid credentials"}), f"the refused registration must create no account: {login.status_code} {login.text}"
        assert afterwards.status_code == 200 and afterwards.json()["status"] == "valid", f"the refused registration must leave the invitation valid: {afterwards.status_code} {afterwards.text}"
    finally:
        try:
            if registered is not None and registered.status_code == 201:
                await _delete_users_of_this_test(app, monkeypatch, *_split_by_role(username, registered.json()["user"]["is_superuser"]))
        finally:
            await _delete_token(invitation.record.id)
    print_success("an invitation while blocked: read as valid, registration 401, no account, still valid")


# =============================================================================
# (a) Blocked: the block page
# =============================================================================


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
    """(a) GET /system/block on a blocked instance: blocked, and the deletion date in ISO, or null when none is given; no
    billing link for a regular user."""
    _block(monkeypatch, deletion_date)

    response = await _request(app, "GET", "/system/block", session=account.session)

    assert (response.status_code, response.json()) == (200, {"blocked": True, "deletion_date": answered, "billing_url": None, "backup_available": False}), f"GET /system/block with {DELETION_DATE_VARIABLE}={deletion_date!r}: {response.status_code} {response.text}"
    InstanceBlockResponse.model_validate(response.json())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("address", "answered"),
    [
        pytest.param(BILLING_ADDRESS, BILLING_LINK, id="https-one-trailing-slash-removed"),
        pytest.param(None, None, id="unset"),
        pytest.param(INVALID_BILLING_ADDRESS, None, id="not-http"),
    ],
)
async def test_the_block_page_gives_an_administrator_the_billing_link(app, monkeypatch, administrator, address, answered):
    """(a) GET /system/block on a blocked instance, to an administrator: ``billing_url`` is ``LIBREFOLIO_BILLING_URL``
    with one trailing slash removed, and null when the variable is unset or not an http(s) address."""
    if address is None:
        monkeypatch.delenv(BILLING_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(BILLING_VARIABLE, address)
    _block(monkeypatch)

    response = await _request(app, "GET", "/system/block", session=administrator.session)

    assert (response.status_code, response.json()) == (200, {"blocked": True, "deletion_date": DELETION_DATE, "billing_url": answered, "backup_available": True}), f"GET /system/block to an administrator with {BILLING_VARIABLE}={address!r}: {response.status_code} {response.text}"
    InstanceBlockResponse.model_validate(response.json())
    print_success(f"{BILLING_VARIABLE}={address!r}: an administrator gets billing_url={answered!r}")


@pytest.mark.asyncio
async def test_the_block_page_gives_a_regular_user_no_billing_link(app, monkeypatch, account):
    """(a) The same variable, a regular user: GET /system/block on a blocked instance answers ``billing_url`` null."""
    monkeypatch.setenv(BILLING_VARIABLE, BILLING_ADDRESS)
    _block(monkeypatch)
    assert billing_link() == BILLING_LINK, "Barrier: the variable is in force in this process, an administrator would get the link"

    response = await _request(app, "GET", "/system/block", session=account.session)

    assert (response.status_code, response.json()) == (200, {"blocked": True, "deletion_date": DELETION_DATE, "billing_url": None, "backup_available": False}), f"GET /system/block to a regular user with {BILLING_VARIABLE} set: {response.status_code} {response.text}"
    print_success("a regular user: billing_url null, whatever the variable says")


# =============================================================================
# (a) Blocked: the full backup, for administrators only (decision 12)
# =============================================================================

#: The answer of a route for administrators only to a regular user, whole: the 403 of ``require_admin``
#: (``api/v1/settings.py``).
ADMIN_REQUIRED_ANSWER = {"detail": "Admin access required"}


@dataclass(frozen=True)
class FakeBackupService:
    """The backup service of the full backup's routes, replaced in this process: one job, done at once, whose archive is
    a small file of the test. Every call is recorded with its name and its argument: the origin, or the job id asked."""

    job_id: str
    archive: Path
    calls: list[tuple[str, str]]


def _replace_the_backup_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, origin: str = "ui") -> FakeBackupService:
    """Replace ``start_backup``, ``get_job``, ``job_archive`` and ``delete_job`` of ``jobs``, the module the routes of
    ``api/v1/backup/instance.py`` and ``panel.py`` call through ``job_views.py`` (``jobs.<name>(...)``), in this process
    only: no backup runs on the lane's data directory, whose run lock other suites of the lane take. Any job id but the
    fake's is unknown, as to the service. The fake's job is of ``origin``: ``ui``, an administrator's, unless a test of
    the hosting panel asks for ``panel``, the only origin the panel's routes serve (B8)."""
    assert backup_instance.job_views.jobs is jobs and backup_panel.job_views.jobs is jobs, "Precondition: the routes of instance.py and panel.py call the very module replaced here, through job_views.py, so no real backup can run"
    job_id = uuid4().hex
    created_at = datetime(2026, 10, 15, 10, 15, tzinfo=UTC)
    archive = tmp_path / jobs.archive_name(created_at)
    archive.write_bytes(job_id.encode() + bytes(range(256)))
    size = archive.stat().st_size
    first = jobs.BackupJob(job_id=job_id, origin=origin, status="running", phase="preparing", done_bytes=0, total_bytes=0, created_at=created_at)
    done = jobs.BackupJob(job_id=job_id, origin=origin, status="done", phase=None, done_bytes=size, total_bytes=size, created_at=created_at, finished_at=datetime(2026, 10, 15, 10, 16, tzinfo=UTC), file_name=archive.name, file_size=size)
    fake = FakeBackupService(job_id, archive, [])

    def record_job_call(name: str, asked: str) -> None:
        fake.calls.append((name, asked))
        if asked != job_id:
            raise jobs.BackupJobNotFoundError("No such backup job")

    def start_backup(*, origin: str = "ui", data_dir: Path | None = None, password: str | None = None) -> jobs.BackupJob:
        fake.calls.append(("start_backup", origin))
        return first

    def get_job(asked: str, *, data_dir: Path | None = None) -> jobs.BackupJob:
        record_job_call("get_job", asked)
        return done

    def job_archive(asked: str, *, data_dir: Path | None = None) -> tuple[Path, str]:
        record_job_call("job_archive", asked)
        return archive, archive.name

    def delete_job(asked: str, *, data_dir: Path | None = None) -> None:
        record_job_call("delete_job", asked)

    for name, replacement in (("start_backup", start_backup), ("get_job", get_job), ("job_archive", job_archive), ("delete_job", delete_job)):
        monkeypatch.setattr(jobs, name, replacement)
    return fake


def _backup_routes(job_id: str) -> list[tuple[str, str]]:
    """The four routes of the full backup (``api/v1/backup/instance.py``) for one job: start, poll, download, delete."""
    return [("POST", "/backup/instance"), ("GET", f"/backup/instance/jobs/{job_id}"), ("GET", f"/backup/instance/jobs/{job_id}/file"), ("DELETE", f"/backup/instance/jobs/{job_id}")]


def _status_and_body(response: httpx.Response) -> tuple[int, object]:
    """Status and body: the JSON of a JSON answer, the first bytes of any other (an archive), so a red always reads."""
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, response.json()
    return response.status_code, response.content[:64]


@pytest.mark.asyncio
async def test_an_administrator_keeps_the_full_backup_on_a_blocked_instance(app, monkeypatch, administrator, tmp_path):
    """(a) Decision 12: on a blocked instance an administrator can still take the data away. The block refuses the
    administrator elsewhere, and the four routes of the full backup answer as on any instance: start 202 with the job,
    poll 200 done, download 200 with the archive's very bytes, delete 204, each reaching the backup service. The block
    page tells the administrator that the backup is available."""
    print_section("Instance block: the full backup of an administrator")
    fake = _replace_the_backup_service(monkeypatch, tmp_path)
    monkeypatch.delenv(BILLING_VARIABLE, raising=False)
    _block(monkeypatch)

    refused = await _request(app, "GET", "/brokers", session=administrator.session)
    started, polled, downloaded, deleted = [await _request(app, method, path, session=administrator.session) for method, path in _backup_routes(fake.job_id)]
    block = await _request(app, "GET", "/system/block", session=administrator.session)

    assert (refused.status_code, refused.json()) == (423, BLOCKED_ANSWER), f"Barrier: the block refuses this administrator outside the list, GET /brokers answers 423: {refused.status_code} {refused.text}"
    assert started.status_code == 202 and started.json()["job_id"] == fake.job_id, f"POST /backup/instance on a blocked instance: 202 with the job started: {_status_and_body(started)}"
    assert polled.status_code == 200 and (polled.json()["job_id"], polled.json()["status"]) == (fake.job_id, "done"), f"GET /backup/instance/jobs/{{job_id}} on a blocked instance: 200, done: {_status_and_body(polled)}"
    assert (downloaded.status_code, downloaded.content) == (200, fake.archive.read_bytes()), f"GET /backup/instance/jobs/{{job_id}}/file on a blocked instance: 200 with exactly the archive's bytes: {_status_and_body(downloaded)}"
    assert deleted.status_code == 204, f"DELETE /backup/instance/jobs/{{job_id}} on a blocked instance: 204: {_status_and_body(deleted)}"
    assert fake.calls == [("start_backup", "ui"), ("get_job", fake.job_id), ("job_archive", fake.job_id), ("delete_job", fake.job_id)], f"each route must reach the backup service, with the job's id: {fake.calls}"
    assert (block.status_code, block.json()) == (200, {"blocked": True, "deletion_date": DELETION_DATE, "billing_url": None, "backup_available": True}), f"GET /system/block for an administrator: {block.status_code} {block.text}"
    print_success("blocked: start 202, poll 200 done, download 200 with the archive's bytes, delete 204; the block page offers the backup")


@pytest.mark.asyncio
async def test_a_regular_user_meets_the_admin_check_of_the_backup_not_the_block(app, monkeypatch, account, tmp_path):
    """(a) Allowed is not open to all: on a blocked instance the four routes of the full backup refuse a regular user as
    on any instance, each with the 403 of require_admin, never the 423 of the block; the backup service is not
    reached."""
    fake = _replace_the_backup_service(monkeypatch, tmp_path)
    _block(monkeypatch)

    refused = await _request(app, "GET", "/brokers", session=account.session)
    answers = {f"{method} {path}": _status_and_body(await _request(app, method, path, session=account.session)) for method, path in _backup_routes(fake.job_id)}

    assert (refused.status_code, refused.json()) == (423, BLOCKED_ANSWER), f"Barrier: the block refuses this user outside the list, GET /brokers answers 423: {refused.status_code} {refused.text}"
    assert answers == dict.fromkeys(answers, (403, ADMIN_REQUIRED_ANSWER)), f"each route of the full backup must refuse a regular user with the 403 of require_admin, never the 423 of the block: {answers}"
    assert fake.calls == [], f"the backup service must never be reached for a regular user: {fake.calls}"
    print_success("blocked: start, poll, download, delete each answer a regular user 403 Admin access required, never 423; the service untouched")


# The same full backup for the hosting panel (B8, ``api/v1/backup/panel.py``): its four routes are allowed on a blocked
# instance, since that is when the provider hands the data back, and answer on their own terms only. No token set: 404,
# as a path that does not exist. A token set: its own 401 without it, whatever else the request carries, a session
# included; with it, the panel's own jobs. Its callers carry no session, so the barrier of these cases is the anonymous
# one: a public route outside the list (GET /utilities/sectors) answers 200 with the block off for that request, then
# the 401 of get_current_user with the block on.

#: The variable of the hosting panel's token (``config/backup.py``); its ``_FILE`` form is cleared with it.
PANEL_TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
#: The panel's answer without its token, whole: a 401 of its own, so neither the 401 of get_current_user nor the 423 of
#: the block can pass for it.
PANEL_UNAUTHORIZED_ANSWER = {"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}
#: The panel's answer while no token is set, whole: the answer of a path that does not exist.
PANEL_OFF_ANSWER = {"detail": "Not Found"}
#: A public route outside the list: 200 to anyone when not blocked, the 401 of get_current_user while blocked.
PUBLIC_BARRIER = "/utilities/sectors"


def _panel_token(monkeypatch: pytest.MonkeyPatch, token: str | None) -> None:
    """The hosting panel's token, in this process only: ``token``, or none at all (neither the variable nor its ``_FILE``,
    so nothing comes from the runner's environment)."""
    monkeypatch.delenv(PANEL_TOKEN_VARIABLE, raising=False)
    monkeypatch.delenv(f"{PANEL_TOKEN_VARIABLE}_FILE", raising=False)
    if token is not None:
        monkeypatch.setenv(PANEL_TOKEN_VARIABLE, token)


def _panel_routes(job_id: str) -> list[tuple[str, str]]:
    """The four routes of the hosting panel (``api/v1/backup/panel.py``) for one job: start, poll, download, delete."""
    return [("POST", "/backup/panel/jobs"), ("GET", f"/backup/panel/jobs/{job_id}"), ("GET", f"/backup/panel/jobs/{job_id}/file"), ("DELETE", f"/backup/panel/jobs/{job_id}")]


async def _panel_request(app: FastAPI, method: str, path: str, *, authorization: str | None = None, session: dict[str, str] | None = None) -> httpx.Response:
    """``method`` ``/api/v1<path>`` on the app in process, as a hosting panel sends it: ``Authorization`` only when given,
    a session cookie only in ``session``."""
    headers = {**(session or {}), **({} if authorization is None else {"Authorization": authorization})}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", headers=headers, timeout=TIMEOUT)


async def _blocked_for_anonymous_callers(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> tuple[int, int, object]:
    """The barrier of the panel's cases: ``PUBLIC_BARRIER`` without a session, with the block off for that request only,
    then with the block on. ``(usual status, blocked status, blocked body)``: (200, 401, Not authenticated) proves the
    block is on."""
    usual, blocked = await _usual_then_blocked(app, monkeypatch, [PUBLIC_BARRIER])
    return usual[PUBLIC_BARRIER].status_code, blocked[PUBLIC_BARRIER].status_code, blocked[PUBLIC_BARRIER].json()


@pytest.mark.asyncio
async def test_the_panel_routes_answer_404_on_a_blocked_instance_while_no_token_is_set(app, monkeypatch, tmp_path):
    """(a) B8: with no token set, each route of the hosting panel answers a caller without a session 404 Not Found, as a
    path that does not exist, with or without a Bearer token: never the archive, never the 401 of the block. The backup
    service is never reached."""
    print_section("Instance block: the hosting panel's backup")
    fake = _replace_the_backup_service(monkeypatch, tmp_path, origin="panel")
    _panel_token(monkeypatch, None)
    _block(monkeypatch)

    barrier = await _blocked_for_anonymous_callers(app, monkeypatch)
    requests = [("no Authorization", None), ("a Bearer token", f"Bearer {secrets.token_hex(32)}")]
    answers = {f"{method} {path}, {label}": _status_and_body(await _panel_request(app, method, path, authorization=authorization)) for method, path in _panel_routes(fake.job_id) for label, authorization in requests}

    assert barrier == (200, 401, {"detail": "Not authenticated"}), f"Barrier: the block refuses an anonymous caller outside the list, GET {PUBLIC_BARRIER} answers 200 when not blocked and 401 when blocked: {barrier}"
    assert answers == dict.fromkeys(answers, (404, PANEL_OFF_ANSWER)), f"with no token set, each route of the panel must answer 404 Not Found on a blocked instance, never the archive: {answers}"
    assert fake.calls == [], f"the backup service must never be reached while the panel's routes are off: {fake.calls}"
    print_success("blocked, no token set: the panel's four routes answer 404 Not Found; the service untouched")


@pytest.mark.asyncio
async def test_the_panel_routes_answer_their_own_401_on_a_blocked_instance_without_the_token(app, monkeypatch, tmp_path):
    """(a) B8: a token set, each route of the hosting panel answers a caller without a session and without the token, or
    with another one, the panel's own 401 (``backup_panel_unauthorized``, ``WWW-Authenticate: Bearer``), whole, so neither
    the 401 of get_current_user nor the 423 of the block passes for it: never the archive. The service is never
    reached."""
    fake = _replace_the_backup_service(monkeypatch, tmp_path, origin="panel")
    _panel_token(monkeypatch, secrets.token_hex(32))
    _block(monkeypatch)

    barrier = await _blocked_for_anonymous_callers(app, monkeypatch)
    requests = [("no Authorization", None), ("another token", f"Bearer {secrets.token_hex(32)}")]
    responses = {f"{method} {path}, {label}": await _panel_request(app, method, path, authorization=authorization) for method, path in _panel_routes(fake.job_id) for label, authorization in requests}

    answers = {name: _status_and_body(response) for name, response in responses.items()}
    challenges = {name: response.headers.get("www-authenticate") for name, response in responses.items()}
    assert barrier == (200, 401, {"detail": "Not authenticated"}), f"Barrier: the block refuses an anonymous caller outside the list, GET {PUBLIC_BARRIER} answers 200 when not blocked and 401 when blocked: {barrier}"
    assert answers == dict.fromkeys(answers, (401, PANEL_UNAUTHORIZED_ANSWER)), f"without the token each route of the panel must answer its own 401 on a blocked instance, never the archive: {answers}"
    assert challenges == dict.fromkeys(challenges, "Bearer"), f"each 401 of the panel asks for a Bearer token: {challenges}"
    assert fake.calls == [], f"the backup service must never be reached without the token: {fake.calls}"
    print_success("blocked, token set: the panel's four routes answer their own 401 without it; the service untouched")


@pytest.mark.asyncio
async def test_the_hosting_panel_takes_the_backup_of_a_blocked_instance_with_its_token(app, monkeypatch, tmp_path):
    """(a) B8, decision 12: on a blocked instance the hosting panel, with its token and no session, starts a backup (202
    with the job), polls it (200, done), downloads its archive (200, its very bytes) and deletes it (204); each route
    reads the job first and asks the service for the panel's jobs only."""
    fake = _replace_the_backup_service(monkeypatch, tmp_path, origin="panel")
    token = secrets.token_hex(32)
    _panel_token(monkeypatch, token)
    _block(monkeypatch)

    barrier = await _blocked_for_anonymous_callers(app, monkeypatch)
    started, polled, downloaded, deleted = [await _panel_request(app, method, path, authorization=f"Bearer {token}") for method, path in _panel_routes(fake.job_id)]

    assert barrier == (200, 401, {"detail": "Not authenticated"}), f"Barrier: the block refuses an anonymous caller outside the list, GET {PUBLIC_BARRIER} answers 200 when not blocked and 401 when blocked: {barrier}"
    assert started.status_code == 202 and started.json()["job_id"] == fake.job_id, f"POST /backup/panel/jobs with the token on a blocked instance: 202 with the job started: {_status_and_body(started)}"
    assert polled.status_code == 200 and (polled.json()["job_id"], polled.json()["status"]) == (fake.job_id, "done"), f"GET /backup/panel/jobs/{{job_id}} with the token on a blocked instance: 200, done: {_status_and_body(polled)}"
    assert (downloaded.status_code, downloaded.content) == (200, fake.archive.read_bytes()), f"GET /backup/panel/jobs/{{job_id}}/file with the token on a blocked instance: 200 with exactly the archive's bytes: {_status_and_body(downloaded)}"
    assert deleted.status_code == 204, f"DELETE /backup/panel/jobs/{{job_id}} with the token on a blocked instance: 204: {_status_and_body(deleted)}"
    job_id = fake.job_id
    assert fake.calls == [("start_backup", "panel"), ("get_job", job_id), ("get_job", job_id), ("job_archive", job_id), ("get_job", job_id), ("delete_job", job_id)], f"start asks for a run of the panel; poll, download and delete read the job first: {fake.calls}"
    print_success("blocked, with the token: start 202, poll 200 done, download 200 with the archive's bytes, delete 204, the panel's jobs only")


@pytest.mark.asyncio
async def test_a_session_never_stands_in_for_the_panel_token_on_a_blocked_instance(app, monkeypatch, administrator, tmp_path):
    """(a) B8: the panel's routes want its token, never a session. A token set, an administrator's session without it gets
    the panel's own 401 from each of the four routes, never the archive; the service is never reached."""
    fake = _replace_the_backup_service(monkeypatch, tmp_path, origin="panel")
    _panel_token(monkeypatch, secrets.token_hex(32))
    _block(monkeypatch)

    refused = await _request(app, "GET", "/brokers", session=administrator.session)
    answers = {f"{method} {path}": _status_and_body(await _panel_request(app, method, path, session=administrator.session)) for method, path in _panel_routes(fake.job_id)}

    assert (refused.status_code, refused.json()) == (423, BLOCKED_ANSWER), f"Barrier: the block refuses this administrator's session outside the list, GET /brokers answers 423: {refused.status_code} {refused.text}"
    assert answers == dict.fromkeys(answers, (401, PANEL_UNAUTHORIZED_ANSWER)), f"an administrator's session must never stand in for the panel's token: each route answers the panel's 401: {answers}"
    assert fake.calls == [], f"the backup service must never be reached with a session in place of the token: {fake.calls}"
    print_success("blocked: an administrator's session without the token gets the panel's 401 on its four routes; the service untouched")


# =============================================================================
# (b) Not blocked
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "", "  ", "false", "0", "no", "OFF"], ids=["unset", "empty", "blank", "false", "0", "no", "OFF"])
async def test_routes_answer_as_before_when_not_blocked(app, monkeypatch, account, value):
    """(b) Unset, blank or a value that does not block: reads answer, invalid bodies are 422, anonymous callers 401; the
    block page reports no block, and no billing link to a regular user."""
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
    assert (block.status_code, block.json()) == (200, {"blocked": False, "deletion_date": None, "billing_url": None, "backup_available": False}), f"GET /system/block: {block.status_code} {block.text}"
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
    """(b) Live: the lane's backend answers the block page, not blocked, without a date or a billing link (a regular
    user), and only to a session."""
    async with httpx.AsyncClient() as client:
        signed_in = await client.get(f"{API_BASE}/system/block", headers=live_session, timeout=TIMEOUT)
    async with httpx.AsyncClient() as client:
        anonymous = await client.get(f"{API_BASE}/system/block", timeout=TIMEOUT)

    assert (signed_in.status_code, signed_in.json()) == (200, {"blocked": False, "deletion_date": None, "billing_url": None, "backup_available": False}), f"GET /system/block on the lane's backend: {signed_in.status_code} {signed_in.text}"
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
    assert flagged == DOCUMENTATION_ROUTES, f"The documentation routes under /api/v1 changed: expected {DOCUMENTATION_ROUTES}, found {flagged}"
    print_success(f"{len(walked)} API paths under {API_V1_PREFIX}, each resolving refuse_when_blocked first; outside: the {len(DOCUMENTATION_ROUTES)} documentation routes")


def test_the_documentation_pages_outside_the_block_are_ours_and_out_of_the_schema(app):
    """(c) The pages and start scripts that stay out of the block are the ones ``install_api_docs`` registers (APIRoutes whose endpoints
    live in ``backend/app/api/api_docs.py``, answering GET, out of the schema), not a FastAPI page and not a route of
    another module: an endpoint that moved elsewhere would slip past the pin above under the same reason."""
    contexts = {_path_of(context): context for context in iter_route_contexts(app.routes) if _path_of(context) in API_DOCS_PAGES}

    assert sorted(contexts) == sorted(API_DOCS_PAGES), f"the app must serve exactly the pages {API_DOCS_PAGES}: found {sorted(contexts)}"
    for path, context in contexts.items():
        route = context.original_route
        assert isinstance(route, APIRoute), f"{path} is a {type(route).__name__}, wanted an APIRoute of install_api_docs"
        assert context.endpoint.__module__ == API_DOCS_MODULE, f"{path} is served by {_endpoint_name(context.endpoint)}, wanted an endpoint of {API_DOCS_MODULE}"
        assert set(context.methods or ()) == {"GET"}, f"{path} answers {sorted(context.methods or ())}, wanted GET only"
        assert route.include_in_schema is False, f"{path} is in the OpenAPI schema"
    assert not set(app.openapi()["paths"]) & set(API_DOCS_PAGES), "the OpenAPI schema lists the documentation pages"


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
    """(d) GET /api/v1/system/block: a System route whose 200 is InstanceBlockResponse, blocked required, the date and the
    billing link optional."""
    document = app.openapi()
    operation = document["paths"][f"{API_V1_PREFIX}/system/block"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert schema == {"$ref": "#/components/schemas/InstanceBlockResponse"}, f"the 200 of GET /system/block must be InstanceBlockResponse: {schema}"
    assert operation["tags"] == ["System"], f"GET /system/block belongs to the System tag: {operation['tags']}"
    component = document["components"]["schemas"]["InstanceBlockResponse"]
    properties = component["properties"]
    assert set(properties) == {"blocked", "deletion_date", "billing_url", "backup_available"} and component.get("required") == ["blocked", "backup_available"], f"InstanceBlockResponse: {component}"
    assert properties["blocked"]["type"] == "boolean", f"blocked: {properties['blocked']}"
    variants = properties["deletion_date"].get("anyOf", [])
    assert {"type": "string", "format": "date"} in variants and {"type": "null"} in variants, f"deletion_date is an ISO date or null: {properties['deletion_date']}"
    billing_variants = properties["billing_url"].get("anyOf", [])
    assert {"type": "string"} in billing_variants and {"type": "null"} in billing_variants, f"billing_url is an address or null: {properties['billing_url']}"

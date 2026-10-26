"""
The state «over the limit» on the API (workstream A, lot A5-7). Selector: ``services user-limit-api``.

Under test: ``backend/app/api/v1/user_limit.py`` (``refuse_when_over_limit``, a dependency of the ``/api/v1`` router, and
its two lists) and the two routes of ``backend/app/api/v1/users.py``: ``GET /users/over-limit`` and
``POST /users/over-limit/resolve``. Analysis: ``ondata5/A-5-7-analisi-oltre-il-limite.md``.

(a) The guard. While the active accounts outnumber ``LIBREFOLIO_MAX_USERS``, a signed-in ordinary user meets
    ``423 {"detail": {"code": "user_limit_exceeded", ...}}`` on every route but a short list (signing in and out, who is
    signed in, the public configuration, the probes, a link already sent, one's own account's deletion, the hosting
    panel's routes, the outcome of a restore); an administrator also reaches the choice and the full backup. Anyone without
    a session gets the 401 of any protected route; an instance not over the limit changes no answer, and neither does a limit
    that cannot be read. The order of the guards: block, awaiting restore, restore interrupted, THEN this one.
(b) The lists. They are fixed by name: the allowed routes are those of the block's list but for the five of the
    administrator's backup, which the administrator alone keeps.
(c) The routes. ``GET /users/over-limit`` and ``POST /users/over-limit/resolve``: exact keys, the refusals with their codes
    and statuses (409 ``NOT_OVER_LIMIT``; 422 ``UNKNOWN_USER`` / ``TOO_MANY_KEPT`` / ``PROTECTED_MISSING`` /
    ``NO_ADMIN_KEPT``), 403 for a user who is not an administrator when the instance is not over the limit. After the
    resolution the kept accounts enter, the deactivated ones meet the 401 of a disabled account.

The app of ``backend/app/main.py`` runs in process through ``httpx.ASGITransport`` on a PRIVATE database (the session
dependency is overridden): the resolution deactivates accounts, and the lane's database is shared. No server, no network.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import instance_block
from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.test_scripts.test_utils import print_section

LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
PASSWORD = "UserLimitPass123!"
TIMEOUT = 30
INHERITED_VARIABLES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_REGISTRATION", LIMIT_VARIABLE, "LIBREFOLIO_BLOCKED", "LIBREFOLIO_PROFILE", "LIBREFOLIO_ADMIN_EMAIL", "LIBREFOLIO_AWAIT_RESTORE")

#: The answer of a refused route to a signed-in ordinary user, whole.
OVER_LIMIT_CODE = "user_limit_exceeded"

#: The five routes of the administrator's full backup: kept for the administrator alone while the instance is over the limit.
ADMIN_BACKUP = {
    "backend.app.api.v1.backup.instance.start_instance_backup",
    "backend.app.api.v1.backup.instance.get_instance_backup_options",
    "backend.app.api.v1.backup.instance.get_instance_backup_job",
    "backend.app.api.v1.backup.instance.download_instance_backup",
    "backend.app.api.v1.backup.instance.delete_instance_backup_job",
}


def _name(function: Any) -> str:
    return f"{function.__module__}.{function.__name__}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_ADMIN_") or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def private_owner_knowledge(monkeypatch: pytest.MonkeyPatch) -> None:
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'limit-api.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def app(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    """The server's own app, in this process, whose every request reads and writes the private database."""
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixtures that need it

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    monkeypatch.setitem(main_app.dependency_overrides, get_session_generator, private_session)
    yield main_app


# =============================================================================
# HELPERS
# =============================================================================


async def _add(engine: AsyncEngine, username: str, *, admin: bool = False, active: bool = True, owner: bool = False) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@zq-limit-api.example.com", hashed_password=auth_service.hash_password(PASSWORD), is_active=active, is_superuser=admin)
        if owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user.id


async def _five(engine: AsyncEngine) -> dict[str, int]:
    return {
        "anna": await _add(engine, "anna", admin=True),
        "bruno": await _add(engine, "bruno", admin=True),
        "carla": await _add(engine, "carla"),
        "dario": await _add(engine, "dario"),
        "elena": await _add(engine, "elena"),
    }


async def _request(app: FastAPI, method: str, path: str, *, session: dict[str, str] | None = None, json: object = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", headers=session or {}, json=json, timeout=TIMEOUT)


async def _sign_in(app: FastAPI, username: str) -> dict[str, str]:
    login = await _request(app, "POST", "/auth/login", json={"username": username, "password": PASSWORD})
    token = login.cookies.get(SESSION_COOKIE_NAME)
    assert login.status_code == 200 and token, f"Setup: the login of {username} must open a session: {login.status_code} {login.text}"
    return {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}


def _limit(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, value)


def _code(response: httpx.Response) -> object:
    body = response.json()
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("code") or detail.get("error_code") if isinstance(detail, dict) else None


# =============================================================================
# (a) THE GUARD
# =============================================================================


@pytest.mark.asyncio
async def test_a_signed_in_ordinary_user_meets_423_while_the_instance_is_over_the_limit(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-100: five active accounts and a limit of 3: an ordinary user, signed in before the limit dropped, gets 423 ``user_limit_exceeded`` with exactly ``{"detail": {"code", "message"}}`` on routes that read and on routes that write, before the body is validated."""
    print_section("A5-7-100: 423 for an ordinary user")
    await _five(engine)
    session = await _sign_in(app, "dario")
    _limit(monkeypatch, "3")

    for method, path, body in (("GET", "/brokers", None), ("GET", "/settings/user", None), ("POST", "/brokers", {"not": "a broker"}), ("GET", "/users/search", None)):
        reply = await _request(app, method, path, session=session, json=body)
        assert reply.status_code == 423, f"{method} {path}: {reply.status_code} {reply.text}"
        assert set(reply.json()) == {"detail"} and set(reply.json()["detail"]) == {"code", "message"}
        assert reply.json()["detail"]["code"] == OVER_LIMIT_CODE


@pytest.mark.asyncio
async def test_the_allowed_routes_answer_as_usual(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-101: while over the limit an ordinary user still signs in (so the page can say what is going on), reads who they are, reads the public configuration and the probes."""
    await _five(engine)
    _limit(monkeypatch, "3")

    session = await _sign_in(app, "elena")
    for path in ("/auth/me", "/system/instance", "/system/health", "/system/info"):
        reply = await _request(app, "GET", path, session=session)
        assert reply.status_code == 200, f"{path}: {reply.status_code} {reply.text}"
    logout = await _request(app, "POST", "/auth/logout", session=session)
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_anyone_without_a_session_gets_the_usual_401(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-102: a caller without a session learns nothing of the state: the 401 of a protected route, as when the instance is not over the limit."""
    await _five(engine)
    _limit(monkeypatch, None)
    usual = await _request(app, "GET", "/brokers")
    _limit(monkeypatch, "3")
    over = await _request(app, "GET", "/brokers")

    assert usual.status_code == over.status_code == 401
    assert usual.json() == over.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "5", "6", "abc", "0"], ids=["no-limit", "active-equals-limit", "room-left", "unreadable", "zero"])
async def test_an_instance_not_over_the_limit_changes_no_answer(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """A5-7-103: no limit, active = limit, room left, and a limit that cannot be read (never a state: a typo must not lock everybody out): an ordinary user reads their brokers as always."""
    await _five(engine)
    session = await _sign_in(app, "carla")
    _limit(monkeypatch, value)

    assert (await _request(app, "GET", "/brokers", session=session)).status_code == 200


@pytest.mark.asyncio
async def test_an_administrator_reaches_the_choice_and_the_backup_but_nothing_else(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-104: the administrator over the limit reaches ``GET /users/over-limit`` and the backup options; every other route is 423. An ordinary user on the same two routes gets the 423 too (they are not in their list)."""
    await _five(engine)
    admin = await _sign_in(app, "anna")
    ordinary = await _sign_in(app, "dario")
    _limit(monkeypatch, "3")

    assert (await _request(app, "GET", "/users/over-limit", session=admin)).status_code == 200
    assert (await _request(app, "GET", "/backup/instance/options", session=admin)).status_code != 423
    assert (await _request(app, "GET", "/brokers", session=admin)).status_code == 423
    assert (await _request(app, "GET", "/users", session=admin)).status_code == 423
    for path in ("/users/over-limit", "/backup/instance/options"):
        reply = await _request(app, "GET", path, session=ordinary)
        assert reply.status_code == 423 and _code(reply) == OVER_LIMIT_CODE, f"{path}: {reply.status_code}"


@pytest.mark.asyncio
async def test_the_blocked_instance_wins(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-105: the guards in order. A blocked instance that is also over the limit answers ``instance_blocked``."""
    await _five(engine)
    session = await _sign_in(app, "dario")
    _limit(monkeypatch, "3")
    monkeypatch.setenv("LIBREFOLIO_BLOCKED", "true")

    reply = await _request(app, "GET", "/brokers", session=session)

    assert reply.status_code == 423 and _code(reply) == "instance_blocked"


@pytest.mark.asyncio
async def test_a_restore_that_serves_no_data_wins_over_the_limit(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-106 (B's revision): the owner of a restored instance still without an account (the restore guard of H, ``instance_restore_interrupted``) AND the accounts over the limit: the restore's guard answers, because nobody can choose yet."""
    await _five(engine)
    session = await _sign_in(app, "anna")
    _limit(monkeypatch, "3")

    async def nothing() -> None:
        return None

    monkeypatch.setattr(instance_block, "refresh_restore_state", nothing)
    monkeypatch.setattr(instance_block, "restore_interrupted", lambda: True)

    reply = await _request(app, "GET", "/users/over-limit", session=session)

    assert reply.status_code == 423 and _code(reply) == instance_block.INSTANCE_RESTORE_INTERRUPTED_CODE


@pytest.mark.asyncio
async def test_the_guard_is_the_fourth_dependency_of_the_router() -> None:
    """A5-7-107: ``refuse_when_over_limit`` follows the block, the awaiting-restore mode and the interrupted restore, in this order, in the dependencies of the ``/api/v1`` router."""
    from backend.app.api.v1 import user_limit  # noqa: PLC0415
    from backend.app.api.v1.router import router  # noqa: PLC0415

    names = [dependency.dependency.__name__ for dependency in router.dependencies]
    assert names[:4] == ["refuse_when_blocked", "refuse_when_awaiting_restore", "refuse_when_restore_interrupted", user_limit.refuse_when_over_limit.__name__]


# =============================================================================
# (b) THE LISTS
# =============================================================================


def test_the_lists_are_the_block_list_less_the_administrators_backup() -> None:
    """A5-7-110: ``ALLOWED_WHEN_OVER_LIMIT`` is ``ALLOWED_WHEN_BLOCKED`` less the five routes of the administrator's backup, which ``ALLOWED_WHEN_OVER_LIMIT_ADMIN`` holds with the two routes of the choice. The restore of the app is in neither."""
    from backend.app.api.v1 import user_limit  # noqa: PLC0415
    from backend.app.api.v1.users import list_over_limit, resolve_over_limit  # noqa: PLC0415

    blocked = {_name(function) for function in instance_block.ALLOWED_WHEN_BLOCKED}
    everyone = {_name(function) for function in user_limit.ALLOWED_WHEN_OVER_LIMIT}
    administrators = {_name(function) for function in user_limit.ALLOWED_WHEN_OVER_LIMIT_ADMIN}

    assert everyone == blocked - ADMIN_BACKUP
    assert administrators == ADMIN_BACKUP | {_name(list_over_limit), _name(resolve_over_limit)}
    assert not any("restore" in name and "panel" not in name and "outcome" not in name for name in everyone | administrators), "the app's own restore is in neither list"


# =============================================================================
# (c) THE ROUTES
# =============================================================================


@pytest.mark.asyncio
async def test_the_choice_has_exactly_these_keys(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-120: ``GET /users/over-limit``: the keys of the page, no password, no hash, no token; the chooser is ``you``."""
    ids = await _five(engine)
    admin = await _sign_in(app, "bruno")
    _limit(monkeypatch, "3")

    reply = await _request(app, "GET", "/users/over-limit", session=admin)

    assert reply.status_code == 200
    body = reply.json()
    assert set(body) == {"over_limit", "active", "max_users", "live_invites", "waiting_accounts", "max_keep", "users"}
    assert (body["over_limit"], body["active"], body["max_users"], body["max_keep"]) == (True, 5, 3, 3)
    assert [row["id"] for row in body["users"]] == list(ids.values())
    assert all(set(row) == {"id", "username", "email", "is_superuser", "protected", "owned_brokers_alone"} for row in body["users"])
    assert {row["username"]: row["protected"] for row in body["users"]}["bruno"] == "you"


@pytest.mark.asyncio
async def test_the_choice_of_an_instance_not_over_the_limit_is_empty_and_for_administrators_only(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-121: not over the limit: an administrator reads ``over_limit`` false and no users; an ordinary user gets the 403 of ``require_admin``."""
    await _five(engine)
    admin = await _sign_in(app, "anna")
    ordinary = await _sign_in(app, "carla")
    _limit(monkeypatch, "5")

    ok = await _request(app, "GET", "/users/over-limit", session=admin)
    refused = await _request(app, "GET", "/users/over-limit", session=ordinary)

    assert ok.status_code == 200 and ok.json()["over_limit"] is False and ok.json()["users"] == []
    assert refused.status_code == 403


@pytest.mark.asyncio
async def test_the_example_through_the_api(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-130: five accounts, a limit of 3. Anna keeps Anna, Bruno and Carla: ``{"kept": 3, "deactivated": 2, "revoked_invites": 0}``; Carla, signed in before, now reaches the app; Dario and Elena, signed in before, meet the 401 of a disabled account, and cannot sign in again (403)."""
    print_section("A5-7-130: the example through the API")
    await _five(engine)
    anna = await _sign_in(app, "anna")
    carla = await _sign_in(app, "carla")
    dario = await _sign_in(app, "dario")
    _limit(monkeypatch, "3")
    ids = {row["username"]: row["id"] for row in (await _request(app, "GET", "/users/over-limit", session=anna)).json()["users"]}

    done = await _request(app, "POST", "/users/over-limit/resolve", session=anna, json={"keep_user_ids": [ids["anna"], ids["bruno"], ids["carla"]]})

    assert done.status_code == 200 and done.json() == {"kept": 3, "deactivated": 2, "revoked_invites": 0}
    assert (await _request(app, "GET", "/brokers", session=carla)).status_code == 200
    assert (await _request(app, "GET", "/auth/me", session=dario)).status_code == 401
    again = await _request(app, "POST", "/auth/login", json={"username": "dario", "password": PASSWORD})
    assert again.status_code == 403 and again.json()["detail"]["error_code"] == "ACCOUNT_DISABLED"
    assert (await _request(app, "GET", "/users/over-limit", session=anna)).json()["over_limit"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("keep", "status", "code"),
    [
        (["anna", "bruno", 99999], 422, "UNKNOWN_USER"),
        (["anna", "bruno", "carla", "dario"], 422, "TOO_MANY_KEPT"),
        (["bruno", "carla", "dario"], 422, "PROTECTED_MISSING"),
    ],
    ids=["unknown", "too-many", "chooser-missing"],
)
async def test_the_refusals_have_their_code_and_change_nothing(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, keep: list[Any], status: int, code: str) -> None:
    """A5-7-131: each refusal answers with its status and ``detail.error_code``, and the accounts stay as they were (the state is still there)."""
    ids = await _five(engine)
    anna = await _sign_in(app, "anna")
    _limit(monkeypatch, "3")

    reply = await _request(app, "POST", "/users/over-limit/resolve", session=anna, json={"keep_user_ids": [ids.get(item, item) for item in keep]})

    assert reply.status_code == status and _code(reply) == code, f"{reply.status_code} {reply.text}"
    assert (await _request(app, "GET", "/users/over-limit", session=anna)).json()["over_limit"] is True


@pytest.mark.asyncio
async def test_a_second_resolution_is_a_409(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-132: when the state is gone (another administrator resolved it) the confirmation answers 409 ``NOT_OVER_LIMIT``."""
    ids = await _five(engine)
    anna = await _sign_in(app, "anna")
    bruno = await _sign_in(app, "bruno")
    _limit(monkeypatch, "3")

    first = await _request(app, "POST", "/users/over-limit/resolve", session=bruno, json={"keep_user_ids": [ids["bruno"], ids["carla"], ids["anna"]]})
    second = await _request(app, "POST", "/users/over-limit/resolve", session=anna, json={"keep_user_ids": [ids["anna"]]})

    assert first.status_code == 200
    assert second.status_code == 409 and _code(second) == "NOT_OVER_LIMIT"


@pytest.mark.asyncio
async def test_an_ordinary_user_cannot_resolve(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-133: an ordinary user: 423 while over the limit, 403 otherwise — never a deactivation."""
    ids = await _five(engine)
    carla = await _sign_in(app, "carla")
    _limit(monkeypatch, "3")
    over = await _request(app, "POST", "/users/over-limit/resolve", session=carla, json={"keep_user_ids": [ids["carla"]]})
    _limit(monkeypatch, "9")
    free = await _request(app, "POST", "/users/over-limit/resolve", session=carla, json={"keep_user_ids": [ids["carla"]]})

    assert (over.status_code, _code(over)) == (423, OVER_LIMIT_CODE)
    assert free.status_code == 403


@pytest.mark.asyncio
async def test_the_request_is_strict(app: FastAPI, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-134: the body is exactly ``{"keep_user_ids": [int…]}``: an unknown field, a missing one or a wrong type is a 422 of the validation, and nothing changes."""
    await _five(engine)
    anna = await _sign_in(app, "anna")
    _limit(monkeypatch, "3")

    for body in ({}, {"keep_user_ids": "all"}, {"keep_user_ids": [1], "force": True}):
        reply = await _request(app, "POST", "/users/over-limit/resolve", session=anna, json=body)
        assert reply.status_code == 422, f"{body}: {reply.status_code}"
    assert (await _request(app, "GET", "/users/over-limit", session=anna)).json()["over_limit"] is True

"""
The state «over the limit» and its resolution (workstream A, lot A5-7). Selector: ``services user-limit``.

When the active accounts outnumber ``LIBREFOLIO_MAX_USERS`` (a smaller plan, or a restore that brought more users than the
plan holds), the instance is «over the limit»: its administrator chooses who keeps the access, the others are DEACTIVATED
(never deleted). The state is never stored: it is read from the accounts every time it is asked
(``services/accounts/user_limit_service.py``). Analysis: ``ondata5/A-5-7-analisi-oltre-il-limite.md``.

(a) The state: only ``active > limit``; no limit, or a limit that cannot be read (never locks anybody out), or ``active ==
    limit`` → no state; inactive accounts, live invitations and accounts waiting for their verification do not trigger it
    but take places (``max_keep``, ``live_invites``).
(b) The list for the choice: who is protected (the owner of a managed instance, else the administrator who chooses), how
    many brokers each account owns alone.
(c) The resolution: the example of 5 accounts with a limit of 3; nothing is deleted; the deactivated lose their sessions,
    the others change nothing; the refusals (``NOT_OVER_LIMIT``, ``UNKNOWN_USER``, ``TOO_MANY_KEPT``,
    ``PROTECTED_MISSING``, ``NO_ADMIN_KEPT``) change nothing; live invitations are revoked only as far as the kept
    accounts need their places; one commit.

Pure: an engine of its own under ``tmp_path``, no server, no network.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountTokenPurpose, Broker, BrokerUserAccess, User, UserRole
from backend.app.services.accounts import auth_service, registration_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.test_scripts.test_utils import print_section

LIMIT_MODULE = "backend.app.services.accounts.user_limit_service"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
INHERITED_VARIABLES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_REGISTRATION", LIMIT_VARIABLE, "LIBREFOLIO_BLOCKED", PROFILE_VARIABLE, ADMIN_EMAIL_VARIABLE)
OWNER_EMAIL = "owner@zq-limit.example.com"


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


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'limit.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def limit() -> ModuleType:
    try:
        return importlib.import_module(LIMIT_MODULE)
    except ModuleNotFoundError as missing:
        if missing.name == LIMIT_MODULE:
            pytest.fail(f"red until A5-7: {LIMIT_MODULE} does not exist", pytrace=False)
        raise


# =============================================================================
# HELPERS
# =============================================================================


def _max_users(monkeypatch: pytest.MonkeyPatch, value: Optional[str]) -> None:
    if value is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, value)


def _managed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, OWNER_EMAIL)


async def _add_user(engine: AsyncEngine, username: str, *, admin: bool = False, active: bool = True, owner: bool = False, email: Optional[str] = None) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@zq-limit.example.com", hashed_password="x", is_active=active, is_superuser=admin)
        if owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user.id


async def _five(engine: AsyncEngine) -> dict[str, int]:
    """Anna (administrator), Bruno (administrator), Carla, Dario, Elena: all active."""
    return {
        "anna": await _add_user(engine, "anna", admin=True),
        "bruno": await _add_user(engine, "bruno", admin=True),
        "carla": await _add_user(engine, "carla"),
        "dario": await _add_user(engine, "dario"),
        "elena": await _add_user(engine, "elena"),
    }


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None
    return user


async def _state(limit: ModuleType, engine: AsyncEngine) -> Any:
    async with AsyncSession(engine) as session:
        return await limit.over_limit_state(session)


async def _choice(limit: ModuleType, engine: AsyncEngine, admin_id: int) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        admin = await session.get(User, admin_id)
        return await limit.list_for_choice(session, admin)


async def _resolve(limit: ModuleType, engine: AsyncEngine, admin_id: int, keep: list[int]) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        admin = await session.get(User, admin_id)
        return await limit.resolve(session, admin, keep)


async def _refusal(limit: ModuleType, engine: AsyncEngine, admin_id: int, keep: list[int]) -> str:
    with pytest.raises(limit.UserLimitError) as refused:
        await _resolve(limit, engine, admin_id, keep)
    return refused.value.code


async def _snapshot(engine: AsyncEngine) -> dict[str, list[Any]]:
    async with engine.connect() as connection:
        users = (await connection.execute(text("SELECT * FROM users ORDER BY id"))).mappings().all()
        tokens = (await connection.execute(text("SELECT * FROM account_tokens ORDER BY id"))).mappings().all()
        access = (await connection.execute(text("SELECT * FROM broker_user_access ORDER BY id"))).mappings().all()
    return {"users": [dict(row) for row in users], "tokens": [dict(row) for row in tokens], "access": [dict(row) for row in access]}


async def _invite(engine: AsyncEngine, *, minutes_ago: int = 0) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE, created_by_user_id=None, now=datetime.now(UTC) - timedelta(minutes=minutes_ago))
        await session.commit()
    return issued.record.id


async def _live_invites(engine: AsyncEngine) -> list[int]:
    async with AsyncSession(engine) as session:
        return [row.id for row in await registration_service.list_pending_invites(session)]


async def _give_broker(engine: AsyncEngine, name: str, *owners: int, others: tuple[int, ...] = ()) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        broker = Broker(name=name)
        session.add(broker)
        await session.flush()
        for user_id in owners:
            session.add(BrokerUserAccess(user_id=user_id, broker_id=broker.id, role=UserRole.OWNER))
        for user_id in others:
            session.add(BrokerUserAccess(user_id=user_id, broker_id=broker.id, role=UserRole.VIEWER, share_percentage=0))
        await session.commit()
    return broker.id


# =============================================================================
# (a) THE STATE
# =============================================================================


@pytest.mark.asyncio
async def test_no_limit_no_state(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-010: without ``LIBREFOLIO_MAX_USERS`` there is no state, however many accounts there are."""
    print_section("A5-7-010: no limit")
    await _five(engine)
    _max_users(monkeypatch, None)
    assert await _state(limit, engine) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["abc", "0", "-3", "2.5"])
async def test_a_limit_that_cannot_be_read_never_triggers_the_state(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """A5-7-011 (D2): an invalid value reads as a limit of 0 for the registration (closed), but must NEVER lock anybody out: no state. The error is in the log, as today."""
    await _five(engine)
    _max_users(monkeypatch, value)
    with capture_logs():
        assert await _state(limit, engine) is None
    async with AsyncSession(engine) as session:
        assert (await registration_service.user_usage(session)).max_users == 0, "barrier: the registration still reads it as 0 (closed)"


@pytest.mark.asyncio
async def test_active_equal_to_the_limit_is_no_state(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-012 (D1): the state is ``active > limit``, strictly."""
    await _five(engine)
    _max_users(monkeypatch, "5")
    assert await _state(limit, engine) is None
    _max_users(monkeypatch, "6")
    assert await _state(limit, engine) is None


@pytest.mark.asyncio
async def test_more_active_accounts_than_the_limit_is_the_state(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-013: five active accounts, a limit of 3 → the state, with the numbers."""
    await _five(engine)
    _max_users(monkeypatch, "3")
    state = await _state(limit, engine)
    assert state is not None
    assert (state.active, state.max_users, state.live_invites, state.waiting_accounts, state.max_keep) == (5, 3, 0, 0, 3)


@pytest.mark.asyncio
async def test_inactive_accounts_do_not_count(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-014: four active and three deactivated, a limit of 4: no state."""
    await _five(engine)
    await _add_user(engine, "old1", active=False)
    await _add_user(engine, "old2", active=False)
    await _add_user(engine, "old3", active=False)
    ids = await _five_ids(engine)
    async with AsyncSession(engine) as session:
        await session.execute(text("UPDATE users SET is_active = 0 WHERE username = 'elena'"))
        await session.commit()
    assert len(ids) == 8
    _max_users(monkeypatch, "4")
    assert await _state(limit, engine) is None


async def _five_ids(engine: AsyncEngine) -> list[int]:
    async with engine.connect() as connection:
        return list((await connection.execute(text("SELECT id FROM users ORDER BY id"))).scalars().all())


@pytest.mark.asyncio
async def test_invitations_and_waiting_accounts_do_not_trigger_but_take_places(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-015: three active accounts and a limit of 3 with two live invitations: no state. With a fourth account the state shows them: ``live_invites`` 2, and ``max_keep`` is the limit less the accounts that wait (not the invitations, which can be revoked)."""
    await _add_user(engine, "anna", admin=True)
    await _add_user(engine, "bruno", admin=True)
    await _add_user(engine, "carla")
    await _invite(engine)
    await _invite(engine)
    _max_users(monkeypatch, "3")
    assert await _state(limit, engine) is None
    await _add_user(engine, "dario")
    state = await _state(limit, engine)
    assert state is not None
    assert (state.active, state.live_invites, state.waiting_accounts, state.max_keep) == (4, 2, 0, 3)


# =============================================================================
# (b) THE LIST FOR THE CHOICE
# =============================================================================


@pytest.mark.asyncio
async def test_the_list_protects_the_administrator_who_chooses_on_a_self_hosted_instance(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-020: nobody is protected on a self-hosted instance but the one who chooses (``you``); every active account is listed once, with its role, and no password."""
    ids = await _five(engine)
    _max_users(monkeypatch, "3")
    choice = await _choice(limit, engine, ids["bruno"])
    assert [row.id for row in choice.users] == list(ids.values())
    assert {row.id: row.protected for row in choice.users} == {ids["anna"]: None, ids["bruno"]: "you", ids["carla"]: None, ids["dario"]: None, ids["elena"]: None}
    assert {row.id: row.is_superuser for row in choice.users} == {ids["anna"]: True, ids["bruno"]: True, ids["carla"]: False, ids["dario"]: False, ids["elena"]: False}


@pytest.mark.asyncio
async def test_the_owner_of_a_managed_instance_is_protected_and_the_chooser_is_not_forced(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-021: on a managed instance the owner is protected (``owner``); with an owner to protect the one who chooses is no longer forced (``None``): the owner is an administrator, so one stays."""
    _managed(monkeypatch)
    owner_id = await _add_user(engine, "titolare", admin=True, owner=True, email=OWNER_EMAIL)
    other = await _add_user(engine, "altro", admin=True)
    await _add_user(engine, "c1")
    await _add_user(engine, "c2")
    _max_users(monkeypatch, "2")
    choice = await _choice(limit, engine, other)
    assert {row.id: row.protected for row in choice.users if row.id in (owner_id, other)} == {owner_id: "owner", other: None}


@pytest.mark.asyncio
async def test_managed_without_an_owner_protects_the_chooser(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-022: a managed instance whose owner has no account (the outcome ``none`` of a restore): only the administrator who chooses is protected."""
    _managed(monkeypatch)
    ids = await _five(engine)
    _max_users(monkeypatch, "3")
    choice = await _choice(limit, engine, ids["anna"])
    assert {row.id: row.protected for row in choice.users} == {ids["anna"]: "you", ids["bruno"]: None, ids["carla"]: None, ids["dario"]: None, ids["elena"]: None}


@pytest.mark.asyncio
async def test_the_list_counts_the_brokers_an_account_owns_alone(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-023: ``owned_brokers_alone``: brokers where the account is the ONLY owner. Two owners → neither is alone; a viewer owns nothing."""
    ids = await _five(engine)
    await _give_broker(engine, "alone-1", ids["dario"], others=(ids["carla"],))
    await _give_broker(engine, "alone-2", ids["dario"])
    await _give_broker(engine, "shared", ids["carla"], ids["elena"])
    _max_users(monkeypatch, "3")
    choice = await _choice(limit, engine, ids["anna"])
    assert {row.id: row.owned_brokers_alone for row in choice.users} == {ids["anna"]: 0, ids["bruno"]: 0, ids["carla"]: 0, ids["dario"]: 2, ids["elena"]: 0}


@pytest.mark.asyncio
async def test_the_list_of_an_instance_not_over_the_limit_is_empty(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-024: not over the limit → ``over_limit`` false and no users (nothing to choose, nothing to read)."""
    ids = await _five(engine)
    _max_users(monkeypatch, "5")
    choice = await _choice(limit, engine, ids["anna"])
    assert (choice.over_limit, choice.users) == (False, [])


# =============================================================================
# (c) THE RESOLUTION
# =============================================================================


@pytest.mark.asyncio
async def test_five_accounts_a_limit_of_three_the_example(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-030: the example of the analysis. Anna keeps herself, Bruno and Carla: Dario and Elena are deactivated — their sessions end (``session_version`` up), nothing is deleted, the three kept change in nothing — and the state is gone."""
    print_section("A5-7-030: 5 accounts, limit 3")
    ids = await _five(engine)
    _max_users(monkeypatch, "3")
    before = await _snapshot(engine)
    versions = {name: (await _account(engine, user_id)).session_version for name, user_id in ids.items()}

    result = await _resolve(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], ids["carla"]])

    assert (result.kept, result.deactivated, result.revoked_invites) == (3, 2, 0)
    after = await _snapshot(engine)
    assert [row["id"] for row in after["users"]] == [row["id"] for row in before["users"]], "nothing was deleted"
    active = {row["username"]: bool(row["is_active"]) for row in after["users"]}
    assert active == {"anna": True, "bruno": True, "carla": True, "dario": False, "elena": False}
    for name in ("anna", "bruno", "carla"):
        kept = await _account(engine, ids[name])
        assert kept.session_version == versions[name], f"{name} (kept) keeps their session"
    for name in ("dario", "elena"):
        assert (await _account(engine, ids[name])).session_version > versions[name], f"{name} loses their sessions"
    assert await _state(limit, engine) is None


@pytest.mark.asyncio
async def test_nothing_else_is_touched(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-031: the brokers, their access rows and every column of the kept accounts are the same after the resolution; only ``is_active``, ``session_version`` and ``updated_at`` of the deactivated change."""
    ids = await _five(engine)
    await _give_broker(engine, "dario-alone", ids["dario"], others=(ids["carla"],))
    _max_users(monkeypatch, "3")
    before = await _snapshot(engine)

    await _resolve(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], ids["carla"]])

    after = await _snapshot(engine)
    assert after["access"] == before["access"], "access rows untouched"
    assert after["users"][:3] == before["users"][:3], "the kept accounts: identical rows"
    for old, new in zip(before["users"][3:], after["users"][3:], strict=True):
        changed = {key for key in old if old[key] != new[key]}
        assert changed <= {"is_active", "session_version", "updated_at"}, changed
        assert new["is_active"] in (0, False)
    async with AsyncSession(engine) as session:
        assert (await session.execute(select(func.count()).select_from(Broker))).scalar() == 1


@pytest.mark.asyncio
async def test_the_refusals_change_nothing(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-032: ``UNKNOWN_USER`` (an id that is not active, or does not exist), ``TOO_MANY_KEPT``, ``PROTECTED_MISSING`` (the chooser, on a self-hosted instance), ``NO_ADMIN_KEPT`` (kept accounts without an administrator but the chooser is not forced): each refuses with its code and the database is the same."""
    ids = await _five(engine)
    await _add_user(engine, "gone", active=False)
    _max_users(monkeypatch, "3")
    before = await _snapshot(engine)
    inactive_id = (await _five_ids(engine))[-1]

    assert await _refusal(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], 99999]) == "UNKNOWN_USER"
    assert await _refusal(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], inactive_id]) == "UNKNOWN_USER"
    assert await _refusal(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], ids["carla"], ids["dario"]]) == "TOO_MANY_KEPT"
    assert await _refusal(limit, engine, ids["anna"], [ids["bruno"], ids["carla"], ids["dario"]]) == "PROTECTED_MISSING"
    assert await _snapshot(engine) == before


@pytest.mark.asyncio
async def test_no_administrator_kept_is_refused_when_the_chooser_is_not_forced(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-033: with a protected owner, who is an administrator, the chooser may leave themselves out: one administrator stays, and the choice is theirs."""
    _managed(monkeypatch)
    owner_id = await _add_user(engine, "titolare", admin=True, owner=True, email=OWNER_EMAIL)
    chooser = await _add_user(engine, "altro", admin=True)
    c1 = await _add_user(engine, "c1")
    await _add_user(engine, "c2")
    _max_users(monkeypatch, "2")

    result = await _resolve(limit, engine, chooser, [owner_id, c1])

    assert (result.kept, result.deactivated) == (2, 2)
    assert (await _account(engine, chooser)).is_active is False, "the chooser left themselves out: their call"
    assert (await _account(engine, owner_id)).is_active is True


@pytest.mark.asyncio
async def test_a_set_without_an_administrator_is_refused(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-034: on a managed instance whose protected account is not an administrator (a restore's mistake), a kept set with no administrator is refused (``NO_ADMIN_KEPT``) and nothing changes: somebody must still be able to administer."""
    _managed(monkeypatch)
    owner_id = await _add_user(engine, "titolare", admin=False, owner=True, email=OWNER_EMAIL)
    chooser = await _add_user(engine, "altro", admin=True)
    await _add_user(engine, "c1")
    _max_users(monkeypatch, "1")
    before = await _snapshot(engine)

    assert await _refusal(limit, engine, chooser, [owner_id]) == "NO_ADMIN_KEPT"
    assert await _snapshot(engine) == before


@pytest.mark.asyncio
async def test_the_owner_cannot_be_left_out(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-035: the protected owner of a managed instance must be in the kept set: ``PROTECTED_MISSING``, nothing changes."""
    _managed(monkeypatch)
    owner_id = await _add_user(engine, "titolare", admin=True, owner=True, email=OWNER_EMAIL)
    chooser = await _add_user(engine, "altro", admin=True)
    c1 = await _add_user(engine, "c1")
    await _add_user(engine, "c2")
    _max_users(monkeypatch, "2")
    before = await _snapshot(engine)

    assert await _refusal(limit, engine, chooser, [chooser, c1]) == "PROTECTED_MISSING"
    assert owner_id and await _snapshot(engine) == before


@pytest.mark.asyncio
async def test_a_second_resolution_finds_nothing_to_do(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-036: two administrators confirm one after the other: the second finds the state gone (``NOT_OVER_LIMIT``) and changes nothing — whatever it chose."""
    ids = await _five(engine)
    _max_users(monkeypatch, "3")
    await _resolve(limit, engine, ids["bruno"], [ids["bruno"], ids["carla"], ids["dario"]])
    after_first = await _snapshot(engine)

    assert await _refusal(limit, engine, ids["anna"], [ids["anna"], ids["elena"]]) == "NOT_OVER_LIMIT"
    assert await _snapshot(engine) == after_first


@pytest.mark.asyncio
async def test_invitations_are_revoked_only_as_far_as_the_kept_accounts_need_their_places(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-037 (D3): a limit of 3 with two live invitations. Keeping 3 accounts needs both places freed: both invitations are revoked (``revoked_invites`` 2, none live afterwards). Only invitations are revoked, never an account."""
    ids = await _five(engine)
    older = await _invite(engine, minutes_ago=10)
    newer = await _invite(engine, minutes_ago=1)
    _max_users(monkeypatch, "3")

    first = await _resolve(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], ids["carla"]])
    assert (first.revoked_invites, await _live_invites(engine)) == (2, [])
    assert older != newer


@pytest.mark.asyncio
async def test_an_invitation_that_fits_is_kept(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-038: five accounts, a limit of 3, one live invitation: keeping 2 accounts leaves a place for it — nothing revoked."""
    ids = await _five(engine)
    invite = await _invite(engine)
    _max_users(monkeypatch, "3")

    result = await _resolve(limit, engine, ids["anna"], [ids["anna"], ids["bruno"]])

    assert (result.kept, result.deactivated, result.revoked_invites) == (2, 3, 0)
    assert await _live_invites(engine) == [invite]


@pytest.mark.asyncio
async def test_the_accounts_that_wait_take_their_places_for_good(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-039: an account that waits for its verification link holds a place that cannot be revoked here: with a limit of 3 and one waiting, ``max_keep`` is 2 and keeping 3 is ``TOO_MANY_KEPT``."""
    ids = await _five(engine)
    waiting = await _add_user(engine, "waiting", active=False)
    async with AsyncSession(engine) as session:
        user = await session.get(User, waiting)
        await token_service.issue_token(session, AccountTokenPurpose.EMAIL_VERIFICATION, user_id=user.id, email=user.email)
        await session.commit()
    _max_users(monkeypatch, "3")
    state = await _state(limit, engine)
    assert state is not None and (state.waiting_accounts, state.max_keep) == (1, 2)

    assert await _refusal(limit, engine, ids["anna"], [ids["anna"], ids["bruno"], ids["carla"]]) == "TOO_MANY_KEPT"


@pytest.mark.asyncio
async def test_one_commit_and_the_log_names_numbers_not_people(engine: AsyncEngine, limit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A5-7-040: the resolution is ONE transaction (one commit, no rollback of the session) and its log lines carry counts and ids, never a username or an address."""
    ids = await _five(engine)
    _max_users(monkeypatch, "3")

    class Counting(AsyncSession):
        commits = 0
        rollbacks = 0

        async def commit(self) -> None:
            Counting.commits += 1
            await super().commit()

        async def rollback(self) -> None:
            Counting.rollbacks += 1
            await super().rollback()

    async with Counting(engine, expire_on_commit=False) as session:
        admin = await session.get(User, ids["anna"])
        with capture_logs() as events:
            await limit.resolve(session, admin, [ids["anna"], ids["bruno"], ids["carla"]])

    assert (Counting.commits, Counting.rollbacks) == (1, 0)
    text_of_log = "\n".join(str(event) for event in events).lower()
    for name in ("anna", "bruno", "carla", "dario", "elena", "zq-limit.example.com"):
        assert name not in text_of_log, f"{name} in the log"

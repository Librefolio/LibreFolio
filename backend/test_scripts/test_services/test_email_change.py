"""The change of address a user asks for from Profile (project 71, block 2): the shared helpers and the revocations.

A change asked from Profile will wait for a link the account issues for itself (the service of step 2.3): an
``email_change`` row with ``created_by_user_id == user_id``. The instance owner's link (A5-1b) is issued by the host and
carries no ``created_by_user_id``. Here such rows are issued directly with ``token_service.issue_token``. The contract
pinned here:

- REVOCATIONS — ``user_service.revoke_pending_email_change(session, user_id)`` revokes the live ``email_change`` links the
  account issued for itself, and never the host's. Every event that ends what the account's owner can trust revokes them
  in its own commit: a password changed (``POST /auth/change-password``), a password reset through a link
  (``complete_password_reset``) or from the command line (``reset_password``), and a deactivation
  (``update_user_status`` and ``deactivate_for_limit``, through ``_apply_active_flag``; ``set_user_active`` from the
  command line), also of an account already inactive. Activating an account revokes nothing. In each case a host link of the same account stays valid:
  the owner flow is not touched (A5-1b).
- SHARED HELPERS — extracted from ``update_profile`` without changing what it does: ``email_refusal(session, user,
  address, *, reserve_owner_address=True)`` (the address of another account, the username of another account, the
  address the host reserved for the owner of a managed instance unless the account is that owner — and the command line
  passes ``reserve_owner_address=False``); ``move_email(session, user, address, *, verified_at)`` (the address moved, its
  verification set, every session ended, the live password-reset, setup and email-change links revoked — the host's too,
  as ``update_profile`` always did). Not committed: the caller commits.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all``; ``get_async_engine`` is a
tripwire; the profile and the owner's variable are set with ``monkeypatch``. No server, no email, no clock wait: every
token gets its ``now`` where it matters.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from backend.app.api.v1 import auth as auth_api
from backend.app.config import get_settings
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountTokenPurpose, User
from backend.app.schemas.auth import ChangePasswordRequest
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import TokenStatus
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_utils import print_section, print_success, unique_id

CHANGE = AccountTokenPurpose.EMAIL_CHANGE
#: The link of a change asked from Profile lives 24 hours (decision D5.2).
PROFILE_TTL = timedelta(hours=24)
PASSWORD = "ZqOldPass123!"
NEW_PASSWORD = "ZqNewPass456!"
NEW_ADDRESS = "zq.new-address@zq-emc.example.com"
OWNER_ADDRESS = "owner@zq-emc.example.com"

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
INHERITED_PREFIXES = ("LIBREFOLIO_ADMIN_", "LIBREFOLIO_SMTP_")
INHERITED_VARIABLES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_BLOCKED", PROFILE_VARIABLE)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """None of the profile, admin, SMTP and links variables of the shell that started the run; test mode keeps ``.env`` out."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's — the engine must be passed through")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'email_change.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


# =============================================================================
# HELPERS
# =============================================================================


async def _add_user(engine: AsyncEngine, *, active: bool = True, admin: bool = False, email: Optional[str] = None, instance_owner: bool = False) -> User:
    """A new account of this test, with ``PASSWORD`` as its password: names and address unique to it."""
    name = f"zq-emc-{unique_id()}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=email or f"{name}@zq-emc.example.com", hashed_password=auth_service.hash_password(PASSWORD), is_active=active, is_superuser=admin)
        if instance_owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user


async def _issue_change(engine: AsyncEngine, user_id: int, *, own: bool) -> str:
    """A live ``email_change`` link of ``user_id``: issued by the account itself (Profile, ``own``) or by the host (no creator)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, CHANGE, user_id=user_id, email=NEW_ADDRESS, created_by_user_id=user_id if own else None, ttl=PROFILE_TTL)
        await session.commit()
    return issued.token


async def _both_links(engine: AsyncEngine, user_id: int) -> tuple[str, str]:
    """The account's own Profile link and a host link, both live: (own, host)."""
    return await _issue_change(engine, user_id, own=True), await _issue_change(engine, user_id, own=False)


async def _status(engine: AsyncEngine, token: str) -> TokenStatus:
    async with AsyncSession(engine) as session:
        return (await token_service.inspect_token(session, token, CHANGE)).status


async def _assert_own_revoked_host_valid(engine: AsyncEngine, own: str, host: str, event: str) -> None:
    own_status, host_status = await _status(engine, own), await _status(engine, host)
    assert own_status is TokenStatus.REVOKED, f"{event}: the Profile link the account issued must be revoked, got {own_status}"
    assert host_status is TokenStatus.VALID, f"{event}: the host's link (no created_by_user_id) must stay valid, got {host_status}"


def _request() -> Request:
    """POST /api/v1/auth/change-password as uvicorn hands it to the app: the route reads the client address and the scheme."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/change-password",
        "raw_path": b"/api/v1/auth/change-password",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"librefolio.test")],
        "client": ("127.0.0.1", 50000),
        "server": ("librefolio.test", 80),
    }
    return Request(scope)


def _managed(monkeypatch: pytest.MonkeyPatch, owner_address: str) -> None:
    """A managed instance whose host named ``owner_address`` for its owner, with a barrier that ``get_settings()`` reads the profile."""
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, owner_address)
    assert get_settings().LIBREFOLIO_PROFILE == "managed", "barrier: get_settings() must read the profile this test sets"


# =============================================================================
# 1. REVOCATIONS
# =============================================================================


@pytest.mark.asyncio
async def test_a_password_change_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-001 — ``POST /auth/change-password`` (the route, called as FastAPI calls it) revokes the account's Profile ``email_change`` link in its commit; a host link of the account stays valid."""
    print_section("EMC-001: change-password revokes the Profile link")
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        current = await session.get(User, user.id)
        await auth_api.change_password(request=ChangePasswordRequest(current_password=PASSWORD, new_password=NEW_PASSWORD), response=Response(), http_request=_request(), current_user=current, session=session)

    await _assert_own_revoked_host_valid(engine, own, host, "change-password")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_a_password_reset_through_a_link_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-002 — ``complete_password_reset`` (a reset link spent) revokes the account's Profile ``email_change`` link in its commit; a host link stays valid."""
    print_section("EMC-002: complete_password_reset revokes the Profile link")
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        reset = await user_service.create_password_reset(session, await session.get(User, user.id))
        await session.commit()

    async with AsyncSession(engine, expire_on_commit=False) as session:
        spent = await user_service.complete_password_reset(session, reset.token, NEW_PASSWORD)
    assert spent is not None, "setup: the reset link must be spent"

    await _assert_own_revoked_host_valid(engine, own, host, "complete_password_reset")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_a_password_reset_from_the_command_line_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-003 — ``reset_password`` (``./dev.py user reset-password``) revokes the account's Profile ``email_change`` link in its commit; a host link stays valid."""
    print_section("EMC-003: reset_password revokes the Profile link")
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        done, error = await user_service.reset_password(session, user.username, NEW_PASSWORD)
    assert (done, error) == (True, None), f"setup: the reset must succeed, got {error!r}"

    await _assert_own_revoked_host_valid(engine, own, host, "reset_password")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_a_deactivation_by_an_administrator_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-004 — ``update_user_status(is_active=False)`` (the administrator's deactivation, through ``_apply_active_flag``) revokes the account's Profile ``email_change`` link in its commit; a host link stays valid."""
    print_section("EMC-004: update_user_status(is_active=False) revokes the Profile link")
    await _add_user(engine, admin=True)  # another active administrator: the deactivation is never the last one's
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        refusal = await user_service.update_user_status(session, await session.get(User, user.id), is_active=False)
    assert refusal is None, f"setup: the deactivation must be accepted, got {refusal!r}"

    await _assert_own_revoked_host_valid(engine, own, host, "update_user_status")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_a_deactivation_for_the_user_limit_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-005 — ``deactivate_for_limit`` (an account over the instance's limit of users, A5-7) revokes the account's Profile ``email_change`` link, committed by its caller; a host link stays valid."""
    print_section("EMC-005: deactivate_for_limit revokes the Profile link")
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await user_service.deactivate_for_limit(session, await session.get(User, user.id))
        await session.commit()

    await _assert_own_revoked_host_valid(engine, own, host, "deactivate_for_limit")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_a_deactivation_from_the_command_line_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-006 — ``set_user_active(active=False)`` (``./dev.py user deactivate``) revokes the account's Profile ``email_change`` link in its commit; a host link stays valid."""
    print_section("EMC-006: set_user_active(False) revokes the Profile link")
    await _add_user(engine, admin=True)
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        done, error = await user_service.set_user_active(session, user.username, False)
    assert (done, error) == (True, None), f"setup: the deactivation must succeed, got {error!r}"

    await _assert_own_revoked_host_valid(engine, own, host, "set_user_active")
    print_success("Profile link revoked, host link valid")


@pytest.mark.asyncio
async def test_deactivating_an_account_already_inactive_revokes_the_pending_profile_change(engine: AsyncEngine) -> None:
    """EMC-006b — ``update_user_status(is_active=False)`` on an account already inactive (the second branch of ``_apply_active_flag``): its Profile ``email_change`` link is revoked and committed — the revocation counts as a change —; a host link stays valid."""
    print_section("EMC-006b: deactivating an inactive account revokes the Profile link")
    user = await _add_user(engine, active=False)
    own, host = await _both_links(engine, user.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        refusal = await user_service.update_user_status(session, await session.get(User, user.id), is_active=False)
    assert refusal is None, f"setup: the deactivation must be accepted, got {refusal!r}"

    await _assert_own_revoked_host_valid(engine, own, host, "update_user_status on an inactive account")
    print_success("Profile link revoked and committed, host link valid")


@pytest.mark.asyncio
async def test_an_activation_revokes_no_email_change_link(engine: AsyncEngine) -> None:
    """EMC-007 — activating an account (``update_user_status(is_active=True)`` and ``set_user_active(True)``) is no reason to stop a change: both links stay valid."""
    print_section("EMC-007: an activation leaves the email-change links alone")
    by_admin = await _add_user(engine, active=False)
    by_cli = await _add_user(engine, active=False)
    links = {user.id: await _both_links(engine, user.id) for user in (by_admin, by_cli)}

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await user_service.update_user_status(session, await session.get(User, by_admin.id), is_active=True) is None
    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await user_service.set_user_active(session, by_cli.username, True) == (True, None)

    for user_id, (own, host) in links.items():
        assert (await _status(engine, own), await _status(engine, host)) == (TokenStatus.VALID, TokenStatus.VALID), f"account {user_id}: activated, its links stay valid"
    print_success("both links valid after an activation")


@pytest.mark.asyncio
async def test_revoke_pending_email_change_touches_only_the_accounts_own_live_links(engine: AsyncEngine) -> None:
    """EMC-008 — ``revoke_pending_email_change(session, user_id)`` revokes the account's own live Profile links (how many) and nothing else: the host's link of the same account, another account's Profile link, and a link already spent keep their state. Not committed: a rollback undoes it."""
    print_section("EMC-008: revoke_pending_email_change, its scope")
    user, other = await _add_user(engine), await _add_user(engine)
    first, host = await _both_links(engine, user.id)
    second = await _issue_change(engine, user.id, own=True)
    neighbour = await _issue_change(engine, other.id, own=True)

    async with AsyncSession(engine) as session:
        assert await user_service.revoke_pending_email_change(session, user.id) == 2
        await session.rollback()
    assert await _status(engine, first) is TokenStatus.VALID, "not committed: a rollback undoes it"

    async with AsyncSession(engine) as session:
        assert await user_service.revoke_pending_email_change(session, user.id) == 2
        await session.commit()
    async with AsyncSession(engine) as session:
        assert await user_service.revoke_pending_email_change(session, user.id) == 0, "nothing live is left to revoke"

    assert [await _status(engine, token) for token in (first, second, host, neighbour)] == [TokenStatus.REVOKED, TokenStatus.REVOKED, TokenStatus.VALID, TokenStatus.VALID]
    print_success("own links revoked; host link and another account's link untouched")


# =============================================================================
# 2. SHARED HELPERS (extracted from update_profile)
# =============================================================================


@pytest.mark.asyncio
async def test_email_refusal_reads_the_three_rules_of_update_profile(engine: AsyncEngine) -> None:
    """EMC-009 — ``email_refusal(session, user, address)``: ``EMAIL_TAKEN`` for another account's address (any letter case) and for another account's username; None for a free address, and for the account's own username or address."""
    print_section("EMC-009: email_refusal, the address and the username of another account")
    user, other = await _add_user(engine), await _add_user(engine)

    async with AsyncSession(engine) as session:
        account = await session.get(User, user.id)
        refusals = {
            "another account's address": await user_service.email_refusal(session, account, other.email.upper()),
            "another account's username": await user_service.email_refusal(session, account, other.username),
            "a free address": await user_service.email_refusal(session, account, NEW_ADDRESS),
            "its own address": await user_service.email_refusal(session, account, user.email),
            "its own username": await user_service.email_refusal(session, account, user.username),
        }

    codes = {case: (refusal.code if refusal is not None else None) for case, refusal in refusals.items()}
    assert codes == {"another account's address": "EMAIL_TAKEN", "another account's username": "EMAIL_TAKEN", "a free address": None, "its own address": None, "its own username": None}
    print_success("taken: another account's address or username; free otherwise")


@pytest.mark.asyncio
async def test_email_refusal_reserves_the_owners_address_unless_the_command_line_asks(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-010 — the address the host named for the owner of a managed instance (A-64 (a)): ``email_refusal`` refuses it to any account other than the recorded owner by default (``reserve_owner_address=True``, the Profile), accepts it with ``reserve_owner_address=False`` (the command line), and never refuses it to the owner's own account."""
    print_section("EMC-010: email_refusal and the owner's reserved address")
    _managed(monkeypatch, OWNER_ADDRESS)
    owner = await _add_user(engine, admin=True, instance_owner=True)
    user = await _add_user(engine)

    async with AsyncSession(engine) as session:
        account, owner_account = await session.get(User, user.id), await session.get(User, owner.id)
        from_profile = await user_service.email_refusal(session, account, OWNER_ADDRESS)
        from_cli = await user_service.email_refusal(session, account, OWNER_ADDRESS, reserve_owner_address=False)
        for_the_owner = await user_service.email_refusal(session, owner_account, OWNER_ADDRESS)

    assert (from_profile.code if from_profile else None, from_cli, for_the_owner) == ("EMAIL_TAKEN", None, None)
    print_success("reserved from Profile; free from the command line and for the owner")


@pytest.mark.asyncio
async def test_move_email_moves_the_address_and_ends_what_the_old_one_could_do(engine: AsyncEngine) -> None:
    """EMC-011 — ``move_email(session, user, address, *, verified_at)``: the address moved, ``email_verified_at`` set to ``verified_at`` (None: not verified), the session version raised, and every live password-reset, setup and email-change link of the account revoked — the host's too, as ``update_profile`` always did. Not committed."""
    print_section("EMC-011: move_email")
    user = await _add_user(engine)
    own, host = await _both_links(engine, user.id)
    moment = utcnow()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        reset = await user_service.create_password_reset(session, await session.get(User, user.id))
        await session.commit()
    before = (await _account(engine, user.id)).session_version

    async with AsyncSession(engine, expire_on_commit=False) as session:
        account = await session.get(User, user.id)
        await user_service.move_email(session, account, NEW_ADDRESS, verified_at=moment)
        await session.rollback()
    assert (await _account(engine, user.id)).email == user.email, "not committed: a rollback undoes it"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        account = await session.get(User, user.id)
        await user_service.move_email(session, account, NEW_ADDRESS, verified_at=moment)
        await session.commit()

    moved = await _account(engine, user.id)
    assert (moved.email, ensure_utc(moved.email_verified_at), moved.session_version) == (NEW_ADDRESS, ensure_utc(moment), before + 1)
    assert (await _status(engine, own), await _status(engine, host)) == (TokenStatus.REVOKED, TokenStatus.REVOKED)
    async with AsyncSession(engine) as session:
        assert (await token_service.inspect_token(session, reset.token, AccountTokenPurpose.PASSWORD_RESET)).status is TokenStatus.REVOKED
    print_success("moved, verified, sessions ended, links revoked")


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None
    return user

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

- THE SERVICE (step 2.3, ``services/accounts/email_change.py``) — a request issues one 24-hour Profile link and changes
  nothing on the account; the confirmation goes to the new address, the notice to the old one. A refused send leaves
  nothing waiting and spends no limit. Limits: 5 confirmations an hour per account, a resend not within 60 seconds, 3 an
  hour per new mailbox, the instance's budget — each refusal before any write. A taken address is refused. A resend
  revokes the old link only after its email went. The click (D10): a dead link says why to anyone; a live one needs the
  session of its account, and without it nothing is written; with it the address moves, verified, the sessions end; of two
  clicks one wins; a condition failed at the click (address taken, inactive, protected, not the account's link) revokes the
  link. ``link_flow`` and ``pending_ids`` read the creator. The owner flow's state is untouched; no log line holds an
  address or a token.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all``; ``get_async_engine`` is a
tripwire; the profile and the owner's variable are set with ``monkeypatch``. No server and no SMTP: the service's
``send_email`` is an outbox, the transport a tripwire, every limit a private one. No clock wait: every call that counts
time gets its ``now``.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlsplit

import pytest
import pytest_asyncio
from fastapi import Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.config import get_settings
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.schemas.auth import ChangePasswordRequest
from backend.app.services.accounts import auth_service, email_change, instance_owner, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import TokenStatus
from backend.app.services.email import delivery, smtp
from backend.app.services.email.delivery import EmailDeliveryError, EmailRateLimitedError
from backend.app.services.email.messages import EmailContent, EmailKind
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
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


# =============================================================================
# 3. THE PROFILE CHANGE SERVICE (step 2.3: services/accounts/email_change.py)
# =============================================================================

SMTP_HOST = "smtp.zq-emc.example.com"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
PUBLIC_URL = "https://folio.zq-emc.example.com"
#: Another mailbox for every request of a test that must not meet the per-mailbox limit.
OTHER_MAILBOXES = tuple(f"zq.box{index}@zq-emc-{index}.example.org" for index in range(8))


@dataclass(frozen=True)
class SentEmail:
    content: EmailContent
    to: str
    user_id: Optional[int]


class Outbox:
    """Stands in for ``send_email`` in ``email_change``: records every attempt, then raises ``failure`` when one is set."""

    def __init__(self) -> None:
        self.attempts: list[SentEmail] = []
        self.failure: Optional[BaseException] = None

    async def send_email(self, content: EmailContent, *, to: str, user_id: Optional[int] = None) -> None:
        self.attempts.append(SentEmail(content=content, to=to, user_id=user_id))
        if self.failure is not None:
            raise self.failure


@pytest.fixture(autouse=True)
def private_owner_knowledge(monkeypatch: pytest.MonkeyPatch) -> None:
    """What the process knows of the recorded owner is put back after the test (``account_protection`` reads it)."""
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """Email on (SMTP and ``LIBREFOLIO_PUBLIC_URL``), sent into an outbox; the SMTP transport a tripwire; every limit private."""
    monkeypatch.setenv("LIBREFOLIO_SMTP_HOST", SMTP_HOST)
    monkeypatch.setenv("LIBREFOLIO_SMTP_FROM", SENDER_HEADER)
    monkeypatch.setenv("LIBREFOLIO_PUBLIC_URL", PUBLIC_URL)

    def refuse(_server: object, _message: object) -> None:
        raise AssertionError("an email-change test reached the SMTP transport: email_change must send through send_email, imported by name")

    monkeypatch.setattr(smtp, "deliver", refuse)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))
    monkeypatch.setattr(email_change, "EMAIL_CHANGE_LINKS_BY_MAILBOX", SlidingWindowLimiter(3, 3600))
    monkeypatch.setattr(email_change, "EMAIL_CHANGE_REQUESTED_BY_MAILBOX", SlidingWindowLimiter(3, 3600))
    box = Outbox()
    monkeypatch.setattr(email_change, "send_email", box.send_email)
    return box


async def _ask(engine: AsyncEngine, user_id: int, address: str = NEW_ADDRESS, *, now: Optional[datetime] = None) -> email_change.PendingEmailChange:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await email_change.request_change(session, await session.get(User, user_id), address, now=now)


async def _resend(engine: AsyncEngine, user_id: int, *, now: Optional[datetime] = None) -> email_change.PendingEmailChange:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await email_change.resend(session, await session.get(User, user_id), now=now)


async def _confirm(engine: AsyncEngine, token: str, acting_user_id: Optional[int], *, now: Optional[datetime] = None) -> email_change.ConfirmedProfileChange:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await email_change.confirm_profile_change(session, token, acting_user_id=acting_user_id, now=now)


async def _rows(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    async with AsyncSession(engine) as session:
        statement = select(AccountToken).where(AccountToken.purpose == CHANGE, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


def _token_of(sent: SentEmail) -> str:
    """The token the confirmation email carries: the fragment of the link on its own line of the plain text."""
    link = next(line for line in sent.content.text.splitlines() if line.startswith(PUBLIC_URL))
    assert urlsplit(link).path == "/confirm-email-change", f"the link opens the change page: {link}"
    return parse_qs(urlsplit(link).fragment)["token"][0]


@pytest.mark.asyncio
async def test_a_request_issues_a_24_hour_profile_link_and_changes_nothing_on_the_account(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-020 — ``request_change``: one live link of 24 hours carrying the new address and marked as the account's own (``created_by_user_id``); the account's address, its verification and its sessions unchanged; the confirmation (kind ``email_change_request``) goes to the NEW address, its link opening ``/confirm-email-change`` with that token; ``pending`` gives the address and the expiry. The notice to the OLD address goes from ``email_change_requested_work``, without the new address."""
    print_section("EMC-020: a request")
    user = await _add_user(engine)
    before = await _account(engine, user.id)
    moment = utcnow()

    waiting = await _ask(engine, user.id, now=moment)

    rows = await _rows(engine, user.id)
    assert len(rows) == 1 and (rows[0].email, rows[0].created_by_user_id, rows[0].revoked_at, rows[0].consumed_at) == (NEW_ADDRESS, user.id, None, None)
    assert ensure_utc(rows[0].expires_at) - ensure_utc(rows[0].created_at) == PROFILE_TTL
    after = await _account(engine, user.id)
    assert (after.email, after.email_verified_at, after.session_version) == (before.email, before.email_verified_at, before.session_version), "nothing on the account changes before the click"
    assert [(sent.to, sent.content.kind) for sent in outbox.attempts] == [(NEW_ADDRESS, EmailKind.EMAIL_CHANGE_REQUEST)]
    assert token_service.hash_token(_token_of(outbox.attempts[0])) == rows[0].token_hash, "the emailed link is the issued one"
    assert (waiting.email, waiting.expires_at) == (NEW_ADDRESS, ensure_utc(rows[0].expires_at))
    async with AsyncSession(engine) as session:
        assert await email_change.pending(session, user.id) == waiting

    await email_change.email_change_requested_work(user.id, user.email, engine=engine)
    notice = outbox.attempts[-1]
    assert (notice.to, notice.content.kind, len(outbox.attempts)) == (user.email, EmailKind.EMAIL_CHANGE_REQUEST, 2)
    assert NEW_ADDRESS.split("@")[0] not in notice.content.text and "://" not in notice.content.text, "the notice holds no link and nothing of the new address"
    print_success("one 24-hour link, nothing changed, confirmation to the new address, notice to the old one")


@pytest.mark.asyncio
async def test_a_refused_send_leaves_nothing_waiting_and_spends_no_limit(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-021 — the SMTP server refuses the confirmation: ``EmailDeliveryError`` raised; the new link revoked and without its address; an earlier request (another address) revoked too — nothing waits; and the next request is admitted at once (a failed send spends no limit)."""
    print_section("EMC-021: a refused send")
    user = await _add_user(engine)
    await _ask(engine, user.id, OTHER_MAILBOXES[0])
    outbox.failure = EmailDeliveryError(smtp.SmtpErrorCode.RECIPIENT_REFUSED)

    with pytest.raises(EmailDeliveryError):
        await _ask(engine, user.id, OTHER_MAILBOXES[1])

    first, failed = await _rows(engine, user.id)
    assert (failed.email, failed.revoked_at is not None) == (None, True), "the failed link is revoked and loses its address"
    assert first.revoked_at is not None, "the earlier request stays revoked: nothing waits"
    async with AsyncSession(engine) as session:
        assert await email_change.pending(session, user.id) is None
    outbox.failure = None
    for index in range(2, 6):  # 1 sent + 4 = the 5 of the hour: the failed one counted nothing
        await _ask(engine, user.id, OTHER_MAILBOXES[index])
    print_success("revoked without address, nothing waits, the limit untouched")


@pytest.mark.asyncio
async def test_the_account_limit_is_five_confirmations_an_hour(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-022 — per account, counted on its rows that carry an address: five requests in an hour go, the sixth is ``EmailRateLimitedError`` and writes no row; an hour after the first, one more goes."""
    print_section("EMC-022: five an hour per account")
    user = await _add_user(engine)
    moment = utcnow()
    for index in range(5):
        await _ask(engine, user.id, OTHER_MAILBOXES[index], now=moment + timedelta(minutes=index))
    rows = len(await _rows(engine, user.id))

    with pytest.raises(EmailRateLimitedError):
        await _ask(engine, user.id, OTHER_MAILBOXES[5], now=moment + timedelta(minutes=10))
    assert len(await _rows(engine, user.id)) == rows, "a refused request writes no row"
    await _ask(engine, user.id, OTHER_MAILBOXES[6], now=moment + timedelta(hours=1, seconds=1))
    print_success("the sixth refused, nothing written; free again after the hour")


@pytest.mark.asyncio
async def test_the_mailbox_limit_and_the_instance_budget_refuse_before_writing(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-023 — three requests of three accounts to one new mailbox (its aliases count together) go; the fourth is refused with no row. A spent hourly budget of the instance refuses too, with no row: never a fallback to the immediate change."""
    print_section("EMC-023: the mailbox limit and the budget")
    users = [await _add_user(engine) for _ in range(5)]
    for index, alias in enumerate(("zq.shared@zq-emc.example.net", "ZQ.Shared+a@zq-emc.example.net", "zq.shared+b@zq-emc.example.net")):
        await _ask(engine, users[index].id, alias)
    with pytest.raises(EmailRateLimitedError):
        await _ask(engine, users[3].id, "zq.shared+c@zq-emc.example.net")
    assert await _rows(engine, users[3].id) == []

    monkeypatch.setenv("LIBREFOLIO_SMTP_MAX_PER_HOUR", "1")
    delivery.INSTANCE_BUDGET.hit(limit=1)
    with pytest.raises(EmailRateLimitedError):
        await _ask(engine, users[4].id, OTHER_MAILBOXES[0])
    assert await _rows(engine, users[4].id) == []
    print_success("the fourth to one mailbox refused; a spent budget refuses; no rows")


@pytest.mark.asyncio
async def test_admit_request_refuses_a_taken_address_and_writes_nothing(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-024 — ``admit_request`` and ``request_change``: another account's address, another account's username and the owner's reserved address are ``EmailChangeRefusedError("EMAIL_TAKEN")``, with no row and no email; the account's own address is a ``ValueError`` (no change to ask for)."""
    print_section("EMC-024: a taken address")
    _managed(monkeypatch, OWNER_ADDRESS)
    other = await _add_user(engine)
    user = await _add_user(engine)
    for taken in (other.email, other.username, OWNER_ADDRESS):
        with pytest.raises(email_change.EmailChangeRefusedError) as refused:
            await _ask(engine, user.id, taken)
        assert refused.value.code == "EMAIL_TAKEN"
    with pytest.raises(ValueError):
        await _ask(engine, user.id, user.email.upper())
    assert (await _rows(engine, user.id), outbox.attempts) == ([], [])
    print_success("EMAIL_TAKEN three ways; own address a ValueError; nothing written")


@pytest.mark.asyncio
async def test_a_resend_waits_60_seconds_and_revokes_the_old_link_only_after_the_send(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-025 — ``resend``: within 60 seconds of the last email it is ``EmailRateLimitedError``; after, a new token for the same address, the old one revoked. A resend whose email fails drops its own link and leaves the old one valid. Nothing waiting → ``EmailChangeNotPendingError``."""
    print_section("EMC-025: resend")
    user = await _add_user(engine)
    moment = utcnow()
    await _ask(engine, user.id, now=moment)
    first = _token_of(outbox.attempts[-1])

    with pytest.raises(EmailRateLimitedError):
        await _resend(engine, user.id, now=moment + timedelta(seconds=30))
    outbox.failure = EmailDeliveryError(smtp.SmtpErrorCode.TIMEOUT)
    with pytest.raises(EmailDeliveryError):
        await _resend(engine, user.id, now=moment + timedelta(seconds=61))
    assert await _status(engine, first) is TokenStatus.VALID, "a failed resend leaves the old link valid"
    outbox.failure = None
    again = await _resend(engine, user.id, now=moment + timedelta(seconds=62))
    second = _token_of(outbox.attempts[-1])

    assert (second != first, again.email, outbox.attempts[-1].to) == (True, NEW_ADDRESS, NEW_ADDRESS)
    assert (await _status(engine, first), await _status(engine, second)) == (TokenStatus.REVOKED, TokenStatus.VALID)
    async with AsyncSession(engine) as session:
        await email_change.cancel(session, user.id)
    with pytest.raises(email_change.EmailChangeNotPendingError):
        await _resend(engine, user.id, now=moment + timedelta(minutes=5))
    print_success("60 s; new token then old revoked; failed resend keeps the old; nothing pending → error")


@pytest.mark.asyncio
async def test_a_resend_to_an_address_taken_meanwhile_revokes_the_request(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-026 — the address the account waits for was taken by another account meanwhile: ``resend`` is ``EmailChangeRefusedError("EMAIL_TAKEN")``, no email, and the waiting link revoked."""
    print_section("EMC-026: resend to a taken address")
    user = await _add_user(engine)
    moment = utcnow()
    await _ask(engine, user.id, now=moment)
    token = _token_of(outbox.attempts[-1])
    await _add_user(engine, email=NEW_ADDRESS)

    with pytest.raises(email_change.EmailChangeRefusedError) as refused:
        await _resend(engine, user.id, now=moment + timedelta(minutes=2))

    assert (refused.value.code, len(outbox.attempts), await _status(engine, token)) == ("EMAIL_TAKEN", 1, TokenStatus.REVOKED)
    print_success("refused, nothing sent, the request revoked")


@pytest.mark.asyncio
async def test_cancel_revokes_the_request_and_is_idempotent(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-027 — ``cancel``: the waiting link revoked, ``pending`` None; a second cancel is no error and sends nothing."""
    print_section("EMC-027: cancel")
    user = await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])

    for _ in range(2):
        async with AsyncSession(engine) as session:
            await email_change.cancel(session, user.id)

    async with AsyncSession(engine) as session:
        assert await email_change.pending(session, user.id) is None
    assert (await _status(engine, token), len(outbox.attempts)) == (TokenStatus.REVOKED, 1)
    print_success("revoked, nothing pending, twice without error")


@pytest.mark.asyncio
async def test_a_click_without_the_accounts_session_writes_nothing(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-028 — D10: a live link clicked with no session (``acting_user_id=None``) or with another account's: ``ProfileEmailChangeSignInRequiredError``, and nothing written — the row neither spent nor revoked, the address and the sessions unchanged. The same link, clicked next by its account, completes the change."""
    print_section("EMC-028: the click needs the account's session")
    user, stranger = await _add_user(engine), await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])
    before = await _account(engine, user.id)

    for acting in (None, stranger.id):
        with pytest.raises(email_change.ProfileEmailChangeSignInRequiredError) as refused:
            await _confirm(engine, token, acting)
        assert refused.value.code == "EMAIL_CHANGE_SIGN_IN_REQUIRED"
    (row,) = await _rows(engine, user.id)
    assert (row.consumed_at, row.revoked_at, await _status(engine, token)) == (None, None, TokenStatus.VALID), "the link is read, never spent or revoked"
    after = await _account(engine, user.id)
    assert (after.email, after.session_version) == (before.email, before.session_version)

    confirmed = await _confirm(engine, token, user.id)
    assert (confirmed.user.email, confirmed.old_email) == (NEW_ADDRESS, before.email)
    print_success("sign in required twice, nothing written; then confirmed by its account")


@pytest.mark.asyncio
async def test_a_dead_link_says_why_to_anyone(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-029 — a dead link answers with its status even with no session: ``unknown`` (never issued), ``expired`` (past 24 hours), ``revoked`` (cancelled, or a password reset since), ``consumed`` (clicked already)."""
    print_section("EMC-029: dead links")
    user = await _add_user(engine)
    moment = utcnow()
    await _ask(engine, user.id, now=moment)
    expired = _token_of(outbox.attempts[-1])
    statuses = {"unknown": "zq-never-issued-token", "expired": expired}

    other = await _add_user(engine)
    await _ask(engine, other.id, OTHER_MAILBOXES[0])
    statuses["revoked"] = _token_of(outbox.attempts[-1])
    async with AsyncSession(engine) as session:
        assert (await user_service.reset_password(session, other.username, NEW_PASSWORD))[0]

    third = await _add_user(engine)
    await _ask(engine, third.id, OTHER_MAILBOXES[1])
    statuses["consumed"] = _token_of(outbox.attempts[-1])
    await _confirm(engine, statuses["consumed"], third.id)

    for status, token in statuses.items():
        with pytest.raises(email_change.ProfileEmailChangeLinkInvalidError) as refused:
            await _confirm(engine, token, None, now=moment + PROFILE_TTL + timedelta(seconds=1) if status == "expired" else None)
        assert refused.value.code == status, f"{status}: got {refused.value.code}"
    print_success("unknown, expired, revoked, consumed — without a session")


@pytest.mark.asyncio
async def test_a_confirmed_change_moves_the_address_verified_and_ends_the_sessions(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-030 — the click with the account's session: the address moved, ``email_verified_at`` the moment of the click, the session version raised once, the account's reset links revoked, the link spent by the account."""
    print_section("EMC-030: a confirmed change")
    user = await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])
    async with AsyncSession(engine, expire_on_commit=False) as session:
        reset = await user_service.create_password_reset(session, await session.get(User, user.id))
        await session.commit()
    before = await _account(engine, user.id)
    moment = utcnow()

    confirmed = await _confirm(engine, token, user.id, now=moment)

    after = await _account(engine, user.id)
    assert (after.email, ensure_utc(after.email_verified_at), after.session_version) == (NEW_ADDRESS, ensure_utc(moment), before.session_version + 1)
    assert (confirmed.user.id, confirmed.old_email) == (user.id, before.email)
    (row,) = await _rows(engine, user.id)
    assert (row.consumed_by_user_id, row.revoked_at) == (user.id, None)
    async with AsyncSession(engine) as session:
        assert (await token_service.inspect_token(session, reset.token, AccountTokenPurpose.PASSWORD_RESET)).status is TokenStatus.REVOKED
    print_success("moved, verified, sessions ended, reset link revoked")


@pytest.mark.asyncio
async def test_of_two_clicks_only_one_wins(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-031 — two clicks of the account at once, each in its own session: one ``ConfirmedProfileChange``, one ``ProfileEmailChangeLinkInvalidError`` (``consumed``), and the session version raised once."""
    print_section("EMC-031: two clicks")
    user = await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])
    before = (await _account(engine, user.id)).session_version

    results = await asyncio.gather(_confirm(engine, token, user.id), _confirm(engine, token, user.id), return_exceptions=True)

    won = [result for result in results if isinstance(result, email_change.ConfirmedProfileChange)]
    lost = [result for result in results if isinstance(result, email_change.ProfileEmailChangeLinkInvalidError)]
    assert (len(won), len(lost)) == (1, 1), f"one wins, one loses: {results!r}"
    assert lost[0].code == "consumed"
    assert (await _account(engine, user.id)).session_version == before + 1
    print_success("one change, one refusal, sessions ended once")


@pytest.mark.asyncio
@pytest.mark.parametrize("taker", ["address", "username", "owner"])
async def test_an_address_taken_before_the_click_revokes_the_link(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, taker: str) -> None:
    """EMC-032 — between request and click the new address became another account's address, another account's username, or the owner's reserved one (D5.4: a waiting address is not reserved): the click is ``revoked``, the link revoked, nothing on the account changes."""
    print_section(f"EMC-032: the address taken as {taker}")
    user = await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])
    if taker == "address":
        await _add_user(engine, email=NEW_ADDRESS)
    elif taker == "username":
        async with AsyncSession(engine) as session:
            session.add(User(username=NEW_ADDRESS, email=f"zq-{unique_id()}@zq-emc.example.com", hashed_password="x"))
            await session.commit()
    else:
        _managed(monkeypatch, NEW_ADDRESS)
    before = await _account(engine, user.id)

    with pytest.raises(email_change.ProfileEmailChangeLinkInvalidError) as refused:
        await _confirm(engine, token, user.id)

    after = await _account(engine, user.id)
    assert (refused.value.code, await _status(engine, token)) == ("revoked", TokenStatus.REVOKED)
    assert (after.email, after.session_version) == (before.email, before.session_version)
    print_success("revoked, nothing changed")


@pytest.mark.asyncio
async def test_an_inactive_protected_or_foreign_link_is_revoked_at_the_click(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-033 — the conditions read after the link is spent: an account made inactive behind the service's back (a direct UPDATE: the service's deactivation revokes the link already, EMC-004), an account that became the protected owner of a managed instance, a link the account did not issue (no creator, or another account as creator, clicked by its account) — each click is ``revoked``, the link revoked, the address unchanged."""
    print_section("EMC-033: inactive, protected, not the account's own")
    inactive, owner, foreign = await _add_user(engine), await _add_user(engine, admin=True), await _add_user(engine)
    tokens = {}
    for name, user, address in (("inactive", inactive, OTHER_MAILBOXES[0]), ("owner", owner, OTHER_MAILBOXES[1])):
        await _ask(engine, user.id, address)
        tokens[name] = (user, _token_of(outbox.attempts[-1]))
    tokens["foreign"] = (foreign, await _issue_change(engine, foreign.id, own=False))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        other_creator = await token_service.issue_token(session, CHANGE, user_id=foreign.id, email=OTHER_MAILBOXES[2], created_by_user_id=owner.id, ttl=PROFILE_TTL)
        await session.commit()
    tokens["other creator"] = (foreign, other_creator.token)
    async with engine.begin() as connection:
        await connection.execute(text("UPDATE users SET is_active = 0 WHERE id = :id"), {"id": inactive.id})
        await connection.execute(text("UPDATE users SET is_instance_owner = 1 WHERE id = :id"), {"id": owner.id})
    _managed(monkeypatch, owner.email)

    for name, (user, token) in tokens.items():
        with pytest.raises(email_change.ProfileEmailChangeLinkInvalidError) as refused:
            await _confirm(engine, token, user.id)
        assert (refused.value.code, await _status(engine, token)) == ("revoked", TokenStatus.REVOKED), name
        assert (await _account(engine, user.id)).email == user.email, name
    print_success("four refusals after the spend, each link revoked")


@pytest.mark.asyncio
async def test_link_flow_and_pending_ids_read_the_creator(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-034 — ``link_flow``: a Profile link is ``profile`` live or spent; the host's link and an unknown token are ``owner``. ``pending_ids``: the accounts with a live Profile link — not one with the host's link alone, an expired request, or a cancelled one."""
    print_section("EMC-034: link_flow and pending_ids")
    waiting, hosted, expired, cancelled = [await _add_user(engine) for _ in range(4)]
    moment = utcnow()
    await _ask(engine, waiting.id, OTHER_MAILBOXES[0])
    own = _token_of(outbox.attempts[-1])
    host = await _issue_change(engine, hosted.id, own=False)
    await _ask(engine, expired.id, OTHER_MAILBOXES[1], now=moment - PROFILE_TTL - timedelta(minutes=1))
    await _ask(engine, cancelled.id, OTHER_MAILBOXES[2])
    async with AsyncSession(engine) as session:
        await email_change.cancel(session, cancelled.id)

    async with AsyncSession(engine) as session:
        flows = [await email_change.link_flow(session, token) for token in (own, host, "zq-unknown")]
        ids = await email_change.pending_ids(session)
    assert flows == ["profile", "owner", "owner"]
    assert waiting.id in ids and not ids & {hosted.id, expired.id, cancelled.id}
    await _confirm(engine, own, waiting.id)
    async with AsyncSession(engine) as session:
        assert await email_change.link_flow(session, own) == "profile", "a spent Profile link is still the Profile flow's"
    print_success("profile / owner / owner; pending_ids exact")


@pytest.mark.asyncio
async def test_verification_mode_follows_the_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-035 — ``verification_mode``: ``immediate`` with email off, and with SMTP but no ``LIBREFOLIO_PUBLIC_URL``; ``verified`` with both."""
    print_section("EMC-035: verification_mode")
    assert await email_change.verification_mode() == "immediate"
    monkeypatch.setenv("LIBREFOLIO_SMTP_HOST", SMTP_HOST)
    monkeypatch.setenv("LIBREFOLIO_SMTP_FROM", SENDER_HEADER)
    assert await email_change.verification_mode() == "immediate"
    monkeypatch.setenv("LIBREFOLIO_PUBLIC_URL", PUBLIC_URL)
    assert await email_change.verification_mode() == "verified"
    print_success("immediate, immediate, verified")


@pytest.mark.asyncio
async def test_the_owner_flow_state_is_untouched_by_a_profile_change(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-036 — a request and its confirmation leave ``instance_owner.startup_change_state()`` and ``owner_change_status()`` as they were: the process waits for the owner's click (``"pending"``), which the owner's confirmation clears and a Profile confirmation must not."""
    print_section("EMC-036: the owner flow untouched")
    monkeypatch.setattr(instance_owner, "_startup_state", "pending")
    user = await _add_user(engine)
    async with AsyncSession(engine) as session:
        before = (instance_owner.startup_change_state(), await instance_owner.owner_change_status(session))

    await _ask(engine, user.id)
    await _confirm(engine, _token_of(outbox.attempts[-1]), user.id)

    async with AsyncSession(engine) as session:
        assert (instance_owner.startup_change_state(), await instance_owner.owner_change_status(session)) == before
    assert before[0] == "pending", "barrier: the owner's state was set"
    print_success(f"unchanged: {before}")


@pytest.mark.asyncio
async def test_no_log_line_holds_an_address_or_a_token(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-037 — a request, a resend, a refused click, a confirmed click, a cancel and the notice: the log lines of the flow (this module's, the token service's, the user service's) hold neither address nor token — and the capture did see the module's lines. ``send_email`` is the outbox here: the delivery's own line is not under test."""
    print_section("EMC-037: nothing secret in the log")
    user, stranger = await _add_user(engine), await _add_user(engine)
    moment = utcnow()
    with capture_logs() as captured:
        await _ask(engine, user.id, now=moment)
        await _resend(engine, user.id, now=moment + timedelta(seconds=61))
        token = _token_of(outbox.attempts[-1])
        with pytest.raises(email_change.ProfileEmailChangeSignInRequiredError):
            await _confirm(engine, token, stranger.id)
        await _confirm(engine, token, user.id)
        await email_change.email_change_requested_work(user.id, user.email, engine=engine)
        async with AsyncSession(engine) as session:
            await email_change.cancel(session, user.id)

    events = [entry["event"] for entry in captured]
    assert any("Email change" in event or "Email changed" in event for event in events), f"the capture saw none of the module's lines: {events}"
    secrets = (NEW_ADDRESS, NEW_ADDRESS.split("@")[0], user.email, token, token_service.hash_token(token))
    leaked = [(entry["event"], secret) for entry in captured for secret in secrets if secret.casefold() in repr(entry).casefold()]
    assert leaked == [], f"a log line holds an address or a token: {leaked}"
    print_success(f"{len(captured)} lines, none with an address or a token")


@pytest.mark.asyncio
async def test_the_unique_index_caught_in_the_savepoint_revokes_the_link_and_undoes_the_change(engine: AsyncEngine, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMC-038 — an account takes the new address after the click's check (here: the check stubbed to pass): the unique index on ``lower(email)`` refuses the move inside the savepoint; the click is ``revoked``, the link revoked, and nothing on the account changed — its address and its session version: the savepoint undid ``end_sessions`` too."""
    print_section("EMC-038: the unique index, inside the savepoint")
    user = await _add_user(engine)
    await _ask(engine, user.id)
    token = _token_of(outbox.attempts[-1])
    await _add_user(engine, email=NEW_ADDRESS.upper())
    before = await _account(engine, user.id)

    async def passes(*_arguments: object, **_keywords: object) -> None:
        return None

    monkeypatch.setattr(user_service, "email_refusal", passes)
    with pytest.raises(email_change.ProfileEmailChangeLinkInvalidError) as refused:
        await _confirm(engine, token, user.id)

    after = await _account(engine, user.id)
    assert (refused.value.code, await _status(engine, token)) == ("revoked", TokenStatus.REVOKED)
    assert (after.email, after.session_version, after.email_verified_at) == (before.email, before.session_version, before.email_verified_at)
    print_success("IntegrityError in the savepoint: revoked, nothing changed")


@pytest.mark.asyncio
async def test_the_requested_notice_has_its_mailbox_limit_and_never_raises(engine: AsyncEngine, outbox: Outbox) -> None:
    """EMC-039 — ``email_change_requested_work``: four notices to one old mailbox in the hour send three (``EMAIL_CHANGE_REQUESTED_BY_MAILBOX``); a refused send, an account gone, email off — none raises."""
    print_section("EMC-039: the requested notice")
    user = await _add_user(engine)
    for _ in range(4):
        await email_change.email_change_requested_work(user.id, user.email, engine=engine)
    assert [sent.to for sent in outbox.attempts] == [user.email] * 3

    other = await _add_user(engine)
    outbox.failure = EmailDeliveryError(smtp.SmtpErrorCode.CONNECTION_FAILED)
    await email_change.email_change_requested_work(other.id, other.email, engine=engine)
    outbox.failure = RuntimeError("zq-unexpected")
    await email_change.email_change_requested_work(other.id, OTHER_MAILBOXES[0], engine=engine)
    await email_change.email_change_requested_work(10**9, OTHER_MAILBOXES[1], engine=engine)
    print_success("three of four; failures swallowed")

"""A5-2: a restore on a managed instance gives the instance to the owner the administrator chose (release 1.3, workstream A).

``instance_owner.assign_owner_and_send_reset(session, user_id, *, now=None)`` is called once by the restore (B), at the first
start after the database swap, with the id — in the restored database — of the account the owner chose. A backup may come
from anywhere, and whoever prepared it writes its tokens too, so NOTHING in the restored database is trusted, the history of
its tokens least of all. Every call gives the full treatment, in ONE transaction under the write lock:

1. the preconditions (``OwnerAssignmentError``: ``NOT_MANAGED``, ``OWNER_EMAIL_NOT_SET``, ``USER_NOT_FOUND``, ``EMAIL_TAKEN`` —
   another account has the address, or has it as its username), before anything is written;
2. the owner mark of every other account cleared, then the chosen account gets the address of ``LIBREFOLIO_ADMIN_EMAIL``,
   administrator, active, the mark, a verified address;
3. its password made unusable (a real bcrypt hash of a random secret), its sessions ended;
4. every token tied to the account neutralised: its ``password_reset`` rows DELETED (the history is unreliable, and a planted
   row dated in the future would block «forgot password» for ever), its live tokens of every other purpose revoked;
5. ONE new password-reset link, marked with the owner's address.

After the commit the link goes by email to that address. If the email cannot go — or fails in any way — the outcome is
``link_only`` and the link is written in the instance's log (a warning), the channel of the hoster, as for the ``/setup`` and the
email-change links; it is never in the result, whose ``repr`` shows no address or name. When the email went, the link is in no
log. A second call (a restart half way) repeats the treatment: the previous link dies, a new one is sent. At-most-once is the
caller's (B keeps it in the restore's state, never in the database).

A5-4 adds the host's remedy for an owner address confirmed by mistake: ``./dev.py user reassign-owner <username>`` (managed
instances only) runs the same treatment from the command line, with the address of ``LIBREFOLIO_ADMIN_EMAIL``; and a change of
an account's address in its profile (``user set-email`` too) also revokes its live ``email_change`` links, as it revokes its
``password_reset`` and ``admin_setup`` ones.

Pure: every database is a private SQLite file under ``tmp_path``; ``instance_owner.send_email`` is an outbox; ``smtp.deliver`` a
tripwire; profile and variables with ``monkeypatch``; the log with ``structlog.testing.capture_logs``.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import importlib
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import get_settings
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import hash_token
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.messages import EmailContent
from backend.app.utils.datetime_utils import ensure_utc
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section

OWNER_MODULE = "backend.app.services.accounts.instance_owner"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
ADMIN_PREFIX = "LIBREFOLIO_ADMIN_"
INHERITED_VARIABLES = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_BLOCKED", PROFILE_VARIABLE)

OWNER_EMAIL = "Owner@zq-assign.example.com"
BACKUP_EMAIL = "someone@other-instance.example.net"
STRANGER_EMAIL = "stranger@zq-assign.example.com"
OLD_PASSWORD = "Backup-Known-Pass-2026"
PUBLIC_URL = "https://folio.zq-assign.example.com:8443/app"
SMTP_HOST = "smtp.zq-assign.example.com"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
NOW = datetime(2026, 1, 15, 9, 30, 0, tzinfo=UTC)
RESET = AccountTokenPurpose.PASSWORD_RESET
RESET_PAGE = "/reset-password"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith((ADMIN_PREFIX, SMTP_PREFIX)) or name in INHERITED_VARIABLES:
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
    try:
        module = importlib.import_module(OWNER_MODULE)
    except Exception:  # the tests that need the module say why
        return
    if hasattr(module, "get_async_engine"):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire)


@pytest.fixture(autouse=True)
def no_smtp_conversation(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    attempts: list[str] = []

    def refuse(_server: object, message: object) -> None:
        attempts.append(type(message).__name__)
        raise AssertionError("an owner-assignment test reached the SMTP transport")

    monkeypatch.setattr(smtp, "deliver", refuse)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))
    yield attempts
    assert attempts == []


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'assign.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def owner() -> ModuleType:
    try:
        module = importlib.import_module(OWNER_MODULE)
    except ModuleNotFoundError as missing:
        if missing.name == OWNER_MODULE:
            pytest.fail(f"red until A5-2: {OWNER_MODULE} does not exist", pytrace=False)
        raise
    if not hasattr(module, "assign_owner_and_send_reset"):
        pytest.fail("red until A5-2: instance_owner has no assign_owner_and_send_reset", pytrace=False)
    return module


@dataclass(frozen=True)
class SentEmail:
    content: EmailContent
    to: str
    user_id: Optional[int]


class Outbox:
    def __init__(self) -> None:
        self.attempts: list[SentEmail] = []
        self.failure: Optional[BaseException] = None

    async def send_email(self, content: EmailContent, *, to: str, user_id: Optional[int] = None) -> None:
        self.attempts.append(SentEmail(content=content, to=to, user_id=user_id))
        if self.failure is not None:
            raise self.failure


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> Outbox:
    box = Outbox()
    monkeypatch.setattr(owner, "send_email", box.send_email)
    return box


# =============================================================================
# HELPERS
# =============================================================================


def _managed(monkeypatch: pytest.MonkeyPatch, *, variable: Optional[str] = OWNER_EMAIL, profile: str = "managed") -> None:
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if variable is not None:
        monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, variable)
    assert get_settings().LIBREFOLIO_PROFILE == profile, "barrier: get_settings() must read the profile this test sets"


def _email_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{SMTP_PREFIX}HOST", SMTP_HOST)
    monkeypatch.setenv(f"{SMTP_PREFIX}FROM", SENDER_HEADER)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


async def _add_user(engine: AsyncEngine, username: str, email: str, *, admin: bool = False, active: bool = True, flag: bool = False) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(OLD_PASSWORD), is_active=active, is_superuser=admin)
        if flag:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user.id


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None
    return user


async def _resets(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    statement = select(AccountToken).where(AccountToken.purpose == RESET, AccountToken.user_id == user_id).order_by(AccountToken.id)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return list((await session.execute(statement)).scalars().all())


def _live(row: AccountToken, moment: datetime) -> bool:
    return row.consumed_at is None and row.revoked_at is None and ensure_utc(row.expires_at) > moment


async def _assign(owner: ModuleType, engine: AsyncEngine, user_id: int, **keywords: Any) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await owner.assign_owner_and_send_reset(session, user_id, **keywords)


async def _issue(engine: AsyncEngine, user_id: int, *, email: Optional[str], now: datetime = NOW) -> Any:
    """A reset link written as a row, marked with ``email`` or not."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, RESET, user_id=user_id, email=email, now=now)
        await session.commit()
    return issued


async def _snapshot(engine: AsyncEngine) -> dict[str, list[Any]]:
    async with engine.connect() as connection:
        users = (await connection.execute(text("SELECT * FROM users ORDER BY id"))).mappings().all()
        tokens = (await connection.execute(text("SELECT * FROM account_tokens ORDER BY id"))).mappings().all()
    return {"users": [dict(row) for row in users], "tokens": [dict(row) for row in tokens]}


def _log_text(events: list[dict[str, Any]]) -> str:
    return "\n".join(str(event) for event in events)


async def _scene(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, *, ready: bool = True) -> int:
    """A managed instance whose variable is OWNER_EMAIL, and the account the owner chose in the restored backup: an ordinary,
    active account of another instance, with a password the preparer of the backup knows. Its id."""
    _managed(monkeypatch)
    if ready:
        _email_ready(monkeypatch)
    return await _add_user(engine, "assign_chosen", BACKUP_EMAIL)


# =============================================================================
# THE UNUSABLE HASH
# =============================================================================


def test_the_unusable_hash_is_a_bcrypt_hash_nobody_can_match() -> None:
    """A52-001: ``unusable_password_hash()`` is a valid bcrypt hash (of the cost every password gets) of a random secret: two calls differ, no plausible password verifies, and ``verify_password_or_dummy`` answers False."""
    print_section("A52-001: unusable_password_hash")
    make = getattr(auth_service, "unusable_password_hash", None)
    assert make is not None, "red until A5-2: auth_service has no unusable_password_hash"
    first, second = make(), make()
    assert first != second
    for hashed in (first, second):
        assert hashed.startswith("$2") and len(hashed) == 60
        assert hashed.split("$")[2] == f"{auth_service.BCRYPT_ROUNDS:02d}"
        for attempt in ("", "password", OLD_PASSWORD, "Admin123!", "a" * 72, hashed):
            assert auth_service.verify_password(attempt, hashed) is False
            assert auth_service.verify_password_or_dummy(attempt, hashed) is False


# =============================================================================
# THE ASSIGNMENT
# =============================================================================


@pytest.mark.asyncio
async def test_the_chosen_account_becomes_the_owner_and_gets_a_link(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-010: the chosen account gets the owner's address (as the variable writes it), is an active administrator, the instance owner, verified; its password is unusable and its sessions end; ONE reset link marked with the owner's address is issued and emailed to that address (``sent``); the account is protected, the status is ``None``, the log holds no token."""
    print_section("A52-010: a new assignment")
    user_id = await _scene(engine, monkeypatch)
    before = await _account(engine, user_id)

    with capture_logs() as events:
        result = await _assign(owner, engine, user_id, now=NOW)

    assert result.outcome == "sent" and not hasattr(result, "reset_path")
    assert (result.user_id, result.username, result.email) == (user_id, "assign_chosen", OWNER_EMAIL)
    after = await _account(engine, user_id)
    assert (after.email, after.is_superuser, after.is_active, after.is_instance_owner) == (OWNER_EMAIL, True, True, True)
    assert after.email_verified_at is not None
    assert after.session_version == before.session_version + 1, "its sessions end"
    assert auth_service.verify_password(OLD_PASSWORD, after.hashed_password) is False, "the old password no longer opens the account"
    assert auth_service.verify_password_or_dummy(OLD_PASSWORD, after.hashed_password) is False
    rows = await _resets(engine, user_id)
    assert len(rows) == 1 and _live(rows[0], NOW) and rows[0].email == OWNER_EMAIL
    assert ensure_utc(result.expires_at) == ensure_utc(rows[0].expires_at)
    assert [(mail.to, mail.user_id, mail.content.kind) for mail in outbox.attempts] == [(OWNER_EMAIL, user_id, "password_reset")]
    link = next(line.strip() for line in outbox.attempts[0].content.text.splitlines() if line.startswith("http"))
    assert link.startswith(f"{PUBLIC_URL}{RESET_PAGE}#token=")
    token = link.split("token=", 1)[1]
    assert hash_token(token) == rows[0].token_hash
    assert token not in _log_text(events), "no token in the log"
    assert user_service.account_protection(after) == user_service.PAYING_ADMINISTRATOR
    async with AsyncSession(engine) as session:
        assert await owner.owner_change_status(session) is None, "the address is the variable's: no change pending"
    assert user_service._recorded_owner == user_id


@pytest.mark.asyncio
async def test_the_flag_of_every_other_account_is_cleared(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-011: the backup's own owner (flag on another account, even one with the owner's address) loses the flag first; afterwards the chosen account is the only owner, and the other is no longer protected."""
    user_id = await _scene(engine, monkeypatch)
    backup_owner = await _add_user(engine, "assign_backup_owner", "backup.owner@other-instance.example.net", admin=True, flag=True)

    await _assign(owner, engine, user_id, now=NOW)

    async with engine.connect() as connection:
        owners = list((await connection.execute(text("SELECT id FROM users WHERE is_instance_owner = 1"))).scalars().all())
    assert owners == [user_id]
    assert user_service.account_protection(await _account(engine, backup_owner)) is None


@pytest.mark.asyncio
async def test_a_chosen_account_that_is_inactive_or_not_an_administrator_becomes_both(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-012: the chosen account may be an ordinary or an inactive account of the backup: after the call it is an active administrator."""
    _managed(monkeypatch)
    _email_ready(monkeypatch)
    user_id = await _add_user(engine, "assign_inactive", BACKUP_EMAIL, admin=False, active=False)

    await _assign(owner, engine, user_id, now=NOW)

    after = await _account(engine, user_id)
    assert (after.is_superuser, after.is_active) == (True, True)


# =============================================================================
# THE PRECONDITIONS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["NOT_MANAGED", "OWNER_EMAIL_NOT_SET", "USER_NOT_FOUND", "EMAIL_TAKEN_BY_EMAIL", "EMAIL_TAKEN_BY_USERNAME"])
async def test_a_missing_precondition_raises_and_changes_nothing(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """A52-020: each of the four codes — the address taken by email in any A–Z case, or as a username —, raised before any write: no row changed, no token, no email."""
    print_section(f"A52-020: {case}")
    user_id = await _scene(engine, monkeypatch)
    expected = case.split("_BY_")[0]
    if case == "NOT_MANAGED":
        _managed(monkeypatch, profile="selfhosted")
    elif case == "OWNER_EMAIL_NOT_SET":
        monkeypatch.delenv(ADMIN_EMAIL_VARIABLE)
    elif case == "USER_NOT_FOUND":
        user_id += 999
    elif case == "EMAIL_TAKEN_BY_EMAIL":
        await _add_user(engine, "assign_other", OWNER_EMAIL.upper().replace("ZQ-ASSIGN.EXAMPLE.COM", "zq-assign.example.com"))
    else:
        await _add_user(engine, OWNER_EMAIL, "unrelated@zq-assign.example.com")  # a username from before A-21a that is the address
    before = await _snapshot(engine)

    with pytest.raises(owner.OwnerAssignmentError) as raised:
        await _assign(owner, engine, user_id, now=NOW)

    assert raised.value.code == expected
    assert await _snapshot(engine) == before and outbox.attempts == []


# =============================================================================
# THE HISTORY OF TOKENS IS NOT TRUSTED (the attacks of the review)
# =============================================================================


async def _plant(engine: AsyncEngine, user_id: int, *, purpose: AccountTokenPurpose = RESET, email: Optional[str] = OWNER_EMAIL, created: datetime = NOW, state: str = "live") -> Any:
    """A token written as a row by whoever prepared the backup: ``state`` live, consumed, revoked or expired."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, user_id=user_id, email=email, now=created)
        await session.commit()
    stamp = "2026-01-15 09:31:00.000000"
    column = {"consumed": "consumed_at", "revoked": "revoked_at"}.get(state)
    async with engine.begin() as connection:
        if column is not None:
            await connection.execute(text(f"UPDATE account_tokens SET {column} = :moment WHERE id = :id"), {"moment": stamp, "id": issued.record.id})
        if state == "expired":
            await connection.execute(text("UPDATE account_tokens SET expires_at = :moment WHERE id = :id"), {"moment": "2026-01-01 00:00:00.000000", "id": issued.record.id})
    return issued


async def _hash(engine: AsyncEngine, user_id: int) -> str:
    return (await _account(engine, user_id)).hashed_password


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["consumed", "revoked", "expired", "live"])
async def test_a_planted_marked_token_never_keeps_the_backup_s_password(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    """A52-030 (attacks i, ii): the backup carries a reset token marked with the owner's address — consumed with its date in the FUTURE, revoked, expired or live — for the account chosen, which may already look assigned. The history decides nothing: the password the backup carried is unusable afterwards, the sessions ended, the planted row gone, one new live link."""
    print_section(f"A52-030: a planted {state} token")
    _managed(monkeypatch)
    _email_ready(monkeypatch)
    assigned = state in ("revoked", "expired")
    user_id = await _add_user(engine, "assign_chosen", OWNER_EMAIL if assigned else BACKUP_EMAIL, admin=assigned, flag=assigned)
    planted = await _plant(engine, user_id, created=NOW + timedelta(days=365) if state == "consumed" else NOW - timedelta(days=2), state=state)
    before = await _account(engine, user_id)

    result = await _assign(owner, engine, user_id, now=NOW)

    assert result.outcome == "sent"
    after = await _account(engine, user_id)
    assert auth_service.verify_password(OLD_PASSWORD, after.hashed_password) is False, "the backup's password does not open the owner's account"
    assert after.hashed_password != before.hashed_password and after.session_version == before.session_version + 1
    rows = await _resets(engine, user_id)
    assert planted.record.token_hash not in [row.token_hash for row in rows], "the planted row is gone"
    assert len(rows) == 1 and _live(rows[0], NOW) and rows[0].email == OWNER_EMAIL


@pytest.mark.asyncio
async def test_a_planted_live_token_with_a_known_plaintext_spends_nothing(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-031 (attack iii): a live marked reset token whose plaintext the attacker knows: after the call it is deleted — unknown to the token service — and using it sets no password."""
    user_id = await _scene(engine, monkeypatch)
    known = await _plant(engine, user_id, created=NOW)

    await _assign(owner, engine, user_id, now=NOW + timedelta(minutes=1))

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert (await token_service.inspect_token(session, known.token, RESET, now=NOW + timedelta(minutes=2))).status == token_service.TokenStatus.UNKNOWN
        assert await user_service.complete_password_reset(session, known.token, "Attacker-Chosen-Pass-2026!", now=NOW + timedelta(minutes=2)) is None
    chosen = await _account(engine, user_id)
    assert auth_service.verify_password("Attacker-Chosen-Pass-2026!", chosen.hashed_password) is False
    assert auth_service.verify_password(OLD_PASSWORD, chosen.hashed_password) is False


@pytest.mark.asyncio
async def test_planted_future_tokens_do_not_block_forgot_password(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-032 (attack iv): reset tokens dated in the future, planted for the account, hold «forgot password» back for ever (``_recent_resets`` counts them). After the call they are gone: ten minutes later the owner is not held back."""
    user_id = await _scene(engine, monkeypatch)
    for number in range(4):
        await _plant(engine, user_id, email=None, created=NOW + timedelta(days=30 + number))
    later = NOW + timedelta(minutes=10)
    async with AsyncSession(engine) as session:
        assert await flows._held_back(session, user_id, later) is not None, "barrier: before the call the planted tokens hold the account back"

    await _assign(owner, engine, user_id, now=NOW)

    assert len(await _resets(engine, user_id)) == 1, "only the new link is left"
    async with AsyncSession(engine) as session:
        assert await flows._held_back(session, user_id, later) is None, "the owner can ask «forgot password» again"


@pytest.mark.asyncio
async def test_the_live_tokens_of_every_other_purpose_of_the_account_are_revoked(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-033: the account's live ``email_verification``, ``admin_setup`` and ``email_change`` tokens are revoked; another account's tokens are not touched."""
    user_id = await _scene(engine, monkeypatch)
    bystander = await _add_user(engine, "assign_bystander", STRANGER_EMAIL)
    planted = [await _plant(engine, user_id, purpose=purpose, email=None, created=NOW) for purpose in (AccountTokenPurpose.EMAIL_VERIFICATION, AccountTokenPurpose.ADMIN_SETUP, AccountTokenPurpose.EMAIL_CHANGE)]
    other = await _plant(engine, bystander, purpose=AccountTokenPurpose.EMAIL_VERIFICATION, email=None, created=NOW)

    await _assign(owner, engine, user_id, now=NOW + timedelta(minutes=1))

    async with AsyncSession(engine, expire_on_commit=False) as session:
        for token in planted:
            status = (await token_service.inspect_token(session, token.token, token.record.purpose, now=NOW + timedelta(minutes=2))).status
            assert status == token_service.TokenStatus.REVOKED, token.record.purpose
        assert (await token_service.inspect_token(session, other.token, AccountTokenPurpose.EMAIL_VERIFICATION, now=NOW + timedelta(minutes=2))).status == token_service.TokenStatus.VALID


@pytest.mark.asyncio
async def test_a_second_call_starts_again_and_the_first_link_dies(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-034: a restart half way calls it twice: the second does the whole treatment again — a new unusable hash, the sessions ended again, the first link dead, ONE reset row, a live new link — and two emails go in all."""
    user_id = await _scene(engine, monkeypatch)
    first = await _assign(owner, engine, user_id, now=NOW)
    state = await _account(engine, user_id)
    first_tokens = await _resets(engine, user_id)

    second = await _assign(owner, engine, user_id, now=NOW + timedelta(minutes=1))

    assert (first.outcome, second.outcome) == ("sent", "sent")
    rows = await _resets(engine, user_id)
    assert len(rows) == 1 and rows[0].token_hash != first_tokens[0].token_hash and _live(rows[0], NOW + timedelta(minutes=1))
    after = await _account(engine, user_id)
    assert after.hashed_password != state.hashed_password and auth_service.verify_password(OLD_PASSWORD, after.hashed_password) is False
    assert after.session_version == state.session_version + 1
    assert len(outbox.attempts) == 2
    first_link = next(line for line in outbox.attempts[0].content.text.splitlines() if line.startswith("http")).split("token=", 1)[1]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert (await token_service.inspect_token(session, first_link, RESET, now=NOW + timedelta(minutes=2))).status == token_service.TokenStatus.UNKNOWN


@pytest.mark.asyncio
async def test_two_calls_at_once_are_serialised_and_one_link_is_left(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-035: two calls on two sessions at once: the write lock serialises them, each does the treatment, and ONE live reset link is left (the other was deleted by the one after it)."""
    user_id = await _scene(engine, monkeypatch)

    results = await asyncio.gather(_assign(owner, engine, user_id, now=NOW), _assign(owner, engine, user_id, now=NOW))

    assert [result.outcome for result in results] == ["sent", "sent"]
    rows = await _resets(engine, user_id)
    assert len(rows) == 1 and _live(rows[0], NOW)
    assert len(outbox.attempts) == 2
    async with engine.connect() as connection:
        assert list((await connection.execute(text("SELECT id FROM users WHERE is_instance_owner = 1"))).scalars().all()) == [user_id]


# =============================================================================
# THE DELIVERY: THE LINK IS IN THE EMAIL, OR IN THE INSTANCE'S LOG; NEVER IN THE RESULT
# =============================================================================


def _link_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("log_level") == "warning" and "link" in event]


@pytest.mark.asyncio
async def test_without_email_the_link_is_in_the_instance_log_not_in_the_result(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-040: SMTP off → ``link_only``; no email attempted; ONE warning line of the instance's log carries the link (``/reset-password#token=…`` under the public address when it is set, else the path with a note), and its token is the stored link's; the result holds nothing secret, not even in its ``repr``."""
    print_section("A52-040: link_only")
    user_id = await _scene(engine, monkeypatch, ready=False)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)

    with capture_logs() as events:
        result = await _assign(owner, engine, user_id, now=NOW)

    assert result.outcome == "link_only" and outbox.attempts == []
    lines = _link_lines(events)
    assert len(lines) == 1, events
    assert lines[0]["link"].startswith(f"{PUBLIC_URL}{RESET_PAGE}#token=")
    token = lines[0]["link"].split("token=", 1)[1]
    row = (await _resets(engine, user_id))[0]
    assert hash_token(token) == row.token_hash
    assert not hasattr(result, "reset_path")
    assert token not in repr(result) and not any(token in str(value) for value in vars(result).values())
    assert ensure_utc(result.expires_at) == ensure_utc(row.expires_at)

    # Without a public address: the path alone, with the note
    monkeypatch.delenv(PUBLIC_URL_VARIABLE)
    with capture_logs() as events:
        again = await _assign(owner, engine, user_id, now=NOW + timedelta(minutes=1))
    assert again.outcome == "link_only"
    lines = _link_lines(events)
    assert len(lines) == 1 and lines[0]["link"].startswith(RESET_PAGE) and lines[0].get("note"), events


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["delivery", "limit", "unexpected"])
async def test_an_error_after_the_commit_is_link_only_not_an_exception(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    """A52-041: the SMTP server refuses, the hourly budget is spent, or anything else goes wrong after the commit: ``link_only``, no exception, the committed link live and in the log; the line about the failure is a warning with no traceback and no address."""
    user_id = await _scene(engine, monkeypatch)
    outbox.failure = {
        "delivery": delivery.EmailDeliveryError(smtp.SmtpErrorCode.CONNECTION_FAILED),
        "limit": delivery.EmailRateLimitedError(60.0),
        "unexpected": RuntimeError(f"boom {OWNER_EMAIL}"),
    }[failure]

    with capture_logs() as events:
        result = await _assign(owner, engine, user_id, now=NOW)

    assert result.outcome == "link_only"
    lines = _link_lines(events)
    assert len(lines) == 1
    token = lines[0]["link"].split("token=", 1)[1]
    rows = await _resets(engine, user_id)
    assert len(rows) == 1 and _live(rows[0], NOW) and hash_token(token) == rows[0].token_hash
    failed = [event for event in events if event.get("log_level") == "warning" and "not emailed" in event["event"]]
    assert len(failed) == 1 and "exc_info" not in failed[0], events
    assert OWNER_EMAIL.lower() not in _log_text(events).lower(), "no address in the log"


@pytest.mark.asyncio
async def test_when_the_email_went_the_link_is_in_no_log(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-042: email sent → ``sent``; the token is in no log line, and the result's ``repr`` shows no address and no name."""
    user_id = await _scene(engine, monkeypatch)
    with capture_logs() as events:
        result = await _assign(owner, engine, user_id, now=NOW)
    assert result.outcome == "sent" and _link_lines(events) == []
    token = next(line for line in outbox.attempts[0].content.text.splitlines() if line.startswith("http")).split("token=", 1)[1]
    assert token not in _log_text(events)
    text_of = repr(result)
    assert OWNER_EMAIL not in text_of and "assign_chosen" not in text_of and BACKUP_EMAIL not in text_of
    assert [field.name for field in dataclasses.fields(result)] == ["outcome", "user_id", "username", "email", "expires_at"]


# =============================================================================
# create_password_reset(email=)
# =============================================================================


@pytest.mark.asyncio
async def test_create_password_reset_can_mark_the_link_with_an_address(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A52-060: ``create_password_reset(session, user, email=…)`` stores the address on the link; without it the link carries none, as before."""
    _managed(monkeypatch)
    user_id = await _add_user(engine, "assign_marked", BACKUP_EMAIL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        plain = await user_service.create_password_reset(session, user, now=NOW)
        marked = await user_service.create_password_reset(session, user, now=NOW, email=OWNER_EMAIL)
        await session.commit()
    assert plain.record.email is None and marked.record.email == OWNER_EMAIL


# =============================================================================
# A5-4: user reassign-owner, the host's remedy for a wrong owner address
# =============================================================================

USER_CLI_MODULE = "scripts.user_cli"
WRONG_EMAIL = "wrong-owner@zq-assign.example.org"
CHANGE = AccountTokenPurpose.EMAIL_CHANGE


@pytest.fixture
def user_cli(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> ModuleType:
    """``scripts/user_cli.py`` in this process, its ``get_async_engine`` answering this test's private file."""
    module = importlib.import_module(USER_CLI_MODULE)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine)
    return module


async def _reassign(user_cli: ModuleType, capsys: pytest.CaptureFixture[str], username: str) -> tuple[Any, str]:
    command = getattr(user_cli, "cmd_reassign_owner", None)
    if command is None:
        pytest.fail("red until A5-4: scripts/user_cli.py has no cmd_reassign_owner", pytrace=False)
    capsys.readouterr()
    answer = await command(username)
    return answer, capsys.readouterr().out


async def _wrong_owner_scene(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, *, ready: bool = True) -> tuple[int, int]:
    """The worst case: the owner account holds a WRONG address (an intruder confirmed it), is marked as the owner, and the
    intruder knows its password. Another administrator is there too. Returns (the owner's id, the other's id)."""
    _managed(monkeypatch)
    if ready:
        _email_ready(monkeypatch)
    owner_id = await _add_user(engine, "wrong_owner", WRONG_EMAIL, admin=True, flag=True)
    other_id = await _add_user(engine, "other_admin", STRANGER_EMAIL, admin=True)
    return owner_id, other_id


@pytest.mark.asyncio
async def test_reassign_owner_takes_the_account_back_and_emails_one_link(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """A54-010: the account with the wrong address gets the address of the variable, keeps the owner mark (the others have none), its password stops working, its sessions end, its pending ``email_change`` link dies; ONE reset link goes to the right address; the command answers ✅, prints no link, no token and no address."""
    print_section("A54-010: reassign-owner")
    owner_id, other_id = await _wrong_owner_scene(engine, monkeypatch)
    before = await _account(engine, owner_id)
    pending = await _plant(engine, owner_id, purpose=CHANGE, email=WRONG_EMAIL)

    answer, printed = await _reassign(user_cli, capsys, "wrong_owner")

    assert answer is True and printed.lstrip().startswith("✅"), printed
    after = await _account(engine, owner_id)
    assert (after.email, after.is_superuser, after.is_active, after.is_instance_owner) == (OWNER_EMAIL, True, True, True)
    assert after.session_version == before.session_version + 1
    assert auth_service.verify_password(OLD_PASSWORD, after.hashed_password) is False, "the intruder's password no longer opens the account"
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(AccountToken).where(AccountToken.id == pending.record.id))).scalar_one()
    assert row.revoked_at is not None, "the wrong address's change link is dead"
    assert [(mail.to, mail.content.kind) for mail in outbox.attempts] == [(OWNER_EMAIL, "password_reset")]
    assert len([r for r in await _resets(engine, owner_id) if _live(r, datetime.now(UTC))]) == 1
    link = next(line.strip() for line in outbox.attempts[0].content.text.splitlines() if line.startswith("http"))
    secrets = (link.split("token=", 1)[1], OWNER_EMAIL, WRONG_EMAIL, OWNER_EMAIL.lower())
    assert not any(secret in printed for secret in secrets), printed
    assert (await _account(engine, other_id)).is_instance_owner is False


@pytest.mark.asyncio
async def test_reassign_owner_without_email_leaves_the_link_in_the_log_and_says_so(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """A54-020: email off → the account is taken back all the same; the command answers True (the owner is reassigned), the link is written in the log (shown on the terminal of the command line) as for a restore and NOT printed by the command itself, and the command names ``user reset-link`` for a link printed on the terminal."""
    owner_id, _ = await _wrong_owner_scene(engine, monkeypatch, ready=False)

    with capture_logs() as events:
        answer, printed = await _reassign(user_cli, capsys, "wrong_owner")

    assert answer is True and outbox.attempts == []
    assert (await _account(engine, owner_id)).email == OWNER_EMAIL
    lines = _link_lines(events)
    assert len(lines) == 1, events
    token = lines[0]["link"].split("token=", 1)[1]
    assert token not in printed and "reset-link" in printed and "⚠" in printed, printed


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["not_managed", "no_variable", "unknown_user", "address_taken"])
async def test_reassign_owner_refuses_and_changes_nothing(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """A54-030: not a managed instance, no ``LIBREFOLIO_ADMIN_EMAIL``, an unknown username, another account holding the address → ❌, False, no email, the database exactly as it was."""
    owner_id, other_id = await _wrong_owner_scene(engine, monkeypatch)
    username = "wrong_owner"
    if case == "not_managed":
        monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    elif case == "no_variable":
        monkeypatch.delenv(ADMIN_EMAIL_VARIABLE)
    elif case == "unknown_user":
        username = "nobody_here"
    else:
        await _add_user(engine, "holds_the_address", OWNER_EMAIL.lower())
    before = await _snapshot(engine)

    answer, printed = await _reassign(user_cli, capsys, username)

    assert answer is False and printed.lstrip().startswith("❌"), printed
    assert outbox.attempts == [] and await _snapshot(engine) == before


def test_reassign_owner_is_a_command_of_both_parsers(user_cli: ModuleType) -> None:
    """A54-040: ``reassign-owner <username>`` in ``user_cli.py`` and under ``./dev.py user``; the dispatch runs ``cmd_reassign_owner`` with the username."""
    parser = argparse.ArgumentParser(prog="user_cli.py")
    user_cli._add_link_commands(parser.add_subparsers(dest="command"))
    devpy = argparse.ArgumentParser(prog="dev.py")
    user_cli.register_subparser(devpy.add_subparsers(dest="group"))

    assert vars(parser.parse_args(["reassign-owner", "someone"])) == {"command": "reassign-owner", "username": "someone"}
    through = devpy.parse_args(["user", "reassign-owner", "someone"])
    assert (through.group, through.command, through.username) == ("user", "reassign-owner", "someone")
    with pytest.raises(SystemExit):
        parser.parse_args(["reassign-owner"])


def test_the_dispatch_runs_cmd_reassign_owner(user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A54-041: ``_dispatch_user_command`` answers what ``cmd_reassign_owner`` answers."""
    seen: list[str] = []

    async def recorded(username: str) -> bool:
        seen.append(username)
        return True

    monkeypatch.setattr(user_cli, "cmd_reassign_owner", recorded, raising=False)
    assert user_cli._dispatch_user_command(argparse.Namespace(command="reassign-owner", username="someone")) is True
    assert seen == ["someone"]


# =============================================================================
# A5-4: a change of address revokes the live email_change links
# =============================================================================


@pytest.mark.asyncio
async def test_a_new_address_revokes_the_live_email_change_links_of_the_account(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """A54-050: ``update_profile`` with a NEW address revokes the account's live ``email_change`` links (a link asked for before cannot move the address again); another account's link and a consumed one are untouched; the same address in another case revokes nothing."""
    _managed(monkeypatch)
    user_id = await _add_user(engine, "change_mine", BACKUP_EMAIL)
    other_id = await _add_user(engine, "change_other", STRANGER_EMAIL)
    mine = await _plant(engine, user_id, purpose=CHANGE, email=WRONG_EMAIL)
    consumed = await _plant(engine, user_id, purpose=CHANGE, email=WRONG_EMAIL, state="consumed")
    others = await _plant(engine, other_id, purpose=CHANGE, email=WRONG_EMAIL)

    async def revoked(issued: Any) -> bool:
        async with AsyncSession(engine) as session:
            return (await session.get(AccountToken, issued.record.id)).revoked_at is not None

    async with AsyncSession(engine) as session:
        _, error = await user_service.update_profile(session, user_id, email=BACKUP_EMAIL.upper())
    assert error is None and not await revoked(mine), "the same address in another case is no change"

    async with AsyncSession(engine) as session:
        updated, error = await user_service.update_profile(session, user_id, email="new-address@zq-assign.example.com")
    assert error is None and updated is not None
    assert await revoked(mine) and not await revoked(others)
    async with AsyncSession(engine) as session:
        assert (await session.get(AccountToken, consumed.record.id)).revoked_at is None, "a spent link stays as it was"

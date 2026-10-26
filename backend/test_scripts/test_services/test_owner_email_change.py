"""A5-1b part 2: the owner of a managed instance changes its address from the host, with a confirmation link (release 1.3, workstream A).

On a MANAGED instance (``LIBREFOLIO_PROFILE=managed``) the account with the address of ``LIBREFOLIO_ADMIN_EMAIL`` is the
«paying administrator» (the owner), protected since A5-1. The real change of its address starts from the host: the hoster
changes the variable and restarts the instance. The contract pinned here (developer decisions of 23/10/2026):

- OWNER IDENTITY — ``users.is_instance_owner`` (bool, default false) records who the owner is, because the variable's
  address cannot identify it once the variable has changed. It is set when the managed bootstrap creates the initial
  administrator, and by the startup sync (self-healing) when no owner is recorded and an account holds the variable's
  address; never in another profile. ``account_protection`` is: managed AND (the account IS the recorded owner, OR no owner
  is known and its address is the variable's). Once the sync has run in the process and found an owner recorded, only
  that account is protected: an account that holds the new address of a variable changed in conflict is NOT protected by
  its address (it would be a stranger). Before the sync has run (the process knows nothing), the address rule of A5-1 is
  the fallback, so every A5-1 behaviour is unchanged.
- STARTUP SYNC — ``instance_owner.run_owner_sync`` / ``startup_owner_sync`` (startup step ``owner-sync``, right after
  ``admin-bootstrap``): managed only, with a usable variable. (a) a pending initial administrator: nothing, as today;
  (b) no owner recorded: an account with the variable's address is recorded as the owner, nothing else; (c) the owner
  has the variable's address (any A-Z case): nothing (its leftover change links are revoked); (d) the address differs:
  another account holds the variable's address → ``blocked`` (an error line, no change); a LIVE ``email_change`` link of
  the owner already carries it → ``waiting`` (nothing resent); otherwise the owner's older links are revoked, a new
  one is issued for the variable's address (7 days) and ``issued``; the link goes by email to the NEW address, and in
  the startup log (a warning) only when that email did not go.
- STATUS — ``owner_change_status(session)``: ``"pending"`` (the change is not completed), ``"blocked"`` (another account
  holds the new address) or ``None``.

Pure: every database is a private SQLite file under ``tmp_path`` (``create_all`` plus the global settings), opened as
production opens its own; ``get_async_engine`` is a tripwire. ``instance_owner.send_email`` is an outbox, ``smtp.deliver`` a
tripwire. Profile and variables are set with ``monkeypatch``. The log is read with ``structlog.testing.capture_logs``. No
clock wait: every call gets its ``now``.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import get_settings
from backend.app.config.accounts import admin_bootstrap_config
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, hash_token
from backend.app.services.email import delivery, messages, smtp
from backend.app.services.email.messages import EmailContent
from backend.app.services.platform import app_lifespan
from backend.app.services.platform.instance_backup import apply
from backend.app.services.platform.instance_backup import owner as backup_owner
from backend.app.services.platform.lifecycle import run_startup_steps
from backend.app.utils.datetime_utils import ensure_utc
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

OWNER_MODULE = "backend.app.services.accounts.instance_owner"
BOOTSTRAP_MODULE = "backend.app.services.accounts.bootstrap_admin_service"

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
ADMIN_PREFIX = "LIBREFOLIO_ADMIN_"
INHERITED_VARIABLES = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_BLOCKED", PROFILE_VARIABLE)

OLD_EMAIL = "owner@zq-own.example.com"
NEW_EMAIL = "new.owner@zq-own.example.com"
NEWER_EMAIL = "newer.owner@zq-own.example.com"
STRANGER_EMAIL = "stranger@zq-own.example.com"
MARKER_HASH = "$argon2id$own-marker"

PUBLIC_URL = "https://folio.zq-own.example.com:8443/app"
PUBLIC_HOST = "folio.zq-own.example.com:8443"
SMTP_HOST = "smtp.zq-own.example.com"
SENDER_HEADER = "LibreFolio <noreply@example.com>"

#: Months before the real clock: a ``now`` that does not reach the token service shows.
NOW = datetime(2026, 1, 15, 9, 30, 0, tzinfo=UTC)
CHANGE_TTL = timedelta(days=7)
CHANGE = AccountTokenPurpose.EMAIL_CHANGE
#: The page the link opens: the web app's, next to ``/verify-email``.
CHANGE_PAGE = "/confirm-email-change"
LOG_CANARY = "canary: the capture reaches the logger of the owner sync"
LOOP_TURNS = 50


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """None of the profile, admin, SMTP and links variables of the shell that started the run; test mode keeps ``.env`` out."""
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
    """What the process knows of the recorded owner is put back after the test: a sync here must not leak into another test of the process."""
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's — the engine must be passed through")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)
    for name in (OWNER_MODULE, BOOTSTRAP_MODULE):
        try:
            module = importlib.import_module(name)
        except Exception:  # red until the lot: the tests that need the module say why
            continue
        if hasattr(module, "get_async_engine"):
            monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire)


@pytest.fixture(autouse=True)
def no_smtp_conversation(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """The SMTP transport refuses to run and the hourly budget is a private one."""
    attempts: list[str] = []

    def refuse(_server: object, message: object) -> None:
        attempts.append(type(message).__name__)
        raise AssertionError("an owner-sync test reached the SMTP transport")

    monkeypatch.setattr(smtp, "deliver", refuse)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))
    yield attempts
    assert attempts == [], f"the delivery reached the real SMTP transport ({len(attempts)}): it must send through instance_owner.send_email, imported by name"


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'owner.db'}", poolclass=NullPool)
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
    """``backend.app.services.accounts.instance_owner``: the owner sync, status and confirmation."""
    try:
        return importlib.import_module(OWNER_MODULE)
    except ModuleNotFoundError as missing:
        if missing.name == OWNER_MODULE:
            pytest.fail(f"red until A5-1b part 2: {OWNER_MODULE} does not exist yet", pytrace=False)
        raise


@dataclass(frozen=True)
class SentEmail:
    content: EmailContent
    to: str
    user_id: Optional[int]


class Outbox:
    """Stands in for ``send_email`` in the owner module: records every attempt, then raises ``failure`` when one is set."""

    def __init__(self) -> None:
        self.attempts: list[SentEmail] = []
        self.failure: Optional[BaseException] = None

    async def send_email(self, content: EmailContent, *, to: str, user_id: Optional[int] = None) -> None:
        self.attempts.append(SentEmail(content=content, to=to, user_id=user_id))
        if self.failure is not None:
            raise self.failure


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> Outbox:
    if not hasattr(owner, "send_email"):
        pytest.fail("red until A5-1b part 2: instance_owner must import send_email by name (backend.app.services.email.delivery)", pytrace=False)
    box = Outbox()
    monkeypatch.setattr(owner, "send_email", box.send_email)
    return box


# =============================================================================
# HELPERS
# =============================================================================


def _managed(monkeypatch: pytest.MonkeyPatch, *, variable: Optional[str] = OLD_EMAIL, profile: Optional[str] = "managed") -> None:
    """The profile and ``LIBREFOLIO_ADMIN_EMAIL`` this test runs with, with a barrier that ``get_settings()`` reads the profile."""
    if profile is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if variable is not None:
        monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, variable)
    assert get_settings().LIBREFOLIO_PROFILE == (profile or "selfhosted"), "barrier: get_settings() must read the profile this test sets"


def _email_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{SMTP_PREFIX}HOST", SMTP_HOST)
    monkeypatch.setenv(f"{SMTP_PREFIX}FROM", SENDER_HEADER)


def _links_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


async def _add_user(engine: AsyncEngine, username: str, email: str, *, active: bool = True, admin: bool = False, instance_owner: bool = False) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=MARKER_HASH, is_active=active, is_superuser=admin)
        if instance_owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user.id


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None
    return user


async def _owner_ids(engine: AsyncEngine) -> list[int]:
    async with engine.connect() as connection:
        return list((await connection.execute(text("SELECT id FROM users WHERE is_instance_owner = 1 ORDER BY id"))).scalars().all())


async def _change_rows(engine: AsyncEngine, user_id: Optional[int] = None) -> list[AccountToken]:
    statement = select(AccountToken).where(AccountToken.purpose == CHANGE).order_by(AccountToken.id)
    if user_id is not None:
        statement = statement.where(AccountToken.user_id == user_id)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return list((await session.execute(statement)).scalars().all())


def _live(row: AccountToken, moment: datetime) -> bool:
    return row.consumed_at is None and row.revoked_at is None and ensure_utc(row.expires_at) > moment


async def _sync(owner: ModuleType, engine: AsyncEngine, moment: datetime = NOW) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await owner.run_owner_sync(session, now=moment)


async def _deliver(owner: ModuleType, engine: AsyncEngine, result: Any, moment: datetime = NOW) -> None:
    await owner.deliver_owner_change_link(result, engine=engine, now=moment)


async def _status(owner: ModuleType, engine: AsyncEngine) -> Optional[str]:
    async with AsyncSession(engine) as session:
        return await owner.owner_change_status(session)


async def _snapshot(engine: AsyncEngine) -> dict[str, list[Any]]:
    async with engine.connect() as connection:
        users = (await connection.execute(text("SELECT * FROM users ORDER BY id"))).mappings().all()
        tokens = (await connection.execute(text("SELECT * FROM account_tokens ORDER BY id"))).mappings().all()
    return {"users": [dict(row) for row in users], "tokens": [dict(row) for row in tokens]}


def _log_text(events: list[dict[str, Any]]) -> str:
    return "\n".join(str(event) for event in events)


def _token_of(link: str) -> str:
    """The token in the fragment of ``link`` (``…/confirm-email-change#token=…``)."""
    parts = urlsplit(link)
    assert parts.path.endswith(CHANGE_PAGE), f"the link must open {CHANGE_PAGE}: {link}"
    return parse_qs(parts.fragment)["token"][0]


def _link_in_text(content: EmailContent) -> str:
    for line in content.text.splitlines():
        if line.startswith("http"):
            return line.strip()
    pytest.fail("the plain-text part carries no link", pytrace=False)


async def _managed_scene(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, *, variable: str = NEW_EMAIL) -> int:
    """An active, recorded owner at OLD_EMAIL on a managed instance whose variable is now ``variable``. The owner's id."""
    owner_id = await _add_user(engine, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
    _managed(monkeypatch, variable=variable)
    return owner_id


# =============================================================================
# THE OWNER FLAG AND THE PROTECTION RULE
# =============================================================================


@pytest.mark.asyncio
async def test_the_flag_defaults_to_false_and_at_most_one_account_holds_it(engine: AsyncEngine) -> None:
    """OWN-001: ``users.is_instance_owner`` is false for a new account; the partial unique index refuses a second owner."""
    print_section("OWN-001: the flag and its unique index")
    first = await _add_user(engine, "own_a", "a@zq-own.example.com")
    assert (await _account(engine, first)).is_instance_owner is False
    await _add_user(engine, "own_b", "b@zq-own.example.com", instance_owner=True)
    with pytest.raises(IntegrityError):
        await _add_user(engine, "own_c", "c@zq-own.example.com", instance_owner=True)
    print_success("default false, one owner at most")


def test_the_flag_protects_the_owner_whatever_its_address_says(monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-010: managed, the variable changed and the link not yet clicked: the recorded owner (flag true, address still the old one) stays protected, its address matching nothing."""
    print_section("OWN-010: the click not made, the owner stays protected")
    _managed(monkeypatch, variable=NEW_EMAIL)
    recorded = User(id=1, username="own_owner", email=OLD_EMAIL, hashed_password="x", is_instance_owner=True)
    plain = User(id=2, username="own_plain", email=OLD_EMAIL, hashed_password="x")
    assert user_service.account_protection(recorded) == user_service.PAYING_ADMINISTRATOR
    # Barrier: with no flag and no knowledge the old address matches nothing now
    assert user_service.account_protection(plain) is None


def test_the_flag_protects_when_the_variable_is_unset_or_unusable(monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-011: managed with the variable unset, blank or not an address: the recorded owner is still protected (it IS the owner); every other account is not."""
    recorded = User(id=1, username="own_owner", email=OLD_EMAIL, hashed_password="x", is_instance_owner=True)
    other = User(id=2, username="own_other", email=OLD_EMAIL, hashed_password="x")
    for written in (None, "", "not-an-address"):
        monkeypatch.delenv(ADMIN_EMAIL_VARIABLE, raising=False)
        _managed(monkeypatch, variable=written)
        assert user_service.account_protection(recorded) == user_service.PAYING_ADMINISTRATOR, written
        assert user_service.account_protection(other) is None, written


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
def test_the_flag_protects_nobody_outside_the_managed_profile(monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
    """OWN-012: any other profile: nobody is protected, a flagged account included (the flag is set only in managed, and means nothing elsewhere)."""
    _managed(monkeypatch, variable=OLD_EMAIL, profile=profile)
    flagged = User(id=1, username="own_owner", email=OLD_EMAIL, hashed_password="x", is_instance_owner=True)
    assert user_service.account_protection(flagged) is None


@pytest.mark.asyncio
async def test_a_stranger_with_the_new_address_is_not_protected_once_the_owner_is_recorded(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-013 (item 1 of the design): the variable changed to an address ANOTHER account already holds. The sync finds the owner recorded and the conflict; from then on the process protects the owner and NOT the stranger by the address rule: the sync cannot hand protection to a stranger."""
    print_section("OWN-013: a conflict hands protection to nobody")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    stranger_id = await _add_user(engine, "own_stranger", NEW_EMAIL)
    owner_row, stranger_row = await _account(engine, owner_id), await _account(engine, stranger_id)

    await _sync(owner, engine)

    assert user_service.account_protection(owner_row) == user_service.PAYING_ADMINISTRATOR, "the recorded owner is protected"
    assert user_service.account_protection(stranger_row) is None, "the stranger holding the variable's address is NOT protected: an owner is recorded"


@pytest.mark.asyncio
async def test_without_a_recorded_owner_the_address_rule_is_the_fallback(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-014: before the sync has run (the process knows nothing), and after a sync that found no owner, the account with the variable's address is protected as in A5-1."""
    holder_id = await _add_user(engine, "own_holder", OLD_EMAIL, admin=True)
    _managed(monkeypatch, variable=OLD_EMAIL)
    holder = await _account(engine, holder_id)
    assert user_service.account_protection(holder) == user_service.PAYING_ADMINISTRATOR, "before the sync: the A5-1 address rule"
    result = await _sync(owner, engine)
    assert result.action == "healed"
    assert user_service.account_protection(await _account(engine, holder_id)) == user_service.PAYING_ADMINISTRATOR, "after the heal: the flag"


# =============================================================================
# WHERE THE FLAG IS SET
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("profile", "flagged"), [pytest.param("managed", True, id="managed"), pytest.param(None, False, id="selfhosted")])
async def test_the_bootstrap_records_the_owner_only_in_managed(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, profile: Optional[str], flagged: bool) -> None:
    """OWN-020: the initial administrator created by the F02 bootstrap is the recorded owner on a managed instance, and nobody is recorded in any other profile."""
    print_section(f"OWN-020: bootstrap, profile {profile}")
    bootstrap = importlib.import_module(BOOTSTRAP_MODULE)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, OLD_EMAIL)
    if profile is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, profile)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await bootstrap.run_admin_bootstrap(session, admin_bootstrap_config(), now=NOW)
    assert result.action == bootstrap.BootstrapAction.CREATED
    assert (await _account(engine, result.user_id)).is_instance_owner is flagged
    assert await _owner_ids(engine) == ([result.user_id] if flagged else [])


# =============================================================================
# THE SYNC, BRANCH BY BRANCH
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [pytest.param("selfhosted", id="selfhosted-profile"), pytest.param("unset", id="variable-unset"), pytest.param("invalid", id="variable-invalid")])
async def test_the_sync_does_nothing_outside_managed_or_without_a_variable(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """OWN-030: another profile, or a variable that is unset or not an address: ``off``, nothing written, no token, no email, no owner recorded even for an account holding the address."""
    print_section(f"OWN-030: {case}")
    await _add_user(engine, "own_holder", OLD_EMAIL, admin=True)
    if case == "selfhosted":
        _managed(monkeypatch, variable=OLD_EMAIL, profile="selfhosted")
    else:
        _managed(monkeypatch, variable=None if case == "unset" else "not-an-address")
    before = await _snapshot(engine)

    result = await _sync(owner, engine)

    assert result.action == "off"
    assert await _snapshot(engine) == before, "nothing is written"
    assert outbox.attempts == []


@pytest.mark.asyncio
async def test_a_pending_admin_is_left_as_today(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-031 (a): the initial administrator still WAITING for its setup (inactive, ``admin_setup`` link): the sync does nothing, and a change of the variable follows the existing logic — the waiting account takes the new address, its setup links are revoked — with no ``email_change`` link."""
    print_section("OWN-031: a waiting administrator")
    bootstrap = importlib.import_module(BOOTSTRAP_MODULE)
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, OLD_EMAIL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = await bootstrap.run_admin_bootstrap(session, admin_bootstrap_config(), now=NOW)
    assert created.action == bootstrap.BootstrapAction.CREATED
    # The host changes the variable and restarts: the bootstrap step runs first, then the sync
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEW_EMAIL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        followed = await bootstrap.run_admin_bootstrap(session, admin_bootstrap_config(), now=NOW + timedelta(minutes=1))
    assert followed.action in (bootstrap.BootstrapAction.EXPIRED, bootstrap.BootstrapAction.PENDING)
    waiting = await _account(engine, created.user_id)
    assert waiting.email == NEW_EMAIL, "today's logic: the waiting administrator follows the variable"
    before = await _snapshot(engine)

    result = await _sync(owner, engine, NOW + timedelta(minutes=2))

    assert result.action == "pending_admin"
    assert await _snapshot(engine) == before
    assert await _change_rows(engine) == [] and outbox.attempts == []
    assert await _status(owner, engine) is None, "the new flow applies only to an active owner"


@pytest.mark.asyncio
async def test_a_account_with_the_variables_address_is_recorded_as_the_owner(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-032 (b): no owner recorded and an account holds the variable's address (any A-Z case): it is recorded; nothing else changes (its address keeps its case); a second sync changes nothing."""
    print_section("OWN-032: heal")
    holder_id = await _add_user(engine, "own_holder", OLD_EMAIL.upper().replace("EXAMPLE.COM", "example.com"), admin=True)
    other_id = await _add_user(engine, "own_other", "other@zq-own.example.com")
    _managed(monkeypatch, variable=OLD_EMAIL)

    first = await _sync(owner, engine)
    after_first = await _snapshot(engine)
    second = await _sync(owner, engine)

    assert (first.action, second.action) == ("healed", "unchanged")
    assert await _owner_ids(engine) == [holder_id]
    assert (await _account(engine, other_id)).is_instance_owner is False
    assert await _snapshot(engine) == after_first, "the second sync writes nothing"
    assert await _change_rows(engine) == [] and outbox.attempts == []
    assert await _status(owner, engine) is None


@pytest.mark.asyncio
async def test_no_account_with_the_address_and_no_owner_is_left_alone(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-033: managed, nobody recorded, nobody holds the variable's address: ``no_owner``, nothing written."""
    await _add_user(engine, "own_other", "other@zq-own.example.com", admin=True)
    _managed(monkeypatch, variable=OLD_EMAIL)
    before = await _snapshot(engine)
    result = await _sync(owner, engine)
    assert result.action == "no_owner"
    assert await _snapshot(engine) == before and outbox.attempts == []


@pytest.mark.asyncio
async def test_an_owner_with_the_variables_address_changes_nothing_and_loses_stale_links(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-034 (c): the recorded owner's address equals the variable (another A-Z case too): ``unchanged``, no new link. A live link left over from an earlier value of the variable (the host changed it back) is revoked."""
    print_section("OWN-034: same address")
    owner_id = await _add_user(engine, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
    _managed(monkeypatch, variable=OLD_EMAIL.replace("owner@", "OWNER@"))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        stale = await token_service.issue_token(session, CHANGE, user_id=owner_id, email=NEW_EMAIL, now=NOW)
        await session.commit()

    result = await _sync(owner, engine, NOW + timedelta(hours=1))

    assert result.action == "unchanged"
    rows = await _change_rows(engine, owner_id)
    assert [row.id for row in rows] == [stale.record.id] and rows[0].revoked_at is not None, "the stale link is revoked, no new one is issued"
    assert outbox.attempts == []
    assert (await _account(engine, owner_id)).email == OLD_EMAIL


@pytest.mark.asyncio
async def test_a_conflict_changes_nothing_and_says_so(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-040 (d, conflict): the variable names an address another account holds. ``blocked``: no link, no email, the owner's address and flag untouched, an error line in the log with no address and no token; the status says ``blocked``."""
    print_section("OWN-040: conflict")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    stranger_id = await _add_user(engine, "own_stranger", NEW_EMAIL.upper().replace("EXAMPLE.COM", "example.com"))
    before = await _snapshot(engine)

    with capture_logs() as events:
        result = await _sync(owner, engine)

    assert result.action == "blocked"
    assert await _snapshot(engine) == before
    assert outbox.attempts == []
    errors = [event for event in events if event.get("log_level") == "error"]
    assert errors, "an error line in the log"
    assert NEW_EMAIL.lower() not in _log_text(events).lower() and OLD_EMAIL.lower() not in _log_text(events).lower(), "no address in the log"
    assert await _status(owner, engine) == "blocked"
    assert await _owner_ids(engine) == [owner_id] and (await _account(engine, stranger_id)).is_instance_owner is False


@pytest.mark.asyncio
async def test_a_new_link_goes_to_the_new_address(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-041 (d, change): the address differs and no other account has the new one. A link is issued for the owner (carrying the variable's address, 7 days) and emailed to the NEW address, with the public link to ``/confirm-email-change``. The owner's address, flag and sessions are untouched until the click; the status says ``pending``; the token is in no log line (the email went)."""
    print_section("OWN-041: issue and email")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    version_before = (await _account(engine, owner_id)).session_version

    with capture_logs() as events:
        result = await _sync(owner, engine)
        await _deliver(owner, engine, result)

    assert result.action == "issued" and result.user_id == owner_id
    rows = await _change_rows(engine, owner_id)
    assert len(rows) == 1
    row = rows[0]
    assert (row.purpose, row.user_id, row.email) == (CHANGE, owner_id, NEW_EMAIL)
    assert ensure_utc(row.expires_at) - ensure_utc(row.created_at) == CHANGE_TTL == DEFAULT_TTL[CHANGE]
    assert row.consumed_at is None and row.revoked_at is None
    assert [(mail.to, mail.user_id) for mail in outbox.attempts] == [(NEW_EMAIL, owner_id)]
    sent = outbox.attempts[0].content
    assert sent.kind == "email_change_confirmation"
    link = _link_in_text(sent)
    assert link.startswith(f"{PUBLIC_URL}{CHANGE_PAGE}#token="), link
    assert hash_token(_token_of(link)) == row.token_hash
    assert PUBLIC_HOST in sent.text
    owner_row = await _account(engine, owner_id)
    assert (owner_row.email, owner_row.is_instance_owner, owner_row.session_version) == (OLD_EMAIL, True, version_before)
    assert await _status(owner, engine) == "pending"
    assert _token_of(link) not in _log_text(events), "the email went: the token is in no log line"


@pytest.mark.asyncio
async def test_with_email_off_the_link_goes_in_the_startup_log(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-042: SMTP off: no email is attempted, and the link (a warning line) is in the startup log with the public address; without ``LIBREFOLIO_PUBLIC_URL`` the path alone, with a note."""
    print_section("OWN-042: SMTP off")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _links_ready(monkeypatch)

    with capture_logs() as events:
        result = await _sync(owner, engine)
        await _deliver(owner, engine, result)

    assert outbox.attempts == []
    logged = [event for event in events if event.get("log_level") == "warning" and "link" in event]
    assert len(logged) == 1, events
    token = _token_of(logged[0]["link"])
    row = (await _change_rows(engine, owner_id))[0]
    assert hash_token(token) == row.token_hash
    assert logged[0]["link"].startswith(PUBLIC_URL)

    # Without a public address: the path alone
    monkeypatch.delenv(PUBLIC_URL_VARIABLE)
    async with AsyncSession(engine) as session:
        await token_service.revoke_tokens(session, user_id=owner_id, purpose=CHANGE, now=NOW)
        await session.commit()
    with capture_logs() as events:
        result = await _sync(owner, engine, NOW + timedelta(minutes=1))
        await _deliver(owner, engine, result, NOW + timedelta(minutes=1))
    path_lines = [event for event in events if event.get("log_level") == "warning" and "link" in event]
    assert len(path_lines) == 1 and path_lines[0]["link"].startswith(CHANGE_PAGE) and path_lines[0].get("note"), events


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["send", "limit", "no-links"])
async def test_an_email_that_did_not_go_leaves_the_link_in_the_log(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    """OWN-043: email usable but the send fails (the SMTP server refuses, the hourly budget is spent) or no link can be built (``LIBREFOLIO_PUBLIC_URL`` unset): the delivery never raises, and the link is in the log."""
    print_section(f"OWN-043: {failure}")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    if failure != "no-links":
        _links_ready(monkeypatch)
    if failure == "send":
        outbox.failure = delivery.EmailDeliveryError(smtp.SmtpErrorCode.CONNECTION_FAILED)
    elif failure == "limit":
        outbox.failure = delivery.EmailRateLimitedError(60.0)

    with capture_logs() as events:
        result = await _sync(owner, engine)
        await _deliver(owner, engine, result)

    logged = [event for event in events if event.get("log_level") == "warning" and "link" in event]
    assert len(logged) == 1, events
    assert hash_token(_token_of(logged[0]["link"])) == (await _change_rows(engine, owner_id))[0].token_hash


@pytest.mark.asyncio
async def test_a_live_link_is_not_issued_again_at_the_next_start(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-044: the second start right after the first finds the live link: ``waiting`` — the same link, no second token, no second email (the plaintext is not kept). The status stays ``pending``."""
    print_section("OWN-044: idempotent")
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    first = await _sync(owner, engine)
    await _deliver(owner, engine, first)

    second = await _sync(owner, engine, NOW + timedelta(hours=2))
    await _deliver(owner, engine, second, NOW + timedelta(hours=2))

    assert (first.action, second.action) == ("issued", "waiting")
    assert second.link_token is None
    assert len(await _change_rows(engine, owner_id)) == 1
    assert len(outbox.attempts) == 1
    assert await _status(owner, engine) == "pending"


@pytest.mark.asyncio
async def test_an_expired_link_is_replaced(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-045: the link expired unused: the next start issues a fresh one for the same address, and emails it."""
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    first = await _sync(owner, engine)
    later = NOW + CHANGE_TTL + timedelta(minutes=1)

    second = await _sync(owner, engine, later)
    await _deliver(owner, engine, second, later)

    assert (first.action, second.action) == ("issued", "issued")
    rows = await _change_rows(engine, owner_id)
    assert len(rows) == 2 and [_live(row, later) for row in rows] == [False, True]
    assert rows[1].email == NEW_EMAIL and len(outbox.attempts) == 1


@pytest.mark.asyncio
async def test_a_variable_changed_again_revokes_the_old_link(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-046: the host changes the variable AGAIN before the click: the next start revokes the older link and issues one for the latest address."""
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    first = await _sync(owner, engine)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEWER_EMAIL)

    second = await _sync(owner, engine, NOW + timedelta(hours=1))

    assert (first.action, second.action) == ("issued", "issued")
    rows = await _change_rows(engine, owner_id)
    assert [(row.email, row.revoked_at is not None) for row in rows] == [(NEW_EMAIL, True), (NEWER_EMAIL, False)]


@pytest.mark.asyncio
async def test_two_starts_at_once_issue_one_link(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-047: two workers starting together: the write lock serialises them, and exactly one live link exists afterwards."""
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)

    results = await asyncio.gather(_sync(owner, engine), _sync(owner, engine))

    assert sorted(result.action for result in results) == ["issued", "waiting"]
    rows = await _change_rows(engine, owner_id)
    assert [_live(row, NOW) for row in rows].count(True) == 1


@pytest.mark.asyncio
async def test_the_startup_step_delivers_in_the_background(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-048: ``startup_owner_sync(engine)`` answers at once with the sync's result and leaves the delivery to a background task; once it ran, the email is in the outbox."""
    await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)

    result = await owner.startup_owner_sync(engine)

    assert result.action == "issued"
    pending = list(owner._DELIVERIES)
    for _ in range(LOOP_TURNS):
        if not owner._DELIVERIES:
            break
        await asyncio.sleep(0)
    await asyncio.gather(*pending)
    assert [mail.to for mail in outbox.attempts] == [NEW_EMAIL]


@pytest.mark.asyncio
async def test_no_token_ever_reaches_the_log_or_a_column_but_its_hash(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-049: through a full issue and delivery the plaintext token is in no log line (email went), and no column of the database holds it."""
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    with capture_logs() as events:
        result = await _sync(owner, engine)
        await _deliver(owner, engine, result)
    token = result.link_token
    assert token and token not in _log_text(events) and token not in repr(result)
    async with engine.connect() as connection:
        for table in (await connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))).scalars().all():
            for row in (await connection.execute(text(f'SELECT * FROM "{table}"'))).mappings().all():
                assert not any(token in str(value) for value in row.values() if value is not None), table
    assert (await _account(engine, owner_id)).email == OLD_EMAIL


# =============================================================================
# THE STATUS
# =============================================================================


@pytest.mark.asyncio
async def test_the_status_values(engine: AsyncEngine, owner: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-050: ``owner_change_status`` is ``None`` with no owner recorded, the same address, another profile or no variable; ``"pending"`` when the owner's address differs; ``"blocked"`` when another account holds the variable's address. Read-only, and its value is a plain word."""
    print_section("OWN-050: owner_change_status")
    await _add_user(engine, "own_holder", OLD_EMAIL, admin=True)
    _managed(monkeypatch, variable=NEW_EMAIL)
    assert await _status(owner, engine) is None, "no owner recorded"
    async with engine.begin() as connection:
        await connection.execute(text("UPDATE users SET is_instance_owner = 1"))
    assert await _status(owner, engine) == "pending"
    before = await _snapshot(engine)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, OLD_EMAIL)
    assert await _status(owner, engine) is None, "same address"
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEW_EMAIL)
    await _add_user(engine, "own_stranger", NEW_EMAIL)
    assert await _status(owner, engine) == "blocked"
    monkeypatch.delenv(ADMIN_EMAIL_VARIABLE)
    assert await _status(owner, engine) is None, "no variable"
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEW_EMAIL)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    assert await _status(owner, engine) is None, "another profile"
    assert (await _snapshot(engine))["tokens"] == before["tokens"], "the status writes nothing"


# =============================================================================
# THE STARTUP STEP, AND THE EMAIL
# =============================================================================


def test_the_owner_sync_step_runs_right_after_the_restore_commit() -> None:
    """OWN-060 (N3): ``STARTUP_STEPS`` has ``owner-sync`` immediately after ``restore-commit`` — which closes the way in after a restore and revokes every live one-time link, a change link just issued included —, and so after ``admin-bootstrap``; skipped when the instance serves no data; running ``startup_owner_sync``."""
    names = [step.name for step in app_lifespan.STARTUP_STEPS]
    assert "owner-sync" in names, "red until A5-1b part 2: STARTUP_STEPS has no owner-sync step"
    between = names[names.index("restore-commit") + 1 : names.index("owner-sync")]
    assert names.index("owner-sync") > names.index("restore-commit") and set(between) <= {"restore-owner"}, f"owner-sync follows restore-commit, only H5-3's restore-owner between them: {names}"
    assert names.index("admin-bootstrap") < names.index("owner-sync")
    step = app_lifespan.STARTUP_STEPS[names.index("owner-sync")]
    assert step.skip_when is app_lifespan._serving_no_data


@pytest.mark.asyncio
async def test_the_step_runs_the_function_by_its_name(owner: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-061: the step reaches ``startup_owner_sync`` through the lifespan module's own name, so a test can replace it."""
    called: list[str] = []

    async def fake() -> str:
        called.append("run")
        return "done"

    monkeypatch.setattr(app_lifespan, "startup_owner_sync", fake)
    step = next(step for step in app_lifespan.STARTUP_STEPS if step.name == "owner-sync")
    assert await step.run() == "done" and called == ["run"]


class _Languages(StrEnum):
    EN = "en"
    IT = "it"
    FR = "fr"
    ES = "es"


@pytest.mark.parametrize("language", list(_Languages))
def test_the_confirmation_email_exists_in_the_four_languages(language: _Languages) -> None:
    """OWN-070: ``build_email_change_confirmation(language, username, link, ttl, instance)`` writes the kind in each language, with the link in both parts, the instance and the duration, and no placeholder left."""
    build = getattr(messages, "build_email_change_confirmation", None)
    assert build is not None, "red until A5-1b part 2: messages has no build_email_change_confirmation"
    link = "https://folio.zq-own.example.com/confirm-email-change#token=abc"
    content = build(language=language.value, username="own_owner", link=link, ttl=CHANGE_TTL, instance=PUBLIC_HOST)
    assert content.kind == "email_change_confirmation" and content.language == language.value
    assert link in content.text and link in content.html and PUBLIC_HOST in content.text
    assert "$" not in content.text and "$" not in content.subject


# =============================================================================
# THE STATE THE STARTUP LEAVES, FOR THE SECURITY CHECKS (A5-1b, request to workstream H)
# =============================================================================
# ``owner_change_status(session)`` reads the database and is async; the configuration checks are synchronous and read no
# database. The startup step therefore leaves the state of its own run in the process, ``startup_change_state()``:
# ``"pending"`` while the change waits for the click (a link issued, or one still live), ``"blocked"`` when another
# account holds the new address, ``None`` otherwise — and None again once the owner has confirmed.


async def _drain_deliveries(owner: ModuleType) -> None:
    pending = list(owner._DELIVERIES)
    if pending:
        await asyncio.gather(*pending)


@pytest.mark.asyncio
async def test_the_startup_leaves_pending_when_it_issued_a_link(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-070: a link issued at the start → ``startup_change_state()`` is ``pending``; a second start that finds the link still live says the same."""
    await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    owner._startup_state = None

    first = await owner.startup_owner_sync(engine)
    await _drain_deliveries(owner)
    state_after_first = owner.startup_change_state()
    owner._startup_state = None
    second = await owner.startup_owner_sync(engine)

    assert (first.action, second.action) == ("issued", "waiting")
    assert state_after_first == "pending"
    assert owner.startup_change_state() == "pending"


@pytest.mark.asyncio
async def test_the_startup_leaves_blocked_when_another_account_has_the_address(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-071: another account holds the new address → ``blocked``, no link."""
    await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    await _add_user(engine, "own_stranger", NEW_EMAIL)
    owner._startup_state = "pending"

    result = await owner.startup_owner_sync(engine)

    assert result.action == "blocked"
    assert owner.startup_change_state() == "blocked"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["same_address", "no_variable", "not_managed"])
async def test_the_startup_leaves_nothing_when_there_is_no_change_to_wait_for(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """OWN-072: the same address, no variable, or another profile → ``None``, whatever an earlier run said."""
    await _add_user(engine, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
    if case == "same_address":
        _managed(monkeypatch, variable=OLD_EMAIL)
    elif case == "no_variable":
        _managed(monkeypatch, variable=None)
    else:
        _managed(monkeypatch, variable=NEW_EMAIL, profile="selfhosted")
    owner._startup_state = "pending"

    await owner.startup_owner_sync(engine)

    assert owner.startup_change_state() is None


@pytest.mark.asyncio
async def test_the_confirmation_clears_the_state(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-073: once the owner has confirmed the new address, the state says nothing is waiting any more."""
    await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    owner._startup_state = None
    result = await owner.startup_owner_sync(engine)
    await _drain_deliveries(owner)
    assert owner.startup_change_state() == "pending"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await owner.confirm_email_change(session, result.link_token or "", now=NOW)

    assert owner.startup_change_state() is None


# =============================================================================
# REVIEW CORRECTIONS (independent security review, 23/10): N1 heal, N3 order after a restore, minors
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "recorded"),
    [
        pytest.param("ordinary", False, id="an-ordinary-account-is-not-recorded"),
        pytest.param("inactive-admin", False, id="an-inactive-administrator-is-not-recorded"),
        pytest.param("active-admin", True, id="an-active-administrator-is-recorded"),
    ],
)
async def test_only_an_active_administrator_is_recorded_as_the_owner(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, kind: str, recorded: bool) -> None:
    """OWN-080 (N1): the heal records the account with the variable's address only when it is an ACTIVE ADMINISTRATOR. An ordinary user who put a free address equal to the variable in their profile, or a self-hosted backup restored on a managed instance, must not become the permanent owner: ``no_owner``, nobody recorded, an error line with no address and no username."""
    print_section(f"OWN-080: {kind}")
    holder_id = await _add_user(engine, "own_heal_holder", OLD_EMAIL, admin=kind != "ordinary", active=kind != "inactive-admin")
    _managed(monkeypatch, variable=OLD_EMAIL)

    with capture_logs() as events:
        result = await _sync(owner, engine)

    assert result.action == ("healed" if recorded else "no_owner")
    assert await _owner_ids(engine) == ([holder_id] if recorded else [])
    errors = [event for event in events if event.get("log_level") == "error"]
    if recorded:
        assert errors == []
    else:
        assert len(errors) == 1 and "not an active administrator" in errors[0]["event"], events
        text = _log_text(events).lower()
        assert OLD_EMAIL.lower() not in text and "own_heal_holder" not in text, "no address and no username in the log"


@pytest.mark.asyncio
async def test_a_refused_heal_leaves_the_address_rule_to_administrators_only(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-081 (N1): once the sync has run and recorded NOBODY, the address fallback of ``account_protection`` protects an active administrator holding the address, and neither an ordinary user nor an inactive administrator. Before any sync (the process knows nothing) the A5-1 rule is untouched: the address alone protects, administrator or not."""
    ordinary_id = await _add_user(engine, "own_ordinary", OLD_EMAIL)
    _managed(monkeypatch, variable=OLD_EMAIL)
    ordinary = await _account(engine, ordinary_id)
    assert user_service.account_protection(ordinary) == user_service.PAYING_ADMINISTRATOR, "barrier: before the sync, A5-1 protects by address alone"

    await _sync(owner, engine)

    assert user_service.account_protection(ordinary) is None, "after a sync that recorded nobody, an ordinary user is not protected by an address"
    inactive_admin = User(id=99, username="own_inactive_admin", email=OLD_EMAIL, hashed_password="x", is_superuser=True, is_active=False)
    active_admin = User(id=98, username="own_active_admin", email=OLD_EMAIL, hashed_password="x", is_superuser=True, is_active=True)
    assert user_service.account_protection(inactive_admin) is None
    assert user_service.account_protection(active_admin) == user_service.PAYING_ADMINISTRATOR, "an active administrator holding the address stays protected until the next start records it"


async def _restored_database(tmp_path: Path) -> tuple[Path, AsyncEngine]:
    """A data directory whose ``sqlite/app.db`` is the restored database: the schema and the global settings."""
    data_dir = tmp_path / "restored-data"
    (data_dir / "sqlite").mkdir(parents=True)
    private = create_async_engine(f"sqlite+aiosqlite:///{data_dir / 'sqlite' / 'app.db'}", poolclass=NullPool)
    async with private.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(private) as session:
        await initialize_global_settings(session)
    return data_dir, private


@pytest.mark.asyncio
async def test_a_restore_revokes_a_change_link_it_finds_live(owner: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-082 (N3, the premise): ``_close_the_way_in`` — the commit of a restore — revokes EVERY live one-time link of the restored database, an ``email_change`` link included: a link issued before it is dead on arrival."""
    data_dir, private = await _restored_database(tmp_path)
    try:
        owner_id = await _add_user(private, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
        _managed(monkeypatch, variable=NEW_EMAIL)
        result = await _sync(owner, private)
        assert result.action == "issued"

        apply._close_the_way_in(data_dir, datetime.now(UTC))

        assert [_live(row, datetime.now(UTC)) for row in await _change_rows(private, owner_id)] == [False]
    finally:
        await private.dispose()


@pytest.mark.asyncio
async def test_after_a_restore_with_the_variable_changed_the_owner_gets_the_address_and_one_reset_link(owner: ModuleType, outbox: Outbox, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-083 (N3, B5-1j): the first start on a restored database whose owner's address differs from the variable, the real ``restore-commit``, ``restore-owner`` and ``owner-sync`` steps in the order ``STARTUP_STEPS`` gives them. The restore's commit revokes the change link the backup carried; ``restore-owner`` (B's real ``assign_restored_owner``, A's real ``assign_owner_and_send_reset``) gives the owner the variable's address, verified, with an unusable password, and emails ONE reset link marked with it; ``owner-sync`` then finds the address settled and issues no change link. No change link is live afterwards, and the only email is that reset."""
    data_dir, private = await _restored_database(tmp_path)
    try:
        owner_id = await _add_user(private, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
        async with AsyncSession(private, expire_on_commit=False) as session:
            carried = await token_service.issue_token(session, CHANGE, user_id=owner_id, email=NEW_EMAIL, now=datetime.now(UTC))
            await session.commit()
        _managed(monkeypatch, variable=NEW_EMAIL)
        _email_ready(monkeypatch)
        _links_ready(monkeypatch)
        (data_dir / ".restore").mkdir()
        monkeypatch.setattr(apply, "owner_pending", lambda _data_dir: ("own083-stage", owner_id))
        recorded: list[str] = []
        monkeypatch.setattr(apply, "record_owner_outcome", lambda _data_dir, _stage, outcome: recorded.append(outcome))
        monkeypatch.setattr(app_lifespan, "finish_pending_restore", lambda: apply._close_the_way_in(data_dir, datetime.now(UTC)))
        monkeypatch.setattr(app_lifespan, "assign_restored_owner", lambda: backup_owner.assign_restored_owner(data_dir))
        monkeypatch.setattr(app_lifespan, "probe_owner_assignment", lambda: None)
        monkeypatch.setattr(app_lifespan, "startup_owner_sync", lambda: owner.startup_owner_sync(private))
        wanted = ("restore-commit", "restore-owner", "owner-sync")
        steps = [step for step in app_lifespan.STARTUP_STEPS if step.name in wanted]
        assert [step.name for step in steps] == list(wanted), "barrier: the three steps are in STARTUP_STEPS, in this order"

        await run_startup_steps(steps)
        await _drain_deliveries(owner)

        assert recorded == ["sent"], "barrier: the restore-owner step ran the real assignment and recorded its outcome"
        account = await _account(private, owner_id)
        assert (account.email, account.is_superuser, account.is_active, account.is_instance_owner) == (NEW_EMAIL, True, True, True)
        assert account.email_verified_at is not None
        assert account.hashed_password != MARKER_HASH and not auth_service.verify_password("anything", account.hashed_password), "the password the backup carried opens nothing"
        assert await _owner_ids(private) == [owner_id]
        now = datetime.now(UTC)
        changes = await _change_rows(private, owner_id)
        assert [row.token_hash for row in changes] == [hash_token(carried.token)] and [_live(row, now) for row in changes] == [False], "no email-change link is live: the one the backup carried died at the commit and none was issued since"
        async with AsyncSession(private) as session:
            resets = list((await session.execute(select(AccountToken).where(AccountToken.purpose == AccountTokenPurpose.PASSWORD_RESET, AccountToken.user_id == owner_id))).scalars().all())
        assert [(row.email, _live(row, now)) for row in resets] == [(NEW_EMAIL, True)], "ONE reset link, live, marked with the owner's address"
        assert [(mail.to, mail.content.kind) for mail in outbox.attempts] == [(NEW_EMAIL, "password_reset")], "the only email is the reset link"
    finally:
        await private.dispose()


@pytest.mark.asyncio
async def test_a_conflict_found_under_the_lock_says_so_in_the_log(engine: AsyncEngine, owner: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """OWN-084 (minor a): another account takes the address between the first check and the write lock: ``blocked``, and the same error line as when the first check finds it (no address, no token)."""
    owner_id = await _managed_scene(engine, monkeypatch, variable=NEW_EMAIL)
    answers = iter([False, True])

    async def taken_after_the_first_look(*_arguments: object, **_keywords: object) -> bool:
        return next(answers)

    monkeypatch.setattr(owner, "_address_taken", taken_after_the_first_look)
    with capture_logs() as events:
        result = await _sync(owner, engine)

    assert result.action == "blocked" and result.user_id == owner_id
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and "belongs to another account" in errors[0]["event"], events
    assert NEW_EMAIL.lower() not in _log_text(events).lower()
    assert await _change_rows(engine, owner_id) == []


class _CountingSession(AsyncSession):
    """An ``AsyncSession`` that counts its commits and rollbacks."""

    def __init__(self, *arguments: Any, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1
        await super().commit()

    async def rollback(self) -> None:
        self.rollbacks += 1
        await super().rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["variable-changed", "address-taken-at-the-commit"])
async def test_a_refused_confirmation_revokes_the_link_in_the_same_transaction(engine: AsyncEngine, owner: ModuleType, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """OWN-085 (minor b): a click refused after the link was spent (the host changed the variable again; or another account holds the address and the unique index refuses it at the write) revokes the link in the SAME transaction: one commit, no rollback of the session — no moment at which the link is neither spent nor revoked. Nothing else changed."""
    owner_id = await _add_user(engine, "own_owner", OLD_EMAIL, admin=True, instance_owner=True)
    _managed(monkeypatch, variable=NEW_EMAIL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, CHANGE, user_id=owner_id, email=NEW_EMAIL, now=NOW)
        await session.commit()
    if case == "variable-changed":
        monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEWER_EMAIL)
    else:
        await _add_user(engine, "own_stranger", NEW_EMAIL)

        async def not_taken(*_arguments: object, **_keywords: object) -> bool:
            return False

        monkeypatch.setattr(owner, "_address_taken", not_taken)  # the check misses it: the unique index is the last word
    version = (await _account(engine, owner_id)).session_version

    async with _CountingSession(engine, expire_on_commit=False) as counting:
        with pytest.raises(owner.OwnerEmailChangeLinkInvalidError) as refused:
            await owner.confirm_email_change(counting, issued.token, now=NOW)

    assert refused.value.code == "revoked"
    assert (counting.commits, counting.rollbacks) == (1, 0), f"one transaction: commits {counting.commits}, rollbacks {counting.rollbacks}"
    row = (await _change_rows(engine, owner_id))[0]
    assert row.revoked_at is not None and row.consumed_at is None, "revoked, and not left as spent"
    account = await _account(engine, owner_id)
    assert (account.email, account.session_version) == (OLD_EMAIL, version)

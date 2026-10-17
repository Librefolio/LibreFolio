"""F02: the first administrator from environment variables, and its single-use ``/setup`` link — backend (release 1.3, workstream A, lot A7a).

A managed instance must not hand its first account to whoever opens the page first. Its hosting provider names the
administrator in ``LIBREFOLIO_ADMIN_EMAIL`` (and ``LIBREFOLIO_ADMIN_USERNAME``); the instance creates that account
inactive, with a single-use link to choose its password: a generated one, logged and emailed, or the one the provider
put in ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` and delivers itself. The contract pinned here («ND»: a night decision, pinned
as written):

- CFG, C1 — ``backend/app/config/accounts.py``, read at call time: the constants; ``AdminBootstrapConfig(email, username,
  token)``, frozen; ``AdminBootstrapConfigError``, a ``ValueError`` with ``variable`` and ``code``, whose message names the
  variable and never the token; ``admin_bootstrap_config()``: ``None`` when none of the three variables is set (blank is
  unset; the token through ``env_secret``, so ``_FILE`` too); with the email, the username ``admin`` unless set, both
  stripped (ND); the codes ``ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL``, ``ADMIN_USERNAME_WITHOUT_EMAIL`` (ND 5),
  ``ADMIN_EMAIL_INVALID`` (``EmailStr``), ``ADMIN_USERNAME_INVALID`` (3 to 50 characters),
  ``ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS`` (URL-unreserved only, ND 4), ``ADMIN_BOOTSTRAP_TOKEN_TOO_SHORT`` (32) and
  ``ADMIN_BOOTSTRAP_TOKEN_TOO_LONG`` (200); an unreadable ``_FILE`` is ``SecretFileError``. ``log_configuration_audit()``
  calls it, so a broken F02 variable stops the start (ND 2) whatever the instance holds: the audit opens no database.
- TOKEN — ``issue_token(..., token=...)``: a given token is stored by its hash and handed back; an empty one is a
  ``ValueError``; without it, a generated token as before; never logged.
- BOOT, C2 — ``bootstrap_admin_service``: ``BootstrapAction``, ``BootstrapResult``; ``pending_admin`` (inactive, an
  ``admin_setup`` token, none consumed); ``run_admin_bootstrap``: OFF, IGNORED, CREATED (an inactive superuser with the
  bcrypt hash of a random secret, ``registration_mode`` ``invite``, one setup link of 72 h), PENDING, REARMED, EXPIRED (a
  warning naming ``./dev.py user setup-link``), the rename and its conflict; two bootstraps racing create one
  administrator; ``deliver_setup_link`` logs a generated link once at warning and emails it (ND 1), and never raises; no
  other log line, and no column, ever holds a token.
- SETUP, C3 — ``complete_admin_setup``: the password set, the account active, its sessions ended, its other setup links
  revoked, the link consumed; any other token changes nothing; the link of an account already active is revoked (ND 6).
- USAGE, C4 — ``registration_service.user_usage`` counts the pending administrator, once.
- CLI, C5 — ``scripts/user_cli.py``: ``setup-link``, ``cmd_setup_link``, and ``issue_setup_link`` behind it.
- STEP — ``startup_admin_bootstrap(engine)`` runs the bootstrap and leaves the delivery to the background (ND 7); the step
  ``admin-bootstrap`` runs right after ``global-settings``.

Where the contract left the choice: ``deliver_setup_link(result, *, engine=None, now=None)`` opens a session of its own,
as E's background works do (``forgotten_password_work``, ``email_changed_work``): the startup schedules it once its own
session is closed. The email is exactly what ``build_admin_setup`` writes in the instance's language, with the
``LIBREFOLIO_PUBLIC_URL`` link, the link's remaining life as ``ttl`` and the host of that address as the instance (E's
``LinksState.instance``, as every email of E that carries a link).

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the global settings the
startup step before this one seeds (``initialize_global_settings``), opened as production opens its own (aiosqlite,
NullPool — a session is a connection —, the PRAGMA listener of ``backend.app.db.session``), disposed at teardown;
``get_async_engine`` is a tripwire, so nothing here ever opens the lane's database. An autouse fixture removes every
``LIBREFOLIO_ADMIN_*`` (``_FILE`` included), ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_REGISTRATION``,
``LIBREFOLIO_MAX_USERS`` and ``LIBREFOLIO_BLOCKED`` the shell may carry; each test sets its own with ``monkeypatch``. No
email leaves: ``bootstrap_admin_service.send_email`` is an outbox (the monkeypatch point of the contract), whether email
and links are available is E's own ``require_email``/``require_links`` reading the variables, and ``smtp.deliver`` is a
tripwire. bcrypt runs at its lowest cost. No clock wait: every call gets its ``now`` — ``NOW`` is months before the real
clock, so a ``now`` dropped on the way shows —, but ``cmd_setup_link`` and ``startup_admin_bootstrap``, which read the
clock and get scenes dated from it. The log is read with ``structlog.testing.capture_logs`` behind a canary barrier.

Red until lot A7a: ``bootstrap_admin_service`` and the F02 names of ``config.accounts`` do not exist (each test says so on
its own: they are imported lazily), ``issue_token`` takes no ``token``, ``user_usage`` does not count the pending
administrator, ``user_cli`` has no ``setup-link`` and ``STARTUP_STEPS`` no ``admin-bootstrap``.

Lot A7b-2 (N60; A-32 and A-33 of the security review) adds two sections at the end. A32 — the setup ends, whatever the
way: the waiting administrator activated another way (``set_user_active``, ``update_user_status``) or given a password
another way (``reset_password``, ``complete_password_reset``) has its setup links retired in the commit of the change
(``token_service.retire_tokens``: revoked and consumed), so a later deactivation leaves it waiting for nothing; and the
refused link of an account already active retires every setup link of that account. Those ``user_service`` functions
read the clock: the A32 scenes are dated from it, as CLI-003's. A33 — a real change of the waiting administrator's
address in the variables revokes its live setup links (``EXPIRED``, or ``REARMED`` with a token never seen); the same
address in other capitals, the username alone and an address another account holds revoke nothing. Red until A7b-2:
each new red says so on its first contract assertion; the new guards are green today and must stay green.

Lot A-42 + A-43 (the setup link's lifecycle; contract approved by the coordinator, 17/10) adds two more sections at the
end, every new or changed red labelled ``# red until A-42/A-43``. A42 — issuing and spending: ``issue_setup_link`` (the
CLI's ``user setup-link``) and the startup re-arm decide «waiting» under SQLite's write lock, so a setup completed by
another worker between their read and their first write leaves nothing issued — rolled back; the CLI says nobody waits;
the start does not re-arm —; ``complete_admin_setup`` refuses a link while another setup link of the same account is
consumed — the account was set up before, or its links were retired —: nothing changes, the account's never-consumed
setup links are retired, a warning is logged. A43 — deactivation and demotion: ``update_user_status(...,
is_active=False)`` and ``set_user_active(..., False)`` revoke the live setup links of the waiting administrator — it
still waits, a new link one ``./dev.py user setup-link`` away — and retire the never-consumed setup links of an account
that does not wait; ``./dev.py user demote`` refuses the waiting administrator — falsy, a line starting with ❌, nothing
changed — and demotes any other administrator as before. A32-004 loses four variants by construction: its two
deactivations of the account already inactive now revoke the link (A43-001), and its two demotions are now refused at
the CLI (A43-004) and in the Users tab (UADM-072), wherever the refusal lives.

Lot A-50 (the restart's warning; cure approved by the coordinator, 17/10) adds one more section at the end, every new
red labelled ``# red until A-50``. A50 — a restart that finds the waiting administrator without a live setup link
still answers ``EXPIRED`` — the same account, no ``link_token``, nothing written — and its one warning says why: the
link «withdrawn» when the account's most recent setup link — the latest created — is revoked and was never consumed,
«has expired» otherwise; the start that changes the address still says «address changed». A50-001 and A50-002: the
setup cancelled, through the Users tab's PATCH with a token in the configuration, and through the CLI's
``user deactivate`` with a generated link; A50-003: the starts after the one that changed the address; A50-004, a
guard: a link that ran out, an earlier one revoked by a re-arm counting for nothing. The remedy is today's:
``./dev.py user setup-link``, and ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` only when the configuration carries a token. Only
a distinctive word of the warning is pinned, never its sentence: the log is English, for the developer.

Lot A-51 (the setup completed while an operator acts; cure approved by the coordinator, 17/10) adds one section right
after A43's — the same two commands —, every new red labelled ``# red until A-51``. A51 — ``set_user_active(...,
False)`` (``./dev.py user deactivate``) and ``set_user_admin(..., False)`` (``./dev.py user demote``) take SQLite's
write lock, refresh the account, and only then decide their guards: on a fresh F02 instance whose only administrator is
the waiting one, a setup completed between the command's load of the account and its decision makes it the instance's
only active administrator, and the command refuses it as the last active administrator — falsy, its message naming the
last active administrator —, nothing changed since the setup. A51-007 (``user deactivate``; today ``(True, None)``,
«deactivated», while the account stays active and only its sessions end) and A51-008 (``user demote``; today ``(True,
None)``, the only active administrator demoted). The window is played as A42's, without threads: the setup lands after
the command's load of the account or before its first write, whichever comes first.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import importlib
import inspect
import logging
import os
import re
import string
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from urllib.parse import parse_qs

import bcrypt
import pytest
import pytest_asyncio
import structlog
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.util import await_only
from structlog.testing import capture_logs

from backend.app.config import SecretFileError, accounts
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.services.accounts import auth_service, registration_service, token_service, user_service
from backend.app.services.accounts.auth_service import verify_password
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenInspection, TokenStatus, hash_token
from backend.app.services.email import delivery, smtp
from backend.app.services.email.delivery import EmailDeliveryError
from backend.app.services.email.messages import EmailContent, EmailKind, build_admin_setup
from backend.app.services.platform.instance_key import InstanceKeyStatus
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

BOOTSTRAP_MODULE = "backend.app.services.accounts.bootstrap_admin_service"
CONFIG_AUDIT_MODULE = "backend.app.services.platform.config_audit"
APP_LIFESPAN_MODULE = "backend.app.services.platform.app_lifespan"
USER_CLI_MODULE = "scripts.user_cli"
#: The names lot A7a adds to ``backend/app/config/accounts.py``.
F02_NAMES = (
    "ADMIN_EMAIL_VARIABLE",
    "ADMIN_USERNAME_VARIABLE",
    "ADMIN_BOOTSTRAP_TOKEN_VARIABLE",
    "DEFAULT_ADMIN_USERNAME",
    "ADMIN_BOOTSTRAP_TOKEN_MIN_LENGTH",
    "ADMIN_BOOTSTRAP_TOKEN_MAX_LENGTH",
    "AdminBootstrapConfig",
    "AdminBootstrapConfigError",
    "admin_bootstrap_config",
)

EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
USERNAME_VARIABLE = "LIBREFOLIO_ADMIN_USERNAME"
TOKEN_VARIABLE = "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN"
TOKEN_FILE_VARIABLE = f"{TOKEN_VARIABLE}_FILE"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
F02_PREFIX = "LIBREFOLIO_ADMIN_"
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
#: Removed before every test, with every variable of the two prefixes: each changes what the bootstrap, the usage or the
#: delivery decide. ``LIBREFOLIO_BLOCKED`` stops every email (E's D-E13).
INHERITED_VARIABLES = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", BLOCKED_VARIABLE)

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
OTHER_USERNAME = "boss"
OTHER_EMAIL = "boss@example.com"
SETUP_PASSWORD = "Setup-Pass-2026!"
#: What the accounts written as rows hold for a hash: nobody signs in with them.
MARKER_HASH = "$argon2id$seeded-account"
MODE_KEY = "registration_mode"
LANGUAGE_KEY = "default_language"

#: In every token of the variable written here: no message, log line or column may hold it.
CANARY = "ZqF02canary"
TOKEN_ONE = f"{CANARY}-one-0123456789abcdefghijklmnop"
TOKEN_TWO = f"{CANARY}-two-0123456789abcdefghijklmnop"
NEVER_ISSUED = "never-issued-f02-0123456789abcdefghijklmnop"
#: RFC 3986's unreserved characters: the only ones a token that travels in a link may hold (ND 4).
UNRESERVED = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-._~"
SHORTEST_TOKEN = (CANARY + UNRESERVED)[:32]
LONGEST_TOKEN = (CANARY + UNRESERVED * 4)[:200]
TOO_SHORT_TOKEN = SHORTEST_TOKEN[:31]
TOO_LONG_TOKEN = (CANARY + UNRESERVED * 4)[:201]
#: Tokens long enough, each with one character a link cannot carry as it is. The last: ``env_secret`` keeps the spaces
#: around a value (only the email and the username are stripped, ND), so they are characters of the token.
INVALID_CHARACTER_TOKENS = {
    "a-slash": f"{CANARY}/{'x' * 30}",
    "a-plus": f"{CANARY}+{'x' * 30}",
    "a-percent-escape": f"{CANARY}%2F{'x' * 30}",
    "an-equals-sign": f"{CANARY}={'x' * 30}",
    "a-hash": f"{CANARY}#{'x' * 30}",
    "an-inner-space": f"{CANARY} {'x' * 30}",
    "a-non-ascii-letter": f"{CANARY}é{'x' * 30}",
    "surrounding-spaces": f" {TOKEN_ONE} ",
}
#: The limit a length error's message must name, by its code.
RULE_LIMITS = {"ADMIN_BOOTSTRAP_TOKEN_TOO_SHORT": "32", "ADMIN_BOOTSTRAP_TOKEN_TOO_LONG": "200"}
#: secrets.token_urlsafe(32), what the token service generates.
URL_SAFE_256_BITS = re.compile(r"[A-Za-z0-9_-]{43}")

#: Months before the real clock: a ``now`` that does not reach the token service shows.
NOW = datetime(2026, 1, 15, 9, 30, 0, 123456, tzinfo=UTC)
SETUP_TTL = timedelta(hours=72)
HOUR = timedelta(hours=1)
MICROSECOND = timedelta(microseconds=1)

#: The public address of the instance, with a port and a path prefix: the links prove both kept.
PUBLIC_URL = "https://folio.zq-bootstrap.example.com:8443/app"
#: How E's emails name the instance: the host of PUBLIC_URL, with its port.
PUBLIC_HOST = "folio.zq-bootstrap.example.com:8443"
#: A usable SMTP configuration towards a host nothing ever connects to: ``send_email`` is the outbox.
SMTP_HOST = "smtp.zq-bootstrap.example.com"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
SETUP_LINK_COMMAND = "./dev.py user setup-link"
LOG_CANARY = "canary: the capture reaches the logger of the F02 bootstrap"
RACE_ROUNDS = 3
#: A bound for a startup that waits for its delivery — a failure —, never a wait.
STARTUP_BOUND_SECONDS = 15.0
#: Turns given to the event loop, ``asyncio.sleep(0)`` each, for a task just scheduled to start.
LOOP_TURNS = 50

ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
EMPTY = inspect.Parameter.empty


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def f02_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the F02, email and accounts variables of the shell that started the run: each test sets the ones it is about."""
    for name in list(os.environ):
        if name.startswith((F02_PREFIX, SMTP_PREFIX)) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at its lowest cost in this process: real hashes that verify, a hundred times cheaper."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's — the engine must be passed through (startup_admin_bootstrap(engine), deliver_setup_link(..., engine=engine))")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises, in the session module and in the bootstrap module once it exists: a pure test never opens the lane's database."""
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)
    try:
        module = importlib.import_module(BOOTSTRAP_MODULE)
    except Exception:  # red until lot A7a: the tests that need the module say why, each on its own
        return
    if hasattr(module, "get_async_engine"):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire)


@pytest.fixture(autouse=True)
def no_smtp_conversation(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """The SMTP transport refuses to run, and the hourly budget is a private one: no test here talks to a server or spends the process's budget.

    Every email goes through the outbox that replaces ``bootstrap_admin_service.send_email``: reaching ``smtp.deliver``
    means the delivery sent through another ``send_email`` than the one the contract names.
    """
    attempts: list[str] = []

    def refuse(_server: object, message: object) -> None:
        attempts.append(type(message).__name__)
        raise AssertionError("an F02 test reached the SMTP transport")

    monkeypatch.setattr(smtp, "deliver", refuse)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))
    yield attempts
    assert attempts == [], f"the delivery reached the real SMTP transport ({len(attempts)} message(s)): it must send through bootstrap_admin_service.send_email, imported by name"


async def _build_schema(engine: AsyncEngine) -> None:
    """The whole ORM schema, and the global settings the startup step before the bootstrap seeds (``registration_mode`` ``invite``, ``default_language`` ``en``)."""
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        await initialize_global_settings(session)


def _private_engine(path: Path) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path, opened as production opens its own, with the schema and the global settings; disposed at teardown."""
    private = _private_engine(tmp_path / "f02.db")
    try:
        await _build_schema(private)
        yield private
    finally:
        await private.dispose()


def _red_until_a7a(name: str) -> ModuleType:
    """The module ``name``; while lot A7a has not written it, the test that needs it fails on its own, saying so."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as missing:
        if missing.name == name:
            pytest.fail(f"red until lot A7a: {name} does not exist yet", pytrace=False)
        raise


@pytest.fixture
def bootstrap() -> ModuleType:
    """``backend.app.services.accounts.bootstrap_admin_service``: C2, C3, ``issue_setup_link`` and the startup step."""
    return _red_until_a7a(BOOTSTRAP_MODULE)


@pytest.fixture
def f02() -> ModuleType:
    """``backend.app.config.accounts``, holding the F02 names of C1."""
    missing = [name for name in F02_NAMES if not hasattr(accounts, name)]
    if missing:
        pytest.fail(f"red until lot A7a: backend.app.config.accounts has no {', '.join(missing)}", pytrace=False)
    return accounts


@pytest.fixture
def cli() -> ModuleType:
    """``scripts/user_cli.py``, in-process, as the password-policy tests import it."""
    return importlib.import_module(USER_CLI_MODULE)


@pytest.fixture
def audit(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """``config_audit`` with the checks of the other workstreams neutralised — never asserted on —: only F02 can stop it here.

    The JWT secret, the block and its deletion date, the instance key and the checks of the lane's environment would
    otherwise decide too; F02 is reached through ``admin_bootstrap_config()``, which reads the variables, untouched.
    """
    module = importlib.import_module(CONFIG_AUDIT_MODULE)
    monkeypatch.setattr(module, "configured_jwt_secret", lambda: None, raising=False)
    monkeypatch.setattr(module, "instance_blocked", lambda: False, raising=False)
    monkeypatch.setattr(module, "instance_deletion_date", lambda: None, raising=False)
    monkeypatch.setattr(module, "instance_key_status", lambda: InstanceKeyStatus("not_created"), raising=False)
    monkeypatch.setattr(module, "run_config_checks", lambda: [], raising=False)
    return module


@dataclass(frozen=True)
class SentEmail:
    """One call of ``send_email``: what, to whom, for which account."""

    content: EmailContent
    to: str
    user_id: Optional[int]


class Outbox:
    """Stands in for ``send_email`` in the bootstrap module: records every attempt, then raises ``failure`` when one is set."""

    def __init__(self) -> None:
        self.attempts: list[SentEmail] = []
        self.failure: Optional[BaseException] = None

    async def send_email(self, content: EmailContent, *, to: str, user_id: Optional[int] = None) -> None:
        self.attempts.append(SentEmail(content=content, to=to, user_id=user_id))
        if self.failure is not None:
            raise self.failure


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch, bootstrap: ModuleType) -> Outbox:
    """``bootstrap_admin_service.send_email`` replaced by an outbox: the monkeypatch point of the contract."""
    if not hasattr(bootstrap, "send_email"):
        pytest.fail("red until lot A7a: bootstrap_admin_service must import send_email by name (backend.app.services.email.delivery): it is the point this test replaces", pytrace=False)
    box = Outbox()
    monkeypatch.setattr(bootstrap, "send_email", box.send_email)
    return box


# =============================================================================
# HELPERS — the environment
# =============================================================================


def _set_variables(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str]) -> None:
    for name, value in variables.items():
        monkeypatch.setenv(name, value)


def _email_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email usable for E's ``require_email``: a host and a sender, nothing more."""
    monkeypatch.setenv(f"{SMTP_PREFIX}HOST", SMTP_HOST)
    monkeypatch.setenv(f"{SMTP_PREFIX}FROM", SENDER_HEADER)


def _links_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """Links ready for E's ``require_links``: ``LIBREFOLIO_PUBLIC_URL`` set."""
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


# =============================================================================
# HELPERS — the database, read fresh
# =============================================================================


async def _add_user(engine: AsyncEngine, username: str, *, email: Optional[str] = None, active: bool = True, admin: bool = False) -> int:
    """An account written as a row (``<username>@example.com``, a marker hash), as an operator's command line would leave one. Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=MARKER_HASH, is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return user.id


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"account {user_id} is not in the database"
    return user


async def _accounts(engine: AsyncEngine) -> dict[str, tuple[int, str, bool, bool]]:
    """Every account: ``{username: (id, email, is_active, is_superuser)}``."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(User.username, User.id, User.email, User.is_active, User.is_superuser))).all()
    return {username: (user_id, email, bool(active), bool(admin)) for username, user_id, email, active, admin in rows}


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """A token issued by the token service directly, committed: a scene set without the module under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _revoke(engine: AsyncEngine, token_id: int, moment: datetime) -> None:
    async with AsyncSession(engine) as session:
        assert await token_service.revoke_tokens(session, token_id=token_id, now=moment) == 1, "setup: the token must be revoked"
        await session.commit()


async def _consume(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose, moment: datetime) -> None:
    async with AsyncSession(engine) as session:
        assert await token_service.consume_token(session, token, purpose, now=moment) is not None, "setup: the token must be consumed"
        await session.commit()


async def _token_row(engine: AsyncEngine, token_id: int) -> AccountToken:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await session.get(AccountToken, token_id)
    assert record is not None, f"token {token_id} is not in the database"
    return record


async def _inspect(engine: AsyncEngine, token: str, moment: datetime, purpose: AccountTokenPurpose = ADMIN_SETUP) -> TokenInspection:
    """What the token service says of ``token`` at ``moment``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await token_service.inspect_token(session, token, purpose, now=moment)


async def _status(engine: AsyncEngine, token: str, moment: datetime, purpose: AccountTokenPurpose = ADMIN_SETUP) -> TokenStatus:
    return (await _inspect(engine, token, moment, purpose)).status


async def _setup_rows(engine: AsyncEngine, user_id: Optional[int] = None) -> list[AccountToken]:
    """The ``admin_setup`` rows, of one account or of every one, oldest first."""
    statement = select(AccountToken).where(AccountToken.purpose == ADMIN_SETUP).order_by(AccountToken.id)
    if user_id is not None:
        statement = statement.where(AccountToken.user_id == user_id)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return list((await session.execute(statement)).scalars().all())


async def _live_setup_rows(engine: AsyncEngine, moment: datetime) -> list[AccountToken]:
    """The ``admin_setup`` rows still good at ``moment``: neither consumed nor revoked, not expired."""
    return [row for row in await _setup_rows(engine) if row.consumed_at is None and row.revoked_at is None and ensure_utc(row.expires_at) > moment]


async def _setting(engine: AsyncEngine, key: str) -> Optional[str]:
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, key)
        return None if row is None else row.value


async def _set_setting(engine: AsyncEngine, key: str, value: str) -> None:
    """The global setting ``key`` says ``value``, written as a row (the startup seeded it)."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, key)
        assert row is not None, f"setup: initialize_global_settings seeded no {key!r} row"
        row.value = value
        session.add(row)
        await session.commit()


async def _snapshot(engine: AsyncEngine) -> dict[str, list[Any]]:
    """Every account, every account token and every global setting exactly as SQLite holds them: what «nothing written» compares."""
    async with engine.connect() as connection:
        users = (await connection.execute(text("SELECT * FROM users ORDER BY id"))).mappings().all()
        tokens = (await connection.execute(text("SELECT * FROM account_tokens ORDER BY id"))).mappings().all()
        settings = (await connection.execute(text('SELECT "key", "value" FROM global_settings ORDER BY "key"'))).all()
    return {"users": [dict(row) for row in users], "tokens": [dict(row) for row in tokens], "settings": [tuple(row) for row in settings]}


async def _plaintext_in_database(engine: AsyncEngine, plaintexts: list[str]) -> list[str]:
    """``table.column`` of every value, in every table, that holds one of ``plaintexts``."""
    found: list[str] = []
    async with engine.connect() as connection:
        tables = (await connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))).scalars().all()
        for table in tables:
            for row in (await connection.execute(text(f'SELECT * FROM "{table}"'))).mappings().all():
                found.extend(f"{table}.{column}" for column, value in row.items() if value is not None and any(plaintext in str(value) for plaintext in plaintexts))
    return found


async def _usage(engine: AsyncEngine, moment: datetime) -> tuple[int, Optional[int]]:
    """``(used, max_users)`` of ``registration_service.user_usage`` at ``moment``."""
    async with AsyncSession(engine) as session:
        usage = await registration_service.user_usage(session, now=moment)
    return usage.used, usage.max_users


async def _register(engine: AsyncEngine, username: str) -> object:
    """``register_user`` without an invitation, in a session of its own: the account, or the refusal (committed after it, as a careless caller would)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            return await registration_service.register_user(session, username=username, email=f"{username}@example.com", password=SETUP_PASSWORD)
        except registration_service.RegistrationError as refusal:
            await session.commit()
            return refusal


# =============================================================================
# HELPERS — calling the module under test as its callers do
# =============================================================================


def _config(f02: ModuleType, *, email: str = ADMIN_EMAIL, username: str = ADMIN_USERNAME, token: Optional[str] = None) -> Any:
    return f02.AdminBootstrapConfig(email=email, username=username, token=token)


async def _run(engine: AsyncEngine, bootstrap: ModuleType, config: Any, *, now: datetime = NOW, then_commit: bool = False) -> Any:
    """``run_admin_bootstrap`` in a session of its own, as the startup step runs it.

    Without ``then_commit`` only what the run committed itself reaches the database: what it writes, it must commit. With
    it the caller commits afterwards: a run that must write nothing must leave nothing to commit either.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await bootstrap.run_admin_bootstrap(session, config, now=now)
        if then_commit:
            await session.commit()
    return result


async def _created(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, *, token: Optional[str] = None, now: datetime = NOW) -> Any:
    """The F02 administrator (``admin``, ``admin@example.com``) created on the empty instance at ``now``: barrier on ``CREATED``."""
    result = await _run(engine, bootstrap, _config(f02, token=token), now=now)
    assert result.action == bootstrap.BootstrapAction.CREATED and result.user_id is not None, f"setup: the empty instance must create its administrator, got {result!r}"
    return result


async def _complete(engine: AsyncEngine, bootstrap: ModuleType, token: str, *, now: datetime, password: str = SETUP_PASSWORD, then_commit: bool = False) -> Optional[User]:
    """``complete_admin_setup`` in a session of its own; ``then_commit`` as in ``_run``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await bootstrap.complete_admin_setup(session, token, password, now=now)
        if then_commit:
            await session.commit()
    return user


async def _pending_id(engine: AsyncEngine, bootstrap: ModuleType) -> Optional[int]:
    """The id of the account ``pending_admin`` answers, or ``None``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await bootstrap.pending_admin(session)
        return None if user is None else user.id


async def _issue_setup_link(engine: AsyncEngine, bootstrap: ModuleType, *, now: datetime) -> Optional[IssuedToken]:
    """``issue_setup_link`` in a session of its own, committed afterwards — after a ``None`` too: it must have written nothing."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await bootstrap.issue_setup_link(session, now=now)
        await session.commit()
    return issued


async def _yield_until(condition: Callable[[], bool]) -> bool:
    """Up to ``LOOP_TURNS`` turns of the event loop — ``asyncio.sleep(0)``, never a clock wait — until ``condition`` holds."""
    for _ in range(LOOP_TURNS):
        if condition():
            return True
        await asyncio.sleep(0)
    return condition()


# =============================================================================
# HELPERS — the log
# =============================================================================


@contextlib.contextmanager
def _captured(bootstrap: ModuleType) -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through the bootstrap module's own logger (its ``logger``, or the structlog logger of its name) must be among them.

    Without it, a capture that misses the module's events would pass every «nothing logged» for a module that logs where
    nobody looks.
    """
    canary_logger = getattr(bootstrap, "logger", None)
    if canary_logger is None:
        canary_logger = structlog.get_logger(bootstrap.__name__)
    with capture_logs() as events:
        canary_logger.debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the events of the bootstrap module's logger do not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _logged(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The captured events, the canary aside."""
    return [event for event in events if event.get("event") != LOG_CANARY]


def _holding(events: list[dict[str, Any]], secret: str) -> list[dict[str, Any]]:
    """The events that hold ``secret`` anywhere: in their message or in any field."""
    return [event for event in _logged(events) if secret in repr(event)]


def _at_level(events: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
    return [event for event in _logged(events) if event.get("log_level") == level]


# =============================================================================
# SCENES — what the instance holds before the call; each returns the id of its pending administrator, if it has one
# =============================================================================

Scene = Callable[[AsyncEngine, ModuleType, ModuleType], Awaitable[Optional[int]]]


async def _no_account(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    """An instance without accounts."""
    return None


async def _an_active_account(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    """An account an operator created: active, not the F02 administrator."""
    await _add_user(engine, "alice")
    return None


async def _an_inactive_account(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    """A deactivated account, without any setup link."""
    await _add_user(engine, "carol", active=False)
    return None


async def _a_pending_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    """The F02 administrator created at NOW, its generated link live: the pending administrator."""
    return (await _created(engine, bootstrap, f02)).user_id


async def _an_administrator_after_its_setup(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    """The F02 administrator created at NOW, its setup completed half an hour later: active, pending no more."""
    created = await _created(engine, bootstrap, f02)
    assert await _complete(engine, bootstrap, created.link_token, now=NOW + timedelta(minutes=30)) is not None, "setup: the administrator completes its setup"
    return None


async def _inactive_with_a_setup_link(engine: AsyncEngine, state: str) -> int:
    """An inactive superuser written as a row, with one ``admin_setup`` link issued directly, ``live``, ``expired``, ``revoked`` or ``consumed``."""
    user_id = await _add_user(engine, "carol", active=False, admin=True)
    issued = await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW - SETUP_TTL - HOUR if state == "expired" else NOW)
    if state == "revoked":
        await _revoke(engine, issued.record.id, NOW + timedelta(minutes=5))
    elif state == "consumed":
        await _consume(engine, issued.token, ADMIN_SETUP, NOW + timedelta(minutes=5))
    return user_id


async def _with_a_live_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    return await _inactive_with_a_setup_link(engine, "live")


async def _with_an_expired_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    return await _inactive_with_a_setup_link(engine, "expired")


async def _with_a_revoked_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    return await _inactive_with_a_setup_link(engine, "revoked")


async def _with_a_consumed_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    await _inactive_with_a_setup_link(engine, "consumed")
    return None


async def _with_a_consumed_and_a_live_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    user_id = await _inactive_with_a_setup_link(engine, "consumed")
    await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW)
    return None


async def _active_with_a_live_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    user_id = await _add_user(engine, "carol", admin=True)
    await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW)
    return None


async def _inactive_with_a_reset_link_only(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> Optional[int]:
    user_id = await _add_user(engine, "carol", active=False)
    await _issue(engine, PASSWORD_RESET, user_id=user_id, now=NOW)
    return None


# =============================================================================
# CFG — C1, THE CONFIGURATION
# =============================================================================


def test_the_f02_constants(f02: ModuleType) -> None:
    """CFG-001 — C1: the three variables by name, the default username ``admin``, and the length limits of the token, 32 and 200."""
    print_section("CFG-001: constants")

    assert (f02.ADMIN_EMAIL_VARIABLE, f02.ADMIN_USERNAME_VARIABLE, f02.ADMIN_BOOTSTRAP_TOKEN_VARIABLE) == (EMAIL_VARIABLE, USERNAME_VARIABLE, TOKEN_VARIABLE)
    assert f02.DEFAULT_ADMIN_USERNAME == "admin"
    assert (f02.ADMIN_BOOTSTRAP_TOKEN_MIN_LENGTH, f02.ADMIN_BOOTSTRAP_TOKEN_MAX_LENGTH) == (32, 200)
    print_success("three variables, 'admin', 32 to 200")


def test_the_config_is_a_frozen_dataclass_and_its_error_a_value_error(f02: ModuleType) -> None:
    """CFG-002 — C1: ``AdminBootstrapConfig(email, username, token)``, a frozen dataclass; ``AdminBootstrapConfigError``, a ``ValueError`` (its ``variable`` and ``code`` are read in CFG-006)."""
    print_section("CFG-002: AdminBootstrapConfig and AdminBootstrapConfigError")
    config = f02.AdminBootstrapConfig(email=ADMIN_EMAIL, username=ADMIN_USERNAME, token=None)

    assert dataclasses.is_dataclass(f02.AdminBootstrapConfig)
    assert [field.name for field in dataclasses.fields(f02.AdminBootstrapConfig)] == ["email", "username", "token"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.username = OTHER_USERNAME
    assert issubclass(f02.AdminBootstrapConfigError, ValueError)
    print_success("a frozen (email, username, token); a ValueError")


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="nothing-set"),
        pytest.param({EMAIL_VARIABLE: "", USERNAME_VARIABLE: "", TOKEN_VARIABLE: ""}, id="all-empty"),
        pytest.param({EMAIL_VARIABLE: "  ", USERNAME_VARIABLE: "\t", TOKEN_VARIABLE: " \n "}, id="all-blank"),
        pytest.param({TOKEN_FILE_VARIABLE: "   "}, id="blank-token-file-variable"),
    ],
)
def test_f02_is_off_while_none_of_its_variables_is_set(f02: ModuleType, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str]) -> None:
    """CFG-003 — C1: none of the three variables set — an empty or blank value counting as unset, the token's ``_FILE`` included —: ``None``, F02 off."""
    _set_variables(monkeypatch, variables)

    assert f02.admin_bootstrap_config() is None, f"{sorted(variables)} blank or unset: F02 must be off"


CONFIG_VALID = [
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL}, (ADMIN_EMAIL, "admin", None), id="the-email-alone"),
    pytest.param({EMAIL_VARIABLE: f"  {ADMIN_EMAIL} \t"}, (ADMIN_EMAIL, "admin", None), id="email-surrounding-whitespace-ignored"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: f"  {OTHER_USERNAME}\n"}, (ADMIN_EMAIL, OTHER_USERNAME, None), id="username-surrounding-whitespace-ignored"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "   "}, (ADMIN_EMAIL, "admin", None), id="blank-username-is-the-default"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: " \t "}, (ADMIN_EMAIL, "admin", None), id="blank-token-is-no-token"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "abc"}, (ADMIN_EMAIL, "abc", None), id="username-of-3-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "u" * 50}, (ADMIN_EMAIL, "u" * 50, None), id="username-of-50-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: TOKEN_ONE}, (ADMIN_EMAIL, "admin", TOKEN_ONE), id="a-token"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: UNRESERVED}, (ADMIN_EMAIL, "admin", UNRESERVED), id="token-of-every-unreserved-character"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: SHORTEST_TOKEN}, (ADMIN_EMAIL, "admin", SHORTEST_TOKEN), id="token-of-32-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: LONGEST_TOKEN}, (ADMIN_EMAIL, "admin", LONGEST_TOKEN), id="token-of-200-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: OTHER_USERNAME, TOKEN_VARIABLE: TOKEN_ONE}, (ADMIN_EMAIL, OTHER_USERNAME, TOKEN_ONE), id="all-three"),
]


@pytest.mark.parametrize(("variables", "expected"), CONFIG_VALID)
def test_the_email_turns_f02_on(f02: ModuleType, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], expected: tuple[str, str, Optional[str]]) -> None:
    """CFG-004 — C1: with the email F02 is on: the username ``admin`` unless set (blank is unset), the email and the username without their surrounding whitespace (ND), the token as written — any of the unreserved characters, 32 to 200 of them —, none when blank."""
    _set_variables(monkeypatch, variables)
    email, username, token = expected

    config = f02.admin_bootstrap_config()

    assert config == f02.AdminBootstrapConfig(email=email, username=username, token=token), f"{variables}: expected ({email!r}, {username!r}, {token!r}), got {config!r}"


def test_the_token_can_come_from_its_file(f02: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CFG-005 — C1: the token is read with ``env_secret``: ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`` names a file holding it, whose trailing line break is not part of it."""
    print_section("CFG-005: the token from its file")
    path = tmp_path / "admin-bootstrap-token"
    path.write_text(f"{TOKEN_ONE}\n", encoding="utf-8")
    monkeypatch.setenv(EMAIL_VARIABLE, ADMIN_EMAIL)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))

    config = f02.admin_bootstrap_config()

    assert config == f02.AdminBootstrapConfig(email=ADMIN_EMAIL, username=ADMIN_USERNAME, token=TOKEN_ONE), f"the token of {TOKEN_FILE_VARIABLE}, without its line break: got {config!r}"
    print_success("the token read from its file")


CONFIG_ERRORS = [
    pytest.param({TOKEN_VARIABLE: TOKEN_ONE}, "ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL", TOKEN_VARIABLE, id="token-without-email"),
    pytest.param({TOKEN_VARIABLE: TOKEN_ONE, EMAIL_VARIABLE: "  "}, "ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL", TOKEN_VARIABLE, id="token-with-a-blank-email"),
    pytest.param({USERNAME_VARIABLE: OTHER_USERNAME}, "ADMIN_USERNAME_WITHOUT_EMAIL", USERNAME_VARIABLE, id="username-without-email"),
    pytest.param({EMAIL_VARIABLE: "not-an-email"}, "ADMIN_EMAIL_INVALID", EMAIL_VARIABLE, id="email-without-an-at-sign"),
    pytest.param({EMAIL_VARIABLE: "admin@"}, "ADMIN_EMAIL_INVALID", EMAIL_VARIABLE, id="email-without-a-domain"),
    pytest.param({EMAIL_VARIABLE: "admin@example"}, "ADMIN_EMAIL_INVALID", EMAIL_VARIABLE, id="email-domain-without-a-period"),
    pytest.param({EMAIL_VARIABLE: "two words@example.com"}, "ADMIN_EMAIL_INVALID", EMAIL_VARIABLE, id="email-with-a-space"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "ab"}, "ADMIN_USERNAME_INVALID", USERNAME_VARIABLE, id="username-of-2-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "  ab  "}, "ADMIN_USERNAME_INVALID", USERNAME_VARIABLE, id="username-of-2-characters-once-stripped"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "u" * 51}, "ADMIN_USERNAME_INVALID", USERNAME_VARIABLE, id="username-of-51-characters"),
    *[pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: token}, "ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS", TOKEN_VARIABLE, id=f"token-with-{name}") for name, token in INVALID_CHARACTER_TOKENS.items()],
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: TOO_SHORT_TOKEN}, "ADMIN_BOOTSTRAP_TOKEN_TOO_SHORT", TOKEN_VARIABLE, id="token-of-31-characters"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: TOO_LONG_TOKEN}, "ADMIN_BOOTSTRAP_TOKEN_TOO_LONG", TOKEN_VARIABLE, id="token-of-201-characters"),
]


@pytest.mark.parametrize(("variables", "code", "variable"), CONFIG_ERRORS)
def test_a_broken_f02_variable_is_an_error_naming_it_and_never_the_token(f02: ModuleType, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], code: str, variable: str) -> None:
    """CFG-006 — C1: ``AdminBootstrapConfigError`` with its ``code`` and ``variable`` exactly: a token or a username without the email (ND 5), an email ``EmailStr`` refuses, a username shorter than 3 or longer than 50 characters once stripped, a token holding a character outside ``A-Z a-z 0-9 - . _ ~`` (ND 4: it travels in a link), shorter than 32 or longer than 200. Its message names the variable — and the limit, for a length — and never the token, not even a part of it."""
    _set_variables(monkeypatch, variables)

    with pytest.raises(f02.AdminBootstrapConfigError) as raised:
        f02.admin_bootstrap_config()

    error = raised.value
    message = str(error)
    assert (error.code, error.variable) == (code, variable), f"{variables}: expected {code} on {variable}, got {error.code!r} on {error.variable!r}: {message!r}"
    assert variable in message, f"the message must name {variable}: {message!r}"
    assert CANARY not in message and CANARY not in repr(error.args), f"the message must never hold the token: {message!r}"
    assert RULE_LIMITS.get(code, "") in message, f"the message must name the limit, {RULE_LIMITS.get(code)}: {message!r}"


@pytest.mark.parametrize("content", [None, b"", b"  \n"], ids=["missing-file", "empty-file", "blank-file"])
def test_a_token_file_that_cannot_give_its_token_is_a_secret_file_error(f02: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: Optional[bytes]) -> None:
    """CFG-007 — C1: ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`` naming a file that is missing, empty or blank: ``SecretFileError`` from ``env_secret``, naming the variable."""
    path = tmp_path / "admin-bootstrap-token"
    if content is not None:
        path.write_bytes(content)
    monkeypatch.setenv(EMAIL_VARIABLE, ADMIN_EMAIL)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))

    with pytest.raises(SecretFileError) as raised:
        f02.admin_bootstrap_config()

    assert TOKEN_FILE_VARIABLE in str(raised.value), f"the error must name {TOKEN_FILE_VARIABLE}: {raised.value}"


def test_the_variables_are_read_at_every_call(f02: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """CFG-008 — C1: read at call time, never cached: off, then on with the email, then with a username, then — the email gone — the username alone is an error."""
    print_section("CFG-008: read at every call")

    assert f02.admin_bootstrap_config() is None
    monkeypatch.setenv(EMAIL_VARIABLE, ADMIN_EMAIL)
    assert f02.admin_bootstrap_config() == f02.AdminBootstrapConfig(email=ADMIN_EMAIL, username=ADMIN_USERNAME, token=None)
    monkeypatch.setenv(USERNAME_VARIABLE, OTHER_USERNAME)
    assert f02.admin_bootstrap_config() == f02.AdminBootstrapConfig(email=ADMIN_EMAIL, username=OTHER_USERNAME, token=None)
    monkeypatch.delenv(EMAIL_VARIABLE)
    with pytest.raises(f02.AdminBootstrapConfigError) as raised:
        f02.admin_bootstrap_config()
    assert raised.value.code == "ADMIN_USERNAME_WITHOUT_EMAIL"
    print_success("each call reads the variables as they are")


AUDIT_STOPS = [
    pytest.param({TOKEN_VARIABLE: TOKEN_ONE}, "ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL", id="token-without-email"),
    pytest.param({USERNAME_VARIABLE: OTHER_USERNAME}, "ADMIN_USERNAME_WITHOUT_EMAIL", id="username-without-email"),
    pytest.param({EMAIL_VARIABLE: "not-an-email"}, "ADMIN_EMAIL_INVALID", id="invalid-email"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: "ab"}, "ADMIN_USERNAME_INVALID", id="short-username"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: INVALID_CHARACTER_TOKENS["a-slash"]}, "ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS", id="token-with-a-slash"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: TOO_SHORT_TOKEN}, "ADMIN_BOOTSTRAP_TOKEN_TOO_SHORT", id="short-token"),
    pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, TOKEN_VARIABLE: TOO_LONG_TOKEN}, "ADMIN_BOOTSTRAP_TOKEN_TOO_LONG", id="long-token"),
]


@pytest.mark.parametrize(("variables", "code"), AUDIT_STOPS)
def test_the_startup_audit_stops_on_a_broken_f02_variable(f02: ModuleType, audit: ModuleType, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], code: str) -> None:
    """CFG-009 — C1, ND 2: ``log_configuration_audit()`` calls ``admin_bootstrap_config()``, so a broken F02 variable raises ``AdminBootstrapConfigError`` out of it and the server does not start. The audit opens no database — ``get_async_engine`` is a tripwire here —, so it stops whatever the instance holds, accounts included."""
    _set_variables(monkeypatch, variables)

    with pytest.raises(f02.AdminBootstrapConfigError) as raised:
        audit.log_configuration_audit()

    assert raised.value.code == code, f"expected {code}, got {raised.value.code!r}: {raised.value}"
    assert CANARY not in str(raised.value), f"the error that stops the start must not hold the token: {raised.value}"


def test_the_startup_audit_stops_on_a_token_file_that_cannot_be_read(f02: ModuleType, audit: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CFG-010 — C1, ND 2: a ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`` that cannot be read stops the start too: the ``SecretFileError`` of ``admin_bootstrap_config()`` comes out of the audit, as an unreadable ``JWT_SECRET_FILE`` does."""
    monkeypatch.setenv(EMAIL_VARIABLE, ADMIN_EMAIL)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(tmp_path / "no-such-token-file"))

    with pytest.raises(SecretFileError):
        audit.log_configuration_audit()


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="f02-off"),
        pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL}, id="the-email-alone"),
        pytest.param({EMAIL_VARIABLE: ADMIN_EMAIL, USERNAME_VARIABLE: OTHER_USERNAME, TOKEN_VARIABLE: TOKEN_ONE}, id="all-three-valid"),
    ],
)
def test_the_startup_audit_goes_on_with_f02_off_or_valid(f02: ModuleType, audit: ModuleType, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str]) -> None:
    """CFG-011 — C1, ND 2: F02 off, or every F02 variable valid: the audit does not raise because of F02."""
    _set_variables(monkeypatch, variables)

    assert audit.log_configuration_audit() is None


# =============================================================================
# TOKEN — issue_token(..., token=...)
# =============================================================================


def test_issue_token_takes_a_token_keyword() -> None:
    """TOKEN-001 — token service: ``issue_token`` takes ``token``, keyword-only, ``None`` by default."""
    parameter = inspect.signature(token_service.issue_token).parameters.get("token")

    assert parameter is not None, "red until lot A7a: issue_token has no token= keyword"
    assert (parameter.kind, parameter.default) == (KEYWORD_ONLY, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(AccountTokenPurpose))
async def test_a_given_token_is_stored_by_its_hash_and_handed_back(engine: AsyncEngine, purpose: AccountTokenPurpose) -> None:
    """TOKEN-002 — token service: given ``token``, ``IssuedToken.token`` is it, the row holds its hash — the plaintext in no column —, with the purpose's lifetime, and ``inspect_token`` answers ``valid``."""
    print_section(f"TOKEN-002: a given token, {purpose.value}")
    owner = await _add_user(engine, "alice")

    issued = await _issue(engine, purpose, user_id=None if purpose == INVITE else owner, token=TOKEN_ONE, now=NOW)

    stored = await _token_row(engine, issued.record.id)
    inspection = await _inspect(engine, TOKEN_ONE, NOW, purpose)
    assert issued.token == TOKEN_ONE
    assert (stored.token_hash, ensure_utc(stored.expires_at)) == (hash_token(TOKEN_ONE), NOW + DEFAULT_TTL[purpose])
    assert inspection.status == TokenStatus.VALID and inspection.record is not None and inspection.record.id == issued.record.id
    assert await _plaintext_in_database(engine, [TOKEN_ONE]) == []
    print_success(f"{purpose.value}: stored as its hash, valid")


@pytest.mark.asyncio
async def test_an_empty_given_token_is_refused_and_adds_nothing(engine: AsyncEngine) -> None:
    """TOKEN-003 — token service: ``token=""`` is a ``ValueError``, and the caller's transaction is left as it was."""
    owner = await _add_user(engine, "alice")

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await token_service.issue_token(session, ADMIN_SETUP, user_id=owner, token="", now=NOW)
        tokens = (await session.execute(select(func.count()).select_from(AccountToken))).scalar_one()

    assert tokens == 0, "a refused issue must add nothing to the caller's transaction"


@pytest.mark.asyncio
async def test_without_a_given_token_one_is_generated_as_before(engine: AsyncEngine) -> None:
    """TOKEN-004 — token service: without ``token``, or with ``token=None``, a new secret is generated as before — 256 bits, URL-safe —, valid, a different one each time."""
    owner = await _add_user(engine, "alice")

    implicit = await _issue(engine, ADMIN_SETUP, user_id=owner, now=NOW)
    explicit = await _issue(engine, ADMIN_SETUP, user_id=owner, token=None, now=NOW)

    for issued in (implicit, explicit):
        assert URL_SAFE_256_BITS.fullmatch(issued.token), f"expected secrets.token_urlsafe(32), got {len(issued.token)} characters"
        assert await _status(engine, issued.token, NOW) == TokenStatus.VALID
    assert implicit.token != explicit.token


@pytest.mark.asyncio
async def test_a_given_token_is_never_logged(engine: AsyncEngine) -> None:
    """TOKEN-005 — token service: issuing a given token logs its issue (the barrier: the capture hears the token service) and never the token."""
    owner = await _add_user(engine, "alice")

    with capture_logs() as events:
        await _issue(engine, ADMIN_SETUP, user_id=owner, token=TOKEN_ONE, now=NOW)

    assert any(event.get("event") == "Account token issued" for event in events), f"barrier: the issue is not among the captured events: {events}"
    assert [event for event in events if TOKEN_ONE in repr(event)] == [], f"a log event holds the given token: {events}"


# =============================================================================
# BOOT — C2, THE BOOTSTRAP
# =============================================================================

EXPECTED_SIGNATURES = {
    "run_admin_bootstrap": [("session", POSITIONAL, EMPTY), ("config", POSITIONAL, EMPTY), ("now", KEYWORD_ONLY, None)],
    "pending_admin": [("session", POSITIONAL, EMPTY)],
    "complete_admin_setup": [("session", POSITIONAL, EMPTY), ("token", POSITIONAL, EMPTY), ("new_password", POSITIONAL, EMPTY), ("now", KEYWORD_ONLY, None)],
    "deliver_setup_link": [("result", POSITIONAL, EMPTY), ("engine", KEYWORD_ONLY, None), ("now", KEYWORD_ONLY, None)],
    "issue_setup_link": [("session", POSITIONAL, EMPTY), ("now", KEYWORD_ONLY, None)],
    "startup_admin_bootstrap": [("engine", POSITIONAL, None)],
}


def test_the_bootstrap_vocabulary(bootstrap: ModuleType) -> None:
    """BOOT-001 — C2: ``BootstrapAction``, a StrEnum of six actions; ``BootstrapResult(action, user_id=None, username=None, link_token=None, expires_at=None)``, frozen."""
    print_section("BOOT-001: BootstrapAction and BootstrapResult")
    action_type, result_type = bootstrap.BootstrapAction, bootstrap.BootstrapResult

    assert issubclass(action_type, StrEnum)
    assert {action.name: action.value for action in action_type} == {"OFF": "off", "IGNORED": "ignored", "CREATED": "created", "REARMED": "rearmed", "PENDING": "pending", "EXPIRED": "expired"}
    assert [(field.name, field.default) for field in dataclasses.fields(result_type)] == [("action", dataclasses.MISSING), ("user_id", None), ("username", None), ("link_token", None), ("expires_at", None)]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result_type(action=action_type.OFF).action = action_type.CREATED
    print_success("six actions; a frozen result")


def test_the_bootstrap_functions_are_coroutines_with_their_signatures(bootstrap: ModuleType) -> None:
    """BOOT-002 — C2, C3, C5, startup: every function is a coroutine function with the parameters of the contract; ``deliver_setup_link(result, *, engine=None, now=None)`` opens a session of its own, as E's background works do."""
    print_section("BOOT-002: signatures")
    missing = [name for name in EXPECTED_SIGNATURES if not hasattr(bootstrap, name)]
    assert not missing, f"red until lot A7a: bootstrap_admin_service has no {missing}"

    signatures = {name: [(parameter.name, parameter.kind, parameter.default) for parameter in inspect.signature(getattr(bootstrap, name)).parameters.values()] for name in EXPECTED_SIGNATURES}
    coroutines = sorted(name for name in EXPECTED_SIGNATURES if inspect.iscoroutinefunction(getattr(bootstrap, name)))

    assert signatures == EXPECTED_SIGNATURES
    assert coroutines == sorted(EXPECTED_SIGNATURES), f"every one is a coroutine function: only {coroutines}"
    print_success(f"{len(EXPECTED_SIGNATURES)} coroutine functions")


@pytest.mark.asyncio
@pytest.mark.parametrize("scene", [pytest.param(_no_account, id="empty-instance"), pytest.param(_a_pending_administrator, id="a-pending-administrator"), pytest.param(_an_active_account, id="an-active-account")])
async def test_without_a_config_the_bootstrap_is_off_and_writes_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, scene: Scene) -> None:
    """BOOT-003 — C2: ``config`` ``None`` — F02 off —: ``BootstrapResult(action=OFF)`` and nothing written, whatever the instance holds: no account, no link, the ``registration_mode`` row as it was (``open`` here, so a write would show)."""
    await scene(engine, bootstrap, f02)
    await _set_setting(engine, MODE_KEY, "open")
    before = await _snapshot(engine)

    result = await _run(engine, bootstrap, None, now=NOW + HOUR, then_commit=True)

    assert result == bootstrap.BootstrapResult(action=bootstrap.BootstrapAction.OFF), f"F02 off: expected OFF and nothing else, got {result!r}"
    assert await _snapshot(engine) == before, "F02 off must write nothing"


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_mode", ["invite", "open"])
async def test_an_empty_instance_creates_the_administrator_with_a_generated_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, stored_mode: str) -> None:
    """BOOT-004 — C2: the ``users`` table empty, no token in the config: ``CREATED``. One account, the config's username and email, inactive, a superuser, whose password is the bcrypt hash of a random secret (``$2``…, and no guess verifies — not even the link); ``registration_mode`` ``invite``, even where it said ``open``; one ``admin_setup`` link of that account until ``now`` + 72 h, generated by the token service, its plaintext in ``link_token`` and valid; ``user_id``, ``username`` and ``expires_at`` in the result. The first-account rule is off by itself: ``first_account_open`` is false, and a registration without an invitation is ``INVITE_REQUIRED``."""
    print_section(f"BOOT-004: CREATED, registration_mode {stored_mode!r} before")
    await _set_setting(engine, MODE_KEY, stored_mode)

    result = await _run(engine, bootstrap, _config(f02), now=NOW)

    assert isinstance(result.action, bootstrap.BootstrapAction) and result.action == bootstrap.BootstrapAction.CREATED, f"expected CREATED: {result!r}"
    assert result.username == ADMIN_USERNAME and result.expires_at is not None and ensure_utc(result.expires_at) == NOW + SETUP_TTL, f"the result names the account and the link's expiry: {result!r}"
    assert isinstance(result.link_token, str) and URL_SAFE_256_BITS.fullmatch(result.link_token), f"link_token must be the generated link's plaintext: {result!r}"
    assert await _accounts(engine) == {ADMIN_USERNAME: (result.user_id, ADMIN_EMAIL, False, True)}, "one inactive superuser, with the config's username and email"
    hashed = (await _account(engine, result.user_id)).hashed_password
    assert hashed.startswith("$2"), f"the password must be a bcrypt hash, never a placeholder: {hashed[:8]!r}…"
    try:
        bcrypt.checkpw(b"admin", hashed.encode())
    except ValueError as malformed:
        pytest.fail(f"the password must be a well-formed bcrypt hash: {malformed}")
    guesses = ["", ADMIN_USERNAME, ADMIN_EMAIL, "password", "changeme", SETUP_PASSWORD, result.link_token]
    assert [guess for guess in guesses if verify_password(guess, hashed)] == [], "no known password may log the account in"
    assert await _setting(engine, MODE_KEY) == "invite", "registration_mode must say invite"
    rows = await _setup_rows(engine, result.user_id)
    assert [(row.token_hash, ensure_utc(row.expires_at), row.consumed_at, row.revoked_at) for row in rows] == [(hash_token(result.link_token), NOW + SETUP_TTL, None, None)], "one live admin_setup link, until now + 72 h"
    assert await _status(engine, result.link_token, NOW) == TokenStatus.VALID
    async with AsyncSession(engine) as session:
        assert await registration_service.first_account_open(session) is False, "the instance holds an account now: the first-account rule is off"
    walkin = await _register(engine, "walkin")
    assert isinstance(walkin, registration_service.RegistrationError) and walkin.code == "INVITE_REQUIRED", f"a stranger must not register: {walkin!r}"
    assert set(await _accounts(engine)) == {ADMIN_USERNAME}
    print_success("an inactive superuser, its link valid 72 h; registration by invitation")


@pytest.mark.asyncio
async def test_an_empty_instance_creates_the_administrator_with_the_variables_token(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """BOOT-005 — C2: with a token in the config, ``CREATED`` stores that token — its hash —, as the account's one ``admin_setup`` link until ``now`` + 72 h, ``valid``; ``link_token`` is ``None``: the hosting provider delivers the link itself."""
    print_section("BOOT-005: CREATED with the variable's token")
    await _set_setting(engine, MODE_KEY, "open")

    result = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW)

    assert (result.action, result.username, result.link_token) == (bootstrap.BootstrapAction.CREATED, ADMIN_USERNAME, None), f"expected CREATED, without a link_token: {result!r}"
    assert await _accounts(engine) == {ADMIN_USERNAME: (result.user_id, ADMIN_EMAIL, False, True)}
    rows = await _setup_rows(engine, result.user_id)
    assert [(row.token_hash, ensure_utc(row.expires_at)) for row in rows] == [(hash_token(TOKEN_ONE), NOW + SETUP_TTL)], "the variable's token, stored by its hash, until now + 72 h"
    assert await _status(engine, TOKEN_ONE, NOW) == TokenStatus.VALID
    assert await _setting(engine, MODE_KEY) == "invite"
    print_success("the variable's token is the setup link")


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, TOKEN_ONE], ids=["generated-link", "variable-token"])
async def test_two_bootstraps_racing_on_an_empty_instance_create_one_administrator(tmp_path: Path, bootstrap: ModuleType, f02: ModuleType, token: Optional[str]) -> None:
    """BOOT-006 — C2: two ``run_admin_bootstrap`` at once on the same empty database — two engines, so two connections, as two workers starting together —: one answers ``CREATED``, the other ``PENDING``, having found the account the first created; the database holds one account, that one, and one live ``admin_setup`` link, the winner's.

    Neither may raise: whatever SQLite answers the loser (the unique username, a stale snapshot, the busy lock), it ends
    in ``PENDING``. A fresh database each round; no sleep: the two are held together by ``asyncio.gather`` alone.
    """
    print_section(f"BOOT-006: two bootstraps racing, {'the variable token' if token else 'a generated link'}")
    config = _config(f02, token=token)
    for race in range(RACE_ROUNDS):
        path = tmp_path / f"race-{race}.db"
        first, second = _private_engine(path), _private_engine(path)
        try:
            await _build_schema(first)
            outcomes = await asyncio.gather(_run(first, bootstrap, config), _run(second, bootstrap, config), return_exceptions=True)

            crashed = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
            assert not crashed, f"race {race}: a bootstrap failed instead of answering: {crashed!r}"
            assert sorted(outcome.action for outcome in outcomes) == ["created", "pending"], f"race {race}: expected one CREATED and one PENDING: {outcomes!r}"
            created = next(outcome for outcome in outcomes if outcome.action == bootstrap.BootstrapAction.CREATED)
            loser = next(outcome for outcome in outcomes if outcome.action == bootstrap.BootstrapAction.PENDING)
            assert loser.link_token is None, f"race {race}: PENDING never hands out a link: {loser!r}"
            assert await _accounts(first) == {ADMIN_USERNAME: (created.user_id, ADMIN_EMAIL, False, True)}, f"race {race}: one account, the winner's"
            live = await _live_setup_rows(first, NOW)
            assert [(row.user_id, row.token_hash) for row in live] == [(created.user_id, hash_token(token or created.link_token))], f"race {race}: one live setup link, the winner's"
        finally:
            await first.dispose()
            await second.dispose()
    print_success(f"{RACE_ROUNDS} races: one administrator, one live link each")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scene",
    [
        pytest.param(_an_active_account, id="an-active-account"),
        pytest.param(_an_inactive_account, id="an-inactive-account-without-a-setup-link"),
        pytest.param(_an_administrator_after_its_setup, id="the-f02-administrator-after-its-setup"),
    ],
)
async def test_accounts_without_a_pending_administrator_are_ignored(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, scene: Scene) -> None:
    """BOOT-007 — C2: the instance holds accounts and none is a pending administrator — an operator's account, a deactivated one, or the F02 administrator once its setup is completed —: ``IGNORED`` and nothing written, even with another username, another email and a new token in the config: no account, no rename, no link, the ``registration_mode`` row as it was."""
    await scene(engine, bootstrap, f02)
    await _set_setting(engine, MODE_KEY, "open")
    before = await _snapshot(engine)

    result = await _run(engine, bootstrap, _config(f02, email=OTHER_EMAIL, username=OTHER_USERNAME, token=TOKEN_TWO), now=NOW + 2 * HOUR, then_commit=True)

    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.IGNORED, None), f"expected IGNORED: {result!r}"
    assert await _snapshot(engine) == before, "IGNORED must write nothing"


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, TOKEN_ONE], ids=["generated-link", "variable-token"])
async def test_a_restart_finds_the_pending_administrator_and_writes_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, token: Optional[str]) -> None:
    """BOOT-008 — C2: a restart an hour later with the same config, the administrator's link still live: ``PENDING``, no ``link_token``, nothing written — no new link, the live one untouched — and the link is not logged again."""
    print_section(f"BOOT-008: a restart, {'the variable token' if token else 'a generated link'}")
    created = await _created(engine, bootstrap, f02, token=token)
    link = token or created.link_token
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        again = await _run(engine, bootstrap, _config(f02, token=token), now=NOW + HOUR, then_commit=True)

    assert (again.action, again.link_token) == (bootstrap.BootstrapAction.PENDING, None), f"expected PENDING: {again!r}"
    assert await _snapshot(engine) == before, "PENDING must write nothing"
    assert await _status(engine, link, NOW + HOUR) == TokenStatus.VALID
    assert _holding(events, link) == [], "a restart must not log the link again"
    print_success("PENDING, nothing written, nothing logged")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        pytest.param(SETUP_TTL - MICROSECOND, "pending", id="a-microsecond-before-expiry-pending"),
        pytest.param(SETUP_TTL, "expired", id="at-expiry-expired"),
        pytest.param(SETUP_TTL + HOUR, "expired", id="after-expiry-expired"),
    ],
)
async def test_the_link_is_live_until_its_expiry_exactly(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, elapsed: timedelta, expected: str) -> None:
    """BOOT-009 — C2: «live» as the token service says it — expired at ``expires_at`` exactly —: a microsecond before, a restart is ``PENDING``; at the expiry and after, ``EXPIRED``; nothing written either way."""
    await _created(engine, bootstrap, f02)
    before = await _snapshot(engine)

    result = await _run(engine, bootstrap, _config(f02), now=NOW + elapsed, then_commit=True)

    assert result.action == expected, f"{elapsed} after the creation: expected {expected}, got {result!r}"
    assert await _snapshot(engine) == before


REARM_CASES = [
    pytest.param(None, HOUR, True, id="over-a-live-generated-link"),
    pytest.param(TOKEN_ONE, HOUR, True, id="over-another-live-variable-token"),
    pytest.param(None, SETUP_TTL + HOUR, False, id="after-the-generated-link-expired"),
    pytest.param(TOKEN_ONE, SETUP_TTL + HOUR, False, id="after-the-variable-token-expired"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("created_with", "elapsed", "previous_live"), REARM_CASES)
async def test_a_new_variable_token_rearms_the_pending_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, created_with: Optional[str], elapsed: timedelta, previous_live: bool) -> None:
    """BOOT-010 — C2: a pending administrator, and a token in the config never stored for that account: ``REARMED``. Its live setup links are revoked, the given token stored as its one live link until ``now`` + 72 h; no ``link_token``; the account otherwise as it was. A link already expired is no longer live: it stays unusable, expired or revoked."""
    print_section(f"BOOT-010: REARMED, {elapsed} after a creation {'with a variable token' if created_with else 'with a generated link'}")
    created = await _created(engine, bootstrap, f02, token=created_with)
    previous = created_with or created.link_token
    moment = NOW + elapsed

    result = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=moment)

    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.REARMED, None), f"expected REARMED, without a link_token: {result!r}"
    rearmed = await _inspect(engine, TOKEN_TWO, moment)
    assert rearmed.status == TokenStatus.VALID and rearmed.record is not None, f"the new token must be a valid setup link: {rearmed.status}"
    assert (rearmed.record.user_id, ensure_utc(rearmed.record.expires_at)) == (created.user_id, moment + SETUP_TTL)
    assert await _status(engine, previous, moment) in ({TokenStatus.REVOKED} if previous_live else {TokenStatus.EXPIRED, TokenStatus.REVOKED}), "the previous link must be revoked when it was live, unusable either way"
    assert [row.id for row in await _live_setup_rows(engine, moment)] == [rearmed.record.id], "one live setup link: the new one"
    assert await _accounts(engine) == {ADMIN_USERNAME: (created.user_id, ADMIN_EMAIL, False, True)}
    print_success("the previous link revoked, the new token live for 72 h")


@pytest.mark.asyncio
async def test_a_token_stored_before_never_rearms(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """BOOT-011 — C2: «never stored before» covers every ``admin_setup`` row of the account, live or not: created with token one, rearmed with token two, a restart with token one again is ``PENDING`` while token two is live — token one stays revoked, nothing written —, and ``EXPIRED`` once token two expired, nothing written."""
    print_section("BOOT-011: a token already seen does not rearm")
    await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    rearmed = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=NOW + HOUR)
    assert rearmed.action == bootstrap.BootstrapAction.REARMED, f"setup: token two rearms: {rearmed!r}"
    before = await _snapshot(engine)

    back = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW + 2 * HOUR, then_commit=True)
    after_back = await _snapshot(engine)
    later = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW + HOUR + SETUP_TTL + HOUR, then_commit=True)

    assert (back.action, back.link_token) == (bootstrap.BootstrapAction.PENDING, None), f"token one was stored before and token two is live: expected PENDING, got {back!r}"
    assert after_back == before, "PENDING must write nothing: token one stays revoked"
    assert (later.action, later.link_token) == (bootstrap.BootstrapAction.EXPIRED, None), f"token one seen, token two expired: expected EXPIRED, got {later!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    print_success("PENDING, then EXPIRED; never rearmed by a token already seen")


@pytest.mark.asyncio
@pytest.mark.parametrize("ended", ["expired", "revoked"])
async def test_without_a_live_link_the_bootstrap_says_how_to_get_one(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, ended: str) -> None:
    """BOOT-012 — C2: no token in the config, and the pending administrator's link expired or revoked: ``EXPIRED``, nothing written — no new link, which only an operator hands out —, and a warning that names ``./dev.py user setup-link``."""
    created = await _created(engine, bootstrap, f02)
    moment = NOW + (SETUP_TTL + HOUR if ended == "expired" else HOUR)
    if ended == "revoked":
        await _revoke(engine, (await _setup_rows(engine, created.user_id))[0].id, NOW + timedelta(minutes=10))
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02), now=moment, then_commit=True)

    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, None), f"expected EXPIRED: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    assert [event for event in _at_level(events, "warning") if SETUP_LINK_COMMAND in repr(event)], f"a warning must name {SETUP_LINK_COMMAND}: {events}"
    assert _holding(events, created.link_token) == []


@pytest.mark.asyncio
async def test_with_the_variables_token_expired_the_warning_names_the_variable_too(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """BOOT-013 — C2: the config's token is the one the administrator was created with, and it expired: ``EXPIRED``, nothing written, and the warning names both ``./dev.py user setup-link`` and ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` — a new token there rearms —, never the token itself."""
    await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW + SETUP_TTL + HOUR, then_commit=True)

    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, None), f"expected EXPIRED: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    warnings = [event for event in _at_level(events, "warning") if SETUP_LINK_COMMAND in repr(event)]
    assert [event for event in warnings if TOKEN_VARIABLE in repr(event)], f"the warning must name {SETUP_LINK_COMMAND} and {TOKEN_VARIABLE}: {warnings}"
    assert _holding(events, CANARY) == [], "no log event may hold the token"


RENAMES = [
    pytest.param(OTHER_USERNAME, OTHER_EMAIL, id="both"),
    pytest.param(OTHER_USERNAME, ADMIN_EMAIL, id="the-username"),
    pytest.param(ADMIN_USERNAME, OTHER_EMAIL, id="the-email"),
]
#: How the restart that renames runs: (the config's token, the time since the creation, the action expected).
RENAME_SITUATIONS = [
    pytest.param(None, HOUR, "pending", id="pending"),
    pytest.param(TOKEN_TWO, HOUR, "rearmed", id="rearmed"),
    pytest.param(None, SETUP_TTL + HOUR, "expired", id="expired"),
]


# updated in A7b-2 (A-32/A-33)
@pytest.mark.asyncio
@pytest.mark.parametrize(("username", "email"), RENAMES)
@pytest.mark.parametrize(("token", "elapsed", "expected"), RENAME_SITUATIONS)
async def test_the_pending_administrator_takes_the_configs_username_and_email(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, username: str, email: str, token: Optional[str], elapsed: timedelta, expected: str) -> None:
    """BOOT-014 — C2: the config's username or email differ from the pending account's: the account — the same one — takes them, together with whatever the restart does: ``PENDING``, ``REARMED`` or ``EXPIRED``. Still inactive, still a superuser.

    Updated in A7b-2 (A-33, C3): a new address revokes the live link handed over before, so the restart that would find it
    live — ``PENDING`` — finds none: ``EXPIRED``, and that link ``revoked``, not consumed (``[pending-both]`` and
    ``[pending-the-email]``, red until A7b-2). A new username alone revokes nothing: ``[pending-the-username]`` stays
    ``PENDING``.
    """
    created = await _created(engine, bootstrap, f02)
    # updated in A7b-2 (A-32/A-33): a new address revokes the live link handed over before, so this restart finds none
    revoked_by_the_new_address = expected == "pending" and email != ADMIN_EMAIL
    if revoked_by_the_new_address:
        expected = "expired"

    result = await _run(engine, bootstrap, _config(f02, username=username, email=email, token=token), now=NOW + elapsed)

    assert result.action == expected, f"expected {expected}: {result!r}"
    assert await _accounts(engine) == {username: (created.user_id, email, False, True)}, f"the pending administrator must become {username} <{email}>"
    if revoked_by_the_new_address:  # updated in A7b-2 (A-32/A-33)
        old = await _inspect(engine, created.link_token, NOW + elapsed)
        assert (old.status, old.record is not None and old.record.consumed_at is None) == (TokenStatus.REVOKED, True), f"the link handed over to the old address must be revoked by the new one, not consumed (C3): it is {old.status}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("token", "expected"), [pytest.param(None, "pending", id="pending"), pytest.param(TOKEN_TWO, "rearmed", id="rearmed")])
async def test_a_username_taken_by_another_account_renames_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, token: Optional[str], expected: str) -> None:
    """BOOT-015 — C2: the config's new username belongs to another account (an operator created ``boss``): nothing renamed — the pending administrator keeps its name, ``boss`` is untouched —, an error is logged, and the action is otherwise what it would be: ``PENDING``, or ``REARMED`` with the new token stored. No token in the log."""
    print_section(f"BOOT-015: a username taken, {expected}")
    created = await _created(engine, bootstrap, f02)
    await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL)
    before = await _accounts(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02, username=OTHER_USERNAME, token=token), now=NOW + HOUR)

    assert result.action == expected, f"a username conflict changes nothing else: expected {expected}, got {result!r}"
    assert await _accounts(engine) == before, "nothing may be renamed"
    assert _at_level(events, "error"), f"the conflict must be logged as an error: {events}"
    assert _holding(events, created.link_token) == [] and _holding(events, CANARY) == [], "no log event may hold a token"
    if token is not None:
        rearmed = await _inspect(engine, token, NOW + HOUR)
        assert rearmed.status == TokenStatus.VALID and rearmed.record is not None and rearmed.record.user_id == created.user_id, "REARMED must still store the new token"
    print_success("nothing renamed, an error logged, the action unchanged")


PENDING_SCENES = [
    pytest.param(_no_account, id="empty-instance"),
    pytest.param(_a_pending_administrator, id="created-by-the-bootstrap"),
    pytest.param(_with_a_live_link, id="inactive-with-a-live-setup-link"),
    pytest.param(_with_an_expired_link, id="inactive-with-an-expired-setup-link"),
    pytest.param(_with_a_revoked_link, id="inactive-with-a-revoked-setup-link"),
    pytest.param(_with_a_consumed_link, id="inactive-with-a-consumed-setup-link"),
    pytest.param(_with_a_consumed_and_a_live_link, id="inactive-with-a-consumed-and-a-live-setup-link"),
    pytest.param(_active_with_a_live_link, id="active-with-a-live-setup-link"),
    pytest.param(_inactive_with_a_reset_link_only, id="inactive-with-a-reset-link-only"),
    pytest.param(_an_inactive_account, id="inactive-without-any-link"),
    pytest.param(_an_administrator_after_its_setup, id="the-administrator-after-its-setup"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("scene", PENDING_SCENES)
async def test_pending_admin_is_the_inactive_account_waiting_for_its_setup(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, scene: Scene) -> None:
    """BOOT-016 — C2: ``pending_admin`` is the inactive account that has at least one ``admin_setup`` token and none consumed — live, expired or revoked alike —; ``None`` without one: an active account, a consumed link, a reset link, no link."""
    expected = await scene(engine, bootstrap, f02)

    assert await _pending_id(engine, bootstrap) == expected


def _setup_link(token: str) -> str:
    """The full setup link of ``token``: ``LIBREFOLIO_PUBLIC_URL`` followed by the ``/setup`` page, the token in the fragment."""
    return PUBLIC_URL + token_service.token_path(ADMIN_SETUP, token)


@pytest.mark.asyncio
async def test_the_delivery_logs_the_generated_link_once_and_emails_it(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """BOOT-017 — C2, ND 1: ``CREATED`` with a generated link, ``LIBREFOLIO_PUBLIC_URL`` set and email usable: the full link is logged once, at warning — the one event that holds the token —, and emailed — log AND email —: one message to the administrator's address, for its account, exactly what ``build_admin_setup`` writes in the instance's language (``fr``) with that link, its 72 h and the host of the public address. Nothing raised, ``None`` returned.

    The precondition is verified: the French subject is not the English one, so an email always written in English
    could not pass.
    """
    print_section("BOOT-017: the link logged and emailed")
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    await _set_setting(engine, LANGUAGE_KEY, "fr")
    created = await _created(engine, bootstrap, f02)
    link = _setup_link(created.link_token)
    expected = build_admin_setup(language="fr", username=ADMIN_USERNAME, link=link, ttl=SETUP_TTL, instance=PUBLIC_HOST)
    assert expected.subject != build_admin_setup(language="en", username=ADMIN_USERNAME, link=link, ttl=SETUP_TTL, instance=PUBLIC_HOST).subject, "precondition: the French subject differs from the English one"

    with _captured(bootstrap) as events:
        returned = await bootstrap.deliver_setup_link(created, engine=engine, now=NOW)

    carrying = _holding(events, created.link_token)
    assert returned is None
    assert [event.get("log_level") for event in carrying] == ["warning"], f"the link must be logged once, at warning, and in no other event: {carrying}"
    assert link in repr(carrying[0]), f"the warning must carry the full link {link}: {carrying[0]}"
    assert [(sent.to, sent.user_id) for sent in outbox.attempts] == [(ADMIN_EMAIL, created.user_id)], f"one email to the administrator's address, for its account: {outbox.attempts}"
    content = outbox.attempts[0].content
    assert (content.kind, content.language, content.subject) == (EmailKind.ADMIN_SETUP, "fr", expected.subject)
    assert (content.text, content.html) == (expected.text, expected.html), "the email must be exactly build_admin_setup's, with the full link"
    print_success("one warning with the link, one email in fr")


@pytest.mark.asyncio
@pytest.mark.parametrize("email_usable", [True, False], ids=["email-usable", "email-off"])
async def test_without_a_public_url_the_delivery_logs_the_path_with_a_note_and_emails_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, email_usable: bool) -> None:
    """BOOT-018 — C2: without ``LIBREFOLIO_PUBLIC_URL`` the one warning carries the path (``token_path``, ``/setup#token=…``) and a note that the server address is missing — it names the variable —, no address guessed in front of the path; no email, which needs the public address, whether email is usable or not."""
    if email_usable:
        _email_ready(monkeypatch)
    created = await _created(engine, bootstrap, f02)
    path = token_service.token_path(ADMIN_SETUP, created.link_token)

    with _captured(bootstrap) as events:
        returned = await bootstrap.deliver_setup_link(created, engine=engine, now=NOW)

    carrying = _holding(events, created.link_token)
    assert returned is None
    assert [event.get("log_level") for event in carrying] == ["warning"], f"the link must be logged once, at warning: {carrying}"
    logged = repr(carrying[0])
    assert path in logged and PUBLIC_URL_VARIABLE in logged, f"the warning must carry {path} and a note naming {PUBLIC_URL_VARIABLE}: {logged}"
    assert re.search(r"https?://\S*" + re.escape(path), logged) is None, f"no address may be guessed in front of the path: {logged}"
    assert outbox.attempts == [], "no email without the public address"


DELIVERY_FAILURES = [
    pytest.param("email-off", None, id="email-off"),
    pytest.param("instance-blocked", None, id="instance-blocked"),
    pytest.param("server-refuses", EmailDeliveryError(smtp.SmtpErrorCode.RECIPIENT_REFUSED), id="the-server-refuses"),
    pytest.param("unexpected-error", RuntimeError("zq-unexpected failure"), id="an-unexpected-error"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("failure", "raised"), DELIVERY_FAILURES)
async def test_a_delivery_that_cannot_email_logs_why_and_never_raises(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, failure: str, raised: Optional[BaseException]) -> None:
    """BOOT-019 — C2: email off, the instance blocked (E's ``require_email`` refuses both: nothing is attempted), or the sending raising — the server refusing, an unexpected error —: the link is logged all the same, once, at warning; the delivery logs why no email went, in an event that holds no token, and returns ``None``: it never raises."""
    created = await _created(engine, bootstrap, f02)
    _links_ready(monkeypatch)
    if failure != "email-off":
        _email_ready(monkeypatch)
    if failure == "instance-blocked":
        monkeypatch.setenv(BLOCKED_VARIABLE, "1")
    outbox.failure = raised

    with _captured(bootstrap) as events:
        returned = await bootstrap.deliver_setup_link(created, engine=engine, now=NOW)

    carrying = _holding(events, created.link_token)
    others = [event for event in _logged(events) if event not in carrying]
    assert returned is None
    assert [event.get("log_level") for event in carrying] == ["warning"] and _setup_link(created.link_token) in repr(carrying[0]), f"the link must be logged once, at warning, before the email is tried: {carrying}"
    assert len(outbox.attempts) == (0 if raised is None else 1), f"{failure}: {outbox.attempts}"
    assert others, f"{failure}: the delivery must log why the link was not emailed: {events}"


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["created-with-the-variable-token", "pending", "rearmed", "expired", "ignored", "off"])
async def test_the_delivery_acts_only_on_a_created_generated_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, action: str) -> None:
    """BOOT-020 — C2: email and links ready. ``CREATED`` with the variable's token (``link_token`` ``None``: the hosting provider delivers it): no email, no link in any log event. Any other action — even a result carrying the live link of the administrator — sends nothing and logs no link: the delivery is for ``CREATED`` with a ``link_token`` only."""
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    if action == "created-with-the-variable-token":
        result = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
        secret = TOKEN_ONE
    else:
        created = await _created(engine, bootstrap, f02)
        result = bootstrap.BootstrapResult(action=bootstrap.BootstrapAction(action), user_id=created.user_id, username=ADMIN_USERNAME, link_token=created.link_token, expires_at=NOW + SETUP_TTL)
        secret = created.link_token

    with _captured(bootstrap) as events:
        returned = await bootstrap.deliver_setup_link(result, engine=engine, now=NOW)

    assert returned is None
    assert outbox.attempts == [], f"{action}: nothing may be emailed"
    assert _holding(events, secret) == [] and _holding(events, "#token=") == [], f"{action}: no log event may hold a link: {events}"


@pytest.mark.asyncio
async def test_a_generated_link_is_logged_once_by_its_delivery(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """BOOT-021 — C2: the run that creates a generated link logs nothing of it; its delivery logs it once; a restart, delivered too, logs it never again — ``PENDING`` hands out no link —; and no column holds it."""
    print_section("BOOT-021: a generated link, logged once")
    _links_ready(monkeypatch)

    with _captured(bootstrap) as creating:
        created = await _created(engine, bootstrap, f02)
    with _captured(bootstrap) as delivering:
        await bootstrap.deliver_setup_link(created, engine=engine, now=NOW)
    with _captured(bootstrap) as restarting:
        again = await _run(engine, bootstrap, _config(f02), now=NOW + HOUR)
        await bootstrap.deliver_setup_link(again, engine=engine, now=NOW + HOUR)

    token = created.link_token
    assert _holding(creating, token) == [], f"the run that creates the link must not log it: {creating}"
    assert [event.get("log_level") for event in _holding(delivering, token)] == ["warning"], f"the delivery logs it once, at warning: {delivering}"
    assert (again.action, again.link_token) == (bootstrap.BootstrapAction.PENDING, None)
    assert _holding(restarting, token) == [], f"a restart must not log the link again: {restarting}"
    assert await _plaintext_in_database(engine, [token]) == [], "only the link's hash may be stored"
    print_success("logged once, by the delivery; stored as its hash")


@pytest.mark.asyncio
async def test_the_variables_token_reaches_no_log_and_no_column(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, outbox: Outbox, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """BOOT-022 — C2: a whole life of the variable's tokens — ``CREATED`` with token one and its delivery, a restart, ``REARMED`` with token two, a restart with token one, ``EXPIRED`` with token two — puts neither token in any structlog event or stdlib record, nor in any column (only hashes). Email and links ready, nothing is emailed.

    Barriers first: canaries through the module's logger reach both captures, and the ``EXPIRED`` warning naming the
    variable is among the events, so the capture hears the module itself.
    """
    print_section("BOOT-022: the variable's tokens never leave")
    _email_ready(monkeypatch)
    _links_ready(monkeypatch)
    stdlib_logger = logging.getLogger(BOOTSTRAP_MODULE)
    monkeypatch.setattr(stdlib_logger, "disabled", False)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=BOOTSTRAP_MODULE)

    with _captured(bootstrap) as events:
        stdlib_logger.debug(LOG_CANARY)
        created = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW)
        await bootstrap.deliver_setup_link(created, engine=engine, now=NOW)
        restarted = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW + HOUR)
        rearmed = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=NOW + 2 * HOUR)
        back = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=NOW + 3 * HOUR)
        expired = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=NOW + 2 * HOUR + SETUP_TTL + HOUR)

    actions = [result.action for result in (created, restarted, rearmed, back, expired)]
    assert actions == ["created", "pending", "rearmed", "pending", "expired"], f"the scene is not what it claims: {actions}"
    assert [event for event in _at_level(events, "warning") if SETUP_LINK_COMMAND in repr(event) and TOKEN_VARIABLE in repr(event)], f"barrier: the EXPIRED warning is not among the captured events: {events}"
    assert any(record.name == BOOTSTRAP_MODULE and record.getMessage() == LOG_CANARY for record in caplog.records), "barrier: the stdlib records of the module's logger do not reach caplog"
    secrets = (TOKEN_ONE, TOKEN_TWO, CANARY)
    assert [event for event in events if any(secret in repr(event) for secret in secrets)] == [], "a structlog event holds a token of the variable"
    assert [record.name for record in caplog.records if any(secret in record.getMessage() or secret in repr(vars(record)) for secret in secrets)] == [], "a stdlib record holds a token of the variable"
    assert await _plaintext_in_database(engine, [TOKEN_ONE, TOKEN_TWO]) == [], "only the tokens' hashes may be stored"
    assert outbox.attempts == []
    print_success(f"{len(events)} events and {len(caplog.records)} records, no token; none in the database")


# =============================================================================
# SETUP — C3, COMPLETING THE SETUP
# =============================================================================


@pytest.mark.asyncio
async def test_completing_the_setup_activates_the_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """SETUP-001 — C3: the valid setup link of the pending administrator, with a new password: the account it returns has that password (it verifies; the random one is gone), is active and still a superuser, its session version one higher (``end_sessions``); the link is consumed and the account's other live setup link revoked. The account is pending no more. Committed: read back fresh."""
    print_section("SETUP-001: completing the setup")
    created = await _created(engine, bootstrap, f02)
    other = await _issue(engine, ADMIN_SETUP, user_id=created.user_id, now=NOW + timedelta(minutes=30))
    before = await _account(engine, created.user_id)
    moment = NOW + HOUR

    user = await _complete(engine, bootstrap, created.link_token, now=moment)

    after = await _account(engine, created.user_id)
    assert user is not None and user.id == created.user_id, f"the administrator's account must be returned: {user!r}"
    assert (after.is_active, after.is_superuser, after.username, after.email) == (True, True, ADMIN_USERNAME, ADMIN_EMAIL)
    assert verify_password(SETUP_PASSWORD, after.hashed_password), "the new password must verify"
    assert after.hashed_password != before.hashed_password, "the random secret must be gone"
    assert after.session_version == before.session_version + 1, "the setup must end every session of the account"
    assert await _status(engine, created.link_token, moment) == TokenStatus.CONSUMED
    assert await _status(engine, other.token, moment) == TokenStatus.REVOKED, "every other live setup link of the account must be revoked"
    assert await _pending_id(engine, bootstrap) is None
    print_success("active, its password set, its sessions ended, its links spent")


async def _an_unknown_link(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    return NEVER_ISSUED, ADMIN_SETUP, TokenStatus.UNKNOWN, NOW + HOUR


async def _the_link_consumed(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    await _consume(engine, created.link_token, ADMIN_SETUP, NOW + timedelta(minutes=30))
    return created.link_token, ADMIN_SETUP, TokenStatus.CONSUMED, NOW + HOUR


async def _the_link_expired(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    return created.link_token, ADMIN_SETUP, TokenStatus.EXPIRED, NOW + SETUP_TTL


async def _the_link_revoked(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    await _revoke(engine, (await _setup_rows(engine, created.user_id))[0].id, NOW + timedelta(minutes=30))
    return created.link_token, ADMIN_SETUP, TokenStatus.REVOKED, NOW + HOUR


async def _an_invitation(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    issued = await _issue(engine, INVITE, now=NOW)
    return issued.token, INVITE, TokenStatus.VALID, NOW + HOUR


async def _a_reset_link_of_the_administrator(engine: AsyncEngine, created: Any) -> tuple[str, AccountTokenPurpose, TokenStatus, datetime]:
    issued = await _issue(engine, PASSWORD_RESET, user_id=created.user_id, now=NOW + timedelta(minutes=45))
    return issued.token, PASSWORD_RESET, TokenStatus.VALID, NOW + HOUR


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "offered",
    [
        pytest.param(_an_unknown_link, id="unknown"),
        pytest.param(_the_link_consumed, id="consumed"),
        pytest.param(_the_link_expired, id="expired-at-its-expiry"),
        pytest.param(_the_link_revoked, id="revoked"),
        pytest.param(_an_invitation, id="an-invitation"),
        pytest.param(_a_reset_link_of_the_administrator, id="a-password-reset-link"),
    ],
)
async def test_any_other_token_completes_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, offered: Callable[[AsyncEngine, Any], Awaitable[tuple[str, AccountTokenPurpose, TokenStatus, datetime]]]) -> None:
    """SETUP-002 — C3: a token never issued, the setup link consumed, expired — at its expiry exactly —, or revoked, a live invitation, a live reset link of the administrator itself: ``None``, and nothing changed — not the account, not a token, not even after the caller commits.

    Barrier first: each token is in the state its name says, for its own purpose.
    """
    created = await _created(engine, bootstrap, f02)
    token, purpose, status, moment = await offered(engine, created)
    assert await _status(engine, token, moment, purpose) == status, f"barrier: the offered token must be {status} as a {purpose.value}"
    before = await _snapshot(engine)

    user = await _complete(engine, bootstrap, token, now=moment, then_commit=True)

    assert user is None, f"a {status} {purpose.value} token must complete nothing: {user!r}"
    assert await _snapshot(engine) == before, "a refused setup must change nothing"


@pytest.mark.asyncio
@pytest.mark.parametrize("set_up", ["an-operators-active-administrator", "the-f02-administrator-after-its-setup"])
async def test_the_setup_link_of_an_account_already_active_is_revoked(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, set_up: str) -> None:
    """SETUP-003 — C3, ND 6: a valid setup link of an account already active — an operator's administrator, or the F02 administrator after its setup —: ``None``, the account unchanged, and that link revoked, committed."""
    print_section(f"SETUP-003: the setup link of {set_up}")
    if set_up == "an-operators-active-administrator":
        user_id = await _add_user(engine, OTHER_USERNAME, admin=True)
    else:
        created = await _created(engine, bootstrap, f02)
        user_id = created.user_id
        assert await _complete(engine, bootstrap, created.link_token, now=NOW + timedelta(minutes=30)) is not None, "setup: the administrator completes its setup"
    stray = await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW + timedelta(minutes=40))
    moment = NOW + HOUR
    assert await _status(engine, stray.token, moment) == TokenStatus.VALID, "barrier: the stray link is valid"
    accounts_before = (await _snapshot(engine))["users"]

    user = await _complete(engine, bootstrap, stray.token, now=moment)

    assert user is None, f"an account already active is set up already: {user!r}"
    assert await _status(engine, stray.token, moment) == TokenStatus.REVOKED, "its setup link must be revoked"
    assert (await _snapshot(engine))["users"] == accounts_before, "the account must be unchanged"
    print_success("None; the link revoked; the account untouched")


@pytest.mark.asyncio
async def test_a_setup_link_completes_once(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """SETUP-004 — C3: the same link a second time, with another password: ``None``, nothing changed — the first password stays."""
    created = await _created(engine, bootstrap, f02)
    assert await _complete(engine, bootstrap, created.link_token, now=NOW + HOUR) is not None, "setup: the first use completes the setup"
    before = await _snapshot(engine)

    again = await _complete(engine, bootstrap, created.link_token, now=NOW + 2 * HOUR, password="Another-Pass-2026!", then_commit=True)

    assert again is None
    assert await _snapshot(engine) == before


# =============================================================================
# USAGE — C4, THE PENDING ADMINISTRATOR HOLDS ITS PLACE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("elapsed", [HOUR, SETUP_TTL + HOUR], ids=["its-link-live", "its-link-expired"])
async def test_the_pending_administrator_holds_a_place(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, elapsed: timedelta) -> None:
    """USAGE-001 — C4: after ``CREATED`` on an otherwise empty instance, ``user_usage`` counts one place — the pending administrator, an inactive account with a setup link never consumed —, its link live or expired alike; no limit without ``LIBREFOLIO_MAX_USERS``."""
    await _created(engine, bootstrap, f02)

    assert await _usage(engine, NOW + elapsed) == (1, None)


@pytest.mark.asyncio
async def test_the_administrator_after_its_setup_is_counted_once(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """USAGE-002 — C4: after ``complete_admin_setup``, still one place: an active account now, not counted twice."""
    created = await _created(engine, bootstrap, f02)
    assert await _complete(engine, bootstrap, created.link_token, now=NOW + HOUR) is not None, "setup: the setup is completed"

    assert await _usage(engine, NOW + 2 * HOUR) == (1, None)


@pytest.mark.asyncio
async def test_only_the_pending_administrator_among_inactive_accounts_is_counted(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """USAGE-003 — C4: the pending administrator, an active account and a live invitation are three places; a deactivated account without a setup link — with no link, or with a reset link — holds none.

    Barrier first: the invitation and the reset link are live.
    """
    print_section("USAGE-003: what user_usage counts")
    await _created(engine, bootstrap, f02)
    await _add_user(engine, "alice")
    await _add_user(engine, "carol", active=False)
    dave = await _add_user(engine, "dave", active=False)
    reset = await _issue(engine, PASSWORD_RESET, user_id=dave, now=NOW + timedelta(minutes=45))
    invitation = await _issue(engine, INVITE, now=NOW)
    moment = NOW + HOUR
    assert (await _status(engine, invitation.token, moment, INVITE), await _status(engine, reset.token, moment, PASSWORD_RESET)) == (TokenStatus.VALID, TokenStatus.VALID), "barrier: the scene is not what it claims"

    assert await _usage(engine, moment) == (3, None), "the pending administrator, alice and the invitation: three places"
    print_success("3 places: the pending administrator, an active account, an invitation")


# =============================================================================
# CLI — C5, ./dev.py user setup-link
# =============================================================================


def _link_parsers(cli: ModuleType) -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    """The parser of ``user_cli.py`` with the link commands, and the one of ``dev.py`` with the ``user`` group."""
    parser = argparse.ArgumentParser(prog="user_cli.py")
    cli._add_link_commands(parser.add_subparsers(dest="command"))
    devpy = argparse.ArgumentParser(prog="dev.py")
    cli.register_subparser(devpy.add_subparsers(dest="group"))
    return parser, devpy


def test_setup_link_is_a_user_command_without_arguments(cli: ModuleType) -> None:
    """CLI-001 — C5: ``_add_link_commands`` registers ``setup-link``, which takes no argument and no option, in ``user_cli.py`` and under ``./dev.py user`` — the command the warning of an expired link names."""
    print_section("CLI-001: setup-link")
    parser, devpy = _link_parsers(cli)

    parsed = parser.parse_args(["setup-link"])
    through_devpy = devpy.parse_args(["user", "setup-link"])

    assert vars(parsed) == {"command": "setup-link"}, f"setup-link takes no argument nor option: {vars(parsed)}"
    assert (through_devpy.group, through_devpy.command) == ("user", "setup-link")
    with pytest.raises(SystemExit):
        parser.parse_args(["setup-link", ADMIN_USERNAME])
    print_success("user_cli.py setup-link and ./dev.py user setup-link, without arguments")


@pytest.mark.parametrize("answer", [True, False], ids=["it-printed-a-link", "it-refused"])
def test_the_dispatch_runs_cmd_setup_link_and_exits_by_its_answer(cli: ModuleType, monkeypatch: pytest.MonkeyPatch, answer: bool) -> None:
    """CLI-002 — C5: ``cmd_setup_link`` is a coroutine function without parameters; ``_dispatch_user_command`` runs it for ``setup-link`` and answers what it answers, and ``./dev.py user setup-link`` exits 0 on ``True``, 1 on ``False``."""
    assert inspect.iscoroutinefunction(getattr(cli, "cmd_setup_link", None)), "red until lot A7a: scripts/user_cli.py has no async cmd_setup_link"
    assert list(inspect.signature(cli.cmd_setup_link).parameters) == [], "cmd_setup_link takes no parameter"
    calls: list[str] = []

    async def recorded_setup_link() -> bool:
        calls.append("setup-link")
        return answer

    monkeypatch.setattr(cli, "cmd_setup_link", recorded_setup_link)
    parser, devpy = _link_parsers(cli)

    dispatched = cli._dispatch_user_command(parser.parse_args(["setup-link"]))
    exit_code = cli._dispatch_user_from_devpy(devpy.parse_args(["user", "setup-link"]))

    assert (dispatched, exit_code, calls) == (answer, 0 if answer else 1, ["setup-link", "setup-link"])


@pytest.mark.asyncio
@pytest.mark.parametrize("previous", ["live", "expired"])
@pytest.mark.parametrize("public", [True, False], ids=["public-url", "no-public-url"])
async def test_cmd_setup_link_gives_the_pending_administrator_a_new_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], previous: str, public: bool) -> None:
    """CLI-003 — C5: a pending administrator, its link live or expired: ``cmd_setup_link`` revokes its live links, issues a generated one for 72 h, commits, prints ``✅`` and the link — the full address with ``LIBREFOLIO_PUBLIC_URL``, otherwise the path and a note naming the variable, as ``reset-link`` does — and answers ``True``. The printed link is valid and the account's one live link; the one before is revoked when it was live.

    It reads the clock: the scene is dated from it, an hour old or past its 72 h. ``get_async_engine`` of ``user_cli`` is
    the private engine.
    """
    print_section(f"CLI-003: setup-link, the previous link {previous}, {'with' if public else 'without'} the public URL")
    moment = utcnow()
    created = await _created(engine, bootstrap, f02, now=moment - (HOUR if previous == "live" else SETUP_TTL + 8 * HOUR))
    if public:
        _links_ready(monkeypatch)
    monkeypatch.setattr(cli, "get_async_engine", lambda: engine)
    capsys.readouterr()

    ok = await cli.cmd_setup_link()

    out = capsys.readouterr().out
    after = utcnow()
    printed = re.search(r"(\S*)/setup#(\S+)", out)
    assert ok is True, f"cmd_setup_link must answer True: {out!r}"
    assert any(line.startswith("✅") for line in out.splitlines()), f"a line must start with ✅: {out!r}"
    assert printed is not None, f"no setup link printed: {out!r}"
    assert printed.group(1) == (PUBLIC_URL if public else ""), f"expected {'the full address' if public else 'the bare path'}: {out!r}"
    assert public or PUBLIC_URL_VARIABLE in out, f"without the public address a note must name {PUBLIC_URL_VARIABLE}: {out!r}"
    inspection = await _inspect(engine, parse_qs(printed.group(2))["token"][0], after)
    assert inspection.status == TokenStatus.VALID and inspection.record is not None, f"the printed link must be valid: {inspection.status}"
    assert (inspection.record.user_id, ensure_utc(inspection.record.expires_at) - ensure_utc(inspection.record.created_at)) == (created.user_id, SETUP_TTL)
    assert await _status(engine, created.link_token, after) in ({TokenStatus.REVOKED} if previous == "live" else {TokenStatus.EXPIRED, TokenStatus.REVOKED})
    assert [row.id for row in await _live_setup_rows(engine, after)] == [inspection.record.id], "the printed link must be the one live setup link"
    assert await _accounts(engine) == {ADMIN_USERNAME: (created.user_id, ADMIN_EMAIL, False, True)}, "the account itself is unchanged"
    print_success("a new link printed, valid 72 h, the only live one")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scene",
    [
        pytest.param(_no_account, id="empty-instance"),
        pytest.param(_an_administrator_after_its_setup, id="the-administrator-after-its-setup"),
        pytest.param(_an_inactive_account, id="an-inactive-account-without-a-setup-link"),
    ],
)
async def test_cmd_setup_link_without_a_pending_administrator_refuses_and_writes_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], scene: Scene) -> None:
    """CLI-004 — C5: no pending administrator: a line starting with ``❌``, no link, ``False``, nothing written."""
    await scene(engine, bootstrap, f02)
    before = await _snapshot(engine)
    monkeypatch.setattr(cli, "get_async_engine", lambda: engine)
    capsys.readouterr()

    ok = await cli.cmd_setup_link()

    out = capsys.readouterr().out
    assert ok is False, f"cmd_setup_link must answer False: {out!r}"
    assert any(line.startswith("❌") for line in out.splitlines()), f"a line must start with ❌: {out!r}"
    assert "#token=" not in out, f"no link may be printed: {out!r}"
    assert await _snapshot(engine) == before, "a refusal must write nothing"


@pytest.mark.asyncio
async def test_issue_setup_link_replaces_the_pending_administrators_live_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """CLI-005 — C5: ``issue_setup_link(session, now=...)``, the service behind the command: for the pending administrator, an ``IssuedToken`` of a generated ``admin_setup`` link until ``now`` + 72 h, valid, its one live link — the live one before revoked —; neither link in any log event."""
    created = await _created(engine, bootstrap, f02)
    moment = NOW + HOUR

    with _captured(bootstrap) as events:
        issued = await _issue_setup_link(engine, bootstrap, now=moment)

    assert isinstance(issued, IssuedToken), f"expected an IssuedToken: {issued!r}"
    inspection = await _inspect(engine, issued.token, moment)
    assert inspection.status == TokenStatus.VALID and inspection.record is not None, f"the new link must be valid: {inspection.status}"
    assert (inspection.record.user_id, ensure_utc(inspection.record.expires_at)) == (created.user_id, moment + SETUP_TTL)
    assert await _status(engine, created.link_token, moment) == TokenStatus.REVOKED
    assert [row.id for row in await _live_setup_rows(engine, moment)] == [issued.record.id]
    assert _holding(events, issued.token) == [] and _holding(events, created.link_token) == [], "no log event may hold a link"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scene",
    [
        pytest.param(_no_account, id="empty-instance"),
        pytest.param(_an_administrator_after_its_setup, id="the-administrator-after-its-setup"),
        pytest.param(_an_active_account, id="an-active-account"),
    ],
)
async def test_issue_setup_link_without_a_pending_administrator_is_none(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, scene: Scene) -> None:
    """CLI-006 — C5: no pending administrator: ``issue_setup_link`` answers ``None`` and writes nothing, even when its caller commits."""
    await scene(engine, bootstrap, f02)
    before = await _snapshot(engine)

    assert await _issue_setup_link(engine, bootstrap, now=NOW + HOUR) is None
    assert await _snapshot(engine) == before


# =============================================================================
# STEP — THE STARTUP
# =============================================================================


def test_the_admin_bootstrap_step_runs_right_after_the_global_settings() -> None:
    """STEP-001 — startup: ``STARTUP_STEPS`` holds ``admin-bootstrap`` once, right after ``global-settings`` — the bootstrap writes ``registration_mode`` over the seeded row, and nothing serves before it."""
    app_lifespan = importlib.import_module(APP_LIFESPAN_MODULE)
    names = [step.name for step in app_lifespan.STARTUP_STEPS]

    assert names.count("admin-bootstrap") == 1, f"red until lot A7a: one admin-bootstrap step expected in {names}"
    assert names.index("admin-bootstrap") == names.index("global-settings") + 1, f"admin-bootstrap must run right after global-settings: {names}"


@pytest.mark.asyncio
async def test_startup_creates_the_administrator_and_leaves_the_delivery_to_the_background(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """STEP-002 — startup, ND 7: ``LIBREFOLIO_ADMIN_EMAIL`` set on an empty instance: ``startup_admin_bootstrap(engine)`` answers ``CREATED`` — the account in the database, its link valid — while the delivery it scheduled is still held: a task of its own, given that result and that engine. A slow SMTP server never delays the start.

    The delivery is replaced by one that waits for the test; a startup that awaited it would never return, and the bound
    on it is a failure's, never a wait.
    """
    print_section("STEP-002: the startup step")
    monkeypatch.setenv(EMAIL_VARIABLE, ADMIN_EMAIL)
    calls: list[tuple[Any, dict[str, Any]]] = []
    tasks: list[Optional[asyncio.Task[Any]]] = []
    release = asyncio.Event()

    async def held_delivery(result: Any, **arguments: Any) -> None:
        calls.append((result, arguments))
        tasks.append(asyncio.current_task())
        await release.wait()

    monkeypatch.setattr(bootstrap, "deliver_setup_link", held_delivery)
    try:
        try:
            result = await asyncio.wait_for(bootstrap.startup_admin_bootstrap(engine), timeout=STARTUP_BOUND_SECONDS)
        except TimeoutError:
            pytest.fail("startup_admin_bootstrap did not return while the delivery was held: the delivery must be scheduled in the background (ND 7)")
        started = await _yield_until(lambda: bool(calls))

        assert result.action == bootstrap.BootstrapAction.CREATED, f"expected CREATED: {result!r}"
        assert await _accounts(engine) == {ADMIN_USERNAME: (result.user_id, ADMIN_EMAIL, False, True)}
        assert await _status(engine, result.link_token, utcnow()) == TokenStatus.VALID
        assert started and len(calls) == 1, f"the startup must schedule one delivery: {calls}"
        delivered, arguments = calls[0]
        assert (delivered, arguments.get("engine")) == (result, engine), f"the delivery must get the result and the engine: {calls[0]}"
        assert tasks[0] is not asyncio.current_task() and not tasks[0].done(), "the delivery must run in a task of its own, still held when the startup returned"
    finally:
        release.set()
        await asyncio.gather(*(task for task in tasks if task is not None and task is not asyncio.current_task()), return_exceptions=True)
    print_success("CREATED; the delivery left to the background")


@pytest.mark.asyncio
async def test_startup_with_f02_off_writes_nothing(engine: AsyncEngine, bootstrap: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """STEP-003 — startup: no F02 variable: ``startup_admin_bootstrap(engine)`` answers ``OFF`` and writes nothing."""
    scheduled: list[Any] = []

    async def recorded_delivery(result: Any, **arguments: Any) -> None:
        scheduled.append(result)

    monkeypatch.setattr(bootstrap, "deliver_setup_link", recorded_delivery)
    before = await _snapshot(engine)

    result = await asyncio.wait_for(bootstrap.startup_admin_bootstrap(engine), timeout=STARTUP_BOUND_SECONDS)
    await _yield_until(lambda: bool(scheduled))  # a delivery scheduled anyway ends before the test does

    assert result.action == bootstrap.BootstrapAction.OFF, f"expected OFF: {result!r}"
    assert await _snapshot(engine) == before


# =============================================================================
# A32 — LOT A7b-2: THE SETUP ENDS, WHATEVER THE WAY (N60)
# =============================================================================
# A-32: the waiting administrator activated another way — ``set_user_active(..., True)``, the CLI's ``user activate``;
# ``update_user_status(..., is_active=True)`` — or given a password another way — ``reset_password``, the CLI's ``user
# reset-password``; a reset link, ``complete_password_reset`` — keeps its setup link today. Deactivated again within the
# 72 hours, it waits again by ``pending_admin_filter`` (inactive, a setup link, none consumed), and whoever holds the old
# link, even read in the log, sets their own password and activates it. The contract (D1, approved as N60): in the
# transaction of the change, ``user_service`` retires the account's setup links — ``token_service.retire_tokens``:
# revoked and consumed, without a consumer —, so the account waits for nothing any more; and ``complete_admin_setup``,
# refusing the link of an account already active, retires every setup link of that account instead of revoking the one
# shown.
#
# The waiting administrator is made by the real bootstrap on the empty private instance with TOKEN_ONE in the config:
# the test holds the link. root, an active administrator written as a row afterwards, lets it be deactivated once
# active. The ``user_service`` functions read the clock, so these scenes are dated from it, as CLI-003's: created an hour
# ago, its link live for 71 hours more — or 72 hours and a minute ago, its link expired a minute before, as UADM-065
# dates it on the API side —; every call that takes a ``now`` gets one, AFTERWARDS later.

#: What the operator gives the waiting administrator another way: the CLI's ``user reset-password``, a reset link.
OPERATOR_PASSWORD = "Operator-Pass-2026!"
#: What whoever holds the old setup link tries to set.
INTRUDER_PASSWORD = "Intruder-Pass-2026!"
ROOT_USERNAME = "root"
#: How long after the scene is read the calls that take a ``now`` are dated.
AFTERWARDS = timedelta(minutes=5)
#: How old an expired setup link is when the scene is read: issued 72 hours and a minute before, as UADM-065 does.
EXPIRED_AGE = SETUP_TTL + timedelta(minutes=1)
#: A setup link's row once retired: (revoked, consumed, consumed_by_user_id).
RETIRED = (True, True, None)
#: The waiting administrator's link when the change comes: live, or already expired.
LINK_STATES = [pytest.param(False, id="its-link-live"), pytest.param(True, id="its-link-expired")]

#: A change made to an account: (the engine, the account's id, the moment its scene is read at).
Change = Callable[[AsyncEngine, int, datetime], Awaitable[None]]


async def _waiting(engine: AsyncEngine, bootstrap: ModuleType, user_id: int) -> tuple[bool, bool, Optional[int]]:
    """Whether the account waits for its setup, as each reader of ``pending_admin_filter`` says: ``(is_pending_admin, in pending_admin_ids, the id pending_admin answers)``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        assert user is not None, f"account {user_id} is not in the database"
        pending = await registration_service.is_pending_admin(session, user)
        listed = user_id in await registration_service.pending_admin_ids(session)
        first = await bootstrap.pending_admin(session)
    return pending, listed, None if first is None else first.id


async def _waiting_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, moment: datetime, *, expired: bool = False) -> int:
    """The F02 administrator created by the bootstrap with TOKEN_ONE an hour before ``moment`` — EXPIRED_AGE before with ``expired``: 72 hours and a minute —, and root beside it: the id of the waiting account.

    Barrier: the account waits for its setup, and its link is valid at ``moment`` — or expired.
    """
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE, now=moment - (EXPIRED_AGE if expired else HOUR))
    await _add_user(engine, ROOT_USERNAME, admin=True)
    expected = TokenStatus.EXPIRED if expired else TokenStatus.VALID
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "barrier: the F02 administrator waits for its setup"
    assert await _status(engine, TOKEN_ONE, moment) == expected, f"barrier: its setup link must be {expected}"
    return created.user_id


def _link_states(rows: list[AccountToken]) -> list[tuple[bool, bool, Optional[int]]]:
    """``(revoked, consumed, consumed_by_user_id)`` of each setup link's row: a retired one is ``RETIRED``."""
    return [(row.revoked_at is not None, row.consumed_at is not None, row.consumed_by_user_id) for row in rows]


def _named(change: Callable[..., Any]) -> str:
    """A change by its function's name, in words: what a section title and a failure message say."""
    return change.__name__.strip("_").replace("_", " ")


async def _assert_waits_for_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, user_id: int, moment: datetime, after: str) -> None:
    """C2, effect 3, ``after`` a change: the account waits for its setup no more — not ``is_pending_admin``, not in ``pending_admin_ids``, ``pending_admin`` ``None`` —; ``issue_setup_link`` is ``None``; a restart with the same config, or with a token never seen that would re-arm it, is ``IGNORED`` — the instance has accounts. None of them writes anything, even when the caller commits."""
    waiting = await _waiting(engine, bootstrap, user_id)
    assert waiting == (False, False, None), f"red until A7b-2: after {after} the account must wait for its setup no more: (is_pending_admin, in pending_admin_ids, pending_admin) {waiting}"
    before = await _snapshot(engine)
    issued = await _issue_setup_link(engine, bootstrap, now=moment)
    same = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=moment, then_commit=True)
    rotated = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=moment, then_commit=True)
    assert issued is None, f"after {after}, ./dev.py user setup-link must find nobody to give a link to: {issued!r}"
    assert (same.action, rotated.action) == (bootstrap.BootstrapAction.IGNORED, bootstrap.BootstrapAction.IGNORED), f"after {after}, a restart must ignore the variables, with the same token or a new one: {same!r}, {rotated!r}"
    assert await _snapshot(engine) == before, f"after {after}, issue_setup_link and the restarts must write nothing"


async def _activate_by_set_user_active(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """The CLI's ``user activate``: ``set_user_active(session, username, True)``."""
    username = (await _account(engine, user_id)).username
    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_active(session, username, True)
    assert outcome == (True, None), f"barrier: user activate must succeed: {outcome}"


async def _activate_by_update_user_status(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """The service of the Users tab's PATCH: ``update_user_status(session, user, is_active=True)``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        refusal = await user_service.update_user_status(session, user, is_active=True)
    assert refusal is None, f"barrier: the activation must succeed: {refusal}"


async def _deactivate_by_set_user_active(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """The CLI's ``user deactivate``: ``set_user_active(session, username, False)``."""
    username = (await _account(engine, user_id)).username
    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_active(session, username, False)
    assert outcome == (True, None), f"barrier: user deactivate must succeed: {outcome}"


async def _deactivate_by_update_user_status(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """The service of the Users tab's PATCH: ``update_user_status(session, user, is_active=False)``."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        refusal = await user_service.update_user_status(session, user, is_active=False)
    assert refusal is None, f"barrier: the deactivation must succeed: {refusal}"


async def _password_by_user_reset_password(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """The CLI's ``user reset-password``: ``reset_password(session, username, OPERATOR_PASSWORD)``."""
    username = (await _account(engine, user_id)).username
    async with AsyncSession(engine) as session:
        outcome = await user_service.reset_password(session, username, OPERATOR_PASSWORD)
    assert outcome == (True, None), f"barrier: user reset-password must succeed: {outcome}"


async def _password_by_a_reset_link(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """A reset link issued for the account (``create_password_reset``, as an administrator issues one), then spent with OPERATOR_PASSWORD (``complete_password_reset``)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        issued = await user_service.create_password_reset(session, user, now=moment)
        await session.commit()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        spent = await user_service.complete_password_reset(session, issued.token, OPERATOR_PASSWORD, now=moment + timedelta(minutes=1))
    assert spent is not None and spent.id == user_id, f"barrier: the reset link must set the password: {spent!r}"


async def _nothing_done(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """Nothing: the waiting administrator as the bootstrap left it."""


async def _a_reset_link_never_spent(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """A reset link issued for the account (``create_password_reset``) and never spent: no password is set."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        await user_service.create_password_reset(session, user, now=moment)
        await session.commit()


#: The ways an account becomes active other than its setup link (C2).
ACTIVATIONS_ANOTHER_WAY = [
    pytest.param(_activate_by_set_user_active, id="activated-by-user-activate"),
    pytest.param(_activate_by_update_user_status, id="activated-by-update-user-status"),
]
#: The ways an account is deactivated.
DEACTIVATIONS = [
    pytest.param(_deactivate_by_set_user_active, id="deactivated-by-user-deactivate"),
    pytest.param(_deactivate_by_update_user_status, id="deactivated-by-update-user-status"),
]
#: The ways an account is given a password other than its setup link (C2).
PASSWORDS_ANOTHER_WAY = [
    pytest.param(_password_by_user_reset_password, id="password-by-user-reset-password"),
    pytest.param(_password_by_a_reset_link, id="password-by-a-reset-link"),
]
#: What neither activates the waiting administrator nor gives it a password, and touches none of its setup links (C2's
#: guards): nothing; a reset link never spent. Updated in A-42/A-43: a deactivation of the account already inactive — by
#: the service of the Users tab or by the CLI — now revokes its live setup link, the account still waiting for a new one
#: (A43-001); a demotion of the waiting administrator is now refused, at the CLI (A43-004) and in the Users tab (UADM-072),
#: wherever the refusal lives. Neither leaves «its link valid» any more: both left this guard.
NO_END_OF_THE_SETUP = [
    pytest.param(_nothing_done, id="nothing-done"),
    pytest.param(_a_reset_link_never_spent, id="a-reset-link-never-spent"),
]


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("activate", ACTIVATIONS_ANOTHER_WAY)
async def test_activating_the_waiting_administrator_another_way_retires_its_setup_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, activate: Change) -> None:
    """A32-001 — NEW, red until A7b-2 (the link stays valid): the waiting administrator activated another way — ``set_user_active(..., True)``, the CLI's ``user activate``, or ``update_user_status(..., is_active=True)`` — has its setup link retired in the commit of the activation: revoked and consumed, without a consumer; ``inspect_token`` says ``revoked``. Offered afterwards, the link sets nothing: ``complete_admin_setup`` is ``None`` and nothing changes — the password hash, ``is_active`` and the session version as the activation left them, every token as it was.

    The link is inspected before it is offered: today ``complete_admin_setup`` refuses the link of an active account
    anyway, and revokes it, which would make «revoked» green for the wrong reason.
    """
    print_section(f"A32-001: {_named(activate)}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment)
    hashed = (await _account(engine, user_id)).hashed_password

    await activate(engine, user_id, moment)

    later = moment + AFTERWARDS
    activated = await _account(engine, user_id)
    status = await _status(engine, TOKEN_ONE, later)
    assert (activated.is_active, activated.hashed_password) == (True, hashed), "barrier: the account is active, its password untouched"
    assert status == TokenStatus.REVOKED, f"red until A7b-2: activating the waiting administrator another way must retire its setup link: it is still {status}"
    assert _link_states(await _setup_rows(engine, user_id)) == [RETIRED], "its setup link must be retired: revoked and consumed, without a consumer"
    before = await _snapshot(engine)
    assert await _complete(engine, bootstrap, TOKEN_ONE, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "the old link must set nothing"
    assert await _snapshot(engine) == before, "the old link must change nothing: the password hash, is_active, the session version, every token"
    print_success("active; its setup link retired, and opening nothing")


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("expired", LINK_STATES)
@pytest.mark.parametrize("deactivate", DEACTIVATIONS)
@pytest.mark.parametrize("activate", ACTIVATIONS_ANOTHER_WAY)
async def test_deactivated_after_another_activation_the_administrator_waits_for_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, activate: Change, deactivate: Change, expired: bool) -> None:
    """A32-002 — NEW, red until A7b-2 — A-32 itself (today, deactivated again, the account waits again, and its live link sets the password of whoever holds it and activates it): the waiting administrator activated another way, then deactivated within its link's 72 hours — ``set_user_active(..., False)`` or ``update_user_status(..., is_active=False)``. Its old link, even read in the log, opens nothing: ``complete_admin_setup`` with an intruder's password is ``None`` and nothing changes — the account inactive, its password hash and session version as the deactivation left them, every token as it was. And the account waits for nothing (C2, effect 3). Its link live, or already expired when the account was activated: an expired link is retired too, or the deactivated account would wait again, for a new link of ``./dev.py user setup-link`` or a re-arming token."""
    print_section(f"A32-002: {_named(activate)}, then {_named(deactivate)}, its link {'expired' if expired else 'live'}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment, expired=expired)
    await activate(engine, user_id, moment)
    await deactivate(engine, user_id, moment)
    later = moment + AFTERWARDS
    assert (await _account(engine, user_id)).is_active is False, "barrier: the account is inactive again"
    before = await _snapshot(engine)

    taken = await _complete(engine, bootstrap, TOKEN_ONE, now=later, password=INTRUDER_PASSWORD, then_commit=True)

    assert taken is None, f"red until A7b-2 (A-32): activated another way then deactivated, the administrator's old setup link must open nothing: it set the intruder's password and activated account {taken.id if taken else None}"
    assert await _snapshot(engine) == before, "the old link must change nothing: the account inactive, its password hash and session version as the deactivation left them, every token as it was"
    await _assert_waits_for_nothing(engine, bootstrap, f02, user_id, later, f"{_named(activate)}, then {_named(deactivate)}")
    print_success("its old link opens nothing, and it waits for nothing")


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("expired", LINK_STATES)
@pytest.mark.parametrize("set_password", PASSWORDS_ANOTHER_WAY)
async def test_a_password_set_another_way_retires_the_setup_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, set_password: Change, expired: bool) -> None:
    """A32-003 — NEW, red until A7b-2 (today the link stays valid: spent, it replaces the operator's password and activates the account; expired, the account still waits for a new one): the waiting administrator, still inactive, given a password another way — the CLI's ``user reset-password`` (``reset_password``), or a reset link issued for it (``create_password_reset``, then ``complete_password_reset``) — has its setup link retired in the commit of the password: ``inspect_token`` says ``revoked``, its row revoked and consumed, without a consumer. The old link opens nothing — ``complete_admin_setup`` is ``None`` and nothing changes: the operator's password stays, the account stays inactive —, and the account waits for nothing (C2, effect 3). Its link live or expired alike."""
    print_section(f"A32-003: {_named(set_password)}, its link {'expired' if expired else 'live'}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment, expired=expired)

    await set_password(engine, user_id, moment)

    later = moment + AFTERWARDS
    account = await _account(engine, user_id)
    status = await _status(engine, TOKEN_ONE, later)
    assert (account.is_active, verify_password(OPERATOR_PASSWORD, account.hashed_password)) == (False, True), "barrier: the operator's password is set, the account still inactive"
    assert status == TokenStatus.REVOKED, f"red until A7b-2: a password set by {_named(set_password)} must retire the waiting administrator's setup link: it is still {status}"
    assert _link_states(await _setup_rows(engine, user_id)) == [RETIRED], "its setup link must be retired: revoked and consumed, without a consumer"
    before = await _snapshot(engine)
    assert await _complete(engine, bootstrap, TOKEN_ONE, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "the old link must set nothing"
    assert await _snapshot(engine) == before, "the old link must change nothing: the operator's password, the account inactive, every token"
    await _assert_waits_for_nothing(engine, bootstrap, f02, user_id, later, f"a password set by {_named(set_password)}")
    print_success("the operator's password kept; the old link retired; it waits for nothing")


# guard — updated in A-42/A-43: four variants left it by construction (NO_END_OF_THE_SETUP)
@pytest.mark.asyncio
@pytest.mark.parametrize("change", NO_END_OF_THE_SETUP)
async def test_what_neither_activates_nor_sets_a_password_leaves_the_administrator_waiting(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, change: Change) -> None:
    """A32-004 — GUARD, green today and after: what neither activates the waiting administrator nor gives it a password, nor touches its setup links, ends nothing — nothing done; a reset link issued and never spent —: the account still waits — ``is_pending_admin``, in ``pending_admin_ids``, the one ``pending_admin`` answers —, its setup link valid; and the link still completes the setup: the account active, with the password chosen through the link, its role as the change left it.

    Updated in A-42/A-43, by construction: the deactivation of the account already inactive (``update_user_status(...,
    is_active=False)``, ``set_user_active(..., False)``) now revokes its live setup link, the account still waiting for a
    new one — A43-001 —; the demotion (``update_user_status(..., is_superuser=False)``, ``set_user_admin(..., False)``)
    is now refused at the CLI and in the Users tab — A43-004, UADM-072 —, and whether these services refuse it too is the
    implementation's choice: no variant pins it here.
    """
    print_section(f"A32-004: {_named(change)}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment)

    await change(engine, user_id, moment)

    later = moment + AFTERWARDS
    superuser = (await _account(engine, user_id)).is_superuser
    assert await _waiting(engine, bootstrap, user_id) == (True, True, user_id), f"after {_named(change)} the account must still wait for its setup"
    assert await _status(engine, TOKEN_ONE, later) == TokenStatus.VALID, f"after {_named(change)} its setup link must stay valid"
    user = await _complete(engine, bootstrap, TOKEN_ONE, now=later)
    after = await _account(engine, user_id)
    assert user is not None and user.id == user_id, f"after {_named(change)} the link must still complete the setup: {user!r}"
    assert (after.is_active, after.is_superuser, verify_password(SETUP_PASSWORD, after.hashed_password)) == (True, superuser, True), "the account active, with the password chosen through the link, its role as the change left it"
    print_success("still waiting; its link completes the setup")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize("activate", ACTIVATIONS_ANOTHER_WAY)
async def test_activating_an_ordinary_inactive_account_still_works(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, activate: Change) -> None:
    """A32-005 — GUARD, green today and after: beside the waiting administrator, carol — an inactive member without any setup link, holding a live reset link — is activated by the same ways: active, still a member. No account token moves — carol's reset link stays valid, and the retirement finds nothing of hers —, and the F02 administrator still waits, its link valid."""
    print_section(f"A32-005: an ordinary account, {_named(activate)}")
    moment = utcnow()
    admin_id = await _waiting_administrator(engine, bootstrap, f02, moment)
    carol = await _add_user(engine, "carol", active=False)
    reset = await _issue(engine, PASSWORD_RESET, user_id=carol, now=moment)
    tokens_before = (await _snapshot(engine))["tokens"]

    await activate(engine, carol, moment)

    later = moment + AFTERWARDS
    after = await _account(engine, carol)
    assert (after.is_active, after.is_superuser) == (True, False), "carol must be active, and still a member"
    assert (await _snapshot(engine))["tokens"] == tokens_before, "no account token may move: carol has no setup link, and the F02 administrator's is not hers"
    assert await _status(engine, reset.token, later, PASSWORD_RESET) == TokenStatus.VALID, "carol's reset link must stay valid"
    assert await _waiting(engine, bootstrap, admin_id) == (True, True, admin_id), "the F02 administrator must still wait"
    assert await _status(engine, TOKEN_ONE, later) == TokenStatus.VALID, "its setup link must stay valid"
    print_success("carol active; nothing else moved")


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("deactivate", DEACTIVATIONS)
async def test_the_refused_link_of_an_active_account_retires_every_setup_link_of_the_account(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, deactivate: Change) -> None:
    """A32-006 — NEW, red until A7b-2 (today the refusal revokes the link shown, and only it, without consuming it: deactivated, the account waits again — inactive, setup links, none consumed —, and its other link sets the password of whoever holds it): boss, an operator's active administrator written as a row beside root, holds two live setup links, issued directly. ``complete_admin_setup`` with one of them is ``None`` and changes no account (ND 6, as today); the refusal now retires every setup link of the account — ``retire_tokens``: revoked and consumed, without a consumer —, not only the one shown. Deactivated afterwards — ``set_user_active(..., False)`` or ``update_user_status(..., is_active=False)`` —, boss waits for nothing: not ``is_pending_admin``, not in ``pending_admin_ids``, ``pending_admin`` ``None``, ``issue_setup_link`` ``None``; both its links retired, and neither sets its password. The API side is the sibling's."""
    print_section(f"A32-006: an active account's refused link, then {_named(deactivate)}")
    moment = utcnow()
    await _add_user(engine, ROOT_USERNAME, admin=True)
    boss = await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL, admin=True)
    shown = await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - HOUR)
    other = await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - timedelta(minutes=50))
    statuses = (await _status(engine, shown.token, moment), await _status(engine, other.token, moment))
    assert statuses == (TokenStatus.VALID, TokenStatus.VALID), f"barrier: both setup links are valid: {statuses}"
    accounts_before = (await _snapshot(engine))["users"]

    refused = await _complete(engine, bootstrap, shown.token, now=moment)

    assert refused is None, f"an account already active is set up already (ND 6): {refused!r}"
    assert (await _snapshot(engine))["users"] == accounts_before, "the refusal must change no account"
    await deactivate(engine, boss, moment)
    assert (await _account(engine, boss)).is_active is False, "barrier: boss is deactivated"
    waiting = await _waiting(engine, bootstrap, boss)
    assert waiting == (False, False, None), f"red until A7b-2: refusing the link of an active account must retire its setup links, or a deactivation makes it wait again: (is_pending_admin, in pending_admin_ids, pending_admin) {waiting}"
    later = moment + AFTERWARDS
    before = await _snapshot(engine)
    assert await _issue_setup_link(engine, bootstrap, now=later) is None, "./dev.py user setup-link must find nobody to give a link to"
    assert _link_states(await _setup_rows(engine, boss)) == [RETIRED, RETIRED], "every setup link of boss must be retired — revoked and consumed, without a consumer —, not only the one shown"
    for link in (shown, other):
        assert await _complete(engine, bootstrap, link.token, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "no setup link of boss may set its password"
    assert await _snapshot(engine) == before, "issue_setup_link and the refused links must write nothing"
    print_success("both links retired; deactivated, boss waits for nothing")


# red until A7b-2
@pytest.mark.asyncio
async def test_the_cli_retires_an_expired_setup_link_and_the_account_waits_no_more(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A32-007 — NEW, red until A7b-2 (workstream E's review; today the expired link stays unconsumed, so the deactivated account waits again — for a new link of ``./dev.py user setup-link``, or a re-arming token): the waiting administrator whose only setup link expired a minute ago — issued 72 hours and a minute before, as UADM-065 dates it on the API side —, activated by the CLI's ``user activate`` (``set_user_active(..., True)``), then deactivated by its ``user deactivate`` (``set_user_active(..., False)``). The account waits for nothing — not ``is_pending_admin``, ``issue_setup_link`` ``None``, and the rest of C2's effect 3 —, and the expired link is retired: revoked and consumed, without a consumer, it now inspects ``revoked``, no longer ``expired``. A32-002 walks the same path among its eight, without reading the link."""
    print_section("A32-007: user activate, then user deactivate, the only setup link expired")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment, expired=True)
    assert len(await _setup_rows(engine, user_id)) == 1, "barrier: the expired link is the account's only setup link"

    await _activate_by_set_user_active(engine, user_id, moment)
    await _deactivate_by_set_user_active(engine, user_id, moment)

    later = moment + AFTERWARDS
    assert (await _account(engine, user_id)).is_active is False, "barrier: the account is inactive again"
    await _assert_waits_for_nothing(engine, bootstrap, f02, user_id, later, "user activate, then user deactivate, its only setup link expired")
    status = await _status(engine, TOKEN_ONE, later)
    assert status == TokenStatus.REVOKED, f"the expired setup link must have been retired by the activation, so it inspects revoked: it is {status}"
    assert _link_states(await _setup_rows(engine, user_id)) == [RETIRED], "its only setup link must be retired: revoked and consumed, without a consumer"
    print_success("waits for nothing; the expired link retired, inspecting revoked")


# =============================================================================
# A33 — LOT A7b-2: THE WAITING ADMINISTRATOR'S NEW ADDRESS (N60)
# =============================================================================
# A-33: the waiting administrator's setup link went to its address. When LIBREFOLIO_ADMIN_EMAIL changes while it waits,
# the restart moves the account to the new address (``_follow_variables``), and the link delivered to the old one keeps
# working. The contract: a real change of the address — another address under ``same_email`` (P18), not the same one in
# other capitals — revokes the account's live setup links. Revoked, not retired: the account still waits, and a new link
# is one ``./dev.py user setup-link`` away. The restart then has no live link, ``EXPIRED``; unless the config carries a
# token never seen, which re-arms it after the revocation, ``REARMED``. ``update_profile`` on the waiting account (the
# CLI's ``user set-email``) is pinned in test_user_profile.py, UPROF-003 to UPROF-005. Every call here takes its ``now``:
# these scenes are dated from NOW, as the rest of this file.

#: Real changes of the address in the variables: (the config's username, the config's email).
NEW_ADDRESSES = [
    pytest.param(ADMIN_USERNAME, OTHER_EMAIL, id="the-email"),
    pytest.param(OTHER_USERNAME, OTHER_EMAIL, id="the-username-and-the-email"),
]
#: How the waiting administrator's link was made: from the variable's token, which the restart's config still carries;
#: or generated, the restart's config carrying none.
LINK_ORIGINS = [
    pytest.param(TOKEN_ONE, id="the-variables-token"),
    pytest.param(None, id="a-generated-link"),
]
#: Changes in the variables that give the waiting administrator no new address: (the config's username, the config's
#: email, whether boss holds OTHER_EMAIL first, the account's username and email expected after the restart).
NO_NEW_ADDRESS = [
    pytest.param(ADMIN_USERNAME, "Admin@Example.COM", False, (ADMIN_USERNAME, "Admin@Example.COM"), id="the-address-in-other-capitals"),
    pytest.param(OTHER_USERNAME, ADMIN_EMAIL, False, (OTHER_USERNAME, ADMIN_EMAIL), id="the-username-alone"),
    pytest.param(ADMIN_USERNAME, OTHER_EMAIL, True, (ADMIN_USERNAME, ADMIN_EMAIL), id="an-address-another-account-holds"),
]


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("token", LINK_ORIGINS)
@pytest.mark.parametrize(("username", "email"), NEW_ADDRESSES)
async def test_a_new_address_in_the_variables_revokes_the_link_delivered_to_the_old_one(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, username: str, email: str, token: Optional[str]) -> None:
    """A33-001 — NEW, red until A7b-2 (today the link stays valid, and the restart is ``PENDING``): a restart an hour after the creation, the config naming another address — alone or with another username —, and no token never seen: the link delivered to the old address is revoked — ``inspect_token`` says ``revoked`` —, not retired (``consumed_at`` empty); no live link is left, so ``EXPIRED``. The account takes the variables' username and address and still waits for its setup; the old link sets nothing — ``complete_admin_setup`` is ``None``, nothing changes —; ``issue_setup_link`` still gives it a new link, valid."""
    print_section(f"A33-001: a new address, {'the variable token' if token else 'a generated link'}")
    created = await _created(engine, bootstrap, f02, token=token)
    link = token or created.link_token
    moment = NOW + HOUR
    assert await _status(engine, link, moment) == TokenStatus.VALID, "barrier: the link delivered to the old address is valid"

    result = await _run(engine, bootstrap, _config(f02, username=username, email=email, token=token), now=moment)

    old = await _inspect(engine, link, moment)
    assert old.status == TokenStatus.REVOKED, f"red until A7b-2: a new address must revoke the setup link delivered to the old one: it is {old.status}"
    assert old.record is not None and old.record.consumed_at is None, "revoked, not retired: the account still waits for its setup"
    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, None), f"no live link is left: expected EXPIRED, got {result!r}"
    assert await _accounts(engine) == {username: (created.user_id, email, False, True)}, "the account takes the variables' username and address"
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "the account still waits for its setup"
    later = moment + HOUR
    before = await _snapshot(engine)
    assert await _complete(engine, bootstrap, link, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "the link delivered to the old address must set nothing"
    assert await _snapshot(engine) == before, "the old link must change nothing"
    issued = await _issue_setup_link(engine, bootstrap, now=later)
    assert isinstance(issued, IssuedToken), f"./dev.py user setup-link must still give the waiting account a new link: {issued!r}"
    fresh = await _inspect(engine, issued.token, later)
    assert fresh.status == TokenStatus.VALID and fresh.record is not None and fresh.record.user_id == created.user_id, f"the new link must be the waiting account's, valid: {fresh.status}"
    print_success("the old link revoked; EXPIRED; still waiting, a new link one command away")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize("token", LINK_ORIGINS)
async def test_a_new_address_with_a_token_never_seen_rearms_after_the_revocation(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, token: Optional[str]) -> None:
    """A33-002 — GUARD, green today and after: a new address in the variables, with a token never seen, TOKEN_TWO: ``REARMED`` — the old link revoked before the new token is stored, never after it —: TOKEN_TWO is the account's one live setup link, valid until ``now`` + 72 h; the link delivered to the old address revoked; the account at its new address, still waiting."""
    print_section(f"A33-002: a new address and a new token, {'the variable token' if token else 'a generated link'} before")
    created = await _created(engine, bootstrap, f02, token=token)
    link = token or created.link_token
    moment = NOW + HOUR

    result = await _run(engine, bootstrap, _config(f02, email=OTHER_EMAIL, token=TOKEN_TWO), now=moment)

    rearmed = await _inspect(engine, TOKEN_TWO, moment)
    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.REARMED, None), f"expected REARMED: {result!r}"
    assert rearmed.status == TokenStatus.VALID and rearmed.record is not None, f"the new token must be a valid setup link: {rearmed.status}"
    assert (rearmed.record.user_id, ensure_utc(rearmed.record.expires_at)) == (created.user_id, moment + SETUP_TTL)
    assert await _status(engine, link, moment) == TokenStatus.REVOKED, "the link delivered to the old address must be revoked"
    assert [row.id for row in await _live_setup_rows(engine, moment)] == [rearmed.record.id], "one live setup link: the new token"
    assert await _accounts(engine) == {ADMIN_USERNAME: (created.user_id, OTHER_EMAIL, False, True)}
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "the account still waits for its setup"
    print_success("REARMED: the new token the one live link, the old one revoked")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize(("username", "email", "held", "expected"), NO_NEW_ADDRESS)
async def test_a_change_that_gives_no_new_address_revokes_no_setup_link(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, username: str, email: str, held: bool, expected: tuple[str, str]) -> None:
    """A33-003 — GUARD, green today and after: the variables change, and the waiting administrator's address does not become another one — the same address in other capitals (P18: the account takes the variable's form), the username alone, or an address another account already holds (the account keeps its own; an error is logged) —: ``PENDING``, no token moves, and the link still completes the setup."""
    print_section(f"A33-003: {username} <{email}>, held by another account: {held}")
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    if held:
        await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL)
    tokens_before = (await _snapshot(engine))["tokens"]
    moment = NOW + HOUR

    result = await _run(engine, bootstrap, _config(f02, username=username, email=email, token=TOKEN_ONE), now=moment)

    accounts_after = await _accounts(engine)
    assert (result.action, result.link_token) == (bootstrap.BootstrapAction.PENDING, None), f"expected PENDING: {result!r}"
    assert accounts_after.get(expected[0]) == (created.user_id, expected[1], False, True), f"the waiting administrator must be {expected}: {accounts_after}"
    assert (await _snapshot(engine))["tokens"] == tokens_before, "no setup link may move: the address is the same one"
    user = await _complete(engine, bootstrap, TOKEN_ONE, now=moment + HOUR)
    assert user is not None and user.id == created.user_id and user.is_active, f"the link must still complete the setup: {user!r}"
    print_success("PENDING; nothing revoked; the link completes the setup")


# =============================================================================
# A42 — LOT A-42: THE SETUP LINK ISSUED, AND SPENT, UNDER THE WRITE LOCK
# =============================================================================
# The race of A-42: ``issue_setup_link`` (the CLI's ``user setup-link``) and the startup re-arm (``_keep_pending_admin``,
# a token of the variable never seen) read «the account waits», then write. Another worker serving ``POST /auth/setup``
# may complete the setup in between: today the issue goes on, and the account, set up, holds a live setup link — which a
# later deactivation turns into a way in, the account waiting again for a link its holder already has. The contract
# (approved by the coordinator, 17/10): they decide «waiting» under SQLite's write lock, and when by then the account no
# longer waits they issue nothing — rolled back; the CLI says nobody waits; the start does not re-arm.
#
# The race is played without threads, and without assuming which read the module makes nor with which function: the
# rival — that setup, through the account's link, on another connection to the same private file — commits right before
# the first write statement of the issuer's engine (``_rival_before_the_first_write``). Every read before it sees the
# account waiting, every read after it the account set up: «decided under the write lock», seen from outside. A guard
# (A42-004) holds the other side: a rival that leaves the account waiting stops nothing.
#
# The spending of A-42: ``complete_admin_setup`` refuses a link while another setup link of the same account is consumed
# — the account was set up before, or its links were retired —: nothing changes (the password, the active flag, the
# session version), the account's never-consumed setup links are retired, a warning is logged. Its scene is rows, as the
# race above or an earlier 1.3 build leaves them. Every call takes its ``now`` but the CLI's: A42-002 is dated from the
# clock, as CLI-003.

#: The first word of the statements that open a write in SQLite: the rival commits right before the first of them.
WRITE_STATEMENTS = frozenset({"INSERT", "UPDATE", "DELETE", "REPLACE", "BEGIN", "SAVEPOINT"})
#: How the other setup link of the account was spent before the stray ones were left live (A42-005): through the
#: account's setup, or retired when the account was set up another way (A-32).
SPENT_BEFORE = [pytest.param("set-up-through-it", id="set-up-through-another-link"), pytest.param("retired", id="its-links-retired")]
#: The issuers of A-42 that a rival leaving the account waiting must not stop (A42-004).
ISSUERS = [pytest.param("issue-setup-link", id="user-setup-link"), pytest.param("restart-with-a-new-token", id="a-restart-with-a-token-never-seen")]

#: The database as the rival left it, appended once it committed: what the issuer must leave as it is.
Landed = list[dict[str, list[Any]]]


@contextlib.asynccontextmanager
async def _issuer_engine(engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """A second engine on the private file of ``engine``, the issuer's: a listener on it sees neither the rival's statements nor the test's own reads. Disposed at the end."""
    issuer = create_async_engine(engine.url, poolclass=NullPool)
    try:
        yield issuer
    finally:
        await issuer.dispose()


@contextlib.contextmanager
def _rival_before_the_first_write(issuer: AsyncEngine, rival: Callable[[], Awaitable[None]]) -> Iterator[list[str]]:
    """``rival`` run right before the first write statement of ``issuer``'s engine; yields the statement it ran before, in a list (the barrier: empty, the rival never ran).

    A ``before_cursor_execute`` listener: when the first INSERT, UPDATE, DELETE, REPLACE, BEGIN or SAVEPOINT is about to
    run, it awaits the rival from the issuer's own greenlet (``await_only``, as SQLAlchemy's asyncio layer awaits), then
    lets the statement go. pysqlite defers ``BEGIN`` to the first write, and in WAL a reader holds nothing once its
    statement is done: the issuer holds no lock yet, so the rival writes and commits on its own connection, and the
    transaction the issuer's write opens sees that commit. No thread and no sleep: one interleaving, every time.
    """
    fired: list[str] = []

    def before_cursor_execute(_connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        words = statement.split(None, 1)
        if fired or not words or words[0].upper() not in WRITE_STATEMENTS:
            return
        fired.append(statement)
        await_only(rival())

    event.listen(issuer.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield fired
    finally:
        event.remove(issuer.sync_engine, "before_cursor_execute", before_cursor_execute)


def _setup_completed_meanwhile(engine: AsyncEngine, bootstrap: ModuleType, token: str, moment: datetime, landed: Landed) -> Callable[[], Awaitable[None]]:
    """The rival of A-42: the waiting administrator's setup completed through ``token`` with SETUP_PASSWORD, on another connection — another worker serving ``POST /auth/setup`` —; the database as it leaves it, appended to ``landed``."""

    async def rival() -> None:
        user = await _complete(engine, bootstrap, token, now=moment)
        assert user is not None and user.is_active, f"barrier: the rival's setup must complete: {user!r}"
        landed.append(await _snapshot(engine))

    return rival


def _setup_links_revoked_meanwhile(engine: AsyncEngine, user_id: int, moment: datetime, landed: Landed) -> Callable[[], Awaitable[None]]:
    """A rival that leaves the account waiting (A42-004): its live setup links revoked on another connection, as a new address in the variables revokes them (A-33); the database as it leaves it, appended to ``landed``."""

    async def rival() -> None:
        async with AsyncSession(engine) as session:
            revoked = await token_service.revoke_tokens(session, user_id=user_id, purpose=ADMIN_SETUP, now=moment)
            await session.commit()
        assert revoked == 1, f"barrier: the rival revokes the account's one live setup link: {revoked}"
        landed.append(await _snapshot(engine))

    return rival


async def _assert_set_up_by_the_rival(engine: AsyncEngine, user_id: int, moment: datetime) -> None:
    """After a lost race: the account as the rival's setup left it — active, SETUP_PASSWORD its own — and no setup link of the instance live."""
    account = await _account(engine, user_id)
    assert (account.is_active, verify_password(SETUP_PASSWORD, account.hashed_password)) == (True, True), "the account must be as the rival's setup left it: active, its password chosen through the link"
    assert await _live_setup_rows(engine, moment) == [], "no setup link may be left live"


async def _set_up_before_with_stray_links(engine: AsyncEngine, spent: str) -> tuple[int, IssuedToken, list[IssuedToken]]:
    """carol, as rows: an administrator set up before and deactivated since — inactive —, her first setup link spent three hours before NOW (``set-up-through-it``: consumed by her setup; ``retired``: retired, carol set up another way, A-32), and two stray setup links issued after, live, as the race of A-42 or an earlier 1.3 build leaves them. ``(carol's id, the spent link, [the stray links])``."""
    user_id = await _add_user(engine, "carol", active=False, admin=True)
    first = await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW - 4 * HOUR)
    async with AsyncSession(engine) as session:
        if spent == "set-up-through-it":
            assert await token_service.consume_token(session, first.token, ADMIN_SETUP, consumed_by_user_id=user_id, now=NOW - 3 * HOUR) is not None, "setup: carol's setup spends her first link"
        else:
            assert await token_service.retire_tokens(session, user_id=user_id, purpose=ADMIN_SETUP, now=NOW - 3 * HOUR) == 1, "setup: carol's first link is retired"
        await session.commit()
    strays = [await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW - 2 * HOUR), await _issue(engine, ADMIN_SETUP, user_id=user_id, now=NOW - HOUR)]
    return user_id, first, strays


# red until A-42/A-43
@pytest.mark.asyncio
async def test_issue_setup_link_issues_nothing_for_an_account_set_up_before_its_first_write(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A42-001 — NEW, red until A-42 (today the issue goes on: the account, set up, holds a new live setup link): the waiting administrator, created with TOKEN_ONE; ``issue_setup_link(session, now=...)`` on the issuer's connection, its setup completed through TOKEN_ONE on another one and committed right before the issuer's first write. ``None``, and nothing written — rolled back, even when its caller commits —: the database exactly as the setup left it, the account active with the password chosen through the link, no setup link live."""
    print_section("A42-001: issue_setup_link, the setup completed before its first write")
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    moment = NOW + HOUR
    landed: Landed = []

    async with _issuer_engine(engine) as issuer:
        with _rival_before_the_first_write(issuer, _setup_completed_meanwhile(engine, bootstrap, TOKEN_ONE, moment, landed)) as fired:
            issued = await _issue_setup_link(issuer, bootstrap, now=moment)

    assert fired and landed, f"barrier: issue_setup_link never wrote, so the rival's setup never landed between its reads and its first write: {issued!r}"
    assert issued is None, f"red until A-42: the account was set up between issue_setup_link's read and its first write, so it must issue nothing: it issued a setup link of account {issued.record.user_id if issued else None}"
    assert await _snapshot(engine) == landed[0], "issue_setup_link must write nothing — rolled back, even when its caller commits —: the database as the setup left it"
    await _assert_set_up_by_the_rival(engine, created.user_id, moment)
    print_success("nothing issued; the database as the setup left it")


# red until A-42/A-43
@pytest.mark.asyncio
async def test_setup_link_says_nobody_waits_when_the_setup_completes_before_its_first_write(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A42-002 — NEW, red until A-42 (today it prints ✅ and a live link for the account already set up, and answers ``True``): ``cmd_setup_link`` — ``./dev.py user setup-link`` — on the issuer's connection, the waiting administrator's setup completed through TOKEN_ONE on another one right before the command's first write. The command says nobody waits: falsy, a line starting with ``❌`` (its wording is not pinned), no link printed; nothing written, the database as the setup left it.

    It reads the clock: the scene is dated from it, the administrator created an hour before.
    """
    print_section("A42-002: user setup-link, the setup completed before its first write")
    moment = utcnow()
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE, now=moment - HOUR)
    landed: Landed = []

    async with _issuer_engine(engine) as issuer:
        monkeypatch.setattr(cli, "get_async_engine", lambda: issuer)
        capsys.readouterr()
        with _rival_before_the_first_write(issuer, _setup_completed_meanwhile(engine, bootstrap, TOKEN_ONE, moment, landed)) as fired:
            ok = await cli.cmd_setup_link()
        out = capsys.readouterr().out

    assert fired and landed, f"barrier: the command never wrote, so the rival's setup never landed between its reads and its first write: {out!r}"
    assert not ok, f"red until A-42: the account was set up between the command's read and its first write: ./dev.py user setup-link must say nobody waits, it answered {ok!r}: {out!r}"
    assert any(line.startswith("❌") for line in out.splitlines()), f"a line must start with ❌: {out!r}"
    assert "#token=" not in out, f"no link may be printed: {out!r}"
    assert await _snapshot(engine) == landed[0], "the command must write nothing: the database as the setup left it"
    await _assert_set_up_by_the_rival(engine, created.user_id, utcnow())
    print_success("❌, nothing printed, nothing written")


# red until A-42/A-43
@pytest.mark.asyncio
async def test_a_restart_does_not_rearm_an_account_set_up_before_its_first_write(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A42-003 — NEW, red until A-42 (today ``REARMED``: TOKEN_TWO stored as a live setup link of the account already set up): a restart an hour after the creation with TOKEN_TWO in the config — a token never seen, which re-arms a waiting administrator (BOOT-010) —, the administrator's setup completed through TOKEN_ONE on another connection right before the restart's first write. The start does not re-arm: neither ``REARMED`` nor ``CREATED`` — which other action it answers is not pinned —, no ``link_token``, TOKEN_TWO never stored (``unknown``), nothing written — even when its caller commits —: the database as the setup left it."""
    print_section("A42-003: a restart re-arming, the setup completed before its first write")
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    moment = NOW + HOUR
    landed: Landed = []

    async with _issuer_engine(engine) as issuer:
        with _rival_before_the_first_write(issuer, _setup_completed_meanwhile(engine, bootstrap, TOKEN_ONE, moment, landed)) as fired:
            result = await _run(issuer, bootstrap, _config(f02, token=TOKEN_TWO), now=moment, then_commit=True)

    assert fired and landed, f"barrier: the restart never wrote, so the rival's setup never landed between its reads and its first write: {result!r}"
    assert result.action not in (bootstrap.BootstrapAction.REARMED, bootstrap.BootstrapAction.CREATED) and result.link_token is None, f"red until A-42: the account was set up between the restart's read and its first write, so the start must not re-arm it: {result!r}"
    assert await _status(engine, TOKEN_TWO, moment) == TokenStatus.UNKNOWN, "the variable's new token must never be stored"
    assert await _snapshot(engine) == landed[0], "the restart must write nothing: the database as the setup left it"
    await _assert_set_up_by_the_rival(engine, created.user_id, moment)
    print_success(f"{result.action}: not re-armed, nothing written")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize("issuer_kind", ISSUERS)
async def test_a_rival_that_leaves_the_account_waiting_stops_no_issue(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, issuer_kind: str) -> None:
    """A42-004 — GUARD, green today and after: «waiting» is decided on what the database holds under the lock, not on whether anything moved. The waiting administrator's live setup link revoked on another connection right before the issuer's first write — what a new address in the variables does (A-33): the account still waits —: ``issue_setup_link`` still issues a new link, valid; a restart with TOKEN_TWO still re-arms, ``REARMED``, TOKEN_TWO valid. Either way the new link is the account's one live setup link, and the account still waits."""
    print_section(f"A42-004: {issuer_kind}, the account still waiting after the rival")
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    moment = NOW + HOUR
    landed: Landed = []

    async with _issuer_engine(engine) as issuer:
        with _rival_before_the_first_write(issuer, _setup_links_revoked_meanwhile(engine, created.user_id, moment, landed)) as fired:
            if issuer_kind == "issue-setup-link":
                outcome: Any = await _issue_setup_link(issuer, bootstrap, now=moment)
            else:
                outcome = await _run(issuer, bootstrap, _config(f02, token=TOKEN_TWO), now=moment)

    assert fired and landed, f"barrier: the rival never ran between the issuer's reads and its first write: {outcome!r}"
    if issuer_kind == "issue-setup-link":
        assert isinstance(outcome, IssuedToken), f"the account still waits: issue_setup_link must issue a new link: {outcome!r}"
        token = outcome.token
    else:
        assert (outcome.action, outcome.link_token) == (bootstrap.BootstrapAction.REARMED, None), f"the account still waits: the restart must re-arm it: {outcome!r}"
        token = TOKEN_TWO
    fresh = await _inspect(engine, token, moment)
    assert fresh.status == TokenStatus.VALID and fresh.record is not None and fresh.record.user_id == created.user_id, f"the new link must be the waiting account's, valid: {fresh.status}"
    assert [row.id for row in await _live_setup_rows(engine, moment)] == [fresh.record.id], "the new link must be the one live setup link"
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "the account still waits for its setup"
    print_success("issued: the account still waited")


# red until A-42/A-43
@pytest.mark.asyncio
@pytest.mark.parametrize("spent", SPENT_BEFORE)
async def test_a_setup_link_is_refused_once_another_setup_link_of_the_account_was_consumed(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, spent: str) -> None:
    """A42-005 — NEW, red until A-42 (today the stray link sets the password of whoever holds it and activates the account): carol, set up before — through another setup link, or her links retired —, deactivated since, holds two stray live setup links (rows: ``_set_up_before_with_stray_links``). ``complete_admin_setup`` with one of them is ``None``: nothing changes on the account — its password hash, ``is_active``, its session version, the whole row —, nor in the settings; every never-consumed setup link of carol is retired — revoked and consumed, without a consumer —, the one shown and the other, the shown one inspecting ``revoked``; the spent link stays as it was. A warning about carol (``user_id``) is logged — its wording is not pinned —, and no event holds a link."""
    print_section(f"A42-005: a stray setup link of an account {spent}")
    user_id, first, strays = await _set_up_before_with_stray_links(engine, spent)
    shown = strays[0]
    statuses = [await _status(engine, issued.token, NOW) for issued in (first, *strays)]
    spent_status = TokenStatus.CONSUMED if spent == "set-up-through-it" else TokenStatus.REVOKED
    assert statuses == [spent_status, TokenStatus.VALID, TokenStatus.VALID], f"barrier: the first link spent, the two stray ones valid: {statuses}"
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        user = await _complete(engine, bootstrap, shown.token, now=NOW, password=INTRUDER_PASSWORD, then_commit=True)

    after = await _snapshot(engine)
    rows = {row.id: row for row in await _setup_rows(engine, user_id)}
    assert user is None, f"red until A-42: another setup link of carol was consumed — she was set up before —, so a stray one must set nothing: it set up account {user.id if user else None}"
    assert (after["users"], after["settings"]) == (before["users"], before["settings"]), "nothing may change on the account — its password hash, is_active, its session version —, nor in the settings"
    assert _link_states([rows[issued.record.id] for issued in strays]) == [RETIRED, RETIRED], "every never-consumed setup link of carol must be retired — revoked and consumed, without a consumer —, the one shown and the other"
    assert await _status(engine, shown.token, NOW) == TokenStatus.REVOKED, "the link shown must inspect revoked"
    assert [row for row in after["tokens"] if row["id"] == first.record.id] == [row for row in before["tokens"] if row["id"] == first.record.id], "the spent link must stay as it was"
    assert [event for event in _at_level(events, "warning") if event.get("user_id") == user_id], f"the refusal must be logged as a warning about carol (user_id {user_id}): {_logged(events)}"
    assert [event for event in _logged(events) if any(issued.token in repr(event) for issued in strays)] == [], "no log event may hold a link"
    print_success("refused; nothing changed; both stray links retired; a warning")


# guard
@pytest.mark.asyncio
async def test_setup_links_revoked_or_expired_beside_the_live_one_refuse_nothing(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A42-006 — GUARD, green today and after: A42-005's refusal is a consumed sibling's alone. The waiting administrator re-armed with TOKEN_TWO — TOKEN_ONE revoked, never consumed — holds besides an expired setup link, neither consumed nor revoked (a row); ``complete_admin_setup`` with TOKEN_TWO sets it up: the account it returns, active, still a superuser, its password the one chosen through the link."""
    print_section("A42-006: siblings revoked or expired, none consumed")
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE)
    rearmed = await _run(engine, bootstrap, _config(f02, token=TOKEN_TWO), now=NOW + HOUR)
    assert rearmed.action == bootstrap.BootstrapAction.REARMED, f"setup: TOKEN_TWO re-arms the waiting administrator: {rearmed!r}"
    expired = await _issue(engine, ADMIN_SETUP, user_id=created.user_id, now=NOW - SETUP_TTL)
    moment = NOW + 2 * HOUR
    statuses = [await _status(engine, token, moment) for token in (TOKEN_ONE, expired.token, TOKEN_TWO)]
    assert statuses == [TokenStatus.REVOKED, TokenStatus.EXPIRED, TokenStatus.VALID], f"barrier: one link revoked, one expired, one live — none consumed: {statuses}"

    user = await _complete(engine, bootstrap, TOKEN_TWO, now=moment)

    account = await _account(engine, created.user_id)
    assert user is not None and user.id == created.user_id, f"no sibling was consumed: the live link must set the account up: {user!r}"
    assert (account.is_active, account.is_superuser, verify_password(SETUP_PASSWORD, account.hashed_password)) == (True, True, True), "active, a superuser, its password the one chosen through the link"
    print_success("set up: a revoked or an expired sibling refuses nothing")


# =============================================================================
# A43 — LOT A-43: THE SETUP LINK WHEN THE ACCOUNT IS DEACTIVATED OR DEMOTED
# =============================================================================
# A-43: a deactivation leaves the account's setup links as they are today. The waiting administrator, already inactive,
# keeps a live link after root's ``{is_active: false}`` or the CLI's ``user deactivate``; an active administrator holding
# a stray setup link becomes, once deactivated, an account that waits — inactive, a setup link, none consumed —, and the
# link sets its password. The contract: ``update_user_status(..., is_active=False)`` (the Users tab's PATCH) and
# ``set_user_active(..., False)`` (the CLI's ``user deactivate``) revoke the live setup links of the waiting administrator
# — revoked, not retired: it still waits, for a new link of ``./dev.py user setup-link`` — and retire the never-consumed
# setup links of an account that does not wait: an active one being deactivated, or an inactive one set up before.
#
# And the waiting administrator is not demoted: ``./dev.py user demote`` refuses it — falsy, a line starting with ❌ (its
# wording is not pinned), nothing changed —, whichever layer holds the refusal, so the command itself runs here
# (``cmd_set_admin``, ``get_async_engine`` the private engine); any other administrator is demoted as before. Through
# ``user_service`` and the CLI, which read the clock: every scene is dated from it, as A32's.

#: A setup link's row once revoked, and only revoked: (revoked, consumed, consumed_by_user_id) — its account still waits.
REVOKED_ONLY = (True, False, None)

#: A scene of A43-002, from (the engine, the moment): (boss's id, its never-consumed setup links, its consumed ones).
StrayScene = Callable[[AsyncEngine, datetime], Awaitable[tuple[int, list[IssuedToken], list[IssuedToken]]]]


async def _boss_active_with_a_stray_link(engine: AsyncEngine, moment: datetime) -> tuple[int, list[IssuedToken], list[IssuedToken]]:
    """boss, an operator's active administrator written as a row, holding a stray setup link issued an hour before ``moment``, live."""
    boss = await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL, admin=True)
    return boss, [await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - HOUR)], []


async def _boss_set_up_before_with_a_stray_link(engine: AsyncEngine, moment: datetime) -> tuple[int, list[IssuedToken], list[IssuedToken]]:
    """boss, an inactive administrator set up before, as rows: its first setup link consumed by its setup two hours before ``moment``, and a stray one issued after, live."""
    boss = await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL, active=False, admin=True)
    first = await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - 3 * HOUR)
    async with AsyncSession(engine) as session:
        assert await token_service.consume_token(session, first.token, ADMIN_SETUP, consumed_by_user_id=boss, now=moment - 2 * HOUR) is not None, "setup: boss's setup spends its first link"
        await session.commit()
    return boss, [await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - HOUR)], [first]


#: Accounts that do not wait for their setup and hold a never-consumed setup link (A43-002).
NOT_WAITING_WITH_A_STRAY_LINK = [
    pytest.param(_boss_active_with_a_stray_link, id="an-active-administrator-with-a-stray-link"),
    pytest.param(_boss_set_up_before_with_a_stray_link, id="an-inactive-administrator-set-up-before-with-a-stray-link"),
]
#: Administrators beside the waiting one, demoted by the CLI as before (A43-005): (active, whether its setup link was spent).
OTHER_ADMINISTRATORS = [
    pytest.param(True, False, id="an-active-administrator"),
    pytest.param(False, False, id="an-inactive-administrator-without-any-link"),
    pytest.param(False, True, id="an-inactive-administrator-whose-setup-link-was-spent"),
]


async def _demote_with_the_cli(cli: ModuleType, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], username: str) -> tuple[Any, str]:
    """``./dev.py user demote <username>``: ``cmd_set_admin(username, False)`` in-process, ``get_async_engine`` the private engine — what it answered, and what it printed."""
    monkeypatch.setattr(cli, "get_async_engine", lambda: engine)
    capsys.readouterr()
    answer = await cli.cmd_set_admin(username, False)
    return answer, capsys.readouterr().out


# red until A-42/A-43
@pytest.mark.asyncio
@pytest.mark.parametrize("deactivate", DEACTIVATIONS)
async def test_deactivating_the_waiting_administrator_revokes_its_setup_link_and_it_still_waits(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, deactivate: Change) -> None:
    """A43-001 — NEW, red until A-43 (today nothing moves: its link stays valid, as A32-004 pinned until A-43): the waiting administrator, already inactive, deactivated — ``update_user_status(..., is_active=False)``, the Users tab's PATCH, or ``set_user_active(..., False)``, the CLI's ``user deactivate`` —: its live setup link is revoked in the commit of the deactivation — ``inspect_token`` says ``revoked`` —, and only revoked: ``consumed_at`` empty, so the account still waits — ``is_pending_admin``, in ``pending_admin_ids``, the one ``pending_admin`` answers —, inactive, a superuser, its password hash untouched. A warning about the account (``user_id``) is logged — the plan's point 3, «un avviso nel log»; its wording is not pinned —, holding no link. The revoked link sets nothing — ``complete_admin_setup`` ``None``, nothing changes —; ``issue_setup_link`` gives the account a new link, which sets it up: active, still a superuser, its password the one chosen through that link."""
    print_section(f"A43-001: the waiting administrator {_named(deactivate)}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment)
    hashed = (await _account(engine, user_id)).hashed_password

    with _captured(bootstrap) as events:
        await deactivate(engine, user_id, moment)

    later = moment + AFTERWARDS
    status = await _status(engine, TOKEN_ONE, later)
    assert status == TokenStatus.REVOKED, f"red until A-43: deactivating the waiting administrator must revoke its live setup link: it is still {status}"
    assert _link_states(await _setup_rows(engine, user_id)) == [REVOKED_ONLY], "revoked, not retired: consumed_at stays empty, so the account still waits"
    assert await _waiting(engine, bootstrap, user_id) == (True, True, user_id), "the account must still wait for its setup"
    account = await _account(engine, user_id)
    assert (account.is_active, account.is_superuser, account.hashed_password) == (False, True, hashed), "inactive, a superuser, its password hash untouched"
    assert [event for event in _at_level(events, "warning") if event.get("user_id") == user_id], f"the revocation must be logged as a warning about the account (user_id {user_id}): {_logged(events)}"
    assert _holding(events, CANARY) == [], "no log event may hold the link"
    before = await _snapshot(engine)
    assert await _complete(engine, bootstrap, TOKEN_ONE, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "the revoked link must set nothing"
    assert await _snapshot(engine) == before, "the revoked link must change nothing"
    issued = await _issue_setup_link(engine, bootstrap, now=later)
    assert isinstance(issued, IssuedToken), f"./dev.py user setup-link must give the waiting account a new link: {issued!r}"
    user = await _complete(engine, bootstrap, issued.token, now=later + timedelta(minutes=1))
    after = await _account(engine, user_id)
    assert user is not None and user.id == user_id, f"the new link must set the account up: {user!r}"
    assert (after.is_active, after.is_superuser, verify_password(SETUP_PASSWORD, after.hashed_password)) == (True, True, True), "active, a superuser, its password the one chosen through the new link"
    print_success("revoked, still waiting; a new link sets it up")


# red until A-42/A-43
@pytest.mark.asyncio
@pytest.mark.parametrize("scene", NOT_WAITING_WITH_A_STRAY_LINK)
@pytest.mark.parametrize("deactivate", DEACTIVATIONS)
async def test_deactivating_an_account_that_does_not_wait_retires_its_setup_links(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, deactivate: Change, scene: StrayScene) -> None:
    """A43-002 — NEW, red until A-43 (today the stray link stays valid; deactivated, an active administrator then waits — inactive, a setup link, none consumed — and the link sets its password): boss does not wait for a setup — active, or set up before — and holds a stray live setup link; root, active, beside. Deactivated — ``update_user_status(..., is_active=False)`` or ``set_user_active(..., False)`` —, boss's never-consumed setup links are retired in the commit of the deactivation — revoked and consumed, without a consumer; ``inspect_token`` says ``revoked`` —, the link its setup consumed stays as it was; boss is inactive and waits for nothing (C2, effect 3: not ``is_pending_admin``, ``issue_setup_link`` ``None``, a restart ``IGNORED``); and the stray link sets nothing."""
    print_section(f"A43-002: {_named(scene)}, {_named(deactivate)}")
    moment = utcnow()
    await _add_user(engine, ROOT_USERNAME, admin=True)
    boss, strays, spent = await scene(engine, moment)
    assert await _waiting(engine, bootstrap, boss) == (False, False, None), "barrier: boss does not wait for a setup"

    await deactivate(engine, boss, moment)

    later = moment + AFTERWARDS
    statuses = [await _status(engine, issued.token, later) for issued in strays]
    assert statuses == [TokenStatus.REVOKED] * len(strays), f"red until A-43: deactivating an account that does not wait must retire its never-consumed setup links: they are {statuses}"
    rows = {row.id: row for row in await _setup_rows(engine, boss)}
    assert _link_states([rows[issued.record.id] for issued in strays]) == [RETIRED] * len(strays), "retired: revoked and consumed at once, without a consumer"
    assert [(rows[issued.record.id].consumed_by_user_id, rows[issued.record.id].revoked_at) for issued in spent] == [(boss, None)] * len(spent), "the link its setup consumed stays as it was"
    assert (await _account(engine, boss)).is_active is False, "boss is inactive"
    await _assert_waits_for_nothing(engine, bootstrap, f02, boss, later, f"{_named(deactivate)} of boss, who does not wait")
    before = await _snapshot(engine)
    for issued in strays:
        assert await _complete(engine, bootstrap, issued.token, now=later, password=INTRUDER_PASSWORD, then_commit=True) is None, "the stray link must set nothing"
    assert await _snapshot(engine) == before, "the stray link must change nothing"
    print_success("the stray link retired; boss waits for nothing")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize("deactivate", DEACTIVATIONS)
async def test_deactivating_another_account_moves_no_setup_link_of_the_waiting_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, deactivate: Change) -> None:
    """A43-003 — GUARD, green today and after: the revocation and the retirement are the deactivated account's own. carol, an active member holding no token, deactivated beside the waiting administrator: no account token moves; the waiting administrator still waits, its link valid."""
    print_section(f"A43-003: another account {_named(deactivate)}")
    moment = utcnow()
    admin_id = await _waiting_administrator(engine, bootstrap, f02, moment)
    carol = await _add_user(engine, "carol")
    tokens_before = (await _snapshot(engine))["tokens"]

    await deactivate(engine, carol, moment)

    assert (await _account(engine, carol)).is_active is False, "barrier: carol is deactivated"
    assert (await _snapshot(engine))["tokens"] == tokens_before, "no account token may move: carol holds none, and the waiting administrator's are not hers"
    assert await _waiting(engine, bootstrap, admin_id) == (True, True, admin_id), "the waiting administrator must still wait"
    assert await _status(engine, TOKEN_ONE, moment + AFTERWARDS) == TokenStatus.VALID, "its setup link must stay valid"
    print_success("nothing moved")


# red until A-42/A-43
@pytest.mark.asyncio
@pytest.mark.parametrize("expired", LINK_STATES)
async def test_the_cli_refuses_to_demote_the_waiting_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], expired: bool) -> None:
    """A43-004 — NEW, red until A-43 (today ``✅ … demoted from admin`` and ``True``: the waiting administrator, a superuser no more, sets up an ordinary account through its link): ``./dev.py user demote`` of the waiting administrator — ``cmd_set_admin(username, False)``, root active beside — is refused: falsy, a line starting with ``❌`` (its wording is not pinned), and nothing changed — every account, token and setting as it was. The account still waits; its link live, it still sets it up, a superuser. Its link live or expired: it waits all the same."""
    print_section(f"A43-004: user demote of the waiting administrator, its link {'expired' if expired else 'live'}")
    moment = utcnow()
    user_id = await _waiting_administrator(engine, bootstrap, f02, moment, expired=expired)
    before = await _snapshot(engine)

    answer, out = await _demote_with_the_cli(cli, engine, monkeypatch, capsys, ADMIN_USERNAME)

    assert not answer, f"red until A-43: ./dev.py user demote must refuse the waiting administrator: it answered {answer!r}: {out!r}"
    assert any(line.startswith("❌") for line in out.splitlines()), f"a line must start with ❌: {out!r}"
    assert await _snapshot(engine) == before, "a refused demotion must change nothing: every account, token and setting as it was"
    assert await _waiting(engine, bootstrap, user_id) == (True, True, user_id), "the account must still wait for its setup"
    if not expired:
        user = await _complete(engine, bootstrap, TOKEN_ONE, now=moment + AFTERWARDS)
        assert user is not None and (user.is_active, user.is_superuser) == (True, True), f"its link must still set it up, a superuser: {user!r}"
    print_success("❌, nothing changed, still waiting")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize(("active", "set_up_before"), OTHER_ADMINISTRATORS)
async def test_the_cli_still_demotes_any_other_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], active: bool, set_up_before: bool) -> None:
    """A43-005 — GUARD, green today and after: the refusal is the waiting administrator's alone — not the instance's while one waits, nor every inactive administrator's, nor every account that ever had a setup link. boss — active, or inactive without any link, or inactive with its setup link spent — beside the waiting administrator and root: ``./dev.py user demote boss`` answers truthy, a line starting with ``✅``; boss is an administrator no more, as active as before; the waiting administrator still waits, its link valid."""
    print_section(f"A43-005: user demote of another administrator, active={active}, set up before={set_up_before}")
    moment = utcnow()
    admin_id = await _waiting_administrator(engine, bootstrap, f02, moment)
    boss = await _add_user(engine, OTHER_USERNAME, email=OTHER_EMAIL, active=active, admin=True)
    if set_up_before:
        spent = await _issue(engine, ADMIN_SETUP, user_id=boss, now=moment - 2 * HOUR)
        async with AsyncSession(engine) as session:
            assert await token_service.consume_token(session, spent.token, ADMIN_SETUP, consumed_by_user_id=boss, now=moment - HOUR) is not None, "setup: boss's setup spends its link"
            await session.commit()

    answer, out = await _demote_with_the_cli(cli, engine, monkeypatch, capsys, OTHER_USERNAME)

    after = await _account(engine, boss)
    assert answer, f"./dev.py user demote must still demote another administrator: it answered {answer!r}: {out!r}"
    assert any(line.startswith("✅") for line in out.splitlines()), f"a line must start with ✅: {out!r}"
    assert (after.is_active, after.is_superuser) == (active, False), f"boss must be an administrator no more, as active as before: (is_active, is_superuser) {(after.is_active, after.is_superuser)}"
    assert await _waiting(engine, bootstrap, admin_id) == (True, True, admin_id), "the waiting administrator must still wait"
    assert await _status(engine, TOKEN_ONE, moment + AFTERWARDS) == TokenStatus.VALID, "its setup link must stay valid"
    print_success("demoted; the waiting administrator untouched")


# =============================================================================
# A51 — LOT A-51: THE SETUP COMPLETED WHILE THE CLI DEACTIVATES OR DEMOTES
# =============================================================================
# A-51: ``set_user_active(..., False)`` — the CLI's ``user deactivate`` — and ``set_user_admin(..., False)`` — ``user
# demote`` — load the account, then decide the last-administrator guard (``_is_last_active_admin``) on what they loaded,
# while ``_is_pending_admin`` reads the database afresh; pysqlite defers BEGIN to the first write, so nothing holds the
# account between the load and the decision. On a fresh F02 instance whose only administrator is the waiting one, a
# setup completed in that window leaves the command deciding on an account still inactive — so not the last active
# administrator — that no longer waits. The cure (approved by the coordinator, 17/10): the write lock first, the account
# refreshed, then the guards — refused as the last active administrator, falsy, nothing changed.
#
# The window is played without threads, as A42's: the setup — ``complete_admin_setup`` through TOKEN_ONE, another worker
# serving ``POST /auth/setup`` — commits on another connection right after the command loaded the account
# (``_rival_after_the_load``: the object it returns keeps what it read, inactive), or right before the command's first
# write (``_rival_before_the_first_write``, the command on an engine of its own), whichever comes first: whichever order
# the cure loads the account and takes the lock in, the setup lands before the lock. The calls are the ones the commands
# make, ``user_service.set_user_active`` and ``user_service.set_user_admin``, on a session of their own; they read the
# clock, so the scene is dated from it, as A43's.

#: What the refusal of the last-administrator guard names, in the message of ``set_user_active`` and ``set_user_admin``.
LAST_ADMIN_WORDS = "last active administrator"

#: A command of A-51 on its session — ``user deactivate`` or ``user demote`` of ADMIN_USERNAME —: its ``(success, message)``.
Command = Callable[[AsyncSession], Awaitable[tuple[bool, Optional[str]]]]


def _once(rival: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
    """``rival`` at its first call only: of the two moments that may run it (A-51), the first lands it."""
    ran: list[bool] = []

    async def once() -> None:
        if not ran:
            ran.append(True)
            await rival()

    return once


def _rival_after_the_load(monkeypatch: pytest.MonkeyPatch, username: str, rival: Callable[[], Awaitable[None]]) -> list[str]:
    """``user_service.get_user_by_username`` replaced: the real load, in the caller's session, then — for ``username`` — ``rival``, before the loaded object is returned: it keeps what it read, as an ORM object does. The usernames it loaded, in order."""
    real = user_service.get_user_by_username
    loaded: list[str] = []

    async def get_user_by_username(session: AsyncSession, name: str) -> Optional[User]:
        user = await real(session, name)
        loaded.append(name)
        if name == username:
            await rival()
        return user

    monkeypatch.setattr(user_service, "get_user_by_username", get_user_by_username)
    return loaded


async def _the_command_while_the_setup_completes(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, monkeypatch: pytest.MonkeyPatch, command: Command) -> tuple[tuple[bool, Optional[str]], int, dict[str, list[Any]]]:
    """A-51's window: a fresh F02 instance — the waiting administrator, created by the bootstrap with TOKEN_ONE an hour ago, its only account and so its only administrator —, then ``command`` on a session of its own engine while the setup completes through TOKEN_ONE, landing after the command's load of the account or before its first write, whichever comes first. ``(what the command answered, the account's id, the database as the setup left it)``.

    Barriers: before, the instance holds that one account, waiting; the setup lands once, during the command.
    """
    moment = utcnow()
    created = await _created(engine, bootstrap, f02, token=TOKEN_ONE, now=moment - HOUR)
    assert await _accounts(engine) == {ADMIN_USERNAME: (created.user_id, ADMIN_EMAIL, False, True)}, "barrier: a fresh F02 instance — its only account, so its only administrator, the waiting one"
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "barrier: the F02 administrator waits for its setup"
    landed: Landed = []
    rival = _once(_setup_completed_meanwhile(engine, bootstrap, TOKEN_ONE, moment, landed))
    loaded = _rival_after_the_load(monkeypatch, ADMIN_USERNAME, rival)

    async with _issuer_engine(engine) as issuer:
        with _rival_before_the_first_write(issuer, rival):
            async with AsyncSession(issuer) as session:
                outcome = await command(session)

    assert len(landed) == 1, f"barrier: the setup must land once, during the command — after its load of the account, or before its first write: it loaded {loaded}, the setup landed {len(landed)} time(s)"
    return outcome, created.user_id, landed[0]


# red until A-51
@pytest.mark.asyncio
async def test_user_deactivate_refuses_the_only_administrator_set_up_while_it_ran(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A51-007 — NEW, red until A-51 (today ``(True, None)``, «deactivated», while the account stays active: the guard read it inactive, as loaded — not the last active administrator —; the command raised its session version, ending the sessions its setup opened, and wrote no ``is_active``, the value it set equal to the stale one it loaded): ``./dev.py user deactivate`` of the waiting administrator — ``set_user_active(session, username, False)`` —, the only administrator of a fresh F02 instance, while its setup completes (``_the_command_while_the_setup_completes``): by the time the command decides, the account is the instance's only active administrator. Refused as the last active administrator — falsy, its message naming the last active administrator —, and nothing changed since the setup: every account, token and setting as it left them — the administrator active, an administrator, its session version, so its sessions alive."""
    print_section("A51-007: user deactivate, the setup completed while it ran")
    outcome, user_id, set_up = await _the_command_while_the_setup_completes(engine, bootstrap, f02, monkeypatch, lambda session: user_service.set_user_active(session, ADMIN_USERNAME, False))

    after = await _account(engine, user_id)
    version = next(row["session_version"] for row in set_up["users"] if row["id"] == user_id)
    afterwards = f"active {after.is_active}, an administrator {after.is_superuser}, session version {version} → {after.session_version}"
    assert outcome[0] is False and LAST_ADMIN_WORDS in str(outcome[1]), f"red until A-51: set up before it decided, the account was the only active administrator: user deactivate must refuse it as the last one; it answered {outcome!r}, the account afterwards {afterwards}"
    assert await _snapshot(engine) == set_up, "a refused deactivation must change nothing: every account, token and setting as the setup left them"
    assert (after.is_active, after.is_superuser) == (True, True), "the administrator must stay active, an administrator"
    print_success("refused: the last active administrator; nothing changed")


# red until A-51
@pytest.mark.asyncio
async def test_user_demote_refuses_the_only_administrator_set_up_while_it_ran(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A51-008 — NEW, red until A-51 (today ``(True, None)`` and the instance left without an administrator: the guard read the account inactive, as loaded — not the last active administrator —, ``_is_pending_admin`` read afresh that it waits no more, and the only active administrator is demoted): ``./dev.py user demote`` of the waiting administrator — ``set_user_admin(session, username, False)`` —, the only administrator of a fresh F02 instance, while its setup completes (``_the_command_while_the_setup_completes``). Refused as the last active administrator — falsy, its message naming the last active administrator —, and nothing changed since the setup: every account, token and setting as it left them — the account active and an administrator, its session version, so its sessions alive."""
    print_section("A51-008: user demote, the setup completed while it ran")
    outcome, user_id, set_up = await _the_command_while_the_setup_completes(engine, bootstrap, f02, monkeypatch, lambda session: user_service.set_user_admin(session, ADMIN_USERNAME, False))

    after = await _account(engine, user_id)
    version = next(row["session_version"] for row in set_up["users"] if row["id"] == user_id)
    afterwards = f"active {after.is_active}, an administrator {after.is_superuser}, session version {version} → {after.session_version}"
    assert outcome[0] is False and LAST_ADMIN_WORDS in str(outcome[1]), f"red until A-51: set up before it decided, the account was the only active administrator: user demote must refuse it as the last one; it answered {outcome!r}, the account afterwards {afterwards}"
    assert await _snapshot(engine) == set_up, "a refused demotion must change nothing: every account, token and setting as the setup left them"
    assert (after.is_active, after.is_superuser) == (True, True), "the account must stay active, an administrator"
    print_success("refused: the last active administrator; nothing changed")


# =============================================================================
# A50 — LOT A-50: THE RESTART SAYS WHY THE SETUP LINK IS GONE
# =============================================================================
# A-50: a restart while the initial administrator waits finds no live setup link, and a token of the variable already
# known re-arms nothing: ``_keep_pending_admin`` answers ``EXPIRED`` and logs one warning — «address changed» at the
# start that changes the address (A-33), «has expired» at any other, even for a link that did not run out but was
# revoked: cancelled (A-43: ``update_user_status(..., is_active=False)``, the Users tab's PATCH, or
# ``set_user_active(..., False)``, the CLI's ``user deactivate``), or revoked by an address changed at an earlier start.
# The cure (approved by the coordinator, 17/10): when the address did not change at this start, and the account's most
# recent setup link — the latest created — is revoked and was never consumed, the warning says the link was withdrawn;
# otherwise «has expired», as today. The action stays ``EXPIRED`` — the same ``user_id`` and ``username``, no
# ``link_token`` —, nothing is written, and the remedy is today's: ``./dev.py user setup-link``, with a new
# LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN when the configuration carries one. The log is English, for the developer: only a
# distinctive word is pinned — «withdrawn», «has expired», «address changed» —, never the sentence. The cancellations go
# through ``user_service``, which reads the clock: A50-001 and A50-002 are dated from it, as A43's; every other call
# takes its ``now``.

#: The distinctive words of the restart's warning, looked for in its message in lower case: the link withdrawn (A-50),
#: the link run out, the address changed at this very start (A-33). The withdrawn warning may name the change of
#: address among its causes, so «address changed» alone does not tell the two apart: «withdrawn» does.
SAYS_WITHDRAWN = "withdrawn"
SAYS_EXPIRED = "has expired"
SAYS_MOVED = "address changed"
#: When the restart after the change of address runs (A50-003): an hour after it, the link's 72 hours not over; or once
#: they are, the link revoked and run out at once — its revocation decides all the same.
LATER_RESTARTS = [
    pytest.param(HOUR, id="an-hour-later"),
    pytest.param(SETUP_TTL + HOUR, id="once-its-72-hours-are-over-too"),
]
#: Setup links that ran out, never revoked (A50-004): (the token the administrator is created with, or None for a
#: generated link; the token that re-arms it an hour later — revoking the first link —, or None). The restart's
#: configuration carries the last token given.
RUN_OUT_LINKS = [
    pytest.param(TOKEN_ONE, None, id="the-variables-token"),
    pytest.param(None, None, id="a-generated-link"),
    pytest.param(TOKEN_ONE, TOKEN_TWO, id="the-token-that-re-armed-it-its-first-link-revoked"),
]


def _said(event: dict[str, Any]) -> str:
    """The message of a log event, in lower case: where a distinctive word is looked for."""
    return str(event.get("event", "")).lower()


def _the_restarts_warning(events: list[dict[str, Any]], token: Optional[str]) -> dict[str, Any]:
    """The one warning of a restart that found no live setup link, its remedy as today: it names ``./dev.py user setup-link``, and ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` exactly when the configuration carries a token — a new one there re-arms."""
    warnings = _at_level(events, "warning")
    assert len(warnings) == 1, f"the restart must log one warning: {warnings}"
    warning = warnings[0]
    assert SETUP_LINK_COMMAND in repr(warning), f"the warning must still name {SETUP_LINK_COMMAND}: {warning}"
    if token is None:
        assert TOKEN_VARIABLE not in repr(warning), f"the configuration carries no token: the warning must name {SETUP_LINK_COMMAND} alone, never {TOKEN_VARIABLE}: {warning}"
    else:
        assert TOKEN_VARIABLE in repr(warning), f"the configuration carries a token: the warning must name {TOKEN_VARIABLE} too: {warning}"
    return warning


async def _cancelled_waiting_administrator(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, cancel: Change, moment: datetime, *, token: Optional[str]) -> tuple[int, str]:
    """The F02 administrator created by the bootstrap an hour before ``moment`` — with ``token`` from the configuration, or a generated link —, root beside it, then its setup cancelled by ``cancel``: the id of the waiting account and its link.

    Barriers: before, the account waits and its link is valid at ``moment``; after, the link is revoked and only
    revoked, and the account still waits — what A43-001 pins.
    """
    created = await _created(engine, bootstrap, f02, token=token, now=moment - HOUR)
    await _add_user(engine, ROOT_USERNAME, admin=True)
    link = token or created.link_token
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "barrier: the F02 administrator waits for its setup"
    assert await _status(engine, link, moment) == TokenStatus.VALID, "barrier: its setup link is valid"
    await cancel(engine, created.user_id, moment)
    assert _link_states(await _setup_rows(engine, created.user_id)) == [REVOKED_ONLY], f"barrier: {_named(cancel)} must revoke the link, and only revoke it (A43-001)"
    assert await _waiting(engine, bootstrap, created.user_id) == (True, True, created.user_id), "barrier: the account still waits for its setup"
    return created.user_id, link


# red until A-50
@pytest.mark.asyncio
async def test_a_restart_after_the_setup_was_cancelled_in_the_users_tab_says_the_link_was_withdrawn(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A50-001 — NEW, red until A-50 (today «has expired», for a link that did not run out): the waiting administrator, created by the bootstrap with TOKEN_ONE from the configuration, its setup cancelled in the Users tab — ``update_user_status(..., is_active=False)``, the PATCH, revokes its link (A43-001) —; a restart five minutes later with the same configuration, TOKEN_ONE known so re-arming nothing: ``EXPIRED``, the same account, no ``link_token``, nothing written; one warning, which says the link was withdrawn — never «has expired» —, its remedy as today: ``./dev.py user setup-link``, or a new ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN``. No token in the log."""
    print_section("A50-001: a restart after the cancellation through the PATCH, a token in the configuration")
    moment = utcnow()
    user_id, link = await _cancelled_waiting_administrator(engine, bootstrap, f02, _deactivate_by_update_user_status, moment, token=TOKEN_ONE)
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02, token=TOKEN_ONE), now=moment + AFTERWARDS, then_commit=True)

    assert (result.action, result.user_id, result.username, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, user_id, ADMIN_USERNAME, None), f"no live link, and a token already known: EXPIRED, for the waiting account, as today: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    warning = _the_restarts_warning(events, TOKEN_ONE)
    assert _holding(events, link) == [] and _holding(events, CANARY) == [], "no log event may hold the token"
    assert SAYS_WITHDRAWN in _said(warning), f"red until A-50: the link was cancelled, it did not run out: the warning must say it was withdrawn: {warning.get('event')!r}"
    assert [event for event in _logged(events) if SAYS_EXPIRED in _said(event)] == [], "a link withdrawn must not be said to have expired"
    print_success("EXPIRED; one warning: withdrawn, the remedy as today")


# red until A-50
@pytest.mark.asyncio
async def test_a_restart_after_user_deactivate_cancelled_a_generated_link_says_it_was_withdrawn(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType) -> None:
    """A50-002 — NEW, red until A-50 (today «has expired»): A50-001 the other way, with the other link — the CLI's ``user deactivate``, ``set_user_active(..., False)``, cancels a generated link, and the configuration carries no token —: a restart five minutes later with the same configuration is ``EXPIRED``, the same account, no ``link_token``, nothing written; one warning, which says the link was withdrawn — never «has expired» —, its remedy as today: ``./dev.py user setup-link`` alone, never ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN``. The link is not in the log."""
    print_section("A50-002: a restart after the cancellation by user deactivate, a generated link")
    moment = utcnow()
    user_id, link = await _cancelled_waiting_administrator(engine, bootstrap, f02, _deactivate_by_set_user_active, moment, token=None)
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02), now=moment + AFTERWARDS, then_commit=True)

    assert (result.action, result.user_id, result.username, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, user_id, ADMIN_USERNAME, None), f"no live link: EXPIRED, for the waiting account, as today: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    warning = _the_restarts_warning(events, None)
    assert _holding(events, link) == [], "no log event may hold the link"
    assert SAYS_WITHDRAWN in _said(warning), f"red until A-50: the link was cancelled, it did not run out: the warning must say it was withdrawn: {warning.get('event')!r}"
    assert [event for event in _logged(events) if SAYS_EXPIRED in _said(event)] == [], "a link withdrawn must not be said to have expired"
    print_success("EXPIRED; one warning: withdrawn, the command alone")


# red until A-50
@pytest.mark.asyncio
@pytest.mark.parametrize("delay", LATER_RESTARTS)
@pytest.mark.parametrize("token", LINK_ORIGINS)
async def test_a_restart_after_the_one_that_changed_the_address_says_the_link_was_withdrawn(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, token: Optional[str], delay: timedelta) -> None:
    """A50-003 — NEW, red until A-50 (today «has expired»): the waiting administrator created at NOW — with TOKEN_ONE from the configuration, or a generated link —; an hour later a start with a new LIBREFOLIO_ADMIN_EMAIL revokes the link (A33-001) and says so: ``EXPIRED``, one warning that the address changed — not «withdrawn», a later start's word —, its remedy as today. A later restart with the same variables — an hour later, or once the link's 72 hours are over too —: ``EXPIRED``, the same account, no ``link_token``, nothing written; one warning, which says the link was withdrawn — never «has expired» —, its remedy as today. No link in the log."""
    print_section(f"A50-003: a restart after the change of address, {'the variable token' if token else 'a generated link'}, {delay} later")
    created = await _created(engine, bootstrap, f02, token=token)
    link = token or created.link_token
    config = _config(f02, email=OTHER_EMAIL, token=token)
    moment = NOW + HOUR

    with _captured(bootstrap) as moving:
        moved = await _run(engine, bootstrap, config, now=moment)

    assert (moved.action, moved.link_token) == (bootstrap.BootstrapAction.EXPIRED, None), f"setup: the new address leaves no live link: {moved!r}"
    assert _link_states(await _setup_rows(engine, created.user_id)) == [REVOKED_ONLY], "barrier: the new address revokes the link, and only revokes it (A33-001)"
    assert await _accounts(engine) == {ADMIN_USERNAME: (created.user_id, OTHER_EMAIL, False, True)}, "barrier: the account at its new address, still inactive"
    said = _said(_the_restarts_warning(moving, token))
    assert SAYS_MOVED in said and SAYS_WITHDRAWN not in said, f"the start that changes the address must still say so, as today — not that the link was withdrawn: {said!r}"
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, config, now=moment + delay, then_commit=True)

    assert (result.action, result.user_id, result.username, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, created.user_id, ADMIN_USERNAME, None), f"no live link: EXPIRED, for the waiting account, as today: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    warning = _the_restarts_warning(events, token)
    assert _holding(moving, link) == [] and _holding(events, link) == [], "no log event may hold the link"
    assert SAYS_WITHDRAWN in _said(warning), f"red until A-50: the link was revoked by the address changed at an earlier start, it did not run out: the warning must say it was withdrawn: {warning.get('event')!r}"
    assert [event for event in _logged(events) if SAYS_EXPIRED in _said(event)] == [], "a link withdrawn must not be said to have expired"
    print_success("the start of the change: address changed; the starts after it: withdrawn")


# guard
@pytest.mark.asyncio
@pytest.mark.parametrize(("created_with", "rearmed_with"), RUN_OUT_LINKS)
async def test_a_restart_after_the_link_ran_out_still_says_it_has_expired(engine: AsyncEngine, bootstrap: ModuleType, f02: ModuleType, created_with: Optional[str], rearmed_with: Optional[str]) -> None:
    """A50-004 — GUARD, green today and after: a setup link that ran out, never revoked — the variable's token, a generated link, or the token that re-armed the waiting administrator an hour after its creation, its first link revoked by that re-arm —; a restart with the same configuration an hour after the link's 72 hours: ``EXPIRED``, the same account, no ``link_token``, nothing written; one warning, which still says the link has expired — never «withdrawn»: the most recent setup link decides, and an earlier one revoked does not —, its remedy as today. No link in the log."""
    print_section(f"A50-004: a restart after the link ran out, {'the variable token' if created_with else 'a generated link'}{', re-armed an hour later' if rearmed_with else ''}")
    created = await _created(engine, bootstrap, f02, token=created_with)
    issued_at = NOW
    if rearmed_with is not None:
        issued_at = NOW + HOUR
        rearmed = await _run(engine, bootstrap, _config(f02, token=rearmed_with), now=issued_at)
        assert rearmed.action == bootstrap.BootstrapAction.REARMED, f"setup: a token never seen re-arms the waiting administrator: {rearmed!r}"
    token = rearmed_with or created_with
    moment = issued_at + SETUP_TTL + HOUR
    states = _link_states(await _setup_rows(engine, created.user_id))
    assert states == [REVOKED_ONLY] * (len(states) - 1) + [(False, False, None)], f"barrier: the latest setup link neither revoked nor consumed, any earlier one revoked: {states}"
    assert await _live_setup_rows(engine, moment) == [], "barrier: no setup link is live at the restart: the latest ran out"
    before = await _snapshot(engine)

    with _captured(bootstrap) as events:
        result = await _run(engine, bootstrap, _config(f02, token=token), now=moment, then_commit=True)

    assert (result.action, result.user_id, result.username, result.link_token) == (bootstrap.BootstrapAction.EXPIRED, created.user_id, ADMIN_USERNAME, None), f"no live link: EXPIRED, for the waiting account: {result!r}"
    assert await _snapshot(engine) == before, "EXPIRED must write nothing"
    warning = _the_restarts_warning(events, token)
    assert SAYS_EXPIRED in _said(warning), f"a link that ran out, never revoked, must still be said to have expired: {warning.get('event')!r}"
    assert [event for event in _logged(events) if SAYS_WITHDRAWN in _said(event)] == [], "a link that ran out must not be said withdrawn: the most recent setup link decides, not an earlier one revoked"
    assert _holding(events, CANARY) == [] and (created.link_token is None or _holding(events, created.link_token) == []), "no log event may hold a link"
    print_success("EXPIRED; one warning: has expired, the remedy as today")

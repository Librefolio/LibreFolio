"""``registration_service`` and the accounts configuration: who may create an account, and how many (plan phase01Accounts §17 A5.1, lot A5a, contract points 2, 3 and 4, and the review of 15/10).

Release 1.3 replaces the registration switch with three modes and adds a user limit. Who may create an account depends
on a row (``registration_mode``), on a variable that overrides it (``LIBREFOLIO_REGISTRATION``), on invitations
(single-use ``account_tokens`` of purpose ``invite``) and on the limit (``LIBREFOLIO_MAX_USERS``). ``registration_service``
holds the whole rule, so that the API and the command line apply the same one. The contract pinned here:

2. The settings registry: ``registration_mode`` replaces ``enable_registration`` — ``value_type`` ``str``, the type of
   every text setting in ``schemas/settings.py`` and the one the 1.3 migration (``005_release_1_3_0_schema``, step 3)
   writes, so a new install and an upgraded one hold the same row —, default ``invite`` (lot A6d, decision 36), choices
   open, invite and disabled and nothing else; ``SETTINGS_REGISTRY.global_.REGISTRATION_MODE``; ``ENABLE_REGISTRATION``
   gone.
3. The variables, one accessor each in ``backend/app/config/accounts.py``, read at every call, each in ``.env.example``'s
   Accounts section as a commented line:
   - ``registration_mode_override()`` — ``LIBREFOLIO_REGISTRATION``, stripped and lower-cased; unset, empty or blank →
     ``None``; open, invite or disabled → that; anything else → ``ValueError`` naming the variable and the three values;
   - ``max_users()`` — ``LIBREFOLIO_MAX_USERS``; unset, empty or blank → ``None``, no limit; an integer ≥ 1 → that;
     anything else → ``ValueError``;
   - ``public_url()`` and ``billing_url()`` — ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BILLING_URL``, stripped and
     without their trailing ``/``, nothing else changed; unset, empty or blank → ``None``; not starting with ``http://``
     or ``https://`` → ``ValueError``; with user info in the authority, an ``@`` in it (X-R35) → ``ValueError`` naming
     the variable, whose message holds neither the user name nor the password.
4. ``registration_service``:
   - ``effective_registration_mode`` → ``RegistrationModeState(mode, locked)``: the variable when it is set, locked;
     otherwise the row, ``invite`` without one (A6d). An invalid variable closes — ``disabled``, locked —, and so does an invalid
     stored value — ``disabled``, not locked: the administrator fixes the row in Settings;
   - ``user_usage`` → ``UserUsage(used, max_users)``: active users plus live invitations (not consumed, not revoked, not
     expired). An invalid limit closes: ``max_users`` 0;
   - ``public_link(path)`` is ``LIBREFOLIO_PUBLIC_URL`` followed by the path, whose token travels in the fragment
     (``token_path`` writes ``#token=…``), and ``None`` without the variable or with an invalid one: the caller then
     shows the bare path. ``billing_link()`` is ``LIBREFOLIO_BILLING_URL``, ``None`` without it or with an invalid one;
   - an invalid setting is reported by ``_report_invalid(problem, consequence)``: one structlog error event,
     ``Invalid account configuration``, whose ``problem`` names the variable or the setting and whose ``consequence``
     says what the fallback does, once per process for each distinct pair (``functools.cache``). «registration stays
     closed until it is fixed» for the variable, the stored mode and the limit; «links show the bare path until it is
     fixed» for the public URL; «the billing link stays hidden until it is fixed» for the billing URL. An invalid URL
     closes nothing — the mode, the limit and the registrations are those of a valid one — and its log never says it does;
     a URL with user info is invalid like the others, and no record of its log holds the user name or the password
     (X-R35);
   - ``create_invite`` issues an invitation (the token service's ``IssuedToken``) unless registration is disabled
     (``REGISTRATION_DISABLED``) or the limit is reached, ``used >= max_users`` (``USER_LIMIT_REACHED``); a refusal
     writes nothing;
   - ``list_pending_invites`` lists the live invitations; ``revoke_invite`` revokes one, ``True``, and answers ``False``
     for anything that is not a live invitation;
   - ``register_user`` holds the whole rule. The first account is the administrator in every mode, whatever role an
     invitation grants; the mode does not apply to it, but a token given with it is checked and spent all the same: a
     valid invitation is consumed by it, one that is not valid refuses it (``INVITE_INVALID``, the instance still
     empty) — an invitation can exist before anyone registered, and its link must not open a second account. After the
     first account, ``disabled`` refuses even an invitation; ``invite`` wants a valid one (``INVITE_REQUIRED``,
     ``INVITE_INVALID``); ``open`` takes one or none, but a given one must be valid. An invitation gives its role and is
     consumed by the new account in the same transaction; its place was counted already, so a full limit does not stop
     it. Without one, the limit is checked after the insert, in the same transaction, so two racing registrations never
     exceed it, and a refusal rolls back. bcrypt runs off the event loop. A taken name or email is today's error, and
     leaves the invitation live.

Refusals are ``RegistrationError`` carrying its code (``.code``, or else its first argument). The helpers that call the
service commit after a refusal on purpose: whatever its caller does next, a refused call must have written nothing.

Every database is a private SQLite file under ``tmp_path`` built with ``create_all`` (``test_migration_005_release_1_3``
keeps that schema equal to the migrated one), opened as production opens its own: aiosqlite, NullPool — a session is a
connection —, and the PRAGMA listener of ``backend.app.db.session`` (foreign keys, WAL, busy_timeout). The accounts
variables are removed from this process's environment before each test and set through ``monkeypatch`` where a test is
about them. bcrypt runs at its lowest cost (``auth_service.BCRYPT_ROUNDS = 4``): real hashes that verify, a hundred
times cheaper. The cache of ``_report_invalid`` is emptied before and after every test, so "once per process" starts
over in each, in this process; the log is read with ``structlog.testing.capture_logs``, behind a barrier: a canary
logged through the service's own logger must reach the capture, or "nothing was logged" would prove nothing. No server,
no lane database, no clock wait: the race is held in step by a barrier, not by sleeps.

Red until the review of 15/10 lands, for the cases it changes: the registry says ``string``, ``public_link`` carries
the token in the query string, the one log line of every invalid setting reads «Invalid account configuration:
registration stays closed until it is fixed», whatever the setting, with no ``consequence`` field; and the first
registration of an empty instance is admitted before its token is looked at, so a valid invitation stays live and an
invalid one is ignored.

Lot A6d (decision 36) changes the default: a new install registers by invitation. ``GLOBAL_SETTINGS_DEFAULTS`` says
``invite``, and so does ``effective_registration_mode`` without a row and without the variable; the first account stays
creatable while the instance has none, in every mode, as the administrator. A case about something else than the
default sets the mode it needs on the row. Red until A6d: the default of the registry, the mode without a row or a
variable, and a second registration without an invitation on an instance without a row.

X-R35 (workstream E's security review «R13-SEC2»): an address whose authority holds user info would be handed out as it
is — the billing link of an administrator's pages, the invitation and reset links — and an error quoting it would write
the credentials into the operator's log. Red until X-R35 lands: ``public_url()`` and ``billing_url()`` take such an
address, and ``public_link()`` and ``billing_link()`` hand it out.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlsplit

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT
from backend.app.config.accounts import billing_url, max_users, public_url, registration_mode_override
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.schemas.settings import GLOBAL_SETTINGS_CONSTRAINTS, GLOBAL_SETTINGS_DEFAULTS, SETTINGS_REGISTRY, validate_global_setting_value
from backend.app.services.accounts import auth_service, registration_service
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, inspect_token, issue_token, revoke_tokens, token_path
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_utils import print_section, print_success

# The service under test, by the names of its contract (imported as a module, so the import block sorts the same before
# and after the module exists).
RegistrationError = registration_service.RegistrationError
RegistrationModeState = registration_service.RegistrationModeState
UserUsage = registration_service.UserUsage
create_invite = registration_service.create_invite
effective_registration_mode = registration_service.effective_registration_mode
list_pending_invites = registration_service.list_pending_invites
register_user = registration_service.register_user
revoke_invite = registration_service.revoke_invite
user_usage = registration_service.user_usage
public_link = registration_service.public_link
billing_link = registration_service.billing_link

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
MODES = ("open", "invite", "disabled")
MODE_KEY = "registration_mode"

REGISTRATION_VARIABLE = "LIBREFOLIO_REGISTRATION"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BILLING_URL_VARIABLE = "LIBREFOLIO_BILLING_URL"
ACCOUNTS_VARIABLES = (REGISTRATION_VARIABLE, MAX_USERS_VARIABLE, PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE)
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
SECTION_BAR = re.compile(r"# =+")

PASSWORD = "Registration-Pass-2026"
SEEDED_HASH = "$argon2id$seeded-account"  # a marker: the accounts seeded here never log in
NEVER_ISSUED = "never-issued-0123456789abcdefghijklmnopqrstuv"
INVALID_INVITES = ("unknown", "expired", "consumed", "revoked", "password_reset")
#: How long two racing registrations wait for each other at the hashing barrier: a deadline for a failure, never a pause.
BARRIER_SECONDS = 15.0
RACE_ROUNDS = 3

#: The one event an invalid account setting logs, and the consequences it may name (review of 15/10), word for word.
INVALID_CONFIGURATION = "Invalid account configuration"
REGISTRATION_STAYS_CLOSED = "registration stays closed until it is fixed"
LINKS_SHOW_THE_BARE_PATH = "links show the bare path until it is fixed"
BILLING_LINK_STAYS_HIDDEN = "the billing link stays hidden until it is fixed"
LOG_CANARY = "canary: the capture reaches the registration service's own logger"
#: A token in the alphabet issue_token uses (URL-safe base64), and the page each purpose of a link opens.
SAMPLE_TOKEN = "Zm9v_YmFy-0123456789abcdefghijklmnopqrstuv"
PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
#: X-R35: the user name and the password of the addresses with user info, distinctive enough that either one found in a
#: message or a log record can only be the value leaking.
USER_INFO_NAME = "alice"
USER_INFO_PASSWORD = "s3cr3t-pw"

Outcome = Union[User, RegistrationError]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def accounts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the accounts variables of the shell that started the run: each test sets the ones it is about."""
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at its lowest cost in this process: real hashes that verify, at a hundredth of the time."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def fresh_reports() -> Iterator[None]:
    """The cache of ``_report_invalid`` empty before and after each test: "once per process" starts over, and no test inherits what another reported."""
    registration_service._report_invalid.cache_clear()
    yield
    registration_service._report_invalid.cache_clear()


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own, disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'registration.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS — the scene
# =============================================================================


def _set_or_unset(monkeypatch: pytest.MonkeyPatch, name: str, value: Optional[str]) -> None:
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


async def _set_mode_row(engine: AsyncEngine, mode: str) -> None:
    """The ``registration_mode`` row says ``mode``: created when missing, as the startup seeding would."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, MODE_KEY)
        if row is None:
            row = GlobalSetting(key=MODE_KEY, value=mode, value_type="str", description="Who may create an account: open, invite or disabled", updated_at=utcnow())
        row.value = mode
        session.add(row)
        await session.commit()


async def _put_mode(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, mode: str, source: str) -> None:
    """Registration is ``mode``, said by the row (``source`` "row") or by the variable over a row that says otherwise ("env")."""
    if source == "row":
        await _set_mode_row(engine, mode)
        return
    await _set_mode_row(engine, "disabled" if mode == "open" else "open")
    monkeypatch.setenv(REGISTRATION_VARIABLE, mode)


async def _add_users(engine: AsyncEngine, *names: str, active: bool = True, admin: bool = False) -> dict[str, int]:
    """Accounts written as rows (``name@example.com``, a marker hash): no bcrypt, no service. Their ids, by name."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = {name: User(username=name, email=f"{name}@example.com", hashed_password=SEEDED_HASH, is_active=active, is_superuser=admin) for name in names}
        session.add_all(created.values())
        await session.commit()
    return {name: user.id for name, user in created.items()}


async def _accounts(engine: AsyncEngine) -> dict[str, tuple[int, bool, bool]]:
    """Every account in the database, read fresh: ``{username: (id, is_active, is_superuser)}``."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(User.username, User.id, User.is_active, User.is_superuser))).all()
    return {username: (user_id, bool(active), bool(admin)) for username, user_id, active, admin in rows}


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose = INVITE, **arguments: Any) -> IssuedToken:
    """A token issued by the token service directly, committed: the scene is set without the service under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _consume(engine: AsyncEngine, token: str, consumer: int, purpose: AccountTokenPurpose = INVITE) -> None:
    async with AsyncSession(engine) as session:
        assert await consume_token(session, token, purpose, consumed_by_user_id=consumer) is not None, "setup: the token must be consumed"
        await session.commit()


async def _revoke(engine: AsyncEngine, token_id: int) -> None:
    async with AsyncSession(engine) as session:
        assert await revoke_tokens(session, token_id=token_id) == 1, "setup: the token must be revoked"
        await session.commit()


async def _token(engine: AsyncEngine, token_id: int) -> AccountToken:
    """The token as a fresh session reads it from the database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await session.get(AccountToken, token_id)
    assert record is not None, f"token {token_id} is not in the database"
    return record


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = INVITE) -> TokenStatus:
    """What the token service says of ``token`` right now, in a session of its own."""
    async with AsyncSession(engine) as session:
        return (await inspect_token(session, token, purpose)).status


async def _token_count(engine: AsyncEngine) -> int:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(func.count()).select_from(AccountToken))).scalar_one()


async def _invalid_invite(engine: AsyncEngine, kind: str, owner: int) -> str:
    """A token that is not a valid invitation, of one ``kind``: never issued, expired, consumed, revoked, or a reset link."""
    if kind == "unknown":
        return NEVER_ISSUED
    if kind == "expired":
        return (await _issue(engine, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(days=1))).token
    if kind == "password_reset":
        return (await _issue(engine, PASSWORD_RESET, user_id=owner)).token
    issued = await _issue(engine)
    if kind == "consumed":
        await _consume(engine, issued.token, owner)
    else:
        await _revoke(engine, issued.record.id)
    return issued.token


# =============================================================================
# HELPERS — calling the service as its callers do
# =============================================================================


async def _register(engine: AsyncEngine, username: str, *, invite_token: Optional[str] = None, email: Optional[str] = None, now: Optional[datetime] = None) -> Outcome:
    """``register_user`` in a session of its own: the new account, or the refusal.

    The session is committed in both cases: a caller that commits after a refusal must find nothing of the refused
    registration to commit, so a refusal that did not roll back what it wrote shows here.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            user = await register_user(session, username=username, email=email or f"{username}@example.com", password=PASSWORD, invite_token=invite_token, now=now)
        except RegistrationError as refusal:
            await session.commit()
            return refusal
        await session.commit()
    return user


async def _create_invite(engine: AsyncEngine, **arguments: Any) -> Union[IssuedToken, RegistrationError]:
    """``create_invite`` in a session of its own, committed afterwards — after a refusal too."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            issued = await create_invite(session, **arguments)
        except RegistrationError as refusal:
            await session.commit()
            return refusal
        await session.commit()
    return issued


async def _revoke_invite(engine: AsyncEngine, invite_id: int) -> bool:
    async with AsyncSession(engine) as session:
        revoked = await revoke_invite(session, invite_id)
        await session.commit()
    return revoked


def _code(refusal: BaseException) -> str:
    """The code a ``RegistrationError`` carries: ``.code``, or else its first argument."""
    code = getattr(refusal, "code", None)
    if code is None and refusal.args:
        code = refusal.args[0]
    return str(code)


def _assert_refused(outcome: object, code: str, what: str) -> None:
    assert isinstance(outcome, RegistrationError), f"{what}: expected a RegistrationError {code}, got {outcome!r}"
    assert _code(outcome) == code, f"{what}: expected the code {code}, got {_code(outcome)!r} ({outcome!r})"


def _assert_registered(outcome: object, what: str) -> User:
    assert isinstance(outcome, User), f"{what}: expected the new account, got {outcome!r}"
    assert outcome.id is not None, f"{what}: the account returned has no id"
    return outcome


# =============================================================================
# HELPERS — reading the log
# =============================================================================


@contextlib.contextmanager
def _captured() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through the service's own logger must be among them.

    Without it, a capture that misses the service's events would pass every "nothing was logged" for a service that
    logs nothing — or worse, for one that logs the wrong thing.
    """
    with capture_logs() as events:
        registration_service.logger.debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the events of the registration service's logger do not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _errors(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The error-level events among those captured: what an operator's log shows as a problem."""
    return [event for event in events if event.get("log_level") in ("error", "critical")]


def _reported(events: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    """``(event, consequence)`` of each error-level event, in order."""
    return [(event.get("event"), event.get("consequence")) for event in _errors(events)]


def _user_info_in(text: str) -> list[str]:
    """The parts of the user info of X-R35 that ``text`` holds, in any case: anything but ``[]`` is the value leaking."""
    return [part for part in (USER_INFO_NAME, USER_INFO_PASSWORD) if part.casefold() in text.casefold()]


# =============================================================================
# 2. THE SETTINGS REGISTRY
# =============================================================================


def test_registration_mode_replaces_enable_registration_in_the_registry() -> None:
    """Contract 2: ``SETTINGS_REGISTRY.global_.REGISTRATION_MODE`` is the global key ``registration_mode``, a ``str`` defaulting to ``invite`` (lot A6d, decision 36); ``enable_registration`` and ``ENABLE_REGISTRATION`` are gone.

    ``str`` (review of 15/10): the documented type of every text setting in ``schemas/settings.py`` — "str", "int",
    "bool", "json" —, and the one the 1.3 migration writes: a new install, seeded from the registry, and an upgraded one
    hold the same row. ``invite`` (A6d): a new install registers by invitation; its first account is always creatable.
    """
    print_section("Contract 2: registration_mode in the registry")
    spec = SETTINGS_REGISTRY.global_.REGISTRATION_MODE

    assert (spec.key, spec.location, spec.value_type) == (MODE_KEY, "global", "str"), f"REGISTRATION_MODE must be the global str key {MODE_KEY!r}: {spec}"
    assert GLOBAL_SETTINGS_DEFAULTS[MODE_KEY]["type"] == "str", f"a new install seeds the row from the defaults, as value_type 'str': {GLOBAL_SETTINGS_DEFAULTS[MODE_KEY]}"
    assert spec in SETTINGS_REGISTRY.global_.all()
    assert GLOBAL_SETTINGS_DEFAULTS[MODE_KEY]["value"] == "invite", f"new installs register by invitation (decision 36), the first account being always creatable: the default must be 'invite', got {GLOBAL_SETTINGS_DEFAULTS[MODE_KEY]}"
    assert "enable_registration" not in GLOBAL_SETTINGS_DEFAULTS, "enable_registration must leave the defaults: a new install would seed both rows"
    assert not hasattr(SETTINGS_REGISTRY.global_, "ENABLE_REGISTRATION"), "ENABLE_REGISTRATION must leave the registry"
    print_success("registration_mode: global, str, invite; enable_registration gone")


def test_registration_mode_accepts_its_three_choices_and_nothing_else() -> None:
    """Contract 2: ``SettingConstraint(choices=("open", "invite", "disabled"))``; a save of any other value is refused."""
    print_section("Contract 2: the three choices")

    assert GLOBAL_SETTINGS_CONSTRAINTS[MODE_KEY].choices == MODES
    for mode in MODES:
        assert validate_global_setting_value(MODE_KEY, mode, "str") == mode
    for refused in ("closed", "true", "invite-only", ""):
        with pytest.raises(ValueError):
            validate_global_setting_value(MODE_KEY, refused, "str")
    print_success("open, invite, disabled accepted; closed, true, invite-only and empty refused")


# =============================================================================
# 3. THE VARIABLES
# =============================================================================


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty"),
        pytest.param(" \t ", None, id="blank"),
        pytest.param("open", "open", id="open"),
        pytest.param("invite", "invite", id="invite"),
        pytest.param("disabled", "disabled", id="disabled"),
        pytest.param("  Invite\n", "invite", id="stripped-and-lower-cased"),
        pytest.param("DISABLED", "disabled", id="upper-case"),
    ],
)
def test_registration_mode_override_reads_the_variable(monkeypatch: pytest.MonkeyPatch, raw: Optional[str], expected: Optional[str]) -> None:
    """Contract 3: ``LIBREFOLIO_REGISTRATION`` stripped and lower-cased; unset, empty or blank is no override."""
    _set_or_unset(monkeypatch, REGISTRATION_VARIABLE, raw)

    assert registration_mode_override() == expected, f"{REGISTRATION_VARIABLE}={raw!r} must give {expected!r}"


@pytest.mark.parametrize("raw", ["closed", "true", "invited", "open invite"])
def test_registration_mode_override_refuses_any_other_value_naming_the_variable_and_the_modes(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """Contract 3: any other value is a ``ValueError`` whose message names the variable and the three values it takes."""
    monkeypatch.setenv(REGISTRATION_VARIABLE, raw)

    with pytest.raises(ValueError) as raised:
        registration_mode_override()
    message = str(raised.value)
    assert REGISTRATION_VARIABLE in message and all(mode in message for mode in MODES), f"the error must name {REGISTRATION_VARIABLE} and open, invite, disabled: {message!r}"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty"),
        pytest.param("   ", None, id="blank"),
        pytest.param("1", 1, id="one"),
        pytest.param("25", 25, id="twenty-five"),
    ],
)
def test_max_users_reads_the_variable(monkeypatch: pytest.MonkeyPatch, raw: Optional[str], expected: Optional[int]) -> None:
    """Contract 3: ``LIBREFOLIO_MAX_USERS``: no limit when unset, empty or blank; an integer of at least 1 otherwise."""
    _set_or_unset(monkeypatch, MAX_USERS_VARIABLE, raw)

    value = max_users()
    assert value == expected and type(value) is type(expected), f"{MAX_USERS_VARIABLE}={raw!r} must give {expected!r}, got {value!r}"


@pytest.mark.parametrize("raw", ["0", "-2", "abc", "2.5", "ten"])
def test_max_users_refuses_anything_but_a_positive_integer(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """Contract 3: zero, a negative number, a decimal or a word is a ``ValueError``, never a limit."""
    monkeypatch.setenv(MAX_USERS_VARIABLE, raw)

    with pytest.raises(ValueError):
        max_users()


URL_ACCESSORS = [pytest.param(public_url, PUBLIC_URL_VARIABLE, id="public_url"), pytest.param(billing_url, BILLING_URL_VARIABLE, id="billing_url")]


@pytest.mark.parametrize(("accessor", "variable"), URL_ACCESSORS)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty"),
        pytest.param("  \n", None, id="blank"),
        pytest.param("https://folio.example.com", "https://folio.example.com", id="https"),
        pytest.param("https://folio.example.com/", "https://folio.example.com", id="trailing-slash"),
        pytest.param("  http://192.168.1.20:6040/ \n", "http://192.168.1.20:6040", id="stripped-http-with-port"),
        pytest.param("https://example.com/Folio/App/", "https://example.com/Folio/App", id="path-and-case-kept"),
    ],
)
def test_a_url_variable_is_stripped_of_spaces_and_of_its_trailing_slash(monkeypatch: pytest.MonkeyPatch, accessor: Callable[[], Optional[str]], variable: str, raw: Optional[str], expected: Optional[str]) -> None:
    """Contract 3: ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BILLING_URL``: no URL when unset, empty or blank; otherwise the URL stripped and without its trailing ``/``, nothing else changed."""
    _set_or_unset(monkeypatch, variable, raw)

    assert accessor() == expected, f"{variable}={raw!r} must give {expected!r}"


@pytest.mark.parametrize(("accessor", "variable"), URL_ACCESSORS)
@pytest.mark.parametrize("raw", ["folio.example.com", "ftp://folio.example.com", "//folio.example.com", "javascript:alert(1)", "mailto:admin@example.com"])
def test_a_url_variable_must_start_with_http_or_https(monkeypatch: pytest.MonkeyPatch, accessor: Callable[[], Optional[str]], variable: str, raw: str) -> None:
    """Contract 3: a URL that does not start with ``http://`` or ``https://`` is a ``ValueError``: it becomes a link the instance hands out."""
    monkeypatch.setenv(variable, raw)

    with pytest.raises(ValueError):
        accessor()


@pytest.mark.parametrize(("accessor", "variable"), URL_ACCESSORS)
@pytest.mark.parametrize("raw", [pytest.param("https://alice:s3cr3t-pw@folio.example.com", id="user-name-and-password")])
def test_a_url_variable_refuses_user_info_and_never_quotes_it(monkeypatch: pytest.MonkeyPatch, accessor: Callable[[], Optional[str]], variable: str, raw: str) -> None:
    """Contract 3 (X-R35): a URL whose authority holds user info is a ``ValueError`` naming the variable, its message holding neither the user name nor the password: the URL becomes a link the instance hands out, and the error is logged.

    Red today: both accessors give it back, credentials included.
    """
    monkeypatch.setenv(variable, raw)

    with pytest.raises(ValueError) as raised:
        accessor()
    message = str(raised.value)
    assert variable in message and _user_info_in(message) == [], f"the error must name {variable} without quoting its user info, neither {USER_INFO_NAME!r} nor {USER_INFO_PASSWORD!r}: {message!r}"


def _env_example_section(title: str) -> list[str]:
    """The lines of ``.env.example`` under the section ``title``: from its header (``# ====`` / ``# Title`` / ``# ====``) to the next one."""
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    headers = {lines[index + 1].removeprefix("#").strip(): index for index in range(len(lines) - 2) if SECTION_BAR.fullmatch(lines[index]) and SECTION_BAR.fullmatch(lines[index + 2])}
    assert title in headers, f"{ENV_EXAMPLE.name} has no section {title!r}: {sorted(headers)}"
    start = headers[title]
    end = min((index for index in headers.values() if index > start), default=len(lines))
    return lines[start + 3 : end]


def test_each_variable_is_a_commented_line_of_the_accounts_section_of_env_example() -> None:
    """Contract 3: the four variables are listed in ``.env.example``'s Accounts section, commented: an install that copies the file sets none of them."""
    print_section("Contract 3: .env.example, Accounts")
    section = _env_example_section("Accounts")

    missing = [name for name in ACCOUNTS_VARIABLES if not any(re.fullmatch(rf"#\s*{name}=.*", line) for line in section)]
    assert not missing, f"the Accounts section of {ENV_EXAMPLE.name} must list {missing} as commented lines ('# NAME=default'): {section}"
    print_success("LIBREFOLIO_REGISTRATION, LIBREFOLIO_MAX_USERS, LIBREFOLIO_PUBLIC_URL, LIBREFOLIO_BILLING_URL: commented, under Accounts")


# =============================================================================
# 4a. THE EFFECTIVE MODE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("row", "variable", "mode", "locked"),
    [
        pytest.param(None, None, "invite", False, id="no-row-no-variable-is-invite"),
        pytest.param("open", None, "open", False, id="row-open"),
        pytest.param("invite", None, "invite", False, id="row-invite"),
        pytest.param("disabled", None, "disabled", False, id="row-disabled"),
        pytest.param("open", "invite", "invite", True, id="variable-invite-over-row-open"),
        pytest.param("open", "disabled", "disabled", True, id="variable-disabled-over-row-open"),
        pytest.param("disabled", "open", "open", True, id="variable-open-over-row-disabled"),
        pytest.param(None, " INVITE ", "invite", True, id="variable-stripped-and-lower-cased"),
        pytest.param("invite", "  ", "invite", False, id="blank-variable-is-no-variable"),
        pytest.param("open", "sometimes", "disabled", True, id="invalid-variable-closes"),
        pytest.param("open", "true", "disabled", True, id="a-boolean-is-no-mode-and-closes"),
    ],
)
async def test_effective_registration_mode(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, row: Optional[str], variable: Optional[str], mode: str, locked: bool) -> None:
    """Contract 4: the variable when set, locked; otherwise the row, ``invite`` without one (A6d, decision 36), not locked; an invalid variable closes, locked."""
    if row is not None:
        await _set_mode_row(engine, row)
    _set_or_unset(monkeypatch, REGISTRATION_VARIABLE, variable)

    async with AsyncSession(engine) as session:
        state = await effective_registration_mode(session)

    assert isinstance(state, RegistrationModeState), f"effective_registration_mode must answer a RegistrationModeState: {state!r}"
    assert (state.mode, state.locked) == (mode, locked), f"row {row!r}, {REGISTRATION_VARIABLE}={variable!r}: expected mode {mode!r}, locked {locked}; got {state!r}"


# =============================================================================
# 4b. THE USAGE
# =============================================================================


async def _usage_scene(engine: AsyncEngine) -> dict[str, tuple[IssuedToken, AccountTokenPurpose]]:
    """Active alice and bob, inactive carol; invitations live (two, one granting admin), consumed, revoked and expired; alice's live reset link."""
    users = await _add_users(engine, "alice", "bob")
    await _add_users(engine, "carol", active=False)
    scene = {
        "live": (await _issue(engine, created_by_user_id=users["alice"]), INVITE),
        "live admin": (await _issue(engine, grants_admin=True, email="boss@example.com"), INVITE),
        "consumed": (await _issue(engine), INVITE),
        "revoked": (await _issue(engine), INVITE),
        "expired": (await _issue(engine, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(days=1)), INVITE),
        "reset link": (await _issue(engine, PASSWORD_RESET, user_id=users["alice"]), PASSWORD_RESET),
    }
    await _consume(engine, scene["consumed"][0].token, users["bob"])
    await _revoke(engine, scene["revoked"][0].record.id)
    return scene


@pytest.mark.asyncio
@pytest.mark.parametrize(("variable", "limit"), [pytest.param(None, None, id="no-limit"), pytest.param("10", 10, id="limit-10")])
async def test_user_usage_counts_active_users_and_live_invitations(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, variable: Optional[str], limit: Optional[int]) -> None:
    """Contract 4: ``used`` is 2 active users + 2 live invitations = 4 — not the inactive user, not the consumed, revoked or expired invitations, not a reset link; ``max_users`` is the variable's.

    Barrier first: every token of the scene is in the state its name says, or the count would prove nothing.
    """
    print_section(f"Contract 4: user_usage, limit {limit}")
    scene = await _usage_scene(engine)
    statuses = {name: await _status(engine, issued.token, purpose) for name, (issued, purpose) in scene.items()}
    assert statuses == {
        "live": TokenStatus.VALID,
        "live admin": TokenStatus.VALID,
        "consumed": TokenStatus.CONSUMED,
        "revoked": TokenStatus.REVOKED,
        "expired": TokenStatus.EXPIRED,
        "reset link": TokenStatus.VALID,
    }, f"barrier: the scene is not what it claims: {statuses}"
    _set_or_unset(monkeypatch, MAX_USERS_VARIABLE, variable)

    async with AsyncSession(engine) as session:
        usage = await user_usage(session)

    assert isinstance(usage, UserUsage), f"user_usage must answer a UserUsage: {usage!r}"
    assert (usage.used, usage.max_users) == (4, limit), f"expected used 4 (alice, bob, two live invitations), max_users {limit}; got {usage!r}"
    print_success(f"used 4, max_users {limit}")


@pytest.mark.asyncio
async def test_an_invalid_limit_closes_the_usage_at_zero(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4: an invalid ``LIBREFOLIO_MAX_USERS`` is a limit of 0, not an error and not "no limit": nobody else gets in until it is fixed."""
    await _add_users(engine, "alice")
    monkeypatch.setenv(MAX_USERS_VARIABLE, "plenty")

    async with AsyncSession(engine) as session:
        usage = await user_usage(session)

    assert (usage.used, usage.max_users) == (1, 0), f"{MAX_USERS_VARIABLE}='plenty' must close: used 1, max_users 0; got {usage!r}"


# =============================================================================
# 4c. THE LINKS: THE PUBLIC URL AND THE BILLING URL
# =============================================================================


@pytest.mark.parametrize("purpose", [INVITE, PASSWORD_RESET], ids=["invite", "password_reset"])
@pytest.mark.parametrize(
    ("configured", "base", "prefix"),
    [
        pytest.param("https://folio.example.com/", "https://folio.example.com", "", id="host-with-trailing-slash"),
        pytest.param("  https://example.com/folio \n", "https://example.com/folio", "/folio", id="sub-path-with-spaces"),
    ],
)
def test_public_link_is_the_public_url_then_the_page_with_the_token_in_its_fragment(monkeypatch: pytest.MonkeyPatch, purpose: AccountTokenPurpose, configured: str, base: str, prefix: str) -> None:
    """Contract 4 (review of 15/10): ``public_link(token_path(purpose, token))`` is ``LIBREFOLIO_PUBLIC_URL`` followed by the page of the purpose, the token in the fragment (``#token=…``) and the query string empty; a valid URL reports nothing.

    A browser never sends the fragment: whoever opens the link an administrator hands out, the token reaches neither the
    instance's access log nor a proxy's on the way.
    """
    print_section(f"Contract 4: public_link, {purpose.value}, {configured.strip()}")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, configured)

    with _captured() as events:
        link = public_link(token_path(purpose, SAMPLE_TOKEN))

    parts = urlsplit(link or "")
    assert link is not None and link.startswith(base + PAGES[purpose]), f"{PUBLIC_URL_VARIABLE}={configured!r}: the link must be the public URL followed by the page {PAGES[purpose]}, got {link!r}"
    assert (parts.scheme, parts.path, parts.query) == ("https", prefix + PAGES[purpose], ""), f"the token must not travel in the query string, which the server and every proxy log: {link!r}"
    assert parse_qs(parts.fragment) == {"token": [SAMPLE_TOKEN]}, f"the token must travel in the fragment, as its 'token' field: {link!r}"
    assert _errors(events) == [], f"a valid {PUBLIC_URL_VARIABLE} is no problem to report: {_errors(events)}"
    print_success(f"{base}{PAGES[purpose]}#token=…")


def test_a_missing_url_or_a_valid_billing_url_is_no_problem_to_report(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4: without ``LIBREFOLIO_PUBLIC_URL`` there is no link — the caller shows the bare path —, without ``LIBREFOLIO_BILLING_URL`` no billing link, and a valid billing URL is the link, stripped of its spaces and of its trailing ``/``. None of this is a problem: nothing is logged."""
    print_section("Contract 4: no URL, or a valid one, reports nothing")

    with _captured() as events:
        missing = (public_link(token_path(INVITE, SAMPLE_TOKEN)), billing_link())
        monkeypatch.setenv(BILLING_URL_VARIABLE, " https://billing.example.com/acme/ ")
        billing = billing_link()

    assert missing == (None, None), f"without the variables there is no link: {missing}"
    assert billing == "https://billing.example.com/acme", f"a valid {BILLING_URL_VARIABLE} is the billing link: {billing!r}"
    assert _errors(events) == [], f"a missing or a valid URL is no problem to report: {_errors(events)}"
    print_success("no link without the variables, the billing link with it, nothing reported")


# =============================================================================
# 4d. AN INVALID SETTING: ITS FALLBACK, AND ONE ERROR THAT SAYS WHAT IT COSTS
# =============================================================================


async def _read_mode(engine: AsyncEngine) -> tuple[str, bool]:
    """The effective mode as ``(mode, locked)``, read in a session of its own."""
    async with AsyncSession(engine) as session:
        state = await effective_registration_mode(session)
    return state.mode, state.locked


async def _read_limit(engine: AsyncEngine) -> Optional[int]:
    """``max_users`` of the usage, read in a session of its own."""
    async with AsyncSession(engine) as session:
        return (await user_usage(session)).max_users


async def _read_public_link(_engine: AsyncEngine) -> Optional[str]:
    """The link an administrator's page shows for an invitation."""
    return public_link(token_path(INVITE, SAMPLE_TOKEN))


async def _read_billing_link(_engine: AsyncEngine) -> Optional[str]:
    """The billing link an administrator's page shows."""
    return billing_link()


@dataclass(frozen=True)
class _InvalidSetting:
    """An account setting made invalid: what the problem must name, the value, how the service reads it, what it falls back to, and what the log must say it costs."""

    name: str
    value: str
    stored: bool
    read: Callable[[AsyncEngine], Awaitable[object]]
    fallback: object
    consequence: str

    async def put(self, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
        """Make it invalid: the row written as a damaged database holds it (no validation on the way), or the variable set."""
        if self.stored:
            await _set_mode_row(engine, self.value)
        else:
            monkeypatch.setenv(self.name, self.value)


INVALID_REGISTRATION = _InvalidSetting(REGISTRATION_VARIABLE, "sometimes", False, _read_mode, ("disabled", True), REGISTRATION_STAYS_CLOSED)
INVALID_STORED_MODE = _InvalidSetting(MODE_KEY, "sometimes", True, _read_mode, ("disabled", False), REGISTRATION_STAYS_CLOSED)
INVALID_LIMIT = _InvalidSetting(MAX_USERS_VARIABLE, "plenty", False, _read_limit, 0, REGISTRATION_STAYS_CLOSED)
INVALID_PUBLIC_URL = _InvalidSetting(PUBLIC_URL_VARIABLE, "folio.example.com", False, _read_public_link, None, LINKS_SHOW_THE_BARE_PATH)
INVALID_BILLING_URL = _InvalidSetting(BILLING_URL_VARIABLE, "ftp://billing.example.com/acme", False, _read_billing_link, None, BILLING_LINK_STAYS_HIDDEN)
INVALID_SETTINGS = [
    pytest.param(INVALID_REGISTRATION, id="LIBREFOLIO_REGISTRATION"),
    pytest.param(INVALID_STORED_MODE, id="stored-registration_mode"),
    pytest.param(INVALID_LIMIT, id="LIBREFOLIO_MAX_USERS"),
    pytest.param(INVALID_PUBLIC_URL, id="LIBREFOLIO_PUBLIC_URL"),
    pytest.param(INVALID_BILLING_URL, id="LIBREFOLIO_BILLING_URL"),
]
INVALID_URLS = [pytest.param(INVALID_PUBLIC_URL, id="LIBREFOLIO_PUBLIC_URL"), pytest.param(INVALID_BILLING_URL, id="LIBREFOLIO_BILLING_URL")]
#: X-R35: a URL with user info is invalid too — each read as an administrator's page reads it.
USER_INFO_PUBLIC_URL = _InvalidSetting(PUBLIC_URL_VARIABLE, "https://alice:s3cr3t-pw@folio.example.com/", False, _read_public_link, None, LINKS_SHOW_THE_BARE_PATH)
USER_INFO_BILLING_URL = _InvalidSetting(BILLING_URL_VARIABLE, "https://alice:s3cr3t-pw@billing.example.com/acme", False, _read_billing_link, None, BILLING_LINK_STAYS_HIDDEN)
USER_INFO_URLS = [pytest.param(USER_INFO_PUBLIC_URL, id="LIBREFOLIO_PUBLIC_URL"), pytest.param(USER_INFO_BILLING_URL, id="LIBREFOLIO_BILLING_URL")]


def test_report_invalid_logs_one_error_per_distinct_problem_and_consequence() -> None:
    """Contract 4 (review of 15/10): ``_report_invalid(problem, consequence)`` logs one error event, ``Invalid account configuration``, with both as fields — once per process for each distinct pair (``functools.cache``).

    The same pair again logs nothing; another problem, or the same problem with another consequence, logs once more.
    """
    print_section("Contract 4: _report_invalid, once per distinct pair")

    with _captured() as events:
        registration_service._report_invalid("problem one", REGISTRATION_STAYS_CLOSED)
        registration_service._report_invalid("problem one", REGISTRATION_STAYS_CLOSED)
        registration_service._report_invalid("problem two", REGISTRATION_STAYS_CLOSED)
        registration_service._report_invalid("problem one", LINKS_SHOW_THE_BARE_PATH)
        registration_service._report_invalid("problem two", REGISTRATION_STAYS_CLOSED)

    logged = [(event.get("event"), event.get("problem"), event.get("consequence")) for event in _errors(events)]
    assert logged == [
        (INVALID_CONFIGURATION, "problem one", REGISTRATION_STAYS_CLOSED),
        (INVALID_CONFIGURATION, "problem two", REGISTRATION_STAYS_CLOSED),
        (INVALID_CONFIGURATION, "problem one", LINKS_SHOW_THE_BARE_PATH),
    ], f"one error per distinct (problem, consequence), in order, each {INVALID_CONFIGURATION!r} with both fields: {_errors(events)}"
    print_success("three distinct pairs, three errors; the repeated pairs logged nothing")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", INVALID_SETTINGS)
async def test_an_invalid_setting_falls_back_and_logs_what_it_costs(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, invalid: _InvalidSetting) -> None:
    """Contract 4 (review of 15/10): an invalid setting falls back — the mode closed (locked when the variable is the culprit, not when the row is), a limit of 0, no public link, no billing link — and logs exactly one error, ``Invalid account configuration``, whose ``problem`` names the setting and whose ``consequence`` is what the fallback costs.

    Registration stays closed for the variable, the stored mode and the limit; an invalid URL only loses its link. An
    operator reading «registration stays closed» for a mistyped billing URL would look for the fault in the wrong place.
    """
    print_section(f"Contract 4: invalid {invalid.name}")
    await invalid.put(engine, monkeypatch)

    with _captured() as events:
        answer = await invalid.read(engine)

    errors = _errors(events)
    assert answer == invalid.fallback, f"{invalid.name}={invalid.value!r}: the service must fall back to {invalid.fallback!r}, got {answer!r}"
    assert _reported(events) == [(INVALID_CONFIGURATION, invalid.consequence)], f"an invalid {invalid.name} must log exactly one error, {INVALID_CONFIGURATION!r}, whose consequence is {invalid.consequence!r}; got {errors}"
    assert invalid.name in str(errors[0].get("problem")), f"the problem must name {invalid.name}: {errors[0]}"
    print_success(f"{invalid.name}: {invalid.fallback!r}, «{invalid.consequence}»")


@pytest.mark.asyncio
async def test_an_invalid_setting_read_again_is_not_reported_again(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (review of 15/10): every reading of an invalid setting falls back, but each problem is logged once per process: three readings of an invalid mode and three of an invalid limit close six times and log two errors, one naming each variable, both «registration stays closed until it is fixed»."""
    print_section("Contract 4: once per process")
    await INVALID_REGISTRATION.put(engine, monkeypatch)
    await INVALID_LIMIT.put(engine, monkeypatch)

    with _captured() as events:
        modes = [await _read_mode(engine) for _ in range(3)]
        limits = [await _read_limit(engine) for _ in range(3)]

    errors = _errors(events)
    assert (modes, limits) == ([("disabled", True)] * 3, [0] * 3), f"every reading must fall back, closed: modes {modes}, limits {limits}"
    assert _reported(events) == [(INVALID_CONFIGURATION, REGISTRATION_STAYS_CLOSED)] * 2, f"three readings of each of two invalid settings must log two errors, one each: {errors}"
    named = [name in str(error.get("problem")) for name, error in zip((REGISTRATION_VARIABLE, MAX_USERS_VARIABLE), errors, strict=True)]
    assert named == [True, True], f"one error names each variable, in the order they were read: {errors}"
    print_success("six readings, closed each time; two errors")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", INVALID_URLS)
async def test_an_invalid_url_closes_nothing_and_its_log_never_says_it_does(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, invalid: _InvalidSetting) -> None:
    """Contract 4 (review of 15/10): with an invalid URL variable, read as an administrator's page reads it, registration works as with a valid one — the mode open and not locked, no limit, an open registration a regular account — and nothing logged says registration is closed: the one error says what the URL costs, its link."""
    print_section(f"Contract 4: an invalid {invalid.name} closes nothing")
    await _add_users(engine, "alice")
    await _set_mode_row(engine, "open")
    await invalid.put(engine, monkeypatch)

    with _captured() as events:
        link = await invalid.read(engine)
        mode = await _read_mode(engine)
        limit = await _read_limit(engine)
        outcome = await _register(engine, "walkin")

    user = _assert_registered(outcome, f"open mode with an invalid {invalid.name}")
    assert (link, mode, limit, user.is_superuser) == (None, ("open", False), None, False), f"an invalid {invalid.name} costs its link and nothing else: link {link!r}, mode {mode!r}, limit {limit!r}, administrator {user.is_superuser}"
    claims = [event for event in events if REGISTRATION_STAYS_CLOSED in repr(event)]
    assert claims == [], f"an invalid {invalid.name} closes nothing, and the log must not say it does — an operator would look for the fault in the wrong place: {claims}"
    assert _reported(events) == [(INVALID_CONFIGURATION, invalid.consequence)], f"the one error must say what an invalid {invalid.name} costs, «{invalid.consequence}»: {_errors(events)}"
    print_success(f"open, no limit, a regular account registered; «{invalid.consequence}»")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", USER_INFO_URLS)
async def test_a_url_with_user_info_is_no_link_and_no_log_record_holds_it(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, invalid: _InvalidSetting) -> None:
    """Contract 4 (X-R35): a URL variable with user info is invalid like the others: no link at every reading, and one error for the process, ``Invalid account configuration``, naming the variable and what it costs.

    The invitation and reset links show the bare path, the billing link stays hidden. No captured record holds the
    user name or the password; the one error, and the canary of the capture, are the presence barriers that give that
    absence its meaning. Red today: both links carry the credentials, and nothing is logged.
    """
    print_section(f"Contract 4 (X-R35): {invalid.name} with user info")
    await invalid.put(engine, monkeypatch)

    with _captured() as events:
        answers = [await invalid.read(engine) for _ in range(2)]

    errors = _errors(events)
    assert answers == [invalid.fallback] * 2, f"{invalid.name} with user info: every reading must fall back to {invalid.fallback!r}, got {answers}"
    assert _reported(events) == [(INVALID_CONFIGURATION, invalid.consequence)], f"two readings of {invalid.name} with user info must log exactly one error, {INVALID_CONFIGURATION!r}, whose consequence is {invalid.consequence!r}; got {errors}"
    assert invalid.name in str(errors[0].get("problem")), f"the problem must name {invalid.name}: {errors[0]}"
    leaking = [event for event in events if _user_info_in(repr(event))]
    assert leaking == [], f"no log record may hold the user name {USER_INFO_NAME!r} or the password {USER_INFO_PASSWORD!r}: {leaking}"
    print_success(f"{invalid.name} with user info: no link twice, «{invalid.consequence}», no credential logged")


# =============================================================================
# 4e. INVITATIONS: CREATE, LIST, REVOKE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["open", "invite"])
@pytest.mark.parametrize(("grants_admin", "email"), [pytest.param(False, None, id="user-invite"), pytest.param(True, "newcomer@example.com", id="admin-invite-with-email")])
async def test_create_invite_issues_a_live_invitation(engine: AsyncEngine, mode: str, grants_admin: bool, email: Optional[str]) -> None:
    """Contract 4: in ``open`` and ``invite`` mode, without a limit, ``create_invite`` issues an invitation of nobody yet, with its role, e-mail and author, living 7 days from ``now``."""
    print_section(f"Contract 4: create_invite in {mode} mode, grants_admin={grants_admin}")
    admin = (await _add_users(engine, "admin", admin=True))["admin"]
    await _set_mode_row(engine, mode)
    moment = utcnow()

    outcome = await _create_invite(engine, created_by_user_id=admin, grants_admin=grants_admin, email=email, now=moment)

    assert isinstance(outcome, IssuedToken), f"create_invite must issue the invitation, an IssuedToken: got {outcome!r}"
    stored = await _token(engine, outcome.record.id)
    assert (stored.purpose, stored.user_id, stored.grants_admin, stored.email, stored.created_by_user_id) == (INVITE, None, grants_admin, email, admin), f"stored invitation: {stored!r}"
    assert ensure_utc(stored.expires_at) == moment + DEFAULT_TTL[INVITE], f"an invitation lives {DEFAULT_TTL[INVITE]} from now: expires {stored.expires_at}"
    assert await _status(engine, outcome.token) == TokenStatus.VALID
    print_success("a live invitation, committed with its role, e-mail, author and expiry")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["row", "env"])
async def test_create_invite_is_refused_while_registration_is_disabled(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    """Contract 4 (D-A3): ``disabled`` — by the row or by the variable — refuses invitations too, ``REGISTRATION_DISABLED``; nothing is written."""
    admin = (await _add_users(engine, "admin", admin=True))["admin"]
    await _put_mode(engine, monkeypatch, "disabled", source)

    outcome = await _create_invite(engine, created_by_user_id=admin)

    _assert_refused(outcome, "REGISTRATION_DISABLED", f"create_invite with registration disabled by the {source}")
    assert await _token_count(engine) == 0, "a refused invitation must write no token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "pending"),
    [
        pytest.param("2", 0, id="two-users-limit-2"),
        pytest.param("3", 1, id="two-users-one-invitation-limit-3"),
        pytest.param("not-a-number", 0, id="invalid-limit-closes"),
    ],
)
async def test_create_invite_is_refused_once_the_limit_is_reached(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, limit: str, pending: int) -> None:
    """Contract 4: ``used >= max_users`` refuses, ``USER_LIMIT_REACHED`` — a live invitation holds a place as an account does, and an invalid limit is 0; nothing is written."""
    users = await _add_users(engine, "admin", "bob")
    for _ in range(pending):
        await _issue(engine)
    monkeypatch.setenv(MAX_USERS_VARIABLE, limit)
    before = await _token_count(engine)

    outcome = await _create_invite(engine, created_by_user_id=users["admin"])

    _assert_refused(outcome, "USER_LIMIT_REACHED", f"create_invite with 2 users, {pending} live invitation(s), {MAX_USERS_VARIABLE}={limit!r}")
    assert await _token_count(engine) == before, "a refused invitation must write no token"


@pytest.mark.asyncio
async def test_create_invite_counts_only_active_users_and_live_invitations(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4: limit 3, two active users, an inactive one, and consumed, revoked and expired invitations: one place left, so one invitation is issued and the next one is refused — the new invitation holds its place."""
    print_section("Contract 4: what create_invite counts")
    users = await _add_users(engine, "admin", "bob")
    await _add_users(engine, "carol", active=False)
    await _invalid_invite(engine, "consumed", users["bob"])
    await _invalid_invite(engine, "revoked", users["bob"])
    await _invalid_invite(engine, "expired", users["bob"])
    monkeypatch.setenv(MAX_USERS_VARIABLE, "3")

    first = await _create_invite(engine, created_by_user_id=users["admin"])
    second = await _create_invite(engine, created_by_user_id=users["admin"])

    assert isinstance(first, IssuedToken), f"one place is left (2 active users of 3; dead invitations and inactive users hold none): got {first!r}"
    _assert_refused(second, "USER_LIMIT_REACHED", "a second invitation once the first took the last place")
    print_success("the last place taken by the first invitation, the second refused")


@pytest.mark.asyncio
async def test_list_pending_invites_lists_the_live_invitations_only(engine: AsyncEngine) -> None:
    """Contract 4: the live invitations, with their role, e-mail and author; not the consumed, revoked or expired ones — expired at ``expires_at`` exactly, as the token service says —, not a reset link. At a given ``now``, and by the clock."""
    print_section("Contract 4: list_pending_invites")
    owner = (await _add_users(engine, "alice"))["alice"]
    moment = utcnow()
    live = await _issue(engine, created_by_user_id=owner, now=moment - timedelta(hours=1))
    live_admin = await _issue(engine, grants_admin=True, email="boss@example.com", now=moment - timedelta(hours=2))
    await _invalid_invite(engine, "consumed", owner)
    await _invalid_invite(engine, "revoked", owner)
    await _invalid_invite(engine, "expired", owner)
    await _issue(engine, now=moment - DEFAULT_TTL[INVITE])  # expires at ``moment`` exactly
    await _issue(engine, PASSWORD_RESET, user_id=owner)

    async with AsyncSession(engine) as session:
        at_moment = await list_pending_invites(session, now=moment)
        by_clock = await list_pending_invites(session)

    expected = {live.record.id: (False, None, owner), live_admin.record.id: (True, "boss@example.com", None)}
    assert {item.id: (item.grants_admin, item.email, item.created_by_user_id) for item in at_moment} == expected, f"pending at {moment}: {at_moment}"
    assert {item.id for item in by_clock} == set(expected), f"pending by the clock: {by_clock}"
    print_success("two live invitations, nothing else")


@pytest.mark.asyncio
async def test_revoke_invite_revokes_a_live_invitation_once(engine: AsyncEngine) -> None:
    """Contract 4: ``revoke_invite`` on a live invitation answers ``True`` and the invitation is revoked, out of the pending list; a second call answers ``False``."""
    issued = await _issue(engine)

    first = await _revoke_invite(engine, issued.record.id)
    second = await _revoke_invite(engine, issued.record.id)

    assert (first, second) == (True, False), f"revoking a live invitation: True, then False; got {(first, second)}"
    assert await _status(engine, issued.token) == TokenStatus.REVOKED
    async with AsyncSession(engine) as session:
        assert issued.record.id not in {item.id for item in await list_pending_invites(session)}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["unknown", "consumed", "expired", "password_reset"])
async def test_revoke_invite_answers_false_for_anything_but_a_live_invitation(engine: AsyncEngine, kind: str) -> None:
    """Contract 4: an unknown id, a consumed or an expired invitation — none is live — and a reset link — not an invitation — give ``False`` and stay as they were.

    The API answers 404 for these: an administrator revoking invitations must not revoke somebody's reset link by its id.
    """
    owner = (await _add_users(engine, "alice"))["alice"]
    token = await _invalid_invite(engine, kind, owner) if kind != "unknown" else None
    purpose = PASSWORD_RESET if kind == "password_reset" else INVITE
    async with AsyncSession(engine) as session:
        found = (await inspect_token(session, token, purpose)).record if token else None
    target = found.id if found is not None else 987654
    before = await _token(engine, target) if found is not None else None

    revoked = await _revoke_invite(engine, target)

    assert revoked is False, f"revoke_invite on the {kind} token must answer False, got {revoked!r}"
    if before is not None:
        after = await _token(engine, target)
        assert (after.revoked_at, after.consumed_at) == (before.revoked_at, before.consumed_at), f"the {kind} token must stay as it was: {before!r} → {after!r}"


# =============================================================================
# 4f. REGISTER_USER: WHO MAY REGISTER
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["row", "env"])
@pytest.mark.parametrize("mode", MODES)
async def test_the_first_account_is_the_administrator_in_every_mode(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, mode: str, source: str) -> None:
    """Contract 4: with no account at all the first registration needs no invitation and makes the administrator, whatever the mode and whoever sets it — as today."""
    await _put_mode(engine, monkeypatch, mode, source)

    user = _assert_registered(await _register(engine, "founder"), f"the first account, registration {mode} by the {source}")

    assert await _accounts(engine) == {"founder": (user.id, True, True)}, "the first account must be an active administrator"


@pytest.mark.asyncio
async def test_an_inactive_account_is_still_an_account_so_the_next_one_is_no_administrator(engine: AsyncEngine) -> None:
    """Contract 4: "no account" means no row at all, as today (``count_users``): beside a deactivated administrator the next registration makes a regular user, never a second administrator. ``open`` mode, set on the row: since A6d an instance without the row is ``invite``."""
    await _add_users(engine, "dormant", active=False, admin=True)
    await _set_mode_row(engine, "open")

    user = _assert_registered(await _register(engine, "newcomer"), "a registration beside an inactive account, open mode")

    assert user.is_superuser is False, "an instance with an account, even inactive, has had its first user: the newcomer must not become an administrator"


@pytest.mark.asyncio
async def test_without_a_row_the_first_account_registers_and_the_next_one_needs_an_invitation(engine: AsyncEngine) -> None:
    """Lot A6d, C2 (decision 36): no ``registration_mode`` row and no variable — the default, ``invite`` —: the first account registers without an invitation, as the administrator; the next registration without one is ``INVITE_REQUIRED`` and creates nothing.

    Barrier first: the instance has no account and no row, so the default — and only the default — decides.
    """
    print_section("Contract A6d: at the default, the first account registers and the next one needs an invitation")
    async with AsyncSession(engine) as session:
        stored_mode = await session.get(GlobalSetting, MODE_KEY)
    accounts = await _accounts(engine)
    assert (accounts, stored_mode) == ({}, None), f"setup: an instance with no account and no {MODE_KEY} row, got {accounts} and {stored_mode!r}"

    founder = _assert_registered(await _register(engine, "founder"), "the first account, at the default, without an invitation")
    walkin = await _register(engine, "walkin")

    _assert_refused(walkin, "INVITE_REQUIRED", "a second registration without an invitation, at the default (new installs register by invitation)")
    assert await _accounts(engine) == {"founder": (founder.id, True, True)}, "the first account must be the only one, an active administrator: the refused registration must leave nothing"
    print_success("the first account an administrator; the next one INVITE_REQUIRED, nothing written")


# The first account and the invitation it comes with (review of 15/10, from the docs review). An invitation can exist on
# an instance that has no account yet — ``dev.py user invite`` before anyone registered —, and its link must not open
# two accounts: given with the first registration, a token is checked and spent like any other.

#: The invitations that are not valid on an instance without accounts, and the status the token service gives each.
INVALID_ON_AN_EMPTY_INSTANCE = {"unknown": TokenStatus.UNKNOWN, "expired": TokenStatus.EXPIRED, "consumed": TokenStatus.CONSUMED, "revoked": TokenStatus.REVOKED}


async def _invalid_invite_on_an_empty_instance(engine: AsyncEngine, kind: str) -> str:
    """An invitation that is not valid, written without any account: never issued, expired, used by an account deleted since, or revoked."""
    if kind == "unknown":
        return NEVER_ISSUED
    if kind == "expired":
        return (await _issue(engine, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(days=1))).token
    issued = await _issue(engine)
    async with AsyncSession(engine) as session:
        if kind == "consumed":
            # The account it opened was deleted since: ON DELETE SET NULL left consumed_by_user_id empty, the invitation used.
            assert await consume_token(session, issued.token, INVITE, consumed_by_user_id=None) is not None, "setup: the invitation must be consumed"
        else:
            assert await revoke_tokens(session, token_id=issued.record.id) == 1, "setup: the invitation must be revoked"
        await session.commit()
    return issued.token


@pytest.mark.asyncio
@pytest.mark.parametrize("grants_admin", [pytest.param(False, id="user-invitation"), pytest.param(True, id="admin-invitation")])
async def test_the_first_account_spends_the_invitation_it_registers_with(engine: AsyncEngine, grants_admin: bool) -> None:
    """Contract 4 (review of 15/10): on an empty instance a valid invitation given with the registration is spent like any other — consumed by the new account, which is the administrator whatever role the invitation grants —, so its link opens no second account: offered again, ``INVITE_INVALID``.

    The invitation's state is read right after the first registration, before the second one tries the link.
    """
    print_section(f"Contract 4: the first account spends its invitation ({'admin' if grants_admin else 'user'} role)")
    issued = await _issue(engine, grants_admin=grants_admin)
    assert await _accounts(engine) == {}, "setup: the instance has no account"

    user = _assert_registered(await _register(engine, "founder", invite_token=issued.token), "the first account, with a valid invitation")
    stored = await _token(engine, issued.record.id)
    again = await _register(engine, "second", invite_token=issued.token)

    assert user.is_superuser is True, "the first account of an empty instance is its administrator, whatever the invitation grants"
    assert (stored.consumed_by_user_id, stored.consumed_at is not None, stored.revoked_at) == (user.id, True, None), f"the invitation must be consumed by the first account, {user.id}: consumed_by_user_id {stored.consumed_by_user_id}, consumed_at {stored.consumed_at}, revoked_at {stored.revoked_at}"
    _assert_refused(again, "INVITE_INVALID", "the first account's invitation, offered again")
    assert set(await _accounts(engine)) == {"founder"}, "the spent invitation must open no second account"
    print_success("administrator; the invitation consumed by it; refused the second time")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(INVALID_ON_AN_EMPTY_INSTANCE))
async def test_the_first_account_with_an_invitation_that_is_not_valid_is_refused(engine: AsyncEngine, kind: str) -> None:
    """Contract 4 (review of 15/10): on an empty instance an invitation that is not valid — never issued, expired, used, revoked — refuses the registration, ``INVITE_INVALID``, and the instance stays empty: a token given is always checked, the first account included."""
    print_section(f"Contract 4: the first account with an invitation that is {kind}")
    token = await _invalid_invite_on_an_empty_instance(engine, kind)
    precondition = (await _accounts(engine), await _status(engine, token))
    assert precondition == ({}, INVALID_ON_AN_EMPTY_INSTANCE[kind]), f"setup: an empty instance and an invitation that is {kind}, got {precondition}"

    outcome = await _register(engine, "founder", invite_token=token)

    _assert_refused(outcome, "INVITE_INVALID", f"the first account, with an invitation that is {kind}")
    assert await _accounts(engine) == {}, "a refused first registration must leave the instance empty"
    print_success(f"an invitation that is {kind}: INVITE_INVALID, the instance still empty")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["row", "env"])
async def test_the_first_account_spends_its_invitation_even_while_registration_is_disabled(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    """Contract 4 (review of 15/10): the mode does not apply to the first account — ``disabled``, by the row or by the variable, still lets it in, as the administrator —, but the invitation it comes with is spent all the same: consumed by it."""
    print_section(f"Contract 4: the first account, registration disabled by the {source}, spends its invitation")
    await _put_mode(engine, monkeypatch, "disabled", source)
    issued = await _issue(engine)

    user = _assert_registered(await _register(engine, "founder", invite_token=issued.token), f"the first account, registration disabled by the {source}, with a valid invitation")
    stored = await _token(engine, issued.record.id)

    assert await _accounts(engine) == {"founder": (user.id, True, True)}, "the first account must be an active administrator, whatever the mode"
    assert (stored.consumed_by_user_id, stored.consumed_at is not None) == (user.id, True), f"the invitation must be consumed by the first account, {user.id}: consumed_by_user_id {stored.consumed_by_user_id}, consumed_at {stored.consumed_at}"
    assert await _status(engine, issued.token) == TokenStatus.CONSUMED
    print_success("administrator; the invitation consumed by it")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
async def test_the_first_account_without_a_token_leaves_a_pending_invitation_alone(engine: AsyncEngine, mode: str) -> None:
    """Contract 4 (review of 15/10) — GUARD: without a token the first account registers as today, the administrator in every mode, and an invitation already issued for somebody else stays live: only the token a registration comes with is spent."""
    print_section(f"Contract 4: the first account without a token, {mode} mode, beside a pending invitation")
    await _set_mode_row(engine, mode)
    pending = await _issue(engine)

    user = _assert_registered(await _register(engine, "founder"), f"the first account, {mode} mode, without a token")

    assert await _accounts(engine) == {"founder": (user.id, True, True)}, "the first account must be an active administrator"
    assert await _status(engine, pending.token) == TokenStatus.VALID, "an invitation the registration did not come with must stay live"
    print_success("administrator; the pending invitation still valid")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["row", "env"])
@pytest.mark.parametrize("with_invite", [pytest.param(False, id="no-invitation"), pytest.param(True, id="valid-invitation")])
async def test_disabled_refuses_every_registration_after_the_first_even_with_an_invitation(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, source: str, with_invite: bool) -> None:
    """Contract 4 (D-A3): ``disabled`` refuses, ``REGISTRATION_DISABLED``, with or without a valid invitation; no account is created and the invitation stays live."""
    await _add_users(engine, "alice")
    issued = await _issue(engine, grants_admin=True)
    await _put_mode(engine, monkeypatch, "disabled", source)

    outcome = await _register(engine, "newcomer", invite_token=issued.token if with_invite else None)

    _assert_refused(outcome, "REGISTRATION_DISABLED", f"registration disabled by the {source}, {'with' if with_invite else 'without'} an invitation")
    assert set(await _accounts(engine)) == {"alice"}
    assert await _status(engine, issued.token) == TokenStatus.VALID, "a refused registration must not consume the invitation"


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["row", "env"])
async def test_invite_mode_refuses_a_registration_without_an_invitation(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    """Contract 4: ``invite`` mode without an invitation: ``INVITE_REQUIRED``, no account."""
    await _add_users(engine, "alice")
    await _put_mode(engine, monkeypatch, "invite", source)

    outcome = await _register(engine, "walkin")

    _assert_refused(outcome, "INVITE_REQUIRED", f"invite mode by the {source}, no invitation")
    assert set(await _accounts(engine)) == {"alice"}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["open", "invite"])
@pytest.mark.parametrize("kind", INVALID_INVITES)
async def test_an_invalid_invitation_is_refused_in_open_and_invite_mode(engine: AsyncEngine, mode: str, kind: str) -> None:
    """Contract 4: an invitation never issued, expired, consumed, revoked, or a reset link offered as one: ``INVITE_INVALID`` — in ``open`` mode too, never silently ignored; no account; a reset link stays usable."""
    owner = (await _add_users(engine, "alice"))["alice"]
    await _set_mode_row(engine, mode)
    token = await _invalid_invite(engine, kind, owner)

    outcome = await _register(engine, "newcomer", invite_token=token)

    _assert_refused(outcome, "INVITE_INVALID", f"{mode} mode, {kind} invitation")
    assert set(await _accounts(engine)) == {"alice"}
    if kind == "password_reset":
        assert await _status(engine, token, PASSWORD_RESET) == TokenStatus.VALID, "a reset link offered as an invitation must stay a usable reset link"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["open", "invite"])
@pytest.mark.parametrize("grants_admin", [pytest.param(False, id="user-invitation"), pytest.param(True, id="admin-invitation")])
async def test_a_valid_invitation_gives_its_role_in_open_and_invite_mode(engine: AsyncEngine, mode: str, grants_admin: bool) -> None:
    """Contract 4: a valid invitation registers an active account with the invitation's role, in ``open`` and ``invite`` mode."""
    await _add_users(engine, "alice")
    await _set_mode_row(engine, mode)
    issued = await _issue(engine, grants_admin=grants_admin)

    user = _assert_registered(await _register(engine, "invited", invite_token=issued.token), f"{mode} mode, a valid invitation granting admin={grants_admin}")

    assert (await _accounts(engine))["invited"] == (user.id, True, grants_admin), f"the account must take the invitation's role, admin={grants_admin}"


@pytest.mark.asyncio
async def test_open_mode_registers_a_regular_user_without_an_invitation(engine: AsyncEngine) -> None:
    """Contract 4: ``open``, set on the row — since A6d an instance without the row is ``invite`` —, registers anybody as a regular, active user, with a bcrypt hash of the password."""
    await _add_users(engine, "alice")
    await _set_mode_row(engine, "open")

    user = _assert_registered(await _register(engine, "walkin"), "open mode, no invitation")

    assert (await _accounts(engine))["walkin"] == (user.id, True, False)
    async with AsyncSession(engine) as session:
        stored = (await session.execute(select(User.hashed_password).where(User.id == user.id))).scalar_one()
    assert stored != PASSWORD and bcrypt.checkpw(PASSWORD.encode(), stored.encode()), "the password must be stored as a bcrypt hash that verifies"


@pytest.mark.asyncio
async def test_the_invitation_is_consumed_by_the_new_account_and_never_again(engine: AsyncEngine) -> None:
    """Contract 4: the invitation used is consumed — ``consumed_by_user_id`` the new account, ``consumed_at`` the registration's moment —; offered again it is ``INVITE_INVALID``."""
    print_section("Contract 4: the invitation is consumed by its account")
    owner = (await _add_users(engine, "alice"))["alice"]
    await _set_mode_row(engine, "invite")
    issued = await _issue(engine, created_by_user_id=owner)
    started = utcnow()

    user = _assert_registered(await _register(engine, "invited", invite_token=issued.token, now=started), "invite mode, a valid invitation")
    finished = utcnow()
    again = await _register(engine, "latecomer", invite_token=issued.token)

    stored = await _token(engine, issued.record.id)
    assert stored.consumed_by_user_id == user.id, f"the invitation must name the account it opened: consumed_by_user_id {stored.consumed_by_user_id}, account {user.id}"
    assert stored.consumed_at is not None and started <= ensure_utc(stored.consumed_at) <= finished, f"consumed at the registration: {stored.consumed_at}, registration between {started} and {finished}"
    assert stored.revoked_at is None
    _assert_refused(again, "INVITE_INVALID", "the same invitation, a second time")
    assert set(await _accounts(engine)) == {"alice", "invited"}
    print_success("consumed by the new account; refused the second time")


@pytest.mark.asyncio
@pytest.mark.parametrize("taken", ["username", "email"])
async def test_a_taken_username_or_email_is_refused_and_leaves_the_invitation_live(engine: AsyncEngine, taken: str) -> None:
    """Contract 4: a name or e-mail already registered is today's error, naming the field; the invitation offered with it is not consumed — the consumption and the account share one transaction."""
    await _add_users(engine, "alice")
    await _set_mode_row(engine, "invite")
    issued = await _issue(engine)
    username = "alice" if taken == "username" else "newcomer"
    email = "alice@example.com" if taken == "email" else "newcomer@example.com"

    failure: Optional[Exception] = None
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            await register_user(session, username=username, email=email, password=PASSWORD, invite_token=issued.token)
        except Exception as error:  # today's error, whatever its class: the API turns it into its 400
            failure = error
            await session.rollback()

    assert failure is not None, f"a taken {taken} must be refused"
    assert taken in f"{failure} {getattr(failure, 'code', '')}".lower(), f"the error must name the {taken}, as today's 'Username already taken' / 'Email already registered': {failure!r}"
    assert set(await _accounts(engine)) == {"alice"}
    assert await _status(engine, issued.token) == TokenStatus.VALID, "a registration refused for a taken name or e-mail must leave its invitation live"


@pytest.mark.asyncio
async def test_an_invitation_with_an_email_does_not_bind_the_registration_to_it(engine: AsyncEngine) -> None:
    """Decision D-A16, rejected (plan §15.1): the e-mail of an invitation is a suggestion; the account takes the e-mail it registers with."""
    await _add_users(engine, "alice")
    await _set_mode_row(engine, "invite")
    issued = await _issue(engine, email="invited@example.com")

    user = _assert_registered(await _register(engine, "elsewhere", email="elsewhere@example.com", invite_token=issued.token), "an invitation for another e-mail")

    assert user.email == "elsewhere@example.com"


# =============================================================================
# 4g. REGISTER_USER: THE LIMIT
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["open", "invite"])
async def test_an_invitation_takes_the_place_it_holds_even_when_the_limit_is_full(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """Contract 4: limit 2, one account and one live invitation — full. The invitation was counted when it was issued, so its registration goes through; in ``open`` mode a registration without one is refused, ``USER_LIMIT_REACHED``."""
    print_section(f"Contract 4: a full limit and an invitation, {mode} mode")
    await _add_users(engine, "alice")
    await _set_mode_row(engine, mode)
    issued = await _issue(engine)
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")
    async with AsyncSession(engine) as session:
        usage = await user_usage(session)
    assert (usage.used, usage.max_users) == (2, 2), f"barrier: the limit must be full, or the invitation going through would prove nothing: {usage!r}"

    if mode == "open":
        _assert_refused(await _register(engine, "walkin"), "USER_LIMIT_REACHED", "open mode, a full limit, no invitation")
    user = _assert_registered(await _register(engine, "invited", invite_token=issued.token), "a full limit, the invitation holding its place")

    assert set(await _accounts(engine)) == {"alice", "invited"} and user.username == "invited"
    print_success("the invitation used its place; nobody else got in")


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [pytest.param("1", id="limit-reached"), pytest.param("not-a-number", id="invalid-limit-closes")])
async def test_an_open_registration_over_the_limit_is_refused_and_leaves_no_account(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, limit: str) -> None:
    """Contract 4: ``open`` (set on the row), no invitation, the limit reached (or invalid, so 0): ``USER_LIMIT_REACHED``, and the account inserted to count is rolled back — even though the caller commits after the refusal."""
    await _add_users(engine, "alice")
    await _set_mode_row(engine, "open")
    monkeypatch.setenv(MAX_USERS_VARIABLE, limit)

    outcome = await _register(engine, "overflow")

    _assert_refused(outcome, "USER_LIMIT_REACHED", f"open mode, {MAX_USERS_VARIABLE}={limit!r}, one account")
    assert set(await _accounts(engine)) == {"alice"}, "a refused registration must leave no account behind"


@pytest.mark.asyncio
async def test_an_open_registration_under_the_limit_is_accepted_and_inactive_accounts_hold_no_place(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4: ``open`` (set on the row), limit 2, one active and one inactive account: one place left — the registration goes through, the next one is refused."""
    await _add_users(engine, "alice")
    await _add_users(engine, "carol", active=False)
    await _set_mode_row(engine, "open")
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")

    _assert_registered(await _register(engine, "fits"), "limit 2, one active account")
    _assert_refused(await _register(engine, "overflow"), "USER_LIMIT_REACHED", "limit 2, now two active accounts")

    assert set(await _accounts(engine)) == {"alice", "carol", "fits"}


@pytest.mark.asyncio
@pytest.mark.parametrize("free", [0, 1, 2], ids=["no-place-left", "one-place-left", "two-places-left"])
async def test_two_registrations_racing_for_the_last_places_never_exceed_the_limit(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, free: int) -> None:
    """Contract 4: two open registrations at once, each in its own session — its own connection — on the same file: exactly ``min(free, 2)`` get in, the other is ``USER_LIMIT_REACHED``, and the database holds exactly the winners.

    The two are held in step where nothing has been written yet: ``bcrypt.hashpw`` waits at a barrier until both are
    hashing. A limit checked before the insert would then let both through; the contract checks it after the insert, in
    the transaction, where the first writer holds SQLite's write lock and the second waits for its commit. The barrier's
    deadline only ends a failure (bcrypt on the event loop, or registrations serialised in the process before hashing,
    which no other worker would honour). Three rounds each, the limit raised to the accounts present plus ``free``; the
    mode ``open``, set on the row (since A6d an instance without the row is ``invite``).
    """
    print_section(f"Contract 4: the race, {free} place(s) left")
    await _add_users(engine, "alice", "bob")
    await _set_mode_row(engine, "open")
    barrier = threading.Barrier(2, timeout=BARRIER_SECONDS)
    real_hashpw = bcrypt.hashpw

    def hashpw_in_step(password: bytes, salt: bytes) -> bytes:
        barrier.wait()
        return real_hashpw(password, salt)

    monkeypatch.setattr(bcrypt, "hashpw", hashpw_in_step)
    for race in range(RACE_ROUNDS):
        before = await _accounts(engine)
        monkeypatch.setenv(MAX_USERS_VARIABLE, str(len(before) + free))

        outcomes = await asyncio.gather(_register(engine, f"racer{race}a"), _register(engine, f"racer{race}b"), return_exceptions=True)

        crashed = [outcome for outcome in outcomes if isinstance(outcome, BaseException) and not isinstance(outcome, RegistrationError)]
        assert not crashed, f"race {race}: a registration failed instead of answering: {crashed!r} (a BrokenBarrierError means the two never hashed at the same time: bcrypt on the event loop, or registrations serialised in-process)"
        winners = [outcome.username for outcome in outcomes if isinstance(outcome, User)]
        refusals = [_code(outcome) for outcome in outcomes if isinstance(outcome, RegistrationError)]
        assert len(winners) == min(free, 2), f"race {race}: {free} place(s) left, {len(winners)} registration(s) got in: {outcomes!r}"
        assert refusals == ["USER_LIMIT_REACHED"] * (2 - len(winners)), f"race {race}: the registration left out must be USER_LIMIT_REACHED: {refusals}"
        assert set(await _accounts(engine)) == set(before) | set(winners), f"race {race}: the database must hold exactly the winners"
    print_success(f"{RACE_ROUNDS} races, {min(free, 2)} winner(s) each, never over the limit")


# =============================================================================
# 4h. REGISTER_USER: BCRYPT OFF THE EVENT LOOP
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["open", "invite"])
async def test_register_user_hashes_the_password_off_the_event_loop(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """Contract 4: the password is hashed in a worker thread, never on the event loop's — which would serve no other request for the whole hash.

    The spy is bcrypt's own ``hashpw``, the call every hashing path ends in, whatever name the service imports.
    """
    await _add_users(engine, "alice")
    await _set_mode_row(engine, mode)
    invitation = (await _issue(engine)).token if mode == "invite" else None
    threads: list[int] = []
    real_hashpw = bcrypt.hashpw

    def spying_hashpw(password: bytes, salt: bytes) -> bytes:
        threads.append(threading.get_ident())
        return real_hashpw(password, salt)

    monkeypatch.setattr(bcrypt, "hashpw", spying_hashpw)
    loop_thread = threading.get_ident()

    _assert_registered(await _register(engine, "offloop", invite_token=invitation), f"{mode} mode")

    assert threads, "barrier: bcrypt.hashpw was never called, so where it ran says nothing"
    assert loop_thread not in threads, f"bcrypt.hashpw ran on the event loop's thread ({loop_thread}): the call belongs in await asyncio.to_thread(...)"

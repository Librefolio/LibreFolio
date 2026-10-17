"""A-21a, rules 1 and 2: no new username with an @, no address that is another account's username — the command line, F02 and registration's service (release 1.3, workstream A, lot A-21a; workstream E's review, point c).

Until A-21a a username is any 3 to 50 characters, ``@`` included — ``AuthRegisterRequest``, ``UpdateProfileRequest``,
``LIBREFOLIO_ADMIN_USERNAME`` and ``./dev.py user create`` check the length alone —, and the sign-in looks what is typed
up as a username OR an address (``user_service.get_user_by_username_or_email``). So account A can be named
``bob@example.com`` while account B has that address, and the sign-in typed ``bob@example.com`` finds A: SQLite answers
that lookup with a MULTI-INDEX OR, the username's index first (workstream E's review: MEDIUM, 8/10). A-21a closes it
with three rules. The first two are pinned here where they do not go through HTTP; over HTTP (registration, the
profile) in ``test_api/test_username_rules_api.py``; the lookup, rule 3, in ``test_username_lookup.py``.

1. No ``@`` in a NEW username. ``scripts/user_cli.py`` ``cmd_create_user`` (``./dev.py user create``, an administrator
   or ``--role user``) refuses one: a falsy answer, a line starting with ❌, nothing written. ``LIBREFOLIO_ADMIN_USERNAME``
   with an ``@`` is an ``AdminBootstrapConfigError`` whose ``variable`` is ``LIBREFOLIO_ADMIN_USERNAME`` and whose message
   names that variable and says what is wrong: it shows the ``@``. Its ``code`` is not pinned — ``ADMIN_USERNAME_INVALID``
   again or a code of its own is the implementer's call; today's message for that code speaks of a length only, which
   would not be clear. Nothing else of the character set changes (GUARDS): spaces, accents, ``.``, ``_``, ``-`` and ``+``
   are taken as today. Legacy usernames with an ``@`` are left as they are: nothing renames them, and the command line
   still reaches such an account by its exact name (GUARD).
2. No address equal to an existing username, A–Z case aside (the fold of SQLite's ``lower()``, decision P18). Only a
   legacy username can hold an ``@``, so each scene has one, written as a row. ``register_user`` refuses such an
   address, open or with a valid invitation, with ``RegistrationError`` ``EMAIL_TAKEN_CODE`` and ``EMAIL_TAKEN_MESSAGE``
   — the answer to an address already registered, which the registration card and the profile already translate: one
   decision, two constants — and writes nothing, so the invitation stays live. ``cmd_set_email`` (``./dev.py user
   set-email``) refuses it: falsy, ❌, nothing written. ``cmd_create_user`` refuses it too: the contract lists
   registration, the profile and set-email, and this is the rule's own invariant on the one other path that writes a new
   address (UNAME-012: drop it if the coordinator does). Whether an account may take its OWN legacy username as its
   address is not pinned.

Where rule 1 refuses registration and the profile — the schema (422) or the service (400) — is the implementer's call:
it is pinned over HTTP only. ``register_user`` is pinned here for rule 2, which no schema can decide.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the global settings the
startup seeds, opened as production opens its own (aiosqlite, NullPool, the PRAGMA listener of
``backend.app.db.session``), disposed at teardown. The command line runs in this process, its ``get_async_engine``
pointed at that file; ``get_async_engine`` of the session module and of the modules that import it by name is a
tripwire. The accounts, F02 and email variables of the shell are removed; bcrypt runs at its lowest cost. The accounts
of a scene are rows with a marker hash; every username and address carries a random tag of its own. «Nothing written»
is every row of every table, ``sqlite_sequence`` included, read by SQLite from the file before and after.

Red until A-21a, each test on its own, at its first assertion: today ``cmd_create_user`` creates an account named with an
``@`` (UNAME-001) or whose address is another account's username (UNAME-012), ``admin_bootstrap_config`` takes an ``@``
username (UNAME-003), ``cmd_set_email`` changes the address (UNAME-010), ``register_user`` creates the account
(UNAME-011). Each refusal carries a barrier, run after it: the same call with the ``@`` replaced, or with a fresh
address, goes through — so the refusal is the rule's, not the scene's. The GUARDS (UNAME-002, 004, 013) are green today
and must stay so.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, Union

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config import accounts
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountTokenPurpose, GlobalSetting, User
from backend.app.services.accounts import auth_service, bootstrap_admin_service, registration_service, token_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE RULES' VALUES — a different decision is an edit here
# =============================================================================

#: The one character rule 1 refuses in a new username: it makes a username look like an address.
AT = "@"
#: What stands for the ``@`` in a barrier's username: the same name without the one character rule 1 refuses.
NOT_AT = "-"
#: New usernames with an ``@``, as templates of a fresh tag: 3 to 50 characters each, so only the ``@`` can refuse them.
AT_USERNAMES = [
    pytest.param("squat.{tag}@example.com", id="an-address"),
    pytest.param("name@{tag}", id="name-at-tag"),
    pytest.param("@{tag}", id="leading-at"),
    pytest.param("{tag}@", id="trailing-at"),
]
#: New usernames rule 1 leaves alone (GUARDS): spaces, accents, and the punctuation an address holds besides the ``@``.
ALLOWED_USERNAMES = [
    pytest.param("José María {tag}", id="spaces-and-accents"),
    pytest.param("Zoë_Ångström-{tag}", id="accents-underscore-hyphen"),
    pytest.param("first.last+{tag}", id="dot-and-plus"),
]
#: How ``register_user`` refuses an address that is another account's username (rule 2): as it refuses an address
#: already registered. A code of its own is the other admissible decision: then change both.
EMAIL_TAKEN_CODE = "ACCOUNT_EXISTS"
EMAIL_TAKEN_MESSAGE = "Email already registered"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
ADMIN_USERNAME_VARIABLE = "LIBREFOLIO_ADMIN_USERNAME"

USER_CLI_MODULE = "scripts.user_cli"
#: How the command line says it did, or did not: the first character of a line.
DONE, REFUSED = "✅", "❌"
#: A password that meets the rules (decision 37): the command line checks it before anything else.
PASSWORD = "Username-Rules-2026!"
#: What the accounts written as rows hold for a hash: nobody signs in with them here.
MARKER_HASH = "$argon2id$username-rules-marker"
#: When an address was verified, and a session version of its own: a refused change must keep both.
VERIFIED_AT = datetime(2026, 10, 2, 8, 0, 0)
SESSION_VERSION = 3
#: Removed before every test: each changes what registration, F02 or an email decide.
INHERITED_PREFIXES = ("LIBREFOLIO_ADMIN_", "LIBREFOLIO_SMTP_")
INHERITED_VARIABLES = ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL", "LIBREFOLIO_BLOCKED")


# =============================================================================
# NAMES AND ADDRESSES
# =============================================================================


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _address(prefix: str) -> str:
    """An address nobody has: ``prefix``, a tag of its own, at ``example.com``, all in lower case."""
    return f"{prefix}.{_tag()}@example.com"


def _named(template: str) -> str:
    """``template`` with a fresh tag: a name nobody has."""
    return template.format(tag=_tag())


def _without_at(name: str) -> str:
    """The barrier's name: ``name`` with each ``@`` replaced, nothing else changed."""
    return name.replace(AT, NOT_AT)


def _ascii_fold(text: str) -> str:
    """The fold of decision P18, written out: A–Z to a–z, every other character as it is."""
    return "".join(chr(ord(character) + 32) if "A" <= character <= "Z" else character for character in text)


def _as_written(address: str) -> str:
    return address


def _upper(address: str) -> str:
    return address.upper()


def _capitalized(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local.capitalize()}@{domain.capitalize()}"


Form = Callable[[str], str]

#: (how the legacy username writes an address, how the address is typed): the same address but for A–Z, both ways.
SQUAT_PAIRS = [
    pytest.param(_as_written, _as_written, id="typed-as-the-name-is-written"),
    pytest.param(_as_written, _upper, id="typed-in-UPPER"),
    pytest.param(_capitalized, _as_written, id="name-Capitalized-typed-in-lower"),
]


def _squat(name_form: Form, typed_form: Form) -> tuple[str, str]:
    """A legacy username holding an address, and that address as typed: checked to be the same address but for A–Z."""
    address = _address("squat")
    name, typed = name_form(address), typed_form(address)
    assert AT in name and _ascii_fold(name) == _ascii_fold(typed), f"test bug: {typed!r} is not the legacy name {name!r} but for A–Z"
    return name, typed


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def accounts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the accounts, F02 and email variables of the shell that started the run."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at its lowest cost in this process: ``user create`` hashes a real password, a hundred times cheaper."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises — in the session module, and in the modules that import it by name and open sessions of their own."""
    for module in (db_session, bootstrap_admin_service, email_flows, email_verification):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=False)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "username-rules.db"


@pytest_asyncio.fixture
async def engine(db_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema (``create_all``) and the global settings the startup seeds; disposed at teardown."""
    private = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def user_cli(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """``scripts/user_cli.py`` in this process, as the F02 and P18 tests import it, its ``get_async_engine`` the private file's engine."""
    module = importlib.import_module(USER_CLI_MODULE)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine)
    return module


# =============================================================================
# HELPERS — the database, read by SQLite, and the accounts as rows
# =============================================================================

Rows = dict[str, list[tuple[Any, ...]]]


def _rows(db_path: Path) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, read from the file: what «nothing written» compares."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: sorted(conn.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr) for table in tables}


def _changed(before: Rows, after: Rows) -> list[str]:
    """The tables whose rows differ between ``before`` and ``after``."""
    return sorted(table for table in set(before) | set(after) if before.get(table) != after.get(table))


@dataclass(frozen=True)
class Stored:
    """A committed ``users`` row, as far as a name and an address go, read in a fresh session."""

    id: int
    username: str
    email: str
    email_verified_at: Optional[datetime]
    session_version: int


async def _add_account(engine: AsyncEngine, *, username: str, email: str) -> int:
    """An account written as a row and committed before anything under test runs — as an install before A-21a may hold it —, its address verified, at ``SESSION_VERSION``. Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=MARKER_HASH, email_verified_at=VERIFIED_AT, session_version=SESSION_VERSION)
        session.add(user)
        await session.commit()
        return user.id


async def _stored(engine: AsyncEngine, user_id: int) -> Optional[Stored]:
    """The committed row of ``user_id``, read in a fresh session; None when there is none."""
    columns = (User.id, User.username, User.email, User.email_verified_at, User.session_version)
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(*columns).where(User.id == user_id))).one_or_none()
    return None if row is None else Stored(row.id, row.username, row.email, row.email_verified_at, row.session_version)


async def _usernames(engine: AsyncEngine, *names: str) -> set[str]:
    """Which of ``names`` the database holds as usernames, compared as written."""
    async with AsyncSession(engine) as session:
        return set((await session.execute(select(User.username).where(User.username.in_(names)))).scalars().all())


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` = ``open``, on the row the startup seeded: a registration needs no invitation."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, "registration_mode")
        assert row is not None, "setup: initialize_global_settings seeded no registration_mode row"
        row.value = "open"
        session.add(row)
        await session.commit()


async def _invitation(engine: AsyncEngine, creator: int) -> str:
    """A live invitation issued by the token service directly and committed: the scene is set without the service under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE, created_by_user_id=creator)
        await session.commit()
    return issued.token


# =============================================================================
# HELPERS — the command line and registration, called as their callers call them
# =============================================================================


async def _cli(user_cli: ModuleType, capsys: pytest.CaptureFixture[str], command: str, *arguments: Any) -> tuple[Any, str]:
    """``user_cli.<command>(*arguments)`` in this process, on the private file: what it answered, and what it printed."""
    capsys.readouterr()
    answer = await getattr(user_cli, command)(*arguments)
    return answer, capsys.readouterr().out


def _lines_starting(printed: str, marker: str) -> list[str]:
    return [line for line in printed.splitlines() if line.startswith(marker)]


def _assert_cli_refused(answer: Any, printed: str, what: str) -> None:
    """The command line's refusal: a falsy answer, a line starting with ❌, none with ✅."""
    assert not answer, f"red until A-21a: {what} must be refused: the command answered {answer!r} and printed {printed!r}"
    assert _lines_starting(printed, REFUSED) and not _lines_starting(printed, DONE), f"{what}: a line must start with {REFUSED} and none with {DONE}: {printed!r}"


def _assert_cli_done(answer: Any, printed: str, what: str) -> None:
    """The command line went through: a truthy answer, a line starting with ✅."""
    assert answer and _lines_starting(printed, DONE), f"{what} must go through: the command answered {answer!r} and printed {printed!r}"


async def _register(engine: AsyncEngine, username: str, email: str, invite_token: Optional[str]) -> Union[User, registration_service.RegistrationError]:
    """``register_user`` as test_registration_service calls it: the new account, or the refusal — committed after it, as a careless caller would, so a refusal that left something behind shows."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            user = await registration_service.register_user(session, username=username, email=email, password=PASSWORD, invite_token=invite_token)
        except registration_service.RegistrationError as refusal:
            await session.commit()
            return refusal
        await session.commit()
    return user


# =============================================================================
# RULE 1 — NO @ IN A NEW USERNAME: user create
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("superuser", [True, False], ids=["administrator", "role-user"])
@pytest.mark.parametrize("template", AT_USERNAMES)
async def test_user_create_refuses_a_new_username_with_an_at(engine: AsyncEngine, db_path: Path, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], template: str, superuser: bool) -> None:
    """UNAME-001 — rule 1, red until A-21a (today the account is created, ✅): ``cmd_create_user`` — ``./dev.py user create``, an administrator or ``--role user`` — with a username holding an ``@`` (an address, ``name@tag``, a leading or a trailing ``@``; 3 to 50 characters) and a password that meets the rules answers falsy and prints a line starting with ❌; every row of every table is as it was. Barrier: the same command with the ``@`` replaced by ``-`` creates the account, ✅ — the refusal is the ``@``'s."""
    print_section(f"UNAME-001: user create {'--role admin' if superuser else '--role user'} with an @ in the username")
    name = _named(template)
    before = _rows(db_path)

    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", name, _address("cli"), PASSWORD, superuser)

    _assert_cli_refused(answer, printed, f"user create {name!r}")
    assert _changed(before, _rows(db_path)) == [], f"a refused user create must write nothing: {_changed(before, _rows(db_path))}"
    allowed = _without_at(name)
    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", allowed, _address("cli"), PASSWORD, superuser)
    _assert_cli_done(answer, printed, f"barrier: user create {allowed!r}, the same name without its @,")
    assert await _usernames(engine, name, allowed) == {allowed}, "barrier: the account without the @ exists, the one with it does not"
    print_success(f"{name!r} refused, nothing written; {allowed!r} created")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("template", ALLOWED_USERNAMES)
async def test_user_create_still_takes_spaces_accents_and_punctuation(engine: AsyncEngine, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], template: str) -> None:
    """UNAME-002 — rule 1, GUARD (green today; red if A-21a refuses more than the ``@``): ``cmd_create_user`` of a username with spaces and accents, or with ``.``, ``_``, ``-`` and ``+``, creates the account, ✅, its username stored exactly as given."""
    name = _named(template)

    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", name, _address("cli"), PASSWORD, False)

    _assert_cli_done(answer, printed, f"user create {name!r}")
    assert await _usernames(engine, name) == {name}, f"{name!r} must be stored exactly as given"


# =============================================================================
# RULE 1 — NO @ IN A NEW USERNAME: LIBREFOLIO_ADMIN_USERNAME (F02)
# =============================================================================

#: The username templates of UNAME-003, and the classic slip: the administrator's own address as its username.
ADMIN_AT_USERNAMES = [*AT_USERNAMES, pytest.param(None, id="the-admin-email-itself")]


# red until A-21a
@pytest.mark.parametrize("template", ADMIN_AT_USERNAMES)
def test_an_admin_username_with_an_at_is_a_config_error_naming_the_variable(monkeypatch: pytest.MonkeyPatch, template: Optional[str]) -> None:
    """UNAME-003 — rule 1, red until A-21a (today the configuration is taken): ``LIBREFOLIO_ADMIN_EMAIL`` a valid address and ``LIBREFOLIO_ADMIN_USERNAME`` a name holding an ``@`` — an address, ``name@tag``, a leading or a trailing ``@``, or that very ``LIBREFOLIO_ADMIN_EMAIL`` —: ``admin_bootstrap_config()`` raises ``AdminBootstrapConfigError``, its ``variable`` ``LIBREFOLIO_ADMIN_USERNAME``, its message naming the variable and saying what is wrong: it shows the ``@``. The startup audit calls it, so the server would not start (CFG-009 of test_admin_bootstrap). Barrier: the same name with the ``@`` replaced is taken, as given."""
    print_section("UNAME-003: LIBREFOLIO_ADMIN_USERNAME with an @")
    email = _address("admin")
    name = email if template is None else _named(template)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, email)
    monkeypatch.setenv(ADMIN_USERNAME_VARIABLE, name)

    try:
        config = accounts.admin_bootstrap_config()
    except accounts.AdminBootstrapConfigError as error:
        refused = error
    else:
        pytest.fail(f"red until A-21a: {ADMIN_USERNAME_VARIABLE}={name!r} was taken ({config!r}): a username with an @ must be an AdminBootstrapConfigError naming the variable", pytrace=False)

    assert refused.variable == ADMIN_USERNAME_VARIABLE, f"the error must be {ADMIN_USERNAME_VARIABLE}'s: variable {refused.variable!r} ({refused})"
    assert ADMIN_USERNAME_VARIABLE in str(refused), f"the message must name {ADMIN_USERNAME_VARIABLE}: {refused}"
    assert AT in str(refused), f"the message must say what is wrong — the {AT} —, not only a length: {refused}"
    monkeypatch.setenv(ADMIN_USERNAME_VARIABLE, _without_at(name))
    allowed = accounts.admin_bootstrap_config()
    assert allowed is not None and allowed.username == _without_at(name), f"barrier: the same name without its @ must be taken, as given: {allowed!r}"
    print_success(f"refused: {refused}")


# GUARD — green today, must stay green
@pytest.mark.parametrize("template", ALLOWED_USERNAMES)
def test_an_admin_username_with_spaces_accents_or_punctuation_is_taken(monkeypatch: pytest.MonkeyPatch, template: str) -> None:
    """UNAME-004 — rule 1, GUARD (green today; red if A-21a refuses more than the ``@``): ``LIBREFOLIO_ADMIN_USERNAME`` with spaces and accents, or with ``.``, ``_``, ``-`` and ``+``, is taken: the configuration's ``username`` is that name, exactly."""
    name = _named(template)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, _address("admin"))
    monkeypatch.setenv(ADMIN_USERNAME_VARIABLE, name)

    config = accounts.admin_bootstrap_config()

    assert config is not None and config.username == name, f"{ADMIN_USERNAME_VARIABLE}={name!r} must be taken as given: {config!r}"


# =============================================================================
# RULE 2 — NO ADDRESS THAT IS ANOTHER ACCOUNT'S USERNAME, A–Z CASE ASIDE
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize(("name_form", "typed_form"), SQUAT_PAIRS)
async def test_set_email_refuses_an_address_that_is_another_accounts_username(engine: AsyncEngine, db_path: Path, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], name_form: Form, typed_form: Form) -> None:
    """UNAME-010 — rule 2, red until A-21a (today the address changes, ✅): a legacy account named with an address, written as a row; ``cmd_set_email`` — ``./dev.py user set-email`` — of another account to that address, as the name writes it or in another A–Z case, answers falsy and prints a line starting with ❌; every row of every table is as it was (the account keeps its address, its verification and its session version). Barrier: ``cmd_set_email`` of the same account to a fresh address goes through, ✅."""
    print_section("UNAME-010: user set-email to another account's username")
    name, typed = _squat(name_form, typed_form)
    await _add_account(engine, username=name, email=_address("legacy"))
    target_name = f"target_{_tag()}"
    target = await _add_account(engine, username=target_name, email=_address("target"))
    before = _rows(db_path)

    answer, printed = await _cli(user_cli, capsys, "cmd_set_email", target_name, typed)

    _assert_cli_refused(answer, printed, f"user set-email {target_name} {typed!r}, the username of another account but for A–Z,")
    assert _changed(before, _rows(db_path)) == [], f"a refused set-email must write nothing: {_changed(before, _rows(db_path))}"
    fresh = _address("fresh")
    answer, printed = await _cli(user_cli, capsys, "cmd_set_email", target_name, fresh)
    _assert_cli_done(answer, printed, f"barrier: user set-email {target_name} to a fresh address")
    stored = await _stored(engine, target)
    assert stored is not None and stored.email == fresh, f"barrier: the fresh address is stored: {stored}"
    print_success("refused, nothing written; a fresh address goes through")


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("with_invitation", [False, True], ids=["open-no-invitation", "a-valid-invitation"])
@pytest.mark.parametrize(("name_form", "typed_form"), SQUAT_PAIRS)
async def test_register_user_refuses_an_address_that_is_another_accounts_username(engine: AsyncEngine, db_path: Path, name_form: Form, typed_form: Form, with_invitation: bool) -> None:
    """UNAME-011 — rule 2, red until A-21a (today the account is created): a legacy account named with an address, written as a row; ``register_user`` of a new username with that address — as the name writes it or in another A–Z case —, registration ``open`` without an invitation or by invitation with a valid one, raises ``RegistrationError`` with ``EMAIL_TAKEN_CODE`` and ``EMAIL_TAKEN_MESSAGE``, as for an address already registered, and writes nothing: every row of every table as it was — the invitation still live. Barrier: the same registration with a fresh address goes through, the invitation spent by it."""
    print_section("UNAME-011: register_user with another account's username for address")
    name, typed = _squat(name_form, typed_form)
    legacy = await _add_account(engine, username=name, email=_address("legacy"))
    invitation = await _invitation(engine, legacy) if with_invitation else None
    if not with_invitation:
        await _registration_open(engine)
    newcomer = f"newcomer_{_tag()}"
    before = _rows(db_path)

    outcome = await _register(engine, newcomer, typed, invitation)

    assert isinstance(outcome, registration_service.RegistrationError), f"red until A-21a: {typed!r} is the username of another account but for A–Z: the registration must be refused, yet it created account #{outcome.id} with that address"
    assert (outcome.code, outcome.message) == (EMAIL_TAKEN_CODE, EMAIL_TAKEN_MESSAGE), f"the refusal must be the answer to an address already registered, ({EMAIL_TAKEN_CODE!r}, {EMAIL_TAKEN_MESSAGE!r}): got ({outcome.code!r}, {outcome.message!r})"
    assert _changed(before, _rows(db_path)) == [], f"a refused registration must write nothing, the invitation included: {_changed(before, _rows(db_path))}"
    created = await _register(engine, newcomer, _address("fresh"), invitation)
    assert isinstance(created, User), f"barrier: the same registration with a fresh address must go through (the invitation still live), refused: {created!r}"
    print_success("refused as an address already registered, nothing written; a fresh address goes through")


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize(("name_form", "typed_form"), SQUAT_PAIRS)
async def test_user_create_refuses_an_address_that_is_another_accounts_username(engine: AsyncEngine, db_path: Path, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], name_form: Form, typed_form: Form) -> None:
    """UNAME-012 — rule 2 on the command line's own path (an extension of the contract's list: drop it if the coordinator does), red until A-21a (today the account is created, ✅): a legacy account named with an address, written as a row; ``cmd_create_user`` of a new username with that address — as the name writes it or in another A–Z case — answers falsy, prints a line starting with ❌, and writes nothing. Barrier: the same command with a fresh address creates the account."""
    name, typed = _squat(name_form, typed_form)
    await _add_account(engine, username=name, email=_address("legacy"))
    newcomer = f"newcomer_{_tag()}"
    before = _rows(db_path)

    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", newcomer, typed, PASSWORD, False)

    _assert_cli_refused(answer, printed, f"user create {newcomer} {typed!r}, the username of another account but for A–Z,")
    assert _changed(before, _rows(db_path)) == [], f"a refused user create must write nothing: {_changed(before, _rows(db_path))}"
    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", newcomer, _address("fresh"), PASSWORD, False)
    _assert_cli_done(answer, printed, f"barrier: user create {newcomer} with a fresh address")


# GUARD — green today, must stay green
@pytest.mark.asyncio
async def test_a_legacy_username_with_an_at_is_left_as_it_is(engine: AsyncEngine, user_cli: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    """UNAME-013 — rules 1 and 2, GUARD (green today; red if A-21a renames legacy accounts or locks them out of the command line): a legacy account named with an address, written as a row: ``cmd_set_email`` reaches it by that exact name and changes its address to a fresh one, ✅; its username is as it was — A-21a refuses NEW names, it renames none."""
    name = _address("legacy.name")
    legacy = await _add_account(engine, username=name, email=_address("legacy"))
    fresh = _address("fresh")

    answer, printed = await _cli(user_cli, capsys, "cmd_set_email", name, fresh)

    _assert_cli_done(answer, printed, f"user set-email {name!r}, a legacy account by its exact name,")
    stored = await _stored(engine, legacy)
    assert stored is not None and (stored.username, stored.email) == (name, fresh), f"the legacy name stays as it is, the address changes: {stored}"

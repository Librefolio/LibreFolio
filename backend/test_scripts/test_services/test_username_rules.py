"""A-21a, rules 1 and 2: no new username with an @, no address that is another account's username — the command line, F02 and registration's service (release 1.3, workstream A, lot A-21a; workstream E's review, point c). A-46 and A-47: 3 to 50 characters on the command line too, and refusals that carry their code (lots A-46 and A-47; A-47 is workstream E's LOW).

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

A-46 and A-47 (workstream A; A-47 is workstream E's LOW). Registration and the profile refuse a username outside 3 to 50
characters — their schemas answer 422 before the service —, and ``LIBREFOLIO_ADMIN_USERNAME`` does at config parse; but
``./dev.py user create`` takes any length (A-46). And the callers of ``user_service.create_user`` and ``update_profile``
read a refusal by its text: ``register_user`` and ``PUT /auth/profile`` answer ``USERNAME_INVALID`` when the message
equals the ``USERNAME_RESERVED_MESSAGE`` they imported, so a change of wording would silently turn that refusal into
another (A-47). The cure, pinned here where it does not go through HTTP (over HTTP: UNAME-API-12 to 14):

- A-47: every refusal of ``create_user`` and ``update_profile`` is a ``user_service.AccountError``, a ``str`` carrying
  ``code`` — its message unchanged, so every comparison with the text still holds: ``USERNAME_INVALID`` (an ``@``, and a
  length outside 3 to 50), ``USERNAME_TAKEN`` («Username already taken»), ``EMAIL_TAKEN`` («Email already registered»:
  an address registered, or another account's username) and ``USER_NOT_FOUND`` («User not found», ``update_profile``).
  ``register_user`` branches on the code: a username with an ``@`` is ``USERNAME_INVALID`` however ``user_service``
  words it — reworded there only, by ``monkeypatch``, so the constant the callers imported no longer equals it.
- A-46: ``create_user`` and ``update_profile`` — a name that CHANGES only, as for the ``@`` — refuse a new username
  shorter than 3 or longer than 50 characters: ``(None, error)``, ``USERNAME_INVALID``, a message of its own that says
  the rule (it names 3 and 50; nothing more of its wording is pinned), nothing written. So ``cmd_create_user`` refuses
  it, an administrator or ``--role user``: falsy, ❌, nothing written. A legacy name of such a length is kept: a change
  that keeps it, or changes the address alone, is not checked (GUARD). The lengths are written out here, 3 and 50: the
  constants the cure renames are not imported.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the global settings the
startup seeds, opened as production opens its own (aiosqlite, NullPool, the PRAGMA listener of
``backend.app.db.session``), disposed at teardown. The command line runs in this process, its ``get_async_engine``
pointed at that file; ``get_async_engine`` of the session module and of the modules that import it by name is a
tripwire. The accounts, F02 and email variables of the shell are removed; bcrypt runs at its lowest cost. The accounts
of a scene are rows with a marker hash; every username and address carries a random tag of its own. «Nothing written»
is every row of every table, ``sqlite_sequence`` included, read by SQLite from the file before and after. UNAME-031
rewords the ``@``'s message in ``user_service`` through ``monkeypatch``, put back after it.

Red until A-21a, each test on its own, at its first assertion: today ``cmd_create_user`` creates an account named with an
``@`` (UNAME-001) or whose address is another account's username (UNAME-012), ``admin_bootstrap_config`` takes an ``@``
username (UNAME-003), ``cmd_set_email`` changes the address (UNAME-010), ``register_user`` creates the account
(UNAME-011). Each refusal carries a barrier, run after it: the same call with the ``@`` replaced, or with a fresh
address, goes through — so the refusal is the rule's, not the scene's. The GUARDS (UNAME-002, 004, 013) are green today
and must stay so.

Red until A-46, each test on its own, at its first assertion: today ``cmd_create_user`` creates an account named with 2
or 51 characters (UNAME-020), so does ``create_user`` (UNAME-021), and ``update_profile`` gives an account such a name
(UNAME-022); 021 and 022 ask A-47's code of the refusal too, so they turn green with both. Red until A-47: every refusal
of ``create_user`` and ``update_profile`` is a bare ``str``, without ``code`` (UNAME-030, at the code: its GUARD half —
the message as today, a ``str``, nothing written — is asserted first and holds today), and ``register_user`` answers
``ACCOUNT_EXISTS`` to a username with an ``@`` once ``user_service`` words the refusal otherwise (UNAME-031, at the code:
the reworded message reaching the refusal is asserted first). Each refusal of A-46 carries a barrier: the same call with
the name one character nearer, at 3 or 50 characters, goes through. UNAME-023 is a GUARD, green today and to stay green.

UNAME-032 — NEW, red until the A-47 review fix (A-51 lot; workstream E's review of A-47): an ``AccountError`` survives
``copy.copy``, ``copy.deepcopy`` and ``pickle.loads(pickle.dumps(…))`` — the duplicate an ``AccountError``, equal as a
``str`` to the original message, with the same ``code``. Today each raises a ``TypeError``: they rebuild a ``str``
subclass from ``str.__getnewargs__``, the message alone, and ``AccountError.__new__`` asks for ``(code, message)``. The
refusal duplicated is a real one, ``create_user``'s to a username taken in UNAME-030's scene, asserted first.
"""

from __future__ import annotations

import contextlib
import copy
import importlib
import os
import pickle
import sqlite3
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
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
from backend.app.services.accounts import auth_service, bootstrap_admin_service, registration_service, token_service, user_service
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
#: A-46: a new username has 3 to 50 characters, as registration and the profile ask (``AuthRegisterRequest``,
#: ``UpdateProfileRequest``) — written out: the constants the cure renames are not imported.
SHORTEST, LONGEST = 3, 50
#: (a length A-46 refuses in a new username, the barrier's length): the barrier is one character nearer, a boundary.
OUTSIDE_LENGTHS = [pytest.param(2, 3, id="2-characters"), pytest.param(51, 50, id="51-characters")]
#: The lengths of a legacy username A-46 leaves alone: those it refuses in a new one (GUARD).
LEGACY_LENGTHS = [pytest.param(2, id="2-characters"), pytest.param(51, id="51-characters")]
#: A-47: the code of a new username refused — by ``user_service.AccountError`` and by ``register_user`` alike.
USERNAME_INVALID = "USERNAME_INVALID"
#: Today's messages of the other refusals of ``create_user`` and ``update_profile``: A-47 leaves them as they are.
USERNAME_TAKEN_MESSAGE = "Username already taken"
USER_NOT_FOUND_MESSAGE = "User not found"
#: The ``@``'s message as ``user_service`` might word it one day: reworded there only (UNAME-031).
REWORDED_RESERVED_MESSAGE = "Reworded for A-47: a new username holds no at sign"
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


def _of_length(length: int) -> str:
    """A fresh name of exactly ``length`` characters, random hex: nothing but its length for a rule to refuse."""
    return "".join(uuid.uuid4().hex for _ in range(length // 32 + 1))[:length]


def _to_length(name: str, length: int) -> str:
    """The barrier's name: ``name`` cut, or carried on with fresh characters, to exactly ``length`` characters."""
    return name[:length] if len(name) >= length else name + _of_length(length - len(name))


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


def _assert_cli_refused(answer: Any, printed: str, what: str, lot: str = "A-21a") -> None:
    """The command line's refusal: a falsy answer, a line starting with ❌, none with ✅. ``lot`` is the one it is red until."""
    assert not answer, f"red until {lot}: {what} must be refused: the command answered {answer!r} and printed {printed!r}"
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
# HELPERS — A-46 AND A-47: the service called as its callers call it
# =============================================================================

Outcome = tuple[Optional[User], Optional[str]]


async def _create(engine: AsyncEngine, username: str, email: str) -> Outcome:
    """``user_service.create_user`` as ``./dev.py user create`` calls it — committed after, as a careless caller would, so a refusal that left something behind shows. Its answer."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        outcome = await user_service.create_user(session, username, email, PASSWORD)
        await session.commit()
    return outcome


async def _update(engine: AsyncEngine, user_id: int, **changes: str) -> Outcome:
    """``user_service.update_profile`` as the profile and ``./dev.py user set-email`` call it — committed after, as a careless caller would. Its answer."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        outcome = await user_service.update_profile(session, user_id, **changes)
        await session.commit()
    return outcome


def _shown(outcome: Outcome) -> str:
    """An answer of the service as a failure says it: the account it gave, or its refusal with the code it carries."""
    user, error = outcome
    if user is not None:
        return f"(account #{user.id} {user.username!r}, {error!r})"
    return f"(None, {error!r}) of type {type(error).__qualname__}, code {getattr(error, 'code', 'none')!r}"


def _assert_length_refusal(outcome: Outcome, what: str) -> None:
    """A-46's refusal: ``(None, error)``, a message of its own that says the rule — it names 3 and 50 —, and A-47's code ``USERNAME_INVALID``."""
    user, error = outcome
    assert user is None and error, f"red until A-46: {what} must be refused, (None, error): got {_shown(outcome)}"
    assert str(SHORTEST) in error and str(LONGEST) in error, f"{what}: the message must say the rule, {SHORTEST} to {LONGEST} characters: {error!r}"
    assert getattr(error, "code", None) == USERNAME_INVALID, f"{what}: the refusal must carry the code {USERNAME_INVALID} (A-47): {_shown(outcome)}"


@dataclass(frozen=True)
class Scene:
    """The accounts the refusals of UNAME-030 meet, written as rows: a holder whose name and address are taken, a legacy account named with an address, a member who changes its profile; and an id no account has."""

    holder_name: str
    holder_email: str
    legacy_name: str
    member: int
    missing: int


async def _scene(engine: AsyncEngine) -> Scene:
    """UNAME-030's accounts, committed before anything under test runs; the id no account has is past every one of them."""
    holder_name, holder_email, legacy_name = f"holder_{_tag()}", _address("holder"), _address("legacy.name")
    await _add_account(engine, username=holder_name, email=holder_email)
    await _add_account(engine, username=legacy_name, email=_address("legacy"))
    member = await _add_account(engine, username=f"member_{_tag()}", email=_address("member"))
    return Scene(holder_name=holder_name, holder_email=holder_email, legacy_name=legacy_name, member=member, missing=member + 1000)


Ask = Callable[[AsyncEngine, Scene], Awaitable[Outcome]]


async def _create_with_an_at(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _create(engine, _named("name@{tag}"), _address("new"))


async def _create_a_taken_username(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _create(engine, scene.holder_name, _address("new"))


async def _create_with_a_taken_address(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _create(engine, f"new_{_tag()}", scene.holder_email)


async def _create_with_a_legacy_username_for_address(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _create(engine, f"new_{_tag()}", scene.legacy_name)


async def _update_no_such_account(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _update(engine, scene.missing, username=f"new_{_tag()}")


async def _update_with_an_at(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _update(engine, scene.member, username=_named("name@{tag}"))


async def _update_to_a_taken_username(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _update(engine, scene.member, username=scene.holder_name)


async def _update_to_a_taken_address(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _update(engine, scene.member, email=scene.holder_email)


async def _update_to_a_legacy_username_for_address(engine: AsyncEngine, scene: Scene) -> Outcome:
    return await _update(engine, scene.member, email=scene.legacy_name)


def _reword_reserved_message(monkeypatch: pytest.MonkeyPatch) -> str:
    """The ``@``'s message reworded in ``user_service`` only — the namespace ``create_user`` and ``update_profile`` read it from at each call —, so the constant the callers imported no longer equals what the service answers. The reworded text."""
    assert hasattr(user_service, "USERNAME_RESERVED_MESSAGE"), "setup: user_service no longer reads USERNAME_RESERVED_MESSAGE from its own namespace: reword the message where the refusal now takes it"
    monkeypatch.setattr(user_service, "USERNAME_RESERVED_MESSAGE", REWORDED_RESERVED_MESSAGE)
    return REWORDED_RESERVED_MESSAGE


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


# =============================================================================
# A-46 — A NEW USERNAME HAS 3 TO 50 CHARACTERS: user create, create_user, update_profile
# =============================================================================


# red until A-46
@pytest.mark.asyncio
@pytest.mark.parametrize("superuser", [True, False], ids=["administrator", "role-user"])
@pytest.mark.parametrize(("length", "boundary"), OUTSIDE_LENGTHS)
async def test_user_create_refuses_a_new_username_outside_3_to_50_characters(engine: AsyncEngine, db_path: Path, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], length: int, boundary: int, superuser: bool) -> None:
    """UNAME-020 — A-46, NEW, red until A-46 (today the account is created, ✅): ``cmd_create_user`` — ``./dev.py user create``, an administrator or ``--role user`` — with a username of 2 or 51 characters, which registration and the profile refuse, and a password that meets the rules answers falsy and prints a line starting with ❌; every row of every table is as it was. Barrier: the same command with the name one character nearer — 3 or 50 characters, the boundaries — creates the account, ✅: the refusal is the length's."""
    print_section(f"UNAME-020: user create {'--role admin' if superuser else '--role user'} with a username of {length} characters")
    name = _of_length(length)
    before = _rows(db_path)

    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", name, _address("cli"), PASSWORD, superuser)

    _assert_cli_refused(answer, printed, f"user create {name!r}, {length} characters,", lot="A-46")
    assert _changed(before, _rows(db_path)) == [], f"a refused user create must write nothing: {_changed(before, _rows(db_path))}"
    allowed = _to_length(name, boundary)
    answer, printed = await _cli(user_cli, capsys, "cmd_create_user", allowed, _address("cli"), PASSWORD, superuser)
    _assert_cli_done(answer, printed, f"barrier: user create {allowed!r}, {boundary} characters,")
    assert await _usernames(engine, name, allowed) == {allowed}, f"barrier: the account of {boundary} characters exists, the one of {length} does not"
    print_success(f"{length} characters refused, nothing written; {boundary} characters created")


# red until A-46
@pytest.mark.asyncio
@pytest.mark.parametrize(("length", "boundary"), OUTSIDE_LENGTHS)
async def test_create_user_refuses_a_new_username_outside_3_to_50_characters(engine: AsyncEngine, db_path: Path, length: int, boundary: int) -> None:
    """UNAME-021 — A-46, NEW, red until A-46 (today the account is created): ``user_service.create_user`` of a username of 2 or 51 characters answers ``(None, error)``: a message of its own that says the rule — it names 3 and 50; nothing more of its wording is pinned —, ``error.code`` ``USERNAME_INVALID`` (A-47); every row of every table is as it was, even once the caller commits. Barrier: the same call with the name one character nearer — 3 or 50 characters — creates the account."""
    print_section(f"UNAME-021: create_user with a username of {length} characters")
    name = _of_length(length)
    before = _rows(db_path)

    outcome = await _create(engine, name, _address("svc"))

    _assert_length_refusal(outcome, f"create_user of {name!r}, {length} characters,")
    assert _changed(before, _rows(db_path)) == [], f"a refused create_user must write nothing, even once the caller commits: {_changed(before, _rows(db_path))}"
    allowed = _to_length(name, boundary)
    created = await _create(engine, allowed, _address("svc"))
    assert created[0] is not None and created[1] is None, f"barrier: create_user of {allowed!r}, {boundary} characters, must go through: {_shown(created)}"
    assert await _usernames(engine, name, allowed) == {allowed}, f"barrier: the account of {boundary} characters exists, the one of {length} does not"
    print_success(f"{length} characters refused: {outcome[1]!r}")


# red until A-46
@pytest.mark.asyncio
@pytest.mark.parametrize(("length", "boundary"), OUTSIDE_LENGTHS)
async def test_update_profile_refuses_a_new_username_outside_3_to_50_characters(engine: AsyncEngine, db_path: Path, length: int, boundary: int) -> None:
    """UNAME-022 — A-46, NEW, red until A-46 (today the name changes): an account written as a row; ``user_service.update_profile`` changing its username to one of 2 or 51 characters answers ``(None, error)`` as ``create_user`` does — the rule's own message naming 3 and 50, ``USERNAME_INVALID`` —, and every row of every table is as it was, even once the caller commits: its name, its address, its session version. Barrier: the same change with the name one character nearer — 3 or 50 characters — goes through, the name stored."""
    print_section(f"UNAME-022: update_profile to a username of {length} characters")
    member = await _add_account(engine, username=f"member_{_tag()}", email=_address("member"))
    name = _of_length(length)
    before = _rows(db_path)

    outcome = await _update(engine, member, username=name)

    _assert_length_refusal(outcome, f"update_profile of #{member} to {name!r}, {length} characters,")
    assert _changed(before, _rows(db_path)) == [], f"a refused update_profile must write nothing, even once the caller commits: {_changed(before, _rows(db_path))}"
    allowed = _to_length(name, boundary)
    updated = await _update(engine, member, username=allowed)
    stored = await _stored(engine, member)
    assert updated[0] is not None and updated[1] is None and stored is not None and stored.username == allowed, f"barrier: update_profile to {allowed!r}, {boundary} characters, must go through and be stored: {_shown(updated)}, {stored}"
    print_success(f"{length} characters refused, nothing written; {boundary} characters stored")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("length", LEGACY_LENGTHS)
async def test_a_legacy_username_outside_3_to_50_characters_is_kept(engine: AsyncEngine, user_cli: ModuleType, capsys: pytest.CaptureFixture[str], length: int) -> None:
    """UNAME-023 — A-46, GUARD (green today; red if A-46 checks a name that does not change, or renames one): a legacy account named with 2 or 51 characters — as ``./dev.py user create`` could write one before A-46 —, written as a row. ``update_profile`` given its own name beside a fresh address answers the account: the address changes, the name stays. ``cmd_set_email`` — ``./dev.py user set-email``, the address alone — reaches it by that exact name and changes the address again, ✅; the name stays — A-46 refuses NEW names, it renames none."""
    name = _of_length(length)
    legacy = await _add_account(engine, username=name, email=_address("legacy"))
    stored = await _stored(engine, legacy)
    assert stored is not None and stored.username == name, f"setup: a legacy name of {length} characters is written as a row, as given: {stored}"
    fresh = _address("fresh")

    outcome = await _update(engine, legacy, username=name, email=fresh)

    assert outcome[0] is not None and outcome[1] is None, f"update_profile of #{legacy} with its own name {name!r} ({length} characters) beside a fresh address must go through: {_shown(outcome)}"
    stored = await _stored(engine, legacy)
    assert stored is not None and (stored.username, stored.email) == (name, fresh), f"the legacy name stays, the address changes: {stored}"
    again = _address("again")
    answer, printed = await _cli(user_cli, capsys, "cmd_set_email", name, again)
    _assert_cli_done(answer, printed, f"user set-email {name!r}, a legacy account of {length} characters by its exact name,")
    stored = await _stored(engine, legacy)
    assert stored is not None and (stored.username, stored.email) == (name, again), f"the legacy name stays, the address changes again: {stored}"


# =============================================================================
# A-47 — EVERY REFUSAL OF create_user AND update_profile CARRIES ITS CODE
# =============================================================================

#: Each refusal of ``create_user`` and ``update_profile``, made against the accounts of ``Scene``: (how it is asked, the
#: message it answers — today, and unchanged after A-47 —, the code A-47 adds to it).
REFUSALS = [
    pytest.param(_create_with_an_at, accounts.USERNAME_RESERVED_MESSAGE, USERNAME_INVALID, id="create_user-an-at"),
    pytest.param(_create_a_taken_username, USERNAME_TAKEN_MESSAGE, "USERNAME_TAKEN", id="create_user-a-taken-username"),
    pytest.param(_create_with_a_taken_address, EMAIL_TAKEN_MESSAGE, "EMAIL_TAKEN", id="create_user-a-taken-address"),
    pytest.param(_create_with_a_legacy_username_for_address, EMAIL_TAKEN_MESSAGE, "EMAIL_TAKEN", id="create_user-a-legacy-username-for-address"),
    pytest.param(_update_no_such_account, USER_NOT_FOUND_MESSAGE, "USER_NOT_FOUND", id="update_profile-no-such-account"),
    pytest.param(_update_with_an_at, accounts.USERNAME_RESERVED_MESSAGE, USERNAME_INVALID, id="update_profile-an-at"),
    pytest.param(_update_to_a_taken_username, USERNAME_TAKEN_MESSAGE, "USERNAME_TAKEN", id="update_profile-a-taken-username"),
    pytest.param(_update_to_a_taken_address, EMAIL_TAKEN_MESSAGE, "EMAIL_TAKEN", id="update_profile-a-taken-address"),
    pytest.param(_update_to_a_legacy_username_for_address, EMAIL_TAKEN_MESSAGE, "EMAIL_TAKEN", id="update_profile-a-legacy-username-for-address"),
]


# red until A-47
@pytest.mark.asyncio
@pytest.mark.parametrize(("ask", "message", "code"), REFUSALS)
async def test_every_refusal_of_create_user_and_update_profile_carries_its_code(engine: AsyncEngine, db_path: Path, ask: Ask, message: str, code: str) -> None:
    """UNAME-030 — A-47, NEW, red until A-47 (today a bare ``str``, without ``code``): every refusal of ``create_user`` and ``update_profile`` — a new username with an ``@``, a username taken, an address registered or another account's username, an account that does not exist — answers ``(None, error)``, ``error`` a ``user_service.AccountError`` whose ``code`` says which: ``USERNAME_INVALID``, ``USERNAME_TAKEN``, ``EMAIL_TAKEN``, ``USER_NOT_FOUND``. GUARD half, asserted first and green today: ``error`` is a ``str`` equal to today's message — so every caller comparing the text still holds —, and nothing is written, even once the caller commits."""
    print_section(f"UNAME-030: the refusal {message!r} carries {code}")
    scene = await _scene(engine)
    before = _rows(db_path)

    outcome = await ask(engine, scene)

    user, error = outcome
    assert user is None and isinstance(error, str) and error == message, f"GUARD half: the refusal must be (None, {message!r}), a str, as today: {_shown(outcome)}"
    assert _changed(before, _rows(db_path)) == [], f"GUARD half: a refusal writes nothing, even once the caller commits: {_changed(before, _rows(db_path))}"
    assert getattr(error, "code", None) == code, f"red until A-47: the refusal {error!r} must carry the code {code!r} — its callers branch on it, not on the text —: {_shown(outcome)}"
    account_error = getattr(user_service, "AccountError", None)
    assert isinstance(account_error, type) and isinstance(error, account_error), f"the refusal must be a user_service.AccountError: it is a {type(error).__module__}.{type(error).__qualname__}"
    print_success(f"(None, {message!r}) carries {code}")


# red until A-47
@pytest.mark.asyncio
async def test_register_user_refuses_an_at_as_username_invalid_whatever_its_wording(engine: AsyncEngine, db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UNAME-031 — A-47, NEW, red until A-47 (today ``ACCOUNT_EXISTS``: ``register_user`` compares the message with the constant it imported): the ``@``'s message reworded in ``user_service`` only — the namespace ``create_user`` reads it from at each call —, an instance with an account, registration ``open``: ``register_user`` of a new username holding an ``@`` raises ``RegistrationError`` with the code ``USERNAME_INVALID`` and the reworded message — the code decides, not the text —, and writes nothing. The reworded message reaching the refusal is asserted first: the test cannot pass by not rewording. Barrier: the same registration with the ``@`` replaced goes through."""
    print_section("UNAME-031: register_user with an @, the message reworded in user_service")
    await _add_account(engine, username=f"seed_{_tag()}", email=_address("seed"))
    await _registration_open(engine)
    reworded = _reword_reserved_message(monkeypatch)
    name = _named("squat.{tag}@example.com")
    before = _rows(db_path)

    outcome = await _register(engine, name, _address("newcomer"), None)

    assert isinstance(outcome, registration_service.RegistrationError), f"{name!r} holds an @: the registration must be refused, yet it created account #{outcome.id}"
    assert outcome.message == reworded, f"setup: the refusal must carry the reworded message — user_service words it —, or this test proves nothing: {outcome.message!r}"
    assert outcome.code == USERNAME_INVALID, f"red until A-47: register_user must answer {USERNAME_INVALID} by the refusal's code, whatever its wording: got {outcome.code!r} ({outcome.message!r})"
    assert _changed(before, _rows(db_path)) == [], f"a refused registration must write nothing: {_changed(before, _rows(db_path))}"
    created = await _register(engine, _without_at(name), _address("newcomer"), None)
    assert isinstance(created, User), f"barrier: the same registration with the @ replaced must go through: {created!r}"
    print_success(f"refused as {USERNAME_INVALID}, the reworded message carried; {_without_at(name)!r} registered")


# =============================================================================
# A-47, WORKSTREAM E'S REVIEW (A-51 lot) — AN AccountError SURVIVES copy AND pickle
# =============================================================================

Duplicate = Callable[[Any], Any]


def _through_pickle(value: Any) -> Any:
    """``value`` dumped by ``pickle`` and loaded back, at the default protocol: what a cache, a queue or another process gets."""
    return pickle.loads(pickle.dumps(value))


#: The three ways a refusal is duplicated — each rebuilds a ``str`` subclass from its ``__getnewargs__``: (how, as a failure names it).
DUPLICATES = [
    pytest.param(copy.copy, "copy.copy", id="copy.copy"),
    pytest.param(copy.deepcopy, "copy.deepcopy", id="copy.deepcopy"),
    pytest.param(_through_pickle, "pickle.loads(pickle.dumps(…))", id="pickle-dumps-then-loads"),
]


# red until the A-47 review fix (A-51 lot)
@pytest.mark.asyncio
@pytest.mark.parametrize(("duplicate", "how"), DUPLICATES)
async def test_an_account_error_survives_copy_deepcopy_and_pickle(engine: AsyncEngine, duplicate: Duplicate, how: str) -> None:
    """UNAME-032 — A-47 as workstream E reviewed it: NEW, red until the A-47 review fix (A-51 lot) — today a ``TypeError``: ``copy.copy``, ``copy.deepcopy`` and ``pickle`` rebuild a ``str`` subclass from ``str.__getnewargs__``, which gives the message alone, and ``AccountError.__new__`` asks for ``(code, message)``. A real refusal of ``create_user`` — a username taken, in UNAME-030's scene: ``AccountError`` ``USERNAME_TAKEN``, «Username already taken» —, duplicated by ``copy.copy``, ``copy.deepcopy`` or ``pickle.loads(pickle.dumps(…))``, is an ``AccountError``, equal as a ``str`` to the original message, with the same ``code``. The refusal itself is asserted first: the test cannot pass by duplicating something else."""
    print_section(f"UNAME-032: {how} of a refusal of create_user")
    scene = await _scene(engine)
    user, refusal = await _create_a_taken_username(engine, scene)
    assert user is None and isinstance(refusal, user_service.AccountError) and (str(refusal), refusal.code) == (USERNAME_TAKEN_MESSAGE, "USERNAME_TAKEN"), f"setup: create_user of a taken username must answer (None, AccountError USERNAME_TAKEN), as in UNAME-030: {_shown((user, refusal))}"

    try:
        duplicated = duplicate(refusal)
    except TypeError as error:
        pytest.fail(f"red until the A-47 review fix (A-51 lot): {how} of the refusal raised TypeError: {error} — str.__getnewargs__ hands AccountError.__new__ the message alone, without its code: {_shown((None, refusal))}", pytrace=False)

    assert isinstance(duplicated, user_service.AccountError), f"{how} must give an AccountError: it gave a {type(duplicated).__module__}.{type(duplicated).__qualname__}, {duplicated!r}"
    assert isinstance(duplicated, str) and str(duplicated) == str(refusal) == USERNAME_TAKEN_MESSAGE, f"{how} must give the original message as a str, {USERNAME_TAKEN_MESSAGE!r}: {duplicated!r}"
    assert getattr(duplicated, "code", None) == refusal.code, f"{how} must keep the code {refusal.code!r}: {_shown((None, duplicated))}"
    print_success(f"{how}: an AccountError {refusal.code}, {str(duplicated)!r}")

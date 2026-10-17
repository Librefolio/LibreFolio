"""C-54, «What's new since your last version»: the release an account last saw, and whether the running one is newer (release 1.3, workstream A, lot C-54 — A11 of the plan; the coordinator's GO and its correction, 17/10).

Until C-54 ``users.last_seen_version`` (``VARCHAR(40) NULL``, migration 005, D-A12) exists and nothing reads or writes
it: an account learns nothing of an update — and on LibreFolio Cloud, where the operator updates the instance, nothing
else would tell it. The contract, pinned here where it does not go through HTTP (over HTTP:
``test_api/test_whats_new_api.py``, WN-API-…):

- ``backend/app/services/accounts/whats_new_service.py``, a new module:
  - ``release_of(version)``: the base release ``X.Y.Z`` of an app version string, or None. ``1.2.1`` and ``v1.2.1`` are
    ``1.2.1``; git describe's ``v1.3.0-7-gabc1234`` and ``v1.2.1-2106-gcd52e25fc-dirty`` are ``1.3.0`` and ``1.2.1``;
    ``v1.2.1-dirty`` is ``1.2.1``; a pre-release ``1.3.0-rc1`` is ``1.3.0``; ``1.3`` is ``1.3.0``; ``v1.10.0`` keeps its
    two digits. A bare hash — ``cd52e25fc``, ``cd52e25fc-dirty``, or digits only —, ``dev``, ``unknown`` (what
    ``get_git_version`` answers without git nor a VERSION file), ``""`` and None are None: a release has at least ``X.Y``.
    A base of ``0.0.0`` is None too: ``v0.0.0-gabc1234`` and ``v0.0.0-gabc1234-dirty`` — what ``get_git_version``
    reports for a checkout without a tag, git describe's bare hash prefixed with ``v0.0.0-g`` — and ``0.0.0``. Read as a
    release, it would be older than every release: a new account there would store it and later see every chapter.
  - ``current_release()``: ``release_of(backend.app.config.get_version())``, read through the config module AT EACH CALL.
    The tests patch ``backend.app.config.get_version``: a module that binds a ``get_version`` of its own at import is a
    setup failure, said; one that keeps an earlier answer is WN-002's red.
  - ``whats_new_disabled()``: the hidden switch ``LIBREFOLIO_DISABLE_WHATS_NEW`` — ``1``, ``true`` or ``yes`` in any case
    —, read at each call, as ``LIBREFOLIO_DISABLE_DONATION_POPUP`` is (``config.accounts.donation_popup_disabled``; D-A7:
    in the tests' documentation only). The lanes run with it: their accounts all have NULL.
  - ``pending_for(user)``: a plain function of the account. None when switched off, when the running release is unknown,
    or when ``user.last_seen_version`` is a release at least the running one — releases compare as numbers, ``1.9.0``
    before ``1.10.0``, a patch release newer —; otherwise an object with ``since``, the release of ``last_seen_version``
    — ``1.2.0`` for a stored ``v1.2.0-5-gabc1234``, not the string —, None when that is NULL (an account from before
    C-54: the running release's chapter only, decision (a)) or unreadable; and ``release``, the running release. It
    reads: it never marks anything seen.
  - ``await mark_seen(session, user)``: writes the running release into ``user.last_seen_version`` — never a value of
    the client: it takes none —, commits, and answers it; the running release unknown, it writes nothing and answers
    None. Idempotent. Whether it touches ``updated_at`` is the implementer's call: that column is set aside after a write.
- ``user_service.create_user`` writes ``last_seen_version = current_release()`` on every new account — every path that
  creates one goes through it, committing itself (``./dev.py user create``) or flushing for a caller that commits
  (registration, invitations, F02's administrator) —, so a new account never sees the modal; an unknown running release
  leaves NULL, never the raw version string.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the global settings the
startup seeds, opened as production opens its own (aiosqlite, NullPool, the PRAGMA listener of
``backend.app.db.session``), disposed at teardown; ``get_async_engine`` is a tripwire. The running version is
``backend.app.config.get_version`` patched through ``monkeypatch``: ``v1.3.0-7-gabc1234`` — git describe, seven commits
after the tag ``v1.3.0`` — unless a test says otherwise. The switch, and the accounts and email variables of the shell,
are removed; bcrypt runs at its lowest cost. The accounts of a scene are rows with a marker hash, each name and address
with a random tag. «Nothing written» is every row of every table, ``sqlite_sequence`` included, read by SQLite from the
file before and after; after a write, «nothing else» is the same comparison with ``users.last_seen_version`` and
``users.updated_at`` set aside, every account's ``last_seen_version`` compared on its own. Nothing waits.

The module is imported when a test runs, never at collection: until C-54 writes it, each test that calls it is red on
its own, at that call, naming the module — the rest of the file is collected and runs. NEW, red until C-54: WN-001 to
WN-007, WN-009 and WN-010; WN-007 at its first assertion, before it calls the module: today ``create_user`` leaves
``last_seen_version`` NULL. WN-008 is a GUARD, green today and to stay green: an unknown running release leaves NULL.

WN-001's three ``0.0.0`` cases — NEW, red until the C-54 fix for a checkout without a tag (found by the docs-writer
after C-54 entered): today ``release_of`` reads ``v0.0.0-gabc1234``, ``v0.0.0-gabc1234-dirty`` and ``0.0.0`` as
``0.0.0``, so ``create_user`` there would write ``last_seen_version = '0.0.0'``. Every other case of the file is green
with C-54.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app import config as app_config
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import User
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT'S VALUES — a different decision is an edit here
# =============================================================================

#: The module C-54 writes: imported when a test runs, never at collection.
WHATS_NEW_MODULE = "backend.app.services.accounts.whats_new_service"
#: The hidden switch (D-A7): the lanes run with it.
SWITCH = "LIBREFOLIO_DISABLE_WHATS_NEW"
#: The running version unless a test says otherwise — git describe, seven commits after the tag v1.3.0 — and its release.
RUNNING_VERSION = "v1.3.0-7-gabc1234"
RUNNING_RELEASE = "1.3.0"
#: A release before the running one — not the lane's own 1.2.1, so an unpatched version shows in a failure — and one after.
OLDER_RELEASE = "1.2.0"
NEWER_RELEASE = "1.4.0"
#: Running versions without a release: get_git_version's answer without git nor VERSION, a bare hash, a development build.
UNKNOWN_VERSIONS = [
    pytest.param("unknown", id="unknown"),
    pytest.param("cd52e25fc-dirty", id="a-bare-hash-dirty"),
    pytest.param("dev", id="dev"),
]
#: The last_seen_version of an account behind the running release: NULL — from before C-54 — or an older release.
BEHIND = [pytest.param(None, id="null-from-before-c54"), pytest.param(OLDER_RELEASE, id="an-older-release")]

#: (an app version string, its base release X.Y.Z or None): a release has at least X.Y, so a hash never is one; and a base
#: of 0.0.0 is none, so a checkout without a tag never stores a release older than every release.
RELEASES = [
    pytest.param("1.2.1", "1.2.1", id="a-release"),
    pytest.param("v1.2.1", "1.2.1", id="a-tag"),
    pytest.param("v1.3.0-7-gabc1234", "1.3.0", id="git-describe"),
    pytest.param("v1.2.1-2106-gcd52e25fc-dirty", "1.2.1", id="git-describe-dirty"),
    pytest.param("v1.2.1-dirty", "1.2.1", id="a-tag-dirty"),
    pytest.param("1.3.0-rc1", "1.3.0", id="a-pre-release"),
    pytest.param("1.3", "1.3.0", id="two-parts"),
    pytest.param("v1.10.0", "1.10.0", id="a-two-digit-minor"),
    pytest.param("cd52e25fc", None, id="a-bare-hash"),
    pytest.param("cd52e25fc-dirty", None, id="a-bare-hash-dirty"),
    pytest.param("2106123", None, id="a-bare-hash-of-digits-only"),
    # A checkout without a tag: get_git_version turns git describe's bare hash into v0.0.0-g<hash>, -dirty kept.
    pytest.param("v0.0.0-gabc1234", None, id="zero-base-untagged-checkout"),
    pytest.param("v0.0.0-gabc1234-dirty", None, id="zero-base-untagged-checkout-dirty"),
    pytest.param("0.0.0", None, id="zero-base-0.0.0"),
    pytest.param("dev", None, id="dev"),
    pytest.param("unknown", None, id="unknown"),
    pytest.param("", None, id="empty"),
    pytest.param(None, None, id="None"),
]

#: The running versions WN-002 goes through, one after the other, and the release each gives: read at each call.
VERSIONS_IN_TURN = [(RUNNING_VERSION, RUNNING_RELEASE), ("v1.2.1", "1.2.1"), ("unknown", None), ("v1.2.1-2106-gcd52e25fc-dirty", "1.2.1")]

#: (LIBREFOLIO_DISABLE_WHATS_NEW, None for unset; whether whats-new is off): 1, true or yes in any case, nothing else.
SWITCH_VALUES = [
    pytest.param(None, False, id="unset"),
    pytest.param("", False, id="blank"),
    pytest.param("0", False, id="0"),
    pytest.param("false", False, id="false"),
    pytest.param("1", True, id="1"),
    pytest.param("TRUE", True, id="TRUE"),
    pytest.param("yes", True, id="yes"),
]

#: What pending_for says, as (since, release), or None: nothing new to see.
Pending = Optional[tuple[Optional[str], str]]

#: (the running version, an account's last_seen_version as stored, what pending_for says): the matrix of WN-004.
PENDING = [
    pytest.param(RUNNING_VERSION, RUNNING_RELEASE, None, id="saw-the-running-release"),
    pytest.param(RUNNING_VERSION, "v1.3.0-2-gdeadbee", None, id="saw-the-running-release-written-as-git-describe"),
    pytest.param(RUNNING_VERSION, OLDER_RELEASE, (OLDER_RELEASE, RUNNING_RELEASE), id="saw-an-older-release"),
    pytest.param(RUNNING_VERSION, "v1.2.0-5-gabc1234", ("1.2.0", RUNNING_RELEASE), id="saw-an-older-release-written-as-git-describe"),
    pytest.param(RUNNING_VERSION, None, (None, RUNNING_RELEASE), id="null-from-before-c54"),
    pytest.param(RUNNING_VERSION, "not-a-version", (None, RUNNING_RELEASE), id="garbage"),
    pytest.param(RUNNING_VERSION, "cd52e25fc", (None, RUNNING_RELEASE), id="a-bare-hash"),
    pytest.param(RUNNING_VERSION, NEWER_RELEASE, None, id="saw-a-newer-release-a-downgrade"),
    pytest.param("v1.3.1", RUNNING_RELEASE, (RUNNING_RELEASE, "1.3.1"), id="a-patch-release-is-newer"),
    pytest.param("v1.10.0", "1.9.0", ("1.9.0", "1.10.0"), id="1.9-is-before-1.10"),
    pytest.param("v1.9.0", "1.10.0", None, id="1.10-is-after-1.9-a-downgrade"),
]

#: A write's «nothing else»: these columns set aside — the one written, and updated_at, the implementer's call.
UPDATED_AT = "users.updated_at"
MARKED = ("users.last_seen_version", UPDATED_AT)
#: What the accounts written as rows hold for a hash: nobody signs in here. create_user's password: it hashes any.
MARKER_HASH = "$argon2id$whats-new-marker"
PASSWORD = "Whats-New-Service-2026!"
#: Removed before every test: the switch, and what changes what an account's creation decides.
INHERITED_PREFIXES = ("LIBREFOLIO_ADMIN_", "LIBREFOLIO_SMTP_")
INHERITED_VARIABLES = (SWITCH, "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL", "LIBREFOLIO_BLOCKED")


# =============================================================================
# THE MODULE UNDER TEST, THE RUNNING VERSION, THE SWITCH
# =============================================================================


def _module() -> ModuleType:
    """The module C-54 writes, imported when a test runs and never at collection: until it exists, the test that calls it
    fails on its own, naming it. A module that exists but fails to import raises as it does."""
    try:
        return importlib.import_module(WHATS_NEW_MODULE)
    except ModuleNotFoundError as error:
        if error.name != WHATS_NEW_MODULE:
            raise
        pytest.fail(f"red until C-54: {WHATS_NEW_MODULE} does not exist yet", pytrace=False)


def _whats_new(name: str) -> Callable[..., Any]:
    """``name`` of the module C-54 writes: the test that needs it fails naming the module, or the name, until both exist."""
    function = getattr(_module(), name, None)
    if not callable(function):
        pytest.fail(f"red until C-54: {WHATS_NEW_MODULE} has no {name}", pytrace=False)
    return function


def _reading_the_running_version(name: str) -> Callable[..., Any]:
    """``_whats_new(name)`` for a function that reads the running version: the module must read it through
    ``backend.app.config.get_version`` at each call — where the tests patch it —, so a ``get_version`` of its own, bound
    at import, is a setup failure, said, rather than a wrong release blamed on the rule."""
    function = _whats_new(name)
    bound = getattr(_module(), "get_version", None)
    if bound is not None and bound is not app_config.get_version:
        pytest.fail(f"setup: {WHATS_NEW_MODULE} holds a get_version of its own, bound at import: it must read backend.app.config.get_version at each call, where the tests set the running version", pytrace=False)
    return function


def _run_as(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    """``backend.app.config.get_version`` answers ``version`` from now on, in this test: the running version."""
    monkeypatch.setattr(app_config, "get_version", lambda: version)


def _set_switch(monkeypatch: pytest.MonkeyPatch, value: Optional[str]) -> None:
    """``LIBREFOLIO_DISABLE_WHATS_NEW`` set to ``value``, or removed for None."""
    if value is None:
        monkeypatch.delenv(SWITCH, raising=False)
    else:
        monkeypatch.setenv(SWITCH, value)


def _pending(user: User) -> Pending:
    """``pending_for(user)`` as ``(since, release)``, or None: what the answers' ``user.whats_new`` will carry. A plain
    function of the account, as the contract writes it: an awaitable, or an answer without ``since`` and ``release``, is a
    failure, said."""
    answer = _reading_the_running_version("pending_for")(user)
    if inspect.isawaitable(answer):
        if inspect.iscoroutine(answer):
            answer.close()
        pytest.fail("pending_for(user) must be a plain function of the account, as the contract writes it: it answered an awaitable", pytrace=False)
    if answer is None:
        return None
    if not (hasattr(answer, "since") and hasattr(answer, "release")):
        pytest.fail(f"pending_for(user) must answer None or an object with since and release: it answered {answer!r}", pytrace=False)
    return answer.since, answer.release


def _said(pending: Pending) -> str:
    """What ``pending_for`` says, as a failure tells it."""
    return "None, nothing new to see" if pending is None else f"since {pending[0]!r}, release {pending[1]!r}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the switch, accounts and email variables of the shell that started the run: the lanes set the switch."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def running_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """The running version is ``RUNNING_VERSION`` unless the test says otherwise (``_run_as``): never the checkout's own."""
    _run_as(monkeypatch, RUNNING_VERSION)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at its lowest cost in this process: ``create_user`` hashes a real password, a hundred times cheaper."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises — in the session module, and in the modules that import it by name and open sessions of their own."""
    for module in (db_session, email_flows, email_verification):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=False)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "whats-new.db"


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


# =============================================================================
# HELPERS — the database, read by SQLite, and the accounts as rows
# =============================================================================

Rows = dict[str, list[tuple[Any, ...]]]


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _address(prefix: str) -> str:
    """An address nobody has: ``prefix``, a tag of its own, at ``example.com``."""
    return f"{prefix}.{_tag()}@example.com"


def _rows(db_path: Path, ignoring: tuple[str, ...] = ()) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, read by SQLite from the file: what «nothing written»
    compares. A column named in ``ignoring``, as ``table.column``, reads NULL in every row."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: _table_rows(conn, table, ignoring) for table in tables}


def _table_rows(conn: sqlite3.Connection, table: str, ignoring: tuple[str, ...]) -> list[tuple[Any, ...]]:
    columns = [info[1] for info in conn.execute(f'PRAGMA table_info("{table}")')]
    selected = ", ".join("NULL" if f"{table}.{column}" in ignoring else f'"{column}"' for column in columns)
    return sorted(conn.execute(f'SELECT {selected} FROM "{table}"').fetchall(), key=repr)


def _changed(before: Rows, after: Rows) -> list[str]:
    """The tables whose rows differ between ``before`` and ``after``."""
    return sorted(table for table in set(before) | set(after) if before.get(table) != after.get(table))


def _last_seen(db_path: Path) -> dict[int, Optional[str]]:
    """Every account's ``last_seen_version``, by id, read by SQLite from the file: only what was committed."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        return dict(conn.execute("SELECT id, last_seen_version FROM users").fetchall())


async def _add_account(engine: AsyncEngine, *, last_seen_version: Optional[str]) -> int:
    """An account written as a row and committed before anything under test runs — as an install from before C-54 holds
    one (NULL), or as the scene needs it —, a fresh name and address, a marker hash. Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"member_{_tag()}", email=_address("member"), hashed_password=MARKER_HASH, last_seen_version=last_seen_version)
        session.add(user)
        await session.commit()
        return user.id


async def _user(engine: AsyncEngine, user_id: int) -> User:
    """The account ``user_id`` as a route has it: read in a fresh session, every column loaded."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"setup: account #{user_id} exists"
    return user


async def _create(engine: AsyncEngine, commit: bool = True) -> int:
    """``user_service.create_user`` of a fresh name and address with ``commit`` — the caller committing after it when it
    does not, as registration and F02 do —: the new account's id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user, error = await user_service.create_user(session, f"newcomer_{_tag()}", _address("newcomer"), PASSWORD, commit=commit)
        if not commit:
            await session.commit()
    assert user is not None and error is None, f"setup: create_user of a fresh name and address must create the account: {error!r}"
    return user.id


@dataclass(frozen=True)
class MarkSeen:
    """What ``mark_seen`` did: its answer; ``last_seen_version`` on the caller's object after it; and every account's
    ``last_seen_version`` in the file — only what was committed — before the caller commits anything."""

    answer: Any
    on_the_object: Optional[str]
    committed: dict[int, Optional[str]]


async def _mark_seen(engine: AsyncEngine, db_path: Path, user_id: int) -> MarkSeen:
    """``await mark_seen(session, user)`` as ``POST /auth/whats-new/seen`` calls it, the account loaded in that session;
    the file read by SQLite before the session ends; then the session committed, as a careless caller would, so a write
    ``mark_seen`` left pending shows too."""
    mark_seen = _reading_the_running_version("mark_seen")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        assert user is not None, f"setup: account #{user_id} exists"
        call = mark_seen(session, user)
        if not inspect.isawaitable(call):
            pytest.fail(f"mark_seen(session, user) must be awaited, as the contract writes it: it answered {call!r}", pytrace=False)
        answer = await call
        committed = _last_seen(db_path)
        await session.commit()
    return MarkSeen(answer=answer, on_the_object=user.last_seen_version, committed=committed)


# =============================================================================
# THE RELEASE — release_of, current_release
# =============================================================================


# NEW — red until C-54; its three 0.0.0 cases red until the fix for a checkout without a tag
@pytest.mark.parametrize(("version", "release"), RELEASES)
def test_release_of_is_the_base_release_of_a_version(version: Optional[str], release: Optional[str]) -> None:
    """WN-001 — C-54, NEW, red until C-54 (the module does not exist): ``release_of(version)`` is the base release ``X.Y.Z`` of an app version string — ``1.2.1`` and ``v1.2.1``; git describe's ``v1.3.0-7-gabc1234`` and ``v1.2.1-2106-gcd52e25fc-dirty``; ``v1.2.1-dirty``; the pre-release ``1.3.0-rc1`` as ``1.3.0``; ``1.3`` as ``1.3.0``; ``v1.10.0`` with its two digits — and None for what holds no release: a bare hash of letters and digits or of digits only, dirty or not, ``dev``, ``unknown`` (``get_git_version`` without git nor VERSION), ``""`` and None. A release has at least ``X.Y``. A base of ``0.0.0`` is no release either — red until the fix for a checkout without a tag (today ``0.0.0``) —: ``v0.0.0-gabc1234`` and ``v0.0.0-gabc1234-dirty``, which ``get_git_version`` reports for such a checkout, and ``0.0.0``."""
    release_of = _whats_new("release_of")

    answer = release_of(version)

    assert answer == release, f"release_of({version!r}) must be {release!r}: got {answer!r}"


# NEW — red until C-54
def test_current_release_reads_get_version_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """WN-002 — C-54, NEW, red until C-54: ``current_release()`` is ``release_of(backend.app.config.get_version())``, read through the config module at each call: ``get_version`` answering ``v1.3.0-7-gabc1234``, then ``v1.2.1``, then ``unknown``, then git describe's ``v1.2.1-2106-gcd52e25fc-dirty``, it answers ``1.3.0``, ``1.2.1``, None, ``1.2.1`` — no answer kept from an earlier call; a ``get_version`` of the module's own, bound at import, is a setup failure, said."""
    print_section("WN-002: current_release follows backend.app.config.get_version at each call")
    current_release = _reading_the_running_version("current_release")
    answers = []

    for version, _release in VERSIONS_IN_TURN:
        _run_as(monkeypatch, version)
        answers.append(current_release())

    expected = [release for _version, release in VERSIONS_IN_TURN]
    assert answers == expected, f"current_release() must follow backend.app.config.get_version at each call — {[version for version, _release in VERSIONS_IN_TURN]} — and answer {expected}: got {answers}"
    print_success(f"current_release(): {answers}")


# =============================================================================
# THE SWITCH — whats_new_disabled
# =============================================================================


# NEW — red until C-54
@pytest.mark.parametrize(("value", "off"), SWITCH_VALUES)
def test_whats_new_disabled_reads_its_switch_at_each_call(monkeypatch: pytest.MonkeyPatch, value: Optional[str], off: bool) -> None:
    """WN-003 — C-54, NEW, red until C-54: ``whats_new_disabled()`` is True when ``LIBREFOLIO_DISABLE_WHATS_NEW`` is ``1``, ``true`` or ``yes`` in any case — ``1``, ``TRUE``, ``yes`` here —, and False when it is unset, blank, ``0`` or ``false``: as ``LIBREFOLIO_DISABLE_DONATION_POPUP``. A ``bool``. Barrier, at each call: the variable turned the other way — ``1`` where it was off, removed where it was on —, the answer turns with it."""
    whats_new_disabled = _whats_new("whats_new_disabled")
    _set_switch(monkeypatch, value)

    answer = whats_new_disabled()

    assert answer is off, f"{SWITCH}={value!r}: whats_new_disabled() must be {off}: got {answer!r}"
    _set_switch(monkeypatch, None if off else "1")
    assert whats_new_disabled() is (not off), f"barrier: {SWITCH} turned the other way, whats_new_disabled() must read it again at this call and answer {not off}"


# =============================================================================
# WHO HAS SOMETHING NEW TO SEE — pending_for
# =============================================================================


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize(("version", "stored", "expected"), PENDING)
async def test_pending_for_compares_the_release_last_seen_with_the_running_one(engine: AsyncEngine, db_path: Path, monkeypatch: pytest.MonkeyPatch, version: str, stored: Optional[str], expected: Pending) -> None:
    """WN-004 — C-54, NEW, red until C-54: an account written as a row with ``last_seen_version`` ``stored``, the running version ``version``. ``pending_for(user)`` is None when ``stored`` is a release at least the running one — the running release, written as such or as git describe; a newer release, a downgrade —; otherwise ``since`` and ``release``: ``since`` the release of ``stored`` — ``1.2.0`` for ``v1.2.0-5-gabc1234``, not the string —, None when it is NULL (an account from before C-54) or unreadable (``not-a-version``, a bare hash); ``release`` the running release. Releases compare as numbers: a patch release is newer, ``1.9.0`` comes before ``1.10.0``. It reads: the account's ``last_seen_version`` is as it was after it."""
    _run_as(monkeypatch, version)
    member = await _add_account(engine, last_seen_version=stored)
    assert _last_seen(db_path)[member] == stored, f"setup: the row holds last_seen_version {stored!r} as written"
    user = await _user(engine, member)

    pending = _pending(user)

    assert pending == expected, f"running {version!r}, last_seen_version {stored!r}: pending_for must say {_said(expected)}; it says {_said(pending)}"
    assert user.last_seen_version == stored, f"pending_for reads, it marks nothing seen: last_seen_version {stored!r} became {user.last_seen_version!r}"


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("stored", BEHIND)
@pytest.mark.parametrize("version", UNKNOWN_VERSIONS)
async def test_pending_for_is_none_while_the_running_release_is_unknown(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, version: str, stored: Optional[str]) -> None:
    """WN-005 — C-54, NEW, red until C-54: the running version holds no release — ``unknown``, a bare hash, ``dev`` —: ``pending_for`` is None for an account written as a row with NULL, and for one with an older release: nothing says what is running, so nothing is new. Barrier: the same account under ``v1.3.0-7-gabc1234`` has something new, ``since`` its own release — the None was the unknown release's."""
    _run_as(monkeypatch, version)
    user = await _user(engine, await _add_account(engine, last_seen_version=stored))

    pending = _pending(user)

    assert pending is None, f"running {version!r}, which holds no release, last_seen_version {stored!r}: pending_for must say None; it says {_said(pending)}"
    _run_as(monkeypatch, RUNNING_VERSION)
    assert _pending(user) == (stored, RUNNING_RELEASE), f"barrier: running {RUNNING_VERSION!r}, the same account has something new since {stored!r}: pending_for says {_said(_pending(user))}"


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("stored", BEHIND)
async def test_pending_for_is_none_when_switched_off(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, stored: Optional[str]) -> None:
    """WN-006 — C-54, NEW, red until C-54: ``LIBREFOLIO_DISABLE_WHATS_NEW=1`` — the lanes, whose accounts all have NULL —: ``pending_for`` is None for an account written as a row with NULL, and for one with an older release. Barrier: the variable removed, the same account has something new, ``since`` its own release — the None was the switch's."""
    user = await _user(engine, await _add_account(engine, last_seen_version=stored))
    _set_switch(monkeypatch, "1")

    pending = _pending(user)

    assert pending is None, f"{SWITCH}=1, last_seen_version {stored!r}: pending_for must say None; it says {_said(pending)}"
    _set_switch(monkeypatch, None)
    assert _pending(user) == (stored, RUNNING_RELEASE), f"barrier: {SWITCH} removed, the same account has something new since {stored!r}: pending_for says {_said(_pending(user))}"


# =============================================================================
# A NEW ACCOUNT — user_service.create_user
# =============================================================================


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [pytest.param(True, id="create_user-commits"), pytest.param(False, id="the-caller-commits")])
async def test_create_user_writes_the_running_release(engine: AsyncEngine, db_path: Path, commit: bool) -> None:
    """WN-007 — C-54, NEW, red until C-54 (today the row holds NULL): ``user_service.create_user`` — committing itself, as ``./dev.py user create`` calls it, or flushing for a caller that commits, as registration, invitations and F02 do — writes the running release, ``1.3.0`` under ``v1.3.0-7-gabc1234``, into the new account's ``last_seen_version``: the committed row holds it. So a new account never sees the modal: ``pending_for`` of the account read back is None."""
    print_section(f"WN-007: create_user ({'commit' if commit else 'the caller commits'}) writes the running release")
    user_id = await _create(engine, commit)

    stored = _last_seen(db_path)[user_id]

    assert stored == RUNNING_RELEASE, f"red until C-54: create_user must write the running release {RUNNING_RELEASE!r} ({RUNNING_VERSION!r}) into the new account's last_seen_version: the committed row holds {stored!r}"
    pending = _pending(await _user(engine, user_id))
    assert pending is None, f"a new account has nothing new to see: pending_for says {_said(pending)}"
    print_success(f"account #{user_id}: last_seen_version {stored!r}, nothing new to see")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("version", UNKNOWN_VERSIONS)
async def test_create_user_leaves_null_while_the_running_release_is_unknown(engine: AsyncEngine, db_path: Path, monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    """WN-008 — C-54, GUARD (green today; red if C-54 writes what is not a release): the running version holds no release — ``unknown``, a bare hash, ``dev`` —: ``create_user`` creates the account with ``last_seen_version`` NULL, never the raw version string."""
    _run_as(monkeypatch, version)

    user_id = await _create(engine)

    stored = _last_seen(db_path)[user_id]
    assert stored is None, f"running {version!r}, which holds no release: create_user must leave last_seen_version NULL: the row holds {stored!r}"


# =============================================================================
# SEEN — mark_seen
# =============================================================================


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("stored", BEHIND)
async def test_mark_seen_commits_the_running_release_once(engine: AsyncEngine, db_path: Path, stored: Optional[str]) -> None:
    """WN-009 — C-54, NEW, red until C-54: an account with ``last_seen_version`` NULL or an older release, and another account with NULL, written as rows. ``await mark_seen(session, user)``, the account loaded in that session as the route has it, answers the running release ``1.3.0`` and writes it — committed by ``mark_seen`` itself: the file holds it before the caller commits anything —; the caller's object holds it; nothing else is written — the other account's NULL, every other column and table, ``updated_at`` aside (the implementer's call) —; ``pending_for`` of the account read back is None. Again — idempotent —: it answers ``1.3.0`` and nothing changes, ``updated_at`` aside."""
    print_section(f"WN-009: mark_seen of an account with last_seen_version {stored!r}")
    member = await _add_account(engine, last_seen_version=stored)
    await _add_account(engine, last_seen_version=None)
    seen_before, rows_before = _last_seen(db_path), _rows(db_path, ignoring=MARKED)

    first = await _mark_seen(engine, db_path, member)

    assert first.answer == RUNNING_RELEASE, f"mark_seen must answer the running release {RUNNING_RELEASE!r}: got {first.answer!r}"
    assert first.committed == {**seen_before, member: RUNNING_RELEASE}, f"mark_seen must commit {RUNNING_RELEASE!r} into account #{member}'s last_seen_version, and nobody else's: before {seen_before}, the file holds {first.committed} before the caller commits"
    assert first.on_the_object == RUNNING_RELEASE, f"the caller's object must hold the release written: {first.on_the_object!r}"
    assert _changed(rows_before, _rows(db_path, ignoring=MARKED)) == [], f"mark_seen writes last_seen_version and nothing else (updated_at aside): {_changed(rows_before, _rows(db_path, ignoring=MARKED))}"
    pending = _pending(await _user(engine, member))
    assert pending is None, f"marked seen, the account has nothing new to see: pending_for says {_said(pending)}"
    rows_seen = _rows(db_path, ignoring=(UPDATED_AT,))
    second = await _mark_seen(engine, db_path, member)
    assert second.answer == RUNNING_RELEASE, f"idempotent: a second mark_seen must answer {RUNNING_RELEASE!r} again: got {second.answer!r}"
    assert _changed(rows_seen, _rows(db_path, ignoring=(UPDATED_AT,))) == [], f"idempotent: a second mark_seen changes nothing (updated_at aside): {_changed(rows_seen, _rows(db_path, ignoring=(UPDATED_AT,)))}"
    print_success(f"account #{member}: {stored!r} → {RUNNING_RELEASE!r}, committed once")


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("version", UNKNOWN_VERSIONS)
async def test_mark_seen_writes_nothing_while_the_running_release_is_unknown(engine: AsyncEngine, db_path: Path, monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    """WN-010 — C-54, NEW, red until C-54: the running version holds no release — ``unknown``, a bare hash, ``dev`` —, an account with an older release written as a row: ``mark_seen`` answers None and writes nothing — every row of every table as it was, ``updated_at`` included, even once the caller commits —; the caller's object keeps the older release."""
    _run_as(monkeypatch, version)
    member = await _add_account(engine, last_seen_version=OLDER_RELEASE)
    before = _rows(db_path)

    outcome = await _mark_seen(engine, db_path, member)

    assert outcome.answer is None, f"running {version!r}, which holds no release: mark_seen must answer None: got {outcome.answer!r}"
    assert _changed(before, _rows(db_path)) == [], f"running {version!r}: mark_seen must write nothing, even once the caller commits: {_changed(before, _rows(db_path))}"
    assert outcome.on_the_object == OLDER_RELEASE, f"the caller's object must keep {OLDER_RELEASE!r}: {outcome.on_the_object!r}"

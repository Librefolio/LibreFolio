"""
The owner's account after a restore in the ``managed`` profile (workstream B, lot B5-1, interface ``B-b51-interface.md``
§0 and §4): ``backend/app/services/platform/instance_backup/owner.py`` (new). Selector: ``services backup-owner``.

Written RED, before B5-1: ``owner.py`` does not exist. It is imported by the fixture ``owner`` that every test asks for,
which fails the test (``pytest.fail``, never a skip) with the ``ImportError``: the whole suite is red until it lands.

(a) ``owner_choice_required()``: whether the profile read now (``get_settings().LIBREFOLIO_PROFILE``) is ``managed``.
(b) ``assign_restored_owner(data_dir=None) -> RestoreState | None``, the startup step ``restore-owner`` after
    ``restore-commit``, never raising. It does nothing — returns ``None``, A's function never called, ``restore.json``
    byte for byte — unless the state is ``committed``, confirmed via ``admin``, with an ``owner_user_id`` and no
    ``owner_outcome`` yet: no state; a phase before or after (pending, applying, applied, rolling back, rolled back);
    confirmed via ``cli`` or ``panel`` (an owner id written there all the same); no owner id; an outcome already
    recorded (a second call after a first one, too). Otherwise A's ``assign_owner_and_send_reset(session, user_id)`` is
    called once, with the owner's id and an ``AsyncSession`` on the data directory's database (``expire_on_commit``
    off) and nothing else (no ``since``, no ``now``): the fake reads the owner's row through it. What it answers is
    recorded in ``restore.json`` and in the state returned: ``owner_outcome`` the outcome's value (``sent`` or
    ``link_only``). The state has no ``owner_reset_path`` (R13 security review): A writes the link in the instance log
    itself, so a stray ``reset_path`` on the result (the canary) is never read, copied, logged or stored.
    ``OwnerAssignmentError`` (each of A's four codes): ``owner_outcome`` ``error:<CODE>``. Any other exception: logged,
    nothing recorded, the state still waiting for the next start (which calls A again and records what A answers),
    nothing raised. ``_assign_owner()`` raising ``ImportError`` (A not merged): an error logged, nothing recorded,
    nothing raised. Without arguments, the configured data directory.
(c) The log: no line of any of these calls holds the owner's email, its username, the link, or the text of an
    unexpected exception (its type only).
(d) Security addendum §7.3 (written RED before it): the step takes a non-blocking exclusive ``flock`` on
    ``.restore/owner.lock`` (created 0600) before calling A and until the outcome is recorded; a worker that cannot take
    it returns ``None`` without calling A. Two workers at once (two tasks; A's first call held until one returns): A
    called once. The lock held by the test (``fcntl.flock`` on a descriptor of its own): ``None``, A not called.
(e) Security addendum §7.4 (written RED before it): ``apply.owner_assignment_problem(data_dir=None)``, the hook of H's
    guard: ``"pending"`` for a committed restore confirmed via ``admin`` with an owner and no outcome, the code of an
    ``error:<CODE>``, ``None`` otherwise — and for a state that cannot be read (``restore_state_problem``'s); never
    raises.
(f) B5-1b (interface §9.1, written RED before it): the way out of a terminal ``error:<CODE>``. ``owner.held_owner_lock(
    data_dir)``: a context manager yielding ``True`` when it took the non-blocking exclusive ``flock`` on
    ``.restore/owner.lock`` (same file, mode 0600), ``False`` when another process holds it (never raising for that),
    released at the end however the block ended. ``apply.reset_owner_assignment(data_dir=None) -> bool``: for a committed
    restore confirmed via ``admin`` with an owner and an ``owner_outcome`` starting ``error:``, clears ``owner_outcome``
    (nothing else: the state has no ``owner_reset_path`` key before nor after) and answers whether a server serves the
    data directory; any other state
    (none, no ``.restore``, a phase before or after, ``cli``/``panel``, no owner, no outcome, an outcome of A) raises
    ``RestoreOwnerNotFailedError`` (code ``owner_not_failed``) and writes nothing — so a second call does too; the owner
    lock held elsewhere raises ``RestoreInUseError``; an unreadable state propagates ``RestoreStateUnreadableError``.
    Afterwards ``owner_assignment_problem`` is ``"pending"`` and the startup step calls A again. One log line (stage,
    user id, the code reset), never an address, a name or a link.

(g) B5-1j (analysis ``B-5-1j-analisi-titolare-nel-restore-cli.md`` §6; written RED before it): the filters ``confirmed_via !=
    "admin"`` are gone. (b), (e) and (f) above now hold for a restore confirmed via ``cli`` or ``panel`` as for the app's:
    the step ``restore-owner`` gives the account picked at the confirmation (``assign_restored_owner``), ``owner_pending``
    answers its stage and account, ``owner_assignment_problem`` is ``pending`` / the code of an ``error:``, and
    ``reset_owner_assignment`` clears such an error. A restore with NOBODY picked (``owner_user_id`` ``None``,
    ``owner_outcome`` ``"none"`` recorded at the confirmation) is left alone by all of them.

How. A's signature (``backend.app.services.accounts.instance_owner.assign_owner_and_send_reset(session, user_id, *,
now=None) -> OwnerResetResult``) is played by the fakes of this module: ``FakeOutcome`` (a ``StrEnum`` of A's two
values), ``FakeResult`` (A's frozen dataclass ``OwnerResetResult``: ``outcome``, ``user_id``, ``username``, ``email``,
``expires_at``; for ``link_only`` a subclass that carries a stray ``reset_path`` canary) and ``FakeOwnerAssignmentError``
(an ``Exception`` with A's ``code``). ``owner.py`` looks A's function up through ``owner._assign_owner()``, a function of
no argument that returns the pair ``(assign_owner_and_send_reset, OwnerAssignmentError)`` — it imports
``backend.app.services.accounts.instance_owner`` lazily —; every test replaces it with one that returns a ``FakeA`` (an
async callable recording each call) and ``FakeOwnerAssignmentError``, or raises ``ImportError``.

The data directory of a test is under ``tmp_path``: a copy of ``test_backup_staging.py``'s database at the head (made
once for the module by ``alembic upgrade`` in a process of its own) holding the owner's account, and ``.restore/
restore.json`` written as raw JSON (the owner's keys included, so the file is the same before and after B5-1). This
process is in test mode with that folder as its test data directory (``LIBREFOLIO_TEST_DATA_DIR``), so that
``get_async_engine()`` opens it; its module singleton ``db.session.async_engine`` is emptied for the test (the engine the
test made disposed at its end, the one before put back). The profile is ``managed``, ``LIBREFOLIO_ADMIN_EMAIL`` the
owner's. Logs are read with ``structlog.testing.capture_logs`` behind a barrier. Pure: no lane database, no server, no
network, no email.
"""

from __future__ import annotations

import asyncio
import fcntl
import importlib
import inspect
import json
import os
import shutil
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.db import session as db_session
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, ensure_private_dir, restore_dir, restore_state_path
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixture of test_backup_staging.py: the real database at the head, made once by alembic.
databases = cases.databases

OWNER_MODULE = "backend.app.services.platform.instance_backup.owner"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
OWNER_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
OWNER_SIDE_VARIABLES = ("LIBREFOLIO_ADMIN_USERNAME", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE")
#: The owner's email (the operator's) and the account the owner chose, as the restored database holds it.
OWNER_EMAIL = "owner.b51@example.com"
OWNER_USERNAME = "b51_chosen_owner"
#: A stray ``reset_path`` on the result of ``link_only``: the code must never read it, so it is in no file, no state, no
#: log line. (A writes the real link in the instance log itself; this module proves the restore never touches one.)
LINK_CANARY = "/reset-password#token=b51-canary-token-never-anywhere-0123456789"
#: The text of an unexpected failure of A's function: only its type may be logged.
UNEXPECTED_TEXT = "b51 unexpected failure text that must not reach the log"
STAGE_ID = "0123456789abcdef0123456789abcdef"
CONFIRMED_AT = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
FINISHED_AT = CONFIRMED_AT + timedelta(minutes=5)
#: A's codes of ``OwnerAssignmentError``.
ASSIGNMENT_CODES = ("NOT_MANAGED", "OWNER_EMAIL_NOT_SET", "USER_NOT_FOUND", "EMAIL_TAKEN")
LOG_CANARY = "b51 owner test: a canary through a logger of owner's name"


# =============================================================================
# A's signature, played
# =============================================================================


class FakeOutcome(StrEnum):
    """A's ``OwnerResetOutcome``: only these two since the R13 security review."""

    SENT = "sent"
    LINK_ONLY = "link_only"


@dataclass(frozen=True)
class FakeResult:
    """A's ``OwnerResetResult``."""

    outcome: FakeOutcome
    user_id: int
    username: str
    email: str
    expires_at: datetime | None


@dataclass(frozen=True)
class LeakyResult(FakeResult):
    """A result that carries, besides A's fields, a ``reset_path``: the canary the restore must never read."""

    reset_path: str = LINK_CANARY


class FakeOwnerAssignmentError(Exception):
    """A's ``OwnerAssignmentError``: raised for a missing precondition, its ``code`` one of ``ASSIGNMENT_CODES``. Its
    message names the owner's email, as a careless one could: it must never reach the log."""

    def __init__(self, code: str) -> None:
        super().__init__(f"the owner {OWNER_EMAIL} cannot be assigned: {code}")
        self.code = code


@dataclass
class FakeA:
    """A's ``assign_owner_and_send_reset(session, user_id, *, now=None)``: each call recorded with what its session showed
    (its type, whether it expires on commit, the username of the row ``user_id`` in its database) and the ``now`` it was
    given (the restore passes none), then ``outcome`` answered or ``raises`` raised. A ``since=`` is a ``TypeError``,
    as for the real function."""

    outcome: FakeOutcome | None = None
    raises: BaseException | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, session: Any, user_id: int, *, now: datetime | None = None) -> FakeResult:
        row = (await session.execute(text("SELECT username FROM users WHERE id = :id"), {"id": user_id})).first()
        sync = getattr(session, "sync_session", None)
        self.calls.append({"user_id": user_id, "async_session": isinstance(session, AsyncSession), "expire_on_commit": getattr(sync, "expire_on_commit", None), "username": row[0] if row else None, "now": now})
        if self.raises is not None:
            raise self.raises
        assert self.outcome is not None, "a FakeA answers an outcome or raises"
        result_type = LeakyResult if self.outcome is FakeOutcome.LINK_ONLY else FakeResult
        return result_type(outcome=self.outcome, user_id=user_id, username=OWNER_USERNAME, email=OWNER_EMAIL, expires_at=FINISHED_AT + timedelta(days=3))


def use_fake(monkeypatch: pytest.MonkeyPatch, owner: ModuleType, fake: FakeA) -> None:
    """``owner._assign_owner`` replaced: it returns the pair ``(fake, FakeOwnerAssignmentError)``, as the real one
    returns ``(instance_owner.assign_owner_and_send_reset, instance_owner.OwnerAssignmentError)``."""
    assert callable(getattr(owner, "_assign_owner", None)), "[new] B5-1: owner._assign_owner() is the lazy lookup of A's function (interface §4)"
    monkeypatch.setattr(owner, "_assign_owner", lambda: (fake, FakeOwnerAssignmentError))


def a_not_merged(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> list[str]:
    """``owner._assign_owner`` raising ``ImportError``, as the lazy import does while A's code is not merged; the calls."""
    assert callable(getattr(owner, "_assign_owner", None)), "[new] B5-1: owner._assign_owner() is the lazy lookup of A's function (interface §4)"
    calls: list[str] = []

    def missing() -> tuple[Any, type[Exception]]:
        calls.append("_assign_owner")
        raise ImportError("cannot import name 'assign_owner_and_send_reset' from 'backend.app.services.accounts.instance_owner'")

    monkeypatch.setattr(owner, "_assign_owner", missing)
    return calls


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def owner() -> ModuleType:
    """``instance_backup.owner``; before B5-1 the test fails here with the ``ImportError``, never a skip."""
    try:
        return importlib.import_module(OWNER_MODULE)
    except ImportError as exc:
        pytest.fail(f"[new] B5-1: {OWNER_MODULE} cannot be imported yet (interface §4): {type(exc).__name__}: {exc}", pytrace=False)


@dataclass(frozen=True)
class DataDir:
    """The data directory of a test and the owner's id in its database."""

    root: Path
    owner_id: int


@pytest.fixture
def data_dir(tmp_path: Path, databases: cases.Databases, monkeypatch: pytest.MonkeyPatch) -> Iterator[DataDir]:
    """A data directory under ``tmp_path``, its database a migrated copy holding the owner's account and two others,
    configured as this process's test data directory, the async engine singleton emptied for the test; ``managed``, the
    owner's email set. At its end the engine the test made is disposed, the one before put back by ``monkeypatch``."""
    root = tmp_path / "data"
    database = root / DATABASE_ENTRY
    database.parent.mkdir(parents=True)
    shutil.copyfile(databases.head, database)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.executemany(
            cases.INSERT_ACCOUNT,
            [
                ("b51_admin", "admin.b51@example.com", "$argon2id$v=19$not-a-real-hash", 1, 1, cases.CREATED, cases.CREATED),
                (OWNER_USERNAME, "chosen.b51@example.com", "$argon2id$v=19$not-a-real-hash", 1, 0, cases.CREATED, cases.CREATED),
                ("b51_user", "user.b51@example.com", "$argon2id$v=19$not-a-real-hash", 1, 0, cases.CREATED, cases.CREATED),
            ],
        )
    owner_id = cases.rows_of(database, f"SELECT id FROM users WHERE username = '{OWNER_USERNAME}'")[0][0]
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.delenv("LIBREFOLIO_DATA_DIR", raising=False)
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    for name in OWNER_SIDE_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(OWNER_EMAIL_VARIABLE, OWNER_EMAIL)
    from backend.app.config import get_data_dir, get_settings  # noqa: PLC0415 — read after the environment is set

    assert get_data_dir() == root.resolve(), f"barrier: the configured data directory is the test's, not {get_data_dir()}"
    assert get_settings().LIBREFOLIO_PROFILE == "managed", "barrier: the profile is managed"
    previous = db_session.async_engine
    monkeypatch.setattr(db_session, "async_engine", None)
    ensure_private_dir(restore_dir(root), root)
    try:
        yield DataDir(root=root, owner_id=owner_id)
    finally:
        made = db_session.async_engine
        if made is not None and made is not previous:
            await_dispose(made)


def await_dispose(engine: Any) -> None:
    """Dispose an async engine from a synchronous teardown."""
    import asyncio  # noqa: PLC0415

    asyncio.run(engine.dispose())


def write_state(root: Path, *, status: str = "committed", confirmed_via: str = "admin", owner_user_id: int | None = None, owner_outcome: str | None = None, stale: dict[str, Any] | None = None) -> bytes:
    """``.restore/restore.json`` as a start leaves a restore in ``status``, raw JSON with the owner's keys (never
    ``owner_reset_path``): its bytes. ``stale``: keys of an older LibreFolio written into it as they are."""
    record: dict[str, Any] = {
        "format": 1,
        "status": status,
        "stage_id": STAGE_ID,
        "data_dir": str(root.resolve()),
        "confirmed_at": CONFIRMED_AT.isoformat(),
        "confirmed_by": "b51-admin" if confirmed_via == "admin" else confirmed_via,
        "confirmed_via": confirmed_via,
        "backup_created_at": (CONFIRMED_AT - timedelta(days=1)).isoformat(),
        "backup_app_version": "v1.3.0",
        "action": "same",
        "owner_user_id": owner_user_id,
        "owner_outcome": owner_outcome,
        **(stale or {}),
    }
    if status in ("applying", "applied", "rolling_back"):
        record["swap"] = [{"name": name, "live": True, "staged": True} for name in ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")]
        record["boot"] = {"pid": 999_999, "started": 1_760_000_000.0}
    if status in ("applied", "committed"):
        record["applied_at"] = (FINISHED_AT - timedelta(minutes=1)).isoformat()
    if status in ("committed", "rolled_back"):
        record["finished_at"] = FINISHED_AT.isoformat()
    if status in ("rolling_back", "rolled_back"):
        record["reason"] = "first_start_failed"
    if status == "committed":
        record["session_version"] = int(FINISHED_AT.timestamp() * 1000)
    path = restore_state_path(root)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path.read_bytes()


def state_bytes(root: Path) -> bytes | None:
    path = restore_state_path(root)
    return path.read_bytes() if path.exists() else None


def recorded(root: Path) -> tuple[Any, Any]:
    """What ``restore.json`` says of the owner: id, outcome. The file never holds an ``owner_reset_path`` key (nor any
    link): a state written by the code carries none."""
    text_ = restore_state_path(root).read_text(encoding="utf-8")
    record = json.loads(text_)
    assert "owner_reset_path" not in record, f"the state has no owner_reset_path key: {sorted(record)}"
    assert LINK_CANARY not in text_ and "reset-password" not in text_, "no link in restore.json"
    return tuple(record.get(name, "<missing>") for name in ("owner_user_id", "owner_outcome"))


async def assigned(owner: ModuleType, root: Path | None) -> tuple[Any, BaseException | None, list[dict[str, Any]]]:
    """``assign_restored_owner`` called (``root`` ``None``: without arguments), its log captured behind a barrier: what
    it returned, what it raised (it must raise nothing), what it logged (the canary left out)."""
    with capture_logs() as events:
        get_logger(OWNER_MODULE).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a logger of {OWNER_MODULE} does not reach capture_logs: {events}"
        returned, raised = None, None
        try:
            returned = await (owner.assign_restored_owner() if root is None else owner.assign_restored_owner(root))
        except BaseException as exc:  # noqa: BLE001 — reported by the caller: the step must never raise
            raised = exc
    return returned, raised, [event for event in events if event.get("event") != LOG_CANARY]


def no_secret_in(events: list[dict[str, Any]], *extra: str) -> None:
    """No log line holds the owner's email, its username, the canary link, nor any of ``extra``."""
    lines = repr(events).lower()
    shown = [secret for secret in (OWNER_EMAIL, OWNER_USERNAME, LINK_CANARY, "b51-canary-token", "reset-password", *extra) if secret.lower() in lines]
    assert shown == [], f"the log holds {shown}: {events}"


def levels(events: list[dict[str, Any]]) -> set[str]:
    return {str(event.get("log_level")) for event in events}


# =============================================================================
# (a) owner_choice_required
# =============================================================================


@pytest.mark.parametrize(("profile", "required"), [("managed", True), ("selfhosted", False)])
def test_the_owner_s_choice_is_required_in_the_managed_profile_only(owner, data_dir, monkeypatch, profile, required):
    """(a) ``owner_choice_required()`` reads the profile now: ``managed`` asks the owner's choice, ``selfhosted`` never."""
    print_section("(a) B5-1 owner_choice_required")
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    assert owner.owner_choice_required() is required, f"{profile}: {required}"
    print_success(f"{profile}: {required}")


# =============================================================================
# (b) assign_restored_owner
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", list(FakeOutcome), ids=[outcome.value for outcome in FakeOutcome])
async def test_a_committed_admin_restore_assigns_the_chosen_owner_once_and_records_the_outcome(owner, data_dir, monkeypatch, outcome):
    """(b) Committed, via ``admin``, the owner chosen, nothing recorded yet: A's function called once, with the owner's
    id and an ``AsyncSession`` (``expire_on_commit`` off) on the data directory's database — it finds the owner's row
    there —; its outcome recorded in ``restore.json`` and in the state returned. The stray ``reset_path`` of the
    ``link_only`` result (the canary) is in no file, no state, no log line; the state has no such field."""
    print_section(f"(b) B5-1 assign_restored_owner: {outcome.value}")
    fake = FakeA(outcome=outcome)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert fake.calls == [{"user_id": data_dir.owner_id, "async_session": True, "expire_on_commit": False, "username": OWNER_USERNAME, "now": None}], f"A's function called once, with the owner's id and a session on this database, nothing else: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, outcome.value), f"restore.json records {outcome.value}: {recorded(data_dir.root)}"
    assert returned is not None and (returned.status, returned.owner_user_id, returned.owner_outcome) == ("committed", data_dir.owner_id, outcome.value), f"the state returned says it too: {returned}"
    assert "owner_reset_path" not in type(returned).model_fields and LINK_CANARY not in repr(returned.model_dump()), f"the state has no field for a link: {returned}"
    no_secret_in(events)
    print_success(f"{outcome.value} recorded, one call")


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ASSIGNMENT_CODES)
async def test_an_owner_assignment_error_is_recorded_as_error_and_its_code(owner, data_dir, monkeypatch, code):
    """(b) A's ``OwnerAssignmentError``: ``owner_outcome`` ``error:<CODE>``, nothing raised; its message
    (which names the email) never in the log."""
    fake = FakeA(raises=FakeOwnerAssignmentError(code))
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 1, f"A's function called once: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, f"error:{code}"), f"restore.json records error:{code}: {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success(f"error:{code}")


@pytest.mark.asyncio
async def test_an_unexpected_failure_leaves_the_owner_pending_for_the_next_start(owner, data_dir, monkeypatch):
    """(b) Any other exception of A's function: logged by its type only, nothing recorded — the next start calls A again
    (each call of A does the whole treatment and is harmless to repeat) —, nothing raised."""
    fake = FakeA(raises=RuntimeError(UNEXPECTED_TEXT))
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 1, f"A's function called once: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, None), f"nothing recorded: {recorded(data_dir.root)}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was"
    assert levels(events) & {"warning", "error", "critical"}, f"the failure is logged: {events}"
    no_secret_in(events, UNEXPECTED_TEXT)
    # The next start: A is called again and whatever it answers is recorded.
    fake.raises, fake.outcome = None, FakeOutcome.LINK_ONLY
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 2, f"the next start calls A again: {raised}, {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "link_only"), f"the next start records what A answered: {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success("RuntimeError: pending, logged by type; then A called again and link_only recorded")


# -----------------------------------------------------------------------------
# (b) B5-1g: a database that is busy for a moment is waited for, a few times, and nothing else is retried
# -----------------------------------------------------------------------------
#
# A's call writes the account and the link in one transaction. Another worker of the same start (admin-bootstrap, the
# scheduler) may hold SQLite's write lock for a moment: the call then fails with ``database is locked``, which
# SQLAlchemy raises as ``OperationalError``. That is not a reason to leave the owner without their link until the next
# start: the step tries a few more times, with a short pause (``_RETRY_PAUSE_SECONDS``, patched to zero here), and only
# for that error. ``_ATTEMPTS`` is the bound: a lock that never frees ends the step with nothing recorded.


@dataclass
class ScriptedA(FakeA):
    """A ``FakeA`` that raises each of ``failures`` in turn, one per call, then does what ``FakeA`` does."""

    failures: list[BaseException] = field(default_factory=list)

    async def __call__(self, session: Any, user_id: int, *, now: datetime | None = None) -> FakeResult:
        self.raises = self.failures.pop(0) if self.failures else None
        return await super().__call__(session, user_id, now=now)


def a_locked_database(kind: str) -> BaseException:
    """The error a busy SQLite gives, as the three layers can show it."""
    if kind == "wrapped-locked":
        return OperationalError("INSERT INTO account_tokens (purpose) VALUES (?)", {}, sqlite3.OperationalError("database is locked"))
    if kind == "wrapped-table-locked":
        return OperationalError("UPDATE users SET email = ?", {}, sqlite3.OperationalError("database table is locked"))
    return sqlite3.OperationalError("database is locked")


LOCK_KINDS = ["wrapped-locked", "wrapped-table-locked", "bare-locked"]


def attempts_of(owner: ModuleType) -> int:
    """``owner._ATTEMPTS``, the bound of the tries; before B5-1g a failure that says so."""
    attempts = getattr(owner, "_ATTEMPTS", None)
    if attempts is None:
        pytest.fail("[new] B5-1g: owner._ATTEMPTS (the bound of the tries on a locked database, 3 or more) does not exist yet", pytrace=False)
    assert isinstance(attempts, int) and attempts >= 3, f"_ATTEMPTS is 3 or more: {attempts!r}"
    return attempts


def no_pause(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> None:
    """The pause between two tries made zero: a test never waits. ``raising=False``: a red test must fail on what it
    asserts, not on the missing name."""
    monkeypatch.setattr(owner, "_RETRY_PAUSE_SECONDS", 0, raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", LOCK_KINDS)
async def test_a_locked_database_is_waited_for_and_the_owner_is_assigned_all_the_same(owner, data_dir, monkeypatch, kind):
    """(b) B5-1g: A's call fails twice with ``database is locked`` (wrapped by SQLAlchemy or not) and then answers: the step
    called A three times, each time with the owner's id and a session on the data directory's database, and records
    what A answered (``sent``), as if nothing had happened. Nothing raised; no address, name or link in the log. Red
    before B5-1g: the first failure ended the step with nothing recorded."""
    print_section(f"(b) B5-1g a locked database retried: {kind}")
    no_pause(monkeypatch, owner)
    fake = ScriptedA(outcome=FakeOutcome.SENT, failures=[a_locked_database(kind), a_locked_database(kind)])
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 3, f"A called until it got through, three times: {len(fake.calls)}"
    assert all(call["user_id"] == data_dir.owner_id and call["async_session"] and call["now"] is None and call["username"] == OWNER_USERNAME for call in fake.calls), f"each try with the owner's id and a session on the database: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent"), f"restore.json records what A answered after the lock freed: {recorded(data_dir.root)}"
    assert returned is not None and returned.owner_outcome == "sent", f"the state returned says it too: {returned}"
    no_secret_in(events)
    print_success(f"{kind}: two locks waited for, then sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", LOCK_KINDS)
async def test_a_lock_that_never_frees_ends_after_the_bounded_tries_and_leaves_the_owner_pending(owner, data_dir, monkeypatch, kind):
    """(b) B5-1g: A's call always fails with ``database is locked``: it is called exactly ``_ATTEMPTS`` times (3 or more),
    then the step returns ``None`` with nothing recorded and ``restore.json`` as it was — the next start tries again —,
    nothing raised, the failure logged by its type, no address, name or link in the log. Red before B5-1g: A was called
    once and ``_ATTEMPTS`` did not exist."""
    no_pause(monkeypatch, owner)
    attempts = attempts_of(owner)
    fake = FakeA(raises=a_locked_database(kind))
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == attempts, f"A called exactly _ATTEMPTS ({attempts}) times, no more: {len(fake.calls)}"
    assert returned is None and recorded(data_dir.root) == (data_dir.owner_id, None), f"nothing recorded: {returned}, {recorded(data_dir.root)}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was: the next start calls A again"
    assert levels(events) & {"warning", "error", "critical"}, f"the failure is logged: {events}"
    no_secret_in(events)
    # The next start, the lock gone: A is called again and whatever it answers is recorded.
    fake.raises, fake.outcome = None, FakeOutcome.SENT
    _returned, raised, _events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == attempts + 1, f"the next start calls A again: {raised}, {len(fake.calls)}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent"), f"the next start records what A answered: {recorded(data_dir.root)}"
    print_success(f"{kind}: {attempts} tries, nothing recorded, then sent at the next start")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(RuntimeError(UNEXPECTED_TEXT), id="runtime-error"),
        pytest.param(OperationalError("SELECT 1 FROM users", {}, sqlite3.OperationalError("no such table: users")), id="operational-error-not-a-lock"),
        pytest.param(sqlite3.IntegrityError("UNIQUE constraint failed: users.email"), id="integrity-error"),
    ],
)
async def test_only_a_locked_database_is_retried(owner, data_dir, monkeypatch, failure):
    """(b) B5-1g, the guard: any other failure of A's call — not an ``OperationalError`` of a lock — is not retried: A is
    called once, the step returns ``None``, nothing is recorded, ``restore.json`` as it was, the failure logged by its
    type only. Green before B5-1g, and it must stay so."""
    no_pause(monkeypatch, owner)
    fake = FakeA(raises=failure)
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 1, f"A called once, not retried: {len(fake.calls)}"
    assert returned is None and state_bytes(data_dir.root) == before, "nothing recorded, restore.json as it was"
    assert levels(events) & {"warning", "error", "critical"}, f"the failure is logged: {events}"
    no_secret_in(events, UNEXPECTED_TEXT, "users.email")
    print_success(f"{type(failure).__name__}: one call, not retried")


@pytest.mark.asyncio
async def test_a_refusal_of_a_is_recorded_at_once_never_retried(owner, data_dir, monkeypatch):
    """(b) B5-1g, the guard: A's own refusal (``OwnerAssignmentError``) is an answer, not a lock: one call, recorded as
    ``error:<CODE>`` at once. Green before B5-1g, and it must stay so."""
    no_pause(monkeypatch, owner)
    fake = FakeA(raises=FakeOwnerAssignmentError("EMAIL_TAKEN"))
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, _events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 1, f"one call: {raised}, {len(fake.calls)}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "error:EMAIL_TAKEN"), f"recorded at once: {recorded(data_dir.root)}"
    print_success("EMAIL_TAKEN: one call, recorded")


@dataclass
class BusyTimeoutProbe(FakeA):
    """A ``FakeA`` that also reads ``PRAGMA busy_timeout`` of the session it is given, in milliseconds."""

    timeouts: list[int] = field(default_factory=list)

    async def __call__(self, session: Any, user_id: int, *, now: datetime | None = None) -> FakeResult:
        self.timeouts.append(int((await session.execute(text("PRAGMA busy_timeout"))).scalar_one()))
        return await super().__call__(session, user_id, now=now)


@pytest.mark.asyncio
async def test_the_session_a_is_given_waits_for_a_busy_database_before_it_fails(owner, data_dir, monkeypatch):
    """(b) B5-1g: the engine the step builds for A's session carries a busy timeout of at least 5000 ms (SQLite then waits
    for a lock before it raises ``database is locked``, so the retries above are for a lock held longer than that)."""
    no_pause(monkeypatch, owner)
    fake = BusyTimeoutProbe(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, _events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 1, f"A called once: {raised}, {len(fake.calls)}"
    assert fake.timeouts and fake.timeouts[0] >= 5000, f"the session waits at least 5000 ms for a lock: {fake.timeouts}"
    print_success(f"busy_timeout {fake.timeouts[0]} ms")


@pytest.mark.asyncio
async def test_without_a_s_code_the_owner_stays_pending_and_an_error_is_logged(owner, data_dir, monkeypatch):
    """(b) ``_assign_owner()`` raising ``ImportError`` (A's code not merged): an error logged, nothing recorded, nothing
    raised."""
    calls = a_not_merged(monkeypatch, owner)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert calls == ["_assign_owner"], f"barrier: the lookup of A's function was tried: {calls}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was: the owner pending"
    assert levels(events) & {"error", "critical"}, f"an error is logged: {events}"
    no_secret_in(events)
    print_success("ImportError: pending, an error logged")


#: Every restore the step must leave alone: (the state's fields, or ``None`` for no state at all).
LEFT_ALONE = [
    pytest.param(None, id="no-restore"),
    *(pytest.param({"status": status, "owner_user_id": "owner"}, id=f"{status}") for status in ("pending", "applying", "applied", "rolling_back", "rolled_back")),
    # B5-1j: a restore confirmed from the command line or by the panel with NO owner picked (none found, or no address) has
    # nothing to give: its outcome ``none`` is recorded at the confirmation and the step does not run for it.
    *(pytest.param({"confirmed_via": via, "owner_user_id": None, "owner_outcome": "none"}, id=f"committed-via-{via}-nobody-picked") for via in ("cli", "panel")),
    *(pytest.param({"confirmed_via": via, "owner_user_id": None}, id=f"committed-via-{via}-no-owner") for via in ("cli", "panel")),
    pytest.param({"owner_user_id": None}, id="committed-no-owner"),
    *(pytest.param({"owner_user_id": "owner", "owner_outcome": outcome}, id=f"already-{outcome}") for outcome in ("sent", "link_only", "error:EMAIL_TAKEN")),
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner", "owner_outcome": "link_only"}, id=f"already-link_only-via-{via}") for via in ("cli", "panel")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fields", LEFT_ALONE)
async def test_anything_but_a_committed_admin_restore_waiting_for_its_owner_is_left_alone(owner, data_dir, monkeypatch, fields):
    """(b) No state; a restore not committed; one without an owner (via ``cli`` or ``panel`` whose outcome ``none`` was
    recorded at the confirmation, B5-1j, or not); one whose outcome is recorded: ``None`` returned, A's function never
    called, ``restore.json`` byte for byte."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    before = None
    if fields is not None:
        given = {name: (data_dir.owner_id if value == "owner" else value) for name, value in fields.items()}
        before = write_state(data_dir.root, **given)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert (returned, fake.calls) == (None, []), f"{fields}: nothing done, A never called: {returned}, {fake.calls}"
    assert state_bytes(data_dir.root) == before, f"{fields}: restore.json as it was"
    no_secret_in(events)
    print_success(f"{fields}: left alone")


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["cli", "panel"])
@pytest.mark.parametrize("outcome", list(FakeOutcome), ids=[outcome.value for outcome in FakeOutcome])
async def test_a_committed_command_line_or_panel_restore_assigns_the_picked_owner_once_and_records_the_outcome(owner, data_dir, monkeypatch, via, outcome):
    """(b) B5-1j: the owner picked at the confirmation of a restore via ``cli`` or ``panel`` is given the account by the same
    step as the app's: A's function called once with the picked id (a session on the data directory's database, nothing
    else), its outcome recorded in ``restore.json`` and in the state returned, no link anywhere. Red before B5-1j: the step
    left a state confirmed from the command line or the panel alone."""
    print_section(f"(b) B5-1j assign_restored_owner via {via}: {outcome.value}")
    fake = FakeA(outcome=outcome)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, confirmed_via=via, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert fake.calls == [{"user_id": data_dir.owner_id, "async_session": True, "expire_on_commit": False, "username": OWNER_USERNAME, "now": None}], f"A's function called once, with the picked id: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, outcome.value), f"restore.json records {outcome.value}: {recorded(data_dir.root)}"
    assert returned is not None and (returned.confirmed_via, returned.owner_user_id, returned.owner_outcome) == (via, data_dir.owner_id, outcome.value), f"the state returned says it too: {returned}"
    no_secret_in(events)
    print_success(f"via {via}: {outcome.value} recorded, one call")


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["cli", "panel"])
@pytest.mark.parametrize("code", ASSIGNMENT_CODES)
async def test_an_owner_assignment_error_of_a_command_line_or_panel_restore_is_recorded_as_error_and_its_code(owner, data_dir, monkeypatch, via, code):
    """(b) B5-1j: A refuses the account picked for a restore via ``cli`` or ``panel``: ``error:<CODE>`` recorded as for the
    app, nothing raised."""
    fake = FakeA(raises=FakeOwnerAssignmentError(code))
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, confirmed_via=via, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 1, f"nothing raised, A called once: {raised}, {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, f"error:{code}"), f"restore.json records error:{code}: {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success(f"via {via}: error:{code}")


@pytest.mark.asyncio
async def test_a_second_call_after_a_recorded_outcome_does_nothing(owner, data_dir, monkeypatch):
    """(b) Idempotent: once an outcome is recorded, the next start does not call A again, and changes nothing."""
    fake = FakeA(outcome=FakeOutcome.LINK_ONLY)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _first, raised, _events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 1, f"precondition: the first call records the outcome: {raised}, {fake.calls}"
    after_first = state_bytes(data_dir.root)
    second, raised, events = await assigned(owner, data_dir.root)
    assert (raised, second, len(fake.calls)) == (None, None, 1), f"the second call does nothing: {raised}, {second}, {fake.calls}"
    assert state_bytes(data_dir.root) == after_first, "restore.json unchanged by the second call"
    no_secret_in(events)
    print_success("second call: nothing")


#: What a state written before the R13 security review carries: a link, a secret that must go.
STALE_KEY = {"owner_reset_path": LINK_CANARY}


def test_a_state_that_still_carries_owner_reset_path_reads_fine_and_the_key_is_dropped(data_dir):
    """(b) R13: a ``restore.json`` of an older LibreFolio that still has ``owner_reset_path`` is read without an error;
    the state has no such field, so the link is nowhere in what ``read_restore`` returns."""
    write_state(data_dir.root, owner_user_id=data_dir.owner_id, stale=STALE_KEY)
    state = apply_module().read_restore(data_dir.root)
    assert state is not None and (state.status, state.owner_user_id, state.owner_outcome) == ("committed", data_dir.owner_id, None), f"read fine: {state}"
    assert "owner_reset_path" not in type(state).model_fields and "owner_reset_path" not in state.model_dump(), "the state has no field for the link"
    assert LINK_CANARY not in repr(state.model_dump()), "the stale link is not in what is read"
    print_success("stale owner_reset_path: ignored")


@pytest.mark.asyncio
async def test_recording_an_outcome_rewrites_a_state_with_a_stale_link_without_it(owner, data_dir, monkeypatch):
    """(b) R13: the start that records the outcome of a state still carrying ``owner_reset_path`` writes it back without
    the key: the old link is in the file no more."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id, stale=STALE_KEY)
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None and len(fake.calls) == 1, f"precondition: the owner was assigned: {raised}, {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent"), f"recorded, and the file holds no owner_reset_path nor the old link: {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success("stale owner_reset_path: gone after the record")


@pytest.mark.parametrize("outcome", ["sent", "link_only", "error:EMAIL_TAKEN"])
def test_record_owner_outcome_takes_the_outcome_only_and_records_it_once(data_dir, outcome):
    """(b) R13: ``apply.record_owner_outcome(data_dir, stage_id, outcome)`` — three arguments, no link — records ``sent``,
    ``link_only`` or ``error:<CODE>`` in ``restore.json`` without an ``owner_reset_path`` key; a second record of the
    same restore changes nothing."""
    apply = apply_module()
    assert list(inspect.signature(apply.record_owner_outcome).parameters) == ["data_dir", "stage_id", "outcome"], "[new] R13: record_owner_outcome(data_dir, stage_id, outcome): it is handed no link"
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    state = apply.record_owner_outcome(data_dir.root, STAGE_ID, outcome)
    assert state is not None and (state.owner_user_id, state.owner_outcome) == (data_dir.owner_id, outcome), f"recorded: {state}"
    assert recorded(data_dir.root) == (data_dir.owner_id, outcome), f"restore.json says it, with no link key: {recorded(data_dir.root)}"
    after_first = state_bytes(data_dir.root)
    apply.record_owner_outcome(data_dir.root, STAGE_ID, "sent" if outcome != "sent" else "link_only")
    assert state_bytes(data_dir.root) == after_first, "a second record changes nothing"
    print_success(f"record_owner_outcome: {outcome}")


@pytest.mark.asyncio
async def test_without_arguments_the_step_reads_the_configured_data_directory(owner, data_dir, monkeypatch):
    """(b) ``assign_restored_owner()`` without arguments: the configured data directory (the startup step's call)."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, None)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert (len(fake.calls), recorded(data_dir.root)) == (1, (data_dir.owner_id, "sent")), f"the configured data directory's restore: {fake.calls}, {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success("no arguments: the configured data directory")


# =============================================================================
# (d) Security addendum §7.3: one worker calls A
# =============================================================================

#: The lock the worker that calls A holds, from before the call until the outcome is recorded (§7.3).
OWNER_LOCK_NAME = "owner.lock"
#: Seconds: every wait of (d) ends by then; none decides alone.
DEADLINE_S = 60


def owner_lock_path(root: Path) -> Path:
    return restore_dir(root) / OWNER_LOCK_NAME


@contextmanager
def owner_lock_held(root: Path) -> Iterator[None]:
    """``.restore/owner.lock`` held by the test, as another worker of the server would hold it: an exclusive ``flock``
    on a descriptor of its own (the product's descriptor is another open file, so the two locks conflict)."""
    fd = os.open(owner_lock_path(root), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


@dataclass
class GatedA(FakeA):
    """A ``FakeA`` whose first call waits until a worker has returned (``released``, set by the test), with a deadline:
    while it waits, the other worker runs its whole course. ``entered``: the user id of each call, as it begins."""

    released: asyncio.Event = field(default_factory=asyncio.Event)
    entered: list[int] = field(default_factory=list)
    timed_out: bool = False

    async def __call__(self, session: Any, user_id: int, *, now: datetime | None = None) -> FakeResult:
        self.entered.append(user_id)
        if len(self.entered) == 1:
            try:
                await asyncio.wait_for(self.released.wait(), timeout=DEADLINE_S)
            except TimeoutError:
                self.timed_out = True
        return await super().__call__(session, user_id, now=now)


@pytest.mark.asyncio
async def test_two_workers_at_once_call_a_once(owner, data_dir, monkeypatch):
    """(d) B5-1 §7.3: two workers of one server run the step at the same time: A's function is called once — the worker
    that cannot take ``.restore/owner.lock`` returns ``None`` without calling it —, the outcome recorded once, nothing
    raised. A's first call waits until one worker has returned, so the other has run its whole course meanwhile."""
    print_section("(d) B5-1 §7.3 two workers at once")
    fake = GatedA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    with capture_logs() as events:
        get_logger(OWNER_MODULE).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a logger of {OWNER_MODULE} does not reach capture_logs: {events}"
        workers = [asyncio.create_task(owner.assign_restored_owner(data_dir.root)) for _ in range(2)]
        for worker in workers:
            worker.add_done_callback(lambda _done: fake.released.set())
        results = await asyncio.wait_for(asyncio.gather(*workers, return_exceptions=True), timeout=2 * DEADLINE_S)
    raised = [result for result in results if isinstance(result, BaseException)]
    assert raised == [], f"the step never raises: {[type(error).__name__ for error in raised]}"
    assert not fake.timed_out, "barrier: A's first call was released by a worker returning, not by the deadline"
    assert fake.entered == [data_dir.owner_id], f"A's function called once, by one worker: {fake.entered}"
    assert sorted(result is None for result in results) == [False, True], f"one worker records the outcome, the other returns None: {results}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent"), f"the outcome recorded once: {recorded(data_dir.root)}"
    no_secret_in([event for event in events if event.get("event") != LOG_CANARY])
    print_success("two workers: one call of A")


@pytest.mark.asyncio
async def test_a_worker_that_cannot_take_the_owner_lock_leaves_the_owner_to_the_other(owner, data_dir, monkeypatch):
    """(d) B5-1 §7.3: ``.restore/owner.lock`` held by another worker: the step returns ``None``, A's function never
    called, ``restore.json`` byte for byte, nothing raised. Once the lock is free, the next call assigns the owner (a
    guard: the restore was waiting for its owner)."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    with owner_lock_held(data_dir.root):
        returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert (returned, fake.calls) == (None, []), f"the lock held elsewhere: nothing done, A never called: {returned}, {fake.calls}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was"
    no_secret_in(events)
    _returned, raised, _events = await assigned(owner, data_dir.root)
    assert (raised, len(fake.calls), recorded(data_dir.root)) == (None, 1, (data_dir.owner_id, "sent")), f"the lock free: the owner assigned: {fake.calls}, {recorded(data_dir.root)}"
    print_success("the lock held elsewhere: None, A not called")


@pytest.mark.asyncio
async def test_the_owner_lock_is_created_readable_by_its_owner_only(owner, data_dir, monkeypatch):
    """(d) B5-1 §7.3: the step creates ``.restore/owner.lock`` with mode 0600 whatever the umask (0 here), a regular
    file, and assigns the owner."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    lock = owner_lock_path(data_dir.root)
    assert not os.path.lexists(lock), "precondition: no owner lock yet"
    previous = os.umask(0)
    try:
        _returned, raised, _events = await assigned(owner, data_dir.root)
    finally:
        os.umask(previous)
    assert raised is None and len(fake.calls) == 1, f"precondition: the owner was assigned: {raised}, {fake.calls}"
    assert os.path.lexists(lock), f"[new] B5-1 §7.3: the step took no lock at .restore/{OWNER_LOCK_NAME}"
    mode = os.lstat(lock).st_mode
    assert stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o600, f"the owner lock is a regular file of mode 0600: {oct(stat.S_IMODE(mode))}"
    print_success("owner.lock 0600")


# =============================================================================
# (e) Security addendum §7.4: the hook of H's guard
# =============================================================================

APPLY_MODULE = "backend.app.services.platform.instance_backup.apply"


def problem_hook() -> Any:
    """``apply.owner_assignment_problem``; before §7.4, a failure that says so."""
    hook = getattr(importlib.import_module(APPLY_MODULE), "owner_assignment_problem", None)
    if hook is None:
        pytest.fail("[new] B5-1 §7.4: apply.owner_assignment_problem does not exist yet", pytrace=False)
    return hook


#: (the state's fields, ``None`` for no state; what the hook answers).
PROBLEMS = [
    pytest.param(None, None, id="no-restore"),
    pytest.param({"owner_user_id": "owner"}, "pending", id="committed-owner-pending"),
    *(pytest.param({"owner_user_id": "owner", "owner_outcome": f"error:{code}"}, code, id=f"committed-error-{code}") for code in ASSIGNMENT_CODES),
    *(pytest.param({"owner_user_id": "owner", "owner_outcome": outcome.value}, None, id=f"committed-{outcome.value}") for outcome in FakeOutcome),
    # B5-1j: the owner picked at a confirmation via the command line or the panel is the guard's concern like the app's.
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner"}, "pending", id=f"committed-via-{via}-owner-pending") for via in ("cli", "panel")),
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner", "owner_outcome": f"error:{code}"}, code, id=f"committed-via-{via}-error-{code}") for via in ("cli", "panel") for code in ("EMAIL_TAKEN", "USER_NOT_FOUND")),
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner", "owner_outcome": outcome.value}, None, id=f"committed-via-{via}-{outcome.value}") for via in ("cli", "panel") for outcome in FakeOutcome),
    *(pytest.param({"confirmed_via": via, "owner_user_id": None, "owner_outcome": "none"}, None, id=f"committed-via-{via}-nobody-picked") for via in ("cli", "panel")),
    pytest.param({"owner_user_id": None}, None, id="committed-no-owner"),
    *(pytest.param({"status": status, "owner_user_id": "owner"}, None, id=f"{status}") for status in ("pending", "applying", "applied", "rolling_back", "rolled_back")),
]


@pytest.mark.parametrize(("fields", "expected"), PROBLEMS)
def test_owner_assignment_problem_says_whether_the_owner_s_account_is_still_open(data_dir, fields, expected):
    """(e) B5-1 §7.4, B5-1j: for the last restore — committed, an owner named, whoever confirmed it (the app, the command
    line, the hosting panel) — ``"pending"`` while no outcome is recorded, the code of an ``error:<CODE>``; ``None``
    otherwise: no restore, an outcome of A, a restore without an owner (``none`` recorded at the confirmation included), or
    not committed. Nothing written."""
    print_section("(e) B5-1 §7.4 owner_assignment_problem")
    hook = problem_hook()
    before = None
    if fields is not None:
        given = {name: (data_dir.owner_id if value == "owner" else value) for name, value in fields.items()}
        before = write_state(data_dir.root, **given)
    assert hook(data_dir.root) == expected, f"{fields}: {expected!r}"
    assert state_bytes(data_dir.root) == before, f"{fields}: restore.json as it was"
    print_success(f"{fields}: {expected!r}")


def test_owner_assignment_problem_without_arguments_reads_the_configured_data_directory(data_dir):
    """(e) B5-1 §7.4: ``owner_assignment_problem()`` without arguments: the configured data directory (the guard's
    call)."""
    hook = problem_hook()
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    assert hook() == "pending", "the configured data directory's restore, its owner pending"
    print_success("no arguments: pending")


def unreadable_as(root: Path, kind: str) -> None:
    """``restore.json`` that no reader can use: not JSON, a folder, a format of a later LibreFolio."""
    path = restore_state_path(root)
    if kind == "a-folder":
        path.mkdir(mode=0o700)
        return
    if kind == "not-json":
        path.write_bytes(b"{ this is not json\n")
    else:
        record = json.loads(write_state(root, owner_user_id=1))
        path.write_text(json.dumps({**record, "format": 2}), encoding="utf-8")
    path.chmod(0o600)


@pytest.mark.parametrize("kind", ["not-json", "a-folder", "format-2"])
def test_owner_assignment_problem_leaves_an_unreadable_state_to_restore_state_problem(data_dir, kind):
    """(e) B5-1 §7.4: a state that cannot be read is ``restore_state_problem``'s: the hook answers ``None`` and never
    raises."""
    hook = problem_hook()
    unreadable_as(data_dir.root, kind)
    try:
        answered = hook(data_dir.root)
    except Exception as exc:  # noqa: BLE001 — reported as the failure: the hook never raises
        pytest.fail(f"{kind}: the hook raised {type(exc).__name__}", pytrace=False)
    assert answered is None, f"{kind}: None, not {answered!r}"
    print_success(f"{kind}: None")


def test_owner_assignment_problem_never_raises(data_dir, monkeypatch):
    """(e) B5-1 §7.4: whatever reading the state raises, the hook answers ``None`` and raises nothing."""
    hook = problem_hook()
    apply = importlib.import_module(APPLY_MODULE)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(UNEXPECTED_TEXT)

    monkeypatch.setattr(apply, "_read_state", failing)
    try:
        answered = hook(data_dir.root)
    except Exception as exc:  # noqa: BLE001 — reported as the failure: the hook never raises
        pytest.fail(f"the hook raised {type(exc).__name__}", pytrace=False)
    assert answered is None, f"an unexpected failure: None, not {answered!r}"
    print_success("an unexpected failure: None")


# =============================================================================
# (f) B5-1b §9.1: the way out of a failed owner assignment
# =============================================================================

RESET_MODULE_ERROR = "RestoreOwnerNotFailedError"


def apply_module() -> ModuleType:
    return importlib.import_module(APPLY_MODULE)


def not_failed_error() -> type[Exception]:
    """``apply.RestoreOwnerNotFailedError``; before B5-1b, a failure that says so."""
    error = getattr(apply_module(), RESET_MODULE_ERROR, None)
    if error is None:
        pytest.fail(f"[new] B5-1b §9.1: apply.{RESET_MODULE_ERROR} does not exist yet", pytrace=False)
    return error


def reset_function() -> Any:
    """``apply.reset_owner_assignment``; before B5-1b, a failure that says so."""
    function = getattr(apply_module(), "reset_owner_assignment", None)
    if function is None:
        pytest.fail("[new] B5-1b §9.1: apply.reset_owner_assignment does not exist yet", pytrace=False)
    return function


def held_lock_function(owner: ModuleType) -> Any:
    function = getattr(owner, "held_owner_lock", None)
    if function is None:
        pytest.fail("[new] B5-1b §9.1: owner.held_owner_lock does not exist yet", pytrace=False)
    return function


@contextmanager
def server_serving(root: Path) -> Iterator[None]:
    """A server serving the data directory for the block: its serving lock held by this process through a descriptor of
    its own, as ``hold_serving_lock`` holds it; released at the end."""
    apply = apply_module()
    assert apply.hold_serving_lock(root) is True, "precondition: a server serves the data directory"
    try:
        yield
    finally:
        os.close(apply._SERVING.pop(str(root.resolve())))


def lock_is_free(root: Path) -> bool:
    """Whether ``.restore/owner.lock`` can be taken now, through a descriptor of the test's own, and is left free."""
    fd = os.open(owner_lock_path(root), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)


def failed_state(root: Path, code: str = "EMAIL_TAKEN", owner_id: int | None = None, **fields: Any) -> bytes:
    """A committed restore from the app whose owner assignment failed with ``code`` (no ``owner_reset_path`` key)."""
    return write_state(root, owner_user_id=owner_id, owner_outcome=f"error:{code}", **fields)


def state_fields(root: Path) -> dict[str, Any]:
    return json.loads(restore_state_path(root).read_text(encoding="utf-8"))


# --- held_owner_lock ----------------------------------------------------------


def test_held_owner_lock_yields_true_and_holds_the_lock_until_the_block_ends(owner, data_dir):
    """(f) B5-1b §9.1: the lock is free: the block gets ``True``, another descriptor cannot take ``.restore/owner.lock``
    meanwhile, and it can once the block has ended."""
    print_section("(f) B5-1b held_owner_lock free")
    with held_lock_function(owner)(data_dir.root) as taken:
        assert taken is True, f"the lock was free: True, not {taken!r}"
        assert lock_is_free(data_dir.root) is False, "the lock is held inside the block"
    assert lock_is_free(data_dir.root) is True, "the lock is released when the block ends"
    print_success("held_owner_lock: True, held, released")


def test_held_owner_lock_yields_false_without_raising_when_another_process_holds_it(owner, data_dir):
    """(f) B5-1b §9.1: held elsewhere: ``False``, nothing raised, and the other holder keeps it."""
    with owner_lock_held(data_dir.root):
        with held_lock_function(owner)(data_dir.root) as taken:
            assert taken is False, f"the lock is held elsewhere: False, not {taken!r}"
        assert lock_is_free(data_dir.root) is False, "leaving the block does not release the other holder's lock"
    assert lock_is_free(data_dir.root) is True, "free once the holder lets go"
    print_success("held_owner_lock: False when held elsewhere")


def test_held_owner_lock_is_released_when_the_block_raises(owner, data_dir):
    """(f) B5-1b §9.1: the lock is released however the block ended."""
    with pytest.raises(RuntimeError, match=UNEXPECTED_TEXT):
        with held_lock_function(owner)(data_dir.root) as taken:
            assert taken is True
            raise RuntimeError(UNEXPECTED_TEXT)
    assert lock_is_free(data_dir.root) is True, "released after an exception in the block"
    print_success("held_owner_lock: released on error")


def test_held_owner_lock_uses_the_file_of_the_startup_step_with_mode_0600(owner, data_dir):
    """(f) B5-1b §9.1: the same file and mode as the startup step: a regular file ``.restore/owner.lock``, 0600 whatever
    the umask (0 here)."""
    lock = owner_lock_path(data_dir.root)
    assert not os.path.lexists(lock), "precondition: no owner lock yet"
    previous = os.umask(0)
    try:
        with held_lock_function(owner)(data_dir.root) as taken:
            assert taken is True
    finally:
        os.umask(previous)
    mode = os.lstat(lock).st_mode
    assert stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o600, f"a regular file of mode 0600: {oct(stat.S_IMODE(mode))}"
    print_success("held_owner_lock: owner.lock 0600")


@pytest.mark.asyncio
async def test_the_startup_step_leaves_the_owner_to_a_process_that_holds_held_owner_lock(owner, data_dir, monkeypatch):
    """(f) B5-1b §9.1: ``held_owner_lock`` and the step share one lock: while the block holds it the step returns ``None``
    and never calls A (the guard that they are the same file, not two that never meet)."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    with held_lock_function(owner)(data_dir.root) as taken:
        assert taken is True
        returned, raised, _events = await assigned(owner, data_dir.root)
    assert raised is None and returned is None and fake.calls == [], f"the lock held by the command: the step does nothing: {returned}, {fake.calls}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was"
    print_success("the step and held_owner_lock share the lock")


# --- reset_owner_assignment: the success --------------------------------------


def test_reset_owner_assignment_exception_is_a_restore_state_error_with_its_code():
    """(f) B5-1b §9.1: ``RestoreOwnerNotFailedError`` is a ``RestoreStateError`` of code ``owner_not_failed``."""
    error = not_failed_error()
    apply = apply_module()
    assert issubclass(error, apply.RestoreStateError), "a RestoreStateError, like the other refusals of the restore"
    assert error.code == "owner_not_failed", f"the stable word: {error.code!r}"
    print_success("RestoreOwnerNotFailedError: owner_not_failed")


@pytest.mark.parametrize("code", ASSIGNMENT_CODES)
def test_reset_clears_the_failed_outcome_and_changes_nothing_else(data_dir, code):
    """(f) B5-1b §9.1: ``owner_outcome`` ``error:<CODE>`` (each of A's codes): ``owner_outcome`` becomes ``None``, every
    other field of the state is equal as a value (the file is rewritten through the model, so dates may change their
    spelling: models are compared), the file has no ``owner_reset_path`` key before nor after, and nobody serving: ``False``."""
    print_section("(f) B5-1b reset_owner_assignment")
    reset = reset_function()
    failed_state(data_dir.root, code, data_dir.owner_id)
    before_raw = state_fields(data_dir.root)
    assert before_raw["owner_outcome"] == f"error:{code}" and "owner_reset_path" not in before_raw, "precondition: a failed assignment, no link key"
    before = apply_module().read_restore(data_dir.root).model_dump()
    answered = reset(data_dir.root)
    assert answered is False, f"nobody serves the data directory: False, not {answered!r}"
    after_raw = state_fields(data_dir.root)
    assert "owner_reset_path" not in after_raw, f"the file has no owner_reset_path key after the reset: {sorted(after_raw)}"
    after = apply_module().read_restore(data_dir.root).model_dump()
    assert after["owner_outcome"] is None, f"the outcome cleared: {after}"
    assert {key: value for key, value in after.items() if key != "owner_outcome"} == {key: value for key, value in before.items() if key != "owner_outcome"}, "nothing else changed, as a value"
    assert stat.S_IMODE(os.lstat(restore_state_path(data_dir.root)).st_mode) == 0o600, "the state stays readable by its owner only"
    print_success(f"{code}: cleared")


def test_reset_answers_true_when_a_server_serves_the_data_directory_and_still_clears(data_dir):
    """(f) B5-1b §9.1: a server serves the data directory: the outcome is cleared all the same and the answer is ``True``
    (the caller then does not call A: a running server only retries at its start)."""
    reset = reset_function()
    failed_state(data_dir.root, "USER_NOT_FOUND", data_dir.owner_id)
    with server_serving(data_dir.root):
        answered = reset(data_dir.root)
    assert answered is True, f"a server serves: True, not {answered!r}"
    after = state_fields(data_dir.root)
    assert (after["owner_outcome"], after["owner_user_id"]) == (None, data_dir.owner_id), f"cleared, the owner still named: {after}"
    assert "owner_reset_path" not in after, f"no owner_reset_path key: {sorted(after)}"
    print_success("served: True, cleared")


def test_reset_without_arguments_reads_the_configured_data_directory(data_dir):
    """(f) B5-1b §9.1: ``reset_owner_assignment()`` without arguments: the configured data directory."""
    reset = reset_function()
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    assert reset() is False, "the configured data directory's restore reset"
    assert recorded(data_dir.root) == (data_dir.owner_id, None), f"cleared: {recorded(data_dir.root)}"
    print_success("no arguments: configured data directory")


def test_reset_turns_the_problem_into_pending_and_a_second_call_refuses(data_dir):
    """(f) B5-1b §9.1: ``owner_assignment_problem`` goes from the code to ``"pending"`` (H's guard keeps serving nothing
    until the step gives the account); a second call finds nothing to reset (idempotent): ``RestoreOwnerNotFailedError``,
    ``restore.json`` byte for byte."""
    reset = reset_function()
    hook = problem_hook()
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    assert hook(data_dir.root) == "EMAIL_TAKEN", "precondition: the guard sees the code"
    reset(data_dir.root)
    assert hook(data_dir.root) == "pending", "after the reset the owner is pending again"
    after_first = state_bytes(data_dir.root)
    with pytest.raises(not_failed_error()):
        reset(data_dir.root)
    assert state_bytes(data_dir.root) == after_first, "the second call wrote nothing"
    print_success("problem: code -> pending; second call refused")


def test_reset_leaves_the_owner_pending_for_the_startup_step_to_assign_it(owner, data_dir, monkeypatch):
    """(f) B5-1b §9.1: end to end: a failed assignment, the reset, then the startup step calls A again and records its
    outcome; the guard sees nothing left."""
    reset = reset_function()
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    reset(data_dir.root)
    returned, raised, _events = asyncio.run(assigned(owner, data_dir.root))
    assert raised is None and returned is not None, f"the step ran: {returned}, {raised}"
    assert [call["user_id"] for call in fake.calls] == [data_dir.owner_id], f"A called once for the owner: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent"), f"the new outcome recorded: {recorded(data_dir.root)}"
    assert problem_hook()(data_dir.root) is None, "nothing keeps the owner out"
    print_success("reset then step: sent")


def test_a_failure_after_the_reset_can_be_reset_again(owner, data_dir, monkeypatch):
    """(f) B5-1b §9.1: A refuses again after the reset (a new ``error:<CODE>``): the new code is recorded and the way out
    is open again (a reset works once more)."""
    reset = reset_function()
    fake = FakeA(raises=FakeOwnerAssignmentError("USER_NOT_FOUND"))
    use_fake(monkeypatch, owner, fake)
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    reset(data_dir.root)
    asyncio.run(assigned(owner, data_dir.root))
    assert recorded(data_dir.root) == (data_dir.owner_id, "error:USER_NOT_FOUND"), f"the new code recorded: {recorded(data_dir.root)}"
    assert reset(data_dir.root) is False, "the second failure can be reset too"
    assert recorded(data_dir.root) == (data_dir.owner_id, None)
    print_success("fail, reset, fail, reset")


@pytest.mark.parametrize("via", ["cli", "panel"])
@pytest.mark.parametrize("code", ["EMAIL_TAKEN", "USER_NOT_FOUND"])
def test_reset_clears_the_failed_outcome_of_a_command_line_or_panel_restore_too(data_dir, via, code):
    """(f) B5-1j: ``owner_outcome`` ``error:<CODE>`` of a restore confirmed via ``cli`` or ``panel``, with the picked owner:
    cleared, nothing else changed, the guard goes from the code to ``pending``. Red before B5-1j: refused as «not failed»."""
    print_section(f"(f) B5-1j reset_owner_assignment via {via}")
    reset = reset_function()
    hook = problem_hook()
    failed_state(data_dir.root, code, data_dir.owner_id, confirmed_via=via)
    before = apply_module().read_restore(data_dir.root).model_dump()
    assert hook(data_dir.root) == code, "precondition: the guard sees the code (B5-1j: for the command line and the panel too)"
    assert reset(data_dir.root) is False, "nobody serves the data directory: False"
    after = apply_module().read_restore(data_dir.root).model_dump()
    assert after["owner_outcome"] is None and {key: value for key, value in after.items() if key != "owner_outcome"} == {key: value for key, value in before.items() if key != "owner_outcome"}, "the outcome cleared, nothing else"
    assert hook(data_dir.root) == "pending", "after the reset the owner is pending again"
    print_success(f"via {via}: {code} cleared")


@pytest.mark.parametrize("via", ["admin", "cli", "panel"])
def test_owner_pending_gives_the_stage_and_the_account_of_a_committed_restore_whoever_confirmed_it(data_dir, via):
    """(e) B5-1j: ``apply.owner_pending(data_dir)`` — the startup step's question — answers ``(stage_id, owner_user_id)`` for
    a committed restore with an owner named and no outcome, confirmed via ``admin``, ``cli`` or ``panel``; ``None`` once
    an outcome is recorded, and for a restore with nobody picked. Red before B5-1j for ``cli`` and ``panel``."""
    apply = apply_module()
    write_state(data_dir.root, confirmed_via=via, owner_user_id=data_dir.owner_id)
    assert apply.owner_pending(data_dir.root) == (STAGE_ID, data_dir.owner_id), f"via {via}: the stage and the account to give"
    apply.record_owner_outcome(data_dir.root, STAGE_ID, "sent")
    assert apply.owner_pending(data_dir.root) is None, "an outcome recorded: nothing pending"
    write_state(data_dir.root, confirmed_via=via, owner_user_id=None, owner_outcome="none")
    assert apply.owner_pending(data_dir.root) is None, "nobody picked: nothing pending"
    print_success(f"via {via}: owner_pending")


# --- reset_owner_assignment: the refusals -------------------------------------

#: (the state's fields; ``owner_outcome`` is given as the case needs) for a restore that is not
#: a failed owner assignment.
NOT_FAILED = [
    pytest.param({"owner_user_id": "owner"}, id="committed-pending-owner"),
    pytest.param({"owner_user_id": "owner", "owner_outcome": "sent"}, id="outcome-sent"),
    pytest.param({"owner_user_id": "owner", "owner_outcome": "link_only"}, id="outcome-link_only"),
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner", "owner_outcome": "link_only"}, id=f"via-{via}-link_only") for via in ("cli", "panel")),
    *(pytest.param({"confirmed_via": via, "owner_user_id": None, "owner_outcome": "none"}, id=f"via-{via}-nobody-picked") for via in ("cli", "panel")),
    pytest.param({"owner_user_id": None, "owner_outcome": "error:EMAIL_TAKEN"}, id="error-without-owner"),
    *(pytest.param({"status": status, "owner_user_id": "owner", "owner_outcome": "error:EMAIL_TAKEN"}, id=f"{status}-error") for status in ("pending", "applying", "applied", "rolling_back", "rolled_back")),
]


@pytest.mark.parametrize("fields", NOT_FAILED)
def test_reset_refuses_anything_but_a_failed_owner_assignment_and_writes_nothing(data_dir, fields):
    """(f) B5-1b §9.1, B5-1j: a restore that is not committed, with an owner and an ``error:`` outcome — whoever confirmed it —
    (no outcome yet; an outcome of A; nobody picked; no owner; any other phase): ``RestoreOwnerNotFailedError``,
    ``restore.json`` byte for byte."""
    reset = reset_function()
    given = {name: (data_dir.owner_id if value == "owner" else value) for name, value in fields.items()}
    before = write_state(data_dir.root, **given)
    with pytest.raises(not_failed_error()):
        reset(data_dir.root)
    assert state_bytes(data_dir.root) == before, f"{fields}: restore.json as it was"
    print_success(f"{fields}: refused")


def test_reset_refuses_when_there_is_no_state_and_creates_nothing_in_restore(data_dir):
    """(f) B5-1b §9.1: a ``.restore`` folder without a state: ``RestoreOwnerNotFailedError``, no ``restore.json`` made."""
    reset = reset_function()
    with pytest.raises(not_failed_error()):
        reset(data_dir.root)
    assert not os.path.lexists(restore_state_path(data_dir.root)), "no state made"
    print_success("no state: refused")


def test_reset_refuses_when_there_is_no_restore_folder_and_does_not_make_one(data_dir):
    """(f) B5-1b §9.1: no ``.restore`` folder at all: ``RestoreOwnerNotFailedError`` (not an ``OSError``), and the folder is
    not created."""
    reset = reset_function()
    shutil.rmtree(restore_dir(data_dir.root))
    with pytest.raises(not_failed_error()):
        reset(data_dir.root)
    assert not os.path.lexists(restore_dir(data_dir.root)), "no .restore folder made by a refusal"
    print_success("no .restore: refused, nothing made")


@pytest.mark.parametrize("kind", ["not-json", "a-folder", "format-2"])
def test_reset_propagates_an_unreadable_state_and_leaves_it_alone(data_dir, kind):
    """(f) B5-1b §9.1: a state that cannot be read: ``RestoreStateUnreadableError`` (not the refusal), nothing changed."""
    reset = reset_function()
    unreadable_as(data_dir.root, kind)
    path = restore_state_path(data_dir.root)
    before = None if path.is_dir() else path.read_bytes()
    with pytest.raises(apply_module().RestoreStateUnreadableError):
        reset(data_dir.root)
    assert (None if path.is_dir() else path.read_bytes()) == before, f"{kind}: the state as it was"
    print_success(f"{kind}: RestoreStateUnreadableError")


def test_reset_while_the_owner_lock_is_held_raises_restore_in_use_and_writes_nothing(data_dir):
    """(f) B5-1b §9.1: another process holds ``.restore/owner.lock`` (the startup step, a second command): ``RestoreInUseError``
    without waiting, ``restore.json`` byte for byte; once the lock is free the reset works."""
    reset = reset_function()
    before = failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    with owner_lock_held(data_dir.root):
        with pytest.raises(apply_module().RestoreInUseError):
            reset(data_dir.root)
    assert state_bytes(data_dir.root) == before, "restore.json as it was"
    assert reset(data_dir.root) is False and recorded(data_dir.root) == (data_dir.owner_id, None), "the lock free: the reset works"
    print_success("owner lock held: RestoreInUseError")


def test_reset_releases_the_owner_lock_when_it_returns_or_raises(data_dir):
    """(f) B5-1b §9.1: the lock is taken for the call only: free afterwards, after a success and after a refusal."""
    reset = reset_function()
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    reset(data_dir.root)
    assert lock_is_free(data_dir.root) is True, "free after a success"
    with pytest.raises(not_failed_error()):
        reset(data_dir.root)
    assert lock_is_free(data_dir.root) is True, "free after a refusal"
    print_success("owner lock released")


def test_reset_logs_one_line_with_the_code_and_never_an_address_a_name_or_a_link(data_dir):
    """(f) B5-1b §9.1: one log line about the reset, naming the stage, the user id and the code that was reset; the owner's
    address, the username and any link are in no line."""
    reset = reset_function()
    failed_state(data_dir.root, "EMAIL_TAKEN", data_dir.owner_id)
    with capture_logs() as events:
        get_logger(OWNER_MODULE).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), "barrier: a logger reaches capture_logs"
        reset(data_dir.root)
    lines = [event for event in events if event.get("event") != LOG_CANARY]
    about_it = [event for event in lines if "EMAIL_TAKEN" in repr(event)]
    assert len(about_it) == 1, f"one line names the code that was reset: {lines}"
    assert STAGE_ID in repr(about_it[0]) and str(data_dir.owner_id) in repr(about_it[0]), f"it names the stage and the user id: {about_it[0]}"
    no_secret_in(lines)
    print_success("reset: one log line")

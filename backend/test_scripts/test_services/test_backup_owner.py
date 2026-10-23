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
    off): the fake reads the owner's row through it. What it answers is recorded in ``restore.json`` and in the state
    returned: ``owner_outcome`` the outcome's value (``sent``, ``link_only``, ``already_issued``, ``already_done``);
    ``owner_reset_path`` the result's ``reset_path`` for ``link_only`` only. ``OwnerAssignmentError`` (each of A's four
    codes): ``owner_outcome`` ``error:<CODE>``, no path. Any other exception: logged, nothing recorded, the state still
    waiting for the next start, nothing raised. ``_assign_owner()`` raising ``ImportError`` (A not merged): an error
    logged, nothing recorded, nothing raised. Without arguments, the configured data directory.
(c) The log: no line of any of these calls holds the owner's email, its username, the reset path, or the text of an
    unexpected exception (its type only).
(d) Security addendum §7.3 (written RED before it): the step takes a non-blocking exclusive ``flock`` on
    ``.restore/owner.lock`` (created 0600) before calling A and until the outcome is recorded; a worker that cannot take
    it returns ``None`` without calling A. Two workers at once (two tasks; A's first call held until one returns): A
    called once. The lock held by the test (``fcntl.flock`` on a descriptor of its own): ``None``, A not called.
(e) Security addendum §7.4 (written RED before it): ``apply.owner_assignment_problem(data_dir=None)``, the hook of H's
    guard: ``"pending"`` for a committed restore confirmed via ``admin`` with an owner and no outcome, the code of an
    ``error:<CODE>``, ``None`` otherwise — and for a state that cannot be read (``restore_state_problem``'s); never
    raises.

How. A's code is not in this branch. Its signature (A5-2, ``side-session-notes/…/A5-2-firma-ripristino-titolare.md``)
is played by the fakes of this module: ``FakeOutcome`` (a ``StrEnum`` of A's four values), ``FakeResult`` (A's frozen
dataclass ``OwnerResetResult``: ``outcome``, ``user_id``, ``username``, ``email``, ``reset_path``, ``expires_at``) and
``FakeOwnerAssignmentError`` (an ``Exception`` with A's ``code``). ``owner.py`` looks A's function up through
``owner._assign_owner()``, a function of no argument that returns the pair ``(assign_owner_and_send_reset,
OwnerAssignmentError)`` — it imports ``backend.app.services.email.flows`` lazily —; every test replaces it with one that
returns a ``FakeA`` (an async callable recording each call) and ``FakeOwnerAssignmentError``, or raises ``ImportError``.

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
#: A's reset link for ``link_only``: a secret, never in a log line.
RESET_PATH = "/reset-password#token=b51-secret-token-never-in-a-log-0123456789"
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
    """A's ``OwnerResetOutcome``."""

    SENT = "sent"
    LINK_ONLY = "link_only"
    ALREADY_ISSUED = "already_issued"
    ALREADY_DONE = "already_done"


@dataclass(frozen=True)
class FakeResult:
    """A's ``OwnerResetResult``."""

    outcome: FakeOutcome
    user_id: int
    username: str
    email: str
    reset_path: str | None
    expires_at: datetime | None


class FakeOwnerAssignmentError(Exception):
    """A's ``OwnerAssignmentError``: raised for a missing precondition, its ``code`` one of ``ASSIGNMENT_CODES``. Its
    message names the owner's email, as a careless one could: it must never reach the log."""

    def __init__(self, code: str) -> None:
        super().__init__(f"the owner {OWNER_EMAIL} cannot be assigned: {code}")
        self.code = code


@dataclass
class FakeA:
    """A's ``assign_owner_and_send_reset(session, user_id)``: each call recorded with what its session showed (its type,
    whether it expires on commit, the username of the row ``user_id`` in its database), then ``outcome`` answered or
    ``raises`` raised."""

    outcome: FakeOutcome | None = None
    raises: BaseException | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, session: Any, user_id: int) -> FakeResult:
        row = (await session.execute(text("SELECT username FROM users WHERE id = :id"), {"id": user_id})).first()
        sync = getattr(session, "sync_session", None)
        self.calls.append({"user_id": user_id, "async_session": isinstance(session, AsyncSession), "expire_on_commit": getattr(sync, "expire_on_commit", None), "username": row[0] if row else None})
        if self.raises is not None:
            raise self.raises
        assert self.outcome is not None, "a FakeA answers an outcome or raises"
        reset_path = RESET_PATH if self.outcome is FakeOutcome.LINK_ONLY else None
        expires = None if self.outcome is FakeOutcome.ALREADY_DONE else FINISHED_AT + timedelta(days=3)
        return FakeResult(outcome=self.outcome, user_id=user_id, username=OWNER_USERNAME, email=OWNER_EMAIL, reset_path=reset_path, expires_at=expires)


def use_fake(monkeypatch: pytest.MonkeyPatch, owner: ModuleType, fake: FakeA) -> None:
    """``owner._assign_owner`` replaced: it returns the pair ``(fake, FakeOwnerAssignmentError)``, as the real one
    returns ``(flows.assign_owner_and_send_reset, flows.OwnerAssignmentError)``."""
    assert callable(getattr(owner, "_assign_owner", None)), "[new] B5-1: owner._assign_owner() is the lazy lookup of A's function (interface §4)"
    monkeypatch.setattr(owner, "_assign_owner", lambda: (fake, FakeOwnerAssignmentError))


def a_not_merged(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> list[str]:
    """``owner._assign_owner`` raising ``ImportError``, as the lazy import does while A's code is not merged; the calls."""
    assert callable(getattr(owner, "_assign_owner", None)), "[new] B5-1: owner._assign_owner() is the lazy lookup of A's function (interface §4)"
    calls: list[str] = []

    def missing() -> tuple[Any, type[Exception]]:
        calls.append("_assign_owner")
        raise ImportError("cannot import name 'assign_owner_and_send_reset' from 'backend.app.services.email.flows'")

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


def write_state(root: Path, *, status: str = "committed", confirmed_via: str = "admin", owner_user_id: int | None = None, owner_outcome: str | None = None, owner_reset_path: str | None = None) -> bytes:
    """``.restore/restore.json`` as a start leaves a restore in ``status``, raw JSON with the owner's keys: its bytes."""
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
        "owner_reset_path": owner_reset_path,
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


def recorded(root: Path) -> tuple[Any, Any, Any]:
    """What ``restore.json`` says of the owner: id, outcome, reset path."""
    record = json.loads(restore_state_path(root).read_text(encoding="utf-8"))
    return tuple(record.get(name, "<missing>") for name in ("owner_user_id", "owner_outcome", "owner_reset_path"))


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
    """No log line holds the owner's email, its username, the reset path, nor any of ``extra``."""
    lines = repr(events).lower()
    shown = [secret for secret in (OWNER_EMAIL, OWNER_USERNAME, RESET_PATH, "b51-secret-token", *extra) if secret.lower() in lines]
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
    there —; its outcome recorded in ``restore.json`` and in the state returned, the reset path only for ``link_only``.
    No log line holds the email, the username or the path."""
    print_section(f"(b) B5-1 assign_restored_owner: {outcome.value}")
    fake = FakeA(outcome=outcome)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert fake.calls == [{"user_id": data_dir.owner_id, "async_session": True, "expire_on_commit": False, "username": OWNER_USERNAME}], f"A's function called once, with the owner's id and a session on this database: {fake.calls}"
    path = RESET_PATH if outcome is FakeOutcome.LINK_ONLY else None
    assert recorded(data_dir.root) == (data_dir.owner_id, outcome.value, path), f"restore.json records {outcome.value}: {recorded(data_dir.root)}"
    assert returned is not None and (returned.status, returned.owner_user_id, returned.owner_outcome, returned.owner_reset_path) == ("committed", data_dir.owner_id, outcome.value, path), f"the state returned says it too: {returned}"
    no_secret_in(events)
    print_success(f"{outcome.value} recorded, one call")


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ASSIGNMENT_CODES)
async def test_an_owner_assignment_error_is_recorded_as_error_and_its_code(owner, data_dir, monkeypatch, code):
    """(b) A's ``OwnerAssignmentError``: ``owner_outcome`` ``error:<CODE>``, no reset path, nothing raised; its message
    (which names the email) never in the log."""
    fake = FakeA(raises=FakeOwnerAssignmentError(code))
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 1, f"A's function called once: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, f"error:{code}", None), f"restore.json records error:{code}: {recorded(data_dir.root)}"
    no_secret_in(events)
    print_success(f"error:{code}")


@pytest.mark.asyncio
async def test_an_unexpected_failure_leaves_the_owner_pending_for_the_next_start(owner, data_dir, monkeypatch):
    """(b) Any other exception of A's function: logged by its type only, nothing recorded — the next start calls A again
    (A is idempotent: ``already_issued``) —, nothing raised."""
    fake = FakeA(raises=RuntimeError(UNEXPECTED_TEXT))
    use_fake(monkeypatch, owner, fake)
    before = write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert len(fake.calls) == 1, f"A's function called once: {fake.calls}"
    assert recorded(data_dir.root) == (data_dir.owner_id, None, None), f"nothing recorded: {recorded(data_dir.root)}"
    assert state_bytes(data_dir.root) == before, "restore.json as it was"
    assert levels(events) & {"warning", "error", "critical"}, f"the failure is logged: {events}"
    no_secret_in(events, UNEXPECTED_TEXT)
    # The next start: A answers, the outcome is recorded.
    fake.raises, fake.outcome = None, FakeOutcome.ALREADY_ISSUED
    _returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None and recorded(data_dir.root) == (data_dir.owner_id, "already_issued", None), f"the next start records already_issued: {recorded(data_dir.root)}"
    print_success("RuntimeError: pending, logged by type; then already_issued")


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
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner"}, id=f"committed-via-{via}") for via in ("cli", "panel")),
    pytest.param({"owner_user_id": None}, id="committed-no-owner"),
    *(pytest.param({"owner_user_id": "owner", "owner_outcome": outcome}, id=f"already-{outcome}") for outcome in ("sent", "link_only", "already_issued", "already_done", "error:EMAIL_TAKEN")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fields", LEFT_ALONE)
async def test_anything_but_a_committed_admin_restore_waiting_for_its_owner_is_left_alone(owner, data_dir, monkeypatch, fields):
    """(b) No state; a restore not committed; one confirmed via ``cli`` or ``panel`` (even with an owner id); one
    without an owner; one whose outcome is recorded: ``None`` returned, A's function never called, ``restore.json`` byte
    for byte."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    before = None
    if fields is not None:
        given = {name: (data_dir.owner_id if value == "owner" else value) for name, value in fields.items()}
        if given.get("owner_outcome") == "link_only":
            given["owner_reset_path"] = RESET_PATH
        before = write_state(data_dir.root, **given)
    returned, raised, events = await assigned(owner, data_dir.root)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert (returned, fake.calls) == (None, []), f"{fields}: nothing done, A never called: {returned}, {fake.calls}"
    assert state_bytes(data_dir.root) == before, f"{fields}: restore.json as it was"
    no_secret_in(events)
    print_success(f"{fields}: left alone")


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


@pytest.mark.asyncio
async def test_without_arguments_the_step_reads_the_configured_data_directory(owner, data_dir, monkeypatch):
    """(b) ``assign_restored_owner()`` without arguments: the configured data directory (the startup step's call)."""
    fake = FakeA(outcome=FakeOutcome.SENT)
    use_fake(monkeypatch, owner, fake)
    write_state(data_dir.root, owner_user_id=data_dir.owner_id)
    _returned, raised, events = await assigned(owner, None)
    assert raised is None, f"the step never raises: {type(raised).__name__}: {raised}"
    assert (len(fake.calls), recorded(data_dir.root)) == (1, (data_dir.owner_id, "sent", None)), f"the configured data directory's restore: {fake.calls}, {recorded(data_dir.root)}"
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

    async def __call__(self, session: Any, user_id: int) -> FakeResult:
        self.entered.append(user_id)
        if len(self.entered) == 1:
            try:
                await asyncio.wait_for(self.released.wait(), timeout=DEADLINE_S)
            except TimeoutError:
                self.timed_out = True
        return await super().__call__(session, user_id)


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
    assert recorded(data_dir.root) == (data_dir.owner_id, "sent", None), f"the outcome recorded once: {recorded(data_dir.root)}"
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
    assert (raised, len(fake.calls), recorded(data_dir.root)) == (None, 1, (data_dir.owner_id, "sent", None)), f"the lock free: the owner assigned: {fake.calls}, {recorded(data_dir.root)}"
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
    *(pytest.param({"confirmed_via": via, "owner_user_id": "owner"}, None, id=f"committed-via-{via}") for via in ("cli", "panel")),
    pytest.param({"owner_user_id": None}, None, id="committed-no-owner"),
    *(pytest.param({"status": status, "owner_user_id": "owner"}, None, id=f"{status}") for status in ("pending", "applying", "applied", "rolling_back", "rolled_back")),
]


@pytest.mark.parametrize(("fields", "expected"), PROBLEMS)
def test_owner_assignment_problem_says_whether_the_owner_s_account_is_still_open(data_dir, fields, expected):
    """(e) B5-1 §7.4: for the last restore — committed, confirmed from the app, an owner named — ``"pending"`` while no
    outcome is recorded, the code of an ``error:<CODE>``; ``None`` otherwise: no restore, an outcome of A, a restore
    via the panel or the command line, without an owner, or not committed. Nothing written."""
    print_section("(e) B5-1 §7.4 owner_assignment_problem")
    hook = problem_hook()
    before = None
    if fields is not None:
        given = {name: (data_dir.owner_id if value == "owner" else value) for name, value in fields.items()}
        if given.get("owner_outcome") == "link_only":
            given["owner_reset_path"] = RESET_PATH
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

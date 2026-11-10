"""E1c: the post-migration fix ``event_types``, and the row-count changes a fix declares (decision 23 of release 1.3, I-09).

Until 1.3 an asset event's type was stored as it came: a CSV written by hand could save ``dividend`` or ``dividendo``,
and every later read of that asset's events failed on ``AssetEventType``. ``EventTypesFix``
(``backend/app/db/post_migration/event_types.py``, ``fix_id = "event_types"``) repairs the rows already stored. It
deletes some, and until now no fix could change a row count: a fix now declares how its ``apply`` changes the row
count of each table, and the framework checks it exactly. The contract pinned here:

A. The framework. ``PostMigrationFix.row_count_changes(anomaly, ctx) -> dict[str, int]`` (``{}`` by default: most
   fixes change no count) says by how much ``apply`` changes each table's row count, negative for the rows it deletes.
   After ``apply`` every table must hold its count before plus the change declared for it — a table not named keeps
   its count — or the fix fails with ``row counts not as expected: <table> (expected N, found M)``. Pinned with a fix
   of these tests only, made the run's only fix (``FIXES`` monkeypatched), on a database at head holding three events:
   1. it declares ``{"asset_events": -1}`` and deletes one: ``applied``, the event gone, no backup. RED: today the
      declaration is never asked for, and any change of a row count fails the fix;
   2. it declares -1 and deletes two: ``failed``, the database as it was, the backup kept, the error naming
      ``asset_events`` with the count expected and the count found. RED on that wording only: today the error reads
      ``row counts changed: asset_events``;
   3. it declares nothing, or another table, and deletes one: ``failed``, the database as it was, the backup kept.
      Guard, green today and after;
   4. its ``row_count_changes`` raises ``RuntimeError("boom")``: the run still returns its report — ``failed``, an
      error of the fix naming ``boom``, the database as it was, the backup kept and named in ``backup_path``. RED:
      today the declaration is never asked for, so the fix goes on to its ``apply`` and fails on the row count it
      changed — no error names ``boom``.
B. ``event_types``, registered after ``autoincrement``, on the rows of ``asset_events`` whose ``type`` is not exactly
   one of the five ``AssetEventType`` values:
   1. a type valid once trimmed and upper-cased (``dividend``, `` Split ``, ``price_adjustment``) is corrected in
      place: the same id, ``updated_at`` moved to the run's time, every other column as it was, its transactions
      still linked and untouched;
   2. any other (``dividendo``, ``bonus``): each transaction linked to it loses that link — ``asset_event_id`` NULL,
      ``updated_at`` moved, nothing else changed: the transaction stays — then the event is deleted, a provider's
      (``provider_assignment_id`` set) as a user's;
   3. an event of a valid type is untouched, ``updated_at`` included, and so are its transactions;
   4. the run: ``applied``, no error, no backup left, ``PRAGMA foreign_key_check`` empty as before it,
      ``asset_events`` down by exactly the deletions, every other table as it was, only the rows above changed; a
      second run ``clean``, nothing written;
   5. a dry run: ``would_apply``, the database file byte-identical, no backup. A database whose types are all valid:
      ``clean``, nothing written, no backup;
   6. the detection warning (logger ``backend.app.db.post_migration.event_types``), dry run or not: ``count``,
      ``corrections`` (the ids by ``<stored>-><valid>``), ``deletions`` (the ids by stored type) and
      ``unlinked_transactions``;
   7. after the commit, one INFO line per corrected event (``Asset event type corrected``: ``event_id``,
      ``from_type``, ``to_type``), per unlinked transaction (``Transaction unlinked from an asset event of unknown
      type``: ``transaction_id``, ``former_event_id``) and per deleted event (``Asset event of unknown type
      deleted``: ``event_id``, ``type``, ``value``, ``currency``, ``is_auto``, ``unlinked_transactions``); none on a
      dry run, none on a failed run;
   8. a verification that fails (``EventTypesFix.verify`` made to report a problem): ``failed`` with it, the database
      as it was, the backup kept beside it holding that database, no INFO line.
   All RED until the cure: today no fix has the id ``event_types``.

Independent of ``orphan_pair_halves`` (N1b-2): nothing is imported from its tests, ``FIXES`` is never asserted whole,
and the rows planted here give that fix, when it is there, nothing to do. A test needing ``EventTypesFix`` finds it by
``fix_id``, or imports its module in its own body: before the cure each test fails on an assertion of its own, and
the file still collects.

The databases. One is built at head by the real migrations — ``alembic upgrade head`` in a child process, always with
``-x sqlalchemy.url=``, as test_post_migration.py does — and copied for each test. The events and their transactions
are written with sqlite3, foreign keys on: the ORM refuses a type it does not know. The expected corrections,
deletions and lists are written out here, never read from the fix. Every database is temporary, and the configured
data dir points at a sandbox with a canary: nothing here can reach the lane's database.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

import pytest
import structlog
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT
from backend.app.db import post_migration
from backend.app.db.post_migration import PostMigrationReport
from backend.app.db.post_migration.base import FixContext, PostMigrationFix

FIX = "event_types"
FIX_MODULE = "backend.app.db.post_migration.event_types"
LOGGER = FIX_MODULE  # the fix logs as its module: get_logger(__name__)
RUN_LOGGER = "backend.app.db.post_migration"
CORRECTED = "Asset event type corrected"
UNLINKED = "Transaction unlinked from an asset event of unknown type"
DELETED = "Asset event of unknown type deleted"
APPLIED_EVENT = "Post-migration fixes applied and verified"
FAILED_EVENT = "Post-migration fix failed: the database was left as it was"
PROVOKED = "provoked: the fix's own check found a problem"
TEST_FIX = "test_declared_row_counts"  # the fix of the framework's tests (A), only ever registered by a monkeypatch
BOOM = "boom"  # what A.4's row_count_changes raises, and what the fix's error must name
TIMESTAMP = "%Y-%m-%d %H:%M:%S.%f"  # how the app stores a DATETIME, and the planted rows with it
STAMP = "2019-09-04 10:00:00.000000"  # created_at and updated_at of every planted row
CHILD_TIMEOUT = 300
CANARY = b"canary: a configured data dir that no run was given\n"
CANARY_FILE = Path("broker_reports", "uploaded", "broker_999", "canary.csv")

NOT_APPLIED = "barrier: the fix did not report 'applied', so the rows below say nothing about what it does"
NOTHING_DONE = "barrier: no event was corrected or deleted, so 'untouched' would pass for a run that does nothing"
NOT_CAPTURED = "barrier: the capture saw no event of the run, so 'no line' would pass for a logger that never reaches it"


@dataclass(frozen=True)
class PlantedEvent:
    """An event planted on X: its type as stored, the valid type it must take when the fix corrects it, whether a
    provider wrote it (``provider_assignment_id`` set), and the type of each transaction linked to it."""

    stored: str
    becomes: Optional[str] = None
    provider: bool = False
    transactions: tuple[str, ...] = ()


# One event of each valid type: nothing may touch them, nor their transactions.
VALID = {
    "DIVIDEND, linked": PlantedEvent("DIVIDEND", transactions=("DIVIDEND",)),
    "INTEREST, linked": PlantedEvent("INTEREST", transactions=("INTEREST",)),
    "PRICE_ADJUSTMENT, from a provider": PlantedEvent("PRICE_ADJUSTMENT", provider=True),
    "SPLIT, from a provider": PlantedEvent("SPLIT", provider=True),
    "MATURITY_SETTLEMENT": PlantedEvent("MATURITY_SETTLEMENT"),
}
# Valid once trimmed and upper-cased: corrected in place. Two share their stored type, which the warning groups.
CORRECTIONS = {
    "dividend, linked": PlantedEvent("dividend", "DIVIDEND", transactions=("DIVIDEND",)),
    "dividend, from a provider": PlantedEvent("dividend", "DIVIDEND", provider=True),
    "' Split ', from a provider": PlantedEvent(" Split ", "SPLIT", provider=True),
    "price_adjustment, linked twice": PlantedEvent("price_adjustment", "PRICE_ADJUSTMENT", transactions=("ADJUSTMENT", "ADJUSTMENT")),
}
# Unknown even trimmed and upper-cased: deleted, their transactions unlinked first. Two share their stored type.
DELETIONS = {
    "dividendo, linked twice": PlantedEvent("dividendo", transactions=("DIVIDEND", "DIVIDEND")),
    "bonus, from a provider, linked": PlantedEvent("bonus", provider=True, transactions=("ADJUSTMENT",)),
    "bonus, alone": PlantedEvent("bonus"),
}
EVENTS = {**VALID, **CORRECTIONS, **DELETIONS}
# What a transaction linked to an event carries besides its link, by its type: every column the fix must keep is set.
LINKED_TRANSACTION = {
    "DIVIDEND": {"quantity": "0", "amount": "2.5", "currency": "EUR", "tags": "event,cash"},
    "INTEREST": {"quantity": "0", "amount": "1.25", "currency": "EUR", "tags": "event,cash"},
    "ADJUSTMENT": {"quantity": "3", "amount": "0", "cost_basis_override": "20", "cost_basis_currency": "EUR", "tags": "event,units"},
}

Tables = dict[str, list[tuple[Any, ...]]]
Rows = dict[int, dict[str, Any]]


@dataclass(frozen=True)
class Run:
    """One observed call of ``run_post_migration_fixes``: its report, its log, and the database just before and just after it."""

    db: Path
    report: PostMigrationReport
    tables_before: Tables
    tables_after: Tables
    events_before: Rows
    events_after: Rows
    transactions_before: Rows
    transactions_after: Rows
    violations_before: list[tuple[Any, ...]]
    violations_after: list[tuple[Any, ...]]
    digest_before: str
    digest_after: str
    backups_after: list[str]
    logs: list[dict[str, Any]]
    started: datetime
    finished: datetime
    ids: dict[str, int] = field(default_factory=dict)

    @property
    def counts_before(self) -> dict[str, int]:
        return _counts(self.tables_before)

    @property
    def counts_after(self) -> dict[str, int]:
        return _counts(self.tables_after)

    def warnings(self) -> list[dict[str, Any]]:
        """The detection warnings of the fix."""
        return [entry for entry in self.logs if entry.get("logger") == LOGGER and entry.get("log_level") == "warning"]

    def row_lines(self) -> list[dict[str, Any]]:
        """The fix's lines about a row it changed, at whatever level."""
        return [entry for entry in self.logs if entry.get("logger") == LOGGER and entry.get("event") in (CORRECTED, UNLINKED, DELETED)]

    def lines(self, event: str, *fields: str) -> list[tuple[Any, ...]]:
        """The fix's lines ``event``, each as ``(level, *fields)``, in a stable order."""
        return sorted((tuple(entry.get(name) for name in ("log_level", *fields)) for entry in self.logs if entry.get("logger") == LOGGER and entry.get("event") == event), key=repr)

    def deleted_lines(self) -> list[tuple[Any, ...]]:
        """The ``deleted`` lines as ``(level, event_id, type, value, currency, is_auto, unlinked_transactions)``: the value a Decimal, the ids sorted."""
        found = self.lines(DELETED, "event_id", "type", "value", "currency", "is_auto", "unlinked_transactions")
        return sorted(((level, event_id, kind, _number(value), currency, is_auto, _sorted(ids)) for level, event_id, kind, value, currency, is_auto, ids in found), key=repr)

    def closing_events(self) -> list[str]:
        return [entry["event"] for entry in self.logs if entry.get("logger") == RUN_LOGGER and entry.get("event") in (APPLIED_EVENT, FAILED_EVENT)]


# =============================================================================
# HELPERS — the configured data dir and the migrations (as test_post_migration.py)
# =============================================================================


@contextmanager
def _configured_sandbox(sandbox: Path) -> Iterator[Path]:
    """Point the configured test data dir at ``sandbox``, with a canary in it, so that nothing can reach the lane's data."""
    canary = sandbox / CANARY_FILE
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_bytes(CANARY)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LIBREFOLIO_TEST_MODE", "1")
        patch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(sandbox))
        yield sandbox
    assert canary.is_file() and canary.read_bytes() == CANARY, f"safety: a run touched the configured data dir {sandbox}, which it was never given"


def _child_env() -> dict[str, str]:
    """This process's environment for a child process: only ever inside a configured sandbox, canary and all."""
    env = dict(os.environ)
    sandbox = Path(env.get("LIBREFOLIO_TEST_DATA_DIR") or "/nonexistent")
    assert env.get("LIBREFOLIO_TEST_MODE") == "1" and (sandbox / CANARY_FILE).is_file(), "safety: a child process starts only with the configured data dir pointed at a sandbox"
    return env


def _alembic_upgrade_head(db: Path) -> None:
    """``alembic upgrade head`` on ``db`` in a child process — always with ``-x sqlalchemy.url=``: without it ``env.py`` migrates the configured database."""
    assert db.is_absolute(), db
    db.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url=sqlite:///{db}", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    assert completed.returncode == 0, f"setup: alembic upgrade head failed on {db}\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}"


# =============================================================================
# HELPERS — databases
# =============================================================================


def _connect(db: Path) -> closing[sqlite3.Connection]:
    """A connection to an existing database: ``sqlite3.connect`` would silently create a missing one."""
    assert db.is_file(), f"{db} does not exist"
    return closing(sqlite3.connect(db))


def _copy(head: Path, root: Path) -> Path:
    """A copy of the database at head, for one test."""
    db = root / "data" / "sqlite" / "app.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(head, db)
    return db


def _settle(db: Path) -> None:
    """Fold any WAL content into the database file, so that the file's bytes are the whole database."""
    with _connect(db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _digest(db: Path) -> str:
    return hashlib.sha256(db.read_bytes()).hexdigest()


def _backups(db: Path) -> list[str]:
    """The backup files beside ``db``: ``<db name>.pre-…``, or anything ending in ``.bak``."""
    return sorted(path.name for path in db.parent.iterdir() if path.name.startswith(f"{db.name}.pre-") or path.name.endswith(".bak"))


def _tables(db: Path) -> Tables:
    """Every row of every table, SQLite's own included."""
    with _connect(db) as conn:
        names = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {name: sorted(conn.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr) for name in names}


def _by_id(db: Path, table: str) -> Rows:
    """The rows of ``table`` by id, each as ``{column: value}``."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY id')}


def _counts(tables: Tables) -> dict[str, int]:
    """The row count of every table but SQLite's own: what the framework compares."""
    return {name: len(rows) for name, rows in tables.items() if not name.startswith("sqlite_")}


def _other_tables(tables: Tables) -> Tables:
    """Every table but the two the fix writes, SQLite's own included."""
    return {name: rows for name, rows in tables.items() if name not in ("asset_events", "transactions")}


def _foreign_key_violations(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute("PRAGMA foreign_key_check").fetchall()


# =============================================================================
# HELPERS — the planted rows
# =============================================================================


def _asset(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, 'EUR', 'STOCK', 1, ?, ?)", (name, STAMP, STAMP)).lastrowid


def _event(conn: sqlite3.Connection, **columns: Any) -> int:
    """One asset event stamped STAMP, its type stored as given: nothing here refuses one."""
    row = {"created_at": STAMP, "updated_at": STAMP, **columns}
    names, marks = ", ".join(row), ", ".join("?" for _ in row)
    return conn.execute(f"INSERT INTO asset_events ({names}) VALUES ({marks})", tuple(row.values())).lastrowid


def _transaction(conn: sqlite3.Connection, **columns: Any) -> int:
    """One transaction stamped STAMP; ``columns`` add to or replace the defaults."""
    row = {"date": "2019-09-04", "quantity": "0", "amount": "0", "created_at": STAMP, "updated_at": STAMP, **columns}
    names, marks = ", ".join(row), ", ".join("?" for _ in row)
    return conn.execute(f"INSERT INTO transactions ({names}) VALUES ({marks})", tuple(row.values())).lastrowid


def _transaction_label(event_label: str, n: int) -> str:
    return f"{event_label} / transaction {n}"


def _linked(events: dict[str, PlantedEvent]) -> list[tuple[str, str]]:
    """``(event label, transaction label)`` of each transaction linked to one of ``events``, in planting order."""
    return [(label, _transaction_label(label, n)) for label, event in events.items() for n in range(1, len(event.transactions) + 1)]


def _plant(db: Path, *, with_unknown_types: bool = True) -> dict[str, int]:
    """X, an asset a provider prices, with the events of VALID — and of CORRECTIONS and DELETIONS unless
    ``with_unknown_types`` is False — each with its transactions, and a BUY linked to no event. Ids by label.

    Written with sqlite3 and foreign keys on: every row consistent, each type stored as it comes. Event n is dated the
    15th of month n and worth n.nn, in USD when n is odd, in EUR otherwise; its notes are its label.
    """
    events = EVENTS if with_unknown_types else VALID
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        broker = conn.execute("INSERT INTO brokers (name, created_at, updated_at) VALUES ('Events', ?, ?)", (STAMP, STAMP)).lastrowid
        x = _asset(conn, "X")
        assignment = conn.execute("INSERT INTO asset_provider_assignments (asset_id, provider_code, identifier, identifier_type, created_at, updated_at) VALUES (?, 'mockprov', 'X', 'TICKER', ?, ?)", (x, STAMP, STAMP)).lastrowid
        ids = {"BUY, no event": _transaction(conn, broker_id=broker, asset_id=x, type="BUY", quantity="10", amount="-200", currency="EUR", description="10 X", tags="core")}
        for n, (label, event) in enumerate(events.items(), start=1):
            day = f"2019-{n:02d}-15"
            provider_assignment_id = assignment if event.provider else None
            ids[label] = _event(conn, asset_id=x, date=day, type=event.stored, value=f"{n}.{n:02d}", currency="USD" if n % 2 else "EUR", provider_assignment_id=provider_assignment_id, notes=label)
            for k, kind in enumerate(event.transactions, start=1):
                ids[_transaction_label(label, k)] = _transaction(conn, broker_id=broker, asset_id=x, type=kind, date=day, asset_event_id=ids[label], description=f"{label}, transaction {k}", **LINKED_TRANSACTION[kind])
        conn.commit()
    assert _foreign_key_violations(db) == [], "setup: every planted row is consistent"
    return ids


def _plant_three_events(db: Path) -> list[int]:
    """Three DIVIDEND events of an asset, no transaction linked to them: rows a fix can delete without breaking a link. Their ids."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        asset = _asset(conn, "Three dividends")
        ids = [_event(conn, asset_id=asset, date=f"2019-0{n}-15", type="DIVIDEND", value=f"0.{n}", currency="EUR") for n in (1, 2, 3)]
        conn.commit()
    return ids


# =============================================================================
# HELPERS — observing a run
# =============================================================================


def _observe(db: Path, ids: dict[str, int], *, dry_run: bool = False) -> Run:
    """Call ``run_post_migration_fixes`` once, without a data dir; record the database, the backups and the log around the call."""
    tables_before = _tables(db)
    events_before, transactions_before = _by_id(db, "asset_events"), _by_id(db, "transactions")
    violations_before = _foreign_key_violations(db)
    _settle(db)
    digest_before = _digest(db)
    started = datetime.now(UTC).replace(tzinfo=None)
    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        report = post_migration.run_post_migration_fixes(db, None, dry_run=dry_run)
    finished = datetime.now(UTC).replace(tzinfo=None)
    digest_after = _digest(db)  # first, before any connection of ours
    backups_after = _backups(db)  # before anything opens a backup
    return Run(
        db=db,
        report=report,
        tables_before=tables_before,
        tables_after=_tables(db),
        events_before=events_before,
        events_after=_by_id(db, "asset_events"),
        transactions_before=transactions_before,
        transactions_after=_by_id(db, "transactions"),
        violations_before=violations_before,
        violations_after=_foreign_key_violations(db),
        digest_before=digest_before,
        digest_after=digest_after,
        backups_after=backups_after,
        logs=list(logs),
        started=started,
        finished=finished,
        ids=ids,
    )


def _number(value: Any) -> Any:
    """``value`` as a Decimal, whether it was logged as a number or as its text; as it is when it is neither."""
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return value


def _sorted(value: Any) -> Any:
    """A list or tuple sorted, as a list; anything else as it is."""
    if not isinstance(value, (list, tuple)):
        return value
    try:
        return sorted(value)
    except TypeError:
        return sorted(value, key=repr)


def _sorted_values(value: Any) -> Any:
    """A mapping of id lists with each list sorted; anything else as it is."""
    return {key: _sorted(ids) for key, ids in value.items()} if isinstance(value, dict) else value


def _without_updated_at(row: dict[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in row.items() if name != "updated_at"}


def _not_moved_to_the_run(run: Run, before: Any, after: Any) -> Optional[str]:
    """``None`` when ``after`` is the run's time, written as the app writes a DATETIME; otherwise what is wrong."""
    if after == before:
        return f"updated_at did not move: {after!r}"
    try:
        written = datetime.strptime(after, TIMESTAMP)
    except (TypeError, ValueError):
        return f"updated_at {after!r} is not written as {TIMESTAMP!r}, as every other DATETIME"
    if not run.started <= written <= run.finished:
        return f"updated_at {after!r} is not the run's time, {run.started} … {run.finished} UTC"
    return None


def _changed_events(run: Run) -> bool:
    """Whether the run did change events: one of CORRECTIONS now of its valid type, or one of DELETIONS gone."""
    corrected = any(run.events_after.get(run.ids[label], {}).get("type") == event.becomes for label, event in CORRECTIONS.items())
    deleted = any(run.ids[label] not in run.events_after for label in DELETIONS)
    return corrected or deleted


def _transactions_of(run: Run, label: str) -> list[int]:
    """The ids of the transactions planted linked to the event ``label``."""
    return sorted(run.ids[transaction] for owner, transaction in _linked(EVENTS) if owner == label)


def _assert_backup_kept(run: Run, fix_id: str) -> None:
    """The backup is kept beside the database — ``<db name>.pre-<fix id>-<UTC>Z.bak``, the only one — named in the report, and holds the database before the run."""
    assert run.report.backup_path is not None, "a failed fix keeps its backup and names it in the report"
    backup = Path(run.report.backup_path)
    assert backup.parent == run.db.parent and re.fullmatch(rf"{re.escape(run.db.name)}\.pre-{re.escape(fix_id)}-\d{{8}}T\d{{6}}Z\.bak", backup.name), f"the backup kept beside the database, named after it, the fix and the UTC time: {backup}"
    assert run.backups_after == [backup.name]
    assert _tables(backup) == run.tables_before, "the backup holds the database as it was before the run"


def _fix_class() -> type:
    """``EventTypesFix``, imported here and not at the top: before the cure its module does not exist, and each test must
    fail on an assertion of its own — never the whole file on its collection."""
    try:
        module = importlib.import_module(FIX_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != FIX_MODULE:
            raise
        module = None
    assert module is not None, f"{FIX_MODULE} does not exist"
    fix_class = getattr(module, "EventTypesFix", None)
    assert isinstance(fix_class, type), f"{FIX_MODULE} defines no class EventTypesFix"
    return fix_class


def _param(*values: str) -> Any:
    """A pytest param of ``values``, named after the last one."""
    return pytest.param(*values, id=re.sub(r"[^A-Za-z0-9]+", "-", values[-1]).strip("-"))


# =============================================================================
# THE FIX OF THE FRAMEWORK'S TESTS (A)
# =============================================================================


class _DeletesEvents(PostMigrationFix):
    """A fix of these tests only: it deletes the first ``deletes`` of ``event_ids``, and declares no change of a row
    count — the default, which it does not override."""

    fix_id = TEST_FIX

    def __init__(self, event_ids: list[int], deletes: int) -> None:
        self.to_delete = list(event_ids[:deletes])
        self.deleted: list[int] = []  # what apply did, committed or rolled back: the barrier

    def detect(self, conn: sqlite3.Connection, ctx: FixContext) -> Optional[list[int]]:
        return list(self.to_delete)

    def apply(self, conn: sqlite3.Connection, anomaly: list[int], ctx: FixContext) -> None:
        for event_id in anomaly:
            conn.execute("DELETE FROM asset_events WHERE id = ?", (event_id,))
            self.deleted.append(event_id)


class _DeclaresRowCounts(_DeletesEvents):
    """The same fix, declaring ``declared`` as the row-count changes of its ``apply``."""

    def __init__(self, event_ids: list[int], deletes: int, declared: dict[str, int]) -> None:
        super().__init__(event_ids, deletes)
        self.declared = dict(declared)

    def row_count_changes(self, anomaly: list[int], ctx: FixContext) -> dict[str, int]:
        return dict(self.declared)


class _RaisesOnRowCounts(_DeletesEvents):
    """The same fix, whose ``row_count_changes`` raises: the framework must report the fix ``failed``, never let the
    exception out of the run."""

    def row_count_changes(self, anomaly: list[int], ctx: FixContext) -> dict[str, int]:
        raise RuntimeError(BOOM)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def configured_sandbox(tmp_path: Path) -> Iterator[Path]:
    """Every test runs with the configured data dir pointed at a sandbox of its own (see ``_configured_sandbox``)."""
    with _configured_sandbox(tmp_path / "configured-lane") as sandbox:
        yield sandbox


@pytest.fixture(scope="module")
def head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A database at head, built once by the real migrations; every test works on a copy (``_copy``)."""
    root = tmp_path_factory.mktemp("head")
    with _configured_sandbox(root / "configured-lane"):
        db = root / "sqlite" / "app.db"
        _alembic_upgrade_head(db)
    _settle(db)
    return db


@pytest.fixture(scope="module")
def applied(head: Path, tmp_path_factory: pytest.TempPathFactory) -> Run:
    """Every event of EVENTS planted with its transactions (``_plant``), then one run. Read-only for the tests."""
    root = tmp_path_factory.mktemp("applied")
    with _configured_sandbox(root / "configured-lane"):
        db = _copy(head, root)
        return _observe(db, _plant(db))


@pytest.fixture(scope="module")
def previewed(head: Path, tmp_path_factory: pytest.TempPathFactory) -> Run:
    """As ``applied``, with ``dry_run=True``."""
    root = tmp_path_factory.mktemp("dry-run")
    with _configured_sandbox(root / "configured-lane"):
        db = _copy(head, root)
        return _observe(db, _plant(db), dry_run=True)


# =============================================================================
# A. THE FRAMEWORK: A FIX DECLARES THE ROW COUNTS IT CHANGES
# =============================================================================


def test_a_fix_that_declares_the_rows_it_deletes_is_applied(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A.1 (RED): a fix declaring ``{"asset_events": -1}`` that deletes one event — ``applied``, no error, no backup; the event gone, the two others there, every other count as it was.

    Today ``row_count_changes`` is never asked for: the count of ``asset_events`` changed, so the fix fails and keeps
    its backup.
    """
    db = _copy(head, tmp_path)
    event_ids = _plant_three_events(db)
    fix = _DeclaresRowCounts(event_ids, deletes=1, declared={"asset_events": -1})
    monkeypatch.setattr(post_migration, "FIXES", (fix,))

    run = _observe(db, {})

    assert fix.deleted == event_ids[:1], "barrier: the fix never reached its apply"
    assert (run.report.outcomes.get(TEST_FIX), run.report.errors) == ("applied", [])
    assert (run.report.backup_path, run.backups_after) == (None, [])
    assert sorted(run.events_after) == sorted(set(run.events_before) - {event_ids[0]})
    assert run.counts_after == {**run.counts_before, "asset_events": run.counts_before["asset_events"] - 1}


def test_a_fix_that_deletes_more_than_it_declares_fails_and_says_by_how_much(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A.2 (RED on the wording only): declaring -1 and deleting two events — ``failed``, the database as it was, the backup kept, and the error ``row counts not as expected: asset_events (expected N, found M)``.

    The wording is asserted last: everything before it holds today too, when the error reads ``row counts changed:
    asset_events``.
    """
    db = _copy(head, tmp_path)
    event_ids = _plant_three_events(db)
    fix = _DeclaresRowCounts(event_ids, deletes=2, declared={"asset_events": -1})
    monkeypatch.setattr(post_migration, "FIXES", (fix,))

    run = _observe(db, {})
    events = run.counts_before["asset_events"]

    assert fix.deleted == event_ids[:2], "barrier: the fix never reached its apply"
    assert run.report.outcomes.get(TEST_FIX) == "failed"
    assert run.tables_after == run.tables_before
    _assert_backup_kept(run, TEST_FIX)
    assert run.report.errors == [f"{TEST_FIX}: row counts not as expected: asset_events (expected {events - 1}, found {events - 2})"]


@pytest.mark.parametrize("declared", [pytest.param(None, id="declares-nothing"), pytest.param({"assets": -1}, id="declares-another-table")])
def test_a_fix_that_deletes_rows_it_does_not_declare_fails(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, declared: Optional[dict[str, int]]) -> None:
    """A.3 (guard, green today and after): deleting one event while declaring nothing — or the deletion of an asset instead — ``failed`` with ``asset_events`` named, the database as it was, the backup kept.

    A table the fix does not name keeps its count, and a declaration about one table excuses no other.
    """
    db = _copy(head, tmp_path)
    event_ids = _plant_three_events(db)
    fix = _DeletesEvents(event_ids, deletes=1) if declared is None else _DeclaresRowCounts(event_ids, deletes=1, declared=declared)
    monkeypatch.setattr(post_migration, "FIXES", (fix,))

    run = _observe(db, {})

    assert fix.deleted == event_ids[:1], "barrier: the fix never reached its apply"
    assert run.report.outcomes.get(TEST_FIX) == "failed"
    assert any("asset_events" in error for error in run.report.errors), run.report.errors
    assert run.tables_after == run.tables_before
    _assert_backup_kept(run, TEST_FIX)


def test_a_fix_whose_row_count_changes_raise_is_reported_failed_never_raised(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A.4 (RED): ``row_count_changes`` raising ``RuntimeError("boom")`` — the run returns its report: ``failed``, an error of the fix naming ``boom``, the database as it was, the backup kept and named in ``backup_path``.

    The error is the barrier, and the reason for the red. Today the declaration is never asked for: the fix goes on to
    delete its event and fails on the row count — ``failed``, the database as it was, the backup kept, all as asserted
    here — and no error names ``boom``. A declaration asked outside the ``try`` of ``_apply_one`` would raise out of
    the run instead.
    """
    db = _copy(head, tmp_path)
    event_ids = _plant_three_events(db)
    monkeypatch.setattr(post_migration, "FIXES", (_RaisesOnRowCounts(event_ids, deletes=1),))

    try:
        run = _observe(db, {})
    except Exception as exc:
        pytest.fail(f"run_post_migration_fixes raised {exc!r}: a fix whose row_count_changes raises is reported failed, never raised")

    assert run.report.outcomes.get(TEST_FIX) == "failed"
    assert any(error.startswith(f"{TEST_FIX}: ") and BOOM in error for error in run.report.errors), f"an error of {TEST_FIX} naming {BOOM!r}, from its row_count_changes: {run.report.errors}"
    assert run.tables_after == run.tables_before
    _assert_backup_kept(run, TEST_FIX)


# =============================================================================
# B. EVENT_TYPES — THE FIX IN THE LIST
# =============================================================================


def test_the_fix_is_registered_after_autoincrement() -> None:
    """B (RED): ``FIXES`` holds one fix whose ``fix_id`` is ``event_types``, an ``EventTypesFix`` of ``event_types.py``, after ``autoincrement``.

    The tuple is never asserted whole: ``orphan_pair_halves`` may be there or not.
    """
    ids = [fix.fix_id for fix in post_migration.FIXES]

    assert ids.count(FIX) == 1, f"one fix with fix_id {FIX!r} in FIXES: {ids}"
    assert ids.index("autoincrement") < ids.index(FIX), ids
    fix = post_migration.FIXES[ids.index(FIX)]
    assert (type(fix).__module__, type(fix).__name__) == (FIX_MODULE, "EventTypesFix")


# =============================================================================
# B.1 — B.3 THE ROWS: CORRECTED, DELETED WITH THEIR TRANSACTIONS UNLINKED, UNTOUCHED
# =============================================================================


@pytest.mark.parametrize("label", [_param(label) for label in CORRECTIONS])
def test_an_event_valid_once_trimmed_and_upper_cased_is_corrected_in_place(applied: Run, label: str) -> None:
    """B.1 (RED): the event keeps its id and takes its valid type; ``updated_at`` moves to the run's time; every other column — asset, date, value, currency, provider, notes, created_at — stays."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    event = CORRECTIONS[label]
    event_id = applied.ids[label]
    before = applied.events_before[event_id]
    assert before["type"] == event.stored, "setup: the event as planted"
    after = applied.events_after.get(event_id)

    assert after is not None, f"event {event_id} is gone: it must be corrected in place, under its own id"
    assert _without_updated_at(after) == _without_updated_at({**before, "type": event.becomes})
    problem = _not_moved_to_the_run(applied, before["updated_at"], after["updated_at"])
    assert problem is None, problem


@pytest.mark.parametrize(("label", "transaction"), [_param(label, transaction) for label, transaction in _linked(CORRECTIONS)])
def test_the_transactions_of_a_corrected_event_stay_linked_and_untouched(applied: Run, label: str, transaction: str) -> None:
    """B.1 (RED): a transaction linked to an event the fix corrects keeps its link and every other column, ``updated_at`` included. Barrier first: that event was corrected."""
    event = CORRECTIONS[label]
    assert applied.events_after.get(applied.ids[label], {}).get("type") == event.becomes, f"barrier: event {label!r} was not corrected, so 'still linked' would pass for a run that does nothing"
    tx_id = applied.ids[transaction]
    assert applied.transactions_before[tx_id]["asset_event_id"] == applied.ids[label], "setup: the transaction is linked to its event"

    assert applied.transactions_after.get(tx_id) == applied.transactions_before[tx_id]


@pytest.mark.parametrize("label", [_param(label) for label in DELETIONS])
def test_an_event_whose_type_stays_unknown_is_deleted(applied: Run, label: str) -> None:
    """B.2 (RED): the event is gone — a provider's (``provider_assignment_id`` set) as a user's."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    event = DELETIONS[label]
    event_id = applied.ids[label]
    before = applied.events_before[event_id]
    assert (before["type"], before["provider_assignment_id"] is not None) == (event.stored, event.provider), "setup: the event as planted"

    assert event_id not in applied.events_after


@pytest.mark.parametrize(("label", "transaction"), [_param(label, transaction) for label, transaction in _linked(DELETIONS)])
def test_a_transaction_of_a_deleted_event_stays_without_its_link(applied: Run, label: str, transaction: str) -> None:
    """B.2 (RED): the transaction stays; its ``asset_event_id`` becomes NULL and ``updated_at`` moves to the run's time; every other column stays."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    tx_id = applied.ids[transaction]
    before = applied.transactions_before[tx_id]
    assert before["asset_event_id"] == applied.ids[label], "setup: the transaction is linked to its event"
    after = applied.transactions_after.get(tx_id)

    assert after is not None, f"transaction {tx_id} is gone: it must stay, without its event"
    assert _without_updated_at(after) == _without_updated_at({**before, "asset_event_id": None})
    problem = _not_moved_to_the_run(applied, before["updated_at"], after["updated_at"])
    assert problem is None, problem


@pytest.mark.parametrize("label", [_param(label) for label in VALID])
def test_an_event_of_a_valid_type_is_untouched_and_so_are_its_transactions(applied: Run, label: str) -> None:
    """B.3 (RED): every column of the event as it was, ``updated_at`` included, and the same for each transaction linked to it. Barrier first: the same run did correct or delete other events."""
    assert applied.report.outcomes.get(FIX) == "applied" and _changed_events(applied), NOTHING_DONE
    event_id = applied.ids[label]
    transactions = _transactions_of(applied, label)

    assert applied.events_after.get(event_id) == applied.events_before[event_id]
    assert {tx_id: applied.transactions_after.get(tx_id) for tx_id in transactions} == {tx_id: applied.transactions_before[tx_id] for tx_id in transactions}


# =============================================================================
# B.4 THE RUN
# =============================================================================


def test_the_run_reports_applied_without_error_or_backup(applied: Run) -> None:
    """B.4 (RED): ``applied``, the integrity check passed, no error; no backup kept, none left beside the database."""
    assert (applied.report.outcomes.get(FIX), applied.report.integrity_ok, applied.report.errors) == ("applied", True, [])
    assert (applied.report.backup_path, applied.backups_after) == (None, [])


def test_the_run_breaks_no_foreign_key(applied: Run) -> None:
    """B.4 (RED): ``PRAGMA foreign_key_check`` is empty after the run as before it: no transaction names a deleted event."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED

    assert (applied.violations_before, applied.violations_after) == ([], [])


def test_the_run_deletes_exactly_the_unknown_events_and_leaves_every_other_table_as_it_was(applied: Run) -> None:
    """B.4 (RED): ``asset_events`` down by exactly the events deleted, ``transactions`` by none, every other count as it was; every other table, SQLite's own included, row for row as it was."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED

    assert applied.counts_after == {**applied.counts_before, "asset_events": applied.counts_before["asset_events"] - len(DELETIONS)}
    assert _other_tables(applied.tables_after) == _other_tables(applied.tables_before)


def test_only_the_events_it_corrects_or_deletes_and_the_transactions_it_unlinks_change(applied: Run) -> None:
    """B.4 (RED): the events changed or gone are exactly those of CORRECTIONS and DELETIONS; the transactions changed, exactly those linked to DELETIONS; no transaction went or appeared."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    changed_events = sorted(event_id for event_id, row in applied.events_before.items() if applied.events_after.get(event_id) != row)
    changed_transactions = sorted(tx_id for tx_id, row in applied.transactions_before.items() if applied.transactions_after.get(tx_id) != row)

    assert changed_events == sorted(applied.ids[label] for label in (*CORRECTIONS, *DELETIONS))
    assert changed_transactions == sorted(applied.ids[transaction] for _label, transaction in _linked(DELETIONS))
    assert sorted(applied.transactions_after) == sorted(applied.transactions_before)


def test_a_second_run_finds_nothing_to_do_and_writes_nothing(head: Path, tmp_path: Path) -> None:
    """B.4 (RED): run again, the fix reports ``clean`` and writes nothing: the file byte-identical, every row as it was, no backup."""
    db = _copy(head, tmp_path)
    ids = _plant(db)
    first = post_migration.run_post_migration_fixes(db, None)
    assert first.outcomes.get(FIX) == "applied", f"precondition: the first run must apply, or the second proves nothing: {first.outcomes} {first.errors}"

    second = _observe(db, ids)

    assert (second.report.outcomes.get(FIX), second.report.errors) == ("clean", [])
    assert second.digest_after == second.digest_before
    assert second.tables_after == second.tables_before
    assert (second.report.backup_path, second.backups_after) == (None, [])


# =============================================================================
# B.5 THE DRY RUN, AND A DATABASE WITH NOTHING TO DO
# =============================================================================


def test_a_dry_run_reports_would_apply_and_writes_nothing(previewed: Run) -> None:
    """B.5 (RED): ``would_apply``, the database file byte-identical, every row as it was, no backup."""
    assert previewed.report.outcomes.get(FIX) == "would_apply"
    assert previewed.digest_after == previewed.digest_before
    assert previewed.tables_after == previewed.tables_before
    assert (previewed.report.backup_path, previewed.backups_after) == (None, [])


def test_a_database_whose_event_types_are_all_valid_needs_nothing(head: Path, tmp_path: Path) -> None:
    """B.5 (RED on the outcome only): one event of each valid type, two with their transactions — ``clean``, the file byte-identical, every row as it was, no backup."""
    db = _copy(head, tmp_path)
    ids = _plant(db, with_unknown_types=False)

    run = _observe(db, ids)

    assert (run.report.outcomes.get(FIX), run.report.errors) == ("clean", [])
    assert run.digest_after == run.digest_before
    assert run.tables_after == run.tables_before
    assert (run.report.backup_path, run.backups_after) == (None, [])


# =============================================================================
# B.6 — B.7 THE LOG: THE DETECTION WARNING, ONE LINE PER CHANGED ROW
# =============================================================================


@pytest.mark.parametrize("observed", [pytest.param("previewed", id="dry-run"), pytest.param("applied", id="run")])
def test_the_detection_warning_lists_what_the_fix_corrects_deletes_and_unlinks(request: pytest.FixtureRequest, observed: str) -> None:
    """B.6 (RED): one warning of the fix per run, dry run or not — ``count`` (every event of unknown type), ``corrections`` (the ids by ``<stored>-><valid>``), ``deletions`` (the ids by stored type), ``unlinked_transactions``."""
    run: Run = request.getfixturevalue(observed)
    corrections: dict[str, list[int]] = {}
    for label, event in CORRECTIONS.items():
        corrections.setdefault(f"{event.stored}->{event.becomes}", []).append(run.ids[label])
    deletions: dict[str, list[int]] = {}
    for label, event in DELETIONS.items():
        deletions.setdefault(event.stored, []).append(run.ids[label])
    expected = {
        "count": len(CORRECTIONS) + len(DELETIONS),
        "corrections": _sorted_values(corrections),
        "deletions": _sorted_values(deletions),
        "unlinked_transactions": _sorted([run.ids[transaction] for _label, transaction in _linked(DELETIONS)]),
    }

    warnings = run.warnings()

    assert len(warnings) == 1, f"one detection warning per run: {warnings}"
    warning = warnings[0]
    found = {
        "count": warning.get("count"),
        "corrections": _sorted_values(warning.get("corrections")),
        "deletions": _sorted_values(warning.get("deletions")),
        "unlinked_transactions": _sorted(warning.get("unlinked_transactions")),
    }
    assert found == expected


def test_an_applied_run_logs_one_line_per_corrected_event_unlinked_transaction_and_deleted_event(applied: Run) -> None:
    """B.7 (RED): after the commit, at INFO, ``Asset event type corrected`` per corrected event (event_id, from_type, to_type), ``Transaction unlinked from an asset event of unknown type`` per unlinked transaction (transaction_id, former_event_id), ``Asset event of unknown type deleted`` per deleted event (event_id, type, value, currency, is_auto, unlinked_transactions); no line for a row left as it was."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    assert applied.closing_events() == [APPLIED_EVENT], NOT_CAPTURED
    ids, before = applied.ids, applied.events_before
    corrected = [("info", ids[label], event.stored, event.becomes) for label, event in CORRECTIONS.items()]
    unlinked = [("info", ids[transaction], ids[label]) for label, transaction in _linked(DELETIONS)]
    deleted = [("info", ids[label], event.stored, _number(before[ids[label]]["value"]), before[ids[label]]["currency"], event.provider, _transactions_of(applied, label)) for label, event in DELETIONS.items()]

    assert applied.lines(CORRECTED, "event_id", "from_type", "to_type") == sorted(corrected, key=repr)
    assert applied.lines(UNLINKED, "transaction_id", "former_event_id") == sorted(unlinked, key=repr)
    assert applied.deleted_lines() == sorted(deleted, key=repr)


def test_a_dry_run_logs_no_line_per_row(previewed: Run) -> None:
    """B.7 (RED): a dry run changes nothing, so it logs no corrected, unlinked or deleted line. Barrier first: it detected, and the same logger's warning reached the capture."""
    assert previewed.report.outcomes.get(FIX) == "would_apply", "barrier: the dry run did not detect the events, so 'no line' says nothing"
    assert previewed.warnings(), NOT_CAPTURED

    assert previewed.row_lines() == []


# =============================================================================
# B.8 A FAILED VERIFICATION
# =============================================================================


def test_a_failed_verification_leaves_the_database_as_it_was_and_keeps_the_backup(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B.8 (RED): ``EventTypesFix.verify`` made to report a problem — ``failed`` with it, every table as it was, the backup kept beside the database holding it, no line per row."""
    fix_class = _fix_class()
    db = _copy(head, tmp_path)
    ids = _plant(db)
    monkeypatch.setattr(fix_class, "verify", lambda self, conn, anomaly, ctx: [PROVOKED])

    run = _observe(db, ids)

    assert (run.report.outcomes.get(FIX), run.report.errors) == ("failed", [f"{FIX}: {PROVOKED}"])
    assert run.tables_after == run.tables_before
    _assert_backup_kept(run, FIX)
    assert run.closing_events() == [FAILED_EVENT], NOT_CAPTURED
    assert run.warnings(), NOT_CAPTURED  # the fix's own logger reached the capture: its detection warning
    assert run.row_lines() == []

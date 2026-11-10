"""
Decision 47, point 4 — the lone giving TRANSFER legs already in a database (workstream W, release 1.3), as N78-1 changed it.

N78-1 (the developer's decision, 21/10/2026; plan 04 «N78-1 · Una rettifica in uscita non ha valore: cura»): an ADJUSTMENT
with a negative quantity has no value, it only lowers the quantity. So the step converts EVERY lone giving leg into an
ADJUSTMENT-out WITHOUT a value — no ``cost_basis_override``, no ``cost_basis_currency`` —: no cost is computed, so a leg
whose broker's pool needs a missing conversion or holds a row that cannot be read is converted like any other, and none
«stays a TRANSFER» any more. The contract below is the one decision 47 wrote; what N78-1 changes is said where it applies,
and the tests it changes are RED until its cure. ``LoneLeg``'s cost fields (``cost``, ``cost_currency``, ``reason``,
``converted``) lose their meaning: the tests no longer read them, and the cure may drop them.

Under test: ``backend/app/services/transactions/lone_transfer_legs.py`` (new with decision 47), its startup step in
``backend/app/services/platform/app_lifespan.py`` and its run in the offline script
``python -m backend.app.db.post_migration`` (``backend/app/db/post_migration/__main__.py``).

Before 1.3, deleting a broker left the giving leg of each TRANSFER it had received as a TRANSFER without its pair:
``related_transaction_id`` NULL, quantity < 0. The lots cannot read it (TRANSFER_PAIR_MISSING) and the Dashboard values
it at market. The sync post-migration fix ``orphan_pair_halves`` converts the lone RECEIVING legs; it cannot price a
giving one — its Auto cost needs ``compute_wac_iterative``, async, with conversions and splits — so it counts it and
leaves it. Decision 47 converts it as the 1.3 deletion converts the giving leg of a broker it deletes
(``delete_by_broker``: BR-U-073, 078, 086–088 in test_broker_service.py): into an ADJUSTMENT handed over at the Auto
cost of its OWN broker — ``compute_wac_iterative(broker of the row, date of the row, the row left out)``,
``TransactionService._handover_cost`` —, which J's CP-16 reads as units handed over at that cost
(``financial_math/fifo/engine.py``).

The contract pinned here — with the coordinator's decisions of 16/10 (1: a leg whose cost cannot be computed is skipped;
2: a link naming a missing row is no link; 3: no step after a failed fix):

1. ``convert_lone_giving_legs(session, *, dry_run=False) -> list[LoneLeg]`` turns each lone giving leg into an
   ADJUSTMENT with the same quantity, asset, date, description and tags, WITHOUT a value (N78-1; before it,
   ``cost_basis_override`` and ``cost_basis_currency`` the Auto cost of its broker), no link, ``updated_at`` moved. A giving leg is lone when its link
   is NULL or names a row that no longer exists (decision 2). Since N78-1 no leg stays a TRANSFER for its cost: a leg
   whose broker's pool needs a missing conversion, or holds an unreadable row, is converted all the same (before N78-1
   it stayed a TRANSFER, decision 1). The legs are selected with ``quantity < 0`` in SQL, so a row whose quantity SQLite cannot read as a
   number is never one of them. A lone receiving leg (quantity > 0: the sync fix's) and a linked TRANSFER are never
   touched, nor is any other row. It returns one ``LoneLeg`` per lone giving leg it found, and commits nothing: the
   caller does. With ``dry_run=True`` it returns the same legs and changes nothing, even when the caller commits. A
   second run finds nothing left to convert — no leg at all since N78-1 — and writes nothing.
2. ``LoneLeg``: a frozen dataclass with at least ``id, broker_id, date, quantity, asset_id`` — ``quantity`` the leg's
   own, signed — and ``describe(dry_run=...)``: one line holding the leg's id, in a dry run and in a real one. Its cost
   fields of decision 47 (``cost``, ``cost_currency``, ``reason``, ``converted``) are no longer read: N78-1 computes no
   cost.
3. ``run_lone_giving_legs(db_path, *, dry_run)``: the same on a SQLite file, through an engine of its own; it commits,
   or leaves the file as it was for a dry run.
4. ``convert_lone_giving_legs_at_startup()`` opens its own session on the configured engine, converts and commits; it
   never raises — an exception is logged and swallowed. When no giving leg is lone it returns at once, nothing checked,
   nothing written; otherwise the database must pass ``_database_is_sound`` (``PRAGMA quick_check``) first, or the
   wrapper logs «Lone transfer legs left as they are: the database failed its quick check» and writes nothing.
   ``app_lifespan.STARTUP_STEPS`` runs it as the step ``lone-transfer-legs``, right after ``post-migration-fixes``, and
   the step reaches it through its name in ``app_lifespan`` when it runs (the module's convention, test_app_lifecycle.py
   (d)).
5. The offline script runs the step after the fixes, on the database it was given — only when the integrity check
   passed and no fix failed (decision 3) —, and prints one line per lone giving leg, holding the leg's id; it exits 1
   when the step raised. The fixes run first, so a giving leg whose link names a row that no longer exists — unlinked
   by ``orphan_pair_halves`` — is converted by the same run; a dry run, which applies no fix, lists it all the same
   (decision 2).

The book. Lone giving legs, as a 1.2 deletion of their receiving broker left them (link NULL):
- leg 470100, TRANSFER −4 X on 4 Sep 2019, on a broker that bought 10 X for 200 EUR on 2 Sep and 10 more for 400 on
  5 Sep (before N78-1: handed over at its Auto cost, 20 EUR);
- leg 470200, TRANSFER −3 Y on 4 Sep, on a broker that paid for Y in PYG on 1 Sep, then in EUR on 2 Sep: no rate
  converts PYG — proven at setup —, so no average of that broker exists (before N78-1 it stayed a TRANSFER);
- with ``unreadable``, leg 470050, TRANSFER −2 V on 4 Sep, on a broker that bought 10 V for 200 EUR on 2 Sep and also
  holds a TRANSFER of V whose quantity is 'n/a', as test_post_migration_orphan_pairs.py plants one: an average of that
  broker would load that row, which SQLAlchemy cannot read as a number (before N78-1 its cost computation raised and it
  stayed a TRANSFER). Its id is the lowest, so a run that stopped at its first leg would convert nothing after it.
Beside them, for the service cases: a lone receiving TRANSFER +2 X without a cost basis, one +1 X at 20 EUR, and a
TRANSFER pair still linked both ways. With ``dangling``: leg 470300, TRANSFER −2 W on 4 Sep, whose link names a row
deleted with foreign keys off — lone all the same (decision 2); in the script's real run the fix unlinks it first (its
broker's Auto cost, before N78-1: 30 EUR, 5 W for 150). The legs carry ids of their own, which no path, count or date the script
prints can contain.

The databases, as test_db/test_post_migration_orphan_pairs.py builds them (its helpers are followed here): one
database built at head by the real migrations — ``alembic upgrade head`` in a child process, always with
``-x sqlalchemy.url=`` —, copied for each test, its rows written with sqlite3 and read back the same way. Every database
is a private file under tmp_path, and the configured data dir points at a sandbox with a canary. Never the lane's
database: the conversion scans a whole database, so on the lane's it would meet — and a real run would convert — the
legs of every other unit, and of every run before. The startup wrapper's cases make a private file's engine the
configured one (``backend.app.db.session.async_engine``, which ``get_async_engine`` returns) and put in place of the
conversion a double that runs the real one only on that engine: a wrapper that reached another database would find it
untouched.

The module does not exist before decision 47: each test imports it when it runs (``_module()``), which fails with
"decision 47: … does not exist yet" while the rest of the file still collects.

Run: ``./dev.py test services lone-transfer-legs`` (the action ``services_lone_transfer_legs``).
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database, never the production one.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import session as db_session
from backend.app.db.post_migration.orphan_pair_halves import OrphanPairHalfFix
from backend.app.services.platform import app_lifespan

MODULE = "backend.app.services.transactions.lone_transfer_legs"
SCRIPT = "backend.app.db.post_migration.__main__"
STEP = "lone-transfer-legs"
CHILD_TIMEOUT = 300
CANARY = b"canary: a configured data dir that no run was given\n"
CANARY_FILE = Path("broker_reports", "uploaded", "broker_999", "canary.csv")
INJECTED = "decision 47 test: injected failure"
LOG_CANARY = "decision 47 test: canary through the module's logger"
PROVOKED = "provoked: the fix's own check found a problem"  # as test_post_migration_orphan_pairs.py provokes it
QUICK_CHECK_FAILED = "Lone transfer legs left as they are: the database failed its quick check"  # the startup wrapper's warning

STAMP = "2019-09-04 10:00:00.000000"  # created_at and updated_at of every planted row
TIMESTAMP = "%Y-%m-%d %H:%M:%S.%f"  # how the app stores a DATETIME
PYG_DAY, BUY_DAY, LEG_DAY, LATER_DAY = "2019-09-01", "2019-09-02", "2019-09-04", "2019-09-05"
LEG_DATE = date.fromisoformat(LEG_DAY)
# The legs' own ids, a hundred apart: after an explicit id, AUTOINCREMENT hands out the next ones, so the rows planted
# between two legs must not reach the second leg's id. The leg over an unreadable pool has the lowest: written last, it is
# still first by id.
UNREADABLE_POOL_LEG, X_LEG, PYG_LEG, DANGLING_LEG = 470050, 470100, 470200, 470300
# The lone giving legs of the default book: since N78-1 both are converted, without a value (before it: X_LEG at 20 EUR,
# PYG_LEG left a TRANSFER).
BOOK_LEGS = (X_LEG, PYG_LEG)
# The rows nothing may touch in the service cases (``_plant(untouchables=True)``).
UNTOUCHABLES = ("lone receiving leg", "lone receiving leg with cost", "linked giving leg", "linked receiving leg")

Rows = dict[int, dict[str, Any]]
Tables = dict[str, list[tuple[Any, ...]]]


class _InjectedFailure(RuntimeError):
    """The failure a case provokes where decision 47's step runs."""


@dataclass
class Book:
    """One test's private database, the ids of what was planted in it by label, and an engine on it."""

    db: Path
    ids: dict[str, int]
    engine: AsyncEngine


# =============================================================================
# HELPERS — the module of decision 47
# =============================================================================


def _module() -> ModuleType:
    """``lone_transfer_legs``, imported when a test needs it: before decision 47 it does not exist, and only the tests
    that need it fail."""
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:
            raise
        pytest.fail(f"decision 47: {MODULE} does not exist yet")


# =============================================================================
# HELPERS — the configured data dir, the migrations, the script (as test_post_migration_orphan_pairs.py)
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


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """``python -m backend.app.db.post_migration`` with ``args`` in a child process, at the INFO level whatever the shell exports."""
    return subprocess.run(
        [sys.executable, "-m", "backend.app.db.post_migration", *args],
        cwd=PROJECT_ROOT,
        env={**_child_env(), "LIBREFOLIO_LOG_LEVEL": "INFO"},
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )


def _output(completed: subprocess.CompletedProcess[str]) -> str:
    """What a child process said, for an assertion message."""
    return f"exit {completed.returncode}\n--- stdout\n{completed.stdout[-3000:]}\n--- stderr\n{completed.stderr[-3000:]}"


def _printed_lines(text: str) -> list[str]:
    """The script's own lines: those of ``text`` that are not JSON objects — its log lines are, since W-B23."""
    printed = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            printed.append(line)
            continue
        if not isinstance(value, dict):
            printed.append(line)
    return printed


def _summary_says(completed: subprocess.CompletedProcess[str], fix_id: str, outcome: str) -> bool:
    """Whether the script printed its summary line ``Fix <fix_id>: <outcome>``, on a line of its own."""
    return re.search(rf"^Fix {fix_id}: {outcome}\s*$", completed.stdout, re.MULTILINE) is not None


def _names_the_leg(line: str, leg_id: int) -> bool:
    """Whether ``line`` holds ``leg_id`` as a number of its own (not a part of a longer one)."""
    return re.search(rf"(?<!\d){leg_id}(?!\d)", line) is not None


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


def _backups(db: Path) -> list[str]:
    """The backup files beside ``db``: ``<db name>.pre-…``, or anything ending in ``.bak``."""
    return sorted(path.name for path in db.parent.iterdir() if path.name.startswith(f"{db.name}.pre-") or path.name.endswith(".bak"))


def _tables(db: Path) -> Tables:
    """Every row of every table, SQLite's own included: what "writes nothing" compares."""
    with _connect(db) as conn:
        names = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {name: sorted(conn.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr) for name in names}


def _transactions(db: Path) -> Rows:
    """The transactions by id, each as ``{column: value}``, read by a connection of their own: what is committed."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute("SELECT * FROM transactions ORDER BY id")}


def _without_updated_at(row: dict[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in row.items() if name != "updated_at"}


def _without_a_value(row: dict[str, Any]) -> dict[str, Any]:
    """``row`` as N78-1 leaves a lone giving leg: an ADJUSTMENT, its quantity, asset, date, description and tags as they
    were, no cost basis nor its currency, no link. ``updated_at`` aside: it moves. (Before N78-1: a cost basis, its
    broker's Auto cost.)"""
    return {**row, "type": "ADJUSTMENT", "cost_basis_override": None, "cost_basis_currency": None, "related_transaction_id": None}


def _utc_now() -> datetime:
    """Now, as the app writes it: UTC, without a zone."""
    return datetime.now(UTC).replace(tzinfo=None)


def _not_moved(before: str, after: str, started: datetime, finished: datetime) -> Optional[str]:
    """``None`` when ``after`` is a time between ``started`` and ``finished``, written as the app writes a DATETIME; otherwise what is wrong."""
    if after == before:
        return f"updated_at did not move: {after!r}"
    try:
        written = datetime.strptime(after, TIMESTAMP)
    except (TypeError, ValueError):
        return f"updated_at {after!r} is not written as {TIMESTAMP!r}, as every other DATETIME"
    if not started <= written <= finished:
        return f"updated_at {after!r} is not the conversion's time, {started} … {finished} UTC"
    return None


# =============================================================================
# HELPERS — the rows a 1.2 deletion left
# =============================================================================


def _broker(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("INSERT INTO brokers (name, created_at, updated_at) VALUES (?, ?, ?)", (name, STAMP, STAMP)).lastrowid


def _asset(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, 'EUR', 'STOCK', 1, ?, ?)", (name, STAMP, STAMP)).lastrowid


def _insert(conn: sqlite3.Connection, **columns: Any) -> int:
    """One transaction on LEG_DAY, stamped STAMP; ``columns`` add to or replace those (``id`` included)."""
    row = {"date": LEG_DAY, "quantity": "0", "amount": "0", "created_at": STAMP, "updated_at": STAMP, **columns}
    names, marks = ", ".join(row), ", ".join("?" for _ in row)
    return conn.execute(f"INSERT INTO transactions ({names}) VALUES ({marks})", tuple(row.values())).lastrowid


def _pair(conn: sqlite3.Connection, half: dict[str, Any], partner: dict[str, Any]) -> tuple[int, int]:
    """Two rows linked both ways, as the app writes a pair: ``(half's id, partner's id)``."""
    half_id, partner_id = _insert(conn, **half), _insert(conn, **partner)
    conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (partner_id, half_id))
    conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (half_id, partner_id))
    return half_id, partner_id


def _plant(db: Path, *, untouchables: bool = False, dangling: bool = False, unreadable: bool = False) -> dict[str, int]:
    """The book of the module docstring, written as a 1.2 deletion left it; the ids by label.

    ``untouchables`` adds the lone receiving legs and the linked pair, ``dangling`` leg 470300 and its deleted partner,
    ``unreadable`` leg 470050 and the row of V whose quantity is 'n/a'.
    """
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        pyg = "(base = 'EUR' AND quote = 'PYG') OR (base = 'PYG' AND quote = 'EUR')"
        found = (conn.execute(f"SELECT count(*) FROM fx_rates WHERE {pyg}").fetchone()[0], conn.execute(f"SELECT count(*) FROM fx_conversion_routes WHERE {pyg}").fetchone()[0])
        assert found == (0, 0), f"setup: leg {PYG_LEG} needs a conversion nobody stores; PYG/EUR has (rates, routes) = {found}"
        x, y = _asset(conn, "X"), _asset(conn, "Y")
        sender_x, sender_y = _broker(conn, "Sender of X, its receiver deleted"), _broker(conn, "Sender of Y, its receiver deleted")
        ids = {"X": x, "Y": y, "sender of X": sender_x, "sender of Y": sender_y}
        ids["deposit"] = _insert(conn, broker_id=sender_x, type="DEPOSIT", date=BUY_DAY, amount="1000", currency="EUR")
        ids["purchase of X"] = _insert(conn, broker_id=sender_x, asset_id=x, type="BUY", date=BUY_DAY, quantity="10", amount="-200", currency="EUR")
        ids["purchase of X, the day after"] = _insert(conn, broker_id=sender_x, asset_id=x, type="BUY", date=LATER_DAY, quantity="10", amount="-400", currency="EUR")
        ids["leg of X"] = _insert(conn, id=X_LEG, broker_id=sender_x, asset_id=x, type="TRANSFER", quantity="-4", description="4 X to a deleted broker", tags="pair,out")
        ids["purchase of Y in PYG"] = _insert(conn, broker_id=sender_y, asset_id=y, type="BUY", date=PYG_DAY, quantity="10", amount="-50000", currency="PYG")
        ids["purchase of Y in EUR"] = _insert(conn, broker_id=sender_y, asset_id=y, type="BUY", date=BUY_DAY, quantity="10", amount="-200", currency="EUR")
        ids["leg of Y"] = _insert(conn, id=PYG_LEG, broker_id=sender_y, asset_id=y, type="TRANSFER", quantity="-3", description="3 Y to a deleted broker", tags="pair,out")
        if untouchables:
            receiver = _broker(conn, "Receiver of X, its sender deleted")
            ids["lone receiving leg"] = _insert(conn, broker_id=receiver, asset_id=x, type="TRANSFER", quantity="2", description="2 X from a deleted broker")
            ids["lone receiving leg with cost"] = _insert(conn, broker_id=receiver, asset_id=x, type="TRANSFER", quantity="1", cost_basis_override="20", cost_basis_currency="EUR")
            pair_sender, pair_receiver = _broker(conn, "Pair sender"), _broker(conn, "Pair receiver")
            ids["linked giving leg"], ids["linked receiving leg"] = _pair(
                conn,
                {"broker_id": pair_sender, "asset_id": x, "type": "TRANSFER", "quantity": "-1"},
                {"broker_id": pair_receiver, "asset_id": x, "type": "TRANSFER", "quantity": "1", "cost_basis_override": "20", "cost_basis_currency": "EUR"},
            )
        if dangling:
            w = _asset(conn, "W")
            sender_w, gone = _broker(conn, "Sender of W"), _broker(conn, "Receiver of W, deleted leaving the links")
            ids |= {"W": w, "sender of W": sender_w}
            ids["purchase of W"] = _insert(conn, broker_id=sender_w, asset_id=w, type="BUY", date=BUY_DAY, quantity="5", amount="-150", currency="EUR")
            ids["leg of W"], _ = _pair(
                conn,
                {"id": DANGLING_LEG, "broker_id": sender_w, "asset_id": w, "type": "TRANSFER", "quantity": "-2", "description": "2 W to a deleted broker"},
                {"broker_id": gone, "asset_id": w, "type": "TRANSFER", "quantity": "2", "cost_basis_override": "30", "cost_basis_currency": "EUR"},
            )
            conn.execute("DELETE FROM transactions WHERE broker_id = ?", (gone,))
            conn.execute("DELETE FROM brokers WHERE id = ?", (gone,))
        if unreadable:
            v = _asset(conn, "V")
            sender_v = _broker(conn, "Sender of V, its receiver deleted")
            ids |= {"V": v, "sender of V": sender_v}
            ids["purchase of V"] = _insert(conn, broker_id=sender_v, asset_id=v, type="BUY", date=BUY_DAY, quantity="10", amount="-200", currency="EUR")
            ids["TRANSFER of V of unreadable quantity"] = _insert(conn, broker_id=sender_v, asset_id=v, type="TRANSFER", quantity="n/a", description="a quantity that is not a number")
            ids["leg of V"] = _insert(conn, id=UNREADABLE_POOL_LEG, broker_id=sender_v, asset_id=v, type="TRANSFER", quantity="-2", description="2 V to a deleted broker")
            stored = conn.execute("SELECT typeof(quantity), quantity < 0 FROM transactions WHERE id = ?", (ids["TRANSFER of V of unreadable quantity"],)).fetchone()
            assert stored == ("text", 0), f"setup: the quantity 'n/a' must stay text, never below zero; (typeof, < 0) = {stored}"
        conn.commit()
        broken = sorted(rowid for _table, rowid, _parent, _key in conn.execute("PRAGMA foreign_key_check").fetchall())
    assert broken == ([DANGLING_LEG] if dangling else []), f"setup: the only broken link must be leg {DANGLING_LEG}'s; found {broken}"
    return ids


def _legs_view(legs: list[Any]) -> dict[int, tuple]:
    """What ``convert_lone_giving_legs`` answered, by leg id: (broker, date, quantity, asset). Its cost fields of decision
    47 are not read: N78-1 computes no cost."""
    return {leg.id: (leg.broker_id, leg.date, leg.quantity, leg.asset_id) for leg in legs}


def _expected_legs(ids: dict[str, int], *, dangling: bool = False, unreadable: bool = False) -> dict[int, tuple]:
    """The answer for the lone giving legs of the book: 470100 and 470200; with ``dangling`` 470300, with ``unreadable``
    470050."""
    legs = {
        X_LEG: (ids["sender of X"], LEG_DATE, Decimal("-4"), ids["X"]),
        PYG_LEG: (ids["sender of Y"], LEG_DATE, Decimal("-3"), ids["Y"]),
    }
    if dangling:
        legs[DANGLING_LEG] = (ids["sender of W"], LEG_DATE, Decimal("-2"), ids["W"])
    if unreadable:
        legs[UNREADABLE_POOL_LEG] = (ids["sender of V"], LEG_DATE, Decimal("-2"), ids["V"])
    return legs


def _assert_converted(before: Rows, after: Rows, leg_ids: tuple[int, ...] | list[int]) -> None:
    """Every leg of ``leg_ids`` is an ADJUSTMENT without a value in ``after``, the rest of it as it was in ``before``."""
    assert {leg_id: _without_updated_at(after[leg_id]) for leg_id in leg_ids} == {leg_id: _without_updated_at(_without_a_value(before[leg_id])) for leg_id in leg_ids}, (
        f"N78-1: each lone giving leg {list(leg_ids)} becomes an ADJUSTMENT without a value; (type, cost, currency, link) now: "
        f"{ {leg_id: (after[leg_id]['type'], after[leg_id]['cost_basis_override'], after[leg_id]['cost_basis_currency'], after[leg_id]['related_transaction_id']) for leg_id in leg_ids} }"
    )


def _broken_links(db: Path) -> list[int]:
    """The ids of the rows ``PRAGMA foreign_key_check`` reports, read by a connection of its own."""
    with _connect(db) as conn:
        return sorted(rowid for _table, rowid, _parent, _key in conn.execute("PRAGMA foreign_key_check").fetchall())


def _make_configured(monkeypatch: pytest.MonkeyPatch, module: ModuleType, engine: AsyncEngine) -> None:
    """Make ``engine`` the configured one for the startup wrapper: the singleton ``get_async_engine`` returns, wherever
    that function was imported, and a copy of it the module may hold by name."""
    monkeypatch.setattr(db_session, "async_engine", engine)
    if hasattr(module, "async_engine"):
        monkeypatch.setattr(module, "async_engine", engine)


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


@asynccontextmanager
async def _opened(head: Path, root: Path, **plant: bool) -> AsyncIterator[Book]:
    """A copy of the database at head under ``root`` with the book planted (``_plant``'s flags), and an engine on it,
    disposed after."""
    db = _copy(head, root)
    ids = _plant(db, **plant)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    try:
        yield Book(db=db, ids=ids, engine=engine)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def book(head: Path, tmp_path: Path) -> AsyncIterator[Book]:
    """A copy of the database at head with the book and its untouchables planted, and an engine on it, disposed after."""
    async with _opened(head, tmp_path, untouchables=True) as opened:
        yield opened


# =============================================================================
# 1. CONVERT_LONE_GIVING_LEGS
# =============================================================================


@pytest.mark.asyncio
async def test_every_lone_giving_leg_becomes_an_adjustment_without_a_value_and_the_caller_commits(book: Book) -> None:
    """Contract 1 (RED until N78-1): legs 470100 and 470200 become ADJUSTMENTs −4 and −3 without a value — whatever their
    brokers' pools hold, PYG with no rate included —, same quantity, asset, date, description and tags, still unlinked,
    updated_at moved; the answer holds a LoneLeg for each. Nothing is committed before the caller commits: read by another
    connection in between, every row is as it was. Before N78-1: 470100 at its broker's Auto cost, 20 EUR; 470200 left a
    TRANSFER."""
    module = _module()
    before = _transactions(book.db)
    started = _utc_now()

    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        legs = await module.convert_lone_giving_legs(session)
        in_between = _transactions(book.db)
        await session.commit()
    finished = _utc_now()
    after = _transactions(book.db)

    assert _legs_view(legs) == _expected_legs(book.ids)
    assert in_between == before, "convert_lone_giving_legs committed by itself: its caller commits"
    _assert_converted(before, after, BOOK_LEGS)
    problems = {leg_id: _not_moved(before[leg_id]["updated_at"], after[leg_id]["updated_at"], started, finished) for leg_id in BOOK_LEGS}
    assert problems == dict.fromkeys(BOOK_LEGS), f"{problems} — what is cached on updated_at would not be computed again"


@pytest.mark.asyncio
async def test_a_lone_giving_leg_over_a_pool_without_a_conversion_is_converted_too(book: Book) -> None:
    """Contract 1 (RED until N78-1): leg 470200's broker paid for Y in PYG, which no rate converts — no cost is needed, so
    the leg becomes an ADJUSTMENT −3 without a value like any other, and is answered. Before N78-1 its Auto cost was
    missing and it stayed a TRANSFER, every column as it was."""
    module = _module()
    before = _transactions(book.db)

    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        legs = await module.convert_lone_giving_legs(session)
        await session.commit()

    assert _legs_view(legs).get(PYG_LEG) == _expected_legs(book.ids)[PYG_LEG]
    _assert_converted(before, _transactions(book.db), [PYG_LEG])


@pytest.mark.asyncio
async def test_only_the_lone_giving_legs_change(book: Book) -> None:
    """Contract 1 (RED until N78-1): the lone receiving legs — without a cost basis and with one: the sync fix's — and both
    legs of the linked pair are neither changed nor answered; every row but legs 470100 and 470200 is as it was. Before
    N78-1 only 470100 changed."""
    module = _module()
    before = _transactions(book.db)
    untouchable_ids = {book.ids[label] for label in UNTOUCHABLES}

    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        legs = await module.convert_lone_giving_legs(session)
        await session.commit()
    after = _transactions(book.db)

    assert {leg_id: after[leg_id]["type"] for leg_id in BOOK_LEGS} == dict.fromkeys(BOOK_LEGS, "ADJUSTMENT"), f"barrier: legs {BOOK_LEGS} must be converted, or 'nothing else changed' proves nothing"
    assert {leg.id for leg in legs} & untouchable_ids == set(), f"only lone giving legs are answered: {_legs_view(legs)}"
    assert {tx_id: row for tx_id, row in after.items() if tx_id not in BOOK_LEGS} == {tx_id: row for tx_id, row in before.items() if tx_id not in BOOK_LEGS}


@pytest.mark.asyncio
async def test_a_dry_run_answers_the_legs_and_changes_nothing(book: Book) -> None:
    """Contract 1 (green since decision 47, its costs no longer read since N78-1): ``dry_run=True`` answers the legs a run
    would convert — 470100 and 470200 — and leaves every table as it was, even once its caller commits."""
    module = _module()
    before = _tables(book.db)

    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        legs = await module.convert_lone_giving_legs(session, dry_run=True)
        await session.commit()  # the caller commits: a dry run must have left nothing to commit

    assert _legs_view(legs) == _expected_legs(book.ids)
    assert _tables(book.db) == before


@pytest.mark.asyncio
async def test_a_second_run_finds_nothing_left_to_convert_and_writes_nothing(book: Book) -> None:
    """Contract 1 (RED until N78-1): after a committed run, a second one finds no lone giving leg — 470100 and 470200 are
    ADJUSTMENTs now — answers none, and every table stays as the first run left it. Before N78-1 470200 stayed a TRANSFER
    and was answered again without a cost."""
    module = _module()
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        await module.convert_lone_giving_legs(session)
        await session.commit()
    once = _tables(book.db)
    assert _transactions(book.db)[X_LEG]["type"] == "ADJUSTMENT", f"barrier: the first run must convert leg {X_LEG}, or the second proves nothing"

    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        second = await module.convert_lone_giving_legs(session)
        await session.commit()

    assert _legs_view(second) == {}, f"N78-1: the first run converted every lone giving leg, so the second finds none: {_legs_view(second)}"
    assert _tables(book.db) == once


@pytest.mark.asyncio
async def test_a_lone_giving_leg_over_an_unreadable_pool_is_converted_too(head: Path, tmp_path: Path) -> None:
    """Contract 1 (RED until N78-1): leg 470050's broker holds a TRANSFER of V whose quantity is 'n/a'. No cost is
    computed, so nothing reads that pool: 470050 becomes an ADJUSTMENT −2 without a value, as 470100 and 470200 do, and the
    three are answered. The row of quantity 'n/a' is neither answered nor touched: the legs are selected with
    quantity < 0. Before N78-1 (decision 1) computing 470050's Auto cost raised: it stayed a TRANSFER, answered with the
    error as its reason, and the run went on."""
    module = _module()
    async with _opened(head, tmp_path, unreadable=True) as opened:
        before = _transactions(opened.db)
        async with AsyncSession(opened.engine, expire_on_commit=False) as session:
            legs = await module.convert_lone_giving_legs(session)
            await session.commit()
        after = _transactions(opened.db)

    converted = (UNREADABLE_POOL_LEG, *BOOK_LEGS)
    assert _legs_view(legs) == _expected_legs(opened.ids, unreadable=True)
    _assert_converted(before, after, converted)
    assert {tx_id: row for tx_id, row in after.items() if tx_id not in converted} == {tx_id: row for tx_id, row in before.items() if tx_id not in converted}


@pytest.mark.asyncio
async def test_a_giving_leg_whose_link_names_a_deleted_row_is_lone_in_a_dry_run_as_in_a_run(head: Path, tmp_path: Path) -> None:
    """Contract 1, decision 2 (RED until N78-1): leg 470300's link names a row deleted with foreign keys off, and no fix
    has run — it counts as lone all the same. A dry run answers it beside 470100 and 470200, and writes nothing; the run
    after it answers the same and converts the three without a value, 470300's dangling link gone, so the foreign key
    check comes out clean. Before N78-1: 470300 and 470100 at their brokers' Auto costs, 30 and 20 EUR; 470200 left."""
    module = _module()
    async with _opened(head, tmp_path, untouchables=True, dangling=True) as opened:
        tables_before, before = _tables(opened.db), _transactions(opened.db)
        async with AsyncSession(opened.engine, expire_on_commit=False) as session:
            previewed = await module.convert_lone_giving_legs(session, dry_run=True)
            await session.commit()  # the caller commits: a dry run must have left nothing to commit
        tables_after_the_dry_run = _tables(opened.db)
        async with AsyncSession(opened.engine, expire_on_commit=False) as session:
            converted = await module.convert_lone_giving_legs(session)
            await session.commit()
        after, broken = _transactions(opened.db), _broken_links(opened.db)

    expected = _expected_legs(opened.ids, dangling=True)
    assert _legs_view(previewed) == expected, "the dry run must list the leg whose link names a deleted row, with its cost"
    assert tables_after_the_dry_run == tables_before
    assert _legs_view(converted) == expected, "the run must answer what its dry run did"
    _assert_converted(before, after, (*BOOK_LEGS, DANGLING_LEG))
    assert broken == [], f"a converted leg keeps no link to a deleted row: foreign_key_check reports {broken}"


# =============================================================================
# 2. LONELEG
# =============================================================================


def _lone_leg(lone_leg: type, **known: Any) -> Any:
    """A ``LoneLeg`` with the ``known`` fields, any other field without a default given None: the cost fields of decision
    47, if the cure keeps them, carry nothing since N78-1."""
    values = dict(known)
    for field in dataclasses.fields(lone_leg):
        if field.name not in values and field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            values[field.name] = None
    return lone_leg(**values)


def test_a_lone_leg_is_a_frozen_record_that_describes_itself_in_one_line() -> None:
    """Contract 2 (green since decision 47, its cost fields no longer read since N78-1): ``LoneLeg`` is a frozen dataclass
    with at least ``id, broker_id, date, quantity, asset_id``; ``describe`` gives one line holding its id, in a dry run and
    in a real one. Before N78-1 the contract also held ``cost``, ``cost_currency``, ``reason`` and ``converted``, and a
    line stating the cost."""
    module = _module()
    lone_leg = module.LoneLeg
    assert dataclasses.is_dataclass(lone_leg), "LoneLeg must be a dataclass"
    fields = [field.name for field in dataclasses.fields(lone_leg)]
    assert {"id", "broker_id", "date", "quantity", "asset_id"} <= set(fields), f"LoneLeg's fields: {fields}"
    leg = _lone_leg(lone_leg, id=X_LEG, broker_id=7, date=LEG_DATE, quantity=Decimal("-4"), asset_id=11)

    with pytest.raises(dataclasses.FrozenInstanceError):
        leg.quantity = Decimal("-1")  # type: ignore[misc]
    for dry_run in (True, False):
        line = leg.describe(dry_run=dry_run)
        assert isinstance(line, str) and len(line.strip().splitlines()) == 1, f"describe(dry_run={dry_run}) gives one line: {line!r}"
        assert _names_the_leg(line, X_LEG), f"describe(dry_run={dry_run}) names the leg: {line!r}"


# =============================================================================
# 3. RUN_LONE_GIVING_LEGS — ON A FILE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("dry_run", [pytest.param(False, id="run"), pytest.param(True, id="dry-run")])
async def test_run_lone_giving_legs_converts_a_file_or_leaves_it_as_it_was(head: Path, tmp_path: Path, dry_run: bool) -> None:
    """Contract 3 (RED until N78-1 for the run): on a SQLite file, through an engine of its own — a run commits the
    conversion of legs 470100 and 470200 without a value and nothing else; a dry run answers the same legs and leaves
    every table as it was. Before N78-1 the run converted 470100 alone, at 20 EUR."""
    module = _module()
    db = _copy(head, tmp_path)
    ids = _plant(db, untouchables=True)
    tables_before, before = _tables(db), _transactions(db)

    legs = await module.run_lone_giving_legs(db, dry_run=dry_run)

    after = _transactions(db)
    assert _legs_view(legs) == _expected_legs(ids)
    if dry_run:
        assert _tables(db) == tables_before
        return
    _assert_converted(before, after, BOOK_LEGS)
    assert {tx_id: row for tx_id, row in after.items() if tx_id not in BOOK_LEGS} == {tx_id: row for tx_id, row in before.items() if tx_id not in BOOK_LEGS}


# =============================================================================
# 4. THE STARTUP STEP AND ITS WRAPPER
# =============================================================================


def test_the_startup_step_runs_right_after_the_post_migration_fixes() -> None:
    """Contract 4 (RED until decision 47): ``lone-transfer-legs`` stands in ``STARTUP_STEPS`` right after
    ``post-migration-fixes`` — the sync fixes have converted the lone receiving legs and cleared the dangling links —
    and before anything else opens the database."""
    names = [step.name for step in app_lifespan.STARTUP_STEPS]

    assert STEP in names, f"decision 47: no startup step {STEP!r} in {names}"
    assert names.index(STEP) == names.index("post-migration-fixes") + 1, f"{STEP!r} must run right after 'post-migration-fixes': {names}"


def test_the_startup_step_reaches_the_wrapper_through_app_lifespan_when_it_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (RED until decision 47): the step calls ``app_lifespan.convert_lone_giving_legs_at_startup`` as it is
    when the step runs, without arguments — the module's convention, so that a test replaces it — and returns what it
    returns, for the runner to await."""
    steps = [step for step in app_lifespan.STARTUP_STEPS if step.name == STEP]
    assert len(steps) == 1, f"decision 47: {len(steps)} startup steps named {STEP!r}"
    calls: list[tuple[tuple, dict]] = []
    sentinel = object()

    def replacement(*args: Any, **kwargs: Any) -> object:
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(app_lifespan, "convert_lone_giving_legs_at_startup", replacement, raising=False)

    result = steps[0].run()
    if inspect.iscoroutine(result):  # the real coroutine function was reached: never run it
        result.close()

    assert calls == [((), {})], "the step did not call app_lifespan.convert_lone_giving_legs_at_startup as it is when the step runs"
    assert result is sentinel


@pytest.mark.asyncio
async def test_the_startup_wrapper_converts_in_a_session_on_the_configured_engine_and_commits(book: Book, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (RED until N78-1): with a private file's engine made the configured one, the wrapper converts once, for
    real (not a dry run), in a session of its own on that engine, and commits: legs 470100 and 470200 are ADJUSTMENTs
    without a value in the file (before N78-1: 470100 at 20 EUR). The conversion is a double that runs the real one only on
    that engine."""
    module = _module()
    _make_configured(monkeypatch, module, book.engine)
    real = module.convert_lone_giving_legs
    seen: list[tuple[bool, bool]] = []

    async def only_on_the_private_file(session: AsyncSession, *args: Any, **kwargs: Any) -> list[Any]:
        seen.append((session.bind is book.engine, bool(kwargs.get("dry_run", False))))
        if session.bind is not book.engine:
            return []  # another database: left as it is
        return await real(session, *args, **kwargs)

    monkeypatch.setattr(module, "convert_lone_giving_legs", only_on_the_private_file)
    before = _transactions(book.db)

    await module.convert_lone_giving_legs_at_startup()

    after = _transactions(book.db)
    assert seen == [(True, False)], f"one real conversion, in a session on the configured engine, expected; (on that engine, dry run) per call: {seen}"
    _assert_converted(before, after, BOOK_LEGS)


@pytest.mark.asyncio
async def test_the_startup_wrapper_never_raises(book: Book, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (RED until decision 47): the conversion raises — the wrapper returns all the same, logs the failure (a
    warning or an error) and leaves the database as it was: a startup never stops on this step."""
    module = _module()
    _make_configured(monkeypatch, module, book.engine)

    async def fails(*args: Any, **kwargs: Any) -> list[Any]:
        raise _InjectedFailure(INJECTED)

    monkeypatch.setattr(module, "convert_lone_giving_legs", fails)
    before = _tables(book.db)

    with capture_logs() as logs:
        module_logger = getattr(module, "logger", None)
        if module_logger is not None:  # barrier: what the module logs must reach the capture, or "it logged" proves nothing
            module_logger.debug(LOG_CANARY)
            assert any(entry.get("event") == LOG_CANARY for entry in logs), f"barrier: the module's logger does not reach capture_logs: {logs}"
        try:
            await module.convert_lone_giving_legs_at_startup()
        except Exception as exc:  # noqa: BLE001 — any exception is the failure under test
            pytest.fail(f"convert_lone_giving_legs_at_startup raised {exc!r}: a failure at startup must be logged and swallowed")

    logged = [entry for entry in logs if entry.get("event") != LOG_CANARY and entry.get("log_level") in ("warning", "error", "critical")]
    assert logged, f"the failure was swallowed without a word: {logs}"
    assert _tables(book.db) == before


@contextmanager
def _module_log(module: ModuleType) -> Iterator[list[dict[str, Any]]]:
    """What the module logs inside the block, behind a barrier: a canary through its own logger must reach the capture,
    or "it warned" and "it said nothing" would prove nothing."""
    with capture_logs() as logs:
        module.logger.debug(LOG_CANARY)
        assert any(entry.get("event") == LOG_CANARY for entry in logs), f"barrier: the module's logger does not reach capture_logs: {logs}"
        yield logs


def _warnings(logs: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    """``(event, level)`` of every captured line at warning level or above, in order."""
    return [(entry.get("event"), entry.get("log_level")) for entry in logs if entry.get("log_level") in ("warning", "error", "critical")]


def _plant_nothing_lone(db: Path) -> dict[str, int]:
    """Rows that look like lone giving legs and are not: a purchase of X, a TRANSFER pair still linked both ways, a lone
    RECEIVING leg (the sync fix's) and a TRANSFER of X whose quantity is 'n/a' (never read as below zero); the ids by
    label."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        x = _asset(conn, "X")
        sender, receiver = _broker(conn, "Pair sender"), _broker(conn, "Pair receiver")
        ids = {"X": x, "sender": sender, "receiver": receiver}
        ids["purchase of X"] = _insert(conn, broker_id=sender, asset_id=x, type="BUY", date=BUY_DAY, quantity="10", amount="-200", currency="EUR")
        ids["linked giving leg"], ids["linked receiving leg"] = _pair(
            conn,
            {"broker_id": sender, "asset_id": x, "type": "TRANSFER", "quantity": "-1"},
            {"broker_id": receiver, "asset_id": x, "type": "TRANSFER", "quantity": "1", "cost_basis_override": "20", "cost_basis_currency": "EUR"},
        )
        ids["lone receiving leg"] = _insert(conn, broker_id=receiver, asset_id=x, type="TRANSFER", quantity="2", description="2 X from a deleted broker")
        ids["TRANSFER of unreadable quantity"] = _insert(conn, broker_id=sender, asset_id=x, type="TRANSFER", quantity="n/a")
        conn.commit()
    return ids


@pytest.mark.asyncio
async def test_the_startup_wrapper_touches_nothing_when_the_database_fails_its_quick_check(book: Book, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (guard of the quick check): lone legs are there — 470100 would be converted —, but
    ``_database_is_sound`` (replaced through the module) answers False: the wrapper asks it once, on the configured
    engine, then logs exactly one warning, «Lone transfer legs left as they are: the database failed its quick check»,
    writes nothing and returns without raising. A damaged database is never touched, as the post-migration fixes leave
    it."""
    module = _module()
    _make_configured(monkeypatch, module, book.engine)
    checks: list[bool] = []

    async def fails_its_quick_check(session: AsyncSession, *args: Any, **kwargs: Any) -> bool:
        checks.append(session.bind is book.engine)
        return False

    monkeypatch.setattr(module, "_database_is_sound", fails_its_quick_check)
    before = _tables(book.db)
    leg = _transactions(book.db)[X_LEG]
    assert (leg["type"], leg["related_transaction_id"]) == ("TRANSFER", None), f"precondition broken: leg {X_LEG} must be a lone giving TRANSFER: {leg}"

    with _module_log(module) as logs:
        try:
            await module.convert_lone_giving_legs_at_startup()
        except Exception as exc:  # noqa: BLE001 — any exception is the failure under test
            pytest.fail(f"convert_lone_giving_legs_at_startup raised {exc!r}: a failed quick check must be logged, never raised")

    assert checks == [True], f"with lone legs present, the quick check must be asked once, in a session on the configured engine; (on that engine) per call: {checks}"
    assert _warnings(logs) == [(QUICK_CHECK_FAILED, "warning")], f"the warnings logged: {_warnings(logs)}"
    assert _tables(book.db) == before, "a database that failed its quick check must not be written"


@pytest.mark.asyncio
async def test_the_startup_wrapper_checks_nothing_when_no_giving_leg_is_lone(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 4 (guard of the common case): the configured database holds a linked pair, a lone receiving leg and a
    TRANSFER of unreadable quantity — no lone giving leg —, so the wrapper returns at once: ``_database_is_sound``
    (replaced through the module) is never asked, nothing is written, nothing raised, nothing logged at warning level.

    The silence is the barrier: a wrapper that failed before its first query would not ask the check either, but it would
    log its failure. The case above is the control: the same wrapper, legs present, asks it."""
    module = _module()
    db = _copy(head, tmp_path)
    _plant_nothing_lone(db)
    before = _tables(db)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    checks: list[bool] = []

    async def recorded_check(session: AsyncSession, *args: Any, **kwargs: Any) -> bool:
        checks.append(session.bind is engine)
        return True

    try:
        _make_configured(monkeypatch, module, engine)
        monkeypatch.setattr(module, "_database_is_sound", recorded_check)
        with _module_log(module) as logs:
            try:
                await module.convert_lone_giving_legs_at_startup()
            except Exception as exc:  # noqa: BLE001 — any exception is the failure under test
                pytest.fail(f"convert_lone_giving_legs_at_startup raised {exc!r}")
    finally:
        await engine.dispose()

    assert _warnings(logs) == [], f"nothing lone, nothing to say — a warning here is a failure the wrapper swallowed: {_warnings(logs)}"
    assert checks == [], f"no lone giving leg: the quick check must not be asked; (on the configured engine) per call: {checks}"
    assert _tables(db) == before


# =============================================================================
# 5. THE OFFLINE SCRIPT
# =============================================================================


LONE_GIVING_LEGS = (UNREADABLE_POOL_LEG, X_LEG, PYG_LEG, DANGLING_LEG)  # the four of a book planted dangling and unreadable


def test_the_offline_dry_run_prints_one_line_per_lone_giving_leg(head: Path, tmp_path: Path) -> None:
    """Contract 5 (green since decision 47, its costs no longer read since N78-1): ``--dry-run`` exits 0, writes nothing,
    and prints one line per lone giving leg — among the lines that are not JSON log lines —, 470300's included, whose link
    names a deleted row the dry run does not unlink (decision 2). Before N78-1 the lines of 470100 and 470300 also stated
    the 20 and 30 EUR they would take."""
    db = _copy(head, tmp_path)
    _plant(db, dangling=True, unreadable=True)
    _settle(db)
    before = _tables(db)

    completed = _run_script("--db", str(db), "--data-dir", str(tmp_path / "data"), "--dry-run")

    printed = _printed_lines(completed.stdout)
    by_leg = {leg_id: [line for line in printed if _names_the_leg(line, leg_id)] for leg_id in LONE_GIVING_LEGS}
    assert completed.returncode == 0, _output(completed)
    assert (_tables(db), _backups(db)) == (before, []), f"a dry run writes nothing\n{_output(completed)}"
    assert {leg_id: len(lines) for leg_id, lines in by_leg.items()} == dict.fromkeys(LONE_GIVING_LEGS, 1), f"one printed line per lone giving leg\n{_output(completed)}"


def test_the_offline_script_converts_every_lone_giving_leg_after_the_fixes(head: Path, tmp_path: Path) -> None:
    """Contract 5 (RED until N78-1): a real run exits 0; ``orphan_pair_halves`` clears leg 470300's dangling link, then the
    step converts the four lone giving legs — 470050, 470100, 470200, 470300 — into ADJUSTMENTs without a value in the same
    run, and prints one line per leg. Before N78-1: 470100 at 20 EUR and 470300 at 30 EUR, 470200 and 470050 left
    TRANSFERs (a missing conversion, a cost computation that raised)."""
    db = _copy(head, tmp_path)
    _plant(db, dangling=True, unreadable=True)
    before = _transactions(db)

    completed = _run_script("--db", str(db), "--data-dir", str(tmp_path / "data"))

    after = _transactions(db)
    printed = _printed_lines(completed.stdout)
    by_leg = {leg_id: [line for line in printed if _names_the_leg(line, leg_id)] for leg_id in LONE_GIVING_LEGS}
    assert completed.returncode == 0, _output(completed)
    assert _summary_says(completed, "orphan_pair_halves", "applied"), f"barrier: the fix must clear leg {DANGLING_LEG}'s dangling link\n{_output(completed)}"
    _assert_converted(before, after, LONE_GIVING_LEGS)
    assert {leg_id: len(lines) for leg_id, lines in by_leg.items()} == dict.fromkeys(LONE_GIVING_LEGS, 1), f"one printed line per lone giving leg\n{_output(completed)}"


def test_the_offline_script_runs_no_step_after_a_failed_fix(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 5, decision 3 (guard, green today and after decision 47): ``orphan_pair_halves`` fails — its own check made
    to report a problem, as test_post_migration_orphan_pairs.py's contract 7 provokes it; leg 470300's dangling link gives
    it something to do — and the script runs no step: ``main`` returns 1 and every row is as it was, leg 470100 — which
    the step would convert — still a TRANSFER. Called in this process, as the next case."""
    script = importlib.import_module(SCRIPT)
    db = _copy(head, tmp_path)
    _plant(db, dangling=True)
    before = _transactions(db)
    monkeypatch.setattr(OrphanPairHalfFix, "verify", lambda self, conn, anomaly, ctx: [PROVOKED])

    code = script.main(["--db", str(db), "--data-dir", str(tmp_path / "data")])

    assert code == 1, f"a fix failed, the script must exit 1: main returned {code!r}"
    assert _transactions(db) == before, "a failed fix rolls back, and no step runs after it"


def test_the_offline_script_exits_1_when_the_step_raises(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 5 (green since decision 47): the step as a whole raises — the conversion replaced, in the module and
    wherever the script holds it by name — and ``main`` returns 1, the database as it was. Called in this process, as test_db/test_post_migration.py's two children call it."""
    module = _module()
    script = importlib.import_module(SCRIPT)
    db = _copy(head, tmp_path)
    _plant(db)
    _settle(db)
    before = _tables(db)

    async def fails(*args: Any, **kwargs: Any) -> list[Any]:
        raise _InjectedFailure(INJECTED)

    monkeypatch.setattr(module, "convert_lone_giving_legs", fails)
    for name in ("convert_lone_giving_legs", "run_lone_giving_legs"):
        if hasattr(script, name):
            monkeypatch.setattr(script, name, fails)

    code = script.main(["--db", str(db), "--data-dir", str(tmp_path / "data")])

    assert code == 1, f"the step raised, the script must exit 1: main returned {code!r}"
    assert _tables(db) == before

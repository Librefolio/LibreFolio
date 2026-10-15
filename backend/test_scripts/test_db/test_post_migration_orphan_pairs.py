"""N1b-2: the post-migration fix ``orphan_pair_halves`` on the halves an older broker deletion left behind (V-3, D-J4).

``OrphanPairHalfFix`` (backend/app/db/post_migration/orphan_pair_halves.py), the second of ``FIXES``, converts
the half of a pair whose partner is gone into the standalone row a split of the pair leaves, and leaves alone
what it may not convert (point 47 of release 1.3). The contract pinned here:

1. A database whose pairs are all whole needs nothing: outcome ``clean``, nothing written, no backup.
2. Conversions — a half whose link a 1.2 deletion cleared (NULL) and one whose link names a deleted row
   alike: a received TRANSFER becomes an ADJUSTMENT with its asset and its cost basis, or without one when
   it had none; a CASH_TRANSFER or an FX_CONVERSION becomes a WITHDRAWAL when its amount is negative, a
   DEPOSIT otherwise, without an asset. The link goes and ``updated_at`` moves to the run's time; every other
   column stays: date, quantity, amount, currency, cost basis and its currency, description, tags,
   asset_event_id, created_at.
3. Left as they are: a giving TRANSFER leg with its link NULL, not even ``updated_at`` touched; a giving
   TRANSFER leg whose link names a deleted row loses that link only (``updated_at`` moves), type and cost
   unchanged; a row whose quantity or amount is not a number, untouched with its link NULL, unlinked with a
   dangling one; the pairs that are whole and the types no pair has, untouched.
4. The run: outcome ``applied``, no error, no backup left, ``PRAGMA foreign_key_check`` empty, the row count
   of every table unchanged, only the halves above changed. A second run: ``clean``, nothing written.
5. A dry run: ``would_apply``, the database byte-identical, no backup. Its detection warning (logger
   ``backend.app.db.post_migration.orphan_pair_halves``) lists the ids by conversion (``TRANSFER->ADJUSTMENT``
   and so on), those left without cost basis, those only unlinked, the giving TRANSFER legs and the rows whose
   sign cannot be read. With only giving legs left, links already NULL, the warning is the "left as they are"
   one and the outcome is ``clean``, dry run or not.
6. After an applied run, one INFO line per changed row — ``Transaction without its pair converted`` or
   ``… unlinked`` — with transaction_id, from_type, to_type and missing_cost_basis; none on a dry run, none
   on a failed run.
7. A verification that fails (``OrphanPairHalfFix.verify`` made to report a problem): outcome ``failed``, the
   database as it was, the backup kept beside it with the database before, no per-row INFO line.
8. A row of a type no pair has — an ADJUSTMENT, a DEPOSIT — whose link names a deleted row loses that link only,
   as delete_by_broker treats "a link no split knows": ``updated_at`` moves, every other column stays, the row is
   listed under ``unlinked_only`` and gets its ``unlinked`` line; the run is ``applied`` beside a half it converts
   and on its own. Seen RED before the fix knew such rows (15/10): it read only the three paired types, so beside a
   conversion the foreign key check of the whole database failed the run — the backup kept, at every start — and on
   their own they stayed broken under a ``clean`` outcome. A row of another type whose link names an existing row is
   left untouched (guard).
9. The offline script, ``python -m backend.app.db.post_migration`` (W-B23): its log reaches stdout as the server
   writes it, one JSON object per line, among its summary lines (``Fix orphan_pair_halves: applied``). A real run
   prints one line per changed row, ``converted`` or ``unlinked`` with its ``transaction_id``, and the closing
   ``Post-migration fixes applied and verified`` with ``seconds``; a dry run prints the detection warning with its
   ``conversions``, no line per row, and writes nothing. RED until ``__main__`` configures logging: today the INFO
   lines are dropped and the warning reaches stderr only, as plain text, through Python's last-resort handler.
   The script runs at the INFO level whatever the shell exports (``LIBREFOLIO_LOG_LEVEL``).

The databases. One is built at head by the real migrations — ``alembic upgrade head`` in a child process, always
with ``-x sqlalchemy.url=``, as test_post_migration.py does — and copied for each test. The rows are written with
sqlite3, foreign keys off, the way the older deletions left them: every half had its partner on a broker that was
then deleted, either the 1.2 way (the links pointing at its rows cleared first) or leaving the links behind, so
that they name rows that no longer exist. The expected types and lists are written out here, never read from the
fix. Every database is temporary, and the configured data dir points at a sandbox with a canary, as in
test_post_migration.py: nothing here can reach the lane's database.
"""

from __future__ import annotations

import hashlib
import json
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
from pathlib import Path
from typing import Any, Optional

import pytest
import structlog
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT
from backend.app.db import post_migration
from backend.app.db.post_migration import PostMigrationReport
from backend.app.db.post_migration.orphan_pair_halves import OrphanPairHalfFix

FIX = "orphan_pair_halves"
LOGGER = "backend.app.db.post_migration.orphan_pair_halves"
RUN_LOGGER = "backend.app.db.post_migration"
CONVERTED = "Transaction without its pair converted"
UNLINKED = "Transaction without its pair unlinked"
FOUND = "Transactions found without their pair"  # the detection warning when something converts
LEFT = "Transactions without their pair left as they are"  # … when nothing does
APPLIED_EVENT = "Post-migration fixes applied and verified"
FAILED_EVENT = "Post-migration fix failed: the database was left as it was"
PROVOKED = "provoked: the fix's own check found a problem"
TIMESTAMP = "%Y-%m-%d %H:%M:%S.%f"  # how the app stores a DATETIME, and the planted rows with it
CHILD_TIMEOUT = 300
CANARY = b"canary: a configured data dir that no run was given\n"
CANARY_FILE = Path("broker_reports", "uploaded", "broker_999", "canary.csv")

NOT_APPLIED = "barrier: the fix did not report 'applied', so the rows below say nothing about a conversion"
NOT_CAPTURED = "barrier: the capture saw no event of the run, so 'no line' would pass for a logger that never reaches it"

DAY = "2019-09-04"
STAMP = "2019-09-04 10:00:00.000000"  # created_at and updated_at of every planted row
HOW = ("link NULL", "dangling link")  # the 1.2 deletion cleared the link; an older one left it naming a deleted row

# What each lone half becomes — the oracle of contract 2, written out: (its type, the type it takes).
CONVERSIONS = {
    "received TRANSFER with cost basis": ("TRANSFER", "ADJUSTMENT"),
    "received TRANSFER without cost basis": ("TRANSFER", "ADJUSTMENT"),
    "CASH_TRANSFER out": ("CASH_TRANSFER", "WITHDRAWAL"),
    "CASH_TRANSFER in": ("CASH_TRANSFER", "DEPOSIT"),
    "FX_CONVERSION out": ("FX_CONVERSION", "WITHDRAWAL"),
    "FX_CONVERSION in": ("FX_CONVERSION", "DEPOSIT"),
}
CONVERTED_LABELS = [f"{kind}, {how}" for kind in CONVERSIONS for how in HOW]
# The halves it may not convert: with a dangling link they lose that link only, keeping their type.
UNLINKED_ONLY = {
    "giving TRANSFER, dangling link": "TRANSFER",
    "TRANSFER of unreadable quantity, dangling link": "TRANSFER",
    "CASH_TRANSFER of unreadable amount, dangling link": "CASH_TRANSFER",
}
# Every row nothing may touch: the same halves with their link already NULL, the whole pairs, the other types.
UNTOUCHED = (
    "giving TRANSFER, link NULL",
    "TRANSFER of unreadable quantity, link NULL",
    "CASH_TRANSFER of unreadable amount, link NULL",
    "whole TRANSFER pair, out",
    "whole TRANSFER pair, in",
    "whole CASH_TRANSFER pair, out",
    "whole CASH_TRANSFER pair, in",
    "whole FX_CONVERSION pair, out",
    "whole FX_CONVERSION pair, in",
    "DEPOSIT",
    "BUY",
    "ADJUSTMENT",
)

Tables = dict[str, list[tuple[Any, ...]]]
Rows = dict[int, dict[str, Any]]


@dataclass(frozen=True)
class Run:
    """One observed call of ``run_post_migration_fixes``: its report, its log, and the database just before and just after it."""

    db: Path
    report: PostMigrationReport
    tables_before: Tables
    tables_after: Tables
    rows_before: Rows
    rows_after: Rows
    counts_before: dict[str, int]
    counts_after: dict[str, int]
    digest_before: str
    digest_after: str
    backups_after: list[str]
    logs: list[dict[str, Any]]
    started: datetime
    finished: datetime
    ids: dict[str, int] = field(default_factory=dict)

    def warnings(self) -> list[dict[str, Any]]:
        """The detection warnings of the fix."""
        return [entry for entry in self.logs if entry.get("logger") == LOGGER and entry.get("log_level") == "warning"]

    def row_lines(self) -> list[tuple[Any, ...]]:
        """The fix's line for each row it changed: (event, level, transaction_id, from_type, to_type, missing_cost_basis)."""
        return sorted((entry["event"], entry.get("log_level"), entry.get("transaction_id"), entry.get("from_type"), entry.get("to_type"), entry.get("missing_cost_basis")) for entry in self.logs if entry.get("logger") == LOGGER and entry.get("event") in (CONVERTED, UNLINKED))

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


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """``python -m backend.app.db.post_migration`` with ``args`` in a child process, as test_post_migration.py runs it — at the INFO level, whatever the shell exports."""
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


def _json_lines(text: str) -> list[dict[str, Any]]:
    """The lines of ``text`` that are JSON objects — log lines as the server writes them — in order; the others are skipped."""
    found = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


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


def _transactions(db: Path) -> Rows:
    """The transactions by id, each as ``{column: value}``."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute("SELECT * FROM transactions ORDER BY id")}


def _counts(tables: Tables) -> dict[str, int]:
    return {name: len(rows) for name, rows in tables.items() if not name.startswith("sqlite_")}


def _foreign_key_violations(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute("PRAGMA foreign_key_check").fetchall()


def _observe(db: Path, ids: dict[str, int], *, dry_run: bool = False) -> Run:
    """Call ``run_post_migration_fixes`` once, without a data dir; record the database, the backups and the log around the call."""
    tables_before, rows_before = _tables(db), _transactions(db)
    _settle(db)
    digest_before = _digest(db)
    started = datetime.now(UTC).replace(tzinfo=None)
    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        report = post_migration.run_post_migration_fixes(db, None, dry_run=dry_run)
    finished = datetime.now(UTC).replace(tzinfo=None)
    digest_after = _digest(db)  # first, before any connection of ours
    backups_after = _backups(db)  # before anything opens a backup
    tables_after = _tables(db)
    return Run(
        db=db,
        report=report,
        tables_before=tables_before,
        tables_after=tables_after,
        rows_before=rows_before,
        rows_after=_transactions(db),
        counts_before=_counts(tables_before),
        counts_after=_counts(tables_after),
        digest_before=digest_before,
        digest_after=digest_after,
        backups_after=backups_after,
        logs=list(logs),
        started=started,
        finished=finished,
        ids=ids,
    )


# =============================================================================
# HELPERS — the rows an older deletion left
# =============================================================================


def _broker(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("INSERT INTO brokers (name, created_at, updated_at) VALUES (?, ?, ?)", (name, STAMP, STAMP)).lastrowid


def _insert(conn: sqlite3.Connection, **columns: Any) -> int:
    """One transaction on DAY, stamped STAMP; ``columns`` add to or replace those."""
    row = {"date": DAY, "quantity": "0", "amount": "0", "created_at": STAMP, "updated_at": STAMP, **columns}
    names, marks = ", ".join(row), ", ".join("?" for _ in row)
    return conn.execute(f"INSERT INTO transactions ({names}) VALUES ({marks})", tuple(row.values())).lastrowid


def _pair(conn: sqlite3.Connection, half: dict[str, Any], partner: dict[str, Any]) -> tuple[int, int]:
    """Two rows linked both ways, as the app writes a pair: ``(half's id, partner's id)``."""
    half_id, partner_id = _insert(conn, **half), _insert(conn, **partner)
    conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (partner_id, half_id))
    conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (half_id, partner_id))
    return half_id, partner_id


def _delete_broker_the_1_2_way(conn: sqlite3.Connection, broker_id: int) -> None:
    """What ``delete_by_broker`` did before 1.3: the links pointing at the broker's rows cleared, then its rows and the broker deleted."""
    conn.execute("UPDATE transactions SET related_transaction_id = NULL WHERE related_transaction_id IN (SELECT id FROM transactions WHERE broker_id = ?)", (broker_id,))
    _delete_broker_leaving_the_links(conn, broker_id)


def _delete_broker_leaving_the_links(conn: sqlite3.Connection, broker_id: int) -> None:
    """A deletion that left the links behind, naming rows that no longer exist (foreign keys off)."""
    conn.execute("DELETE FROM transactions WHERE broker_id = ?", (broker_id,))
    conn.execute("DELETE FROM brokers WHERE id = ?", (broker_id,))


def _halves(x: int, event: int) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Each half a deletion leaves on the kept broker, with the partner it had: ``(kind, half, partner)``.

    Every half carries something a conversion must keep or clear: the received TRANSFERs their asset (one of
    them an asset event too, a column the fix must carry over), cost basis, description and tags; the cash
    halves an asset — not what the app writes on a cash row, but the column a split clears, so the clearing shows.
    """
    return [
        (
            "received TRANSFER with cost basis",
            {"asset_id": x, "type": "TRANSFER", "quantity": "4", "cost_basis_override": "20", "cost_basis_currency": "EUR", "description": "4 X from a deleted broker", "tags": "pair,in", "asset_event_id": event},
            {"asset_id": x, "type": "TRANSFER", "quantity": "-4"},
        ),
        ("received TRANSFER without cost basis", {"asset_id": x, "type": "TRANSFER", "quantity": "3", "description": "3 X, no cost basis", "tags": "pair,in"}, {"asset_id": x, "type": "TRANSFER", "quantity": "-3"}),
        ("CASH_TRANSFER out", {"asset_id": x, "type": "CASH_TRANSFER", "amount": "-300", "currency": "EUR", "description": "to a deleted broker", "tags": "cash,out"}, {"type": "CASH_TRANSFER", "amount": "300", "currency": "EUR"}),
        ("CASH_TRANSFER in", {"asset_id": x, "type": "CASH_TRANSFER", "amount": "250", "currency": "EUR", "description": "from a deleted broker", "tags": "cash,in"}, {"type": "CASH_TRANSFER", "amount": "-250", "currency": "EUR"}),
        ("FX_CONVERSION out", {"asset_id": x, "type": "FX_CONVERSION", "amount": "-100", "currency": "EUR", "description": "EUR sold"}, {"type": "FX_CONVERSION", "amount": "110", "currency": "USD"}),
        ("FX_CONVERSION in", {"asset_id": x, "type": "FX_CONVERSION", "amount": "110", "currency": "USD", "description": "USD bought"}, {"type": "FX_CONVERSION", "amount": "-100", "currency": "EUR"}),
        ("giving TRANSFER", {"asset_id": x, "type": "TRANSFER", "quantity": "-2", "description": "2 X to a deleted broker"}, {"asset_id": x, "type": "TRANSFER", "quantity": "2", "cost_basis_override": "20", "cost_basis_currency": "EUR"}),
        ("TRANSFER of unreadable quantity", {"asset_id": x, "type": "TRANSFER", "quantity": "n/a"}, {"asset_id": x, "type": "TRANSFER", "quantity": "1"}),
        ("CASH_TRANSFER of unreadable amount", {"type": "CASH_TRANSFER", "amount": "n/a", "currency": "EUR"}, {"type": "CASH_TRANSFER", "amount": "75", "currency": "EUR"}),
    ]


def _plant_book(conn: sqlite3.Connection) -> tuple[dict[str, int], int, int, int]:
    """Two kept brokers with whole pairs and rows of other types, and X: ``(ids by label, kept broker, X, an event of X)``."""
    kept, kept_too = _broker(conn, "Kept"), _broker(conn, "Kept too")
    x = conn.execute("INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES ('X', 'EUR', 'STOCK', 1, ?, ?)", (STAMP, STAMP)).lastrowid
    event = conn.execute("INSERT INTO asset_events (asset_id, date, type, value, currency, created_at, updated_at) VALUES (?, ?, 'PRICE_ADJUSTMENT', 1, 'EUR', ?, ?)", (x, DAY, STAMP, STAMP)).lastrowid
    ids = {
        "DEPOSIT": _insert(conn, broker_id=kept, type="DEPOSIT", amount="1000", currency="EUR"),
        "BUY": _insert(conn, broker_id=kept, asset_id=x, type="BUY", quantity="10", amount="-200", currency="EUR"),
        "ADJUSTMENT": _insert(conn, broker_id=kept_too, asset_id=x, type="ADJUSTMENT", quantity="2", cost_basis_override="15", cost_basis_currency="EUR"),
    }
    whole = {
        "TRANSFER": ({"broker_id": kept, "asset_id": x, "type": "TRANSFER", "quantity": "-1"}, {"broker_id": kept_too, "asset_id": x, "type": "TRANSFER", "quantity": "1", "cost_basis_override": "20", "cost_basis_currency": "EUR"}),
        "CASH_TRANSFER": ({"broker_id": kept, "type": "CASH_TRANSFER", "amount": "-50", "currency": "EUR"}, {"broker_id": kept_too, "type": "CASH_TRANSFER", "amount": "50", "currency": "EUR"}),
        "FX_CONVERSION": ({"broker_id": kept, "type": "FX_CONVERSION", "amount": "-20", "currency": "EUR"}, {"broker_id": kept, "type": "FX_CONVERSION", "amount": "22", "currency": "USD"}),
    }
    for kind, (out, into) in whole.items():
        ids[f"whole {kind} pair, out"], ids[f"whole {kind} pair, in"] = _pair(conn, out, into)
    return ids, kept, x, event


def _plant_orphans(db: Path) -> dict[str, int]:
    """The book, and every lone half twice: its partner on a broker deleted the 1.2 way, then on one deleted leaving the links. Ids by label."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        ids, kept, x, event = _plant_book(conn)
        gone = {how: _broker(conn, f"Deleted, {how}") for how in HOW}
        for how, gone_broker in gone.items():
            for kind, half, partner in _halves(x, event):
                ids[f"{kind}, {how}"], _ = _pair(conn, {"broker_id": kept, **half}, {"broker_id": gone_broker, **partner})
        _delete_broker_the_1_2_way(conn, gone["link NULL"])
        _delete_broker_leaving_the_links(conn, gone["dangling link"])
        conn.commit()
    dangling = sorted(tx_id for label, tx_id in ids.items() if label.endswith(", dangling link"))
    violations = _foreign_key_violations(db)
    assert sorted(rowid for _table, rowid, _parent, _key in violations) == dangling and {(table, parent) for table, rowid, parent, _key in violations} == {("transactions", "transactions")}, f"setup: the only broken links must be the dangling halves' {dangling}; found {violations}"
    return ids


def _plant_giving_legs_only(db: Path) -> dict[str, int]:
    """The book, and two giving TRANSFER legs whose receiving broker was deleted the 1.2 way: their links are NULL."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        ids, kept, x, _event = _plant_book(conn)
        receiver = _broker(conn, "Receiver, deleted")
        for n, quantity in enumerate(("2", "1"), start=1):
            ids[f"giving TRANSFER {n}"], _ = _pair(conn, {"broker_id": kept, "asset_id": x, "type": "TRANSFER", "quantity": f"-{quantity}"}, {"broker_id": receiver, "asset_id": x, "type": "TRANSFER", "quantity": quantity, "cost_basis_override": "20", "cost_basis_currency": "EUR"})
        _delete_broker_the_1_2_way(conn, receiver)
        conn.commit()
    assert _foreign_key_violations(db) == [], "setup: a 1.2 deletion leaves no broken link"
    return ids


def _plant_whole_pairs_only(db: Path) -> dict[str, int]:
    """The book alone: whole pairs, cross-broker and same-broker, and rows of other types."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        ids, _kept, _x, _event = _plant_book(conn)
        conn.commit()
    assert _foreign_key_violations(db) == [], "setup: every pair is whole"
    return ids


# Rows of types no pair has, linked all the same — "a link no split knows", as delete_by_broker calls it: (type,
# the row on the kept broker, the row its link names on another broker). Every column a conversion could touch is set.
OTHER_TYPES = ("ADJUSTMENT", "DEPOSIT")


def _linked_rows_of_other_types(x: int) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    return [
        ("ADJUSTMENT", {"asset_id": x, "type": "ADJUSTMENT", "quantity": "2", "cost_basis_override": "15", "cost_basis_currency": "EUR", "description": "2 X in", "tags": "adjustment,in"}, {"asset_id": x, "type": "ADJUSTMENT", "quantity": "-2"}),
        ("DEPOSIT", {"type": "DEPOSIT", "amount": "500", "currency": "EUR", "description": "cash in", "tags": "cash"}, {"type": "WITHDRAWAL", "amount": "-500", "currency": "EUR"}),
    ]


def _plant_other_types_linked(db: Path, *, partners: str, with_a_convertible_half: bool) -> dict[str, int]:
    """The book; an ADJUSTMENT and a DEPOSIT linked to rows of another broker, deleted leaving the links (``partners="deleted"``) or ``"still there"``; and, if asked, a received TRANSFER a 1.2 deletion left without its pair."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        ids, kept, x, _event = _plant_book(conn)
        other = _broker(conn, f"Other broker, rows {partners}")
        for kind, row, partner in _linked_rows_of_other_types(x):
            ids[f"{kind}, its partner {partners}"], partner_id = _pair(conn, {"broker_id": kept, **row}, {"broker_id": other, **partner})
            if partners == "still there":
                ids[f"the {kind}'s partner"] = partner_id
        if with_a_convertible_half:
            sender = _broker(conn, "Sender, deleted by 1.2")
            half = {"broker_id": kept, "asset_id": x, "type": "TRANSFER", "quantity": "4", "cost_basis_override": "20", "cost_basis_currency": "EUR"}
            ids["received TRANSFER with cost basis, link NULL"], _ = _pair(conn, half, {"broker_id": sender, "asset_id": x, "type": "TRANSFER", "quantity": "-4"})
            _delete_broker_the_1_2_way(conn, sender)
        if partners == "deleted":
            _delete_broker_leaving_the_links(conn, other)
        conn.commit()
    broken = sorted(ids[f"{kind}, its partner deleted"] for kind in OTHER_TYPES) if partners == "deleted" else []
    assert sorted(rowid for _table, rowid, _parent, _key in _foreign_key_violations(db)) == broken, f"setup: the only broken links must be {broken}"
    return ids


def _ids(run: Run, *labels: str) -> list[int]:
    return sorted(run.ids[label] for label in labels)


def _without_updated_at(row: dict[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in row.items() if name != "updated_at"}


def _not_moved_to_the_run(run: Run, before: str, after: str) -> Optional[str]:
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


def _param(label: str):
    return pytest.param(label, id=re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-"))


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
    """Every lone half planted (``_plant_orphans``), then one run. Read-only for the tests."""
    root = tmp_path_factory.mktemp("applied")
    with _configured_sandbox(root / "configured-lane"):
        db = _copy(head, root)
        return _observe(db, _plant_orphans(db))


@pytest.fixture(scope="module")
def previewed(head: Path, tmp_path_factory: pytest.TempPathFactory) -> Run:
    """As ``applied``, with ``dry_run=True``."""
    root = tmp_path_factory.mktemp("dry-run")
    with _configured_sandbox(root / "configured-lane"):
        db = _copy(head, root)
        return _observe(db, _plant_orphans(db), dry_run=True)


# =============================================================================
# THE FIX IN THE LIST
# =============================================================================


def test_the_fix_runs_right_after_autoincrement() -> None:
    """``orphan_pair_halves`` is registered second in ``FIXES``, after ``autoincrement``: fixes run in that order, and a new one is appended."""
    assert [fix.fix_id for fix in post_migration.FIXES][:2] == ["autoincrement", FIX]


# =============================================================================
# 1. WHOLE PAIRS NEED NOTHING
# =============================================================================


def test_a_database_whose_pairs_are_whole_needs_nothing(head: Path, tmp_path: Path) -> None:
    """Contract 1: whole pairs — TRANSFER and CASH_TRANSFER across two brokers, an FX_CONVERSION on one — and rows of other types: ``clean``, the file byte-identical, no backup."""
    db = _copy(head, tmp_path)
    ids = _plant_whole_pairs_only(db)

    run = _observe(db, ids)

    assert run.report.outcomes.get(FIX) == "clean"
    assert run.report.errors == []
    assert run.digest_after == run.digest_before
    assert run.tables_after == run.tables_before
    assert (run.report.backup_path, run.backups_after) == (None, [])


# =============================================================================
# 2. THE LONE HALVES BECOME STANDALONE ROWS
# =============================================================================


@pytest.mark.parametrize("label", [_param(label) for label in CONVERTED_LABELS])
def test_a_lone_half_becomes_the_standalone_row_a_split_leaves(applied: Run, label: str) -> None:
    """Contract 2: the half takes its standalone type and loses its link; an ADJUSTMENT keeps its asset, a WITHDRAWAL or a DEPOSIT loses it; every other column stays, ``updated_at`` moves to the run's time."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    kind, how = label.rsplit(", ", 1)
    from_type, to_type = CONVERSIONS[kind]
    before, after = applied.rows_before[applied.ids[label]], applied.rows_after[applied.ids[label]]
    assert (before["type"], before["asset_id"] is not None, before["related_transaction_id"] is not None) == (from_type, True, how == "dangling link"), "setup: the half as planted"

    expected = {**before, "type": to_type, "related_transaction_id": None, "asset_id": before["asset_id"] if to_type == "ADJUSTMENT" else None}

    assert _without_updated_at(after) == _without_updated_at(expected)
    problem = _not_moved_to_the_run(applied, before["updated_at"], after["updated_at"])
    assert problem is None, problem


@pytest.mark.parametrize(
    ("how", "cost_basis"),
    [pytest.param(how, cost_basis, id=f"{'with' if cost_basis else 'without'}-cost-basis-{how.replace(' ', '-')}") for how in HOW for cost_basis in (("20", "EUR"), None)],
)
def test_a_received_transfer_becomes_an_adjustment_in_with_its_cost_basis_or_without_one(applied: Run, how: str, cost_basis: Optional[tuple[str, str]]) -> None:
    """Contract 2, the TRANSFER halves spelled out: an ADJUSTMENT of the same quantity of X, with its cost basis of 20 EUR per unit, or with none — its sender is gone, nothing computes one."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    label = f"received TRANSFER {'with' if cost_basis else 'without'} cost basis, {how}"
    after = applied.rows_after[applied.ids[label]]
    x = applied.rows_before[applied.ids["BUY"]]["asset_id"]

    observed = (after["type"], after["asset_id"] == x, str(after["quantity"]), after["cost_basis_override"], after["cost_basis_currency"], after["related_transaction_id"])

    quantity = "4" if cost_basis else "3"
    assert observed == ("ADJUSTMENT", True, quantity, int(cost_basis[0]) if cost_basis else None, cost_basis[1] if cost_basis else None, None)


# =============================================================================
# 3. WHAT IS LEFT AS IT IS
# =============================================================================


@pytest.mark.parametrize("label", [_param(label) for label in UNTOUCHED])
def test_a_row_the_fix_may_not_convert_or_does_not_concern_is_left_untouched(applied: Run, label: str) -> None:
    """Contract 3: a giving TRANSFER leg or a row of unreadable sign whose link is already NULL, a half of a whole pair, a row of another type — every column as it was, ``updated_at`` included."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    tx_id = applied.ids[label]

    assert applied.rows_after[tx_id] == applied.rows_before[tx_id]


@pytest.mark.parametrize("label", [_param(label) for label in UNLINKED_ONLY])
def test_a_half_the_fix_may_not_convert_loses_only_its_dangling_link(applied: Run, label: str) -> None:
    """Contract 3: a giving TRANSFER leg, or a row whose quantity or amount is not a number, whose link names a deleted row: that link goes, ``updated_at`` moves, the type and every other column stay."""
    assert applied.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    before, after = applied.rows_before[applied.ids[label]], applied.rows_after[applied.ids[label]]
    assert (before["type"], before["related_transaction_id"] is not None) == (UNLINKED_ONLY[label], True), "setup: the half as planted, its link naming a deleted row"

    assert _without_updated_at(after) == _without_updated_at({**before, "related_transaction_id": None})
    problem = _not_moved_to_the_run(applied, before["updated_at"], after["updated_at"])
    assert problem is None, problem


# =============================================================================
# 4. THE RUN
# =============================================================================


def test_the_run_reports_applied_and_leaves_a_consistent_database(applied: Run) -> None:
    """Contract 4: ``applied`` with no error, no backup left, no broken foreign key, the same number of rows in every table, and only the lone halves changed."""
    changed = sorted(tx_id for tx_id, row in applied.rows_before.items() if applied.rows_after.get(tx_id) != row)

    assert (applied.report.outcomes.get(FIX), applied.report.integrity_ok, applied.report.errors) == ("applied", True, [])
    assert (applied.report.backup_path, applied.backups_after) == (None, [])
    assert _foreign_key_violations(applied.db) == []
    assert applied.counts_after == applied.counts_before
    assert changed == _ids(applied, *CONVERTED_LABELS, *UNLINKED_ONLY)


def test_a_second_run_finds_nothing_to_do_and_writes_nothing(head: Path, tmp_path: Path) -> None:
    """Contract 4: run again, the fix reports ``clean`` — the giving legs and the unreadable rows it left are still there, with nothing left to do — and writes nothing, no backup."""
    db = _copy(head, tmp_path)
    ids = _plant_orphans(db)
    first = post_migration.run_post_migration_fixes(db, None)
    assert first.outcomes.get(FIX) == "applied", "precondition: the first run must convert, or the second proves nothing"

    second = _observe(db, ids)

    assert second.report.outcomes.get(FIX) == "clean"
    assert second.digest_after == second.digest_before
    assert second.tables_after == second.tables_before
    assert (second.report.backup_path, second.backups_after) == (None, [])


# =============================================================================
# 5. THE DRY RUN AND THE DETECTION WARNING
# =============================================================================


def test_a_dry_run_reports_would_apply_and_writes_nothing(previewed: Run) -> None:
    """Contract 5: ``would_apply``, the database file byte-identical, every row as it was, no backup."""
    assert previewed.report.outcomes.get(FIX) == "would_apply"
    assert previewed.digest_after == previewed.digest_before
    assert previewed.tables_after == previewed.tables_before
    assert (previewed.report.backup_path, previewed.backups_after) == (None, [])


def test_the_detection_warning_lists_every_lone_half_by_what_it_becomes_or_why_it_stays(previewed: Run) -> None:
    """Contract 5: one warning, the dry run's preview — the ids by conversion, those left without cost basis, those only unlinked, the giving TRANSFER legs, the rows of unreadable sign."""
    conversions: dict[str, list[int]] = {}
    for kind, (from_type, to_type) in CONVERSIONS.items():
        conversions.setdefault(f"{from_type}->{to_type}", []).extend(previewed.ids[f"{kind}, {how}"] for how in HOW)
    expected = {
        "count": len(CONVERTED_LABELS) + 2 * 3,  # and, twice each, the giving TRANSFER leg and the two rows of unreadable sign
        "conversions": {key: sorted(ids) for key, ids in conversions.items()},
        "without_cost_basis": _ids(previewed, *(f"received TRANSFER without cost basis, {how}" for how in HOW)),
        "unlinked_only": _ids(previewed, *UNLINKED_ONLY),
        "left_giving_transfer_legs": _ids(previewed, *(f"giving TRANSFER, {how}" for how in HOW)),
        "left_unreadable_sign": _ids(previewed, *(f"{kind}, {how}" for kind in ("TRANSFER of unreadable quantity", "CASH_TRANSFER of unreadable amount") for how in HOW)),
    }

    warnings = previewed.warnings()

    assert len(warnings) == 1, f"one detection warning per run: {warnings}"
    warning = warnings[0]
    assert str(warning.get("event")).startswith(FOUND), warning.get("event")
    assert {name: warning.get(name) for name in expected} == expected


def test_a_dry_run_logs_no_line_per_row(previewed: Run) -> None:
    """Contract 6: a dry run changes nothing, so it logs no ``converted`` or ``unlinked`` line. Barrier: the same logger's warning was captured."""
    assert previewed.warnings(), NOT_CAPTURED

    assert previewed.row_lines() == []


@pytest.mark.parametrize("dry_run", [pytest.param(False, id="run"), pytest.param(True, id="dry-run")])
def test_with_only_giving_legs_left_the_warning_says_they_stay_and_nothing_is_done(head: Path, tmp_path: Path, dry_run: bool) -> None:
    """Contract 5: two giving TRANSFER legs whose receiving broker was deleted the 1.2 way, links already NULL: the warning is the "left as they are" one, listing them; ``clean``, nothing written."""
    db = _copy(head, tmp_path)
    ids = _plant_giving_legs_only(db)

    run = _observe(db, ids, dry_run=dry_run)

    warnings = run.warnings()
    assert len(warnings) == 1, f"one detection warning per run: {warnings}"
    observed = {name: warnings[0].get(name) for name in ("count", "conversions", "without_cost_basis", "unlinked_only", "left_giving_transfer_legs", "left_unreadable_sign")}
    assert str(warnings[0].get("event")).startswith(LEFT), warnings[0].get("event")
    assert observed == {"count": 2, "conversions": {}, "without_cost_basis": [], "unlinked_only": [], "left_giving_transfer_legs": _ids(run, "giving TRANSFER 1", "giving TRANSFER 2"), "left_unreadable_sign": []}
    assert run.report.outcomes.get(FIX) == "clean"
    assert run.digest_after == run.digest_before
    assert (run.report.backup_path, run.backups_after) == (None, [])


# =============================================================================
# 6. ONE LINE PER CHANGED ROW
# =============================================================================


def test_an_applied_run_logs_one_line_per_changed_row(applied: Run) -> None:
    """Contract 6: after the commit, one INFO line per row changed — ``converted`` with the type it took, ``unlinked`` with the type it kept — and whether it stays without cost basis; none for an untouched row."""
    assert applied.closing_events() == [APPLIED_EVENT], NOT_CAPTURED
    expected = [(CONVERTED, "info", applied.ids[f"{kind}, {how}"], from_type, to_type, kind == "received TRANSFER without cost basis") for kind, (from_type, to_type) in CONVERSIONS.items() for how in HOW]
    expected += [(UNLINKED, "info", applied.ids[label], kept_type, kept_type, False) for label, kept_type in UNLINKED_ONLY.items()]

    assert applied.row_lines() == sorted(expected)


# =============================================================================
# 7. A FAILED VERIFICATION
# =============================================================================


def test_a_failed_verification_leaves_the_database_as_it_was_and_keeps_the_backup(head: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 7: the fix's own check reports a problem — ``failed`` with it, the database as before, the backup kept beside it holding that database, no line per row."""
    db = _copy(head, tmp_path)
    ids = _plant_orphans(db)
    monkeypatch.setattr(OrphanPairHalfFix, "verify", lambda self, conn, anomaly, ctx: [PROVOKED])

    run = _observe(db, ids)

    assert (run.report.outcomes.get(FIX), run.report.errors) == ("failed", [f"{FIX}: {PROVOKED}"])
    assert run.tables_after == run.tables_before
    backup = run.report.backup_path
    assert backup is not None and backup.parent == db.parent and re.fullmatch(rf"{re.escape(db.name)}\.pre-{FIX}-\d{{8}}T\d{{6}}Z\.bak", backup.name), f"the backup kept beside the database, named after it, the fix and the UTC time: {backup}"
    assert run.backups_after == [backup.name]
    assert _tables(backup) == run.tables_before
    assert run.closing_events() == [FAILED_EVENT], NOT_CAPTURED
    assert run.warnings(), NOT_CAPTURED  # the fix's own logger reached the capture: its detection warning
    assert run.row_lines() == []


# =============================================================================
# 8. A LINK ON A ROW OF ANOTHER TYPE (red before the fix knew such rows, 15/10)
# =============================================================================


@pytest.mark.parametrize("with_a_convertible_half", [pytest.param(True, id="beside-a-convertible-half"), pytest.param(False, id="the-only-anomaly")])
def test_a_row_of_another_type_whose_link_names_a_deleted_row_only_loses_that_link(head: Path, tmp_path: Path, with_a_convertible_half: bool) -> None:
    """Contract 8 (RED): an ADJUSTMENT and a DEPOSIT whose link names a deleted row lose that link and nothing else — ``updated_at`` moves — listed under ``unlinked_only``, one ``unlinked`` line each; the run ``applied``, no broken foreign key, no backup.

    It is delete_by_broker's rule for a link no split knows. Today the fix sees only the three paired types:
    beside a half it converts, the run's foreign key check of the whole database finds the two links and
    fails — nothing converted, the backup kept, at every start; alone, they are ``clean`` and stay broken.
    """
    db = _copy(head, tmp_path)
    ids = _plant_other_types_linked(db, partners="deleted", with_a_convertible_half=with_a_convertible_half)
    labels = [f"{kind}, its partner deleted" for kind in OTHER_TYPES]

    run = _observe(db, ids)
    print(f"outcomes: {run.report.outcomes}, errors: {run.report.errors}, backups: {run.backups_after}, broken links after: {_foreign_key_violations(db)}")

    assert (run.report.outcomes.get(FIX), run.report.errors) == ("applied", [])
    assert (run.report.backup_path, run.backups_after, _foreign_key_violations(db)) == (None, [], [])
    for label in labels:
        before, after = run.rows_before[ids[label]], run.rows_after[ids[label]]
        assert _without_updated_at(after) == _without_updated_at({**before, "related_transaction_id": None}), label
        problem = _not_moved_to_the_run(run, before["updated_at"], after["updated_at"])
        assert problem is None, f"{label}: {problem}"
    if with_a_convertible_half:
        assert run.rows_after[ids["received TRANSFER with cost basis, link NULL"]]["type"] == "ADJUSTMENT", "the half beside them is converted in the same run"
    warnings = run.warnings()
    assert [warning.get("unlinked_only") for warning in warnings] == [_ids(run, *labels)]
    expected_lines = [(UNLINKED, "info", ids[label], kind, kind, False) for label, kind in zip(labels, OTHER_TYPES, strict=True)]
    if with_a_convertible_half:
        expected_lines.append((CONVERTED, "info", ids["received TRANSFER with cost basis, link NULL"], "TRANSFER", "ADJUSTMENT", False))
    assert run.row_lines() == sorted(expected_lines), "contract 6: one line per row changed"


def test_a_row_of_another_type_whose_link_names_an_existing_row_is_untouched(head: Path, tmp_path: Path) -> None:
    """Contract 8 (guard, green today and after): an ADJUSTMENT and a DEPOSIT linked to rows that exist — and those rows — keep every column, ``updated_at`` included, and are not listed, while the run converts the half beside them."""
    db = _copy(head, tmp_path)
    ids = _plant_other_types_linked(db, partners="still there", with_a_convertible_half=True)
    labels = [*(f"{kind}, its partner still there" for kind in OTHER_TYPES), *(f"the {kind}'s partner" for kind in OTHER_TYPES)]

    run = _observe(db, ids)

    assert run.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    assert {label: run.rows_after[ids[label]] for label in labels} == {label: run.rows_before[ids[label]] for label in labels}
    assert [warning.get("unlinked_only") for warning in run.warnings()] == [[]]


# =============================================================================
# 9. THE OFFLINE SCRIPT'S LOG (W-B23: RED until __main__ configures logging)
# =============================================================================


def _summary_says(completed: subprocess.CompletedProcess[str], outcome: str) -> bool:
    """Whether the script printed its summary line ``Fix orphan_pair_halves: <outcome>``, on a line of its own."""
    return re.search(rf"^Fix {FIX}: {outcome}\s*$", completed.stdout, re.MULTILINE) is not None


def _expected_conversions(ids: dict[str, int]) -> dict[str, list[int]]:
    """The detection warning's ``conversions`` for the lone halves of ``_plant_orphans``: ids by ``<type>-><type>``."""
    conversions: dict[str, list[int]] = {}
    for kind, (from_type, to_type) in CONVERSIONS.items():
        conversions.setdefault(f"{from_type}->{to_type}", []).extend(ids[f"{kind}, {how}"] for how in HOW)
    return {key: sorted(found) for key, found in conversions.items()}


def test_the_offline_script_prints_a_json_line_per_changed_row_and_the_closing_line(head: Path, tmp_path: Path) -> None:
    """Contract 9 (RED): a real run exits 0 and prints, among its summary lines, one JSON line per row it changed — ``converted`` or ``unlinked``, with its ``transaction_id`` — and the closing ``Post-migration fixes applied and verified`` with ``seconds``.

    Today ``__main__`` configures no logging: the INFO lines go nowhere, and a manual run says what it did
    only through its summary.
    """
    db = _copy(head, tmp_path)
    ids = _plant_orphans(db)

    completed = _run_script("--db", str(db), "--data-dir", str(tmp_path / "data"))
    lines = _json_lines(completed.stdout)

    assert completed.returncode == 0, _output(completed)
    assert _summary_says(completed, "applied"), _output(completed)
    expected_rows = [(CONVERTED, ids[label]) for label in CONVERTED_LABELS] + [(UNLINKED, ids[label]) for label in UNLINKED_ONLY]
    assert sorted((line.get("event"), line.get("transaction_id")) for line in lines if line.get("event") in (CONVERTED, UNLINKED)) == sorted(expected_rows), _output(completed)
    closing = [line.get("seconds") for line in lines if line.get("event") == APPLIED_EVENT]
    assert len(closing) == 1 and isinstance(closing[0], (int, float)) and closing[0] >= 0, f"one closing line, with seconds >= 0: {closing}\n{_output(completed)}"


def test_the_offline_dry_run_prints_the_detection_warning_as_a_json_line(head: Path, tmp_path: Path) -> None:
    """Contract 9 (RED): ``--dry-run`` exits 0, writes nothing and prints the detection warning as a JSON line — its ``conversions`` by id — and no line per row.

    Today that warning reaches stderr only, as plain text, through Python's last-resort handler.
    """
    db = _copy(head, tmp_path)
    ids = _plant_orphans(db)
    _settle(db)
    digest = _digest(db)

    completed = _run_script("--db", str(db), "--data-dir", str(tmp_path / "data"), "--dry-run")
    lines = _json_lines(completed.stdout)

    assert completed.returncode == 0, _output(completed)
    assert (_digest(db), _backups(db)) == (digest, []), f"a dry run writes nothing\n{_output(completed)}"
    assert _summary_says(completed, "would_apply"), _output(completed)
    assert [line.get("conversions") for line in lines if str(line.get("event", "")).startswith(FOUND)] == [_expected_conversions(ids)], _output(completed)
    assert [line for line in lines if line.get("event") in (CONVERTED, UNLINKED)] == [], _output(completed)

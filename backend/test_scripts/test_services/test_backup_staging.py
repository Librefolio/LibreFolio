"""
Instance backup, checking an archive for a restore on a copy (workstream B, lot B2a): ``staging.py``.

Under test, in ``backend/app/services/platform/instance_backup/``:

(a) ``paths``: a check works in ``.restore/stage/<32 lowercase hex>/`` (``data/`` and ``report.json``), one at a time
    under ``.restore/stage/.stage.lock``. ``stage_dir``, ``read_report``, ``remove_stage`` and ``stage_archive`` never
    build a path from anything else than a stage id. A stage never enters a backup.
(b) A backup at this LibreFolio's head: ``action == "same"``, no migration, no post-migration fix, rows unchanged. The
    copy holds the archive's database and files byte for byte (folders 0700, entries 0600) beside ``report.json``
    (0600), which ``read_report`` gives back equal to the report returned. The report says what the manifest says; it
    names the active administrators of the copy, sorted; it expires 24 hours after the check. ``remove_stage`` removes
    the copy; a stage that is a link, or a file, is unlinked and never followed.
(c) An older backup, at ``005_accounts_invites`` (pinned by name: the revision just before ``006_registration_mode``,
    whose data conversion is checked), upgraded for real once for the module: ``action == "upgrade"``, ``migrations``
    the revisions after the backup's up to the head, oldest first, each with the first line of its description, as the
    migration files themselves say (read here with ``ast``, not through Alembic); the copy is at the head and its data
    converted; tables before (the manifest's counts) and after (the copy's, those the upgrade created included).
    ``_revision_plan`` gives, for every revision of the history, the migrations after it.
(d) Without an active administrator: ``blockers == ["no_administrator"]``, not restorable, the report still written.
(e) Refusals: every ``StagingError`` code. After each, no stage left, the lock free, a message holding no path, the
    archive unchanged and the live data directory untouched; a refusal decided before writing never began to unpack.
(f) One check at a time: while the lock is held (by this test, or by a check in progress) a check raises
    ``StagingBusyError`` and creates nothing; a lock passed by the caller (lot B2b) stays held after a success, a
    refusal and an invalid stage id, for the caller to release once the check's end is recorded; without one, the check
    takes its own and releases it in every case.
(g) Links: ``.restore`` or ``.restore/stage`` a link (dangling too) or a file: ``BackupPathError`` naming it, nothing
    written through it; an existing stage, a folder or a link, is never written over. ``remove_stage`` removes nothing
    while ``.restore`` or ``.restore/stage`` is a link or a file.
(h) Progress: checking, unpacking (from 0 to the total, each entry's size at a time), upgrading (for an upgrade only:
    none of the migrations done, then all of them), verifying.
(i) The live data directory, its database open in WAL mode with rows still in its ``-wal``, its files, secrets, logs
    and backups: every path of it but ``.restore/`` keeps its mode, size and SHA-256 through every check of the module.
(j) The warnings: ``rows_changed`` with the post-migration fix that removed rows (``event_types``),
    ``foreign_key_violations`` for the backup's own broken references, ``foreign_key_violations_added`` for new ones.
(k) The ledger's control totals (lot B-13, as the contract's §7 decided them): the manifest records J's totals of the
    snapshot; the check reads them again on the copy, after its upgrade and its post-migration fixes, and compares.
    ``same`` for a ledger as recorded (at the head, after a real upgrade, after a fix that only reclassifies lone pair
    halves, and for totals written otherwise but equal: lines in another order, zero lines, trailing zeros);
    ``changed`` when only the manifest's totals were rewritten (the manifest is not in its own list of checksums:
    nothing else tells), when the upgrade or a fix moved an amount, each difference listed (the first 20, all counted)
    and the warning ``control_totals_changed``; ``absent`` for a manifest without them, with ``null``, a value of
    another type, an amount that is not plain text or what J's reading refuses; ``other_version`` for totals of another
    method; ``unreadable``, warned ``control_totals_unreadable``, when they cannot be read on the copy, and when J cannot
    read back what it wrote of the copy's ledger (B-29: a position of 1E+70, which J writes with 71 digits, past the 60
    it reads): the check ends with its report, never ``stage_failed``. Never a blocker:
    ``restorable`` and ``blockers`` as they would be without them. ``_report`` without a comparison says ``absent``,
    with one carries it; a ``report.json`` written before lot B-13 still reads, its totals ``absent``.
(l) The database's own schema objects (lot B-28): LibreFolio never creates a trigger, a view or a virtual table, so a
    backup whose database holds one — a trigger on an app table, a view whose recursive CTE never ends, an fts5 virtual
    table, a trigger whose SQL hides its kind behind a comment (``CREATE/**/TRIGGER``), or all four at once — is
    refused ``database_foreign_objects`` once unpacked, before anything else opens the copy (``describe_database``, as
    ``staging`` imports it, fails the test if it is reached). Nothing of the copy is left; one warning gives the count
    and the kinds, and no line of the log nor the message names an object or quotes its SQL. A schema SQLite refuses
    to read — a trigger whose row claims ``type = 'table'`` (revision 05:30 of the contract: «malformed database
    schema»), a row whose SQL does not parse — is ``database_damaged``, also before anything else opens the copy. This
    LibreFolio's own schema, the head made by alembic, holds only tables and indexes, which the refusal lets through.
    Every connection a check opens on its copy through ``staging``, ``snapshot``, the post-migration fixes (lot B-37)
    and ``totals`` turns ``trusted_schema`` off before any other statement; the first of them reads the schema, read
    only, and runs nothing of it. The upgrade's own process is read in ``test_dev_cli_db_path.py`` (its ``env.py``).
(m) Lot B-35, a cap on what an archive unpacks to (``stage_archive(..., max_unpacked=)``, bytes): the declared total
    (the manifest's sizes, which the zip's headers equal) at the cap or under it is checked as without one; above it,
    ``unpacked_too_large`` in the contract's words, once the entries are checked and before the free space is asked or a
    byte written — never unpacked, the progress never past ``checking``, nothing left. A secure archive is decrypted
    first, then refused the same way. ``None``: no limit, the check as before.
(n) Lot B-43, a function the reader lacks: B-28 lets tables and indexes through by their kind, without reading their
    expressions. An index's expression, a virtual generated column or a CHECK calling a function this LibreFolio does not
    have (``lf_b43_probe``, registered only while its database is built) ends the check with ``database_damaged`` once
    unpacked — never a raw ``sqlite3.OperationalError`` («unknown function») escaping it — the copy removed as for any
    refusal, the lock free, the archive only read, the live data directory untouched. The index and the column fail the
    copy's first description (its integrity check, read only); SQLite leaves a CHECK out of the schema of a read-only
    connection, so that description finds the database intact (the barrier: ``describe_database`` of that very database,
    and the check's own first description of its copy) and the first read-write step refuses it. One warning, with the
    error's class and ``sqlite_errorname``; the function's name, the archive's text, in no message and no line of the
    log. The guard: a CHECK calling ``abs``, built in and innocuous, is checked as usual.
    Part 1, the functions the server registers: since H-51 the server's connections register ``regexp`` (2 arguments)
    and ``floor`` (1), deterministic and never innocuous, with ``trusted_schema`` off, so a schema calling one in an
    index's expression or a generated column cannot be read there, and a restored instance fails every connection. The
    check's plain readers pass it (``regexp`` unknown to them and never computed in a virtual column without a declared
    type; ``floor`` built in): a generated column on ``regexp`` and an index on ``floor`` are refused ``database_damaged``
    where the copy's schema is first read, with the server's functions as stand-ins, before ``describe_database`` opens
    the copy; the same one warning, no line naming the function. The guard: this LibreFolio's own index on
    ``lower(email)`` reads with the stand-ins, and its backup checks as usual. A CHECK or a DEFAULT calling them is
    resolved only when used: lot B-45's, not pinned here.
(o) Lot B-49, text that is not UTF-8: SQLite keeps as TEXT whatever bytes it is handed and checks no encoding, and its
    integrity check passes them; once restored, every ``select`` of such a table fails in the server, its error quoting
    the bytes. A check reads every text value of its copy — every table but SQLite's own, those LibreFolio does not have
    too, by storage class (the text of a DATE column counts, a BLOB is no text) — on a connection of ``staging`` of its
    own, ``mode=ro``, ``trusted_schema`` off first, once the copy is found to be the database its manifest describes and
    before anything writes in it. An archive holding text that is not UTF-8 — in ``transactions.description``, in
    ``fx_rates.date``, in a table LibreFolio does not have (its names quoted, its column untyped), the three at once,
    one character whose two bytes are split over two rows, the first or the last row of a table whose rowids are as far
    apart as SQLite allows, a column generated VIRTUAL or STORED from a ``CAST`` of bytes (``PRAGMA table_info`` does
    not list it, ``table_xinfo`` does) — is refused ``database_damaged`` in the contract's words: the copy described
    once, never fixed nor upgraded (an older backup too, its progress never reaching ``upgrading``), nothing of it left,
    the lock free, the archive only read. One warning, whose payload is numbers only: how many tables hold such text; no
    line of the log holds the text, its bytes, the words of a decode error, a name of the archive or a path. A manifest
    that does not describe the database is still refused for that, first. The guards: valid UTF-8 beyond ASCII
    (characters of two to four bytes) in the same places, and the same bytes stored as a BLOB, are checked as usual,
    and the copy keeps them as they are.

Real databases: two, made once for the module by ``alembic upgrade`` in a process of their own (at the head, and at
``OLDER``), then copied for every data directory and given accounts by SQL. Two more ``alembic`` processes
are the product's: the upgrade of a copy that succeeds, and one that fails on the copy (an index already holds the name
of the table a pending migration creates, so its ``CREATE TABLE`` fails). Every other failure is simulated in this
process, for one test: ``staging.subprocess`` (an ``alembic`` that ends badly, times out or cannot start),
``staging._upgrade``, ``staging.run_post_migration_fixes``, ``staging.os`` (files that fail to write), ``staging.shutil``
(a disk with little room), ``staging.ALEMBIC_INI``,
``staging.MAX_ENTRIES`` and ``ledger_totals_of`` (as ``staging`` and ``totals`` name it). ``instance_backup.totals`` is
imported by the tests that need it, never at collection: until lot B-13 writes it, each of them fails on its own.
(l) replaces ``describe_database`` as ``staging`` imports it with a function that fails the test, and wraps ``connect``
where ``staging``, ``snapshot`` and ``post_migration`` look up ``sqlite3`` and ``totals`` looks up ``aiosqlite``, to
record the statements of each connection from its very first (a trace set as the connection is made); the fixes'
backup copy, a new file beside the copy, is no connection to it. Two of its archives are a real backup
whose database was then edited through ``writable_schema``: SQLite refuses their schema, so no backup is made of them.
``staging._refuse_foreign_objects`` is looked up by the test that needs it, never at collection. (m) replaces
``staging._unpack`` with a function that fails the test, and ``staging._check_space`` with a disk without room; each
of its cases asks ``stage_archive`` for ``max_unpacked`` first, so that until lot B-35 each fails on its own. (n) wraps
``describe_database`` as ``staging`` imports it, the real one, to keep what each description answered. Its archives are
a real backup at the head whose database then got, on the one connection where the function it calls is registered
(``lf_b43_probe``, ``regexp``; ``floor`` and ``abs`` are built in), an object calling it, and was put back in its place,
the manifest listing its new bytes and its tables: the snapshot's ``VACUUM INTO`` fails on a function its connection
lacks, so only a hand puts such a database in an archive (``floor``'s index takes the same road). Every reader the
product opens today lacks ``lf_b43_probe`` and ``regexp``; the server's connections are played by a read-only reader
that registers ``regexp`` and ``floor`` as stand-ins, deterministic and never run, ``trusted_schema`` off
(``server_schema_error``). (o) replaces ``run_post_migration_fixes`` as ``staging`` imports it, the first step that
writes in the copy, with a function that fails the test, and wraps ``describe_database`` as (n) does. Its archives are
real backups whose database got its text by SQL (a ``CAST`` of bytes, stored, or the expression of a generated column)
before the backup: the snapshot copies the bytes as they are, and nothing of the build reads them. Its check of a table
whose rowids are far apart runs in a thread, joined with a deadline: a scan that never ends fails the test instead of
holding it.

Pure: every data directory, database and archive lives in ``tmp_path``. This process and every process it starts are
configured with a production data directory of the test (``LIBREFOLIO_TEST_*`` removed, ``LIBREFOLIO_DATA_DIR`` set and
checked) that must stay absent: a check writing in the configured data directory instead of the one it is given fails
the test, and the lane's is never reached. ``LF_APP_VERSION`` is set, so no git process runs. No lane database, no
server, no network. Every wait is an ``Event`` or a ``join`` with a deadline. Modes, links and the lock are POSIX-only.
"""

from __future__ import annotations

import ast
import errno
import hashlib
import importlib
import inspect
import json
import os
import re
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import threading
import unicodedata
import warnings
import zipfile
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from structlog.testing import capture_logs

from backend.app.config import get_data_dir
from backend.app.db import post_migration
from backend.app.db.post_migration.base import PostMigrationReport
from backend.app.services.financial_math.ledger_totals import CONTROL_TOTALS_VERSION, ControlTotals, control_totals
from backend.app.services.platform.instance_backup import envelope, snapshot, staging
from backend.app.services.platform.instance_backup.archive import BuiltArchive, build_archive
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.services.platform.instance_backup.manifest import MANIFEST_MAX_BYTES, BackupManifest, ManifestDatabase, ManifestFile
from backend.app.services.platform.instance_backup.paths import (
    DATABASE_ENTRY,
    MANIFEST_ENTRY,
    RESTORE_FOLDER,
    STAGE_DATA_FOLDER,
    STAGE_FOLDER,
    STAGE_LOCK_FILE,
    STAGE_REPORT_FILE,
    BackupPathError,
    ensure_private_dir,
    restore_dir,
    stage_dir,
    stages_dir,
)
from backend.app.services.platform.instance_backup.snapshot import DatabaseDescription, file_digest
from backend.app.services.platform.instance_backup.staging import (
    ALEMBIC_INI,
    MAX_ENTRIES,
    STAGE_LIFETIME,
    UPGRADE_TIMEOUT_SECONDS,
    AppliedMigration,
    StagingBusyError,
    StagingError,
    StagingReport,
    TableRows,
    _report,
    _revision_plan,
    new_stage_id,
    read_report,
    remove_stage,
    space_needed,
    stage_archive,
)
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VERSIONS = PROJECT_ROOT / "backend" / "alembic" / "versions"
#: What every manifest and report of this module must say made it: set as LF_APP_VERSION, so no ``git describe`` runs.
APP_VERSION = "v0.0.0-b2a-staging-test"
#: Seconds an ``alembic upgrade`` made by this module may last: it imports the application first, on a loaded machine.
ALEMBIC_TIMEOUT_S = 600
#: Seconds. Every wait of this module ends by then; none of them decides anything by itself.
DEADLINE_S = 60
#: Characters of a child's output quoted by an assertion message.
TAIL = 3000
ZIP_DATE = (2026, 10, 15, 10, 15, 0)
#: When every row of this module was created, as SQLite stores a DATETIME.
CREATED = "2026-10-15 10:15:00.000000"
#: A revision no LibreFolio has: what the database of a newer LibreFolio records.
NEWER_REVISION = "999_from_a_newer_librefolio"
VALID_ID = "0123456789abcdef0123456789abcdef"
#: The phases of a check, in their order; ``upgrading`` only for an older backup.
PHASES = ["checking", "unpacking", "upgrading", "verifying"]
#: What SQLite and the post-migration fixes may leave beside the copy's database (the fixes' lock always).
SQLITE_SIDE_FILES = ("-wal", "-shm", "-journal", ".post-migration.lock")
SECRET = b"instance-key-never-in-a-stage-5c2e9a"


def migration_chain() -> list[AppliedMigration]:
    """This LibreFolio's migrations, oldest first, as their files say: revision, parent and first line of description.

    Read with ``ast`` from ``backend/alembic/versions``, independently of Alembic's walk, which the product uses: the two
    must agree.
    """
    children: dict[str | None, tuple[str, str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.AnnAssign):
                target, value = node.target, node.value
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            else:
                continue
            if isinstance(target, ast.Name) and target.id in ("revision", "down_revision") and value is not None:
                names[target.id] = ast.literal_eval(value)
        first = next((line.strip() for line in (ast.get_docstring(tree) or "").splitlines() if line.strip()), "")
        assert "revision" in names and "down_revision" in names and first, f"precondition: {path.name} declares revision, down_revision and a description"
        assert names["down_revision"] not in children, f"precondition: one migration per parent, {path.name} makes a branch"
        children[names["down_revision"]] = (str(names["revision"]), first)
    chain: list[AppliedMigration] = []
    parent: str | None = None
    while parent in children:
        revision, message = children.pop(parent)
        chain.append(AppliedMigration(revision=revision, message=message))
        parent = revision
    assert not children and len(chain) >= 2, f"precondition: the migrations make one chain from the base, of two at least; left over: {children}"
    return chain


CHAIN = migration_chain()
HEAD = CHAIN[-1].revision


def position(revision: str) -> int:
    """Where ``revision`` stands in ``CHAIN``. A revision this module pins that is gone fails at import, loudly."""
    revisions = [migration.revision for migration in CHAIN]
    if revision not in revisions:
        raise AssertionError(f"the revision {revision!r} this module pins is not among this LibreFolio's migrations: {revisions}")
    return revisions.index(revision)


#: The migration whose data conversion the real upgrade of an older backup is checked by (``enable_registration``
#: becomes ``registration_mode``), and the revision just before it, which every older backup of this module is at. Both
#: pinned by name: a new migration moves the head, never them.
CONVERSION = "006_registration_mode"
OLDER = "005_accounts_invites"
if position(CONVERSION) != position(OLDER) + 1:
    raise AssertionError(f"{OLDER} must be the revision just before {CONVERSION}")
#: What the upgrade of an older backup applies: every migration after ``OLDER`` up to the head, oldest first.
AFTER_OLDER = CHAIN[position(OLDER) + 1 :]

#: The accounts of the backups of this module, in the order they are inserted: (username, is_active, is_superuser).
ACCOUNTS = (("zoe_admin", 1, 1), ("bob_user", 1, 0), ("olga_former_admin", 0, 1), ("ada_admin", 1, 1))
#: The active administrators among them, in order: what a report names.
ADMINISTRATORS = ["ada_admin", "zoe_admin"]
#: Accounts without an active administrator: a user, and an administrator whose account is disabled.
WITHOUT_ADMINISTRATOR = (("bob_user", 1, 0), ("olga_former_admin", 0, 1))
INSERT_ACCOUNT = "INSERT INTO users (username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"

LOGO = "custom-uploads/logo.png"
#: The files of the backups of this module, besides the database.
FILES = {
    LOGO: bytes(range(256)) * 16,
    "custom-uploads/avatars/user-1.webp": b"RIFF\x24\x00\x00\x00WEBPVP8 " + bytes(64),
    "custom-uploads/résumé.pdf": b"%PDF-1.7 a file whose name has accents\n",
    "custom-uploads/empty.txt": b"",
    # 2.5 MiB and a bit: several chunks of the copy, the last one partial.
    "custom-uploads/big.bin": bytes(range(256)) * (10 * 1024 + 7),
    "broker_reports/uploaded/2026-10.csv": b"date,amount\n2026-10-01,10.00\n",
    "broker_reports/failed/broken.csv": b"\xff\xfe a report that is not UTF-8 is still a file\n",
    "scenario_catalog/user-scenarios.json": b'{"scenarios": []}\n',
}
#: The files of the live data directory a check runs in, besides its database: none of them may change.
LIVE_FILES = {
    LOGO: b"the live instance's own logo\n",
    "broker_reports/uploaded/2026-11.csv": b"date,amount\n2026-11-01,30.00\n",
    "secrets/instance.key": SECRET + b"\n",
    "backups/librefolio-backup-20261014-090000.zip": b"PK an older backup of the live instance",
    "logs/librefolio.log": b'{"event": "a log line"}\n',
}

#: The brokers and assets the ledger's rows refer to: (id, name) and (id, name, currency, asset type).
LEDGER_BROKERS = ((1, "Broker Alpha"), (2, "Broker Beta"), (3, "Broker Gamma"))
LEDGER_ASSETS = ((1, "Asset One", "EUR", "STOCK"), (2, "Asset Two", "USD", "ETF"), (3, "Asset Three", "CHF", "BOND"))
#: A ledger as the app keeps it: (broker id, asset id, type, date, quantity, amount, currency), the numbers as SQL text
#: (the columns' NUMERIC affinity stores them as it stores the app's). Cash in several currencies and positions in
#: several brokers, negatives, the smallest amount and quantity, a row of nothing, a position without cash and lines
#: whose rows cancel out: broker 3 is left with none. No TRANSFER, CASH_TRANSFER or FX_CONVERSION: alone, such a row
#: is a lone pair half, which a post-migration fix converts (one test does it on purpose).
LEDGER = (
    (1, None, "DEPOSIT", "2026-01-02", "0", "10000", "EUR"),
    (1, 1, "BUY", "2026-01-05", "10", "-1500.5", "EUR"),
    (1, 1, "SELL", "2026-02-01", "-4", "700.25", "EUR"),
    (1, 1, "DIVIDEND", "2026-03-01", "0", "12.34", "EUR"),
    (1, None, "FEE", "2026-03-02", "0", "-2.5", "EUR"),
    (1, None, "DEPOSIT", "2026-01-02", "0", "500", "USD"),
    (1, 2, "BUY", "2026-01-06", "0.000001", "-0.01", "USD"),
    (1, 3, "ADJUSTMENT", "2026-04-01", "5", "0", None),
    (2, None, "DEPOSIT", "2026-01-03", "0", "100", "EUR"),
    (2, None, "WITHDRAWAL", "2026-05-03", "0", "-100", "EUR"),
    (2, 1, "ADJUSTMENT", "2026-01-10", "3", "0", None),
    (2, 1, "ADJUSTMENT", "2026-01-11", "-3", "0", None),
    (2, None, "INTEREST", "2026-06-30", "0", "0.000001", "CHF"),
    (2, None, "TAX", "2026-06-30", "0", "-7", "GBP"),
    (2, 2, "ADJUSTMENT", "2026-07-01", "0", "0", "USD"),
    (3, None, "DEPOSIT", "2026-01-04", "0", "50", "JPY"),
    (3, None, "WITHDRAWAL", "2026-01-05", "0", "-50", "JPY"),
)
INSERT_BROKER = "INSERT INTO brokers (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)"
INSERT_ASSET = "INSERT INTO assets (id, display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)"
INSERT_TRANSACTION = "INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
#: The module of the ledger's control totals in a backup (lot B-13), and the fields it adds to a check's report.
TOTALS_MODULE = "backend.app.services.platform.instance_backup.totals"
TOTALS_FIELDS = ("control_totals", "control_totals_differences", "control_totals_differences_count")


# =============================================================================
# Helpers
# =============================================================================


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def nfc(name: str) -> str:
    """A name as NFC: a file system may give a name back in the other normalisation (HFS+)."""
    return unicodedata.normalize("NFC", name)


def write_files(root: Path, files: dict[str, bytes]) -> None:
    for entry, content in files.items():
        path = root / entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def listing(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) if root.exists() else []


def side_files(database: Path) -> list[str]:
    return [suffix for suffix in ("-wal", "-shm", "-journal") if database.with_name(database.name + suffix).exists()]


def read_only(database: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)


def rows_of(database: Path, sql: str) -> list[tuple]:
    with closing(read_only(database)) as conn:
        return conn.execute(sql).fetchall()


def revisions_of(database: Path) -> list[str]:
    """What ``alembic_version`` records, every row of it."""
    return [row[0] for row in rows_of(database, "SELECT version_num FROM alembic_version")]


def execute(database: Path, *statements: str) -> None:
    """Run SQL on a database and commit; foreign keys off, as SQLite has them by default."""
    with closing(sqlite3.connect(database)) as conn, conn:
        for statement in statements:
            conn.execute(statement)


def account(username: str, is_active: int, is_superuser: int) -> tuple:
    return (username, f"{username}@example.test", "$argon2id$v=19$not-a-real-hash", is_active, is_superuser, CREATED, CREATED)


def add_accounts(database: Path, accounts) -> None:
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.executemany(INSERT_ACCOUNT, [account(*entry) for entry in accounts])


def break_not_null(database: Path, rows: int) -> None:
    """Rows that break a NOT NULL constraint the schema now declares: the integrity check reports them."""
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("CREATE TABLE notes (body TEXT)")
        with conn:
            conn.executemany("INSERT INTO notes (body) VALUES (NULL)", [()] * rows)
        conn.execute("PRAGMA writable_schema = ON")
        with conn:
            conn.execute("UPDATE sqlite_schema SET sql = 'CREATE TABLE notes (body TEXT NOT NULL)' WHERE name = 'notes'")


def stamp_head(database: Path) -> None:
    """What an upgrade leaves in ``alembic_version``: the head. The simulated upgrades only stamp it: none of the cases
    that use them needs the schema of the head."""
    execute(database, f"UPDATE alembic_version SET version_num = '{HEAD}'")


def fingerprint(root: Path) -> dict[str, tuple]:
    """Every path below ``root`` but the restore's own folder: a folder with its mode, a link with its target, a file
    with its mode, size and SHA-256."""
    found: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == RESTORE_FOLDER:
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            found[relative.as_posix()] = ("link", os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            found[relative.as_posix()] = ("folder", stat.S_IMODE(info.st_mode))
        else:
            found[relative.as_posix()] = ("file", stat.S_IMODE(info.st_mode), info.st_size, sha256(path.read_bytes()))
    return found


def changed(before: dict, after: dict) -> list[str]:
    return sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))


def leftover_stages(root: Path) -> list[str]:
    """What ``.restore/stage/`` holds but its lock: the stages a check left."""
    folder = stages_dir(root)
    return sorted(path.name for path in folder.iterdir() if path.name != STAGE_LOCK_FILE) if folder.is_dir() else []


def lock_is_free(root: Path) -> bool:
    """Whether a check could take the lock now (a probe: taken and released at once when free)."""
    if not stages_dir(root).is_dir():
        return True
    probe = _RunLock(stages_dir(root) / STAGE_LOCK_FILE)
    if not probe.try_acquire():
        return False
    probe.release()
    return True


def holds_no_path(message: str, archive: Path, root: Path) -> None:
    """The message of a refusal names neither the archive nor the data directory, nor any folder of the tests."""
    for form in {str(archive), str(archive.resolve()), archive.name, str(root), str(root.resolve())}:
        assert form not in message, f"the message of a refusal holds no path, yet it says {form!r}: {message!r}"
    assert f"{os.sep}pytest-of-" not in message, f"the message of a refusal holds no path: {message!r}"


class Progress:
    """A ``progress`` callback that keeps every call, (phase, done, total), in ``events``.

    Not a list: an empty list is false, and ``stage_archive`` takes ``progress or _no_progress``."""

    def __init__(self) -> None:
        self.events: list[tuple[str, int, int]] = []

    def __call__(self, phase: str, done: int, total: int) -> None:
        self.events.append((phase, done, total))

    @property
    def phases(self) -> list[str]:
        """The phases, in the order they began."""
        phases: list[str] = []
        for phase, _done, _total in self.events:
            if not phases or phases[-1] != phase:
                phases.append(phase)
        return phases


def configure(patch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """Make ``data_dir`` the production data directory this process and the processes it starts are configured with,
    and ``APP_VERSION`` the version of every manifest and report, without a git process. Checked before returning."""
    patch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    patch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)
    patch.setenv("LIBREFOLIO_DATA_DIR", str(data_dir))
    patch.setenv("LF_APP_VERSION", APP_VERSION)
    get_git_version.cache_clear()
    assert get_data_dir() == data_dir.resolve(), f"precondition: the configured data directory must be the test's, not {get_data_dir()}"
    return data_dir


@pytest.fixture(autouse=True)
def configured_data_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    """The data directory configured for this process and its children: a folder of the test that must stay absent. A
    check works in the data directory it is given; one that wrote in the configured one would create it.

    ``get_git_version`` keeps the first version it computes for the life of the process: its cache is emptied before the
    test and after it, so ``APP_VERSION`` is the version read here and never reaches the tests that follow."""
    configured = configure(monkeypatch, tmp_path / "configured-data-dir")
    yield configured
    get_git_version.cache_clear()
    assert not configured.exists(), f"something was written in the configured data directory instead of the one given: {listing(configured)}"


def child_env(data_dir: Path) -> dict[str, str]:
    """This process's environment without what could point a child at another data directory (or start coverage in
    it), plus ``data_dir`` as its production data directory."""
    env = {name: value for name, value in os.environ.items() if not name.startswith(("LIBREFOLIO_", "COVERAGE_"))}
    env.update(LIBREFOLIO_DATA_DIR=str(data_dir), LF_APP_VERSION=APP_VERSION, PYTHONUNBUFFERED="1", PYTHONUTF8="1")
    return env


def alembic_upgrade(database: Path, revision: str, env: dict[str, str]) -> None:
    """``alembic upgrade <revision>`` of a new database, in a process of its own, as the product upgrades a copy."""
    command = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "-x", f"sqlalchemy.url=sqlite:///{database}", "upgrade", revision]
    try:
        done = subprocess.run(command, cwd=PROJECT_ROOT, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=ALEMBIC_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"precondition: alembic upgrade {revision} did not end within {ALEMBIC_TIMEOUT_S}s: {exc.stderr!r}")
    assert done.returncode == 0, f"precondition: alembic upgrade {revision} of a new database exited {done.returncode}\n--- stdout\n{done.stdout[-TAIL:]}\n--- stderr\n{done.stderr[-TAIL:]}"


def make_data_dir(root: Path, database: Path, *, accounts=ACCOUNTS) -> Path:
    """A data directory: a copy of ``database`` with ``accounts``, and ``FILES``."""
    (root / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(database, root / DATABASE_ENTRY)
    add_accounts(root / DATABASE_ENTRY, accounts)
    write_files(root, FILES)
    return root


def build_into(data: Path, work: Path, name: str = "librefolio-backup-test.zip") -> BuiltArchive:
    work.mkdir(parents=True, exist_ok=True)
    return build_archive(data, work, work / name, origin="cli")


@dataclass(frozen=True)
class Databases:
    """Two real databases made by ``alembic upgrade``: at this LibreFolio's head, and at ``OLDER``."""

    head: Path
    older: Path


@pytest.fixture(scope="module")
def databases(tmp_path_factory) -> Databases:
    root = tmp_path_factory.mktemp("migrated")
    configured = root / "configured-data-dir"
    env = child_env(configured)
    made = Databases(head=root / "head.db", older=root / "older.db")
    for database, revision, expected in ((made.head, "head", HEAD), (made.older, OLDER, OLDER)):
        alembic_upgrade(database, revision, env)
        # Copied for every data directory of the module: one file, in rollback-journal mode, nothing beside it.
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
        assert revisions_of(database) == [expected], f"precondition: alembic upgrade {revision} gives a database at {expected}: {revisions_of(database)}"
        assert side_files(database) == [], f"precondition: nothing beside {database.name}: {side_files(database)}"
    assert not configured.exists(), f"alembic wrote in the configured data directory: {listing(configured)}"
    return made


def archive_of(databases: Databases, root: Path, database: Path) -> BuiltArchive:
    """The archive of a data directory made from ``database``, under the module's configuration."""
    with pytest.MonkeyPatch.context() as patch:
        configure(patch, root / "configured-data-dir")
        built = build_into(make_data_dir(root / "data", database), root / "work")
        get_git_version.cache_clear()
    return built


@pytest.fixture(scope="module")
def head_archive(databases, tmp_path_factory) -> BuiltArchive:
    """The backup most cases start from, built once: a data directory at the head with ``ACCOUNTS`` and ``FILES``. Every
    case reads it; none changes it (the cases that need another archive write their own)."""
    built = archive_of(databases, tmp_path_factory.mktemp("head-archive"), databases.head)
    assert (built.manifest.alembic_revision, built.warnings) == (HEAD, ()), f"precondition: a clean archive at the head: {built.manifest.alembic_revision}, {built.warnings}"
    return built


@pytest.fixture(scope="module")
def older_archive(databases, tmp_path_factory) -> BuiltArchive:
    """The same backup, at ``OLDER``: what the simulated upgrades start from."""
    built = archive_of(databases, tmp_path_factory.mktemp("older-archive"), databases.older)
    assert (built.manifest.alembic_revision, built.warnings) == (OLDER, ()), f"precondition: a clean archive at {OLDER}: {built.manifest.alembic_revision}, {built.warnings}"
    return built


@dataclass
class Instance:
    """The data directory a check runs in, as a running server leaves it: its database open in WAL mode with rows still
    in its ``-wal``, its own files, secrets, logs and backups. ``before``: its fingerprint when the test starts."""

    root: Path
    connection: sqlite3.Connection
    before: dict[str, tuple]


def open_instance(root: Path, database: Path) -> Instance:
    (root / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(database, root / DATABASE_ENTRY)
    write_files(root, LIVE_FILES)
    connection = sqlite3.connect(root / DATABASE_ENTRY, isolation_level=None)
    assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal", "precondition: the live database runs in WAL mode"
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute(INSERT_ACCOUNT, account("live_admin", 1, 1))
    assert "-wal" in side_files(root / DATABASE_ENTRY), "precondition: the live database has rows still in its -wal"
    return Instance(root=root, connection=connection, before=fingerprint(root))


@pytest.fixture
def instance(tmp_path, databases) -> Iterator[Instance]:
    """(i) The live data directory of the test. At its end every path of it but ``.restore/`` is as it was."""
    live = open_instance(tmp_path / "instance", databases.head)
    try:
        yield live
        after = fingerprint(live.root)
        assert after == live.before, f"the live data directory changed: {changed(live.before, after)}"
    finally:
        live.connection.close()


@dataclass(frozen=True)
class Upgraded:
    """An older backup checked once for the module, through a real ``alembic upgrade`` of its copy."""

    archive: BuiltArchive
    archive_sha256: str
    instance: Path
    before: dict[str, tuple]
    after: dict[str, tuple]
    configured: Path
    progress: Progress
    report: StagingReport


@pytest.fixture(scope="module")
def upgraded(databases, tmp_path_factory) -> Upgraded:
    root = tmp_path_factory.mktemp("upgraded")
    with pytest.MonkeyPatch.context() as patch:
        configured = configure(patch, root / "configured-data-dir")
        data = make_data_dir(root / "data", databases.older)
        # What CONVERSION converts: an instance open to sign-ups stays open after it.
        execute(data / DATABASE_ENTRY, f"INSERT INTO global_settings (key, value, value_type, description, updated_at) VALUES ('enable_registration', 'true', 'bool', 'Allow new user registration', '{CREATED}')")
        built = build_into(data, root / "work")
        archive_sha256 = sha256(built.path.read_bytes())
        live = open_instance(root / "instance", databases.head)
        progress = Progress()
        try:
            report = stage_archive(built.path, live.root, progress=progress)
            after = fingerprint(live.root)
        finally:
            live.connection.close()
            get_git_version.cache_clear()
    return Upgraded(archive=built, archive_sha256=archive_sha256, instance=live.root, before=live.before, after=after, configured=configured, progress=progress, report=report)


# -----------------------------------------------------------------------------
# Crafted archives
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One entry of a crafted archive: its name and bytes, and how the zip stores it."""

    name: str
    data: bytes
    mode: int = stat.S_IFREG | 0o600
    compress_type: int = zipfile.ZIP_DEFLATED
    encrypted: bool = False


def entries_of(archive: BuiltArchive) -> list[Entry]:
    """The entries of a built archive but its manifest, in their order, as plain deflated files."""
    with zipfile.ZipFile(archive.path) as zf:
        return [Entry(info.filename, zf.read(info)) for info in zf.infolist() if info.filename != MANIFEST_ENTRY]


def with_logo(archive: BuiltArchive, **changes) -> list[Entry]:
    """The entries of ``archive``, the logo's changed."""
    return [replace(entry, **changes) if entry.name == LOGO else entry for entry in entries_of(archive)]


def listed(name: str, data: bytes) -> ManifestFile:
    return ManifestFile(path=name, size=len(data), sha256=sha256(data))


def listing_also(archive: BuiltArchive, *entries: Entry):
    """The manifest of ``archive``, listing ``entries`` too, each with its real size and SHA-256."""
    return archive.manifest.model_copy(update={"files": [*archive.manifest.files, *(listed(entry.name, entry.data) for entry in entries)]})


def manifest_document(archive: BuiltArchive, **changes) -> bytes:
    """The manifest of ``archive`` as JSON, its top-level fields changed: what no ``BackupManifest`` would let be built."""
    return json.dumps(archive.manifest.model_dump(mode="json") | changes).encode("utf-8")


def pack(target: Path, entries: list[Entry], manifest, *, manifest_twice: bool = False) -> Path:
    """A zip of ``entries``, then ``manifest`` (a ``BackupManifest``, raw bytes, or ``None`` for none) as the last entry,
    once or twice. The manifest is stored, not deflated."""
    with zipfile.ZipFile(target, "w") as zf, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # zipfile warns about a name written twice, on purpose here
        for entry in entries:
            info = zipfile.ZipInfo(entry.name, date_time=ZIP_DATE)
            info.compress_type = entry.compress_type
            info.external_attr = entry.mode << 16
            zf.writestr(info, entry.data)
            if entry.encrypted:
                # The central directory says so; the bytes are not encrypted: a check must refuse it without reading them.
                info.flag_bits |= 0x1
        if manifest is not None:
            raw = manifest if isinstance(manifest, bytes) else manifest.to_bytes()
            for _ in range(2 if manifest_twice else 1):
                zf.writestr(zipfile.ZipInfo(MANIFEST_ENTRY, date_time=ZIP_DATE), raw)
    return target


def flip(path: Path, entry: str) -> Path:
    """Invert one byte in the middle of the stored data of ``entry``: the zip stays intact, as after bit rot."""
    raw = bytearray(path.read_bytes())
    with zipfile.ZipFile(path) as zf:
        info = zf.getinfo(entry)
    signature, *_, name_length, extra_length = struct.unpack("<4s2B4HL2L2H", raw[info.header_offset : info.header_offset + 30])
    assert signature == b"PK\x03\x04", "precondition: the local header of the entry is where the central directory says"
    raw[info.header_offset + 30 + name_length + extra_length + info.compress_size // 2] ^= 0xFF
    path.write_bytes(bytes(raw))
    return path


def refused(archive: Path, instance: Instance, **kwargs) -> tuple[StagingError, Progress]:
    """Check ``archive`` expecting a refusal; returned once checked: nothing of the copy left, the lock free, no path said."""
    progress = Progress()
    with pytest.raises(StagingError) as raised:
        stage_archive(archive, instance.root, progress=progress, **kwargs)
    error = raised.value
    assert leftover_stages(instance.root) == [], f"({error.code}) a refused archive leaves nothing of its copy: {leftover_stages(instance.root)}"
    assert lock_is_free(instance.root), f"({error.code}) the lock is released after a refusal"
    holds_no_path(str(error), archive, instance.root)
    return error, progress


def never_upgrade(database: Path) -> None:
    raise AssertionError("this archive must be refused before its copy is upgraded: _upgrade ran")


# -----------------------------------------------------------------------------
# The ledger and its control totals (lot B-13)
# -----------------------------------------------------------------------------


def totals_module() -> ModuleType:
    """``instance_backup.totals`` (lot B-13). Imported when a test needs it, never at collection: until it exists, each
    test that needs it fails on its own, with this message."""
    try:
        return importlib.import_module(TOTALS_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != TOTALS_MODULE:
            raise
        pytest.fail(f"{TOTALS_MODULE} does not exist: lot B-13 is not written yet ({exc})")


def add_ledger(database: Path, rows=LEDGER) -> None:
    """``LEDGER_BROKERS``, ``LEDGER_ASSETS`` and the ledger ``rows``, inserted by SQL into a LibreFolio database."""
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.executemany(INSERT_BROKER, [(broker_id, name, CREATED, CREATED) for broker_id, name in LEDGER_BROKERS])
        conn.executemany(INSERT_ASSET, [(asset_id, name, currency, kind, CREATED, CREATED) for asset_id, name, currency, kind in LEDGER_ASSETS])
        conn.executemany(INSERT_TRANSACTION, [(*row, CREATED, CREATED) for row in rows])


def ledger_rows(database: Path) -> list[SimpleNamespace]:
    """The rows of the ledger as J's ``compute_control_totals`` reads them, read here with ``sqlite3`` alone: its eight
    columns, by id; a ``Numeric(18, 6)`` as SQLAlchemy gives it back on SQLite (the stored value, at six places)."""
    with closing(read_only(database)) as conn:
        rows = conn.execute("SELECT id, type, date, broker_id, asset_id, currency, amount, quantity FROM transactions ORDER BY id").fetchall()
    return [SimpleNamespace(id=row_id, type=kind, date=date.fromisoformat(day), broker_id=broker_id, asset_id=asset_id, currency=currency, amount=Decimal(f"{amount:.6f}"), quantity=Decimal(f"{quantity:.6f}")) for row_id, kind, day, broker_id, asset_id, currency, amount, quantity in rows]


def ledger_archive(root: Path, database: Path, *, accounts=ACCOUNTS, rows=LEDGER) -> BuiltArchive:
    """The archive of a data directory (``root/data``) made from ``database``, with ``accounts``, ``FILES`` and the
    ledger ``rows``."""
    data = make_data_dir(root / "data", database, accounts=accounts)
    add_ledger(data / DATABASE_ENTRY, rows)
    return build_into(data, root / "work")


def recorded_totals(manifest: BackupManifest) -> object:
    """What the manifest records of the ledger's totals (lot B-13)."""
    assert "control_totals" in type(manifest.database).model_fields, "ManifestDatabase has no control_totals: lot B-13 is not written yet"
    return manifest.database.control_totals


def manifest_with_totals(archive: BuiltArchive, recorded: object = None, *, drop: bool = False) -> bytes:
    """The manifest of ``archive`` as JSON, its ``database.control_totals`` replaced by ``recorded`` (any JSON value), or
    left out (``drop``, as a backup made before lot B-13 has it); every other field as the build wrote it."""
    document = archive.manifest.model_dump(mode="json")
    database = dict(document["database"])
    if drop:
        database.pop("control_totals", None)
    else:
        database["control_totals"] = recorded
    return json.dumps({**document, "database": database}).encode("utf-8")


def totals_in(report: StagingReport) -> tuple[str, list[dict], int]:
    """What a check's report says of the ledger's totals (lot B-13): the status, the differences (as JSON) and how many
    there are in all."""
    dumped = report.model_dump(mode="json")
    missing = [field for field in TOTALS_FIELDS if field not in dumped]
    assert not missing, f"the report of a check has no {', '.join(missing)}: lot B-13 is not written yet"
    return dumped["control_totals"], dumped["control_totals_differences"], dumped["control_totals_differences_count"]


def totals_difference(kind: str, broker_id: int, key: str | int, before: str | None, after: str | None) -> dict:
    """A difference as a report gives it: ``key`` is the currency of a cash line, the asset of a quantity line."""
    return {"kind": kind, "broker_id": broker_id, "currency": key if kind == "cash" else None, "asset_id": key if kind == "quantity" else None, "before": before, "after": after}


def replace_ledger_totals(patch: pytest.MonkeyPatch, replacement) -> None:
    """``ledger_totals_of`` replaced wherever a check may read it: the totals module's own, and the name ``staging``
    imported (set even if it has none: the module's is then the one it reads)."""
    patch.setattr(totals_module(), "ledger_totals_of", replacement)
    patch.setattr(staging, "ledger_totals_of", replacement, raising=False)


# =============================================================================
# (a) The restore's folders and the stage ids
# =============================================================================


def test_the_restore_layout_is_pinned():
    """(a) Where a check works, what it keeps and how long: a change here strands the stages already on disk."""
    print_section("The restore's folders")
    assert (RESTORE_FOLDER, STAGE_FOLDER, STAGE_DATA_FOLDER, STAGE_REPORT_FILE, STAGE_LOCK_FILE) == (".restore", "stage", "data", "report.json", ".stage.lock"), "the restore's layout moved"
    data = Path("/srv/librefolio-data")
    assert restore_dir(data) == data / ".restore", "the restore's folder is <data dir>/.restore"
    assert stages_dir(data) == data / ".restore" / "stage", "the checks work in <data dir>/.restore/stage"
    assert stage_dir(data, VALID_ID) == data / ".restore" / "stage" / VALID_ID, "one check, one folder named after its id"
    assert STAGE_LIFETIME == timedelta(hours=24), f"a checked archive waits 24 hours for its confirmation, not {STAGE_LIFETIME}"
    assert (MAX_ENTRIES, UPGRADE_TIMEOUT_SECONDS) == (500_000, 3600), f"the limits moved: {MAX_ENTRIES} entries, {UPGRADE_TIMEOUT_SECONDS}s"
    assert ALEMBIC_INI.resolve() == PROJECT_ROOT / "backend" / "alembic.ini", f"the copy is upgraded with this LibreFolio's own migrations: {ALEMBIC_INI}"
    print_success(".restore/stage/<id>/{data,report.json}, .stage.lock, 24 h")


def test_a_stage_id_is_32_lowercase_hexadecimal_digits():
    ids = {new_stage_id() for _ in range(200)}
    assert len(ids) == 200, "every check gets its own id"
    assert all(re.fullmatch(r"[0-9a-f]{32}", value) for value in ids), f"a stage id is 32 lowercase hexadecimal digits: {sorted(ids)[:3]}"
    print_success("200 ids, all distinct, all 32 lowercase hex")


NOT_STAGE_IDS = [
    pytest.param("../" + "0" * 29, id="parent-folder"),
    pytest.param("0" * 31, id="31-digits"),
    pytest.param("0" * 33, id="33-digits"),
    pytest.param("ABCDEF" + "0" * 26, id="uppercase"),
    pytest.param("0" * 31 + "g", id="not-hex"),
    pytest.param("0" * 31 + "/", id="slash"),
    pytest.param(" " + "0" * 31, id="blank"),
]


@pytest.mark.parametrize("value", NOT_STAGE_IDS)
def test_anything_else_never_becomes_a_stage_folder(instance, head_archive, value):
    """(a) A stage id comes back from the API (lot B2b): anything else than one is a ``ValueError``, never a path."""
    for call in (lambda: stage_dir(instance.root, value), lambda: read_report(instance.root, value), lambda: remove_stage(instance.root, value)):
        with pytest.raises(ValueError, match="not a restore stage id"):
            call()
    with pytest.raises(ValueError, match="not a restore stage id"):
        stage_archive(head_archive.path, instance.root, stage_id=value)
    assert leftover_stages(instance.root) == [] and lock_is_free(instance.root), f"{value!r}: no stage, the lock free: {leftover_stages(instance.root)}"
    print_success(f"{value!r} refused everywhere")


def test_a_stage_never_enters_a_backup(tmp_path, databases):
    """(a) ``.restore`` holds the copy of every user's data and its report: a backup must not carry it along."""
    data = make_data_dir(tmp_path / "data", databases.head)
    write_files(data, {f".restore/stage/{VALID_ID}/data/sqlite/app.db": b"a copy being checked", f".restore/stage/{VALID_ID}/report.json": b"{}", ".restore/stage/.stage.lock": b""})
    built = build_into(data, tmp_path / "work")
    with zipfile.ZipFile(built.path) as zf:
        names = zf.namelist()
    assert not [name for name in names if RESTORE_FOLDER in name], f"no entry of the archive comes from .restore: {names}"
    assert built.skipped == (), f"and nothing of it is even reported as left out: {built.skipped}"
    print_success(f"{len(names)} entries, none from .restore")


# =============================================================================
# (b) A backup at this LibreFolio's head
# =============================================================================


def test_a_backup_at_the_head_is_restored_as_it_is(instance, head_archive):
    print_section("A backup at this LibreFolio's head")
    manifest = head_archive.manifest
    report = stage_archive(head_archive.path, instance.root)
    assert (report.action, report.migrations, report.post_migration_fixes) == ("same", [], []), f"at the head: nothing to upgrade, nothing to fix: {report.action}, {report.migrations}, {report.post_migration_fixes}"
    assert (report.head_revision, report.app_version) == (HEAD, APP_VERSION), f"the report says this LibreFolio's head and version: {report.head_revision}, {report.app_version}"
    expected_backup = {"created_at": manifest.created_at, "app_version": APP_VERSION, "origin": "cli", "alembic_revision": HEAD}
    assert report.backup.model_dump() == expected_backup, f"the report says what the manifest says of the backup: {report.backup}"
    assert report.tables == {name: TableRows(before=rows, after=rows) for name, rows in manifest.database.tables.items()}, f"every table, its rows as the manifest counts them, unchanged: {report.tables}"
    assert (report.foreign_key_violations_before, report.foreign_key_violations_after) == (0, 0), "no broken reference"
    assert (report.files, report.files_size, report.instance_key_included) == (len(FILES), sum(map(len, FILES.values())), False), f"the files besides the database: {report.files}, {report.files_size}"
    copy = stage_dir(instance.root, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    assert report.database_size == copy.stat().st_size == manifest.files[0].size, f"the size of the copy's database: {report.database_size}"
    assert report.administrators == ADMINISTRATORS, f"the active administrators of the backup, in order, not the inactive one nor the user: {report.administrators}"
    assert rows_of(copy, "SELECT username FROM users ORDER BY id") == [(name,) for name, _active, _admin in ACCOUNTS], "the copy holds the backup's accounts, not the live instance's"
    assert (report.warnings, report.blockers, report.restorable) == ([], [], True), f"nothing to warn, nothing blocking: {report.warnings}, {report.blockers}"
    print_success(f"same, {len(report.tables)} tables, administrators {report.administrators}")


@needs_posix_modes
def test_the_copy_holds_the_archive_byte_for_byte_beside_its_report(instance, head_archive):
    """(b) ``data/`` is the data directory the archive rebuilds; ``report.json`` beside it, both readable by their owner
    only: they hold every user's data."""
    manifest = head_archive.manifest
    report = stage_archive(head_archive.path, instance.root)
    root = stage_dir(instance.root, report.stage_id)
    assert sorted(path.name for path in root.iterdir()) == [STAGE_DATA_FOLDER, STAGE_REPORT_FILE], f"a stage holds data/ and report.json: {listing(root)[:10]}"
    data = root / STAGE_DATA_FOLDER
    found = {nfc(path.relative_to(data).as_posix()) for path in data.rglob("*") if path.is_file()}
    beside = {name for name in found if name.startswith(DATABASE_ENTRY) and name != DATABASE_ENTRY}
    assert beside <= {DATABASE_ENTRY + suffix for suffix in SQLITE_SIDE_FILES}, f"only SQLite's files beside the database: {sorted(beside)}"
    assert found - beside == {DATABASE_ENTRY, *map(nfc, FILES)}, f"the database and every file of the archive, nothing else: {sorted(found - beside)}"
    for entry, content in FILES.items():
        assert (data / entry).read_bytes() == content, f"{entry} is restored byte for byte"
    assert file_digest(data / DATABASE_ENTRY) == (manifest.files[0].size, manifest.files[0].sha256), "at the head, the copy's database is the archive's, byte for byte: nothing wrote in it"
    folders = [restore_dir(instance.root), stages_dir(instance.root), root, *(path for path in data.rglob("*") if path.is_dir())]
    assert {path.relative_to(instance.root).as_posix(): oct(mode(path)) for path in folders if mode(path) != 0o700} == {}, "every folder of the restore is 0700"
    private = [root / STAGE_REPORT_FILE, data / DATABASE_ENTRY, *(data / entry for entry in FILES)]
    assert {path.relative_to(root).as_posix(): oct(mode(path)) for path in private if mode(path) != 0o600} == {}, "the report and every entry are 0600"
    assert json.loads((root / STAGE_REPORT_FILE).read_text(encoding="utf-8")) == report.model_dump(mode="json"), "report.json is the report returned"
    assert read_report(instance.root, report.stage_id) == report, "read_report gives the report back as it was returned"
    print_success(f"{len(found)} files, 0700/0600, report.json read back equal")


def test_the_report_keeps_its_stage_id_and_expires_24_hours_after_the_check(instance, head_archive):
    first_id = new_stage_id()
    started = datetime.now(UTC)
    first = stage_archive(head_archive.path, instance.root, stage_id=first_id)
    ended = datetime.now(UTC)
    assert first.stage_id == first_id and stage_dir(instance.root, first_id).is_dir(), "the stage id given is the one used"
    assert started <= first.staged_at <= ended, f"staged_at is the time of the check: {first.staged_at} not in [{started}, {ended}]"
    assert first.expires_at - first.staged_at == STAGE_LIFETIME, f"the copy waits 24 hours for its confirmation: {first.expires_at - first.staged_at}"
    second = stage_archive(head_archive.path, instance.root)
    assert re.fullmatch(r"[0-9a-f]{32}", second.stage_id) and second.stage_id != first_id, f"without an id, a new one: {second.stage_id}"
    assert leftover_stages(instance.root) == sorted([first_id, second.stage_id]), "two checks, two stages side by side"
    print_success("stage id kept, expires_at = staged_at + 24 h")


def test_remove_stage_removes_the_copy_and_its_report(instance, head_archive):
    report = stage_archive(head_archive.path, instance.root)
    remove_stage(instance.root, report.stage_id)
    assert leftover_stages(instance.root) == [], f"the copy and its report are gone: {leftover_stages(instance.root)}"
    with pytest.raises(FileNotFoundError):
        read_report(instance.root, report.stage_id)
    remove_stage(instance.root, report.stage_id)  # nothing left to remove: nothing happens
    print_success("removed; read_report → FileNotFoundError; removing again is a no-op")


@needs_symlinks
@pytest.mark.parametrize("what", ["link-to-a-folder", "dangling-link", "file"])
def test_a_stage_that_is_not_a_folder_is_unlinked_never_followed(instance, tmp_path, what):
    ensure_private_dir(stages_dir(instance.root), instance.root)
    elsewhere = tmp_path / "elsewhere"
    write_files(elsewhere, {"report.json": b"{}", "data/sqlite/app.db": b"not the stage's"})
    before = fingerprint(elsewhere)
    stage = stages_dir(instance.root) / VALID_ID
    if what == "link-to-a-folder":
        stage.symlink_to(elsewhere, target_is_directory=True)
    elif what == "dangling-link":
        stage.symlink_to(tmp_path / "nowhere", target_is_directory=True)
    else:
        stage.write_bytes(b"a file where a stage belongs")
    remove_stage(instance.root, VALID_ID)
    assert not stage.exists() and not stage.is_symlink(), f"{what}: the stage is gone"
    assert fingerprint(elsewhere) == before, f"{what}: nothing it pointed to was removed or changed"
    assert not (tmp_path / "nowhere").exists(), "a dangling link is not made to point to a new folder"
    print_success(f"{what}: unlinked, never followed")


@needs_symlinks
@pytest.mark.parametrize("case", ["restore-is-a-link", "stage-is-a-link", "restore-is-a-file", "stage-is-a-file"])
def test_remove_stage_removes_nothing_while_a_restore_folder_is_not_a_plain_folder(instance, tmp_path, case):
    """(g) Lot B2b: ``.restore`` or ``.restore/stage`` a link to a folder holding a stage of that id, or a file: nothing
    is removed, nothing is raised, the link's target is left as it was."""
    elsewhere = tmp_path / "elsewhere"
    write_files(elsewhere, {f"stage/{VALID_ID}/report.json": b"{}", f"stage/{VALID_ID}/data/sqlite/app.db": b"a copy that is not this instance's", f"{VALID_ID}/report.json": b"{}"})
    before = fingerprint(elsewhere)
    restore = restore_dir(instance.root)
    if case.startswith("restore"):
        culprit, target = restore, elsewhere
    else:
        ensure_private_dir(restore, instance.root)
        culprit, target = stages_dir(instance.root), elsewhere
    if case.endswith("link"):
        culprit.symlink_to(target, target_is_directory=True)
    else:
        culprit.write_bytes(b"a file where a folder of the restore belongs")
    remove_stage(instance.root, VALID_ID)
    assert fingerprint(elsewhere) == before, f"{case}: removed or changed through it: {changed(before, fingerprint(elsewhere))}"
    assert culprit.is_symlink() if case.endswith("link") else culprit.is_file(), f"{case}: left in place"
    print_success(f"{case}: nothing removed")


@needs_symlinks
@pytest.mark.parametrize("case", ["no-stage", "not-a-report", "a-link"])
def test_read_report_reads_only_a_report_of_its_own(instance, tmp_path, case):
    """(b) No stage, or a ``report.json`` that is not a report: ``FileNotFoundError``. A ``report.json`` that is a link,
    even to a valid report: never followed."""
    folder = stage_dir(instance.root, VALID_ID)
    if case != "no-stage":
        ensure_private_dir(folder, instance.root)
    if case == "not-a-report":
        (folder / STAGE_REPORT_FILE).write_text('{"stage_id": "not a report"}', encoding="utf-8")
    elif case == "a-link":
        elsewhere = tmp_path / "elsewhere.json"
        elsewhere.write_text("{}", encoding="utf-8")
        (folder / STAGE_REPORT_FILE).symlink_to(elsewhere)
    with pytest.raises(OSError) as raised:
        read_report(instance.root, VALID_ID)
    if case != "a-link":
        assert isinstance(raised.value, FileNotFoundError), f"{case}: FileNotFoundError, not {type(raised.value).__name__}"
    print_success(f"{case}: {type(raised.value).__name__}")


# =============================================================================
# (c) An older backup: the copy upgraded for real
# =============================================================================


def description(tables: dict[str, int]) -> DatabaseDescription:
    """A database as ``describe_database`` would describe it: intact, no broken reference, these rows per table."""
    return DatabaseDescription(size=8192, sha256="a" * 64, integrity_check="ok", foreign_key_violations=0, tables=dict(tables), alembic_revision=OLDER)


def synthetic_manifest(tables: dict[str, int]) -> BackupManifest:
    return BackupManifest(
        created_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC),
        origin="cli",
        app_version=APP_VERSION,
        alembic_revision=OLDER,
        database=ManifestDatabase(integrity_check="ok", foreign_key_violations=0, tables=dict(tables)),
        files=[ManifestFile(path=DATABASE_ENTRY, size=8192, sha256="a" * 64)],
    )


#: (rows before the upgrade, rows after it, the warnings): a table absent on one side counts as empty.
ROW_CHANGES = [
    pytest.param({"users": 3}, {"users": 3}, [], id="unchanged"),
    pytest.param({"users": 3}, {"users": 3, "plugin_settings": 0}, [], id="created-empty"),
    pytest.param({"users": 3}, {"users": 3, "plugin_settings": 2}, ["rows_changed"], id="created-with-rows"),
    pytest.param({"users": 3, "old_cache": 0}, {"users": 3}, [], id="dropped-empty"),
    pytest.param({"users": 3, "old_cache": 5}, {"users": 3}, ["rows_changed"], id="dropped-with-rows"),
    pytest.param({"users": 3}, {"users": 4}, ["rows_changed"], id="rows-changed"),
]


@pytest.mark.parametrize(("before", "after", "warnings"), ROW_CHANGES)
def test_rows_changed_is_warned_only_when_a_count_differs_an_absent_table_counting_as_empty(before, after, warnings):
    """(j) The rule of ``rows_changed``, on the report alone: a table the upgrade creates empty (``None`` → 0) or drops
    empty (0 → ``None``) changes no row; created or dropped with rows, or a count that moved, does. The table still
    appears in ``tables``, absent on one side as ``None``."""
    report = _report(VALID_ID, synthetic_manifest(before), description(before), description(after), "upgrade", AFTER_OLDER, HEAD, [], ADMINISTRATORS)
    assert report.warnings == warnings, f"{before} → {after}: warnings {report.warnings}, expected {warnings}"
    assert report.tables == {name: TableRows(before=before.get(name), after=after.get(name)) for name in before.keys() | after.keys()}, f"every table, absent as None: {report.tables}"
    print_success(f"{before} → {after}: {report.warnings}")


def test_the_plan_of_every_revision_is_the_migrations_after_it_oldest_first():
    """(c) What ``alembic upgrade head`` will apply to a backup at each revision, as the migration files describe it."""
    print_section("The migrations a restore applies")
    for index, migration in enumerate(CHAIN):
        expected = ("same", [], HEAD) if migration.revision == HEAD else ("upgrade", CHAIN[index + 1 :], HEAD)
        assert _revision_plan(migration.revision) == expected, f"a backup at {migration.revision}: {expected[1]}"
    print_success(f"{len(CHAIN)} revisions, each planned up to {HEAD}")


def test_an_older_backup_is_upgraded_on_the_copy(upgraded):
    print_section("An older backup")
    report = upgraded.report
    assert (report.action, report.backup.alembic_revision, report.head_revision) == ("upgrade", OLDER, HEAD), f"a backup at {OLDER} is upgraded to {HEAD}: {report.action}"
    assert report.migrations == AFTER_OLDER, f"the migrations after {OLDER} up to the head, oldest first, each with its first line: {report.migrations}"
    copy = stage_dir(upgraded.instance, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    assert revisions_of(copy) == [HEAD], f"the copy is at the head: {revisions_of(copy)}"
    assert rows_of(copy, "SELECT key, value FROM global_settings ORDER BY key") == [("registration_mode", "open")], f"{CONVERSION} ran on the copy: enable_registration became registration_mode"
    manifest_tables = upgraded.archive.manifest.database.tables
    names = [row[0] for row in rows_of(copy, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    copy_tables = {name: rows_of(copy, f'SELECT count(*) FROM "{name}"')[0][0] for name in names}
    expected = {name: TableRows(before=manifest_tables.get(name), after=copy_tables.get(name)) for name in manifest_tables.keys() | copy_tables.keys()}
    assert report.tables == expected, f"every table: before, the rows the manifest counts (none for a table the upgrade created); after, the copy's: {report.tables}"
    assert report.warnings == (["rows_changed"] if any((rows.before or 0) != (rows.after or 0) for rows in expected.values()) else []), f"rows_changed exactly when a table's count differs, an absent table counting as empty (a table the upgrade creates empty changes no row): {report.warnings}"
    assert (report.post_migration_fixes, report.administrators, report.restorable) == ([], ADMINISTRATORS, True), f"nothing to fix, restorable: {report.post_migration_fixes}"
    print_success(f"{OLDER} → {HEAD}: {[m.revision for m in report.migrations]}")


def test_the_upgrade_reads_the_archive_and_leaves_the_live_data_directory_as_it_was(upgraded):
    """(c)(i) The upgrade runs on the copy alone: the archive, and every path of the live data directory, are unchanged."""
    assert sha256(upgraded.archive.path.read_bytes()) == upgraded.archive_sha256, "the archive is only read"
    assert upgraded.after == upgraded.before, f"the live data directory changed: {changed(upgraded.before, upgraded.after)}"
    assert not upgraded.configured.exists(), f"the upgrade wrote in the configured data directory: {listing(upgraded.configured)}"
    print_success(f"archive and {len(upgraded.before)} live paths unchanged")


def test_the_progress_of_an_upgrade_goes_through_every_phase(upgraded):
    """(h) Upgrading: none of the migrations done, then all of them, between unpacking and verifying."""
    progress = upgraded.progress
    count = len(upgraded.report.migrations)
    assert progress.phases == PHASES, f"checking, unpacking, upgrading, verifying: {progress.phases}"
    assert [event for event in progress.events if event[0] == "upgrading"] == [("upgrading", 0, count), ("upgrading", count, count)], f"upgrading 0/{count}, then {count}/{count}: {progress.events}"
    print_success(f"phases {progress.phases}")


# =============================================================================
# (d) Administrators
# =============================================================================


def test_without_an_active_administrator_the_restore_is_blocked(instance, databases, tmp_path):
    """(d) A disabled administrator and a user: after a restore nobody could manage the instance. Blocked, with the
    report still written, so that the confirmation can say why."""
    print_section("No active administrator")
    data = make_data_dir(tmp_path / "data", databases.head, accounts=WITHOUT_ADMINISTRATOR)
    report = stage_archive(build_into(data, tmp_path / "work").path, instance.root)
    assert (report.administrators, report.blockers, report.restorable) == ([], ["no_administrator"], False), f"blocked: {report.administrators}, {report.blockers}"
    assert read_report(instance.root, report.stage_id) == report, "the report is written all the same"
    print_success("no_administrator, not restorable, report written")


# =============================================================================
# (e) Refusals
# =============================================================================
#
# Each case writes an archive from the module's head archive (``base``) or from a database of its own, and names the
# code it must be refused with and the last phase the check reached: ``checking`` when it is refused before a byte of
# the copy is written, ``unpacking`` when the copy, or part of it, had to be written to know.


def not_a_zip(tmp, base, databases):
    path = tmp / "notes.zip"
    path.write_text("these are not the bytes of a zip\n", encoding="utf-8")
    return path


def empty_zip(tmp, base, databases):
    path = tmp / "empty.zip"
    zipfile.ZipFile(path, "w").close()
    return path


def zipped_by_hand(tmp, base, databases):
    """The files of a backup without its manifest: a data directory zipped by hand (decision 42)."""
    return pack(tmp / "by-hand.zip", entries_of(base), None)


def another_format(tmp, base, databases):
    return pack(tmp / "other.zip", entries_of(base), manifest_document(base, format="another-backup-tool"))


def missing_file(tmp, base, databases):
    return tmp / "absent.zip"


def a_folder(tmp, base, databases):
    folder = tmp / "folder.zip"
    folder.mkdir()
    return folder


def zip_header_only(tmp, base, databases):
    path = tmp / "header.zip"
    path.write_bytes(b"PK\x03\x04" + bytes(64))
    return path


def truncated(tmp, base, databases):
    raw = base.path.read_bytes()
    path = tmp / "truncated.zip"
    path.write_bytes(raw[: len(raw) // 2])
    return path


def damaged_entry(tmp, base, databases):
    """The logo stored, one of its bytes inverted: its CRC tells, once it is read to its end."""
    stored = [replace(entry, compress_type=zipfile.ZIP_STORED) for entry in entries_of(base)]
    return flip(pack(tmp / "damaged.zip", stored, base.manifest), LOGO)


def damaged_manifest(tmp, base, databases):
    return flip(pack(tmp / "damaged.zip", entries_of(base), base.manifest), MANIFEST_ENTRY)


def newer_format(tmp, base, databases):
    return pack(tmp / "newer.zip", entries_of(base), manifest_document(base, format_version=2))


def database_not_first(tmp, base, databases):
    files = base.manifest.model_dump(mode="json")["files"]
    return pack(tmp / "invalid.zip", entries_of(base), manifest_document(base, files=files[1:] + files[:1]))


def secrets_listed(tmp, base, databases):
    """The instance key in the zip and in its manifest: a path no backup carries, refused with the manifest."""
    files = [*base.manifest.model_dump(mode="json")["files"], {"path": "secrets/instance.key", "size": len(SECRET), "sha256": sha256(SECRET)}]
    return pack(tmp / "secrets.zip", [*entries_of(base), Entry("secrets/instance.key", SECRET)], manifest_document(base, files=files))


def manifest_not_json(tmp, base, databases):
    return pack(tmp / "unreadable.zip", entries_of(base), b"{not json")


def huge_manifest(tmp, base, databases):
    """65 MiB of blanks as the manifest: a few dozen KiB deflated, refused by the size the zip declares."""
    path = tmp / "huge-manifest.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(DATABASE_ENTRY, b"not even a database")
        with zf.open(MANIFEST_ENTRY, "w", force_zip64=True) as handle:
            for _ in range(MANIFEST_MAX_BYTES // (1024 * 1024) + 1):
                handle.write(b" " * (1024 * 1024))
    return path


#: The logo again, its name in capitals: on a file system that ignores case, the same file.
CASE_VARIANT = Entry("custom-uploads/LOGO.png", b"another logo, under the same name in capitals\n")


def name_twice(tmp, base, databases):
    return pack(tmp / "twice.zip", [*entries_of(base), Entry(LOGO, FILES[LOGO])], base.manifest)


def manifest_twice(tmp, base, databases):
    """Two manifests: which one a restore would trust is not defined."""
    return pack(tmp / "twice.zip", entries_of(base), base.manifest, manifest_twice=True)


def case_in_the_zip(tmp, base, databases):
    """The variant in the zip only: the manifest does not list it (the check of names comes first)."""
    return pack(tmp / "case.zip", [*entries_of(base), CASE_VARIANT], base.manifest)


def case_in_the_manifest(tmp, base, databases):
    """The variant in the manifest only: the zip does not hold it (the check of names comes first)."""
    return pack(tmp / "case.zip", entries_of(base), listing_also(base, CASE_VARIANT))


def case_in_both(tmp, base, databases):
    return pack(tmp / "case.zip", [*entries_of(base), CASE_VARIANT], listing_also(base, CASE_VARIANT))


def unlisted_file(tmp, base, databases):
    return pack(tmp / "unlisted.zip", [*entries_of(base), Entry("custom-uploads/new.txt", b"not in the manifest\n")], base.manifest)


def unlisted_instance_key(tmp, base, databases):
    return pack(tmp / "unlisted.zip", [*entries_of(base), Entry("secrets/instance.key", SECRET)], base.manifest)


def parent_folder_entry(tmp, base, databases):
    return pack(tmp / "slip.zip", [*entries_of(base), Entry("../../outside.txt", b"written outside the copy\n")], base.manifest)


#: An entry that is a folder by its mode, listed as an empty file; one that is a link to the instance key, listed with
#: the bytes of its target: unpacked as files, both would be something else than what the backup held.
FOLDER_ENTRY = Entry("custom-uploads/sub", b"", mode=stat.S_IFDIR | 0o755)
LINK_ENTRY = Entry("custom-uploads/link", b"../../secrets/instance.key", mode=stat.S_IFLNK | 0o777)


def folder_entry(tmp, base, databases):
    return pack(tmp / "folder.zip", [*entries_of(base), FOLDER_ENTRY], listing_also(base, FOLDER_ENTRY))


def link_entry(tmp, base, databases):
    return pack(tmp / "link.zip", [*entries_of(base), LINK_ENTRY], listing_also(base, LINK_ENTRY))


def encrypted_entry(tmp, base, databases):
    return pack(tmp / "encrypted.zip", with_logo(base, encrypted=True), base.manifest)


def bzip2_entry(tmp, base, databases):
    return pack(tmp / "bzip2.zip", with_logo(base, compress_type=zipfile.ZIP_BZIP2), base.manifest)


def lzma_entry(tmp, base, databases):
    return pack(tmp / "lzma.zip", with_logo(base, compress_type=zipfile.ZIP_LZMA), base.manifest)


def size_differs(tmp, base, databases):
    """The manifest gives the logo one byte more than the zip says it holds."""
    files = [entry.model_copy(update={"size": entry.size + 1}) if entry.path == LOGO else entry for entry in base.manifest.files]
    return pack(tmp / "larger.zip", entries_of(base), base.manifest.model_copy(update={"files": files}))


def bytes_differ(tmp, base, databases):
    """The logo has other bytes of the same size: only its SHA-256, computed as it is written, tells."""
    return pack(tmp / "other.zip", with_logo(base, data=bytes(reversed(FILES[LOGO]))), base.manifest)


def missing_entry(tmp, base, databases):
    return pack(tmp / "missing.zip", [entry for entry in entries_of(base) if entry.name != LOGO], base.manifest)


def with_tables(base: BuiltArchive, tables: dict[str, int]):
    return base.manifest.model_copy(update={"database": base.manifest.database.model_copy(update={"tables": tables})})


def rows_differ(tmp, base, databases):
    tables = base.manifest.database.tables
    return pack(tmp / "rows.zip", entries_of(base), with_tables(base, {**tables, "users": tables["users"] + 1}))


def table_differs(tmp, base, databases):
    return pack(tmp / "tables.zip", entries_of(base), with_tables(base, {**base.manifest.database.tables, "ghost": 0}))


def revision_differs(tmp, base, databases):
    """The manifest says an older revision; the database is at the head."""
    return pack(tmp / "revision.zip", entries_of(base), base.manifest.model_copy(update={"alembic_revision": OLDER}))


def from_head_database(tmp: Path, databases: Databases, *statements: str) -> Path:
    """The archive of a data directory at the head whose database ``statements`` change."""
    data = make_data_dir(tmp / "data", databases.head)
    execute(data / DATABASE_ENTRY, *statements)
    return build_into(data, tmp / "work").path


def damaged_database(tmp, base, databases):
    data = make_data_dir(tmp / "data", databases.head)
    break_not_null(data / DATABASE_ENTRY, rows=2)
    return build_into(data, tmp / "work").path


def no_revision(tmp, base, databases):
    return from_head_database(tmp, databases, "DELETE FROM alembic_version")


def two_revisions(tmp, base, databases):
    return from_head_database(tmp, databases, f"INSERT INTO alembic_version (version_num) VALUES ('{NEWER_REVISION}')")


def no_version_table(tmp, base, databases):
    return from_head_database(tmp, databases, "DROP TABLE alembic_version")


def newer_revision(tmp, base, databases):
    return from_head_database(tmp, databases, f"UPDATE alembic_version SET version_num = '{NEWER_REVISION}'")


REFUSALS = [
    pytest.param(not_a_zip, "not_a_backup", "checking", id="not-a-zip"),
    pytest.param(empty_zip, "not_a_backup", "checking", id="empty-zip"),
    pytest.param(zipped_by_hand, "not_a_backup", "checking", id="data-directory-zipped-by-hand"),
    pytest.param(another_format, "not_a_backup", "checking", id="manifest-of-another-format"),
    pytest.param(missing_file, "archive_unreadable", "checking", id="missing-file"),
    pytest.param(a_folder, "archive_unreadable", "checking", id="a-folder"),
    pytest.param(zip_header_only, "archive_damaged", "checking", id="zip-header-only"),
    pytest.param(truncated, "archive_damaged", "checking", id="truncated"),
    pytest.param(damaged_entry, "archive_damaged", "unpacking", id="damaged-entry"),
    pytest.param(newer_format, "manifest_newer_format", "checking", id="newer-format"),
    pytest.param(database_not_first, "manifest_invalid", "checking", id="database-not-first"),
    pytest.param(secrets_listed, "manifest_invalid", "checking", id="instance-key-listed"),
    pytest.param(manifest_not_json, "manifest_unreadable", "checking", id="manifest-not-json"),
    pytest.param(damaged_manifest, "manifest_unreadable", "checking", id="damaged-manifest"),
    pytest.param(huge_manifest, "manifest_too_large", "checking", id="huge-manifest"),
    pytest.param(name_twice, "duplicate_entry", "checking", id="name-twice"),
    pytest.param(manifest_twice, "duplicate_entry", "checking", id="manifest-twice"),
    pytest.param(case_in_the_zip, "duplicate_entry", "checking", id="case-variant-in-the-zip"),
    pytest.param(case_in_the_manifest, "duplicate_entry", "checking", id="case-variant-in-the-manifest"),
    pytest.param(case_in_both, "duplicate_entry", "checking", id="case-variant-in-both"),
    pytest.param(unlisted_file, "unexpected_entry", "checking", id="unlisted-file"),
    pytest.param(unlisted_instance_key, "unexpected_entry", "checking", id="unlisted-instance-key"),
    pytest.param(parent_folder_entry, "unexpected_entry", "checking", id="parent-folder-entry"),
    pytest.param(folder_entry, "not_a_file", "checking", id="folder-entry"),
    pytest.param(link_entry, "not_a_file", "checking", id="link-entry"),
    pytest.param(encrypted_entry, "encrypted_entry", "checking", id="encrypted-entry"),
    pytest.param(bzip2_entry, "unsupported_entry", "checking", id="bzip2-entry"),
    pytest.param(lzma_entry, "unsupported_entry", "checking", id="lzma-entry"),
    pytest.param(size_differs, "checksum_mismatch", "checking", id="size-differs"),
    pytest.param(bytes_differ, "checksum_mismatch", "unpacking", id="bytes-differ"),
    pytest.param(missing_entry, "missing_entry", "checking", id="missing-entry"),
    pytest.param(damaged_database, "database_damaged", "unpacking", id="damaged-database"),
    pytest.param(rows_differ, "manifest_mismatch", "unpacking", id="rows-differ"),
    pytest.param(table_differs, "manifest_mismatch", "unpacking", id="tables-differ"),
    pytest.param(revision_differs, "manifest_mismatch", "unpacking", id="revision-differs"),
    pytest.param(no_revision, "revision_missing", "unpacking", id="no-revision"),
    pytest.param(two_revisions, "revision_missing", "unpacking", id="two-revisions"),
    pytest.param(no_version_table, "revision_missing", "unpacking", id="no-version-table"),
    pytest.param(newer_revision, "revision_unknown", "unpacking", id="newer-revision"),
]


@pytest.mark.parametrize(("make", "code", "reached"), REFUSALS)
def test_an_archive_that_cannot_be_restored_is_refused_and_leaves_nothing(instance, head_archive, databases, tmp_path, monkeypatch, make, code, reached):
    """(e) The code says why. Nothing of the copy is left, the lock is free, the message says no path, the archive is
    unchanged, no upgrade ran, and a refusal decided from the zip and its manifest never began to unpack."""
    archive = make(tmp_path, head_archive, databases)
    original = sha256(archive.read_bytes()) if archive.is_file() else None
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert error.code == code, f"{code} expected, the check said {error.code}: {error}"
    assert progress.phases == PHASES[: PHASES.index(reached) + 1], f"{code}: the check must stop in {reached}, it went through {progress.phases}"
    if original is not None:
        assert sha256(archive.read_bytes()) == original, "the archive is only read"
    print_success(f"{code} ({reached}): {error}")


def test_a_backup_of_a_newer_librefolio_says_to_update_first_and_is_never_downgraded(instance, databases, tmp_path, monkeypatch):
    """(e) A revision this LibreFolio does not know comes from a newer one, most likely: update first. No ``alembic``
    process is ever started for it (a ``downgrade`` would destroy what the newer schema holds)."""
    started: list[list[str]] = []
    monkeypatch.setattr(staging, "subprocess", SimpleNamespace(run=lambda command, **kwargs: started.append(command), TimeoutExpired=subprocess.TimeoutExpired))
    error, _progress = refused(newer_revision(tmp_path, None, databases), instance)
    assert error.code == "revision_unknown" and "update LibreFolio first" in str(error), f"revision_unknown, saying to update first: {error.code}: {error}"
    assert started == [], f"no alembic process may run for a newer backup: {started}"
    print_success(f"revision_unknown: {error}")


def test_entries_are_checked_against_the_manifest_before_one_is_read(instance, head_archive, tmp_path, monkeypatch):
    """(e) A size that differs from the manifest's is refused from the zip's directory: no entry is read, not even the
    database, whose copy is the first written."""
    archive = size_differs(tmp_path, head_archive, None)
    reads: list[str] = []
    real_open = zipfile.ZipFile.open

    def open_entry(self, name, *args, **kwargs):
        reads.append(name if isinstance(name, str) else name.filename)
        return real_open(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", open_entry)
    error, _progress = refused(archive, instance)
    assert error.code == "checksum_mismatch", f"checksum_mismatch, not {error.code}"
    assert reads == [MANIFEST_ENTRY], f"only the manifest is read before the entries are checked: {reads}"
    print_success("refused with only manifest.json read")


def test_more_entries_than_the_limit_are_refused_before_any_is_written(instance, head_archive, monkeypatch):
    """(e) ``MAX_ENTRIES`` files and the manifest is the most an archive holds; one more is refused from the directory."""
    files = len(head_archive.manifest.files)
    monkeypatch.setattr(staging, "MAX_ENTRIES", files - 1)
    error, progress = refused(head_archive.path, instance)
    assert (error.code, progress.phases) == ("too_many_entries", ["checking"]), f"one entry over the limit: {error.code}, {progress.phases}"
    monkeypatch.setattr(staging, "MAX_ENTRIES", files)
    report = stage_archive(head_archive.path, instance.root)
    assert report.restorable, "at the limit exactly, the archive is checked"
    print_success(f"{files + 1} entries: refused over a limit of {files - 1}, checked at {files}")


#: Two files where one names the folder of the other: no data directory can hold both.
NESTED = {
    "file-first": [Entry("custom-uploads/x", b"a file\n"), Entry("custom-uploads/x/y", b"a file below the first, as if it were a folder\n")],
    "folder-first": [Entry("custom-uploads/x/y", b"a file below the second, as if it were a folder\n"), Entry("custom-uploads/x", b"a file\n")],
    # The same on a file system that ignores case: the folder named in another case than the file.
    "folder-in-another-case": [Entry("custom-uploads/X", b"a file\n"), Entry("custom-uploads/x/y", b"a file below the first, its name in another case\n")],
}


@pytest.mark.parametrize("order", list(NESTED))
def test_an_entry_whose_name_is_the_folder_of_another_is_refused_as_a_duplicate(instance, head_archive, tmp_path, order):
    """(e) ``custom-uploads/x`` a file, and ``custom-uploads/x/y`` below it as if it were a folder: one path named twice.
    Refused as ``duplicate_entry`` in checking, before a byte is written, in either order and whatever the case of the
    folder; never with another error (a ``BackupPathError`` blamed a folder of the data directory, with a path, for a
    fault of the archive, and ``_unpack`` now turns one into ``duplicate_entry``: reaching it is too late)."""
    pair = NESTED[order]
    archive = pack(tmp_path / "collision.zip", [*entries_of(head_archive), *pair], listing_also(head_archive, *pair))
    try:
        error, progress = refused(archive, instance)
    except BackupPathError as exc:
        pytest.fail(f"{order}: the archive names custom-uploads/x as a file and as a folder, and the check let BackupPathError escape ({exc}; stages left: {leftover_stages(instance.root)}) where StagingError('duplicate_entry') belongs")
    assert (error.code, progress.phases) == ("duplicate_entry", ["checking"]), f"{order}: duplicate_entry before anything is written, not {error.code} after {progress.phases}"
    print_success(f"{order}: duplicate_entry, in checking")


@pytest.mark.parametrize("where", ["in-both", "in-the-zip", "in-the-manifest"])
def test_one_name_in_two_unicode_forms_is_never_written_over(instance, head_archive, tmp_path, where):
    """(e) ``café.txt`` composed (NFC) and decomposed (NFD): two names for Python, one file for a file system that ignores
    the form (APFS). Deliberate contract, on every file system: refused in checking as ``duplicate_entry``, as a name
    twice in another case is (genuine backups never hold such names: uploads are stored as ``{uuid}.{ext}``). The second
    form in the zip and the manifest, in the zip only (unlisted), or in the manifest only (missing): the names are
    compared first."""
    composed = Entry(unicodedata.normalize("NFC", "custom-uploads/café.txt"), b"composed\n")
    decomposed = Entry(unicodedata.normalize("NFD", "custom-uploads/café.txt"), b"decomposed, longer than the first\n")
    assert composed.name != decomposed.name, "precondition: two names for Python"
    in_zip = [composed, decomposed] if where != "in-the-manifest" else [composed]
    listed_too = [composed, decomposed] if where != "in-the-zip" else [composed]
    archive = pack(tmp_path / "forms.zip", [*entries_of(head_archive), *in_zip], listing_also(head_archive, *listed_too))
    error, progress = refused(archive, instance)
    assert (error.code, progress.phases) == ("duplicate_entry", ["checking"]), f"{where}: duplicate_entry before anything is written, not {error.code} after {progress.phases}"
    print_success(f"{where}: duplicate_entry, in checking")


# -----------------------------------------------------------------------------
# (e) Refusals that need the disk, the migrations or the upgrade to fail
# -----------------------------------------------------------------------------


class LittleRoom:
    """``staging``'s ``shutil``, but ``disk_usage`` reports ``free`` bytes for ``mount`` and everything below it."""

    def __init__(self, mount: Path, free: int):
        self._mount = mount
        self._free = free

    def __getattr__(self, name: str):
        return getattr(shutil, name)

    def disk_usage(self, path):
        path = Path(path)
        if path == self._mount or self._mount in path.parents:
            return SimpleNamespace(total=2 * self._free, used=self._free, free=self._free)
        return shutil.disk_usage(path)


def test_the_space_needed_is_every_entry_the_database_twice_more_and_a_margin(head_archive):
    """(e) The copy, room for the upgrade to rewrite the database, and 64 MiB the file system keeps for itself."""
    manifest = head_archive.manifest
    expected = sum(entry.size for entry in manifest.files) + 2 * manifest.files[0].size + 64 * 1024 * 1024
    assert space_needed(manifest) == expected, f"space_needed: {space_needed(manifest)}, expected {expected}"
    print_success(f"{expected} bytes")


def test_without_the_space_needed_nothing_is_written(instance, head_archive, monkeypatch):
    needed = space_needed(head_archive.manifest)
    monkeypatch.setattr(staging, "shutil", LittleRoom(instance.root, needed - 1))
    error, progress = refused(head_archive.path, instance)
    assert (error.code, progress.phases) == ("no_space", ["checking"]), f"one byte short: no_space before anything is written: {error.code}, {progress.phases}"
    assert str(needed) in str(error), f"the message says how many bytes are needed: {error}"
    monkeypatch.setattr(staging, "shutil", LittleRoom(instance.root, needed))
    assert stage_archive(head_archive.path, instance.root).restorable, "with exactly the space needed, the archive is checked"
    print_success(f"{needed - 1} bytes free: no_space; {needed}: checked")


class BrokenWriter:
    """A file opened for writing whose every write fails with ``code``."""

    def __init__(self, handle, code: int):
        self._handle = handle
        self._code = code

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        self._handle.close()
        return False

    def write(self, data: bytes) -> int:
        raise OSError(self._code, os.strerror(self._code))


class FailingWrites:
    """``staging``'s ``os``, but the file of every entry fails at its first write with ``code``; the rest is the real ``os``."""

    def __init__(self, code: int):
        self._code = code
        self.failed = 0

    def __getattr__(self, name: str):
        return getattr(os, name)

    def fdopen(self, fd, mode="r", *args, **kwargs):
        handle = os.fdopen(fd, mode, *args, **kwargs)
        if mode != "wb":
            return handle
        self.failed += 1
        return BrokenWriter(handle, self._code)


WRITE_FAILURES = [pytest.param(errno.ENOSPC, "no_space", id="ENOSPC"), pytest.param(errno.EIO, "stage_failed", id="EIO"), pytest.param(errno.EACCES, "stage_failed", id="EACCES")]
if hasattr(errno, "EDQUOT"):
    WRITE_FAILURES.insert(1, pytest.param(errno.EDQUOT, "no_space", id="EDQUOT"))


@pytest.mark.parametrize(("code", "expected"), WRITE_FAILURES)
def test_a_write_that_fails_while_unpacking_is_no_space_or_stage_failed(instance, head_archive, monkeypatch, code, expected):
    """(e) A disk that fills up, or a quota reached, after the space was checked: ``no_space``; any other failure of a
    write: ``stage_failed``, the cause in the log. The first failure stops the check."""
    writes = FailingWrites(code)
    monkeypatch.setattr(staging, "os", writes)
    error, progress = refused(head_archive.path, instance)
    assert (error.code, progress.phases, writes.failed) == (expected, ["checking", "unpacking"], 1), f"{errno.errorcode[code]}: {error.code}, {progress.phases}, {writes.failed} write(s) failed"
    print_success(f"{errno.errorcode[code]} → {error.code}")


@pytest.mark.parametrize("scripts", ["no-configuration", "no-migration"])
def test_without_migration_scripts_to_read_the_check_is_refused(instance, head_archive, tmp_path, monkeypatch, scripts):
    """(e) ``head_unknown``: an ``alembic.ini`` that cannot be read, or migrations without a head."""
    ini = tmp_path / "alembic.ini"
    if scripts == "no-migration":
        (tmp_path / "scripts" / "versions").mkdir(parents=True)
        ini.write_text(f"[alembic]\nscript_location = {tmp_path / 'scripts'}\n", encoding="utf-8")
    monkeypatch.setattr(staging, "ALEMBIC_INI", ini)
    error, progress = refused(head_archive.path, instance)
    assert (error.code, progress.phases) == ("head_unknown", ["checking", "unpacking"]), f"{scripts}: head_unknown once the copy is checked: {error.code}, {progress.phases}"
    print_success(f"{scripts}: head_unknown")


class AlembicStandIn:
    """``staging``'s ``subprocess``: ``run`` records the command and what the copy holds then, and answers ``outcome`` (a
    result, or an exception to raise) without starting anything. ``TimeoutExpired`` is the real one."""

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, outcome):
        self._outcome = outcome
        self.calls: list[tuple[list[str], dict]] = []
        self.copies: list[tuple[Path, list[str]]] = []

    def run(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        database = Path(next(arg for arg in command if arg.startswith("sqlalchemy.url=")).removeprefix("sqlalchemy.url=sqlite:///"))
        self.copies.append((database, revisions_of(database) if database.is_file() else []))
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


def test_the_upgrade_is_alembic_on_the_copy_in_a_process_of_its_own(instance, older_archive, monkeypatch):
    """(c)(e) ``alembic upgrade head`` of the copy, this LibreFolio's migrations, from the project root, within the
    hour. An ``alembic`` that ends well but leaves the copy where it was: ``upgrade_failed``, found when verifying."""
    alembic = AlembicStandIn(subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(staging, "subprocess", alembic)
    stage_id = new_stage_id()
    error, progress = refused(older_archive.path, instance, stage_id=stage_id)
    copy = (stage_dir(instance.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY).resolve()
    assert len(alembic.calls) == 1, f"one alembic process: {alembic.calls}"
    command, kwargs = alembic.calls[0]
    assert command == [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "-x", f"sqlalchemy.url=sqlite:///{copy}", "upgrade", "head"], f"the upgrade of the copy: {command}"
    assert (Path(kwargs.get("cwd", "")).resolve(), kwargs.get("timeout")) == (PROJECT_ROOT, UPGRADE_TIMEOUT_SECONDS), f"from the project root, within the hour: {kwargs}"
    assert alembic.copies == [(copy, [OLDER])], f"the copy is there, at the backup's revision, when alembic is asked to upgrade it: {alembic.copies}"
    assert (error.code, progress.phases) == ("upgrade_failed", PHASES), f"the copy did not reach the head: {error.code}, {progress.phases}"
    print_success("alembic -c backend/alembic.ini -x sqlalchemy.url=<copy> upgrade head")


UPGRADE_FAILURES = [
    pytest.param(subprocess.CompletedProcess([], 1, "", "alembic: a migration failed\n"), id="exit-code-1"),
    pytest.param(subprocess.TimeoutExpired(["alembic"], UPGRADE_TIMEOUT_SECONDS), id="timeout"),
    pytest.param(FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT)), id="cannot-start"),
]


@pytest.mark.parametrize("outcome", UPGRADE_FAILURES)
def test_an_upgrade_that_fails_ends_late_or_cannot_start_is_refused(instance, older_archive, monkeypatch, outcome):
    monkeypatch.setattr(staging, "subprocess", AlembicStandIn(outcome))
    count = len(AFTER_OLDER)
    error, progress = refused(older_archive.path, instance)
    assert error.code == "upgrade_failed", f"upgrade_failed, not {error.code}"
    assert progress.events[-1] == ("upgrading", 0, count) and progress.phases == ["checking", "unpacking", "upgrading"], f"the upgrade began and never ended: {progress.events}"
    print_success(f"{type(outcome).__name__}: upgrade_failed")


#: The migration every older backup of this module still has to run that creates a table, and that table. It creates the
#: tables it does not find among the tables: an index holding that name is not one, and refuses its ``CREATE TABLE``.
PENDING_MIGRATION = "007_plugin_settings"
PENDING_TABLE = "plugin_system_settings"


def test_an_upgrade_that_fails_in_alembic_is_refused_and_leaves_nothing(instance, databases, tmp_path):
    """(e) For real: an older backup whose database holds an index under the name of the table ``007_plugin_settings``
    creates. That migration sees no such table, and its ``op.create_table`` fails («there is already an index named»)
    in alembic's own process, on the copy; the check says ``upgrade_failed`` and removes the copy. Tables and indexes
    only, as LibreFolio makes them: lot B-28 lets the archive through to its upgrade."""
    assert PENDING_MIGRATION in [migration.revision for migration in AFTER_OLDER], f"precondition: {PENDING_MIGRATION} is still to run on a backup at {OLDER}"
    data = make_data_dir(tmp_path / "data", databases.older)
    execute(data / DATABASE_ENTRY, f"CREATE INDEX {PENDING_TABLE} ON users (username)")
    archive = build_into(data, tmp_path / "work").path
    rows = rows_of(database_of(archive, tmp_path / "archived.db"), "SELECT type, name, sql FROM sqlite_master")
    foreign = [(kind, name, schema_kind(sql)) for kind, name, sql in rows if kind not in ("table", "index") or schema_kind(sql) not in ALLOWED_KINDS]
    assert not foreign, f"precondition: the backup's database holds no trigger, view or virtual table, so lot B-28 lets it through: {foreign}"
    assert ("index", PENDING_TABLE) in {(kind, name) for kind, name, _sql in rows}, f"precondition: the backup carries the index named {PENDING_TABLE}"
    error, progress = refused(archive, instance)
    assert (error.code, progress.phases) == ("upgrade_failed", ["checking", "unpacking", "upgrading"]), f"alembic exited with an error: {error.code}, {progress.phases}"
    print_success("alembic failed on the copy: upgrade_failed, copy removed")


def clean_fixes(database, data_root) -> PostMigrationReport:
    return PostMigrationReport()


@pytest.mark.parametrize("found_by", ["post-migration-fixes", "verification"])
def test_an_upgrade_that_damages_the_copy_is_refused(instance, older_archive, monkeypatch, found_by):
    """(e) The copy fails its integrity check after the upgrade: the post-migration fixes check it first and fail
    (``post_migration_failed``); fixes that did not would leave it to the verification (``database_damaged``)."""

    def damaging_upgrade(database: Path) -> None:
        stamp_head(database)
        break_not_null(database, rows=1)

    monkeypatch.setattr(staging, "_upgrade", damaging_upgrade)
    if found_by == "verification":
        monkeypatch.setattr(staging, "run_post_migration_fixes", clean_fixes)
    error, progress = refused(older_archive.path, instance)
    expected = ("post_migration_failed", ["checking", "unpacking", "upgrading"]) if found_by == "post-migration-fixes" else ("database_damaged", PHASES)
    assert (error.code, progress.phases) == expected, f"found by the {found_by}: {error.code}, {progress.phases}"
    print_success(f"{found_by}: {error.code}")


@pytest.mark.parametrize("failure", ["a-fix-failed", "integrity"])
def test_a_post_migration_fix_that_fails_on_the_copy_refuses_the_archive(instance, head_archive, monkeypatch, failure):
    """(e) The fixes run on the copy, with the copy's data directory (a fix may move files of it), never the live one."""
    calls: list[tuple[Path, Path]] = []

    def failing_fixes(database, data_root) -> PostMigrationReport:
        calls.append((Path(database), Path(data_root)))
        if failure == "integrity":
            return PostMigrationReport(integrity_ok=False, errors=["integrity_check did not answer ok: no fix applied"])
        return PostMigrationReport(outcomes={"autoincrement": "failed"}, errors=["autoincrement: simulated failure"])

    monkeypatch.setattr(staging, "run_post_migration_fixes", failing_fixes)
    stage_id = new_stage_id()
    error, _progress = refused(head_archive.path, instance, stage_id=stage_id)
    data = stage_dir(instance.root, stage_id) / STAGE_DATA_FOLDER
    assert error.code == "post_migration_failed", f"{failure}: post_migration_failed, not {error.code}"
    assert calls == [(data / DATABASE_ENTRY, data)], f"the fixes ran once, on the copy and its data directory: {calls}"
    print_success(f"{failure}: post_migration_failed")


# =============================================================================
# (f) One check at a time
# =============================================================================


def hold_the_lock(root: Path) -> _RunLock:
    ensure_private_dir(stages_dir(root), root)
    lock = _RunLock(stages_dir(root) / STAGE_LOCK_FILE)
    assert lock.try_acquire(), "precondition: the lock is free"
    return lock


def test_while_the_lock_is_held_a_check_is_refused_and_creates_nothing(instance, head_archive):
    print_section("One check at a time")
    holder = hold_the_lock(instance.root)
    try:
        with pytest.raises(StagingBusyError):
            stage_archive(head_archive.path, instance.root)
        assert leftover_stages(instance.root) == [], f"a check refused as busy creates no stage: {leftover_stages(instance.root)}"
    finally:
        holder.release()
    assert stage_archive(head_archive.path, instance.root).restorable, "once the lock is released, the next check runs"
    print_success("busy while held, runs once released")


def test_a_check_holds_the_lock_from_its_start_to_its_end(instance, head_archive):
    """(f) A check in progress (held at its first ``unpacking`` progress) keeps any other out until it ends."""
    reached, release = threading.Event(), threading.Event()
    outcome: dict[str, object] = {}

    def gate(phase: str, done: int, total: int) -> None:
        if phase == "unpacking" and not reached.is_set():
            reached.set()
            assert release.wait(DEADLINE_S), "the test never let the first check go on"

    def first_check() -> None:
        try:
            outcome["report"] = stage_archive(head_archive.path, instance.root, progress=gate)
        except BaseException as exc:  # reported by the test, below
            outcome["error"] = exc

    thread = threading.Thread(target=first_check, name="staging-first-check", daemon=True)
    thread.start()
    try:
        assert reached.wait(DEADLINE_S), f"the first check never reached its unpacking: {outcome}"
        running = leftover_stages(instance.root)
        with pytest.raises(StagingBusyError):
            stage_archive(head_archive.path, instance.root)
        assert leftover_stages(instance.root) == running, f"the refused check created no stage of its own: {leftover_stages(instance.root)} besides {running}"
    finally:
        release.set()
        thread.join(DEADLINE_S)
    assert not thread.is_alive(), f"the first check did not end within {DEADLINE_S}s"
    assert "error" not in outcome, f"the first check failed: {outcome.get('error')!r}"
    assert [outcome["report"].stage_id] == running and lock_is_free(instance.root), "the first check ends with its own stage, and the lock is free"
    print_success("busy while another check runs")


def run_ending(ending: str, archive: BuiltArchive, root: Path, tmp_path: Path, **kwargs) -> None:
    """A check of ``ending``: a success, a refusal, or a stage id that is not one."""
    if ending == "success":
        assert stage_archive(archive.path, root, **kwargs).restorable, "a check that succeeds"
    elif ending == "refusal":
        with pytest.raises(StagingError):
            stage_archive(not_a_zip(tmp_path, archive, None), root, **kwargs)
    else:
        with pytest.raises(ValueError, match="not a restore stage id"):
            stage_archive(archive.path, root, stage_id="../" + "0" * 29, **kwargs)


ENDINGS = ["success", "refusal", "invalid-stage-id"]


@pytest.mark.parametrize("ending", ENDINGS)
def test_a_lock_the_caller_holds_stays_held_whatever_the_ending(instance, head_archive, tmp_path, ending):
    """(f) Lot B2b: the restore job takes the lock in the request and checks in a thread, passing the lock it holds. The
    check never releases it: the job does, once it has written the check's end, so that a reader who finds the lock free
    finds that end. Released by its holder, it is free again."""
    lock = hold_the_lock(instance.root)
    try:
        run_ending(ending, head_archive, instance.root, tmp_path, lock=lock)
        assert not lock_is_free(instance.root), f"{ending}: the lock given is still held, for its caller to release"
    finally:
        lock.release()
    assert lock_is_free(instance.root), f"{ending}: released by its holder, the lock is free"
    print_success(f"{ending}: kept for the caller")


@pytest.mark.parametrize("ending", ENDINGS)
def test_a_check_without_a_lock_takes_its_own_and_releases_it_whatever_the_ending(instance, head_archive, tmp_path, ending):
    """(f) The command line checks without a lock of its own: the check takes the lock, and lets it go at its end."""
    run_ending(ending, head_archive, instance.root, tmp_path)
    assert lock_is_free(instance.root), f"{ending}: the check's own lock is released"


# =============================================================================
# (g) Links
# =============================================================================


@needs_symlinks
@pytest.mark.parametrize("case", ["restore-is-a-link", "restore-is-a-dangling-link", "restore-is-a-file", "stage-is-a-link"])
def test_a_restore_folder_that_is_not_a_plain_folder_is_refused_and_never_written_through(instance, head_archive, tmp_path, case):
    """(g) ``BackupPathError`` naming the very folder (``.restore`` or ``.restore/stage``); nothing created through it."""
    print_section("Links")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    culprit = stages_dir(instance.root) if case == "stage-is-a-link" else restore_dir(instance.root)
    if case == "restore-is-a-link":
        culprit.symlink_to(elsewhere, target_is_directory=True)
    elif case == "restore-is-a-dangling-link":
        culprit.symlink_to(tmp_path / "nowhere", target_is_directory=True)
    elif case == "restore-is-a-file":
        culprit.write_bytes(b"not a folder")
    else:
        restore_dir(instance.root).mkdir()
        culprit.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(BackupPathError) as raised:
        stage_archive(head_archive.path, instance.root)
    assert raised.value.path == culprit, f"{case}: the error names {culprit}, not {raised.value.path}"
    assert list(elsewhere.iterdir()) == [], f"{case}: nothing may be created through the link: {listing(elsewhere)}"
    assert not (tmp_path / "nowhere").exists(), f"{case}: a dangling link is not made to point to a new folder"
    print_success(f"{case}: BackupPathError({culprit.name})")


@needs_symlinks
@pytest.mark.parametrize("taken_by", ["a-stage", "a-link"])
def test_an_existing_stage_is_never_written_over(instance, head_archive, tmp_path, taken_by):
    """(g) A stage id already taken, by a stage or by a link: refused, the stage and what the link points to unchanged."""
    elsewhere = tmp_path / "elsewhere"
    write_files(elsewhere, {STAGE_REPORT_FILE: b"{}"})
    ensure_private_dir(stages_dir(instance.root), instance.root)
    taken = stages_dir(instance.root) / VALID_ID
    if taken_by == "a-stage":
        write_files(taken, {STAGE_REPORT_FILE: b"the report of an earlier check"})
    else:
        taken.symlink_to(elsewhere, target_is_directory=True)
    before = (fingerprint(taken) if taken_by == "a-stage" else os.readlink(taken), fingerprint(elsewhere))
    with pytest.raises(FileExistsError):
        stage_archive(head_archive.path, instance.root, stage_id=VALID_ID)
    after = (fingerprint(taken) if taken_by == "a-stage" else os.readlink(taken), fingerprint(elsewhere))
    assert after == before and lock_is_free(instance.root), f"{taken_by}: nothing written over, the lock free"
    print_success(f"{taken_by}: FileExistsError, nothing written")


# =============================================================================
# (h) Progress
# =============================================================================


def test_the_progress_of_a_check_goes_from_checking_through_unpacking_to_verifying(instance, head_archive):
    """(h) Unpacking: from 0 to the total of the manifest's sizes, each entry's size at a time, in the manifest's order."""
    print_section("Progress")
    progress = Progress()
    stage_archive(head_archive.path, instance.root, progress=progress)
    sizes = [entry.size for entry in head_archive.manifest.files]
    assert progress.phases == ["checking", "unpacking", "verifying"], f"no upgrading at the head: {progress.phases}"
    unpacking = [(done, total) for phase, done, total in progress.events if phase == "unpacking"]
    assert {total for _done, total in unpacking} == {sum(sizes)}, f"one total, every entry's size: {unpacking}"
    dones = [done for done, _total in unpacking]
    assert dones[0] == 0 and dones[-1] == sum(sizes), f"from 0 to the total: {dones}"
    assert [later - earlier for earlier, later in zip(dones, dones[1:], strict=False)] == sizes, f"each step is the size of the entry just written: {dones}"
    print_success(f"{len(sizes)} entries, {sum(sizes)} bytes")


# =============================================================================
# (j) Warnings
# =============================================================================


def test_a_post_migration_fix_that_removes_rows_is_listed_and_warned(instance, databases, tmp_path):
    """(j) An asset event of a type the app does not know: the ``event_types`` fix deletes it from the copy, the report
    lists the fix, counts the rows before and after, and warns ``rows_changed``; the restore is not blocked."""
    print_section("Warnings")
    archive = from_head_database(
        tmp_path,
        databases,
        f"INSERT INTO assets (id, display_name, currency, asset_type, active, created_at, updated_at) VALUES (1, 'An asset', 'EUR', 'STOCK', 1, '{CREATED}', '{CREATED}')",
        f"INSERT INTO asset_events (asset_id, date, type, value, currency, created_at, updated_at) VALUES (1, '2026-10-01', 'NOT_A_KNOWN_TYPE', 1.5, 'EUR', '{CREATED}', '{CREATED}')",
    )
    report = stage_archive(archive, instance.root)
    assert (report.post_migration_fixes, report.warnings, report.restorable) == (["event_types"], ["rows_changed"], True), f"{report.post_migration_fixes}, {report.warnings}"
    assert report.tables["asset_events"] == TableRows(before=1, after=0), f"the event deleted from the copy: {report.tables['asset_events']}"
    assert [name for name, rows in report.tables.items() if rows.before != rows.after] == ["asset_events"], "no other table changed"
    print_success("event_types applied: asset_events 1 → 0, rows_changed")


def test_broken_references_of_the_backup_are_kept_and_warned(instance, databases, tmp_path):
    archive = from_head_database(tmp_path, databases, f"INSERT INTO user_settings (user_id, created_at, updated_at) VALUES (999, '{CREATED}', '{CREATED}')")
    report = stage_archive(archive, instance.root)
    assert (report.foreign_key_violations_before, report.foreign_key_violations_after) == (1, 1), "the backup's broken reference, kept as it is"
    assert (report.warnings, report.restorable) == (["foreign_key_violations"], True), f"a warning, not a blocker: {report.warnings}"
    print_success("1 broken reference kept: foreign_key_violations")


def test_broken_references_the_upgrade_adds_are_warned(instance, older_archive, monkeypatch):
    def upgrade_adding_a_broken_reference(database: Path) -> None:
        stamp_head(database)
        execute(database, f"INSERT INTO user_settings (user_id, created_at, updated_at) VALUES (999, '{CREATED}', '{CREATED}')")

    monkeypatch.setattr(staging, "_upgrade", upgrade_adding_a_broken_reference)
    report = stage_archive(older_archive.path, instance.root)
    assert (report.action, report.foreign_key_violations_before, report.foreign_key_violations_after) == ("upgrade", 0, 1), "a broken reference the upgrade added"
    assert report.warnings == ["rows_changed", "foreign_key_violations_added"], f"both warned, in this order: {report.warnings}"
    assert (report.tables["user_settings"], report.restorable) == (TableRows(before=0, after=1), True), f"{report.tables['user_settings']}"
    print_success("rows_changed, foreign_key_violations_added")


# =============================================================================
# (k) The ledger's control totals (lot B-13)
# =============================================================================


def test_a_ledger_as_the_backup_recorded_it_reads_the_same(instance, databases, tmp_path):
    """(k) The manifest records J's totals of the ledger the backup copied; at the head the copy is that very database,
    read again: ``same``, no difference, no warning; the report written with them."""
    print_section("The ledger's control totals")
    built = ledger_archive(tmp_path / "source", databases.head)
    recorded = recorded_totals(built.manifest)
    expected = control_totals(ledger_rows(tmp_path / "source" / "data" / DATABASE_ENTRY)).to_json()
    assert expected["cash"] and expected["quantities"], f"precondition: a ledger with cash and positions: {expected}"
    assert recorded == expected, f"the manifest records J's totals of the ledger: {recorded} != {expected}"
    report = stage_archive(built.path, instance.root)
    assert totals_in(report) == ("same", [], 0), f"the ledger as recorded: same, nothing listed: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == ([], [], True), f"nothing to warn, nothing blocking: {report.warnings}, {report.blockers}"
    assert read_report(instance.root, report.stage_id) == report, "report.json keeps the totals' verdict"
    print_success(f"same: {len(expected['cash'])} cash lines, {len(expected['quantities'])} positions")


def test_an_older_backup_upgraded_for_real_keeps_the_same_totals(upgraded):
    """(k) The real ``alembic upgrade`` of (c): the totals recorded at ``OLDER`` (made by this code) are those read on the
    copy after the upgrade, which leaves it in WAL mode: ``same``, no warning of the totals."""
    recorded = recorded_totals(upgraded.archive.manifest)
    assert isinstance(recorded, dict) and recorded.get("version") == CONTROL_TOTALS_VERSION, f"precondition: the backup at {OLDER} records its totals: {recorded}"
    assert totals_in(upgraded.report) == ("same", [], 0), f"upgraded to {HEAD}: same totals: {totals_in(upgraded.report)}"
    assert not [code for code in upgraded.report.warnings if code.startswith("control_totals")], f"no warning of the totals: {upgraded.report.warnings}"
    print_success(f"{OLDER} → {HEAD}: same")


def test_totals_rewritten_in_the_manifest_alone_are_changed_listed_and_warned(instance, databases, tmp_path):
    """(k) Only the manifest's totals are rewritten; every other entry is the archive's own, byte for byte, and the
    manifest is not in its own list of checksums: the check accepts the archive and only the totals tell. ``changed``,
    each difference in order (cash first, by broker, then currency or asset), J's canonical text, ``None`` where a line
    is absent; a warning, never a blocker; report.json keeps the differences."""
    built = ledger_archive(tmp_path / "source", databases.head)
    assert MANIFEST_ENTRY not in [entry.path for entry in built.manifest.files], f"precondition: the manifest lists every entry but itself: {[entry.path for entry in built.manifest.files]}"
    real = recorded_totals(built.manifest)
    assert isinstance(real, dict) and real["cash"] and real["quantities"], f"precondition: the totals of a ledger with cash and positions: {real}"
    first_cash, last_quantity = real["cash"][0], real["quantities"][-1]
    bumped = str(Decimal(first_cash["balance"]) + 1)
    recorded = {
        **real,
        "cash": [{**first_cash, "balance": bumped}, *real["cash"][1:], {"broker_id": 99, "currency": "SEK", "balance": "12"}],
        "quantities": real["quantities"][:-1],
    }
    archive = pack(tmp_path / "changed.zip", entries_of(built), manifest_with_totals(built, recorded))
    report = stage_archive(archive, instance.root)
    expected = [
        totals_difference("cash", first_cash["broker_id"], first_cash["currency"], bumped, first_cash["balance"]),
        totals_difference("cash", 99, "SEK", "12", None),
        totals_difference("quantity", last_quantity["broker_id"], last_quantity["asset_id"], None, last_quantity["quantity"]),
    ]
    assert totals_in(report) == ("changed", expected, 3), f"the three lines that differ, in order: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == (["control_totals_changed"], [], True), f"warned, not blocked: {report.warnings}, {report.blockers}"
    assert read_report(instance.root, report.stage_id) == report, "report.json keeps the differences"
    print_success(f"changed: {[(line['kind'], line['broker_id']) for line in expected]}")


def test_past_20_differences_a_report_keeps_the_first_20_and_counts_them_all(instance, head_archive, tmp_path):
    """(k) 25 cash lines recorded, none in the backup's empty ledger: the first 20 in order, 25 counted."""
    recorded = {"version": CONTROL_TOTALS_VERSION, "cash": [{"broker_id": 7, "currency": f"C{index:02d}", "balance": str(index + 1)} for index in range(25)], "quantities": []}
    report = stage_archive(pack(tmp_path / "many.zip", entries_of(head_archive), manifest_with_totals(head_archive, recorded)), instance.root)
    expected = [totals_difference("cash", 7, f"C{index:02d}", str(index + 1), None) for index in range(20)]
    assert totals_in(report) == ("changed", expected, 25), f"the first 20 of 25: {totals_in(report)}"
    print_success("20 listed, 25 counted")


#: What a manifest may record that is not a comparable total: (left out, the value recorded). §7.2: the field is ``Any``,
#: so a value of another type keeps the archive valid; §7.3: an amount that is not plain text is never read.
NOT_RECORDED = [
    pytest.param(True, None, id="left-out-a-backup-made-before"),
    pytest.param(False, None, id="null"),
    pytest.param(False, {"version": CONTROL_TOTALS_VERSION}, id="malformed-no-lines"),
    pytest.param(False, {"version": "1", "cash": [], "quantities": []}, id="a-version-that-is-not-an-int"),
    pytest.param(False, [{"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}], id="a-list"),
    pytest.param(False, "version 1", id="a-string"),
    pytest.param(False, 42, id="a-number"),
    pytest.param(False, {"version": CONTROL_TOTALS_VERSION, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "1E+3"}], "quantities": []}, id="an-amount-not-plain-text"),
]


@pytest.mark.parametrize(("drop", "recorded"), NOT_RECORDED)
def test_totals_a_manifest_does_not_record_are_absent_without_a_warning(instance, head_archive, tmp_path, drop, recorded):
    """(k) Nothing to compare: the archive is checked as usual, ``absent``, nothing listed, no warning. An archive
    without a manifest is not a backup (``not_a_backup``, (e); §7.7): what a backup made before lot B-13, or by hand, can
    lack or spoil is the field."""
    report = stage_archive(pack(tmp_path / "absent.zip", entries_of(head_archive), manifest_with_totals(head_archive, recorded, drop=drop)), instance.root)
    assert totals_in(report) == ("absent", [], 0), f"nothing comparable recorded: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == ([], [], True), f"no warning: {report.warnings}"
    print_success("absent")


def test_totals_recorded_otherwise_but_equal_read_the_same(instance, databases, tmp_path):
    """(k) §7.4: the lines in another order, an explicit zero line and amounts with trailing zeros, in an otherwise equal
    document: the lines are compared as maps, in J's canonical text, zero lines dropped: no difference, ``same``."""
    built = ledger_archive(tmp_path / "source", databases.head)
    real = recorded_totals(built.manifest)
    assert isinstance(real, dict) and len(real["cash"]) > 1 and len(real["quantities"]) > 1, f"precondition: several lines of each: {real}"
    first = real["cash"][0]
    recorded = {
        **real,
        "cash": [{**first, "balance": first["balance"] + ("0" if "." in first["balance"] else ".000")}, *real["cash"][:0:-1], {"broker_id": 3, "currency": "JPY", "balance": "0"}],
        "quantities": [{"broker_id": 2, "asset_id": 1, "quantity": "-0.0"}, *real["quantities"][::-1]],
    }
    report = stage_archive(pack(tmp_path / "otherwise.zip", entries_of(built), manifest_with_totals(built, recorded)), instance.root)
    assert totals_in(report) == ("same", [], 0), f"equal as maps: same: {totals_in(report)}"
    assert report.warnings == [], f"no warning: {report.warnings}"
    print_success("reordered, zero lines, trailing zeros: same")


def test_a_report_made_without_totals_says_absent():
    """(k) §7.6: ``_report`` without ``totals`` (as every call of this module's (j) makes it): ``absent``, nothing
    listed, no warning of the totals."""
    tables = {"users": 3}
    report = _report(VALID_ID, synthetic_manifest(tables), description(tables), description(tables), "same", [], HEAD, [], ADMINISTRATORS)
    assert totals_in(report) == ("absent", [], 0), f"no comparison given: absent: {totals_in(report)}"
    assert (report.warnings, report.blockers) == ([], []), f"nothing to warn: {report.warnings}"


#: (recorded, current, the status, the warning of the report): ``_report`` given each comparison.
REPORTED_COMPARISONS = [
    pytest.param({"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}, {"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}, "same", None, id="same"),
    pytest.param(
        {"version": CONTROL_TOTALS_VERSION, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "10"}], "quantities": [{"broker_id": 2, "asset_id": 3, "quantity": "1"}]},
        {"version": CONTROL_TOTALS_VERSION, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "12.5"}], "quantities": []},
        "changed",
        "control_totals_changed",
        id="changed",
    ),
    pytest.param({"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}, None, "unreadable", "control_totals_unreadable", id="unreadable"),
    pytest.param(None, {"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}, "absent", None, id="absent"),
    pytest.param({"version": 99}, None, "other_version", None, id="other-version"),
]


@pytest.mark.parametrize(("recorded", "current", "status", "warning"), REPORTED_COMPARISONS)
def test_a_report_carries_the_comparison_it_is_given(recorded, current, status, warning):
    """(k) §7.6: ``_report(..., totals=<TotalsComparison>)``: the status, each difference with its six fields, the count;
    a warning for ``changed`` and ``unreadable`` alone, never a blocker."""
    comparison = totals_module().compare_totals(recorded, current)
    assert comparison.status == status, f"precondition: {status}: {comparison.status}"
    tables = {"users": 3}
    report = _report(VALID_ID, synthetic_manifest(tables), description(tables), description(tables), "same", [], HEAD, [], ADMINISTRATORS, totals=comparison)
    differences = [totals_difference(line.kind, line.broker_id, line.currency if line.kind == "cash" else line.asset_id, line.before, line.after) for line in comparison.differences]
    assert totals_in(report) == (status, differences, comparison.differences_count), f"{status}: carried as given: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == ([warning] if warning else [], [], True), f"{status}: {report.warnings}, {report.blockers}"


def test_a_report_written_before_lot_b13_still_reads_its_totals_absent(instance, head_archive):
    """(k) §7.6: a ``report.json`` a check of before lot B-13 wrote (no field of the totals) is read, its totals
    ``absent``, nothing listed, everything else as written."""
    report = stage_archive(head_archive.path, instance.root)
    written = report.model_dump(mode="json")
    assert set(TOTALS_FIELDS) <= set(written), f"precondition: the report has the totals' fields: lot B-13 is not written yet: {sorted(written)}"
    old = {key: value for key, value in written.items() if key not in TOTALS_FIELDS}
    (stage_dir(instance.root, report.stage_id) / STAGE_REPORT_FILE).write_text(json.dumps(old, indent=2) + "\n", encoding="utf-8")
    read = read_report(instance.root, report.stage_id)
    assert totals_in(read) == ("absent", [], 0), f"a report of before: absent: {totals_in(read)}"
    assert read.model_dump(mode="json", exclude=set(TOTALS_FIELDS)) == old, "everything else as written"
    print_success("report.json of before B-13: read, absent")


def test_totals_of_another_version_of_the_method_are_not_compared(instance, head_archive, tmp_path):
    """(k) Version 99, of a shape this LibreFolio does not know: the manifest is read all the same (J's JSON is kept as
    it is), and the totals are not compared: ``other_version``, nothing listed, no warning."""
    recorded = {"version": 99, "lines": "of a method this LibreFolio does not know"}
    report = stage_archive(pack(tmp_path / "other.zip", entries_of(head_archive), manifest_with_totals(head_archive, recorded)), instance.root)
    assert totals_in(report) == ("other_version", [], 0), f"not comparable: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == ([], [], True), f"no warning: {report.warnings}"
    print_success("other_version")


def test_totals_that_cannot_be_read_on_the_copy_are_unreadable_and_warned(instance, head_archive, monkeypatch):
    """(k) ``ledger_totals_of`` answers ``None`` (it has logged why): ``unreadable``, warned, never blocking. It was asked
    once, for the copy's database, never for the live one."""
    recorded = recorded_totals(head_archive.manifest)
    assert recorded is not None, "precondition: the archive records its totals"
    asked: list[Path] = []

    def unreadable(database: Path) -> None:
        asked.append(Path(database).resolve())

    replace_ledger_totals(monkeypatch, unreadable)
    stage_id = new_stage_id()
    report = stage_archive(head_archive.path, instance.root, stage_id=stage_id)
    copy = (stage_dir(instance.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY).resolve()
    assert asked == [copy], f"read once, on the copy (never {instance.root / DATABASE_ENTRY}): {asked}"
    assert totals_in(report) == ("unreadable", [], 0), f"unreadable: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == (["control_totals_unreadable"], [], True), f"warned, not blocked: {report.warnings}"
    print_success("unreadable, warned")


#: A position of 1E+70 at broker 2 in asset 3, a pair no other row of ``LEDGER`` holds: stored as a double, which the
#: quantity column (``RealDecimal``) reads back as exactly 10^70; J adds it exactly, and its ``to_json`` writes it in
#: plain text, 71 digits, past the 60 its ``from_json`` reads back (B-29, E's R13-SEC2).
HUGE_POSITION = (2, 3, "ADJUSTMENT", "2026-08-01", "1e70", "0", None)


def test_totals_j_cannot_read_back_on_the_copy_are_unreadable_never_a_failed_check(instance, databases, tmp_path):
    """(k) B-29 (E's R13-SEC2): the backup's ledger holds ``HUGE_POSITION``, which J adds exactly and writes with 71
    digits that its own ``from_json`` refuses. The manifest's totals are rewritten without that line, so that J reads the
    recorded side and the copy's is the one it refuses: a backup LibreFolio makes of this ledger records the line too,
    and the recorded side, decided first, is then ``absent``. The check ends with its report: ``unreadable``, warned,
    never blocking, instead of the ``ValueError`` that ends it ``stage_failed``."""
    built = ledger_archive(tmp_path / "source", databases.head, rows=(*LEDGER, HUGE_POSITION))
    real = recorded_totals(built.manifest)
    huge = {"broker_id": 2, "asset_id": 3, "quantity": "1" + "0" * 70}
    assert isinstance(real, dict) and huge in real["quantities"], f"precondition: J adds 1E+70 exactly and writes it with 71 digits: {real}"
    with pytest.raises(ValueError):
        ControlTotals.from_json(real)
    recorded = {**real, "quantities": [line for line in real["quantities"] if line != huge]}
    assert ControlTotals.from_json(recorded).version == CONTROL_TOTALS_VERSION, "precondition: J reads the recorded totals, that line left out"
    archive = pack(tmp_path / "huge.zip", entries_of(built), manifest_with_totals(built, recorded))
    try:
        report = stage_archive(archive, instance.root)
    except Exception as exc:
        pytest.fail(f"the check ends with its report, the totals unreadable; it raised {type(exc).__name__}: {exc} (stage_failed through the API)")
    assert totals_in(report) == ("unreadable", [], 0), f"what J cannot read back on the copy: unreadable: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == (["control_totals_unreadable"], [], True), f"warned, not blocked: {report.warnings}, {report.blockers}"
    print_success("a position of 1E+70: unreadable, warned")


@pytest.mark.parametrize("status", ["changed", "unreadable"])
def test_the_totals_never_block_a_restore_nor_lift_a_blocker(instance, databases, tmp_path, monkeypatch, status):
    """(k) Without an active administrator, the restore stays blocked by that alone: the totals add their warning, never a
    blocker."""
    built = build_into(make_data_dir(tmp_path / "data", databases.head, accounts=WITHOUT_ADMINISTRATOR), tmp_path / "work")
    archive = built.path
    if status == "changed":
        recorded = {"version": CONTROL_TOTALS_VERSION, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "1"}], "quantities": []}
        archive = pack(tmp_path / "changed.zip", entries_of(built), manifest_with_totals(built, recorded))
    else:
        replace_ledger_totals(monkeypatch, lambda database: None)
    report = stage_archive(archive, instance.root)
    assert totals_in(report)[0] == status, f"precondition: {status}: {totals_in(report)}"
    assert (report.warnings, report.blockers, report.restorable) == ([f"control_totals_{status}"], ["no_administrator"], False), f"{status}: {report.warnings}, {report.blockers}"
    print_success(f"{status}: no_administrator alone blocks")


def test_the_totals_are_read_on_the_copy_after_its_upgrade(instance, databases, tmp_path, monkeypatch):
    """(k) An upgrade that moves a position (simulated, as in (c)): the difference is the upgrade's, so the totals were
    read after it."""
    built = ledger_archive(tmp_path / "source", databases.older)
    real = recorded_totals(built.manifest)
    assert isinstance(real, dict), f"precondition: the backup at {OLDER} records its totals: {real}"
    position_line = next(line for line in real["quantities"] if (line["broker_id"], line["asset_id"]) == (1, 3))

    def upgrade_moving_a_position(database: Path) -> None:
        stamp_head(database)
        execute(database, "UPDATE transactions SET quantity = quantity + 1 WHERE id = (SELECT min(id) FROM transactions WHERE broker_id = 1 AND asset_id = 3)")

    monkeypatch.setattr(staging, "_upgrade", upgrade_moving_a_position)
    report = stage_archive(built.path, instance.root)
    expected = [totals_difference("quantity", 1, 3, position_line["quantity"], str(Decimal(position_line["quantity"]) + 1))]
    assert report.action == "upgrade", f"precondition: an upgrade: {report.action}"
    assert totals_in(report) == ("changed", expected, 1), f"the position the upgrade moved: {totals_in(report)}"
    assert report.warnings == ["control_totals_changed"], f"warned: {report.warnings}"
    print_success(f"broker 1, asset 3: {expected[0]['before']} → {expected[0]['after']}")


def test_the_totals_are_read_on_the_copy_after_the_post_migration_fixes(instance, databases, tmp_path, monkeypatch):
    """(k) A fix that moves cash on the copy (simulated): the difference is the fix's, so the totals were read after
    the fixes."""
    built = ledger_archive(tmp_path / "source", databases.head)
    real = recorded_totals(built.manifest)
    assert isinstance(real, dict), f"precondition: the archive records its totals: {real}"
    cash_line = next(line for line in real["cash"] if (line["broker_id"], line["currency"]) == (2, "GBP"))

    def fix_moving_cash(database, data_root) -> PostMigrationReport:
        execute(database, "UPDATE transactions SET amount = amount - 2.5 WHERE id = (SELECT min(id) FROM transactions WHERE broker_id = 2 AND currency = 'GBP')")
        return PostMigrationReport(outcomes={"a_ledger_fix": "applied"})

    monkeypatch.setattr(staging, "run_post_migration_fixes", fix_moving_cash)
    report = stage_archive(built.path, instance.root)
    expected = [totals_difference("cash", 2, "GBP", cash_line["balance"], str(Decimal(cash_line["balance"]) - Decimal("2.5")))]
    assert report.post_migration_fixes == ["a_ledger_fix"], f"precondition: the fix ran on the copy: {report.post_migration_fixes}"
    assert totals_in(report) == ("changed", expected, 1), f"the cash the fix moved: {totals_in(report)}"
    print_success(f"broker 2, GBP: {expected[0]['before']} → {expected[0]['after']}")


def test_a_fix_that_reclassifies_lone_pair_halves_changes_no_total(instance, databases, tmp_path):
    """(k) For real: a received TRANSFER and a CASH_TRANSFER without their partners, as a deleted broker left them before
    1.3; ``orphan_pair_halves`` makes them an ADJUSTMENT and a WITHDRAWAL on the copy. J's totals do not depend on the
    type of a row: ``same``, so a restore of such a backup warns of nothing."""
    rows = (*LEDGER, (1, 3, "TRANSFER", "2026-08-01", "5", "0", None), (1, None, "CASH_TRANSFER", "2026-08-02", "0", "-20", "EUR"))
    built = ledger_archive(tmp_path / "source", databases.head, rows=rows)
    stage_id = new_stage_id()
    report = stage_archive(built.path, instance.root, stage_id=stage_id)
    copy = stage_dir(instance.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    assert report.post_migration_fixes == ["orphan_pair_halves"], f"precondition: the fix ran on the copy: {report.post_migration_fixes}"
    assert rows_of(copy, "SELECT type FROM transactions ORDER BY id DESC LIMIT 2") == [("WITHDRAWAL",), ("ADJUSTMENT",)], "precondition: both halves reclassified on the copy"
    assert totals_in(report) == ("same", [], 0), f"reclassified rows change no total: {totals_in(report)}"
    assert report.warnings == [], f"nothing to warn: {report.warnings}"
    print_success("orphan_pair_halves applied: same")


# =============================================================================
# (l) The database's own schema objects (lot B-28)
# =============================================================================
#
# An archive brings the schema of its database: SQLite builds every object from the SQL text of its row in
# ``sqlite_master``. LibreFolio's migrations create tables and indexes only, so a trigger, a view or a virtual table
# means a database LibreFolio did not make, or one changed since: the check refuses it before any of it can run. Every
# name written below holds ``UNTRUSTED``: a line of the log or a message that holds it names an object of the archive
# or quotes its SQL.

#: What every name of an object this section writes into a database holds: the archive's own text, untrusted.
UNTRUSTED = "b28_untrusted"
#: The one warning a refusal of foreign objects logs (§1 of the contract), with their count and their kinds.
FOREIGN_OBJECTS_EVENT = "A backup's database holds schema objects LibreFolio never creates"
#: Logged through ``staging``'s own logger before a check: the capture must see it, or «no line names an object» proves
#: nothing.
LOG_CANARY = "b28 staging test: a canary through staging's own logger"
#: ``PRAGMA trusted_schema=OFF`` however a check writes it: any case and spacing, ``OFF`` as ``0``, ``false`` or ``no``.
TRUSTED_SCHEMA_OFF = re.compile(r"\s*pragma\s+trusted_schema\s*(?:=\s*(?:off|0|false|no)|\(\s*(?:off|0|false|no)\s*\))\s*;?\s*", re.IGNORECASE)
#: How far a check goes before it refuses what the database of its copy holds: the copy must be written to be read.
UNPACKED = ["checking", "unpacking"]
#: The rows of a schema a restore lets through, read by their SQL: tables, indexes, the indexes SQLite makes (no SQL).
ALLOWED_KINDS = ("table", "index", "automatic index")
#: The keywords after ``CREATE`` and the kind they make, as §1 of the contract reads a row; anything else is ``other``.
_KEYWORD_KINDS = {("TABLE",): "table", ("INDEX",): "index", ("UNIQUE", "INDEX"): "index", ("TRIGGER",): "trigger", ("VIEW",): "view", ("VIRTUAL", "TABLE"): "virtual"}
#: What may stand between two keywords: spaces, ``-- …`` to the end of the line, ``/* … */`` (unclosed: to the end).
_SQL_GAP = re.compile(r"(?:\s+|--[^\n]*|/\*.*?(?:\*/|\Z))*", re.DOTALL)
_SQL_WORD = re.compile(r"[A-Za-z_]+")


@dataclass(frozen=True)
class SchemaObject:
    """An object LibreFolio never creates: its name, the SQL that makes it, its kind as the refusal counts it. Its row in
    ``sqlite_master``: ``row_type``, and the SQL itself, or ``stored`` when the test writes another text in its place
    through ``writable_schema`` (SQLite stores the text of what it creates in a form of its own)."""

    name: str
    sql: str
    row_type: str
    kind: str
    stored: str | None = None

    @property
    def row(self) -> tuple[str, str]:
        return self.row_type, self.stored or self.sql

    def add_to(self, database: Path) -> None:
        execute(database, self.sql)
        if self.stored is not None:
            rewrite_schema(database, "UPDATE sqlite_schema SET sql = ? WHERE name = ?", self.stored, self.name)


#: A trigger on an app table the check writes (the post-migration fixes, the rekey): it would make an account an
#: administrator of the restored instance.
TRIGGER = SchemaObject(
    name="b28_untrusted_promote",
    sql="CREATE TRIGGER b28_untrusted_promote AFTER UPDATE ON users BEGIN UPDATE users SET is_superuser = 1, is_active = 1 WHERE username = 'bob_user'; END",
    row_type="trigger",
    kind="trigger",
)
#: A view whose recursive CTE never ends: whatever read it would hold the lock of the checks until a restart.
ENDLESS_VIEW = SchemaObject(
    name="b28_untrusted_endless",
    sql="CREATE VIEW b28_untrusted_endless AS WITH RECURSIVE b28_untrusted_n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM b28_untrusted_n) SELECT i FROM b28_untrusted_n",
    row_type="view",
    kind="view",
)
#: An fts5 virtual table: code of its module runs whenever it is read. Its shadow tables are plain tables, let through.
VIRTUAL_TABLE = SchemaObject(name="b28_untrusted_search", sql="CREATE VIRTUAL TABLE b28_untrusted_search USING fts5(body)", row_type="table", kind="virtual")
_COMMENTED = "CREATE TRIGGER b28_untrusted_commented AFTER UPDATE ON users BEGIN UPDATE users SET is_superuser = 1 WHERE username = 'bob_user'; END"
#: A trigger whose SQL hides its kind behind a comment between the keywords. SQLite stores ``CREATE TRIGGER`` for any
#: trigger it creates, so the comment is written in its place through ``writable_schema``; SQLite loads it all the same.
COMMENTED_TRIGGER = SchemaObject(name="b28_untrusted_commented", sql=_COMMENTED, row_type="trigger", kind="trigger", stored=_COMMENTED.replace("CREATE TRIGGER", "CREATE/**/TRIGGER", 1))

FOREIGN_OBJECTS = [
    pytest.param((TRIGGER,), id="trigger"),
    pytest.param((ENDLESS_VIEW,), id="recursive-cte-view"),
    pytest.param((VIRTUAL_TABLE,), id="fts5-virtual-table"),
    pytest.param((COMMENTED_TRIGGER,), id="comment-between-the-keywords"),
    pytest.param((TRIGGER, ENDLESS_VIEW, VIRTUAL_TABLE, COMMENTED_TRIGGER), id="all-four-at-once"),
]


@dataclass(frozen=True)
class SchemaDamage:
    """A schema SQLite refuses to read. ``sql`` makes the object ``name`` before the backup; ``edit`` then changes its
    row, through ``writable_schema``, in the database of the archive. No backup is made of such a database (its
    snapshot's description fails: SQLite refuses the schema), so only a hand puts one in an archive."""

    name: str
    sql: str
    edit: str


#: A trigger whose row claims ``type = 'table'``, its rootpage left at 0 as SQLite wrote it. SQLite 3.54 then refuses
#: the whole schema («malformed database schema»), as for ``index`` or ``view`` and whatever the rootpage: a trigger
#: only loads as ``type = 'trigger'`` (revision 05:30 of the contract) — unless the connection turned
#: ``writable_schema`` on, as ``VACUUM`` does inside: then SQLite loads it, and it fires. Nothing of the app turns it on.
DISGUISED_TRIGGER = SchemaDamage(
    name="b28_untrusted_disguised",
    sql="CREATE TRIGGER b28_untrusted_disguised AFTER UPDATE ON users BEGIN UPDATE users SET is_superuser = 1 WHERE username = 'bob_user'; END",
    edit="UPDATE sqlite_schema SET type = 'table' WHERE name = 'b28_untrusted_disguised'",
)
#: A table whose SQL does not parse: its closing parenthesis gone.
UNPARSABLE = SchemaDamage(
    name="b28_untrusted_unparsable",
    sql="CREATE TABLE b28_untrusted_unparsable (body TEXT)",
    edit="UPDATE sqlite_schema SET sql = 'CREATE TABLE b28_untrusted_unparsable (body TEXT' WHERE name = 'b28_untrusted_unparsable'",
)

DAMAGED_SCHEMAS = [pytest.param(DISGUISED_TRIGGER, id="trigger-whose-row-claims-type-table"), pytest.param(UNPARSABLE, id="row-whose-sql-does-not-parse")]


def rewrite_schema(database: Path, statement: str, *parameters: object) -> None:
    """Run ``statement`` on ``sqlite_schema`` itself (``PRAGMA writable_schema``) and commit: what neither the app nor
    SQLite's own ``CREATE`` writes."""
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA writable_schema = ON")
        with conn:
            conn.execute(statement, parameters)


def database_of(archive: Path, target: Path) -> Path:
    """The database ``archive`` holds, written out at ``target``."""
    with zipfile.ZipFile(archive) as zf:
        target.write_bytes(zf.read(DATABASE_ENTRY))
    return target


def schema_rows(database: Path, names: set[str]) -> dict[str, tuple[str, str | None]]:
    """The rows of ``sqlite_master`` named in ``names``: their type and their SQL, by name."""
    return {name: (kind, sql) for kind, name, sql in rows_of(database, "SELECT type, name, sql FROM sqlite_master") if name in names}


def sqlite_refusal(database: Path) -> str:
    """What SQLite answers when the schema of ``database`` is read: its error, or nothing when it reads it."""
    try:
        rows_of(database, "SELECT name, sql FROM sqlite_master")
    except sqlite3.DatabaseError as exc:
        return str(exc)
    return ""


def archive_holding(tmp: Path, databases: Databases, objects: tuple[SchemaObject, ...]) -> Path:
    """A real backup of a data directory at the head whose database got ``objects`` before it was archived. Checked: the
    database of the archive keeps the row of each, as written."""
    data = make_data_dir(tmp / "data", databases.head)
    for item in objects:
        item.add_to(data / DATABASE_ENTRY)
    archive = build_into(data, tmp / "work").path
    held = schema_rows(database_of(archive, tmp / "archived.db"), {item.name for item in objects})
    assert held == {item.name: item.row for item in objects}, f"precondition: the backup carries every object as written: {held}"
    return archive


def archive_damaged_after_the_backup(tmp: Path, databases: Databases, damage: SchemaDamage) -> Path:
    """A real backup of a data directory at the head whose database got ``damage.sql``; then its database edited by
    ``damage.edit`` and put back in its place, the manifest listing its new bytes: only the database itself tells.
    Checked: SQLite refuses the edited schema, for that very row, on a connection as the app opens one."""
    data = make_data_dir(tmp / "data", databases.head)
    execute(data / DATABASE_ENTRY, damage.sql)
    built = build_into(data, tmp / "work")
    database = database_of(built.path, tmp / "edited.db")
    rewrite_schema(database, damage.edit)
    refusal = sqlite_refusal(database)
    assert refusal.startswith("malformed database schema") and damage.name in refusal, f"precondition: SQLite refuses the schema of the edited database, for {damage.name}: {refusal!r}"
    raw = database.read_bytes()
    entries = [replace(entry, data=raw) if entry.name == DATABASE_ENTRY else entry for entry in entries_of(built)]
    files = [listed(DATABASE_ENTRY, raw) if entry.path == DATABASE_ENTRY else entry for entry in built.manifest.files]
    return pack(tmp / "damaged.zip", entries, built.manifest.model_copy(update={"files": files}))


def never_described(patch: pytest.MonkeyPatch) -> list[Path]:
    """``describe_database`` as ``staging`` imports it, failing the test when a check reaches it: what the database of
    the copy holds is refused before anything else opens it (§1 of the contract). The calls, kept."""
    calls: list[Path] = []

    def describe(path: Path) -> DatabaseDescription:
        calls.append(Path(path))
        pytest.fail("describe_database (as staging imports it) ran on the copy: the check opened it before refusing what its database holds (B-28)")

    patch.setattr(staging, "describe_database", describe)
    return calls


@contextmanager
def staging_logs() -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block, behind a barrier: a warning through ``staging``'s own logger must reach the
    capture, or «no line names an object» would prove nothing either way."""
    with capture_logs() as events:
        staging.logger.warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: staging's logger does not reach capture_logs: {events}"
        yield events


def words_of(value: object) -> set[str]:
    """The words a logged value holds: the items of a list, a tuple or a set, the keys of a mapping, the words of a text."""
    if isinstance(value, str):
        return set(re.findall(r"[a-z]+", value.lower()))
    if isinstance(value, dict):
        return {str(key) for key in value}
    if isinstance(value, list | tuple | set | frozenset):
        return {str(item) for item in value}
    return set()


def leading_keywords(sql: str, count: int) -> list[str]:
    """The first ``count`` words of ``sql``, in capitals, spaces and comments skipped before each."""
    words: list[str] = []
    position = 0
    while len(words) < count:
        gap = _SQL_GAP.match(sql, position)
        word = _SQL_WORD.match(sql, gap.end() if gap else position)
        if word is None:
            break
        words.append(word.group().upper())
        position = word.end()
    return words


def schema_kind(sql: str | None) -> str:
    """The kind of a row of a schema, read by its SQL as SQLite builds it whatever its ``type`` says (§1 of the
    contract): ``table``, ``index``, ``automatic index`` (no SQL), or what a restore refuses: ``trigger``, ``view``,
    ``virtual``, ``other``."""
    if sql is None:
        return "automatic index"
    words = leading_keywords(sql, 3)
    if words[:1] == ["CREATE"]:
        for keywords, kind in _KEYWORD_KINDS.items():
            if tuple(words[1 : 1 + len(keywords)]) == keywords:
                return kind
    return "other"


def staging_function(name: str) -> Callable[..., Any]:
    """A function lot B-28 adds to ``staging``, looked up when a test needs it, never at collection: until it exists,
    each test that needs it fails on its own."""
    function = getattr(staging, name, None)
    if function is None:
        pytest.fail(f"[new] staging.{name} does not exist: lot B-28 is not written yet")
    return function


@dataclass
class Opened:
    """A connection opened through a lookup this section wraps: ``by`` the module that looked ``connect`` up
    (``staging``, ``snapshot`` or ``totals``), what it was asked to open and how, and every statement SQLite ran on it,
    in order, from its very first."""

    by: str
    target: str
    uri: bool
    statements: list[str] = field(default_factory=list)

    @property
    def path(self) -> Path:
        """The file it opened: a path, or a ``file:`` URI, its query left out and its escapes undone."""
        if self.target.startswith("file:"):
            return Path(unquote(urlsplit(self.target).path)).resolve()
        return Path(self.target).resolve()

    @property
    def opened_read_only(self) -> bool:
        """Opened as a ``file:`` URI with ``mode=ro``, read as a URI."""
        split = urlsplit(self.target)
        return self.uri and split.scheme == "file" and parse_qs(split.query).get("mode") == ["ro"]


def traced_connection(base: type[sqlite3.Connection], statements: list[str]) -> type[sqlite3.Connection]:
    """A connection class that puts every statement SQLite runs on it into ``statements``: the trace is set as the
    connection is made, before whoever opened it can run anything."""

    class Traced(base):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.set_trace_callback(statements.append)

    return Traced


class RecordingConnect:
    """``sqlite3`` or ``aiosqlite`` as a module of the product looks it up: ``connect`` records each connection it opens
    in ``opened``, traced; every other name is the module's own."""

    def __init__(self, module: ModuleType, by: str, opened: list[Opened]) -> None:
        self._module = module
        self._by = by
        self._opened = opened

    def __getattr__(self, name: str) -> Any:
        return getattr(self._module, name)

    def connect(self, database: Any, *args: Any, **kwargs: Any) -> Any:
        record = Opened(by=self._by, target=str(database), uri=bool(kwargs.get("uri")))
        self._opened.append(record)
        # aiosqlite hands its keywords to sqlite3.connect, in the thread that makes the connection.
        kwargs["factory"] = traced_connection(kwargs.get("factory", sqlite3.Connection), record.statements)
        return self._module.connect(database, *args, **kwargs)


def recorded_connections(patch: pytest.MonkeyPatch) -> list[Opened]:
    """Every connection opened through ``connect`` where ``staging``, ``snapshot`` and the post-migration fixes
    (``post_migration``, lot B-37) look up ``sqlite3`` and ``totals`` looks up ``aiosqlite``, in the order they open.
    The upgrade runs in a process of its own: not recorded here (``test_dev_cli_db_path.py`` reads its ``env.py``). The
    fixes' backup copy (a new ``.bak`` file beside the copy) is recorded too, and is no connection to the copy:
    ``on_the_copy`` leaves it out by its path."""
    opened: list[Opened] = []
    totals = totals_module()
    patch.setattr(staging, "sqlite3", RecordingConnect(sqlite3, "staging", opened))
    patch.setattr(snapshot, "sqlite3", RecordingConnect(sqlite3, "snapshot", opened))
    patch.setattr(post_migration, "sqlite3", RecordingConnect(sqlite3, "post_migration", opened))
    patch.setattr(totals, "aiosqlite", RecordingConnect(totals.aiosqlite, "totals", opened))
    return opened


def on_the_copy(opened: list[Opened], root: Path, stage_id: str) -> list[Opened]:
    """The connections opened on the database of the copy of stage ``stage_id``, in their order."""
    copy = (stage_dir(root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY).resolve()
    return [record for record in opened if record.path == copy]


def turns_trust_off_first(record: Opened) -> bool:
    """Whether ``PRAGMA trusted_schema=OFF`` is the first statement SQLite ran on the connection."""
    return bool(record.statements) and TRUSTED_SCHEMA_OFF.fullmatch(record.statements[0]) is not None


def first_statements(records: list[Opened]) -> list[tuple[str, list[str]]]:
    """Who opened each connection, and its first two statements: what a failure shows."""
    return [(record.by, record.statements[:2]) for record in records]


@pytest.mark.parametrize("objects", FOREIGN_OBJECTS)
def test_a_database_holding_what_librefolio_never_creates_is_refused_before_anything_else_opens_its_copy(instance, databases, tmp_path, monkeypatch, objects):
    """(l) §1 Refused once unpacked, before any other connection to the copy: ``describe_database`` (its integrity
    check, its counts), the upgrade, the fixes and all that follows never see it. Nothing of the copy left, the lock
    free, the archive unchanged; the message names no object and quotes no SQL."""
    print_section("B-28: the database's own schema objects")
    archive = archive_holding(tmp_path, databases, objects)
    original = sha256(archive.read_bytes())
    described = never_described(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert described == [], f"refused before describe_database opened the copy: {described}"
    assert (error.code, progress.phases) == ("database_foreign_objects", UNPACKED), f"refused for what the database holds, once unpacked: {error.code}, {progress.phases}: {error}"
    assert sha256(archive.read_bytes()) == original, "the archive is only read"
    assert UNTRUSTED not in str(error), f"the message names no object of the archive and quotes none of its SQL: {error}"
    print_success(f"{len(objects)} object(s), {sorted({item.kind for item in objects})}: database_foreign_objects")


@pytest.mark.parametrize("objects", FOREIGN_OBJECTS)
def test_the_refusal_warns_once_with_the_count_and_the_kinds_never_a_name_nor_its_sql(instance, databases, tmp_path, monkeypatch, objects):
    """(l) §1 One warning, «A backup's database holds schema objects LibreFolio never creates», with how many objects and
    their kinds (``trigger``, ``view``, ``virtual``, ``other``). Their names and their SQL are the archive's untrusted
    text: no line of the log holds them."""
    archive = archive_holding(tmp_path, databases, objects)
    never_described(monkeypatch)
    kinds = {item.kind for item in objects}
    with staging_logs() as events:
        error, _progress = refused(archive, instance)
    assert error.code == "database_foreign_objects", f"precondition: refused for what the database holds: {error.code}: {error}"
    lines = [event for event in events if event.get("event") != LOG_CANARY]
    warned = [event for event in lines if event.get("log_level") in ("warning", "error", "critical")]
    assert [(event.get("log_level"), event.get("event")) for event in warned] == [("warning", FOREIGN_OBJECTS_EVENT)], f"one warning, and only that one: {[(event.get('log_level'), event.get('event')) for event in lines]}"
    fields = {key: value for key, value in warned[0].items() if key not in ("event", "log_level")}
    assert any(type(value) is int and value == len(objects) for value in fields.values()), f"the warning gives the count, {len(objects)}: {fields}"
    assert any(words_of(value) == kinds for value in fields.values()), f"the warning gives the kinds, {sorted(kinds)}: {fields}"
    leaked = [event for event in lines if UNTRUSTED in repr(event)]
    assert not leaked, f"no line of the log names an object of the archive or quotes its SQL: {leaked}"
    print_success(f"warned: {len(objects)}, {sorted(kinds)}")


@pytest.mark.parametrize("damage", DAMAGED_SCHEMAS)
def test_a_schema_sqlite_refuses_to_read_is_refused_as_damaged_before_anything_else_opens_the_copy(instance, databases, tmp_path, monkeypatch, damage):
    """(l) §1 A ``sqlite3.DatabaseError`` while the schema is read: ``database_damaged``, the code of the integrity check,
    and still before any other connection to the copy. Nothing of the copy left, the lock free, the archive unchanged."""
    archive = archive_damaged_after_the_backup(tmp_path, databases, damage)
    original = sha256(archive.read_bytes())
    described = never_described(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert described == [], f"refused before describe_database opened the copy: {described}"
    assert (error.code, progress.phases) == ("database_damaged", UNPACKED), f"refused as damaged, once unpacked: {error.code}, {progress.phases}: {error}"
    assert sha256(archive.read_bytes()) == original, "the archive is only read"
    print_success(f"{damage.name}: database_damaged")


def test_this_librefolio_s_own_schema_holds_only_tables_and_indexes_which_the_refusal_lets_through(databases, tmp_path):
    """(l) The guard. Every row of the schema of the head made by alembic, read by its SQL as §1 reads it, is a table or
    an index, and ``_refuse_foreign_objects`` lets it through. The day a migration creates a trigger, a view or a virtual
    table, this test says so: no backup of that LibreFolio could be restored."""
    for item in (TRIGGER, ENDLESS_VIEW, VIRTUAL_TABLE, COMMENTED_TRIGGER):
        assert schema_kind(item.row[1]) == item.kind, f"precondition: this test reads {item.name} as a {item.kind}, not a {schema_kind(item.row[1])}"
    readings = [(sql, schema_kind(sql)) for sql in ("CREATE TABLE t (a)", "create  /* a */ unique -- b\n index i ON t (a)", "CREATE INDEX i ON t (a)", "CREATE TEMP TABLE t (a)", None)]
    assert [kind for _sql, kind in readings] == ["table", "index", "index", "other", "automatic index"], f"precondition: this test reads SQL as §1 does: {readings}"
    rows = rows_of(databases.head, "SELECT type, name, sql FROM sqlite_master ORDER BY rowid")
    foreign = [(schema_kind(sql), name) for _type, name, sql in rows if schema_kind(sql) not in ALLOWED_KINDS]
    assert rows and not foreign, f"this LibreFolio's own schema holds {foreign}: a migration created what a restore refuses as foreign, so no backup of this LibreFolio could be restored; staging._refuse_foreign_objects must learn the app's own objects (an allow-list) before that migration ships"
    copy = tmp_path / "head.db"
    shutil.copyfile(databases.head, copy)
    refuse = staging_function("_refuse_foreign_objects")
    try:
        refuse(copy)
    except StagingError as exc:
        pytest.fail(f"_refuse_foreign_objects refuses this LibreFolio's own schema ({exc.code}: {exc}): it must learn the app's own objects (an allow-list)")
    print_success(f"{len(rows)} rows of the head's schema: tables and indexes, let through")


def test_every_connection_a_check_opens_on_its_copy_turns_trusted_schema_off_before_anything_else(instance, older_archive, monkeypatch):
    """(l) §2 A whole check of an older backup, every phase run (its upgrade simulated, as in (c): the upgrade's own
    process is read in ``test_dev_cli_db_path.py``). Every connection opened on the copy where ``staging``,
    ``snapshot`` and the post-migration fixes (lot B-37) look up ``sqlite3`` and ``totals`` looks up ``aiosqlite`` runs
    ``PRAGMA trusted_schema=OFF`` before any other statement: the copy's schema (its views, triggers, checks, defaults)
    can reach no function or virtual table that is not harmless. Red before B-37: the fixes' connection begins with
    their integrity check."""
    opened = recorded_connections(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", stamp_head)
    stage_id = new_stage_id()
    progress = Progress()
    report = stage_archive(older_archive.path, instance.root, stage_id=stage_id, progress=progress)
    assert (report.action, progress.phases, report.control_totals) == ("upgrade", PHASES, "same"), f"precondition: a whole check, the totals read on the copy: {report.action}, {progress.phases}, {report.control_totals}"
    on_copy = on_the_copy(opened, instance.root, stage_id)
    silent = {"staging", "snapshot", "post_migration", "totals"} - {record.by for record in on_copy}
    assert not silent, f"precondition: each of the four opens the copy during a check, yet {sorted(silent)} opened nothing recorded: {first_statements(opened)}"
    trusting = [record for record in on_copy if not turns_trust_off_first(record)]
    assert not trusting, f"every connection to the copy turns trusted_schema off first: {len(trusting)} of {len(on_copy)} did not: {first_statements(trusting)}"
    print_success(f"{len(on_copy)} connections to the copy, each trusted_schema=OFF first")


def test_a_check_first_reads_the_schema_of_its_copy_read_only_and_runs_nothing_of_it(instance, head_archive, monkeypatch):
    """(l) §1 The first connection a check opens on its copy is ``staging``'s read of the schema: a ``file:`` URI with
    ``mode=ro``, ``trusted_schema`` off, then reads only. It runs no statement of the archive and writes nothing."""
    opened = recorded_connections(monkeypatch)
    stage_id = new_stage_id()
    report = stage_archive(head_archive.path, instance.root, stage_id=stage_id)
    on_copy = on_the_copy(opened, instance.root, stage_id)
    assert report.restorable and on_copy, f"precondition: a genuine archive checked, its copy opened: {report.blockers}, {first_statements(opened)}"
    first = on_copy[0]
    assert first.by == "staging", f"the first connection to the copy is staging's read of its schema, not {first.by}'s: {first_statements(on_copy)}"
    assert first.opened_read_only, f"read only: a file: URI with mode=ro, opened as a URI: {first.target!r}, uri={first.uri}"
    assert turns_trust_off_first(first) and all(statement.lstrip().upper().startswith("SELECT") for statement in first.statements[1:]), f"trusted_schema off, then reads only: {first.statements}"
    print_success(f"first on the copy: {first.statements}")


# =============================================================================
# (m) Lot B-35: a cap on what an archive unpacks to
# =============================================================================
#
# The upload limit bounds the compressed archive only; the check unpacks what the manifest declares (equal to the zip's
# headers). ``stage_archive(..., max_unpacked=)``, in bytes: the declared total above it is refused once the entries are
# checked, before the free space and before a byte is written.

#: What the check says of an archive whose files, unpacked, are more than this LibreFolio accepts (contract §2).
UNPACKED_TOO_LARGE = "unpacked_too_large"
UNPACKED_TOO_LARGE_MESSAGE = "Unpacked, the archive is larger than this LibreFolio accepts for a restore"
#: The password of (m)'s secure archive: a test's, not a secret.
B35_PASSWORD = "Correct-Horse-Battery-35"
#: Caps the module's head archive is within: one byte above its declared total, and the total itself.
CAPS = [pytest.param(1, id="cap-one-byte-above-the-total"), pytest.param(0, id="cap-equal-to-the-total")]
#: Caps it is over, from its declared total: one byte under it, and a cap of one byte in all.
OVER_THE_CAP = [pytest.param(lambda total: total - 1, id="cap-one-byte-under-the-total"), pytest.param(lambda total: 1, id="a-cap-of-one-byte")]


def b35_parameter() -> None:
    """``stage_archive`` takes ``max_unpacked``, which lot B-35 adds: each case of (m) asks it first."""
    assert "max_unpacked" in inspect.signature(stage_archive).parameters, "[new] stage_archive() has no parameter 'max_unpacked' yet: lot B-35 adds it (contract §2)"


def declared_total(archive: BuiltArchive) -> int:
    """What ``archive`` declares its files unpack to: the sum of its manifest's sizes, which the zip's headers equal."""
    return sum(entry.size for entry in archive.manifest.files)


def never_unpacked(patch: pytest.MonkeyPatch) -> list[tuple]:
    """``staging._unpack`` failing the test if a check reaches it: an archive refused for its size is refused before a
    byte of it is written (no ``data/``). The calls, kept."""
    calls: list[tuple] = []

    def unpack(*args: object) -> None:
        calls.append(args)
        pytest.fail("the archive was unpacked before its declared size was refused (B-35)")

    patch.setattr(staging, "_unpack", unpack)
    return calls


def no_room(patch: pytest.MonkeyPatch) -> list[object]:
    """``staging._check_space`` answering as a disk without room (``no_space``); the manifests it was asked about."""
    asked: list[object] = []

    def check_space(root: Path, manifest: object) -> None:
        asked.append(manifest)
        raise StagingError("no_space", "Not enough free space to check the archive")

    patch.setattr(staging, "_check_space", check_space)
    return asked


@pytest.mark.parametrize("margin", CAPS)
def test_an_archive_whose_files_unpack_to_the_cap_or_less_is_checked(instance, head_archive, margin):
    """(m) B-35 §2 The declared total under the cap, or equal to it: the check goes on as without one — unpacked,
    verified, restorable."""
    print_section("B-35: a cap on what an archive unpacks to")
    b35_parameter()
    progress = Progress()
    report = stage_archive(head_archive.path, instance.root, progress=progress, max_unpacked=declared_total(head_archive) + margin)
    assert (report.action, report.restorable, progress.phases) == ("same", True, ["checking", "unpacking", "verifying"]), f"checked as without a cap: {report.action}, {report.blockers}, {progress.phases}"
    print_success(f"cap {declared_total(head_archive) + margin} bytes for {declared_total(head_archive)}: checked")


@pytest.mark.parametrize("cap_of", OVER_THE_CAP)
def test_an_archive_whose_files_unpack_to_more_than_the_cap_is_refused_before_a_byte_is_written(instance, head_archive, monkeypatch, cap_of):
    """(m) B-35 §2 The declared total above the cap: ``StagingError`` ``unpacked_too_large`` in the contract's words,
    once the entries are checked and before any is written — never unpacked (no ``data/``), the progress never past
    ``checking``; the stage removed, the lock free, no path said, the archive only read."""
    b35_parameter()
    limit = cap_of(declared_total(head_archive))
    original = sha256(head_archive.path.read_bytes())
    unpacked = never_unpacked(monkeypatch)
    error, progress = refused(head_archive.path, instance, max_unpacked=limit)
    assert (error.code, str(error)) == (UNPACKED_TOO_LARGE, UNPACKED_TOO_LARGE_MESSAGE), f"{error.code}: {error}"
    assert (progress.phases, unpacked) == (["checking"], []), f"refused before a byte is written: {progress.phases}"
    assert sha256(head_archive.path.read_bytes()) == original, "the archive is only read"
    print_success(f"cap {limit} bytes for {declared_total(head_archive)}: unpacked_too_large")


def test_the_cap_is_checked_before_the_free_space(instance, head_archive, monkeypatch):
    """(m) B-35 §2 After the entries, before ``_check_space``: with no room on the disk, an archive over the cap is
    refused for its size, the free space never asked. The control: at the cap, the disk without room is what refuses it
    (``no_space``), so the stand-in is the one the check calls."""
    b35_parameter()
    asked = no_room(monkeypatch)
    error, progress = refused(head_archive.path, instance, max_unpacked=declared_total(head_archive) - 1)
    assert (error.code, progress.phases, asked) == (UNPACKED_TOO_LARGE, ["checking"], []), f"the cap first, the free space never asked: {error.code}, {progress.phases}, asked {len(asked)} times"
    control, _progress = refused(head_archive.path, instance, max_unpacked=declared_total(head_archive))
    assert (control.code, len(asked)) == ("no_space", 1), f"barrier: at the cap, the disk without room refuses it: {control.code}, asked {len(asked)} times"
    print_success("unpacked_too_large before no_space")


def test_a_secure_archive_is_decrypted_then_refused_the_same_way(instance, head_archive, tmp_path, monkeypatch):
    """(m) B-35 §2 A secure archive (the module's head archive in an envelope): decrypted first, then its declared total
    refused as a zip's — ``unpacked_too_large``, never unpacked, the stage (the decrypted archive with it) removed."""
    b35_parameter()
    secure = tmp_path / "head.lfbk"
    envelope.encrypt_file(head_archive.path, secure, B35_PASSWORD, log2_n=envelope.MIN_LOG2_N)
    unpacked = never_unpacked(monkeypatch)
    error, progress = refused(secure, instance, key=envelope.unlock(secure, B35_PASSWORD), max_unpacked=declared_total(head_archive) - 1)
    assert (error.code, progress.phases, unpacked) == (UNPACKED_TOO_LARGE, ["decrypting", "checking"], []), f"decrypted, then refused before a byte is written: {error.code}, {progress.phases}"
    print_success("decrypted, then unpacked_too_large")


def test_no_cap_is_today_s_check(instance, head_archive):
    """(m) B-35 §2 ``max_unpacked=None``: no limit, the check as it was before B-35."""
    b35_parameter()
    progress = Progress()
    report = stage_archive(head_archive.path, instance.root, progress=progress, max_unpacked=None)
    assert (report.action, report.restorable, progress.phases) == ("same", True, ["checking", "unpacking", "verifying"]), f"the check as before: {report.action}, {report.blockers}, {progress.phases}"
    print_success("no cap: checked as before")


# =============================================================================
# (n) Lot B-43: a function the reader lacks
# =============================================================================
#
# B-28 lets tables and indexes through by their kind, without reading their expressions: an index's expression, a
# generated column or a CHECK may call a function the connection that reads the copy does not have. SQLite loads such a
# schema all the same, and fails the first statement that needs the expression: «unknown function». An index or a
# generated column fails the integrity check of any connection, so the copy's first description raises; SQLite leaves a
# CHECK out of the schema of a read-only connection, so that description passes and the first read-write integrity
# check raises (the post-migration fixes'). Either way the check ends with ``database_damaged`` and removes its copy, as
# for any refusal — never with the raw ``sqlite3`` error (an API job's ``stage_failed``, a traceback on the command line)
# — and the function's name, the archive's text, is in no message and no line of the log.
#
# Part 1, the functions the server registers. Since H-51 the server's connections register ``regexp`` (2 arguments) and
# ``floor`` (1), deterministic and never innocuous (SQLAlchemy 2.0's pysqlite dialect, ``on_connect``), with
# ``trusted_schema`` off, and read the schema again: an index's expression or a generated column calling one cannot be
# read there («malformed database schema (…) - unsafe use of regexp()»), so every connection of a restored server fails.
# The check's plain readers pass such a schema (``regexp`` unknown to them and never computed in a virtual column without
# a declared type; ``floor`` built into SQLite): it must be refused where the copy's schema is first read, with the
# server's functions registered as stand-ins, before ``describe_database`` opens the copy. A CHECK or a DEFAULT calling
# them is resolved only when used, and reads: lot B-45's, not pinned here.

#: The function each schema of this section calls: registered on the one connection that builds its database, never on
#: a reader's. Its name is the archive's text (B-28's rule): no message and no line of the log may hold it.
B43_FUNCTION = "lf_b43_probe"
#: (Part 1) The functions the server's connections register, and their numbers of arguments: deterministic, never
#: innocuous. With ``trusted_schema`` off, a schema calling one in an index's expression or a generated column cannot
#: be read on such a connection.
SERVER_FUNCTIONS = (("regexp", 2), ("floor", 1))


@dataclass(frozen=True)
class FunctionCall:
    """An object of a schema that calls ``function``: ``statements`` make it, and its rows, on a connection where
    ``function`` is registered with ``registered`` arguments, answering 1 (``None``: SQLite has it built in);
    ``table``, the table it adds with one row (``None``: an index on a table of the app). Whether the ``PRAGMA
    integrity_check`` of a plain reader — no function registered, ``trusted_schema`` off as on every connection to a
    copy — fails: read only (the copy's descriptions), and read write (the post-migration fixes, the plugin secrets).
    ``unreadable_by_the_server``: whether a reader that registers ``SERVER_FUNCTIONS`` as the server's connections do
    cannot read the schema (part 1)."""

    name: str
    function: str
    registered: int | None
    statements: tuple[str, ...]
    table: str | None
    fails_read_only: bool
    fails_read_write: bool
    unreadable_by_the_server: bool = False


#: An index on an expression calling it, on a table of the app that has rows: ``users``, by its ``id``.
IN_AN_INDEX = FunctionCall(name="index-expression", function=B43_FUNCTION, registered=1, statements=(f"CREATE INDEX ix_b43 ON users ({B43_FUNCTION}(id))",), table=None, fails_read_only=True, fails_read_write=True)
#: A virtual generated column calling it, in a table of its own with one row.
IN_A_GENERATED_COLUMN = FunctionCall(
    name="generated-column",
    function=B43_FUNCTION,
    registered=1,
    statements=(f"CREATE TABLE b43_gen (x INTEGER, y INTEGER GENERATED ALWAYS AS ({B43_FUNCTION}(x)) VIRTUAL)", "INSERT INTO b43_gen (x) VALUES (1)"),
    table="b43_gen",
    fails_read_only=True,
    fails_read_write=True,
)
#: A CHECK calling it, in a table of its own with one row. Read only, SQLite leaves the CHECK out of the schema: the
#: copy's first description finds the database intact, and the first read-write integrity check fails.
IN_A_CHECK = FunctionCall(
    name="check-constraint",
    function=B43_FUNCTION,
    registered=1,
    statements=(f"CREATE TABLE b43_check (x INTEGER CHECK ({B43_FUNCTION}(x)))", "INSERT INTO b43_check (x) VALUES (1)"),
    table="b43_check",
    fails_read_only=False,
    fails_read_write=True,
)
#: The guard: a CHECK calling ``abs``, built in and innocuous, which every reader has, in a table of its own with one
#: row; the server's stand-ins read it too.
BUILT_IN_CHECK = FunctionCall(
    name="built-in-check",
    function="abs",
    registered=None,
    statements=("CREATE TABLE b43_builtin (x INTEGER CHECK (abs(x) >= 0))", "INSERT INTO b43_builtin (x) VALUES (-7)"),
    table="b43_builtin",
    fails_read_only=False,
    fails_read_write=False,
)
#: (Part 1) A virtual generated column calling ``regexp``, without a declared type, in a table of its own with one row:
#: no plain reader computes it (SQLite 3.54's integrity check computes a virtual column only when it declares a type),
#: so every plain reader passes it; the server's connections cannot read the schema.
REGEXP_IN_A_GENERATED_COLUMN = FunctionCall(
    name="regexp-in-a-generated-column",
    function="regexp",
    registered=2,
    statements=("CREATE TABLE b43_regexp (x TEXT, y GENERATED ALWAYS AS (regexp('a', x)) VIRTUAL)", "INSERT INTO b43_regexp (x) VALUES ('abc')"),
    table="b43_regexp",
    fails_read_only=False,
    fails_read_write=False,
    unreadable_by_the_server=True,
)
#: (Part 1) An index on ``floor()`` of a REAL column, in a table of its own with one row: SQLite's own ``floor()``, built
#: in and innocuous, serves every plain reader; the server's connections, which register their own, cannot read the
#: schema.
FLOOR_IN_AN_INDEX = FunctionCall(
    name="floor-in-an-index",
    function="floor",
    registered=None,
    statements=("CREATE TABLE b43_floor (x REAL)", "INSERT INTO b43_floor (x) VALUES (2.5)", "CREATE INDEX ix_b43_floor ON b43_floor (floor(x))"),
    table="b43_floor",
    fails_read_only=False,
    fails_read_write=False,
    unreadable_by_the_server=True,
)
#: The three calls a reader without the function cannot check.
LACKED_FUNCTION_CALLS = [pytest.param(call, id=call.name) for call in (IN_AN_INDEX, IN_A_GENERATED_COLUMN, IN_A_CHECK)]
#: (Part 1) The two calls every plain reader checks and the server cannot read.
SERVER_FUNCTION_CALLS = [pytest.param(call, id=call.name) for call in (REGEXP_IN_A_GENERATED_COLUMN, FLOOR_IN_AN_INDEX)]


def plain_integrity_error(database: Path, *, read_only: bool) -> sqlite3.DatabaseError | None:
    """The error ``PRAGMA integrity_check`` raises on ``database`` for a plain reader — no function registered,
    ``trusted_schema`` off as on every connection to a copy —; ``None`` when it answers. Run on a scratch copy of the
    file, read only or read write: ``database`` stays as it is."""
    scratch = database.with_name(f"{database.name}.{'read-only' if read_only else 'read-write'}")
    shutil.copyfile(database, scratch)
    try:
        with closing(sqlite3.connect(f"{scratch.resolve().as_uri()}?mode={'ro' if read_only else 'rw'}", uri=True)) as conn:
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.DatabaseError as exc:
        return exc
    return None


def never_run(*values: object) -> object:
    """A stand-in of one of the server's functions: registered so that a schema calling it cannot be read, never run."""
    raise AssertionError("a stand-in of the server's functions ran: reading a schema computes none of its expressions")


def server_schema_error(database: Path) -> sqlite3.DatabaseError | None:
    """(Part 1) The error reading the schema of ``database`` raises on a reader that registers ``SERVER_FUNCTIONS`` as the
    server's connections do — stand-ins, deterministic, never run — ``trusted_schema`` off, read only; ``None`` when it
    reads it. ``database`` stays as it is."""
    try:
        with closing(read_only(database)) as conn:
            conn.execute("PRAGMA trusted_schema=OFF")
            for name, arguments in SERVER_FUNCTIONS:
                conn.create_function(name, arguments, never_run, deterministic=True)
            conn.execute("SELECT sql FROM sqlite_master").fetchall()
    except sqlite3.DatabaseError as exc:
        return exc
    return None


def error_met_first(database: Path, call: FunctionCall) -> sqlite3.DatabaseError | None:
    """The error the check meets first on a copy of ``database``, as ``call`` says: the read of its schema with the
    server's stand-ins (part 1); else the integrity check of a plain reader, read only (the copy's first description),
    or read write (the post-migration fixes) when only that fails."""
    if call.unreadable_by_the_server:
        return server_schema_error(database)
    return plain_integrity_error(database, read_only=call.fails_read_only)


def archive_calling(tmp: Path, database: Path, call: FunctionCall) -> Path:
    """A real backup of a data directory made from ``database`` (at the head: no upgrade runs), whose database then got
    ``call``'s object, trusted, on the one connection where ``call.function`` is registered (unless SQLite has it built
    in), and was put back in its place, the manifest listing its new bytes and its tables: only the database itself
    tells. Added after the backup: the snapshot's ``VACUUM INTO`` fails on a schema calling a function its connection
    lacks («no such function»), so only a hand puts such a database in an archive (a built-in one, ``floor``, takes the
    same road). Checked: intact for a reader that has the function, nothing beside it; its tables the backup's, plus
    ``call.table`` with its row; the integrity check of a plain reader failing as ``call`` says, and the read of its
    schema with the server's stand-ins too (part 1); each error naming the function (so that a log of its message would
    leak it). Also the command line's tests' (``test_backup_cli_restore.py``)."""
    data = make_data_dir(tmp / "data", database)
    built = build_into(data, tmp / "work")
    edited = database_of(built.path, tmp / "b43.db")
    with closing(sqlite3.connect(edited)) as conn:
        # Trusted, as SQLite opens a database by default: untrusted, a schema may not call a function that is not innocuous.
        conn.execute("PRAGMA trusted_schema=ON")
        if call.registered is not None:
            conn.create_function(call.function, call.registered, lambda *values: 1, deterministic=True)
        with conn:
            for statement in call.statements:
                conn.execute(statement)
        intact = conn.execute("PRAGMA integrity_check").fetchall()
        names = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        tables = {name: conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in names}
    assert (intact, side_files(edited)) == ([("ok",)], []), f"precondition: {call.name}: intact for a reader that has the function, nothing beside it: {intact}, {side_files(edited)}"
    added = {call.table: 1} if call.table else {}
    assert tables == built.manifest.database.tables | added, f"precondition: {call.name}: the tables of the backup, plus {added}: {tables}"
    errors = {mode: plain_integrity_error(edited, read_only=mode == "read-only") for mode in ("read-only", "read-write")}
    failing = {mode: error is not None for mode, error in errors.items()}
    assert failing == {"read-only": call.fails_read_only, "read-write": call.fails_read_write}, f"precondition: {call.name}: a plain reader fails its integrity check as the case says: {errors}"
    errors["server"] = server_schema_error(edited)
    assert (errors["server"] is not None) == call.unreadable_by_the_server, f"precondition: {call.name}: a reader with the server's stand-ins reads the schema as the case says (unreadable: {call.unreadable_by_the_server}): {errors['server']!r}"
    unnamed = {mode: repr(error) for mode, error in errors.items() if error is not None and call.function not in str(error)}
    assert not unnamed, f"precondition: {call.name}: SQLite's error names the function, so that a log of its message would leak it: {unnamed}"
    raw = edited.read_bytes()
    entries = [replace(entry, data=raw) if entry.name == DATABASE_ENTRY else entry for entry in entries_of(built)]
    files = [listed(DATABASE_ENTRY, raw) if entry.path == DATABASE_ENTRY else entry for entry in built.manifest.files]
    manifest_database = built.manifest.database.model_copy(update={"tables": tables})
    return pack(tmp / "b43.zip", entries, built.manifest.model_copy(update={"files": files, "database": manifest_database}))


def recorded_descriptions(patch: pytest.MonkeyPatch) -> list[str]:
    """``describe_database`` as ``staging`` imports it, the real one, what each call answered kept in order: the
    integrity check it found, or ``raised`` (and it raises again what it raised)."""
    answers: list[str] = []
    real = staging.describe_database

    def describe(path: Path) -> DatabaseDescription:
        try:
            description = real(path)
        except BaseException:
            answers.append("raised")
            raise
        answers.append(description.integrity_check)
        return description

    patch.setattr(staging, "describe_database", describe)
    return answers


@pytest.mark.parametrize("call", LACKED_FUNCTION_CALLS)
def test_a_function_the_reader_lacks_ends_the_check_as_database_damaged_never_a_raw_sqlite3_error(instance, databases, tmp_path, monkeypatch, call):
    """(n) B-43 An index's expression, a generated column or a CHECK calling a function this LibreFolio does not have:
    ``StagingError`` ``database_damaged`` once unpacked, as for a database that fails its integrity check (red before
    B-43: the ``sqlite3.OperationalError`` «unknown function» escapes the check, an API job's ``stage_failed``). Nothing
    of the copy left, the lock free, the archive only read, the live data directory untouched; the message names no path
    and not the function."""
    print_section("B-43: a function the reader lacks")
    archive = archive_calling(tmp_path, databases.head, call)
    original = sha256(archive.read_bytes())
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert (error.code, progress.phases) == ("database_damaged", UNPACKED), f"{call.name}: refused as damaged, once unpacked: {error.code}, {progress.phases}: {error}"
    assert call.function not in str(error), f"{call.name}: the message names no function of the archive: {error}"
    assert sha256(archive.read_bytes()) == original, f"{call.name}: the archive is only read"
    after = fingerprint(instance.root)
    assert after == instance.before, f"{call.name}: the live data directory changed: {changed(instance.before, after)}"
    print_success(f"{call.name}: database_damaged, nothing left")


def test_a_check_calling_a_function_the_reader_lacks_passes_the_read_only_description_and_is_refused_after_it(instance, databases, tmp_path, monkeypatch):
    """(n) B-43 The barrier: ``describe_database`` of that very database, read only, finds it intact — SQLite leaves the
    CHECK out of the schema of a read-only connection — at the head, its tables those of its manifest. The check's own
    first description of its copy answers the same; the refusal comes after it, from a read-write step that meets the
    function: ``database_damaged``, the copy removed (red before B-43: the raw ``sqlite3.OperationalError`` of the
    post-migration fixes' integrity check)."""
    archive = archive_calling(tmp_path, databases.head, IN_A_CHECK)
    with zipfile.ZipFile(archive) as zf:
        manifest = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
    described = snapshot.describe_database(database_of(archive, tmp_path / "b43-described.db"))
    found = (described.integrity_check, described.alembic_revision, described.tables)
    assert found == ("ok", HEAD, manifest.database.tables), f"barrier: read only, the database is intact, at the head, its tables its manifest's: {found}"
    answers = recorded_descriptions(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, _progress = refused(archive, instance)
    assert error.code == "database_damaged", f"refused as damaged: {error.code}: {error}"
    assert answers == ["ok"], f"the check's first description of its copy found it intact too, and the refusal came after it, from a read-write step: {answers}"
    print_success("CHECK: described intact read only, then database_damaged")


@pytest.mark.parametrize("call", [*LACKED_FUNCTION_CALLS, *SERVER_FUNCTION_CALLS])
def test_the_refusal_warns_with_the_error_s_class_and_sqlite_name_never_the_function_s_name(instance, databases, tmp_path, monkeypatch, call):
    """(n) B-43 One warning, with the class of the ``sqlite3`` error the check met and SQLite's name for it
    (``sqlite_errorname``), never its message, which names the function: the archive's text (B-28's rule). No line of
    the log holds the function's name. The error expected is the one SQLite raises for a plain reader, first read only
    (the index, the column), else read write (the CHECK); for a function the server registers (part 1), the one the read
    of the schema with the server's stand-ins raises (red before part 1: nothing refuses those)."""
    archive = archive_calling(tmp_path, databases.head, call)
    met = error_met_first(database_of(archive, tmp_path / "b43-probed.db"), call)
    assert met is not None and call.function in str(met), f"precondition: {call.name}: the error the check meets first names the function, so that a log of its message would leak it: {met!r}"
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    with staging_logs() as events:
        error, _progress = refused(archive, instance)
    assert error.code == "database_damaged", f"precondition: {call.name}: refused as damaged: {error.code}: {error}"
    lines = [event for event in events if event.get("event") != LOG_CANARY]
    leaked = [event for event in lines if call.function in repr(event)]
    assert not leaked, f"{call.name}: no line of the log names the function of the archive: {leaked}"
    warned = [event for event in lines if event.get("log_level") in ("warning", "error", "critical")]
    assert [event.get("log_level") for event in warned] == ["warning"], f"{call.name}: one warning, and only that one: {[(event.get('log_level'), event.get('event')) for event in lines]}"
    fields = {key: value for key, value in warned[0].items() if key not in ("event", "log_level")}
    assert any(type(met).__name__ in str(value) for value in fields.values()), f"{call.name}: the warning gives the error's class, {type(met).__name__}: {fields}"
    assert any(str(value) == met.sqlite_errorname for value in fields.values()), f"{call.name}: and SQLite's name for it, {met.sqlite_errorname}: {fields}"
    print_success(f"{call.name}: warned {type(met).__name__}, {met.sqlite_errorname}; no function named")


def test_a_check_calling_a_built_in_function_is_checked_as_usual(instance, databases, tmp_path, monkeypatch):
    """(n) B-43, the guard (green before and after): a CHECK calling ``abs``, built in and innocuous, which every reader
    has, in a table of its own, built and put in the archive as the cases above: checked as any backup at the head,
    read only and read write with ``trusted_schema`` off — restorable, its table with its row before and after."""
    archive = archive_calling(tmp_path, databases.head, BUILT_IN_CHECK)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    report = stage_archive(archive, instance.root)
    copy = stage_dir(instance.root, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    kept = rows_of(copy, f"SELECT sql FROM sqlite_master WHERE name = '{BUILT_IN_CHECK.table}'")
    assert kept and "CHECK (abs(x) >= 0)" in kept[0][0], f"precondition: the copy keeps the CHECK: {kept}"
    assert (report.action, report.migrations, report.post_migration_fixes) == ("same", [], []), f"at the head: nothing to upgrade, nothing to fix: {report.action}, {report.migrations}, {report.post_migration_fixes}"
    assert report.tables[BUILT_IN_CHECK.table] == TableRows(before=1, after=1), f"its table, with its row before and after: {report.tables.get(BUILT_IN_CHECK.table)}"
    assert (report.warnings, report.blockers, report.restorable, report.administrators) == ([], [], True, ADMINISTRATORS), f"nothing to warn, restorable: {report.warnings}, {report.blockers}, {report.administrators}"
    print_success("abs() in a CHECK: same, restorable")


# -----------------------------------------------------------------------------
# (n) B-43, part 1: the functions the server registers
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("call", SERVER_FUNCTION_CALLS)
def test_a_function_the_server_registers_in_an_index_or_a_generated_column_is_refused_before_anything_else_opens_the_copy(instance, databases, tmp_path, monkeypatch, call):
    """(n) B-43, part 1: ``regexp`` in a virtual generated column, ``floor`` in an index's expression. Every plain reader
    of the check passes them, the server's connections cannot read the schema: restored, the instance would fail every
    connection. Refused ``database_damaged`` where the copy's schema is first read, with the server's functions as
    stand-ins, before ``describe_database`` opens the copy, as (l)§1 refuses what LibreFolio never creates (red before
    part 1: nothing refuses it, and ``describe_database`` opens the copy). Nothing of the copy left, the lock free, the
    archive only read, the live data directory untouched; the message names no path and not the function."""
    print_section("B-43, part 1: a function the server registers")
    archive = archive_calling(tmp_path, databases.head, call)
    original = sha256(archive.read_bytes())
    described = never_described(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert described == [], f"{call.name}: refused before describe_database opened the copy: {described}"
    assert (error.code, progress.phases) == ("database_damaged", UNPACKED), f"{call.name}: refused as damaged, once unpacked: {error.code}, {progress.phases}: {error}"
    assert call.function not in str(error), f"{call.name}: the message names no function of the archive: {error}"
    assert sha256(archive.read_bytes()) == original, f"{call.name}: the archive is only read"
    after = fingerprint(instance.root)
    assert after == instance.before, f"{call.name}: the live data directory changed: {changed(instance.before, after)}"
    print_success(f"{call.name}: database_damaged before describe_database, nothing left")


#: (Part 1) This LibreFolio's own index on an expression (revision ``009_email_unique_ignoring_case``).
OWN_LOWER_INDEX = "ux_users_email_lower"


def test_this_librefolio_s_own_index_on_lower_reads_with_the_server_s_functions_and_its_backup_checks_as_usual(instance, databases, head_archive):
    """(n) B-43, part 1, the guard (green before and after): the head made by alembic indexes an expression,
    ``ux_users_email_lower`` on ``lower(email)``: SQLite's own ``lower()``, built in and innocuous, never one of the
    server's stand-ins. A reader that registers them reads this schema, and the module's head archive checks as a
    backup at the head, restorable, as in (b): the stand-ins are the server's functions, not every function a schema
    calls."""
    own = rows_of(databases.head, f"SELECT sql FROM sqlite_master WHERE type = 'index' AND name = '{OWN_LOWER_INDEX}'")
    assert own and re.search(r"\(\s*lower\s*\(\s*email\s*\)\s*\)", own[0][0], re.IGNORECASE), f"precondition: this LibreFolio's own schema indexes lower(email) as {OWN_LOWER_INDEX}: {own}"
    error = server_schema_error(databases.head)
    assert error is None, f"a reader with the server's stand-ins reads this LibreFolio's own schema: {error!r}"
    report = stage_archive(head_archive.path, instance.root)
    assert (report.action, report.warnings, report.blockers, report.restorable) == ("same", [], [], True), f"the head archive checks as a backup at the head, restorable: {report.action}, {report.warnings}, {report.blockers}"
    print_success(f"{OWN_LOWER_INDEX} on lower(email): read with the stand-ins, the head archive restorable")


# =============================================================================
# (o) Lot B-49: text that is not UTF-8
# =============================================================================
#
# SQLite keeps as TEXT whatever bytes a statement hands it (a ``CAST`` of a blob; a crafted archive) and checks no
# encoding: ``PRAGMA integrity_check`` passes such a database, and nothing of the check reads most of its columns. Once
# restored, every ``select`` of that table fails in the server: ``sqlite3`` cannot decode the value, and its
# ``OperationalError`` quotes the archive's bytes («Could not decode to UTF-8 column … with text …»). A check reads
# every text value of its copy — every table but SQLite's own, those LibreFolio does not have too; by storage class, so
# the text of a DATE column counts and a BLOB does not — on a connection of its own (``mode=ro``, ``trusted_schema``
# off first), once the copy is found to be the database its manifest describes and before anything writes in it, and
# refuses an archive holding any text that is not UTF-8: ``database_damaged``, with a message of its own. One warning
# gives how many tables hold such text, and nothing else. Every text this section stores that is not UTF-8 holds
# ``B49_MARKER``, every name it gives a table or a column ``B49_UNTRUSTED``: a line of the log or a message that holds
# one of them quotes the archive's text or names its tables.

#: The refusal of a copy holding text that is not UTF-8 (B-49): B-43's code, the contract's message.
UNDECODABLE_CODE = "database_damaged"
UNDECODABLE_MESSAGE = "The backup's database holds text that is not UTF-8: it cannot be restored"
#: The one warning the refusal logs (B-49): its only payload, the number of tables holding such text.
UNDECODABLE_EVENT = "A backup's database holds text that is not UTF-8"
#: What every text that is not UTF-8 this section stores holds: the archive's own text.
B49_MARKER = "b49-archive-text"
#: What every name this section gives a table or a column holds: the archive's own names.
B49_UNTRUSTED = "b49_untrusted"
#: A text that is not UTF-8: 0xff, a byte UTF-8 never uses, between two letters, then the marker. SQLite keeps it as
#: TEXT (a ``CAST`` of its bytes); ``sqlite3`` cannot read it back as text, and its error quotes it, 0xff as U+FFFD.
NOT_UTF8 = b"E\xffR " + B49_MARKER.encode()
#: Valid UTF-8 beyond ASCII: characters of two bytes (é), three (日本) and four (💶, an emoji; 𝄞, a musical symbol).
VALID_TEXT = "Caf\u00e9 \u65e5\u672c \U0001f4b6 \U0001d11e"
VALID_UTF8 = VALID_TEXT.encode("utf-8")
#: What no line of the log may hold: the text (its marker; its 0xff as sqlite3 quotes it, as Python escapes it or names
#: it, as Latin-1 decodes it; in hex), the words of sqlite3's error and of Python's decoder, and the archive's names.
UNDECODABLE_FRAGMENTS = (B49_MARKER, "E\ufffdR", "\ufffd", "\\xff", "0xff", "\xff", "45ff52", "45FF52", "Could not decode", "with text", "can't decode", "invalid start byte", B49_UNTRUSTED)
#: A statement that reads values by their storage class, as B-49's read does: ``typeof(`` and ``'text'``, whatever the
#: case, the spacing or the form of the comparison. No exact SQL is pinned.
TEXT_BY_STORAGE_CLASS = (re.compile(r"\btypeof\s*\(", re.IGNORECASE), re.compile(r"'text'", re.IGNORECASE))


def sql_name(name: str) -> str:
    """``name`` as an SQL identifier: in double quotes, a quote it holds doubled."""
    return '"' + name.replace('"', '""') + '"'


def text_sql(raw: bytes) -> str:
    """The SQL of a TEXT value made of the bytes ``raw`` as they are: SQLite checks no encoding."""
    return f"CAST(x'{raw.hex()}' AS TEXT)"


def blob_sql(raw: bytes) -> str:
    """The SQL of a BLOB made of the bytes ``raw``."""
    return f"x'{raw.hex()}'"


def stored_bytes(database: Path, sql: str) -> list[tuple]:
    """What ``sql`` reads of ``database``, read only, every text as its bytes: a text that is not UTF-8 included."""
    with closing(read_only(database)) as conn:
        conn.text_factory = bytes
        return conn.execute(sql).fetchall()


@dataclass(frozen=True)
class TextPlace:
    """Where this section stores a value: ``column`` of ``table``. ``store(value)``, the statements storing the SQL
    expression ``value`` there, in ``rows`` rows; ``read``, the query reading back the storage class and the value of
    each, in order."""

    name: str
    table: str
    column: str
    rows: int
    store: Callable[[str], tuple[str, ...]]
    read: str


#: A TEXT column of the app, which every ``select`` of its model reads: ``transactions.description``, in the two rows of
#: a broker of their own. Nothing of today's check reads it: the control totals read eight other columns.
IN_A_TEXT_COLUMN = TextPlace(
    name="transactions.description",
    table="transactions",
    column="description",
    rows=2,
    store=lambda value: (
        f"INSERT INTO brokers (id, name, created_at, updated_at) VALUES (49, 'Broker B-49', '{CREATED}', '{CREATED}')",
        f"INSERT INTO transactions (broker_id, type, date, quantity, amount, currency, description, created_at, updated_at) VALUES (49, 'DEPOSIT', '2026-01-02', 0, 100, 'EUR', {value}, '{CREATED}', '{CREATED}')",
        f"INSERT INTO transactions (broker_id, type, date, quantity, amount, currency, description, created_at, updated_at) VALUES (49, 'WITHDRAWAL', '2026-01-03', 0, -40, 'EUR', {value}, '{CREATED}', '{CREATED}')",
    ),
    read="SELECT typeof(description), description FROM transactions WHERE broker_id = 49 ORDER BY id",
)
#: A DATE column of the app: ``fx_rates.date``, whose NUMERIC affinity keeps a text that is no number as TEXT; read by
#: storage class, it counts. Nothing of today's check reads it: the currency audit reads ``base`` and ``quote``.
IN_A_DATE_COLUMN = TextPlace(
    name="fx_rates.date",
    table="fx_rates",
    column="date",
    rows=1,
    store=lambda value: (f"INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES ({value}, 'EUR', 'USD', 1.0849, 'ECB', '{CREATED}')",),
    read="SELECT typeof(date), date FROM fx_rates WHERE base = 'EUR' AND quote = 'USD'",
)
#: A table LibreFolio does not have, as a crafted archive carries one (B-28 lets a table through by its kind): its name
#: and its column's need quotes, and the column declares no type, so that only its storage class says a value is text.
B49_TABLE = f'{B49_UNTRUSTED} "notes"'
B49_COLUMN = f"{B49_UNTRUSTED} body"
IN_A_TABLE_LIBREFOLIO_DOES_NOT_HAVE = TextPlace(
    name="a-table-librefolio-does-not-have",
    table=B49_TABLE,
    column=B49_COLUMN,
    rows=1,
    store=lambda value: (f"CREATE TABLE {sql_name(B49_TABLE)} (id INTEGER PRIMARY KEY, {sql_name(B49_COLUMN)})", f"INSERT INTO {sql_name(B49_TABLE)} ({sql_name(B49_COLUMN)}) VALUES ({value})"),
    read=f"SELECT typeof({sql_name(B49_COLUMN)}), {sql_name(B49_COLUMN)} FROM {sql_name(B49_TABLE)} ORDER BY id",
)
ALL_TEXT_PLACES = (IN_A_TEXT_COLUMN, IN_A_DATE_COLUMN, IN_A_TABLE_LIBREFOLIO_DOES_NOT_HAVE)
TEXT_PLACES = [
    pytest.param((IN_A_TEXT_COLUMN,), id="text-column-transactions.description"),
    pytest.param((IN_A_DATE_COLUMN,), id="date-column-fx_rates.date"),
    pytest.param((IN_A_TABLE_LIBREFOLIO_DOES_NOT_HAVE,), id="a-table-librefolio-does-not-have"),
    pytest.param(ALL_TEXT_PLACES, id="the-three-at-once"),
]
#: é (C3 A9) split over two rows of a table LibreFolio does not have: neither row is UTF-8, though their bytes joined
#: with nothing between them are. The server reads each row on its own.
SPLIT_TABLE = f"{B49_UNTRUSTED}_halves"
SPLIT_COLUMN = f"{B49_UNTRUSTED}_half"
SPLIT_HALVES = (b"\xc3", b"\xa9")
#: A table whose rowids are as far apart as SQLite allows: the smallest, 1 and the largest. Windows of 200 000 rows are
#: rows: a read stepping through rowid values instead would walk 2**64 / 200 000 windows, and hold the lock of the
#: checks for ever; one starting at rowid 0 would never meet the first row. The text that is not UTF-8 lies at either
#: end.
SPARSE_TABLE = f"{B49_UNTRUSTED}_sparse"
SPARSE_COLUMN = f"{B49_UNTRUSTED}_body"
SMALLEST_ROWID = -(2**63)
LARGEST_ROWID = 2**63 - 1
SPARSE_ENDS = [pytest.param(SMALLEST_ROWID, id="at-the-smallest-rowid"), pytest.param(LARGEST_ROWID, id="at-the-largest-rowid")]
#: A table LibreFolio does not have, its one row holding valid UTF-8 in a plain column, and a column generated from an
#: expression of the schema alone, declared ``TEXT``: VIRTUAL (computed whenever it is read, never stored) or STORED
#: (computed when the row is written). ``PRAGMA table_info`` does not list a generated column; ``table_xinfo`` does,
#: its ``hidden`` 2 (VIRTUAL) or 3 (STORED): a read whose columns come from ``table_info`` passes it by. The expression
#: calls no function, so neither B-43's integrity check (it computes a VIRTUAL column that declares a type, and finds
#: TEXT in a TEXT column) nor the server's stand-ins (B-43, part 1) meet one, and B-28 lets a table through.
GENERATED_TABLE = f"{B49_UNTRUSTED}_computed"
GENERATED_PLAIN = f"{B49_UNTRUSTED}_plain"
GENERATED_COLUMN = f"{B49_UNTRUSTED}_generated"
GENERATED_KINDS = [pytest.param("VIRTUAL", 2, id="virtual"), pytest.param("STORED", 3, id="stored")]


def archive_with(tmp: Path, database: Path, statements: tuple[str, ...], stored: dict[str, list[tuple]]) -> BuiltArchive:
    """A real backup of a data directory made from ``database`` (``ACCOUNTS``, ``FILES``), whose database got
    ``statements`` before it was archived: the snapshot copies the bytes as they are, and nothing of the build reads
    them (the control totals read eight columns of ``transactions``, never ``description``). Checked: the build warned
    of nothing, and each query of ``stored``, read as bytes on the database the archive carries, gives back its rows."""
    data = make_data_dir(tmp / "data", database)
    execute(data / DATABASE_ENTRY, *statements)
    built = build_into(data, tmp / "work")
    assert built.warnings == (), f"precondition: a backup its build warns nothing of: {built.warnings}"
    carried = database_of(built.path, tmp / "carried.db")
    held = {sql: stored_bytes(carried, sql) for sql in stored}
    assert held == stored, f"precondition: the database of the archive stores what the test wrote, as it wrote it: {held}"
    return built


def archive_storing(tmp: Path, database: Path, places: tuple[TextPlace, ...], raw: bytes, *, as_blob: bool = False) -> BuiltArchive:
    """``archive_with`` the bytes ``raw`` in every row of each of ``places``: as TEXT (a ``CAST`` of them), or as a
    BLOB."""
    value, kind = (blob_sql(raw), b"blob") if as_blob else (text_sql(raw), b"text")
    statements = tuple(statement for place in places for statement in place.store(value))
    return archive_with(tmp, database, statements, {place.read: [(kind, raw)] * place.rows for place in places})


def in_a_generated_column(storage: str) -> TextPlace:
    """``GENERATED_COLUMN`` of ``GENERATED_TABLE``, generated ``storage`` (``VIRTUAL`` or ``STORED``) and declared
    ``TEXT``: ``store(value)`` creates the table, the SQL expression ``value`` the column's own, and inserts its one
    row, ``GENERATED_PLAIN`` holding ``VALID_UTF8``; ``read``, the storage class and the value the column gives."""
    return TextPlace(
        name=f"{storage.lower()}-generated-column",
        table=GENERATED_TABLE,
        column=GENERATED_COLUMN,
        rows=1,
        store=lambda value: (
            f"CREATE TABLE {GENERATED_TABLE} (id INTEGER PRIMARY KEY, {GENERATED_PLAIN} TEXT, {GENERATED_COLUMN} TEXT GENERATED ALWAYS AS ({value}) {storage})",
            f"INSERT INTO {GENERATED_TABLE} (id, {GENERATED_PLAIN}) VALUES (1, {text_sql(VALID_UTF8)})",
        ),
        read=f"SELECT typeof({GENERATED_COLUMN}), {GENERATED_COLUMN} FROM {GENERATED_TABLE} ORDER BY id",
    )


def never_fixed(patch: pytest.MonkeyPatch, *, why: str = "the check went on with a database holding text that is not UTF-8 (B-49)") -> list[Path]:
    """``run_post_migration_fixes`` as ``staging`` imports it, failing the test when a check reaches it: the first step
    that writes in the copy, which a copy holding text that is not UTF-8 never reaches (B-49). ``why``: what the failure
    says the check let through. The calls, kept."""
    calls: list[Path] = []

    def fixes(database: Path, data_dir: Path | None = None, **_options: Any) -> PostMigrationReport:
        calls.append(Path(database))
        pytest.fail(f"run_post_migration_fixes (as staging imports it) ran on the copy: {why}")

    patch.setattr(staging, "run_post_migration_fixes", fixes)
    return calls


def given_away(line: dict[str, Any], places: tuple[TextPlace, ...], paths: tuple[str, ...]) -> list[str]:
    """What a line of the log gives away: a fragment of the archive's text or of a decode error, a name of a table or a
    column of ``places`` (as a whole word: ``date`` is not ``updated``), a path of the test."""
    text = repr(line)
    names = {name for place in places for name in (place.table, place.column)}
    told = [fragment for fragment in UNDECODABLE_FRAGMENTS if fragment in text]
    named = sorted(name for name in names if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text))
    return [*told, *named, *(path for path in paths if path in text)]


def reads_text_by_storage_class(statement: str) -> bool:
    """Whether ``statement`` reads values by their storage class, as B-49's read does (``TEXT_BY_STORAGE_CLASS``)."""
    return all(pattern.search(statement) for pattern in TEXT_BY_STORAGE_CLASS)


@pytest.mark.parametrize("places", TEXT_PLACES)
def test_a_database_holding_text_that_is_not_utf8_is_refused_before_anything_writes_in_its_copy(instance, databases, tmp_path, monkeypatch, places):
    """(o) B-49 A backup at the head holding text that is not UTF-8 — in ``transactions.description`` (two rows), in
    ``fx_rates.date`` (a DATE column), in a table LibreFolio does not have (its names quoted, its column untyped), or
    the three at once — is refused ``database_damaged`` in the contract's words, once unpacked: after the copy's first
    description (``describe_database``, the real one, answered ``ok`` once: the copy is the one its manifest describes)
    and before anything writes in it (``run_post_migration_fixes`` and ``_upgrade`` fail the test if reached). Nothing
    of the copy left, the lock free, no path said, the archive only read, the live data directory untouched
    (``instance``). Red before B-49: nothing reads these values, and the check goes on to the post-migration fixes."""
    print_section("B-49: text that is not UTF-8")
    archive = archive_storing(tmp_path / "b49", databases.head, places, NOT_UTF8).path
    original = sha256(archive.read_bytes())
    answers = recorded_descriptions(monkeypatch)
    fixed = never_fixed(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert (error.code, str(error)) == (UNDECODABLE_CODE, UNDECODABLE_MESSAGE), f"refused in the contract's words: {error.code}: {error}"
    assert progress.phases == UNPACKED, f"refused once unpacked, never upgraded nor verified: {progress.phases}"
    assert (answers, fixed) == (["ok"], []), f"described once, as its manifest says, then refused before anything wrote in the copy: descriptions {answers}, fixes run on {fixed}"
    assert sha256(archive.read_bytes()) == original, "the archive is only read"
    print_success(f"{[place.name for place in places]}: {error.code}, nothing of the copy left")


def test_an_older_backup_holding_text_that_is_not_utf8_is_refused_before_its_upgrade(instance, databases, tmp_path, monkeypatch):
    """(o) B-49 An older backup — at ``OLDER``, built as the module's ``older_archive`` is — holding text that is not
    UTF-8 in ``transactions.description``: refused ``database_damaged`` in the contract's words before its copy is
    upgraded (``_upgrade`` fails the test if reached), the progress never reaching ``upgrading``; the copy described
    once, nothing of it left, the lock free, the archive only read. Red before B-49: nothing refuses it, and the check
    goes on to upgrade the copy."""
    built = archive_storing(tmp_path / "b49-older", databases.older, (IN_A_TEXT_COLUMN,), NOT_UTF8)
    assert (built.manifest.alembic_revision, _revision_plan(OLDER)[0]) == (OLDER, "upgrade"), f"precondition: a backup at {OLDER}, which a restore upgrades: {built.manifest.alembic_revision}"
    original = sha256(built.path.read_bytes())
    answers = recorded_descriptions(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(built.path, instance)
    assert (error.code, str(error)) == (UNDECODABLE_CODE, UNDECODABLE_MESSAGE), f"refused in the contract's words: {error.code}: {error}"
    assert progress.phases == UNPACKED, f"refused before upgrading: {progress.events}"
    assert answers == ["ok"], f"described once, as its manifest says, then refused: {answers}"
    assert sha256(built.path.read_bytes()) == original, "the archive is only read"
    print_success(f"{OLDER}: {error.code} before upgrading")


@pytest.mark.parametrize("places", TEXT_PLACES)
def test_the_refusal_warns_once_with_the_number_of_tables_never_the_text_its_bytes_a_name_nor_a_path(instance, databases, tmp_path, monkeypatch, places):
    """(o) B-49 One warning, «A backup's database holds text that is not UTF-8», whose payload is numbers only, the
    number of tables holding such text among them (the three at once: 3, for four values). No line of the log holds the
    text, its bytes (as ``sqlite3`` quotes them, as Python escapes or names them, in hex), the words of a decode error,
    a name of a table or a column of the archive, or a path of the test. The barrier: ``sqlite3``, reading the archive's
    value as the server reads text, fails with an error quoting it: a log of an error's message would leak it."""
    archive = archive_storing(tmp_path / "b49", databases.head, places, NOT_UTF8).path
    probed = database_of(archive, tmp_path / "b49-probed.db")
    for place in places:
        with pytest.raises(sqlite3.OperationalError) as raised:
            rows_of(probed, place.read)
        assert B49_MARKER in str(raised.value), f"barrier: {place.name}: sqlite3's error quotes the archive's text, so the log had something to keep out: {raised.value}"
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    with staging_logs() as events:
        error, _progress = refused(archive, instance)
    assert error.code == UNDECODABLE_CODE, f"precondition: refused for its text: {error.code}: {error}"
    lines = [event for event in events if event.get("event") != LOG_CANARY]
    warned = [event for event in lines if event.get("log_level") in ("warning", "error", "critical")]
    assert [(event.get("log_level"), event.get("event")) for event in warned] == [("warning", UNDECODABLE_EVENT)], f"one warning, and only that one: {[(event.get('log_level'), event.get('event')) for event in lines]}"
    fields = {key: value for key, value in warned[0].items() if key not in ("event", "log_level")}
    tables = len({place.table for place in places})
    assert fields and all(type(value) is int for value in fields.values()), f"the warning's payload is numbers only, never a text: {fields}"
    assert tables in fields.values(), f"the warning gives the number of tables holding such text, {tables}, for {sum(place.rows for place in places)} values: {fields}"
    paths = (str(tmp_path), str(tmp_path.resolve()), f"{os.sep}pytest-of-")
    leaked = {str(line.get("event")): found for line in lines if (found := given_away(line, places, paths))}
    assert not leaked, f"no line of the log holds the archive's text, its bytes, a decode error's words, its names or a path: {leaked}"
    print_success(f"warned once: {fields}")


def test_a_character_whose_two_bytes_are_split_over_two_rows_is_text_that_is_not_utf8_in_each(instance, databases, tmp_path, monkeypatch):
    """(o) B-49 é (C3 A9) split over two rows of a table LibreFolio does not have: each row holds one byte of it, so
    neither is UTF-8 and the server fails on each, though the two, joined with nothing between them, are. Every value is
    to be UTF-8 on its own, whatever a read joins: refused ``database_damaged`` in the contract's words, once unpacked,
    before anything writes in the copy. Red before B-49: nothing reads them."""
    first, second = SPLIT_HALVES
    assert (first + second).decode("utf-8") == "\u00e9", "precondition: joined with nothing between them, the two halves are é"
    for half in SPLIT_HALVES:
        with pytest.raises(UnicodeDecodeError):
            half.decode("utf-8")
    statements = (f"CREATE TABLE {SPLIT_TABLE} (id INTEGER PRIMARY KEY, {SPLIT_COLUMN} TEXT)", *(f"INSERT INTO {SPLIT_TABLE} (id, {SPLIT_COLUMN}) VALUES ({row}, {text_sql(half)})" for row, half in enumerate(SPLIT_HALVES, start=1)))
    read = f"SELECT typeof({SPLIT_COLUMN}), {SPLIT_COLUMN} FROM {SPLIT_TABLE} ORDER BY id"
    archive = archive_with(tmp_path / "b49-split", databases.head, statements, {read: [(b"text", half) for half in SPLIT_HALVES]}).path
    fixed = never_fixed(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert (error.code, str(error), progress.phases, fixed) == (UNDECODABLE_CODE, UNDECODABLE_MESSAGE, UNPACKED, []), f"refused once unpacked, before anything wrote in the copy: {error.code}: {error}, {progress.phases}"
    print_success("é split over two rows: database_damaged")


@pytest.mark.parametrize("end", SPARSE_ENDS)
def test_text_that_is_not_utf8_at_either_end_of_rowids_as_far_apart_as_sqlite_allows_is_found_and_the_check_ends(instance, databases, tmp_path, monkeypatch, end):
    """(o) B-49 A table LibreFolio does not have, its rows at the smallest rowid SQLite allows (-2**63), at 1 and at the
    largest (2**63 - 1), the text that is not UTF-8 in the first or in the last of them, valid UTF-8 in the others.
    Windows of 200 000 rows are rows, so the read meets every row in a window or two: the check refuses the archive
    ``database_damaged`` in the contract's words, once unpacked, and ends — within ``DEADLINE_S``, run in a thread: a
    read stepping through rowid values would walk 2**64 / 200 000 windows and never end, holding the lock of the checks;
    one starting at rowid 0 would pass the first row by. Nothing of the copy left, the lock free. Red before B-49:
    nothing reads the row, and the check goes on to the post-migration fixes."""
    rows = tuple((rowid, NOT_UTF8 if rowid == end else VALID_UTF8) for rowid in (SMALLEST_ROWID, 1, LARGEST_ROWID))
    statements = (f"CREATE TABLE {SPARSE_TABLE} (id INTEGER PRIMARY KEY, {SPARSE_COLUMN} TEXT)", *(f"INSERT INTO {SPARSE_TABLE} (id, {SPARSE_COLUMN}) VALUES ({rowid}, {text_sql(raw)})" for rowid, raw in rows))
    read = f"SELECT id, typeof({SPARSE_COLUMN}), {SPARSE_COLUMN} FROM {SPARSE_TABLE} ORDER BY id"
    archive = archive_with(tmp_path / "b49-sparse", databases.head, statements, {read: [(rowid, b"text", raw) for rowid, raw in rows]}).path
    never_fixed(monkeypatch)
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    progress = Progress()
    outcome: dict[str, object] = {}

    def check() -> None:
        try:
            outcome["report"] = stage_archive(archive, instance.root, progress=progress)
        except BaseException as exc:  # reported by the test, below
            outcome["error"] = exc

    thread = threading.Thread(target=check, name="staging-b49-sparse-rowids", daemon=True)
    thread.start()
    thread.join(DEADLINE_S)
    assert not thread.is_alive(), f"the check did not end within {DEADLINE_S}s: a read stepping through rowid values, not rows, walks 2**64 / 200 000 windows (phases so far: {progress.phases})"
    error = outcome.get("error")
    assert isinstance(error, StagingError), f"refused for the text of the row at rowid {end}: {outcome}"
    assert (error.code, str(error), progress.phases) == (UNDECODABLE_CODE, UNDECODABLE_MESSAGE, UNPACKED), f"refused in the contract's words, once unpacked: {error.code}: {error}, {progress.phases}"
    assert leftover_stages(instance.root) == [] and lock_is_free(instance.root), f"nothing of the copy left, the lock free: {leftover_stages(instance.root)}"
    print_success(f"text that is not UTF-8 at rowid {end}: database_damaged, ended")


@pytest.mark.parametrize(("storage", "hidden"), GENERATED_KINDS)
def test_text_that_is_not_utf8_in_a_generated_column_which_table_info_does_not_list_is_refused(instance, databases, tmp_path, monkeypatch, storage, hidden):
    """(o) B-49 A table LibreFolio does not have, its one row holding valid UTF-8 in a plain column and, in a column
    generated from ``CAST(x'45ff…' AS TEXT)`` and declared ``TEXT`` — VIRTUAL (computed whenever it is read) or STORED
    (computed when the row was written) — text that is not UTF-8. ``PRAGMA table_info`` does not list a generated
    column, ``table_xinfo`` does: a read whose columns come from ``table_info`` passes it by, while a reader naming the
    column, as the server names those of its models, fails on it. Refused ``database_damaged`` in the contract's words,
    once unpacked: after the copy's first description, which finds it intact, and before anything writes in it (the
    fixes and the upgrade fail the test if reached). One warning, its payload numbers only, the one table among them;
    no line of the log holds the text, its bytes, the hex of the schema's expression, a decode error's words, a name of
    the archive or a path. Nothing of the copy left, the lock free, the archive only read.

    Preconditions, on the database the archive carries: ``table_info`` lists the plain columns alone, ``table_xinfo``
    the generated one too, its ``hidden`` 2 or 3; the plain column reads as the server reads text. Barrier: the
    generated one fails with an error quoting the text, so a log of an error's message would leak it. And nothing
    refuses it first: B-28 reads a table; B-43's description, read only, answers ``ok``, and its integrity checks of a
    plain reader (read only, read write) and its read of the schema with the server's stand-ins raise nothing. Red
    before B-49 (nothing reads the column), and with a read whose columns come from ``table_info``: the check goes on
    to the post-migration fixes."""
    place = in_a_generated_column(storage)
    plain = f"SELECT typeof({GENERATED_PLAIN}), {GENERATED_PLAIN} FROM {GENERATED_TABLE} ORDER BY id"
    built = archive_with(tmp_path / "b49-generated", databases.head, place.store(text_sql(NOT_UTF8)), {place.read: [(b"text", NOT_UTF8)], plain: [(b"text", VALID_UTF8)]})
    probed = database_of(built.path, tmp_path / "b49-generated-probed.db")
    by_info = [row[1] for row in rows_of(probed, f"PRAGMA table_info({GENERATED_TABLE})")]
    by_xinfo = {row[1]: row[6] for row in rows_of(probed, f"PRAGMA table_xinfo({GENERATED_TABLE})")}
    assert (by_info, by_xinfo) == (["id", GENERATED_PLAIN], {"id": 0, GENERATED_PLAIN: 0, GENERATED_COLUMN: hidden}), f"precondition: table_info lists the plain columns alone, table_xinfo the generated one too (hidden {hidden}): {by_info}, {by_xinfo}"
    assert rows_of(probed, f"SELECT {GENERATED_PLAIN} FROM {GENERATED_TABLE}") == [(VALID_TEXT,)], "precondition: the plain column holds valid UTF-8, read as the server reads text"
    with pytest.raises(sqlite3.OperationalError) as raised:
        rows_of(probed, place.read)
    assert B49_MARKER in str(raised.value), f"barrier: sqlite3's error on the generated column quotes the archive's text, so the log had something to keep out: {raised.value}"
    described = snapshot.describe_database(probed)
    foreign = [(name, schema_kind(sql)) for _type, name, sql in rows_of(probed, "SELECT type, name, sql FROM sqlite_master") if schema_kind(sql) not in ALLOWED_KINDS]
    met = {"integrity, read only": plain_integrity_error(probed, read_only=True), "integrity, read write": plain_integrity_error(probed, read_only=False), "schema, server's stand-ins": server_schema_error(probed)}
    assert (described.integrity_check, foreign, {step: repr(error) for step, error in met.items() if error is not None}) == ("ok", [], {}), f"precondition: neither B-28 nor B-43 refuses it before B-49's read: integrity {described.integrity_check!r}, foreign {foreign}, errors {met}"
    original = sha256(built.path.read_bytes())
    answers = recorded_descriptions(monkeypatch)
    fixed = never_fixed(monkeypatch, why=f"the check went on with a {storage} generated column computing text that is not UTF-8 (B-49): PRAGMA table_info does not list it, table_xinfo does")
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    with staging_logs() as events:
        error, progress = refused(built.path, instance)
    assert (error.code, str(error), progress.phases) == (UNDECODABLE_CODE, UNDECODABLE_MESSAGE, UNPACKED), f"refused in the contract's words, once unpacked: {error.code}: {error}, {progress.phases}"
    assert (answers, fixed) == (["ok"], []), f"described once, intact, then refused before anything wrote in the copy: descriptions {answers}, fixes run on {fixed}"
    lines = [event for event in events if event.get("event") != LOG_CANARY]
    warned = [event for event in lines if event.get("log_level") in ("warning", "error", "critical")]
    assert [(event.get("log_level"), event.get("event")) for event in warned] == [("warning", UNDECODABLE_EVENT)], f"one warning, and only that one: {[(event.get('log_level'), event.get('event')) for event in lines]}"
    fields = {key: value for key, value in warned[0].items() if key not in ("event", "log_level")}
    assert fields and all(type(value) is int for value in fields.values()) and 1 in fields.values(), f"the warning's payload is numbers only, the one table holding such text among them: {fields}"
    paths = (str(tmp_path), str(tmp_path.resolve()), f"{os.sep}pytest-of-")
    leaked = {str(line.get("event")): found for line in lines if (found := given_away(line, (place,), paths))}
    assert not leaked, f"no line of the log holds the archive's text, its bytes, a decode error's words, its names or a path: {leaked}"
    assert sha256(built.path.read_bytes()) == original, "the archive is only read"
    print_success(f"{storage} generated column, hidden {hidden} in table_xinfo: {error.code}, warned once")


def test_a_check_reads_the_text_of_its_copy_by_storage_class_read_only_trusted_schema_off_first(instance, head_archive, monkeypatch):
    """(o) B-49 A check of the module's head archive, nothing to refuse, reads the text of its copy: a connection of
    ``staging``, opened after the copy's first description (``snapshot``'s) and before the post-migration fixes', runs
    statements reading values by their storage class (``typeof(…)`` compared with ``'text'``; no exact SQL pinned), one
    of them on ``users``, which every backup of the module fills. It is read only (a ``file:`` URI with ``mode=ro``) and
    runs ``PRAGMA trusted_schema=OFF`` before anything else; (l)'s B-37 test sees it among every connection to the copy.
    Red before B-49: no statement of a check reads ``typeof``."""
    opened = recorded_connections(monkeypatch)
    stage_id = new_stage_id()
    report = stage_archive(head_archive.path, instance.root, stage_id=stage_id)
    on_copy = on_the_copy(opened, instance.root, stage_id)
    kinds = [record.by for record in on_copy]
    assert report.restorable and {"snapshot", "post_migration"} <= set(kinds), f"precondition: a genuine archive checked, its copy described and fixed: {report.blockers}, {first_statements(on_copy)}"
    between = on_copy[kinds.index("snapshot") + 1 : kinds.index("post_migration")]
    reads = [record for record in between if record.by == "staging" and any(reads_text_by_storage_class(statement) for statement in record.statements)]
    if not reads:
        pytest.fail(f"[new] no connection of staging between the copy's first description and the post-migration fixes reads its values by storage class (typeof(…) compared with 'text'): lot B-49 is not written yet: {first_statements(on_copy)}")
    loose = [(record.target, record.uri, record.statements[:2]) for record in reads if not (record.opened_read_only and turns_trust_off_first(record))]
    assert not loose, f"the read of the text is read only (mode=ro) and turns trusted_schema off first: {loose}"
    statements = "\n".join(statement for record in reads for statement in record.statements if reads_text_by_storage_class(statement))
    assert re.search(r"(?<!\w)users(?!\w)", statements), f"every table is read, users among them: {statements[:2000]}"
    print_success(f"{len(reads)} connection(s) reading the copy's text by storage class, read only, trusted_schema=OFF first")


@pytest.mark.parametrize("places", TEXT_PLACES)
def test_valid_utf8_beyond_ascii_in_the_same_places_is_checked_as_usual_and_kept_intact(instance, databases, tmp_path, places):
    """(o) B-49, the guard (green before and after): valid UTF-8 beyond ASCII — characters of two, three and four bytes
    (é, 日本, an emoji, 𝄞) — in the same places is no finding. The archive is checked as any backup at the head (``same``,
    nothing to fix, nothing to warn, restorable), no warning of B-49 logged, and the copy keeps every value as TEXT,
    read back intact as the server reads text."""
    assert {len(character.encode("utf-8")) for character in VALID_TEXT} >= {2, 3, 4}, f"precondition: characters of two, three and four bytes: {VALID_TEXT!r}"
    archive = archive_storing(tmp_path / "b49-valid", databases.head, places, VALID_UTF8).path
    with staging_logs() as events:
        report = stage_archive(archive, instance.root)
    found = (report.action, report.post_migration_fixes, report.warnings, report.blockers, report.restorable)
    assert found == ("same", [], [], [], True), f"checked as any backup at the head: {found}"
    assert not [event for event in events if event.get("event") == UNDECODABLE_EVENT], "no warning of text that is not UTF-8"
    copy = stage_dir(instance.root, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    kept = {place.name: rows_of(copy, place.read) for place in places}
    assert kept == {place.name: [("text", VALID_TEXT)] * place.rows for place in places}, f"the copy keeps every value as TEXT, read back intact: {kept}"
    print_success(f"{[place.name for place in places]}: valid UTF-8 kept, restorable")


def test_the_same_bytes_stored_as_a_blob_are_no_text_and_are_checked_as_usual(instance, databases, tmp_path):
    """(o) B-49, the guard (green before and after): the very bytes of ``NOT_UTF8`` stored as a BLOB in the same three
    places are no text — B-49 reads by storage class, and a BLOB in a column of text is out of its scope. The archive is
    checked as any backup at the head, restorable, no warning of B-49 logged, and the copy keeps every BLOB as it is."""
    archive = archive_storing(tmp_path / "b49-blob", databases.head, ALL_TEXT_PLACES, NOT_UTF8, as_blob=True).path
    with staging_logs() as events:
        report = stage_archive(archive, instance.root)
    found = (report.action, report.warnings, report.blockers, report.restorable)
    assert found == ("same", [], [], True), f"checked as any backup at the head: {found}"
    assert not [event for event in events if event.get("event") == UNDECODABLE_EVENT], "no warning of text that is not UTF-8"
    copy = stage_dir(instance.root, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    kept = {place.name: stored_bytes(copy, place.read) for place in ALL_TEXT_PLACES}
    assert kept == {place.name: [(b"blob", NOT_UTF8)] * place.rows for place in ALL_TEXT_PLACES}, f"the copy keeps every BLOB as it is: {kept}"
    print_success("the same bytes as BLOBs: restorable")


def test_a_manifest_that_does_not_describe_the_database_is_refused_for_that_first_whatever_text_it_holds(instance, databases, tmp_path, monkeypatch):
    """(o) B-49, the guard (green before and after): the text is read once the copy is found to be the database its
    manifest describes, never before. An archive holding text that is not UTF-8 whose manifest counts one account more
    than its database holds is refused ``manifest_mismatch``, as without that text ((e), ``rows_differ``)."""
    built = archive_storing(tmp_path / "b49-mismatch", databases.head, (IN_A_TEXT_COLUMN,), NOT_UTF8)
    tables = built.manifest.database.tables
    archive = pack(tmp_path / "b49-mismatch.zip", entries_of(built), with_tables(built, {**tables, "users": tables["users"] + 1}))
    monkeypatch.setattr(staging, "_upgrade", never_upgrade)
    error, progress = refused(archive, instance)
    assert (error.code, progress.phases) == ("manifest_mismatch", UNPACKED), f"the manifest's mismatch first, the text never read: {error.code}: {error}, {progress.phases}"
    print_success("manifest_mismatch, before the text is read")

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

Real databases: two, made once for the module by ``alembic upgrade`` in a process of their own (at the head, and at
``OLDER``), then copied for every data directory and given accounts by SQL. Two more ``alembic`` processes
are the product's: the upgrade of a copy that succeeds, and one that fails on the copy (a trigger refuses any change of
its revision). Every other failure is simulated in this process, for one test: ``staging.subprocess`` (an ``alembic``
that ends badly, times out or cannot start), ``staging._upgrade``, ``staging.run_post_migration_fixes``, ``staging.os``
(files that fail to write), ``staging.shutil`` (a disk with little room), ``staging.ALEMBIC_INI`` and
``staging.MAX_ENTRIES``.

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
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import get_data_dir
from backend.app.db.post_migration.base import PostMigrationReport
from backend.app.services.platform.instance_backup import staging
from backend.app.services.platform.instance_backup.archive import BuiltArchive, build_archive
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.services.platform.instance_backup.manifest import MANIFEST_MAX_BYTES, ManifestFile
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
from backend.app.services.platform.instance_backup.snapshot import file_digest
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
    assert report.warnings == (["rows_changed"] if any(rows.before != rows.after for rows in expected.values()) else []), f"rows_changed exactly when a table's rows differ, a table created included: {report.warnings}"
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


def test_an_upgrade_that_fails_in_alembic_is_refused_and_leaves_nothing(instance, databases, tmp_path):
    """(e) For real: an older backup whose database refuses any change of its revision (a trigger). ``alembic`` fails in
    its own process, on the copy, whatever the migration; the check says ``upgrade_failed`` and removes the copy."""
    data = make_data_dir(tmp_path / "data", databases.older)
    execute(data / DATABASE_ENTRY, "CREATE TRIGGER refuse_every_upgrade BEFORE UPDATE ON alembic_version BEGIN SELECT RAISE(ABORT, 'this database refuses every upgrade'); END")
    archive = build_into(data, tmp_path / "work").path
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

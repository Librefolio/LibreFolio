"""
Instance backup, the ledger's control totals (workstream B, lot B-13): ``instance_backup/totals.py``.

B computes nothing financial (rule 10): J's ``backend/app/services/financial_math/ledger_totals.py`` does. Under test,
B's two functions around it, as the contract's §7 decided them (it overrides §1-§5):

(a) ``ledger_totals_of(database)``: J's ``compute_control_totals`` on a database file, through an engine of its own that
    reads it as immutable (``<Path.as_uri()>?mode=ro&immutable=1``). A real LibreFolio database (made by ``alembic
    upgrade head``) holding a ledger of several brokers, currencies and positions gives J's JSON: the same as J's pure
    ``control_totals`` of the same rows, read here with ``sqlite3`` alone; an empty ledger gives no line. The file is
    only read: its bytes and its mtime unchanged, nothing created beside it, in rollback-journal mode (a backup's
    snapshot, as ``VACUUM INTO`` writes it), in WAL mode (a check's copy, once ``alembic`` upgraded it) and with an
    empty ``-wal`` and its ``-shm`` beside it (as ``describe_database`` leaves the copy). A ``-wal`` still holding frames
    is never read past (immutable would ignore them): ``None``, the error ``PendingWriteAheadLog``. Its path is a name,
    never read as a URI: a folder named with spaces, accents, ``#``, ``?``, ``&`` or ``%41``, the file of that folder is
    read, and no other. It never raises: a missing file (never created), a folder, a file that is not a database, an
    empty or a truncated one, a database without the ledger's table, a sum J's exact context refuses, a running event
    loop: ``None``, and one error logged, «The ledger's control totals could not be read», with the exception's type
    name alone (no path, no value).
(b) ``compare_totals(recorded, current)``: the status, in the contract's decision order: ``absent`` when nothing is
    recorded; ``other_version`` for an ``int`` version other than J's, checked before anything is read (malformed, or
    nothing read on the copy, all the same); ``absent`` for whatever J's ``from_json`` refuses, the one rule for a
    recorded document (B-22: B keeps no copy of J-27's): an amount that is not plain decimal text
    (``-?[0-9]{1,60}(\\.[0-9]{1,60})?``), the lines not a list or a line not an object, a version that is not an ``int``
    (such as ``"1"`` or ``true``), lines missing or malformed, not an object. The recorded document reaches J's
    ``from_json`` and J's ``from_json`` refuses it; an exponent such as ``1E+999999999`` is never expanded.
    ``unreadable`` when nothing was read on the copy, and when J's ``from_json`` refuses what was read there (B-29, E's
    R13-SEC2: J's ``to_json`` writes every amount in plain text, so an exact sum such as ``1E+70`` is written with 71
    digits, past the 60 it reads back): never an exception, which would end the whole check ``stage_failed``, and one
    warning, «The control totals of the copy cannot be read: they are not compared», with nothing else in it, as the
    recorded side's own; a recorded document J refuses is still ``absent`` first, whatever the copy's. Then the lines
    compared as maps, in J's canonical text, zero lines
    dropped: ``same`` without a difference (``10.50`` is ``10.5``; lines in another order, an explicit zero line),
    ``changed`` otherwise, always with one line at least. The differences: cash first, then quantities; by broker,
    numerically; then currency, or asset numerically; J's canonical text, ``None`` for a line absent (zero) on that side;
    the first ``MAX_DIFFERENCES`` (20) kept, ``differences_count`` counting them all; none, and 0, for any other
    status. The result and its differences are frozen, the differences a tuple; the documents given are never changed.

Pure: one ``alembic upgrade head``, in a process of its own, makes the module's database on a file of ``tmp_path``;
every file a test reads is a copy of it under ``tmp_path``. This process is configured with a production data directory
of the test that must stay absent (``configure`` of ``test_backup_staging.py``). No lane database, no server, no
network. ``instance_backup.totals`` is imported by each test (the ``totals`` fixture), never at collection: until lot
B-13 writes it, each test fails on its own, saying so. J's ``ControlTotals.from_json`` is wrapped for the tests of what J
refuses, recorded or read on the copy: every document it gets is kept with its answer, and one holding an amount that is
not plain text is refused at once, with the ``ValueError`` J answers, before J's own code runs: nothing is expanded in
this process, even if J's rule regressed. Folder names with ``?`` are POSIX-only.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import shutil
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import closing
from pathlib import Path
from types import ModuleType

import pytest
from structlog.testing import capture_logs

from backend.app.services.financial_math import ledger_totals
from backend.app.services.financial_math.ledger_totals import CONTROL_TOTALS_VERSION, control_totals
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
needs_posix_names = pytest.mark.skipif(not POSIX, reason="? is not allowed in a Windows file name")

#: What ``ledger_totals_of`` logs, once, when it cannot read the totals.
READ_ERROR = "The ledger's control totals could not be read"
#: What ``compare_totals`` logs, once, a warning with nothing else in it, when J's ``from_json`` refuses the totals the
#: backup recorded, or those read on the copy (B-29).
RECORDED_UNREADABLE = "The control totals the backup recorded cannot be read: they are not compared"
COPY_UNREADABLE = "The control totals of the copy cannot be read: they are not compared"
#: An amount of a recorded document as J may read it (contract §7.3): plain decimal text, 60 digits at most on a side.
PLAIN_AMOUNT = re.compile(r"-?[0-9]{1,60}(\.[0-9]{1,60})?")


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def configured_data_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    """The production data directory this process is configured with: a folder of the test that must stay absent. The
    totals are read from the file given, never through the app's own database."""
    configured = cases.configure(monkeypatch, tmp_path / "configured-data-dir")
    yield configured
    get_git_version.cache_clear()
    assert not configured.exists(), f"something was written in the configured data directory: {cases.listing(configured)}"


@pytest.fixture
def totals() -> ModuleType:
    """``instance_backup.totals``, imported for the test that asks for it."""
    return cases.totals_module()


@pytest.fixture(scope="module")
def head_database(tmp_path_factory) -> Path:
    """A real database at this LibreFolio's head, made once by ``alembic upgrade head`` in a process of its own, in
    rollback-journal mode, nothing beside it. Its ledger is empty."""
    root = tmp_path_factory.mktemp("migrated")
    configured = root / "configured-data-dir"
    database = root / "head.db"
    cases.alembic_upgrade(database, "head", cases.child_env(configured))
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    assert cases.revisions_of(database) == [cases.HEAD], f"precondition: a database at the head: {cases.revisions_of(database)}"
    assert cases.side_files(database) == [], f"precondition: nothing beside it: {cases.side_files(database)}"
    assert not configured.exists(), f"alembic wrote in the configured data directory: {cases.listing(configured)}"
    return database


@pytest.fixture(scope="module")
def ledger_database(head_database, tmp_path_factory) -> Path:
    """The head database with the brokers, assets and ledger of ``test_backup_staging`` (``cases.LEDGER``). Never read by
    a test itself: each reads a copy."""
    database = tmp_path_factory.mktemp("ledger") / "ledger.db"
    shutil.copyfile(head_database, database)
    cases.add_ledger(database)
    assert cases.side_files(database) == [], f"precondition: nothing beside it: {cases.side_files(database)}"
    return database


@pytest.fixture(scope="module")
def expected(ledger_database) -> dict:
    """J's totals of the ledger: its pure ``control_totals`` of the rows read with ``sqlite3`` alone."""
    found = control_totals(cases.ledger_rows(ledger_database)).to_json()
    assert len(found["cash"]) >= 3 and len(found["quantities"]) >= 2, f"precondition: a ledger of several lines of cash and of positions: {found}"
    assert not [line for line in found["cash"] + found["quantities"] if line["broker_id"] == 3], f"precondition: the lines of broker 3 cancel out, none left: {found}"
    return found


def placed(source: Path, folder: Path, name: str = "app.db") -> Path:
    """A copy of ``source`` alone in ``folder``: what is beside it afterwards, the call left."""
    folder.mkdir(parents=True)
    target = folder / name
    shutil.copyfile(source, target)
    return target


def state_of(database: Path) -> tuple[str, int, list[str]]:
    """The bytes (SHA-256) and mtime of a database file, and what its folder holds."""
    return hashlib.sha256(database.read_bytes()).hexdigest(), database.stat().st_mtime_ns, sorted(os.listdir(database.parent))


def errors_in(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("log_level") == "error"]


def the_read_error(events: list[dict], database: Path) -> str:
    """The one error ``ledger_totals_of`` logged: its event, and the exception's type name, nothing else."""
    errors = errors_in(events)
    assert len(errors) == 1, f"one error logged, not {len(errors)}: {errors}"
    [error] = errors
    assert error.get("event") == READ_ERROR, f"the event says the totals could not be read: {error}"
    assert sorted(error) == ["error", "event", "log_level"], f"the exception's type and nothing else, no path, no value: {error}"
    assert re.fullmatch(r"[A-Za-z_]\w*", str(error["error"])), f"error is the exception's type name: {error['error']!r}"
    assert str(database.parent) not in repr(error), f"no path: {error}"
    return error["error"]


def lines_of(comparison) -> list[tuple]:
    """The differences of a comparison as (kind, broker, currency, asset, before, after)."""
    return [(line.kind, line.broker_id, line.currency, line.asset_id, line.before, line.after) for line in comparison.differences]


def document(cash=(), quantities=(), version=CONTROL_TOTALS_VERSION) -> dict:
    """Totals as J's ``to_json`` writes them: (broker, currency, balance) and (broker, asset, quantity), amounts as text."""
    return {
        "version": version,
        "cash": [{"broker_id": broker_id, "currency": currency, "balance": balance} for broker_id, currency, balance in cash],
        "quantities": [{"broker_id": broker_id, "asset_id": asset_id, "quantity": quantity} for broker_id, asset_id, quantity in quantities],
    }


def with_version(version, base: dict | None = None) -> dict:
    return {**copy.deepcopy(base if base is not None else CURRENT), "version": version}


def with_amount(field: str, value: object) -> dict:
    """``CURRENT``, the amount of its first line of ``field`` (``balance`` or ``quantity``) replaced by ``value``: read
    by J, the document would be compared."""
    changed = copy.deepcopy(CURRENT)
    changed["cash" if field == "balance" else "quantities"][0][field] = value
    return changed


def holds_text_that_is_not_plain(data: object) -> bool:
    """Whether a totals document holds an amount written as text that is not plain decimal text."""
    if not isinstance(data, Mapping):
        return False
    for lines, field in (("cash", "balance"), ("quantities", "quantity")):
        rows = data.get(lines)
        if isinstance(rows, list) and any(isinstance(row, Mapping) and isinstance(row.get(field), str) and not PLAIN_AMOUNT.fullmatch(row[field]) for row in rows):
            return True
    return False


@pytest.fixture
def j_reads(monkeypatch) -> list[tuple[object, str]]:
    """Every document J's ``ControlTotals.from_json`` is given from now on, in order, with its answer: ``"refused"`` (a
    ``ValueError``) or ``"read"``. One holding an amount that is not plain text is refused at once, before J's own code
    runs (a ``ValueError``, as J refuses it since J-27), never expanded: a comparison that hands ``1E+999999999`` to J
    gets its refusal in a moment instead of building a string of a billion digits, even if J's own rule regressed."""
    given: list[tuple[object, str]] = []
    real = ledger_totals.ControlTotals.from_json

    def from_json(cls, data):
        try:
            if holds_text_that_is_not_plain(data):
                raise ValueError("refused by the test: an amount that is not plain text reached J's from_json")
            answer = real(data)
        except ValueError:
            given.append((data, "refused"))
            raise
        given.append((data, "read"))
        return answer

    monkeypatch.setattr(ledger_totals.ControlTotals, "from_json", classmethod(from_json))
    return given


#: What a copy's ledger reads: two brokers, three currencies, two positions.
CURRENT = document(cash=[(1, "EUR", "1500.25"), (1, "USD", "-20"), (2, "CHF", "0.000001")], quantities=[(1, 7, "10"), (2, 7, "0.5")])


# =============================================================================
# (a) ledger_totals_of
# =============================================================================


def test_a_ledger_gives_j_s_totals_of_its_rows(totals, ledger_database, expected, tmp_path):
    """(a) J's JSON, the same as J's pure ``control_totals`` of the rows read with ``sqlite3`` alone; nothing logged."""
    print_section("ledger_totals_of")
    database = placed(ledger_database, tmp_path / "snapshot")
    with capture_logs() as events:
        found = totals.ledger_totals_of(database)
    assert found == expected, f"J's totals of the ledger: {found} != {expected}"
    assert found["version"] == CONTROL_TOTALS_VERSION, f"J's version: {found['version']}"
    assert errors_in(events) == [], f"nothing to log: {errors_in(events)}"
    print_success(f"{len(expected['cash'])} cash lines, {len(expected['quantities'])} positions")


def test_an_empty_ledger_gives_totals_without_a_line(totals, head_database, tmp_path):
    found = totals.ledger_totals_of(placed(head_database, tmp_path / "empty"))
    assert found == control_totals([]).to_json() == {"version": CONTROL_TOTALS_VERSION, "cash": [], "quantities": []}, f"no line: {found}"
    print_success("empty ledger: no line")


def test_a_snapshot_in_rollback_journal_mode_is_only_read(totals, ledger_database, expected, tmp_path):
    """(a) As ``VACUUM INTO`` writes a backup's snapshot: the bytes and the mtime as they were, nothing beside it.

    Why immutable (§7.1): every engine of the process gets ``PRAGMA journal_mode=WAL`` from the ``connect`` listener of
    ``backend/app/db/session.py``, which a connection opened with ``mode=ro`` alone refuses on such a file ("attempt to
    write a readonly database", measured with SQLite 3.54): every backup would record ``null``."""
    database = placed(ledger_database, tmp_path / "snapshot")
    assert database.read_bytes()[18:20] == b"\x01\x01", "precondition: a rollback-journal file"
    before = state_of(database)
    assert totals.ledger_totals_of(database) == expected, "J's totals of the snapshot"
    assert state_of(database) == before, f"only read: bytes, mtime and folder as they were: {before} → {state_of(database)}"
    print_success("rollback journal: unchanged, nothing beside it")


def in_wal_mode(database: Path) -> Path:
    """``database`` switched to WAL mode, then closed: nothing left beside it."""
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal", "precondition: WAL mode"
    assert database.read_bytes()[18:20] == b"\x02\x02" and sorted(os.listdir(database.parent)) == [database.name], f"precondition: a WAL file, closed, nothing beside it: {sorted(os.listdir(database.parent))}"
    return database


def test_a_copy_in_wal_mode_is_only_read_and_nothing_is_left_beside_it(totals, ledger_database, expected, tmp_path):
    """(a) As a check's copy is once ``alembic`` upgraded it: in WAL mode, closed, nothing beside it. Read, it is left
    so: no ``-wal``, no ``-shm`` (a connection opened with ``mode=ro`` alone would create both and leave them, measured
    with SQLite 3.54; immutable creates nothing)."""
    database = in_wal_mode(placed(ledger_database, tmp_path / "copy"))
    before = state_of(database)
    assert totals.ledger_totals_of(database) == expected, "J's totals of the copy"
    assert state_of(database) == before, f"only read: bytes, mtime and folder as they were: {before} → {state_of(database)}"
    print_success("WAL: unchanged, nothing beside it")


def test_an_empty_wal_beside_the_file_is_read_normally(totals, ledger_database, expected, tmp_path):
    """(a) As ``describe_database`` leaves a check's copy before its totals are read: a ``-wal`` of no byte and a
    ``-shm`` beside the WAL file, left by a read-only connection. Nothing is pending: read normally, everything as it
    was."""
    database = in_wal_mode(placed(ledger_database, tmp_path / "copy"))
    with closing(cases.read_only(database)) as conn:
        conn.execute("SELECT count(*) FROM transactions").fetchone()
    wal = database.with_name(database.name + "-wal")
    assert wal.is_file() and wal.stat().st_size == 0, f"precondition: an empty -wal beside it: {sorted(os.listdir(database.parent))}"
    before = (cases.fingerprint(database.parent), database.stat().st_mtime_ns)
    with capture_logs() as events:
        found = totals.ledger_totals_of(database)
    assert found == expected, f"an empty -wal holds nothing: J's totals of the file: {found} (errors: {errors_in(events)})"
    after = (cases.fingerprint(database.parent), database.stat().st_mtime_ns)
    assert after == before, f"the file, its -wal and its -shm as they were: {cases.changed(before[0], after[0])}"
    print_success("empty -wal: read")


def test_a_wal_still_holding_frames_is_never_read_past(totals, ledger_database, tmp_path):
    """(a) A copy taken while a writer still had committed frames in its ``-wal`` (a deposit more): the file alone is not
    the database, and immutable would read it without them. ``None``, the error ``PendingWriteAheadLog``; nothing
    created or changed beside it."""
    writer_folder = tmp_path / "writer"
    live = placed(ledger_database, writer_folder)
    folder = tmp_path / "copy"
    folder.mkdir()
    database = folder / "app.db"
    writer = sqlite3.connect(live, isolation_level=None)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal", "precondition: WAL mode"
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(cases.INSERT_TRANSACTION, (1, None, "DEPOSIT", "2026-09-01", "0", "1", "EUR", cases.CREATED, cases.CREATED))
        shutil.copyfile(live, database)
        shutil.copyfile(live.with_name(live.name + "-wal"), database.with_name(database.name + "-wal"))
    finally:
        writer.close()
    wal = database.with_name(database.name + "-wal")
    assert wal.stat().st_size > 0 and sorted(os.listdir(folder)) == ["app.db", "app.db-wal"], f"precondition: a -wal with frames beside the copy: {sorted(os.listdir(folder))}"
    before = (cases.fingerprint(folder), database.stat().st_mtime_ns)
    with capture_logs() as events:
        try:
            found = totals.ledger_totals_of(database)
        except Exception as exc:
            pytest.fail(f"ledger_totals_of raised {type(exc).__name__}: {exc}: it never raises")
    assert found is None, f"a pending -wal: nothing read, not the totals of the file alone: {found}"
    assert the_read_error(events, database) == "PendingWriteAheadLog", "the error names the pending -wal"
    after = (cases.fingerprint(folder), database.stat().st_mtime_ns)
    assert after == before, f"nothing created or changed: {cases.changed(before[0], after[0])}"
    print_success("pending -wal: None, error=PendingWriteAheadLog")


#: Folder names a data directory may have, which mean something in a URI: ``#`` ends its path, ``?`` starts its
#: parameters, ``&`` and ``=`` separate them, ``%41`` reads as ``A``.
FOLDER_NAMES = [
    pytest.param("Application Support", id="spaces"),
    pytest.param("données é", id="accents"),
    pytest.param("Backup #1", id="hash"),
    pytest.param("why?", id="question-mark", marks=needs_posix_names),
    pytest.param("a&b=c;d", id="ampersand-equals"),
    pytest.param("%41", id="percent-escape"),
]


@pytest.mark.parametrize("name", FOLDER_NAMES)
def test_the_path_is_a_name_never_read_as_a_uri(totals, ledger_database, head_database, expected, tmp_path, name):
    """(a) The file of the folder named so is read, and no other: beside ``%41``, a folder ``A`` holds a database whose
    ledger is empty."""
    root = tmp_path / "data-dirs"
    placed(head_database, root / "A")
    database = placed(ledger_database, root / name)
    with capture_logs() as events:
        found = totals.ledger_totals_of(database)
    assert found == expected, f"{name!r}: the totals of {database}, not of another file nor None: {found} (errors: {errors_in(events)})"
    print_success(f"{name!r}: read")


def missing_file(folder: Path, ledger: Path) -> Path:
    return folder / "app.db"


def a_folder(folder: Path, ledger: Path) -> Path:
    path = folder / "app.db"
    path.mkdir()
    return path


def not_a_database(folder: Path, ledger: Path) -> Path:
    path = folder / "app.db"
    path.write_bytes(b"these are not the bytes of a SQLite database\n" * 100)
    return path


def an_empty_file(folder: Path, ledger: Path) -> Path:
    path = folder / "app.db"
    path.write_bytes(b"")
    return path


def truncated(folder: Path, ledger: Path) -> Path:
    """The first two pages of the ledger's database: its schema says more tables than the file holds."""
    path = folder / "app.db"
    path.write_bytes(ledger.read_bytes()[: 2 * 4096])
    return path


def without_the_ledger(folder: Path, ledger: Path) -> Path:
    """A SQLite database that is not LibreFolio's: no ``transactions`` table."""
    path = folder / "app.db"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO users (name) VALUES ('ada')")
    return path


def a_sum_out_of_range(folder: Path, ledger: Path) -> Path:
    """An amount of 1e300: J's exact context (60 digits) refuses to round it."""
    path = folder / "app.db"
    shutil.copyfile(ledger, path)
    cases.execute(path, f"INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES (1, NULL, 'DEPOSIT', '2026-09-01', 0, 1e300, 'EUR', '{cases.CREATED}', '{cases.CREATED}')")
    return path


UNREADABLE = [
    pytest.param(missing_file, id="missing"),
    pytest.param(a_folder, id="a-folder"),
    pytest.param(not_a_database, id="not-a-database"),
    pytest.param(an_empty_file, id="an-empty-file"),
    pytest.param(truncated, id="truncated"),
    pytest.param(without_the_ledger, id="not-librefolio-s"),
    pytest.param(a_sum_out_of_range, id="a-decimal-trap"),
]


@pytest.mark.parametrize("make", UNREADABLE)
def test_what_it_cannot_read_is_none_and_one_error_without_a_path(totals, ledger_database, tmp_path, make):
    """(a) Never raises: ``None``, one error naming the exception's type alone; nothing created or changed where it
    looked (a missing file stays missing, an empty file empty)."""
    folder = tmp_path / "data"
    folder.mkdir()
    database = make(folder, ledger_database)
    before = cases.fingerprint(folder)
    mtime = database.stat().st_mtime_ns if database.is_file() else None
    with capture_logs() as events:
        try:
            found = totals.ledger_totals_of(database)
        except Exception as exc:
            pytest.fail(f"ledger_totals_of raised {type(exc).__name__}: {exc}: it never raises")
    assert found is None, f"nothing read: None, not {found}"
    error = the_read_error(events, database)
    assert cases.fingerprint(folder) == before, f"nothing created or changed: {cases.changed(before, cases.fingerprint(folder))}"
    assert (database.stat().st_mtime_ns if database.is_file() else None) == mtime, "the file's mtime as it was"
    print_success(f"{make.__name__}: None, error={error}")


@pytest.mark.asyncio
async def test_inside_a_running_event_loop_it_is_none_and_one_error(totals, ledger_database, tmp_path):
    """(a) Called from the event loop (it never should: it runs a loop of its own): ``None``, and the error says
    ``RuntimeError``."""
    database = placed(ledger_database, tmp_path / "copy")
    with capture_logs() as events:
        try:
            found = totals.ledger_totals_of(database)
        except Exception as exc:
            pytest.fail(f"ledger_totals_of raised {type(exc).__name__}: {exc}: it never raises")
    assert found is None, f"inside a running loop: None, not {found}"
    assert the_read_error(events, database) == "RuntimeError", "the error names the exception's type"
    print_success("running loop: None, error=RuntimeError")


# =============================================================================
# (b) compare_totals
# =============================================================================


#: (recorded, current, status): the decision order of contract §1 as §7 refines it, each step pinned against the next.
#: What J's ``from_json`` refuses for B (amounts not plain, lines not lists, rows not objects: one rule, J's, B-22) is
#: pinned by ``NOT_PLAIN`` below, and what it refuses on the copy (B-29) by ``REFUSED_ON_THE_COPY``, with J's
#: ``from_json`` watched.
DECISIONS = [
    pytest.param(None, CURRENT, "absent", id="1-nothing-recorded"),
    pytest.param(None, None, "absent", id="1-nothing-recorded-nothing-read"),
    pytest.param(with_version(99), CURRENT, "other_version", id="2-version-99"),
    pytest.param(with_version(2), CURRENT, "other_version", id="2-version-2"),
    pytest.param(with_version(0), CURRENT, "other_version", id="2-version-0"),
    pytest.param(with_version(-1), CURRENT, "other_version", id="2-version-negative"),
    pytest.param({"version": 99}, CURRENT, "other_version", id="2-before-the-lines-are-read"),
    pytest.param({"version": 99, "cash": "of another shape"}, CURRENT, "other_version", id="2-another-shape"),
    pytest.param(with_version(99, with_amount("balance", "1E+3")), CURRENT, "other_version", id="2-before-the-amounts-are-read"),
    pytest.param(with_version(99), None, "other_version", id="2-before-unreadable"),
    pytest.param(with_version("1"), CURRENT, "absent", id="3-version-a-string"),
    pytest.param(with_version(True), CURRENT, "absent", id="3-version-true"),
    pytest.param(with_version(False), CURRENT, "absent", id="3-version-false"),
    pytest.param(with_version(1.0), CURRENT, "absent", id="3-version-a-float"),
    pytest.param(with_version(None), CURRENT, "absent", id="3-version-null"),
    pytest.param({"cash": [], "quantities": []}, CURRENT, "absent", id="3-no-version"),
    pytest.param({"version": 1}, CURRENT, "absent", id="3-no-lines"),
    pytest.param({**CURRENT, "quantities": [{"broker_id": 1, "asset_id": 7}]}, CURRENT, "absent", id="3-a-line-without-its-amount"),
    pytest.param(document(cash=[("1", "EUR", "1.5")]), CURRENT, "absent", id="3-a-broker-not-an-id"),
    pytest.param(document(cash=[(1, "", "1.5")]), CURRENT, "absent", id="3-no-currency"),
    pytest.param([CURRENT], CURRENT, "absent", id="3-a-list"),
    pytest.param("version 1", CURRENT, "absent", id="3-a-string"),
    pytest.param(1, CURRENT, "absent", id="3-a-number"),
    pytest.param(with_amount("balance", "1,5"), None, "absent", id="3-before-unreadable"),
    pytest.param(with_amount("balance", "1,5"), with_amount("quantity", "1" + "0" * 60), "absent", id="3-before-what-j-refuses-on-the-copy"),
    pytest.param(CURRENT, None, "unreadable", id="4-nothing-read"),
    pytest.param(document(), None, "unreadable", id="4-nothing-read-of-an-empty-ledger"),
    pytest.param(CURRENT, with_amount("quantity", "1" + "0" * 60), "unreadable", id="4-what-j-refuses-on-the-copy"),
    pytest.param(copy.deepcopy(CURRENT), CURRENT, "same", id="5-equal"),
    pytest.param(document(), document(), "same", id="5-two-empty-ledgers"),
    pytest.param(
        document(cash=[(1, "EUR", "1500.250"), (1, "USD", "-20.0"), (2, "CHF", "0.0000010")], quantities=[(1, 7, "10.000000"), (2, 7, "0.50")]),
        CURRENT,
        "same",
        id="5-the-same-amounts-written-otherwise",
    ),
    pytest.param({**CURRENT, "cash": CURRENT["cash"][::-1], "quantities": CURRENT["quantities"][::-1]}, CURRENT, "same", id="5-the-lines-in-another-order"),
    pytest.param({**CURRENT, "cash": [*CURRENT["cash"], {"broker_id": 3, "currency": "JPY", "balance": "0"}]}, CURRENT, "same", id="5-an-explicit-zero-line"),
    pytest.param({**CURRENT, "quantities": [{"broker_id": 1, "asset_id": 3, "quantity": "-0.000"}, *CURRENT["quantities"]]}, CURRENT, "same", id="5-a-zero-line-written-otherwise"),
    pytest.param(document(cash=[(1, "EUR", "1500.26"), (1, "USD", "-20"), (2, "CHF", "0.000001")], quantities=[(1, 7, "10"), (2, 7, "0.5")]), CURRENT, "changed", id="6-an-amount"),
    pytest.param(document(), CURRENT, "changed", id="6-lines-added"),
    pytest.param(CURRENT, document(), "changed", id="6-lines-gone"),
]


@pytest.mark.parametrize(("recorded", "current", "status"), DECISIONS)
def test_the_status_follows_the_decision_order(totals, recorded, current, status):
    """(b) Never raises. ``changed`` comes from the differences, so it always lists one line at least; every other status
    lists none, and counts 0."""
    try:
        comparison = totals.compare_totals(recorded, current)
    except Exception as exc:
        pytest.fail(f"compare_totals raised {type(exc).__name__}: {exc}: it never raises")
    assert comparison.status == status, f"recorded {recorded!r}, current {current!r}: {status}, not {comparison.status}"
    if status == "changed":
        assert 0 < comparison.differences_count == len(comparison.differences), f"changed: the differences, counted: {comparison.differences_count}, {lines_of(comparison)}"
    else:
        assert (comparison.differences, comparison.differences_count) == ((), 0), f"{status}: no difference: {comparison.differences}, {comparison.differences_count}"
    print_success(status)


#: Recorded documents J's ``from_json`` refuses (J-27), and B with it, keeping no rule of its own (B-22): ``CURRENT``
#: with one amount that is not plain decimal text (before J-27, J read most of them, and expanded the first two in full),
#: or lines that are not a list of objects. ``absent``: J gets the document, and refuses it.
NOT_PLAIN = [
    pytest.param(with_amount("balance", "1E+999999999"), id="balance-an-exponent-of-a-billion-digits"),
    pytest.param(with_amount("quantity", "1E+999999999"), id="quantity-an-exponent-of-a-billion-digits"),
    pytest.param(with_amount("balance", "1500.25E0"), id="an-exponent"),
    pytest.param(with_amount("balance", 1500.25), id="balance-a-number"),
    pytest.param(with_amount("quantity", 10), id="quantity-a-number"),
    pytest.param(with_amount("balance", "1" * 61), id="61-digits"),
    pytest.param(with_amount("balance", "1." + "0" * 61), id="61-decimals"),
    pytest.param(with_amount("balance", "+1500.25"), id="a-plus-sign"),
    pytest.param(with_amount("quantity", "10."), id="a-point-without-decimals"),
    pytest.param(with_amount("quantity", ".5"), id="decimals-without-units"),
    pytest.param(with_amount("balance", " 1500.25"), id="a-space"),
    pytest.param(with_amount("quantity", "١٠"), id="digits-that-are-not-ascii"),
    pytest.param(with_amount("balance", "NaN"), id="not-a-number"),
    pytest.param(with_amount("balance", "1,5"), id="a-comma"),
    pytest.param({**CURRENT, "cash": {"broker_id": 1, "currency": "EUR", "balance": "1500.25"}}, id="cash-not-a-list"),
    pytest.param({**CURRENT, "quantities": "10"}, id="quantities-not-a-list"),
    pytest.param({**CURRENT, "cash": None}, id="cash-null"),
    pytest.param({**CURRENT, "cash": [*CURRENT["cash"], "not a row"]}, id="a-row-not-an-object"),
    pytest.param({**CURRENT, "quantities": [[1, 7, "10"]]}, id="a-row-a-list"),
]


@pytest.mark.parametrize("recorded", NOT_PLAIN)
def test_what_is_not_plain_text_in_lines_of_objects_is_refused_by_j_and_absent(totals, j_reads, recorded):
    """(b) B-22, one rule in one home, J's (J-27): B keeps no copy of it, so the recorded document reaches J's
    ``from_json``, which refuses it, and the status is ``absent``, without a difference. An amount that is not plain text
    is refused by the test's wrapper on J's behalf, before J's own code runs: nothing is expanded here, even if J
    regressed."""
    comparison = totals.compare_totals(recorded, CURRENT)
    assert (comparison.status, comparison.differences, comparison.differences_count) == ("absent", (), 0), f"refused by J: absent without a difference, not {comparison.status} with {comparison.differences_count}"
    answers = [answer for given, answer in j_reads if given == recorded]
    assert answers == ["refused"], f"the recorded document reaches J's from_json once, and J refuses it: J's answers to it {answers}, {len(j_reads)} documents given to J in all"
    print_success("absent, refused by J")


@pytest.mark.parametrize("amount", ["9" * 60, "-" + "9" * 60, "0." + "0" * 59 + "1", "9" * 60 + "." + "9" * 60], ids=["60-digits", "60-digits-negative", "60-decimals", "60-and-60"])
def test_sixty_digits_on_each_side_of_the_point_are_plain(totals, j_reads, amount):
    """(b) §7.3's bound itself is read, and compared: the line, absent on the copy, is the one difference."""
    comparison = totals.compare_totals(document(cash=[(5, "EUR", amount)]), document())
    assert (comparison.status, lines_of(comparison)) == ("changed", [("cash", 5, "EUR", None, amount, None)]), f"{len(amount)} characters: read and compared: {comparison.status}, {lines_of(comparison)}"
    print_success(f"{len(amount)} characters: read")


#: What may be read on the copy that J's ``from_json`` refuses (B-29, E's R13-SEC2): ``CURRENT`` with one line spoiled.
#: J's ``to_json`` writes every amount in plain text, so the exact sum 1E+60 is written with 61 digits, past the 60 its
#: ``from_json`` reads back (E's example: 1E+70, 71 digits); the others stand for a document spoiled otherwise. An
#: amount that is not plain text is refused by the test's wrapper on J's behalf, never expanded.
REFUSED_ON_THE_COPY = [
    pytest.param(with_amount("quantity", "1" + "0" * 60), id="61-digits-the-exact-1E+60-as-j-writes-it"),
    pytest.param(with_amount("balance", "1E+999999999"), id="an-exponent-of-a-billion-digits"),
    pytest.param({**CURRENT, "cash": [*CURRENT["cash"], "not a line"]}, id="a-line-not-an-object"),
    pytest.param({**CURRENT, "quantities": [{"broker_id": 1, "asset_id": 7}]}, id="a-line-without-its-amount"),
]


def warnings_and_above(events: list[dict]) -> list[dict]:
    """What was logged at WARNING or above, each event as it was logged."""
    return [event for event in events if event.get("log_level") in ("warning", "error", "critical")]


@pytest.mark.parametrize("current", REFUSED_ON_THE_COPY)
def test_what_j_refuses_on_the_copy_is_unreadable_with_one_warning(totals, j_reads, current):
    """(b) B-29 (E's R13-SEC2): the copy's totals, which J's ``from_json`` gets and refuses, are ``unreadable``: no
    difference, a count of 0, never an exception, which would end the whole check ``stage_failed``. One warning, «The
    control totals of the copy cannot be read: they are not compared», and nothing else in it: no amount, no value, no
    exception message, as the recorded side's own warning."""
    with capture_logs() as events:
        try:
            comparison = totals.compare_totals(copy.deepcopy(CURRENT), current)
        except Exception as exc:
            pytest.fail(f"compare_totals raised {type(exc).__name__}: {exc}: it never raises, and what J refuses on the copy is unreadable")
    assert (comparison.status, comparison.differences, comparison.differences_count) == ("unreadable", (), 0), f"refused by J on the copy: unreadable without a difference, not {comparison.status} with {comparison.differences_count}"
    answers = [answer for given, answer in j_reads if given == current]
    assert answers == ["refused"], f"the copy's document reaches J's from_json once, and J refuses it: J's answers to it {answers}"
    assert warnings_and_above(events) == [{"event": COPY_UNREADABLE, "log_level": "warning"}], f"one warning, its event alone: {warnings_and_above(events)}"
    print_success("unreadable, one warning")


def test_a_recorded_document_j_refuses_is_absent_whatever_is_read_on_the_copy(totals, j_reads):
    """(b) B-29, the decision order kept (a guard, green from the start): the recorded side is decided first. Refused by
    J (61 digits), it is ``absent``, with its own warning alone, though J would refuse the copy's too (an exponent): the
    copy is never judged, and its warning never logged."""
    recorded, current = with_amount("balance", "1" + "0" * 60), with_amount("balance", "1E+999999999")
    with capture_logs() as events:
        try:
            comparison = totals.compare_totals(recorded, current)
        except Exception as exc:
            pytest.fail(f"compare_totals raised {type(exc).__name__}: {exc}: it never raises")
    assert (comparison.status, comparison.differences, comparison.differences_count) == ("absent", (), 0), f"the recorded side refused first: absent, not {comparison.status} with {comparison.differences_count}"
    assert warnings_and_above(events) == [{"event": RECORDED_UNREADABLE, "log_level": "warning"}], f"the recorded side's warning alone: {warnings_and_above(events)}"
    print_success("absent first, the copy never judged")


#: Two readings of a ledger, and their differences in order. Equal on both sides, left out: (2, USD) and (2, asset 5).
RECORDED = document(cash=[(1, "EUR", "100"), (1, "GBP", "5"), (2, "USD", "-3"), (10, "EUR", "1")], quantities=[(1, 9, "2"), (1, 10, "7"), (2, 4, "1"), (2, 5, "6")])
READ = document(cash=[(1, "CHF", "2"), (1, "EUR", "100.5"), (2, "USD", "-3"), (9, "CHF", "0.000001"), (10, "EUR", "2")], quantities=[(1, 9, "3"), (1, 10, "8"), (2, 5, "6"), (3, 1, "4")])
DIFFERENCES = [
    ("cash", 1, "CHF", None, None, "2"),
    ("cash", 1, "EUR", None, "100", "100.5"),
    ("cash", 1, "GBP", None, "5", None),
    ("cash", 9, "CHF", None, None, "0.000001"),
    ("cash", 10, "EUR", None, "1", "2"),
    ("quantity", 1, None, 9, "2", "3"),
    ("quantity", 1, None, 10, "7", "8"),
    ("quantity", 2, None, 4, "1", None),
    ("quantity", 3, None, 1, None, "4"),
]


def test_the_differences_are_listed_cash_first_by_broker_then_currency_or_asset(totals):
    """(b) Brokers and assets in numeric order (9 before 10), currencies in alphabetical order; a line absent on a side is
    ``None`` there; the lines equal on both sides are left out. The documents given are left as they were."""
    print_section("compare_totals")
    recorded, current = copy.deepcopy(RECORDED), copy.deepcopy(READ)
    comparison = totals.compare_totals(recorded, current)
    assert comparison.status == "changed", f"changed: {comparison.status}"
    assert lines_of(comparison) == DIFFERENCES, f"every difference, in order: {lines_of(comparison)}"
    assert comparison.differences_count == len(DIFFERENCES), f"all counted: {comparison.differences_count}"
    assert (recorded, current) == (RECORDED, READ), "the documents given are never changed"
    print_success(f"{len(DIFFERENCES)} differences, in order")


def test_the_amounts_of_a_difference_are_j_s_canonical_text(totals):
    """(b) As J reads them: no trailing zero, whatever the plain text recorded; a zero line is no line (``None``)."""
    recorded = document(cash=[(1, "EUR", "10.50"), (1, "USD", "0")], quantities=[(1, 7, "10.000"), (1, 8, "-0.250")])
    current = document(cash=[(1, "EUR", "11"), (1, "USD", "4")], quantities=[(1, 7, "12"), (1, 8, "0.25")])
    expected = [("cash", 1, "EUR", None, "10.5", "11"), ("cash", 1, "USD", None, None, "4"), ("quantity", 1, None, 7, "10", "12"), ("quantity", 1, None, 8, "-0.25", "0.25")]
    found = lines_of(totals.compare_totals(recorded, current))
    assert found == expected, f"canonical text, a zero line as None: {found}"
    print_success("10.50 → 10.5, 10.000 → 10, -0.250 → -0.25, 0 → None")


@pytest.mark.parametrize("count", [20, 21, 45])
def test_the_first_20_differences_are_kept_and_all_are_counted(totals, count):
    """(b) ``MAX_DIFFERENCES``: 15 cash lines then quantities, recorded and gone: the first 20 in order (the cash, then
    the positions of assets 1 to 5, numerically: 10 comes after 9), every one counted."""
    assert totals.MAX_DIFFERENCES == 20, f"20 differences kept: {totals.MAX_DIFFERENCES}"
    cash = [(1, f"C{index:02d}", "1") for index in range(min(count, 15))]
    quantities = [(1, asset_id, "1") for asset_id in range(1, count - 15 + 1)]
    comparison = totals.compare_totals(document(cash=cash, quantities=quantities), document())
    kept = [("cash", 1, f"C{index:02d}", None, "1", None) for index in range(15)] + [("quantity", 1, None, asset_id, "1", None) for asset_id in range(1, 6)]
    assert (comparison.status, comparison.differences_count) == ("changed", count), f"{count} differences counted: {comparison.status}, {comparison.differences_count}"
    assert lines_of(comparison) == kept, f"the first 20, in order: {lines_of(comparison)}"
    print_success(f"{count}: 20 kept, {count} counted")


def test_a_comparison_and_its_differences_are_frozen(totals):
    comparison = totals.compare_totals(RECORDED, READ)
    assert isinstance(comparison.differences, tuple), f"a tuple: {type(comparison.differences).__name__}"
    with pytest.raises((AttributeError, TypeError, ValueError)):
        comparison.status = "same"
    with pytest.raises((AttributeError, TypeError, ValueError)):
        comparison.differences[0].before = "0"
    print_success("frozen")

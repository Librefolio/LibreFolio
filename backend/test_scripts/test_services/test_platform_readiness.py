"""
Readiness of the instance (workstream H, platform, checkpoint CP5a).

Under test: ``backend/app/services/platform/readiness.py``, which answers ``GET /system/ready``.
``check_readiness(session)`` returns a ``ReadinessResponse``:

(a) ``database`` is ``ok`` when the database answers ``SELECT 1``, ``unreachable`` otherwise, and then ``migrations``
    is ``unknown``;
(b) ``migrations`` is ``ok`` when ``alembic_version`` holds exactly one row, the head revision of the migration
    scripts; ``mismatch`` when its one row is another revision; ``unknown`` when the head cannot be read (no
    ``alembic.ini``, no revision, several heads), the table is missing, or it holds no row or several;
(c) ``status`` is ``ready`` only when both checks are ``ok``, ``not_ready`` otherwise;
(d) the head is read from the migration scripts once per process, in a worker thread and never on the event loop (the
    read is synchronous I/O); a failed read is not kept, the next check reads again;
(e) the response carries one code per check and nothing else: no revision id, no database path, no error text. The
    details go to the log, once per change of state.

Pure: every database is a throwaway SQLite file under ``tmp_path``, prepared with ``sqlite3`` and checked through an
aiosqlite engine of the test's own, disposed at teardown. The head is read from the repository's migration scripts
(read only), or from a tree of scripts under ``tmp_path``. The module's logger is replaced by a recorder, and its head
cache and its last logged state are reset around each test. No server, no shared database, no network.
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.system import ReadinessResponse
from backend.app.services.platform import readiness
from backend.app.services.platform.readiness import check_readiness
from backend.test_scripts.test_utils import print_section, print_success

ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
#: A revision id no migration script carries: the database of a mismatch is at this one.
OTHER_REVISION = "0123456789ab"
#: Stands for the head revision in the parameters below, which are built before the head is read.
HEAD = "<head>"

# H-62 (contract L3 §6): ``ReadinessResponse.mode``, normal outside the «awaiting restore» mode; red until H-62
READY = {"status": "ready", "checks": {"database": "ok", "migrations": "ok"}, "mode": "normal"}


def _not_ready(database: str, migrations: str) -> dict:
    return {"status": "not_ready", "checks": {"database": database, "migrations": migrations}, "mode": "normal"}


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(scope="module")
def head() -> str:
    """The head revision of the repository's migration scripts, read here without the module under test."""
    revision = ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()
    assert isinstance(revision, str) and revision, f"Precondition: the migration scripts of {ALEMBIC_INI} have one head, got {revision!r}"
    assert revision != OTHER_REVISION, f"Precondition: {OTHER_REVISION!r} must not be the head revision"
    return revision


class LogRecorder:
    """Stands in for the module's structlog logger: one ``(level, event, fields)`` per call."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    def debug(self, event: str, **fields) -> None:
        self.records.append(("debug", event, fields))

    def info(self, event: str, **fields) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields) -> None:
        self.records.append(("error", event, fields))


@pytest.fixture(autouse=True)
def logged(monkeypatch) -> list[tuple[str, str, dict]]:
    """The module's log, recorded; and its last logged state empty, as in a process that has not checked yet."""
    recorder = LogRecorder()
    monkeypatch.setattr(readiness, "logger", recorder)
    monkeypatch.setattr(readiness, "_logged", [])
    return recorder.records


@pytest.fixture(autouse=True)
def fresh_head_cache():
    """Forget the head read by an earlier test, before the test and again after it (a finalizer: also when it fails)."""
    readiness._read_alembic_head.cache_clear()
    yield
    readiness._read_alembic_head.cache_clear()


@pytest.fixture
def head_reads(monkeypatch, head) -> list[str]:
    """Every read of migration scripts: the ``alembic.ini`` given to each ``ScriptDirectory.from_config``.

    Depends on ``head`` so that the test's own read of the head happens before the recording starts.
    """
    reads: list[str] = []
    original = ScriptDirectory.from_config

    def recording_from_config(config, *args, **kwargs):
        reads.append(config.config_file_name)
        return original(config, *args, **kwargs)

    monkeypatch.setattr(ScriptDirectory, "from_config", recording_from_config)
    return reads


def _make_database(path: Path, revisions: list[str] | None) -> Path:
    """A SQLite file at ``path``: without an ``alembic_version`` table when ``revisions`` is None, else one row per revision.

    The table is the one Alembic creates. Another table makes the file a database even without it.
    """
    with contextlib.closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE app_data (id INTEGER PRIMARY KEY)")
        if revisions is not None:
            connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))")
            connection.executemany("INSERT INTO alembic_version (version_num) VALUES (?)", [(revision,) for revision in revisions])
    return path


@asynccontextmanager
async def _session(path: Path) -> AsyncIterator[AsyncSession]:
    """An AsyncSession on the SQLite file ``path``, through an aiosqlite engine of this test, disposed on exit."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    try:
        async with AsyncSession(engine) as session:
            yield session
    finally:
        await engine.dispose()


async def _check(path: Path) -> ReadinessResponse:
    async with _session(path) as session:
        return await check_readiness(session)


def _assert_codes_only(result: ReadinessResponse, *hidden: str) -> None:
    """The serialized response holds none of ``hidden``: a revision id, a path, an error text."""
    serialized = result.model_dump_json()
    leaked = [value for value in hidden if value and value in serialized]
    assert not leaked, f"the readiness response must carry one code per check and nothing else; it holds {leaked}: {serialized}"


class _SessionThatDoesNotAnswer:
    """Stands in for an AsyncSession whose database does not answer: every ``execute`` raises ``error``."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.statements: list[object] = []

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        raise self.error


def _scripts_without_revision(root: Path) -> Path:
    """An ``alembic.ini`` whose script folder holds no revision."""
    (root / "alembic" / "versions").mkdir(parents=True)
    ini = root / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = %(here)s/alembic\npath_separator = os\n")
    return ini


def _scripts_with_two_heads(root: Path) -> Path:
    """An ``alembic.ini`` whose script folder holds two revisions with no parent: two heads."""
    ini = _scripts_without_revision(root)
    for revision in ("aaaa00000001", "bbbb00000002"):
        (root / "alembic" / "versions" / f"{revision}_branch.py").write_text(f'revision = "{revision}"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n')
    return ini


#: The ways the head cannot be read, each a factory of the ``alembic.ini`` the module is pointed at, under a folder.
UNREADABLE_HEADS: list = [
    pytest.param(lambda root: root / "missing" / "alembic.ini", id="no-alembic-ini"),
    pytest.param(_scripts_without_revision, id="no-revision"),
    pytest.param(_scripts_with_two_heads, id="several-heads"),
]


# =============================================================================
# (a)-(c) THE CODES
# =============================================================================


@pytest.mark.asyncio
class TestReadinessCodes:
    """One code per check, and ``ready`` only when both are ``ok``."""

    async def test_one_row_at_the_head_is_ready(self, tmp_path, head):
        print_section("Readiness: alembic_version at the head")
        database = _make_database(tmp_path / "app.db", [head])

        result = await _check(database)

        assert result.model_dump() == READY, f"one row at the head {head!r}: the instance is ready, got {result.model_dump()}"
        print_success("✓ At the head: ready, database ok, migrations ok")

    @pytest.mark.parametrize(
        ("revisions", "migrations"),
        [
            pytest.param([OTHER_REVISION], "mismatch", id="mismatch-another-revision"),
            pytest.param(None, "unknown", id="unknown-no-alembic-version-table"),
            pytest.param([], "unknown", id="unknown-empty-alembic-version"),
            pytest.param([HEAD, OTHER_REVISION], "unknown", id="unknown-two-rows-one-at-the-head"),
        ],
    )
    async def test_a_database_not_at_the_head_is_not_ready(self, tmp_path, head, revisions, migrations):
        """The database answers, its revision is another one (mismatch) or cannot be told (unknown): not ready, and codes only."""
        print_section(f"Readiness: alembic_version {revisions!r} → {migrations}")
        stored = None if revisions is None else [head if revision == HEAD else revision for revision in revisions]
        database = _make_database(tmp_path / "app.db", stored)

        result = await _check(database)

        assert result.model_dump() == _not_ready("ok", migrations), f"alembic_version {stored!r} against the head {head!r}: expected migrations {migrations!r}, got {result.model_dump()}"
        _assert_codes_only(result, head, OTHER_REVISION, str(database), "alembic_version", "no such table")
        print_success(f"✓ {migrations}: not ready, codes only")

    async def test_a_database_that_cannot_be_opened_is_unreachable(self, tmp_path, head):
        print_section("Readiness: a database file that cannot be opened")
        missing = tmp_path / "no-such-folder" / "app.db"

        result = await _check(missing)

        assert result.model_dump() == _not_ready("unreachable", "unknown"), f"{missing} cannot be opened: expected unreachable and unknown, got {result.model_dump()}"
        _assert_codes_only(result, head, str(missing), "unable to open")
        assert not missing.parent.exists(), "the check must create nothing"
        print_success("✓ Cannot be opened: unreachable, migrations unknown")

    async def test_a_session_that_does_not_answer_is_unreachable_and_the_detail_goes_to_the_log(self, tmp_path, head, logged):
        print_section("Readiness: a session whose database does not answer")
        location = str(tmp_path / "remote" / "app.db")
        error_text = f"disk I/O error reading {location}"
        session = _SessionThatDoesNotAnswer(OperationalError("SELECT 1", {}, Exception(error_text)))

        result = await check_readiness(session)  # type: ignore[arg-type]

        assert len(session.statements) == 1, f"Barrier: the database was asked once, then given up on: {session.statements}"
        assert result.model_dump() == _not_ready("unreachable", "unknown"), f"a database that does not answer: expected unreachable and unknown, got {result.model_dump()}"
        _assert_codes_only(result, head, location, error_text, "disk I/O")
        warnings = [fields for level, _event, fields in logged if level == "warning"]
        assert len(warnings) == 1 and error_text in warnings[0].get("problem", ""), f"the error must go to the log, once: {logged}"
        print_success("✓ No answer: unreachable in the response, the error in the log only")


# =============================================================================
# (d) THE HEAD REVISION: READ ONCE, OFF THE EVENT LOOP, A FAILURE NOT KEPT
# =============================================================================


def _loop_runs_here() -> bool:
    """Whether an event loop runs in the calling thread: ``asyncio.get_running_loop()`` raises ``RuntimeError`` where none does."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


@pytest.mark.asyncio
class TestHeadRevision:
    """The head is read from the migration scripts once per process, off the event loop, and read again after a failure."""

    async def test_the_head_is_read_off_the_event_loop(self, tmp_path, monkeypatch, head):
        """The read parses ``alembic.ini`` and imports the migration scripts, synchronous I/O: it runs in a worker thread, where no loop runs."""
        database = _make_database(tmp_path / "app.db", [head])
        real_head_revision = readiness.alembic_head_revision
        reads: list[tuple[int, bool]] = []

        def recording_head_revision() -> str | None:
            reads.append((threading.get_ident(), _loop_runs_here()))
            return real_head_revision()

        monkeypatch.setattr(readiness, "alembic_head_revision", recording_head_revision)
        loop_thread = threading.get_ident()
        # Presence barrier: the probe sees the loop where it runs, so "no loop" in the recorder is about its thread.
        assert _loop_runs_here(), "Barrier: the test runs on the event loop, and the probe must see the loop there"

        result = await _check(database)

        assert len(reads) == 1, f"one check must read the head once, through alembic_head_revision: {reads}"
        read_thread, loop_in_read_thread = reads[0]
        assert read_thread != loop_thread, f"the head was read in the event loop's thread ({loop_thread}): the synchronous read blocks the loop"
        assert loop_in_read_thread is False, f"the head was read in a thread where an event loop runs: {reads}"
        assert result.model_dump() == READY, f"the recorder returned the real head {head!r} and the database is at it: got {result.model_dump()}"

    async def test_the_head_is_read_once_for_several_checks(self, tmp_path, head, head_reads):
        at_head = _make_database(tmp_path / "at-head.db", [head])
        elsewhere = _make_database(tmp_path / "elsewhere.db", [OTHER_REVISION])

        results = [await _check(at_head), await _check(elsewhere), await _check(at_head)]

        assert [result.checks.migrations for result in results] == ["ok", "mismatch", "ok"], f"Barrier: each check compared against the head: {results}"
        assert head_reads == [str(ALEMBIC_INI)], f"three checks must read the migration scripts once, from {ALEMBIC_INI}: {head_reads}"

    @pytest.mark.parametrize("make_ini", UNREADABLE_HEADS)
    async def test_an_unreadable_head_is_unknown_and_read_again_next_time(self, tmp_path, monkeypatch, head, head_reads, make_ini: Callable[[Path], Path]):
        """The database is at the head and the scripts cannot be read: unknown. Once readable again, the next check reads and is ready."""
        database = _make_database(tmp_path / "app.db", [head])
        broken_ini = make_ini(tmp_path / "scripts")
        monkeypatch.setattr(readiness, "_ALEMBIC_INI", broken_ini)

        first = await _check(database)

        assert head_reads == [str(broken_ini)], f"Barrier: the check read the scripts of {broken_ini}: {head_reads}"
        assert first.model_dump() == _not_ready("ok", "unknown"), f"the head cannot be read from {broken_ini}: expected migrations unknown, got {first.model_dump()}"
        _assert_codes_only(first, head, str(broken_ini), str(tmp_path), "aaaa00000001", "bbbb00000002", "script_location")

        monkeypatch.setattr(readiness, "_ALEMBIC_INI", ALEMBIC_INI)
        second = await _check(database)

        assert head_reads == [str(broken_ini), str(ALEMBIC_INI)], f"a failed read must not be kept: the next check must read the scripts again: {head_reads}"
        assert second.model_dump() == READY, f"the scripts are readable again and the database is at their head: got {second.model_dump()}"


def test_alembic_head_revision_is_none_when_the_head_cannot_be_read(tmp_path, monkeypatch, logged):
    """The error is not raised to the caller: it goes to the debug log."""
    monkeypatch.setattr(readiness, "_ALEMBIC_INI", tmp_path / "missing" / "alembic.ini")

    assert readiness.alembic_head_revision() is None
    assert [level for level, _event, _fields in logged] == ["debug"], f"one debug record for the failed read: {logged}"


# =============================================================================
# (e) THE LOG: ONCE PER CHANGE OF STATE
# =============================================================================


@pytest.mark.asyncio
async def test_each_change_of_state_is_logged_once(tmp_path, head, logged):
    """ready, ready, mismatch, mismatch, ready: three records. The mismatch record names both revisions, the response none."""
    at_head = _make_database(tmp_path / "at-head.db", [head])
    elsewhere = _make_database(tmp_path / "elsewhere.db", [OTHER_REVISION])

    results = [await _check(database) for database in (at_head, at_head, elsewhere, elsewhere, at_head)]

    assert [result.status for result in results] == ["ready", "ready", "not_ready", "not_ready", "ready"], f"Barrier: the five checks: {results}"
    states = [(level, fields.get("database"), fields.get("migrations")) for level, _event, fields in logged if level != "debug"]
    assert states == [("info", "ok", "ok"), ("warning", "ok", "mismatch"), ("info", "ok", "ok")], f"one record per change of state, not per check: {logged}"
    problem = next(fields.get("problem", "") for level, _event, fields in logged if level == "warning")
    assert head in problem and OTHER_REVISION in problem, f"the log names both revisions, for the operator: {problem!r}"

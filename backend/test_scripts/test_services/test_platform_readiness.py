"""
Readiness of the instance (workstream H, platform, checkpoint CP5a).

Under test: ``backend/app/services/platform/readiness.py``, which answers ``GET /system/ready``.
``check_readiness(session)`` returns a ``ReadinessResponse``:

(a) ``database`` is ``ok`` when the database answers ``SELECT 1``, ``unreachable`` otherwise, and then ``migrations``
    is ``unknown``;
(b) ``migrations`` is ``ok`` when ``alembic_version`` holds exactly one row, the head revision of the migration
    scripts; ``behind`` when its one row is a revision the scripts know but not the head (a migration was not applied
    or failed); ``ahead`` when it is a revision the scripts do not know (the database is newer than the image, or from
    another LibreFolio); ``unknown`` when the head cannot be read (no ``alembic.ini``, no revision, several heads),
    the table is missing, or it holds no row or several;
(c) ``status`` is ``ready`` only when both checks are ``ok``, ``not_ready`` otherwise;
(d) the head, and the revisions the scripts know, are read from the migration scripts once per process, in a worker
    thread and never on the event loop (the read is synchronous I/O); a failed read is not kept, the next check reads
    again;
(e) ``database_revision`` is the one row of ``alembic_version`` whenever it can be read (also when ``behind`` or
    ``ahead``, also when the head cannot be read), ``None`` when the database is unreachable, the table is missing or
    it does not hold exactly one row. Besides it the response carries one code per check and the mode: no error text,
    no database path, no revision id other than the database's own (the head is never in it). The details go to the
    log, once per change of state (developer decision, 25/10/2026).

Pure: every database is a throwaway SQLite file under ``tmp_path``, prepared with ``sqlite3`` and checked through an
aiosqlite engine of the test's own, disposed at teardown. The head is read from the repository's migration scripts
(read only), or from a tree of scripts under ``tmp_path``. The module's logger is replaced by a recorder, and its head
cache and its last logged state are reset around each test. ``behind`` and ``ahead`` are also checked against a tree
of scripts under ``tmp_path`` with a chain of three revisions, independent of the repository's migrations. No server, no shared database, no network.
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
#: A revision id no migration script carries: the database of an ``ahead`` is at this one.
OTHER_REVISION = "0123456789ab"
#: Stand for the head revision and for a revision the scripts know that is not the head, in the parameters below,
#: which are built before the scripts are read.
HEAD = "<head>"
PREVIOUS = "<previous>"


def _ready(revision: str) -> dict:
    """The answer of a database at the head ``revision``, in the mode ``normal`` (H-62)."""
    return {"status": "ready", "checks": {"database": "ok", "migrations": "ok"}, "database_revision": revision, "mode": "normal"}


def _not_ready(database: str, migrations: str, revision: str | None) -> dict:
    return {"status": "not_ready", "checks": {"database": database, "migrations": migrations}, "database_revision": revision, "mode": "normal"}


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


@pytest.fixture(scope="module")
def previous(head) -> str:
    """A revision of the repository's migration scripts that is not the head: the one before it. Read without the module under test."""
    revisions = [script.revision for script in ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).walk_revisions()]
    assert revisions[0] == head and len(revisions) > 1, f"Precondition: walk_revisions goes from the head down, and the repository has more than one migration: {revisions}"
    assert revisions[1] not in (head, OTHER_REVISION), f"Precondition: the revision before the head is neither the head nor {OTHER_REVISION!r}: {revisions}"
    return revisions[1]


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
    readiness._read_alembic_scripts.cache_clear()
    yield
    readiness._read_alembic_scripts.cache_clear()


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
    """The serialized response holds none of ``hidden`` (a revision id, a path, an error text), ``database_revision`` apart.

    ``database_revision`` is the one place a revision id may be: its value is pinned by each test, so a hidden value
    equal to it (the database at the head) is not a leak, while the same id anywhere else would be.
    """
    serialized = result.model_dump_json(exclude={"database_revision"})
    leaked = [value for value in hidden if value and value in serialized]
    assert not leaked, f"the readiness response must carry one code per check, the mode and the database's revision, and nothing else; it holds {leaked}: {serialized}"


class _SessionThatDoesNotAnswer:
    """Stands in for an AsyncSession whose database does not answer: every ``execute`` raises ``error``."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.statements: list[object] = []

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        raise self.error


def _scripts_with_chain(root: Path) -> tuple[Path, list[str]]:
    """An ``alembic.ini`` whose scripts form one chain of three revisions, oldest first; returns it and the revisions."""
    ini = _scripts_without_revision(root)
    chain = ["cccc00000001", "cccc00000002", "cccc00000003"]
    for parent, revision in zip([None, *chain[:-1]], chain, strict=True):
        (root / "alembic" / "versions" / f"{revision}_chain.py").write_text(f'revision = "{revision}"\ndown_revision = {parent!r}\nbranch_labels = None\ndepends_on = None\n')
    return ini, chain


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

        assert result.model_dump() == _ready(head), f"one row at the head {head!r}: the instance is ready and says its revision, got {result.model_dump()}"
        print_success("✓ At the head: ready, database ok, migrations ok, database_revision the head")

    @pytest.mark.parametrize(
        ("revisions", "migrations", "database_revision"),
        [
            pytest.param([OTHER_REVISION], "ahead", OTHER_REVISION, id="ahead-a-revision-the-scripts-do-not-know"),
            pytest.param([PREVIOUS], "behind", PREVIOUS, id="behind-a-revision-the-scripts-know"),
            pytest.param(None, "unknown", None, id="unknown-no-alembic-version-table"),
            pytest.param([], "unknown", None, id="unknown-empty-alembic-version"),
            pytest.param([HEAD, OTHER_REVISION], "unknown", None, id="unknown-two-rows-one-at-the-head"),
            pytest.param([PREVIOUS, HEAD], "unknown", None, id="unknown-two-rows-both-known"),
        ],
    )
    async def test_a_database_not_at_the_head_is_not_ready(self, tmp_path, head, previous, revisions, migrations, database_revision):
        """The database answers, its revision is one the scripts know (behind) or not (ahead) or cannot be told (unknown): not ready, its revision only when it is one."""
        print_section(f"Readiness: alembic_version {revisions!r} → {migrations}")
        placeholders = {HEAD: head, PREVIOUS: previous}
        stored = None if revisions is None else [placeholders.get(revision, revision) for revision in revisions]
        expected_revision = placeholders.get(database_revision, database_revision)
        database = _make_database(tmp_path / "app.db", stored)

        result = await _check(database)

        assert result.model_dump() == _not_ready("ok", migrations, expected_revision), f"alembic_version {stored!r} against the head {head!r}: expected migrations {migrations!r} and database_revision {expected_revision!r}, got {result.model_dump()}"
        # The head is never in the response, the database's own revision only as database_revision; no path, no error text
        _assert_codes_only(result, head, previous, OTHER_REVISION, str(database), "alembic_version", "no such table")
        print_success(f"✓ {migrations}: not ready, database_revision {expected_revision!r}")

    async def test_behind_and_ahead_follow_the_scripts_not_the_repository(self, tmp_path, monkeypatch, head):
        """Against a tree of scripts of this test (three revisions): the oldest two are behind, the head ok, any other id ahead, whatever the repository's migrations say."""
        ini, chain = _scripts_with_chain(tmp_path / "scripts")
        monkeypatch.setattr(readiness, "_ALEMBIC_INI", ini)
        assert head not in chain and OTHER_REVISION not in chain, f"Precondition: the chain shares no id with the repository's head or {OTHER_REVISION!r}: {chain}"
        expected = {
            chain[0]: "behind",
            chain[1]: "behind",
            chain[2]: "ok",
            head: "ahead",  # the repository's own head is a stranger to this tree
            OTHER_REVISION: "ahead",
        }

        answers = {revision: await _check(_make_database(tmp_path / f"{revision}.db", [revision])) for revision in expected}

        assert {revision: (answer.checks.migrations, answer.database_revision) for revision, answer in answers.items()} == {revision: (migrations, revision) for revision, migrations in expected.items()}, f"each database against the chain {chain}: {answers}"
        for answer in answers.values():
            _assert_codes_only(answer, str(tmp_path))
        assert readiness.alembic_head_revision() == chain[2], f"Barrier: the head read is the tree's, {chain[2]!r}"
        assert readiness._read_alembic_scripts().known == frozenset(chain), f"the scripts know the three revisions of the chain: {readiness._read_alembic_scripts()}"

    async def test_a_database_that_cannot_be_opened_is_unreachable(self, tmp_path, head):
        print_section("Readiness: a database file that cannot be opened")
        missing = tmp_path / "no-such-folder" / "app.db"

        result = await _check(missing)

        assert result.model_dump() == _not_ready("unreachable", "unknown", None), f"{missing} cannot be opened: expected unreachable, unknown and no revision, got {result.model_dump()}"
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
        assert result.model_dump() == _not_ready("unreachable", "unknown", None), f"a database that does not answer: expected unreachable, unknown and no revision, got {result.model_dump()}"
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
        assert result.model_dump() == _ready(head), f"the recorder returned the real head {head!r} and the database is at it: got {result.model_dump()}"

    async def test_the_scripts_are_read_once_for_several_checks(self, tmp_path, head, previous, head_reads):
        at_head = _make_database(tmp_path / "at-head.db", [head])
        elsewhere = _make_database(tmp_path / "elsewhere.db", [OTHER_REVISION])
        older = _make_database(tmp_path / "older.db", [previous])

        results = [await _check(at_head), await _check(elsewhere), await _check(older), await _check(at_head)]

        assert [result.checks.migrations for result in results] == ["ok", "ahead", "behind", "ok"], f"Barrier: each check compared against the head and the known revisions: {results}"
        assert head_reads == [str(ALEMBIC_INI)], f"three checks must read the migration scripts once, from {ALEMBIC_INI}: {head_reads}"

    @pytest.mark.parametrize("make_ini", UNREADABLE_HEADS)
    async def test_an_unreadable_head_is_unknown_and_read_again_next_time(self, tmp_path, monkeypatch, head, head_reads, make_ini: Callable[[Path], Path]):
        """The database is at the head and the scripts cannot be read: unknown. Once readable again, the next check reads and is ready."""
        database = _make_database(tmp_path / "app.db", [head])
        broken_ini = make_ini(tmp_path / "scripts")
        monkeypatch.setattr(readiness, "_ALEMBIC_INI", broken_ini)

        first = await _check(database)

        assert head_reads == [str(broken_ini)], f"Barrier: the check read the scripts of {broken_ini}: {head_reads}"
        assert first.model_dump() == _not_ready("ok", "unknown", head), f"the head cannot be read from {broken_ini}: expected migrations unknown, and the database's revision still told, got {first.model_dump()}"
        _assert_codes_only(first, str(broken_ini), str(tmp_path), "aaaa00000001", "bbbb00000002", "script_location")

        monkeypatch.setattr(readiness, "_ALEMBIC_INI", ALEMBIC_INI)
        second = await _check(database)

        assert head_reads == [str(broken_ini), str(ALEMBIC_INI)], f"a failed read must not be kept: the next check must read the scripts again: {head_reads}"
        assert second.model_dump() == _ready(head), f"the scripts are readable again and the database is at their head: got {second.model_dump()}"


@pytest.mark.asyncio
async def test_an_unreadable_head_still_tells_the_revision_of_the_database(tmp_path, monkeypatch, head_reads):
    """The head cannot be read: unknown, and the database's revision is still the one row, whatever it is."""
    ini = _scripts_without_revision(tmp_path / "scripts")
    monkeypatch.setattr(readiness, "_ALEMBIC_INI", ini)

    result = await _check(_make_database(tmp_path / "app.db", [OTHER_REVISION]))

    assert head_reads == [str(ini)], f"Barrier: the check read the scripts of {ini}: {head_reads}"
    assert result.model_dump() == _not_ready("ok", "unknown", OTHER_REVISION), f"the head is unreadable and the database holds one row: unknown, with the row as database_revision, got {result.model_dump()}"


def test_alembic_head_revision_is_none_when_the_head_cannot_be_read(tmp_path, monkeypatch, logged):
    """The error is not raised to the caller: it goes to the debug log."""
    monkeypatch.setattr(readiness, "_ALEMBIC_INI", tmp_path / "missing" / "alembic.ini")

    assert readiness.alembic_head_revision() is None
    assert [level for level, _event, _fields in logged] == ["debug"], f"one debug record for the failed read: {logged}"


# =============================================================================
# (e) THE LOG: ONCE PER CHANGE OF STATE
# =============================================================================


@pytest.mark.asyncio
async def test_each_change_of_state_is_logged_once(tmp_path, head, previous, logged):
    """ready, ready, behind, behind, ahead, ahead, ready: four records. Behind and ahead each name both revisions, the response only the database's."""
    at_head = _make_database(tmp_path / "at-head.db", [head])
    behind = _make_database(tmp_path / "behind.db", [previous])
    ahead = _make_database(tmp_path / "ahead.db", [OTHER_REVISION])

    results = [await _check(database) for database in (at_head, at_head, behind, behind, ahead, ahead, at_head)]

    assert [result.status for result in results] == ["ready", "ready", "not_ready", "not_ready", "not_ready", "not_ready", "ready"], f"Barrier: the seven checks: {results}"
    assert [result.checks.migrations for result in results] == ["ok", "ok", "behind", "behind", "ahead", "ahead", "ok"], f"Barrier: behind, then ahead: {results}"
    states = [(level, fields.get("database"), fields.get("migrations")) for level, _event, fields in logged if level != "debug"]
    assert states == [("info", "ok", "ok"), ("warning", "ok", "behind"), ("warning", "ok", "ahead"), ("info", "ok", "ok")], f"one record per change of state, not per check: {logged}"
    problems = {fields["migrations"]: fields.get("problem", "") for level, _event, fields in logged if level == "warning"}
    assert head in problems["behind"] and previous in problems["behind"], f"the log names both revisions of a behind, for the operator: {problems['behind']!r}"
    assert head in problems["ahead"] and OTHER_REVISION in problems["ahead"], f"the log names both revisions of an ahead, for the operator: {problems['ahead']!r}"
    for result in results:
        _assert_codes_only(result, head, previous, OTHER_REVISION)

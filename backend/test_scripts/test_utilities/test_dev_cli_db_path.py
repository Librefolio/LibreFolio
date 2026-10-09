"""``dev.py db current|upgrade|downgrade|migrate|check [path]`` must act on ``path`` (N, R2 P0, plan 28_fxDashboardSync/plan-phase00DbPathArgument).

The defect: ``dev.py`` hands Alembic the path only as ``DATABASE_URL`` in its environment. Without
``-x sqlalchemy.url=``, ``backend/alembic/env.py`` uses ``get_settings().DATABASE_URL``, which ``backend/app/config.py``
recomputes from the data directory, overwriting the environment's value. Every command thus works on the configured
database while printing the path it was given, and ``db downgrade <copy>`` rolls the configured one back. ``db check``
runs ``backend/test_scripts/verify_db_check_constraints.py``, which does not exist.

Isolation: every database lives in ``tmp_path``. Each child process gets the runner's environment (``PATH``, ``HOME``,
``PIPENV_CUSTOM_VENV_NAME``: ``dev.py`` starts Alembic with ``pipenv run``) minus ``LIBREFOLIO_*``, ``COVERAGE_*``,
``DATABASE_URL``, ``ALEMBIC_DATABASE_URL``, ``PORT`` and ``TEST_PORT``, then ``LIBREFOLIO_DATA_DIR=<tmp>/configured``,
``LIBREFOLIO_TEST_DATA_DIR=<tmp>/test-lane``, ``LIBREFOLIO_TEST_MODE=0``, ``PIPENV_DONT_LOAD_ENV=1`` and two free
ports. Before any ``dev.py db`` command, a probe through ``pipenv run`` proves that pipenv picks this test's
environment and that the configured databases are the sandbox's. Alembic builds the databases with ``-x`` once per
module (``upgrade head``, then ``downgrade -1`` for head-1) and each test copies them; head and head-1 are read from
the script directory, never written here.

The sentinel: the configured database, ``<tmp>/configured/sqlite/app.db``, which the defect touches instead of the
target. Its bytes are hashed before each command and compared after; a case without one checks that none appears.
"""

import hashlib
import os
import re
import shlex
import shutil
import socket
import sqlite3
import subprocess
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app.config import validate_test_data_dir
from backend.test_scripts.test_utils import print_info, print_section, print_success
from scripts.cli_base import pipenv_prefix

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEV_PY = PROJECT_ROOT / "dev.py"
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
ALEMBIC_SCRIPTS = PROJECT_ROOT / "backend" / "alembic"
VERSIONS_DIR = ALEMBIC_SCRIPTS / "versions"

#: Seconds. Python, pipenv start-up and Alembic take a few, a loaded parallel run more; a hang still ends.
CLI_TIMEOUT = 120
#: Characters of a child's stdout, and of its stderr, quoted by an assertion message.
TAIL = 3000

#: Inherited variables that could point a child at another database, data dir or server, or start coverage in it.
STRIPPED_PREFIXES = ("LIBREFOLIO_", "COVERAGE_")
STRIPPED_NAMES = frozenset({"DATABASE_URL", "ALEMBIC_DATABASE_URL", "PORT", "TEST_PORT"})

#: The success line of ``python -m backend.alembic.check_constraints_hook``.
CHECK_OK = "All CHECK constraints are present"
#: How a refusal may say that a file is missing. It counts only on a line that also names the file: dev.py echoes the path it is given.
MISSING_WORDS = re.compile(r"not found|not be found|not exist|n't exist|no such|missing|cannot find|can't find", re.IGNORECASE)
CRASH = "Traceback (most recent call last)"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

#: Run through the launcher dev.py starts Alembic with: the configured databases, as env.py and dev.py compute them.
ISOLATION_PROBE = "from backend.app.config import get_settings; from scripts.cli_base import get_database_path, get_test_database_path; print('url=' + get_settings().DATABASE_URL); print('configured=' + get_database_path()); print('test=' + get_test_database_path())"


# ---------------------------------------------------------------------------
# What the module works with
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chain:
    """The migration chain as the script directory declares it."""

    head: str
    down: str  # head-1: the head's down_revision
    revisions: frozenset[str]


@dataclass(frozen=True)
class Templates:
    """Databases Alembic built once for the module, at head and at head-1; every test copies them."""

    head: Path
    down: Path


@dataclass(frozen=True)
class Sandbox:
    """One test's world: its tmp dir, the configured and test data dirs inside it, and the environment pointing there."""

    root: Path
    configured: Path  # LIBREFOLIO_DATA_DIR
    test_lane: Path  # LIBREFOLIO_TEST_DATA_DIR
    env: dict[str, str]

    @property
    def sentinel(self) -> Path:
        """The configured database: what the defect migrates instead of the path it is given."""
        return self.configured / "sqlite" / "app.db"


@dataclass(frozen=True)
class Run:
    """A finished child process: its command line, where it ran, its exit status and what it printed."""

    argv: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """stdout, then stderr, without colour codes."""
        return ANSI.sub("", f"{self.stdout}\n{self.stderr}")

    def __str__(self) -> str:
        return f"`{shlex.join(self.argv)}` (cwd {self.cwd}) exited {self.returncode}\n--- stdout (tail)\n{self.stdout[-TAIL:]}\n--- stderr (tail)\n{self.stderr[-TAIL:]}"


@dataclass(frozen=True)
class DbState:
    """A database file as it stands: the digest of its bytes and its Alembic revision, both None when it is absent."""

    path: Path
    digest: str | None
    revision: str | None


# ---------------------------------------------------------------------------
# The sandbox and its child processes
# ---------------------------------------------------------------------------


def free_ports(count: int) -> list[int]:
    """Ports nothing listens on: bound together on 127.0.0.1, so they differ from one another, then released."""
    sockets = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in range(count)]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def isolated_env(configured: Path, test_lane: Path) -> dict[str, str]:
    """The runner's environment minus whatever could redirect a child, plus the sandbox's data dirs and two free ports."""
    env = {name: value for name, value in os.environ.items() if not name.startswith(STRIPPED_PREFIXES) and name not in STRIPPED_NAMES}
    port, test_port = free_ports(2)
    env.update(
        LIBREFOLIO_DATA_DIR=str(configured),
        LIBREFOLIO_TEST_DATA_DIR=str(test_lane),
        LIBREFOLIO_TEST_MODE="0",
        PIPENV_DONT_LOAD_ENV="1",
        PORT=str(port),
        TEST_PORT=str(test_port),
        # Readability only: the output in the order it was printed, emoji encodable whatever the locale.
        PYTHONUNBUFFERED="1",
        PYTHONUTF8="1",
    )
    return env


def make_sandbox(directory: Path) -> Sandbox:
    """A sandbox in ``directory``. Its test data dir passes the checks ``backend/app/config.py`` applies, before any child starts."""
    root = directory.resolve()
    configured, test_lane = root / "configured", root / "test-lane"
    validate_test_data_dir(test_lane, production_data_dir=configured)
    return Sandbox(root=root, configured=configured, test_lane=test_lane, env=isolated_env(configured, test_lane))


def text(data: bytes | str | None) -> str:
    """What a killed child had printed, whichever type ``TimeoutExpired`` carries."""
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data or ""


def run(argv: list[str], env: dict[str, str], cwd: Path = PROJECT_ROOT) -> Run:
    """``argv`` in a child process: no stdin, output captured, killed after ``CLI_TIMEOUT``."""
    try:
        done = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CLI_TIMEOUT, check=False)
    except FileNotFoundError as exc:
        pytest.fail(f"cannot start `{shlex.join(argv)}`: {exc}")
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"`{shlex.join(argv)}` did not end within {CLI_TIMEOUT}s and was killed\n--- stdout so far\n{text(exc.stdout)[-TAIL:]}\n--- stderr so far\n{text(exc.stderr)[-TAIL:]}")
    return Run(argv=tuple(argv), cwd=cwd, returncode=done.returncode, stdout=done.stdout, stderr=done.stderr)


def dev_db(sandbox: Sandbox, *argv: str, cwd: Path = PROJECT_ROOT) -> Run:
    """``python dev.py db <argv>`` with the interpreter running this test, in the sandbox's environment."""
    return run([sys.executable, str(DEV_PY), "db", *argv], sandbox.env, cwd)


def alembic(db: Path, env: dict[str, str], *command: str) -> None:
    """``alembic <command>`` on ``db``, always with ``-x sqlalchemy.url=``: without it env.py takes the configured database."""
    done = run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url=sqlite:///{db}", *command], env)
    assert done.returncode == 0, f"setup: alembic {' '.join(command)} failed on {db}\n{done}"


def prove_isolation(sandbox: Sandbox) -> None:
    """Before any ``dev.py db`` command: pipenv picks this test's environment, and through it the configured databases are the sandbox's.

    ``dev.py`` starts Alembic with ``pipenv run``. Another environment, or a ``.env`` loaded on the way, and the
    defect under test would migrate a real database. ``pipenv --venv`` only reads, so a worktree that lacks its
    ``PIPENV_CUSTOM_VENV_NAME`` stops here instead of getting an empty virtualenv from ``pipenv run``.
    """
    launcher = pipenv_prefix()
    if launcher:
        venv = run(["pipenv", "--venv"], sandbox.env)
        lines = venv.stdout.strip().splitlines()
        found = Path(lines[-1].strip()).resolve() if venv.returncode == 0 and lines else None
        assert found == Path(sys.prefix).resolve(), f"safety: pipenv would run Alembic in {found or 'no environment'}, not in {sys.prefix} where this test runs (a worktree needs its PIPENV_CUSTOM_VENV_NAME)\n{venv}"
    expected = {"url": f"sqlite:///{sandbox.sentinel}", "configured": str(sandbox.sentinel), "test": str(sandbox.test_lane / "sqlite" / "app.db")}
    probe = run([*launcher, "python", "-c", ISOLATION_PROBE], sandbox.env)
    seen = {key: value for key, _, value in (line.partition("=") for line in probe.stdout.splitlines()) if key in expected}
    assert probe.returncode == 0 and seen == expected, f"safety: through `{shlex.join(launcher) or 'python'}` the configured databases are {seen}, expected the sandbox's {expected}; no dev.py db command may run\n{probe}"


# ---------------------------------------------------------------------------
# Databases, files and output
# ---------------------------------------------------------------------------


def revision_of(db: Path) -> str | None:
    """``alembic_version.version_num``, through a read-only connection: ``sqlite3.connect`` would create a missing file."""
    try:
        with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)) as conn:
            rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    except sqlite3.Error as exc:
        return f"<unreadable: {exc}>"
    return ", ".join(sorted(row[0] for row in rows)) or None


def state(db: Path) -> DbState:
    """``db`` as it stands now."""
    if not db.is_file():
        return DbState(path=db, digest=None, revision=None)
    return DbState(path=db, digest=hashlib.sha256(db.read_bytes()).hexdigest(), revision=revision_of(db))


def place(template: Path, db: Path) -> DbState:
    """A copy of ``template`` at ``db``, and its state to compare with afterwards."""
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, db)
    return state(db)


def tree(root: Path) -> set[str]:
    """Every file and directory below ``root``, relative to it."""
    return {path.relative_to(root).as_posix() for path in root.rglob("*")}


def revision_files() -> set[str]:
    """The revision scripts in ``backend/alembic/versions/``; ``__pycache__``, which any Alembic run may refresh, aside."""
    return {path.name for path in VERSIONS_DIR.glob("*.py")}


def revisions_named(done: Run, chain: Chain) -> set[str]:
    """The chain's revisions that the output names, as whole words."""
    return {revision for revision in chain.revisions if re.search(rf"(?<![\w-]){re.escape(revision)}(?![\w-])", done.output)}


def names_as_missing(done: Run, path: Path) -> bool:
    """Whether one line of the output both names ``path`` and says that it is missing."""
    # The words are searched with the path cut out of the line: the sandbox path carries the test's name (pytest builds
    # tmp_path from it, e.g. test_missing_file_is_refused_c1), so dev.py's mere echo of the path would say "missing".
    return any(str(path) in line and MISSING_WORDS.search(line.replace(str(path), "")) for line in done.output.splitlines())


# ---------------------------------------------------------------------------
# What a case found wrong, in words
# ---------------------------------------------------------------------------


def exit_problems(done: Run, *, success: bool) -> list[str]:
    if success:
        return [] if done.returncode == 0 else [f"exit {done.returncode}, expected 0"]
    return [] if done.returncode != 0 else ["exit 0, expected a refusal (exit ≠ 0)"]


def revision_problems(db: Path, expected: str, what: str) -> list[str]:
    if not db.is_file():
        return [f"{what} {db} does not exist, expected it at {expected}"]
    found = revision_of(db)
    return [] if found == expected else [f"{what} {db} is at {found}, expected {expected}"]


def reported_problems(done: Run, chain: Chain, expected: str) -> list[str]:
    named = revisions_named(done, chain)
    return [] if named == {expected} else [f"the output names {sorted(named) or 'no revision'}, expected {expected} alone"]


def change_problems(before: DbState, what: str) -> list[str]:
    after = state(before.path)
    if after.digest == before.digest:
        return []
    if before.digest is None:
        return [f"{what} {before.path} was created, at {after.revision}"]
    if after.digest is None:
        return [f"{what} {before.path} was deleted"]
    return [f"{what} {before.path} was modified: {before.revision} → {after.revision}"]


def refusal_problems(done: Run, root: Path, before: set[str], missing: Path | None = None) -> list[str]:
    """What keeps ``done`` from being a clean refusal: exit ≠ 0, no traceback, ``missing`` named as missing, nothing created or removed below ``root``."""
    problems = exit_problems(done, success=False)
    if CRASH in done.output:
        problems.append("it crashed with a traceback instead of refusing")
    if missing is not None and not names_as_missing(done, missing):
        problems.append(f"no line of the output names {missing} and says that it is missing")
    after = tree(root)
    if after != before:
        problems.append(f"below {root}: created {sorted(after - before)}, removed {sorted(before - after)}")
    return problems


def verdict(done: Run, problems: list[str]) -> None:
    """One assertion for everything a case found wrong, then what the command printed."""
    listed = "\n".join(f"  - {problem}" for problem in problems)
    assert not problems, f"{len(problems)} problem(s):\n{listed}\n{done}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def chain() -> Chain:
    """Head and head-1 from the script directory of ``backend/alembic.ini``."""
    saved = list(sys.path)
    try:
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
        scripts = ScriptDirectory.from_config(config)
        heads = scripts.get_heads()
        down = scripts.get_revision(heads[0]).down_revision if len(heads) == 1 else None
        revisions = frozenset(script.revision for script in scripts.walk_revisions())
    finally:
        sys.path[:] = saved  # from_config prepends alembic.ini's prepend_sys_path
    assert len(heads) == 1 and isinstance(down, str), f"setup: expected one head with one parent, found heads {heads}, down_revision {down!r}"
    return Chain(head=heads[0], down=down, revisions=revisions)


@pytest.fixture(scope="module")
def templates(tmp_path_factory: pytest.TempPathFactory, chain: Chain) -> Templates:
    """Proves the isolation, then has Alembic build the module's databases: head, and head-1 by ``downgrade -1``."""
    sandbox = make_sandbox(tmp_path_factory.mktemp("dev_cli_db_path"))
    prove_isolation(sandbox)
    head, down = sandbox.root / "head.db", sandbox.root / "down.db"
    alembic(head, sandbox.env, "upgrade", "head")
    shutil.copyfile(head, down)
    alembic(down, sandbox.env, "downgrade", "-1")
    built = (revision_of(head), revision_of(down))
    assert built == (chain.head, chain.down), f"setup: the templates are at {built}, expected {(chain.head, chain.down)}"
    return Templates(head=head, down=down)


@pytest.fixture
def sandbox(tmp_path: Path, templates: Templates) -> Sandbox:
    """This test's sandbox. Depending on ``templates`` makes the isolation proof run before any test does."""
    return make_sandbox(tmp_path)


# ---------------------------------------------------------------------------
# DBP-a..DBP-e: the command acts on the path it is given
# ---------------------------------------------------------------------------


class TestTheTargetIsThePath:
    """With a path, the command acts on that file, never on the configured database."""

    def test_upgrade_migrates_the_target(self, sandbox: Sandbox, templates: Templates, chain: Chain):
        """DBP-a: ``db upgrade <absolute path>`` takes the target from head-1 to head; the configured database, at head-1 too, keeps its bytes.

        Red today: Alembic upgrades the configured database to head, and the target stays at head-1.
        """
        print_section("DBP-a: db upgrade <absolute path>")
        target = place(templates.down, sandbox.root / "target" / "app.db")
        sentinel = place(templates.down, sandbox.sentinel)

        done = dev_db(sandbox, "upgrade", str(target.path))

        problems = exit_problems(done, success=True)
        problems += revision_problems(target.path, chain.head, "the target")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"the target went from {chain.down} to {chain.head}; the configured database kept its bytes")

    def test_current_reports_the_target(self, sandbox: Sandbox, templates: Templates, chain: Chain):
        """DBP-b: ``db current <absolute path>``, the target at head-1 and the configured database at head, names head-1 and not head.

        Red today: it reports the configured database's revision, head.
        """
        print_section("DBP-b: db current <absolute path>")
        target = place(templates.down, sandbox.root / "target" / "app.db")
        sentinel = place(templates.head, sandbox.sentinel)

        done = dev_db(sandbox, "current", str(target.path))

        problems = exit_problems(done, success=True)
        problems += reported_problems(done, chain, chain.down)
        problems += change_problems(target, "the target")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"reported {chain.down}, the target's revision")

    def test_downgrade_rolls_back_the_target(self, sandbox: Sandbox, templates: Templates, chain: Chain):
        """DBP-c: ``db downgrade <absolute path>`` takes the target from head to head-1; the configured database, at head, keeps its bytes.

        Red today: Alembic rolls the configured database back to head-1, and the target stays at head.
        """
        print_section("DBP-c: db downgrade <absolute path>")
        target = place(templates.head, sandbox.root / "target" / "app.db")
        sentinel = place(templates.head, sandbox.sentinel)

        done = dev_db(sandbox, "downgrade", str(target.path))

        problems = exit_problems(done, success=True)
        problems += revision_problems(target.path, chain.down, "the target")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"the target went from {chain.head} to {chain.down}; the configured database kept its bytes")

    def test_check_verifies_the_target(self, sandbox: Sandbox, templates: Templates):
        """DBP-d: ``db check <absolute path>`` on a target at head exits 0 with the success line of the CHECK constraints hook, writes nothing to the target, and creates no configured database.

        There is no configured database in this case: it must not appear. Red today: ``db check`` runs
        ``backend/test_scripts/verify_db_check_constraints.py``, which does not exist (exit 2, no success line).
        """
        print_section("DBP-d: db check <absolute path>")
        target = place(templates.head, sandbox.root / "target" / "app.db")
        sentinel = state(sandbox.sentinel)

        done = dev_db(sandbox, "check", str(target.path))

        problems = exit_problems(done, success=True)
        if CHECK_OK not in done.output:
            problems.append(f"the output lacks the hook's success line {CHECK_OK!r}")
        problems += change_problems(target, "the target")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success("all CHECK constraints present in the target; no configured database created")

    def test_relative_path_starts_at_the_project_root(self, sandbox: Sandbox, templates: Templates, chain: Chain):
        """DBP-e: a relative path starts at the project root, not at the working directory: ``db current <relative path>``, launched from a temporary directory, names the target's revision (head-1), not the configured database's (head).

        The path leads from the project root to the target through ``..``. The working directory, inside
        ``tmp_path``, is at least as deep as the path climbs, so from there the same path stays inside the sandbox
        and misses the target, which is checked first; from ``tmp_path`` itself, shallower than the project root
        on Linux, the ``..`` would stop at ``/`` and reach the target either way. Red today: it reports the
        configured database's revision, head.
        """
        print_section("DBP-e: db current <path relative to the project root>, from another directory")
        target = place(templates.down, sandbox.root / "target" / "app.db")
        sentinel = place(templates.head, sandbox.sentinel)
        relative = os.path.relpath(target.path, PROJECT_ROOT)
        cwd = sandbox.root.joinpath("cwd", *["deeper"] * Path(relative).parts.count(".."))
        cwd.mkdir(parents=True)
        assert not os.path.isabs(relative) and (cwd / relative).resolve() != target.path, f"setup: {relative} must be relative and, from {cwd}, lead somewhere else than {target.path}"
        print_info(f"cwd {cwd}, path {relative}")

        done = dev_db(sandbox, "current", relative, cwd=cwd)

        problems = exit_problems(done, success=True)
        problems += reported_problems(done, chain, chain.down)
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"reported {chain.down}, the target's revision")


# ---------------------------------------------------------------------------
# DBP-f, DBP-f2, DBP-h: a path that cannot be used is refused, cleanly
# ---------------------------------------------------------------------------


class TestRefusals:
    """A path that cannot be used is refused before anything is touched: exit ≠ 0, no traceback, nothing created."""

    @pytest.mark.parametrize("command", ["current", "downgrade", "check"])
    def test_missing_file_is_refused(self, sandbox: Sandbox, templates: Templates, command: str):
        """DBP-f: ``db current|downgrade|check <missing file>`` exits ≠ 0 without a traceback, a line of its output names the absolute path and says it is missing, the file and its folder are not created, and the configured database keeps its bytes.

        Saying *missing* on the line that names the path is the point: ``dev.py`` already echoes whatever path it
        is given. Red today: ``current`` and ``downgrade`` exit 0 on the configured database (``downgrade`` rolls
        it back); ``check`` exits 2 because its script does not exist, never naming the file as missing.
        """
        print_section(f"DBP-f: db {command} <missing file>")
        missing = sandbox.root / "nope" / "app.db"
        sentinel = place(templates.head, sandbox.sentinel)
        before = tree(sandbox.root)

        done = dev_db(sandbox, command, str(missing))

        problems = refusal_problems(done, sandbox.root, before, missing)
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"db {command} refused {missing}, nothing created, the configured database untouched")

    def test_migrate_refuses_a_missing_file(self, sandbox: Sandbox, templates: Templates, chain: Chain):
        """DBP-f2: ``db migrate <message> <missing file>`` is refused as in DBP-f, and ``backend/alembic/versions/`` keeps its file list.

        Only the refusal may ever run: a successful ``migrate`` writes a revision into the repository. So the safety
        check comes first: no database within the command's reach is at head (the configured one is at head-1, the
        test lane has none, the target does not exist), and Alembic's autogenerate refuses such a database too
        ("Target database is not up to date"). A revision carrying this run's marker is removed should it appear
        anyway, and the test fails. Red today: the refusal is Alembic's, about the configured database; no line
        names the missing file.
        """
        print_section("DBP-f2: db migrate <message> <missing file>")
        missing = sandbox.root / "nope" / "app.db"
        sentinel = place(templates.down, sandbox.sentinel)
        lane_db = sandbox.test_lane / "sqlite" / "app.db"
        assert sentinel.revision == chain.down and not lane_db.exists() and not missing.parent.exists(), f"safety: a database at head within reach (configured at {sentinel.revision}, lane database present: {lane_db.exists()}) or an existing target; db migrate must not run"
        marker = f"dbpath_refusal_{uuid.uuid4().hex[:8]}"  # Alembic's slug of the message, in any revision file it would write
        message = marker.replace("_", " ")
        print_info(f"migration message {message!r}")
        before, versions = tree(sandbox.root), revision_files()
        try:
            done = dev_db(sandbox, "migrate", message, str(missing))
        finally:
            versions_after = revision_files()
            for name in versions_after - versions:
                if marker in name:
                    (VERSIONS_DIR / name).unlink()

        problems = refusal_problems(done, sandbox.root, before, missing)
        if versions_after != versions:
            problems.append(f"backend/alembic/versions/ changed: gained {sorted(versions_after - versions)} (those carrying {marker} were removed), lost {sorted(versions - versions_after)}")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"db migrate refused {missing}; backend/alembic/versions/ unchanged")

    @pytest.mark.parametrize("folder", [pytest.param("a%20b", id="percent"), pytest.param("a?b", id="question-mark"), pytest.param("a#b", id="hash")])
    def test_url_metacharacters_are_refused(self, sandbox: Sandbox, templates: Templates, folder: str):
        """DBP-h: ``db upgrade`` refuses a path holding ``%``, ``?`` or ``#``: exit ≠ 0 without a traceback, nothing created, the configured database keeps its bytes.

        In ``sqlite:///…`` a ``%`` decodes and ``?`` starts the query; ``#`` goes with them, as for data dirs
        (``resolve_data_dir``). A ``%`` reaching Alembic also breaks the ConfigParser interpolation behind
        ``set_main_option``: a crash that exits 1 as well, hence "without a traceback". The folder exists, so the
        character is the only possible reason. Red today: exit 0, the configured database (head-1) upgraded.
        """
        print_section(f"DBP-h: db upgrade <path with {folder}>")
        target = sandbox.root / folder / "app.db"
        target.parent.mkdir()
        sentinel = place(templates.down, sandbox.sentinel)
        before = tree(sandbox.root)

        done = dev_db(sandbox, "upgrade", str(target))

        problems = refusal_problems(done, sandbox.root, before)
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"db upgrade refused {target}, nothing created")


# ---------------------------------------------------------------------------
# DBP-g: upgrade creates the database it is given
# ---------------------------------------------------------------------------


class TestUpgradeCreates:
    """``upgrade`` is the one command that creates a missing database: the test runner relies on it."""

    def test_upgrade_creates_a_missing_file(self, sandbox: Sandbox, chain: Chain):
        """DBP-g: ``db upgrade <missing file>``, its folder present, creates the file at head and no configured database.

        The test runner rebuilds its database this way: it deletes the file, then runs
        ``python dev.py db upgrade <path>`` (``scripts/test_runner/_backend_db.py``). Red today: Alembic opens the
        configured database instead, whose folder does not exist: exit 1, nothing created.
        """
        print_section("DBP-g: db upgrade <missing file>")
        target = sandbox.root / "fresh" / "app.db"
        target.parent.mkdir()
        sentinel = state(sandbox.sentinel)

        done = dev_db(sandbox, "upgrade", str(target))

        problems = exit_problems(done, success=True)
        problems += revision_problems(target, chain.head, "the target")
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"created {target} at {chain.head}; no configured database")


# ---------------------------------------------------------------------------
# DBP-i, guard: without a path, the configured database
# ---------------------------------------------------------------------------


class TestWithoutPath:
    """Without a path nothing changes: the commands keep working on the configured database."""

    @pytest.mark.parametrize("at", [pytest.param("head", id="head"), pytest.param("down", id="head-1")])
    def test_current_reports_the_configured_database(self, sandbox: Sandbox, templates: Templates, chain: Chain, at: str):
        """DBP-i, guard: without a path, ``db current`` reports the configured database's revision.

        Green today and after the fix. At head, as the contract has it, and at head-1: a command reading some
        other database could pass one of the two, never both. Only ``current`` runs without a path here: an
        ``upgrade`` or ``downgrade`` without one acts on the configured database by design.
        """
        print_section(f"DBP-i: db current without a path, the configured database at {at}")
        sentinel = place(getattr(templates, at), sandbox.sentinel)

        done = dev_db(sandbox, "current")

        problems = exit_problems(done, success=True)
        problems += reported_problems(done, chain, sentinel.revision)
        problems += change_problems(sentinel, "the configured database")
        verdict(done, problems)
        print_success(f"reported {sentinel.revision}, the configured database's revision")

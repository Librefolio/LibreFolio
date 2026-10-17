"""
Restoring a backup, end to end: the founder's acceptance (workstream B: lot B3, contract §9; lot B-13, contract §6, the
ledger's control totals). Selector: ``e2e backup-roundtrip``.

1. A backup of a populated instance, restored on an empty instance, gives the same totals — among them the ledger's
   control totals, which its archive recorded when it was made.
2. A LibreFolio backup at an older revision (``OLDER``) is restored through the check and the confirmation: committed,
   at the head, its rows as the check's report said, its ledger's totals the same through the upgrade.
3. A backup of a newer LibreFolio is refused (B2's ``revision_unknown``) through the same flow, the target untouched.

The flow is the user's. ``python scripts/backup_cli.py --test-db restore ARCHIVE --yes`` checks the archive on a copy
and confirms it; then «a start», in a fresh process, in test mode, on the target: the slice of
``app_lifespan.STARTUP_STEPS`` from ``pending-restore`` to ``restore-commit``, run by ``lifecycle.run_startup_steps`` as
the lifespan runs it. No server is started: one server per lane, and this test needs none.

The source is a populated instance under ``tmp_path``, made for the module: ``python -m
backend.test_scripts.test_db.populate_mock_data --force`` in a child process (the project's mock data, as ``./dev.py test
db populate`` writes it, on a data directory of the test), then files of this module in ``custom-uploads/`` and
``broker_reports/`` (after the populate: its ``--force`` empties ``broker_reports/``), then a first start (the steps from
``data-directories`` to ``global-settings``: the instance as a server leaves it). It is archived with
``jobs.run_backup(origin="cli", data_dir=<source>)``. The target is an empty instance: a database made at the head by
``alembic upgrade`` in a process of its own (``test_backup_staging.py``'s module fixture, imported) and the same first
start; each test restores into its own copy of it.

The archive at ``OLDER`` is made by this LibreFolio's backup (``archive.build_archive``, as ``test_backup_staging.py``
makes its own) from a database made at ``OLDER`` by ``alembic`` (that module's fixture, imported) with that module's
accounts and files, and a small ledger written in the schema of ``OLDER`` (``LEDGER_AT_OLDER``: a broker, an asset,
cash in two currencies, a buy, a sell, a dividend). Not that module's ``older_archive``: it has no ledger, and the totals
of an empty ledger are the same whatever an upgrade does to the rows.

The totals are computed in a fresh process, in test mode, on a data directory: the rows of every table; the SHA-256 of
every file of the archived folders; the ledger's control totals, by J's ``compute_control_totals`` on the app's own
session (``get_session_generator``, on the database of that data directory) — the cash of every broker in each currency
and the quantity of every position, read from the rows alone, as J's canonical JSON (``ControlTotals.to_json``); and,
for every account that sees a broker, the report of the official engine (``PortfolioService(session).get_report``, as
``POST /portfolio/report`` computes it) over one past date range, the same for both instances, without its
``generated_at`` (the day the report is made, not a figure). The source's and the target's are computed back to back,
once the target is restored: the backup changes nothing they read, and a midnight between the two shrinks to the seconds
between two runs. The source's totals are checked against its archive's manifest — rows, files, and the control totals
the backup read on its snapshot (``database.control_totals``): the archive holds exactly what was measured. Restored,
the target's totals are the source's, and the check had reported the ledger's totals ``same``. At ``OLDER``, the
manifest records the totals of ``LEDGER_AT_OLDER`` (worked by hand: the sum of the amounts per broker and currency, of
the quantities per broker and asset), the check reports them ``same`` after its upgrade, and the restored database at
the head has them. Both runs hash with the same ``PYTHONHASHSEED``, so a list the engine builds from a set comes out in
the same order for the same data.

Pure: every data directory, database and archive under ``tmp_path``; the lane's data directory is never read or written,
its server never called, its backup lock never taken. Every child runs in test mode on a data directory of the test, with
a production data directory of the test that must stay absent, without the lane's variables (``LIBREFOLIO_*``), coverage
or the instance's secrets, the interpreter's own folder first on its ``PATH`` (the populate's database bootstrap runs
``alembic`` by name); ``LF_APP_VERSION`` is set, so no git process runs. No network: the mock data assign providers but
fetch nothing. Every wait is a child process with a timeout. POSIX-only.

RED until B-13 lands: the manifest has no ``database.control_totals`` and the check's report no ``control_totals``. Both
are read with ``getattr`` and asserted last ("[new] …"): each test runs everything B3 already does, and the ledger's
totals the children measure, before it fails on the first of them. The refusal of a newer backup is unchanged.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from backend.app.config import INSTANCE_TRUST_SECRETS
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
from backend.app.services.financial_math.ledger_totals import CONTROL_TOTALS_VERSION
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.archive import BuiltArchive
from backend.app.services.platform.instance_backup.manifest import BackupManifest
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, MANIFEST_ENTRY, STAGE_DATA_FOLDER, STAGE_LOCK_FILE, restore_dir, stage_dir, stages_dir
from backend.app.services.platform.instance_backup.staging import read_report
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixture of test_backup_staging.py (lot B2a), re-exported: two databases made by alembic in a process of
# their own, at the head and at OLDER.
databases = cases.databases
# Autouse: this process's production data directory is a folder of the test that must stay absent, LF_APP_VERSION set.
configured_data_dir = cases.configured_data_dir

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the restore's folders, links and locks are POSIX only")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "backup_cli.py"
#: The project's mock data, as ``./dev.py test db populate`` writes them (``--force``: the database made by the script).
POPULATE = "backend.test_scripts.test_db.populate_mock_data"
APP_VERSION = "v0.0.0-b3-roundtrip-test"
#: The same hash seed in every child: a list built from a set of strings comes out in one order for one content.
HASH_SEED = "0"
#: Seconds a child may take: it imports the application, populates, checks or upgrades a copy, computes reports, on a
#: loaded machine. A hang still ends.
CHILD_TIMEOUT_S = 900
#: Characters of a child's output quoted by an assertion message.
TAIL = 3000
#: The startup steps that make an instance what a server leaves: those of today's start that touch the data.
FIRST_START = ("data-directories", "global-settings")
#: «A start» with a restore waiting (§9).
RESTORE_START = ("pending-restore", "restore-commit")
#: The past date range of every report: the same for both instances, ending yesterday, so no report reaches today.
REPORT_END = date.today() - timedelta(days=1)
REPORT_START = REPORT_END - timedelta(days=5 * 365)
#: Files of this module in the source, beside what the populate and the first start write: a restore must bring them
#: back byte for byte.
OWN_FILES = {
    "custom-uploads/b3-roundtrip/receipt-2026-09.pdf": b"%PDF-1.7 a receipt the round trip must bring back\n" + bytes(range(256)) * 8,
    "custom-uploads/b3-roundtrip/notes.txt": "accents survive a round trip: é è ü ß 漢字\n".encode(),
    "broker_reports/uploaded/b3-roundtrip-2026-09.csv": b"date,amount,currency\n2026-09-30,1250.00,EUR\n",
    "broker_reports/parsed/b3-roundtrip-2026-08.csv": b"date,amount,currency\n2026-08-31,980.40,EUR\n",
}

#: The transactions of the ledger at ``OLDER``, all at broker 1: (asset id, type, date, quantity, amount, currency).
#: Binary fractions only: SQLite stores these columns as reals, and they read back exactly.
LEDGER_TRANSACTIONS = (
    (None, "DEPOSIT", "2026-01-02", "0", "10000", "EUR"),
    (None, "DEPOSIT", "2026-01-03", "0", "2500.5", "USD"),
    (1, "BUY", "2026-01-05", "12", "-1500.75", "EUR"),
    (1, "SELL", "2026-03-10", "-2", "260.5", "EUR"),
    (1, "DIVIDEND", "2026-06-30", "0", "12.25", "EUR"),
)
#: That ledger, written into a database at ``OLDER`` in that revision's schema: ``brokers``, ``assets`` and
#: ``transactions`` as ``001_initial`` made them (``004`` added ``assets.is_benchmark``, with a default); no migration
#: after ``OLDER`` touches them. A fixed revision: these statements stay right.
LEDGER_AT_OLDER = (
    f"INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'B-13 ledger broker', '{cases.CREATED}', '{cases.CREATED}')",
    f"INSERT INTO assets (id, display_name, currency, asset_type, active, created_at, updated_at) VALUES (1, 'B-13 ledger asset', 'EUR', 'STOCK', 1, '{cases.CREATED}', '{cases.CREATED}')",
    *(
        f"INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES (1, {'NULL' if asset_id is None else asset_id}, '{kind}', '{day}', {quantity}, {amount}, '{currency}', '{cases.CREATED}', '{cases.CREATED}')"
        for asset_id, kind, day, quantity, amount, currency in LEDGER_TRANSACTIONS
    ),
)
#: The control totals of that ledger, worked by hand by J's rule: the sum of the amounts per broker and currency
#: (10000 - 1500.75 + 260.5 + 12.25 = 8772 EUR; 2500.5 USD), of the quantities per broker and asset (12 - 2 = 10), as
#: J's canonical JSON.
LEDGER_AT_OLDER_TOTALS = {
    "version": CONTROL_TOTALS_VERSION,
    "cash": [{"broker_id": 1, "currency": "EUR", "balance": "8772"}, {"broker_id": 1, "currency": "USD", "balance": "2500.5"}],
    "quantities": [{"broker_id": 1, "asset_id": 1, "quantity": "10"}],
}
#: The check's warnings about the ledger's totals (B-13 §3): neither for a ledger the restore keeps.
TOTALS_WARNINGS = {"control_totals_changed", "control_totals_unreadable"}

#: «A start»: the steps of ``app_lifespan.STARTUP_STEPS`` from ``argv[1]`` to ``argv[2]``, both included, run by
#: ``lifecycle.run_startup_steps``.
START_PROGRAM = """
import asyncio
import sys

from backend.app.services.platform import app_lifespan, lifecycle

first, last = sys.argv[1], sys.argv[2]
names = [step.name for step in app_lifespan.STARTUP_STEPS]
missing = [name for name in (first, last) if name not in names]
if missing:
    sys.exit(f"no startup step named {missing}: {names}")
asyncio.run(lifecycle.run_startup_steps(app_lifespan.STARTUP_STEPS[names.index(first) : names.index(last) + 1]))
"""

#: The totals of the configured data directory, written as JSON to ``argv[3]``: the reports over ``argv[1]``–``argv[2]``;
#: the ledger's control totals on the app's own session; the database file the app's engine opened.
TOTALS_PROGRAM = """
import asyncio
import hashlib
import json
import sqlite3
import sys
from contextlib import aclosing, closing
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_data_dir
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services.financial_math.ledger_totals import compute_control_totals
from backend.app.services.portfolio_service import PortfolioService

start, end, output = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2]), sys.argv[3]
data = get_data_dir()
with closing(sqlite3.connect(f"{(data / 'sqlite' / 'app.db').as_uri()}?mode=ro", uri=True)) as conn:
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    rows = {name: conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in tables}
    owners = conn.execute("SELECT id, username FROM users WHERE id IN (SELECT user_id FROM broker_user_access) ORDER BY id").fetchall()
files = {}
for folder in ("custom-uploads", "broker_reports", "scenario_catalog"):
    for path in sorted((data / folder).rglob("*")):
        if path.is_file() and not path.is_symlink():
            files[path.relative_to(data).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()


async def measured():
    engine = get_async_engine()
    try:
        # The ledger's control totals as the app reads them: J's read point, on a session of the app's own factory.
        async with aclosing(get_session_generator()) as sessions:
            ledger = (await compute_control_totals(await anext(sessions))).to_json()
        reports = {}
        for user_id, username in owners:
            async with AsyncSession(engine) as session:
                report = await PortfolioService(session).get_report(user_id=user_id, query=PortfolioReportQuery(date_range=OpenDateRangeModel(start=start, end=end)))
            dumped = report.model_dump(mode="json")
            dumped["metadata"].pop("generated_at", None)
            reports[username] = dumped
        return {"database": str(Path(engine.url.database).resolve()), "control_totals": ledger, "reports": reports}
    finally:
        await engine.dispose()


with open(output, "w", encoding="utf-8") as handle:
    json.dump({"data_dir": str(data), "rows": rows, "files": files, **asyncio.run(measured())}, handle, sort_keys=True)
"""


# =============================================================================
# Children
# =============================================================================


def production_of(data_dir: Path) -> Path:
    """The production data directory of a child working on ``data_dir``: a folder of the test that must stay absent."""
    return data_dir.parent / f"{data_dir.name}-configured-production-data-dir"


def child_env(data_dir: Path) -> dict[str, str]:
    """This process's environment for a child in test mode on ``data_dir``: without the lane's variables, coverage or
    the instance's secrets; the project importable; this interpreter's folder first on ``PATH``, so that a command run
    by name (``alembic``) is this environment's; ``LF_APP_VERSION`` and the hash seed set."""
    env = {name: value for name, value in os.environ.items() if not name.startswith(("LIBREFOLIO_", "COVERAGE_")) and name not in INSTANCE_TRUST_SECRETS}
    env.update(
        LIBREFOLIO_TEST_MODE="1",
        LIBREFOLIO_TEST_DATA_DIR=str(data_dir),
        LIBREFOLIO_DATA_DIR=str(production_of(data_dir)),
        LF_APP_VERSION=APP_VERSION,
        PATH=os.pathsep.join([str(Path(sys.executable).parent), *filter(None, [os.environ.get("PATH")])]),
        PYTHONPATH=os.pathsep.join([str(PROJECT_ROOT), *filter(None, [os.environ.get("PYTHONPATH")])]),
        PYTHONHASHSEED=HASH_SEED,
        PYTHONUNBUFFERED="1",
        PYTHONUTF8="1",
    )
    return env


def run(command: list[str], data_dir: Path, what: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """``command`` in a child in test mode on ``data_dir``, working in ``cwd`` (the data directory's parent folder by
    default); its end, within the timeout."""
    try:
        return subprocess.run(command, cwd=cwd or data_dir.parent, env=child_env(data_dir), stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CHILD_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"{what} did not end within {CHILD_TIMEOUT_S}s: {exc.stdout!r} {exc.stderr!r}")


def shown(done: subprocess.CompletedProcess) -> str:
    return f"exit {done.returncode}\n--- stdout\n{done.stdout[-TAIL:]}\n--- stderr\n{done.stderr[-TAIL:]}"


def start(data_dir: Path, steps: tuple[str, str]) -> subprocess.CompletedProcess:
    """«A start» of the instance at ``data_dir``: the startup steps from ``steps[0]`` to ``steps[1]``, a fresh process."""
    return run([sys.executable, "-c", START_PROGRAM, *steps], data_dir, f"a start ({steps[0]} … {steps[1]})")


def populate(data_dir: Path) -> float:
    """The project's mock data written into a new instance at ``data_dir``, as ``./dev.py test db populate --force``
    writes them, in a child working in the project root; the seconds it took."""
    started = time.monotonic()
    done = run([sys.executable, "-m", POPULATE, "--force"], data_dir, "the populate", cwd=PROJECT_ROOT)
    assert done.returncode == 0, f"precondition: the mock data are written into the source: {shown(done)}"
    return time.monotonic() - started


def restore_yes(archive: Path, data_dir: Path) -> subprocess.CompletedProcess:
    """``backup --test-db restore ARCHIVE --yes`` on ``data_dir``, as an administrator types it, without a terminal."""
    return run([sys.executable, str(SCRIPT), "--test-db", "restore", str(archive), "--yes"], data_dir, "backup restore --yes")


def totals(data_dir: Path) -> dict[str, Any]:
    """The totals of the instance at ``data_dir``, computed in a fresh process in test mode on it."""
    output = data_dir.parent / f"{data_dir.name}-totals.json"
    done = run([sys.executable, "-c", TOTALS_PROGRAM, REPORT_START.isoformat(), REPORT_END.isoformat(), str(output)], data_dir, "the totals")
    assert done.returncode == 0, f"the totals of {data_dir.name} could not be computed: {shown(done)}"
    found = json.loads(output.read_text(encoding="utf-8"))
    assert found["data_dir"] == str(data_dir.resolve()), f"the totals were computed on {found['data_dir']}, not on {data_dir}"
    assert found["database"] == str((data_dir / DATABASE_ENTRY).resolve()), f"the app's session read {found['database']}, not the database of {data_dir}"
    return found


# =============================================================================
# The instances
# =============================================================================


def restore_state(data_dir: Path) -> dict[str, Any] | None:
    """The restore's state as it is on disk (``.restore/restore.json``, contract §1), or ``None``."""
    path = restore_dir(data_dir) / "restore.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def stages_left(data_dir: Path) -> list[str]:
    """What ``.restore/stage/`` holds but its lock: the checked copies."""
    folder = stages_dir(data_dir)
    return sorted(path.name for path in folder.iterdir() if path.name != STAGE_LOCK_FILE) if folder.is_dir() else []


def table_rows(database: Path) -> dict[str, int]:
    """The rows of every table of ``database``, as the report and the manifest count them."""
    names = [row[0] for row in cases.rows_of(database, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    return {name: cases.rows_of(database, f'SELECT count(*) FROM "{name}"')[0][0] for name in names}


def differences(expected: dict[str, Any], found: dict[str, Any]) -> list[str]:
    """The keys whose values differ, or that one side lacks."""
    return sorted(key for key in expected.keys() | found.keys() if expected.get(key) != found.get(key))


def ledger_lines(found: Any) -> dict[str, Any]:
    """J's control totals as one entry per line, for a difference that reads: ``version``, ``cash <broker>/<currency>``,
    ``quantity <broker>/<asset>``. Nothing for what is not totals (``None`` before B-13)."""
    if not isinstance(found, dict):
        return {}
    lines: dict[str, Any] = {"version": found.get("version")}
    lines |= {f"cash {line['broker_id']}/{line['currency']}": line["balance"] for line in found.get("cash", [])}
    lines |= {f"quantity {line['broker_id']}/{line['asset_id']}": line["quantity"] for line in found.get("quantities", [])}
    return lines


def assert_populated(database: Path) -> None:
    """A precondition on the populate's work: the source's database at this LibreFolio's head, and an account that sees
    a broker with transactions, so that a report has something to total."""
    revisions = cases.revisions_of(database)
    assert revisions == [cases.HEAD], f"precondition: the populated database is at the head, {cases.HEAD}, not {revisions}"
    [(owners,)] = cases.rows_of(database, "SELECT count(DISTINCT access.user_id) FROM broker_user_access AS access JOIN transactions AS tx ON tx.broker_id = access.broker_id")
    assert owners >= 1, "precondition: the populated source has an account that sees a broker with transactions"


@dataclass(frozen=True)
class Source:
    """The populated instance, archived: its data directory, its archive and that archive's manifest, the session
    versions its accounts held, and how long the populate took."""

    root: Path
    archive: Path
    manifest: BackupManifest
    versions: set[int]
    populate_seconds: float


@pytest.fixture(scope="module")
def source(tmp_path_factory) -> Source:
    """The project's mock data in a new instance of the test, files of this module, a first start, then its archive."""
    root = tmp_path_factory.mktemp("roundtrip") / "source"
    root.mkdir()
    seconds = populate(root)
    assert_populated(root / DATABASE_ENTRY)
    cases.write_files(root, OWN_FILES)
    started = start(root, FIRST_START)
    assert started.returncode == 0, f"precondition: the source's first start: {shown(started)}"
    with pytest.MonkeyPatch.context() as patch:
        configured = cases.configure(patch, root.parent / "configured-data-dir")
        try:
            job, folder = jobs.run_backup(origin="cli", data_dir=root)
        finally:
            get_git_version.cache_clear()
    assert not configured.exists(), f"the backup wrote in the configured data directory: {cases.listing(configured)}"
    assert (job.status, job.error_code) == ("done", None) and job.file_name, f"precondition: the source is archived: {job}"
    archive = folder / job.file_name
    with zipfile.ZipFile(archive) as zf:
        manifest = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
    assert set(OWN_FILES) <= {entry.path for entry in manifest.files}, f"this module's files are in the archive: {sorted(set(OWN_FILES) - {entry.path for entry in manifest.files})}"
    assert not production_of(root).exists(), f"a child wrote in its production data directory: {cases.listing(production_of(root))}"
    versions = {row[0] for row in cases.rows_of(root / DATABASE_ENTRY, "SELECT DISTINCT session_version FROM users")}
    return Source(root=root, archive=archive, manifest=manifest, versions=versions, populate_seconds=seconds)


@pytest.fixture(scope="module")
def empty_instance(databases, tmp_path_factory) -> Path:
    """An empty instance after its first start: a database made at the head by alembic in a process of its own, no
    account, the folders, default avatars and settings a start writes."""
    root = tmp_path_factory.mktemp("empty") / "instance"
    (root / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(databases.head, root / DATABASE_ENTRY)
    started = start(root, FIRST_START)
    assert started.returncode == 0, f"precondition: the empty instance's first start: {shown(started)}"
    found = (cases.revisions_of(root / DATABASE_ENTRY), cases.rows_of(root / DATABASE_ENTRY, "SELECT count(*) FROM users"), restore_state(root))
    assert found == ([cases.HEAD], [(0,)], None), f"precondition: at the head, no account, no restore: {found}"
    return root


@pytest.fixture(scope="module")
def older_ledger_archive(databases, tmp_path_factory) -> BuiltArchive:
    """A backup at ``OLDER`` with a ledger, made by this LibreFolio's backup (``archive.build_archive``) as
    ``test_backup_staging.py`` makes its ``older_archive``: that module's accounts and files, and ``LEDGER_AT_OLDER``."""
    root = tmp_path_factory.mktemp("older-ledger-archive")
    with pytest.MonkeyPatch.context() as patch:
        configured = cases.configure(patch, root / "configured-data-dir")
        try:
            data = cases.make_data_dir(root / "data", databases.older)
            cases.execute(data / DATABASE_ENTRY, *LEDGER_AT_OLDER)
            built = cases.build_into(data, root / "work")
        finally:
            get_git_version.cache_clear()
    assert not configured.exists(), f"the backup wrote in the configured data directory: {cases.listing(configured)}"
    assert (built.manifest.alembic_revision, built.warnings) == (cases.OLDER, ()), f"precondition: a clean archive at {cases.OLDER}: {built.manifest.alembic_revision}, {built.warnings}"
    assert built.manifest.database.tables.get("transactions") == len(LEDGER_TRANSACTIONS), f"precondition: the archive holds the ledger: {built.manifest.database.tables.get('transactions')} transactions"
    return built


@pytest.fixture
def target(empty_instance, tmp_path) -> Iterator[Path]:
    """A copy of the empty instance, for one test. At its end, its children wrote nothing in their production data
    directory."""
    root = tmp_path / "target"
    shutil.copytree(empty_instance, root, symlinks=True)
    yield root
    assert not production_of(root).exists(), f"a child wrote in its production data directory: {cases.listing(production_of(root))}"


# =============================================================================
# §9 The founder's acceptance
# =============================================================================


def test_a_backup_of_a_populated_instance_restored_on_an_empty_instance_gives_the_same_totals(source, target):
    """§9.1 Checked and confirmed by the command line (the copy kept, nothing written outside ``.restore``), applied and
    committed by the next start; then the totals of the source and of the target, back to back. The source's are what
    its archive holds (rows and files); the target's are the same: every table holds the rows it held, every file is
    back byte for byte, every account's portfolio report is the same, and so is the ledger's control totals. ``committed``,
    nothing of the restore left; every account at the restore's session value, above every version the source held: no
    session of the source survives. B-13 §6: the source's ledger totals are those its archive's manifest recorded at the
    backup, and the check reported them ``same``."""
    print_section("§9.1 A populated instance, restored on an empty one")
    before = cases.fingerprint(target)
    confirmed = restore_yes(source.archive, target)
    assert confirmed.returncode == 0, f"restore --yes checks the archive on a copy and confirms it: {shown(confirmed)}"
    pending = restore_state(target)
    assert pending is not None and pending["status"] == "pending", f"the restore waits for the next start: {pending}"
    assert (stage_dir(target, pending["stage_id"]) / STAGE_DATA_FOLDER / DATABASE_ENTRY).is_file(), "the checked copy is kept for the start"
    assert cases.changed(before, cases.fingerprint(target)) == [], f"a confirmation writes nothing outside .restore: {cases.changed(before, cases.fingerprint(target))}"
    # Read now: the commit removes the copy and its report.
    checked = read_report(target, pending["stage_id"])
    started = start(target, RESTORE_START)
    assert started.returncode == 0, f"the start applies and commits the restore: {shown(started)}"
    state = restore_state(target)
    assert state is not None and state["status"] == "committed", f"committed by the start: {state}"
    left = [name for name in ("previous", "failed") if (restore_dir(target) / name).exists()] + stages_left(target)
    assert left == [], f"nothing of the restore left: {left}"
    versions = {row[0] for row in cases.rows_of(target / DATABASE_ENTRY, "SELECT DISTINCT session_version FROM users")}
    assert versions == {state["session_version"]}, f"every account at the restore's session value: {versions}, {state['session_version']}"
    assert state["session_version"] > max(source.versions), "above every version the source held"

    original, restored = totals(source.root), totals(target)
    archived_files = {entry.path: entry.sha256 for entry in source.manifest.files[1:]}
    assert source.manifest.database.tables == original["rows"], f"the archive holds the source's rows: {differences(original['rows'], source.manifest.database.tables)}"
    assert archived_files == original["files"], f"the archive holds the source's files: {differences(original['files'], archived_files)}"
    assert original["reports"], "precondition: an account of the source has a portfolio to report"
    assert differences(original["rows"], restored["rows"]) == [], f"the rows of every table: {differences(original['rows'], restored['rows'])}"
    assert differences(original["files"], restored["files"]) == [], f"every file: {differences(original['files'], restored['files'])}"
    assert differences(original["reports"], restored["reports"]) == [], f"every account's portfolio report: {differences(original['reports'], restored['reports'])}"
    ledger = original["control_totals"]
    assert ledger["cash"] and ledger["quantities"], f"precondition: the populated ledger has cash and positions to total: {ledger}"
    assert restored["control_totals"] == ledger, f"the ledger's control totals: {differences(ledger_lines(ledger), ledger_lines(restored['control_totals']))}"

    # B-13: what the backup recorded, and what the check said.
    recorded = getattr(source.manifest.database, "control_totals", None)
    assert recorded == ledger, f"[new] the archive's manifest records the source's ledger totals, read on the backup's snapshot (B-13 §2): {differences(ledger_lines(ledger), ledger_lines(recorded))}"
    status = getattr(checked, "control_totals", None)
    assert status == "same", f"[new] the check compares the archive's ledger totals with its copy's: the same (B-13 §3), not {status!r}"
    assert (list(checked.control_totals_differences), checked.control_totals_differences_count) == ([], 0), f"no difference: {checked.control_totals_differences}, {checked.control_totals_differences_count}"
    assert not TOTALS_WARNINGS & set(checked.warnings), f"no warning about the ledger's totals: {checked.warnings}"
    print_success(f"{len(restored['rows'])} tables, {len(restored['files'])} files, {len(restored['reports'])} reports, {len(ledger['cash'])} cash lines and {len(ledger['quantities'])} positions: the same (populate {source.populate_seconds:.1f}s)")


def test_an_older_backup_is_restored_through_the_check_and_the_confirmation(older_ledger_archive, target):
    """§9.2 A backup at ``OLDER``: the check upgrades its copy (a real ``alembic upgrade``), the start puts it in place.
    Committed, the live database at the head, its rows as the check's report said — but ``global_settings``, to which
    the start's ``global-settings`` step adds the defaults the backup lacked, and only those: every setting the check
    left is there, unchanged. The backup's administrators are the instance's. Its ledger (B-13 §6): the restored database
    at the head has the totals of ``LEDGER_AT_OLDER``; the manifest made at ``OLDER`` by this LibreFolio's backup records
    them, and the check reports them ``same`` after its upgrade."""
    print_section("§9.2 A backup at an older revision")
    confirmed = restore_yes(older_ledger_archive.path, target)
    assert confirmed.returncode == 0, f"restore --yes checks the archive on a copy and confirms it: {shown(confirmed)}"
    pending = restore_state(target)
    assert pending is not None and (pending["status"], pending["action"]) == ("pending", "upgrade"), f"an upgrade waits for the next start: {pending}"
    report = read_report(target, pending["stage_id"])
    assert (report.backup.alembic_revision, report.head_revision, report.action) == (cases.OLDER, cases.HEAD, "upgrade"), f"the check upgraded {report.backup.alembic_revision} to {report.head_revision}"
    copy = stage_dir(target, pending["stage_id"]) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    checked_settings = set(cases.rows_of(copy, "SELECT key, value FROM global_settings"))
    started = start(target, RESTORE_START)
    assert started.returncode == 0, f"the start applies and commits the restore: {shown(started)}"
    state = restore_state(target)
    assert state is not None and state["status"] == "committed", f"committed by the start: {state}"
    database = target / DATABASE_ENTRY
    assert cases.revisions_of(database) == [cases.HEAD], f"the live database at the head: {cases.revisions_of(database)}"
    expected = {name: rows.after for name, rows in report.tables.items() if rows.after is not None}
    found = table_rows(database)
    changed = differences({name: rows for name, rows in expected.items() if name != "global_settings"}, {name: rows for name, rows in found.items() if name != "global_settings"})
    assert changed == [], f"the rows the check's report said: {[(name, expected.get(name), found.get(name)) for name in changed]}"
    live_settings = set(cases.rows_of(database, "SELECT key, value FROM global_settings"))
    added = {key for key, _value in live_settings} - {key for key, _value in checked_settings}
    assert checked_settings <= live_settings, f"every setting the check left, unchanged: {sorted(checked_settings - live_settings)}"
    assert added <= set(GLOBAL_SETTINGS_DEFAULTS), f"the start adds only default settings: {sorted(added - set(GLOBAL_SETTINGS_DEFAULTS))}"
    assert found["global_settings"] == expected["global_settings"] + len(added), f"global_settings: {expected['global_settings']} restored + {len(added)} defaults, not {found['global_settings']}"
    administrators = [row[0] for row in cases.rows_of(database, "SELECT username FROM users WHERE is_superuser = 1 AND is_active = 1 ORDER BY username")]
    assert administrators == report.administrators, f"the backup's administrators sign in after it: {administrators}"
    measured = totals(target)
    assert measured["control_totals"] == LEDGER_AT_OLDER_TOTALS, f"the restored database at the head holds the ledger written at {cases.OLDER}: {differences(ledger_lines(LEDGER_AT_OLDER_TOTALS), ledger_lines(measured['control_totals']))}"

    # B-13: what the backup at OLDER recorded, and what the check said after its upgrade.
    recorded = getattr(older_ledger_archive.manifest.database, "control_totals", None)
    assert recorded == LEDGER_AT_OLDER_TOTALS, f"[new] the manifest made at {cases.OLDER} by this LibreFolio's backup records the totals of its ledger (B-13 §2): {differences(ledger_lines(LEDGER_AT_OLDER_TOTALS), ledger_lines(recorded))}"
    status = getattr(report, "control_totals", None)
    assert status == "same", f"[new] the check compares the archive's ledger totals with its copy's after the upgrade: the same (B-13 §3), not {status!r}"
    assert (list(report.control_totals_differences), report.control_totals_differences_count) == ([], 0), f"no difference: {report.control_totals_differences}, {report.control_totals_differences_count}"
    assert not TOTALS_WARNINGS & set(report.warnings), f"no warning about the ledger's totals: {report.warnings}"
    print_success(f"{cases.OLDER} → {cases.HEAD}: committed, {len(expected)} tables as the report said, the ledger's totals the same")


def test_a_backup_of_a_newer_librefolio_is_refused_and_the_target_is_left_as_it_was(databases, target, tmp_path):
    """§9.3 A database at a revision this LibreFolio does not know (a newer one, most likely): the check refuses it
    (``revision_unknown``, B2), the command exits 1 with the code in parentheses, nothing is confirmed, no copy is left,
    and the target is untouched."""
    print_section("§9.3 A backup of a newer LibreFolio")
    archive = cases.newer_revision(tmp_path / "newer", None, databases)
    before = cases.fingerprint(target)
    refused = restore_yes(archive, target)
    assert refused.returncode == 1 and "(revision_unknown)" in refused.stdout, f"refused by the check, exit 1, its code in parentheses: {shown(refused)}"
    assert (restore_state(target), stages_left(target)) == (None, []), "nothing confirmed, no copy left"
    assert cases.changed(before, cases.fingerprint(target)) == [], f"the target untouched: {cases.changed(before, cases.fingerprint(target))}"
    print_success("revision_unknown, exit 1, nothing changed")

"""
The figures the hosting panel reads of an instance (lot CL-M1, ``GET /api/v1/panel/metrics``): the service behind the
route, ``backend/app/services/platform/hosting_panel/metrics.py``, and its answer ``PanelMetricsResponse``
(``backend/app/schemas/hosting_panel.py``).

The contract these cases pin (SECURITY lot: the panel sees figures, never who):

- ``collect_panel_metrics(session)`` answers a ``PanelMetricsResponse`` with all of its 15 keys, always present. A measure
  that fails is ``null`` and never a 500, and each measure fails alone: ``process_started_at`` -> ``started_at``;
  ``storage_usage_mb`` -> ``storage_used_mb`` and ``storage_limit_mb``; ``database_size_mb`` -> ``database_mb``;
  ``uploads_size_mb`` -> ``uploads_mb``; ``config_warnings`` -> ``config_warnings``; ``job_figures`` ->
  ``price_refresh_last_ok_at``, ``price_refresh_errors_24h``, ``jobs_failed_24h``; ``table_counts`` -> the three counts;
  ``providers_in_use`` -> ``plugins_enabled``. A failing measure is logged once, with its traceback and the name of its
  key; one that left the shared session in need of a rollback (a failed flush) does not poison the next.
- Sizes are in MiB (1024 * 1024) rounded to 0.1: the filesystem holding the data directory (``shutil.disk_usage``), the
  SQLite file with its ``-wal``, the ``custom-uploads`` folder (recursive, symbolic links never followed).
- ``config_warnings``: every check of the Security tab that is not ``ok`` (``run_config_checks()``, then
  ``check_plugin_secrets(session)``, then ``check_instance_key(session)``), as ``{check_id, severity}`` and nothing else:
  never the detail, the i18n key or a value.
- The job log (``scheduler/joblog.py``): ``price_refresh_last_ok_at`` is the ``ts`` of the newest entry of the job
  ``current_price`` or ``history_sync`` whose status is ``ok`` (any age; ``partial`` and ``error`` never); the errors are
  the ``summary.err`` of those two jobs' entries of the last 24 hours; ``jobs_failed_24h`` the entries of ANY job with
  status ``error`` in the last 24 hours. With an empty log: ``None``, 0, 0.
- Row counts of Broker, Transaction and Asset; ``plugins_enabled`` is the sorted distinct ``provider_code`` of the
  asset provider assignments. ``market_data_credits_*`` are always null.
- Privacy: no email, user name, broker or asset name, path of the data directory or secret in the JSON.

How. In process, pure: the data directory is ``tmp_path/data`` (test mode, ``LIBREFOLIO_TEST_DATA_DIR``), the database an
in-memory SQLite the test fills itself and owns entirely (so a count is legitimate here), ``shutil.disk_usage`` is
replaced by a recording stand-in. No server, no lane database, no network. ``metrics`` is imported by the fixture that
needs it, so the file collects and each test reports the missing module as its red.

Red today: ``hosting_panel/metrics.py`` and ``PanelMetricsResponse`` do not exist.
"""

from __future__ import annotations

import collections
import importlib
import json
import os
import shutil
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from structlog.testing import capture_logs

from backend.app.config import API_V1_PREFIX, get_data_dir, is_test_mode
from backend.app.db.base import SQLModel  # imports every model: the in-memory database gets the whole ORM schema
from backend.app.db.models import Asset, AssetProviderAssignment, Broker, PluginSystemSetting, ProviderInputType, Transaction, TransactionType, User
from backend.app.services.platform.sleep_wake.activity import request_kind
from backend.test_scripts.test_utils import print_section, print_success

METRICS_MODULE = "backend.app.services.platform.hosting_panel.metrics"
SCHEMAS_MODULE = "backend.app.schemas.hosting_panel"

MIB = 1024 * 1024

#: The 15 keys of the answer, exactly, and the keys each measure owns (a measure that fails nulls its keys alone).
ANSWER_KEYS = frozenset(
    {
        "started_at",
        "storage_used_mb",
        "storage_limit_mb",
        "database_mb",
        "uploads_mb",
        "config_warnings",
        "price_refresh_last_ok_at",
        "price_refresh_errors_24h",
        "jobs_failed_24h",
        "brokers_count",
        "transactions_count",
        "assets_count",
        "plugins_enabled",
        "market_data_credits_used",
        "market_data_credits_limit",
    }
)
SEAMS: dict[str, tuple[str, ...]] = {
    "process_started_at": ("started_at",),
    "storage_usage_mb": ("storage_used_mb", "storage_limit_mb"),
    "database_size_mb": ("database_mb",),
    "uploads_size_mb": ("uploads_mb",),
    "config_warnings": ("config_warnings",),
    "job_figures": ("price_refresh_last_ok_at", "price_refresh_errors_24h", "jobs_failed_24h"),
    "table_counts": ("brokers_count", "transactions_count", "assets_count"),
    "providers_in_use": ("plugins_enabled",),
}
ASYNC_SEAMS = frozenset({"config_warnings", "table_counts", "providers_in_use"})
SEAM_CASES = [pytest.param(name, id=name) for name in SEAMS]
ALWAYS_NULL = ("market_data_credits_used", "market_data_credits_limit")

#: Canaries: a figure of the panel must never show who or what the instance holds.
CANARY = "clm1canary"
BROKER_NAMES = (f"{CANARY}-broker-alpha", f"{CANARY}-broker-beta")
ASSET_NAMES = (f"{CANARY}-asset-1", f"{CANARY}-asset-2", f"{CANARY}-asset-3", f"{CANARY}-asset-4")
USER_NAME = f"{CANARY}_user"
USER_EMAIL = f"{CANARY}_user@example.com"
TX_DESCRIPTION = f"{CANARY}-private-note"

#: What the world below holds, so a swapped or mixed-up count shows: 2 brokers, 3 transactions, 4 assets, 2 providers.
BROKERS, TRANSACTIONS, ASSETS = 2, 3, 4
PROVIDERS = ["justetf", "yfinance"]  # sorted; the insertion order is yfinance first

#: The files of the world: sizes chosen so no rounding is a tie (2.5977 -> 2.6, 2.0977 -> 2.1, 1.5859 -> 1.6).
DATABASE_BYTES = 2 * MIB + 100 * 1024
WAL_BYTES = 512 * 1024
DATABASE_MB, DATABASE_WITHOUT_WAL_MB = 2.6, 2.1
UPLOAD_BYTES = (MIB, 600 * 1024)
UPLOADS_MB = 1.6
OUTSIDE_BYTES = 3 * MIB  # behind the symbolic links: counting any of it is following a link

#: The filesystem the stand-in ``shutil.disk_usage`` reports.
DISK_TOTAL = int(20000.04 * MIB)
DISK_USED = int(1234.5678 * MIB)
DISK_LIMIT_MB, DISK_USED_MB = 20000.0, 1234.6

JOB_LOG = ("logs", "scheduler_jobs.jsonl")
PRICE_JOBS = ("current_price", "history_sync")
JWT_CANARY = "Clm1Jwt-short-7Q"
KEY_FILE_CANARY = "clm1canary-secret-file-that-does-not-exist"
INSTANCE_KEY_CANARY = "clm1canary-instance-key-0123456789abcdef"  # 32+ characters: a usable key from the environment


# =============================================================================
# The module under test, imported by the test that needs it
# =============================================================================


def _missing(module: str, error: ModuleNotFoundError) -> bool:
    return error.name is not None and (module == error.name or module.startswith(f"{error.name}."))


@pytest.fixture
def metrics() -> Any:
    """``hosting_panel/metrics.py`` of CL-M1: a test that needs it fails here, naming what is missing."""
    try:
        return importlib.import_module(METRICS_MODULE)
    except ModuleNotFoundError as error:
        if not _missing(METRICS_MODULE, error):
            raise
    pytest.fail(f"CL-M1: {METRICS_MODULE} does not exist yet (backend/app/services/platform/hosting_panel/metrics.py)")


def response_class() -> Any:
    """``PanelMetricsResponse`` of CL-M1, or a red naming it."""
    module = importlib.import_module(SCHEMAS_MODULE)
    found = getattr(module, "PanelMetricsResponse", None)
    if found is None:
        pytest.fail(f"CL-M1: {SCHEMAS_MODULE} gives no PanelMetricsResponse")
    return found


def seam(module: Any, name: str) -> Callable[..., Any]:
    found = getattr(module, name, None)
    if not callable(found):
        pytest.fail(f"CL-M1: {METRICS_MODULE} gives no {name}()")
    return found


# =============================================================================
# The world: data directory, files, job log, database
# =============================================================================


def entry(job: str, status: str, when: datetime, **summary: Any) -> dict[str, Any]:
    """A job-log entry as the scheduler writes it: ``ts`` with its offset, ``job``, ``status``, ``summary``."""
    return {"ts": when.isoformat(), "job": job, "duration_s": 1.0, "status": status, "summary": summary, "retry_at": None, "items": []}


def write_job_log(root: Path, entries: list[dict[str, Any]] | list[str]) -> Path:
    """The scheduler's job log under ``root``, one JSON line per entry (a string is written as it is), in the order given."""
    path = root.joinpath(*JOB_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join((item if isinstance(item, str) else json.dumps(item)) + "\n" for item in entries), encoding="utf-8")
    return path


def happy_entries(now: datetime) -> list[dict[str, Any]]:
    """The log of the world, none of it within an hour of the 24 h edge: last ok 5 h ago; errors 2 + 1 + 4; two failed."""
    return [
        entry("current_price", "ok", now - timedelta(hours=40), ok=1, err=50),
        entry("current_price", "error", now - timedelta(hours=30), ok=0, err=100),
        entry("current_price", "ok", now - timedelta(hours=5), ok=3, err=2),
        entry("fx_sync", "error", now - timedelta(hours=4), err=9),
        entry("current_price", "partial", now - timedelta(hours=3), ok=2, err=1),
        entry("current_price", "error", now - timedelta(hours=1), ok=0, err=4),
        entry("fx_sync", "ok", now - timedelta(minutes=30), ok=5, err=0),
    ]


HAPPY_LAST_OK_HOURS = 5
HAPPY_ERRORS = 2 + 1 + 4
HAPPY_FAILED = 2


def write_data_files(root: Path) -> Path:
    """The database file with its ``-wal``, and ``custom-uploads`` with a nested file and links that lead outside it.
    Returns the folder behind the links."""
    (root / "sqlite").mkdir(parents=True, exist_ok=True)
    (root / "sqlite" / "app.db").write_bytes(b"\0" * DATABASE_BYTES)
    (root / "sqlite" / "app.db-wal").write_bytes(b"\0" * WAL_BYTES)
    uploads = root / "custom-uploads"
    (uploads / "sub" / "deeper").mkdir(parents=True, exist_ok=True)
    (uploads / "a.bin").write_bytes(b"\0" * UPLOAD_BYTES[0])
    (uploads / "sub" / "deeper" / "b.bin").write_bytes(b"\0" * UPLOAD_BYTES[1])
    outside = root.parent / "outside-the-data-directory"
    outside.mkdir(exist_ok=True)
    (outside / "big.bin").write_bytes(b"\0" * OUTSIDE_BYTES)
    os.symlink(outside / "big.bin", uploads / "link-to-file.bin")
    os.symlink(outside, uploads / "sub" / "link-to-folder")
    os.symlink(uploads, uploads / "sub" / "loop")
    return outside


async def seed_world(session: AsyncSession) -> None:
    """2 brokers, 4 assets (3 with a provider: yfinance, justetf, yfinance), 3 transactions and one user, all named with
    canaries."""
    session.add(User(username=USER_NAME, email=USER_EMAIL, hashed_password="not-a-password-hash"))
    brokers = [Broker(name=name) for name in BROKER_NAMES]
    assets = [Asset(display_name=name, currency="EUR") for name in ASSET_NAMES]
    session.add_all([*brokers, *assets])
    await session.flush()
    for asset, code in zip(assets, ("yfinance", "justetf", "yfinance"), strict=False):
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=code, identifier=f"{CANARY}-{asset.id}", identifier_type=ProviderInputType.TICKER))
    for index in range(TRANSACTIONS):
        session.add(
            Transaction(
                broker_id=brokers[index % 2].id,
                asset_id=assets[index].id,
                type=TransactionType.BUY,
                date=datetime(2026, 1, 2 + index, tzinfo=UTC).date(),
                quantity=Decimal("2"),
                amount=Decimal("-20"),
                currency="EUR",
                description=TX_DESCRIPTION,
            )
        )
    await session.commit()


DiskUsage = collections.namedtuple("DiskUsage", "total used free")


@dataclass
class FakeDisk:
    """Stands in for ``shutil.disk_usage``: a fixed filesystem, the paths it was asked about."""

    asked: list[Path] = field(default_factory=list)

    def __call__(self, path: Any) -> DiskUsage:
        self.asked.append(Path(path))
        return DiskUsage(DISK_TOTAL, DISK_USED, DISK_TOTAL - DISK_USED)


@dataclass
class World:
    root: Path
    outside: Path
    session: AsyncSession
    disk: FakeDisk
    now: datetime


def use_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Test mode on ``tmp_path/data`` (the job log, the files and the registry of tickets all read it), and no secret or
    switch from the runner's environment."""
    assert is_test_mode(), "Precondition: test mode, so nothing here reaches the production data directory"
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    for name in ("JWT_SECRET", "JWT_SECRET_FILE", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE", "LIBREFOLIO_INSTANCE_KEY_ACCEPT", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_AWAIT_RESTORE", "LIBREFOLIO_DELETION_DATE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    assert get_data_dir() == root, f"Precondition: the data directory is this test's own, not {get_data_dir()}"
    return root


@pytest_asyncio.fixture
async def empty_db() -> AsyncIterator[AsyncSession]:
    """An in-memory database with the ORM schema and nothing in it; closed and disposed on the way out."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def world(metrics: Any, empty_db: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> World:
    """The data directory, its files, its job log (``happy_entries``), the database seeded and the disk stood in for."""
    root = use_data_dir(monkeypatch, tmp_path)
    outside = write_data_files(root)
    now = datetime.now(UTC)
    write_job_log(root, happy_entries(now))
    await seed_world(empty_db)
    disk = FakeDisk()
    monkeypatch.setattr(shutil, "disk_usage", disk)
    return World(root, outside, empty_db, disk, now)


def keys_of(response: Any) -> dict[str, Any]:
    """The answer as plain data (datetimes as ISO text), to compare whole."""
    return json.loads(response.model_dump_json())


def warnings_of(response: Any) -> list[dict[str, Any]]:
    return [dict(item) if isinstance(item, dict) else item.model_dump() for item in (response.config_warnings or [])]


# =============================================================================
# CM-001..004: the schema
# =============================================================================


def test_the_answer_has_exactly_the_15_keys_all_required_and_refuses_any_other():
    """CM-001: ``PanelMetricsResponse`` has exactly the 15 keys, every one required (a measure that fails is ``null``, it
    is never absent), ``extra="forbid"`` so a key added later is a decision, and a response of 15 nulls is valid."""
    print_section("CM-001: PanelMetricsResponse, its 15 required keys")
    model = response_class()

    assert set(model.model_fields) == ANSWER_KEYS, f"the keys: only here {sorted(set(model.model_fields) - ANSWER_KEYS)}, missing {sorted(ANSWER_KEYS - set(model.model_fields))}"
    optional = sorted(name for name, info in model.model_fields.items() if not info.is_required())
    assert optional == [], f"every key is required (always present, null when its measure fails): {optional}"
    assert model.model_config.get("extra") == "forbid", f"extra must be forbid: {model.model_config}"
    all_null = dict.fromkeys(ANSWER_KEYS)
    assert model(**all_null), "a response whose 15 measures all failed is valid"
    with pytest.raises(ValidationError):
        model(**all_null, email="someone@example.com")
    with pytest.raises(ValidationError):
        model(**dict.fromkeys(ANSWER_KEYS - {"brokers_count"}))
    print_success("15 required keys, extra forbidden")


def test_a_config_warning_has_exactly_check_id_and_severity_and_never_ok():
    """CM-002: the items of ``config_warnings`` hold ``check_id`` and ``severity`` and nothing else (no detail, no i18n
    key), and the severity is ``info``, ``warning`` or ``error``: an ``ok`` check is not a warning."""
    schema = response_class().model_json_schema()
    definitions = schema.get("$defs", {})

    def resolved(node: dict[str, Any]) -> dict[str, Any]:
        reference = node.get("$ref")
        return definitions[reference.rsplit("/", 1)[-1]] if reference else node

    prop = schema["properties"]["config_warnings"]
    arrays = [variant for variant in prop.get("anyOf", [prop]) if variant.get("type") == "array"]
    assert len(arrays) == 1, f"config_warnings is a list or null: {prop}"
    item = resolved(arrays[0]["items"])
    properties = item.get("properties") or {}
    assert set(properties) == {"check_id", "severity"} and item.get("additionalProperties") is False, f"an item has exactly check_id and severity, and no other: {item}"
    severities = set(resolved(properties["severity"]).get("enum", []))
    assert severities == {"info", "warning", "error"}, f"severity is info, warning or error: {severities}"


def test_the_limit_of_the_job_log_is_declared_where_the_panel_reads_it():
    """CM-003: ``jobs_failed_24h`` can only count what the job log still holds (the last ``MAX_ENTRIES``, 500): the
    field's description says so, so it is in the OpenAPI document the panel reads."""
    from backend.app.services.platform.scheduler import joblog  # noqa: PLC0415

    assert joblog.MAX_ENTRIES == 500, "Barrier: the declared limit is the log's"
    description = response_class().model_fields["jobs_failed_24h"].description or ""
    assert "500" in description, f"jobs_failed_24h must declare that the job log keeps the last 500 entries: {description!r}"
    for name in ("price_refresh_errors_24h", "price_refresh_last_ok_at", "config_warnings", "storage_used_mb", "uploads_mb", "plugins_enabled"):
        assert (response_class().model_fields[name].description or "").strip(), f"{name} has a description (the OpenAPI document is the contract the panel reads)"


def test_a_metrics_call_is_never_user_activity():
    """CM-004: the panel's metrics path is under ``PANEL_PATH_PREFIXES``, so the activity middleware classifies it as the
    wake-up (in flight, never the user): a panel polling the figures never keeps a machine awake."""
    for path in (f"{API_V1_PREFIX}/panel/metrics", f"{API_V1_PREFIX}/panel/metrics/"):
        assert request_kind(path) == "wake", f"{path} must not be a visit: {request_kind(path)}"


# =============================================================================
# CM-010..014: the happy path
# =============================================================================


@pytest.mark.asyncio
async def test_the_figures_of_a_known_instance(metrics, world):
    """CM-010: with a world the test made (2 brokers, 3 transactions, 4 assets, 3 assignments of 2 providers, a database
    file with its wal, uploads, a job log, a disk), ``collect_panel_metrics`` answers every figure."""
    print_section("CM-010: the figures of a known instance")
    response = await seam(metrics, "collect_panel_metrics")(world.session)

    assert isinstance(response, response_class()), f"a PanelMetricsResponse: {type(response)}"
    assert response.started_at == seam(metrics, "process_started_at")(), "started_at is the start of this process"
    figures = {
        "storage_limit_mb": DISK_LIMIT_MB,
        "storage_used_mb": DISK_USED_MB,
        "database_mb": DATABASE_MB,
        "uploads_mb": UPLOADS_MB,
        "price_refresh_errors_24h": HAPPY_ERRORS,
        "jobs_failed_24h": HAPPY_FAILED,
        "brokers_count": BROKERS,
        "transactions_count": TRANSACTIONS,
        "assets_count": ASSETS,
        "plugins_enabled": PROVIDERS,
        "market_data_credits_used": None,
        "market_data_credits_limit": None,
    }
    got = {name: getattr(response, name) for name in figures}
    assert got == figures, f"the figures of the known instance:\n  expected {figures}\n  got      {got}"
    assert response.price_refresh_last_ok_at == world.now - timedelta(hours=HAPPY_LAST_OK_HOURS), f"the last ok price refresh is the 5 h old entry, not the newer partial or error, nor another job's ok: {response.price_refresh_last_ok_at}"
    assert world.root in world.disk.asked, f"the disk is the one holding the data directory {world.root}: asked {world.disk.asked}"
    print_success("every figure of the known instance")


@pytest.mark.asyncio
async def test_an_empty_instance_answers_zeros_and_an_empty_list_not_nulls(metrics, empty_db, monkeypatch, tmp_path):
    """CM-011: nothing in the database and no job log: the counts are 0, ``plugins_enabled`` is ``[]``, the errors and
    failures 0 and the last ok ``None``: null is the answer of a measure that FAILED, never of one that found nothing."""
    root = use_data_dir(monkeypatch, tmp_path)
    write_data_files(root)
    monkeypatch.setattr(shutil, "disk_usage", FakeDisk())

    response = await seam(metrics, "collect_panel_metrics")(empty_db)

    got = (response.brokers_count, response.transactions_count, response.assets_count, response.plugins_enabled, response.price_refresh_errors_24h, response.jobs_failed_24h, response.price_refresh_last_ok_at)
    assert got == (0, 0, 0, [], 0, 0, None), f"an empty instance: zero counts, an empty list, no failure, no last ok: {got}"


@pytest.mark.asyncio
async def test_the_json_names_neither_who_nor_where(metrics, world):
    """CM-012 (privacy): no email, user name, broker or asset name, transaction note, identifier or path of the data
    directory in the answer: it holds figures."""
    response = await seam(metrics, "collect_panel_metrics")(world.session)
    shown = response.model_dump_json()

    leaked = [canary for canary in (CANARY, USER_EMAIL, USER_NAME, TX_DESCRIPTION, *BROKER_NAMES, *ASSET_NAMES, str(world.root), str(world.root.parent), "@") if canary in shown]
    assert leaked == [], f"the answer shows {leaked}: {shown}"
    assert len(json.loads(shown)) == len(ANSWER_KEYS)


def test_the_start_of_the_process_is_one_aware_instant_in_the_past(metrics):
    """CM-013: ``process_started_at()`` is a UTC instant before now, the same at each call: when this server process
    started, not when the panel asked."""
    first, second = seam(metrics, "process_started_at")(), seam(metrics, "process_started_at")()

    assert first == second, "the start of the process does not move"
    assert first.utcoffset() == timedelta(0), f"started_at is in UTC: {first!r}"
    assert first <= datetime.now(UTC), f"the process started before now: {first!r}"


def test_the_storage_is_the_filesystem_of_the_data_directory_in_mib_to_a_tenth(metrics, monkeypatch, tmp_path):
    """CM-014: ``storage_usage_mb()`` reads ``shutil.disk_usage`` of the data directory: used and total in MiB, rounded
    to 0.1 (1234.5678 -> 1234.6)."""
    root = use_data_dir(monkeypatch, tmp_path)
    disk = FakeDisk()
    monkeypatch.setattr(shutil, "disk_usage", disk)

    used, limit = seam(metrics, "storage_usage_mb")()

    assert (used, limit) == (DISK_USED_MB, DISK_LIMIT_MB), f"used and limit in MiB to a tenth: {(used, limit)}"
    assert root in disk.asked, f"asked about the data directory {root}: {disk.asked}"


# =============================================================================
# CM-020..024: the files
# =============================================================================


def test_the_database_is_its_file_and_its_wal(metrics, monkeypatch, tmp_path):
    """CM-020: ``database_size_mb()`` is ``sqlite/app.db`` plus ``sqlite/app.db-wal`` in MiB to a tenth (2.5977 -> 2.6);
    without a wal, the file alone (2.0977 -> 2.1)."""
    root = use_data_dir(monkeypatch, tmp_path)
    write_data_files(root)

    with_wal = seam(metrics, "database_size_mb")()
    (root / "sqlite" / "app.db-wal").unlink()
    without_wal = seam(metrics, "database_size_mb")()

    assert (with_wal, without_wal) == (DATABASE_MB, DATABASE_WITHOUT_WAL_MB), f"the file with its wal, then alone: {(with_wal, without_wal)}"


def test_the_uploads_are_the_files_of_the_folder_recursively_and_no_link_is_followed(metrics, monkeypatch, tmp_path):
    """CM-021: ``uploads_size_mb()`` adds the files of ``custom-uploads`` at any depth (1 MiB + 600 KiB = 1.6), and follows
    no symbolic link: a link to a 3 MiB file, a link to a folder with it and a link back to the folder itself (a loop)
    add nothing, and a link cannot make the figure read outside the folder or never end."""
    root = use_data_dir(monkeypatch, tmp_path)
    outside = write_data_files(root)
    assert (outside / "big.bin").stat().st_size == OUTSIDE_BYTES, "Barrier: the file behind the links is there"
    assert (root / "custom-uploads" / "link-to-file.bin").is_symlink() and (root / "custom-uploads" / "sub" / "loop").is_symlink(), "Barrier: the links are links"

    assert seam(metrics, "uploads_size_mb")() == UPLOADS_MB


@pytest.mark.parametrize("target", ["folder-with-files", "dangling"])
def test_an_uploads_folder_that_is_itself_a_link_is_zero_and_never_followed(metrics, monkeypatch, tmp_path, target):
    """CM-022: when ``custom-uploads`` ITSELF is a symbolic link (to a folder with 3 MiB in it, or to nothing),
    ``uploads_size_mb()`` is 0.0: ``os.walk(..., followlinks=False)`` still walks its top, so the link has to be refused
    before the walk, or the figure reads outside the data directory."""
    root = use_data_dir(monkeypatch, tmp_path)
    elsewhere = root.parent / "uploads-somewhere-else"
    if target == "folder-with-files":
        elsewhere.mkdir()
        (elsewhere / "big.bin").write_bytes(b"\0" * OUTSIDE_BYTES)
    os.symlink(elsewhere, root / "custom-uploads")
    assert (root / "custom-uploads").is_symlink(), "Barrier: custom-uploads is a link"
    # In test mode ``get_data_dir()`` itself refuses a data directory whose custom-uploads leaves it (a ValueError): the figure
    # reads the data directory through the name it imported, which this case gives the directory whose folder is the link.
    monkeypatch.setattr(metrics, "get_data_dir", lambda: root)
    assert target != "folder-with-files" or (root / "custom-uploads" / "big.bin").stat().st_size == OUTSIDE_BYTES, "Barrier: the link leads to the 3 MiB file"

    assert seam(metrics, "uploads_size_mb")() == 0.0, "a link as the uploads folder is nothing uploaded: 0.0, never what lies behind it"


@pytest.mark.parametrize("failure", [FileNotFoundError, PermissionError])
def test_a_file_that_vanishes_during_the_walk_is_skipped_and_the_rest_is_counted(metrics, monkeypatch, tmp_path, failure):
    """CM-023: a file listed by the walk that is gone (or cannot be read) when ``os.lstat`` asks for its size is skipped
    (an upload deleted while the panel measures): the measure does not fail, it counts the others. ``a.bin`` (1 MiB)
    vanishes, ``sub/deeper/b.bin`` (600 KiB) stands: 0.6."""
    root = use_data_dir(monkeypatch, tmp_path)
    write_data_files(root)
    real_lstat = os.lstat

    def lstat(path: Any, *args: Any, **kwargs: Any) -> Any:
        if os.fspath(path).endswith("a.bin"):
            raise failure(2, "vanished mid-walk", os.fspath(path))
        return real_lstat(path, *args, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", lstat)
        got = seam(metrics, "uploads_size_mb")()

    assert got == round(UPLOAD_BYTES[1] / MIB, 1), f"the file that vanished adds nothing and the other one is counted (0.6), the measure is not lost: {got}"


# =============================================================================
# CM-030..039: the job log
# =============================================================================

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
WINDOW = timedelta(hours=24)


def figures(metrics: Any, root: Path, entries: list[Any], *, now: datetime = NOW) -> tuple[Any, Any, Any]:
    write_job_log(root, entries)
    last_ok, errors, failed = seam(metrics, "job_figures")(now)
    return last_ok, errors, failed


@pytest.fixture
def log_root(monkeypatch, tmp_path) -> Path:
    return use_data_dir(monkeypatch, tmp_path)


def test_the_24_hour_window_takes_23h59_and_leaves_24h01(metrics, log_root):
    """CM-030: an entry 23 h 59 old is in the window, one 24 h 01 old is not: for the errors of the two price jobs and for
    the failures of any job."""
    entries = [
        entry("current_price", "error", NOW - timedelta(hours=23, minutes=59), err=3),
        entry("current_price", "error", NOW - timedelta(hours=24, minutes=1), err=100),
        entry("history_sync", "error", NOW - timedelta(hours=23, minutes=59), err=5),
        entry("history_sync", "error", NOW - timedelta(hours=24, minutes=1), err=1000),
        entry("fx_sync", "error", NOW - timedelta(hours=23, minutes=59), err=7),
        entry("fx_sync", "error", NOW - timedelta(hours=24, minutes=1), err=7),
    ]

    _, errors, failed = figures(metrics, log_root, entries)

    assert failed == 3, f"three error entries 23 h 59 old (current_price, history_sync, fx_sync), none of the 24 h 01 old: {failed}"
    assert errors >= 3, f"the 23 h 59 old current_price error counts: {errors}"
    assert errors < 100, f"nothing 24 h 01 old counts: {errors}"


def test_only_the_two_price_jobs_feed_the_errors_and_any_job_feeds_the_failures(metrics, log_root):
    """CM-031: ``summary.err`` is summed over ``current_price`` entries of the window whatever their status (ok, partial,
    error); another job's ``err`` is not a price refresh error; ``jobs_failed_24h`` counts status ``error`` of any job,
    and only that."""
    entries = [
        entry("current_price", "ok", NOW - timedelta(hours=2), err=2),
        entry("current_price", "partial", NOW - timedelta(hours=3), err=1),
        entry("current_price", "error", NOW - timedelta(hours=4), err=4),
        entry("fx_sync", "error", NOW - timedelta(hours=5), err=9),
        entry("fx_sync", "partial", NOW - timedelta(hours=6), err=11),
        entry("other_job", "error", NOW - timedelta(hours=7), err=13),
        entry("other_job", "ok", NOW - timedelta(hours=8), err=17),
    ]

    _, errors, failed = figures(metrics, log_root, entries)

    assert errors == 2 + 1 + 4, f"only current_price's err counts (2 + 1 + 4): {errors}"
    assert failed == 3, f"the three entries with status error, of any job: {failed}"


def test_history_sync_errors_are_its_assets_and_fx_errors_PENDING_DECISION(metrics, log_root):
    """CM-032 (DECISION OF THE CALLER NEEDED, see the report): ``build_history_sync_entry`` writes no ``summary.err``, it
    writes ``assets_err`` and ``fx_err``. The brief says «sum of ``summary.err`` over the entries of those two jobs», which
    read literally makes history_sync contribute 0 forever. This case pins the useful reading, ``assets_err + fx_err``
    (2 + 1 = 3); if the decision is «0», delete this case and pin 0 here instead. It stands apart so it fails alone."""
    entries = [entry("history_sync", "partial", NOW - timedelta(hours=2), assets_ok=4, assets_err=2, assets_deferred=0, fx_ok=1, fx_err=1, fx_deferred=0)]

    _, errors, _ = figures(metrics, log_root, entries)

    assert errors == 3, f"history_sync's errors are assets_err + fx_err (3): {errors}"


def test_the_last_ok_is_the_newest_ok_of_a_price_job_whatever_its_age_and_never_partial_or_error(metrics, log_root):
    """CM-033: ``price_refresh_last_ok_at`` is the ``ts`` of the newest ``ok`` entry of ``current_price`` or
    ``history_sync``, of any age (10 days here); a newer ``partial`` or ``error`` of the same jobs, and a newer ``ok`` of
    another job, do not replace it."""
    expected = NOW - timedelta(days=10)
    entries = [
        entry("current_price", "ok", NOW - timedelta(days=30), ok=1, err=0),
        entry("current_price", "ok", expected, ok=1, err=0),
        entry("current_price", "partial", NOW - timedelta(days=9), ok=1, err=1),
        entry("history_sync", "error", NOW - timedelta(days=2), assets_err=3),
        entry("fx_sync", "ok", NOW - timedelta(hours=1), ok=1, err=0),
    ]

    last_ok, _, _ = figures(metrics, log_root, entries)

    assert last_ok == expected, f"the last ok is the 10 day old current_price ok: {last_ok}"


def test_the_last_ok_picks_the_newer_of_the_two_price_jobs_and_the_newest_by_ts_not_by_position(metrics, log_root):
    """CM-034: the newest of the two jobs together wins (history_sync, 2 h ago, beats current_price, 5 h ago), and
    «newest» is by ``ts``: an older entry written LAST in the file does not win."""
    newest = NOW - timedelta(hours=2)
    entries = [
        entry("history_sync", "ok", newest, assets_ok=3, assets_err=0, fx_ok=1, fx_err=0),
        entry("current_price", "ok", NOW - timedelta(hours=5), ok=3, err=0),
        entry("current_price", "ok", NOW - timedelta(hours=9), ok=3, err=0),
    ]

    last_ok, _, _ = figures(metrics, log_root, entries)

    assert last_ok == newest, f"the newest ok by ts, wherever it sits in the file: {last_ok}"


def test_partial_and_error_alone_leave_the_last_ok_null(metrics, log_root):
    """CM-035: with only ``partial`` and ``error`` entries of the price jobs there is no last ok: ``None``, while the
    errors and failures still count."""
    entries = [entry("current_price", "partial", NOW - timedelta(hours=2), ok=1, err=1), entry("current_price", "error", NOW - timedelta(hours=3), ok=0, err=2)]

    last_ok, errors, failed = figures(metrics, log_root, entries)

    assert (last_ok, errors, failed) == (None, 3, 1)


def test_no_log_and_an_empty_log_are_none_zero_zero(metrics, log_root):
    """CM-036: no job log at all, then an empty one: ``(None, 0, 0)``: nothing ran is a figure, not a failed measure."""
    assert not log_root.joinpath(*JOB_LOG).exists(), "Barrier: no log file"
    assert seam(metrics, "job_figures")(NOW) == (None, 0, 0), "no log file"
    assert figures(metrics, log_root, []) == (None, 0, 0), "an empty log"


def test_the_window_reads_the_instant_whatever_the_offset_of_the_entry(metrics, log_root):
    """CM-037: the scheduler writes ``ts`` with the offset of the machine. 23 h 59 old written at +05:00 is in the window,
    24 h 01 old written at -08:00 is not, and the last ok is the same instant whatever the offset."""
    inside = NOW - timedelta(hours=23, minutes=59)
    outside = NOW - timedelta(hours=24, minutes=1)
    ok_at = NOW - timedelta(hours=3)
    entries = [
        entry("current_price", "error", inside.astimezone(timezone_of(5)), err=3),
        entry("current_price", "error", outside.astimezone(timezone_of(-8)), err=100),
        entry("current_price", "ok", ok_at.astimezone(timezone_of(2)), ok=1, err=0),
    ]
    assert entries[0]["ts"].endswith("+05:00") and entries[1]["ts"].endswith("-08:00"), "Barrier: the entries carry their offsets"

    last_ok, errors, failed = figures(metrics, log_root, entries)

    assert (last_ok, errors, failed) == (ok_at, 3, 1), f"the instants, not the wall clocks: {(last_ok, errors, failed)}"


def timezone_of(hours: int) -> Any:
    from datetime import timezone  # noqa: PLC0415

    return timezone(timedelta(hours=hours))


def test_a_damaged_log_costs_the_damaged_lines_only_not_the_measure(metrics, log_root):
    """CM-038: a line that is not JSON, an entry without ``ts``, one whose ``ts`` is not a date, a ``summary`` that is null
    or whose ``err`` is not a number: each is skipped (or counts 0), and the figures of the good entries stand: the
    measure does not fail (null) because of a bad line."""
    good = NOW - timedelta(hours=2)
    entries: list[Any] = [
        "this line is not json {",
        {"job": "current_price", "status": "error", "summary": {"err": 50}},
        {"ts": "yesterday evening", "job": "current_price", "status": "error", "summary": {"err": 60}},
        entry("current_price", "partial", NOW - timedelta(hours=3), ok=1, err=1),
        {"ts": (NOW - timedelta(hours=4)).isoformat(), "job": "current_price", "status": "error", "summary": None},
        {"ts": (NOW - timedelta(hours=5)).isoformat(), "job": "current_price", "status": "error", "summary": {"err": "many"}},
        entry("current_price", "ok", good, ok=2, err=2),
    ]

    last_ok, errors, failed = figures(metrics, log_root, entries)

    assert last_ok == good, f"the good ok: {last_ok}"
    assert errors == 1 + 2, f"the good entries' err (1 + 2), the damaged ones 0: {errors}"
    assert failed == 2, f"the two dated error entries (the undated ones are skipped): {failed}"


# =============================================================================
# CM-040..045: the Security tab's checks
# =============================================================================


async def expected_warnings(session: AsyncSession) -> list[dict[str, str]]:
    """What the Security tab shows as not ok, in its order, from the real checks (``api/v1/security.py``)."""
    from backend.app.services.platform.config_audit import run_config_checks  # noqa: PLC0415
    from backend.app.services.platform.instance_key_check import check_instance_key  # noqa: PLC0415
    from backend.app.services.platform.plugin_secrets_check import check_plugin_secrets  # noqa: PLC0415

    checks = [*run_config_checks(), await check_plugin_secrets(session), await check_instance_key(session)]
    return [{"check_id": check.check_id, "severity": check.severity} for check in checks if check.severity != "ok"]


@pytest.mark.asyncio
async def test_the_warnings_are_every_check_that_is_not_ok_in_the_order_of_the_security_tab(metrics, empty_db, monkeypatch, tmp_path):
    """CM-040: ``config_warnings`` lists the checks of ``run_config_checks()``, then the plugin secrets, then the instance
    key, those whose severity is not ``ok``, in that order, as ``{check_id, severity}``. Here a short JWT secret (a
    warning), stored plugin secrets the key cannot read and an instance key mismatch (two errors from the database
    checks): the last two come last, in that order."""
    from backend.app.services.platform import instance_key_check, plugin_secrets_check  # noqa: PLC0415

    use_data_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("JWT_SECRET", JWT_CANARY)
    # An instance key from the environment: the plugin secrets are only checked where a key exists (CM-043..045)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", INSTANCE_KEY_CANARY)

    async def unreadable_secrets(_session: Any) -> Any:
        return collections.namedtuple("Status", "system")(2)

    async def mismatch(_session: Any) -> str:
        return "mismatch"

    monkeypatch.setattr(plugin_secrets_check, "plugin_secrets_key_status", unreadable_secrets)
    monkeypatch.setattr(instance_key_check, "instance_key_state", mismatch)
    expected = await expected_warnings(empty_db)
    assert {"check_id": "platform.jwt_secret", "severity": "warning"} in expected, f"Barrier: the short JWT secret is a warning of the tab: {expected}"
    assert [item["check_id"] for item in expected[-2:]] == [plugin_secrets_check.CHECK_ID, instance_key_check.CHECK_ID], f"Barrier: the database checks come last: {expected}"

    got = await seam(metrics, "config_warnings")(empty_db)

    assert [dict(item) if isinstance(item, dict) else item.model_dump() for item in got] == expected, f"the tab's warnings, in its order, nothing else:\n  expected {expected}\n  got      {got}"


@pytest.mark.asyncio
async def test_an_info_check_is_listed_and_an_ok_one_is_not(metrics, empty_db, monkeypatch, tmp_path):
    """CM-041: everything that is not ``ok`` is listed, ``info`` included (an unset JWT secret is an info: a new key at each
    start), and no listed severity is ``ok``."""
    use_data_dir(monkeypatch, tmp_path)

    got = [dict(item) if isinstance(item, dict) else item.model_dump() for item in await seam(metrics, "config_warnings")(empty_db)]

    assert {"check_id": "platform.jwt_secret", "severity": "info"} in got, f"an unset JWT secret is listed as info: {got}"
    assert [item for item in got if item["severity"] == "ok"] == [], f"no ok check is listed: {got}"
    assert got == await expected_warnings(empty_db), "and exactly the tab's"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["short-secret", "unreadable-file"])
async def test_a_warning_never_carries_its_detail_or_a_value(metrics, world, monkeypatch, case):
    """CM-042 (privacy): checks with a detail (a short secret: source, length, minimum; a secret file that cannot be read:
    the reason, with its path) reach the panel as ``{check_id, severity}`` alone. The JSON holds no ``detail``, no
    ``i18n_key``, no message key, no parameter name, no secret and no path."""
    if case == "short-secret":
        monkeypatch.setenv("JWT_SECRET", JWT_CANARY)
    else:
        monkeypatch.setenv("JWT_SECRET_FILE", str(world.root / KEY_FILE_CANARY))

    response = await seam(metrics, "collect_panel_metrics")(world.session)

    items = warnings_of(response)
    ours = [item for item in items if item["check_id"] == "platform.jwt_secret"]
    assert ours and ours[0]["severity"] in ("warning", "error"), f"Barrier: the check with a detail is listed: {items}"
    assert all(set(item) == {"check_id", "severity"} for item in items), f"every item has exactly two keys: {items}"
    shown = response.model_dump_json()
    leaked = [word for word in ("detail", "i18n", "instance.checks", "minimum", "length", "reason", "source", "JWT_SECRET", JWT_CANARY, KEY_FILE_CANARY, str(world.root)) if word in shown]
    assert leaked == [], f"the answer shows {leaked}: {shown}"


def stored_secret(key_id: str = "0" * 32) -> PluginSystemSetting:
    """A plugin secret as the settings store it: a ciphertext and the id of the key that encrypted it (not the instance's)."""
    return PluginSystemSetting(family="asset", plugin_code="lab", field_key="api_key", secret_ciphertext=b"clm1canary-ciphertext", key_id=key_id)


async def a_world_with_a_stored_secret_and_no_key(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The state in which the read-only route used to create ``secrets/instance.key``: a stored plugin secret, no key from
    the environment, no key file. Returns where the key file would be."""
    from backend.app.services.platform.instance_key import instance_key_path, instance_key_status  # noqa: PLC0415

    use_data_dir(monkeypatch, tmp_path)
    session.add(stored_secret())
    await session.commit()
    path = instance_key_path()
    assert path.parent.parent == get_data_dir(), f"Barrier: the key file belongs to this test's data directory: {path}"
    assert not path.exists() and not path.parent.exists(), "Barrier: no key file (nor its folder) yet"
    assert instance_key_status().source == "not_created", "Barrier: the instance has no key yet"
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_point", ["config_warnings", "collect_panel_metrics"])
async def test_the_figures_never_create_the_instance_key_file(metrics, empty_db, monkeypatch, tmp_path, entry_point):
    """CM-043 (the route is read-only): a stored plugin secret, no key from the environment and no key file. Measuring the
    configuration used to read the key to count the secrets it cannot read, and reading it generates it
    (``plugin_secrets_key_status`` -> ``settings_subkey`` -> ``derive_key`` -> ``_instance_key`` -> ``_create_key_file``): a
    GET made a file. It must leave no ``secrets/instance.key``, and not even its folder."""
    path = await a_world_with_a_stored_secret_and_no_key(empty_db, monkeypatch, tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", FakeDisk())

    with capture_logs():
        await seam(metrics, entry_point)(empty_db)

    assert not path.exists(), f"{entry_point} created the instance key file {path}: the panel's figures are a read, they generate nothing"
    assert not path.parent.exists(), f"{entry_point} created the folder of the key file: {path.parent}"


@pytest.mark.asyncio
async def test_without_an_instance_key_the_plugin_secrets_are_not_checked_but_the_key_check_still_is(metrics, empty_db, monkeypatch, tmp_path):
    """CM-044 (spy): with ``instance_key_status().source == "not_created"`` and a stored secret, ``config_warnings`` does not
    call ``check_plugin_secrets`` (the call that reads the key) and does not reach ``_create_key_file``, and it still calls
    ``check_instance_key`` (which stops earlier on ``not_created``: it is ``ok`` and generates nothing)."""
    from backend.app.services.platform import instance_key  # noqa: PLC0415

    await a_world_with_a_stored_secret_and_no_key(empty_db, monkeypatch, tmp_path)
    calls: list[str] = []
    real_check_instance_key = metrics.check_instance_key

    async def plugin_secrets_spy(_session: Any) -> Any:
        calls.append("check_plugin_secrets")
        pytest.fail("check_plugin_secrets was called while the instance has no key: it reads the key, and reading generates it")

    async def instance_key_spy(session: Any) -> Any:
        calls.append("check_instance_key")
        return await real_check_instance_key(session)

    def create_spy(_path: Path) -> None:
        calls.append("_create_key_file")
        raise AssertionError("the instance key file was generated by a read")

    monkeypatch.setattr(metrics, "check_plugin_secrets", plugin_secrets_spy)
    monkeypatch.setattr(metrics, "check_instance_key", instance_key_spy)
    monkeypatch.setattr(instance_key, "_create_key_file", create_spy)

    got = await seam(metrics, "config_warnings")(empty_db)

    assert calls == ["check_instance_key"], f"only the instance key check runs, once: {calls}"
    assert "platform.plugin_secrets" not in [item.check_id for item in got], f"the plugin secrets check did not run: {got}"


@pytest.mark.asyncio
async def test_with_an_instance_key_the_plugin_secrets_are_still_checked(metrics, empty_db, monkeypatch, tmp_path):
    """CM-045 (the other half of CM-043/044, must not be lost by the fix): with a key from the environment, a stored secret
    written under another key is still listed by ``config_warnings`` as the ``platform.plugin_secrets`` error."""
    use_data_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", INSTANCE_KEY_CANARY)
    empty_db.add(stored_secret())
    await empty_db.commit()

    got = [dict(item) if isinstance(item, dict) else item.model_dump() for item in await seam(metrics, "config_warnings")(empty_db)]

    assert {"check_id": "platform.plugin_secrets", "severity": "error"} in got, f"a secret the key cannot read is listed: {got}"


# =============================================================================
# CM-050..053: each measure fails alone
# =============================================================================


def raising(name: str) -> Callable[..., Any]:
    """A stand-in for the measure ``name`` that raises, async when the measure is."""
    if name in ASYNC_SEAMS:

        async def async_boom(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError(f"boom-{name}")

        return async_boom

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"boom-{name}")

    return boom


@pytest.mark.asyncio
@pytest.mark.parametrize("name", SEAM_CASES)
async def test_a_measure_that_raises_nulls_its_keys_alone_and_is_logged_once(metrics, world, monkeypatch, name):
    """CM-050: each measure patched to raise in turn: the answer still comes (no exception), the keys of that measure are
    ``null``, every other key equals what it was without the failure, and the failure is logged once, a warning or an
    error with its traceback (``exc_info``) and the name of a key it owns."""
    collect = seam(metrics, "collect_panel_metrics")
    baseline = keys_of(await collect(world.session))
    assert [key for key in SEAMS[name] if baseline[key] is None] == [], f"Barrier: without the failure the keys of {name} hold a figure: {baseline}"
    seam(metrics, name)
    monkeypatch.setattr(metrics, name, raising(name))

    with capture_logs() as events:
        failed = keys_of(await collect(world.session))

    assert set(failed) == ANSWER_KEYS, f"all 15 keys are still there: {sorted(set(failed) ^ ANSWER_KEYS)}"
    assert [key for key in SEAMS[name] if failed[key] is not None] == [], f"the keys of {name} are null: {failed}"
    others = {key: value for key, value in failed.items() if key not in SEAMS[name]}
    assert others == {key: baseline[key] for key in others}, f"only the keys of {name} change:\n  expected {baseline}\n  got      {failed}"
    traced = [event for event in events if event.get("exc_info") and event.get("log_level") in ("warning", "error")]
    assert len(traced) == 1, f"the failure is logged once, with its traceback: {events}"
    assert any(key in repr(traced[0]) for key in SEAMS[name]), f"the line names the key it lost ({', '.join(SEAMS[name])}): {traced[0]}"


@pytest.mark.asyncio
async def test_every_measure_failing_together_is_an_answer_of_15_keys_with_the_constant_nulls(metrics, world, monkeypatch):
    """CM-051: all eight measures raise: 200-shaped, 15 keys, every one null."""
    for name in SEAMS:
        seam(metrics, name)
        monkeypatch.setattr(metrics, name, raising(name))

    with capture_logs():
        failed = keys_of(await seam(metrics, "collect_panel_metrics")(world.session))

    assert failed == dict.fromkeys(ANSWER_KEYS), f"everything failed, everything null: {failed}"


def bad_sql(_name: str) -> Callable[..., Any]:
    async def run(session: AsyncSession, *_args: Any, **_kwargs: Any) -> Any:
        await session.execute(text("SELECT * FROM a_table_that_does_not_exist_clm1"))

    return run


def failed_flush(_name: str) -> Callable[..., Any]:
    """Leaves the session in need of a rollback: a flush that violates a unique constraint (a second broker with a name
    the world already holds)."""

    async def run(session: AsyncSession, *_args: Any, **_kwargs: Any) -> Any:
        session.add(Broker(name=BROKER_NAMES[0]))
        await session.flush()

    return run


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [pytest.param(bad_sql, id="operational-error"), pytest.param(failed_flush, id="failed-flush-needs-rollback")])
@pytest.mark.parametrize("name", [pytest.param("table_counts", id="table_counts"), pytest.param("providers_in_use", id="providers_in_use"), pytest.param("config_warnings", id="config_warnings")])
async def test_a_database_measure_that_fails_does_not_poison_the_session_for_the_next(metrics, world, monkeypatch, name, failure):
    """CM-052: a database measure that really fails on the shared session (an ``OperationalError`` from a missing table;
    and a failed flush, which leaves the session needing a rollback) nulls its own keys; the measures that read the
    session after it still answer their real figures, because the failure is rolled back where it is caught."""
    collect = seam(metrics, "collect_panel_metrics")
    baseline = keys_of(await collect(world.session))
    seam(metrics, name)
    monkeypatch.setattr(metrics, name, failure(name))
    with pytest.raises(OperationalError):
        await bad_sql(name)(world.session)  # Barrier: that SQL does fail for real

    with capture_logs():
        failed = keys_of(await collect(world.session))

    assert [key for key in SEAMS[name] if failed[key] is not None] == [], f"the keys of {name} are null: {failed}"
    others = {key: value for key, value in failed.items() if key not in SEAMS[name]}
    assert others == {key: baseline[key] for key in others}, f"the failure of {name} must not null or change another key (a poisoned session):\n  expected {baseline}\n  got      {failed}"
    assert (await world.session.execute(text("SELECT count(*) FROM brokers"))).scalar_one() == BROKERS, "the session is usable after the answer, and the failed flush wrote nothing"

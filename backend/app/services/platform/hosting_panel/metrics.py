"""The figures the hosting panel reads of an instance (lot CL-M1, ``GET /api/v1/panel/metrics``).

Owner: workstream H (platform). Read-only and cheap: sizes, counts and the scheduler's job log, never who or what the
instance holds (no email, no name, no path, no secret, no detail of a check).

``collect_panel_metrics`` runs the measures one by one and never lets one fail the others: a measure that raises is
logged once, with its traceback and the keys it owns, and those keys are ``null``; a database measure that failed also
rolls the session back, so the next one reads a usable session. The measures are public so that a test can replace each.
"""

import asyncio
import os
import shutil
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_data_dir
from backend.app.db.models import Asset, AssetProviderAssignment, Broker, Transaction
from backend.app.logging_config import get_logger
from backend.app.schemas.hosting_panel import PanelConfigWarning, PanelMetricsResponse
from backend.app.services.platform.config_audit import run_config_checks
from backend.app.services.platform.instance_key import instance_key_status
from backend.app.services.platform.instance_key_check import check_instance_key
from backend.app.services.platform.plugin_secrets_check import check_plugin_secrets
from backend.app.services.platform.scheduler import joblog

logger = get_logger(__name__)

MIB = 1024 * 1024
#: The window of the figures drawn from the job log.
WINDOW = timedelta(hours=24)
#: The scheduler jobs that refresh prices.
PRICE_JOBS = ("current_price", "history_sync")

#: When this server process started: the moment this module was first imported, at the app's start.
_STARTED_AT = datetime.now(UTC)


def _mib(size: float) -> float:
    return round(size / MIB, 1)


def process_started_at() -> datetime:
    """When this server process started, in UTC."""
    return _STARTED_AT


def storage_usage_mb() -> tuple[float, float]:
    """Used and total space, in MiB, of the filesystem that holds the data directory."""
    usage = shutil.disk_usage(get_data_dir())
    return _mib(usage.used), _mib(usage.total)


def database_size_mb() -> float:
    """The SQLite file with its write-ahead log, in MiB; a database file that cannot be read raises."""
    database = get_data_dir() / "sqlite" / "app.db"
    size = database.stat().st_size
    wal = database.with_name(database.name + "-wal")
    if wal.exists():
        size += wal.stat().st_size
    return _mib(size)


def uploads_size_mb() -> float:
    """The files of ``custom-uploads``, recursive, in MiB: a symbolic link, to a file or a folder, is never followed.

    No folder yet, or a folder that is itself a link, is 0.0; a file that vanishes during the walk counts nothing.
    """
    root: Path = get_data_dir() / "custom-uploads"
    if root.is_symlink():
        return 0.0
    total = 0
    for folder, _dirs, files in os.walk(root, followlinks=False):
        for name in files:
            path = os.path.join(folder, name)
            try:
                if not os.path.islink(path):
                    total += os.lstat(path).st_size
            except OSError:  # deleted or unreadable between the listing and the stat: only this file costs
                continue
    return _mib(total)


async def config_warnings(session: AsyncSession) -> list[PanelConfigWarning]:
    """The checks of the Security tab that are not ``ok``, in its order (``api/v1/security.py`` assembles them the same way).

    Read-only by contract: with no instance key yet, the stored plugin secrets are not asked — reading them derives the
    key, and deriving it creates the key file (a restore stopped half way has the secrets and no key: a panel call
    must not invent one). The key check itself stops earlier on that state, as ``_file_verdict`` does.
    """
    checks = await asyncio.to_thread(run_config_checks)
    if (await asyncio.to_thread(instance_key_status)).source != "not_created":
        checks = [*checks, await check_plugin_secrets(session)]
    checks = [*checks, await check_instance_key(session)]
    return [PanelConfigWarning(check_id=check.check_id, severity=check.severity) for check in checks if check.severity != "ok"]


def _instant(value: Any) -> datetime | None:
    """A job-log ``ts`` as an aware instant; None for anything else (a damaged line costs only itself)."""
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value)
    except ValueError:
        return None
    return when if when.tzinfo is not None else when.replace(tzinfo=UTC)


def _count(summary: Any, *names: str) -> int:
    """The sum of the integer counts ``names`` of a job's summary; what is not a count adds nothing."""
    if not isinstance(summary, dict):
        return 0
    return sum(summary[name] for name in names if isinstance(summary.get(name), int) and not isinstance(summary.get(name), bool) and summary[name] > 0)


def job_figures(now: datetime) -> tuple[datetime | None, int, int]:
    """From the job log: when a price refresh last ended ok, the failed items of the price refreshes and the failed runs of any job in the last 24 hours.

    The log keeps the last ``MAX_ENTRIES`` entries only: the 24 hours can reach back less. ``current_price`` counts its
    ``err``; ``history_sync`` its failed assets and rates (``assets_err`` and ``fx_err``).
    """
    since = now - WINDOW
    last_ok: datetime | None = None
    errors = 0
    failed = 0
    for item in joblog.read_entries():
        when = _instant(item.get("ts"))
        if when is None:
            continue
        job, status = item.get("job"), item.get("status")
        if job in PRICE_JOBS and status == "ok" and (last_ok is None or when > last_ok):
            last_ok = when
        if when < since:
            continue
        if status == "error":
            failed += 1
        if job == "current_price":
            errors += _count(item.get("summary"), "err")
        elif job == "history_sync":
            errors += _count(item.get("summary"), "assets_err", "fx_err")
    return last_ok, errors, failed


async def table_counts(session: AsyncSession) -> tuple[int, int, int]:
    """How many brokers, transactions and assets the database holds."""
    counts = []
    for model in (Broker, Transaction, Asset):
        counts.append((await session.execute(select(func.count()).select_from(model))).scalar_one())
    return counts[0], counts[1], counts[2]


async def providers_in_use(session: AsyncSession) -> list[str]:
    """The sorted codes of the price providers some asset is assigned to."""
    rows = await session.execute(select(AssetProviderAssignment.provider_code).distinct().order_by(AssetProviderAssignment.provider_code))
    return [str(code) for code in rows.scalars()]


async def _measure(session: AsyncSession, keys: tuple[str, ...], run: Callable[[], Any], *, database: bool = False) -> Any:
    """One measure's answer, or ``None`` when it raises: logged once, with its traceback and the keys it owns.

    A database measure that failed leaves its transaction to be rolled back, so the session is usable for the next.
    """
    try:
        answer = run()
        return await answer if isinstance(answer, Awaitable) else answer
    except Exception as exc:  # noqa: BLE001 — isolation boundary: a figure that cannot be measured is null, never an error for the panel
        logger.warning("A figure of the panel metrics could not be measured: its keys are null", keys=list(keys), exc_info=exc)
        if database:
            await session.rollback()
        return None


async def collect_panel_metrics(session: AsyncSession) -> PanelMetricsResponse:
    """Every figure of ``GET /panel/metrics``; each measure on its own, so one that fails is ``null`` and the rest stand."""
    now = datetime.now(UTC)
    started = await _measure(session, ("started_at",), lambda: process_started_at())
    storage = await _measure(session, ("storage_used_mb", "storage_limit_mb"), lambda: asyncio.to_thread(storage_usage_mb))
    database_mb = await _measure(session, ("database_mb",), lambda: asyncio.to_thread(database_size_mb))
    uploads_mb = await _measure(session, ("uploads_mb",), lambda: asyncio.to_thread(uploads_size_mb))
    warnings = await _measure(session, ("config_warnings",), lambda: config_warnings(session), database=True)
    jobs = await _measure(session, ("price_refresh_last_ok_at", "price_refresh_errors_24h", "jobs_failed_24h"), lambda: asyncio.to_thread(job_figures, now))
    counts = await _measure(session, ("brokers_count", "transactions_count", "assets_count"), lambda: table_counts(session), database=True)
    providers = await _measure(session, ("plugins_enabled",), lambda: providers_in_use(session), database=True)
    return PanelMetricsResponse(
        started_at=started,
        storage_used_mb=storage[0] if storage else None,
        storage_limit_mb=storage[1] if storage else None,
        database_mb=database_mb,
        uploads_mb=uploads_mb,
        config_warnings=warnings,
        price_refresh_last_ok_at=jobs[0] if jobs else None,
        price_refresh_errors_24h=jobs[1] if jobs else None,
        jobs_failed_24h=jobs[2] if jobs else None,
        brokers_count=counts[0] if counts else None,
        transactions_count=counts[1] if counts else None,
        assets_count=counts[2] if counts else None,
        plugins_enabled=providers,
        market_data_credits_used=None,
        market_data_credits_limit=None,
    )

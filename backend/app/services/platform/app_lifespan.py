"""The app's startup and shutdown: its steps, in order, and the lifespan that runs them.

Owner: workstream H (platform). Moved out of ``main.py`` as it was (CP2b): the same steps in the same order. A
workstream adds a step with one line in ``STARTUP_STEPS`` or ``SHUTDOWN_STEPS``; ``lifecycle.py`` runs them, names the
one in progress and, under a deadline, limits each. Every step reaches its functions through their names in this
module when it runs, so a test replaces one with ``monkeypatch.setattr(app_lifespan, "<name>", ...)``.

Shutdown runs the tool executor's step in the lifespan's ``finally``, then the other steps: not the reverse of the
startup. ``shutdown_deadline()`` comes from the shutdown budget (``shutdown_budget.py``, workstream Z): it limits the
shutdown steps; the first startup step installs the watchdog that ends the process when the budget runs out after a
signal, and the last shutdown step terminates the child processes still alive.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import ensure_data_dirs, get_settings, is_test_mode
from backend.app.config.brim import BrimConfigError, brim_prewarm_enabled
from backend.app.config.platform import awaiting_restore
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.accounts.bootstrap_admin_service import startup_admin_bootstrap
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.assets.market_calendar import shutdown_market_holidays, start_market_holiday_prewarm
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.brim_parse_pool import prewarm as prewarm_brim_parse_pool
from backend.app.services.brim.brim_parse_pool import shutdown_pool as shutdown_brim_parse_pool
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.files.static_uploads import seed_default_avatars
from backend.app.services.financial_math.portfolio.engine import shutdown_engine_executor
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.config_audit import log_configuration_audit
from backend.app.services.platform.database_bootstrap import ensure_database_exists, run_post_migration_fixes_at_startup
from backend.app.services.platform.instance_backup.apply import apply_pending_restore, finish_pending_restore, hold_serving_lock
from backend.app.services.platform.instance_backup.leftovers import sweep_backup_leftovers
from backend.app.services.platform.lifecycle import Step, run_shutdown_steps, run_startup_steps
from backend.app.services.platform.plugin_secrets_check import log_plugin_secrets_check
from backend.app.services.platform.restore_guard import probe_restore_state, restore_interrupted
from backend.app.services.platform.scheduler import get_shutdown_event, scheduler_loop
from backend.app.services.platform.shutdown_budget import child_processes_step, install_shutdown_watchdog, shutdown_deadline
from backend.app.services.platform.sleep_wake.idle_monitor import start_idle_monitor, stop_idle_monitor
from backend.app.services.platform.stored_currencies import log_stored_currency_audit
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk.scenario_catalog import (
    initialize_risk_scenario_catalog,
)
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.runtime import validate_signal_runtime
from backend.app.services.tools.executor import shutdown_tool_executor
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.services.transactions.lone_transfer_legs import convert_lone_giving_legs_at_startup
from backend.app.utils.runtime.cache import close_all_caches
from backend.app.utils.runtime.version import get_git_version

logger = get_logger(__name__)
_background_tasks: set[asyncio.Task] = set()


@dataclass
class _SchedulerRun:
    """The scheduler's task and stop signal, from the startup step that starts it to the shutdown step that stops it."""

    shutdown_event: asyncio.Event | None = None
    task: asyncio.Task | None = None


_scheduler = _SchedulerRun()


# =============================================================================
# Startup
# =============================================================================


def _announce() -> None:
    git_version = get_git_version()
    logger.info(
        "Starting LibreFolio",
        version=git_version,
        database_url=get_settings().DATABASE_URL.split("///")[-1],  # Hide full path in logs
        test_mode=is_test_mode(),
    )


async def _check_configuration() -> None:
    # A configured secret that cannot be read stops the start; settings that weaken the instance are logged
    await asyncio.to_thread(log_configuration_audit)


def _load_signal_plugins() -> None:
    signal_runtime = validate_signal_runtime()
    SignalPluginRegistry.auto_discover()
    logger.info(
        "Signal plugin runtime ready",
        pandas_ta_classic_version=signal_runtime.pandas_ta_classic_version,
        talib_version=signal_runtime.talib_version,
        plugin_count=len(SignalPluginRegistry.list_plugin_codes()),
    )


async def _load_tool_catalog() -> None:
    tool_catalog = await asyncio.to_thread(ToolPluginRegistry.get_snapshot)
    logger.info("Tool catalog initialized", plugin_count=len(tool_catalog.definitions), quarantined_count=len(tool_catalog.failures))


async def _load_risk_scenarios() -> None:
    scenario_catalog = await initialize_risk_scenario_catalog()
    logger.info(
        "Risk scenario catalog ready",
        built_in_count=scenario_catalog.status.built_in_count,
        host_count=scenario_catalog.status.host_count,
        warning_count=scenario_catalog.status.warning_count,
    )


def _seed_avatars() -> None:
    # Seed default avatar images on first startup
    seeded = seed_default_avatars()
    if seeded > 0:
        logger.info(f"Seeded {seeded} default avatar(s) into static resources")


def _keep_in_background(task: asyncio.Task) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _start_provider_prewarm() -> None:
    # Pre-warm provider caches in background (non-blocking)
    _keep_in_background(asyncio.create_task(_prewarm_provider_caches()))


def _start_market_holiday_prewarm() -> None:
    # Build the market holiday table in its own process, in background: the first computation that needs it awaits it
    _keep_in_background(start_market_holiday_prewarm())


def _start_stored_currency_audit() -> None:
    # The audit of the stored currency codes (E-19a), in background (H's review): its scans take about 0.6 s at a million
    # price rows and 1.6 s at three, and it only reads and logs, never raises
    _keep_in_background(asyncio.create_task(asyncio.to_thread(log_stored_currency_audit)))


def _start_brim_parse_pool_prewarm() -> None:
    # Opt-in (LIBREFOLIO_BRIM_PREWARM, decision N56: off by default, on in test mode): start the BRIM parse pool's
    # forkserver with the BRIM module and its plugins preloaded, in a thread, in background: the first import of a
    # broker file then forks a ready worker instead of starting an interpreter (W-B53)
    try:
        enabled = brim_prewarm_enabled()
    except BrimConfigError as exc:
        logger.warning("BRIM parse pool prewarm off: invalid setting", variable=exc.variable, error=str(exc))
        return
    if enabled:
        _keep_in_background(asyncio.create_task(asyncio.to_thread(prewarm_brim_parse_pool)))


def _start_scheduler() -> None:
    # Start scheduler daemon
    _scheduler.shutdown_event = get_shutdown_event()
    _scheduler.task = asyncio.create_task(scheduler_loop(_scheduler.shutdown_event))


async def _initialize_global_settings():
    """Initialize global settings with default values if not present."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        created = await initialize_global_settings(session)
        if created > 0:
            logger.info(f"Initialized {created} global setting(s)")


async def _prewarm_provider_caches():
    """Pre-warm provider instances and their caches in background."""
    try:
        for provider_info in AssetProviderRegistry.list_providers():
            code = provider_info["code"]
            AssetProviderRegistry.get_provider_instance(code)
        logger.debug("Provider caches pre-warmed successfully")
    except Exception as e:
        logger.warning(f"Provider cache pre-warm failed (non-blocking): {e}")


# =============================================================================
# Shutdown — stop scheduler first, then cleanup providers
# =============================================================================


def _stop_scheduler() -> asyncio.Task | None:
    """Signal the scheduler to stop; its task is returned, for the runner to await."""
    if _scheduler.shutdown_event is not None:
        _scheduler.shutdown_event.set()
    return _scheduler.task


def _shutdown_providers() -> None:
    AssetProviderRegistry.shutdown_all_providers()
    FXProviderRegistry.shutdown_all_providers()
    BRIMProviderRegistry.shutdown_all_providers()


def _shutdown_brim_parse_pool() -> None:
    # wait=True: releasing the parse workers has to actually happen here. The
    # runner escalates to SIGKILL after a grace period, and a SIGKILL skips the
    # atexit handler that would otherwise join them — the workers then survive,
    # re-parented to init, holding the stdout they inherited. Nothing is running
    # at this point anyway: uvicorn has already drained in-flight requests, and
    # a parse only exists inside one.
    shutdown_brim_parse_pool(wait=True)


# =============================================================================
# The steps, in order
# =============================================================================


def _serving_no_data() -> bool:
    """The instance serves no data: it awaits its restore (H-62) or its restore stopped half way (B-33)."""
    return awaiting_restore() or restore_interrupted()


#: H-62: an instance awaiting its restore (``LIBREFOLIO_AWAIT_RESTORE``) skips the steps marked ``skip_when=_serving_no_data``:
#: no initial administrator nor ``/setup`` link (a backup brings its own), no scheduler nor background warm-ups on an
#: empty database. B-33: so does an instance whose restore state cannot be read, which also skips the repairs of the
#: data (``skip_when=restore_interrupted``). The database, the restore's own steps and the idle monitor still run.
STARTUP_STEPS: tuple[Step, ...] = (
    # First: from here on a SIGTERM or a SIGINT starts the shutdown budget (only under uvicorn's own signal handlers)
    Step("shutdown-watchdog", lambda: install_shutdown_watchdog()),
    Step("announce", lambda: _announce()),
    Step("configuration-checks", lambda: _check_configuration()),
    Step("signal-plugins", lambda: _load_signal_plugins()),
    Step("tool-catalog", lambda: _load_tool_catalog()),
    Step("pending-restore", lambda: asyncio.to_thread(apply_pending_restore)),
    # B-33: a state of the restore that cannot be read may hide a restore stopped half way: from here on this process
    # serves no data (restore_guard.py), and the steps that repair, write or warm up the data are skipped
    Step("restore-state", lambda: asyncio.to_thread(probe_restore_state)),
    # Ensure all data directories exist (prod or test based on mode)
    Step("data-directories", lambda: ensure_data_dirs()),
    # Before any step reads the data: from here on a restore never swaps or undoes under this process
    Step("serving-lock", lambda: asyncio.to_thread(hold_serving_lock)),
    Step("risk-scenarios", lambda: _load_risk_scenarios()),
    Step("default-avatars", lambda: _seed_avatars()),
    # Ensure database exists and is migrated
    Step("database", lambda: ensure_database_exists()),
    # Then the repairs that cannot be migrations, before anything else opens the database
    Step("post-migration-fixes", lambda: asyncio.to_thread(run_post_migration_fixes_at_startup), skip_when=restore_interrupted),
    # Then the lone giving TRANSFER legs older deletions left, at their Auto cost, which the fixes cannot compute (decision 47)
    Step("lone-transfer-legs", lambda: convert_lone_giving_legs_at_startup(), skip_when=restore_interrupted),
    # Initialize global settings with defaults (if not already present)
    Step("global-settings", lambda: _initialize_global_settings()),
    # The initial administrator of LIBREFOLIO_ADMIN_EMAIL (F02, workstream A), once the settings exist
    Step("admin-bootstrap", lambda: startup_admin_bootstrap(), skip_when=_serving_no_data),
    # The first start on restored data completed: commit the restore (B3), before any step reports on or serves the data.
    # A step before this one that raises rolls the restore back at the next start; one after it no longer does (N57).
    Step("restore-commit", lambda: asyncio.to_thread(finish_pending_restore)),
    # What runs killed outright left in clear: a check's decrypted archive, an inspect's folder, a backup's work files
    # (B-23, N66). Once the restore is settled; it never raises: after restore-commit, a step that raises stops every start
    Step("backup-leftovers", lambda: asyncio.to_thread(sweep_backup_leftovers)),
    # The stored plugin secrets the instance key can no longer read: an error in the log, with their count (H-15)
    Step("plugin-secrets-check", lambda: log_plugin_secrets_check()),
    # The audit of the stored currency codes, in background: one warning when some are not ISO 4217 codes (E-19a). After
    # both repairs and once the restore is settled, since it reports on the data (N57); read-only, never a stop or a wait
    Step("stored-currencies", lambda: _start_stored_currency_audit(), skip_when=_serving_no_data),
    Step("provider-prewarm", lambda: _start_provider_prewarm(), skip_when=_serving_no_data),
    Step("market-holidays", lambda: _start_market_holiday_prewarm(), skip_when=_serving_no_data),
    Step("brim-parse-pool", lambda: _start_brim_parse_pool_prewarm(), skip_when=_serving_no_data),
    Step("scheduler", lambda: _start_scheduler(), skip_when=_serving_no_data),
    Step("idle-monitor", lambda: start_idle_monitor()),
)

#: Run in the lifespan's ``finally``: also when serving ended with an error.
FINALLY_STEPS: tuple[Step, ...] = (Step("tool-executor", lambda: shutdown_tool_executor()),)

SHUTDOWN_STEPS: tuple[Step, ...] = (
    Step("idle-monitor", lambda: stop_idle_monitor()),
    Step("scheduler", lambda: _stop_scheduler()),
    Step("providers", lambda: _shutdown_providers()),
    Step("brim-parse-pool", lambda: _shutdown_brim_parse_pool(), blocking=True),
    Step("quant-pools", lambda: shutdown_quant_worker_pools()),
    # The portfolio replay's threads: a queued replay is cancelled, never waited for (MF-J45a)
    Step("portfolio-engine", lambda: shutdown_engine_executor()),
    # Never waits for a holiday build in progress: its process is ended at once
    Step("market-holidays", lambda: shutdown_market_holidays()),
    # Close all TTL caches (stop timer wheel threads for clean exit)
    Step("caches", lambda: close_all_caches()),
    # Last: the child processes still alive (parse, risk, tool workers) are terminated, so none outlives the server
    child_processes_step(),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    await run_startup_steps(STARTUP_STEPS)
    try:
        yield
    finally:
        deadline = shutdown_deadline()
        await run_shutdown_steps(FINALLY_STEPS, deadline)
    logger.info("Shutting down LibreFolio")
    await run_shutdown_steps(SHUTDOWN_STEPS, deadline)

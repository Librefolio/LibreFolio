"""Main scheduler loop — asyncio task embedded in FastAPI lifespan."""

import asyncio
import os
from datetime import datetime, timedelta

import structlog

from backend.app.services.scheduler.jobs import run_current_price_refresh, run_history_sync
from backend.app.services.scheduler.leader import am_i_leader
from backend.app.services.scheduler.settings import SchedulerSettings, load_scheduler_settings
from backend.app.services.scheduler.state import SchedulerState, load_state, save_state

logger = structlog.get_logger(__name__)

_shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event (singleton per process).

    Resets the event if it was previously set (e.g., after hot-reload).
    """
    global _shutdown_event
    if _shutdown_event is None or _shutdown_event.is_set():
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def due_current_price(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if current-price refresh is due."""
    last = state.current_price.last_run_at
    if last is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except (ValueError, TypeError):
        return True
    return (now - last_dt) >= timedelta(minutes=settings.current_price_frequency_minutes)


def due_history_sync(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if any history sync slot is due."""
    # 1. Is today a configured day?
    today_dow = now.strftime("%a").lower()[:3]
    if today_dow not in settings.history_sync_days:
        return False

    # 2. Check each configured time slot
    last = state.history_sync.last_run_at
    last_dt = None
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
        except (ValueError, TypeError):
            last_dt = None

    for slot_time in settings.history_sync_times:
        slot_dt = now.replace(
            hour=slot_time.hour, minute=slot_time.minute, second=0, microsecond=0
        )
        if now >= slot_dt:
            if last_dt is None or last_dt < slot_dt:
                return True
    return False


async def scheduler_loop(shutdown_event: asyncio.Event) -> None:
    """
    Main scheduler loop — runs as asyncio.Task on the FastAPI event loop.

    Every 60s:
    1. Check leader election (psutil, offloaded to thread)
    2. If leader: read settings, check due jobs, execute
    3. Save state after each job

    Disabled entirely when LIBREFOLIO_NO_SCHEDULER=1 is set (e.g. during
    gallery screenshot generation to prevent data changes mid-run).
    """
    if os.getenv("LIBREFOLIO_NO_SCHEDULER"):
        logger.info("Scheduler disabled via LIBREFOLIO_NO_SCHEDULER — loop not started")
        return

    logger.info("Scheduler loop started")

    # Initial delay to let the application fully initialize
    await asyncio.sleep(5)

    while not shutdown_event.is_set():
        try:
            is_leader = am_i_leader()

            if is_leader:
                settings = await load_scheduler_settings()

                if settings.scheduler_enabled:
                    state = load_state()
                    now = datetime.now().astimezone()

                    if due_current_price(now, settings, state):
                        await run_current_price_refresh(state)
                        save_state(state)

                    if due_history_sync(now, settings, state):
                        await run_history_sync(state, horizon_days=settings.history_sync_horizon_days)
                        save_state(state)

        except Exception as e:
            logger.exception("scheduler_loop tick failed", error=str(e))

        # Sleep 60s, but check shutdown every 5s for faster exit
        for _ in range(12):
            if shutdown_event.is_set():
                break
            await asyncio.sleep(5)

    logger.info("Scheduler loop stopped")

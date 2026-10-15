"""Market Data Scheduler — embedded daemon for automatic price/FX sync."""

from backend.app.services.platform.scheduler.joblog import read_entries as read_job_log
from backend.app.services.platform.scheduler.scheduler import get_shutdown_event, scheduler_loop

__all__ = ["get_shutdown_event", "read_job_log", "scheduler_loop"]

"""Schemas of sleep and wake (workstream Z, release 1.3): the answer of the scheduled wake-up.

``POST /api/v1/system/wake-sync`` (``api/v1/system/wake.py``) streams whitespace while the scheduler's jobs run, then
``WakeSyncResponse``. The list of jobs is generic, so a future job (notifications) is one more entry, and a field such
as the next wake-up can be added without breaking a caller.

``GET /api/v1/system/price-refresh`` (``api/v1/system/price_refresh.py``, lot Z5) answers ``PriceRefreshResponse``:
whether the prices are catching up now, for the web app's notice «Updating prices…».
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from backend.app.schemas.common import StrictModel


class WakeSyncJob(StrictModel):
    """How one scheduler job ended in a wake-up run."""

    name: str = Field(description="The job: `current_price` or `history_sync`")
    status: str = Field(description="`ok`, `partial`, `error`, or `not_due` when the job was not due")
    started_at: datetime | None = Field(default=None, description="When the job started, in UTC; null when not due")
    duration_s: float | None = Field(default=None, description="How long the job ran, in seconds; null when not due")
    items_ok: int = Field(default=0, description="Items brought up to date")
    items_err: int = Field(default=0, description="Items that failed")
    error: str | None = Field(default=None, description="What went wrong: the class of the error, never its message")
    items_deferred: int = Field(default=0, description="Items a provider's pause after too many requests deferred: neither ok nor failed")
    retry_at: datetime | None = Field(default=None, description="When the job runs again before its regular round, in UTC: the end of a provider's pause or of the wait after a failure; null when none")


class WakeSyncResponse(StrictModel):
    """The JSON that ends the answer of the scheduled wake-up, after the whitespace streamed while the jobs run."""

    status: str = Field(
        description="How the run ended: `ok`, `partial`, `error`, `disabled` (scheduler off), `not_leader` (another worker runs the jobs), `blocked` (instance blocked: no job runs), `awaiting_restore` (the hosting panel restores the instance: no job runs), `restore_interrupted` (the state of a restore cannot be read: no job runs) or `instance_key_mismatch` (the instance key is not the one the data was written with: no job runs)"
    )
    started_at: datetime = Field(description="When the run started, in UTC")
    finished_at: datetime = Field(description="When the run ended, in UTC")
    error: str | None = Field(default=None, description="The class of the error that stopped the run, never its message; null otherwise")
    jobs: list[WakeSyncJob] = Field(default_factory=list, description="Each job of the scheduler and how it ended, in the order they run")


class PriceRefreshResponse(StrictModel):
    """Whether the prices are catching up now (``GET /api/v1/system/price-refresh``)."""

    state: Literal["idle", "starting", "running"] = Field(description="`starting` from the moment a catch-up (startup, return after a silence, scheduled wake-up) is announced, `running` while one of its jobs runs, `idle` otherwise")
    reason: Literal["startup", "return", "wake"] | None = Field(default=None, description="Why the pending catch-up runs; null when idle")
    job: str | None = Field(default=None, description="The job running now (`current_price` or `history_sync`); only while `running`")
    since: datetime | None = Field(default=None, description="When the pending catch-up began, in UTC; null when idle")
    last_finished_at: datetime | None = Field(default=None, description="When the last catch-up that ran a job ended, in UTC; null before the first")
    last_refreshed: bool = Field(default=False, description="Whether that catch-up updated at least one item")

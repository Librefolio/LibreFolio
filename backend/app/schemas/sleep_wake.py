"""Schemas of sleep and wake (workstream Z, release 1.3): the answer of the scheduled wake-up.

``POST /api/v1/system/wake-sync`` (``api/v1/system/wake.py``) streams whitespace while the scheduler's jobs run, then
``WakeSyncResponse``. The list of jobs is generic, so a future job (notifications) is one more entry, and a field such
as the next wake-up can be added without breaking a caller.
"""

from datetime import datetime

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


class WakeSyncResponse(StrictModel):
    """The JSON that ends the answer of the scheduled wake-up, after the whitespace streamed while the jobs run."""

    status: str = Field(description="How the run ended: `ok`, `partial`, `error`, `disabled` (scheduler off), `not_leader` (another worker runs the jobs) or `blocked` (instance blocked: no job runs)")
    started_at: datetime = Field(description="When the run started, in UTC")
    finished_at: datetime = Field(description="When the run ended, in UTC")
    error: str | None = Field(default=None, description="The class of the error that stopped the run, never its message; null otherwise")
    jobs: list[WakeSyncJob] = Field(default_factory=list, description="Each job of the scheduler and how it ended, in the order they run")

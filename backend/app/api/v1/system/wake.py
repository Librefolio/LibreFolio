"""The scheduled wake-up (``POST /system/wake-sync``): run the scheduler's due jobs now, for a hosting panel or a cron.

Owner: workstream Z (sleep and wake, release 1.3; F07, decisions D-W1…D-W3 and 33). A hosting panel that wakes a
suspended machine, or a self-hosted cron, calls it to bring the prices and the exchange rates up to date without a
user: it runs ``run_due_jobs("wake")`` and answers how each job ended. ``LIBREFOLIO_WAKE_TOKEN`` (or its ``_FILE``,
``config/sleep_wake.py``) turns the route on, with the rules of the hosting panel's backup token: unset, it answers 404,
as a path that does not exist; the token travels only in ``Authorization: Bearer``, never in the URL, and is compared
in constant time; a missing or wrong one answers 401; one the server cannot use answers 503 and is logged.

One wake-up at a time in the process: another one meanwhile answers 409 ``wake_in_progress``. The run is a task of its
own: if the caller goes away, the jobs still end, and the next wake-up is accepted only then. The answer is streamed,
because a run can outlast the 60 seconds after which Fly's proxy closes a connection that carries no byte: a space at
once, one every ``WAKE_KEEPALIVE_SECONDS`` while the jobs run, then the JSON of ``WakeSyncResponse``, which the leading
whitespace leaves valid. Once the first space has left, the status is 200 whatever happens, and the body's ``status``
tells how the run ended: ``blocked`` on an instance its hosting provider blocked, where the route stays allowed
(``api/v1/instance_block.py``) and no job runs. A wake-up is never the user's presence (``sleep_wake/activity.py``).
"""

import asyncio
import hmac
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import SecretFileError
from backend.app.config.sleep_wake import WAKE_TOKEN_VARIABLE, SleepWakeConfigError, wake_token
from backend.app.logging_config import get_logger
from backend.app.schemas.sleep_wake import WakeSyncJob, WakeSyncResponse
from backend.app.services.platform.scheduler.scheduler import RunReport, run_due_jobs
from backend.app.services.platform.sleep_wake import idle_monitor

logger = get_logger(__name__)

wake_router = APIRouter()

#: Seconds between two spaces of the streamed answer, well under the 60 seconds after which Fly's proxy closes a
#: connection that carries no byte.
WAKE_KEEPALIVE_SECONDS = 15.0
KEEPALIVE = b" "

_bearer = HTTPBearer(auto_error=False, scheme_name="WakeToken", description="LIBREFOLIO_WAKE_TOKEN, sent as `Authorization: Bearer <token>`")

_RESPONSES: dict[int | str, dict] = {
    200: {"model": WakeSyncResponse, "description": "Streamed: whitespace while the jobs run, then this JSON; `status` tells how the run ended"},
    401: {"description": "No token, or not the token of this instance (code `wake_unauthorized`)"},
    404: {"description": "The scheduled wake-up is off: no `LIBREFOLIO_WAKE_TOKEN`"},
    409: {"description": "A wake-up is already running (code `wake_in_progress`)"},
    503: {"description": "The wake-up token of this instance cannot be used: its file is unreadable, or it is too short or not visible ASCII (code `wake_unavailable`)"},
}

_running: asyncio.Task[WakeSyncResponse] | None = None


def _refusal(status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message}, headers=headers)


def require_wake_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> None:
    """Let the request through only with the wake-up token: 404 when the route is off, 401 without the token."""
    try:
        expected = wake_token()
    except (SecretFileError, SleepWakeConfigError) as exc:
        logger.error("The wake-up token cannot be used: the scheduled wake-up refuses every request", variable=WAKE_TOKEN_VARIABLE, error=str(exc))
        raise _refusal(status.HTTP_503_SERVICE_UNAVAILABLE, "wake_unavailable", "The wake-up token of this instance cannot be used") from None
    if expected is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    presented = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8")):
        raise _refusal(status.HTTP_401_UNAUTHORIZED, "wake_unauthorized", "A valid wake-up token is required", headers={"WWW-Authenticate": "Bearer"})


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _response(report: RunReport) -> WakeSyncResponse:
    jobs = [
        WakeSyncJob(
            name=job.name,
            status=job.status,
            started_at=job.started_at,
            duration_s=job.duration_s,
            items_ok=job.items_ok,
            items_err=job.items_err,
            error=job.error,
            items_deferred=job.items_deferred,
            retry_at=job.retry_at,
        )
        for job in report.jobs
    ]
    return WakeSyncResponse(status=report.status, started_at=report.started_at, finished_at=report.finished_at, jobs=jobs)


async def _wake_run() -> WakeSyncResponse:
    """The run of one wake-up, to its end whatever happens to the request that asked for it."""
    started_at = _utc_now()
    try:
        result = _response(await run_due_jobs("wake"))
    except Exception as exc:
        logger.exception("Wake-up run failed")
        result = WakeSyncResponse(status="error", started_at=started_at, finished_at=_utc_now(), error=type(exc).__name__)
    logger.info("Wake-up run finished", status=result.status, jobs=[job.name for job in result.jobs if job.status != "not_due"])
    # With nobody around, the machine goes back to sleep at once (Z2b): the check comes when this request has ended.
    idle_monitor.request_idle_check(idle_monitor.WAKE_CHECK_DELAY_SECONDS)
    return result


def _in_progress() -> bool:
    """A wake-up of this event loop is still running (a task of a loop that is gone counts for nothing)."""
    return _running is not None and not _running.done() and _running.get_loop() is asyncio.get_running_loop()


async def _stream(run: asyncio.Task[WakeSyncResponse]) -> AsyncIterator[bytes]:
    yield KEEPALIVE
    while not run.done():
        done, _ = await asyncio.wait({run}, timeout=WAKE_KEEPALIVE_SECONDS)
        if not done:
            yield KEEPALIVE
    if run.cancelled():
        now = _utc_now()
        result = WakeSyncResponse(status="error", started_at=now, finished_at=now, error="CancelledError")
    else:
        result = run.result()
    yield result.model_dump_json().encode("utf-8")


@wake_router.post("/wake-sync", response_model=None, responses=_RESPONSES)
async def wake_sync(_token: Annotated[None, Depends(require_wake_token)]) -> StreamingResponse:
    """Run the scheduler's due jobs now, and stream how each one ended: whitespace while they run, then the JSON."""
    global _running
    if _in_progress():
        raise _refusal(status.HTTP_409_CONFLICT, "wake_in_progress", "A wake-up is already running")
    logger.info("Wake-up run started")
    _running = asyncio.create_task(_wake_run(), name="wake-sync")
    return StreamingResponse(_stream(_running), media_type="application/json", headers={"Cache-Control": "no-store"})

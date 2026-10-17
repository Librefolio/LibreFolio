"""``GET /system/price-refresh``: whether the prices are catching up now, for the notice «Updating prices…» (release 1.3,
workstream Z, lot Z5).

At startup, at the first request after a silence and at a scheduled wake-up, the scheduler runs the jobs that are due
in the background. While such a catch-up is about to run or runs, every ``/api/`` response carries
``X-LibreFolio-Price-Refresh`` (``ActivityMiddleware``); the web app then asks this route every few seconds, shows the
notice while a job runs, and refreshes the portfolio views when the catch-up has updated something.

Signed-in users only: any user may ask, since the answer tells nothing about anyone's data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.sleep_wake import PriceRefreshResponse
from backend.app.services.platform.scheduler.scheduler import price_refresh_progress

price_refresh_router = APIRouter()


@price_refresh_router.get("/price-refresh", response_model=PriceRefreshResponse)
def get_price_refresh(_current_user: Annotated[User, Depends(get_current_user)]) -> PriceRefreshResponse:
    """Whether a catch-up of the prices is about to run (``starting``) or runs a job (``running``), and how the last one
    that ran a job ended."""
    progress = price_refresh_progress()
    return PriceRefreshResponse(
        state=progress.state,
        reason=progress.reason,
        job=progress.job,
        since=progress.since,
        last_finished_at=progress.last_finished_at,
        last_refreshed=progress.last_refreshed,
    )

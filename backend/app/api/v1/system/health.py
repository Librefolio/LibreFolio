"""Health (``GET /system/health``) and the test runner's readiness probe (``GET /system/test-lane-health``)."""

import secrets
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from backend.app.config import TEST_LANE_HEADER, is_test_mode
from backend.app.config.platform import TEST_LANE_ID_MAX_LENGTH, TEST_LANE_ID_MIN_LENGTH, owning_test_lane_id
from backend.app.schemas.system import HealthCheckResponse

health_router = APIRouter()


@health_router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Status message with "ok" status
    """
    return {"status": "ok"}


@health_router.get(
    "/test-lane-health",
    response_model=HealthCheckResponse,
    include_in_schema=False,
)
def test_lane_health(
    token: Annotated[str, Query(min_length=TEST_LANE_ID_MIN_LENGTH, max_length=TEST_LANE_ID_MAX_LENGTH)],
) -> JSONResponse:
    """Confirm readiness only for the test process tree that owns this server."""
    expected = owning_test_lane_id()
    if not is_test_mode() or not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(
        content={"status": "ok"},
        headers={TEST_LANE_HEADER: expected},
    )

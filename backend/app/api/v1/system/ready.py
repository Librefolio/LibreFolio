"""Readiness (``GET /system/ready``): 200 when the database answers and its schema is at the head revision, 503 otherwise.

Public, for health checks and orchestrators (Docker, Uptime Kuma, a hosting panel): no session in the path, and a body
with one code per check.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session_generator
from backend.app.schemas.system import ReadinessResponse
from backend.app.services.platform.readiness import check_readiness

ready_router = APIRouter()


@ready_router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse, "description": "Not ready: a check is not ok"}},
)
async def get_readiness(session: Annotated[AsyncSession, Depends(get_session_generator)]) -> ReadinessResponse | JSONResponse:
    """Whether this instance can serve requests: the database answers and its schema is at the head revision."""
    readiness = await check_readiness(session)
    if readiness.status == "ready":
        return readiness
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=readiness.model_dump(mode="json"))

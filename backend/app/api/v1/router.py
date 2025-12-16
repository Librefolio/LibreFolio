"""
API v1 router.
Aggregates all v1 endpoints.
"""
from fastapi import APIRouter

from backend.app.api.v1 import fx, assets
from backend.app.api.v1.utilities import router as utilities_router
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Include sub-routers
router.include_router(fx.fx_router)
router.include_router(assets.asset_router)
router.include_router(utilities_router)


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status.

    Returns:
        dict: Status message
    """
    logger.info("Health check requested")
    return {"status": "ok"}

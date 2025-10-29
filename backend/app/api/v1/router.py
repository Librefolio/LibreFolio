"""
API v1 router.
Aggregates all v1 endpoints.
"""
from fastapi import APIRouter

from backend.app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


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


"""
API v1 router.
Aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from backend.app.api.v1 import (
    assets,
    auth,
    backup,
    brokers,
    fx,
    portfolio_api,
    settings,
    system,
    transactions,
    uploads,
    users,
)
from backend.app.api.v1.utilities import router as utilities_router
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Include sub-routers
router.include_router(auth.router)  # Auth first (no prefix, uses /auth)
router.include_router(settings.router)  # Settings
router.include_router(system.router)  # System info
router.include_router(uploads.router)  # File uploads
router.include_router(users.router)  # User search
router.include_router(fx.fx_router)
router.include_router(assets.asset_router)
router.include_router(transactions.tx_router)
router.include_router(brokers.broker_router)
router.include_router(backup.backup_router)
router.include_router(portfolio_api.portfolio_router)
router.include_router(utilities_router)

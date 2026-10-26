"""
API v1 router.
Aggregates all v1 endpoints.
"""

from fastapi import APIRouter, Depends

from backend.app.api.v1 import (
    address_probe_image,
    ai_export,
    assets,
    auth,
    backup,
    brokers,
    email,
    fx,
    panel,
    pdf_fonts,
    plugin_settings,
    portfolio_api,
    risk,
    security,
    settings,
    signals,
    system,
    tools,
    transactions,
    uploads,
    users,
)
from backend.app.api.v1.instance_block import refuse_when_awaiting_restore, refuse_when_blocked, refuse_when_restore_interrupted
from backend.app.api.v1.user_limit import refuse_when_over_limit
from backend.app.api.v1.utilities import router as utilities_router
from backend.app.logging_config import get_logger
from backend.app.services.platform.hosting_panel.access import HOSTING_PANEL_TAG

logger = get_logger(__name__)

# On a blocked instance, every route below answers 423 but those of instance_block.ALLOWED_WHEN_BLOCKED; while the instance
# awaits its restore (H-62), but those of instance_block.ALLOWED_WHEN_AWAITING_RESTORE; while its restore state cannot be
# read (B-33), but those of instance_block.ALLOWED_WHEN_RESTORE_INTERRUPTED; while the active accounts outnumber
# LIBREFOLIO_MAX_USERS (A5-7), but those of user_limit.ALLOWED_WHEN_OVER_LIMIT (and, for an administrator, its ADMIN list).
# The block is read first, this guard last
router = APIRouter(dependencies=[Depends(refuse_when_blocked), Depends(refuse_when_awaiting_restore), Depends(refuse_when_restore_interrupted), Depends(refuse_when_over_limit)])

# Include sub-routers
router.include_router(auth.router)  # Auth first (no prefix, uses /auth)
router.include_router(address_probe_image.router)  # The address probe as an image, /auth/address-probe.png (H-55 v2)
router.include_router(ai_export.router)
router.include_router(settings.router)  # Settings
router.include_router(plugin_settings.router)  # Plugin settings (/settings/plugins)
router.include_router(system.router)  # System info
router.include_router(uploads.router)  # File uploads
router.include_router(pdf_fonts.router)  # The PDF viewer's CJK fonts, fetched once and served by the instance (H-55)
router.include_router(users.router)  # User search
router.include_router(email.router)  # Email: state and test email (admin)
router.include_router(security.router)  # Security: the checks of the «Security» tab (admin)
router.include_router(fx.fx_router)
router.include_router(assets.asset_router)
router.include_router(transactions.tx_router)
router.include_router(brokers.broker_router)
router.include_router(backup.backup_router)
router.include_router(panel.panel_router, prefix="/panel", tags=[HOSTING_PANEL_TAG])  # Hosting panel: the setup status of the instance
router.include_router(portfolio_api.portfolio_router)
router.include_router(risk.router)
router.include_router(signals.signals_router)
router.include_router(tools.router)
router.include_router(utilities_router)

"""Market-data endpoints of one asset (``/assets/{asset_id}/market-data``): summary and wipe of what a currency change deletes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager

logger = get_logger(__name__)

market_data_router = APIRouter()


# ============================================================================
# MARKET-DATA WIPE (R3-3 Policy D)
# ============================================================================


@market_data_router.get("/{asset_id}/market-data/summary", tags=["FA CRUD"])
async def market_data_summary(
    asset_id: int,
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Return market-data counters for an asset (dry-run summary).

    Used by the currency-change confirm modal to show the user exactly
    what will be deleted / disconnected **before** they confirm. Same
    shape as the ``POST /market-data/wipe`` response but without side
    effects (``dry_run=true``).
    """
    try:
        return await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=asset_id, session=session, dry_run=True)
    except AssetSourceError as e:
        status = 404 if e.error_code == "ASSET_NOT_FOUND" else 400
        raise HTTPException(status_code=status, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error in market-data summary for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error while reading the asset's market data") from e



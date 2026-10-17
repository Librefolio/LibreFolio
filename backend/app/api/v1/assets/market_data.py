"""Market-data endpoints of one asset (``/assets/{asset_id}/market-data``): summary and wipe after a currency change."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@market_data_router.post("/{asset_id}/market-data/wipe", tags=["FA CRUD"])
async def wipe_market_data(
    asset_id: int,
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Wipe all market data (prices + events) and disconnect linked transactions.

    Part of the Policy D currency-change flow. After this returns 200 the
    caller should:

    1. ``PATCH /assets`` with the new currency (will now succeed — no
       residual market data blocks the change).
    2. Re-sync from the provider (optional) via
       ``POST /assets/prices/sync`` to repopulate the price history in the
       new currency.

    Response body matches the summary endpoint:
    ``{prices, events_manual, events_provider, linked_tx, oldest, newest,
    dry_run}`` (``dry_run`` is always ``false`` here). Transactions are
    **preserved** — only their ``asset_event_id`` FK is set to ``NULL``
    so they stop referencing the now-deleted events; the user is free to
    re-associate them manually after re-inserting replacement events.

    Refused, nothing written: 409 ``detail = {"error_code", "message",
    "params"}`` with ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`` (X-R48) when a
    SPLIT of the asset has linked incoming adjustments without a purchase cost:
    deleting it would make them acquisitions of unknown cost. ``params.splits``
    lists each such SPLIT by date (``event_id``, ``date``, ``transaction_ids`` —
    only those the caller can see — and ``hidden_transactions_count``).
    """
    try:
        return await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=asset_id, session=session, dry_run=False, current_user_id=_current_user.id)
    except AssetSourceError as e:
        if e.error_code == "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST":
            raise HTTPException(status_code=409, detail={"error_code": e.error_code, "message": e.message, "params": jsonable_encoder(e.details)}) from e
        status = 404 if e.error_code == "ASSET_NOT_FOUND" else 400
        raise HTTPException(status_code=status, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error in market-data wipe for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

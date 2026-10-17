"""Asset price endpoints (``/assets/prices``): manual upsert and delete, signal catalog, bulk and current queries, provider sync."""

from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import PERIOD_CHANGES_MAX_AS_OF_DAYS
from backend.app.schemas.prices import (
    PERIOD_CHANGES_MAX_ASSETS,
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkUpsertResponse,
    FACurrentPriceResponse,
    FAPeriodChangesQueryItem,
    FAPeriodChangesResponse,
    FAPriceQueryItem,
    FAPriceQueryResponse,
    FAUpsert,
    FAUpsertResult,
)
from backend.app.schemas.refresh import FABulkRefreshResponse, FARefreshItem
from backend.app.schemas.signals import (
    SignalCatalogResponse,
    SignalDomain,
)
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.period_changes import get_period_changes_bulk
from backend.app.services.signals.planning import SignalRequestValidationError
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.utils.date_range_limits import MAX_BULK_ITEMS, BulkTooManyDaysError, DateOutOfRangeError, bulk_too_many_days_detail, bulk_too_many_items_detail, date_out_of_range_detail

logger = get_logger(__name__)

price_router = APIRouter(prefix="/prices", tags=["FA Prices"])


# ============================================================================
# MANUAL PRICE MANAGEMENT ENDPOINTS
# ============================================================================


@price_router.post("", response_model=FABulkUpsertResponse)
async def upsert_prices_bulk(
    assets: List[FAUpsert],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk upsert prices manually (PRIMARY bulk endpoint).

    A date outside ``stored_date_bounds()`` (1900-01-01 to tomorrow) refuses the whole request with 422
    ``date_out_of_range``, before anything is written (X-R65, N83).
    """
    try:
        # Pass FAUpsert objects directly to service
        result = await AssetSourceManager.bulk_upsert_prices(assets, session)

        results_list = [FAUpsertResult(**r) for r in result["results"]]
        success_count = sum(1 for r in results_list if r.count > 0)

        return FABulkUpsertResponse(
            inserted_count=result["inserted_count"],
            updated_count=result["updated_count"],
            results=results_list,
            success_count=success_count,
        )
    except DateOutOfRangeError as e:
        raise HTTPException(status_code=422, detail=date_out_of_range_detail(e.items, e.count, e.earliest, e.latest)) from e
    except ValueError as e:
        # I.2 — currency mismatch (or other domain validation errors from the service)
        # surface as 400 Bad Request, with the structured message the service produced.
        logger.warning("Upsert prices validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error in bulk upsert prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@price_router.delete("", response_model=FABulkDeleteResponse)
async def delete_prices_bulk(
    assets: List[FAAssetDelete],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk delete price ranges (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_delete_prices(assets, session)
    except Exception as e:
        logger.exception(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# PRICE QUERY ENDPOINTS
# ============================================================================


# R3-3b: ``GET /assets/prices/{id}/export`` has been removed. Use the unified
# backup router instead:
#   GET /api/v1/backup/asset/{id}/prices?format=csv|json
#   GET /api/v1/backup/asset/{id}/events?format=csv|json
#   GET /api/v1/backup/fx/{base}/{quote}/rates?format=csv|json


@price_router.get("/signals", response_model=SignalCatalogResponse)
async def list_asset_signal_catalog(
    _current_user: User = Depends(get_current_user),
) -> SignalCatalogResponse:
    """Return static signal definitions compatible with Asset price data."""
    return SignalCatalogResponse(items=[definition for definition in SignalPluginRegistry.list_definitions() if SignalDomain.ASSET in definition.compatible_domains])


@price_router.post("/query", response_model=FAPriceQueryResponse)
async def query_prices_bulk(
    requests: List[FAPriceQueryItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk query prices for multiple assets.

    Reads from DB only (no provider delegation). Uses a single SQL query
    for all assets, then applies backward-fill per asset.
    Analogous to POST /fx/currencies/convert for FX rates.

    Limits (Z-25; the day budget lowered by R13-SEC9-2): at most ``MAX_BULK_ITEMS`` items (422
    ``bulk_too_many_items``, before any read) and at most ``MAX_BULK_ITEM_DAYS`` per-day points over all the fills (422
    ``bulk_too_many_days``, counted once the prices are read, before the fills). The web app's asset list splits its
    request into batches under both, and splits again a batch refused for its days (Z-27).
    """
    if len(requests) > MAX_BULK_ITEMS:
        raise HTTPException(status_code=422, detail=bulk_too_many_items_detail(len(requests), MAX_BULK_ITEMS))
    try:
        results = await AssetSourceManager.get_prices_bulk(requests, session)
        return FAPriceQueryResponse(items=results)
    except SignalRequestValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except BulkTooManyDaysError as e:
        raise HTTPException(status_code=422, detail=bulk_too_many_days_detail(e.item_days, e.max_item_days)) from e
    except Exception as e:
        logger.exception(f"Error querying prices bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@price_router.post("/current", response_model=FACurrentPriceResponse)
async def get_current_prices_bulk(
    asset_ids: List[int],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Bulk fetch current/live prices for multiple assets.

    For each asset:
    1. If a provider is assigned → calls provider.get_current_value() (parallel)
    2. Fallback → returns the latest price from DB (PriceHistory)

    **Side effect**: For successful provider fetches with as_of_date == today,
    the OHLC row for today is created or extended (F.2/F.3 intra-day upsert).
    DB-fallback results are NOT persisted (stale data, not fresh quotes).

    **Example Request**:
    ```json
    POST /api/v1/assets/prices/current
    [1, 2, 3]
    ```

    **Example Response**:
    ```json
    {
      "results": [
        {"asset_id": 1, "value": "142.50", "currency": "USD", "as_of_date": "2026-04-10", "source": "provider:yfinance"},
        {"asset_id": 2, "value": "98.32", "currency": "EUR", "as_of_date": "2026-04-10", "source": "db:last_known"},
        {"asset_id": 3, "value": null, "currency": null, "as_of_date": null, "source": null, "error": "No price data available"}
      ],
      "success_count": 2
    }
    ```
    """
    try:
        results = await AssetSourceManager.get_current_prices_bulk(asset_ids, session)
        success_count = sum(1 for r in results if r.value is not None)
        return FACurrentPriceResponse(results=results, success_count=success_count)
    except Exception as e:
        logger.exception(f"Error fetching current prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# PROVIDER REFRESH ENDPOINTS
# ============================================================================


@price_router.post("/sync", response_model=FABulkRefreshResponse)
async def sync_prices_bulk(
    requests: List[FARefreshItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk sync prices via providers (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_refresh_prices(requests, session)
    except Exception as e:
        logger.exception(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# FIXED-PERIOD CHANGES (MF-P2)
# ============================================================================


@price_router.post("/period-changes", response_model=FAPeriodChangesResponse)
async def query_period_changes_bulk(
    requests: Annotated[List[FAPeriodChangesQueryItem], Body(max_length=PERIOD_CHANGES_MAX_ASSETS)],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """The Assets table's fixed-period changes (1D … 5Y) of several assets, up to each one's ``as_of``.

    Reads the stored price history only: the price on a day is the last stored one on or before it, converted at that
    day's rate when ``target_currency`` is given. Each change is a fraction, null without a usable price on either day.
    At most ``PERIOD_CHANGES_MAX_ASSETS`` items and ``PERIOD_CHANGES_MAX_AS_OF_DAYS`` distinct ``as_of`` days, each from
    1900-01-01 (MF-P2b): 422 otherwise.
    """
    if len({item.as_of for item in requests}) > PERIOD_CHANGES_MAX_AS_OF_DAYS:
        raise HTTPException(status_code=422, detail=f"At most {PERIOD_CHANGES_MAX_AS_OF_DAYS} distinct as_of days per request")
    return FAPeriodChangesResponse(items=await get_period_changes_bulk(requests, session))

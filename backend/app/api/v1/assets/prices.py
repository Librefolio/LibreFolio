"""Asset price endpoints (``/assets/prices``): manual upsert and delete, signal catalog, bulk and current queries, provider sync."""

from datetime import date as date_type
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AfterValidator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import Currency, period_changes_request_refusal
from backend.app.schemas.prices import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkUpsertResponse,
    FACurrentPriceResponse,
    FAPeriodChangesQueryItem,
    FAPeriodChangesResponse,
    FAPriceQueryItem,
    FAPriceQueryResponse,
    FARangeChange,
    FAUpsert,
    FAUpsertResult,
)
from backend.app.schemas.refresh import FABulkRefreshResponse, FARefreshItem
from backend.app.schemas.signals import (
    SignalCatalogResponse,
    SignalDomain,
)
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.period_changes import get_period_changes_bulk, live_range_changes
from backend.app.services.assets.price_store import PriceCurrencyMismatchError, price_currency_mismatch_detail
from backend.app.services.signals.planning import SignalRequestValidationError
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.utils.date_range_limits import MAX_BULK_ITEMS, MAX_BULK_WRITE_ITEMS, BulkTooManyDaysError, DateOutOfRangeError, bulk_too_many_days_detail, bulk_too_many_items_detail, date_out_of_range_detail
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, latest_range_end

logger = get_logger(__name__)

price_router = APIRouter(prefix="/prices", tags=["FA Prices"])


def _range_start_in_bounds(value: date_type | None) -> date_type | None:
    """``range_start`` of ``POST /prices/current`` (R13-SEC9-4): from ``EARLIEST_RANGE_START`` to ``latest_range_end()``, as
    the period changes bound their days; refused by the parameter itself, so the 422 has the standard shape."""
    if value is not None and not EARLIEST_RANGE_START <= value <= latest_range_end():
        raise ValueError(f"range_start ({value}) must be between {EARLIEST_RANGE_START} and {latest_range_end()}")
    return value


def _currency_code(value: str | None) -> str | None:
    """``target_currency`` of ``POST /prices/current``: an ISO 4217 code, normalized as every other ``target_currency``."""
    return Currency.validate_code(value) if value is not None else None


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

    Every refusal of the whole request comes before anything is written. A price over its column's limits refuses it
    with 400; a date outside ``stored_date_bounds()`` (1900-01-01 to tomorrow) with 422 ``date_out_of_range`` (X-R65,
    N83); a price in a currency other than its asset's, on any asset of the request, with 422
    ``price_currency_mismatch``, naming every asset at fault (X-R71). An asset that does not exist is answered in its
    own result, and the others are written.
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
    except PriceCurrencyMismatchError as e:
        raise HTTPException(status_code=422, detail=price_currency_mismatch_detail(e.items, e.count)) from e
    except ValueError as e:
        # A domain refusal of the service (C-97: a price over its column's limits) surfaces as 400 Bad Request, with
        # the structured message the service produced.
        logger.warning("Upsert prices validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # MF-SEC9a: the log keeps the error; the answer never echoes it
        logger.exception(f"Error in bulk upsert prices: {e}")
        raise HTTPException(status_code=500, detail="Internal error while saving prices") from e


@price_router.delete("", response_model=FABulkDeleteResponse)
async def delete_prices_bulk(
    assets: List[FAAssetDelete],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk delete price ranges (PRIMARY bulk endpoint).

    Limit (MF-SEC9a): at most ``MAX_BULK_WRITE_ITEMS`` date ranges, all assets together (422 ``bulk_too_many_items``,
    before any read). The deletion runs in chunks of ranges, in one transaction.
    """
    ranges = sum(len(item.date_ranges) for item in assets)
    if ranges > MAX_BULK_WRITE_ITEMS:
        raise HTTPException(status_code=422, detail=bulk_too_many_items_detail(ranges, MAX_BULK_WRITE_ITEMS))
    try:
        return await AssetSourceManager.bulk_delete_prices(assets, session)
    except Exception as e:
        # MF-SEC9a: the log keeps the error; the answer never echoes it
        logger.exception(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail="Internal error while deleting prices") from e


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
        # R13-SEC9-3: the log keeps the error; the answer never echoes it (an SQL error names the schema)
        logger.exception(f"Error querying prices bulk: {e}")
        raise HTTPException(status_code=500, detail="Internal error while querying prices") from e


@price_router.post("/current", response_model=FACurrentPriceResponse)
async def get_current_prices_bulk(
    asset_ids: List[int],
    range_start: Annotated[
        Optional[date_type],
        Query(description="First day of the range the page shows: each result also carries its whole-range change to the current price (X-R59); from 1900-01-01 to tomorrow"),
        AfterValidator(_range_start_in_bounds),
    ] = None,
    target_currency: Annotated[
        Optional[str],
        Query(description="With range_start: the currency of range_change (Y's D1, the page's converted view): the reference converted at its own day's rate, the price at today's; null changes without a rate. The quotes stay in their own currency"),
        AfterValidator(_currency_code),
    ] = None,
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Bulk fetch current/live prices for multiple assets.

    For each asset:
    1. If a provider is assigned → calls provider.get_current_value() (parallel)
    2. Fallback → returns the latest price from DB (PriceHistory)

    With ``range_start`` each result also carries ``range_change``: the change from the range's reference (the stored
    price on ``range_start``, or the first one inside the range) to this price, by the house's ``range_change`` — the Δ
    the asset page shows next to a live quote, which may not be stored (X-R59).
    With ``target_currency`` too, that change is in that currency: the reference converted at its own day's rate, the
    price at today's; a missing rate leaves it null (Y's D1).

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
    # R13-SEC9-1: refused before any read, the cap of the other bulk requests (range_start is bounded by its parameter)
    if len(asset_ids) > MAX_BULK_ITEMS:
        raise HTTPException(status_code=422, detail=bulk_too_many_items_detail(len(asset_ids), MAX_BULK_ITEMS))
    try:
        results = await AssetSourceManager.get_current_prices_bulk(asset_ids, session)
        if range_start is not None:
            try:
                # One change per distinct id (R13-SEC9-1): a repeated id reads the same item
                changes = await live_range_changes(session, list({result.asset_id: result for result in results}.values()), range_start, target_currency)
            except Exception:  # noqa: BLE001 — the quotes stand without their change, which stays unavailable (null)
                logger.exception("Range change of the current prices failed", range_start=str(range_start))
                changes = {}
            results = [result.model_copy(update={"range_change": changes.get(result.asset_id, FARangeChange())}) for result in results]
        success_count = sum(1 for r in results if r.value is not None)
        return FACurrentPriceResponse(results=results, success_count=success_count)
    except Exception as e:
        # R13-SEC9-3: the log keeps the error; the answer never echoes it
        logger.exception(f"Error fetching current prices: {e}")
        raise HTTPException(status_code=500, detail="Internal error while fetching current prices") from e


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
        # MF-SEC9a: the log keeps the error; the answer never echoes it
        logger.exception(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail="Internal error while syncing prices") from e


# ============================================================================
# FIXED-PERIOD CHANGES (MF-P2)
# ============================================================================


@price_router.post("/period-changes", response_model=FAPeriodChangesResponse)
async def query_period_changes_bulk(
    requests: List[FAPeriodChangesQueryItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """The Assets table's fixed-period changes (1D … 5Y) of several assets, up to each one's ``as_of``, and the change over
    the whole range the page shows when ``range_start`` is given (X-R59).

    Reads the stored price history only: the price on a day is the last stored one on or before it, converted at that
    day's rate when ``target_currency`` is given. Each change is a fraction, null without a usable price on either day.
    Limits (``period_changes_request_refusal``): at most ``MAX_BULK_ITEMS`` items (422 ``bulk_too_many_items``, as the
    price query) and ``PERIOD_CHANGES_MAX_AS_OF_DAYS`` distinct ``as_of`` and ``range_start`` days (422
    ``period_changes_too_many_days``), each from 1900-01-01.
    """
    refusal = period_changes_request_refusal(requests)
    if refusal is not None:
        raise HTTPException(status_code=422, detail=refusal)
    return FAPeriodChangesResponse(items=await get_period_changes_bulk(requests, session))

"""
Asset Provider API endpoints.
Handles provider assignment, price management, and price refresh operations.
"""
import logging
from datetime import date
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.assets import (
    AssetProviderAssignmentModel,
    PricePointModel,
)
from backend.app.schemas.common import BackwardFillInfo
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.provider_registry import AssetProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Assets"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProviderAssignmentItem(BaseModel):
    """Single provider assignment."""
    asset_id: int = Field(..., description="Asset ID")
    provider_code: str = Field(..., description="Provider code (yfinance, cssscraper, etc.)")
    provider_params: dict = Field(..., description="Provider-specific configuration (JSON)")
    fetch_interval: Optional[int] = Field(None, description="Refresh frequency in minutes (NULL = default 1440 = 24h)")


class BulkAssignProvidersRequest(BaseModel):
    """Request for bulk provider assignment."""
    assignments: List[ProviderAssignmentItem] = Field(..., min_length=1, description="List of provider assignments")


class ProviderAssignmentResult(BaseModel):
    """Result of single provider assignment."""
    asset_id: int
    success: bool
    message: str


class BulkAssignProvidersResponse(BaseModel):
    """Response for bulk provider assignment."""
    results: List[ProviderAssignmentResult]
    success_count: int
    failed_count: int


class BulkRemoveProvidersRequest(BaseModel):
    """Request for bulk provider removal."""
    asset_ids: List[int] = Field(..., min_length=1, description="List of asset IDs")


class BulkRemoveProvidersResponse(BaseModel):
    """Response for bulk provider removal."""
    results: List[ProviderAssignmentResult]
    success_count: int


class PriceUpsertItem(BaseModel):
    """Price data for upsert."""
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = "USD"


class AssetPricesUpsert(BaseModel):
    """Prices to upsert for a single asset."""
    asset_id: int
    prices: List[PriceUpsertItem] = Field(..., min_length=1)


class BulkUpsertPricesRequest(BaseModel):
    """Request for bulk price upsert."""
    data: List[AssetPricesUpsert] = Field(..., min_length=1)


class AssetPricesUpsertResult(BaseModel):
    """Result of upsert for single asset."""
    asset_id: int
    count: int
    message: str


class BulkUpsertPricesResponse(BaseModel):
    """Response for bulk price upsert."""
    inserted_count: int
    updated_count: int
    results: List[AssetPricesUpsertResult]


class DateRange(BaseModel):
    """Date range for deletion."""
    start: date
    end: Optional[date] = None  # If None, only delete start date


class AssetPricesDelete(BaseModel):
    """Price ranges to delete for a single asset."""
    asset_id: int
    date_ranges: List[DateRange] = Field(..., min_length=1)


class BulkDeletePricesRequest(BaseModel):
    """Request for bulk price deletion."""
    data: List[AssetPricesDelete] = Field(..., min_length=1)


class AssetPricesDeleteResult(BaseModel):
    """Result of deletion for single asset."""
    asset_id: int
    deleted: int
    message: str


class BulkDeletePricesResponse(BaseModel):
    """Response for bulk price deletion."""
    deleted_count: int
    results: List[AssetPricesDeleteResult]


class RefreshItem(BaseModel):
    """Single asset refresh request."""
    asset_id: int
    start_date: date
    end_date: date
    force: Optional[bool] = Field(False, description="Force refresh even if recently fetched")


class BulkRefreshRequest(BaseModel):
    """Request for bulk price refresh."""
    requests: List[RefreshItem] = Field(..., min_length=1)


class RefreshResult(BaseModel):
    """Result of refresh for single asset."""
    asset_id: int
    fetched_count: int
    inserted_count: int
    updated_count: int
    errors: List[str]


class BulkRefreshResponse(BaseModel):
    """Response for bulk price refresh."""
    results: List[RefreshResult]


class PriceQueryResult(BaseModel):
    """Single price point with backward-fill info."""
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    currency: str
    backward_fill_info: Optional[BackwardFillInfo] = None


class GetPricesResponse(BaseModel):
    """Response for price query."""
    prices: List[PriceQueryResult]


class ProviderInfo(BaseModel):
    """Information about a single asset pricing provider."""
    code: str = Field(..., description="Provider code (e.g., yfinance, cssscraper)")
    name: str = Field(..., description="Provider full name")
    description: str = Field(..., description="Provider description")
    supports_search: bool = Field(..., description="Whether provider supports asset search")


# ============================================================================
# PROVIDER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    """List all available asset pricing providers."""
    providers = []

    AssetProviderRegistry.auto_discover()

    for code in AssetProviderRegistry.list_providers():
        provider_class = AssetProviderRegistry.get_provider(code)
        if provider_class:
            instance = AssetProviderRegistry.get_provider_instance(code)
            if instance:
                # Check if provider supports search
                supports_search = True
                try:
                    # Try calling search with empty query to see if it raises NOT_SUPPORTED
                    await instance.search("")
                except Exception as e:
                    if "NOT_SUPPORTED" in str(e) or "not supported" in str(e).lower():
                        supports_search = False

                providers.append(ProviderInfo(
                    code=instance.provider_code,
                    name=instance.provider_name,
                    description=f"{instance.provider_name} pricing provider",
                    supports_search=supports_search
                ))

    return providers


@router.post("/provider/bulk", response_model=BulkAssignProvidersResponse)
async def assign_providers_bulk(
    request: BulkAssignProvidersRequest,
    session: AsyncSession = Depends(get_session)
):
    """Bulk assign providers to assets (PRIMARY bulk endpoint)."""
    try:
        assignments = [item.model_dump() for item in request.assignments]
        results = await AssetSourceManager.bulk_assign_providers(assignments, session)

        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count

        return BulkAssignProvidersResponse(
            results=[ProviderAssignmentResult(**r) for r in results],
            success_count=success_count,
            failed_count=failed_count
        )
    except Exception as e:
        logger.error(f"Error in bulk assign providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/provider")
async def assign_provider_single(
    asset_id: int,
    assignment: ProviderAssignmentItem,
    session: AsyncSession = Depends(get_session)
):
    """Assign provider to single asset (convenience endpoint, calls bulk internally)."""
    try:
        # Ensure asset_id from path matches body
        if assignment.asset_id != asset_id:
            raise HTTPException(status_code=400, detail="asset_id in path must match asset_id in body")

        result = await AssetSourceManager.assign_provider(
            asset_id,
            assignment.provider_code,
            assignment.provider_params,
            session
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning provider to asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/provider/bulk", response_model=BulkRemoveProvidersResponse)
async def remove_providers_bulk(
    request: BulkRemoveProvidersRequest,
    session: AsyncSession = Depends(get_session)
):
    """Bulk remove provider assignments (PRIMARY bulk endpoint)."""
    try:
        results = await AssetSourceManager.bulk_remove_providers(request.asset_ids, session)

        return BulkRemoveProvidersResponse(
            results=[ProviderAssignmentResult(**r) for r in results],
            success_count=len(results)
        )
    except Exception as e:
        logger.error(f"Error in bulk remove providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}/provider")
async def remove_provider_single(
    asset_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Remove provider from single asset (convenience endpoint, calls bulk internally)."""
    try:
        result = await AssetSourceManager.remove_provider(asset_id, session)
        return result
    except Exception as e:
        logger.error(f"Error removing provider from asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MANUAL PRICE MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/prices/bulk", response_model=BulkUpsertPricesResponse)
async def upsert_prices_bulk(
    request: BulkUpsertPricesRequest,
    session: AsyncSession = Depends(get_session)
):
    """Bulk upsert prices manually (PRIMARY bulk endpoint)."""
    try:
        data = [
            {
                "asset_id": item.asset_id,
                "prices": [p.model_dump() for p in item.prices]
            }
            for item in request.data
        ]

        result = await AssetSourceManager.bulk_upsert_prices(data, session)

        return BulkUpsertPricesResponse(
            inserted_count=result["inserted_count"],
            updated_count=result["updated_count"],
            results=[AssetPricesUpsertResult(**r) for r in result["results"]]
        )
    except Exception as e:
        logger.error(f"Error in bulk upsert prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/prices")
async def upsert_prices_single(
    asset_id: int,
    prices: List[PriceUpsertItem],
    session: AsyncSession = Depends(get_session)
):
    """Upsert prices for single asset (convenience endpoint, calls bulk internally)."""
    try:
        prices_dict = [p.model_dump() for p in prices]
        result = await AssetSourceManager.upsert_prices(asset_id, prices_dict, session)
        return result
    except Exception as e:
        logger.error(f"Error upserting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prices/bulk", response_model=BulkDeletePricesResponse)
async def delete_prices_bulk(
    request: BulkDeletePricesRequest,
    session: AsyncSession = Depends(get_session)
):
    """Bulk delete price ranges (PRIMARY bulk endpoint)."""
    try:
        data = [
            {
                "asset_id": item.asset_id,
                "date_ranges": [r.model_dump() for r in item.date_ranges]
            }
            for item in request.data
        ]

        result = await AssetSourceManager.bulk_delete_prices(data, session)

        return BulkDeletePricesResponse(
            deleted_count=result["deleted_count"],
            results=[AssetPricesDeleteResult(**r) for r in result["results"]]
        )
    except Exception as e:
        logger.error(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}/prices")
async def delete_prices_single(
    asset_id: int,
    date_ranges: List[DateRange],
    session: AsyncSession = Depends(get_session)
):
    """Delete price ranges for single asset (convenience endpoint, calls bulk internally)."""
    try:
        ranges_dict = [r.model_dump() for r in date_ranges]
        result = await AssetSourceManager.delete_prices(asset_id, ranges_dict, session)
        return result
    except Exception as e:
        logger.error(f"Error deleting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRICE QUERY ENDPOINTS
# ============================================================================

@router.get("/{asset_id}/prices", response_model=GetPricesResponse)
async def get_prices(
    asset_id: int,
    start_date: date = Query(..., description="Start date (required)"),
    end_date: Optional[date] = Query(None, description="End date (optional, defaults to start_date)"),
    session: AsyncSession = Depends(get_session)
):
    """Get prices for asset with backward-fill support."""
    try:
        if end_date is None:
            end_date = start_date

        prices = await AssetSourceManager.get_prices(asset_id, start_date, end_date, session)

        return GetPricesResponse(
            prices=[PriceQueryResult(**p) for p in prices]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROVIDER REFRESH ENDPOINTS
# ============================================================================

@router.post("/prices-refresh/bulk", response_model=BulkRefreshResponse)
async def refresh_prices_bulk(
    request: BulkRefreshRequest,
    session: AsyncSession = Depends(get_session)
):
    """Bulk refresh prices via providers (PRIMARY bulk endpoint)."""
    try:
        payload = [r.model_dump() for r in request.requests]
        results = await AssetSourceManager.bulk_refresh_prices(payload, session)

        return BulkRefreshResponse(
            results=[RefreshResult(**r) for r in results]
        )
    except Exception as e:
        logger.error(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/prices-refresh")
async def refresh_prices_single(
    asset_id: int,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    force: bool = Query(False, description="Force refresh"),
    session: AsyncSession = Depends(get_session)
):
    """Refresh prices for single asset (convenience endpoint, calls bulk internally)."""
    try:
        result = await AssetSourceManager.refresh_price(
            asset_id, start_date, end_date, session, force=force
        )
        return result
    except Exception as e:
        logger.error(f"Error refreshing prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))




"""
Asset Provider API endpoints.
Handles provider assignment, price management, and price refresh operations.
"""
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.db.session import get_session_generator
from backend.app.schemas.assets import (
    PricePointModel,
    MetadataRefreshResult,
    BulkPatchAssetMetadataRequest,
    AssetMetadataResponse,
    BulkAssetReadRequest,
    BulkMetadataRefreshRequest,
    BulkMetadataRefreshResponse,
    )
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import (
    FAUpsertItem,
    FABulkUpsertRequest,
    FAUpsertResult,
    FABulkUpsertResponse,
    FABulkDeleteRequest,
    FAAssetDeleteResult,
    FABulkDeleteResponse,
    )
from backend.app.schemas.provider import (
    FAProviderInfo,
    FAProviderAssignmentItem,
    FABulkAssignRequest,
    FAProviderAssignmentResult,
    FABulkAssignResponse,
    FABulkRemoveRequest,
    FAProviderRemovalResult,
    FABulkRemoveResponse,
    )
from backend.app.schemas.refresh import (
    FABulkRefreshRequest,
    FARefreshResult,
    FABulkRefreshResponse,
    )
from backend.app.services.asset_metadata import AssetMetadataService
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.provider_registry import AssetProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Assets"])


# ============================================================================
# PROVIDER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/providers", response_model=List[FAProviderInfo])
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

                providers.append(FAProviderInfo(
                    code=instance.provider_code,
                    name=instance.provider_name,
                    description=f"{instance.provider_name} pricing provider",
                    supports_search=supports_search
                    ))

    return providers


@router.post("/provider/bulk", response_model=FABulkAssignResponse)
async def assign_providers_bulk(
    request: FABulkAssignRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk assign providers to assets (PRIMARY bulk endpoint)."""
    try:
        assignments = [item.model_dump() for item in request.assignments]
        results = await AssetSourceManager.bulk_assign_providers(assignments, session)

        success_count = sum(1 for r in results if r["success"])

        return FABulkAssignResponse(
            results=[FAProviderAssignmentResult(**r) for r in results],
            success_count=success_count
            )
    except Exception as e:
        logger.error(f"Error in bulk assign providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/provider")
async def assign_provider_single(
    asset_id: int,
    assignment: FAProviderAssignmentItem,
    session: AsyncSession = Depends(get_session_generator)
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


@router.delete("/provider/bulk", response_model=FABulkRemoveResponse)
async def remove_providers_bulk(
    request: FABulkRemoveRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk remove provider assignments (PRIMARY bulk endpoint)."""
    try:
        results = await AssetSourceManager.bulk_remove_providers(request.asset_ids, session)

        return FABulkRemoveResponse(
            results=[FAProviderRemovalResult(**r) for r in results],
            success_count=len(results)
            )
    except Exception as e:
        logger.error(f"Error in bulk remove providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}/provider")
async def remove_provider_single(
    asset_id: int,
    session: AsyncSession = Depends(get_session_generator)
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

@router.post("/prices/bulk", response_model=FABulkUpsertResponse)
async def upsert_prices_bulk(
    request: FABulkUpsertRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk upsert prices manually (PRIMARY bulk endpoint)."""
    try:
        data = [
            {
                "asset_id": item.asset_id,
                "prices": [p.model_dump() for p in item.prices]
                }
            for item in request.assets
            ]

        result = await AssetSourceManager.bulk_upsert_prices(data, session)

        return FABulkUpsertResponse(
            inserted_count=result["inserted_count"],
            updated_count=result["updated_count"],
            results=[FAUpsertResult(**r) for r in result["results"]]
            )
    except Exception as e:
        logger.error(f"Error in bulk upsert prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TODO: rimuovere e usare solo la bulk
@router.post("/{asset_id}/prices")
async def upsert_prices_single(
    asset_id: int,
    prices: List[FAUpsertItem],
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Upsert prices for single asset (convenience endpoint, calls bulk internally)."""
    try:
        prices_dict = [p.model_dump() for p in prices]
        result = await AssetSourceManager.upsert_prices(asset_id, prices_dict, session)
        return result
    except Exception as e:
        logger.error(f"Error upserting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prices/bulk", response_model=FABulkDeleteResponse)
async def delete_prices_bulk(
    request: FABulkDeleteRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk delete price ranges (PRIMARY bulk endpoint)."""
    try:
        data = [
            {
                "asset_id": item.asset_id,
                "date_ranges": [r.model_dump() for r in item.date_ranges]
                }
            for item in request.assets  # Changed from request.data to request.assets
            ]

        result = await AssetSourceManager.bulk_delete_prices(data, session)

        return FABulkDeleteResponse(
            deleted_count=result["deleted_count"],
            results=[FAAssetDeleteResult(**r) for r in result["results"]]
            )
    except Exception as e:
        logger.error(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TODO: rimuovere e usare solo la bulk
@router.delete("/{asset_id}/prices")
async def delete_prices_single(
    asset_id: int,
    date_ranges: List[DateRangeModel],
    session: AsyncSession = Depends(get_session_generator)
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

@router.get("/{asset_id}/prices", response_model=List[PricePointModel])
async def get_prices(
    asset_id: int,
    start_date: date = Query(..., description="Start date (required)"),
    end_date: Optional[date] = Query(None, description="End date (optional, defaults to start_date)"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Get prices for asset with backward-fill support.

    Returns a list of PricePointModel with OHLC data, volume, and backward-fill info.
    """
    try:
        if end_date is None:
            end_date = start_date

        prices = await AssetSourceManager.get_prices(asset_id, start_date, end_date, session)

        return prices  # Already List[PricePointModel] from service
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TODO: aggiungere endpoint per creare Asset bulk, capire endpoint e request/response model e anche per eliminare asset e

# TODO: aggiungere GET /api/v1/assets per avere la lista degli asset

# TODO: rinominare in /bulk
@router.post("", response_model=List[AssetMetadataResponse])
async def read_assets_bulk(
    request: BulkAssetReadRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Bulk read assets with classification metadata (preserves request order).

    Fetches basic asset information along with parsed classification_params
    for multiple assets in a single request. Assets not found are silently
    skipped.

    **Request Body**:
    ```json
    {
      "asset_ids": [1, 2, 3]
    }
    ```

    **Response** (ordered by request):
    ```json
    [
      {
        "asset_id": 1,
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "currency": "USD",
        "classification_params": {
          "investment_type": "stock",
          "sector": "Technology",
          "short_description": "Consumer electronics",
          "geographic_area": {
            "USA": "1.0000"
          }
        }
      },
      {
        "asset_id": 2,
        "display_name": "Vanguard S&P 500",
        "identifier": "VOO",
        "currency": "USD",
        "classification_params": {
          "investment_type": "etf",
          "geographic_area": {
            "USA": "1.0000"
          }
        }
      }
    ]
    ```

    **Classification Params**:
    - Parsed from JSON stored in database
    - May be null if no metadata set
    - Geographic area contains ISO-3166-A3 codes
    - Weights are Decimal strings (4 decimal places)

    Args:
        request: Bulk read request with list of asset IDs
        session: Database session

    Returns:
        List of AssetMetadataResponse in request order (missing assets skipped)

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        if not request.asset_ids:
            return []

        stmt = select(Asset).where(Asset.id.in_(request.asset_ids))
        result = await session.execute(stmt)
        assets = result.scalars().all()
        asset_map = {asset.id: asset for asset in assets}

        responses = []
        for asset_id in request.asset_ids:
            asset = asset_map.get(asset_id)
            if not asset:
                continue
            responses.append(
                AssetMetadataResponse(
                    asset_id=asset.id,
                    display_name=asset.display_name,
                    identifier=asset.identifier,
                    currency=asset.currency,
                    classification_params=AssetMetadataService.parse_classification_params(
                        asset.classification_params
                        )
                    )
                )

        return responses
    except Exception as e:
        logger.error(f"Error reading assets bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROVIDER REFRESH ENDPOINTS
# ============================================================================

@router.post("/prices-refresh/bulk", response_model=FABulkRefreshResponse)
async def refresh_prices_bulk(
    request: FABulkRefreshRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk refresh prices via providers (PRIMARY bulk endpoint)."""
    try:
        payload = [r.model_dump() for r in request.requests]
        results = await AssetSourceManager.bulk_refresh_prices(payload, session)

        return FABulkRefreshResponse(
            results=[FARefreshResult(**r) for r in results]
            )
    except Exception as e:
        logger.error(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TODO: rimuovere e usare solo la bulk
@router.post("/{asset_id}/prices-refresh")
async def refresh_prices_single(
    asset_id: int,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    force: bool = Query(False, description="Force refresh"),
    session: AsyncSession = Depends(get_session_generator)
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


@router.patch("/metadata", response_model=list[MetadataRefreshResult])
async def update_assets_metadata_bulk(
    request: BulkPatchAssetMetadataRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Bulk partial update (PATCH) of asset classification metadata.

    Follows RFC 7386 JSON Merge Patch semantics:
    - Absent fields in patch: ignored (no change)
    - Field = null: clears the field
    - Field = value: updates the field

    **Geographic Area Handling**:
    - Full replacement (not merge) of geographic_area dict
    - Countries normalized to ISO-3166-A3 codes
    - Weights must sum to 1.0 (±0.0001 tolerance)
    - Weights quantized to 4 decimal places

    **Request Body**:
    ```json
    {
      "assets": [
        {
          "asset_id": 1,
          "patch": {
            "investment_type": "etf",
            "sector": "Technology",
            "geographic_area": {
              "USA": "0.6",
              "GBR": "0.4"
            }
          }
        }
      ]
    }
    ```

    **Response** (per-item results):
    ```json
    [
      {
        "asset_id": 1,
        "success": true,
        "message": "updated",
        "changes": [
          {"field": "investment_type", "old": "stock", "new": "etf"},
          {"field": "geographic_area", "old": {...}, "new": {...}}
        ]
      }
    ]
    ```

    **Validation Errors** (per-item):
    - Invalid country code → success=false, message with details
    - Geographic area sum != 1.0 → success=false
    - Negative weights → success=false

    Args:
        request: Bulk PATCH request with list of asset patches
        session: Database session

    Returns:
        List of MetadataRefreshResult (per-item success/failure)

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        results = []
        for item in request.assets:
            try:
                res = await AssetMetadataService.update_asset_metadata(item.asset_id, item.patch, session)
                results.append({
                    "asset_id": item.asset_id,
                    "success": True,
                    "message": "updated",
                    "changes": getattr(res, "changes", None)
                    })
            except ValueError as e:
                results.append({
                    "asset_id": item.asset_id,
                    "success": False,
                    "message": str(e)
                    })
            except Exception as e:
                logger.error(f"Error updating metadata for asset {item.asset_id}: {e}")
                results.append({
                    "asset_id": item.asset_id,
                    "success": False,
                    "message": "internal error"
                    })
        return results
    except Exception as e:
        logger.error(f"Error in bulk metadata update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TODO: rimuovere endpoint singolo e usare solo il bulk
@router.post("/{asset_id}/metadata/refresh", response_model=MetadataRefreshResult)
async def refresh_asset_metadata_single(
    asset_id: int,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Refresh classification metadata for a single asset from its assigned provider.

    Fetches fresh metadata from the asset's pricing provider (if it supports
    metadata) and merges it with existing classification_params. Provider data
    takes precedence over existing user-entered data.

    **Provider Requirements**:
    - Asset must have a provider assigned
    - Provider must support metadata fetching
    - Provider must return valid classification data

    **Response Examples**:

    Success with metadata updated:
    ```json
    {
      "asset_id": 1,
      "success": true,
      "message": "Metadata refreshed from yfinance",
      "changes": [
        {"field": "sector", "old": null, "new": "Technology"},
        {"field": "investment_type", "old": "stock", "new": "etf"}
      ]
    }
    ```

    No provider assigned:
    ```json
    {
      "asset_id": 1,
      "success": false,
      "message": "No provider assigned to asset"
    }
    ```

    Provider doesn't support metadata:
    ```json
    {
      "asset_id": 1,
      "success": false,
      "message": "Provider cssscraper does not support metadata"
    }
    ```

    Args:
        asset_id: ID of the asset to refresh metadata for
        session: Database session

    Returns:
        MetadataRefreshResult with success status and changes

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        result = await AssetSourceManager.refresh_asset_metadata(asset_id, session)
        return MetadataRefreshResult(**result)
    except Exception as e:
        logger.error(f"Error refreshing metadata for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata/refresh/bulk", response_model=BulkMetadataRefreshResponse)
async def refresh_asset_metadata_bulk(
    request: BulkMetadataRefreshRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Bulk refresh classification metadata from providers (partial success allowed).

    Refreshes metadata for multiple assets in a single request. Each asset is
    processed independently, and partial failures are reported per-item.

    **Request Body**:
    ```json
    {
      "asset_ids": [1, 2, 3]
    }
    ```

    **Response**:
    ```json
    {
      "results": [
        {
          "asset_id": 1,
          "success": true,
          "message": "Metadata refreshed from yfinance",
          "changes": [{"field": "sector", "old": null, "new": "Technology"}]
        },
        {
          "asset_id": 2,
          "success": false,
          "message": "No provider assigned to asset"
        },
        {
          "asset_id": 3,
          "success": true,
          "message": "No metadata changes"
        }
      ],
      "success_count": 2,
      "failed_count": 1
    }
    ```

    **Per-Item Outcomes**:
    - success=true: Metadata refreshed (may have 0 changes)
    - success=false: No provider, provider doesn't support metadata, or error

    Args:
        request: Bulk refresh request with list of asset IDs
        session: Database session

    Returns:
        BulkMetadataRefreshResponse with per-item results and counts

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        result = await AssetSourceManager.bulk_refresh_metadata(request.asset_ids, session)
        return BulkMetadataRefreshResponse(**result)
    except Exception as e:
        logger.error(f"Error in bulk metadata refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))

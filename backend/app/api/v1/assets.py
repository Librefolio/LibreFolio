"""
Asset Provider API endpoints.
Handles provider assignment, price management, and price refresh operations.
"""
import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAPricePoint,
    FAMetadataRefreshResult,
    FAClassificationParams,
    FAPatchMetadataItem,
    FAAssetMetadataResponse,
    FABulkMetadataRefreshResponse,
    # Asset CRUD schemas
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    FAAinfoFiltersRequest,
    FAinfoResponse,
    FABulkAssetDeleteRequest,
    FABulkAssetDeleteResponse,
    # Asset PATCH schemas
    FAAssetPatchItem,
    FABulkAssetPatchResponse,
    )
from backend.app.schemas.prices import (
    FAUpsertResult,
    FABulkUpsertResponse,
    FAPriceBulkDeleteRequest,
    FABulkDeleteResponse,
    )
from backend.app.schemas.provider import (
    FAProviderInfo,
    FAProviderAssignmentItem,
    FABulkAssignResponse,
    FABulkRemoveResponse,
    FAProviderAssignmentReadItem,
    )
from backend.app.schemas.refresh import FABulkRefreshResponse
from backend.app.services.asset_crud import AssetCRUDService
from backend.app.services.asset_metadata import AssetMetadataService
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.provider_registry import AssetProviderRegistry

logger = get_logger(__name__)

asset_router = APIRouter(prefix="/assets", tags=["Assets"])
metadata_router = APIRouter(prefix="/metadata", tags=["FA Metadata"])
price_router = APIRouter(prefix="/prices", tags=["FA Prices"])
provider_router = APIRouter(prefix="/provider", tags=["FA Provider"])
# Include metadata_router in main router at the end because include_router do a run-time copy, not dynamic reference

# ============================================================================
# ASSET CRUD ENDPOINTS
# ============================================================================

@asset_router.post("", response_model=FABulkAssetCreateResponse, status_code=201, tags=["FA CRUD"])
async def create_assets_bulk(
    assets: List[FAAssetCreateItem],
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Create multiple assets in bulk (partial success allowed).

    Creates asset records with optional classification metadata.
    Provider assignment can be done separately via POST /assets/provider.

    **Request Example**:
    ```json
    [
      {
        "display_name": "Apple Inc.",
        "currency": "USD",
        "asset_type": "STOCK",
        "icon_url": "https://example.com/aapl.png",
        "classification_params": {
          "sector": "Technology",
          "geographic_area": {"USA": "1.0"}
        }
      }
    ]
    ```

    **Response Example**:
    ```json
    {
      "results": [
        {
          "asset_id": 1,
          "success": true,
          "message": "Asset created successfully",
          "display_name": "Apple Inc."
        }
      ],
      "success_count": 1,
      "failed_count": 0
    }
    ```
    """
    try:
        return await AssetCRUDService.create_assets_bulk(assets, session)
    except Exception as e:
        logger.error(f"Error in bulk asset creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@asset_router.patch("", response_model=FABulkAssetPatchResponse, tags=["FA CRUD"])
async def patch_assets_bulk(
    assets: List[FAAssetPatchItem],
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Update multiple assets in bulk (partial success allowed).

    **Merge Logic**:
    - Field present (even if None): UPDATE or BLANK value
    - Field absent: IGNORE (keep existing value)

    **Example Request**:
    ```json
    [
      {
        "asset_id": 1,
        "display_name": "Apple Inc. - Updated",
        "classification_params": {
          "sector": "Technology",
          "short_description": "New description"
        }
      },
      {
        "asset_id": 2,
        "classification_params": null,
        "active": false
      }
    ]
    ```

    **Classification Params Optimization**:
    - If None: Clears metadata (DB column set to NULL)
    - If present: Only non-null subfields saved to DB (JSON optimization)

    **Response Fields**:
    - `updated_fields`: List of field names actually changed
    - Per-item success/failure status
    """
    try:
        return await AssetCRUDService.patch_assets_bulk(assets, session)
    except Exception as e:
        logger.error(f"Error in bulk asset patch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@asset_router.get("/query", response_model=List[FAinfoResponse], tags=["FA CRUD"])
async def list_assets(
    currency: Optional[str] = Query(None, description="Filter by currency (e.g., USD)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (e.g., STOCK)"),
    valuation_model: Optional[str] = Query(None, description="Filter by valuation model (e.g., MARKET_PRICE)"),
    active: bool = Query(True, description="Include only active assets (default: true)"),
    search: Optional[str] = Query(None, description="Search in display_name or identifier"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    List all assets with optional filters.

    **Query Parameters**:
    - `currency`: Filter by currency code (e.g., "USD", "EUR")
    - `asset_type`: Filter by type (e.g., "STOCK", "ETF", "BOND")
    - `valuation_model`: Filter by valuation model (e.g., "MARKET_PRICE", "SCHEDULED_YIELD")
    - `active`: Include only active assets (default: true, set to false for inactive)
    - `search`: Search text in asset name or identifier (case-insensitive)

    **Response Fields**:
    - `has_provider`: True if asset has a pricing provider assigned
    - `has_metadata`: True if asset has classification metadata (sector, geographic_area, etc.)

    **Example**:
    ```
    GET /api/v1/assets/list?currency=USD&asset_type=STOCK&search=Apple
    ```
    """
    try:
        filters = FAAinfoFiltersRequest(
            currency=currency,
            asset_type=asset_type,
            valuation_model=valuation_model,
            active=active,
            search=search
            )
        return await AssetCRUDService.list_assets(filters, session)
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@asset_router.delete("", response_model=FABulkAssetDeleteResponse, tags=["FA CRUD"])
async def delete_assets_bulk(
    request: FABulkAssetDeleteRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Delete multiple assets in bulk (partial success allowed).

    **Warning**: This will CASCADE DELETE:
    - Provider assignments (asset_provider_assignments table)
    - Price history (price_history table)

    **Blocks deletion** if asset has transactions (foreign key constraint).

    **Request Example**:
    ```json
    {
      "asset_ids": [1, 2, 3]
    }
    ```

    **Response Example**:
    ```json
    {
      "results": [
        {
          "asset_id": 1,
          "success": true,
          "message": "Asset deleted successfully"
        },
        {
          "asset_id": 2,
          "success": false,
          "message": "Cannot delete asset 2: has existing transactions"
        }
      ],
      "success_count": 1,
      "failed_count": 1
    }
    ```
    """
    try:
        return await AssetCRUDService.delete_assets_bulk(request.asset_ids, session)
    except Exception as e:
        logger.error(f"Error in bulk asset deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROVIDER MANAGEMENT ENDPOINTS
# ============================================================================

@provider_router.get("", response_model=List[FAProviderInfo])
async def list_providers():
    """List all available asset pricing providers."""
    providers = []

    # list_providers() returns list of dicts with 'code' and 'name' keys
    for provider_info in AssetProviderRegistry.list_providers():
        code = provider_info['code']  # Extract code from dict
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
                    icon_url=instance.get_icon(),
                    supports_search=supports_search
                    ))

    return providers


@provider_router.post("", response_model=FABulkAssignResponse)
async def assign_providers_bulk(
    assignments: List[FAProviderAssignmentItem],
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk assign providers to assets (PRIMARY bulk endpoint)."""
    try:
        results = await AssetSourceManager.bulk_assign_providers(assignments, session)
        success_count = sum(1 for r in results if r.success)
        return FABulkAssignResponse(results=results, success_count=success_count)
    except Exception as e:
        logger.error(f"Error in bulk assign providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@provider_router.delete("", response_model=FABulkRemoveResponse)
async def remove_providers_bulk(
    asset_ids: List[int],
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk remove provider assignments (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_remove_providers(asset_ids, session)
    except Exception as e:
        logger.error(f"Error in bulk remove providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@provider_router.get("/assignments", response_model=List[FAProviderAssignmentReadItem])
async def get_provider_assignments(
    asset_ids: List[int] = Query(..., description="List of asset IDs"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Get provider assignments for multiple assets.

    Returns identifier, identifier_type, and provider_params for each assigned asset.

    **Example**:
    ```
    GET /api/v1/assets/provider/assignments?asset_ids=1&asset_ids=2&asset_ids=3
    ```

    **Response**:
    ```json
    [
      {
        "asset_id": 1,
        "provider_code": "yfinance",
        "identifier": "AAPL",
        "identifier_type": "TICKER",
        "provider_params": {},
        "fetch_interval": 1440,
        "last_fetch_at": "2025-01-15T10:30:00Z"
      }
    ]
    ```
    """
    try:
        # Query with WHERE IN for efficiency
        stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        result = await session.execute(stmt)
        assignments = result.scalars().all()

        # Convert to response schema
        items = []
        for a in assignments:
            params = json.loads(a.provider_params) if a.provider_params else None
            items.append(FAProviderAssignmentReadItem(
                asset_id=a.asset_id,
                provider_code=a.provider_code,
                identifier=a.identifier,
                identifier_type=a.identifier_type,
                provider_params=params,
                fetch_interval=a.fetch_interval,
                last_fetch_at=a.last_fetch_at.isoformat() if a.last_fetch_at else None
            ))

        return items
    except Exception as e:
        logger.error(f"Error getting provider assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MANUAL PRICE MANAGEMENT ENDPOINTS
# ============================================================================

@price_router.post("", response_model=FABulkUpsertResponse)
async def upsert_prices_bulk(
    request: FABulkUpsertRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk upsert prices manually (PRIMARY bulk endpoint)."""
    try:
        # Pass FAUpsert objects directly to service
        result = await AssetSourceManager.bulk_upsert_prices(request.assets, session)

        return FABulkUpsertResponse(
            inserted_count=result["inserted_count"],
            updated_count=result["updated_count"],
            results=[FAUpsertResult(**r) for r in result["results"]]
            )
    except Exception as e:
        logger.error(f"Error in bulk upsert prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@price_router.delete("", response_model=FABulkDeleteResponse)
async def delete_prices_bulk(
    request: FAPriceBulkDeleteRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk delete price ranges (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_delete_prices(request.assets, session)
    except Exception as e:
        logger.error(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRICE QUERY ENDPOINTS
# ============================================================================

# Use single asset price history with backward-fill support because
# create a POST and encapsulate params is too much overhead and complexity
@price_router.get("/{asset_id}", response_model=List[FAPricePoint])
async def get_prices(
    asset_id: int,
    start_date: date = Query(..., description="Start date (required)"),
    end_date: Optional[date] = Query(None, description="End date (optional, defaults to start_date)"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Get prices for asset with backward-fill support.

    Returns a list of FAPricePoint with OHLC data, volume, and backward-fill info.
    """
    try:
        if end_date is None:
            end_date = start_date

        prices = await AssetSourceManager.get_prices(asset_id, start_date, end_date, session)

        return prices  # Already List[FAPricePoint] from service
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting prices for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Bulk read endpoint
@asset_router.get("", response_model=List[FAAssetMetadataResponse], tags=["FA CRUD"])
async def read_assets_bulk(
    asset_ids: List[int] = Query(..., description="List of asset IDs to read"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Bulk read assets with classification metadata (preserves request order).

    Fetches basic asset information along with parsed classification_params
    for multiple assets in a single request. Assets not found are silently
    skipped.

    **Request query**:
    ```json
    GET /api/v1/assets?asset_ids=1&asset_ids=2&asset_ids=3
    ```

    **Response** (ordered by request):
    ```json
    [
      {
        "asset_id": 1,
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "currency": "USD",
        "asset_type": "stock",
        "classification_params": {
          "sector": "Technology",
          "short_description": "Consumer electronics",
          "geographic_area": {
            "USA": "1.0000"
          }
        },
        has_provider: false
      },
      {
        "asset_id": 2,
        "display_name": "Vanguard S&P 500",
        "identifier": "VOO",
        "currency": "USD",
        "asset_type": "etf",
        "classification_params": {
          "geographic_area": {
            "USA": "1.0000"
          }
        },
        has_provider: true
      }
    ]
    ```

    **Classification Params**:
    - Parsed from JSON stored in database
    - May be null if no metadata set
    - Geographic area contains ISO-3166-A3 codes
    - Weights are Decimal strings (4 decimal places)

    Args:
        asset_ids: Bulk read request with list of asset IDs
        session: Database session

    Returns:
        List of FAAssetMetadataResponse in request order (missing assets skipped)

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        if not asset_ids:
            return []

        # Fetch assets
        stmt = select(Asset).where(Asset.id.in_(asset_ids))
        result = await session.execute(stmt)
        assets = result.scalars().all()
        asset_map = {asset.id: asset for asset in assets}

        # Fetch provider assignments for has_provider flag
        provider_stmt = select(AssetProviderAssignment.asset_id).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        provider_result = await session.execute(provider_stmt)
        assets_with_provider = {row[0] for row in provider_result.fetchall()}

        responses = []
        for asset_id in asset_ids:
            asset = asset_map.get(asset_id)
            if not asset:
                continue

            # Parse classification params
            classification_params = None
            if asset.classification_params:
                try:
                    classification_params = FAClassificationParams.model_validate_json(asset.classification_params)
                except Exception as e:
                    logger.error(f"Failed to parse classification_params for asset {asset.id}: {e}", extra={"asset_id": asset.id, "error": str(e)})
                    pass  # Skip invalid JSON

            responses.append(
                FAAssetMetadataResponse(
                    asset_id=asset.id,
                    display_name=asset.display_name,
                    currency=asset.currency,
                    icon_url=asset.icon_url,
                    asset_type=asset.asset_type,
                    classification_params=classification_params,
                    has_provider=asset.id in assets_with_provider,
                    )
                )

        return responses
    except Exception as e:
        logger.error(f"Error reading assets bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROVIDER REFRESH ENDPOINTS
# ============================================================================

@price_router.post("/refresh", response_model=FABulkRefreshResponse)
async def refresh_prices_bulk(
    request: FABulkRefreshRequest,
    session: AsyncSession = Depends(get_session_generator)
    ):
    """Bulk refresh prices via providers (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_refresh_prices(request.requests, session)
    except Exception as e:
        logger.error(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@metadata_router.patch("", response_model=list[FAMetadataRefreshResult])
async def update_assets_metadata_bulk(
    patches: List[FAPatchMetadataItem],
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
    [
      {
        "asset_id": 1,
        "patch": {
          "sector": "Technology",
          "geographic_area": {
            "USA": "0.6",
            "GBR": "0.4"
          }
        }
      }
    ]
    ```

    **Response** (per-item results):
    ```json
    [
      {
        "asset_id": 1,
        "success": true,
        "message": "updated",
        "changes": [
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
        patches: List of metadata patches
        session: Database session

    Returns:
        List of FAMetadataRefreshResult (per-item success/failure)

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        results = []
        for item in patches:
            try:
                result = await AssetMetadataService.update_asset_metadata(item.asset_id, item.patch, session)
                # Result is now FAMetadataRefreshResult with changes included
                results.append(result)
            except ValueError as e:
                results.append(FAMetadataRefreshResult(asset_id=item.asset_id, success=False, message=str(e), changes=None))
            except Exception as e:
                logger.error(f"Error updating metadata for asset {item.asset_id}: {e}")
                results.append(FAMetadataRefreshResult(asset_id=item.asset_id, success=False, message="internal error", changes=None))
        return results
    except Exception as e:
        logger.error(f"Error in bulk metadata update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@provider_router.post("/refresh", response_model=FABulkMetadataRefreshResponse, tags=["FA Provider"])
async def refresh_assets_from_provider(
    asset_ids: List[int] = Query(..., description="List of asset IDs to refresh metadata for"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Refresh asset data from assigned providers (bulk operation).

    **EXPLICIT REFRESH** - No auto-refresh during provider assignment.

    Fetches latest metadata from provider and updates:
    - asset_type (if provider supports)
    - classification_params (sector, short_description, geographic_area)

    **Field-level response**:
    - refreshed_fields: Successfully updated from provider
    - missing_data_fields: Provider couldn't fetch (no data available)
    - ignored_fields: Provider doesn't support these fields

    **Example Request**:
    ```
    POST /api/v1/assets/provider/refresh?asset_ids=1&asset_ids=2
    ```

    **Example Response**:
    ```json
    {
      "results": [
        {
          "asset_id": 1,
          "success": true,
          "message": "Refreshed from yfinance",
          "fields_detail": {
            "refreshed_fields": ["asset_type", "sector", "short_description"],
            "missing_data_fields": ["geographic_area"],
            "ignored_fields": []
          }
        }
      ],
      "success_count": 1,
      "failed_count": 0
    }
    ```

    **Per-Item Outcomes**:
    - success=true: Metadata refreshed (may have 0 changes)
    - success=false: No provider, provider doesn't support metadata, or error

    Args:
        asset_ids: List of asset IDs to refresh
        session: Database session

    Returns:
        FABulkMetadataRefreshResponse with per-item results and field-level details

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        result = await AssetSourceManager.refresh_assets_from_provider(asset_ids, session)
        return result
    except Exception as e:
        logger.error(f"Error refreshing assets from provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Include sub-route in main router
# ============================================================================
asset_router.include_router(metadata_router)
asset_router.include_router(price_router)
asset_router.include_router(provider_router)

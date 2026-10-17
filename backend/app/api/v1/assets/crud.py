"""Asset CRUD endpoints (``/assets``): create, read, patch, delete and merge."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.assets import (
    FAAinfoFiltersRequest,
    FAAssetCreateItem,
    FAAssetMergeRequest,
    FAAssetMergeResponse,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FAinfoResponse,
)
from backend.app.schemas.assets.metadata import (
    FAAssetMetadataResponse,
    FAClassificationParams,
)
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.crud import AssetCRUDService

logger = get_logger(__name__)

crud_router = APIRouter()


# ============================================================================
# ASSET CRUD ENDPOINTS
# ============================================================================


@crud_router.post("", response_model=FABulkAssetCreateResponse, status_code=201, tags=["FA CRUD"])
async def create_assets_bulk(
    assets: List[FAAssetCreateItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
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
        logger.exception(f"Error in bulk asset creation: {e}")
        raise HTTPException(status_code=500, detail="Internal error while creating assets") from e


@crud_router.patch("", response_model=FABulkAssetPatchResponse, tags=["FA CRUD"])
async def patch_assets_bulk(
    assets: List[FAAssetPatchItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
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
        response = await AssetCRUDService.patch_assets_bulk(assets, session)
        # I-bis #7 — HTTP 409 semantics: if every item in the batch failed
        # for the same business reason (currency change blocked by market
        # data), raise 409 so clients can distinguish "nothing happened"
        # from the happy-path 200. Individual partial-success responses
        # still return 200 — this only triggers when 100% of the items
        # failed AND at least one failure carries the
        # ``CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA`` token.
        if response.success_count == 0 and len(response.results) > 0 and all(not r.success for r in response.results) and any(r.message and "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA" in r.message for r in response.results):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA",
                    "message": "All assets in the batch are blocked by existing market data.",
                    "results": [r.model_dump() for r in response.results],
                },
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bulk asset patch: {e}")
        raise HTTPException(status_code=500, detail="Internal error while updating assets") from e


@crud_router.get("/all", response_model=List[FAinfoResponse], tags=["FA CRUD"])
async def get_all_assets(session: AsyncSession = Depends(get_session_generator), current_user: User = Depends(get_current_user)):
    """
    Get all active assets without filters.

    Simple endpoint for frontend to load complete asset list.
    Returns all active assets with identifier info.

    **Response Fields**:
    - `identifier`: Asset identifier (ticker, ISIN, etc.) if provider assigned
    - `identifier_type`: Type of identifier (TICKER, ISIN, UUID, OTHER)
    """
    try:
        filters = FAAinfoFiltersRequest(active=True)
        return await AssetCRUDService.list_assets(filters, session, user_id=current_user.id)
    except Exception as e:
        logger.exception(f"Error getting all assets: {e}")
        raise HTTPException(status_code=500, detail="Internal error while listing assets") from e


@crud_router.get("/query", response_model=List[FAinfoResponse], tags=["FA CRUD"])
async def list_assets(
    currency: Optional[str] = Query(None, description="Filter by currency (ISO 4217, e.g., USD)"),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type enum"),
    active: Optional[bool] = Query(None, description="Tri-state: true = only active, false = only inactive, omit = return both (default)"),
    is_benchmark: Optional[bool] = Query(None, description="Tri-state: true = only benchmarks, false = only non-benchmarks, omit = return both (default)"),
    search: Optional[str] = Query(None, description="Search in display_name (partial match)"),
    isin: Optional[str] = Query(None, description="Exact ISIN match"),
    ticker: Optional[str] = Query(None, description="Exact ticker match"),
    cusip: Optional[str] = Query(None, description="Exact CUSIP match"),
    sedol: Optional[str] = Query(None, description="Exact SEDOL match"),
    figi: Optional[str] = Query(None, description="Exact FIGI match"),
    uuid: Optional[str] = Query(None, description="Exact UUID match"),
    identifier_other: Optional[str] = Query(None, description="Partial match in identifier_other"),
    identifier_contains: Optional[str] = Query(None, description="Partial match in any identifier field"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
):
    """
    List all assets with optional filters - enhanced for BRIM asset matching.

    **Query Parameters**:
    - `currency`: Filter by currency code (e.g., "USD", "EUR")
    - `asset_type`: Filter by type enum (STOCK, ETF, BOND, etc.)
    - `active`: Include only active assets (default: true)
    - `is_benchmark`: Include only assets flagged as comparison benchmarks (omit for both)
    - `search`: Search text in display_name (case-insensitive partial match)
    - `isin`: Exact ISIN match
    - `ticker`: Exact ticker match
    - `cusip`: Exact CUSIP match
    - `sedol`: Exact SEDOL match
    - `figi`: Exact FIGI match
    - `uuid`: Exact UUID match
    - `identifier_other`: Partial match in identifier_other field
    - `identifier_contains`: Partial match in any identifier

    **Response Fields**:
    - `provider_code`: Provider code string if assigned (e.g. 'yfinance'), null otherwise
    - `has_metadata`: True if asset has classification metadata
    - `identifier`: Asset identifier (ticker, ISIN, etc.) if provider assigned
    - `identifier_type`: Type of identifier (TICKER, ISIN, UUID, OTHER)

    **Example**:
    ```
    GET /api/v1/assets/query?currency=USD&asset_type=STOCK&search=Apple
    GET /api/v1/assets/query?isin=US0378331005
    GET /api/v1/assets/query?ticker=AAPL
    ```
    """
    try:
        filters = FAAinfoFiltersRequest(
            currency=currency,
            asset_type=asset_type,
            active=active,
            is_benchmark=is_benchmark,
            search=search,
            isin=isin,
            ticker=ticker,
            cusip=cusip,
            sedol=sedol,
            figi=figi,
            uuid=uuid,
            identifier_other=identifier_other,
            identifier_contains=identifier_contains,
        )
        return await AssetCRUDService.list_assets(filters, session, user_id=current_user.id)
    except Exception as e:
        logger.exception(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail="Internal error while listing assets") from e


@crud_router.delete("", response_model=FABulkAssetDeleteResponse, tags=["FA CRUD"])
async def delete_assets_bulk(
    asset_ids: List[int] = Query(..., min_length=1, description="List of asset IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Delete multiple assets in bulk (partial success allowed).

    **Warning**: This will CASCADE DELETE:
    - Provider assignments (asset_provider_assignments table)
    - Price history (price_history table)

    **Blocks deletion** if asset has transactions (foreign key constraint).

    **Request Example**:
    ```
    DELETE /api/v1/assets?asset_ids=1&asset_ids=2&asset_ids=3
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
        return await AssetCRUDService.delete_assets_bulk(asset_ids, session)
    except Exception as e:
        logger.exception(f"Error in bulk asset deletion: {e}")
        raise HTTPException(status_code=500, detail="Internal error while deleting assets") from e


@crud_router.post("/merge", response_model=FAAssetMergeResponse, tags=["FA CRUD"])
async def merge_assets(
    payload: FAAssetMergeRequest,
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Merge two assets that describe the same instrument, keeping ``target_asset_id``.

    Typical case: an Italian BTP booked twice because the placement ("CUM") ISIN and
    the tradeable market ISIN were treated as two instruments. Transactions, prices
    and events converge on the target; every identifier survives, either as primary
    or inside ``identifier_other``; the source asset is **deleted**.

    Collision policy: on the same price date the **target row wins**; duplicate events
    are dropped after remapping the transactions that realized them.

    Use ``dry_run: true`` to obtain the preview shown in the confirmation dialog
    without writing anything.

    **Request Example**:
    ```json
    {
      "source_asset_id": 42,
      "target_asset_id": 7,
      "identifier_primaries": {"identifier_isin": "IT0005634800"},
      "dry_run": true
    }
    ```
    """
    try:
        return await AssetCRUDService.merge_assets(
            source_asset_id=payload.source_asset_id,
            target_asset_id=payload.target_asset_id,
            session=session,
            identifier_primaries=payload.identifier_primaries,
            dry_run=payload.dry_run,
        )
    except AssetSourceError as e:
        status = 404 if e.error_code == "NOT_FOUND" else 400
        raise HTTPException(status_code=status, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error merging assets: {e}")
        raise HTTPException(status_code=500, detail="Internal error while merging assets") from e


# Bulk read endpoint
@crud_router.get("", response_model=List[FAAssetMetadataResponse], tags=["FA CRUD"])
async def read_assets_bulk(
    asset_ids: List[int] = Query(..., description="List of asset IDs to read"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
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
        "provider_code": null
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
        "provider_code": "yfinance"
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

        # Fetch provider assignments for provider_code
        provider_stmt = select(
            AssetProviderAssignment.asset_id,
            AssetProviderAssignment.provider_code,
        ).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        provider_result = await session.execute(provider_stmt)
        provider_map = {row[0]: row[1] for row in provider_result.fetchall()}

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
                    logger.exception(
                        f"Failed to parse classification_params for asset {asset.id}: {e}",
                        extra={"asset_id": asset.id, "error": str(e)},
                    )
                    # Skip invalid JSON

            responses.append(
                FAAssetMetadataResponse(
                    asset_id=asset.id,
                    display_name=asset.display_name,
                    currency=asset.currency,
                    icon_url=asset.icon_url,
                    asset_type=asset.asset_type,
                    quote_base_quantity=asset.quote_base_quantity,
                    classification_params=classification_params,
                    provider_code=provider_map.get(asset.id),
                )
            )

        return responses
    except Exception as e:
        logger.exception(f"Error reading assets bulk: {e}")
        raise HTTPException(status_code=500, detail="Internal error while reading assets") from e
